from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from kr36.iyiou.constants import STEALTH_INIT_SCRIPT, STEALTH_USER_AGENT
from kr36.paths import configure_playwright_browsers


class IyiouBrowser:
    """带反爬规避的 Playwright 浏览器会话。"""

    def __init__(
        self,
        *,
        headless: bool = True,
        profile: Path | None = None,
    ) -> None:
        self.headless = headless
        self.profile = profile
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> IyiouBrowser:
        configure_playwright_browsers()
        self._playwright = sync_playwright().start()
        launch_args = ["--disable-blink-features=AutomationControlled"]
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": 1440, "height": 900},
            "user_agent": STEALTH_USER_AGENT,
            "locale": "zh-CN",
        }

        if self.profile:
            self.profile.mkdir(parents=True, exist_ok=True)
            self.context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile.resolve()),
                headless=self.headless,
                args=launch_args,
                **context_kwargs,
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=self.headless, args=launch_args)
            self.context = self._browser.new_context(**context_kwargs)
            self.page = self.context.new_page()

        self.context.add_init_script(STEALTH_INIT_SCRIPT)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.context:
            self.context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def goto(self, url: str, *, wait_ms: int = 2000) -> Page:
        assert self.page is not None
        self.page.goto(url, wait_until="load", timeout=60_000)
        if wait_ms:
            self.page.wait_for_timeout(wait_ms)
        return self.page

    def save_storage_state(self, path: Path) -> None:
        assert self.context is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        self.context.storage_state(path=str(path))
