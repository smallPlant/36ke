from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import cpca

from kr36.config import SOUTH_CHINA_ADCODE_PREFIXES, SOUTH_CHINA_PROVINCES


@dataclass(frozen=True)
class ParsedAddress:
    province: str
    city: str
    district: str
    adcode: str
    detail: str


@lru_cache(maxsize=4096)
def parse_address(address: str) -> ParsedAddress | None:
    """使用 cpca 标准区划库解析中国地址。"""
    text = (address or "").strip()
    if not text:
        return None

    row = cpca.transform([text]).iloc[0]
    province = _clean(row.get("省"))
    city = _clean(row.get("市"))
    district = _clean(row.get("区"))
    adcode = _clean(row.get("adcode"))
    detail = _clean(row.get("地址"))

    if not any([province, city, district, adcode]):
        return None

    return ParsedAddress(
        province=province,
        city=city,
        district=district,
        adcode=adcode,
        detail=detail,
    )


def is_south_china_address(address: str) -> bool:
    """判断注册地址是否属于华南（广东、广西、福建、海南）。"""
    parsed = parse_address(address)
    if not parsed:
        return False

    if parsed.province and parsed.province in SOUTH_CHINA_PROVINCES:
        return True

    if parsed.adcode:
        prefix = parsed.adcode[:2]
        return prefix in SOUTH_CHINA_ADCODE_PREFIXES

    return False


_PROVINCE_ALIASES: dict[str, str] = {
    "广东": "广东省",
    "广西": "广西壮族自治区",
    "福建": "福建省",
    "海南": "海南省",
}


def is_south_china_province(province: str) -> bool:
    """根据省份字段判断是否属于华南。"""
    text = (province or "").strip()
    if not text:
        return False
    if text in SOUTH_CHINA_PROVINCES:
        return True
    return _PROVINCE_ALIASES.get(text, text) in SOUTH_CHINA_PROVINCES


def is_south_china_region(*, reg_location: str = "", province: str = "") -> bool:
    """综合注册地址与省份字段判断是否在华南。"""
    if is_south_china_address(reg_location):
        return True
    return is_south_china_province(province)


def _clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text
