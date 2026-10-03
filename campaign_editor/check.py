"""Check mod: read every file the tool works with and say what it found and
what it could not make sense of. Read-only - nothing is written.

The quick check reads the files; the deep one also rehearses the tool's own
work in memory for every faction (an edit that takes a rebel town with a
garrison, a new army, agent and fleet, and a new faction cloned from it) and
checks the result the way the game would read it."""

import os
import time
import traceback

from .buildings import is_temple, read_buildings, settlement_info
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
    from .strat import headers_out_of_order
    for n, _ in headers_out_of_order(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))):
        bad("%s: its first lines in descr_strat.txt are out of the games' order (denari before superfaction / "
            "ai_label...) - the game starts it without its towns; Load offers to put them in order" % n)
    from .buildings import pop_problem, population_of, settlement_info, settlement_kind
    strat_f = mod.load(mod.campaign_file(campaign, "descr_strat.txt"))
    for fb in s.factions:
        for st in fb.settlements:
            lines = [l.rstrip("\r\n") for l in strat_f.texts()[st.start:st.end]]
            why = pop_problem(population_of(lines), settlement_info(lines)[0], settlement_kind(lines) == "castle",
                              mod)
            if why:
                bad("%s (%s): %s - the game stops reading descr_strat.txt there (towns, armies and diplomacy after "
                    "it are lost); set the population or the level on the Settlements tab" % (st.region, fb.name, why))
    from .limits import game_kind
    if game_kind(mod) == "medieval2":
        from .campaignrules import game_data, read as read_rules
        from .moddata import _ci
        from . import family as FM
        gd = game_data(mod)
        cdb = _ci(mod.data, "descr_campaign_db.xml") or (_ci(gd, "descr_campaign_db.xml") if gd else None)
        rule = next((r for r in read_rules(cdb) if r.key == "max_number_of_children"), None) if cdb else None
        most_allowed = int(rule.value) if rule is not None and str(rule.value).isdigit() else None
        if most_allowed is not None:
            for fb in s.factions:
                try:
                    tree = FM.read(strat_f, fb.name)["tree"]
                except Exception:
                    continue
                for father, wife, kids in tree:
                    if len(kids) > most_allowed:
                        bad("%s: %s has %d children, descr_campaign_db.xml max_number_of_children is %d - the game "
                            "stops reading descr_strat.txt at that family's relative line; raise the number (Tools > "
                            "Campaign rules) or take a child out" % (fb.name, father, len(kids), most_allowed))
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
    md = _modeldb_report(mod)
    if md:
        (bad if md[0] else say)(md[1])

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
        elif regions[r].get("wasteland"):
            bad("'%s' is a wasteland region (no town) but descr_strat.txt gives it a settlement" % r)
        elif r not in tiles:
            bad("region '%s' has no town pixel (black) in map_regions.tga" % r)
    waste = [r for r in regions if regions[r].get("wasteland")]
    if waste:
        say("    wasteland regions (REX / M2EX: no town, no owner): %d - %s" % (len(waste), ", ".join(waste[:5])))
    no_pixel = [r for r in regions if r not in tiles and not regions[r].get("wasteland")]
    if no_pixel:
        bad("%d region(s) without a town pixel: %s" % (len(no_pixel), ", ".join(no_pixel[:5])))
    seen = {}
    for fb in s.factions:
        for st in fb.settlements:
            if st.region in seen:
                bad("%s has two settlement blocks (%s and %s) - the game crashes" % (st.region, seen[st.region], fb.name))
            seen[st.region] = fb.name

    # ---- the engine's limits, win conditions, rebels ----
    step("limits...")
    for msg, fault in engine_limits(mod, campaign, regions, units, blds, img):
        (bad if fault else say)(msg)
    for msg in win_condition_problems(mod, campaign, regions, names):
        bad(msg)
    for msg in rebel_problems(mod, units):
        bad(msg)
    for msg in slaves_problems(mod, regions):
        bad(msg)
    from .emergence import problems as later_problems       # emergent / shadow / split-off factions
    faults, notes = later_problems(mod, campaign)
    for msg in faults:
        bad(msg)
    for msg in notes:
        say("    note: " + msg)
    ring = town_ring_problems(mod, campaign)
    serious = [m for s_, m in ring if s_]
    for m in serious[:8]:
        bad(m)
    if len(serious) > 8:
        bad("... and %d more town / port placement problem(s) of the same kind" % (len(serious) - 8))
    light = [m for s_, m in ring if not s_]
    if light:
        say("    note: %d town(s) touch another region's land (vanilla never does; the game may still run - "
            "HLR has 6), e.g. %s" % (len(light), light[0]))

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
            temples = [c for c, _ in bs if is_temple(c)]
            if len(temples) > 1:
                bad("%s holds %d temples (%s) - the game stops: 'Settlement specified with multiple temple "
                    "buildings'; keep one" % (st.region, len(temples), ", ".join(temples)))
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
    for msg in building_condition_problems(mod):
        bad(msg)
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


