"""Markdown source document with syntax coloring."""

from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Optional

from versa_note.documents.base import (
    Document,
    text_widget_edit_copy,
    text_widget_edit_cut,
    text_widget_edit_paste,
)
from versa_note.line_numbers import LineNumberGutter
from versa_note.transforms import apply_caps_to_text_widget


class MarkdownDocument(Document):
    note_type = "markdown"
    default_extension = ".md"
    filetypes = [("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]

    TAG_STYLES = {
        "heading": {"foreground": "#0550AE", "font": ("Consolas", 11, "bold")},
        "bold": {"foreground": "#CF222E"},
        "italic": {"foreground": "#8250DF"},
        "code": {"foreground": "#0A3069", "background": "#F6F8FA"},
        "codeblock": {"foreground": "#0A3069", "background": "#F6F8FA"},
        "link": {"foreground": "#0969DA", "underline": True},
        "list": {"foreground": "#1A7F37"},
        "quote": {"foreground": "#6E7781"},
        "hr": {"foreground": "#8C959F"},
    }

    PATTERNS: list[tuple[str, re.Pattern[str]]] = [
        ("hr", re.compile(r"(?m)^(?:-{3,}|\*{3,}|_{3,})\s*$")),
        ("heading", re.compile(r"(?m)^#{1,6}\s+.*$")),
        ("quote", re.compile(r"(?m)^>\s?.*$")),
        ("list", re.compile(r"(?m)^(?:\s*[-*+]|\s*\d+\.)\s+")),
        ("codeblock", re.compile(r"(?s)```.*?```")),
        ("code", re.compile(r"`[^`\n]+`")),
        ("link", re.compile(r"\[[^\]]+\]\([^)]+\)|https?://\S+")),
        ("bold", re.compile(r"(\*\*|__)(?!\s)(.+?)(?<!\s)\1")),
        ("italic", re.compile(r"(?<!\*)\*(?!\*| )([^*\n]+?)(?<! )\*(?!\*)|(?<!_)_(?!_| )([^_\n]+?)(?<! )_(?!_)")),
    ]

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
            foreground="#1F2328",
            background="#FFFFFF",
            insertbackground="#1F2328",
        )
        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)

        for tag, style in self.TAG_STYLES.items():
            self.text.tag_configure(tag, **style)

        self.text.tag_raise("sel")

        self.line_numbers = LineNumberGutter(self, self.text)
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        yscroll.grid(row=0, column=2, sticky="ns")
        self.line_numbers.attach(yscroll=yscroll)

        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<KeyRelease>", self._schedule_highlight)
        self._highlight_job: Optional[str] = None
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

    def _schedule_highlight(self, _event=None) -> None:
        if self._highlight_job is not None:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(80, self._highlight)

    def _highlight(self) -> None:
        self._highlight_job = None
        content = self.text.get("1.0", "end-1c")
        for tag in self.TAG_STYLES:
            self.text.tag_remove(tag, "1.0", "end")

        for tag, pattern in self.PATTERNS:
            for match in pattern.finditer(content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text.tag_add(tag, start, end)
        self.line_numbers.redraw()

    def get_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_content(self, content: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_modified(False)
        self._highlight()
        self.mark_clean()

    def apply_caps_transform(self, transform: Callable[[str], str]) -> bool:
        if apply_caps_to_text_widget(self.text, transform):
            self.mark_dirty()
            self._highlight()
            return True
        return False

    def edit_cut(self) -> bool:
        if text_widget_edit_cut(self.text, self):
            self._highlight()
            return True
        return False

    def edit_copy(self) -> bool:
        return text_widget_edit_copy(self.text, self)

    def edit_paste(self) -> bool:
        if text_widget_edit_paste(self.text, self):
            self._highlight()
            return True
        return False
