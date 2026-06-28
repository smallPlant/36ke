from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Any

from kr36.sources.events.qcc.cookie_store import resolve_cookie_header

from kr36.sources.events.qcc.constants import (
    DEFAULT_PAGE_SIZE,
    EVENT_API_PATHS,
    EVENT_REFERERS,
    EVENT_TYPES,
    QCC_ORIGIN,
)


class QccClient:
    """企查查创投事件 HTTP 客户端；优先使用已保存 Cookie（见 setup-qcc）。"""

    def __init__(
        self,
        *,
        delay_min: float = 0.5,
        delay_max: float = 1.5,
        timeout: float = 30.0,
    ) -> None:
        """初始化企查查 HTTP 客户端。"""
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.timeout = timeout

    def fetch_event_page(
        self,
        event_type: str,
        *,
        page_index: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        search_key: str = "",
        chain_code: str = "",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """拉取指定类型的单页创投事件。"""
        if event_type not in EVENT_TYPES:
            raise ValueError(f"未知企查查事件类型: {event_type}")

        body: dict[str, Any] = {
            "pageIndex": page_index,
            "pageSize": page_size,
        }
        if search_key:
            body["searchKey"] = search_key
        if chain_code:
            body["chainCode"] = chain_code
        if extra:
            body.update(extra)

        path = EVENT_API_PATHS[event_type]
        referer = EVENT_REFERERS[event_type]
        if chain_code and event_type == EVENT_TYPES[-1]:
            referer = f"{referer}?code={chain_code}"

        return self._post(path, body, referer=referer)

    def _post(self, path: str, body: dict[str, Any], *, referer: str) -> dict[str, Any]:
        """向企查查 API 发送 POST 请求并解析 JSON 响应。"""
        payload = json.dumps(body).encode("utf-8")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": QCC_ORIGIN,
            "Referer": referer,
        }
        cookie = resolve_cookie_header()
        if cookie:
            headers["Cookie"] = cookie

        req = urllib.request.Request(
            f"{QCC_ORIGIN}{path}",
            data=payload,
            method="POST",
            headers=headers,
        )
        self._sleep()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"企查查 HTTP {exc.code}: {detail}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            if raw.lstrip().startswith("<"):
                raise RuntimeError(
                    "企查查返回 HTML 页面（可能触发登录/频率限制）。"
                    "请先执行: python main.py setup-qcc"
                ) from exc
            raise RuntimeError(f"企查查响应非 JSON: {raw[:200]}") from exc
        status = data.get("Status")
        if status not in (200, "200", None):
            message = data.get("Message") or data.get("msg") or raw[:200]
            raise RuntimeError(f"企查查 API 错误 Status={status}: {message}")
        return data

    def _sleep(self) -> None:
        """请求前随机休眠，避免频率限制。"""
        if self.delay_max <= 0:
            return
        time.sleep(random.uniform(self.delay_min, self.delay_max))
