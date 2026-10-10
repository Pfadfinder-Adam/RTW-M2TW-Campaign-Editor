"""Units and Buildings tabs: pick a unit (a building chain) on
the left, change any line of its block on the right, and import its pictures -
the tool puts them where the game reads them, in the mod's own format."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .gui_util import ask, ask_choice
from .gui_util import ShortHint, hint
from .gui_util import scroll_body
from . import editors as E
from . import settings, theme, unitattrs
from .gui_util import save_copy
from .moddata import ModData, _ci
from .plan import Plan

CHANGED = "#fff2b3"          # a field changed and not written yet
REMOVED = "#f4c7c3"          # a line to be removed
ADDED = "#d9f2d0"            # a line to be added
SMALL = dict(cursor="hand2", width=0)        # a row's small x / undo: a button like every other one


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
        self.text_edits = {}                 # {key in export_buildings / export_units: new text}, written on Apply
        # the list and the record side by side; the line between them is dragged to make the list wider (kept)
        pane = self.pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)
        side = ttk.Frame(pane, padding=(0, 0, 6, 0))
        pane.add(side, weight=0)
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
        self.lb = tk.Listbox(side, width=34, exportselection=False)        # (as wide as the pane gives it)
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda ev: self.show())
        self.lbl_count = ttk.Label(side, text="", foreground="#666")
        self.lbl_count.pack(anchor="w")
        # the editor's side scrolls up and down: what does not fit the window is never out of reach (a tester: the
        # voices were cut at the bottom, no scroll bar)
        from .gui_util import ScrollFrame
        scroll = ScrollFrame(pane, padding=(6, 0, 0, 0))
        pane.add(scroll, weight=1)
        right = scroll.inner
        w0 = settings.get("editor_list_width_" + kind)
        if isinstance(w0, int) and w0 > 80:
            self.after(50, lambda: self._sash_to(w0))
        pane.bind("<ButtonRelease-1>", lambda e: self._sash_kept())
        head = ttk.Frame(right)
        head.pack(fill="x")
        self.title = ttk.Label(head, text="Load a mod, then pick one on the left", font=("", 11, "bold"))
        self.title.pack(side="left")
        # the buttons on a row of their own that wraps (gui_util.flow): on a narrow window the last one was cut
        tools = ttk.Frame(right)
        tools.pack(fill="x", pady=(2, 0))
        if kind == "unit":
            # packs: units taken out with everything they need, and put into another mod
            ttk.Button(tools, text="Export pack...", command=self.export_pack).pack(side="left", padx=(0, 4))
            ttk.Button(tools, text="Import pack...", command=self.import_pack).pack(side="left", padx=(0, 12))
        b = ttk.Button(tools, text="Bring from another mod...", command=self.bring_dialog)
        b.pack(side="left", padx=(0, 6))
        from .gui_util import flow, tip
        tip(b, "Copy %s from another mod of the same game into this one, step by step: pick the mod, tick what "
                "to bring, names, who has it, %s, then Preview and write (one backup; Restore undoes it)." % (
                    "units (with their models, textures, cards and texts)" if kind == "unit" else
                    "building chains (with their levels, texts and pictures)",
                    "where they are recruited" if kind == "unit" else "the units they recruit"))
        ttk.Button(tools, text="Where it is recruited..." if kind == "unit" else "Where it can be built...",
                   command=self.where_window).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="Add line...", command=self.add_dialog).pack(side="left")
        ttk.Button(tools, text="New %s step by step..." % ("unit" if kind == "unit" else "building"),
                   command=self.copy_dialog).pack(side="left", padx=6)
        ttk.Button(tools, text="Undo all changes here", command=self.reset).pack(side="left")
        flow(tools)
        self.copy_ops = []                   # [(source, new name, details)] written on Apply
        self.pics = ttk.LabelFrame(right, text="Pictures", padding=6)
        self.pics.pack(fill="x", pady=(6, 6))
        self.links = ttk.LabelFrame(right, text="Tied to it (kept in step when you change it)", padding=(6, 2))
        self.links.pack(fill="x", pady=(0, 6))
        self.lbl_links = ttk.Label(self.links, text="", justify="left", foreground="#333", wraplength=820)
        self.lbl_links.pack(anchor="w")
        # the block's lines fold away behind a button (like the family tree): the pictures, model and voice
        # keep the room; open, the lines take the space below them (a tester: too little room in the editor)
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        self.b_lines = ttk.Button(bar, command=self.toggle_lines)
        self.b_lines.pack(side="left")
        ShortHint(bar, text="Every line of the block: the key on the left, what follows it on the right. "
                            "Changed fields turn yellow, lines to add green, lines to remove red (x on the left); "
                            "Preview, then Apply writes them (with a backup). A unit's line: the ? on its right says "
                            "what each value means, from the game's own notes.",
                  foreground="#555", wraplength=900, justify="left").pack(side="left", padx=8)
        # a window of their own, like the family tree's (a tester: folded open in the editor they still left too
        # little room): opened by the button, closed by its own close box; the editor keeps its whole height
        self._lines_open = False
        self._make_lines_window()
        self._photos = []

    def _make_lines_window(self):
        """The lines' own window (made again if something destroyed it: a closed window must never break the editor)."""
        top = self._lines_win = tk.Toplevel(self)
        top.withdraw()
        top.geometry("980x680")
        top.protocol("WM_DELETE_WINDOW", self.toggle_lines)
        # another work picked (the editor hidden): its lines window goes too
        if not getattr(self, "_unmap_bound", False):
            self._unmap_bound = True
            self.bind("<Unmap>", lambda e: self.toggle_lines() if e.widget is self and self._lines_open else None, "+")
        box = self._lines_box = ttk.Frame(top, padding=6)
        box.pack(fill="both", expand=True)
        self._lines_label()
        canvas = tk.Canvas(box, highlightthickness=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        self.form = ttk.Frame(canvas)
        self.form.bind("<Configure>", lambda ev: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        from .gui_util import scroll_y, wheel
        wheel(canvas, scroll_y(canvas))

    def _form(self):
        if not self.form.winfo_exists():
            self._lines_open = False
            self._make_lines_window()
        return self.form

    def where_window(self):
        """Where the picked unit is recruited / the picked building can be built (buildwhere.open_where)."""
        if not self.current:
            from tkinter import messagebox
            messagebox.showinfo("Where", "Pick one on the left first.")
            return None
        from .buildwhere import open_where
        return open_where(self, self.current[0])

    def _sash_to(self, x):
        try:
            self.pane.sashpos(0, x)
        except tk.TclError:
            pass

    def _sash_kept(self):
        try:
            settings.put("editor_list_width_" + self.kind, int(self.pane.sashpos(0)))
        except tk.TclError:
            pass

    def _lines_label(self):
        n = len(getattr(self, "fields", None) or ()) if self.current else 0
        self.b_lines.configure(text="Every line of the block%s%s" % (
            " (%d)" % n if n else "", " - open" if self._lines_open else "..."))
        if self._lines_open and self._lines_win.winfo_exists():
            cur = self.current[0] if isinstance(self.current, tuple) else (self.current or "")
            self._lines_win.title("Every line of %s %s" % (self.kind, cur))

    def toggle_lines(self):
        """Open the block's lines in their own window, or close it."""
        if not self._lines_win.winfo_exists():         # destroyed by something else: made again, closed
            self._form()
            self._lines_stale = True
        self._lines_open = not self._lines_open
        w = self._lines_win
        if self._lines_open:
            w.deiconify()
            w.lift()
            if getattr(self, "_lines_stale", False) and self.current:
                self.show()                      # the rows were not made while it was closed
        else:
            w.withdraw()
        self._lines_label()

    # ---- data ----
    def path(self):
        return self.mod.file("edu" if self.kind == "unit" else "edb") if self.mod else None

    def load(self, mod):
        self.mod = mod
        self.changes, self.imports, self.current, self.copy_ops = {}, [], None, []
        self.adds, self.removes, self.text_edits = [], set(), {}
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
        for w in self._form().winfo_children():
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
        from .build import faction_label
        shown = self.app.shown_names() if hasattr(self.app, "shown_names") else {}
        cultures = sorted({c for _, c in facs if c})
        if self.kind == "unit":
            vals = ["all", "mercenaries only", "no mercenaries", "general's units"]
            vals += ["faction: %s" % faction_label(n, shown.get(n)) for n, _ in facs]
            vals += ["culture: %s" % c for c in cultures]
            vals += ["category: %s" % c for c in sorted({x.get("category") for x in self.facets.values()} - {"", None})]
            vals += ["class: %s" % c for c in sorted({x.get("class") for x in self.facets.values()} - {"", None})]
        else:
            vals = ["all", "recruit units", "no recruiting"]
            vals += ["type: %s" % g for g, _ in E.CHAIN_GROUPS + (("other", ()),)]
            vals += ["faction: %s" % faction_label(n, shown.get(n)) for n, _ in facs]
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
        what = what.split(" - ")[0] if kind == "faction" else what
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
        for src, new, d in self.copy_ops:
            self.lb.insert("end", "%s  (new, %s - on Apply)" % (new, "made from nothing" if d.get("nothing") else
                                                                "from %s" % src))
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
        for w in self._form().winfo_children():
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
        self._lines_stale = not self._lines_open
        if self._lines_stale:                    # folded away: the rows are made when opened (a report: lag)
            self._lines_label()
            self.show_pictures()
            self.show_links()
            return
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
                        ttk.Button(self.form, text="x", command=lambda n=n: self.drop_add(n), **SMALL).grid(
                            row=row, column=0, padx=(0, 4))
                    row += 1
                pending.remove((at, n, lines))
        from . import edufields as EF
        from .limits import game_kind
        m2 = game_kind(self.mod) == "medieval2"
        for fd in self.fields:
            added_rows(fd.line)
            gone = fd.line in self.removes
            v = tk.StringVar(value=self.changes.get(fd.line, fd.value))
            head = ttk.Frame(self.form)
            head.grid(row=row, column=1, sticky="w", padx=(0, 8))
            ttk.Label(head, text="    " * fd.depth + fd.key, font=("", 9, "bold", "overstrike") if gone else
                      ("", 9, "bold")).pack(side="left")
            if self.kind == "unit" and EF.explain(fd.key, v.get(), m2):
                # what each value means, for what is typed there now (a modder: 'we can edit every line but do
                # not know what the numbers mean')
                hint(head, lambda fd=fd, v=v: EF.explain(fd.key, v.get(), m2), width=640).pack(side="left")
            e = tk.Entry(self.form, textvariable=v, width=90,
                         background=REMOVED if gone else CHANGED if fd.line in self.changes else theme.field(),
                         foreground="#000000" if gone or fd.line in self.changes else theme.palette()["fg"])
            e.grid(row=row, column=2, sticky="we", pady=1)
            v.trace_add("write", lambda *x, fd=fd, v=v, e=e: self.edited(fd, v.get(), e))
            if self.kind == "unit" and fd.key in unitattrs.LINES and unitattrs.for_line(fd.key) and not gone:
                ttk.Button(self.form, text="REX...",
                           command=lambda fd=fd, v=v: self.attrs_dialog(fd, v)).grid(row=row, column=3, padx=(4, 0))
            why = E.removable(self.kind, fd, self.tree, self.required())
            if why is None:
                ttk.Button(self.form, text="\u21ba" if gone else "x", command=lambda fd=fd: self.toggle_remove(fd),
                          **SMALL).grid(row=row, column=0, padx=(0, 4))
            row += 1
        added_rows(b + 1)
        self._lines_label()
        self.show_pictures()
        self.show_links()

    def attrs_dialog(self, fd, var):
        """Tick the words REX knows for this line (attributes, morale, terrain, weapons);
        the line's value changes like a typed edit."""
        from .limits import faction_limit
        w = tk.Toplevel(self)
        w.title("%s: what REX adds" % fd.key)
        w.transient(self)
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
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
        self.changes, self.imports, self.copy_ops, self.text_edits = {}, [], [], {}
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
            lv_txt.append("%s: %s" % (lv["name"], "everyone" if names is None or "all" in names else self._short(names, 3)))
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
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
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
            if not self._lines_open:
                self.toggle_lines()                  # the new line shows (green) among the others
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
        from .units import owner_factions
        return owner_factions(self.mod, self.value("ownership").replace(",", " ").split())

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
            have = pending or card_path(self.mod, facs[0] if facs else "", dic, info, owners=facs,
                                        mercenary="mercenary_unit" in self.value("attributes").replace(",", " ").split())
            self._thumb(box, have).grid(row=0, column=0, rowspan=3)
            need = E.unit_picture_need(self.mod, info)
            ttk.Label(box, text=label, font=("", 9, "bold")).grid(row=0, column=1, sticky="w", padx=6)
            ttk.Label(box, foreground="#555", justify="left", wraplength=330, text=(
                "needs %d x %d, %d-bit TGA (as this mod's own)" % need if need else "size: as you like") +
                "\nPNG / JPG / TGA are converted\ngoes to %s for %s" % (
                    "ui/unit_info/<faction>/%s_info.tga" % dic if info else "ui/units/<faction>/#%s.tga" % dic,
                    ", ".join(facs[:4]) + (" and %d more" % (len(facs) - 4) if len(facs) > 4 else "")) +
                ("\nnew: %s (not written yet)" % os.path.basename(pending) if pending else "")).grid(
                row=1, column=1, sticky="w", padx=6)
            bb = ttk.Frame(box)
            bb.grid(row=2, column=1, sticky="w", padx=6)
            ttk.Button(bb, text="Import...", command=lambda t=targets, n=need, l=label: self.import_pic(t, n, l)).pack(
                side="left")
            if have and not pending:
                ttk.Button(bb, text="Save a copy...", command=lambda h=have, l=label: save_copy(
                    self, h, "the %s" % l.lower())).pack(side="left", padx=4)
        # the battle model beside the two pictures; the voice a third column when the window is wide enough (a
        # tester: the voices were cut at the bottom while the right half stood empty), else under the model
        self._unit_models(0, 1)
        self._unit_voice(1, 1)
        if not getattr(self, "_voice_bound", False):          # once: the pictures frame lives as long as the editor
            self.pics.bind("<Configure>", lambda e: self._place_voice(), add="+")
            self._voice_bound = True
        self.after_idle(self._place_voice)

    def _place_voice(self):
        if not self.pics.winfo_exists():                      # the editor closed before the idle call came
            return
        voice = next((w for w in self.pics.grid_slaves() if isinstance(w, ttk.LabelFrame)
                      and str(w.cget("text")).startswith("Voice")), None)
        model = next((w for w in self.pics.grid_slaves() if isinstance(w, ttk.LabelFrame)
                      and str(w.cget("text")).startswith("Battle model")), None)
        if voice is None or model is None:
            return
        cols = [w for w in self.pics.grid_slaves(column=0)]
        need = max([w.winfo_reqwidth() for w in cols] or [0]) + model.winfo_reqwidth() + voice.winfo_reqwidth() + 40
        wide = self.pics.winfo_width() >= need
        at = voice.grid_info()
        if wide and int(at.get("column", 1)) != 2:
            voice.grid(row=0, column=2, rowspan=2, sticky="nwe", pady=(4, 0), padx=(12, 0))
            model.grid(rowspan=2)
        elif not wide and int(at.get("column", 1)) != 1:
            voice.grid(row=1, column=1, rowspan=1, sticky="nwe", pady=(4, 0), padx=(12, 0))
            model.grid(rowspan=1)

    # ---- battle models ----
    def _model_catalogue(self, mod=None):
        """models.catalogue of mod (this one by default), kept while its model files are unchanged."""
        from . import models as MO
        from . import modeldb as MDB
        mod = mod or self.mod
        src, _ = MDB.find(mod) if MO.game_kind(mod) == "medieval2" else (None, None)
        stamp = tuple(os.path.getmtime(p) if p and os.path.exists(p) else 0
                      for p in (mod.find(MO.TEXT_FILE), src, mod.file("edu")))
        cache = self.__dict__.setdefault("_models_cache", {})
        key = os.path.normcase(os.path.abspath(mod.data))
        if key not in cache or cache[key][0] != stamp:
            cache[key] = (stamp, MO.catalogue(mod))
        return cache[key][1]

    def _texture_thumb(self, parent, mod, rel, size=(72, 72)):
        """A texture as a small picture (cached: a Medieval II texture takes a moment to decode)."""
        from PIL import ImageTk
        from . import models as MO
        cache = self.__dict__.setdefault("_tex_cache", {})
        k = (mod.data, rel, size)
        if k not in cache:
            im = None
            try:
                im = MO.texture_image(mod, rel) if rel else None
                if im is not None:
                    im.thumbnail(size)
            except Exception:
                im = None
            cache[k] = im
        im = cache[k]
        if im is None:
            return ttk.Label(parent, text="(no texture\nfile here)", width=11, relief="sunken", anchor="center")
        ph = ImageTk.PhotoImage(im)
        self._photos.append(ph)
        return tk.Label(parent, image=ph, relief="sunken")

    def _unit_lines(self):
        name, a, b = self.current
        f = self.mod.load(self.path())
        return [f.text(i) for i in range(a, b)]

    def _unit_models(self, row, column=0):
        """The unit's battle models: each soldier / officer line's model, how it sits, a texture, Replace model..."""
        from . import models as MO
        box = ttk.LabelFrame(self.pics, text="Battle model", padding=6)
        box.grid(row=row, column=column, sticky="nwe", pady=(4, 0), padx=(12 if column else 0, 0))
        try:
            cat = self._model_catalogue()
            lines = self._unit_lines()
        except Exception as e:
            ttk.Label(box, text="cannot read the battle models: %s" % e, foreground="#a33").grid(sticky="w")
            return
        if MO.is_ship(lines):
            ttk.Label(box, foreground="#555", wraplength=380, justify="left", text=(
                "A ship: the game fights sea battles by itself (auto-resolve), so a ship has no battle model. Its "
                "soldier line (%s) is only there because the file's form asks for one." % (
                    ", ".join(m for _, _, m in MO.unit_slots(lines)) or "none"))).grid(sticky="w")
            return
        seat = MO.unit_seat(self.mod, lines)
        slots = MO.unit_slots(lines)
        if not slots:
            ttk.Label(box, text="no soldier line - nothing to show").grid(sticky="w")
            return
        facs = self._factions_of()
        kind, mmodel = MO.unit_mount(self.mod, lines)
        minfo = cat.get((mmodel or "").lower()) if kind else None
        mount = (minfo, kind) if minfo is not None else None
        chariot = MO.chariot_of(self.mod, lines)          # Rome: a chariot / scorpion cart has lods, no model line
        if chariot:
            chariot["horse_info"] = cat.get((chariot["horse"] or "").lower())
            minfo = chariot["info"]
            mount = (minfo, kind, chariot)
            mmodel = ", ".join(m.split("/")[-1] for m in minfo.meshes[:1]) or None
        engine = MO.engine_of(self.mod, lines)
        for r, (key, idx, model) in enumerate(slots):
            info = cat.get(model.lower())
            tex = None
            if info:
                tex = next((info.textures[f] for f in facs if f in info.textures), None) or \
                    next(iter(info.textures.values()), None)
            self._texture_thumb(box, self.mod, tex).grid(row=r, column=0, rowspan=1, sticky="nw", pady=2)
            txt = "%s: %s" % ("Soldiers" if key == "soldier" else "Officer %d" % (idx + 1), model)
            if info is None:
                detail, colour = "not in this mod's battle models - the game cannot show the unit", "#a33"
            else:
                probs = MO.fit_problems(self.mod, info, seat)
                missing = [f for f in facs if f not in info.textures and "" not in info.textures]
                detail = "the model is made %s; the unit is %s" % (info.seat_words(), MO.SEAT_WORDS.get(seat, seat))
                detail += "\ntextures for %d faction(s)%s" % (
                    len([f for f in info.textures if f]) or 1,
                    ("; none for %s" % ", ".join(missing[:4]) + (" ..." if len(missing) > 4 else "")) if missing else "")
                if probs:
                    detail += "\n" + "\n".join(("WARNING: " if s else "") + m for s, m in probs)
                colour = "#a33" if any(s for s, _ in probs) else ("#b60" if probs else "#555")
            cell = ttk.Frame(box)
            cell.grid(row=r, column=1, sticky="nw", padx=6)
            ttk.Label(cell, text=txt, font=("", 9, "bold")).pack(anchor="w")
            ttk.Label(cell, text=detail, foreground=colour, justify="left", wraplength=300).pack(anchor="w")
            bar = ttk.Frame(cell)
            bar.pack(anchor="w", pady=(2, 0))
            ttk.Button(bar, text="Replace model...",
                       command=lambda k=key, i=idx, m=model: self.replace_model(k, i, m)).pack(side="left")
            if info is not None:
                ttk.Button(bar, text="View in 3D...", command=lambda i=info, k=key: self.view_model(
                    i, mount=mount if k == "soldier" else None, unit=k == "soldier")).pack(side="left", padx=4)
                ttk.Button(bar, text="Save its files...", command=lambda i=info: self.save_model_files(i)).pack(
                    side="left")
                ttk.Button(bar, text="Your own files...", command=lambda k=key, i=idx, m=model: self.own_files(
                    k, i, m)).pack(side="left", padx=(4, 0))
        # the mount (horse, camel, elephant ...): its own model, from descr_mount.txt
        if kind:
            r = len(slots)
            info = minfo
            tex = next(iter(info.textures.values()), None) if info and info.textures else None
            self._texture_thumb(box, self.mod, tex).grid(row=r, column=0, sticky="nw", pady=2)
            cell = ttk.Frame(box)
            cell.grid(row=r, column=1, sticky="nw", padx=6)
            ttk.Label(cell, text="Mount: %s" % kind, font=("", 9, "bold")).pack(anchor="w")
            ttk.Label(cell, foreground="#555" if info else "#a33", justify="left", wraplength=300, text=(
                "its model %s (descr_mount.txt)" % mmodel if info else
                "descr_mount.txt names the model %s - not in this mod's battle models" % mmodel if mmodel else
                "no such mount in descr_mount.txt")).pack(anchor="w")
            if info is not None:
                bar = ttk.Frame(cell)
                bar.pack(anchor="w", pady=(2, 0))
                ttk.Button(bar, text="View in 3D...", command=lambda i=info: self.view_model(i)).pack(side="left")
                ttk.Button(bar, text="Save its files...", command=lambda i=info: self.save_model_files(i)).pack(
                    side="left", padx=4)
        # the siege engine its crew works (Rome: descr_engines.txt) - its own model, shown in 3D
        if engine is not None:
            r = len(slots) + (1 if kind else 0)
            cell = ttk.Frame(box)
            cell.grid(row=r, column=1, sticky="nw", padx=6)
            ttk.Label(cell, text="Siege engine: %s" % engine.name, font=("", 9, "bold")).pack(anchor="w")
            ttk.Label(cell, foreground="#555", justify="left", wraplength=300, text="its models %s (descr_engines.txt)"
                      % ", ".join(m.split("/")[-1] for m in engine.meshes[:2])).pack(anchor="w")
            ttk.Button(cell, text="View in 3D...", command=lambda i=engine: self.view_model(i)).pack(
                anchor="w", pady=(2, 0))

    def save_model_files(self, info):
        """The model's files (meshes, textures) copied into a folder the user picks, in their data/ folders - a
        copy to keep or to work on before Replace model."""
        import shutil
        from tkinter import filedialog
        from . import models as MO
        files = MO.model_files(self.mod, info)
        if not files:
            messagebox.showerror("Save its files", "No file of %s was found on disk." % info.name, parent=self)
            return
        out = filedialog.askdirectory(parent=self, title="A folder for the files of %s" % info.name)
        if not out:
            return
        if os.path.normcase(os.path.abspath(out)).startswith(os.path.normcase(os.path.abspath(self.mod.data))):
            messagebox.showerror("Save its files", "Pick a folder outside the mod - this saves a copy.", parent=self)
            return
        root = os.path.join(out, "%s_files" % info.name.replace(" ", "_"), "data")
        try:
            for rel, path in files:
                dst = os.path.join(root, *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(path, dst)
        except OSError as e:
            messagebox.showerror("Save its files", str(e), parent=self)
            return
        from . import log
        log.write("Saved %d file(s) of %s to %s" % (len(files), info.name, root))
        messagebox.showinfo("Save its files", "%d file(s) of %s saved in\n%s\n\n%s" % (
            len(files), info.name, root, "\n".join(rel for rel, _ in files[:12]) +
            ("\n..." if len(files) > 12 else "")), parent=self)

    def save_sounds(self, files, what):
        """A set of sounds (from the game's packs or the mod's folders) saved into a folder the user picks."""
        from tkinter import filedialog
        from . import sounds as SN
        out = filedialog.askdirectory(parent=self, title="A folder for %s" % what)
        if not out:
            return
        index, _ = self._voice_data()
        saved, missing = 0, 0
        for rel in files:
            data = SN.sound_bytes(self.mod, rel, index)
            if data is None:
                missing += 1
                continue
            with open(os.path.join(out, os.path.basename(rel.replace("\\", "/"))), "wb") as fh:
                fh.write(data)
            saved += 1
        self.app.status.set("Saved %d sound(s) of %s in %s%s" % (saved, what, out, (
            " (%d in no pack and not on disk)" % missing) if missing else ""))

    # ---- voice ----
    def _voice_data(self):
        """(pack index, voice events) of this mod, kept while the voice file and the packs are unchanged."""
        from . import sounds as SN
        from .textio import TextFile
        path = SN.voice_file(self.mod)
        idxs = [os.path.join(d, n) for d in SN.sound_dirs(self.mod) for n in os.listdir(d) if n.lower().endswith(".idx")]
        stamp = tuple(os.path.getmtime(p) for p in [path] + idxs if p and os.path.exists(p))
        got = self.__dict__.get("_voice_cache")
        if not got or got[0] != (self.mod.data, stamp):
            events = SN.voice_events(TextFile.load(path)) if path else []
            got = self._voice_cache = ((self.mod.data, stamp), SN.pack_index(self.mod), events)
        return got[1], got[2]

    def _unit_voice(self, row, column=0):
        """What the unit says in battle, for each accent (Medieval II) / culture (Rome) of its owners: its voice class,
        its own name call (Play, Put in my own...), and its orders (Play)."""
        from . import sounds as SN
        box = ttk.LabelFrame(self.pics, text="Voice in battle", padding=6)
        box.grid(row=row, column=column, sticky="nwe", pady=(4, 0), padx=(12 if column else 0, 0))
        unit = self.current[0]
        vt = self.value("voice_type").split(";")[0].strip()
        from . import models as MO
        try:
            ship = MO.is_ship(self._unit_lines())
        except Exception:
            ship = False
        if ship:
            ttk.Label(box, foreground="#555", wraplength=320, justify="left", text=(
                "A ship: it never stands on a battlefield, so it says nothing in battle. Its voice_type line (%s) "
                "is only there because the file's form asks for one." % (vt or "none"))).grid(sticky="w")
            return
        if not SN.voice_file(self.mod):
            ttk.Label(box, text="this mod has no %s - no unit voices to show" % SN.VOICE_FILE).grid(sticky="w")
            return
        if not vt:
            ttk.Label(box, foreground="#b60", wraplength=320, justify="left", text=(
                "no voice_type line - the unit says nothing. Add a voice_type line (Add line...) to give it a "
                "voice.")).grid(sticky="w")
            return
        try:
            index, events = self._voice_data()
        except Exception as e:
            ttk.Label(box, text="cannot read the voices: %s" % e, foreground="#a33").grid(sticky="w")
            return
        facs = self._factions_of()
        r = 0
        for uv in SN.unit_voices(self.mod, events, unit, vt, facs):
            who = ", ".join(uv.factions[:4]) + (" ..." if len(uv.factions) > 4 else "")
            if uv.key is None:
                ttk.Label(box, foreground="#a33", wraplength=320, justify="left", text=(
                    "%s: no accent in %s - these factions have no voice in battle. Add them to an accent "
                    "there." % (who, SN.ACCENTS_FILE))).grid(row=r, column=0, sticky="w")
                r += 1
                continue
            head = ("%s accent" if SN.accents(self.mod) else "culture %s") % (uv.label or uv.key)
            ttk.Label(box, text="%s (%s), voice %s" % (head, who, vt), font=("", 9, "bold")).grid(
                row=r, column=0, sticky="w", pady=(4 if r else 0, 0))
            r += 1
            if not uv.known_class:
                ttk.Label(box, foreground="#a33", wraplength=320, justify="left", text=(
                    "this voice file has no class %s here - the unit stays silent. Change the voice_type line above "
                    "to one of: %s." % (vt, ", ".join(uv.classes)))).grid(row=r, column=0, sticky="w")
                r += 1
                continue
            line = ttk.Frame(box)
            line.grid(row=r, column=0, sticky="w")
            r += 1
            nc = uv.name_call
            ttk.Label(line, text=("Name call: %d sound(s)" % len(nc.files)) if nc else
                      "Name call: none of its own (it says only its orders)",
                      foreground="#555" if nc else "#b60").pack(side="left")
            if nc:
                ttk.Button(line, text="Play",
                           command=lambda fs=nc.files: self.play_sound(fs)).pack(side="left", padx=4)
                ttk.Button(line, text="Save...", command=lambda fs=nc.files, u=unit: self.save_sounds(
                    fs, "the name call of %s" % u)).pack(side="left", padx=(0, 4))
            ttk.Button(line, text="Put in my own...",
                       command=lambda uv=uv: self.own_name_call(uv)).pack(side="left", padx=(4 if not nc else 0, 0))
            orders = [ev for ev in uv.orders if ev.files]
            if orders:
                line = ttk.Frame(box)
                line.grid(row=r, column=0, sticky="w", pady=(2, 0))
                r += 1
                ttk.Label(line, text="Orders (%d):" % len(orders), foreground="#555").pack(side="left")
                names = [ev.vocal for ev in orders]
                v = tk.StringVar(value=names[0])
                ttk.Combobox(line, textvariable=v, values=names, state="readonly", width=30).pack(side="left", padx=4)
                ttk.Button(line, text="Play", command=lambda v=v, o=orders: self.play_sound(
                    next(ev.files for ev in o if ev.vocal == v.get()))).pack(side="left")
        ttk.Label(box, foreground="#555", wraplength=320, justify="left", text=(
            "The voice class is the voice_type line above (%s)." % ", ".join(
                sorted({ev.cls for ev in events}, key=str.lower)))).grid(row=r, column=0, sticky="w", pady=(4, 0))

    def play_sound(self, files):
        """Play the next of a set of sounds (each click the next one, as the game picks among them)."""
        from . import sounds as SN
        if not files:
            return
        k = self.__dict__.setdefault("_play_turn", {})
        i = k.get(tuple(files), 0) % len(files)
        k[tuple(files)] = i + 1
        index, _ = self._voice_data()
        rel = files[i]
        data = SN.sound_bytes(self.mod, rel, index)
        if data is None:
            messagebox.showerror("Play", "%s is in no sound pack and not on disk - the game has nothing to play "
                                         "there. Put in your own sound for it." % rel, parent=self)
            return
        try:
            why = SN.play(data, rel)
        except Exception as e:
            why = str(e)
        self.app.status.set("Playing %s (%d of %d)%s" % (os.path.basename(rel), i + 1, len(files),
                                                        (" - " + why) if why else ""))

    def own_name_call(self, uv):
        """The unit's name call for one accent / culture from the user's own .wav files: Preview, then written with a
        backup (Restore undoes it)."""
        from . import sounds as SN
        from . import log
        unit = self.current[0]
        paths = filedialog.askopenfilenames(parent=self, title="Sounds for the name call of %s (%s)" % (unit, uv.key),
                                            filetypes=[("wav sounds", "*.wav"), ("all files", "*.*")])
        if not paths:
            return
        plan = Plan(self.mod, "voice", "unit_voice", {})
        try:
            SN.set_name_call(plan, unit, uv.key, uv.cls, list(paths))
        except Exception as e:
            messagebox.showerror("Name call", "%s\n\nNothing was written." % e, parent=self)
            return
        warns = "\n".join(x for _, x in plan.warnings)
        if not ask("Name call", (
                "%s (%s, class %s) will say your %d sound(s) when selected.\n\n%s%sWrite %d file(s)? A backup is made "
                "first (Restore undoes it).\n\nThen start the game: it builds data/sounds/events.dat again on the "
                "first start (that start takes a little longer)." % (
                    unit, uv.key, uv.cls, len(paths), plan.report(), ("\n\n" + warns + "\n\n") if warns else "\n\n",
                    len(plan.changed_files()))), parent=self, yes='Write it in', no='Cancel'):
            return
        bdir = plan.apply()
        log.write("Name call of %s (%s, %s) replaced (backup %s)\n%s" % (unit, uv.key, uv.cls, bdir, plan.report()))
        self.__dict__.pop("_voice_cache", None)
        self.show_pictures()
        self.app.status.set("%s has its own name call for %s now (backup %s) - start the game to hear it." % (
            unit, uv.key, bdir))

    def view_model(self, info, mod=None, mount=None, unit=False):
        """View in 3D...; unit: the unit's soldier model - Make a card... / Make a picture... there give the unit on
        show its card / description picture from the view."""
        from .gui_meshview import ModelViewer
        ModelViewer(self, mod or self.mod, info, self._factions_of(), mount=mount,
                    make=self._picture_maker() if unit and mod is None else None)

    def _picture_maker(self):
        """{'unit', 'need', 'write'} for View in 3D's Make a card... / Make a picture... - the unit on show now
        (its dictionary name and owners taken at once: the editor may show another unit by the time it is used);
        the picture waits for Apply as an imported one."""
        if self.kind != "unit" or not self.current:
            return None
        dic, facs, unit = self.value("dictionary"), self._factions_of(), self.current[0]
        if not dic:
            return None
        need = {False: E.unit_picture_need(self.mod), True: E.unit_picture_need(self.mod, True)}

        def write(info, picture):
            targets = E.unit_picture_targets(self.mod, dic, facs, info)
            if not targets:
                raise ValueError("No faction owns %s - there is no folder for its %s." % (
                    unit, "picture" if info else "card"))
            from . import log
            import time
            folder = os.path.join(log.logs_dir() or os.path.expanduser("~"), "made_pictures")
            os.makedirs(folder, exist_ok=True)
            src = os.path.join(folder, "%s_%s_%s.png" % (dic, "info" if info else "card",
                                                         time.strftime("%Y%m%d_%H%M%S")))
            picture.save(src)
            label = "Picture in the description" if info else "Unit card"
            self.imports = [(s, t, z) for s, t, z in self.imports if not set(t) & set(targets)]
            self.imports.append((src, list(targets), picture.size))
            self.app.status.set("%s of %s made from its 3D model, for %d place(s) - Preview, then Apply." % (
                label, unit, len(targets)))
            self.show_pictures()
        return {"unit": unit, "need": need, "write": write}

    def replace_model(self, key, idx, current):
        """Another battle model for this unit's soldiers (or an officer): from this mod or another mod folder of the
        same game (it comes with every file it names), Preview, then written with a backup like every change."""
        from tkinter import filedialog
        from . import models as MO
        from .moddata import ModData
        from .plan import Plan
        unit = self.current[0]
        what = "soldiers" if key == "soldier" else "officer %d" % (idx + 1)
        if self.pending() and not ask(
                "Replace model", "The unit editor holds changes not written yet; replacing the model writes "
                                 "export_descr_unit.txt, so they would be dropped. Go on?", parent=self, yes='Replace, drop them', no='Stay', danger=True):
            return
        lines = self._unit_lines()
        seat = MO.unit_seat(self.mod, lines)
        facs = self._factions_of()
        st = {"mod": self.mod, "cat": self._model_catalogue(), "names": []}
        w = tk.Toplevel(self)
        w.title("Replace battle model - %s, %s" % (unit, what))
        w.transient(self)
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
        ttk.Label(frm, justify="left", wraplength=640, text=(
            "%s of %s use %s now. Pick the model to use instead. The unit is %s: a model made to sit otherwise is "
            "marked. Every faction that owns the unit gets a texture on the model where it has none (a copy of "
            "the mercenaries' or the first one's)." % (what.capitalize(), unit, current,
                                                       MO.SEAT_WORDS.get(seat, seat)))).grid(
            row=0, column=0, columnspan=3, sticky="w")
        src_bar = ttk.Frame(frm)
        src_bar.grid(row=1, column=0, columnspan=3, sticky="we", pady=(8, 4))
        ttk.Label(src_bar, text="Take it from:").pack(side="left")
        v_src = tk.StringVar(value="this mod")
        lbl_src = ttk.Label(src_bar, textvariable=v_src, foreground="#555")
        lbl_src.pack(side="left", padx=6)

        def fill(*_):
            q = v_find.get().strip().lower()
            lb.delete(0, "end")
            st["names"] = []
            for k in sorted(st["cat"]):
                info = st["cat"][k]
                if q and q not in k:
                    continue
                fits = not [p for p in MO.fit_problems(self.mod, info, seat) if "made" in p[1]]
                st["names"].append(info.name)
                lb.insert("end", "%s%s   (%s)" % ("" if fits else "! ", info.name, info.seat_words()))
            lbl_n.configure(text="%d model(s)" % len(st["names"]))

        def other():
            path = filedialog.askdirectory(parent=w, title="The other mod's data folder (or the mod folder)")
            if not path:
                return
            data = path if os.path.isdir(os.path.join(path, "unit_models")) or _ci(path, "descr_sm_factions.txt") \
                else (_ci(path, "data") or path)
            try:
                m = ModData(data)
                if MO.game_kind(m) != MO.game_kind(self.mod):
                    raise ValueError("that mod is of the other game - models go between mods of one game")
                cat = self._model_catalogue(m)
            except Exception as e:
                messagebox.showerror("Replace model", str(e), parent=w)
                return
            st.update(mod=m, cat=cat)
            v_src.set(data)
            fill()

        def mine():
            st.update(mod=self.mod, cat=self._model_catalogue())
            v_src.set("this mod")
            fill()
        ttk.Button(src_bar, text="Another mod...", command=other).pack(side="right")
        ttk.Button(src_bar, text="This mod", command=mine).pack(side="right", padx=4)
        fbar = ttk.Frame(frm)
        fbar.grid(row=2, column=0, sticky="we")
        ttk.Label(fbar, text="Find").pack(side="left")
        v_find = tk.StringVar()
        ttk.Entry(fbar, textvariable=v_find, width=24).pack(side="left", padx=4)
        lbl_n = ttk.Label(fbar, foreground="#555")
        lbl_n.pack(side="left", padx=4)
        v_find.trace_add("write", fill)
        lb = tk.Listbox(frm, height=18, width=46, exportselection=False)
        lb.grid(row=3, column=0, sticky="nsew")
        sb = ttk.Scrollbar(frm, orient="vertical", command=lb.yview)
        sb.grid(row=3, column=1, sticky="ns")
        lb.configure(yscrollcommand=sb.set)
        side = ttk.Frame(frm, padding=(10, 0))
        side.grid(row=3, column=2, sticky="nw")
        frm.rowconfigure(3, weight=1)
        frm.columnconfigure(0, weight=1)

        def picked():
            sel = lb.curselection()
            return st["names"][sel[0]] if sel and sel[0] < len(st["names"]) else None

        def show(*_):
            for c in side.winfo_children():
                c.destroy()
            name = picked()
            if not name:
                return
            info = st["cat"][name.lower()]
            tex = next((info.textures[f] for f in facs if f in info.textures), None) or \
                next(iter(info.textures.values()), None)
            self._texture_thumb(side, st["mod"], tex, size=(160, 160)).pack(anchor="w")
            ttk.Button(side, text="View in 3D...", command=lambda: self.view_model(info, st["mod"])).pack(
                anchor="w", pady=(4, 0))
            have = [f for f in info.textures if f]
            missing = [f for f in facs if f not in info.textures and "" not in info.textures]
            ttk.Label(side, text=name, font=("", 10, "bold")).pack(anchor="w", pady=(6, 0))
            ttk.Label(side, justify="left", wraplength=300, text=(
                "made %s\ntextures: %s%s%s" % (
                    info.seat_words(), ", ".join(have[:8]) + (" and %d more" % (len(have) - 8) if len(have) > 8 else "")
                    if have else "one for everyone",
                    ("\ngets a texture copy for: %s" % ", ".join(missing)) if missing else "",
                    "\ncomes with every file it names (meshes, textures, sprites)" if st["mod"] is not self.mod
                    else ""))).pack(anchor="w")
            for serious, msg in MO.fit_problems(self.mod, info, seat):
                ttk.Label(side, text=("WARNING: " if serious else "") + msg, foreground="#a33" if serious else "#b60",
                          justify="left", wraplength=300).pack(anchor="w", pady=(4, 0))
        lb.bind("<<ListboxSelect>>", show)

        def make():
            name = picked()
            if not name:
                raise ValueError("pick a model in the list first")
            plan = Plan(self.mod, "model", "unit_model", {})
            MO.replace(plan, unit, key, idx, name, src_mod=None if st["mod"] is self.mod else st["mod"])
            return plan

        def preview():
            try:
                plan = make()
            except Exception as e:
                messagebox.showerror("Replace model", str(e), parent=w)
                return
            self.app.show_text("Replace model - preview (nothing written)", plan.report())

        def write():
            try:
                plan = make()
            except Exception as e:
                messagebox.showerror("Replace model", str(e), parent=w)
                return
            serious = [x for _, x in plan.warnings if "WARNING" in x]
            if serious and not ask("Replace model", "%sWrite %d file(s)? A backup is made first (Restore undoes "
                                                        "it)." % (("\n".join(serious) + "\n\n") if serious else "",
                                                                  len(plan.changed_files())),
                                       icon="warning" if serious else "question", parent=w, yes='Write it in', no='Cancel'):
                return
            bdir = plan.apply()
            from . import log
            log.write("Battle model of %s (%s) replaced (backup %s)\n%s" % (unit, what, bdir, plan.report()))
            w.destroy()
            self.app.load()
            self.app.status.set("%s: %s now use another battle model (backup %s)." % (unit, what, bdir))
        bar = ttk.Frame(frm)
        bar.grid(row=4, column=0, columnspan=3, sticky="e", pady=(8, 0))
        ttk.Button(bar, text="Preview", command=preview).pack(side="left")
        ttk.Button(bar, text="Write it in", command=write).pack(side="left", padx=6)
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")
        fill()
        if current.lower() in st["cat"]:
            i = st["names"].index(st["cat"][current.lower()].name)
            lb.selection_set(i)
            lb.see(i)
            show()

    def own_files(self, key, idx, current):
        """The modder's own files in place of the model's (made in another program): a texture per faction or
        one for every faction, Medieval II's weapons and shields texture, the model file itself (Rome .cas,
        Medieval II .mesh; several = detail levels, closest first). The editor converts the pictures, names and
        places every file, writes the lines; Preview first, a backup, Restore takes it all out (models.own_files)."""
        from . import models as MO
        unit = self.current[0]
        what = "soldiers" if key == "soldier" else "officer %d" % (idx + 1)
        info = self._model_catalogue().get(current.lower())
        if info is None:
            messagebox.showerror("Your own files", "%s is not in this mod's battle models." % current, parent=self)
            return
        if self.pending() and not ask(
                "Your own files", "The unit editor holds changes not written yet; this writes "
                                  "export_descr_unit.txt, so they would be dropped. Go on?", parent=self,
                yes="Go on, drop them", no="Stay", danger=True):
            return
        m2 = MO.game_kind(self.mod) == "medieval2"
        ext, word = MO.mesh_kind(self.mod)
        others = sorted({u for u, k, i in MO.users_of(self.mod, info.name) if (u, k, i) != (unit, key, idx)})
        st = {"tex": {}, "attach": None, "meshes": []}
        w = tk.Toplevel(self)
        w.title("Your own files - %s, %s" % (unit, what))
        w.transient(self)
        frm = scroll_body(w, 10)
        ttk.Label(frm, justify="left", wraplength=620, text=(
            "Put files you made in another program in place of the model's: the editor turns a picture into the "
            "game's texture form, names and places every file and writes the lines. Nothing is drawn here.")).grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frm, justify="left", wraplength=620, foreground="#555", text=(
            "%s of %s use the model %s.%s" % (
                what.capitalize(), unit, info.name,
                (" %d other unit(s) use it too (%s): %s gets a model of its own - a copy of %s - so they keep "
                 "their look." % (len(others), ", ".join(others[:3]) + (" ..." if len(others) > 3 else ""), unit,
                                  info.name)) if others else
                " No other unit uses it; a model file of yours makes a copy of it for this unit.")
            )).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 8))
        pics = "*" + " *".join(MO.PICTURES)

        def pick_picture(target, label):
            path = filedialog.askopenfilename(parent=w, title="A picture for the texture", filetypes=[
                ("Pictures", pics), ("Every file", "*.*")])
            if not path:
                return
            if target == "attach":
                st["attach"] = path
            else:
                st["tex"][target] = path
            label.configure(text=os.path.basename(path))

        def take_back(target, label):
            if target == "attach":
                st["attach"] = None
            else:
                st["tex"].pop(target, None)
            label.configure(text="(as it is)")
        tex = ttk.LabelFrame(frm, text="Texture (the picture wrapped round the model)", padding=6)
        tex.grid(row=2, column=0, columnspan=3, sticky="we")
        facs = [f for f in info.textures if f] or [""]
        rows = [("*", "Every faction")] + [(f, f) for f in facs if f]
        for r, (target, text) in enumerate(rows):
            ttk.Label(tex, text=text).grid(row=r, column=0, sticky="w")
            lbl = ttk.Label(tex, text="(as it is)", foreground="#555")
            lbl.grid(row=r, column=2, sticky="w", padx=6)
            b = ttk.Button(tex, text="Pick a picture...", command=lambda t=target, lb=lbl: pick_picture(t, lb))
            b.grid(row=r, column=1, sticky="w", padx=6, pady=1)
            for wd in (b, lbl):
                wd.bind("<Button-3>", lambda e, t=target, lb=lbl: take_back(t, lb))
        ttk.Label(tex, foreground="#555", wraplength=600, justify="left", text=(
            "PNG, TGA, DDS%s or JPG; sides of 64, 128, 256, 512, 1024... (another size is made the old texture's). "
            "'Every faction' fills the factions you leave as they are. Right click: as it is." % (
                ", .texture" if m2 else ""))).grid(row=len(rows), column=0, columnspan=3, sticky="w", pady=(4, 0))
        r0 = 3
        if m2:
            att = ttk.LabelFrame(frm, text="Weapons and shields texture (Medieval II)", padding=6)
            att.grid(row=r0, column=0, columnspan=3, sticky="we", pady=(6, 0))
            lbl = ttk.Label(att, text="(as it is)", foreground="#555")
            ttk.Button(att, text="Pick a picture...", command=lambda lb=lbl: pick_picture("attach", lb)).grid(
                row=0, column=0, sticky="w")
            lbl.grid(row=0, column=1, sticky="w", padx=6)
            lbl.bind("<Button-3>", lambda e, lb=lbl: take_back("attach", lb))
            r0 += 1
        mdl = ttk.LabelFrame(frm, text="The model itself (%s)" % word, padding=6)
        mdl.grid(row=r0, column=0, columnspan=3, sticky="we", pady=(6, 0))
        v_meshes = tk.StringVar(value="(as it is: %s%s)" % (", ".join(
            m.replace("\\", "/").split("/")[-1] for m in info.meshes[:2]), " ..." if len(info.meshes) > 2 else ""))

        def pick_meshes():
            paths = filedialog.askopenfilenames(parent=w, title="Your %s file(s), the closest detail first" % word,
                                                filetypes=[(word, "*" + ext), ("Every file", "*.*")])
            if not paths:
                return
            try:
                for p in paths:
                    MO.check_mesh(self.mod, p)
            except ValueError as e:
                messagebox.showerror("Your own files", str(e), parent=w)
                return
            st["meshes"] = list(paths)
            v_meshes.set(", ".join(os.path.basename(p) for p in paths))
        ttk.Button(mdl, text="Pick the model file(s)...", command=pick_meshes).grid(row=0, column=0, sticky="w")
        ttk.Label(mdl, textvariable=v_meshes, foreground="#555", wraplength=420, justify="left").grid(
            row=0, column=1, sticky="w", padx=6)
        ttk.Label(mdl, foreground="#555", wraplength=600, justify="left", text=(
            "Several files = its detail levels, the closest first (they take the old levels' distances). It keeps "
            "the old model's skeleton, so it must be made for it (%s)." % ", ".join(info.skeletons[:2]))).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        nbar = ttk.Frame(frm)
        nbar.grid(row=r0 + 1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(nbar, text="Name of the unit's own model (when one is made)").pack(side="left")
        dic = (self.value("dictionary") or unit).split()[0].lower() if (self.value("dictionary") or unit).split() \
            else unit.lower()
        v_name = tk.StringVar(value=dic if dic != info.name.lower() else info.name + "_own")
        ttk.Entry(nbar, textvariable=v_name, width=30).pack(side="left", padx=6)

        def make():
            plan = Plan(self.mod, "model", "unit_model", {})
            MO.own_files(plan, unit, key, idx, textures=dict(st["tex"]), attach=st["attach"],
                         meshes=st["meshes"], name=v_name.get())
            return plan

        def preview():
            try:
                plan = make()
            except Exception as e:
                messagebox.showerror("Your own files", str(e), parent=w)
                return
            self.app.show_text("Your own files - preview (nothing written)", plan.report())

        def write():
            try:
                plan = make()
            except Exception as e:
                messagebox.showerror("Your own files", str(e), parent=w)
                return
            bdir = plan.apply()
            from . import log
            log.write("Own files for the battle model of %s (%s) (backup %s)\n%s" % (unit, what, bdir,
                                                                                    plan.report()))
            w.destroy()
            self.app.load()
            self.app.status.set("%s: %s wear your own files now (backup %s) - Undo this write takes them out." % (
                unit, what, bdir))
        bar = ttk.Frame(frm)
        bar.grid(row=r0 + 2, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(bar, text="Preview", command=preview).pack(side="left")
        ttk.Button(bar, text="Write it in", command=write).pack(side="left", padx=6)
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")

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
        pics = BuildingPictures(self.mod)
        # the cultures that build this level first (its factions lists): a culture that never builds it has only
        # the game's stand-ins - no picture, an empty name, 'WARNING! ... never appear on screen!' (a tester)
        from .buildings import builder_cultures, read_buildings
        chain = self.current[0] if self.current else None
        lv_obj = next((b.level(self.v_level.get()) for b in read_buildings(self.mod.load(self.path()))
                       if b.name == chain), None)
        builders = [c for c in builder_cultures(self.mod, lv_obj) if c in cultures] if lv_obj else list(cultures)
        others = [c for c in cultures if c not in builders]
        never = " (never builds it)"
        shown = builders + [c + never for c in others]
        self.v_cult = getattr(self, "v_cult", tk.StringVar())
        if self.v_cult.get().replace(never, "") not in cultures or getattr(self, "_cult_for", None) != (
                chain, self.v_level.get()):
            first = next((c for c in builders if pics.find(c, self.v_level.get())), builders[0] if builders else
                         (cultures[0] if cultures else ""))
            if getattr(self, "_cult_for", None) is None or self.v_cult.get().replace(never, "") not in builders:
                self.v_cult.set(first)
        self._cult_for = (chain, self.v_level.get())
        cur = self.v_cult.get().replace(never, "")
        self.v_cult.set(cur + (never if cur in others else ""))
        cb2 = ttk.Combobox(bar, textvariable=self.v_cult, values=shown, state="readonly", width=28)
        cb2.pack(side="left", padx=4)
        cb2.bind("<<ComboboxSelected>>", lambda ev: self.show_pictures())
        if not cultures:
            ttk.Label(self.pics, text="no ui/<culture>/buildings folders in this mod").grid(row=1, column=0)
            return
        level, cult = self.v_level.get(), cur
        if cult in others and lv_obj is not None:
            ttk.Label(self.pics, foreground=theme.ink("#a60000"), wraplength=520, justify="left", text=(
                "%s never builds %s (requires factions %s): the game has no picture of it and only its stand-in "
                "texts - pick a culture that builds it." % (cult, level, ", ".join(lv_obj.factions() or []))
            )).grid(row=2, column=0, columnspan=3, sticky="w")
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
            bb = ttk.Frame(box)
            bb.grid(row=2, column=1, sticky="w", padx=6)
            ttk.Button(bb, text="Import...", command=lambda t=[target], n=need, l=label: self.import_pic(t, n, l)).pack(
                side="left")
            now = pics.find(cult, level, constructed)
            if now and not pending:
                ttk.Button(bb, text="Save a copy...", command=lambda h=now, l=label: save_copy(
                    self, h, "the %s" % l.lower())).pack(side="left", padx=4)
        self._building_texts(level, cult)

    def _building_texts(self, level, cult):
        """The level's name and descriptions players read, for a culture or faction (the game takes
        <level>_<faction>, else <level>_<culture>, else the plain <level>): shown and changed here, written on Apply
        into export_buildings.txt."""
        from .gui_newrecord import _text_value
        box = ttk.LabelFrame(self.pics, text="Texts players read", padding=6)
        box.grid(row=2, column=0, columnspan=3, sticky="we", pady=(8, 0))
        have = E.level_text_suffixes(self.mod, level)
        cults = sorted({c for _, c in self.mod.factions() if c})
        facs = sorted(f for f, _ in self.mod.factions())
        choices = ["(plain)"] + [c for c in dict.fromkeys(cults + facs + [x for x in have if x])]
        marked = ["%s%s" % (c, " *" if (c == "(plain)" and "" in have) or c.lower() in have else "") for c in choices]
        self.v_tfor = getattr(self, "v_tfor", tk.StringVar())
        cur = self.v_tfor.get().rstrip(" *")
        if cur not in choices:
            # the picture's culture when it has texts of its own (Rome names some by faction: carthage, parthia)
            cur = next((c for c in (cult, cult.replace("ian", "")) if c.lower() in have), "(plain)")
        self.v_tfor.set(marked[choices.index(cur)])
        top = ttk.Frame(box)
        top.grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(top, text="Texts for").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.v_tfor, values=marked, state="readonly", width=26)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda ev: self.show_pictures())
        hint(top, "The game shows a level's texts for the faction first ({level_faction}), else for its culture "
                  "({level_culture}), else the plain ones ({level}). * = this one has texts of its own. A change is "
                  "written to export_buildings.txt on Apply (with a backup).").pack(side="left", padx=4)
        suffix = "" if cur == "(plain)" else cur
        base = level + ("_" + suffix if suffix else "")
        rows = []
        for r, (part, label) in enumerate(E.TEXT_PARTS, start=1):
            key = base + part
            now = self.text_edits.get(key)
            if now is None:
                now = _text_value(self.mod, "export_buildings.txt", key)
            ttk.Label(box, text=label.capitalize()).grid(row=r, column=0, sticky="nw", padx=(0, 6), pady=2)
            if part == "_desc":
                w = tk.Text(box, height=4, width=60, wrap="word", font="TkDefaultFont")
                w.insert("1.0", now)
                w.bind("<KeyRelease>", lambda ev, k=key, w=w: self._text_edited(k, w.get("1.0", "end-1c")))
            else:
                v = tk.StringVar(value=now)
                w = ttk.Entry(box, textvariable=v, width=60)
                w.bind("<KeyRelease>", lambda ev, k=key, v=v: self._text_edited(k, v.get()))
            w.grid(row=r, column=1, sticky="we", pady=2)
            rows.append(w)
        if any(x in _text_value(self.mod, "export_buildings.txt", base + p)
               for p, _ in E.TEXT_PARTS for x in E.STAND_INS):
            ttk.Label(box, foreground=theme.ink("#a60"), text="These texts are stand-ins the game never shows - pick "
                      "a culture or faction that builds it above.").grid(row=4, column=1, sticky="w")
        box.columnconfigure(1, weight=1)

    def _text_edited(self, key, text):
        from .gui_newrecord import _text_value
        if text == _text_value(self.mod, "export_buildings.txt", key):
            self.text_edits.pop(key, None)
        else:
            self.text_edits[key] = text
        self.app._mark_work() if hasattr(self.app, "_mark_work") else None

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
            if not ask("Import", "%s is %d x %d; this mod's own are %d x %d.\n\n"
                                                 "Resize it to %d x %d?" % ((os.path.basename(src),) + tuple(got) +
                                                                            tuple(size) + tuple(size)), yes='Resize it', no='Keep its size'):
                size = None
        self.imports = [(s, t, z) for s, t, z in self.imports if not set(t) & set(targets)]
        self.imports.append((src, list(targets), size))
        self.app.status.set("%s: %s for %d place(s) - Preview, then Apply." % (label, os.path.basename(src), len(targets)))
        self.show_pictures()

    # ---- writing ----
    def dirty(self):
        return bool(self.changes or self.imports or self.copy_ops or self.adds or self.removes or self.text_edits)

    # ---- unit packs ----
    def bring_dialog(self):
        """Units or building chains from another mod's folder, step by step (gui_bring)."""
        if not self.mod:
            messagebox.showerror("Bring from another mod", "load a mod first", parent=self)
            return
        from .gui_bring import BringWindow
        BringWindow(self)

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
            k = ask_choice(self, "Export pack", "Export which units?", ["Only %s" % picked,
                           "All %d the list shows now" % len(types), "Cancel"], cancel=2)
            one = None if k == 2 else k == 0
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
        if self.pending() and not ask(
                "Import pack", "The unit editor holds changes not written yet; the import writes "
                               "export_descr_unit.txt, so they would be dropped. Go on?", parent=self, yes='Import, drop them', no='Stay', danger=True):
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
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
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
            if plan.warnings and not ask("Import pack", "Write %d file(s)? A backup is made first (Restore undoes "
                                                      "it)." % len(plan.changed_files()), parent=w, yes='Write it in', no='Cancel'):
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
        return len(self.changes) + len(self.imports) + len(self.copy_ops) + len(self.adds) + len(self.removes) + \
            len(self.text_edits)

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
                                "New building step by step" % (name, " ".join(have)))
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
        """A new unit (building chain) step by step, starting from the one on show (gui_newrecord)."""
        if not self.mod:
            messagebox.showerror("New", "load a mod first")
            return
        from .gui_newrecord import NewRecordWizard
        NewRecordWizard(self, self.current[0] if self.current else None)

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
        if self.text_edits:                              # names and descriptions players read
            E.set_text_values(plan, mod.text_file("export_buildings.txt" if self.kind == "building" else
                                                  "export_units.txt"), dict(self.text_edits))
        for src, new, d in self.copy_ops:                 # after the field changes: copies add lines
            if d.get("nothing") and self.kind == "building":
                from . import fromnothing as FN
                FN.new_building(plan, d["nothing"], new, d["levels"], d["factions"], d["numbers"], d["castle"],
                                d["units"], d["chain_name"], d["pictures"])
            elif d.get("nothing"):
                from . import fromnothing as FN
                FN.new_unit(plan, d["nothing"], new, d["dict"], d["owners"], d["model"], d["mount"], d["values"],
                            d["texts"], d["pictures"], d["recruit"])
            elif self.kind == "unit":
                E.copy_unit(plan, src, new, d["dict"], d["recruit"], texts=d.get("texts"), owners=d.get("owners"),
                            values=d.get("values"), pictures=d.get("pictures"))
            else:
                E.copy_building(plan, src, new, d["levels"], texts=d.get("texts"), factions=d.get("factions"),
                                pictures=d.get("pictures"))
        return plan
