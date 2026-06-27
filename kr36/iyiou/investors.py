from __future__ import annotations

import ast
import json
from typing import Any


def format_iyiou_investors(raw: Any) -> str:
    """将亿欧 investors 字段清洗为纯文本投资方名称（顿号分隔）。"""
    if raw is None:
        return ""
    if isinstance(raw, list):
        return _join_names(_names_from_list(raw))
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return ""
        if text.startswith("["):
            parsed = _parse_list_string(text)
            if parsed is not None:
                return _join_names(_names_from_list(parsed))
        return text
    return str(raw).strip()


def _parse_list_string(text: str) -> list[Any] | None:
    for loader in (json.loads, ast.literal_eval):
        try:
            parsed = loader(text)
        except (json.JSONDecodeError, ValueError, SyntaxError):
            continue
        if isinstance(parsed, list):
            return parsed
    return None


def _names_from_list(items: list[Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for item in items:
        name = ""
        if isinstance(item, dict):
            name = str(item.get("investorName") or item.get("name") or "").strip()
        elif isinstance(item, str):
            name = item.strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _join_names(names: list[str]) -> str:
    return "、".join(names)
