"""The Terrain editor (its own work at the top): paint what each tile of the campaign map is
(map_ground_types.tga) and what runs across it (map_features.tga: rivers, fords, sources,
cliffs), on the map drawn tile by tile. Kept here until Apply, written by terrain.apply with
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
        self.ground, self.features = {}, {}          # painted tiles: {(x, y): colour}
        self.base = {}                               # what the files have there: {('ground'|'features', xy): colour}
        self._undo, self._redo = [], []
        self._last_river = None         # the last river tile of the stroke: the next one joins it side to side
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Paint", font=("", 10, "bold")).pack(side="left")
        self.v_what = tk.StringVar(value="ground")
        for val, text in (("ground", "Ground"), ("features", "Rivers, fords, cliffs")):
            ttk.Radiobutton(top, text=text, value=val, variable=self.v_what, command=self.fill_palette).pack(
                side="left", padx=4)
        ttk.Label(top, text="   brush").pack(side="left")
        self.v_brush = tk.IntVar(value=1)
        ttk.Spinbox(top, from_=1, to=6, width=3, textvariable=self.v_brush,
                    command=lambda: setattr(self.view, "brush", self.v_brush.get())).pack(side="left", padx=2)
        ttk.Button(top, text="Undo all changes here", command=self.reset).pack(side="right")
        self.v_grid_here = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Grid", variable=self.v_grid_here, command=self._grid_toggled).pack(
            side="left", padx=(16, 0))
        ttk.Button(top, text="Redo stroke", command=self.redo_stroke).pack(side="right", padx=(0, 4))
        ttk.Button(top, text="Undo stroke", command=self.undo_stroke).pack(side="right", padx=4)
        self.palette = ttk.Frame(self, padding=(0, 4))
        self.palette.pack(fill="x")
        self.v_colour = tk.StringVar()
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
        for name in ("map_ground_types.tga", "map_features.tga"):
            try:
                with open(self.mod.campaign_file(self.app.v_campaign.get(), name), "rb") as fh:
                    h.update(fh.read())
            except (OSError, TypeError, AttributeError):
                pass
        return h.hexdigest()

    def dirty(self):
        return bool(self.ground or self.features)

    def pending(self):
        return len(self.ground) + len(self.features)

    def rebind(self, mod):
        lost = 0
        if self.mod is not None and self.dirty() and mod.data == self.mod.data and self._signature() != self._sig:
            lost = self.pending()
        if lost or self.mod is None or mod.data != self.mod.data or not self.dirty():
            self.ground, self.features, self.base, self._undo = {}, {}, {}, []
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
        T.apply(plan, self.app.v_campaign.get(), self.ground, self.features)
        broken = T.river_warnings(self._features_now(), self.cmap.w, self.cmap.h, self.cmap.is_sea) \
            if self.features else []
        for x, y, n in broken[:20]:
            plan.warnings.append(("map_features.tga", "the river at %d, %d (%d tile(s)) joins no sea, map edge, river "
                                                      "source or other river by a tile's side - the game will not draw "
                                                      "it: it follows a river side to side and stops where two river "
                                                      "tiles touch only by a corner" % (x, y, n)))
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
                {c.xy for fb in (s.factions if s else []) for c in fb.characters if c.xy}
            self._apply_memory()
        self.view.brush = self.v_brush.get()
        self.view.load(self.cmap, {}, {}, region_mode=True, on_paint=self.paint, on_pick=self.pick,
                       brush=self.v_brush.get(), plain=True)

    def _img(self, name):
        return self.mod._optional_map(self.app.v_campaign.get(), name)

    def _set_px(self, img, x, y, colour):
        if img is not None and 0 <= x < img.width and 0 <= y < img.height:
            img.pixels[y * img.width + x] = tuple(colour)

    def _apply_memory(self):
        """The painted tiles laid into the in-memory pictures the map is drawn from."""
        g, f = self._img("map_ground_types.tga"), self._img("map_features.tga")
        for (px, py), c in T.ground_changes(self.ground).items():
            self._set_px(g, px, py, c)
        for (x, y), c in self.features.items():
            self._set_px(f, x, y, c)
        if self.cmap is not None:
            self.cmap.__dict__.pop("_backgrounds", None)

    def _features_now(self):
        f = self._img("map_features.tga")
        if f is None:
            return {}
        return {(x, y): f.get(x, y) for y in range(f.height) for x in range(f.width) if f.get(x, y) != (0, 0, 0)}

    def _current(self, what, xy):
        if what == "ground":
            return self.cmap.ground_at(*xy)
        f = self._img("map_features.tga")
        return f.get(*xy) if f and 0 <= xy[0] < f.width and 0 <= xy[1] < f.height else None

    def paint(self, tiles):
        what = self.v_what.get()
        colour = tuple(int(v) for v in self.v_colour.get().split(",")) if self.v_colour.get() else None
        if colour is None:
            return []
        store = self.ground if what == "ground" else self.features
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
            if what == "ground":
                for (px, py), c in T.ground_changes({t: colour}).items():
                    self._set_px(self._img("map_ground_types.tga"), px, py, c)
            else:
                self._set_px(self._img("map_features.tga"), t[0], t[1], colour)
            from .mapdata import GROUND_LOOK, CampaignMap
            took.append((t, GROUND_LOOK.get(colour) if what == "ground" else CampaignMap.FEATURE_LOOK.get(colour, (0, 0, 0))))
        if took:
            self.cmap.__dict__.pop("_backgrounds", None)
        self.app.status.set(("Terrain: %d tile(s) painted - Preview, then Apply changes." % self.pending()) +
                            ("   (not here: %s)" % why if why else ""))
        self.app._mark_work()
        return took

    def pick(self, xy):
        c = self._current(self.v_what.get(), tuple(xy))
        if c is not None:
            self.v_colour.set("%d,%d,%d" % c)

    def _stroke(self):
        self._last_river = None
        self._undo.append((dict(self.ground), dict(self.features)))
        del self._undo[:-100]
        self._redo = []                          # a new stroke drops the strokes undone before it

    def _restore_to(self, ground, features):
        # back to the files' colours first, then the kept strokes on top
        g, f = self._img("map_ground_types.tga"), self._img("map_features.tga")
        for (what, t), c in self.base.items():
            if c is None:
                continue
            if what == "ground":
                for (px, py), cc in T.ground_changes({t: c}).items():
                    self._set_px(g, px, py, cc)
            else:
                self._set_px(f, t[0], t[1], c)
        self.ground, self.features = ground, features
        self._apply_memory()
        self.view.render()
        self.app._mark_work()

    def undo_stroke(self):
        if self._undo:
            self._redo.append((dict(self.ground), dict(self.features)))
            self._restore_to(*self._undo.pop())
            self.app.status.set("Terrain: a stroke undone (%d more back, %d to redo)." % (len(self._undo), len(self._redo)))
        else:
            self.app.status.set("Terrain: nothing to undo.")

    def redo_stroke(self):
        if self._redo:
            self._undo.append((dict(self.ground), dict(self.features)))
            self._restore_to(*self._redo.pop())
            self.app.status.set("Terrain: a stroke redone (%d more to redo)." % len(self._redo))
        else:
            self.app.status.set("Terrain: nothing to redo.")

    # the window's Undo / Redo (bottom bar, Ctrl+Z / Ctrl+Y) while this editor is on show
    undo_step = undo_stroke
    redo_step = redo_stroke

    def reset(self):
        self._undo, self._redo = [], []
        self._restore_to({}, {})
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
        else:
            items = [("marks", T.FEATURE_BRUSHES, T.FEATURES)]
            self.hint.configure(text=(
                "Rivers, fords (the tiles where armies cross a river), river sources and cliffs: one per tile in "
                "map_features.tga. A ford goes on the river's own line; 'nothing' rubs a mark out. The game follows "
                "a river side to side from the sea, a source or another river and stops where two river tiles "
                "touch only by a corner - the 1-tile brush fills such steps itself, and Preview names a river "
                "the game will not draw. Not under towns, ports or characters (the game refuses them there)."))
        from .mapdata import GROUND_LOOK, CampaignMap
        first = None
        for label, colours, names in items:
            ttk.Label(self.palette, text=label + ":").pack(side="left", padx=(8, 2))
            for c in colours:
                look = GROUND_LOOK.get(c) if what == "ground" else CampaignMap.FEATURE_LOOK.get(c, (20, 20, 20))
                hexc = "#%02x%02x%02x" % look
                fg = "white" if sum(look) < 380 else "black"
                b = tk.Radiobutton(self.palette, text=names[c], value="%d,%d,%d" % c, variable=self.v_colour,
                                   indicatoron=0, bg=hexc, fg=fg, selectcolor=hexc, activebackground=hexc,
                                   padx=6, pady=3, relief="raised", offrelief="flat", bd=3, cursor="hand2")
                b.pack(side="left", padx=1)
                first = first or "%d,%d,%d" % c
        if first and self.v_colour.get() not in [w.cget("value") for w in self.palette.winfo_children()
                                                 if isinstance(w, tk.Radiobutton)]:
            self.v_colour.set(first)
