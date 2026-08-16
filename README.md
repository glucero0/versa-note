# Versa Note

A simple multi-type note-taking app built with Python and tkinter. Open plain text, markdown, spreadsheet, and JSON notes in tabs; edit, transform, and copy them with familiar desktop shortcuts.

## Requirements

- **Python 3.13.x** (`>=3.13.5,<3.14` in `pyproject.toml`; `.python-version` pins **3.13.5** for local tools)
- tkinter (included with most Python installs)

No third-party packages are required to run the app.

If you use [pyenv](https://github.com/pyenv/pyenv) or [uv](https://github.com/astral-sh/uv), run `pyenv install` or `uv python install` from the repo root to pick up the version in `.python-version`.

## Run

```bash
python main.py
```

Or as a module:

```bash
python -m versa_note
```

## Features

### Note types

| Type | Extension | Description |
|------|-----------|-------------|
| Plain text | `.txt` | Word-wrapped text editor |
| Markdown | `.md` | Source editor with syntax coloring (headings, bold, italic, code, links, lists, quotes) — not a rendered preview |
| Spreadsheet | `.csv` | Simple grid for data entry; not a full spreadsheet engine |
| JSON | `.json` | Source editor with syntax coloring (keys, strings, numbers, keywords), validity in the status bar, Prettify / Minify |

### Tabs & session

- **File → New** opens plain text, markdown, spreadsheet, or JSON notes in tabs
- Unnamed notes autosave on exit as `New`, `New - 1`, `New - 2`, … (with the right extension)
- Open tabs are restored next launch via `.versa-note-session.json`

### Editing

- **Edit → Cut / Copy / Paste** (Ctrl+X / Ctrl+C / Ctrl+V)
- Spreadsheet ranges copy as HTML tables (for Google Docs / Sheets) plus TSV plain text
- Spreadsheet columns grow as you type; drag column header edges to resize (double-click a sizer to autofit)
- Right-click a row header, column header, or cell for Insert/Delete Row and Column (above/below, left/right)
- Tab from the last cell of the last row adds a new row

### Transforms

**Transform → Caps**

- To Upper / To Lower
- Initial Caps (first letter of each sentence)
- Sentence Caps (first letter of every word)

Works on text selections and on spreadsheet cell / row / column selections.

**Transform → Prettify / Minify** (JSON tabs only; disabled otherwise)

- Prettify (Ctrl+Shift+F) — indent with 2 spaces
- Minify — compact single-line JSON
- Invalid JSON is left unchanged; the status bar shows the parse error

## Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New plain text note |
| Ctrl+O | Open |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+W | Close tab |
| Ctrl+X / C / V | Cut / Copy / Paste |
| Ctrl+Shift+F | Prettify JSON (JSON tabs only) |

## Project layout

```
versa-note/
├── .python-version         # Pinned Python version (3.13.5)
├── pyproject.toml          # Project metadata and Python pin
├── main.py                 # Entry point (python main.py)
├── versa_note/
│   ├── __init__.py
│   ├── __main__.py         # Module entry (python -m versa_note)
│   ├── app.py              # Main window, menus, file/session logic
│   ├── constants.py        # Shared constants
│   ├── transforms.py       # Caps transforms
│   ├── json_format.py      # Prettify / minify / validate helpers
│   ├── clipboard.py        # HTML table / clipboard helpers
│   └── documents/
│       ├── base.py         # Document base class
│       ├── plain.py        # Plain text notes
│       ├── markdown.py     # Markdown source editor
│       ├── spreadsheet.py  # CSV grid
│       ├── json_document.py # JSON source editor
│       └── registry.py     # DOC_TYPES, EXT_TO_TYPE, extension resolution
├── README.md
└── .gitignore
```

### Adding a new note type

1. Subclass `Document` in `versa_note/documents/`
2. Register it in `versa_note/documents/registry.py` (`DOC_TYPES`, `EXT_TO_TYPE`, `NOTE_TYPE_LABELS`)
3. Add a **File → New** menu item in `versa_note/app.py`
4. Update open-dialog file types and `.gitignore` autosave patterns if needed

## Development

```bash
pip install pytest
pytest
```

No third-party packages are required to run the app itself.

## License

Use and modify freely for your own projects.
