"""企查查 Cookie / Playwright storage_state 读写。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from kr36.core.paths import default_qcc_cookie_path, default_qcc_storage_state_path

QCC_COOKIE_ENV = "QCC_COOKIE"


def resolve_cookie_header() -> str:
    """按优先级读取 Cookie：环境变量 > cookie.txt > storage_state.json。"""
    env = os.getenv(QCC_COOKIE_ENV, "").strip()
    if env:
        return env

    cookie_path = default_qcc_cookie_path()
    if cookie_path.is_file():
        text = cookie_path.read_text(encoding="utf-8").strip()
        if text:
            return text

    return cookie_header_from_storage_state(default_qcc_storage_state_path())


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
        if "qcc.com" not in domain:
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
