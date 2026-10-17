"""The campaign map's tile models - mountains, hills, volcanoes - placed and shaped the way the engines do it, for
the 3D map on the graphics card (glmap). Facts from the engine source (editor-notes strat_tile_models.md; no code
copied):

- descr_aerial_map_tile_models.txt names, per tile set, the .cas files (data/terrain/aerial_map/tile_models/<set>/),
  'geom's (a part of them + which edges meet the ground), 'geom_links' (the names the game knows, each a geom and a
  turn: rotation_0/90/180/270 clockwise from above) and 'overlay's (parts drawn on a part with their own texture -
  the mountains' rock, its strip of mountain4.tga and its piece of the alpha_page mask);
- which tile gets which: a dormant volcano's 3 x 3 round each red pixel of map_features.tga; high mountains
  (map_ground_types' mountains_high) fitted with seven 'tetris' pieces of four tiles in a 4 x 4 window moved over the
  map in steps of 4, 3, 2, 1 - what stays a single; hills: 2 x 2 blocks of hill tiles above the sea first, then a
  model on half of the hill tiles left (low mountains: none in either game - the code is switched off);
- a model is 1 x 1 tile (x, z from -0.5 to 0.5, +z the top / north), turned, and every one of its points rides the
  ground under it (the ground's height at that point added - the model drapes over the relief); the ground of a tile
  with a model is not drawn, the model takes its place; a part without a texture of its own (or 'dummy') wears the
  ground's own pictures.

The game picks among the pieces with its own random numbers (kept in map.rwm); here a stable hash of the tile picks
instead, so the pieces are the game's but not always the same ones in the same places.

Tiles here: (x, z) with z counted UP from the map's bottom row, as the engine counts; the arrays of heights are top
row first, as the pictures."""

import re

import numpy as np

from . import stratcas
from . import terrain3d as T3

MOUNTAIN_PIECES = ("line", "l", "lr", "t", "s", "sr", "square")
# each piece's 4 slots (gx, gy) at rotation 0 in a 4 x 4 window, gy up (tetris_set)
SLOTS = {"line": ((0, 2), (1, 2), (2, 2), (3, 2)), "l": ((0, 2), (1, 2), (2, 2), (0, 1)),
         "lr": ((0, 2), (1, 2), (2, 2), (2, 1)), "t": ((0, 2), (1, 2), (2, 2), (1, 1)),
         "s": ((1, 2), (2, 2), (0, 1), (1, 1)), "sr": ((0, 2), (1, 2), (1, 1), (2, 1)),
         "square": ((1, 2), (2, 2), (1, 1), (2, 1))}
VOLCANO_PARTS = ("top_left", "top", "top_right", "left", "centre", "right", "bottom_left", "bottom", "bottom_right")
MOUNTAINS_HIGH, HILLS = "mountains_high", "hills"
KIND = {"mountains": 1, "hills": 2, "volcano": 1, "volcano_dormant": 1}    # which Layers switch shows a tile set


