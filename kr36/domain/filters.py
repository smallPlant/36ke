"""华南地区判定与股东名称过滤规则。"""

from __future__ import annotations

import re

from kr36.core.config import SHAREHOLDER_EXCLUDE_KEYWORDS
from kr36.domain.region import is_south_china_address, is_south_china_region

__all__ = [
    "is_natural_person_name",
    "is_south_china_address",
    "is_south_china_region",
    "should_exclude_shareholder",
]

# 含以下片段视为机构名称，不参与自然人判定
_CORPORATE_MARKERS: tuple[str, ...] = (
    "公司",
    "企业",
    "有限",
    "股份",
    "合伙",
    "集团",
    "银行",
    "证券",
    "基金",
    "投资",
    "控股",
    "实业",
    "科技",
    "管理",
    "中心",
    "事务所",
    "研究院",
    "协会",
    "委员会",
    "厂",
    "店",
    "行",
    "社",
    "部",
    "局",
    "院",
    "所",
    "咨询",
    "股权",
)

# 中国大陆自然人姓名多为 2～3 个汉字
_PERSON_NAME_PATTERN = re.compile(r"^[\u4e00-\u9fff]{2,3}$")


def is_natural_person_name(name: str) -> bool:
    """判断名称是否 Likely 为自然人（纯 2～3 个汉字且无机构特征词）。"""
    text = (name or "").strip()
    if not text:
        return False
    if any(marker in text for marker in _CORPORATE_MARKERS):
        return False
    return _PERSON_NAME_PATTERN.fullmatch(text) is not None


def should_exclude_shareholder(name: str) -> bool:
    """过滤不应拉取工商详情的股东：空名、含机构关键词、或 Likely 为自然人。"""
    text = (name or "").strip()
    if not text:
        return True
    if any(keyword in text for keyword in SHAREHOLDER_EXCLUDE_KEYWORDS):
        return True
    return is_natural_person_name(text)
