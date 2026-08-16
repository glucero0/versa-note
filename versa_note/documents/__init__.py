"""Document panes for Versa Note."""

from versa_note.documents.base import Document
from versa_note.documents.markdown import MarkdownDocument
from versa_note.documents.plain import PlainTextDocument
from versa_note.documents.registry import (
    DOC_TYPES,
    EXT_TO_TYPE,
    NOTE_TYPE_LABELS,
    SUPPORTED_EXTENSIONS,
    get_document_class,
    resolve_note_type,
)
from versa_note.documents.spreadsheet import SpreadsheetDocument

__all__ = [
    "DOC_TYPES",
    "Document",
    "EXT_TO_TYPE",
    "MarkdownDocument",
    "NOTE_TYPE_LABELS",
    "PlainTextDocument",
    "SUPPORTED_EXTENSIONS",
    "SpreadsheetDocument",
    "get_document_class",
    "resolve_note_type",
]
