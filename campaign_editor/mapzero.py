"""A campaign map from zero (the user, 2026-10-21: 'a map from zero: one region, one town, a port, a resource; the
faction France in Medieval II, the Gauls in Rome'): a small island in the sea, ONE region with its town, a port on
its coast and one resource, owned by one faction (its own capital region's names, rebels and resources kept, so
every text the game looks up is there), the rebels with one army - the start of a new map the modder grows himself.

Everything is written into the mod's campaign folder (the game reads the campaign folder before world/maps/base,
both games; editor-notes mapzero_facts.md has every rule with the engine source's lines): the map pictures at their
sizes for W x H (tiles / corners 2W+1 x 2H+1 / double), map_heights.hgt, descr_terrain.txt, descr_regions.txt,
descr_strat.txt, the win conditions, the mercenaries, an empty descr_events.txt, water_surface.tga (the sea's colour
picture, stretched over the whole map - the old one left the old coasts showing in the new sea); map.rwm removed (the
game builds a new one). Through a Plan: a backup first, Restore puts every byte back."""

import io
import os
import re

from .textio import strip_comment, tokens

SIZE = (32, 24)                     # tiles; the land block below sits in the middle, 4+ sea tiles round it
LAND = (10, 7, 21, 16)              # x0, y0, x1, y1 (tiles, y from the map's bottom - as descr_strat counts)
TOWN, PORT, RESOURCE, REBELS = (15, 12), (21, 12), (13, 10), (13, 14)
SEA_REGION, TOWN_PX, PORT_PX = (41, 140, 233), (0, 0, 0), (255, 255, 255)
SEA_BLUE, SHALLOW, DEEP = (0, 0, 253), (196, 0, 0), (128, 0, 0)
DEFAULT_FACTION = {"rome": "gauls", "medieval2": "france"}
OPEN_SEA = {"rome": (60, 132, 159), "medieval2": (97, 227, 255)}   # the vanilla water_surface.tga's most common colour
WATER_SIZE = (256, 256)             # the games' own water_surface.tga size (a texture: power of two)


