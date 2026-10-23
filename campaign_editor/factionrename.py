"""Rename a faction everywhere (the faction's code name - romans_julii, england - the one the files use; the names
players read are changed on the Faction tab). Both games.

What follows the new name, in one plan (Preview lists every line; one backup, Restore gives it all back):
- every text file of the mod's data (descr_sm_factions, descr_strat of every campaign, descr_names, the unit and
  building files, descr_character, descr_model_*, banners, win conditions, regions, events, mercenaries, traits,
  ancillaries, sounds, Medieval II's XML lists...): the faction's name as a word of its own (in any case, as the game
  reads it - the new name written in the case found; a
  name glued to more by '_' or standing in a file path - egypt_chariot, symbol_egypt.tga, ui/units/egypt/ - is not
  the faction and is not touched);
- every campaign folder's leader_pic_, description_, vc_ and vcs_ files of the faction (the game finds them by its
  name) copied under the new name;
- its pictures (ui, menu, loading_screen, the campaign folder: files and folders named after it) copied under the new
  name (clone.art_files) and every line naming such a file by path pointed at the copy; the old files stay - nothing
  reads them any more;
- the string tables: every key holding the faction's name ({EGYPT}, {IMPERIAL_CAMPAIGN_EGYPT_TITLE}) copied under the
  new name (clone.text_strings), the old keys stay;
- Medieval II's battle_models.modeldb: its texture entries for the faction renamed.
- the campaign scripts (campaign_script.txt and the like - the game's own script words): the name as a word of its
  own, as in the data files (report #186: venice renamed, 'I_LocalFaction venice' left - the game logged
  "'venice' is not a known faction" thousands of times);
Not changed, only listed: Lua / Squirrel scripts naming it (code - a blind change there can break it)."""

import os
import re

from . import clone as C

RE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
TEXT_EXT = (".txt", ".xml", ".json")
SCRIPT_NAMES = ("campaign_script", "be_script", "four_turns")
SKIP_DIRS = ("text",)                       # string tables: their keys are copied (clone.text_strings)


def _word(name):
    """The faction as a word of its own: not glued by '_' and not part of a path or a file name - in any case, as the
    game reads it (faction_type_from_string ignores case: a 'Venice' left in descr_strat stops the game)."""
    return re.compile(r"(?<![A-Za-z0-9_/\\.])%s(?![A-Za-z0-9_/\\.])" % re.escape(name), re.I)


def _cased(new, found, old=None):
    """new written in the case the old name was found in (VENICE -> MILAN, Venice -> Milan, venice -> milan); the
    name spelled as the faction is (old) takes the new name as given."""
    if found == old:
        return new
    if found.isupper() and not found.islower():
        return new.upper()
    if found[:1].isupper():
        return new.capitalize()
    return new


# pictures and texts of a campaign folder the game finds by the faction's name, no line naming them
# (menu_components.cpp: the select screen's leader picture and description; faction_scrolls.cpp: the victory scrolls)
RE_CAMPAIGN_OWN = r"^(leader_pic_|description_|vc_|vcs_)(%s)(\.(?:tga|dds|png|txt))$"


def _campaign_files(plan, old, new):
    """Every campaign's own pictures and texts of the faction (not only the campaign the rename was started from)
    copied under the new name, unless the plan or the mod already has one there."""
    mod = plan.mod
    rx = re.compile(RE_CAMPAIGN_OWN % re.escape(old), re.I)
    taken = {os.path.normcase(os.path.abspath(d)) for _, d in plan.copies}
    for campaign in mod.campaigns():
        for folder in (mod.campaign_dirs(campaign) if hasattr(mod, "campaign_dirs") else []):
            mine = os.path.join(mod.campaign_root, campaign)
            for n in sorted(os.listdir(folder)):
                m = rx.match(n)
                if not m:
                    continue
                dst = os.path.join(mine, m.group(1) + new + m.group(3))
                key = os.path.normcase(os.path.abspath(dst))
                if key in taken or os.path.exists(dst):
                    continue
                taken.add(key)
                plan.copy(os.path.join(folder, n), dst)


