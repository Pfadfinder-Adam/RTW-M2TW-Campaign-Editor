"""How many factions the game takes, and raising it where the engine lets us.

The original exes stop at a fixed number (slave included): Rome 21, Medieval II 31. REX and M2EX read
`max_factions` from data/descr_ex.txt ("Maximum number of factions (default in M2: 31, RTW: 21) /
Increase to support more factions in mods") - the mod's own copy only (see ex_file). Over the limit the game
closes at start: "Too many factions described here, maximum is(21).
The rest will be ignored" (REX faction_db.cpp(564), the user's nabataea, 2026-09-29)."""

import os
import re

from .moddata import _ci
from .textio import strip_comment

DEFAULTS = {"rome": 21, "medieval2": 31}
ENGINES = ("REX.exe", "M2EX.exe")               # the engines that read max_factions and let it be raised


class LimitError(ValueError):
    """A new faction over the limit. can_raise: the engine reads max_factions, so the tool may raise it."""

    def __init__(self, msg, limit):
        super().__init__(msg)
        self.limit = limit
        self.can_raise = bool(limit.get("engine"))


def game_kind(mod):
    """'medieval2' or 'rome': by the game's exe, else by the data (only Medieval II has religions)."""
    from .newmod import game_of, is_medieval2
    try:
        if is_medieval2(game_of(mod.data)):
            return "medieval2"
    except Exception:
        pass
    return "medieval2" if mod.find("descr_religions.txt") else "rome"


def _setting(path, key="max_factions"):
    """(line index, value) of a number setting in a descr_ex.txt, or (None, None)."""
    from .textio import TextFile
    f = TextFile.load(path)
    for i in range(len(f)):
        m = re.match(r"^\s*%s\s+(\d+)\s*$" % re.escape(key), strip_comment(f.text(i)))
        if m:
            return i, int(m.group(1))
    return None, None


# REX's descr_ex.txt: "Max ancillaries a single character can hold (default 8)", "Max children a
# character can have (default 4)" - the original Rome's fixed numbers. Medieval II keeps 8 ancillaries;
# its children follow descr_campaign_db, so the tool does not count them there.
# The original exes' hard limits modders found (
# heavengames "A List of Known Hardcodes", TWC "Hardcoded Limits - M2TW"). REX / M2EX lift some of them
# (HLR runs 750 regions under REX), so with an engine beside the data they are notes, not faults.
# Not here: heavengames' "20 landmasses" - vanilla RTW's own map has 32 separate pieces of land and runs,
# so what the game counts is not known.
HARD_LIMITS = {
    "rome": {"regions": 200, "map_size": 510, "units": 500, "chains": 64, "levels": 9, "hidden_resources": 64},
    "medieval2": {"regions": 200, "map_size": 510, "units": 500, "chains": 128, "levels": 9,
                  "hidden_resources": 64},
}
# What REX / M2EX do with them (one engine, two builds - the same notes). Sources: REX's README "Removed every single
# major engine limit like factions, regions, religions, cultures etc.", its release notes (08/06 cultures and
# religions uncapped; 18/04 maps past 32768), the EB II / M2EX thread on TWC ("no faction, religion, region, unit,
# cultures, model etc. limits"), HLR's 750 regions under REX. Factions stay a number of their own (max_factions).
# Not named anywhere: building chains, levels, hidden resources - those keep the original's number as a note.
# Since 2026-10-22 (limits.md THE RULE) a key is here ONLY when the engine source shows it lifted; lifted() lifts
# nothing else (officers 3, rebel unit types 20, army 20 / 40 stay - the source keeps them).
_LIFTS = {
    "regions": "lifted by REX / M2EX (engine source: REGION_ID int32, region arrays grow - world_map.h)",
    "map_size": "lifted by REX / M2EX (engine source: map coordinates int16, about 32767 - strategy_map_common.h)",
    "units": "lifted by REX / M2EX (engine source: the unit table grows past CA's 500 - env/database.h)",
    "religions": "lifted by REX / M2EX (engine source: 'No cap to enforce' - romans.cpp)",
    "chains": "lifted by REX / M2EX (engine source: building chains in a growing array - building_db.h)",
    "levels": "lifted by REX / M2EX (engine source: levels read without a limit - building_db.cpp)",
    "hidden_resources": "lifted by REX / M2EX (engine source: the list grows, regions keep a bit field of any size)",
}
ENGINE_LIFTS = {"REX.exe": dict(_LIFTS), "M2EX.exe": dict(_LIFTS)}
# The original exes' fixed numbers the tool refuses beyond when no REX / M2EX runs the game.
MAX_RELIGIONS = 9
LIMIT_WORDS = {"regions": "regions (the sea counts as one)", "map_size": "map_regions.tga width / height",
"units": "units in export_descr_unit.txt",
               "chains": "building chains", "levels": "levels in one building chain",
               "hidden_resources": "hidden resources (export_descr_buildings.txt)"}

