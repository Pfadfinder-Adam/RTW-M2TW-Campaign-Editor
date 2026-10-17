"""The campaign map as one picture in the game's own ground textures - both games; the minimap is drawn from it
(minimap.top_view), and the graphics card's 3D map (glmap) takes its readers (aerial_sets, heights_metres, the
ground / climate indexes).

What the game lays on its campaign map: descr_aerial_map_ground_types.txt names, for each climate (map_climates.tga)
and each kind of ground (map_ground_types.tga), the texture of summer and of winter (data/terrain/aerial_map/
ground_types/*.tga); map_heights.tga gives the relief, the water lies at height 0 (terrain.hgt_value), the rivers come
from map_features.tga. Everything is read from the pictures the Terrain editor's brushes paint into (ModData's cached
maps), so what is painted and not written yet is seen at once.

colour_map(): the whole map as one picture, K pixels a heights point - each pixel the texture of its point's ground and
climate, sampled where it lies on the map (the textures tile across it as in the game), the borders between grounds
softened by a little jitter, lit by the slope (sun from the north-west), the water by its depth, the rivers drawn in.
(The older 3D view drawn from it without the graphics card - render / Camera - was taken out at the user's word,
2026-10-16.)"""

import math
import os

import numpy as np

from . import terrain as T

GROUND_KEYS = {
    (101, 124, 0): "fertility_low", (96, 160, 64): "fertility_medium", (0, 128, 0): "fertility_high",
    (0, 0, 0): "fertility_low", (0, 64, 0): "forest_dense", (0, 128, 128): "forest_sparse",
    (128, 128, 64): "hills", (98, 65, 65): "mountains_low", (196, 128, 128): "mountains_high",
    (0, 255, 128): "swamp", (255, 255, 255): "beach", (64, 64, 64): "impassable_land",
    (32, 32, 32): "impassable_shrouded",
}
FALLBACK = {"impassable_land": "mountains_high", "impassable_shrouded": None, "scorched": "fertility_low"}
# a colour when a texture is missing (the ground's own colour on the Terrain editor's palette, a little toned)
PLAIN = {"fertility_low": (128, 132, 70), "fertility_medium": (110, 140, 70), "fertility_high": (80, 125, 55),
         "forest_dense": (45, 80, 40), "forest_sparse": (70, 105, 60), "hills": (130, 125, 85),
         "mountains_low": (125, 110, 95), "mountains_high": (170, 165, 160), "swamp": (75, 100, 70),
         "beach": (210, 195, 150), "impassable_land": (110, 100, 95), "impassable_shrouded": (15, 15, 15)}
WATER_SHALLOW, WATER_DEEP = np.array([70, 140, 160], np.float32), np.array([18, 45, 85], np.float32)
RIVER = np.array([60, 110, 170], np.float32)
PERIOD = 64             # pixels one texture repeat covers on the colour map (x texture_density)


def aerial_sets(mod, path=None):
    """({climate: {ground key: (summer file, winter file or None)}}, texture_density) of
    descr_aerial_map_ground_types.txt (the mod's, else the game's; path: that file)."""
    from .textio import strip_comment
    p = path or mod.find("descr_aerial_map_ground_types.txt")
    out, density, cur = {}, 1.0, None
    if not p:
        return out, density
    for line in mod.load(p).texts():
        t = strip_comment(line).split()
        if not t:
            continue
        if t[0] == "texture_density" and len(t) > 1:
            try:
                density = max(0.25, min(8.0, float(t[1])))
            except ValueError:
                pass
        elif t[0] == "climate" and len(t) > 1:
            cur = out.setdefault(t[1], {})
        elif cur is not None and len(t) >= 2 and t[0] not in ("{", "}"):
            cur[t[0]] = (t[1], t[2] if len(t) > 2 else None)
    return out, density


