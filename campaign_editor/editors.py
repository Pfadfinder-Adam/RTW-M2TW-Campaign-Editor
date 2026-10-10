"""The unit and building editors' data side: a unit's block of
export_descr_unit.txt and a building chain's block of export_descr_buildings.txt
as fields (one line = one field: its key and the rest), changed in place with
each line's own layout kept; and pictures imported into the place the game
reads them from, in the format the mod's own pictures have.

    type             roman hastati          <- a unit block starts at 'type'
    dictionary       roman_hastati
    stat_cost        1, 400, 170, 60, 70, 400

    building core_building                  <- a chain; its levels, requirements
    {                                          and capabilities nest in braces
        levels governors_house governors_villa ...
"""

import io
import os
import re

from .textio import strip_comment, tokens

# ---------------------------------------------------------------------------
# Blocks and fields
# ---------------------------------------------------------------------------


class Field:
    def __init__(self, line, key, value, depth):
        self.line = line          # the line in the file
        self.key = key
        self.value = value        # the text after the key (comments left out)
        self.depth = depth        # brace depth (buildings), 0 for units


def unit_blocks(f):
    """[(type, first line, end line)] of export_descr_unit.txt."""
    out = []
    for i in range(len(f.raw)):
        t = tokens(f.text(i))
        if t[:1] == ["type"]:
            if out:
                out[-1][2] = i
            out.append([" ".join(strip_comment(f.text(i)).split()[1:]), i, len(f.raw)])
    return [tuple(b) for b in out]


def building_blocks(f):
    """[(chain, first line, end line)] of export_descr_buildings.txt: from
    'building <name>' to the brace that closes it."""
    out, depth, cur = [], 0, None
    for i in range(len(f.raw)):
        code = strip_comment(f.text(i))
        t = code.split()
        if depth == 0 and t[:1] == ["building"] and len(t) > 1:
            cur = [t[1], i, None]
        depth += code.count("{") - code.count("}")
        if cur and depth <= 0 and i > cur[1] and "}" in code:
            cur[2] = i + 1
            out.append(tuple(cur))
            cur, depth = None, 0
    return out


# what a chain is for, by the words in its name (vanilla and HLR names; the rest is 'other')
CHAIN_GROUPS = (("guild", ("guild", "chapter_house")),
                ("temple", ("temple", "shrine", "church", "mosque", "cathedral", "abbey", "religi")),
                ("economy", ("market", "farm", "road", "mine", "caravan", "trade", "smith", "hinterland",
                             "tavern", "merchant", "bank", "sewer", "health", "bath", "paved")),
                ("military", ("barracks", "equestrian", "missiles", "siege", "stables", "range", "military",
                              "cannon", "gun", "tower", "port", "shipwright", "dock", "academy", "tourney")),
                ("walls and core", ("core", "defenses", "wall", "castle", "citadel")),
                ("culture and law", ("academic", "amphitheat", "theatre", "law", "university", "school",
                                     "brothel", "arena", "palace", "library", "hall", "music")))


def chain_group(name):
    n = name.lower()
    for group, words in CHAIN_GROUPS:
        if any(w in n for w in words):
            return group
    return "other"


def block_facets(f, kind, block):
    """What the editors' lists sort and filter by. A unit: {'owners', 'category',
    'class', 'mercenary', 'general'}; a building chain: {'factions' (None = everyone),
    'recruits', 'group'}."""
    name, a, b = block
    if kind == "unit":
        out = {"owners": [], "category": "", "class": "", "mercenary": False, "general": False}
        for i in range(a, b):
            t = strip_comment(f.text(i)).split(None, 1)
            if not t:
                continue
            rest = t[1].strip() if len(t) > 1 else ""
            if t[0] == "ownership":
                out["owners"] = [x for x in rest.replace(",", " ").split() if x]
            elif t[0] in ("category", "class"):
                out[t[0]] = rest
            elif t[0] == "attributes":
                attrs = [x.strip() for x in rest.split(",")]
                out["mercenary"] = "mercenary_unit" in attrs
                out["general"] = any(x.startswith("general_unit") for x in attrs)
        return out
    from .roster import factions_in, recruit_of, RECRUITING
    facs, everyone, recruits = set(), False, False
    for lv in chain_tree(f, a, b)["levels"]:
        names = factions_in(f.text(lv["head"]))
        if names is None or "all" in names:
            everyone = True
        else:
            facs.update(names)
    for i in range(a, b):
        if recruit_of(f.text(i), RECRUITING):
            recruits = True
            break
    return {"factions": None if everyone else sorted(facs), "recruits": recruits, "group": chain_group(name)}


def chain_tree(f, start, end):
    """The shape of a building chain's block [start, end):
    {'levels_line': i, 'levels': [{'name', 'head', 'open', 'close',
     'capability': (open, close) or None, 'upgrades': (open, close) or None}]}
    - 'head' is the '<level> requires ...' line, open/close its braces' lines.
    Braces inside one line ('factions { a, b, }') do not count."""
    out = {"levels_line": None, "levels": []}
    stack = []                     # [(key, head line, open line)]
    key, key_line = None, None
    names = []
    for i in range(start, end):
        code = RE_INLINE.sub("", strip_comment(f.text(i)))
        s = code.strip()
        word = s.replace("{", " ").replace("}", " ").split()
        if word:
            key, key_line = word[0], i
            if key == "levels" and out["levels_line"] is None:
                out["levels_line"] = i
                names = word[1:]
        for ch in code:
            if ch == "{":
                stack.append((key, key_line, i))
            elif ch == "}" and stack:
                k, head, op = stack.pop()
                depth = len(stack)
                if depth == 2 and k in names:
                    lv = {"name": k, "head": head, "open": op, "close": i, "capability": None, "upgrades": None}
                    lv.update(out.pop("_inner", {}))
                    out["levels"].append(lv)
                elif depth == 3 and k in ("capability", "upgrades"):
                    out.setdefault("_inner", {})[k] = (op, i)
    out.pop("_inner", None)
    return out


RE_INLINE = re.compile(r"\{[^{}]*\}")      # a list closed on its own line


