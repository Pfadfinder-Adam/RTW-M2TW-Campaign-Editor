"""descr_strat.txt: faction blocks, settlements, characters, diplomacy."""

import re

from .textio import strip_comment, tokens

RE_XY = re.compile(r"\bx\s+(-?\d+)\s*,\s*y\s+(-?\d+)")


def _head(line):
    t = tokens(line)
    return t[0] if t else ""


class Settlement:
    def __init__(self, start, end, region, owner):
        self.start, self.end = start, end          # line range [start, end)
        self.region = region
        self.owner = owner
        # the town's own garrison, no captain: 'garrisoned_army' + its 'unit' lines inside the block (both games'
        # engines read it - a tester's Medieval II map held 900 towns so; Rome: 'must add at least one unit to the
        # garrison army of %s'). garrison_at = the garrisoned_army line or None; garrison_units = its unit lines
        self.garrison_at, self.garrison_units, self.garrison, self.garrison_end = None, [], [], None


def unit_of(line):
    """'unit   Town Militia   exp 0 armour 0 weapon_lvl 0' -> 'Town Militia'."""
    body = strip_comment(line).strip()[len("unit"):].strip()
    return re.split(r"\s+exp\s+\d+", body)[0].strip()


def garrison_lines(lines, start, end):
    """(index of a settlement block's 'garrisoned_army' line, [indexes of the unit lines after it], the index after
    the last of them) or (None, [], None). A repeated 'garrisoned_army' line (a tester's map has one) belongs to it."""
    for k in range(start, end):
        if tokens(lines[k])[:1] == ["garrisoned_army"]:
            units, j, last = [], k + 1, k
            while j < end:
                t = tokens(lines[j])
                if t and t[0] not in ("unit", "garrisoned_army"):
                    break
                if t:
                    last = j
                    if t[0] == "unit":
                        units.append(j)
                j += 1
            return k, units, last + 1
    return None, [], None


class Character:
    def __init__(self, start, end, line, owner):
        self.start, self.end = start, end
        self.line = line
        self.owner = owner
        m = RE_XY.search(line)
        self.xy = (int(m.group(1)), int(m.group(2))) if m else None
        body = strip_comment(line).strip()
        body = body[len("character"):].lstrip(", \t")
        parts = [p.strip() for p in body.split(",")]
        self.sub_faction = None
        if parts and parts[0].startswith("sub_faction"):
            self.sub_faction = parts[0].split()[1] if len(parts[0].split()) > 1 else None
            parts = parts[1:]
        self.name = parts[0] if parts else ""
        self.kind = parts[1] if len(parts) > 1 else ""
        self.role = next((p for p in parts[2:4] if p in ("leader", "heir")), None)

    @property
    def named(self):
        return self.kind == "named character"


# forts and watchtowers: 'fort 263 330 cerin_amroth_fort culture middle_eastern permanent name Cerin Amroth'
# (Medieval II; REX adds 'permanent' and 'name ...'), Rome also 'fort x, y'
# forts / watchtowers (both games) and Rome's wonders: `landmark pharos 178, 21` (the type between)
RE_FORT = re.compile(r"^\s*(fort|watchtower|landmark)\s+(?:([A-Za-z_]\w*)\s+)?(-?\d+)\s*,?\s*(-?\d+)(.*)$")


class Fort:
    def __init__(self, i, line, owner):
        m = RE_FORT.match(strip_comment(line))
        self.line, self.text, self.owner = i, line, owner
        self.kind = m.group(1)
        self.type = m.group(2) or ""                     # a landmark's type (descr_sm_landmarks.txt)
        self.xy = (int(m.group(3)), int(m.group(4)))
        rest = m.group(5).split()
        self.permanent = "permanent" in rest
        self.name = " ".join(rest[rest.index("name") + 1:]).strip('"') if "name" in rest else ""


# the lines that open the diplomacy section: Rome core_attitudes, Medieval II faction_standings
DIPLOMACY_HEADS = ("core_attitudes", "faction_standings", "faction_relationships")


