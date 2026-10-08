"""New unit / New building, step by step (the Unit and Building editors' "New ... step by step" button).

A new unit or building chain starts as a copy of one that surely works in the game (like a new faction starts
from a template); each step changes one side of it, Back and Next go between the steps and keep what was typed,
the last step shows everything and a Preview of every file before it is added. It is written on Apply with the
editor's other changes (editors.copy_unit / copy_building)."""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from . import editors as E
from .gui_util import StepWindow
from .moddata import ModData

UNIT_VALUES = [
    ("category", "infantry, cavalry, siege, handler, ship or non_combatant"),
    ("class", "light, heavy, missile, spearmen or skirmish"),
    ("soldier", "model, men, extras, mass - the model it looks like and how many men"),
    ("mount", "the animal it rides (empty = on foot)"),
    ("stat_health", "hit points of a man, of his mount"),
    ("stat_pri", "main weapon: attack, charge, missile, range, ammunition, kind, ..."),
    ("stat_sec", "second weapon, the same way"),
    ("stat_pri_armour", "armour, defence skill, shield, sound"),
    ("stat_mental", "morale, discipline, training"),
    ("stat_cost", "turns to train, cost, upkeep, weapon and armour upgrades, custom battle cost, ..."),
    ("attributes", "abilities, comma separated"),
]


def _text_value(mod, name, key):
    """The value of {key} in a string table (lines joined with new lines), or ''."""
    path = mod.text_file(name)
    if not path:
        return ""
    texts = mod.load(path).texts()
    low = "{" + key.lower() + "}"
    for i, t in enumerate(texts):
        s = t.lstrip()
        if s.lower().startswith(low):
            out = [s[len(low):].strip()]
            j = i + 1
            while j < len(texts) and not texts[j].lstrip().startswith(("{", "¬")):
                out.append(texts[j].rstrip())
                j += 1
            while len(out) > 1 and not out[-1]:
                out.pop()
            while len(out) > 1 and not out[0]:
                out.pop(0)
            return "\n".join(out).replace("\\n", "\n")
    return ""


