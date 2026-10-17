"""The campaign map's roads and region borders for the 3D map (glmap), drawn as the engines draw them (facts from the
engine source's aerial_map_roads, aerial_map_region_border_manager, aerial_map_interface and world_map; editor-notes
strat_map_render.md section 5; no code copied).

ROADS
- A region's road level is its town's road building (descr_strat 'type hinterland_roads paved_roads': the level's
  place in its chain, 1 dirt, 2 stone, 3 highway - export_descr_buildings.txt); none: no road.
- Which tiles: the game finds them in code not in the source we have (the strategy map's region_link_path between
  neighbouring regions' towns, a path through a third region refused, rivers crossed only at fords). Here: the
  cheapest 4-connected path from town to town of every two neighbouring land regions over those two regions' tiles
  (each step 1, more uphill, never the sea, high mountains or a river but at a ford); each tile in its own region's
  level - a step between two tiles in the higher of the two, none where both regions have none.
- Shape (the engine's): a point in each tile's middle moved by its own dice (a straight tile up to 0.35 each way, a
  bend 0.25 toward the bend's inside and up to 0.15; ends, forks and river tiles not moved), its way along the road
  turned up to 15 degrees; one Bezier curve a step (control points a third along each end's way), 5 pieces; a ribbon
  0.2 tiles wide, its texture across it, repeating every piece; faded out on a river tile; where 3 or 4 ways meet
  the fork's own square (road_*_T / road_*_X, 0.2 wide) - textures terrain/aerial_map/roads/road_<dirt|stone|
  highway>[_T|_X].tga.

BORDERS
- Each land region's outline, inward of its edge: a strip 0.2 tiles wide where the owners differ, 0.05 between two
  regions of one owner (none along a river there); none along the coast, the map's edge or high mountains; 0.7
  opaque. The line through the tile corners, each corner moved by its own dice (both ways alike, up to 0.125) and
  its way turned up to 30 degrees, one Bezier a tile edge (4 pieces), the corners rounded a quarter in; a corner of
  3 regions or more keeps its edges straight. The region's owner's primary and secondary colours (descr_sm_factions)
  on indicators/region_borders_primary.tga / _secondary.tga, unlit.

The game's dice per tile are its own; ours are stable (tilemodels._hash), so the lines run as in the game but do not
wiggle the same. Our world: x east, y up, z SOUTH from the map's top (tiles)."""

import heapq
import math
import re

import numpy as np

from . import tilemodels as TM
from .textio import strip_comment

ROAD_NAMES = {1: "dirt", 2: "stone", 3: "highway"}
HALF = 0.1                      # a road's half width
PIECES = 5                      # a road step's pieces
DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))          # north, east, south, west (z up)