class FactionBlock:
    def __init__(self, name, start, end, header):
        self.name, self.start, self.end, self.header = name, start, end, header
        self.settlements = []
        self.characters = []


class Strat:
    """An index over a loaded descr_strat.txt TextFile. Rebuild it after editing."""

    def __init__(self, f):
        self.f = f
        lines = f.texts()
        self.lines = lines
        self.playable = self._list("playable")
        self.unlockable = self._list("unlockable")
        self.nonplayable = self._list("nonplayable")
        self.diplomacy_start = next((i for i, l in enumerate(lines)
                                     if _head(l) in DIPLOMACY_HEADS), len(lines))
        # the block of the last faction stops at the comment banner before the diplomacy section
        stop = self.diplomacy_start
        while stop > 0 and (lines[stop - 1].strip() == "" or lines[stop - 1].lstrip().startswith(";")):
            stop -= 1
        starts = [(i, tokens(l)) for i, l in enumerate(lines[:self.diplomacy_start])
                  if _head(l) == "faction"]
        self.factions = []
        for n, (i, t) in enumerate(starts):
            end = starts[n + 1][0] if n + 1 < len(starts) else stop
            # a faction's banner comments belong to the next block
            e = end
            while e > i + 1 and (lines[e - 1].strip() == "" or lines[e - 1].lstrip().startswith(";")):
                e -= 1
            fb = FactionBlock(t[1], i, e, lines[i])
            self._scan_block(fb)
            self.factions.append(fb)
        # forts / watchtowers anywhere in the file: a faction's block, the top, or after the diplomacy (Barbarian
        # Invasion lists its 53 watchtowers under the regions there)
        owner_at = {}
        for fb in self.factions:
            for k in range(fb.start, fb.end):
                owner_at[k] = fb.name
        self.forts = [Fort(i, l, owner_at.get(i)) for i, l in enumerate(lines)
                      if RE_FORT.match(strip_comment(l))]

    def _list(self, key):
        for i, l in enumerate(self.lines):
            if _head(l) == key:
                out = []
                j = i + 1
                while j < len(self.lines) and _head(self.lines[j]) != "end":
                    t = tokens(self.lines[j])
                    if t:
                        out.append((j, t[0]))
                    j += 1
                return {"start": i, "end": j, "items": out}
        return None

    def _scan_block(self, fb):
        lines = self.lines
        i = fb.start + 1
        marks = []
        while i < fb.end:
            h = _head(lines[i])
            if h == "settlement":
                depth, j, seen = 0, i, False
                while j < fb.end:
                    s = strip_comment(lines[j])
                    depth += s.count("{") - s.count("}")
                    seen = seen or "{" in s
                    j += 1
                    if seen and depth == 0:
                        break
                region = None
                for k in range(i, j):
                    t = tokens(lines[k])
                    if len(t) >= 2 and t[0] == "region":
                        region = t[1]
                        break
                st = Settlement(i, j, region, fb.name)
                st.garrison_at, st.garrison_units, st.garrison_end = garrison_lines(lines, i, j)
                st.garrison = [unit_of(lines[k]) for k in st.garrison_units]
                fb.settlements.append(st)
                i = j
                continue
            if h in ("character", "character_record", "relative", "fort", "watchtower"):
                marks.append((i, h))                    # a fort line ends the character before it
            i += 1
        for n, (i, h) in enumerate(marks):
            if h != "character":
                continue
            end = marks[n + 1][0] if n + 1 < len(marks) else fb.end
            # stop before settlements that follow, and leave trailing comments to the next one
            for s in fb.settlements:
                if i < s.start < end:
                    end = s.start
            while end > i + 1 and (lines[end - 1].strip() == "" or lines[end - 1].lstrip().startswith(";")):
                end -= 1
            fb.characters.append(Character(i, end, lines[i], fb.name))

    # ---- queries ----
    def faction(self, name):
        return next((fb for fb in self.factions if fb.name == name), None)

    def settlement_of(self, region):
        for fb in self.factions:
            for s in fb.settlements:
                if s.region == region:
                    return s
        return None

    def owners(self):
        """{region: owner} for every settlement in the file."""
        return {s.region: fb.name for fb in self.factions for s in fb.settlements}

    def taken_tiles(self):
        """Tiles someone stands on at the start: every character, fort and watchtower."""
        return {c.xy for fb in self.factions for c in fb.characters if c.xy} | {x.xy for x in self.forts}

    def characters_at(self, xy):
        return [c for fb in self.factions for c in fb.characters if c.xy == xy]

    def diplomacy_lines(self):
        """[(index, kind, a, value, b)] for core_attitudes / faction_standings / faction_relationships lines."""
        out = []
        for i in range(self.diplomacy_start, len(self.lines)):
            t = tokens(self.lines[i])
            if len(t) >= 4 and t[0] in ("core_attitudes", "faction_standings", "faction_relationships"):
                out.append((i, t[0], t[1], t[2], t[3:]))
        return out


