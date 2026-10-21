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

from .packs import _data_rel
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
    """What the New faction window takes from the brought faction: names players read, colours, culture, its AI,
    its leader's and heir's titles, money, religion, victory conditions (the tester, 2026-10-17: the template's
    stayed in the window)."""
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
        for k in ("description", "long_description", "leader_title", "heir_title", "religion", "denari", "ai"):
            if now.get(k):
                out[k] = now[k]
    except Exception:
        pass
    try:
        from .wincond import read as read_wins
        got = read_wins(src, campaign).get(faction)
        if got:
            out["victory"] = got
    except Exception:
        pass
    try:
        out["culture"] = src.culture(faction)
    except Exception:
        pass
    try:                                                # its leader and heir (the rest of the family comes on Apply)
        import re as _re
        from .strat import Strat
        ss = Strat(src.load(src.campaign_file(campaign, "descr_strat.txt")))
        for c in ss.faction(faction).characters:
            if c.role in ("leader", "heir") and c.named and c.role not in out:
                m = _re.search(r"\bage\s+(\d+)", ss.lines[c.start])
                out[c.role] = {"name": c.name, "age": int(m.group(1)) if m else 30}
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
    brought (with everything it needs) where not. -> (shared, brought, {its unit: the name it has here})."""
    from . import packs
    from .packs import type_blocks, _block_lines
    mod = plan.mod
    want = own_units(src, faction)
    if not want:
        return [], [], {}
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
    names = {u: u for u in shared}
    if bring:
        manifest, files = packs.collect(src, bring)
        got = packs.plan_names(mod, manifest)          # a name this mod has already: a free one
        packs.import_pack(plan, manifest, files, [new], names=got)
        names.update({old: t for old, (t, _) in got.items()})
        plan.note(None, "%d unit(s) of %s brought with their models, cards and recruit lines: %s" % (
            len(bring), faction, ", ".join(bring)))
    return shared, bring, names


def unit_pool(plan, new):
    """[(unit type, upkeep)] of the land units new owns in plan's export_descr_unit (the brought and the shared ones),
    generals' bodyguards, siege engines, animal handlers and ships left out - what its garrisons are drawn from."""
    from .packs import _block_lines, _values, type_blocks
    edu = plan.edit(plan.mod.file("edu"))
    out = []
    for name, span in type_blocks(edu).items():
        lines = _block_lines(edu, span)

        def first(key):
            got = _values(lines, key)
            return [x.strip().lower() for x in got[0]] if got else []
        owners = [o for part in first("ownership") for o in re.split(r"[\s,]+", part) if o]
        attrs = [a for part in first("attributes") for a in re.split(r"[\s,]+", part) if a]
        if new not in owners or "general_unit" in attrs or (first("category") or [""])[0] in (
                "siege", "handler", "ship", "non_combatant"):
            continue
        cost = first("stat_cost")
        try:
            upkeep = int(float(cost[2]))
        except (IndexError, ValueError):
            upkeep = 0
        out.append((name, upkeep))
    return out