FAMILY_DEFAULTS = {"max_num_ancillaries": 8, "max_num_children": 4, "age_of_manhood": 16}


def manhood_age(mod):
    """The age a boy comes of age - the oldest a living man off the map (a record) may be. A setting, not a fixed
    number: Rome + REX read `age_of_manhood` in descr_ex.txt, Medieval II `<age_of_manhood uint="N"/>` in
    descr_campaign_db.xml (the mod's copy, else the game's); vanilla and the defaults say 16."""
    return family_age(mod, "age_of_manhood")


FAMILY_AGES = {"age_of_manhood": 16, "daughters_age_of_consent": 12}


def family_age(mod, key):
    """A family tree age setting (`age_of_manhood`, `daughters_age_of_consent`) as the engine reads it: Rome + REX
    from descr_ex.txt (engine source descr_ex.cpp, defaults 16 / 12; the original RomeTW.exe has them fixed at the
    same), Medieval II from descr_campaign_db.xml's family_tree block (campaign_db.cpp, the mod's copy, else the
    game's) - vanilla Medieval II's own file says 16 for both, not 12."""
    import re
    from .newmod import game_of
    default = FAMILY_AGES[key]
    if game_kind(mod) != "medieval2":
        p = ex_file(mod, "descr_ex.txt")
        value = _setting(p, key)[1] if p else None
        return default if value is None else value
    game = game_of(mod.data)
    for folder in (mod.data, _ci(game, "data") if game else None):
        p = _ci(folder, "descr_campaign_db.xml") if folder else None
        if p:
            with open(p, encoding="latin-1") as fh:
                m = re.search(r"<%s\s+(?:uint|int|float)=\"(\d+)" % key, fh.read())
            return int(m.group(1)) if m else default
    return default


def ex_file(mod, name):
    """The engine's own settings file (descr_ex.txt, descr_caps_ex.txt, ...) the engine reads for this mod: the
    mod's own copy, else None - the engine's built-in defaults. A mod never takes the game's data copy: both
    engines' descr_caps_ex.txt say "Mods that don't ship this file get safe defaults" (each option marked "default
    for mods"), REX ships separate copies for bi/ and alexander/, M2EX one in each Kingdoms mod, and modders
    (Klerski, 2026-10-01) found the same. For the game's own data the mod's copy is that copy.
    descr_ex.txt is different (engine source, 2026-10-22): it is read through the file overlay, the mod's copy, else
    the GAME's data/descr_ex.txt (descr_ex.cpp + romans_cmd_line.cpp setup_path_make); only descr_caps_ex.txt skips
    the overlay on purpose (descr_caps_ex.cpp caps_ex_path: 'a mod that doesn't ship it should get compiled-in
    defaults, not vanilla's settings')."""
    own = _ci(mod.data, name)
    if own or name.lower() == "descr_caps_ex.txt":
        return own
    return game_ex_file(mod, name)


