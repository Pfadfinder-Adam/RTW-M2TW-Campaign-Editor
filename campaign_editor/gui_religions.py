"""The Religions work (Medieval II; Barbarian Invasion's beliefs): the game's religions and every region's shares in one place - the same state the
Map's Religions... / New religion... dialogs keep (App.region_religions, App.new_religions), written by the bottom
Apply with the rest of the campaign work. Rome has no religions: the page says so."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import ShortHint

APP = "RTW & M2TW Campaign Editor"


class ReligionsPanel(ttk.Frame):
    kind = "religions"

    def __init__(self, master, app):
        super().__init__(master)
        self.app, self.mod = app, None
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Religions", font=("", 10, "bold")).pack(side="left")
        self.lbl = ttk.Label(top, foreground="#666")
        self.lbl.pack(side="left", padx=8)
        ShortHint(self, foreground="#666", wraplength=1100, justify="left", text=(
            "Medieval II: the religions of the game and how many of each region's people follow each (100 in all); "
            "Barbarian Invasion: its beliefs (a town follows them by its buildings - no region shares). "
            "A new religion is written everywhere the game needs it; its shares are set region by region. The same "
            "as Religions... / New religion... on the Map - Preview, then Apply changes writes them.")).pack(
            anchor="w", pady=(4, 4))
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        side = ttk.Frame(body, padding=(0, 0, 8, 0))
        side.pack(side="left", fill="y")
        ttk.Label(side, text="Religions of the game").pack(anchor="w")
        self.lb = tk.Listbox(side, width=34, height=12, exportselection=False)
        self.lb.pack(fill="y")
        for text, cmd in (("New religion...", self.new_religion), ("Shares of the region...", self.shares),
                          ("Show on the map", self.show_on_map)):
            ttk.Button(side, text=text, command=cmd).pack(fill="x", pady=(4, 0))
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.tv = ttk.Treeview(right, show="tree headings", height=22)
        sb = ttk.Scrollbar(right, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.bind("<Double-1>", lambda e: self.shares() if self.tv.identify_row(e.y) else None)

    # ---- what the window asks of a work ----
    def rebind(self, mod):
        self.mod = mod
        self.fill()
        return 0

    def dirty(self):
        return False                          # its changes sit in the campaign work (the faction tabs' Apply)

    def pending(self):
        return 0

    def make_plan(self):
        return self.app._faction_plan()

    # ---- the page ----
    def names(self):
        from . import religions as RL
        have = RL.names(self.mod) if self.mod else []
        return have + [r["name"] for r in self.app.new_religions if r["name"] not in have]

    def shares_of(self, region):
        app = self.app
        new = app._new_region(region) if hasattr(app, "_new_region") else None
        return (new or {}).get("religions") or app.region_religions.get(region) or \
            (app.regions.get(region) or {}).get("religions") or {}

    def fill(self):
        self.lb.delete(0, "end")
        for i in self.tv.get_children():
            self.tv.delete(i)
        if not self.mod:
            self.lbl.configure(text="Load a mod first.")
            return
        names = self.names()
        if not names:
            self.lbl.configure(text="This game has no religions (plain Rome has none - Medieval II and Barbarian "
                                    "Invasion have them).")
            return
        regions = sorted(getattr(self.app, "regions", {}) or {}, key=str.lower)
        largest = {}
        for r in regions:
            sh = self.shares_of(r)
            if sh:
                top = max(sh, key=lambda k: sh[k])
                largest[top] = largest.get(top, 0) + 1
        pending = {r["name"] for r in self.app.new_religions}
        for n in names:
            self.lb.insert("end", "%-12s %s" % (n, "(new - written with Apply)" if n in pending else
                                               "largest in %d region(s)" % largest.get(n, 0)))
        self.tv["columns"] = names
        self.tv.heading("#0", text="Region")
        self.tv.column("#0", width=200)
        for n in names:
            self.tv.heading(n, text=n)
            self.tv.column(n, width=80, anchor="e")
        changed = set(self.app.region_religions)
        for r in regions:
            sh = self.shares_of(r)
            self.tv.insert("", "end", iid=r, text=r + ("  *" if r in changed else ""),
                           values=[sh.get(n, 0) for n in names])
        self.lbl.configure(text="%d religion(s), %d region(s)%s" % (
            len(names), len(regions), (" - %d changed, not written yet" % len(changed)) if changed else ""))

    def picked(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showerror(APP, "Pick a region in the list first (a click on its line).", parent=self)
            return None
        return sel[0]

    def shares(self):
        region = self.picked()
        if not region:
            return
        self.app.v_paint.set(region)
        self.app.religions_dialog()
        w = [c for c in self.app.winfo_children() if isinstance(c, tk.Toplevel)]
        if w:
            self.wait_window(w[-1])
        self.fill()
        self.tv.selection_set(region)
        self.tv.see(region)

    def new_religion(self):
        self.app.new_religion_dialog()
        w = [c for c in self.app.winfo_children() if isinstance(c, tk.Toplevel)]
        if w:
            self.wait_window(w[-1])
        self.fill()

    def show_on_map(self):
        region = (self.tv.selection() or [None])[0]
        app = self.app
        app.v_work.set("map")                            # Maps: the regions and their shares
        app.work_changed()
        if not app.map_view.v_regions.get():
            app.map_view.v_regions.set(True)
        if region:
            app.v_paint.set(region)
        app.show_map()
        app.update()
        xy = app.mod.city_tiles(app.v_campaign.get()).get(region) if region else None
        if xy:
            app.map_view.centre_on(tuple(xy), zoom=6)
