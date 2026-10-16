"""Rebels... (the work bar beside Mercenaries; the map's right click: 'Rebels in <region>...', with Select on: 'Rebel
type for the N selected region(s)...'): the rebel types of descr_rebel_factions.txt in one window, two tabs (report
#252: 'a Rebels tab like the Mercenaries one').

'Rebel types': the types left; right the picked one - the name players read (rebel_faction_descr.txt), its kind
(category), chance, and the units the game raises for it (a click on 'Add' adds the unit picked, a right click takes a
line out). New type / Copy / Rename beside the list, Delete set apart; a type renamed or deleted takes its regions along
(rebels.plan_types).

'Regions': every region with its owner and rebel type, a faction filter; the rows picked (or the map's selection) get
the type picked under the table at once. A change waits for Apply changes in the main
window (a backup first; Restore undoes it)."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import rebels as RB
from . import theme
from .gui_util import AutoKeep, ShortHint, ask, Page

TITLE = "Rebels"
ALL = "every faction"


class RebelsWindow(AutoKeep, Page):
    _ak_fields = ('types', 'removed', 'given')

    def __init__(self, app):
        super().__init__(app)
        self.app, self.mod, self.campaign = app, app.mod, app.v_campaign.get()
        self.transient(app)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d" % (min(1080, sw - 40), min(660, sh - 100)))
        self.minsize(min(640, sw - 40), min(420, sh - 100))
        self.protocol("WM_DELETE_WINDOW", self.close)
        from .units import read_units
        edu = self.mod.file("edu")
        units = read_units(self.mod.load(edu)) if edu else []
        # the rebels' own units first (the game raises units the rebels own), the rest after
        slave = [u.type for u in units if "slave" in [o.lower() for o in getattr(u, "ownership", []) or []]]
        self.unit_names = slave + sorted(u.type for u in units if u.type not in slave)
        self._build()
        self._ak_busy = True
        self.reload()
        self.ak_start()

    # ---- the window ----
    def _build(self):
        bar = ttk.Frame(self, padding=(10, 4, 10, 10))
        bar.pack(side="bottom", fill="x")
        self.lbl_problems = ttk.Label(bar, foreground=theme.ink("#c00000"), wraplength=700, justify="left")
        self.lbl_problems.pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        top = ttk.Frame(self, padding=(10, 10, 10, 0))
        top.pack(fill="x")
        self.lbl_title = ttk.Label(top, font=("", 12, "bold"))
        self.lbl_title.pack(anchor="w")
        self.lbl_file = ttk.Label(top, foreground=theme.palette()["muted"])
        self.lbl_file.pack(anchor="w")
        ShortHint(top, text=(
            "Who rises when a region revolts. Each region names a rebel type (descr_regions.txt); a type lists the "
            "units the game raises for it (descr_rebel_factions.txt) and the name players read "
            "(rebel_faction_descr.txt). Brigands and pirates are types too. A type renamed or deleted takes its "
            "regions along. A change waits for Apply changes in the main window.")).pack(
            anchor="w", fill="x", pady=(2, 6))
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10)
        self._types_tab()
        self._regions_tab()

    def _types_tab(self):
        body = ttk.PanedWindow(self.nb, orient="horizontal")
        self.nb.add(body, text="Rebel types")
        left = ttk.Frame(body)
        body.add(left, weight=1)
        ttk.Label(left, text="Rebel types", font=("", 10, "bold")).pack(anchor="w")
        self.v_find = tk.StringVar()
        fe = ttk.Entry(left, textvariable=self.v_find)
        fe.pack(fill="x", pady=(2, 4))
        self.v_find.trace_add("write", lambda *_: self.fill())
        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True)
        self.lb = tk.Listbox(lf, exportselection=False, width=34, activestyle="none")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.show())
        for text, fn in (("New type...", self.new_type), ("Copy this type...", self.copy_type),
                         ("Rename...", self.rename)):
            ttk.Button(left, text=text, command=fn).pack(fill="x", pady=(4, 0))
        # destructive: set apart from the others
        ttk.Button(left, text="Delete this type...", command=self.delete_type).pack(fill="x", pady=(16, 0))
        right = ttk.Frame(body, padding=(10, 0, 0, 0))
        body.add(right, weight=3)
        self.lbl_type = ttk.Label(right, font=("", 10, "bold"))
        self.lbl_type.pack(anchor="w")
        form = ttk.Frame(right)
        form.pack(anchor="w", fill="x", pady=(4, 6))
        self.vars = {}
        for r, (key, label) in enumerate((("words", "Name players read"), ("category", "Kind (category)"),
                                          ("chance", "Chance"), ("description", "Text key"))):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=2)
            v = self.vars[key] = tk.StringVar()
            if key == "category":
                w = ttk.Combobox(form, textvariable=v, values=list(RB.CATEGORIES), width=30)
            else:
                w = ttk.Entry(form, textvariable=v, width=40 if key == "words" else 32)
            w.grid(row=r, column=1, sticky="w", padx=6)
            v.trace_add("write", lambda *_, k=key: self.field_edited(k))
        self.lbl_about = ttk.Label(form, foreground=theme.palette()["muted"], wraplength=360, justify="left",
                                   text="peasant_revolt: a region that revolts; brigands / pirates: bands that "
                                        "appear on land / at sea; chance: how likely they rise (a bigger number, "
                                        "more often)")
        self.lbl_about.grid(row=0, column=2, rowspan=4, sticky="nw", padx=(12, 0))
        self.lbl_regions = ttk.Label(right, wraplength=700, justify="left")
        self.lbl_regions.pack(anchor="w", fill="x")
        ttk.Button(right, text="Show its regions on the map", command=self.type_on_map).pack(anchor="w", pady=(4, 8))
        ttk.Label(right, text="The units the game raises for it", font=("", 10, "bold")).pack(anchor="w")
        uf = ttk.Frame(right)
        uf.pack(fill="both", expand=True)
        self.lb_units = tk.Listbox(uf, exportselection=False, activestyle="none", height=8)
        us = ttk.Scrollbar(uf, orient="vertical", command=self.lb_units.yview)
        self.lb_units.configure(yscrollcommand=us.set)
        us.pack(side="right", fill="y")
        self.lb_units.pack(fill="both", expand=True)
        self.lb_units.bind("<Button-3>", self._unit_take)
        add = ttk.Frame(right)
        add.pack(fill="x", pady=(6, 0))
        ttk.Label(add, text="Add a unit:").pack(side="left")
        self.v_add = tk.StringVar()
        ttk.Combobox(add, textvariable=self.v_add, width=36, values=self.unit_names).pack(side="left", padx=6)
        ttk.Button(add, text="Add", command=self.add_unit).pack(side="left")
        ttk.Label(add, text="(right click a unit: take it out; the same unit twice = raised more often)",
                  foreground=theme.palette()["muted"]).pack(side="left", padx=(8, 0))

    def _regions_tab(self):
        tab = ttk.Frame(self.nb, padding=(0, 6, 0, 0))
        self.nb.add(tab, text="Regions")
        row = ttk.Frame(tab)
        row.pack(fill="x")
        ttk.Label(row, text="Show the regions of").pack(side="left")
        self.v_owner = tk.StringVar(value=ALL)
        self.cb_owner = ttk.Combobox(row, textvariable=self.v_owner, state="readonly", width=28)
        self.cb_owner.pack(side="left", padx=6)
        self.cb_owner.bind("<<ComboboxSelected>>", lambda e: self.fill_regions())
        ttk.Button(row, text="Pick the map's selection", command=self.take_map_selection).pack(side="left", padx=6)
        ttk.Button(row, text="Show the picked on the map", command=self.regions_on_map).pack(side="left")
        tf = ttk.Frame(tab)
        tf.pack(fill="both", expand=True, pady=(6, 0))
        cols = (("town", "town", 160), ("owner", "owner", 150), ("type", "rebel type", 200))
        self.tree = ttk.Treeview(tf, columns=[c for c, _, _ in cols], selectmode="extended")
        self.tree.heading("#0", text="region")
        self.tree.column("#0", width=180, stretch=True)
        for c, text, w in cols:
            self.tree.heading(c, text=text)
            self.tree.column(c, width=w, stretch=True)
        ts = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ts.set)
        ts.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        give = ttk.Frame(tab)
        give.pack(fill="x", pady=(6, 0))
        ttk.Label(give, text="Give the picked region(s) the rebel type").pack(side="left")
        self.v_give = tk.StringVar()
        self.cb_give = ttk.Combobox(give, textvariable=self.v_give, state="readonly", width=30)
        self.cb_give.pack(side="left", padx=6)
        ttk.Button(give, text="Give it", command=self.give_type).pack(side="left")
        ttk.Label(give, text="(Ctrl / Shift + click picks many)", foreground=theme.palette()["muted"]).pack(
            side="left", padx=(8, 0))

    # ---- reading ----
    def reload(self, pick=None):
        p = RB.path_of(self.mod)
        if p:
            self.mod._cache.pop(p, None)
        self.path, self.types = RB.read(self.mod)
        self.removed = []                             # types taken out (their regions must get another)
        self.given = {}                               # {region: rebel type} picked on the Regions tab
        self.title("%s - %s" % (TITLE, self.campaign))
        self.lbl_title.configure(text="Rebels - campaign %s" % self.campaign)
        self.lbl_file.configure(text=self.mod.rel(self.path) if self.path else "no %s" % RB.FILE)
        self.regions = RB.regions_of(self.mod, self.campaign)
        self.fill(pick)
        self._owners()
        self.fill_regions()

    def _town_names(self):
        cm = getattr(self.app, "_cmap", None)
        return {r: i.get("settlement", r) for r, i in cm.info.items()} if cm else {
            r: v.get("settlement", r) for r, v in self.mod.regions(self.campaign).items()}

    def _owner_of(self):
        try:
            return self.app.town_owners()
        except Exception:
            return {}

    def region_type(self, region):
        """The region's rebel type as the write will leave it: picked here, else the file's - renamed with its type."""
        if region in self.given:
            return self.given[region]
        t = self.regions.get(region, "")
        return next((x.name for x in self.types if x.old and x.old[0] == t), t)

    # ---- the types ----
    def shown_types(self):
        q = self.v_find.get().strip().lower()
        return [t for t in self.types if not q or q in t.name.lower() or q in (self._words(t) or "").lower()]

    def _words(self, t):
        return t.words if t.words is not None else getattr(t, "words_now", "")

    def fill(self, pick=None):
        cur = pick or self.current()
        self.lb.delete(0, "end")
        self._shown = self.shown_types()
        for t in self._shown:
            n = sum(1 for r in self.regions if self.region_type(r) == t.name)
            self.lb.insert("end", "%s%s - %d unit(s)%s%s" % (
                t.name, (" (%s)" % self._words(t)) if self._words(t) and self._words(t) != t.name else "",
                len(t.units), ", %d region(s)" % n if n else "", "  *" if t.changed() else ""))
        if cur in self._shown:
            i = self._shown.index(cur)
            self.lb.selection_set(i)
            self.lb.see(i)
        self.cb_give.configure(values=[t.name for t in self.types])
        self.show()
        self.check()

    def current(self):
        sel = self.lb.curselection()
        shown = getattr(self, "_shown", [])
        return shown[sel[0]] if sel and sel[0] < len(shown) else None

    def show(self):
        t = self.current()
        self._filling = True
        try:
            for k, v in self.vars.items():
                v.set("" if t is None else (self._words(t) if k == "words" else getattr(t, k)))
        finally:
            self._filling = False
        self.lb_units.delete(0, "end")
        if t is None:
            self.lbl_type.configure(text="Pick a rebel type on the left")
            self.lbl_regions.configure(text="")
            return
        self.lbl_type.configure(text="Rebel type %s" % t.name)
        names = self._town_names()
        regs = sorted(r for r in self.regions if self.region_type(r) == t.name)
        self.lbl_regions.configure(text="Regions of this type (%d): %s" % (len(regs), ", ".join(
            names.get(r) or r for r in regs[:20]) + (" ..." if len(regs) > 20 else "") if regs else "none"))
        for u in t.units:
            self.lb_units.insert("end", u)

    def field_edited(self, key):
        t = self.current()
        if getattr(self, "_filling", False) or t is None:
            return
        val = self.vars[key].get()
        if key == "words":
            t.words = val
        else:
            setattr(t, key, val.strip())
        self.check()

    def add_unit(self):
        t, name = self.current(), self.v_add.get().strip()
        if t is None or not name:
            messagebox.showinfo(TITLE, "Pick a rebel type on the left and a unit beside 'Add a unit'.", parent=self)
            return
        t.units.append(name)
        self.show()
        self.lb_units.see("end")
        self.check()

    def _unit_take(self, e):
        t = self.current()
        i = self.lb_units.nearest(e.y)
        if t is None or i < 0 or i >= len(t.units):
            return
        del t.units[i]
        self.show()
        self.check()

    def _ask_name(self, text, initial=""):
        name = simpledialog.askstring(TITLE, text, initialvalue=initial, parent=self)
        if not name:
            return None
        name = name.strip().replace(" ", "_")
        if not RB.RE_NAME.match(name) or name.lower() in {t.name.lower() for t in self.types}:
            messagebox.showerror(TITLE, "%s: one word of letters, digits, _ and -, not the name of another rebel "
                                        "type." % name, parent=self)
            return None
        return name

    def new_type(self, copy_of=None):
        src = copy_of
        name = self._ask_name("The new rebel type's name (one word):", (src.name + "_2") if src else "My_Rebels")
        if not name:
            return
        t = RB.RebelType(name, src.category if src else "peasant_revolt", src.chance if src else "3",
                         name, list(src.units) if src else [])
        t.words = name.replace("_", " ")
        self.types.append(t)
        self.v_find.set("")
        self.fill(t)

    def copy_type(self):
        t = self.current()
        if t is None:
            messagebox.showinfo(TITLE, "Pick the rebel type to copy on the left.", parent=self)
            return
        self.new_type(copy_of=t)

    def rename(self):
        t = self.current()
        if t is None:
            return
        name = self._ask_name("New name of the rebel type %s (its regions follow):" % t.name, t.name)
        if not name:
            return
        old = t.name
        for r, v in list(self.given.items()):
            if v == old:
                self.given[r] = name
        if t.description == old:                     # the text key follows the name when it was the name
            t.description = name
            if t.words is None:
                t.words = getattr(t, "words_now", "") or name.replace("_", " ")
        t.name = name
        self.fill(t)
        self.fill_regions()

    def delete_type(self):
        t = self.current()
        if t is None:
            return
        regs = sorted(r for r in self.regions if self.region_type(r) == t.name)
        others = [x.name for x in self.types if x is not t]
        if regs and not others:
            messagebox.showinfo(TITLE, "%s is the only rebel type and %d region(s) name it - make another type "
                                       "first." % (t.name, len(regs)), parent=self)
            return
        to = None
        if regs:
            to = self._pick_type("%d region(s) name %s: %s.\n\nWhich rebel type do they get instead?" % (
                len(regs), t.name, ", ".join(regs[:12]) + (" ..." if len(regs) > 12 else "")), others)
            if not to:
                return
        elif not ask(TITLE, "Delete the rebel type %s? (written with Apply changes)" % t.name,
                     parent=self, yes="Delete the type", no="Keep it", danger=True):
            return
        for r in regs:
            self.given[r] = to
        self.types.remove(t)
        self.removed.append(t)
        self.fill()
        self.fill_regions()

    def _pick_type(self, text, names):
        """A small question with a list: the rebel type picked, or None."""
        w = tk.Toplevel(self)
        w.title(TITLE)
        w.transient(self.winfo_toplevel())
        w.grab_set()
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=text, wraplength=420, justify="left").pack(anchor="w")
        v = tk.StringVar(value=names[0])
        ttk.Combobox(f, textvariable=v, values=names, state="readonly", width=34).pack(anchor="w", pady=8)
        got = []
        b = ttk.Frame(f)
        b.pack(anchor="e")
        ttk.Button(b, text="Delete the type, give them this one", command=lambda: (got.append(v.get()),
                                                                                    w.destroy())).pack(side="left")
        ttk.Button(b, text="Keep it", command=w.destroy).pack(side="left", padx=(6, 0))
        w.wait_window()
        return got[0] if got else None

    # ---- the regions ----
    def _owners(self):
        owners = self._owner_of()
        facs = sorted({o for o in owners.values() if o})
        self.cb_owner.configure(values=[ALL] + facs)

    def fill_regions(self, pick=()):
        self.tree.delete(*self.tree.get_children())
        names, owners, want = self._town_names(), self._owner_of(), self.v_owner.get()
        for r in sorted(self.regions, key=lambda x: (names.get(x) or x).lower()):
            o = owners.get(r, "")
            if want != ALL and o != want:
                continue
            t = self.region_type(r)
            self.tree.insert("", "end", iid=r, text=r, values=(names.get(r, ""), "rebels" if o == "slave" else o,
                                                               t + ("  *" if r in self.given else "")))
        sel = [r for r in pick if self.tree.exists(r)]
        if sel:
            self.tree.selection_set(sel)
            self.tree.see(sel[0])

    def picked_regions(self):
        return list(self.tree.selection())

    def give_type(self):
        regs, t = self.picked_regions(), self.v_give.get()
        if not regs or not t:
            messagebox.showinfo(TITLE, "Pick the regions in the table (or 'Pick the map's selection') and a rebel "
                                       "type beside 'Give it'.", parent=self)
            return
        for r in regs:
            if self.regions.get(r) == t:
                self.given.pop(r, None)
            else:
                self.given[r] = t
        self.fill_regions(regs)
        self.fill(self.current())
        self.ak_changed()

    def pick_regions(self, regions):
        """These regions picked on the Regions tab (the map's right click)."""
        self.v_owner.set(ALL)
        self.nb.select(1)
        self.fill_regions(list(regions))

    def _map(self):
        mv = getattr(self.app, "map_view", None)
        return mv if mv is not None and mv.winfo_exists() else None

    def take_map_selection(self):
        mv = self._map()
        picked = sorted(mv.picked) if mv is not None else []
        if not picked:
            messagebox.showinfo(TITLE, "Nothing is selected on the map. Switch Select on (on the map) and drag a box "
                                       "over the regions - Shift + box takes some away.", parent=self)
            return
        self.pick_regions(picked)

    def _show_on_map(self, regions):
        mv = self._map()
        if mv is None:
            return
        if not mv.v_pick.get():
            mv.v_pick.set(True)
            mv._pick_toggled()
        mv.pick_many(None)
        mv.pick_many(list(regions))

    def regions_on_map(self):
        self._show_on_map(self.picked_regions())

    def type_on_map(self):
        t = self.current()
        if t is not None:
            self._show_on_map([r for r in self.regions if self.region_type(r) == t.name])

    # ---- checking and writing ----
    def check(self):
        why = RB.problems(self.mod, self.types) if self.path else []
        self.lbl_problems.configure(text=("Not right yet (the game would stumble on it): " + "; ".join(why[:4]) + (
            " (and %d more)" % (len(why) - 4) if len(why) > 4 else "")) if why else "")
        self.ak_changed()

    def _plan(self):
        from .plan import Plan
        if not self.path:
            raise ValueError("this mod has no %s" % RB.FILE)
        plan = Plan(self.mod, "rebels", self.campaign, {})
        RB.plan_types(plan, self.campaign, self.types, given=self.given)
        return plan

    # ---- kept by itself (gui_util.AutoKeep) ----
    def _ak_key(self):
        return "rebels:%s" % self.campaign if self.path else None

    def _ak_label(self):
        return "Rebel types (%s)" % self.campaign

    def _ak_plan(self):
        return self._plan()

    def ak_refresh(self):
        name = self.current().name if self.current() else None
        self.fill(next((x for x in self.types if x.name == name), None))

    @property
    def _ak_after(self):
        def after(bdir):
            from . import log
            log.write("Rebel types changed (backup %s)" % bdir)
            if self.winfo_exists():
                self.ak_reload()
        return after

    def ak_reload(self):
        self.mod = self.app.mod
        name = self.current().name if self.current() else None
        self._ak_busy = True
        self.reload()
        x = next((q for q in self.types if q.name == name), None) if name else None
        if x:
            self.fill(x)
        self.ak_start()

    def _forget(self):
        if getattr(self.app, "_rebels_window", None) is self:
            self.app._rebels_window = None

    def close(self):
        self.ak_close()
        self._forget()
        self.destroy()


def open_rebels(app, regions=None):
    """Rebels: a work of the main window (App.show_page); regions: those picked on its Regions tab."""
    w = app.show_page("rebels")
    if isinstance(w, RebelsWindow) and w.path and regions:
        w.pick_regions(regions)
    return w


def make_page(app):
    if not app.mod:
        return None
    return RebelsWindow(app)
