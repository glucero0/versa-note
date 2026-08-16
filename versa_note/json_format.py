"""JSON format helpers (stdlib only)."""

from __future__ import annotations

import json
from typing import Optional


def prettify_json(text: str) -> Optional[str]:
    """Parse JSON and return indented text with a trailing newline, or None on error."""
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def minify_json(text: str) -> Optional[str]:
    """Parse JSON and return compact text, or None on error."""
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def json_error_message(text: str) -> Optional[str]:
    """Return None if text is valid JSON; otherwise a short error message."""
    if not text.strip():
        return "empty"
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return f"{exc.msg} (line {exc.lineno}, col {exc.colno})"
    return None
