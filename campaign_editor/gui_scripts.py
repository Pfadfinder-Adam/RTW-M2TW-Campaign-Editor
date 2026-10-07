"""Scripts in the game... (Add-ons): every script the engine runs from script/modules - REX for Rome, M2EX for
Medieval II - listed with what it is; one picked shows its words and its settings, and can be turned off / on, deleted
or have its settings written (scriptmods: each through a Plan - the whole list of changes asked first, a backup,
Restore). The user asked for it: 'to delete an old one or change its settings'."""

import datetime
import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import log
from . import scriptmods as SM
from .gui_addons import SettingsForm
from .gui_util import ScrollFrame
from .plan import Plan

TITLE = "Scripts in the game"


class ScriptsWindow(SettingsForm, tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.mod = app, app.mod
        self.vars, self.items = {}, []
        self.title(TITLE)
        self.transient(app)
        self.geometry("1100x640")
        top = ttk.Frame(self, padding=(10, 8, 10, 0))
        top.pack(fill="x")
        self.head = ttk.Label(top, justify="left", wraplength=1060)
        self.head.pack(anchor="w")
        # the test mod's scripts stay in the game's folder when the test mod is thrown away: one press takes them out
        self.testbar = ttk.Frame(top)
        self.testline = ttk.Label(self.testbar, justify="left", wraplength=760)
        self.testline.pack(side="left", anchor="w")
        ttk.Button(self.testbar, text="Take out every script the test mod put in",
                   command=self.take_out_test).pack(side="left", padx=(10, 0))
        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=8)
        left = ttk.Frame(body)
        body.add(left, weight=0)
        self.tv = ttk.Treeview(left, columns=("what", "on"), show="tree headings", selectmode="browse", height=18)
        self.tv.heading("#0", text="Script")
        self.tv.heading("what", text="What it is")
        self.tv.heading("on", text="Runs")
        self.tv.column("#0", width=190)
        self.tv.column("what", width=170)
        self.tv.column("on", width=50, anchor="center")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tv.pack(side="left", fill="both", expand=True)
        self.tv.bind("<<TreeviewSelect>>", lambda e: self.show())
        self.sf = ScrollFrame(body, padding=(10, 0, 0, 0))
        body.add(self.sf, weight=1)
        # the words on the right wrap at the width they get (no text cut at the edge)
        self.sf.bind("<Configure>", lambda e: self._wrap(e.width), add="+")
        self.fill()

    # ---- the list ----
    def fill(self, keep=None):
        self.items = SM.scripts(self.mod)
        folders = SM.folders(self.mod)
        if not folders:
            self.head.configure(text=(
                "No script/modules folder for this mod: REX (Rome) and M2EX (Medieval II) run the scripts of "
                "<game>/script/modules - the engine is not beside the game, or it has no such folder yet. Add-ons "
                "and the Module builder make it when they put a script in."))
        else:
            self.head.configure(text=(
                "Every script the engine runs from %s: REX (Rome) and M2EX (Medieval II) require each .nut there "
                "when the campaign starts. Turned off = renamed .nut.off - kept, not run. Pick one to see what it is, "
                "change its settings, turn it off or delete it; every change asks first and makes a backup "
                "(Restore undoes it)." % folders[0][0]))
        test = [x for x in self.items if x.test]
        if test:
            self.testline.configure(text="%d script(s) here were put in by the editor's test mod (CE_Test): %s. "
                                    "They stay in the game's folder when the test mod is thrown away." % (
                                        len(test), ", ".join(x.file for x in test)))
            self.testbar.pack(anchor="w", fill="x", pady=(6, 0))
        else:
            self.testbar.pack_forget()
        self.tv.delete(*self.tv.get_children())
        many = len(folders) > 1
        parents = {}
        for folder, runs in folders:
            if many:
                parents[folder] = self.tv.insert("", "end", text=folder, open=True, values=(
                    "the engine runs these" if runs else "NOT run (no main.nut loading them)", ""))
        for i, s in enumerate(self.items):
            self.tv.insert(parents.get(s.folder, ""), "end", iid="s%d" % i, text=s.file + ("" if s.on else "  (off)"),
                           values=(s.kind, "yes" if s.on and s.runs and not s.lua else "no"))
        pick = next((i for i, s in enumerate(self.items) if keep and s.file.lower() == keep.lower()), 0 if self.items
                    else None)
        if pick is not None:
            self.tv.selection_set("s%d" % pick)
            self.tv.see("s%d" % pick)
        else:
            self.show()

    def picked(self):
        sel = self.tv.selection()
        if not sel or not sel[0].startswith("s"):
            return None
        return self.items[int(sel[0][1:])]

    def addon(self):
        s = self.picked()
        return s.addon if s else None

    def _wrap(self, width):
        for w in self.sf.inner.winfo_children():
            if isinstance(w, ttk.Label) and int(w.grid_info().get("columnspan", 1)) > 1:
                w.configure(wraplength=max(200, width - 30))

    # ---- one script ----
    def show(self):
        inner = self.sf.inner
        for w in inner.winfo_children():
            w.destroy()
        s = self.picked()
        if s is None:
            ttk.Label(inner, text="No script here yet." if not self.items else "Pick a script on the left.").grid(
                row=0, column=0, sticky="w")
            return
        ttk.Label(inner, text=s.title, font=("", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(inner, text=s.addon.summary, wraplength=640, justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(2, 4))
        when = datetime.datetime.fromtimestamp(s.mtime).strftime("%Y-%m-%d %H:%M")
        state = ("runs when the campaign starts" if s.on and s.runs and not s.lua else
                 "turned off - kept, not run" if not s.on else
                 "a Lua file - the engines run .nut modules, this one does nothing" if s.lua else
                 "not run - the main.nut of its folder does not load the modules")
        ttk.Label(inner, foreground="#555", wraplength=640, justify="left", text="%s, %s.\nThe file %s, %d bytes, "
                  "changed %s (Open the folder shows it)." % (s.kind[0].upper() + s.kind[1:], state,
                                                            os.path.basename(s.path), s.size, when)).grid(
            row=2, column=0, columnspan=3, sticky="w")
        r = 3
        if s.addon.settings:
            ttk.Label(inner, text="Its settings", font=("", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(10, 2))
            r = self.build_form(inner, s.addon, s.values, r + 1)
        else:
            self.vars = {}
            ttk.Label(inner, foreground="#555", wraplength=640, justify="left", text=(
                "No settings found in it (settings are the UPPER_CASE 'local NAME = value' lines at the top of a "
                "script).")).grid(row=r, column=0, columnspan=3, sticky="w", pady=(10, 0))
            r += 1
        bar = ttk.Frame(inner)                    # two rows: what changes it, then what only shows it
        bar.grid(row=r, column=0, columnspan=3, sticky="w", pady=(12, 0))
        if s.addon.settings:
            ttk.Button(bar, text="Write the settings", command=self.write_settings).grid(row=0, column=0, sticky="we")
        ttk.Button(bar, text="Turn it on" if not s.on else "Turn it off", command=self.switch).grid(
            row=0, column=1, sticky="we", padx=(6, 0))
        ttk.Button(bar, text="Delete it...", command=self.delete).grid(row=0, column=2, sticky="we", padx=(24, 0))
        ttk.Button(bar, text="Show the code", command=lambda: self.app.show_text(
            "%s - %s" % (s.file, s.title), s.text)).grid(row=1, column=0, sticky="we", pady=(6, 0))
        ttk.Button(bar, text="Open the folder", command=lambda: _open(s.folder)).grid(
            row=1, column=1, sticky="we", padx=(6, 0), pady=(6, 0))
        inner.columnconfigure(2, weight=1)
        self._wrap(self.sf.winfo_width())

    # ---- writing ----
    def _write(self, s, make, what, keep=None, name=None):
        plan = Plan(s.plan_mod(self.mod), "scripts", name or os.path.splitext(s.file)[0], {})
        try:
            if make(plan) is False or not plan.changed_files():
                messagebox.showinfo(TITLE, "Nothing to change.", parent=self)
                return
        except ValueError as e:
            messagebox.showerror(TITLE, "%s\n\nNothing was written." % e, parent=self)
            return
        if not messagebox.askyesno(TITLE, "%s\n\n%s? A backup is made first (Tools > Restore a backup undoes it)."
                                   % (plan.report(), what), parent=self):
            return
        try:
            bdir = plan.apply()
        except Exception as e:
            messagebox.showerror(TITLE, "Not written: %s" % e, parent=self)
            return
        log.write("Scripts in the game: %s - %s (backup %s)\n%s" % (s.file, what, bdir, plan.report()))
        self.app.status.set("%s: %s (backup %s)." % (s.file, what, bdir))
        self.fill(keep or s.file)

    def write_settings(self):
        s = self.picked()
        if s:
            values = self.values()
            self._write(s, lambda plan: SM.plan_settings(plan, s, values), "Write its settings")

    def switch(self):
        s = self.picked()
        if s:
            self._write(s, lambda plan: SM.plan_switch(plan, s, not s.on),
                        "Turn %s %s" % (s.file, "on" if not s.on else "off"))

    def take_out_test(self):
        """Every script of the test mod deleted - one Plan (one backup) for each folder they are in."""
        by = {}
        for x in self.items:
            if x.test:
                by.setdefault(x.folder, []).append(x)
        for items in by.values():
            self._write(items[0], lambda plan, items=items: SM.plan_take_out_test(plan, items),
                        "Take out the %d script(s) the test mod put in" % len(items), name="test_mod_scripts")

    def delete(self):
        s = self.picked()
        if s:
            self._write(s, lambda plan: SM.plan_delete(plan, s), "Delete %s" % os.path.basename(s.path))


def _open(folder):
    from .gui_settings import open_folder
    open_folder(folder)


def open_scripts(app):
    """The window (Add-ons > Scripts in the game...)."""
    if not app.mod:
        messagebox.showinfo(TITLE, "Load a mod first.")
        return None
    return ScriptsWindow(app)
