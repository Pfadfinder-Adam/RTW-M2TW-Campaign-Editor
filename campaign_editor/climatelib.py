"""A climate's passport: everything one climate gives the game, gathered from every file that names it (the climate
library, Terrain > Climates).

A climate is not one switch: map_climates.tga picks it by colour (descr_climates.txt), and each file that knows
climates finds its own block or line by the climate's NAME - the trees and the ground textures of the campaign map,
the mountains' textures, the vegetation, ground, grass and water of the battle map, the weather, the sounds, the
trees in towns, the disasters, the name players read. The battle files may name a climate by its engine slot name
instead (the slot = its place in descr_climates.txt's 'climates' list; Rome's slot 0 is 'default', Medieval II's
'mediterranean'; with REX / M2EX 32 slots, the last 20 'custom_1' .. 'custom_20' - engine source geography.cpp,
editor-notes strat_map_render.md), so both names are looked for.

Nothing here writes: rows only say what stands where (file and line), the mod's own or the game's under it."""

import os
import re

# the engine's slot names (geography.cpp climate_type_strings): Rome, Medieval II; then custom_1 .. custom_20
_SLOTS_ROME = ("default", "sandy_desert", "rocky_desert", "temperate_grassland_fertile",
               "temperate_grassland_infertile", "temperate_forest_open", "temperate_forest_deep", "swamp", "highland",
               "alpine", "sub_arctic", "semi_arid")
_SLOTS_M2 = ("mediterranean", "sandy_desert", "rocky_desert", "unused1", "steppe", "temperate_deciduous_forest",
             "temperate_coniferous_forest", "unused2", "highland", "alpine", "tropical", "semi_arid")
CUSTOM = tuple("custom_%d" % i for i in range(1, 21))
SLOTS = 32

# (section, file under data/) - the order the passport shows them in
FILES = (
    ("Campaign map", "descr_climates.txt"),
    ("Campaign map", "descr_aerial_map_ground_types.txt"),
    ("Battle map", "descr_geography.txt"),
    ("Battle map", "descr_geography_new.txt"),
    ("Battle map", "descr_ground_type_db.txt"),
    ("Battle map", "descr_landscape_ground_types.txt"),
    ("Battle map", "descr_terrain_generation.txt"),
    ("Battle map", "descr_vegetation.txt"),
    ("Battle map", "descr_grass.txt"),
    ("Battle map", "descr_water.txt"),
    ("Battle map", "descr_water_types.txt"),
    ("Battle map", "descr_battlefield_roads.xml"),
    ("Battle map", "descr_settlement_plan.txt"),
    ("Battle map", "custom_locations.txt"),
    ("Weather and sounds", "descr_daytypes.txt"),
    ("Weather and sounds", "descr_daytypes_ex.txt"),
    ("Weather and sounds", "weather_db.xml"),
    ("Weather and sounds", "descr_sounds_enviro.txt"),
    ("Weather and sounds", "descr_sounds_stratmap.txt"),
    ("Weather and sounds", "descr_sounds.txt"),
    ("Weather and sounds", "descr_landscape_ambient_settlements.txt"),
    ("Other", "world/maps/base/descr_disasters.txt"),
    ("Other", "text/climates.txt"),
    ("Other", "descr_climates_lookup.txt"),
)
SECTIONS = ("Campaign map", "Mountains and hills", "Battle map", "Weather and sounds", "Other")

# descr_aerial_map_ground_types.txt's slots: the campaign map's ground texture by ground type
GROUND_SLOTS = ("cultivated_low", "cultivated_medium", "cultivated_high", "fertility_low", "fertility_medium",
                "fertility_high", "forest_dense", "forest_sparse", "hills", "mountains_high", "mountains_low", "swamp",
                "beach", "scorched", "impassable_land", "impassable_sea", "impassable_shrouded")


class Row:
    """One thing a climate gives: section, what (the slot or the block it sits in), value (the line's words), file
    (path under data/), line (1 = the first), own (the mod's own file, not the game's), picture (a file under data/
    to show, or None), note (e.g. 'from default')."""
    __slots__ = ("section", "what", "value", "file", "line", "own", "picture", "note")

    def __init__(self, section, what, value, file, line, own, picture=None, note=""):
        self.section, self.what, self.value, self.file, self.line = section, what, value, file, line
        self.own, self.picture, self.note = own, picture, note

    def __repr__(self):
        return "Row(%r, %r, %r, %s:%d)" % (self.section, self.what, self.value, self.file, self.line)


