"""Document type registry and extension resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Type

from versa_note.documents.base import Document
from versa_note.documents.json_document import JsonDocument
from versa_note.documents.markdown import MarkdownDocument
from versa_note.documents.plain import PlainTextDocument
from versa_note.documents.spreadsheet import SpreadsheetDocument

DOC_TYPES: dict[str, Type[Document]] = {
    "plain": PlainTextDocument,
    "markdown": MarkdownDocument,
    "spreadsheet": SpreadsheetDocument,
    "json": JsonDocument,
}

EXT_TO_TYPE: dict[str, str] = {
    ".txt": "plain",
    ".md": "markdown",
    ".markdown": "markdown",
    ".csv": "spreadsheet",
    ".json": "json",
}

SUPPORTED_EXTENSIONS = frozenset(EXT_TO_TYPE.keys())

NOTE_TYPE_LABELS: dict[str, str] = {
    "plain": "Plain text",
    "markdown": "Markdown",
    "spreadsheet": "Spreadsheet",
    "json": "JSON",
}


def resolve_note_type(path: Path) -> str:
    """Return the note type key for a file path based on its extension."""
    return EXT_TO_TYPE.get(path.suffix.lower(), "plain")


def get_document_class(note_type: str) -> Type[Document]:
    """Return the document class for a note type key."""
    return DOC_TYPES[note_type]
