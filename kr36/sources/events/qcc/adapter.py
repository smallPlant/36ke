from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from kr36.core.models import FinancingCompany
from kr36.sources.events.pitchhub.financing import format_financing_date
from kr36.sources.events.qcc.auth import ensure_qcc_login
from kr36.sources.events.qcc.client import QccClient
from kr36.sources.events.qcc.constants import (
    DATA_SOURCE_QCC,
    DEFAULT_PAGE_SIZE,
    EVENT_ADDITIONAL,
    EVENT_EXIT,
    EVENT_INDUSTRIAL_CHAIN,
    EVENT_IPO,
    EVENT_MAINLAND_FINANCING,
    EVENT_MERGER_ACQUISITION,
    EVENT_TYPES,
)

_MAX_PAGES_WHEN_DAYS = 100

_EVENT_NORMALIZERS = {
    EVENT_MAINLAND_FINANCING: "_normalize_mainland",
    EVENT_IPO: "_normalize_ipo",
    EVENT_EXIT: "_normalize_exit",
    EVENT_MERGER_ACQUISITION: "_normalize_merger",
    EVENT_ADDITIONAL: "_normalize_additional",
    EVENT_INDUSTRIAL_CHAIN: "_normalize_industrial_chain",
}


def fetch_qcc_events(
    *,
    event_types: Iterable[str] | None = None,
    max_pages: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    days: int | None = None,
    search_key: str = "",
    chain_code: str = "",
    client: QccClient | None = None,
) -> list[FinancingCompany]:
    """拉取一个或多个企查查创投事件列表。"""
    selected = list(event_types or EVENT_TYPES)
    unknown = [item for item in selected if item not in EVENT_TYPES]
    if unknown:
        raise ValueError(f"未知事件类型: {', '.join(unknown)}")

    if not ensure_qcc_login():
        raise RuntimeError("企查查登录未完成，无法拉取数据")

    http = client or QccClient()
    since_ts = _since_ts(days) if days else None
    page_limit = _MAX_PAGES_WHEN_DAYS if days else max_pages

    collected: list[FinancingCompany] = []
    seen: set[tuple[str, str]] = set()

    for event_type in selected:
        chain = chain_code if event_type == EVENT_INDUSTRIAL_CHAIN else ""
        for page_index in range(1, page_limit + 1):
            payload = http.fetch_event_page(
                event_type,
                page_index=page_index,
                page_size=page_size,
                search_key=search_key,
                chain_code=chain,
            )
            items = payload.get("Result") or []
            if not items:
                break

            stop = False
            for raw in items:
                company = normalize_qcc_event(raw, event_type=event_type, chain_code=chain)
                if since_ts and company.financing_date and company.financing_date < since_ts:
                    stop = True
                    continue
                key = (company.event_type, company.external_id)
                if key in seen:
                    continue
                seen.add(key)
                collected.append(company)

            paging = payload.get("Paging") or {}
            total_page = _total_pages(paging, page_size)
            if stop or page_index >= total_page:
                break

    return collected


def normalize_qcc_event(
    raw: dict[str, Any],
    *,
    event_type: str,
    chain_code: str = "",
) -> FinancingCompany:
    """将企查查原始事件记录规范化为 FinancingCompany。"""
    handler_name = _EVENT_NORMALIZERS.get(event_type, "_normalize_mainland")
    handler = globals()[handler_name]
    return handler(raw, event_type=event_type, chain_code=chain_code)


def _normalize_mainland(raw: dict[str, Any], *, event_type: str, chain_code: str) -> FinancingCompany:
    """境内融资：融资日期、项目名称、轮次、金额、投资方、行业、地区、成立日期。"""
    area = raw.get("Area") or {}
    industry_category, industry_major = _qcc_industry(raw)
    product_name = _strip_html(raw.get("ProductName") or "")
    company_name = raw.get("CompanyName") or ""

    return _base_company(
        raw,
        event_type=event_type,
        chain_code=chain_code,
        project_name=product_name or company_name,
        company_name=company_name,
        project_brief=raw.get("Slogan") or "",
        financing_round=raw.get("Round") or "",
        financing_date=_event_date_ms(raw, "FinanceDate"),
        financing_money=raw.get("Amount") or "",
        investor=_format_participants(raw.get("ParticipantDetails")),
        industry=_national_industry(raw),
        industry_category=industry_category,
        industry_major=industry_major,
        area=area,
        country=raw.get("Nation") or "",
        establish_date=_establish_date(raw),
        url=_build_product_url(raw),
    )


