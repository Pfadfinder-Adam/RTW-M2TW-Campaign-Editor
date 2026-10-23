"""A faction's buildings as the game shows them: every chain it may build, its levels in order (cost, turns, the
town they need) and, under each level, the units the faction recruits there - from export_descr_buildings.txt and
export_descr_unit.txt, both games (Rome's 'recruit' lines, Medieval II's 'recruit_pool' lines). What the Buildings
work's 'By faction' tab shows (gui_factionbuildings); nothing here writes."""

import copy
import re

from . import editors as E
from .roster import covers, factions_in, recruit_key, recruit_of
from .textio import strip_comment

# the chains' groups in the order the tab shows them (editors.CHAIN_GROUPS names them)
GROUP_ORDER = ("walls and core", "military", "economy", "temple", "culture and law", "guild", "other")
GROUP_TITLES = {"walls and core": "Core and walls", "military": "Military", "economy": "Economy and roads",
                "temple": "Temples", "culture and law": "Culture and law", "guild": "Guilds", "other": "Other"}

_RE_LIST = re.compile(r"(?<![A-Za-z0-9_])factions\s*\{[^}]*\}")


def conditions(text):
    """What a 'requires ...' asks for besides the factions lists, in the file's words ('' when nothing):
    'building_present_min_level barracks muster', 'hidden_resource rome'."""
    code = strip_comment(text)
    i = code.find("requires")
    if i < 0:
        return ""
    rest = _RE_LIST.sub("", code[i + len("requires"):])
    rest = re.sub(r"\s+", " ", rest).strip()
    rest = re.sub(r"\band(\s+and\b)+", "and", rest)                 # two lists in a row left 'and and'
    rest = re.sub(r"^and\b\s*|\s*\band$", "", rest).strip()
    return "" if rest in ("", "()", "( )") else rest


def recruit_numbers(text):
    """What the numbers of a recruit line say: Rome 'recruit "x" 1' = {'experience': 1}; Medieval II 'recruit_pool
    "x" 1 0.5 4 0' = {'start': 1, 'per_turn': 0.5, 'most': 4, 'experience': 0} (the pool the town starts with, what
    it gains a turn, the most it holds)."""
    code = strip_comment(text)
    m = re.match(r'\s*(\w+)\s+"[^"]+"\s*([^r]*)', code)
    if not m:
        return {}
    nums = []
    for p in m.group(2).split():
        try:
            nums.append(float(p))
        except ValueError:
            break
    if m.group(1).endswith("_pool") and len(nums) >= 4:
        return {"start": nums[0], "per_turn": nums[1], "most": nums[2], "experience": int(nums[3])}
    return {"experience": int(nums[0])} if nums else {}


def _level_value(f, lv, key):
    for i in range(lv["open"], lv["close"] + 1):
        t = strip_comment(f.text(i)).split()
        if t[:1] == [key] and len(t) > 1:
            return t[1]
    return ""


def chains(f, faction, culture, unit_types=None):
    """[{chain, group, builds, castle, levels: [...]}] of a loaded export_descr_buildings.txt, in file order, for a
    faction. builds: whether the faction may build at least one level; castle: every level is a castle's (Medieval
    II names a castle's chain as the city's one - 'Port' twice). A level: {name, head (its line), has (how its
    factions list lets the faction in: 'own' / 'culture' / 'all' / None), kind ('city' / 'castle' / None), cost,
    turns, town (settlement_min), needs (what else it asks for), units: the recruit lines that let the faction in
    [{unit, line, key, has, needs, numbers, known}], others: how many recruit lines there are for other factions}.
    unit_types: the types export_descr_unit.txt has, in lower case (the games read them so; a recruit line naming
    another one: known False)."""
    out = []
    for name, a, b in E.building_blocks(f):
        tree = E.chain_tree(f, a, b)
        levels = []
        for lv in tree["levels"]:
            head = f.text(lv["head"])
            words = strip_comment(head).split()
            units, others = [], 0
            for i in range(lv["open"], lv["close"] + 1):
                r = recruit_of(f.text(i))
                if not r or r[0].startswith("retrain"):
                    continue
                has = covers(factions_in(f.text(i)), faction, culture)
                if not has:
                    others += 1
                    continue
                units.append({"unit": r[1], "line": i, "key": r[0], "has": has, "needs": conditions(f.text(i)),
                              "numbers": recruit_numbers(f.text(i)),
                              "known": unit_types is None or r[1].lower() in unit_types})
            cost, turns = _level_value(f, lv, "cost"), _level_value(f, lv, "construction")
            levels.append({"name": lv["name"], "head": lv["head"],
                           "has": covers(factions_in(head), faction, culture),
                           "kind": words[1] if len(words) > 1 and words[1] in ("city", "castle") else None,
                           "cost": int(cost) if cost.isdigit() else 0, "turns": int(turns) if turns.isdigit() else 0,
                           "town": _level_value(f, lv, "settlement_min"), "needs": conditions(head),
                           "units": units, "others": others})
        out.append({"chain": name, "group": E.chain_group(name), "builds": any(x["has"] for x in levels),
                    "castle": bool(levels) and all(x["kind"] == "castle" for x in levels), "levels": levels})
    return out


def lines_for_others(f, start, end, faction, culture):
    """The lines of a chain's block [start, end) that are not for a faction (or, faction None, a culture): every line
    of a level its factions list keeps out, and in the levels it may build each line (a recruit line, a capability
    'requires factions { }') whose factions list keeps it out (#374: Stats shown for one faction / culture)."""
    out = set()
    for lv in E.chain_tree(f, start, end)["levels"]:
        if not covers(factions_in(f.text(lv["head"])), faction, culture):
            out.update(range(lv["head"], lv["close"] + 1))
            continue
        for i in range(lv["open"] + 1, lv["close"]):
            if not covers(factions_in(f.text(i)), faction, culture):
                out.add(i)
    return out


