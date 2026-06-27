from __future__ import annotations

import os
from dataclasses import dataclass, field

from kr36.paths import default_data_dir, default_db_path

# 华南地区省级行政区（民政部标准名称，cpca 解析结果）
SOUTH_CHINA_PROVINCES: frozenset[str] = frozenset({
    "广东省",
    "广西壮族自治区",
    "福建省",
    "海南省",
})

# 国标 adcode 省级前缀：44=广东, 45=广西, 35=福建, 46=海南
SOUTH_CHINA_ADCODE_PREFIXES: frozenset[str] = frozenset({"44", "45", "35", "46"})

# 股东名称过滤关键词
SHAREHOLDER_EXCLUDE_KEYWORDS: tuple[str, ...] = (
    "咨询",
    "投资",
    "管理",
    "基金",
    "股权",
)

DEFAULT_DELAY_MIN = 0.5
DEFAULT_DELAY_MAX = 3.0
DEFAULT_PAGE_SIZE = 20
DEFAULT_CACHE_TTL_DAYS = 30
DEFAULT_DB_PATH = str(default_db_path())

PITCHHUB_ORIGIN = "https://pitchhub.36kr.com"
GATEWAY_BASE = "https://gateway.36kr.com/api/pms"
DATA_SOURCE_36KR = "36kr"


@dataclass
class Settings:
    delay_min: float = DEFAULT_DELAY_MIN
    delay_max: float = DEFAULT_DELAY_MAX
    page_size: int = DEFAULT_PAGE_SIZE
    output_dir: str = field(default_factory=lambda: str(default_data_dir()))
    db_path: str = field(default_factory=lambda: os.getenv("KR36_DB_PATH", str(default_db_path())))
    cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS
    feishu_user_id: str = field(default_factory=lambda: os.getenv("FEISHU_USER_ID", ""))
    lark_cli_bin: str = field(default_factory=lambda: os.getenv("LARK_CLI_BIN", "lark-cli"))
