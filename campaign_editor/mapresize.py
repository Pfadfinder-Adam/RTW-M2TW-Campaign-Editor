"""Grow or cut the campaign map at its edges (Map size...): rows / columns of tiles added at the left, right, top or
bottom - deep sea, as the map's own deepest water - or cut off. Both games.

Tile (x, y) - counted from the map's bottom left, as descr_strat.txt and map_regions.tga (read bottom-up) count
them - becomes (x + left, y + bottom); the pictures 2W+1 / 2W wide move by twice as many points. Every place the
x3 upscale moves is moved the same way (upscale's shared movers, given this shift instead): characters,
resources, forts / watchtowers / wonders in descr_strat.txt, events' positions, the campaign's scripts (tile
commands; distances, radii and rectangle sizes stay), trait / ancillary conditions when the mod has this one
campaign. descr_terrain.txt gets the new width / height, map_heights.hgt is moved with the picture, map.rwm goes.

A cut that would leave a town, a port, a character, a resource, a fort or an event's place off the map is refused
with the file and line of each (nothing is written)."""

import os
import re
import struct
from collections import deque

from . import upscale as U
from .tga import _decode, read_tga

STEP = {"tiles": 1, "corners": 2, "double": 2}     # how many points a tile is in each kind of picture


def deepest_sea(mod, campaign):
    """(x, y): the sea tile farthest from any land in map_regions (the colour the new edges are filled with comes
    from there in every picture); ValueError when the map has no sea."""
    img = read_tga(mod.campaign_file(campaign, "map_regions.tga"))
    w, h = img.width, img.height
    lands = {v["colour"] for v in mod.regions(campaign).values()} | {U.CITY, U.PORT}
    counts = {}
    for y in range(h):
        for x in range(w):
            c = img.get(x, y)
            if c not in lands:
                counts[c] = counts.get(c, 0) + 1
    if not counts:
        raise ValueError("the map has no sea - the new edge has nothing to be filled with")
    sea = max(counts, key=counts.get)
    dist = [-1] * (w * h)
    todo = deque()
    for y in range(h):
        for x in range(w):
            if img.get(x, y) != sea:
                dist[y * w + x] = 0
                todo.append((x, y))
    if not todo:                                    # all sea: the middle
        return w // 2, h // 2
    while todo:
        x, y = todo.popleft()
        d = dist[y * w + x] + 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and dist[ny * w + nx] < 0:
                dist[ny * w + nx] = d
                todo.append((nx, ny))
    i = max(range(w * h), key=lambda k: dist[k])
    return i % w, i // w


def shifted(data, kind, left, bottom, right, top, fill_tile, path="(picture)"):
    """A picture's bytes with `left` .. `top` tiles added (or cut, when negative) at its edges; new points take the
    value of fill_tile's point (deep sea)."""
    w, h, step, top_down, _, raw = _decode(data, path)
    k = STEP[kind]
    W, H = w + (left + right) * k, h + (bottom + top) * k
    if W < 1 or H < 1:
        raise ValueError("%s would have no tiles left" % os.path.basename(path))
    fx, fy = (fill_tile[0], fill_tile[1]) if kind == "tiles" else \
        (2 * fill_tile[0] + 1, 2 * fill_tile[1] + 1) if kind == "corners" else (2 * fill_tile[0], 2 * fill_tile[1])
    fx, fy = min(fx, w - 1), min(fy, h - 1)

    def row_of(y, height):                         # storage row of bottom-up row y
        return (height - 1 - y) if top_down else y
    o = (row_of(fy, h) * w + fx) * step
    fill = bytes(raw[o:o + step])
    out = bytearray(fill * (W * H))
    dx, dy = left * k, bottom * k
    for Y in range(H):
        y = Y - dy
        if not 0 <= y < h:
            continue
        x0, x1 = max(0, -dx), min(w, W - dx)          # the old columns that land inside
        if x0 >= x1:
            continue
        src = row_of(y, h) * w
        dst = row_of(Y, H) * W
        out[(dst + x0 + dx) * step:(dst + x1 + dx) * step] = raw[(src + x0) * step:(src + x1) * step]
    return U._write(data, W, H, step, out)