def faction_chains(mod, faction, f=None):
    """chains() for a faction of the loaded mod (f: the buildings file as the editor shows it, typed lines and all;
    else the mod's own). [] without export_descr_buildings.txt."""
    if f is None:
        p = mod.file("edb")
        if not p:
            return []
        f = mod.load(p)
    types = None
    edu = mod.file("edu")
    if edu:
        from .units import read_units
        types = {u.type.lower() for u in read_units(mod.load(edu))}
    return chains(f, faction, mod.culture(faction), types)


def with_changes(items, changes):
    """chains() as the Roster's picks (App.roster_set) leave them, not yet written: a level given or taken
    ('building:<chain>:<level>') has its 'has' set and pending 'give' / 'take'; a unit added to a level
    ('recruit:<chain>:<level>:<type>' True) is a card with pending 'give', one taken away (False) pending 'take'.
    The items are copied; nothing else changes."""
    out = copy.deepcopy(items)
    for c in out:
        for lv in c["levels"]:
            lv["pending"] = None
            pick = changes.get("building:%s:%s" % (c["chain"], lv["name"]))
            if pick is True and not lv["has"]:
                lv["has"], lv["pending"] = "own", "give"
            elif pick is False and lv["has"]:
                lv["has"], lv["pending"] = None, "take"
            have = set()
            for u in lv["units"]:
                u["pending"] = "take" if changes.get(recruit_key(c["chain"], lv["name"], u["unit"])) is False \
                    else None
                have.add(u["unit"])
            head = recruit_key(c["chain"], lv["name"], "")
            for key, give in sorted(changes.items()):
                unit = key[len(head):] if key.startswith(head) else None
                if unit and give and unit not in have:
                    have.add(unit)
                    lv["units"].append({"unit": unit, "line": None, "key": "", "has": "own", "needs": "",
                                        "numbers": {}, "known": True, "pending": "give"})
        c["builds"] = any(x["has"] for x in c["levels"])
    return out


def upward(chain, level, unit, give, has_unit):
    """The Roster's keys for adding (give) or taking away a unit at a level of a chain (a chains() item): that level
    and every one above it - the game trains only what the town's CURRENT level lists, a unit put in one level was
    gone once the building grew (report #283). has_unit(level) tells
    whether the level recruits it for the faction now (as the files say). [(key, give)], give None where the files
    are so already (a pick there is dropped)."""
    names = [x["name"] for x in chain["levels"]]
    if level not in names:
        return []
    return [(recruit_key(chain["chain"], n, unit), None if bool(has_unit(n)) == give else give)
            for n in names[names.index(level):]]


def grouped(items, everyone=False, find=""):
    """[(group, [chain])] in GROUP_ORDER; only the chains the faction may build unless everyone; find = a part of
    the chain's name (any case)."""
    q = find.strip().lower()
    by = {}
    for c in items:
        if (everyone or c["builds"]) and (not q or q in c["chain"].lower()):
            by.setdefault(c["group"], []).append(c)
    return [(g, by[g]) for g in GROUP_ORDER if g in by]


def recruited_in(items, unit):
    """[(chain, level)] where the faction recruits the unit (the chains() it was read for)."""
    return [(c["chain"], lv["name"]) for c in items for lv in c["levels"] if lv["has"]
            for u in lv["units"] if u["unit"] == unit]


def unit_words(u):
    """One unit card's hover text: how it is recruited there, in plain words."""
    n = u["numbers"]
    parts = []
    if "most" in n:
        parts.append("the town's pool starts with %g, grows %g a turn, holds at most %g" % (
            n["start"], n["per_turn"], n["most"]))
    if n.get("experience"):
        parts.append("trained with experience %d" % n["experience"])
    if u["has"] in ("culture", "all"):
        parts.append("for its %s" % ("culture" if u["has"] == "culture" else "everyone (no faction named)"))
    if u["needs"]:
        parts.append("only when: %s" % u["needs"])
    if not u["known"]:
        parts.append("NOT in export_descr_unit.txt - the game stops at the start ('Unknown unit type specified')")
    return "; ".join(parts)


def text_index(mod, name):
    """{lower key: text} of a string table (export_buildings.txt, export_units.txt): the .txt the game reads, else
    Medieval II's .strings.bin (strtables.strings, cached)."""
    from .strtables import strings
    return {k.lower(): v.replace("\\n", "\n") for k, v in strings(mod, name).items()}


def _real(text, key):
    """A text players really read (gui_preview._real): not empty, not the key, not the 'DO NOT TRANSLATE' stand-in."""
    t = (text or "").strip()
    return bool(t) and t != key and "DO NOT TRANSLATE" not in t and not t.startswith("WARNING!")


def level_shown(index, level, faction, culture):
    """(name, description) players read for a building level: <level>_<faction>, <level>_<culture>, then <level>
    (the order the games look them up in - editors.level_names); '' for what the table lacks."""
    order = [k for k in (level + "_" + faction if faction else "", level + "_" + culture if culture else "", level) if k]
    name = next((index[k.lower()] for k in order if _real(index.get(k.lower()), level)), "")
    desc = next((index[(k + "_desc").lower()] for k in order if _real(index.get((k + "_desc").lower()), level)), "")
    return name, desc
