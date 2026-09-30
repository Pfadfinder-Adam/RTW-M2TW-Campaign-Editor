"""The Terrain editor (its own work at the top): paint what each tile of the campaign map is
(map_ground_types.tga), what runs across it (map_features.tga: rivers, fords, sources,
cliffs), its climate (map_climates.tga, the climates of descr_climates.txt) and how high the land is
(map_heights.tga, a spray brush: held longer, it raises / lowers more), on the map drawn tile by tile. Kept here until Apply, written by terrain.apply with
a backup like the unit and building editors (dirty / pending / make_plan / rebind)."""

import hashlib
import tkinter as tk
from tkinter import ttk

from . import terrain as T


class TerrainEditor(ttk.Frame):
    kind = "terrain"

    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        self.mod, self._sig, self.cmap = None, None, None
        self.ground, self.features, self.climate = {}, {}, {}     # painted tiles: {(x, y): colour}
        self.heights = {}               # sprayed map_heights pixels: {(px, py): grey}
        self._hvals = {}                # their running values with fractions (small puffs add up)
        self.base = {}                  # what the files have there: {('ground'|'features'|'climate', xy): colour}
        self.hbase = {}                 # map_heights pixels as the file has them: {(px, py): grey}
        self._undo, self._redo = [], []
        self._last_river = None         # the last river tile of the stroke: the next one joins it side to side
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Paint", font=("", 10, "bold")).pack(side="left")
        self.v_what = tk.StringVar(value="ground")
        for val, text in (("ground", "Ground"), ("features", "Rivers, cliffs, volcanoes..."),
                          ("climate", "Climates"), ("heights", "Heights")):
            ttk.Radiobutton(top, text=text, value=val, variable=self.v_what, command=self.fill_palette).pack(
                side="left", padx=4)
        ttk.Label(top, text="   brush").pack(side="left")
        self.v_brush = tk.IntVar(value=1)
        ttk.Spinbox(top, from_=1, to=12, width=3, textvariable=self.v_brush,
                    command=lambda: setattr(self.view, "brush", self.v_brush.get())).pack(side="left", padx=2)
        ttk.Button(top, text="Undo all changes here", command=self.reset).pack(side="right")
        self.v_grid_here = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Grid", variable=self.v_grid_here, command=self._grid_toggled).pack(
            side="left", padx=(16, 0))
        ttk.Button(top, text="Redo stroke", command=self.redo_stroke).pack(side="right", padx=(0, 4))
        ttk.Button(top, text="Undo stroke", command=self.undo_stroke).pack(side="right", padx=4)
        from .gui_util import first
        first(*[w for w in top.pack_slaves() if w.pack_info().get("side") == "right"][::-1])
        rights = [w for w in top.pack_slaves() if w.pack_info().get("side") == "right"]
        grid = [w for w in top.pack_slaves() if str(w.cget("text") if w.winfo_class() == "TCheckbutton" else "") == "Grid"]
        if grid:                                   # Grid beside the undo buttons, not after the brush controls
            grid[0].pack_configure(side="right", after=rights[-1], padx=(0, 12))
        self.palette = ttk.Frame(self, padding=(0, 4))
        self.palette.pack(fill="x")
        self.v_colour = tk.StringVar()
        self.v_tool = tk.StringVar(value="raise")       # the heights brush
        self.v_strength = tk.IntVar(value=4)
        self.v_level = tk.IntVar(value=40)
        self.hint = ttk.Label(self, foreground="#555", justify="left", wraplength=1200)
        self.hint.pack(fill="x")
        from .gui_map import MapView
        self.view = MapView(self, status=None, on_layers=self.show)
        self.view.pack(fill="both", expand=True)
        self.view.on_stroke = self._stroke
        # the campaign's own switches (regions, resources, the towns legend, political layers) do not
        # belong here: only the ground, its relief and the rivers are drawn
        bar = self.view.winfo_children()[0]
        for w in bar.winfo_children():
            if w.winfo_class() == "TCheckbutton" or w is self.view.lbl_layers:
                w.pack_forget()
            elif w.winfo_class() == "TLabel" and str(w.cget("text")).startswith("wheel"):
                w.configure(text="wheel: zoom   left drag: paint   right click: pick that tile's   right drag: map")
        self.view.legend.pack_forget()
        self.v_grid_here.set(self.view.v_grid.get())
        self.fill_palette()

    def _grid_toggled(self):
        """The lines between the tiles up close, on or off (the same switch as Layers > grid, kept)."""
        from . import settings
        self.view.v_grid.set(self.v_grid_here.get())
        look = dict(settings.get("map_look") or {})
        look["grid"] = self.v_grid_here.get()
        settings.put("map_look", look)
        self.view.render()

    # ---- the editor protocol (like the unit / building / character editors) ----
    def path(self):
        try:
            return self.mod.campaign_file(self.app.v_campaign.get(), "map_ground_types.tga") if self.mod else None
        except Exception:
            return None

    def _signature(self):
        h = hashlib.md5()
        for name in ("map_ground_types.tga", "map_features.tga", "map_climates.tga", "map_heights.tga"):
            try:
                with open(self.mod.campaign_file(self.app.v_campaign.get(), name), "rb") as fh:
                    h.update(fh.read())
            except (OSError, TypeError, AttributeError):
                pass
        return h.hexdigest()

    def dirty(self):
        return bool(self.ground or self.features or self.climate or self.heights)

    def pending(self):
        return len(self.ground) + len(self.features) + len(self.climate) + (1 if self.heights else 0)

    def rebind(self, mod):
        lost = 0
        if self.mod is not None and self.dirty() and mod.data == self.mod.data and self._signature() != self._sig:
            lost = self.pending()
        if lost or self.mod is None or mod.data != self.mod.data or not self.dirty():
            self.ground, self.features, self.climate, self.base = {}, {}, {}, {}
            self.heights, self._hvals, self.hbase = {}, {}, {}
            self._undo, self._redo = [], []
        from .moddata import ModData
        self.mod = ModData(mod.data)                 # its own copy: the pictures are changed in memory
        self._sig = self._signature()
        self.cmap = None
        self.show()
        return lost

    def make_plan(self):
        from .moddata import ModData
        from .plan import Plan
        if not self.dirty():
            raise ValueError("nothing painted in the Terrain editor")
        mod = ModData(self.mod.data)
        plan = Plan(mod, "terrain", "terrain", {})
        T.apply(plan, self.app.v_campaign.get(), self.ground, self.features, self.climate, self.heights)
        broken = T.river_warnings(self._features_now(), self.cmap.w, self.cmap.h, self.cmap.is_sea) \
            if self.features else []
        for x, y, n in broken[:20]:
            plan.warnings.append(("map_features.tga", "the river at %d, %d (%d tile(s)) joins no sea, map edge, river "
                                                      "source or other river by a tile's side - the game will not draw "
                                                      "it: it follows a river side to side and stops where two river "
                                                      "tiles touch only by a corner" % (x, y, n)))
        painted = {t for t, c in self.features.items()} if self.features else set()
        for shape in (T.river_shapes(self._features_now(), painted) if painted else [])[:20]:
            if shape[0] == "square":
                plan.warnings.append(("map_features.tga", "river tiles at %d, %d form a 2 x 2 block - rivers must be "
                                                          "one tile wide (the game cannot draw a block of river)"
                                      % shape[1:]))
            else:
                plan.warnings.append(("map_features.tga", "the river at %d, %d (%d tile(s)) closes into a ring around "
                                                          "land - the modders' guides say a river may split but never "
                                                          "rejoin itself (big mods have a few that load)" % shape[1:]))
        for x, y, n, why in (T.bridge_warnings(self._features_now()) if painted else [])[:20]:
            plan.warnings.append(("map_features.tga", "the land bridge at %d, %d (%d tile(s)): %s" % (x, y, n, why)))
        return plan

    # ---- the map ----
    def show(self):
        if not self.mod:
            return
        from .mapdata import CampaignMap
        camp = self.app.v_campaign.get()
        if self.cmap is None:
            try:
                self.cmap = CampaignMap(self.mod, camp)
            except Exception as e:
                self.hint.configure(text="Cannot draw the map: %s" % e)
                return
            s = self.app.strat
            self.standing = set(self.cmap.cities.values()) | set(self.cmap.ports.values()) | \
                (s.taken_tiles() if s else set())
            self._apply_memory()
        self.cmap.show_climates = self.v_what.get() == "climate"
        self.cmap.show_heights = self.v_what.get() == "heights"
        self.view.brush = self.v_brush.get()
        self.view.load(self.cmap, {}, {}, region_mode=True, on_paint=self.paint, on_pick=self.pick,
                       brush=self.v_brush.get(), plain=True)
        self.view.on_spray = self.spray if self.v_what.get() == "heights" else None

    def _img(self, name):
        return self.mod._optional_map(self.app.v_campaign.get(), name)

    def _set_px(self, img, x, y, colour):
        if img is not None and 0 <= x < img.width and 0 <= y < img.height:
            img.set(x, y, colour)

    def _apply_memory(self):
        """The painted tiles laid into the in-memory pictures the map is drawn from."""
        g, f = self._img("map_ground_types.tga"), self._img("map_features.tga")
        for (px, py), c in T.ground_changes(self.ground).items():
            self._set_px(g, px, py, c)
        cl = self._img("map_climates.tga")
        for (px, py), c in T.ground_changes(self.climate).items():
            self._set_px(cl, px, py, c)
        for (x, y), c in self.features.items():
            self._set_px(f, x, y, c)
        h = self._img("map_heights.tga")
        for (px, py), v in self.heights.items():
            self._set_px(h, px, py, (v, v, v))
        if self.cmap is not None:
            self.cmap.__dict__.pop("_backgrounds", None)
            self.cmap._hpil = None

    def _features_now(self):
        f = self._img("map_features.tga")
        if f is None:
            return {}
        return {(x, y): f.get(x, y) for y in range(f.height) for x in range(f.width) if f.get(x, y) != (0, 0, 0)}

    def _current(self, what, xy):
        if what == "ground":
            return self.cmap.ground_at(*xy)
        if what == "climate":
            return self.cmap.climate_at(*xy)
        f = self._img("map_features.tga")
        return f.get(*xy) if f and 0 <= xy[0] < f.width and 0 <= xy[1] < f.height else None

    def paint(self, tiles):
        what = self.v_what.get()
        colour = tuple(int(v) for v in self.v_colour.get().split(",")) if self.v_colour.get() else None
        if colour is None:
            return []
        store = {"ground": self.ground, "climate": self.climate}.get(what, self.features)
        if what == "features" and colour in T.RIVERY and len(tiles) == 1:
            # a river drawn with the 1-tile brush stays joined side to side: a diagonal step (or a fast
            # drag's jump) gets the tiles between (the game stops a river at a corner-only step)
            last, self._last_river = self._last_river, tuple(tiles[0])
            if last and max(abs(last[0] - tiles[0][0]), abs(last[1] - tiles[0][1])) >= 1:
                tiles = T.river_path(last, tiles[0])
        took, why = [], None
        for t in tiles:
            if self._current(what, t) == colour:
                continue
            why = T.paint_problem(self.cmap, what, t, colour, self.standing) or None
            if why:
                continue
            self.base.setdefault((what, t), self._current(what, t))
            if self.base[(what, t)] == colour:
                store.pop(t, None)
            else:
                store[t] = colour
            if what in ("ground", "climate"):
                img = self._img("map_ground_types.tga" if what == "ground" else "map_climates.tga")
                for (px, py), c in T.ground_changes({t: colour}).items():
                    self._set_px(img, px, py, c)
            else:
                self._set_px(self._img("map_features.tga"), t[0], t[1], colour)
            from .mapdata import GROUND_LOOK, CampaignMap
            took.append((t, GROUND_LOOK.get(colour) if what == "ground" else colour if what == "climate" else
                         CampaignMap.FEATURE_LOOK.get(colour, (0, 0, 0))))
        if took:
            self.cmap.__dict__.pop("_backgrounds", None)
        self.app.status.set(("Terrain: %d tile(s) painted - Preview, then Apply changes." % self.pending()) +
                            ("   (not here: %s)" % why if why else ""))
        self.app._mark_work()
        return took

    def spray(self, px, py):
        """One puff of the heights brush at map_heights pixel (px, py); True when a pixel changed."""
        img = self._img("map_heights.tga")
        if img is None:
            self.app.status.set("This campaign has no map_heights.tga.")
            return False
        tool = self.v_tool.get()
        # the brush in tiles, a tile being 2 pixels of map_heights: size 1 = about one tile across
        radius = max(1.5, 2.0 * self.v_brush.get() - 0.5)
        got = T.height_spray(img, (px, py), radius, tool, max(1, min(10, self.v_strength.get())), self._hvals,
                             level=self.v_level.get())
        for p, v in got.items():
            self.hbase.setdefault(p, img.get(*p)[0])
            self._set_px(img, p[0], p[1], (v, v, v))
            self.cmap.set_height(p[0], p[1], v)
            if self.hbase[p] == v:
                self.heights.pop(p, None)
            else:
                self.heights[p] = v
        if got:
            self.cmap.__dict__.pop("_backgrounds", None)
            self.app.status.set("Terrain: %d pixel(s) of height changed - Preview, then Apply changes."
                                % len(self.heights))
            self.app._mark_work()
        return bool(got)

    def pick(self, xy):
        if self.v_what.get() == "heights":
            hv = self.cmap.height_at(*xy) if self.cmap else None
            if hv is not None:
                self.v_level.set(hv)
                self.v_tool.set("level")
                self.app.status.set("Terrain: height %d picked - 'Level' brings the land towards it." % hv)
            return
        c = self._current(self.v_what.get(), tuple(xy))
        if c is not None:
            self.v_colour.set("%d,%d,%d" % c)

    def _stroke(self):
        self._last_river = None
        self._undo.append(self._state())
        del self._undo[:-100]
        self._redo = []                          # a new stroke drops the strokes undone before it

    def _state(self):
        return dict(self.ground), dict(self.features), dict(self.climate), dict(self.heights)

    def _restore_to(self, ground, features, climate, heights=None):
        # back to the files' colours first, then the kept strokes on top
        g, f = self._img("map_ground_types.tga"), self._img("map_features.tga")
        cl = self._img("map_climates.tga")
        for (what, t), c in self.base.items():
            if c is None:
                continue
            if what in ("ground", "climate"):
                for (px, py), cc in T.ground_changes({t: c}).items():
                    self._set_px(g if what == "ground" else cl, px, py, cc)
            else:
                self._set_px(f, t[0], t[1], c)
        h = self._img("map_heights.tga")
        for (px, py), v in self.hbase.items():
            self._set_px(h, px, py, (v, v, v))
        self.ground, self.features, self.climate = ground, features, climate
        self.heights = dict(heights or {})
        self._hvals = {p: float(v) for p, v in self.heights.items()}
        self._apply_memory()
        self.view.render()
        self.app._mark_work()

    def undo_stroke(self):
        if self._undo:
            self._redo.append(self._state())
            self._restore_to(*self._undo.pop())
            self.app.status.set("Terrain: a stroke undone (%d more back, %d to redo)." % (len(self._undo), len(self._redo)))
        else:
            self.app.status.set("Terrain: nothing to undo.")

    def redo_stroke(self):
        if self._redo:
            self._undo.append(self._state())
            self._restore_to(*self._redo.pop())
            self.app.status.set("Terrain: a stroke redone (%d more to redo)." % len(self._redo))
        else:
            self.app.status.set("Terrain: nothing to redo.")

    # the window's Undo / Redo (bottom bar, Ctrl+Z / Ctrl+Y) while this editor is on show
    undo_step = undo_stroke
    redo_step = redo_stroke

    def reset(self):
        self._undo, self._redo = [], []
        self._restore_to({}, {}, {}, {})
        self.app.status.set("Terrain: nothing painted.")

    def fill_palette(self):
        for w in self.palette.winfo_children():
            w.destroy()
        what = self.v_what.get()
        if what == "ground":
            items = [("land", T.LAND_BRUSHES, T.GROUND), ("sea", T.SEA_BRUSHES, T.GROUND)]
            self.hint.configure(text=(
                "Left drag paints the picked ground, right click picks a tile's own, right drag moves the map. "
                "A tile's ground decides movement, farming and what may stand there; land stays land and sea stays "
                "sea (the coast is the regions and heights too - a later step). Mountains, high mountains and dense "
                "forest are refused under towns, ports and characters (the game refuses them there). "
                "On Apply: map_ground_types.tga written, map.rwm deleted - the game builds its map again."))
        elif what == "climate":
            found = T.climates(self.mod) if self.mod else []
            items = [("climates", [c for _, c, _ in found], {c: n for n, c, _ in found})]
            self.hint.configure(text=(
                "Left drag paints the picked climate, right click picks a tile's own. The climate decides the trees "
                "and plants on the campaign and battle maps, the snow in winter and the heat (tiring in battle). "
                "The climates are the mod's own (descr_climates.txt), drawn here in their colours over the land; "
                "the sea keeps its climate. On Apply: map_climates.tga written, map.rwm deleted." if found else
                "This mod has no descr_climates.txt, so its climates are not known here."))
        elif what == "heights":
            self._heights_palette()
            if self.cmap is not None and not getattr(self.cmap, "show_heights", False):
                self.show()
            return
        else:
            from .limits import game_kind
            m2 = bool(self.mod) and game_kind(self.mod) == "medieval2"
            items = [("marks", T.feature_brushes("medieval2" if m2 else "rome"), T.FEATURES)]
            self.hint.configure(text=(
                "Rivers, fords (the tiles where armies cross a river), river sources, cliffs and volcanoes: one per "
                "tile in map_features.tga. A ford goes on the river's own line; 'nothing' rubs a mark out. The game "
                "follows a river side to side from the sea, a source or another river and stops where two river "
                "tiles touch only by a corner - the 1-tile brush fills such steps itself, and Preview names a river "
                "the game will not draw. Not under towns, ports or characters (the game refuses them there)." +
                (" Land bridge: armies walk across a narrow strait (vanilla has 9, like the Bosporus and the Danish "
                 "islands) - paint a straight strip of 3 tiles: land, sea, land." if m2 else "")))
        from .mapdata import GROUND_LOOK, CampaignMap
        first = None
        swatches = []
        for label, colours, names in items:
            ttk.Label(self.palette, text=label + ":").pack(side="left", padx=(8, 2), anchor="n")
            # a long list (a mod's climates) goes in rows, so every one stays in the window
            box = ttk.Frame(self.palette)
            box.pack(side="left")
            per_row = 6 if len(colours) > 8 else len(colours) or 1
            for i, c in enumerate(colours):
                look = GROUND_LOOK.get(c) if what == "ground" else c if what == "climate" else \
                    CampaignMap.FEATURE_LOOK.get(c, (20, 20, 20))
                hexc = "#%02x%02x%02x" % look
                fg = "white" if sum(look) < 380 else "black"
                b = tk.Radiobutton(box, text=names[c], value="%d,%d,%d" % c, variable=self.v_colour,
                                   indicatoron=0, bg=hexc, fg=fg, selectcolor=hexc, activebackground=hexc,
                                   padx=6, pady=3, relief="raised", offrelief="flat", bd=3, cursor="hand2")
                b.grid(row=i // per_row, column=i % per_row, padx=1, pady=1, sticky="ew")
                swatches.append(b.cget("value"))
                first = first or "%d,%d,%d" % c
        if first and self.v_colour.get() not in swatches:
            self.v_colour.set(first)
        if self.cmap is not None and (getattr(self.cmap, "show_climates", False) != (what == "climate") or
                                      getattr(self.cmap, "show_heights", False)):
            self.show()

    def _heights_palette(self):
        """The heights brush: what it does, how strong, and the height 'Level' brings the land to."""
        box = ttk.Frame(self.palette)
        box.pack(side="left")
        ttk.Label(box, text="brush:").pack(side="left", padx=(8, 2))
        for val, text in (("raise", "Raise"), ("lower", "Lower"), ("smooth", "Smooth"),
                          ("level", "Level to height")):
            ttk.Radiobutton(box, text=text, value=val, variable=self.v_tool).pack(side="left", padx=3)
        ttk.Spinbox(box, from_=0, to=255, width=4, textvariable=self.v_level).pack(side="left")
        ttk.Label(box, text="   strength").pack(side="left", padx=(12, 2))
        ttk.Scale(box, from_=1, to=10, orient="horizontal", length=140,
                  command=lambda v: self.v_strength.set(int(float(v)))).pack(side="left")
        box.winfo_children()[-1].set(self.v_strength.get())
        self.hint.configure(text=(
            "Like a spray can: hold the left button and the land under the brush rises (or sinks) more the "
            "longer you hold; the middle of the brush does the most, the edge fades out. Smooth evens out bumps, "
            "Level brings the land towards the height set beside it (right click picks a tile's own height). "
            "Shown as map_heights.tga is: land grey - black low, white high (brightened a little here) - "
            "the sea blue; only land is changed, the coast stays. On Apply: map_heights.tga written, "
            "the same points changed in map_heights.hgt (the game's own copy of the heights, read instead of the "
            "picture while it is there), map.rwm deleted (the game builds its map again). Land never goes down to "
            "black: the game may take black for sea."))
