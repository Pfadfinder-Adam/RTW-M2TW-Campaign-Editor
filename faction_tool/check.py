"""Check mod: read every file the tool works with and say what it found and
what it could not make sense of. Read-only - nothing is written.

The quick check reads the files; the deep one also rehearses the tool's own
work in memory for every faction (an edit that takes a rebel town with a
garrison, a new army, agent and fleet, and a new faction cloned from it) and
checks the result the way the game would read it."""

import os
import time
import traceback

from .buildings import read_buildings, settlement_info
from .strat import Strat, characters_after_tree
from .textio import tokens
from .units import read_units


def _has_army(lines):
    return any(tokens(l)[:1] == ["army"] for l in lines)


def check_mod(mod, campaign, deep=False, progress=None):
    """A report (text) on the mod as the tool sees it."""
    out, problems = [], []

    def say(msg):
        out.append(msg)

    def bad(msg):
        problems.append(msg)

    def step(msg):
        if progress:
            progress(msg)

    t0 = time.time()
    say("Mod: %s" % mod.data)
    say("Campaign: %s" % campaign)
    say("")
    # ---- files ----
    say("FILES")
    needed = [("sm_factions", True), ("names", True), ("edu", True), ("edb", True), ("character", False),
              ("model_strat", False), ("banners", False), ("traits", False), ("ancillaries", False)]
    for key, must in needed:
        p = mod.file(key)
        say("    %-28s %s" % (key, mod.rel(p) if p else ("MISSING" if must else "not there (fine)")))
        if not p and must:
            bad("%s is missing" % key)
    for name in ("descr_strat.txt", "descr_regions.txt", "map_regions.tga", "map_ground_types.tga",
                 "map_features.tga", "map_heights.tga", "descr_win_conditions.txt"):
        p = mod.campaign_file(campaign, name)
        say("    %-28s %s" % (name, mod.rel(p) if p else "MISSING"))
        if not p and name in ("descr_strat.txt", "descr_regions.txt", "map_regions.tga"):
            bad("%s is missing" % name)
    texts = mod.campaign_text_files(campaign)
    say("    %-28s %d file(s)" % ("text tables", len(texts)))
    say("")
    if problems:
        say("PROBLEMS")
        for p in problems:
            say("    " + p)
        return "\n".join(out)

    # ---- factions ----
    step("factions...")
    facs = mod.factions()
    names = [n for n, _ in facs]
    s = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
    in_strat = [fb.name for fb in s.factions]
    say("FACTIONS: %d in descr_sm_factions.txt, %d blocks in descr_strat.txt" % (len(names), len(in_strat)))
    for n in in_strat:
        if n not in names:
            bad("descr_strat.txt has a block for '%s', which descr_sm_factions.txt does not know" % n)
    no_culture = [n for n, c in facs if not c]
    if no_culture:
        bad("no culture line for: %s" % ", ".join(no_culture))
    missing_pool = [n for n in in_strat if n != "slave" and not (mod.name_pool(n) or {}).get("characters")]
    if missing_pool:
        bad("no name list in descr_names.txt for: %s" % ", ".join(missing_pool))
    say("    cultures: %s" % ", ".join(sorted({c for _, c in facs if c})))

    # ---- units, buildings ----
    step("units and buildings...")
    units = read_units(mod.load(mod.file("edu")))
    types = {u.type for u in units}
    say("UNITS: %d in export_descr_unit.txt (%d mercenaries, %d ships)" % (
        len(units), sum(u.mercenary for u in units), sum(u.category == "ship" for u in units)))
    no_owner = [u.type for u in units if not u.ownership]
    if no_owner:
        bad("%d unit(s) without an ownership line, e.g. %s" % (len(no_owner), ", ".join(no_owner[:3])))
    blds = read_buildings(mod.load(mod.file("edb")))
    chains = {b.name: b for b in blds}
    say("BUILDINGS: %d chains, %d levels in export_descr_buildings.txt" % (
        len(blds), sum(len(b.levels) for b in blds)))
    if not any(b.lower().startswith("core") for b in chains):
        say("    (no core_building chain: settlements are not grown by the governor's building)")

    # ---- map ----
    step("map...")
    regions = mod.regions(campaign)
    tiles = mod.city_tiles(campaign)
    from .mapedit import ports
    prt = ports(mod, campaign)
    owners = s.owners()
    img = mod.region_map(campaign)
    say("MAP: %d x %d tiles, %d regions in descr_regions.txt, %d town pixels, %d ports" % (
        img.width, img.height, len(regions), len(tiles), len(prt)))
    say("    settlements in descr_strat.txt: %d; regions left out (the game makes rebel villages): %d" % (
        len(owners), sum(1 for r in regions if r not in owners and tiles.get(r))))
    for r in owners:
        if r not in regions:
            bad("settlement of '%s' in descr_strat.txt, but no such region in descr_regions.txt" % r)
        elif r not in tiles:
            bad("region '%s' has no town pixel (black) in map_regions.tga" % r)
    no_pixel = [r for r in regions if r not in tiles]
    if no_pixel:
        bad("%d region(s) without a town pixel: %s" % (len(no_pixel), ", ".join(no_pixel[:5])))
    seen = {}
    for fb in s.factions:
        for st in fb.settlements:
            if st.region in seen:
                bad("%s has two settlement blocks (%s and %s) - the game crashes" % (st.region, seen[st.region], fb.name))
            seen[st.region] = fb.name

    # ---- start positions ----
    step("characters...")
    nchar = sum(len(fb.characters) for fb in s.factions)
    say("CHARACTERS: %d in descr_strat.txt" % nchar)
    for n in characters_after_tree(s):
        bad("%s: a character stands after the family tree lines - the game crashes" % n)
    unknown_units, unknown_buildings, off_map, bad_names = set(), set(), [], []
    pools = {}
    for fb in s.factions:
        pool = pools.setdefault(fb.name, mod.name_pool(fb.name) or {})
        first = set(pool.get("characters", []))
        for c in fb.characters:
            lines = s.lines[c.start:c.end]
            for l in lines:
                t = tokens(l)
                if t[:1] == ["unit"]:
                    from .start import unit_name
                    u = unit_name(l)
                    if u not in types:
                        unknown_units.add(u)
            if c.xy and not (0 <= c.xy[0] < img.width and 0 <= c.xy[1] < img.height):
                off_map.append("%s (%s)" % (c.name, fb.name))
            if fb.name != "slave" and first and c.name and c.name.split()[0] not in first and c.named:
                bad_names.append("%s (%s)" % (c.name, fb.name))
        for st in fb.settlements:
            _, bs = settlement_info(s.lines[st.start:st.end])
            for chain, level in bs:
                b = chains.get(chain)
                if not b or not b.level(level):
                    unknown_buildings.add("%s %s" % (chain, level))
    if unknown_units:
        bad("units in armies that export_descr_unit.txt lacks: %s" % ", ".join(sorted(unknown_units)[:8]))
    if unknown_buildings:
        bad("buildings in towns that export_descr_buildings.txt lacks: %s" % ", ".join(sorted(unknown_buildings)[:8]))
    if off_map:
        bad("characters off the map: %s" % ", ".join(off_map[:5]))
    if bad_names:
        say("    note: %d named character(s) whose first name is not in their faction's list "
            "(fine if the game has the string), e.g. %s" % (len(bad_names), ", ".join(bad_names[:3])))
    say("DIPLOMACY: %d core_attitudes, %d faction_relationships lines" % (
        sum(1 for l in s.lines if tokens(l)[:1] == ["core_attitudes"]),
        sum(1 for l in s.lines if tokens(l)[:1] == ["faction_relationships"])))

    # ---- deep: rehearse the tool's work for every faction ----
    if deep:
        say("")
        say("REHEARSAL (in memory, nothing written)")
        fails = rehearse(mod.data, campaign, step)
        ok = len([f for f in in_strat if f != "slave"]) - len(fails)
        say("    %d faction(s) fine" % ok)
        for fac, msg in fails:
            say("    %s: %s" % (fac, msg))
            if "internal" in msg or "Error" in msg:
                bad("rehearsal for %s: %s" % (fac, msg))

    say("")
    if problems:
        say("PROBLEMS (%d)" % len(problems))
        for p in problems:
            say("    " + p)
    else:
        say("No problems found.")
    say("(%.1f s)" % (time.time() - t0))
    return "\n".join(out)


