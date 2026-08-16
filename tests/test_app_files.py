"""App file dialog and close-tab flow tests (dialogs mocked)."""

from __future__ import annotations

from pathlib import Path

import pytest

from versa_note.documents.registry import DOC_TYPES


def test_open_document_cancelled(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("versa_note.app.filedialog.askopenfilename", lambda **kwargs: "")
    before = len(app._all_documents())
    app.open_document()
    assert len(app._all_documents()) == before


def test_open_document_loads_file(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    note = tmp_path / "opened.json"
    note.write_text('{"ok": true}\n', encoding="utf-8")
    monkeypatch.setattr("versa_note.app.filedialog.askopenfilename", lambda **kwargs: str(note))
    app.open_document()
    doc = app.current_document()
    assert doc is not None
    assert doc.note_type == "json"
    assert doc.get_content() == '{"ok": true}\n'
    assert doc.path == note


def test_save_document_as_writes_and_sets_path(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    doc = app.current_document()
    assert doc is not None
    doc.set_content("hello save")
    target = tmp_path / "out.txt"
    monkeypatch.setattr("versa_note.app.filedialog.asksaveasfilename", lambda **kwargs: str(target))
    assert app.save_document_as() is True
    assert target.read_text(encoding="utf-8") == "hello save"
    assert doc.path == target
    assert not doc.dirty


def test_save_document_as_adds_default_extension(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    doc = app.current_document()
    assert doc is not None
    doc.set_content("x")
    target = tmp_path / "noext"
    monkeypatch.setattr("versa_note.app.filedialog.asksaveasfilename", lambda **kwargs: str(target))
    assert app.save_document_as() is True
    assert doc.path == tmp_path / "noext.txt"
    assert (tmp_path / "noext.txt").is_file()


def test_save_document_without_path_delegates_to_save_as(
    app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = app.current_document()
    assert doc is not None
    assert doc.path is None
    doc.set_content("via save")
    target = tmp_path / "via-save.txt"
    monkeypatch.setattr("versa_note.app.filedialog.asksaveasfilename", lambda **kwargs: str(target))
    assert app.save_document() is True
    assert target.read_text(encoding="utf-8") == "via save"


def test_close_dirty_named_tab_cancel(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    note = tmp_path / "named.txt"
    note.write_text("orig", encoding="utf-8")
    doc = app._open_path(note)
    assert doc is not None
    doc.set_content("changed")
    doc.mark_dirty()
    monkeypatch.setattr("versa_note.app.messagebox.askyesnocancel", lambda *a, **k: None)
    before = len(app._all_documents())
    app.close_current_tab()
    assert len(app._all_documents()) == before
    assert doc.winfo_exists()
    assert note.read_text(encoding="utf-8") == "orig"


def test_close_dirty_named_tab_yes_saves(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    note = tmp_path / "named2.txt"
    note.write_text("orig", encoding="utf-8")
    doc = app._open_path(note)
    assert doc is not None
    doc.set_content("saved-on-close")
    doc.mark_dirty()
    monkeypatch.setattr("versa_note.app.messagebox.askyesnocancel", lambda *a, **k: True)
    app.close_current_tab()
    assert note.read_text(encoding="utf-8") == "saved-on-close"
    assert not any(d.path and d.path.resolve() == note.resolve() for d in app._all_documents())


def test_close_dirty_named_tab_no_discards(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    note = tmp_path / "named3.txt"
    note.write_text("keep", encoding="utf-8")
    doc = app._open_path(note)
    assert doc is not None
    doc.set_content("discard-me")
    doc.mark_dirty()
    monkeypatch.setattr("versa_note.app.messagebox.askyesnocancel", lambda *a, **k: False)
    app.close_current_tab()
    assert note.read_text(encoding="utf-8") == "keep"


def test_close_unnamed_nonempty_autosaves(app, tmp_path: Path) -> None:
    doc = app.current_document()
    assert doc is not None
    assert doc.path is None
    doc.set_content("autosave body")
    stem = doc.untitled_stem
    app.close_current_tab()
    saved = tmp_path / f"{stem}.txt"
    assert saved.is_file()
    assert saved.read_text(encoding="utf-8") == "autosave body"


def test_close_last_tab_opens_new_plain(app) -> None:
    doc = app.current_document()
    assert doc is not None
    # empty unnamed — no autosave
    app.close_current_tab()
    remaining = app._all_documents()
    assert len(remaining) == 1
    assert remaining[0].note_type == "plain"
    assert remaining[0].path is None
