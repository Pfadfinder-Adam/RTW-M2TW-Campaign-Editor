"""The game's own campaign-map editor, used beside ours (the user, 2026-10-15: 'a strong extra - keep ours').

What the game's editor does (read from the exes, modding_knowledge.md 'Deep study 2026-10-15' - not tried in a game):
it opens only data/world/maps/campaign/custom/<name>/ and, on Save, writes the whole campaign there again from
memory - descr_strat.txt without its 'script' line, without comments or anything it could not read, and the map's
pictures. So the work goes in three steps, the web's knots tied here in one place:

  prepare     the campaign's text files and its map files (the campaign's own, else the base ones, as the game finds
              them) copied into custom/<name>/ with a note of what each was (campaign_editor.json); the region names'
              text as text/<name>_regions_and_settlement_names.txt. Through a Plan: Restore takes it all out.
  start_line  the game started straight in its editor where it can be: Medieval II with M2EX
              '--editor.campaign=custom/<name>'; Rome always with its own exe (RomeTW.exe / RomeTW-BI.exe
              -enable_editor -strat_ed:<name>), never REX: REX of 2026-10-05 knows neither switch - its log says
              'unknown option', #299 #301 - and opens the main menu; plain
              Medieval II only from its menus (cfg '[features] editor = true'). The menus' own way is switched off
              in the game's code (#288). opened() reads the game's log after a try: did the editor start?
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
        line.update(direct=False, how="Medieval II without M2EX has no way into its campaign editor: the menu page "
                    "for it is switched off in the game's own code. Start it with M2EX instead (it opens %s "
                    "straight in the editor)." % where)
        return line
    low = (base or "").lower()
    rel = None
    if base:
        rel = os.path.relpath(os.path.dirname(data), game).replace(os.sep, "/")
    # The menus cannot open the campaign editor in either game: OPTIONS > EDITORS > PROVINCIAL CAMPAIGN EDITOR leads
    # to a load page whose list and buttons are switched off in the game's own code, and New Game > PROVINCIAL
    # CAMPAIGN only plays the custom campaigns (report #288; read in the engine source 2026-10-15). Only a switch
    # opens it: CA's Rome builds '-strat_ed:<name>' (under campaign/custom/).
    # Rome: the game's own exe, never REX (the user, 2026-10-16: 'stop trying with REX, make sure the vanilla starts
    # it'): RomeTW.exe / RomeTW-BI.exe hold 'strat_ed' among their switches beside enable_editor; REX of 2026-10-05
    # knows neither it nor --editor.campaign (#299, #301). A Barbarian Invasion mod goes to RomeTW-BI.exe.
    bi = low == "bi" or _bi_data(data, campaign)
    alx = low == "alexander"
    plain = "RomeTW-ALX.exe" if alx else "RomeTW-BI.exe" if bi else "RomeTW.exe"
    if not os.path.isfile(os.path.join(game, plain)):
        raise ValueError("no %s in %s - the game's campaign editor is started with the game's own exe (REX has no "
                         "way into it)" % (plain, game))
    args = ([] if low in EXPANSIONS or not base else ["-show_err", "-mod:%s" % rel]) + \
        ["-enable_editor", "-strat_ed:%s" % folder_name(campaign)]
    return {"exe": os.path.join(game, plain), "args": args, "cwd": game, "direct": True,
            "words": " ".join([plain] + args), "how": PLAIN_HOW}


def _bi_data(data, campaign):
    """A Rome mod of Barbarian Invasion: its campaign barbarian_invasion or BI's own descr_beliefs.txt."""
    return campaign.lower() == "barbarian_invasion" or any(
        n.lower() == "descr_beliefs.txt" for n in (os.listdir(data) if os.path.isdir(data) else []))


PLAIN_HOW = ("Started with the game's own exe, without REX (REX has no way into the campaign editor). A mod made "
             "for REX only may not start on the plain game - try the game's own campaign first (load its data "
             "folder: data, or bi/data for Barbarian Invasion).")

def opened(text):
    """Did the game's start open its campaign editor? From its log (system.log.txt): True when the log says
    'STARTING CAMPAIGN EDITOR', False when the game ran without it, None when the log says nothing either way."""
    if not text:
        return None
    if "STARTING CAMPAIGN EDITOR" in text:
        return True
    if re.search(r"unknown option: --?(editor\.campaign|strat_ed)", text) or "Loading string table" in text:
        return False
    return None


def last_try(game, mod_dir, since):
    """opened() of the newest game log written after `since` (a time.time()), None without one."""
    from .report import game_logs
    for p in game_logs(game, mod_dir) if game else []:
        try:
            if os.path.getmtime(p) < since:
                continue
            with open(p, "rb") as fh:
                return opened(fh.read().decode("latin-1", errors="replace"))
        except OSError:
            continue
    return None


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


def _lists_span(text):
    """(start, end, text) of the playable ... nonplayable lists' lines at the file's top (from the 'playable' line
    to the 'end' after 'nonplayable', or the last list's 'end'), else None."""
    lines = text.splitlines(keepends=True)
    pos, start, end, open_ = 0, None, None, None
    for l in lines:
        w = l.split(";")[0].split()
        head = w[0] if w else ""
        if head in ("playable", "unlockable", "nonplayable") and open_ is None:
            if start is None:
                start = pos
            open_ = head
        elif head == "end" and open_:
            end = pos + len(l)
            if open_ == "nonplayable":
                break
            open_ = None
        elif head and open_ is None and start is not None:
            break
        pos += len(l)
    return (start, end, text[start:end]) if start is not None and end else None


def _lists_of(text):
    """{list: [factions]} of the lists' text (_lists_span) - to see whether two files list the same."""
    out, cur = {}, None
    for l in text.splitlines():
        w = l.split(";")[0].split()
        if not w:
            continue
        if w[0] in ("playable", "unlockable", "nonplayable"):
            cur = out.setdefault(w[0], [])
        elif w[0] == "end":
            cur = None
        elif cur is not None:
            cur.append(w[0].rstrip(","))
    return out


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
    lists = _lists_span(old_t)
    if lists:
        now = _lists_span(new_t)
        if now and _lists_of(now[2]) != _lists_of(lists[2]):
            new_t = new_t[:now[0]] + lists[2] + new_t[now[1]:]
            said.append("the playable / unlockable / nonplayable lists put back as they were - the game's editor "
                        "rewrites them from memory (an undiscovered faction it lists as playable stops Medieval II)")
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