def hgt_shifted(raw, left, bottom, right, top, fill_tile):
    """map_heights.hgt (uint32 w, h, then w * h float32 bottom-up) moved as the 2W+1 picture."""
    w, h = struct.unpack_from("<II", raw)
    vals = struct.unpack_from("<%df" % (w * h), raw, 8)
    fx, fy = min(2 * fill_tile[0] + 1, w - 1), min(2 * fill_tile[1] + 1, h - 1)
    fill = vals[fy * w + fx]
    W, H = w + 2 * (left + right), h + 2 * (bottom + top)
    out = [fill] * (W * H)
    dx, dy = 2 * left, 2 * bottom
    for Y in range(H):
        y = Y - dy
        if 0 <= y < h:
            for X in range(max(0, dx), min(W, w + dx)):
                out[Y * W + X] = vals[y * w + X - dx]
    return struct.pack("<II", W, H) + struct.pack("<%df" % (W * H), *out)


def _mover(left, bottom):
    """(xy(x, y), values(kind, nums)) moving tiles by the shift: distances, radii and sizes stay."""
    def xy(x, y):
        return x + left, y + bottom

    def values(kind, nums):
        if kind == "xy":
            return list(xy(nums[0], nums[1]))
        if kind == "xyr":
            return list(xy(nums[0], nums[1])) + [nums[2]]
        if kind == "dxy":
            return [nums[0]] + list(xy(nums[1], nums[2]))
        if kind == "area":
            return list(xy(nums[0], nums[1])) + list(xy(nums[2], nums[3]))
        return list(xy(nums[0], nums[1])) + list(nums[2:4])          # rect: a corner, then width / height
    return xy, values


def _texts(path):
    with open(path, encoding="latin-1") as fh:
        return fh.read().splitlines()


def off_map(mod, campaign, left, bottom, right, top):
    """What a cut would leave off the map: ['file line N: what (x, y)']. Towns and ports from map_regions."""
    img = read_tga(mod.campaign_file(campaign, "map_regions.tga"))
    W, H = img.width + left + right, img.height + bottom + top
    xy, values = _mover(left, bottom)
    out = []

    def gone(p):
        return not (0 <= p[0] < W and 0 <= p[1] < H)
    for region, t in sorted(mod.city_tiles(campaign).items()):
        if gone(xy(*t)):
            out.append("map_regions.tga: the town of %s (%d, %d)" % (region, t[0], t[1]))
    from .mapedit import ports
    for region, t in sorted(ports(mod, campaign).items()):
        if gone(xy(*t)):
            out.append("map_regions.tga: the port of %s (%d, %d)" % (region, t[0], t[1]))
    camp = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt"))
    files = [(mod.campaign_file(campaign, "descr_strat.txt"), (U.RE_CHAR_XY, U.RE_RESOURCE, U.RE_FORT))]
    ev = os.path.join(camp, "descr_events.txt")
    if os.path.isfile(ev):
        files.append((ev, (U.RE_POSITION,)))
    for path, patterns in files:
        for i, text in enumerate(_texts(path)):
            seen = []
            U._move_line(text, patterns, lambda x, y: seen.append((x, y)) or xy(x, y))
            for p in seen:
                if gone(xy(*p)):
                    out.append("%s line %d: %s (%d, %d)" % (os.path.basename(path), i + 1,
                                                             text.split(";")[0].strip()[:60], p[0], p[1]))
    for path in U.script_files(mod, campaign):
        for i, text in enumerate(_texts(path)):
            code = text.split(";")[0]
            new = _tiles_in(text, values) + [xy(int(m.group(2)), int(m.group(4))) for m in U.RE_CHAR_XY.finditer(code)]
            for p in new:
                if gone(p):
                    out.append("%s line %d: %s (%d, %d)" % (os.path.basename(path), i + 1, code.strip()[:60],
                                                             p[0] - left, p[1] - bottom))
    return out