def picture_choices(mod, keys, winter=False):
    """(climates, {(climate, ground key): [pictures to try, the first that opens wins]}, texture_density): the
    picture descr_aerial_map_ground_types.txt names (its 'default' block where the climate has none, the stand-in
    ground where the key is missing), then the game's own picture for the same place - a mod whose pictures the
    editor cannot reach (packed in a way it does not read) still shows the ground drawn, not a plain colour."""
    import os
    from .moddata import ci_path
    sets, density = aerial_sets(mod)
    game = {}
    own = mod.find("descr_aerial_map_ground_types.txt")
    under = ci_path(mod.under, "descr_aerial_map_ground_types.txt") if getattr(mod, "under", None) else None
    if under and (not own or os.path.normcase(own) != os.path.normcase(under)):
        game = aerial_sets(mod, under)[0]
    names = list(sets) or ["default"]

    def pick(s, cname, key):
        entry = s.get(cname, {}).get(key) or s.get("default", {}).get(key)
        if entry is None and FALLBACK.get(key):
            entry = s.get(cname, {}).get(FALLBACK[key]) or s.get("default", {}).get(FALLBACK[key])
        return (entry[1] if winter and entry[1] else entry[0]) if entry else None
    out = {}
    for cname in names:
        for key in keys:
            files = []
            for f in (pick(sets, cname, key), pick(game, cname, key)):
                if f and f not in files:
                    files.append(f)
            out[(cname, key)] = files
    return names, out, density


def ground_file(name):
    """The path under data/ of a picture named in descr_aerial_map_ground_types.txt: the game puts the name after
    data/terrain/aerial_map/ground_types/ as it stands, so a mod may climb out with '../' (HLR names
    '../../../../data/terrain/aerial_map/ground_types/x.tga' - the same folder reached from the game's root)."""
    import posixpath
    p = posixpath.normpath("data/terrain/aerial_map/ground_types/" + name.replace("\\", "/"))
    return p[5:] if p.lower().startswith("data/") else p.lstrip("./")


def _texture(mod, name, period):
    """A ground texture as a (period, period, 3) float array, or None."""
    from PIL import Image
    for rel in (ground_file(name), "terrain/aerial_map/" + name):
        p = mod.find_any(rel)
        if not p and not name.lower().endswith(".dds"):
            p = mod.find_any(rel + ".dds")
        if p:
            try:
                with Image.open(p) as im:
                    im = im.convert("RGB").resize((period, period), Image.BILINEAR)
                    return np.asarray(im, dtype=np.float32)
            except Exception:
                return None
    return None


def _picture(mod, campaign, name):
    """A campaign map picture as it stands in memory (the brushes paint into these): (h, w, 3) uint8, top row first;
    None without the file."""
    t = mod._optional_map(campaign, name)
    if t is None:
        return None
    return np.frombuffer(t.rgb_top_down(), dtype=np.uint8).reshape(t.height, t.width, 3)


def heights_metres(mod, campaign):
    """map_heights.tga as metres (h, w) float32, top row first: land grey * top / 255, water - its depth (terrain
    .hgt_value), None without the file."""
    rgb = _picture(mod, campaign, "map_heights.tga")
    if rgb is None:
        return None
    hgt = None
    try:
        path = mod.campaign_file(campaign, "map_heights.tga")
        if path:
            hgt = T.read_hgt(os.path.join(os.path.dirname(path), "map_heights.hgt"))
    except Exception:                                   # a mod object without files: the picture alone
        hgt = None
    return game_metres(rgb, T.max_land_height(mod, campaign), T.min_sea_height(mod, campaign), hgt)