def start_of(plan, src, campaign, faction, new, names):
    """What the new faction's start takes from the brought one (start.py reads plan.bring_start): the pool its
    garrisons are drawn from (its own units), its leader's bodyguard, and its family in the other mod's
    descr_strat.txt - every named character with his traits and his bodyguard, the records (wives, the dead) and
    the family tree's relative lines. Its armies and towns stay there: towns are picked on this map."""
    from .packs import type_blocks
    from .strat import Strat
    pool = unit_pool(plan, new)
    have = {t.lower(): t for t in type_blocks(plan.edit(plan.mod.file("edu")))}
    out = {"pool": pool, "bodyguard": None, "family": {"men": [], "records": [], "relatives": []}}
    sp = src.campaign_file(campaign, "descr_strat.txt") if campaign else None
    if not sp or not os.path.isfile(sp):
        return out
    from .start import _strip_sub_faction, unit_name
    ss = Strat(src.load(sp))
    fb = ss.faction(faction)
    if fb is None:
        return out

    def here(line):
        """A unit line under the name its unit has in this mod, or None when this mod lacks it."""
        u = unit_name(line)
        got = names.get(u, u)
        return line.replace(u, have[got.lower()], 1).strip() if got.lower() in have else None
    for c in fb.characters:
        if not c.named:
            continue
        body = ss.lines[c.start:c.end]
        units = [x for x in body if tokens(x)[:1] == ["unit"]]
        rest = [x for x in body[1:] if tokens(x)[:1] not in (["unit"], ["army"]) and x.strip()]
        guard = here(units[0]) if units else None
        if c.role == "leader" and guard:
            out["bodyguard"] = guard
        out["family"]["men"].append({"name": c.name, "line": _strip_sub_faction(body[0]), "rest": rest,
                                     "bodyguard": guard, "role": c.role})
    for x in ss.lines[fb.start:fb.end]:
        t = tokens(x)[:1]
        if t == ["character_record"]:
            out["family"]["records"].append(x)
        elif t == ["relative"]:
            out["family"]["relatives"].append(x)
    guard = out["bodyguard"] or next((m["bodyguard"] for m in out["family"]["men"] if m["bodyguard"]), None)
    for m in out["family"]["men"]:
        m["bodyguard"] = m["bodyguard"] or guard
    if guard is None:
        plan.warn(None, "%s's generals' bodyguard is not a unit of this mod - its family stays in the other mod "
                        "(only the leader and heir picked in the window come)" % faction)
        out["family"]["men"] = []
    return out


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


def _kind(path):
    """A picture's file kind by its whole ending: 'x.tga.dds' -> '.tga.dds', 'x.texture' -> '.texture'."""
    name = os.path.basename(path).lower()
    return name[name.find("."):] if "." in name else ""


def _put_over(plan, src, dst):
    """The brought faction's own picture at dst, in place of a copy queued there before (the frame's picture named
    after the new faction): a copy onto a file already there is skipped at the write, so the first one queued would
    win (the user's game test: the brought Celts showed Gaul's boar on the faction-select button)."""
    own = plan.mod.own(dst) if hasattr(plan.mod, "own") else dst
    plan.copies[:] = [(a, b) for a, b in plan.copies if os.path.normcase(b) != os.path.normcase(own)]
    if os.path.exists(own):
        # a file there already (an earlier try left the frame's picture under the new name): written over, with a
        # backup - a copy never replaces a file
        with open(src, "rb") as fh:
            plan.binary(own, fh.read())
    else:
        plan.copy(src, dst)


# the faction's lines in descr_sm_factions that name its own files: its 3D symbol on the campaign map and its movies
SM_FILES = ("symbol", "intro_movie", "victory_movie", "defeat_movie", "death_movie")


def bring_sm_files(plan, src, faction, new):
    """The brought faction's own symbol and movies (descr_sm_factions lines naming files): its line values put on
    new's lines, the files this mod lacks brought from the other mod (the user's game test: the Celts kept Gaul's
    3D symbol). A file the other mod lacks too leaves the line as the frame had it."""
    from .symbols import sm_values, _set_value
    theirs = src.load(src.file("sm_factions"))
    sm = plan.edit(plan.mod.file("sm_factions"))
    for key in SM_FILES:
        got = sm_values(theirs, key).get(faction)
        mine = sm_values(sm, key).get(new)
        if not got or not mine or got[1] == mine[1]:
            continue
        rel = got[1].replace("\\", "/")
        if not plan.mod.find(rel):
            path = src.find(rel)
            if not path:
                continue                                # neither mod has it: the frame's line stays
            dst = os.path.join(plan.mod.data, *rel.split("/"))
            if not _queued(plan, path, dst):
                plan.copy(path, dst)
        _set_value(sm, mine[0], got[1])
        plan.note(sm, "%s's %s now %s (%s's own)" % (new, key, got[1], faction))


def _queued(plan, src, dst):
    """The plan copies this very file there already."""
    own = plan.mod.own(dst) if hasattr(plan.mod, "own") else dst
    return any(a == src and os.path.normcase(b) == os.path.normcase(own) for a, b in plan.copies)


