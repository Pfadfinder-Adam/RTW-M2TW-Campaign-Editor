"""A faction's culture (the user, 2026-10-17: 'the faction screen lacks a culture pick - which culture the faction
belongs to, and everything follows from it'). New / Edit faction pick it; ONE line of descr_sm_factions.txt (`culture
<name>`, and REX's descr_sm_factions.json "culture") is written - the game takes the rest from it by itself: the
town / fort / port models (descr_sm_settlements / descr_cultures), the portraits and agents' pictures
(ui/<culture>/...), the buildings whose 'requires factions { <culture>, }' lets it in, the units owned by the culture's
name, the event pictures, Rome's voices. What changes with it is said before Apply (effects): the units it gains and
loses, the buildings standing in its towns the new culture may not build (they stay, as the game keeps them), and in
Rome the roman culture's own ways (the Senate) won or lost."""

import re

from .textio import strip_comment, tokens


def names(mod):
    """The cultures a faction may take: descr_cultures.txt's (both games have one) in its order, then any other the
    factions use already."""
    from .culturenames import cultures
    out = list(cultures(mod))
    for _, c in mod.factions():
        if c and c not in out:
            out.append(c)
    return out


def _culture_line(f, faction):
    """(line number, culture) of the faction's `culture` line in descr_sm_factions.txt, (None, None) without one."""
    cur = None
    for i in range(len(f)):
        t = tokens(strip_comment(f.text(i)))
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1].rstrip(",")
        elif cur == faction and t[:1] == ["culture"] and len(t) > 1:
            return i, t[1]
    return None, None


def set_faction_culture(plan, faction, culture):
    """Its `culture` line changed (as the plan leaves descr_sm_factions.txt: a new faction's block is there already),
    REX's .json too when the mod has one; what changes with it said as warnings (effects). The rest of the line -
    spacing, comment - kept."""
    mod = plan.mod
    known = names(mod)
    if known and culture not in known:
        raise ValueError("'%s' is no culture of this mod (%s)" % (culture, ", ".join(known)))
    f = plan.edit(mod.file("sm_factions"))
    i, now = _culture_line(f, faction)
    if i is None:
        raise ValueError("%s has no culture line in descr_sm_factions.txt" % faction)
    if now == culture:
        return
    for w in effects(mod, faction, now, culture, sm=f):
        plan.warn(f, w)
    f.set(i, re.sub(r"(\bculture\s+)%s\b" % re.escape(now), lambda m: m.group(1) + culture, f.text(i), count=1))
    plan.note(f, "%s: culture %s (was %s) - its towns' models, portraits, buildings and units follow it in the "
                 "game" % (faction, culture, now))
    path = mod.file("sm_factions_json")
    if path:
        j = plan.edit(path)
        inside = depth = 0
        for k in range(len(j)):
            line = j.text(k)
            if not inside and re.match(r'\s*"%s"\s*:' % re.escape(faction), line):
                inside, depth = 1, 0
            if inside:
                if depth == 1 and re.match(r'\s*"culture"\s*:', line):
                    j.set(k, re.sub(r'("culture"\s*:\s*")[^"]*(")', lambda m: m.group(1) + culture + m.group(2),
                                    line, count=1))
                depth += line.count("{") - line.count("}")
                if "{" in line or depth:
                    inside = 2
                if inside == 2 and depth <= 0:
                    inside = 0


def effects(mod, faction, old, new, sm=None, campaigns=None):
    """What changes with the faction's culture old -> new, in plain words (each one line): the units it gains / loses
    (export_descr_unit ownership naming the culture), the buildings in its towns the new culture may not build (every
    campaign - they stay), Rome's roman culture (the Senate) won or lost."""
    out = []
    from .units import read_units
    edu = mod.file("edu")
    if edu:
        gained, lost = [], []
        for u in read_units(mod.load(edu)):
            own = set(u.ownership)
            if faction in own or "all" in own:
                continue
            if old in own and new not in own:
                lost.append(u.type)
            elif new in own and old not in own:
                gained.append(u.type)
        for words, got in (("may no longer recruit", lost), ("may now recruit", gained)):
            if got:
                out.append("%s %s %d unit(s) owned by the culture: %s%s" % (
                    faction, words, len(got), ", ".join(got[:6]), " ..." if len(got) > 6 else ""))
    blocked = _buildings_closed(mod, faction, new, campaigns)
    if blocked:
        out.append("%d building(s) in %s's towns are not open to the culture %s - they stay, the game keeps them: %s%s"
                   % (len(blocked), faction, new, ", ".join(blocked[:5]), " ..." if len(blocked) > 5 else ""))
    if "roman" in (old, new) and old != new and mod.find("descr_senate.txt"):
        out.append("%s %s the roman culture's own ways (the Senate's missions and offices go by it)" % (
            faction, "leaves" if old == "roman" else "takes"))
    return out


def _buildings_closed(mod, faction, culture, campaigns=None):
    """['<town>: <level>'] standing in the faction's towns that the culture may not build (none of its levels' lists
    name the faction, the culture or 'all')."""
    from .buildings import available, read_buildings
    from .strat import Strat
    edb = mod.file("edb")
    if not edb:
        return []
    known = {b.name: b for b in read_buildings(mod.load(edb))}
    out = []
    for campaign in campaigns or mod.campaigns():
        try:
            s = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
        except (OSError, ValueError):
            continue
        fb = s.faction(faction)
        if not fb:
            continue
        for st in fb.settlements:
            for line in s.lines[st.start:st.end]:
                t = tokens(strip_comment(line))
                if t[:1] != ["type"] or len(t) < 3:
                    continue
                b = known.get(t[1])
                lv = b.level(t[2]) if b else None
                item = "%s: %s" % (st.region, t[2])
                if lv and not available(lv, faction, culture) and item not in out:
                    out.append(item)
    return out


__all__ = ["names", "set_faction_culture", "effects"]
