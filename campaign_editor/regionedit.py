"""New regions and region borders.

A region is, for the game:
  * an area of its own colour in map_regions.tga, with its town pixel (black)
    and maybe a port pixel (white, on the coast);
  * eight lines in descr_regions.txt: name, settlement, creator faction,
    rebels, colour r g b, resources, triumph value, farming level;
  * its name and its settlement's name in the campaign's
    descr_regions_and_settlement_name_lookup.txt (appended: the existing lines
    keep their places) and labels {Name} in data/text/<campaign>_regions_and_settlement_names.txt;
  * optionally a settlement block in descr_strat.txt - without one the game
    makes it a rebel village.
The compiled map map.rwm is removed so the game rebuilds it.

painted = {(x, y): region} gives tiles to regions (new or old); only land
tiles can change hands, never a town or port pixel."""

import os
import re

from .mapedit import CITY, PORT
from .moddata import religions_line
from .strat import Strat, village_block

RE_NAME_OK = "letters, digits and _ (like Tribus_Novus)"


def _ok_name(n):
    return bool(n) and all(ch.isalnum() or ch == "_" for ch in n) and not n[0].isdigit()


def free_colour(mod, campaign, taken=()):
    """A colour no pixel of map_regions.tga has (nor black, white or near the seas'). The three channels step through
    199, 197 and 193 values (primes): 7.5 million different colours before the walk comes round again - it used to
    step all three by 200, so only 200 colours were ever tried and a big map (a tester's, with hundreds of regions)
    ran out ('no free colour left')."""
    img = mod.region_map(campaign)
    used = img.colours() | set(taken)
    for i in range(1, 2000000):
        c = ((i * 97) % 199 + 30, (i * 57) % 197 + 30, (i * 37) % 193 + 30)
        if c in used or (c[0] < 60 and 120 < c[1] < 160):             # keep clear of the sea blues
            continue
        return c
    raise ValueError("no colour left for a new region: map_regions.tga uses nearly every colour")


