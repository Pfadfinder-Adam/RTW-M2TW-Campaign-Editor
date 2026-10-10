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


def problems(mod, on_load=False):
    """[{'id', 'why', 'file', 'line', 'new'}] - what would stop the game and can be put right. on_load: what Load
    asks about - not the engine's settings files a mod lacks (the game runs either way; the user, 2026-10-10:
    Check mod files says it, New mod folder puts them in at once)."""
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
            m = re.match(r"^(\s*model_battle_source\s+)text\s*$", code)
            if m and _models_only_in_modeldb(mod):
                out.append({
                    "id": "model_battle_source",
                    "why": "descr_caps_ex.txt reads the battle models from text (model_battle_source text), but this "
                           "mod keeps its own in unit_models/battle_models.modeldb and has no descr_model_battle.txt "
                           "of its own - M2EX then reads the game's descr_model_battle.txt, misses the mod's models "
                           "and closes at start ('Could not find soldier battle model for unit type ...'). Older "
                           "versions of this tool put that line in with the game's copy of the file. The fix: "
                           "model_battle_source modeldb (M2EX's default for mods), nothing else changed.",
                    "file": caps, "line": i, "new": f.text(i).replace(m.group(0), m.group(1) + "modeldb", 1),
                    "note": "model_battle_source: text -> modeldb (the mod's own battle_models.modeldb is read)"})
    missing = [] if on_load else missing_engine_files(mod)
    if missing:
        from .limits import engine_of
        name = engine_of(mod)[:-4]
        out.append({"id": "engine_files", "names": missing,
                    "why": "This mod has no %s of its own, though %s in the game's data. %s reads its "
                           "settings (the faction limit, sprites, models, AI...) only from the mod's own data "
                           "folder - its descr_caps_ex.txt says \"Mods that don't ship this file get safe defaults\", "
                           "so this mod runs on %s's built-in defaults, not on the game's settings. The fix: the "
                           "game's copies go into the mod with every setting line switched off (a ';' before it) - "
                           "the mod runs exactly as now, and each setting can be switched on there for this mod "
                           "alone (the game's own values would change how the mod reads its models, items and "
                           "sprites, and could stop it)."
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
        from . import emergence
        sf = mod.load(sp) if sp and emergence.plain_rome(mod) else None
        dead = [i for i in range(len(sf)) if tokens(strip_comment(sf.text(i)))[:1] in
                (["dead_until_resurrected"], ["re_emergent"])] if sf else []
        if dead:
            out.append({"id": "rome_dead", "file": sp, "rows": dead, "line": 0,
                        "why": "%s's descr_strat.txt line %d: dead_until_resurrected - %s. Older versions of this "
                               "tool wrote it for a faction that comes later. The fix: the line taken out (that "
                               "faction then dies as the campaign loads; the rest of the file is read again), "
                               "nothing else changed." % (camp, dead[0] + 1, emergence.DEAD_ROME)})
        from .diplomacy import foreign_lines
        from .strat import Strat
        foreign = foreign_lines(Strat(mod.load(sp))) if sp else []
        if foreign:
            out.append({"id": "diplomacy_form", "file": sp, "lines": foreign,
                        "why": "%s's descr_strat.txt: %d diplomacy line(s) in the other game's form (e.g. line %d) - "
                               "this game reads none of them, and Medieval II then loses the whole diplomacy at the "
                               "start (every faction neutral). Older versions of this tool wrote them so. The fix: "
                               "the same feelings written in this game's own form, nothing else changed."
                               % (camp, len(foreign), foreign[0][0] + 1)})
    from . import eventimages
    why = eventimages.problem(mod)
    if why:
        out.append({"id": "faction_defeated", "line": 0,
                    "why": why[0].upper() + why[1:] + ". Versions up to 0.29.2 of this tool left it so. The fix: a "
                           "case for every faction (a new one shows the film of the last), nothing else changed."})
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
    if game_kind(mod) == "medieval2":
        from .check import weapons_texture_gaps
        text, db = weapons_texture_gaps(mod)
        if text or db:
            first = (text or db)[0]
            out.append({"id": "weapons_texture", "text": text, "db": db, "line": 0,
                        "why": "%d battle model(s) give a faction its texture but no weapons / shields texture, e.g. "
                               "%s for %s - in battle its men look like bare skeletons (the figure takes half its "
                               "picture from that texture). Older versions of this tool and other tools left it so. "
                               "The fix: each such faction gets the weapons texture the model's other factions wear "
                               "(the mercenaries', else the first), nothing else changed."
                               % (len(text) + len(db), first[0], ", ".join(first[1][:3]))})
    try:                                            # add-ons in the game older than this editor's
        from . import addons as AD
        found = AD.outdated(mod)
    except Exception:
        found = []
    if found:
        import hashlib
        names = [o["addon"].title for o in found]
        # the id carries the versions: a 'Not now' is not remembered past the next editor with other scripts
        key = hashlib.md5("".join(o["addon"].template() for o in found).encode("utf-8")).hexdigest()[:8]
        one = len(found) == 1
        out.append({"id": "old_addons_" + key, "addons": found, "line": 0,
                    "why": "%s in the game %s an older version than this editor's - an older one could draw the "
                           "game's script console in its own font and write 'font autoscale: game font ...' there. "
                           "The fix: %s put in again in this version, with the settings %s has now (Add-ons > "
                           "Update it does the same, one at a time)."
                           % (", ".join(names), "is" if one else "are", "it is" if one else "they are",
                              "it" if one else "each")})
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


# the engines' settings files: each line overrides a built-in default, a missing file = every default ("This file is
# optional - delete it to use defaults"); the other *_ex files (lighting, day types, AI) change how the game reads
# its own files when they are there, so they are never copied into a mod
ENGINE_SETTINGS = ("descr_ex.txt", "descr_caps_ex.txt")


def _models_only_in_modeldb(mod):
    """True when the mod has its own battle_models.modeldb and no descr_model_battle.txt of its own."""
    units = _ci(mod.data, "unit_models")
    own_db = _ci(units, "battle_models.modeldb") if units and os.path.isdir(units) else None
    return bool(own_db) and not _ci(mod.data, "descr_model_battle.txt")


def settings_off(raw):
    """A settings file's bytes with every setting line switched off (';' before it); comments, blank lines and the
    line ends kept - the engine then runs on its built-in defaults, as with no file."""
    out = []
    for line in raw.splitlines(True):
        body = line.rstrip(b"\r\n")
        out.append(b";" + line if body.split(b";", 1)[0].strip() else line)
    return b"".join(out)


def engine_files_words(mod):
    """Check mod files' line about the engine's settings files the mod lacks ('' when none) - check.FIXES gives it
    the button that copies them in (App.copy_engine_files)."""
    from .limits import engine_of
    missing = missing_engine_files(mod)
    if not missing:
        return ""
    name = engine_of(mod)[:-4]
    return ("the mod has no %s of its own (the game's data has) - %s runs it on its built-in defaults, as it does "
            "now; copy them in to set this mod's own engine settings (every line switched off, the mod runs as "
            "before)" % (", ".join(missing), name))


def engine_settings_into(data, game_data):
    """The engine's settings files (ENGINE_SETTINGS) the game's data has and data lacks, copied into data with every
    setting switched off (settings_off - the mod runs as on the engine's defaults) -> [names]. New mod folder."""
    out = []
    try:
        names = sorted(n for n in os.listdir(game_data) if n.lower() in ENGINE_SETTINGS
                       and os.path.isfile(os.path.join(game_data, n)))
    except OSError:
        return out
    for n in names:
        if _ci(data, n):
            continue
        with open(os.path.join(game_data, n), "rb") as fh:
            raw = settings_off(fh.read())
        with open(os.path.join(data, n), "wb") as fh:
            fh.write(raw)
        out.append(n)
    return out


def missing_engine_files(mod):
    """The engine's settings files (descr_ex.txt, descr_caps_ex.txt) the game's data has and this mod's data lacks
    - only for a mod (not the game's own data) of a game with REX / M2EX."""
    from .limits import engine_of
    from .newmod import game_of
    game = game_of(mod.data)
    gdata = _ci(game, "data") if game else None
    if not gdata or os.path.normcase(os.path.abspath(gdata)) == os.path.normcase(os.path.abspath(mod.data)):
        return []
    if not engine_of(mod):
        return []
    try:
        names = sorted(n for n in os.listdir(gdata) if n.lower() in ENGINE_SETTINGS
                       and os.path.isfile(os.path.join(gdata, n)))
    except OSError:
        return []
    return [n for n in names if not _ci(mod.data, n)]   # the engines read these from the mod alone


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
                    plan.binary(os.path.join(mod.data, n), settings_off(fh.read()))
                plan.note(None, "%s copied from the game's data into the mod, every setting switched off (the mod "
                                "runs on the engine's defaults, as before; remove the ';' to switch one on)" % n)
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
        if p["id"] == "rome_dead":
            f = plan.edit(p["file"])
            for i in reversed(p["rows"]):
                f.delete(i, i + 1)
            plan.note(f, "%d dead_until_resurrected / re_emergent line(s) taken out (plain Rome stops reading "
                         "the file at them)" % len(p["rows"]))
            continue
        if p["id"] == "diplomacy_form":
            f = plan.edit(p["file"])
            for i, text in p["lines"]:
                f.set(i, text)
            plan.note(f, "%d diplomacy line(s) written in this game's own form" % len(p["lines"]))
            continue
        if p["id"] == "weapons_texture":
            from .packs import _block_lines, _owner_textures, type_blocks
            from .models import TEXT_FILE
            if p["text"]:
                f = plan.edit(mod.find(TEXT_FILE))
                for name, facs in p["text"]:
                    blocks = type_blocks(f)
                    if name in blocks:
                        a, b = blocks[name]
                        now = _block_lines(f, (a, b))
                        got, _ = _owner_textures(now, facs)
                        f.raw[a:a + len(now)] = [f.make(x) for x in got]
                plan.note(f, "%d model(s): a weapons texture line for the factions that had none" % len(p["text"]))
            if p["db"]:
                from . import modeldb as MDB
                src, dst = MDB.find(mod)
                db = MDB._db_in_plan(plan, src, dst)
                for name, facs in p["db"]:
                    m = db.model(name)
                    if m is not None:
                        MDB.give_owners(m, facs)
                plan.binary(dst, db.dump().encode("latin-1"))
                plan.notes.append((mod.rel(dst), "%d model(s): a weapons texture for the factions that had none"
                                   % len(p["db"])))
            continue
        if p["id"] == "faction_defeated":
            from . import eventimages
            eventimages.keep_up(plan)
            continue
        if p["id"].startswith("old_addons"):
            from . import addons as AD
            AD.plan_update(plan, p["addons"], mod)
            continue
        if p["id"] == "old_culture_names":
            from . import culturenames as CN
            for camp in mod.campaigns() if p["table"] else []:
                CN.apply(plan, camp, p["table"])
            plan.delete(p["file"], "the early names-by-culture module - its names are in the campaign script now")
            continue
        f = plan.edit(p["file"])
        f.set(p["line"], p["new"])
        plan.note(f, p.get("note") or "%s: text -> binary (the game started without it closing)" % p["id"])
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


# the Kingdoms campaigns' folders and the names of their unpack scripts in tools/unpacker
KINGDOMS_BATS = {"americas": "americas", "british_isles": "britannia", "crusades": "crusades", "teutonic": "teutonic"}


def _campaign_folder(path):
    """(game folder, campaign folder) when path is a Medieval II Kingdoms campaign (or any mod) with packs of its own:
    <game>/mods/<name>[/data]; else None."""
    path = os.path.abspath(path)
    for cand in (path, os.path.dirname(path)):
        parent = os.path.dirname(cand)
        if os.path.basename(parent).lower() == "mods" and os.path.isdir(os.path.join(cand, "packs")):
            return os.path.dirname(parent), cand
    return None


def unpack_needed(path):
    """{'game', 'unpacker', 'bat', 'dlls': [missing next to the unpacker], 'packs', 'data': the folder to load
    afterwards, 'campaign': a Kingdoms campaign's folder name or ''} when path (the game, its data folder or a
    Kingdoms campaign's folder - mods/british_isles...) is a Medieval II with its files still in packs; else None.
    Steam's Medieval II comes packed; a campaign's folder holds only its own few files until its packs are unpacked
    (tools/unpacker/unpack_britannia.bat and the like)."""
    camp = _campaign_folder(path)
    if camp:
        game, folder_c = camp
        data = os.path.join(folder_c, "data")
        name = os.path.basename(folder_c)
        if not _ci(data, "descr_sm_factions.txt"):
            folder = os.path.join(game, "tools", "unpacker")
            exe = _ci(folder, "unpacker.exe")
            bat = _ci(folder, "unpack_%s.bat" % KINGDOMS_BATS.get(name.lower(), name))
            packs = [n for n in os.listdir(os.path.join(folder_c, "packs")) if n.lower().endswith(".pack")]
            if exe and packs:
                return {"game": game, "unpacker": exe, "bat": bat, "packs": len(packs), "data": data,
                        "campaign": name, "dlls": [d for d in UNPACK_DLLS if not _ci(folder, d)],
                        "source": "../../mods/%s/packs/*.pack" % name, "base": "mods/%s/data/" % name}
        return None
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
            "dlls": [d for d in UNPACK_DLLS if not _ci(folder, d)], "packs": len(packs),
            "data": os.path.join(game, "data"), "campaign": ""}


def unpacker_missing(path):
    """The plain words to show when path is a Medieval II (or a Kingdoms campaign) with its files still in packs but
    no unpacker in <game>/tools/unpacker to unpack them with; else ''."""
    camp = _campaign_folder(path)
    if camp:
        game, folder_c = camp
        if _ci(os.path.join(folder_c, "data"), "descr_sm_factions.txt"):
            return ""
        packs = os.path.join(folder_c, "packs")
        what = "This Medieval II campaign (%s)" % os.path.basename(folder_c)
    else:
        game = _game_folder(path)
        if not game or _ci(os.path.join(game, "data"), "descr_sm_factions.txt"):
            return ""
        packs = os.path.join(game, "packs")
        what = "This Medieval II"
    if not any(n.lower().endswith(".pack") for n in os.listdir(packs)):
        return ""
    if _ci(os.path.join(game, "tools", "unpacker"), "unpacker.exe"):
        return ""
    return ("%s is not unpacked yet: its files are still in .pack files, and the game's own unpacker is not there "
            "to unpack them (%s).\n\nSteam puts it there with the game: in Steam right click Medieval II: Total War > "
            "Properties > Installed Files > Verify integrity of game files - it brings back what is missing. Or copy "
            "the folder tools\\unpacker from another Medieval II.\n\nThen press Load again - the editor offers to "
            "unpack it.") % (what, os.path.join(game, "tools", "unpacker", "unpacker.exe"))


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
        cmd = [need["unpacker"], "--source=%s" % need.get("source", "../../packs/*.pack"), "--destination=../../"]
        if need.get("base"):
            cmd.append("--base_pack_path=%s" % need["base"])
    # the unpacker first asks 'Do you agree to these terms and conditions? (Y/N)' - 'y' answers it (a newline alone
    # left it waiting and nothing was unpacked: a tester's Kingdoms campaign); the batch ends with 'pause': newlines
    run = subprocess.run(cmd, cwd=folder, input=b"y\r\ny\r\n\r\n\r\n", stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    out = run.stdout.decode("latin-1", "replace")
    data = need.get("data") or os.path.join(need["game"], "data")
    if not _ci(data, "descr_sm_factions.txt"):
        raise RuntimeError("the unpacker ran (exit %s) but %s is still missing:\n%s"
                           % (run.returncode, os.path.join(data, "descr_sm_factions.txt"), out[-2000:]))
    return out


__all__ = ["problems", "fix_plan", "unpack_needed", "unpacker_missing", "unpack"]


def grouped_words(found):
    """The problems in words, the same one on many lines of a file said once with its lines ('lines 5, 13, 21 ...
    - 23 lines'): a tester's mod had one mistake on 23 lines of descr_win_conditions.txt and the list ran off the
    screen."""
    groups = {}
    for p in found:
        why = p["why"]
        m = re.search(r"\bline (\d+)\b", why)
        key = re.sub(r"\bline \d+\b", "line #", why, count=1) if m else why
        groups.setdefault(key, []).append(int(m.group(1)) if m else None)
    out = []
    for key, lines in groups.items():
        nums = [n for n in lines if n is not None]
        if len(nums) > 1:
            shown = ", ".join(str(n) for n in nums[:8]) + (" ..." if len(nums) > 8 else "")
            out.append(key.replace("line #", "lines %s (%d lines)" % (shown, len(nums)), 1))
        else:
            out.append(key.replace("line #", "line %d" % nums[0], 1) if nums else key)
    return out
