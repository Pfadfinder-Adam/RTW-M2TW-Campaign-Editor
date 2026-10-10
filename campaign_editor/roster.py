"""What a faction may have: its units and its buildings, and giving or taking
them with everything tied to them kept in step.

A unit is really the faction's only when three places agree:
  * export_descr_unit.txt   'ownership' names the faction (or its culture, or all);
  * export_descr_buildings  a 'recruit "<unit>" ... requires factions { ... }' line (Medieval II:
                            'recruit_pool "<unit>" ...') in a level the faction can build lets it
                            (or its culture); REX's 'retrain' / 'retrain_pool' lines only retrain;
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
# recruit lines: Rome 'recruit', Medieval II 'recruit_pool', REX's retrain-only 'retrain' / 'retrain_pool'
RECRUIT_KEYS = ("recruit", "recruit_pool", "retrain", "retrain_pool")
RECRUITING = ("recruit", "recruit_pool")
RE_RECRUIT = re.compile(r'^\s*(recruit_pool|retrain_pool|recruit|retrain)\s+"([^"]+)"')


def recruit_of(text, keys=RECRUIT_KEYS):
    """(key, unit) of a recruit line whose key is one of keys, else None."""
    m = RE_RECRUIT.match(strip_comment(text))
    return (m.group(1), m.group(2)) if m and m.group(1) in keys else None


def recruit_dialect(f):
    """'pool' when the buildings file recruits with recruit_pool (Medieval II), else 'plain'."""
    for i in range(len(f.raw)):
        r = recruit_of(f.text(i))
        if r:
            return "pool" if r[0].endswith("_pool") else "plain"
    return "plain"


# ---------------------------------------------------------------------------
# factions { ... } lists
# ---------------------------------------------------------------------------
def factions_groups(text):
    """Every 'factions { ... }' list of a line, in order. REX lets one line carry several,
    each with conditions of its own: 'requires ( ( factions { greek, } and X ) or
    ( factions { middle_eastern, } and Y ) )'."""
    return [[w for w in m.group(1).replace(",", " ").split() if w]
            for m in RE_FACTIONS.finditer(strip_comment(text))]


def factions_in(text):
    """The names of a line's factions lists (all of them, once each), or None when it has none."""
    groups = factions_groups(text)
    if not groups:
        return None
    out = []
    for g in groups:
        out += [n for n in g if n not in out]
    return out


def _body(names):
    return "factions { %s}" % "".join("%s, " % n for n in names)


def with_factions(text, names):
    """The line with its (first) factions list replaced by names (the layout 'a, b, ' kept)."""
    return RE_FACTIONS.sub(lambda m: _body(names), text, count=1)


def add_faction(text, faction):
    """The faction written into the line's first factions list (a line of several REX
    groups: the first group's conditions then apply to it)."""
    names = (factions_groups(text) or [[]])[0]
    return with_factions(text, names + [faction]) if faction not in names else text


def drop_faction(text, faction):
    """The faction out of every factions list of the line; None when that would leave a
    list empty on a line of several groups (such a line is for a person to rewrite)."""
    groups = factions_groups(text)
    if len(groups) > 1 and any(g == [faction] for g in groups):
        return None
    it = iter(groups)
    return RE_FACTIONS.sub(lambda m: _body([n for n in next(it) if n != faction]), text)


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


