"""Make a campaign map bigger: every tile becomes a 3 x 3 block (alpha). Both games.

Why 3: an odd factor keeps each town, port, army and resource in the MIDDLE of its block - tile (x, y) becomes
(3x + 1, 3y + 1) - so nothing has to be placed again by hand. The room in between is for new regions and factions.

What it writes (Preview lists it; one backup, Restore gives everything back):
- world/maps/base pictures (colours stay exact - no new colours are made, except the heights' blended values):
    W x H         map_regions with a WINDING coast and winding region borders (a new point is land when most of
                  the old land round a place bent by _warp - two golden-ratio waves - is: bays and capes, not 3 x 3
                  squares nor 45-degree cuts; a region keeps its pieces; every block's middle keeps its old value, so towns,
                  armies and resources stay on their kind of ground). The rules both games' own maps keep (measured
                  on vanilla Rome and Medieval II, 2026-10-02): a town pixel in its block's middle with its own
                  region (or sea) all round it; a port on a coastal LAND tile (its heights' point is land) touching
                  the sea and its region's land; any colour descr_regions does not list but the heights hold above
                  the sea counts as land (land_colours),
                  map_features (rivers redrawn as 1-pixel lines through the middles - a 2-pixel river crashes the
                  game -, a corner link as a staircase, a river mouth carried on to the new coast; cliffs and land
                  bridges as unbroken lines too, a bridge's end on the water carried on to the land; fords, sources
                  and volcanoes on the middle pixel), map_trade_routes
    2W+1 x 2H+1   map_heights the NATURAL way (blended, land and sea apart, bent by _warp as the ground, fractal
                  crags on mountains, river valleys, no slope steeper than the old map's steepest) with ONE coast: each tile's middle point sea
                  exactly when the new map_regions has sea there (heights_from_tiles), and map_heights.hgt beside it
                  at the new size (the game reads it instead of the picture and never makes it again);
                  map_ground_types and map_climates BY TILES (kinds_scaled: every new tile the kind of the old tile
                  it lies in, winding edges between kinds, the sea ground under the heights' sea), map_fog
    2W x 2H       map_roughness (smooth)
  and the campaign's disasters.tga, radar_map1 / radar_map2 (when present);
- descr_terrain.txt: the dimensions (width / height x 3) and - by default - the heights x 3 (max_land_height,
  min_sea_height): the land is 3 x wider, so its hills and mountains must be 3 x higher to keep their slopes;
- descr_strat.txt: every character's x / y, every resource, fort, watchtower and wonder (Rome's landmarks);
- descr_events.txt: every 'position x, y';
- the campaign's scripts (campaign_script.txt and the file descr_strat names after 'script'): every command and
  condition the engines take campaign-map tiles in (SCRIPT_TILES: spawned characters, camera, reveal, move /
  reposition, forts and resources by console_command, 'near a tile' distances, 'in a rectangle' sizes); battle
  positions in the same scripts are left alone; the trait / ancillary triggers too when the mod has this one campaign;
- map.rwm removed (the game builds it again).
Warned, not moved: script lines with 'x, y'-like numbers outside the known commands, and Lua / Squirrel scripts.
The faction-select pictures (map_<faction>.tga, map_FE) and water_surface keep their size."""

import os
import re
import struct

from .tga import _decode

FACTOR = 3
CITY, PORT = (0, 0, 0), (255, 255, 255)
RIVERY = {(0, 0, 255), (0, 255, 255), (255, 255, 255)}      # river, ford, source: one line
CLIFF = (255, 255, 0)
BRIDGE = (0, 255, 0)                                          # Medieval II's land bridge: a chain over the water
BASE_PICTURES = {                       # name: how its size follows the map's W x H
    "map_regions.tga": "tiles", "map_features.tga": "tiles", "map_trade_routes.tga": "tiles",
    "map_heights.tga": "corners", "map_ground_types.tga": "corners", "map_climates.tga": "corners",
    "map_fog.tga": "corners", "map_roughness.tga": "double",
}
CAMPAIGN_PICTURES = {"disasters.tga": "tiles", "radar_map1.tga": "tiles", "radar_map2.tga": "double",
                     "map_radar2.tga": "double"}


def new_xy(x, y):
    return FACTOR * x + FACTOR // 2, FACTOR * y + FACTOR // 2


