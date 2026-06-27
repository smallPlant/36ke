from __future__ import annotations

import os
import sys
from pathlib import Path


def app_dir() -> Path:
    """程序根目录：开发时为项目根，PyInstaller 打包后为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def default_data_dir() -> Path:
    return app_dir() / "data"


def default_db_path() -> Path:
    return default_data_dir() / "kr36.db"


def bundled_browsers_dir() -> Path:
    return app_dir() / "browsers"


def configure_playwright_browsers() -> None:
    """若存在内置 browsers 目录，则指向 Playwright 使用内置 Chromium。"""
    browsers = bundled_browsers_dir()
    if browsers.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
