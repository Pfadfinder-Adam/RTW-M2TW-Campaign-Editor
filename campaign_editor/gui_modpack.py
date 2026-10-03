"""The window of Tools > Check and install a pack...: every file of a pack with what it would do, a choice per
file, Preview, then the install as one Plan (a backup; Restore undoes it). modpack.py does the work."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .gui_util import one_window, ShortHint
from . import modpack as MP

WORDS = {"install": "put in", "keep": "keep this mod's", "merge": "only its changes", "skip": "-"}
STATE = {"new": "new", "same": "same as the mod's", "replaces": "replaces the mod's"}


def choices_for(e):
    if e["state"] == "same":
        return ["skip"]
    if e["state"] == "new":
        return ["install", "keep"]
    if e["kind"] == "text":
        return ["merge", "install", "keep"]
    return ["install", "keep"]


def open_pack(app):
    """Ask for a pack (.zip, or a folder) and show the check."""
    if not app.mod:
        messagebox.showinfo("Check a pack", "Load a mod first - the pack is checked against it.", parent=app)
        return
    path = filedialog.askopenfilename(parent=app, title="The pack (.zip) - Cancel to pick a folder instead",
                                      filetypes=[("Mod pack", "*.zip"), ("All files", "*.*")])
    if not path:
        path = filedialog.askdirectory(parent=app, title="The pack's folder (the one holding data/)")
    if not path:
        return
    try:
        files, left = MP.read(path)
        entries = MP.check(app.mod, files)
    except Exception as e:
        messagebox.showerror("Check a pack", str(e), parent=app)
        return
    PackWindow(app, path, files, left, entries)


@one_window
class PackWindow(tk.Toplevel):
    def __init__(self, app, path, files, left, entries):
        super().__init__(app)
        # what loses something first, then what has a note, then the rest (in path order)
        entries = sorted(entries, key=lambda e: (not any(s for s, _ in e["notes"]), not e["notes"], e["rel"].lower()))
        self.app, self.path, self.files, self.entries = app, path, files, entries
        self.title("Check and install a pack - %s" % os.path.basename(path.rstrip("/\\")))
        self.geometry("1100x640")
        self.minsize(900, 480)
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        count = {k: sum(1 for e in entries if e["state"] == k) for k in STATE}
        serious = sum(1 for e in entries if any(s for s, _ in e["notes"]))
        ShortHint(frm, justify="left", wraplength=1060, text=(
            "%d file(s) in the pack's data folder, checked against %s: %d new, %d replace this mod's, %d already the "
            "same.%s%s\nA red line would lose something (a file of REX's own, a picture of another size, another "
            "mod's whole file) and is set to keep this mod's file. Text files that differ in a few lines go in as "
            "'only its changes': the pack's changed and added lines are taken, lines it would drop stay. Double click "
            "a line to change what happens to it, or pick lines and use the buttons. Nothing is written before "
            "Install; a backup is made first and Restore undoes it." % (
                len(entries), self.app.mod.data, count["new"], count["replaces"], count["same"],
                ("  %d with a warning." % serious) if serious else "",
                ("  Not put in (outside data/): %s." % ", ".join(left[:5]) + (" ..." if len(left) > 5 else ""))
                if left else ""))).pack(anchor="w")
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True, pady=(8, 4))
        cols = ("state", "choice", "notes")
        self.tree = ttk.Treeview(box, columns=cols, selectmode="extended")
        self.tree.heading("#0", text="File (under data/)")
        self.tree.heading("state", text="What it is")
        self.tree.heading("choice", text="Will")
        self.tree.heading("notes", text="What would be lost / changed")
        self.tree.column("#0", width=330)
        self.tree.column("state", width=150, stretch=False)
        self.tree.column("choice", width=120, stretch=False)
        self.tree.column("notes", width=500)
        self.tree.tag_configure("serious", foreground="#b00")
        self.tree.tag_configure("note", foreground="#b60")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for i, e in enumerate(entries):
            self.tree.insert("", "end", iid=str(i), text=e["rel"])
            self._show(i)
        self.tree.bind("<Double-1>", self._cycle)
        self.detail = ttk.Label(frm, justify="left", wraplength=1060, foreground="#555",
                                text="Pick a line to read everything the check says about it.")
        self.detail.pack(anchor="w", fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._detail)
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=(6, 0))
        for word in ("install", "merge", "keep"):
            ttk.Button(bar, text=WORDS[word].capitalize(), command=lambda w=word: self._set(w)).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Install", command=self.install).pack(side="right", padx=4)
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right")

    def _show(self, i):
        e = self.entries[i]
        notes = "; ".join(t for _, t in e["notes"])
        tag = "serious" if any(s for s, _ in e["notes"]) else ("note" if e["notes"] else "")
        self.tree.item(str(i), values=(STATE[e["state"]], WORDS[e["choice"]], notes), tags=(tag,) if tag else ())

    def _detail(self, *_):
        sel = self.tree.selection()
        if not sel:
            return
        e = self.entries[int(sel[0])]
        text = "%s - %s; will: %s" % (e["rel"], STATE[e["state"]], WORDS[e["choice"]])
        for serious, t in e["notes"]:
            text += "\n%s %s" % ("LOSES:" if serious else "note:", t)
        self.detail.configure(text=text)

    def _cycle(self, ev):
        iid = self.tree.identify_row(ev.y)
        if not iid:
            return
        e = self.entries[int(iid)]
        opts = choices_for(e)
        e["choice"] = opts[(opts.index(e["choice"]) + 1) % len(opts)] if e["choice"] in opts else opts[0]
        self._show(int(iid))

    def _set(self, word):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Check a pack", "Pick one or more lines first.", parent=self)
            return
        for iid in sel:
            e = self.entries[int(iid)]
            if word in choices_for(e):
                e["choice"] = word
                self._show(int(iid))

    def _plan(self):
        from .plan import Plan
        plan = Plan(self.app.mod, "pack", "mod_pack", {})
        MP.install(plan, self.files, self.entries)
        return plan

    def preview(self):
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror("Check a pack", str(e), parent=self)
            return
        self.app.show_text("Install a pack - preview (nothing written)", plan.report())

    def install(self):
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror("Check a pack", str(e), parent=self)
            return
        n = len(plan.changed_files())
        if not n:
            messagebox.showinfo("Check a pack", "Nothing picked to go in.", parent=self)
            return
        risky = [w for _, w in plan.warnings if w != "nothing picked to go in"]
        if not messagebox.askyesno("Install a pack", "%sWrite %d file(s)? A backup is made first (Restore undoes it)."
                                   % (("These go in although they lose something:\n- " + "\n- ".join(risky[:6]) +
                                       "\n\n") if risky else "", n), icon="warning" if risky else "question",
                                   parent=self):
            return
        bdir = plan.apply()
        from . import log
        log.write("Pack %s installed (backup %s)\n%s" % (self.path, bdir, plan.report()))
        self.destroy()
        self.app.load()
        self.app.status.set("Pack installed: %d file(s) written (backup %s)." % (n, bdir))
