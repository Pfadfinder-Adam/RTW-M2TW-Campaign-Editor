"""Buildings: export_descr_buildings.txt, the buildings in a settlement block of
descr_strat.txt, and the pictures the game shows for each level."""

import os
import re

from .moddata import _ci
from .textio import strip_comment, tokens

SETTLEMENT_LEVELS = ("village", "town", "large_town", "city", "large_city", "huge_city")


class Level:
    def __init__(self, name, requires):
        self.name = name
        self.requires = requires.strip()          # the text after 'requires', or ''
        self.settlement_min = "village"
        self.cost = 0
        self.turns = 0

    def factions(self):
        m = re.search(r"(?<![A-Za-z0-9_])factions\s*\{([^}]*)\}", self.requires)
        return [x.strip() for x in m.group(1).replace(",", " ").split()] if m else None

    def conditional(self):
        """Requirements beyond the faction list (resources, other buildings...)."""
        rest = re.sub(r"(?<![A-Za-z0-9_])factions\s*\{[^}]*\}", "", self.requires).strip()
        return rest.lstrip("and").strip()


class Building:
    def __init__(self, name):
        self.name = name
        self.levels = []
        self.classification = ""

    def level(self, name):
        return next((l for l in self.levels if l.name == name), None)


def read_buildings(edb):
    """[Building] from a loaded export_descr_buildings TextFile."""
    out, cur, names, pending = [], None, [], None
    depth = 0
    for l in edb.texts():
        code = strip_comment(l)
        t = tokens(l)
        if t[:1] == ["building"] and depth == 0 and len(t) > 1:
            cur = Building(t[1])
            out.append(cur)
            names = []
        elif cur is not None and t:
            if t[0] == "classification" and len(t) > 1:
                cur.classification = t[1]
            elif t[0] == "levels" and depth == 1:
                names = t[1:]
            elif t[0] in names and depth == 2:
                req = code.split("requires", 1)[1] if "requires" in code else ""
                pending = Level(t[0], req)
                cur.levels.append(pending)
            elif pending is not None and depth == 3:
                if t[0] == "settlement_min" and len(t) > 1:
                    pending.settlement_min = t[1]
                elif t[0] == "cost" and len(t) > 1 and t[1].isdigit():
                    pending.cost = int(t[1])
                elif t[0] == "construction" and len(t) > 1 and t[1].isdigit():
                    pending.turns = int(t[1])
        depth += code.count("{") - code.count("}")
        if depth <= 0:
            depth = 0
            cur = cur if code.count("}") == 0 else None
    return out


def available(level, faction, culture, template=None):
    """Whether a level's faction list lets this faction (or its culture, or the
    template it copies) build it."""
    fs = level.factions()
    if fs is None:
        return True
    return any(x in fs for x in (faction, culture, template) if x)


def ranks_ok(level, settlement_level):
    try:
        return SETTLEMENT_LEVELS.index(level.settlement_min) <= SETTLEMENT_LEVELS.index(settlement_level)
    except ValueError:
        return True


# ---------------------------------------------------------------------------
# A settlement block in descr_strat.txt
# ---------------------------------------------------------------------------
def settlement_info(lines):
    """(settlement level, [(chain, level)]) of a settlement block's lines."""
    level, found, inside = "town", [], False
    for l in lines:
        t = tokens(l)
        if t[:1] == ["level"] and len(t) > 1 and not inside:
            level = t[1]
        elif t[:1] == ["building"]:
            inside = True
        elif inside and t[:1] == ["type"] and len(t) > 2:
            found.append((t[1], t[2]))
            inside = False
    return level, found


# the population at which the game grows a settlement to each level (vanilla)
POP_MIN = {"village": 0, "town": 400, "large_town": 2000, "city": 6000, "large_city": 12000, "huge_city": 24000}


def population_of(lines):
    for l in lines:
        t = tokens(l)
        if t[:1] == ["population"] and len(t) > 1:
            try:
                return int(t[1])
            except ValueError:
                return None
    return None


def core_need(picked, known):
    """The settlement level the picked governor's building needs (the core
    building chain's settlement_min), or None."""
    for chain, name in picked:
        b = known.get(chain)
        lv = b.level(name) if b else None
        if lv and chain.lower().startswith("core"):
            return lv.settlement_min
    return None


def rank(level):
    return SETTLEMENT_LEVELS.index(level) if level in SETTLEMENT_LEVELS else -1


