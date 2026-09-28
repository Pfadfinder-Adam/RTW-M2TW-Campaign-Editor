"""What a faction may have: its units and its buildings, and giving or taking
them with everything tied to them kept in step.

A unit is really the faction's only when three places agree:
  * export_descr_unit.txt   'ownership' names the faction (or its culture, or all);
  * export_descr_buildings  a 'recruit "<unit>" ... requires factions { ... }' line
                            in a level the faction can build lets it (or its culture);
  * ui/units/<faction>/#<dictionary>.tga and ui/unit_info/<faction>/<dictionary>_info.tga
                            its cards (the game shows an empty card without them).
A building level is the faction's when its line 'requires factions { ... }' in
export_descr_buildings.txt names it (or its culture), or has no factions list.

Giving writes the faction into those lists and copies the cards; taking removes it
(a culture or 'all' is written out as the other factions it stood for) and warns
about armies and towns in descr_strat that already hold the unit or building."""

import os
import re

from .moddata import _ci
from .textio import strip_comment, tokens

RE_FACTIONS = re.compile(r"(?<![A-Za-z0-9_])factions\s*\{([^}]*)\}")
RE_RECRUIT = re.compile(r'^\s*recruit\s+"([^"]+)"')


# ---------------------------------------------------------------------------
# factions { ... } lists
# ---------------------------------------------------------------------------
def factions_in(text):
    """The names of a line's 'factions { ... }' list, or None when it has none."""
    m = RE_FACTIONS.search(strip_comment(text))
    if not m:
        return None
    return [w for w in m.group(1).replace(",", " ").split() if w]


def with_factions(text, names):
    """The line with its factions list replaced by names (the layout 'a, b, ' kept)."""
    body = "{ %s}" % "".join("%s, " % n for n in names)
    return RE_FACTIONS.sub(lambda m: "factions " + body, text, count=1)


def covers(names, faction, culture):
    """How a list lets the faction in: 'own', 'culture', 'all' or None."""
    if names is None:
        return "all"
    if faction in names:
        return "own"
    if culture and culture in names:
        return "culture"
    if "all" in names:
        return "all"
    return None


def _spelled_out(names, faction, cultures):
    """names without the faction: a culture or 'all' it came through becomes the
    other factions it stands for."""
    out = []
    for n in names:
        if n == faction:
            continue
        if n == "all":
            out += [f for f, _ in cultures if f != faction]
        elif any(c == n for _, c in cultures):
            out += [f for f, c in cultures if c == n and f != faction]
        else:
            out.append(n)
    seen = set()
    return [n for n in out if not (n in seen or seen.add(n))]


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------
def _edu_blocks(f):
    from .editors import unit_blocks
    return unit_blocks(f)


def unit_line(f, block, key):
    """The line number of key in a unit block, or None."""
    _, a, b = block
    for i in range(a, b):
        if tokens(f.text(i))[:1] == [key]:
            return i
    return None


def ownership(f, block):
    i = unit_line(f, block, "ownership")
    if i is None:
        return []
    code = strip_comment(f.text(i)).strip()
    return [w for w in code[len("ownership"):].replace(",", " ").split() if w]


def dictionary(f, block):
    i = unit_line(f, block, "dictionary")
    t = tokens(f.text(i)) if i is not None else []
    return t[1] if len(t) > 1 else ""


def level_heads(f):
    """{(chain, level): line of '<level> requires ...'} in export_descr_buildings.txt."""
    from .editors import building_blocks, chain_tree
    out = {}
    for chain, a, b in building_blocks(f):
        for lv in chain_tree(f, a, b)["levels"]:
            out[(chain, lv["name"])] = lv["head"]
    return out


