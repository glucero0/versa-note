"""Spreadsheet (CSV grid) document."""

from __future__ import annotations

import csv
import io
import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable
from tkinter import ttk
from typing import Optional

from versa_note.clipboard import (
    build_html_table,
    get_windows_clipboard_html,
    parse_clipboard_grid,
    parse_html_table,
    set_windows_clipboard_text_and_html,
)
from versa_note.constants import (
    CELL_BG,
    CELL_SEL_BG,
    CELL_TEXT_PAD,
    DEFAULT_COLS,
    DEFAULT_COL_WIDTH,
    DEFAULT_ROWS,
    HEADER_BG,
    HEADER_SEL_BG,
    MAX_COL_WIDTH,
    MIN_COL_WIDTH,
    STATUS_FORMAT_LABELS,
)
from versa_note.documents.base import Document, format_editor_status


def column_header_label(col: int) -> str:
    """Excel-style column label: 0→A, 25→Z, 26→AA."""
    name = ""
    n = col
    while True:
        name = chr(ord("A") + (n % 26)) + name
        n = n // 26 - 1
        if n < 0:
            break
    return name


def pad_matrix(values: list[list[str]], rows: int, cols: int) -> list[list[str]]:
    """Pad or truncate a matrix to exactly rows × cols."""
    padded: list[list[str]] = []
    for r in range(rows):
        if r < len(values):
            row = list(values[r])
        else:
            row = []
        if len(row) < cols:
            row.extend([""] * (cols - len(row)))
        else:
            row = row[:cols]
        padded.append(row)
    return padded