def fields(f, start, end):
    """[Field] of the lines [start, end): every line with a key (not braces or
    comments alone)."""
    out, depth = [], 0
    for i in range(start, end):
        code = strip_comment(f.text(i))
        s = code.strip()
        if s and s not in ("{", "}"):
            key, _, rest = s.partition(" ")
            if "\t" in key:
                key, _, more = key.partition("\t")
                rest = (more + " " + rest).strip()
            out.append(Field(i, key, rest.strip(), max(depth, 0)))
        depth += code.count("{") - code.count("}")
    return out


def set_value(text, value):
    """A line with the text after its key replaced; the indent, the gap after the
    key and a comment at the end are kept."""
    body, sep, comment = text.partition(";")
    indent = body[:len(body) - len(body.lstrip())]
    rest = body.lstrip()
    key_end = 0
    while key_end < len(rest) and not rest[key_end].isspace():
        key_end += 1
    key = rest[:key_end]
    gap_end = key_end
    while gap_end < len(rest) and rest[gap_end].isspace():
        gap_end += 1
    gap = rest[key_end:gap_end] or "\t"
    tail = body[len(body.rstrip()):] if sep else ""
    return indent + key + gap + value + tail + sep + comment


def apply_fields(plan, path, changes, what):
    """changes = {line: new value}: those lines of the file get the new text after
    their key. what: for the notes ('unit roman hastati')."""
    if not changes:
        return
    f = plan.edit(path)
    for line, value in sorted(changes.items()):
        line = int(line)
        old = f.text(line)
        new = set_value(old, value.strip())
        if new != old:
            f.set(line, new)
            plan.note(f, "%s: %s -> %s" % (what, " ".join(strip_comment(old).split()),
                                           " ".join(strip_comment(new).split())))


# ---------------------------------------------------------------------------
# Pictures
# ---------------------------------------------------------------------------

def tga_info(path):
    """(width, height, bits per pixel) from a TGA header, or None."""
    try:
        with open(path, "rb") as fh:
            h = fh.read(18)
        if len(h) < 18:
            return None
        return h[12] | (h[13] << 8), h[14] | (h[15] << 8), h[16]
    except OSError:
        return None


def sample_size(folder, pattern_end, limit=40):
    """The most common (width, height, bpp) of the TGA pictures under folder whose
    names end with pattern_end - what the mod's own pictures of that kind are."""
    seen = {}
    n = 0
    for dirpath, _, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(pattern_end):
                info = tga_info(os.path.join(dirpath, name))
                if info:
                    seen[info] = seen.get(info, 0) + 1
                    n += 1
                    if n >= limit:
                        break
        if n >= limit:
            break
    return max(seen, key=seen.get) if seen else None


def tga_bytes(src, size=None):
    """src (PNG, JPG, TGA... any picture Pillow reads) as an uncompressed 32-bit TGA,
    resized to size (width, height) if given - a (width, height, bits) of tga_info / sample_size is fine too."""
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    size = tuple(size)[:2] if size else None
    if size and im.size != size:
        im = im.resize(tuple(size), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="TGA", rle=False, orientation=-1)      # bottom-up, like the game's own
    return out.getvalue()


def unit_picture_targets(mod, dictionary, factions, info=False):
    """Where a unit's card (or info picture) goes: ui/units/<f>/#<dict>.tga or
    ui/unit_info/<f>/<dict>_info.tga for each faction folder."""
    folder = os.path.join(mod.data, "ui", "unit_info" if info else "units")
    name = ("%s_info.tga" if info else "#%s.tga") % dictionary
    return [os.path.join(folder, f, name) for f in factions]


def unit_picture_need(mod, info=False):
    """(w, h, bpp) of the mod's own unit cards / info pictures (vanilla: 48 x 64 cards)."""
    for folder in mod.dirs("ui/" + ("unit_info" if info else "units")):     # the mod's, else the game's
        got = sample_size(folder, "_info.tga" if info else ".tga")
        if got:
            return got
    return None


def building_picture_target(mod, culture, level, constructed=False):
    """ui/<culture>/buildings/#<culture>_<level>[_constructed].tga."""
    return os.path.join(mod.data, "ui", culture, "buildings",
                        "#%s_%s%s.tga" % (culture, level, "_constructed" if constructed else ""))


def building_picture_need(mod, culture, constructed=False):
    end = "_constructed.tga" if constructed else ".tga"
    for folder in mod.dirs("ui/%s/buildings" % culture) + mod.dirs("ui"):   # the mod's, else the game's
        got = sample_size(folder, end)
        if got:
            return got
    return None


def import_picture(plan, src, targets, size=None):
    """The picture src written to every target path (a TGA in the given size)."""
    data = tga_bytes(src, size)
    for t in targets:
        plan.binary(t, data)
        plan.notes.append((plan.mod.rel(t), "picture from %s%s" % (
            os.path.basename(src), " (%d x %d)" % tuple(size)[:2] if size else "")))


# ---------------------------------------------------------------------------
# New units and buildings, copied from one there is
# ---------------------------------------------------------------------------
def _text_file(mod, name):
    return mod.text_file(name)


def copy_text_entries(plan, path, renames):
    """In a string table: every entry whose key is one of renames (old -> new, keys
    without braces, any case) copied under the new key right after the old one's
    whole entry. Returns the number of entries copied."""
    from .clone import entry_end_in
    if not path:
        return 0
    f = plan.edit(path)
    low = {k.lower(): v for k, v in renames.items()}
    n, i = 0, 0
    while i < len(f.raw):
        text = f.text(i)
        s = text.lstrip()
        if s.startswith("{") and "}" in s:
            key = s[1:s.index("}")]
            new = low.get(key.lower())
            if new:
                end = entry_end_in(f, i)
                lines = [text.replace("{" + key + "}", "{" + new + "}", 1)] + [f.text(k) for k in range(i + 1, end)]
                f.insert(end, lines)
                n += 1
                i = end + len(lines)
                continue
        i += 1
    if n:
        plan.note(f, "%d string(s) copied" % n)
    return n