def recruit_lines(f):
    """[(line, unit, chain, level)] of every recruit line in export_descr_buildings.txt."""
    from .editors import building_blocks, chain_tree
    out = []
    for chain, a, b in building_blocks(f):
        for lv in chain_tree(f, a, b)["levels"]:
            for i in range(lv["open"], lv["close"]):
                m = RE_RECRUIT.match(f.text(i))
                if m:
                    out.append((i, m.group(1), chain, lv["name"]))
    return out


def roster(mod, faction):
    """What the faction has now:
    units: [{type, dictionary, category, has ('own'|'culture'|'all'|None), recruit: [(chain, level)]
             where it recruits it now, recruit_any: every (chain, level) that recruits it}]
    buildings: [{chain, level, has, line}] in file order."""
    culture = mod.culture(faction)
    edu_p, edb_p = mod.file("edu"), mod.file("edb")
    units, buildings = [], []
    edb = mod.load(edb_p) if edb_p else None
    heads = level_heads(edb) if edb else {}
    lv_ok = {k: covers(factions_in(edb.text(i)), faction, culture) for k, i in heads.items()}
    where, anywhere = {}, {}
    for i, unit, chain, level in (recruit_lines(edb) if edb else []):
        if (chain, level) not in anywhere.setdefault(unit, []):
            anywhere[unit].append((chain, level))
        if lv_ok.get((chain, level)) and covers(factions_in(edb.text(i)), faction, culture):
            where.setdefault(unit, []).append((chain, level))
    if edu_p:
        f = mod.load(edu_p)
        for blk in _edu_blocks(f):
            cat_i = unit_line(f, blk, "category")
            cat = tokens(f.text(cat_i))[1] if cat_i is not None and len(tokens(f.text(cat_i))) > 1 else ""
            if cat == "non_combatant":
                continue
            units.append({"type": blk[0], "dictionary": dictionary(f, blk), "category": cat,
                          "has": covers(ownership(f, blk), faction, culture), "recruit": where.get(blk[0], []),
                          "recruit_any": anywhere.get(blk[0], [])})
    for (chain, level), i in heads.items():
        buildings.append({"chain": chain, "level": level, "has": lv_ok[(chain, level)], "line": i})
    return {"units": units, "buildings": buildings}


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------
def _find_unit(f, unit):
    blk = next((b for b in _edu_blocks(f) if b[0] == unit), None)
    if blk is None:
        raise ValueError("no unit '%s' in export_descr_unit.txt" % unit)
    return blk


def own_unit(plan, faction, unit, give=True):
    """EDU ownership: the faction written in (give) or out (take; a culture or 'all'
    it came through is written out as the other factions). True when changed."""
    mod = plan.mod
    f = plan.edit(mod.file("edu"))
    blk = _find_unit(f, unit)
    cultures = mod.factions()
    culture = dict(cultures).get(faction)
    names = ownership(f, blk)
    now = covers(names, faction, culture)
    i = unit_line(f, blk, "ownership")
    if give:
        if now:
            return False
        new = names + [faction]
    else:
        if not now:
            return False
        new = _spelled_out(names, faction, cultures)
        if not new:
            new = ["slave"]                          # an ownership line may not be empty
        if now in ("culture", "all"):
            plan.warn(f, "%s: ownership '%s' written out as %s, so that only %s loses it"
                      % (unit, " ".join(names), ", ".join(new), faction))
    from .editors import set_value
    if i is None:
        at = unit_line(f, blk, "dictionary")
        f.insert((at if at is not None else blk[1]) + 1, ["ownership       " + ", ".join(new)])
    else:
        f.set(i, set_value(f.text(i), ", ".join(new)))
    plan.note(f, "%s: ownership %s -> %s" % (unit, ", ".join(names) or "(none)", ", ".join(new)))
    return True


