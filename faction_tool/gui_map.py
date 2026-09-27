"""The Map tab: the campaign map as a full-window minimap - a
terrain picture, the political colours over it on demand, cities and ports.
Wheel zooms at the mouse, dragging pans, clicking a city picks it."""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from .mapdata import REBELS

ZOOMS = (1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)       # screen pixels per tile


class MapView(ttk.Frame):
    def __init__(self, master, status=None, on_layers=None):
        super().__init__(master)
        self.on_layers = on_layers                      # the window redraws when a layer that needs it changes
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
        self.v_chars = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Characters", variable=self.v_chars, command=self.render).pack(side="left", padx=8)
        self.v_dip = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Diplomacy", variable=self.v_dip,
                        command=lambda: self.on_layers() if self.on_layers else self.render()).pack(side="left")
        ttk.Button(bar, text="Fit", width=5, command=self.fit).pack(side="right")
        ttk.Button(bar, text="+", width=3, command=lambda: self.zoom_by(1)).pack(side="right", padx=2)
        ttk.Button(bar, text="-", width=3, command=lambda: self.zoom_by(-1)).pack(side="right")
        ttk.Label(bar, text="wheel: zoom   drag: the map, your characters, towns and ports   click a town: add / remove it",
                  foreground="#666").pack(side="right", padx=12)
        self.canvas = tk.Canvas(self, background="#1d2b3a", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.readout = ttk.Label(self, text="", anchor="w")
        self.readout.pack(fill="x")
        self.z, self.ox, self.oy = 2, 0.0, 0.0           # zoom; top-left corner in top-down tile units
        self._photo = None
        self._pending = None
        self._drag = None
        self._cdrag = None
        self._pdrag = None               # a town or port being dragged
        self.chars, self.draggable, self.symbols = [], set(), {}
        self.on_char_move = self.check_tile = None
        self._symimg = {}
        c = self.canvas
        c.bind("<Configure>", lambda e: self.render())
        c.bind("<MouseWheel>", self._wheel)
        c.bind("<Button-4>", lambda e: self._wheel(e, 1))
        c.bind("<Button-5>", lambda e: self._wheel(e, -1))
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._move)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Motion>", self._hover)
        c.bind("<Leave>", lambda e: (self._grow(None), c.delete("tile_outline")))
        self._hot = None                                # the marker under the mouse, drawn bigger

    # ---- data ----
    def load(self, cmap, owners, colours, faction=None, chosen=(), on_city=None, chars=(), draggable=(),
             on_char_move=None, check_tile=None, symbols=None, on_place=None,
             places=None, check_place=None, on_place_move=None):
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
        self._markers(cw, ch)

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
        bg = self.cmap.background()
        if not self.v_pol.get():
            return bg
        pol = self.cmap.political(self.owners, self.colours, self.faction)
        key = (id(bg), id(pol))
        if getattr(self, "_base_key", None) != key:
            over = pol.resize((pol.width * 2, pol.height * 2), Image.NEAREST)
            if over.size != bg.size:
                over = over.resize(bg.size, Image.NEAREST)
            self._base_img = Image.alpha_composite(bg.convert("RGBA"), over).convert("RGB")
            self._base_key = key
        return self._base_img

    def _markers(self, cw, ch):
        c, cm = self.canvas, self.cmap
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
                name = cm.info.get(region, {}).get("settlement", region)
                c.create_text(sx + r + 3, sy + 1, text=name, anchor="w", fill="black", font=font)   # shadow
                c.create_text(sx + r + 2, sy, text=name, anchor="w", fill="white", font=font)
        if self.v_chars.get() and self.z >= 4:
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
    AGENT_LETTER = {"spy": "S", "diplomat": "D", "assassin": "A", "merchant": "M", "priest": "P"}

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
        if k in self.AGENT_LETTER:
            r = size * 0.45
            c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=fill, outline=edge, width=2 if mine else 1, tags=tags)
            if size >= 8:
                c.create_text(sx, sy, text=self.AGENT_LETTER[k], fill="white", font=("", max(6, int(size * 0.5)), "bold"),
                              tags=tags)
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

    def _press(self, e):
        cid = self._char_under(e.x, e.y) if self.cmap else None
        if cid is not None and cid in self.draggable:
            self._cdrag = (cid, e.x, e.y)
            return
        pl = self._place_under(e.x, e.y) if self.cmap and self.on_place_move and not self.on_place else None
        if pl:
            self._pdrag = [pl[0], pl[1], e.x, e.y, False]      # a click unless the mouse moves
            return
        self._drag = (e.x, e.y, self.ox, self.oy, False)

    def _move(self, e):
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
            self.readout.configure(text=("tile %d, %d: " % (x, y)) + (why or "fine - drop it here"))
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
            if what == "city" and self.on_city:              # a plain click on a town
                self.on_city(region)
            return
        if self._cdrag:
            cid = self._cdrag[0]
            self._cdrag = None
            xy = self.to_tile(e.x, e.y)
            why = self.check_tile(cid, xy) if self.check_tile else None
            if why:
                self.readout.configure(text="not moved - " + why)
            elif self.on_char_move:
                self.on_char_move(cid, xy)
            self.render()
            return
        moved = self._drag and self._drag[4]
        self._drag = None
        if moved:
            self.render()                                # the smooth picture once the map stops
        if moved or not self.cmap:
            return
        if self.on_place:
            why = self.on_place(self.to_tile(e.x, e.y))
            if why:
                self.readout.configure(text="cannot place here - " + why)
            return
        hit = self.canvas.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        for item in reversed(hit):
            for tag in self.canvas.gettags(item):
                if tag.startswith("city:") and self.on_city:
                    self.on_city(tag[5:])
                    return

    def _hover(self, e):
        if self.cmap and self.on_place and not self._cdrag:
            self._outline(e.x, e.y)
            x, y = self.to_tile(e.x, e.y)
            self.canvas.config(cursor="hand2")
            self.readout.configure(text="click to place   " + self.cmap.describe(x, y, self.owners))
            return
        self.canvas.config(cursor="crosshair")
        self._outline(e.x, e.y)
        if self.cmap and not self._cdrag:
            self._grow(self._marker_under(e.x, e.y))
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
