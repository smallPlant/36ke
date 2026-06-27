from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from kr36.iyiou.browser import IyiouBrowser
from kr36.iyiou.constants import (
    DEFAULT_COLUMN_ORDER,
    IYIOU_INVEST_API,
    IYIOU_INVEST_LIST_URL,
)
from kr36.iyiou.models import InvestEvent


class IyiouInvestClient:
    """通过 Playwright 浏览器上下文请求亿欧投资事件 API。"""

    def __init__(self, browser: IyiouBrowser) -> None:
        self.browser = browser

    def warmup(self) -> None:
        """访问列表页，获取反爬 Cookie 与 SSR 初始数据。"""
        self.browser.goto(IYIOU_INVEST_LIST_URL)

    def get_token(self) -> str:
        page = self.browser.page
        assert page is not None
        return page.evaluate(
            """() => {
                const state = window.__INITIAL_STATE__;
                return (state && state.userModule && state.userModule.token) || '';
            }"""
        )

    def fetch_page(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search_box: str = "",
        country: int = 0,
        invest_round: int = 0,
        time_section: int = 0,
        column_order: str = DEFAULT_COLUMN_ORDER,
    ) -> tuple[list[InvestEvent], int]:
        """拉取单页投资事件，返回 (records, total)。"""
        context = self.browser.context
        assert context is not None

        token = self.get_token()
        params = {
            "token": token,
            "page": page,
            "pageSize": page_size,
            "columnOrder": column_order,
            "country": country,
            "tagId": "",
            "investRound": invest_round,
            "timeSection": time_section,
            "startTime": "",
            "endTime": "",
            "searchBox": search_box,
        }
        url = f"{IYIOU_INVEST_API}?{urlencode(params)}"
        response = context.request.get(
            url,
            headers={
                "Auth": token,
                "Referer": IYIOU_INVEST_LIST_URL,
            },
        )
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"亿欧 API 失败: {payload.get('message') or payload}")

        data_list = payload["data"]["dataList"]
        records = [InvestEvent.from_api_record(item) for item in data_list.get("records", [])]
        total = int(data_list.get("total") or 0)
        return records, total

    def fetch_initial_state(self) -> tuple[list[InvestEvent], int]:
        """从 SSR 嵌入的 __INITIAL_STATE__ 读取首页数据。"""
        page = self.browser.page
        assert page is not None
        raw = page.evaluate(
            """() => {
                const list = window.__INITIAL_STATE__?.investModule?.investList;
                if (!list) return null;
                return { total: list.total || 0, records: list.records || [] };
            }"""
        )
        if not raw:
            return [], 0
        records = [InvestEvent.from_api_record(item) for item in raw.get("records", [])]
        return records, int(raw.get("total") or 0)

    def fetch_pages(
        self,
        *,
        max_pages: int = 1,
        page_size: int = 20,
        search_box: str = "",
    ) -> tuple[list[InvestEvent], int]:
        """拉取多页，自动去重。"""
        results: list[InvestEvent] = []
        seen: set[str] = set()
        total = 0

        for page_no in range(1, max_pages + 1):
            batch, total = self.fetch_page(page=page_no, page_size=page_size, search_box=search_box)
            if not batch:
                break
            for item in batch:
                if item.invest_id in seen:
                    continue
                seen.add(item.invest_id)
                results.append(item)
            if len(batch) < page_size:
                break

        return results, total

    @staticmethod
    def build_api_params(
        *,
        page: int = 1,
        page_size: int = 20,
        token: str = "",
        search_box: str = "",
    ) -> dict[str, Any]:
        return {
            "token": token,
            "page": page,
            "pageSize": page_size,
            "columnOrder": DEFAULT_COLUMN_ORDER,
            "country": 0,
            "tagId": "",
            "investRound": 0,
            "timeSection": 0,
            "startTime": "",
            "endTime": "",
            "searchBox": search_box,
        }
