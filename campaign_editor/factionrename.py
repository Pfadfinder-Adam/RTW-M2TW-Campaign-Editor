"""Rename a faction everywhere (the faction's code name - romans_julii, england - the one the files use; the names
players read are changed on the Faction tab). Both games.

What follows the new name, in one plan (Preview lists every line; one backup, Restore gives it all back):
- every text file of the mod's data (descr_sm_factions, descr_strat of every campaign, descr_names, the unit and
  building files, descr_character, descr_model_*, banners, win conditions, regions, events, mercenaries, traits,
  ancillaries, sounds, Medieval II's XML lists...): the faction's name as a word of its own (case as written; a
  name glued to more by '_' or standing in a file path - egypt_chariot, symbol_egypt.tga, ui/units/egypt/ - is not
  the faction and is not touched);
- its pictures (ui, menu, loading_screen, the campaign folder: files and folders named after it) copied under the new
  name (clone.art_files) and every line naming such a file by path pointed at the copy; the old files stay - nothing
  reads them any more;
- the string tables: every key holding the faction's name ({EGYPT}, {IMPERIAL_CAMPAIGN_EGYPT_TITLE}) copied under the
  new name (clone.text_strings), the old keys stay;
- Medieval II's battle_models.modeldb: its texture entries for the faction renamed.
Not changed, only listed: campaign scripts and Lua / Squirrel scripts naming it (a script is read as code - a
blind change there can break it)."""

import os
import re

from . import clone as C

RE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
TEXT_EXT = (".txt", ".xml", ".json")
SCRIPT_NAMES = ("campaign_script", "be_script", "four_turns")
SKIP_DIRS = ("text",)                       # string tables: their keys are copied (clone.text_strings)


def _word(name):
    """The faction as a word of its own: not glued by '_' and not part of a path or a file name."""
    return re.compile(r"(?<![A-Za-z0-9_/\\.])%s(?![A-Za-z0-9_/\\.])" % re.escape(name))


def problems(mod, old, new):
    """Why the faction cannot be renamed so, or None."""
    names = [n for n, _ in mod.factions()]
    if old not in names:
        return "%s is not a faction of descr_sm_factions.txt" % old
    if old == "slave":
        return "the rebels (slave) keep their name - the games look for it"
    if not RE_NAME.match(new or ""):
        return "a faction's code name is lower-case letters, digits and _, starting with a letter"
    if new in names or new == old:
        return "%s is already a faction of this mod" % new
    return None


def _is_script(path):
    low = os.path.basename(path).lower()
    return low.endswith((".lua", ".nut")) or any(low.startswith(s) for s in SCRIPT_NAMES)


def _text_files(mod, campaign):
    """Every text file of the data folder but the string tables, scripts apart."""
    out, scripts = [], []
    script_names = {os.path.normcase(p) for p in _strat_scripts(mod)}
    for dirpath, dirs, files in os.walk(mod.data):
        rel = os.path.relpath(dirpath, mod.data).replace("\\", "/").lower()
        if rel.split("/")[0] in SKIP_DIRS:
            dirs[:] = []
            continue
        for n in files:
            p = os.path.join(dirpath, n)
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
    # 1. its pictures under the new name; the paths that name them follow
    C.art_files(plan, campaign)
    moved = []
    for src, dst in plan.copies:
        a = os.path.relpath(src, mod.data).replace("\\", "/")
        b = os.path.relpath(dst, mod.data).replace("\\", "/")
        if not a.startswith(".."):
            moved.append((a, b))
    moved.sort(key=lambda m: -len(m[0]))
    rx = _word(old)
    rx_xml = re.compile(r'(\bfaction\s*=\s*")(%s)(")' % re.escape(old), re.I)
    files, scripts = _text_files(mod, campaign)
    total = 0
    for p in files:
        with open(p, "rb") as fh:
            raw = fh.read()
        if b"\0" in raw[:2048]:
            continue                                    # a UTF-16 / binary file under a text name: not ours
        text = raw.decode("latin-1")
        low = text.lower()
        if old not in low and not any(a.lower() in low for a, _ in moved):
            continue
        f = plan.edit(p)
        n = 0
        for i in range(len(f.raw)):
            t = f.text(i)
            new_t = rx.sub(new, t)
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
    # 4. scripts: listed, not changed
    left = []
    for p in scripts:
        try:
            with open(p, encoding="latin-1") as fh:
                hits = [i + 1 for i, line in enumerate(fh) if rx.search(line)]
        except OSError:
            continue
        if hits:
            left.append("%s: line(s) %s" % (mod.rel(p), ", ".join(str(h) for h in hits[:12]) +
                                             (" ..." if len(hits) > 12 else "")))
    if left:
        plan.warn(None, "scripts name %s - not changed (code is changed by hand): %s" % (old, "; ".join(left[:8])))
    plan.note(None, "%s renamed %s: %d line(s) in the data files, its pictures copied under the new name, the "
                    "string tables' keys copied" % (old, new, total))
    return left
