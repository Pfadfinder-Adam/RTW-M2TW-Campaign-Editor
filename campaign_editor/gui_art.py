"""The Art tab: every picture of the faction (for a new one: the template's, under
the names they get), each with what it needs and Replace...; and, as an optional part
that opens and closes (closed and off by default: the original stays), a new
campaign-select map drawn from the faction's towns in a colour you pick."""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from .gui_util import ShortHint
from . import factionart as FA

# The campaign-select map part is put away for now (the user, 2026-10-01): the code stays for a later release;
# True shows it again. While False the originals stay and nothing is drawn (gui.App.select_map_opts).
MAP_PART = False


class ArtEditor(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        self._photos = []
        from . import settings
        head = ttk.Frame(self)
        if MAP_PART:
            head.pack(fill="x")
        self.v_open = tk.BooleanVar(value=MAP_PART and bool(settings.get("art_map_open")))
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
        # the faction's figures on the campaign map: a strat model per character type, changed here, seen in 3D
        self.fig_box = ttk.LabelFrame(self, text="Figures on the campaign map - who is shown by which model",
                                      padding=6)
        self.fig_box.pack(fill="x", pady=(6, 0))
        self.pics_note = ttk.Label(self, text="Every picture of the faction. Replace... takes a PNG, JPG, TGA or DDS and makes it the "
                             "size and format the game's own has (a DDS stays a DDS); Preview, then Apply writes it (with a backup).",
                  foreground="#555")
        self.pics_note.pack(anchor="w", pady=(8, 2))
        from .gui_util import tip
        btns = ttk.Frame(self)
        btns.pack(anchor="w", pady=(0, 4))
        tip(ttk.Button(btns, text="Faction emblem - one picture everywhere...", command=self.emblem_window),
            "The faction's emblem is shown in many places and sizes: the campaign-menu buttons (normal, mouse over, "
            "selected, greyed out), the loading screen, the faction screen, the faction logo and small logo in the "
            "game's panels. Pick one picture: every one of them is made from it in its own size; the button states "
            "the way the mod's own are made (brighter, the glow, grey).").pack(side="left", padx=(0, 6))
        tip(ttk.Button(btns, text="Recolour all its pictures...", command=lambda: self.app.recolour_window()),
            "Unit cards, battle textures, symbols, banners, captain cards: moved from the colours they carry now "
            "(a template's, for a cloned faction) to the faction's own - light and shade kept, faces and metal "
            "untouched. Before / after shown; written with a backup.").pack(side="left")
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
        if save and MAP_PART:
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
            from .recolour import read_picture       # .tga, .dds, Medieval II's .texture
            im = read_picture(path).convert("RGBA")
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
        self.fill_figures(src_faction, new)
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
            if note and not p.get("symbol"):
                text += "\n" + note
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
                # shared with other factions: Replace gives this faction a copy of its own (Edit faction - a new
                # faction's lines are not written yet); Save a copy always (a tester: no buttons on some)
                if p.get("extra") and (not new or new == src_faction):
                    ttk.Button(bar, text="Replace (its own copy)...", command=lambda t=target, s=p["size"],
                               l=p["label"], x=p["extra"]: self.replace(t, s, l, extra=[x["kind"], x["ref"]])).pack(
                        side="left")
                if os.path.isfile(p["path"]):
                    from .gui_util import save_copy
                    ttk.Button(bar, text="Save a copy...", command=lambda n=p["path"], l=p["label"]:
                               save_copy(self, n, l)).pack(side="left", padx=4)
                if pick:
                    ttk.Button(bar, text="Keep the current one", command=lambda t=target: self.unreplace(t)).pack(
                        side="left", padx=4)
                continue
            ttk.Button(bar, text="Replace...", command=lambda t=target, s=p["size"], l=p["label"], k=link:
                       self.replace(t, s, l, k)).pack(side="left")
            now = os.path.join(a.mod.data, target) if not target.startswith("symbol:") else None
            if not pick and now and os.path.isfile(now):
                from .gui_util import save_copy
                ttk.Button(bar, text="Save a copy...", command=lambda n=now, l=p["label"]: save_copy(self, n, l)).pack(
                    side="left", padx=4)
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

    def fill_figures(self, faction, new):
        """A row per character type of the faction: its figure (a strat model of descr_model_strat.txt, one per
        level) to pick, and View in 3D. The pick waits for Apply like every change (app.figures)."""
        from . import stratmodels as SM
        a = self.app
        box = self.fig_box
        for w in box.winfo_children():
            w.destroy()
        figs = SM.figures(a.mod, faction) if faction else []
        if not figs:
            ttk.Label(box, text="%s has no character types in descr_character.txt." % faction if faction else
                      "Pick the faction first.", foreground="#555").grid(row=0, column=0, sticky="w")
            return
        names = sorted(SM.model_types(a.mod), key=str.lower)
        cols = 3
        r = c = 0
        for fg in figs:
            wide = len(fg["models"]) > 1                # levels (a priest, bishop, cardinal): a row of its own
            if wide and c:
                r, c = r + 1, 0
            cell = ttk.Frame(box, padding=(0, 2, 12, 2))
            cell.grid(row=r, column=c, columnspan=cols if wide else 1, sticky="w")
            want = a.figures.get(fg["type"]) or fg["models"]
            ttk.Label(cell, text=fg["type"], width=16, font=("", 9, "bold")).grid(row=0, column=0, sticky="w")
            for lv, now in enumerate(fg["models"]):
                v = tk.StringVar(value=want[lv] if lv < len(want) else now)
                cb = ttk.Combobox(cell, textvariable=v, values=names, width=20, state="readonly")
                cb.grid(row=0, column=1 + 2 * lv, padx=(0, 2))
                cb.bind("<<ComboboxSelected>>", lambda e, t=fg["type"], lv=lv, v=v, fg=fg: self.pick_figure(
                    t, lv, v.get(), fg["models"]))
                ttk.Button(cell, text="3D", width=3, command=lambda v=v: self.view_figure(v.get(), faction)).grid(
                    row=0, column=2 + 2 * lv, padx=(0, 6))
            if fg["type"] in a.figures:
                ttk.Label(cell, text="was %s (not written yet)" % ", ".join(fg["models"]),
                          foreground="#b05a00").grid(row=1, column=1, columnspan=2 * len(fg["models"]), sticky="w")
            if wide:
                r, c = r + 1, 0
            else:
                r, c = (r + 1, 0) if c + 1 >= cols else (r, c + 1)
        r += 1 if c else 0
        ShortHint(box, foreground="#555", justify="left", wraplength=900, text=(
            "Pick another model for a character type (the list holds every figure of descr_model_strat.txt); "
            "Preview, then Apply writes descr_character.txt (a faction sharing its line with others gets a line "
            "of its own). A model the faction has no texture in gets a line with the model's first texture; "
            "its picture then shows below after Apply, to Replace. 3D shows the figure with the faction's texture.")
        ).grid(row=r, column=0, columnspan=cols, sticky="w", pady=(4, 0))

    def pick_figure(self, ctype, level, model, now):
        a = self.app
        a.remember()
        want = list(a.figures.get(ctype) or now)
        want[level] = model
        if want == list(now):
            a.figures.pop(ctype, None)
        else:
            a.figures[ctype] = want
        a.status.set("%s on the campaign map: %s - Preview, then Apply." % (ctype, ", ".join(want)))
        self.load()

    def view_figure(self, model, faction):
        from . import stratmodels as SM
        from .gui_meshview import ModelViewer
        info = SM.mesh_info(self.app.mod, model)
        if info is None or not info.meshes:
            messagebox.showinfo("3D", "%s names no model file (.cas) in descr_model_strat.txt." % model)
            return
        ModelViewer(self, self.app.mod, info, (faction,), title="Campaign map figure in 3D")

    @staticmethod
    def _need(size, target):
        if not size:
            return "as the file it replaces"
        if target.startswith("symbol:") and isinstance(size[2], str):
            return "needs %d x %d (kept in the sheet's DDS %s)" % size
        if target.lower().endswith(".dds"):
            return "needs %d x %d, DDS %s (with its mipmaps)" % size
        return "needs %d x %d, %d-bit TGA" % size

    def replace(self, target, size, label, link=None, extra=None):
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
        self.app.art_replace[target] = {"src": src, "extra": extra} if extra else \
            {"src": src, "link": link} if link else src
        self.app.status.set("%s: %s - Preview, then Apply." % (label, os.path.basename(src)))
        self.load()

    def emblem_window(self):
        """One picture -> every emblem picture of the faction (emblem.py), shown before / after, then put in as
        the Art picks (written on Apply with the rest, a backup first)."""
        from . import emblem as E
        a = self.app
        src_faction, new = self._names()
        if not a.mod or not src_faction:
            messagebox.showinfo("Faction emblem", "Load a mod and pick the faction first.")
            return
        pics = E.emblem_pictures(FA.faction_pictures(a.mod, a.v_campaign.get(), src_faction))
        if not pics:
            messagebox.showinfo("Faction emblem", "No emblem pictures of %s were found." % src_faction)
            return
        src = filedialog.askopenfilename(title="The faction's emblem (best: a square PNG with a clear background)",
                                         filetypes=[("Pictures", "*.png *.tga *.dds *.jpg *.jpeg *.bmp"),
                                                    ("All files", "*.*")])
        if not src:
            return
        try:
            from .recolour import read_picture
            picture = read_picture(src)
        except Exception as e:
            messagebox.showerror("Faction emblem", "Cannot read %s: %s" % (src, e))
            return
        # first fitted by hand (place, size, turn, the shape, the ground, magic wand, paint bucket), then made
        # into every emblem picture (a tester: the emblem needs an editor of its own)
        from . import emblem_edit as EE
        from .gui_emblem import EmblemFitter
        from .recolour import faction_colours
        olds = {p["rel"]: E._old(p) for p in pics}
        cols = faction_colours(a.mod).get(src_faction, (None, None))
        EmblemFitter(self, picture, EE.frame_mask(pics, olds), cols,
                     lambda master, sym: self._emblem_made(master, pics, src, src_faction, new, sym))

    def _banner_settings(self, pics, src_faction):
        """The battle banners' first look: the blank banner nearest the old one's shape, the faction's primary."""
        from . import banners as B
        from . import emblem as E
        from .recolour import faction_colours
        a = self.app
        blanks = B.templates(a.mod)
        if not blanks:
            return blanks, None
        own = next((p for p in pics if E.is_banner(p) and p["link"][1] == "standard_texture"), None)
        fc = faction_colours(a.mod).get(src_faction, (None, None))
        first = a.colours.get("primary") or fc[0] or (200, 200, 200)
        second = a.colours.get("secondary") or fc[1] or (240, 240, 240)
        kind = B.best_template(blanks, E._old(own) if own else None)
        return blanks, {"kind": kind, "colours": [tuple(first[:3]), tuple(second[:3]), (240, 240, 240)],
                        "pattern": "plain", "boxes": None}

    def _emblem_made(self, master, pics, src, src_faction, new, symbol=None, banner=None):
        from . import emblem as E
        a = self.app
        blanks, first = self._banner_settings(pics, src_faction)
        banner = banner or first
        made = E.build(master, pics, symbol, dict(banner, blank=blanks[banner["kind"]]) if banner else None)
        import tempfile
        paths = E.save_all(made, tempfile.mkdtemp(prefix="emblem_"))
        w = tk.Toplevel(self)
        w.title("Faction emblem - %s" % (new or src_faction))
        w.transient(self.winfo_toplevel())
        ShortHint(w, text=(
            "Every place the game shows the emblem, now and after - the flag on the campaign map and the battle "
            "banners carry the symbol alone - the banners made from the game's blank white banner dyed in the faction's colour. Each picture keeps "
            "its size and format; the button states are made like the mod's own. Nothing is written yet: 'Use it' puts them on the Art tab, "
            "Preview and Apply write them with a backup (Restore gives them back).")).pack(anchor="w", padx=8, pady=6)
        grid = ttk.Frame(w, padding=8)
        grid.pack()
        photos = []
        from PIL import Image, ImageTk
        for k, p in enumerate(pics):
            cell = ttk.Frame(grid, padding=4)
            cell.grid(row=k // 6, column=k % 6, sticky="n")
            for j, im in enumerate((E._old(p), made.get(p["rel"]))):
                if im is None:
                    continue
                x = im.copy()
                if max(x.size) < 48:
                    x = x.resize((x.size[0] * 2, x.size[1] * 2), Image.NEAREST)
                x.thumbnail((96, 96))
                bg = Image.new("RGBA", x.size, (110, 110, 110, 255))
                bg.alpha_composite(x)
                ph = ImageTk.PhotoImage(bg)
                photos.append(ph)
                tk.Label(cell, image=ph).grid(row=0, column=j, padx=1)
            ttk.Label(cell, text="%s\n%d x %d" % (p["label"], p["size"][0], p["size"][1]), wraplength=200,
                      justify="center", foreground="#444").grid(row=1, column=0, columnspan=2)
            if E.is_banner(p):
                if p["rel"] not in made:
                    ttk.Label(cell, text="no blank banner (standard_routing) in the mod - left as it is",
                              foreground="#a60", wraplength=200).grid(row=2, column=0, columnspan=2)
                else:
                    ttk.Button(cell, text="Banner...", command=lambda: fix()).grid(row=3, column=0, columnspan=2)
        w._photos = photos

        def fix():
            from .gui_banners import BannerWindow

            def done(got):
                w.destroy()
                self._emblem_made(master, pics, src, src_faction, new, symbol, got)
            BannerWindow(w, blanks, symbol or master, banner, done)

        def use():
            a.remember()
            for p in pics:
                if p["rel"] in paths:
                    a.art_replace[FA.picture_target(p, src_faction, new or src_faction)] = paths[p["rel"]]
            w.destroy()
            a.status.set("Faction emblem: %d pictures made from %s - Preview, then Apply." % (
                len(paths), os.path.basename(src)))
            self.load()
        bar = ttk.Frame(w, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text="Use it (%d pictures)" % len(paths), command=use).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="right")

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
        self.lbl_map.configure(text="%d town(s) lit - the faction's towns (given on the Map) (written with the "
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
