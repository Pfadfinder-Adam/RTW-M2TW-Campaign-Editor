"""Bring a faction from another mod (New faction > 'From another mod...'): the faction of the other mod made a faction
of this one, both games (Rome <-> Rome, Barbarian Invasion, REX mods; Medieval II <-> Medieval II).

How (open.md 'BRING A FACTION FROM ANOTHER MOD'): the new faction is made the New faction way (build.build, clone.py)
on a faction of this mod of the same culture - its 'frame', so every file that lists factions gets a line of the
new one the way this mod writes them - and then what is the brought faction's own is laid over it:
- its colours, culture (when this mod has it), and the names players read (the window's fields, filled from it);
- its own units (export_descr_unit 'ownership' naming it): one this mod has with the very same lines is shared
  (the new faction added to its ownership), any other comes with its models, textures, cards, sounds and recruit
  lines (packs.collect / import_pack - Bring units);
- its characters' names (descr_names.txt and the names' texts);
- its campaign-map figures' textures (descr_model_strat.txt) where this mod has the same figure;
- its pictures (Art: buttons, symbols, banners, loading logo) - each into the place the frame's copy took.
What does not come (said in the plan): its towns and armies (the maps differ - picked on the map as for any new
faction), scripts and events naming it, traits only it has, a culture this mod lacks (the frame's is kept)."""

import os
import re

from .textio import strip_comment, tokens


def factions(src):
    """[(faction, culture)] of the other mod (not the rebels)."""
    return [(n, c) for n, c in src.factions() if n != "slave"]


def frame_of(mod, culture, prefer=None):
    """The faction of this mod the new one is made on: prefer when given and here, else the first of the same
    culture, else the first faction (not the rebels)."""
    have = [(n, c) for n, c in mod.factions() if n != "slave"]
    names = [n for n, _ in have]
    if prefer in names:
        return prefer
    return next((n for n, c in have if c == culture), names[0] if names else None)


def window_fields(src, campaign, faction):
    """What the New faction window takes from the brought faction: names players read, colours, culture."""
    from .build import template_display
    from .edit import read_faction
    out = {}
    try:
        out.update(template_display(src, faction, campaign))
    except Exception:
        pass
    try:
        now = read_faction(src, campaign, faction)
        out["primary_colour"] = now.get("primary_colour")
        out["secondary_colour"] = now.get("secondary_colour")
        for k in ("description", "long_description"):
            if now.get(k):
                out[k] = now[k]
    except Exception:
        pass
    try:
        out["culture"] = src.culture(faction)
    except Exception:
        pass
    return out


def own_units(src, faction):
    """[unit type] of the other mod's units whose ownership names the faction itself (not its culture: units of a
    culture come with the culture)."""
    from .packs import type_blocks, _block_lines, _values
    path = src.file("edu")
    if not path:
        return []
    f = src.load(path)
    out = []
    for name, span in type_blocks(f).items():
        owners = [x.strip() for v in _values(_block_lines(f, span), "ownership") for x in v]
        owners = [o for part in owners for o in re.split(r"[\s,]+", part) if o]
        if faction in owners:
            out.append(name)
    return out


def _same_unit(a, b):
    """Two EDU blocks alike but for their ownership (and comments, spacing)."""
    def norm(lines):
        return [strip_comment(x).split() for x in lines if strip_comment(x).strip() and
                tokens(x)[:1] != ["ownership"]]
    return norm(a) == norm(b)


