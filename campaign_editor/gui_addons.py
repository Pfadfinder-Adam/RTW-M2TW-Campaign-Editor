"""The Add-ons work: ready-made scripts (Sack Settlement ...) and anyone's (Add an add-on...) put into the game with
their settings picked here; Share... packs one as a zip for others. It writes on its own (Preview / Put it in / Take
it out, each with a backup); the bottom Apply is for the other works."""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import addons as AD
from .gui_util import ScrollFrame
from .plan import Plan


# the line each built-in add-on writes into the game's log once it runs
LOADED = {"sack_settlement": "'[SACK] Sack Settlement module loaded'.",
          "raze_settlement": "'[RAZE] Raze Settlement module loaded'.",
          "avoid_growth": "'[GROWTH] Avoid Growth module loaded'."}


class SettingsForm:
    """The settings of a script as a form: a row each (its words, a field, its help), shown or hidden as a choice
    asks. The Add-ons panel and the window of the scripts in the game share it. The owner has .app, .mod and
    .addon() (the add-on whose settings these are); the form keeps its fields in .vars."""

    def build_form(self, inner, a, values, r):
        """A row per setting of add-on a from grid row r on, filled with values. -> the next free row."""
        self.vars = {}
        rows = {}
        for s in a.settings:
            lbl = ttk.Label(inner, text=s.label)
            lbl.grid(row=r, column=0, sticky="nw", padx=(0, 8), pady=2)
            w = self._widget(inner, s, values.get(s.var))
            w.grid(row=r, column=1, sticky="w", pady=2)
            hint = ttk.Label(inner, text=s.help, foreground="#666", wraplength=260, justify="left")
            hint.grid(row=r, column=2, sticky="we", padx=6)
            hint.bind("<Configure>", lambda e, h=hint: h.configure(wraplength=max(60, e.width - 4)), add="+")
            rows[s.var] = (lbl, w, hint, r)
            r += 1

        def visible(*_):
            for s in a.settings:
                if s.when:
                    on = self._value(a.settings[[x.var for x in a.settings].index(s.when[0])]) in s.when[1]
                    for x in rows[s.var][:3]:
                        if on:
                            x.grid()
                        else:
                            x.grid_remove()
        for s in a.settings:
            if s.kind == "choice":
                self.vars[s.var].trace_add("write", visible)
        visible()
        return r

    def _widget(self, parent, s, value):
        if s.kind == "bool":
            v = self.vars[s.var] = tk.BooleanVar(value=bool(value))
            return ttk.Checkbutton(parent, variable=v)
        if s.kind == "choice":
            labels = dict(s.choices)
            v = self.vars[s.var] = tk.StringVar(value=value if value in labels else s.choices[0][0])
            shown = tk.StringVar(value=labels[v.get()])
            cb = ttk.Combobox(parent, textvariable=shown, values=[l for _, l in s.choices], state="readonly", width=46)
            shown.trace_add("write", lambda *a: v.set(next(k for k, l in s.choices if l == shown.get())))
            return cb
        if s.kind in ("list", "set") and a_picks(self, s) == "factions":
            box = ttk.Frame(parent)
            lb = tk.Listbox(box, selectmode="multiple", height=6, width=40, exportselection=False)
            sb = ttk.Scrollbar(box, orient="vertical", command=lb.yview)
            lb.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            lb.pack(side="left")
            from .build import faction_label
            names = [n for n, _ in self.mod.factions() if n != "slave"]
            shown = self.app.shown_names() if hasattr(self.app, "shown_names") else {}
            for i, n in enumerate(names):
                lb.insert("end", faction_label(n, shown.get(n)))
                if n in (value or []):
                    lb.selection_set(i)
            self.vars[s.var] = (lb, names)
            return box
        if s.kind in ("list", "set"):
            v = self.vars[s.var] = tk.StringVar(value=", ".join(value or []))
            if not a_picks(self, s):
                return ttk.Entry(parent, textvariable=v, width=46)
            box = ttk.Frame(parent)
            ttk.Entry(box, textvariable=v, width=38).pack(side="left")
            ttk.Button(box, text="Pick...", command=lambda: self.pick(s, v)).pack(side="left", padx=4)
            return box
        v = self.vars[s.var] = tk.StringVar(value="" if value is None else str(value))
        return ttk.Entry(parent, textvariable=v, width=46 if s.kind == "text" else 10)

    def pick(self, s, var):
        """Pick names for a setting from this mod's own file (building chains, unit types)."""
        what = a_picks(self, s)
        names = AD.mod_names(self.mod, what)
        if not names:
            messagebox.showinfo("Add-ons", "This mod has no %s to pick from - type the names." % (
                "export_descr_buildings.txt" if what == "chains" else "export_descr_unit.txt"), parent=self)
            return
        now = {x.strip().lower() for x in var.get().split(",") if x.strip()}
        w = tk.Toplevel(self)
        w.title(s.label)
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="%s - from this mod's %s. Click to tick or untick." % (
            s.label, "buildings" if what == "chains" else "units"), wraplength=420).pack(anchor="w")
        body = ttk.Frame(frm)
        body.pack(fill="both", expand=True, pady=6)
        lb = tk.Listbox(body, selectmode="multiple", height=18, width=44, exportselection=False)
        sb = ttk.Scrollbar(body, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for i, n in enumerate(names):
            lb.insert("end", n)
            if n.lower() in now:
                lb.selection_set(i)

        def ok():
            var.set(", ".join(names[i] for i in lb.curselection()))
            w.destroy()
        bar = ttk.Frame(frm)
        bar.pack(anchor="e")
        ttk.Button(bar, text="OK", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    def _value(self, s):
        v = self.vars[s.var]
        if isinstance(v, tuple):
            lb, names = v
            return [names[i] for i in lb.curselection()]
        raw = v.get()
        if s.kind == "int":
            try:
                return int(str(raw).strip())
            except ValueError:
                return str(raw)                     # not a number: check() says so
        if s.kind == "float":
            try:
                return float(str(raw).strip().replace(",", "."))
            except ValueError:
                return str(raw)
        if s.kind in ("list", "set"):
            return [x.strip() for x in str(raw).split(",") if x.strip()]
        return raw

    def values(self):
        a = self.addon()
        return {s.var: self._value(s) for s in a.settings if s.var in self.vars}


class AddonsPanel(SettingsForm, ttk.Frame):
    kind = "add-ons"

    def __init__(self, master, app):
        super().__init__(master)
        self.app, self.mod = app, None
        self.vars = {}
        side = ttk.Frame(self, padding=(0, 0, 8, 0))
        side.pack(side="left", fill="y")
        ttk.Label(side, text="Add-ons", font=("", 10, "bold")).pack(anchor="w")
        self.lb = tk.Listbox(side, width=28, height=10, exportselection=False)
        self.lb.pack(fill="y", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.show())
        ttk.Label(side, text="scripts that add something\nnew to the game", foreground="#666").pack(anchor="w")
        for text, cmd in (("Add an add-on...", self.add), ("Share...", self.share),
                          ("Remove from the list", self.drop), ("New module (no code)...", self.builder)):
            ttk.Button(side, text=text, command=cmd).pack(fill="x", pady=(4, 0))
        ttk.Button(side, text="Scripts in the game...", command=self.scripts).pack(fill="x", pady=(10, 0))
        ttk.Label(side, foreground="#666", justify="left", wraplength=190, text=(
            "Add an add-on: anyone's REX / M2EX script (.nut) or a zip with one - its settings are found by "
            "themselves. Only from people you trust: a script runs inside the game.")).pack(anchor="w", pady=(4, 0))
        self.sf = ScrollFrame(self)
        self.sf.pack(side="left", fill="both", expand=True)
        self.fill()

    def fill(self, pick=None):
        self.addons = AD.library()
        self.lb.delete(0, "end")
        for a in self.addons:
            self.lb.insert("end", a.title + ("   (added)" if a.own else ""))
        keys = [a.key for a in self.addons]
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(keys.index(pick) if pick in keys else self._first_fitting())

    def _first_fitting(self):
        """The first add-on made for the loaded mod's game (Sack for Rome, Raze for Medieval II)."""
        if getattr(self, "mod", None) is None:
            return 0
        from .limits import game_kind
        game = game_kind(self.mod)
        return next((i for i, a in enumerate(self.addons) if a.fits(game)), 0)

    # ---- what the window asks of a work ----
    def rebind(self, mod):
        self.mod = mod
        sel = self.lb.curselection()
        if mod is not None and (not sel or not self.addons[sel[0]].fits(__import__(
                "campaign_editor.limits", fromlist=["game_kind"]).game_kind(mod))):
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(self._first_fitting())
        self.show()
        return 0

    def dirty(self):
        return False

    def pending(self):
        return 0

    def make_plan(self):
        raise ValueError("Add-ons write on their own: use Preview / Put it in on the Add-ons page.")

    # ---- the page ----
    def addon(self):
        sel = self.lb.curselection()
        return self.addons[sel[0] if sel else 0]

    def add(self):
        from tkinter import filedialog
        src = filedialog.askopenfilename(parent=self, title="An add-on: a Squirrel script or a zip with one",
                                         filetypes=[("Add-on", "*.nut *.zip"), ("All files", "*.*")])
        if not src:
            return
        try:
            got = AD.add_to_library(src)
        except Exception as e:
            messagebox.showerror("Add-ons", str(e), parent=self)
            return
        from . import log
        log.write("Add-on(s) added to the list: %s (from %s)" % (", ".join(a.file for a in got), src))
        self.fill(got[0].key)
        self.show()
        a = got[0]
        messagebox.showinfo("Add-ons", "%s is in the list.\n\n%d setting(s) found in it%s. Pick them, then Put it "
                                       "in." % (a.title, len(a.settings), (": " + ", ".join(s.label for s in
                                                                                  a.settings[:6]) + (
                                           " ..." if len(a.settings) > 6 else "")) if a.settings else ""),
                            parent=self)

    def share(self):
        from tkinter import filedialog
        a = self.addon()
        out = filedialog.asksaveasfilename(parent=self, title="Share %s" % a.title, defaultextension=".zip",
                                           initialfile="%s.zip" % a.key, filetypes=[("Zip", "*.zip")])
        if not out:
            return
        with_values = self.mod is not None and self.vars and messagebox.askyesno(
            "Share", "With the settings picked here?\n\nYes: your settings\nNo: the script as it came", parent=self)
        try:
            AD.share(a, out, self.values() if with_values else None)
        except Exception as e:
            messagebox.showerror("Share", str(e), parent=self)
            return
        messagebox.showinfo("Share", "Saved %s - give it to others: Add-ons > Add an add-on... takes it." % out,
                            parent=self)

    def scripts(self):
        """Every script the engine runs from script/modules - ours and anyone's: turn off, delete, settings."""
        from .gui_scripts import open_scripts
        run = self.app.once("scripts_in_game", lambda: open_scripts(self.app)) if hasattr(self.app, "once") else \
            (lambda: open_scripts(self.app))
        run()

    def builder(self, recipe=None):
        """The Module builder: a new add-on made of blocks, or a builder-made one opened again."""
        from .gui_modbuilder import open_builder
        open_builder(self.app, recipe)

    @staticmethod
    def recipe_of(a):
        """The Module builder's recipe of an add-on someone added, or None."""
        if not a.own:
            return None
        from . import modbuilder as MB
        try:
            return MB.recipe_of(a.template())
        except OSError:
            return None

    def drop(self):
        a = self.addon()
        if not a.own:
            messagebox.showinfo("Add-ons", "%s is built in - it stays in the list." % a.title, parent=self)
            return
        if not messagebox.askyesno("Add-ons", "Take %s off the list? (If it is put into a game it stays there - "
                                              "Take it out does that.)" % a.title, parent=self):
            return
        AD.remove_from_library(a)
        self.fill()
        self.show()

    def show(self):
        inner = self.sf.inner
        for w in inner.winfo_children():
            w.destroy()
        a = self.addon()
        ttk.Label(inner, text=a.title, font=("", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(inner, text=a.summary, wraplength=760, justify="left").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(2, 4))
        ttk.Label(inner, text="Needs: " + a.needs, foreground="#555", wraplength=760, justify="left").grid(
            row=2, column=0, columnspan=3, sticky="w")
        if not self.mod:
            ttk.Label(inner, text="Load a mod first (Mod or Browse..., then Load).").grid(row=3, column=0, sticky="w")
            return
        from .packs import game_kind
        if not a.fits(game_kind(self.mod)):
            ttk.Label(inner, foreground="#a33", text="This add-on is for %s - the loaded mod is of the other game."
                      % ("Medieval II" if a.game == "medieval2" else "Rome: Total War")).grid(
                row=3, column=0, columnspan=3, sticky="w", pady=6)
            return
        dst = AD.target(self.mod, a)
        now = AD.installed(self.mod, a)
        ttk.Label(inner, foreground="#2a7a1f" if now is not None else "#b60", wraplength=760, justify="left", text=(
            "Put in: %s - the settings below are the ones it has now." % dst if now is not None else
            "Not put in yet. It goes to %s - pick the settings, then Put it in." % dst)).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(6, 8))
        values = now if now is not None else AD.read_settings(a, a.template())
        r = self.build_form(inner, a, values, 4)
        bar = ttk.Frame(inner)
        bar.grid(row=r, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="left")
        ttk.Button(bar, text="Update it" if now is not None else "Put it in", command=self.install).pack(
            side="left", padx=6)
        if now is not None:
            ttk.Button(bar, text="Take it out", command=self.remove).pack(side="left")
        recipe = self.recipe_of(a)
        if recipe is not None:
            ttk.Button(bar, text="Change it in the Module builder...",
                       command=lambda: self.builder(recipe)).pack(side="left", padx=6)
        ttk.Label(inner, foreground="#555", wraplength=760, justify="left", text=(
            "Every write makes a backup first (Tools > Restore a backup undoes it). Then start the campaign: the "
            "script console says " + (LOADED[a.key] if a.key in LOADED else "that the module %s was "
                                      "loaded (or why not)." % os.path.splitext(a.file)[0]) +
            " (Rome with REX writes it into system.log.txt too; Medieval II with M2EX only while the game starts up)."
        )).grid(
            row=r + 1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        inner.columnconfigure(2, weight=1)

    def _plan(self, remove=False):
        a = self.addon()
        mod = AD.plan_mod(self.mod, a)
        plan = Plan(mod, "addon", a.key, {})
        if remove:
            AD.plan_remove(plan, a, self.mod)
        else:
            AD.plan_install(plan, a, self.values(), self.mod)
        return plan

    def preview(self):
        try:
            plan = self._plan()
            a = self.addon()
            text = AD.render(a, a.template(), self.values())
        except Exception as e:
            messagebox.showerror("Add-ons", "%s\n\nNothing was written." % e, parent=self)
            return
        lines = [l for l in text.splitlines() if l.startswith("local ") and any(
            l.startswith("local %s " % s.var) for s in self.addon().settings)]
        self.app.show_text("Add-ons - preview (nothing written)", plan.report() + "\n\nThe settings in the script:\n  "
                           + "\n  ".join(lines))

    def install(self):
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror("Add-ons", "%s\n\nNothing was written." % e, parent=self)
            return
        if not plan.changed_files():
            messagebox.showinfo("Add-ons", "It is in already with exactly these settings - nothing to write.",
                                parent=self)
            return
        if not messagebox.askyesno("Add-ons", "%s\n\nWrite it? A backup is made first (Restore undoes it)."
                                   % plan.report(), parent=self):
            return
        self._apply(plan, "put in")

    def remove(self):
        plan = self._plan(remove=True)
        if not messagebox.askyesno("Add-ons", "Take %s out of the game? A backup is made first (Restore puts it "
                                              "back)." % self.addon().title, parent=self):
            return
        self._apply(plan, "taken out")

    def _apply(self, plan, what):
        bdir = plan.apply()
        from . import log
        log.write("Add-on %s %s (backup %s)\n%s" % (self.addon().title, what, bdir, plan.report()))
        self.app.status.set("%s %s (backup %s) - start the campaign to use it." % (self.addon().title, what, bdir))
        self.show()


def a_picks(panel, s):
    """What a setting is picked from (chains, units, factions), or None."""
    return panel.addon().picks.get(s.var)

