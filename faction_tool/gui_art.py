"""The Art tab: every picture of the faction (for a new one: the template's, under
the names they get), each with what it needs and Replace...; and, as an optional part
that opens and closes (closed and off by default: the original stays), a new
campaign-select map drawn from the faction's towns in a colour you pick."""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import factionart as FA


class ArtEditor(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        self._photos = []
        from . import settings
        head = ttk.Frame(self)
        head.pack(fill="x")
        self.v_open = tk.BooleanVar(value=bool(settings.get("art_map_open")))
        self.b_open = ttk.Checkbutton(head, variable=self.v_open, command=self.toggle, style="Toolbutton")
        self.b_open.pack(side="left")
        self.lbl_state = ttk.Label(head, text="", foreground="#555")
        self.lbl_state.pack(side="left", padx=8)
        top = ttk.LabelFrame(self, text="Campaign-select map (the faction's land lit, as on the start screen)",
                             padding=6)
        self.top = top
        # the map as big as half the window allows (1x to 2x), its controls to the right
        self.map_pic = tk.Label(top, relief="sunken", width=48, height=15)
        self.map_pic.grid(row=0, column=0, rowspan=4, sticky="nw")
        self.v_draw = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Draw a new one from the faction's towns",
                        variable=self.v_draw, command=self.changed).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(top, foreground="#555", justify="left", wraplength=420, text=(
            "It replaces the faction's map_<faction>.tga, and the maps of the factions whose land changes "
            "follow. Off (the default): every map stays the original.")).grid(row=1, column=1, sticky="w", padx=10)
        self.b_colour = tk.Button(top, text="Colour of its land...", command=self.pick_colour, width=22)
        self.b_colour.grid(row=2, column=1, sticky="w", padx=10, pady=4)
        self.lbl_map = ttk.Label(top, text="", foreground="#555", justify="left", wraplength=420)
        self.lbl_map.grid(row=3, column=1, sticky="nw", padx=10)
        top.columnconfigure(1, weight=1)
        self._map_im, self._map_scale = None, 0
        top.bind("<Configure>", lambda e: self._fit_map(), add="+")
        self.bind("<Configure>", lambda e: self._fit_map(), add="+")        # the tab's height counts too
        self.pics_note = ttk.Label(self, text="Every picture of the faction. Replace... takes a PNG, JPG, TGA or DDS and makes it the "
                             "size and format the game's own has (a DDS stays a DDS); Preview, then Apply writes it (with a backup).",
                  foreground="#555")
        self.pics_note.pack(anchor="w", pady=(8, 2))
        box = ttk.Frame(self)
        box.pack(fill="both", expand=True)
        canvas = self.canvas = tk.Canvas(box, highlightthickness=0)
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
        # the picture cards flow into as many columns as the width takes
        self.cells, self._cols = [], 0
        canvas.bind("<Configure>", lambda e: self._reflow(), add="+")
        self.toggle(save=False)

    def toggle(self, save=True):
        """Open or close the campaign-select map part; closed, the pictures take the whole tab."""
        from . import settings
        on = self.v_open.get()
        self.b_open.configure(text=("\u25be" if on else "\u25b8") + "  Campaign-select map - optional: draw a new one")
        if on:
            self.top.pack(fill="x", before=self.pics_note)
            self.draw_map()
        else:
            self.top.pack_forget()
        self._state_text()
        if save:
            settings.put("art_map_open", on)

    def _state_text(self):
        on = bool(self.app.sel_map.get("on"))
        self.lbl_state.configure(text="a new one is drawn on Apply" if on else "off - the original map stays",
                                 foreground="#1c6b1c" if on else "#555")

    CELL = 400                  # a picture card's width in the grid

    def _reflow(self, force=False):
        cols = max(1, (self.canvas.winfo_width() - 8) // self.CELL)
        if cols == self._cols and not force:
            return
        self._cols = cols
        for c in range(8):
            self.inner.columnconfigure(c, weight=0, minsize=0)
        for c in range(cols):
            self.inner.columnconfigure(c, weight=1, minsize=self.CELL - 8)
        for i, w in enumerate(self.cells):
            w.grid(row=i // cols, column=i % cols, sticky="nwe", padx=3, pady=3)

    # ---- what the window keeps: app.art_replace {rel: src}, app.sel_map {colour, off} ----
    def _names(self):
        """(faction the pictures belong to now, the name they will have)."""
        a = self.app
        if a.editing():
            f = a.v["template"].get().strip()
            return f, f
        return a.v["template"].get().strip(), (a.v["name"].get().strip().lower() or None)

    def _thumb(self, parent, path, box=(72, 72), crop=None):
        from PIL import Image, ImageTk
        try:
            im = Image.open(path).convert("RGBA")
            if crop:                                     # a symbol on a shared sheet
                x, y, w, h = crop
                im = im.crop((x, y, x + w, y + h))
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
        self.cells = []
        for i, p in enumerate(pics):
            target = FA.picture_target(p, src_faction, new or src_faction)
            row = ttk.Frame(self.inner, padding=3, relief="groove")
            self.cells.append(row)
            pick = a.art_replace.get(target)
            pending = FA.art_source(pick) if pick else None
            self._thumb(row, pending or p["path"], crop=None if pending else p.get("crop")).grid(
                row=0, column=0, rowspan=4, sticky="n")
            ttk.Label(row, text=p["label"], font=("", 9, "bold"), wraplength=self.CELL - 110).grid(
                row=0, column=1, sticky="w", padx=6)
            if p.get("where"):
                ttk.Label(row, text="in the game: " + p["where"], wraplength=self.CELL - 110, justify="left").grid(
                    row=1, column=1, sticky="w", padx=6)
            note = p.get("note") or ""
            if p.get("symbol") and new and new != src_faction:
                note = note.split(" - ")[0]              # the template's sheet; the new faction's own is below
            text = "%s\n%s" % (note if p.get("symbol") else target, self._need(p["size"], target))
            if p.get("symbol") and new and new != src_faction:
                text += "\n%s gets a copy of its own (%s's until you replace it)" % (new, src_faction)
            if p.get("link"):
                text += "\nnamed in %s (%s)" % (os.path.basename(a.mod.file(p["link"][0]) or ""), p["link"][1])
                if target != p["rel"]:
                    text += "\n" + ("shared with %s - Replace gives %s a copy of its own under this name" % (
                        ", ".join(p["shared"]), new or src_faction) if p.get("shared") else
                        "%s's own copy, made from %s" % (new, p["rel"]))
            if pick:
                text += "\nnew: %s (not written yet)" % (
                    "the original, as it was" if isinstance(pick, dict) and pick.get("exact") else
                    os.path.basename(pending))
            ttk.Label(row, foreground="#555", justify="left", wraplength=self.CELL - 110, text=text).grid(
                row=2, column=1, sticky="w", padx=6)
            bar = ttk.Frame(row)
            bar.grid(row=3, column=1, sticky="w", padx=6)
            link = p.get("link") if target != p["rel"] else None
            if p.get("locked"):
                continue
            ttk.Button(bar, text="Replace...", command=lambda t=target, s=p["size"], l=p["label"], k=link:
                       self.replace(t, s, l, k)).pack(side="left")
            if pick:
                ttk.Button(bar, text="Keep the current one", command=lambda t=target: self.unreplace(t)).pack(
                    side="left", padx=4)
            else:
                orig = FA.original_picture(a.mod, target) if os.path.exists(os.path.join(a.mod.data, target)) \
                    else None
                if orig and not _same(orig, os.path.join(a.mod.data, target)):
                    ttk.Button(bar, text="Back to the original", command=lambda t=target, o=orig, k=link:
                               self.revert(t, o, k)).pack(side="left", padx=4)
        self._reflow(force=True)
        self.draw_map()

    @staticmethod
    def _need(size, target):
        if not size:
            return "as the file it replaces"
        if target.startswith("symbol:") and isinstance(size[2], str):
            return "needs %d x %d (kept in the sheet's DDS %s)" % size
        if target.lower().endswith(".dds"):
            return "needs %d x %d, DDS %s (with its mipmaps)" % size
        return "needs %d x %d, %d-bit TGA" % size

    def replace(self, target, size, label, link=None):
        src = filedialog.askopenfilename(title=label, filetypes=[
            ("Pictures", "*.tga *.png *.jpg *.jpeg *.bmp *.dds"), ("All files", "*.*")])
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
        self.app.art_replace[target] = {"src": src, "link": link} if link else src
        self.app.status.set("%s: %s - Preview, then Apply." % (label, os.path.basename(src)))
        self.load()

    def revert(self, target, orig, link=None):
        """The picture as it was before the tool first changed it (a pending change, written on Apply)."""
        self.app.remember()
        pick = {"src": orig, "exact": True}
        if link:
            pick["link"] = link
        self.app.art_replace[target] = pick
        self.app.status.set("%s goes back to the original on Apply." % target)
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
        if not a.colours.get("primary"):             # as its (template's) own map has it
            t = a.v["template"].get().strip()
            fb = a.strat.faction(t) if a.strat and t else None
            got = FA.colour_on_map(a.mod, a.v_campaign.get(), t, [st.region for st in fb.settlements]) if fb else None
            if got:
                return got
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
            self.draw_map()

    def changed(self):
        a = self.app
        a.remember()
        if self.v_draw.get():
            a.sel_map["on"] = True
        else:
            a.sel_map.pop("on", None)
        self._state_text()
        self.draw_map()

    def draw_map(self):
        a = self.app
        self.v_draw.set(bool(a.sel_map.get("on")))
        self._state_text()
        if not self.v_open.get():
            return                                  # closed: nothing drawn (on Medieval II the first draw takes a while)
        col = self.colour()
        self.b_colour.configure(bg="#%02x%02x%02x" % col, fg="white" if sum(col) < 380 else "black")
        if not a.mod:
            return
        finding = ("select_frame", a.v_campaign.get()) not in a.mod._cache
        if finding:
            # the first time for a mod (Medieval II): learning where the map lies takes a few seconds
            a.status.set("Finding where the map lies in the campaign-select pictures (once per mod)...")
            self.update_idletasks()
        try:
            im = FA.draw_select_map(a.mod, a.v_campaign.get(), list(a.chosen), col)
        except Exception as e:
            im = None
            self.lbl_map.configure(text="cannot draw it: %s" % e)
        if finding and a.status.get().startswith("Finding where the map lies"):
            a.status.set("")
        if im is None:
            self._map_im = None
            self.map_pic.configure(image="", text="(this campaign has fewer than three\ncampaign-select maps "
                                                   "to learn from)", width=48, height=15)
            return
        self._map_im, self._map_scale = im, 0
        self._fit_map()
        self.lbl_map.configure(text="%d town(s) lit - the towns chosen on the Faction tab (written with the "
                                    "borders as painted on the Map tab).\n%s" % (
            len(a.chosen), "Written on Apply / Create." if self.v_draw.get() else
            "Only a preview: the file stays the original (for a new faction: the template's copy)."))

    def _fit_map(self):
        """The select map shown as big as the tab allows: half its width, 40 % of its height (0.5x to 2x)."""
        im = self._map_im
        if im is None:
            return
        room = max(1, self.top.winfo_width() - 460)
        # and no taller than about 40 % of the tab: the picture list below keeps its room (the map
        # blown up to 2x once squeezed the list to a strip)
        tall = self.winfo_height()
        high = (tall * 0.40 / float(im.height)) if tall > 50 else 1.0
        scale = max(0.5, min(2.0, room / float(im.width), high))
        scale = round(scale * 4) / 4.0                 # steps of a quarter: no redraw per pixel of resize
        if scale == self._map_scale:
            return
        self._map_scale = scale
        from PIL import Image, ImageTk
        big = im if scale == 1 else im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))),
                                              Image.LANCZOS)
        self._map_photo = ImageTk.PhotoImage(big)
        self.map_pic.configure(image=self._map_photo, text="", width=big.width, height=big.height)


def _same(a, b):
    """Whether two files hold the same bytes."""
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, "rb") as x, open(b, "rb") as y:
            return x.read() == y.read()
    except OSError:
        return False
