"""Spreadsheet clipboard, paste, and structure UI tests."""

from __future__ import annotations

from versa_note.clipboard import build_html_table
from versa_note.documents.spreadsheet import SpreadsheetDocument


def _fill(doc: SpreadsheetDocument, matrix: list[list[str]]) -> None:
    for r, row in enumerate(matrix):
        for c, value in enumerate(row):
            doc.cells[r][c].delete(0, "end")
            doc.cells[r][c].insert(0, value)


def test_copy_selection_as_tsv_fallback(tk_root, monkeypatch) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        monkeypatch.setattr(
            "versa_note.documents.spreadsheet.set_windows_clipboard_text_and_html",
            lambda *a, **k: False,
        )
        _fill(doc, [["a", "b"], ["c", "d"]])
        doc._set_selection(0, 0, 1, 1)
        assert doc.edit_copy()
        clip = doc._get_clipboard()
        assert clip is not None
        assert "a\tb" in clip.replace("\r\n", "\n")
        assert "c\td" in clip.replace("\r\n", "\n")
    finally:
        doc.destroy()


def test_copy_partial_cell_selection_is_plain_text(tk_root, monkeypatch) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        monkeypatch.setattr(
            "versa_note.documents.spreadsheet.set_windows_clipboard_text_and_html",
            lambda *a, **k: False,
        )
        entry = doc.cells[0][0]
        entry.insert(0, "abcdef")
        entry.selection_range(1, 4)  # bcd
        doc._set_selection(0, 0, 0, 0)
        assert doc.edit_copy()
        assert doc._get_clipboard() == "bcd"
    finally:
        doc.destroy()


def test_paste_tsv_grid_expands_and_fills(tk_root, monkeypatch) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        monkeypatch.setattr(
            "versa_note.documents.spreadsheet.get_windows_clipboard_html",
            lambda: None,
        )
        doc._set_clipboard("x\ty\r\nz\tw")
        doc._set_selection(0, 0, 0, 0)
        assert doc.edit_paste()
        assert doc.cells[0][0].get() == "x"
        assert doc.cells[0][1].get() == "y"
        assert doc.cells[1][0].get() == "z"
        assert doc.cells[1][1].get() == "w"
    finally:
        doc.destroy()


def test_paste_html_table_from_windows_clipboard(tk_root, monkeypatch) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        html = build_html_table([["h1", "h2"], ["1", "2"]])
        monkeypatch.setattr(
            "versa_note.documents.spreadsheet.get_windows_clipboard_html",
            lambda: html,
        )
        doc._set_selection(0, 0, 0, 0)
        assert doc.edit_paste()
        assert doc.cells[0][0].get() == "h1"
        assert doc.cells[0][1].get() == "h2"
        assert doc.cells[1][0].get() == "1"
        assert doc.cells[1][1].get() == "2"
    finally:
        doc.destroy()


def test_paste_scalar_into_single_cell(tk_root, monkeypatch) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        monkeypatch.setattr(
            "versa_note.documents.spreadsheet.get_windows_clipboard_html",
            lambda: None,
        )
        entry = doc.cells[0][0]
        entry.insert(0, "ab")
        entry.icursor(1)
        entry.selection_clear()
        doc._set_clipboard("X")
        doc._set_selection(0, 0, 0, 0)
        assert doc.edit_paste()
        assert "X" in entry.get()
    finally:
        doc.destroy()


def test_cut_clears_selected_cells(tk_root, monkeypatch) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        monkeypatch.setattr(
            "versa_note.documents.spreadsheet.set_windows_clipboard_text_and_html",
            lambda *a, **k: False,
        )
        _fill(doc, [["a", "b"]])
        doc._set_selection(0, 0, 0, 1)
        assert doc.edit_cut()
        assert doc.cells[0][0].get() == ""
        assert doc.cells[0][1].get() == ""
        assert doc.dirty
    finally:
        doc.destroy()


def test_caps_transform_on_selected_cells(tk_root) -> None:
    from versa_note.transforms import caps_upper

    doc = SpreadsheetDocument(tk_root)
    try:
        _fill(doc, [["ab", "cd"]])
        doc._set_selection(0, 0, 0, 1)
        assert doc.apply_caps_transform(caps_upper)
        assert doc.cells[0][0].get() == "AB"
        assert doc.cells[0][1].get() == "CD"
    finally:
        doc.destroy()


def test_fit_column_grows_for_long_text(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        before = doc.col_widths[0]
        doc.cells[0][0].insert(0, "this is a much longer cell value than default")
        doc._fit_column(0, shrink=False)
        assert doc.col_widths[0] >= before
    finally:
        doc.destroy()


def test_autofit_from_sizer_shrinks_to_content(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        doc.col_widths[0] = 400
        doc.cells[0][0].insert(0, "hi")
        doc._autofit_from_sizer(0)
        assert doc.col_widths[0] < 400
        assert doc.col_widths[0] >= 72  # MIN_COL_WIDTH
    finally:
        doc.destroy()


def test_structure_menu_builds_for_cell_mode(tk_root) -> None:
    doc = SpreadsheetDocument(tk_root)
    try:
        doc._set_selection(0, 0, 0, 0)

        class FakeEvent:
            x_root = 0
            y_root = 0

        # Avoid actually posting the popup
        doc._context_menu.tk_popup = lambda *a, **k: None  # type: ignore[method-assign]
        doc._context_menu.grab_release = lambda: None  # type: ignore[method-assign]
        doc._show_structure_menu(FakeEvent(), mode="cell")  # type: ignore[arg-type]
        end = doc._context_menu.index("end")
        assert end is not None
        labels = []
        for i in range(int(end) + 1):
            if doc._context_menu.type(i) != "command":
                continue
            labels.append(doc._context_menu.entrycget(i, "label"))
        assert any("Insert Row" in label for label in labels)
        assert any("Insert Column" in label for label in labels)
        assert any(label.startswith("Delete") for label in labels)
    finally:
        doc.destroy()