def _tiles_in(text, values):
    """The new tiles of a script line's tile commands (the shifted x, y pairs the commands take)."""
    out = []
    code = text.partition(";")[0]
    cmds = list(U.RE_SCRIPT_CMD.finditer(code))
    for k, m in enumerate(cmds):
        kind = U.SCRIPT_TILES[next(c for c in U.SCRIPT_TILES if c.lower() == m.group(1).lower())]
        end = cmds[k + 1].start() if k + 1 < len(cmds) else len(code)
        stop = U.RE_SCRIPT_STOP.search(code, m.end(), end)
        if stop:
            end = stop.start()
        ints = [int(i.group()) for i in list(U.RE_INT.finditer(code, m.end(), end))[:U.NEEDS[kind]]]
        if len(ints) < U.NEEDS[kind]:
            continue
        new = values(kind, ints)
        pairs = {"xy": [(0, 1)], "xyr": [(0, 1)], "dxy": [(1, 2)], "area": [(0, 1), (2, 3)], "rect": [(0, 1)]}[kind]
        out += [(new[a], new[b]) for a, b in pairs]
    return out


def plan_resize(plan, campaign, left=0, bottom=0, right=0, top=0):
    """Every file of the map grown (positive) or cut (negative) by that many tiles at each edge, in the plan.
    Returns the warnings; ValueError (with every place named) when a cut would leave something off the map."""
    mod = plan.mod
    if not any((left, bottom, right, top)):
        raise ValueError("no tiles to add or cut")
    gone = off_map(mod, campaign, left, bottom, right, top)
    if gone:
        raise ValueError("the cut would leave %d place(s) off the map - move them first:\n%s" % (
            len(gone), "\n".join(gone[:30]) + ("\n... and %d more" % (len(gone) - 30) if len(gone) > 30 else "")))
    regions_path = mod.campaign_file(campaign, "map_regions.tga")
    img = read_tga(regions_path)
    W, H = img.width + left + right, img.height + bottom + top
    fill = deepest_sea(mod, campaign)
    xy, values = _mover(left, bottom)
    words = _words(left, bottom, right, top)
    base = os.path.dirname(regions_path)
    camp = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt"))
    warn = []
    for folder, pictures in ((base, U.BASE_PICTURES), (camp, U.CAMPAIGN_PICTURES)):
        for name, kind in pictures.items():
            p = os.path.join(folder, name)
            if not os.path.isfile(p):
                continue
            with open(p, "rb") as fh:
                data = fh.read()
            pw, ph = struct.unpack_from("<HH", data, 12)
            want = {"tiles": (img.width, img.height), "corners": (2 * img.width + 1, 2 * img.height + 1),
                    "double": (2 * img.width, 2 * img.height)}[kind]
            if (pw, ph) != want:                    # a picture of its own size (Medieval II's radar maps, a
                plan.note(None, "%s left as it is (%d x %d - not tied to the map's tiles)" % (name, pw, ph))
                continue                            # disasters.tga left from Rome) is not the map's: left alone
            plan.binary(p, shifted(data, kind, left, bottom, right, top, fill, p))
            plan.note(None, "%s %s (new tiles: the map's deep sea)" % (name, words))
    hgt = os.path.join(base, "map_heights.hgt")
    hpath = os.path.join(base, "map_heights.tga")
    if os.path.isfile(hgt) and os.path.isfile(hpath) and U.hgt_usable(hgt, hpath):
        with open(hgt, "rb") as fh:
            plan.binary(hgt, hgt_shifted(fh.read(), left, bottom, right, top, fill))
        plan.note(None, "map_heights.hgt %s" % words)
    elif os.path.isfile(hgt):
        warn.append("map_heights.hgt was empty or did not fit map_heights.tga - left as it is")
    t = os.path.join(base, "descr_terrain.txt")
    if os.path.isfile(t):
        f = plan.edit(t)
        n = 0
        for i in range(len(f.raw)):
            m = re.match(r"^(\s*)(width|height)(\s+)(\d+)(.*)$", f.text(i))
            if m:
                f.raw[i] = f.make(m.group(1) + m.group(2) + m.group(3) + str(W if m.group(2) == "width" else H)
                                  + m.group(5))
                n += 1
        if n:
            plan.note(f, "the map's size: %d x %d tiles" % (W, H))
        else:
            warn.append("descr_terrain.txt: no width / height line found - check its dimensions by hand")
    shift = (left, bottom) != (0, 0)
    if shift:
        f = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
        n = U.move_coordinates(f, (U.RE_CHAR_XY, U.RE_RESOURCE, U.RE_FORT), xy)
        plan.note(f, "%d character / resource / fort / wonder place(s) moved by %d, %d" % (n, left, bottom))
        ev = os.path.join(camp, "descr_events.txt")
        if os.path.isfile(ev):
            f = plan.edit(ev)
            n = U.move_coordinates(f, (U.RE_POSITION,), xy)
            if n:
                plan.note(f, "%d event position(s) moved" % n)
        for p in U.script_files(mod, campaign):
            f = plan.edit(p)
            n, check = U.move_script(f, values, xy)
            if n:
                plan.note(f, "%d place(s) on the campaign map moved by %d, %d (distances and sizes stay)"
                          % (n, left, bottom))
            if check:
                warn.append("%s: line(s) %s hold numbers that may be map tiles the editor does not know - check them "
                            "by hand (a tile x, y becomes x%+d, y%+d)" % (os.path.basename(p), ", ".join(
                                str(k) for k in check[:12]) + (" ..." if len(check) > 12 else ""), left, bottom))
        one = mod.campaigns() == [campaign]
        for key in ("traits", "ancillaries"):
            p = mod.file(key)
            if not p:
                continue
            hits = sum(1 for line in _texts(p) if U.RE_SCRIPT_CMD.search(line.split(";")[0]))
            if not hits:
                continue
            if one:
                f = plan.edit(p)
                n, _ = U.move_script(f, values, xy)
                plan.note(f, "%d 'near a tile' / 'in a rectangle' condition(s) moved" % n)
            else:
                warn.append("%s: %d condition(s) name map tiles - not moved, the file serves the mod's other "
                            "campaigns too (a tile x, y becomes x%+d, y%+d on this campaign's map)"
                            % (os.path.basename(p), hits, left, bottom))
        for sub, hits in U.code_with_tiles(os.path.dirname(os.path.abspath(mod.data))):
            warn.append("%s: %s - Lua / Squirrel scripts are not changed; if they place things on the map by x, y, "
                        "move those by %d, %d by hand" % (sub, ", ".join(hits[:8]), left, bottom))
    p = os.path.join(base, "map.rwm")
    if os.path.isfile(p):
        plan.delete(p, "the game builds it again from the new pictures")
    from .limits import HARD_LIMITS, game_kind, lifted
    most = HARD_LIMITS[game_kind(mod)]["map_size"]
    if max(W, H) > most and not lifted(mod, "map_size"):
        warn.append("The map is %d tiles wide now - the original exe stops at %d: run it with %s"
                    % (max(W, H), most, "REX" if game_kind(mod) == "rome" else "M2EX"))
    for w_ in warn:
        plan.warn(None, w_)
    return warn


def _words(left, bottom, right, top):
    parts = []
    for n, side in ((left, "left"), (right, "right"), (top, "top"), (bottom, "bottom")):
        if n:
            parts.append("%s %d at the %s" % ("grown by" if n > 0 else "cut by", abs(n), side))
    return ", ".join(parts)