def link_of(index):
    """(tile set, link name) of an AERIAL_MAP_TILE_MODEL_INDEX the code places, or None."""
    if 136 <= index <= 153:
        return ("volcano" if index < 145 else "volcano_dormant"), VOLCANO_PARTS[(index - 136) % 9]
    if 181 <= index <= 292:
        k = index - 181
        return "mountains", "%s%d_%d" % (MOUNTAIN_PIECES[k // 16], (k % 16) // 4, (k % 4) * 90)
    if 293 <= index <= 296:
        return "mountains", "single_%d" % ((index - 293) * 90)
    if 297 <= index <= 308:
        return "hills", "hill%d" % (index - 296)
    if 309 <= index <= 324:
        k = index - 309
        return "hills", "hill%d%s" % (13 + k // 4, ("tl", "tr", "bl", "br")[k % 4])
    if 325 <= index <= 328:
        return "hills", "hills%d" % (index - 324)
    if 329 <= index <= 336:
        return "hills", "crag%d" % (index - 328)
    return None


def _tokens(text):
    out = []
    for line in text.splitlines():
        line = line.split(";", 1)[0]
        out += [t.rstrip(",") for t in re.findall(r"[{}]|[^\s{}]+", line) if t.rstrip(",")]
    return out


def read_sets(text):
    """(tile sets {name: {'flags', 'files', 'geoms' {geom: (part, (t, b, l, r))}, 'links' {link: (geom, degrees)},
    'overlays' {underlay part: [(overlay part, {water, lava, strips, alpha: (page, cx, cz, degrees)})]}}},
    alpha pages {name: (file, across, up)}) of descr_aerial_map_tile_models.txt."""
    toks, i = _tokens(text), 0
    sets, pages = {}, {}

    def block():                                  # the tokens between a '{' at i and its '}'
        nonlocal i
        if i >= len(toks) or toks[i] != "{":
            return []
        depth, start = 0, i
        while i < len(toks):
            if toks[i] == "{":
                depth += 1
            elif toks[i] == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    return toks[start + 1:i - 1]
            i += 1
        return toks[start + 1:]

    while i < len(toks):
        t = toks[i]
        i += 1
        if t == "alpha_page" and i < len(toks):
            name = toks[i]
            i += 1
            b = block()
            d = {b[k]: b[k + 1] for k in range(0, len(b) - 1, 2)}
            try:
                pages[name] = (d.get("filename", ""), int(d.get("cells_across", 1)), int(d.get("cells_up", 1)))
            except ValueError:
                pass
        elif t == "tile_set" and i < len(toks):
            name = toks[i]
            i += 1
            sets[name] = _tile_set(block())
    return sets, pages


def _tile_set(body):
    s = {"flags": set(), "files": [], "geoms": {}, "links": {}, "overlays": {}}
    j = 0

    def sub(j):
        depth, start = 0, j
        while j < len(body):
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
                if depth == 0:
                    return body[start + 1:j], j + 1
            j += 1
        return body[start + 1:], j
    while j < len(body):
        t = body[j]
        if t == "model_files":
            b, j = sub(j + 1)
            s["files"] = [x for x in b if x not in "{}"]
        elif t == "geom" and j + 1 < len(body):
            name = body[j + 1]
            b, j = sub(j + 2)
            if len(b) >= 5:
                s["geoms"][name] = (b[0], tuple(x.lower() == "true" for x in b[1:5]))
        elif t == "geom_links":
            b, j = sub(j + 1)
            for k in range(0, len(b) - 2, 3):
                m = re.match(r"rotation_(\d+)", b[k + 2])
                s["links"][b[k]] = (b[k + 1], int(m.group(1)) if m else 0)
        elif t == "overlay" and j + 1 < len(body):
            under = body[j + 1]
            b, j = sub(j + 2)
            k, got = 0, []
            while k < len(b):
                part = b[k]
                if k + 1 < len(b) and b[k + 1] == "{":
                    depth, start = 0, k + 1
                    e = start
                    while e < len(b):
                        if b[e] == "{":
                            depth += 1
                        elif b[e] == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        e += 1
                    opts = b[start + 1:e]
                    o = {"water": "water" in opts, "lava": "lava" in opts, "strips": 0, "alpha": None}
                    if "texture_uv_strips" in opts:
                        try:
                            o["strips"] = int(opts[opts.index("texture_uv_strips") + 1])
                        except (ValueError, IndexError):
                            pass
                    if "alpha_page" in opts:
                        a = opts[opts.index("alpha_page") + 1:opts.index("alpha_page") + 5]
                        try:
                            m = re.match(r"rotation_(\d+)", a[3])
                            o["alpha"] = (a[0], int(a[1]), int(a[2]), int(m.group(1)) if m else 0)
                        except (ValueError, IndexError):
                            pass
                    got.append((part, o))
                    k = e + 1
                else:
                    k += 1
            s["overlays"].setdefault(under, []).extend(got)
        else:
            if t not in "{}":
                s["flags"].add(t)
            j += 1
    return s


def _hash(x, z, salt):
    h = (x * 73856093) ^ (z * 19349663) ^ (salt * 83492791) ^ 0x5bd1e995
    h = (h ^ (h >> 13)) * 0x5bd1e995 & 0xffffffff
    return (h ^ (h >> 15)) & 0xffffffff


def rnd(x, z, salt, n):
    """A stable pick 0 .. n-1 for tile (x, z) - in place of the game's random number for that tile and draw."""
    return _hash(x, z, salt) % max(1, n)


def tile_types(ground_rgb, keys=(MOUNTAINS_HIGH, HILLS)):
    """{key: (H, W) bool} of the tiles whose centre point (map_ground_types.tga, 2W + 1 x 2H + 1) is that ground,
    rows bottom first (z up)."""
    gi = T3._ground_index(ground_rgb, list(keys))
    centre = gi[1::2, 1::2][::-1]
    return {k: centre == n for n, k in enumerate(keys)}


def assign(heights, ground_rgb, features_rgb=None):
    """(H, W) int32 tile model index of every tile (-1: none), rows bottom first (z up), and the seed of each tile
    (its piece's), the way the engine's map building places them (volcanoes, mountains, hills)."""
    rows, cols = heights.shape
    H, W = (rows - 1) // 2, (cols - 1) // 2
    idx = np.full((H, W), -1, np.int32)
    seed = np.zeros((H, W), np.int32)
    if ground_rgb is None or ground_rgb.shape[:2] != heights.shape:
        return idx, seed
    types = tile_types(ground_rgb)
    # a tile's 9 points all above the sea (hills need it)
    up = heights[::-1] > 0                                   # bottom row first
    dry = np.ones((H, W), bool)
    for dz in range(3):
        for dx in range(3):
            dry &= up[dz:dz + 2 * H:2, dx:dx + 2 * W:2]
    # volcanoes: the dormant set's 3 x 3 round every red pixel of map_features (the game always passes dormant)
    if features_rgb is not None and features_rgb.shape[:2] == (H, W):
        f = features_rgb[::-1]
        red = (f[..., 0] == 255) & (f[..., 1] == 0) & (f[..., 2] == 0)
        for z, x in zip(*np.nonzero(red)):
            for k, (dx, dz) in enumerate(((-1, 1), (0, 1), (1, 1), (-1, 0), (0, 0), (1, 0), (-1, -1), (0, -1),
                                          (1, -1))):
                tx, tz = x + dx, z + dz
                if 0 <= tx < W and 0 <= tz < H:
                    idx[tz, tx] = 145 + k
    _mountains(idx, seed, types[MOUNTAINS_HIGH])
    _hills(idx, seed, types[HILLS] & dry)
    return idx, seed


def _rotated(slots, rot):
    out = []
    for gx, gy in slots:
        for _ in range(rot):
            gx, gy = gy, 3 - gx
        out.append((gx, gy))
    return out


ROTATED = {(p, r): _rotated(SLOTS[p], r) for p in MOUNTAIN_PIECES for r in range(4)}


def _mountains(idx, seed, high):
    """The 'tetris' fitting of the high mountains (world_map calculate_mountains): a 4 x 4 window moved over the map
    in steps of 4, then 3, 2, 1; where some pieces fit into its free mountain tiles one is picked; what stays is a
    single (turned at random). The map's top row and right column take singles only, as in the game."""
    H, W = idx.shape
    inc = 4
    while True:
        placed = False
        free = high & (idx < 0)
        if free.sum() < 4:
            break
        ii = np.pad(free.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        for z in range(0, H - 4, inc):
            for x in range(0, W - 4, inc):
                if ii[z + 4, x + 4] - ii[z, x + 4] - ii[z + 4, x] + ii[z, x] < 4:
                    continue
                win = free[z:z + 4, x:x + 4]
                if win.sum() < 4:
                    continue
                cands = [(p, r) for p in MOUNTAIN_PIECES for r in range(4)
                         if all(win[gy, gx] for gx, gy in ROTATED[(p, r)])]
                if not cands:
                    continue
                p, r = cands[rnd(x, z, 1, len(cands))]
                cells = ROTATED[(p, r)]
                s = _hash(x + cells[0][0], z + cells[0][1], 2) & 0xff
                for slot, (gx, gy) in enumerate(cells):
                    idx[z + gy, x + gx] = 181 + MOUNTAIN_PIECES.index(p) * 16 + slot * 4 + r
                    seed[z + gy, x + gx] = s
                    free[z + gy, x + gx] = False
                placed = True
        if placed:
            inc = max(1, inc - 1)
            continue
        if inc == 1:
            break
        inc -= 1
    zs, xs = np.nonzero(high & (idx < 0))
    for z, x in zip(zs.tolist(), xs.tolist()):
        idx[z, x] = 293 + rnd(x, z, 3, 4)
        seed[z, x] = rnd(x, z, 4, 256)


def _hills(idx, seed, hills):
    """Hills (world_map calculate_hills): a 2 x 2 hill (hill13-16, its four parts) where four hill tiles above the
    sea meet, then on half of the hill tiles left a single (hill1-12: three hills turned four ways, or hills1-4)."""
    H, W = idx.shape
    for z in range(H - 1):
        for x in range(W - 1):
            if hills[z, x] and hills[z, x + 1] and hills[z + 1, x] and hills[z + 1, x + 1] and \
                    idx[z, x] < 0 and idx[z, x + 1] < 0 and idx[z + 1, x] < 0 and idx[z + 1, x + 1] < 0:
                tl = 309 + 4 * rnd(x, z, 5, 4)
                idx[z + 1, x], idx[z + 1, x + 1], idx[z, x], idx[z, x + 1] = tl, tl + 1, tl + 2, tl + 3
    zs, xs = np.nonzero(hills & (idx < 0))
    for z, x in zip(zs.tolist(), xs.tolist()):
        if rnd(x, z, 6, 2):
            continue
        idx[z, x] = 297 + rnd(x, z, 7, 12) if rnd(x, z, 8, 4) else 325 + rnd(x, z, 9, 4)


class Library:
    """The tile sets of a mod with their .cas parts read (once): model(set, link) -> the pieces to draw."""

    def __init__(self, mod):
        self.mod = mod
        p = mod.find("descr_aerial_map_tile_models.txt")
        text = ""
        if p:
            with open(p, "rb") as fh:
                text = fh.read().decode("latin-1")
        self.sets, self.pages = read_sets(text)
        self._parts = {}
        self._models = {}
        self.missing = set()

    def parts(self, tile_set):
        """{part name (lower case): stratcas.Part} of a tile set's .cas files."""
        if tile_set not in self._parts:
            got = {}
            for f in self.sets.get(tile_set, {}).get("files", []):
                path = self.mod.find_any("terrain/aerial_map/tile_models/%s/%s" % (tile_set, f))
                if not path:
                    self.missing.add(f)
                    continue
                try:
                    with open(path, "rb") as fh:
                        for part in stratcas.read(fh.read()):
                            got.setdefault(part.name.lower(), part)
                except (OSError, stratcas.CasError):
                    self.missing.add(f)
            self._parts[tile_set] = got
        return self._parts[tile_set]

    def model(self, tile_set, link):
        """(underlay Part, degrees, [(overlay Part, options, which underlay point each of its points is)], set's
        flags) for a link, or None."""
        key = (tile_set, link)
        if key in self._models:
            return self._models[key]
        out = None
        s = self.sets.get(tile_set)
        if s and link in s["links"]:
            geom, deg = s["links"][link]
            g = s["geoms"].get(geom)
            parts = self.parts(tile_set)
            under = parts.get(g[0].lower()) if g else None
            if under is not None:
                up = np.asarray(under.positions, np.float64).reshape(-1, 3)
                ovs = []
                for name, opts in s["overlays"].get(g[0], []):
                    o = parts.get(name.lower())
                    if o is None:
                        continue
                    op = np.asarray(o.positions, np.float64).reshape(-1, 3)
                    d = ((op[:, None, :] - up[None, :, :]) ** 2).sum(-1)
                    ovs.append((o, opts, d.argmin(1)))     # an overlay point takes its underlay point's place
                out = (under, deg, ovs, s["flags"])
        self._models[key] = out
        return out


def turn(x, z, deg):
    """A model's (x, z) turned clockwise seen from above (the engine's rotation_N, +z north)."""
    if deg == 90:
        return z, -x
    if deg == 180:
        return -x, -z
    if deg == 270:
        return -z, x
    return x, z


def _ground_h(heights, prow, pcol):
    """Bilinear ground height (metres) on the points' grid at fractional (row, col)."""
    rows, cols = heights.shape
    r0 = np.clip(np.floor(prow).astype(np.int64), 0, rows - 2)
    c0 = np.clip(np.floor(pcol).astype(np.int64), 0, cols - 2)
    fr, fc = np.clip(prow - r0, 0, 1), np.clip(pcol - c0, 0, 1)
    h = heights
    return (h[r0, c0] * (1 - fr) * (1 - fc) + h[r0, c0 + 1] * (1 - fr) * fc + h[r0 + 1, c0] * fr * (1 - fc) +
            h[r0 + 1, c0 + 1] * fr * fc)


def build(lib, idx, seed, heights, yscale):
    """The tile models laid on the map, as arrays for the card: {'under': (vertices (n, 7): x y z, normal, kind),
    'over': {(texture file, alpha page): (vertices (n, 15): x y z, normal, u v, alpha u v, r g b a, kind)}} - triangles as vertex
    triples (no index lists); our world: x east, y up, z SOUTH from the map's top (tiles)."""
    H, W = idx.shape
    under, over = [], {}
    groups = {}
    for z, x in zip(*np.nonzero(idx >= 0)):
        groups.setdefault(int(idx[z, x]), []).append((int(x), int(z)))
    for index, tiles in groups.items():
        got = link_of(index)
        m = lib.model(*got) if got else None
        if m is None:
            continue
        kind = KIND.get(got[0], 1)
        part, deg, ovs, flags = m
        P = np.asarray(part.positions, np.float64).reshape(-1, 3)
        F = np.asarray(part.faces, np.int64).reshape(-1, 3)
        tx, tz = turn(P[:, 0], P[:, 2], deg)
        u, w = tx + 0.5, tz + 0.5
        T = np.asarray(tiles, np.float64)                        # (n, 2): x, z (z up)
        top = (H - 1 - T[:, 1])                                   # the tile's row from the map's top
        prow = 2 * top[:, None] + 2 * (1 - w)[None, :]
        pcol = 2 * T[:, 0][:, None] + 2 * u[None, :]
        Y = P[None, :, 1] + _ground_h(heights, prow, pcol) * yscale
        X = T[:, 0][:, None] + u[None, :]
        Z = top[:, None] + (1 - w)[None, :]
        V = np.stack([X, Y, Z], -1)                               # (n, v, 3)
        A, B, C = V[:, F[:, 0]], V[:, F[:, 1]], V[:, F[:, 2]]
        fn = np.cross(B - A, C - A)
        fn *= np.where(fn[..., 1:2] < 0, -1.0, 1.0)              # the faces look up (our z runs south)
        vn = np.zeros_like(V)
        for k in range(3):
            np.add.at(vn, (slice(None), F[:, k]), fn)
        vn /= np.maximum(np.linalg.norm(vn, axis=-1, keepdims=True), 1e-9)
        dx = (_ground_h(heights, prow, pcol + 0.5) - _ground_h(heights, prow, pcol - 0.5)) * yscale
        dz = (_ground_h(heights, prow + 0.5, pcol) - _ground_h(heights, prow - 0.5, pcol)) * yscale
        gn = np.stack([-dx, np.full_like(dx, 0.5), -dz], -1)
        gn /= np.linalg.norm(gn, axis=-1, keepdims=True)
        if "underlay_up_normals" in flags:              # the ground's own normal under each point (mountains)
            vn = gn
        else:                                           # the points on the tile's edge as the ground beside them
            edge = (np.abs(P[:, 0]) > 0.495) | (np.abs(P[:, 2]) > 0.495)
            vn[:, edge] = gn[:, edge]
        if part.texture is None or "dummy" in (part.texture or "").lower():
            tri = np.concatenate([V[:, F].reshape(len(T), -1, 3), vn[:, F].reshape(len(T), -1, 3),
                                  np.full((len(T), F.size, 1), float(kind))], -1)
            under.append(tri.reshape(-1, 7))
        for o, opts, which in ovs:
            if opts["water"] or opts["lava"] or not o.texture:
                continue                                          # the rivers' and lava's water: later
            OF = np.asarray(o.faces, np.int64).reshape(-1, 3)
            OV = V[:, which]
            if "seperate_overlay_normals" in flags:
                on = np.asarray(o.normals, np.float64).reshape(-1, 3)
                nx, nz = turn(on[:, 0], on[:, 2], deg)
                ON = np.broadcast_to(np.stack([nx, on[:, 1], -nz], -1), OV.shape)
            else:
                ON = vn[:, which]
            uv = np.asarray(o.uvs if o.uvs else [0.0] * (2 * len(which)), np.float64).reshape(-1, 2)
            UV = np.broadcast_to(uv, (len(T),) + uv.shape).copy()
            if opts["strips"]:
                s = np.asarray([seed[tz_, tx_] for tx_, tz_ in tiles])
                UV[..., 1] += (np.asarray([_hash(int(v), int(v) * 256, 10) % opts["strips"] for v in s]) /
                               float(opts["strips"]))[:, None]
            AUV = np.zeros_like(UV)
            col = np.ones((len(which), 4))
            if o.colours:
                col = np.frombuffer(o.colours, np.uint8).reshape(-1, 4) / 255.0
            if opts["alpha"] and opts["alpha"][0] in lib.pages:
                _, across, upn = lib.pages[opts["alpha"][0]]
                op = np.asarray(o.positions, np.float64).reshape(-1, 3)
                ax, az = turn(op[:, 0], op[:, 2], opts["alpha"][3])
                cx, cz = ax + opts["alpha"][1] + 0.5, az + opts["alpha"][2] + 0.5
                AUV[:] = np.stack([np.clip(cx / across, 0, 1), np.clip(1 - cz / upn, 0, 1)], -1)
                col[:, :3], col[:, 3] = 1.0, -1.0                 # white, the mask's alpha (the engine's own)
            COL = np.broadcast_to(col, (len(T),) + col.shape)
            tri = np.concatenate([OV[:, OF].reshape(len(T), -1, 3), np.asarray(ON)[:, OF].reshape(len(T), -1, 3),
                                  UV[:, OF].reshape(len(T), -1, 2), AUV[:, OF].reshape(len(T), -1, 2),
                                  COL[:, OF].reshape(len(T), -1, 4), np.full((len(T), OF.size, 1), float(kind))], -1)
            over.setdefault((o.texture, opts["alpha"][0] if opts["alpha"] else None), []).append(tri.reshape(-1, 15))
    return {"under": np.concatenate(under).astype(np.float32) if under else np.zeros((0, 7), np.float32),
            "over": {k: np.concatenate(v).astype(np.float32) for k, v in over.items()}}


def void_map(idx):
    """(H, W) uint8 of what a tile's ground gives way to, top row first: 0 nothing, else KIND (1 mountains and
    volcanoes, 2 hills) - the 3D map leaves that ground out while that Layers switch shows the models."""
    out = np.zeros(idx.shape, np.uint8)
    for index in np.unique(idx[idx >= 0]):
        got = link_of(int(index))
        if got:
            out[idx == index] = KIND.get(got[0], 1)
    return out[::-1].copy()


def texture_rel(name, climate=None, winter=False):
    """The paths under data/ to try for a tile model's texture: the climate's own, the winter one, the base."""
    base = "terrain/aerial_map/tile_textures/"
    out = []
    if climate:
        out.append(base + "%s/%s/%s" % (climate, "winter" if winter else "summer", name))
    if winter:
        out.append(base + "winter/" + name)
    out.append(base + name)
    return out


__all__ = ["read_sets", "link_of", "assign", "Library", "build", "void_map", "turn", "texture_rel", "rnd"]
