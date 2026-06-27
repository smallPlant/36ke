from __future__ import annotations

from datetime import datetime
from pathlib import Path

from kr36.client import PitchHubClient
from kr36.config import Settings
from kr36.db.connection import connect, init_db
from kr36.db.repository import BatchRepository, CompanyRepository, FinancingRepository, RelatedRepository
from kr36.export import save_excel, save_financing_excel
from kr36.feishu import FeishuNotifier
from kr36.filters import is_south_china_region, should_exclude_shareholder
from kr36.financing import FinancingCrawler, format_financing_date
from kr36.iyiou.financing_adapter import fetch_iyiou_financing_list
from kr36.iyiou.company_detail import parse_com_id_from_url
from kr36.models import FinancingCompany, FinancingListRow, ProjectDetail, RelatedCompanyRow
from kr36.project import ProjectService
from kr36.services.cached_project import CachedProjectService


class FinancingRelationPipeline:
    """融资关联公司拉取主流程。"""

    def __init__(self, settings: Settings | None = None) -> None:
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
        self._iyiou_details: dict[str, ProjectDetail] = {}

    def run(
        self,
        *,
        max_pages: int = 1,
        page_size: int | None = None,
        days: int | None = None,
        output_dir: str | None = None,
        push_feishu: bool = True,
        source: str = "36kr",
        iyiou_headless: bool = True,
    ) -> tuple[list[RelatedCompanyRow], Path, Path, int, dict]:
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
            }
        )

        financing_list = self._fetch_financing_list(
            max_pages=max_pages,
            page_size=page_size,
            days=days,
            source=source,
            iyiou_headless=iyiou_headless,
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

        if push_feishu:
            try:
                self.feishu.notify_result(
                    rows,
                    related_excel_path,
                    financing_excel_path=financing_excel_path,
                    financing_count=len(financing_list),
                )
                print("飞书：摘要与 Excel（关联结果 + 融资列表）已发送至本人")
            except RuntimeError as exc:
                print(f"飞书通知失败: {exc}")

        meta = {"batch_id": batch_id, "cache": cache_stats, "db_path": self.settings.db_path}
        return rows, related_excel_path, financing_excel_path, len(financing_list), meta

    def _fetch_financing_list(
        self,
        *,
        max_pages: int,
        page_size: int,
        days: int | None,
        source: str,
        iyiou_headless: bool,
    ) -> list[FinancingCompany]:
        self._iyiou_details = {}
        if source == "iyiou":
            companies, self._iyiou_details = fetch_iyiou_financing_list(
                headless=iyiou_headless,
                days=days,
            )
            return companies

        kr_list = self.financing.crawl(max_pages=max_pages, page_size=page_size, days=days)
        if source != "all":
            return kr_list

        iyiou_list: list[FinancingCompany] = []
        try:
            iyiou_list, self._iyiou_details = fetch_iyiou_financing_list(
                headless=iyiou_headless,
                days=days,
            )
        except Exception as exc:
            print(f"⚠️  亿欧数据源拉取失败，已跳过（仅使用 36氪）: {exc}")
            return kr_list

        seen = {(item.project_name, format_financing_date(item.financing_date) or "") for item in kr_list}
        merged = list(kr_list)
        added = 0
        for item in iyiou_list:
            key = (item.project_name, format_financing_date(item.financing_date) or "")
            if key in seen:
                continue
            merged.append(item)
            seen.add(key)
            added += 1
        skipped = len(iyiou_list) - added
        print(
            f"数据源合并：36氪 {len(kr_list)} 条，亿欧 {len(iyiou_list)} 条"
            f"（新增 {added} 条，重复跳过 {skipped} 条），合计 {len(merged)} 条"
        )
        return merged

    def _process_financing_list(
        self,
        financing_list: list[FinancingCompany],
        batch_id: int,
    ) -> tuple[list[RelatedCompanyRow], list[FinancingListRow]]:
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
        detail: ProjectDetail | None = None
        if company.source == "36kr":
            detail = self.cached_project.get_detail(company.project_id)
            if not detail and company.project_name:
                detail = self.cached_project.get_detail_by_name(company.project_name)
        elif company.source == "iyiou":
            com_id = company.com_id or parse_com_id_from_url(company.url)
            if com_id:
                detail = self._iyiou_details.get(com_id)
        if detail and self._has_list_location(company):
            detail = self._merge_list_into_detail(detail, company)
        elif not detail and self._has_list_location(company):
            detail = self._detail_from_financing_company(company)
        elif not detail and company.source != "36kr":
            detail = self._detail_from_financing_company(company)
        return detail

    @staticmethod
    def _has_list_location(company: FinancingCompany) -> bool:
        return bool(company.reg_location or company.province or company.full_name)

    @staticmethod
    def _merge_list_into_detail(detail: ProjectDetail, company: FinancingCompany) -> ProjectDetail:
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
        reg_location = company.reg_location or ""
        province = company.province or ""
        return ProjectDetail(
            project_id=company.project_id,
            name=company.project_name,
            company_name=company.full_name or company.project_name,
            reg_location=reg_location,
            province=province,
            country=company.country or "中国",
            is_south_china=is_south_china_region(reg_location=reg_location, province=province),
        )

    @staticmethod
    def _financing_list_row(
        company: FinancingCompany,
        detail: ProjectDetail | None,
    ) -> FinancingListRow:
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
            industry="、".join(company.industry_list),
            reg_location=reg_location,
            province=province,
            country=(detail.country if detail else company.country) or "",
            source=company.source,
        )

    @staticmethod
    def _base_row(company: FinancingCompany) -> RelatedCompanyRow:
        return RelatedCompanyRow(
            financing_company=company.project_name,
            financing_date=format_financing_date(company.financing_date),
            financing_amount=company.financing_money,
            financing_round=company.financing_round,
            related_company="",
        )