def layout(W, H, n=1):
    """Where everything stands: {'land': (x0, y0, x1, y1), 'cells': [{'rect', 'town'}] (one a region - the first is
    the main faction's, with the port), 'port', 'resource', 'rebels'}. One region: the island above; more: the
    island cut into rows of regions, each 5 x 5 tiles or more, its town in its middle (a town needs its own land all
    round - Medieval II stops when a town or port touches another region, even at a corner)."""
    import math
    if n <= 1:
        cells = [{"rect": LAND, "town": TOWN}]
        out = {"land": LAND, "cells": cells, "port": PORT, "resource": RESOURCE, "rebels": REBELS}
    else:
        cols = int(math.ceil(math.sqrt(n)))
        rows = int(math.ceil(n / float(cols)))
        lw, lh = cols * 5, rows * 5
        x0, y0 = (W - lw) // 2, (H - lh) // 2
        land = (x0, y0, x0 + lw - 1, y0 + lh - 1)
        cells, left = [], n
        for r in range(rows):                           # from the top row down: the first region top right
            in_row = min(cols, left - (rows - r - 1)) if r < rows - 1 else left
            in_row = max(1, min(cols, in_row))
            ry1 = land[3] - r * 5
            ry0 = ry1 - 4
            widths = [lw // in_row] * in_row
            widths[-1] += lw - sum(widths)
            x = land[0]
            row = []
            for w in widths:
                rect = (x, ry0, x + w - 1, ry1)
                row.append({"rect": rect, "town": (x + w // 2, ry0 + 2)})
                x += w
            cells += row[::-1]                          # the east-most first: the port's region
            left -= in_row
        main = cells[0]
        tx, ty = main["town"]
        rx0, ry0, rx1, ry1 = main["rect"]
        out = {"land": land, "cells": cells, "port": (rx1, ty), "resource": (rx0 + 1, ry0 + 1),
               "rebels": (tx, ty - 2)}
    x0, y0, x1, y1 = out["land"]
    if x0 < 5 or y0 < 5 or x1 > W - 6 or y1 > H - 6:
        raise ValueError("the map needs at least %d x %d tiles for %d region(s) (sea round the island)" % (
            x1 - x0 + 11, y1 - y0 + 11, n))
    return out


def _tga(im):
    """24-bit uncompressed TGA bytes, bottom-up rows (the games' own; 0x18 / 0x20 descriptors crashed Medieval II)."""
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="TGA", rle=False, orientation=-1)
    return buf.getvalue()


def _text(s):
    return s.replace("\r\n", "\n").replace("\n", "\r\n").encode("latin-1")


def _land_tile(x, y, land=LAND):
    x0, y0, x1, y1 = land
    return x0 <= x <= x1 and y0 <= y <= y1


def _land_point(px, py, land=LAND):
    """A corner point (map_heights / ground / climates) on the land: inside the land block's corners."""
    x0, y0, x1, y1 = land
    return 2 * x0 <= px <= 2 * x1 + 2 and 2 * y0 <= py <= 2 * y1 + 2


def _ring(px, py, land=LAND):
    """Points in from the land block's edge (0 = its edge)."""
    x0, y0, x1, y1 = land
    return min(px - 2 * x0, 2 * x1 + 2 - px, py - 2 * y0, 2 * y1 + 2 - py)


def _sample(mod, campaign, name, xy, corners=True):
    """The colour of an old map picture at a tile (its centre point on a corner picture), or None."""
    try:
        from .tga import read_tga
        path = mod.campaign_file(campaign, name)
        if not path:
            return None
        im = read_tga(path)
        x, y = xy
        px, py = (2 * x + 1, 2 * y + 1) if corners else (x, y)
        return tuple(im.get(px, py)[:3])                # tga.Image counts rows from the bottom, as the map does
    except Exception:
        return None


def _open_sea(mod, campaign, rome):
    """The old water_surface.tga's most common colour (its open sea), or the game's vanilla one."""
    try:
        from collections import Counter
        from .tga import read_tga
        path = mod.campaign_file(campaign, "water_surface.tga")
        if path:
            im = read_tga(path)
            seen = Counter(tuple(im.get(x, y)[:3]) for y in range(0, im.height, 2) for x in range(0, im.width, 2))
            if seen:
                return seen.most_common(1)[0][0]
    except Exception:
        pass
    return OPEN_SEA["rome" if rome else "medieval2"]


def pictures(W, H, region, land_ground, land_climate, sea_climate, lay=None, sea_colour=OPEN_SEA["medieval2"]):
    """{name: Pillow picture} of the new map (rows top-down as Pillow keeps them; written bottom-up); region: the one
    region's colour, or a list of colours, one for each of lay's cells; sea_colour: water_surface.tga's one colour."""
    from PIL import Image
    lay = lay or layout(W, H, 1)
    land = lay["land"]
    colours = region if isinstance(region, list) else [region]
    towns = {c["town"] for c in lay["cells"]}
    pw, ph = 2 * W + 1, 2 * H + 1
    out = {}

    def tiles(colour_at, w=W, h=H):
        im = Image.new("RGB", (w, h))
        im.putdata([colour_at(x, h - 1 - r) for r in range(h) for x in range(w)])
        return im

    def regions(x, y):
        if (x, y) in towns:
            return TOWN_PX
        if (x, y) == lay["port"]:
            return PORT_PX
        if not _land_tile(x, y, land):
            return SEA_REGION
        for c, colour in zip(lay["cells"], colours):
            cx0, cy0, cx1, cy1 = c["rect"]
            if cx0 <= x <= cx1 and cy0 <= y <= cy1:
                return colour
        return colours[0]
    out["map_regions.tga"] = tiles(regions)

    def heights(px, py):
        if not _land_point(px, py, land):
            return SEA_BLUE
        g = {0: 4, 1: 8, 2: 12}.get(_ring(px, py, land), 16)          # a low shore rising inland (grey >= 1: land)
        return (g, g, g)
    out["map_heights.tga"] = tiles(heights, pw, ph)

    def ground(px, py):
        if _land_point(px, py, land):
            return land_ground
        x0, y0, x1, y1 = land
        near = 2 * x0 - 3 <= px <= 2 * x1 + 5 and 2 * y0 - 3 <= py <= 2 * y1 + 5
        return SHALLOW if near else DEEP
    out["map_ground_types.tga"] = tiles(ground, pw, ph)
    out["map_climates.tga"] = tiles(lambda px, py: land_climate if _land_point(px, py, land) else sea_climate, pw, ph)
    out["map_fog.tga"] = tiles(lambda px, py: (255, 255, 255), pw, ph)
    out["map_features.tga"] = tiles(lambda x, y: (0, 0, 0))
    out["map_trade_routes.tga"] = tiles(lambda x, y: (0, 0, 0))

    def rough(qx, qy):
        x0, y0, x1, y1 = land
        return (4, 4, 4) if 2 * x0 <= qx <= 2 * x1 + 1 and 2 * y0 <= qy <= 2 * y1 + 1 else (0, 0, 0)
    out["map_roughness.tga"] = tiles(rough, 2 * W, 2 * H)
    radar = tiles(lambda x, y: (96, 140, 70) if _land_tile(x, y, land) else (40, 80, 150))
    out["radar_map1.tga"] = radar
    out["radar_map2.tga"] = radar.resize((2 * W, 2 * H))
    # the sea's colour picture (sea_plane.cpp, validate_file_path: the campaign folder, then base), stretched over the
    # whole map whatever its size: the old map's kept its coasts and deeps in the new sea (the user, 2026-10-22)
    out["water_surface.tga"] = Image.new("RGB", WATER_SIZE, tuple(sea_colour))
    return out


def _terrain_text(mod, campaign, W, H):
    path = mod.campaign_file(campaign, "descr_terrain.txt")
    text = None
    if path:
        with open(path, encoding="latin-1") as fh:
            text = fh.read()
    text = text or (
        "dimensions\n{\n\twidth  %d\n\theight  %d\n}\nheights\n{\n\tmin_sea_height  -3122.256\n\tmax_land_height  "
        "7511.272\n}\nroughness\n{\n\tmin  50.000\n\tmax  200.000\n}\nfractal\n{\n\tmultiplier  0.500\n}\nlattitude\n"
        "{\n\tmin  22.000\n\tmax  56.000\n}\n" % (W, H))
    text = re.sub(r"(\bwidth\s+)\d+", lambda m: m.group(1) + str(W), text, count=1)
    return re.sub(r"(\bheight\s+)\d+", lambda m: m.group(1) + str(H), text, count=1)


def pick_regions(mod, campaign, main, others=0, n=1):
    """[(region, owner)] of the new map: the main faction's capital first, then each other faction's capital (the
    first `others` factions of the campaign with a town and a leader), the rest the rebels' (the campaign's other
    regions - their names are in the text files). n regions in all."""
    from .strat import Strat
    st = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))

    def leads(fb):
        return fb is not None and fb.settlements and any(c.named for c in fb.characters)
    if not leads(st.faction(main)):
        raise ValueError("%s has no town and leader in this campaign to take its region's names from" % main)
    owners = [main] + [fb.name for fb in st.factions if fb.name not in (main, "slave") and leads(fb)][:max(0, others)]
    out, taken = [], set()
    for f in owners[:max(1, n)]:
        r = st.faction(f).settlements[0].region
        out.append((r, f))
        taken.add(r)
    sb = st.faction("slave")
    rebel_owner = "slave" if sb is not None and sb.settlements else main
    rebel_towns = [st_.region for st_ in sb.settlements] if sb is not None else []
    for r in rebel_towns + list(mod.regions(campaign)):    # the rebels' own towns first
        if len(out) >= n:
            break
        if r not in taken and not mod.regions(campaign)[r].get("wasteland"):
            out.append((r, rebel_owner))
            taken.add(r)
    return out


def _region_text(mod, campaign, picked, main):
    """The picked regions' own blocks (their names are in the text files), each its owner its creator (the rebels'
    the main faction - the rebels may not create a region)."""
    from .moddata import region_entries
    f = mod.load(mod.campaign_file(campaign, "descr_regions.txt"))
    entries = region_entries(f)
    keys = ["settlement", "creator", "rebels", "colour", "resources", "triumph", "farming"]
    blocks = []
    for region, owner in picked:
        vals = {k: v for k, (_, v) in entries[region].items()}
        vals["creator"] = owner if owner != "slave" else main
        lines = [region] + ["\t" + vals[k] for k in keys if vals.get(k)]
        for k in ("religions", "beliefs"):
            if vals.get(k):
                lines.append("\t" + (vals[k] if vals[k].lstrip().startswith(k) else "%s %s" % (k, vals[k])))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def _swap_xy(line, xy):
    return re.sub(r"x\s*\d+\s*,\s*y\s*\d+", "x %d, y %d" % xy, line, count=1)


def _port_chain(chain):
    """A chain whose building stands in the port (Rome's port_buildings, Medieval II's port / castle_port)."""
    c = chain.lower()
    return c in ("port_buildings", "port", "castle_port") or c.startswith("port_") or c.endswith("_port")


def _drop_port_buildings(block):
    """The settlement's lines without its port buildings' blocks (building { type <port chain> <level> }): its
    region has no port on the new map (the tester, 2026-10-22: 'Settlement specifies port, but this region is not
    allowed a port')."""
    out, i = [], 0
    while i < len(block):
        if (tokens(strip_comment(block[i])) or [""])[0] == "building":
            j, typ = i + 1, None
            while j < len(block):
                t = tokens(strip_comment(block[j]))
                if t[:1] == ["type"] and len(t) > 1:
                    typ = t[1]
                if t[:1] == ["}"]:
                    break
                j += 1
            if typ and _port_chain(typ):
                i = j + 1
                continue
        out.append(block[i])
        i += 1
    return out


def _settlement(lines, st, region, creator, port=True):
    """A settlement block copied with its region and its creator changed; port False: its port buildings left out
    (its region has no port on the new map)."""
    out = []
    for l in (lines[st.start:st.end] if port else _drop_port_buildings(lines[st.start:st.end])):
        t = tokens(strip_comment(l))
        if t[:1] == ["region"]:
            l = re.sub(r"(\bregion\s+)\S+", lambda m: m.group(1) + region, l)
        elif t[:1] == ["faction_creator"]:
            l = re.sub(r"(\bfaction_creator\s+)\S+", lambda m: m.group(1) + creator, l)
        out.append(l)
    return out


def _strat_text(mod, campaign, main, picked, lay, resource, rome):
    from .strat import Strat
    old = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
    lines = old.lines
    sb = old.faction("slave")
    factions = []
    for _, owner in picked:
        if owner != "slave" and owner not in factions:
            factions.append(owner)
    first = min(x.start for x in old.factions)
    head, skip = [], None
    for l in lines[:first]:
        h = (tokens(strip_comment(l)) or [""])[0]
        if h in ("playable", "unlockable", "nonplayable"):
            head.append(l)
            head += (["\t%s" % main] if h == "playable" else
                     ["\t%s" % f for f in factions[1:]] + ["\tslave"] if h == "nonplayable" else [])
            skip = h
            continue
        if skip:
            if h == "end":
                head.append(l)
                skip = None
            continue
        if h in ("resource", "landmark", "fort", "watchtower"):
            continue
        head.append(l)
    head.append("resource\t%s,\t%d,\t%d" % ((resource,) + lay["resource"]))
    head.append("")

    def block_top(b):
        stop = min([s.start for s in b.settlements] + [c.start for c in b.characters] + [b.end])
        return [l for l in lines[b.start:stop] if (tokens(strip_comment(l)) or [""])[0] not in ("fort", "watchtower")]
    towns = {r: c["town"] for (r, _), c in zip(picked, lay["cells"])}
    out = list(head)
    for f in factions:
        fb = old.faction(f)
        out += block_top(fb)
        mine = [r for r, o in picked if o == f]
        for r in mine:
            out += _settlement(lines, fb.settlements[0], r, f, port=r == picked[0][0])
        leader = next((c for c in fb.characters if c.role == "leader"), None) or next(
            (c for c in fb.characters if c.named), None)
        out.append(_swap_xy(lines[leader.start], towns[mine[0]]))
        out += _first_units(lines[leader.start + 1:leader.end], 4)
        out.append("")
    if sb is not None:
        mfb = old.faction(main)
        leader = next((c for c in mfb.characters if c.role == "leader"), None) or next(
            (c for c in mfb.characters if c.named), None)
        other = next((c for c in mfb.characters if c is not leader and c.named), None)
        rebel_name = (other.name if other else leader.name).replace("sub_faction", "").strip()
        out += block_top(sb)
        for r in [r for r, o in picked if o == "slave"]:
            out += _settlement(lines, sb.settlements[0], r, main, port=r == picked[0][0])
        rc = next((c for c in sb.characters if any(tokens(l)[:1] == ["army"] for l in lines[c.start:c.end])),
                  sb.characters[0] if sb.characters else None)
        if rc is not None:
            line = _swap_xy(lines[rc.start], lay["rebels"])
            line = re.sub(r"(sub_faction\s+)\w+(\s*,\s*)[^,]+", lambda m: m.group(1) + main + m.group(2) +
                          rebel_name, line, count=1)
            out.append(line)
            out += _first_units(lines[rc.start + 1:rc.end], 2)
        out.append("")
    for f in factions:
        if rome:
            out += ["core_attitudes\t%s,\t600\t\tslave" % f,
                    "faction_relationships\t%s,\t600\t\tslave" % f,
                    "faction_relationships\tslave,\t600\t\t%s" % f]
        else:
            out += ["faction_standings\t%s,\t\t-1.0\tslave" % f,
                    "faction_relationships\t%s, at_war_with\tslave" % f]
    return "\n".join(out) + "\n"


def _wins_text(picked, rome):
    """Each faction: hold its own regions, take them all (one region: 2 - never won at the start)."""
    out, n = [], len(picked)
    for f in [o for i, (_, o) in enumerate(picked) if o != "slave" and o not in [x for _, x in picked[:i]]]:
        hold = " ".join(r for r, o in picked if o == f)
        take = max(2, n)
        out.append("%s\nhold_regions %s\ntake_regions %d\n%s" % (
            f, hold, take, "" if rome else "short_campaign hold_regions %s\ntake_regions %d\n" % (hold, take)))
    return "\n".join(out)


def _first_units(block, most):
    """A character's lines after his own: traits / ancillaries kept, 'army' and its first `most` units."""
    out, n = [], 0
    for l in block:
        t = tokens(strip_comment(l))
        if t[:1] == ["unit"]:
            if n < most:
                out.append(l)
            n += 1
        elif t[:1] in (["character"], ["relative"], ["character_record"]):
            break
        elif t:
            out.append(l)
    return out


def _resource(mod, campaign):
    """A resource the campaign's map already uses (it is a known type there)."""
    f = mod.load(mod.campaign_file(campaign, "descr_strat.txt"))
    for l in f.texts():
        t = tokens(strip_comment(l).replace(",", " "))
        if t[:1] == ["resource"] and len(t) > 1:
            return t[1]
    return "wine"


def _mercenaries(mod, campaign, region, regions=None):
    """One pool for the map's regions: the units of the pool the main region was in (else the file's first unit)."""
    path = mod.campaign_file(campaign, "descr_mercenaries.txt")
    units, first, mine = [], None, False
    if path:
        for l in mod.load(path).texts():
            t = tokens(strip_comment(l))
            if t[:1] == ["pool"]:
                if mine and units:
                    break
                mine, units = False, []
            elif t[:1] == ["regions"]:
                mine = region in t[1:]
            elif t[:1] == ["unit"]:
                first = first or strip_comment(l).strip()
                units.append(strip_comment(l).strip())
    if not mine:
        units = [first] if first else []
    return "pool New_Map\n\tregions %s\n" % " ".join(regions or [region]) + "".join("\t%s\n" % u for u in units)


def _music_text(lines, regions):
    """descr_sounds_music_types.txt with every 'regions' line keeping only the map's regions, each once (a line left
    with none is taken out); the music types themselves stay."""
    out, given = [], set()
    for l in lines:
        t = tokens(strip_comment(l))
        if t[:1] == ["regions"]:
            keep = [r for r in t[1:] if r in regions and r not in given]
            if keep:
                out.append(l[:len(l) - len(l.lstrip())] + "regions " + " ".join(keep))
                given.update(keep)
            continue
        out.append(l)
    return "\n".join(out) + "\n"


def make(plan, campaign, faction=None, size=SIZE, regions=1, others=0):
    """The new map into plan (its mod's campaign folder): `regions` regions, the main faction's and `others` other
    factions' capitals among them, the rest the rebels'. Returns the main region's name."""
    from .limits import game_kind
    from .upscale import hgt_from_picture
    from . import terrain
    mod = plan.mod
    rome = game_kind(mod) == "rome"
    faction = faction or DEFAULT_FACTION["rome" if rome else "medieval2"]
    W, H = size
    regions = max(1, int(regions))
    grown = False
    for _ in range(200):                                # a map too small for the regions grows to fit (sea round)
        try:
            lay = layout(W, H, regions)
            break
        except ValueError:
            if regions == 1:
                raise
            W, H, grown = W + 1, H + 1, True
    picked = pick_regions(mod, campaign, faction, others, regions)
    if len(picked) < regions:
        raise ValueError("the campaign has %d region(s) to take names from, %d asked" % (len(picked), regions))
    info = mod.regions(campaign)
    region = picked[0][0]
    try:
        old_town = mod.city_tiles(campaign).get(region)
    except Exception:
        old_town = None
    land_ground = (old_town and _sample(mod, campaign, "map_ground_types.tga", old_town)) or terrain.NEW_LAND_GROUND
    if land_ground in (SHALLOW, DEEP, (64, 0, 0)):
        land_ground = terrain.NEW_LAND_GROUND
    land_climate = (old_town and _sample(mod, campaign, "map_climates.tga", old_town)) or \
        next((c for _, c, _ in terrain.climates(mod)), (237, 20, 91))
    sea_climate = _sample(mod, campaign, "map_climates.tga", (0, 0)) or land_climate
    folder = mod.own(mod.campaign_dir(campaign)) if hasattr(mod, "own") else mod.campaign_dir(campaign)
    pics = pictures(W, H, [info[r]["colour"] for r, _ in picked], land_ground, land_climate, sea_climate, lay,
                    _open_sea(mod, campaign, rome))
    for name, im in pics.items():
        if name == "map_fog.tga" and rome:
            continue                                    # Rome has no fog picture
        if name == "map_trade_routes.tga" and not mod.campaign_file(campaign, name):
            continue
        plan.binary(os.path.join(folder, name), _tga(im))
    top, low = terrain.max_land_height(mod, campaign), terrain.min_sea_height(mod, campaign)
    plan.binary(os.path.join(folder, "map_heights.hgt"), hgt_from_picture(_tga(pics["map_heights.tga"]), top, low))
    names = [r for r, _ in picked]
    resource = _resource(mod, campaign)
    texts = {
        "descr_terrain.txt": _terrain_text(mod, campaign, W, H),
        "descr_regions.txt": _region_text(mod, campaign, picked, faction),
        "descr_strat.txt": _strat_text(mod, campaign, faction, picked, lay, resource, rome),
        "descr_win_conditions.txt": _wins_text(picked, rome),
        "descr_events.txt": "",
        "descr_mercenaries.txt": _mercenaries(mod, campaign, region, names),
    }
    music = mod.campaign_file(campaign, "descr_sounds_music_types.txt")
    if music:                                           # Medieval II: its regions lines name only this map's regions
        texts["descr_sounds_music_types.txt"] = _music_text(mod.load(music).texts(), set(names))
    if mod.campaign_file(campaign, "descr_regions_and_settlement_name_lookup.txt"):
        texts["descr_regions_and_settlement_name_lookup.txt"] = "".join(
            "%s\n%s\n" % (r, info[r]["settlement"]) for r in names)
    for name, text in texts.items():
        plan.binary(os.path.join(folder, name), _text(text))
    for d in (folder, os.path.join(mod.data, "world", "maps", "base")):
        rwm = os.path.join(d, "map.rwm")
        if os.path.exists(rwm):
            plan.delete(rwm, "the game builds the map anew from the new pictures")
    owners = sorted({o for _, o in picked if o != "slave"})
    if grown:
        plan.note(None, "the map made %d x %d tiles: room for %d regions with sea round them" % (W, H, regions))
    plan.note(None, "a new map from zero: %d x %d tiles, %d region(s) (%s), factions %s and the rebels; a port at "
                    "%d, %d, %s at %d, %d; the campaign's other factions are not in it" % (
                        W, H, len(picked), ", ".join("%s (%s)" % p for p in picked), ", ".join(owners),
                        lay["port"][0], lay["port"][1], resource, lay["resource"][0], lay["resource"][1]))
    if rome and len(owners) < 5:
        plan.warn(None, "Rome: with fewer than 5 factions alive the Faction Rankings 'Top 5' view crashes the game "
                        "(the engine's own loop reads past its list) - do not pick it, or make the map with 5 factions")
    if rome:                                            # the engine source: END_CAMPAIGN_SCROLL, < 50 regions
        plan.note(None, "Rome: on a map of fewer than 50 regions (the sea's counted) the campaign's victory scroll "
                        "ends the game instead of offering to play on - not a crash")
    return region


__all__ = ["make", "pictures", "layout", "pick_regions", "SIZE"]
