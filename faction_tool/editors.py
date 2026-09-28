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