def game_metres(rgb, top, low, hgt=None):
    """The heights as the game reads them (#339: the 3D map took the picture's 29 m steps, the heights brush the
    game's own map_heights.hgt - a square of other heights round every stroke): map_heights.hgt's value where it
    still agrees with the picture (an unchanged point - terrain.ShapeCoast.metres, the same rule), else the
    picture's; land never 0 (0 reads as water). hgt: read_hgt() (bottom-up rows) or None."""
    rgb = np.asarray(rgb)
    v = metres_of(rgb, top, low)
    land = (rgb[..., 0] == rgb[..., 1]) & (rgb[..., 1] == rgb[..., 2])
    out = np.where(land, np.maximum(v, 1.0), v).astype(np.float32)
    if hgt is not None and (hgt[0], hgt[1]) == (rgb.shape[1], rgb.shape[0]):
        f = np.asarray(hgt[2], np.float32).reshape(hgt[1], hgt[0])[::-1]
        step = np.where(land, top / 255.0, -low / 255.0)
        ok = ((f > 0) == land) & (np.abs(f - v) <= 1.5 * step)
        out = np.where(ok, f, out).astype(np.float32)
    return out


def metres_of(rgb, top, low):
    """map_heights colours (..., 3) as metres: land grey * top / 255, water its depth (the one formula of
    heights_metres and the 3D view's brush)."""
    rgb = np.asarray(rgb)
    r, b = rgb[..., 0].astype(np.float32), rgb[..., 2].astype(np.float32)
    land = (rgb[..., 0] == rgb[..., 1]) & (rgb[..., 1] == rgb[..., 2])
    return np.where(land, r * top / 255.0, low * (255.0 - b) / 255.0).astype(np.float32)


def _ground_index(ground, keys):
    """(h, w) int index into keys of each ground pixel's key (-1: the sea / unknown)."""
    code = (ground[..., 0].astype(np.int32) << 16) | (ground[..., 1].astype(np.int32) << 8) | ground[..., 2]
    out = np.full(code.shape, -1, np.int32)
    for colour, key in GROUND_KEYS.items():
        if key in keys:
            c = (colour[0] << 16) | (colour[1] << 8) | colour[2]
            out[code == c] = keys.index(key)
    return out


def _climate_index(mod, climate_rgb, names):
    """(h, w) int index into names of each climate pixel (0 = the first / default)."""
    out = np.zeros(climate_rgb.shape[:2], np.int32)
    code = (climate_rgb[..., 0].astype(np.int32) << 16) | (climate_rgb[..., 1].astype(np.int32) << 8) | \
        climate_rgb[..., 2]
    for name, colour, _ in T.climates(mod):
        if name in names:
            c = (colour[0] << 16) | (colour[1] << 8) | colour[2]
            out[code == c] = names.index(name)
    return out


def _upsample(a, k):
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def _smooth_up(h, k):
    """h (h, w) float made k times bigger, bilinear between the points."""
    hh, ww = h.shape
    ys = np.linspace(0, hh - 1, hh * k, dtype=np.float32)
    xs = np.linspace(0, ww - 1, ww * k, dtype=np.float32)
    y0 = np.floor(ys).astype(np.int32)
    x0 = np.floor(xs).astype(np.int32)
    y1, x1 = np.minimum(y0 + 1, hh - 1), np.minimum(x0 + 1, ww - 1)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a = h[y0][:, x0] * (1 - fx) + h[y0][:, x1] * fx
    b = h[y1][:, x0] * (1 - fx) + h[y1][:, x1] * fx
    return (a * (1 - fy) + b * fy).astype(np.float32)