def set_text_values(plan, path, values):
    """In a string table: the value of each key of values ({key: text}, any case) set to its text, the key's
    own spelling and the gap after it kept; a text of several lines is written over several lines (a value runs
    until the next {KEY} - the tables' own way). A key the table lacks is added at its end."""
    from .clone import entry_end_in
    values = {k: v for k, v in values.items() if v is not None}
    if not path or not values:
        return
    f = plan.edit(path)
    low = {k.lower(): (k, v) for k, v in values.items()}
    done, gap = set(), "\t"
    i = 0
    while i < len(f.raw):
        s = f.text(i).lstrip()
        if s.startswith("{") and "}" in s:
            key = s[1:s.index("}")]
            rest = s[s.index("}") + 1:]
            own = rest[:len(rest) - len(rest.lstrip())]
            gap = own or gap
            hit = low.get(key.lower())
            if hit:
                end = entry_end_in(f, i)
                head = f.text(i)[:f.text(i).index("}") + 1]
                parts = hit[1].split("\n")
                f.raw[i:end] = [f.make(x) for x in [head + own + parts[0]] + parts[1:]]
                done.add(key.lower())
                i += 1
                continue
        i += 1
    new = [k for k in low if k not in done]
    if new:
        lines = []
        for k in new:
            parts = low[k][1].split("\n")
            lines += ["{%s}%s%s" % (low[k][0], gap, parts[0])] + parts[1:]
        f.insert(len(f.raw), lines)
    plan.note(f, "text of %s" % ", ".join(sorted(v[0] for v in low.values())))


def copy_unit(plan, src_type, new_type, new_dict, recruit=True, texts=None, owners=None, values=None, pictures=None):
    """A new unit: the block of src_type copied after it under new_type and new_dict,
    its names and descriptions (export_units.txt) and cards copied to the new
    dictionary name, and - with recruit - a recruit line next to each of the old
    unit's in export_descr_buildings.txt. The step-by-step New unit window also gives: texts {'name',
    'descr', 'descr_short'} (what players read), owners [factions or cultures] (its ownership line),
    values {key: value} for the copied block's lines (soldier, stat_cost ...) and pictures {'card' |
    'info': a picture file} put in the size the mod's own cards have."""
    mod = plan.mod
    new_type, new_dict = " ".join(new_type.split()), new_dict.strip()
    if not new_type or not new_dict or " " in new_dict:
        raise ValueError("a new unit needs a type and a dictionary name without spaces")
    edu = mod.file("edu")
    f = plan.edit(edu)
    blocks = unit_blocks(f)
    if any(b[0].lower() == new_type.lower() for b in blocks):
        raise ValueError("a unit '%s' exists already" % new_type)
    src = next((b for b in blocks if b[0] == src_type), None)
    if src is None:
        raise ValueError("no unit '%s' in export_descr_unit.txt" % src_type)
    old_dict = None
    lines = []
    for i in range(src[1], src[2]):
        t = tokens(f.text(i))
        if t[:1] == ["dictionary"] and len(t) > 1:
            old_dict = t[1]
            lines.append(set_value(f.text(i), new_dict))
        elif t[:1] == ["type"]:
            lines.append(set_value(f.text(i), new_type))
        else:
            lines.append(f.text(i))
    for b in blocks:
        if old_dict and any(tokens(f.text(i))[:2] == ["dictionary", new_dict] for i in range(b[1], b[2])):
            raise ValueError("the dictionary name '%s' is taken by %s" % (new_dict, b[0]))
    vals = dict(values or {})
    if owners:
        vals["ownership"] = ", ".join(owners)
    seen = set()
    for i, text in enumerate(lines):
        t = tokens(text)
        if t and t[0] in vals and t[0] not in seen and t[0] not in ("type", "dictionary"):
            lines[i] = set_value(text, vals[t[0]])
            seen.add(t[0])
    for key in vals:
        if key not in seen and key not in ("type", "dictionary"):
            plan.warn(f, "%s has no '%s' line to set - left out" % (src_type, key))
    while lines and not lines[-1].strip():
        lines.pop()
    at = src[2]
    f.insert(at, lines + [""])
    plan.note(f, "unit %s copied from %s (dictionary %s)" % (new_type, src_type, new_dict))
    if old_dict:
        copy_text_entries(plan, _text_file(mod, "export_units.txt"), {
            old_dict: new_dict, old_dict + "_descr": new_dict + "_descr",
            old_dict + "_descr_short": new_dict + "_descr_short"})
        for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
            for fac, _ in mod.listing("ui/" + sub):             # the mod's folders and the game's under it
                srcp = mod.find("ui/%s/%s/%s" % (sub, fac, pattern % old_dict))       # the card in either
                if srcp:
                    plan.copy(srcp, os.path.join(mod.data, "ui", sub, fac, pattern % new_dict))
    if texts:
        set_text_values(plan, _text_file(mod, "export_units.txt"), {
            new_dict: texts.get("name"), new_dict + "_descr": texts.get("descr"),
            new_dict + "_descr_short": texts.get("descr_short")})
    if owners:                                      # the new owners' card folders get a copy too
        facs = dict(mod.factions())
        for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
            made = [(a, d) for a, d in plan.copies if os.path.basename(d).lower() == (pattern % new_dict).lower()]
            if not made:
                continue
            for fac in owners:
                if fac in facs and not any(os.path.basename(os.path.dirname(d)).lower() == fac.lower()
                                           for _, d in made):
                    plan.copy(made[0][0], os.path.join(mod.data, "ui", sub, fac, pattern % new_dict))
    for which, pic in (pictures or {}).items():
        if not pic:
            continue
        info = which == "info"
        name = (("%s_info.tga" if info else "#%s.tga") % new_dict).lower()
        targets = [d for _, d in plan.copies if os.path.basename(d).lower() == name]
        if not targets:
            targets = unit_picture_targets(mod, new_dict, [o for o in (owners or []) if o in dict(mod.factions())],
                                           info)
        plan.copies = [(a, d) for a, d in plan.copies if d not in targets]
        import_picture(plan, pic, targets, unit_picture_need(mod, info))
    if recruit and mod.file("edb"):
        from .roster import recruit_of
        e = plan.edit(mod.file("edb"))
        n, i = 0, 0
        q = '"%s"' % src_type
        while i < len(e.raw):
            text = e.text(i)
            if (recruit_of(text) or ("", ""))[1] == src_type:
                e.insert(i + 1, [_owners_only(text.replace(q, '"%s"' % new_type, 1), owners, mod)])
                n += 1
                i += 2
                continue
            i += 1
        if n:
            plan.note(e, "%s recruited where %s is (%d line(s))" % (new_type, src_type, n))


