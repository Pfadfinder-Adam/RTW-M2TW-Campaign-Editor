"""The campaign map drawn by the graphics card (OpenGL through moderngl) the way the games draw it - Maps > 3D, both
games. What the games do (read in the engine's source, facts only - editor-notes strat_map_render.md):

- the ground is one grid of points, map_heights.tga's own size (2 W + 1 x 2 H + 1 for W x H tiles): a tile is
  1 x 1, a point every half tile, each half-tile square split along its south-west -> north-east diagonal; a point
  stands h * 0.0005 * (1.2 Medieval II, 0.6 Rome) high, the sea level at 0;
- each point names a ground picture (its climate on map_climates.tga and ground on map_ground_types.tga, through
  descr_aerial_map_ground_types.txt); a half-tile square blends the pictures of its four corners with the game's
  painted masks (terrain/aerial_map/template_weights/weights*.tga - each corner one of them at random, mirrored to
  its corner), so the borders between grounds are soft and ragged, never a straight cross-fade;
- the pictures lie fixed on the world: a picture N pixels wide repeats every N / (64 x texture_density) tiles;
- the light (descr_strategy_lighting.txt): colour = picture x min(ambient + diffuse x (normal . sun), 1); with REX /
  M2EX (descr_strategy_lighting_ex.txt) the same sum in linear light, made sRGB at the end (lighting());
- the sea is a flat sheet at height 0 under everything - land below 0 hides under it, so the coast is where the
  ground crosses 0: water_surface.tga stretched over the whole map, with the waves and the sky's reflection;
- along that line lie see-through strips: the beach (sea/beach_strip.tga) and the wet sand and surf (sea/surf2b.tga)
  sliding in from the sea (coast_line, coast_strips).

Everything lives on the card as pictures (the heights, the ground picture of each point): a brush stroke changes
a few of their pixels, the next frame shows it. The frame is drawn off the screen and handed to the window as a
picture (the same way on every system - no window of its own to fit into Tk). Without moderngl or a card that
gives OpenGL 3.3, available() says why and Maps > 3D draws as before (terrain3d)."""

import math
import os
import time

import numpy as np

from . import maptrees as MT
from . import terrain as T
from . import terrain3d as T3

SCALE = {"medieval2": 1.2, "rome": 0.6}         # the games' height scale (aerial_map.h)
LAYERS = (("sea", "Sea"), ("coast", "Beach and surf"), ("mountains", "Mountains and volcanoes"),
          ("hills", "Hills"), ("rivers", "Rivers"), ("cliffs", "Cliffs"), ("trees", "Trees"),
          ("roads", "Roads"), ("borders", "Region borders"), ("towns", "Towns and ports"),
          ("resources", "Resources"),
          ("armies", "Armies, agents and fleets"))                        # what render(show=) can leave out
MODEL_LAYERS = {"mountains": 1, "hills": 2, "rivers": 3, "cliffs": 4}     # tilemodels.KIND of each
OBJECT_LAYERS = {"towns": 1, "resources": 2, "armies": 3}                 # mapmodels.KIND of each
SEGMENT_TEXELS = 64                             # a picture's pixels a tile covers at texture_density 1
LAYER = 512                                     # every ground picture is made this size on the card
SEA_LIGHT = (0.5, 1.0, 1.0)                     # the way to the sea's own light (the engine's (-0.5, -1, -1) reversed)

_ctx = None
_why = None


def context():
    """The one OpenGL context of the editor (made the first time), or None - available() says why."""
    global _ctx, _why
    if _ctx is not None or _why is not None:
        return _ctx
    try:
        import moderngl
    except ImportError:
        _why = "moderngl is not installed (the editor's exe has it)"
        return None
    errors = []
    for backend in (None, "egl"):                # the system's own way first; EGL where there is no display
        try:
            ctx = moderngl.create_standalone_context(**({"backend": backend} if backend else {}))
            if ctx.version_code < 330:
                errors.append("OpenGL %s - 3.3 is needed" % ctx.info.get("GL_VERSION", ctx.version_code))
                ctx.release()
                continue
            _ctx = ctx
            return ctx
        except Exception as e:                   # each way said why it could not
            errors.append(str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__)
    _why = "no OpenGL 3.3 from the graphics card (%s)" % "; ".join(errors)
    return None


def available():
    """(True, '') when the card draws the map, else (False, why in plain words)."""
    return (context() is not None, _why or "")


def lighting(mod):
    """{ambient, diffuse, direction, linear, exposure} of the campaign map's light. REX / M2EX read
    descr_strategy_lighting_ex.txt when there is one (its colours are linear: the light is added up in linear
    light and the picture made sRGB at the end, a soft shoulder above 0.9 - the engine's own look); else
    descr_strategy_lighting.txt in the old games' way (picture x min(light, 1), all in sRGB). The mod's file, else
    the game's; the games' own values where a line is missing."""
    from .textio import strip_comment
    m2 = _kind(mod) == "medieval2"
    out = {"ambient": (0.5, 0.5, 0.52) if m2 else (0.3, 0.3, 0.5),
           "diffuse": (0.7, 0.7, 0.72) if m2 else (1.1, 1.1, 0.85),
           "direction": (-1.0, -1.0, 1.0), "linear": False, "exposure": 1.0}
    p = mod.find_any("descr_strategy_lighting_ex.txt")
    if p:
        out["linear"] = True
    else:
        p = mod.find_any("descr_strategy_lighting.txt")
    if p:
        for line in mod.load(p).texts():
            t = strip_comment(line).split()
            key = {"ambient_colour": "ambient", "diffuse_colour": "diffuse", "diffuse_direction": "direction"}.get(
                t[0] if t else "")
            try:
                if key and len(t) >= 4:
                    out[key] = tuple(float(v) for v in t[1:4])
                elif t and t[0] == "exposure" and len(t) >= 2:
                    out["exposure"] = float(t[1])
            except ValueError:
                pass
    return out


def _kind(mod):
    from .limits import game_kind
    return game_kind(mod)


def _image(mod, rels, size=None, mode="RGB"):
    """A picture of the mod (else the game) as an array (h, w, channels), resized to size when given; None
    without one. rels: the paths under data/ to try, each also with '.dds' after it."""
    from PIL import Image
    for rel in rels:
        for name in (rel, rel + ".dds"):
            p = mod.find_any(name)
            if not p:
                continue
            try:
                with Image.open(p) as im:
                    im = im.convert(mode)
                    if size:
                        im = im.resize((size, size), Image.BILINEAR)
                    return np.asarray(im, dtype=np.uint8)
            except Exception:
                continue
    return None


def _image_size(mod, rel):
    from PIL import Image
    for name in (rel, rel + ".dds"):
        p = mod.find_any(name)
        if p:
            try:
                with Image.open(p) as im:
                    return im.size[0]
            except Exception:
                return None
    return None


def _coast_hidden(feats):
    """Where the game draws no coast strip: rivers (sources, fords) and cliffs on map_features ((h, w, 3) or None)."""
    if feats is None:
        return None
    code = (feats[..., 0].astype(np.int32) << 16) | (feats[..., 1].astype(np.int32) << 8) | feats[..., 2]
    return np.isin(code, [(r << 16) | (g << 8) | b for r, g, b in T.RIVERY | {(255, 255, 0)}])


def _rivers(feats, H, W):
    """(H, W) bool, rows bottom first: the river tiles of map_features (roads and borders bend round them)."""
    if feats is None or feats.shape[:2] != (H, W):
        return np.zeros((H, W), bool)
    f = feats[::-1].astype(np.int32)
    return np.isin((f[..., 0] << 16) | (f[..., 1] << 8) | f[..., 2], (0x0000ff, 0xffffff, 0x00ffff))


