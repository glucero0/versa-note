"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from versa_note.app import VersaNoteApp
from versa_note.documents.base import Document


def _clear_tabs(application: VersaNoteApp) -> None:
    for tab_id in list(application.notebook.tabs()):
        widget = application.notebook.nametowidget(tab_id)
        application.notebook.forget(widget)
        widget.destroy()


@pytest.fixture(scope="session")
def tk_root(tmp_path_factory: pytest.TempPathFactory) -> Iterator[VersaNoteApp]:
    """
    One VersaNoteApp (Tk) for the whole process.

    Windows Tcl is unreliable with multiple Tk() instances, so document widgets
    and app-level tests share this single root.
    """
    base = tmp_path_factory.mktemp("versa_session")
    previous = Path.cwd()
    os.chdir(base)
    application = VersaNoteApp()
    application.withdraw()
    application._save_dir = base
    try:
        yield application
    finally:
        try:
            application.destroy()
        except Exception:
            pass
        os.chdir(previous)


@pytest.fixture
def app(tk_root: VersaNoteApp, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[VersaNoteApp]:
    """Fresh save directory and a single blank plain tab on the shared app."""
    monkeypatch.chdir(tmp_path)
    tk_root._save_dir = tmp_path
    _clear_tabs(tk_root)
    tk_root.new_document("plain")
    try:
        yield tk_root
    finally:
        _clear_tabs(tk_root)
        for child in list(tk_root.winfo_children()):
            # Drop stray document frames created by unit tests as direct children
            if isinstance(child, Document) and child not in [
                tk_root.notebook.nametowidget(t) for t in tk_root.notebook.tabs()
            ]:
                try:
                    child.destroy()
                except Exception:
                    pass
