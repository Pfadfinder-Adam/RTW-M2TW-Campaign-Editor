"""The Map editor's special places (specialplaces.py): a right click on the map > 'Special place here...' or on a
place's diamond > its window; a double click on the diamond opens it too. The window: its name, what it gives (two
lines), its text, its model (any of the campaign map's, or one's own .cas) and size, a picture, money a turn for its
holder - and the window the game will show, drawn as it will look. Keep for Apply puts every place of the mod into
the session's list (one part 'Special places'), written by Apply with the rest."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import specialplaces as SP

TITLE = "Special place"
OWN = "(my own .cas file...)"
_OPEN = {}                                         # place id (or the tile of a new one) -> its window


def places(app):
    """The mod's special places as the editor holds them now (read from the mod's script once, then the window's
    changes kept for Apply)."""
    key = os.path.normcase(os.path.abspath(app.mod.data)) if app.mod else None
    got = app.__dict__.get("_special")
    if got is None or got[0] != key:
        got = app._special = [key, SP.read(app.mod) if app.mod else [], {}, {}]   # places, pictures, own models
    return got[1]


def _extra(app):
    places(app)
    return app._special[2], app._special[3]


def marks(app):
    """The diamonds of the campaign shown: [{'id', 'xy', 'title', 'new'}]."""
    if not app.mod:
        return []
    camp = app.v_campaign.get()
    return [{"id": str(p.id or "new"), "xy": (p.x, p.y), "title": p.title, "new": getattr(p, "_new", False)}
            for p in places(app) if not p.campaign or p.campaign == camp]


def culture_of(app):
    """place -> the culture of its tile's owner (whose scroll the window wears)."""
    cultures = dict(app.mod.factions())
    owners = app.owners_after() if hasattr(app, "owners_after") else {}

    def f(p):
        region = app._cmap.region_at(p.x, p.y) if getattr(app, "_cmap", None) else None
        return cultures.get(owners.get(region)) if region else None
    return f


def keep(app, win=None):
    """Every place of the mod into the session's list (one part, replaced when kept again)."""
    from .gui_util import keep_for_apply
    pics, own = _extra(app)
    lst = places(app)

    def after(bdir):
        app._special = None                           # read again from what was written
        if hasattr(app, "show_map"):
            app.show_map()
    return keep_for_apply(win or app, "special_places", "Special places: %d" % len(lst),
                          lambda: SP.plan(app.mod, lst, culture_of(app), dict(pics), dict(own)), after, TITLE)


def open_place(app, place_id=None, xy=None):
    """The window of the place `place_id` (its diamond), or of a new one at tile xy."""
    key = str(place_id) if place_id is not None else "new:%d,%d" % tuple(xy)
    w = _OPEN.get(key)
    if w is not None and w.winfo_exists():
        w.deiconify()
        w.lift()
        return w
    p = next((q for q in places(app) if str(q.id) == str(place_id) or (str(place_id) == "new" and
                                                                       getattr(q, "_new", False))), None)
    if p is None:
        if xy is None:
            return None
        p = SP.Place(campaign=app.v_campaign.get(), x=xy[0], y=xy[1])
        p._new = True
    w = _OPEN[key] = PlaceWindow(app, p)
    return w


def move(app, place_id, xy):
    """A place's diamond dragged on the map to tile xy: the place stands there from the next Apply (its open window
    follows - it holds the same place)."""
    p = next((q for q in places(app) if str(q.id or "new") == str(place_id)), None)
    if p is None or (p.x, p.y) == tuple(xy):
        app.show_map()
        return
    p.x, p.y = int(xy[0]), int(xy[1])
    if getattr(p, "_new", False):                     # not kept yet: its window keeps it with the rest
        app.status.set("Special place moved to %d, %d - Keep for Apply in its window." % (p.x, p.y))
    elif keep(app):
        app.status.set("Special place %s moved to %d, %d - written with the next Apply (Preview first)."
                       % (p.title, p.x, p.y))
    w = _OPEN.get(str(place_id))
    if w is not None and w.winfo_exists():
        w.title("%s - %s" % (TITLE, p.title or "new, at %d, %d" % (p.x, p.y)))
    app.show_map()


