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
KIND = {"mountains": 1, "hills": 2, "volcano": 1, "volcano_dormant": 1, "river_a": 3, "cliffs": 4}   # its Layers switch
NONE, CLIFF, NEAR_COAST, BEACH, END_CW, END_ACW, END_DBL, NOT_CLIFF, NOT_NEAR_COAST = range(9)   # a tile's cliff state
# the engine's cliff templates (world_map m_cliff_templates): (centre, top, bottom, left, right), the model index at
# 0 / 90 / 180 / 270 degrees - the first that fits (turned) wins
CLIFF_TEMPLATES = (
    ((CLIFF, NEAR_COAST, NOT_NEAR_COAST, NOT_NEAR_COAST, NOT_NEAR_COAST), (154, 157, 155, 156)),     # wall
    ((CLIFF, NEAR_COAST, NOT_NEAR_COAST, NEAR_COAST, NOT_NEAR_COAST), (158, 159, 161, 160)),         # corner
    ((CLIFF, NEAR_COAST, NOT_NEAR_COAST, NEAR_COAST, NEAR_COAST), (162, 165, 163, 164)),             # outcrop
    ((CLIFF, NEAR_COAST, NEAR_COAST, NEAR_COAST, NEAR_COAST), (166, 166, 166, 166)),                 # pillar
    ((CLIFF, NEAR_COAST, NEAR_COAST, NOT_NEAR_COAST, NOT_NEAR_COAST), (167, 168, 167, 168)),         # bridge
    ((END_CW, NOT_CLIFF, NOT_CLIFF, CLIFF, NOT_CLIFF), (172, 170, 171, 169)),
    ((END_ACW, NOT_CLIFF, NOT_CLIFF, NOT_CLIFF, CLIFF), (175, 173, 176, 174)),
    ((END_DBL, NOT_CLIFF, NOT_CLIFF, NOT_CLIFF, CLIFF), (179, 177, 180, 178)))
CLIFF_LINKS = ("wall_1_top", "wall_1_bottom", "wall_1_left", "wall_1_right", "corner_1_tl", "corner_1_tr",
               "corner_1_bl", "corner_1_br", "outcrop_1_top", "outcrop_1_bottom", "outcrop_1_left",
               "outcrop_1_right", "pillar_1", "bridge_1_horizontal", "bridge_1_vertical", "end_cw_1_top",
               "end_cw_1_bottom", "end_cw_1_left", "end_cw_1_right", "end_acw_1_top", "end_acw_1_bottom",
               "end_acw_1_left", "end_acw_1_right", "end_dbl_1_top", "end_dbl_1_bottom", "end_dbl_1_left",
               "end_dbl_1_right")
SIDES = ("top", "bottom", "left", "right")
LINE_KINDS = ("", "b_", "c_", "bg_", "bi_", "ag_", "ah_", "ai_", "cg_", "ch_", "ci_")
SPLITS = ("t_out_lr", "t_out_lb", "t_out_rb", "b_out_lr", "b_out_lt", "b_out_rt", "l_out_tb", "l_out_tr",
          "l_out_br", "r_out_tb", "r_out_tl", "r_out_bl")
JOINS = ("t_in_lr", "t_in_lb", "t_in_rb", "b_in_lr", "b_in_lt", "b_in_rt", "l_in_tb", "l_in_tr", "l_in_br",
         "r_in_tb", "r_in_tl", "r_in_bl")
LINE, BEND_CW, BEND_ACW, SPLIT, JOIN, SOURCE, END, FORD = 0, 44, 60, 76, 88, 100, 104, 108
# the engine's index of each river join / split by its sides: (out, ins) / (in, outs), sides t b l r
JOIN_OF = {(name[0], frozenset(name[-2:])): k for k, name in enumerate(JOINS)}


