"""The new faction's start in descr_strat.txt: lists, block, settlements,
characters and diplomacy."""

import re

from .strat import Strat, RE_XY
from .textio import tokens


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


def unit_name(line):
    """'unit   east horse archer   exp 0 armour 0 weapon_lvl 0' -> 'east horse archer'."""
    body = line.strip()[len("unit"):].strip()
    m = re.split(r"\s+exp\s+\d+", body)
    return m[0].strip()


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
    tiles = mod.city_tiles(campaign)
    regions = list(start.get("regions") or [])
    if not regions:
        raise ValueError("pick at least one starting settlement")
    capital = start.get("capital") or regions[0]
    if capital not in regions:
        regions.insert(0, capital)
    else:
        regions.remove(capital)
        regions.insert(0, capital)

    moved_blocks = []          # raw lines of settlement blocks
    moved_chars = []           # raw lines of character chunks
    removals = []              # (start, end) ranges to delete
    edits = {}                 # line index -> new text (relocated characters)
    losers = {}
    for r in regions:
        st = s.settlement_of(r)
        if st is None:
            raise ValueError("%s has no settlement in descr_strat.txt" % r)
        if st.owner == new:
            continue
        owner = s.faction(st.owner)
        moved_blocks.append(f.raw[st.start:st.end])
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
                moved_chars.append(chunk)
                removals.append((c.start, c.end))
                plan.note(f, "%s: %s (%s) joins %s with the town" % (r, c.name, c.kind, new))
            else:
                # the owner keeps this character: move him to one of its remaining towns
                keep = [x.region for x in owner.settlements if x.region not in regions and tiles.get(x.region)]
                if not keep:
                    raise ValueError("%s: %s of %s stands in the town and %s has no other settlement to "
                                     "move him to - pick another town or edit descr_strat.txt by hand"
                                     % (r, c.name, c.owner, c.owner))
                edits[c.start] = _set_xy(f.text(c.start), tiles[keep[0]])
                plan.note(f, "%s: %s of %s moved to %s" % (r, c.name, c.owner, keep[0]))
    for owner, rs in losers.items():
        fb = s.faction(owner)
        left = [x for x in fb.settlements if x.region not in regions]
        plan.note(f, "%s gives up %s" % (owner, ", ".join(rs)))
        if owner != "slave" and not left:
            plan.warn(f, "%s is left with no settlement - it starts as a horde or dies on turn 1" % owner)

    # ---- the new faction's own characters ----
    cap_xy = tiles.get(capital)
    if not cap_xy:
        raise ValueError("no city pixel for the capital %s in map_regions.tga" % capital)
    army = start.get("army") or default_army(s, t)
    if not army:
        plan.warn(f, "the template leader has no army to copy - the leader starts with no units")
    pool = plan.mod.name_pool(new) or plan.mod.name_pool(t)
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
        own.append(f.make(";;\t%s" % role))
        own.append(f.make("character\t%s, named character, %s, age %d, , x %d, y %d"
                          % (name, role, int(who.get("age", 30)), cap_xy[0], cap_xy[1])))
        if role == "leader" and army:
            own.append(f.make("army"))
            own.extend(f.make(u.rstrip("\r")) for u in army)
        elif role == "heir" and army:
            own.append(f.make("army"))
            own.append(f.make(army[0].rstrip("\r")))       # the bodyguard
        own.append(f.make(""))
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
    for ch in moved_chars:
        block.extend(ch)
        block.append(f.make(""))
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
