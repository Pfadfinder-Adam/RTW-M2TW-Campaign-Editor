"""Buildings and garrisons for many towns at once (both games): every town of the campaign with its owner, level,
city / castle (Medieval II), buildings and garrison; a building level added to (or a chain taken out of) the
towns picked, each town checked the way the game would see it; garrisons drawn at random from the units each
owner may recruit, 2 to 6 per town (any range), under an upkeep cap.

Writes only descr_strat.txt, through a Plan (Preview, backup, Restore)."""

import re

from .buildings import (available, castles_allowed, ranks_ok, read_buildings, set_buildings, settlement_info,
                        settlement_kind, SETTLEMENT_LEVELS)
from .start import MAX_UNITS, _has_army, _units, unit_name
from .strat import Strat

PORT = re.compile(r"(^|_)port(_|$)", re.I)


def known_buildings(mod):
    edb = mod.file("edb")
    return {b.name: b for b in read_buildings(mod.load(edb))} if edb else {}


def towns(mod, campaign):
    """[{'region', 'name', 'owner', 'level', 'kind' ('city' | 'castle', None in a game without castles),
    'buildings' [(chain, level)], 'units' (in the army on the town), 'upkeep', 'port'}] in descr_strat's order."""
    from .mapedit import ports
    from .start import unit_upkeep
    f = mod.load(mod.campaign_file(campaign, "descr_strat.txt"))
    s = Strat(f)
    regions = mod.regions(campaign)
    tiles = mod.city_tiles(campaign)
    try:
        port = ports(mod, campaign)
    except Exception:
        port = {}
    edu = mod.file("edu")
    upkeep = unit_upkeep(mod.load(edu)) if edu else {}
    castles = castles_allowed(mod, known_buildings(mod))
    out = []
    for fb in s.factions:
        for st in fb.settlements:
            lines = s.lines[st.start:st.end]
            level, items = settlement_info(lines)
            xy = tiles.get(st.region)
            army = next((c for c in fb.characters if xy and c.xy == xy and _has_army(s.lines[c.start:c.end])),
                        None)
            units = [unit_name(l) for l in _units(s.lines[army.start:army.end])] if army else []
            out.append({"region": st.region, "name": (regions.get(st.region) or {}).get("settlement") or st.region,
                        "owner": fb.name, "culture": _culture(mod, fb.name), "level": level,
                        "kind": settlement_kind(lines) if castles else None, "buildings": items,
                        "units": len(units), "upkeep": sum(upkeep.get(u, 0) for u in units),
                        "port": st.region in port})
    return out


def _culture(mod, faction):
    try:
        return mod.culture(faction)
    except Exception:
        return None


def is_core(chain):
    return chain.lower().startswith("core")


def building_fit(known, town, chain, level, mode="upgrade", any_owner=False, culture=None):
    """(what, why) for building level `level` of `chain` in a town (an entry of towns()):
    what = 'add' | 'upgrade' | 'set' | 'skip' | 'remove' (level None: the chain is taken out); why in plain words."""
    b = known.get(chain)
    have = next((lv for c, lv in town["buildings"] if c == chain), None)
    if is_core(chain):
        return "skip", "the governor's building follows the town's level - change the level instead"
    if level is None:
        return ("remove", "%s goes" % have) if have else ("skip", "has no %s" % chain)
    lv = b.level(level) if b else None
    if known and lv is None:
        return "skip", "%s %s is not in export_descr_buildings.txt" % (chain, level)
    if lv is not None:
        if lv.kind and town.get("kind") and lv.kind != town["kind"]:
            return "skip", "%s is built in %ss only - this is a %s, not a %s" % (level, lv.kind, town["kind"], lv.kind)
        if not ranks_ok(lv, town["level"]):
            return "skip", "%s needs a %s or bigger, this is a %s" % (level, lv.settlement_min.replace("_", " "),
                                                                      town["level"].replace("_", " "))
        if not any_owner and not available(lv, town["owner"], culture or town.get("culture")):
            return "skip", "%s may not build it (the level's faction list)" % town["owner"]
    if PORT.search(chain) and not town.get("port"):
        return "skip", "the town has no port on the map"
    if have == level:
        return "skip", "has it already"
    if have:
        names = [l.name for l in b.levels] if b else []
        higher = names.index(have) > names.index(level) if have in names and level in names else False
        if higher and mode != "set":
            return "skip", "has a higher level already (%s)" % have
        if mode == "skip":
            return "skip", "has %s already" % have
        return ("set" if higher else "upgrade"), "%s -> %s" % (have, level)
    why = "new"
    if lv is not None and lv.conditional():
        why += "; the game asks for more when it builds it (%s) - not checked here" % lv.conditional()[:80]
    return "add", why


