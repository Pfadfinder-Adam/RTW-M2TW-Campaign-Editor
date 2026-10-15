"""Bring units or buildings from another mod - step by step (the Unit and Buildingss' "Bring from another
mod..." button).

The other mod is read straight from its folder (no pack file to make first): pick the mod, tick what to bring,
check the names it gets here, who may have it, where it is recruited (units) or what it recruits (buildings), then
Preview and write - one backup, Restore undoes it, like every other change. The work itself is packs.py
(collect / import_pack for units, collect_buildings / import_buildings for building chains); a .zip pack
(Export pack / Import pack) is still the way to share units with other people."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .gui_util import ask
from . import packs
from .editors import building_blocks
from .gui_util import one_window, ScrollFrame, StepWindow
from .moddata import ModData

NOWHERE = "(not recruited there)"
BRING = "bring its building too (this mod has none)"
LEAVE_OUT = "(leave the line out)"


@one_window
class BringWindow(StepWindow):
    def __init__(self, editor):
        super().__init__(editor)
        self.ed, self.app, self.kind, self.mod = editor, editor.app, editor.kind, editor.mod
        self.what = "units" if self.kind == "unit" else "buildings"
        self.title("Bring %s from another mod - step by step" % self.what)
        self.transient(editor)
        self.full_size = (1000, 660, 720, 520)
        self.fit_steps = (0,)                 # step 1 holds a short list: no big empty window (a tester)
        self.src = None                       # the other mod (ModData)
        self.picked = []                      # unit types / chain names of the other mod
        self.man = self.files = None          # what is brought (the same contents as a pack)
        self.names = {}                       # units: {old type: (type, dictionary)}
        self.chain_names, self.level_names = {}, {}
        self.owners = []                      # factions / cultures of this mod
        self.recruit_map = {}                 # units: {(chain, level): (chain, level) or None}
        self.unit_map = {}                    # buildings: {unit: unit of this mod or None}
        self.bring_chains = {}                # units: {unit: [chain of the other mod brought along with it]}
        facs = [n for n, _ in self.mod.factions()]
        self.factions = facs
        self.cultures = sorted({c for _, c in self.mod.factions() if c and c not in facs})
        self.finish_text = "Write it into this mod"
        steps = [("From which mod", self.s_mod), ("Which %s" % self.what, self.s_pick),
                 ("Names here", self.s_names),
                 ("Who has them" if self.kind == "unit" else "Who may build them", self.s_owners),
                 ("Where they are recruited" if self.kind == "unit" else "The units they recruit", self.s_links),
                 ("Check and write", self.s_check)]
        self.make_steps(steps)
        self.show()

    # ---- step 1: the other mod ----
    def s_mod(self):
        self._note("Pick the mod to bring %s from - they go into the mod loaded now (%s). It is only read - nothing "
                   "in it changes. It must be a mod of the same game (Rome to Rome - with REX, HLR, BI... -, "
                   "Medieval II to Medieval II); the list shows only those." % (self.what, self.mod.data))
        mods = packs.same_game_mods(getattr(self.app, "_mods", []), self.mod)
        v = tk.StringVar(value=self.src.data if self.src else "")
        if mods:
            ttk.Label(self.body, text="Mods in your game folder:").pack(anchor="w")
            lb = tk.Listbox(self.body, height=min(10, len(mods)), exportselection=False)
            for label, d in mods:
                lb.insert("end", "%s    %s" % (label, d))
            lb.pack(fill="both", expand=True, pady=(2, 8))     # grows with the window (R-20261014-E0784E)
            lb.bind("<<ListboxSelect>>", lambda e: lb.curselection() and v.set(mods[lb.curselection()[0]][1]))
        row = ttk.Frame(self.body)
        row.pack(fill="x")
        ttk.Label(row, text="Its data folder").pack(side="left")
        ttk.Entry(row, textvariable=v, width=70).pack(side="left", padx=4, fill="x", expand=True)
        ttk.Button(row, text="Browse...", command=lambda: v.set(
            filedialog.askdirectory(parent=self, title="The other mod's data folder") or v.get())).pack(side="left")

        def collect():
            self._path = v.get().strip()
        self._collect = collect

    def leaving(self, step):
        if step == 0 and self.b_next_pressed():
            return self._load_source()
        if step == 1 and self.b_next_pressed():
            return self._gather()
        return None

    def go(self, d):
        self._dir = d
        return super().go(d)

    def b_next_pressed(self):
        return getattr(self, "_dir", 1) > 0

    def _load_source(self):
        path = getattr(self, "_path", "")
        if not path:
            messagebox.showerror(self.title(), "pick the other mod (or Browse to its data folder)", parent=self)
            return False
        try:
            src = ModData(path)
            if not src.file("edu" if self.kind == "unit" else "edb"):
                raise ValueError("no %s in %s" % (
                    "export_descr_unit.txt" if self.kind == "unit" else "export_descr_buildings.txt", src.data))
        except Exception as e:
            messagebox.showerror(self.title(), str(e), parent=self)
            return False
        if os.path.normcase(os.path.abspath(src.data)) == os.path.normcase(os.path.abspath(self.mod.data)):
            messagebox.showerror(self.title(), "that is this mod - pick another one", parent=self)
            return False
        if packs.game_kind(src) != packs.game_kind(self.mod):
            messagebox.showerror(self.title(), "%s is a %s mod and this one is %s - %s go between mods of one game "
                                 "(the files and models differ)." % (
                                     src.data, _game(src), _game(self.mod), self.what), parent=self)
            return False
        if self.src is None or self.src.data != src.data:
            self.src, self.picked, self.man = src, [], None
        return None

    # ---- step 2: what to bring ----
    def _source_names(self):
        if self.kind == "unit":
            return list(packs.type_blocks(self.src.load(self.src.file("edu"))))
        return [b[0] for b in building_blocks(self.src.load(self.src.file("edb")))]

    def s_pick(self):
        self._note("Tick the %s to bring (click; Ctrl / Shift for more) - the one under the mouse (or clicked last) "
                   "shows on the right as the game shows it; '(renamed here)' = this mod has one of that name, it gets a new one. %s" % (
            self.what, "Each comes with what it needs: its battle models, mount, projectiles, textures, cards, "
                       "name and description." if self.kind == "unit" else
            "Each chain comes with all its levels, their names, descriptions and pictures."))
        names = self._source_names()
        if self.kind == "unit":
            here = {n.lower() for n in packs.type_blocks(self.mod.load(self.mod.file("edu")))}
        else:
            here = {b[0].lower() for b in building_blocks(self.mod.load(self.mod.file("edb")))}
        bar = ttk.Frame(self.body)
        bar.pack(fill="x")
        # Sort and Faction first, where the eye starts (a tester, R-20261014-97E905: 'the sorter stands where it is
        # not seen at once; by owner still mixed - let me pick the faction')
        orders = packs.UNIT_ORDERS if self.kind == "unit" else packs.UNIT_ORDERS[:2]
        v_order = tk.StringVar(value=getattr(self, "_order", orders[0]))
        ttk.Label(bar, text="Sort").pack(side="left")
        ttk.Combobox(bar, textvariable=v_order, values=orders, state="readonly", width=14).pack(side="left", padx=4)
        EVERY = "every faction"
        v_owner = tk.StringVar(value=getattr(self, "_owner", EVERY))
        owners = {}
        if self.kind == "unit":
            src_edu = self.src.load(self.src.file("edu"))
            owners = packs.unit_owners(src_edu)
            ttk.Label(bar, text="Faction").pack(side="left", padx=(12, 0))
            from .gui_util import tip as _tip
            _tip(ttk.Combobox(bar, textvariable=v_owner, values=[EVERY] + packs.owner_choices(src_edu),
                              state="readonly", width=18),
                 "Only the units this faction (or culture) may own - its name on their ownership line. In Rome a "
                 "unit's look also follows the culture, so one unit can stand under several factions.").pack(
                side="left", padx=4)
        ttk.Label(bar, text="Find").pack(side="left", padx=(12, 0))
        v_find = tk.StringVar()
        ttk.Entry(bar, textvariable=v_find, width=24).pack(side="left", padx=4)
        v_new = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="only those this mod has not", variable=v_new).pack(side="left", padx=8)
        info = ttk.Label(bar, foreground="#555")
        info.pack(side="right")
        box = ttk.Frame(self.body)
        box.pack(fill="both", expand=True, pady=4)
        lb = tk.Listbox(box, selectmode="extended", exportselection=False, width=40)
        lb._cards_mod = self.src                       # the hover card: the other mod's unit, as on the right
        sb = ttk.Scrollbar(box, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")
        # the one clicked last, as the game shows it (pictures, names, what it does) - from the other mod
        from .gui_preview import BuildingPreview, UnitPreview
        look = (UnitPreview if self.kind == "unit" else BuildingPreview)(box, self.src)
        look.pack(side="left", fill="both", expand=True)
        lb._cards_faction = lambda: look.faction       # ...in the picked faction's look (report #290)
        chosen = set(self.picked)
        shown = []

        def remember():
            for i, n in enumerate(shown):
                if lb.selection_includes(i):
                    chosen.add(n)
                else:
                    chosen.discard(n)

        def fill(*a):
            remember()
            self._order = v_order.get()
            if self.kind == "unit":
                names[:] = packs.sorted_units(self.src.load(self.src.file("edu")), self._order)
            else:
                names[:] = sorted(names, key=str.lower) if self._order == "by name" else self._source_names()
            self._owner = v_owner.get()
            look.faction = None if self._owner == EVERY else self._owner       # its look in the picture
            on_show[1] = None
            lb.delete(0, "end")
            shown[:] = [n for n in names if (not v_find.get().strip() or v_find.get().strip().lower() in n.lower())
                        and (not v_new.get() or n.lower() not in here)
                        and (self._owner == EVERY or self._owner in owners.get(n, ()))]
            for i, n in enumerate(shown):
                lb.insert("end", n + ("   [%s]" % ", ".join(owners.get(n) or ["no owner"])
                                      if self._order == "by owner" else "")
                          + ("   (renamed here)" if n.lower() in here else ""))
                if n in chosen:
                    lb.selection_set(i)
            info.configure(text="%d picked" % len(chosen))
        on_show = [None, None]                         # [the one clicked, the one on show]

        def put(n):
            if n is not None and n != on_show[1]:
                on_show[1] = n
                look.show(n, self.src)

        def clicked(e=None):
            remember()
            info.configure(text="%d picked" % len(chosen))
            near = lb.nearest(e.y) if e is not None and hasattr(e, "y") else None
            i = near if near is not None and near >= 0 else (lb.curselection() or [None])[-1]
            if i is not None and i < len(shown):
                on_show[0] = shown[i]
                put(shown[i])

        def hover(e):                                  # the one under the mouse shows without ticking it
            i = lb.nearest(e.y)
            if 0 <= i < len(shown):
                bbox = lb.bbox(i)
                if bbox and bbox[1] <= e.y < bbox[1] + bbox[3] + 2:
                    put(shown[i])
        lb.bind("<<ListboxSelect>>", lambda e: clicked())
        lb.bind("<ButtonRelease-1>", clicked, add="+")
        lb.bind("<Motion>", hover)
        lb.bind("<Leave>", lambda e: put(on_show[0]))
        v_find.trace_add("write", fill)
        v_new.trace_add("write", fill)
        v_order.trace_add("write", fill)
        v_owner.trace_add("write", fill)
        shown[:] = []
        fill()

        def collect():
            remember()
            self.picked = [n for n in names if n in chosen]
        self._collect = collect

    def _gather(self):
        if not self.picked:
            messagebox.showerror(self.title(), "tick at least one", parent=self)
            return False
        key = tuple(self.picked)
        if getattr(self, "_gathered", None) == (self.src.data, key):
            return None
        try:
            if self.kind == "unit":
                self.man, self.files = packs.collect(self.src, self.picked)
                self.names = packs.plan_names(self.mod, self.man)
                self.recruit_map = packs.default_recruit_map(self.mod, self.man)
                had = set()
                for u in self.man["units"]:
                    for v in packs._values(u["lines"], "ownership"):
                        had |= set(v)
            else:
                self.man, self.files = packs.collect_buildings(self.src, self.picked)
                self.chain_names, self.level_names = packs.building_names(self.mod, self.man)
                here = {t.lower(): t for t in packs.type_blocks(self.mod.load(self.mod.file("edu")))}
                self.unit_map = {u: here.get(u.lower()) for b in self.man["buildings"] for u in b["units"]}
                from .roster import factions_in
                had = set()
                for b in self.man["buildings"]:
                    for l in b["lines"]:
                        had |= set(factions_in(l) or [])
        except Exception as e:
            messagebox.showerror(self.title(), str(e), parent=self)
            return False
        self.owners = [o for o in self.factions + self.cultures if o in had]
        self._gathered = (self.src.data, key)
        return None

    # ---- step 3: names ----
    def s_names(self):
        if self.kind == "unit":
            self._note("The name each unit gets in this mod. A name this mod already has got a free one (... 2) - "
                       "change it if you like. 'Card / text name' (the 'dictionary' line) names its card pictures "
                       "and its entries in export_units.txt: letters, digits and _ only.")
            rows = [(u["type"], self.names[u["type"]]) for u in self.man["units"]]
            heads = ("in the other mod", "name in this mod", "card / text name")
        else:
            self._note("The name the chain and each of its levels get in this mod. A name this mod already has got "
                       "a free one (..._2): the game needs every chain and level name once. Letters, digits and _ "
                       "only.")
            rows = []
            for b in self.man["buildings"]:
                rows.append((b["chain"], (self.chain_names[b["chain"]], None)))
                rows += [("    level " + lv, (self.level_names[lv], None)) for lv in b["levels"]]
            heads = ("in the other mod", "name in this mod", "")
        cv = tk.Canvas(self.body, highlightthickness=0)
        sb = ttk.Scrollbar(self.body, command=cv.yview)
        frm = ttk.Frame(cv)
        frm.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window(0, 0, window=frm, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        for c, h in enumerate(heads):
            ttk.Label(frm, text=h, foreground="#555").grid(row=0, column=c, sticky="w")
        vs = []
        for i, (old, (a, b)) in enumerate(rows):
            ttk.Label(frm, text=old).grid(row=i + 1, column=0, sticky="w", padx=(0, 8))
            va, vb = tk.StringVar(value=a), tk.StringVar(value=b or "")
            ttk.Entry(frm, textvariable=va, width=32).grid(row=i + 1, column=1, pady=1)
            if self.kind == "unit":
                ttk.Entry(frm, textvariable=vb, width=28).grid(row=i + 1, column=2, padx=4, pady=1)
            vs.append((old, va, vb))

        def collect():
            for old, va, vb in vs:
                if self.kind == "unit":
                    self.names[old] = (va.get().strip(), vb.get().strip() or None)
                elif old.startswith("    level "):
                    self.level_names[old[len("    level "):]] = va.get().strip()
                else:
                    self.chain_names[old] = va.get().strip()
        self._collect = collect

    # ---- step 4: owners ----
    def s_owners(self):
        self._note(("Who gets these units: the factions (or whole cultures) of this mod that may recruit them. "
                    "They get the units' cards too.") if self.kind == "unit" else
                   "Who may build these buildings: the factions (or whole cultures) of this mod. Every level and every "
                   "recruit line in them gets this list.")
        self._note("Picked already: those of the other mod's owners that this mod has too.")
        box = ttk.Frame(self.body)
        box.pack(fill="both", expand=True)
        lists = []
        for title, items in (("Factions", self.factions), ("Cultures (every faction of that culture)", self.cultures)):
            if not items:
                continue
            f = ttk.LabelFrame(box, text=title, padding=4)
            f.pack(side="left", fill="both", expand=True, padx=(0, 6))
            lb = tk.Listbox(f, selectmode="multiple", exportselection=False, height=14)
            sb = ttk.Scrollbar(f, command=lb.yview)
            lb.configure(yscrollcommand=sb.set)
            names = self.app.shown_names() if hasattr(self.app, "shown_names") else {}
            for i, n in enumerate(items):
                lb.insert("end", n + ("  (%s)" % names[n] if names.get(n) and names[n] != n else ""))
                if n in self.owners:
                    lb.selection_set(i)
            lb.pack(side="left", fill="both", expand=True)
            sb.pack(side="left", fill="y")
            lists.append((lb, items))

        def collect():
            self.owners = [items[i] for lb, items in lists for i in lb.curselection()]
        self._collect = collect

    # ---- step 5: recruiting ----
    def s_links(self):
        if self.kind == "unit":
            return self._unit_places()
        else:
            self._note("The units these buildings recruit. Each one goes to a unit of THIS mod: the same one when this "
                       "mod has it; otherwise pick one, or '%s'. To bring a unit this mod lacks, bring it first with "
                       "Units' 'Bring from another mod...'." % LEAVE_OUT)
            here = list(packs.type_blocks(self.mod.load(self.mod.file("edu"))))
            rows = [(u, u, v or LEAVE_OUT) for u, v in self.unit_map.items()]
            choices = [LEAVE_OUT] + here
            units_at = {}
        if not rows:
            self._note("Nothing to set here: %s." % ("the other mod recruits these units nowhere" if self.kind == "unit"
                                                     else "these buildings recruit no units"))
            self._collect = None
            return
        sf = ScrollFrame(self.body)                 # a long list scrolls (wheel and bar) - report #109
        sf.pack(fill="both", expand=True)
        frm = sf.inner
        vs = []
        for i, (label, key, cur) in enumerate(rows):
            extra = (" (%s)" % ", ".join(units_at.get(key, []))) if units_at.get(key) else ""
            ttk.Label(frm, text=label + extra, wraplength=360).grid(row=i, column=0, sticky="w", padx=(0, 8), pady=1)
            v = tk.StringVar(value=cur)
            cb = ttk.Combobox(frm, textvariable=v, values=choices, state="readonly", width=48)
            cb.grid(row=i, column=1, sticky="w", pady=1)
            vs.append((key, v))

        def collect():
            for key, v in vs:
                val = v.get()
                if self.kind == "unit":
                    self.recruit_map[key] = None if val == NOWHERE else tuple(val.split(" / ", 1))
                else:
                    self.unit_map[key] = None if val == LEAVE_OUT else val
        self._collect = collect

    def _unit_places(self):
        """Units: one row each - which building of THIS mod trains it. Only the units come over, never a building;
        'as in the other mod' keeps the places this mod has under the same names."""
        AS_THERE = "the same buildings as in the other mod"
        self._note("Pick the building level of THIS mod that trains each unit - it trains there and on every level "
                   "above it (the game trains only what a town's current level lists): '%s' uses the levels this mod has "
                   "under the same names (shown beside it), '%s' = trained nowhere until you add a recruit line by "
                   "hand. A building this mod has not at all can come along: '%s' (all its levels, names and "
                   "pictures; its recruit lines for units this mod lacks left out, said)." % (AS_THERE, NOWHERE, BRING))
        lacking = packs.missing_chains(self.mod, self.man)
        levels = ["%s / %s" % x for x in packs.recruit_levels(self.mod)]
        have = set(packs.recruit_levels(self.mod))
        places = {}
        for r in self.man.get("recruit", []):
            places.setdefault(r["unit"], []).append((r["chain"], r["level"]))
        units = [u["type"] for u in self.man["units"]] if self.man.get("units") else list(places)
        if not units:
            self._note("Nothing to set here.")
            self._collect = None
            return
        # one building for every unit at once (the user, 2026-10-14: to try brought units in a mod quickly) - it
        # sets each row below, which stays its own to change after
        allrow = ttk.Frame(self.body)
        allrow.pack(fill="x", pady=(0, 4))
        ttk.Label(allrow, text="All the units here:", font=("", 9, "bold")).pack(side="left")
        v_all = tk.StringVar(value="")
        cb_all = ttk.Combobox(allrow, textvariable=v_all, values=[NOWHERE] + levels, state="readonly", width=56)
        cb_all.pack(side="left", padx=8)
        from .gui_util import tip as _tip
        _tip(cb_all, "Every unit below is trained in this building level (also a unit the other mod trains nowhere); "
                     "each row can still be changed after.")
        sf = ScrollFrame(self.body)                 # wheel and bar
        sf.pack(fill="both", expand=True)
        frm = sf.inner
        vs = []
        for i, unit in enumerate(units):
            mine = places.get(unit, [])
            same = [p for p in mine if p in have]
            picked = {self.recruit_map.get((unit,) + p, self.recruit_map.get(p, p if p in have else None))
                      for p in mine}
            if self.bring_chains.get(unit):
                cur = BRING
            elif not mine:
                cur = NOWHERE
            elif picked == {p if p in have else None for p in mine}:
                cur = AS_THERE if same else NOWHERE
            else:
                one = next((x for x in picked if x), None)
                cur = "%s / %s" % one if one else NOWHERE
            ttk.Label(frm, text=unit, font=("", 9, "bold")).grid(row=2 * i, column=0, sticky="w", pady=(6, 0))
            v = tk.StringVar(value=cur)
            ttk.Combobox(frm, textvariable=v, values=([BRING] if lacking.get(unit) else []) +
                         ([AS_THERE] if same else []) + [NOWHERE] + levels,
                         state="readonly", width=56).grid(row=2 * i, column=1, sticky="w", padx=8, pady=(6, 0))
            ttk.Label(frm, foreground="#666", wraplength=700, justify="left", text=(
                "in the other mod: %s; here under the same names: %s%s" % (
                    ", ".join("%s / %s" % p for p in mine) or "nowhere",
                    ", ".join("%s / %s" % p for p in same) or "none",
                    "; this mod has no %s at all" % ", ".join(lacking[unit]) if lacking.get(unit) else ""))).grid(
                row=2 * i + 1, column=0, columnspan=2, sticky="w")
            vs.append((unit, mine, v))

        cb_all.bind("<<ComboboxSelected>>", lambda e: [v.set(v_all.get()) for _, _, v in vs])

        def collect():
            from .editors import recruit_text
            from .roster import recruit_dialect
            dialect = recruit_dialect(self.mod.load(self.mod.file("edb"))) if self.mod.file("edb") else "plain"
            self.man["recruit"] = [r for r in self.man.get("recruit", []) if not r.get("picked")]
            for unit, mine, v in vs:
                val = v.get()
                self.bring_chains[unit] = list(lacking.get(unit, [])) if val == BRING else []
                if not mine and val not in (NOWHERE, BRING, AS_THERE, ""):
                    chain, level = val.split(" / ", 1)       # trained nowhere in the other mod: a line of its own
                    self.man["recruit"].append({"unit": unit, "chain": chain, "level": level, "picked": True,
                                                "line": recruit_text(dialect, unit, "0", factions=self.owners)})
                for p in mine:
                    if val in (AS_THERE, BRING):
                        self.recruit_map[(unit,) + p] = p if p in have else None
                    elif val == NOWHERE:
                        self.recruit_map[(unit,) + p] = None
                    else:
                        self.recruit_map[(unit,) + p] = tuple(val.split(" / ", 1))
        self._collect = collect

    # ---- step 6: check and write ----
    def _plan(self):
        from .plan import Plan
        plan = Plan(self.mod, "pack", "unit_pack" if self.kind == "unit" else "building_pack", {})
        if self.kind == "unit":
            chains = sorted({c for u in self.man["units"] for c in self.bring_chains.get(u["type"], [])})
            packs.bring_with_buildings(plan, self.src, self.man, self.files, self.owners, self.names,
                                       self.recruit_map, chains)
        else:
            packs.import_buildings(plan, self.man, self.files, self.owners, self.chain_names, self.level_names,
                                   self.unit_map)
        return plan

    def s_check(self):
        try:
            plan = self._plan()
        except Exception as e:
            self._note("Something must change before it can be written:")
            ttk.Label(self.body, text=str(e), foreground="#b00020", wraplength=780).pack(anchor="w")
            self.b_next.state(["disabled"])
            return
        self._note("Everything below is written with one click; a backup is made first and Restore (bottom bar) "
                   "gives every file back. Read the WARNINGS at the end: they say what to finish by hand.")
        txt = tk.Text(self.body, wrap="word", height=20)
        sb = ttk.Scrollbar(self.body, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.insert("1.0", plan.report())
        txt.configure(state="disabled")
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

    def finish(self):
        if self.ed.pending() and not ask(
                self.title(), "The %s editor holds changes not written yet; writing now reads the files again, so "
                              "they would be dropped. Go on?" % self.kind, parent=self, yes='Write, drop them', no='Stay', danger=True):
            return
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror(self.title(), str(e), parent=self)
            return
        bdir = plan.apply()
        from . import log
        log.write("Brought %s from %s (backup %s)\n%s" % (self.what, self.src.data, bdir, plan.report()))
        n = len(self.picked)
        self.destroy()
        self.app.load()
        self.app.status.set("%d %s brought from %s (backup %s) - Restore undoes it." % (
            n, self.what if n != 1 else self.what[:-1], os.path.basename(os.path.dirname(self.src.data))
            or self.src.data, bdir))


def _game(mod):
    return "Medieval II" if packs.game_kind(mod) == "medieval2" else "Rome"
