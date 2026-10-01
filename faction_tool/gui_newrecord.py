"""New unit / New building, step by step (the Unit and Building editors' "New ... step by step" button).

A new unit or building chain starts as a copy of one that surely works in the game (like a new faction starts
from a template); each step changes one side of it, Back and Next go between the steps and keep what was typed,
the last step shows everything and a Preview of every file before it is added. It is written on Apply with the
editor's other changes (editors.copy_unit / copy_building)."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

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
        self.geometry("820x620")
        self.minsize(700, 520)
        f = self.mod.load(self.mod.file("edu" if self.kind == "unit" else "edb"))
        self.f = f
        self.blocks = E.unit_blocks(f) if self.kind == "unit" else E.building_blocks(f)
        self.names = [b[0] for b in self.blocks]
        facs = [n for n, _ in self.mod.factions()]
        cults = sorted({c for _, c in self.mod.factions() if c})
        self.choices = facs + [c for c in cults if c not in facs] + ["all"]
        self.v = {"src": tk.StringVar(value=start if start in self.names else (self.names[0] if self.names else ""))}
        self.state = {}                      # what each step holds, filled when the source is chosen
        self.finish_text = "Add to the %s editor" % self.kind
        self.make_steps([("Start from", self.s_start), ("Names and texts", self.s_names), ("Who has it", self.s_who),
                       ("Numbers", self.s_values), ("Pictures", self.s_pictures), ("Check and add", self.s_check)]
                      if self.kind == "unit" else
                      [("Start from", self.s_start), ("Names and texts", self.s_names),
                       ("Who may build it", self.s_who), ("Pictures", self.s_pictures),
                       ("Check and add", self.s_check)])
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
                      factions=groups, keep_factions=True, pictures={lv: "" for lv in levels})
        st["orig_values"] = dict(st.get("values", {}))
        st["orig"] = {k: st.get(k) for k in ("name", "descr", "descr_short")} if self.kind == "unit" else \
            {old: (name, desc) for old, _, name, desc in st["levels"]}
        self.state = st

    def _level_texts(self, lv):
        """(name, description) players see for a level: its own key, else the first culture's own one (Medieval
        II keeps 'DO NOT TRANSLATE' under the plain key and the real names under <level>_<culture>)."""
        def real(t):
            return t and t.strip() != lv and "DO NOT TRANSLATE" not in t and not t.startswith("WARNING!")
        cults = sorted({c for _, c in self.mod.factions() if c})
        for suffix in [""] + ["_" + c for c in cults]:
            name = _text_value(self.mod, "export_buildings.txt", lv + suffix)
            if real(name):
                desc = _text_value(self.mod, "export_buildings.txt", lv + suffix + "_desc")
                return name, desc if real(desc) else ""
        return _text_value(self.mod, "export_buildings.txt", lv), ""

    # ---- moving between steps (gui_util.StepWindow) ----
    def leaving(self, step):
        if step == 0:
            self.load_source()

    def finish(self):
        return self.add()

    # ---- step 1 ----
    def s_start(self):
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
        lb = tk.Listbox(box, exportselection=False)
        sb = ttk.Scrollbar(box, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        info = ttk.Label(box, wraplength=330, justify="left")
        info.pack(side="left", fill="y", padx=10)
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
            if not src:
                return
            lines = self._lines(src)
            keys = ("category", "class", "ownership", "soldier") if self.kind == "unit" else ("levels",)
            info.configure(text="%s\n\n%s" % (src, "\n".join("%s: %s" % (k, self._val(lines, k)) for k in keys
                                                           if self._val(lines, k) is not None)))
        v_find.trace_add("write", fill)
        lb.bind("<<ListboxSelect>>", pick)
        fill()

    # ---- step 2 ----
    def s_names(self):
        st = self.state
        if self.kind == "unit":
            self._note("The name in the files (type) is what descr_strat and the buildings use; the dictionary "
                       "name keys its cards and texts (no spaces). Players see the name and descriptions.")
        else:
            self._note("The chain and each of its levels get names of their own in the files; players see "
                       "each level's name and description (the culture's and faction's own names are copied "
                       "under the new level names too). Texts left as they are stay the copied ones.")
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
            for r, (old, new, name, desc) in enumerate(st["levels"]):
                ttk.Label(inner, text="level %s" % old, font=("", 9, "bold")).grid(row=3 * r, column=0, sticky="w",
                                                                                  pady=(6, 0))
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
                       "of that culture) or 'all'. Picked from the copy; new owners get a copy of its cards.")
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

    # ---- pictures ----
    def s_pictures(self):
        st = self.state
        pics = st["pictures"]
        if self.kind == "unit":
            self._note("Without a picture of your own the new unit shows %s's card and description picture (a "
                       "copy under its own name). A picture of yours (PNG, JPG, TGA...) is put in the size and "
                       "format this mod's cards have." % st["src"])
            rows = [("card", "Unit card", E.unit_picture_need(self.mod)),
                    ("info", "Picture in the description", E.unit_picture_need(self.mod, True))]
        else:
            self._note("Without a picture of your own each new level shows the copied level's picture. A picture "
                       "of yours is put in the size of the mod's building pictures, for every culture folder.")
            names = dict((old, new) for old, new, _, _ in st["levels"])
            rows = [(old, "level %s" % names.get(old, old), None) for old in pics]
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

    # ---- the last step ----
    def op(self):
        st = self.state
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
             "pictures": {levels[k]: v for k, v in st["pictures"].items() if v and k in levels}}
        return st["src"], st["chain"], d

    def problems(self):
        st = self.state
        out = []
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
        return out

    def s_check(self):
        src, new, d = self.op()
        why = self.problems()
        plan = None
        if not why:
            from .plan import Plan
            try:
                plan = Plan(ModData(self.mod.data), "new_" + self.kind, "new_" + self.kind, {})
                if self.kind == "unit":
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
        self._note("%s %s from %s. Nothing is written yet: Add puts it into the %s editor's changes, written "
                   "with a backup on Apply (Restore undoes it). Below: every file it will change and how." % (
                       "New unit" if self.kind == "unit" else "New building chain", new, src, self.kind))
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
        self.ed.app.status.set("New %s %s from %s waits in the %s editor - Preview, then Apply." % (
            self.kind, op[1], op[0], self.kind))
        self.destroy()
