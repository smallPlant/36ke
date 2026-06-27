from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kr36.client import PitchHubClient
from kr36.config import PITCHHUB_ORIGIN
from kr36.models import FinancingCompany

# 按天数拉取时的翻页安全上限
MAX_PAGES_WHEN_DAYS = 100


class FinancingCrawler:
    """拉取 36氪融资公司列表。"""

    API_PATH = "project/financing/list"
    REFERER = f"{PITCHHUB_ORIGIN}/financing-flash"

    def __init__(self, client: PitchHubClient | None = None) -> None:
        self.client = client or PitchHubClient()

    def fetch_page(self, page_no: int, page_size: int) -> tuple[list[FinancingCompany], dict]:
        data = self.client.gateway_post(
            self.API_PATH,
            {"pageNo": page_no, "pageSize": page_size},
            referer=self.REFERER,
        )["data"]
        items = [self._normalize(raw) for raw in data.get("financingList", [])]
        return items, data.get("page", {})

    def crawl(
        self,
        *,
        max_pages: int = 1,
        page_size: int = 20,
        days: int | None = None,
    ) -> list[FinancingCompany]:
        since_ms = self._since_ms(days) if days else None
        page_limit = MAX_PAGES_WHEN_DAYS if days else max_pages

        collected: list[FinancingCompany] = []
        seen_ids: set[int] = set()

        for page_no in range(1, page_limit + 1):
            items, page_info = self.fetch_page(page_no, page_size)
            if not items:
                break

            for item in items:
                if item.project_id in seen_ids:
                    continue
                if since_ms and item.financing_date and item.financing_date < since_ms:
                    continue
                seen_ids.add(item.project_id)
                collected.append(item)

            if since_ms and items[-1].financing_date < since_ms:
                break
            if page_no >= page_info.get("totalPage", page_no):
                break

        return collected

    @staticmethod
    def _since_ms(days: int) -> int:
        since = datetime.now() - timedelta(days=days)
        return int(since.timestamp() * 1000)

    @staticmethod
    def _normalize(raw: dict) -> FinancingCompany:
        project_id = int(raw["projectId"])
        return FinancingCompany(
            project_id=project_id,
            project_name=raw.get("projectName", ""),
            project_brief=raw.get("projectBrief", ""),
            industry_list=list(raw.get("industryList") or []),
            financing_round=raw.get("financingRoundRemark", ""),
            financing_date=int(raw.get("financingDate") or 0),
            financing_money=raw.get("financingMoney", ""),
            investor=raw.get("investor", ""),
            url=raw.get("projectUrlRoute") or f"{PITCHHUB_ORIGIN}/project/{project_id}",
        )


def format_financing_date(ms: int) -> str:
    if not ms:
        return ""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d")
