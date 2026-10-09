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
LAND_BRUSHES = [(101, 124, 0), (96, 160, 64), (0, 128, 0), (0, 0, 0), (0, 128, 128), (0, 64, 0), (128, 128, 64),
                (98, 65, 65), (196, 128, 128), (0, 255, 128)]
# the beach (white): the sea's tiles along the coast, one wide, as both games' own maps draw it (M2TW 502 on the sea,
# 1 inland; Rome 571 / 9) - painted with the sea's brushes
SEA_BRUSHES = [(196, 0, 0), (64, 0, 0), (128, 0, 0), (255, 255, 255)]

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
    if what == "climate":
        if sea:
            return "the sea keeps its climate - climates are painted on land"
        return None
    if what == "ground":
        if colour == BEACH:                           # the sea's edge along the coast, one tile wide
            if not sea:
                return "the beach is the sea's edge along the coast - paint it on a sea tile beside the land"
            if not any(0 <= x + dx < cmap.w and 0 <= y + dy < cmap.h and not cmap.is_sea(x + dx, y + dy)
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy):
                return "the beach is one tile wide along the coast - this sea tile does not touch the land"
            return None
        if (colour in SEA) != sea:
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


def ground_changes(ground_tiles):
    """{(px, py): colour} for map_ground_types.tga: each painted tile's 3 x 3 block."""
    out = {}
    for (x, y), c in ground_tiles.items():
        for dx in (0, 1, 2):
            for dy in (0, 1, 2):
                out[(2 * x + dx, 2 * y + dy)] = tuple(c)
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


def height_spray(img, centre, radius, tool, strength, values, level=None):
    """One puff of the heights brush, like a spray can: held longer, it does more. img: map_heights.tga
    (tga.Image, bottom-up); centre: (px, py) in its pixels, fractions allowed; radius in pixels; strength
    1..10; values: {(px, py): float} - the running heights of pixels touched so far (kept between puffs,
    so small steps add up), updated here. Returns {(px, py): int} of the pixels whose grey changed."""
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
            w = (1 - d / r) ** 2 if r >= 1 else 1.0     # soft edge: the middle gets the most
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


def apply(plan, campaign, ground=None, features=None, climate=None, heights=None, coast=None):
    """Write the painted tiles: ground {(x, y): colour} into map_ground_types.tga, features
    {(x, y): colour} into map_features.tga, climate {(x, y): colour} into map_climates.tga (the same
    3 x 3 block per tile as the ground); coast {'tiles': {(x, y): 'land' | 'sea'}, 'regions' / 'ground' /
    'heights': pixels (coast_pixels)} into map_regions, map_ground_types (the painted ground on top),
    map_heights and map_heights.hgt; map.rwm deleted so the game builds the map again."""
    mod = plan.mod
    ground = {tuple(k): tuple(v) for k, v in (ground or {}).items()}
    features = {tuple(k): tuple(v) for k, v in (features or {}).items()}
    climate = {tuple(k): tuple(v) for k, v in (climate or {}).items()}
    heights = {tuple(k): int(v) for k, v in (heights or {}).items()}
    coast = coast or {}
    ctiles = coast.get("tiles") or {}
    if not ground and not features and not climate and not heights and not ctiles:
        return
    from collections import Counter
    climate_names = {c: n for n, c, _ in climates(mod)}
    if ctiles:
        path = mod.campaign_file(campaign, "map_regions.tga")
        plan.patch_tga(path, {tuple(k): tuple(v) for k, v in coast["regions"].items()})
        n_land = sum(1 for v in ctiles.values() if v == "land")
        plan.notes.append((mod.rel(path), "%d tile(s) made land, %d made sea" % (n_land, len(ctiles) - n_land)))
    gchanges = {tuple(k): tuple(v) for k, v in (coast.get("ground") or {}).items()}
    gchanges.update(ground_changes(ground))
    gtiles = dict(ground)
    for xy, v in ctiles.items():
        gtiles.setdefault(tuple(xy), (SHALLOW_SEA if v == "sea" else NEW_LAND_GROUND))
    for name, tiles, names, changes in (("map_ground_types.tga", gtiles, GROUND, gchanges),
                                        ("map_features.tga", features, FEATURES, features),
                                        ("map_climates.tga", climate, climate_names, ground_changes(climate))):
        if not tiles:
            continue
        path = mod.campaign_file(campaign, name)
        if not path:
            raise ValueError("this campaign has no %s" % name)
        plan.patch_tga(path, changes)
        count = Counter(names.get(c, str(c)) for c in tiles.values())
        plan.notes.append((mod.rel(path), "%d tile(s): %s" % (len(tiles), ", ".join(
            "%d %s" % (n, k) for k, n in count.most_common()))))
    cheights = {tuple(k): tuple(v) for k, v in (coast.get("heights") or {}).items()}
    if heights or cheights:
        path = mod.campaign_file(campaign, "map_heights.tga")
        if not path:
            raise ValueError("this campaign has no map_heights.tga")
        img = mod._optional_map(campaign, "map_heights.tga")
        bad = [p for p in heights if not is_land_height(cheights.get(p, img.get(*p)))]
        if bad:
            raise ValueError("heights painted on the sea at %d, %d - the brush changes land only" % bad[0])
        final = dict(cheights)
        final.update({p: (v, v, v) for p, v in heights.items()})
        plan.patch_tga(path, final)
        if heights:
            up = sum(1 for p, v in heights.items() if is_land_height(img.get(*p)) and v > img.get(*p)[0])
            plan.notes.append((mod.rel(path), "%d pixel(s) of land: %d raised, %d lowered" % (
                len(heights), up, len(heights) - up)))
        if cheights:
            plan.notes.append((mod.rel(path), "%d pixel(s) turned from sea to land or land to sea (the coast brush)"
                               % len(cheights)))
        hgt = os.path.join(os.path.dirname(path), "map_heights.hgt")
        if os.path.isfile(hgt):
            top, low = max_land_height(mod, campaign), min_sea_height(mod, campaign)
            step = top / 255.0
            relative = {p: (img.get(*p)[0], v) for p, v in heights.items() if p not in cheights}
            absolute = {p: hgt_value(final[p], top, low) for p in cheights}
            plan.binary(hgt, hgt_patched(hgt, img, relative, step, absolute))
            plan.notes.append((mod.rel(hgt), "the same %d pixel(s) changed (the game reads this copy of the heights "
                                             "while it is there; %.2f per grey step)" % (len(final), step)))
    for folder in {os.path.dirname(mod.campaign_file(campaign, "map_regions.tga")),
                   os.path.join(mod.data, "world", "maps", "base")}:
        plan.delete(os.path.join(folder, "map.rwm"), "the game builds the map again from the changed pictures")


__all__ = ["GROUND", "SEA", "FEATURES", "LAND_BRUSHES", "SEA_BRUSHES", "ground_brushes", "FEATURE_BRUSHES", "paint_problem",
           "river_warnings", "river_shapes", "bridge_warnings", "feature_brushes", "river_path", "climates", "HEIGHT_TOOLS", "is_land_height", "height_spray", "max_land_height", "hgt_patched",
           "sea_colour", "nearest_region", "coast_problem", "coast_pixels", "shore_rise", "min_sea_height", "hgt_value", "apply"]