def _owners_only(text, owners, mod):
    """A recruit line copied for a new unit, its factions list narrowed to the unit's owners (factions, or cultures
    standing for theirs): the game stops on a line letting in a faction the unit's ownership does not ('Settlement
    recruitment availability included unit ... but the faction is spain and the unit ownership does not allow
    this'). A list keeps the names it shares with the owners, else gets the owners; a line with no list gets one."""
    if not owners:
        return text
    from .roster import factions_in, with_factions
    now = factions_in(text)
    cultures = {}
    for fac, _ in mod.factions():
        try:
            cultures.setdefault(mod.culture(fac), set()).add(fac)
        except Exception:
            pass
    own = set(owners) | {f for o in owners for f in cultures.get(o, ())}
    if now is None:
        code, sep, comment = text.partition(";")
        return "%s requires factions { %s}%s%s" % (code.rstrip(), "".join("%s, " % n for n in owners),
                                                   (" " + sep) if sep else "", comment)
    keep = [n for n in now if n in own or n in owners]
    return with_factions(text, keep or list(owners))


def renamed_chain_lines(src_lines, src_chain, new_chain, level_names):
    """A chain block's lines with the chain and its levels renamed ({old level: new}) where they are names: the
    'building', 'levels' and 'upgrades' lines, each level's own head, and the lines inside an upgrades list. Other
    lines (a requires naming another chain, a recruit line) stay as they are. Used by copy_building and by moving a
    chain into another mod (packs.import_buildings)."""
    import re
    words = dict(level_names)
    words[src_chain] = new_chain

    def swap(text):
        return re.sub(r"\b[A-Za-z0-9_]+\b", lambda m: words.get(m.group(0), m.group(0)), text)
    lines = []
    for text in src_lines:
        code = strip_comment(text).strip()
        head = code.split()[:1]
        if head in (["building"], ["levels"], ["upgrades"]) or (head and head[0] in level_names) or \
                (lines and strip_comment(lines[-1]).strip().split()[:1] == ["upgrades"]) or \
                (head and all(w in level_names for w in code.split())):
            lines.append(swap(text))
        else:
            lines.append(text)
    return lines


def copy_building(plan, src_chain, new_chain, level_names, texts=None, factions=None, pictures=None):
    """A new building chain: src_chain's block copied under new_chain with its levels
    renamed by level_names {old: new} (in 'levels', their own blocks and 'upgrades'),
    their names and descriptions (export_buildings.txt, every key made of a level name)
    and pictures (ui/<culture>/buildings/#<culture>_<level>[_constructed].tga). The step-by-step New building
    window also gives: texts {new level: {'name', 'desc', 'desc_short'}}, factions [who may build every
    level: factions or cultures] and pictures {new level: a picture file, or {'pic': file, 'constructed': file}}."""
    import re
    from .roster import factions_groups, with_factions
    mod = plan.mod
    edb = mod.file("edb")
    f = plan.edit(edb)
    blocks = building_blocks(f)
    if any(b[0] == new_chain for b in blocks):
        raise ValueError("a building chain '%s' exists already" % new_chain)
    src = next((b for b in blocks if b[0] == src_chain), None)
    if src is None:
        raise ValueError("no building chain '%s'" % src_chain)
    taken = set()
    for b in blocks:
        for fd in fields(f, b[1], b[2]):
            if fd.key == "levels":
                taken.update(fd.value.split())
    for old, new in level_names.items():
        if not re.match(r"^[A-Za-z0-9_]+$", new or ""):
            raise ValueError("level name '%s': letters, digits and _ only" % new)
        if new in taken:
            raise ValueError("a level '%s' exists already" % new)
    lines = renamed_chain_lines([f.text(i) for i in range(src[1], src[2])], src_chain, new_chain, level_names)
    new_levels = set(level_names.values())
    if factions:
        for i, text in enumerate(lines):
            head = strip_comment(text).strip().split()[:1]
            if head and head[0] in new_levels and "requires" in text:
                groups = factions_groups(text)
                if len(groups) == 1:
                    lines[i] = with_factions(text, list(factions))
                elif len(groups) > 1:
                    plan.warn(f, "%s: its requires line has %d factions groups (REX) - left as it is, change "
                                 "it in Buildings" % (head[0], len(groups)))
    f.insert(src[2], [""] + lines)
    plan.note(f, "building %s copied from %s: levels %s" % (
        new_chain, src_chain, ", ".join("%s -> %s" % kv for kv in level_names.items())))
    path = _text_file(mod, "export_buildings.txt")
    keys = {}
    if path:
        for s in mod.load(path).texts():
            s = s.lstrip()
            if s.startswith("{") and "}" in s:
                k = s[1:s.index("}")]
                for old, new in level_names.items():
                    if k.lower() == old.lower() or k.lower().startswith(old.lower() + "_"):
                        keys[k] = new + k[len(old):]
                if k.lower() == src_chain.lower() + "_name":      # the chain's own name ({market_name}): the
                    keys[k] = new_chain + "_name"                    # game asks for it ('localised string ...')
        copy_text_entries(plan, path, keys)
    # the pictures of every culture folder the mod or the game's data under it holds (a mod folder keeps only
    # what it changes); the copies go into the mod
    cultures = [c for c, _ in mod.listing("ui") if mod.dirs("ui/%s/buildings" % c)]
    listing = {c: {n.lower(): p for n, p in mod.listing("ui/%s/buildings" % c)} for c in cultures}
    if cultures:
        def card(old, tail, cult):
            """The level's picture for this culture: its own, else one of another culture's - in its folder first
            (Barbarian Invasion's nomad folder holds barbarian and hun pictures), then in the others' folders."""
            own = listing[cult].get(("#%s_%s%s" % (cult, old, tail)).lower())
            if own:
                return own
            for c2 in [cult] + [c for c in cultures if c != cult]:
                for c3 in cultures:
                    p = listing[c2].get(("#%s_%s%s" % (c3, old, tail)).lower())
                    if p:
                        return p
            return None
        for cult in cultures:
            folder = os.path.join(mod.data, "ui", cult, "buildings")
            smalls = {n.lower(): p for n, p in mod.listing("ui/%s/buildings/construction" % cult)}
            for old, new in level_names.items():
                for tail in (".tga", "_constructed.tga"):
                    src = card(old, tail, cult)
                    if src:
                        plan.copy(src, os.path.join(folder, "#%s_%s%s" % (cult, new, tail)))
                got = smalls.get(("#%s_%s.tga" % (cult, old)).lower())
                if got:                                     # Medieval II: the construction queue's small pictures
                    plan.copy(got, os.path.join(folder, os.path.basename(os.path.dirname(got)),
                                                "#%s_%s.tga" % (cult, new)))
    if texts:
        # a level's name and description, and every culture's / faction's own copy of them (<level>_<culture>,
        # <level>_<culture>_desc ...): the game shows the most specific one, so all say the new text
        tpath = _text_file(mod, "export_buildings.txt")
        made = set(keys.values()) if path else set()
        vals = {}
        for lvl, t in texts.items():
            for k in {lvl} | {k for k in made if k.lower().startswith(lvl.lower() + "_")}:
                low = k.lower()
                if low.endswith("_desc_short"):
                    vals[k] = t.get("desc_short")
                elif low.endswith("_desc"):
                    vals[k] = t.get("desc")
                else:
                    vals[k] = t.get("name")
            vals.setdefault(lvl + "_desc", t.get("desc"))
            vals.setdefault(lvl + "_desc_short", t.get("desc_short"))
        set_text_values(plan, tpath, vals)
    # pictures {level: file} (the picture in the town) or {level: {'pic': file, 'constructed': file}}
    for lvl, given in (pictures or {}).items():
        pair = given if isinstance(given, dict) else {"pic": given}
        for built, pic in ((False, pair.get("pic")), (True, pair.get("constructed"))):
            if not pic:
                continue
            tail = "_constructed.tga" if built else ".tga"
            names = {("#%s_%s%s" % (c, lvl, tail)).lower() for c in cultures}
            targets = [d for _, d in plan.copies if os.path.basename(d).lower() in names]
            if not targets:
                targets = [building_picture_target(mod, c, lvl, built) for c in cultures]
            plan.copies = [(a, d) for a, d in plan.copies if d not in targets]
            for t in targets:
                cult = os.path.basename(os.path.dirname(os.path.dirname(t)))
                import_picture(plan, pic, [t], building_picture_need(mod, cult, built))
                smalls = mod.dirs("ui/%s/buildings/construction" % cult)
                if not built and smalls:                                # its small one in the construction queue
                    to = os.path.join(os.path.dirname(t), os.path.basename(smalls[0]), os.path.basename(t))
                    plan.copies = [(a, d) for a, d in plan.copies if d != to]
                    import_picture(plan, pic, [to], sample_size(smalls[0], ".tga") or (64, 51))


