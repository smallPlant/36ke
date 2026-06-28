"""全局配置：请求参数、华南地区定义、数据源标识。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from kr36.core.paths import default_data_dir, default_db_path

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
DEFAULT_DAYS = 3
DEFAULT_SOURCE = "all"
DEFAULT_DB_PATH = str(default_db_path())


def default_push_feishu() -> bool:
    """是否默认推送飞书，可通过环境变量 KR36_PUSH_FEISHU=false 关闭。"""
    value = os.getenv("KR36_PUSH_FEISHU", "true").strip().lower()
    return value in ("1", "true", "yes", "on")

PITCHHUB_ORIGIN = "https://pitchhub.36kr.com"
GATEWAY_BASE = "https://gateway.36kr.com/api/pms"
DATA_SOURCE_36KR = "36kr"
DATA_SOURCE_QCC = "qcc"


@dataclass
class Settings:
    """Pipeline 运行时配置，部分字段可通过环境变量覆盖。"""

    # 请求随机间隔下限（秒）
    delay_min: float = DEFAULT_DELAY_MIN
    # 请求随机间隔上限（秒）
    delay_max: float = DEFAULT_DELAY_MAX
    # 每页拉取条数
    page_size: int = DEFAULT_PAGE_SIZE
    # Excel 输出目录
    output_dir: str = field(default_factory=lambda: str(default_data_dir()))
    # SQLite 数据库路径（可用 KR36_DB_PATH 覆盖）
    db_path: str = field(default_factory=lambda: os.getenv("KR36_DB_PATH", str(default_db_path())))
    # 公司详情缓存有效期（天）
    cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS
    # 飞书用户 open_id（可用 FEISHU_USER_ID 覆盖）
    feishu_user_id: str = field(default_factory=lambda: os.getenv("FEISHU_USER_ID", ""))
    # lark-cli 可执行文件路径（可用 LARK_CLI_BIN 覆盖）
    lark_cli_bin: str = field(default_factory=lambda: os.getenv("LARK_CLI_BIN", "lark-cli"))
    # 是否推送飞书（可用 KR36_PUSH_FEISHU 覆盖）
    push_feishu: bool = field(default_factory=default_push_feishu)
