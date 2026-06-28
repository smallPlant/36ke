"""企查查 Cookie / Playwright storage_state 读写。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from kr36.core.paths import default_qcc_cookie_path, default_qcc_storage_state_path

QCC_COOKIE_ENV = "QCC_COOKIE"


def resolve_cookie_header() -> str:
    """按优先级读取 Cookie：环境变量 > storage_state.json > cookie.txt。"""
    env = os.getenv(QCC_COOKIE_ENV, "").strip()
    if env:
        return env

    storage_cookie = cookie_header_from_storage_state(default_qcc_storage_state_path())
    if storage_cookie:
        return storage_cookie

    cookie_path = default_qcc_cookie_path()
    if cookie_path.is_file():
        text = cookie_path.read_text(encoding="utf-8").strip()
        if text:
            return text

    return ""


def cookie_header_from_storage_state(path: Path) -> str:
    """从 Playwright storage_state 提取 qcc.com 域 Cookie 字符串。"""
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""

    parts: list[str] = []
    seen: set[str] = set()
    for item in data.get("cookies") or []:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or "")
        if "qcc.com" not in domain.lower():
            continue
        name = str(item.get("name") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        parts.append(f"{name}={item.get('value', '')}")
    return "; ".join(parts)


def save_cookie_header(cookie_header: str, *, path: Path | None = None) -> Path:
    """保存 Cookie 字符串到 data/qcc/cookie.txt。"""
    target = path or default_qcc_cookie_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(cookie_header.strip(), encoding="utf-8")
    return target


def save_storage_state_copy(source: Path, *, dest: Path | None = None) -> Path:
    """复制 Playwright storage_state 到默认路径。"""
    target = dest or default_qcc_storage_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def persist_qcc_session(context, *, storage_path: Path | None = None) -> str:
    """从 Playwright 上下文导出 storage_state 并同步 cookie.txt。"""
    target = storage_path or default_qcc_storage_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(target))
    cookie_header = cookie_header_from_storage_state(target)
    if cookie_header:
        save_cookie_header(cookie_header)
    return cookie_header