def game_ex_file(mod, name="descr_ex.txt"):
    """The game's own data/<name> under a mod (its fallback through the engine's file overlay), or None."""
    from .newmod import game_of
    game = game_of(mod.data)
    data = _ci(game, "data") if game else None
    if not data or os.path.normcase(os.path.abspath(data)) == os.path.normcase(os.path.abspath(mod.data)):
        return None
    return _ci(data, name)


def mod_ex_path(plan, name="descr_ex.txt"):
    """The mod's own descr_ex.txt to write - when the mod has none but the game has one, the game's whole file is
    copied in first (a one-line file would hide every other setting the game's copy gives the mod). Returns the
    path, ready for plan.edit, or None when neither has one."""
    own = _ci(plan.mod.data, name)
    if own:
        return own
    base = game_ex_file(plan.mod, name)
    if not base:
        return None
    path = os.path.join(plan.mod.data, name)
    if path not in plan.files:                       # the game's text, written as the mod's own new file
        from .textio import TextFile
        f = TextFile.load(base)
        f.path = path
        plan.borrowed.add(path)
        plan.originals[path] = f.dump()
        plan.files[path] = f
    return path


def ex_setting(mod, key):
    """A number setting the engine reads from the mod's descr_ex.txt, else the engine's default; None when the
    tool knows no default for this game."""
    kind = game_kind(mod)
    default = FAMILY_DEFAULTS.get(key)
    if kind == "medieval2" and key == "max_num_children":
        default = None
    p = ex_file(mod, "descr_ex.txt")
    value = _setting(p, key)[1] if p else None
    return value if value is not None else default


RE_ENGINE = re.compile(r"^(rex|m2ex)[^\\/]*\.(exe|xdb)$", re.I)


def engine_files(folder):
    """The engine files in a game folder: REX.exe / M2EX.exe and their .xdb, any case, also a renamed copy
    ('M2EX (1).exe', 'REX_old.exe') - the engine is copied over the game's root folder."""
    try:
        names = os.listdir(folder) if folder and os.path.isdir(folder) else []
    except OSError:
        names = []
    return sorted(n for n in names if RE_ENGINE.match(n) and os.path.isfile(os.path.join(folder, n)))


def engine_of(mod):
    """'REX.exe' / 'M2EX.exe' when that engine lies in the game folder the mod belongs to (also when the mod
    sits in mods/<mod>), else None - the one place that decides whether the original exes' limits hold."""
    from .newmod import game_of
    game = game_of(mod.data)
    found = engine_files(game)
    if not found:
        # descr_ex.txt comes only with an engine (the original games have none): the mod or the game has the
        # engine's settings, so the engine runs it even when its exe was not seen (renamed, elsewhere)
        if any(_ci(d, "descr_ex.txt") for d in (mod.data, _ci(game, "data") if game else None) if d):
            return "M2EX.exe" if game_kind(mod) == "medieval2" else "REX.exe"
        return None
    m2 = any(n.lower().startswith("m2ex") for n in found)
    rex = any(n.lower().startswith("rex") for n in found)
    if m2 and rex:
        return "M2EX.exe" if game_kind(mod) == "medieval2" else "REX.exe"
    return "M2EX.exe" if m2 else "REX.exe"


def engine_report(mod):
    """Plain words: which engine runs this mod, where it was looked for, and where its settings come from."""
    from .newmod import game_of
    game = game_of(mod.data)
    engine = engine_of(mod)
    name = "M2EX" if game_kind(mod) == "medieval2" else "REX"
    if not engine:
        return ("%s not found in %s - the original exe's limits hold (copy %s over the game's folder to lift "
                "them)" % (name, game or "the game folder (not found)", name))
    lim = faction_limit(mod)
    how = "found in %s" % game if engine_files(game) else "taken as installed (its descr_ex.txt is there, its exe " \
        "was not seen in %s)" % game
    own = "the mod's own %s" % os.path.basename(lim["file"]) if lim.get("own") else \
        "the game's data/descr_ex.txt (the mod has none of its own; the engine falls back to the game's)" \
        if lim.get("file") and os.path.isfile(lim["file"]) else "its built-in defaults - no descr_ex.txt in the mod or the game"
    return "%s %s - max_factions %d (from %s)" % (engine[:-4], how, lim["max"], own)


