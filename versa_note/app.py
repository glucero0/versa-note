"""Main Versa Note application window."""

from __future__ import annotations

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from versa_note.constants import APP_NAME, NEW_STEM, SESSION_FILENAME
from versa_note.documents import (
    DOC_TYPES,
    Document,
    NOTE_TYPE_LABELS,
    SUPPORTED_EXTENSIONS,
    resolve_note_type,
)
from versa_note.transforms import CAPS_TRANSFORMS


class VersaNoteApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("960x640")
        self.minsize(640, 400)

        self._save_dir = Path.cwd()

        self._build_style()
        self._build_menu()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if not self._restore_session():
            self.new_document("plain")

    def _build_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        new_menu = tk.Menu(file_menu, tearoff=0)
        new_menu.add_command(label="Plain text", accelerator="Ctrl+N", command=lambda: self.new_document("plain"))
        new_menu.add_command(label="Markdown", command=lambda: self.new_document("markdown"))
        new_menu.add_command(label="Spreadsheet", command=lambda: self.new_document("spreadsheet"))
        file_menu.add_cascade(label="New", menu=new_menu)
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self.open_document)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_document)
        file_menu.add_command(label="Save As…", accelerator="Ctrl+Shift+S", command=self.save_document_as)
        file_menu.add_separator()
        file_menu.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=self.edit_cut)
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self.edit_copy)
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=self.edit_paste)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        transform_menu = tk.Menu(menubar, tearoff=0)
        caps_menu = tk.Menu(transform_menu, tearoff=0)
        caps_menu.add_command(label="To Upper", command=lambda: self.apply_caps("upper"))
        caps_menu.add_command(label="To Lower", command=lambda: self.apply_caps("lower"))
        caps_menu.add_command(label="Initial Caps", command=lambda: self.apply_caps("initial"))
        caps_menu.add_command(label="Sentence Caps", command=lambda: self.apply_caps("sentence"))
        transform_menu.add_cascade(label="Caps", menu=caps_menu)
        menubar.add_cascade(label="Transform", menu=transform_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

        self.bind_all("<Control-n>", lambda e: self.new_document("plain"))
        self.bind_all("<Control-o>", lambda e: self.open_document())
        self.bind_all("<Control-s>", lambda e: self.save_document())
        self.bind_all("<Control-S>", lambda e: self.save_document_as())
        self.bind_all("<Control-w>", lambda e: self.close_current_tab())
        # Cut/Copy/Paste are bound on editor widgets (not bind_all) so they
        # run before Tk class defaults and do not paste/cut twice.

    def _build_ui(self) -> None:
        self.status = ttk.Label(self, text="Ready", anchor="w", padding=(8, 4))
        self.status.pack(side="bottom", fill="x")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    # ------------------------------------------------------------------
    # Tab / document helpers
    # ------------------------------------------------------------------

    def _all_documents(self) -> list[Document]:
        docs: list[Document] = []
        for tab_id in self.notebook.tabs():
            widget = self.notebook.nametowidget(tab_id)
            if isinstance(widget, Document):
                docs.append(widget)
        return docs

    def current_document(self) -> Optional[Document]:
        selection = self.notebook.select()
        if not selection:
            return None
        widget = self.notebook.nametowidget(selection)
        return widget if isinstance(widget, Document) else None

    def _used_new_stems(self) -> set[str]:
        used: set[str] = set()
        for doc in self._all_documents():
            if doc.path is None:
                used.add(doc.untitled_stem)
            else:
                used.add(doc.path.stem)
        # Avoid colliding with New / New - N files already on disk
        if self._save_dir.is_dir():
            for path in self._save_dir.iterdir():
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    if path.stem == NEW_STEM or path.stem.startswith(f"{NEW_STEM} - "):
                        used.add(path.stem)
        return used

    def _next_new_stem(self) -> str:
        used = self._used_new_stems()
        if NEW_STEM not in used:
            return NEW_STEM
        n = 1
        while f"{NEW_STEM} - {n}" in used:
            n += 1
        return f"{NEW_STEM} - {n}"

    def _refresh_tab(self, doc: Document) -> None:
        try:
            self.notebook.tab(doc, text=doc.display_name())
        except tk.TclError:
            pass

    def _set_status(self, message: str) -> None:
        self.status.configure(text=message)

    def _update_chrome(self) -> None:
        doc = self.current_document()
        if doc:
            self._refresh_tab(doc)
            self.title(f"{doc.display_name()} — {APP_NAME}")
            type_label = NOTE_TYPE_LABELS.get(doc.note_type, doc.note_type)
            path = str(doc.path) if doc.path else f"(unsaved · {doc.base_name()})"
            self._set_status(f"{type_label}  ·  {path}")
        else:
            self.title(APP_NAME)
            self._set_status("Ready")

    def _on_tab_changed(self, _event=None) -> None:
        self._update_chrome()

    def _on_dirty(self, event=None) -> None:
        widget = event.widget if event is not None else None
        if isinstance(widget, Document):
            self._refresh_tab(widget)
        self._update_chrome()

    def _add_document_tab(self, doc: Document, *, select: bool = True) -> None:
        doc.bind("<<DocumentDirty>>", self._on_dirty)
        self.notebook.add(doc, text=doc.display_name())
        if select:
            self.notebook.select(doc)
        self._update_chrome()

    def _find_tab_for_path(self, path: Path) -> Optional[Document]:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        for doc in self._all_documents():
            if doc.path is None:
                continue
            try:
                if doc.path.resolve() == resolved:
                    return doc
            except OSError:
                if doc.path == path:
                    return doc
        return None

    # ------------------------------------------------------------------
    # Edit
    # ------------------------------------------------------------------

    def edit_cut(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        if doc.edit_cut():
            self._update_chrome()
        else:
            self._set_status("Nothing to cut")

    def edit_copy(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        if doc.edit_copy():
            self._set_status("Copied")
        else:
            self._set_status("Nothing to copy")

    def edit_paste(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        if doc.edit_paste():
            self._update_chrome()
            self._set_status("Pasted")
        else:
            self._set_status("Nothing to paste")

    # ------------------------------------------------------------------
    # Transforms
    # ------------------------------------------------------------------

    def apply_caps(self, kind: str) -> None:
        doc = self.current_document()
        if doc is None:
            return
        transform = CAPS_TRANSFORMS.get(kind)
        if transform is None:
            return
        if not doc.apply_caps_transform(transform):
            self._set_status("Select text or spreadsheet cells to transform")
            return
        labels = {
            "upper": "To Upper",
            "lower": "To Lower",
            "initial": "Initial Caps",
            "sentence": "Sentence Caps",
        }
        self._set_status(f"Applied Caps → {labels.get(kind, kind)}")
        self._update_chrome()

    # ------------------------------------------------------------------
    # File actions
    # ------------------------------------------------------------------

    def new_document(self, note_type: str) -> None:
        cls = DOC_TYPES[note_type]
        doc = cls(self.notebook, untitled_stem=self._next_new_stem())
        self._add_document_tab(doc)

    def _open_path(self, path: Path, *, select: bool = True, quiet: bool = False) -> Optional[Document]:
        existing = self._find_tab_for_path(path)
        if existing is not None:
            if select:
                self.notebook.select(existing)
                self._update_chrome()
            return existing

        note_type = resolve_note_type(path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            if not quiet:
                messagebox.showerror("Open failed", str(exc), parent=self)
            return None

        doc = DOC_TYPES[note_type](self.notebook, untitled_stem=path.stem)
        doc.set_content(content)
        doc.path = path
        doc.mark_clean()
        self._add_document_tab(doc, select=select)
        return doc

    def open_document(self) -> None:
        path_str = filedialog.askopenfilename(
            parent=self,
            title="Open",
            filetypes=[
                ("Supported notes", "*.txt *.md *.markdown *.csv"),
                ("Text files", "*.txt"),
                ("Markdown files", "*.md *.markdown"),
                ("CSV spreadsheets", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path_str:
            return
        self._open_path(Path(path_str))

    def save_document(self) -> bool:
        doc = self.current_document()
        if doc is None:
            return False
        if doc.path is None:
            return self.save_document_as()
        return self._write_doc(doc, doc.path)

    def save_document_as(self) -> bool:
        doc = self.current_document()
        if doc is None:
            return False
        initial = doc.base_name()
        path_str = filedialog.asksaveasfilename(
            parent=self,
            title="Save As",
            initialfile=initial,
            defaultextension=doc.default_extension,
            filetypes=doc.filetypes,
        )
        if not path_str:
            return False
        path = Path(path_str)
        if not path.suffix:
            path = path.with_suffix(doc.default_extension)
        return self._write_doc(doc, path)

    def _write_doc(self, doc: Document, path: Path) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(doc.get_content(), encoding="utf-8", newline="\n")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            return False
        doc.path = path
        doc.untitled_stem = path.stem
        doc.mark_clean()
        self._refresh_tab(doc)
        self._update_chrome()
        return True

    def close_current_tab(self) -> None:
        doc = self.current_document()
        if doc is None:
            return
        if doc.dirty and doc.path is not None:
            result = messagebox.askyesnocancel(
                "Unsaved changes",
                f"Save changes to {doc.path.name} before closing?",
                parent=self,
            )
            if result is None:
                return
            if result and not self._write_doc(doc, doc.path):
                return
        elif doc.path is None and not doc.is_empty():
            # Persist unnamed note content with its default New / New - N name
            if not self._autosave_unnamed(doc, reserved=set()):
                return

        self.notebook.forget(doc)
        doc.destroy()
        if not self.notebook.tabs():
            self.new_document("plain")
        else:
            self._update_chrome()

    # ------------------------------------------------------------------
    # Autosave unnamed notes
    # ------------------------------------------------------------------

    def _path_available(self, path: Path, reserved: set[Path]) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in reserved:
            return False
        return not path.exists()

    def _default_path_for(self, doc: Document, reserved: set[Path]) -> Path:
        """Pick New.ext / New - 1.ext that is free on disk and not reserved."""
        ext = doc.default_extension
        stems = [doc.untitled_stem, NEW_STEM, *[f"{NEW_STEM} - {i}" for i in range(1, 10_001)]]
        seen: set[str] = set()
        for stem in stems:
            if stem in seen:
                continue
            seen.add(stem)
            path = self._save_dir / f"{stem}{ext}"
            if self._path_available(path, reserved):
                return path
        return self._save_dir / f"{NEW_STEM} - {os.getpid()}{ext}"

    def _autosave_unnamed(self, doc: Document, reserved: set[Path]) -> bool:
        path = self._default_path_for(doc, reserved)
        if not self._write_doc(doc, path):
            return False
        try:
            reserved.add(path.resolve())
        except OSError:
            reserved.add(path)
        return True

    def _autosave_on_exit(self) -> bool:
        """Save dirty named notes and all unnamed notes with New / New - N names."""
        reserved: set[Path] = set()
        for doc in self._all_documents():
            if doc.path is not None:
                try:
                    reserved.add(doc.path.resolve())
                except OSError:
                    reserved.add(doc.path)

        for doc in self._all_documents():
            if doc.path is None:
                if doc.is_empty() and not doc.dirty:
                    continue
                if not self._autosave_unnamed(doc, reserved):
                    return False
            elif doc.dirty:
                if not self._write_doc(doc, doc.path):
                    return False
        return True

    # ------------------------------------------------------------------
    # Session restore
    # ------------------------------------------------------------------

    def _session_path(self) -> Path:
        return self._save_dir / SESSION_FILENAME

    def _path_for_session(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self._save_dir.resolve()))
        except (OSError, ValueError):
            try:
                return str(path.resolve())
            except OSError:
                return str(path)

    def _resolve_session_path(self, raw: str) -> Path:
        path = Path(raw)
        if path.is_file():
            return path
        candidate = self._save_dir / path
        if candidate.is_file():
            return candidate
        candidate = self._save_dir / path.name
        return candidate

    def _write_session(self) -> None:
        tabs: list[str] = []
        active = 0
        current = self.current_document()
        for doc in self._all_documents():
            if doc.path is None:
                continue
            tabs.append(self._path_for_session(doc.path))
            if current is doc:
                active = len(tabs) - 1
        payload = {"tabs": tabs, "active": active}
        try:
            self._session_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Session save failed", str(exc), parent=self)

    def _restore_session(self) -> bool:
        session_file = self._session_path()
        if not session_file.is_file():
            return False
        try:
            payload = json.loads(session_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        raw_tabs = payload.get("tabs") or []
        if not isinstance(raw_tabs, list) or not raw_tabs:
            return False

        active_index = payload.get("active", 0)
        if not isinstance(active_index, int):
            active_index = 0

        loaded: list[Document] = []
        for raw in raw_tabs:
            if not isinstance(raw, str):
                continue
            path = self._resolve_session_path(raw)
            if not path.is_file():
                continue
            doc = self._open_path(path, select=False, quiet=True)
            if doc is not None and doc not in loaded:
                loaded.append(doc)

        if not loaded:
            return False

        select_doc = loaded[min(max(active_index, 0), len(loaded) - 1)]
        # active_index refers to original session list; prefer matching path order among loaded
        if 0 <= active_index < len(raw_tabs):
            preferred = self._resolve_session_path(raw_tabs[active_index])
            for doc in loaded:
                try:
                    if doc.path and doc.path.resolve() == preferred.resolve():
                        select_doc = doc
                        break
                except OSError:
                    if doc.path == preferred:
                        select_doc = doc
                        break

        self.notebook.select(select_doc)
        self._update_chrome()
        return True

    def _about(self) -> None:
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\n\n"
            "A simple note-taking app with plain text, markdown\n"
            "(syntax-colored source), and spreadsheet grid notes.",
            parent=self,
        )

    def _on_close(self) -> None:
        if self._autosave_on_exit():
            self._write_session()
            self.destroy()


def main() -> None:
    app = VersaNoteApp()
    app.mainloop()


if __name__ == "__main__":
    main()