def random_garrison(pool, lo, hi, cap, rng):
    """[unit type]: between lo and hi units (rng picks how many) drawn from pool [(type, upkeep)], their upkeep
    together not above cap (None: no cap). Fewer than lo when even the cheapest do not fit under the cap."""
    if not pool:
        return []
    n = rng.randint(min(lo, hi), max(lo, hi))
    cheapest = min(u for _, u in pool)
    out, total = [], 0
    for k in range(n):
        left = n - k - 1
        cands = [t for t, u in pool if cap is None or total + u + cheapest * left <= cap]
        if not cands:
            cands = [t for t, u in pool if cap is None or total + u <= cap]
            if not cands:
                break
        t = rng.choice(cands)
        out.append(t)
        total += dict(pool)[t]
    return out


def garrison_pool(mod, faction, siege=False):
    """[(unit type, upkeep)] a garrison of this faction may be drawn from: the land units it may own AND some
    building lets it recruit (else the land units it may own; the rebels: their mercenaries too), generals'
    bodyguards left out, siege engines too only when asked."""
    from .roster import roster
    from .units import faction_units
    units = faction_units(mod, faction, mercs=faction == "slave")
    land = [u for u in units if not u.general and (siege or u.category not in ("siege", "handler"))]
    try:
        recruits = {u["type"] for u in roster(mod, faction)["units"] if u["has"] and u["recruit"]}
    except Exception:
        recruits = set()
    picked = [u for u in land if u.type in recruits] or land
    return [(u.type, u.upkeep) for u in picked]


def rebel_pool(mod, campaign, region, near=3, siege=False):
    """[(unit type, upkeep)] for a rebel town: the units of the rebel armies nearest to it (its own garrison
    first) - the rebels' starting armies are local troops, so a Greek town gets Greek rebels, not anyone the
    rebels may own; garrison_pool when the rebels have no army."""
    from .units import read_units
    f = mod.load(mod.campaign_file(campaign, "descr_strat.txt"))
    s = Strat(f)
    fb = s.faction("slave")
    xy = mod.city_tiles(campaign).get(region)
    edu = mod.file("edu")
    units = {u.type: u for u in read_units(mod.load(edu))} if edu else {}
    armies = []
    for c in fb.characters if fb and xy else []:
        lines = s.lines[c.start:c.end]
        if c.xy and _has_army(lines):
            got = [unit_name(l) for l in _units(lines)]
            armies.append(((c.xy[0] - xy[0]) ** 2 + (c.xy[1] - xy[1]) ** 2, got))
    out = []
    for _, got in sorted(armies, key=lambda a: a[0])[:near]:
        for t in got:
            u = units.get(t)
            if u and not u.general and (siege or u.category not in ("siege", "handler")) and \
                    t not in [x for x, _ in out]:
                out.append((t, u.upkeep))
    return out or garrison_pool(mod, "slave", siege)


def apply(plan, campaign, opts):
    """opts: 'build' {region: (chain, level)} | 'remove' {region: chain} (the towns' buildings, checked as the
    window showed them), 'garrisons' {region: [unit type]}, 'add_units' (the units join the army in the town
    instead of replacing it)."""
    from .edit import _garrisons
    f = plan.edit(plan.mod.campaign_file(campaign, "descr_strat.txt"))
    s = Strat(f)
    where = {st.region: st for fb in s.factions for st in fb.settlements}
    jobs = [(r, x, None) for r, x in (opts.get("build") or {}).items()] + \
        [(r, None, c) for r, c in (opts.get("remove") or {}).items()]
    for region, build, chain in sorted(jobs, key=lambda j: -where[j[0]].start if j[0] in where else 0):
        st = where.get(region)
        if st is None:
            raise ValueError("%s has no town in descr_strat.txt" % region)
        raw = f.raw[st.start:st.end]
        _, items = settlement_info([l.rstrip("\r") for l in raw])
        if build:
            ch, lv = build
            if any(c == ch for c, _ in items):
                items = [(c, lv if c == ch else l) for c, l in items]
            else:
                items = items + [(ch, lv)]
            plan.note(f, "%s: %s %s" % (region, ch, lv))
        else:
            items = [(c, l) for c, l in items if c != chain]
            plan.note(f, "%s: %s taken out" % (region, chain))
        f.raw[st.start:st.end] = set_buildings(raw, items, f.make)
    picked = opts.get("garrisons") or {}
    by_owner = {}
    for region, types in picked.items():
        st = where.get(region)
        if st is None:
            raise ValueError("%s has no town in descr_strat.txt" % region)
        by_owner.setdefault(st.owner, {})[region] = list(types)
    for owner, got in by_owner.items():
        _garrisons(plan, f, Strat(f), campaign, faction=owner, picked=got, add=bool(opts.get("add_units")))
    return plan


__all__ = ["towns", "building_fit", "random_garrison", "garrison_pool", "rebel_pool", "apply", "known_buildings", "is_core",
           "MAX_UNITS", "SETTLEMENT_LEVELS"]
