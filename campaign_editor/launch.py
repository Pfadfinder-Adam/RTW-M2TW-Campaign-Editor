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


def _engine(game):
    """'M2EX.exe' / 'REX.exe' when the extender sits in the game folder, else None."""
    return next((e for e in ("M2EX.exe", "REX.exe") if os.path.isfile(os.path.join(game, e))), None)


def _own_script(game, base, mod_dir):
    """The start script of the mod: one in its own folder naming it (Start_<name>.bat first), else one there that
    starts the game at all, else one in the game folder naming it (-mod:<name>, mods/<name>, -bi / -alx). With
    M2EX / REX in the game folder only a script that starts the extender counts: a mod's own script for the plain
    exe (or a launcher) did not start the game from the editor (a tester's Third Age Reforged with M2EX), and the
    extender's own line does."""
    eng = _engine(game)
    uses = re.compile(r"(?<![a-z])%s\b" % re.escape(eng), re.I) if eng else None   # %~dp0REX.exe too
    names = [re.compile(r"-mod:\s*\"?%s\b" % re.escape(base), re.I),
             re.compile(r"mods[/\\]+%s\b" % re.escape(base), re.I)]
    flag = EXPANSIONS.get(base.lower(), (None,))[0]
    if flag:
        names.append(re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(flag), re.I))
    own = [p for p in _scripts(mod_dir) if not uses or uses.search(_text(p))]
    first = [p for p in own if os.path.basename(p).lower() == ("start_%s.bat" % base).lower()]
    for p in first + [p for p in own if any(rx.search(_text(p)) for rx in names)] + \
            [p for p in own if RE_STARTS.search(_text(p))]:
        return p
    for p in _scripts(game):
        if any(rx.search(_text(p)) for rx in names) and (not uses or uses.search(_text(p))):
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


def large_address_aware(exe):
    """True / False: the exe may use more than 2 GB (the PE header's flag - a big mod runs out of memory without it on
    the 32-bit games); None when it cannot be read or is a 64-bit exe (the extenders: no such limit)."""
    try:
        with open(exe, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return None
    if head[:2] != b"MZ" or len(head) < 64:
        return None
    pe = int.from_bytes(head[60:64], "little")
    if pe + 24 > len(head) or head[pe:pe + 4] != b"PE\0\0":
        return None
    machine = int.from_bytes(head[pe + 4:pe + 6], "little")
    if machine != 0x14c:                                    # not 32-bit x86
        return None
    return bool(int.from_bytes(head[pe + 22:pe + 24], "little") & 0x20)


RE_EXE = re.compile(r"([\w.-]+\.exe)\b", re.I)


def problems(how, data):
    """What would keep the game from starting with the mod, before it is started: [(stops, words)] - stops True
    when it surely would not start (refused), False when it may still start (asked), None a note (said beside: the
    games' own exes are all so, a question every start would only nag)."""
    out = []
    data = os.path.abspath(data)
    game = game_of(data)
    _, base = game_root_of(data)
    if "bat" in how:
        text = re.sub(r"%~[a-z]*\d", " ", _text(how["bat"]))        # %~dp0REX.exe = the folder's REX.exe
        exes = [e for e in RE_EXE.findall(text) if not e.lower().startswith(("unpacker", "cmd"))]
        here = [e for e in exes if os.path.isfile(os.path.join(game, e)) or
                os.path.isfile(os.path.join(os.path.dirname(how["bat"]), e))]
        if exes and not here:
            out.append((True, "%s starts %s, which is not in the game folder %s" % (
                os.path.basename(how["bat"]), " / ".join(sorted(set(exes))), game)))
        for cfg in re.findall(r"@(\S+?\.cfg)\b", text, re.I):
            path = os.path.join(game, cfg.replace("\\", os.sep).replace("/", os.sep))
            if not os.path.isfile(path):
                out.append((True, "%s starts the game with %s, which is not there" % (os.path.basename(how["bat"]),
                                                                                       cfg)))
            else:
                out += _cfg_problems(path, base)
        exe = next((os.path.join(game, e) for e in here if os.path.isfile(os.path.join(game, e))), None)
    else:
        exe = how["exe"]
        cfg = next((a[1:] for a in how["args"] if a.startswith("@")), None)
        if cfg:
            out += _cfg_problems(os.path.join(game, cfg.replace("\\", os.sep)), base)
    if exe and large_address_aware(exe) is False:
        out.append((None, "%s can use only 2 GB of memory (it is not 'Large Address Aware') - a big mod may "
                           "crash when the campaign loads; a 4 GB patch for it fixes that" % os.path.basename(exe)))
    return out


def _cfg_problems(path, base):
    """Medieval II's mod .cfg: [features] mod = mods/<name>, or the game starts without the mod (file_first is not
    asked for: whether a mod = line needs it is not known for sure)."""
    text = _text(path)
    out = []
    if base and not re.search(r"^\s*mod\s*=\s*mods[/\\]+%s\b" % re.escape(base), text, re.I | re.M):
        out.append((False, "%s does not name the mod's folder (mod = mods/%s under [features]) - the game may "
                           "start without the mod" % (os.path.basename(path), base)))
    return out


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
