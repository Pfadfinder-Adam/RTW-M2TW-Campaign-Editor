"""Rename a region and its settlement in the files (the system names), with everything that names them.

The names players see live in the campaign's names text and are changed by Edit region / Rename (regionedit
.set_labels). The names in the files - `Latium`, `Rome` - are what the game's files use to tie things together:
descr_regions.txt (the region and its town), descr_strat.txt (`region Latium` in each settlement), the campaign's
descr_regions_and_settlement_name_lookup.txt, the {keys} of the names texts, and whatever a mod's own files say:
campaign_script and descr_events conditions (SettlementName Rome, RegionName, IsRegionOneOf ...), win conditions,
mercenary pools, trait / ancillary triggers, REX scripts. A rename changes the name as a whole word, spelled exactly
(case matters: `rome` the region tag stays when the town `Rome` is renamed), in every text file of the mod's data;
in the string tables (data/text) only the {keys}, so prose that mentions the place keeps its words. map.rwm is
removed (the game builds it again). Everything goes through a Plan: Preview first, a backup, Restore."""

import os
import re

from .plan import BACKUP_DIR
from .scan import _read_text

TEXT_EXT = (".txt", ".xml", ".nut", ".lua")
RE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _token(name):
    """The name as a whole word of a file: letters, digits and _ on neither side (Rome, not Rome_Province)."""
    return re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(name))


# a word right after these is a faction's name, never a place's (a town named like a faction: Jerusalem)
FACTION_BEFORE = re.compile(r"(Faction\s*=\s*\"|FactionType\s+|FactionIsLocal\s+|\bfaction\s+|\bfactions\s*\{[^}]*|"
                            r"ownership\s+[^;]*|I_CompareCounter\s+)$", re.I)


def _replace(rx, rep, code):
    """code with rx's matches replaced, except where the word stands as a faction's name; (text, count)."""
    out, last, n = [], 0, 0
    for m in rx.finditer(code):
        if FACTION_BEFORE.search(code[:m.start()]):
            continue
        out.append(code[last:m.start()] + rep)
        last = m.end()
        n += 1
    return "".join(out) + code[last:], n


def _key(name):
    return re.compile(r"\{%s\}" % re.escape(name))


def problems(mod, campaign, region, new_region, new_town):
    """Plain words for what the game would not take, or []."""
    regions = mod.regions(campaign)
    if region not in regions:
        return ["%s is no region of this campaign" % region]
    town = regions[region].get("settlement") or ""
    out = []
    for what, name in (("region", new_region), ("town", new_town)):
        if not RE_NAME.match(name or ""):
            out.append("the %s's name in the files: letters, digits and _ only, starting with a letter (like "
                       "Tribus_Novus) - '%s'" % (what, name))
    if new_region and new_region == new_town:
        out.append("the region and its town need different names in the files (their names players see may match)")
    taken = {}
    for r, v in regions.items():
        if r != region:
            taken[r.lower()] = "region %s" % r
            if v.get("settlement"):
                taken[v["settlement"].lower()] = "town of %s" % r
    for name, was in ((new_region, region), (new_town, town)):
        if name and name != was and name.lower() in taken:
            out.append("%s is taken already (%s)" % (name, taken[name.lower()]))
    return out


# left out: battle maps and historical battles, logs, copies and backups (scripts, advice and translations stay in)
SKIP = re.compile(r"(^|/)world/maps/(battle|custom)/|(^|/)descr_battle\.txt$|(^|/)editor_log\.txt$|"
                  r"(^|/)[^/]*\.log(\.txt)?$|(^|/)system\.log|"
                  r"(^|/)(![^/]*|[^/]*kopie[^/]*|[^/]*backup[^/]*|[^/]* - copy[^/]*)(/|$)", re.I)
PROSE = re.compile(r"(^|/)description[^/]*\.txt$", re.I)      # the campaign screen's faction texts: prose


