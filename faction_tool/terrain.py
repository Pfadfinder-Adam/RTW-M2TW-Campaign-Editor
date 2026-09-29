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

from .tga import patched

# map_ground_types.tga colours (Rome and Medieval II; the last two are Medieval II's)
GROUND = {
    (101, 124, 0): "low fertility", (96, 160, 64): "medium fertility", (0, 128, 0): "high fertility",
    (0, 0, 0): "wilderness", (0, 64, 0): "dense forest", (0, 128, 128): "sparse forest",
    (128, 128, 64): "hills", (98, 65, 65): "mountains", (196, 128, 128): "high mountains",
    (0, 255, 128): "swamp", (255, 255, 255): "beach / impassable", (64, 0, 0): "ocean",
    (128, 0, 0): "deep sea", (196, 0, 0): "shallow sea",
    (64, 64, 64): "impassable land", (128, 128, 128): "impassable sea",
}
SEA = {(64, 0, 0), (128, 0, 0), (196, 0, 0), (128, 128, 128)}
LAND_BRUSHES = [(101, 124, 0), (96, 160, 64), (0, 128, 0), (0, 0, 0), (0, 128, 128), (0, 64, 0), (128, 128, 64),
                (98, 65, 65), (196, 128, 128), (0, 255, 128)]
SEA_BRUSHES = [(196, 0, 0), (64, 0, 0), (128, 0, 0)]

# map_features.tga colours (one pixel per tile; black = nothing)
FEATURES = {
    (0, 0, 0): "nothing", (0, 0, 255): "river", (0, 255, 255): "ford (river crossing)",
    (255, 255, 255): "river source", (255, 255, 0): "cliff", (255, 0, 0): "volcano",
    (0, 255, 0): "land bridge (Medieval II)",
}
FEATURE_BRUSHES = [(0, 0, 255), (0, 255, 255), (255, 255, 255), (255, 255, 0), (0, 0, 0)]
RIVERY = {(0, 0, 255), (0, 255, 255), (255, 255, 255)}

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
        if (colour in SEA) != sea:
            return "land and sea are not swapped here (the coast is also the regions and the heights)"
        if xy in standing and colour in BLOCKED_GROUND:
            return "a town, port or character stands there - the game refuses %s under them" % GROUND.get(colour)
        return None
    if sea and colour != (0, 0, 0):
        return "rivers, fords and cliffs are on land"
    if xy in standing and colour != (0, 0, 0):
        return "a town, port or character stands there - the game refuses them on a river, ford or cliff"
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
    from .moddata import _ci
    from .textio import strip_comment
    path = _ci(mod.data, "descr_climates.txt")
    if not path:
        return []
    out, cur, heat = [], None, None
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
    r = max(float(radius), 1.0)
    out = {}
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
            w = (1 - d / r) ** 2 if r > 1 else 1.0      # soft edge: the middle gets the most
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
        m = re.search(r"max_land_height\s+(-?[\d.]+)", open(path, encoding="latin-1").read())
        if m:
            return float(m.group(1))
    return 7511.272


def hgt_patched(path, img, changes, step):
    """map_heights.hgt's bytes with the pixels {(px, py): (old grey, new grey)} moved by (new - old) x step;
    refused when its size is not the picture's (then the game's copy and the picture do not match anyway)."""
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
    return bytes(data)


def apply(plan, campaign, ground=None, features=None, climate=None, heights=None):
    """Write the painted tiles: ground {(x, y): colour} into map_ground_types.tga, features
    {(x, y): colour} into map_features.tga, climate {(x, y): colour} into map_climates.tga (the same
    3 x 3 block per tile as the ground); map.rwm deleted so the game builds the map again."""
    mod = plan.mod
    ground = {tuple(k): tuple(v) for k, v in (ground or {}).items()}
    features = {tuple(k): tuple(v) for k, v in (features or {}).items()}
    climate = {tuple(k): tuple(v) for k, v in (climate or {}).items()}
    heights = {tuple(k): int(v) for k, v in (heights or {}).items()}
    if not ground and not features and not climate and not heights:
        return
    from collections import Counter
    climate_names = {c: n for n, c, _ in climates(mod)}
    for name, tiles, names, changes in (("map_ground_types.tga", ground, GROUND, ground_changes(ground)),
                                        ("map_features.tga", features, FEATURES, features),
                                        ("map_climates.tga", climate, climate_names, ground_changes(climate))):
        if not tiles:
            continue
        path = mod.campaign_file(campaign, name)
        if not path:
            raise ValueError("this campaign has no %s" % name)
        plan.binary(path, patched(path, changes))
        count = Counter(names.get(c, str(c)) for c in tiles.values())
        plan.notes.append((mod.rel(path), "%d tile(s): %s" % (len(tiles), ", ".join(
            "%d %s" % (n, k) for k, n in count.most_common()))))
    if heights:
        path = mod.campaign_file(campaign, "map_heights.tga")
        if not path:
            raise ValueError("this campaign has no map_heights.tga")
        img = mod._optional_map(campaign, "map_heights.tga")
        bad = [p for p in heights if not is_land_height(img.get(*p))]
        if bad:
            raise ValueError("heights painted on the sea at %d, %d - the brush changes land only" % bad[0])
        plan.binary(path, patched(path, {p: (v, v, v) for p, v in heights.items()}))
        up = sum(1 for p, v in heights.items() if v > img.get(*p)[0])
        plan.notes.append((mod.rel(path), "%d pixel(s) of land: %d raised, %d lowered" % (
            len(heights), up, len(heights) - up)))
        hgt = os.path.join(os.path.dirname(path), "map_heights.hgt")
        if os.path.isfile(hgt):
            step = max_land_height(mod, campaign) / 255.0
            plan.binary(hgt, hgt_patched(hgt, img, {p: (img.get(*p)[0], v) for p, v in heights.items()}, step))
            plan.notes.append((mod.rel(hgt), "the same %d pixel(s) changed (the game reads this copy of the heights "
                                             "while it is there; %.2f per grey step)" % (len(heights), step)))
    for folder in {os.path.dirname(mod.campaign_file(campaign, "map_regions.tga")),
                   os.path.join(mod.data, "world", "maps", "base")}:
        plan.delete(os.path.join(folder, "map.rwm"), "the game builds the map again from the changed pictures")


__all__ = ["GROUND", "SEA", "FEATURES", "LAND_BRUSHES", "SEA_BRUSHES", "FEATURE_BRUSHES", "paint_problem",
           "river_warnings", "river_shapes", "river_path", "climates", "HEIGHT_TOOLS", "is_land_height", "height_spray", "max_land_height", "hgt_patched",
           "apply"]
