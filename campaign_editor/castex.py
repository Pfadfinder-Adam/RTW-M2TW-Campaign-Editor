"""The textures named INSIDE the campaign-map models (.cas) - a missing one stops the game: both exes' texture loader
says 'Failed to find texture <name>' and the game quits (RomeTW.exe FUN_00a9397f, medieval2.exe FUN_008ff680 - read in
their code, 2026-10-16; a modders' finding long before, IWTE's documentation too).

Only the models whose texture the game takes from the model itself are looked at - measured on the vanilla files of
Rome, Barbarian Invasion and Medieval II (every texture found, none left over by these rules):
  - descr_sm_resources.txt   the resources' models (item)
  - descr_cultures.txt       the settlements' and residences' models
  - descr_sm_factions.txt    the faction symbols
  - descr_model_strat.txt    the models of a type with NO texture line (a type with texture lines gives them itself)
The rest of the vanilla .cas name textures that are not there (battle units take theirs from descr_model_battle,
banners from their own files, settlement plans from elsewhere) - so the rest is never looked at.

Where the game looks: the name as written (often 'textures\\x.tga') beside the model, '.dds' added to it
(x.tga.dds - the usual way) or in its place; a bare name also in the 'textures' folder beside the model; the mod's
own folder first, then the game's under it."""

import os
import re

RE_TEX = re.compile(rb"([ -~]{1,160}?\.(?:tga|dds))\x00", re.I)
RE_CAS = re.compile(r"([A-Za-z0-9_\-./\\ #&]+\.cas)\b", re.I)
SOURCES = (("descr_sm_resources.txt", "a resource's model"), ("descr_cultures.txt", "a settlement's model"),
           ("descr_sm_factions.txt", "a faction symbol"))


def texture_names(data):
    """The texture file names a .cas names (its strings ending .tga / .dds), in order, once each."""
    out = []
    for m in RE_TEX.finditer(data):
        s = m.group(1).decode("latin-1")
        s = re.split(r"[^A-Za-z0-9_#\\/. \-()&'+]", s)[-1].strip()    # what is before the name: its length, junk
        if s and "." in s and s not in out:
            out.append(s)
    return out


def _rel(path):
    """'data/models_strat/x.cas' / '../mymod/data/models_strat/x.cas' (Rome's mod:switch form) -> 'models_strat/x.cas'."""
    p = path.strip().strip(",").replace("\\", "/")
    low = p.lower()
    i = low.rfind("data/")
    return p[i + 5:] if i >= 0 and (i == 0 or low[i - 1] == "/") else p


def used_models(mod):
    """{model rel (to data): set(what it is)} of the models whose textures the game takes from the model itself."""
    out = {}
    for name, what in SOURCES:
        p = mod.find(name)
        if not p:
            continue
        with open(p, encoding="latin-1") as fh:
            for line in fh:
                for m in RE_CAS.finditer(line.split(";")[0]):
                    out.setdefault(_rel(m.group(1).split()[-1]), set()).add(what)
    p = mod.find("descr_model_strat.txt")
    if p:
        blocks, cur = [], None
        with open(p, encoding="latin-1") as fh:
            for line in fh:
                t = line.split(";")[0].split()
                if not t:
                    continue
                if t[0] == "type":
                    cur = {"tex": False, "cas": [], "type": t[1] if len(t) > 1 else "?"}
                    blocks.append(cur)
                elif cur is not None and t[0] == "texture":
                    cur["tex"] = True
                elif cur is not None and t[0].startswith(("model", "shadow")):
                    m = RE_CAS.search(line.split(";")[0])
                    if m:
                        cur["cas"].append(_rel(m.group(1).split()[-1]))
        for b in blocks:
            if not b["tex"]:
                for c in b["cas"]:
                    out.setdefault(c, set()).add("the campaign-map model of %s" % b["type"])
    return out


