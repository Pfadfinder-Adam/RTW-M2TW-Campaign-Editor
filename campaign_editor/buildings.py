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
        self.kind = None                          # Medieval II: 'city' or 'castle' (the word after the name)
        self.convert_to = None                    # the level of the chain's convert_to it becomes

    def factions(self):
        """Every faction / culture named in the level's factions lists (REX may have several), or None."""
        from .roster import factions_in
        return factions_in(self.requires)

    def conditional(self):
        """Requirements beyond the faction list (resources, other buildings...)."""
        rest = re.sub(r"(?<![A-Za-z0-9_])factions\s*\{[^}]*\}", "", self.requires).strip()
        return rest.lstrip("and").strip()


class Building:
    def __init__(self, name):
        self.name = name
        self.levels = []
        self.classification = ""
        self.convert_to = None                    # Medieval II: the chain a castle's becomes in a city and back

    def level(self, name):
        return next((l for l in self.levels if l.name == name), None)


def is_temple(chain):
    """A temple chain as the games see it: its name starts with 'temple_' (RomeTW.exe, RomeTW-BI.exe and
    medieval2.exe test that prefix). A town holds ONE temple: a second is refused when built and in descr_strat.txt
    stops the game ('Settlement specified with multiple temple buildings'); modders who want more name the chain
    without 'temple'."""
    return chain.lower().startswith("temple_")


def other_temple(chains, chain):
    """The town's temple chain other than `chain` (chains: names it holds), or None - only when chain is a temple."""
    if not is_temple(chain):
        return None
    return next((c for c in chains if c != chain and is_temple(c)), None)


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
            elif t[0] == "convert_to" and depth == 1 and len(t) > 1:
                cur.convert_to = t[1]
            elif t[0] in names and depth == 2:
                req = code.split("requires", 1)[1] if "requires" in code else ""
                pending = Level(t[0], req)
                if len(t) > 1 and t[1] in ("city", "castle"):
                    pending.kind = t[1]
                cur.levels.append(pending)
            elif pending is not None and depth == 3:
                if t[0] == "convert_to" and len(t) > 1 and t[1].isdigit():
                    pending.convert_to = int(t[1])
                elif t[0] == "settlement_min" and len(t) > 1:
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
    template it copies) build it. 'all' in the list lets everyone in (a modder's
    'factions { all, }')."""
    fs = level.factions()
    if fs is None or "all" in fs:
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
POP_MIN = {"village": 400, "town": 400, "large_town": 2000, "city": 6000, "large_city": 12000, "huge_city": 24000}


# the population each level holds (min, max): the game stops reading descr_strat.txt at a town outside it ("Population
# of 2600 is too high for a village - max is 1500" - and the towns, armies and diplomacy after it are lost). Read from
# descr_settlement_mechanics.xml <population_levels> when the mod or the game has it (M2TW, REX), else vanilla.
POP_RANGE = {"village": (400, 1500), "town": (400, 3500), "large_town": (400, 9000), "city": (400, 18000),
             "large_city": (400, 36000), "huge_city": (400, 72000)}
# Medieval II castles use the city level words in descr_strat.txt but hold their own (motte and bailey = village...)
CASTLE_OF = {"village": "moot_and_bailey", "town": "wooden_castle", "large_town": "castle", "city": "fortress",
             "large_city": "citadel"}
CASTLE_RANGE = {"moot_and_bailey": (400, 1500), "wooden_castle": (400, 3500), "castle": (400, 9000),
                "fortress": (400, 13500), "citadel": (400, 18000)}


def population_levels(mod):
    """{level: (min, max)} of descr_settlement_mechanics.xml (the mod's, else the game's), or {} without one."""
    import os
    from .moddata import _ci
    if mod is None:
        return {}
    roots = [mod.data]
    try:
        from .newmod import game_of
        game = game_of(mod.data)
        if game:
            roots.append(os.path.join(game, "data"))
    except Exception:
        pass
    for root in roots:
        p = _ci(root, "descr_settlement_mechanics.xml") if os.path.isdir(root) else None
        if not p:
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        out = {}
        for m in re.finditer(r"<level\b([^>]*)/?>", text):
            a = dict(re.findall(r'(\w+)\s*=\s*"([^"]*)"', m.group(1)))
            try:
                if a.get("name") and "max" in a:
                    out[a["name"].lower()] = (int(a.get("min", 0) or 0), int(a["max"]))
            except ValueError:
                pass
        if out:
            return out
    return {}


def pop_range(level, castle=False, mod=None):
    """(min, max) population a settlement of this level holds (castle: a Medieval II castle), or None unknown."""
    level = (level or "").lower()
    key = CASTLE_OF.get(level, level) if castle else level
    got = population_levels(mod).get(key)
    if got:
        return got
    return (CASTLE_RANGE if castle else POP_RANGE).get(key) or POP_RANGE.get(level)


def pop_problem(population, level, castle=False, mod=None):
    """The game's own words when the population does not fit the level, else None."""
    r = pop_range(level, castle, mod)
    if r is None or population is None:
        return None
    what = CASTLE_OF.get(level, level) if castle else level
    if population > r[1]:
        return "Population of %d is too high for a %s - max is %d" % (population, what.replace("_", " "), r[1])
    if population < r[0]:
        return "Population of %d is too low for a %s - min is %d" % (population, what.replace("_", " "), r[0])
    return None


