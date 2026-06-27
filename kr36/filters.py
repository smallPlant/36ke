from __future__ import annotations

from kr36.config import SHAREHOLDER_EXCLUDE_KEYWORDS
from kr36.region import is_south_china_address, is_south_china_region

__all__ = ["is_south_china_address", "is_south_china_region", "should_exclude_shareholder"]


def should_exclude_shareholder(name: str) -> bool:
    """过滤含咨询/投资/管理/基金/股权等关键词的股东。"""
    if not name:
        return True
    return any(keyword in name for keyword in SHAREHOLDER_EXCLUDE_KEYWORDS)
