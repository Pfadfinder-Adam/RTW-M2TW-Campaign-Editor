"""The terrain of the campaign map: what each tile is (map_ground_types.tga) and what runs
across it (map_features.tga: rivers, fords, cliffs...), painted and written back.

map_ground_types.tga is 2 x the map + 1: tile (x, y) is the 3 x 3 block around pixel
(2x + 1, 2y + 1) - its middle is what the game (and the tool) takes as the tile's ground.
map_features.tga is one pixel per tile. The game builds its 3D map (map.rwm) from these
pictures; deleting map.rwm makes it build it again on the next start, as for moved towns.

Checked colours (both games' vanilla files): see GROUND and FEATURES. Land and sea are not
swapped here - the coast is also map_regions.tga, the heights and the regions, a step of
its own. Nothing a town, a port or a character stands on is made a tile the game refuses
for them (the rules of moddata.land_problem)."""

import os
from collections import Counter


# map_ground_types.tga colours (Rome and Medieval II; the impassable ones Medieval II's and the engines', the black one
# only the engines' - REX / M2EX's ground type impassable_shrouded)
GROUND = {
    (101, 124, 0): "low fertility", (96, 160, 64): "medium fertility", (0, 128, 0): "high fertility",
    (0, 0, 0): "wilderness", (0, 64, 0): "dense forest", (0, 128, 128): "sparse forest",
    (128, 128, 64): "hills", (98, 65, 65): "mountains", (196, 128, 128): "high mountains",
    (0, 255, 128): "swamp", (255, 255, 255): "beach", (64, 0, 0): "ocean",
    (128, 0, 0): "deep sea", (196, 0, 0): "shallow sea",
    (64, 64, 64): "impassable land", (128, 128, 128): "impassable sea",
    (32, 32, 32): "impassable land, always black",
}
SEA = {(64, 0, 0), (128, 0, 0), (196, 0, 0), (128, 128, 128)}
# the beach (white) is LAND: both games' own maps lay it on land tiles along the coast (map_regions: M2TW 503 of 503,
# Rome 580 of 580; touching the sea by a side 482 / 439), every beach point on land heights (measured 2026-10-09) -
# painted with the land's brushes (it was a sea brush: its sand lay on the water)
LAND_BRUSHES = [(101, 124, 0), (96, 160, 64), (0, 128, 0), (0, 0, 0), (0, 128, 128), (0, 64, 0), (128, 128, 64),
                (98, 65, 65), (196, 128, 128), (0, 255, 128), (255, 255, 255)]
SEA_BRUSHES = [(196, 0, 0), (64, 0, 0), (128, 0, 0)]

# map_features.tga colours (one pixel per tile; black = nothing)
FEATURES = {
    (0, 0, 0): "nothing", (0, 0, 255): "river", (0, 255, 255): "ford (river crossing)",
    (255, 255, 255): "river source", (255, 255, 0): "cliff", (255, 0, 0): "volcano",
    (0, 255, 0): "land bridge (Medieval II)",
}
FEATURE_BRUSHES = [(0, 0, 255), (0, 255, 255), (255, 255, 255), (255, 255, 0), (255, 0, 0), (0, 0, 0)]
RIVERY = {(0, 0, 255), (0, 255, 255), (255, 255, 255)}
VOLCANO, LAND_BRIDGE = (255, 0, 0), (0, 255, 0)


IMPASSABLE_LAND, IMPASSABLE_SEA = (64, 64, 64), (128, 128, 128)
SHROUDED = (32, 32, 32)          # impassable_shrouded: no army walks there and it is never seen (black) - REX / M2EX
BEACH = (255, 255, 255)


def ground_brushes(game, engine=None):
    """(land, sea) ground colours the Terrain editor paints: impassable land / sea (no army walks or sails there)
    on Medieval II (its vanilla map is full of them) and on Rome only with REX (REX names the ground types
    IMPASSABLE_LAND / IMPASSABLE_SEA, the original RomeTW.exe does not - not tried in the game yet); the black
    impassable land (impassable_shrouded - a wasteland's land hidden for good) with REX or M2EX, both games (REX's
    wasteland_regions.md)."""
    engine = (engine or "").lower()
    extra = game == "medieval2" or engine.startswith("rex")
    black = engine.startswith(("rex", "m2ex"))
    return (LAND_BRUSHES + ([IMPASSABLE_LAND] if extra else []) + ([SHROUDED] if black else []),
            SEA_BRUSHES + ([IMPASSABLE_SEA] if extra else []))


def feature_brushes(game):
    """The marks the Terrain editor paints for game ('rome' | 'medieval2'): land bridges only on Medieval II
    (vanilla Rome's map has none, whether its engine reads them is not known)."""
    return FEATURE_BRUSHES[:-1] + ([LAND_BRIDGE] if game == "medieval2" else []) + [(0, 0, 0)]


def bridge_warnings(features):
    """[(x, y, n, why)] for land bridges (green, Medieval II) the game may not take: vanilla's 9 are straight
    strips of 3 tiles across a strait (land - sea - land), so a group that is not one straight row or column, or
    a single tile, is named."""
    green = {t for t, c in features.items() if c == LAND_BRIDGE}
    seen, out = set(), []
    for t0 in sorted(green, key=lambda t: (t[1], t[0])):
        if t0 in seen:
            continue
        group, todo = [], [t0]
        seen.add(t0)
        while todo:
            x, y = todo.pop()
            group.append((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1), (x - 1, y - 1),
                      (x + 1, y - 1), (x - 1, y + 1)):
                if n in green and n not in seen:
                    seen.add(n)
                    todo.append(n)
        xs, ys = {x for x, _ in group}, {y for _, y in group}
        if len(group) < 2:
            out.append((t0[0], t0[1], 1, "a single tile - a land bridge crosses a strait: land, sea, land in a "
                                         "straight line (3 tiles in vanilla)"))
        elif len(xs) > 1 and len(ys) > 1:
            out.append((t0[0], t0[1], len(group), "not one straight row or column - vanilla's land bridges are "
                                                  "straight strips (3 tiles) across a strait"))
        elif max(len(xs), len(ys)) != len(group):
            out.append((t0[0], t0[1], len(group), "has a gap - a land bridge is one unbroken strip"))
    return out

# what no town, port or character may stand on (moddata.BLOCKED_GROUND, the user's checks in game)
from .moddata import BLOCKED_GROUND                                       # noqa: E402


def paint_problem(cmap, what, xy, colour, standing):
    """None, or why tile xy cannot take colour. what: 'ground' | 'features' | 'climate'; cmap: the
    CampaignMap as painted so far; standing: tiles with a town, port or character."""
    x, y = xy
    if not (0 <= x < cmap.w and 0 <= y < cmap.h):
        return "off the map"
    sea = cmap.is_sea(x, y)
    if what == "climate":                             # the sea too (FREEDOM FIRST - the game reads every point)
        return None
    if what == "ground":
        if (colour in SEA) != sea:                    # the beach is a land ground (on the land tiles along the coast)
            return "land and sea are not swapped with the ground brush - use 'Land and sea' (it changes the regions and heights too)"
        if xy in standing and colour in BLOCKED_GROUND:
            return "a town, port or character stands there - the game refuses %s under them" % GROUND.get(colour)
        return None
    # rivers, fords and sources may run onto the sea: the games' own maps end a river in the water at a few mouths
    # (estuaries - M2TW 15 river pixels on sea tiles, Rome 7; one M2TW source); cliffs and volcanoes stay on land
    if sea and colour not in ((0, 0, 0), LAND_BRIDGE) and colour not in RIVERY:
        return "cliffs and volcanoes are on land (rivers, fords and sources may run onto the sea, a land bridge may " \
               "cross it)"
    if xy in standing and colour not in ((0, 0, 0), LAND_BRIDGE):
        return "a town, port or character stands there - the game refuses them on a river, ford, cliff or volcano"
    return None