def _strip(line):
    i = line.find(";")
    return (line if i < 0 else line[:i]).strip()


def _word(name):
    return re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])", re.I)


def listed(lines):
    """[names] of descr_climates.txt's 'climates { }' list, in order (each name's place = its engine slot)."""
    out, state = [], 0
    for line in lines:
        t = _strip(line).split()
        if not t:
            continue
        if state == 0 and t[0] == "climates":
            state = 1 if t[-1] != "{" else 2
        elif state == 1 and t[0] == "{":
            state = 2
        elif state == 2:
            if t[0] == "}":
                break
            out.append(t[0])
    return out


def slot_name(index, game):
    """The engine's own name of slot index ('medieval2' or 'rome'), or None past the 32."""
    own = _SLOTS_M2 if game == "medieval2" else _SLOTS_ROME
    if 0 <= index < len(own):
        return own[index]
    if 0 <= index - len(own) < len(CUSTOM):
        return CUSTOM[index - len(own)]
    return None


def free_slots(lines, game):
    """[(slot index, engine name)] still free with REX / M2EX: the slots past descr_climates.txt's list, up to 32."""
    n = len(listed(lines))
    return [(i, slot_name(i, game)) for i in range(n, SLOTS)]


def _own_header(text, alias):
    """True when a block header names alias as its own (not after 'modifies' / 'parent': 'x modifies default' is
    x's block, not default's)."""
    words = []
    for w in text.rstrip("{").split():
        if w.lower() in ("modifies", "parent"):
            break
        words.append(w.lower())
    return alias.lower() in words


def _context(lines, i, reach=400):
    """The header of the block line i sits in (its nearest unclosed '{' looking up), or ''."""
    depth = 0
    for k in range(i - 1, max(-1, i - reach), -1):
        v = _strip(lines[k])
        depth += v.count("}") - v.count("{")
        if depth < 0:
            head = v.rstrip("{").strip()
            m = k - 1
            while not head and m >= 0 and m > k - 5:
                head, m = _strip(lines[m]), m - 1
            return head
    # no braces: the nearest line above set further left (descr_daytypes' 'daytype x', the sound files' events)
    ind = _indent(lines[i])
    for k in range(i - 1, max(-1, i - 60), -1):
        v = _strip(lines[k])
        if v and _indent(lines[k]) < ind:
            return v
    return ""


def _indent(line):
    n = 0
    for ch in line:
        if ch == " ":
            n += 1
        elif ch == "\t":
            n += 4
        else:
            break
    return n


def scan(lines, names, aliases=()):
    """[(line index, header, value)] for every place lines name one of names (whole words, any case): inside a
    block whose header names it, each line of the block (header = the header's words); an XML element <x id="name">
    up to its end tag likewise; a block that only builds on it ('x modifies name') by its header line alone (header
    'built on it'); anywhere else, the line itself (header = the block it sits in, or ''). aliases: other names counted only as a
    block's own header (the engine's slot name - Rome's slot 0 is 'default', a word many lines use)."""
    pats = [_word(n) for n in names if n]
    apats = [_word(a) for a in aliases if a]
    out, i, n = [], 0, len(lines)
    while i < n:
        raw = lines[i]
        text = raw.strip() if raw.lstrip().startswith("<") else _strip(raw)
        named = text and any(p.search(text) for p in pats)
        alias = not named and text and any(p.search(text) for p in apats)
        if not named and not alias:
            i += 1
            continue
        xml = re.match(r"<\s*(\w+)\b[^>]*\bid\s*=\s*\"([^\"]*)\"", text)
        if alias and not (xml and xml.group(2).lower() in [a.lower() for a in aliases]):
            if xml or not any(_own_header(text, a) for a in aliases):
                i += 1
                continue
        if xml and not text.endswith("/>"):
            tag, end = xml.group(1), re.compile(r"</\s*" + re.escape(xml.group(1)) + r"\s*>")
            j = i + 1
            while j < n and not end.search(lines[j]):
                v = lines[j].strip()
                if v and not v.startswith("<!--"):
                    out.append((j, '<%s id="%s">' % (tag, xml.group(2)), v))
                j += 1
            i = j + 1
            continue
        # a block: '{' at the end of the header or on the next words-bearing line
        j = i + 1
        opened = text.endswith("{")
        if not opened:
            while j < n and not _strip(lines[j]):
                j += 1
            opened = j < n and _strip(lines[j]).split()[:1] == ["{"]     # not a text file's next {TAG}
            j += 1
        if opened:
            header = text.rstrip("{").strip()
            mine = any(_own_header(text, x) for x in list(names) + list(aliases))
            if not mine:                                # 'x modifies name': x builds on it - its header line only
                out.append((i, "built on it", header))
            depth = 1
            k = j
            while k < n and depth > 0:
                v = _strip(lines[k])
                depth += v.count("{") - v.count("}")
                if mine and depth > 0 and v and v not in ("{", "}"):
                    out.append((k, header, v))
                k += 1
            i = k
            continue
        if not alias:
            out.append((i, _context(lines, i), text))
        i += 1
    return out


