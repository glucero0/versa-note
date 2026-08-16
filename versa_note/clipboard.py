"""Clipboard helpers (Windows HTML Format + plain text for Google Docs/Sheets)."""

from __future__ import annotations

import csv
import html
import io
import re
import sys
from html.parser import HTMLParser
from typing import Optional


def build_html_table(rows: list[list[str]]) -> str:
    lines = ["<table>", "<tbody>"]
    for row in rows:
        lines.append("<tr>")
        for cell in row:
            lines.append(f"<td>{html.escape(cell)}</td>")
        lines.append("</tr>")
    lines.extend(["</tbody>", "</table>"])
    return "".join(lines)


def build_cf_html(fragment_html: str) -> bytes:
    """Build a Windows CF_HTML payload (UTF-8) around an HTML fragment."""
    header_template = (
        "Version:0.9\r\n"
        "StartHTML:{0:08d}\r\n"
        "EndHTML:{1:08d}\r\n"
        "StartFragment:{2:08d}\r\n"
        "EndFragment:{3:08d}\r\n"
    )
    prefix = "<html>\r\n<body>\r\n<!--StartFragment-->"
    suffix = "<!--EndFragment-->\r\n</body>\r\n</html>"
    header_len = len(header_template.format(0, 0, 0, 0).encode("utf-8"))
    prefix_bytes = prefix.encode("utf-8")
    fragment_bytes = fragment_html.encode("utf-8")
    suffix_bytes = suffix.encode("utf-8")
    start_html = header_len
    start_fragment = start_html + len(prefix_bytes)
    end_fragment = start_fragment + len(fragment_bytes)
    end_html = end_fragment + len(suffix_bytes)
    header = header_template.format(start_html, end_html, start_fragment, end_fragment).encode("utf-8")
    return header + prefix_bytes + fragment_bytes + suffix_bytes


def set_windows_clipboard_text_and_html(plain_text: str, html_fragment: str) -> bool:
    """Place text/plain and text/html (CF_HTML) on the Windows clipboard."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterClipboardFormatW.restype = wintypes.UINT

    html_format = user32.RegisterClipboardFormatW("HTML Format")
    if not html_format:
        return False

    text_bytes = plain_text.encode("utf-16-le") + b"\x00\x00"
    html_bytes = build_cf_html(html_fragment) + b"\x00"

    def _set_format(fmt: int, data: bytes) -> bool:
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not handle:
            return False
        locked = kernel32.GlobalLock(handle)
        if not locked:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(locked, data, len(data))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(fmt, handle):
            kernel32.GlobalFree(handle)
            return False
        return True

    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        if not _set_format(CF_UNICODETEXT, text_bytes):
            return False
        if not _set_format(html_format, html_bytes):
            return False
        return True
    finally:
        user32.CloseClipboard()


def get_windows_clipboard_html() -> Optional[str]:
    """Return the HTML fragment from the Windows HTML Format clipboard, if any."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterClipboardFormatW.restype = wintypes.UINT
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.restype = ctypes.c_size_t

    html_format = user32.RegisterClipboardFormatW("HTML Format")
    if not html_format or not user32.IsClipboardFormatAvailable(html_format):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(html_format)
        if not handle:
            return None
        locked = kernel32.GlobalLock(handle)
        if not locked:
            return None
        try:
            size = kernel32.GlobalSize(handle)
            raw = ctypes.string_at(locked, size)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()

    raw = raw.split(b"\x00", 1)[0]
    try:
        payload = raw.decode("utf-8")
    except UnicodeDecodeError:
        payload = raw.decode("utf-8", errors="replace")

    start_marker = "<!--StartFragment-->"
    end_marker = "<!--EndFragment-->"
    if start_marker in payload and end_marker in payload:
        start = payload.index(start_marker) + len(start_marker)
        end = payload.index(end_marker)
        return payload[start:end].strip()

    def _offset(name: str) -> Optional[int]:
        match = re.search(rf"{name}:\s*(-?\d+)", payload)
        if not match:
            return None
        value = int(match.group(1))
        return None if value < 0 else value

    start_fragment = _offset("StartFragment")
    end_fragment = _offset("EndFragment")
    if start_fragment is not None and end_fragment is not None and end_fragment >= start_fragment:
        return raw[start_fragment:end_fragment].decode("utf-8", errors="replace").strip()
    return None


class _HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: Optional[list[str]] = None
        self._cell: Optional[str] = None
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._in_cell = True
            self._cell = ""

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append(self._cell)
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._in_cell and self._cell is not None:
            self._cell += data


def parse_html_table(html_text: str) -> Optional[list[list[str]]]:
    if "<table" not in html_text.lower():
        return None
    parser = _HTMLTableParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:
        return None
    if not parser.rows:
        return None
    width = max((len(row) for row in parser.rows), default=0)
    return [row + [""] * (width - len(row)) for row in parser.rows]


def parse_clipboard_grid(clip: str) -> list[list[str]]:
    """Parse TSV or CSV clipboard text into a row/column matrix."""
    if clip == "":
        return [[""]]
    normalized = clip.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.endswith("\n"):
        normalized = normalized[:-1]
    if "\t" in normalized:
        return [line.split("\t") for line in normalized.split("\n")]
    rows = list(csv.reader(io.StringIO(normalized)))
    return rows or [[normalized]]
