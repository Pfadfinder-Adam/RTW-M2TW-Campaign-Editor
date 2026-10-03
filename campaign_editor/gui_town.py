"""A town's own window, straight from the Map (a double click on a town, or the right click's 'This town...'), both
games: its owner (hand it to another faction), city or castle (Medieval II), level, population, its buildings (add,
raise, take out - checked the way the game would) and the garrison it holds (shown; changed in Edit faction).
Preview / Write it in with a backup like every write; the writing is masstown.apply - the same one place the 'many
towns at once' window uses, so one town and many follow the same rules."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import masstown as MT
from .gui_util import FactionBox, ShortHint
from .plan import Plan

TITLE = "Town"


class TownWindow(tk.Toplevel):
    def __init__(self, app, region):
        super().__init__(app)
        self.app = app
        self.transient(app)
        self.geometry("880x680")
        self.minsize(640, 520)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.body = ttk.Frame(self, padding=10)
        self.body.pack(fill="both", expand=True)
        self.load(region)

    # ---- reading ----
    def load(self, region):
        """Show region's town as the files hold it now (also when the window is reused for another town)."""
        self.region = region
        self.mod, self.campaign = self.app.mod, self.app.v_campaign.get()
        town = next((t for t in MT.towns(self.mod, self.campaign) if t["region"] == region), None)
        for w in self.body.winfo_children():
            w.destroy()
        if town is None:
            ttk.Label(self.body, text="%s has no town in descr_strat.txt (a rebel village the game makes by itself) - "
                                      "give it to a faction first (right click on the Map > Give this town to)."
                      % region, wraplength=640).pack(anchor="w")
            ttk.Button(self.body, text="Close", command=self.close).pack(anchor="e", pady=10)
            return
        self.town = town
        self.known = MT.known_buildings(self.mod)
        self.build, self.remove = {}, set()                 # {chain: level} to add / raise; chains to take out
        self.title("%s - %s (%s)" % (TITLE, town["name"], region))
        b = self.body
        ShortHint(b, text=(
            "This town as the campaign starts: its owner, its size and its buildings. Changes are checked the way the "
            "game checks them (a level the town is too small for, a castle-only building in a city, one temple per "
            "town...). Preview shows every line, Write it in makes a backup first - Tools > Restore undoes it. The "
            "garrison and the characters in the town are changed in Edit faction (the button below).")).pack(
            fill="x", pady=(0, 6))
        top = ttk.LabelFrame(b, text="%s  (%s)" % (town["name"], region), padding=8)
        top.pack(fill="x")
        shown = self.app.shown_names() if hasattr(self.app, "shown_names") else {}
        facs = [n for n, _ in self.mod.factions()]
        self.v_owner = tk.StringVar(value=town["owner"])
        ttk.Label(top, text="Owner").grid(row=0, column=0, sticky="w")
        FactionBox(top, self.v_owner, facs, shown, state="readonly", width=30).grid(row=0, column=1, sticky="w",
                                                                                     padx=4, pady=2)
        ttk.Label(top, foreground="#666", text="culture %s%s" % (town.get("culture") or "?",
                                                               ", a port" if town.get("port") else "")).grid(
            row=0, column=2, sticky="w", padx=8)
        self.v_kind = tk.StringVar(value=town.get("kind") or "")
        row = 1
        if town.get("kind") is not None:                   # Medieval II: city or castle
            ttk.Label(top, text="City or castle").grid(row=row, column=0, sticky="w")
            ttk.Combobox(top, textvariable=self.v_kind, values=("city", "castle"), state="readonly",
                         width=12).grid(row=row, column=1, sticky="w", padx=4, pady=2)
            row += 1
        self.v_level = tk.StringVar(value=town["level"])
        ttk.Label(top, text="Level").grid(row=row, column=0, sticky="w")
        ttk.Combobox(top, textvariable=self.v_level, values=MT.SETTLEMENT_LEVELS, state="readonly",
                     width=14).grid(row=row, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(top, foreground="#666", wraplength=420, justify="left",
                  text="the governor's building and the population follow the level").grid(row=row, column=2,
                                                                                            sticky="w", padx=8)
        row += 1
        self.v_pop = tk.StringVar(value=str(town.get("population") or ""))
        ttk.Label(top, text="Population").grid(row=row, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.v_pop, width=10).grid(row=row, column=1, sticky="w", padx=4, pady=2)
        ttk.Label(top, foreground="#666", wraplength=420, justify="left",
                  text="people at the start (vanilla grows a level at 400 / 2000 / 6000 / 12000 / 24000)").grid(
            row=row, column=2, sticky="w", padx=8)

        mid = ttk.LabelFrame(b, text="Buildings", padding=8)
        mid.pack(fill="both", expand=True, pady=6)
        self.tv = ttk.Treeview(mid, columns=("chain", "level", "what"), show="headings", height=9,
                               selectmode="browse")
        for c, t, w in (("chain", "building", 200), ("level", "level", 180), ("what", "", 260)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, stretch=c == "what")
        self.tv.pack(fill="both", expand=True)
        add = ttk.Frame(mid)
        add.pack(fill="x", pady=(6, 0))
        chains = sorted(c for c in self.known if not MT.is_core(c))
        self.v_chain, self.v_blevel = tk.StringVar(), tk.StringVar()
        cb = ttk.Combobox(add, textvariable=self.v_chain, values=chains, width=28)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self._levels())
        self.cb_blevel = ttk.Combobox(add, textvariable=self.v_blevel, state="readonly", width=24)
        self.cb_blevel.pack(side="left", padx=4)
        ttk.Button(add, text="Add / raise", command=self.add_building).pack(side="left")
        ttk.Button(add, text="Take out", command=self.take_out).pack(side="left", padx=4)
        self.lbl_why = ttk.Label(mid, foreground="#a33", text="", wraplength=680)
        self.lbl_why.pack(anchor="w")

        gar = ttk.LabelFrame(b, text="Garrison", padding=8)
        gar.pack(fill="x")
        units = town.get("unit_names") or []
        ttk.Label(gar, wraplength=680, justify="left", text=(
            "%s holds the town with %d unit(s): %s" % (town.get("army") or "An army", len(units), ", ".join(units))
            if units else "No army in the town.")).pack(anchor="w")
        bar = ttk.Frame(b)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Garrison and characters in Edit faction...", command=self.to_edit).pack(side="left")
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Write it in", command=self.write).pack(side="right", padx=4)
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right")
        self.fill()

    def fill(self):
        self.tv.delete(*self.tv.get_children())
        have = dict(self.town["buildings"])
        for chain, level in self.town["buildings"]:
            what = "goes" if chain in self.remove else \
                ("-> %s" % self.build[chain]) if chain in self.build else \
                ("follows the level" if MT.is_core(chain) else "")
            self.tv.insert("", "end", iid=chain, values=(chain, level, what))
        for chain, level in self.build.items():
            if chain not in have:
                self.tv.insert("", "end", iid=chain, values=(chain, level, "new"))

    def _levels(self):
        b = self.known.get(self.v_chain.get())
        names = [l.name for l in b.levels] if b else []
        self.cb_blevel["values"] = names
        self.v_blevel.set(names[0] if names else "")

    def _as_now(self):
        """The town as it will be with the kind / level picked (a building is checked against the new size)."""
        t = dict(self.town)
        if self.v_kind.get() and t.get("kind") is not None:
            t["kind"] = self.v_kind.get()
        t["level"] = self.v_level.get() or t["level"]
        t["owner"] = self.v_owner.get() or t["owner"]
        t["buildings"] = [(c, self.build.get(c, l)) for c, l in t["buildings"] if c not in self.remove] + \
            [(c, l) for c, l in self.build.items() if c not in dict(t["buildings"])]
        return t

    def add_building(self):
        chain, level = self.v_chain.get().strip(), self.v_blevel.get()
        if not chain or not level:
            self.lbl_why.configure(text="Pick a building and its level.")
            return
        town = self._as_now()
        town["buildings"] = [(c, l) for c, l in town["buildings"] if not (c == chain and chain in self.build)]
        what, why = MT.building_fit(self.known, town, chain, level, mode="set")
        if what == "skip":
            self.lbl_why.configure(text="%s %s: %s" % (chain, level, why))
            return
        self.remove.discard(chain)
        self.build[chain] = level
        self.lbl_why.configure(text="")
        self.fill()

    def take_out(self):
        sel = self.tv.selection()
        if not sel:
            self.lbl_why.configure(text="Pick a building in the list.")
            return
        chain = sel[0]
        if MT.is_core(chain):
            self.lbl_why.configure(text="The governor's building follows the town's level - change the level instead.")
            return
        if chain in self.build and chain not in dict(self.town["buildings"]):
            self.build.pop(chain)
        else:
            self.build.pop(chain, None)
            self.remove.add(chain)
        self.lbl_why.configure(text="")
        self.fill()

    # ---- writing ----
    def changes(self):
        r, t = self.region, self.town
        opts = {}
        kind = self.v_kind.get() if t.get("kind") is not None else None
        level = self.v_level.get()
        if (kind and kind != t.get("kind")) or level != t["level"]:
            what, why = MT.town_fit(self.known, t, kind, level)
            if what == "skip":
                raise ValueError("%s: %s" % (t["name"], why))
            opts["towns"] = {r: {"kind": kind if kind != t.get("kind") else None,
                                 "level": level if level != t["level"] else None}}
        pop = self.v_pop.get().strip()
        if pop and pop != str(t.get("population") or ""):
            if not pop.isdigit() or int(pop) < 1:
                raise ValueError("The population is a whole number above 0.")
            opts["population"] = {r: int(pop)}
        if self.v_owner.get() and self.v_owner.get() != t["owner"]:
            opts["owners"] = {r: self.v_owner.get()}
        return opts

    def _plan(self):
        opts = self.changes()
        plan = Plan(self.mod, "town", self.region, {})
        builds = list(self.build.items())
        base = {k: v for k, v in opts.items() if k not in ("build", "owners")}
        if base or builds or self.remove:
            first = dict(base)
            if builds:
                first["build"] = {self.region: builds[0]}
            if self.remove:
                first["remove"] = {self.region: sorted(self.remove)[0]}
            MT.apply(plan, self.campaign, first)
            for chain, lv in builds[1:]:                 # apply takes one building per town at a time
                MT.apply(plan, self.campaign, {"build": {self.region: (chain, lv)}})
            for chain in sorted(self.remove)[1:]:
                MT.apply(plan, self.campaign, {"remove": {self.region: chain}})
        if opts.get("owners"):
            MT.apply(plan, self.campaign, {"owners": opts["owners"]})
        return plan

    def preview(self):
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        if not plan.changed_files():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        self.app.show_text("%s - preview (nothing written)" % self.town["name"], plan.report())

    def write(self):
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        if not plan.changed_files():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        if self.app.pending_parts():
            messagebox.showerror(TITLE, "Other changes of the window wait for Apply - Apply (or undo) them first: the "
                                        "mod is read again after this write.", parent=self)
            return
        if not messagebox.askyesno(TITLE, "%s\n\nWrite it? A backup is made first (Tools > Restore undoes it)."
                                   % plan.report()[:1500], parent=self):
            return
        bdir = plan.apply()
        from . import log
        log.write("Town %s changed (backup %s)\n%s" % (self.region, bdir, plan.report()))
        self.app.load()
        self.app.status.set("%s written (backup %s)." % (self.town["name"], bdir))
        self.load(self.region)

    def to_edit(self):
        region = self.region
        self.close()
        self.app.open_town(region)

    def close(self):
        if getattr(self.app, "_town_window", None) is self:
            self.app._town_window = None
        self.destroy()


def open_town_window(app, region):
    """One town window: a second town opens in the same window (the one already open comes to the front)."""
    if not app.mod:
        return
    w = getattr(app, "_town_window", None)
    if w is not None and w.winfo_exists():
        w.load(region)
        w.deiconify()
        w.lift()
        return w
    app._town_window = TownWindow(app, region)
    return app._town_window
