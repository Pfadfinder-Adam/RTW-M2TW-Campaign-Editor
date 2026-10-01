"""Make a campaign map bigger: every tile becomes a 3 x 3 block (alpha). Both games.

Why 3: an odd factor keeps each town, port, army and resource in the MIDDLE of its block - tile (x, y) becomes
(3x + 1, 3y + 1) - so nothing has to be placed again by hand. The room in between is for new regions and factions.

What it writes (Preview lists it; one backup, Restore gives everything back):
- world/maps/base pictures (colours stay exact - no new colours are made, except the heights' blended values):
    W x H         map_regions with a SMOOTH coast (a new point is land when most of the old land round it is: the
                  coast is a rounded line, not 3 x 3 squares; every block's middle keeps its old value, so towns,
                  armies and resources stay on their kind of ground; a town / port pixel only in the middle of its
                  block, a port on the shore side, touching its region's land),
                  map_features (rivers redrawn as 1-pixel lines through the middles - a 2-pixel river crashes the
                  game -, a corner link as a staircase, a river mouth carried on to the new coast; fords, sources,
                  cliffs, volcanoes, land bridges on the middle pixel), map_trade_routes
    2W+1 x 2H+1   map_heights SMOOTH (blended, land and sea apart along its own smooth coast) and
                  map_heights.hgt beside it at the new size (the game reads it instead of the picture and never
                  makes it again); map_ground_types (the sea ground under the heights' sea), map_climates, map_fog
    2W x 2H       map_roughness (smooth)
  and the campaign's disasters.tga, radar_map1 / radar_map2 (when present);
- descr_terrain.txt: the dimensions (width / height x 3) and - by default - the heights x 3 (max_land_height,
  min_sea_height): the land is 3 x wider, so its hills and mountains must be 3 x higher to keep their slopes;
- descr_strat.txt: every character's x / y, every resource, fort, watchtower and wonder (Rome's landmarks);
- descr_events.txt: every 'position x, y';
- map.rwm removed (the game builds it again).
Not moved (warned): coordinates inside campaign_script.txt and other scripts - they take many forms.
The faction-select pictures (map_<faction>.tga, map_FE) and water_surface keep their size."""

import os
import re
import struct

from .tga import _decode

FACTOR = 3
CITY, PORT = (0, 0, 0), (255, 255, 255)
RIVERY = {(0, 0, 255), (0, 255, 255), (255, 255, 255)}      # river, ford, source: one line
CLIFF = (255, 255, 0)
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


def _sources(kind, w, h):
    """For each new point (X, Y) - bottom-up, like the game's tiles -: the 4 old points round it with their
    weights. A block's middle (tiles) or an old corner point (corners) has its old point at weight 1, so it keeps
    its old value exactly: towns, armies, resources and the rest never change their kind of ground."""
    xs, ys = _weights(kind, w), _weights(kind, h)
    for Y, (ya, yb, fy) in enumerate(ys):
        for X, (xa, xb, fx) in enumerate(xs):
            yield X, Y, ((xa, ya, (1 - fx) * (1 - fy)), (xb, ya, fx * (1 - fy)),
                         (xa, yb, (1 - fx) * fy), (xb, yb, fx * fy))


def _share_mask(kind, w, h, flag):
    """A yes / no picture made bigger SMOOTHLY: a new point is yes when more than half of the 4 old points round it
    (by weight) are (a tie: its nearest old point decides). Blocks become rounded shapes - a coast drawn in
    3 x 3 squares becomes a smooth line - while every old middle keeps its value. -> {(X, Y): bool}, W, H."""
    out = {}
    W = H = 0
    for X, Y, pts in _sources(kind, w, h):
        share = sum(wt for x, y, wt in pts if flag(x, y))
        if abs(share - 0.5) < 1e-9:
            x, y, _ = max(pts, key=lambda p: p[2])
            yes = flag(x, y)
        else:
            yes = share > 0.5
        out[(X, Y)] = yes
        W, H = max(W, X + 1), max(H, Y + 1)
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


def smooth_scaled(path, kind, sea=False, mask=None):
    """A height-like picture made bigger SMOOTHLY (no steps): each new point blends the old ones round it. With
    sea=True (map_heights: land grey, its level; the sea blue, its depth) land and sea are blended apart: a point is
    sea or land by mask (heights_mask - a smooth coast), and only old points of that kind are blended."""
    data, w, h, step, top_down, at = _pixels(path)
    is_sea = _heights_sea(at) if sea else (lambda x, y: False)
    if sea and mask is None:
        mask = heights_mask(path)
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
            x, y, _ = _pick(pts, want, is_sea) or max(pts, key=lambda p: p[2])
            c = at(x, y)
            val, tot = (c[2] if is_sea(x, y) else c[0]), 1.0
        v = int(val / tot + 0.5)
        if want:
            _put(raw, W, H, step, top_down, X, Y, (0, 0, max(v, 1)))
        else:
            _put(raw, W, H, step, top_down, X, Y, (v, v, v))
    return _write(data, W, H, step, raw)