def delete(app, place_id):
    lst = places(app)
    p = next((q for q in lst if str(q.id) == str(place_id)), None)
    if p is None:
        return
    lst.remove(p)
    keep(app)
    app.status.set("The special place %s goes with the next Apply (Preview first)." % p.title)
    app.show_map()


class PlaceWindow(tk.Toplevel):
    def __init__(self, app, place):
        super().__init__(app)
        self.app, self.place, self.mod = app, place, app.mod
        self.title("%s - %s" % (TITLE, place.title or "new, at %d, %d" % (place.x, place.y)))
        self.transient(app)
        self.picture = None                     # a new picture picked (its file)
        from .packs import game_kind
        from .limits import engine_of
        self.game = "medieval2" if game_kind(self.mod) == "medieval2" else "rome"
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        left = ttk.Frame(frm)
        left.pack(side="left", fill="y")
        right = ttk.Frame(frm, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)
        from .gui_util import ShortHint, hint
        ShortHint(left, text=(
            "A model of your own on the campaign map with its own window, as the game's wonders have - for any "
            "place: a mine, a holy site, a lighthouse, a battlefield. The engine (%s) draws it on its tile; the mouse "
            "on it shows its name, a double click opens its window at the screen's left (the game's own scroll). "
            "A name and a text are a must; what it gives, a picture and money are yours to add." % (
                "REX" if self.game == "rome" else "M2EX"))).pack(anchor="w")
        if not engine_of(self.mod):
            ttk.Label(left, foreground="#b60", wraplength=420, justify="left", text=(
                "This mod runs without %s: the place is written, but only the engine draws it in the game." % (
                    "REX" if self.game == "rome" else "M2EX"))).pack(anchor="w", pady=(4, 0))
        form = ttk.Frame(left)
        form.pack(anchor="w", fill="x", pady=(6, 0))
        self.v_title = tk.StringVar(value=place.title)
        self.v_money = tk.StringVar(value=str(place.money or ""))
        self.v_size = tk.DoubleVar(value=place.size or 1.0)
        r = 0

        def row(label, widget, tip=None):
            nonlocal r
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="nw", pady=2)
            widget.grid(row=r, column=1, sticky="we", padx=6, pady=2)
            if tip:
                hint(form, tip, width=420).grid(row=r, column=2, sticky="nw")
            r += 1
        row("Name", ttk.Entry(form, textvariable=self.v_title, width=40))
        self.t_bonus = tk.Text(form, width=40, height=2, wrap="word")
        self.t_bonus.insert("1.0", place.bonus)
        row("What it gives", self.t_bonus, "One or two lines under its name (green), e.g. '+150 florins a turn to "
                                           "whoever holds it'. Words only - money a turn is below.")
        self.t_text = tk.Text(form, width=40, height=6, wrap="word")
        self.t_text.insert("1.0", place.text)
        row("Text", self.t_text, "What the place is - the window's main text (a must).")
        self.v_model = tk.StringVar(value=place.model)
        self.models = SP.model_choices(self.mod)
        cb = ttk.Combobox(form, textvariable=self.v_model, values=self.models + [OWN], width=40, height=24)
        cb.bind("<<ComboboxSelected>>", lambda e: self._model_picked())
        cb.bind("<KeyRelease>", lambda e: cb.configure(values=[m for m in self.models if self.v_model.get().lower()
                                                               in m.lower()] + [OWN]))
        row("Model", cb, "Any model of the campaign map (models_strat: towers, forts, wonders, mines, resources...) "
                         "- type to find one - or your own .cas (copied into the mod's models_strat; its textures "
                         "go beside it in models_strat/textures, as the game's own).")
        bar = ttk.Frame(form)
        ttk.Button(bar, text="View in 3D...", command=self.view_model).pack(side="left")
        row("", bar)
        row("Size", ttk.Spinbox(form, from_=0.2, to=5.0, increment=0.1, textvariable=self.v_size, width=6),
            "1.0 = the model's own size on the map.")
        row("Money a turn", ttk.Entry(form, textvariable=self.v_money, width=8),
            "Given at the start of its turn to the faction holding the place's tile; empty or 0: none.")
        pb = ttk.Frame(form)
        ttk.Button(pb, text="Picture...", command=self.pick_picture).pack(side="left")
        ttk.Button(pb, text="No picture", command=self.no_picture).pack(side="left", padx=4)
        self.lbl_pic = ttk.Label(pb, foreground="#555")
        self.lbl_pic.pack(side="left", padx=4)
        row("Picture", pb, "Across the whole width of its window, never cut (PNG, JPG, TGA).")
        form.columnconfigure(1, weight=1)
        self.lbl_where = ttk.Label(left, foreground="#555", text="Tile %d, %d%s" % (
            place.x, place.y, " - campaign %s" % place.campaign if place.campaign else ""))
        self.lbl_where.pack(anchor="w", pady=(6, 0))
        self.lbl_problems = ttk.Label(left, foreground="#a33", wraplength=420, justify="left")
        self.lbl_problems.pack(anchor="w")
        bot = ttk.Frame(left)
        bot.pack(anchor="w", pady=(10, 0))
        ttk.Button(bot, text="Show the game's window", command=self.preview).pack(side="left")
        ttk.Button(bot, text="Keep for Apply", command=self.keep).pack(side="left", padx=4)
        if not getattr(place, "_new", False):
            ttk.Button(bot, text="Delete this place", command=self.delete).pack(side="left", padx=(12, 0))
        ttk.Button(bot, text="Close", command=self.destroy).pack(side="left", padx=(12, 0))
        ttk.Label(right, text="In the game (its words drawn here roughly - the game's font wraps them):",
                  foreground="#555").pack(anchor="w")
        self.canvas = tk.Canvas(right, width=SP.WIDTH + 10, height=620, highlightthickness=0, background="#2e3036")
        self.canvas.pack(anchor="nw", fill="both", expand=True)
        self._photo = None
        self._shown_picture()
        self.preview()

    # ---- the fields ----
    def _model_picked(self):
        if self.v_model.get() != OWN:
            return
        path = filedialog.askopenfilename(parent=self, title="A model for %s (.cas)" % (self.v_title.get() or "it"),
                                          filetypes=[("Campaign map models", "*.cas"), ("All files", "*.*")])
        if not path:
            self.v_model.set(self.place.model)
            return
        rel = "data/models_strat/%s" % os.path.basename(path).replace(" ", "_")
        _extra(self.app)[1][rel] = path
        self.v_model.set(rel)

    def view_model(self):
        from . import models as MO
        from .gui_meshview import ModelViewer
        rel = self.v_model.get()
        if not rel or rel == OWN:
            return
        info = MO.ModelInfo(os.path.basename(rel))
        info.meshes = [rel[5:] if rel.lower().startswith("data/") else rel]
        info.one_texture = True
        ModelViewer(self, self.mod, info, title="Special place's model in 3D")

    def pick_picture(self):
        path = filedialog.askopenfilename(parent=self, title="A picture for %s" % (self.v_title.get() or "it"),
                                          filetypes=[("Pictures", "*.png *.jpg *.jpeg *.tga *.bmp *.dds"),
                                                     ("All files", "*.*")])
        if path:
            self.picture = path
            self._shown_picture()
            self.preview()

    def no_picture(self):
        self.picture = ""
        self._shown_picture()
        self.preview()

    def _shown_picture(self):
        if self.picture:
            self.lbl_pic.configure(text=os.path.basename(self.picture))
        elif self.picture == "" or not self.place.picture:
            self.lbl_pic.configure(text="none")
        else:
            self.lbl_pic.configure(text=os.path.basename(self.place.picture))

    def _picture_image(self):
        from PIL import Image
        path = self.picture if self.picture else (None if self.picture == "" else (
            self.mod.find(self.place.picture[5:]) if self.place.picture else None))
        if not path:
            return None
        try:
            return Image.open(path).convert("RGBA")
        except OSError:
            return None

    def _values(self):
        try:
            money = int(self.v_money.get().strip() or 0)
        except ValueError:
            money = 0
        try:
            size = float(self.v_size.get())
        except (ValueError, tk.TclError):
            size = 1.0
        return SP.Place(id=self.place.id, campaign=self.place.campaign, x=self.place.x, y=self.place.y,
                        model=self.v_model.get() if self.v_model.get() != OWN else "", size=size,
                        title=self.v_title.get().strip(), bonus=self.t_bonus.get("1.0", "end").strip(),
                        text=self.t_text.get("1.0", "end").strip(), money=money,
                        picture="" if self.picture == "" else self.place.picture)

    # ---- the game's window, drawn ----
    def preview(self):
        from PIL import ImageDraw, ImageTk
        p = self._values()
        img, lay = SP.window_picture(self.mod, p, self.game, culture_of(self.app)(p), self._picture_image())
        d = ImageDraw.Draw(img)
        words = _rough_lines

        tw = len(p.title) * 7
        d.text(((lay["w"] - tw) // 2, lay["title"] + 6), p.title, fill=(70, 30, 10))
        y = lay["bonus"]
        for line in words(p.bonus, lay["inner"]):
            d.text((lay["mx"], y), line, fill=(25, 85, 20))
            y += SP.LINE
        y = lay["text"]
        for line in words(p.text, lay["inner"]):
            d.text((lay["mx"], y), line, fill=(40, 25, 10))
            y += SP.LINE
        owner = self._owner()
        held = "Held by: %s" % (owner or "nobody")
        d.text(((lay["w"] - len(held) * 6) // 2, lay["held"]), held, fill=(60, 30, 10))
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(5, 5, anchor="nw", image=self._photo)
        self.canvas.configure(height=min(900, img.height + 10))
        probs = SP.problems(p)
        self.lbl_problems.configure(text=("Before Keep for Apply: " + "; ".join(probs) + ".") if probs else "")

    def _owner(self):
        region = self.app._cmap.region_at(self.place.x, self.place.y) if getattr(self.app, "_cmap", None) else None
        owners = self.app.owners_after() if hasattr(self.app, "owners_after") else {}
        f = owners.get(region) if region else None
        names = self.app.shown_names() if hasattr(self.app, "shown_names") else {}
        return names.get(f) or f

    # ---- keeping ----
    def keep(self):
        p = self._values()
        probs = SP.problems(p)
        if probs:
            messagebox.showerror(TITLE, "Before it is kept: " + "; ".join(probs) + ".", parent=self)
            return
        lst = places(self.app)
        old = next((q for q in lst if q is self.place), None)
        if old is not None:
            lst[lst.index(old)] = p
        else:
            lst.append(p)
        if not p.id:
            p.id = max([q.id for q in lst] + [0]) + 1
        if self.picture:
            _extra(self.app)[0][p.id] = self.picture
        if keep(self.app, self):
            self.place = p
            self.app.status.set("Special place %s kept - Apply changes (bottom left) writes it with the rest." % p.title)
            self.app.show_map()
            self.destroy()

    def delete(self):
        from .gui_util import ask
        if not ask(TITLE, "Take %s off the map? (written with the next Apply)" % self.place.title, parent=self,
                   yes="Take it off", no="Keep it"):
            return
        delete(self.app, self.place.id)
        self.destroy()


def _rough_lines(text, width, size=17):
    """The text cut into lines about as the game's font would (half a size a letter) - for the preview only."""
    per = max(8, int(width / (size * 0.42)))
    out = []
    for para in (text or "").split("\n"):
        line = ""
        for word in para.split():
            if line and len(line) + 1 + len(word) > per:
                out.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        out.append(line)
    return out if text else []


__all__ = ["places", "marks", "open_place", "delete", "keep", "PlaceWindow"]
