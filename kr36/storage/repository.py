"""SQLite 数据访问层：公司详情缓存、融资事件、关联公司与爬取批次。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from kr36.core.config import DATA_SOURCE_36KR
from kr36.core.models import FinancingCompany, ProjectDetail, RelatedCompanyRow, Shareholder
from kr36.sources.events.pitchhub.financing import format_financing_date
from kr36.sources.events.qcc.adapter import dedupe_name
from kr36.storage.schema import dumps_json, utc_now_iso


def _parse_iso(value: str) -> datetime:
    """解析 ISO 时间字符串，兼容末尾 Z 后缀。"""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class CompanyRepository:
    """公司详情与股东的读写，支持按 project_id / 搜索关键词查询及 TTL 缓存判断。"""

    def __init__(self, conn: sqlite3.Connection, *, cache_ttl_days: int = 30) -> None:
        """初始化仓储，conn 为已打开的 SQLite 连接。"""
        self.conn = conn
        self.cache_ttl_days = cache_ttl_days

    def is_fresh(self, fetched_at: str) -> bool:
        """判断缓存是否在 cache_ttl_days 有效期内。"""
        fetched = _parse_iso(fetched_at)
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        expires = fetched + timedelta(days=self.cache_ttl_days)
        return datetime.now(timezone.utc) < expires

    def get_by_project_id(self, project_id: int) -> sqlite3.Row | None:
        """按 36氪 project_id 查询公司缓存记录。"""
        return self.conn.execute(
            """
            SELECT * FROM company
            WHERE source = ? AND project_id = ?
            """,
            (DATA_SOURCE_36KR, project_id),
        ).fetchone()

    def get_by_search_keyword(self, keyword: str) -> sqlite3.Row | None:
        """按搜索关键词查询公司缓存记录。"""
        keyword = keyword.strip()
        if not keyword:
            return None
        return self.conn.execute(
            """
            SELECT * FROM company
            WHERE source = ? AND search_keyword = ?
            """,
            (DATA_SOURCE_36KR, keyword),
        ).fetchone()

    def get_shareholders(self, company_id: int) -> list[Shareholder]:
        """查询指定公司的股东列表。"""
        rows = self.conn.execute(
            """
            SELECT name, share_ratio, subscribed_amount, subscribed_date
            FROM shareholder
            WHERE company_id = ?
            ORDER BY id
            """,
            (company_id,),
        ).fetchall()
        return [
            Shareholder(
                name=row["name"],
                percent=row["share_ratio"] or "",
                amount=row["subscribed_amount"] or "",
                time=row["subscribed_date"] or "",
            )
            for row in rows
        ]

    def row_to_detail(self, row: sqlite3.Row) -> ProjectDetail:
        """将数据库行转换为 ProjectDetail 对象。"""
        return ProjectDetail(
            project_id=int(row["project_id"] or 0),
            name=row["brief_name"] or "",
            company_name=row["full_name"] or "",
            reg_location=row["reg_location"] or "",
            english_name=row["english_name"] or "",
            legal_person=row["legal_person"] or "",
            establish_date=row["establish_date"] or "",
            province=row["province"] or "",
            city=row["city"] or "",
            country=row["country"] or "中国",
            website=row["website"] or "",
            is_south_china=bool(row["is_south_china"]),
            shareholders=self.get_shareholders(int(row["id"])),
            search_keyword=row["search_keyword"] or "",
        )

    def save_detail(self, detail: ProjectDetail, *, search_keyword: str = "") -> int:
        """写入或更新公司详情；股东列表全量替换（先删后插）。"""
        now = utc_now_iso()
        keyword = (search_keyword or detail.search_keyword or "").strip() or None
        project_id = detail.project_id or None
        existing = None
        if project_id:
            existing = self.get_by_project_id(project_id)
        elif keyword:
            existing = self.get_by_search_keyword(keyword)

        values = (
            detail.name,
            detail.company_name,
            detail.english_name,
            detail.legal_person,
            detail.establish_date,
            detail.reg_location,
            detail.province,
            detail.city,
            detail.country,
            detail.website,
            1 if detail.is_south_china else 0,
        )

        if existing:
            company_id = int(existing["id"])
            self.conn.execute(
                """
                UPDATE company SET
                    project_id = COALESCE(?, project_id),
                    search_keyword = COALESCE(?, search_keyword),
                    brief_name = ?,
                    full_name = ?,
                    english_name = ?,
                    legal_person = ?,
                    establish_date = ?,
                    reg_location = ?,
                    province = ?,
                    city = ?,
                    country = ?,
                    website = ?,
                    is_south_china = ?,
                    fetched_at = ?
                WHERE id = ?
                """,
                (
                    project_id,
                    keyword,
                    *values,
                    now,
                    company_id,
                ),
            )
            self.conn.execute("DELETE FROM shareholder WHERE company_id = ?", (company_id,))
        else:
            cursor = self.conn.execute(
                """
                INSERT INTO company (
                    source, project_id, search_keyword, brief_name, full_name,
                    english_name, legal_person, establish_date, reg_location,
                    province, city, country, website, is_south_china,
                    fetched_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    DATA_SOURCE_36KR,
                    project_id,
                    keyword,
                    *values,
                    now,
                    now,
                ),
            )
            company_id = int(cursor.lastrowid)

        for sh in detail.shareholders:
            self.conn.execute(
                """
                INSERT INTO shareholder (
                    company_id, name, share_ratio, subscribed_amount, subscribed_date
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (company_id, sh.name, sh.percent, sh.amount, sh.time),
            )
        self.conn.commit()
        return company_id

    def get_or_create_placeholder(self, name: str) -> int:
        """为仅知名称的关联公司创建占位记录。"""
        row = self.conn.execute(
            "SELECT id FROM company WHERE source = ? AND full_name = ?",
            (DATA_SOURCE_36KR, name),
        ).fetchone()
        if row:
            return int(row["id"])
        now = utc_now_iso()
        cursor = self.conn.execute(
            """
            INSERT INTO company (
                source, full_name, fetched_at, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (DATA_SOURCE_36KR, name, now, now),
        )
        self.conn.commit()
        return int(cursor.lastrowid)


class BatchRepository:
    """每次 pipeline 运行对应一条 crawl_batch 记录，用于统计缓存命中率。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """初始化批次仓储。"""
        self.conn = conn

    def start_batch(self, params: dict[str, Any]) -> int:
        """创建新的爬取批次记录，返回 batch_id。"""
        cursor = self.conn.execute(
            """
            INSERT INTO crawl_batch (source, params_json, started_at, status)
            VALUES (?, ?, ?, 'running')
            """,
            (DATA_SOURCE_36KR, dumps_json(params), utc_now_iso()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def finish_batch(
        self,
        batch_id: int,
        *,
        status: str = "completed",
        cache_hits: int = 0,
        cache_misses: int = 0,
        cache_expired: int = 0,
    ) -> None:
        """更新批次结束时间与缓存统计。"""
        self.conn.execute(
            """
            UPDATE crawl_batch SET
                finished_at = ?,
                status = ?,
                company_cache_hits = ?,
                company_cache_misses = ?,
                company_cache_expired = ?
            WHERE id = ?
            """,
            (utc_now_iso(), status, cache_hits, cache_misses, cache_expired, batch_id),
        )
        self.conn.commit()


class FinancingRepository:
    """融资事件持久化；按 (project_name, financing_date, event_type) 去重更新。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """初始化融资事件仓储。"""
        self.conn = conn

    def find_event_id(
        self,
        company: FinancingCompany,
        financing_date: str,
    ) -> int | None:
        """按企业名 + 融资日期 + 事件类型查找已有事件 ID。"""
        name = dedupe_name(company)
        row = self.conn.execute(
            """
            SELECT id FROM financing_event
            WHERE financing_date = ?
              AND event_type = ?
              AND COALESCE(NULLIF(company_full_name, ''), project_name) = ?
            """,
            (financing_date, company.event_type, name),
        ).fetchone()
        return int(row["id"]) if row else None

    def save_event(
        self,
        batch_id: int,
        company: FinancingCompany,
        *,
        company_id: int | None = None,
    ) -> int:
        """写入或更新融资事件，返回 event_id。"""
        financing_date = format_financing_date(company.financing_date) or ""
        existing_id = self.find_event_id(company, financing_date)
        industry = company.national_industry or "、".join(company.industry_list)
        values = (
            batch_id,
            company.source,
            company.project_id,
            company_id,
            company.project_name,
            company.project_brief,
            industry,
            financing_date,
            company.financing_round,
            company.financing_money,
            company.investor,
            company.url,
            company.event_type,
            company.external_id or None,
            company.full_name or None,
            company.company_keyno or None,
            company.province or None,
            company.city or None,
            company.county or None,
            company.country or None,
            company.industry_category or None,
            company.industry_major or None,
            company.national_industry or None,
            company.listing_board or None,
            company.establish_date or None,
            company.buyer or None,
            company.seller or None,
            company.trade_equity_ratio or None,
            company.exit_type or None,
            company.holder_name or None,
            company.return_multiple or None,
            company.irr or None,
            company.exit_equity_ratio or None,
        )
        if existing_id:
            self.conn.execute(
                """
                UPDATE financing_event SET
                    batch_id = ?,
                    source = ?,
                    project_id = ?,
                    company_id = COALESCE(?, company_id),
                    project_name = ?,
                    project_brief = ?,
                    industry = ?,
                    financing_date = ?,
                    financing_round = ?,
                    financing_amount = ?,
                    investor = ?,
                    source_url = ?,
                    event_type = ?,
                    external_id = ?,
                    company_full_name = ?,
                    company_keyno = ?,
                    province = ?,
                    city = ?,
                    county = ?,
                    country = ?,
                    industry_category = ?,
                    industry_major = ?,
                    national_industry = ?,
                    listing_board = ?,
                    establish_date = ?,
                    buyer = ?,
                    seller = ?,
                    trade_equity_ratio = ?,
                    exit_type = ?,
                    holder_name = ?,
                    return_multiple = ?,
                    irr = ?,
                    exit_equity_ratio = ?
                WHERE id = ?
                """,
                (*values, existing_id),
            )
            self.conn.commit()
            return existing_id

        cursor = self.conn.execute(
            """
            INSERT INTO financing_event (
                batch_id, source, project_id, company_id, project_name,
                project_brief, industry, financing_date, financing_round,
                financing_amount, investor, source_url, event_type,
                external_id, company_full_name, company_keyno, province,
                city, county, country, industry_category, industry_major,
                national_industry, listing_board, establish_date, buyer,
                seller, trade_equity_ratio, exit_type, holder_name,
                return_multiple, irr, exit_equity_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def update_company_link(self, event_id: int, company_id: int) -> None:
        """将融资事件关联到 company 表记录。"""
        self.conn.execute(
            "UPDATE financing_event SET company_id = ? WHERE id = ?",
            (company_id, event_id),
        )
        self.conn.commit()


class RelatedRepository:
    """融资公司与华南关联公司之间的多对多关系。"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """初始化关联公司仓储。"""
        self.conn = conn

    def save_related(
        self,
        batch_id: int,
        financing_event_id: int,
        related_company_id: int,
        relation_type: str,
        related_name: str,
    ) -> None:
        """保存融资公司与华南关联公司的关系（重复则忽略）。"""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO related_company (
                batch_id, financing_event_id, related_company_id,
                relation_type, related_name
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (batch_id, financing_event_id, related_company_id, relation_type, related_name),
        )
        self.conn.commit()

    def list_rows_for_batch(self, batch_id: int) -> list[RelatedCompanyRow]:
        """查询指定批次的所有华南关联行。"""
        rows = self.conn.execute(
            """
            SELECT
                fe.project_name AS financing_company,
                fe.financing_date,
                fe.financing_amount,
                fe.financing_round,
                rc.related_name AS related_company,
                rc.relation_type
            FROM related_company rc
            JOIN financing_event fe ON fe.id = rc.financing_event_id
            WHERE rc.batch_id = ?
            ORDER BY fe.project_name, rc.relation_type, rc.related_name
            """,
            (batch_id,),
        ).fetchall()
        return [
            RelatedCompanyRow(
                financing_company=row["financing_company"],
                financing_date=row["financing_date"] or "",
                financing_amount=row["financing_amount"] or "",
                financing_round=row["financing_round"] or "",
                related_company=row["related_company"],
                related_type=row["relation_type"],
            )
            for row in rows
        ]
