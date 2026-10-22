"""Authors and sources: whose work a mod holds - units, factions, models, packs taken from other mods - with the
author, a link and whether the author was asked. Both games.

Kept in the mod folder (beside data/): CampaignEditor_sources.json (the list) and Authors_and_sources.txt (the same
list in plain words, for the players and for whoever shares the mod - rewritten at every change). Nothing is checked
or blocked: it only helps an honest modder not forget. The game's own data (and its expansions) is the game makers'
work and is not listed; on the game's own data folder there is no mod folder to keep a list in."""

import json
import os

from .newmod import game_root_of

LIST_NAME = "CampaignEditor_sources.json"
TEXT_NAME = "Authors_and_sources.txt"
HEAD = "Authors and sources"
GAME_PARTS = ("bi", "alexander")                # the expansions: the game makers' work, like the game's own data
# whether the author was asked (the key kept, the words shown)
ASKED = (("not_yet", "Not yet"), ("waiting", "Asked, waiting"), ("yes", "Yes, allowed"),
         ("no", "No"), ("not_needed", "Not needed"))
ASKED_WORDS = dict(ASKED)
FIELDS = ("what", "source", "author", "link", "asked")


def folder(data_dir):
    """The mod folder the list lives in (the data folder's parent), None on the game's own data folder."""
    if not data_dir:
        return None
    _, base = game_root_of(data_dir)
    return os.path.dirname(os.path.abspath(data_dir)) if base else None


def is_game_own(data_dir):
    """The game's own data or an expansion's (bi, alexander): the game makers' work, not another modder's."""
    _, base = game_root_of(data_dir)
    return base is None or base.lower() in GAME_PARTS


def source_name(path):
    """The name a source goes by: a mod's folder name for its data folder, a pack's file name without .zip."""
    p = os.path.abspath(path).rstrip("\\/")
    if os.path.basename(p).lower() == "data":
        p = os.path.dirname(p)
    name = os.path.basename(p)
    return name[:-4] if name.lower().endswith(".zip") else name


def _clean(e):
    out = {k: str(e.get(k) or "").strip() for k in FIELDS}
    if out["asked"] not in ASKED_WORDS:
        out["asked"] = "not_yet"
    return out


def load(root):
    """The list of a mod folder: [{what, source, author, link, asked}] ([] when none or not readable)."""
    if not root:
        return []
    try:
        with open(os.path.join(root, LIST_NAME), encoding="utf-8") as fh:
            got = json.load(fh)
    except (OSError, ValueError):
        return []
    items = got.get("sources") if isinstance(got, dict) else None
    return [_clean(e) for e in items if isinstance(e, dict)] if isinstance(items, list) else []


def text(items, mod=""):
    """Authors_and_sources.txt: the list in plain words, one block a source."""
    out = [HEAD + (" - " + mod if mod else ""), "=" * len(HEAD + (" - " + mod if mod else "")),
           "This mod uses the work of these people. Thank you!", ""]
    for e in items:
        out.append("- " + (e["source"] or "(unknown)") + (" - " + e["author"] if e["author"] else ""))
        if e["link"]:
            out.append("  " + e["link"])
        if e["what"]:
            out.append("  Taken: " + e["what"])
        if e["asked"] == "yes":
            out.append("  Used with the author's permission.")
        out.append("")
    out.append("Made with the RTW & M2TW Campaign Editor")
    return "\r\n".join(out) + "\r\n"


def save(root, items):
    """The list and its text file written into the mod folder; an empty list leaves no text file behind."""
    items = [_clean(e) for e in items]
    with open(os.path.join(root, LIST_NAME), "w", encoding="utf-8") as fh:
        json.dump({"sources": items}, fh, indent=1, ensure_ascii=False)
    txt = os.path.join(root, TEXT_NAME)
    if items:
        with open(txt, "w", encoding="utf-8", newline="") as fh:
            fh.write(text(items, os.path.basename(root)))
    elif os.path.exists(txt):
        os.remove(txt)
    return items


def find(items, source):
    """The index of a source's entry (by its name, any case), None when not listed yet."""
    key = source.strip().lower()
    return next((i for i, e in enumerate(items) if e["source"].lower() == key), None)


def noted(items, source, what):
    """The list with `what` noted under `source`: a source already listed keeps its author, link and answer and
    gets the new thing added to its 'taken' words (once); a new source comes in with 'not asked yet'.
    Returns (items, index of the entry)."""
    items = [_clean(e) for e in items]
    what = what.strip()
    i = find(items, source)
    if i is None:
        items.append(_clean({"source": source, "what": what}))
        return items, len(items) - 1
    have = [w.strip() for w in items[i]["what"].split(";") if w.strip()]
    if what and what.lower() not in [w.lower() for w in have]:
        items[i]["what"] = "; ".join(have + [what])
    return items, i
