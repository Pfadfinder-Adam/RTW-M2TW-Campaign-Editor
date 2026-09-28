"""The Art tab: every picture of the faction (for a new one: the template's, under
the names they get), each with what it needs and Replace...; and the
campaign-select map, drawn from the faction's towns in a colour you pick."""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import factionart as FA


class ArtEditor(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        self._photos = []
        top = ttk.LabelFrame(self, text="Campaign-select map (the faction's land lit, as on the start screen)",
                             padding=6)
        top.pack(fill="x")
        self.map_pic = tk.Label(top, relief="sunken", width=48, height=15)
        self.map_pic.grid(row=0, column=0, rowspan=4, sticky="nw")
        self.v_draw = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Draw it from the faction's towns (else the file stays as it is)",
                        variable=self.v_draw, command=self.changed).grid(row=0, column=1, sticky="w", padx=10)
        self.b_colour = tk.Button(top, text="Colour of its land...", command=self.pick_colour, width=22)
        self.b_colour.grid(row=1, column=1, sticky="w", padx=10, pady=4)
        self.lbl_map = ttk.Label(top, text="", foreground="#555", justify="left", wraplength=420)
        self.lbl_map.grid(row=2, column=1, sticky="nw", padx=10)
        ttk.Label(self, text="Every picture of the faction. Replace... takes a PNG, JPG or TGA and makes it the "
                             "size and depth the game's own has; Preview, then Apply writes it (with a backup).",
                  foreground="#555").pack(anchor="w", pady=(8, 2))
        box = ttk.Frame(self)
        box.pack(fill="both", expand=True)
        canvas = tk.Canvas(box, highlightthickness=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",
                    lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    # ---- what the window keeps: app.art_replace {rel: src}, app.sel_map {colour, off} ----
    def _names(self):
        """(faction the pictures belong to now, the name they will have)."""
        a = self.app
        if a.editing():
            f = a.v["template"].get().strip()
            return f, f
        return a.v["template"].get().strip(), (a.v["name"].get().strip().lower() or None)

    def _target(self, rel, src_faction, new):
        """The path a template's picture gets for the new faction: its name swapped where it
        stands as a whole (symbol24_romans_julii_roll -> symbol24_saba_roll), as the clone does."""
        import re
        if not new or new == src_faction:
            return rel
        return re.sub(r"(?i)(^|[^a-z0-9])%s(?=$|[^a-z0-9])" % re.escape(src_faction),
                      lambda m: m.group(1) + new, rel)

    def _thumb(self, parent, path, box=(72, 72)):
        from PIL import Image, ImageTk
        try:
            im = Image.open(path).convert("RGBA")
            im.thumbnail(box)
            ph = ImageTk.PhotoImage(im)
        except Exception:
            return ttk.Label(parent, text="(none)", width=10, relief="sunken")
        self._photos.append(ph)
        return tk.Label(parent, image=ph, relief="sunken")

    def load(self):
        a = self.app
        for w in self.inner.winfo_children():
            w.destroy()
        self._photos = []
        if not a.mod:
            return
        src_faction, new = self._names()
        if not src_faction:
            ttk.Label(self.inner, text="Pick the %s on the Faction tab first." % (
                "faction" if a.editing() else "template")).grid(row=0, column=0, sticky="w")
            self.draw_map()
            return
        pics = FA.faction_pictures(a.mod, a.v_campaign.get(), src_faction)
        if not pics:
            ttk.Label(self.inner, text="No pictures named after %s were found." % src_faction).grid(row=0, column=0)
        for i, p in enumerate(pics):
            target = self._target(p["rel"], src_faction, new)
            row = ttk.Frame(self.inner, padding=3, relief="groove")
            row.grid(row=i // 2, column=i % 2, sticky="nwe", padx=3, pady=3)
            pending = a.art_replace.get(target)
            self._thumb(row, pending or p["path"]).grid(row=0, column=0, rowspan=3)
            ttk.Label(row, text=p["label"], font=("", 9, "bold")).grid(row=0, column=1, sticky="w", padx=6)
            size = p["size"]
            need = ("needs %d x %d, %d-bit TGA" % size) if size else "as the file it replaces"
            ttk.Label(row, foreground="#555", justify="left", text="%s\n%s%s" % (
                target, need, "\nnew: %s (not written yet)" % os.path.basename(pending) if pending else "")).grid(
                row=1, column=1, sticky="w", padx=6)
            bar = ttk.Frame(row)
            bar.grid(row=2, column=1, sticky="w", padx=6)
            ttk.Button(bar, text="Replace...", command=lambda t=target, s=size, l=p["label"]: self.replace(t, s, l)).pack(
                side="left")
            if pending:
                ttk.Button(bar, text="Keep the old one", command=lambda t=target: self.unreplace(t)).pack(
                    side="left", padx=4)
        self.draw_map()

    def replace(self, target, size, label):
        src = filedialog.askopenfilename(title=label, filetypes=[
            ("Pictures", "*.tga *.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        if not src:
            return
        try:
            from PIL import Image
            with Image.open(src) as im:
                got = im.size
        except Exception as e:
            messagebox.showerror("Replace", "Cannot read %s: %s" % (src, e))
            return
        if size and tuple(got) != tuple(size[:2]):
            if not messagebox.askyesno("Replace", "%s is %d x %d; the game's picture is %d x %d.\n\n"
                                                  "Resize it to %d x %d?" % ((os.path.basename(src),) + tuple(got) +
                                                                             tuple(size[:2]) + tuple(size[:2]))):
                return
        self.app.remember()
        self.app.art_replace[target] = src
        self.app.status.set("%s: %s - Preview, then Apply." % (label, os.path.basename(src)))
        self.load()

    def unreplace(self, target):
        self.app.remember()
        self.app.art_replace.pop(target, None)
        self.load()

    # ---- the campaign-select map ----
    def colour(self):
        a = self.app
        c = a.sel_map.get("colour")
        if c:
            return tuple(c)
        return FA.default_map_colour(a.colours.get("primary") or self._template_primary())

    def _template_primary(self):
        a = self.app
        t = a.v["template"].get().strip()
        try:
            from .edit import read_faction
            return read_faction(a.mod, a.v_campaign.get(), t).get("primary_colour") if t else None
        except Exception:
            return None

    def pick_colour(self):
        c = colorchooser.askcolor(color="#%02x%02x%02x" % self.colour(), title="Colour of the faction's land")
        if c and c[0]:
            self.app.remember()
            self.app.sel_map["colour"] = [int(v) for v in c[0]]
            self.changed()

    def changed(self):
        a = self.app
        if self.v_draw.get():
            a.sel_map.pop("off", None)
        else:
            a.sel_map["off"] = True
        self.draw_map()

    def draw_map(self):
        a = self.app
        self.v_draw.set(not a.sel_map.get("off"))
        col = self.colour()
        self.b_colour.configure(bg="#%02x%02x%02x" % col, fg="white" if sum(col) < 380 else "black")
        if not a.mod:
            return
        try:
            im = FA.draw_select_map(a.mod, a.v_campaign.get(), list(a.chosen), col)
        except Exception as e:
            im = None
            self.lbl_map.configure(text="cannot draw it: %s" % e)
        if im is None:
            self.map_pic.configure(image="", text="(this campaign has fewer than three\ncampaign-select maps "
                                                   "to learn from)", width=48, height=15)
            return
        from PIL import ImageTk
        self._map_photo = ImageTk.PhotoImage(im)
        self.map_pic.configure(image=self._map_photo, text="", width=im.width, height=im.height)
        self.lbl_map.configure(text="%d town(s) lit - the towns chosen on the Faction tab.\n%s" % (
            len(a.chosen), "Written on Apply / Create." if self.v_draw.get() else
            "Not drawn: the file stays as it is (for a new faction: the template's copy)."))