def _strat_block(src, model, faction, new, game):
    """(lines, {data-relative path: file}) of the other mod's descr_model_strat block `model` made for this mod:
    only the brought faction's texture line (named new) and the ones naming no faction, paths as this mod writes
    them, with the files they name."""
    from . import stratmodels as SM
    from .packs import _on_disk, _rebase_line
    f = src.load(src.file("model_strat"))
    a, b = SM.model_types(src)[model]["span"]
    lines, files = [], {}
    for i in range(a, b):
        t = tokens(f.text(i))
        if t[:1] and t[0] in SM.LINK_KEYS and len(t) >= 3:
            if t[1] != faction:
                continue
            line = re.sub(r"(%s\s+)%s(?![\w])" % (t[0], re.escape(faction)), lambda m: m.group(1) + new, f.text(i),
                          count=1)
        else:
            line = f.text(i)
        lines.append(_rebase_line(line, game))
        for ref in re.findall(r"[^,\s]+", strip_comment(f.text(i))):
            if "/" in ref:
                got = _on_disk(src, ref)
                if got:
                    files[got[0]] = got[1]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines, files


def bring_characters(plan, src, faction, new):
    """The brought faction's characters on the campaign map and in battle (descr_character.txt): each figure it has
    and the new faction has a place for gets the brought one - a strat model this mod lacks comes with its block
    (descr_model_strat.txt) and files, a battle model this mod lacks with its own (Bring units' way). -> how many
    figures changed."""
    from . import packs
    from . import stratmodels as SM
    mod = plan.mod
    if not src.file("character") or not mod.file("character") or not mod.file("model_strat"):
        return 0
    game = packs.game_kind(mod)
    theirs = {e["type"]: e for e in SM._entries(src.load(src.file("character"))) if faction in e["factions"]}
    sk = SM.model_types(src)
    ms = plan.edit(mod.file("model_strat"))
    added = []
    n = 0
    for ctype, e in theirs.items():
        models = [m for _, m in e["models"]]
        if not models:
            continue
        here = SM.model_types(mod, plan.edit)
        for m in models:
            if m in here or m not in sk:
                continue
            lines, files = _strat_block(src, m, faction, new, game)
            while ms.raw and not ms.text(len(ms.raw) - 1).strip():
                del ms.raw[-1]
            ms.raw.extend(ms.make(x) for x in [""] + lines + [""])
            for rel, path in files.items():
                dst = os.path.join(mod.data, *rel.split("/"))
                if not mod.find(rel) and not _queued(plan, path, dst):
                    plan.copy(path, dst)
            added.append(m)
        try:
            if SM.set_figure(plan, new, ctype, models):
                n += 1
        except ValueError as err:
            plan.warn(None, "%s's %s on the campaign map stays its frame's: %s" % (new, ctype, err))
    if added:
        plan.note(ms, "campaign-map figure(s) of %s brought: %s" % (faction, ", ".join(added)))
    n += _bring_battle_models(plan, src, theirs, new)
    return n


def _bring_battle_models(plan, src, theirs, new):
    """The battle_model lines of the new faction's characters: the brought faction's, the model brought when this
    mod lacks it."""
    from . import packs
    from . import stratmodels as SM
    from .packs import type_blocks
    mod = plan.mod
    sf = src.load(src.file("character"))
    want = {}                                           # character type -> battle model
    for ctype, e in theirs.items():
        for i in range(e["head"], e["end"]):
            t = tokens(sf.text(i))
            if t[:1] == ["battle_model"] and len(t) > 1:
                want[ctype] = t[1]
    if not want:
        return 0
    mb = mod.file("model_battle")
    have = {k.lower() for k in type_blocks(plan.edit(mb))} if mb else set()
    lack = sorted({m for m in want.values() if m.lower() not in have})
    renamed = {}
    if lack:
        try:
            manifest, files = packs.collect_models(src, lack)
            renamed = packs.import_models(plan, manifest, files, [new]) or {}
        except ValueError as err:
            plan.warn(None, "%s's battle figures stay its frame's: %s" % (new, err))
            return 0
    f = plan.edit(mod.file("character"))
    n = 0
    for e in SM._entries(f):
        if e["type"] not in want or new not in e["factions"]:
            continue
        model = renamed.get(want[e["type"]], want[e["type"]])
        for i in range(e["head"], e["end"]):
            t = tokens(f.text(i))
            if t[:1] == ["battle_model"] and len(t) > 1 and t[1] != model:
                if len(e["factions"]) > 1:                  # shared with others: the frame's entry stays theirs
                    break
                f.set(i, re.sub(r"^(\s*battle_model\s+)\S+", lambda m: m.group(1) + model, f.text(i), count=1))
                n += 1
    if n:
        plan.note(f, "%s's characters in battle wear the brought models: %s" % (
            new, ", ".join(sorted({renamed.get(m, m) for m in want.values()}))))
    return n


