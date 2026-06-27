from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from kr36.financing import format_financing_date
from kr36.iyiou.browser import IyiouBrowser
from kr36.iyiou.client import IyiouInvestClient
from kr36.iyiou.company_detail import (
    apply_detail_to_company,
    fetch_company_detail,
    parse_com_id_from_url,
)
from kr36.models import FinancingCompany, ProjectDetail


def _stable_project_id(invest_id: str) -> int:
    digest = hashlib.sha1(invest_id.encode()).hexdigest()
    return int(digest[:15], 16)


def _parse_invest_time_ms(invest_time: str) -> int:
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
) -> tuple[list[FinancingCompany], dict[str, ProjectDetail]]:
    """通过 Playwright 拉取亿欧投资事件，并可选访问企业详情页补充工商信息。"""
    details: dict[str, ProjectDetail] = {}

    with IyiouBrowser(headless=headless) as browser:
        client = IyiouInvestClient(browser)
        client.warmup()
        events, _ = client.fetch_pages(max_pages=1, page_size=20)
        if not events:
            events, _ = client.fetch_initial_state()

        since_ms = None
        if days:
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

    return results, details