def lifted(mod, key):
    """Why the original exe's limit `key` does not hold for this mod, or None. THE RULE (the user, 2026-10-22,
    replaces 2026-10-03's 'with REX / M2EX EVERY limit is lifted'): only what the engine source shows lifted
    (ENGINE_LIFTS); any other key keeps its limit with the engine too. Setting lines (max_factions) are still
    rewritten to fit (keep_up) - the engine's own way."""
    engine = engine_of(mod)
    if not engine:
        return None
    return ENGINE_LIFTS.get(engine, {}).get(key)


def faction_limit(mod):
    """{'max', 'engine' (REX.exe / M2EX.exe or None), 'file' (the descr_ex.txt the engine reads or would
    read), 'line', 'written' (max_factions is in that file), 'game'}."""
    from .newmod import game_of, is_game
    kind = game_kind(mod)
    game = game_of(mod.data)
    engine = engine_of(mod)
    known = bool(game) and is_game(game)             # the game folder found (an exe beside the data)
    out = {"max": DEFAULTS[kind], "engine": engine, "file": None, "line": None, "written": False, "game": kind,
           "known": known, "own": False}
    if not engine:
        return out
    p = ex_file(mod, "descr_ex.txt")
    out["file"] = p or os.path.join(mod.data, "descr_ex.txt")
    out["own"] = bool(_ci(mod.data, "descr_ex.txt"))
    if p:
        line, value = _setting(p)
        if value is not None:                   # no line: the engine's default holds
            out.update(max=value, line=line, written=True)
    return out


def describe(limit, count):
    if limit["engine"]:                             # no limit: max_factions follows the factions on Apply
        return "%d factions (slave included; no limit with %s - max_factions is raised with Apply when needed)" % (
            count, limit["engine"][:-4])
    return "%d of %d factions (slave included; the game's limit)" % (count, limit["max"])


def check(plan, count, allow_raise=True):
    """Refuse a faction count over the original exe's limit; under REX / M2EX (no faction limit of their own -
    the user: 'raise the cap by itself every time a faction is added') max_factions is raised in the same plan,
    without a question. allow_raise=False only to see the old refusal."""
    limit = faction_limit(plan.mod)
    if count <= limit["max"]:
        return limit
    if limit["engine"] and allow_raise:             # REX / M2EX: no limit - the line follows, nothing said
        raise_limit(plan, limit, count)
        return limit
    if not limit["known"]:                          # no game exe beside the data: which engine runs it is unknown
        plan.warn(None, "%d factions (slave included) - over %d, the limit of the original %s exe; REX / M2EX "
                        "take more when their max_factions (data/descr_ex.txt) allows it"
                  % (count, limit["max"], "Medieval II" if limit["game"] == "medieval2" else "Rome"))
        return limit
    if not limit["engine"]:
        from .newmod import game_of
        name = "M2EX" if limit["game"] == "medieval2" else "REX"
        raise LimitError("%d factions, but the game takes at most %d (slave included) - the game would close at "
                         "start ('Too many factions described here'). The original exe cannot take more; %s can, "
                         "but it was not found in the game folder %s (no %s.exe there). Copy %s over that folder "
                         "(beside the game's exe) and Load again. Nothing written."
                         % (count, limit["max"], name, game_of(plan.mod.data), name, name), limit)
    if not allow_raise:
        raise LimitError("%d factions, but %s is set to take at most %d (max_factions%s) - the game would close "
                         "at start ('Too many factions described here'). The tool can raise max_factions to %d "
                         "for you." % (count, limit["engine"][:-4], limit["max"],
                                       " in %s" % os.path.basename(limit["file"]) if limit["written"] else
                                       ", its default", count), limit)
    raise_limit(plan, limit, count)
    return limit