def rehearse(data, campaign, step=None):
    """For every faction: an edit (take the nearest rebel town with a garrison,
    add an army, a spy and a fleet) and a new faction cloned from it - all in
    memory - then the file checks. [(faction, what went wrong)]."""
    from .build import build
    from .edit import edit, read_faction
    from .moddata import ModData
    from .units import faction_units
    base = ModData(data)
    s0 = Strat(base.load(base.campaign_file(campaign, "descr_strat.txt")))
    owners, tiles = s0.owners(), base.city_tiles(campaign)
    rebels = [r for r, o in owners.items() if o == "slave" and tiles.get(r)]
    armies0 = {c.xy for fb in s0.factions for c in fb.characters if c.xy and _has_army(s0.lines[c.start:c.end])}
    fails = []
    facs = [fb.name for fb in s0.factions if fb.name != "slave"]
    for n, fac in enumerate(facs, 1):
        if step:
            step("rehearsing %s (%d/%d)..." % (fac, n, len(facs)))
        try:
            mod = ModData(data)
            now = read_faction(mod, campaign, fac)
            if not now["regions"]:
                continue
            cap = tiles.get(now["regions"][0])
            units = [u.type for u in faction_units(mod, fac)][:3]
            ships = [u.type for u in faction_units(mod, fac, ships=True, mercs=True)][:2]
            from .strat import faction_names
            pool_names = (mod.name_pool(fac) or {}).get("characters") or ["X"]
            used_names = set(faction_names(Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))), fac))
            free = [n for n in pool_names if n not in used_names] or pool_names
            first = free[0]
            spare = (free[1:] + free)[:2]           # the rehearsal's spy and fleet: names of their own
            take = sorted(rebels, key=lambda r: abs(tiles[r][0] - cap[0]) + abs(tiles[r][1] - cap[1]))[:1] if cap else []
            land = sea = None
            if cap:
                for d in range(2, 12):
                    for dx in range(-d, d + 1):
                        for dy in (-d, d):
                            xy = (cap[0] + dx, cap[1] + dy)
                            if land is None and not mod.tile_problem(campaign, xy, "general", True,
                                                                     armies0 | set(tiles.values())):
                                land = xy
                            if sea is None and ships and not mod.tile_problem(campaign, xy, "admiral", True, set()):
                                sea = xy
                    if land and (sea or not ships):
                        break
            chars = []
            if land and units:
                chars.append({"kind": "army", "name": first, "age": 30, "units": units, "xy": land})
            if cap:
                chars.append({"kind": "spy", "name": spare[0], "age": 25, "units": [], "xy": cap})
            if sea:
                chars.append({"kind": "fleet", "name": spare[1], "age": 30, "units": ships, "xy": sea})
            plan = edit(mod, campaign, fac, {"take": take, "garrisons": {r: units[:2] for r in take if units},
                                             "characters": chars})
            _file_checks(plan, mod, campaign, fac, "edit", fails)
            mod = ModData(data)
            plan = build(mod, campaign, fac, "zzcheck", {
                "display_name": "Check", "short_name": "Check", "adjective": "Check", "copy_art": False,
                "raise_faction_limit": True,                  # in memory only: a full campaign still rehearses
                "start": {"regions": now["regions"][:1] + take, "leader": {"name": first}}})
            _file_checks(plan, mod, campaign, fac, "new faction", fails)
        except ValueError as e:
            fails.append((fac, "refused: %s" % e))
        except Exception as e:
            fails.append((fac, "%s: %s | %s" % (type(e).__name__, e, traceback.format_exc().splitlines()[-2].strip())))
    return fails


def _file_checks(plan, mod, campaign, fac, what, fails):
    s = Strat(plan.files[mod.campaign_file(campaign, "descr_strat.txt")])
    msgs = ["internal: character after the family tree of %s" % n for n in characters_after_tree(s)]
    seen = set()
    for fb in s.factions:
        for st in fb.settlements:
            if st.region in seen:
                msgs.append("internal: two settlement blocks for %s" % st.region)
            seen.add(st.region)
    depth = sum(l.count("{") - l.count("}") for l in s.lines)
    if depth:
        msgs.append("internal: braces do not balance (%+d)" % depth)
    for m in msgs:
        fails.append((fac, "%s: %s" % (what, m)))
