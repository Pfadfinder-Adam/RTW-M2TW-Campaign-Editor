"""The game's own campaign-map editor, used beside ours (the user, 2026-10-15: 'a strong extra - keep ours').

What the game's editor does (read from the exes, modding_knowledge.md 'Deep study 2026-10-15' - not tried in a game):
it opens only data/world/maps/campaign/custom/<name>/ and, on Save, writes the whole campaign there again from
memory - descr_strat.txt without its 'script' line, without comments or anything it could not read, and the map's
pictures. So the work goes in three steps, the web's knots tied here in one place:

  prepare     the campaign's text files and its map files (the campaign's own, else the base ones, as the game finds
              them) copied into custom/<name>/ with a note of what each was (campaign_editor.json); the region names'
              text as text/<name>_regions_and_settlement_names.txt. Through a Plan: Restore takes it all out.
  start_line  the game started straight in its editor where it can be: Medieval II with M2EX
              '--editor.campaign=custom/<name>'; Rome (with REX too - no such switch in its exe) and plain Medieval II
              only show the editor in their menus ('-enable_editor' for Rome; Medieval II's cfg
              '[features] editor = true').
  take_back   every file the game's editor saved and changed goes back over the campaign's own (into the mod: the
              campaign folder, or where the mod's own file lay), descr_strat.txt with its 'script' lines put back,
              map.rwm removed (the game builds it again) - and what the editor dropped is said: header keys,
              factions, towns, characters fewer than before."""

import hashlib
import json
import os
import re

NOTE = "campaign_editor.json"
# what the game's editor writes on Save (and so what may come back)
SAVED = ("descr_strat.txt", "descr_regions.txt", "descr_regions_and_settlement_name_lookup.txt", "map_regions.tga",
         "map_features.tga", "map_climates.tga", "map_ground_types.tga", "descr_terrain.txt", "map_heights.tga",
         "map_heights.hgt", "map_heights_ex.png", "map_trade_routes.tga", "map_roughness.tga")
# the map files the campaign is built from (its own, else world/maps/base) - copied so the editor builds the same map
MAP_FILES = ("descr_regions.txt", "descr_terrain.txt", "descr_disasters.txt", "descr_sounds_music_types.txt",
             "map_regions.tga", "map_features.tga", "map_climates.tga", "map_ground_types.tga", "map_heights.tga",
             "map_heights.hgt", "map_heights_ex.png", "map_trade_routes.tga", "map_roughness.tga", "map_fog.tga",
             "map_fe.tga", "water_surface.tga")


def folder_name(campaign):
    """The custom campaign's folder name for a campaign: ce_<campaign> (letters, digits and _ only)."""
    return "ce_" + re.sub(r"[^A-Za-z0-9_]", "_", campaign)


def custom_dir(mod, campaign):
    """data/world/maps/campaign/custom/<name> of THIS mod (the game looks in the mod's data first)."""
    return os.path.join(mod.data, "world", "maps", "campaign", "custom", folder_name(campaign))


def _inside(mod, path):
    data = os.path.normcase(os.path.abspath(mod.data))
    return os.path.normcase(os.path.abspath(path)).startswith(data + os.sep)


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


def _names_text(mod, campaign):
    try:
        return mod.text_file("%s_regions_and_settlement_names.txt" % campaign)
    except Exception:
        return None


def prepare(plan, campaign):
    """The campaign copied for the game's editor (see the module's words). Returns the custom folder."""
    mod = plan.mod
    dst = custom_dir(mod, campaign)
    note = {"campaign": campaign, "files": {}, "text": None}
    own = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt") or "")
    names = set()
    if own and os.path.isdir(own):
        names |= {n for n in os.listdir(own) if n.lower().endswith(".txt")}
    names |= set(MAP_FILES)
    for name in sorted(names, key=str.lower):
        src = mod.campaign_file(campaign, name)
        if not src or not os.path.isfile(src):
            continue
        plan.copy(src, os.path.join(dst, name))
        note["files"][name] = {"from": src, "sha1": _sha(src)}
    txt = _names_text(mod, campaign)
    if txt and os.path.isfile(txt):
        new_name = "%s_regions_and_settlement_names.txt" % folder_name(campaign)
        if _inside(mod, txt):
            there = os.path.join(os.path.dirname(txt), new_name)
        else:                                       # the game's text under a thin mod: the copy goes into the mod
            there = os.path.join(mod.data, "text", new_name)
        plan.copy(txt, there)
        note["text"] = {"from": txt, "to": there, "sha1": _sha(txt)}
    plan.binary(os.path.join(dst, NOTE), json.dumps(note, indent=1).encode("utf-8"))
    plan.note(None, "the campaign %s copied for the game's editor into %s (%d files) - Restore takes it out" % (
        campaign, mod.rel(dst), len(note["files"])))
    return dst


