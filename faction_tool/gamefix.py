"""Known set-up problems of a game or mod that stop it from starting, found on Load and
fixed with the user's yes (a Plan: previewed, backed up, undone by Restore like any
other change)."""

import os
import re

from .moddata import _ci
from .plan import Plan
from .textio import strip_comment


def _vegetation_maps(mod):
    """Whether the raw vegetation maps M2EX's text source needs are there."""
    game = os.path.dirname(mod.data)
    for root in (mod.data, game):
        if os.path.isdir(os.path.join(root, "export", "new_vegetation", "raw_distribution_maps")):
            return True
    return False


def problems(mod):
    """[{'id', 'why', 'file', 'line', 'new'}] - what would stop the game and can be put right."""
    out = []
    caps = _ci(mod.data, "descr_caps_ex.txt")
    if caps:
        f = mod.load(caps)
        for i in range(len(f)):
            code = strip_comment(f.text(i))
            m = re.match(r"^(\s*vegetation_source\s+)text\s*$", code)
            if m and not _vegetation_maps(mod):
                out.append({
                    "id": "vegetation_source",
                    "why": "descr_caps_ex.txt reads the vegetation from text (vegetation_source text), which "
                           "needs export/new_vegetation/raw_distribution_maps - not here, so M2EX closes "
                           "at start ('Failed to load text vegetation database'). The fix: vegetation_source "
                           "binary (the game's own vegetation.db, M2EX's default for mods).",
                    "file": caps, "line": i, "new": f.text(i).replace(m.group(0), m.group(1) + "binary", 1)})
    return out


def fix_plan(mod, found):
    """A Plan that puts the problems found right."""
    plan = Plan(mod, "setup", "setup_fix")
    for p in found:
        f = plan.edit(p["file"])
        f.set(p["line"], p["new"])
        plan.note(f, "%s: text -> binary (the game started without it closing)" % p["id"])
    return plan


# ---------------------------------------------------------------------------
# Medieval II straight from Steam: everything is in packs/*.pack; the game's own
# unpacker (tools/unpacker) needs the two runtime DLLs medieval2.exe itself loads
# (msvcp71.dll, msvcr71.dll, in the game folder) next to it.
# ---------------------------------------------------------------------------
UNPACK_DLLS = ("msvcp71.dll", "msvcr71.dll")


def _game_folder(path):
    path = os.path.abspath(path)
    for cand in (path, os.path.dirname(path)):
        if os.path.isdir(os.path.join(cand, "packs")):
            return cand
    return None


def unpack_needed(path):
    """{'game', 'unpacker', 'bat', 'dlls': [missing next to the unpacker], 'from': game folder}
    when path (the game or its data folder) is a Medieval II with packs and nothing unpacked;
    else None."""
    game = _game_folder(path)
    if not game:
        return None
    if _ci(os.path.join(game, "data"), "descr_sm_factions.txt"):
        return None                                  # unpacked already
    packs = [n for n in os.listdir(os.path.join(game, "packs")) if n.lower().endswith(".pack")]
    folder = os.path.join(game, "tools", "unpacker")
    exe = _ci(folder, "unpacker.exe")
    if not packs or not exe:
        return None
    return {"game": game, "unpacker": exe, "bat": _ci(folder, "unpack_all.bat"),
            "dlls": [d for d in UNPACK_DLLS if not _ci(folder, d)], "packs": len(packs)}


def unpack(need, log=None):
    """Copy the missing DLLs from the game folder next to the unpacker, then run the game's
    unpack_all.bat (or unpacker.exe on every pack). Returns the unpacker's output; raises
    with the reason when a DLL is nowhere to copy from or the unpacker fails."""
    import shutil
    import subprocess
    folder = os.path.dirname(need["unpacker"])
    for d in need["dlls"]:
        src = _ci(need["game"], d)
        if not src:
            raise FileNotFoundError("%s is not in the game folder %s either - the unpacker cannot run "
                                    "without it" % (d, need["game"]))
        shutil.copy2(src, os.path.join(folder, d))
        if log:
            log("copied %s next to the unpacker" % d)
    if need.get("bat"):
        cmd = ["cmd", "/c", os.path.basename(need["bat"])]
    else:
        cmd = [need["unpacker"], "--source=../../packs/*.pack", "--destination=../../"]
    # the batch ends with 'pause': a newline on stdin lets it finish
    run = subprocess.run(cmd, cwd=folder, input=b"\r\n\r\n", stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    out = run.stdout.decode("latin-1", "replace")
    if not _ci(os.path.join(need["game"], "data"), "descr_sm_factions.txt"):
        raise RuntimeError("the unpacker ran (exit %s) but data/descr_sm_factions.txt is still missing:\n%s"
                           % (run.returncode, out[-2000:]))
    return out


__all__ = ["problems", "fix_plan", "unpack_needed", "unpack"]
