"""Mercenaries... (the work bar; a right click on the map: 'Mercenaries for hire in <region>...', and with Select on:
'New mercenary pool from the selected regions...'): the campaign's mercenary pools in one window.

Left: the pools. A pool picked here is selected on the map (Select switches on, its regions show yellow), so its
regions can be changed the map's own way - a box adds, Shift + box takes away - and 'Take the map's selection'
gives the pool exactly what is selected. 'New pool from the map's selection' makes a pool of the selected regions.
Right: the pool's units with their numbers in plain words; a picked unit's numbers are changed in the fields under
the list. Nothing is written before 'Write it in' (a backup first; Tools > Restore a backup undoes it)."""

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
        ttk.Button(bar, text="Write it in", command=self.write).pack(side="right", padx=(0, 6))
        ttk.Button(bar, text="Show every change...", command=self.preview).pack(side="right", padx=(0, 6))
        top = ttk.Frame(self, padding=(10, 10, 10, 0))
        top.pack(fill="x")
        self.lbl_title = ttk.Label(top, font=("", 12, "bold"))
        self.lbl_title.pack(anchor="w")
        self.lbl_file = ttk.Label(top, foreground=theme.palette()["muted"])
        self.lbl_file.pack(anchor="w")
        ttk.Label(top, wraplength=1000, justify="left", text=(
            "A pool = regions that share one list of mercenaries for hire. Pick a pool: its regions are selected on "
            "the map (Select). Change the selection the map's way - a box adds, Shift + box takes away - then 'Take "
            "the map's selection'. A region stands in one pool only: given to a pool it leaves its old one.")
                  ).pack(anchor="w", pady=(2, 6))
        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10)
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
        for text, fn in (("New pool from the map's selection", self.new_pool), ("Rename...", self.rename),
                         ("Delete this pool", self.delete_pool)):
            ttk.Button(left, text=text, command=fn).pack(fill="x", pady=(4, 0))
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
        ed = ttk.LabelFrame(right, text="The picked unit", padding=8)
        ed.pack(fill="x", pady=(8, 0))
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
        ttk.Entry(row2, textvariable=self.vars["more"]).pack(fill="x")
        self.lbl_words = ttk.Label(ed, wraplength=700, justify="left")
        self.lbl_words.pack(anchor="w", pady=(6, 0))
        self._filling = False
        for v in self.vars.values():
            v.trace_add("write", lambda *_: self.unit_edited())

    # ---- reading ----
    def reload(self, pick=None):
        self.path, self.pools = M.read(self.mod, self.campaign)
        self.hash = _hash(self.path) if self.path else None
        self.title("%s - %s" % (TITLE, self.campaign))
        self.lbl_title.configure(text="Mercenaries for hire - campaign %s" % self.campaign)
        self.lbl_file.configure(text=self.mod.rel(self.path) if self.path else "no descr_mercenaries.txt")
        self.fill(pick)

    def fill(self, pick=None):
        self.lb.delete(0, "end")
        for p in self.pools:
            self.lb.insert("end", p.words() + ("  - no region: goes" if not p.regions else ""))
        if pick is not None and pick in self.pools:
            i = self.pools.index(pick)
            self.lb.selection_set(i)
            self.lb.see(i)
        self.show(map_too=pick is not None)
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
        self.lbl_words.configure(text=u.words() if u else "Pick a unit in the list to change its numbers.")

    def unit_edited(self):
        u = self.unit()
        if self._filling or u is None:
            return
        for key, v in self.vars.items():
            setattr(u, key, v.get().strip())
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

    def _free_name(self):
        have = {q.name.lower() for q in self.pools}
        k = 1
        while "my_pool_%d" % k in have:
            k += 1
        return "my_pool_%d" % k

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
                                          "(written with 'Write it in')." % (p.name, ", ".join(p.regions) or "none"),
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
        p, u = self.pool(), self.unit()
        if p is None or u is None:
            return
        p.units.remove(u)
        self.show(map_too=False)
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
        plan = self._try_plan()
        if plan is None:
            return
        if not plan.changed_files():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        if not messagebox.askyesno(TITLE, "%s\n\nWrite it? A backup is made first (Tools > Restore a backup undoes "
                                          "it)." % plan.report()[:1500], parent=self):
            return
        bdir = plan.apply()
        from . import log
        log.write("Mercenary pools changed (backup %s)\n%s" % (bdir, plan.report()))
        self.app.status.set("Mercenaries written (backup %s)." % bdir)
        name = self.pool().name if self.pool() else None
        self.reload()
        if name:
            p = next((q for q in self.pools if q.name == name), None)
            if p:
                self.fill(p)

    def close(self):
        if getattr(self.app, "_merc_window", None) is self:
            self.app._merc_window = None
        self.destroy()


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
    w.lift()
    if not w.path:
        messagebox.showinfo(TITLE, "This campaign has no descr_mercenaries.txt - nothing to hire.", parent=w)
        return w
    if region:
        p = M.pool_of(w.pools, region)
        if p is None:
            if messagebox.askyesno(TITLE, "%s is in no pool - nobody is for hire there. Make a new pool of it?"
                                   % region, parent=w):
                w.new_pool([region])
        else:
            w.fill(p)
    elif new_from:
        w.new_pool(list(new_from))
    return w
