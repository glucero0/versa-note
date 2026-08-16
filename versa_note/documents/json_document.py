"""JSON source document with syntax coloring."""

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
from versa_note.json_format import json_error_message, minify_json, prettify_json
from versa_note.transforms import apply_caps_to_text_widget


class JsonDocument(Document):
    note_type = "json"
    default_extension = ".json"
    filetypes = [("JSON files", "*.json"), ("All files", "*.*")]

    TAG_STYLES = {
        "key": {"foreground": "#0550AE"},
        "string": {"foreground": "#0A3069"},
        "number": {"foreground": "#116329"},
        "keyword": {"foreground": "#CF222E"},
        "punct": {"foreground": "#6E7781"},
    }

    # Tokenize strings first so keys/numbers/keywords are not matched inside them.
    _STRING = re.compile(r'"(?:\\.|[^"\\])*"')
    _NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")
    _KEYWORD = re.compile(r"\b(?:true|false|null)\b")
    _PUNCT = re.compile(r"[{}\[\]:,]")
    _KEY = re.compile(r'("(?:\\.|[^"\\])*")\s*:')

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
            foreground="#1F2328",
            background="#FFFFFF",
            insertbackground="#1F2328",
        )
        yscroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=yscroll.set)

        for tag, style in self.TAG_STYLES.items():
            self.text.tag_configure(tag, **style)

        self.text.tag_raise("key")
        self.text.tag_raise("sel")

        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<KeyRelease>", self._schedule_highlight)
        self._highlight_job: Optional[str] = None
        self._parse_error: Optional[str] = None
        self._parsed = False
        self.bind_edit_shortcuts()

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

    def _tag_range(self, tag: str, start: int, end: int) -> None:
        self.text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")

    def _highlight(self) -> None:
        self._highlight_job = None
        content = self.text.get("1.0", "end-1c")
        for tag in self.TAG_STYLES:
            self.text.tag_remove(tag, "1.0", "end")

        # Mark string spans so other tokens skip them.
        string_spans: list[tuple[int, int]] = []
        for match in self._STRING.finditer(content):
            string_spans.append((match.start(), match.end()))
            self._tag_range("string", match.start(), match.end())

        for match in self._KEY.finditer(content):
            self._tag_range("key", match.start(1), match.end(1))

        def in_string(pos: int) -> bool:
            return any(start <= pos < end for start, end in string_spans)

        for match in self._NUMBER.finditer(content):
            if not in_string(match.start()):
                self._tag_range("number", match.start(), match.end())

        for match in self._KEYWORD.finditer(content):
            if not in_string(match.start()):
                self._tag_range("keyword", match.start(), match.end())

        for match in self._PUNCT.finditer(content):
            if not in_string(match.start()):
                self._tag_range("punct", match.start(), match.end())

        self._parse_error = json_error_message(content)
        self._parsed = True
        self.event_generate("<<JsonStatusChanged>>", when="tail")

    def status_validity(self) -> str:
        """Human-readable validity for the status bar (`valid` or `invalid: …`)."""
        if not self._parsed:
            self._parse_error = json_error_message(self.get_content())
            self._parsed = True
        if self._parse_error is None:
            return "valid"
        return f"invalid: {self._parse_error}"

    def get_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_content(self, content: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_modified(False)
        self.mark_clean()
        self._highlight()

    def _replace_content(self, content: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.mark_set("insert", "1.0")
        self.text.see("1.0")
        self.text.edit_modified(False)
        self.mark_dirty()
        self._highlight()

    def prettify(self) -> bool:
        result = prettify_json(self.get_content())
        if result is None:
            return False
        if result == self.get_content():
            self._parse_error = None
            self._parsed = True
            return True
        self._replace_content(result)
        return True

    def minify(self) -> bool:
        result = minify_json(self.get_content())
        if result is None:
            return False
        if result == self.get_content():
            self._parse_error = None
            self._parsed = True
            return True
        self._replace_content(result)
        return True

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
