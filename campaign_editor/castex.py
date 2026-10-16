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
            if mod.find(f):
                return True
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


__all__ = ["texture_names", "used_models", "missing", "problems"]