def region_grid(mod, campaign):
    """((H, W) int32 region number of each tile, rows bottom first (z up) - -1 for the sea / no region; [region
    names]) of map_regions.tga; a town's (black) or port's (white) pixel counts as its region."""
    img = mod.region_map(campaign)
    w, h = img.width, img.height
    rgb = np.frombuffer(bytes(img.raw), np.uint8).reshape(h, w, 3).astype(np.int32)
    code = (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    regions = mod.regions(campaign)
    names = sorted(regions)
    out = np.full((h, w), -1, np.int32)
    for i, n in enumerate(names):
        r, g, b = regions[n]["colour"]
        out[code == ((r << 16) | (g << 8) | b)] = i
    try:
        from .mapedit import ports
        spots = list(mod.city_tiles(campaign).items()) + list(ports(mod, campaign).items())
    except Exception:
        spots = []
    for n, (x, y) in spots:
        if n in regions and 0 <= x < w and 0 <= y < h:
            out[y, x] = names.index(n)
    return out, names


def road_chains(mod):
    """{building: [levels]} of the road buildings (a name with 'road' in it) in export_descr_buildings.txt."""
    p = mod.file("edb") if hasattr(mod, "file") else None
    try:
        lines = mod.load(p).texts() if p else []
    except (OSError, ValueError):
        lines = []
    out, cur = {}, None
    for line in lines:
        t = strip_comment(line).split()
        if t[:1] == ["building"] and len(t) > 1:
            cur = t[1] if "road" in t[1].lower() else None
        elif cur and t[:1] == ["levels"] and cur not in out:
            out[cur] = t[1:]
    return out


def road_levels(strat, chains):
    """{region: 1..3} - the road level each town has built (descr_strat's 'type <road building> <level>')."""
    out = {}
    for fb in strat.factions:
        for st in fb.settlements:
            for i in range(st.start, st.end):
                t = strip_comment(strat.lines[i]).split()
                if t[:1] == ["type"] and len(t) > 2 and t[1] in chains and t[2] in chains[t[1]]:
                    out[st.region] = max(out.get(st.region, 0), min(3, chains[t[1]].index(t[2]) + 1))
    return out


def _path(a, b, allowed, cost, h):
    """The cheapest 4-connected path of tiles (x, z) from a to b over the allowed tiles (rows of bools, z up; h
    the tiles' heights alike), or None."""
    H, W = len(allowed), len(allowed[0])
    best, came, todo = {a: 0.0}, {}, [(0.0, a)]
    while todo:
        d, p = heapq.heappop(todo)
        if p == b:
            out = [p]
            while p in came:
                p = came[p]
                out.append(p)
            return out[::-1]
        if d > best.get(p, 1e18):
            continue
        for dx, dz in DIRS:
            q = (p[0] + dx, p[1] + dz)
            if not (0 <= q[0] < W and 0 <= q[1] < H) or not allowed[q[1]][q[0]]:
                continue
            nd = d + 1.0 + cost * abs(h[q[1]][q[0]] - h[p[1]][p[0]])
            if nd < best.get(q, 1e18):
                best[q], came[q] = nd, p
                heapq.heappush(todo, (nd, q))
    return None


def roads(grid, names, towns, levels, heights, features=None, blocked=None):
    """{(tile a, tile b): level} - every road step (tiles (x, z up), a < b) with its level."""
    H, W = grid.shape
    h = heights[::-1][1::2, 1::2][:H, :W].astype(np.float64)
    land = (h > 0) & (grid >= 0)
    if blocked is not None:
        land &= ~blocked
    if features is not None and features.shape[:2] == (H, W):
        f = features[::-1].astype(np.int32)
        code = (f[..., 0] << 16) | (f[..., 1] << 8) | f[..., 2]
        land &= ~np.isin(code, (0x0000ff, 0xffffff)) | (code == 0x00ffff)     # a river tile only at its ford
    idx = {n: i for i, n in enumerate(names)}
    pairs = set()
    a, b = grid[:, :-1], grid[:, 1:]
    for p, q in ((a, b), (grid[:-1], grid[1:])):
        sel = (p != q) & (p >= 0) & (q >= 0)
        pairs |= {(min(int(u), int(v)), max(int(u), int(v))) for u, v in zip(p[sel], q[sel])}
    lev = np.zeros(len(names) + 1, np.int32)
    for n, v in levels.items():
        if n in idx:
            lev[idx[n]] = v
    out = {}
    rise = 20.0 / max(1.0, float(np.percentile(h[land], 95)) if land.any() else 1.0)    # the highest climb: 20 steps
    hl = h.tolist()
    for r1, r2 in sorted(pairs):
        if not (lev[r1] or lev[r2]):
            continue
        t1, t2 = towns.get(names[r1]), towns.get(names[r2])
        if t1 is None or t2 is None:
            continue
        allowed = land & ((grid == r1) | (grid == r2))
        allowed[t1[1], t1[0]] = allowed[t2[1], t2[0]] = True
        path = _path(tuple(t1), tuple(t2), allowed.tolist(), rise, hl)
        if not path:
            continue
        for p, q in zip(path, path[1:]):
            level = max(lev[grid[p[1], p[0]]], lev[grid[q[1], q[0]]])
            if level:
                key = (min(p, q), max(p, q))
                out[key] = max(out.get(key, 0), int(level))
    return out


def _ground(heights, yscale, X, Zc):
    """The ground's height (world units) at world x and z up (tiles, continuous); never under the sea's level."""
    H = (heights.shape[0] - 1) // 2
    return np.maximum(TM._ground_h(heights, 2 * (H - np.asarray(Zc)), 2 * np.asarray(X)) * yscale, 0.0)


def _rnd(x, z, salt):
    return TM._hash(int(x), int(z), salt) / 4294967296.0


def road_geometry(steps, heights, yscale, rivers=None):
    """{texture rel: (n, 6) float32 x y z u v alpha} - the roads' ribbons and fork squares, triangles as vertex
    triples; rivers (H, W) bool z up: their tiles fade the road out."""
    H = (heights.shape[0] - 1) // 2
    links = {}
    for (p, q), level in steps.items():
        links.setdefault(p, {})[q] = level
        links.setdefault(q, {})[p] = level
    out = {}

    def add(tex, tris):
        out.setdefault(tex, []).append(tris)

    def river(t):
        return rivers is not None and 0 <= t[1] < rivers.shape[0] and 0 <= t[0] < rivers.shape[1] and \
            bool(rivers[t[1], t[0]])

    def node(t):
        """A road tile's point (x, z up) and whether it is a plain one (moved by its dice)."""
        nb = list(links[t])
        cx, cz = t[0] + 0.5, t[1] + 0.5
        if len(nb) != 2 or river(t):
            return cx, cz
        d1 = (nb[0][0] - t[0], nb[0][1] - t[1])
        d2 = (nb[1][0] - t[0], nb[1][1] - t[1])
        if d1[0] + d2[0] == 0 and d1[1] + d2[1] == 0:                       # straight
            return cx + 0.35 * (_rnd(*t, 11) - 0.5), cz + 0.35 * (_rnd(*t, 12) - 0.5)
        return (cx + 0.25 * (d1[0] + d2[0]) + 0.15 * (_rnd(*t, 11) - 0.5),
                cz + 0.25 * (d1[1] + d2[1]) + 0.15 * (_rnd(*t, 12) - 0.5))

    P = {t: node(t) for t in links}

    def way(t, toward):
        """The road's way at tile t's point on the step toward a neighbour."""
        nb = list(links[t])
        if len(nb) == 2 and not river(t):
            o = nb[0] if nb[1] == toward else nb[1]
            vx, vz = P[toward][0] - P[o][0], P[toward][1] - P[o][1]
            a = math.radians(30.0 * (_rnd(*t, 13) - 0.5))
            vx, vz = vx * math.cos(a) - vz * math.sin(a), vx * math.sin(a) + vz * math.cos(a)
        else:
            vx, vz = toward[0] - t[0], toward[1] - t[1]
        n = math.hypot(vx, vz) or 1.0
        return vx / n, vz / n
    tt = np.linspace(0.0, 1.0, PIECES + 1)
    for (p, q), level in steps.items():
        tex = "terrain/aerial_map/roads/road_%s.tga" % ROAD_NAMES[level]
        a, b = np.array(P[p]), np.array(P[q])
        ta, tb = np.array(way(p, q)), np.array(way(q, p))
        c1, c2 = a + 0.33 * ta, b + 0.33 * tb
        s = tt[:, None]
        pts = ((1 - s) ** 3) * a + 3 * ((1 - s) ** 2) * s * c1 + 3 * (1 - s) * s * s * c2 + s ** 3 * b
        tan = np.gradient(pts, axis=0)
        tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-9)
        nrm = np.stack([-tan[:, 1], tan[:, 0]], 1)
        al = (0.0 if river(p) else 1.0) * (1 - tt) + (0.0 if river(q) else 1.0) * tt
        L, R = pts + nrm * HALF, pts - nrm * HALF
        u = np.arange(PIECES + 1, dtype=np.float64)

        def vert(e, v):
            return np.stack([e[:, 0], _ground(heights, yscale, e[:, 0], e[:, 1]), H - e[:, 1], u,
                             np.full(len(u), v), al], 1)
        vl, vr = vert(L, 0.0), vert(R, 1.0)
        quads = np.stack([vl[:-1], vr[:-1], vr[1:], vl[:-1], vr[1:], vl[1:]], 1).reshape(-1, 6)
        add(tex, quads)
    for t, nb in links.items():                                           # forks: the T / X squares
        if len(nb) < 3:
            continue
        level = max(nb.values())
        have = {(q[0] - t[0], q[1] - t[1]) for q in nb}
        if len(nb) >= 4:
            kind, deg = "X", 0
        else:
            kind = "T"
            deg = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[next(d for d in DIRS if d not in have)]
        cx, cz = P[t]
        corners = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], np.float64) * HALF
        uv = np.array([[0, 1], [1, 1], [1, 0], [0, 0]], np.float64)
        for _ in range(deg // 90):
            uv = np.roll(uv, 1, axis=0)
        xs, zs = cx + corners[:, 0], cz + corners[:, 1]
        v = np.stack([xs, _ground(heights, yscale, xs, zs), H - zs, uv[:, 0], uv[:, 1], np.ones(4)], 1)
        add("terrain/aerial_map/roads/road_%s_%s.tga" % (ROAD_NAMES[level], kind), v[[0, 1, 2, 0, 2, 3]])
    return {k: np.concatenate(v).astype(np.float32) for k, v in out.items()}


def faction_colours(mod):
    """{faction: (primary (r, g, b), secondary (r, g, b))} of descr_sm_factions.txt."""
    out, cur = {}, None
    try:
        lines = mod.load(mod.file("sm_factions")).texts()
    except Exception:
        lines = []
    for line in lines:
        t = strip_comment(line).split()
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1].rstrip(",")
            out[cur] = [(200, 200, 200), (60, 60, 60)]
        elif cur and t[:1] in (["primary_colour"], ["secondary_colour"]):
            m = re.search(r"red\s*(\d+)\s*,\s*green\s*(\d+)\s*,\s*blue\s*(\d+)", line)
            if m:
                out[cur][0 if t[0] == "primary_colour" else 1] = tuple(int(v) for v in m.groups())
    return {k: tuple(v) for k, v in out.items()}


