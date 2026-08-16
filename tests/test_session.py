"""Session path, naming, and restore tests."""

from __future__ import annotations

import json
from pathlib import Path

from versa_note.constants import NEW_STEM, SESSION_FILENAME
from versa_note.documents.registry import DOC_TYPES


def test_path_for_session_relative(app, tmp_path: Path) -> None:
    app._save_dir = tmp_path
    inside = tmp_path / "notes" / "a.txt"
    inside.parent.mkdir()
    inside.write_text("hi", encoding="utf-8")
    rel = app._path_for_session(inside).replace("\\", "/")
    assert rel == "notes/a.txt"


def test_path_for_session_absolute_outside(app, tmp_path: Path) -> None:
    app._save_dir = tmp_path
    outside = tmp_path.parent / f"versa-note-outside-{tmp_path.name}.txt"
    outside.write_text("x", encoding="utf-8")
    try:
        stored = app._path_for_session(outside)
        assert Path(stored).is_absolute()
        assert outside.name in stored
    finally:
        outside.unlink(missing_ok=True)


def test_resolve_session_path_variants(app, tmp_path: Path) -> None:
    app._save_dir = tmp_path
    target = tmp_path / "tab.txt"
    target.write_text("body", encoding="utf-8")

    assert app._resolve_session_path("tab.txt").resolve() == target.resolve()
    assert app._resolve_session_path(str(Path("nested") / "tab.txt")).resolve() == target.resolve()
    assert app._resolve_session_path(str(target.resolve())).resolve() == target.resolve()


def test_next_new_stem_avoids_disk(app, tmp_path: Path) -> None:
    app._save_dir = tmp_path
    (tmp_path / f"{NEW_STEM}.txt").write_text("x", encoding="utf-8")
    (tmp_path / f"{NEW_STEM} - 1.md").write_text("x", encoding="utf-8")
    used = app._used_new_stems()
    assert NEW_STEM in used
    assert f"{NEW_STEM} - 1" in used
    stem = app._next_new_stem()
    assert stem not in used


def test_default_path_for_picks_free_name(app, tmp_path: Path) -> None:
    app._save_dir = tmp_path
    (tmp_path / "New.txt").write_text("taken", encoding="utf-8")
    doc = DOC_TYPES["plain"](app.notebook, untitled_stem="New")
    try:
        path = app._default_path_for(doc, reserved=set())
        assert path.name == "New - 1.txt"
        assert not path.exists()
    finally:
        doc.destroy()


def test_write_and_restore_session(app, tmp_path: Path) -> None:
    app._save_dir = tmp_path
    note = tmp_path / "saved.md"
    note.write_text("# hi\n", encoding="utf-8")
    doc = app._open_path(note)
    assert doc is not None
    app._write_session()

    session_file = tmp_path / SESSION_FILENAME
    assert session_file.is_file()
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert any("saved.md" in tab.replace("\\", "/") for tab in payload["tabs"])

    # Clear tabs and restore in-process (avoid a second Tk() on Windows)
    for tab_id in list(app.notebook.tabs()):
        widget = app.notebook.nametowidget(tab_id)
        app.notebook.forget(widget)
        widget.destroy()

    assert app._restore_session()
    docs = app._all_documents()
    assert any(d.path and d.path.name == "saved.md" for d in docs)
    current = app.current_document()
    assert current is not None
    assert current.get_content() == "# hi\n"


def test_find_tab_for_path_dedupes(app, tmp_path: Path) -> None:
    app._save_dir = tmp_path
    note = tmp_path / "once.txt"
    note.write_text("one", encoding="utf-8")
    first = app._open_path(note)
    second = app._open_path(note)
    assert first is second
    assert sum(1 for d in app._all_documents() if d.path and d.path.resolve() == note.resolve()) == 1
