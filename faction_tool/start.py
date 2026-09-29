"""The new faction's start in descr_strat.txt: lists, block, settlements,
characters and diplomacy."""

import re
from types import SimpleNamespace

from .strat import FEMALE_KINDS, Strat, RE_XY, character_line, first_names, village_block
from .textio import strip_comment, tokens


def _set_xy(text, xy):
    return RE_XY.sub("x %d, y %d" % xy, text, 1)


def _strip_sub_faction(text):
    return re.sub(r"(character\s*,?\s*)sub_faction\s+\S+\s*,\s*", r"\1", text, 1)


def default_army(strat, template):
    """The unit lines of the template leader's army (or of its first general)."""
    fb = strat.faction(template)
    if not fb:
        return []
    chars = [c for c in fb.characters if c.role == "leader"] or [c for c in fb.characters if c.kind in ("named character", "general")]
    if not chars:
        return []
    c = chars[0]
    return [l for l in strat.lines[c.start:c.end] if tokens(l)[:1] == ["unit"]]


MAX_UNITS = 20


def unit_upkeep(edu):
    """{unit type: upkeep} from stat_cost (turns, cost, upkeep, ...)."""
    out, cur = {}, None
    for l in edu.texts():
        t = tokens(l)
        if t[:1] == ["type"]:
            cur = " ".join(strip_comment(l).split()[1:])
        elif t[:1] == ["stat_cost"] and cur and len(t) >= 4:
            try:
                out[cur] = int(t[3])
            except ValueError:
                pass
    return out


def template_pool(strat, template, upkeep):
    """[[unit line, count]] of the template's own starting armies, bodyguards
    of named characters left out, cheapest upkeep first."""
    pool = {}
    fb = strat.faction(template)
    for c in fb.characters if fb else []:
        if c.kind not in ("named character", "general"):
            continue                        # admirals' fleets and agents are not an army's pool
        units = _units(strat.lines[c.start:c.end])
        if c.named and units:
            units = units[1:]
        for l in units:
            name = unit_name(l)
            pool.setdefault(name, [l, 0])
            pool[name][1] += 1
    return sorted(pool.values(), key=lambda e: (upkeep.get(unit_name(e[0]), 0), unit_name(e[0])))


def cheap_garrison(strat, template, upkeep, n):
    """n unit lines from the template pool: the cheapest few, one of each in turn."""
    order = [e[0] for e in template_pool(strat, template, upkeep)][:3]
    return [order[i % len(order)] for i in range(n)] if order else []


