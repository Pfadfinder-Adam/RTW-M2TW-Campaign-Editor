"""Known set-up problems of a game or mod that stop it from starting, found on Load and
fixed with the user's yes (a Plan: previewed, backed up, undone by Restore like any
other change)."""

import os
import re

from .moddata import _ci
from .plan import Plan
from .textio import strip_comment, tokens


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
    from .limits import ex_file
    caps = ex_file(mod, "descr_caps_ex.txt")
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
    missing = missing_engine_files(mod)
    if missing:
        from .limits import engine_of
        name = engine_of(mod)[:-4]
        out.append({"id": "engine_files", "names": missing,
                    "why": "This mod has no %s of its own, though %s in the game's data. %s reads its "
                           "settings (the faction limit, sprites, models, AI...) only from the mod's own data "
                           "folder - its descr_caps_ex.txt says \"Mods that don't ship this file get safe defaults\", "
                           "so this mod runs on %s's built-in defaults, not on the game's settings. The fix: the "
                           "game's copies go into the mod (they can be changed there for this mod alone)."
                           % (", ".join(missing), "it lies" if len(missing) == 1 else "they lie", name, name)})
    from .strat import headers_out_of_order
    for camp in mod.campaigns():
        sp = mod.campaign_file(camp, "descr_strat.txt")
        bad = headers_out_of_order(mod.load(sp)) if sp else []
        if bad:
            out.append({"id": "faction_header", "file": sp, "blocks": bad,
                        "why": "%s's descr_strat.txt: the first lines of %s are out of the games' order (denari "
                               "before superfaction / ai_label, or dead_until_resurrected after them) - the game then "
                               "starts the faction without its towns and it is destroyed on the first turn. Versions "
                               "0.29.1 and 0.29.2 of this tool wrote new factions so. The fix: the lines put in the "
                               "games' order (superfaction / ai_label, dead_until_resurrected, re_emergent, denari, "
                               "denari_kings_purse), nothing else changed."
                               % (camp, ", ".join(n for n, _ in bad))})
    from .packs import game_kind
    if game_kind(mod) == "medieval2":
        for camp in mod.campaigns():
            wp = mod.campaign_file(camp, "descr_win_conditions.txt")
            f = mod.load(wp) if wp else None
            for i in range(len(f) if f else 0):
                t = tokens(strip_comment(f.text(i)))
                if t[:1] == ["short_campaign"] and t[1:2] != ["hold_regions"]:
                    out.append({"id": "short_campaign", "file": wp, "line": i,
                                "why": "%s's descr_win_conditions.txt line %d: '%s' - Medieval II wants hold_regions "
                                       "right after short_campaign (all its own files have it, even with an empty "
                                       "list) and stops reading there, so every faction after it has no victory "
                                       "conditions ('No win condition has been set'). Version 0.29.2 of this tool "
                                       "wrote it so. The fix: 'short_campaign hold_regions' and the rest on the next "
                                       "line." % (camp, i + 1, f.text(i).strip())})
    old = _old_culture_module(mod)
    if old:
        out.append({"id": "old_culture_names", "file": old[0], "table": old[1],
                    "why": "script/modules/ft_settlement_names.nut was written by an early 0.12 build of this tool "
                           "(names by culture as a Squirrel module with guessed REX calls - REX loads every "
                           "module there). The names now live in the campaign's campaign_script.txt, the way "
                           "REX's documentation gives. The fix: its %d town(s) move there and the module goes."
                           % len(old[1])})
    return out


OLD_MODULE = ("script", "modules", "ft_settlement_names.nut")


def _old_culture_module(mod):
    """(path, table) of the early names-by-culture module, or None."""
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(mod.data)), *OLD_MODULE)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        text = fh.read().decode("utf-8", "replace")
    m = re.search(r"^// DATA (.*)$", text, re.M)
    try:
        table = json.loads(m.group(1)) if m else {}
    except ValueError:
        table = {}
    return path, table if isinstance(table, dict) else {}


def missing_engine_files(mod):
    """The engine's own files (descr_ex.txt, descr_caps_ex.txt, *_ex.txt / *_ex.xml) the game's data has and this
    mod's data lacks - only for a mod (not the game's own data) of a game with REX / M2EX."""
    from .limits import engine_of
    from .newmod import game_of
    game = game_of(mod.data)
    gdata = _ci(game, "data") if game else None
    if not gdata or os.path.normcase(os.path.abspath(gdata)) == os.path.normcase(os.path.abspath(mod.data)):
        return []
    if not engine_of(mod):
        return []
    try:
        names = sorted(n for n in os.listdir(gdata) if re.search(r"_ex\.(txt|xml)$", n, re.I)
                       and os.path.isfile(os.path.join(gdata, n)))
    except OSError:
        return []
    return [n for n in names if not _ci(mod.data, n)]


def fix_plan(mod, found):
    """A Plan that puts the problems found right."""
    plan = Plan(mod, "setup", "setup_fix")
    # lines inserted (short_campaign) move the lines below them: the lowest of a file first
    found = sorted(found, key=lambda p: -p["line"] if p["id"] == "short_campaign" else 0)
    for p in found:
        if p["id"] == "engine_files":
            from .newmod import game_of
            gdata = _ci(game_of(mod.data), "data")
            for n in p["names"]:
                with open(os.path.join(gdata, n), "rb") as fh:
                    plan.binary(os.path.join(mod.data, n), fh.read())
                plan.note(None, "%s copied from the game's data into the mod" % n)
            continue
        if p["id"] == "short_campaign":
            f = plan.edit(p["file"])
            text = f.text(p["line"])
            rest = text.split("short_campaign", 1)[1].strip()
            f.set(p["line"], "short_campaign hold_regions")
            f.insert(p["line"] + 1, [rest])
            plan.note(f, "line %d: short_campaign hold_regions + '%s' on its own line" % (p["line"] + 1, rest))
            continue
        if p["id"] == "faction_header":
            from .strat import ordered_header
            f = plan.edit(p["file"])
            for name, idx in p["blocks"]:
                texts = ordered_header([f.text(i) for i in idx])
                for i, t in zip(idx, texts):
                    f.set(i, t)
            plan.note(f, "faction header lines put in the games' order: %s" % ", ".join(n for n, _ in p["blocks"]))
            continue
        if p["id"] == "old_culture_names":
            from . import culturenames as CN
            for camp in mod.campaigns() if p["table"] else []:
                CN.apply(plan, camp, p["table"])
            plan.delete(p["file"], "the early names-by-culture module - its names are in the campaign script now")
            continue
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
