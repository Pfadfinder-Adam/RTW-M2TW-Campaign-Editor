"""The Terrain editor (Maps' Terrain tab, beside its Map): paint what each tile of the campaign map is
(map_ground_types.tga), what runs across it (map_features.tga: rivers, fords, sources,
cliffs), its climate (map_climates.tga, the climates of descr_climates.txt) and how high the land is
(map_heights.tga, a spray brush: held longer, it raises / lowers more), on the map drawn tile by tile. Kept here until Apply, written by terrain.apply with
a backup like the unit and building editors (dirty / pending / make_plan / rebind)."""

import hashlib
import tkinter as tk
from tkinter import ttk

from . import terrain as T, theme

NEAREST = "(the nearest region)"
POINT_BRUSHES = ("pen", "shape", "smooth", "pull", "push")       # the coast brushes that work by map_heights point, not by tile



class _FeatureLookup:
    """map_features read tile by tile where asked ({(x, y): colour}.get), black for an empty tile or off the picture."""

    def __init__(self, img):
        self.img = img

    def get(self, xy, default=None):
        f = self.img
        if f is None or not (0 <= xy[0] < f.width and 0 <= xy[1] < f.height):
            return default
        c = f.get(*xy)
        return default if c == (0, 0, 0) else c

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
        self.coast = {}                 # tiles made land or sea: {(x, y): 'land' | 'sea'}
        self.cpx = {"regions": {}, "ground": {}, "heights": {}, "hgt": {}}   # the pixels those tiles change (hgt: the
        #                                                 shape brush's exact heights for map_heights.hgt)
        self.cbase = {}                 # those pixels as the files have them: {(file, (x, y)): colour}
        self._undo, self._redo = [], []
        self._last_river = None         # the last river tile of the stroke: the next one joins it side to side
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Paint", font=("", 10, "bold")).pack(side="left")
        self.v_what = tk.StringVar(value="ground")
        self.group, self._last_of = "terrain", {}
        self._what_buttons = {}
        for val, text in (("ground", "Ground"), ("features", "Rivers, cliffs, volcanoes..."),
                          ("climate", "Climates"), ("heights", "Heights"), ("coast", "Land and sea")):
            self._what_buttons[val] = ttk.Radiobutton(top, text=text, value=val, variable=self.v_what,
                                                      command=self.fill_palette)
            self._what_buttons[val].pack(side="left", padx=4)
        self._paint_end = ttk.Label(top, text="   brush")       # the Paint radios of the tab on show go before it
        self._paint_end.pack(side="left")
        self.v_brush = tk.IntVar(value=1)
        self.v_brush.trace_add("write", lambda *_: self._brush_changed())     # typed too, not only the arrows
        ttk.Spinbox(top, from_=1, to=24, width=3, textvariable=self.v_brush,
                    command=lambda: setattr(self.view, "brush", self.v_brush.get())).pack(side="left", padx=2)
        ttk.Button(top, text="Undo all changes here", command=self.reset).pack(side="right")
        self.v_grid_here = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Grid", variable=self.v_grid_here, command=self._grid_toggled).pack(
            side="left", padx=(16, 0))
        ttk.Button(top, text="Redo stroke", command=self.redo_stroke).pack(side="right", padx=(0, 4))
        self.v_shore = tk.BooleanVar(value=True)       # the shore as the game draws it (Land and sea's 2nd row)
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
        self.v_coast = tk.StringVar(value="shape_land")    # the land / sea brushes: the shape brush first
        self.v_coast.trace_add("write", lambda *_: self._coast_mode())
        self.v_coast_region = tk.StringVar(value=NEAREST)
        from .gui_util import ShortHint
        self.hint = ShortHint(self)                      # one line; the whole explanation on its '?'
        self.hint.pack(fill="x")
        from .gui_map import MapView
        self.view = MapView(self, status=None, on_layers=self.show)
        self.view.pack(fill="both", expand=True)
        self.view.on_stroke = self._stroke
        # the campaign map's own switches (Layers, Edit regions, Select, Merge regions, Signs and tools, Find) do not
        # belong here - nothing of the map's towns, armies or regions is worked here (the user, 2026-10-09); the
        # zoom stays
        self.view.lbar.pack_forget()
        self.view.legend.pack_forget()
        self.v_grid_here.set(self.view.v_grid.get())
        self.fill_palette()

    GROUPS = {"terrain": ("ground", "features", "climate"), "heights": ("coast", "heights")}

    def set_group(self, group):
        """Terrain (ground, rivers, climates) or Coast & heights (land and sea, heights): only that tab's brushes on
        the Paint row; the one picked last in that tab comes back."""
        if group not in self.GROUPS:
            return
        if self.group != group:
            self._last_of[self.group] = self.v_what.get()
        self.group = group
        mine = self.GROUPS[group]
        for val, b in self._what_buttons.items():
            b.pack_forget()
        for val in mine:
            self._what_buttons[val].pack(side="left", padx=4, before=self._paint_end)
        if self.v_what.get() not in mine:
            self.v_what.set(self._last_of.get(group) or mine[0])
            self.fill_palette()
        if (self.view.shore is not None) != self._shore_wanted() and self.mod is not None:
            self._shore_toggled()                         # the shore line on in Coast & heights, off in Terrain

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
        for name in ("map_ground_types.tga", "map_features.tga", "map_climates.tga", "map_heights.tga",
                     "map_regions.tga"):
            try:
                with open(self.mod.campaign_file(self.app.v_campaign.get(), name), "rb") as fh:
                    h.update(fh.read())
            except (OSError, TypeError, AttributeError):
                pass
        return h.hexdigest()

    def dirty(self):
        return bool(self.ground or self.features or self.climate or self.heights or self.coast or
                    self.cpx["heights"] or self.cpx["ground"] or self.cpx.get("hgt"))

    def pending(self):
        return len(self.ground) + len(self.features) + len(self.climate) + (1 if self.heights else 0) + \
            len(self.coast)

    def rebind(self, mod):
        lost = 0
        if self.mod is not None and self.dirty() and mod.data == self.mod.data and self._signature() != self._sig:
            lost = self.pending()
        if lost or self.mod is None or mod.data != self.mod.data or not self.dirty():
            self.ground, self.features, self.climate, self.base = {}, {}, {}, {}
            self.heights, self._hvals, self.hbase = {}, {}, {}
            self.coast, self.cbase = {}, {}
            self.cpx = {"regions": {}, "ground": {}, "heights": {}, "hgt": {}}
            self._undo, self._redo = [], []
        self._off_said = ""                             # a check's finding belongs to the files it looked at
        self._sc = self._shape_ctx = None
        if getattr(self, "view", None) is not None:
            self.view.point_marks = []
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
        T.apply(plan, self.app.v_campaign.get(), self.ground, self.features, self.climate, self.heights,
                dict(self.cpx, tiles=self.coast) if self.coast or self.cpx["heights"] or self.cpx["ground"] or
                self.cpx.get("hgt") else None)
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
            try:                                       # resources: a coast change never drowns one
                from . import resources as RS
                strat = self.mod.campaign_file(camp, "descr_strat.txt")
                self.standing |= {r.xy for r in RS.read(self.mod.load(strat))}
            except Exception:
                pass
            self._apply_memory()
        self.cmap.show_climates = self.v_what.get() == "climate"
        self.cmap.show_heights = self._by_points()
        self.view.brush = self.v_brush.get()
        self.view.shore = self._shore() if self._shore_wanted() else None
        self.view.load(self.cmap, {}, {}, region_mode=True, on_paint=self.paint, on_pick=self.pick,
                       brush=self.v_brush.get(), plain=True)
        self._spray_hook()

    def _shore(self):
        """(map_heights picture, metres) for the map's shore line (MapView._shore_line)."""
        sc = self._shape_coast()
        return (self._img("map_heights.tga"), sc.metres) if sc is not None else None

    def _shore_wanted(self):
        """The shore line belongs to Coast & heights (its tick on Land and sea's 2nd row): never on the Terrain tab."""
        return self.group == "heights" and self.v_shore.get()

    def _shore_toggled(self):
        self.view.shore = self._shore() if self._shore_wanted() else None
        self.view.render()

    def _by_points(self):
        """The map drawn point by point (map_heights: land grey, water blue, each point centred on its place): the
        heights brush and the coast's point brushes (the shape brush, Smooth the coast, the pen) - the coast runs
        between the tiles, so its points must be seen (the user, 2026-10-09: 'show the map by points')."""
        return self.v_what.get() == "heights" or (self.v_what.get() == "coast" and
                                                  self.v_coast.get().startswith(POINT_BRUSHES))

    def _coast_mode(self):
        """Land / Sea / Smooth / the pen picked: the pen draws by point on the map drawn by point."""
        self._spray_hook()
        if getattr(self, "cmap", None) is not None and self.v_what.get() == "coast" and \
                getattr(self.cmap, "show_heights", False) != self._by_points():
            self.show()

    def _spray_hook(self):
        """The heights brush and the coast pen work point by point (map_heights), the other brushes by tile."""
        if getattr(self, "view", None) is None:
            return
        what, mode = self.v_what.get(), self.v_coast.get()
        self.view.on_spray = self.spray if what == "heights" else None
        # the heights brush's outline: exactly the pixels it takes
        self.view.spray_points = ((lambda px, py, b: T.spray_footprint((px, py), b)[2]) if what == "heights" else None)
        if what == "coast" and mode.startswith("pen"):
            self.view.on_spray = self.pen
        elif what == "coast" and mode.startswith(("shape", "smooth", "pull", "push")):
            self.view.on_spray = self.shape
        # the coast's point brushes follow the mouse at every size, size 1 too: the outline is the circle they work
        smooth = what == "coast" and mode in ("smooth", "pull", "push")      # these work at least a point round
        self.view.spray_radius = ((lambda b: max(1.0 if smooth else 0.5, b - 0.5))
                                  if what == "coast" and self.view.on_spray else None)

    def _brush_changed(self):
        try:
            self.view.brush = max(1, int(self.v_brush.get()))
        except (tk.TclError, ValueError, AttributeError):
            pass

    def _bound(self):
        """True when the editor has the loaded mod's files - after an Apply it starts clean on the new ones (a brush
        stroke then went into nothing: "'NoneType' object has no attribute '_optional_map'", report #141)."""
        if self.mod is None and self.app.mod is not None:
            self.app.open_terrain()
        return self.mod is not None and self.cmap is not None

    def _img(self, name):
        return self.mod._optional_map(self.app.v_campaign.get(), name)

    def _set_px(self, img, x, y, colour):
        if img is not None and 0 <= x < img.width and 0 <= y < img.height:
            img.set(x, y, colour)

    def _apply_memory(self):
        """The painted tiles laid into the in-memory pictures the map is drawn from."""
        g, f = self._img("map_ground_types.tga"), self._img("map_features.tga")
        h = self._img("map_heights.tga")
        for (px, py), c in self.cpx["heights"].items():             # the coast's heights first: the ground
            self._set_px(h, px, py, c)                               # follows them
        for (px, py), c in T.ground_changes(self.ground, T.land_points(h)).items():
            self._set_px(g, px, py, c)
        cl = self._img("map_climates.tga")
        for (px, py), c in T.ground_changes(self.climate).items():
            self._set_px(cl, px, py, c)
        for (x, y), c in self.features.items():
            self._set_px(f, x, y, c)
        for (px, py), c in self.cpx["ground"].items():
            self._set_px(g, px, py, c)
        if self.cpx["regions"]:
            reg = self.mod.region_map(self.app.v_campaign.get())
            for (x, y), c in self.cpx["regions"].items():
                self._set_px(reg, x, y, c)
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
        if not self._bound():
            return []
        what = self.v_what.get()
        if what == "coast":
            return self.paint_coast(tiles)
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
                # a ground stays on its side of the waterline (the heights lead); each point's own colour kept
                # for Undo - the tile's block is not one colour on the coast
                land_at = T.land_points(self._img("map_heights.tga")) if what == "ground" else None
                for (px, py), c in T.ground_changes({t: colour}, land_at).items():
                    if img is not None and 0 <= px < img.width and 0 <= py < img.height:
                        self.cbase.setdefault((what, (px, py)), img.get(px, py))
                        img.set(px, py, c)
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

    def _region_tiles(self):
        """{region: its land tiles now} - counted once, kept up to date by paint_coast."""
        if getattr(self, "_rtiles", None) is None:
            from collections import Counter
            c = Counter()
            for y in range(self.cmap.h):
                for x in range(self.cmap.w):
                    r = self.cmap.region_at(x, y)
                    if r:
                        c[r] += 1
            self._rtiles = c
        return self._rtiles

    def paint_coast(self, tiles, mode=None):
        """The land / sea brush: each tile turned with its regions pixel, the ground and heights round it."""
        mode = mode or self.v_coast.get()
        if mode.startswith(("shape", "smooth")):
            return []                                   # point brushes: shape()
        if mode.startswith("pen") and mode not in ("pen_land", "pen_sea"):
            return []
        if mode in ("pen_land", "pen_sea") and self.v_coast.get() == mode and not getattr(self, "_pen_tiles", False):
            return []                                   # the pen draws by point (pen()), not by the tile brush
        to_land = mode in ("land", "pen_land")
        camp = self.app.v_campaign.get()
        reg_img = self.mod.region_map(camp)
        if not hasattr(self, "_sea"):
            self._sea = T.sea_colour(reg_img, [v["colour"] for v in self.cmap.info.values()])
        heights = self._img("map_heights.tga")
        feats = _FeatureLookup(self._img("map_features.tga"))   # read where asked - a whole-map scan per mouse
        counts = self._region_tiles()                           # move made the brush lag (worse on big maps)
        changed = set()
        took, why = [], None
        from .mapdata import GROUND_LOOK
        for t in tiles:
            t = tuple(t)
            if self.cmap.is_sea(*t) != to_land:                     # already what the brush makes
                continue
            why = T.coast_problem(self.cmap, t, to_land, self.standing, feats, counts, self.cmap.ports) or None
            if why:
                continue
            region = None
            if to_land:
                pick = self.v_coast_region.get()
                region = pick if pick in self.cmap.info else T.nearest_region(self.cmap, t)
                if not region:
                    why = "no region to join near here - pick one in 'new land joins'"
                    continue
            px = T.coast_pixels(self.cmap, t, to_land, self.cmap.info[region]["colour"] if region else None,
                                heights, self._sea)
            old_region = self.cmap.region_at(*t)
            for name, img in (("regions", reg_img), ("ground", self._img("map_ground_types.tga")),
                              ("heights", heights)):
                for p, c in px[name].items():
                    if img is None or not (0 <= p[0] < img.width and 0 <= p[1] < img.height):
                        continue
                    self.cbase.setdefault((name, p), img.get(*p))
                    if self.cbase[(name, p)] == c:
                        self.cpx[name].pop(p, None)
                    else:
                        self.cpx[name][p] = c
                    img.set(p[0], p[1], c)
                    if name == "heights":
                        changed.add(p)
                    if name == "heights" and self.cmap is not None:
                        if c[0] == c[1] == c[2]:
                            self.cmap.set_height(p[0], p[1], c[0])
            if to_land:
                counts[region] += 1
            elif old_region:
                counts[old_region] -= 1
            orig = self.cbase.get(("regions", t))
            if orig == px["regions"][t]:
                self.coast.pop(t, None)
            else:
                self.coast[t] = "land" if to_land else "sea"
            took.append((t, GROUND_LOOK.get(px["ground"][(2 * t[0] + 1, 2 * t[1] + 1)], (0, 0, 0))))
        if took and to_land and heights is not None:      # land made tile by tile: what is inland now rises
            # only the land near this move can be further from the sea now (_from_sea looks 5 pixels out) - all the
            # stroke's pixels each move made it slower the longer it went on
            reach = 6
            near = {(p[0] + a, p[1] + b) for p in changed for a in range(-reach, reach + 1)
                    for b in range(-reach, reach + 1)}
            for p, c in T.shore_rise(heights, [p for p in near if p in self.cpx["heights"]]).items():
                self.cbase.setdefault(("heights", p), heights.get(*p))
                self.cpx["heights"][p] = c
                heights.set(p[0], p[1], c)
                self.cmap.set_height(p[0], p[1], c[0])
        if took and heights is not None and not mode.startswith("pen"):   # the coast on a smooth curve (the pen: by hand)
            ground = self._img("map_ground_types.tga")
            got = T.coast_smoothed(heights, ground, lambda x, y: not self.cmap.is_sea(x, y), [t for t, _ in took])
            for name, img in (("heights", heights), ("ground", ground)):
                for p, c in got[name].items():
                    self.cbase.setdefault((name, p), img.get(*p))
                    if self.cbase[(name, p)] == c:
                        self.cpx[name].pop(p, None)
                    else:
                        self.cpx[name][p] = c
                    img.set(p[0], p[1], c)
                    if name == "heights" and c[0] == c[1] == c[2]:
                        self.cmap.set_height(p[0], p[1], c[0])
        if took:
            self.cmap.__dict__.pop("_backgrounds", None)
            self.cmap._hpil = None
        self.app.status.set(("Terrain: %d tile(s) of land / sea changed - Preview, then Apply changes."
                             % len(self.coast)) + ("   (not here: %s)" % why if why else ""))
        self.app._mark_work()
        return took

    def _coast_points(self, got):
        """Pixels of map_heights / map_ground_types the coast changes, kept as the land brush keeps its own (Undo,
        Preview, Apply)."""
        imgs = {"heights": self._img("map_heights.tga"), "ground": self._img("map_ground_types.tga")}
        for name, img in imgs.items():
            if img is None:
                continue
            for p, c in got.get(name, {}).items():
                self.cbase.setdefault((name, p), img.get(*p))
                if self.cbase[(name, p)] == c:
                    self.cpx[name].pop(p, None)
                else:
                    self.cpx[name][p] = c
                img.set(p[0], p[1], c)
                if name == "heights":
                    self.cmap.set_height(p[0], p[1], c)
        if got.get("heights") or got.get("ground") or got.get("regions"):
            self.cmap.__dict__.pop("_backgrounds", None)
            self.app.status.set("Terrain: %d point(s) of the coast changed - Preview, then Apply changes."
                                % len(set(self.cpx["heights"]) | set(self.cpx["ground"])))
            self.app._mark_work()

    def _say_off(self, text):
        self._off_said = text                       # kept when the palette is drawn again
        if getattr(self, "lbl_off", None) is not None and self.lbl_off.winfo_exists():
            self.lbl_off.configure(text=text)
        self.app.status.set("Terrain: " + text)

    def ground_check(self):
        """'Find ground on the wrong side of the coast' (the user, 2026-10-09: 'textures crawled onto the water though
        the tile is not, and the other way round holes in the land'): every map_ground_types point on the other side
        of the waterline than map_heights says, ringed on the map; on a yes each gets the ground round it on its own
        side - the heights lead (terrain.ground_off_heights / ground_under_heights). Kept with the coast's points:
        Undo stroke, Preview, Apply."""
        if not self._bound():
            return
        heights, ground = self._img("map_heights.tga"), self._img("map_ground_types.tga")
        if heights is None or ground is None:
            self._say_off("this campaign has no map_heights.tga or map_ground_types.tga - nothing to compare.")
            return
        wrong = T.ground_off_heights(heights, ground)
        self.view.mark_points(wrong)
        if not wrong:
            self._say_off("the ground and the heights agree everywhere - no land ground on the water, no sea in the "
                          "land.")
            return
        water = sum(1 for w in wrong if w[2] == "water")
        self._say_off("%d point(s) on the wrong side of the coast, ringed on the map: %d land ground on the water, "
                      "%d sea ground in the land." % (len(wrong), water, len(wrong) - water))
        from .gui_util import ask
        if not ask("Terrain editor", (
                "%d point(s) of map_ground_types.tga lie on the other side of the coast than map_heights.tga says:\n"
                "  - %d land ground on the water (the land's texture shows on the water in the game)\n"
                "  - %d sea ground in the land (holes of sea in the land)\n\n"
                "They are ringed on the map. Put the ground right under the heights? Each point takes the ground "
                "round it on its own side - the sea's on the water, the land's on the land; the heights stay as "
                "they are. Kept until Apply; Undo stroke takes it back." % (len(wrong), water, len(wrong) - water)),
                yes="Put the ground right", no="Only show them", parent=self):
            return
        self._stroke()                                  # one step back with Undo stroke
        self._coast_points({"ground": T.ground_under_heights(heights, ground, wrong)})
        self.view.mark_points(None)
        self._say_off("%d point(s) of the ground put right under the heights - Preview, then Apply changes (Undo "
                      "stroke takes it back)." % len(wrong))
        self.view.render()

    def _shape_coast(self):
        """The coast as a shape over the pictures being painted (terrain.ShapeCoast), kept while they stay the same
        (made again after an Undo, a Load, a new campaign)."""
        if self.mod is None or self.cmap is None:
            return None
        heights = self._img("map_heights.tga")
        if heights is None:
            return None
        exact = self.cpx.setdefault("hgt", {})
        pick = self.v_coast_region.get()
        sc = getattr(self, "_sc", None)
        if sc is not None and sc.heights is heights and sc.exact is exact:
            sc.region = pick if pick in self.cmap.info else None
            return sc
        camp = self.app.v_campaign.get()
        ctx = getattr(self, "_shape_ctx", None)
        if ctx is None or ctx[0] != (self.mod.data, camp):
            import os
            path = self.mod.campaign_file(camp, "map_heights.tga")
            ctx = ((self.mod.data, camp), T.max_land_height(self.mod, camp), T.min_sea_height(self.mod, camp),
                   T.read_hgt(os.path.join(os.path.dirname(path), "map_heights.hgt")) if path else None)
            self._shape_ctx = ctx
        if not hasattr(self, "_sea"):
            self._sea = T.sea_colour(self.mod.region_map(camp), [v["colour"] for v in self.cmap.info.values()])
        self._sc = T.ShapeCoast(heights, self._img("map_ground_types.tga"), self.cmap, self.standing,
                                _FeatureLookup(self._img("map_features.tga")), self._region_tiles(), self._sea,
                                ctx[1], ctx[2], ctx[3], pick if pick in self.cmap.info else None, exact)
        return self._sc

    def shape(self, px, py):
        """The shape brush (land / water) and 'Smooth the coast' at map_heights point (px, py), fractions kept: the
        coast is a shape and the heights near it follow its distance, so the game's shore falls where the brush's
        edge went (terrain.ShapeCoast); the tiles follow by their middles, the ground by its points. True when
        anything changed."""
        if not self._bound():
            return None
        sc = self._shape_coast()
        if sc is None:
            self.app.status.set("This campaign has no map_heights.tga.")
            return False
        mode = self.v_coast.get()
        r = max(0.5, self.v_brush.get() - 0.5)          # in points, 2 a tile: size 1 = half a point round the mouse
        if mode == "smooth":
            got = sc.smooth((px, py), max(1.0, r))
        elif mode == "pull":                            # the coast grabbed where the press began goes with the mouse
            last = getattr(self, "_shape_last", None)
            self._shape_last = (px, py)
            if last is None or last == (px, py):
                return False
            got = sc.pull(last, (px, py), max(1.0, r))
        elif mode == "push":                            # pushed from the side the press began on
            if getattr(self, "_push_land", None) is None:
                m = sc.metres(int(round(px)), int(round(py)))
                self._push_land = m is not None and m > 0
            got = sc.push((px, py), max(1.0, r), self._push_land)
        else:
            last = getattr(self, "_shape_last", None)
            if last == (px, py):
                return False                            # the mouse held still: the same band again changes nothing
            got = sc.stroke(last or (px, py), (px, py), r, mode == "shape_land")
            self._shape_last = (px, py)
        reg = self.mod.region_map(self.app.v_campaign.get())
        for t, c in got["regions"].items():
            self.cbase.setdefault(("regions", t), reg.get(*t))
            if self.cbase[("regions", t)] == c:
                self.cpx["regions"].pop(t, None)
                self.coast.pop(t, None)
            else:
                self.cpx["regions"][t] = c
                self.coast[t] = got["tiles"][t]
            reg.set(t[0], t[1], c)
        self._coast_points(got)
        if got["kept"]:
            self.app.status.set(self.app.status.get() + "   (kept: %s)" % got["kept"][-1])
        return bool(got["heights"] or got["ground"] or got["regions"] or got["hgt"])

    def pen(self, px, py):
        """The coast pen: the map_heights points under it made land (a low shore) or water, as modders draw the coast
        by hand on map_heights; a tile's middle point stays its tile's (change a tile with Land / Sea)."""
        heights = self._img("map_heights.tga")
        if heights is None or not self._bound():
            return False
        to_land = self.v_coast.get() == "pen_land"
        r = max(0.5, self.v_brush.get() - 0.5)
        # a tile's middle under the pen: the tile itself turns (its region pixel too), as the Land / Sea brush does
        middles = [((mx - 1) // 2, (my - 1) // 2) for mx in range(int(px - r) - 1, int(px + r) + 2)
                   for my in range(int(py - r) - 1, int(py + r) + 2)
                   if mx % 2 and my % 2 and ((mx - px) ** 2 + (my - py) ** 2) ** 0.5 <= r]
        middles = [t for t in middles if 0 <= t[0] < self.cmap.w and 0 <= t[1] < self.cmap.h and
                   self.cmap.is_sea(*t) == to_land]
        turned = []
        if middles:
            self._pen_tiles = True
            try:
                turned = self.paint_coast(middles, "pen_land" if to_land else "pen_sea")
            finally:
                self._pen_tiles = False
        got = T.pen_points(heights, self._img("map_ground_types.tga"), (px, py), r, to_land)
        self._coast_points(got)
        return bool(got["heights"] or turned)

    def spray(self, px, py):
        """One puff of the heights brush at map_heights pixel (px, py); True when a pixel changed."""
        if not self._bound():
            return None
        img = self._img("map_heights.tga")
        if img is None:
            self.app.status.set("This campaign has no map_heights.tga.")
            return False
        tool = self.v_tool.get()
        # the brush in pixels of map_heights (a tile is 2 x 2 of them): size n = n pixels across, round, snapped to
        # the pixels (terrain.spray_footprint) - 1 the pixel under the mouse, 2 a square of 2 x 2
        c, radius, _ = T.spray_footprint((px, py), self.v_brush.get())
        got = T.height_spray(img, c, radius, tool, max(1, min(10, self.v_strength.get())), self._hvals,
                             level=self.v_level.get(), dome=True)
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
        if not self._bound():
            return None
        if self.v_what.get() == "heights":               # the eyedropper: the point under the mouse, not the tile
            img = self._img("map_heights.tga")
            px = getattr(self.view, "pick_px", None)
            c = img.get(*px) if img is not None and px and 0 <= px[0] < img.width and 0 <= px[1] < img.height \
                else None
            if c is not None and T.is_land_height(c):
                self.v_level.set(c[0])
                self.v_tool.set("level")
                self.app.status.set("Terrain: height %d picked (point %d, %d) - 'Level' brings the land towards it."
                                    % (c[0], px[0], px[1]))
            elif c is not None:
                self.app.status.set("Terrain: point %d, %d is water - the heights brush changes land only." % px)
            return
        c = self._current(self.v_what.get(), tuple(xy))
        if c is not None:
            self.v_colour.set("%d,%d,%d" % c)

    def _stroke(self):
        self._last_river = None
        self._shape_last = self._push_land = None
        self._undo.append(self._state())
        del self._undo[:-100]
        self._redo = []                          # a new stroke drops the strokes undone before it

    def _state(self):
        return (dict(self.ground), dict(self.features), dict(self.climate), dict(self.heights), dict(self.coast),
                {k: dict(v) for k, v in self.cpx.items()})

    def _restore_to(self, ground, features, climate, heights=None, coast=None, cpx=None):
        # back to the files' colours first, then the kept strokes on top
        g, f = self._img("map_ground_types.tga"), self._img("map_features.tga")
        cl = self._img("map_climates.tga")
        for (what, t), c in self.base.items():
            if c is not None and what == "features":          # ground and climate: by point, in cbase
                self._set_px(f, t[0], t[1], c)
        h = self._img("map_heights.tga")
        for (px, py), v in self.hbase.items():
            self._set_px(h, px, py, (v, v, v))
        imgs = {"regions": self.mod.region_map(self.app.v_campaign.get()) if self.mod else None,
                "ground": g, "heights": h, "climate": cl}
        for (name, p), c in self.cbase.items():
            self._set_px(imgs[name], p[0], p[1], c)
        self.coast = dict(coast or {})
        self.cpx = {k: dict(v) for k, v in (cpx or {"regions": {}, "ground": {}, "heights": {}}).items()}
        self.cpx.setdefault("hgt", {})
        self._sc = None
        self._rtiles = None
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
        if self.mod is None:                    # no mod loaded yet: nothing painted, nothing to put back
            self.app.status.set("Terrain: load a mod first.")
            return
        self._restore_to({}, {}, {}, {}, {}, None)
        self.app.status.set("Terrain: nothing painted.")

    def fill_palette(self):
        for w in self.palette.winfo_children():
            w.destroy()
        what = self.v_what.get()
        if what == "ground":
            from .limits import engine_of, game_kind
            land, sea = T.ground_brushes(game_kind(self.mod) if self.mod else None,
                                         engine_of(self.mod) if self.mod else None)
            items = [("land", land, T.GROUND), ("sea", sea, T.GROUND)]
            self.hint.configure(text=(
                "Left drag paints the picked ground, right click picks a tile's own, right drag moves the map. "
                "A tile's ground decides movement, farming and what may stand there; land stays land and sea stays "
                "sea here - to turn sea into land or land into sea, use 'Land and sea' above. On the coast a tile's "
                "ground stays on its own side of the waterline (map_heights: the coast runs between the tiles' "
                "middles), so no land texture is laid on the water. The beach is land: both games lay it on the "
                "land tiles along the coast. Mountains, high mountains, dense "
                "forest and impassable land / sea are refused under towns, ports and characters (the game refuses them "
                "there); impassable: no army walks or sails there (Medieval II; Rome with REX only); impassable, always black: "
                "never walked and never seen - a wasteland's land hidden for good (REX / M2EX). "
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
        elif what == "coast":
            self._coast_palette()
            self._spray_hook()          # the brush follows the pick even when the map needs no new drawing
            if self.cmap is not None and (getattr(self.cmap, "show_heights", False) != self._by_points() or
                                          getattr(self.cmap, "show_climates", False)):
                self.show()
            return
        elif what == "heights":
            self._heights_palette()
            self._spray_hook()
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
                b = ttk.Radiobutton(box, text=names[c], value="%d,%d,%d" % c, variable=self.v_colour,
                                    style=theme.colour_style(hexc, "Toolbutton"), cursor="hand2")
                b.grid(row=i // per_row, column=i % per_row, padx=1, pady=1, sticky="ew")
                swatches.append(b.cget("value"))
                first = first or "%d,%d,%d" % c
        if first and self.v_colour.get() not in swatches:
            self.v_colour.set(first)
        self._spray_hook()
        if self.cmap is not None and (getattr(self.cmap, "show_climates", False) != (what == "climate") or
                                      getattr(self.cmap, "show_heights", False)):
            self.show()

    def _coast_palette(self):
        """The land / sea brush: which one, and the region new land joins; under it the check of the ground along the
        coast."""
        rows = ttk.Frame(self.palette)
        rows.pack(side="left", fill="x")
        box = ttk.Frame(rows)
        box.pack(side="top", anchor="w")
        ttk.Label(box, text="brush:").pack(side="left", padx=(8, 2))
        ttk.Radiobutton(box, text="Land", value="land", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Radiobutton(box, text="Sea", value="sea", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Radiobutton(box, text="Smooth the coast", value="smooth", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Label(box, text="  coast pen:").pack(side="left", padx=(8, 2))
        ttk.Radiobutton(box, text="land point", value="pen_land", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Radiobutton(box, text="water point", value="pen_sea", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Label(box, text="   new land joins").pack(side="left", padx=(12, 2))
        names = sorted(self.cmap.info) if self.cmap is not None else []
        ttk.Combobox(box, textvariable=self.v_coast_region, values=[NEAREST] + names, width=24,
                     state="readonly").pack(side="left")
        more = ttk.Frame(rows)
        more.pack(side="top", fill="x", pady=(4, 0))
        ttk.Label(more, text="shape brush (a smooth coast where you draw):").pack(side="left", padx=(8, 2))
        ttk.Radiobutton(more, text="land", value="shape_land", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Radiobutton(more, text="water", value="shape_sea", variable=self.v_coast).pack(side="left", padx=3)
        from .gui_util import tip
        tip(ttk.Radiobutton(more, text="pull", value="pull", variable=self.v_coast),
            "Pull the coast, like a painter's liquify: press on the coast and drag - the coast under the brush goes "
            "with the mouse, most in its middle, softly less to its edge; the heights, the tiles and the ground "
            "follow. Draw capes and bays that way.").pack(side="left", padx=3)
        tip(ttk.Radiobutton(more, text="push", value="push", variable=self.v_coast),
            "Push the coast: press on the land beside the coast and the land grows into the water; press on the "
            "water and the water eats into the land - the longer you hold, the further; most in the brush's "
            "middle. Evens a ragged line.").pack(side="left", padx=3)
        ttk.Button(more, text="Find ground on the wrong side of the coast", command=self.ground_check).pack(
            side="left", padx=(16, 0))
        tip(ttk.Checkbutton(more, text="Shore line", variable=self.v_shore, command=self._shore_toggled),
            "Close up, a light line shows the shore exactly as the game will draw it (in every mode of this tab): "
            "the game cuts every square of four heights points into two triangles and lays the water at height 0 - "
            "so the shore runs between the points, not along the tiles.").pack(side="left", padx=(12, 0))
        from .gui_modbuilder import wrapping
        self.lbl_off = wrapping(ttk.Label(more, text=getattr(self, "_off_said", "")), side="left", expand=True, padx=8)
        self.hint.configure(text=(
            "The SHAPE BRUSH draws the coast where the brush's edge goes, smooth like the games' own coasts: the "
            "game cuts every square of four heights points into two triangles and lays the water at height 0, so "
            "the brush sets the heights near the water by their distance from the edge - the game's shore then "
            "falls on it, not on the points' grid (equal heights make stairs at 90 / 45 degrees). The tiles follow "
            "by their middles (new land joins a region), the ground by its points; towns, ports, characters, forts, "
            "rivers keep a little land round them. PULL grabs the coast under the brush and drags it with the "
            "mouse; PUSH, pressed on the land, grows the land into the water (on the water: the water into the "
            "land). Smooth the coast rounds what is under it, the longer you hold "
            "the more (no town lost); the light Shore line shows the shore as the game will draw it. The exact "
            "heights go into map_heights.hgt (the game reads it). "
            "Land / Sea turn whole tiles: sea into land (a new island, a longer coast) or land into sea (a bay, a "
            "strait). Land and sea are "
            "written in three places that must agree, so each tile changes all of them: map_regions.tga (the "
            "region's colour or the sea's), map_ground_types.tga (a land ground like its neighbours', or shallow "
            "sea) and map_heights.tga with map_heights.hgt (a low shore, or the sea's depth). New land joins the "
            "region of the nearest land, or the one picked here - move borders later on the Map (Regions). Refused: "
            "drowning a town, port, character, fort or resource, a region's last land, a river (rub it out first) "
            "or a port's last land. On Apply: those files written, map.rwm deleted (the game builds its map again). "
            "'Find ground on the wrong side of the coast' rings every point where map_ground_types and map_heights "
            "disagree - a land ground on the water (the land's texture lies on the water in the game) or a sea "
            "ground in the land (holes of sea) - and, on a yes, gives each the ground round it on its own side: "
            "the heights lead, they are not changed. The games' own maps have next to none (Rome 0, Medieval II "
            "18 by lakes in the hills)."))

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
            "Level brings the land towards the height set beside it (right click picks the height of the point "
            "under the mouse - an eyedropper). The heights picture has 2 x 2 points a tile, drawn as they are; brush "
            "size 1 is one point, and the line under the map gives the point under the mouse exactly (grey, metres, "
            "water's depth). "
            "Shown as map_heights.tga is: land grey - black low, white high (brightened a little here) - "
            "the sea blue; only land is changed, the coast stays. On Apply: map_heights.tga written, "
            "the same points changed in map_heights.hgt (the game's own copy of the heights, read instead of the "
            "picture while it is there), map.rwm deleted (the game builds its map again). Land never goes down to "
            "black: the game may take black for sea."))
