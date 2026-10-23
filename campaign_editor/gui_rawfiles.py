"""Tools > Any game file, as it is written...: every text file the game reads (rawfiles.listing - the mod's own and
the game's under it), found by a part of its name, opened in the editor's notepad (gui_textblock) and changed there.
Kept for Apply by itself (gui_util.AutoKeep): the main window's Preview changes / Apply changes / Undo / Redo, a
backup and Restore as for every other change. The floor of the rule COMPLETENESS (decisions.md): nothing the game
reads is out of reach, even before it has a window of its own - and where it has one, the window is named."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import rawfiles as RF
from .gui_textblock import BlockText
from .gui_util import AutoKeep, one_window
from .plan import Plan

TITLE = "Any game file, as it is written"


@one_window
class RawFilesWindow(AutoKeep, tk.Toplevel):
    _ak_fields = ("edits",)

    def __init__(self, app, rel=None):
        super().__init__(app)
        self.app, self.mod = app, app.mod
        self.title(TITLE)
        self.geometry("1180x720")
        self.transient(app)
        self.edits = {}                                 # path -> the lines typed (only files that differ)
        self.path = None
        top = ttk.Frame(self, padding=8)
        top.pack(fill="both", expand=True)
        body = ttk.Panedwindow(top, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(0, 6))
        left = ttk.Frame(body)
        body.add(left, weight=0)
        fb = ttk.Frame(left)
        fb.pack(side="top", fill="x")
        ttk.Label(fb, text="Find a file").pack(side="left")
        self.v_filter = tk.StringVar()
        ent = ttk.Entry(fb, textvariable=self.v_filter, width=30)
        ent.pack(side="left", padx=4, fill="x", expand=True)
        self.v_filter.trace_add("write", lambda *a: self.fill())
        self.tv = ttk.Treeview(left, columns=("where",), show="tree headings", height=24, selectmode="browse")
        self.tv.heading("#0", text="file (under data/)")
        self.tv.heading("where", text="whose")
        self.tv.column("#0", width=340)
        self.tv.column("where", width=70, stretch=False)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.lbl_count = ttk.Label(left, text="", foreground="#666")
        self.lbl_count.pack(side="bottom", fill="x", pady=(4, 0))
        sb.pack(side="right", fill="y")
        self.tv.pack(side="left", fill="both", expand=True)
        self.tv.bind("<<TreeviewSelect>>", lambda e: self.show())
        right = ttk.Frame(body)
        body.add(right, weight=1)
        self.lbl_about = ttk.Label(right, text="Pick a file on the left.", foreground="#333", wraplength=760,
                                   justify="left")
        self.lbl_about.pack(side="top", fill="x", pady=(0, 4))
        self.block = BlockText(right, on_change=self.typed)
        self.block.pack(fill="both", expand=True)
        bar = ttk.Frame(top)
        bar.pack(fill="x", pady=(6, 0))
        self.lbl = ttk.Label(bar, text="", foreground="#555")
        self.lbl.pack(side="left")
        self._ak_line = ttk.Label(bar, text="", foreground="#c0392b")
        self._ak_line.pack(side="left", padx=8)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Undo this file's changes", command=self.undo_file).pack(side="right", padx=4)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.files = RF.listing(self.mod)
        self.by_path = {f["path"]: f for f in self.files}
        self.fill(rel)
        self.ak_start()

    # ---- the list ----
    def fill(self, rel=None):
        words = self.v_filter.get().lower().split()
        self.tv.delete(*self.tv.get_children())
        shown = 0
        for f in self.files:
            low = f["rel"].lower()
            if words and not all(w in low for w in words):
                continue
            mark = "* " if f["path"] in self.edits else ""
            self.tv.insert("", "end", iid=f["path"], text=mark + f["rel"],
                           values=("the game's" if f["game"] else "the mod's",))
            shown += 1
        self.lbl_count.configure(text="%d of %d file(s)%s" % (shown, len(self.files), (
            " - * changed, waiting for Apply changes" if self.edits else "")))
        want = next((f["path"] for f in self.files if rel and f["rel"].lower() == rel.lower()), None) or self.path
        if want and self.tv.exists(want):
            self.tv.selection_set(want)
            self.tv.see(want)

    def show(self):
        sel = self.tv.selection()
        if not sel or sel[0] == self.path:
            return
        self.block.flush()
        self.path = sel[0]
        f = self.by_path[self.path]
        what, window = RF.about(f["rel"])
        self.lbl_about.configure(text="%s - %s.%s%s" % (
            self.mod.rel(self.path), what, ("  Its own window: %s." % window) if window else "",
            "  The game's own file: a change is written as the mod's copy." if f["game"] else ""))
        lines = self.edits.get(self.path)
        if lines is None:
            lines = self.mod.load(self.path).texts()
        self.block.comment = RF.comment_mark(f["rel"])
        self.block.set_lines(lines)
        self.block.mark_errors(RF.check(f["rel"], lines))
        self.say()

    def typed(self, lines):
        if not self.path:
            return
        f = self.by_path[self.path]
        before = self.path in self.edits
        if lines == self.mod.load(self.path).texts():
            self.edits.pop(self.path, None)
        else:
            self.edits[self.path] = list(lines)
        self.block.mark_errors(RF.check(f["rel"], lines))
        if before != (self.path in self.edits):
            self.tv.item(self.path, text=("* " if self.path in self.edits else "") + f["rel"])
        self.say()
        self.ak_changed()

    def say(self):
        n = len(self.edits)
        self.lbl.configure(text="%d file(s) changed - waiting for Apply changes (Preview changes shows them)." % n
                           if n else "Nothing changed yet.")

    def undo_file(self):
        if self.path in self.edits and messagebox.askyesno(
                TITLE, "Throw away what you typed in this file? It shows as it is on disk again.", parent=self):
            self.edits.pop(self.path)
            p, self.path = self.path, None
            self.fill()
            self.tv.selection_set(p)
            self.show()
            self.ak_changed()

    # ---- kept by itself (gui_util.AutoKeep) ----
    def _ak_key(self):
        return "raw_files"

    def _ak_label(self):
        return "Files changed by hand (%d)" % len(self.edits)

    def _ak_plan(self):
        plan = Plan(self.mod, "raw_files", "raw_files", {})
        for path in sorted(self.edits):
            RF.plan_lines(plan, path, self.edits[path])
        return plan

    def ak_refresh(self):
        p, self.path = self.path, None
        self.fill()
        if p and self.tv.exists(p):
            self.tv.selection_set(p)
            self.show()
        self.say()

    @property
    def _ak_after(self):
        def after(bdir):
            from . import log
            log.write("Files changed by hand (backup %s)" % bdir)
            if self.winfo_exists():
                self.ak_reload()
        return after

    def ak_reload(self):
        self.mod, self.edits = self.app.mod, {}
        self.files = RF.listing(self.mod)
        self.by_path = {f["path"]: f for f in self.files}
        self.ak_refresh()
        self.ak_start()

    def close(self):
        self.block.flush()
        self.ak_close()
        self.destroy()


def open_raw_files(app, rel=None):
    """Tools > Any game file, as it is written... (App.raw_files_window); rel: a file to show at once."""
    if not getattr(app, "mod", None):
        messagebox.showinfo(TITLE, "Load a mod first (Mod or Browse..., then Load).", parent=app)
        return None
    return RawFilesWindow(app, rel)
