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
    if what == "city":
        why = mod.land_problem(campaign, (x, y))
        if why:
            return why
    else:
        if not any(mod.is_sea(campaign, (x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            return "a port needs the sea next to it"
    serious = [m for s, m in _move_ring(mod, campaign, what, region, xy, moved) if s]
    return serious[0] if serious else None


def _move_ring(mod, campaign, what, region, xy, moved):
    """ring_problems for one town / port put at xy (with the other moves picked)."""
    moves = dict(moved or {})
    moves[(what, region)] = tuple(xy)
    towns = {r: tuple(t) for r, t in mod.city_tiles(campaign).items()}
    port_tiles = dict(ports(mod, campaign))
    for (w, r), to in moves.items():
        (towns if w == "city" else port_tiles)[r] = tuple(to)
    return ring_problems(mod, campaign, owner_of(mod, campaign, moves), towns, port_tiles,
                         touched=({tuple(xy)}, {region}))


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
    for x, y in img.find(PORT):
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


# ---------------------------------------------------------------------------
# The ring round a town (the M2EX Campaign Map Builder's rule, measured on the vanilla maps 2026-09-30):
# the 8 tiles round a town are its own region or sea - never another region (0 towns in vanilla Rome and
# Medieval II; HLR has 6 under REX) - and on Medieval II no port stands inside a town's 3 x 3 (vanilla M2TW 0;
# vanilla Rome 1, HLR 104 - so Rome is not held to it).
# ---------------------------------------------------------------------------
def ring(xy):
    x, y = xy
    return [(x + dx, y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]


def owner_of(mod, campaign, moved=None, painted=None, towns=None, port_tiles=None):
    """A function tile -> the region it will belong to (None for sea / off the map), the map as moves (moved
    {(what, region): xy}), painted tiles ({xy: region}) and new towns / ports leave it."""
    img = mod.region_map(campaign)
    by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}
    markers, freed = {}, {}
    for what, table in (("city", mod.city_tiles(campaign)), ("port", ports(mod, campaign))):
        for r, xy in table.items():
            if xy:
                markers[tuple(xy)] = r
    for (what, r), to in (moved or {}).items():
        old = orig(mod, campaign, what, r)
        if old:
            markers.pop(tuple(old), None)
            freed[tuple(old)] = r
    for (what, r), to in (moved or {}).items():
        markers[tuple(to)] = r
    for table in (towns or {}, port_tiles or {}):
        for r, xy in table.items():
            if xy:
                markers[tuple(xy)] = r
    painted = painted or {}

    def get(xy):
        x, y = xy
        if not (0 <= x < img.width and 0 <= y < img.height):
            return None
        if xy in markers:
            return markers[xy]
        if xy in painted:
            return painted[xy]
        if xy in freed:
            return freed[xy]
        return by_colour.get(img.get(x, y))
    return get


def ring_problems(mod, campaign, owner, towns, port_tiles, touched=None):
    """[(serious, message)] for towns {region: xy} and ports {region: xy} on the map owner (owner_of) gives:
    another region in a town's ring (serious on Medieval II, a warning on Rome), a port in a town's ring
    (Medieval II only). touched = (tiles, regions): only problems this edit makes - a ring tile or port among
    the tiles, or a town / port of the regions (None: every problem, for Check mod)."""
    from .limits import game_kind
    m2 = game_kind(mod) == "medieval2"
    tiles, regs = (set(touched[0]), set(touched[1])) if touched else (None, None)
    port_at = {tuple(v): r for r, v in port_tiles.items() if v}
    out = []
    for r, t in sorted(towns.items()):
        if not t:
            continue
        near = ring(tuple(t))
        mine = touched is None or r in regs or bool(tiles & set(near))
        others = sorted({owner(n) for n in near} - {None, r})
        if others and mine:
            out.append((m2, "the town of %s touches %s's land - the 8 tiles round a town must be its own region "
                            "or sea%s" % (r, ", ".join(others),
                                          " (Medieval II crashes on it)" if m2 else " (vanilla Rome never does it)")))
        if m2:
            for n in near:
                pr = port_at.get(n)
                if pr and (touched is None or mine or pr in regs or n in tiles):
                    out.append((True, "the port of %s stands next to the town of %s - Medieval II takes no port "
                                      "inside a town's 3 x 3" % (pr, r)))
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
        for serious, msg in _move_ring(mod, campaign, p["what"], p["region"], tuple(p["to"]),
                                       {k: v for k, v in moved.items() if k != key}):
            if not serious:
                plan.warn(None, msg)
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
                # an army on the town's new tile (often one this very plan sent out of a taken town) steps
                # aside to the nearest free tile of the region - two armies may not share a tile
                busy = {cc.xy for fb in s.factions for cc in fb.characters if cc.xy} | set(moved.values()) | \
                    {tuple(orig(mod, campaign, w, r)) for (w, r) in moved}
                dest = mod.free_tile(campaign, region, busy, start=tuple(to))
                if dest is None:
                    raise ValueError("%s: %s's army stands on %d, %d and there is no free tile next to it - move "
                                     "it first" % (region, c.name, to[0], to[1]))
                f.set(c.start, RE_XY.sub("x %d, y %d" % dest, f.text(c.start), 1))
                plan.note(f, "%s's army steps aside to %d, %d: the town of %s moves onto its tile" % (
                    c.name, dest[0], dest[1], region))
