"""A separate mod folder for the new faction, so the base game and the base mod
are never touched. Rome: <game>/<name>, started with -mod:<name>; Medieval II:
<game>/mods/<name>, started with mods/<name>/<name>.cfg ([features] mod = ...).

The game takes one -mod:<folder> and falls back to the game's own data for
every file that folder lacks - there is no chain "my mod -> HLR -> game". So a
mod built on HLR must hold all of HLR. Text files (what the tool edits) are
real copies; everything else (models, textures, sounds) is a hard link: the
same file on disk under a second name, no extra space, made at once. A mod
built on the plain game only needs the files that differ, so after a faction
is added the files still identical to the game's are removed again (slim).

Hard links need the new folder on the same drive (NTFS); otherwise, or with
copy_all, every file is copied."""

import json
import os
import re
import shutil

from .plan import BACKUP_DIRS

MARKER = "CampaignEditor_mod.json"
OLD_MARKERS = ("faction_tool_mod.json",)          # written by older versions: still read
# written by the tool, so real copies; the rest is linked
COPY_EXT = {".txt", ".json", ".xml", ".nut", ".lua", ".ini", ".cfg", ".csv", ".yml", ".yaml", ".bat", ".cmd"}
GAME_EXES = ("REX.exe", "RomeTW-ALX.exe", "RomeTW-BI.exe", "RomeTW.exe", "M2EX.exe", "medieval2.exe", "kingdoms.exe")
RE_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")


def game_root_of(data_dir):
    """(game folder, base mod folder name or None for the plain game) for a data folder."""
    base = os.path.dirname(os.path.abspath(data_dir))
    if any(os.path.isfile(os.path.join(base, e)) for e in GAME_EXES):
        return base, None
    return os.path.dirname(base), os.path.basename(base)


def game_of(data_dir):
    """The game folder a data folder belongs to (Medieval II: <game>/mods/<mod>/data)."""
    game = game_root_of(data_dir)[0]
    if os.path.basename(game).lower() == "mods" and is_game(os.path.dirname(game)):
        game = os.path.dirname(game)
    return game


def is_game(folder):
    return bool(folder) and any(os.path.isfile(os.path.join(folder, e)) for e in GAME_EXES)


def list_mods(game):
    """[(label, data folder)] of what a game folder holds: the game's own data, the
    expansions (bi, alexander), every mod folder with a data/descr_sm_factions.txt
    of its own, and Medieval II's mods/<name>/data. Sorted: the game first."""
    out = []
    if not game or not os.path.isdir(game):
        return out
    if os.path.isfile(os.path.join(game, "data", "descr_sm_factions.txt")):
        out.append(("(the game's own data)", os.path.join(game, "data")))
    found = []
    for parent, prefix in ((game, ""), (os.path.join(game, "mods"), "mods/")):
        if not os.path.isdir(parent):
            continue
        for n in sorted(os.listdir(parent), key=str.lower):
            if n in BACKUP_DIRS or (not prefix and n.lower() in ("data", "mods")):
                continue
            d = os.path.join(parent, n, "data")
            if os.path.isfile(os.path.join(d, "descr_sm_factions.txt")):
                found.append((prefix + n, d))
    return out + found


def marker(mod_dir):
    """The mod folder's mark (made by New mod folder): CampaignEditor_mod.json; an older version's mark is renamed
    to it on the first read (the same content)."""
    for name in (MARKER,) + OLD_MARKERS:
        p = os.path.join(mod_dir, name)
        try:
            with open(p, encoding="utf-8") as f:
                got = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(got, dict):                 # another version's mark: not one this version reads
            continue
        if name != MARKER and not os.path.exists(os.path.join(mod_dir, MARKER)):
            try:
                os.replace(p, os.path.join(mod_dir, MARKER))
            except OSError:
                pass
        return got
    return None


M2_EXES = ("M2EX.exe", "medieval2.exe", "kingdoms.exe")


def is_medieval2(game):
    """A Medieval II game folder: its mods live in mods/<name> and start with a .cfg."""
    return bool(game) and any(os.path.isfile(os.path.join(game, e)) for e in M2_EXES)


def mod_target(data_dir, name):
    """Where a new mod folder goes: <game>/<name> for Rome (started with -mod:<name>),
    <game>/mods/<name> for Medieval II (started with mods/<name>/<name>.cfg)."""
    game = game_of(data_dir)
    return os.path.join(game, "mods", name) if is_medieval2(game) else os.path.join(game, name)


