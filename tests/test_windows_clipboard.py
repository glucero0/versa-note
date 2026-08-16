"""Windows clipboard API edge cases (mocked / platform gated)."""

from __future__ import annotations

import sys

import pytest

from versa_note.clipboard import (
    build_cf_html,
    get_windows_clipboard_html,
    set_windows_clipboard_text_and_html,
)


def test_set_windows_clipboard_returns_false_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert set_windows_clipboard_text_and_html("plain", "<b>x</b>") is False


def test_get_windows_clipboard_html_returns_none_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert get_windows_clipboard_html() is None


def test_build_cf_html_round_trips_fragment_bytes() -> None:
    fragment = '<td>A&amp;B</td>'
    raw = build_cf_html(fragment)
    text = raw.decode("utf-8")
    start = text.index("<!--StartFragment-->") + len("<!--StartFragment-->")
    end = text.index("<!--EndFragment-->")
    assert text[start:end] == fragment