class SpreadsheetDocument(Document):
    note_type = "spreadsheet"
    default_extension = ".csv"
    filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]

    def _build(self) -> None:
        self.rows = DEFAULT_ROWS
        self.cols = DEFAULT_COLS
        self.cells: list[list[tk.Entry]] = []
        self.row_labels: list[ttk.Label] = []
        self.col_labels: list[ttk.Label] = []
        self.col_widths: list[int] = [DEFAULT_COL_WIDTH] * self.cols
        self._cell_font = tkfont.Font(family="Segoe UI", size=10)
        self._resize_col: Optional[int] = None
        self._resize_start_x = 0
        self._resize_start_width = 0
        self._sel_anchor: Optional[tuple[int, int]] = None
        self._sel_r1: Optional[int] = None
        self._sel_c1: Optional[int] = None
        self._sel_r2: Optional[int] = None
        self._sel_c2: Optional[int] = None
        self._context_menu = tk.Menu(self, tearoff=0)
        self._caret_status_callback = None

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, highlightthickness=0, background="#F0F0F0")
        self.hbar = ttk.Scrollbar(outer, orient="horizontal", command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        self.vbar.pack(side="right", fill="y")
        self.hbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.grid_frame = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        self.grid_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._rebuild_grid()

    def _on_frame_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        # Keep inner frame at least as wide as the canvas when small
        self.canvas.itemconfigure(self._window, width=max(event.width, self.grid_frame.winfo_reqwidth()))

    def _header_label(self, col: int) -> str:
        return column_header_label(col)

    def _sync_col_widths(self) -> None:
        widths = list(getattr(self, "col_widths", []))
        if len(widths) < self.cols:
            widths.extend([DEFAULT_COL_WIDTH] * (self.cols - len(widths)))
        self.col_widths = widths[: self.cols]

    def _apply_col_widths(self) -> None:
        self.grid_frame.columnconfigure(0, minsize=36)
        for c, width in enumerate(self.col_widths):
            self.grid_frame.columnconfigure(c + 1, minsize=width)
        # Refresh scrollregion after width changes
        self.grid_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _needed_width_for_text(self, text: str) -> int:
        return min(MAX_COL_WIDTH, max(MIN_COL_WIDTH, self._cell_font.measure(text) + CELL_TEXT_PAD))

    def _content_width_for_column(self, col: int) -> int:
        widest = self._needed_width_for_text(self._header_label(col))
        for row in self.cells:
            widest = max(widest, self._needed_width_for_text(row[col].get()))
        return widest

    def _fit_column(self, col: int, *, shrink: bool = False) -> None:
        if col < 0 or col >= self.cols:
            return
        needed = self._content_width_for_column(col)
        if shrink:
            self.col_widths[col] = needed
        elif needed > self.col_widths[col]:
            self.col_widths[col] = needed
        else:
            return
        self._apply_col_widths()

    def _fit_all_columns(self, *, shrink: bool = True) -> None:
        for col in range(self.cols):
            needed = self._content_width_for_column(col)
            if shrink:
                self.col_widths[col] = needed
            else:
                self.col_widths[col] = max(self.col_widths[col], needed)
        self._apply_col_widths()

    def _on_cell_edit(self, col: int, *_args) -> None:
        self.mark_dirty()
        self._fit_column(col, shrink=False)
        self._notify_caret_status()

    def _start_resize(self, event: tk.Event, col: int) -> None:
        self._resize_col = col
        self._resize_start_x = event.x_root
        self._resize_start_width = self.col_widths[col]

    def _do_resize(self, event: tk.Event) -> None:
        if self._resize_col is None:
            return
        delta = event.x_root - self._resize_start_x
        width = max(MIN_COL_WIDTH, min(MAX_COL_WIDTH, self._resize_start_width + delta))
        self.col_widths[self._resize_col] = width
        self._apply_col_widths()

    def _end_resize(self, _event: tk.Event | None = None) -> None:
        self._resize_col = None

    def _autofit_from_sizer(self, col: int, _event: tk.Event | None = None) -> None:
        self._fit_column(col, shrink=True)

    def _make_header(self, col: int) -> None:
        frame = ttk.Frame(self.grid_frame)
        frame.grid(row=0, column=col + 1, sticky="nsew", padx=1, pady=1)
        frame.columnconfigure(0, weight=1)

        label = tk.Label(
            frame,
            text=self._header_label(col),
            anchor="center",
            relief="ridge",
            background=HEADER_BG,
            font=("Segoe UI", 9, "bold"),
        )
        label.grid(row=0, column=0, sticky="nsew")
        label.bind("<Button-1>", lambda e, c=col: self._select_column(c))
        label.bind("<Button-3>", lambda e, c=col: self._on_col_header_context(e, c))
        self.col_labels.append(label)

        sizer = tk.Frame(frame, width=5, cursor="sb_h_double_arrow", background="#B8B8B8", borderwidth=0)
        sizer.grid(row=0, column=1, sticky="ns")
        sizer.bind("<ButtonPress-1>", lambda e, c=col: self._start_resize(e, c))
        sizer.bind("<B1-Motion>", self._do_resize)
        sizer.bind("<ButtonRelease-1>", self._end_resize)
        sizer.bind("<Double-Button-1>", lambda e, c=col: self._autofit_from_sizer(c, e))

    def _clear_selection(self) -> None:
        self._sel_anchor = None
        self._sel_r1 = self._sel_c1 = self._sel_r2 = self._sel_c2 = None
        self._refresh_selection_styles()

    def _set_selection(self, r1: int, c1: int, r2: int, c2: int) -> None:
        self._sel_r1, self._sel_c1, self._sel_r2, self._sel_c2 = r1, c1, r2, c2
        self._refresh_selection_styles()
        self._notify_caret_status()

    def _selected_cells(self) -> list[tuple[int, int]]:
        if self._sel_r1 is None or self._sel_c1 is None or self._sel_r2 is None or self._sel_c2 is None:
            return []
        r1, r2 = sorted((self._sel_r1, self._sel_r2))
        c1, c2 = sorted((self._sel_c1, self._sel_c2))
        return [(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]

    def _refresh_selection_styles(self) -> None:
        selected = set(self._selected_cells())
        selected_rows = {r for r, _ in selected}
        selected_cols = {c for _, c in selected}
        for r, row in enumerate(self.cells):
            for c, entry in enumerate(row):
                entry.configure(background=CELL_SEL_BG if (r, c) in selected else CELL_BG)
        for r, label in enumerate(self.row_labels):
            label.configure(background=HEADER_SEL_BG if r in selected_rows else HEADER_BG)
        for c, label in enumerate(self.col_labels):
            label.configure(background=HEADER_SEL_BG if c in selected_cols else HEADER_BG)

    def _select_row(self, row: int) -> None:
        self._sel_anchor = (row, 0)
        self._set_selection(row, 0, row, self.cols - 1)

    def _select_column(self, col: int) -> None:
        self._sel_anchor = (0, col)
        self._set_selection(0, col, self.rows - 1, col)

    def _on_cell_button1(self, _event: tk.Event, row: int, col: int) -> None:
        self._sel_anchor = (row, col)
        self._set_selection(row, col, row, col)

    def _on_cell_shift_click(self, _event: tk.Event, row: int, col: int) -> str:
        if self._sel_anchor is None:
            self._sel_anchor = (row, col)
        ar, ac = self._sel_anchor
        self._set_selection(ar, ac, row, col)
        return "break"

    def _transform_entry_text(
        self,
        entry: tk.Entry,
        transform: Callable[[str], str],
        *,
        prefer_selection: bool,
    ) -> bool:
        if prefer_selection and entry.selection_present():
            start = entry.index("sel.first")
            end = entry.index("sel.last")
            value = entry.get()
            converted = transform(value[start:end])
            entry.delete(start, end)
            entry.insert(start, converted)
            entry.selection_range(start, start + len(converted))
            entry.icursor(start + len(converted))
            return True
        value = entry.get()
        converted = transform(value)
        if converted == value:
            return False
        entry.delete(0, "end")
        entry.insert(0, converted)
        return True

    def apply_caps_transform(self, transform: Callable[[str], str]) -> bool:
        cells = self._selected_cells()
        if not cells:
            focus = self.focus_get()
            for r, row in enumerate(self.cells):
                for c, entry in enumerate(row):
                    if entry is focus:
                        cells = [(r, c)]
                        self._sel_anchor = (r, c)
                        self._set_selection(r, c, r, c)
                        break
                if cells:
                    break
        if not cells:
            return False

        changed = False
        touched_cols: set[int] = set()
        single = len(cells) == 1
        for r, c in cells:
            entry = self.cells[r][c]
            if self._transform_entry_text(entry, transform, prefer_selection=single):
                changed = True
                touched_cols.add(c)
        if changed:
            for c in touched_cols:
                self._fit_column(c, shrink=False)
            self.mark_dirty()
        return changed

    def _rebuild_grid(self, values: Optional[list[list[str]]] = None, *, autofit: bool = False) -> None:
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.cells = []
        self.row_labels = []
        self.col_labels = []
        self._sync_col_widths()

        corner = tk.Label(self.grid_frame, text="", width=4, anchor="center", background=HEADER_BG, relief="ridge")
        corner.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        for c in range(self.cols):
            self._make_header(c)

        for r in range(self.rows):
            row_label = tk.Label(
                self.grid_frame,
                text=str(r + 1),
                width=4,
                anchor="center",
                relief="ridge",
                background=HEADER_BG,
                font=("Segoe UI", 9),
            )
            row_label.grid(row=r + 1, column=0, sticky="nsew", padx=1, pady=1)
            row_label.bind("<Button-1>", lambda e, row=r: self._select_row(row))
            row_label.bind("<Button-3>", lambda e, row=r: self._on_row_header_context(e, row))
            self.row_labels.append(row_label)

            row_entries: list[tk.Entry] = []
            for c in range(self.cols):
                entry = tk.Entry(
                    self.grid_frame,
                    width=1,
                    font=self._cell_font,
                    relief="solid",
                    borderwidth=1,
                    background=CELL_BG,
                )
                entry.grid(row=r + 1, column=c + 1, sticky="nsew", padx=1, pady=1)
                if values and r < len(values) and c < len(values[r]):
                    entry.insert(0, values[r][c])
                entry.bind("<KeyRelease>", lambda e, col=c: self._on_cell_edit(col, e))
                entry.bind("<<Paste>>", lambda e, col=c: self.after_idle(lambda c=col: self._on_cell_edit(c)))
                entry.bind("<FocusOut>", self.mark_dirty)
                entry.bind("<Tab>", lambda e, row=r, col=c: self._on_cell_tab(row, col))
                entry.bind("<Button-1>", lambda e, row=r, col=c: self._on_cell_button1(e, row, col))
                entry.bind("<Shift-Button-1>", lambda e, row=r, col=c: self._on_cell_shift_click(e, row, col))
                entry.bind("<Button-3>", lambda e, row=r, col=c: self._on_cell_context(e, row, col))
                entry.bind("<Control-x>", self._shortcut_cut)
                entry.bind("<Control-c>", self._shortcut_copy)
                entry.bind("<Control-v>", self._shortcut_paste)
                row_entries.append(entry)
            self.cells.append(row_entries)

        # Keep prior selection if still in range; otherwise clear
        if self._sel_r1 is not None:
            self._sel_r1 = min(self._sel_r1, self.rows - 1)
            self._sel_r2 = min(self._sel_r2 if self._sel_r2 is not None else 0, self.rows - 1)
            self._sel_c1 = min(self._sel_c1 if self._sel_c1 is not None else 0, self.cols - 1)
            self._sel_c2 = min(self._sel_c2 if self._sel_c2 is not None else 0, self.cols - 1)
            self._refresh_selection_styles()
        else:
            self._clear_selection()

        self._fit_all_columns(shrink=autofit)
        if values is not None and autofit:
            self.mark_clean()

    def _focus_cell(self, row: int, col: int) -> None:
        if not (0 <= row < len(self.cells) and 0 <= col < len(self.cells[row])):
            return
        cell = self.cells[row][col]
        self._sel_anchor = (row, col)
        self._set_selection(row, col, row, col)
        cell.focus_set()
        cell.selection_range(0, "end")
        self.grid_frame.update_idletasks()
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        left, top, right, bottom = bbox
        width = max(right - left, 1)
        height = max(bottom - top, 1)
        # Entry coords are relative to grid_frame, which is the canvas window
        cell_x = cell.winfo_x()
        cell_y = cell.winfo_y()
        self.canvas.xview_moveto(max(0.0, min(1.0, (cell_x - 40) / width)))
        self.canvas.yview_moveto(max(0.0, min(1.0, (cell_y - 40) / height)))

    def _on_cell_tab(self, row: int, col: int) -> str:
        """Move right; from the last cell of the last row, append a row."""
        if row == self.rows - 1 and col == self.cols - 1:
            self._insert_rows(self.rows, count=1)
            self.after_idle(lambda: self._focus_cell(self.rows - 1, 0))
            return "break"

        next_col = col + 1
        next_row = row
        if next_col >= self.cols:
            next_col = 0
            next_row += 1
        self._focus_cell(next_row, next_col)
        return "break"

    # ------------------------------------------------------------------
    # Row / column structure (context menu)
    # ------------------------------------------------------------------

    def _selection_row_span(self) -> tuple[int, int]:
        bounds = self._selection_bounds()
        if bounds is None:
            return 0, 0
        r1, _c1, r2, _c2 = bounds
        return min(r1, r2), max(r1, r2)

    def _selection_col_span(self) -> tuple[int, int]:
        bounds = self._selection_bounds()
        if bounds is None:
            return 0, 0
        _r1, c1, _r2, c2 = bounds
        return min(c1, c2), max(c1, c2)

    def _pad_matrix(self, values: list[list[str]], rows: int, cols: int) -> list[list[str]]:
        return pad_matrix(values, rows, cols)

    def editor_status_text(self) -> str:
        content = self.get_content()
        length = len(content)
        if not content:
            lines = 0
        else:
            lines = content.count("\n") + (0 if content.endswith("\n") else 1)
        bounds = self._selection_bounds()
        if bounds is None:
            line, column = 1, 1
        else:
            r1, c1, _r2, _c2 = bounds
            line, column = r1 + 1, c1 + 1
        return format_editor_status(
            fmt=STATUS_FORMAT_LABELS[self.note_type],
            length=length,
            lines=lines,
            line=line,
            column=column,
        )

    def bind_caret_status(self, callback) -> None:
        self._caret_status_callback = callback

    def _notify_caret_status(self) -> None:
        callback = getattr(self, "_caret_status_callback", None)
        if callback is not None:
            callback()

    def _insert_rows(self, at_index: int, count: int = 1) -> None:
        if count < 1:
            return
        at_index = max(0, min(at_index, self.rows))
        values = self._pad_matrix(self._read_matrix(), self.rows, self.cols)
        for _ in range(count):
            values.insert(at_index, [""] * self.cols)
        self.rows += count
        self._rebuild_grid(values, autofit=False)
        self.mark_dirty()
        self._sel_anchor = (at_index, 0)
        self._set_selection(at_index, 0, at_index + count - 1, self.cols - 1)

    def _delete_rows(self, r1: int, r2: int) -> None:
        r1, r2 = min(r1, r2), max(r1, r2)
        r1 = max(0, r1)
        r2 = min(self.rows - 1, r2)
        if r1 > r2:
            return
        values = self._pad_matrix(self._read_matrix(), self.rows, self.cols)
        del values[r1 : r2 + 1]
        removed = r2 - r1 + 1
        self.rows = max(1, self.rows - removed)
        if not values:
            values = [[""] * self.cols]
            self.rows = 1
        elif len(values) < self.rows:
            values.extend([[""] * self.cols for _ in range(self.rows - len(values))])
        self._rebuild_grid(values, autofit=False)
        self.mark_dirty()
        self._select_row(min(r1, self.rows - 1))

    def _insert_cols(self, at_index: int, count: int = 1) -> None:
        if count < 1:
            return
        at_index = max(0, min(at_index, self.cols))
        values = self._pad_matrix(self._read_matrix(), self.rows, self.cols)
        for row in values:
            for _ in range(count):
                row.insert(at_index, "")
        for _ in range(count):
            self.col_widths.insert(at_index, DEFAULT_COL_WIDTH)
        self.cols += count
        self._rebuild_grid(values, autofit=False)
        self.mark_dirty()
        self._sel_anchor = (0, at_index)
        self._set_selection(0, at_index, self.rows - 1, at_index + count - 1)

    def _delete_cols(self, c1: int, c2: int) -> None:
        c1, c2 = min(c1, c2), max(c1, c2)
        c1 = max(0, c1)
        c2 = min(self.cols - 1, c2)
        if c1 > c2:
            return
        values = self._pad_matrix(self._read_matrix(), self.rows, self.cols)
        for row in values:
            del row[c1 : c2 + 1]
        del self.col_widths[c1 : c2 + 1]
        removed = c2 - c1 + 1
        self.cols = max(1, self.cols - removed)
        if self.cols == 1 and not self.col_widths:
            self.col_widths = [DEFAULT_COL_WIDTH]
        for row in values:
            while len(row) < self.cols:
                row.append("")
        self._rebuild_grid(values, autofit=False)
        self.mark_dirty()
        self._select_column(min(c1, self.cols - 1))

    def _row_in_selection(self, row: int) -> bool:
        r1, r2 = self._selection_row_span()
        bounds = self._selection_bounds()
        if bounds is None:
            return False
        return r1 <= row <= r2

    def _col_in_selection(self, col: int) -> bool:
        c1, c2 = self._selection_col_span()
        bounds = self._selection_bounds()
        if bounds is None:
            return False
        return c1 <= col <= c2

    def _on_row_header_context(self, event: tk.Event, row: int) -> str:
        if not self._row_in_selection(row):
            self._select_row(row)
        self._show_structure_menu(event, mode="row")
        return "break"

    def _on_col_header_context(self, event: tk.Event, col: int) -> str:
        if not self._col_in_selection(col):
            self._select_column(col)
        self._show_structure_menu(event, mode="column")
        return "break"

    def _on_cell_context(self, event: tk.Event, row: int, col: int) -> str:
        if (row, col) not in self._selected_cells():
            self._sel_anchor = (row, col)
            self._set_selection(row, col, row, col)
        self._show_structure_menu(event, mode="cell")
        return "break"

    def _show_structure_menu(self, event: tk.Event, *, mode: str) -> None:
        menu = self._context_menu
        menu.delete(0, "end")

        r1, r2 = self._selection_row_span()
        c1, c2 = self._selection_col_span()
        row_count = r2 - r1 + 1
        col_count = c2 - c1 + 1
        row_label = "Row" if row_count == 1 else "Rows"
        col_label = "Column" if col_count == 1 else "Columns"

        if mode in ("row", "cell"):
            menu.add_command(
                label=f"Insert {row_count} {row_label} Above" if row_count > 1 else "Insert Row Above",
                command=lambda: self._insert_rows(r1, count=row_count),
            )
            menu.add_command(
                label=f"Insert {row_count} {row_label} Below" if row_count > 1 else "Insert Row Below",
                command=lambda: self._insert_rows(r2 + 1, count=row_count),
            )
            menu.add_command(
                label=f"Delete {row_label}",
                command=lambda: self._delete_rows(r1, r2),
            )

        if mode == "cell":
            menu.add_separator()

        if mode in ("column", "cell"):
            menu.add_command(
                label=f"Insert {col_count} {col_label} Left" if col_count > 1 else "Insert Column Left",
                command=lambda: self._insert_cols(c1, count=col_count),
            )
            menu.add_command(
                label=f"Insert {col_count} {col_label} Right" if col_count > 1 else "Insert Column Right",
                command=lambda: self._insert_cols(c2 + 1, count=col_count),
            )
            menu.add_command(
                label=f"Delete {col_label}",
                command=lambda: self._delete_cols(c1, c2),
            )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _read_matrix(self) -> list[list[str]]:
        return [[cell.get() for cell in row] for row in self.cells]

    def get_content(self) -> str:
        matrix = self._read_matrix()
        # Trim trailing empty rows/cols for a tidier file
        while matrix and all(not cell.strip() for cell in matrix[-1]):
            matrix.pop()
        if not matrix:
            return ""
        max_col = 0
        for row in matrix:
            for i in range(len(row) - 1, -1, -1):
                if row[i].strip():
                    max_col = max(max_col, i + 1)
                    break
        matrix = [row[:max_col] for row in matrix]
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerows(matrix)
        return buf.getvalue()

    def set_content(self, content: str) -> None:
        rows = list(csv.reader(io.StringIO(content)))
        if not rows:
            self.rows = DEFAULT_ROWS
            self.cols = DEFAULT_COLS
            self.col_widths = [DEFAULT_COL_WIDTH] * self.cols
            self._rebuild_grid([[]], autofit=True)
            self.mark_clean()
            return
        self.rows = max(DEFAULT_ROWS, len(rows))
        self.cols = max(DEFAULT_COLS, max((len(r) for r in rows), default=DEFAULT_COLS))
        self.col_widths = [DEFAULT_COL_WIDTH] * self.cols
        self._rebuild_grid(rows, autofit=True)
        self.mark_clean()

    # ------------------------------------------------------------------
    # Clipboard (HTML table + TSV — works with Google Docs / Sheets)
    # ------------------------------------------------------------------

    def _active_cells(self) -> list[tuple[int, int]]:
        cells = self._selected_cells()
        if cells:
            return cells
        focus = self.focus_get()
        for r, row in enumerate(self.cells):
            for c, entry in enumerate(row):
                if entry is focus:
                    self._sel_anchor = (r, c)
                    self._set_selection(r, c, r, c)
                    return [(r, c)]
        return []

    def _selection_bounds(self) -> Optional[tuple[int, int, int, int]]:
        cells = self._active_cells()
        if not cells:
            return None
        rows = [r for r, _ in cells]
        cols = [c for _, c in cells]
        return min(rows), min(cols), max(rows), max(cols)

    def _selection_matrix(self) -> Optional[list[list[str]]]:
        bounds = self._selection_bounds()
        if bounds is None:
            return None
        r1, c1, r2, c2 = bounds
        matrix: list[list[str]] = []
        for r in range(r1, r2 + 1):
            matrix.append(
                [self.cells[r][c].get().replace("\t", " ").replace("\r", " ").replace("\n", " ") for c in range(c1, c2 + 1)]
            )
        return matrix

    def _selection_as_tsv(self) -> Optional[str]:
        matrix = self._selection_matrix()
        if matrix is None:
            return None
        # CRLF + tabs: standard spreadsheet plain-text fallback
        return "\r\n".join("\t".join(row) for row in matrix)

    def _selection_as_html(self) -> Optional[str]:
        matrix = self._selection_matrix()
        if matrix is None:
            return None
        return build_html_table(matrix)

    def _set_clipboard_cells(self, matrix: list[list[str]]) -> None:
        plain = "\r\n".join("\t".join(row) for row in matrix)
        html_fragment = build_html_table(matrix)
        if set_windows_clipboard_text_and_html(plain, html_fragment):
            return
        # Non-Windows / API failure: plain TSV via Tk
        self._set_clipboard(plain)

    def _clipboard_grid(self) -> Optional[list[list[str]]]:
        html_clip = get_windows_clipboard_html()
        if html_clip:
            table = parse_html_table(html_clip)
            if table:
                return table
        clip = self._get_clipboard()
        if clip is None:
            return None
        return parse_clipboard_grid(clip)

    def _ensure_grid_size(self, min_rows: int, min_cols: int) -> None:
        if min_rows <= self.rows and min_cols <= self.cols:
            return
        values = self._read_matrix()
        sel = (self._sel_r1, self._sel_c1, self._sel_r2, self._sel_c2, self._sel_anchor)
        self.rows = max(self.rows, min_rows)
        self.cols = max(self.cols, min_cols)
        while len(self.col_widths) < self.cols:
            self.col_widths.append(DEFAULT_COL_WIDTH)
        self._rebuild_grid(values, autofit=False)
        self._sel_r1, self._sel_c1, self._sel_r2, self._sel_c2, self._sel_anchor = sel
        if self._sel_r1 is not None:
            self._refresh_selection_styles()

    def _clear_cells(self, cells: list[tuple[int, int]]) -> None:
        cols: set[int] = set()
        for r, c in cells:
            self.cells[r][c].delete(0, "end")
            cols.add(c)
        for c in cols:
            self._fit_column(c, shrink=False)

    def edit_copy(self) -> bool:
        cells = self._active_cells()
        if not cells:
            return False
        if len(cells) == 1:
            r, c = cells[0]
            entry = self.cells[r][c]
            if entry.selection_present():
                selected = entry.selection_get()
                whole = entry.get()
                # Partial text selection → plain text only; whole-cell → HTML table
                if selected != whole:
                    self._set_clipboard(selected)
                    return True
        matrix = self._selection_matrix()
        if matrix is None:
            return False
        self._set_clipboard_cells(matrix)
        return True

    def edit_cut(self) -> bool:
        cells = self._active_cells()
        if not cells:
            return False
        if len(cells) == 1:
            r, c = cells[0]
            entry = self.cells[r][c]
            if entry.selection_present():
                selected = entry.selection_get()
                whole = entry.get()
                if selected != whole:
                    self._set_clipboard(selected)
                    start = entry.index("sel.first")
                    end = entry.index("sel.last")
                    entry.delete(start, end)
                    self._fit_column(c, shrink=False)
                    self.mark_dirty()
                    return True
        if not self.edit_copy():
            return False
        self._clear_cells(cells)
        self.mark_dirty()
        return True

    def edit_paste(self) -> bool:
        grid = self._clipboard_grid()
        if grid is None:
            return False
        cells = self._active_cells()
        if not cells:
            return False

        r0 = min(r for r, _ in cells)
        c0 = min(c for _, c in cells)
        is_grid = len(grid) > 1 or (len(grid) == 1 and len(grid[0]) > 1)

        if not is_grid and len(cells) == 1:
            entry = self.cells[r0][c0]
            value = grid[0][0] if grid and grid[0] else ""
            if entry.selection_present():
                start = entry.index("sel.first")
                end = entry.index("sel.last")
                entry.delete(start, end)
                entry.insert(start, value)
                entry.icursor(start + len(value))
            else:
                # Insert at caret when editing a single cell without a selection
                try:
                    pos = entry.index("insert")
                except tk.TclError:
                    pos = len(entry.get())
                entry.insert(pos, value)
                entry.icursor(pos + len(value))
            self._fit_column(c0, shrink=False)
            self.mark_dirty()
            return True

        row_count = len(grid)
        col_count = max((len(row) for row in grid), default=1)
        self._ensure_grid_size(r0 + row_count, c0 + col_count)

        touched_cols: set[int] = set()
        for i, row in enumerate(grid):
            for j in range(col_count):
                value = row[j] if j < len(row) else ""
                entry = self.cells[r0 + i][c0 + j]
                entry.delete(0, "end")
                entry.insert(0, value)
                touched_cols.add(c0 + j)

        self._sel_anchor = (r0, c0)
        self._set_selection(r0, c0, r0 + row_count - 1, c0 + col_count - 1)
        for c in touched_cols:
            self._fit_column(c, shrink=False)
        self.mark_dirty()
        return True


# ---------------------------------------------------------------------------