def level_for_population(population, castle=False, mod=None):
    """The smallest settlement level whose range holds the population (the town grows to fit), or None (above every
    level: the top level is the nearest)."""
    for level in SETTLEMENT_LEVELS:
        r = pop_range(level, castle, mod)
        if castle and level not in CASTLE_OF:
            continue
        if r and r[0] <= population <= r[1]:
            return level
    return None


def fit_population(plan, f, region, population, level, castle=False):
    """population moved into the level's range (min, max) with a warning in the game's words - a town outside it
    makes the game stop reading descr_strat.txt there."""
    why = pop_problem(population, level, castle, plan.mod if plan is not None else None)
    if not why:
        return population
    lo, hi = pop_range(level, castle, plan.mod if plan is not None else None)
    fitted = min(max(population, lo), hi)
    if plan is not None:
        plan.warn(f, "%s: %s (the game would stop reading descr_strat.txt there) - written as %d" % (
            region, why, fitted))
    return fitted


def population_of(lines):
    for l in lines:
        t = tokens(l)
        if t[:1] == ["population"] and len(t) > 1:
            try:
                return int(t[1])
            except ValueError:
                return None
    return None


def core_offset(b):
    """How far below the settlement level core chain b's level stands. Towns and cities: one
    ("The core building level should be one less than the settlement level!" - fatal on load;
    the chain's first level is a town's, a village has none). Medieval II castles
    (core_castle_building): none ("The castle core building level should be EQUAL the
    settlement level!": motte_and_bailey = village, wooden_castle = town, castle = large_town...)."""
    return 0 if "castle" in b.name.lower() else 1


def core_settlement(b, name):
    """The settlement level a governor's building (a level of a core chain) stands in.
    settlement_min is only where the level may be built (it grows the town)."""
    names = [l.name for l in b.levels]
    if name not in names:
        return None
    return SETTLEMENT_LEVELS[min(names.index(name) + core_offset(b), len(SETTLEMENT_LEVELS) - 1)]


def core_level_for(b, settlement_level):
    """The level of core chain b a settlement of this level has; None when it has none."""
    i = rank(settlement_level) - core_offset(b)
    return b.levels[i] if 0 <= i < len(b.levels) and rank(settlement_level) >= 0 else None


def core_need(picked, known):
    """The settlement level the picked governor's building belongs to, or None."""
    for chain, name in picked:
        b = known.get(chain)
        if b and chain.lower().startswith("core") and b.level(name):
            return core_settlement(b, name)
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
            out[i] = make(re.sub(r"(level\s+)\S+", r"\g<1>" + level, l.rstrip("\r\n"), count=1))
        elif depth == 1 and t[:1] == ["population"] and population is not None:
            out[i] = make(re.sub(r"(population\s+)\S+", r"\g<1>%d" % population, l.rstrip("\r\n"), count=1))
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
    if (size or {}).get("level_follows") and want_pop is not None and not want:
        # the level grows (or shrinks) to hold the people, the governor's building with it (a tester's wish)
        fits = level_for_population(want_pop, settlement_kind(texts) == "castle", plan.mod)
        if fits and fits != level and pop_problem(want_pop, level, settlement_kind(texts) == "castle", plan.mod):
            want = fits
    need = core_need(picked or [], known)
    new = want or level
    if need and need != new:
        if want:
            plan.warn(f, "%s: the governor's building belongs to a %s, the level is set to %s - the game "
                         "refuses to load that" % (region, need, want))
        else:
            new = need
            plan.note(f, "%s: %s -> %s for its governor's building" % (region, level, new))
    elif picked and not need and rank(new) > 0 and any(c.lower().startswith("core") for c in known):
        plan.warn(f, "%s: a %s with no governor's building" % (region, new))
    if want and want != level:
        plan.note(f, "%s: level %s -> %s" % (region, level, want))
    if want_pop is None and new != level and pop is not None and pop < POP_MIN.get(new, 0):
        want_pop = POP_MIN[new]
    castle = settlement_kind(texts) == "castle"
    if want_pop is not None:
        want_pop = fit_population(plan, f, region, want_pop, new, castle)
    elif new != level and pop is not None and pop_problem(pop, new, castle, plan.mod):
        want_pop = min(max(pop, pop_range(new, castle, plan.mod)[0]), pop_range(new, castle, plan.mod)[1])
    if want_pop is not None and want_pop != pop:
        plan.note(f, "%s: population %s -> %d" % (region, pop, want_pop))
    if new == level and want_pop in (None, pop):
        return raw, level
    return resize(raw, f.make, new if new != level else None, want_pop), new