def hgt_scaled(hgt_path, tga_path, mask, vertical=1.0):
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
    W, H = len(_weights("corners", w)), len(_weights("corners", h))
    out = [0.0] * (W * H)
    for X, Y, pts in _sources("corners", w, h):
        want = mask[(X, Y)]
        tot = val = 0.0
        for x, y, wt in pts:
            if is_sea(x, y) == want:
                tot += wt
                val += vals[y * w + x] * wt
        if not tot:
            x, y, _ = _pick(pts, want, is_sea) or max(pts, key=lambda p: p[2])
            val, tot = vals[y * w + x], 1.0
        v = val / tot
        if want:
            v = min(v, 0.0)
        else:
            v = max(v, 0.0)
        out[Y * W + X] = v * vertical
    return struct.pack("<II", W, H) + struct.pack("<%df" % (W * H), *out)


def ground_scaled(path, mask, sea_colours):
    """map_ground_types made bigger: each point sea or land by the heights' smooth coast (mask), its colour the
    nearest old point's of that kind (the sea ground types lie under the heights' sea, as in the games' own maps);
    then the land's patches rounded (organic_patches) - forests and hills are not 3 x 3 squares."""
    data, w, h, step, top_down, at = _pixels(path)
    kind_of = lambda x, y: at(x, y) in sea_colours
    W, H = len(_weights("corners", w)), len(_weights("corners", h))
    raw = _blank(W, H, step, (0, 0, 0))
    for X, Y, pts in _sources("corners", w, h):
        want = mask.get((X, Y))
        p = _pick(pts, want, kind_of) if want is not None else None
        if p is None:
            p = max(pts, key=lambda q: q[2])
            c = at(p[0], p[1])
            if want is not None and (c in sea_colours) != want:       # no old point of that kind round it
                c = (196, 0, 0) if want else (0, 0, 0)               # shallow sea / wilderness
        else:
            c = at(p[0], p[1])
        _put(raw, W, H, step, top_down, X, Y, c)
    organic_patches(raw, W, H, step, keep=lambda c: c in sea_colours)
    return _write(data, W, H, step, raw)


def organic_patches(raw, W, H, step, keep=lambda c: False, rounds=2):
    """Round off the 3 x 3 blocks of a picture of kinds (ground types, climates) in place: every new point that is
    not an old one (X or Y not a multiple of 3) takes the kind most common in the 3 x 3 around it (Pillow's mode
    filter, twice), so a forest drawn in squares gets ragged, natural edges. The old points keep their kind
    exactly (the tiles' own ground - what may stand where does not change), and so does any point whose kind or
    new kind `keep` names (the sea ground: the coast stays where the heights put it)."""
    from PIL import Image, ImageFilter
    colours = {}
    idx = bytearray(W * H)
    for i in range(W * H):
        o = i * step
        c = (raw[o + 2], raw[o + 1], raw[o])
        k = colours.get(c)
        if k is None:
            if len(colours) >= 255:
                return                                   # not a picture of kinds: leave it
            k = colours[c] = len(colours)
        idx[i] = k
    pal = {v: k for k, v in colours.items()}
    im = Image.frombytes("L", (W, H), bytes(idx))
    for _ in range(rounds):
        im = im.filter(ImageFilter.ModeFilter(3))
    new = im.tobytes()
    kept = {k for c, k in colours.items() if keep(c)}
    for Y in range(H):
        for X in range(W):
            if X % FACTOR == 0 and Y % FACTOR == 0:
                continue
            i = Y * W + X
            a, b = idx[i], new[i]
            if a == b or a in kept or b in kept:
                continue
            c = pal[b]
            o = i * step
            raw[o:o + 3] = bytes((c[2], c[1], c[0]))


def climates_scaled(path):
    """map_climates made bigger with organic edges (each point its nearest old point's climate, then rounded)."""
    data, w, h, step, top_down, at = _pixels(path)
    W, H = len(_weights("corners", w)), len(_weights("corners", h))
    raw = _blank(W, H, step, (0, 0, 0))
    for X, Y, pts in _sources("corners", w, h):
        x, y, _ = max(pts, key=lambda q: q[2])
        _put(raw, W, H, step, top_down, X, Y, at(x, y))
    organic_patches(raw, W, H, step)
    return _write(data, W, H, step, raw)


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


