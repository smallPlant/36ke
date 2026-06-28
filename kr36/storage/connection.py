"""SQLite 连接管理、建表与增量迁移。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kr36.sources.events.iyiou.investors import format_iyiou_investors
from kr36.storage.schema import DDL, SCHEMA_VERSION


def _migrate_financing_event(conn: sqlite3.Connection) -> None:
    """为 financing_event 添加 (project_name, financing_date) 唯一约束，合并历史重复行。"""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='financing_event'"
    ).fetchone()
    if not row or not row[0]:
        return
    if "UNIQUE (project_name, financing_date)" in row[0]:
        return

    conn.execute("PRAGMA foreign_keys = OFF")

    groups = conn.execute(
        """
        SELECT project_name, COALESCE(financing_date, '') AS fd, MIN(id) AS keep_id
        FROM financing_event
        GROUP BY project_name, COALESCE(financing_date, '')
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for group in groups:
        dupes = conn.execute(
            """
            SELECT id FROM financing_event
            WHERE project_name = ? AND COALESCE(financing_date, '') = ?
            """,
            (group["project_name"], group["fd"]),
        ).fetchall()
        keep_id = int(group["keep_id"])
        for item in dupes:
            dup_id = int(item["id"])
            if dup_id == keep_id:
                continue
            related_rows = conn.execute(
                "SELECT id, related_company_id, relation_type FROM related_company WHERE financing_event_id = ?",
                (dup_id,),
            ).fetchall()
            for rc in related_rows:
                conflict = conn.execute(
                    """
                    SELECT 1 FROM related_company
                    WHERE financing_event_id = ?
                      AND related_company_id = ?
                      AND relation_type = ?
                    """,
                    (keep_id, rc["related_company_id"], rc["relation_type"]),
                ).fetchone()
                if conflict:
                    conn.execute("DELETE FROM related_company WHERE id = ?", (rc["id"],))
                else:
                    conn.execute(
                        "UPDATE related_company SET financing_event_id = ? WHERE id = ?",
                        (keep_id, rc["id"]),
                    )
            conn.execute("DELETE FROM financing_event WHERE id = ?", (dup_id,))

    conn.executescript(
        """
        CREATE TABLE financing_event_new (
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

        INSERT INTO financing_event_new (
            id, batch_id, source, project_id, company_id, project_name,
            project_brief, industry, financing_date, financing_round,
            financing_amount, investor, source_url
        )
        SELECT
            id, batch_id, source, project_id, company_id, project_name,
            project_brief, industry, COALESCE(financing_date, ''), financing_round,
            financing_amount, investor, source_url
        FROM financing_event;

        DROP TABLE financing_event;
        ALTER TABLE financing_event_new RENAME TO financing_event;

        CREATE INDEX IF NOT EXISTS idx_financing_event_project ON financing_event(project_id);
        CREATE INDEX IF NOT EXISTS idx_financing_event_name_date ON financing_event(project_name, financing_date);
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _clean_iyiou_investors(conn: sqlite3.Connection) -> None:
    """清洗历史亿欧融资事件中的 investor JSON 字符串。"""
    rows = conn.execute(
        """
        SELECT id, investor FROM financing_event
        WHERE source = 'iyiou' AND investor LIKE '[%'
        """
    ).fetchall()
    if not rows:
        return
    try:
        for row in rows:
            cleaned = format_iyiou_investors(row["investor"])
            if cleaned != row["investor"]:
                conn.execute(
                    "UPDATE financing_event SET investor = ? WHERE id = ?",
                    (cleaned, row["id"]),
                )
        conn.commit()
    except sqlite3.OperationalError as exc:
        conn.rollback()
        if "locked" in str(exc).lower():
            print("⚠️  数据库被占用，跳过历史 investor 清洗（请关闭 DB 查看工具后重试）")
            return
        raise


def _migrate_company(conn: sqlite3.Connection) -> None:
    """移除 raw_json / updated_at，详情字段已展开到各列。"""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(company)").fetchall()}
    if "raw_json" not in columns and "updated_at" not in columns:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE company_new (
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

        INSERT INTO company_new (
            id, source, project_id, search_keyword, brief_name, full_name,
            english_name, legal_person, establish_date, reg_location,
            province, city, country, website, is_south_china,
            fetched_at, created_at
        )
        SELECT
            id, source, project_id, search_keyword, brief_name, full_name,
            english_name, legal_person, establish_date, reg_location,
            province, city, country, website, is_south_china,
            fetched_at, created_at
        FROM company;

        DROP TABLE company;
        ALTER TABLE company_new RENAME TO company;

        CREATE INDEX IF NOT EXISTS idx_company_fetched_at ON company(fetched_at);
        CREATE INDEX IF NOT EXISTS idx_company_project_id ON company(project_id);
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _add_financing_event_qcc_columns(conn: sqlite3.Connection) -> None:
    """在原 financing_event 表上增量追加企查查扩展列（不重建表）。"""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(financing_event)").fetchall()}
    if not columns:
        return

    additions = [
        ("event_type", "TEXT NOT NULL DEFAULT 'financing'"),
        ("external_id", "TEXT"),
        ("company_full_name", "TEXT"),
        ("company_keyno", "TEXT"),
        ("province", "TEXT"),
        ("city", "TEXT"),
        ("valuation", "TEXT"),
        ("stock_code", "TEXT"),
        ("exit_type", "TEXT"),
        ("holder_name", "TEXT"),
        ("event_summary", "TEXT"),
        ("news_title", "TEXT"),
        ("news_url", "TEXT"),
        ("chain_code", "TEXT"),
    ]
    for name, col_type in additions:
        if name not in columns:
            conn.execute(f"ALTER TABLE financing_event ADD COLUMN {name} {col_type}")
    conn.commit()


def _financing_event_table_sql(conn: sqlite3.Connection) -> str:
    """读取 financing_event 建表 SQL。"""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='financing_event'"
    ).fetchone()
    return row[0] if row and row[0] else ""


def _migrate_financing_event_v5(conn: sqlite3.Connection) -> None:
    """修正唯一约束：保留原字段，移除 dedupe_key，改为 (source, project_name, financing_date, event_type)。"""
    table_sql = _financing_event_table_sql(conn)
    if not table_sql:
        return

    target_unique = "UNIQUE (source, project_name, financing_date, event_type)"
    columns = {row[1] for row in conn.execute("PRAGMA table_info(financing_event)").fetchall()}
    if target_unique in table_sql and "dedupe_key" not in columns:
        return

    _add_financing_event_qcc_columns(conn)

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        CREATE TABLE financing_event_new (
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
            valuation       TEXT,
            stock_code      TEXT,
            exit_type       TEXT,
            holder_name     TEXT,
            event_summary   TEXT,
            news_title      TEXT,
            news_url        TEXT,
            chain_code      TEXT,
            UNIQUE (source, project_name, financing_date, event_type)
        );

        INSERT INTO financing_event_new (
            id, batch_id, source, project_id, company_id, project_name,
            project_brief, industry, financing_date, financing_round,
            financing_amount, investor, source_url,
            event_type, external_id, company_full_name, company_keyno,
            province, city, valuation, stock_code, exit_type,
            holder_name, event_summary, news_title, news_url, chain_code
        )
        SELECT
            id,
            batch_id,
            source,
            project_id,
            company_id,
            project_name,
            project_brief,
            industry,
            COALESCE(financing_date, ''),
            financing_round,
            financing_amount,
            investor,
            source_url,
            COALESCE(event_type, 'financing'),
            external_id,
            company_full_name,
            company_keyno,
            province,
            city,
            valuation,
            stock_code,
            exit_type,
            holder_name,
            event_summary,
            news_title,
            news_url,
            chain_code
        FROM financing_event;

        DROP TABLE financing_event;
        ALTER TABLE financing_event_new RENAME TO financing_event;

        CREATE INDEX IF NOT EXISTS idx_financing_event_project ON financing_event(project_id);
        CREATE INDEX IF NOT EXISTS idx_financing_event_name_date ON financing_event(project_name, financing_date);
        CREATE INDEX IF NOT EXISTS idx_financing_event_type_date ON financing_event(event_type, financing_date);
        CREATE INDEX IF NOT EXISTS idx_financing_event_external ON financing_event(source, external_id);
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _migrate_financing_event_v6(conn: sqlite3.Connection) -> None:
    """唯一约束改为 (project_name, financing_date, event_type)。"""
    table_sql = _financing_event_table_sql(conn)
    if not table_sql:
        return

    target_unique = "UNIQUE (project_name, financing_date, event_type)"
    if target_unique in table_sql:
        return

    conn.execute("PRAGMA foreign_keys = OFF")

    groups = conn.execute(
        """
        SELECT
            project_name,
            COALESCE(financing_date, '') AS fd,
            COALESCE(event_type, 'financing') AS et,
            MIN(id) AS keep_id
        FROM financing_event
        GROUP BY project_name, COALESCE(financing_date, ''), COALESCE(event_type, 'financing')
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for group in groups:
        dupes = conn.execute(
            """
            SELECT id FROM financing_event
            WHERE project_name = ?
              AND COALESCE(financing_date, '') = ?
              AND COALESCE(event_type, 'financing') = ?
            """,
            (group["project_name"], group["fd"], group["et"]),
        ).fetchall()
        keep_id = int(group["keep_id"])
        for item in dupes:
            dup_id = int(item["id"])
            if dup_id == keep_id:
                continue
            related_rows = conn.execute(
                """
                SELECT id, related_company_id, relation_type
                FROM related_company
                WHERE financing_event_id = ?
                """,
                (dup_id,),
            ).fetchall()
            for rc in related_rows:
                conflict = conn.execute(
                    """
                    SELECT 1 FROM related_company
                    WHERE financing_event_id = ?
                      AND related_company_id = ?
                      AND relation_type = ?
                    """,
                    (keep_id, rc["related_company_id"], rc["relation_type"]),
                ).fetchone()
                if conflict:
                    conn.execute("DELETE FROM related_company WHERE id = ?", (rc["id"],))
                else:
                    conn.execute(
                        "UPDATE related_company SET financing_event_id = ? WHERE id = ?",
                        (keep_id, rc["id"]),
                    )
            conn.execute("DELETE FROM financing_event WHERE id = ?", (dup_id,))

    conn.executescript(
        """
        CREATE TABLE financing_event_new (
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
            valuation       TEXT,
            stock_code      TEXT,
            exit_type       TEXT,
            holder_name     TEXT,
            event_summary   TEXT,
            news_title      TEXT,
            news_url        TEXT,
            chain_code      TEXT,
            UNIQUE (project_name, financing_date, event_type)
        );

        INSERT INTO financing_event_new (
            id, batch_id, source, project_id, company_id, project_name,
            project_brief, industry, financing_date, financing_round,
            financing_amount, investor, source_url,
            event_type, external_id, company_full_name, company_keyno,
            province, city, valuation, stock_code, exit_type,
            holder_name, event_summary, news_title, news_url, chain_code
        )
        SELECT
            id,
            batch_id,
            source,
            project_id,
            company_id,
            project_name,
            project_brief,
            industry,
            COALESCE(financing_date, ''),
            financing_round,
            financing_amount,
            investor,
            source_url,
            COALESCE(event_type, 'financing'),
            external_id,
            company_full_name,
            company_keyno,
            province,
            city,
            valuation,
            stock_code,
            exit_type,
            holder_name,
            event_summary,
            news_title,
            news_url,
            chain_code
        FROM financing_event;

        DROP TABLE financing_event;
        ALTER TABLE financing_event_new RENAME TO financing_event;

        CREATE INDEX IF NOT EXISTS idx_financing_event_project ON financing_event(project_id);
        CREATE INDEX IF NOT EXISTS idx_financing_event_name_date ON financing_event(project_name, financing_date);
        CREATE INDEX IF NOT EXISTS idx_financing_event_type_date ON financing_event(event_type, financing_date);
        CREATE INDEX IF NOT EXISTS idx_financing_event_external ON financing_event(source, external_id);
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _migrate_financing_event_v7(conn: sqlite3.Connection) -> None:
    """追加企查查页面字段：行业门类/大类、上市板块、退出回报、买卖方等。"""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(financing_event)").fetchall()}
    if not columns:
        return

    additions = [
        ("county", "TEXT"),
        ("country", "TEXT"),
        ("industry_category", "TEXT"),
        ("industry_major", "TEXT"),
        ("national_industry", "TEXT"),
        ("listing_board", "TEXT"),
        ("establish_date", "TEXT"),
        ("buyer", "TEXT"),
        ("seller", "TEXT"),
        ("trade_equity_ratio", "TEXT"),
        ("return_multiple", "TEXT"),
        ("irr", "TEXT"),
        ("exit_equity_ratio", "TEXT"),
    ]
    for name, col_type in additions:
        if name not in columns:
            conn.execute(f"ALTER TABLE financing_event ADD COLUMN {name} {col_type}")
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """按序执行所有增量迁移（列追加、表重建、数据清洗）。"""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(company)").fetchall()}
    if "country" not in columns:
        conn.execute("ALTER TABLE company ADD COLUMN country TEXT")
    if "website" not in columns:
        conn.execute("ALTER TABLE company ADD COLUMN website TEXT")
    conn.commit()
    _migrate_financing_event(conn)
    _migrate_company(conn)
    _add_financing_event_qcc_columns(conn)
    _migrate_financing_event_v5(conn)
    _migrate_financing_event_v6(conn)
    _migrate_financing_event_v7(conn)
    _clean_iyiou_investors(conn)


def connect(db_path: str | Path) -> sqlite3.Connection:
    """打开数据库连接，启用外键约束与 30 秒忙等待。"""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _ensure_financing_event_indexes(conn: sqlite3.Connection) -> None:
    """确保 financing_event 索引完整（兼容旧库升级后缺索引的情况）。"""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(financing_event)").fetchall()}
    if not columns:
        return
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_financing_event_project ON financing_event(project_id);
        CREATE INDEX IF NOT EXISTS idx_financing_event_name_date ON financing_event(project_name, financing_date);
        CREATE INDEX IF NOT EXISTS idx_financing_event_type_date ON financing_event(event_type, financing_date);
        CREATE INDEX IF NOT EXISTS idx_financing_event_external ON financing_event(source, external_id);
        """
    )
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    """建表、更新 schema_version 并运行增量迁移。"""
    conn.executescript(DDL)
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
    elif int(row[0]) < SCHEMA_VERSION:
        conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
        conn.commit()
    _migrate(conn)
    _ensure_financing_event_indexes(conn)