def bring_units(plan, src, faction, new):
    """The brought faction's own units into plan.mod for new: shared where this mod has the very same unit,
    brought (with everything it needs) where not. -> (shared, brought) unit names."""
    from . import packs
    from .packs import type_blocks, _block_lines
    mod = plan.mod
    want = own_units(src, faction)
    if not want:
        return [], []
    sf = src.load(src.file("edu"))
    sblocks = type_blocks(sf)
    edu = plan.edit(mod.file("edu"))
    tblocks = type_blocks(edu)
    shared, bring = [], []
    for u in want:
        if u in tblocks and _same_unit(_block_lines(sf, sblocks[u]), _block_lines(edu, tblocks[u])):
            shared.append(u)
        else:
            bring.append(u)
    for u in shared:                                    # the same unit: the new faction owns it too
        a, b = tblocks[u]
        for i in range(a, b):
            if tokens(edu.text(i))[:1] == ["ownership"] and new not in tokens(edu.text(i)):
                code = strip_comment(edu.text(i))
                rest = edu.text(i)[len(code):]
                edu.set(i, code.rstrip() + ", " + new + (" " + rest if rest else ""))
                break
    if shared:
        plan.note(edu, "%s owns %d unit(s) this mod has just as %s has them: %s" % (
            new, len(shared), faction, ", ".join(shared)))
    if bring:
        manifest, files = packs.collect(src, bring)
        packs.import_pack(plan, manifest, files, [new])
        plan.note(None, "%d unit(s) of %s brought with their models, cards and recruit lines: %s" % (
            len(bring), faction, ", ".join(bring)))
    return shared, bring


def bring_names(plan, src, faction, new):
    """The new faction's name lists (a copy of its frame's, made by clone.names) made the brought faction's own -
    its section of descr_names.txt, and every name's text the names table lacks."""
    from .moddata import name_sections
    from .strtables import strings, write_texts
    sp = src.file("names")
    tp = plan.mod.file("names")
    if not sp or not tp:
        return
    stexts = src.load(sp).texts()
    sh = name_sections(stexts)
    k = next((k for k, (_, o) in enumerate(sh) if faction in o), None)
    if k is None:
        plan.warn(None, "%s has no name lists in the other mod - %s keeps its frame's names" % (faction, new))
        return
    s = sh[k][0]
    e = sh[k + 1][0] if k + 1 < len(sh) else len(stexts)
    section = ["faction: %s" % new] + stexts[s + 1:e]
    f = plan.edit(tp)
    th = name_sections(f.texts())
    j = next((j for j, (_, o) in enumerate(th) if new in o), None)
    if j is not None:
        a = th[j][0]
        b = th[j + 1][0] if j + 1 < len(th) else len(f)
        f.raw[a:b] = [f.make(x) for x in section]
    else:
        slave = next((i for i, o in th if "slave" in o), None)
        f.insert(slave if slave is not None else len(f), section)
    # every name needs its text (a name in no table crashes the game): the other mod's, where this mod lacks it
    names = {strip_comment(x).strip() for x in section[1:]}
    names = {n for n in names if n and n not in ("characters", "surnames", "women") and " " not in n}
    have, theirs = strings(plan.mod, "names.txt"), strings(src, "names.txt")
    add = {n: theirs[n.upper()] for n in names if n.upper() not in have and n.upper() in theirs}
    if add:
        write_texts(plan, "names.txt", add)
    plan.note(f, "%s's name lists: %s's own (%d name(s), %d new text(s))" % (new, faction, len(names), len(add)))


def bring_figures(plan, src, faction, new):
    """descr_model_strat.txt: each campaign-map figure this mod has too gets new's texture line in the brought
    faction's texture (the picture copied in when this mod lacks it). -> how many."""
    p_src, p_tgt = src.find("descr_model_strat.txt"), plan.mod.find("descr_model_strat.txt")
    if not p_src or not p_tgt:
        return 0
    theirs = _texture_lines(src.load(p_src).texts(), faction)
    f = plan.edit(p_tgt)
    n = 0
    cur = None
    for i in range(len(f)):
        t = strip_comment(f.text(i)).replace(",", " ").split()
        if len(t) >= 2 and t[0] == "type":
            cur = t[1]
        elif len(t) >= 3 and t[0] == "texture" and t[1] == new and cur in theirs:
            ref = theirs[cur]
            rel = ref[5:] if ref.lower().startswith("data/") else ref
            if not plan.mod.find(rel):
                got = src.find(rel) or src.find(rel + ".dds")
                if not got:
                    continue
                dst = os.path.join(plan.mod.data, *rel.split("/")) + (".dds" if got.lower().endswith(".dds") and
                                                                      not rel.lower().endswith(".dds") else "")
                plan.copy(got, dst)
            f.set(i, re.sub(r"(texture\s+%s\s*,\s*)(\S+)" % re.escape(new), lambda m: m.group(1) + ref, f.text(i),
                            count=1))
            n += 1
    if n:
        plan.note(f, "%d campaign-map figure(s) of %s in %s's textures" % (n, new, faction))
    return n