def resize(raw, make, level=None, population=None):
    """The settlement block's raw lines with its own 'level' / 'population' lines
    set (not those inside building entries)."""
    out, depth = list(raw), 0
    for i, l in enumerate(out):
        code = strip_comment(l)
        t = tokens(l)
        if depth == 1 and t[:1] == ["level"] and level:
            out[i] = make(re.sub(r"(level\s+)\S+", r"\g<1>" + level, l.rstrip("\r\n"), 1))
        elif depth == 1 and t[:1] == ["population"] and population is not None:
            out[i] = make(re.sub(r"(population\s+)\S+", r"\g<1>%d" % population, l.rstrip("\r\n"), 1))
        depth += code.count("{") - code.count("}")
    return out


def sized(plan, f, region, raw, picked, size, known):
    """raw with the settlement level and population from size = {'level',
    'population'} (either may be missing); without a level set by hand, a
    governor's building that needs a bigger settlement raises the level, and
    the population rises to that level's threshold."""
    texts = [l.rstrip("\r") for l in raw]
    level, _ = settlement_info(texts)
    pop = population_of(texts)
    want, want_pop = (size or {}).get("level"), (size or {}).get("population")
    need = core_need(picked or [], known)
    new = want or level
    if need and rank(need) > rank(new):
        if want:
            plan.warn(f, "%s: the governor's building needs a %s, the level is set to %s" % (region, need, want))
        else:
            new = need
            plan.note(f, "%s: %s -> %s for its governor's building" % (region, level, new))
    if want and want != level:
        plan.note(f, "%s: level %s -> %s" % (region, level, want))
    if want_pop is None and new != level and pop is not None and pop < POP_MIN.get(new, 0):
        want_pop = POP_MIN[new]
    if want_pop is not None and want_pop != pop:
        plan.note(f, "%s: population %s -> %d" % (region, pop, want_pop))
    if new == level and want_pop in (None, pop):
        return raw, level
    return resize(raw, f.make, new if new != level else None, want_pop), new


def set_buildings(raw, buildings, make):
    """The settlement block's raw lines with its building { } entries replaced."""
    out, i = [], 0
    while i < len(raw):
        if tokens(raw[i])[:1] == ["building"]:
            depth, seen = 0, False
            while i < len(raw):
                code = strip_comment(raw[i])
                depth += code.count("{") - code.count("}")
                seen = seen or "{" in code
                i += 1
                if seen and depth == 0:
                    break
            continue
        out.append(raw[i])
        i += 1
    close = max(j for j, l in enumerate(out) if "}" in strip_comment(l))
    new = []
    for chain, level in buildings:
        new += [make("\tbuilding"), make("\t{"), make("\t\ttype %s %s" % (chain, level)), make("\t}")]
    return out[:close] + new + out[close:]


# ---------------------------------------------------------------------------
# Pictures: ui/<culture>/buildings/#<culture>_<level>.tga, with fallbacks
# ---------------------------------------------------------------------------
class BuildingPictures:
    """Finds the picture the game would show for a building level."""

    def __init__(self, mod):
        self.ui = os.path.join(mod.data, "ui")
        self.index = {}                        # culture folder -> {lower file name: path}
        if os.path.isdir(self.ui):
            for c in os.listdir(self.ui):
                b = _ci(os.path.join(self.ui, c), "buildings")
                if b and os.path.isdir(b):
                    self.index[c.lower()] = {n.lower(): os.path.join(b, n) for n in os.listdir(b)}
        self.variants, self.aliases = {}, {}
        path = _ci(mod.data, "descr_ui_buildings.txt")
        if path:
            for l in mod.load(path).texts():
                t = tokens(l)
                if len(t) == 2:
                    if t[0] in self.index or t[1] in self.index:
                        self.variants.setdefault(t[0], []).append(t[1])
                    else:
                        self.aliases[t[0]] = t[1]

    def cultures(self, culture):
        order, todo = [], [culture]
        while todo:
            c = todo.pop(0)
            if c and c not in order:
                order.append(c)
                todo += self.variants.get(c, [])
        return order + sorted(c for c in self.index if c not in order)

    def names(self, level):
        """The level, its alias from descr_ui_buildings, then with prefixes dropped
        (african_muster_field -> muster_field)."""
        out = [level]
        if level in self.aliases:
            out.append(self.aliases[level])
        parts = level.split("_")
        out += ["_".join(parts[i:]) for i in range(1, len(parts))]
        return out

    def find(self, culture, level, constructed=False):
        tail = "_constructed.tga" if constructed else ".tga"
        for name in self.names(level):
            for c in self.cultures(culture):
                files = self.index.get(c, {})
                p = files.get(("#%s_%s%s" % (c, name, tail)).lower())
                if p:
                    return p
                # a folder may hold another culture's prefix (celtic/#barbarian_...)
                end = ("_%s%s" % (name, tail)).lower()
                hit = next((v for k, v in files.items() if k.startswith("#") and k.endswith(end)
                            and "_" not in k[1:-len(end)]), None)
                if hit:
                    return hit
        return None
