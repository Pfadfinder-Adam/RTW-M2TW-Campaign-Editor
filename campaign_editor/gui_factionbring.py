"""New faction > 'From another mod...': pick a mod of the same game and one of its factions - the New faction
window is filled from it (names, colours, descriptions, a template of the same culture) and Apply brings what is
the faction's own (factionbring.py: its units, names, figures on the map and in battle, flags, pictures).
The other mod is only read."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import factionbring as FB
from . import packs
from .gui_util import one_window, window_body
from .moddata import ModData


@one_window
class FactionBringWindow(tk.Toplevel):
    def __init__(self, app, on_pick):
        super().__init__(app.root if hasattr(app, "root") else app)
        self.app, self.on_pick, self.src = app, on_pick, None
        self.title("A faction from another mod")
        frm, bar = window_body(self, 640, 560)
        ttk.Label(frm, text="Pick the mod, then its faction. The mod is only read - nothing in it changes. It must be "
                            "a mod of the same game (Rome to Rome, Medieval II to Medieval II); the list shows only "
                            "those.", wraplength=600, justify="left").pack(anchor="w")
        self.mods = packs.same_game_mods(getattr(app, "_mods", []), app.mod)
        self.v_path = tk.StringVar()
        if self.mods:
            ttk.Label(frm, text="Mods in your game folder:").pack(anchor="w", pady=(8, 0))
            self.lb_mods = self._list(frm, min(8, len(self.mods)))
            for label, d in self.mods:
                self.lb_mods.insert("end", "%s    %s" % (label, d))
            self.lb_mods.bind("<<ListboxSelect>>", self._mod_clicked)
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="Its data folder").pack(side="left")
        ttk.Entry(row, textvariable=self.v_path).pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(row, text="Browse...", command=self._browse).pack(side="left")
        ttk.Button(row, text="Read", command=self._read).pack(side="left", padx=(4, 0))
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(10, 0))
        ttk.Label(row, text="Campaign").pack(side="left")
        self.v_camp = tk.StringVar()
        self.cb_camp = ttk.Combobox(row, textvariable=self.v_camp, state="readonly", width=30)
        self.cb_camp.pack(side="left", padx=4)
        ttk.Label(frm, text="Its factions:").pack(anchor="w", pady=(6, 0))
        self.lb_fac = self._list(frm, 10)
        self.lb_fac.bind("<Double-Button-1>", lambda e: self._ok())
        self.factions = []
        self.b_ok = ttk.Button(bar, text="Bring this faction", command=self._ok, state="disabled")
        self.b_ok.pack(side="right")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 6))

    def _list(self, parent, height):
        box = ttk.Frame(parent)
        box.pack(fill="both", expand=True, pady=(2, 0))
        lb = tk.Listbox(box, height=height, exportselection=False)
        sb = ttk.Scrollbar(box, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        return lb

    def _mod_clicked(self, e=None):
        sel = self.lb_mods.curselection()
        if sel:
            self.v_path.set(self.mods[sel[0]][1])
            self._read()

    def _browse(self):
        d = filedialog.askdirectory(parent=self, title="The other mod's data folder")
        if d:
            self.v_path.set(d)
            self._read()

    def _read(self):
        path = self.v_path.get().strip()
        if not path:
            return
        try:
            src = ModData(path)
        except Exception as err:
            messagebox.showerror(self.title(), str(err), parent=self)
            return
        if os.path.normcase(os.path.abspath(src.data)) == os.path.normcase(os.path.abspath(self.app.mod.data)):
            messagebox.showerror(self.title(), "that is this mod - pick another one", parent=self)
            return
        if packs.game_kind(src) != packs.game_kind(self.app.mod):
            messagebox.showerror(self.title(), "a faction goes between mods of one game - this one is %s, that one %s" % (
                _game(self.app.mod), _game(src)), parent=self)
            return
        self.src = src
        camps = src.campaigns()
        self.cb_camp.configure(values=camps)
        self.v_camp.set(camps[0] if camps else "")
        self.factions = FB.factions(src)
        shown = _shown(src, self.v_camp.get())
        self.lb_fac.delete(0, "end")
        for name, culture in self.factions:
            self.lb_fac.insert("end", "%s  (%s%s)" % (shown.get(name) or name, name, ", " + culture if culture else ""))
        self.b_ok.configure(state="normal" if self.factions else "disabled")

    def _ok(self):
        sel = self.lb_fac.curselection()
        if not self.src or not sel:
            messagebox.showinfo(self.title(), "pick one of its factions", parent=self)
            return
        faction, culture = self.factions[sel[0]]
        camp = self.v_camp.get() or None
        fields = FB.window_fields(self.src, camp, faction)
        self.destroy()
        self.on_pick({"src": self.src.data, "faction": faction, "campaign": camp, "culture": culture,
                      "fields": fields})


def _game(mod):
    return "Medieval II" if packs.game_kind(mod) == "medieval2" else "Rome"


def _shown(src, campaign):
    """{faction: the name players read} of the other mod (empty where it cannot be read)."""
    from .build import template_display
    out = {}
    for name, _ in FB.factions(src):
        try:
            out[name] = template_display(src, name, campaign).get("display_name")
        except Exception:
            pass
    return out
