from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlencode

from playwright.sync_api import Request, Response

from kr36.sources.infra.iyiou.browser import IyiouBrowser
from kr36.sources.events.iyiou.client import IyiouInvestClient
from kr36.sources.infra.iyiou.constants import IYIOU_INVEST_LIST_URL

STATIC_SUFFIXES = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".woff2", ".ico")


def _is_static_asset(url: str) -> bool:
    """判断 URL 是否为静态资源（非 API）。"""
    lower = url.lower().split("?", 1)[0]
    return lower.endswith(STATIC_SUFFIXES) or "/probe" in lower


def _is_api_request(request: Request) -> bool:
    """判断 Playwright 请求是否为亿欧 API（XHR/Fetch）。"""
    url = request.url.lower()
    if not url.startswith("http") or _is_static_asset(url):
        return False
    if request.resource_type not in {"xhr", "fetch"}:
        return False
    return "iyiou.com" in url


def _safe_filename(url: str, index: int) -> str:
    """根据 URL 生成安全的抓包文件名。"""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "root"
    path = re.sub(r"[^\w.-]+", "_", path)[:80]
    return f"{index:03d}_{parsed.netloc}_{path}.json"


def _build_record(request: Request, response: Response, body: Any) -> dict[str, Any]:
    """组装单次 HTTP 抓包记录。"""
    return {
        "url": response.url,
        "method": request.method,
        "status": response.status,
        "resource_type": request.resource_type,
        "request_headers": request.headers,
        "response_headers": response.headers,
        "post_data": request.post_data,
        "body": body,
    }


def _to_curl(record: dict[str, Any]) -> str:
    """将抓包记录转换为可执行的 curl 命令。"""
    lines = [f"curl '{record['url']}'", f"  -X {record['method']}"]
    for key, value in record["request_headers"].items():
        if key.lower() in {"content-length", "host"}:
            continue
        lines.append(f"  -H '{key}: {value}'")
    if record.get("post_data"):
        escaped = str(record["post_data"]).replace("'", "'\\''")
        lines.append(f"  --data-raw '{escaped}'")
    return " \\\n".join(lines)


def _try_trigger_actions(page) -> None:
    """尝试点击翻页按钮以触发更多 API 请求。"""
    selectors = [
        ".ant-pagination-next",
        ".ant-pagination-item:nth-child(2)",
        "button:has-text('下一页')",
        "text=下一页",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=1000):
                locator.click(timeout=3000)
                page.wait_for_timeout(2000)
                return
        except Exception:
            continue


class IyiouCaptureRunner:
    """Playwright 自动抓包：记录 XHR/Fetch 并导出 API 规格。"""

    API_SPEC = {
        "name": "亿欧投资事件列表",
        "page_url": IYIOU_INVEST_LIST_URL,
        "endpoint": "https://apidata.iyiou.com/spa/invest/defaultList",
        "method": "GET",
        "auth_header": "Auth",
        "query_params": IyiouInvestClient.build_api_params(),
        "response_path": "data.dataList.records",
        "notes": [
            "需先通过 Playwright 打开列表页以获取反爬 Cookie",
            "未登录时 API 可能只返回第一页数据；翻页需登录并使用 --profile 保存登录态",
        ],
    }

    def __init__(
        self,
        *,
        url: str = IYIOU_INVEST_LIST_URL,
        output_dir: Path,
        headless: bool = False,
        profile: Path | None = None,
        wait_seconds: int = 30,
        auto_paginate: bool = True,
        save_curl: bool = True,
    ) -> None:
        """配置抓包参数：输出目录、等待时间、是否自动翻页等。"""
        self.url = url
        self.output_dir = output_dir
        self.headless = headless
        self.profile = profile
        self.wait_seconds = wait_seconds
        self.auto_paginate = auto_paginate
        self.save_curl = save_curl
        self.records: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    def run(self) -> Path:
        """执行抓包流程，返回输出目录路径。"""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.output_dir / f"iyiou_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        with IyiouBrowser(headless=self.headless, profile=self.profile) as browser:
            page = browser.page
            assert page is not None

            def on_response(response: Response) -> None:
                """Playwright 响应回调：过滤并保存 API 抓包记录。"""
                request = response.request
                if not _is_api_request(request) or response.status >= 400:
                    return

                content_type = response.headers.get("content-type", "")
                try:
                    body = response.json() if "json" in content_type else response.text()[:2000]
                except Exception as exc:
                    body = {"_parse_error": str(exc)}

                dedupe_key = f"{request.method}:{response.url}"
                if dedupe_key in self._seen:
                    return
                self._seen.add(dedupe_key)

                record = _build_record(request, response, body)
                self.records.append(record)
                index = len(self.records)
                file_path = out_dir / _safe_filename(response.url, index)
                file_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                if self.save_curl:
                    curl_path = out_dir / f"{file_path.stem}.curl.sh"
                    curl_path.write_text(_to_curl(record) + "\n", encoding="utf-8")

            page.on("response", on_response)
            browser.goto(self.url, wait_ms=3000)
            if self.auto_paginate:
                _try_trigger_actions(page)
            page.wait_for_timeout(max(0, self.wait_seconds - 3) * 1000)
            browser.save_storage_state(out_dir / "storage_state.json")

            client = IyiouInvestClient(browser)
            initial_records, total = client.fetch_initial_state()
            (out_dir / "initial_state_sample.json").write_text(
                json.dumps(
                    {
                        "total": total,
                        "sample_count": len(initial_records),
                        "sample": [item.to_row() for item in initial_records[:3]],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            probe_params = client.build_api_params(page=1, page_size=20, token=client.get_token())
            probe_url = f"{self.API_SPEC['endpoint']}?{urlencode(probe_params)}"
            probe_resp = browser.context.request.get(
                probe_url,
                headers={"Auth": client.get_token(), "Referer": self.url},
            )
            probe_body = probe_resp.json()
            probe_record = {
                "url": probe_url,
                "method": "GET",
                "status": probe_resp.status,
                "resource_type": "probe",
                "request_headers": {"Auth": client.get_token(), "Referer": self.url},
                "response_headers": probe_resp.headers,
                "post_data": None,
                "body": probe_body,
                "note": "脚本主动探测的投资列表 API（首页 SSR 不一定触发 XHR）",
            }
            self.records.append(probe_record)
            probe_path = out_dir / "006_apidata.iyiou.com_spa_invest_defaultList.probe.json"
            probe_path.write_text(json.dumps(probe_record, ensure_ascii=False, indent=2), encoding="utf-8")
            if self.save_curl:
                (out_dir / "006_apidata.iyiou.com_spa_invest_defaultList.probe.curl.sh").write_text(
                    _to_curl(probe_record) + "\n",
                    encoding="utf-8",
                )

        (out_dir / "api_spec.json").write_text(
            json.dumps(self.API_SPEC, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = {
            "url": self.url,
            "captured_at": stamp,
            "total": len(self.records),
            "apis": [
                {
                    "method": item["method"],
                    "status": item["status"],
                    "url": item["url"],
                    "file": _safe_filename(item["url"], idx),
                }
                for idx, item in enumerate(self.records, start=1)
            ],
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_dir
