"""应用路径解析：数据目录、数据库路径与 Playwright 浏览器目录。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def app_dir() -> Path:
    """程序根目录：开发时为项目根，PyInstaller 打包后为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def default_data_dir() -> Path:
    """默认数据目录（项目根下 data/）。"""
    return app_dir() / "data"


def default_db_path() -> Path:
    """默认 SQLite 数据库路径。"""
    return default_data_dir() / "kr36.db"


def default_qcc_dir() -> Path:
    """企查查 Cookie / 浏览器配置目录。"""
    return default_data_dir() / "qcc"


def default_qcc_storage_state_path() -> Path:
    """Playwright storage_state 默认路径。"""
    return default_qcc_dir() / "storage_state.json"


def default_qcc_cookie_path() -> Path:
    """urllib 使用的 Cookie 字符串文件。"""
    return default_qcc_dir() / "cookie.txt"


def default_qcc_profile_dir() -> Path:
    """企查查 Playwright 持久化用户目录（保留浏览器登录态）。"""
    return default_qcc_dir() / "profile"


def bundled_browsers_dir() -> Path:
    """打包内置 Playwright Chromium 目录。"""
    return app_dir() / "browsers"


def configure_playwright_browsers() -> None:
    """若存在内置 browsers 目录，则指向 Playwright 使用内置 Chromium。"""
    browsers = bundled_browsers_dir()
    if browsers.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