def balanced_army(strat, template, new_towns, upkeep, garrison):
    """A leader's army sized like the other factions' start, not a copy of the
    template leader's (often among the strongest in the mod).

    Target: the median size and upkeep of the leader armies of factions with
    about as many towns (up to max(3, towns + 2)). The garrison that joins
    with the capital counts toward it. The rest is the template leader's
    bodyguard plus an escort from the units of the template's own starting
    armies (bodyguards left out), cheapest first, one of each in turn.
    Returns (unit lines, target units, target upkeep)."""
    def army(c):
        return _units(strat.lines[c.start:c.end])

    def cost(lines):
        return sum(upkeep.get(unit_name(l), 0) for l in lines)

    limit = max(3, new_towns + 2)
    leaders = [army(c) for fb in strat.factions if fb.name != "slave" and len(fb.settlements) <= limit
               for c in fb.characters if c.role == "leader"]
    leaders = [a for a in leaders if a] or [army(c) for fb in strat.factions for c in fb.characters
                                            if c.role == "leader" and army(c)]
    if not leaders:
        return default_army(strat, template), 0, 0
    sizes = sorted(len(a) for a in leaders)
    costs = sorted(cost(a) for a in leaders)
    size_t, cost_t = sizes[len(sizes) // 2], costs[len(costs) // 2]

    lead = default_army(strat, template)
    out = lead[:1]                                    # the bodyguard
    have_n = len(out) + len(garrison)
    have_c = cost(out) + cost(garrison)
    order = template_pool(strat, template, upkeep)
    while have_n < size_t and any(e[1] for e in order):
        for e in order:
            if not e[1] or have_n >= size_t:
                continue
            c = upkeep.get(unit_name(e[0]), 0)
            if have_c + c > cost_t * 1.1 and have_n > 1:
                have_n = size_t                       # the budget is spent
                break
            out.append(e[0])
            e[1] -= 1
            have_n += 1
            have_c += c
    return out, size_t, cost_t


def _has_army(lines):
    return any(tokens(l)[:1] == ["army"] for l in lines)


def _units(lines):
    return [l for l in lines if tokens(l)[:1] == ["unit"]]


def unit_name(line):
    """'unit   east horse archer   exp 0 armour 0 weapon_lvl 0' -> 'east horse archer'."""
    body = line.strip()[len("unit"):].strip()
    m = re.split(r"\s+exp\s+\d+", body)
    return m[0].strip()


def _with_buildings(plan, f, region, raw, picked, size=None):
    """The settlement block with the buildings picked by hand, checked against
    export_descr_buildings: the level exists, the faction may build it, and the
    settlement is big enough."""
    from .buildings import available, ranks_ok, read_buildings, set_buildings, sized
    edb = plan.files.get(plan.mod.file("edb")) or (plan.mod.load(plan.mod.file("edb")) if plan.mod.file("edb") else None)
    known = {b.name: b for b in read_buildings(edb)} if edb is not None else {}
    raw, town_level = sized(plan, f, region, raw, picked or [], size, known)
    if picked is None:
        return raw
    culture = plan.mod.culture(plan.template)
    for chain, level in picked:
        b = known.get(chain)
        lv = b.level(level) if b else None
        if known and not lv:
            raise ValueError("%s: %s %s is not in export_descr_buildings.txt" % (region, chain, level))
        if lv and not available(lv, plan.new, culture, plan.template):
            plan.warn(f, "%s: %s is not for %s's faction list (%s)" % (region, level, plan.template, lv.requires))
        if lv and not chain.lower().startswith("core") and not ranks_ok(lv, town_level):
            plan.warn(f, "%s: %s needs a %s, the settlement is a %s" % (region, level, lv.settlement_min, town_level))
    if len({c for c, _ in picked}) != len(picked):
        raise ValueError("%s: one level per building chain" % region)
    plan.note(f, "%s: %d building(s) set by hand (%s)" % (region, len(picked), town_level))
    return set_buildings(raw, picked, f.make)


def build_start(plan, campaign, start):
    """start = {
        'regions': [...], 'capital': region,
        'leader': {'name': 'First Surname', 'age': 40},
        'heir': {...} or None,
        'army': [unit lines] or None (template leader's army),
        'denari': 5000, 'ai': 'balanced smith' or None,
        'playable': True, 'diplomacy': 'neutral' | 'template'}"""
    mod, t, new = plan.mod, plan.template, plan.new
    path = mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(path)
    s = Strat(f)
    if s.faction(new):
        raise ValueError("descr_strat.txt already has a faction block for %s" % new)
    tb = s.faction(t)
    if not tb:
        raise ValueError("template %s has no block in this campaign's descr_strat.txt" % t)
    from .regionedit import plan_land
    tiles, own = plan_land(plan, campaign)          # new regions of the same Apply count as regions
    new_regions = {r["name"] for r in (plan.opts.get("regions") or {}).get("new") or []}
    img = mod.region_map(campaign)
    plan.note(f, "map: %s (%dx%d)" % (mod.rel(mod.campaign_file(campaign, "map_regions.tga")), img.width, img.height))
    regions = list(start.get("regions") or [])
    if not regions:
        raise ValueError("pick at least one starting settlement")
    capital = start.get("capital") or regions[0]
    if capital not in regions:
        regions.insert(0, capital)
    else:
        regions.remove(capital)
        regions.insert(0, capital)

    picked_buildings = {r: [tuple(x) for x in v] for r, v in (start.get("buildings") or {}).items()}
    sizes = start.get("sizes") or {}
    moved_blocks = []          # raw lines of settlement blocks
    joined = {}                # region -> raw character chunks that join with the town
    removals = []              # (start, end) ranges to delete
    edits = {}                 # line index -> new text (relocated characters)
    relocate = []              # (region, character) the old owner keeps
    losers = {}
    for r in regions:
        st = s.settlement_of(r)
        if st is None:
            if (r not in plan.mod.regions(campaign) and r not in new_regions) or not tiles.get(r):
                raise ValueError("%s is not a region of this campaign's map" % r)
            # the game makes such a region a rebel village: write that village out
            st = SimpleNamespace(owner="slave", start=None, end=None)
            block_raw = [f.make(l) for l in village_block(r, new)]
            plan.note(f, "%s: the rebel village (no settlement in descr_strat.txt) is written as a village" % r)
        else:
            if st.owner == new:
                continue
            block_raw = list(f.raw[st.start:st.end])
        if r in picked_buildings or r in sizes:
            block_raw = _with_buildings(plan, f, r, block_raw, picked_buildings.get(r), sizes.get(r))
        moved_blocks.append(block_raw)
        if st.start is not None:
            removals.append((st.start, st.end))
        losers.setdefault(st.owner, []).append(r)
        tile = tiles.get(r)
        if not tile:
            plan.warn(f, "%s: no city pixel found in map_regions.tga - characters there were not checked" % r)
            continue
        for c in s.characters_at(tile):
            if c.owner == st.owner and (not c.named or st.owner == "slave") and c.role is None:
                chunk = list(f.raw[c.start:c.end])
                chunk[0] = _strip_sub_faction(chunk[0])
                joined.setdefault(r, []).append((c.name, c.kind, chunk))
                removals.append((c.start, c.end))
            else:
                relocate.append((r, c))
    for owner, rs in losers.items():
        fb = s.faction(owner)
        left = [x for x in fb.settlements if x.region not in regions]
        plan.note(f, "%s gives up %s" % (owner, ", ".join(rs)))
        if owner != "slave" and not left:
            plan.warn(f, "%s is left with no settlement - it starts as a horde or dies on turn 1" % owner)

    # A settlement takes one army at the start: a second army placed on a
    # garrisoned city tile is refused by the game and stays stuck on the tile.
    # Characters with an army that do not garrison a town stand on a free
    # tile of its region instead.
    removed = set()
    for a, b in removals:
        removed.update(range(a, b))
    armies_at = set()          # tiles with an army that stays where it is
    taken = set(tiles.values())
    for fb in s.factions:
        for c in fb.characters:
            if c.start in removed or not c.xy:
                continue
            taken.add(c.xy)
            if _has_army(s.lines[c.start:c.end]) and not any(c is x for _, x in relocate):
                armies_at.add(c.xy)

    def place(region, what):
        xy = mod.free_tile(campaign, region, taken, start=tiles.get(region), own=own(region))
        if not xy:
            raise ValueError("%s: no free land tile next to %s for %s - pick another town or edit "
                             "descr_strat.txt by hand" % (region, region, what))
        taken.add(xy)
        return xy

    for r, c in relocate:
        owner = s.faction(c.owner)
        keep = [x.region for x in owner.settlements if x.region not in regions and tiles.get(x.region)]
        if not keep:
            raise ValueError("%s: %s of %s stands in the town and %s has no other settlement to "
                             "move him to - pick another town or edit descr_strat.txt by hand"
                             % (r, c.name, c.owner, c.owner))
        xy = tiles[keep[0]]
        where = keep[0]
        if _has_army(s.lines[c.start:c.end]):
            if xy in armies_at:
                xy = place(keep[0], c.name)
                where = "next to " + keep[0]
            else:
                armies_at.add(xy)
        edits[c.start] = _set_xy(f.text(c.start), xy)
        plan.note(f, "%s: %s of %s moved to %s" % (r, c.name, c.owner, where))

    # ---- the new faction's own characters ----
    cap_xy = tiles.get(capital)
    if not cap_xy:
        raise ValueError("no city pixel for the capital %s in map_regions.tga" % capital)
    mode = start.get("army_mode") or "balanced"
    template_army = default_army(s, t)
    if not template_army and not start.get("army"):
        plan.warn(f, "the template leader has no army to copy - the leader starts with no units")
    pool = plan.mod.name_pool(new) or plan.mod.name_pool(t)

    def merge(role_units, region, into):
        """Fold the armies that join with `region` into `into`'s units; the
        characters that led them are dropped. Agents without an army stay."""
        units = list(role_units)
        for name, kind, chunk in joined.get(region, []):
            if not _has_army(chunk):
                continue
            extra = _units(chunk)
            room = MAX_UNITS - len(units)
            units.extend(extra[:max(room, 0)])
            plan.note(f, "%s: %s (%s) hands his %d unit(s) to %s"
                      % (region, name, kind, min(len(extra), max(room, 0)), into))
            if len(extra) > room:
                plan.warn(f, "%s: %d unit(s) of %s's garrison dropped - an army holds %d"
                          % (region, len(extra) - max(room, 0), name, MAX_UNITS))
        joined[region] = [j for j in joined.get(region, []) if not _has_army(j[2])]
        return units

    # The towns' old garrisons (rebel levies, often costly mercenaries) give
    # way to the new faction's own units unless start['garrison'] == 'keep'.
    replace = start.get("garrison", "replace") != "keep"
    if replace:
        edu = plan.files.get(mod.file("edu"))
        upkeep_all = unit_upkeep(edu) if edu is not None else {}
        for r in regions:
            if r in (start.get("garrisons") or {}):
                continue                    # a garrison picked by hand replaces it below
            kept = []
            for name, kind, chunk in joined.get(r, []):
                units = _units(chunk)
                if not _has_army(chunk) or not units:
                    kept.append((name, kind, chunk))
                    continue
                if r == capital:
                    plan.note(f, "%s: %s (%s) and his %d unit(s) leave - the leader's army holds the town"
                              % (r, name, kind, len(units)))
                    continue
                fresh = cheap_garrison(s, t, upkeep_all, len(units))
                if not fresh:
                    kept.append((name, kind, chunk))
                    continue
                it = iter(fresh)
                chunk = [next(it) if tokens(l)[:1] == ["unit"] else l for l in chunk]
                plan.note(f, "%s: %s keeps the town with %d unit(s) of %s's own instead of the old garrison"
                          % (r, name, len(fresh), t))
                kept.append((name, kind, chunk))
            joined[r] = kept

    # who stands where: the leader garrisons the capital, the heir the next
    # chosen town, or a free tile by the capital when there is only one town
    spots = {"leader": (capital, cap_xy)}
    if start.get("heir"):
        if len(regions) > 1 and tiles.get(regions[1]):
            spots["heir"] = (regions[1], tiles[regions[1]])
        else:
            spots["heir"] = (None, place(capital, "the heir"))
    held = {spots[r][0] for r in spots if spots[r][0]}          # towns one of our characters holds

    # Garrisons picked by hand: start['garrisons'] = {region: [unit type, ...]}.
    # In a town our leader or heir holds, they follow the bodyguard; elsewhere
    # they replace the old garrison, or a new captain leads them.
    custom = {}
    for r, types in (start.get("garrisons") or {}).items():
        if r not in regions:
            continue
        room = MAX_UNITS - (1 if r in held else 0)
        custom[r] = ["unit\t\t%s\t\t\t\texp 0 armour 0 weapon_lvl 0" % tp for tp in types][:room]
        if len(types) > room:
            plan.warn(f, "%s: %d unit(s) over the %d an army holds were left out" % (r, len(types) - room, MAX_UNITS))
    captains = first_names(pool, "general")
    used = {c.name.split()[0] for fb in s.factions for c in fb.characters if c.name}
    used |= {start[r]["name"].split()[0] for r in ("leader", "heir") if start.get(r) and start[r].get("name")}
    # and the armies / agents placed by hand (written later): a captain never takes one of their names
    used |= {c["name"].split()[0] for c in start.get("characters") or [] if (c.get("name") or "").strip()}
    for r, lines in custom.items():
        agents = [j for j in joined.get(r, []) if not _has_army(j[2])]
        armies = [j for j in joined.get(r, []) if _has_army(j[2])]
        for name, kind, chunk in (armies if r in held else armies[1:]):
            plan.note(f, "%s: %s (%s) and his old garrison leave - your garrison holds the town" % (r, name, kind))
        if r in held:
            joined[r] = agents
            continue
        if armies:
            name, kind, chunk = armies[0]
            head = [l for l in chunk if tokens(l)[:1] != ["unit"]]
            at = next(i for i, l in enumerate(head) if tokens(l)[:1] == ["army"]) + 1
            chunk = head[:at] + [f.make(l) for l in lines] + head[at:]
            plan.note(f, "%s: %s leads your garrison of %d unit(s)" % (r, name, len(lines)))
        else:
            name = next((n for n in captains if n not in used), captains[0] if captains else None)
            if not name:
                raise ValueError("%s: no name in the %s name list for a captain to lead the garrison" % (r, t))
            used.add(name)
            kind = "general"
            chunk = [f.make(character_line(f, name, "general", 30, tiles[r])),
                     f.make("army")] + [f.make(l) for l in lines]
            plan.note(f, "%s: captain %s leads your garrison of %d unit(s)" % (r, name, len(lines)))
        joined[r] = agents + [(name, kind, chunk)]

    own = []
    for role in ("leader", "heir"):
        who = start.get(role)
        if not who:
            continue
        name = who["name"].strip()
        first = name.split(" ")[0]
        if pool and first not in pool.get("characters", []):
            raise ValueError("%s: '%s' is not in the %s name list - the game crashes on names it has no "
                             "string for; pick one from the list" % (role, first, t))
        rest = name[len(first):].strip()
        if rest and pool and rest not in pool.get("surnames", []):
            raise ValueError("%s: surname '%s' is not in the %s surname list" % (role, rest, t))
        region, xy = spots[role]
        if region in custom:
            units = template_army[:1] + custom[region]                # bodyguard + your garrison
            plan.note(f, "%s's army: bodyguard + your garrison of %d unit(s)" % (role, len(custom[region])))
        elif role == "heir":
            units = template_army[:1]                               # the bodyguard
        elif start.get("army"):
            units = list(start["army"])
        elif mode == "template":
            units = list(template_army)
        elif mode == "bodyguard":
            units = template_army[:1]
        else:
            garrison = [u for _, _, c in joined.get(capital, []) if _has_army(c) for u in _units(c)]
            edu = plan.files.get(mod.file("edu"))
            upkeep = unit_upkeep(edu) if edu is not None else {}
            units, size_t, cost_t = balanced_army(s, t, len(regions), upkeep, garrison)
            plan.note(f, "leader's army: bodyguard + %d unit(s) (target like similar factions: %d units, "
                         "upkeep %d%s)" % (len(units) - 1, size_t, cost_t,
                                           ", the town's garrison included" if garrison else ""))
        if region:
            units = merge(units, region, name)
        own.append(f.make(";;\t%s" % role))
        own.append(f.make(character_line(f, name, "named character", who.get("age", 30), xy, role=role)))
        if units:
            own.append(f.make("army"))
            own.extend(f.make(u.rstrip("\r")) for u in units)
        own.append(f.make(""))
        if role == "heir" and not region:
            plan.note(f, "heir %s stands next to %s (a town holds one army)" % (name, capital))
    if not own:
        raise ValueError("the new faction needs a leader")

    header = tokens(tb.header)
    ai = start.get("ai") or " ".join(header[2:]) or "balanced smith"
    block = [f.make(";#######################################################################################>"),
             f.make("faction\t%s, %s" % (new, ai)),
             f.make("denari\t%d" % int(start.get("denari", 5000))),
             f.make("")]
    for b in moved_blocks:
        block.extend(b)
        block.append(f.make(""))
    block.extend(own)
    if start.get("characters"):
        armies_now = {c.xy for x in s.factions for c in x.characters
                      if c.xy and _has_army(s.lines[c.start:c.end]) and c.start not in removed}
        armies_now |= {spots[r][1] for r in spots}
        block.extend(extra_characters(plan, f, campaign, start["characters"], pool, armies_now))
    for r in regions:
        # a town without one of our own characters keeps its first joined army
        # as the garrison; any further armies there fold into that one
        group = joined.get(r, [])
        lead = next((j for j in group if _has_army(j[2])), None)
        for name, kind, chunk in group:
            if lead and _has_army(chunk) and chunk is not lead[2]:
                continue
            if lead and chunk is lead[2]:
                extra = [u for _, _, c in group if c is not chunk and _has_army(c) for u in _units(c)]
                room = max(MAX_UNITS - len(_units(chunk)), 0)
                chunk = chunk + extra[:room]
                if len(extra) > room:
                    plan.warn(f, "%s: %d garrison unit(s) dropped - an army holds %d"
                              % (r, len(extra) - room, MAX_UNITS))
            block.extend(chunk)
            block.append(f.make(""))
            plan.note(f, "%s: %s (%s) joins %s with the town" % (r, name, kind, new))
    block.append(f.make(";#######################################################################################<"))
    block.append(f.make(""))

    # ---- write: edits and removals bottom-up, then the new block before slave ----
    for i, text in edits.items():
        f.set(i, text)
    slave = s.faction("slave")
    at = slave.start if slave else s.factions[-1].end
    # slave's own banner comments stay with it; the previous block's closing
    # banner (a comment ending in "<") stays with that block
    while at > 0 and f.text(at - 1).lstrip().startswith(";") and not f.text(at - 1).rstrip().endswith("<"):
        at -= 1
    shift = 0
    for a, b in sorted(removals, reverse=True):
        del f.raw[a:b]
        if a < at:
            shift += b - a
    at -= shift
    f.insert_raw(at, block)
    plan.note(f, "faction block for %s: %d settlement(s), capital %s, leader %s"
              % (new, len(moved_blocks), capital, start["leader"]["name"]))

    # ---- lists and diplomacy (indices from a fresh scan) ----
    s = Strat(f)
    lst = s.playable if start.get("playable", True) else s.nonplayable
    if lst:
        items = lst["items"]
        after = next((j for j, n in items if n == t), None)
        if after is None:
            before_slave = [j for j, n in items if n == "slave"]
            after = (before_slave[0] - 1) if before_slave else (items[-1][0] if items else lst["start"])
        indent = re.match(r"\s*", f.text(items[0][0])).group(0) if items else "\t"
        f.insert(after + 1, [indent + new])
        plan.note(f, "%s added to the %s list" % (new, "playable" if start.get("playable", True) else "nonplayable"))
    s = Strat(f)
    dip = s.diplomacy_lines()
    add = {"core_attitudes": [], "faction_relationships": []}
    if start.get("diplomacy") == "template":
        for i, kind, a, value, targets in dip:
            if a == t:
                tg = [x for x in targets if x not in (new, t)]
                if tg:
                    add[kind].append("%s\t%s,\t%s\t\t%s" % (kind, new, value, ", ".join(tg)))
            elif t in targets and a != new:
                add[kind].append("%s\t%s,\t%s\t\t%s" % (kind, a, value, new))
    else:
        for kind in add:
            if any(k == kind for _, k, _, _, _ in dip):
                add[kind].append("%s\t%s,\t600\t\tslave" % (kind, new))
                add[kind].append("%s\tslave,\t600\t\t%s" % (kind, new))
    for kind in ("faction_relationships", "core_attitudes"):
        if not add[kind]:
            continue
        s = Strat(f)
        last = max((i for i, k, _, _, _ in s.diplomacy_lines() if k == kind), default=len(f) - 1)
        f.insert(last + 1, add[kind])
        plan.note(f, "%d %s line(s) for %s" % (len(add[kind]), kind, new))


# ---------------------------------------------------------------------------
# Field armies, agents and fleets placed by hand
# ---------------------------------------------------------------------------
class _Kinds(dict):
    """kind in the window -> (descr_strat character type, has an army): army and
    fleet, and any agent type the mod's descr_character.txt has (spy, assassin,
    diplomat; in Medieval II also merchant, priest, princess, inquisitor...)."""

    def __missing__(self, kind):
        if isinstance(kind, str) and kind.replace("_", "").isalpha() and kind not in ("general", "admiral"):
            return (kind, False)
        raise KeyError(kind)

    def __contains__(self, kind):
        try:
            self[kind]
            return True
        except KeyError:
            return False


KINDS = _Kinds({"army": ("general", True), "fleet": ("admiral", True)})


def extra_characters(plan, f, campaign, chars, pool, armies_at, owner=None):
    """Lines for descr_strat for start['characters'] / opts['characters']:
    [{'kind': army|spy|assassin|diplomat|fleet, 'name', 'age', 'units', 'xy'}].
    Names must be in the name pool, tiles must pass tile_problem, an army or
    fleet needs units. armies_at is updated."""
    out = []
    owner = owner or plan.new
    for n, c in enumerate(chars, 1):
        kind = c.get("kind")
        if kind not in KINDS:
            raise ValueError("character %d: unknown kind %r" % (n, kind))
        rtw_kind, army = KINDS[kind]
        name = (c.get("name") or "").strip()
        if not name:
            raise ValueError("%s %d needs a name" % (kind, n))
        first = name.split(" ")[0]
        names = first_names(pool, rtw_kind)
        if pool and first not in names:
            raise ValueError("%s: '%s' is not in the %s name list - the game crashes on names it has no string for"
                             % (kind, first, "women's" if rtw_kind in FEMALE_KINDS else "men's"))
        rest = name[len(first):].strip()
        if rest and pool and rest not in pool.get("surnames", []):
            raise ValueError("%s: surname '%s' is not in the surname list" % (kind, rest))
        xy = c.get("xy")
        if not xy:
            raise ValueError("%s %s is not placed on the map yet" % (kind, name))
        xy = tuple(xy)
        why = plan.mod.tile_problem(campaign, xy, rtw_kind, army, armies_at)
        if why:
            raise ValueError("%s %s at %d, %d: %s" % (kind, name, xy[0], xy[1], why))
        units = list(c.get("units") or [])
        if army and not units:
            raise ValueError("%s %s has no units" % (kind, name))
        if army:
            armies_at.add(xy)
        out.append(";;\t%s placed with the faction tool" % kind)
        out.append(character_line(f, name, rtw_kind, c.get("age") or 30, xy))
        if army:
            out.append("army")
            out += ["unit\t\t%s\t\t\t\texp 0 armour 0 weapon_lvl 0" % u for u in units[:MAX_UNITS]]
        out.append("")
        plan.note(f, "%s %s at %d, %d%s" % (kind, name, xy[0], xy[1],
                                              " with %d unit(s)" % min(len(units), MAX_UNITS) if army else ""))
    return [f.make(l) for l in out]
