"""The Map's 'Scripts' layer (scriptmap.py; the user, 2026-10-18: 'they are dragged like any other object on the map;
a double click opens a window over it, as a town opens, to edit that script; so we see every script on the map at
once'): a scroll on every tile the campaign's scripts and the Lua / Squirrel scripts name; dragged, the line gets
the new tile; double clicked, the lines round it open to be edited. Kept in App.script_edits (Undo / Redo), written
by Apply with the Map's other changes (edit.map_changes 'scripts')."""

import os
import tkinter as tk
from tkinter import ttk

from . import scriptmap as SM

TITLE = "Script"
_OPEN = {}                                         # (path, first line) -> its window


def spots(app):
    """The script places of the campaign shown, with the edits not written yet (read again only when a script file
    or an edit changed)."""
    if not app.mod:
        return []
    camp = app.v_campaign.get()
    try:
        fs = SM.files(app.mod, camp)
    except Exception:                              # no descr_strat, an unreadable campaign: no scrolls
        return []
    key = (os.path.abspath(app.mod.data), camp, repr(sorted((p, sorted(v.items())) for p, v in app.script_edits.items())),
           tuple((p, _mtime(p)) for p, _ in fs))
    got = app.__dict__.get("_script_spots")
    if got is None or got[0] != key:
        got = app._script_spots = [key, SM.spots(app.mod, camp, app.script_edits)]
    return got[1]


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def title(app, sp):
    return "%s:%d" % (os.path.basename(sp["path"]), sp["line"] + 1)


def marks(app):
    """The scrolls: [{'id', 'xy', 'title', 'text', 'changed'}]."""
    out = []
    for sp in spots(app):
        out.append({"id": sp["id"], "xy": sp["xy"], "title": title(app, sp), "text": sp["text"],
                    "changed": sp["line"] in (app.script_edits.get(sp["path"]) or {})})
    return out


def _spot(app, sid):
    return next((s for s in spots(app) if s["id"] == sid), None)


def move(app, sid, xy):
    """A scroll dragged to tile xy: its line names that tile from the next Apply."""
    sp = _spot(app, sid)
    if sp is None or tuple(sp["xy"]) == tuple(xy):
        app.show_map()
        return
    app.remember()
    app.script_edits = SM.move_spot(app.script_edits, sp, xy)
    app.status.set("%s: the place %d, %d moved to %d, %d - Preview, then Apply changes." % (
        title(app, sp), sp["xy"][0], sp["xy"][1], xy[0], xy[1]))
    app.show_map()
    for w in list(_OPEN.values()):                 # an open window of the same lines shows the new numbers
        if w.winfo_exists() and w.path == sp["path"]:
            w.reload()


def open_script(app, sid):
    """The window of the lines round a scroll."""
    sp = _spot(app, sid)
    if sp is None:
        return None
    return open_line(app, sp["path"], sp["line"], sp["code"], sp["sub"])


def open_line(app, path, line, code=False, sub=0):
    """The window of the lines round a script file's line (a scroll, or a town's right click > Scripts of ...)."""
    rs = SM.rows(path, app.script_edits)
    n = next((k for k, r in enumerate(rs) if r[0] == line and r[1] == sub), 0)
    a, b = SM.block(rs, n, code)
    key = (path, rs[a][0] if rs else 0)
    w = _OPEN.get(key)
    if w is not None and w.winfo_exists():
        w.deiconify()
        w.lift()
        return w
    w = _OPEN[key] = ScriptWindow(app, {"path": path, "code": code, "line": line}, key[1], n - a)
    return w


def town_lines(app, region, town, xy):
    """[(label, path, line, code)] of the script lines about a town: the ones naming its tile, then the ones naming
    the town or its region by name (I_SettlementOwner Sarkel, a region in a list ...) - for its right click."""
    import re
    if not app.mod:
        return []
    out, seen = [], set()
    for sp in spots(app):
        if xy and tuple(sp["xy"]) == tuple(xy) and (sp["path"], sp["line"]) not in seen:
            seen.add((sp["path"], sp["line"]))
            out.append((sp["path"], sp["line"], sp["code"], sp["text"]))
    words = {w for w in (region, town) if w}
    if words:
        pat = re.compile(r"(?<![\w-])(%s)(?![\w-])" % "|".join(re.escape(w) for w in words), re.I)
        try:
            fs = SM.files(app.mod, app.v_campaign.get())
        except Exception:
            fs = []
        for path, code in fs:
            try:
                rs = SM.rows(path, app.script_edits)
            except OSError:
                continue
            for i, j, text in rs:
                body = text.split(";")[0] if not code else text
                if (path, i) not in seen and pat.search(body):
                    seen.add((path, i))
                    out.append((path, i, code, text))
    return [("%s:%d   %s" % (os.path.basename(p), i + 1, t.strip()[:70]), p, i, c) for p, i, c, t in out[:40]]