# ---------------------------------------------------------------------------
# Medieval II: a settlement is a city or a castle
# ---------------------------------------------------------------------------
KINDS = ("city", "castle")


def settlement_kind(lines):
    """'castle' for a `settlement castle` block, else 'city'."""
    for l in lines:
        t = tokens(l)
        if t[:1] == ["settlement"]:
            return "castle" if t[1:2] == ["castle"] else "city"
    return "city"


def has_castles(known):
    """Whether the mod's buildings know castles (Medieval II); Rome has none."""
    return any(l.kind == "castle" for b in known.values() for l in b.levels)


def castles_allowed(mod, known):
    """Whether settlements may be switched between city and castle: only Medieval II (its exe, else its data -
    religions) AND its buildings mark castle levels. Rome, Barbarian Invasion and Alexander have no castles."""
    from .limits import game_kind
    return game_kind(mod) == "medieval2" and has_castles(known)


def core_chain(known, kind):
    """The governor's chain of a city or of a castle (core_building / core_castle_building); Rome's levels say
    neither, its one core chain is the city's."""
    cores = [b for n, b in known.items() if n.lower().startswith("core") and b.levels]
    got = next((b for b in cores if any(l.kind == kind for l in b.levels)), None)
    if got is None and kind != "castle":            # Rome: one core chain, its levels marked neither city nor castle
        got = next((b for b in cores if all(l.kind is None for l in b.levels) and "castle" not in b.name.lower()),
                   None)
    return got


def kind_problem(known, kind, level):
    """Why a settlement of this level cannot be that kind, or None."""
    core = core_chain(known, kind)
    if kind == "castle" and core is None:
        return "this game has no castles (no castle core building in export_descr_buildings.txt)"
    if core is not None and kind == "castle" and rank(level) >= len(core.levels) + core_offset(core):
        top = SETTLEMENT_LEVELS[len(core.levels) - 1 + core_offset(core)]
        return "a %s cannot be a castle - castles go up to %s (%s)" % (level, top, core.levels[-1].name)
    return None


def convert(items, kind, known, level, fit_core=True):
    """The buildings as the game converts them when the settlement becomes that kind: a level marked for the
    other kind becomes level `convert_to` of its chain's `convert_to` chain, or goes (none given). The governor's
    building then fits the settlement level (a castle's = the level, a city's one below; a village city has none).
    Returns (items, [(old, new or None)])."""
    out, changes = [], []
    for chain, name in items:
        b = known.get(chain)
        lv = b.level(name) if b else None
        if lv is None or lv.kind in (None, kind):
            out.append((chain, name))
            continue
        to = known.get(b.convert_to) if b.convert_to else None
        if to is not None and lv.convert_to is not None and 0 <= lv.convert_to < len(to.levels):
            new = (to.name, to.levels[lv.convert_to].name)
            out.append(new)
            changes.append(((chain, name), new))
        else:
            changes.append(((chain, name), None))
    core = core_chain(known, kind) if fit_core else None
    if core is not None:
        want = core_level_for(core, level)
        have = [x for x in out if x[0].lower().startswith("core")]
        rest = [x for x in out if not x[0].lower().startswith("core")]
        if want is not None and have != [(core.name, want.name)]:
            changes += [(h, (core.name, want.name)) for h in have] or [(None, (core.name, want.name))]
            out = [(core.name, want.name)] + rest
        elif want is None and have:
            changes += [(h, None) for h in have]
            out = rest
    return out, changes


def set_kind(raw, kind, make):
    """The settlement block's raw lines with its header `settlement` / `settlement castle`."""
    out = list(raw)
    for i, l in enumerate(out):
        t = tokens(l)
        if t[:1] == ["settlement"]:
            code = strip_comment(l.rstrip("\r\n"))
            rest = l.rstrip("\r\n")[len(code):]
            lead = code[:len(code) - len(code.lstrip())]
            out[i] = make(lead + ("settlement castle" if kind == "castle" else "settlement") + rest)
            break
    return out