def _index(kind, n_old):
    """For each new row / column: the old one it copies."""
    if kind == "corners":                       # 2W+1 points -> 6W+1 points
        n_new = FACTOR * (n_old - 1) + 1
        return [int(j / FACTOR + 0.5) for j in range(n_new)]
    return [j // FACTOR for j in range(n_old * FACTOR)]


def _read(path):
    with open(path, "rb") as fh:
        data = fh.read()
    w, h, step, top_down, _, raw = _decode(data, path)
    return data, w, h, step, top_down, raw


def _write(data, w, h, step, raw):
    id_len = data[0]
    head = bytearray(data[:18 + id_len])
    head[2] = 2                                 # uncompressed: the game reads it the same way
    struct.pack_into("<HH", head, 12, w, h)
    return bytes(head) + bytes(raw)


def scaled(path, kind):
    """The picture's bytes made bigger, every pixel copied (no blending)."""
    data, w, h, step, top_down, raw = _read(path)
    xs, ys = _index(kind, w), _index(kind, h)
    row = w * step
    out = bytearray()
    cache = {}
    for oy in ys:
        line = cache.get(oy)
        if line is None:
            src = raw[oy * row:(oy + 1) * row]
            px = [bytes(src[i * step:(i + 1) * step]) for i in range(w)]
            line = cache[oy] = b"".join(px[i] for i in xs)
            if len(cache) > 4:
                cache.pop(next(iter(cache)))
        out += line
    return _write(data, len(xs), len(ys), step, out), (w, h)


def _weights(kind, n_old):
    """For each new row / column: (old a, old b, weight of b) - where it falls between two old points."""
    out = []
    if kind == "corners":
        n_new = FACTOR * (n_old - 1) + 1
        pos = [j / FACTOR for j in range(n_new)]
    else:                                        # pixel middles line up: (j + 0.5) / 3 - 0.5
        pos = [(j + 0.5) / FACTOR - 0.5 for j in range(n_old * FACTOR)]
    for p in pos:
        p = min(max(p, 0.0), n_old - 1.0)
        a = int(p)
        b = min(a + 1, n_old - 1)
        out.append((a, b, p - a))
    return out


def _sources(kind, w, h, natural=False):
    """For each new point (X, Y) - bottom-up, like the game's tiles -: the 4 old points round it with their
    weights. A block's middle (tiles) or an old corner point (corners) has its old point at weight 1, so it keeps
    its old value exactly: towns, armies, resources and the rest never change their kind of ground. natural (tiles
    only): every other pixel looks from a place bent by _warp, so a coast or a border made from these weights winds
    like a real one instead of running in steps and straight 45-degree cuts (the heights bend in _bent_corners)."""
    xs, ys = _weights(kind, w), _weights(kind, h)
    bend = natural and kind == "tiles"
    mid = FACTOR // 2
    for Y, (ya, yb, fy) in enumerate(ys):
        for X, (xa, xb, fx) in enumerate(xs):
            if bend and not (X % FACTOR == mid and Y % FACTOR == mid):
                wx, wy = _warp(X, Y)
                px = min(max((X + 0.5 + wx) / FACTOR - 0.5, 0.0), w - 1.0)
                py = min(max((Y + 0.5 + wy) / FACTOR - 0.5, 0.0), h - 1.0)
                xa, ya = int(px), int(py)
                xb, yb = min(xa + 1, w - 1), min(ya + 1, h - 1)
                fx, fy = px - xa, py - ya
                yield X, Y, ((xa, ya, (1 - fx) * (1 - fy)), (xb, ya, fx * (1 - fy)),
                             (xa, yb, (1 - fx) * fy), (xb, yb, fx * fy))
                xa, xb, fx = xs[X]
                ya, yb, fy = ys[Y]
                continue
            yield X, Y, ((xa, ya, (1 - fx) * (1 - fy)), (xb, ya, fx * (1 - fy)),
                         (xa, yb, (1 - fx) * fy), (xb, yb, fx * fy))


class Mask:
    """A yes / no picture, one byte a point, read and set by (X, Y) like a dict - a 1500 x 1500-tile map has
    9 million height points, too many for a dict."""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.b = bytearray(W * H)

    def __getitem__(self, xy):
        return bool(self.b[xy[1] * self.W + xy[0]])

    def __setitem__(self, xy, v):
        self.b[xy[1] * self.W + xy[0]] = 1 if v else 0

    def get(self, xy, default=None):
        x, y = xy
        if 0 <= x < self.W and 0 <= y < self.H:
            return bool(self.b[y * self.W + x])
        return default


def _share_mask(kind, w, h, flag, natural=False):
    """A yes / no picture made bigger SMOOTHLY: a new point is yes when more than half of the 4 old points round it
    (by weight) are (a tie: its nearest old point decides). Blocks become rounded shapes - a coast drawn in
    3 x 3 squares becomes a smooth line - while every old middle keeps its value. -> Mask, W, H."""
    W, H = len(_weights(kind, w)), len(_weights(kind, h))
    out = Mask(W, H)
    flags = {}
    for X, Y, pts in _sources(kind, w, h, natural):
        share = 0.0
        for x, y, wt in pts:
            f = flags.get((x, y))
            if f is None:
                f = flags[(x, y)] = bool(flag(x, y))
            if f:
                share += wt
        if abs(share - 0.5) < 1e-9:
            x, y, _ = max(pts, key=lambda p: p[2])
            yes = flags[(x, y)]
        else:
            yes = share > 0.5
        if yes:
            out.b[Y * W + X] = 1
    return out, W, H


def _pick(pts, want, kind_of):
    """The old point of the wanted kind with the most weight among the 4 (None when none is)."""
    best = None
    for x, y, wt in pts:
        if kind_of(x, y) == want and (best is None or wt > best[2]):
            best = (x, y, wt)
    return best


def _heights_sea(at):
    def sea(x, y):
        r, g, b = at(x, y)
        return r == 0 and g == 0 and b > 0
    return sea


def heights_mask(path):
    """map_heights' sea made bigger smoothly (its own coast, which the sea ground types follow): {(X, Y): sea}."""
    data, w, h, step, top_down, at = _pixels(path)
    return _share_mask("corners", w, h, _heights_sea(at))[0]


def _nearest_kind(pts, want, kind_of, w, h, reach=4):
    """The old point of the wanted kind nearest the new point's 4 (pts) within `reach`, or None: the coast was
    set by the tiles, so a new land point may have only sea points round it (its height comes from the nearest
    land point, not from a sea depth read as a grey)."""
    x0, y0, _ = max(pts, key=lambda p: p[2])
    for r in range(1, reach + 1):
        best = None
        for x in range(max(0, x0 - r), min(w, x0 + r + 1)):
            for y in range(max(0, y0 - r), min(h, y0 + r + 1)):
                if max(abs(x - x0), abs(y - y0)) == r and kind_of(x, y) == want:
                    d = (x - x0) ** 2 + (y - y0) ** 2
                    if best is None or d < best[0]:
                        best = (d, x, y)
        if best:
            return best[1], best[2]
    return None


def _bent_corners(w, h, still):
    """_sources for the heights' points bent by _warp EVERYWHERE (an old point too: pinned in place while its
    neighbours move, it stood as a step - slopes twice the old map's steepest); the bend fades out round a town
    (still: {point: 0 .. 1}), so a town keeps its ground."""
    W, H = len(_weights("corners", w)), len(_weights("corners", h))
    for Y in range(H):
        for X in range(W):
            f = still.get((X, Y), 1.0)
            wx, wy = _warp((X - 1) / 2, (Y - 1) / 2) if f else (0.0, 0.0)
            px = min(max((X + 2 * wx * f) / FACTOR, 0.0), w - 1.0)
            py = min(max((Y + 2 * wy * f) / FACTOR, 0.0), h - 1.0)
            xa, ya = int(px), int(py)
            xb, yb = min(xa + 1, w - 1), min(ya + 1, h - 1)
            fx, fy = px - xa, py - ya
            yield X, Y, ((xa, ya, (1 - fx) * (1 - fy)), (xb, ya, fx * (1 - fy)),
                         (xa, yb, (1 - fx) * fy), (xb, yb, fx * fy))


STILL = 6                                                 # points round a town where the bend fades out


def _heights_field(w, h, value, is_sea, mask, natural=False, towns=()):
    """The heights at the new size (corners), land and sea blended apart by mask (True = sea): only old points of
    the new point's kind are blended; none round it - the nearest one's value. natural: bent as the ground is
    (_bent_corners, still round the towns). -> (values, relief, W, H): relief = how much the old points of that
    kind round each new point differ (a mountain's slope; 0 on a plain or the sea)."""
    W, H = len(_weights("corners", w)), len(_weights("corners", h))
    if natural:
        still = {p: d / STILL for p, d in _rings(_tile_points(towns), W, H, STILL).items()}
        out, relief = _blend_heights(_bent_corners(w, h, still), w, h, W, H, value, is_sea, mask)
        out.plain = _blend_heights(_sources("corners", w, h), w, h, W, H, value, is_sea, mask)[0]
    else:
        out, relief = _blend_heights(_sources("corners", w, h), w, h, W, H, value, is_sea, mask)
    return out, relief, W, H


class _Heights(list):
    """The new heights (a list), with .plain: the same not bent (natural only) - what _nature falls back to."""
    plain = None


def _blend_heights(source, w, h, W, H, value, is_sea, mask):
    out, relief = _Heights([0.0] * (W * H)), [0.0] * (W * H)
    for X, Y, pts in source:
        want = mask[(X, Y)]
        tot = val = 0.0
        lo = hi = None
        for x, y, wt in pts:
            if is_sea(x, y) == want:
                v = value(x, y)
                tot += wt
                val += v * wt
                lo = v if lo is None or v < lo else lo
                hi = v if hi is None or v > hi else hi
        if not tot:                                  # no old point of that kind round it: the nearest one's value
            got = _nearest_kind(pts, want, is_sea, w, h)
            val, tot = (value(*got) if got else None), 1.0
        i = Y * W + X
        out[i] = val / tot if val is not None else None
        if lo is not None and not want:
            relief[i] = hi - lo
    return out, relief


ROUGH, CARVE = 0.45, 0.35       # mountains' fine relief (a share of the slope); a river's valley (a share of the height)


def _noise(W, H):
    """Fine relief the way mountains have it - big hills carrying smaller ones carrying smaller ones (fractal, three
    sizes: 24, 12 and 6 points - 4, 2 and 1 tiles): -1 .. 1 a point, the same map always alike. None without Pillow (only a run from the
    source may lack it - the exe has it): then the heights stay smooth."""
    try:
        from PIL import Image
    except ImportError:
        return None
    import random
    rnd = random.Random(1618)
    total = [0.0] * (W * H)
    for size, part in ((24, 0.45), (12, 0.35), (6, 0.2)):
        sw, sh = W // size + 2, H // size + 2
        small = Image.frombytes("L", (sw, sh), bytes(rnd.randrange(256) for _ in range(sw * sh)))
        big = small.resize((sw * size, sh * size), Image.BICUBIC).crop((0, 0, W, H)).tobytes()
        for i, b in enumerate(big):
            total[i] += (b / 127.5 - 1.0) * part
    return total


def _rings(points, W, H, reach):
    """{point: steps to the nearest of points} for every point of the W x H grid within reach (8 ways)."""
    dist = {p: 0 for p in points if 0 <= p[0] < W and 0 <= p[1] < H}
    edge = list(dist)
    for d in range(1, reach + 1):
        nxt = []
        for x, y in edge:
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    q = (x + a, y + b)
                    if 0 <= q[0] < W and 0 <= q[1] < H and q not in dist:
                        dist[q] = d
                        nxt.append(q)
        edge = nxt
    return dist


def _tile_points(tiles):
    """The heights' points of new tiles (a tile = the 3 x 3 points round its middle 2X+1, 2Y+1)."""
    return {(2 * X + 1 + a, 2 * Y + 1 + b) for X, Y in tiles for a in (-1, 0, 1) for b in (-1, 0, 1)}


VALLEY = {0: 1.0, 1: 0.8, 2: 0.55, 3: 0.3, 4: 0.12}      # a river's valley: how deep, by points from the river
CALM = 4                                                  # points round a town where the land is left smooth


def _steepest(w, h, value, is_sea):
    """The steepest step between two neighbouring land points of the old heights (the file's own unit): no slope of
    the new map may be steeper than the old map's steepest (the game takes too steep a slope for impassable)."""
    top = 0.0
    for y in range(h):
        for x in range(w):
            if is_sea(x, y):
                continue
            v = value(x, y)
            for a, b in ((x + 1, y), (x, y + 1)):
                if a < w and b < h and not is_sea(a, b):
                    top = max(top, abs(value(a, b) - v))
    return top


def _nature(vals, relief, W, H, mask, floor, rivers=(), towns=(), vertical=1.0, steepest=None):
    """Land heights the way nature makes them (in place; vals in the file's own unit, floor = the lowest land):
    - fine relief on mountains: _noise times the old slope (ROUGH; half as much when the heights grow - vertical >
      1 -, which multiplies the small crags too) - rocky ranges, plains stay flat;
    - rivers carve their valleys: the land along a river (rivers: its new tiles) lowered by CARVE of its height
      above the floor, less further off (VALLEY) - deep in the mountains, hardly at all on a plain;
    - every old point keeps its height (the fine relief fades to nothing at it), round a town (towns: new tiles)
      the land is left smooth, the sea is never touched and no land drops to the sea;
    - no slope steeper than the old map's steepest (steepest: _steepest; a new point's step to its neighbour,
      times vertical - the heights' growth -, against the old step): where the bend (it squeezes a slope), the
      crags or a valley's side would be steeper, all three are made gentler there, step by step, down to the
      heights neither bent nor roughened (vals.plain)."""
    noise = _noise(W, H)
    plain = getattr(vals, "plain", None)               # the heights not bent: where a slope is too steep, back to it
    near_river = _rings(_tile_points(rivers), W, H, max(VALLEY)) if rivers else {}
    near_town = _rings(_tile_points(towns), W, H, CALM) if towns else {}
    rough = ROUGH if vertical <= 1 else ROUGH / 2
    extra = {}                                           # point: what nature adds to the smooth height
    for Y in range(H):
        for X in range(W):
            i = Y * W + X
            v = vals[i]
            if v is None or mask.b[i]:
                continue
            calm = min(near_town.get((X, Y), CALM), CALM) / CALM
            add = 0.0
            if noise is not None and relief[i]:
                dx, dy = min(X % FACTOR, -X % FACTOR), min(Y % FACTOR, -Y % FACTOR)
                fade = min(1.0, (dx * dx + dy * dy) ** 0.5)          # 0 on an old point
                add += rough * relief[i] * noise[i] * fade * calm
            d = near_river.get((X, Y))
            if d is not None:
                add -= CARVE * VALLEY[d] * max(v + add - floor, 0.0) * max(calm, 0.25)
            base = plain[i] if plain is not None and plain[i] is not None else v
            add = max(v + add, floor) - base                 # the bend, the crags and the valley together
            if add:
                extra[i] = add
    share = dict.fromkeys(extra, 1.0)

    def height(i):
        base = plain[i] if plain is not None and plain[i] is not None else vals[i]
        return base + extra.get(i, 0.0) * share.get(i, 0.0)
    if steepest:
        limit = steepest / max(vertical, 1e-9)
        for _ in range(12):
            steep = set()
            for i in extra:
                if not share[i]:
                    continue
                X, Y = i % W, i // W
                v = height(i)
                for a, b in ((X + 1, Y), (X - 1, Y), (X, Y + 1), (X, Y - 1)):
                    if 0 <= a < W and 0 <= b < H:
                        j = b * W + a
                        if vals[j] is not None and not mask.b[j] and abs(height(j) - v) > limit:
                            steep.add(i)
                            if j in share:
                                steep.add(j)
                            break
            if not steep:
                break
            for i in steep:
                share[i] = share[i] * 0.5 if share[i] > 0.1 else 0.0
    for i in extra:
        vals[i] = max(height(i), floor)
    if plain is not None:
        vals.plain = None


def smooth_scaled(path, kind, sea=False, mask=None, natural=False, rivers=(), towns=(), vertical=1.0):
    """A height-like picture made bigger SMOOTHLY (no steps): each new point blends the old ones round it. With
    sea=True (map_heights: land grey, its level; the sea blue, its depth) land and sea are blended apart: a point is
    sea or land by mask (heights_mask - a smooth coast), and only old points of that kind are blended."""
    data, w, h, step, top_down, at = _pixels(path)
    is_sea = _heights_sea(at) if sea else (lambda x, y: False)
    if sea and mask is None:
        mask = heights_mask(path)
    if sea and kind == "corners":                    # map_heights: land grey (its level), the sea blue (its depth)
        value = lambda x, y: float(at(x, y)[2] if is_sea(x, y) else at(x, y)[0])
        vals, relief, W, H = _heights_field(w, h, value, is_sea, mask, natural, towns)
        if natural:
            _nature(vals, relief, W, H, mask, 1.0, rivers, towns, vertical, _steepest(w, h, value, is_sea))
        raw = _blank(W, H, step, (0, 0, 0))
        for Y in range(H):
            for X in range(W):
                want = mask.b[Y * W + X]
                v = vals[Y * W + X]
                v = int(v + 0.5) if v is not None else (253 if want else 1)
                if want:
                    _put(raw, W, H, step, top_down, X, Y, (0, 0, min(max(v, 1), 255)))
                else:                                # land never black (0 0 0 may be read as sea)
                    v = min(max(v, 1), 255)
                    _put(raw, W, H, step, top_down, X, Y, (v, v, v))
        return _write(data, W, H, step, raw)
    W, H = len(_weights(kind, w)), len(_weights(kind, h))
    raw = _blank(W, H, step, (0, 0, 0))
    for X, Y, pts in _sources(kind, w, h):
        want = mask[(X, Y)] if sea else False
        tot = val = 0.0
        for x, y, wt in pts:
            if is_sea(x, y) == want:
                c = at(x, y)
                tot += wt
                val += (c[2] if want else c[0]) * wt
        if not tot:                                  # no old point of that kind round it: the nearest one's value
            got = _nearest_kind(pts, want, is_sea, w, h)
            if got:
                c = at(*got)
                val, tot = (c[2] if want else c[0]), 1.0
            else:                                    # none near: the lowest land / the usual sea
                val, tot = (253.0 if want else 1.0), 1.0
        v = int(val / tot + 0.5)
        if not want and sea:
            v = max(v, 1)                            # land never black (0 0 0 may be read as sea)
        if want:
            _put(raw, W, H, step, top_down, X, Y, (0, 0, max(v, 1)))
        else:
            _put(raw, W, H, step, top_down, X, Y, (v, v, v))
    return _write(data, W, H, step, raw)


def hgt_scaled(hgt_path, tga_path, mask, vertical=1.0, natural=False, rivers=(), towns=()):
    """map_heights.hgt (the game's own float copy of the heights, read INSTEAD of the picture and never made again)
    at the new size: the old floats blended like the picture (land and sea apart, by mask), times `vertical` (the
    heights grow with the land: descr_terrain's max_land_height / min_sea_height are multiplied the same way).
    Format: uint32 w, h, then w * h float32, bottom-up rows (vanilla RTW and M2TW measured)."""
    with open(hgt_path, "rb") as fh:
        raw = fh.read()
    w, h = struct.unpack_from("<II", raw)
    vals = struct.unpack_from("<%df" % (w * h), raw, 8)
    _, tw, th, _, _, at = _pixels(tga_path)
    if (tw, th) != (w, h):
        raise ValueError("map_heights.hgt is %d x %d but map_heights.tga %d x %d - they must match" % (w, h, tw, th))
    is_sea = _heights_sea(at)
    out, relief, W, H = _heights_field(w, h, lambda x, y: vals[y * w + x], is_sea, mask, natural, towns)
    if natural:                                     # the same fine relief and valleys as the picture's
        old = lambda x, y: vals[y * w + x]
        _nature(out, relief, W, H, mask, 0.0, rivers, towns, vertical, _steepest(w, h, old, is_sea))
    for i, v in enumerate(out):
        v = 0.0 if v is None else v
        v = min(v, 0.0) if mask.b[i] else max(v, 0.0)
        out[i] = v * vertical
    return struct.pack("<II", W, H) + struct.pack("<%df" % (W * H), *out)


def hgt_usable(hgt_path, tga_path):
    """Whether map_heights.hgt can be read as the heights at the picture's size: uint32 w, h matching
    map_heights.tga, then w * h floats. A mod may carry an empty or cut one (a tester's Rome mod: 0 bytes - x3
    stopped with 'unpack_from requires a buffer of at least 8 bytes')."""
    try:
        with open(hgt_path, "rb") as fh:
            raw = fh.read()
        if len(raw) < 8:
            return False
        w, h = struct.unpack_from("<II", raw)
        _, tw, th, _, _, _ = _pixels(tga_path)
        return (w, h) == (tw, th) and len(raw) >= 8 + 4 * w * h
    except (OSError, ValueError, struct.error):
        return False


def hgt_from_picture(tga_bytes, top, low):
    """map_heights.hgt made from a map_heights.tga's bytes, as the games convert it (terrain.hgt_value: land grey *
    top / 255, sea low * (255 - blue) / 255; top / low = descr_terrain's max_land_height / min_sea_height)."""
    from .terrain import hgt_value
    w, h, step, top_down, _, raw = _decode(tga_bytes, "map_heights.tga")
    out = []
    for y in range(h):                            # bottom-up rows, as the .hgt keeps them
        r = (h - 1 - y) if top_down else y
        for x in range(w):
            o = (r * w + x) * step
            out.append(hgt_value((raw[o + 2], raw[o + 1], raw[o]), top, low))
    return struct.pack("<II", w, h) + struct.pack("<%df" % (w * h), *out)


def _warp(TX, TY):
    """A smooth sideways shift (in new tiles, -1.2 .. 1.2) for the tile TX, TY: two waves whose sizes stand in the
    golden ratio, so the field never repeats (quasi-periodic, as girih's patterns) and borders bend like a forest's
    or a marsh's edge, not in 3 x 3 steps nor in random dots; the same map, the same shift."""
    import math
    k = 2 * math.pi / 13.0                          # a bend every ~13 new tiles (4 - 5 old ones)
    p = 1 / GOLD                                    # 1.618...
    wx = 0.65 * math.sin(k * (TX + p * TY)) + 0.55 * math.sin(k * p * (TY - 0.5 * TX) + 1.3)
    wy = 0.65 * math.sin(k * (TY - p * TX) + 2.1) + 0.55 * math.sin(k * p * (TX + 0.5 * TY) + 0.4)
    return wx, wy


def kinds_scaled(path, mask=None, sea_colours=(), rounds=2, shore=(), natural=False):
    """A picture of kinds on the heights' grid (map_ground_types, map_climates; 2W+1 x 2H+1, a tile = the point at
    its middle and the 8 round it) made 3 x bigger BY TILES - a tester's DaC map lost its forests: 8 of every 9 new
    tiles took their kind from the old picture's in-between points (Mirkwood: dense forest middles, wilderness
    between them), not from the old tile:
    - each new tile's middle point: the kind of the old tile it lies in (sea or land as mask - the heights' new
      coast - says; where the coast moved, the nearest old tile of that kind);
    - natural edges: the new tiles round each block's middle take the kind most common round them (a mode filter on
      the tiles, twice) - only kinds of real old tiles, the block's middle tile never changes, the sea never;
    - the points between tiles: the old picture's nearest point when its kind is one of the tiles round it (the
      painter's patterns stay), else the kind of the tile round it the nearest old point lies in.
    -> bytes."""
    data, w, h, step, top_down, at = _pixels(path)
    ow, oh = (w - 1) // 2, (h - 1) // 2               # old tiles
    W, H = len(_weights("corners", w)), len(_weights("corners", h))
    TW, TH = (W - 1) // 2, (H - 1) // 2               # new tiles (3 x)
    seas = set(sea_colours)
    is_sea = (lambda c: c in seas) if mask is not None else (lambda c: False)
    old = lambda x, y: at(2 * x + 1, 2 * y + 1)      # an old tile's kind
    default = {True: (196, 0, 0), False: (0, 0, 0)}  # shallow sea / wilderness when nothing near has the kind
    types = [None] * (TW * TH)
    for TY in range(TH):
        oy = min(TY // FACTOR, oh - 1)
        for TX in range(TW):
            ox = min(TX // FACTOR, ow - 1)
            want = bool(mask[(2 * TX + 1, 2 * TY + 1)]) if mask is not None else None
            c = old(ox, oy)
            if want is not None and is_sea(c) != want:     # the coast moved: the nearest old tile of that kind
                best = None
                fx, fy = (TX + 0.5) / FACTOR - 0.5, (TY + 0.5) / FACTOR - 0.5
                for x in range(max(0, ox - 2), min(ow, ox + 3)):
                    for y in range(max(0, oy - 2), min(oh, oy + 3)):
                        k = old(x, y)
                        if is_sea(k) == want:
                            d = (x - fx) ** 2 + (y - fy) ** 2
                            if best is None or d < best[0]:
                                best = (d, k)
                c = best[1] if best else default[want]
            if natural and not (TX % FACTOR == FACTOR // 2 and TY % FACTOR == FACTOR // 2):
                wx, wy = _warp(TX, TY)                     # natural edges: the kind from a bent place (land kinds
                sx = min(max(int((TX + 0.5 + wx) / FACTOR), 0), ow - 1)   # only, never across the coast)
                sy = min(max(int((TY + 0.5 + wy) / FACTOR), 0), oh - 1)
                k = old(sx, sy)
                if not is_sea(k) and not is_sea(c):
                    c = k
            types[TY * TW + TX] = c
    if rounds:
        _round_tiles(types, TW, TH, keep=is_sea)
    shore = set(shore) if mask is not None else set()
    if shore:
        _thin_shore(types, TW, TH, ow, oh, old, is_sea, shore)
    raw = _blank(W, H, step, (0, 0, 0))
    near = lambda j: int(j / FACTOR + 0.5)            # the old point nearest a new one (as _index('corners'))
    for Y in range(H):
        ty = ((Y - 1) // 2,) if Y % 2 else tuple(t for t in (Y // 2 - 1, Y // 2) if 0 <= t < TH)
        for X in range(W):
            tx = ((X - 1) // 2,) if X % 2 else tuple(t for t in (X // 2 - 1, X // 2) if 0 <= t < TW)
            if len(tx) == 1 and len(ty) == 1:
                c = types[ty[0] * TW + tx[0]]
            else:
                want = bool(mask[(X, Y)]) if mask is not None else None
                round_ = [types[b * TW + a] for a in tx for b in ty]
                if want is not None:
                    round_ = [k for k in round_ if is_sea(k) == want] or [default[want]]
                c = at(min(near(X), w - 1), min(near(Y), h - 1))
                if c not in round_:
                    c = round_[0]
                if c in shore and any(k not in shore for k in round_):   # the beach no wider than its tiles
                    c = next(k for k in round_ if k not in shore)
            _put(raw, W, H, step, top_down, X, Y, c)
    return _write(data, W, H, step, raw)


def _round_tiles(types, TW, TH, keep=lambda c: False, rounds=2):
    """Round off the 3 x 3 blocks of new tiles in place: a tile that is not its block's middle takes the kind most
    common in the 3 x 3 tiles round it (Pillow's mode filter, `rounds` times) - never a kind `keep` names (the sea
    stays where the heights put it) and never into one. Without Pillow (only a run from the source may lack it - the
    exe has it) the blocks stay as they are: every tile keeps its old tile's kind either way."""
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return
    ids, pal = {}, []
    idx = bytearray(TW * TH)
    for i, c in enumerate(types):
        k = ids.get(c)
        if k is None:
            if len(ids) >= 255:
                return                                   # not a picture of kinds: leave it
            k = ids[c] = len(pal)
            pal.append(c)
        idx[i] = k
    im = Image.frombytes("L", (TW, TH), bytes(idx))
    for _ in range(rounds):
        im = im.filter(ImageFilter.ModeFilter(3))
    new = im.tobytes()
    kept = {ids[c] for c in ids if keep(c)}
    for TY in range(TH):
        for TX in range(TW):
            if TX % FACTOR == FACTOR // 2 and TY % FACTOR == FACTOR // 2:
                continue                                 # the block's middle: the old tile's own kind
            i = TY * TW + TX
            a, b = idx[i], new[i]
            if a != b and a not in kept and b not in kept:
                types[i] = pal[b]


BEACH = (255, 255, 255)        # map_ground_types: the beach - one tile along the sea in both games' own maps


def _thin_shore(types, TW, TH, ow, oh, old, is_sea, shore):
    """A shore kind (the beach) one tile wide along the new coast, as the games' own maps draw it (vanilla M2TW: 502
    beach tiles on the sea, 1 inland; Rome 571 / 9) - grown 3 x it was a band 3 tiles wide (a tester's DaC x3). A
    shore tile that touches no sea takes the land kind round it; a land tile on the sea where the old coast had that
    shore takes it. Works on new tiles (types, TW x TH); old(x, y) = an old tile's kind (ow x oh)."""
    N8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    at = lambda x, y: types[y * TW + x]

    def on_sea(x, y):
        return any(0 <= x + a < TW and 0 <= y + b < TH and is_sea(at(x + a, y + b)) for a, b in N8)

    def old_shore(x, y):                                  # an old shore tile on the sea
        return old(x, y) in shore and any(0 <= x + a < ow and 0 <= y + b < oh and is_sea(old(x + a, y + b))
                                          for a, b in N8)
    first = list(types)
    for y in range(TH):
        for x in range(TW):
            c = first[y * TW + x]
            if c not in shore or on_sea(x, y):
                continue
            pick = None
            for r in range(1, 5):                         # the land kind round it, nearest ring first
                ring = [first[b * TW + a] for a in range(max(0, x - r), min(TW, x + r + 1))
                        for b in range(max(0, y - r), min(TH, y + r + 1))
                        if max(abs(a - x), abs(b - y)) == r]
                ring = [k for k in ring if k not in shore and not is_sea(k)]
                if ring:
                    pick = max(sorted(set(ring)), key=ring.count)
                    break
            types[y * TW + x] = pick or (0, 0, 0)
    second = list(types)
    for y in range(TH):
        for x in range(TW):
            c = second[y * TW + x]
            if c in shore or is_sea(c) or not on_sea(x, y):
                continue
            ox, oy = min(x // FACTOR, ow - 1), min(y // FACTOR, oh - 1)
            near = [(a, b) for a in range(max(0, ox - 1), min(ow, ox + 2)) for b in range(max(0, oy - 1), min(oh, oy + 2))
                    if old_shore(a, b)]
            if near:
                a, b = min(near, key=lambda q: abs(q[0] * FACTOR + 1 - x) + abs(q[1] * FACTOR + 1 - y))
                types[y * TW + x] = old(a, b)


def ground_scaled(path, mask, sea_colours, natural=False):
    """map_ground_types made bigger by tiles (kinds_scaled): sea or land as the heights' new coast (mask) says, the
    sea ground under the heights' sea as in the games' own maps, the beach one tile wide along the new coast.
    natural: the edges between kinds of ground wind (_warp) instead of following the 3 x 3 blocks."""
    return kinds_scaled(path, mask, sea_colours, shore=(BEACH,), natural=natural)


def climates_scaled(path, natural=False):
    """map_climates made bigger by tiles (kinds_scaled): every new tile the climate of the old tile it lies in, the
    edges between climates rounded (natural: winding as well)."""
    return kinds_scaled(path, natural=natural)


def _pixels(path):
    """{(x, y): (r, g, b)} bottom-up tile coordinates, the decoded picture parts."""
    data, w, h, step, top_down, raw = _read(path)

    def at(x, y):
        r = (h - 1 - y) if top_down else y
        o = (r * w + x) * step
        return (raw[o + 2], raw[o + 1], raw[o])
    return data, w, h, step, top_down, at


def _blank(w, h, step, colour):
    px = bytes((colour[2], colour[1], colour[0])) + (b"\xff" if step == 4 else b"")
    return bytearray(px * (w * h))


def _put(raw, w, h, step, top_down, x, y, colour):
    r = (h - 1 - y) if top_down else y
    o = (r * w + x) * step
    raw[o:o + 3] = bytes((colour[2], colour[1], colour[0]))


def land_colours(regions_path, region_colours, heights_path=None):
    """The colours of map_regions that are land: the regions' (descr_regions), towns' and ports' (a port stands on
    a coastal LAND tile - its heights' point is land in every vanilla map of both games), and any other colour
    whose tiles the heights mostly hold above the sea - a region descr_regions does not list (a mod's own form, a
    typo) is land all the same; without it its town lost its land round it (a tester's Erebor: 9 town pixels)."""
    lands = set(region_colours) | {CITY, PORT}
    data, w, h, step, top_down, at = _pixels(regions_path)
    others = {}
    for y in range(h):
        for x in range(w):
            c = at(x, y)
            if c not in lands:
                others.setdefault(c, []).append((x, y))
    if not others:
        return lands
    if heights_path and os.path.isfile(heights_path):
        _, hw, hh, _, _, hat = _pixels(heights_path)
        sea = _heights_sea(hat)
        for c, tiles in others.items():
            land = sum(1 for x, y in tiles if 2 * x + 1 < hw and 2 * y + 1 < hh and not sea(2 * x + 1, 2 * y + 1))
            if land * 2 > len(tiles):
                lands.add(c)
    return lands


def coast_mask(path, lands, natural=False):
    """map_regions' land made bigger smoothly: Mask of the new tiles (lands: land_colours - towns and ports count as
    land). natural: the coast winds (bays and capes, _warp) instead of running in steps and 45-degree cuts; every
    old tile's middle keeps its land or sea."""
    data, w, h, step, top_down, at = _pixels(path)
    lands = set(lands) | {CITY, PORT}
    return _share_mask("tiles", w, h, lambda x, y: at(x, y) in lands, natural)[0]


def _mode(cols):
    return max(sorted(set(cols)), key=cols.count) if cols else None


def regions_scaled(path, lands, mask=None, keep_land=(), info=None, natural=False):
    """map_regions x3 with a SMOOTH coast (mask: coast_mask): a land pixel takes the region of the old land tile round
    it with the most weight, a sea pixel the sea's colour; keep_land (pixels under a river) stay land. Each town on its
    block's middle pixel with its own region all round it (the game wants the 8 tiles round a town its region or
    sea); each port on a coastal land pixel of its block touching the sea and its region's land (as every port of the
    games' own maps stands). info (a dict) gets 'land': Mask of the new tiles' land (towns and ports land) and
    'moved_ports'. -> bytes."""
    data, w, h, step, top_down, at = _pixels(path)
    lands = set(lands) | {CITY, PORT}
    plain = lands - {CITY, PORT}                  # the colours a land pixel takes
    if mask is None:
        mask = coast_mask(path, lands, natural)
    keep_land = set(keep_land)
    N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
    N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))

    def around(x, y, ring, ok):
        return [at(x + dx, y + dy) for dx, dy in ring if 0 <= x + dx < w and 0 <= y + dy < h
                and ok(at(x + dx, y + dy))]

    def nearest_land(x, y):
        for r in range(2, 7):
            cols = [at(a, b) for a in range(max(0, x - r), min(w, x + r + 1)) for b in range(max(0, y - r), min(h, y + r + 1))
                    if max(abs(a - x), abs(b - y)) == r and at(a, b) in plain]
            if cols:
                return _mode(cols)
        return None
    fill, towns, ports = {}, [], []              # an old town / port tile: the region's colour round it
    from .moddata import town_colours            # the town's own region - the one the editor and the game see
    owner = town_colours(at, w, h, [(x, y) for y in range(h) for x in range(w) if at(x, y) == CITY], plain)
    for y in range(h):
        for x in range(w):
            c = at(x, y)
            if c == CITY:
                fill[(x, y)] = owner.get((x, y)) or _mode(around(x, y, N8, lambda q: q in plain)) or \
                    nearest_land(x, y) or c
                towns.append((x, y))
            elif c == PORT:                       # the region it serves: its land on a side first
                fill[(x, y)] = _mode(around(x, y, N4, lambda q: q in plain)) or \
                    _mode(around(x, y, N8, lambda q: q in plain)) or nearest_land(x, y) or c
                ports.append((x, y))
    colour = lambda x, y: fill.get((x, y), at(x, y))
    land_of = lambda x, y: colour(x, y) in plain
    W, H = w * FACTOR, h * FACTOR
    raw = _blank(W, H, step, (0, 0, 0))
    for X, Y, pts in _sources("tiles", w, h, natural):     # natural: borders between regions wind as the coast
        land = mask[(X, Y)] or (X, Y) in keep_land
        p = _pick(pts, land, land_of)
        if p is None and land:                    # no land tile round it (a river kept on land, a coast corner)
            p = min(((x, y) for x in range(max(0, X // FACTOR - 1), min(w, X // FACTOR + 2))
                     for y in range(max(0, Y // FACTOR - 1), min(h, Y // FACTOR + 2)) if land_of(x, y)),
                    key=lambda q: abs(new_xy(*q)[0] - X) + abs(new_xy(*q)[1] - Y), default=None)
            p = p + (0,) if p else None
        if p is None:
            p = max(pts, key=lambda q: q[2])
        _put(raw, W, H, step, top_down, X, Y, colour(p[0], p[1]))

    def get(X, Y):
        r = (H - 1 - Y) if top_down else Y
        o = (r * W + X) * step
        return (raw[o + 2], raw[o + 1], raw[o])
    if natural:
        _join_pieces(raw, W, H, step, top_down, plain)
    town_px = set()
    for x, y in towns:                            # the town and its own region all round it (its 3 x 3 block)
        cx, cy = new_xy(x, y)
        for dx, dy in N8:
            if get(cx + dx, cy + dy) in plain:
                _put(raw, W, H, step, top_down, cx + dx, cy + dy, fill[(x, y)])
        _put(raw, W, H, step, top_down, cx, cy, CITY)
        town_px.add((cx, cy))
    near_town = {(a + dx, b + dy) for a, b in town_px for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    port_px, moved = set(), []

    def sea_px(X, Y):
        return 0 <= X < W and 0 <= Y < H and get(X, Y) not in lands

    def good(X, Y, reg, convert):
        if not (0 <= X < W and 0 <= Y < H) or (X, Y) in near_town or (X, Y) in port_px:
            return False
        here = get(X, Y)
        if convert:
            if here in lands:
                return False
        elif here not in plain:
            return False
        sides = [(X + dx, Y + dy) for dx, dy in N4]
        return any(sea_px(a, b) for a, b in sides) and \
            any(0 <= a < W and 0 <= b < H and get(a, b) == reg for a, b in sides)
    for x, y in ports:
        reg = fill[(x, y)]
        cx, cy = new_xy(x, y)
        toward = [(dx, dy) for dx, dy in N4 if not (0 <= x + dx < w and 0 <= y + dy < h)
                  or at(x + dx, y + dy) not in lands]          # where the old port met the sea
        pref = (cx + toward[0][0], cy + toward[0][1]) if toward else (cx, cy)
        spot = None
        for convert in (False, True):            # a land pixel by the sea first; else a sea pixel by the land
            cands = [(X, Y) for X in range(cx - 4, cx + 5) for Y in range(cy - 4, cy + 5) if good(X, Y, reg, convert)]
            if cands:
                spot = min(cands, key=lambda q: (max(abs(q[0] - cx), abs(q[1] - cy)), get(*q) != reg,
                                                 abs(q[0] - pref[0]) + abs(q[1] - pref[1]), q[1], q[0]))
                break
        if spot is None:
            spot = pref if 0 <= pref[0] < W and 0 <= pref[1] < H else (cx, cy)
            moved.append(((x, y), spot, "no coastal place found - check this port"))
        _put(raw, W, H, step, top_down, spot[0], spot[1], PORT)
        port_px.add(spot)
    if info is not None:
        land = Mask(W, H)
        for Y in range(H):
            for X in range(W):
                if get(X, Y) in lands:
                    land.b[Y * W + X] = 1
        info["land"] = land
        info["towns"] = town_px
        info["moved_ports"] = moved
    return _write(data, W, H, step, raw)


def _join_pieces(raw, W, H, step, top_down, plain):
    """A bent border may cut a sliver off a region: a piece of a region's colour holding no block middle (every old
    tile's middle keeps its own region, so each real piece - an island too - holds one) takes the region round it
    most (side neighbours, land only), until none is left; a region stays one piece as it was."""
    def get(X, Y):
        r = (H - 1 - Y) if top_down else Y
        o = (r * W + X) * step
        return (raw[o + 2], raw[o + 1], raw[o])
    mid = FACTOR // 2
    N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for _ in range(4):
        seen = bytearray(W * H)
        loose = []
        for Y in range(H):
            for X in range(W):
                if seen[Y * W + X]:
                    continue
                c = get(X, Y)
                if c not in plain:
                    continue
                piece, st, real = [], [(X, Y)], False
                seen[Y * W + X] = 1
                while st:
                    a, b = st.pop()
                    piece.append((a, b))
                    real = real or (a % FACTOR == mid and b % FACTOR == mid)
                    for dx, dy in N4:
                        q = (a + dx, b + dy)
                        if 0 <= q[0] < W and 0 <= q[1] < H and not seen[q[1] * W + q[0]] and get(*q) == c:
                            seen[q[1] * W + q[0]] = 1
                            st.append(q)
                if not real:
                    loose.append((c, piece))
        if not loose:
            return
        for c, piece in loose:
            inside = set(piece)
            round_ = [get(a + dx, b + dy) for a, b in piece for dx, dy in N4
                      if 0 <= a + dx < W and 0 <= b + dy < H and (a + dx, b + dy) not in inside]
            round_ = [k for k in round_ if k in plain and k != c]
            if round_:
                k = _mode(round_)
                for a, b in piece:
                    _put(raw, W, H, step, top_down, a, b, k)


def _agreement(regions_path, heights_path, lands):
    """agree(x, y): whether the old map_regions and map_heights agreed about tile (x, y) - land in one, land in the
    other (they always do in both games' own maps; a mod may differ here and there, and keeps that)."""
    _, w, h, _, _, rat = _pixels(regions_path)
    _, hw, hh, _, _, hat = _pixels(heights_path)
    sea = _heights_sea(hat)
    lands = set(lands) | {CITY, PORT}

    def agree(x, y):
        if not (0 <= x < w and 0 <= y < h) or 2 * x + 1 >= hw or 2 * y + 1 >= hh:
            return False
        return (rat(x, y) in lands) == (not sea(2 * x + 1, 2 * y + 1))

    def in_water(x, y):
        """The old tile and every tile round it are water in the heights (a sea tile inside a mod's navigable river,
        whose banks map_regions calls land - a tester's DaC)."""
        return all(sea(min(max(2 * (x + a) + 1, 0), hw - 1), min(max(2 * (y + b) + 1, 0), hh - 1))
                   for a in (-1, 0, 1) for b in (-1, 0, 1))
    agree.in_water = in_water
    return agree


def heights_from_tiles(land, agree, own):
    """The heights' sea at the new size made to fit the new map_regions (land: info['land'] of regions_scaled): a
    tile's middle point is sea exactly when its tile is - as in both games' own maps -, a point between tiles is sea
    when every tile round it is; where those tiles differ, or where the old map_regions and map_heights did not agree
    about the old tile (agree(x, y) False - a mod's own mismatch, kept as it was), the heights' own smooth coast (own)
    decides; so does it where the new map_regions made land of an old tile the heights hold under water all round
    (agree.in_water: a sea tile inside a mod's navigable river - the land the smooth coast gave it from the river's
    'land' banks rose as islands in the game, a tester's DaC x3). -> Mask of the points (6W+1 x 6H+1)."""
    TW, TH = land.W, land.H
    PW, PH = 2 * TW + 1, 2 * TH + 1
    out = Mask(PW, PH)

    def tiles_of(i, n):
        if i % 2:
            return ((i - 1) // 2,)
        return tuple(t for t in (i // 2 - 1, i // 2) if 0 <= t < n)
    ok_old = {}
    for J in range(PH):
        ty = tiles_of(J, TH)
        for I in range(PW):
            tx = tiles_of(I, TW)
            first, same, fine = None, True, True
            for a in tx:
                for b in ty:
                    v = land.b[b * TW + a]
                    if first is None:
                        first = v
                    elif v != first:
                        same = False
                    k = (a // FACTOR, b // FACTOR)
                    g = ok_old.get(k)
                    if g is None:
                        wet = getattr(agree, "in_water", None)
                        g = ok_old[k] = (agree(*k), bool(wet(*k)) if wet else False)
                    fine = fine and g[0] and not (v and g[1])
            if same and fine and first is not None:
                sea = not first
            else:
                sea = own[(I, J)]
            if sea:
                out.b[J * PW + I] = 1
    return out


GOLD = (5 ** 0.5 - 1) / 2                                      # 0.618...: the golden ratio's part
MEANDER = (0, 1, 0, -1)                                        # a bend each way, half a wave apart


def _meander(t, row):
    """A river's sideways offset (-1, 0, 1 pixels) at step t along a straight run, row = the run's other
    coordinate: a meander (rivers swing every ~12 channel widths - Langbein & Leopold's sine-generated curve) whose
    phase moves on by 1 or 2 by the Fibonacci word (the golden ratio's 1-D quasi-crystal, girih's cousin) - never the
    same twice, the same map always the same."""
    g = 1 - GOLD                                              # 0.382: the share of the longer steps
    seed = (row * GOLD) % 1.0
    phase = t + int(t * g + seed)
    return MEANDER[phase % 4]


def _river_offsets(lines, is_river, land, cx_of):
    """{old river tile: (ox, oy)} - where in its 3 x 3 block a river tile's point lies (0, 0 = the middle): at a bend
    the point moves one pixel into the bend (the corner cut, as a real river rounds it); on a straight run it swings
    by _meander; a tile with a ford or a source, a river's end or a fork keeps the middle; never onto the new sea."""
    river = {p for p, c in lines.items() if is_river(c)}

    def links(p):
        x, y = p
        out = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, y + dy) in river]
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            if (x + dx, y + dy) in river and (x + dx, y) not in river and (x, y + dy) not in river:
                out.append((dx, dy))
        return out
    off = {}
    ends = set()
    for p in river:
        ls = links(p)
        if len(ls) <= 1:
            ends.add(p)
        o = (0, 0)
        if len(ls) == 2 and lines[p] == (0, 0, 255):
            (a, b), (c, d) = ls
            sx, sy = a + c, b + d
            if (sx, sy) != (0, 0):                            # a bend: into it
                o = (max(-1, min(1, sx)), max(-1, min(1, sy)))
            elif b == 0:                                      # a straight run along x: swing in y
                o = (0, _meander(p[0], p[1]))
            elif a == 0:                                      # along y: swing in x
                o = (_meander(p[1], p[0]), 0)
        if o != (0, 0) and land is not None:
            cx, cy = cx_of(*p)
            if not land.get((cx + o[0], cy + o[1]), True):
                o = (0, 0)
        off[p] = o
    return off, ends


def _line4(a, b):
    """The pixels from a to b, side by side only (a diagonal move becomes across, then up): a river the game reads
    as unbroken."""
    (x, y), (x1, y1) = a, b
    out = [(x, y)]
    dx, dy = abs(x1 - x), abs(y1 - y)
    sx, sy = (1 if x1 > x else -1), (1 if y1 > y else -1)
    err = dx - dy
    while (x, y) != (x1, y1):
        e2 = 2 * err
        if e2 > -dy and x != x1:
            err -= dy
            x += sx
            out.append((x, y))
        elif y != y1:
            err += dx
            y += sy
            out.append((x, y))
        else:
            x += sx
            out.append((x, y))
    return out


def features_scaled(path, land=None, natural=False):
    """map_features x3: black, rivers drawn as 1-pixel lines from block middle to block middle - a corner link a
    staircase (one step across, one up, ...: always side by side, never a corner-only step the game stops a river
    at); a river that met the sea runs on to the new, smoother coast (land: coast_mask) and stops there - none of it
    on the new sea; cliffs and Medieval II's
    land bridges drawn as lines the same way (a bridge only on its middles left the water between them: a tester's
    DaC map), a bridge that ended on the water carried on to the land beside it; every other feature on its block's
    middle pixel. -> (bytes, the river pixels)."""
    data, w, h, step, top_down, at = _pixels(path)
    W, H = w * FACTOR, h * FACTOR
    raw = _blank(W, H, step, (0, 0, 0))
    lines = {}
    for y in range(h):
        for x in range(w):
            c = at(x, y)
            if c != (0, 0, 0):
                lines[(x, y)] = c
    river = (0, 0, 255)
    drawn = set()

    def kind(c):
        return "river" if c in RIVERY else ("cliff" if c == CLIFF else ("bridge" if c == BRIDGE else None))
    line_colour = {"river": river, "cliff": CLIFF, "bridge": BRIDGE}

    def paint(px, py, c):
        if 0 <= px < W and 0 <= py < H:
            _put(raw, W, H, step, top_down, px, py, c)
            if c in RIVERY:
                drawn.add((px, py))

    off, river_ends = _river_offsets(lines, lambda c: kind(c) == "river", land, new_xy) if natural else ({}, set())
    if natural:                                               # rivers through their shifted points (see above)
        done = set()
        for p, o in off.items():
            cx, cy = new_xy(*p)
            a = (cx + o[0], cy + o[1])
            for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1), (-1, 1), (-1, -1), (-1, 0), (0, -1)):
                q = (p[0] + dx, p[1] + dy)
                if q not in off or (q, p) in done:
                    continue
                if dx and dy and ((p[0] + dx, p[1]) in off or (p[0], p[1] + dy) in off):
                    continue                                  # a corner with a straight way round it: that way
                done.add((p, q))
                qx, qy = new_xy(*q)
                b = (qx + off[q][0], qy + off[q][1])
                for px, py in _line4(a, b):
                    paint(px, py, river)
            paint(a[0], a[1], river)
        # a river is ONE pixel wide (the user, 2026-10-04: 'never wider than one tile'): where two pieces meet the
        # lines can touch in a 2 x 2 square - one pixel of it goes, the one whose neighbours stay joined without it
        def joined_without(q):
            near = [(q[0] + a, q[1] + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (q[0] + a, q[1] + b) in drawn]
            if len(near) <= 1:
                return False                                  # an end: kept
            ring = {(q[0] + a, q[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)} & drawn
            seen, todo = {near[0]}, [near[0]]
            while todo:
                x0, y0 = todo.pop()
                for r in ((x0 + 1, y0), (x0 - 1, y0), (x0, y0 + 1), (x0, y0 - 1)):
                    if r in ring and r not in seen:
                        seen.add(r)
                        todo.append(r)
            return all(n_ in seen for n_ in near)
        for _ in range(8):
            squares = [(x0, y0) for (x0, y0) in drawn if (x0 + 1, y0) in drawn and (x0, y0 + 1) in drawn and
                       (x0 + 1, y0 + 1) in drawn]
            if not squares:
                break
            for x0, y0 in sorted(squares):
                cell = [(x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)]
                if not all(q in drawn for q in cell):
                    continue                                  # a square beside it was thinned already
                q = next((q for q in cell if joined_without(q)), None)
                if q is not None:
                    _put(raw, W, H, step, top_down, q[0], q[1], (0, 0, 0))
                    drawn.discard(q)
        # where two pieces meet at a moved point a one-pixel spur can stick out: cut every pixel with one neighbour
        # that is not a river's real end (its source or its mouth stays)
        for _ in range(4):
            spurs = [q for q in drawn if (q[0] // FACTOR, q[1] // FACTOR) not in river_ends and
                     sum((q[0] + a, q[1] + b) in drawn for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))) <= 1]
            if not spurs:
                break
            for q in spurs:
                _put(raw, W, H, step, top_down, q[0], q[1], (0, 0, 0))
                drawn.discard(q)
    for (x, y), c in lines.items():
        k = kind(c)
        if not k:
            continue
        cx, cy = new_xy(x, y)
        colour = line_colour[k]
        straight = () if natural and k == "river" else ((1, 0), (0, 1))     # natural rivers: drawn above
        for dx, dy in straight:                               # each straight link once
            o = lines.get((x + dx, y + dy))
            if o is not None and kind(o) == k:
                for s in range(1, FACTOR):
                    paint(cx + dx * s, cy + dy * s, colour)
        for dx, dy in ((1, 1), (1, -1)) if straight else ():  # corner links with no straight path between
            o = lines.get((x + dx, y + dy))
            if o is None or kind(o) != k:
                continue
            if kind(lines.get((x + dx, y), (0, 0, 0))) == k or kind(lines.get((x, y + dy), (0, 0, 0))) == k:
                continue
            px, py = cx, cy
            for s in range(FACTOR):                           # a staircase: across one, then up / down one
                px += 1
                paint(px, py, colour)
                py += dy
                if (px, py) != (cx + FACTOR, cy + dy * FACTOR):
                    paint(px, py, colour)
        ends = sum(1 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if kind(lines.get((x + a, y + b), (0, 0, 0))) == "river")
        if natural and k == "river":                          # a real end only (a corner link is a link too)
            ends = 1 if (x, y) in river_ends else 2
        if k == "river" and land is not None and ends <= 1:  # a river's end: on to the new coast / the edge
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h):            # it ran off the map's edge: to the new edge too
                    for s in range(1, FACTOR // 2 + 1):
                        paint(cx + dx * s, cy + dy * s, colour)
                    continue
                if kind(lines.get((nx, ny), (0, 0, 0))) == "river":
                    continue
                if land.get(new_xy(nx, ny), True):           # that tile was not sea
                    continue
                px, py = cx, cy
                for s in range(1, 2 * FACTOR):
                    if not land.get((px + dx, py + dy), False):
                        break                                 # the next pixel is sea: this one touches it
                    px, py = px + dx, py + dy
                    paint(px, py, colour)
        if k == "bridge" and land is not None and not land.get(new_xy(x, y), True):
            links = sum(1 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if kind(lines.get((x + a, y + b), (0, 0, 0))) == "bridge")
            if links <= 1:                                    # a bridge's end on the water: on to the land beside it
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and kind(lines.get((nx, ny), (0, 0, 0))) != "bridge" \
                            and land.get(new_xy(nx, ny), False):
                        for s_ in range(1, FACTOR + 1):
                            paint(cx + dx * s_, cy + dy * s_, BRIDGE)
    for (x, y), c in lines.items():                           # every feature's own colour on its middle
        if (x, y) in off and c == river:                      # a natural river is drawn already (a moved point
            continue                                          # whose spur was cut must not come back)
        o = off.get((x, y), (0, 0))
        cx, cy = new_xy(x, y)
        at = (cx + o[0], cy + o[1])
        if (x, y) in off and at not in drawn:                 # a ford / source whose point was cut as a spur: on the
            at = next((q for q in ((at[0], at[1] + 1), (at[0], at[1] - 1), (at[0] + 1, at[1]),   # river beside it
                                   (at[0] - 1, at[1])) if q in drawn), at)
        paint(at[0], at[1], c)
    if land is not None:                                      # a river ends where the new coast begins: land kept
        for p in [p for p in drawn if not land.get(p, True)]: # under it stood in the sea as a sandbar (a tester's
            _put(raw, W, H, step, top_down, p[0], p[1], (0, 0, 0))   # DaC: a strip of beach off every river mouth)
            drawn.discard(p)
    return _write(data, W, H, step, raw), drawn


# ---------------------------------------------------------------------------
RE_CHAR_XY = re.compile(r"(\bx\s+)(-?\d+)(\s*,\s*y\s+)(-?\d+)")
RE_RESOURCE = re.compile(r"^(\s*resource\s+[^,;]+,\s*)(-?\d+)(\s*,\s*)(-?\d+)")
RE_FORT = re.compile(r"^(\s*(?:fort|watchtower|landmark)\s+(?:[A-Za-z_]\w*\s+)?)(-?\d+)(\s*,?\s*)(-?\d+)")
RE_POSITION = re.compile(r"^(\s*position\s+)(-?\d+)(\s*,\s*)(-?\d+)")
RE_SCRIPT_XY = re.compile(r"\b\d+\s*,\s*\d+\b")
# a Squirrel / Lua line that may put something on the map: a tile command with its numbers, or a tile / teleport /
# spawn / coordinates call with an 'x, y' (screen places of the interface, colours ... are not map tiles)
RE_CODE_TILE = re.compile(r"(?<![A-Za-z])tile|Tile|[Tt]eleport|[Ss]pawn|[Cc]oord")       # not hostile
ENGINE_SCRIPTS = ("core", "ui", "main.nut", "manifest.nut")     # REX's / M2EX's own interface in script/

# Script commands and conditions that name campaign-map tiles (REX's and M2EX's docudemon and console lists, 2026-10-03)
# and what their numbers are: xy = a tile; xyr = a tile and a radius in tiles; area = two corners; dxy = a distance in
# tiles, then a tile; rect = a corner, then [width height]. Everything else in a script - battle positions (unit_*,
# camera bookmarks, point_at_location, label_location ...), money, turns - is left as it is.
SCRIPT_TILES = {
    "move_strat_camera": "xy", "snap_strat_camera": "xy", "point_at_strat_position": "xy", "reveal_tile": "xy",
    "move": "xy", "reposition_character": "xy", "move_character": "xy", "go_to_pos": "xy",
    "create_fort": "xy", "destroy_fort": "xy", "rename_fort": "xy", "create_resource": "xy", "remove_resource": "xy",
    "reveal_radius": "xyr", "reveal_area": "area",
    "I_CharacterTypeNearTile": "dxy", "I_CharacterNameNearTile": "dxy", "I_FactionNearTile": "dxy",
    "IsPositionInRect": "rect",
}
NEEDS = {"xy": 2, "xyr": 3, "area": 4, "dxy": 3, "rect": 2}
RE_SCRIPT_CMD = re.compile(r"(?<![\w.])(%s)(?![\w.])" % "|".join(sorted(SCRIPT_TILES, key=len, reverse=True)), re.I)
RE_SCRIPT_STOP = re.compile(r"(?<![\w.])(?:and|or)(?![\w.])", re.I)
RE_INT = re.compile(r"(?<![\w.-])-?\d+(?![\w.])")
# lines of battle commands: their numbers are places on a battle map, not tiles
RE_BATTLE = re.compile(r"(?<![\w.])(?:unit_\w+|I_Unit\w*|\w*camera_bookmark\w*|camera_\w+|point_at_location|"
                       r"point_at_unit\w*|label_location|battle_\w+|show_battle_\w+|area_effect|ui_indicator|"
                       r"ai_gta_\w+|add_road_point)(?![\w.])", re.I)


def code_names_tiles(line):
    """Does a line of a Lua / Squirrel script name map tiles by number (a tile command with its x y, a teleport /
    spawn / tile call with x, y)?"""
    for m in RE_SCRIPT_CMD.finditer(line):               # in code a command is a string: runScriptCommand("move", ..)
        if m.start() and line[m.start() - 1] in "\"'" and len(RE_INT.findall(line[m.end():])) >= 2:
            return True
    return bool(RE_CODE_TILE.search(line) and RE_SCRIPT_XY.search(line))


def code_with_tiles(root):
    """[(folder, [script files])] of the Lua (eopData/eopScripts) and Squirrel (script/) scripts beside a mod's data
    that name map tiles by number - the engines' own interface (script/core, script/ui) left out."""
    out = []
    for sub, ext in ((("eopData", "eopScripts"), ".lua"), (("script",), ".nut")):
        d = os.path.join(root, *sub)
        hits = []
        for dirpath, dirs, files in os.walk(d):
            if dirpath == d and ext == ".nut":
                dirs[:] = [x for x in dirs if x.lower() not in ENGINE_SCRIPTS]
                files = [x for x in files if x.lower() not in ENGINE_SCRIPTS]
            for name in files:
                if name.lower().endswith(ext):
                    with open(os.path.join(dirpath, name), encoding="latin-1") as fh:
                        if any(code_names_tiles(line) for line in fh):
                            hits.append(name)
        if hits:
            out.append(("/".join(sub), sorted(hits)))
    return out


def _script_values(kind, nums):
    """The new values for a command's numbers (as many as it takes). A tile goes to its block's middle; a distance d
    or a radius becomes 3d + 1 (anywhere on the blocks of the tiles that were within d - 'distance 0' = the whole
    block of the old tile); a rectangle's size x 3 (a character in a block's middle is inside exactly when he was
    before); an area's corners take in their whole blocks."""
    if kind == "xy":
        return list(new_xy(nums[0], nums[1]))
    if kind == "xyr":
        return list(new_xy(nums[0], nums[1])) + [nums[2] * FACTOR + FACTOR // 2]
    if kind == "dxy":
        return [nums[0] * FACTOR + FACTOR // 2] + list(new_xy(nums[1], nums[2]))
    if kind == "area":
        x1, y1, x2, y2 = nums[:4]
        lo = lambda a, b: FACTOR * a if a <= b else FACTOR * a + FACTOR - 1
        return [lo(x1, x2), lo(y1, y2), lo(x2, x1), lo(y2, y1)]
    out = list(new_xy(nums[0], nums[1]))                          # rect: a corner, then width / height
    return out + [v * FACTOR for v in nums[2:4]]


def move_script_line(text):
    """One script line with its campaign-map tiles moved to their blocks (a spawned character's 'x N, y M' too);
    (the new text, how many places moved, places a known command wanted but could not be read)."""
    code, sep, comment = text.partition(";")
    moved = missing = 0
    def char_xy(m):
        x, y = new_xy(int(m.group(2)), int(m.group(4)))
        return "%s%d%s%d" % (m.group(1), x, m.group(3), y)
    code, n = RE_CHAR_XY.subn(char_xy, code)
    moved += n
    cmds = list(RE_SCRIPT_CMD.finditer(code))
    edits = []
    for k, m in enumerate(cmds):
        kind = SCRIPT_TILES[next(c for c in SCRIPT_TILES if c.lower() == m.group(1).lower())]
        end = cmds[k + 1].start() if k + 1 < len(cmds) else len(code)
        stop = RE_SCRIPT_STOP.search(code, m.end(), end)
        if stop:
            end = stop.start()
        ints = list(RE_INT.finditer(code, m.end(), end))[:4 if kind == "rect" else NEEDS[kind]]
        if len(ints) < NEEDS[kind]:
            missing += 1
            continue
        new = _script_values(kind, [int(i.group()) for i in ints])
        edits += [(i.start(), i.end(), str(v)) for i, v in zip(ints, new)]
        moved += 1
    for a, b, v in sorted(edits, reverse=True):
        code = code[:a] + v + code[b:]
    return code + sep + comment, moved, missing


def script_files(mod, campaign):
    """The campaign's script files: the ones descr_strat names after its 'script' line, and campaign_script.txt."""
    from .moddata import _ci
    from .textio import strip_comment, tokens
    camp = mod.campaign_dir(campaign)
    names = []
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    if sp:
        texts = mod.load(sp).texts()
        for i, t in enumerate(texts):
            if tokens(strip_comment(t))[:1] == ["script"]:
                for t2 in texts[i + 1:]:
                    t2 = strip_comment(t2).strip()
                    if t2:
                        names.append(t2)
                        break
    names.append("campaign_script.txt")
    out = []
    for n in names:
        p = _ci(camp, n.replace("\\", "/"))
        if p and os.path.isfile(p) and p not in out:
            out.append(p)
    return out


def move_script(f):
    """Every campaign-map tile in a script file moved; (places moved, [line numbers left to check by hand]): lines a
    known command could not be read on, and lines holding 'x, y'-like numbers outside any known command and outside
    the battle commands."""
    moved, check = 0, []
    for i in range(len(f.raw)):
        text = f.text(i)
        new, n, missing = move_script_line(text)
        if n:
            f.raw[i] = f.make(new)
            moved += n
        code = text.split(";")[0]
        if missing or (not n and RE_SCRIPT_XY.search(code) and not RE_BATTLE.search(code)):
            check.append(i + 1)
    return moved, check


def _move_line(text, patterns):
    code, sep, comment = text.partition(";")
    for rx in patterns:
        m = rx.search(code)
        if m:
            x, y = new_xy(int(m.group(2)), int(m.group(4)))
            code = code[:m.start()] + m.group(1) + str(x) + m.group(3) + str(y) + code[m.end():]
            return code + sep + comment, True
    return text, False


def move_coordinates(f, patterns):
    """Every coordinate in a text file's lines moved to its block's middle; how many."""
    n = 0
    for i in range(len(f.raw)):
        new, hit = _move_line(f.text(i), patterns)
        if hit:
            f.raw[i] = f.make(new)
            n += 1
    return n


def _dimensions(f, vertical=1.0):
    """descr_terrain.txt: width / height x 3; max_land_height / min_sea_height x vertical."""
    n = 0
    for i in range(len(f.raw)):
        t = f.text(i)
        m = re.match(r"^(\s*(?:width|height)\s+)(\d+)(.*)$", t)
        if m:
            f.raw[i] = f.make(m.group(1) + str(int(m.group(2)) * FACTOR) + m.group(3))
            n += 1
            continue
        m = re.match(r"^(\s*(?:max_land_height|min_sea_height)\s+)(-?[\d.]+)(.*)$", t)
        if m and vertical != 1.0:
            v = float(m.group(2)) * vertical
            dec = len(m.group(2).partition(".")[2])
            f.raw[i] = f.make(m.group(1) + ("%.*f" % (dec, v) if dec else str(int(round(v)))) + m.group(3))
    return n


def plan_upscale(plan, campaign, vertical=FACTOR, progress=None):
    """Every file of the map made 3 x bigger, in the plan (nothing written until Apply). vertical: how much higher
    the hills, mountains and sea floor get (3 = in proportion with the wider land; 1 = as high as before). Returns
    the warnings. progress(text) is told each step (a big map takes half a minute)."""
    say = progress or (lambda text: None)
    mod = plan.mod
    warn = []
    regions_path = mod.campaign_file(campaign, "map_regions.tga")
    base = os.path.dirname(regions_path)
    camp = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt"))
    colours = [v["colour"] for v in mod.regions(campaign).values()]
    from .terrain import SEA
    hpath = os.path.join(base, "map_heights.tga")
    if not os.path.isfile(hpath):
        hpath = None
    lands = land_colours(regions_path, colours, hpath)   # the regions' colours and any other land colour
    say("the coast (map_regions)...")
    coast = coast_mask(regions_path, lands, natural=True)  # the regions' land, made bigger with a winding coast
    keep_land, rivers = (), ()
    feats = os.path.join(base, "map_features.tga")
    if os.path.isfile(feats):
        say("rivers, cliffs and land bridges (map_features)...")
        data, rivers = features_scaled(feats, coast, natural=True)   # natural rivers (bends cut, meanders), stopping
        #                                                   at the new coast: no land kept under them
        plan.binary(feats, data)
        plan.note(None, "map_features.tga made 3 x bigger (rivers drawn naturally - bends rounded, gentle meanders, "
                        "one pixel wide -, cliffs and land bridges as unbroken lines, river mouths on the new coast)")
    say("map_regions.tga...")
    info = {}
    plan.binary(regions_path, regions_scaled(regions_path, lands, coast, keep_land, info, natural=True))
    plan.note(None, "map_regions.tga made 3 x bigger (a winding coast and winding borders between regions, no 3 x 3 "
                    "steps, every region in as many pieces as before; every town with its own region round it, "
                    "every port on a coastal land tile touching the sea and its region)")
    for (x, y), spot, why in info.get("moved_ports", []):
        warn.append("the port at %d, %d: %s (now at %d, %d)" % (x, y, why, spot[0], spot[1]))
    hmask = heights_data = None
    if hpath:
        say("the heights' coast...")
        hmask = heights_from_tiles(info["land"], _agreement(regions_path, hpath, lands), heights_mask(hpath))
    for name, kind in BASE_PICTURES.items():
        p = os.path.join(base, name)
        if not os.path.isfile(p) or name in ("map_features.tga", "map_regions.tga"):
            continue
        say("%s..." % name)
        if name == "map_heights.tga":
            data = smooth_scaled(p, kind, sea=True, mask=hmask, natural=True, rivers=rivers,
                                 towns=info.get("towns", ()), vertical=vertical)
            note = "the relief the natural way: bent with the ground, rocky mountains, rivers in their valleys, no " \
                   "slope steeper than the old map's steepest, the same coast as map_regions"
        elif name == "map_ground_types.tga" and hmask is not None:
            data = ground_scaled(p, hmask, SEA, natural=True)
            note = "every tile the ground of the old tile it lies in, the sea ground under the heights' new coast, " \
                   "winding edges (no 3 x 3 steps)"
        elif name == "map_climates.tga":
            data = climates_scaled(p, natural=True)
            note = "every tile the climate of the old tile it lies in, winding edges (no 3 x 3 steps)"
        elif name == "map_roughness.tga":
            data = smooth_scaled(p, kind)
            note = "smooth"
        else:
            data, _ = scaled(p, kind)
            note = ""
        plan.binary(p, data)
        if name == "map_heights.tga":
            heights_data = data
        plan.note(None, "%s made 3 x bigger%s" % (name, " (%s)" % note if note else ""))
    hgt = os.path.join(base, "map_heights.hgt")
    say("map_heights.hgt...")
    if os.path.isfile(hgt) and heights_data and not hgt_usable(hgt, hpath):
        from .terrain import max_land_height, min_sea_height    # empty or cut: made again from the new picture
        top, low = max_land_height(mod, campaign) * vertical, min_sea_height(mod, campaign) * vertical
        plan.binary(hgt, hgt_from_picture(heights_data, top, low))
        plan.note(None, "map_heights.hgt was empty or did not fit map_heights.tga - made again from the new "
                        "map_heights.tga (the game reads it instead of the picture)")
        warn.append("map_heights.hgt was empty or did not fit map_heights.tga: made again from the new heights")
    elif os.path.isfile(hgt) and hpath and os.path.isfile(hpath):
        plan.binary(hgt, hgt_scaled(hgt, hpath, hmask, vertical, natural=True, rivers=rivers,
                                    towns=info.get("towns", ())))
        plan.note(None, "map_heights.hgt made 3 x bigger%s (the game reads it instead of the picture and never "
                        "makes it again)" % (", the heights x %g" % vertical if vertical != 1 else ""))
    for name, kind in CAMPAIGN_PICTURES.items():
        p = os.path.join(camp, name)
        if os.path.isfile(p):
            data, _ = scaled(p, kind)
            plan.binary(p, data)
            plan.note(None, "%s made 3 x bigger" % name)
    t = os.path.join(base, "descr_terrain.txt")
    if os.path.isfile(t):
        f = plan.edit(t)
        if vertical != 1:
            plan.note(f, "the hills, mountains and sea floor x %g (max_land_height, min_sea_height): the land is 3 x "
                         "wider, so the slopes stay as steep as they were" % vertical)
        if _dimensions(f, vertical) == 0:
            warn.append("descr_terrain.txt: no width / height line found - check its dimensions by hand")
    f = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
    n = move_coordinates(f, (RE_CHAR_XY, RE_RESOURCE, RE_FORT))
    plan.note(f, "%d character / resource / fort / wonder place(s) moved to the middle of their 3 x 3 block" % n)
    ev = os.path.join(camp, "descr_events.txt")
    if os.path.isfile(ev):
        f = plan.edit(ev)
        n = move_coordinates(f, (RE_POSITION,))
        if n:
            plan.note(f, "%d event position(s) moved" % n)
    for name in ("map.rwm",):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            plan.delete(p, "the game builds it again from the bigger pictures")
    for p in script_files(mod, campaign):
        f = plan.edit(p)
        n, check = move_script(f)
        if n:
            plan.note(f, "%d place(s) on the campaign map moved (spawned characters, camera, reveal, move, forts, "
                         "resources, 'near a tile' and 'in a rectangle' conditions; battle positions left as they are)"
                         % n)
        if check:
            warn.append("%s: line(s) %s hold numbers that may be map tiles the editor does not know - check them by "
                        "hand (a tile x, y becomes 3x+1, 3y+1); a place on water or off the map can crash the game"
                        % (os.path.basename(p), ", ".join(str(k) for k in check[:12])
                           + (" ..." if len(check) > 12 else "")))
    # trigger files serve every campaign of the mod: moved only when the mod has this one campaign
    one = mod.campaigns() == [campaign]
    for key in ("traits", "ancillaries"):
        p = mod.file(key)
        if not p:
            continue
        with open(p, encoding="latin-1") as fh:
            hits = sum(1 for l in fh if RE_SCRIPT_CMD.search(l.split(";")[0]))
        if not hits:
            continue
        if one:
            f = plan.edit(p)
            n, _ = move_script(f)
            plan.note(f, "%d 'near a tile' / 'in a rectangle' condition(s) moved" % n)
        else:
            warn.append("%s: %d condition(s) name map tiles - not moved, the file serves the mod's other campaigns "
                        "too (a tile x, y becomes 3x+1, 3y+1 on this campaign's map)" % (os.path.basename(p), hits))
    for sub, hits in code_with_tiles(os.path.dirname(os.path.abspath(mod.data))):
        warn.append("%s: %s - Lua / Squirrel scripts are not changed; if they place things on the map by x, y, "
                    "make those 3x+1, 3y+1 by hand" % (sub, ", ".join(hits[:8])))
    from .limits import HARD_LIMITS, game_kind, lifted
    from .tga import read_tga
    img = read_tga(regions_path)
    size = max(img.width, img.height) * FACTOR
    top = HARD_LIMITS[game_kind(mod)]["map_size"]
    if size > top and not lifted(mod, "map_size"):
        warn.append("The bigger map is %d tiles wide - the original exe stops at %d: run it with %s (REX / M2EX "
                    "lift the map size limit)" % (size, top, "REX" if game_kind(mod) == "rome" else "M2EX"))
    warn.append("A big map is new ground for the game's AI (pathfinding, slower turns) - test it in the game.")
    for w in warn:
        plan.warn(None, w)
    return warn
