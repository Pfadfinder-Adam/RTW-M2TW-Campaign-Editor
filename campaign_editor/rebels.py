"""Rebel types (Rebels... on the work bar, report #252): descr_rebel_factions.txt read and written, both games.

A rebel type is a block of the file:

    rebel_type      Livonian_Rebels
    category        peasant_revolt
    chance          3
    description     Livonian_Rebels
    unit            Woodsmen
    unit            EE Peasant Archers

the units the game raises when a region of that type revolts (or brigands / pirates appear); the name players read is
the description key in text/rebel_faction_descr.txt ({Livonian_Rebels} Livonian Rebels); each region names its type
on the 4th line of its block in descr_regions.txt. A type renamed or deleted pulls its regions along (the one web):
renamed - every region naming it follows; deleted - its regions get the type picked in its place. Lines of a type not
changed keep their bytes."""

import re

FILE = "descr_rebel_factions.txt"
TEXTS = "rebel_faction_descr.txt"
CATEGORIES = ("peasant_revolt", "brigands", "pirates", "gladiator_revolt")   # the vanilla files' own
KEYS = ("rebel_type", "category", "chance", "description", "unit")
# unit types per rebel type the game takes - REX / M2EX too: a fixed array in the engine source
# (rebel_faction_db.h MAX_REBEL_UNIT_TYPES 20; RebelFactionRegistry.cpp clamps to it), so no engine lifts it
VANILLA_UNITS = 20
RE_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")


class RebelType:
    def __init__(self, name, category="peasant_revolt", chance="3", description=None, units=(), start=None,
                 end=None, words=None):
        self.name, self.category, self.chance = name, category, str(chance)
        self.description = description if description is not None else name
        self.units = list(units)
        self.start, self.end = start, end          # its lines in the file as read (end: after its last key line)
        self.words = words                         # the text players read (rebel_faction_descr.txt), None = as is
        self.old = None                            # (name, category, chance, description, units) as read

    def key(self):
        return (self.name, self.category, self.chance, self.description, tuple(self.units))

    def changed(self):
        return self.old is None or self.key() != self.old

    def __repr__(self):
        return "RebelType(%s, %d units)" % (self.name, len(self.units))


def _body(line):
    return line.split(";")[0].split("//")[0].strip()


def read_lines(texts):
    """[RebelType] of the file's lines, each with its first and end line."""
    out, cur = [], None
    for i, line in enumerate(texts):
        t = _body(line)
        if not t:
            continue
        parts = t.split(None, 1)
        word, rest = parts[0].lower(), (parts[1].strip() if len(parts) > 1 else "")
        if word == "rebel_type":
            cur = RebelType(rest.split()[0] if rest else "", start=i, end=i + 1)
            cur.category, cur.chance, cur.description = "", "", None
            out.append(cur)
        elif cur is not None and word in KEYS:
            if word == "unit":
                cur.units.append(rest)
            elif word == "category":
                cur.category = rest
            elif word == "chance":
                cur.chance = rest
            elif word == "description":
                cur.description = rest
            cur.end = i + 1
        else:
            cur = None                              # a line of another kind ends the block
    for r in out:
        if r.description is None:
            r.description = r.name
        r.old = r.key()
    return out


def path_of(mod):
    return mod.find(FILE)


def read(mod):
    """(path, [RebelType]) - the mod's file, else the game's; with the names players read."""
    from .strtables import strings
    path = path_of(mod)
    types = read_lines(mod.load(path).texts()) if path else []
    table = strings(mod, TEXTS)
    for r in types:
        r.words_now = table.get((r.description or "").upper(), "")
    return path, types


def regions_of(mod, campaign):
    """{region: rebel type} as descr_regions.txt names them."""
    return {r: (v.get("rebels") or "") for r, v in mod.regions(campaign).items()}


def problems(mod, types):
    """Mistakes the game stumbles on, in plain words (nothing refused that the game takes)."""
    from .units import read_units
    out = []
    edu = mod.file("edu")
    known = {u.type.lower(): u for u in read_units(mod.load(edu))} if edu else {}
    names = [r.name.lower() for r in types]
    for r in types:
        if not r.changed():
            continue
        if not RE_NAME.match(r.name or ""):
            out.append("%s: a rebel type's name is one word (letters, digits, _ and -)" % (r.name or "(no name)"))
        if names.count(r.name.lower()) > 1:
            out.append("%s: two rebel types of that name" % r.name)
        if not str(r.chance).strip().isdigit():
            out.append("%s: chance must be a whole number (%s)" % (r.name, r.chance))
        if not r.units:
            out.append("%s: no unit - the game raises nobody" % r.name)
        for u in r.units:
            if known and u.lower() not in known:
                out.append("%s: unit '%s' is not in export_descr_unit.txt" % (r.name, u))
        if len(set(u.lower() for u in r.units)) > VANILLA_UNITS:
            out.append("%s: %d unit types - the game takes the first %d (REX / M2EX too), the rest are dropped" % (
                r.name, len(set(u.lower() for u in r.units)), VANILLA_UNITS))
    return out


