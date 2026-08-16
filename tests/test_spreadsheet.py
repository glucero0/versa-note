"""Spreadsheet helper and CSV content tests."""

from __future__ import annotations

import pytest

from versa_note.constants import DEFAULT_COLS, DEFAULT_ROWS
from versa_note.documents.spreadsheet import (
    SpreadsheetDocument,
    column_header_label,
    pad_matrix,
)


@pytest.mark.parametrize(
    ("col", "expected"),
    [
        (0, "A"),
        (25, "Z"),
        (26, "AA"),
        (27, "AB"),
        (51, "AZ"),
        (52, "BA"),
    ],
)
def test_column_header_label(col: int, expected: str) -> None:
    assert column_header_label(col) == expected


def test_pad_matrix_grows_and_truncates() -> None:
    assert pad_matrix([["a", "b", "c"]], rows=2, cols=2) == [["a", "b"], ["", ""]]
    assert pad_matrix([], rows=1, cols=3) == [["", "", ""]]


def test_csv_round_trip_trims_trailing_empties(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        doc.set_content("name,age\nAda,36\n")
        assert doc.rows >= DEFAULT_ROWS
        assert doc.cols >= DEFAULT_COLS
        # Trailing empty grid rows/cols are trimmed on save
        assert doc.get_content() == "name,age\nAda,36\n"
        assert not doc.dirty
    finally:
        doc.destroy()


def test_csv_quoted_fields_and_commas(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        raw = 'a,"b,c",d\n1,2,3\n'
        doc.set_content(raw)
        assert doc.cells[0][0].get() == "a"
        assert doc.cells[0][1].get() == "b,c"
        assert doc.cells[0][2].get() == "d"
        assert doc.get_content() == raw
    finally:
        doc.destroy()


def test_empty_csv_resets_to_defaults(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        doc.set_content("a,b\n1,2\n")
        doc.set_content("")
        assert doc.rows == DEFAULT_ROWS
        assert doc.cols == DEFAULT_COLS
        assert doc.get_content() == ""
    finally:
        doc.destroy()


def test_insert_and_delete_rows(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        doc.set_content("a\nb\n")
        before = doc.rows
        doc._insert_rows(1, count=1)
        assert doc.rows == before + 1
        assert doc.cells[1][0].get() == ""
        assert doc.cells[2][0].get() == "b"
        doc._delete_rows(1, 1)
        assert doc.rows == before
        assert doc.cells[1][0].get() == "b"
    finally:
        doc.destroy()


def test_insert_and_delete_cols(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        doc.set_content("a,b\n")
        before = doc.cols
        doc._insert_cols(1, count=1)
        assert doc.cols == before + 1
        assert doc.cells[0][1].get() == ""
        assert doc.cells[0][2].get() == "b"
        doc._delete_cols(1, 1)
        assert doc.cols == before
        assert doc.cells[0][1].get() == "b"
    finally:
        doc.destroy()


def test_parse_clipboard_grid_via_module() -> None:
    from versa_note.clipboard import parse_clipboard_grid

    assert parse_clipboard_grid("x\ty") == [["x", "y"]]
