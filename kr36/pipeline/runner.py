"""融资关联公司主流程：拉取 → 解析详情 → 筛选华南关联 → 导出 → 通知。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kr36.core.config import DEFAULT_SOURCE, Settings
from kr36.domain.filters import is_south_china_region, should_exclude_shareholder
from kr36.core.models import FinancingCompany, FinancingListRow, ProjectDetail, RelatedCompanyRow
from kr36.notify.feishu import FeishuNotifier
from kr36.output.excel import save_excel, save_financing_excel
from kr36.sources.company.iyiou.detail import parse_com_id_from_url
from kr36.sources.events.iyiou.adapter import fetch_iyiou_financing_list
from kr36.sources.events.qcc.adapter import fetch_qcc_events
from kr36.sources.events.qcc.client import QccClient
from kr36.sources.infra.pitchhub.client import PitchHubClient
from kr36.sources.events.pitchhub.financing import FinancingCrawler, format_financing_date
from kr36.sources.company.pitchhub.project import ProjectService
from kr36.services.cached_project import CachedProjectService
from kr36.storage import (
    BatchRepository,
    CompanyRepository,
    FinancingRepository,
    RelatedRepository,
    connect,
    init_db,
)


class FinancingRelationPipeline:
    """融资关联公司拉取主流程。"""

    def __init__(self, settings: Settings | None = None) -> None:
        """初始化 pipeline 各组件：客户端、仓储、缓存服务与飞书通知。"""
        self.settings = settings or Settings()
        self.client = PitchHubClient(
            delay_min=self.settings.delay_min,
            delay_max=self.settings.delay_max,
        )
        self.financing = FinancingCrawler(self.client)
        self.project = ProjectService(self.client)
        self.feishu = FeishuNotifier(self.settings)
        self.conn = connect(self.settings.db_path)
        init_db(self.conn)
        self.company_repo = CompanyRepository(self.conn, cache_ttl_days=self.settings.cache_ttl_days)
        self.batch_repo = BatchRepository(self.conn)
        self.financing_repo = FinancingRepository(self.conn)
        self.related_repo = RelatedRepository(self.conn)
        self.cached_project = CachedProjectService(self.project, self.company_repo)
        # 亿欧详情在拉取融资列表时批量预取，按 com_id 索引
        self._iyiou_details: dict[str, ProjectDetail] = {}

    def run(
        self,
        *,
        max_pages: int = 1,
        page_size: int | None = None,
        days: int | None = None,
        output_dir: str | None = None,
        push_feishu: bool | None = None,
        source: str = DEFAULT_SOURCE,
        iyiou_headless: bool = True,
        qcc_event_types: list[str] | None = None,
        qcc_chain_code: str = "IC0007",
        qcc_search_key: str = "",
    ) -> tuple[list[RelatedCompanyRow], Path, Path, int, dict]:
        """执行完整 pipeline，返回关联行、两个 Excel 路径、融资条数与元信息。"""
        page_size = page_size or self.settings.page_size
        output_root = Path(output_dir or self.settings.output_dir)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        related_excel_path = output_root / f"融资关联公司_{stamp}.xlsx"
        financing_excel_path = output_root / f"融资公司列表_{stamp}.xlsx"

        batch_id = self.batch_repo.start_batch(
            {
                "max_pages": max_pages,
                "page_size": page_size,
                "days": days,
                "source": source,
                "qcc_event_types": qcc_event_types,
                "qcc_chain_code": qcc_chain_code,
            }
        )

        financing_list = self._fetch_financing_list(
            max_pages=max_pages,
            page_size=page_size,
            days=days,
            source=source,
            iyiou_headless=iyiou_headless,
            qcc_event_types=qcc_event_types,
            qcc_chain_code=qcc_chain_code,
            qcc_search_key=qcc_search_key,
        )
        rows, financing_rows = self._process_financing_list(financing_list, batch_id)

        save_financing_excel(financing_rows, financing_excel_path)
        save_excel(rows, related_excel_path)

        cache_stats = {
            "hits": self.cached_project.stats.hits,
            "misses": self.cached_project.stats.misses,
            "expired": self.cached_project.stats.expired,
        }
        self.batch_repo.finish_batch(
            batch_id,
            cache_hits=cache_stats["hits"],
            cache_misses=cache_stats["misses"],
            cache_expired=cache_stats["expired"],
        )

        excel_cleaned = False
        should_push = push_feishu if push_feishu is not None else self.settings.push_feishu
        if should_push:
            try:
                self.feishu.notify_result(
                    rows,
                    related_excel_path,
                    financing_excel_path=financing_excel_path,
                    financing_count=len(financing_list),
                )
                excel_cleaned = True
                print("飞书：摘要与 Excel 已发送，本地 Excel 已清理")
            except RuntimeError as exc:
                print(f"飞书通知失败: {exc}")

        meta = {
            "batch_id": batch_id,
            "cache": cache_stats,
            "db_path": self.settings.db_path,
            "excel_cleaned": excel_cleaned,
        }
        return rows, related_excel_path, financing_excel_path, len(financing_list), meta

    def _fetch_financing_list(
        self,
        *,
        max_pages: int,
        page_size: int,
        days: int | None,
        source: str,
        iyiou_headless: bool,
        qcc_event_types: list[str] | None = None,
        qcc_chain_code: str = "IC0007",
        qcc_search_key: str = "",
    ) -> list[FinancingCompany]:
        """按数据源拉取融资列表；source=all 时合并 36氪、企查查（按 days）与亿欧（仅首页）。"""
        self._iyiou_details = {}
        if source == "qcc":
            return self._fetch_qcc_list(
                max_pages=max_pages,
                page_size=page_size,
                days=days,
                qcc_event_types=qcc_event_types,
                qcc_chain_code=qcc_chain_code,
                qcc_search_key=qcc_search_key,
            )

        if source == "iyiou":
            companies, self._iyiou_details = fetch_iyiou_financing_list(
                headless=iyiou_headless,
                days=days,
            )
            return companies

        if source == "36kr":
            kr_list = self.financing.crawl(max_pages=max_pages, page_size=page_size, days=days)
            print(f"36氪：拉取 {len(kr_list)} 条")
            return kr_list

        if source == "all":
            merged = self.financing.crawl(max_pages=max_pages, page_size=page_size, days=days)
            print(f"36氪：拉取 {len(merged)} 条")
            try:
                qcc_list = self._fetch_qcc_list(
                    max_pages=max_pages,
                    page_size=page_size,
                    days=days,
                    qcc_event_types=qcc_event_types,
                    qcc_chain_code=qcc_chain_code,
                    qcc_search_key=qcc_search_key,
                )
                merged = self._merge_financing_lists(merged, qcc_list, label="企查查")
            except Exception as exc:
                print(f"[WARN] 企查查拉取失败，已跳过: {exc}")
            try:
                iyiou_list, self._iyiou_details = fetch_iyiou_financing_list(
                    headless=iyiou_headless,
                    homepage_only=True,
                )
                merged = self._merge_financing_lists(merged, iyiou_list, label="亿欧")
            except Exception as exc:
                print(f"[WARN] 亿欧数据源拉取失败，已跳过: {exc}")
            print(f"数据源合并：合计 {len(merged)} 条")
            return merged

        kr_list = self.financing.crawl(max_pages=max_pages, page_size=page_size, days=days)
        print(f"36氪：拉取 {len(kr_list)} 条")
        return kr_list

    def _fetch_qcc_list(
        self,
        *,
        max_pages: int,
        page_size: int,
        days: int | None,
        qcc_event_types: list[str] | None,
        qcc_chain_code: str,
        qcc_search_key: str,
    ) -> list[FinancingCompany]:
        """拉取企查查创投事件列表。"""
        client = QccClient(
            delay_min=self.settings.delay_min,
            delay_max=self.settings.delay_max,
        )
        items = fetch_qcc_events(
            event_types=qcc_event_types,
            max_pages=max_pages,
            page_size=page_size,
            days=days,
            search_key=qcc_search_key,
            chain_code=qcc_chain_code,
            client=client,
        )
        scope = f"最近 {days} 天" if days else f"{max_pages} 页"
        print(f"企查查：拉取 {len(items)} 条（{scope}）")
        return items

    @staticmethod
    def _event_merge_key(item: FinancingCompany) -> tuple:
        """跨数据源合并时的去重键。"""
        fd = format_financing_date(item.financing_date) or ""
        if item.external_id:
            return (item.source, item.event_type, item.external_id)
        return (item.source, item.project_name, fd, item.event_type)

    def _merge_financing_lists(
        self,
        base: list[FinancingCompany],
        new_items: list[FinancingCompany],
        *,
        label: str,
    ) -> list[FinancingCompany]:
        """将 new_items 并入 base，按 _event_merge_key 去重。"""
        seen = {self._event_merge_key(item) for item in base}
        merged = list(base)
        added = 0
        for item in new_items:
            key = self._event_merge_key(item)
            if key in seen:
                continue
            merged.append(item)
            seen.add(key)
            added += 1
        skipped = len(new_items) - added
        print(f"{label}：{len(new_items)} 条（新增 {added} 条，重复跳过 {skipped} 条）")
        return merged

    def _process_financing_list(
        self,
        financing_list: list[FinancingCompany],
        batch_id: int,
    ) -> tuple[list[RelatedCompanyRow], list[FinancingListRow]]:
        """逐条解析公司详情、入库融资事件，并收集华南关联公司。"""
        results: list[RelatedCompanyRow] = []
        financing_rows: list[FinancingListRow] = []
        seen_pairs: set[tuple[str, str]] = set()

        for company in financing_list:
            detail = self._resolve_detail(company)
            company_id = None
            if detail:
                company_id = self.company_repo.save_detail(detail)

            event_id = self.financing_repo.save_event(batch_id, company, company_id=company_id)
            if company_id:
                self.financing_repo.update_company_link(event_id, company_id)

            financing_rows.append(self._financing_list_row(company, detail))
            base = self._base_row(company)
            related_items = self._collect_related_items(company, detail)

            for related_name, relation_type in related_items:
                pair = (company.project_name, related_name)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                related_company_id = self.company_repo.get_or_create_placeholder(related_name)
                self.related_repo.save_related(
                    batch_id,
                    event_id,
                    related_company_id,
                    relation_type,
                    related_name,
                )
                results.append(
                    RelatedCompanyRow(
                        financing_company=base.financing_company,
                        financing_date=base.financing_date,
                        financing_amount=base.financing_amount,
                        financing_round=base.financing_round,
                        related_company=related_name,
                        related_type=relation_type,
                    )
                )

        return results, financing_rows

    def _resolve_detail(self, company: FinancingCompany) -> ProjectDetail | None:
        """按数据源获取公司详情：36氪走缓存 API，亿欧用预拉取的详情字典。"""
        detail: ProjectDetail | None = None
        if company.source == "36kr":
            detail = self.cached_project.get_detail(company.project_id)
            if not detail and company.project_name:
                detail = self.cached_project.get_detail_by_name(company.project_name)
        elif company.source == "iyiou":
            com_id = company.com_id or parse_com_id_from_url(company.url)
            if com_id:
                detail = self._iyiou_details.get(com_id)
        elif company.source == "qcc":
            detail = self._detail_from_financing_company(company)
        if detail and self._has_list_location(company):
            detail = self._merge_list_into_detail(detail, company)
        elif not detail and self._has_list_location(company):
            detail = self._detail_from_financing_company(company)
        elif not detail and company.source != "36kr":
            detail = self._detail_from_financing_company(company)
        return detail

    @staticmethod
    def _has_list_location(company: FinancingCompany) -> bool:
        """判断融资列表是否携带地址或全称信息。"""
        return bool(company.reg_location or company.province or company.full_name)

    @staticmethod
    def _merge_list_into_detail(detail: ProjectDetail, company: FinancingCompany) -> ProjectDetail:
        """将列表中的地址/全称补全到详情对象，并重新判定华南。"""
        if not detail.reg_location and company.reg_location:
            detail.reg_location = company.reg_location
        if not detail.province and company.province:
            detail.province = company.province
        if not detail.company_name and company.full_name:
            detail.company_name = company.full_name
        detail.is_south_china = is_south_china_region(
            reg_location=detail.reg_location,
            province=detail.province,
        )
        return detail

    def _collect_related_items(
        self,
        company: FinancingCompany,
        detail: ProjectDetail | None,
    ) -> list[tuple[str, str]]:
        """收集华南关联项：(公司名, 关联类型)。类型为 self 或 shareholder。"""
        related_items: list[tuple[str, str]] = []
        reg_location = (detail.reg_location if detail else "") or company.reg_location
        province = (detail.province if detail else "") or company.province

        if (detail and detail.is_south_china) or is_south_china_region(
            reg_location=reg_location,
            province=province,
        ):
            name = (
                (detail.company_name if detail else "")
                or company.full_name
                or company.project_name
            )
            related_items.append((name, "self"))

        if not detail or company.source != "36kr":
            # 亿欧/企查查无股东链，仅判断融资公司本身是否在华南
            return related_items

        for shareholder_name in [
            sh.name for sh in detail.shareholders if not should_exclude_shareholder(sh.name)
        ]:
            shareholder_detail = self.cached_project.get_detail_by_name(shareholder_name)
            if not shareholder_detail:
                continue
            if shareholder_detail.is_south_china or is_south_china_region(
                reg_location=shareholder_detail.reg_location,
                province=shareholder_detail.province,
            ):
                related_items.append(
                    (shareholder_detail.company_name or shareholder_name, "shareholder")
                )
        return related_items

    @staticmethod
    def _detail_from_financing_company(company: FinancingCompany) -> ProjectDetail:
        """从融资列表字段构造最小 ProjectDetail（无股东信息）。"""
        reg_location = company.reg_location or ""
        province = company.province or ""
        return ProjectDetail(
            project_id=company.project_id,
            name=company.project_name,
            company_name=company.full_name or company.project_name,
            reg_location=reg_location,
            province=province,
            city=company.city or "",
            country=company.country or "中国",
            is_south_china=is_south_china_region(reg_location=reg_location, province=province),
        )

    @staticmethod
    def _financing_list_row(
        company: FinancingCompany,
        detail: ProjectDetail | None,
    ) -> FinancingListRow:
        """将融资事件与详情合并为 Excel 导出行。"""
        reg_location = (detail.reg_location if detail else "") or company.reg_location or ""
        province = (detail.province if detail else "") or company.province or ""
        return FinancingListRow(
            brief_name=company.project_name,
            full_name=(detail.company_name if detail else company.full_name) or company.project_name,
            brief_intro=company.project_brief,
            financing_round=company.financing_round,
            financing_date=format_financing_date(company.financing_date),
            financing_amount=company.financing_money,
            investor=company.investor,
            industry=company.national_industry or "、".join(company.industry_list),
            reg_location=reg_location,
            province=province,
            country=(detail.country if detail else company.country) or "",
            source=company.source,
            event_type=company.event_type,
            industry_category=company.industry_category,
            industry_major=company.industry_major,
            national_industry=company.national_industry,
            city=(detail.city if detail else company.city) or "",
            county=company.county,
            establish_date=company.establish_date,
            listing_board=company.listing_board,
            buyer=company.buyer,
            seller=company.seller,
            trade_equity_ratio=company.trade_equity_ratio,
            exit_type=company.exit_type,
            holder_name=company.holder_name,
            return_multiple=company.return_multiple,
            irr=company.irr,
            exit_equity_ratio=company.exit_equity_ratio,
        )

    @staticmethod
    def _base_row(company: FinancingCompany) -> RelatedCompanyRow:
        """构造关联行的融资公司基础信息（不含关联公司名）。"""
        return RelatedCompanyRow(
            financing_company=company.project_name,
            financing_date=format_financing_date(company.financing_date),
            financing_amount=company.financing_money,
            financing_round=company.financing_round,
            related_company="",
        )