def _modeldb_report(mod):
    """(fault, text) on Medieval II's battle_models.modeldb when the game reads it, or None."""
    from . import modeldb as MDB
    src, _ = MDB.find(mod)
    if not src or MDB.text_source(mod):
        return None
    try:
        db = MDB.load(src)
    except Exception as e:
        return True, "battle_models.modeldb cannot be read (%s) - a new faction or a unit pack cannot add its " \
                     "models' textures until it is put right" % e
    note = db.uncounted_note()
    if note:
        return False, "    note: " + note
    return False, "    battle_models.modeldb: %d models (%s)" % (len(db.models), mod.rel(src))


def building_condition_problems(mod):
    """[message]: export_descr_buildings.txt lines naming a hidden resource, a resource or a religion the mod does
    not have - the game stops at start ('Hidden resource condition, unrecognised hidden resource 'britain''; a
    tester's Barbarian Invasion units brought into plain Rome). One message per kind, with the first lines."""
    from .packs import known_conditions, _COND
    if not mod.file("edb"):
        return []
    known = known_conditions(mod)
    found = {}
    for n, line in enumerate(mod.load(mod.file("edb")).texts(), 1):
        body = line.split(";")[0]
        t = body.split()
        if not t or t[0] == "hidden_resources":
            continue
        if t[0] == "religious_belief" and len(t) > 1:
            rel = known["religion"]
            if rel is None or t[1].lower() not in rel:
                found.setdefault("religion", []).append("%s (line %d)" % (t[1], n))
            continue
        i = body.find("requires")
        if i < 0 or "(" in body[i:]:
            continue
        for m in _COND.finditer(body[i:]):
            have = known.get(m.group(2))
            if have is not None and m.group(3).lower() not in have:
                found.setdefault(m.group(2), []).append("%s (line %d)" % (m.group(3), n))
    words = {"hidden_resource": "hidden resource(s) the hidden_resources line does not list",
             "resource": "resource(s) descr_sm_resources.txt does not have",
             "religion": "religion(s) this game does not have (religious_belief)"}
    return ["export_descr_buildings.txt names %s - the game stops at start: %s" % (words[k], ", ".join(v[:5]) +
            (" and %d more" % (len(v) - 5) if len(v) > 5 else "")) for k, v in found.items()]


def hidden_resources(mod):
    """The names on export_descr_buildings.txt's hidden_resources line."""
    for line in mod.load(mod.file("edb")).texts():
        t = tokens(line.split(";")[0])
        if t[:1] == ["hidden_resources"]:
            return t[1:]
    return []