def _lines_of(r, tab):
    sep = tab
    out = ["rebel_type" + sep + r.name, "category" + sep + r.category, "chance" + sep + str(r.chance),
           "description" + sep + r.description]
    return out + ["unit" + sep + u for u in r.units]


def _tab_of(f, types):
    """The gap the file puts after its keys (vanilla: tabs)."""
    for r in types:
        if r.start is not None:
            m = re.match(r"\s*rebel_type(\s+)", f.text(r.start))
            if m:
                return m.group(1)
    return "\t\t\t"


def plan_types(plan, campaign, types, given=None, read_types=None):
    """Write the rebel types as edited (types = the whole list, read with read() and changed; one taken out of the
    list goes). given = {region: rebel type} - descr_regions.txt's lines for them. A type renamed: its regions follow;
    a type gone: its regions take given's pick (the window asks) - a region left naming a type that is no more is
    refused in words."""
    mod = plan.mod
    path = path_of(mod)
    if not path:
        raise ValueError("this mod has no %s" % FILE)
    why = problems(mod, types)
    if why:
        raise ValueError("; ".join(why))
    f = plan.edit(path)
    old = {r.start: r for r in read_lines(f.texts())}
    tab = _tab_of(f, list(old.values()))
    keep = {r.start for r in types if r.start is not None}
    edits = []
    renamed = {}
    for start, o in old.items():
        if start not in keep:
            end = o.end
            if end < len(f.raw) and not f.text(end).strip():
                end += 1
            edits.append((start, end, [], "rebel type %s goes" % o.name))
    for r in types:
        if r.start is None:
            continue
        o = old.get(r.start)
        if o is None or o.name != r.old[0]:
            raise ValueError("%s changed since it was read - open the window again" % FILE)
        if r.key() == o.key():
            continue
        if r.name != o.name:
            renamed[o.name] = r.name
        lines = _lines_of(r, tab)
        # its comment on the rebel_type line stays (// Britons)
        first = f.text(r.start)
        m = re.search(r"\s*(//|;).*$", first)
        if m:
            lines[0] += m.group(0)
        edits.append((r.start, o.end, lines, "rebel type %s: %d unit(s), %s, chance %s" % (
            r.name, len(r.units), r.category, r.chance)))
    new = [r for r in types if r.start is None]
    for s, e, lines, note in sorted(edits, key=lambda x: -x[0]):
        f.raw[s:e] = [f.make(x) for x in lines]
        plan.note(f, note)
    if new:
        while f.raw and not f.text(len(f.raw) - 1).strip():
            f.raw.pop()
        for r in new:
            f.raw.append(f.make(""))
            f.raw.extend(f.make(x) for x in _lines_of(r, tab))
            plan.note(f, "new rebel type %s: %s" % (r.name, ", ".join(r.units)))
        f.raw.append(f.make(""))
    # the names players read
    words = {r.description: r.words for r in types if r.words is not None and r.words != getattr(r, "words_now", "")}
    for r in new:
        if r.words is None:
            words.setdefault(r.description, r.name.replace("_", " "))
    if words:
        from .strtables import write_texts
        write_texts(plan, TEXTS, words)
    # the regions: renamed types followed, gone types replaced, the picks of the Regions tab
    from .regionedit import edit_regions
    have = {r.name for r in types}
    now = regions_of(mod, campaign)
    want = {}
    for region, t in now.items():
        if t in renamed:
            want[region] = renamed[t]
    for region, t in (given or {}).items():
        if t and now.get(region) != t:
            want[region] = t
    left = sorted(r for r, t in now.items() if t and t not in have and t not in renamed and r not in want
                  and t in {o.name for o in old.values()})
    if left:
        raise ValueError("these regions name a rebel type that goes - give them another first: %s" % ", ".join(left))
    if want:
        edit_regions(plan, campaign, {r: {"rebels": t} for r, t in want.items()})
    return plan


__all__ = ["RebelType", "read", "read_lines", "plan_types", "problems", "regions_of", "CATEGORIES"]
