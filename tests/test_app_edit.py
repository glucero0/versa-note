"""App-level edit / transform / status wiring tests."""

from __future__ import annotations

from versa_note.documents.plain import PlainTextDocument
from versa_note.documents.registry import DOC_TYPES


def test_app_edit_copy_paste_on_plain(app) -> None:
    doc = app.current_document()
    assert isinstance(doc, PlainTextDocument)
    doc.set_content("xyz")
    doc.text.tag_add("sel", "1.0", "1.2")
    app.edit_copy()
    assert "Copied" in app.status.cget("text")
    doc.text.delete("1.0", "end")
    doc.text.mark_set("insert", "1.0")
    app.edit_paste()
    assert doc.get_content().startswith("xy")


def test_app_apply_caps_upper(app) -> None:
    doc = app.current_document()
    assert isinstance(doc, PlainTextDocument)
    doc.set_content("abc")
    doc.text.tag_add("sel", "1.0", "end-1c")
    app.apply_caps("upper")
    assert doc.get_content() == "ABC"


def test_app_json_actions_enabled_only_for_json(app) -> None:
    assert app._transform_menu.entrycget("Prettify", "state") == "disabled"
    app.new_document("json")
    app._update_json_actions()
    assert app._transform_menu.entrycget("Prettify", "state") == "normal"
    assert app._transform_menu.entrycget("Minify", "state") == "normal"


def test_app_editor_status_populated(app) -> None:
    doc = app.current_document()
    assert doc is not None
    doc.set_content("hi\n")
    app._update_editor_status()
    text = app.editor_status.cget("text")
    assert text.startswith("TXT\t")
    assert "Len:" in text
    assert "Ln:" in text


def test_toggle_line_numbers_applies_to_open_tabs(app) -> None:
    app.new_document("markdown")
    docs = [d for d in app._all_documents() if d.supports_line_numbers()]
    assert docs
    app._show_line_numbers.set(False)
    app._toggle_line_numbers()
    assert all(not d.line_numbers.visible for d in docs)
    app._show_line_numbers.set(True)
    app._toggle_line_numbers()
    assert all(d.line_numbers.visible for d in docs)
