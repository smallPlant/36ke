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


def tools_dir() -> Path:
    """打包版内置工具目录（便携 Node.js + lark-cli）。"""
    return app_dir() / "tools"


def bundled_node_dir() -> Path:
    """便携 Node.js 目录（tools/node）。"""
    return tools_dir() / "node"


def bundled_npm_prefix() -> Path:
    """npm 全局前缀（tools/npm，含 lark-cli）。"""
    return tools_dir() / "npm"


def bundled_node_exe() -> Path | None:
    """便携 node.exe，不存在则返回 None。"""
    path = bundled_node_dir() / "node.exe"
    return path if path.is_file() else None


def bundled_npm_cmd() -> Path | None:
    """便携 npm.cmd，不存在则返回 None。"""
    path = bundled_node_dir() / "npm.cmd"
    return path if path.is_file() else None


def bundled_lark_cli() -> Path | None:
    """内置 lark-cli 可执行文件，不存在则返回 None。"""
    candidates = [
        tools_dir() / "lark-cli" / "lark-cli.exe",
        bundled_npm_prefix() / "lark-cli.cmd",
        bundled_npm_prefix() / "node_modules" / ".bin" / "lark-cli.cmd",
        bundled_npm_prefix() / "lark-cli",
        bundled_npm_prefix() / "node_modules" / ".bin" / "lark-cli",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def default_lark_cli_bin() -> str:
    """默认 lark-cli 路径：环境变量 > 内置 tools > 系统 PATH 中的 lark-cli。"""
    env = os.getenv("LARK_CLI_BIN", "").strip()
    if env:
        return env
    bundled = bundled_lark_cli()
    if bundled:
        return str(bundled)
    return "lark-cli"


def configure_playwright_browsers() -> None:
    """若存在内置 browsers 目录，则指向 Playwright 使用内置 Chromium。"""
    browsers = bundled_browsers_dir()
    if browsers.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
