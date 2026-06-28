"""SQLite 表结构定义与 schema 版本管理。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

SCHEMA_VERSION = 7

# 表说明：
#   crawl_batch      — 每次 pipeline 运行的批次记录与缓存统计
#   company          — 公司工商详情缓存（36氪 / 亿欧）
#   shareholder      — 公司股东（仅 36氪有数据）
#   financing_event  — 融资/创投事件，原字段不变；企查查扩展列追加在末尾
#   related_company  — 融资公司与华南关联公司的多对多关系

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS crawl_batch (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL DEFAULT '36kr',
    params_json TEXT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL DEFAULT 'running',
    company_cache_hits   INTEGER NOT NULL DEFAULT 0,
    company_cache_misses INTEGER NOT NULL DEFAULT 0,
    company_cache_expired INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS company (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL DEFAULT '36kr',
    project_id      INTEGER,
    search_keyword  TEXT,
    brief_name      TEXT,
    full_name       TEXT NOT NULL DEFAULT '',
    english_name    TEXT,
    legal_person    TEXT,
    establish_date  TEXT,
    reg_location    TEXT,
    province        TEXT,
    city            TEXT,
    country         TEXT,
    website         TEXT,
    is_south_china  INTEGER NOT NULL DEFAULT 0,
    fetched_at      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    UNIQUE (source, project_id),
    UNIQUE (source, search_keyword)
);

CREATE INDEX IF NOT EXISTS idx_company_fetched_at ON company(fetched_at);
CREATE INDEX IF NOT EXISTS idx_company_project_id ON company(project_id);

CREATE TABLE IF NOT EXISTS shareholder (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    share_ratio     TEXT,
    subscribed_amount TEXT,
    subscribed_date TEXT,
    UNIQUE (company_id, name)
);

CREATE TABLE IF NOT EXISTS financing_event (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id        INTEGER NOT NULL REFERENCES crawl_batch(id),
    source          TEXT NOT NULL DEFAULT '36kr',
    project_id      INTEGER NOT NULL,
    company_id      INTEGER REFERENCES company(id),
    project_name    TEXT NOT NULL,
    project_brief   TEXT,
    industry        TEXT,
    financing_date  TEXT NOT NULL DEFAULT '',
    financing_round TEXT,
    financing_amount TEXT,
    investor        TEXT,
    source_url      TEXT,
    event_type      TEXT NOT NULL DEFAULT 'financing',
    external_id     TEXT,
    company_full_name TEXT,
    company_keyno   TEXT,
    province        TEXT,
    city            TEXT,
    county          TEXT,
    country         TEXT,
    industry_category TEXT,
    industry_major  TEXT,
    national_industry TEXT,
    listing_board   TEXT,
    establish_date  TEXT,
    buyer           TEXT,
    seller          TEXT,
    trade_equity_ratio TEXT,
    exit_type       TEXT,
    holder_name     TEXT,
    return_multiple TEXT,
    irr             TEXT,
    exit_equity_ratio TEXT,
    UNIQUE (project_name, financing_date, event_type)
);

CREATE INDEX IF NOT EXISTS idx_financing_event_project ON financing_event(project_id);
CREATE INDEX IF NOT EXISTS idx_financing_event_name_date ON financing_event(project_name, financing_date);
CREATE INDEX IF NOT EXISTS idx_financing_event_type_date ON financing_event(event_type, financing_date);
CREATE INDEX IF NOT EXISTS idx_financing_event_external ON financing_event(source, external_id);

CREATE TABLE IF NOT EXISTS related_company (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id            INTEGER NOT NULL REFERENCES crawl_batch(id),
    financing_event_id  INTEGER NOT NULL REFERENCES financing_event(id),
    related_company_id  INTEGER NOT NULL REFERENCES company(id),
    relation_type       TEXT NOT NULL,
    related_name        TEXT NOT NULL,
    UNIQUE (financing_event_id, related_company_id, relation_type)
);
"""


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 字符串。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dumps_json(data: object) -> str:
    """将对象序列化为 JSON 字符串（保留中文）。"""
    return json.dumps(data, ensure_ascii=False)
