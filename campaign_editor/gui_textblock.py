"""A notepad inside the editor (the user, 2026-10-21: 'the lines bind people - open the block as it is written in the
file, as Notepad does'): line numbers in the file's own count, the key of each line, comments and braces in their
colours, Undo / Redo (Ctrl+Z / Ctrl+Y), Find (Ctrl+F), a line with a mistake underlined red (its reason on hover),
the right click's menu of the line (what it means, its form, its words - gui_lineinfo). What is typed is handed to
on_change a moment after the typing stops."""

import tkinter as tk
from tkinter import ttk

from . import theme


class BlockText(ttk.Frame):
    def __init__(self, master, on_change=None, on_menu=None, comment=";"):
        super().__init__(master)
        self.on_change, self.on_menu = on_change, on_menu
        self.comment = comment                          # the line comment of the file's kind (None: xml has none)
        self.first = 0                                  # the file's line number of the first line shown
        self._after, self._loading, self._errors = None, False, {}
        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x")
        ttk.Label(bar, text="Find").pack(side="left")
        self.v_find = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.v_find, width=28)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.find_next())
        ttk.Button(bar, text="Next", command=self.find_next).pack(side="left")
        self.lbl = ttk.Label(bar, text="", foreground=theme.palette()["muted"])
        self.lbl.pack(side="left", padx=8)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        pal = theme.palette()
        self.gutter = tk.Text(body, width=6, padx=4, takefocus=0, borderwidth=0, state="disabled",
                              background=pal.get("bg2", "#ececec"), foreground=pal["muted"], font=("Consolas", 10))
        self.gutter.pack(side="left", fill="y")
        self.text = tk.Text(body, wrap="none", undo=True, maxundo=-1, autoseparators=True, font=("Consolas", 10),
                            background=theme.field(), foreground=pal["fg"], insertbackground=pal["fg"])
        ys = ttk.Scrollbar(body, orient="vertical", command=self._yview)
        xs = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=lambda a, b: (ys.set(a, b), self.gutter.yview_moveto(a)),
                            xscrollcommand=xs.set)
        ys.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        xs.pack(side="bottom", fill="x")
        t = self.text
        t.tag_configure("key", foreground="#2b6cb0", font=("Consolas", 10, "bold"))
        t.tag_configure("comment", foreground="#7a8a7a")
        t.tag_configure("brace", foreground="#a0522d", font=("Consolas", 10, "bold"))
        t.tag_configure("error", underline=True, foreground="#c0392b")
        t.tag_configure("found", background="#ffe066", foreground="#000000")
        t.bind("<<Modified>>", self._modified)
        t.bind("<Control-y>", lambda e: self._redo())
        t.bind("<Control-f>", lambda e: (e.widget.focus_set(), self.v_find.set(t.get("sel.first", "sel.last")
                                                                                  if t.tag_ranges("sel") else
                                                                                  self.v_find.get()), "break")[-1])
        t.bind("<Button-3>", self._menu)
        t.bind("<Motion>", self._hover)
        self.gutter.bind("<MouseWheel>", lambda e: (t.yview_scroll(int(-e.delta / 120), "units"), "break")[-1])

    def _yview(self, *a):
        self.text.yview(*a)
        self.gutter.yview(*a)

    def _redo(self):
        try:
            self.text.edit_redo()
        except tk.TclError:
            pass
        return "break"

    # ---- content ----
    def set_lines(self, lines, first=0, at=None):
        """The lines shown (their file line numbers from first + 1); at: a file line to show and put the cursor on."""
        self._loading = True
        self.first = first
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(lines))
        self.text.edit_reset()
        self.text.edit_modified(False)
        self._loading = False
        self._numbers()
        self.colour()
        if at is not None:
            row = max(1, at - first + 1)
            self.text.mark_set("insert", "%d.0" % row)
            self.text.see("%d.0" % row)
            self.text.yview("%d.0" % max(1, row - 3))

    def lines(self):
        return self.text.get("1.0", "end-1c").split("\n")

    def _numbers(self):
        n = int(self.text.index("end-1c").split(".")[0])
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", "\n".join(str(self.first + i + 1) for i in range(n)))
        self.gutter.configure(state="disabled")
        self.gutter.yview_moveto(self.text.yview()[0])

    def colour(self, rows=None):
        """The key, comments and braces of the lines (rows: 1-based; all when None)."""
        t = self.text
        last = int(t.index("end-1c").split(".")[0])
        rows = range(1, last + 1) if rows is None else rows
        for r in rows:
            for tag in ("key", "comment", "brace"):
                t.tag_remove(tag, "%d.0" % r, "%d.end" % r)
            s = t.get("%d.0" % r, "%d.end" % r)
            c = s.find(self.comment) if self.comment else -1
            code = s if c < 0 else s[:c]
            if c >= 0:
                t.tag_add("comment", "%d.%d" % (r, c), "%d.end" % r)
            st = len(code) - len(code.lstrip())
            rest = code.lstrip()
            if rest[:1] in ("{", "}"):
                t.tag_add("brace", "%d.%d" % (r, st), "%d.%d" % (r, st + 1))
            elif rest:
                k = 0
                while k < len(rest) and not rest[k].isspace():
                    k += 1
                t.tag_add("key", "%d.%d" % (r, st), "%d.%d" % (r, st + k))

    def mark_errors(self, errors):
        """{row (1-based): reason} underlined red; the reason shows on hover and in the bar."""
        self._errors = dict(errors)
        self.text.tag_remove("error", "1.0", "end")
        for r in errors:
            self.text.tag_add("error", "%d.0" % r, "%d.end" % r)
        self.lbl.configure(text=("%d line(s) with a mistake - hover over the red line" % len(errors))
                           if errors else "")

    def _hover(self, e):
        r = int(self.text.index("@%d,%d" % (e.x, e.y)).split(".")[0])
        why = self._errors.get(r)
        if why:
            self.lbl.configure(text="line %d: %s" % (self.first + r, why))

    def _modified(self, e=None):
        if self._loading or not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self._numbers()
        r = int(self.text.index("insert").split(".")[0])
        self.colour(range(max(1, r - 1), r + 2))
        if self._after is not None:
            self.after_cancel(self._after)
        self._after = self.after(500, self._changed)

    def _changed(self):
        self._after = None
        if self.on_change:
            self.on_change(self.lines())

    def flush(self):
        """What is typed handed over at once (before a switch of view or Apply)."""
        if self._after is not None:
            self.after_cancel(self._after)
            self._changed()

    # ---- find ----
    def find_next(self):
        word = self.v_find.get()
        t = self.text
        t.tag_remove("found", "1.0", "end")
        if not word:
            return
        start = t.index("insert +1c")
        at = t.search(word, start, nocase=True, stopindex="end") or t.search(word, "1.0", nocase=True,
                                                                             stopindex=start)
        if not at:
            self.lbl.configure(text="'%s' not found" % word)
            return
        end = "%s+%dc" % (at, len(word))
        t.tag_add("found", at, end)
        t.mark_set("insert", end)
        t.see(at)
        self.lbl.configure(text="line %d" % (self.first + int(at.split(".")[0])))

    # ---- the line's menu ----
    def _menu(self, e):
        if not self.on_menu:
            return
        r = int(self.text.index("@%d,%d" % (e.x, e.y)).split(".")[0])
        line = self.text.get("%d.0" % r, "%d.end" % r)

        def put(new):                                   # the menu's new text for this line
            self.text.edit_separator()
            self.text.delete("%d.0" % r, "%d.end" % r)
            self.text.insert("%d.0" % r, new)
            self.text.edit_separator()
        self.on_menu(e, line, put, self.first + r - 1)
        return "break"


__all__ = ["BlockText"]
