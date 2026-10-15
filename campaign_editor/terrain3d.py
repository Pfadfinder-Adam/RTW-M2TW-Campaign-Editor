"""The campaign map in 3D, in the game's own ground textures (Maps > 3D) - both games.

What the game lays on its campaign map: descr_aerial_map_ground_types.txt names, for each climate (map_climates.tga)
and each kind of ground (map_ground_types.tga), the texture of summer and of winter (data/terrain/aerial_map/
ground_types/*.tga); map_heights.tga gives the relief, the water lies at height 0 (terrain.hgt_value), the rivers come
from map_features.tga. Everything is read from the pictures the Terrain editor's brushes paint into (ModData's cached
maps), so what is painted and not written yet is seen at once.

Two steps, both on NumPy arrays:
- colour_map(): the whole map as one picture, K pixels a heights point - each pixel the texture of its point's ground
  and climate, sampled where it lies on the map (the textures tile across it as in the game), the borders between
  grounds softened by a little jitter, lit by the slope (sun from the north-west), the water by its depth, the rivers
  drawn in.
- render(): a view of it from a camera over the map - the 'voxel space' way: for each column of the screen, the map
  is walked away from the camera in steps; each step's height is put on the screen, and only the part above what the
  nearer steps already cover is seen (front to back, so nothing is drawn twice). Fast enough to turn with the mouse.
"""

import math

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


def aerial_sets(mod):
    """({climate: {ground key: (summer file, winter file or None)}}, texture_density) of
    descr_aerial_map_ground_types.txt (the mod's, else the game's)."""
    from .textio import strip_comment
    p = mod.find("descr_aerial_map_ground_types.txt")
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


