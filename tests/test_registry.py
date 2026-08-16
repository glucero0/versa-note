"""Registry contract tests for note types and extensions."""

from __future__ import annotations

from pathlib import Path

from versa_note.documents.registry import (
    DOC_TYPES,
    EXT_TO_TYPE,
    NOTE_TYPE_LABELS,
    SUPPORTED_EXTENSIONS,
    resolve_note_type,
)


def test_supported_extensions_match_ext_map() -> None:
    assert SUPPORTED_EXTENSIONS == frozenset(EXT_TO_TYPE.keys())


def test_json_registered() -> None:
    assert "json" in DOC_TYPES
    assert DOC_TYPES["json"].note_type == "json"
    assert DOC_TYPES["json"].default_extension == ".json"
    assert EXT_TO_TYPE[".json"] == "json"
    assert NOTE_TYPE_LABELS["json"] == "JSON"


def test_every_doc_type_has_label_and_matching_note_type() -> None:
    for key, cls in DOC_TYPES.items():
        assert cls.note_type == key
        assert key in NOTE_TYPE_LABELS


def test_default_extensions_resolve() -> None:
    for cls in DOC_TYPES.values():
        assert resolve_note_type(Path(f"note{cls.default_extension}")) == cls.note_type


def test_markdown_alias_extension() -> None:
    assert EXT_TO_TYPE[".markdown"] == "markdown"
    assert resolve_note_type(Path("readme.markdown")) == "markdown"


def test_get_document_class() -> None:
    from versa_note.documents.registry import get_document_class

    assert get_document_class("json") is DOC_TYPES["json"]
