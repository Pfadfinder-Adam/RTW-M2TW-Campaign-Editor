"""A town's own window, straight from the Map (a double click on a town, or the right click's 'This town...'), both
games, any owner (Maps too): its owner (hand it to another faction), city or castle (Medieval II), level,
population, and - switched in the same window - its buildings (the Buildings tab's own editor: the pictures, a click
builds a level) and its garrison (the Units & armies tab's card picker; a named character keeps his bodyguard).
Every change is kept for Apply by itself (gui_util.AutoKeep - no Keep button; the main window's Preview changes /
Apply changes show and write it with the rest of the session, a backup first; its Undo / Redo and Ctrl+Z step this
window's changes); the writing is masstown.apply - the same one place the 'many towns at once' window uses, so one
town and many follow the same rules."""

import re
import tkinter as tk
from tkinter import ttk

from . import masstown as MT
from .gui_util import AutoKeep, FactionBox, hint
from .plan import Plan

TITLE = "Town"


class TownWindow(AutoKeep, tk.Toplevel):
    def __init__(self, app, region):
        super().__init__(app)
        self.app = app
        self.transient(app)
        self.small = None                                  # sized for a town (False) or for the short note (True)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.body = ttk.Frame(self, padding=(10, 6, 10, 6))
        self.body.pack(fill="both", expand=True)
        self.load(region)

    def _size(self, small):
        """A town: 960 x 680 (report #155: the screen's height was 'a bit long'), never past the screen (a 900-pixel
        screen kept the buttons under the taskbar), or the size the modder gave it last (kept in the settings); the
        short note of a region with no town: as big as its words (a tester's screen: two lines in a window the size of
        the screen)."""
        from . import settings as _settings
        if small == self.small:
            return
        self.small = small
        if small:
            self.minsize(1, 1)
            self.geometry("")
        else:
            kept = str(_settings.get("town_window_size", "") or "")
            m = re.match(r"^(\d+)x(\d+)$", kept)
            w, h = (int(m.group(1)), int(m.group(2))) if m else (960, 680)
            self.geometry("%dx%d" % (max(720, min(w, self.winfo_screenwidth() - 40)),
                                     max(480, min(h, self.winfo_screenheight() - 110))))
            self.minsize(720, 480)

    def _keep_size(self):
        """The town window's size as the modder left it - the next one opens so."""
        from . import settings as _settings
        if self.small is False:
            try:
                size = self.geometry().split("+")[0]
            except tk.TclError:
                return
            if re.match(r"^\d+x\d+$", size):
                _settings.put("town_window_size", size)

    def _no_town(self, region):
        """A region descr_strat.txt has no town for: the game makes a rebel village there by itself (no buildings,
        a few rebels), so there is nothing to change yet - unless its town is written: for the rebels (the village
        as it is, the look of the faction descr_regions names as its builder) or for a faction. Kept for Apply like
        the Map's 'Give this town to' (the same one place, gui_mapadd.give_town)."""
        from .gui_mapadd import factions_here, give_town
        self.title("%s - %s" % (TITLE, region))
        if (self.mod.regions(self.campaign).get(region) or {}).get("wasteland"):
            ttk.Label(self.body, text="%s is a wasteland (REX / M2EX): no town, no owner, no rebels - nobody's land. "
                                      "To give it a town again, right click a tile of its land on the Map: 'Give %s "
                                      "its town here...'." % (region, region),
                      wraplength=560, justify="left").pack(anchor="w")
            ttk.Button(self.body, text="Close", command=self.close).pack(anchor="e", pady=(10, 0))
            return
        ttk.Label(self.body, text="%s has no town in descr_strat.txt: the game makes a rebel village there by itself "
                                  "(no buildings, a few rebels). Write its town to change it here:" % region,
                  wraplength=560, justify="left").pack(anchor="w")
        facs = factions_here(self.app)
        row = ttk.Frame(self.body)
        row.pack(anchor="w", pady=(8, 0))
        if not facs:
            ttk.Label(row, text="(descr_strat.txt has no faction to give it to)", foreground="#666").pack(side="left")
        else:
            shown = self.app.shown_names() if hasattr(self.app, "shown_names") else {}
            v_owner = tk.StringVar(value="slave" if "slave" in facs else facs[0])
            ttk.Label(row, text="Owner").pack(side="left")
            FactionBox(row, v_owner, facs, shown, state="readonly", width=30).pack(side="left", padx=4)

            def write():
                owner = v_owner.get()
                if owner not in facs:
                    return
                give_town(self.app, region, owner)
                self.app.status.set("%s: its town goes to %s with the next Apply - Preview first. Then double click "
                                    "it on the Map to change its buildings and garrison." % (region, owner))
                self._forget()
                self.destroy()
            ttk.Button(row, text="Write its town", command=write).pack(side="left", padx=(4, 0))
            hint(row, "Its town is written into descr_strat.txt with the next Apply: a village of 400 people with no "
                      "buildings, as the game makes it. Given to the rebels (slave) it stays theirs; given to a "
                      "faction, that faction starts with it.", width=420).pack(side="left", padx=4)
        ttk.Button(self.body, text="Close", command=self.close).pack(anchor="e", pady=(10, 0))

    # ---- reading ----
    def load(self, region):
        """Show region's town as the files hold it now (also when the window is reused for another town)."""
        self.ak_close()                                    # the town shown before: what waits is kept first
        self._ak_busy = True
        self.region = region
        # the town as the other windows' kept changes leave it (its own kept part not: keeping again replaces it)
        self._read_from = self.app.mod
        self.mod = self.app.kept_view(but="town:%s" % region) if hasattr(self.app, "kept_view") else self.app.mod
        self.campaign = self.app.v_campaign.get()
        town = next(iter(MT.towns(self.mod, self.campaign, only=region)), None)      # one town, not all 749
        for w in self.body.winfo_children():
            w.destroy()
        self.town = town                                   # None: nothing to change - closing asks nothing
        self._size(town is None)
        if town is None:
            self._no_town(region)
            return
        app = self.app
        me = app.field_faction() if getattr(app, "editing", lambda: False)() and not app.map_only() else None
        now = MT.owner_now(town["owner"], region, getattr(app, "map_owners", {}), me,
                           getattr(app, "chosen", None) if me else None,
                           app.v_give.get() if me and hasattr(app, "v_give") else None)
        if now != town["owner"] and now in dict(self.mod.factions()):     # given on the Map / the towns list: shown so
            town = dict(town, owner=now)                                   # (a report: it still said slave)
        self.town = town
        if not town.get("army") and town.get("near"):        # said in the log too: a report shows it
            from . import log
            log.write("Town %s: no army on its tile %s; beside it: %s" % (region, town.get("tile"), ", ".join(
                "%s (%s) %s" % x for x in town["near"])))
        self.known = MT.known_buildings(self.mod)
        self.title("%s - %s (%s)" % (TITLE, town["name"], region))
        b = self.body
        # the town's name once (the title of the box); every explanation behind a '?' - the room is for the buildings
        head = ttk.Frame(b)
        head.pack(fill="x", pady=(0, 2))
        ttk.Label(head, text="%s  (%s)" % (town["name"], region), font=("", 11, "bold")).pack(side="left")
        hint(head, "This town as the campaign starts: its owner, its size and its buildings. Changes are checked the "
                   "way the game checks them (a level the town is too small for, a castle-only building in a city, "
                   "one temple per town...). Buildings and Garrison switch this window between the two (as the "
                   "Buildings and Units & armies tabs look). Every change is kept for the write by itself: Preview "
                   "changes in the main window shows every line, Apply changes writes them with the rest (a backup "
                   "first; Undo this write puts them back). Undo / Redo (or Ctrl+Z / Ctrl+Y) step this window's "
                   "changes; closing it keeps them.", width=520).pack(side="left")
        self.lbl_view = ttk.Label(head, foreground="#666", text="", wraplength=430, justify="left")
        self.lbl_view.pack(side="left", padx=10)
        top = ttk.Frame(b, padding=(0, 2))
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
        follow = ttk.Frame(top)
        follow.grid(row=row, column=2, sticky="w", padx=8)
        ttk.Checkbutton(follow, variable=self.v_follow, text="the level follows the population",
                        command=lambda: _settings.put("level_follows_population", bool(self.v_follow.get()))).pack(
            side="left")
        hint(follow, "Each level holds a range of people at the start (a village 400 - 1500, a town up to 3500, a "
                     "large town 9000, a city 18000...): outside it the game stops reading the campaign file. "
                     "Ticked, the town grows with its governor's building when the people do not fit; unticked, "
                     "the population is cut to the level's range.", width=480).pack(side="left")

        # the town's buildings and its garrison in ONE window, switched by the two buttons - each looks exactly as
        # its tab of the main window (Buildings; Units & armies), and nothing jumps to the main window
        # two tabs as clear as the main window's (the flat buttons were hardly seen in the dark look)
        self.v_view = tk.StringVar(value="buildings")
        self.views = ttk.Notebook(b)
        self.views.pack(fill="both", expand=True, pady=(4, 2))
        from .gui_buildings import BuildingsEditor
        from .gui_garrison import GarrisonEditor
        self.bed = BuildingsEditor(self.views, self.app.pictures)
        self.ged = GarrisonEditor(self.views, pictures=self.app.pictures)
        self.bed.title.pack_forget()                        # the town's name and level are shown above already
        self.views.add(self.bed, text="  Buildings  ")
        self.views.add(self.ged, text="  Garrison  ")
        self.views.bind("<<NotebookTabChanged>>", lambda e: self._tab_changed())
        self.picked = None                                  # the buildings as picked here, None = as the file has
        self.garrison = None                                # the garrison as picked here, None = as it stands
        self._restore(region)
        self.load_buildings()
        self.ged_loaded = False                             # the garrison's cards are made when it is first shown:
        self.v_owner.trace_add("write", lambda *a: self._owner_changed())
        self.v_level.trace_add("write", lambda *a: self.v_level.get() and self.bed.buildings is not None and
                               self.bed.set_level(self.v_level.get()))
        for var in (self.v_owner, self.v_kind, self.v_level, self.v_pop, self.v_follow):
            var.trace_add("write", self.ak_changed)
        bar = ttk.Frame(b)                                  # only as tall as its buttons
        bar.pack(side="bottom", fill="x", before=self.views)
        self.lbl_why = ttk.Label(bar, foreground="#a33", text="", wraplength=600, justify="left")
        self.lbl_why.pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        self._ak_line = self.lbl_why
        self.show_view()
        self.ak_start()

    def _restore(self, region):
        """This town's changes kept for Apply, shown again when it is opened again (a report: a garrison kept here
        showed the old one on the next opening - the town is read without its own kept part, which Keep replaces)."""
        kept = getattr(self.app, "_town_kept", {})
        st = kept.get(region)
        if st is None:
            return
        if not (hasattr(self.app, "session_kept") and self.app.session_kept("town:%s" % region)):
            kept.pop(region, None)                          # written or dropped since: the files say it now
            return
        for var, key in ((self.v_owner, "owner"), (self.v_kind, "kind"), (self.v_level, "level"),
                         (self.v_pop, "population")):
            if st.get(key) is not None:
                var.set(st[key])
        self.picked = st.get("picked")
        self.garrison = st.get("garrison")

    def _kept_state(self):
        return {"owner": self.v_owner.get(), "kind": self.v_kind.get(), "level": self.v_level.get(),
                "population": self.v_pop.get(), "picked": self.picked,
                "garrison": None if self.garrison is None else list(self.garrison)}

    # ---- kept by itself (gui_util.AutoKeep) ----
    def _ak_key(self):
        return "town:%s" % self.region if self.town is not None else None

    def _ak_label(self):
        return "Town %s: buildings / garrison / owner" % self.town["name"]

    def _ak_plan(self):
        return self._plan()

    def _ak_state(self):
        return dict(self._kept_state(), follow=bool(self.v_follow.get())) if self.town is not None else None

    def _ak_set(self, st):
        for var, key in ((self.v_owner, "owner"), (self.v_kind, "kind"), (self.v_level, "level"),
                         (self.v_pop, "population")):
            var.set(st[key])
        self.v_follow.set(st["follow"])
        self.picked = st["picked"]
        self.garrison = None if st["garrison"] is None else list(st["garrison"])
        self.load_buildings()
        if self.ged_loaded:
            self.load_garrison()

    def ak_reload(self):
        self._ak_job = None
        self.load(self.region)

    def _ak_saw(self, st):
        """Shown again when this town opens again (a report: a garrison kept here showed the old one)."""
        kept = self.app.__dict__.setdefault("_town_kept", {})
        if st is None:
            kept.pop(self.region, None)
        else:
            kept[self.region] = st

    @property
    def _ak_after(self):
        """Once written: said in the log, the window shows the files as they are now (its town taken at keep time)."""
        region = self.region
        return lambda bdir: self._written(bdir, region)

    def _written(self, bdir, region):
        from . import log
        log.write("Town %s changed (backup %s)" % (region, bdir))
        try:
            if self.winfo_exists() and self.region == region:
                self.load(region)
        except tk.TclError:
            pass

    # ---- the two views ----
    def _tab_changed(self):
        self.v_view.set("garrison" if self.views.select() == str(self.ged) else "buildings")
        self.show_view(select=False)

    def show_view(self, select=True):
        if select:
            self.views.select(self.ged if self.v_view.get() == "garrison" else self.bed)
        if self.v_view.get() == "garrison" and not self.ged_loaded:
            self.load_garrison()                            # HLR's owners have 500+ cards (report #155: slow to open)
        if self.v_view.get() == "garrison":
            t = self.town
            self.lbl_view.configure(text=("the army in the town: %s%s" % (t.get("army") or "a captain",
                                    " (his bodyguard stays)" if t.get("army_named") else "")) if t.get("army")
                                    else ("the town's own garrison, no captain (garrisoned_army in its block): %d "
                                          "unit(s)" % len(t.get("unit_names") or [])) if t.get("inside")
                                    else self._nobody())
        else:
            self.lbl_view.configure(text="click a level to build it; the governor's building follows the level")

    def _nobody(self):
        """No army of the owner on the town's tile: the town starts empty - and who stands beside it (a garrison one
        tile off is outside the walls; a tester's mod showed none in the town window)."""
        t = self.town
        near = t.get("near") or []
        if not near:
            return "nobody holds the town: units picked here get a captain"
        tile = t.get("tile") or ("?", "?")
        return ("nobody stands on the town's tile (%s, %s) - the game starts it empty. Beside it, outside the walls: "
                "%s. To make one the garrison, drag him onto the town on the Map; or pick units here (a captain gets "
                "them)." % (tile[0], tile[1], "; ".join("%s (%s) at %d, %d" % (n, f, xy[0], xy[1])
                                                         for n, f, xy in near[:3])))

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
            self.ak_changed()
        self.bed.load(self.region, self.v_level.get() or t["level"], edb, t["buildings"], self.picked,
                      self.mod.culture(owner), owner, owner, bpics, changed,
                      kind=(self.v_kind.get() or t.get("kind") or "city") if castles else None,
                      on_kind=lambda k: self.v_kind.set(k))

    def load_garrison(self):
        from .units import faction_units
        self.ged_loaded = True
        t, owner = self.town, self._owner()
        named = t.get("army_named")
        now = list(t.get("unit_names") or [])
        now = now[1:] if named else now                    # without the bodyguard
        units = faction_units(self.mod, owner, mercs=True)
        units = self.app._with_types(units, now) if hasattr(self.app, "_with_types") else units

        def changed(types):
            if getattr(self.ged, "cleared", False):            # 'As it was': back to the town as it stands
                self.garrison = None
                self.after_idle(self.load_garrison)
            else:
                self.garrison = list(types)
            self.lbl_why.configure(text="")
            self.ak_changed()
        def suggest(lo, hi, cap):                       # the units the town's owner trains, by the numbers by Suggest
            import random
            pool = MT.town_pool(self.mod, t, MT.garrison_pool(self.mod, owner))
            return MT.random_garrison(pool, lo, hi, cap, random.Random())
        self.ged.load(self.mod, owner, "%s (%s)" % (t["name"], self.region), units,
                      self.garrison if self.garrison is not None else now, changed, auto=suggest, as_was=True,
                      held=(t.get("army_role") or True) if named else False, unchanged=self.garrison is None)

    def _owner_changed(self):
        """Another owner: the buildings it may build and the units it may have are its own."""
        self.load_buildings()
        if self.ged_loaded:
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
            opts["owners"] = {r: self.v_owner.get()}      # (an owner the Map gave already is the Map's to write)
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

    def _fresh(self):
        """The main window read the mod again (an Apply there): this window's town is read again too, so its changes
        are never built on files as they were before."""
        if self.app.mod is getattr(self, "_read_from", self.mod):
            return False
        self.load(self.region)
        return True

    def _forget(self):
        if getattr(self.app, "_town_window", None) is self:
            self.app._town_window = None

    def close(self):
        """Closing keeps what it holds (it waits for Apply changes) - nothing is asked."""
        self._keep_size()
        self.ak_close()
        self._forget()
        try:
            self.destroy()
        except tk.TclError:
            pass


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
