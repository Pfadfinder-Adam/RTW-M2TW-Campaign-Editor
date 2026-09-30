"""The Family tab (Edit faction) and the Character editor (its own work, any faction):
every character of a faction - on the map with their traits, ancillaries and portrait,
and the family members off the map (character_record) - and the family tree drawn the
way the game shows it: portraits, couples side by side, their children in the row below.
On the Family tab the picks are kept by the window (App.family_set, with Undo) and written
with the faction; the Character editor keeps its own per faction and writes them itself
(the editors' dirty / pending / make_plan / rebind, like the unit and building editors).
Both write through family.apply."""

import copy
import hashlib
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import family as FM

CARD_W, CARD_H, GAP, ROW = 150, 66, 16, 110
PIC_W, PIC_H = 40, 56                           # a portrait on a card (the game's are 69 x 96)
COUPLE_GAP = 10


class FamilyEditor(ttk.Frame):
    kind = "character"

    def __init__(self, master, app, standalone=False):
        super().__init__(master, padding=4)
        self.app, self.standalone = app, standalone
        self.states = {}                       # Character editor: {faction: family opts}
        self.mod, self._sig = None, None
        self._imgs = {}                        # PhotoImages kept alive: {(path, w, h): image}
        self.fam, self.faction, self._for = None, None, None
        self.traits, self.ancs, self.pool = {}, {}, {}
        self.sel = None                        # key of the picked person
        top = ttk.Frame(self)
        top.pack(fill="x")
        if standalone:
            ttk.Label(top, text="Faction", font=("", 10, "bold")).pack(side="left")
            self.v_fac = tk.StringVar()
            from .gui_util import FactionBox
            self.cb_fac = FactionBox(top, self.v_fac, state="readonly", width=26)
            self.cb_fac.pack(side="left", padx=4)
            self.cb_fac.bind("<<ComboboxSelected>>", lambda e: self.load())
        self.title = ttk.Label(top, text="" if standalone else "Edit faction: pick the faction on the Faction tab",
                               font=("", 10, "bold"))
        self.title.pack(side="left")
        ttk.Label(top, text="   Find").pack(side="left")
        self.v_find = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.v_find, width=18)
        e.pack(side="left", padx=4)
        e.bind("<KeyRelease>", lambda ev: self.fill_list())
        ttk.Button(top, text="Undo all changes here", command=self.reset).pack(side="right")
        if standalone:
            ttk.Button(top, text="Portrait library...", command=self.open_library).pack(side="right", padx=6)
        from .gui_util import first
        first(*[w for w in top.pack_slaves() if w.pack_info().get("side") == "right"][::-1])
        self.lib_adds = []                     # Character editor: [{'culture', 'group', 'pics': {age: src}}]
        ttk.Label(self, foreground="#555", justify="left", wraplength=1100, text=(
            "Everyone of the faction: characters on the map (name, age, traits, ancillaries) and family members "
            "off the map (name, sex, age). The tree is drawn like the game's: a couple side by side, their "
            "children below. Click a card or a row to edit that person. Names come from the faction's name lists "
            "(the game crashes on a name it has no string for); a renamed person is renamed on the tree too.")
                  ).pack(fill="x", pady=(2, 6))
        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes)
        panes.add(left, weight=2)
        right = ttk.LabelFrame(panes, text="Family tree", padding=2)
        panes.add(right, weight=5)

        # the people
        cols = (("name", "name", 140), ("kind", "who", 140), ("age", "age", 40), ("where", "where", 80))
        self.tv = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", height=7, selectmode="browse")
        for cid, text, w in cols:
            self.tv.heading(cid, text=text)
            self.tv.column(cid, width=w, stretch=cid == "name")
        self.tv.tag_configure("changed", background="#d9e6ff", foreground="#000000")
        self.tv.tag_configure("new", background="#d9f2d0", foreground="#000000")
        self.tv.pack(fill="x")
        self.tv.bind("<<TreeviewSelect>>", lambda e: self._picked_row())

        # the person's form
        # the form scrolls when the window is lower than it (the portrait, traits and ancillaries stay reachable)
        from .gui_util import ScrollFrame
        box = ttk.LabelFrame(left, text="Person", padding=4)
        box.pack(fill="both", expand=True, pady=(6, 0))
        sf = ScrollFrame(box)
        sf.pack(fill="both", expand=True)
        form = sf.inner
        self.form = box                           # its title names the person
        r = ttk.Frame(form)
        r.pack(fill="x")
        ttk.Label(r, text="Name").grid(row=0, column=0, sticky="w")
        self.v_first, self.v_last, self.v_age, self.v_sex = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.cb_first = ttk.Combobox(r, textvariable=self.v_first, width=16)
        self.cb_first.grid(row=0, column=1, padx=2)
        self.cb_last = ttk.Combobox(r, textvariable=self.v_last, width=16)
        self.cb_last.grid(row=0, column=2, padx=2)
        ttk.Label(r, text="Age").grid(row=0, column=3, padx=(8, 2))
        ttk.Spinbox(r, from_=0, to=120, textvariable=self.v_age, width=5).grid(row=0, column=4)
        self.sex_box = ttk.Frame(r)
        self.sex_box.grid(row=1, column=1, columnspan=3, sticky="w", pady=2)
        for s in ("male", "female"):
            ttk.Radiobutton(self.sex_box, text=s, value=s, variable=self.v_sex).pack(side="left")
        ttk.Button(r, text="Set name / age", command=self.set_basic).grid(row=1, column=4, pady=2)
        self.lbl_who = ttk.Label(form, text="", foreground="#555", wraplength=420, justify="left")
        self.lbl_who.pack(fill="x", pady=(2, 4))
        fb = ttk.Frame(form)
        fb.pack(fill="x", pady=(0, 4))
        ttk.Button(fb, text="Give a wife...", command=self.add_wife).pack(side="left")
        ttk.Button(fb, text="Add a child...", command=self.add_child).pack(side="left", padx=4)
        ttk.Button(fb, text="Take off the tree", command=self.off_tree).pack(side="left")
        ttk.Button(fb, text="Leave out", command=self.leave_out).pack(side="left", padx=4)

        pf = ttk.LabelFrame(form, text="Portrait  (a click on a picture saves a copy)", padding=2)
        pf.pack(fill="x")
        self.pic_boxes = {}
        for a in FM.AGES:
            box = ttk.Frame(pf)
            box.pack(side="left", padx=4)
            lab = tk.Label(box, text=a, width=7, height=4, relief="sunken", bg="#ddd")
            lab.pack()
            b = ttk.Button(box, text="Replace...", command=lambda a=a: self.replace_portrait(a))
            b.pack(pady=1)
            # a click on the picture saves a copy of it (the portrait as it is now)
            lab.bind("<Button-1>", lambda e, lab=lab, a=a: self.save_portrait(lab, a))
            lab.configure(cursor="hand2")
            self.pic_boxes[a] = (lab, b)
        side = ttk.Frame(pf)
        side.pack(side="left", padx=6, fill="both", expand=True)
        self.lbl_pic = ttk.Label(side, text="", foreground="#555", wraplength=230, justify="left", font=("", 8))
        self.lbl_pic.pack(side="top", anchor="w", fill="x")
        self.b_pool = ttk.Button(side, text="Portrait library...", command=self.open_library)

        tr = ttk.LabelFrame(form, text="Traits (level)", padding=2)
        tr.pack(fill="both", expand=True)
        self.tv_tr = ttk.Treeview(tr, columns=("trait", "level", "lname"), show="headings", height=4)
        for cid, text, w in (("trait", "trait", 150), ("level", "level", 45), ("lname", "level name", 170)):
            self.tv_tr.heading(cid, text=text)
            self.tv_tr.column(cid, width=w, stretch=cid == "lname")
        self.tv_tr.pack(fill="both", expand=True)
        tb = ttk.Frame(tr)
        tb.pack(fill="x", pady=2)
        self.v_trait, self.v_level = tk.StringVar(), tk.StringVar(value="1")
        self.cb_trait = ttk.Combobox(tb, textvariable=self.v_trait, width=22)
        self.cb_trait.pack(side="left")
        ttk.Spinbox(tb, from_=1, to=10, textvariable=self.v_level, width=4).pack(side="left", padx=2)
        ttk.Button(tb, text="Add / set", command=self.add_trait).pack(side="left", padx=2)
        ttk.Button(tb, text="Remove", command=self.remove_trait).pack(side="left")
        self.tv_tr.bind("<<TreeviewSelect>>", lambda e: self._trait_row())

        an = ttk.LabelFrame(form, text="Ancillaries (retinue)", padding=2)
        an.pack(fill="x", pady=(4, 0))
        self.lb_an = tk.Listbox(an, height=3, exportselection=False)
        self.lb_an.pack(fill="x")
        ab = ttk.Frame(an)
        ab.pack(fill="x", pady=2)
        self.v_anc = tk.StringVar()
        self.cb_anc = ttk.Combobox(ab, textvariable=self.v_anc, width=24)
        self.cb_anc.pack(side="left")
        ttk.Button(ab, text="Add", command=self.add_anc).pack(side="left", padx=2)
        ttk.Button(ab, text="Remove", command=self.remove_anc).pack(side="left")
        self.char_parts = [tr, an]

        # the tree
        self.cv = tk.Canvas(right, bg="#efe6d2", highlightthickness=0)
        xs = ttk.Scrollbar(right, orient="horizontal", command=self.cv.xview)
        ys = ttk.Scrollbar(right, orient="vertical", command=self.cv.yview)
        self.cv.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<ButtonPress-3>", lambda e: self.cv.scan_mark(e.x, e.y))
        self.cv.bind("<B3-Motion>", lambda e: self.cv.scan_dragto(e.x, e.y, gain=1))
        self.cv.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", lambda x: self.cv.yview_scroll(
            int(-x.delta / 120), "units")))
        self.cv.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))

    # ---------------------------------------------------------------- data
    @property
    def st(self):
        if self.standalone:
            return self.states.setdefault(self.faction, {}) if self.faction else {}
        return self.app.family_set

    def campaign(self):
        return self.app.v_campaign.get()

    def _manhood(self):
        """The mod's age of manhood (REX descr_ex.txt / M2TW descr_campaign_db.xml, else 16)."""
        from .limits import manhood_age
        mod = self.mod if self.standalone else self.app.mod
        try:
            return manhood_age(mod) if mod else FM.MAX_RECORD_AGE
        except Exception:
            return FM.MAX_RECORD_AGE

    def path(self):
        mod = self.mod if self.standalone else self.app.mod
        try:
            return mod.campaign_file(self.campaign(), "descr_strat.txt") if mod else None
        except Exception:
            return None

    def load(self, mod=None):
        app = self.app
        if self.standalone:
            if mod is not None:
                self.mod = mod
            if not self.mod:
                return
            s = app.strat
            names = [fb.name for fb in s.factions] if s else []
            self.cb_fac.set_names(names, app.shown_names())
            if self.v_fac.get() not in names:
                self.v_fac.set(names[0] if names else "")
            faction = self.v_fac.get()
        else:
            faction = app.v["template"].get().strip() if app.editing() else ""
        if not app.mod or not faction or not app.strat or not app.strat.faction(faction):
            self.fam, self.faction = None, None
            self.title.configure(text="Edit faction: pick the faction on the Faction tab")
            self.redraw()
            return
        path = self.path()
        key = (app.mod.data, path, faction)
        if self._for != key:
            try:
                self.fam = FM.read(app.mod.load(path), faction)
                self.traits, self.ancs = FM.trait_list(app.mod), FM.ancillary_list(app.mod)
                self.pool = app.pool_for(faction) if hasattr(app, "pool_for") else (app.mod.name_pool(faction) or {})
            except Exception as e:
                messagebox.showerror("Family", str(e))
                self.fam = None
                return
            self.faction, self._for, self.sel = faction, key, None
            self.m2 = self.fam["medieval"]
            if self.standalone and self._sig is None:
                self._sig = self._signature()
        self.title.configure(text=("  people and family" if self.standalone else "People and family of %s" % faction))
        self.redraw()

    # ---- as an editor of its own (Character editor), like the unit and building editors ----
    def _signature(self):
        p = self.path()
        try:
            with open(p, "rb") as fh:
                return hashlib.md5(fh.read()).hexdigest()
        except (OSError, TypeError):
            return None

    def dirty(self):
        return bool(self.lib_adds) or any(v for st in self.states.values() for v in st.values())

    def pending(self):
        n = len(self.lib_adds)
        for st in self.states.values():
            n += len(st.get("people") or {}) + len(st.get("new") or []) + len(st.get("remove") or []) + \
                len(st.get("portraits") or {}) + (1 if st.get("tree") is not None else 0)
        return n

    def rebind(self, mod):
        """The window loaded the mod again: changes wait while descr_strat is as it was read."""
        lost = 0
        if self.mod is not None and self.dirty() and mod.data == self.mod.data:
            self.mod = mod
            if self._signature() != self._sig:
                lost = self.pending()
                self.states, self.lib_adds = {}, []
        else:
            self.states, self.lib_adds = {}, []
        self.mod, self._for = mod, None
        self._sig = self._signature()
        self.load(mod)
        return lost

    def make_plan(self):
        from .moddata import ModData
        from .plan import Plan
        if not self.mod:
            raise ValueError("load a mod first")
        if not self.dirty():
            raise ValueError("nothing changed in the Character editor")
        mod = ModData(self.mod.data)
        plan = Plan(mod, "characters", "characters", {})
        f = plan.edit(mod.campaign_file(self.campaign(), "descr_strat.txt"))
        for faction, st in self.states.items():
            if any(st.values()):
                FM.apply(plan, f, faction, st)
        from . import portraits as PL
        for a in self.lib_adds:
            PL.add(plan, a["culture"], a["group"], [a["pics"]])
        return plan

    def open_library(self):
        if not self.standalone:
            # the Family tab writes with the faction; new pool pictures are the Character editor's own write
            app = self.app
            app.v_work.set("characters")
            app.work_changed()
            ed = app.editor()
            if ed is not None and ed.mod:
                app.status.set("Portrait library: new pictures are written with the Character editor's Apply.")
                PortraitLibrary(ed)
            return
        if not self.mod:
            return
        PortraitLibrary(self)

    def forget(self):
        self._for, self.fam, self.sel = None, None, None
        self._imgs.clear()

    def people(self):
        """Everyone as they will be: [dict] with 'changed' / 'new' marks."""
        if not self.fam:
            return []
        ch, gone = self.st.get("people") or {}, set(self.st.get("remove") or [])
        out = []
        for p in self.fam["people"]:
            if p.key in gone:
                continue
            d = p.as_dict()
            c = ch.get(p.key) or {}
            d.update({k: copy.deepcopy(v) for k, v in c.items() if v is not None})
            d["changed"], d["new"] = bool(c) or p.key in (self.st.get("portraits") or {}), False
            out.append(d)
        for i, n in enumerate(self.st.get("new") or []):
            out.append({"key": "new:%d" % i, "name": n["name"], "source": "record", "kind": "record",
                        "sex": n.get("sex", "male"), "age": n.get("age"), "role": None, "status": "alive",
                        "xy": None, "traits": [], "ancillaries": [], "changed": False, "new": True})
        return out

    def tree(self):
        if self.st.get("tree") is not None:
            return self.st["tree"]
        if not self.fam:
            return []
        ren = {}
        for k, c in (self.st.get("people") or {}).items():
            p = next((p for p in self.fam["people"] if p.key == k), None)
            if p and c.get("name") and c["name"] != p.name:
                ren[p.name] = c["name"]
        return [[ren.get(a, a), ren.get(b, b), [ren.get(k, k) for k in ks]] for a, b, ks in self.fam["tree"]]

    def person(self, key):
        return next((p for p in self.people() if p["key"] == key), None)

    # ---- portraits ----
    def portrait_info(self, p):
        wives = {b for _, b, _ in self.tree()}
        d = dict(p, wife=p["name"] in wives)
        info = FM.portraits(self.app.mod, self.faction, d, getattr(self, "m2", False))
        new = (self.st.get("portraits") or {}).get(p["key"]) or {}
        return info, new

    def image(self, path, w, h):
        """A picture file as a PhotoImage of w x h (kept), or None."""
        if not path:
            return None
        k = (path, w, h)
        if k not in self._imgs:
            try:
                from PIL import Image, ImageTk
                with Image.open(path) as im:
                    im = im.convert("RGBA")
                    im.thumbnail((w, h))
                    self._imgs[k] = ImageTk.PhotoImage(im)
            except Exception:
                self._imgs[k] = None
        return self._imgs[k]

    def card_picture(self, p):
        info, new = self.portrait_info(p)
        age = "old" if (p.get("age") or 0) >= 45 else "young"
        return new.get(age) or new.get("young") or info["files"].get(age) or info["files"].get("young") or \
            info["sample"]

    def fill_portrait(self, p):
        info, new = self.portrait_info(p)
        own = getattr(self, "m2", False) and p["source"] == "map"
        for a, (lab, b) in self.pic_boxes.items():
            samples = info.get("samples") or {}
            path = new.get(a) or info["files"].get(a) or samples.get(a) or (info["sample"] if a == "young" else None)
            if a != "young" and not (new.get(a) or info["files"].get(a)) and new.get("young"):
                path = new["young"]
            img = self.image(path, 52, 72)
            lab.configure(image=img or "", text="" if img else a, width=52 if img else 7, height=72 if img else 4)
            lab.image, lab.path = img, path
            # Replace only where the game takes a portrait of one's own (Medieval II, on the map)
            if own:
                b.pack(pady=1)
            else:
                b.pack_forget()
        rome = not getattr(self, "m2", False) and p["source"] == "map"
        if rome:
            self.b_pool.pack(side="bottom", anchor="w", padx=6, pady=2)
        else:
            self.b_pool.pack_forget()
        text = info["how"]
        if new:
            text = "new portrait on Apply (%s) - " % ", ".join(sorted(new)) + text
        if rome:
            text += (" (the same man young, old and dead). Rome gives no portrait of one's own to a character - "
                     "to see your own pictures in the game, add them to the pool:")
        self.lbl_pic.configure(text=text)

    def save_portrait(self, lab, age):
        """A click on a portrait: a copy of the picture saved where the user picks (as it is, or PNG)."""
        from .gui_util import save_copy
        if getattr(lab, "path", None):
            save_copy(self, lab.path, "the %s portrait" % age)

    def replace_portrait(self, age):
        from tkinter import filedialog
        p = self.person(self.sel)
        if not p or p["source"] != "map" or not getattr(self, "m2", False):
            return
        src = filedialog.askopenfilename(parent=self, title="Portrait (%s) of %s" % (age, p["name"]), filetypes=[
            ("Pictures", "*.png *.jpg *.jpeg *.tga *.bmp *.dds"), ("All files", "*.*")])
        if not src:
            return
        self._before()
        self.st.setdefault("portraits", {}).setdefault(p["key"], {})[age] = src
        self.changed()

    def changed(self):
        self.app.status.set("%s: changes waiting - Preview, then Apply changes." % (
            "Character editor" if self.standalone else "Family"))
        self.redraw()
        if self.standalone:
            self.app._mark_work()

    def _before(self):
        if not self.standalone:                 # the Character editor's own changes are not in the window's Undo
            self.app.remember()

    def _own_tree(self):
        """The tree as the window's own list (made from the file on the first change)."""
        if self.st.get("tree") is None:
            self.st["tree"] = copy.deepcopy(self.tree())
        return self.st["tree"]

    # ---------------------------------------------------------------- showing
    def redraw(self):
        self.fill_list()
        self.fill_form()
        self.draw_tree()

    def fill_list(self):
        self.tv.delete(*self.tv.get_children())
        q = self.v_find.get().strip().lower()
        for p in self.people():
            if q and q not in p["name"].lower():
                continue
            kind = p["kind"] if p["source"] == "map" else ("woman" if p["sex"] == "female" else "man")
            if p.get("role"):
                kind += ", " + p["role"]
            tag = "new" if p["new"] else ("changed" if p["changed"] else "")
            self.tv.insert("", "end", iid=p["key"], values=(p["name"], kind, p["age"] if p["age"] is not None else "",
                                                           "on the map" if p["source"] == "map" else "off the map"),
                           tags=(tag,))
        if self.sel and self.tv.exists(self.sel):
            self.tv.selection_set(self.sel)
            self.tv.see(self.sel)

    def _picked_row(self):
        s = self.tv.selection()
        if s and s[0] != self.sel:
            self.sel = s[0]
            self.fill_form()
            self.draw_tree()

    def fill_form(self):
        p = self.person(self.sel) if self.sel else None
        if not p:
            self.form.configure(text="Person - pick one in the list or on the tree")
            for v in (self.v_first, self.v_last, self.v_age):
                v.set("")
            self.tv_tr.delete(*self.tv_tr.get_children())
            self.lb_an.delete(0, "end")
            self.lbl_who.configure(text="")
            for lab, b in self.pic_boxes.values():
                lab.configure(image="", text="", width=7, height=4)
                b.configure(state="disabled")
            self.lbl_pic.configure(text="")
            return
        self.form.configure(text="Person: %s" % p["name"])
        first = p["name"].split(" ")[0]
        self.v_first.set(first)
        self.v_last.set(p["name"][len(first):].strip())
        self.v_age.set(str(p["age"] or ""))
        self.v_sex.set(p["sex"])
        self.cb_first["values"] = self.pool.get("women" if p["sex"] == "female" else "characters", [])
        self.cb_last["values"] = [""] + self.pool.get("surnames", [])
        rec = p["source"] != "map"
        for w in self.sex_box.winfo_children():
            w.configure(state="normal" if rec else "disabled")
        if rec:
            who = "Off the map (character_record): the game keeps only the name, sex and age of such a person."
        else:
            who = "On the map at %d, %d: %s%s." % (p["xy"][0], p["xy"][1], p["kind"],
                                                   ", " + p["role"] if p.get("role") else "") if p.get("xy") else p["kind"]
        self.lbl_who.configure(text=who)
        self.fill_portrait(p)
        self.tv_tr.delete(*self.tv_tr.get_children())
        for i, (t, n) in enumerate(p["traits"]):
            levels = (self.traits.get(t) or {}).get("levels") or []
            self.tv_tr.insert("", "end", iid=str(i), values=(t, n, levels[n - 1] if 0 < n <= len(levels) else ""))
        self.lb_an.delete(0, "end")
        for a in p["ancillaries"]:
            self.lb_an.insert("end", a)
        kind = FM.trait_kind(p["kind"])
        # traits for this kind of character (`Characters all` fits everyone); ancillaries not barred to the
        # faction's culture (ExcludeCultures)
        self.cb_trait["values"] = sorted(t for t, info in self.traits.items()
                                         if not info["characters"] or kind in info["characters"]
                                         or "all" in info["characters"])
        try:
            mod = self.mod if self.standalone else self.app.mod
            culture = mod.culture(self.faction) if self.faction and mod else None
        except Exception:
            culture = None
        self.cb_anc["values"] = sorted(a for a, info in self.ancs.items()
                                       if not culture or culture not in (info.get("exclude") or []))
        for part in self.char_parts:
            for w in part.winfo_children():
                for x in [w] + list(w.winfo_children()):
                    try:
                        x.configure(state="disabled" if rec else "normal")
                    except tk.TclError:
                        pass

    def _trait_row(self):
        s = self.tv_tr.selection()
        p = self.person(self.sel)
        if s and p:
            t, n = p["traits"][int(s[0])]
            self.v_trait.set(t)
            self.v_level.set(str(n))

    # ---------------------------------------------------------------- the tree
    def draw_tree(self):
        cv = self.cv
        cv.delete("all")
        if not self.fam:
            cv.create_text(20, 20, anchor="nw", fill="#555", text="Load a mod and pick the faction above." if
                           self.standalone else "Pick the faction on the Faction tab (Edit faction).")
            return
        people = {p["name"]: p for p in self.people() if p["source"] == "record" or
                  p["kind"] in ("named character", "princess")}
        tree = self.tree()
        couples = {a: (a, b, ks) for a, b, ks in tree}
        kids = {k for _, _, ks in tree for k in ks}
        roots = [a for a, b, _ in tree if a not in kids and b not in kids]
        placed = {}

        def width(name, seen=()):
            if name in seen:
                return CARD_W
            c = couples.get(name)
            own = 2 * CARD_W + COUPLE_GAP if c and c[1] else CARD_W
            if not c or not c[2]:
                return own
            return max(own, sum(width(k, seen + (name,)) for k in c[2]) + GAP * (len(c[2]) - 1))

        def place(name, x, y, seen=()):
            """Lays out name (and wife, and children below) in [x, x + width); returns the
            x of the card's middle, where the line from the parents ends."""
            w = width(name, seen)
            c = couples.get(name)
            own = 2 * CARD_W + COUPLE_GAP if c and c[1] else CARD_W
            cx = x + (w - own) / 2
            placed[name] = (cx, y)
            if c and c[1]:
                placed[c[1]] = (cx + CARD_W + COUPLE_GAP, y)
            if c and c[2] and name not in seen:
                kx = x + (w - (sum(width(k, seen + (name,)) for k in c[2]) + GAP * (len(c[2]) - 1))) / 2
                mid = cx + own / 2
                bar = y + CARD_H + (ROW - CARD_H) / 2
                cv.create_line(mid, y + CARD_H / 2, mid, bar, fill="#6b5a3a", width=2)
                ends = []
                for k in c[2]:
                    kw = width(k, seen + (name,))
                    kxm = place(k, kx, y + ROW, seen + (name,))
                    ends.append(kxm)
                    cv.create_line(kxm, bar, kxm, y + ROW, fill="#6b5a3a", width=2)
                    kx += kw + GAP
                cv.create_line(min(ends + [mid]), bar, max(ends + [mid]), bar, fill="#6b5a3a", width=2)
            return cx + CARD_W / 2

        x = 20
        for r in roots:
            place(r, x, 20)
            x += width(r) + 3 * GAP
        bottom = max([y for _, y in placed.values()] + [20]) + ROW + 10
        loose = [n for n, p in people.items() if n not in placed]
        if loose:
            cv.create_text(20, bottom, anchor="nw", text="Not on the tree:", fill="#5a4a2a", font=("", 9, "bold"))
            lx, ly = 20, bottom + 20
            for n in loose:
                placed[n] = (lx, ly)
                lx += CARD_W + GAP
                if lx > 20 + 6 * (CARD_W + GAP):
                    lx, ly = 20, ly + CARD_H + GAP
        for a, b, _ in tree:
            if a in placed and b in placed and b:
                (x1, y1), (x2, y2) = placed[a], placed[b]
                if y1 == y2 and abs(x2 - x1 - CARD_W - COUPLE_GAP) < 1:
                    cv.create_line(x1 + CARD_W, y1 + CARD_H / 2, x2, y2 + CARD_H / 2, fill="#a0364b", width=3)
        for n, (x, y) in placed.items():
            self._card(n, people.get(n), x, y)
        cv.configure(scrollregion=cv.bbox("all") or (0, 0, 100, 100))

    def _card(self, name, p, x, y):
        cv = self.cv
        female = p and p["sex"] == "female"
        fill = "#f6dfe3" if female else "#dfe7f3"
        if p is None:
            fill = "#e0e0e0"
        sel = p is not None and p["key"] == self.sel
        tag = "card:%s" % (p["key"] if p else name)
        cv.create_rectangle(x, y, x + CARD_W, y + CARD_H, fill=fill, outline="#1c5bd6" if sel else "#6b5a3a",
                            width=3 if sel else 1, tags=(tag,))
        crown = ""
        if p and p.get("role") == "leader":
            crown = "♛ "
        elif p and p.get("role") == "heir":
            crown = "♘ "
        tx = x + 6
        img = self.image(self.card_picture(p), PIC_W, PIC_H) if p else None
        if img:
            cv.create_image(x + 4, y + (CARD_H - PIC_H) / 2, anchor="nw", image=img, tags=(tag,))
            tx = x + PIC_W + 8
        cv.create_text(tx, y + 5, anchor="nw", text=crown + name, width=x + CARD_W - tx - 4,
                       font=("", 9, "bold"), fill="#222", tags=(tag,))
        if p is None:
            sub = "nobody of the faction!"
        else:
            where = "on the map" if p["source"] == "map" else "off the map"
            sub = "age %s, %s" % (p["age"] if p["age"] is not None else "?", where)
            if p.get("role"):
                sub = "%s, %s" % (p["role"], sub)
        cv.create_text(tx, y + CARD_H - 5, anchor="sw", text=sub, width=x + CARD_W - tx - 4, font=("", 8),
                       fill="#444", tags=(tag,))
        if p and (p["changed"] or p["new"]):
            cv.create_oval(x + CARD_W - 12, y + 4, x + CARD_W - 4, y + 12, fill="#2a9d3a" if p["new"] else "#1c5bd6",
                           outline="", tags=(tag,))
        if p:
            cv.tag_bind(tag, "<Button-1>", lambda e, k=p["key"]: self.pick(k))

    def pick(self, key):
        self.sel = key
        self.fill_list()
        self.fill_form()
        self.draw_tree()

    # ---------------------------------------------------------------- changes
    def _change(self, p, **kw):
        """Store a change of person p (a file person or a new one)."""
        if p["new"]:
            n = self.st["new"][int(p["key"].split(":")[1])]
            n.update({k: v for k, v in kw.items() if k in ("name", "sex", "age")})
            return
        ch = self.st.setdefault("people", {}).setdefault(p["key"], {})
        ch.update(kw)
        orig = next(x for x in self.fam["people"] if x.key == p["key"])
        for k in list(ch):
            if ch[k] == getattr(orig, k, None):
                del ch[k]
        if not ch:
            del self.st["people"][p["key"]]

    def set_basic(self):
        p = self.person(self.sel)
        if not p:
            return
        name = (self.v_first.get().strip() + " " + self.v_last.get().strip()).strip()
        sex = self.v_sex.get() if p["source"] != "map" else p["sex"]
        if not name:
            return
        if name != p["name"]:
            why = FM.check_name(self.pool, name, sex, self.faction)
            if why:
                messagebox.showerror("Family", why)
                return
            if any(x["name"] == name for x in self.people()):
                messagebox.showerror("Family", "%s is already the name of someone of the faction - "
                                               "the family tree could not tell them apart" % name)
                return
        age = self.v_age.get().strip()
        if age and not age.isdigit():
            messagebox.showerror("Family", "The age is a whole number")
            return
        self._before()
        if name != p["name"] and self.st.get("tree") is not None:   # a tree of its own names people itself
            for c in self.st["tree"]:
                c[0] = name if c[0] == p["name"] else c[0]
                c[1] = name if c[1] == p["name"] else c[1]
                c[2] = [name if k == p["name"] else k for k in c[2]]
        self._change(p, name=name, age=int(age) if age else p["age"], sex=sex)
        self.changed()

    def add_trait(self):
        p = self.person(self.sel)
        t = self.v_trait.get().strip()
        if not p or p["source"] != "map" or not t:
            return
        info = self.traits.get(t)
        if self.traits and info is None:
            messagebox.showerror("Family", "%s is not a trait of this mod" % t)
            return
        try:
            n = int(self.v_level.get())
        except ValueError:
            return
        top = len(info["levels"]) if info and info["levels"] else n
        if not 1 <= n <= top:
            messagebox.showerror("Family", "%s has levels 1-%d" % (t, top))
            return
        traits = [list(x) for x in p["traits"]]
        anti = set(info["anti"]) if info else set()
        clash = [x for x, _ in traits if x in anti]
        if clash:
            messagebox.showerror("Family", "%s is the opposite of %s - take that one off first" % (t, clash[0]))
            return
        hit = next((x for x in traits if x[0] == t), None)
        if hit:
            hit[1] = n
        else:
            traits.append([t, n])
        self._before()
        self._change(p, traits=traits)
        self.changed()

    def remove_trait(self):
        p = self.person(self.sel)
        s = self.tv_tr.selection()
        if not p or not s:
            return
        traits = [list(x) for i, x in enumerate(p["traits"]) if str(i) != s[0]]
        self._before()
        self._change(p, traits=traits)
        self.changed()

    def add_anc(self):
        p = self.person(self.sel)
        a = self.v_anc.get().strip()
        if not p or p["source"] != "map" or not a or a in p["ancillaries"]:
            return
        if self.ancs and a not in self.ancs:
            messagebox.showerror("Family", "%s is not an ancillary of this mod" % a)
            return
        self._before()
        self._change(p, ancillaries=list(p["ancillaries"]) + [a])
        self.changed()

    def remove_anc(self):
        p = self.person(self.sel)
        s = self.lb_an.curselection()
        if not p or not s:
            return
        self._before()
        self._change(p, ancillaries=[a for i, a in enumerate(p["ancillaries"]) if i != s[0]])
        self.changed()

    def _ask_person(self, title, sex, age, surname=""):
        """(name, age) for a new person from the name lists, or None."""
        names = self.pool.get("women" if sex == "female" else "characters", [])
        taken = {p["name"] for p in self.people()}
        free = next((n for n in names if (n + (" " + surname if surname else "")) not in taken), names[0] if names else "")
        d = _PersonDialog(self, title, names, [""] + self.pool.get("surnames", []), free, surname, age)
        if not d.result:
            return None
        name, a = d.result
        why = FM.check_name(self.pool, name, sex, self.faction)
        if why:
            messagebox.showerror("Family", why)
            return None
        if name in taken:
            messagebox.showerror("Family", "%s is already the name of someone of the faction" % name)
            return None
        most = self._manhood()
        if sex == "male" and a not in (None, "") and int(a) > most:
            messagebox.showerror("Family", "A new son is written off the map, and the game crashes on a living man "
                                 "off the map older than %d (this mod's age of manhood). Give him an age of %d or "
                                 "less - he comes of age in the game by himself." % (most, most))
            return None
        return name, a

    def _picked(self):
        """The person picked in the list or on the tree, or None with a word on what to do."""
        p = self.person(self.sel)
        if not p:
            messagebox.showinfo("Family", "Pick a person first: a row in the list or a card on the tree.")
        return p

    def _off_tree(self, sex=None, but=()):
        """People of the faction no couple has as a child yet (and not in `but`), of one sex if given."""
        kids = {k for _, _, ks in self.tree() for k in ks}
        return [x for x in self.people() if x["name"] not in kids and x["name"] not in but
                and (sex is None or x["sex"] == sex)]

    def _choose(self, title, people):
        """A name from people already in the faction, "" for someone new, or None (cancelled)."""
        if not people:
            return ""
        w = tk.Toplevel(self)
        w.title(title)
        w.transient(self.winfo_toplevel())
        ttk.Label(w, text="Someone already in the faction, or a new person from the name lists:",
                  padding=(10, 8, 10, 2)).pack(anchor="w")
        lb = tk.Listbox(w, height=min(10, len(people)), width=46, exportselection=False)
        for x in people:
            lb.insert("end", "%s  (%s, age %s, %s)" % (x["name"], x["sex"], x.get("age") or "?",
                                                       "on the map" if x["source"] == "map" else "off the map"))
        lb.pack(fill="both", expand=True, padx=10)
        lb.selection_set(0)
        out = {"v": None}

        def done(v):
            out["v"] = v
            w.destroy()
        bar = ttk.Frame(w, padding=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="This one", command=lambda: done(people[lb.curselection()[0]]["name"]
                                                            if lb.curselection() else None)).pack(side="left")
        ttk.Button(bar, text="Someone new...", command=lambda: done("")).pack(side="left", padx=4)
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")
        lb.bind("<Double-Button-1>", lambda e: done(people[lb.curselection()[0]]["name"]))
        w.grab_set()
        self.wait_window(w)
        return out["v"]

    def add_wife(self):
        p = self._picked()
        if not p:
            return
        if p["sex"] != "male":
            messagebox.showinfo("Family", "Pick the husband: a couple on the tree is written under the man.")
            return
        tree = self.tree()
        if any(a == p["name"] and b for a, b, _ in tree):
            messagebox.showinfo("Family", "%s has a wife already." % p["name"])
            return
        wives = {b for _, b, _ in tree if b}
        pick = self._choose("Wife of %s" % p["name"], [x for x in self._off_tree("female") if x["name"] not in wives])
        if pick is None:
            return
        if pick:
            got = (pick, None)
        else:
            got = self._ask_person("Wife of %s" % p["name"], "female", max(16, (p["age"] or 30) - 3))
            if not got:
                return
        self._before()
        t = self._own_tree()
        if not pick:
            self.st.setdefault("new", []).append({"name": got[0], "sex": "female", "age": got[1]})
        hit = next((c for c in t if c[0] == p["name"]), None)
        if hit:
            hit[1] = got[0]
        else:
            t.append([p["name"], got[0], []])
        self.changed()

    def add_child(self):
        p = self._picked()
        if not p:
            return
        tree = self.tree()
        couple = next((c for c in tree if p["name"] in (c[0], c[1])), None)
        if not couple or not couple[1]:
            messagebox.showinfo("Family", "Give %s a wife first: a child is written under a couple." % p["name"]
                                if p["sex"] == "male" else "Pick a married man or woman.")
            return
        father = couple[0]
        # someone already in the faction as the child (a new faction's heir as its leader's son)
        pick = self._choose("Child of %s and %s" % (couple[0], couple[1]), self._off_tree(but=couple[:2]))
        if pick is None:
            return
        if pick:
            self._before()
            t = self._own_tree()
            next(c for c in t if c[0] == father)[2].append(pick)
            self.changed()
            return
        sex = "female" if messagebox.askyesno("Family", "A daughter? (No = a son)") else "male"
        first = father.split(" ")[0]
        surname = father[len(first):].strip() if sex == "male" else ""
        by = {x["name"]: x for x in self.people()}
        young = min([(by.get(n) or {}).get("age") or 40 for n in couple[:2]])
        got = self._ask_person("Child of %s and %s" % (couple[0], couple[1]), sex,
                                min(self._manhood(), max(1, young - 20)) if sex == "male" else max(1, young - 20),
                                surname)
        if not got:
            return
        self._before()
        t = self._own_tree()
        self.st.setdefault("new", []).append({"name": got[0], "sex": sex, "age": got[1]})
        c = next(c for c in t if c[0] == father)
        c[2].append(got[0])
        self.changed()

    def off_tree(self):
        p = self._picked()
        if not p:
            return
        t = self.tree()
        if any(a == p["name"] and ks for a, b, ks in t) or any(b == p["name"] and ks for a, b, ks in t):
            messagebox.showerror("Family", "%s has children on the tree - take them off first." % p["name"])
            return
        self._before()
        t = self._own_tree()
        t[:] = [c for c in t if c[0] != p["name"]]
        for c in t:
            if c[1] == p["name"]:
                c[1] = ""
            c[2] = [k for k in c[2] if k != p["name"]]
        bad = [c for c in t if not c[1]]
        if bad:
            messagebox.showinfo("Family", "%s is off the tree; %s has no wife now - give him one or take the "
                                          "couple off." % (p["name"], bad[0][0]))
        self.changed()

    def leave_out(self):
        p = self._picked()
        if not p:
            return
        if p["source"] == "map":
            messagebox.showinfo("Family", "%s is on the map: remove characters on the map in Units & armies "
                                          "(family members are never removed there)." % p["name"])
            return
        if any(p["name"] in (a, b) for a, b, _ in self.tree()) or any(p["name"] in ks for _, _, ks in self.tree()):
            messagebox.showerror("Family", "Take %s off the tree first." % p["name"])
            return
        self._before()
        if p["new"]:
            del self.st["new"][int(p["key"].split(":")[1])]
        else:
            self.st.setdefault("remove", []).append(p["key"])
            (self.st.get("people") or {}).pop(p["key"], None)
        self.sel = None
        self.changed()

    def reset(self):
        self._before()
        self.st.clear()
        self.changed()

    def leave(self):
        """Nothing here for the window's Undo to put back."""


