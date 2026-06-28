"""企查查登录：Cookie 失效或缺失时自动打开浏览器扫码登录并保存。"""

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
from kr36.sources.events.qcc.cookie_store import persist_qcc_session

LOGIN_WAIT_URL = EVENT_REFERERS[EVENT_MAINLAND_FINANCING]
DEFAULT_TIMEOUT_SEC = 300


def load_saved_cookie_header() -> str:
    """读取已保存的 Cookie（storage_state 或 cookie.txt）。"""
    from kr36.sources.events.qcc.cookie_store import resolve_cookie_header

    return resolve_cookie_header()


def _api_probe_ok(cookie_header: str | None = None) -> bool:
    """用 Cookie 探测创投 API 是否返回 JSON。"""
    header = (cookie_header or load_saved_cookie_header()).strip()
    if not header:
        return False
    try:
        from kr36.sources.events.qcc.client import QccClient

        client = QccClient(delay_min=0, delay_max=0)
        client.fetch_event_page(
            EVENT_MAINLAND_FINANCING,
            page_index=1,
            page_size=1,
            cookie_header=header,
            allow_relogin=False,
        )
        return True
    except RuntimeError:
        return False


def is_qcc_authenticated() -> bool:
    """当前 Cookie 是否存在且可用。"""
    return _api_probe_ok()


def _is_login_page(url: str, title: str) -> bool:
    return "weblogin" in url or "会员登录" in title


def _interactive_qcc_login(
    *,
    headless: bool = False,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    profile_dir: Path | None = None,
) -> bool:
    """打开浏览器等待用户扫码/登录，成功后写入 Cookie。"""
    from playwright.sync_api import sync_playwright

    profile = profile_dir or default_qcc_profile_dir()
    storage_path = default_qcc_storage_state_path()
    profile.mkdir(parents=True, exist_ok=True)
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    configure_playwright_browsers()

    print("企查查 Cookie 无效或缺失，即将打开浏览器请扫码/登录...")
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
                cookie_header = persist_qcc_session(context, storage_path=storage_path)
                if cookie_header and _api_probe_ok(cookie_header):
                    logged_in = True
                    break
            page.wait_for_timeout(2000)

        if not logged_in:
            cookie_header = persist_qcc_session(context, storage_path=storage_path)
            if cookie_header:
                logged_in = _api_probe_ok(cookie_header)

        context.close()

    if logged_in:
        print("[OK] 企查查登录成功，Cookie 已保存")
        return True

    print("[失败] 登录超时或 API 仍不可用，请重试")
    return False


def ensure_qcc_login(
    *,
    force: bool = False,
    headless: bool = False,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    profile_dir: Path | None = None,
) -> bool:
    """确保企查查已登录；Cookie 有效则跳过，否则触发浏览器扫码登录。"""
    if is_qcc_authenticated():
        return True
    if force and load_saved_cookie_header():
        print("企查查 Cookie 已失效，需重新登录...")
    return _interactive_qcc_login(
        headless=headless,
        timeout_sec=timeout_sec,
        profile_dir=profile_dir,
    )


def run_setup_qcc(
    *,
    headless: bool = False,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    profile_dir: Path | None = None,
) -> bool:
    """CLI 入口：检查 Cookie，无效则引导登录。"""
    if is_qcc_authenticated():
        print(f"[OK] 已有有效企查查 Cookie（{default_qcc_storage_state_path()}）")
        return True
    return ensure_qcc_login(
        force=True,
        headless=headless,
        timeout_sec=timeout_sec,
        profile_dir=profile_dir,
    )


def verify_saved_cookie() -> dict[str, object]:
    """检查已保存 Cookie 是否有效。"""
    cookie_header = load_saved_cookie_header()
    ok = _api_probe_ok(cookie_header) if cookie_header else False
    return {
        "valid": ok,
        "storage_state": str(default_qcc_storage_state_path()),
        "cookie_file": str(default_qcc_cookie_path()),
        "has_cookie": bool(cookie_header),
    }
