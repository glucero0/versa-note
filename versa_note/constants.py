"""Shared application constants."""

APP_NAME = "Versa Note"
DEFAULT_COLS = 6
DEFAULT_ROWS = 12
NEW_STEM = "New"
SESSION_FILENAME = ".versa-note-session.json"
MIN_COL_WIDTH = 72
DEFAULT_COL_WIDTH = 96
MAX_COL_WIDTH = 720
CELL_TEXT_PAD = 22
CELL_BG = "#FFFFFF"
CELL_SEL_BG = "#CDE4FF"
HEADER_BG = "#F0F0F0"
HEADER_SEL_BG = "#B7D4F5"

# Short labels for the lower-right editor status strip
STATUS_FORMAT_LABELS: dict[str, str] = {
    "plain": "TXT",
    "markdown": "MD",
    "spreadsheet": "CSV",
    "json": "JSON",
}
