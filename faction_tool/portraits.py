"""The portrait library: the pictures the game gives characters, per culture
(descr_cultures portrait_mapping), and new ones added to it.

On disk (Rome, checked on the vanilla files; Medieval II uses the same folders, its exe
also reads young/<group>_<religion>/):
    ui/<culture>/portraits/portraits/young/<group>/NNN.tga      69 x 96
    ui/<culture>/portraits/portraits/old/<group>/NNN.tga
    ui/<culture>/portraits/portraits/dead/NNN.tga               generals only
    ui/<culture>/portraits/cards/young|old/<group>/NNN.tga      44 x 63 (the small card)
    ui/<culture>/portraits/cards/dead/NNN.tga
Groups: generals (named characters, admirals), civilians (diplomats, merchants, family...),
rogues (spies, assassins). The same number is the same man: a general gets number N and
shows young/N, then old/N, then dead/N - so every folder of a group keeps the same count, and
a new portrait is added under the next free number in all of them at once. Folder names keep
the case they have (barbarian uses Young / Old / Dead). A mod folder adds to the game's own
(REX: portrait_pool merged pools them; the numbers go on after the game's)."""

import os
import re

from .family import data_roots, portrait_culture
from .moddata import _ci

AGES = ("young", "old")


def _dir(root, *parts):
    """The existing folder root/parts (any case), or None."""
    cur = root
    for p in parts:
        cur = _ci(cur, p) if cur else None
    return cur if cur and os.path.isdir(cur) else None


def _numbers(folder):
    out = {}
    if folder and os.path.isdir(folder):
        for n in os.listdir(folder):
            m = re.match(r"^(\d+)\.tga$", n, re.I)
            if m:
                out[int(m.group(1))] = os.path.join(folder, n)
    return out


def cultures(mod):
    """The portrait cultures of the mod's factions, in their order, each once."""
    out = []
    for f, _ in mod.factions():
        c = portrait_culture(mod, f)
        if c and c not in out:
            out.append(c)
    return out


def library(mod, culture):
    """{group: {'young': {n: path}, 'old': {...}, 'dead': {...} (generals), 'cards': {age: {n: path}},
    'count': n}} - the mod's pictures over the game's (a mod's file wins by number)."""
    out = {}
    for root in reversed(data_roots(mod)):                 # the game first, the mod on top
        base = _dir(root, "ui", culture, "portraits")
        if not base:
            continue
        for age in AGES:
            ad = _dir(base, "portraits", age)
            if not ad:
                continue
            for g in sorted(os.listdir(ad)):
                gd = os.path.join(ad, g)
                if not os.path.isdir(gd):
                    continue
                e = out.setdefault(g.lower(), {"young": {}, "old": {}, "cards": {}})
                e[age].update(_numbers(gd))
                e["cards"].setdefault(age, {}).update(_numbers(_dir(base, "cards", age, g)))
        dead = _numbers(_dir(base, "portraits", "dead"))
        if dead and "generals" in out:
            out["generals"].setdefault("dead", {}).update(dead)
            out["generals"]["cards"].setdefault("dead", {}).update(_numbers(_dir(base, "cards", "dead")))
    for e in out.values():
        e["count"] = max([len(e["young"]), len(e["old"])])
    return out


def sizes(mod, culture):
    """(portrait (w, h), card (w, h)) of the culture's own pictures (vanilla 69 x 96 and 44 x 63)."""
    from .factionart import tga_info
    lib = library(mod, culture)
    pic = card = None
    for e in lib.values():
        for p in list(e["young"].values())[:1]:
            pic = pic or tga_info(p)
        for p in list((e["cards"].get("young") or {}).values())[:1]:
            card = card or tga_info(p)
    return (tuple(pic[:2]) if pic else (69, 96)), (tuple(card[:2]) if card else (44, 63))


def next_number(entry):
    nums = set(entry["young"]) | set(entry["old"]) | set(entry.get("dead") or {})
    for c in entry["cards"].values():
        nums |= set(c)
    return max(nums) + 1 if nums else 0


def _folder_name(mod, culture, *parts):
    """The path under the mod's data for parts, in the case the game's folders have."""
    for root in data_roots(mod):
        d = _dir(root, "ui", culture, "portraits", *parts)
        if d:
            rel = os.path.relpath(d, root)
            return os.path.join(mod.data, rel)
    return os.path.join(mod.data, "ui", culture, "portraits", *parts)


def _like(entry, age, card=False):
    src = (entry["cards"].get(age) or {}) if card else (entry.get(age) or {})
    return next(iter(src.values()), None)


def add(plan, culture, group, pics):
    """New portrait(s) in culture's group: pics = [{'young': src, 'old': src?, 'dead': src?}]. Each gets
    the next free number in every folder of the group (young, old, dead for generals, and the cards),
    in the size and depth of the pictures there; an age not given takes the young one (the dead one
    greyed, as the game's own). Returns the numbers."""
    from PIL import Image, ImageOps
    from .factionart import image_tga
    lib = library(plan.mod, culture)
    entry = lib.get(group.lower())
    if entry is None:
        raise ValueError("%s has no portrait group %s (it has: %s)" % (culture, group, ", ".join(sorted(lib)) or "none"))
    (pw, ph), (cw, chh) = sizes(plan.mod, culture)
    ages = list(AGES) + (["dead"] if entry.get("dead") else [])
    done = []
    n = next_number(entry)
    for p in pics:
        first = p.get("young") or p.get("old")
        if not first:
            continue
        for age in ages:
            src = p.get(age) or (p.get("old") if age == "dead" else None) or first
            with Image.open(src) as im:
                im = im.convert("RGBA")
                if age == "dead" and not p.get("dead"):
                    grey = ImageOps.grayscale(im).convert("RGBA")
                    grey.putalpha(im.getchannel("A"))
                    im = grey
                big = im.resize((pw, ph), Image.LANCZOS)
                small = im.resize((cw, chh), Image.LANCZOS)
            where = ("portraits", "dead") if age == "dead" else ("portraits", age, group)
            cwhere = ("cards", "dead") if age == "dead" else ("cards", age, group)
            target = os.path.join(_folder_name(plan.mod, culture, *where), "%03d.tga" % n)
            plan.binary(target, image_tga(big, _like(entry, age)))
            if entry["cards"].get(age) is not None or age == "young":
                ct = os.path.join(_folder_name(plan.mod, culture, *cwhere), "%03d.tga" % n)
                plan.binary(ct, image_tga(small, _like(entry, age, card=True)))
        plan.notes.append((plan.mod.rel(_folder_name(plan.mod, culture, "portraits")),
                           "portrait %03d added to %s / %s (%s; %d x %d, card %d x %d) from %s" % (
                               n, culture, group, ", ".join(ages), pw, ph, cw, chh, os.path.basename(first))))
        done.append(n)
        n += 1
    return done


__all__ = ["cultures", "library", "sizes", "add", "next_number"]
