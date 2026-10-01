"""Traits and retinue: the traits and ancillaries themselves (traitsedit), both games - a list to pick from, each
level's name and description as players see them, its threshold and effects; an ancillary's name, text,
picture, the cultures it is barred from and its effects. A new one is made as a copy of the picked one (written
at once, then edited like the others). Changes wait for Preview / Write it in, with a backup like every write."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .gui_util import ShortHint
from . import traitsedit as TE
from .plan import Plan

TITLE = "Traits and retinue"


class TraitsWindow(tk.Toplevel):
    def __init__(self, app, pick=None):
        super().__init__(app)
        self.app, self.mod = app, app.mod
        self.title(TITLE)
        self.geometry("1100x720")
        self.transient(app)
        self.pending = {"trait": {}, "ancillary": {}}          # name: {'characters', 'levels': {...}, ...}
        self.texts = {"trait": {}, "ancillary": {}}            # KEY: text players see
        self.pictures = {}                                     # image name: picture file
        self._photos = []
        top = ttk.Frame(self, padding=8)
        top.pack(fill="both", expand=True)
        ShortHint(top, foreground="#555", justify="left", wraplength=1060, text=(
            "The traits and the retinue themselves (export_descr_character_traits.txt, export_descr_ancillaries.txt). "
            "Pick one on the left: each level's name and description as players see them, the points it needs "
            "(Threshold) and what it gives (Effects, like 'Command 1, Loyalty -2'). New... makes a copy of the "
            "picked one under a new name - then give it to characters in the Character editor. Preview, then "
            "Write it in (a backup first, Tools > Restore undoes it).")).pack(fill="x")
        self.nb = ttk.Notebook(top)
        self.nb.pack(fill="both", expand=True, pady=6)
        self.tabs = {}
        for kind, text in (("trait", "  Traits  "), ("ancillary", "  Retinue (ancillaries)  ")):
            self.tabs[kind] = self._tab(kind, text)
        bar = ttk.Frame(top)
        bar.pack(fill="x")
        self.lbl = ttk.Label(bar, text="", foreground="#555")
        self.lbl.pack(side="left")
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Write it in", command=self.write).pack(side="right", padx=4)
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right")
        self.reload(pick)

    # ---- reading ----
    def reload(self, pick=None):
        from .charpanel import strings
        self.blocks, self.shown = {}, {}
        for kind in ("trait", "ancillary"):
            path = TE.file_of(self.mod, kind)
            self.blocks[kind] = TE.blocks(self.mod.load(path), kind) if path else {}
            self.shown[kind] = strings(self.mod, TE.TEXTS[kind])
        self.known = TE.effect_names(self.mod)
        for kind in self.tabs:
            self.fill_list(kind, pick if pick and pick in self.blocks[kind] else None)
        self._status()

    def text_of(self, kind, key):
        got = self.texts[kind].get(key)
        return got if got is not None else self.shown[kind].get((key or "").upper(), "")

    # ---- a tab ----
    def _tab(self, kind, text):
        tab = ttk.Frame(self.nb, padding=6)
        self.nb.add(tab, text=text)
        left = ttk.Frame(tab)
        left.pack(side="left", fill="y")
        v_find = tk.StringVar()
        e = ttk.Entry(left, textvariable=v_find, width=34)
        e.pack(fill="x")
        lb = tk.Listbox(left, width=40, exportselection=False)
        sb = ttk.Scrollbar(left, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        ttk.Button(left, text="New %s (a copy of the picked one)..." % ("trait" if kind == "trait" else "ancillary"),
                   command=lambda: self.new(kind)).pack(side="bottom", fill="x", pady=(4, 0))
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True, pady=(4, 0))
        from .gui_util import ScrollFrame
        right = ScrollFrame(tab)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        t = {"find": v_find, "list": lb, "form": right.inner, "names": []}
        e.bind("<KeyRelease>", lambda ev: self.fill_list(kind))
        lb.bind("<<ListboxSelect>>", lambda ev: self.show(kind))
        return t

    def fill_list(self, kind, pick=None):
        t = self.tabs[kind]
        cur = pick or self.picked(kind)
        q = t["find"].get().strip().lower()
        names = []
        for name, b in sorted(self.blocks[kind].items(), key=lambda kv: kv[0].lower()):
            first = b["levels"][0]["name"] if kind == "trait" and b["levels"] else name
            label = self.text_of(kind, first)
            if q and q not in name.lower() and q not in label.lower():
                continue
            names.append(name)
        t["names"] = names
        lb = t["list"]
        lb.delete(0, "end")
        for n in names:
            b = self.blocks[kind][n]
            first = b["levels"][0]["name"] if kind == "trait" and b["levels"] else n
            mark = "  *" if n in self.pending[kind] else ""
            lb.insert("end", "%s  -  %s%s" % (n, self.text_of(kind, first), mark))
        if cur in names:
            i = names.index(cur)
            lb.selection_set(i)
            lb.see(i)
        self.show(kind)

    def picked(self, kind):
        t = self.tabs[kind]
        sel = t["list"].curselection()
        return t["names"][sel[0]] if sel and sel[0] < len(t["names"]) else None

    # ---- the form ----
    def _entry(self, parent, value, width=40):
        v = tk.StringVar(value=value)
        ttk.Entry(parent, textvariable=v, width=width).pack(side="left", fill="x", expand=True)
        return v

    def _text(self, parent, value, height=2):
        w = tk.Text(parent, height=height, width=60, wrap="word")
        w.insert("1.0", value)
        w.pack(fill="x")
        return w

    def show(self, kind):
        form = self.tabs[kind]["form"]
        for w in form.winfo_children():
            w.destroy()
        self._photos = [p for p in self._photos if p is not None][-20:]
        name = self.picked(kind)
        if not name:
            ttk.Label(form, text="Pick one on the left.", foreground="#555").pack(anchor="w")
            return
        b = self.blocks[kind][name]
        pend = self.pending[kind].get(name, {})
        ttk.Label(form, text=name, font=("", 12, "bold")).pack(anchor="w")
        if kind == "trait":
            self._trait_form(form, name, b, pend)
        else:
            self._anc_form(form, name, b, pend)

    def _row(self, parent, label):
        r = ttk.Frame(parent)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text=label, width=22).pack(side="left")
        return r

    def _trait_form(self, form, name, b, pend):
        r = self._row(form, "Characters (who can have it)")
        now = (b["lines"].get("Characters") or (None, ""))[1]
        v_ch = self._entry(r, pend.get("characters", now))
        v_ch.trace_add("write", lambda *a: self._set("trait", name, "characters", v_ch.get(), now))
        anti = (b["lines"].get("AntiTraits") or (None, ""))[1]
        if anti:
            ttk.Label(form, text="Opposite traits (AntiTraits): %s" % anti, foreground="#555").pack(anchor="w")
        for k, lv in enumerate(b["levels"], 1):
            box = ttk.LabelFrame(form, text="Level %d: %s" % (k, lv["name"]), padding=6)
            box.pack(fill="x", pady=4)
            r = self._row(box, "Name players see")
            v_name = self._entry(r, self.text_of("trait", lv["name"]))
            v_name.trace_add("write", lambda *a, key=lv["name"], v=v_name: self._text_set("trait", key, v.get(), name))
            desc_key = (lv["keys"].get("Description") or (None, None))[1]
            if desc_key:
                ttk.Label(box, text="Description").pack(anchor="w")
                t = self._text(box, self.text_of("trait", desc_key))
                t.bind("<KeyRelease>", lambda e, key=desc_key, w=t: self._text_set(
                    "trait", key, w.get("1.0", "end").rstrip("\n"), name))
            r = self._row(box, "Points it needs (Threshold)")
            lp = pend.get("levels", {}).get(lv["name"], {})
            th_now = lv["threshold"][1] if lv["threshold"] else None
            v_th = tk.StringVar(value=str(lp.get("threshold", th_now if th_now is not None else "")))
            ttk.Spinbox(r, from_=0, to=100, textvariable=v_th, width=6).pack(side="left")
            v_th.trace_add("write", lambda *a, ln=lv["name"], v=v_th, now=th_now: self._level_set(
                name, ln, "threshold", v.get(), now))
            r = self._row(box, "Effects")
            eff_now = TE.effects_words([(a, v) for _, a, v in lv["effects"]])
            v_eff = self._entry(r, lp.get("effects_text", eff_now), 50)
            v_eff.trace_add("write", lambda *a, ln=lv["name"], v=v_eff, now=eff_now: self._level_set(
                name, ln, "effects", v.get(), now))

    def _anc_form(self, form, name, b, pend):
        r = self._row(form, "Name players see")
        v_name = self._entry(r, self.text_of("ancillary", name))
        v_name.trace_add("write", lambda *a: self._text_set("ancillary", name, v_name.get(), name))
        desc_key = ((b["lines"].get("Description") or (None, ""))[1].split() or [None])[0]
        if desc_key:
            ttk.Label(form, text="Description").pack(anchor="w")
            t = self._text(form, self.text_of("ancillary", desc_key), 3)
            t.bind("<KeyRelease>", lambda e: self._text_set("ancillary", desc_key, t.get("1.0", "end").rstrip("\n"),
                                                           name))
        # the picture
        from .charpanel import ancillary_picture
        img_now = (b["lines"].get("Image") or (None, ""))[1]
        img = pend.get("image", img_now)
        r = self._row(form, "Picture")
        pic = self.pictures.get(img) or ancillary_picture(self.mod, img)
        self._thumb(r, pic)
        side = ttk.Frame(r)
        side.pack(side="left", padx=8)
        ttk.Label(side, text=img or "(none)", foreground="#555").pack(anchor="w")
        ttk.Button(side, text="Replace picture...", command=lambda: self.replace_picture(name, img_now)).pack(
            anchor="w", pady=2)
        r = self._row(form, "Barred to cultures")
        ex_now = (b["lines"].get("ExcludeCultures") or (None, ""))[1]
        v_ex = self._entry(r, pend.get("exclude", ex_now))
        v_ex.trace_add("write", lambda *a: self._set("ancillary", name, "exclude", v_ex.get(), ex_now))
        r = self._row(form, "Effects")
        eff_now = TE.effects_words([(a, v) for _, a, v in b["effects"]])
        v_eff = self._entry(r, pend.get("effects_text", eff_now), 50)
        v_eff.trace_add("write", lambda *a: self._set("ancillary", name, "effects_text", v_eff.get(), eff_now))

    def _thumb(self, parent, path):
        from PIL import Image, ImageTk
        try:
            with Image.open(path) as im:
                im = im.convert("RGBA")
                k = min(96 / im.width, 128 / im.height)
                ph = ImageTk.PhotoImage(im.resize((max(1, int(im.width * k)), max(1, int(im.height * k)))))
        except Exception:
            ttk.Label(parent, text="(no picture)", width=14, relief="sunken").pack(side="left")
            return
        self._photos.append(ph)
        tk.Label(parent, image=ph, relief="sunken").pack(side="left")

    # ---- keeping the changes ----
    def _set(self, kind, name, key, value, now):
        p = self.pending[kind].setdefault(name, {})
        if value.strip() == (now or "").strip():
            p.pop(key, None)
        else:
            p[key] = value
        self._tidy(kind, name)

    def _level_set(self, name, level, key, value, now):
        p = self.pending["trait"].setdefault(name, {}).setdefault("levels", {}).setdefault(level, {})
        if key == "threshold":
            same = str(value).strip() == str(now if now is not None else "")
            if same:
                p.pop("threshold", None)
            else:
                p["threshold"] = value
        else:
            if value.strip() == now.strip():
                p.pop("effects_text", None)
            else:
                p["effects_text"] = value
        if not p:
            self.pending["trait"][name]["levels"].pop(level, None)
        if not self.pending["trait"][name].get("levels"):
            self.pending["trait"][name].pop("levels", None)
        self._tidy("trait", name)

    def _text_set(self, kind, key, value, name):
        if value == self.shown[kind].get(key.upper(), ""):
            self.texts[kind].pop(key, None)
        else:
            self.texts[kind][key] = value
        self._status()

    def _tidy(self, kind, name):
        if not self.pending[kind].get(name):
            self.pending[kind].pop(name, None)
        self._status()

    def _count(self):
        return sum(len(v) for v in self.pending.values()) + sum(len(v) for v in self.texts.values()) + \
            len(self.pictures)

    def _status(self):
        n = self._count()
        self.lbl.configure(text="%d change(s) - Preview, then Write it in." % n if n else
                           "Nothing changed yet.")

    def replace_picture(self, name, image):
        src = filedialog.askopenfilename(parent=self, title="Picture for %s" % name, filetypes=[
            ("Pictures", "*.tga *.png *.jpg *.jpeg *.bmp *.dds"), ("All files", "*.*")])
        if not src:
            return
        shared = [n for n, b in self.blocks["ancillary"].items()
                  if n != name and (b["lines"].get("Image") or (None, ""))[1].lower() == (image or "").lower()]
        if not image or shared:
            # a picture of its own (the one it had is shared with others, or it had none)
            new = "%s.tga" % name
            self._set("ancillary", name, "image", new, image)
            image = new
        self.pictures[image] = src
        self._status()
        self.show("ancillary")

    # ---- writing ----
    def _plan(self):
        plan = Plan(self.mod, "traits", "traits_and_retinue", {})
        for kind in ("trait", "ancillary"):
            edit = {}
            for name, p in self.pending[kind].items():
                ch = {}
                for key in ("characters", "exclude", "image"):
                    if key in p:
                        ch[key] = p[key]
                if "effects_text" in p:
                    ch["effects"] = [list(x) for x in TE.parse_effects(p["effects_text"])]
                for lv, lp in (p.get("levels") or {}).items():
                    out = {}
                    if "threshold" in lp:
                        try:
                            out["threshold"] = int(str(lp["threshold"]).strip())
                        except ValueError:
                            raise ValueError("%s / %s: the points it needs are a whole number" % (name, lv))
                    if "effects_text" in lp:
                        out["effects"] = [list(x) for x in TE.parse_effects(lp["effects_text"])]
                    ch.setdefault("levels", {})[lv] = out
                edit[name] = ch
            pics = {k: v for k, v in self.pictures.items()} if kind == "ancillary" else {}
            if edit or self.texts[kind] or pics:
                TE.apply(plan, kind, {"edit": edit, "texts": dict(self.texts[kind]), "pictures": pics})
        unknown = sorted({a for kind in self.pending for p in self.pending[kind].values()
                          for txt in [p.get("effects_text", "")] + [lp.get("effects_text", "")
                                                                     for lp in (p.get("levels") or {}).values()]
                          for a, _ in TE.parse_effects(txt)} - self.known)
        if unknown:
            plan.warn(None, "effects no trait or ancillary of this mod uses yet: %s - check the spelling (the game "
                            "may refuse a name it does not know)" % ", ".join(unknown))
        return plan

    def preview(self):
        if not self._count():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        self.app.show_text("Traits and retinue - preview (nothing written)", plan.report())

    def write(self):
        if not self._count():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        if not self._apply(plan, "Write %d change(s) into %d file(s)?" % (self._count(), len(plan.changed_files()))):
            return
        self.pending = {"trait": {}, "ancillary": {}}
        self.texts = {"trait": {}, "ancillary": {}}
        self.pictures = {}
        self.reload()

    def _apply(self, plan, question):
        if self.app.pending_parts():
            messagebox.showerror(TITLE, "Other changes of the window wait for Apply - Apply (or undo) them first: "
                                        "the mod is read again after this write.", parent=self)
            return None
        if not messagebox.askyesno(TITLE, "%s\n\n%s\n\nA backup is made first (Tools > Restore undoes it)." % (
                question, plan.report()[:1500]), parent=self):
            return None
        bdir = plan.apply()
        from . import log
        log.write("Traits and retinue changed (backup %s)\n%s" % (bdir, plan.report()))
        self.app.load()                                     # everything reads the new files (Character editor too)
        self.mod = self.app.mod
        self.app.status.set("Traits and retinue written (backup %s) - start the game to see them." % bdir)
        return bdir

    def new(self, kind):
        src = self.picked(kind)
        if not src:
            messagebox.showinfo(TITLE, "Pick the %s to copy first (on the left)." % kind, parent=self)
            return
        if self._count():
            messagebox.showinfo(TITLE, "Write in (or close without) the changes waiting first - a new one is "
                                       "written at once.", parent=self)
            return
        new = simpledialog.askstring(TITLE, "Name of the new %s (letters, digits and _), a copy of %s:" % (kind, src),
                                     parent=self)
        if not new:
            return
        plan = Plan(self.mod, "traits", "traits_and_retinue", {})
        try:
            TE.apply(plan, kind, {"new": [[src, new.strip()]]})
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        if self._apply(plan, "Make %s, a copy of %s?" % (new.strip(), src)):
            self.reload(new.strip())


def open_traits(app, pick=None):
    if not app.mod:
        messagebox.showinfo(TITLE, "Load a mod first (Mod or Browse..., then Load).", parent=app)
        return
    if not (TE.file_of(app.mod, "trait") or TE.file_of(app.mod, "ancillary")):
        messagebox.showinfo(TITLE, "This mod has neither export_descr_character_traits.txt nor "
                                   "export_descr_ancillaries.txt.", parent=app)
        return
    TraitsWindow(app, pick)
