"""亿欧企业详情页解析：从 SSR __INITIAL_STATE__ 提取工商信息。"""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page

from kr36.core.models import FinancingCompany, ProjectDetail
from kr36.domain.filters import is_south_china_region
from kr36.domain.region import parse_address

PROFILE_URL = "https://data.iyiou.com/company/details/{com_id}/profile"
REGINFO_URL = "https://data.iyiou.com/company/details/{com_id}/reginfo"


def parse_com_id_from_url(url: str) -> str:
    """从亿欧企业详情 URL 提取 com_id。"""
    match = re.search(r"/company/details/([^/]+)/", url or "")
    return match.group(1) if match else ""


def fetch_company_detail(
    page: Page,
    *,
    com_id: str,
    project_id: int,
    brief_name: str,
    wait_ms: int = 1500,
) -> ProjectDetail | None:
    """访问亿欧企业详情页（SSR），补充工商与注册地址等信息。"""
    if not com_id:
        return None

    page.goto(PROFILE_URL.format(com_id=com_id), wait_until="domcontentloaded", timeout=45_000)
    if wait_ms:
        page.wait_for_timeout(wait_ms)

    module = page.evaluate("() => window.__INITIAL_STATE__?.companyDetailModule")
    if not module:
        return None

    detail = _build_detail(project_id, brief_name, module)

    reg_info = _extract_reg_info(module)
    if not reg_info.get("regLocation"):
        page.goto(REGINFO_URL.format(com_id=com_id), wait_until="domcontentloaded", timeout=45_000)
        if wait_ms:
            page.wait_for_timeout(wait_ms)
        reg_module = page.evaluate("() => window.__INITIAL_STATE__?.companyDetailModule")
        if reg_module:
            reg_info = _extract_reg_info(reg_module) or reg_info
            detail = _merge_reg_info(detail, reg_info)

    if reg_info:
        detail = _merge_reg_info(detail, reg_info)

    if not detail.reg_location and not detail.company_name:
        return None
    return detail


def _extract_reg_info(module: dict[str, Any]) -> dict[str, Any]:
    """从 companyDetailModule 提取工商注册信息。"""
    reginfo = module.get("reginfoData") or {}
    reg_info = reginfo.get("regInfo") or {}
    return reg_info if isinstance(reg_info, dict) else {}


def _build_detail(project_id: int, brief_name: str, module: dict[str, Any]) -> ProjectDetail:
    """从 profileData 构建 ProjectDetail。"""
    profile = module.get("profileData") or {}
    basic = profile.get("basicInfo") or {}
    contact = _first_contact(profile.get("companyContact") or basic.get("companyContactHead"))

    full_name = str(basic.get("fullName") or basic.get("regFullName") or "").strip()
    reg_location = str(contact.get("address") or "").strip()
    province = str(contact.get("provinceStr") or "").strip()
    city = str(contact.get("cityStr") or "").strip()
    country = str(contact.get("countryStr") or basic.get("countryStr") or "中国").strip() or "中国"

    parsed = parse_address(reg_location)
    if parsed:
        province = province or parsed.province
        city = city or parsed.city

    establish_date = str(basic.get("establishTime") or "").strip()
    website = str(basic.get("website") or "").strip()

    return ProjectDetail(
        project_id=project_id,
        name=brief_name or str(basic.get("briefName") or ""),
        company_name=full_name or brief_name,
        reg_location=reg_location,
        establish_date=establish_date,
        province=province,
        city=city,
        country=country,
        website=website,
        is_south_china=is_south_china_region(reg_location=reg_location, province=province),
    )


def _merge_reg_info(detail: ProjectDetail, reg_info: dict[str, Any]) -> ProjectDetail:
    """将工商注册信息合并到已有 ProjectDetail。"""
    reg_location = str(reg_info.get("regLocation") or detail.reg_location or "").strip()
    company_name = str(reg_info.get("regFullName") or detail.company_name or "").strip()
    legal_person = str(reg_info.get("legalRepresent") or detail.legal_person or "").strip()
    establish_date = str(reg_info.get("regTime") or reg_info.get("approveTime") or detail.establish_date or "").strip()

    province = detail.province
    city = detail.city
    parsed = parse_address(reg_location)
    if parsed:
        province = province or parsed.province
        city = city or parsed.city

    detail.reg_location = reg_location or detail.reg_location
    detail.company_name = company_name or detail.company_name
    detail.legal_person = legal_person or detail.legal_person
    detail.establish_date = establish_date or detail.establish_date
    detail.province = province
    detail.city = city
    detail.is_south_china = is_south_china_region(reg_location=detail.reg_location, province=detail.province)
    return detail


def _first_contact(contacts: list[Any]) -> dict[str, Any]:
    """取联系信息列表的第一条记录。"""
    if not contacts:
        return {}
    first = contacts[0]
    return first if isinstance(first, dict) else {}


def apply_detail_to_company(company: FinancingCompany, detail: ProjectDetail) -> None:
    """将详情字段回填到融资列表对象，便于导出与入库。"""
    if detail.company_name:
        company.full_name = detail.company_name
    if detail.reg_location:
        company.reg_location = detail.reg_location
    if detail.province:
        company.province = detail.province
    if detail.country:
        company.country = detail.country
