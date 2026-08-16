"""Plain text document."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from versa_note.documents.base import (
    Document,
    text_widget_edit_copy,
    text_widget_edit_cut,
    text_widget_edit_paste,
)
from versa_note.line_numbers import LineNumberGutter
from versa_note.transforms import apply_caps_to_text_widget


class PlainTextDocument(Document):
    note_type = "plain"
    default_extension = ".txt"
    filetypes = [("Text files", "*.txt"), ("All files", "*.*")]

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.text = tk.Text(
            self,
            wrap="word",
            undo=True,
            font=("Consolas", 11),
            padx=8,
            pady=8,
            relief="flat",
            borderwidth=0,
        )
        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)

        self.line_numbers = LineNumberGutter(self, self.text)
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        yscroll.grid(row=0, column=2, sticky="ns")
        self.line_numbers.attach(yscroll=yscroll)

        self.text.bind("<<Modified>>", self._on_modified)
        self.bind_edit_shortcuts()

    def supports_line_numbers(self) -> bool:
        return True

    def set_line_numbers_visible(self, visible: bool) -> None:
        self.line_numbers.set_visible(visible)

    def bind_edit_shortcuts(self) -> None:
        self.text.bind("<Control-x>", self._shortcut_cut)
        self.text.bind("<Control-c>", self._shortcut_copy)
        self.text.bind("<Control-v>", self._shortcut_paste)

    def _on_modified(self, _event=None) -> None:
        if self.text.edit_modified():
            self.mark_dirty()
            self.text.edit_modified(False)

    def get_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_content(self, content: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_modified(False)
        self.mark_clean()
        self.line_numbers.redraw()

    def apply_caps_transform(self, transform: Callable[[str], str]) -> bool:
        if apply_caps_to_text_widget(self.text, transform):
            self.mark_dirty()
            self.line_numbers.redraw()
            return True
        return False

    def edit_cut(self) -> bool:
        if text_widget_edit_cut(self.text, self):
            self.line_numbers.redraw()
            return True
        return False

    def edit_copy(self) -> bool:
        return text_widget_edit_copy(self.text, self)

    def edit_paste(self) -> bool:
        if text_widget_edit_paste(self.text, self):
            self.line_numbers.redraw()
            return True
        return False