class NewRecordWizard(StepWindow):
    def __init__(self, editor, start=None):
        super().__init__(editor)
        self.ed, self.kind, self.mod = editor, editor.kind, editor.mod
        self.title("New %s - step by step" % self.kind)
        self.transient(editor)
        self.geometry("1000x660")
        self.minsize(700, 520)
        f = self.mod.load(self.mod.file("edu" if self.kind == "unit" else "edb"))
        self.f = f
        self.blocks = E.unit_blocks(f) if self.kind == "unit" else E.building_blocks(f)
        self.names = [b[0] for b in self.blocks]
        facs = [n for n, _ in self.mod.factions()]
        cults = sorted({c for _, c in self.mod.factions() if c})
        self.choices = facs + [c for c in cults if c not in facs] + ["all"]
        self.v = {"src": tk.StringVar(value=start if start in self.names else (self.names[0] if self.names else "")),
                  "mode": tk.StringVar(value="copy"), "kind": tk.StringVar(value="")}
        self.state = {}                      # what each step holds, filled when the source is chosen
        self.finish_text = "Add to the %s editor" % self.kind
        self.steps_copy = ([("Start from", self.s_start), ("Names and texts", self.s_names),
                            ("Who has it", self.s_who), ("Numbers", self.s_values), ("Pictures", self.s_pictures),
                            ("Check and add", self.s_check)]
                           if self.kind == "unit" else
                           [("Start from", self.s_start), ("Names and texts", self.s_names),
                            ("Who may build it", self.s_who), ("Pictures", self.s_pictures),
                            ("Check and add", self.s_check)])
        # a unit made from nothing (fromnothing.py): the modder says what it is, every line is written new
        self.steps_nothing = [("Start from", self.s_start), ("Names and texts", self.s_names),
                              ("Who has it", self.s_who), ("Numbers and look", self.s_nothing_values),
                              ("Where it is recruited", self.s_where), ("Pictures", self.s_pictures),
                              ("Check and add", self.s_check)]
        self.make_steps(self.steps_copy)
        self.load_source()
        self.show()

    # ---- the source's values ----
    def _lines(self, name):
        b = next(b for b in self.blocks if b[0] == name)
        return [self.f.text(i) for i in range(b[1], b[2])]

    def _val(self, lines, key):
        for t in lines:
            tk_ = E.tokens(t)
            if tk_[:1] == [key]:
                body = E.strip_comment(t).strip()
                return body[len(key):].strip()
        return None

    def load_source(self):
        src = self.v["src"].get()
        if not src or self.state.get("src") == src:
            return
        lines = self._lines(src)
        st = {"src": src}
        if self.kind == "unit":
            dic = self._val(lines, "dictionary") or src.replace(" ", "_")
            st.update(type=src + " 2", dict=dic + "_2", name=_text_value(self.mod, "export_units.txt", dic),
                      descr=_text_value(self.mod, "export_units.txt", dic + "_descr"),
                      descr_short=_text_value(self.mod, "export_units.txt", dic + "_descr_short"),
                      owners=[x.strip() for x in (self._val(lines, "ownership") or "").split(",") if x.strip()],
                      recruit=True, values={k: self._val(lines, k) for k, _ in UNIT_VALUES
                                            if self._val(lines, k) is not None},
                      pictures={"card": "", "info": ""})
        else:
            from .roster import factions_in
            levels = (self._val(lines, "levels") or "").split()
            groups = []
            for t in lines:
                head = E.strip_comment(t).strip().split()[:1]
                if head and head[0] in levels and "requires" in t:
                    for n in factions_in(t) or []:
                        if n not in groups:
                            groups.append(n)
            st.update(chain=src + "_2", levels=[(lv, lv + "_2") + self._level_texts(lv) for lv in levels],
                      factions=groups, keep_factions=True,
                      pictures={lv: {"pic": "", "constructed": ""} for lv in levels})
        st["orig_values"] = dict(st.get("values", {}))
        st["orig"] = {k: st.get(k) for k in ("name", "descr", "descr_short")} if self.kind == "unit" else \
            {old: (name, desc) for old, _, name, desc in st["levels"]}
        self.state = st

    def _level_texts(self, lv):
        """(name, description) players see for a level (gui_preview.level_text: its own key, else a culture's
        own one - Medieval II keeps 'DO NOT TRANSLATE' under the plain key)."""
        from .gui_preview import level_text
        cults = sorted({c for _, c in self.mod.factions() if c})
        name, desc = level_text(self.mod, lv, cults[0] if cults else "")
        return name or _text_value(self.mod, "export_buildings.txt", lv), desc

    # ---- moving between steps (gui_util.StepWindow) ----
    def nothing(self):
        return self.kind == "unit" and self.v["mode"].get() == "nothing"

    def load_nothing(self):
        """A unit made from nothing: what is usual for the kind in this mod, the names left to the modder."""
        from . import fromnothing as FN
        kind = self.v["kind"].get()
        if self.state.get("mode") == "nothing" and self.state.get("kind") == kind:
            return True
        try:
            typ = FN.typical(self.mod, kind)
        except ValueError as e:
            from tkinter import messagebox
            messagebox.showerror("New unit", str(e), parent=self)
            return False
        facs = [n for n, _ in self.mod.factions() if n != "slave"]
        self.state = {"mode": "nothing", "kind": kind, "typ": typ, "type": "", "dict": "", "name": "",
                      "descr": "", "descr_short": "", "owners": facs[:1], "recruit": True,
                      "values": {(k, i): v for _, k, i, v, _, _, _ in FN.fields(kind, typ)},
                      "model": typ["model"], "mount": typ["mount"],
                      "levels": None, "pictures": {"card": "", "info": ""}}
        return True

    def leaving(self, step):
        if step == 0:
            if self.nothing():
                if not self.v["kind"].get():
                    from tkinter import messagebox
                    messagebox.showinfo("New unit", "Pick what kind of unit it is.", parent=self)
                    return False
                if not self.load_nothing():
                    return False
                self.steps = self.steps_nothing
            else:
                self.steps = self.steps_copy
                self.load_source()

    def finish(self):
        return self.add()

    # ---- step 1 ----
    def s_start(self):
        if self.kind == "unit":
            top = ttk.Frame(self.body)
            top.pack(fill="x", pady=(0, 6))
            def mode():
                self.steps = self.steps_nothing if self.nothing() else self.steps_copy
                self.show()
            ttk.Radiobutton(top, text="A copy of a unit of the mod", variable=self.v["mode"], value="copy",
                            command=mode).pack(side="left")
            ttk.Radiobutton(top, text="Nothing - I say what it is, the editor writes every line",
                            variable=self.v["mode"], value="nothing", command=mode).pack(side="left", padx=12)
            if self.nothing():
                return self._start_nothing()
        self._note("A new %s starts as a copy of one that already works in the game - pick the one closest to "
                   "what you want. Every later step changes the copy; the %s you pick stays as it is." % (
                       self.kind, self.kind))
        bar = ttk.Frame(self.body)
        bar.pack(fill="x")
        ttk.Label(bar, text="Find").pack(side="left")
        v_find = tk.StringVar()
        ttk.Entry(bar, textvariable=v_find, width=24).pack(side="left", padx=4)
        box = ttk.Frame(self.body)
        box.pack(fill="both", expand=True, pady=4)
        lb = tk.Listbox(box, exportselection=False, width=34)
        sb = ttk.Scrollbar(box, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")
        from .gui_preview import BuildingPreview, UnitPreview
        look = (UnitPreview if self.kind == "unit" else BuildingPreview)(box, self.mod)
        look.pack(side="left", fill="both", expand=True)
        shown = []

        def fill(*_):
            q = v_find.get().strip().lower()
            lb.delete(0, "end")
            shown[:] = [n for n in self.names if q in n.lower()]
            for n in shown:
                lb.insert("end", n)
            if self.v["src"].get() in shown:
                i = shown.index(self.v["src"].get())
                lb.selection_set(i)
                lb.see(i)
            pick()

        def pick(*_):
            sel = lb.curselection()
            if sel:
                self.v["src"].set(shown[sel[0]])
            src = self.v["src"].get()
            if src and getattr(look, "_shown", None) != src:
                look._shown = src
                look.show(src)
        v_find.trace_add("write", fill)
        lb.bind("<<ListboxSelect>>", pick)
        fill()

    def _start_nothing(self):
        from . import fromnothing as FN
        self._note("Say what kind of unit it is. The editor writes every line of it new, in the form this mod's units "
                   "of that kind have; its numbers start at what is usual for such a unit in this mod (the middle "
                   "of them all) and you set each one in a later step. A siege crew, a ship, an elephant or a "
                   "chariot needs an engine or an animal of its own - make those as a copy.")
        box = ttk.Frame(self.body)
        box.pack(fill="x", anchor="w")
        for key, words, *_ in FN.KINDS:
            n = len(FN.units_of_kind(self.mod, key))
            rb = ttk.Radiobutton(box, variable=self.v["kind"], value=key, text="%s   (%d in this mod)" % (words, n))
            rb.pack(anchor="w", pady=2)
            if not n:
                rb.state(["disabled"])

    # ---- step 2 ----
    def s_names(self):
        st = self.state
        if self.kind == "unit":
            self._note("The name in the files (type) is what descr_strat and the buildings use; the dictionary "
                       "name keys its cards and texts (no spaces). Players see the name and descriptions.%s" % (
                           " Empty descriptions are written as its name." if self.nothing() else ""))
        else:
            self._note("Only names and the texts players read are written here. Everything the building does - "
                       "bonuses, the units it trains, what it needs, costs, its pictures - is copied whole from %s "
                       "(shown in grey under each level); change those later in the Building editor. A text you "
                       "write here is shown for every culture; one left as it is stays the copied one." % st["src"])
        g = ttk.Frame(self.body)
        g.pack(fill="both", expand=True)
        if self.kind == "unit":
            vs = {k: tk.StringVar(value=st[k]) for k in ("type", "dict", "name")}
            rows = [("Name in the files (type)", "type"), ("Dictionary (no spaces)", "dict"),
                    ("Name players see", "name")]
            for r, (label, k) in enumerate(rows):
                ttk.Label(g, text=label).grid(row=r, column=0, sticky="w", pady=2)
                ttk.Entry(g, textvariable=vs[k], width=48).grid(row=r, column=1, sticky="we", padx=6)
            auto = {"last": st["dict"]}

            def follow(*_):                          # the dictionary follows the type until typed by hand
                if vs["dict"].get() == auto["last"]:
                    auto["last"] = "_".join(vs["type"].get().split())
                    vs["dict"].set(auto["last"])
            vs["type"].trace_add("write", follow)
            texts = {}
            for r, (label, k, h) in enumerate((("Short description", "descr_short", 3),
                                               ("Description", "descr", 7)), start=3):
                ttk.Label(g, text=label).grid(row=r, column=0, sticky="nw", pady=2)
                t = tk.Text(g, height=h, width=60, wrap="word")
                t.insert("1.0", st[k])
                t.grid(row=r, column=1, sticky="we", padx=6, pady=2)
                texts[k] = t
            g.columnconfigure(1, weight=1)

            def collect():
                for k in vs:
                    st[k] = vs[k].get().strip()
                for k, t in texts.items():
                    st[k] = t.get("1.0", "end").strip()
        else:
            v_chain = tk.StringVar(value=st["chain"])
            ttk.Label(g, text="Chain name in the files").grid(row=0, column=0, sticky="w")
            ttk.Entry(g, textvariable=v_chain, width=30).grid(row=0, column=1, sticky="w", padx=6)
            canvas = tk.Canvas(g, highlightthickness=0, height=380)
            inner = ttk.Frame(canvas)
            sb = ttk.Scrollbar(g, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=sb.set)
            canvas.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=6)
            sb.grid(row=1, column=2, sticky="ns")
            canvas.create_window(0, 0, anchor="nw", window=inner)
            inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            g.rowconfigure(1, weight=1)
            g.columnconfigure(1, weight=1)
            rows = []
            from .effects import level_words
            blk = next(b for b in self.blocks if b[0] == st["src"])
            does = {lv["name"]: level_words(self.f.text(i) for i in range(*lv["capability"])) if lv["capability"]
                    else [] for lv in E.chain_tree(self.f, blk[1], blk[2])["levels"]}
            for r, (old, new, name, desc) in enumerate(st["levels"]):
                ttk.Label(inner, text="level %s" % old, font=("", 9, "bold")).grid(row=3 * r, column=0, sticky="w",
                                                                                  pady=(6, 0))
                if does.get(old):
                    ttk.Label(inner, text="does: " + "; ".join(does[old][:6]) + (" ..." if len(does[old]) > 6 else ""),
                              foreground="#777", wraplength=640, justify="left").grid(
                        row=3 * r, column=1, columnspan=3, sticky="w", pady=(6, 0))
                vn, vs_ = tk.StringVar(value=new), tk.StringVar(value=name)
                ttk.Label(inner, text="name in the files").grid(row=3 * r + 1, column=0, sticky="w")
                ttk.Entry(inner, textvariable=vn, width=28).grid(row=3 * r + 1, column=1, sticky="w", padx=6)
                ttk.Label(inner, text="name players see").grid(row=3 * r + 1, column=2, sticky="w")
                ttk.Entry(inner, textvariable=vs_, width=28).grid(row=3 * r + 1, column=3, sticky="w", padx=6)
                t = tk.Text(inner, height=2, width=76, wrap="word")
                t.insert("1.0", desc)
                t.grid(row=3 * r + 2, column=0, columnspan=4, sticky="we", pady=2)
                rows.append((old, vn, vs_, t))

            def collect():
                st["chain"] = v_chain.get().strip()
                st["levels"] = [(old, vn.get().strip(), vs_.get().strip(), t.get("1.0", "end").strip())
                                for old, vn, vs_, t in rows]
        self._collect = collect

    # ---- step 3 ----
    def s_who(self):
        st = self.state
        if self.kind == "unit":
            self._note("Who owns the unit (export_descr_unit's ownership line): factions, cultures (every faction "
                       "of that culture) or 'all'. %s" % (
                           "Each of their factions gets its cards and a texture on its model." if self.nothing() else
                           "Picked from the copy; new owners get a copy of its cards."))
            picked = st["owners"]
        else:
            self._note("Who may build every level of the new chain (the factions list of each level's requires "
                       "line): factions or cultures. 'Keep each level's own list' copies them as they are.")
            picked = st["factions"]
        top = ttk.Frame(self.body)
        top.pack(fill="both", expand=True)
        lb = tk.Listbox(top, selectmode="multiple", exportselection=False, height=16)
        sb = ttk.Scrollbar(top, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        for i, n in enumerate(self.choices):
            lb.insert("end", n)
            if n in picked:
                lb.selection_set(i)
        lb.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")
        side = ttk.Frame(top, padding=(12, 0))
        side.pack(side="left", fill="both", expand=True)
        v_extra = tk.BooleanVar(value=st["recruit"] if self.kind == "unit" else st["keep_factions"])
        if not self.nothing():
            ttk.Checkbutton(side, variable=v_extra, text=(
                "recruited wherever %s is (a recruit line next to each of its own)" % st["src"]
                if self.kind == "unit" else "keep each level's own list (the picks on the left are not used)")).pack(
                anchor="w")
        lbl = ttk.Label(side, wraplength=380, justify="left", foreground="#555")
        lbl.pack(anchor="w", pady=(8, 0))

        def update(*_):
            names = [self.choices[i] for i in lb.curselection()]
            lbl.configure(text="%d picked: %s" % (len(names), ", ".join(names)) if names else "none picked")
        lb.bind("<<ListboxSelect>>", update)
        update()

        def collect():
            names = [self.choices[i] for i in lb.curselection()]
            if self.kind == "unit":
                st["owners"], st["recruit"] = names, v_extra.get()
            else:
                st["factions"], st["keep_factions"] = names, v_extra.get()
        self._collect = collect

    # ---- step 4 (units) ----
    def s_values(self):
        st = self.state
        self._note("The copy's main lines - change what should differ (the Unit editor has every other line "
                   "afterwards). Left as it is = as %s has it." % st["src"])
        g = ttk.Frame(self.body)
        g.pack(fill="both", expand=True)
        vs = {}
        r = 0
        for key, what in UNIT_VALUES:
            if key not in st["values"]:
                continue
            ttk.Label(g, text=key).grid(row=r, column=0, sticky="w", pady=1)
            vs[key] = tk.StringVar(value=st["values"][key])
            ttk.Entry(g, textvariable=vs[key], width=56).grid(row=r, column=1, sticky="we", padx=6)
            ttk.Label(g, text=what, foreground="#666", wraplength=260).grid(row=r, column=2, sticky="w")
            r += 1
        g.columnconfigure(1, weight=1)

        def collect():
            for k, v in vs.items():
                st["values"][k] = v.get().strip()
        self._collect = collect

    # ---- a unit made from nothing: its numbers, model and mount; where it is recruited ----
    def s_nothing_values(self):
        from . import fromnothing as FN
        from . import models as MO
        st = self.state
        typ = st["typ"]
        self._note("Every number starts at what is usual for such a unit in this mod (the middle of its %d units of "
                   "the kind); beside it the lowest and highest the mod has. Every other line (formation, ground, "
                   "heat, the weapons' kinds and sounds) is written as such units usually have it - change any of "
                   "them later in the Unit editor (Every line of the block)." % typ["count"])
        g = ttk.Frame(self.body)
        g.pack(fill="x")
        vs = {}
        for r, (label, key, i, _, rng, choices, help_) in enumerate(FN.fields(st["kind"], typ)):
            ttk.Label(g, text=label).grid(row=r, column=0, sticky="w", pady=1)
            vs[(key, i)] = v = tk.StringVar(value=st["values"].get((key, i), ""))
            if choices:
                ttk.Combobox(g, textvariable=v, values=choices, state="readonly", width=14).grid(
                    row=r, column=1, sticky="w", padx=6)
            else:
                ttk.Entry(g, textvariable=v, width=10).grid(row=r, column=1, sticky="w", padx=6)
            rtxt = "usual %s, in this mod %s - %s" % (FN.nice(rng[1]), FN.nice(rng[0]), FN.nice(rng[2])) if rng \
                else ""
            ttk.Label(g, text=("%s;  %s" % (help_, rtxt)) if rtxt else help_, foreground="#666").grid(
                row=r, column=2, sticky="w")
        look = ttk.LabelFrame(self.body, text="How it looks", padding=6)
        look.pack(fill="x", pady=(8, 0))
        seat = "horse" if st["kind"].startswith("horse") else "none"
        cat = MO.catalogue(self.mod)
        models = sorted(i.name for i in cat.values() if not [p for p in MO.fit_problems(self.mod, i, seat)
                                                              if "made" in p[1]])
        ttk.Label(look, text="Battle model").grid(row=0, column=0, sticky="w")
        v_model = tk.StringVar(value=st["model"])
        ttk.Combobox(look, textvariable=v_model, values=models, width=34).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(look, foreground="#666", wraplength=420, justify="left", text=(
            "a model of the mod made to sit %s; your own files (texture, .cas / .mesh) go in afterwards with the "
            "Unit editor's Your own files..." % MO.SEAT_WORDS.get(seat))).grid(row=0, column=2, sticky="w")
        v_mount = tk.StringVar(value=st["mount"] or "")
        if st["kind"].startswith("horse"):
            mounts = sorted(m for m, c in MO.mount_classes(self.mod).items() if c in FN.RIDDEN)
            ttk.Label(look, text="It rides").grid(row=1, column=0, sticky="w", pady=(4, 0))
            ttk.Combobox(look, textvariable=v_mount, values=mounts, state="readonly", width=34).grid(
                row=1, column=1, sticky="w", padx=6, pady=(4, 0))

        def collect():
            for k, v in vs.items():
                st["values"][k] = v.get().strip()
            st["model"] = v_model.get().strip()
            st["mount"] = v_mount.get().strip() or None
        self._collect = collect

    def s_where(self):
        from . import fromnothing as FN
        st = self.state
        levels = sorted(FN.recruit_levels(self.mod))
        if st["levels"] is None:
            st["levels"] = FN.usual_levels(self.mod, st["kind"], st["owners"])
        self._note("The building levels that train it: a recruit line is written in each one picked, letting in "
                   "its owners. First picked: where this mod trains such units most. None picked = it is recruited "
                   "nowhere yet (Roster or the Building editor can add it later).")
        box = ttk.Frame(self.body)
        box.pack(fill="both", expand=True)
        lb = tk.Listbox(box, selectmode="multiple", exportselection=False, height=18, width=60)
        sb = ttk.Scrollbar(box, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        for i, (chain, level, n) in enumerate(levels):
            lb.insert("end", "%s / %s   (trains %d unit(s) now)" % (chain, level, n))
            if (chain, level) in st["levels"]:
                lb.selection_set(i)
        lb.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")

        def collect():
            st["levels"] = [levels[i][:2] for i in lb.curselection()]
        self._collect = collect

    # ---- pictures ----
    def s_pictures(self):
        st = self.state
        pics = st["pictures"]
        if self.kind == "unit" and self.nothing():
            self._note("Without a picture of your own the editor draws a plain card and description picture (the "
                       "unit's initials) so the game has one. A picture of yours (PNG, JPG, TGA...) is put in the "
                       "size and format this mod's cards have.")
        elif self.kind == "unit":
            self._note("Without a picture of your own the new unit shows %s's card and description picture (a "
                       "copy under its own name). A picture of yours (PNG, JPG, TGA...) is put in the size and "
                       "format this mod's cards have." % st["src"])
        if self.kind == "unit":
            rows = [("card", "Unit card", E.unit_picture_need(self.mod)),
                    ("info", "Picture in the description", E.unit_picture_need(self.mod, True))]
        else:
            return self._building_pictures()
        g = ttk.Frame(self.body)
        g.pack(fill="x")
        vs = {}
        for r, (k, label, need) in enumerate(rows):
            ttk.Label(g, text=label).grid(row=r, column=0, sticky="w", pady=2)
            vs[k] = tk.StringVar(value=pics.get(k, ""))
            ttk.Entry(g, textvariable=vs[k], width=50).grid(row=r, column=1, sticky="we", padx=6)
            ttk.Button(g, text="Browse...", command=lambda v=vs[k]: v.set(filedialog.askopenfilename(
                parent=self, title="A picture") or v.get())).grid(row=r, column=2)
            if need:
                ttk.Label(g, text="%d x %d" % need[:2], foreground="#666").grid(row=r, column=3, padx=6)
        g.columnconfigure(1, weight=1)

        def collect():
            for k, v in vs.items():
                pics[k] = v.get().strip()
        self._collect = collect

    def _building_pictures(self):
        """Each level has two pictures: in the town (the building panel) and when built (the wide one shown when
        it is finished). Shown as they are now (the copied level's) and as chosen; a culture to look with."""
        from .buildings import BuildingPictures
        from .gui_preview import _photo
        st = self.state
        pics = st["pictures"]
        self._note("Each level has two pictures: the one in the town and the wide one shown when it is built. "
                   "Without a picture of your own a new level shows the copied level's (left as it is now). A "
                   "picture of yours (PNG, JPG, TGA...) is put in the size of this mod's building pictures, into "
                   "every culture's folder.")
        bp = BuildingPictures(self.mod)
        cults = sorted({c for _, c in self.mod.factions() if c})
        v_cult = tk.StringVar(value=next((c for c in cults if pics and bp.find(c, next(iter(pics)))),
                                         cults[0] if cults else ""))
        bar = ttk.Frame(self.body)
        bar.pack(fill="x")
        ttk.Label(bar, text="Pictures as the culture").pack(side="left")
        cb = ttk.Combobox(bar, textvariable=v_cult, values=cults, state="readonly", width=16)
        cb.pack(side="left", padx=4)
        ttk.Label(bar, text="sees them (only for looking - yours go to every culture)", foreground="#666").pack(
            side="left")
        outer = ttk.Frame(self.body)
        outer.pack(fill="both", expand=True, pady=4)
        canvas = tk.Canvas(outer, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        canvas.create_window(0, 0, anchor="nw", window=inner)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        names = dict((old, new) for old, new, _, _ in st["levels"])
        keep = []
        vs = {}

        def draw(*_):
            for w in inner.winfo_children():
                w.destroy()
            keep.clear()
            for r, old in enumerate(pics):
                ttk.Label(inner, text="level %s" % names.get(old, old), font=("", 9, "bold")).grid(
                    row=2 * r, column=0, columnspan=4, sticky="w", pady=(8, 0))
                for c, (key, label, box) in enumerate((("pic", "in the town", (90, 72)),
                                                       ("constructed", "when built", (190, 72)))):
                    cell = ttk.Frame(inner)
                    cell.grid(row=2 * r + 1, column=c, sticky="nw", padx=(0, 16))
                    v = vs.setdefault((old, key), tk.StringVar(value=pics[old].get(key, "")))
                    mine = v.get()
                    ph = _photo(mine or bp.find(v_cult.get(), old, key == "constructed"), box)
                    if ph:
                        keep.append(ph)
                        ttk.Label(cell, image=ph).pack(anchor="w")
                    else:
                        ttk.Label(cell, text="(no picture)", foreground="#888").pack(anchor="w", pady=8)
                    ttk.Label(cell, text="%s: %s" % (label, os.path.basename(mine) if mine else "the copied one"),
                              foreground="#2a7a1f" if mine else "#666").pack(anchor="w")
                    row = ttk.Frame(cell)
                    row.pack(anchor="w")

                    def browse(v=v):
                        p = filedialog.askopenfilename(parent=self, title="A picture", filetypes=[
                            ("Pictures", "*.tga *.png *.jpg *.jpeg *.bmp *.dds"), ("All files", "*.*")])
                        if p:
                            v.set(p)
                            draw()
                    ttk.Button(row, text="Picture...", command=browse).pack(side="left")
                    if mine:
                        ttk.Button(row, text="Back to the copied one",
                                   command=lambda v=v: (v.set(""), draw())).pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", draw)
        draw()

        def collect():
            for (old, key), v in vs.items():
                pics[old][key] = v.get().strip()
        self._collect = collect

    # ---- the last step ----
    def op(self):
        st = self.state
        if self.nothing():
            return "", st["type"], {"nothing": st["kind"], "dict": st["dict"], "owners": st["owners"],
                                    "model": st["model"], "mount": st["mount"], "values": dict(st["values"]),
                                    "texts": {k: st[k] for k in ("name", "descr", "descr_short")},
                                    "pictures": {k: v for k, v in st["pictures"].items() if v},
                                    "recruit": list(st["levels"] or [])}
        if self.kind == "unit":
            d = {"dict": st["dict"], "recruit": st["recruit"],
                 "texts": {k: (st[k] if st[k] != st["orig"][k] else None) for k in ("name", "descr", "descr_short")},
                 "owners": st["owners"] or None,
                 "values": {k: v for k, v in st["values"].items() if v != st["orig_values"].get(k)},
                 "pictures": {k: v for k, v in st["pictures"].items() if v}}
            return st["src"], st["type"], d
        levels = {old: new for old, new, _, _ in st["levels"]}
        d = {"levels": levels,
             "texts": {new: {"name": name if name != st["orig"][old][0] else None,
                             "desc": desc if desc != st["orig"][old][1] else None}
                       for old, new, name, desc in st["levels"]},
             "factions": None if st["keep_factions"] else (st["factions"] or None),
             "pictures": {levels[k]: v for k, v in st["pictures"].items()
                          if k in levels and any((v or {}).values())}}
        return st["src"], st["chain"], d

    def problems(self):
        st = self.state
        out = []
        if self.nothing():
            from . import fromnothing as FN
            out = FN.problems(self.mod, st["kind"], st["type"], st["dict"], st["owners"], st["model"],
                              st["mount"], st["values"])
            out += ["picture not found: %s" % v for v in st["pictures"].values() if v and not os.path.isfile(v)]
            return out
        if self.kind == "unit":
            if not st["type"]:
                out.append("the unit needs a name in the files")
            if not st["dict"] or " " in st["dict"]:
                out.append("the dictionary name must be one word (letters, digits, _)")
            for k, v in st["pictures"].items():
                if v and not os.path.isfile(v):
                    out.append("picture not found: %s" % v)
        else:
            if not st["chain"]:
                out.append("the chain needs a name in the files")
            if not st["keep_factions"] and not st["factions"]:
                out.append("pick who may build it, or keep each level's own list")
            for lv, pair in st["pictures"].items():
                for v in (pair or {}).values():
                    if v and not os.path.isfile(v):
                        out.append("picture not found: %s" % v)
        return out

    def s_check(self):
        src, new, d = self.op()
        why = self.problems()
        plan = None
        if not why:
            from .plan import Plan
            try:
                plan = Plan(ModData(self.mod.data), "new_" + self.kind, "new_" + self.kind, {})
                if d.get("nothing"):
                    from . import fromnothing as FN
                    FN.new_unit(plan, d["nothing"], new, d["dict"], d["owners"], d["model"], d["mount"],
                                d["values"], d["texts"], d["pictures"], d["recruit"])
                elif self.kind == "unit":
                    E.copy_unit(plan, src, new, d["dict"], d["recruit"], texts=d["texts"], owners=d["owners"],
                                values=d["values"], pictures=d["pictures"])
                else:
                    E.copy_building(plan, src, new, d["levels"], texts=d["texts"], factions=d["factions"],
                                    pictures=d["pictures"])
            except Exception as e:
                why = [str(e)]
        if why:
            ttk.Label(self.body, text="Not ready yet:\n- " + "\n- ".join(why), foreground="#a33",
                      justify="left", wraplength=780).pack(anchor="w")
            self._note("Go Back to the step that needs it.")
            self.b_next.state(["disabled"])
            return
        self.b_next.state(["!disabled"])
        self._note("%s %s %s. Nothing is written yet: Add puts it into the %s editor's changes, written "
                   "with a backup on Apply (Restore undoes it). Below: every file it will change and how." % (
                       "New unit" if self.kind == "unit" else "New building chain", new,
                       "made from nothing" if d.get("nothing") else "from %s" % src, self.kind))
        box = ttk.Frame(self.body)
        box.pack(fill="both", expand=True)
        t = tk.Text(box, wrap="none", height=20)
        sb = ttk.Scrollbar(box, command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        t.insert("1.0", plan.report())
        t.configure(state="disabled")

    def add(self):
        if self.problems():
            return
        op = self.op()
        self.ed.copy_ops.append(op)
        self.ed.fill_list()
        self.ed.app.status.set("New %s %s %s waits in the %s editor - Preview, then Apply." % (
            self.kind, op[1], "made from nothing" if op[2].get("nothing") else "from %s" % op[0], self.kind))
        self.destroy()
