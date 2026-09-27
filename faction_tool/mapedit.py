"""Moving towns and ports on the campaign map.

A town is the black pixel, a port the white pixel of map_regions.tga, each on
a tile of its region's own colour; a port stands on the coast (a sea tile next
to it, as all 75 vanilla and 315 HLR ports do). Moving one repaints two pixels:
the old spot gets the region's colour back, the new one turns black or white.
The game keeps a compiled copy of the map in map.rwm and rebuilds it when the
file is missing, so the plan removes it (backed up like every change).
Characters standing on a moved town's tile move with the town; fleets lying
next to a moved port sail to the sea next to its new spot."""

import os

from .moddata import BLOCKED_GROUND
from .strat import RE_XY, Strat
from .tga import patched

CITY, PORT = (0, 0, 0), (255, 255, 255)


def place_problem(mod, campaign, what, region, xy, moved=None):
    """Why town/port ('city' or 'port') of region may not go to tile xy, or None.
    moved: {(what, region): xy} other moves already picked."""
    moved = moved or {}
    img = mod.region_map(campaign)
    x, y = xy
    if not (0 <= x < img.width and 0 <= y < img.height):
        return "off the map"
    info = mod.regions(campaign).get(region)
    if not info:
        return "%s is not a region of this map" % region
    now = current(mod, campaign, what, region, moved)
    if now is None:
        return "%s has no %s on the map" % (region, "town" if what == "city" else "port")
    if tuple(xy) == tuple(now):
        return "already there"
    # the tile as it would be: freed spots of other moves count as the region's own land
    px = img.get(x, y)
    for (w, r), to in moved.items():
        if tuple(to) == (x, y) and (w, r) != (what, region):
            return "the new %s of %s goes there" % ("town" if w == "city" else "port", r)
    freed = {tuple(orig(mod, campaign, w, r)): r for (w, r) in moved if (w, r) != (what, region)}
    if px in (CITY, PORT) and (x, y) not in freed and (x, y) != tuple(orig(mod, campaign, what, region)):
        return "another town or port stands there"
    if px != info["colour"] and freed.get((x, y)) != region and (x, y) != tuple(orig(mod, campaign, what, region)):
        return "not %s's land" % region
    feat = mod._optional_map(campaign, "map_features.tga")
    ground = mod._optional_map(campaign, "map_ground_types.tga")
    if what == "city":
        if feat and (feat.width, feat.height) == (img.width, img.height) and feat.get(x, y) != (0, 0, 0):
            return "a river, ford or cliff runs there"
        if ground and (ground.width, ground.height) == (2 * img.width + 1, 2 * img.height + 1) \
                and ground.get(2 * x + 1, 2 * y + 1) in BLOCKED_GROUND:
            return "sea, mountain or impassable ground"
    else:
        if not any(mod.is_sea(campaign, (x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            return "a port needs the sea next to it"
    return None


def orig(mod, campaign, what, region):
    """The town's or port's tile in the file as it is."""
    if what == "city":
        return mod.city_tiles(campaign).get(region)
    return ports(mod, campaign).get(region)


def current(mod, campaign, what, region, moved=None):
    return (moved or {}).get((what, region)) or orig(mod, campaign, what, region)


def ports(mod, campaign):
    """{region: (x, y)} of the white port pixels (by the region around them)."""
    key = ("ports", campaign)
    if key in mod._cache:
        return mod._cache[key]
    img = mod.region_map(campaign)
    by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}
    out = {}
    for y in range(img.height):
        for x in range(img.width):
            if img.get(x, y) != PORT:
                continue
            votes = {}
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < img.width and 0 <= ny < img.height:
                    r = by_colour.get(img.get(nx, ny))
                    if r:
                        votes[r] = votes.get(r, 0) + 1
            if votes:
                out[max(votes, key=votes.get)] = (x, y)
    mod._cache[key] = out
    return out


def port_fleets(s, port):
    """The fleets (admirals) lying at most two tiles off a port (vanilla puts
    them one or two tiles out)."""
    if not port:
        return []
    return [c for fb in s.factions for c in fb.characters
            if c.kind == "admiral" and c.xy and max(abs(c.xy[0] - port[0]), abs(c.xy[1] - port[1])) <= 2]


def sea_spot(mod, campaign, port, taken):
    """The nearest free sea tile next to a port (the four sides first), or None."""
    x, y = port
    ring = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
    ring += [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3) if max(abs(dx), abs(dy)) == 2]
    for dx, dy in ring:
        p = (x + dx, y + dy)
        if p not in taken and mod.is_sea(campaign, p):
            return p
    return None


def apply_places(plan, campaign, places):
    """places = [{'what': 'city'|'port', 'region', 'to': (x, y)}]: repaint
    map_regions.tga, remove map.rwm, move the characters on a moved town."""
    mod = plan.mod
    moved = {}
    for p in places:
        key = (p["what"], p["region"])
        why = place_problem(mod, campaign, p["what"], p["region"], tuple(p["to"]),
                            {k: v for k, v in moved.items() if k != key})
        if why:
            raise ValueError("%s of %s cannot go to %d, %d: %s" % (
                "town" if p["what"] == "city" else "port", p["region"], p["to"][0], p["to"][1], why))
        moved[key] = tuple(p["to"])
    if not moved:
        return
    path = mod.campaign_file(campaign, "map_regions.tga")
    regions = mod.regions(campaign)
    changes = {}
    for (what, region), to in moved.items():                 # old spots first, then the new ones
        changes[tuple(orig(mod, campaign, what, region))] = regions[region]["colour"]
    for (what, region), to in moved.items():
        changes[to] = CITY if what == "city" else PORT
        old = orig(mod, campaign, what, region)
        plan.notes.append((mod.rel(path), "%s of %s moved from %d, %d to %d, %d" % (
            "town" if what == "city" else "port", region, old[0], old[1], to[0], to[1])))
    plan.binary(path, patched(path, changes))
    for folder in {os.path.dirname(path), os.path.join(mod.data, "world", "maps", "base")}:
        rwm = os.path.join(folder, "map.rwm")
        plan.delete(rwm, "the game rebuilds it from the changed map on the next start (takes a moment)")
    # characters on a moved town's tile go with it
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(sp)
    s = Strat(f)
    taken = {c.xy for fb in s.factions for c in fb.characters if c.xy}
    for (what, region), to in moved.items():
        if what != "port":
            continue
        for c in port_fleets(s, orig(mod, campaign, what, region)):
            dest = sea_spot(mod, campaign, to, taken)
            if dest is None:
                plan.warn(f, "%s: no free sea next to the new port for %s's fleet - it stays" % (region, c.name))
                continue
            taken.discard(c.xy)
            taken.add(dest)
            f.set(c.start, RE_XY.sub("x %d, y %d" % dest, f.text(c.start), 1))
            plan.note(f, "%s's fleet follows the port of %s to %d, %d" % (c.name, region, dest[0], dest[1]))
    for (what, region), to in moved.items():
        if what != "city":
            continue
        old = orig(mod, campaign, what, region)
        for c in s.characters_at(tuple(old)):
            f.set(c.start, RE_XY.sub("x %d, y %d" % to, f.text(c.start), 1))
            plan.note(f, "%s moves with the town of %s to %d, %d" % (c.name, region, to[0], to[1]))
        for c in s.characters_at(tuple(to)):
            if any(l.split(None, 1)[:1] == ["army"] for l in s.lines[c.start:c.end]):
                raise ValueError("%s: %s's army stands on %d, %d - move it first" % (region, c.name, to[0], to[1]))