def pixels_per_point(w, h, limit=2048):
    """How many colour-map pixels a heights point gets: as many as keep the map's long side within limit."""
    return max(1, min(6, limit // max(w, h, 1)))


class ColourMap:
    """The map's colour picture and heights at the same size (K pixels a heights point)."""

    def __init__(self, rgb, height, k, top, notes):
        self.rgb, self.height, self.k, self.top, self.notes = rgb, height, k, top, notes


def _box3(a):
    """a (h, w) float averaged over each point's 3 x 3 neighbours (the edges repeated)."""
    p = np.pad(a, 1, mode="edge")
    h, w = a.shape
    return sum(p[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3)) / 9.0


def _rounded(mask, k):
    """(h, w) float 0-1 of a line mask drawn tile by tile: blurred and cut again, so its stair steps round off like
    the game's rivers, then a soft edge (no hard pixels). The mask as it is without Pillow."""
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return mask.astype(np.float32)
    im = Image.fromarray((mask * 255).astype(np.uint8))
    im = im.filter(ImageFilter.GaussianBlur(max(1.0, k * 0.6))).point(lambda v: 255 if v >= 105 else 0)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255


def _blended(tex, gi, ci, k, period, bh, bw, rng):
    """(bh, bw, 3) float: every pixel the grounds of the points round it mixed by how near they are - the game lays
    its ground textures blended into each other, never in squares or speckles (the user, 2026-10-15: 'smooth the
    textures and their edges as in the game, no pixels'). Each (climate, ground) on the map gets a weight: 1 at its
    own points, smoothed over a tile (3 x 3 points), bilinear between the points, a little uneven (a soft noise), so
    the borders wind; the textures are mixed by those weights. The sea (ground -1) weighs nothing - the water is
    drawn over it later."""
    H, W = gi.shape
    yy = np.broadcast_to((np.arange(bh) % period)[:, None], (bh, bw))
    xx = np.broadcast_to((np.arange(bw) % period)[None, :], (bh, bw))
    pair = np.where(gi < 0, -1, ci * tex.shape[1] + gi)
    wobble = 1.0 + 0.8 * _smooth_up(rng.uniform(-1, 1, (H, W)).astype(np.float32), k)[:bh, :bw]
    out = np.zeros((bh, bw, 3), np.float32)
    total = np.full((bh, bw), 1e-6, np.float32)
    for p in np.unique(pair):
        if p < 0:
            continue
        w = _smooth_up(_box3((pair == p).astype(np.float32)), k)[:bh, :bw]
        w = np.clip(w * wobble, 0, None) ** 2                 # squared: each ground firm at home, mixed at its edge
        if not w.any():
            continue
        c, g = divmod(int(p), tex.shape[1])
        out += w[..., None] * tex[c, g][yy, xx]
        total += w
    # nowhere a land weight (the sea): the first texture, drawn over by the water later
    out += (total <= 1e-6)[..., None] * tex[0, 0][yy, xx]
    return out / total[..., None]


def colour_map(mod, campaign, winter=False, limit=2048, rng=None):
    """ColourMap of the campaign as it stands in memory now (see the module's words). Raises ValueError without the
    heights picture."""
    h = heights_metres(mod, campaign)
    if h is None:
        raise ValueError("this campaign has no map_heights.tga - nothing to raise in 3D")
    H, W = h.shape
    k = pixels_per_point(W, H, limit)
    ground = _picture(mod, campaign, "map_ground_types.tga")
    climate = _picture(mod, campaign, "map_climates.tga")
    keys = sorted(set(GROUND_KEYS.values()))
    names, choices, density = picture_choices(mod, keys, winter)
    notes = []
    period = max(8, int(PERIOD * density))
    # one texture per (climate, ground): looked up once, the plain colour where none
    tex = np.zeros((len(names), len(keys), period, period, 3), np.float32)
    missing = set()
    cache = {}
    for ci, cname in enumerate(names):
        for gi, key in enumerate(keys):
            files = choices[(cname, key)]
            arr = None
            for fname in files:
                if fname not in cache:
                    cache[fname] = _texture(mod, fname, period)
                arr = cache[fname]
                if arr is not None:
                    break
            if files and cache[files[0]] is None:
                missing.add(files[0])
            tex[ci, gi] = arr if arr is not None else np.array(PLAIN.get(key, (120, 120, 90)), np.float32)
    if missing:
        notes.append("%d ground texture(s) not found - the game's own picture of that ground (else its plain colour) "
                     "shown: %s" % (
            len(missing), ", ".join(sorted(missing)[:4]) + (" ..." if len(missing) > 4 else "")))
    if not any(choices.values()):
        notes.append("no descr_aerial_map_ground_types.txt - the grounds' plain colours shown")
    # the grounds and climates of the heights' points (the pictures share the 2 W + 1 size; else stretched)
    gi = _ground_index(ground, keys) if ground is not None and ground.shape[:2] == (H, W) else np.zeros((H, W), np.int32)
    ci = _climate_index(mod, climate, names) if climate is not None and climate.shape[:2] == (H, W) else \
        np.zeros((H, W), np.int32)
    big_h = _smooth_up(h, k)
    bh, bw = big_h.shape
    rng = rng or np.random.default_rng(7)
    rgb = _blended(tex, gi, ci, k, period, bh, bw, rng)
    # light: the slope's normal against a sun from the north-west, a little from above
    top = max(1.0, float(T.max_land_height(mod, campaign)))
    scale = top / (k * 6.0)                            # metres a pixel across, for the slopes' look
    land_h = np.maximum(big_h, 0)
    dy, dx = np.gradient(land_h / scale)
    nx, ny, nz = -dx, dy, np.ones_like(dx)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    sun = np.array([-0.55, 0.55, 0.63], np.float32)
    lit = np.clip((nx * sun[0] + ny * sun[1] + nz * sun[2]) / norm, 0, 1)
    rgb = rgb * (0.45 + 0.75 * lit)[..., None]
    # water: its depth from shallow to deep, a little sun glint from the same light
    water = big_h <= 0
    depth = np.clip(-big_h / max(1.0, -float(T.min_sea_height(mod, campaign))) * 3.0, 0, 1)[..., None]
    wcol = WATER_SHALLOW * (1 - depth) + WATER_DEEP * depth
    rgb = np.where(water[..., None], wcol, rgb)
    # rivers: one pixel per tile in map_features - a blue line through the tile's middle, both ways
    feat = _picture(mod, campaign, "map_features.tga")
    if feat is not None:
        code = (feat[..., 0].astype(np.int32) << 16) | (feat[..., 1].astype(np.int32) << 8) | feat[..., 2]
        rivery = np.isin(code, [(r << 16) | (gg << 8) | b for r, gg, b in T.RIVERY])
        ty, tx = np.nonzero(rivery)
        step = 2 * k                                   # a tile is two heights points
        half = max(0.6, k / 4.0)                       # a thin line, as the game's rivers
        segs = []
        nb = rivery.shape
        for y, x in zip(ty.tolist(), tx.tolist()):
            near = [(y + dy, x + dx) for dy, dx in ((1, 0), (0, 1), (1, 1), (1, -1))
                    if 0 <= y + dy < nb[0] and 0 <= x + dx < nb[1] and rivery[y + dy, x + dx]]
            # a diagonal only where no side step joins the two already (no little triangles)
            near = [(a, b) for a, b in near if a == y or b == x or not (rivery[y, b] or rivery[a, x])]
            segs += [((y, x), n) for n in near] or [((y, x), (y, x))]
        mask = np.zeros((bh, bw), bool)
        for (y0, x0), (y1, x1) in segs:
            n = max(2, int(max(abs(y1 - y0), abs(x1 - x0)) * step * 2))
            ys = np.linspace(y0 * step + k, y1 * step + k, n)
            xs = np.linspace(x0 * step + k, x1 * step + k, n)
            r = int(math.ceil(half))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dy * dy + dx * dx <= half * half + 0.5:
                        mask[np.clip((ys + dy).astype(int), 0, bh - 1), np.clip((xs + dx).astype(int), 0, bw - 1)] = True
        a = _rounded(mask, k)                          # the tiles' steps rounded off, the line's edge soft
        rgb = rgb * (1 - 0.65 * a[..., None]) + RIVER * (0.65 * a[..., None])
    return ColourMap(np.clip(rgb, 0, 255).astype(np.uint8), np.maximum(big_h, 0).astype(np.float32), k, top, notes)


__all__ = ["colour_map", "ColourMap", "aerial_sets", "heights_metres", "game_metres"]