def _hash_np(x, z, salt):
    """tilemodels._hash on arrays (the same numbers)."""
    x, z = np.asarray(x, np.uint64), np.asarray(z, np.uint64)
    with np.errstate(over="ignore"):                  # the low 32 bits are the same as Python's big numbers
        h = (x * np.uint64(73856093)) ^ (z * np.uint64(19349663)) ^ np.uint64((salt * 83492791) ^ 0x5bd1e995)
        h = ((h ^ (h >> np.uint64(13))) * np.uint64(0x5bd1e995)) & np.uint64(0xffffffff)
    return (h ^ (h >> np.uint64(15))) & np.uint64(0xffffffff)


def _loops(grid):
    """{region: [loop]} - every region's outline loops, each [(corner x, corner z)] walked with its tiles on the
    left (z up); where two of its tiles touch only at a corner the walk turns left first (they stay apart)."""
    H, W = grid.shape
    pad = np.pad(grid, 1, constant_values=-1)
    me = pad[1:-1, 1:-1]
    out_of = {}
    for (dz, dx), (ox, oz), d in (((-1, 0), (0, 0), (1, 0)), ((0, 1), (1, 0), (0, 1)),
                                  ((1, 0), (1, 1), (-1, 0)), ((0, -1), (0, 1), (0, -1))):
        nb = pad[1 + dz:1 + dz + H, 1 + dx:1 + dx + W]
        zs, xs = np.nonzero((me >= 0) & (nb != me))
        for r, x, z in zip(me[zs, xs].tolist(), xs.tolist(), zs.tolist()):
            out_of.setdefault((r, x + ox, z + oz), []).append(d)
    loops = {}
    while out_of:
        key = next(iter(out_of))
        r, start = key[0], key[1:]
        c, d, loop = start, out_of[key][0], []
        while True:
            ways = out_of.get((r,) + c)
            if not ways:
                break
            if loop:                                       # left, straight, right
                d = next((w for w in ((-d[1], d[0]), d, (d[1], -d[0])) if w in ways), ways[0])
            ways.remove(d)
            if not ways:
                del out_of[(r,) + c]
            loop.append(c)
            c = (c[0] + d[0], c[1] + d[1])
        if len(loop) >= 4:
            loops.setdefault(r, []).append(loop)
    return loops


