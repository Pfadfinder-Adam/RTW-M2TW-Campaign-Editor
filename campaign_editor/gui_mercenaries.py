"""Mercenaries... (the work bar; a right click on the map: 'Mercenaries for hire in <region>...', and with Select on:
'New mercenary pool from the selected regions...'): the campaign's mercenary pools in one window, two tabs.

'For hire in a region' (the right click opens it): the region's list the way a garrison is made - the mercenaries'
cards on the left, a click adds one, the units for hire on the right, a click picks one for its numbers. A region
shares its list with the other regions of its pool: said above the cards, and 'A list of its own' splits it off.

'Pools': the pools. A pool picked here is selected on the map (Select switches on, its regions show yellow), so its
regions can be changed the map's own way - a box adds, Shift + box takes away - and 'Take the map's selection'
gives the pool exactly what is selected. 'New pool from the map's selection' makes a pool of the selected regions.
Right: the pool's units with their numbers in plain words; a picked unit's numbers are changed in the fields under
the list. Nothing is written before 'Keep for Apply' and then Apply changes in the main window, which writes it with
the rest of the session (a backup first; Undo this write / Tools > Restore a backup undo it)."""

import hashlib
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import mercenaries as M
from . import theme

TITLE = "Mercenaries"
COLS = (("initial", "at the start", 0), ("max", "at most", 0), ("back", "comes back a turn", 0),
        ("every", "one every", 110), ("cost", "cost", 0), ("exp", "experience", 0), ("more", "more", 200))
FIELDS = (("initial", "At the start"), ("max", "At most"), ("lo", "Comes back from"), ("hi", "up to"),
          ("cost", "Cost"), ("exp", "Experience"))


def _hash(path):
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


class MercWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.mod, self.campaign = app, app.mod, app.v_campaign.get()
        self.transient(app)
        self.resizable(True, True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d" % (min(1120, sw - 40), min(680, sh - 100)))
        self.minsize(min(640, sw - 40), min(420, sh - 100))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.units = M.mercenary_units(self.mod)
        self._build()
        self.reload()

    # ---- the window ----
    def _build(self):
        bar = ttk.Frame(self, padding=(10, 4, 10, 10))
        bar.pack(side="bottom", fill="x")
        self.lbl_problems = ttk.Label(bar, foreground=theme.ink("#c00000"), wraplength=700, justify="left")
        self.lbl_problems.pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Keep for Apply", command=self.write).pack(side="right", padx=(0, 6))
        ttk.Button(bar, text="Show every change...", command=self.preview).pack(side="right", padx=(0, 6))
        top = ttk.Frame(self, padding=(10, 10, 10, 0))
        top.pack(fill="x")
        self.lbl_title = ttk.Label(top, font=("", 12, "bold"))
        self.lbl_title.pack(anchor="w")
        self.lbl_file = ttk.Label(top, foreground=theme.palette()["muted"])
        self.lbl_file.pack(anchor="w")
        ttk.Label(top, wraplength=1000, justify="left", text=(
            "Who is for hire where. A region takes its mercenaries from its pool: the regions of one pool share one "
            "list. 'For hire in a region' makes a region's list the way a garrison is made; 'Pools' groups the "
            "regions on the map (a box adds, Shift + box takes away). Keep for Apply, then Apply changes in the main window writes it.")
                  ).pack(anchor="w", pady=(2, 6))
        # the picked unit's numbers: under both tabs, for the unit picked on either
        ed = ttk.LabelFrame(self, text="The picked unit", padding=8)
        ed.pack(side="bottom", fill="x", padx=10, pady=(6, 0))
        self._numbers(ed)
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10)
        self._region_tab()
        body = ttk.PanedWindow(self.nb, orient="horizontal")
        self.nb.add(body, text="Pools")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._tab_changed())
        # left: the pools
        left = ttk.Frame(body)
        body.add(left, weight=1)
        ttk.Label(left, text="Pools", font=("", 10, "bold")).pack(anchor="w")
        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True)
        self.lb = tk.Listbox(lf, exportselection=False, width=40, activestyle="none")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.show())
        for text, fn in (("New pool from the map's selection", self.new_pool), ("Rename...", self.rename)):
            ttk.Button(left, text=text, command=fn).pack(fill="x", pady=(4, 0))
        # destructive: set apart from the others (NN/g - a slip onto it costs the pool)
        ttk.Button(left, text="Delete this pool...", command=self.delete_pool).pack(fill="x", pady=(16, 0))
        # right: the pool picked
        right = ttk.Frame(body, padding=(10, 0, 0, 0))
        body.add(right, weight=3)
        self.lbl_pool = ttk.Label(right, font=("", 10, "bold"))
        self.lbl_pool.pack(anchor="w")
        self.lbl_regions = ttk.Label(right, wraplength=700, justify="left")
        self.lbl_regions.pack(anchor="w", fill="x")
        rb = ttk.Frame(right)
        rb.pack(anchor="w", pady=(4, 8))
        for text, fn in (("Show them on the map", self.show_on_map), ("Take the map's selection", self.take_selection),
                         ("Add the map's selection", lambda: self.take_selection(add=True))):
            ttk.Button(rb, text=text, command=fn).pack(side="left", padx=(0, 6))
        ttk.Label(right, text="For hire here", font=("", 10, "bold")).pack(anchor="w")
        tf = ttk.Frame(right)
        tf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=[c for c, _, _ in COLS], selectmode="browse", height=8)
        self.tree.heading("#0", text="unit")
        self.tree.column("#0", width=230, minwidth=150, stretch=True)
        import tkinter.font as tkfont
        font = tkfont.nametofont("TkHeadingFont")
        for c, text, width in COLS:                     # every heading whole (the user: no text cut at the edge)
            self.tree.heading(c, text=text)
            w = max(width, font.measure(text) + 24)
            self.tree.column(c, width=w, minwidth=w, stretch=c == "more", anchor="w" if c == "more" else "center")
        ts = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ts.set, xscrollcommand=xs.set)
        xs.pack(side="bottom", fill="x")
        ts.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_unit())
        add = ttk.Frame(right)
        add.pack(fill="x", pady=(6, 0))
        ttk.Label(add, text="Add for hire:").pack(side="left")
        self.v_add = tk.StringVar()
        self.cb_add = ttk.Combobox(add, textvariable=self.v_add, width=36,
                                   values=[u.type for u in self.units])
        self.cb_add.pack(side="left", padx=(6, 6))
        ttk.Button(add, text="Add", command=self.add_unit).pack(side="left")
        ttk.Button(add, text="Take the picked unit out", command=self.remove_unit).pack(side="left", padx=(6, 0))
    def _region_tab(self):
        """For hire in a region: the region's list the garrison way - mercenaries' cards left (a click adds), the
        units for hire right (a click picks one for its numbers)."""
        from .gui_garrison import Pictures
        self.pics = getattr(self.app, "pictures", None) or Pictures()
        tab = ttk.Frame(self.nb, padding=(0, 6, 0, 0))
        self.nb.add(tab, text="For hire in a region")
        row = ttk.Frame(tab)
        row.pack(fill="x")
        ttk.Label(row, text="Region").pack(side="left")
        self.v_region = tk.StringVar()
        self.cb_region = ttk.Combobox(row, textvariable=self.v_region, state="readonly", width=40)
        self.cb_region.pack(side="left", padx=(6, 10))
        self.cb_region.bind("<<ComboboxSelected>>", lambda e: self.show_region())
        ttk.Button(row, text="Show it on the map", command=self.region_on_map).pack(side="left")
        self.lbl_shared = ttk.Label(tab, justify="left", wraplength=900)
        self.lbl_shared.pack(anchor="w", fill="x", pady=(4, 0))
        row2 = ttk.Frame(tab)
        row2.pack(anchor="w", pady=(2, 4))
        self.b_own = ttk.Button(row2, text="A list of its own (leave the pool)", command=self.own_list)
        self.b_own.pack(side="left")
        self.b_take = ttk.Button(row2, text="Take the picked unit out", command=self.remove_unit)
        self.b_take.pack(side="left", padx=(6, 0))
        self.lbl_card = ttk.Label(tab, foreground=theme.palette()["muted"])
        self.lbl_card.pack(anchor="w", fill="x")
        panes = ttk.Panedwindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = ttk.LabelFrame(panes, text="Mercenaries - click to add")
        right = ttk.LabelFrame(panes, text="For hire here - click to pick")
        panes.add(left, weight=3)
        panes.add(right, weight=2)
        self.cards_all = self._cards_box(left)
        self.cards_here = self._cards_box(right)
        self._picked_unit = None

    def _cards_box(self, parent):
        from .gui_util import scroll_y, wheel
        canvas = tk.Canvas(parent, highlightthickness=0, background=theme.palette()["field"])
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, background=theme.palette()["field"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner.canvas, inner.cols = canvas, 0
        canvas.bind("<Configure>", lambda e: self._reflow(inner, force=True), add="+")
        wheel(canvas, scroll_y(canvas))
        return inner

    def _reflow(self, inner, force=False):
        kids = inner.winfo_children()
        cell = (kids[0].winfo_reqwidth() + 2) if kids else 58
        cols = max(1, (inner.canvas.winfo_width() - 4) // cell)
        if cols == inner.cols and not force:
            return
        inner.cols = cols
        for i, w in enumerate(kids):
            w.grid(row=i // cols, column=i % cols, padx=1, pady=1)

    def _card_img(self, name):
        from .units import card_path
        u = next((x for x in self.units if x.type == name), None)
        path = None
        if u is not None:
            for folder in ("mercs", "mercenaries", "merc"):          # the games' own mercenary folders first
                path = card_path(self.mod, folder, u.dictionary)
                if path:
                    break
        return self.pics.get(path) or self.pics.missing(name)

    def _card(self, parent, name, under, command, summary):
        img = self._card_img(name)
        b = tk.Button(parent, image=img, text=under, compound="top" if img else "none", wraplength=90,
                      width=None if img else 12, relief="flat", command=command, cursor="hand2", font=("", 8), pady=0)
        b.image = img
        b.bind("<Enter>", lambda e: self.lbl_card.configure(text=summary))
        b.bind("<Leave>", lambda e: self.lbl_card.configure(text=""))
        return b

    def _regions(self):
        names = self._town_names()
        regs = sorted(self.mod.regions(self.campaign), key=lambda r: (names.get(r) or r).lower())
        self._region_of = {("%s (%s)" % (names[r], r) if names.get(r) and names[r] != r else r): r for r in regs}
        self.cb_region.configure(values=list(self._region_of))

    def region(self):
        return getattr(self, "_region_of", {}).get(self.v_region.get())

    def pick_region(self, region):
        self._regions()
        label = next((k for k, v in self._region_of.items() if v == region), None)
        if label:
            self.v_region.set(label)
        self.nb.select(0)
        self.show_region()

    def show_region(self, keep=None):
        r = self.region()
        for w in self.cards_here.winfo_children():
            w.destroy()
        self.cards_here.cols = 0
        if not self.cards_all.winfo_children():
            self._fill_roster()
        self._picked_unit = keep
        if r is None:
            self.lbl_shared.configure(text="Pick a region above (or right click it on the map > Mercenaries for hire "
                                           "in ...).")
            self.b_own.state(["disabled"])
            self.show_unit()
            return
        p = M.pool_of(self.pools, r)
        names = self._town_names()
        if p is None:
            self.lbl_shared.configure(text="%s is in no pool: nobody is for hire there. Click a card on the left to "
                                           "give it a list of its own." % r)
        else:
            others = [q for q in p.regions if q != r]
            self.lbl_shared.configure(text=(
                "Pool %s. %s" % (p.name, ("The same list is for hire in %d other region(s): %s - a change here is a "
                                          "change there too ('A list of its own' takes %s out of the pool first)." % (
                    len(others), ", ".join(names.get(q) or q for q in others[:12]) + (" ..." if len(others) > 12
                                                                                     else ""), r))
                                         if others else "Only this region uses it.")))
        self.b_own.state(["!disabled"] if p is not None and len(p.regions) > 1 else ["disabled"])
        for u in (p.units if p else []):
            b = self._card(self.cards_here, u.name, "%s / %s" % (u.initial, u.max), lambda x=u: self.pick_here(x),
                           "%s: %s" % (u.name, u.words()))
            if u is keep:
                b.configure(relief="solid", borderwidth=2)
        self.after_idle(lambda: self._reflow(self.cards_here, True))
        self.show_unit()

    def _fill_roster(self):
        """Every unit that may be hired (mercenary_unit in export_descr_unit.txt), once."""
        for u in self.units:
            self._card(self.cards_all, u.type, str(getattr(u, "upkeep", "")), lambda n=u.type: self.add_here(n),
                       u.summary() if hasattr(u, "summary") else u.type)
        self.after_idle(lambda: self._reflow(self.cards_all, True))

    def pick_here(self, u):
        self.show_region(keep=u)

    def add_here(self, name):
        r = self.region()
        if r is None:
            return
        p = M.pool_of(self.pools, r)
        if p is None:                                   # no pool yet: one of its own
            p = M.Pool(self._free_name(r))
            self.pools.append(p)
            M.give_regions(self.pools, p, [r])
        u = M.Unit(name)
        p.units.append(u)
        self.fill(None, map_too=False)
        self.show_region(keep=u)
        self.check()

    def own_list(self):
        """The region leaves its pool with a copy of the pool's list: changed from now on for it alone."""
        r = self.region()
        p = M.pool_of(self.pools, r) if r else None
        if p is None or len(p.regions) < 2:
            return
        q = M.Pool(self._free_name(r), units=[M.Unit(u.name, u.exp, u.cost, u.lo, u.hi, u.max, u.initial, u.more)
                                              for u in p.units])
        self.pools.append(q)
        M.give_regions(self.pools, q, [r])
        self.fill(None, map_too=False)
        self.show_region()

    def region_on_map(self):
        r, mv = self.region(), self._map()
        if r is None or mv is None:
            return
        if not mv.v_pick.get():
            mv.v_pick.set(True)
            mv._pick_toggled()
        mv.pick_many(None)
        mv.pick_many([r])

    def _tab_changed(self):
        self._picked_unit = None
        if self.nb.index("current") == 0:
            self.show_region()
        else:
            self.show(map_too=False)

    def _numbers(self, ed):
        self.vars = {}
        row = ttk.Frame(ed)
        row.pack(anchor="w")
        for k, (key, text) in enumerate(FIELDS):         # two rows of three: never cut at the window's edge
            ttk.Label(row, text=text).grid(row=k // 3, column=(k % 3) * 2, sticky="w", padx=(0 if k % 3 == 0 else 14, 4),
                                           pady=2)
            v = tk.StringVar()
            ttk.Entry(row, textvariable=v, width=8).grid(row=k // 3, column=(k % 3) * 2 + 1, sticky="w")
            self.vars[key] = v
        row2 = ttk.Frame(ed)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, wraplength=640, justify="left", text="More words, Medieval II only - start_year, end_year, "
                  "religions { }, crusading, events { }:").pack(anchor="w")
        self.vars["more"] = tk.StringVar()
        e = ttk.Entry(row2, textvariable=self.vars["more"])
        e.pack(fill="x")
        if not self.app._m2():                          # Rome reads no more words: shown greyed, said why
            e.state(["disabled"])
            row2.winfo_children()[0].configure(text="More words (Medieval II only - Rome reads none):")
        self.lbl_words = ttk.Label(ed, wraplength=700, justify="left")
        self.lbl_words.pack(anchor="w", pady=(6, 0))
        self._filling = False
        for v in self.vars.values():
            v.trace_add("write", lambda *_: self.unit_edited())

    # ---- reading ----
    def reload(self, pick=None):
        p = M.path_of(self.mod, self.campaign)
        if p:
            self.mod._cache.pop(p, None)              # read as the file is now (after a write it was the old text)
        self.path, self.pools = M.read(self.mod, self.campaign)
        self.hash = _hash(self.path) if self.path else None
        self.title("%s - %s" % (TITLE, self.campaign))
        self.lbl_title.configure(text="Mercenaries for hire - campaign %s" % self.campaign)
        self.lbl_file.configure(text=self.mod.rel(self.path) if self.path else "no descr_mercenaries.txt")
        self._regions()
        self.fill(pick)
        if hasattr(self, "nb") and self.nb.index("current") == 0:
            self.show_region()

    def fill(self, pick=None, map_too=None):
        self.lb.delete(0, "end")
        for p in self.pools:
            self.lb.insert("end", p.words() + ("  - no region: goes" if not p.regions else ""))
        if pick is not None and pick in self.pools:
            i = self.pools.index(pick)
            self.lb.selection_set(i)
            self.lb.see(i)
        self.show(map_too=pick is not None if map_too is None else map_too)
        self.check()

    def pool(self):
        sel = self.lb.curselection()
        return self.pools[sel[0]] if sel and sel[0] < len(self.pools) else None

    def show(self, map_too=True):
        p = self.pool()
        self.tree.delete(*self.tree.get_children())
        if p is None:
            self.lbl_pool.configure(text="Pick a pool on the left")
            self.lbl_regions.configure(text="")
            self.show_unit()
            return
        names = self._town_names()
        self.lbl_pool.configure(text="Pool %s" % p.name)
        self.lbl_regions.configure(text="Regions (%d): %s" % (len(p.regions), ", ".join(
            "%s (%s)" % (r, names[r]) if names.get(r) and names[r] != r else r for r in p.regions) or "none"))
        for i, u in enumerate(p.units):
            self.tree.insert("", "end", iid=str(i), text=u.name, values=self._row(u))
        self.show_unit()
        if map_too:
            self.show_on_map()

    def _row(self, u):
        try:
            hi, lo = float(u.hi), float(u.lo)
            every = ("%s turns" % M._turns(hi, lo)) if hi > 0 else "never"
        except ValueError:
            every = "?"
        return (u.initial, u.max, "%s - %s" % (u.lo, u.hi), every, u.cost, u.exp, u.more)

    def _town_names(self):
        cm = getattr(self.app, "_cmap", None)
        return {r: i.get("settlement", r) for r, i in cm.info.items()} if cm else {}

    def unit(self):
        if self.nb.index("current") == 0:
            return self._picked_unit
        p, sel = self.pool(), self.tree.selection()
        return p.units[int(sel[0])] if p and sel and int(sel[0]) < len(p.units) else None

    def show_unit(self):
        u = self.unit()
        self._filling = True
        try:
            for key, v in self.vars.items():
                v.set(getattr(u, key) if u else "")
        finally:
            self._filling = False
        self.lbl_words.configure(text=u.words() if u else "Pick a unit (a click on its card, or its line in a pool) to change its numbers.")

    def unit_edited(self):
        u = self.unit()
        if self._filling or u is None:
            return
        for key, v in self.vars.items():
            setattr(u, key, v.get().strip())
        if self.tree.selection():
            self.tree.item(self.tree.selection()[0], values=self._row(u))
        self.lbl_words.configure(text=u.words())
        self.check()

    def check(self):
        why = M.problems(self.mod, self.campaign, [p for p in self.pools if p.regions]) if self.path else []
        self.lbl_problems.configure(text=("Not right in the pools (the game may stumble on it): " + "; ".join(why[:4]) +
                                          (" (and %d more)" % (len(why) - 4) if len(why) > 4 else "")) if why else "")

    # ---- the map ----
    def _map(self):
        mv = getattr(self.app, "map_view", None)
        return mv if mv is not None and mv.winfo_exists() else None

    def selected_regions(self):
        mv = self._map()
        return sorted(mv.picked) if mv is not None else []

    def show_on_map(self):
        """The pool's regions selected on the map (Select switched on): the map's box changes them from there."""
        p, mv = self.pool(), self._map()
        if p is None or mv is None:
            return
        if not mv.v_pick.get():
            mv.v_pick.set(True)
            mv._pick_toggled()
        mv.pick_many(None)
        mv.pick_many(p.regions)

    def take_selection(self, add=False):
        p = self.pool()
        if p is None:
            messagebox.showinfo(TITLE, "Pick a pool on the left first.", parent=self)
            return
        picked = self.selected_regions()
        if not picked:
            messagebox.showinfo(TITLE, "Nothing is selected on the map. Switch Select on (on the map) and drag a box "
                                       "over the regions - Shift + box takes some away.", parent=self)
            return
        want = list(p.regions) + [r for r in picked if r not in p.regions] if add else picked
        self._give(p, want)

    def _give(self, p, want):
        left = M.give_regions(self.pools, p, want)
        if left:
            gone = [q.name for q in self.pools if not q.regions and q is not p]
            messagebox.showinfo(TITLE, "Moved into %s from other pools:\n%s%s" % (
                p.name, "\n".join("- %s (was in %s)" % x for x in left),
                ("\n\nLeft without a region (they go when written): %s" % ", ".join(gone)) if gone else ""),
                parent=self)
        self.fill(p)

    # ---- pools ----
    def new_pool(self, regions=None):
        picked = regions if regions is not None else self.selected_regions()
        if not picked:
            messagebox.showinfo(TITLE, "Select the regions on the map first: switch Select on (on the map) and drag a "
                                       "box over them (Shift + box takes some away).", parent=self)
            return
        name = simpledialog.askstring(TITLE, "The new pool's name (one word - letters, digits and _):",
                                      initialvalue=self._free_name(), parent=self)
        if not name:
            return
        name = name.strip().replace(" ", "_")
        if not M.RE_POOL_NAME.match(name) or name.lower() in {q.name.lower() for q in self.pools}:
            messagebox.showerror(TITLE, "%s: one word of letters, digits and _, not the name of another pool." % name,
                                 parent=self)
            return
        p = M.Pool(name)
        self.pools.append(p)
        self._give(p, list(picked))

    def _free_name(self, region=None):
        have = {q.name.lower() for q in self.pools}
        base = "%s_mercs" % "".join(c if c.isalnum() or c == "_" else "_" for c in region) if region else "my_pool"
        if region and base.lower() not in have:
            return base
        k = 1
        while "%s_%d" % (base, k) in have:
            k += 1
        return "%s_%d" % (base, k)

    def rename(self):
        p = self.pool()
        if p is None:
            return
        name = simpledialog.askstring(TITLE, "New name of the pool %s:" % p.name, initialvalue=p.name, parent=self)
        if not name or name.strip() == p.name:
            return
        name = name.strip().replace(" ", "_")
        if not M.RE_POOL_NAME.match(name) or name.lower() in {q.name.lower() for q in self.pools if q is not p}:
            messagebox.showerror(TITLE, "%s: one word of letters, digits and _, not the name of another pool." % name,
                                 parent=self)
            return
        p.name = name
        self.fill(p)

    def delete_pool(self):
        p = self.pool()
        if p is None:
            return
        if not messagebox.askyesno(TITLE, "Delete the pool %s? Its regions (%s) will have no mercenaries for hire "
                                          "(written with Keep for Apply, then Apply changes)." % (p.name, ", ".join(p.regions) or "none"),
                                   parent=self):
            return
        self.pools.remove(p)
        if p.start is not None:                 # an old pool: kept with no region, so the write takes its lines out
            p.regions = []
            self.pools.append(p)
        self.fill()

    def add_unit(self):
        p = self.pool()
        name = self.v_add.get().strip()
        if p is None or not name:
            messagebox.showinfo(TITLE, "Pick a pool on the left and a unit in the list beside 'Add for hire'.",
                                parent=self)
            return
        p.units.append(M.Unit(name))
        self.show(map_too=False)
        iid = str(len(p.units) - 1)
        self.tree.selection_set(iid)
        self.tree.see(iid)
        self.check()

    def remove_unit(self):
        u = self.unit()
        p = next((q for q in self.pools if u is not None and any(x is u for x in q.units)), None)
        if p is None:
            messagebox.showinfo(TITLE, "Pick a unit first (a click on its card, or its line in the pool's list).",
                                parent=self)
            return
        p.units = [x for x in p.units if x is not u]
        self._picked_unit = None
        self.show(map_too=False)
        if self.nb.index("current") == 0:
            self.show_region()
        self.check()

    # ---- writing ----
    def _plan(self):
        from .plan import Plan
        if not self.path:
            raise ValueError("this campaign has no descr_mercenaries.txt")
        if _hash(self.path) != self.hash:
            raise ValueError("descr_mercenaries.txt was changed since this window read it - it is read again now; "
                             "make your changes again")
        plan = Plan(self.mod, "mercenaries", self.campaign, {})
        M.plan_pools(plan, self.campaign, self.pools)
        return plan

    def _try_plan(self):
        try:
            return self._plan()
        except ValueError as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            if "read again" in str(e):
                self.reload()
            return None

    def preview(self):
        plan = self._try_plan()
        if plan is None:
            return
        if not plan.changed_files():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        self.app.show_text("Mercenaries - every change (nothing written yet)", plan.report())

    def write(self):
        """Keep for Apply: the pools' changes go into the session's list, written by the main window's Apply changes
        with everything else (one write, one Undo)."""
        from .gui_util import keep_for_apply
        try:
            self._plan()
        except ValueError as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            if "read again" in str(e):
                self.reload()
            return False

        def after(bdir):
            from . import log
            log.write("Mercenary pools changed (backup %s)" % bdir)
            if self.winfo_exists():
                self.mod = self.app.mod
                name = self.pool().name if self.pool() else None
                self.reload()
                p = next((q for q in self.pools if q.name == name), None) if name else None
                if p:
                    self.fill(p)
        return keep_for_apply(self, "mercenaries:%s" % self.campaign, "Mercenary pools (%s)" % self.campaign,
                              self._plan, after, TITLE)

    def _unwritten(self):
        """Words of what is neither written nor kept for the write, or '' (the close guard asks before throwing it
        away)."""
        if not self.path:
            return ""
        from .gui_util import kept_or_not
        return kept_or_not(self.app, "mercenaries:%s" % self.campaign, self._plan)

    def _forget(self):
        if getattr(self.app, "_merc_window", None) is self:
            self.app._merc_window = None

    def close(self):
        from .gui_util import close_guard                 # never closes over unwritten changes silently
        close_guard(self, TITLE, self._unwritten, self.write, after=self._forget)()


def open_mercenaries(app, region=None, new_from=None):
    """One window: opened again it comes to the front; region picks that region's pool, new_from makes a pool of
    those regions."""
    if not app.mod:
        messagebox.showinfo(TITLE, "Load a mod first.")
        return None
    w = getattr(app, "_merc_window", None)
    if w is None or not w.winfo_exists() or w.mod is not app.mod or w.campaign != app.v_campaign.get():
        if w is not None and w.winfo_exists():
            w.destroy()
        w = app._merc_window = MercWindow(app)
        if not region:
            w.nb.select(1)                      # from the work bar: the pools first
    w.lift()
    if not w.path:
        messagebox.showinfo(TITLE, "This campaign has no descr_mercenaries.txt - nothing to hire.", parent=w)
        return w
    if region:                                  # the region's own list, the garrison way (it says if it has none)
        w.pick_region(region)
    elif new_from:
        w.nb.select(1)
        w.new_pool(list(new_from))
    return w