# ---------------------------------------------------------------------------
# Lines added and removed, and what a change drags along
# ---------------------------------------------------------------------------
# lines that hold a block together: never removed by hand
FIXED_UNIT = {"type", "dictionary"}
FIXED_BUILDING = {"building", "levels", "capability", "upgrades"}
PLACES = ("capability", "upgrades", "level")


def _indent(f, a, b):
    """The indent of the lines inside braces opened on line a and closed on line b."""
    for i in range(a + 1, b):
        s = strip_comment(f.text(i))
        if s.strip() and s.strip() not in ("{", "}"):
            return s[:len(s) - len(s.lstrip())]
    close = f.text(b)
    lead = close[:len(close) - len(close.lstrip())]
    return lead + ("\t" if "\t" in lead else "    ")


def line_place(f, kind, block, place=None, level=None, key=None):
    """(position, [lines]) for a new line in a unit block or a building chain:
    position = the line it goes before; lines = a function text -> the lines to
    insert (with a capability / upgrades block around it when the level has none)."""
    name, a, b = block
    if kind == "unit":
        last = same = None
        for i in range(a, b):
            if strip_comment(f.text(i)).strip():
                last = i
                if key and tokens(f.text(i))[:1] == [key]:
                    same = i                       # next to the lines of its kind (officer, officer...)
        at = (same if same is not None else last if last is not None else a) + 1
        ind = f.text(a)[:len(f.text(a)) - len(f.text(a).lstrip())]
        return at, lambda text: [ind + text]
    tree = chain_tree(f, a, b)
    lv = next((x for x in tree["levels"] if x["name"] == level), None)
    if lv is None:
        raise ValueError("no level %s in %s" % (level, name))
    if place in ("capability", "upgrades"):
        if lv[place]:
            op, cl = lv[place]
            ind = _indent(f, op, cl)
            return cl, lambda text: [ind + text]
        ind = _indent(f, lv["open"], lv["close"])
        inner = ind + ("\t" if "\t" in ind else "    ")
        at = lv["open"] + 1 if place == "capability" else lv["close"]
        return at, lambda text: [ind + place, ind + "{", inner + text, ind + "}"]
    ind = _indent(f, lv["open"], lv["close"])
    at = lv["close"]
    if lv["upgrades"]:                    # before 'upgrades', where the level's own lines are
        at = lv["upgrades"][0]
        if tokens(f.text(at))[:1] != ["upgrades"] and tokens(f.text(at - 1))[:1] == ["upgrades"]:
            at -= 1
    return at, lambda text: [ind + text]


def removable(kind, fd, tree=None, required=()):
    """Why a field's line may not be removed, or None. required: the keys every unit
    (every building level) of the mod has - the game expects them."""
    fixed = FIXED_UNIT if kind == "unit" else FIXED_BUILDING
    if fd.key in fixed:
        return "%s holds the block together" % fd.key
    if tree and any(lv["head"] == fd.line for lv in tree["levels"]):
        return "a level's own line - remove the level from 'levels' by copying the chain instead"
    if fd.key in required and (kind == "unit" or fd.depth == 3):
        return "every %s has a '%s' line" % ("unit" if kind == "unit" else "building level", fd.key)
    return None


