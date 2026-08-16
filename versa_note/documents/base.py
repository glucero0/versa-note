"""Base document pane and shared text-edit helpers."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk
from typing import Optional

from versa_note.constants import NEW_STEM


class Document(ttk.Frame):
    """Base document pane."""

    note_type: str = "plain"
    default_extension: str = ".txt"
    filetypes: list[tuple[str, str]] = [("Text files", "*.txt"), ("All files", "*.*")]

    def __init__(self, master: tk.Misc, *, untitled_stem: str = NEW_STEM, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.path: Optional[Path] = None
        self.untitled_stem = untitled_stem
        self._dirty = False
        self._build()

    def _build(self) -> None:
        raise NotImplementedError

    def get_content(self) -> str:
        raise NotImplementedError

    def set_content(self, content: str) -> None:
        raise NotImplementedError

    def is_empty(self) -> bool:
        return not self.get_content().strip()

    def mark_dirty(self, *_args) -> None:
        self._dirty = True
        self.event_generate("<<DocumentDirty>>", when="tail")

    def mark_clean(self) -> None:
        self._dirty = False

    @property
    def dirty(self) -> bool:
        return self._dirty

    def base_name(self) -> str:
        if self.path:
            return self.path.name
        return f"{self.untitled_stem}{self.default_extension}"

    def display_name(self) -> str:
        return f"{self.base_name()}{' *' if self._dirty else ''}"

    def apply_caps_transform(self, transform: Callable[[str], str]) -> bool:
        """Apply a caps transform to the current selection. Returns True if anything changed."""
        return False

    def edit_cut(self) -> bool:
        return False

    def edit_copy(self) -> bool:
        return False

    def edit_paste(self) -> bool:
        return False

    def bind_edit_shortcuts(self) -> None:
        """Bind Ctrl+X/C/V on editor widgets so they run before class defaults."""

    def set_line_numbers_visible(self, visible: bool) -> None:
        """Show or hide line numbers when supported. Default: no-op."""

    def supports_line_numbers(self) -> bool:
        return False

    def editor_status_text(self) -> str:
        """Lower-right status: FORMAT\\tLen: n\\tLines: n\\tLn: n\\tCol: n."""
        return ""

    def bind_caret_status(self, callback) -> None:
        """Invoke callback when caret/selection metrics may have changed."""

    def _shortcut_cut(self, _event=None) -> str:
        self.edit_cut()
        return "break"

    def _shortcut_copy(self, _event=None) -> str:
        self.edit_copy()
        return "break"

    def _shortcut_paste(self, _event=None) -> str:
        self.edit_paste()
        return "break"

    def _set_clipboard(self, text: str) -> None:
        root = self.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update_idletasks()

    def _get_clipboard(self) -> Optional[str]:
        try:
            return self.winfo_toplevel().clipboard_get()
        except tk.TclError:
            return None


def text_widget_edit_copy(text: tk.Text, doc: Document) -> bool:
    try:
        selected = text.get("sel.first", "sel.last")
    except tk.TclError:
        return False
    doc._set_clipboard(selected)
    return True


def text_widget_edit_cut(text: tk.Text, doc: Document) -> bool:
    if not text_widget_edit_copy(text, doc):
        return False
    text.delete("sel.first", "sel.last")
    doc.mark_dirty()
    return True


def text_widget_edit_paste(text: tk.Text, doc: Document) -> bool:
    clip = doc._get_clipboard()
    if clip is None:
        return False
    try:
        text.delete("sel.first", "sel.last")
    except tk.TclError:
        pass
    text.insert("insert", clip)
    doc.mark_dirty()
    return True


def format_editor_status(*, fmt: str, length: int, lines: int, line: int, column: int) -> str:
    """Build the lower-right status strip (tab-separated fields)."""
    return f"{fmt}\tLen: {length}\tLines: {lines}\tLn: {line}\tCol: {column}"


def text_widget_editor_status(text: tk.Text, fmt: str) -> str:
    content = text.get("1.0", "end-1c")
    length = len(content)
    lines = int(float(text.index("end-1c")))
    line_s, col_s = str(text.index("insert")).split(".", 1)
    # Tk columns are 0-based; show 1-based like common editors
    return format_editor_status(
        fmt=fmt,
        length=length,
        lines=lines,
        line=int(line_s),
        column=int(col_s) + 1,
    )


def bind_text_caret_status(text: tk.Text, callback) -> None:
    for sequence in (
        "<KeyRelease>",
        "<ButtonRelease-1>",
        "<FocusIn>",
        "<<Modified>>",
        "<Control-v>",
        "<Control-x>",
        "<Control-z>",
        "<Control-y>",
    ):
        text.bind(sequence, lambda e, cb=callback: cb(), add="+")