class _Reader:
    """The files a passport reads: the mod's own first, the game's under it (ModData.find)."""

    def __init__(self, mod):
        self.mod = mod
        self._lines = {}

    def lines(self, rel):
        if rel not in self._lines:
            p = self.mod.find(rel)
            got = None
            if p:
                try:
                    got = (self.mod.load(p).texts(), self._own(p))
                except (OSError, UnicodeDecodeError):
                    got = None
            self._lines[rel] = got
        return self._lines[rel]

    def _own(self, path):
        return os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(self.mod.data)))


def climates_block(lines, name):
    """{'colour', 'heat', 'winter', 'trees': [(season, kind, file, cell, line)], 'battle': [(key, value, winter,
    line)], 'env_map', 'line'} of descr_climates.txt's block 'climate name', or None."""
    out = None
    depth, opened, battle_winter = 0, False, None
    for i, raw in enumerate(lines):
        t = _strip(raw).split()
        if not t:
            continue
        if out is None:
            if t[:2] == ["climate", name] and len(t) <= 3:
                out = {"colour": None, "heat": None, "winter": False, "trees": [], "battle": [], "env_map": None,
                       "line": i}
            continue
        v = " ".join(t)
        depth += v.count("{") - v.count("}")
        opened = opened or depth > 0
        if opened and depth <= 0:
            break
        if t[0] == "colour" and len(t) >= 4:
            out["colour"] = tuple(int(v) for v in t[1:4] if v.isdigit())[:3]
        elif t[0] == "heat" and len(t) >= 2:
            out["heat"] = t[1]
        elif t[0] == "winter":
            out["winter"] = True
        elif t[0] == "strategy" and len(t) >= 4:
            out["trees"].append((t[1], t[2], t[3], t[4] if len(t) > 4 else "", i))
        elif t[0] in ("battle_vegetation", "battle_winter_vegetation"):
            battle_winter = t[0] == "battle_winter_vegetation"
        elif t[0] == "env_map" and len(t) >= 2:
            out["env_map"] = (t[1], i)
        elif battle_winter is not None and len(t) >= 2 and t[0] not in ("{", "}"):
            out["battle"].append((t[0], t[1], battle_winter, i))
    return out


def aerial_blocks(lines):
    """{climate: {slot: (summer, winter or None, line)}} of descr_aerial_map_ground_types.txt (its 'default' too)."""
    out, cur = {}, None
    for i, raw in enumerate(lines):
        t = _strip(raw).split()
        if not t:
            continue
        if t[0] == "climate" and len(t) > 1:
            cur = out.setdefault(t[1], {})
        elif cur is not None and len(t) >= 2 and t[0] not in ("{", "}"):
            cur[t[0]] = (t[1], t[2] if len(t) > 2 else None, i)
    return out


def passport(mod, name, game=None):
    """[Row] - everything climate name gives, file by file (FILES), the mod's own files first, the game's under
    them. game: 'medieval2' | 'rome' (limits.game_kind; None = looked up)."""
    if game is None:
        from .limits import game_kind
        game = game_kind(mod)
    rd = _Reader(mod)
    rows = []
    got = rd.lines("descr_climates.txt")
    order = listed(got[0]) if got else []
    names, aliases = [name], []
    if name in order:
        other = slot_name(order.index(name), game)
        if other and other != name and other != "default":     # 'default' is every file's base block, not this
            aliases.append(other)                                # climate's own (Rome's slot 0)
    for section, rel in FILES:
        found = rd.lines(rel)
        if not found:
            continue
        lines, own = found
        if rel == "descr_climates.txt":
            rows += _climate_rows(lines, own, name, order, game)
        elif rel == "descr_aerial_map_ground_types.txt":
            rows += _aerial_rows(lines, own, names + aliases)
        else:
            for i, header, value in scan(lines, names, aliases):
                rows.append(Row(section, header or "(a line)", value, rel, i + 1, own,
                                _picture_of(value) if section == "Battle map" else None))
    rows += _tile_texture_rows(mod, names + aliases)
    return rows