def _cfg(base_dir, base_name, name):
    """Medieval II's <name>.cfg: the base mod's own with its folder renamed, else a plain one."""
    if base_name and os.path.isdir(base_dir):
        rx = re.compile(r"mods[/\\]%s\b" % re.escape(base_name), re.I)
        for n in sorted(os.listdir(base_dir)):
            if n.lower().endswith(".cfg"):
                with open(os.path.join(base_dir, n), "rb") as f:
                    text = f.read().decode("latin-1")
                if rx.search(text):
                    return rx.sub("mods/" + name, text)
    return ("[features]\r\nmod = mods/%s\r\n\r\n[log]\r\nto = mods/%s/system.log.txt\r\nlevel = * error\r\n"
            % (name, name))


def _m2_start(game, base_dir, base_name, name):
    """{file name: text} of a Medieval II mod's start files: the .cfg and a .bat that
    starts the game with it (the game's exe from the game folder, two levels up)."""
    exe = next((e for e in M2_EXES if os.path.isfile(os.path.join(game, e))), "medieval2.exe")
    # M2EX's own start files (Teutonic.bat ...) name the mod folder on the command line, not a .cfg
    how = ("--features.mod=mods/%s" % name if exe.lower() == "m2ex.exe"
           else "@mods\\%s\\%s.cfg" % (name, name))
    return {"%s.cfg" % name: _cfg(base_dir, base_name, name),
            "Start_%s.bat" % name: 'cd /d "%%~dp0..\\.."\r\nstart "" %s %s\r\n' % (exe, how)}


def _game_exe(game):
    return next((e for e in GAME_EXES if os.path.isfile(os.path.join(game, e))), "RomeTW.exe")


def _bats(base_dir, base_name, name, game):
    """Start scripts: the base mod's own, with -mod:<base> turned into -mod:<name>."""
    out = {}
    if base_name and os.path.isdir(base_dir):
        rx = re.compile(r"(-mod:)%s\b" % re.escape(base_name), re.I)
        for n in os.listdir(base_dir):
            if not n.lower().endswith((".bat", ".cmd")):
                continue
            with open(os.path.join(base_dir, n), "rb") as f:
                text = f.read().decode("latin-1")
            if rx.search(text):
                out["Start_%s.bat" % name] = rx.sub(lambda m: m.group(1) + name, text)
                break
    if not out:
        # a mod made from Barbarian Invasion or Alexander starts that game, as REX's own
        # "Barbarian Invasion.bat" (-bi) and "Alexander.bat" (-alx) do; without it REX reads the mod over
        # the plain game's data (the user's bi_Empire_east: imperial_campaign parsed with BI's factions)
        flag = {"bi": " -bi", "alexander": " -alx"}.get((base_name or "").lower(), "") \
            if _game_exe(game) == "REX.exe" else ""
        # the game's folder from where the .bat lies (cd ..\. counted from wherever it was started: a shortcut
        # or another folder started the engine away from the game)
        out["Start_%s.bat" % name] = 'cd /d "%%~dp0.."\r\nstart %s%s -nm -show_err -mod:%s\r\n' % (
            _game_exe(game), flag, name)
    return out


