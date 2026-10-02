"""The Terrain editor (its own work at the top): paint what each tile of the campaign map is
(map_ground_types.tga), what runs across it (map_features.tga: rivers, fords, sources,
cliffs), its climate (map_climates.tga, the climates of descr_climates.txt) and how high the land is
(map_heights.tga, a spray brush: held longer, it raises / lowers more), on the map drawn tile by tile. Kept here until Apply, written by terrain.apply with
a backup like the unit and building editors (dirty / pending / make_plan / rebind)."""

import hashlib
import tkinter as tk
from tkinter import ttk

from . import terrain as T

NEAREST = "(the nearest region)"


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
        self.cpx = {"regions": {}, "ground": {}, "heights": {}}     # the pixels those tiles change
        self.cbase = {}                 # those pixels as the files have them: {(file, (x, y)): colour}
        self._undo, self._redo = [], []
        self._last_river = None         # the last river tile of the stroke: the next one joins it side to side
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Paint", font=("", 10, "bold")).pack(side="left")
        self.v_what = tk.StringVar(value="ground")
        for val, text in (("ground", "Ground"), ("features", "Rivers, cliffs, volcanoes..."),
                          ("climate", "Climates"), ("heights", "Heights"), ("coast", "Land and sea")):
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
        self.v_coast = tk.StringVar(value="land")          # the land / sea brush
        self.v_coast_region = tk.StringVar(value=NEAREST)
        from .gui_util import ShortHint
        self.hint = ShortHint(self)                      # one line; the whole explanation on its '?'
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
        for name in ("map_ground_types.tga", "map_features.tga", "map_climates.tga", "map_heights.tga",
                     "map_regions.tga"):
            try:
                with open(self.mod.campaign_file(self.app.v_campaign.get(), name), "rb") as fh:
                    h.update(fh.read())
            except (OSError, TypeError, AttributeError):
                pass
        return h.hexdigest()

    def dirty(self):
        return bool(self.ground or self.features or self.climate or self.heights or self.coast)

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
            self.cpx = {"regions": {}, "ground": {}, "heights": {}}
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
        T.apply(plan, self.app.v_campaign.get(), self.ground, self.features, self.climate, self.heights,
                dict(self.cpx, tiles=self.coast) if self.coast else None)
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
        for (px, py), c in self.cpx["heights"].items():
            self._set_px(h, px, py, c)
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

    def paint_coast(self, tiles):
        """The land / sea brush: each tile turned with its regions pixel, the ground and heights round it."""
        to_land = self.v_coast.get() == "land"
        camp = self.app.v_campaign.get()
        reg_img = self.mod.region_map(camp)
        if not hasattr(self, "_sea"):
            self._sea = T.sea_colour(reg_img, [v["colour"] for v in self.cmap.info.values()])
        heights = self._img("map_heights.tga")
        feats = self._features_now()
        counts = self._region_tiles()
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
        if took:
            self.cmap.__dict__.pop("_backgrounds", None)
            self.cmap._hpil = None
        self.app.status.set(("Terrain: %d tile(s) of land / sea changed - Preview, then Apply changes."
                             % len(self.coast)) + ("   (not here: %s)" % why if why else ""))
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
        return (dict(self.ground), dict(self.features), dict(self.climate), dict(self.heights), dict(self.coast),
                {k: dict(v) for k, v in self.cpx.items()})

    def _restore_to(self, ground, features, climate, heights=None, coast=None, cpx=None):
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
        imgs = {"regions": self.mod.region_map(self.app.v_campaign.get()) if self.mod else None,
                "ground": g, "heights": h}
        for (name, p), c in self.cbase.items():
            self._set_px(imgs[name], p[0], p[1], c)
        self.coast = dict(coast or {})
        self.cpx = {k: dict(v) for k, v in (cpx or {"regions": {}, "ground": {}, "heights": {}}).items()}
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
                "sea here - to turn sea into land or land into sea, use 'Land and sea' above. Mountains, high mountains, dense "
                "forest and impassable land / sea are refused under towns, ports and characters (the game refuses them "
                "there); impassable: no army walks or sails there (Medieval II; Rome with REX only). "
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
            if self.cmap is not None and (getattr(self.cmap, "show_heights", False) or
                                          getattr(self.cmap, "show_climates", False)):
                self.show()
            return
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

    def _coast_palette(self):
        """The land / sea brush: which one, and the region new land joins."""
        box = ttk.Frame(self.palette)
        box.pack(side="left")
        ttk.Label(box, text="brush:").pack(side="left", padx=(8, 2))
        ttk.Radiobutton(box, text="Land", value="land", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Radiobutton(box, text="Sea", value="sea", variable=self.v_coast).pack(side="left", padx=3)
        ttk.Label(box, text="   new land joins").pack(side="left", padx=(12, 2))
        names = sorted(self.cmap.info) if self.cmap is not None else []
        ttk.Combobox(box, textvariable=self.v_coast_region, values=[NEAREST] + names, width=24,
                     state="readonly").pack(side="left")
        self.hint.configure(text=(
            "Turn sea into land (a new island, a longer coast) or land into sea (a bay, a strait). Land and sea are "
            "written in three places that must agree, so each tile changes all of them: map_regions.tga (the "
            "region's colour or the sea's), map_ground_types.tga (a land ground like its neighbours', or shallow "
            "sea) and map_heights.tga with map_heights.hgt (a low shore, or the sea's depth). New land joins the "
            "region of the nearest land, or the one picked here - move borders later on the Map (Regions). Refused: "
            "drowning a town, port, character, fort or resource, a region's last land, a river (rub it out first) "
            "or a port's last land. On Apply: those files written, map.rwm deleted (the game builds its map again)."))

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