def engine_limits(mod, campaign, regions, units, blds, img):
    """[(message, fault)] - the counts against the game's limits: factions against the engine's own
    max_factions (limits.faction_limit), the rest against the original exe's hard limits
    (limits.HARD_LIMITS). Over a limit is a fault on the original exe; with REX / M2EX beside the data there is
    no limit at all - one line says so (limits.md THE RULE)."""
    from .limits import HARD_LIMITS, LIMIT_WORDS, faction_limit, game_kind
    kind = game_kind(mod)
    hard = HARD_LIMITS.get(kind, {})
    lim = faction_limit(mod)
    engine = lim.get("engine")
    counts = {"regions": len(regions) + 1, "map_size": max(img.width, img.height), "units": len(units),
              "chains": len(blds), "levels": max((len(b.levels) for b in blds), default=0),
              "hidden_resources": len(hidden_resources(mod))}
    exe = "Rome" if kind == "rome" else "Medieval II"
    if engine:                  # the user's rule: REX / M2EX = no limits at all - no fault, no warning, no count
        out = [("LIMITS: none - %s beside the game (factions, regions, religions, cultures, units, buildings: no "
                "limit; max_factions follows the factions on every Apply)" % engine[:-4], False)]
        from .gamefix import missing_engine_files
        missing = missing_engine_files(mod)
        if missing:
            out.append(("    the mod has no %s of its own (the game's data has) - %s may run it on its built-in "
                        "defaults; Load offers to copy them in" % (", ".join(missing), engine[:-4]), False))
        return out
    out = [("LIMITS (the original %s exe: no REX / M2EX found beside the game)" % exe, False)]
    nfac = len(mod.factions())
    out.append(("    %-46s %5d of %d (%s)" % ("factions (slave included)", nfac, lim["max"],
                                             ("max_factions in %s" % os.path.basename(lim["file"])) if lim.get("written")
                                             else ("%s's default" % engine[:-4]) if engine else "the original exe"),
                False))
    if nfac > lim["max"]:
        out.append(("%d factions, the game takes %d - it closes at the start (\"Too many factions described\")"
                    % (nfac, lim["max"]), True))
    for key, most in hard.items():                  # the original exe only (an engine returned above)
        n = counts.get(key)
        over = n is not None and n > most
        out.append(("    %-46s %5s of %d%s" % (LIMIT_WORDS[key], n, most, "  <- OVER" if over else ""), False))
        if over:
            out.append(("%s: %d, the original game stops at %d - it may crash or refuse to load"
                        % (LIMIT_WORDS[key], n, most), True))
    return out


def win_condition_problems(mod, campaign, regions, factions):
    """Regions and factions descr_win_conditions.txt names that do not exist (the game crashes when
    that faction is played - TWC "Crashes and how to fix them")."""
    p = mod.campaign_file(campaign, "descr_win_conditions.txt")
    if not p:
        return []
    out, known = [], set(factions)
    from .packs import game_kind
    m2 = game_kind(mod) == "medieval2"
    for i, line in enumerate(mod.load(p).texts()):
        t = tokens(line.split(";")[0])
        if t[:1] == ["short_campaign"]:
            t = t[1:]
            if m2 and t[:1] != ["hold_regions"]:
                out.append("descr_win_conditions.txt line %d: 'short_campaign %s' - Medieval II wants hold_regions "
                           "right after short_campaign (even an empty list) and reads no further: every faction after "
                           "it has no victory conditions; Load offers to put it right" % (i + 1, " ".join(t)))
        if t[:1] == ["hold_regions"]:
            for r in t[1:]:
                if r not in regions:
                    out.append("descr_win_conditions.txt line %d: region '%s' does not exist - the game crashes "
                               "when that faction is played" % (i + 1, r))
        elif t[:1] == ["outlive"]:                       # Medieval II: outlive <factions>
            for fac in t[1:]:
                if fac not in known:
                    out.append("descr_win_conditions.txt line %d: faction '%s' does not exist" % (i + 1, fac))
    return out


def rebel_problems(mod, units):
    """Medieval II: rebel types listing units the slave faction may not own - the game crashes (TWC
    "Crashes and how to fix them"). Vanilla RTW has five such units and runs, so Rome is not checked."""
    from .limits import game_kind
    if game_kind(mod) != "medieval2":
        return []
    p = _data_file(mod, "descr_rebel_factions.txt")
    if not p:
        return []
    from .masstown import rebel_types
    owners = {u.type: set(u.ownership) for u in units}
    out = []
    for cur, names in rebel_types(mod).items():
        for u in names:
            if u not in owners:
                out.append("descr_rebel_factions.txt, %s: unit '%s' is not in export_descr_unit.txt" % (cur, u))
            elif "slave" not in owners[u]:
                out.append("descr_rebel_factions.txt, %s: unit '%s' has no 'slave' in its ownership - the game "
                           "crashes when these rebels appear" % (cur, u))
    return out