def bring_figures(plan, src, faction, new):
    """descr_model_strat.txt: each campaign-map figure this mod has too gets new's texture line in the brought
    faction's texture (the picture copied in when this mod lacks it). -> how many."""
    p_src, p_tgt = src.find("descr_model_strat.txt"), plan.mod.find("descr_model_strat.txt")
    if not p_src or not p_tgt:
        return 0
    theirs = _texture_lines(src.load(p_src).texts(), faction)
    from .packs import game_kind
    game = game_kind(plan.mod)
    f = plan.edit(p_tgt)
    n = 0
    cur = None
    for i in range(len(f)):
        t = strip_comment(f.text(i)).replace(",", " ").split()
        if len(t) >= 2 and t[0] == "type":
            cur = t[1]
        elif len(t) >= 3 and t[0] == "texture" and t[1] == new and cur in theirs:
            rel = _data_rel(theirs[cur])                  # 'bi/data/x' (from the game's root) -> under data
            ref = ("data/" + rel) if game == "rome" else rel  # how this game writes its own lines
            if not plan.mod.find(rel):
                got = src.find(rel) or src.find(rel + ".dds")
                if not got:
                    continue
                dst = os.path.join(plan.mod.data, *rel.split("/")) + (".dds" if got.lower().endswith(".dds") and
                                                                      not rel.lower().endswith(".dds") else "")
                if not _queued(plan, got, dst):
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
        own = re.compile(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(faction), re.I)
        if own.search(rel):                             # its own picture (shared ones - routing, rebels - stay)
            out[own.sub(new, rel)] = e["path"]
    return out


def blank_frame_pictures(plan, campaign, picks_done, folder):
    """A brought faction is made from zero (the user, 2026-10-21: 'I got the Huns' flags - flags, icons, pictures:
    zero, nothing'): every picture the frame's copy put under the new faction's name (its buttons, logos, flag,
    banners...) that the brought faction has no picture of its own for is made EMPTY (a clear picture of the same
    size and format) - never the frame's. The file is there, so the game finds it; the modder gives his own on the
    Art tab. [the data paths emptied]."""
    from . import factionart as FA
    t, new = plan.template, plan.new
    try:
        pics = FA.faction_pictures(plan.mod, campaign, t)
    except Exception:
        return []
    try:
        from .symbols import entries as symbol_entries
        pics = pics + symbol_entries(plan.mod, t)
    except Exception:
        pass
    own = re.compile(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(t), re.I)
    art = plan.opts.setdefault("art", {})
    blank, out = None, []
    # its campaign-select map gets the stand-in of this map (own_select_map), not an empty picture
    select_map = os.path.relpath(FA.map_name(plan.mod.campaign_dir(campaign), new), plan.mod.data).replace("\\", "/")
    for e in pics:
        rel = e.get("rel") or ""
        if rel.startswith("symbol:"):
            mine = rel                                  # its own flag slot / logos (symbols.give_own made them)
        elif own.search(rel):
            mine = own.sub(new, rel)
        else:
            continue                                    # shared with others (routing, rebels): not the frame's own
        if mine in art or mine in picks_done or mine.lower() == select_map.lower():
            continue
        if blank is None:
            try:
                from PIL import Image
                os.makedirs(folder, exist_ok=True)
                blank = os.path.join(folder, "empty_picture.png")
                Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(blank)
            except Exception:
                return out                              # no Pillow: the frame's copies stay (said in the note)
        art[mine] = blank
        out.append(mine)
    if out:
        plan.note(None, "%s from zero: %d picture(s) the brought faction has none of are left EMPTY, not %s's (%s) - "
                        "give its own on the Art tab" % (new, len(out), t, ", ".join(sorted(out)[:6]) +
                                                         (" ..." if len(out) > 6 else "")))
    return out