def required_keys(f, kind):
    """The keys every unit block has (kind 'unit'), or every building level has on its
    own (not inside capability / upgrades)."""
    sets = []
    if kind == "unit":
        for _, a, b in unit_blocks(f):
            sets.append({fd.key for fd in fields(f, a, b)})
    else:
        for _, a, b in building_blocks(f):
            for lv in chain_tree(f, a, b)["levels"]:
                inner = set()
                for p in ("capability", "upgrades"):
                    if lv[p]:
                        inner.update(range(lv[p][0], lv[p][1] + 1))
                sets.append({tokens(f.text(i))[0] for i in range(lv["open"] + 1, lv["close"])
                             if i not in inner and tokens(f.text(i)) and tokens(f.text(i))[0] not in ("{", "}")})
    return set.intersection(*sets) if sets else set()


def restructure(plan, path, kind, adds, removes):
    """adds = [{'block': name, 'place', 'level', 'key', 'text'}], removes = [line] (lines
    of the file as it is on disk; field changes keep the line count). Every insert and
    removal is placed first, then done from the bottom up."""
    if not adds and not removes:
        return
    f = plan.edit(path)
    blocks = unit_blocks(f) if kind == "unit" else building_blocks(f)
    by = {b[0]: b for b in blocks}
    work = []                                   # (position, order, 'del' | lines)
    for n, op in enumerate(adds):
        blk = by.get(op["block"])
        if blk is None:
            raise ValueError("no %s %s" % (kind, op["block"]))
        at, make = line_place(f, kind, blk, op.get("place"), op.get("level"), op.get("key"))
        work.append((at, 1, n, make(op["text"].strip())))
        plan.note(f, "%s %s%s: + %s" % (kind, op["block"], "/" + op["level"] if op.get("level") else "",
                                         op["text"].strip()))
    for ln in sorted(set(removes)):
        work.append((ln, 0, 0, "del"))
        plan.note(f, "%s: - %s" % (_block_of(blocks, ln), " ".join(strip_comment(f.text(ln)).split())))
    # bottom first; at one position the removal before the inserts, inserts in the order given
    work.sort(key=lambda w: (-w[0], w[1], -w[2]))
    for at, _, _, what in work:
        if what == "del":
            f.delete(at, at + 1)
        else:
            f.insert(at, what)


def _block_of(blocks, line):
    return next(("%s" % b[0] for b in blocks if b[1] <= line < b[2]), "line %d" % (line + 1))


def keys_seen(f, kind, place=None):
    """{key: an example value} of the lines the mod has in that place: unit lines,
    capability lines (not recruit), or a level's own lines."""
    out = {}
    if kind == "unit":
        for i in range(len(f.raw)):
            s = strip_comment(f.text(i)).strip()
            if s:
                k, _, v = s.partition(" ") if " " in s else s.partition("\t")
                out.setdefault(k, v.strip())
        out.pop("type", None)
        from .unitattrs import ENGINE_KEYS           # keys the engine knows, even when no unit has one yet
        for k, (example, _) in ENGINE_KEYS.items():
            out.setdefault(k, example)
        return out
    for chain, a, b in building_blocks(f):
        for lv in chain_tree(f, a, b)["levels"]:
            if place == "capability" and lv["capability"]:
                rng = range(lv["capability"][0] + 1, lv["capability"][1])
            elif place == "level":
                inner = set()
                for p in ("capability", "upgrades"):
                    if lv[p]:
                        inner.update(range(lv[p][0] - 1, lv[p][1] + 1))
                rng = [i for i in range(lv["open"] + 1, lv["close"]) if i not in inner]
            else:
                continue
            for i in rng:
                s = strip_comment(f.text(i)).strip()
                if s and s not in ("{", "}"):
                    k, _, v = s.replace("\t", " ").partition(" ")
                    if k not in RECRUIT_KEYS:
                        out.setdefault(k, v.strip())
    return out


def conditions_seen(f):
    """The words that follow 'requires' / 'and' / 'or' / 'not' in the buildings file:
    what a requirement may name in this mod (factions, building_present_min_level,
    hidden_resource, marian_reforms...)."""
    seen = {}
    for l in f.texts():
        for m in re.finditer(r"\b(?:requires|and|or|not)\s+([a-z_]+)", strip_comment(l)):
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    seen.pop("not", None)
    return sorted(seen, key=lambda k: -seen[k])


# ---- checks ----
RECRUIT_KEYS = ("recruit", "recruit_pool", "retrain", "retrain_pool")
RECRUIT_FORMS = {
    "recruit": 'a recruit line is: recruit "unit name" <experience> requires factions { ... }',
    "retrain": 'a retrain line (REX) is: retrain "unit name" <experience> requires factions { ... }',
    "recruit_pool": 'a recruit_pool line is: recruit_pool "unit name" <starting units> <new units a turn> '
                    '<most units> <experience> requires factions { ... }',
    "retrain_pool": 'a retrain_pool line (REX) is: retrain_pool "unit name" <starting units> <new units a turn> '
                    '<most units> <experience> requires factions { ... }'}


def _number(x):
    try:
        float(x)
        return True
    except ValueError:
        return False


def recruit_text(dialect, unit, exp, pool=("1", "0.5", "4"), retrain=False, factions=(), extra=""):
    """A recruit line in the file's own form: Rome 'recruit "u" exp', Medieval II
    'recruit_pool "u" start per_turn most exp'; retrain = REX's retrain-only key."""
    key = ("retrain" if retrain else "recruit") + ("_pool" if dialect == "pool" else "")
    t = '%s "%s"  %s' % (key, unit, ("%s   %s   %s  %s" % (tuple(pool) + (exp,))) if dialect == "pool" else exp)
    fs = [x for x in factions if x]
    if fs:
        t += "  requires factions { %s}" % "".join("%s, " % x for x in fs)
    extra = extra.strip()
    if extra:
        t += (" " if fs else "  requires ") + (extra if fs or not extra.startswith("and ") else extra[4:])
    return t
RE_PRESENT = re.compile(r"\bbuilding_present(?:_min_level)?\s+([A-Za-z0-9_]+)(?:\s+([A-Za-z0-9_+\-]+))?")


