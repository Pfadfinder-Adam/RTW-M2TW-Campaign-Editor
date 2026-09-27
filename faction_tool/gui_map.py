"""The Map tab: the campaign map as a full-window minimap - the game's own
radar picture, the political colours over it on demand, cities and ports.
Wheel zooms at the mouse, dragging pans, clicking a city picks it."""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from .mapdata import REBELS

ZOOMS = (1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24)       # screen pixels per tile


class MapView(ttk.Frame):
    def __init__(self, master, status=None):
        super().__init__(master)
        self.cmap = None
        self.owners, self.colours, self.faction, self.chosen = {}, {}, None, set()
        self.on_city = None
        self.status = status
        bar = ttk.Frame(self, padding=(0, 0, 0, 4))
        bar.pack(fill="x")
        self.v_pol = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Political", variable=self.v_pol, command=self.render).pack(side="left")
        self.v_names = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Town names", variable=self.v_names, command=self.render).pack(side="left", padx=8)
        self.v_ports = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Ports", variable=self.v_ports, command=self.render).pack(side="left")
        ttk.Button(bar, text="Fit", width=5, command=self.fit).pack(side="right")
        ttk.Button(bar, text="+", width=3, command=lambda: self.zoom_by(1)).pack(side="right", padx=2)
        ttk.Button(bar, text="-", width=3, command=lambda: self.zoom_by(-1)).pack(side="right")
        ttk.Label(bar, text="wheel: zoom   drag: move   click a town: add / remove it",
                  foreground="#666").pack(side="right", padx=12)
        self.canvas = tk.Canvas(self, background="#1d2b3a", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.readout = ttk.Label(self, text="", anchor="w")
        self.readout.pack(fill="x")
        self.z, self.ox, self.oy = 2, 0.0, 0.0           # zoom; top-left corner in top-down tile units
        self._photo = None
        self._pending = None
        self._drag = None
        c = self.canvas
        c.bind("<Configure>", lambda e: self.render())
        c.bind("<MouseWheel>", self._wheel)
        c.bind("<Button-4>", lambda e: self._wheel(e, 1))
        c.bind("<Button-5>", lambda e: self._wheel(e, -1))
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._move)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Motion>", self._hover)

    # ---- data ----
    def load(self, cmap, owners, colours, faction=None, chosen=(), on_city=None):
        first = self.cmap is None or self.cmap is not cmap
        self.cmap, self.owners, self.colours = cmap, dict(owners), colours
        self.faction, self.chosen, self.on_city = faction, set(chosen), on_city
        if first:
            self.fit()
        else:
            self.render()

    # ---- geometry ----
    def to_screen(self, x, y):
        """Tile (x, y) (y up) -> the canvas point at the tile's centre."""
        return (x - self.ox + 0.5) * self.z, ((self.cmap.h - 1 - y) - self.oy + 0.5) * self.z

    def to_tile(self, sx, sy):
        x = int(self.ox + sx / self.z)
        row = int(self.oy + sy / self.z)
        return x, self.cmap.h - 1 - row

    def fit(self):
        if not self.cmap:
            return
        cw, ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        self.z = min(cw / self.cmap.w, ch / self.cmap.h)
        self.ox = self.oy = 0.0
        self.render()

    def zoom_by(self, step, at=None):
        if not self.cmap:
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        sx, sy = at or (cw / 2, ch / 2)
        tx, ty = self.ox + sx / self.z, self.oy + sy / self.z
        bigger = [z for z in ZOOMS if z > self.z + 1e-6]
        smaller = [z for z in ZOOMS if z < self.z - 1e-6]
        fit = min(cw / self.cmap.w, ch / self.cmap.h)
        if step > 0 and bigger:
            self.z = bigger[0]
        elif step < 0:
            self.z = max(smaller[-1] if smaller else fit, fit)
        self.ox, self.oy = tx - sx / self.z, ty - sy / self.z
        self.render()

    def _clamp(self):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        vw, vh = cw / self.z, ch / self.z
        self.ox = min(max(self.ox, 0), max(self.cmap.w - vw, 0)) if vw < self.cmap.w else (self.cmap.w - vw) / 2
        self.oy = min(max(self.oy, 0), max(self.cmap.h - vh, 0)) if vh < self.cmap.h else (self.cmap.h - vh) / 2

    # ---- drawing ----
    def render(self):
        if self._pending is None:
            self._pending = self.after(15, self._render)

    def _render(self):
        self._pending = None
        c = self.canvas
        c.delete("all")
        if not self.cmap:
            c.create_text(20, 20, anchor="nw", fill="#ccc", text="Load a mod: the campaign map shows here.")
            return
        self._clamp()
        cw, ch = c.winfo_width(), c.winfo_height()
        vw, vh = cw / self.z, ch / self.z
        box = (self.ox, self.oy, self.ox + vw, self.oy + vh)
        bg = self.cmap.background()                                   # 2 px per tile
        pic = bg.crop(tuple(int(round(v * 2)) for v in box)).resize((cw, ch), Image.BILINEAR)
        if self.v_pol.get():
            pol = self.cmap.political(self.owners, self.colours, self.faction)
            ov = pol.crop(tuple(int(round(v)) for v in box)).resize((cw, ch), Image.NEAREST)
            pic = Image.alpha_composite(pic.convert("RGBA"), ov)
        self._photo = ImageTk.PhotoImage(pic)
        c.create_image(0, 0, anchor="nw", image=self._photo)
        self._markers(cw, ch)

    def _markers(self, cw, ch):
        c, cm = self.canvas, self.cmap
        size = max(3, min(self.z * 0.9, 14))
        font = ("", 8 if self.z < 10 else 9)
        if self.v_ports.get() and self.z >= 3:
            for region, (x, y) in cm.ports.items():
                sx, sy = self.to_screen(x, y)
                if -10 < sx < cw + 10 and -10 < sy < ch + 10:
                    r = size * 0.45
                    c.create_oval(sx - r, sy - r, sx + r, sy + r, fill="#2a6fdb", outline="white", width=1)
        for region, (x, y) in cm.cities.items():
            sx, sy = self.to_screen(x, y)
            if not (-40 < sx < cw + 40 and -20 < sy < ch + 20):
                continue
            owner = self.owners.get(region, "slave")
            rgb = REBELS if owner == "slave" else self.colours.get(owner, REBELS)
            mine = region in self.chosen
            r = size / 2 + (2 if mine else 0)
            c.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill="#%02x%02x%02x" % rgb,
                               outline="#ffd400" if mine else "black", width=3 if mine else 1,
                               tags=("city", "city:" + region))
            if self.v_names.get() and (self.z >= 4 or mine):
                name = cm.info.get(region, {}).get("settlement", region)
                c.create_text(sx + r + 3, sy + 1, text=name, anchor="w", fill="black", font=font)   # shadow
                c.create_text(sx + r + 2, sy, text=name, anchor="w", fill="white", font=font)

    # ---- mouse ----
    def _wheel(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        self.zoom_by(d, (e.x, e.y))

    def _press(self, e):
        self._drag = (e.x, e.y, self.ox, self.oy, False)

    def _move(self, e):
        if not self._drag or not self.cmap:
            return
        x0, y0, ox, oy, _ = self._drag
        if abs(e.x - x0) + abs(e.y - y0) > 3:
            self._drag = (x0, y0, ox, oy, True)
            self.ox, self.oy = ox - (e.x - x0) / self.z, oy - (e.y - y0) / self.z
            self.render()

    def _release(self, e):
        moved = self._drag and self._drag[4]
        self._drag = None
        if moved or not self.cmap:
            return
        hit = self.canvas.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        for item in reversed(hit):
            for tag in self.canvas.gettags(item):
                if tag.startswith("city:") and self.on_city:
                    self.on_city(tag[5:])
                    return

    def _hover(self, e):
        if self.cmap:
            x, y = self.to_tile(e.x, e.y)
            self.readout.configure(text=self.cmap.describe(x, y, self.owners))