class MapData:
    """What the card needs of a campaign map, as arrays (the slow part, no OpenGL - made once, also in a thread):
    heights (metres, top row first), the ground picture of each point (an index into pictures), the pictures, the
    masks, the sea's pictures, the light."""

    def __init__(self, mod, campaign, winter=False, strat=None, moved=None):
        h = T3.heights_metres(mod, campaign)
        if h is None:
            raise ValueError("this campaign has no map_heights.tga - nothing to raise in 3D")
        self.heights = h.astype(np.float32)
        self.rows, self.cols = h.shape
        self.kind = _kind(mod)
        self.scale = SCALE.get(self.kind, 0.6)
        self.notes = []
        self.layers, self.pictures, self.repeat = self._ground(mod, campaign, winter)
        self.masks = self._masks(mod)
        self.water = _image(mod, ["world/maps/campaign/%s/water_surface.tga" % campaign,
                                  "world/maps/base/water_surface.tga"])
        self.waves = _image(mod, ["terrain/aerial_map/sea/waves.tga"], mode="RGBA")
        self.sky = _image(mod, ["terrain/aerial_map/sea/sky_environment_summer.tga"])
        self.beach = _image(mod, ["terrain/aerial_map/sea/beach_strip.tga"], mode="RGBA")
        self.surf = _image(mod, ["terrain/aerial_map/sea/surf2b.tga"], mode="RGBA")
        self.light = lighting(mod)
        self._tile_models(mod, campaign, winter)
        self._trees(mod, campaign, winter)
        self._objects(mod, campaign, strat, moved=moved)
        self.coast_hidden = _coast_hidden(T3._picture(mod, campaign, "map_features.tga"))

    def _ground(self, mod, campaign, winter):
        """(layer of each point (rows, cols) uint16, [pictures (LAYER, LAYER, 3)], [repeats a tile per layer])."""
        keys = sorted(set(T3.GROUND_KEYS.values()) | {"beach"})
        names, choices, density = T3.picture_choices(mod, keys, winter)
        files, loaded, pictures, repeat, missing = {}, {}, [], [], set()
        table = np.zeros((len(names), len(keys)), np.int32)
        for c, cname in enumerate(names):
            for g, key in enumerate(keys):
                tag = None
                for fname in choices[(cname, key)]:          # the mod's picture, else the game's own
                    if fname.lower() not in loaded:
                        rel = T3.ground_file(fname)
                        arr = _image(mod, [rel], LAYER)
                        loaded[fname.lower()] = (arr, _image_size(mod, rel)) if arr is not None else None
                    if loaded[fname.lower()] is None:
                        missing.add(fname)
                        continue
                    tag = fname.lower()
                    break
                if tag is None:
                    tag = "plain:" + key
                if tag not in files:
                    if tag.startswith("plain:"):             # the ground's plain colour where no picture opens
                        arr, n = np.empty((LAYER, LAYER, 3), np.uint8), None
                        arr[:] = T3.PLAIN.get(key, (120, 120, 90))
                    else:
                        arr, n = loaded[tag]
                    files[tag] = len(pictures)
                    pictures.append(arr)
                    repeat.append(SEGMENT_TEXELS * density / float(n or LAYER))
                table[c, g] = files[tag]
        missing = {m for m in missing if loaded.get(m.lower()) is None}
        if missing:
            self.notes.append("%d ground picture(s) not found - the game's own picture of that ground (else its plain "
                              "colour) shown: %s" % (len(missing), ", ".join(
                                  sorted(os.path.basename(m) for m in missing)[:4]) + (" ..." if len(missing) > 4 else "")))
        if not any(choices.values()):
            self.notes.append("no descr_aerial_map_ground_types.txt - the grounds' plain colours shown")
        self._ground_keys, self._climate_names, self._climates, self._table = keys, names, T.climates(mod), table
        layers = self.layers_of(T3._picture(mod, campaign, "map_ground_types.tga"),
                                T3._picture(mod, campaign, "map_climates.tga"), self.heights <= 0)
        return layers, pictures, repeat

    def layers_of(self, ground, climate, sea):
        """The ground picture (layer) of points: (h, w) uint16 from their map_ground_types and map_climates colours
        ((h, w, 3) top row first, or None) and whether each is under the sea ((h, w) bool) - the rule of loading,
        also for a brush's few points (a point raised out of the water shows its own ground and climate at once)."""
        keys, shape = self._ground_keys, sea.shape
        gi = T3._ground_index(ground, keys) if ground is not None and ground.shape[:2] == shape else \
            np.full(shape, keys.index("fertility_low"), np.int32)
        ci = T3._climate_index(None, climate, self._climate_names, self._climates) if climate is not None and \
            climate.shape[:2] == shape else np.zeros(shape, np.int32)
        # the games' own fix at loading: a land point with a sea colour is low fertility, a sea point is beach
        gi = np.where(gi < 0, keys.index("fertility_low"), gi)
        gi = np.where(sea, keys.index("beach"), gi)
        return self._table[ci, gi].astype(np.uint16)

    def tint_of(self, kind, climate=None, regions=None):
        """The colours laid over the map, a tile each ((H, W, 4) uint8, top row first): 'climates' - each tile's
        climate colour (map_climates, (h, w, 3) top row first), the sea's too: what new land made there gets;
        'regions' - each land tile's map_regions colour ((H, W, 3) top row first), the sea left clear."""
        H, W = (self.rows - 1) // 2, (self.cols - 1) // 2
        out = np.zeros((H, W, 4), np.uint8)
        if kind == "climates" and climate is not None and climate.shape[:2] == self.heights.shape:
            out[..., :3] = climate[1::2, 1::2][:H, :W]
            out[..., 3] = 255
        elif kind == "regions" and regions is not None and regions.shape[:2] == (H, W):
            out[..., :3] = regions
            out[..., 3] = np.where(self.heights[1::2, 1::2][:H, :W] > 0, 255, 0)
        return out

    def refresh_ground(self, mod, campaign, painted=None):
        """The brushes changed the ground, climates or regions in memory (land raised out of the water, land sunk
        under it): what the tile models, trees and borders stand on read again, each point's picture made again -
        returned, for the card to take on the main thread. painted: {tile: region} the Map's Edit regions gave and
        Apply will write (the borders drawn as it will leave them). No new build of the map (the user, 2026-10-22: the map
        made again at a stroke's end lagged, and the new land's texture came in after)."""
        from . import mapnet as N
        from . import tilemodels as TM
        ground = T3._picture(mod, campaign, "map_ground_types.tga")
        climate = T3._picture(mod, campaign, "map_climates.tga")
        feats = T3._picture(mod, campaign, "map_features.tga")
        if getattr(self, "_model_src", None):
            self._model_src = (ground, feats) + tuple(self._model_src[2:])
        self.coast_hidden = _coast_hidden(feats)
        if getattr(self, "_tree_src", None):
            H, W = (self.rows - 1) // 2, (self.cols - 1) // 2
            names = [n for n, _ in self._tree_src[2]]
            ci = T3._climate_index(mod, climate, names) if climate is not None and \
                climate.shape[:2] == self.heights.shape else np.zeros(self.heights.shape, np.int32)
            self._tree_src = (ground, ci[1::2, 1::2][:H, :W][::-1]) + tuple(self._tree_src[2:])
        src = getattr(self, "_net_src", None)
        if src:
            from .regionedit import SEA
            src["grid"], src["names"] = N.region_grid(mod, campaign)
            index = {n: i for i, n in enumerate(src["names"])}
            gh, gw = src["grid"].shape
            for (x, y), name in (painted or {}).items():
                if 0 <= x < gw and 0 <= y < gh and (name in index or name == SEA):
                    src["grid"][y, x] = index.get(name, -1)
            H, W = src["grid"].shape
            src["mountains"] = TM.tile_types(ground)[TM.MOUNTAINS_HIGH] if ground is not None and \
                ground.shape[:2] == self.heights.shape else np.zeros((H, W), bool)
            src["feats"], src["rivers"] = feats, _rivers(feats, H, W)
        return self.layers_of(ground, climate, self.heights <= 0)

    def _tile_models(self, mod, campaign, winter):
        """The tile models (mountains, hills, volcanoes - tilemodels) placed on this map, their pictures."""
        from . import tilemodels as TM
        self.models = {"under": np.zeros((0, 7), np.float32), "over": {}, "water": np.zeros((0, 6), np.float32)}
        self.river_flow = _image(mod, ["terrain/aerial_map/water.tga"])
        self.voids = np.zeros(((self.rows - 1) // 2, (self.cols - 1) // 2), np.uint8)
        self.model_pictures, self.model_masks = {}, {}
        try:
            self._lib = TM.Library(mod)
            towns = []
            try:                                         # towns and ports: no cliffs within 2 tiles of them
                img = mod.region_map(campaign)
                towns = list(mod.city_tiles(campaign).values()) + list(img.find((255, 255, 255)))
            except Exception:
                pass
            self._model_src = (T3._picture(mod, campaign, "map_ground_types.tga"),
                               T3._picture(mod, campaign, "map_features.tga"), towns)
            self.place_models()
        except Exception as e:                          # said in the bar, the map still drawn
            self._lib = None
            self.notes.append("the mountains and hills are not drawn: %s" % e)
            return
        for tex, page in self.models["over"]:
            if tex not in self.model_pictures:
                self.model_pictures[tex] = _image(mod, TM.texture_rel(tex, winter=winter), mode="RGBA")
            if page and page not in self.model_masks:
                f = self._lib.pages.get(page, ("",))[0]
                self.model_masks[page] = _image(mod, ["terrain/aerial_map/tile_models/alpha_pages/" + f], mode="RGBA")
        if self._lib.missing:
            self.notes.append("tile model file(s) not found: %s" % ", ".join(sorted(self._lib.missing)[:4]))

    def place_models(self):
        """The tile models (and the trees) placed again on the heights as they are now (after a brush)."""
        from . import tilemodels as TM
        self.place_trees()
        self.place_objects()
        if getattr(self, "_lib", None) is None:
            return
        idx, seed = TM.assign(self.heights, *self._model_src)
        self.models = TM.build(self._lib, idx, seed, self.heights, 0.0005 * self.scale)
        self.voids = TM.void_map(idx, self._lib)

    def _trees(self, mod, campaign, winter):
        """The forests' trees (maptrees): each forest tile's models from descr_climates.txt, their pictures."""
        from . import maptrees as MT
        self.trees, self.tree_models, self.tree_pictures, self._tree_src = {}, {}, {}, None
        try:
            path = mod.find_any("descr_climates.txt")
            climates = MT.read_climates("\n".join(mod.load(path).texts())) if path else []
            ground = self._model_src[0] if getattr(self, "_model_src", None) else \
                T3._picture(mod, campaign, "map_ground_types.tga")
            cpic = T3._picture(mod, campaign, "map_climates.tga")
            names = [n for n, _ in climates]
            ci = T3._climate_index(mod, cpic, names) if cpic is not None and cpic.shape[:2] == self.heights.shape \
                else np.zeros(self.heights.shape, np.int32)
            H, W = (self.rows - 1) // 2, (self.cols - 1) // 2
            self._tree_src = (ground, ci[1::2, 1::2][:H, :W][::-1], climates, winter)
            lib = MT.Models(mod)
            for _, seasons in climates:
                for kinds in seasons.values():
                    for files in kinds.values():
                        for f, _cell in files:
                            m = lib.model(f)
                            if m is not None and f.lower() not in self.tree_models:
                                self.tree_models[f.lower()] = m
                                if m[2] and m[2] not in self.tree_pictures:
                                    self.tree_pictures[m[2]] = _image(mod, [m[2]], mode="RGBA")
            if lib.missing:
                self.notes.append("tree model file(s) not found (the game leaves them out too): %s" %
                                  ", ".join(sorted(lib.missing)[:4]))
            self.place_trees()
        except Exception as e:                          # said in the bar, the map still drawn
            self.notes.append("the trees are not drawn: %s" % e)

    def _objects(self, mod, campaign, strat=None, loader=None, moved=None):
        """What stands on the map (mapobjects3d.objects: towns, ports, forts, resources, characters) as the game's
        models (mapmodels), their textures. strat: descr_strat as read (a Strat) - the Map's changes not written yet
        included - else the file."""
        from . import mapmodels as MM
        from . import mapobjects3d as O
        from .strat import Strat
        self.objects, self.object_pictures, self._objs = {}, {}, None
        try:
            if strat is None:
                strat = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
            self._objs = (O.objects(mod, campaign, strat, moved), loader or MM.Loader(mod))
            try:
                self._net(mod, campaign, strat)
            except Exception as e:                      # the roads and borders alone left out
                self.notes.append("the roads and borders are not drawn: %s" % e)
            self.place_objects()
            loader = self._objs[1]
            for tex in self.objects:
                if tex is not None:
                    self.object_pictures[tex] = loader.picture(tex)
            self.objects_missing = sorted(loader.missing)        # all of them (the bar names four): into the log
            if loader.missing:
                self.notes.append("model(s) or texture(s) of what stands on the map not found: %s" %
                                  ", ".join(self.objects_missing[:4]))
        except Exception as e:                          # said in the bar, the map still drawn
            self.notes.append("the towns and armies are not drawn: %s" % e)

    def set_strat(self, mod, campaign, strat, moved=None):
        """descr_strat changed (an army added or moved on the Map, not written yet): what stands on the map laid
        again from it, the models already read kept. GLMap.models_placed() then gives it to the card."""
        loader = self._objs[1] if getattr(self, "_objs", None) else None
        self.notes = [n for n in self.notes if not n.startswith(("model(s) or texture(s)", "the towns and armies",
                                                                "the roads and borders"))]
        self._objects(mod, campaign, strat, loader, moved)

    def place_objects(self):
        """The towns, armies, roads and borders laid again on the heights as they are now."""
        from . import mapmodels as MM
        self.ghost, self._held = {}, None
        if getattr(self, "_objs", None):
            self._each = MM.build_each(self._objs[0], self._objs[1], self.heights, 0.0005 * self.scale)
            self.objects = MM.join(self._each)
        self.place_net()

    def lift_out(self, pick):
        """What pick(object) chooses (mapobjects3d.objects' dicts) taken out of the map into the hand: self.ghost
        holds it as the card draws it, self.objects the rest - it then goes with the mouse (GLMap.ghost_shift) until
        put down. True when anything was taken. Only joined again from each object's laid pieces (_each), nothing
        laid anew."""
        from . import mapmodels as MM
        if not getattr(self, "_objs", None) or len(getattr(self, "_each", ())) != len(self._objs[0]):
            return False
        objs = self._objs[0]
        held = [i for i, o in enumerate(objs) if pick(o)]
        if not held:
            return False
        out = set(held)
        self.objects = MM.join(e for i, e in enumerate(self._each) if i not in out)
        self.ghost = MM.join(self._each[i] for i in held)
        self._held = held
        return True

    def put_down(self, tile=None):
        """What is in the hand put down - on tile (its objects moved there, only they laid again), else back where it
        stood - and joined to the rest without laying the whole map again (a tester: a short stall each time a
        figure was let go: every town, army and resource was laid anew, 0.7 s on Rome's map)."""
        from . import mapmodels as MM
        held = getattr(self, "_held", None)
        if not held or not getattr(self, "ghost", None):
            return False
        if tile is not None:
            objs = self._objs[0]
            towns = {tuple(o["xy"]) for o in objs if o["kind"] == "town"}
            for i in held:
                objs[i]["xy"] = tuple(tile)
                if objs[i]["kind"] == "character":
                    objs[i]["in_town"] = tuple(tile) in towns
            laid = MM.build_each([objs[i] for i in held], self._objs[1], self.heights, 0.0005 * self.scale)
            for i, one in zip(held, laid):
                self._each[i] = one
            self.ghost = MM.join(laid)
        for tex, arr in self.ghost.items():
            if len(arr):
                have = self.objects.get(tex)
                self.objects[tex] = arr if have is None or not len(have) else np.concatenate([have, arr])
        self.ghost, self._held = {}, None
        return True

    def put_back(self):
        """What is in the hand back where it stood (Esc, a tile the game would not take)."""
        if getattr(self, "ghost", None):
            self.put_down()

    def _net(self, mod, campaign, strat):
        """The roads and region borders (mapnet): the towns' road buildings and the regions' owners from strat."""
        from . import mapnet as N
        from . import tilemodels as TM
        if getattr(self, "_net_src", None) is None:
            self.roads, self.borders, self.net_pictures = {}, np.zeros((0, 12), np.float32), {}
            grid, names = N.region_grid(mod, campaign)
            src = getattr(self, "_model_src", None)
            ground = src[0] if src else T3._picture(mod, campaign, "map_ground_types.tga")
            feats = src[1] if src else T3._picture(mod, campaign, "map_features.tga")
            H, W = grid.shape
            mh = TM.tile_types(ground)[TM.MOUNTAINS_HIGH] if ground is not None and \
                ground.shape[:2] == self.heights.shape else np.zeros((H, W), bool)
            rivers = _rivers(feats, H, W)
            regs = mod.regions(campaign)
            self._net_src = {"grid": grid, "names": names, "chains": N.road_chains(mod), "feats": feats,
                             "mountains": mh, "rivers": rivers, "towns": mod.city_tiles(campaign),
                             "creators": {k: v.get("creator") for k, v in regs.items()},
                             "colours": N.faction_colours(mod),
                             "skip": {k for k, v in regs.items() if v.get("wasteland")}}
            for name in ("road_dirt", "road_stone", "road_highway"):
                for tail in ("", "_T", "_X"):
                    rel = "terrain/aerial_map/roads/%s%s.tga" % (name, tail)
                    self.net_pictures[rel] = _image(mod, [rel], mode="RGBA")
            for part in ("primary", "secondary"):
                rel = "terrain/aerial_map/indicators/region_borders_%s.tga" % part
                self.net_pictures[rel] = _image(mod, [rel], mode="RGBA")
        src = self._net_src
        src["levels"] = N.road_levels(strat, src["chains"])
        src["owners"] = strat.owners()                  # laid by place_objects, which follows

    def place_net(self):
        """The roads (their tiles found again: the heights steer them) and borders laid on the heights."""
        from . import mapnet as N
        src = getattr(self, "_net_src", None)
        if not src or "levels" not in src:
            return
        ys = 0.0005 * self.scale
        try:
            steps = N.roads(src["grid"], src["names"], src["towns"], src["levels"], self.heights, src["feats"],
                            src["mountains"])
            self.roads = N.road_geometry(steps, self.heights, ys, src["rivers"])
            self.borders = N.border_geometry(src["grid"], src["names"], src["owners"], src["creators"],
                                             src["colours"], self.heights, ys, src["mountains"], src["rivers"],
                                             src["skip"])
        except Exception as e:                          # said in the bar, the map still drawn
            self.notes.append("the roads and borders are not drawn: %s" % e)

    def place_trees(self):
        """The trees placed again on the heights as they are now."""
        from . import maptrees as MT
        if not getattr(self, "_tree_src", None):
            return
        ground, climate, climates, winter = self._tree_src
        levels = MT.forest_levels(self.heights, ground)
        placed = MT.place(levels, climate, climates, winter)
        self.trees = {f: a for f, a in MT.instances(placed, self.heights, 0.0005 * self.scale).items()
                      if f in self.tree_models}

    def _masks(self, mod):
        """The game's blend masks (template_weights/weights*.tga, their red), all made one size; a plain fade from
        the corner when the mod has none."""
        from PIL import Image
        out = []
        for i in range(1, 33):
            a = _image(mod, ["terrain/aerial_map/template_weights/weights%d.tga" % i])
            if a is None:
                break
            out.append(np.asarray(Image.fromarray(a[..., 0]).resize((32, 32), Image.BILINEAR), np.uint8))
        if not out:
            y, x = np.mgrid[0:32, 0:32] / 31.0
            out.append((np.clip(1 - (x + y) / 2.0, 0, 1) * 255).astype(np.uint8))
            self.notes.append("no template_weights - the grounds blend in a plain fade")
        return out

    def tiles(self):
        """The map's size in tiles (across, up)."""
        return (self.cols - 1) / 2.0, (self.rows - 1) / 2.0

    def ground_height(self, x, z):
        """The ground's height (world units) at tile point (x east, z south - from the map's top), 0 on the sea."""
        c = int(round(min(max(x * 2, 0), self.cols - 1)))
        r = int(round(min(max(z * 2, 0), self.rows - 1)))
        return max(0.0, float(self.heights[r, c])) * 0.0005 * self.scale


COAST_TIGHT = 0.5                               # the slope the strips lean to: half a step along a cell side,
COAST_CORNER = 0.707                            # 0.707 across a corner (the engine's 'opposite' / 'adjacent')
WET_SAND = 0.2176                               # the wet sand's dimming (the engine's, in linear light)


def coast_line(heights, yscale, hidden=None):
    """The coast as the games trace it (aerial_map_coastline): where the ground crosses height 0 on every half-tile
    square of the points' grid - a square with two sides crossing gets one piece between them; one with all four (two
    land corners facing each other) gets two, cutting off its top-left and bottom-right corners, as the ground's own
    SW -> NE diagonal joins the other two. Pieces join into lines; each point of a line has a direction across the
    shore, pointing inland and up the slope, and its length along the line (the strips' pictures run along it, one
    repeat a tile). heights: metres (rows, cols), top row first; yscale: metres -> world units; hidden: tiles
    (rows // 2, cols // 2) where the game draws no strip (a river or a cliff there) - a point beside one is clear.
    Returns (vertices (n, 9) float32: x, y, z, direction x, y, z, length, side - two a point, side 0 the strip's
    inland edge, 1 its sea edge -, how much it shows (0 or 1); triangles (m,) uint32)."""
    h = np.asarray(heights, np.float64)
    rows, cols = h.shape
    empty = (np.zeros((0, 9), np.float32), np.zeros(0, np.uint32))
    if rows < 2 or cols < 2:
        return empty
    land = h > 0
    # where each side of a square crosses 0: across (r, c)-(r, c+1), down (r, c)-(r+1, c)
    with np.errstate(divide="ignore", invalid="ignore"):
        ta = np.clip(-h[:, :-1] / (h[:, 1:] - h[:, :-1]), 0.0, 1.0)
        td = np.clip(-h[:-1, :] / (h[1:, :] - h[:-1, :]), 0.0, 1.0)
    xa = land[:, :-1] != land[:, 1:]
    xd = land[:-1, :] != land[1:, :]
    na = rows * (cols - 1)
    ida = np.arange(na).reshape(rows, cols - 1)
    idd = na + np.arange((rows - 1) * cols).reshape(rows - 1, cols)
    ra, ca = np.nonzero(np.ones((rows, cols - 1), bool))
    rd, cd = np.nonzero(np.ones((rows - 1, cols), bool))
    px = np.concatenate([(ca + ta.ravel()) * 0.5, cd * 0.5])
    pz = np.concatenate([ra * 0.5, (rd + td.ravel()) * 0.5])
    slope = np.concatenate([np.abs(h[:, 1:] - h[:, :-1]).ravel(),
                            np.abs(h[1:, :] - h[:-1, :]).ravel()]) * yscale / 0.5
    top, bottom = np.where(xa[:-1], ida[:-1], -1), np.where(xa[1:], ida[1:], -1)
    left, right = np.where(xd[:, :-1], idd[:, :-1], -1), np.where(xd[:, 1:], idd[:, 1:], -1)
    sides = np.stack([top, right, bottom, left], -1)          # (rows-1, cols-1, 4), clockwise from the top
    count = (sides >= 0).sum(-1)
    sign = np.where(land, 1.0, -1.0)
    cell = (sign[:-1, :-1], sign[:-1, 1:], sign[1:, :-1], sign[1:, 1:])
    two = count == 2
    s2 = sides[two]                                # the two crossed sides of each square, in clockwise order
    order = np.argsort(s2 < 0, axis=1, kind="stable")[:, :2]
    a2 = np.take_along_axis(s2, order, 1)
    k2 = np.where(order[:, 1] - order[:, 0] == 2, COAST_TIGHT, COAST_CORNER)
    tl, tr, bl, br = (c[two] for c in cell)
    four = count == 4
    s4 = sides[four]
    t4, b4 = cell[0][four], cell[3][four]
    # (side a, side b, the way inland x / z, slope factor) of every piece; a 4-crossing square's two pieces cut off
    # its top-left and bottom-right corners
    a = np.concatenate([a2[:, 0], s4[:, 0], s4[:, 2]])
    b = np.concatenate([a2[:, 1], s4[:, 3], s4[:, 1]])
    vx = np.concatenate([tr + br - tl - bl, -t4, b4])
    vz = np.concatenate([bl + br - tl - tr, -t4, b4])
    k = np.concatenate([k2, np.full(len(s4) * 2, COAST_CORNER)])
    if not len(a):
        return empty
    r2, c2 = np.nonzero(two)
    r4, c4 = np.nonzero(four)
    shown = np.ones(len(a))
    if hidden is not None and hidden.shape == ((rows - 1) // 2, (cols - 1) // 2):
        pr, pc = np.concatenate([r2, r4, r4]) // 2, np.concatenate([c2, c4, c4]) // 2
        shown = np.where(hidden[np.minimum(pr, hidden.shape[0] - 1), np.minimum(pc, hidden.shape[1] - 1)], 0.0, 1.0)
    dx, dz = px[b] - px[a], pz[b] - pz[a]
    flip = -dz * vx + dx * vz < 0                  # walk with the land on the same hand everywhere
    a, b = np.where(flip, b, a), np.where(flip, a, b)
    dx, dz = np.where(flip, -dx, dx), np.where(flip, -dz, dz)
    n = np.maximum(np.hypot(dx, dz), 1e-9)
    d = np.stack([-dz / n, k * (slope[a] + slope[b]), dx / n], 1)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    seg_from, seg_to = a.tolist(), b.tolist()
    starts = {e: i for i, e in enumerate(seg_from)}
    nxt = [starts.get(e, -1) for e in seg_to]
    has_prev = [False] * len(nxt)
    for j in nxt:
        if j >= 0:
            has_prev[j] = True
    used = [False] * len(nxt)
    pts, dirs, lines = [], [], []                  # every line's points (crossing ids) and their segments

    def chain(first):
        line, i = [], first
        while i >= 0 and not used[i]:
            used[i] = True
            line.append(i)
            i = nxt[i]
        closed = i == first
        start = len(pts)
        pts.append(seg_from[line[0]])
        dirs.append((line[-1] if closed else line[0], line[0]))
        for x, y in zip(line, line[1:]):
            pts.append(seg_to[x])
            dirs.append((x, y))
        pts.append(seg_to[line[-1]])
        dirs.append((line[-1], line[0]) if closed else (line[-1], line[-1]))
        lines.append((start, len(pts)))

    for i in range(len(nxt)):                      # open lines from their heads, then the closed ones (islands)
        if not has_prev[i] and not used[i]:
            chain(i)
    for i in range(len(nxt)):
        if not used[i]:
            chain(i)
    p = np.asarray(pts)
    j = np.asarray(dirs)
    pd = d[j[:, 0]] + d[j[:, 1]]                   # at a joint the two pieces' directions meet half way
    pd /= np.maximum(np.linalg.norm(pd, axis=1, keepdims=True), 1e-9)
    step = np.hypot(np.diff(px[p]), np.diff(pz[p]))
    u = np.concatenate([[0.0], np.cumsum(step)])
    first = np.zeros(len(p), bool)
    for s, e in lines:
        first[s] = True
    u -= np.maximum.accumulate(np.where(first, u, 0.0))      # each line's length from its own start
    alpha = np.minimum(shown[j[:, 0]], shown[j[:, 1]])     # a joint shows only when both its pieces do
    one = np.stack([px[p], np.zeros(len(p)), pz[p], pd[:, 0], pd[:, 1], pd[:, 2], u], 1)
    verts = np.repeat(one, 2, 0)
    verts = np.concatenate([verts, np.tile([[0.0], [1.0]], (len(p), 1)), np.repeat(alpha, 2)[:, None]], 1)
    q = np.concatenate([np.arange(s, e - 1) for s, e in lines]) * 2
    tris = np.stack([q, q + 1, q + 2, q + 2, q + 1, q + 3], 1).ravel()
    return verts.astype(np.float32), tris.astype(np.uint32)


def coast_strips(t):
    """The coast's five strips at time t (0..1, a wave every 5 seconds - the engine's coastline): the beach (a fixed
    strip 0.15 tile either side of the shore), two of wet sand and two of surf, each pair half a wave apart, sliding
    in from the sea and fading. [(picture 'beach' / 'surf', inland edge, sea edge (tiles along the direction),
    alpha, brightness)]."""
    def travel(x):                                 # the engine's distance_t: starts slow, speeds up
        return (0.25 + 0.75 * x) * x
    size, distance, start = 0.3, 0.225, -0.4
    out = [("beach", 0.15, -0.15, 1.0, 1.0)]
    for shift in (0.0, 0.5):
        dt = (t + shift) % 1.0
        if dt < 0.8:
            low, alpha = start + distance * travel(dt), dt / 0.8 * 0.5
        else:
            low, alpha = start + distance * travel(0.8 - (dt - 0.8) * 0.5), (1.0 - (dt - 0.8) / 0.2) * 0.5
        out.append(("surf", low + size, low, alpha, WET_SAND))
    for shift in (0.0, 0.5):
        dt = (t + shift) % 1.0
        alpha = math.sin(dt / 0.25 * math.pi / 2) if dt < 0.25 else 1.0 if dt < 0.75 else 1.0 - (dt - 0.75) / 0.25
        low = start + distance * travel(dt)
        out.append(("surf", low + size, low, alpha, 1.0))
    return out


COLOUR_GLSL = """
uniform int linear;
uniform float exposure;
vec3 dec(vec3 c) { return linear == 1 ? pow(c, vec3(2.2)) : c; }
vec3 enc(vec3 c) {
    if (linear == 0) return c;
    c = max(c * exposure, vec3(0.0));
    c = mix(c, 0.9 + 0.1 * (1.0 - exp(-(c - 0.9) / 0.1)), step(vec3(0.9), c));
    return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}
"""

TERRAIN_VS = """
#version 330
uniform sampler2D heights;
uniform sampler2D lift;                 // the ground raised to meet a tile model's edge (a cliff's top)
uniform mat4 mvp;
uniform float yscale;
uniform ivec2 size;
in vec2 grid;
out vec2 g;
out vec3 n;
flat out float kind_v;
float h(ivec2 p) { return texelFetch(heights, clamp(p, ivec2(0), size - 1), 0).r * yscale; }
void main() {
    ivec2 p = ivec2(grid);
    float y = h(p) + texelFetch(lift, p, 0).r;
    n = normalize(vec3(-(h(p + ivec2(1, 0)) - h(p - ivec2(1, 0))) * 0.5, 0.5,
                       -(h(p + ivec2(0, 1)) - h(p - ivec2(0, 1))) * 0.5));
    g = grid;
    kind_v = 0.0;
    gl_Position = mvp * vec4(grid.x * 0.5, y, grid.y * 0.5, 1.0);
}
"""

UNDER_VS = """
#version 330
uniform mat4 mvp;
in vec3 pos;
in vec3 nrm;
in float kind;
out vec2 g;
out vec3 n;
flat out float kind_v;
void main() { g = pos.xz * 2.0; n = nrm; kind_v = kind; gl_Position = mvp * vec4(pos, 1.0); }
"""

# colours laid over the map to see what is painted (Maps > 3D: the climates - on the water too -, the regions): one
# texel a tile, top row first; its alpha how much it shows
TINT_GLSL = """
uniform sampler2D tint;
uniform int tinted;
vec3 tinted_by(vec3 c, vec2 tile) {
    if (tinted == 0) return c;
    ivec2 ts = textureSize(tint, 0);
    vec4 t = texelFetch(tint, clamp(ivec2(floor(tile)), ivec2(0), ts - 1), 0);
    return mix(c, dec(t.rgb), t.a * 0.55);
}
"""

TERRAIN_FS = """
#version 330
""" + COLOUR_GLSL + TINT_GLSL + """
uniform vec3 to_light;
uniform vec3 ambient;
uniform vec3 diffuse;
uniform usampler2D layers;
uniform sampler2DArray ground;
uniform sampler2DArray masks;
uniform int nmasks;
uniform ivec2 size;
uniform float rep[64];
uniform usampler2D voids;
uniform int mode;                       // 0 the ground, 1 a tile model's ground-dressed part
uniform int shown;                      // bit k: the models of kind k shown (their tiles' ground left out)
in vec2 g;
in vec3 n;
flat in float kind_v;
out vec4 colour;
uint mix3(uint a, uint b, uint c) {
    uint x = a * 73856093u ^ b * 19349663u ^ c * 83492791u;
    x ^= x >> 13; x *= 0x5bd1e995u; x ^= x >> 15;
    return x;
}
vec2 tdx, tdy;
// the picture's mip level from slopes taken once, before any discard or branch: a texture() inside them has no
// sure slope where a 2 x 2 pixel block straddles a half-tile's edge - some cards then drew a thin pale line along
// the edges of blended half-tiles and of tile models' tiles (a tester: faint squares on the ground)
vec3 pic(uint l, vec2 t) { return dec(textureGrad(ground, vec3(t * rep[l], float(l)), tdx * rep[l], tdy * rep[l]).rgb); }
void main() {
    tdx = dFdx(g * 0.5);
    tdy = dFdy(g * 0.5);
    if (mode == 0) {
        ivec2 vs = textureSize(voids, 0);
        uint k = texelFetch(voids, clamp(ivec2(floor(g * 0.5)), ivec2(0), vs - 1), 0).r;
        if (k > 0u && ((shown >> int(k)) & 1) == 1) discard;     // a tile model stands here: its ground instead
    } else if (((shown >> int(kind_v + 0.5)) & 1) == 0) {
        discard;
    }
    ivec2 c = clamp(ivec2(floor(g)), ivec2(0), size - 2);
    vec2 f = clamp(g - vec2(c), 0.0, 1.0);
    uint l0 = texelFetch(layers, c, 0).r;
    uint l1 = texelFetch(layers, c + ivec2(1, 0), 0).r;
    uint l2 = texelFetch(layers, c + ivec2(0, 1), 0).r;
    uint l3 = texelFetch(layers, c + ivec2(1, 1), 0).r;
    vec2 t = g * 0.5;
    vec3 col;
    if (l0 == l1 && l0 == l2 && l0 == l3) {
        col = pic(l0, t);
    } else {
        uint v = mix3(uint(c.x), uint(c.y), 7u) % 8u;
        float k = 31.0 / 32.0, o = 0.5 / 32.0;
        float w0 = texture(masks, vec3(f * k + o, float(mix3(uint(c.x), uint(c.y), v * 4u) % uint(nmasks)))).r;
        float w1 = texture(masks, vec3(vec2(1.0 - f.x, f.y) * k + o,
                                       float(mix3(uint(c.x), uint(c.y), v * 4u + 1u) % uint(nmasks)))).r;
        float w2 = texture(masks, vec3(vec2(f.x, 1.0 - f.y) * k + o,
                                       float(mix3(uint(c.x), uint(c.y), v * 4u + 2u) % uint(nmasks)))).r;
        float w3 = texture(masks, vec3((1.0 - f) * k + o,
                                       float(mix3(uint(c.x), uint(c.y), v * 4u + 3u) % uint(nmasks)))).r;
        float sum = max(w0 + w1 + w2 + w3, 1e-4);
        col = (pic(l0, t) * w0 + pic(l1, t) * w1 + pic(l2, t) * w2 + pic(l3, t) * w3) / sum;
    }
    col = tinted_by(col, g * 0.5);
    vec3 light = ambient + diffuse * max(dot(normalize(n), to_light), 0.0);
    colour = vec4(enc(col * (linear == 1 ? light : min(light, vec3(1.0)))), 1.0);
}
"""

OVER_VS = """
#version 330
uniform mat4 mvp;
in vec3 pos;
in vec3 nrm;
in vec2 uv;
in vec2 auv;
in vec4 col;
in float kind;
out vec3 n;
out vec2 t;
out vec2 at;
out vec4 c;
flat out float kind_v;
void main() { n = nrm; t = uv; at = auv; c = col; kind_v = kind; gl_Position = mvp * vec4(pos, 1.0); }
"""

OVER_FS = """
#version 330
""" + COLOUR_GLSL + """
uniform vec3 to_light;
uniform vec3 ambient;
uniform vec3 diffuse;
uniform sampler2D pic;
uniform sampler2D mask;
uniform int shown;
in vec3 n;
in vec2 t;
in vec2 at;
in vec4 c;
flat in float kind_v;
out vec4 colour;
void main() {
    if (((shown >> int(kind_v + 0.5)) & 1) == 0) discard;
    vec4 p = texture(pic, t);
    float a = c.a < 0.0 ? texture(mask, at).a : p.a * c.a;      // the mountains' alpha page, else the picture's
    if (a < 0.02) discard;
    vec3 light = ambient + diffuse * max(dot(normalize(n), to_light), 0.0);
    colour = vec4(enc(dec(p.rgb) * c.rgb * (linear == 1 ? light : min(light, vec3(1.0)))), a);
}
"""

TREE_VS = """
#version 330
uniform mat4 mvp;
uniform float sheers[20];
in vec3 pos;
in vec3 nrm;
in vec2 uv;
in vec4 inst;                           // where the tree stands (x y z) and its sheer slot
out vec3 n;
out vec2 t;
void main() {
    float s = sheers[int(inst.w + 0.5)];
    vec3 p = pos + inst.xyz;
    p.x += pos.y * s;                   // the engine's lean in the wind: the higher, the farther
    n = vec3(nrm.x + nrm.y * s, nrm.yz);
    t = uv;
    gl_Position = mvp * vec4(p, 1.0);
}
"""

OBJ_VS = """
#version 330
uniform mat4 mvp;
uniform vec3 shift;                     // what is carried: where the mouse took it, from where it stood
in vec3 pos;
in vec3 nrm;
in vec2 uv;
in float kind;
out vec3 n;
out vec2 t;
flat out float kind_v;
void main() { n = nrm; t = uv; kind_v = kind; gl_Position = mvp * vec4(pos + shift, 1.0); }
"""

OBJ_FS = """
#version 330
""" + COLOUR_GLSL + """
uniform vec3 to_light;
uniform vec3 ambient;
uniform vec3 diffuse;
uniform sampler2D pic;
uniform int shown;
in vec3 n;
in vec2 t;
flat in float kind_v;
out vec4 colour;
void main() {
    if (((shown >> int(kind_v + 0.5)) & 1) == 0) discard;
    vec4 p = texture(pic, t);
    if (p.a < 0.5) discard;
    vec3 light = ambient + diffuse * abs(dot(normalize(n), to_light));
    colour = vec4(enc(dec(p.rgb) * (linear == 1 ? light : min(light, vec3(1.0)))), 1.0);
}
"""

ROAD_VS = """
#version 330
uniform mat4 mvp;
in vec3 pos;
in vec2 uv;
in float alpha;
out vec2 t;
out float a;
void main() { t = uv; a = alpha; gl_Position = mvp * vec4(pos, 1.0); }
"""

ROAD_FS = """
#version 330
""" + COLOUR_GLSL + """
uniform vec3 to_light;
uniform vec3 ambient;
uniform vec3 diffuse;
uniform sampler2D pic;
in vec2 t;
in float a;
out vec4 colour;
void main() {                           // the engine's ribbon: the picture under the sun, see-through as it is
    vec4 p = texture(pic, t);
    vec3 light = ambient + diffuse * max(to_light.y, 0.0);
    colour = vec4(enc(dec(p.rgb) * (linear == 1 ? light : min(light, vec3(1.0)))), p.a * a);
}
"""

BORDER_VS = """
#version 330
uniform mat4 mvp;
in vec3 pos;
in vec2 uv;
in float alpha;
in vec3 c1;
in vec3 c2;
out vec2 t;
out float a;
out vec3 k1;
out vec3 k2;
void main() { t = uv; a = alpha; k1 = c1; k2 = c2; gl_Position = mvp * vec4(pos, 1.0); }
"""

BORDER_FS = """
#version 330
""" + COLOUR_GLSL + """
uniform sampler2D pri;
uniform sampler2D sec;
in vec2 t;
in float a;
in vec3 k1;
in vec3 k2;
out vec4 colour;
void main() {                           // the engine's border: the owner's two colours, unlit, one over the other
    vec4 p = texture(pri, t);
    vec4 s = texture(sec, t);
    float pa = p.a * a;
    float sa = s.a * a * (1.0 - pa);
    vec3 rgb = dec(p.rgb * k1) * pa + dec(s.rgb * k2) * sa;
    float oa = pa + sa;
    colour = vec4(oa > 0.0 ? enc(rgb / oa) * oa : vec3(0.0), oa);     // premultiplied
}
"""

TREE_FS = """
#version 330
""" + COLOUR_GLSL + """
uniform vec3 to_light;
uniform vec3 ambient;
uniform vec3 diffuse;
uniform sampler2D pic;
in vec3 n;
in vec2 t;
out vec4 colour;
void main() {
    vec4 p = texture(pic, t);
    if (p.a < 0.5) discard;             // the leaves cut out of their squares
    vec3 light = ambient + diffuse * max(dot(n, to_light), 0.0);
    colour = vec4(enc(dec(p.rgb) * (linear == 1 ? light : min(light, vec3(1.0)))), 1.0);
}
"""

SEA_VS = """
#version 330
uniform mat4 mvp;
in vec2 pos;
out vec2 w;
void main() { w = pos; gl_Position = mvp * vec4(pos.x, 0.0, pos.y, 1.0); }
"""

SEA_GLSL = COLOUR_GLSL + """
uniform sampler2D water;
uniform sampler2D waves;
uniform sampler2D sky;
uniform vec2 tiles;
uniform vec3 sea_light;
uniform vec3 eye;
uniform float waves_mean;
vec3 sea(vec2 w) {                      // the open water's colour at world point w (linear when the light is)
    vec3 c = dec(texture(water, w / tiles).rgb) * sea_light;
    float wave = dec(texture(waves, w * 0.25).rgb).r;
    c *= linear == 1 ? wave : wave / max(waves_mean, 0.05);    // the old games: the waves around their own mean
    vec2 r = (w + (eye.xz - w) * 0.15) / 32.0;
    return mix(c, dec(texture(sky, r).rgb), 0.5);
}
"""

SEA_FS = """
#version 330
""" + SEA_GLSL + TINT_GLSL + """
out vec4 colour;
in vec2 w;
void main() { colour = vec4(enc(tinted_by(sea(w), w)), 1.0); }
"""

RIVER_VS = """
#version 330
uniform mat4 mvp;
in vec3 pos;
in vec2 uv;
in float kind;
out vec2 w;
out vec2 t;
out float y;
flat out float kind_v;
void main() { w = pos.xz; t = uv; y = pos.y; kind_v = kind; gl_Position = mvp * vec4(pos, 1.0); }
"""

RIVER_FS = """
#version 330
""" + SEA_GLSL + """
uniform sampler2D flow;
uniform float shift;
uniform int shown;
in vec2 w;
in vec2 t;
in float y;
flat in float kind_v;
out vec4 colour;
void main() {                           // a river's water: the open water's look, its flow over it at a quarter
    if (((shown >> int(kind_v + 0.5)) & 1) == 0) discard;
    vec3 f = dec(texture(flow, t + vec2(shift, 0.0)).rgb) * sea_light;
    colour = vec4(enc(mix(sea(w), f, 0.25)), clamp(y * 10.0, 0.0, 1.0));     // fading out at the sea's level
}
"""


COAST_VS = """
#version 330
uniform mat4 mvp;
uniform vec2 edges;
in vec3 pos;
in vec3 dir;
in vec2 uv;
in float shown;
out vec2 t;
out float a;
void main() {
    t = vec2(uv.x, uv.y * 0.95);
    a = shown;
    gl_Position = mvp * vec4(pos + dir * (uv.y < 0.5 ? edges.x : edges.y), 1.0);
}
"""

COAST_FS = """
#version 330
""" + COLOUR_GLSL + """
uniform sampler2D strip;
uniform vec4 tint;
in vec2 t;
in float a;
out vec4 colour;
void main() {
    vec4 c = texture(strip, t);
    colour = vec4(enc(dec(c.rgb) * tint.rgb), c.a * tint.a * a);
}
"""


def look_at(eye, target, up=(0.0, 1.0, 0.0)):
    eye, target, up = (np.asarray(v, np.float64) for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= max(np.linalg.norm(s), 1e-9)
    u = np.cross(s, f)
    m = np.identity(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1.0
    return m


class Camera:
    """The game's camera: it looks at a point of the map (x east, z south - tiles from the map's top-left corner)
    from dist tiles away, turned yaw (0 = looking north) and tilted down pitch (radians; the game's default 53
    degrees), 45 degrees of view. (x east, y up, z south: OpenGL's right-handed world.)"""
    FOV = 45.0

    def __init__(self, data):
        cols, rows = data.tiles()
        self.x, self.z = cols / 2.0, rows / 2.0
        self.yaw = 0.0
        self.pitch = math.radians(53.13)
        self.far_limit = max(cols, rows) * 1.6
        self.dist = self.far_limit * 0.6

    def eye(self, ground=0.0):
        cp = math.cos(self.pitch)
        return (self.x - math.sin(self.yaw) * cp * self.dist, ground + math.sin(self.pitch) * self.dist,
                self.z + math.cos(self.yaw) * cp * self.dist)

    def moved(self, forward, right):
        """forward: tiles the way the camera looks (along the ground), right: to its right."""
        s, c = math.sin(self.yaw), math.cos(self.yaw)
        self.x += forward * s + right * c
        self.z += -forward * c + right * s

    def zoom(self, factor):
        self.dist = min(self.far_limit, max(1.5, self.dist * factor))

    def matrix(self, w, h, ground=0.0):
        eye = self.eye(ground)
        view = look_at(eye, (self.x, ground, self.z))
        proj = perspective(self.FOV, w / float(max(h, 1)), max(0.05, self.dist * 0.01), self.dist * 4 + 50)
        return (proj @ view).astype(np.float32), eye


class TopCamera(Camera):
    """Straight down on the whole map, no perspective (a map's picture: the faction-select map) - the same
    attributes as Camera for render()."""

    def __init__(self, data):
        super().__init__(data)
        self.cols, self.rows = data.tiles()
        self.pitch = math.pi / 2

    def matrix(self, w, h, ground=0.0):
        cx, cz, hw, hh = self.cols / 2.0, self.rows / 2.0, self.cols / 2.0, self.rows / 2.0
        depth = 400.0                                    # world heights stay within +-200 (a few units in truth)
        m = np.array([[1.0 / hw, 0.0, 0.0, -cx / hw],
                      [0.0, 0.0, -1.0 / hh, cz / hh],     # z runs south: down the picture
                      [0.0, -2.0 / depth, 0.0, 0.0],      # higher ground nearer
                      [0.0, 0.0, 0.0, 1.0]])
        return m.astype(np.float32), (cx, 1000.0, cz)


def top_picture(mod, campaign, width, winter=False, sea=True):
    """The whole campaign map seen straight down as the graphics card draws the 3D map - the game's ground textures,
    relief, rivers, mountains, trees, the sea - no towns, armies, roads or borders: (h, w, 3) uint8, the map's shape,
    `width` wide. None when the card cannot draw (available()). sea=False: the sea floor (a picture painting its own
    sea over it). The user, 2026-10-18: the faction-select map drawn by hand came out in two or three colours - the
    3D map's own picture of it."""
    if not available()[0]:
        return None
    data = MapData(mod, campaign, winter=winter)
    cols, rows = data.tiles()
    w = int(width)
    h = max(16, int(round(w * rows / float(max(cols, 1)))))
    gl = GLMap(data)
    try:
        cam = TopCamera(data)
        show = {k: False for k in ("roads", "borders", "towns", "resources", "armies")}
        show["sea"] = bool(sea)
        return gl.render(cam, w, h, show=show)
    finally:
        gl.release()


class GLMap:
    """The map on the card: made from MapData, then render(camera, w, h) -> (h, w, 3) uint8 picture as many times
    as the view moves. set_heights / set_layers change part of what the card holds (the brushes, live)."""

    def __init__(self, data):
        ctx = context()
        if ctx is None:
            raise RuntimeError(_why or "no OpenGL")
        self.ctx, self.data = ctx, data
        self._gone = []
        rows, cols = data.rows, data.cols
        self.heights = self._keep(ctx.texture((cols, rows), 1, data.heights.tobytes(), dtype="f4"))
        self.heights.filter = (ctx.NEAREST, ctx.NEAREST)
        self.layers = self._keep(ctx.texture((cols, rows), 1, data.layers.tobytes(), dtype="u2"))
        self.layers.filter = (ctx.NEAREST, ctx.NEAREST)          # whole numbers: never blended
        n = len(data.pictures)
        self.ground = self._keep(ctx.texture_array((LAYER, LAYER, n), 3, np.stack(data.pictures).tobytes()))
        self.ground.build_mipmaps()
        self.ground.filter = (ctx.LINEAR_MIPMAP_LINEAR, ctx.LINEAR)
        self.ground.repeat_x = self.ground.repeat_y = True
        try:
            self.ground.anisotropy = 8.0
        except Exception:
            pass
        self.masks = self._keep(ctx.texture_array((32, 32, len(data.masks)), 1, np.stack(data.masks).tobytes()))
        self.masks.repeat_x = self.masks.repeat_y = False
        self.water = self._picture(data.water, 3, (40, 70, 110))
        self.waves = self._picture(data.waves, 4, (128, 128, 128, 255), repeat=True)
        self.sky = self._picture(data.sky, 3, (150, 170, 190), repeat=True)
        self.terrain = self._keep(ctx.program(vertex_shader=TERRAIN_VS, fragment_shader=TERRAIN_FS))
        self.under = self._keep(ctx.program(vertex_shader=UNDER_VS, fragment_shader=TERRAIN_FS))
        self.over = self._keep(ctx.program(vertex_shader=OVER_VS, fragment_shader=OVER_FS))
        self.tree = self._keep(ctx.program(vertex_shader=TREE_VS, fragment_shader=TREE_FS))
        self.obj = self._keep(ctx.program(vertex_shader=OBJ_VS, fragment_shader=OBJ_FS))
        self.obj_pics = {k: self._picture(v, 4, (150, 140, 120, 255), repeat=True)
                         for k, v in data.object_pictures.items()}
        self._obj_buffers, self.obj_vaos, self.ghost_vaos, self.ghost_shift = [], [], [], (0.0, 0.0, 0.0)
        self.road = self._keep(ctx.program(vertex_shader=ROAD_VS, fragment_shader=ROAD_FS))
        self.border = self._keep(ctx.program(vertex_shader=BORDER_VS, fragment_shader=BORDER_FS))
        self.net_pics = {}
        for k, v in getattr(data, "net_pictures", {}).items():
            if v is not None:
                t = self._picture(v, 4, (0, 0, 0, 0), repeat=True)
                t.repeat_y = False                             # across a ribbon: held at its edges
                self.net_pics[k] = t
        self._net_buffers, self.road_vaos, self.border_vao = [], [], None
        self.tree_pics = {k: self._picture(v, 4, (60, 90, 50, 255), repeat=True)
                          for k, v in data.tree_pictures.items()}
        self._tree_buffers, self.tree_vaos = [], []
        self.river = self._keep(ctx.program(vertex_shader=RIVER_VS, fragment_shader=RIVER_FS))
        self.flow = self._picture(data.river_flow, 3, (60, 90, 120), repeat=True)
        self.sea = self._keep(ctx.program(vertex_shader=SEA_VS, fragment_shader=SEA_FS))
        self._model_buffers, self.voids = [], None
        self.model_pics = {k: self._picture(v, 4, (128, 120, 110, 255), repeat=True)
                           for k, v in data.model_pictures.items()}
        self.model_masks = {k: self._picture(v, 4, (255, 255, 255, 255)) for k, v in data.model_masks.items()}
        self._white = self._picture(None, 4, (255, 255, 255, 255))
        H, W = (rows - 1) // 2, (cols - 1) // 2
        self.tint = self._keep(ctx.texture((max(1, W), max(1, H)), 4, bytes(max(1, W) * max(1, H) * 4)))
        self.tint.filter = (ctx.NEAREST, ctx.NEAREST)            # a tile's own colour, its edges sharp
        # the grid: one point per heights pixel, two triangles a half-tile square along its SW -> NE diagonal
        gy, gx = np.mgrid[0:rows, 0:cols].astype(np.float32)
        pts = np.stack([gx.ravel(), gy.ravel()], 1)
        i = np.arange(rows * cols, dtype=np.uint32).reshape(rows, cols)
        tl, tr, bl, br = i[:-1, :-1], i[:-1, 1:], i[1:, :-1], i[1:, 1:]
        tri = np.stack([tl, bl, tr, tr, bl, br], -1).ravel().astype(np.uint32)
        vbo = self._keep(ctx.buffer(pts.tobytes()))
        ibo = self._keep(ctx.buffer(tri.tobytes()))
        self.vao = self._keep(ctx.vertex_array(self.terrain, [(vbo, "2f", "grid")], ibo, index_element_size=4))
        tc, tr_ = data.tiles()
        quad = np.array([[0, 0], [tc, 0], [0, tr_], [tc, tr_]], np.float32)
        qbo = self._keep(ctx.buffer(quad.tobytes()))
        self.sea_vao = self._keep(ctx.vertex_array(self.sea, [(qbo, "2f", "pos")]))
        self.coast = self._keep(ctx.program(vertex_shader=COAST_VS, fragment_shader=COAST_FS))
        self.strips = {"beach": self._picture(data.beach, 4, (0, 0, 0, 0), repeat=True),
                       "surf": self._picture(data.surf, 4, (0, 0, 0, 0), repeat=True)}
        for t in self.strips.values():
            t.repeat_y = False
        self.coast["strip"].value = 7
        self.coast_vao, self._coast_buffers, self.coast_dirty = None, [], True
        self.fbo, self.fbo_size, self.last = None, None, None
        L = data.light
        d = np.asarray(L["direction"], np.float64) * (1.0, 1.0, -1.0)    # the game's z runs north, ours south
        to_light = -d / max(np.linalg.norm(d), 1e-9)
        s = np.asarray(SEA_LIGHT, np.float64)
        s /= np.linalg.norm(s)
        lin = bool(L.get("linear"))
        top = np.inf if lin else 1.0                # linear light is not cut at 1 (the shoulder bends it at the end)
        sea_l = np.minimum(np.asarray(L["ambient"]) + np.asarray(L["diffuse"]) * max(float(s[1]), 0.0), top)
        self.linear = lin
        for prog in (self.terrain, self.under, self.over, self.sea, self.coast, self.river, self.tree, self.obj,
                     self.road, self.border):
            prog["linear"].value = int(lin)
            prog["exposure"].value = float(L.get("exposure", 1.0))
        for prog in (self.terrain, self.under, self.over, self.tree, self.obj, self.road):   # one light on the land
            for name, value in (("to_light", tuple(to_light)), ("ambient", L["ambient"]), ("diffuse", L["diffuse"])):
                prog[name].value = value
        for prog in (self.terrain, self.under):              # the tile models' plain parts wear the ground's pictures
            prog["size"].value = (cols, rows)
            prog["rep"].value = tuple(data.repeat[:64]) + (1.0,) * (64 - min(64, len(data.repeat)))
            prog["nmasks"].value = len(data.masks)
            for name, unit in (("heights", 0), ("layers", 1), ("ground", 2), ("masks", 3), ("voids", 8), ("lift", 12)):
                if name in prog:
                    prog[name].value = unit
            prog["mode"].value = 0 if prog is self.terrain else 1
        for prog in (self.terrain, self.under, self.sea):
            if "tint" in prog:
                prog["tint"].value = 13
            if "tinted" in prog:
                prog["tinted"].value = 0
        self.over["pic"].value, self.over["mask"].value = 9, 10
        self.tree["pic"].value = 9
        self.obj["pic"].value = 9
        self.road["pic"].value = 9
        self.border["pri"].value, self.border["sec"].value = 9, 10
        self.models_stale = False
        self._models()
        self._trees()
        self._objects()
        self._net()
        for prog in (self.sea, self.river):             # the rivers' water looks like the open water
            prog["tiles"].value = (tc, tr_)
            prog["sea_light"].value = tuple(float(v) for v in sea_l)
            prog["waves_mean"].value = float(data.waves[..., 0].mean()) / 255.0 if data.waves is not None else 0.5
            for name, unit in (("water", 4), ("waves", 5), ("sky", 6)):
                prog[name].value = unit
        self.river["flow"].value = 11
        # the strips are lit as flat ground facing up (the engine's coastline shader)
        self.strip_light = np.minimum(np.asarray(L["ambient"]) + np.asarray(L["diffuse"]) * max(float(to_light[1]), 0.0),
                                      top)

    def _keep(self, obj):
        self._gone.append(obj)
        return obj

    def _models(self):
        """The tile models' buffers (and the tiles whose ground gives way to them) from data.models."""
        for obj in self._model_buffers:
            obj.release()
        self._model_buffers, self.model_vaos = [], []
        ctx, d = self.ctx, self.data
        v = np.ascontiguousarray(d.voids)
        self.voids = ctx.texture((v.shape[1], v.shape[0]), 1, v.tobytes(), dtype="u1")
        self.voids.filter = (ctx.NEAREST, ctx.NEAREST)
        lift = d.models.get("lift")
        if lift is None or lift.shape != (d.rows, d.cols):
            lift = np.zeros((d.rows, d.cols), np.float32)
        self.lift = ctx.texture((d.cols, d.rows), 1, np.ascontiguousarray(lift, np.float32).tobytes(), dtype="f4")
        self.lift.filter = (ctx.NEAREST, ctx.NEAREST)
        self._model_buffers += [self.voids, self.lift]
        under = d.models["under"]
        if len(under):
            vbo = ctx.buffer(np.ascontiguousarray(under).tobytes())
            vao = ctx.vertex_array(self.under, [(vbo, "3f 3f 1f", "pos", "nrm", "kind")])
            self._model_buffers += [vbo, vao]
            self.model_vaos.append(("under", None, None, vao))
        water = d.models.get("water")
        if water is not None and len(water):
            vbo = ctx.buffer(np.ascontiguousarray(water).tobytes())
            vao = ctx.vertex_array(self.river, [(vbo, "3f 2f 1f", "pos", "uv", "kind")])
            self._model_buffers += [vbo, vao]
            self.model_vaos.append(("water", None, None, vao))
        for (tex, page), arr in d.models["over"].items():
            vbo = ctx.buffer(np.ascontiguousarray(arr).tobytes())
            vao = ctx.vertex_array(self.over, [(vbo, "3f 3f 2f 2f 4f 1f", "pos", "nrm", "uv", "auv", "col", "kind")])
            self._model_buffers += [vbo, vao]
            self.model_vaos.append(("over", tex, page, vao))

    def refresh_models(self):
        """The tile models laid again on the heights as the brushes left them (after a stroke: placing them takes
        a moment, so not at every puff). gui_map3d places them in a thread (data.place_models) and calls
        models_placed() on the main thread; this does both at once."""
        if self.models_stale:
            self.models_stale = False
            self.data.place_models()
            self.models_placed()

    def models_placed(self):
        """data.models changed (placed again): the card takes them."""
        self._models()
        self._trees()
        self._objects()
        self._net()

    def _net(self):
        """The roads' and borders' buffers."""
        for obj in self._net_buffers:
            obj.release()
        self._net_buffers, self.road_vaos, self.border_vao = [], [], None
        for tex, arr in getattr(self.data, "roads", {}).items():
            if len(arr):
                vbo = self.ctx.buffer(np.ascontiguousarray(arr).tobytes())
                vao = self.ctx.vertex_array(self.road, [(vbo, "3f 2f 1f", "pos", "uv", "alpha")])
                self._net_buffers += [vao, vbo]
                self.road_vaos.append((tex, vao))
        b = getattr(self.data, "borders", None)
        if b is not None and len(b):
            vbo = self.ctx.buffer(np.ascontiguousarray(b).tobytes())
            self.border_vao = self.ctx.vertex_array(self.border, [(vbo, "3f 2f 1f 3f 3f", "pos", "uv", "alpha",
                                                                    "c1", "c2")])
            self._net_buffers += [self.border_vao, vbo]

    def _objects(self):
        """The buffers of what stands on the map, one per texture - and of what is carried (data.ghost)."""
        for obj in self._obj_buffers:
            obj.release()
        self._obj_buffers, self.obj_vaos, self.ghost_vaos = [], [], []
        for store, out in ((self.data.objects, self.obj_vaos), (getattr(self.data, "ghost", {}) or {}, self.ghost_vaos)):
            for tex, arr in store.items():
                if not len(arr):
                    continue
                vbo = self.ctx.buffer(np.ascontiguousarray(arr).tobytes())
                vao = self.ctx.vertex_array(self.obj, [(vbo, "3f 3f 2f 1f", "pos", "nrm", "uv", "kind")])
                self._obj_buffers += [vao, vbo]
                out.append((tex, vao))

    def _trees(self):
        """The trees' buffers: each model once, drawn as many times as it stands (instances)."""
        for obj in self._tree_buffers:
            obj.release()
        self._tree_buffers, self.tree_vaos = [], []
        ctx, d = self.ctx, self.data
        for f, inst in d.trees.items():
            v, idx, tex = d.tree_models[f]
            if not len(inst) or not len(idx):
                continue
            vbo, ibo = ctx.buffer(np.ascontiguousarray(v).tobytes()), ctx.buffer(np.ascontiguousarray(idx).tobytes())
            ins = ctx.buffer(np.ascontiguousarray(inst).tobytes())
            vao = ctx.vertex_array(self.tree, [(vbo, "3f 3f 2f", "pos", "nrm", "uv"), (ins, "4f/i", "inst")], ibo,
                                   index_element_size=4)
            self._tree_buffers += [vao, vbo, ibo, ins]
            self.tree_vaos.append((tex, vao, len(inst)))

    def _picture(self, arr, comps, plain, repeat=False):
        if arr is None:
            arr = np.empty((4, 4, comps), np.uint8)
            arr[:] = plain
        t = self._keep(self.ctx.texture((arr.shape[1], arr.shape[0]), comps, np.ascontiguousarray(arr).tobytes()))
        t.build_mipmaps()
        t.filter = (self.ctx.LINEAR_MIPMAP_LINEAR, self.ctx.LINEAR)
        t.repeat_x = t.repeat_y = repeat
        return t

    def set_heights(self, row, col, block):
        """Heights (metres) of a block of points from (row, col) - top row first - changed on the card."""
        block = np.asarray(block, np.float32)
        self.data.heights[row:row + block.shape[0], col:col + block.shape[1]] = block
        self.heights.write(np.ascontiguousarray(block).tobytes(),
                           viewport=(col, row, block.shape[1], block.shape[0]))
        self.coast_dirty = True                                  # the shore traced again at the next frame
        self.models_stale = True                                 # the tile models laid again after the stroke

    def set_tint(self, rgba):
        """Colours over the map: (H, W, 4) uint8, a tile each, top row first (MapData.tint_of), or None for none."""
        on = rgba is not None
        if on:
            self.tint.write(np.ascontiguousarray(rgba, np.uint8).tobytes())
        for prog in (self.terrain, self.under, self.sea):
            if "tinted" in prog:
                prog["tinted"].value = int(on)

    def set_layers(self, row, col, block):
        """The ground picture (layer) of a block of points from (row, col) changed on the card."""
        block = np.asarray(block, np.uint16)
        self.data.layers[row:row + block.shape[0], col:col + block.shape[1]] = block
        self.layers.write(np.ascontiguousarray(block).tobytes(),
                          viewport=(col, row, block.shape[1], block.shape[0]))

    def _coast(self):
        """The coast's strips traced again from the heights (made once, then after a heights change)."""
        for obj in self._coast_buffers:
            obj.release()
        self._coast_buffers, self.coast_vao, self.coast_dirty = [], None, False
        verts, tris = coast_line(self.data.heights, 0.0005 * self.data.scale, self.data.coast_hidden)
        if not len(tris):
            return
        vbo, ibo = self.ctx.buffer(verts.tobytes()), self.ctx.buffer(tris.tobytes())
        self.coast_vao = self.ctx.vertex_array(self.coast, [(vbo, "3f 3f 2f 1f", "pos", "dir", "uv", "shown")], ibo,
                                               index_element_size=4)
        self._coast_buffers = [self.coast_vao, vbo, ibo]

    def ground_at(self, fx, fy):
        """The map point (x, z in tiles, y in world units) seen at (fx, fy) - fractions of the last frame from its
        top-left corner - read from the frame's depth; None off the map (the black beyond it)."""
        if self.fbo is None or self.last is None:
            return None
        mvp, w, h = self.last
        px, py = min(w - 1, max(0, int(fx * w))), min(h - 1, max(0, int((1.0 - fy) * h)))
        d = float(np.frombuffer(self.fbo.read(viewport=(px, py, 1, 1), attachment=-1, dtype="f4"), np.float32)[0])
        if d >= 1.0:
            return None
        ndc = np.array([(px + 0.5) / w * 2 - 1, (py + 0.5) / h * 2 - 1, d * 2 - 1, 1.0])
        p = np.linalg.inv(mvp.astype(np.float64)) @ ndc
        return tuple(p[:3] / p[3])

    def to_screen(self, points):
        """World points (n, 3) -> (n, 2) fractions of the last frame from its top-left corner (None behind the
        eye)."""
        if self.last is None:
            return None
        mvp = self.last[0].astype(np.float64)
        p = np.c_[np.asarray(points, np.float64), np.ones(len(points))] @ mvp.T
        if (p[:, 3] <= 1e-6).any():
            return None
        return np.c_[(p[:, 0] / p[:, 3] + 1) / 2, 1 - (p[:, 1] / p[:, 3] + 1) / 2]

    def render(self, cam, w, h, t=0.3, show=None, clock=0.0, read=True):
        """The map seen from cam as a (h, w, 3) uint8 picture, top row first; t: the moment of the surf's wave
        (0..1); show: {layer: False} leaves a layer out (LAYERS - the sea off shows the sea floor); clock: seconds,
        the trees' lean in the wind. read=False: left on the card in self.fbo (glwindow shows it), None returned."""
        show = show or {}
        ctx = self.ctx
        started = time.perf_counter()
        w, h = max(16, int(w)), max(16, int(h))
        if self.fbo_size != (w, h):
            if self.fbo is not None:
                self.fbo.release()
            self.fbo = ctx.simple_framebuffer((w, h))
            self.fbo_size = (w, h)
        self.fbo.use()
        ctx.viewport = (0, 0, w, h)
        ctx.clear(0.0, 0.0, 0.0, 1.0, depth=1.0)
        ctx.enable(ctx.DEPTH_TEST)
        ground = self.data.ground_height(cam.x, cam.z)
        mvp, eye = cam.matrix(w, h, ground)
        self.last = (mvp, w, h)
        mvp_bytes = np.ascontiguousarray(mvp.T).tobytes()        # column-major, as OpenGL reads it
        self.water.use(4)
        self.waves.use(5)
        self.sky.use(6)
        self.tint.use(13)
        if show.get("sea", True):
            self.sea["mvp"].write(mvp_bytes)
            if "eye" in self.sea:
                self.sea["eye"].value = tuple(float(v) for v in eye)
            self.sea_vao.render(ctx.TRIANGLE_STRIP)
        self.heights.use(0)
        self.layers.use(1)
        self.ground.use(2)
        self.masks.use(3)
        self.voids.use(8)
        self.lift.use(12)
        bits = sum(1 << k for name, k in MODEL_LAYERS.items() if show.get(name, True))
        self.terrain["mvp"].write(mvp_bytes)
        self.terrain["yscale"].value = 0.0005 * self.data.scale
        self.terrain["shown"].value = bits
        self.vao.render()
        # the tile models: their plain parts dressed in the ground's pictures, then the rock laid on them
        for what, tex, page, vao in self.model_vaos:
            if not bits:
                break
            if what == "under":
                self.under["mvp"].write(mvp_bytes)
                self.under["shown"].value = bits
                vao.render()
        if bits and any(w == "over" for w, _, _, _ in self.model_vaos):
            ctx.enable(ctx.BLEND)
            ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
            ctx.depth_func = "<="                                # laid on its part's own points
            self.over["mvp"].write(mvp_bytes)
            self.over["shown"].value = bits
            for what, tex, page, vao in self.model_vaos:
                if what != "over":
                    continue
                self.model_pics.get(tex, self._white).use(9)
                self.model_masks.get(page, self._white).use(10)
                vao.render()
            ctx.depth_func = "<"
            ctx.disable(ctx.BLEND)
        if self.tree_vaos and show.get("trees", True):            # the forests, leaning with the wind
            self.tree["mvp"].write(mvp_bytes)
            self.tree["sheers"].write(MT.sheers(clock).astype("f4").tobytes())
            ctx.enable(ctx.CULL_FACE)
            ctx.front_face = "cw"                                # the models' z turned round to run south
            for tex, vao, n in self.tree_vaos:
                self.tree_pics.get(tex, self._white).use(9)
                vao.render(instances=n)
            ctx.front_face = "ccw"
            ctx.disable(ctx.CULL_FACE)
        obits = sum(1 << k for name, k in OBJECT_LAYERS.items() if show.get(name, True))
        if (self.obj_vaos or self.ghost_vaos) and obits:          # the towns, ports, resources and armies
            self.obj["mvp"].write(mvp_bytes)
            self.obj["shown"].value = obits
            for vaos, shift in ((self.obj_vaos, (0.0, 0.0, 0.0)), (self.ghost_vaos, self.ghost_shift)):
                self.obj["shift"].value = tuple(float(v) for v in shift)
                for tex, vao in vaos:
                    self.obj_pics.get(tex, self._white).use(9)
                    vao.render()
        waters = [vao for w_, _, _, vao in self.model_vaos if w_ == "water"]
        if waters and bits & (1 << MODEL_LAYERS["rivers"]):      # the rivers' water over their beds
            ctx.enable(ctx.BLEND)
            ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
            self.fbo.depth_mask = False
            ctx.depth_func = "<="
            self.flow.use(11)
            self.river["mvp"].write(mvp_bytes)
            self.river["shown"].value = bits
            self.river["shift"].value = float(t % 1.0)
            if "eye" in self.river:
                self.river["eye"].value = tuple(float(v) for v in eye)
            for vao in waters:
                vao.render()
            ctx.depth_func = "<"
            self.fbo.depth_mask = True
            ctx.disable(ctx.BLEND)
        if self.coast_dirty and not getattr(self, "coast_frozen", False):   # a brush held: traced when let go
            self._coast()
        if self.coast_vao is not None and show.get("coast", True):   # see-through strips over the ground, as the game
            self.coast["mvp"].write(mvp_bytes)
            self.fbo.depth_mask = False
            ctx.enable(ctx.BLEND)
            ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
            ctx.depth_func = "<="
            ctx.polygon_offset = (-2.0, -256.0)
            for key, inland, sea, alpha, bright in coast_strips(t % 1.0):
                if alpha <= 0.0:
                    continue
                self.strips[key].use(7)
                self.coast["edges"].value = (inland, sea)
                bright = bright if self.linear else bright ** (1 / 2.2)     # the old games' light is sRGB
                self.coast["tint"].value = tuple(float(v) * bright for v in self.strip_light) + (alpha,)
                self.coast_vao.render()
            ctx.polygon_offset = (0.0, 0.0)
            ctx.depth_func = "<"
            ctx.disable(ctx.BLEND)
            self.fbo.depth_mask = True
        roads = self.road_vaos if show.get("roads", True) else []
        border = self.border_vao if show.get("borders", True) else None
        if roads or border is not None:                  # after the ground, see-through, lifted toward the eye
            self.fbo.depth_mask = False
            ctx.enable(ctx.BLEND)
            ctx.depth_func = "<="
            ctx.polygon_offset = (-2.0, -512.0)
            if roads:
                ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
                self.road["mvp"].write(mvp_bytes)
                for tex, vao in roads:
                    self.net_pics.get(tex, self._white).use(9)
                    vao.render()
            if border is not None:
                ctx.blend_func = ctx.ONE, ctx.ONE_MINUS_SRC_ALPHA
                self.border["mvp"].write(mvp_bytes)
                self.net_pics.get("terrain/aerial_map/indicators/region_borders_primary.tga", self._white).use(9)
                self.net_pics.get("terrain/aerial_map/indicators/region_borders_secondary.tga", self._white).use(10)
                border.render()
            ctx.polygon_offset = (0.0, 0.0)
            ctx.depth_func = "<"
            ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
            ctx.disable(ctx.BLEND)
            self.fbo.depth_mask = True
        ctx.finish()                                             # the card's own time ends here (step 1, measured)
        took = time.perf_counter()
        if not read:
            self.took = (took - started, 0.0)
            return None
        raw = self.fbo.read(components=3)
        self.took = (took - started, time.perf_counter() - took)  # (drawn by the card, copied back) in seconds
        return np.frombuffer(raw, np.uint8).reshape(h, w, 3)[::-1]

    def release(self):
        for obj in reversed(self._gone + self._coast_buffers + self._model_buffers + self._tree_buffers +
                            self._obj_buffers + self._net_buffers +
                            ([self.fbo] if self.fbo is not None else [])):
            try:
                obj.release()
            except Exception:
                pass
        self._gone, self._coast_buffers, self._model_buffers, self._tree_buffers, self.fbo = [], [], [], [], None
        self._obj_buffers, self._net_buffers = [], []


class FrameClock:
    """How long a 3D frame takes, by its parts (the user, 2026-10-17: step 1 before drawing straight into the window):
    drawn by the card, copied back from it, put in the window - the mean of the last frames, said in plain words."""

    KEEP = 10

    def __init__(self):
        self.frames = []

    def add(self, card, back, window, size):
        self.frames = (self.frames + [(card, back, window, size)])[-self.KEEP:]

    def text(self):
        if not self.frames:
            return ""
        n = len(self.frames)
        card, back, window = (sum(f[i] for f in self.frames) / n * 1000 for i in range(3))
        total = card + back + window
        w, h = self.frames[-1][3]
        return ("a frame (%d x %d): the graphics card draws it in %d ms, copying it back takes %d ms, putting it in "
                "the window %d ms = %d ms (%d frames a second)" % (w, h, round(card), round(back), round(window),
                                                                   round(total), 1000 / max(total, 1)))


__all__ = ["available", "context", "MapData", "GLMap", "FrameClock", "Camera", "TopCamera", "top_picture", "lighting", "LAYERS", "coast_line", "coast_strips"]
