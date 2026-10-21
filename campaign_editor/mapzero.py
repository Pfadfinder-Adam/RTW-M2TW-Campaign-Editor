"""A campaign map from zero (the user, 2026-10-21: 'a map from zero: one region, one town, a port, a resource; the
faction France in Medieval II, the Gauls in Rome'): a small island in the sea, ONE region with its town, a port on
its coast and one resource, owned by one faction (its own capital region's names, rebels and resources kept, so
every text the game looks up is there), the rebels with one army - the start of a new map the modder grows himself.

Everything is written into the mod's campaign folder (the game reads the campaign folder before world/maps/base,
both games; editor-notes mapzero_facts.md has every rule with the engine source's lines): the map pictures at their
sizes for W x H (tiles / corners 2W+1 x 2H+1 / double), map_heights.hgt, descr_terrain.txt, descr_regions.txt,
descr_strat.txt, the win conditions, the mercenaries, an empty descr_events.txt; map.rwm removed (the game builds a
new one). Through a Plan: a backup first, Restore puts every byte back."""

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


def _tga(im):
    """24-bit uncompressed TGA bytes, bottom-up rows (the games' own; 0x18 / 0x20 descriptors crashed Medieval II)."""
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="TGA", rle=False, orientation=-1)
    return buf.getvalue()


def _text(s):
    return s.replace("\r\n", "\n").replace("\n", "\r\n").encode("latin-1")


def _land_tile(x, y):
    x0, y0, x1, y1 = LAND
    return x0 <= x <= x1 and y0 <= y <= y1


def _land_point(px, py):
    """A corner point (map_heights / ground / climates) on the land: inside the land block's corners."""
    x0, y0, x1, y1 = LAND
    return 2 * x0 <= px <= 2 * x1 + 2 and 2 * y0 <= py <= 2 * y1 + 2


def _ring(px, py):
    """Points in from the land block's edge (0 = its edge)."""
    x0, y0, x1, y1 = LAND
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


def pictures(W, H, region, land_ground, land_climate, sea_climate):
    """{name: Pillow picture} of the new map (rows top-down as Pillow keeps them; written bottom-up)."""
    from PIL import Image
    pw, ph = 2 * W + 1, 2 * H + 1
    out = {}

    def tiles(colour_at, w=W, h=H):
        im = Image.new("RGB", (w, h))
        im.putdata([colour_at(x, h - 1 - r) for r in range(h) for x in range(w)])
        return im

    def regions(x, y):
        if (x, y) == TOWN:
            return TOWN_PX
        if (x, y) == PORT:
            return PORT_PX
        return region if _land_tile(x, y) else SEA_REGION
    out["map_regions.tga"] = tiles(regions)

    def heights(px, py):
        if not _land_point(px, py):
            return SEA_BLUE
        g = {0: 4, 1: 8, 2: 12}.get(_ring(px, py), 16)          # a low shore rising inland (grey >= 1: land)
        return (g, g, g)
    out["map_heights.tga"] = tiles(heights, pw, ph)

    def ground(px, py):
        if _land_point(px, py):
            return land_ground
        x0, y0, x1, y1 = LAND
        near = 2 * x0 - 3 <= px <= 2 * x1 + 5 and 2 * y0 - 3 <= py <= 2 * y1 + 5
        return SHALLOW if near else DEEP
    out["map_ground_types.tga"] = tiles(ground, pw, ph)
    out["map_climates.tga"] = tiles(lambda px, py: land_climate if _land_point(px, py) else sea_climate, pw, ph)
    out["map_fog.tga"] = tiles(lambda px, py: (255, 255, 255), pw, ph)
    out["map_features.tga"] = tiles(lambda x, y: (0, 0, 0))
    out["map_trade_routes.tga"] = tiles(lambda x, y: (0, 0, 0))

    def rough(qx, qy):
        x0, y0, x1, y1 = LAND
        return (4, 4, 4) if 2 * x0 <= qx <= 2 * x1 + 1 and 2 * y0 <= qy <= 2 * y1 + 1 else (0, 0, 0)
    out["map_roughness.tga"] = tiles(rough, 2 * W, 2 * H)
    radar = tiles(lambda x, y: (96, 140, 70) if _land_tile(x, y) else (40, 80, 150))
    out["radar_map1.tga"] = radar
    out["radar_map2.tga"] = radar.resize((2 * W, 2 * H))
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


