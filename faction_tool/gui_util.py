"""Small layout helpers shared by the windows, so a smaller window never hides a button.

A packed widget gets its space in packing order: when a window is too small, the widgets packed last lose it
first. So buttons are packed first and long hint labels last, and a form taller than the window scrolls."""

import tkinter as tk
from tkinter import ttk


def first(*widgets):
    """Move packed widgets to the front of their parent's packing order, the last one named first - so they keep
    their room and a hint label packed after them is the one that is cut. Only for widgets packed on the same
    side (moving a side="left" widget also moves it to the left edge)."""
    for w in widgets:
        slaves = w.master.pack_slaves()
        if slaves and slaves[0] is not w:
            w.pack_configure(before=slaves[0])


class ScrollFrame(ttk.Frame):
    """A frame whose contents (built in .inner) scroll up and down when the window is lower than they are.
    The inner frame is as wide as the visible area, so rows still fill the width; its height is what its
    contents ask for (an expanding list inside does not grow past that)."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._bar_set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self._resize())
        self.canvas.bind("<Configure>", lambda e: self._resize())
        self.bind("<Enter>", lambda e: self._wheel(True))
        self.bind("<Leave>", lambda e: self._wheel(self._inside(e)))

    def _resize(self):
        # the contents keep the height they ask for (a fixed height would not follow them when they grow)
        cw = self.canvas.winfo_width()
        self.canvas.itemconfigure(self._win, width=cw)
        self.canvas.configure(scrollregion=(0, 0, cw, self.inner.winfo_reqheight()))

    def _bar_set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y", before=self.canvas)
        self.bar.set(lo, hi)

    def _wheel(self, on):
        if on:
            self.bind_all("<MouseWheel>", self._on_wheel)
            self.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
            self.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        else:
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.unbind_all(ev)

    def _inside(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        return w is not None and str(w).startswith(str(self))

    def _on_wheel(self, e):
        if self.bar.winfo_ismapped() and self._inside(e):
            self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")


def fit_first_pane(panes, inner, extra=20):
    """Set a horizontal Panedwindow's first sash to the width its first pane's contents ask for, once, when the
    window first shows it (a ScrollFrame asks for no width of its own)."""
    def fit(e):
        panes.unbind("<Map>")
        panes.update_idletasks()
        panes.sashpos(0, inner.winfo_reqwidth() + extra)
    panes.bind("<Map>", fit)


class FactionBox(ttk.Combobox):
    """A faction picker showing 'turks - Ryazan' (the internal name and the one players see) while its variable
    keeps the internal name, so the code reading it is unchanged. Other values ('(all)', ...) pass as they are."""

    def __init__(self, master, variable, names=(), shown=None, **kw):
        self._real = variable
        self._shown = tk.StringVar()
        self._labels = {}
        self._busy = False
        super().__init__(master, textvariable=self._shown, **kw)
        variable.trace_add("write", self._from_real)
        self._shown.trace_add("write", self._from_shown)
        self.set_names(names, shown or {})

    def set_names(self, names, shown=None):
        from .build import faction_label
        shown = shown or {}
        self._labels = {n: faction_label(n, shown.get(n)) for n in names}
        self["values"] = [self._labels[n] for n in names]
        self._from_real()

    def _from_real(self, *_):
        if self._busy:
            return
        self._busy = True
        try:
            v = self._real.get()
            self._shown.set(self._labels.get(v, v))
        finally:
            self._busy = False

    def _from_shown(self, *_):
        if self._busy:
            return
        self._busy = True
        try:
            s = self._shown.get()
            self._real.set(next((n for n, l in self._labels.items() if l == s), s))
        finally:
            self._busy = False


def flow(frame):
    """Lay the widgets packed side="left" in `frame` out in rows that wrap at the frame's width, as words in a line
    of text: a toolbar with more buttons than the window is wide goes on to a second row instead of hiding the last
    ones past the edge. Call it once the toolbar is built; it follows the window's width from then on."""
    items = []
    for w in frame.pack_slaves():
        padx = w.pack_info().get("padx", 0)
        if isinstance(padx, (tuple, list)):
            left, right = int(padx[0]), int(padx[-1])
        else:
            left = right = int(padx or 0)
        items.append((w, left, right))
        w.pack_forget()
    state = {"key": None}

    def reflow(_=None):
        width = frame.winfo_width()
        if width <= 1:
            width = max(frame.winfo_toplevel().winfo_width() - 20, 200)
        places, x, y, line = [], 0, 0, 0
        for w, left, right in items:
            need = w.winfo_reqwidth() + left + right
            if x and x + need > width:
                x, y, line = 0, y + line + 2, 0
            h = w.winfo_reqheight()
            places.append((w, x + left, y, h))
            x += need
            line = max(line, h)
        height = y + line + 2
        key = (width, tuple((p[1], p[2]) for p in places))
        if key == state["key"]:
            return
        state["key"] = key
        rows = {}
        for w, px, py, h in places:
            rows[py] = max(rows.get(py, 0), h)
        for w, px, py, h in places:
            w.place(x=px, y=py + (rows[py] - h) // 2)
        frame.configure(height=height)
    frame.bind("<Configure>", reflow, add="+")
    frame.after_idle(reflow)