class _PersonDialog(simpledialog.Dialog):
    def __init__(self, master, title, firsts, surnames, first, surname, age):
        self.firsts, self.surnames, self.first, self.surname, self.age = firsts, surnames, first, surname, age
        self.result = None
        super().__init__(master, title)

    def body(self, m):
        ttk.Label(m, text="Name (from the faction's name lists)").grid(row=0, column=0, columnspan=3, sticky="w")
        self.v1, self.v2, self.va = tk.StringVar(value=self.first), tk.StringVar(value=self.surname), \
            tk.StringVar(value=str(self.age))
        c = ttk.Combobox(m, textvariable=self.v1, values=self.firsts, width=18)
        c.grid(row=1, column=0, padx=2)
        ttk.Combobox(m, textvariable=self.v2, values=self.surnames, width=18).grid(row=1, column=1, padx=2)
        ttk.Label(m, text="Age").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(m, from_=0, to=100, textvariable=self.va, width=6).grid(row=2, column=1, sticky="w", pady=(6, 0))
        return c

    def validate(self):
        return bool(self.v1.get().strip()) and self.va.get().strip().isdigit()

    def apply(self):
        self.result = ((self.v1.get().strip() + " " + self.v2.get().strip()).strip(), int(self.va.get()))


class PortraitLibrary(tk.Toplevel):
    """The game's portraits of a culture, as the game gives them to characters, and new ones added
    (Add portraits...: any PNG / JPG / TGA, made the size and depth of the culture's own, with its card,
    under the next free number in every folder of the group). Medieval II: 'Use for ...' gives the
    picked portrait to the picked character as a portrait of his own."""

    def __init__(self, ed):
        super().__init__(ed)
        from . import portraits as PL
        self.ed, self.PL = ed, PL
        self.title("Portrait library")
        self.geometry("980x720")
        self.transient(ed.winfo_toplevel())
        mod = ed.mod
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Culture").pack(side="left")
        cults = PL.cultures(mod)
        own = FM.portrait_culture(mod, ed.faction) if ed.faction else None
        self.v_c = tk.StringVar(value=own if own in cults else (cults[0] if cults else ""))
        cb = ttk.Combobox(top, textvariable=self.v_c, values=cults, state="readonly", width=16)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.load())
        ttk.Label(top, text="Group").pack(side="left", padx=(10, 0))
        self.v_g = tk.StringVar()
        self.cb_g = ttk.Combobox(top, textvariable=self.v_g, state="readonly", width=14)
        self.cb_g.pack(side="left", padx=4)
        self.cb_g.bind("<<ComboboxSelected>>", lambda e: self.show())
        self.v_age = tk.StringVar(value="young")
        for a in ("young", "old", "dead"):
            ttk.Radiobutton(top, text=a, value=a, variable=self.v_age, command=self.show).pack(side="left")
        ttk.Button(top, text="Add portraits...", command=self.add).pack(side="right")
        self.b_use = ttk.Button(top, text="Use for the picked character", command=self.use)
        self.b_use.pack(side="right", padx=6)
        self.info = ttk.Label(self, foreground="#555", justify="left", wraplength=940, padding=(6, 0))
        self.info.pack(fill="x")
        box = ttk.Frame(self)
        box.pack(fill="both", expand=True, padx=6, pady=6)
        self.cv = tk.Canvas(box, highlightthickness=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", lambda x: self.cv.yview_scroll(
            int(-x.delta / 120), "units")))
        self.cv.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))
        # the grid follows the window's width: laid out again when it changes (the first show() ran
        # before the canvas had its width and put every portrait in one column - the user's report)
        self._cols = 0
        self.cv.bind("<Configure>", lambda e: self._cols != self._columns() and self.show(), add="+")
        self.sel = None
        self._imgs = {}
        self.load()

    def load(self):
        self.lib = self.PL.library(self.ed.mod, self.v_c.get()) if self.v_c.get() else {}
        groups = sorted(self.lib)
        self.cb_g["values"] = groups
        if self.v_g.get() not in groups:
            self.v_g.set("generals" if "generals" in groups else (groups[0] if groups else ""))
        self.show()

    def pending(self):
        return [a for a in self.ed.lib_adds if a["culture"] == self.v_c.get() and a["group"] == self.v_g.get()]

    def _columns(self):
        w = self.cv.winfo_width()
        if w <= 1:                                   # not laid out yet: the window's own width
            w = max(self.winfo_width(), 980) - 40
        return max(1, (w - 6) // 56)

    def show(self):
        cv = self.cv
        cv.delete("all")
        e = self.lib.get(self.v_g.get())
        age = self.v_age.get()
        if not e:
            self.info.configure(text="No portraits of %s in this mod or the game's data." % self.v_c.get())
            return
        pics = e.get(age) or {}
        (pw, ph), (cw, chh) = self.PL.sizes(self.ed.mod, self.v_c.get())
        new = self.pending()
        self.info.configure(text=(
            "%d portraits of %s / %s (%s shown). The game gives each character one of them at random when the campaign "
            "starts; the same number is the same man young, old and dead. New ones: any picture - made %d x %d%s, "
            "under the next free number in every folder of the group%s. %s") % (
            e["count"], self.v_c.get(), self.v_g.get(), age, pw, ph,
            (" with a %d x %d card" % (cw, chh)) if e.get("cards") else "",
            " (the dead one greyed unless you give one)" if e.get("dead") else "",
            ("%d new waiting for Apply (green)." % len(new)) if new else ""))
        W, H, cols = 50, 70, self._columns()
        self._cols = cols
        items = sorted(pics.items()) + [("new", a["pics"].get(age) or a["pics"].get("young")) for a in new]
        for i, (n, path) in enumerate(items):
            x, y = 6 + (i % cols) * 56, 6 + (i // cols) * 88
            img = self.ed.image(path, W, H)
            tag = "p%s" % i
            if img:
                cv.create_image(x, y, anchor="nw", image=img, tags=(tag,))
            fill = "#2a9d3a" if n == "new" else ("#1c5bd6" if self.sel == (n, path) else "#555")
            cv.create_rectangle(x - 1, y - 1, x + W + 1, y + H + 1, outline=fill, width=2 if fill != "#555" else 1,
                                tags=(tag,))
            cv.create_text(x + W / 2, y + H + 8, text="new" if n == "new" else "%03d" % n, font=("", 8), tags=(tag,))
            cv.tag_bind(tag, "<Button-1>", lambda ev, n=n, p=path: self.pick(n, p))
        cv.configure(scrollregion=cv.bbox("all") or (0, 0, 10, 10))
        m2 = getattr(self.ed, "m2", False)
        p = self.ed.person(self.ed.sel) if self.ed.sel else None
        self.b_use.configure(state="normal" if m2 and p and p["source"] == "map" else "disabled",
                             text="Use for %s" % p["name"] if p else "Use for the picked character")

    def pick(self, n, path):
        self.sel = (n, path)
        self.show()

    def add(self):
        from tkinter import filedialog
        files = filedialog.askopenfilenames(parent=self, title="New portraits for %s / %s" % (
            self.v_c.get(), self.v_g.get()), filetypes=[("Pictures", "*.png *.jpg *.jpeg *.tga *.bmp"),
                                                      ("All files", "*.*")])
        for f in files:
            self.ed.lib_adds.append({"culture": self.v_c.get(), "group": self.v_g.get(), "pics": {"young": f}})
        if files:
            self.ed.app.status.set("Portrait library: %d new portrait(s) - Preview, then Apply changes." % len(
                self.ed.lib_adds))
            self.ed.app._mark_work()
            self.show()

    def use(self):
        """Medieval II: the picked portrait (young, old and dead of its number) as the picked
        character's own (ui/custom_portraits + his portrait line, on Apply)."""
        p = self.ed.person(self.ed.sel) if self.ed.sel else None
        if not self.sel or not p:
            return
        n, path = self.sel
        e = self.lib.get(self.v_g.get()) or {}
        if n == "new":
            pics = {"young": path}
        else:
            pics = {a: (e.get(a) or {}).get(n) for a in ("young", "old", "dead") if (e.get(a) or {}).get(n)}
        self.ed.st.setdefault("portraits", {})[p["key"]] = pics
        self.ed.changed()
        self.show()
