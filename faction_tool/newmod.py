"""A separate mod folder for the new faction, so the base game and the base mod
are never touched.

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

from .plan import BACKUP_DIR

MARKER = "faction_tool_mod.json"
# written by the tool, so real copies; the rest is linked
COPY_EXT = {".txt", ".json", ".xml", ".nut", ".lua", ".ini", ".cfg", ".csv", ".yml", ".yaml", ".bat", ".cmd"}
GAME_EXES = ("REX.exe", "RomeTW-ALX.exe", "RomeTW-BI.exe", "RomeTW.exe")
RE_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")


def game_root_of(data_dir):
    """(game folder, base mod folder name or None for the plain game) for a data folder."""
    base = os.path.dirname(os.path.abspath(data_dir))
    if any(os.path.isfile(os.path.join(base, e)) for e in GAME_EXES):
        return base, None
    return os.path.dirname(base), os.path.basename(base)


def marker(mod_dir):
    try:
        with open(os.path.join(mod_dir, MARKER), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


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
        out["Start_%s.bat" % name] = "cd ..\\.\r\nstart %s -nm -show_err -mod:%s\r\n" % (_game_exe(game), name)
    return out


def create_mod(data_dir, name, copy_all=False, progress=None):
    """Make <game>/<name> from the mod (or plain game) that data_dir belongs to.
    Returns (new data folder, summary dict)."""
    if not RE_NAME.match(name or ""):
        raise ValueError("the mod name may use letters, digits, _ and - (like HLR_Saba)")
    game, base_name = game_root_of(data_dir)
    target = os.path.join(game, name)
    if os.path.exists(target):
        raise ValueError("%s already exists - pick another name, or load its data folder to add to it" % target)
    if base_name and base_name.lower() == name.lower():
        raise ValueError("the new mod needs a name other than its base")
    base_dir = os.path.join(game, base_name) if base_name else game
    # the plain game: only its data folder; a mod: the whole mod folder
    sources = [(os.path.join(game, "data"), os.path.join(target, "data"))] if not base_name \
        else [(base_dir, target)]
    stats = {"linked": 0, "copied": 0, "renamed": 0, "bytes_copied": 0}
    link_ok = [not copy_all]
    os.makedirs(target)
    try:
        for src_root, dst_root in sources:
            for dirpath, dirnames, filenames in os.walk(src_root):
                dirnames[:] = [d for d in dirnames if d != BACKUP_DIR]
                rel = os.path.relpath(dirpath, src_root)
                out_dir = os.path.normpath(os.path.join(dst_root, rel))
                os.makedirs(out_dir, exist_ok=True)
                for n in filenames:
                    if n == MARKER or n.lower().endswith((".bat", ".cmd")) and dirpath == base_dir:
                        continue
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
        for n, text in _bats(base_dir, base_name, name, game).items():
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