def _normalize_ipo(raw: dict[str, Any], *, event_type: str, chain_code: str) -> FinancingCompany:
    """IPO 上市：上市日期、上市板块、募资金额、投资方、行业门类/大类、成立日期。"""
    area = raw.get("Area") or {}
    industry_category, industry_major = _qcc_industry(raw)
    product_name = _strip_html(raw.get("ProductName") or "")
    company_name = raw.get("CompanyName") or ""

    return _base_company(
        raw,
        event_type=event_type,
        chain_code=chain_code,
        project_name=product_name or company_name,
        company_name=company_name,
        project_brief=raw.get("Slogan") or "",
        financing_round=raw.get("ShortStockExchange") or raw.get("ListSection") or "",
        financing_date=_event_date_ms(raw, "FinanceDate"),
        financing_money=raw.get("Amount") or "",
        investor=_format_participants(raw.get("ParticipantDetails")),
        industry=_national_industry(raw),
        industry_category=industry_category,
        industry_major=industry_major,
        area=area,
        establish_date=_establish_date(raw),
        listing_board=raw.get("ShortStockExchange") or raw.get("ListSection") or "",
        url=_build_company_url(raw),
    )


def _normalize_additional(raw: dict[str, Any], *, event_type: str, chain_code: str) -> FinancingCompany:
    """定向增发：增发日期、企业名称、项目名称、募资金额、行业门类/大类。"""
    area = raw.get("Area") or {}
    industry_category, industry_major = _qcc_industry(raw)
    product_name = _strip_html(raw.get("ProductName") or "")
    company_name = raw.get("CompanyName") or ""

    return _base_company(
        raw,
        event_type=event_type,
        chain_code=chain_code,
        project_name=product_name or company_name,
        company_name=company_name,
        project_brief=raw.get("Slogan") or "",
        financing_round="定向增发",
        financing_date=_event_date_ms(raw, "FinanceDate"),
        financing_money=raw.get("Amount") or "",
        industry=_national_industry(raw),
        industry_category=industry_category,
        industry_major=industry_major,
        area=area,
        establish_date=_establish_date(raw),
        url=_build_company_url(raw),
    )


def _normalize_merger(raw: dict[str, Any], *, event_type: str, chain_code: str) -> FinancingCompany:
    """并购/股权转让：交易日期、项目名称、购买方、出让方、交易金额、行业。"""
    area = raw.get("Area") or {}
    industry_category, industry_major = _qcc_industry(raw)
    product_name = _strip_html(raw.get("ProductName") or "")
    company_name = raw.get("CompanyName") or ""

    return _base_company(
        raw,
        event_type=event_type,
        chain_code=chain_code,
        project_name=product_name or company_name,
        company_name=company_name,
        project_brief=raw.get("Slogan") or "",
        financing_round=raw.get("Round") or "",
        financing_date=_event_date_ms(raw, "FinanceDate"),
        financing_money=raw.get("Amount") or "",
        industry=_national_industry(raw),
        industry_category=industry_category,
        industry_major=industry_major,
        area=area,
        establish_date=_establish_date(raw),
        buyer=_format_participants(raw.get("ParticipantDetails")),
        seller=_format_participants(raw.get("TransferSubjects")),
        trade_equity_ratio=raw.get("Rate") or "",
        url=_build_product_url(raw),
    )


def _normalize_industrial_chain(raw: dict[str, Any], *, event_type: str, chain_code: str) -> FinancingCompany:
    """产业链融资：融资日期、项目名称、行业大类、城市、成立日期、企业名称。"""
    area = raw.get("Area") or {}
    industry_category, industry_major = _qcc_industry(raw)
    product_name = _strip_html(raw.get("ProductName") or "")
    company_name = raw.get("CompanyName") or ""

    return _base_company(
        raw,
        event_type=event_type,
        chain_code=chain_code,
        project_name=product_name or company_name,
        company_name=company_name,
        project_brief=raw.get("Slogan") or "",
        financing_round=raw.get("Round") or "",
        financing_date=_event_date_ms(raw, "FinanceDate"),
        financing_money=raw.get("Amount") or "",
        investor=_format_participants(raw.get("ParticipantDetails")),
        industry=_national_industry(raw),
        industry_category=industry_category,
        industry_major=industry_major,
        area=area,
        establish_date=_establish_date(raw),
        url=_build_product_url(raw),
    )


