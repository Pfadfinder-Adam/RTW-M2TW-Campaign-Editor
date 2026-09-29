"""The Unit editor and Building editor tabs: pick a unit (a building chain) on
the left, change any line of its block on the right, and import its pictures -
the tool puts them where the game reads them, in the mod's own format."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import editors as E
from . import theme, unitattrs
from .moddata import ModData
from .plan import Plan

CHANGED = "#fff2b3"          # a field changed and not written yet
REMOVED = "#f4c7c3"          # a line to be removed
ADDED = "#d9f2d0"            # a line to be added
SMALL = dict(padx=3, pady=0, bd=1, font=("", 8), cursor="hand2")


class RecordEditor(ttk.Frame):
    """kind 'unit' (export_descr_unit.txt) or 'building' (export_descr_buildings.txt)."""

    def __init__(self, master, app, kind):
        super().__init__(master, padding=4)
        self.app, self.kind = app, kind
        self.mod = None
        self.blocks, self.changes, self.imports = [], {}, []    # changes {line: value}; imports [(src, targets, size)]
        # lines added [{'at': block's first line, 'block', 'place', 'level', 'key', 'text', 'own': [factions]}]
        # and removed {line}; both placed on Apply, after the changed fields
        self.adds, self.removes = [], set()
        self.current = None
        side = ttk.Frame(self)
        side.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(side, text="Units" if kind == "unit" else "Building chains", font=("", 10, "bold")).pack(anchor="w")
        self.v_find = tk.StringVar()
        e = ttk.Entry(side, textvariable=self.v_find, width=32)
        e.pack(fill="x", pady=(2, 4))
        e.bind("<KeyRelease>", lambda ev: self.fill_list())
        fl = ttk.Frame(side)
        fl.pack(fill="x", pady=(0, 4))
        ttk.Label(fl, text="Show", width=5).grid(row=0, column=0, sticky="w")
        self.v_show = tk.StringVar(value="all")
        self.cb_show = ttk.Combobox(fl, textvariable=self.v_show, values=["all"], state="readonly", width=26)
        self.cb_show.grid(row=0, column=1, sticky="we")
        self.cb_show.bind("<<ComboboxSelected>>", lambda ev: self.fill_list())
        ttk.Label(fl, text="Sort", width=5).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.v_sort = tk.StringVar(value="file order")
        sorts = ["file order", "name", "owner", "category", "class"] if kind == "unit" else \
            ["file order", "name", "who may build", "type"]
        ttk.Combobox(fl, textvariable=self.v_sort, values=sorts, state="readonly", width=26).grid(
            row=1, column=1, sticky="we", pady=(2, 0))
        fl.winfo_children()[-1].bind("<<ComboboxSelected>>", lambda ev: self.fill_list())
        fl.columnconfigure(1, weight=1)
        self.facets = {}
        self.lb = tk.Listbox(side, width=34, exportselection=False)
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda ev: self.show())
        self.lbl_count = ttk.Label(side, text="", foreground="#666")
        self.lbl_count.pack(anchor="w")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)
        head = ttk.Frame(right)
        head.pack(fill="x")
        self.title = ttk.Label(head, text="Load a mod, then pick one on the left", font=("", 11, "bold"))
        self.title.pack(side="left")
        ttk.Button(head, text="Undo all changes here", command=self.reset).pack(side="right")
        ttk.Button(head, text="Copy as new %s..." % ("unit" if kind == "unit" else "building"),
                   command=self.copy_dialog).pack(side="right", padx=6)
        ttk.Button(head, text="Add line...", command=self.add_dialog).pack(side="right")
        if kind == "unit":
            # packs: units taken out with everything they need, and put into another mod
            ttk.Button(head, text="Import pack...", command=self.import_pack).pack(side="right", padx=(0, 12))
            ttk.Button(head, text="Export pack...", command=self.export_pack).pack(side="right", padx=4)
        from .gui_util import first
        first(*head.pack_slaves()[1:][::-1])       # the buttons keep their room; the title is the one cut
        self.copy_ops = []                   # [(source, new name, details)] written on Apply
        self.pics = ttk.LabelFrame(right, text="Pictures", padding=6)
        self.pics.pack(fill="x", pady=(6, 6))
        self.links = ttk.LabelFrame(right, text="Tied to it (kept in step when you change it)", padding=(6, 2))
        self.links.pack(fill="x", pady=(0, 6))
        self.lbl_links = ttk.Label(self.links, text="", justify="left", foreground="#333", wraplength=820)
        self.lbl_links.pack(anchor="w")
        ttk.Label(right, text="Every line of the block: the key on the left, what follows it on the right. "
                              "Changed fields turn yellow, lines to add green, lines to remove red (x on the left); "
                              "Preview, then Apply writes them (with a backup).",
                  foreground="#555", wraplength=900, justify="left").pack(anchor="w")
        box = ttk.Frame(right)
        box.pack(fill="both", expand=True)
        canvas = tk.Canvas(box, highlightthickness=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        self.form = ttk.Frame(canvas)
        self.form.bind("<Configure>", lambda ev: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Enter>", lambda ev: canvas.bind_all("<MouseWheel>",
                    lambda x: canvas.yview_scroll(int(-x.delta / 120), "units")))
        canvas.bind("<Leave>", lambda ev: canvas.unbind_all("<MouseWheel>"))
        self._photos = []

    # ---- data ----
    def path(self):
        return self.mod.file("edu" if self.kind == "unit" else "edb") if self.mod else None

    def load(self, mod):
        self.mod = mod
        self.changes, self.imports, self.current, self.copy_ops = {}, [], None, []
        self.adds, self.removes = [], set()
        self._recruits = self._required = self._limits = None      # read from the file when first asked
        p = self.path()
        self._sig = self._signature()
        if not p:
            self.blocks = []
        else:
            f = mod.load(p)
            self.blocks = E.unit_blocks(f) if self.kind == "unit" else E.building_blocks(f)
        self._fill_filters()
        self.fill_list()
        for w in self.form.winfo_children():
            w.destroy()
        for w in self.pics.winfo_children():
            w.destroy()
        self.title.configure(text="Pick one on the left" if self.blocks else "No %s in this mod" % (
            "export_descr_unit.txt" if self.kind == "unit" else "export_descr_buildings.txt"))

    def _fill_filters(self):
        """The Show list: by owner (faction or culture), by kind, mercenaries apart."""
        self.facets = {}
        if not self.blocks:
            self.cb_show["values"] = ["all"]
            self.v_show.set("all")
            return
        f = self.mod.load(self.path())
        for blk in self.blocks:
            try:
                self.facets[blk[1]] = E.block_facets(f, self.kind, blk)
            except Exception:                     # a broken block is still listed, only not sorted
                self.facets[blk[1]] = {}
        facs = self.mod.factions()
        cultures = sorted({c for _, c in facs if c})
        if self.kind == "unit":
            vals = ["all", "mercenaries only", "no mercenaries", "general's units"]
            vals += ["faction: %s" % n for n, _ in facs]
            vals += ["culture: %s" % c for c in cultures]
            vals += ["category: %s" % c for c in sorted({x.get("category") for x in self.facets.values()} - {"", None})]
            vals += ["class: %s" % c for c in sorted({x.get("class") for x in self.facets.values()} - {"", None})]
        else:
            vals = ["all", "recruit units", "no recruiting"]
            vals += ["type: %s" % g for g, _ in E.CHAIN_GROUPS + (("other", ()),)]
            vals += ["faction: %s" % n for n, _ in facs]
            vals += ["culture: %s" % c for c in cultures]
        self.cb_show["values"] = vals
        if self.v_show.get() not in vals:
            self.v_show.set("all")
        self._cultures = dict(facs)

    def _passes(self, blk):
        want = self.v_show.get()
        if want == "all":
            return True
        fc = self.facets.get(blk[1]) or {}
        kind, _, what = want.partition(": ")
        if self.kind == "unit":
            if want == "mercenaries only":
                return fc.get("mercenary", False)
            if want == "no mercenaries":
                return not fc.get("mercenary", False)
            if want == "general's units":
                return fc.get("general", False)
            owners = fc.get("owners", [])
            if kind == "faction":
                c = self._cultures.get(what)
                return what in owners or (c and c in owners) or "all" in owners
            if kind == "culture":
                return what in owners or "all" in owners
            return fc.get(kind) == what
        if want == "recruit units":
            return fc.get("recruits", False)
        if want == "no recruiting":
            return not fc.get("recruits", True)
        if kind == "type":
            return fc.get("group") == what
        facs = fc.get("factions")
        if facs is None:
            return True                               # every faction may build it
        if kind == "faction":
            c = self._cultures.get(what)
            return what in facs or (c and c in facs) or "all" in facs
        return what in facs or "all" in facs

    def _sort_key(self, blk):
        how = self.v_sort.get()
        fc = self.facets.get(blk[1]) or {}
        name = blk[0].lower()
        if how == "name":
            return (name,)
        if how == "owner":
            return (", ".join(fc.get("owners", [])), name)
        if how in ("category", "class"):
            return (fc.get(how, ""), name)
        if how == "who may build":
            facs = fc.get("factions")
            return ("everyone" if facs is None else ", ".join(facs), name)
        if how == "type":
            return (fc.get("group", ""), name)
        return (blk[1],)

    def fill_list(self):
        q = self.v_find.get().strip().lower()
        self.shown = [b for b in self.blocks if (not q or q in b[0].lower()) and self._passes(b)]
        if self.v_sort.get() != "file order":
            self.shown.sort(key=self._sort_key)
        self.lb.delete(0, "end")
        for name, a, b in self.shown:
            mark = " *" if any(a <= ln < b for ln in list(self.changes) + list(self.removes)) or \
                any(op["at"] == a for op in self.adds) else ""
            key = self._sort_key((name, a, b))
            note = "   [%s]" % (key[0] or "-") if self.v_sort.get() not in ("file order", "name") else ""
            self.lb.insert("end", name + mark + note)
        for src, new, _ in self.copy_ops:
            self.lb.insert("end", "%s  (new, from %s - on Apply)" % (new, src))
        self.lbl_count.configure(text="%d of %d" % (len(self.shown), len(self.blocks)))

    def show(self):
        sel = self.lb.curselection()
        if not sel or sel[0] >= len(self.shown):
            return
        self.current = self.shown[sel[0]]
        name, a, b = self.current
        f = self.mod.load(self.path())
        self.fields = E.fields(f, a, b)
        self.tree = E.chain_tree(f, a, b) if self.kind == "building" else None
        self.title.configure(text=("unit " if self.kind == "unit" else "building ") + name)
        for w in self.form.winfo_children():
            w.destroy()
        # the lines to add, each shown after the field it will follow
        pending = []
        for n, op in enumerate(self.adds):
            if op["at"] != a:
                continue
            try:
                at, make = E.line_place(f, self.kind, self.current, op.get("place"), op.get("level"), op.get("key"))
            except ValueError:
                continue
            pending.append((at, n, make(op["text"])))
        row = 0

        def added_rows(before):
            nonlocal row
            for at, n, lines in [p for p in pending if p[0] <= before]:
                for text in lines:
                    ttk.Label(self.form, text="+ new", foreground="#2a7a1f", font=("", 9, "bold")).grid(
                        row=row, column=1, sticky="w", padx=(0, 8))
                    tk.Label(self.form, text=text.expandtabs(4).strip(), anchor="w", background=ADDED, foreground="#000000",
                             font=("", 9)).grid(row=row, column=2, sticky="we", pady=1)
                    if text.strip() == self.adds[n]["text"].strip():
                        tk.Button(self.form, text="x", command=lambda n=n: self.drop_add(n), **SMALL).grid(
                            row=row, column=0, padx=(0, 4))
                    row += 1
                pending.remove((at, n, lines))
        for fd in self.fields:
            added_rows(fd.line)
            gone = fd.line in self.removes
            ttk.Label(self.form, text="    " * fd.depth + fd.key, font=("", 9, "bold", "overstrike") if gone else
                      ("", 9, "bold")).grid(row=row, column=1, sticky="w", padx=(0, 8))
            v = tk.StringVar(value=self.changes.get(fd.line, fd.value))
            e = tk.Entry(self.form, textvariable=v, width=90,
                         background=REMOVED if gone else CHANGED if fd.line in self.changes else theme.field(),
                         foreground="#000000" if gone or fd.line in self.changes else theme.palette()["fg"])
            e.grid(row=row, column=2, sticky="we", pady=1)
            v.trace_add("write", lambda *x, fd=fd, v=v, e=e: self.edited(fd, v.get(), e))
            if self.kind == "unit" and fd.key in unitattrs.LINES and unitattrs.for_line(fd.key) and not gone:
                ttk.Button(self.form, text="REX...", width=7,
                           command=lambda fd=fd, v=v: self.attrs_dialog(fd, v)).grid(row=row, column=3, padx=(4, 0))
            why = E.removable(self.kind, fd, self.tree, self.required())
            if why is None:
                tk.Button(self.form, text="\u21ba" if gone else "x", command=lambda fd=fd: self.toggle_remove(fd),
                          **SMALL).grid(row=row, column=0, padx=(0, 4))
            row += 1
        added_rows(b + 1)
        self.show_pictures()
        self.show_links()

    def attrs_dialog(self, fd, var):
        """Tick the words REX knows for this line (attributes, morale, terrain, weapons);
        the line's value changes like a typed edit."""
        from .limits import faction_limit
        w = tk.Toplevel(self)
        w.title("%s: what REX adds" % fd.key)
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        rex = faction_limit(self.mod).get("engine") == "REX.exe"
        ttk.Label(frm, text=("Ticked = on this unit's '%s' line. These words work only under REX; "
                             "the original game refuses them%s." % (
                                 fd.key, "" if rex else " - the game folder has no REX.exe")),
                  wraplength=560, justify="left").pack(anchor="w", pady=(0, 8))
        now = unitattrs.words(var.get())
        ticks = {}
        for word, effect in unitattrs.for_line(fd.key):
            ticks[word] = tk.BooleanVar(value=word in now)
            row = ttk.Frame(frm)
            row.pack(fill="x", anchor="w")
            ttk.Checkbutton(row, text=word, variable=ticks[word], width=28).pack(side="left")
            ttk.Label(row, text=effect, foreground="#666", wraplength=420, justify="left").pack(side="left")

        def ok():
            value = var.get()
            for word, t in ticks.items():
                value = unitattrs.toggled(fd.key, value, word, t.get())
            var.set(value)
            w.destroy()
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=(10, 0))
        ttk.Button(bar, text="OK", command=ok).pack(side="right")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="right", padx=6)

    def limits(self):
        if getattr(self, "_limits", None) is None:
            self._limits = E.line_limits(self.mod.load(self.path()), self.kind)
        return self._limits

    def required(self):
        if getattr(self, "_required", None) is None:
            self._required = E.required_keys(self.mod.load(self.path()), self.kind)
        return self._required

    def toggle_remove(self, fd):
        if fd.line in self.removes:
            self.removes.discard(fd.line)
        else:
            self.removes.add(fd.line)
            self.changes.pop(fd.line, None)
        self._changed()
        self.show()

    def drop_add(self, n):
        del self.adds[n]
        self._changed()
        self.show()

    def _changed(self):
        self.fill_list_keep()
        self.app.status.set("%d field(s) changed, %d line(s) to add, %d to remove in %s - Preview, then Apply." % (
            len(self.changes), len(self.adds), len(self.removes), os.path.basename(self.path())))

    def fill_list_keep(self):
        sel = self.lb.curselection()
        self.fill_list()
        if sel:
            self.lb.selection_set(sel[0])

    def edited(self, fd, value, entry):
        if value.strip() == fd.value:
            self.changes.pop(fd.line, None)
            entry.configure(background=theme.field(), foreground=theme.palette()["fg"])
        else:
            self.changes[fd.line] = value
            entry.configure(background=CHANGED, foreground="#000000")
        self.app.status.set("%d field(s) changed in %s - Preview, then Apply." % (
            len(self.changes), os.path.basename(self.path())))

    def value(self, key):
        fd = next((x for x in getattr(self, "fields", []) if x.key == key), None)
        return self.changes.get(fd.line, fd.value) if fd else ""

    def reset(self):
        self.changes, self.imports, self.copy_ops = {}, [], []
        self.adds, self.removes = [], set()
        self.fill_list()
        self.show()
        self.app.status.set("Nothing changed in the %s editor." % self.kind)

    # ---- what it is tied to ----
    def recruits(self):
        """[(line, unit, chain, level)] of the buildings file, read once per load."""
        if self._recruits is None:
            from .roster import recruit_lines
            edb = self.mod.file("edb")
            self._recruits = recruit_lines(self.mod.load(edb)) if edb else []
        return self._recruits

    def show_links(self):
        try:
            text = self._unit_links() if self.kind == "unit" else self._building_links()
        except Exception as e:                     # information only: never in the way of editing
            text = "(could not read: %s)" % e
        self.lbl_links.configure(text=text)

    def _short(self, items, n=6):
        items = list(items)
        return ", ".join(items[:n]) + (" and %d more" % (len(items) - n) if len(items) > n else "") if items else "none"

    def _unit_links(self):
        from .roster import covers, factions_in
        name = self.current[0]
        own = [x for x in self.value("ownership").replace(",", " ").split() if x]
        facs = self.mod.factions()
        owners = [f for f, c in facs if covers(own, f, c)]
        edb = self.mod.load(self.mod.file("edb")) if self.mod.file("edb") else None
        places = ["%s/%s (%s)" % (c, l, " ".join(factions_in(edb.text(i)) or ["all"]))
                  for i, u, c, l in self.recruits() if u == name]
        camp = self.app.v_campaign.get()
        armies = 0
        if self.app.strat is not None:
            from .start import unit_name
            from .textio import tokens
            armies = sum(1 for l in self.app.strat.lines if tokens(l)[:1] == ["unit"] and unit_name(l) == name)
        return ("owned by: %s\nrecruited in: %s\nin armies at the start of %s: %d\n"
                "follows a change: new 'type' -> recruit lines, armies of every campaign, mercenaries, rebels; "
                "new 'dictionary' -> texts and cards copied; new owners -> their cards" % (
                    self._short(owners), self._short(places, 4), camp or "the campaign", armies))

    def _building_links(self):
        from .roster import factions_in
        name, a, b = self.current
        f = self.mod.load(self.path())
        lv_txt = []
        for lv in self.tree["levels"]:
            names = factions_in(f.text(lv["head"]))
            lv_txt.append("%s: %s" % (lv["name"], "everyone" if names is None else self._short(names, 3)))
        need = []
        rx = E.re.compile(r"\bbuilding_present(?:_min_level)?\s+%s\b" % E.re.escape(name))
        for c, x, y in self.blocks:
            if c != name and any(rx.search(f.text(i)) for i in range(x, y)):
                need.append(c)
        towns = 0
        if self.app.strat is not None:
            from .textio import tokens
            towns = sum(1 for l in self.app.strat.lines if tokens(l)[:2] == ["type", name])
        lv = getattr(self, "v_level", None)
        lv = lv.get() if lv is not None and lv.get() else (self.tree["levels"][0]["name"] if self.tree["levels"] else "")
        names = E.level_names(self.mod, lv) if lv else []
        named = ("names of %s (per culture or faction; pictures per culture above): %s\n" % (
            lv, self._short(["%s: %s" % x for x in names], 8))) if names else ""
        return (named + "who may build: %s\nrequired by (building_present...): %s;   in towns at the start of %s: %d\n"
                "follows a change: new chain name -> towns of every campaign and the requirements naming it; "
                "a recruit line added -> its factions own the unit and get its cards" % (
                    ";  ".join(lv_txt), self._short(need), self.app.v_campaign.get() or "the campaign", towns))

    # ---- adding a line ----
    def add_dialog(self):
        if not self.current:
            messagebox.showerror("Add line", "pick the %s on the left first" % self.kind)
            return
        name, a, b = self.current
        f = self.mod.load(self.path())
        w = tk.Toplevel(self)
        w.title("Add a line to %s" % name)
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        v = {k: tk.StringVar() for k in ("place", "level", "key", "value", "unit", "exp", "factions", "extra",
                                         "start", "per_turn", "most")}
        v["exp"].set("0")
        v["start"].set("1")
        v["per_turn"].set("0.5")
        v["most"].set("4")
        v_own = tk.BooleanVar(value=True)
        v_retrain = tk.BooleanVar(value=False)
        from .roster import recruit_dialect
        dialect = recruit_dialect(f) if self.kind == "building" else "plain"
        body = ttk.Frame(frm)
        preview = ttk.Label(frm, text="", font=("Courier", 10))
        problems = ttk.Label(frm, text="", foreground="#b00020", justify="left", wraplength=620)
        levels = [lv["name"] for lv in self.tree["levels"]] if self.tree else []
        units = E.unit_names(self.mod) if self.kind == "building" else []
        conds = E.conditions_seen(f) if self.kind == "building" else []
        seen = {}

        def keys(place):
            if place not in seen:
                seen[place] = E.keys_seen(f, self.kind, place)
            return seen[place]

        def text():
            place = v["place"].get()
            if place == "recruit":
                return E.recruit_text(dialect, v["unit"].get().strip(), v["exp"].get().strip() or "0",
                                      (v["start"].get().strip() or "1", v["per_turn"].get().strip() or "0.5",
                                       v["most"].get().strip() or "4"), v_retrain.get(),
                                      v["factions"].get().replace(",", " ").split(), v["extra"].get())
            if place == "upgrades":
                return v["value"].get().strip()
            return ("%s %s" % (v["key"].get().strip(), v["value"].get().strip())).strip()

        def refresh(*_):
            t = text()
            preview.configure(text=t)
            probs = E.check_text(self.mod, self.kind, t) if t else []
            if v["place"].get() == "upgrades" and t and t not in levels:
                probs.append((True, "'%s' is not a level of %s" % (t, name)))
            if v["place"].get() == "upgrades" and t == v["level"].get():
                probs.append((True, "a level cannot upgrade to itself"))
            problems.configure(text="\n".join(("error: " if e else "note: ") + m for e, m in probs))

        def rebuild(*_):
            for c in body.winfo_children():
                c.destroy()
            place = v["place"].get()
            r = 0

            def row(label, widget, hint=None):
                nonlocal r
                ttk.Label(body, text=label).grid(row=r, column=0, sticky="w", pady=2)
                widget.grid(row=r, column=1, sticky="we", padx=6, pady=2)
                if hint:
                    ttk.Label(body, text=hint, foreground="#666", wraplength=420, justify="left").grid(
                        row=r + 1, column=1, sticky="w", padx=6)
                    r += 1
                r += 1
            if place == "recruit":
                cb = ttk.Combobox(body, textvariable=v["unit"], values=units, width=40)
                cb.bind("<KeyRelease>", lambda e: cb.configure(
                    values=[u for u in units if v["unit"].get().lower() in u.lower()]))

                def unit_picked(*_):
                    from .roster import ownership, _find_unit
                    try:
                        edu = self.mod.load(self.mod.file("edu"))
                        v["factions"].set(", ".join(ownership(edu, _find_unit(edu, v["unit"].get()))))
                    except ValueError:
                        pass
                cb.bind("<<ComboboxSelected>>", unit_picked)
                row("Unit", cb)
                if dialect == "pool":            # Medieval II: a pool of units that fills up turn by turn
                    row("Units at the start", ttk.Entry(body, textvariable=v["start"], width=8))
                    row("New units a turn", ttk.Entry(body, textvariable=v["per_turn"], width=8),
                        "may be a fraction: 0.5 = one unit every two turns")
                    row("Most units waiting", ttk.Entry(body, textvariable=v["most"], width=8))
                row("Experience", ttk.Spinbox(body, from_=0, to=9, textvariable=v["exp"], width=5))
                ttk.Checkbutton(body, text="only retraining, no new units (REX: '%s')" % (
                    "retrain_pool" if dialect == "pool" else "retrain"), variable=v_retrain,
                    command=refresh).grid(row=r, column=0, columnspan=2, sticky="w")
                r += 1
                row("Factions", ttk.Entry(body, textvariable=v["factions"], width=50),
                    "who recruits it here: factions or cultures, comma separated (the unit's owners when you pick it)")
                row("More conditions", ttk.Entry(body, textvariable=v["extra"], width=50),
                    "optional, e.g. 'and not marian_reforms'. This mod uses: " + ", ".join(conds[:12]))
                ttk.Checkbutton(body, text="factions named here that do not own the unit get it "
                                           "(its ownership line) and its cards", variable=v_own).grid(
                    row=r, column=0, columnspan=2, sticky="w", pady=(4, 0))
            elif place == "upgrades":
                row("Upgrades to", ttk.Combobox(body, textvariable=v["value"], values=levels, state="readonly"))
            else:
                ks = keys("capability" if place == "capability" else "level" if place == "level" else None)
                # only keys that may take one more line here (unknown keys and a second one-line key left out)
                ks = {k: x for k, x in ks.items() if not E.room_for(
                    f, self.kind, self.current, place if self.kind == "building" else None,
                    v["level"].get() or None, k, self.limits(), mod=self.mod)}
                cb = ttk.Combobox(body, textvariable=v["key"], values=sorted(ks), width=40)

                def key_picked(*_):
                    v["value"].set(ks.get(v["key"].get(), ""))
                cb.bind("<<ComboboxSelected>>", key_picked)
                engine = "; also keys the engine knows: %s" % ", ".join(
                    "%s (%s)" % (k, d) for k, (_, d) in unitattrs.ENGINE_KEYS.items()) if self.kind == "unit" else ""
                row("Key", cb, "the keys this mod already uses here (a one-line key only once, the others as many "
                               "times as you like); the value is filled with an example" + engine)
                row("Value", ttk.Entry(body, textvariable=v["value"], width=50))
            refresh()
        top = ttk.Frame(frm)
        top.pack(fill="x")
        if self.kind == "building":
            ttk.Label(top, text="Level").pack(side="left")
            v["level"].set(self.v_level.get() if getattr(self, "v_level", None) and self.v_level.get() in levels
                           else (levels[0] if levels else ""))
            ttk.Combobox(top, textvariable=v["level"], values=levels, state="readonly", width=28).pack(
                side="left", padx=(4, 12))
            for label, val in (("Recruit a unit", "recruit"), ("Capability (bonus...)", "capability"),
                               ("Upgrades to", "upgrades"), ("Other line of the level", "level")):
                ttk.Radiobutton(top, text=label, value=val, variable=v["place"], command=rebuild).pack(side="left")
            v["place"].set("recruit")
        else:
            v["place"].set("unit")
        body.pack(fill="x", pady=8)
        ttk.Label(frm, text="The line:").pack(anchor="w")
        preview.pack(anchor="w", pady=(0, 4))
        problems.pack(anchor="w")
        for x in v.values():
            x.trace_add("write", refresh)

        def ok():
            t = text()
            probs = E.check_text(self.mod, self.kind, t) if t else [(True, "empty line")]
            place = v["place"].get()
            if place == "upgrades" and (t not in levels or t == v["level"].get()):
                probs.append((True, "pick another level of this chain"))
            errs = [m for e, m in probs if e]
            if errs:
                messagebox.showerror("Add line", "\n".join(errs), parent=w)
                return
            op = {"at": a, "block": name, "place": "capability" if place == "recruit" else place,
                  "level": v["level"].get() or None, "key": v["key"].get().strip() or None, "text": t}
            if self.kind == "unit":
                op["place"], op["level"] = None, None
            key = E.tokens(t)[0] if E.tokens(t) else ""
            same = sum(1 for x in self.adds if x["at"] == a and x.get("place") == op["place"]
                       and x.get("level") == op["level"] and (E.tokens(x["text"]) or [""])[0] == key)
            full = E.room_for(f, self.kind, self.current, op["place"], op["level"], key, self.limits(),
                              same if op["place"] != "upgrades" else sum(
                                  1 for x in self.adds if x["at"] == a and x.get("place") == "upgrades"
                                  and x.get("level") == op["level"]), mod=self.mod)
            if full:
                messagebox.showerror("Add line", full + " - the tool keeps to what the mod already uses", parent=w)
                return
            if place == "recruit" and v_own.get():
                op["own"] = [x for x in v["factions"].get().replace(",", " ").split() if x]
            self.adds.append(op)
            w.destroy()
            self._changed()
            self.show()
        bar = ttk.Frame(frm)
        bar.pack(anchor="e", pady=(8, 0))
        ttk.Button(bar, text="Add", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)
        rebuild()

    # ---- pictures ----
    def _thumb(self, parent, path, size=(80, 100)):
        from PIL import Image, ImageTk
        try:
            im = Image.open(path).convert("RGBA")
            im.thumbnail(size)
            ph = ImageTk.PhotoImage(im)
        except Exception:
            return ttk.Label(parent, text="(none)", width=12, relief="sunken")
        self._photos.append(ph)
        return tk.Label(parent, image=ph, relief="sunken")

    def _factions_of(self):
        """The faction folders a unit's card goes to: the factions its ownership names,
        and those of a culture it names."""
        own = [x.strip() for x in self.value("ownership").replace(",", " ").split() if x.strip()]
        facs = self.mod.factions()
        out = [n for n, c in facs if n in own or c in own or "all" in own]
        return out or own

    def show_pictures(self):
        for w in self.pics.winfo_children():
            w.destroy()
        self._photos = []
        if self.kind == "unit":
            self._unit_pictures()
        else:
            self._building_pictures()

    def _pending(self, targets):
        return next((src for src, t, _ in self.imports if set(t) & set(targets)), None)

    def _unit_pictures(self):
        from .units import card_path
        dic = self.value("dictionary")
        facs = self._factions_of()
        if not dic:
            ttk.Label(self.pics, text="no dictionary line - no pictures").pack(anchor="w")
            return
        for col, (info, label) in enumerate(((False, "Unit card"), (True, "Picture in the description"))):
            box = ttk.Frame(self.pics)
            box.grid(row=col, column=0, sticky="nw", pady=(0, 6))
            targets = E.unit_picture_targets(self.mod, dic, facs, info)
            pending = self._pending(targets)
            have = pending or card_path(self.mod, facs[0] if facs else "", dic, info)
            self._thumb(box, have).grid(row=0, column=0, rowspan=3)
            need = E.unit_picture_need(self.mod, info)
            ttk.Label(box, text=label, font=("", 9, "bold")).grid(row=0, column=1, sticky="w", padx=6)
            ttk.Label(box, foreground="#555", justify="left", text=(
                "needs %d x %d, %d-bit TGA (as this mod's own)" % need if need else "size: as you like") +
                "\nPNG / JPG / TGA are converted\ngoes to %s for %s" % (
                    "ui/unit_info/<faction>/%s_info.tga" % dic if info else "ui/units/<faction>/#%s.tga" % dic,
                    ", ".join(facs[:4]) + (" and %d more" % (len(facs) - 4) if len(facs) > 4 else "")) +
                ("\nnew: %s (not written yet)" % os.path.basename(pending) if pending else "")).grid(
                row=1, column=1, sticky="w", padx=6)
            ttk.Button(box, text="Import...", command=lambda t=targets, n=need, l=label: self.import_pic(t, n, l)).grid(
                row=2, column=1, sticky="w", padx=6)
        ttk.Label(self.pics, text="3D model, textures and icons: next steps", foreground="#888").grid(
            row=2, column=0, sticky="w")

    def _building_pictures(self):
        from .buildings import BuildingPictures
        levels = self.value("levels").split()
        if not levels:
            ttk.Label(self.pics, text="no levels line").pack(anchor="w")
            return
        ui = os.path.join(self.mod.data, "ui")
        cultures = sorted(n for n in os.listdir(ui) if os.path.isdir(os.path.join(ui, n, "buildings"))) \
            if os.path.isdir(ui) else []
        bar = ttk.Frame(self.pics)
        bar.grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(bar, text="Level").pack(side="left")
        self.v_level = getattr(self, "v_level", tk.StringVar())
        if self.v_level.get() not in levels:
            self.v_level.set(levels[0])
        cb = ttk.Combobox(bar, textvariable=self.v_level, values=levels, state="readonly", width=24)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda ev: (self.show_pictures(), self.show_links()))
        ttk.Label(bar, text="Culture").pack(side="left", padx=(12, 0))
        self.v_cult = getattr(self, "v_cult", tk.StringVar())
        if self.v_cult.get() not in cultures:
            self.v_cult.set(cultures[0] if cultures else "")
        cb2 = ttk.Combobox(bar, textvariable=self.v_cult, values=cultures, state="readonly", width=14)
        cb2.pack(side="left", padx=4)
        cb2.bind("<<ComboboxSelected>>", lambda ev: self.show_pictures())
        if not cultures:
            ttk.Label(self.pics, text="no ui/<culture>/buildings folders in this mod").grid(row=1, column=0)
            return
        pics = BuildingPictures(self.mod)
        level, cult = self.v_level.get(), self.v_cult.get()
        for col, (constructed, label) in enumerate(((False, "Building picture"), (True, "Picture when built"))):
            box = ttk.Frame(self.pics)
            box.grid(row=1, column=col, sticky="nw", padx=(0, 24), pady=(6, 0))
            target = E.building_picture_target(self.mod, cult, level, constructed)
            pending = self._pending([target])
            self._thumb(box, pending or pics.find(cult, level, constructed), (120, 100)).grid(row=0, column=0, rowspan=3)
            need = E.building_picture_need(self.mod, cult, constructed)
            ttk.Label(box, text=label, font=("", 9, "bold")).grid(row=0, column=1, sticky="w", padx=6)
            ttk.Label(box, foreground="#555", justify="left", text=(
                "needs %d x %d, %d-bit TGA (as this mod's own)" % need if need else "size: as you like") +
                "\nPNG / JPG / TGA are converted\ngoes to ui/%s/buildings/%s" % (cult, os.path.basename(target)) +
                ("\nnew: %s (not written yet)" % os.path.basename(pending) if pending else "")).grid(
                row=1, column=1, sticky="w", padx=6)
            ttk.Button(box, text="Import...", command=lambda t=[target], n=need, l=label: self.import_pic(t, n, l)).grid(
                row=2, column=1, sticky="w", padx=6)

    def import_pic(self, targets, need, label):
        if not targets:
            messagebox.showerror("Import", "no folder to put it in (no faction owns this unit?)")
            return
        src = filedialog.askopenfilename(title=label, filetypes=[
            ("Pictures", "*.tga *.png *.jpg *.jpeg *.bmp *.dds"), ("All files", "*.*")])
        if not src:
            return
        try:
            from PIL import Image
            with Image.open(src) as im:
                got = im.size
        except Exception as e:
            messagebox.showerror("Import", "Cannot read %s: %s" % (src, e))
            return
        size = need[:2] if need else None
        if size and tuple(got) != tuple(size):
            if not messagebox.askyesno("Import", "%s is %d x %d; this mod's own are %d x %d.\n\n"
                                                 "Resize it to %d x %d?" % ((os.path.basename(src),) + tuple(got) +
                                                                            tuple(size) + tuple(size))):
                size = None
        self.imports = [(s, t, z) for s, t, z in self.imports if not set(t) & set(targets)]
        self.imports.append((src, list(targets), size))
        self.app.status.set("%s: %s for %d place(s) - Preview, then Apply." % (label, os.path.basename(src), len(targets)))
        self.show_pictures()

    # ---- writing ----
    def dirty(self):
        return bool(self.changes or self.imports or self.copy_ops or self.adds or self.removes)

    # ---- unit packs ----
    def export_pack(self):
        """The picked unit - or every unit the list shows - with its models, mount, textures,
        cards, texts and recruit places, into one .zip for another mod."""
        from tkinter import filedialog
        from . import packs
        if not self.mod:
            return
        sel = self.lb.curselection()
        picked = self.shown[sel[0]][0] if sel and sel[0] < len(self.shown) else None
        types = [b[0] for b in self.shown]
        if picked and len(types) > 1:
            one = messagebox.askyesnocancel(
                "Export pack", "Yes: only %s\nNo: all %d units the list shows now (Show / Find)" % (picked, len(types)),
                parent=self)
            if one is None:
                return
            if one:
                types = [picked]
        elif picked:
            types = [picked]
        if not types:
            messagebox.showinfo("Export pack", "no unit in the list", parent=self)
            return
        name = (types[0] if len(types) == 1 else "%d_units" % len(types)).replace(" ", "_")
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".zip", initialfile="%s_pack.zip" % name,
                                            filetypes=[("Unit pack", "*.zip")])
        if not path:
            return
        try:
            man = packs.export_pack(self.mod, types, path)
        except Exception as e:
            messagebox.showerror("Export pack", str(e), parent=self)
            return
        miss = man.get("missing") or []
        blocks = man["blocks"]
        messagebox.showinfo("Export pack", (
            "%s\n\n%d unit(s), %d model(s), %d mount(s), %d engine(s), %d animal(s), %d file(s), "
            "%d name / description text(s), %d recruit place(s).%s" % (
                path, len(man["units"]), len(blocks["model"]), len(blocks["mount"]), len(blocks["engine"]),
                len(blocks["animal"]), len(man["files"]), len(man["texts"]), len(man["recruit"]),
                ("\n\n%d file(s) the units name are not in this mod (the game takes them from its own data "
                 "or they are missing): %s%s" % (len(miss), ", ".join(miss[:3]), " ..." if len(miss) > 3 else ""))
                if miss else "")), parent=self)
        self.app.status.set("Pack written: %s (%d unit(s))." % (path, len(man["units"])))

    def import_pack(self):
        """A pack's units put into this mod: names checked (taken ones get a free name you may
        change), the factions or cultures that own them picked, then Preview and a written plan
        with a backup like every other change."""
        from tkinter import filedialog
        from . import packs
        from .plan import Plan
        if not self.mod:
            return
        if self.pending() and not messagebox.askyesno(
                "Import pack", "The unit editor holds changes not written yet; the import writes "
                               "export_descr_unit.txt, so they would be dropped. Go on?", parent=self):
            return
        path = filedialog.askopenfilename(parent=self, filetypes=[("Unit pack", "*.zip")])
        if not path:
            return
        try:
            man, files = packs.read_pack(path)
            names = packs.plan_names(self.mod, man)
        except Exception as e:
            messagebox.showerror("Import pack", str(e), parent=self)
            return
        w = tk.Toplevel(self)
        w.title("Import pack - %s" % os.path.basename(path))
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Units (a name taken in this mod has a free one already; change it if you like)",
                  font=("", 9, "bold")).grid(row=0, column=0, columnspan=3, sticky="nw")
        vs = {}
        for c, head in enumerate(("in the pack", "type in this mod", "dictionary (cards, texts)")):
            ttk.Label(frm, text=head, foreground="#555").grid(row=0, column=c, sticky="w", pady=(18, 0))
        for i, u in enumerate(man["units"]):
            t, d = names[u["type"]]
            ttk.Label(frm, text=u["type"]).grid(row=i + 1, column=0, sticky="w")
            vt, vd = tk.StringVar(value=t), tk.StringVar(value=d or "")
            ttk.Entry(frm, textvariable=vt, width=30).grid(row=i + 1, column=1, padx=4, pady=1)
            ttk.Entry(frm, textvariable=vd, width=26).grid(row=i + 1, column=2, padx=4, pady=1)
            vs[u["type"]] = (vt, vd)
        row = len(man["units"]) + 1
        ttk.Label(frm, text="Given to (factions or cultures - pick one or more):",
                  font=("", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
        facs = [n for n, _ in self.mod.factions()]
        cultures = sorted({self.mod.culture(n) for n in facs if self.mod.culture(n)})
        choices = facs + [c for c in cultures if c not in facs]
        lb = tk.Listbox(frm, selectmode="multiple", height=min(12, len(choices)), exportselection=False)
        for c in choices:
            lb.insert("end", c + ("  (culture)" if c in cultures and c not in facs else ""))
        had = set()
        for u in man["units"]:
            for v in packs._values(u["lines"], "ownership"):
                had |= set(v)
        for i, c in enumerate(choices):
            if c in had:
                lb.selection_set(i)
        lb.grid(row=row + 1, column=0, columnspan=3, sticky="we")
        what = "%d model(s), %d mount(s), %d file(s), %d recruit place(s)%s" % (
            len(man["blocks"]["model"]), len(man["blocks"]["mount"]), len(files), len(man["recruit"]),
            " - from Medieval II" if man.get("game") == "medieval2" else " - from Rome")
        ttk.Label(frm, text="In the pack: " + what, foreground="#555").grid(
            row=row + 2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        def make():
            owners = [choices[i] for i in lb.curselection()]
            chosen = {k: (vt.get().strip(), vd.get().strip() or None) for k, (vt, vd) in vs.items()}
            plan = Plan(self.mod, "pack", "unit_pack", {})
            packs.import_pack(plan, man, files, owners, chosen)
            return plan

        def preview():
            try:
                plan = make()
            except Exception as e:
                messagebox.showerror("Import pack", str(e), parent=w)
                return
            self.app.show_text("Import pack - preview (nothing written)", plan.report())

        def write():
            try:
                plan = make()
            except Exception as e:
                messagebox.showerror("Import pack", str(e), parent=w)
                return
            if not messagebox.askyesno("Import pack", "Write %d file(s)? A backup is made first (Restore undoes "
                                                      "it)." % len(plan.changed_files()), parent=w):
                return
            bdir = plan.apply()
            from . import log
            log.write("Unit pack %s written (backup %s)\n%s" % (path, bdir, plan.report()))
            w.destroy()
            self.app.load()
            self.app.status.set("Pack put in: %d unit(s) (backup %s)." % (len(man["units"]), bdir))
        bar = ttk.Frame(frm)
        bar.grid(row=row + 3, column=0, columnspan=3, sticky="e", pady=(8, 0))
        ttk.Button(bar, text="Preview", command=preview).pack(side="left")
        ttk.Button(bar, text="Write it in", command=write).pack(side="left", padx=4)
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")

    def pending(self):
        """How many changes wait for Apply here."""
        return len(self.changes) + len(self.imports) + len(self.copy_ops) + len(self.adds) + len(self.removes)

    def _signature(self):
        """What the file is now (its bytes' md5): the changes wait on the lines as they were read."""
        import hashlib
        p = self.path()
        try:
            with open(p, "rb") as fh:
                return hashlib.md5(fh.read()).hexdigest()
        except (OSError, TypeError):
            return None

    def rebind(self, mod):
        """The window loaded the mod again (after an Apply, say). Changes waiting here are
        kept while the file they sit on is unchanged; else the editor reads it again and
        they go (their line numbers would be wrong). Returns how many were dropped."""
        if self.mod is not None and self.dirty() and mod.data == self.mod.data:
            old = self.mod
            self.mod = mod
            if self._signature() == getattr(self, "_sig", None):
                return 0
            self.mod = old
            n = self.pending()
            self.load(mod)
            return n
        self.load(mod)
        return 0

    def _check(self, mod, f, changes):
        """Nothing is written while a changed or added line names what the mod has not
        (a unit, a building level), or a chain's levels line and its level blocks differ."""
        errs, notes = [], []
        for ln, value in changes.items():
            key = E.tokens(f.text(ln))[:1]
            name = next((b[0] for b in self.blocks if b[1] <= ln < b[2]), "")
            text = "%s %s" % (key[0] if key else "", value)
            for e, m in E.check_text(mod, self.kind, text):
                (errs if e else notes).append("%s, line %d: %s" % (name, ln + 1, m))
            if self.kind == "building" and key == ["levels"]:
                blk = next(b for b in self.blocks if b[1] <= ln < b[2])
                have = [lv["name"] for lv in E.chain_tree(f, blk[1], blk[2])["levels"]]
                if sorted(value.split()) != sorted(have):
                    errs.append("%s: 'levels' must name its level blocks (%s); a new or renamed level: "
                                "Copy as new building" % (name, " ".join(have)))
        for op in self.adds:
            for e, m in E.check_text(mod, self.kind, op["text"]):
                (errs if e else notes).append("%s: %s" % (op["block"], m))
        if errs:
            raise ValueError("Nothing written:\n" + "\n".join(errs))
        self._notes = notes

    def _follow(self, plan, f, changes):
        for n in getattr(self, "_notes", []):
            plan.warn(None, n)
        from .roster import copy_cards, covers
        for ln, value in changes.items():
            key = E.tokens(f.text(ln))[:1]
            old = E.strip_comment(f.text(ln)).strip()[len(key[0]):].strip() if key else ""
            new = " ".join(value.split())
            if self.kind == "unit" and key == ["type"] and new != old:
                E.rename_unit(plan, old, new)
            elif self.kind == "unit" and key == ["dictionary"] and new != old:
                E.rename_dictionary(plan, old, new)
            elif self.kind == "unit" and key == ["ownership"]:
                was = [x for x in old.replace(",", " ").split() if x]
                now = [x for x in new.replace(",", " ").split() if x]
                blk = next(b for b in self.blocks if b[1] <= ln < b[2])
                dic = next((E.tokens(f.text(i))[1] for i in range(blk[1], blk[2])
                            if E.tokens(f.text(i))[:1] == ["dictionary"] and len(E.tokens(f.text(i))) > 1), None)
                facs = plan.mod.factions()
                owners = [x for x, c in facs if covers(was, x, c)]
                for fac, cult in facs:
                    if covers(now, fac, cult) and not covers(was, fac, cult) and fac != "slave" and dic:
                        copy_cards(plan, fac, dic, owners)
            elif self.kind == "building" and key == ["building"] and new != old:
                E.rename_chain(plan, old, new)

    def copy_dialog(self):
        """A new unit (building chain) made from the one on show: new names, then Apply."""
        if not self.current:
            messagebox.showerror("Copy", "pick the %s to copy on the left first" % self.kind)
            return
        name = self.current[0]
        w = tk.Toplevel(self)
        w.title("New %s from %s" % (self.kind, name))
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        vs = {}
        if self.kind == "unit":
            dic = self.value("dictionary")
            rows = [("type (its name in the files)", "type", name + " 2"),
                    ("dictionary (cards and text keys; no spaces)", "dict", dic + "_2")]
        else:
            levels = self.value("levels").split()
            rows = [("building chain", "chain", name + "_2")] + \
                [("level %s becomes" % l, "lv:" + l, l + "_2") for l in levels]
        for i, (label, key, default) in enumerate(rows):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=1)
            vs[key] = tk.StringVar(value=default)
            ttk.Entry(frm, textvariable=vs[key], width=40).grid(row=i, column=1, sticky="we", padx=6)
        v_rec = tk.BooleanVar(value=True)
        if self.kind == "unit":
            ttk.Checkbutton(frm, text="recruitable wherever %s is (a recruit line next to each of its own)" % name,
                            variable=v_rec).grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(frm, foreground="#555", justify="left", wraplength=460, text=(
            "Copied too: its names and descriptions in the text tables and its pictures (cards / building "
            "pictures) under the new names - replace them afterwards. Written on Apply, with a backup.")).grid(
            row=len(rows) + 1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        def ok():
            d = {k: v.get().strip() for k, v in vs.items()}
            if self.kind == "unit":
                op = (name, d["type"], {"dict": d["dict"], "recruit": v_rec.get()})
            else:
                op = (name, d["chain"], {"levels": {k[3:]: v for k, v in d.items() if k.startswith("lv:")}})
            if not all(d.values()):
                messagebox.showerror("Copy", "fill in every name", parent=w)
                return
            self.copy_ops.append(op)
            w.destroy()
            self.app.status.set("New %s %s from %s - Preview, then Apply." % (self.kind, op[1], name))
            self.fill_list()
        bar = ttk.Frame(frm)
        bar.grid(row=len(rows) + 2, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(bar, text="Add", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    def make_plan(self):
        if not self.mod:
            raise ValueError("load a mod first")
        if not self.dirty():
            raise ValueError("nothing changed in the %s editor" % self.kind)
        mod = ModData(self.mod.data)
        plan = Plan(mod, self.kind + "s", self.kind + "s", {})
        path = mod.file("edu" if self.kind == "unit" else "edb")
        f = mod.load(path)
        changes = {ln: v for ln, v in self.changes.items() if ln not in self.removes}
        self._check(mod, f, changes)
        by_line = {}
        for name, a, b in self.blocks:
            for ln in changes:
                if a <= ln < b:
                    by_line.setdefault(name, {})[ln] = changes[ln]
        for name, ch in by_line.items():
            E.apply_fields(plan, path, ch, "%s %s" % (self.kind, name))
        # what the changed fields drag along (names used elsewhere, new owners' cards)
        self._follow(plan, f, changes)
        # lines added and removed: the blocks are found by their first line (a renamed
        # unit or chain keeps it), so this works on the file with the fields changed
        g = plan.edit(path)
        now = {b[1]: b[0] for b in (E.unit_blocks(g) if self.kind == "unit" else E.building_blocks(g))}
        adds = [dict(op, block=now.get(op["at"], op["block"])) for op in self.adds]
        E.restructure(plan, path, self.kind, adds, sorted(self.removes))
        from .roster import copy_cards, dictionary, _find_unit, own_unit
        for op in self.adds:                            # a recruit line's factions that do not own the unit
            if not op.get("own"):
                continue
            unit = E.re.match(r'\s*recruit\s+"([^"]+)"', op["text"]).group(1)
            edu = plan.edit(mod.file("edu"))
            blk = _find_unit(edu, unit)
            facs = dict(mod.factions())
            for fac in op["own"]:
                if fac in facs and own_unit(plan, fac, unit, True):
                    copy_cards(plan, fac, dictionary(edu, blk))
        for src, targets, size in self.imports:
            E.import_picture(plan, src, targets, size)
        for src, new, d in self.copy_ops:                 # after the field changes: copies add lines
            if self.kind == "unit":
                E.copy_unit(plan, src, new, d["dict"], d["recruit"])
            else:
                E.copy_building(plan, src, new, d["levels"])
        return plan
