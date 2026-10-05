"""Start the game with the loaded mod (the bottom bar's Start the game). The mod's own start script when it has one
(New mod folder writes Start_<name>.bat into the mod folder; the engines keep theirs in the game folder: REX's
'Barbarian Invasion.bat' = REX.exe -bi, M2EX's 'Teutonic.bat' = M2EX.exe --features.mod=mods/teutonic), else the
line those scripts use: REX.exe -nm -show_err -mod:<name> (-bi / -alx for the expansions), M2EX.exe
--features.mod=mods/<name>, medieval2.exe @mods\\<name>\\<name>.cfg, and the plain game with its own exe."""

import os
import re
import subprocess
import sys

from .newmod import M2_EXES, game_of, game_root_of, is_medieval2

# a script that starts the game (not an unpacker's): a game exe, -mod:, M2EX's --features.mod or a .cfg after @
RE_STARTS = re.compile(r"\b(?:rex|m2ex|rometw(?:-bi|-alx)?|medieval2|kingdoms)\.exe\b|-mod:|features\.mod|@\S+\.cfg\b",
                       re.I)
EXPANSIONS = {"bi": ("-bi", "RomeTW-BI.exe"), "alexander": ("-alx", "RomeTW-ALX.exe")}


def _scripts(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, n) for n in os.listdir(folder)
                  if n.lower().endswith((".bat", ".cmd")) and os.path.isfile(os.path.join(folder, n)))


def _text(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(20000).decode("latin-1")
    except OSError:
        return ""


def _own_script(game, base, mod_dir):
    """The start script of the mod: one in its own folder naming it (Start_<name>.bat first), else one there that
    starts the game at all, else one in the game folder naming it (-mod:<name>, mods/<name>, -bi / -alx)."""
    names = [re.compile(r"-mod:\s*\"?%s\b" % re.escape(base), re.I),
             re.compile(r"mods[/\\]+%s\b" % re.escape(base), re.I)]
    flag = EXPANSIONS.get(base.lower(), (None,))[0]
    if flag:
        names.append(re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(flag), re.I))
    own = _scripts(mod_dir)
    first = [p for p in own if os.path.basename(p).lower() == ("start_%s.bat" % base).lower()]
    for p in first + [p for p in own if any(rx.search(_text(p)) for rx in names)] + \
            [p for p in own if RE_STARTS.search(_text(p))]:
        return p
    for p in _scripts(game):
        if any(rx.search(_text(p)) for rx in names):
            return p
    return None


def start_line(data):
    """How the game starts with the mod of this data folder: {'bat': its start script} or {'exe': the engine,
    'args': [...], 'cwd': the game folder}, both with 'words' (what is started, in plain words). ValueError when the
    game folder has no exe to start."""
    data = os.path.abspath(data)
    game = game_of(data)
    _, base = game_root_of(data)
    m2 = is_medieval2(game)
    mod_dir = os.path.dirname(data) if base else None
    if base:
        bat = _own_script(game, base, mod_dir)
        if bat:
            return {"bat": bat, "words": "%s (the mod's start script)" % os.path.basename(bat)}
    if m2:
        exe = next((e for e in M2_EXES if os.path.isfile(os.path.join(game, e))), None)
        if not exe:
            raise ValueError("no game exe (M2EX.exe, medieval2.exe) in %s" % game)
        if not base:
            args = []
        elif exe.lower() == "m2ex.exe":
            args = ["--features.mod=mods/%s" % base]
        else:
            if not os.path.isfile(os.path.join(mod_dir, base + ".cfg")):
                raise ValueError("the mod has no start script and no %s.cfg - Medieval II starts a mod with one "
                                 "(New mod folder... makes both)" % base)
            args = ["@mods\\%s\\%s.cfg" % (base, base)]
    else:
        low = (base or "").lower()
        if os.path.isfile(os.path.join(game, "REX.exe")):
            exe = "REX.exe"
            args = [EXPANSIONS[low][0]] if low in EXPANSIONS else (["-nm", "-show_err", "-mod:%s" % base]
                                                                   if base else [])
        else:
            exe = EXPANSIONS[low][1] if low in EXPANSIONS else "RomeTW.exe"
            if not os.path.isfile(os.path.join(game, exe)):
                raise ValueError("no game exe (REX.exe, %s) in %s" % (exe, game))
            args = ["-nm", "-show_err", "-mod:%s" % base] if base and low not in EXPANSIONS else []
    return {"exe": os.path.join(game, exe), "args": args, "cwd": game, "words": " ".join([exe] + args)}


def start(how):
    """Start it (start_line's answer) and return at once - the game runs on its own. Windows only: elsewhere
    OSError names the line to start by hand."""
    if sys.platform != "win32":
        line = how["bat"] if "bat" in how else " ".join([how["exe"]] + how["args"])
        raise OSError("the game starts on Windows - start it by hand: %s" % line)
    hidden = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if "bat" in how:                              # the script goes to the game folder itself (cd /d %~dp0..)
        return subprocess.Popen(["cmd", "/c", how["bat"]], cwd=os.path.dirname(how["bat"]), creationflags=hidden)
    return subprocess.Popen([how["exe"]] + how["args"], cwd=how["cwd"])
