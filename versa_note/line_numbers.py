"""Line-number gutter for tkinter Text widgets."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Optional


class LineNumberGutter(tk.Canvas):
    """Scroll-synced line numbers drawn beside a Text widget."""

    def __init__(
        self,
        master: tk.Misc,
        text: tk.Text,
        *,
        background: str = "#F0F0F0",
        foreground: str = "#6E7781",
        font: tuple = ("Consolas", 11),
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=40,
            highlightthickness=0,
            borderwidth=0,
            background=background,
            **kwargs,
        )
        self.text = text
        self._foreground = foreground
        self._font = font
        self._visible = True
        self._padx = 8
        self._redraw_job: Optional[str] = None
        self._digit_width = max(7, tkfont.Font(font=self._font).measure("0"))

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", self._on_mousewheel_linux)
        self.bind("<Button-5>", self._on_mousewheel_linux)

    def attach(self, *, yscroll: Any = None) -> None:
        """Wire scroll/update hooks. Call once after the Text and scrollbar exist."""

        def _on_scroll(*args) -> None:
            if yscroll is not None:
                yscroll.set(*args)
            self.redraw()

        self.text.configure(yscrollcommand=_on_scroll)
        self.text.bind("<Configure>", self._schedule_redraw, add="+")
        self.text.bind("<KeyRelease>", self._schedule_redraw, add="+")
        self.text.bind("<<Modified>>", self._schedule_redraw, add="+")
        self.text.bind("<MouseWheel>", self._schedule_redraw, add="+")
        self.bind("<Configure>", self._schedule_redraw, add="+")
        self.after_idle(self.redraw)

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        if visible:
            self.grid()
            self.redraw()
        else:
            self.grid_remove()

    @property
    def visible(self) -> bool:
        return self._visible

    def _schedule_redraw(self, _event=None) -> None:
        if not self._visible:
            return
        if self._redraw_job is not None:
            try:
                self.after_cancel(self._redraw_job)
            except tk.TclError:
                pass
        self._redraw_job = self.after(16, self.redraw)

    def redraw(self, *_args) -> None:
        self._redraw_job = None
        if not self._visible:
            return
        try:
            first = self.text.index("@0,0")
            last = self.text.index(f"@0,{max(self.text.winfo_height(), 1)}")
        except tk.TclError:
            return

        end_line = int(float(self.text.index("end-1c")))
        digits = max(2, len(str(max(end_line, 1))))
        width = self._padx * 2 + digits * self._digit_width
        if int(self.cget("width")) != width:
            self.configure(width=width)

        self.delete("all")
        i = first
        while True:
            dline = self.text.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".", 1)[0]
            self.create_text(
                width - self._padx,
                y,
                anchor="ne",
                text=linenum,
                fill=self._foreground,
                font=self._font,
            )
            if self.text.compare(i, ">=", last):
                break
            i = self.text.index(f"{i}+1line")
            if self.text.compare(i, ">=", "end"):
                break

    def _on_mousewheel(self, event: tk.Event) -> str:
        delta = -1 * (event.delta // 120) if event.delta else 0
        if delta:
            self.text.yview_scroll(delta, "units")
            self.redraw()
        return "break"

    def _on_mousewheel_linux(self, event: tk.Event) -> str:
        if getattr(event, "num", None) == 4:
            self.text.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.text.yview_scroll(1, "units")
        self.redraw()
        return "break"
