"""Make a campaign map bigger: every tile becomes a 3 x 3 block (alpha). Both games.

Why 3: an odd factor keeps each town, port, army and resource in the MIDDLE of its block - tile (x, y) becomes
(3x + 1, 3y + 1) - so nothing has to be placed again by hand. The room in between is for new regions and factions.

What it writes (Preview lists it; one backup, Restore gives everything back):
- world/maps/base pictures, scaled with no blending (colours stay exact):
    W x H         map_regions (a town / port pixel only in the middle of its block, the rest its region / the sea),
                  map_features (rivers redrawn as 1-pixel lines through the middles - a 2-pixel river crashes the
                  game; fords, sources, cliffs, volcanoes, land bridges on the middle pixel), map_trade_routes
    2W+1 x 2H+1   map_ground_types, map_climates, map_fog (corner points: new j -> old round(j / 3));
                  map_heights SMOOTH (each new point blends the old ones round it; land and sea apart, so the
                  coast stays where the regions have it)
    2W x 2H       map_roughness (smooth)
  and the campaign's disasters.tga, radar_map1 / radar_map2 (when present);
- descr_terrain.txt: the dimensions (width / height x 3);
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


def smooth_scaled(path, kind, sea=False):
    """A height-like picture made bigger SMOOTHLY (no steps): each new point blends the 4 old ones round it.
    With sea=True (map_heights: land is grey, its level; the sea is blue, its depth) land and sea are blended
    apart - a point takes the kind of the old point nearest to it, so the coast stays where it was (it must match
    the regions and the ground), and only points of that kind are blended."""
    data, w, h, step, top_down, raw = _read(path)
    xs, ys = _weights(kind, w), _weights(kind, h)
    W, H = len(xs), len(ys)
    row = w * step
    # per old pixel: (is sea, value)
    def cell(x, y):
        o = y * row + x * step
        b, g, r = raw[o], raw[o + 1], raw[o + 2]
        if sea and r == 0 and g == 0 and b > 0:
            return True, b
        return False, r
    cells = [[cell(x, y) for x in range(w)] for y in range(h)]
    alpha = b"\xff" if step == 4 else b""
    out = bytearray()
    for (ya, yb, fy) in ys:
        ra, rb = cells[ya], cells[yb]
        near_row = ra if fy < 0.5 else rb
        for (xa, xb, fx) in xs:
            pts = ((ra[xa], (1 - fx) * (1 - fy)), (ra[xb], fx * (1 - fy)), (rb[xa], (1 - fx) * fy), (rb[xb], fx * fy))
            want = (near_row[xa] if fx < 0.5 else near_row[xb])[0]
            tot = val = 0.0
            for (s, v), wt in pts:
                if s == want:
                    tot += wt
                    val += v * wt
            v = int(val / tot + 0.5) if tot else 0
            if want:
                out += bytes((v, 0, 0)) + alpha              # B G R: blue = the depth
            else:
                out += bytes((v, v, v)) + alpha
    if top_down:
        pass                                     # rows were read and written in the same storage order
    return _write(data, W, H, step, out)


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


def regions_scaled(path, region_colours):
    """map_regions x3: each block its tile's colour; a town / port only on the middle pixel, the rest of its block
    the region round it (a town) or the sea (a port)."""
    data, w, h, step, top_down, at = _pixels(path)
    big, _ = scaled(path, "tiles")
    W, H = w * FACTOR, h * FACTOR
    raw = bytearray(big[18 + data[0]:])
    regions = set(region_colours)
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
            fill = max(set(pick), key=pick.count) if pick else c
            for dx in range(FACTOR):
                for dy in range(FACTOR):
                    _put(raw, W, H, step, top_down, FACTOR * x + dx, FACTOR * y + dy, fill)
            cx, cy = new_xy(x, y)
            if c == PORT:          # a port must touch its region's land: the block's pixel on the shore side
                cx, cy = port_spot(at, w, h, x, y, regions)
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


def features_scaled(path):
    """map_features x3: black, rivers drawn as 1-pixel lines from block middle to block middle (an L where two
    river tiles touch only at a corner), every other feature on its block's middle pixel."""
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

    def kind(c):
        return "river" if c in RIVERY else ("cliff" if c == CLIFF else None)

    for (x, y), c in lines.items():
        k = kind(c)
        if not k:
            continue
        cx, cy = new_xy(x, y)
        paint = river if k == "river" else CLIFF
        for dx, dy in ((1, 0), (0, 1)):                       # each straight link once
            o = lines.get((x + dx, y + dy))
            if o is not None and kind(o) == k:
                for s in range(1, FACTOR):
                    _put(raw, W, H, step, top_down, cx + dx * s, cy + dy * s, paint)
        for dx, dy in ((1, 1), (1, -1)):                      # corner links with no straight path between
            o = lines.get((x + dx, y + dy))
            if o is None or kind(o) != k:
                continue
            if kind(lines.get((x + dx, y), (0, 0, 0))) == k or kind(lines.get((x, y + dy), (0, 0, 0))) == k:
                continue
            for s in range(1, FACTOR + 1):                    # across, then up / down
                _put(raw, W, H, step, top_down, cx + s, cy, paint)
            for s in range(1, FACTOR):
                _put(raw, W, H, step, top_down, cx + FACTOR, cy + dy * s, paint)
    for (x, y), c in lines.items():                           # every feature's own colour on its middle
        _put(raw, W, H, step, top_down, *new_xy(x, y), c)
    return _write(data, W, H, step, raw)


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


def _dimensions(f):
    """descr_terrain.txt: width / height x 3."""
    n = 0
    for i in range(len(f.raw)):
        t = f.text(i)
        m = re.match(r"^(\s*(?:width|height)\s+)(\d+)(.*)$", t)
        if m:
            f.raw[i] = f.make(m.group(1) + str(int(m.group(2)) * FACTOR) + m.group(3))
            n += 1
    return n


def plan_upscale(plan, campaign):
    """Every file of the map made 3 x bigger, in the plan (nothing written until Apply). Returns the warnings."""
    mod = plan.mod
    warn = []
    regions_path = mod.campaign_file(campaign, "map_regions.tga")
    base = os.path.dirname(regions_path)
    camp = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt"))
    colours = [v["colour"] for v in mod.regions(campaign).values()]
    w0 = h0 = None
    for name, kind in BASE_PICTURES.items():
        p = os.path.join(base, name)
        if not os.path.isfile(p):
            continue
        if name == "map_regions.tga":
            data = regions_scaled(p, colours)
        elif name == "map_heights.tga":
            data = smooth_scaled(p, kind, sea=True)          # the relief smooth, no steps
        elif name == "map_roughness.tga":
            data = smooth_scaled(p, kind)
        elif name == "map_features.tga":
            data = features_scaled(p)
        else:
            data, _ = scaled(p, kind)
        plan.binary(p, data)
        plan.note(None, "%s made 3 x bigger" % name)
    for name, kind in CAMPAIGN_PICTURES.items():
        p = os.path.join(camp, name)
        if os.path.isfile(p):
            data, _ = scaled(p, kind)
            plan.binary(p, data)
            plan.note(None, "%s made 3 x bigger" % name)
    t = os.path.join(base, "descr_terrain.txt")
    if os.path.isfile(t):
        f = plan.edit(t)
        if _dimensions(f) == 0:
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
