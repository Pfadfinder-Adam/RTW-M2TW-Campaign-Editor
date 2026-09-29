"""The Map tab: the campaign map as a full-window minimap - a
terrain picture, the political colours over it on demand, cities and ports.
Wheel zooms at the mouse, dragging pans, clicking a city picks it."""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from . import theme
from .mapdata import REBELS

ZOOMS = (1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)       # screen pixels per tile


class MapView(ttk.Frame):
    def __init__(self, master, status=None, on_layers=None):
        super().__init__(master)
        self.on_layers = on_layers                      # the window redraws when a layer that needs it changes
        self.cmap = None
        self.owners, self.colours, self.faction, self.chosen = {}, {}, None, set()
        self.labels = {}
        self.on_city = None
        self.status = status
        bar = ttk.Frame(self, padding=(0, 0, 0, 4))
        bar.pack(fill="x")
        # the layers, in one menu: what is drawn on the map
        self.v_pol = tk.BooleanVar(value=True)
        self.v_borders = tk.BooleanVar(value=True)
        self.v_names = tk.BooleanVar(value=True)
        self.v_ports = tk.BooleanVar(value=True)
        self.v_chars = tk.BooleanVar(value=True)
        self.v_res = tk.BooleanVar(value=False)
        self.v_dip = tk.BooleanVar(value=False)
        self.v_regions = tk.BooleanVar(value=False)
        # how the ground is drawn (kept between starts): tile by tile, relief, rivers, the tile grid up close
        from . import settings
        look = settings.get("map_look") or {}
        # one colour per tile unless the detailed picture was picked ("ground"; 0.6.0 kept a "tiles" flag
        # that defaulted to off - not read, so everyone starts on tiles)
        self.v_tiles = tk.BooleanVar(value=look.get("ground", "tiles") != "detailed")
        self.v_relief = tk.BooleanVar(value=bool(look.get("relief", True)))
        self.v_rivers = tk.BooleanVar(value=bool(look.get("rivers", True)))
        self.v_grid = tk.BooleanVar(value=bool(look.get("grid", True)))

        def look_changed():
            settings.put("map_look", {"ground": "tiles" if self.v_tiles.get() else "detailed",
                                      "relief": self.v_relief.get(),
                                      "rivers": self.v_rivers.get(), "grid": self.v_grid.get()})
            self.render()
        relayer = lambda: self.on_layers() if self.on_layers else self.render()
        lb = ttk.Menubutton(bar, text="Layers")
        lm = tk.Menu(lb, tearoff=False)
        for label, var, cmd in (("Political colours", self.v_pol, self.render), ("Borders", self.v_borders, relayer),
                                ("Town names", self.v_names, self.render), ("Ports", self.v_ports, self.render),
                                ("Characters", self.v_chars, self.render), ("Resources", self.v_res, relayer),
                                ("Diplomacy colours", self.v_dip, relayer)):
            lm.add_checkbutton(label=label, variable=var, command=cmd)
        lm.add_separator()
        for label, var in (("Ground by tiles: one colour per tile (off = detailed picture)", self.v_tiles),
                           ("Relief (map_heights)", self.v_relief),
                           ("Rivers, fords, cliffs (map_features)", self.v_rivers),
                           ("Tile grid when zoomed in", self.v_grid)):
            lm.add_checkbutton(label=label, variable=var, command=look_changed)
        lb["menu"] = lm
        lb.pack(side="left")
        # the two modes that change what a click does, as switches of their own
        ttk.Checkbutton(bar, text="Edit regions", variable=self.v_regions,
                        command=self._regions_toggled).pack(side="left", padx=(12, 4))
        ttk.Checkbutton(bar, text="Edit resources", variable=self.v_res, command=relayer).pack(side="left", padx=4)
        self.lbl_layers = ttk.Label(bar, text="", foreground="#666")
        self.lbl_layers.pack(side="left", padx=8)
        for v in (self.v_pol, self.v_borders, self.v_names, self.v_ports, self.v_chars, self.v_res, self.v_dip,
                  self.v_regions):
            v.trace_add("write", lambda *a: self._layers_label())
        self._layers_label()
        ttk.Button(bar, text="Fit", width=5, command=self.fit).pack(side="right")
        ttk.Button(bar, text="+", width=3, command=lambda: self.zoom_by(1)).pack(side="right", padx=2)
        ttk.Button(bar, text="-", width=3, command=lambda: self.zoom_by(-1)).pack(side="right")
        ttk.Label(bar, text="wheel: zoom   left drag: map   right drag: markers   click a town: take / give",
                  foreground="#666").pack(side="right", padx=12)
        from . import settings
        self.v_legend = tk.BooleanVar(value=bool(settings.get("map_legend", True)))
        ttk.Checkbutton(bar, text="Legend", variable=self.v_legend, command=self._legend_toggled).pack(
            side="left", padx=(4, 0), before=self.lbl_layers)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, background="#1d2b3a", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(side="left", fill="both", expand=True)
        # the legend: what every sign means, on the right; shown or hidden as last time
        self.legend = ttk.Frame(body, padding=(6, 0, 0, 0))
        self.legend_canvas = tk.Canvas(self.legend, width=250, background="#f4f1ea", highlightthickness=1,
                                       highlightbackground="#bbb")
        lsb = ttk.Scrollbar(self.legend, orient="vertical", command=self.legend_canvas.yview)
        self.legend_canvas.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right", fill="y")
        self.legend_canvas.pack(side="left", fill="y", expand=True)
        for seq, step in (("<MouseWheel>", None), ("<Button-4>", -1), ("<Button-5>", 1)):
            self.legend_canvas.bind(seq, lambda e, st=step: self.legend_canvas.yview_scroll(
                st if st is not None else int(-e.delta / 120), "units"))
        if self.v_legend.get():
            self.legend.pack(side="right", fill="y")
        self.readout = ttk.Label(self, text="", anchor="w")
        self.readout.pack(fill="x")
        self.z, self.ox, self.oy = 2, 0.0, 0.0           # zoom; top-left corner in top-down tile units
        self._photo = None
        self._pending = None
        self._drag = None
        self._cdrag = None
        self._pdrag = None               # a town or port being dragged
        # the Regions mode: left drag paints tiles to a region, right click picks one
        self.region_mode, self.paint_overlay, self.region_points = False, {}, []
        self.region_painted, self.region_colours = {}, {}
        self.on_paint = self.on_pick = None
        self.brush, self._painting, self._rclick = 1, False, False
        self.chars, self.draggable, self.symbols = [], set(), {}
        self.on_char_move = self.check_tile = None
        # resources: [{id, kind, xy}]; check_res(id, xy) -> None or why; on_res_move(id, xy); on_res_click(id)
        self.resources, self.check_res, self.on_res_move, self.on_res_click = [], None, None, None
        self.res_sel, self._rdrag, self._rpress = None, None, None
        self._symimg = {}
        c = self.canvas
        c.bind("<Configure>", lambda e: self.render())
        c.bind("<MouseWheel>", self._wheel)
        c.bind("<Button-4>", lambda e: self._wheel(e, 1))
        c.bind("<Button-5>", lambda e: self._wheel(e, -1))
        # left button: the map moves (a click picks a town); right button - or Ctrl + left
        # on a touchpad - moves characters, towns and ports, so nothing moves by accident
        c.bind("<ButtonPress-1>", lambda e: self._press(e, icons=False))
        c.bind("<Control-ButtonPress-1>", lambda e: self._press(e, icons=True))
        c.bind("<B1-Motion>", self._move)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<ButtonPress-3>", lambda e: self._press(e, icons=True))
        c.bind("<B3-Motion>", self._move)
        c.bind("<ButtonRelease-3>", self._release)
        c.bind("<Motion>", self._hover)
        c.bind("<Leave>", lambda e: (self._grow(None), c.delete("tile_outline")))
        self._hot = None                                # the marker under the mouse, drawn bigger

    def _layers_label(self):
        on = [n for n, v in (("political", self.v_pol), ("borders", self.v_borders), ("names", self.v_names),
                             ("ports", self.v_ports), ("characters", self.v_chars), ("resources", self.v_res),
                             ("diplomacy", self.v_dip)) if v.get()]
        self.lbl_layers.configure(text="shown: " + (", ".join(on) or "the ground only"))

    def _regions_toggled(self):
        """Regions mode colours the land by region: the political colours and the
        borders are switched off meanwhile, and come back as they were after."""
        if self.v_regions.get():
            self._before_regions = (self.v_pol.get(), self.v_borders.get())
            self.v_pol.set(False)
            self.v_borders.set(False)
        elif getattr(self, "_before_regions", None):
            self.v_pol.set(self._before_regions[0])
            self.v_borders.set(self._before_regions[1])
            self._before_regions = None
        if self.on_layers:
            self.on_layers()
        else:
            self.render()

    # ---- the legend ----
    def _legend_toggled(self):
        from . import settings
        settings.put("map_legend", bool(self.v_legend.get()))
        if self.v_legend.get():
            self.legend.pack(side="right", fill="y")
            self._draw_legend()
        else:
            self.legend.pack_forget()

    LEGEND_RED = (190, 40, 40)

    def _draw_legend(self):
        """Every sign the map draws, with what it means (drawn by the map's own code)."""
        if not self.v_legend.get():
            return
        lc = self.legend_canvas
        lc.delete("all")
        main, self.canvas = self.canvas, lc            # the drawing helpers draw on self.canvas
        colours = self.colours
        self.colours = dict(colours, __legend__=self.LEGEND_RED)
        try:
            y = [14]

            def head(text):
                y[0] += 6
                lc.create_text(8, y[0], text=text, anchor="w", font=("", 9, "bold"), fill=theme.palette()["fg"])
                y[0] += 20

            def row(text, draw):
                draw(22, y[0])
                lc.create_text(44, y[0], text=text, anchor="w", font=("", 9), fill=theme.palette()["fg"])
                y[0] += 24

            def town(fill, outline, width, hollow=False):
                def d(x, yy):
                    r = 9
                    lc.create_rectangle(x - r, yy - r, x + r, yy + r, fill="" if hollow else fill, outline=outline,
                                        width=width)
                    if not hollow:
                        self._hall(x, yy, r, self.LEGEND_RED, ())
                return d

            def port(x, yy):
                r = 8
                lc.create_oval(x - r, yy - r, x + r, yy + r, fill="#2a6fdb", outline="white")
                self._anchor(x, yy, r, ())

            def char(kind, army=False, mine=False):
                def d(x, yy):
                    self._draw_char({"id": "legend" if not mine else "legend_mine", "faction": "__legend__",
                                     "kind": kind, "army": army, "name": ""}, x, yy, 20)
                return d
            head("Towns and ports")
            red = "#%02x%02x%02x" % self.LEGEND_RED
            row("a town (its owner's colour)", town(red, "black", 1))
            row("one of your towns", town(red, "#ffd400", 3))
            row("rebel village (no town yet)", town("", "black", 1, hollow=True))
            row("a port", port)
            head("Characters")
            keep = self.draggable
            self.draggable = set(keep) | {"legend_mine"}
            row("an army (general)", char("general", army=True))
            row("yours: drag it (right button)", char("general", army=True, mine=True))
            row("a fleet (admiral)", char("admiral", army=True))
            row("family member, no army", char("named character"))
            for k, label in (("spy", "spy"), ("assassin", "assassin"), ("diplomat", "diplomat"),
                             ("merchant", "merchant"), ("priest", "priest"), ("princess", "princess"),
                             ("inquisitor", "inquisitor"), ("heretic", "heretic"), ("witch", "witch")):
                row(label, char(k))
            self.draggable = keep
            head("Map")
            row("political: land in its owner's colour", lambda x, yy: lc.create_rectangle(
                x - 9, yy - 7, x + 9, yy + 7, fill=red, outline="#401010", width=2))
            row("rebel land: barely tinted", lambda x, yy: lc.create_rectangle(
                x - 9, yy - 7, x + 9, yy + 7, fill="#9a9a9a", outline=""))
            row("the tile under the mouse", lambda x, yy: lc.create_rectangle(
                x - 8, yy - 8, x + 8, yy + 8, outline="white", width=2))
            row("drop here: fine", lambda x, yy: lc.create_rectangle(
                x - 8, yy - 8, x + 8, yy + 8, outline="#30ff60", width=2))
            row("drop here: refused (why below)", lambda x, yy: lc.create_rectangle(
                x - 8, yy - 8, x + 8, yy + 8, outline="#ff3030", width=2))
            kinds = sorted({r["kind"] for r in self.resources})
            if kinds or self.v_res.get():
                head("Resources (first letters)")
                for k in kinds:
                    def d(x, yy, k=k):
                        lc.create_rectangle(x - 9, yy - 9, x + 9, yy + 9, fill=self.res_colour(k), outline="black")
                        lc.create_text(x, yy, text=k[:2].capitalize(), font=("", 8, "bold"))
                    row(k, d)
                if not kinds:
                    lc.create_text(8, y[0], text="(tick Edit resources to see them)", anchor="w",
                                   fill=theme.palette()["muted"])
                    y[0] += 20
            lc.configure(scrollregion=(0, 0, 250, y[0] + 10))
        finally:
            self.canvas, self.colours = main, colours

    # ---- data ----
    def load(self, cmap, owners, colours, faction=None, chosen=(), on_city=None, chars=(), draggable=(),
             on_char_move=None, check_tile=None, symbols=None, on_place=None,
             places=None, check_place=None, on_place_move=None,
             region_mode=False, paint_overlay=None, on_paint=None, on_pick=None, brush=1, region_points=(),
             region_painted=None, region_colours=None, borders=True, ghost=None, locked=None,
             resources=None, check_res=None, on_res_move=None, on_res_click=None, res_sel=None, new_land=None,
             plain=False, labels=None):
        """chars: [{id, faction, name, kind, xy, army, units}]; draggable: ids that may be moved;
        check_tile(id, xy) -> None or why not; on_char_move(id, xy) after a valid drop;
        symbols: {faction: path of its small symbol picture}."""
        first = self.cmap is None or self.cmap is not cmap
        self.cmap, self.owners, self.colours = cmap, dict(owners), colours
        self.faction, self.chosen, self.on_city = faction, set(chosen), on_city
        self.chars, self.draggable = list(chars), set(draggable)
        self.on_char_move, self.check_tile = on_char_move, check_tile
        self.symbols = symbols or {}
        self.on_place = on_place            # on_place(xy) -> None, or why not: the next click places
        # towns and ports dragged to new tiles: {(what, region): xy}; check_place(what, region, xy)
        # -> None or why not; on_place_move(what, region, xy) after a good drop
        self.places = dict(places or {})
        self.check_place, self.on_place_move = check_place, on_place_move
        # Regions mode: paint_overlay {(x, y): (r, g, b)} tiles given to another region;
        # on_paint([tiles]) -> the tiles it took; on_pick(xy); region_points [(xy, 'city'|'port', rgb)]
        self.region_mode, self.paint_overlay = region_mode, dict(paint_overlay or {})
        self.on_paint, self.on_pick, self.brush = on_paint, on_pick, brush
        self.region_points = list(region_points)
        # outside the Regions mode: the land of new regions {(x, y): rgb}, drawn until Apply
        self.new_land = dict(new_land or {})
        # the window's own dict: a stroke shows as soon as it ends
        self.region_painted = region_painted if region_painted is not None else {}
        self.region_colours, self.borders = dict(region_colours or {}), borders
        # ghost = {'kind': 'city'|'port'|'army'|'agent'|'fleet', 'check': fn(xy) -> None or why}:
        # a see-through marker under the mouse while placing
        self.ghost = ghost
        # locked(char) -> why this character cannot be dragged here (shown when one tries)
        self.locked = locked
        self.resources = list(resources or [])
        self.check_res, self.on_res_move, self.on_res_click = check_res, on_res_move, on_res_click
        self.res_sel = res_sel
        self.labels = dict(labels or {})     # {region: name} the town shows for its owner (names by culture)
        self.plain = plain                  # the Terrain editor: the ground alone, no political or region colours
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

    def centre_on(self, xy, zoom=16):
        """Put tile xy in the middle, zoomed in to at least `zoom` pixels a tile, and mark it."""
        if not self.cmap:
            return
        cw, ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        self.z = max(self.z, zoom)
        self.ox = xy[0] + 0.5 - cw / 2 / self.z
        self.oy = (self.cmap.h - 1 - xy[1]) + 0.5 - ch / 2 / self.z
        self.render()
        self._flash = xy
        self.after(60, self._mark_flash)

    def _mark_flash(self):
        xy = getattr(self, "_flash", None)
        if not xy or not self.cmap:
            return
        self.canvas.delete("flash")
        sx, sy = self.to_screen(*xy)
        r = max(self.z, 8)
        self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, outline="#ffd400", width=3, tags=("flash",))
        self.after(1500, lambda: self.canvas.delete("flash"))

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
        self._hot = None
        if not self.cmap:
            c.create_text(20, 20, anchor="nw", fill="#ccc", text="Load a mod: the campaign map shows here.")
            return
        self._clamp()
        cw, ch = c.winfo_width(), c.winfo_height()
        vw, vh = cw / self.z, ch / self.z
        box = (self.ox, self.oy, self.ox + vw, self.oy + vh)
        base = self._base()                                           # 2 px per tile, colours laid on once
        # while the map is dragged the quick resize, the smooth one when it stops; sharp tiles up close
        quick = self._drag is not None and self._drag[4]
        pic = base.crop(tuple(int(round(v * 2)) for v in box)).resize(
            (cw, ch), Image.NEAREST if quick or self.z >= 12 else Image.BILINEAR)
        self._photo = ImageTk.PhotoImage(pic)
        c.create_image(0, 0, anchor="nw", image=self._photo, tags=("bg",))
        self._drawn_at = (self.ox, self.oy)
        if self.v_grid.get() and self.z >= 10:
            self._grid(cw, ch)
        self._markers(cw, ch)
        key = (tuple(sorted({r["kind"] for r in self.resources})), self.v_res.get())
        if key != getattr(self, "_legend_key", None):
            self._legend_key = key
            self._draw_legend()

    def _pan(self):
        """While the map is dragged: a new background, the markers only shifted (drawing
        a couple of thousand of them again is the slow part); all is redrawn on release."""
        self._pending = None
        c = self.canvas
        if not self.cmap or not c.find_withtag("bg"):
            return self._render()
        self._clamp()
        cw, ch = c.winfo_width(), c.winfo_height()
        box = (self.ox, self.oy, self.ox + cw / self.z, self.oy + ch / self.z)
        pic = self._base().crop(tuple(int(round(v * 2)) for v in box)).resize((cw, ch), Image.NEAREST)
        self._photo = ImageTk.PhotoImage(pic)
        c.itemconfigure("bg", image=self._photo)
        ox, oy = self._drawn_at
        dx, dy = (ox - self.ox) * self.z, (oy - self.oy) * self.z
        c.move("all", dx, dy)
        c.move("bg", -dx, -dy)
        self._drawn_at = (self.ox, self.oy)

    def _base(self):
        """The background with the political colours laid on, at 2 px per tile,
        made again only when the colours change - moving the map only crops it."""
        bg = self.cmap.background(self.v_tiles.get(), self.v_relief.get(), self.v_rivers.get())
        if getattr(self, "plain", False):
            return bg
        land = () if self.region_mode else tuple(sorted(self.new_land.items()))
        if self.region_mode:
            pol = self.cmap.regions_layer(self.region_painted, self.region_colours, borders=self.v_borders.get())
        elif not self.v_pol.get() and not self.v_borders.get() and not land:
            return bg
        elif not self.v_pol.get() and not self.v_borders.get():
            pol = Image.new("RGBA", (self.cmap.w, self.cmap.h), (0, 0, 0, 0))
        else:
            if self.v_pol.get():
                pol = self.cmap.political(self.owners, self.colours, self.faction, borders=self.v_borders.get(),
                                          painted=self.region_painted)
            else:                                   # the borders alone
                pol = self.cmap.political(self.owners, self.colours, None, alpha=0, borders=True,
                                          painted=self.region_painted)
        key = (id(bg), id(pol), land)
        if getattr(self, "_base_key", None) != key:
            if land:                                    # a new region's land, in its colour, until Apply
                pol = pol.copy()
                px = pol.load()
                for (x, y), rgb in land:
                    if 0 <= x < pol.width and 0 <= y < pol.height:
                        px[x, pol.height - 1 - y] = tuple(rgb) + (215,)
            over = pol.resize((pol.width * 2, pol.height * 2), Image.NEAREST)
            if over.size != bg.size:
                over = over.resize(bg.size, Image.NEAREST)
            self._base_img = Image.alpha_composite(bg.convert("RGBA"), over).convert("RGB")
            self._base_key = key
        return self._base_img

    def _grid(self, cw, ch):
        """Thin lines between the tiles up close: what is placed or painted is one square."""
        c, z = self.canvas, self.z
        col = "#000000"
        x0 = int(self.ox) - 1
        while (x0 - self.ox) * z < cw:
            sx = (x0 - self.ox) * z
            if sx >= 0:
                c.create_line(sx, 0, sx, ch, fill=col, stipple="gray50", tags=("grid",))
            x0 += 1
        y0 = int(self.oy) - 1
        while (y0 - self.oy) * z < ch:
            sy = (y0 - self.oy) * z
            if sy >= 0:
                c.create_line(0, sy, cw, sy, fill=col, stipple="gray50", tags=("grid",))
            y0 += 1

    def _painted(self, cw, ch):
        """Tiles given to another region, in that region's colour, and the new towns and ports."""
        c, z = self.canvas, self.z                      # painted tiles are in the regions layer itself
        size = max(4, min(z * 0.9, 60))
        for (x, y), what, rgb in self.region_points:
            sx, sy = self.to_screen(x, y)
            r = size / 2
            if what == "city":
                c.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill="#%02x%02x%02x" % rgb, outline="#ffd400",
                                   width=3)
                if r >= 6:
                    self._hall(sx, sy, r, rgb, ("newtown",))
            else:
                c.create_oval(sx - r * 0.9, sy - r * 0.9, sx + r * 0.9, sy + r * 0.9, fill="#2a6fdb", outline="#ffd400",
                              width=3)
                if r >= 5:
                    self._anchor(sx, sy, r * 0.9, ("newport",))

    def _paint_at(self, e):
        x, y = self.to_tile(e.x, e.y)
        b = self.brush - 1
        tiles = [(x + dx, y + dy) for dx in range(-b, b + 1) for dy in range(-b, b + 1)]
        took = self.on_paint(tiles) if self.on_paint else []
        z, c = self.z, self.canvas
        for (tx, ty), rgb in took:
            self.paint_overlay[(tx, ty)] = rgb
            sx, sy = self.to_screen(tx, ty)
            c.create_rectangle(sx - z / 2, sy - z / 2, sx + z / 2, sy + z / 2, fill="#%02x%02x%02x" % rgb,
                               outline="", stipple="gray50", tags=("paint",))     # until the stroke ends

    def _markers(self, cw, ch):
        c, cm = self.canvas, self.cmap
        if self.region_mode or self.region_points:       # new towns and ports show until Apply
            self._painted(cw, ch)
        size = max(3, min(self.z * 0.9, 60))           # a town fills its tile
        font = ("", 8 if self.z < 10 else 9)
        if self.v_ports.get() and self.z >= 4:        # far out: towns only - less to draw, less clutter
            for region, (x, y) in cm.ports.items():
                x, y = self.places.get(("port", region), (x, y))
                sx, sy = self.to_screen(x, y)
                if -10 < sx < cw + 10 and -10 < sy < ch + 10:
                    r = size * 0.45
                    tags = ("port", "port:" + region)
                    c.create_oval(sx - r, sy - r, sx + r, sy + r, fill="#2a6fdb", outline="white", width=1, tags=tags)
                    if r >= 5:
                        self._anchor(sx, sy, r, tags)
        if self.v_res.get():
            self._resources(cw, ch)
        for region, (x, y) in cm.cities.items():
            x, y = self.places.get(("city", region), (x, y))
            sx, sy = self.to_screen(x, y)
            if not (-40 < sx < cw + 40 and -20 < sy < ch + 20):
                continue
            owner = self.owners.get(region)
            rgb = REBELS if owner in (None, "slave") else self.colours.get(owner, REBELS)
            mine = region in self.chosen
            r = size / 2 + (2 if mine else 0)
            c.create_rectangle(sx - r, sy - r, sx + r, sy + r,
                               fill="" if owner is None else "#%02x%02x%02x" % rgb,    # hollow: no town at the start
                               outline="#ffd400" if mine else "black", width=3 if mine else 1,
                               tags=("city", "city:" + region))
            if r >= 6:
                self._hall(sx, sy, size / 2, rgb, ("city", "city:" + region))
            if self.v_names.get() and (self.z >= 4 or mine):
                name = self.labels.get(region) or cm.info.get(region, {}).get("settlement", region)
                c.create_text(sx + r + 3, sy + 1, text=name, anchor="w", fill="black", font=font)   # shadow
                c.create_text(sx + r + 2, sy, text=name, anchor="w", fill="white", font=font)
        if self.v_chars.get() and self.z >= 4 and not self.region_mode:
            self._characters(cw, ch, size)

    def _anchor(self, sx, sy, r, tags):
        """An anchor inside the port's circle: ring, shank, stock and flukes."""
        c, w = self.canvas, max(1, int(r / 6))
        k = r * 0.14
        c.create_oval(sx - k, sy - r * 0.72 - k, sx + k, sy - r * 0.72 + k, outline="white", width=w, tags=tags)
        c.create_line(sx, sy - r * 0.58, sx, sy + r * 0.62, fill="white", width=w, tags=tags)
        c.create_line(sx - r * 0.35, sy - r * 0.35, sx + r * 0.35, sy - r * 0.35, fill="white", width=w, tags=tags)
        a = r * 0.5                                   # the flukes: an arc that stays inside the circle
        c.create_arc(sx - a, sy + r * 0.12 - a, sx + a, sy + r * 0.12 + a, start=200, extent=140,
                     style="arc", outline="white", width=w, tags=tags)

    def _hall(self, sx, sy, r, rgb, tags):
        """A town hall inside the town's square: roof, three columns, steps -
        light on a dark owner colour, dark on a light one."""
        c = self.canvas
        ink = "#202020" if sum(rgb) > 420 else "#f4f0e0"
        # roof (pediment) and the beam under it
        c.create_polygon(sx - r * 0.8, sy - r * 0.38, sx, sy - r * 0.82, sx + r * 0.8, sy - r * 0.38,
                         fill=ink, outline="", tags=tags)
        c.create_rectangle(sx - r * 0.72, sy - r * 0.34, sx + r * 0.72, sy - r * 0.24, fill=ink, outline="", tags=tags)
        for cx in (-0.48, 0, 0.48):                   # three columns
            c.create_rectangle(sx + r * (cx - 0.1), sy - r * 0.2, sx + r * (cx + 0.1), sy + r * 0.42,
                               fill=ink, outline="", tags=tags)
        c.create_rectangle(sx - r * 0.72, sy + r * 0.46, sx + r * 0.72, sy + r * 0.58, fill=ink, outline="", tags=tags)
        c.create_rectangle(sx - r * 0.84, sy + r * 0.62, sx + r * 0.84, sy + r * 0.76, fill=ink, outline="", tags=tags)

    # ---- characters ----
    AGENT_LETTER = {"spy": "S", "diplomat": "D", "assassin": "A", "merchant": "M", "priest": "P",
                    "princess": "Q", "inquisitor": "I", "heretic": "H", "witch": "W"}

    def _glyph(self, k, sx, sy, r, tags):
        """A white sign for an agent kind inside its disc (r = the disc's radius)."""
        c, ink = self.canvas, "white"
        w = max(1, int(r / 4))
        if k == "spy":                                  # an eye
            c.create_oval(sx - r * 0.7, sy - r * 0.38, sx + r * 0.7, sy + r * 0.38, outline=ink, width=w, tags=tags)
            c.create_oval(sx - r * 0.2, sy - r * 0.2, sx + r * 0.2, sy + r * 0.2, fill=ink, outline="", tags=tags)
        elif k == "assassin":                           # a slanted dagger: blade, guard, grip
            c.create_polygon(sx + r * 0.7, sy - r * 0.7, sx + r * 0.05, sy + r * 0.2, sx - r * 0.2, sy - r * 0.05,
                             fill=ink, outline="", tags=tags)
            c.create_line(sx - r * 0.35, sy - r * 0.05, sx + r * 0.1, sy + r * 0.4, fill=ink, width=w, tags=tags)
            c.create_line(sx - r * 0.1, sy + r * 0.15, sx - r * 0.55, sy + r * 0.6, fill=ink, width=w + 1, tags=tags)
        elif k == "diplomat":                           # a scroll
            c.create_rectangle(sx - r * 0.5, sy - r * 0.6, sx + r * 0.5, sy + r * 0.6, outline=ink, width=w, tags=tags)
            for dy in (-0.25, 0.05, 0.35):
                c.create_line(sx - r * 0.3, sy + r * dy, sx + r * 0.3, sy + r * dy, fill=ink, tags=tags)
        elif k == "merchant":                           # a stack of coins
            for dy in (0.35, 0.0, -0.35):
                c.create_oval(sx - r * 0.55, sy + r * (dy - 0.18), sx + r * 0.55, sy + r * (dy + 0.18),
                              fill=ink, outline="black", tags=tags)
        elif k == "priest":                             # an open book (no faith's own sign: imams are priests too)
            c.create_polygon(sx - r * 0.7, sy - r * 0.4, sx, sy - r * 0.25, sx, sy + r * 0.55, sx - r * 0.7,
                             sy + r * 0.4, fill=ink, outline="", tags=tags)
            c.create_polygon(sx + r * 0.7, sy - r * 0.4, sx, sy - r * 0.25, sx, sy + r * 0.55, sx + r * 0.7,
                             sy + r * 0.4, fill=ink, outline="", tags=tags)
            c.create_line(sx, sy - r * 0.25, sx, sy + r * 0.55, fill=self._fill_of_disc, width=max(1, w - 1),
                          tags=tags)
        elif k == "princess":                           # a crown
            c.create_polygon(sx - r * 0.6, sy + r * 0.4, sx - r * 0.6, sy - r * 0.35, sx - r * 0.3, sy,
                             sx, sy - r * 0.5, sx + r * 0.3, sy, sx + r * 0.6, sy - r * 0.35, sx + r * 0.6, sy + r * 0.4,
                             fill=ink, outline="", tags=tags)
        elif k == "inquisitor":                         # scales: judgement
            c.create_line(sx, sy - r * 0.6, sx, sy + r * 0.5, fill=ink, width=w, tags=tags)
            c.create_line(sx - r * 0.6, sy - r * 0.35, sx + r * 0.6, sy - r * 0.35, fill=ink, width=w, tags=tags)
            for dx in (-0.45, 0.45):
                c.create_polygon(sx + r * (dx - 0.25), sy + r * 0.05, sx + r * (dx + 0.25), sy + r * 0.05,
                                 sx + r * dx, sy + r * 0.3, fill=ink, outline="", tags=tags)
            c.create_line(sx - r * 0.3, sy + r * 0.55, sx + r * 0.3, sy + r * 0.55, fill=ink, width=w, tags=tags)
        elif k == "witch":                              # a pointed hat
            c.create_polygon(sx - r * 0.2, sy + r * 0.25, sx + r * 0.1, sy - r * 0.75, sx + r * 0.25, sy + r * 0.25,
                             fill=ink, outline="", tags=tags)
            c.create_oval(sx - r * 0.7, sy + r * 0.15, sx + r * 0.7, sy + r * 0.45, fill=ink, outline="", tags=tags)
        elif k == "heretic":                            # a book torn in two
            c.create_polygon(sx - r * 0.75, sy - r * 0.35, sx - r * 0.1, sy - r * 0.2, sx - r * 0.2, sy + r * 0.55,
                             sx - r * 0.75, sy + r * 0.4, fill=ink, outline="", tags=tags)
            c.create_polygon(sx + r * 0.75, sy - r * 0.45, sx + r * 0.15, sy - r * 0.3, sx + r * 0.05, sy + r * 0.45,
                             sx + r * 0.75, sy + r * 0.3, fill=ink, outline="", tags=tags)
        else:
            c.create_text(sx, sy, text=self.AGENT_LETTER.get(k, k[:1].upper()), fill=ink,
                          font=("", max(6, int(r)), "bold"), tags=tags)

    def _characters(self, cw, ch, size):
        c, cm = self.canvas, self.cmap
        busy = {self.places.get(("city", r), xy) for r, xy in cm.cities.items()} | \
            {self.places.get(("port", r), xy) for r, xy in cm.ports.items()}
        tile = max(self.z * 0.9, 6)                    # a character fills its tile...
        seen = {}
        for ch_ in sorted(self.chars, key=lambda c: not c["army"]):     # the garrison first
            x, y = ch_["xy"]
            sx, sy = self.to_screen(x, y)
            if not (-30 < sx < cw + 30 and -30 < sy < ch + 30):
                continue
            n = seen.get((x, y), 0)
            seen[(x, y)] = n + 1
            one = tile
            if (x, y) in busy:                         # ...or stands small beside the town / port, to its
                one = max(tile * 0.6, 6)               # left (the name is on the right), in a row
                sx = sx - tile * 0.5 - one * 0.45 - n * one * 0.75
            else:
                sx += n * one * 0.5
            self._draw_char(ch_, sx, sy, one)

    def _draw_char(self, ch_, sx, sy, size):
        c = self.canvas
        rgb = REBELS if ch_["faction"] == "slave" else self.colours.get(ch_["faction"], REBELS)
        fill = "#%02x%02x%02x" % rgb
        mine = ch_["id"] in self.draggable
        edge = "#ffd400" if mine else "black"
        tags = ("char", "char:%s" % ch_["id"])
        k = ch_["kind"]
        if k not in ("admiral", "general", "named character"):          # an agent: a disc with its sign
            r = max(size * 0.5, 5)
            c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=fill, outline=edge, width=2 if mine else 1, tags=tags)
            if size >= 8:
                self._fill_of_disc = fill
                self._glyph(k, sx, sy, r, tags)
        elif k == "admiral":
            w = size * 0.5
            c.create_polygon(sx - w, sy - w * 0.1, sx + w, sy - w * 0.1, sx + w * 0.6, sy + w * 0.5,
                             sx - w * 0.6, sy + w * 0.5, fill=fill, outline=edge, width=2 if mine else 1, tags=tags)
            c.create_line(sx, sy - w * 0.1, sx, sy - w, fill=edge, width=2, tags=tags)
        elif ch_["army"]:
            h = size
            sx -= h * 0.3                                  # the flag, not its pole, sits on the tile
            c.create_line(sx, sy + h * 0.5, sx, sy - h * 0.5, fill="black", width=2, tags=tags)
            c.create_polygon(sx, sy - h * 0.5, sx + h * 0.7, sy - h * 0.25, sx, sy,
                             fill=fill, outline=edge, width=2 if mine else 1, tags=tags)
            if mine:
                c.create_rectangle(sx - 2, sy + h * 0.5 - 2, sx + 2, sy + h * 0.5 + 2, fill="#ffd400", outline="",
                                   tags=tags)
        else:                                          # a named character without an army
            r = size * 0.4
            c.create_polygon(sx, sy - r, sx + r, sy, sx, sy + r, sx - r, sy, fill=fill, outline=edge, tags=tags)

    def _symbol(self, faction, px):
        path = self.symbols.get(faction)
        if not path:
            return None
        key = (faction, px)
        if key not in self._symimg:
            try:
                im = Image.open(path).convert("RGBA")
                im.thumbnail((px, px))
                self._symimg[key] = ImageTk.PhotoImage(im)
            except Exception:
                self._symimg[key] = None
        return self._symimg[key]

    # ---- resources ----
    RES_COLOURS = {"gold": "#f2c200", "silver": "#c8ccd4", "iron": "#5a5f66", "copper": "#c8743a", "tin": "#9aa3a8",
                   "lead": "#6f7488", "marble": "#f4f1ea", "wine": "#8a1f5a", "olive_oil": "#9aa832",
                   "grain": "#e6c56a", "timber": "#7a4b21", "furs": "#9b6a44", "hides": "#b3875a",
                   "slaves": "#7a1010", "pottery": "#d0612e", "glass": "#7fd6e0", "purple_dye": "#7a2ea0",
                   "dogs": "#6b5337", "elephants": "#8f8f8f", "camels": "#d9b47a", "incense": "#e8a0c0",
                   "silk": "#e04a86", "spices": "#e0621c", "textiles": "#4a78d0", "amber": "#ffa31a",
                   "wild_animals": "#4e8a3a", "fish": "#3a8fd0", "salt": "#ffffff", "coal": "#222222",
                   "sugar": "#f5f5dc", "sulfur": "#e8e04a", "tobacco": "#6b8e23", "chocolate": "#5c3317"}

    @staticmethod
    def res_colour(kind):
        """A steady colour per resource type: a fitting one for the common types,
        else one made from the name (the same type, the same colour)."""
        if kind in MapView.RES_COLOURS:
            return MapView.RES_COLOURS[kind]
        import colorsys
        h = (sum(ord(ch) * (i + 7) for i, ch in enumerate(kind)) % 360) / 360.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.85)
        return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

    def _resources(self, cw, ch):
        """A small square in the type's colour with its first two letters; on a town's
        tile it sits in the tile's corner. Far out only a dot."""
        c = self.canvas
        towns = {self.places.get(("city", r), xy) for r, xy in self.cmap.cities.items()}
        for res in self.resources:
            x, y = res["xy"]
            sx, sy = self.to_screen(x, y)
            if not (-20 < sx < cw + 20 and -20 < sy < ch + 20):
                continue
            tags = ("res", "res:%s" % res["id"])
            fill = self.res_colour(res["kind"])
            sel = res["id"] == self.res_sel
            if self.z < 6:
                r = max(2, self.z * 0.35)
                c.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill=fill, outline="#ffd400" if sel else "",
                                   tags=tags)
                continue
            r = min(self.z * 0.42, 14)
            if (x, y) in towns:                        # beside the town, at the tile's corner
                sx, sy = sx + self.z * 0.35, sy - self.z * 0.35
                r *= 0.6
            c.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill=fill,
                               outline="#ffd400" if sel else "black", width=3 if sel else 1, tags=tags)
            if r >= 5:
                dark = self.res_colour(res["kind"]) in ("#5a5f66", "#6f7488", "#7a1010", "#7a4b21", "#222222",
                                                        "#8a1f5a", "#7a2ea0", "#6b5337", "#5c3317")
                c.create_text(sx, sy, text=res["kind"][:2].capitalize(), fill="white" if dark else "black",
                              font=("", max(6, int(r * 0.8)), "bold"), tags=tags)

    def _res_under(self, sx, sy):
        if not self.v_res.get():
            return None
        for item in reversed(self.canvas.find_overlapping(sx - 2, sy - 2, sx + 2, sy + 2)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("res:"):
                    return tag[4:]
        return None

    def _char_under(self, sx, sy):
        for item in reversed(self.canvas.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("char:"):
                    return tag[5:]
        return None

    def _marker_under(self, sx, sy):
        """The tag of the town or character under the mouse: 'char:<id>' or 'city:<region>'."""
        for item in reversed(self.canvas.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)):
            for tag in self.canvas.gettags(item):
                if tag.startswith(("char:", "city:")):
                    return tag
        return None

    GROW = 1.6

    def _ghost(self, sx, sy):
        """What is being placed, under the mouse: green frame where it may go, red where not."""
        c = self.canvas
        c.delete("ghost")
        g = self.ghost
        if not g or not self.cmap:
            return
        xy = self.to_tile(sx, sy)
        why = g["check"](xy) if g.get("check") else None
        cx, cy = self.to_screen(*xy)
        size = max(8, min(self.z * 0.9, 60))
        r = size / 2
        edge = "#ff3030" if why else "#30ff60"
        tags = ("ghost",)
        kind = g.get("kind")
        if kind == "city":
            c.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill="#d8c080", stipple="gray50", outline=edge,
                               width=2, tags=tags)
            if r >= 6:
                self._hall(cx, cy, r, (216, 192, 128), tags)
        elif kind == "port":
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#2a6fdb", stipple="gray50", outline=edge, width=2,
                          tags=tags)
            if r >= 5:
                self._anchor(cx, cy, r, tags)
        elif kind in ("army", "fleet"):
            h = size
            c.create_line(cx - h * 0.3, cy + h * 0.5, cx - h * 0.3, cy - h * 0.5, fill=edge, width=2, tags=tags)
            c.create_polygon(cx - h * 0.3, cy - h * 0.5, cx + h * 0.4, cy - h * 0.25, cx - h * 0.3, cy,
                             fill=edge, stipple="gray50", outline=edge, tags=tags)
        else:
            c.create_oval(cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6, fill=edge, stipple="gray50",
                          outline=edge, width=2, tags=tags)
        if why:
            c.create_text(cx + r + 4, cy, text=why, anchor="w", fill="#ff5050", font=("", 9, "bold"), tags=tags)

    def _outline(self, sx, sy):
        """The edges of the tile under the mouse, like a block outline in Minecraft."""
        c = self.canvas
        c.delete("tile_outline")
        if not self.cmap or self.z < 3:
            return
        x, y = self.to_tile(sx, sy)
        cx, cy = self.to_screen(x, y)
        h = self.z / 2
        c.create_rectangle(cx - h, cy - h, cx + h, cy + h, outline="white", width=2 if self.z >= 12 else 1,
                           tags="tile_outline")
        c.tag_lower("tile_outline", "city") if c.find_withtag("city") else None

    def _grow(self, tag):
        """Draw the marker under the mouse bigger (and on top); put the last one back."""
        if tag == self._hot:
            return
        c = self.canvas
        if self._hot:
            box = c.bbox(self._hot)
            if box:
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                c.scale(self._hot, cx, cy, 1 / self.GROW, 1 / self.GROW)
        self._hot = tag
        if tag:
            box = c.bbox(tag)
            if box:
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                c.scale(tag, cx, cy, self.GROW, self.GROW)
                c.tag_raise(tag)

    # ---- mouse ----
    def _wheel(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        self.zoom_by(d, (e.x, e.y))

    def _place_under(self, sx, sy):
        """('city' | 'port', region) of the town or port under the mouse, or None."""
        for item in reversed(self.canvas.find_overlapping(sx - 2, sy - 2, sx + 2, sy + 2)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("char:"):
                    return None
                if tag.startswith(("city:", "port:")):
                    return tag[:4], tag[5:]
        return None

    def _press(self, e, icons=False):
        if self.region_mode and self.cmap:
            if not icons and not self.on_place:           # left: paint
                if getattr(self, "on_stroke", None):
                    self.on_stroke()                      # one Undo step per stroke
                self._painting = True
                self._paint_at(e)
                return
            if icons:                                     # right: drag the map, or a click picks the region
                self._rclick = True
                self._drag = (e.x, e.y, self.ox, self.oy, False)
                return
        if icons and self.cmap and self.on_res_move:
            rid = self._res_under(e.x, e.y)
            if rid is not None:
                self._rdrag = [rid, e.x, e.y, False]
                return
        if not icons and self.cmap:
            self._rpress = self._res_under(e.x, e.y)      # a click (no drag) on a resource picks it
        if icons:
            cid = self._char_under(e.x, e.y) if self.cmap else None
            if cid is not None and cid in self.draggable:
                self._cdrag = (cid, e.x, e.y)
                return
            if cid is not None and self.locked:
                ch_ = next((c for c in self.chars if c["id"] == cid), None)
                if ch_:
                    self.readout.configure(text=self.locked(ch_))
                return
            pl = self._place_under(e.x, e.y) if self.cmap and self.on_place_move and not self.on_place else None
            if pl:
                self._pdrag = [pl[0], pl[1], e.x, e.y, False]      # nothing happens unless the mouse moves
            return
        self._drag = (e.x, e.y, self.ox, self.oy, False)

    def _move(self, e):
        if self._painting:
            self._paint_at(e)
            return
        if self._rdrag:
            rid, lx, ly, started = self._rdrag
            if not started and abs(e.x - lx) + abs(e.y - ly) <= 3:
                return
            self.canvas.move("res:" + rid, e.x - lx, e.y - ly)
            self._rdrag = [rid, e.x, e.y, True]
            x, y = self.to_tile(e.x, e.y)
            why = self.check_res(rid, (x, y)) if self.check_res else None
            self.canvas.delete("target")
            ax, ay = self.to_screen(x, y)
            r = max(self.z / 2, 4)
            self.canvas.create_rectangle(ax - r, ay - r, ax + r, ay + r, outline="#ff3030" if why else "#30ff60",
                                         width=2, tags=("target",))
            self.readout.configure(text="resource to tile %d, %d: %s" % (x, y, why or "fine - drop it here"))
            return
        if getattr(self, "_pdrag", None):
            what, region, lx, ly, started = self._pdrag
            if not started and abs(e.x - lx) + abs(e.y - ly) <= 3:
                return
            self._grow(None)
            self.canvas.move("%s:%s" % (what, region), e.x - lx, e.y - ly)
            self._pdrag = [what, region, e.x, e.y, True]
            x, y = self.to_tile(e.x, e.y)
            why = self.check_place(what, region, (x, y)) if self.check_place else None
            self.canvas.delete("target")
            ax, ay = self.to_screen(x, y)
            r = max(self.z / 2, 4)
            self.canvas.create_rectangle(ax - r, ay - r, ax + r, ay + r, outline="#ff3030" if why else "#30ff60",
                                         width=2, tags=("target",))
            self.readout.configure(text=("%s of %s to tile %d, %d: " % ("town" if what == "city" else "port",
                                   region, x, y)) + (why or "fine - drop it here"))
            return
        if self._cdrag:
            cid, lx, ly = self._cdrag
            self.canvas.move("char:" + cid, e.x - lx, e.y - ly)
            self._cdrag = (cid, e.x, e.y)
            x, y = self.to_tile(e.x, e.y)
            why = self.check_tile(cid, (x, y)) if self.check_tile else None
            self.canvas.delete("target")
            ax, ay = self.to_screen(x, y)
            r = max(self.z / 2, 4)
            self.canvas.create_rectangle(ax - r, ay - r, ax + r, ay + r, outline="#ff3030" if why else "#30ff60",
                                         width=2, tags=("target",))
            self.readout.configure(text=("tile %d, %d: " % (x, y)) + (
                why + " - dropped here it goes to the nearest good tile" if why else "fine - drop it here"))
            return
        if not self._drag or not self.cmap:
            return
        x0, y0, ox, oy, _ = self._drag
        if abs(e.x - x0) + abs(e.y - y0) > 3:
            self._drag = (x0, y0, ox, oy, True)
            self.ox, self.oy = ox - (e.x - x0) / self.z, oy - (e.y - y0) / self.z
            if self._pending is None:
                self._pending = self.after(15, self._pan)

    def _release(self, e):
        if self._painting:
            self._painting = False
            self.render()
            return
        if self._rclick:
            self._rclick = False
            moved = self._drag and self._drag[4]
            self._drag = None
            if moved:
                self.render()
            elif self.on_pick:
                self.on_pick(self.to_tile(e.x, e.y))
            return
        if self._rdrag:
            rid, _, _, started = self._rdrag
            self._rdrag = None
            if started:
                xy = self.to_tile(e.x, e.y)
                why = self.check_res(rid, xy) if self.check_res else None
                if why:
                    self.readout.configure(text="not moved - " + why)
                    self.render()
                else:
                    self.on_res_move(rid, xy)
            elif self.on_res_click:
                self.on_res_click(rid)
            return
        rpress, self._rpress = self._rpress, None
        if getattr(self, "_pdrag", None):
            what, region, _, _, started = self._pdrag
            self._pdrag = None
            if started:
                xy = self.to_tile(e.x, e.y)
                why = self.check_place(what, region, xy) if self.check_place else None
                if why:
                    self.readout.configure(text="not moved - " + why)
                    self.render()
                else:
                    self.on_place_move(what, region, xy)
                return
            return
        if self._cdrag:
            cid = self._cdrag[0]
            self._cdrag = None
            xy = self.to_tile(e.x, e.y)
            why = self.check_tile(cid, xy) if self.check_tile else None
            note = None
            if why:
                alt = self.nearest(lambda p: self.check_tile(cid, p), xy)
                if alt is None:
                    self.readout.configure(text="not moved - " + why)
                    self.render()
                    return
                note = "tile %d, %d: %s - put on the nearest good tile %d, %d" % (xy[0], xy[1], why, alt[0], alt[1])
                xy = alt
            if self.on_char_move:
                self.on_char_move(cid, xy)
            self.render()
            if note:
                self.readout.configure(text=note)
            return
        moved = self._drag and self._drag[4]
        self._drag = None
        if moved:
            self.render()                                # the smooth picture once the map stops
        if moved or not self.cmap:
            return
        if rpress is not None and self.on_res_click and not self.on_place:
            self.on_res_click(rpress)
            return
        if self.on_place:
            xy = self.to_tile(e.x, e.y)
            why = self.on_place(xy)
            if why and self.ghost and self.ghost.get("kind") in ("army", "agent", "fleet") and self.ghost.get("check"):
                alt = self.nearest(self.ghost["check"], xy)       # a character: the nearest good tile
                if alt is not None and not self.on_place(alt):
                    self.readout.configure(text="tile %d, %d: %s - placed on the nearest good tile %d, %d" % (
                        xy[0], xy[1], why, alt[0], alt[1]))
                    return
            if why:
                self.readout.configure(text="cannot place here - " + why)
            return
        hit = self.canvas.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        for item in reversed(hit):
            for tag in self.canvas.gettags(item):
                if tag.startswith("city:") and self.on_city:
                    self.on_city(tag[5:])
                    return

    @staticmethod
    def nearest(check, xy, reach=3):
        """The nearest tile to xy (ring by ring, the four sides first) that check() accepts, or None."""
        x, y = xy
        for d in range(1, reach + 1):
            ring = [(dx, dy) for dx in range(-d, d + 1) for dy in range(-d, d + 1) if max(abs(dx), abs(dy)) == d]
            ring.sort(key=lambda t: abs(t[0]) + abs(t[1]))
            for dx, dy in ring:
                p = (x + dx, y + dy)
                if not check(p):
                    return p
        return None

    def _hover(self, e):
        if self.cmap and self.on_place and not self._cdrag:
            self._outline(e.x, e.y)
            self._ghost(e.x, e.y)
            x, y = self.to_tile(e.x, e.y)
            self.canvas.config(cursor="hand2")
            self.readout.configure(text="click to place   " + self.cmap.describe(x, y, self.owners))
            return
        self.canvas.config(cursor="crosshair")
        self.canvas.delete("ghost")
        self._outline(e.x, e.y)
        if self.cmap and not self._cdrag:
            self._grow(self._marker_under(e.x, e.y))
            rid = self._res_under(e.x, e.y)
            res = next((r for r in self.resources if r["id"] == rid), None) if rid else None
            if res:
                x, y = res["xy"]
                self.readout.configure(text="%s at %d, %d - %s   (click: pick it; right drag: move it)" % (
                    res["kind"], x, y, self.cmap.region_at(x, y) or next(
                        (r for r, t in self.cmap.cities.items() if t == (x, y)), "no region")))
                return
            cid = self._char_under(e.x, e.y)
            ch_ = next((c for c in self.chars if c["id"] == cid), None) if cid else None
            if ch_:
                self.readout.configure(text="%s - %s of %s%s%s" % (
                    ch_["name"], ch_["kind"], ch_["faction"],
                    ", %d unit(s)" % ch_["units"] if ch_["army"] else "",
                    "   (drag to move)" if cid in self.draggable else ""))
                return
            x, y = self.to_tile(e.x, e.y)
            text = self.cmap.describe(x, y, self.owners)
            here = [c for c in self.chars if tuple(c["xy"]) == (x, y)]
            if here:                                   # who is in the town: army first, then agents
                here.sort(key=lambda c: not c["army"])
                text += "   in it: " + ", ".join("%s (%s%s)" % (c["name"], c["kind"], ", %d units" % c["units"]
                                                             if c["army"] else "") for c in here)
            self.readout.configure(text=text)
