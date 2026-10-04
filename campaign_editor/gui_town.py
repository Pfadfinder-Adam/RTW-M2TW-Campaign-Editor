"""A town's own window, straight from the Map (a double click on a town, or the right click's 'This town...'), both
games, any owner (the Map editor too): its owner (hand it to another faction), city or castle (Medieval II), level,
population, and - switched in the same window - its buildings (the Buildings tab's own editor: the pictures, a click
builds a level) and its garrison (the Units & armies tab's card picker; a named character keeps his bodyguard).
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
        self.geometry("980x860")
        self.minsize(720, 600)
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
        self.title("%s - %s (%s)" % (TITLE, town["name"], region))
        b = self.body
        ShortHint(b, text=(
            "This town as the campaign starts: its owner, its size and its buildings. Changes are checked the way the "
            "game checks them (a level the town is too small for, a castle-only building in a city, one temple per "
            "town...). Buildings and Garrison switch this window between the two (as the Buildings and Units & armies "
            "tabs look). Preview shows every line, Write it in makes a backup first - Tools > Restore undoes it.")).pack(
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
        from . import settings as _settings
        self.v_follow = tk.BooleanVar(value=_settings.get("level_follows_population", True) is not False)
        ttk.Checkbutton(top, variable=self.v_follow, text="the level follows the population",
                        command=lambda: _settings.put("level_follows_population", bool(self.v_follow.get()))).grid(
            row=row, column=2, sticky="w", padx=8)
        row += 1
        ttk.Label(top, foreground="#666", wraplength=520, justify="left",
                  text="Each level holds a range of people at the start (a village 400 - 1500, a town up to 3500, a "
                       "large town 9000, a city 18000...): outside it the game stops reading the campaign file. "
                       "Ticked, the town grows with its governor's building when the people do not fit; unticked, "
                       "the population is cut to the level's range.").grid(
            row=row, column=1, columnspan=2, sticky="w", padx=4)

        # the town's buildings and its garrison in ONE window, switched by the two buttons - each looks exactly as
        # its tab of the main window (Buildings; Units & armies), and nothing jumps to the main window
        sw = ttk.Frame(b)
        sw.pack(fill="x", pady=(6, 0))
        self.v_view = tk.StringVar(value="buildings")
        for key, text in (("buildings", "Buildings"), ("garrison", "Garrison")):
            ttk.Radiobutton(sw, text=text, value=key, variable=self.v_view, style="Toolbutton",
                            command=self.show_view).pack(side="left", padx=(0, 4))
        self.lbl_view = ttk.Label(sw, foreground="#666", text="")
        self.lbl_view.pack(side="left", padx=8)
        self.views = ttk.Frame(b)
        self.views.pack(fill="both", expand=True, pady=6)
        from .gui_buildings import BuildingsEditor
        from .gui_garrison import GarrisonEditor
        self.bed = BuildingsEditor(self.views, self.app.pictures)
        self.ged = GarrisonEditor(self.views, pictures=self.app.pictures)
        self.picked = None                                  # the buildings as picked here, None = as the file has
        self.garrison = None                                # the garrison as picked here, None = as it stands
        self.load_buildings()
        self.load_garrison()
        self.v_owner.trace_add("write", lambda *a: self._owner_changed())
        self.v_level.trace_add("write", lambda *a: self.v_level.get() and self.bed.buildings is not None and
                               self.bed.set_level(self.v_level.get()))
        bar = ttk.Frame(b)
        bar.pack(side="bottom", fill="x", pady=(4, 0), before=self.views)
        self.lbl_why = ttk.Label(b, foreground="#a33", text="", wraplength=760, justify="left")
        self.lbl_why.pack(side="bottom", anchor="w", before=self.views)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Write it in", command=self.write).pack(side="right", padx=4)
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right")
        self.show_view()

    # ---- the two views ----
    def show_view(self):
        for w in (self.bed, self.ged):
            w.pack_forget()
        if self.v_view.get() == "garrison":
            self.ged.pack(fill="both", expand=True)
            t = self.town
            self.lbl_view.configure(text=("the army in the town: %s%s" % (t.get("army") or "a captain",
                                    " (his bodyguard stays)" if t.get("army_named") else "")) if t.get("army")
                                    else "nobody holds the town: units picked here get a captain")
        else:
            self.bed.pack(fill="both", expand=True)
            self.lbl_view.configure(text="click a level to build it; the governor's building follows the level")

    def _owner(self):
        return self.v_owner.get() or self.town["owner"]

    def load_buildings(self):
        from .buildings import BuildingPictures, castles_allowed, read_buildings
        if getattr(self.app, "_edb_for", None) == self.mod.data and getattr(self.app, "_edb", None) is not None:
            edb, bpics = self.app._edb, self.app._bpics
        else:
            edb = read_buildings(self.mod.load(self.mod.file("edb"))) if self.mod.file("edb") else []
            bpics = BuildingPictures(self.mod)
        self.edb = edb
        t, owner = self.town, self._owner()
        castles = castles_allowed(self.mod, self.known)

        def changed(picked):
            self.picked = None if picked is None else [tuple(x) for x in picked]
            core = next(((c, lv) for c, lv in (picked or []) if MT.is_core(c)), None)
            have = next(((c, lv) for c, lv in t["buildings"] if MT.is_core(c)), None)
            if core and core != have and core[1] not in (None, "-"):     # a governor's building picked: its level
                from .buildings import core_settlement
                b = self.known.get(core[0])
                lvl = core_settlement(b, core[1]) if b else None
                if lvl:
                    self.v_level.set(lvl)
            self.lbl_why.configure(text="")
        self.bed.load(self.region, self.v_level.get() or t["level"], edb, t["buildings"], self.picked,
                      self.mod.culture(owner), owner, owner, bpics, changed,
                      kind=(self.v_kind.get() or t.get("kind") or "city") if castles else None,
                      on_kind=lambda k: self.v_kind.set(k))

    def load_garrison(self):
        from .units import faction_units
        t, owner = self.town, self._owner()
        named = t.get("army_named")
        now = list(t.get("unit_names") or [])
        now = now[1:] if named else now                    # without the bodyguard
        units = faction_units(self.mod, owner, mercs=True)
        units = self.app._with_types(units, now) if hasattr(self.app, "_with_types") else units

        def changed(types):
            if getattr(self.ged, "cleared", False):            # 'Automatic': back to the town as it stands
                self.garrison = None
                self.after_idle(self.load_garrison)
            else:
                self.garrison = list(types)
            self.lbl_why.configure(text="")
        def suggest():                                  # the units the town's owner trains, under a sensible upkeep
            import random
            pool = MT.town_pool(self.mod, t, MT.garrison_pool(self.mod, owner))
            return MT.random_garrison(pool, 3, 6, 2000, random.Random())
        self.ged.load(self.mod, owner, "%s (%s)" % (t["name"], self.region), units,
                      self.garrison if self.garrison is not None else now, changed, auto=suggest,
                      held=(t.get("army_role") or True) if named else False, unchanged=self.garrison is None)

    def _owner_changed(self):
        """Another owner: the buildings it may build and the units it may have are its own."""
        self.load_buildings()
        self.load_garrison()

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
            opts["level_follows"] = bool(self.v_follow.get())
        if self.v_owner.get() and self.v_owner.get() != t["owner"]:
            opts["owners"] = {r: self.v_owner.get()}
        return opts

    def building_changes(self):
        """([(chain, level)] to build or raise, [chain] to take out) - the editor's pick against the town's own
        buildings; the governor's building is left to the level (it follows it)."""
        if self.picked is None:
            return [], []
        own = dict(self.town["buildings"])
        want = {c: lv for c, lv in self.picked if lv not in (None, "-", "")}
        builds = [(c, lv) for c, lv in want.items() if own.get(c) != lv and not MT.is_core(c)]
        removes = sorted(c for c in own if c not in want and not MT.is_core(c))
        return builds, removes

    def _plan(self):
        opts = self.changes()
        plan = Plan(self.mod, "town", self.region, {})
        builds, removes = self.building_changes()
        for chain, lv in builds:                      # checked the way the game checks it (size, kind, one temple)
            town = dict(self.town, level=self.v_level.get() or self.town["level"])
            if self.v_kind.get() and town.get("kind") is not None:
                town["kind"] = self.v_kind.get()
            town["buildings"] = [(c, l) for c, l in town["buildings"] if c != chain]
            what, why = MT.building_fit(self.known, town, chain, lv, mode="set")
            if what == "skip":
                raise ValueError("%s %s: %s" % (chain, lv, why))
        self.remove = set(removes)
        if self.garrison is not None:
            opts["garrisons"] = {self.region: list(self.garrison)}
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