def read_note(mod, campaign):
    p = os.path.join(custom_dir(mod, campaign), NOTE)
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def start_line(data, campaign):
    """{'exe', 'args', 'cwd', 'words', 'direct'}: the game started in its campaign-map editor (direct True) or the
    plain game with its editor shown in the menus (direct False, 'how' says where to click). ValueError without a
    game exe."""
    from .launch import start_line as game_line, EXPANSIONS
    from .newmod import game_of, game_root_of, is_medieval2
    data = os.path.abspath(data)
    game = game_of(data)
    _, base = game_root_of(data)
    where = "custom/%s" % folder_name(campaign)
    m2 = is_medieval2(game)
    if m2:
        if os.path.isfile(os.path.join(game, "M2EX.exe")):
            args = (["--features.mod=mods/%s" % base] if base else []) + ["--editor.campaign=%s" % where]
            return {"exe": os.path.join(game, "M2EX.exe"), "args": args, "cwd": game, "direct": True,
                    "words": " ".join(["M2EX.exe"] + args), "how": ""}
        line = game_line(data)
        line.update(direct=False, how="Medieval II without M2EX opens its editor only from its menus: add the lines "
                    "'[features]' and 'editor = true' to the mod's .cfg (or the game's medieval2.preference.cfg), "
                    "then in the game: the editors in the main menu > the campaign map editor > load %s." % where)
        return line
    low = (base or "").lower()
    rel = None
    if base:
        rel = os.path.relpath(os.path.dirname(data), game).replace(os.sep, "/")
    mod_args = [EXPANSIONS[low][0]] if low in EXPANSIONS else (["-nm", "-show_err", "-mod:%s" % rel] if base else [])
    # Rome, with REX too: no switch opens the campaign editor straight away (REX.exe's command line knows strat,
    # battle, battle_ed and enable_editor - 'strat_ed' is only a keyboard-shortcut set), so -enable_editor shows it
    # in the menus and the words say where to click
    rex = os.path.isfile(os.path.join(game, "REX.exe"))
    exe = "REX.exe" if rex else EXPANSIONS[low][1] if low in EXPANSIONS else "RomeTW.exe"
    if not os.path.isfile(os.path.join(game, exe)):
        raise ValueError("no game exe (REX.exe, %s) in %s" % (exe, game))
    args = mod_args + ["-enable_editor"]
    return {"exe": os.path.join(game, exe), "args": args, "cwd": game, "direct": False,
            "words": " ".join([exe] + args),
            "how": "Rome%s opens its editor only from its menus: in the game, the editors' entry of the main menu > "
                   "the campaign map editor > load custom campaign %s." % (" with REX" if rex else " without REX",
                                                                          folder_name(campaign))}


# ---- taking it back ----
RE_KEY = re.compile(r"^\s*([A-Za-z_]+)")


def _code_lines(text):
    out = []
    for line in text.splitlines():
        line = line.split(";", 1)[0].rstrip()
        if line.strip():
            out.append(line)
    return out


def _counts(text):
    """{keyword: how many} of descr_strat's lines that make things (the first word of each code line)."""
    out = {}
    for line in _code_lines(text):
        m = RE_KEY.match(line)
        if m:
            out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