def _files(mod, campaign):
    """Text files of the mod's data that may name a place (backups, logs, battle maps, prose left out). Of the
    campaign folders only this campaign's and those without a map of their own (a campaign with its own
    descr_regions.txt - a prologue - has its own places, even when they share a name); of the names texts
    likewise."""
    from .moddata import _ci
    camp_root = os.path.join(mod.data, "world", "maps", "campaign")
    own_map = set()
    if os.path.isdir(camp_root):
        for c in os.listdir(camp_root):
            if c.lower() != campaign.lower() and _ci(os.path.join(camp_root, c), "descr_regions.txt"):
                own_map.add(c.lower())
    for dirpath, dirnames, filenames in os.walk(mod.data):
        dirnames[:] = [d for d in dirnames if d != BACKUP_DIR and not (
            os.path.normcase(dirpath) == os.path.normcase(camp_root) and d.lower() in own_map)]
        for n in filenames:
            low = n.lower()
            if not low.endswith(TEXT_EXT) or any(low.startswith(c + "_regions_and_settlement_names")
                                                 for c in own_map):
                continue
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, os.path.dirname(mod.data)).replace("\\", "/")
            if not SKIP.search(rel) and not PROSE.search(rel):
                yield p


def _split(path, line):
    """(code, comment) of a line: the comment keeps its words (';' in the game's text files, '//' / '--' / '#' in
    scripts)."""
    low = path.lower()
    marks = ("//", "#") if low.endswith(".nut") else ("--",) if low.endswith(".lua") else \
        ("<!--",) if low.endswith(".xml") else (";",)
    cut = min([line.find(m) for m in marks if m in line] or [len(line)])
    return line[:cut], line[cut:]


def _is_strings(mod, path):
    """A string table of data/text ({KEY} text lines): only its keys are renamed."""
    rel = os.path.relpath(path, mod.data).replace("\\", "/").lower()
    return rel.startswith("text/")


def rename(plan, campaign, region, new_region, new_town=None):
    """The region (and its town, when new_town is given) renamed in the files, everywhere the mod's text files name
    them. Returns {old name: number of files}."""
    mod = plan.mod
    regions = mod.regions(campaign)
    town = (regions.get(region) or {}).get("settlement") or ""
    new_town = new_town or town
    why = problems(mod, campaign, region, new_region, new_town)
    if why:
        raise ValueError("; ".join(why))
    pairs = [(old, new) for old, new in ((region, new_region), (town, new_town)) if old and new and old != new]
    if not pairs:
        return {}
    counts = {old: 0 for old, _ in pairs}
    facs = {n.lower() for n, _ in mod.factions()}
    for old, _ in pairs:
        if old.lower() in facs:
            plan.warn(None, "%s is also a faction's name: where a line names the faction (Faction=\"...\", FactionType, "
                            "faction ...) it stays - check the Preview's list for a line that meant the faction" % old)
    for path in _files(mod, campaign):
        text = _read_text(path)
        if text is None or not any(old in text for old, _ in pairs):
            continue
        strings = _is_strings(mod, path)
        rxs = [((_key(old) if strings else _token(old)), ("{%s}" % new if strings else new), old)
               for old, new in pairs]
        if not any(rx.search(text) for rx, _, _ in rxs):
            continue
        f = plan.edit(path)
        hit = set()
        for i in range(len(f.raw)):
            line = f.text(i)
            code, comment = (line, "") if strings else _split(path, line)
            for rx, rep, old in rxs:
                code, n = rx.subn(rep, code) if strings else _replace(rx, rep, code)
                if n:
                    hit.add(old)
            new_line = code + comment
            if new_line != line:
                f.set(i, new_line)
        if hit:
            for old in hit:
                counts[old] += 1
            plan.note(f, ", ".join("%s -> %s" % (o, n) for o, n in pairs if o in hit))
    base = os.path.join(mod.data, "world", "maps", "base")
    from .moddata import _ci
    rwm = _ci(base, "map.rwm") if os.path.isdir(base) else None
    if rwm:
        plan.delete(rwm, "the game rebuilds it from the renamed map on the next start")
    bins = [n for n in os.listdir(os.path.join(mod.data, "text"))
            if n.lower().endswith(".strings.bin") and "regions_and_settlement_names" in n.lower()] \
        if os.path.isdir(os.path.join(mod.data, "text")) else []
    if bins:
        plan.warn(None, "Medieval II keeps the names text also compiled (%s): if the game shows the old name or a key, "
                        "remove that .strings.bin so it is built again from the .txt" % ", ".join(sorted(bins)))
    return counts