# words the games read in a faction's place with a meaning of their own (building_battle 'all' / 'any', descr_names
# 'dummy', the modeldb's 'merc' / 'default', the movie tracks' 'none', the scripts' 'local' / 'target')
RESERVED = ("slave", "all", "any", "none", "default", "merc", "dummy", "local", "target")
# names the exes look for themselves: what a rename takes away (game_rtw / game sources, 2026-10-23 study)
HARD_CODED = {
    "romans_senate": "the Senate (its missions, its scroll) is found by this name",
    "romans_julii": "the Senate scroll, its missions and the outlaw / civil war messages name the Roman houses",
    "romans_brutii": "the Senate scroll, its missions and the outlaw / civil war messages name the Roman houses",
    "romans_scipii": "the Senate scroll, its missions and the outlaw / civil war messages name the Roman houses",
    "romano_british": "its revolt / comeback looks for this name - without it the game can crash then",
    "slavs": "its emergence looks for this name - without it the game can crash then",
    "empire_west": "the Roman empire's split looks for this name",
    "empire_east": "the Roman empire's split looks for this name",
    "huns": "the Huns' arrival message looks for this name",
}


def problems(mod, old, new):
    """Why the faction cannot be renamed so, or None."""
    names = [n for n, _ in mod.factions()]
    if old not in names:
        return "%s is not a faction of descr_sm_factions.txt" % old
    if old == "slave":
        return "the rebels (slave) keep their name - the games look for it"
    if not RE_NAME.match(new or ""):
        return "a faction's code name is lower-case letters, digits and _, starting with a letter"
    if new.lower() in [n.lower() for n in names] or new == old:
        return "%s is already a faction of this mod" % new
    if new in RESERVED:
        return "'%s' is a word the game reads with a meaning of its own where a faction stands - pick another" % new
    cultures = {(mod.culture(n) or "").lower() for n in names}
    if new in cultures:
        return ("'%s' is a culture - a faction of that name hides the culture in the units, buildings and regions "
                "files (the game tries a faction first)" % new)
    return None


def _is_script(path):
    low = os.path.basename(path).lower()
    return low.endswith((".lua", ".nut")) or any(low.startswith(s) for s in SCRIPT_NAMES)


def _text_files(mod, campaign):
    """Every text file of the data folder but the string tables, scripts apart - the mod's, and the game's own data
    under a mod folder that keeps only what it changes (a file only the game has is read from there; the edit is
    written as the mod's own copy). A file the mod has hides the game's of the same place."""
    out, scripts, seen = [], [], set()
    script_names = {os.path.normcase(p) for p in _strat_scripts(mod)}
    for root in (mod.roots() if hasattr(mod, "roots") else [mod.data]):
        for dirpath, dirs, files in os.walk(root):
            rel = os.path.relpath(dirpath, root).replace("\\", "/").lower()
            if rel.split("/")[0] in SKIP_DIRS:
                dirs[:] = []
                continue
            for n in files:
                p = os.path.join(dirpath, n)
                key = os.path.normcase(os.path.relpath(p, root))
                if key in seen:
                    continue
                seen.add(key)
                if os.path.normcase(p) in script_names or _is_script(p):
                    scripts.append(p)
                elif n.lower().endswith(TEXT_EXT):
                    out.append(p)
    return sorted(out), sorted(scripts)


def _strat_scripts(mod):
    from .upscale import script_files
    out = []
    for c in mod.campaigns():
        try:
            out += script_files(mod, c)
        except Exception:
            pass
    return out