# The faction block's header lines in the order the games read them (every vanilla descr_strat.txt of both games:
# faction, superfaction / ai_label, dead_until_resurrected, re_emergent, denari, denari_kings_purse, then the towns);
# out of order the game drops the faction's towns at the start ('Faction Destroyed' on turn 1 - the editor's own
# test mod, 2026-10-03)
HEADER_RANK = {"superfaction": 0, "ai_label": 0, "dead_until_resurrected": 1, "re_emergent": 2, "denari": 3,
               "denari_kings_purse": 4}


def header_rank(text):
    t = tokens(strip_comment(text))
    return HEADER_RANK.get(t[0], 0) if t else 0


def ordered_header(lines):
    """The header lines (text, after the 'faction' line) in the games' order; lines of one rank keep theirs."""
    return [x for _, _, x in sorted((header_rank(x), i, x) for i, x in enumerate(lines))]


HEADER_STOP = ("settlement", "character", "character_record", "relative", "army", "navy", "fleet")


def headers_out_of_order(f):
    """[(faction, [line numbers of its header lines])] of the faction blocks of a descr_strat.txt (TextFile) whose
    header lines are not in the games' order (ordered_header puts them right)."""
    out = []
    for fb in Strat(f).factions:
        idx = []
        for i in range(fb.start + 1, fb.end):
            t = tokens(strip_comment(f.text(i)))
            if not t:
                continue
            if t[0] in HEADER_STOP or t[0].startswith("{"):
                break
            idx.append(i)
        ranks = [header_rank(f.text(i)) for i in idx]
        if ranks != sorted(ranks):
            out.append((fb.name, idx))
    return out


def characters_after_tree(s):
    """Factions whose block has a character line after its character_record /
    relative lines - the game crashes on that (a hard-won rule)."""
    bad = []
    for fb in s.factions:
        tree = False
        for l in s.lines[fb.start:fb.end]:
            w = l.split(None, 1)[:1]
            if w in (["character_record"], ["relative"]):
                tree = True
            elif tree and w == ["character"]:
                bad.append(fb.name)
                break
    return bad


def faction_names(s, faction):
    """Every name a faction's block gives its characters and family records, as written
    (first name and surname) - the game wants each once per faction."""
    fb = s.faction(faction)
    out = []
    for l in (s.lines[fb.start:fb.end] if fb else []):
        body = strip_comment(l).strip()
        head = body.split(None, 1)[:1]
        if head not in (["character"], ["character_record"]):
            continue
        parts = [p.strip() for p in body[len(head[0]):].strip().split(",")]
        if parts and parts[0].startswith("sub_faction"):
            parts = parts[1:]
        if parts and parts[0]:
            out.append(parts[0])
    return out


def duplicate_names(s):
    """[(faction, name)] for a name used twice in one faction's block: the game skips the
    second one ("duplicated character name in this faction, skipping", REX world.cpp(987))."""
    out = []
    for fb in s.factions:
        seen = set()
        for n in faction_names(s, fb.name):
            if n in seen and (fb.name, n) not in out:
                out.append((fb.name, n))
            seen.add(n)
    return out


