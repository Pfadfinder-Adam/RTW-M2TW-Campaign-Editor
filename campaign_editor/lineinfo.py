"""What a line of export_descr_unit.txt / export_descr_buildings.txt is, for the right click on it (the notepad and
the fields alike - the user, 2026-10-21: 'what the line means, its form - by commas, by spaces, what comes next -
and what it may hold'): its key, what it does, its form (the values in order with their separators), a line like it,
and the words it may take. One place for it - edufields / edbfields / unitattrs hold the knowledge, this puts it
together; the '?' hints read the same."""

import re

from . import edbfields, edufields, unitattrs

WORD_KEYS = ("attributes", "stat_pri_attr", "stat_sec_attr", "stat_ter_attr")


def split(line):
    """(indent, key, value, comment) of a line."""
    body, sep, comment = line.partition(";")
    indent = body[:len(body) - len(body.lstrip())]
    rest = body.strip()
    m = re.match(r"(\S+)\s*(.*)$", rest)
    key, value = (m.group(1), m.group(2).strip()) if m else ("", "")
    return indent, key, value, (sep + comment) if sep else ""


def _unit(key, m2):
    if key in ("stat_pri", "stat_sec", "stat_ter"):
        names = [n for n, _ in edufields.WEAPON]
        if m2:
            names.insert(9, edufields.EFFECT[0] + " (may be left out)")
        what = {"stat_pri": "the primary weapon (a missile weapon is always the primary)",
                "stat_sec": "the secondary weapon (a missile unit's melee arm, a side arm, an animal's attack)",
                "stat_ter": "Medieval II: a third weapon"}[key]
        return what, ", ".join(names) + "   (commas between; attack 0 or 'no' = no weapon)"
    if key in edufields.NOTE_ONLY:
        return edufields.NOTE % key, edufields.FORMS[key]
    if key in edufields.FIXED and key in edufields.FORMS:
        what = {"soldier": "the men: their model and how many", "formation": "how the men stand",
                "stat_health": "hit points", "stat_pri_armour": "the man's armour", "stat_sec_armour": "the "
                "animal's or vehicle's armour", "stat_ground": "bonus or penalty by ground", "stat_mental": "morale",
                "stat_food": "no longer used", "stat_cost": "what it costs"}.get(key, key)
        return what, edufields.FORMS[key]
    if key in edufields.FIXED:
        names = [n for n, _ in edufields.FIXED[key]]
        return key, ", ".join(names) + "   (commas between)"
    if key in edufields.LISTS:
        if key == "ownership":
            return edufields.LISTS[key], "faction or culture, faction or culture, ...   (commas between)"
        return edufields.LISTS[key], "word, word, ...   (commas between)"
    if key.startswith("era"):
        return ("Medieval II: the factions that use it in a multiplayer era", "N  faction, faction, ...   (the era "
                "number 0-2, a space, then commas)")
    if key in edufields.ONE:
        return edufields.ONE[key], edufields.FORMS.get(key, "one value")
    if key in unitattrs.ENGINE_KEYS:
        return unitattrs.ENGINE_KEYS[key][1], "one value"
    return "", ""


def _building(key):
    got = edbfields.LINES.get(key)
    what = got[0] if got else {"recruit": "a unit this level lets the town train",
                               "recruit_pool": "Medieval II: a unit this level lets the town hire from its pool",
                               "agent": "an agent this level lets the town train"}.get(key, "")
    return what, edbfields.form(key)


def words_for(kind, key, factions=()):
    """[(word, what it means)] the line may hold, or []."""
    if kind == "unit" and key in WORD_KEYS:
        out = {w: m for w, m in edufields.WORDS.items()}
        for word, line, effect in unitattrs.ATTRIBUTES:
            if line == key or key == "attributes" and line in ("attributes", ""):
                out.setdefault(word, effect + " (REX / M2EX)")
        return sorted(out.items())
    if (kind == "unit" and (key == "ownership" or key.startswith("era"))) or key == "factions":
        return [(f, "") for f in factions]
    if kind == "unit" and key in edufields.CHOICES:
        return [(w, "") for w in edufields.CHOICES[key]]
    if kind == "building" and key in edbfields.WORDS:
        return [(w, "") for w in edbfields.WORDS[key]]
    if kind == "unit" and unitattrs.for_line(key):
        return [(w, e) for w, e in unitattrs.for_line(key)]
    return []


def about(kind, line, m2=False, factions=()):
    """{'key', 'what', 'form', 'example', 'words': [(word, meaning)]} of the line."""
    _, key, value, _ = split(line)
    what, form = _unit(key, m2) if kind == "unit" else _building(key)
    return {"key": key, "value": value, "what": what, "form": (key + "  " + form) if form else "",
            "example": "", "words": words_for(kind, key, factions),
            "one": kind == "building" and key in edbfields.WORDS or kind == "unit" and key in edufields.CHOICES}   # the word REPLACES the line's first value


def with_word(line, word, one=False):
    """The line with word added to its list (commas between; 'no' replaced); one: the word put in place of the
    line's first value, the rest kept (a building's 'agent spy 0 requires ...')."""
    indent, key, value, comment = split(line)
    if one:
        rest = value.split(None, 1)[1:] if value else []
        return "%s%s\t%s%s" % (indent, key, " ".join([word] + rest), (" " + comment) if comment else "")
    have = [w for w in re.split(r"\s*,\s*", value) if w] if value else []
    if word in have:
        return line
    have = [w for w in have if w.lower() != "no"] + [word]
    return "%s%s\t%s%s" % (indent, key, ", ".join(have), (" " + comment) if comment else "")


def template(line, info):
    """The line's form put in to fill: 'key  <name>, <name>, ...' (the indent kept)."""
    indent, key, _, _ = split(line)
    form = info["form"][len(key):].split("   (")[0].strip()
    return "%s%s\t%s" % (indent, key, form)


__all__ = ["about", "words_for", "with_word", "template", "split"]