def recruit_lines(f, keys=RECRUITING):
    """[(line, unit, chain, level)] of every recruit line in export_descr_buildings.txt
    (by default the lines that recruit: recruit / recruit_pool, not retrain-only ones)."""
    from .editors import building_blocks, chain_tree
    out = []
    for chain, a, b in building_blocks(f):
        for lv in chain_tree(f, a, b)["levels"]:
            for i in range(lv["open"], lv["close"]):
                r = recruit_of(f.text(i), keys)
                if r:
                    out.append((i, r[1], chain, lv["name"]))
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
        if mod.find("ui/%s/%s/%s" % (sub, faction, pattern % dictionary_name)):    # its own card, mod's or game's
            continue
        src = next((p for p in (mod.find("ui/%s/%s/%s" % (sub, o, pattern % dictionary_name)) for o in owners)
                    if p), None) or card_path(mod, faction, dictionary_name, info)
        if not src:
            plan.warn(None, "%s: no %s picture anywhere to copy for %s - add one in Units"
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
        # a level may recruit the unit by several lines for different factions (vanilla: Arab Cavalry for moors
        # and for egypt): the faction joins one of them, and none when one lets it in already - in each it is
        # listed twice in the building's description
        let_in = {(c, l) for i, _, c, l in lines
                  if factions_in(e.text(i)) is None or covers(factions_in(e.text(i)), faction, culture)}
        for i, _, chain, level in lines:
            if (chain, level) not in let_in:
                let_in.add((chain, level))
                if len(factions_groups(e.text(i))) > 1:
                    plan.warn(e, "%s/%s: the recruit line has several faction groups - %s joins the first one "
                                 "and its conditions" % (chain, level, faction))
                e.set(i, add_faction(e.text(i), faction))
                if "%s/%s" % (chain, level) not in added:
                    added.append("%s/%s" % (chain, level))
            if covers(factions_in(e.text(heads[(chain, level)])), faction, culture):
                reachable.append(level)
        if added:
            plan.note(e, "%s recruited by %s in %s" % (unit, faction, ", ".join(added)))
        if not lines:
            plan.warn(e, "%s: no building recruits it - add a recruit line in Buildings" % unit)
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
        for i, _, chain, level in reversed([r for r in recruit_lines(e, RECRUIT_KEYS) if r[1] == unit]):
            names = factions_in(e.text(i))
            if names and faction in names:
                rest = [n for n in names if n != faction]
                new = drop_faction(e.text(i), faction) if rest else None
                if rest and new is None:
                    plan.warn(e, "%s/%s: %s is a faction group of its own on a recruit line with several groups - "
                                 "rewrite that line in Buildings" % (chain, level, faction))
                    continue
                if rest:
                    e.set(i, new)
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
        if len(factions_groups(text)) > 1:
            plan.warn(e, "%s/%s: the level has several faction groups - %s joins the first one and its conditions"
                      % (chain, level, faction))
        e.set(i, add_faction(text, faction))
        plan.note(e, "%s/%s: %s may build it" % (chain, level, faction))
        # its picture comes from the faction's culture folder (ui/<culture>/buildings)
        # none there: the picture of a culture that has one is copied in (the building as it is)
        from .buildings import BuildingPictures
        if culture and mod.dirs("ui"):                          # the mod's ui or the game's under it
            bp = BuildingPictures(mod)
            if not bp.find(culture, level):
                got = None
                for built in (False, True):
                    tail = "_constructed.tga" if built else ".tga"
                    src = next((files.get(("#%s_%s%s" % (c, level, tail)).lower())
                                for c, files in sorted(bp.index.items())
                                if files.get(("#%s_%s%s" % (c, level, tail)).lower())), None)
                    if src:
                        dst = os.path.join(mod.data, "ui", culture, "buildings",
                                           "#%s_%s%s" % (culture, level, tail))
                        plan.copy(src, dst)
                        got = got or src
                if got:
                    plan.note(e, "%s/%s: the %s culture had no picture of it - the one of %s copied in (import "
                                 "another in Buildings)" % (chain, level, culture,
                                                                      os.path.basename(got).split("_")[0][1:]))
                else:
                    plan.warn(e, "%s/%s: no picture for the %s culture (ui/%s/buildings/#%s_%s.tga) - import one "
                                 "in Buildings" % (chain, level, culture, culture, culture, level))
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
    elif len(factions_groups(text)) > 1:                # REX groups: out of every group, by name only
        new_text = drop_faction(text, faction) if now == "own" else None
        if new_text is None:
            plan.warn(e, "%s/%s: the level's faction groups let %s in %s - rewrite that line in the Building "
                         "editor" % (chain, level, faction, "by its culture or 'all'" if now != "own"
                                     else "through a group of its own"))
            return False
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