def _texture(mod, name, period):
    """A ground texture as a (period, period, 3) float array, or None."""
    from PIL import Image
    for rel in ("terrain/aerial_map/ground_types/" + name, "terrain/aerial_map/" + name):
        p = mod.find(rel)
        if not p and not name.lower().endswith(".dds"):
            p = mod.find(rel + ".dds")
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
    top, low = T.max_land_height(mod, campaign), T.min_sea_height(mod, campaign)
    r, g, b = (rgb[..., k].astype(np.float32) for k in range(3))
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
    sets, density = aerial_sets(mod)
    names = list(sets) or ["default"]
    keys = sorted(set(GROUND_KEYS.values()))
    notes = []
    period = max(8, int(PERIOD * density))
    # one texture per (climate, ground): looked up once, the plain colour where none
    tex = np.zeros((len(names), len(keys), period, period, 3), np.float32)
    missing = set()
    cache = {}
    for ci, cname in enumerate(names):
        for gi, key in enumerate(keys):
            entry = sets.get(cname, {}).get(key) or sets.get("default", {}).get(key)
            if entry is None and FALLBACK.get(key):
                entry = sets.get(cname, {}).get(FALLBACK[key]) or sets.get("default", {}).get(FALLBACK[key])
            fname = entry[1] if entry and winter and entry[1] else (entry[0] if entry else None)
            arr = None
            if fname:
                if fname not in cache:
                    cache[fname] = _texture(mod, fname, period)
                arr = cache[fname]
                if arr is None:
                    missing.add(fname)
            tex[ci, gi] = arr if arr is not None else np.array(PLAIN.get(key, (120, 120, 90)), np.float32)
    if missing:
        notes.append("%d ground texture(s) not found - their ground's plain colour shown: %s" % (
            len(missing), ", ".join(sorted(missing)[:4]) + (" ..." if len(missing) > 4 else "")))
    if not sets:
        notes.append("no descr_aerial_map_ground_types.txt - the grounds' plain colours shown")
    # the grounds and climates of the heights' points (the pictures share the 2 W + 1 size; else stretched)
    gi = _ground_index(ground, keys) if ground is not None and ground.shape[:2] == (H, W) else np.zeros((H, W), np.int32)
    ci = _climate_index(mod, climate, names) if climate is not None and climate.shape[:2] == (H, W) else \
        np.zeros((H, W), np.int32)
    big_h = _smooth_up(h, k)
    bh, bw = big_h.shape
    rng = rng or np.random.default_rng(7)
    # where a pixel looks up its point is pushed by a smooth wave (random at each point, bilinear between): the
    # borders between grounds wind softly as the game blends them, never in squares or speckles
    wave = 1.1 * k
    oy = _smooth_up(rng.uniform(-wave, wave, (H, W)).astype(np.float32), k)
    ox = _smooth_up(rng.uniform(-wave, wave, (H, W)).astype(np.float32), k)
    jy = np.clip(((np.arange(bh)[:, None] + oy) // k).astype(np.int32), 0, H - 1)
    jx = np.clip(((np.arange(bw)[None, :] + ox) // k).astype(np.int32), 0, W - 1)
    g = gi[jy, jx]
    c = ci[jy, jx]
    land_g = np.where(g < 0, 0, g)
    yy = (np.arange(bh) % period)[:, None]
    xx = (np.arange(bw) % period)[None, :]
    rgb = tex[c, land_g, np.broadcast_to(yy, (bh, bw)), np.broadcast_to(xx, (bh, bw))]
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
        rgb = np.where(mask[..., None], rgb * 0.35 + RIVER * 0.65, rgb)
    return ColourMap(np.clip(rgb, 0, 255).astype(np.uint8), np.maximum(big_h, 0).astype(np.float32), k, top, notes)


FOV = 0.9                   # half the view's width at depth 1


def focal(W):
    return W / (2.0 * FOV)


def project(f, dv, cam, W, H):
    """(depth, screen y) of a point f ahead of the camera along the ground and dv above its eye (negative: below),
    for a camera tilted down by cam.pitch - a real tilt, so the ground and the models on it keep their shapes from
    any height."""
    sp, cp = math.sin(cam.pitch), math.cos(cam.pitch)
    depth = f * cp - dv * sp
    up = f * sp + dv * cp
    return depth, H / 2.0 - up / np.maximum(depth, 1e-3) * focal(W)


class Camera:
    """Where the view stands: over map pixel (x, y) (colour-map pixels, x right, y down), looking towards yaw
    (radians, 0 = north / up the map), at a height above the ground there, tilted down by pitch (radians)."""

    def __init__(self, cmap):
        bh, bw = cmap.height.shape
        self.x, self.y = bw / 2.0, bh * 0.85
        self.yaw = 0.0
        self.alt = max(bh, bw) * 0.12
        self.pitch = 0.62                   # looking down about 35 degrees, as the game's camera
        self.far = max(bh, bw) * 0.9
        self.exaggerate = 1.0

    def moved(self, forward, right):
        s, c = math.sin(self.yaw), math.cos(self.yaw)
        self.x += right * c + forward * s
        self.y += right * s - forward * c


def render(cmap, cam, W, H, steps=None, sky=(170, 196, 220), with_depth=False):
    """(H, W, 3) uint8 picture of the map from cam (see the module's words); with_depth: (picture, (H, W) distance
    of the ground each pixel shows - infinite for the sky), what the models on the map are hidden behind."""
    bh, bw = cmap.height.shape
    steps = steps or max(200, min(900, int(cam.far)))
    # the distances walked: closer steps near the camera, wider further away
    z = np.linspace(0, 1, steps, dtype=np.float32) ** 1.6 * cam.far + 1.0
    s, c = math.sin(cam.yaw), math.cos(cam.yaw)
    a = (np.arange(W, dtype=np.float32) - W / 2.0) / focal(W)        # each column's side / depth
    k = cmap.k
    hscale = (k * 6.0) / max(1.0, cmap.top) * cam.exaggerate      # a mountain's top ~ 3 tiles high at x1
    here = cmap.height[int(np.clip(cam.y, 0, bh - 1)), int(np.clip(cam.x, 0, bw - 1))] * hscale
    eye = here + cam.alt
    # the map point every (step, column) looks at: ahead z, to the side as the column's ray reaches the ground there
    side = a[None, :] * (z[:, None] * math.cos(cam.pitch) + eye * math.sin(cam.pitch))
    px = cam.x + z[:, None] * s + side * c
    py = cam.y - z[:, None] * c + side * s
    inside = (px >= 0) & (px < bw) & (py >= 0) & (py < bh)
    # between the pixels: the four around each point blended (bilinear) - smooth slopes and no squares up close
    fx0 = np.clip(px - 0.5, 0, bw - 1.001)
    fy0 = np.clip(py - 0.5, 0, bh - 1.001)
    ix, iy = fx0.astype(np.int32), fy0.astype(np.int32)
    tx, ty = (fx0 - ix)[..., None], (fy0 - iy)[..., None]
    ix1, iy1 = np.minimum(ix + 1, bw - 1), np.minimum(iy + 1, bh - 1)
    hm = cmap.height
    ground_h = ((hm[iy, ix] * (1 - tx[..., 0]) + hm[iy, ix1] * tx[..., 0]) * (1 - ty[..., 0]) +
                (hm[iy1, ix] * (1 - tx[..., 0]) + hm[iy1, ix1] * tx[..., 0]) * ty[..., 0]) * hscale
    dist, y = project(z[:, None], ground_h - eye, cam, W, H)
    y = np.where(inside & (dist > 0.5), y, H + 1.0)    # off the map: nothing drawn
    # front to back: a step is seen where it rises above every nearer step
    cover = np.minimum.accumulate(y, axis=0)
    rows = np.arange(H, dtype=np.float32)
    out = np.empty((H, W, 3), np.uint8)
    # the sky: lighter towards the horizon
    horizon = H / 2.0 - math.tan(cam.pitch) * focal(W)
    t = np.clip(rows / max(1.0, horizon), 0, 1)[:, None]
    skyc = (np.array(sky, np.float32)[None, :] * (0.75 + 0.25 * t)).astype(np.uint8)
    out[:] = skyc[:, None, :]
    rgb = cmap.rgb
    colours = ((rgb[iy, ix] * (1 - tx) + rgb[iy, ix1] * tx) * (1 - ty) +
               (rgb[iy1, ix] * (1 - tx) + rgb[iy1, ix1] * tx) * ty)     # (steps, W, 3)
    fog = np.clip((z - cam.far * 0.55) / (cam.far * 0.45), 0, 1)[:, None, None]
    colours = (colours * (1 - fog) + np.array(sky, np.float32) * fog).astype(np.uint8)
    depth = np.full((H, W), np.inf, np.float32) if with_depth else None
    for col in range(W):
        cv = -cover[:, col]                            # rising: searchsorted wants it sorted
        s_idx = np.searchsorted(cv, -rows, side="left")
        seen = s_idx < steps
        r = np.nonzero(seen)[0]
        if r.size:
            out[r, col] = colours[s_idx[r], col]
            if depth is not None:
                depth[r, col] = dist[s_idx[r], col]
    return (out, depth) if with_depth else out


__all__ = ["colour_map", "render", "Camera", "ColourMap", "aerial_sets", "heights_metres"]
