"""Document content contract tests (requires tkinter)."""

from __future__ import annotations

import pytest

from versa_note.documents.registry import DOC_TYPES
from versa_note.json_format import prettify_json


TEXT_TYPES = ["plain", "markdown", "json"]


@pytest.fixture(params=TEXT_TYPES)
def text_doc(tk_root, request):
    doc = DOC_TYPES[request.param](tk_root)
    yield doc
    doc.destroy()


@pytest.mark.parametrize("note_type", TEXT_TYPES)
def test_text_round_trip_preserves_content(tk_root, note_type: str) -> None:
    doc = DOC_TYPES[note_type](tk_root)
    try:
        sample = "Hello\nWorld 123\n"
        doc.set_content(sample)
        assert doc.get_content() == sample
        assert not doc.dirty
    finally:
        doc.destroy()


def test_plain_and_markdown_is_empty(tk_root) -> None:
    for note_type in ("plain", "markdown"):
        doc = DOC_TYPES[note_type](tk_root)
        try:
            assert doc.is_empty()
            doc.set_content("   \n  ")
            assert doc.is_empty()
            doc.set_content("0")
            assert not doc.is_empty()
        finally:
            doc.destroy()


def test_display_name_dirty_and_path(tk_root, tmp_path) -> None:
    from pathlib import Path

    doc = DOC_TYPES["plain"](tk_root, untitled_stem="New")
    try:
        assert doc.base_name() == "New.txt"
        assert doc.display_name() == "New.txt"
        doc.set_content("x")
        doc.mark_dirty()
        assert doc.display_name() == "New.txt *"
        path = tmp_path / "note.txt"
        doc.path = path
        doc.mark_clean()
        assert doc.base_name() == "note.txt"
        assert doc.display_name() == "note.txt"
    finally:
        doc.destroy()


def test_line_numbers_toggle_on_text_docs(text_doc) -> None:
    assert text_doc.supports_line_numbers()
    text_doc.set_line_numbers_visible(False)
    assert not text_doc.line_numbers.visible
    text_doc.set_line_numbers_visible(True)
    assert text_doc.line_numbers.visible


def test_spreadsheet_does_not_support_line_numbers(tk_root) -> None:
    doc = DOC_TYPES["spreadsheet"](tk_root)
    try:
        assert not doc.supports_line_numbers()
        doc.set_line_numbers_visible(True)  # no-op
    finally:
        doc.destroy()


def test_json_prettify_and_minify(tk_root) -> None:
    doc = DOC_TYPES["json"](tk_root)
    try:
        doc.set_content('{"a":1}')
        assert doc.prettify()
        assert doc.get_content() == prettify_json('{"a":1}')
        assert doc.minify()
        assert doc.get_content() == '{"a":1}'
        doc.set_content("{")
        assert not doc.prettify()
        assert doc.status_validity().startswith("invalid:")
    finally:
        doc.destroy()


def test_markdown_highlight_patterns_match_common_constructs() -> None:
    from versa_note.documents.markdown import MarkdownDocument

    sample = "# Title\n\n**bold** and *italic*\n\n- item\n\n`code`\n\n```\nblock\n```\n"
    tags = {tag for tag, pattern in MarkdownDocument.PATTERNS if pattern.search(sample)}
    assert "heading" in tags
    assert "bold" in tags
    assert "italic" in tags
    assert "list" in tags
    assert "code" in tags
    assert "codeblock" in tags
