"""Text widget edit / caps / highlight / line-number tests."""

from __future__ import annotations

from versa_note.documents.json_document import JsonDocument
from versa_note.documents.markdown import MarkdownDocument
from versa_note.documents.plain import PlainTextDocument
from versa_note.transforms import caps_upper


def test_plain_cut_copy_paste(tk_root) -> None:
    doc = PlainTextDocument(tk_root)
    try:
        doc.set_content("abcdef")
        doc.text.tag_add("sel", "1.0", "1.3")
        assert doc.edit_copy()
        assert doc._get_clipboard() == "abc"
        doc.text.tag_add("sel", "1.0", "1.3")
        assert doc.edit_cut()
        assert doc.get_content() == "def"
        doc.text.mark_set("insert", "1.0")
        assert doc.edit_paste()
        assert doc.get_content() == "abcdef"
    finally:
        doc.destroy()


def test_markdown_paste_triggers_content(tk_root) -> None:
    doc = MarkdownDocument(tk_root)
    try:
        doc.set_content("hi")
        doc._set_clipboard(" there")
        doc.text.mark_set("insert", "end-1c")
        assert doc.edit_paste()
        assert "there" in doc.get_content()
    finally:
        doc.destroy()


def test_apply_caps_to_selection(tk_root) -> None:
    doc = PlainTextDocument(tk_root)
    try:
        doc.set_content("hello world")
        doc.text.tag_add("sel", "1.0", "1.5")
        assert doc.apply_caps_transform(caps_upper)
        assert doc.get_content() == "HELLO world"
        assert doc.dirty
    finally:
        doc.destroy()


def test_apply_caps_without_selection_returns_false(tk_root) -> None:
    doc = PlainTextDocument(tk_root)
    try:
        doc.set_content("hello")
        doc.text.tag_remove("sel", "1.0", "end")
        assert not doc.apply_caps_transform(caps_upper)
        assert doc.get_content() == "hello"
    finally:
        doc.destroy()


def test_markdown_highlight_applies_heading_tag(tk_root) -> None:
    doc = MarkdownDocument(tk_root)
    try:
        doc.set_content("# Title\n\nbody\n")
        doc.update_idletasks()
        ranges = doc.text.tag_ranges("heading")
        assert ranges, "expected heading tag ranges"
    finally:
        doc.destroy()


def test_json_highlight_applies_key_and_number_tags(tk_root) -> None:
    doc = JsonDocument(tk_root)
    try:
        doc.set_content('{"n": 42}\n')
        doc.update_idletasks()
        assert doc.text.tag_ranges("key")
        assert doc.text.tag_ranges("number")
    finally:
        doc.destroy()


def test_line_numbers_hide_and_show(tk_root) -> None:
    doc = PlainTextDocument(tk_root)
    try:
        doc.set_content("a\nb\nc\n")
        doc.line_numbers.redraw()
        assert doc.line_numbers.visible
        width_shown = int(doc.line_numbers.cget("width"))
        assert width_shown > 0
        doc.set_line_numbers_visible(False)
        assert not doc.line_numbers.visible
        # grid_remove keeps geometry config; visibility flag is the contract
        doc.set_line_numbers_visible(True)
        assert doc.line_numbers.visible
        doc.line_numbers.redraw()
        assert int(doc.line_numbers.cget("width")) >= width_shown
    finally:
        doc.destroy()


def test_line_numbers_widen_for_many_lines(tk_root) -> None:
    doc = PlainTextDocument(tk_root)
    try:
        doc.set_content("x\n")
        doc.line_numbers.redraw()
        narrow = int(doc.line_numbers.cget("width"))
        doc.set_content("\n".join(str(i) for i in range(1, 120)) + "\n")
        doc.line_numbers.redraw()
        wide = int(doc.line_numbers.cget("width"))
        assert wide >= narrow
    finally:
        doc.destroy()


def test_editor_status_text_updates_with_caret(tk_root) -> None:
    doc = PlainTextDocument(tk_root)
    try:
        doc.set_content("abc\ndef\n")
        doc.text.mark_set("insert", "2.1")
        status = doc.editor_status_text()
        assert status.startswith("TXT\t")
        assert "Ln: 2\t" in status
        assert "Col: 2" in status
        assert "Len: 8" in status
    finally:
        doc.destroy()