def check_text(mod, kind, text, chain=None, levels=()):
    """Problems of a line about to be written: a recruit line naming no unit, an
    upgrade to a level the chain has not, a requirement naming a building or a
    faction the mod has not. [(error?, message)]."""
    out = []
    s = strip_comment(text).strip()
    if not s:
        return [(True, "empty line")]
    if kind == "building":
        key = s.split()[0] if s.split() else ""
        if key in RECRUIT_KEYS:
            m = re.match(r'(\w+)\s+"([^"]+)"\s*(.*)$', s)
            nums = (m.group(3).split(" requires")[0].split() if m else [])
            pool = key.endswith("_pool")
            if not m:
                out.append((True, RECRUIT_FORMS[key]))
            else:
                units = unit_names(mod)
                if m.group(2) not in units:
                    close = [u for u in units if u.lower() == m.group(2).lower()]
                    out.append((True, "no unit '%s' in export_descr_unit.txt%s" % (
                        m.group(2), " (did you mean '%s'?)" % close[0] if close else "")))
                if len(nums) != (4 if pool else 1) or not all(_number(x) for x in nums):
                    out.append((True, RECRUIT_FORMS[key]))
                elif not nums[-1].isdigit():
                    out.append((True, "the experience (the last number before 'requires') must be a whole number (0-9)"))
        edb = mod.file("edb")
        chains = {}
        if edb:
            f = mod.load(edb)
            for c, a, b in building_blocks(f):
                chains[c] = [lv["name"] for lv in chain_tree(f, a, b)["levels"]]
        for m in RE_PRESENT.finditer(s):
            if m.group(1) not in chains:
                out.append((True, "no building chain '%s'" % m.group(1)))
            elif m.group(2) and "_min_level" in m.group(0) and m.group(2) not in chains[m.group(1)]:
                out.append((True, "%s has no level '%s'" % (m.group(1), m.group(2))))
    from .roster import factions_in
    names = factions_in(s)
    if names:
        known = {"all"} | {n for n, _ in mod.factions()} | {c for _, c in mod.factions() if c}
        bad = [n for n in names if n not in known]
        if bad:
            out.append((False, "not a faction or culture of this mod: %s" % ", ".join(bad)))
    return out


def unit_names(mod):
    edu = mod.file("edu")
    return [b[0] for b in unit_blocks(mod.load(edu))] if edu else []


# ---- what a rename drags along ----
def _unit_span(line):
    """(start, end) of the unit name in 'unit <name>[,] exp ...' lines (descr_strat,
    descr_mercenaries, descr_rebel_factions), or None."""
    m = re.match(r"^(\s*unit\s+)(.+?)(\s*,|\s+exp\s+\d|\s*;|\s*$)", line)
    return (m.end(1), m.end(2)) if m else None


def rename_unit(plan, old, new):
    """A unit's type renamed: its recruit lines, the armies in every campaign's
    descr_strat, the mercenary pools and the rebels' lists follow."""
    mod = plan.mod
    if new in unit_names(mod):
        raise ValueError("a unit '%s' exists already" % new)
    edb = mod.file("edb")
    if edb:
        e = plan.edit(edb)
        n = 0
        from .roster import recruit_of
        for i in range(len(e.raw)):
            t = e.text(i)
            if (recruit_of(t) or ("", ""))[1] == old:
                e.set(i, t.replace('"%s"' % old, '"%s"' % new, 1))
                n += 1
        if n:
            plan.note(e, "recruit lines follow the new name %s (%d)" % (new, n))
    files = [mod.campaign_file(c, "descr_strat.txt") for c in mod.campaigns()] + \
        [mod.campaign_file(c, "descr_mercenaries.txt") for c in mod.campaigns()] + \
        [os.path.join(mod.data, "descr_rebel_factions.txt")]
    seen = set()
    for p in files:
        if not p or not os.path.isfile(p) or p in seen:
            continue
        seen.add(p)
        f = plan.edit(p)
        n = 0
        for i in range(len(f.raw)):
            t = f.text(i)
            sp = _unit_span(t)
            if sp and t[sp[0]:sp[1]] == old:
                f.set(i, t[:sp[0]] + new + t[sp[1]:])
                n += 1
        if n:
            plan.note(f, "%d line(s) follow the unit's new name %s" % (n, new))


def rename_dictionary(plan, old, new):
    """A unit's dictionary renamed: its names and descriptions and its cards are
    copied under the new name (the old ones stay; nothing else reads them)."""
    mod = plan.mod
    copy_text_entries(plan, _text_file(mod, "export_units.txt"), {
        old: new, old + "_descr": new + "_descr", old + "_descr_short": new + "_descr_short"})
    from .moddata import _ci
    for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
        for fac, _ in mod.listing("ui/" + sub):                     # the mod's folders and the game's under it
            have = [d for d in mod.dirs("ui/%s/%s" % (sub, fac))]
            src = next((p for p in (_ci(d, pattern % old) for d in have) if p), None)
            if src and not any(_ci(d, pattern % new) for d in have):
                plan.copy(src, os.path.join(mod.data, "ui", sub, fac, pattern % new))


def rename_chain(plan, old, new):
    """A building chain renamed: the towns' buildings in every campaign's descr_strat
    and the requirements naming it (building_present...) follow."""
    mod = plan.mod
    e = plan.edit(mod.file("edb"))
    if any(b[0] == new for b in building_blocks(mod.load(mod.file("edb")))):   # the file as it is on disk
        raise ValueError("a building chain '%s' exists already" % new)
    rx = re.compile(r"(\bbuilding_present(?:_min_level)?\s+)%s\b" % re.escape(old))
    n = 0
    for i in range(len(e.raw)):
        t = e.text(i)
        if rx.search(t):
            e.set(i, rx.sub(lambda m: m.group(1) + new, t))
            n += 1
    if n:
        plan.note(e, "%d requirement(s) follow the chain's new name %s" % (n, new))
    for c in mod.campaigns():
        p = mod.campaign_file(c, "descr_strat.txt")
        if not p:
            continue
        f = plan.edit(p)
        k = 0
        for i in range(len(f.raw)):
            t = f.text(i)
            tk = tokens(t)
            if tk[:2] == ["type", old] and len(tk) > 2:
                f.set(i, re.sub(r"(\btype\s+)%s\b" % re.escape(old), lambda m: m.group(1) + new, t, count=1))
                k += 1
        if k:
            plan.note(f, "%d town building(s) follow the chain's new name %s" % (k, new))