def border_geometry(grid, names, owners, creators, colours, heights, yscale, mountains=None, rivers=None,
                    skip=()):
    """(n, 12) float32 x y z u v alpha, primary r g b, secondary r g b (0..1) - every land region's border strip,
    triangles as vertex triples."""
    H, W = grid.shape
    Hm = (heights.shape[0] - 1) // 2
    pad = np.pad(grid, 1, constant_values=-1)
    flags = np.zeros((H + 2, W + 2), bool)
    for a in (mountains,):
        if a is not None and a.shape == grid.shape:
            flags[1:-1, 1:-1] |= a
    riv = np.zeros((H + 2, W + 2), bool)
    if rivers is not None and rivers.shape == grid.shape:
        riv[1:-1, 1:-1] = rivers
    own_names = [owners.get(n) or creators.get(n) for n in names]
    oid = {o: i for i, o in enumerate(sorted({o for o in own_names if o}))}
    own = np.array([oid.get(o, -1) for o in own_names] + [-2], np.int64)      # [-1] (no region): -2
    # each corner's dice and whether 3 regions or more meet there
    cz, cx = np.mgrid[0:H + 1, 0:W + 1]
    jit = 0.25 * (_hash_np(cx, cz, 21).astype(np.float64) / 4294967296.0 - 0.5)
    ang = np.radians(60.0 * (_hash_np(cx, cz, 22).astype(np.float64) / 4294967296.0 - 0.5))
    q4 = np.stack([pad[:-1, :-1], pad[:-1, 1:], pad[1:, :-1], pad[1:, 1:]], -1)
    q4s = np.sort(q4, -1)
    junction = (1 + (q4s[..., 1:] != q4s[..., :-1]).sum(-1)) >= 3
    tris = []
    for r, loops in _loops(grid).items():
        if names[r] in skip:
            continue
        pri, sec = colours.get(own_names[r], ((200, 200, 200), (60, 60, 60)))
        col = np.array(list(pri) + list(sec), np.float64) / 255.0
        for loop in loops:
            C = np.asarray(loop, np.int64)
            D = np.roll(C, -1, axis=0) - C
            # the tiles inside (left) and outside each edge, in pad's frame
            ix = C[:, 0] + (D[:, 0] - D[:, 1] - 1) // 2 + 1
            iz = C[:, 1] + (D[:, 1] + D[:, 0] - 1) // 2 + 1
            ox, oz = ix + D[:, 1], iz - D[:, 0]
            o = pad[oz, ox]
            same = (own[o] == own[r]) & (own[r] >= 0)
            alpha = np.where((o < 0) | flags[iz, ix] | flags[oz, ox] | (same & (riv[iz, ix] | riv[oz, ox])),
                             0.0, 0.7)
            if not alpha.any():
                continue
            wide = np.where(alpha > 0, np.where(same, 0.25, 1.0), 0.0)    # an unseen edge widens nothing
            jn = junction[C[:, 1], C[:, 0]]
            Pt = C + jit[C[:, 1], C[:, 0]][:, None]
            din = np.roll(D, 1, axis=0)
            delta = np.where(jn[:, None], 0.0, 0.25 * (D - din))
            f = (din + D).astype(np.float64)
            f /= np.maximum(np.linalg.norm(f, axis=1, keepdims=True), 1e-9)
            a_ = ang[C[:, 1], C[:, 0]][:, None]
            face = np.concatenate([f[:, :1] * np.cos(a_) - f[:, 1:] * np.sin(a_),
                                   f[:, :1] * np.sin(a_) + f[:, 1:] * np.cos(a_)], 1)
            a0 = Pt + delta
            a3 = np.roll(a0, -1, axis=0)
            fs = np.where(jn[:, None], D, face)
            fe = np.where(np.roll(jn, -1)[:, None], D, np.roll(face, -1, axis=0))
            a1, a2 = a0 + 0.33 * fs, a3 - 0.33 * fe
            t = np.array([0.0, 0.25, 0.5, 0.75])[None, :, None]
            pts = (((1 - t) ** 3) * a0[:, None] + 3 * ((1 - t) ** 2) * t * a1[:, None] +
                   3 * (1 - t) * t * t * a2[:, None] + t ** 3 * a3[:, None]).reshape(-1, 2)
            wid = np.repeat(wide, 4)
            alp = np.repeat(alpha, 4)
            wid[0::4] = np.maximum(wide, np.roll(wide, 1))
            alp[0::4] = 0.5 * (alpha + np.roll(alpha, 1))
            tan = np.roll(pts, -1, axis=0) - np.roll(pts, 1, axis=0)
            tan /= np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-9)
            nrm = np.stack([-tan[:, 1], tan[:, 0]], 1)                  # to the left: into the region
            inner = pts + nrm * (0.2 * wid)[:, None]
            u = np.arange(len(pts)) / 4.0

            def vert(e, v):
                return np.stack([e[:, 0], _ground(heights, yscale, e[:, 0], e[:, 1]), Hm - e[:, 1], u,
                                 np.full(len(u), v), alp], 1)
            a, b = vert(pts, 0.0), vert(inner, 1.0)
            a2_, b2_ = np.roll(a, -1, axis=0), np.roll(b, -1, axis=0)
            a2_[:, 3], b2_[:, 3] = a[:, 3] + 0.25, b[:, 3] + 0.25
            keep = (alp > 0) | (np.roll(alp, -1) > 0)
            q = np.stack([a, b, b2_, a, b2_, a2_], 1)[keep].reshape(-1, 6)
            tris.append(np.c_[q, np.repeat(col[None], len(q), 0)])
    return np.concatenate(tris).astype(np.float32) if tris else np.zeros((0, 12), np.float32)


__all__ = ["region_grid", "road_chains", "road_levels", "roads", "road_geometry", "faction_colours",
           "border_geometry", "ROAD_NAMES"]