def link_of(index):
    """(tile set, link name) of an AERIAL_MAP_TILE_MODEL_INDEX the code places, or None."""
    if 0 <= index < 44:
        return "river_a", "line_%s%s" % (LINE_KINDS[index % 11], SIDES[index // 11])
    if 44 <= index < 76:
        k = (index - 44) % 16
        return "river_a", "bend_%s_%s%s" % ("cw" if index < 60 else "acw", ("", "b_", "c_", "d_")[k % 4],
                                            ("tl", "tr", "bl", "br")[k // 4])
    if 76 <= index < 88:
        return "river_a", "split_in_" + SPLITS[index - 76]
    if 88 <= index < 100:
        return "river_a", "join_out_" + JOINS[index - 88]
    if 100 <= index < 112:
        return "river_a", "%s_%s" % (("source", "end", "ford")[(index - 100) // 4], SIDES[(index - 100) % 4])
    if 136 <= index <= 153:
        return ("volcano" if index < 145 else "volcano_dormant"), VOLCANO_PARTS[(index - 136) % 9]
    if 154 <= index <= 180:
        return "cliffs", CLIFF_LINKS[index - 154]
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
    s = {"flags": set(), "files": [], "geoms": {}, "links": {}, "overlays": {}, "knit": {}}
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
            corners, k = (True,) * 4, 0                 # a 'corners tl tr bl br' line; the model's line: t b l r
            while k + 4 < len(b):
                flags = tuple(x.lower() == "true" for x in b[k + 1:k + 5])
                if b[k].lower() == "corners":
                    corners = flags
                elif name not in s["geoms"]:
                    s["geoms"][name] = (b[k], flags)
                k += 5
            if name in s["geoms"]:                      # the points of its rim that meet the ground (the knit)
                t, bo, le, ri = s["geoms"][name][1]
                s["knit"][name] = {n for n, on in zip(("t", "b", "l", "r", "tl", "tr", "bl", "br"),
                                                     (t, bo, le, ri) + corners) if on}
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


def assign(heights, ground_rgb, features_rgb=None, towns=()):
    """(H, W) int32 tile model index of every tile (-1: none), rows bottom first (z up), and the seed of each tile
    (its piece's), the way the engine's map building places them (volcanoes, rivers, mountains, hills, cliffs).
    towns: (x, z up) of the towns and ports (no cliffs within 2 tiles of them)."""
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
    if features_rgb is not None and features_rgb.shape[:2] == (H, W):
        rivers(idx, features_rgb[::-1])
    _mountains(idx, seed, types[MOUNTAINS_HIGH])
    _hills(idx, seed, types[HILLS] & dry)
    if features_rgb is not None and features_rgb.shape[:2] == (H, W):
        f = features_rgb[::-1]
        code = (f[..., 0].astype(np.int32) << 16) | (f[..., 1].astype(np.int32) << 8) | f[..., 2]
        sea = heights[::-1][1::2, 1::2][:H, :W] <= 0           # a tile's centre point at or below the sea's level
        cliffs(idx, sea, code == 0xffff00, np.isin(code, (0x0000ff, 0x00ffff, 0xffffff)), towns)
    return idx, seed


def cliff_states(sea, painted, rivers, towns=()):
    """(H, W) cliff state of every tile (world_map calculate_cliffs with the cliffs as painted): the yellow tiles
    cliffs; sea tiles beside a coastal land tile 'near the coast'; cliffs within 2 tiles of a river or a town /
    port a beach, then (again and again) cliffs within 1 of a beach touching two cliffs; a coastal land tile beside
    one cliff its end (clockwise, anticlockwise or both by the sea tiles beyond)."""
    H, W = sea.shape
    st = np.where(painted & ~sea, CLIFF, NONE).astype(np.int8)
    pad = np.pad(sea, 1)
    near = np.zeros_like(sea)                                 # a land tile with sea among its 8 neighbours
    for dz in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dz or dx:
                near |= pad[1 + dz:1 + dz + H, 1 + dx:1 + dx + W]
    coastal = near & ~sea
    padc = np.pad(coastal, 1)
    around = np.zeros_like(sea)
    for dz in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dz or dx:
                around |= padc[1 + dz:1 + dz + H, 1 + dx:1 + dx + W]
    st[sea & around] = NEAR_COAST

    def remove(x, z, r):
        z0, z1, x0, x1 = max(0, z - r), min(H, z + r + 1), max(0, x - r), min(W, x + r + 1)
        box = st[z0:z1, x0:x1]
        box[box == CLIFF] = BEACH
    for z, x in zip(*np.nonzero(rivers)):
        remove(x, z, 2)
    for x, z in towns:
        if 0 <= x < W and 0 <= z < H:
            remove(x, z, 2)

    def state(x, z):
        return int(st[z, x]) if 0 <= x < W and 0 <= z < H else NONE
    changed = True
    while changed:                                            # cliff_sanity_pass
        changed = False
        for z, x in zip(*np.nonzero(st == BEACH)):
            if sum(state(x + dx, z + dz) == CLIFF for dx, dz in ((0, 1), (0, -1), (-1, 0), (1, 0))) > 1:
                before = int((st == CLIFF).sum())
                remove(x, z, 1)
                changed = changed or int((st == CLIFF).sum()) != before
    for z, x in zip(*np.nonzero(coastal & (st != CLIFF))):    # place_cliff_ends
        hits = [(dx, dz) for dx, dz in ((0, 0), (0, 1), (0, -1), (-1, 0), (1, 0)) if state(x + dx, z + dz) == CLIFF]
        if len(hits) != 1:
            continue
        dx, dz = hits[0]
        beyond = {(0, 1): ((1, 1), (-1, 1)), (0, -1): ((-1, -1), (1, -1)), (-1, 0): ((-1, 1), (-1, -1)),
                  (1, 0): ((1, -1), (1, 1))}.get((dx, dz))
        if beyond is None:
            continue
        a, b = (state(x + ox, z + oz) == NEAR_COAST for ox, oz in beyond)
        if a or b:
            st[z, x] = END_DBL if a and b else END_CW if a else END_ACW
    return st


def _matches(a, b):
    return a == b or (a == NOT_CLIFF and b != CLIFF) or (b == NOT_CLIFF and a != CLIFF) or \
        (a == NOT_NEAR_COAST and b != NEAR_COAST) or (b == NOT_NEAR_COAST and a != NEAR_COAST)


def cliffs(idx, sea, painted, rivers, towns=()):
    """The cliff models of the tiles still without a model (world_map calculate_cliff_models): each tile's state
    and its four neighbours' against the engine's templates, each turned four ways; the first that fits."""
    H, W = idx.shape
    st = cliff_states(sea, painted, rivers, towns)

    def state(x, z):
        return int(st[z, x]) if 0 <= x < W and 0 <= z < H else NONE
    for z, x in zip(*np.nonzero((st != NONE) & (st != NEAR_COAST) & (st != BEACH) & (idx < 0))):
        here = (state(x, z), state(x, z + 1), state(x, z - 1), state(x - 1, z), state(x + 1, z))
        for (c, t, b, l, r), indices in CLIFF_TEMPLATES:
            hit = None
            for rot in range(4):
                if all(_matches(u, v) for u, v in zip(here, (c, t, b, l, r))):
                    hit = indices[rot]
                    break
                t, b, l, r = l, r, b, t                         # the template turned 90 degrees on
            if hit is not None:
                idx[z, x] = hit
                break


def _river_index(f, t, x, z):
    """The engine's river model for a tile entered from sides f and left by sides t (sets of 't' 'b' 'l' 'r'),
    first match wins (world_map route_river): joins, splits, lines, clockwise / anticlockwise bends, ends."""
    if len(t) == 1 and len(f) == 2:
        k = JOIN_OF.get((next(iter(t)), frozenset(f)))
        if k is not None:
            return JOIN + k
    if len(f) == 1 and len(t) == 2:
        k = JOIN_OF.get((next(iter(f)), frozenset(t)))
        if k is not None:
            return SPLIT + k
    alt3, alt4 = rnd(x, z, 11, 3), rnd(x, z, 12, 4)
    for (a, b), base in ((("l", "r"), 0), (("r", "l"), 11), (("b", "t"), 22), (("t", "b"), 33)):
        if a in f and b in t:
            return LINE + base + alt3
    for (a, b), k in ((("b", "r"), 0), (("l", "b"), 4), (("r", "t"), 8), (("t", "l"), 12)):
        if a in f and b in t:
            return BEND_CW + k + alt4
    for (a, b), k in ((("r", "b"), 0), (("b", "l"), 4), (("t", "r"), 8), (("l", "t"), 12)):
        if a in f and b in t:
            return BEND_ACW + k + alt4
    for a, k in (("l", 0), ("r", 1), ("b", 2), ("t", 3)):
        if a in f:
            return END + k
    return None


STEP = {"t": (0, 1), "b": (0, -1), "l": (-1, 0), "r": (1, 0)}
BACK = {"t": "b", "b": "t", "l": "r", "r": "l"}


def rivers(idx, feats):
    """The rivers of map_features.tga (rows bottom first: white source, blue river, cyan ford) routed from each
    source the way the engine does (world_map route_rivers): every river tile asks its neighbours in turn (up,
    down, left, right) whether the river goes on there, a second river reaching a tile already routed makes it a
    join; a dead end touching another river is refused; then the source's own model and the meanders of the long
    straight runs (apply_river_variations)."""
    H, W = idx.shape
    code = (feats[..., 0].astype(np.int32) << 16) | (feats[..., 1].astype(np.int32) << 8) | feats[..., 2]
    source = code == 0xffffff
    ford = code == 0x00ffff
    river = (code == 0x0000ff) | ford
    dirs = {}                                         # (x, z): (sides it is entered from, sides it leaves by)

    def valid(x, z):
        return 0 <= x < W and 0 <= z < H

    def route(fx, fz, x, z):                          # a generator: yields the neighbour to try, gets its answer
        if not valid(x, z) or not river[z, x] or source[z, x]:
            return False
        f = {"t" if fz > z else "b" if fz < z else "l" if fx < x else "r"}
        t = set()
        if (x, z) in dirs:                            # routed before: its own sides kept (a join forms)
            f |= dirs[(x, z)][0]
            t |= dirs[(x, z)][1]
        for side in "tblr":
            if side not in f and side not in t:
                dx, dz = STEP[side]
                if (yield (x, z, x + dx, z + dz)):
                    t.add(side)
        if len(f) + len(t) == 1:                      # a dead end beside another river: not this way
            for side in "tblr":
                if side in f:
                    continue
                nx, nz = x + STEP[side][0], z + STEP[side][1]
                if valid(nx, nz) and (river[nz, nx] or source[nz, nx]):
                    return False
        index = _river_index(f, t, x, z)
        if index is None:
            return False
        if ford[z, x] and LINE <= index < LINE + 44 and index % 11 < 3:
            index = FORD + index // 11
        idx[z, x] = index
        dirs[(x, z)] = (f, t)
        return True

    def run(fx, fz, x, z):                            # the recursion without Python's own stack (long rivers)
        stack, answer = [route(fx, fz, x, z)], None
        while stack:
            try:
                ask = stack[-1].send(answer) if answer is not None else next(stack[-1])
                answer = None
                stack.append(route(*ask))
            except StopIteration as e:
                stack.pop()
                answer = bool(e.value)
        return bool(answer)
    zs, xs = np.nonzero(source[::-1])                 # the picture's order: top row first
    for z, x in zip((H - 1 - zs).tolist(), xs.tolist()):
        got = [run(x, z, x + dx, z + dz) for dx, dz in ((0, 1), (0, -1), (-1, 0), (1, 0))]
        for ok, k in zip(got, (2, 3, 1, 0)):          # up: source_left, down: _right, left: _bottom, right: _top
            if ok:
                idx[z, x] = SOURCE + k
                break
    _meanders(idx)


def _meanders(idx):
    """The long straight river runs wind between three lanes (world_map apply_river_variations): each run of plain
    lines gets crossing places at its tiles' edges - the run's two ends in the middle lane, the others any - and
    each tile the piece that goes from its in-lane to its out-lane."""
    H, W = idx.shape
    k = 0
    combo = {(0, 0): 8, (0, 1): 9, (0, 2): 10, (1, 0): 3, (1, 2): 4, (2, 0): 5, (2, 1): 6, (2, 2): 7}

    def plain(v, base):
        return base <= v < base + 3

    def wind(tiles, base):
        nonlocal k
        edges = [1] + [_hash(k, i, 13) % 3 for i in range(1, len(tiles))] + [1]
        k += 1
        for i, (x, z) in enumerate(tiles):
            e = (edges[i], edges[i + 1])
            if e != (1, 1):
                idx[z, x] = LINE + base + combo[e]
    for z in range(H):                                 # flowing right (line_*top) or left (line_*bottom)
        x = 0
        while x < W:
            for base, step in ((0, 1), (11, -1)):
                if plain(idx[z, x], base):
                    e = x
                    while e < W and plain(idx[z, e], base):
                        e += 1
                    if e - x > 1:
                        run = [(c, z) for c in range(x, e)]
                        wind(run if step == 1 else run[::-1], base)
                    x = e - 1
                    break
            x += 1
    for x in range(W):                                 # flowing up (line_*left) or down (line_*right)
        z = 0
        while z < H:
            for base, step in ((22, 1), (33, -1)):
                if plain(idx[z, x], base):
                    e = z
                    while e < H and plain(idx[e, x], base):
                        e += 1
                    if e - z > 1:
                        run = [(x, r) for r in range(z, e)]
                        wind(run if step == 1 else run[::-1], base)
                    z = e - 1
                    break
            z += 1


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
        flags + 'knit_<point>' for each rim point (t b l r tl tr bl br) that meets the ground) for a link, or None."""
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
                    # an overlay point takes its underlay point's place (the engine matches within 0.005); one
                    # with none so near (a river's water a little above its bed) is laid on the ground itself
                    ovs.append((o, opts, d.argmin(1), d.min(1) < 0.006 ** 2))
                out = (under, deg, ovs, set(s["flags"]) | {"knit_" + n for n in s["knit"].get(geom, ())})
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


def _edge_points(P, flags):
    """[(indices of the model's points standing there, (x, z))] for the tile's 4 corners and 4 edge middles its geom
    knits to the ground ('knit_t' ... in flags) that have points (the engine's tolerance 0.005), in the model's own
    unturned frame (+z the top)."""
    out = []
    for px in (-0.5, 0.0, 0.5):
        for pz in (-0.5, 0.0, 0.5):
            name = {0.5: "t", -0.5: "b", 0.0: ""}[pz] + {-0.5: "l", 0.5: "r", 0.0: ""}[px]
            if not name or "knit_" + name not in flags:
                continue
            sel = np.nonzero((np.abs(P[:, 0] - px) < 0.005) & (np.abs(P[:, 2] - pz) < 0.005))[0]
            if len(sel):
                out.append((sel, (px, pz)))
    return out


def _rim(P, F):
    """(k, 2) the model's open edges (used by one face) lying along one side of the tile."""
    e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    u, n = np.unique(e, axis=0, return_counts=True)
    u = u[n == 1]
    if not len(u):
        return u
    out = np.zeros(len(u), bool)
    for ax in (0, 2):
        for side in (-0.5, 0.5):
            on = np.abs(P[:, ax] - side) < 0.005
            out |= on[u[:, 0]] & on[u[:, 1]]
    return u[out]


def build(lib, idx, seed, heights, yscale):
    """The tile models laid on the map, as arrays for the card: {'under': (vertices (n, 7): x y z, normal, kind),
    'over': {(texture file, alpha page): (vertices (n, 15): x y z, normal, u v, alpha u v, r g b a, kind)},
    'water': (vertices (n, 6): x y z, u v, kind) - the rivers' water, 'lift': (rows, cols) world units the ground's
    points rise to meet the models' edges} - triangles as vertex triples (no index lists); our world: x east, y up,
    z SOUTH from the map's top (tiles)."""
    H, W = idx.shape
    under, over, water = [], {}, []
    lift = np.zeros(heights.shape, np.float32)       # how far the ground's points are raised to meet the models' edges

    def place(P, deg, T, top):                    # a model's points on the tiles T, each riding the ground
        tx, tz = turn(P[:, 0], P[:, 2], deg)
        u, w = tx + 0.5, tz + 0.5
        prow = 2 * top[:, None] + 2 * (1 - w)[None, :]
        pcol = 2 * T[:, 0][:, None] + 2 * u[None, :]
        Y = P[None, :, 1] + _ground_h(heights, prow, pcol) * yscale
        return np.stack([T[:, 0][:, None] + u[None, :], Y, top[:, None] + (1 - w)[None, :]], -1), prow, pcol
    groups = {}
    for z, x in zip(*np.nonzero(idx >= 0)):
        groups.setdefault(int(idx[z, x]), []).append((int(x), int(z)))
    # the engine's height_adjustment: a ground corner beside a model whose corner stands HIGH there (two points at
    # one place, a cliff's top over its foot) rises to that top - not where any of the 4 tiles round it is sea
    # (lifting it would drag the shore up); the slit that leaves is closed by the models' skirts below
    sea = heights[::-1][1::2, 1::2][:H, :W] <= 0
    for index, tiles in groups.items():
        got = link_of(index)
        m = lib.model(*got) if got else None
        if m is None:
            continue
        P = np.asarray(m[0].positions, np.float64).reshape(-1, 3)
        for sel, (px, pz) in _edge_points(P, m[3]):
            if abs(px) < 0.4 or abs(pz) < 0.4 or not (P[sel, 1] - P[sel, 1].min() > 0.005).any():
                continue
            tx, tz = turn(np.array([px]), np.array([pz]), m[1])
            for x, z in tiles:
                cx, cz = x + int(round(tx[0] + 0.5)), z + int(round(tz[0] + 0.5))    # the corner, z up
                if any(sea[min(max(b, 0), H - 1), min(max(a, 0), W - 1)]
                       for a in (cx - 1, cx) for b in (cz - 1, cz)):
                    continue
                r, c = 2 * (H - cz), 2 * cx
                if 0 <= r < lift.shape[0] and 0 <= c < lift.shape[1]:
                    lift[r, c] = max(lift[r, c], float(P[sel, 1].max() - P[sel, 1].min()))
    for index, tiles in groups.items():
        got = link_of(index)
        m = lib.model(*got) if got else None
        if m is None:
            continue
        kind = KIND.get(got[0], 1)
        part, deg, ovs, flags = m
        P = np.asarray(part.positions, np.float64).reshape(-1, 3)
        F = np.asarray(part.faces, np.int64).reshape(-1, 3)
        T = np.asarray(tiles, np.float64)                        # (n, 2): x, z (z up)
        top = (H - 1 - T[:, 1])                                   # the tile's row from the map's top
        V, prow, pcol = place(P, deg, T, top)                     # (n, v, 3)
        # the engine's snap: on the tile's corners and edge middles the lowest point of the model IS the ground's
        # point (plus its height_adjustment) - a cliff's raised top comes down to the ground at the tile's edges,
        # so the plain ground beside it meets it with no crack
        for sel, _ in _edge_points(P, flags):
            low = sel[np.argmin(P[sel, 1])]
            r = np.clip(np.round(prow[:, low]).astype(np.int64), 0, heights.shape[0] - 1)
            c = np.clip(np.round(pcol[:, low]).astype(np.int64), 0, heights.shape[1] - 1)
            V[:, low, 1] = heights[r, c] * yscale + (0.0 if (P[sel, 1] - P[low, 1] > 0.005).any() else lift[r, c])
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
            # the skirt: where the model's rim on the tile's edge stands above the ground beside it (a cliff's high
            # corner the ground may not rise to), a strip of ground from the rim down to the ground - no slit
            rim = _rim(P, F)
            if len(rim):
                g = _ground_h(heights, prow, pcol) * yscale + _ground_h(lift, prow, pcol)
                a_, b_ = rim[:, 0], rim[:, 1]
                up = np.maximum(V[:, a_, 1] - g[:, a_], V[:, b_, 1] - g[:, b_]) > 0.002     # (n tiles, rims)
                if up.any():
                    G = V.copy()
                    G[..., 1] = g
                    q = np.stack([V[:, a_], V[:, b_], G[:, b_], V[:, a_], G[:, b_], G[:, a_]], 2)[up]
                    qn = np.stack([gn[:, a_], gn[:, b_], gn[:, b_], gn[:, a_], gn[:, b_], gn[:, a_]], 2)[up]
                    under.append(np.concatenate([q, qn, np.full(q.shape[:2] + (1,), float(kind))], -1)
                                 .reshape(-1, 7))
        for o, opts, which, close in ovs:
            OF = np.asarray(o.faces, np.int64).reshape(-1, 3)
            own = place(np.asarray(o.positions, np.float64).reshape(-1, 3), deg, T, top)[0]
            OV = np.where(close[None, :, None], V[:, which], own)
            if opts["water"]:                                     # the rivers' water: its own pass
                uv = np.asarray(o.uvs if o.uvs else [0.0] * (2 * len(which)), np.float64).reshape(-1, 2)
                UV = np.broadcast_to(uv, (len(T),) + uv.shape)
                tri = np.concatenate([OV[:, OF].reshape(len(T), -1, 3), UV[:, OF].reshape(len(T), -1, 2),
                                      np.full((len(T), OF.size, 1), float(kind))], -1)
                water.append(tri.reshape(-1, 6))
                continue
            if opts["lava"] or not o.texture:
                continue                                          # the lava's flow: not yet
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
            "over": {k: np.concatenate(v).astype(np.float32) for k, v in over.items()},
            "water": np.concatenate(water).astype(np.float32) if water else np.zeros((0, 6), np.float32),
            "lift": lift}


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