def _texture_there(mod, cas_rel, tex):
    rel = tex.replace("\\", "/").strip()
    folder = os.path.dirname(cas_rel)
    cands = [rel.lstrip("/")]
    if "/" not in rel.strip("/"):
        cands.append("textures/" + rel.strip("/"))
    for c in cands:
        base = os.path.normpath(os.path.join(folder, c)).replace("\\", "/")
        forms = [base, base + ".dds"]
        if base.lower().endswith(".tga"):
            forms.append(base[:-4] + ".dds")
        for f in forms:
            if mod.find(f) or _packed(mod, f):
                return True
    return False


def _packed(mod, rel):
    """In one of the mod's packs (HLR keeps its towns' textures in data/packs - a tester, 2026-10-22: 90 textures
    named missing that the game finds there)."""
    from .gamepacks import in_packs
    try:
        return in_packs(mod.roots() if hasattr(mod, "roots") else [mod.data], rel)
    except Exception:
        return False


def missing(mod):
    """[(model rel, texture as named, sorted what-it-is)] of the textures the used models name that are not there."""
    out = []
    for rel, whats in sorted(used_models(mod).items()):
        path = mod.find(rel)
        if not path or not os.path.isfile(path):
            continue                                       # a model not found: other checks say it
        try:
            with open(path, "rb") as fh:
                names = texture_names(fh.read())
        except OSError:
            continue
        for t in names:
            if not _texture_there(mod, rel, t):
                out.append((rel, t, sorted(whats)))
    return out


def problems(mod):
    """Plain words for Check mod files, one per missing texture."""
    return ["%s (%s) names the texture '%s' inside it, and it is not there (looked beside the model, as .tga, "
            ".tga.dds and .dds, and in its textures folder) - the game stops as the campaign loads: 'Failed to find "
            "texture'. Put the picture there, or point the model at one that is (its texture name must keep its "
            "length)" % (rel, ", ".join(whats), tex) for rel, tex, whats in missing(mod)]


# ---- files named in the banners / standards / projectile files ----
PATH_FILES = ("descr_banners.txt", "descr_banners_new.xml", "descr_standards.txt", "descr_projectile.txt",
              "descr_projectile_new.txt")
RE_PATH = re.compile(r"""([A-Za-z]:[\\/][^\s,"<>]+|[A-Za-z0-9_#&.\-]*(?:[\\/][A-Za-z0-9_#&.\- ]+?)+"""
                     r"""\.(?:tga|dds|cas|texture|mesh|wav))(?=[\s,"<>]|$)""", re.I)
RE_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


def _file_there(mod, rel):
    forms = [rel, rel + ".dds"]
    if rel.lower().endswith(".tga"):
        forms.append(rel[:-4] + ".dds")
    return any(mod.find(f) for f in forms)


def path_problems(mod):
    """Plain words for the files the banners, standards and projectile files name that are not there - an absolute
    path (C:\\...) said as such: it is found only on the PC it was written on. Measured on vanilla Rome, BI and
    Medieval II: 1081 paths, every one found."""
    out = []
    for name in PATH_FILES:
        p = mod.find(name)
        if not p:
            continue
        lost = []
        with open(p, encoding="latin-1") as fh:
            for i, line in enumerate(fh, 1):
                code = line if name.endswith(".xml") else line.split(";")[0]
                for m in RE_PATH.finditer(code):
                    path = m.group(1)
                    if RE_DRIVE.match(path):
                        lost.append((i, path, True))
                    elif not _file_there(mod, _rel(path)):
                        lost.append((i, path, False))
        for i, path, drive in lost[:5]:
            out.append("%s line %d: %s" % (name, i, (
                "'%s' is a whole path on one PC (a drive letter) - the game finds it only there; write it from the "
                "data folder (data/...)" % path) if drive else (
                "'%s' is not there (not in the mod, not in the game) - the game reads it from there" % path)))
        if len(lost) > 5:
            out.append("%s: %d more file(s) like that" % (name, len(lost) - 5))
    return out


__all__ = ["texture_names", "used_models", "missing", "problems", "path_problems"]
