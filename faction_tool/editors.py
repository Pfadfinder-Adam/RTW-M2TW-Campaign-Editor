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
    resized to size (width, height) if given."""
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    if size and im.size != tuple(size):
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
    folder = os.path.join(mod.data, "ui", "unit_info" if info else "units")
    return sample_size(folder, "_info.tga" if info else ".tga") if os.path.isdir(folder) else None


def building_picture_target(mod, culture, level, constructed=False):
    """ui/<culture>/buildings/#<culture>_<level>[_constructed].tga."""
    return os.path.join(mod.data, "ui", culture, "buildings",
                        "#%s_%s%s.tga" % (culture, level, "_constructed" if constructed else ""))


def building_picture_need(mod, culture, constructed=False):
    folder = os.path.join(mod.data, "ui", culture, "buildings")
    if not os.path.isdir(folder):
        folder = os.path.join(mod.data, "ui")
    end = "_constructed.tga" if constructed else ".tga"
    return sample_size(folder, end) if os.path.isdir(folder) else None


def import_picture(plan, src, targets, size=None):
    """The picture src written to every target path (a TGA in the given size)."""
    data = tga_bytes(src, size)
    for t in targets:
        plan.binary(t, data)
        plan.notes.append((plan.mod.rel(t), "picture from %s%s" % (
            os.path.basename(src), " (%d x %d)" % tuple(size) if size else "")))


# ---------------------------------------------------------------------------
# New units and buildings, copied from one there is
# ---------------------------------------------------------------------------
def _text_file(mod, name):
    from .moddata import _ci
    return _ci(os.path.join(mod.data, "text"), name)


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


def copy_unit(plan, src_type, new_type, new_dict, recruit=True):
    """A new unit: the block of src_type copied after it under new_type and new_dict,
    its names and descriptions (export_units.txt) and cards copied to the new
    dictionary name, and - with recruit - a recruit line next to each of the old
    unit's in export_descr_buildings.txt."""
    import shutil  # noqa: F401  (copies go through the plan)
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
            folder = os.path.join(mod.data, "ui", sub)
            if not os.path.isdir(folder):
                continue
            for fac in sorted(os.listdir(folder)):
                from .moddata import _ci
                srcp = _ci(os.path.join(folder, fac), pattern % old_dict) if os.path.isdir(
                    os.path.join(folder, fac)) else None
                if srcp:
                    plan.copy(srcp, os.path.join(folder, fac, pattern % new_dict))
    if recruit and mod.file("edb"):
        e = plan.edit(mod.file("edb"))
        n, i = 0, 0
        q = '"%s"' % src_type
        while i < len(e.raw):
            text = e.text(i)
            if tokens(text)[:1] == ["recruit"] and q in text:
                e.insert(i + 1, [text.replace(q, '"%s"' % new_type, 1)])
                n += 1
                i += 2
                continue
            i += 1
        if n:
            plan.note(e, "%s recruited where %s is (%d line(s))" % (new_type, src_type, n))


def copy_building(plan, src_chain, new_chain, level_names):
    """A new building chain: src_chain's block copied under new_chain with its levels
    renamed by level_names {old: new} (in 'levels', their own blocks and 'upgrades'),
    their names and descriptions (export_buildings.txt, every key made of a level name)
    and pictures (ui/<culture>/buildings/#<culture>_<level>[_constructed].tga)."""
    import re
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
    words = dict(level_names)
    words[src_chain] = new_chain

    def swap(text):
        return re.sub(r"\b[A-Za-z0-9_]+\b", lambda m: words.get(m.group(0), m.group(0)), text)
    lines = []
    for i in range(src[1], src[2]):
        text = f.text(i)
        code = strip_comment(text).strip()
        head = code.split()[:1]
        if head in (["building"], ["levels"], ["upgrades"]) or (head and head[0] in level_names) or \
                (lines and strip_comment(lines[-1]).strip().split()[:1] == ["upgrades"]) or \
                (head and all(w in level_names for w in code.split())):
            lines.append(swap(text))
        else:
            lines.append(text)
    f.insert(src[2], [""] + lines)
    plan.note(f, "building %s copied from %s: levels %s" % (
        new_chain, src_chain, ", ".join("%s -> %s" % kv for kv in level_names.items())))
    path = _text_file(mod, "export_buildings.txt")
    if path:
        keys = {}
        for s in mod.load(path).texts():
            s = s.lstrip()
            if s.startswith("{") and "}" in s:
                k = s[1:s.index("}")]
                for old, new in level_names.items():
                    if k.lower() == old.lower() or k.lower().startswith(old.lower() + "_"):
                        keys[k] = new + k[len(old):]
        copy_text_entries(plan, path, keys)
    ui = os.path.join(mod.data, "ui")
    if os.path.isdir(ui):
        for cult in sorted(os.listdir(ui)):
            folder = os.path.join(ui, cult, "buildings")
            if not os.path.isdir(folder):
                continue
            names = {n.lower(): n for n in os.listdir(folder)}
            for old, new in level_names.items():
                for tail in (".tga", "_constructed.tga"):
                    n = names.get(("#%s_%s%s" % (cult, old, tail)).lower())
                    if n:
                        plan.copy(os.path.join(folder, n), os.path.join(folder, "#%s_%s%s" % (cult, new, tail)))