def river_warnings(features, w, h, is_sea=None):
    """[(x, y, n)] for river pieces the game will not draw: the game follows a river from where it joins
    the sea, the map's edge, a river source or another river, edge to edge - a step where two river tiles
    touch only by a corner stops it, and everything past it is left out (the user's river west of the Nile,
    2026-09-29). A piece = river, ford and source tiles joined by edges; one joined to none of those is
    named by its tile nearest the top left and its size. features: tile -> colour, the whole map as painted."""
    rivery = {t for t, c in features.items() if c in RIVERY}
    seen, out = set(), []
    for t0 in sorted(rivery, key=lambda t: (t[1], t[0])):
        if t0 in seen:
            continue
        piece, stack = [], [t0]
        seen.add(t0)
        while stack:
            x, y = stack.pop()
            piece.append((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in rivery and n not in seen:
                    seen.add(n)
                    stack.append(n)
        joined = False
        for x, y in piece:
            if features.get((x, y)) == (255, 255, 255) or x in (0, w - 1) or y in (0, h - 1):
                joined = True
                break
            if is_sea and any(0 <= nx < w and 0 <= ny < h and is_sea(nx, ny)
                              for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))):
                joined = True
                break
        if not joined:
            x, y = min(piece, key=lambda t: (t[1], t[0]))
            out.append((x, y, len(piece)))
    return out


def river_shapes(features, painted=None):
    """[('square', x, y) | ('loop', x, y, n)] - river shapes the modders' guides say the game cannot take
    (heavengames "Changing Terrain Features in RTW"): a 2 x 2 block of river tiles, and a river that
    rejoins itself around land. Vanilla RTW / M2TW have neither; HLR has 6 loops and runs, so a loop is
    a softer warning. painted: only shapes touching these tiles (what this edit makes); None = all.
    A loop = a piece whose cycles are more than its 2 x 2 blocks (V - 1 edges make a tree)."""
    rivery = {t for t, c in features.items() if c in RIVERY}
    out, seen = [], set()
    touch = set(painted) if painted is not None else None

    def near(tiles):
        return touch is None or any(t in touch for t in tiles)

    for x, y in sorted(rivery, key=lambda t: (t[1], t[0])):
        block = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
        if all(t in rivery for t in block) and near(block):
            out.append(("square", x, y))
    for t0 in sorted(rivery, key=lambda t: (t[1], t[0])):
        if t0 in seen:
            continue
        piece, stack, edges, squares = [], [t0], 0, 0
        seen.add(t0)
        while stack:
            x, y = stack.pop()
            piece.append((x, y))
            edges += ((x + 1, y) in rivery) + ((x, y + 1) in rivery)
            squares += all(t in rivery for t in ((x + 1, y), (x, y + 1), (x + 1, y + 1)))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in rivery and n not in seen:
                    seen.add(n)
                    stack.append(n)
        if edges - len(piece) + 1 - squares > 0 and near(piece):
            x, y = min(piece, key=lambda t: (t[1], t[0]))
            out.append(("loop", x, y, len(piece)))
    return out


def river_path(a, b):
    """The tiles from a (left out) to b that keep a river joined by edges: a diagonal or a longer jump
    of the brush becomes a staircase of edge steps, the corner tile before the diagonal one."""
    (x, y), out = a, []
    while (x, y) != tuple(b):
        if x != b[0] and (y == b[1] or len(out) % 2 == 0):
            x += 1 if b[0] > x else -1
        else:
            y += 1 if b[1] > y else -1
        out.append((x, y))
    return out


def climates(mod):
    """[(name, colour, heat)] of data/descr_climates.txt in its order - each colour is a climate on
    map_climates.tga (what grows on the strategy and battle maps, winter, heat - fatigue in battle)."""
    import re
    from .textio import strip_comment
    path = mod.find("descr_climates.txt")
    if not path:
        return []
    out, cur = [], None
    for l in mod.load(path).texts():
        t = strip_comment(l).split()
        if len(t) == 2 and t[0] == "climate":
            cur = t[1]
        elif cur and t[:1] == ["colour"] and len(t) >= 4:
            out.append([cur, tuple(int(v) for v in t[1:4]), None])
        elif cur and t[:1] == ["heat"] and len(t) >= 2 and out and out[-1][0] == cur:
            out[-1][2] = int(t[1]) if re.match(r"^\d+$", t[1]) else None
    return [tuple(x) for x in out]


def ground_changes(ground_tiles, land_at=None):
    """{(px, py): colour} for map_ground_types.tga: each painted tile's 3 x 3 block. With land_at ((px, py) -> True
    for a land point of map_heights, False for water, None off the picture - land_points()) only the block's points
    on the ground's own side of the waterline: a coastal tile's block reaches over the coast, which runs between the
    tiles - its land ground lay on the water in the game and a sea ground made holes in the land (the heights lead)."""
    out = {}
    for (x, y), c in ground_tiles.items():
        land = is_land_ground(c)
        for dx in (0, 1, 2):
            for dy in (0, 1, 2):
                p = (2 * x + dx, 2 * y + dy)
                if land_at is not None and land_at(*p) not in (None, land):
                    continue
                out[p] = tuple(c)
    return out


def is_land_ground(c):
    """A map_ground_types colour of the land (the beach too - the games lay it on land)."""
    return c is not None and tuple(c[:3]) not in SEA


def land_points(heights, changed=None):
    """(px, py) -> True for a land point of map_heights (grey), False for water (blue), None off the picture;
    changed: {(px, py): colour} laid over the picture (the coast brush's points not written yet)."""
    if heights is None:
        return None
    changed = changed or {}

    def land(px, py):
        c = changed.get((px, py))
        if c is None:
            if not (0 <= px < heights.width and 0 <= py < heights.height):
                return None
            c = heights.get(px, py)
        return is_land_height(c)
    return land


