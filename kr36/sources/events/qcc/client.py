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

from kr36.sources.infra.iyiou.constants import STEALTH_USER_AGENT


class QccClient:
    """企查查创投事件 HTTP 客户端；Cookie 失效时自动触发浏览器登录。"""

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
        cookie_header: str | None = None,
        allow_relogin: bool = True,
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

        return self._post(
            path,
            body,
            referer=referer,
            cookie_header=cookie_header,
            allow_relogin=allow_relogin,
        )

    def _post(
        self,
        path: str,
        body: dict[str, Any],
        *,
        referer: str,
        cookie_header: str | None = None,
        allow_relogin: bool = True,
        _retried: bool = False,
    ) -> dict[str, Any]:
        """向企查查 API 发送 POST 请求并解析 JSON 响应。"""
        payload = json.dumps(body).encode("utf-8")
        headers = {
            "User-Agent": STEALTH_USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": QCC_ORIGIN,
            "Referer": referer,
        }
        cookie = (cookie_header or resolve_cookie_header()).strip()
        if cookie:
            headers["Cookie"] = cookie

        req = urllib.request.Request(
            f"{QCC_ORIGIN}{path}",
            data=payload,
            method="POST",
            headers=headers,
        )
        self._sleep()
        raw = ""
        http_code: int | None = None
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            http_code = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
            if not _looks_like_auth_failure(raw=raw, http_code=http_code):
                raise RuntimeError(f"企查查 HTTP {exc.code}: {raw[:500]}") from exc

        data: dict[str, Any] = {}
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    data = parsed
            except json.JSONDecodeError:
                if not _looks_like_auth_failure(raw=raw, http_code=http_code):
                    raise RuntimeError(f"企查查响应非 JSON: {raw[:200]}")
                if not allow_relogin or _retried:
                    raise RuntimeError("企查查 API 返回非 JSON，可能未登录或触发风控")
                return self._retry_after_login(
                    path, body, referer=referer, cookie_header=cookie_header, _retried=_retried
                )

        if _looks_like_auth_failure(raw=raw, http_code=http_code, data=data):
            if not allow_relogin or _retried:
                raise RuntimeError("企查查 API 需要登录或 Cookie 已失效")
            return self._retry_after_login(
                path, body, referer=referer, cookie_header=cookie_header, _retried=_retried
            )

        status = data.get("Status")
        if status not in (200, "200", None):
            message = str(data.get("Message") or data.get("msg") or raw[:200])
            if _looks_like_auth_failure(raw=raw, data=data, message=message):
                if not allow_relogin or _retried:
                    raise RuntimeError(f"企查查 API 错误 Status={status}: {message}")
                return self._retry_after_login(
                    path, body, referer=referer, cookie_header=cookie_header, _retried=_retried
                )
            raise RuntimeError(f"企查查 API 错误 Status={status}: {message}")
        return data

    def _retry_after_login(
        self,
        path: str,
        body: dict[str, Any],
        *,
        referer: str,
        cookie_header: str | None,
        _retried: bool,
    ) -> dict[str, Any]:
        if _retried:
            raise RuntimeError("企查查登录后仍无法访问 API，请稍后重试")
        from kr36.sources.events.qcc.auth import ensure_qcc_login

        if not ensure_qcc_login():
            raise RuntimeError("企查查需要登录，浏览器扫码未完成")
        return self._post(path, body, referer=referer, _retried=True)

    def _sleep(self) -> None:
        """请求前随机休眠，避免频率限制。"""
        if self.delay_max <= 0:
            return
        time.sleep(random.uniform(self.delay_min, self.delay_max))


def _looks_like_auth_failure(
    *,
    raw: str = "",
    http_code: int | None = None,
    data: dict[str, Any] | None = None,
    message: str = "",
) -> bool:
    """判断响应是否因未登录 / Cookie 失效导致。"""
    if http_code in (401, 403):
        return True
    if raw.lstrip().startswith("<"):
        return True
    text = message or str((data or {}).get("Message") or (data or {}).get("msg") or "")
    lowered = text.lower()
    login_tokens = ("未登录", "请登录", "需要登录", "登录后", "重新登录", "请先登录")
    if any(token in text for token in login_tokens):
        return True
    if "login" in lowered or "unauthorized" in lowered or "weblogin" in lowered:
        return True
    status = (data or {}).get("Status")
    if status in (401, "401", 403, "403"):
        return True
    return False