def _normalize_exit(raw: dict[str, Any], *, event_type: str, chain_code: str) -> FinancingCompany:
    """退出事件：退出日期、退出方、退出方式、退出项目、回报倍数、IRR、退出股权。"""
    area = raw.get("Area") or {}
    brand = raw.get("BrandName") or ""
    comp_name = raw.get("CompName") or brand
    holder = raw.get("HolderName") or raw.get("InstitutionName") or ""

    return _base_company(
        raw,
        event_type=event_type,
        chain_code=chain_code,
        project_name=brand or comp_name,
        company_name=comp_name,
        project_brief=raw.get("Slogan") or "",
        financing_round=raw.get("ExitType") or "退出",
        financing_date=_event_date_ms(raw, "ExitDate"),
        financing_money=raw.get("AmountStandard") or "",
        investor=holder,
        area=area,
        exit_type=raw.get("ExitType") or "",
        holder_name=holder,
        return_multiple=raw.get("MOCNew") or "",
        irr=raw.get("IRRNew") or "",
        exit_equity_ratio=(
            raw.get("SumOfBeforeSharesRatioNew") or raw.get("SumOfBeforeSharesRatio") or ""
        ),
        url=_build_exit_url(raw),
        com_id=raw.get("CompKeyNo") or raw.get("HolderKeyno") or "",
        company_keyno=raw.get("CompKeyNo") or "",
        product_id=raw.get("BrandId") or "",
    )


def _base_company(
    raw: dict[str, Any],
    *,
    event_type: str,
    chain_code: str,
    project_name: str,
    company_name: str = "",
    project_brief: str = "",
    financing_round: str = "",
    financing_date: int = 0,
    financing_money: str = "",
    investor: str = "",
    industry: str = "",
    industry_category: str = "",
    industry_major: str = "",
    area: dict[str, Any] | None = None,
    country: str = "",
    establish_date: str = "",
    listing_board: str = "",
    buyer: str = "",
    seller: str = "",
    trade_equity_ratio: str = "",
    exit_type: str = "",
    holder_name: str = "",
    return_multiple: str = "",
    irr: str = "",
    exit_equity_ratio: str = "",
    url: str = "",
    com_id: str = "",
    company_keyno: str = "",
    product_id: str = "",
) -> FinancingCompany:
    """组装通用 FinancingCompany，填充地区与企查查公共字段。"""
    area = area or {}
    province = area.get("ProvinceName") or ""
    city = area.get("CityName") or ""
    county = area.get("CountyName") or ""
    external_id = str(raw.get("Id") or "")
    keyno = company_keyno or raw.get("CompanyKeyno") or raw.get("CompKeyNo") or ""

    return FinancingCompany(
        project_id=_external_id_to_int(external_id),
        project_name=project_name,
        project_brief=project_brief,
        industry_list=[item for item in [industry, industry_major, industry_category] if item],
        financing_round=financing_round,
        financing_date=financing_date,
        financing_money=financing_money,
        investor=investor,
        url=url,
        source=DATA_SOURCE_QCC,
        com_id=com_id or keyno,
        full_name=company_name or project_name,
        reg_location=_format_area(area),
        province=province,
        city=city,
        county=county,
        country=country or ("中国" if province or city else ""),
        event_type=event_type,
        external_id=external_id,
        company_keyno=keyno,
        industry_category=industry_category,
        industry_major=industry_major,
        national_industry=industry,
        listing_board=listing_board,
        establish_date=establish_date,
        buyer=buyer,
        seller=seller,
        trade_equity_ratio=trade_equity_ratio,
        exit_type=exit_type,
        holder_name=holder_name,
        return_multiple=return_multiple,
        irr=irr,
        exit_equity_ratio=exit_equity_ratio,
        chain_code=chain_code,
        product_id=product_id or raw.get("ProductId") or "",
    )