class ScriptWindow(tk.Toplevel):
    """The lines of a script round one place, to be edited as text (as a town's window edits the town); kept by
    themselves a moment after the typing rests (no Keep - the user, 2026-10-16), closing keeps too; Put back returns
    the file's own lines (the opposite)."""

    def __init__(self, app, sp, first, at):
        super().__init__(app)
        self.app, self.path, self.code, self.first, self.at = app, sp["path"], sp["code"], first, at
        self.transient(app)
        self.title("%s - %s:%d" % (TITLE, os.path.basename(sp["path"]), sp["line"] + 1))
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        self.lbl = ttk.Label(frm, text="", wraplength=640, justify="left")
        self.lbl.pack(anchor="w")
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True, pady=6)
        self.txt = tk.Text(box, width=90, height=18, wrap="none", undo=True, font=("Courier New", 10))
        sy = ttk.Scrollbar(box, orient="vertical", command=self.txt.yview)
        sx = ttk.Scrollbar(box, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.txt.pack(side="left", fill="both", expand=True)
        self.txt.tag_configure("here", background="#fff3b0", foreground="#000000")   # the line of the scroll
        bar = ttk.Frame(frm)
        bar.pack(fill="x")
        ttk.Button(bar, text="Put back as in the file", command=self.put_back).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._job = None
        self.txt.bind("<<Modified>>", self._typed)
        self.reload()

    def _typed(self, e=None):
        if not self.txt.edit_modified():
            return
        self.txt.edit_modified(False)
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(400, self.keep)

    def close(self):
        if self._job is not None:
            self.after_cancel(self._job)
            self.keep()
        self.destroy()

    def _block(self):
        rs = SM.rows(self.path, self.app.script_edits)
        n = next((k for k, r in enumerate(rs) if r[0] >= self.first), 0) + self.at
        n = min(max(n, 0), max(len(rs) - 1, 0))
        a, b = SM.block(rs, n, self.code) if rs else (0, 0)
        return rs, a, b, n

    def reload(self):
        rs, a, b, n = self._block()
        self.rs, self.a, self.b = rs, a, b
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(r[2] for r in rs[a:b]))
        self.txt.edit_modified(False)
        self.txt.edit_reset()
        self.txt.tag_add("here", "%d.0" % (n - a + 1), "%d.end" % (n - a + 1))
        self.txt.see("%d.0" % (n - a + 1))
        changed = any(r[0] in (self.app.script_edits.get(self.path) or {}) for r in rs[a:b])
        self.lbl.configure(text="%s, lines %d-%d%s. Edit the lines: kept by themselves for Apply (Ctrl+Z here undoes the typing; "
                           "the bottom Undo the whole change once this window is closed). "
                           "The tile numbers here are what the scroll on the map shows." % (
                               self.app.mod.rel(self.path) if hasattr(self.app.mod, "rel") else self.path, rs[a][0] + 1 if rs else 1, rs[b - 1][0] + 1 if rs else 1,
                               " - changed, not written yet" if changed else ""))

    def keep(self):
        """The text as it stands into App.script_edits (the block grows / shrinks with it)."""
        self._job = None
        if not self.winfo_exists():
            return
        text = self.txt.get("1.0", "end-1c")
        if text == "\n".join(r[2] for r in self.rs[self.a:self.b]):
            return
        self.app.remember()
        self.app.script_edits = SM.set_block(self.app.script_edits, self.path, self.rs, self.a, self.b, text)
        rs = SM.rows(self.path, self.app.script_edits)        # the block as it is now (its rows may be more / fewer)
        n = len(text.split("\n"))
        self.rs, self.b = rs, min(len(rs), self.a + n)
        self.app.status.set("%s: the lines kept - Preview, then Apply changes." % os.path.basename(self.path))
        self.app.show_map()

    def put_back(self):
        mine = self.app.script_edits.get(self.path) or {}
        if not self.rs[self.a:self.b]:
            return
        # the block's file lines, the ones an edit took out (between its rows and the next row) too
        last = self.rs[self.b][0] if self.b < len(self.rs) else max(list(mine) + [self.rs[-1][0]]) + 1
        lines = set(range(self.rs[self.a][0], last))
        if not lines & set(mine):
            self.app.status.set("These lines are as in the file.")
            return
        self.app.remember()
        edits = {p: dict(v) for p, v in self.app.script_edits.items()}
        for i in lines:
            edits[self.path].pop(i, None)
        self.app.script_edits = {p: v for p, v in edits.items() if v}
        self.app.status.set("%s: the lines put back as in the file." % os.path.basename(self.path))
        self.app.show_map()
        self.reload()


__all__ = ["marks", "move", "open_script", "open_line", "town_lines", "spots", "ScriptWindow"]