def coast_mask(path, region_colours):
    """map_regions' land made bigger smoothly: {(X, Y): land}. A town counts as land, a port as sea (it sits in the
    sea next to its region)."""
    data, w, h, step, top_down, at = _pixels(path)
    regions = set(region_colours)
    return _share_mask("tiles", w, h, lambda x, y: at(x, y) in regions or at(x, y) == CITY)[0]


def regions_scaled(path, region_colours, mask=None, keep_land=()):
    """map_regions x3 with a SMOOTH coast (mask: coast_mask): a land pixel takes the region of the old land tile
    round it with the most weight, a sea pixel the sea's colour; keep_land (pixels under a river) stay land. A
    town / port only on its block's middle pixel (a port on the shore side of its block, touching its region's
    land)."""
    data, w, h, step, top_down, at = _pixels(path)
    regions = set(region_colours)
    if mask is None:
        mask = coast_mask(path, region_colours)
    keep_land = set(keep_land)
    fill = {}                                  # an old town / port tile: the colour round it
    for y in range(h):
        for x in range(w):
            c = at(x, y)
            if c not in (CITY, PORT):
                continue
            near = [at(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if (dx or dy) and 0 <= x + dx < w and 0 <= y + dy < h]
            if c == CITY:
                pick = [n for n in near if n in regions]
            else:
                pick = [n for n in near if n not in regions and n not in (CITY, PORT)]
            fill[(x, y)] = max(set(pick), key=pick.count) if pick else c
    colour = lambda x, y: fill.get((x, y), at(x, y))
    land_of = lambda x, y: colour(x, y) in regions
    W, H = w * FACTOR, h * FACTOR
    raw = _blank(W, H, step, (0, 0, 0))
    for X, Y, pts in _sources("tiles", w, h):
        land = mask[(X, Y)] or (X, Y) in keep_land
        p = _pick(pts, land, land_of) or max(pts, key=lambda q: q[2])
        if land and not land_of(p[0], p[1]):          # a river kept on land where the 4 round it are sea
            p = min(((x, y) for x in range(max(0, X // FACTOR - 1), min(w, X // FACTOR + 2))
                     for y in range(max(0, Y // FACTOR - 1), min(h, Y // FACTOR + 2)) if land_of(x, y)),
                    key=lambda q: abs(new_xy(*q)[0] - X) + abs(new_xy(*q)[1] - Y), default=(p[0], p[1])) + (0,)
        _put(raw, W, H, step, top_down, X, Y, colour(p[0], p[1]))
    for (x, y), c0 in fill.items():
        c = at(x, y)
        cx, cy = new_xy(x, y)
        if c == PORT:          # a port must touch its region's land: the block's pixel on the shore side
            cx, cy = port_spot(at, w, h, x, y, regions)
            dx, dy = cx - new_xy(x, y)[0], cy - new_xy(x, y)[1]
            lx, ly = cx + dx, cy + dy                   # the pixel beyond it, in the land block: kept land
            if 0 <= lx < W and 0 <= ly < H:
                r = (H - 1 - ly) if top_down else ly
                o = (r * W + lx) * step
                if (raw[o + 2], raw[o + 1], raw[o]) not in regions:
                    land = [at(x + dx, y + dy)] if at(x + dx, y + dy) in regions else [c0]
                    _put(raw, W, H, step, top_down, lx, ly, land[0])
        _put(raw, W, H, step, top_down, cx, cy, c)
    return _write(data, W, H, step, raw)


def port_spot(at, w, h, x, y, regions):
    """Where an old port tile's pixel goes in its 3 x 3 block: next to the land of the region it serves (a side
    first, else a corner), so it touches that land's block as it touched the tile before."""
    cx, cy = new_xy(x, y)
    land = {}
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        if 0 <= x + dx < w and 0 <= y + dy < h and at(x + dx, y + dy) in regions:
            land.setdefault(at(x + dx, y + dy), []).append((dx, dy))
    if not land:
        return cx, cy
    best = max(land, key=lambda k: len(land[k]))
    dx, dy = land[best][0]                     # sides come first in the order above
    return cx + dx, cy + dy


def features_scaled(path, land=None):
    """map_features x3: black, rivers drawn as 1-pixel lines from block middle to block middle - a corner link a
    staircase (one step across, one up, ...: always side by side, never a corner-only step the game stops a river
    at); a river that met the sea runs on to the new, smoother coast (land: coast_mask); every other feature on its
    block's middle pixel. -> (bytes, the river pixels)."""
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
        return "river" if c in RIVERY else ("cliff" if c == CLIFF else None)

    def paint(px, py, c):
        if 0 <= px < W and 0 <= py < H:
            _put(raw, W, H, step, top_down, px, py, c)
            if c == river:
                drawn.add((px, py))

    for (x, y), c in lines.items():
        k = kind(c)
        if not k:
            continue
        cx, cy = new_xy(x, y)
        colour = river if k == "river" else CLIFF
        for dx, dy in ((1, 0), (0, 1)):                       # each straight link once
            o = lines.get((x + dx, y + dy))
            if o is not None and kind(o) == k:
                for s in range(1, FACTOR):
                    paint(cx + dx * s, cy + dy * s, colour)
        for dx, dy in ((1, 1), (1, -1)):                      # corner links with no straight path between
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
    for (x, y), c in lines.items():                           # every feature's own colour on its middle
        paint(*new_xy(x, y), c)
    return _write(data, W, H, step, raw), drawn


# ---------------------------------------------------------------------------
RE_CHAR_XY = re.compile(r"(\bx\s+)(-?\d+)(\s*,\s*y\s+)(-?\d+)")
RE_RESOURCE = re.compile(r"^(\s*resource\s+[^,;]+,\s*)(-?\d+)(\s*,\s*)(-?\d+)")
RE_FORT = re.compile(r"^(\s*(?:fort|watchtower|landmark)\s+(?:[A-Za-z_]\w*\s+)?)(-?\d+)(\s*,?\s*)(-?\d+)")
RE_POSITION = re.compile(r"^(\s*position\s+)(-?\d+)(\s*,\s*)(-?\d+)")
RE_SCRIPT_XY = re.compile(r"\b\d+\s*,\s*\d+\b")


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
    say("the coast (map_regions)...")
    coast = coast_mask(regions_path, colours)              # the regions' land, made bigger with a smooth coast
    hpath = os.path.join(base, "map_heights.tga")
    say("the heights' coast...")
    hmask = heights_mask(hpath) if os.path.isfile(hpath) else None
    keep_land = ()
    feats = os.path.join(base, "map_features.tga")
    if os.path.isfile(feats):
        say("rivers and cliffs (map_features)...")
        data, rivers = features_scaled(feats, coast)
        plan.binary(feats, data)
        plan.note(None, "map_features.tga made 3 x bigger (rivers as staircases, mouths on the new coast)")
        keep_land = {p for p in rivers if not coast.get(p, True)}
    for name, kind in BASE_PICTURES.items():
        p = os.path.join(base, name)
        if not os.path.isfile(p) or name == "map_features.tga":
            continue
        say("%s..." % name)
        if name == "map_regions.tga":
            data = regions_scaled(p, colours, coast, keep_land)
            note = "with a smooth coast"
        elif name == "map_heights.tga":
            data = smooth_scaled(p, kind, sea=True, mask=hmask)       # the relief smooth, no steps
            note = "smooth, with a smooth coast"
        elif name == "map_ground_types.tga" and hmask is not None:
            data = ground_scaled(p, hmask, SEA)
            note = "the sea ground under the heights' new coast, the land's patches with natural edges"
        elif name == "map_climates.tga":
            data = climates_scaled(p)
            note = "with natural edges"
        elif name == "map_roughness.tga":
            data = smooth_scaled(p, kind)
            note = "smooth"
        else:
            data, _ = scaled(p, kind)
            note = ""
        plan.binary(p, data)
        plan.note(None, "%s made 3 x bigger%s" % (name, " (%s)" % note if note else ""))
    hgt = os.path.join(base, "map_heights.hgt")
    say("map_heights.hgt...")
    if os.path.isfile(hgt) and os.path.isfile(hpath):
        plan.binary(hgt, hgt_scaled(hgt, hpath, hmask, vertical))
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
    for script in ("campaign_script.txt",):
        p = os.path.join(camp, script)
        if os.path.isfile(p):
            with open(p, encoding="latin-1") as fh:
                hits = sum(1 for l in fh if RE_SCRIPT_XY.search(l.split(";")[0]))
            if hits:
                warn.append("%s: %d line(s) hold numbers like 'x, y' - coordinates in scripts are NOT moved "
                            "(multiply them by 3 and add 1 by hand); a coordinate on water or off the map crashes "
                            "the game" % (script, hits))
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
