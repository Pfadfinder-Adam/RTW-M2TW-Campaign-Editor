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

CITY, PORT = (0, 0, 0), (255, 255, 255)


def place_problem(mod, campaign, what, region, xy, moved=None, painted=None):
    """Why town/port ('city' or 'port') of region may not go to tile xy, or None.
    moved: {(what, region): xy} other moves already picked; painted: {(x, y): region} land painted to a region of
    the map and not written yet - it counts as that region's (paint, then move the town or port onto it, one go)."""
    moved = moved or {}
    painted = {tuple(k): v for k, v in (painted or {}).items()}
    img = mod.region_map(campaign)
    colours = {k: v["colour"] for k, v in mod.regions(campaign).items()}

    def colour_at(cx, cy):
        c = img.get(cx, cy)
        r = painted.get((cx, cy))
        return colours[r] if r in colours and c not in (CITY, PORT) else c
    x, y = xy
    if not (0 <= x < img.width and 0 <= y < img.height):
        return "off the map"
    info = mod.regions(campaign).get(region)
    if not info:
        return "%s is not a region of this map" % region
    now = current(mod, campaign, what, region, moved)
    if now is None and what == "city":
        return "%s has no town on the map" % region
    if now is not None and tuple(xy) == tuple(now):
        return "already there"                         # a region without a port gets a new one (now is None)
    here = orig(mod, campaign, what, region)
    here = tuple(here) if here else None
    # the tile as it would be: freed spots of other moves count as the region's own land
    px = colour_at(x, y)
    for (w, r), to in moved.items():
        if tuple(to) == (x, y) and (w, r) != (what, region):
            return "the new %s of %s goes there" % ("town" if w == "city" else "port", r)
    freed = {tuple(orig(mod, campaign, w, r)): r for (w, r) in moved if (w, r) != (what, region)}
    if px in (CITY, PORT) and (x, y) not in freed and (x, y) != here:
        return "another town or port stands there"
    if px != info["colour"] and freed.get((x, y)) != region and (x, y) != here:
        return "not %s's land" % region
    if what == "city":
        why = mod.land_problem(campaign, (x, y))
        if why:
            return why
    else:
        if not any(mod.is_sea(campaign, (x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            return "a port needs the sea next to it"
        # a port belongs to the region most of the land round it is (as ports() reads it): there must be more
        # of this region's tiles round it than of any other's, or the port would count as the neighbour's
        by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}
        votes = {}
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < img.width and 0 <= ny < img.height:
                r = by_colour.get(colour_at(nx, ny))
                if (nx, ny) == here:
                    r = region
                if r:
                    votes[r] = votes.get(r, 0) + 1
        if votes.get(region, 0) <= max([n for r, n in votes.items() if r != region] or [0]):
            return "most of the land round it is another region's - the port would count as theirs"
    serious = [m for s, m in _move_ring(mod, campaign, what, region, xy, moved, painted) if s]
    return serious[0] if serious else None


def _move_ring(mod, campaign, what, region, xy, moved, painted=None):
    """ring_problems for one town / port put at xy (with the other moves picked)."""
    moves = dict(moved or {})
    moves[(what, region)] = tuple(xy)
    towns = {r: tuple(t) for r, t in mod.city_tiles(campaign).items()}
    port_tiles = dict(ports(mod, campaign))
    for (w, r), to in moves.items():
        (towns if w == "city" else port_tiles)[r] = tuple(to)
    return ring_problems(mod, campaign, owner_of(mod, campaign, moves, painted=painted or None), towns, port_tiles,
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
# Medieval II; HLR has 6 under REX) - and on Medieval II a port inside a town's 3 x 3 is warned about (vanilla M2TW's
# imperial campaign 0, but its norman_prologue 2 and it plays - so a warning, never a refusal; Rome 1, HLR 104).
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
    (Medieval II only, a warning). touched = (tiles, regions): only problems this edit makes - a ring tile or port among
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
                    # a warning, not a fault: vanilla M2TW's own norman_prologue has two (Marseille, Venice) and
                    # plays - only its imperial campaign never does it
                    out.append((False, "the port of %s stands next to the town of %s - vanilla Medieval II's grand "
                                       "campaign never puts a port inside a town's 3 x 3 (its prologue does)"
                                       % (pr, r)))
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


PORT_CHAINS = ("port", "sea_trade", "port_buildings")   # a town's harbour chains: gone with its port


def _remove_ports(plan, campaign, regions):
    """The ports of `regions` taken off the map: the port pixel of map_regions.tga back to its region's land, a fleet
    standing on it moved to the sea beside, the town's harbour buildings (a port with no port on the map) taken out
    of descr_strat.txt."""
    mod = plan.mod
    path = mod.campaign_file(campaign, "map_regions.tga")
    info = mod.regions(campaign)
    changes = {}
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(sp)
    s = Strat(f)
    taken = {c.xy for fb in s.factions for c in fb.characters if c.xy}
    for region in regions:
        at = orig(mod, campaign, "port", region)
        if not at:
            continue
        changes[tuple(at)] = info[region]["colour"]
        plan.notes.append((mod.rel(path), "the port of %s at %d, %d taken off the map" % (region, at[0], at[1])))
        for c in port_fleets(s, tuple(at)):
            dest = sea_spot(mod, campaign, tuple(at), taken)
            if dest:
                taken.discard(c.xy)
                taken.add(dest)
                f.set(c.start, RE_XY.sub("x %d, y %d" % dest, f.text(c.start), 1))
                plan.note(f, "%s's fleet leaves the port of %s for the sea at %d, %d" % (c.name, region, dest[0],
                                                                                        dest[1]))
        s = Strat(f)                                  # afresh: an earlier town's lines may be gone
        town = next((st for fb in s.factions for st in fb.settlements if st.region == region), None)
        lines = f.texts()
        start, end = (town.start, town.end) if town else _settlement_span(lines, region)
        if start is None:
            continue
        i = end - 1
        while i >= start:                             # building { type <chain> <level> } blocks of a harbour chain
            t = lines[i].split()
            if t[:1] == ["type"] and len(t) >= 2 and t[1] in PORT_CHAINS:
                a, b = i, i
                while a > start and lines[a].strip() != "building":
                    a -= 1
                while b < end - 1 and lines[b].strip() != "}":
                    b += 1
                if lines[a].strip() == "building":
                    f.delete(a, b + 1)
                    plan.note(f, "%s: its %s building taken out - the town has no port now" % (region, t[1]))
                    lines = f.texts()
                    i = a
            i -= 1
    if changes:
        plan.patch_tga(path, changes)
        for folder in {os.path.dirname(path), os.path.join(mod.data, "world", "maps", "base")}:
            plan.delete(os.path.join(folder, "map.rwm"), "the game rebuilds it from the changed map")


def _settlement_span(lines, region):
    """(first, end) of the settlement block naming `region` in descr_strat lines, or (None, None)."""
    for i, l in enumerate(lines):
        if l.split()[:2] == ["region", region]:
            a = i
            while a > 0 and lines[a].strip() != "settlement" and not lines[a].strip().startswith("settlement"):
                a -= 1
            depth, b = 0, a
            while b < len(lines):
                depth += lines[b].count("{") - lines[b].count("}")
                b += 1
                if depth == 0 and b > a + 1 and "{" in "".join(lines[a:b]):
                    break
            return a, b
    return None, None


def apply_places(plan, campaign, places, painted=None):
    """places = [{'what': 'city'|'port', 'region', 'to': (x, y)}]: repaint
    map_regions.tga, remove map.rwm, move the characters on a moved town. painted: the land painted in the same
    write (apply_regions first), so a town or port may go onto it."""
    mod = plan.mod
    moved = {}
    gone = [p["region"] for p in places if p["what"] == "port" and p.get("to") is None]
    places = [p for p in places if p.get("to") is not None]
    if gone:
        _remove_ports(plan, campaign, gone)
    for p in places:
        key = (p["what"], p["region"])
        why = place_problem(mod, campaign, p["what"], p["region"], tuple(p["to"]),
                            {k: v for k, v in moved.items() if k != key}, painted)
        if why:
            raise ValueError("%s of %s cannot go to %d, %d: %s" % (
                "town" if p["what"] == "city" else "port", p["region"], p["to"][0], p["to"][1], why))
        for serious, msg in _move_ring(mod, campaign, p["what"], p["region"], tuple(p["to"]),
                                       {k: v for k, v in moved.items() if k != key}, painted):
            if not serious:
                plan.warn(None, msg)
        moved[key] = tuple(p["to"])
    if not moved:
        return
    path = mod.campaign_file(campaign, "map_regions.tga")
    regions = mod.regions(campaign)
    changes = {}
    for (what, region), to in moved.items():                 # old spots first, then the new ones
        old = orig(mod, campaign, what, region)
        if old:
            changes[tuple(old)] = regions[region]["colour"]
    for (what, region), to in moved.items():
        changes[to] = CITY if what == "city" else PORT
        old = orig(mod, campaign, what, region)
        plan.notes.append((mod.rel(path), "%s of %s moved from %d, %d to %d, %d" % (
            "town" if what == "city" else "port", region, old[0], old[1], to[0], to[1]) if old else
            "a new port for %s at %d, %d (its town can build a port now)" % (region, to[0], to[1])))
    plan.patch_tga(path, changes)
    for folder in {os.path.dirname(path), os.path.join(mod.data, "world", "maps", "base")}:
        rwm = os.path.join(folder, "map.rwm")
        plan.delete(rwm, "the game rebuilds it from the changed map on the next start (takes a moment)")
    # characters on a moved town's tile go with it
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(sp)
    s = Strat(f)
    taken = {c.xy for fb in s.factions for c in fb.characters if c.xy}
    for (what, region), to in moved.items():
        if what != "port" or not orig(mod, campaign, what, region):
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