def select_screen_source(mod, campaign, template, bring):
    """Where the faction tab's select-screen pictures (the map, the leader's face) are read from: (mod, campaign,
    faction, frame_face). A faction brought from another mod (bring = {'src', 'faction', 'campaign'}) shows ITS
    pictures, never the frame's (a tester, 2026-10-18: the leader's face was still the template's); frame_face: the
    frame has a leader_pic of its own here, which Apply empties (blank_frame_pictures) when the brought faction has
    none - the screen then shows an empty picture, not the brought leader's portrait."""
    from .factionart import START_KINDS, start_kind, start_pictures
    if not bring:
        return mod, campaign, template, False
    try:
        from .moddata import ModData
        src = ModData(bring["src"])
        frame_face = any(start_kind(p) == START_KINDS[1] for p in start_pictures(mod, campaign, template))
        return src, bring.get("campaign") or campaign, bring["faction"], frame_face
    except Exception:
        return mod, campaign, template, False


def own_select_map(plan, campaign, new):
    """A brought faction is made from zero (report #270: 'not a clone - pictures of the clone stayed'): its
    faction-select map is never its frame's copy (the frame's land lit). It gets a stand-in, this map with no land
    lit (the user, 2026-10-15: 'a stub in case you forget and start the game' - Art's Draw from the map lights its
    land once its towns are given), unless a picture of its own was given. The picture's path, or None."""
    from . import log
    from .factionart import map_drawing, map_name
    target = map_name(plan.mod.campaign_dir(campaign), new)
    rel = os.path.relpath(target, plan.mod.data).replace("\\", "/")
    art = plan.opts.setdefault("art", {})
    if rel in art:
        return None
    try:
        im = map_drawing(plan.mod, campaign, [], (128, 128, 128))
    except Exception:
        im = None
    if im is None:
        return None
    folder = os.path.join(log.logs_dir() or os.path.expanduser("~"), "brought_pictures")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "map_%s_empty.png" % new)
    im.save(path)
    art[rel] = path
    plan.note(None, "%s's faction-select map: this map with no land lit yet - Art > Draw from the map lights its "
                    "land once its towns are given" % new)
    return path


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
    shared, brought, names = bring_units(plan, src, faction, new)
    plan.bring_start = start_of(plan, src, bring.get("campaign") or campaign, faction, new, names)
    if plan.opts.get("copy_art", True):                 # its pictures where the frame's copies went (yours win)
        from . import log
        folder = os.path.join(log.logs_dir() or os.path.expanduser("~"), "brought_pictures")
        art = plan.opts.setdefault("art", {})
        picks = art_picks(src, bring.get("campaign") or campaign, faction, new, folder)
        for rel, pic in picks.items():
            if rel in art:
                continue
            if not rel.startswith("symbol:") and _kind(pic) == _kind(rel):
                dst = os.path.join(plan.mod.data, *rel.split("/"))  # the same format: the file itself, byte for byte
                _put_over(plan, pic, dst)                # over the frame's copy queued there
            else:
                art[rel] = pic                          # a cut-out or another format: made to fit (Art's way)
        blank_frame_pictures(plan, campaign, set(art) | set(picks), folder)
    bring_sm_files(plan, src, faction, new)
    own_select_map(plan, campaign, new)
    if not plan.opts.get("names"):                      # a name list typed in the window wins (clone.names wrote it):
        bring_names(plan, src, faction, new)            # the other mod's took its place and the leader typed from it
    else:                                               # was refused (report R-20261018-B80774)
        plan.note(None, "%s's name lists: the ones typed in the window (not %s's of the other mod)" % (new, faction))
    bring_characters(plan, src, faction, new)
    bring_figures(plan, src, faction, new)
    plan.note(None, "brought from %s: %s as %s (made on %s; %d unit(s) shared, %d brought). Not brought: its towns "
                    "and armies (placed on this map), scripts and events naming it" % (
                        os.path.basename(os.path.dirname(os.path.abspath(bring["src"]))) or bring["src"], faction,
                        new, plan.template, len(shared), len(brought)))


__all__ = ["factions", "frame_of", "window_fields", "own_units", "overlay", "art_picks", "own_select_map", "select_screen_source"]