def with_kind(plan, f, region, raw, kind, picked, known, size=None):
    """(raw, picked) with the settlement made a city or a castle: the header, and the buildings converted the
    game's way. Buildings picked in the window were converted and fitted there already (their governor's
    building belongs to the level they set): only a wrong-kind level left among them is converted. Without
    picks the block's own buildings are converted and the governor's building fitted to the settlement's level
    (the one set by hand, else the file's). Refused where the game has no such settlement."""
    texts = [l.rstrip("\r") for l in raw]
    level, own = settlement_info(texts)
    level = (size or {}).get("level") or level
    now = settlement_kind(texts)
    if kind not in KINDS or kind == now:
        return raw, picked
    if not castles_allowed(plan.mod, known):
        raise ValueError("%s: only Medieval II has castles - this game has cities only" % region)
    bad = kind_problem(known, kind, level)
    if bad:
        raise ValueError("%s: %s" % (region, bad))
    items, changes = convert(list(picked) if picked is not None else own, kind, known, level,
                             fit_core=picked is None)
    plan.note(f, "%s: %s -> %s (settlement%s)" % (region, now, kind, " castle" if kind == "castle" else ""))
    for old, new in changes:
        if old and new:
            plan.note(f, "%s: %s %s becomes %s %s" % (region, old[0], old[1], new[0], new[1]))
        elif old and old[0].lower().startswith("core"):
            plan.note(f, "%s: %s %s goes (a %s village has no governor's building)" % (region, old[0], old[1], kind))
        elif old:
            plan.note(f, "%s: %s %s goes (a %s has no such building)" % (region, old[0], old[1], kind))
        elif new:
            plan.note(f, "%s: governor's building %s %s" % (region, new[0], new[1]))
    return set_kind(raw, kind, f.make), items


def castle_fits(plan, region, raw, level, known):
    """A castle (Medieval II) bigger than castles go is refused before anything is written."""
    if settlement_kind([l.rstrip("\r") for l in raw]) == "castle" and castles_allowed(plan.mod, known):
        bad = kind_problem(known, "castle", level)
        if bad:
            raise ValueError("%s: %s - make it a city (Buildings tab: Settlement is a city)" % (region, bad))


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
    """Finds the picture the game would show for a building level: the culture's own
    folder, then the cultures descr_ui_buildings.txt sends it to (lookup_variants), in the
    mod and then in the game's data (Barbarian Invasion and REX mods read what they lack
    there). Never another culture's picture: a Roman town must not show barbarian huts."""

    def __init__(self, mod):
        self.ui = os.path.join(mod.data, "ui")
        folders = [mod.data]
        game = _game_data(mod.data)
        if game:
            folders.append(game)
        self.index = {}                        # culture folder -> {lower file name: path}, the mod's first
        for data in folders:
            ui = _ci(data, "ui")
            if not ui or not os.path.isdir(ui):
                continue
            for c in os.listdir(ui):
                b = _ci(os.path.join(ui, c), "buildings")
                if b and os.path.isdir(b):
                    files = self.index.setdefault(c.lower(), {})
                    for n in os.listdir(b):
                        files.setdefault(n.lower(), os.path.join(b, n))
        self.variants, self.aliases = {}, {}
        path = next((p for p in (_ci(d, "descr_ui_buildings.txt") for d in folders) if p), None)
        if path:
            for l in mod.load(path).texts():
                t = tokens(l)
                if len(t) == 2:
                    if t[0] in self.index or t[1] in self.index:
                        self.variants.setdefault(t[0], []).append(t[1])
                    else:
                        self.aliases[t[0]] = t[1]

    def cultures(self, culture):
        """The culture, then the ones descr_ui_buildings.txt sends it to - nothing else."""
        order, todo = [], [culture]
        while todo:
            c = todo.pop(0)
            if c and c not in order:
                order.append(c)
                todo += self.variants.get(c, [])
        return order

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
        for c in self.cultures(culture):              # the culture's own picture beats a variant's
            files = self.index.get(c, {})
            for name in self.names(level):
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


def _game_data(data):
    """The game's own data folder when data is a mod's or Barbarian Invasion's (None for the game's)."""
    from .newmod import game_of
    game = game_of(data)
    d = _ci(game, "data") if game else None
    if d and os.path.normcase(os.path.abspath(d)) != os.path.normcase(os.path.abspath(data)):
        return d
    return None
