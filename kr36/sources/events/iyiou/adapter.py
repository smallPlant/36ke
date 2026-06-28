"""亿欧融资数据适配器：将 InvestEvent 转换为统一的 FinancingCompany 模型。"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from kr36.core.models import FinancingCompany, ProjectDetail
from kr36.sources.infra.iyiou.browser import IyiouBrowser
from kr36.sources.events.iyiou.client import IyiouInvestClient
from kr36.sources.company.iyiou.detail import (
    apply_detail_to_company,
    fetch_company_detail,
    parse_com_id_from_url,
)
from kr36.sources.events.pitchhub.financing import format_financing_date


def _stable_project_id(invest_id: str) -> int:
    """亿欧无数字 project_id，用 invest_id 哈希生成稳定的伪 ID。"""
    digest = hashlib.sha1(invest_id.encode()).hexdigest()
    return int(digest[:15], 16)


def _parse_invest_time_ms(invest_time: str) -> int:
    """将 YYYY-MM-DD 投资时间转为毫秒时间戳。"""
    if not invest_time:
        return 0
    try:
        parts = [int(x) for x in invest_time.split("-")]
        if len(parts) != 3:
            return 0
        dt = datetime(parts[0], parts[1], parts[2], tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return 0


def fetch_iyiou_financing_list(
    *,
    headless: bool = True,
    days: int | None = None,
    enrich_details: bool = True,
    homepage_only: bool = False,
) -> tuple[list[FinancingCompany], dict[str, ProjectDetail]]:
    """通过 Playwright 拉取亿欧投资事件，并可选访问企业详情页补充工商信息。

    homepage_only=True 时仅拉取首页一页，不按 days 过滤日期。
    """
    details: dict[str, ProjectDetail] = {}

    with IyiouBrowser(headless=headless) as browser:
        client = IyiouInvestClient(browser)
        client.warmup()
        events, _ = client.fetch_pages(max_pages=1, page_size=20)
        if not events:
            events, _ = client.fetch_initial_state()

        since_ms = None
        if days and not homepage_only:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            since_ms = int(since.timestamp() * 1000)

        results: list[FinancingCompany] = []
        for event in events:
            financing_date = _parse_invest_time_ms(event.invest_time)
            if since_ms and financing_date and financing_date < since_ms:
                continue

            com_id = event.com_id or ""
            results.append(
                FinancingCompany(
                    project_id=_stable_project_id(event.invest_id or com_id or event.brief_name),
                    project_name=event.brief_name,
                    project_brief=event.brief_intro,
                    industry_list=[event.industry] if event.industry else [],
                    financing_round=event.invest_round,
                    financing_date=financing_date,
                    financing_money=event.invest_amount,
                    investor=event.investors,
                    url=f"https://data.iyiou.com/company/details/{com_id}/profile" if com_id else "",
                    source="iyiou",
                    com_id=com_id,
                    full_name=event.full_name or event.brief_name,
                    reg_location=event.reg_location,
                    province=event.province,
                    country=event.country or "中国",
                )
            )

        if enrich_details and results and browser.page:
            enriched = 0
            failed = 0
            for company in results:
                com_id = company.com_id or parse_com_id_from_url(company.url)
                if not com_id or com_id in details:
                    continue
                try:
                    detail = fetch_company_detail(
                        browser.page,
                        com_id=com_id,
                        project_id=company.project_id,
                        brief_name=company.project_name,
                    )
                except Exception as exc:
                    failed += 1
                    print(f"⚠️  亿欧详情跳过 {company.project_name}: {exc}")
                    continue
                if detail:
                    details[com_id] = detail
                    apply_detail_to_company(company, detail)
                    enriched += 1
            if enriched or failed:
                print(f"亿欧详情补充：成功 {enriched} 家，跳过 {failed} 家")

        mode = "首页" if homepage_only or not days else f"最近 {days} 天"
        print(f"亿欧：拉取 {len(results)} 条（{mode}）")

    return results, details