def plan_rename(plan, campaign, old, new):
    """Fill the plan; returns the lines (file: line numbers) of scripts naming the faction - left to check by hand."""
    mod = plan.mod
    why = problems(mod, old, new)
    if why:
        raise ValueError(why)
    plan.template, plan.new = old, new
    if old.lower() in HARD_CODED:
        plan.warn(None, "%s is a name the game itself looks for: %s - renamed, that is gone"
                  % (old, HARD_CODED[old.lower()]))
    # 1. its pictures under the new name; the paths that name them follow
    C.art_files(plan, campaign)
    _campaign_files(plan, old, new)
    moved = []
    for src, dst in plan.copies:
        a = os.path.relpath(src, mod.data).replace("\\", "/")
        b = os.path.relpath(dst, mod.data).replace("\\", "/")
        if not a.startswith(".."):
            moved.append((a, b))
    moved.sort(key=lambda m: -len(m[0]))
    rx = _word(old)
    rx_xml = re.compile(r'(\bfaction\s*=\s*")(%s)(")' % re.escape(old), re.I)
    # the traits' effect against a faction glues its name on, in any case: Combat_V_Faction_Venice (a report: the
    # game closed at start - 'Unknown attribute type(Combat_V_Faction_Venice)' after venice was renamed)
    # REX also takes Combat_V_<faction> (game_rtw string_recognition.cpp: a name no faction has falls back to
    # InfantryCommand, silently)
    rx_glued = re.compile(r"(\bCombat_V_(?:Faction_)?)(%s)(?![A-Za-z0-9_])" % re.escape(old), re.I)
    files, scripts = _text_files(mod, campaign)
    total = 0
    for p in files:
        with open(p, "rb") as fh:
            raw = fh.read()
        if b"\0" in raw[:2048]:
            continue                                    # a UTF-16 / binary file under a text name: not ours
        text = raw.decode("latin-1")
        low = text.lower()
        if old.lower() not in low and not any(a.lower() in low for a, _ in moved):
            continue
        f = plan.edit(p)
        n = 0
        for i in range(len(f.raw)):
            t = f.text(i)
            new_t = rx.sub(lambda m: _cased(new, m.group(), old), t)
            new_t = rx_glued.sub(lambda m: m.group(1) + (new.capitalize() if m.group(2)[:1].isupper() else new), new_t)
            if p.lower().endswith(".xml"):            # Medieval II's XML lists: Faction="Milan" - any case
                new_t = rx_xml.sub(lambda m: m.group(1) + (new.capitalize() if m.group(2)[:1].isupper() else new)
                                   + m.group(3), new_t)
            for a, b in moved:                          # a path to a picture that was copied: to the copy
                for sa, sb in ((a, b), (a.replace("/", "\\"), b.replace("/", "\\"))):
                    k = new_t.lower().find(sa.lower())
                    while k >= 0:
                        new_t = new_t[:k] + sb + new_t[k + len(sa):]
                        k = new_t.lower().find(sa.lower(), k + len(sb))
            if new_t != t:
                f.set(i, new_t)
                n += 1
        if n:
            plan.note(f, "%d line(s): %s -> %s" % (n, old, new))
            total += n
    # 2. the string tables' keys
    C.text_strings(plan)
    # 3. Medieval II's battle models
    from . import modeldb as MD
    src, dst = MD.find(mod)
    if src:
        db = MD._db_in_plan(plan, src, dst)
        k = 0
        for m in db.models:
            for key in ("textures", "attach"):
                for r in getattr(m, key):
                    if r[0] == old:
                        r[0] = new
                        k += 1
        if k:
            plan.binary(dst, db.dump().encode("latin-1"))
            plan.notes.append((mod.rel(dst), "%d texture entr(ies) of %s renamed %s" % (k, old, new)))
    # 4. the campaign scripts follow (the game's script words); Lua / Squirrel scripts: listed, not changed
    left = []
    for p in scripts:
        try:
            with open(p, encoding="latin-1") as fh:
                hits = [i + 1 for i, line in enumerate(fh) if rx.search(line)]
        except OSError:
            continue
        if hits and not p.lower().endswith((".lua", ".nut")):
            f = plan.edit(p)
            for i in hits:
                f.set(i - 1, rx.sub(lambda m: _cased(new, m.group(), old), f.text(i - 1)))
            plan.note(f, "%d line(s) of the campaign script: %s -> %s" % (len(hits), old, new))
            total += len(hits)
        elif hits:
            left.append("%s: line(s) %s" % (mod.rel(p), ", ".join(str(h) for h in hits[:12]) +
                                             (" ..." if len(hits) > 12 else "")))
    if left:
        plan.warn(None, "Lua / Squirrel scripts name %s - not changed (code is changed by hand): %s" % (
            old, "; ".join(left[:8])))
    plan.note(None, "%s renamed %s: %d line(s) in the data files, its pictures copied under the new name, the "
                    "string tables' keys copied" % (old, new, total))
    return left