def copy_cards(plan, faction, dictionary_name, owners=()):
    """The unit's card and description picture into the faction's own folders,
    from an owner's folder (owners, in order) or any other when it has none."""
    from .units import card_path
    mod = plan.mod
    if not owners and mod.file("edu"):              # the unit's owners' folders have its own cards
        f = plan.edit(mod.file("edu"))
        blk = next((b for b in _edu_blocks(f) if dictionary(f, b) == dictionary_name), None)
        if blk:
            owners = [o for o, c in mod.factions() if o != faction and covers(ownership(f, blk), o, c) in ("own", "culture")]
    n = 0
    for info, sub, pattern in ((False, "units", "#%s.tga"), (True, "unit_info", "%s_info.tga")):
        folder = os.path.join(mod.data, "ui", sub)
        own = _ci(folder, faction)
        if own and _ci(own, pattern % dictionary_name):
            continue
        src = next((p for p in (_ci(_ci(folder, o) or "", pattern % dictionary_name) for o in owners) if p),
                   None) or card_path(mod, faction, dictionary_name, info)
        if not src:
            plan.warn(None, "%s: no %s picture anywhere to copy for %s - add one in the Unit editor"
                      % (dictionary_name, "card" if not info else "description", faction))
            continue
        dst = os.path.join(own or os.path.join(folder, faction), pattern % dictionary_name)
        if any(d == dst for _, d in plan.copies):
            continue
        plan.copy(src, dst)
        n += 1
    return n


def give_unit(plan, faction, unit):
    """The unit becomes the faction's: ownership, the recruit lines that hold it
    (the faction added where it is not let in yet), its cards."""
    mod = plan.mod
    own_unit(plan, faction, unit, True)
    culture = mod.culture(faction)
    edb_p = mod.file("edb")
    if edb_p:
        e = plan.edit(edb_p)
        heads = level_heads(e)
        lines = [r for r in recruit_lines(e) if r[1] == unit]
        added, reachable = [], []
        for i, _, chain, level in lines:
            names = factions_in(e.text(i))
            if names is not None and not covers(names, faction, culture):
                e.set(i, with_factions(e.text(i), names + [faction]))
                if "%s/%s" % (chain, level) not in added:
                    added.append("%s/%s" % (chain, level))
            if covers(factions_in(e.text(heads[(chain, level)])), faction, culture):
                reachable.append(level)
        if added:
            plan.note(e, "%s recruited by %s in %s" % (unit, faction, ", ".join(added)))
        if not lines:
            plan.warn(e, "%s: no building recruits it - add a recruit line in the Building editor" % unit)
        elif not reachable:
            plan.warn(e, "%s: recruited only in %s, which %s cannot build - give it one of those levels"
                      % (unit, ", ".join(sorted({"%s/%s" % (c, l) for _, _, c, l in lines})), faction))
    f = plan.edit(mod.file("edu"))
    blk = _find_unit(f, unit)
    dic = dictionary(f, blk)
    if dic:
        cultures = mod.factions()
        owners = [o for o, c in cultures if o != faction and covers(ownership(f, blk), o, c) in ("own", "culture")]
        copy_cards(plan, faction, dic, owners)


def take_unit(plan, faction, unit, campaign=None):
    """The unit is no longer the faction's: ownership, the faction's name out of
    the recruit lines (a line left with no faction goes), a warning for its armies
    that hold the unit (they keep it; the game lets them)."""
    mod = plan.mod
    own_unit(plan, faction, unit, False)
    edb_p = mod.file("edb")
    if edb_p:
        e = plan.edit(edb_p)
        gone = []
        for i, _, chain, level in reversed([r for r in recruit_lines(e) if r[1] == unit]):
            names = factions_in(e.text(i))
            if names and faction in names:
                rest = [n for n in names if n != faction]
                if rest:
                    e.set(i, with_factions(e.text(i), rest))
                else:
                    e.delete(i, i + 1)
                gone.append("%s/%s" % (chain, level))
        if gone:
            plan.note(e, "%s no longer recruited by %s in %s" % (unit, faction, ", ".join(reversed(gone))))
    for camp in ([campaign] if campaign else mod.campaigns()):
        n = _units_in_armies(mod, camp, faction, unit)
        if n:
            plan.warn(None, "%s: %d of %s's armies in %s start with %s - they keep it"
                      % (unit, n, faction, camp, unit))