def _region_text(mod, campaign, region, faction):
    """The faction's capital region's own block (its names are in the text files), the faction its creator."""
    from .moddata import region_entries
    f = mod.load(mod.campaign_file(campaign, "descr_regions.txt"))
    e = region_entries(f)[region]
    keys = ["settlement", "creator", "rebels", "colour", "resources", "triumph", "farming"]
    vals = {k: v for k, (_, v) in e.items()}
    vals["creator"] = faction
    lines = [region] + ["\t" + vals[k] for k in keys if vals.get(k)]
    for k in ("religions", "beliefs"):
        if vals.get(k):
            lines.append("\t" + (vals[k] if vals[k].lstrip().startswith(k) else "%s %s" % (k, vals[k])))
    return "\n".join(lines) + "\n"


def _swap_xy(line, xy):
    return re.sub(r"x\s*\d+\s*,\s*y\s*\d+", "x %d, y %d" % xy, line, count=1)


def _strat_text(mod, campaign, faction, region, resource, rome):
    from .strat import Strat
    old = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
    lines = old.lines
    fb, sb = old.faction(faction), old.faction("slave")
    if fb is None:
        raise ValueError("%s is not in this campaign's descr_strat.txt" % faction)
    first = min(x.start for x in old.factions)
    head, skip = [], None
    for i, l in enumerate(lines[:first]):
        h = (tokens(strip_comment(l)) or [""])[0]
        if h in ("playable", "unlockable", "nonplayable"):
            head.append(l)
            head += ["\t%s" % faction] if h == "playable" else (["\tslave"] if h == "nonplayable" else [])
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
    head.append("resource\t%s,\t%d,\t%d" % ((resource,) + RESOURCE))
    head.append("")

    def block_top(b):
        stop = min([s.start for s in b.settlements] + [c.start for c in b.characters] + [b.end])
        return [l for l in lines[b.start:stop] if (tokens(strip_comment(l)) or [""])[0] not in ("fort", "watchtower")]
    out = head + block_top(fb)
    st = fb.settlements[0]
    for l in lines[st.start:st.end]:
        t = tokens(strip_comment(l))
        out.append(re.sub(r"(\bregion\s+)\S+", lambda m: m.group(1) + region, l) if t[:1] == ["region"] else l)
    leader = next((c for c in fb.characters if c.role == "leader"), None) or next(
        (c for c in fb.characters if c.named), None) or (fb.characters[0] if fb.characters else None)
    if leader is None:
        raise ValueError("%s has no character in descr_strat.txt to lead it" % faction)
    out.append(_swap_xy(lines[leader.start], TOWN))
    out += _first_units(lines[leader.start + 1:leader.end], 4)
    out.append("")
    other = next((c for c in fb.characters if c is not leader and c.named), None)
    rebel_name = (other.name if other else leader.name).replace("sub_faction", "").strip()
    if sb is not None:
        out += block_top(sb)
        rc = next((c for c in sb.characters if any(tokens(l)[:1] == ["army"] for l in lines[c.start:c.end])),
                  sb.characters[0] if sb.characters else None)
        if rc is not None:
            line = _swap_xy(lines[rc.start], REBELS)
            line = re.sub(r"(sub_faction\s+)\w+(\s*,\s*)[^,]+", lambda m: m.group(1) + faction + m.group(2) +
                          rebel_name, line, count=1)
            out.append(line)
            out += _first_units(lines[rc.start + 1:rc.end], 2)
        out.append("")
    if rome:
        out += ["core_attitudes\t%s,\t600\t\tslave" % faction,
                "faction_relationships\t%s,\t600\t\tslave" % faction,
                "faction_relationships\tslave,\t600\t\t%s" % faction]
    else:
        out += ["faction_standings\t%s,\t\t-1.0\tslave" % faction,
                "faction_relationships\t%s, at_war_with\tslave" % faction]
    return "\n".join(out) + "\n"


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


def _mercenaries(mod, campaign, region):
    """One pool for the region: the units of the pool it was in (else the file's first unit)."""
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
    return "pool New_Map\n\tregions %s\n" % region + "".join("\t%s\n" % u for u in units)


