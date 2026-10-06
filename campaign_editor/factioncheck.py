"""Is this faction complete? Every file of the mod that names (nearly) every faction, and whether it names this one
- measured on the mod itself: a file where nearly all the other factions are named and this one is not is a GAP
(the game or the faction-select screen will miss something); a file where many but not all are named is a NOTE
(real, working factions go without it too). Read-only. Shown in Check mod files when a faction is picked."""

import os
import re

from .moddata import DATA_FILES
from .scan import _read_text, _word

RE_KEY = re.compile(r"^\s*\{[A-Za-z0-9_]+\}", re.M)
GAP, NOTE = 1.0, 0.5            # share of the other factions a file names: a gap when EVERY other faction is named
#                                 there (vanilla factions that play without a file's line are named in less), a note
#                                 from NOTE up


def _files(mod, campaign):
    out = []
    for key in DATA_FILES:
        p = mod.file(key)
        if p and p not in out:
            out.append(p)
    for name in ("descr_strat.txt", "descr_win_conditions.txt"):
        p = mod.campaign_file(campaign, name)
        if p and p not in out:
            out.append(p)
    for p in mod.campaign_text_files(campaign):
        if p not in out:
            out.append(p)
    return out


def complete(mod, faction, campaign):
    """[(file, 'gap' | 'note', share of the others named there (0..1), a same-culture faction that is named there or
    None)], gaps first; and how many files name it as the others do (the fine ones)."""
    facs = mod.factions()
    culture = dict(facs).get(faction)
    others = [n for n, _ in facs if n not in (faction, "slave")]
    if not others or faction == "slave":           # the rebels are named in other places than a faction
        return [], 0
    rows, fine = [], 0
    words = {n: _word(n) for n in others + [faction]}
    for path in _files(mod, campaign):
        try:
            text = _read_text(path)
        except OSError:
            continue
        if not text:
            continue
        if path.lower().endswith(".txt") and os.sep + "text" + os.sep in path.lower() and not RE_KEY.search(text):
            continue                                 # a text dump with no {KEY} lines (M2TW's menu_english.txt
            #                                          beside its .strings.bin): the game does not read it
        by_culture = os.path.basename(path).lower() == "export_descr_buildings.txt"    # 'factions { eastern, }'
        cult = {}                                    # names a whole culture (Rome's egypt builds that way)

        def has(n):
            if words[n].search(text):
                return True
            c = dict(facs).get(n)
            if not by_culture or not c:
                return False
            if c not in cult:
                cult[c] = bool(_word(c).search(text))
            return cult[c]
        named = [n for n in others if has(n)]
        share = len(named) / len(others)
        if share < NOTE:
            continue
        if has(faction):
            fine += 1
            continue
        like = next((n for n in named if dict(facs).get(n) == culture), named[0] if named else None)
        rows.append((mod.rel(path), "gap" if share >= GAP else "note", share, like))
    rows.sort(key=lambda r: (r[1] != "gap", -r[2], r[0]))
    return rows, fine


def words(rows, fine, faction):
    """The rows as lines for a report."""
    out = ["IS %s COMPLETE? %d file(s) name it as the other factions do" % (faction.upper(), fine)]
    for rel, kind, share, like in rows:
        out.append("    %s %s: %d %% of the other factions are named there, %s is not%s" % (
            "GAP " if kind == "gap" else "note", rel, round(share * 100), faction,
            " (e.g. %s is - copy its lines and rename them)" % like if like else ""))
    if not rows:
        out.append("    nothing missing")
    return out
