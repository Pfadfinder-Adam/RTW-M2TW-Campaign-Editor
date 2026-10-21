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
        return what, ", ".join(names) + "   (commas between; 'no' for no weapon)"
    if key in edufields.FIXED:
        names = [n for n, _ in edufields.FIXED[key]]
        return key, ", ".join(names) + "   (commas between)"
    if key in edufields.LISTS:
        if key == "ownership":
            return edufields.LISTS[key], "faction or culture, faction or culture, ...   (commas between)"
        return edufields.LISTS[key], "word, word, ...   (commas between)"
    if key.startswith("era"):
        return "Medieval II: the factions that use it in this multiplayer era", "faction, faction, ...   (commas)"
    if key in edufields.ONE:
        return edufields.ONE[key], "one value"
    if key in unitattrs.ENGINE_KEYS:
        return unitattrs.ENGINE_KEYS[key][1], "one value"
    return "", ""


def _building(key):
    got = edbfields.LINES.get(key)
    if not got:
        return "", ""
    what, names = got
    return what, (" ".join(names) + "   (spaces between)") if names else ""


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
    if kind == "unit" and unitattrs.for_line(key):
        return [(w, e) for w, e in unitattrs.for_line(key)]
    return []


def about(kind, line, m2=False, factions=()):
    """{'key', 'what', 'form', 'example', 'words': [(word, meaning)]} of the line."""
    _, key, value, _ = split(line)
    what, form = _unit(key, m2) if kind == "unit" else _building(key)
    return {"key": key, "value": value, "what": what, "form": (key + "  " + form) if form else "",
            "example": "", "words": words_for(kind, key, factions)}


def with_word(line, word):
    """The line with word added to its list (commas between; 'no' replaced)."""
    indent, key, value, comment = split(line)
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