def region_problems(mod, campaign, painted, new_regions):
    """(errors, warnings) for a set of tile changes and new regions:
    new_regions = [{'name', 'settlement', 'city': (x, y), 'port': (x, y) or None, ...}]."""
    errors, warns = [], []
    img = mod.region_map(campaign)
    regions = mod.regions(campaign)
    by_colour = {v["colour"]: k for k, v in regions.items()}
    new_names = {r["name"] for r in new_regions}
    known = set(regions) | new_names
    settlements = {v.get("settlement") for v in regions.values()}
    for r in new_regions:
        if not _ok_name(r["name"]):
            errors.append("region name '%s': %s" % (r["name"], RE_NAME_OK))
        if r["name"] in regions:
            errors.append("a region '%s' exists already" % r["name"])
        if not _ok_name(r.get("settlement", "")):
            errors.append("settlement name '%s': %s" % (r.get("settlement", ""), RE_NAME_OK))
        elif r["settlement"] in settlements:
            errors.append("a settlement '%s' exists already" % r["settlement"])
        if r["name"] == r.get("settlement"):
            errors.append("%s: the region and its settlement need different names" % r["name"])
    for (x, y), r in painted.items():
        if r not in known:
            errors.append("tile %d, %d: no region '%s'" % (x, y, r))
            continue
        if not (0 <= x < img.width and 0 <= y < img.height):
            errors.append("tile %d, %d is off the map" % (x, y))
            continue
        px = img.get(x, y)
        if px in (CITY, PORT):
            errors.append("tile %d, %d holds a town or port - it keeps its region" % (x, y))
        elif px not in by_colour:
            errors.append("tile %d, %d is sea - only land changes region" % (x, y))
    # what each region would hold - worked out only for the regions the painting touches (a map of millions
    # of tiles once made a dict of every tile here)
    def before(t):                                   # the tile's colour now (None off the map)
        x, y = t
        return img.get(x, y) if 0 <= x < img.width and 0 <= y < img.height else None

    def owner_get(t):
        if t in painted:
            return painted[t]
        x, y = t
        return by_colour.get(img.get(x, y)) if 0 <= x < img.width and 0 <= y < img.height else None
    held = {}

    def cells_of(r):
        if r not in held:
            col = regions.get(r, {}).get("colour")
            cells = {t for t in img.find(col) if t not in painted} if col else set()
            held[r] = cells | {tuple(t) for t, v in painted.items() if v == r}
        return held[r]
    tiles = mod.city_tiles(campaign)
    for r in {v for v in painted.values()} | {by_colour.get(before(t)) for t in painted if before(t) in by_colour}:
        if r and r in regions and not cells_of(r):
            errors.append("%s would have no land left" % r)
    for r in new_regions:
        c = r.get("city")
        if not c:
            errors.append("%s: place its town (a click on one of its tiles)" % r["name"])
        elif owner_get(tuple(c)) != r["name"]:
            errors.append("%s: the town must stand on its own land" % r["name"])
        else:
            feat = mod._optional_map(campaign, "map_features.tga")
            if feat and (feat.width, feat.height) == (img.width, img.height) and feat.get(*c) != (0, 0, 0):
                errors.append("%s: a river, ford or cliff runs where the town is" % r["name"])
        p = r.get("port")
        if p:
            if owner_get(tuple(p)) != r["name"]:
                errors.append("%s: the port must stand on its own land" % r["name"])
            elif not any(mod.is_sea(campaign, (p[0] + dx, p[1] + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                errors.append("%s: a port needs the sea next to it" % r["name"])
            elif c and tuple(p) == tuple(c):
                errors.append("%s: the port and the town need different tiles" % r["name"])
    # the ring round each town (mapedit.ring_problems): only what this painting and these new regions make
    from .mapedit import owner_of, ports as port_map, ring_problems
    new_towns = {r["name"]: tuple(r["city"]) for r in new_regions if r.get("city")}
    new_ports = {r["name"]: tuple(r["port"]) for r in new_regions if r.get("port")}
    towns = dict(tiles)
    towns.update(new_towns)
    port_tiles = dict(port_map(mod, campaign))
    port_tiles.update(new_ports)
    look = owner_of(mod, campaign, painted={tuple(k): v for k, v in painted.items()}, towns=new_towns,
                    port_tiles=new_ports)
    touched = ({tuple(t) for t in painted} | set(new_towns.values()) | set(new_ports.values()), new_names)
    for serious, msg in ring_problems(mod, campaign, look, towns, port_tiles, touched):
        (errors if serious else warns).append(msg)
    # regions cut in two
    for r in sorted({v for v in painted.values()} | {owner_before for owner_before in
                     (by_colour.get(before(t)) for t in painted) if owner_before}):
        cells = set(cells_of(r))
        town = tiles.get(r) or next((tuple(n["city"]) for n in new_regions if n["name"] == r and n.get("city")), None)
        if town:
            cells.add(tuple(town))
        if cells and len(_part(cells, next(iter(cells)))) != len(cells):
            warns.append("%s would be in more than one piece (fine for islands)" % r)
    return errors, warns


def _part(cells, start):
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + d[0], y + d[1])
            if n in cells and n not in seen:
                seen.add(n)
                todo.append(n)
    return seen


def donor_of(mod, campaign, painted, new):
    """The region a new region is cut out of: the one most of its painted land came from,
    else the one under its town; None when neither is known. painted = {xy: region}."""
    regions = mod.regions(campaign)
    by_colour = {v["colour"]: k for k, v in regions.items()}
    img = mod.region_map(campaign)
    src = {}
    for xy, to in painted.items():
        was = by_colour.get(img.get(*tuple(xy)))
        if to == new["name"] and was:
            src[was] = src.get(was, 0) + 1
    if src:
        return max(src, key=src.get)
    if new.get("city"):
        return by_colour.get(img.get(*tuple(new["city"])))
    return None


def religions_for(regions, given, donor):
    """The religions a new region is written with (Medieval II): those given when they add up
    to 100, else the donor's, else the campaign's most common line - never a broken or empty
    one (the game may not start with it)."""
    if given and sum(int(v) for v in given.values()) == 100:
        return {k: int(v) for k, v in given.items()}
    if (regions.get(donor) or {}).get("religions"):
        return dict(regions[donor]["religions"])
    lines = [tuple(sorted(v["religions"].items())) for v in regions.values() if v.get("religions")]
    return dict(max(set(lines), key=lines.count)) if lines else {}


def apply_regions(plan, campaign, painted, new_regions):
    """Write the changes (see the module text). painted keys may be lists (from JSON)."""
    mod = plan.mod
    painted = {tuple(k): v for k, v in painted.items()}
    errors, warns = region_problems(mod, campaign, painted, new_regions)
    if errors:
        raise ValueError("; ".join(errors))
    regions = mod.regions(campaign)
    colours = {k: v["colour"] for k, v in regions.items()}
    for r in new_regions:
        colours[r["name"]] = tuple(r.get("colour") or free_colour(mod, campaign, colours.values()))
    path = mod.campaign_file(campaign, "map_regions.tga")
    changes = {xy: colours[r] for xy, r in painted.items()}
    for r in new_regions:
        changes[tuple(r["city"])] = CITY
        if r.get("port"):
            changes[tuple(r["port"])] = PORT
    plan.patch_tga(path, changes)
    moved = {}
    for xy, r in painted.items():
        moved.setdefault(r, 0)
        moved[r] += 1
    for r, n in sorted(moved.items()):
        plan.notes.append((mod.rel(path), "%d tile(s) to %s" % (n, r)))
    for folder in {os.path.dirname(path), os.path.join(mod.data, "world", "maps", "base")}:
        plan.delete(os.path.join(folder, "map.rwm"), "the game rebuilds it from the changed map on the next start")
    for w in warns:
        plan.warnings.append((mod.rel(path), w))
    if not new_regions:
        _slave_resources(plan, campaign, painted, colours)
        return
    # descr_regions.txt
    dr = plan.edit(mod.campaign_file(campaign, "descr_regions.txt"))
    while dr.raw and not dr.text(len(dr.raw) - 1).strip():
        del dr.raw[-1]
    built_by = {}
    for r in new_regions:
        c = colours[r["name"]]
        res = ", ".join(r.get("resources") or [])
        donor = donor_of(mod, campaign, painted, r)
        if not res:
            # no resources given: the donor's (no region in the game files has none; in HLR
            # they are the hidden resources that open local units)
            res = (regions.get(donor) or {}).get("resources") or ""
            if res:
                plan.note(dr, "%s: resources of %s (%s)" % (r["name"], donor, res))
        if not res:
            raise ValueError("%s: give it at least one resource (the game files have no region without)" % r["name"])
        d = regions.get(donor) or {}
        creator = r.get("creator") or d.get("creator") or r.get("owner")
        rebels = r.get("rebels") or d.get("rebels")
        if not creator or not rebels:
            raise ValueError("%s: pick who built it and its rebels (no land to take them from)" % r["name"])
        built_by[r["name"]] = creator
        if not r.get("creator") or not r.get("rebels"):
            plan.note(dr, "%s: built by %s, rebels %s (as %s)" % (r["name"], creator, rebels, donor))
        lines = [r["name"], "\t" + r["settlement"], "\t" + creator, "\t" + rebels,
                 "\t%d %d %d" % c, "\t" + res,
                 "\t%d" % int(r.get("triumph", 5)), "\t%d" % int(r.get("farming", 3))]
        if any("legion" in v for v in regions.values()):
            # Barbarian Invasion: a legion line after the name and a beliefs line after farming, as the
            # region most of its land came from (every region of BI's own file has both)
            legion = d.get("legion") or next(v["legion"] for v in regions.values() if v.get("legion"))
            lines.insert(1, "\t" + legion)
            beliefs = d.get("beliefs") or next((v["beliefs"] for v in regions.values() if v.get("beliefs")), {})
            if beliefs:
                lines.append("\t" + " ".join("%s %d" % (k, n) for k, n in beliefs.items()))
            plan.note(dr, "%s: %s, beliefs as %s" % (r["name"], legion, donor))
        if any("religions" in v for v in regions.values()):
            # Medieval II: a ninth line, the religions; given, else the region most land came from
            rel = religions_for(regions, r.get("religions"), donor)
            lines.append("\t" + religions_line(rel))
            plan.note(dr, "%s: %s" % (r["name"], religions_line(rel)))
        dr.raw.extend(dr.make(l) for l in lines)
        plan.note(dr, "region %s (%s), colour %d %d %d" % (r["name"], r["settlement"], c[0], c[1], c[2]))
    dr.raw.append(dr.make(""))
    # mercenaries: a new region joins the pool of the region most of its land came from
    img = mod.region_map(campaign)
    by_colour = {v["colour"]: k for k, v in regions.items()}
    _mercenary_pools(plan, campaign, new_regions, painted, by_colour, img)
    # the name lookup: appended, so the names already there keep their places
    lk = mod.campaign_file(campaign, "descr_regions_and_settlement_name_lookup.txt")
    if lk:
        f = plan.edit(lk)
        while f.raw and not f.text(len(f.raw) - 1).strip():
            del f.raw[-1]
        for r in new_regions:
            f.raw.extend([f.make(r["name"]), f.make(r["settlement"])])
        f.raw.append(f.make(""))
        plan.note(f, "%d name(s) added" % (2 * len(new_regions)))
    # labels
    labels = mod.region_labels_file(campaign)
    if labels:
        f = plan.edit(labels)
        while f.raw and not f.text(len(f.raw) - 1).strip():
            del f.raw[-1]
        for r in new_regions:
            f.raw.extend([f.make("{%s}\t\t\t%s" % (r["name"], r.get("label") or r["name"].replace("_", " "))),
                          f.make("{%s}\t\t\t%s" % (r["settlement"], r.get("settlement_label") or
                                                   r["settlement"].replace("_", " ")))])
        f.raw.append(f.make(""))
        plan.note(f, "labels for %s" % ", ".join(r["name"] for r in new_regions))
    else:
        plan.warn(None, "no %s_regions_and_settlement_names.txt found - the new names show as keys" % campaign)
    # descr_strat: a settlement for an owner; without one the game makes a rebel village
    sf = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
    for r in new_regions:
        own = r.get("owner")
        if not own:
            plan.note(sf, "%s: no settlement written - the game makes it a rebel village" % r["name"])
            continue
        s = Strat(sf)
        fb = s.faction(own)
        if fb is None:
            raise ValueError("%s: no faction block for %s in descr_strat.txt" % (r["name"], own))
        block = village_block(r["name"], built_by.get(r["name"]) or own)
        level = r.get("level") or "village"
        block = [l.replace("level village", "level " + level) for l in block]
        block = _grown_block(plan, block, level, r["name"], sf)
        at = fb.settlements[-1].end if fb.settlements else \
            next((i + 1 for i in range(fb.start, fb.end) if sf.text(i).split()[:1] == ["denari"]), fb.start + 1)
        sf.raw[at:at] = [sf.make(l) for l in block]
        plan.note(sf, "%s: a %s of %s" % (r["name"], level, own))
    _slave_resources(plan, campaign, painted, colours, new_regions)


def _slave_resources(plan, campaign, painted, colours, new_regions=()):
    """Rome gives every region a 'resource slaves' on the map (103 of 103 in vanilla) and stops at a region without
    one ("could not find slave resource in <region>, every region must have one" - a tester's test mod's new
    region). After the regions changed, a region left without one gets it on a free land tile of its own. A game
    whose regions do not all carry one (Medieval II: 2 in the whole map) is left alone."""
    from . import resources as R
    mod = plan.mod
    sf = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
    have = R.read(sf)
    slaves = [r for r in have if r.kind == "slaves"]
    regions = mod.regions(campaign)
    if len(slaves) < 0.9 * len(regions):
        return
    img = mod.region_map(campaign)                    # game tiles: x, y from the bottom (tga.Image.get)
    by_colour = {tuple(c): name for name, c in colours.items()}
    town_of = {tuple(xy): name for name, xy in mod.city_tiles(campaign).items()}

    def region_at(xy):
        if xy in painted:
            return painted[xy]
        px = tuple(img.get(xy[0], xy[1]))
        if px in ((0, 0, 0), (255, 255, 255)):       # a town's (HLR keeps its slaves there) or a port's tile
            if xy in town_of:
                return town_of[xy]
            near = [by_colour.get(tuple(img.get(x, y))) for x in (xy[0] - 1, xy[0], xy[0] + 1)
                    for y in (xy[1] - 1, xy[1], xy[1] + 1) if 0 <= x < img.width and 0 <= y < img.height]
            near = [n for n in near if n]
            return max(set(near), key=near.count) if near else None
        return by_colour.get(px)
    with_slaves = {region_at(tuple(r.xy)) for r in slaves if 0 <= r.xy[0] < img.width and 0 <= r.xy[1] < img.height}
    taken = {tuple(r.xy) for r in have}
    towns = {tuple(r["city"]) for r in new_regions} | {tuple(r["port"]) for r in new_regions if r.get("port")}
    wanting = [n for n in list(regions) + [r["name"] for r in new_regions] if n not in with_slaves]
    if not wanting:
        return
    tiles = {}
    for xy, r in painted.items():
        tiles.setdefault(r, []).append(xy)
    for name in wanting:
        cells = tiles.get(name)
        if not cells:
            c = tuple(colours.get(name) or ())
            cells = [tuple(p) for p in img.find(c) if tuple(p) not in painted] if c else []
        cells = [xy for xy in cells if xy not in towns and not R.problem(mod, campaign, xy, taken)]
        if not cells:
            plan.warn(sf, "%s has no free land tile for its slaves resource - Rome needs one in every region" % name)
            continue
        cx = sum(x for x, _ in cells) / len(cells)
        cy = sum(y for _, y in cells) / len(cells)
        xy = min(cells, key=lambda p: ((p[0] - cx) ** 2 + (p[1] - cy) ** 2, p))
        R.apply(plan, campaign, {"added": [{"type": "slaves", "xy": xy}]})
        taken.add(xy)
        plan.note(sf, "%s: a slaves resource at %d, %d (Rome needs one in every region)" % (name, xy[0], xy[1]))


def _grown_block(plan, block, level, region, sf):
    """A new town bigger than a village: its population at the level's threshold and the
    governor's building the game wants for that level (one below it), else it refuses."""
    from .buildings import POP_MIN, core_level_for, read_buildings
    if level == "village":
        return block
    block = [("\tpopulation %d" % POP_MIN[level]) if l.strip().startswith("population") and
             POP_MIN.get(level, 0) > 400 else l for l in block]
    path = plan.mod.file("edb")
    edb = plan.files.get(path) or (plan.mod.load(path) if path else None)
    core = next((b for b in read_buildings(edb) if b.name == "core_building"), None) if edb is not None else None
    lv = core_level_for(core, level) if core else None
    if lv is None:
        plan.warn(sf, "%s: a %s with no governor's building (none found for that level)" % (region, level))
        return block
    return block[:-1] + ["\tbuilding", "\t{", "\t\ttype core_building %s" % lv.name, "\t}", "}"]


def set_religions(plan, campaign, religions):
    """religions = {region: {religion: percent}}: the regions' religions lines in
    descr_regions.txt (Medieval II) set; other lines keep their bytes."""
    if not religions:
        return
    mod = plan.mod
    known = mod.regions(campaign)
    f = plan.edit(mod.campaign_file(campaign, "descr_regions.txt"))
    cur = None
    done = set()
    for i in range(len(f.raw)):
        line = f.text(i)
        code = line.split(";", 1)[0]
        if code.strip() and not code[0].isspace():
            cur = code.strip()
        elif cur in religions and code.strip().startswith("religions"):
            rel = {k: int(v) for k, v in religions[cur].items()}
            if sum(rel.values()) != 100:
                raise ValueError("%s: the religions add up to %d, not 100" % (cur, sum(rel.values())))
            indent = line[:len(line) - len(line.lstrip())]
            new = indent + religions_line(rel)
            if new != line.rstrip("\r\n"):
                f.set(i, new)
                plan.note(f, "%s: %s" % (cur, religions_line(rel)))
            done.add(cur)
    for r in religions:
        if r not in done:
            raise ValueError("%s: no religions line in descr_regions.txt%s" % (
                r, "" if r in known else " (no such region)"))


def _mercenary_pools(plan, campaign, new_regions, painted, by_colour, img):
    """descr_mercenaries.txt: each new region added to the 'regions' line of the pool
    that holds the region most of its land came from (else no mercenaries there)."""
    mod = plan.mod
    path = mod.campaign_file(campaign, "descr_mercenaries.txt")
    if not path:
        return
    f = None
    for r in new_regions:
        src = {}
        for xy, to in painted.items():
            was = by_colour.get(img.get(*xy))
            if to == r["name"] and was:
                src[was] = src.get(was, 0) + 1
        donor = max(src, key=src.get) if src else None
        if not donor:
            continue
        f = f or plan.edit(path)
        for i in range(len(f.raw)):
            text = f.text(i)
            body, sep, comment = text.partition(";")
            words = body.split()
            if words[:1] == ["regions"] and donor in [w.rstrip(",") for w in words[1:]]:
                end = len(body.rstrip())
                f.set(i, body[:end] + " " + r["name"] + body[end:] + sep + comment)
                plan.note(f, "%s joins %s's mercenary pool" % (r["name"], donor))
                break


EDITABLE = ("creator", "rebels", "resources", "triumph", "farming")
SHOWN = ("label", "settlement_label")          # the names players see, kept in the campaign's labels text


def shown_labels(mod, campaign, keys):
    """{key: text} of the campaign's region labels ({Latium} Latium) for the given region / town names."""
    p = mod.region_labels_file(campaign)
    want = {k.lower(): k for k in keys}
    out = {}
    if p:
        for line in mod.load(p).texts():
            m = re.match(r"\s*\{([^}]+)\}(\s*)(.*)$", line)
            if m and m.group(1).lower() in want:
                out[want[m.group(1).lower()]] = m.group(3).strip()
    return out


def set_labels(plan, campaign, labels):
    """labels = {region or town file name: the name players see}: its {key} line in the campaign's
    *_regions_and_settlement_names.txt gets the new text (the key and the gap before the text stay), a key the
    file lacks is added at its end. Every other line keeps its bytes."""
    if not labels:
        return
    for key, text in labels.items():
        if not text.strip() or "\n" in text or "{" in text or "}" in text:
            raise ValueError("%s: the name players see must be one line of text without { }" % key)
    p = plan.mod.region_labels_file(campaign)
    if not p:
        raise ValueError("no %s_regions_and_settlement_names.txt found - the names players see live there"
                         % campaign)
    f = plan.edit(p)
    left = {k.lower(): (k, v.strip()) for k, v in labels.items()}
    for i in range(len(f.raw)):
        m = re.match(r"(\s*\{([^}]+)\}(\s*))(.*?)(\s*)$", f.text(i))
        if m and m.group(2).lower() in left:
            key, text = left.pop(m.group(2).lower())
            gap = m.group(3) or "\t\t\t"
            if m.group(4) != text:
                f.set(i, m.group(1)[:len(m.group(1)) - len(m.group(3))] + gap + text)
                plan.note(f, "%s: shown as '%s' (was '%s')" % (key, text, m.group(4)))
    if left:
        while f.raw and not f.text(len(f.raw) - 1).strip():
            del f.raw[-1]
        for key, text in left.values():
            f.raw.append(f.make("{%s}\t\t\t%s" % (key, text)))
            plan.note(f, "%s: shown as '%s' (added)" % (key, text))
        f.raw.append(f.make(""))


def set_region_lines(plan, f, changes, why=""):
    """changes = {region: {field: value}} on a loaded descr_regions.txt, each value line found by
    moddata.region_entries (the one place that knows the layout); the line keeps its indent and
    comment. Raises for a region or line the file does not have."""
    from .moddata import region_entries
    entries = region_entries(f)
    for region, ch in changes.items():
        e = entries.get(region)
        if e is None:
            raise ValueError("%s is no region of descr_regions.txt" % region)
        for field, want in ch.items():
            if field not in e:
                raise ValueError("%s: descr_regions.txt has no %s line for it" % (region, field))
            i = e[field][0]
            line = f.text(i).rstrip("\r\n")
            code = line.split(";", 1)[0]
            indent = line[:len(line) - len(line.lstrip())]
            tail = line[len(code.rstrip()):]            # what follows the value (spaces, a comment) stays
            if code.strip() != want:
                f.set(i, indent + want + tail)
                plan.note(f, "%s: %s %s -> %s%s" % (region, field, code.strip(), want, why))


def edit_regions(plan, campaign, edits):
    """edits = {region: {'creator', 'rebels', 'resources' (list or text), 'triumph', 'farming'}}:
    those lines of existing regions in descr_regions.txt set (the given keys only); every other
    line keeps its bytes."""
    if not edits:
        return
    mod = plan.mod
    facs = {n for n, _ in mod.factions()}
    changes = {}
    shown = {}
    towns = None
    for region, ch in edits.items():
        if ch.get("label", "").strip():
            shown[region] = ch["label"]
        if ch.get("settlement_label", "").strip():
            if towns is None:
                towns = {k: v.get("settlement") for k, v in mod.regions(campaign).items()}
            if not towns.get(region):
                raise ValueError("%s has no town in descr_regions.txt" % region)
            shown[towns[region]] = ch["settlement_label"]
        out = {}
        for field in EDITABLE:
            want = ch.get(field)
            if want is None or str(want).strip() == "":
                continue
            if field == "resources":
                want = ", ".join(x.strip() for x in (want if isinstance(want, list) else str(want).split(","))
                                 if x.strip()) or "none"
            elif field in ("triumph", "farming"):
                if not str(want).strip().isdigit():
                    raise ValueError("%s: %s must be a whole number" % (region, field))
                want = str(int(want))
            elif field == "creator" and want not in facs:
                raise ValueError("%s: %s is no faction of this mod" % (region, want))
            out[field] = str(want).strip()
        if out:
            changes[region] = out
    if changes:
        set_region_lines(plan, plan.edit(mod.campaign_file(campaign, "descr_regions.txt")), changes)
    set_labels(plan, campaign, shown)


def apply_opts(plan, campaign, regions):
    """Everything the window's region work holds ({'new_religions', 'painted', 'new', 'religions',
    'edits', 'culture_names'}), in
    one place for every kind of run (map only, new faction, edited faction)."""
    if not regions:
        return
    if regions.get("new_religions"):          # before the shares: a region may be given one at once
        from .religions import apply as apply_religions
        apply_religions(plan, regions["new_religions"])
    apply_regions(plan, campaign, regions.get("painted") or {}, regions.get("new") or [])
    set_religions(plan, campaign, regions.get("religions") or {})
    edit_regions(plan, campaign, regions.get("edits") or {})
    if regions.get("culture_names"):
        from .culturenames import apply as apply_culture_names
        apply_culture_names(plan, campaign, regions["culture_names"])


def plan_land(plan, campaign):
    """(tiles, own): the town tiles as the plan leaves the map (towns moved, new regions' towns)
    and own(region) -> a test 'is this tile that region's land' with the painted tiles and the
    new towns and ports on top of map_regions.tga - for placing characters in one Apply with
    the map's changes."""
    from .edit import plan_tiles
    mod = plan.mod
    tiles = plan_tiles(plan, campaign)
    regions = (plan.opts.get("regions") or {})
    painted = {tuple(k): v for k, v in (regions.get("painted") or {}).items()}
    points = {tuple(r[w]) for r in regions.get("new") or [] for w in ("city", "port") if r.get(w)}
    img = mod.region_map(campaign)
    by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}

    def own(region):
        def test(p):
            if p in points:
                return False
            return painted.get(p, by_colour.get(img.get(*p))) == region
        return test
    return tiles, own
