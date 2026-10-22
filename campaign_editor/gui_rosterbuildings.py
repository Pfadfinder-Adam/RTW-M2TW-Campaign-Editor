"""The Roster's 'By buildings' tab (Edit faction): the faction's buildings as tiles, a building's levels as steps, the
units a level recruits as cards - the Buildings work's 'By faction' view (gui_factionbuildings) with every piece
given or taken away right there, as garrisons are picked: on the right every unit of the mod, a click adds it to
the picked level AND every level above it in the chain (the game trains only what the town's current level lists -
a unit put in one level was gone once the building grew, report #283); the x on a card takes it from that level and
the ones above. '+ Building' lists the chains the faction may not build yet - a click lets it build every level; the
x on a tile takes the building away; the + / x on a level gives it with the ones below / takes it with the ones
above (the game builds a chain level by level). The picks go into App.roster_set beside the 'Units and levels'
tab's (Undo, Preview, Apply - roster.apply writes them)."""

import tkinter as tk
from tkinter import ttk

from . import factionbuildings as FB
from . import theme
from .gui_factionbuildings import CARD, FactionBuildings
from .gui_util import ScrollFrame, tip


class RosterBuildings(FactionBuildings):
    PICK_FACTION = False                             # the faction is the one Edit faction has picked

    def __init__(self, master, app):
        self._raw = []
        super().__init__(master, app, None)
        self.hint.configure(text=(
            "Pick a building on the left, a level of it in the middle; click a unit on the right (All units) to add "
            "it to that level and every level above it - the game trains only what the town's current level "
            "lists. The x on a card takes the unit from that level and the ones above; + Building lets the faction "
            "build a chain, the x on a tile takes it away; the + / x on a level gives it with the ones below / "
            "takes it with the ones above. Green = added, red = taken away, written on Apply (Preview first; "
            "Undo works)."))

    # ---- the pieces it adds to the By faction view ----
    def _bar_extra(self, bar):
        self.title = ttk.Label(bar, text="", font=("", 10, "bold"))
        self.title.pack(side="left", padx=(0, 8))
        b = ttk.Button(bar, text="+ Building", command=self.building_list)
        b.pack(side="left", padx=4)
        tip(b, "Every building chain the faction may not build yet: click one to let it build every level.")

    def _build_right(self, right):
        self.side = ttk.Notebook(right)
        self.side.pack(fill="both", expand=True)
        pick = ttk.Frame(self.side, padding=2)
        self.side.add(pick, text="All units")
        one = ttk.Frame(self.side, padding=2)
        self.side.add(one, text="Unit")
        super()._build_right(one)
        top = ttk.Frame(pick)
        top.pack(fill="x")
        ttk.Label(top, text="Find").pack(side="left")
        self.v_ufind = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.v_ufind, width=14)
        e.pack(side="left", padx=4)
        e.bind("<KeyRelease>", lambda ev: self.fill_units())
        self.v_cat = tk.StringVar(value="all")
        self.cb_cat = ttk.Combobox(top, textvariable=self.v_cat, values=["all"], state="readonly", width=10)
        self.cb_cat.pack(side="left", padx=4)
        self.cb_cat.bind("<<ComboboxSelected>>", lambda ev: self.fill_units())
        self.v_mine = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="only its units", variable=self.v_mine, command=self.fill_units).pack(side="left")
        self.lbl_pick = ttk.Label(pick, text="", justify="left")
        self.lbl_pick.pack(fill="x", pady=(2, 2))
        self.lbl_pick.bind("<Configure>", lambda ev: self.lbl_pick.configure(wraplength=max(120, ev.width - 4)),
                           add="+")
        self.grid_units = ScrollFrame(pick)
        self.grid_units.pack(fill="both", expand=True)
        self.grid_units.cols = 0
        self.grid_units.canvas.bind("<Configure>", lambda ev: self._reflow(), add="+")
        self.lbl_info = ttk.Label(pick, text="", foreground=theme.ink("#444", "bg"), justify="left")
        self.lbl_info.pack(fill="x")

    def _changed(self, items):
        self._raw = items
        return FB.with_changes(items, self.app.roster_set)

    def _tile_made(self, box, c):
        self._corner(box, "x" if c["builds"] else "+", lambda: self.give_chain(c, not c["builds"]),
                     "Take the whole building away from %s" % self._faction() if c["builds"] else
                     "Let %s build every level of it" % self._faction())

    def _level_made(self, box, lv):
        c = self.chain
        self._corner(box, "x" if lv["has"] else "+", lambda: self.give_level(c, lv["name"], not lv["has"]),
                     "Take this level away (and the ones above it)" if lv["has"] else
                     "Let %s build this level (and the ones below it)" % self._faction())

    def _card_made(self, box, u, lv):
        if u.get("pending") == "take":
            self._corner(box, "+", lambda: self.give_unit(u["unit"], lv["name"], True),
                         "Keep it here (and in the levels above)")
        else:
            self._corner(box, "x", lambda: self.give_unit(u["unit"], lv["name"], False),
                         "Take it from this level and every level above it")

    def _level_tail(self, parent, c, lv):
        if lv["has"]:
            above = [x["name"] for x in c["levels"]]
            n = len(above) - above.index(lv["name"]) - 1
            text = "Add a unit: click it under All units on the right - it goes to %s%s." % (
                self._level_name(lv["name"]), " and the %d level(s) above it" % n if n else "")
        else:
            text = "%s may not build this level: its + lets it (with the levels below), then add units." % (
                self._faction())
        self._wrapped(ttk.Label(parent, text=text, foreground=theme.ink("#555", "bg"), justify="left")).pack(
            fill="x", anchor="w", pady=(4, 0))
        self._pick_words()

    @staticmethod
    def _corner(box, sign, command, words):
        """A small + / x in the tile's top right corner (a click there does not pick the tile)."""
        pal = theme.palette()
        for w in box.winfo_children():              # the words keep clear of the corner
            if isinstance(w, tk.Label) and w.cget("text"):
                w.pack_configure(padx=(2, 16))
        lb = tk.Label(box, text="✕" if sign == "x" else "+", font=("", 9, "bold"), cursor="hand2", padx=2, pady=0,
                      background=theme.mark("take" if sign == "x" else "give"), foreground=pal["fg"])
        lb.place(relx=1.0, x=-1, y=1, anchor="ne")
        lb.bind("<Button-1>", lambda e: (command(), "break")[1])
        tip(lb, words)

    # ---- the faction and reading ----
    def _faction(self):
        try:
            return self.app.v["template"].get().strip() if self.app.editing() else ""
        except Exception:
            return ""

    def refresh(self):
        self._stale = False
        fac = self._faction()
        if self.mod is None or not fac:
            self.items, self._raw = [], []
            self.title.configure(text="Pick the faction on the Faction tab (Edit faction)")
            self._clear(self.left.inner)
            self.show_chain(None)
            return
        self.title.configure(text="%s (%s)" % (fac, self.mod.culture(fac) or "?"))
        self._read()
        self._fill_categories()
        self.fill_units()

    def forget(self):
        """The files changed (Apply, Restore, another mod): read again when shown."""
        self._stale = True
        self._pics = self._texts = self._utexts = self._units = None

    def shown(self):
        if self._stale or self._for != self._faction():
            self.refresh()

    @property
    def _for(self):
        return getattr(self, "_read_for", None)

    def _read(self):
        self._read_for = self._faction()
        super()._read()

    def relay(self):
        """The picks changed (here, on Units and levels, Undo): the view again without reading the files."""
        if not self._raw or self._for != self._faction():
            if self.winfo_ismapped():
                self.refresh()
            else:
                self._stale = True
            return
        self.items = self._changed(self._raw)
        self._tiles()
        keep = next((c for c in self.items if self.chain and c["chain"] == self.chain["chain"]), None)
        self.show_chain(keep, self.level["name"] if keep and self.level else None)
        self.fill_units()

    def show_unit(self, unit):
        super().show_unit(unit)
        self.side.select(1)

    # ---- the picks ----
    def _raw_chain(self, c):
        return next((x for x in self._raw if x["chain"] == c["chain"]), None)

    def _set(self, pairs):
        """[(key, give or None)] into App.roster_set (None: back to what the files say), one Undo step."""
        if not pairs:
            return
        self.app.remember()
        for key, give in pairs:
            if give is None:
                self.app.roster_set.pop(key, None)
            else:
                self.app.roster_set[key] = give
        self.app.roster_changed()
        self.relay()

    def give_unit(self, unit, level, give):
        c = self._raw_chain(self.chain) if self.chain else None
        if c is None:
            return
        levels = {x["name"]: x for x in c["levels"]}
        shown = next((x for x in self.items if x["chain"] == c["chain"]), c)
        if give and not next((x for x in shown["levels"] if x["name"] == level), {}).get("has"):
            self.app.status.set("%s may not build %s: let it build the level first (its +)." % (
                self._faction(), level))
            return
        # what the files say each level recruits for the faction (a pick there is dropped when it says the same)
        pairs = FB.upward(c, level, unit, give, lambda n: any(u["unit"] == unit for u in levels[n]["units"]))
        self._set(pairs)
        if len(pairs) > 1:
            self.app.status.set("%s %s %s and the level(s) above it (%s) - Preview, then Apply changes." % (
                unit, "added to" if give else "taken from", level, ", ".join(k.split(":")[2] for k, _ in pairs[1:])))

    def _level_keys(self, c, names, give):
        raw = {x["name"]: x for x in c["levels"]}
        return [("building:%s:%s" % (c["chain"], n), None if bool(raw[n]["has"]) == give else give) for n in names]

    def give_level(self, c, level, give):
        """A level given with the ones below it, or taken away with the ones above (no gap in the chain - the game
        stops at 'faction has gap in building')."""
        rc = self._raw_chain(c)
        if rc is None:
            return
        names = [x["name"] for x in rc["levels"]]
        i = names.index(level)
        self._set(self._level_keys(rc, names[:i + 1] if give else names[i:], give))

    def give_chain(self, c, give):
        rc = self._raw_chain(c)
        if rc is not None:
            self._set(self._level_keys(rc, [x["name"] for x in rc["levels"]], give))

    # ---- + Building: the chains it may not build yet ----
    def building_list(self):
        if not self.items:
            self.app.status.set("Pick the faction on the Faction tab (Edit faction) first.")
            return
        top = tk.Toplevel(self)
        top.title("Add a building to %s" % self._faction())
        top.transient(self.winfo_toplevel())
        top.geometry("420x480")
        frame = ttk.Frame(top, padding=6)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Click a building: %s may build every level of it (written on Apply)."
                  % self._faction(), wraplength=400, justify="left").pack(fill="x")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Find").pack(side="left")
        v = tk.StringVar()
        e = ttk.Entry(row, textvariable=v)
        e.pack(side="left", fill="x", expand=True, padx=4)
        box = ttk.Frame(frame)
        box.pack(fill="both", expand=True)
        tv = ttk.Treeview(box, columns=("levels",), show="tree headings", selectmode="browse")
        tv.heading("#0", text="building")
        tv.heading("levels", text="levels it may build")
        tv.column("#0", width=260)
        tv.column("levels", width=120, stretch=False)
        sb = ttk.Scrollbar(box, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)

        def fill(_=None):
            tv.delete(*tv.get_children())
            q = v.get().strip().lower()
            for c in self.items:
                n = sum(1 for x in c["levels"] if x["has"])
                first = c["levels"][0]["name"] if c["levels"] else c["chain"]
                words = "%s - %s" % (c["chain"], self._level_name(first))
                if n == len(c["levels"]) or q and q not in words.lower():
                    continue
                tv.insert("", "end", iid=c["chain"], text=words, values=("%d of %d" % (n, len(c["levels"])),))

        def picked(_=None):
            item = tv.focus()
            c = next((x for x in self.items if x["chain"] == item), None)
            if c is not None:
                self.give_chain(c, True)
                self.show_chain(next((x for x in self.items if x["chain"] == item), None))
                fill()
        e.bind("<KeyRelease>", fill)
        tv.bind("<ButtonRelease-1>", picked)
        tv.bind("<Return>", picked)
        ttk.Button(frame, text="Close", command=top.destroy).pack(anchor="e", pady=(4, 0))
        fill()
        e.focus_set()

    # ---- All units: click to add ----
    def _fill_categories(self):
        cats = sorted({u.category for u in (self._units or {}).values() if u.category})
        self.cb_cat["values"] = ["all"] + cats
        if self.v_cat.get() not in self.cb_cat["values"]:
            self.v_cat.set("all")

    def _owners(self):
        fac = self._faction()
        culture = self.mod.culture(fac) if self.mod and fac else None
        return {x for x in (fac, culture, "all") if x}

    def visible_units(self):
        q = self.v_ufind.get().strip().lower()
        cat = self.v_cat.get()
        owners = self._owners()
        out = []
        for u in (self._units or {}).values():
            if u.category == "non_combatant" or cat != "all" and u.category != cat:
                continue
            if self.v_mine.get() and not owners & set(u.ownership):
                continue
            if q and q not in u.type.lower() and q not in self._unit_name(u.type).lower():
                continue
            out.append(u)
        return sorted(out, key=lambda u: (u.category, u.type))

    def _pick_words(self):
        lv = self.level
        if lv is None or self.chain is None:
            text = "Pick a building and a level of it, then click a unit here to add it there."
        elif not lv["has"]:
            text = "%s may not build %s - let it build the level first." % (self._faction(), lv["name"])
        else:
            text = "A click adds the unit to %s / %s and every level above it." % (self.chain["chain"], lv["name"])
        self.lbl_pick.configure(text=text)

    def fill_units(self):
        inner = self.grid_units.inner
        self._clear(inner)
        self.grid_units.cols = 0
        if self.mod is None:
            return
        owners = self._owners()
        for u in self.visible_units():
            img = self._unit_card(u.type)
            mine = bool(owners & set(u.ownership))
            b = tk.Button(inner, image=img, text=u.type if img is None else "", compound="top", relief="flat",
                          cursor="hand2", command=lambda u=u: self.add(u.type), width=None if img else 10,
                          wraplength=80, font=("", 8), pady=0)
            b.image = img
            words = "%s%s\n%s" % (self._unit_name(u.type) or u.type,
                                  "" if mine else "  (not its unit yet - it becomes its own)", u.summary())
            b.bind("<Enter>", lambda e, w=words: self.lbl_info.configure(text=w))
            b.bind("<Leave>", lambda e: self.lbl_info.configure(text=""))
            b.bind("<Button-3>", lambda e, u=u: self.show_unit(u.type))
        self._reflow()
        self._pick_words()

    def _reflow(self):
        inner = self.grid_units.inner
        kids = inner.winfo_children()
        if not kids:
            return
        cell = max(CARD[0] + 8, kids[0].winfo_reqwidth() + 2)
        width = self.grid_units.canvas.winfo_width()
        if width <= 1:
            width = 300
        cols = max(1, (width - 4) // cell)
        if cols == self.grid_units.cols:
            return
        self.grid_units.cols = cols
        for i, w in enumerate(kids):
            w.grid(row=i // cols, column=i % cols, padx=1, pady=1)

    def add(self, unit):
        """A click on a unit under All units: into the picked level and every level above it."""
        if self.chain is None or self.level is None:
            self.app.status.set("Pick a building and a level of it first (on the left, then in the middle).")
            return
        self.give_unit(unit, self.level["name"], True)
