"""Tests for JSON format helpers."""

from __future__ import annotations

from versa_note.json_format import json_error_message, minify_json, prettify_json


def test_prettify_json_indents_and_trailing_newline() -> None:
    assert prettify_json('{"a":1,"b":[true,null]}') == (
        '{\n  "a": 1,\n  "b": [\n    true,\n    null\n  ]\n}\n'
    )


def test_prettify_json_preserves_unicode() -> None:
    assert prettify_json('{"n":"café"}') == '{\n  "n": "café"\n}\n'


def test_prettify_json_invalid_returns_none() -> None:
    assert prettify_json("{") is None
    assert prettify_json("") is None


def test_minify_json_compacts() -> None:
    assert minify_json('{\n  "a": 1\n}') == '{"a":1}'


def test_minify_json_invalid_returns_none() -> None:
    assert minify_json("not json") is None


def test_json_error_message_valid() -> None:
    assert json_error_message('{"ok": true}') is None
    assert json_error_message("[]") is None


def test_json_error_message_empty() -> None:
    assert json_error_message("") == "empty"
    assert json_error_message("   ") == "empty"


def test_json_error_message_includes_line_col() -> None:
    msg = json_error_message("{")
    assert msg is not None
    assert "line" in msg
    assert "col" in msg