def create_mod(data_dir, name, copy_all=False, progress=None):
    """Make <game>/<name> from the mod (or plain game) that data_dir belongs to.
    Returns (new data folder, summary dict)."""
    if not RE_NAME.match(name or ""):
        raise ValueError("the mod name may use letters, digits, _ and - (like HLR_Saba)")
    _, base_name = game_root_of(data_dir)
    game = game_of(data_dir)
    m2 = is_medieval2(game)
    target = mod_target(data_dir, name)
    if os.path.exists(target):
        raise ValueError("%s already exists - pick another name, or load its data folder to add to it" % target)
    if base_name and base_name.lower() == name.lower():
        raise ValueError("the new mod needs a name other than its base")
    base_dir = os.path.dirname(os.path.abspath(data_dir)) if base_name else game
    # the plain game: only its data folder; a mod: the whole mod folder
    sources = [(os.path.join(game, "data"), os.path.join(target, "data"))] if not base_name \
        else [(base_dir, target)]
    stats = {"linked": 0, "copied": 0, "renamed": 0, "bytes_copied": 0}
    link_ok = [not copy_all]
    os.makedirs(target)
    try:
        starts = _m2_start(game, base_dir, base_name, name) if m2 else _bats(base_dir, base_name, name, game)
        for src_root, dst_root in sources:
            for dirpath, dirnames, filenames in os.walk(src_root):
                dirnames[:] = [d for d in dirnames if d not in BACKUP_DIRS]
                rel = os.path.relpath(dirpath, src_root)
                out_dir = os.path.normpath(os.path.join(dst_root, rel))
                os.makedirs(out_dir, exist_ok=True)
                for n in filenames:
                    if n in (MARKER,) + OLD_MARKERS or n.lower().endswith((".bat", ".cmd") + ((".cfg",) if m2 else ())) \
                            and dirpath == base_dir:
                        continue                  # the start files are written for the new name below
                    src = os.path.join(dirpath, n)
                    names = [n]
                    # files named after the base mod (HLR.idx, HLR.dat): also under the new name
                    if base_name and re.match(r"^%s\." % re.escape(base_name), n, re.I):
                        names.append(name + n[len(base_name):])
                    for dn in names:
                        _put(src, os.path.join(out_dir, dn), link_ok, stats)
                        if dn != n:
                            stats["renamed"] += 1
                    total = stats["linked"] + stats["copied"]
                    if progress and total % 500 == 0:
                        progress(total)
        for n, text in starts.items():
            with open(os.path.join(target, n), "wb") as f:
                f.write(text.encode("latin-1"))
        with open(os.path.join(target, MARKER), "w", encoding="utf-8") as f:
            json.dump({"base": base_name or "(game)", "linked": link_ok[0]}, f, indent=2)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    stats["target"] = target
    stats["base"] = base_name or "(game)"
    stats["hard_links"] = link_ok[0]
    return os.path.join(target, "data"), stats


def _put(src, dst, link_ok, stats):
    if link_ok[0] and os.path.splitext(src)[1].lower() not in COPY_EXT:
        try:
            os.link(src, dst)
            stats["linked"] += 1
            return
        except OSError:
            link_ok[0] = False          # another drive or no NTFS: copy from here on
    shutil.copy2(src, dst)
    stats["copied"] += 1
    stats["bytes_copied"] += os.path.getsize(dst)


def slim(data_dir):
    """For a mod built on the plain game: remove every file still identical to
    the game's own (the game falls back to those anyway). Returns the count."""
    target = os.path.dirname(os.path.abspath(data_dir))
    m = marker(target)
    if not m or m.get("base") != "(game)":
        return 0
    game = os.path.dirname(target)
    if os.path.basename(game).lower() == "mods" and is_game(os.path.dirname(game)):
        game = os.path.dirname(game)                  # Medieval II: <game>/mods/<name>
    removed = 0
    for dirpath, dirnames, filenames in os.walk(data_dir, topdown=False):
        for n in filenames:
            p = os.path.join(dirpath, n)
            orig = os.path.join(game, "data", os.path.relpath(p, data_dir))
            if os.path.isfile(orig) and _same(p, orig):
                os.remove(p)
                removed += 1
        if dirpath != data_dir and not os.listdir(dirpath):
            os.rmdir(dirpath)
    return removed


def _same(a, b):
    try:
        if os.path.samefile(a, b):
            return True
    except OSError:
        return False
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if x != y:
                return False
            if not x:
                return True


def deletable_mod_folder(data_dir):
    """The mod folder Tools > Delete this mod... may delete for a loaded data folder: <game>/<mod> (Rome) or
    <game>/mods/<mod> (Medieval II). ValueError in plain words for the game's own data, an expansion's (bi,
    alexander) or a folder that is not inside a game - those are never deleted."""
    data = os.path.abspath(data_dir)
    folder = os.path.dirname(data)
    if is_game(folder):
        raise ValueError("this is the game's own data folder, not a mod - it is never deleted")
    if os.path.basename(folder).lower() in ("bi", "alexander", "data") or os.path.basename(data).lower() != "data":
        raise ValueError("%s is the game's own (an expansion), not a mod folder - it is never deleted" % folder)
    parent = os.path.dirname(folder)
    game = os.path.dirname(parent) if os.path.basename(parent).lower() == "mods" else parent
    if not is_game(game):
        raise ValueError("%s does not lie in a game folder (<game>/<mod> or <game>/mods/<mod>) - not deleted" % folder)
    return folder

