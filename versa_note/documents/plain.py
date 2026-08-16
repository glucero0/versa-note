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
from versa_note.transforms import apply_caps_to_text_widget


class PlainTextDocument(Document):
    note_type = "plain"
    default_extension = ".txt"
    filetypes = [("Text files", "*.txt"), ("All files", "*.*")]

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
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
        self.text.configure(yscrollcommand=yscroll.set)

        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        self.text.bind("<<Modified>>", self._on_modified)
        self.bind_edit_shortcuts()

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

    def apply_caps_transform(self, transform: Callable[[str], str]) -> bool:
        if apply_caps_to_text_widget(self.text, transform):
            self.mark_dirty()
            return True
        return False

    def edit_cut(self) -> bool:
        return text_widget_edit_cut(self.text, self)

    def edit_copy(self) -> bool:
        return text_widget_edit_copy(self.text, self)

    def edit_paste(self) -> bool:
        return text_widget_edit_paste(self.text, self)