def _script_lines(text):
    """The 'script' line and the file name after it (Medieval II and Rome: 'script' on its own line, then the
    file; or both on one line) - [] when there is none."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        t = line.split(";", 1)[0].split()
        if t and t[0] == "script":
            if len(t) > 1:
                return [line]
            nxt = next((x for x in lines[i + 1:] if x.split(";", 1)[0].strip()), None)
            return [line] + ([nxt] if nxt is not None else [])
    return []


def _decode(data):
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), "latin-1"


def strat_back(old, new):
    """(new descr_strat bytes with what the editor drops put back, [what was dropped, in words]). old / new bytes."""
    old_t, _ = _decode(old)
    new_t, enc = _decode(new)
    said = []
    script = _script_lines(old_t)
    if script and not _script_lines(new_t):
        nl = "\r\n" if "\r\n" in new_t else "\n"
        new_t = new_t.rstrip("\r\n") + nl + nl + nl.join(script) + nl
        said.append("the 'script' lines (%s) put back - the game's editor does not save them" % " / ".join(
            s.strip() for s in script))
    a, b = _counts(old_t), _counts(new_t)
    for key in ("faction", "settlement", "character", "character_record", "army", "navy", "resource", "landmark",
                "region", "building", "unit", "relative", "core_attitudes", "faction_relationships"):
        if b.get(key, 0) < a.get(key, 0):
            said.append("%s: %d before, %d now" % (key, a[key], b.get(key, 0)))
    for key in sorted(a):
        if key not in b and key not in ("script",) and a[key] <= 3:
            said.append("'%s' is gone" % key)
    return new_t.encode(enc), said


def changed(mod, campaign):
    """[(name, path in custom/, sha1 there)] the game's editor saved and changed since prepare."""
    note = read_note(mod, campaign)
    if not note:
        return []
    dst = custom_dir(mod, campaign)
    out = []
    for name in SAVED:
        p = os.path.join(dst, name)
        if not os.path.isfile(p):
            continue
        sha = _sha(p)
        was = note["files"].get(name, {}).get("sha1")
        if sha != was:
            out.append((name, p, sha))
    return out


def _target(mod, campaign, name, note):
    """Where a file comes back: where the mod's own one lay, else the mod's campaign folder (the game reads a map
    file there before world/maps/base - only this campaign changes)."""
    was = note["files"].get(name, {}).get("from")
    if was and _inside(mod, was):
        return was
    return os.path.join(mod.data, "world", "maps", "campaign", campaign, name)


def take_back(plan, campaign):
    """What the game's editor saved, back into the campaign (see the module's words). Returns the files taken."""
    mod = plan.mod
    note = read_note(mod, campaign)
    if not note:
        raise ValueError("the campaign was not opened in the game's editor from here (no %s in %s)" % (
            NOTE, mod.rel(custom_dir(mod, campaign))))
    got = changed(mod, campaign)
    taken = []
    for name, p, _ in got:
        with open(p, "rb") as fh:
            data = fh.read()
        target = _target(mod, campaign, name, note)
        if name == "descr_strat.txt":
            src = note["files"].get(name, {}).get("from")
            old = b""
            if src and os.path.isfile(src):
                with open(src, "rb") as fh:
                    old = fh.read()
            data, said = strat_back(old, data)
            for s in said:
                plan.warn(None, "descr_strat.txt from the game's editor: %s" % s)
        plan.binary(target, data)
        taken.append(name)
    text = note.get("text")
    if text and os.path.isfile(text.get("to", "")) and _sha(text["to"]) != text.get("sha1"):
        with open(text["to"], "rb") as fh:
            plan.binary(text["from"] if _inside(mod, text["from"])
                        else os.path.join(mod.data, "text", os.path.basename(text["from"])), fh.read())
        taken.append(os.path.basename(text["from"]))
    if any(n.endswith((".tga", ".hgt", ".png")) or n in ("descr_regions.txt", "descr_terrain.txt") for n in taken):
        for where in (os.path.join(mod.data, "world", "maps", "campaign", campaign),
                      os.path.join(mod.data, "world", "maps", "base")):
            rwm = os.path.join(where, "map.rwm")
            if os.path.isfile(rwm):
                plan.delete(rwm, "the game builds it again from the map's pictures on the next start")
    if taken:
        plan.note(None, "from the game's editor: %s" % ", ".join(taken))
    return taken


def remove(plan, campaign):
    """The opposite of prepare: the copy for the game's editor taken out (its files and the names' text copy)."""
    mod = plan.mod
    note = read_note(mod, campaign) or {}
    dst = custom_dir(mod, campaign)
    if os.path.isdir(dst):
        for name in sorted(os.listdir(dst)):
            p = os.path.join(dst, name)
            if os.path.isfile(p):
                plan.delete(p, "the copy for the game's editor taken out")
    text = (note.get("text") or {}).get("to")
    if text and os.path.isfile(text):
        plan.delete(text, "the copy for the game's editor taken out")
