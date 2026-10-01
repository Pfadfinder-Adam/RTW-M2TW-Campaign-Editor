"""How many factions the game takes, and raising it where the engine lets us.

The original exes stop at a fixed number (slave included): Rome 21, Medieval II 31. REX and M2EX read
`max_factions` from data/descr_ex.txt ("Maximum number of factions (default in M2: 31, RTW: 21) /
Increase to support more factions in mods") - the mod's own copy, else the game's data (REX falls back
to it). Over the limit the game closes at start: "Too many factions described here, maximum is(21).
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
    return "medieval2" if _ci(mod.data, "descr_religions.txt") else "rome"


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
    "rome": {"regions": 200, "map_size": 510, "units": 500, "chains": 64, "levels": 9, "hidden_resources": 63},
    "medieval2": {"regions": 200, "map_size": 510, "units": 500, "chains": 128, "levels": 9,
                  "hidden_resources": 64},
}
# What REX / M2EX do with them (one engine, two builds - the same notes). Sources: REX's README "Removed every single
# major engine limit like factions, regions, religions, cultures etc.", its release notes (08/06 cultures and
# religions uncapped; 18/04 maps past 32768), the EB II / M2EX thread on TWC ("no faction, religion, region, unit,
# cultures, model etc. limits"), HLR's 750 regions under REX. Factions stay a number of their own (max_factions).
# Not named anywhere: building chains, levels, hidden resources - those keep the original's number as a note.
_LIFTS = {
    "regions": "lifted by REX / M2EX (HLR runs 750 regions under REX)",
    "map_size": "lifted by REX / M2EX (their notes: map size limits removed, maps past 32768 fixed)",
    "units": "lifted by REX / M2EX (\"no ... unit ... limits\" - M2EX's own notes)",
    "religions": "lifted by REX / M2EX (README: religions uncapped)",
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
    import re
    from .newmod import game_of
    if game_kind(mod) != "medieval2":
        return ex_setting(mod, "age_of_manhood") or 16
    game = game_of(mod.data)
    for folder in (mod.data, _ci(game, "data") if game else None):
        p = _ci(folder, "descr_campaign_db.xml") if folder else None
        if p:
            m = re.search(r"<age_of_manhood\s+(?:uint|int|float)=\"(\d+)", open(p, encoding="latin-1").read())
            return int(m.group(1)) if m else 16
    return 16


def ex_setting(mod, key):
    """A number setting the engine reads from descr_ex.txt (the mod's copy, else the game's data),
    else the game's default; None when the tool knows no default for this game."""
    from .newmod import game_of
    kind = game_kind(mod)
    default = FAMILY_DEFAULTS.get(key)
    if kind == "medieval2" and key == "max_num_children":
        default = None
    game = game_of(mod.data)
    game_data = _ci(game, "data") if game else None
    for folder in (mod.data, game_data):
        p = _ci(folder, "descr_ex.txt") if folder else None
        if p:
            value = _setting(p, key)[1]
            return value if value is not None else default     # the file the engine reads decides
    return default


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
        ("the game's data/descr_ex.txt (the mod has none of its own)" if lim["written"] else "its defaults")
    return "%s %s - max_factions %d (from %s)" % (engine[:-4], how, lim["max"], own)


def lifted(mod, key):
    """Why the original exe's limit `key` does not hold for this mod (the engine lifts it), or None."""
    engine = engine_of(mod)
    return ENGINE_LIFTS.get(engine, {}).get(key) if engine else None


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
    game_data = _ci(game, "data") if game else None
    for folder in (mod.data, game_data):
        p = _ci(folder, "descr_ex.txt") if folder else None
        if not p:
            continue
        line, value = _setting(p)
        out["file"] = p
        out["own"] = folder == mod.data
        if value is not None:
            out.update(max=value, line=line, written=True)
            return out
        break                                   # the file the engine reads has no line: the default holds
    if out["file"] is None:
        out["file"] = os.path.join(mod.data, "descr_ex.txt")
    return out


def describe(limit, count):
    where = ("max_factions in %s" % os.path.basename(limit["file"])) if limit["written"] else \
        ("%s's default" % limit["engine"][:-4] if limit["engine"] else "the game's limit")
    return "%d of %d factions (slave included; %s)" % (count, limit["max"], where)


def check(plan, count, allow_raise=False):
    """Refuse a faction count over the limit, or with allow_raise write a higher max_factions (REX / M2EX)."""
    limit = faction_limit(plan.mod)
    if count <= limit["max"]:
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
    """max_factions set to count in the descr_ex.txt the engine reads (a line added when missing; the
    file made in the mod's data when there is none) - with the plan's backup like any change."""
    path = limit["file"]
    own = os.path.join(plan.mod.data, "descr_ex.txt")
    if path and os.path.isfile(path) and not limit.get("own") and \
            os.path.normcase(os.path.abspath(path)) != os.path.normcase(os.path.abspath(own)):
        # the game's copy: the mod gets its own (M2EX's Kingdoms mods each carry their _ex files; the game's
        # data is never changed for one mod) - the game's file copied, then the line raised in the copy
        with open(path, "rb") as fh:
            plan.binary(own, re.sub(rb"(?m)^(\s*max_factions\s+)\d+", lambda m: m.group(1) + str(count).encode(),
                                    fh.read(), count=1) if limit["line"] is not None else fh.read() +
                        ("\r\nmax_factions %d\r\n" % count).encode("latin-1"))
        plan.note(None, "max_factions %d -> %d in %s, a copy of the game's %s for this mod (%s reads it; over it "
                        "the game closes at start)" % (limit["max"], count, plan.mod.rel(own), plan.mod.rel(path),
                                                       limit["engine"][:-4]))
        return
    path = own if not path else path
    if os.path.isfile(path):
        f = plan.edit(path)
        if limit["line"] is not None:
            old = f.text(limit["line"])
            f.set(limit["line"], re.sub(r"(max_factions\s+)\d+", r"\g<1>%d" % count, old, count=1))
        else:
            f.insert(len(f), ["", "; Maximum number of factions - raised by the campaign editor for a new faction",
                              "max_factions %d" % count])
    else:
        plan.binary(path, ("; Extended settings (REX / M2EX)\r\n; Maximum number of factions - set by the "
                           "campaign editor for a new faction\r\nmax_factions %d\r\n" % count).encode("latin-1"))
    plan.note(None, "max_factions %d -> %d in %s (%s reads it; over it the game closes at start)"
              % (limit["max"], count, plan.mod.rel(path), limit["engine"][:-4]))