def check_names(before, after):
    """Raise ValueError for a name a write would give twice to one faction (names already twice in the
    file before stay the mod's own business)."""
    old = set(duplicate_names(before)) if before is not None else set()
    new = [d for d in duplicate_names(after) if d not in old]
    if new:
        raise ValueError("two characters of %s would be called %s - the game skips the second one "
                         "(\"duplicated character name in this faction\"). Pick another name; nothing written."
                         % (new[0][0], new[0][1]))


def medieval(lines):
    """Whether a descr_strat's character lines name the sex (Medieval II:
    'character Name, general, male, age 30, x 1, y 2'); Rome's do not
    ('character Name, general, age 30, , x 1, y 2')."""
    if hasattr(lines, "raw"):                       # a TextFile: read up to the first character only
        tf = lines
        lines = (tf.text(i) for i in range(len(tf.raw)))
    for l in lines:
        t = strip_comment(l)
        if t.lstrip().startswith("character") and not t.lstrip().startswith("character_record"):
            parts = [p.strip() for p in t.split(",")]
            return "male" in parts or "female" in parts
    return False


FEMALE_KINDS = ("princess", "witch")


def first_names(pool, kind):
    """The descr_names list a character of this kind takes its first name from:
    'women' for a princess or witch, 'characters' (the men's) for everyone else."""
    # a first name of two words (Medieval II's egyptian 'al Adil') cannot start a character line: the game
    # reads 'al' as the first name and 'Adil' as the surname - such names serve as surnames only
    return [n for n in (pool or {}).get("women" if kind in FEMALE_KINDS else "characters", []) if " " not in n.strip()]


def character_line(lines, name, kind, age, xy, role=None, female=None, sub_faction=None):
    """A character line in the file's own dialect (see medieval). kind: general,
    named character, spy, princess...; role: leader / heir or None; sub_faction: a rebel's
    ('character\tsub_faction britons, Brigomaglos, general, ...' - every rebel in vanilla has one)."""
    extra = ", %s" % role if role else ""
    sub = "sub_faction %s, " % sub_faction if sub_faction else ""
    if medieval(lines):
        sex = "female" if (female if female is not None else kind in FEMALE_KINDS) else "male"
        return "character\t%s%s, %s, %s%s, age %d, x %d, y %d" % (sub, name, kind, sex, extra, int(age), xy[0], xy[1])
    return "character\t%s%s, %s%s, age %d, , x %d, y %d" % (sub, name, kind, extra, int(age), xy[0], xy[1])


def rebel_look(s, xy, mod=None, campaign=None):
    """The sub_faction a new rebel character at xy takes: the nearest rebel's (vanilla picks them by the
    land around: greek_cities over the Aegean, britons in Britain), else the region's creator, else the
    first faction. A rebel's name comes from that faction's name list (all 91 vanilla rebels, Rome and
    Medieval II), not from the slave list."""
    fb = s.faction("slave")
    near = [(abs(c.xy[0] - xy[0]) + abs(c.xy[1] - xy[1]), c.sub_faction) for c in (fb.characters if fb else [])
            if c.xy and c.sub_faction]
    if near:
        return min(near)[1]
    if mod is not None and campaign:
        img = mod.region_map(campaign)
        regions = mod.regions(campaign)
        colour = img.get(*xy) if 0 <= xy[0] < img.width and 0 <= xy[1] < img.height else None
        region = next((r for r, v in regions.items() if v.get("colour") == colour), None) or next(
            (r for r, t in mod.city_tiles(campaign).items() if t == tuple(xy)), None)
        creator = (regions.get(region) or {}).get("creator")
        if creator and creator != "slave":
            return creator
    return next((x.name for x in s.factions if x.name != "slave"), None)


def village_block(region, faction):
    """A settlement block for a region descr_strat leaves out. The game makes
    such a region a rebel village with no buildings; taking it means writing
    that village into the new owner's block."""
    return ["settlement", "{", "\tlevel village", "\tregion %s" % region, "",
            "\tyear_founded 0", "\tpopulation 400", "\tplan_set default_set",
            "\tfaction_creator %s" % faction, "}"]
