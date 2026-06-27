from __future__ import annotations

import json
from datetime import datetime, timezone

SCHEMA_VERSION = 3

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
    UNIQUE (project_name, financing_date)
);

CREATE INDEX IF NOT EXISTS idx_financing_event_project ON financing_event(project_id);
CREATE INDEX IF NOT EXISTS idx_financing_event_name_date ON financing_event(project_name, financing_date);

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
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dumps_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False)