def raise_limit(plan, limit, count):
    """max_factions set to count in the mod's descr_ex.txt (a line added when missing; the file made with that
    line alone when the mod has none - the game's copy is never read for a mod, ex_file) - with the plan's backup."""
    path = mod_ex_path(plan) or os.path.join(plan.mod.data, "descr_ex.txt")    # the mod's own, the game's copied in
    if path in plan.files or os.path.isfile(path):
        f = plan.edit(path)
        if limit["line"] is not None:
            old = f.text(limit["line"])
            f.set(limit["line"], re.sub(r"(max_factions\s+)\d+", r"\g<1>%d" % count, old, count=1))
        else:
            f.insert(len(f), ["", "; Maximum number of factions - raised by the campaign editor for a new faction",
                              "max_factions %d" % count])
    else:
        # only the one line: every other setting stays the engine's default, as the mod ran before
        plan.binary(path, ("; Extended settings (REX / M2EX) - lines here override the engine's defaults\r\n"
                           "; Maximum number of factions - set by the campaign editor for a new faction\r\n"
                           "max_factions %d\r\n" % count).encode("latin-1"))
    plan.note(None, "max_factions %d -> %d in %s (%s has no faction limit; the line follows the factions)"
              % (limit["max"], count, plan.mod.rel(path), limit["engine"][:-4]))


def raise_setting(plan, key, value):
    """A number line of the mod's descr_ex.txt (max_num_children, max_num_ancillaries, ...) raised to value under
    REX / M2EX - rewritten in place, added when missing, the file made when the mod has none; nothing said but a
    note (the user's rule: with an engine nothing is a limit). Returns True when written."""
    if not engine_of(plan.mod):
        return False
    path = mod_ex_path(plan) or os.path.join(plan.mod.data, "descr_ex.txt")
    if path in plan.files or os.path.isfile(path):
        f = plan.edit(path)
        at = next((i for i, l in enumerate(f.texts()) if re.match(r"\s*%s\s+\d+" % re.escape(key), l)), None)
        if at is not None:
            old = int(re.match(r"\s*%s\s+(\d+)" % re.escape(key), f.text(at)).group(1))
            if old >= value:
                return False
            f.set(at, re.sub(r"(%s\s+)\d+" % re.escape(key), r"\g<1>%d" % value, f.text(at), count=1))
        else:
            f.insert(len(f), ["%s %d" % (key, value)])
    else:
        plan.binary(path, ("; Extended settings (REX / M2EX) - lines here override the engine's defaults\r\n"
                           "%s %d\r\n" % (key, value)).encode("latin-1"))
    plan.note(None, "%s %d in %s (no limit with %s; the line follows)" % (key, value, plan.mod.rel(path),
                                                                        engine_of(plan.mod)[:-4]))
    return True


def keep_up(plan):
    """Every write under REX / M2EX: max_factions in the mod's descr_ex.txt is raised to the faction count the plan
    leaves (descr_sm_factions as edited, else on disk) - a mod whose line is too low (set by hand, an older editor)
    is put right by any Apply, without a word to the modder. No engine: nothing (the original exe's limit holds)."""
    try:
        if not engine_of(plan.mod):
            return
        sm = plan.mod.file("sm_factions")
        if not sm:
            return
        f = plan.files.get(sm) or plan.mod.load(sm)
        from .textio import tokens
        count = sum(1 for l in f.texts() if tokens(l)[:1] == ["faction"])
        limit = faction_limit(plan.mod)
        if limit["file"] and limit["file"] in plan.files:
            line, value = None, None
            for i, l in enumerate(plan.files[limit["file"]].texts()):
                m = re.match(r"\s*max_factions\s+(\d+)", l)
                if m:
                    line, value = i, int(m.group(1))
            if value is not None:
                limit.update(max=value, line=line, written=True)
        if count > limit["max"]:
            raise_limit(plan, limit, count)
    except Exception:
        pass                                        # never stops a write