def _climate_rows(lines, own, name, order, game):
    b = climates_block(lines, name)
    rel, sec = "descr_climates.txt", "Campaign map"
    if b is None:
        return [Row(sec, "climate", "no block 'climate %s' - the game has no colour, trees or heat for it" % name,
                    rel, 1, own)]
    out = []
    if name in order:
        i = order.index(name)
        out.append(Row(sec, "slot", "%d of %d (engine name %s)" % (i + 1, SLOTS, slot_name(i, game) or "-"), rel,
                       b["line"] + 1, own))
    else:
        out.append(Row(sec, "slot", "not in the 'climates' list - the game does not use this block", rel,
                       b["line"] + 1, own))
    out.append(Row(sec, "colour", " ".join(str(v) for v in b["colour"]) if b["colour"] else "-", rel, b["line"] + 1,
                   own))
    out.append(Row(sec, "heat", "%s (1 cool .. 4 hot: armour tires in battle)" % (b["heat"] or "-"), rel,
                   b["line"] + 1, own))
    out.append(Row(sec, "winter", "snow in winter" if b["winter"] else "no winter look", rel, b["line"] + 1, own))
    for season, kind, f, cell, i in b["trees"]:
        out.append(Row(sec, "trees %s %s" % (season, kind.replace("_", " ")), "%s (sprite %s)" % (f, cell or "-"),
                       rel, i + 1, own, "terrain/aerial_map/tree_models/" + f))
    for key, value, winter, i in b["battle"]:
        out.append(Row("Battle map", ("winter " if winter else "") + key.replace("_", " "), value, rel, i + 1, own))
    if b["env_map"]:
        out.append(Row("Battle map", "sky reflection (env_map)", b["env_map"][0], rel, b["env_map"][1] + 1, own,
                       b["env_map"][0][5:] if b["env_map"][0].lower().startswith("data/") else b["env_map"][0]))
    return out


def _aerial_rows(lines, own, names):
    from .terrain import ground_file
    blocks = aerial_blocks(lines)
    rel, sec = "descr_aerial_map_ground_types.txt", "Campaign map"
    mine = next((blocks[n] for n in names if n in blocks), None)
    default = blocks.get("default", {})
    out = []
    for slot in GROUND_SLOTS:
        entry, note = (mine or {}).get(slot), ""
        if entry is None:
            entry, note = default.get(slot), "from default"
        if entry is None:
            continue
        summer, winter, i = entry
        out.append(Row(sec, "ground " + slot.replace("_", " "), summer + ("  /  winter " + winter if winter else ""),
                       rel, i + 1, own, ground_file(summer), note))
    return out


def _tile_texture_rows(mod, names):
    """The mountains' and hills' own textures in tile_textures/<climate>/summer|winter/ (the game takes the
    climate's page first)."""
    out, seen = [], set()
    for n in names:
        for season in ("summer", "winter"):
            rel = "terrain/aerial_map/tile_textures/%s/%s" % (n, season)
            for d in mod.dirs(rel):
                own = os.path.normcase(os.path.abspath(d)).startswith(os.path.normcase(os.path.abspath(mod.data)))
                for f in sorted(os.listdir(d)):
                    if f.lower() in seen or not os.path.isfile(os.path.join(d, f)):
                        continue
                    seen.add(f.lower())
                    out.append(Row("Mountains and hills", season, f, rel + "/" + f, 0, own, rel + "/" + f))
    return out


def _picture_of(value):
    """A picture path named in a battle line (terrain/battlefield/..., data/...), else None."""
    for w in value.split():
        lw = w.lower()
        if lw.endswith((".tga", ".dds", ".texture")):
            return w[5:] if lw.startswith("data/") else w
    return None


def coverage(mod, campaign):
    """{climate colour: tiles} of the campaign's map_climates.tga (each tile's middle point)."""
    from collections import Counter
    img = mod._optional_map(campaign, "map_climates.tga")
    out = Counter()
    if img is None:
        return out
    for y in range(1, img.height, 2):
        for x in range(1, img.width, 2):
            out[img.get(x, y)] += 1
    return out


__all__ = ["Row", "passport", "scan", "listed", "slot_name", "free_slots", "climates_block", "aerial_blocks",
           "coverage", "FILES", "SECTIONS", "GROUND_SLOTS", "SLOTS", "CUSTOM"]