def _units_in_armies(mod, campaign, faction, unit):
    from .start import unit_name
    from .strat import Strat
    p = mod.campaign_file(campaign, "descr_strat.txt")
    if not p:
        return 0
    s = Strat(mod.load(p))
    fb = s.faction(faction)
    if not fb:
        return 0
    n = 0
    for c in fb.characters:
        if any(tokens(l)[:1] == ["unit"] and unit_name(l) == unit for l in s.lines[c.start:c.end]):
            n += 1
    return n


def set_level(plan, faction, chain, level, give=True, campaign=None):
    """A building level let in (give) or shut (take) for the faction on its
    'requires factions' line. Taking warns about its towns that hold it."""
    mod = plan.mod
    e = plan.edit(mod.file("edb"))
    heads = level_heads(e)
    if (chain, level) not in heads:
        raise ValueError("no building level %s in %s" % (level, chain))
    i = heads[(chain, level)]
    cultures = mod.factions()
    culture = dict(cultures).get(faction)
    text = e.text(i)
    names = factions_in(text)
    now = covers(names, faction, culture)
    if give:
        if now:
            return False
        e.set(i, with_factions(text, names + [faction]))
        plan.note(e, "%s/%s: %s may build it" % (chain, level, faction))
        # its picture comes from the faction's culture folder (ui/<culture>/buildings)
        from .buildings import BuildingPictures
        if culture and os.path.isdir(os.path.join(mod.data, "ui")) and \
                not BuildingPictures(mod).find(culture, level):
            plan.warn(e, "%s/%s: no picture for the %s culture (ui/%s/buildings/#%s_%s.tga) - import one in "
                         "the Building editor" % (chain, level, culture, culture, culture, level))
        return True
    if not now:
        return False
    if names is None:                                   # open to all: a list of the others
        new = [f for f, _ in cultures if f != faction]
        code = strip_comment(text).rstrip()
        rest = text[len(code):]
        if " requires " in " %s " % code:
            head, _, cond = code.partition("requires")
            new_text = "%srequires factions { %s} and %s%s" % (head, "".join("%s, " % n for n in new), cond.strip(), rest)
        else:
            new_text = "%s requires factions { %s}%s" % (code, "".join("%s, " % n for n in new), rest)
        e.set(i, new_text)
    else:
        new = _spelled_out(names, faction, cultures)
        e.set(i, with_factions(text, new))
    if now in ("culture", "all"):
        plan.warn(e, "%s/%s: '%s' written out as the other factions, so that only %s loses it"
                  % (chain, level, " ".join(names or ["(everyone)"]), faction))
    plan.note(e, "%s/%s: %s may no longer build it" % (chain, level, faction))
    from .buildings import settlement_info
    from .strat import Strat
    for camp in ([campaign] if campaign else mod.campaigns()):
        p = mod.campaign_file(camp, "descr_strat.txt")
        s = Strat(mod.load(p)) if p else None
        fb = s.faction(faction) if s else None
        towns = [st.region for st in (fb.settlements if fb else [])
                 if (chain, level) in settlement_info(s.lines[st.start:st.end])[1]]
        if towns:
            plan.warn(None, "%s/%s stands in %s's %s in %s - it stays there"
                      % (chain, level, faction, ", ".join(towns), camp))
    return True


def apply(plan, faction, changes, campaign=None):
    """changes = {'unit:<type>': bool, 'building:<chain>:<level>': bool} (True = give)."""
    for key, give in sorted(changes.items()):
        kind, _, rest = key.partition(":")
        if kind == "unit":
            (give_unit if give else take_unit)(plan, faction, rest, *([] if give else [campaign]))
        elif kind == "building":
            chain, _, level = rest.partition(":")
            set_level(plan, faction, chain, level, give, campaign)
