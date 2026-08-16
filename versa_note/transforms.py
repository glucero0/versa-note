"""Text transform helpers (caps, etc.)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


def caps_upper(text: str) -> str:
    return text.upper()


def caps_lower(text: str) -> str:
    return text.lower()


def caps_initial(text: str) -> str:
    """Capitalize the first letter of each sentence; lower-case the rest."""
    if not text:
        return text
    chars = list(text.lower())
    capitalize = True
    for i, ch in enumerate(chars):
        if ch.isalpha():
            if capitalize:
                chars[i] = ch.upper()
                capitalize = False
        elif ch in ".!?" or ch == "\n":
            capitalize = True
    return "".join(chars)


def caps_sentence(text: str) -> str:
    """Capitalize the first letter of every word (title case)."""
    if not text:
        return text
    chars = list(text.lower())
    capitalize = True
    for i, ch in enumerate(chars):
        if ch.isalpha():
            if capitalize:
                chars[i] = ch.upper()
                capitalize = False
        else:
            # New word after any non-letter (space, hyphen, punctuation, etc.)
            capitalize = True
    return "".join(chars)


CAPS_TRANSFORMS: dict[str, Callable[[str], str]] = {
    "upper": caps_upper,
    "lower": caps_lower,
    "initial": caps_initial,
    "sentence": caps_sentence,
}


def apply_caps_to_text_widget(text: tk.Text, transform: Callable[[str], str]) -> bool:
    try:
        start = text.index("sel.first")
        end = text.index("sel.last")
    except tk.TclError:
        return False
    original = text.get(start, end)
    converted = transform(original)
    text.delete(start, end)
    text.insert(start, converted)
    text.mark_set("insert", start)
    text.tag_add("sel", start, f"{start}+{len(converted)}c")
    text.see(start)
    return True