def _texture_lines(texts, faction):
    out, cur = {}, None
    for line in texts:
        t = strip_comment(line).replace(",", " ").split()
        if len(t) >= 2 and t[0] == "type":
            cur = t[1]
        elif len(t) >= 3 and t[0] == "texture" and t[1] == faction and cur:
            out[cur] = t[2]
    return out


def art_picks(src, campaign, faction, new, folder):
    """{picture path under data: source picture} - the brought faction's pictures (Art) for the places the new
    faction's copies take (its name for the other's in each path); the pictures on sprite sheets cut out into
    folder first."""
    from . import factionart as FA
    out = {}
    try:
        pics = FA.faction_pictures(src, campaign, faction)
    except Exception:
        return out
    for e in pics:
        rel = e.get("rel") or ""
        if e.get("crop") and e.get("path"):
            try:
                from PIL import Image
                x, y, w, h = e["crop"]
                with Image.open(e["path"]) as im:
                    cut = im.convert("RGBA").crop((x, y, x + w, y + h))
                os.makedirs(folder, exist_ok=True)
                dst = os.path.join(folder, "%s_%s.png" % (faction, re.sub(r"\W+", "_", rel)))
                cut.save(dst)
                out[rel] = dst
            except Exception:
                continue
            continue
        if rel.startswith("symbol:") or not e.get("path"):
            continue
        new_rel = re.sub(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(faction), new, rel, flags=re.I)
        if new_rel != rel:
            out[new_rel] = e["path"]
    return out


def overlay(plan, campaign, bring):
    """Lay the brought faction (bring = {'src': its data folder, 'faction', 'campaign'}) over plan.new, made on its
    frame (build.build calls this before the start is written)."""
    from .moddata import ModData
    src = ModData(bring["src"])
    faction, new = bring["faction"], plan.new
    from .packs import game_kind
    if game_kind(src) != game_kind(plan.mod):
        raise ValueError("a faction goes between mods of one game (this one is %s, %s's %s)" % (
            game_kind(plan.mod), faction, game_kind(src)))
    culture = None
    try:
        culture = src.culture(faction)
    except Exception:
        pass
    known = {c for _, c in plan.mod.factions() if c}
    sm = plan.edit(plan.mod.file("sm_factions"))
    if culture and culture in known:                    # its own culture, when this mod has it
        inside = False
        for i in range(len(sm)):
            t = tokens(sm.text(i))
            if t[:1] == ["faction"]:
                inside = len(t) > 1 and t[1].rstrip(",") == new
            elif inside and t[:1] == ["culture"] and t[1:2] != [culture]:
                sm.set(i, re.sub(r"(culture\s+)\S+", lambda m: m.group(1) + culture, sm.text(i), count=1))
                break
    elif culture:
        plan.warn(sm, "%s's culture %s is not in this mod - %s keeps its frame's culture" % (faction, culture, new))
    shared, brought = bring_units(plan, src, faction, new)
    if plan.opts.get("copy_art", True):                 # its pictures where the frame's copies went (yours win)
        from . import log
        folder = os.path.join(log.logs_dir() or os.path.expanduser("~"), "brought_pictures")
        art = plan.opts.setdefault("art", {})
        for rel, pic in art_picks(src, bring.get("campaign") or campaign, faction, new, folder).items():
            art.setdefault(rel, pic)
    bring_names(plan, src, faction, new)
    bring_figures(plan, src, faction, new)
    plan.note(None, "brought from %s: %s as %s (made on %s; %d unit(s) shared, %d brought). Not brought: its towns "
                    "and armies (placed on this map), scripts and events naming it" % (
                        os.path.basename(os.path.dirname(os.path.abspath(bring["src"]))) or bring["src"], faction,
                        new, plan.template, len(shared), len(brought)))


__all__ = ["factions", "frame_of", "window_fields", "own_units", "overlay", "art_picks"]
