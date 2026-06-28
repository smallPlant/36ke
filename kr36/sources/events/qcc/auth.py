"""企查查登录：Playwright 打开浏览器，等待扫码/登录后保存 Cookie。"""

from __future__ import annotations

import time
from pathlib import Path

from kr36.core.paths import (
    configure_playwright_browsers,
    default_qcc_cookie_path,
    default_qcc_profile_dir,
    default_qcc_storage_state_path,
)
from kr36.sources.infra.iyiou.constants import STEALTH_INIT_SCRIPT, STEALTH_USER_AGENT
from kr36.sources.events.qcc.constants import EVENT_REFERERS, EVENT_MAINLAND_FINANCING, QCC_ORIGIN
from kr36.sources.events.qcc.cookie_store import cookie_header_from_storage_state, save_cookie_header

LOGIN_WAIT_URL = EVENT_REFERERS[EVENT_MAINLAND_FINANCING]
PROBE_API = f"{QCC_ORIGIN}/api/investOrg/getMainlandFinancingList"
DEFAULT_TIMEOUT_SEC = 300


def _api_probe_ok(cookie_header: str) -> bool:
    """用 Cookie 探测创投 API 是否返回 JSON。"""
    if not cookie_header:
        return False
    try:
        from kr36.sources.events.qcc.client import QccClient

        client = QccClient(delay_min=0, delay_max=0)
        client.fetch_event_page(EVENT_MAINLAND_FINANCING, page_index=1, page_size=1)
        return True
    except RuntimeError:
        return False


def _cookie_header_from_context(context) -> str:
    cookies = context.cookies("https://www.qcc.com")
    parts = [f"{item['name']}={item['value']}" for item in cookies if item.get("name")]
    return "; ".join(parts)


def _is_login_page(url: str, title: str) -> bool:
    return "weblogin" in url or "会员登录" in title


def run_setup_qcc(
    *,
    headless: bool = False,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    profile_dir: Path | None = None,
) -> bool:
    """
    打开企查查创投页，等待用户扫码/登录，成功后保存 Cookie。

    - 持久化浏览器目录：data/qcc/profile（下次可复用登录态）
    - storage_state：data/qcc/storage_state.json
    - Cookie 字符串：data/qcc/cookie.txt
    """
    from playwright.sync_api import sync_playwright

    profile = profile_dir or default_qcc_profile_dir()
    storage_path = default_qcc_storage_state_path()
    profile.mkdir(parents=True, exist_ok=True)
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    configure_playwright_browsers()

    existing = cookie_header_from_storage_state(storage_path)
    if existing and _api_probe_ok(existing):
        print(f"✓ 已有有效企查查 Cookie（{storage_path}）")
        return True

    print("即将打开浏览器，请使用企查查 App 扫码或账号登录（仅需一次）...")
    print(f"登录成功后 Cookie 将保存到：\n  - {storage_path}\n  - {default_qcc_cookie_path()}")

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile.resolve()),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1440, "height": 900},
            user_agent=STEALTH_USER_AGENT,
            locale="zh-CN",
        )
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(LOGIN_WAIT_URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(1500)

        deadline = time.time() + timeout_sec
        logged_in = False
        while time.time() < deadline:
            url = page.url
            title = page.title()
            if not _is_login_page(url, title):
                cookie_header = _cookie_header_from_context(context)
                if cookie_header:
                    context.storage_state(path=str(storage_path))
                    save_cookie_header(cookie_header)
                    if _api_probe_ok(cookie_header):
                        logged_in = True
                        break
            page.wait_for_timeout(2000)

        if not logged_in:
            # 最后再试一次 storage_state（有时页面标题滞后）
            context.storage_state(path=str(storage_path))
            cookie_header = cookie_header_from_storage_state(storage_path) or _cookie_header_from_context(context)
            if cookie_header:
                save_cookie_header(cookie_header)
                logged_in = _api_probe_ok(cookie_header)

        context.close()

    if logged_in:
        print("✓ 企查查登录成功，Cookie 已保存。之后可直接运行：")
        print("  python main.py --source qcc --pages 1 --no-push-feishu")
        return True

    print("✗ 登录超时或 API 仍不可用。请重试：python main.py setup-qcc")
    return False


def verify_saved_cookie() -> dict[str, object]:
    """检查已保存 Cookie 是否有效。"""
    storage_path = default_qcc_storage_state_path()
    cookie_header = cookie_header_from_storage_state(storage_path)
    if not cookie_header:
        cookie_path = default_qcc_cookie_path()
        if cookie_path.is_file():
            cookie_header = cookie_path.read_text(encoding="utf-8").strip()
    ok = _api_probe_ok(cookie_header) if cookie_header else False
    return {
        "valid": ok,
        "storage_state": str(storage_path),
        "cookie_file": str(default_qcc_cookie_path()),
        "has_cookie": bool(cookie_header),
    }