# ---- how many lines of a key a place may hold ----
def _place_lines(f, kind, block, place=None, level=None):
    """The line numbers of one place: a unit block, or a building level's capability,
    upgrades or own lines."""
    name, a, b = block
    if kind == "unit":
        return range(a, b)
    lv = next((x for x in chain_tree(f, a, b)["levels"] if x["name"] == level), None)
    if lv is None:
        return []
    if place in ("capability", "upgrades"):
        return range(lv[place][0] + 1, lv[place][1]) if lv[place] else []
    inner = set()
    for p in ("capability", "upgrades"):
        if lv[p]:
            inner.update(range(lv[p][0] - 1, lv[p][1] + 1))
    return [i for i in range(lv["open"] + 1, lv["close"]) if i not in inner]


def _count(f, lines, upgrades=False):
    n = {}
    for i in lines:
        t = tokens(f.text(i))
        if t and t[0] not in ("{", "}"):
            k = "(level)" if upgrades else t[0]
            n[k] = n.get(k, 0) + 1
    return n


def line_limits(f, kind):
    """{place: {key: the most lines of that key one unit (one building level's place)
    of the mod has}} - which keys the mod uses and whether it repeats them (room_for).
    Places: None for units; 'capability', 'upgrades' (key '(level)'), 'level'."""
    out = {}

    def keep(place, counts):
        d = out.setdefault(place, {})
        for k, v in counts.items():
            d[k] = max(d.get(k, 0), v)
    if kind == "unit":
        for blk in unit_blocks(f):
            keep(None, _count(f, _place_lines(f, kind, blk)))
        return out
    for blk in building_blocks(f):
        for lv in chain_tree(f, blk[1], blk[2])["levels"]:
            for place in ("capability", "upgrades", "level"):
                keep(place, _count(f, _place_lines(f, kind, blk, place, lv["name"]), place == "upgrades"))
    return out


# How many lines of a key a place may get (the user, 2026-09-30: no cap of our own - "we removed it once already"):
# - a key the mod never uses there (and the engine does not know) is refused - most likely a typo;
# - a key that is one line wherever the mod has it (category, class, soldier, recruit_priority_offset...) stays one
#   line: a second one is a broken file, not more of the thing;
# - a key the mod repeats somewhere (officer, recruit lines, bonuses, upgrades) takes any number, except the
#   original exes' own caps below - and those only when no REX / M2EX runs the game (limits.lifted).
LIST_KEYS = {"recruit", "recruit_pool", "retrain", "retrain_pool"}       # repeatable even where the mod has one
GAME_CAPS = {("unit", "officer"): 3}      # TWC wiki Hardcoded Limits (RTW + M2TW): at most 3 officers


def room_for(f, kind, block, place, level, key, limits, pending=0, mod=None):
    """None when one more line of key fits in that place, else why not."""
    place_key = None if kind == "unit" else place
    k = "(level)" if place == "upgrades" else key
    most = (limits.get(place_key) or {}).get(k, 0)
    if kind == "unit":
        from .unitattrs import ENGINE_KEYS
        if k in ENGINE_KEYS:
            most = max(most, 1)
    repeatable = most >= 2 or k == "(level)" or (key in LIST_KEYS and most)
    have = _count(f, _place_lines(f, kind, block, place, level), place == "upgrades").get(k, 0) + pending
    if not most:
        return "no %s in this mod has a '%s' line%s - not a key this mod uses there" % (
            "unit" if kind == "unit" else "building level", k, "" if kind == "unit" else " in its %s" % place)
    if not repeatable:
        return "'%s' is one line only (every %s of the mod has at most one)" % (
            k, "unit" if kind == "unit" else "building level") if have >= 1 else None
    cap = GAME_CAPS.get((kind, k))
    if cap and have >= cap:
        from .limits import lifted
        if not (mod is not None and lifted(mod, "units")):
            return "the original game takes at most %d '%s' lines (REX / M2EX not found beside the game)" % (cap, k)
    return None


TEXT_PARTS = (("", "name"), ("_desc_short", "short description"), ("_desc", "description"))


def level_text_suffixes(mod, level):
    """The suffixes a building level's texts have in export_buildings.txt: '' (its plain texts) and every culture or
    faction it has a text of its own for ({<level>_<suffix>}, {..._desc}, {..._desc_short}) - both games."""
    path = _text_file(mod, "export_buildings.txt")
    out = {""}
    if not path:
        return [""]
    low = level.lower() + "_"
    for t in mod.load(path).texts():
        s = t.lstrip()
        if not (s.startswith("{") and "}" in s):
            continue
        k = s[1:s.index("}")].lower()
        if not k.startswith(low):
            continue
        rest = k[len(low):]
        for end in ("_desc_short", "_desc"):
            if rest.endswith(end):
                rest = rest[:-len(end)]
                break
        if rest in ("desc", "desc_short"):
            continue
        out.add(rest)
    return sorted(out)


# Texts the games keep for a level a culture never builds (the plain key): shown as stand-ins, never as real texts
STAND_INS = ("DO NOT TRANSLATE", "should never appear on screen")


def level_names(mod, level):
    """[(suffix, name)] of a building level in export_buildings.txt: its own name and
    the names for a culture or a faction ({<level>_<culture or faction>}, e.g. Shrine to
    Ares for greek) - the game shows the one for the faction, else its culture, else
    the plain one."""
    path = _text_file(mod, "export_buildings.txt")
    if not path:
        return []
    out = []
    low = level.lower()
    for t in mod.load(path).texts():
        s = t.lstrip()
        if not (s.startswith("{") and "}" in s):
            continue
        key = s[1:s.index("}")]
        k = key.lower()
        if k == low or (k.startswith(low + "_") and not k.endswith("_desc") and not k.endswith("_desc_short")):
            suffix = key[len(level) + 1:] or "(plain)"
            name = s[s.index("}") + 1:].strip()
            if name and "_" not in suffix.strip("()"):
                out.append((suffix, name))
    return out
