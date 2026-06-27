from __future__ import annotations

import json
import random
import re
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from kr36.config import DEFAULT_DELAY_MAX, DEFAULT_DELAY_MIN, GATEWAY_BASE, PITCHHUB_ORIGIN

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class PitchHubClient:
    """36氪 PitchHub Gateway / 页面客户端。"""

    def __init__(
        self,
        delay_min: float = DEFAULT_DELAY_MIN,
        delay_max: float = DEFAULT_DELAY_MAX,
        timeout: int = 30,
    ) -> None:
        self.delay_min = min(delay_min, delay_max)
        self.delay_max = max(delay_min, delay_max)
        self.timeout = timeout
        self._last_request_at = 0.0
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)

    def _throttle(self) -> None:
        if self._last_request_at > 0:
            wait = random.uniform(self.delay_min, self.delay_max)
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < wait:
                time.sleep(wait - elapsed)
        self._last_request_at = time.monotonic()

    def gateway_post(self, path: str, param: dict[str, Any], *, referer: str) -> dict[str, Any]:
        self._throttle()
        payload = {
            "partner_id": "web",
            "timestamp": int(time.time() * 1000),
            "param": param,
        }
        headers = {
            "Content-Type": "application/json",
            "Origin": PITCHHUB_ORIGIN,
            "Referer": referer,
        }
        url = f"{GATEWAY_BASE}/{path.lstrip('/')}"
        resp = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Gateway API 错误 [{path}]: {data.get('msg', data)}")
        return data

    def get_project_html(self, project_id: int) -> str:
        self._throttle()
        url = f"{PITCHHUB_ORIGIN}/project/{project_id}"
        resp = self.session.get(url, headers={"Referer": PITCHHUB_ORIGIN}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def parse_init_props(html: str) -> dict[str, Any] | None:
        marker = "window.__INIT_PROPS__ = "
        start = html.find(marker)
        if start == -1:
            return None
        start += len(marker)
        depth = 0
        for index, char in enumerate(html[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(html[start : index + 1])
        return None

    @staticmethod
    def strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text or "").strip()