def _qcc_industry(raw: dict[str, Any]) -> tuple[str, str]:
    """解析企查查行业门类 (An) 与行业大类 (Bn)。"""
    data = raw.get("QccIndustry")
    if isinstance(data, dict):
        return str(data.get("An") or ""), str(data.get("Bn") or "")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return str(first.get("An") or ""), str(first.get("Bn") or "")
    return "", ""


def _national_industry(raw: dict[str, Any]) -> str:
    """国标行业字段。"""
    industry = raw.get("Industry")
    if isinstance(industry, str):
        return industry.strip()
    if isinstance(industry, dict):
        parts = [industry.get("Industry"), industry.get("SubIndustry")]
        return "、".join(str(item) for item in parts if item)
    tags = list(raw.get("IndustryTags") or [])
    return "、".join(_dedupe(str(item) for item in tags if item))


def _format_participants(items: Any) -> str:
    """格式化投资方/购买方/出让方列表。"""
    if not items:
        return ""
    names: list[str] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                name = item.get("Name") or item.get("InstitutionName") or item.get("CompanyName")
                if name:
                    names.append(str(name))
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())
    elif isinstance(items, str):
        return items.strip()
    return "、".join(_dedupe(names))


def _establish_date(raw: dict[str, Any]) -> str:
    """成立日期转 YYYY-MM-DD。"""
    value = raw.get("EstablishDate")
    if not value:
        return ""
    if isinstance(value, str) and not value.isdigit():
        return value[:10]
    ms = _to_financing_ms(int(value))
    return format_financing_date(ms) if ms else ""


def _event_date_ms(raw: dict[str, Any], *keys: str) -> int:
    """读取事件日期字段并转为毫秒时间戳。"""
    for key in keys:
        value = raw.get(key)
        if value:
            return _to_financing_ms(int(value))
    return 0


def _build_company_url(raw: dict[str, Any]) -> str:
    keyno = raw.get("CompanyKeyno") or raw.get("CompKeyNo") or ""
    if keyno:
        return f"https://www.qcc.com/firm/{keyno}.html"
    product_id = raw.get("ProductId") or ""
    if product_id:
        return f"https://www.qcc.com/product/{product_id}.html"
    return ""


def _build_product_url(raw: dict[str, Any]) -> str:
    product_id = raw.get("ProductId") or ""
    if product_id:
        return f"https://www.qcc.com/product/{product_id}.html"
    return _build_company_url(raw)


def _build_exit_url(raw: dict[str, Any]) -> str:
    keyno = raw.get("CompKeyNo") or ""
    if keyno:
        return f"https://www.qcc.com/firm/{keyno}.html"
    brand_id = raw.get("BrandId") or ""
    if brand_id:
        return f"https://www.qcc.com/product/{brand_id}.html"
    return ""


def _format_area(area: dict[str, Any]) -> str:
    parts = [area.get("ProvinceName"), area.get("CityName"), area.get("CountyName")]
    return "".join(part for part in parts if part)


def _strip_html(value: str) -> str:
    return value.replace("<em>", "").replace("</em>", "")


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _external_id_to_int(external_id: str) -> int:
    if not external_id:
        return 0
    return abs(hash(external_id)) % (2**31 - 1)


def _since_ts(days: int) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return int(since.timestamp() * 1000)


def _to_financing_ms(ts: int) -> int:
    if not ts:
        return 0
    if ts < 10_000_000_000:
        return ts * 1000
    return ts


def _total_pages(paging: dict[str, Any], page_size: int) -> int:
    total = int(paging.get("TotalRecords") or 0)
    size = int(paging.get("PageSize") or page_size) or page_size
    if total <= 0:
        return int(paging.get("PageIndex") or 1)
    return max(1, (total + size - 1) // size)


def dedupe_name(company: FinancingCompany) -> str:
    """去重键中的企业名：增发/产业链优先工商全称。"""
    if company.event_type in (EVENT_ADDITIONAL, EVENT_INDUSTRIAL_CHAIN) and company.full_name:
        return company.full_name
    return company.project_name
