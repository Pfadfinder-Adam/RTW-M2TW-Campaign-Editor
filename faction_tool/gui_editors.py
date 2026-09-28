"""The Unit editor and Building editor tabs: pick a unit (a building chain) on
the left, change any line of its block on the right, and import its pictures -
the tool puts them where the game reads them, in the mod's own format."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import editors as E
from .moddata import ModData
from .plan import Plan

CHANGED = "#fff2b3"          # a field changed and not written yet


class RecordEditor(ttk.Frame):
    """kind 'unit' (export_descr_unit.txt) or 'building' (export_descr_buildings.txt)."""

    def __init__(self, master, app, kind):
        super().__init__(master, padding=4)
        self.app, self.kind = app, kind
        self.mod = None
        self.blocks, self.changes, self.imports = [], {}, []    # changes {line: value}; imports [(src, targets, size)]
        self.current = None
        side = ttk.Frame(self)
        side.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(side, text="Units" if kind == "unit" else "Building chains", font=("", 10, "bold")).pack(anchor="w")
        self.v_find = tk.StringVar()
        e = ttk.Entry(side, textvariable=self.v_find, width=32)
        e.pack(fill="x", pady=(2, 4))
        e.bind("<KeyRelease>", lambda ev: self.fill_list())
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
        self.pics = ttk.LabelFrame(right, text="Pictures", padding=6)
        self.pics.pack(fill="x", pady=(6, 6))
        ttk.Label(right, text="Every line of the block: the key on the left, what follows it on the right. "
                              "Changed fields turn yellow; Preview, then Apply writes them (with a backup).",
                  foreground="#555").pack(anchor="w")
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
        self.changes, self.imports, self.current = {}, [], None
        p = self.path()
        if not p:
            self.blocks = []
        else:
            f = mod.load(p)
            self.blocks = E.unit_blocks(f) if self.kind == "unit" else E.building_blocks(f)
        self.fill_list()
        for w in self.form.winfo_children():
            w.destroy()
        for w in self.pics.winfo_children():
            w.destroy()
        self.title.configure(text="Pick one on the left" if self.blocks else "No %s in this mod" % (
            "export_descr_unit.txt" if self.kind == "unit" else "export_descr_buildings.txt"))

    def fill_list(self):
        q = self.v_find.get().strip().lower()
        self.shown = [b for b in self.blocks if not q or q in b[0].lower()]
        self.lb.delete(0, "end")
        for name, a, b in self.shown:
            mark = " *" if any(a <= ln < b for ln in self.changes) else ""
            self.lb.insert("end", name + mark)
        self.lbl_count.configure(text="%d of %d" % (len(self.shown), len(self.blocks)))

    def show(self):
        sel = self.lb.curselection()
        if not sel or sel[0] >= len(self.shown):
            return
        self.current = self.shown[sel[0]]
        name, a, b = self.current
        f = self.mod.load(self.path())
        self.fields = E.fields(f, a, b)
        self.title.configure(text=("unit " if self.kind == "unit" else "building ") + name)
        for w in self.form.winfo_children():
            w.destroy()
        for row, fd in enumerate(self.fields):
            ttk.Label(self.form, text="    " * fd.depth + fd.key, font=("", 9, "bold")).grid(
                row=row, column=0, sticky="w", padx=(0, 8))
            v = tk.StringVar(value=self.changes.get(fd.line, fd.value))
            e = tk.Entry(self.form, textvariable=v, width=90,
                         background=CHANGED if fd.line in self.changes else "white")
            e.grid(row=row, column=1, sticky="we", pady=1)
            v.trace_add("write", lambda *x, fd=fd, v=v, e=e: self.edited(fd, v.get(), e))
        self.show_pictures()

    def edited(self, fd, value, entry):
        if value.strip() == fd.value:
            self.changes.pop(fd.line, None)
            entry.configure(background="white")
        else:
            self.changes[fd.line] = value
            entry.configure(background=CHANGED)
        self.app.status.set("%d field(s) changed in %s - Preview, then Apply." % (
            len(self.changes), os.path.basename(self.path())))

    def value(self, key):
        fd = next((x for x in getattr(self, "fields", []) if x.key == key), None)
        return self.changes.get(fd.line, fd.value) if fd else ""

    def reset(self):
        self.changes, self.imports = {}, []
        self.fill_list()
        self.show()
        self.app.status.set("Nothing changed in the %s editor." % self.kind)

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
        cb.bind("<<ComboboxSelected>>", lambda ev: self.show_pictures())
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
        return bool(self.changes or self.imports)

    def make_plan(self):
        if not self.mod:
            raise ValueError("load a mod first")
        if not self.dirty():
            raise ValueError("nothing changed in the %s editor" % self.kind)
        mod = ModData(self.mod.data)
        plan = Plan(mod, self.kind + "s", self.kind + "s", {})
        path = mod.file("edu" if self.kind == "unit" else "edb")
        f = mod.load(path)
        by_line = {}
        for name, a, b in self.blocks:
            for ln in self.changes:
                if a <= ln < b:
                    by_line.setdefault(name, {})[ln] = self.changes[ln]
        for name, ch in by_line.items():
            E.apply_fields(plan, path, ch, "%s %s" % (self.kind, name))
        for src, targets, size in self.imports:
            E.import_picture(plan, src, targets, size)
        return plan
