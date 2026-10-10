"""The window 'Buildings and garrisons for many towns': every town of the campaign on the left (filter by owner,
level, city / castle, name), the towns chosen on the right with what will happen in each; a building level added
to them (or a chain taken out), or garrisons drawn at random under an upkeep cap. Preview, then one write with a
backup (Restore undoes it)."""

import random
import tkinter as tk
from tkinter import messagebox, ttk

from . import masstown as M
from . import theme
from .gui_util import ShortHint, hint, tip

ANY = "(any)"
TITLE = "Buildings and garrisons for many towns"


def _level(t):
    return t["level"].replace("_", " ") + (" " + t["kind"] if t.get("kind") == "castle" else "")


class MassTownWindow(tk.Toplevel):
    def __init__(self, app, picked=(), tab="building"):
        super().__init__(app)
        # the towns as the changes kept for Apply leave them (a building kept is seen, never added twice)
        self.app, self.mod, self.camp = app, app.kept_view(), app.v_campaign.get()
        self.title(TITLE)
        self.transient(app)
        self.geometry("1180x720")
        self.minsize(900, 560)
        self.pools, self.garrisons = {}, {}
        self.rng = random.Random()
        self._read()
        self.chosen = [r for r in picked if r in self.by]
        self._build(tab)
        self.fill_all()
        self.fill_chosen()

    def _read(self):
        self.towns = M.towns(self.mod, self.camp)
        self.by = {t["region"]: t for t in self.towns}
        self.known = M.known_buildings(self.mod)
        self.castles = any(t.get("kind") for t in self.towns)

    # ---- the window ----
    def _build(self, tab):
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill="both", expand=True)
        ShortHint(outer, text=(
            "Pick towns on the left (filter them by owner, level%s or name), move them to the right, then add a "
            "building to all of them, give them garrisons, or make them city / castle and of another level. Each town is checked the way the game would see it: "
            "a level the town is too small for, a castle's building in a city (or the other way), a level the "
            "owner's faction list does not allow, a port building in a town without a port - those towns are "
            "left out and the column 'What happens' says why. Only descr_strat.txt is written, with a backup; "
            "Restore (bottom bar of the main window) gives it back." % (", city / castle" if self.castles else ""))
        ).pack(anchor="w", pady=(0, 6))
        panes = ttk.PanedWindow(outer, orient="horizontal")
        panes.pack(fill="both", expand=True)
        # left: all towns
        left = ttk.LabelFrame(panes, text="All towns", padding=6)
        self.left_box = left
        flt = ttk.Frame(left)
        flt.pack(fill="x")
        owners = sorted({t["owner"] for t in self.towns})
        levels = [lv for lv in M.SETTLEMENT_LEVELS if any(t["level"] == lv for t in self.towns)]
        self.v_owner, self.v_lv, self.v_kind, self.v_find = (tk.StringVar(value=ANY) for _ in range(4))
        self.v_find.set("")
        ttk.Label(flt, text="Owner").pack(side="left")
        ttk.Combobox(flt, textvariable=self.v_owner, values=[ANY] + owners, state="readonly", width=14).pack(
            side="left", padx=(2, 8))
        ttk.Label(flt, text="Level").pack(side="left")
        ttk.Combobox(flt, textvariable=self.v_lv, values=[ANY] + [lv.replace("_", " ") for lv in levels],
                     state="readonly", width=11).pack(side="left", padx=(2, 8))
        flt2 = ttk.Frame(left)
        flt2.pack(fill="x", pady=(4, 0))
        ttk.Label(flt2, text="Find a town").pack(side="left")
        ttk.Entry(flt2, textvariable=self.v_find, width=24).pack(side="left", padx=2)
        if self.castles:
            ttk.Label(flt2, text="City / castle").pack(side="left", padx=(10, 0))
            ttk.Combobox(flt2, textvariable=self.v_kind, values=[ANY, "city", "castle"], state="readonly",
                         width=7).pack(side="left", padx=2)
        for v in (self.v_owner, self.v_lv, self.v_kind, self.v_find):
            v.trace_add("write", lambda *a: self.fill_all())
        self.t_all = self._tree(left, ("town", "owner", "level", "garrison"),
                                ("Town", "Owner", "Level", "Garrison"), (130, 100, 125, 150))
        self.t_all.bind("<Double-1>", lambda e: self.add(False))
        b = ttk.Frame(left)
        b.pack(fill="x", pady=(4, 0))
        ttk.Button(b, text="Add the selected  >", command=lambda: self.add(False)).pack(side="left")
        ttk.Button(b, text="Add all shown  >>", command=lambda: self.add(True)).pack(side="left", padx=4)
        self.lbl_all = ttk.Label(b, foreground="#555")
        self.lbl_all.pack(side="left", padx=6)
        panes.add(left, weight=1)
        # right: the chosen towns and what happens in each
        right = ttk.LabelFrame(panes, text="Chosen towns", padding=6)
        self.right_box = right
        self.t_chosen = self._tree(right, ("town", "owner", "level", "what"),
                                   ("Town", "Owner", "Level", "What happens"), (120, 90, 125, 330))
        self.t_chosen.bind("<Double-1>", lambda e: self.take_out())
        self.lbl_full = ttk.Label(right, foreground="#333", wraplength=520, justify="left")
        self.lbl_full.pack(fill="x", pady=(4, 0))
        self.t_chosen.bind("<<TreeviewSelect>>", lambda e: self._show_full())
        b = ttk.Frame(right)
        b.pack(fill="x", pady=(4, 0))
        ttk.Button(b, text="<  Take out", command=self.take_out).pack(side="left")
        ttk.Button(b, text="Clear", command=self.clear).pack(side="left", padx=4)
        self.lbl_chosen = ttk.Label(b, foreground="#555")
        self.lbl_chosen.pack(side="left", padx=6)
        panes.add(right, weight=1)
        # what to do
        self.nb = ttk.Notebook(outer)
        self.nb.pack(fill="x", pady=(8, 0))
        self.nb.add(self._building_tab(self.nb), text="  A building  ")
        self.nb.add(self._garrison_tab(self.nb), text="  Garrisons  ")
        self.nb.add(self._town_tab(self.nb), text="  City / castle and level  ")
        self.nb.select({"garrison": 1, "town": 2}.get(tab, 0))
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.fill_chosen())
        bar = ttk.Frame(outer)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="left")
        self.b_write = ttk.Button(bar, text="Keep for Apply", command=self.write)
        self.b_write.pack(side="left", padx=4)
        self.status = ttk.Label(bar, foreground="#555")
        self.status.pack(side="left", padx=8)
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")

    def _tree(self, parent, cols, heads, widths):
        box = ttk.Frame(parent)
        box.pack(fill="both", expand=True, pady=(4, 0))
        t = ttk.Treeview(box, columns=cols, show="headings", selectmode="extended")
        for c, h, w in zip(cols, heads, widths):
            t.heading(c, text=h, command=lambda c=c, t=t: self._sort(t, c))
            t.column(c, width=w, stretch=c in ("town", "what"))
        sb = ttk.Scrollbar(box, command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        t.tag_configure("skip", foreground=theme.ink("#888", "field"))
        t.tag_configure("do", foreground=theme.ink("#106010", "field"))
        return t

    def _sort(self, t, col):
        rows = [(t.set(i, col), i) for i in t.get_children("")]
        if col == "level":
            order = {lv.replace("_", " "): k for k, lv in enumerate(M.SETTLEMENT_LEVELS)}
            key = lambda r: (order.get(r[0].replace(" castle", ""), 9), r[0])
        else:
            key = lambda r: r[0].lower()
        desc = getattr(t, "_desc", None) == col
        rows.sort(key=key, reverse=desc)
        t._desc = None if desc else col
        for k, (_, i) in enumerate(rows):
            t.move(i, "", k)

    def _building_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        self.v_bact = tk.StringVar(value="add")
        self.v_chain, self.v_blv = tk.StringVar(), tk.StringVar()
        self.v_have = tk.StringVar(value="upgrade")
        self.v_anyone = tk.BooleanVar(value=False)
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Radiobutton(row, text="Add (or raise to) a level", value="add", variable=self.v_bact,
                        command=self.fill_chosen).pack(side="left")
        ttk.Radiobutton(row, text="Take a building out", value="remove", variable=self.v_bact,
                        command=self.fill_chosen).pack(side="left", padx=(12, 0))
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(6, 0))
        chains = sorted(n for n, b in self.known.items() if not M.is_core(n) and b.levels)
        ttk.Label(row, text="Building").pack(side="left")
        self.cb_chain = ttk.Combobox(row, textvariable=self.v_chain, values=chains, state="readonly", width=26)
        self.cb_chain.pack(side="left", padx=(2, 10))
        ttk.Label(row, text="Level").pack(side="left")
        self.cb_blv = ttk.Combobox(row, textvariable=self.v_blv, state="readonly", width=26)
        self.cb_blv.pack(side="left", padx=2)
        self.cb_chain.bind("<<ComboboxSelected>>", lambda e: self._chain_picked())
        self.cb_blv.bind("<<ComboboxSelected>>", lambda e: self.fill_chosen())
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="A town that has this building already:").pack(side="left")
        for text, val in (("raise it to this level (never lower)", "upgrade"), ("set it to this level", "set"),
                          ("leave it as it is", "skip")):
            ttk.Radiobutton(row, text=text, value=val, variable=self.v_have, command=self.fill_chosen).pack(
                side="left", padx=(8, 0))
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(row, text="also where the owner's faction list does not allow this level",
                        variable=self.v_anyone, command=self.fill_chosen).pack(side="left")
        hint(row, "A level's 'requires factions { ... }' in export_descr_buildings.txt says who may BUILD it. "
                  "The game loads a town that already has a building its owner could not build (a town taken "
                  "from another faction has such buildings too), but the owner cannot upgrade or rebuild it. "
                  "Off: those towns are left out.", width=480).pack(side="left")
        ttk.Label(f, text="The governor's building (the walls / the castle) follows the town's level - change "
                          "the level on the Buildings tab instead.", foreground="#666").pack(anchor="w", pady=(6, 0))
        return f

    def _town_tab(self, nb):
        """The chosen towns' own properties at once (a tester: 'select several towns and set some properties at the
        same time, like changing from city to castle')."""
        f = ttk.Frame(nb, padding=8)
        self.v_tkind, self.v_tlevel = tk.StringVar(value="as it is"), tk.StringVar(value="as it is")
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text="Make them").pack(side="left")
        for text in ("as it is", "city", "castle"):
            rb = ttk.Radiobutton(row, text=text, value=text, variable=self.v_tkind, command=self.fill_chosen)
            rb.pack(side="left", padx=(8, 0))
            if text != "as it is" and not self.castles:
                rb.state(["disabled"])
        if not self.castles:
            ttk.Label(row, text="(this game has no castles - Medieval II only)", foreground="#666").pack(
                side="left", padx=8)
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="Level").pack(side="left")
        cb = ttk.Combobox(row, textvariable=self.v_tlevel, state="readonly", width=16,
                          values=["as it is"] + list(M.SETTLEMENT_LEVELS))
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill_chosen())
        ttk.Label(f, foreground="#666", justify="left", wraplength=900, text=(
            "City <-> castle converts each town's buildings the game's way (a castle has no town hall or market; "
            "the barracks, church and roads take their castle kind). A new level brings the governor's building "
            "of that level and raises the population to the level's threshold. Written for towns of any owner; "
            "a backup first, Restore undoes it.")).pack(anchor="w", pady=(6, 0))
        return f

    def _town_choice(self):
        kind = self.v_tkind.get() if self.v_tkind.get() in ("city", "castle") else None
        level = self.v_tlevel.get() if self.v_tlevel.get() in M.SETTLEMENT_LEVELS else None
        return kind, level

    def _garrison_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        self.v_lo, self.v_hi, self.v_cap = tk.StringVar(value="2"), tk.StringVar(value="6"), tk.StringVar(value="500")
        self.v_siege, self.v_gmode = tk.BooleanVar(value=False), tk.StringVar(value="add")
        self.v_here = tk.BooleanVar(value=True)            # only what the town's own buildings recruit
        self.v_gamesize = tk.BooleanVar(value=False)       # units per town as the game's own towns of that level
        row = ttk.Frame(f)
        row.pack(fill="x")
        ttk.Label(row, text="Units per town: from").pack(side="left")
        ttk.Spinbox(row, from_=1, to=M.MAX_UNITS, textvariable=self.v_lo, width=4).pack(side="left", padx=2)
        ttk.Label(row, text="to").pack(side="left")
        ttk.Spinbox(row, from_=1, to=M.MAX_UNITS, textvariable=self.v_hi, width=4).pack(side="left", padx=2)
        ttk.Label(row, text="   their upkeep together at most").pack(side="left")
        ttk.Entry(row, textvariable=self.v_cap, width=7).pack(side="left", padx=2)
        ttk.Label(row, text="per town (empty = no limit)").pack(side="left")
        hint(row, "Each town gets a number of units picked at random between the two numbers, drawn at random "
                  "from the units its OWNER may recruit (its ownership in export_descr_unit.txt and a recruit "
                  "line of some building), generals' bodyguards left out; a rebel town from the units of the "
                  "rebel armies nearest to it (local troops). Their upkeep (the 3rd number of "
                  "stat_cost) together stays under the limit - where even the cheapest units do not fit, the "
                  "town gets fewer. 'Draw again' gives other units.", width=480).pack(side="left", padx=4)
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(6, 0))
        ttk.Radiobutton(row, text="add them to the army in the town", value="add", variable=self.v_gmode,
                        command=self.fill_chosen).pack(side="left")
        ttk.Radiobutton(row, text="replace that army's units (a general keeps his bodyguard)", value="replace",
                        variable=self.v_gmode, command=self.fill_chosen).pack(side="left", padx=(12, 0))
        ttk.Checkbutton(row, text="siege engines too", variable=self.v_siege,
                        command=lambda: (self.pools.clear(), self.draw())).pack(side="left", padx=(12, 0))
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(row, text="only units the town's own buildings recruit", variable=self.v_here,
                        command=self.draw).pack(side="left")
        ttk.Checkbutton(row, text="as many units as the game gives such a town", variable=self.v_gamesize,
                        command=self.draw).pack(side="left", padx=(12, 0))
        hint(row, "On: the number of units follows the town's level the way the mod's own towns of that owner have "
                  "them at the start (the middle value per level; vanilla's rebel towns: Medieval II village 5, "
                  "town 4, large town 7, city 6 - Rome 3, 3, 4, 4). The 'from - to' numbers above are not used then; "
                  "the upkeep limit still is.", width=480).pack(side="left", padx=4)
        hint(row, "On: a town gets only the units its own buildings recruit for its owner - no catapult in a village "
                  "without a siege workshop, no heavy infantry where there are no barracks. A town that recruits "
                  "none of them gets the cheapest units (peasants, levy spearmen): the base every town has. Off: "
                  "anything its owner recruits somewhere.", width=480).pack(side="left", padx=4)
        row = ttk.Frame(f)
        row.pack(fill="x", pady=(6, 0))
        tip(ttk.Button(row, text="Draw the garrisons", command=self.draw), "Pick the units for every chosen town "
            "(again: other units). The column 'What happens' shows them; nothing is written yet.").pack(side="left")
        ttk.Label(row, text="A town nobody holds gets a captain who leads its garrison. An army holds 20 units "
                            "at most.", foreground="#666").pack(side="left", padx=10)
        return f

    # ---- the lists ----
    def _shown(self):
        o, lv, k, q = self.v_owner.get(), self.v_lv.get(), self.v_kind.get(), self.v_find.get().strip().lower()
        for t in self.towns:
            if o != ANY and t["owner"] != o or lv != ANY and t["level"] != lv.replace(" ", "_"):
                continue
            if k != ANY and t.get("kind") != k:
                continue
            if q and q not in t["name"].lower() and q not in t["region"].lower():
                continue
            yield t

    @staticmethod
    def _garrison_text(t):
        return "%d unit(s), upkeep %d" % (t["units"], t["upkeep"]) if t["units"] else "none"

    def fill_all(self):
        tv = getattr(self, "t_all", None)
        if tv is None or not tv.winfo_exists():         # a filter's variable written as the window closes
            return
        tv.delete(*tv.get_children(""))
        n = 0
        for t in self._shown():
            if t["region"] in self.chosen:
                continue
            tv.insert("", "end", iid=t["region"], values=(t["name"], t["owner"], _level(t),
                                                          self._garrison_text(t)))
            n += 1
        from .gui_util import tint_owners
        tint_owners(tv, {t["region"]: t["owner"] for t in self._shown() if tv.exists(t["region"])}, self.app.mod)
        self.left_box.configure(text="All towns - %d shown of %d" % (n, len(self.towns) - len(self.chosen)))

    def _what(self, t):
        """(text, tag) for the column 'What happens' of a chosen town."""
        if self.nb.index("current") == 2:
            kind, level = self._town_choice()
            if not kind and not level:
                return "", ""
            what, why = M.town_fit(self.known, t, kind, level)
            return ("left out: " + why if what == "skip" else why), ("skip" if what == "skip" else "do")
        if self.nb.index("current") == 1:
            if t["region"] in self.garrisons:
                units = self.garrisons[t["region"]]
                pool = dict(self._pool(t))
                if not units:
                    return "no unit fits under the upkeep limit", "skip"
                return "%s%d: %s (upkeep %d)" % ("+" if self.v_gmode.get() == "add" else "= ", len(units),
                                                 ", ".join(units), sum(pool.get(u, 0) for u in units)), "do"
            if not self._pool(t):
                return "%s has no unit to draw from" % t["owner"], "skip"
            return "garrison now: %s - press 'Draw the garrisons'" % self._garrison_text(t), ""
        chain = self.v_chain.get()
        if not chain:
            return "", ""
        level = None if self.v_bact.get() == "remove" else self.v_blv.get() or None
        if level is None and self.v_bact.get() == "add":
            return "", ""
        what, why = M.building_fit(self.known, t, chain, level, self.v_have.get(), self.v_anyone.get())
        return ("left out: " + why if what == "skip" else why), ("skip" if what == "skip" else "do")

    def fill_chosen(self):
        tv = self.t_chosen
        tv.delete(*tv.get_children(""))
        do = 0
        for r in self.chosen:
            t = self.by[r]
            text, tag = self._what(t)
            do += tag == "do"
            tv.insert("", "end", iid=r, values=(t["name"], t["owner"], _level(t), text), tags=(tag,) if tag else ())
        from .gui_util import tint_owners
        tint_owners(tv, {r: self.by[r]["owner"] for r in self.chosen}, self.app.mod)
        self.right_box.configure(text="Chosen towns - %d" % len(self.chosen))
        self.lbl_chosen.configure(text="%d will change" % do if self.chosen else "")

    def _show_full(self):
        """The selected town's whole 'What happens' (the column is often too narrow for a garrison's units)."""
        sel = self.t_chosen.selection()
        if len(sel) == 1:
            t = self.by[sel[0]]
            self.lbl_full.configure(text="%s: %s" % (t["name"], self.t_chosen.set(sel[0], "what")))
        else:
            self.lbl_full.configure(text="")

    def add(self, shown):
        tv = self.t_all
        ids = tv.get_children("") if shown else tv.selection()
        self.chosen += [r for r in ids if r not in self.chosen]
        self.fill_all()
        self.fill_chosen()

    def take_out(self):
        gone = set(self.t_chosen.selection())
        self.chosen = [r for r in self.chosen if r not in gone]
        for r in gone:
            self.garrisons.pop(r, None)
        self.fill_all()
        self.fill_chosen()

    def clear(self):
        self.chosen, self.garrisons = [], {}
        self.fill_all()
        self.fill_chosen()

    def _chain_picked(self):
        b = self.known.get(self.v_chain.get())
        names = [l.name for l in b.levels] if b else []
        self.cb_blv["values"] = names
        if self.v_blv.get() not in names:
            self.v_blv.set(names[0] if names else "")
        self.fill_chosen()

    # ---- garrisons ----
    def _pool(self, t):
        """The units a town's garrison is drawn from: its owner's (a rebel town: the nearest rebel armies')."""
        key = ("slave", t["region"]) if t["owner"] == "slave" else t["owner"]
        if key not in self.pools:
            self.pools[key] = (M.rebel_pool(self.mod, self.camp, t["region"], siege=self.v_siege.get())
                               if t["owner"] == "slave" else
                               M.garrison_pool(self.mod, t["owner"], siege=self.v_siege.get()))
        return self.pools[key]

    def _town_pool(self, t):
        """_pool narrowed to what the town's own buildings recruit (masstown.town_pool) when that box is ticked."""
        pool = self._pool(t)
        return M.town_pool(self.mod, t, pool) if self.v_here.get() else pool

    def _numbers(self):
        try:
            lo, hi = int(self.v_lo.get()), int(self.v_hi.get())
        except ValueError:
            raise ValueError("The number of units must be whole numbers")
        cap = self.v_cap.get().strip()
        try:
            cap = int(cap) if cap else None
        except ValueError:
            raise ValueError("The upkeep limit must be a whole number (or empty for no limit)")
        if not 1 <= min(lo, hi) or max(lo, hi) > M.MAX_UNITS:
            raise ValueError("Units per town: 1 to %d" % M.MAX_UNITS)
        return lo, hi, cap

    def draw(self):
        if not self.chosen:
            self.status.configure(text="choose towns first")
            return
        try:
            lo, hi, cap = self._numbers()
        except ValueError as e:
            messagebox.showwarning(TITLE, str(e), parent=self)
            return
        self.nb.select(1)
        sizes = {}
        self.garrisons = {}
        for r in self.chosen:
            t = self.by[r]
            a, b = lo, hi
            if self.v_gamesize.get():
                if t["owner"] not in sizes:
                    sizes[t["owner"]] = M.level_sizes(self.mod, self.camp, t["owner"])
                a = b = max(1, min(M.MAX_UNITS, sizes[t["owner"]].get(t["level"], lo)))
            self.garrisons[r] = M.random_garrison(self._town_pool(t), a, b, cap, self.rng)
        self.fill_chosen()
        self.status.configure(text="garrisons drawn - Preview, or Keep for Apply")

    # ---- writing ----
    def opts(self):
        """The opts for masstown.apply from the tab on show, or raises ValueError in plain words."""
        if not self.chosen:
            raise ValueError("Choose towns first (left list > right list).")
        if self.nb.index("current") == 2:
            kind, level = self._town_choice()
            if not kind and not level:
                raise ValueError("Pick city / castle or a level.")
            got = {r: {"kind": kind, "level": level} for r in self.chosen
                   if M.town_fit(self.known, self.by[r], kind, level)[0] == "set"}
            if not got:
                raise ValueError("No chosen town changes - 'What happens' says why for each.")
            return {"towns": got}
        if self.nb.index("current") == 1:
            if not self.garrisons:
                raise ValueError("Press 'Draw the garrisons' first - the units show in 'What happens'.")
            got = {r: u for r, u in self.garrisons.items() if u and r in self.chosen}
            if not got:
                raise ValueError("No town got a unit - raise the upkeep limit.")
            return {"garrisons": got, "add_units": self.v_gmode.get() == "add"}
        chain = self.v_chain.get()
        if not chain:
            raise ValueError("Pick a building.")
        remove = self.v_bact.get() == "remove"
        level = None if remove else self.v_blv.get()
        out = {}
        for r in self.chosen:
            what, _ = M.building_fit(self.known, self.by[r], chain, level, self.v_have.get(), self.v_anyone.get())
            if what in ("add", "upgrade", "set"):
                out[r] = (chain, level)
            elif what == "remove":
                out[r] = chain
        if not out:
            raise ValueError("No chosen town can take it - 'What happens' says why for each.")
        return {"remove": out} if remove else {"build": out}

    def _plan(self):
        from .plan import Plan
        plan = Plan(self.mod, "towns", "towns", {})
        o = self.opts()
        M.apply(plan, self.camp, o)
        plan.towns_written = len(o.get("build") or o.get("remove") or o.get("garrisons") or o.get("towns") or {})
        return plan

    def preview(self):
        try:
            plan = self._plan()
        except ValueError as e:
            messagebox.showinfo(TITLE, str(e), parent=self)
            return
        self.app.show_text("Preview - " + TITLE, plan.report(), wrap="word")

    def write(self):
        """Keep for Apply: this change for many towns goes into the session's list (each one a part of its own),
        written by the main window's Apply changes with everything else."""
        from .gui_util import keep_for_apply
        try:
            plan = self._plan()
        except ValueError as e:
            messagebox.showinfo(TITLE, str(e), parent=self)
            return False
        n = plan.towns_written
        App = type(self.app)
        App._towns_kept = getattr(App, "_towns_kept", 0) + 1

        def after(bdir):
            from . import log
            log.write("%s (backup %s)" % (TITLE, bdir))
            if self.winfo_exists():
                self.mod = self.app.kept_view()
                self._read()
                self.garrisons = {}
                self.fill_all()
                self.fill_chosen()
                self.status.configure(text="written for %d town(s) (backup %s)" % (n, bdir))
        if keep_for_apply(self, "towns:%d" % App._towns_kept, "%s: %d town(s)" % (TITLE, n), lambda: plan, after,
                          TITLE):
            self.mod = self.app.kept_view()               # the towns as kept: the change is seen in the lists
            self.pools = {}
            self._read()
            self.garrisons = {}
            self.fill_all()
            self.fill_chosen()
            self.status.configure(text="kept for %d town(s) - shown in the lists; Apply changes in the main window "
                                       "writes it" % n)
            return True
        return False


__all__ = ["MassTownWindow"]