def _music_text(lines, region):
    """descr_sounds_music_types.txt with every 'regions' line keeping only the map's region (a line left with none
    is taken out); the music types themselves stay."""
    out, given = [], False
    for l in lines:
        t = tokens(strip_comment(l))
        if t[:1] == ["regions"]:
            if region in t[1:] and not given:
                out.append(l[:len(l) - len(l.lstrip())] + "regions " + region)
                given = True
            continue
        out.append(l)
    return "\n".join(out) + "\n"


def make(plan, campaign, faction=None, size=SIZE):
    """The new map into plan (its mod's campaign folder). Returns the region's name."""
    from .limits import game_kind
    from .upscale import hgt_from_picture
    from . import terrain
    mod = plan.mod
    rome = game_kind(mod) == "rome"
    faction = faction or DEFAULT_FACTION["rome" if rome else "medieval2"]
    W, H = size
    if W < LAND[2] + 5 or H < LAND[3] + 5:
        raise ValueError("the map needs at least %d x %d tiles (sea round the island)" % (LAND[2] + 5, LAND[3] + 5))
    from .strat import Strat
    fb = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).faction(faction)
    if fb is None or not fb.settlements:
        raise ValueError("%s has no town in this campaign to take its region's names from" % faction)
    region = fb.settlements[0].region
    info = mod.regions(campaign)[region]
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
    pics = pictures(W, H, info["colour"], land_ground, land_climate, sea_climate)
    for name, im in pics.items():
        if name == "map_fog.tga" and rome:
            continue                                    # Rome has no fog picture
        if name == "map_trade_routes.tga" and not mod.campaign_file(campaign, name):
            continue
        plan.binary(os.path.join(folder, name), _tga(im))
    top, low = terrain.max_land_height(mod, campaign), terrain.min_sea_height(mod, campaign)
    plan.binary(os.path.join(folder, "map_heights.hgt"), hgt_from_picture(_tga(pics["map_heights.tga"]), top, low))
    texts = {
        "descr_terrain.txt": _terrain_text(mod, campaign, W, H),
        "descr_regions.txt": _region_text(mod, campaign, region, faction),
        "descr_strat.txt": _strat_text(mod, campaign, faction, region, _resource(mod, campaign), rome),
        "descr_win_conditions.txt": "%s\nhold_regions %s\ntake_regions 2\n%s" % (
            faction, region, "" if rome else "short_campaign hold_regions %s\ntake_regions 2\n" % region),
        "descr_events.txt": "",
        "descr_mercenaries.txt": _mercenaries(mod, campaign, region),
    }
    music = mod.campaign_file(campaign, "descr_sounds_music_types.txt")
    if music:                                           # Medieval II: its regions lines name only this map's region
        texts["descr_sounds_music_types.txt"] = _music_text(mod.load(music).texts(), region)
    if mod.campaign_file(campaign, "descr_regions_and_settlement_name_lookup.txt"):
        texts["descr_regions_and_settlement_name_lookup.txt"] = "%s\n%s\n" % (region, info["settlement"])
    for name, text in texts.items():
        plan.binary(os.path.join(folder, name), _text(text))
    for d in (folder, os.path.join(mod.data, "world", "maps", "base")):
        rwm = os.path.join(d, "map.rwm")
        if os.path.exists(rwm):
            plan.delete(rwm, "the game builds the map anew from the new pictures")
    plan.note(None, "a new map from zero: %d x %d tiles, one region %s (town %s at %d, %d, a port at %d, %d, %s at "
                    "%d, %d), %s's, the rebels with one army; the campaign's other factions are not in it" % (
                        W, H, region, info["settlement"], TOWN[0], TOWN[1], PORT[0], PORT[1],
                        _resource(mod, campaign), RESOURCE[0], RESOURCE[1], faction))
    if rome:
        plan.warn(None, "Rome: with fewer than 5 factions alive the Faction Rankings 'Top 5' view crashes the game "
                        "(the engine's own loop) - do not pick it until the map has 5 factions")
    else:
        plan.warn(None, "Medieval II: modders say the game wants 10 regions or more (not found in the engine's "
                        "code) - try it; if it does not load, add regions")
    return region


__all__ = ["make", "pictures", "SIZE"]