def ground_off_heights(heights, ground):
    """[(px, py, 'water' | 'land')]: the points of map_ground_types on the other side of the waterline than
    map_heights says - 'water': a land ground (the beach too) on a water point, the land's texture lies on the water
    in the game; 'land': a sea ground on a land point, a hole of sea in the land (the user, 2026-10-09: 'textures
    crawled onto the water though the tile is not, and the other way round holes in the land'). The games' own maps
    have nearly none (measured 2026-10-09: Rome, BI, sons_of_mars, norman_prologue 0, Medieval II 18 (lakes in the
    hills), HLR 17). [] when the two pictures are not the same size (then they do not belong together anyway)."""
    if heights is None or ground is None or (heights.width, heights.height) != (ground.width, ground.height):
        return []
    w = heights.width
    out = []
    hr, gr = getattr(heights, "raw", None), getattr(ground, "raw", None)
    if hr is not None and gr is not None:            # the whole map at once - a big mod's 1.3 million points
        hs = zip(hr[0::3], hr[1::3], hr[2::3])
        for i, (h, g) in enumerate(zip(hs, zip(gr[0::3], gr[1::3], gr[2::3]))):
            land_h = h[0] == h[1] == h[2]
            if land_h == (g not in SEA):
                continue
            out.append((i % w, i // w, "land" if land_h else "water"))
        return out
    for py in range(heights.height):
        for px in range(w):
            land_h = is_land_height(heights.get(px, py))
            if land_h != is_land_ground(ground.get(px, py)):
                out.append((px, py, "land" if land_h else "water"))
    return out


def ground_under_heights(heights, ground, wrong):
    """{(px, py): colour}: the ground put right under the heights at the points ground_off_heights found (wrong): a
    water point takes the sea ground most common round it, a land point the land ground most common round it (the
    beach too), looking one point out, then two; points that are wrong themselves are not counted. None near: shallow
    sea / medium fertility."""
    bad = {(px, py) for px, py, _ in wrong}
    out = {}
    for px, py, side in wrong:
        land = side == "land"
        pick = None
        for reach in (1, 2):
            near = Counter()
            for a in range(-reach, reach + 1):
                for b in range(-reach, reach + 1):
                    q = (px + a, py + b)
                    if q in bad or not (0 <= q[0] < ground.width and 0 <= q[1] < ground.height):
                        continue
                    c = ground.get(*q)
                    if is_land_ground(c) == land:
                        near[c] += 1
            if near:
                pick = near.most_common(1)[0][0]
                break
        out[(px, py)] = tuple(pick) if pick else (NEW_LAND_GROUND if land else SHALLOW_SEA)
    return out


# ---- heights (map_heights.tga) ----
# 2 x the map + 1 like the ground. Land is grey: 0 the lowest, 255 descr_terrain's max_land_height (vanilla RTW
# 7511); the sea is blue (0, 0, b) - b the depth (253 nearly everywhere) - and lies exactly under the sea
# ground types (vanilla RTW and M2TW measured). The brush changes land only; the coast stays where it is.
# Land stays 1 or more: a black 0 0 0 may be read as sea (TWC wiki "map_heights.tga"; vanilla keeps a few 0s on
# the coast - left as they are unless the brush raises them).
# map_heights.hgt beside it (the game's own converted copy: two uint32 w, h, then w * h float32 heights, bottom-up;
# vanilla RTW and M2TW measured) wins over the picture while it is there and is not made again by the game, and
# M2TW needs map changes to load without it (TWC wiki "Map heights.hgt") - so it is kept and the same pixels are
# changed in it: old height + (new grey - old grey) x max_land_height / 255 (descr_terrain.txt; vanilla 7511.272,
# about 29.45 a grey step - the vanilla files agree), the rest of the file byte for byte as it was.
HEIGHT_TOOLS = ("raise", "lower", "smooth", "level")


def is_land_height(c):
    return c is not None and c[0] == c[1] == c[2]


def spray_footprint(centre, size):
    """The heights brush of size n, n map_heights pixels across and round, snapped to the pixels like a pixel-art
    pencil (the user, 2026-10-09: 'odd sizes only - make even ones too: 1 = one pixel, 2 = 2 x 2'): an odd size
    centred on the pixel under the mouse, an even one on the corner between the 4 pixels nearest to it. Returns
    (centre, radius, [(px, py)]) - the radius as height_spray takes it."""
    import math
    n = max(1, int(size))
    if n % 2:
        c = (float(math.floor(centre[0] + 0.5)), float(math.floor(centre[1] + 0.5)))
    else:
        c = (math.floor(centre[0]) + 0.5, math.floor(centre[1]) + 0.5)
    r = n / 2.0
    k = int(math.ceil(r))
    pts = [(x, y) for x in range(int(math.floor(c[0])) - k, int(math.floor(c[0])) + k + 2)
           for y in range(int(math.floor(c[1])) - k, int(math.floor(c[1])) + k + 2)
           if (x - c[0]) ** 2 + (y - c[1]) ** 2 <= r * r + 1e-9]
    return c, r, pts


def height_spray(img, centre, radius, tool, strength, values, level=None, dome=False):
    """One puff of the heights brush, like a spray can: held longer, it does more. img: map_heights.tga
    (tga.Image, bottom-up); centre: (px, py) in its pixels, fractions allowed; radius in pixels; strength
    1..10; values: {(px, py): float} - the running heights of pixels touched so far (kept between puffs,
    so small steps add up), updated here. dome: the strength falls off as a dome to just past the edge (the pixel
    brush of spray_footprint: its edge pixels still take some), else from the middle to nothing at the edge.
    Returns {(px, py): int} of the pixels whose grey changed."""
    cx, cy = centre
    out = {}
    if float(radius) < 1.0:                      # size 1: the one point under the mouse, the whole strength
        cx, cy = int(round(cx)), int(round(cy))
        if not (0 <= cx < img.width and 0 <= cy < img.height):
            return out
        r = 0.5
        x0 = x1 = cx
        y0 = y1 = cy
    else:
        r = float(radius)
        x0, x1 = max(int(cx - r), 0), min(int(cx + r) + 1, img.width - 1)
        y0, y1 = max(int(cy - r), 0), min(int(cy + r) + 1, img.height - 1)

    def now(x, y):
        v = values.get((x, y))
        if v is None:
            c = img.get(x, y)
            v = float(c[0]) if is_land_height(c) else None
        return v

    k = strength / 10.0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if d > r:
                continue
            v = now(x, y)
            if v is None:                               # the sea: left alone
                continue
            if r < 1:
                w = 1.0
            elif dome:
                w = 1 - (d / (r + 0.5)) ** 2            # the edge pixels of a small brush still take a good part
            else:
                w = (1 - d / r) ** 2                    # soft edge: the middle gets the most
            if tool == "raise":
                nv = v + 4.0 * k * w
            elif tool == "lower":
                nv = v - 4.0 * k * w
            elif tool == "smooth":
                near = [now(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if 0 <= x + dx < img.width and 0 <= y + dy < img.height]
                near = [n for n in near if n is not None]
                nv = v + (sum(near) / len(near) - v) * 0.5 * k * w
            elif tool == "level" and level is not None:
                nv = v + (level - v) * 0.35 * k * w
            else:
                continue
            floor = 1.0 if v >= 1.0 else v                 # land never goes down to black (sea)
            nv = min(max(nv, floor), 255.0)
            values[(x, y)] = nv
            if int(round(nv)) != img.get(x, y)[0]:
                out[(x, y)] = int(round(nv))
    return out


def max_land_height(mod, campaign):
    """descr_terrain.txt's max_land_height (the campaign's copy, else the base map's), else vanilla's 7511.272."""
    import re
    path = mod.campaign_file(campaign, "descr_terrain.txt")
    if path:
        with open(path, encoding="latin-1") as fh:
            m = re.search(r"max_land_height\s+(-?[\d.]+)", fh.read())
        if m:
            return float(m.group(1))
    return 7511.272


def hgt_patched(path, img, changes, step, absolute=None):
    """map_heights.hgt's bytes with the pixels {(px, py): (old grey, new grey)} moved by (new - old) x step, and the
    pixels of absolute {(px, py): float} set to that height (land made sea or sea made land); refused when its size
    is not the picture's (then the game's copy and the picture do not match anyway)."""
    import struct
    with open(path, "rb") as fh:
        data = bytearray(fh.read())
    w, h = struct.unpack_from("<II", data, 0)
    if (w, h) != (img.width, img.height) or len(data) != 8 + w * h * 4:
        raise ValueError("map_heights.hgt is %d x %d, map_heights.tga %d x %d - they do not match, so the "
                         "heights cannot be changed in both; nothing written" % (w, h, img.width, img.height))
    for (px, py), (old, new) in changes.items():
        at = 8 + (py * w + px) * 4
        v = struct.unpack_from("<f", data, at)[0]
        struct.pack_into("<f", data, at, v + (new - old) * step)
    for (px, py), v in (absolute or {}).items():
        struct.pack_into("<f", data, 8 + (py * w + px) * 4, v)
    return bytes(data)


# ---- land and sea (the coast) ----
# Land or sea is written in three places that must agree: map_regions.tga (a region's colour, or the sea's),
# map_heights.tga (grey land, blue sea - and map_heights.hgt, the game's own copy) and map_ground_types.tga (a land
# or a sea ground) - so the coast brush changes all of them together, tile by tile: its regions pixel, and the 3 x 3
# block of ground and heights round its middle (2x..2x+2, 2y..2y+2).
SHALLOW_SEA, NEW_LAND_GROUND = (196, 0, 0), (96, 160, 64)
DEEPER_SEA = {(64, 0, 0), (128, 0, 0)}                  # ocean, deep sea: deeper than the shallow sea
SEA_DEPTH, COAST_LAND = 253, 2                      # vanilla's usual sea blue; a low shore (about 60 m)
# new land rises from the shore inland as both vanillas' coasts do (median grey by pixels from the sea, measured on
# RTW and M2TW: 2, 8, 12-14, 14-16 ...) - a new island left at the shore's height everywhere lay flat on the water
# and flickered in the game (a report: 'z fighting')
SHORE_RISE = {1: 2, 2: 8, 3: 12, 4: 14}
INLAND = 16


def _from_sea(heights, px, py, new_land, reach=5):
    """Pixels from (px, py) to the nearest sea pixel of the heights picture (Manhattan, up to reach; new_land:
    pixels being made land count as land), or reach + 1 when none is that near."""
    for d in range(1, reach + 1):
        for a in range(-d, d + 1):
            b = d - abs(a)
            for q in {(px + a, py + b), (px + a, py - b)}:
                if q in new_land or not (0 <= q[0] < heights.width and 0 <= q[1] < heights.height):
                    continue
                if not is_land_height(heights.get(*q)):
                    return d
    return reach + 1


def sea_colour(regions_img, region_colours):
    """The sea's colour in map_regions.tga: its most common pixel that is no region, town or port."""
    from collections import Counter
    regions = set(region_colours) | {(0, 0, 0), (255, 255, 255)}
    seen = Counter()
    for y in range(0, regions_img.height, 2):
        for x in range(0, regions_img.width, 2):
            c = regions_img.get(x, y)
            if c not in regions:
                seen[c] += 1
    return seen.most_common(1)[0][0] if seen else (41, 140, 233)


def nearest_region(cmap, xy, reach=60):
    """The region of the land tile nearest to xy (ring by ring), or None."""
    x0, y0 = xy
    for r in range(1, reach + 1):
        best = None
        for dx in range(-r, r + 1):
            for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                reg = cmap.region_at(x0 + dx, y0 + dy)
                if reg and (best is None or abs(dx) + abs(dy) < best[0]):
                    best = (abs(dx) + abs(dy), reg)
        if best:
            return best[1]
    return None


def coast_problem(cmap, xy, to_land, standing, features, region_tiles, ports):
    """None, or why tile xy cannot be made land (to_land) or sea. standing: tiles with a town, port, character,
    fort or resource; features: map_features {(x, y): colour}; region_tiles: {region: how many land tiles it has
    now}; ports: {region: (x, y)}."""
    x, y = xy
    if not (0 <= x < cmap.w and 0 <= y < cmap.h):
        return "off the map"
    if xy in standing:
        return "a town, port, character, fort or resource stands there"
    if to_land:
        return None
    reg = cmap.region_at(x, y)
    if reg and region_tiles.get(reg, 0) <= 1:
        return "it is the last land of %s - a region needs land" % reg
    if features.get(xy, (0, 0, 0)) not in ((0, 0, 0), LAND_BRIDGE):
        return "a river, ford, cliff or volcano is there - rub it out first (Rivers, cliffs, volcanoes...: nothing)"
    for r, p in ports.items():                      # a port must keep touching its region's land
        if r != reg or max(abs(p[0] - x), abs(p[1] - y)) != 1:
            continue
        land = [(p[0] + a, p[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                if (a or b) and (p[0] + a, p[1] + b) != xy and cmap.region_at(p[0] + a, p[1] + b) == r]
        if not land:
            return "the port of %s would touch no land of its region" % r
    return None


def coast_pixels(cmap, xy, to_land, region_colour, heights, sea):
    """What one tile made land (in region_colour) or sea changes: {'regions': {(x, y): colour}, 'ground':
    {(px, py): colour}, 'heights': {(px, py): (r, g, b)}}. heights: map_heights.tga (or None); sea: the sea's
    colour in map_regions. New land: the ground most of its land neighbours have (else medium fertility), low
    heights (its land neighbours' if any, at least 1 - black may be read as sea); new sea: shallow sea, its sea
    neighbours' depth (else vanilla's 253). New land also gets a shallow-sea ring: the 8 sea tiles round it that are
    deeper (ocean / deep sea) turn shallow sea in the ground (a tester: an island stands in shallows, as in nature)."""
    x, y = xy
    out = {"regions": {xy: region_colour if to_land else sea}, "ground": {}, "heights": {}}
    from collections import Counter
    near = Counter()
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            if (a or b) and 0 <= x + a < cmap.w and 0 <= y + b < cmap.h:
                g = cmap.ground_at(x + a, y + b)
                if g is not None and (g in SEA) != to_land:
                    near[g] += 1
    ground = (near.most_common(1)[0][0] if near else NEW_LAND_GROUND) if to_land else SHALLOW_SEA
    if ground in SEA and to_land:
        ground = NEW_LAND_GROUND
    g = cmap.ground
    if to_land and g is not None:
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                nx, ny = x + a, y + b
                if not (a or b) or not (0 <= nx < cmap.w and 0 <= ny < cmap.h) or not cmap.is_sea(nx, ny):
                    continue
                for px in range(2 * nx, 2 * nx + 3):
                    for py in range(2 * ny, 2 * ny + 3):
                        if 0 <= px < g.width and 0 <= py < g.height and g.get(px, py) in DEEPER_SEA:
                            out["ground"][(px, py)] = SHALLOW_SEA
    for px in range(2 * x, 2 * x + 3):
        for py in range(2 * y, 2 * y + 3):
            out["ground"][(px, py)] = ground
    if heights is not None:
        vals = []
        for px in range(2 * x - 1, 2 * x + 4):
            for py in range(2 * y - 1, 2 * y + 4):
                if 0 <= px < heights.width and 0 <= py < heights.height:
                    c = heights.get(px, py)
                    if to_land and is_land_height(c):
                        vals.append(c[0])
                    elif not to_land and not is_land_height(c):
                        vals.append(c[2])
        block = {(px, py) for px in range(2 * x, 2 * x + 3) for py in range(2 * y, 2 * y + 3)}
        for px in range(2 * x, 2 * x + 3):
            for py in range(2 * y, 2 * y + 3):
                if not (0 <= px < heights.width and 0 <= py < heights.height):
                    continue
                c = heights.get(px, py)
                if to_land and not is_land_height(c):
                    v = max(1, min(int(sum(vals) / len(vals)) if vals else COAST_LAND, 12))
                    v = max(v, SHORE_RISE.get(_from_sea(heights, px, py, block), INLAND))   # rises from the shore
                    out["heights"][(px, py)] = (v, v, v)
                elif not to_land and is_land_height(c):
                    v = int(sum(vals) / len(vals)) if vals else SEA_DEPTH
                    out["heights"][(px, py)] = (0, 0, max(1, v))
    return out


def shore_rise(heights, pixels):
    """{(px, py): (v, v, v)} raising the land pixels among `pixels` (the ones the land brush made) to the height
    their distance from the sea asks (SHORE_RISE) - a land made tile by tile otherwise keeps the shore's height
    where it is inland now. Never lowers."""
    out = {}
    for p in pixels:
        if not (0 <= p[0] < heights.width and 0 <= p[1] < heights.height):
            continue
        c = heights.get(*p)
        if not is_land_height(c):
            continue
        want = SHORE_RISE.get(_from_sea(heights, p[0], p[1], ()), INLAND)
        if c[0] < want:
            out[p] = (want, want, want)
    return out


def pen_points(heights, ground, centre, radius, to_land):
    """{'heights': {...}, 'ground': {...}}: the coast pen - map_heights points within radius (points; below 1 the
    one under the mouse) made land (grey COAST_LAND, the low shore modders give the coastline) or water (blue 250,
    shallow), their ground following (the land ground round it / shallow sea). Tile middles left: they are their
    tiles (map_regions)."""
    cx, cy = centre
    r = max(0.5, float(radius))
    out = {"heights": {}, "ground": {}}
    for py in range(int(cy - r) - 1, int(cy + r) + 2):
        for px in range(int(cx - r) - 1, int(cx + r) + 2):
            if not (0 <= px < heights.width and 0 <= py < heights.height) or (px % 2 and py % 2):
                continue
            if ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 > r:
                continue
            land = is_land_height(heights.get(px, py))
            if to_land and not land:
                out["heights"][(px, py)] = (COAST_LAND,) * 3
                if ground is not None:
                    near = Counter(ground.get(px + a, py + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                                   if 0 <= px + a < ground.width and 0 <= py + b < ground.height)
                    out["ground"][(px, py)] = next((k for k, _ in near.most_common() if k not in SEA),
                                                   NEW_LAND_GROUND)
            elif not to_land and land:
                out["heights"][(px, py)] = (0, 0, 250)
                if ground is not None:
                    out["ground"][(px, py)] = SHALLOW_SEA
    return out


COAST_BLUR = 1.6                # tiles: how far the smooth coast looks round a point (rules.md 'HOW THE GAMES' OWN COASTS')


def coast_smoothed(heights, ground, is_land, tiles, blur=COAST_BLUR):
    """{'heights': {(px, py): colour}, 'ground': {...}} putting the coast round the land brush's tiles on a smooth
    curve, the way the games' own maps are made (measured: the coast is decided at half-tile level - the points
    between a land and a sea tile half land, half sea - and follows a curve through the tiles, not their squares; a
    report: 'where is the smoothing?', the brush's coast ran in tile-sized steps). Each point of the changed tiles'
    blocks takes the land share of the tiles round it (a soft blur of `blur` tiles); land where it is over a half.
    A tile's middle never changes side (its region, town, port stay) and pulls the points next to it to its side -
    a 1-tile island or cape stays an oval of land, a 1-tile strait stays open (the blur alone drowned Dalmatia's
    islets). Heights
    follow the share near the waterline (grey 1 - 16, blue 254 - 223), so the game's cut falls on the curve.
    is_land(x, y): the tile is land (map_regions)."""
    import math
    W, H = heights.width, heights.height
    reach = int(2 * blur) + 1
    sigma2 = 2 * (blur / 1.4) ** 2
    memo = {}

    def land_tile(x, y):
        if (x, y) not in memo:
            memo[(x, y)] = bool(is_land(x, y)) if 0 <= 2 * x + 1 < W and 0 <= 2 * y + 1 < H else None
        return memo[(x, y)]

    def share(px, py):
        num = den = 0.0
        cx, cy = (px - 1) // 2, (py - 1) // 2
        for x in range(cx - reach, cx + reach + 2):
            for y in range(cy - reach, cy + reach + 2):
                t = land_tile(x, y)
                if t is None:
                    continue
                dx, dy = (2 * x + 1 - px) / 2.0, (2 * y + 1 - py) / 2.0
                d2 = dx * dx + dy * dy
                if d2 < (2 * blur) ** 2:
                    w = math.exp(-d2 / sigma2)
                    num += w * t
                    den += w
        return num / den if den else 0.0
    points = {(px, py) for x, y in tiles for px in range(2 * x, 2 * x + 3) for py in range(2 * y, 2 * y + 3)
              if 0 <= px < W and 0 <= py < H}
    lone = {}

    def alone(x, y, t):                               # how much a tile stands among the other kind (0 .. 1)
        if (x, y) not in lone:
            lone[(x, y)] = abs(share(2 * x + 1, 2 * y + 1) - t)
        return lone[(x, y)]

    def pull(px, py):                                 # each tile's middle pulls the points next to it to its side,
        best = {True: 0.0, False: 0.0}                # harder the more it stands alone (a 1-tile islet, a strait)
        for x in ((px - 1) // 2, (px - 1) // 2 + 1, (px - 2) // 2):
            for y in ((py - 1) // 2, (py - 1) // 2 + 1, (py - 2) // 2):
                t = land_tile(x, y)
                if t is None:
                    continue
                d2 = ((2 * x + 1 - px) ** 2 + (2 * y + 1 - py) ** 2) / 4.0
                best[t] = max(best[t], 0.6 * (1 + 2 * alone(x, y, t)) * math.exp(-d2 / 0.5))
        return best[True] - best[False]
    out = {"heights": {}, "ground": {}}
    for px, py in sorted(points):
        if px % 2 and py % 2:
            continue                                  # a tile's middle: the tile itself
        s = share(px, py) - 0.5 + pull(px, py)
        c = heights.get(px, py)
        was = is_land_height(c)
        if s > 0:
            g = max(1, min(INLAND, int(round(s * 28))))
            if not was or c[0] > g:
                out["heights"][(px, py)] = (g, g, g)
            if not was and ground is not None and 0 <= px < ground.width and 0 <= py < ground.height:
                near = Counter(ground.get(px + a, py + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                               if 0 <= px + a < ground.width and 0 <= py + b < ground.height)
                kind = next((k for k, _ in near.most_common() if k not in SEA), NEW_LAND_GROUND)
                out["ground"][(px, py)] = kind
        else:
            b = max(1, min(32, int(round(-s * 60))))
            if was:
                out["heights"][(px, py)] = (0, 0, 255 - b)
                if ground is not None and 0 <= px < ground.width and 0 <= py < ground.height:
                    out["ground"][(px, py)] = SHALLOW_SEA
    return out


def min_sea_height(mod, campaign):
    """descr_terrain.txt's min_sea_height, else vanilla RTW's -3122.256."""
    import re
    path = mod.campaign_file(campaign, "descr_terrain.txt")
    if path:
        with open(path, encoding="latin-1") as fh:
            m = re.search(r"min_sea_height\s+(-?[\d.]+)", fh.read())
        if m:
            return float(m.group(1))
    return -3122.256


def hgt_value(colour, top, low):
    """map_heights.hgt's float for a map_heights.tga colour (measured on both vanilla games): land grey * top / 255,
    sea low * (255 - blue) / 255."""
    if is_land_height(colour):
        return colour[0] * top / 255.0
    return low * (255 - colour[2]) / 255.0


# ---- the coast as a shape (rules.md 'WHY A COAST PAINTED BY TILES LOOKS LIKE STAIRS') ----
# The game cuts each square of four map_heights points into two triangles and lays the water at height 0: the shore
# runs where the height crosses 0, at h_land / (h_land - h_water) of the way from a land point to a water point.
# Equal numbers everywhere put every crossing at the same place - the shore can only run along the points' grid and
# its diagonals (stairs at 90 / 45 degrees). So the coast is kept as a SHAPE - each point's signed distance from the
# shore in points (land +, water -) - and the heights near the water are made proportional to it, one slope on both
# sides: the game's crossing then falls on the shore meant. Tiles (map_regions) follow by their middles, the ground
# by its points (the user's yes, 2026-10-09: 'coast as a shape').
SHAPE_SLOPE = 118.0         # metres a point on both sides of the waterline (4 of vanilla's 29.45 m grey steps)
SHAPE_BAND = 1.5            # points from the waterline that follow the slope (a shore's two points are <= 1.42 apart)
SHAPE_RISE = 60.0           # new land further in rises this much a point, up to INLAND (vanilla's inland grey)
SEA_KEEP = 253              # new open water further out: vanilla's usual blue


def tga_colour(m, top, low):
    """map_heights.tga's colour nearest to height m (metres; land grey 1 or more, water blue 254 or less)."""
    if m > 0:
        g = max(1, min(255, int(round(m * 255.0 / top))))
        return (g, g, g)
    b = max(1, min(254, int(round(m * 255.0 / low))))
    return (0, 0, 255 - b)


def read_hgt(path):
    """(w, h, floats) of map_heights.hgt (bottom-up rows, little-endian float32), or None."""
    import struct
    import sys
    from array import array
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except (OSError, TypeError):
        return None
    if len(data) < 8:
        return None
    w, h = struct.unpack_from("<II", data, 0)
    if len(data) != 8 + w * h * 4:
        return None
    a = array("f")
    a.frombytes(data[8:])
    if sys.byteorder != "little":
        a.byteswap()
    return w, h, a


def seg_dist(p, a, b):
    """The distance from point p to the line from a to b."""
    import math
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def shore_segments(metres, x0, y0, x1, y1):
    """The game's waterline among the points x0..x1, y0..y1 (map_heights, bottom-up): [((ax, ay), (bx, by))] in
    points. Each square of four points is cut into two triangles along its (px, py) - (px + 1, py + 1) diagonal (which
    diagonal the game takes is not known: the line differs only in a square with land and water crosswise); the
    water lies under height 0. metres(px, py) -> the height there, None off the map."""
    out = []

    def cut(tri):
        pts = []
        for (a, ha), (b, hb) in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            if (ha > 0) != (hb > 0):
                t = ha / (ha - hb)
                pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        if len(pts) == 2:
            out.append((pts[0], pts[1]))
    for py in range(y0, y1):
        for px in range(x0, x1):
            hs = (metres(px, py), metres(px + 1, py), metres(px, py + 1), metres(px + 1, py + 1))
            if None in hs or sum(1 for v in hs if v > 0) in (0, 4):
                continue
            a, b, c, d = ((px, py), hs[0]), ((px + 1, py), hs[1]), ((px, py + 1), hs[2]), ((px + 1, py + 1), hs[3])
            cut((a, b, d))
            cut((a, d, c))
    return out


class ShapeCoast:
    """The coast as a shape on one campaign's pictures - the Terrain editor's shape brush, 'Smooth the coast', Pull and
    Push, the test mod. stroke() / smooth() / pull() / push() return what to change: {'regions': {(x, y): colour}, 'heights': {(px, py): colour},
    'hgt': {(px, py): metres}, 'ground': {(px, py): colour}, 'tiles': {(x, y): 'land' | 'sea'}, 'kept': [why]}; the
    caller lays them into the pictures (read live from them) and keeps 'hgt' in `exact` (the heights written to
    map_heights.hgt exactly - the game reads them there; the picture only has 29 m grey steps, which left ripples). cmap: the CampaignMap over the same map_regions picture; standing, features (.get),
    counts ({region: land tiles}, kept up to date here), as coast_problem takes them; sea: the sea's colour in
    map_regions; region: the region new land joins (None: the nearest); hgt: read_hgt() of map_heights.hgt (the
    heights the game reads) or None."""

    def __init__(self, heights, ground, cmap, standing, features, counts, sea, top, low, hgt=None, region=None,
                 exact=None):
        self.heights, self.ground, self.cmap = heights, ground, cmap
        self.exact = exact if exact is not None else {}
        self.standing, self.features, self.counts, self.sea = standing, features, counts, sea
        self.top, self.low, self.region = top, low, region
        self.grey, self.blue = top / 255.0, -low / 255.0
        self.hgt = hgt if hgt and (hgt[0], hgt[1]) == (heights.width, heights.height) else None

    def metres(self, px, py):
        """The height at point (px, py) as the game reads it: map_heights.hgt's own value while the picture still
        agrees with it (an unchanged point), else the picture's; land never 0 (0 reads as water)."""
        h = self.heights
        if not (0 <= px < h.width and 0 <= py < h.height):
            return None
        c = h.get(px, py)
        e = self.exact.get((px, py))
        if e is not None and self.tga_colour(e) == c:     # written by the shape brush (and not changed since)
            return e
        land = is_land_height(c)
        v = hgt_value(c, self.top, self.low)
        if self.hgt is not None:
            f = self.hgt[2][py * h.width + px]
            if (f > 0) == land and abs(f - v) <= 1.5 * (self.grey if land else self.blue):
                return f
        return max(v, 1.0) if land else v

    def field(self, cx, cy, reach, cap):
        """{(px, py): signed distance in points from the game's waterline (land +, water -), at most cap} of the points
        within reach of (cx, cy)."""
        import math
        x0, x1 = int(math.floor(cx - reach)), int(math.ceil(cx + reach))
        y0, y1 = int(math.floor(cy - reach)), int(math.ceil(cy + reach))
        memo = {}

        def mt(px, py):
            if (px, py) not in memo:
                memo[(px, py)] = self.metres(px, py)
            return memo[(px, py)]
        g = int(math.ceil(cap + 0.75))
        cells = {}
        for s in shore_segments(mt, x0 - g, y0 - g, x1 + g, y1 + g):
            k = (int(math.floor((s[0][0] + s[1][0]) / 2.0)), int(math.floor((s[0][1] + s[1][1]) / 2.0)))
            cells.setdefault(k, []).append(s)
        out = {}
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                v = mt(px, py)
                if v is None:
                    continue
                best = cap
                for i in range(px - g, px + g + 1):
                    for j in range(py - g, py + g + 1):
                        for a, b in cells.get((i, j), ()):
                            d = seg_dist((px, py), a, b)
                            if d < best:
                                best = d
                out[(px, py)] = best if v > 0 else -best
        return out

    def stroke(self, a, b, radius, to_land):
        """The shape brush moved from point a to point b (fractions allowed): the land (to_land) or the water grows by
        the round-ended band of `radius` points along that line."""
        import math
        r = max(0.5, float(radius))
        reach = r + math.hypot(b[0] - a[0], b[1] - a[1]) / 2.0 + SHAPE_BAND + 1
        old = self.field((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, reach, SHAPE_BAND + 0.5)
        new = {}
        for p, s in old.items():
            d = r - seg_dist(p, a, b)                 # + inside the brush's band
            new[p] = max(s, d) if to_land else min(s, -d)
        return self._settle(old, new)

    def smooth(self, centre, radius, k=0.5):
        """'Smooth the coast' under a round brush: the shape blurred a little each time (corners rounded, small bays
        and capes eased - like the sea wearing a coast down); held longer, it smooths more."""
        import math
        r = max(1.0, float(radius))
        old = self.field(centre[0], centre[1], r + SHAPE_BAND + 3, SHAPE_BAND + 2.5)
        kern = [(i, j, math.exp(-(i * i + j * j) / 2.0)) for i in range(-2, 3) for j in range(-2, 3)]
        new = dict(old)
        for p, s in old.items():
            d = math.hypot(p[0] - centre[0], p[1] - centre[1])
            if d > r + 0.5 or abs(s) > SHAPE_BAND + 0.5:
                continue
            num = den = 0.0
            for i, j, w in kern:
                q = old.get((p[0] + i, p[1] + j))
                if q is not None:
                    num += w * q
                    den += w
            new[p] = s + k * min(1.0, r + 0.5 - d) * (num / den - s)
        return self._settle(old, new)

    @staticmethod
    def _falloff(d, radius):
        """How much of a pull / push a point takes at distance d from the brush's middle: all of it there, softly
        less outwards, none at the brush's edge."""
        t = d / radius
        return (1.0 - t * t) ** 2 if t < 1.0 else 0.0

    def pull(self, a, b, radius):
        """'Pull the coast' (like a painter's liquify): the coast under a round brush grabbed at point a and dragged to
        point b - the shape moves with the mouse, most in the brush's middle, softly less to its edge; the rest of
        the coast stays. Each point takes the shape from where it was pulled from: s(p) = s_old(p - w(p) * move)."""
        import math
        r = max(1.0, float(radius))
        dx, dy = b[0] - a[0], b[1] - a[1]
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return self._settle({}, {})
        steps = max(1, int(math.ceil(dist / (r / 3.0))))  # a long jump of the mouse in small steps: never folded
        old = self.field((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, r + dist / 2.0 + SHAPE_BAND + 3,
                         SHAPE_BAND + 0.5)
        cur = dict(old)

        def at(x, y):                                   # the shape between the points (bilinear)
            x0, y0 = int(math.floor(x)), int(math.floor(y))
            fx, fy = x - x0, y - y0
            num = den = 0.0
            for i, j, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy),
                            (1, 1, fx * fy)):
                v = cur.get((x0 + i, y0 + j))
                if v is not None and w > 0:
                    num += w * v
                    den += w
            return num / den if den else None
        for k in range(steps):
            cx, cy = a[0] + dx * k / steps, a[1] + dy * k / steps
            mx, my = dx / steps, dy / steps
            nxt = dict(cur)
            for p in cur:
                w = self._falloff(math.hypot(p[0] - cx, p[1] - cy), r)
                if w > 0:
                    v = at(p[0] - w * mx, p[1] - w * my)
                    if v is not None:
                        nxt[p] = v
            cur = nxt
        return self._settle(old, cur)

    def push(self, centre, radius, grow_land, k=0.35):
        """'Push the coast': the coast under a round brush pushed outwards from the side the press began on - from
        the land the land grows into the water, from the water the water eats into the land; most in the brush's
        middle, softly less to its edge; held longer, it pushes further."""
        import math
        r = max(1.0, float(radius))
        old = self.field(centre[0], centre[1], r + SHAPE_BAND + 2, SHAPE_BAND + 0.5)
        new = dict(old)
        for p, s in old.items():
            w = self._falloff(math.hypot(p[0] - centre[0], p[1] - centre[1]), r)
            if w > 0:
                new[p] = s + k * w if grow_land else s - k * w
        return self._settle(old, new)

    def tga_colour(self, m):
        return tga_colour(m, self.top, self.low)

    def _height(self, s, was):
        """(colour, metres) for signed distance s (points) - metres None where the point keeps its own; was: its
        colour now."""
        if s > SHAPE_BAND:                              # further in: new land rises, old land stays as high
            m = SHAPE_SLOPE * SHAPE_BAND + SHAPE_RISE * (s - SHAPE_BAND)
            c = self.tga_colour(min(m, INLAND * self.grey))
            if is_land_height(was) and was[0] >= c[0]:
                return was, None
            return c, None
        if s < -SHAPE_BAND:                             # further out: old water stays, new water is vanilla's usual
            return (was, None) if not is_land_height(was) else ((0, 0, SEA_KEEP), None)
        m = SHAPE_SLOPE * s if s <= 0 else max(0.5, SHAPE_SLOPE * s)   # land never 0 (it reads as water)
        return self.tga_colour(m), m

    def _settle(self, old, new):
        import math
        out = {"regions": {}, "heights": {}, "hgt": {}, "ground": {}, "tiles": {}, "kept": []}
        flips = {}
        for (px, py), s in new.items():                 # tiles whose middle changes side
            if px % 2 and py % 2 and (s > 0) != (old[(px, py)] > 0):
                flips[((px - 1) // 2, (py - 1) // 2)] = s > 0
        for t, to_land in sorted(flips.items()):
            if not (0 <= t[0] < self.cmap.w and 0 <= t[1] < self.cmap.h) or self.cmap.is_sea(*t) != to_land:
                continue                                # map_regions already says so (a lake in the heights only)
            why = coast_problem(self.cmap, t, to_land, self.standing, self.features, self.counts, self.cmap.ports)
            region = None
            if not why and to_land:
                region = self.region if self.region in self.cmap.info else nearest_region(self.cmap, t)
                if not region:
                    why = "no region near enough to join - pick one in 'new land joins'"
            if why:                                     # it keeps its side: a little land / water round its middle
                out["kept"].append(why)
                m = (2 * t[0] + 1, 2 * t[1] + 1)
                for p in new:
                    d = math.hypot(p[0] - m[0], p[1] - m[1])
                    if d < 1.6:
                        new[p] = min(new[p], d - 0.75) if to_land else max(new[p], 0.75 - d)
                continue
            was = self.cmap.region_at(*t)
            out["regions"][t] = self.cmap.info[region]["colour"] if to_land else self.sea
            out["tiles"][t] = "land" if to_land else "sea"
            if to_land:
                self.counts[region] = self.counts.get(region, 0) + 1
            elif was:
                self.counts[was] = self.counts.get(was, 0) - 1
        g = self.ground
        for p, s in new.items():
            o = old[p]
            flip = (s > 0) != (o > 0)
            if not flip and (abs(s - o) < 0.02 or abs(s) > SHAPE_BAND):
                continue
            was = self.heights.get(*p)
            c, m = self._height(s, was)
            if c != was:
                out["heights"][p] = c
            if m is not None:
                out["hgt"][p] = m
                self.exact[p] = m
            else:
                self.exact.pop(p, None)
            if g is None or not (0 <= p[0] < g.width and 0 <= p[1] < g.height):
                continue
            now = g.get(*p)
            if s > 0 and not is_land_ground(now):       # the ground follows: the land round it ...
                near = Counter(g.get(p[0] + a, p[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)
                               if 0 <= p[0] + a < g.width and 0 <= p[1] + b < g.height)
                out["ground"][p] = next((k for k, _ in near.most_common() if is_land_ground(k)), NEW_LAND_GROUND)
            elif s <= 0 and (is_land_ground(now) or (s >= -2 * SHAPE_BAND and now in DEEPER_SEA)):
                out["ground"][p] = SHALLOW_SEA          # ... and shallow water along the shore
        return out


def radar_painted(data, map_w, map_h, kind_of, changed):
    """A minimap picture (radar_map1 / radar_map2.tga) with the changed tiles drawn again by their new ground (the
    user, 2026-10-09: 'and if I painted land there - can it draw the land, by its type?'): each changed tile takes
    the picture's own pixels from the nearest unchanged tile of the same ground (a forest from a forest, the sea
    from the sea - its texture and its season kept: snow on the winter map where the land round it is white), else
    the nearest land / sea. kind_of(x, y): the tile's ground colour after the change. (TGA bytes) or None without
    Pillow or with nothing to change."""
    try:
        from PIL import Image
    except ImportError:
        return None
    import io
    from .mapresize import radar_frame
    changed = {tuple(t) for t in changed if 0 <= t[0] < map_w and 0 <= t[1] < map_h}
    if not changed:
        return None
    pic = Image.open(io.BytesIO(data))
    pic.load()
    t, b, lft, r, _ = radar_frame(pic)
    iw, ih = pic.width - lft - r, pic.height - t - b
    sx, sy = iw / float(map_w), ih / float(map_h)

    def box(x, y):                                    # the tile's pixels (the picture is top row first)
        row = map_h - 1 - y
        x0, y0 = lft + int(x * sx), t + int(row * sy)
        return x0, y0, max(x0 + 1, lft + int((x + 1) * sx)), max(y0 + 1, t + int((row + 1) * sy))
    step = 1 if map_w * map_h <= 120000 else 2         # a huge map: every second tile is source enough
    cell = 8
    kinds = {}

    def kind(x, y):
        if (x, y) not in kinds:
            kinds[(x, y)] = kind_of(x, y)
        return kinds[(x, y)]
    # sources: tiles deep inside their own ground (all 8 round them the same, none changed) - a coastal tile's
    # pixels carry sand and foam; the coastal ones only when a ground has no inside at all
    inner = ({}, {True: {}, False: {}})
    edge = ({}, {True: {}, False: {}})
    for x in range(0, map_w, step):
        for y in range(0, map_h, step):
            if (x, y) in changed:
                continue
            k = kind(x, y)
            deep = all(0 <= x + a < map_w and 0 <= y + bb < map_h and (x + a, y + bb) not in changed and
                       kind(x + a, y + bb) == k for a in (-1, 0, 1) for bb in (-1, 0, 1))
            by_kind, by_sea = inner if deep else edge
            key = (x // cell, y // cell)
            by_kind.setdefault(k, {}).setdefault(key, []).append((x, y))
            by_sea[k in SEA].setdefault(key, []).append((x, y))

    def nearest(buckets, x, y):
        if not buckets:
            return None
        cx, cy = x // cell, y // cell
        for ring in range(0, max(map_w, map_h) // cell + 2):
            found = []
            for a in range(cx - ring, cx + ring + 1):
                for bb in (cy - ring, cy + ring) if ring else (cy,):
                    found += buckets.get((a, bb), [])
                for bb in range(cy - ring + 1, cy + ring) if ring else ():
                    if a in (cx - ring, cx + ring):
                        found += buckets.get((a, bb), [])
            if found:
                return min(found, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)
        return None
    out = pic.copy()
    for x, y in sorted(changed):
        k = kind(x, y)
        src = (nearest(inner[0].get(k), x, y) or nearest(edge[0].get(k), x, y) or
               nearest(inner[1][k in SEA], x, y) or nearest(edge[1][k in SEA], x, y))
        if src is None:
            continue
        x0, y0, x1, y1 = box(x, y)
        patch = pic.crop(box(*src))
        if patch.size != (x1 - x0, y1 - y0):
            patch = patch.resize((x1 - x0, y1 - y0), Image.NEAREST)
        out.paste(patch, (x0, y0))
    buf = io.BytesIO()
    out.save(buf, format="TGA")
    return buf.getvalue()


def apply(plan, campaign, ground=None, features=None, climate=None, heights=None, coast=None, wasteland=None):
    """Write the painted tiles: ground {(x, y): colour} into map_ground_types.tga, features
    {(x, y): colour} into map_features.tga, climate {(x, y): colour} into map_climates.tga (the same
    3 x 3 block per tile as the ground); coast {'tiles': {(x, y): 'land' | 'sea'}, 'regions' / 'ground' /
    'heights': pixels (coast_pixels)} into map_regions, map_ground_types (the painted ground on top),
    map_heights and map_heights.hgt; map.rwm deleted so the game builds the map again. wasteland: (name, colour) of
    the common wasteland not written yet (regiondelete.common_wasteland) - made when land of its colour is painted."""
    mod = plan.mod
    ground = {tuple(k): tuple(v) for k, v in (ground or {}).items()}
    features = {tuple(k): tuple(v) for k, v in (features or {}).items()}
    climate = {tuple(k): tuple(v) for k, v in (climate or {}).items()}
    heights = {tuple(k): int(v) for k, v in (heights or {}).items()}
    coast = coast or {}
    ctiles = coast.get("tiles") or {}
    if not ground and not features and not climate and not heights and not ctiles and \
            not coast.get("heights") and not coast.get("ground") and not coast.get("hgt"):
        return
    from collections import Counter
    climate_names = {c: n for n, c, _ in climates(mod)}
    if ctiles:
        path = mod.campaign_file(campaign, "map_regions.tga")
        plan.patch_tga(path, {tuple(k): tuple(v) for k, v in coast["regions"].items()})
        n_land = sum(1 for v in ctiles.values() if v == "land")
        plan.notes.append((mod.rel(path), "%d tile(s) made land, %d made sea" % (n_land, len(ctiles) - n_land)))
        if wasteland:
            mine = [tuple(k) for k, v in coast["regions"].items() if tuple(v) == tuple(wasteland[1])]
            if mine:
                from .regiondelete import make_wasteland
                make_wasteland(plan, campaign, wasteland[0], wasteland[1], mine, land=True)
    gchanges = {tuple(k): tuple(v) for k, v in (coast.get("ground") or {}).items()}
    cheights = {tuple(k): tuple(v) for k, v in (coast.get("heights") or {}).items()}
    exact = {tuple(k): float(v) for k, v in (coast.get("hgt") or {}).items()}
    # the painted ground stays on its side of the waterline (the heights as they will be written)
    land_at = land_points(mod._optional_map(campaign, "map_heights.tga"), cheights) if ground else None
    gchanges.update(ground_changes(ground, land_at))
    gtiles = dict(ground)
    gimg = mod._optional_map(campaign, "map_ground_types.tga") if ctiles else None
    for xy, v in ctiles.items():                    # a turned tile's ground: its middle's, as written
        xy = tuple(xy)
        mid = (2 * xy[0] + 1, 2 * xy[1] + 1)
        now = gimg.get(*mid) if gimg is not None and mid[0] < gimg.width and mid[1] < gimg.height else None
        gtiles.setdefault(xy, gchanges.get(mid) or (now if now and (now in SEA) == (v == "sea") else None) or
                          (SHALLOW_SEA if v == "sea" else NEW_LAND_GROUND))
    for name, tiles, names, changes in (("map_ground_types.tga", gtiles, GROUND, gchanges),
                                        ("map_features.tga", features, FEATURES, features),
                                        ("map_climates.tga", climate, climate_names, ground_changes(climate))):
        if not tiles and not changes:
            continue
        path = mod.campaign_file(campaign, name)
        if not path:
            raise ValueError("this campaign has no %s" % name)
        plan.patch_tga(path, changes)
        count = Counter(names.get(c, str(c)) for c in tiles.values())
        plan.notes.append((mod.rel(path), "%d tile(s): %s" % (len(tiles), ", ".join(
            "%d %s" % (n, k) for k, n in count.most_common())) if tiles else
            "%d point(s) of the coast (the coast pen, Smooth the coast or the ground put right under the "
            "heights)" % len(changes)))
    if heights or cheights or exact:
        path = mod.campaign_file(campaign, "map_heights.tga")
        if not path:
            raise ValueError("this campaign has no map_heights.tga")
        img = mod._optional_map(campaign, "map_heights.tga")
        bad = [p for p in heights if not is_land_height(cheights.get(p, img.get(*p)))]
        if bad:
            raise ValueError("heights painted on the sea at %d, %d - the brush changes land only" % bad[0])
        final = dict(cheights)
        final.update({p: (v, v, v) for p, v in heights.items()})
        if final:
            plan.patch_tga(path, final)
        if heights:
            up = sum(1 for p, v in heights.items() if is_land_height(img.get(*p)) and v > img.get(*p)[0])
            plan.notes.append((mod.rel(path), "%d pixel(s) of land: %d raised, %d lowered" % (
                len(heights), up, len(heights) - up)))
        if cheights:
            plan.notes.append((mod.rel(path), "%d pixel(s) of the coast: turned land or water, or set on the shore's "
                                              "slope (the coast brushes)" % len(cheights)))
        hgt = os.path.join(os.path.dirname(path), "map_heights.hgt")
        if os.path.isfile(hgt):
            top, low = max_land_height(mod, campaign), min_sea_height(mod, campaign)
            step = top / 255.0
            relative = {p: (img.get(*p)[0], v) for p, v in heights.items() if p not in cheights}
            absolute = {p: hgt_value(final[p], top, low) for p in cheights}
            # the shape brush's exact heights, where the picture still has the colour they were written with
            for p, m in exact.items():
                if p not in heights and tga_colour(m, top, low) == final.get(p, img.get(*p)):
                    absolute[p] = m
            plan.binary(hgt, hgt_patched(hgt, img, relative, step, absolute))
            plan.notes.append((mod.rel(hgt), "%d pixel(s) changed (the game reads this copy of the heights while it "
                                             "is there; %.2f per grey step; the shape brush's to the metre)"
                               % (len(set(relative) | set(absolute)), step)))
    if gtiles:                                        # the minimap follows the new land / sea / ground
        _radar_follows(plan, mod, campaign, gtiles, gchanges)
    for folder in {os.path.dirname(mod.campaign_file(campaign, "map_regions.tga")),
                   os.path.join(mod.data, "world", "maps", "base")}:
        plan.delete(os.path.join(folder, "map.rwm"), "the game builds the map again from the changed pictures")


def _radar_follows(plan, mod, campaign, tiles, gchanges):
    """The campaign's minimap pictures repainted on the tiles whose ground (or land / sea) changed."""
    from .upscale import CAMPAIGN_PICTURES
    strat = mod.campaign_file(campaign, "descr_strat.txt")
    regions = mod.campaign_file(campaign, "map_regions.tga")
    if not strat or not regions:
        return
    import struct
    with open(regions, "rb") as fh:
        w, h = struct.unpack_from("<HH", fh.read(18), 12)
    g = mod._optional_map(campaign, "map_ground_types.tga")

    def kind_of(x, y):
        p = (2 * x + 1, 2 * y + 1)
        return gchanges.get(p) or (g.get(*p) if g is not None else None)
    for name in CAMPAIGN_PICTURES:
        if not name.startswith(("radar_map", "map_radar")):
            continue
        p = os.path.join(os.path.dirname(strat), name)
        if not os.path.isfile(p):
            continue
        data = plan.binaries.get(p)
        if data is None:
            with open(p, "rb") as fh:
                data = fh.read()
        got = radar_painted(data, w, h, kind_of, tiles)
        if got is None:
            plan.notes.append((mod.rel(p), "not repainted (no Pillow) - the minimap still shows the old land and sea"))
            continue
        plan.binary(p, got)
        plan.notes.append((mod.rel(p), "the minimap drawn again on the %d changed tile(s) from the nearest tiles "
                                       "of the same ground" % len(tiles)))


__all__ = ["GROUND", "SEA", "FEATURES", "LAND_BRUSHES", "SEA_BRUSHES", "ground_brushes", "FEATURE_BRUSHES", "paint_problem",
           "river_warnings", "river_shapes", "bridge_warnings", "feature_brushes", "river_path", "climates", "HEIGHT_TOOLS", "is_land_height", "height_spray", "max_land_height", "hgt_patched",
           "sea_colour", "nearest_region", "coast_problem", "coast_pixels", "shore_rise", "coast_smoothed", "pen_points", "min_sea_height", "hgt_value", "radar_painted", "apply", "tga_colour",
           "is_land_ground", "land_points", "ground_off_heights", "ground_under_heights", "read_hgt", "seg_dist",
           "shore_segments", "ShapeCoast", "SHAPE_SLOPE", "SHAPE_BAND"]