def town_ring_problems(mod, campaign):
    """mapedit.ring_problems over the whole map: [(serious, message)]."""
    from .mapedit import owner_of, ports, ring_problems
    towns = mod.city_tiles(campaign)
    return ring_problems(mod, campaign, owner_of(mod, campaign), towns, ports(mod, campaign))


def slaves_problems(mod, regions):
    """Rome: a region without the 'slaves' resource while the mod's other regions have it (every vanilla
    region does; HLR uses none - the mod's own rule counts)."""
    from .limits import game_kind
    if game_kind(mod) != "rome" or not regions:
        return []
    def res(v):
        return [x.strip() for x in str(v.get("resources") or "").split(",")]
    without = [r for r, v in regions.items() if "slaves" not in res(v)]
    if not without or len(without) * 2 > len(regions):
        return []
    return ["%d region(s) lack the 'slaves' resource the mod's other regions have: %s" % (
        len(without), ", ".join(sorted(without)[:6]))]


def _data_file(mod, name):
    from .moddata import _ci
    return _ci(mod.data, name)


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
            from .strat import first_names
            pool_names = first_names(mod.name_pool(fac), "general") or ["X"]
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


def mod_summary(mod, campaign=None):
    """A short picture of the mod for the log (so every report shows what the mod is - a tester's idea): the game
    and engine, its campaigns, factions and cultures, regions and who holds the towns, how many units and building
    chains, the map's size, and which of its files are its own (the rest the game's). No game files, just counts and
    names; never raises (a part that cannot be read says so)."""
    import collections
    out = []

    def part(title, fn):
        try:
            out.append("    %-11s %s" % (title, fn()))
        except Exception as e:
            out.append("    %-11s (not read: %s)" % (title, e))
    from .limits import engine_of, game_kind
    out.append("Mod at a glance: %s" % mod.data)
    part("game", lambda: "%s, engine %s" % (game_kind(mod), engine_of(mod) or "none (the original exe)"))
    camps = mod.campaigns()
    campaign = campaign or ("imperial_campaign" if "imperial_campaign" in camps else (camps[0] if camps else None))
    part("campaigns", lambda: ", ".join(camps) or "none")
    facs = mod.factions()
    part("factions", lambda: "%d: %s" % (len(facs), ", ".join(n for n, _ in facs)))
    part("cultures", lambda: ", ".join(sorted({c for _, c in facs if c})))
    if campaign:
        def towns():
            s = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
            held = collections.Counter(s.owners().values())
            return "%d regions; towns held: %s" % (len(mod.regions(campaign)), ", ".join(
                "%s %d" % (k, v) for k, v in held.most_common()))
        part("regions", towns)
        part("map", lambda: "%d x %d tiles" % (mod.region_map(campaign).width, mod.region_map(campaign).height))
    def count(key, word):
        p = mod.file(key)
        if not p:
            return "none"
        n = sum(1 for l in mod.load(p).texts() if l.split()[:1] == [word])
        own = os.path.normcase(os.path.abspath(p)).startswith(os.path.normcase(os.path.abspath(mod.data)))
        return "%d (%s)" % (n, "its own file" if own else "the game's file")
    part("units", lambda: count("edu", "type"))
    part("buildings", lambda: count("edb", "building"))
    def own_files():
        tops = collections.Counter()
        for dp, dn, fs in os.walk(mod.data):
            dn[:] = [d for d in dn if not d.startswith("CampaignEditor_")]
            rel = os.path.relpath(dp, mod.data).replace("\\", "/")
            tops[rel.split("/")[0] if rel != "." else "(data root)"] += len(fs)
        return "%d: %s" % (sum(tops.values()), ", ".join("%s %d" % kv for kv in tops.most_common(12)))
    part("own files", own_files)
    return "\n".join(out)
