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

from .mapedit import CITY, PORT, ports
from .moddata import religions_line
from .strat import Strat, village_block
from .tga import patched

RE_NAME_OK = "letters, digits and _ (like Tribus_Novus)"


def _ok_name(n):
    return bool(n) and all(ch.isalnum() or ch == "_" for ch in n) and not n[0].isdigit()


def free_colour(mod, campaign, taken=()):
    """A colour no pixel of map_regions.tga has (nor black, white or near the seas')."""
    img = mod.region_map(campaign)
    used = set(img.pixels) | set(taken)
    for i in range(1, 5000):
        c = ((i * 97) % 200 + 30, (i * 57) % 200 + 30, (i * 37) % 200 + 30)
        if c in used or (c[0] < 60 and 120 < c[1] < 160):             # keep clear of the sea blues
            continue
        return c
    raise ValueError("no free colour left")


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
    # what each region would hold
    owner = {}
    for y in range(img.height):
        for x in range(img.width):
            r = by_colour.get(img.get(x, y))
            if r:
                owner[(x, y)] = r
    owner.update(painted)
    count = {}
    for r in owner.values():
        count[r] = count.get(r, 0) + 1
    tiles = mod.city_tiles(campaign)
    for r in {v for v in painted.values()} | {by_colour.get(img.get(*t)) for t in painted if img.get(*t) in by_colour}:
        if r and r in regions and not count.get(r):
            errors.append("%s would have no land left" % r)
    for r in new_regions:
        c = r.get("city")
        if not c:
            errors.append("%s: place its town (a click on one of its tiles)" % r["name"])
        elif owner.get(tuple(c)) != r["name"]:
            errors.append("%s: the town must stand on its own land" % r["name"])
        else:
            feat = mod._optional_map(campaign, "map_features.tga")
            if feat and (feat.width, feat.height) == (img.width, img.height) and feat.get(*c) != (0, 0, 0):
                errors.append("%s: a river, ford or cliff runs where the town is" % r["name"])
        p = r.get("port")
        if p:
            if owner.get(tuple(p)) != r["name"]:
                errors.append("%s: the port must stand on its own land" % r["name"])
            elif not any(mod.is_sea(campaign, (p[0] + dx, p[1] + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                errors.append("%s: a port needs the sea next to it" % r["name"])
            elif c and tuple(p) == tuple(c):
                errors.append("%s: the port and the town need different tiles" % r["name"])
    # regions cut in two
    for r in sorted({v for v in painted.values()} | {owner_before for owner_before in
                     (by_colour.get(img.get(*t)) for t in painted) if owner_before}):
        cells = {t for t, v in owner.items() if v == r}
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
    plan.binary(path, patched(path, changes))
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
        return
    # descr_regions.txt
    dr = plan.edit(mod.campaign_file(campaign, "descr_regions.txt"))
    while dr.raw and not dr.text(len(dr.raw) - 1).strip():
        del dr.raw[-1]
    img = mod.region_map(campaign)
    by_colour = {v["colour"]: k for k, v in regions.items()}
    for r in new_regions:
        c = colours[r["name"]]
        res = ", ".join(r.get("resources") or [])
        src = {}                                   # the region most of its land came from
        for xy, to in painted.items():
            was = by_colour.get(img.get(*xy))
            if to == r["name"] and was:
                src[was] = src.get(was, 0) + 1
        donor = max(src, key=src.get) if src else None
        if not res:
            # no resources given: the donor's (no region in the game files has none; in HLR
            # they are the hidden resources that open local units)
            res = (regions.get(donor) or {}).get("resources") or ""
            if res:
                plan.note(dr, "%s: resources of %s (%s)" % (r["name"], donor, res))
        if not res:
            raise ValueError("%s: give it at least one resource (the game files have no region without)" % r["name"])
        lines = [r["name"], "\t" + r["settlement"], "\t" + r["creator"], "\t" + r["rebels"],
                 "\t%d %d %d" % c, "\t" + res,
                 "\t%d" % int(r.get("triumph", 5)), "\t%d" % int(r.get("farming", 3))]
        if any("religions" in v for v in regions.values()):
            # Medieval II: a ninth line, the religions; given, else the region most land came from
            rel = r.get("religions") or (regions.get(donor) or {}).get("religions") or \
                next(v["religions"] for v in regions.values() if "religions" in v)
            lines.append("\t" + religions_line(rel))
            plan.note(dr, "%s: %s" % (r["name"], religions_line(rel)))
        dr.raw.extend(dr.make(l) for l in lines)
        plan.note(dr, "region %s (%s), colour %d %d %d" % (r["name"], r["settlement"], c[0], c[1], c[2]))
    dr.raw.append(dr.make(""))
    # mercenaries: a new region joins the pool of the region most of its land came from
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
        block = village_block(r["name"], r.get("creator") or own)
        level = r.get("level") or "village"
        block = [l.replace("level village", "level " + level) for l in block]
        at = fb.settlements[-1].end if fb.settlements else \
            next((i + 1 for i in range(fb.start, fb.end) if sf.text(i).split()[:1] == ["denari"]), fb.start + 1)
        sf.raw[at:at] = [sf.make(l) for l in block]
        plan.note(sf, "%s: a %s of %s" % (r["name"], level, own))


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
