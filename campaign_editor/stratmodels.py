"""A faction's figures on the campaign map, both games.

descr_character.txt gives every character type (named character, general, admiral, spy, assassin, diplomat,
merchant, priest, princess ...) one entry per faction group:

    faction         venice                  (or several: 'faction a, b')
    dictionary      15
    strat_model     southern_general        (more than one line: levels - Medieval II's pope, 'level 1')
    battle_model    Northern_General

descr_model_strat.txt describes each strat model: `type <name>`, skeleton, scale, `texture <faction>, <picture>`
(also `texture_no_move`), `model_flexi[_m|_c] <.cas>, <distance>` and a shadow model. A faction may use only the
character types it is listed in (the game's own words in the file's header).

Changing a figure writes the faction's strat_model line; a faction listed together with others in one `faction`
line gets an entry of its own first (the others keep theirs). A strat model the faction has no texture line in gets
one (a copy of the model's first texture line, the faction's name in it) - the Art tab then gives the faction a
picture of its own on Replace. The textures themselves are pictures the Art tab lists (clone.picture_links)."""

import re

from .textio import strip_comment, tokens

LINK_KEYS = ("texture", "texture_no_move")


def model_types(mod, load=None):
    """{strat model name: {'textures': {faction: ref}, 'meshes': [ref], 'span': (a, b)}} of descr_model_strat.txt."""
    path = mod.file("model_strat")
    if not path:
        return {}
    f = (load or mod.load)(path)
    out, cur = {}, None
    for i in range(len(f)):
        t = tokens(f.text(i))
        if not t:
            continue
        if t[0] == "type" and len(t) > 1:
            cur = " ".join(strip_comment(f.text(i)).split()[1:])
            out[cur] = {"textures": {}, "meshes": [], "span": (i, i + 1)}
            continue
        if cur is None:
            continue
        out[cur]["span"] = (out[cur]["span"][0], i + 1)
        if t[0] == "texture":
            if len(t) >= 3:
                out[cur]["textures"].setdefault(t[1], t[2])
            elif len(t) == 2:
                out[cur]["textures"].setdefault("", t[1])
        elif t[0].startswith("model_flexi") or t[0] == "model_tri":
            out[cur]["meshes"].append(t[1])
    return out


def _entries(f):
    """[{'type', 'factions', 'head' (the faction line), 'end', 'models': [(line, name)]}] of descr_character.txt:
    every faction group of every character type."""
    out, ctype, cur = [], None, None
    for i in range(len(f)):
        code = strip_comment(f.text(i)).strip()
        if not code:
            continue
        word = code.split(None, 1)[0]
        if word == "type":
            parts = code.split(None, 1)
            ctype = parts[1].strip() if len(parts) > 1 else ""
            cur = None
            continue
        if word == "faction" and ctype is not None:
            cur = {"type": ctype, "factions": tokens(code)[1:], "head": i, "end": i + 1, "models": []}
            out.append(cur)
            continue
        if cur is None:
            continue
        if word in ("actions", "wage_base", "starting_action_points"):
            cur = None                                  # a type's own lines, never inside a faction group
            continue
        cur["end"] = i + 1
        if word == "strat_model":
            t = tokens(code)
            if len(t) > 1:
                cur["models"].append((i, t[1]))
    return out


def figures(mod, faction, load=None):
    """[{'type': character type, 'models': [strat model per level], 'shared': [other factions of its entry]}] -
    the faction's figures on the campaign map, in the file's order."""
    path = mod.file("character")
    if not path:
        return []
    out = []
    for e in _entries((load or mod.load)(path)):
        if faction in e["factions"] and e["models"]:
            out.append({"type": e["type"], "models": [m for _, m in e["models"]],
                        "shared": [x for x in e["factions"] if x != faction]})
    return out


def _own_entry(f, e, faction):
    """The faction's entry split out of a shared one: its name taken out of the shared faction line, a copy of the
    group for it alone put right after. Returns the new entry's head line index."""
    head = f.text(e["head"])
    rest = [x for x in e["factions"] if x != faction]
    code = strip_comment(head).rstrip()
    comment = head[len(code):]                          # the spacing before a comment stays with it
    lead = code[:len(code) - len(code.lstrip())]
    word_gap = code.lstrip()[len("faction"):]
    gap = word_gap[:len(word_gap) - len(word_gap.lstrip())] or "\t"
    f.set(e["head"], "%sfaction%s%s%s" % (lead, gap, ", ".join(rest), comment))
    body = [f.raw[i] for i in range(e["head"] + 1, e["end"])]
    first = f.raw[e["head"]]
    nl = first[len(first.rstrip("\r\n")):] or "\n"
    new_head = "%sfaction%s%s%s" % (lead, gap, faction, nl)
    f.insert_raw(e["end"], [nl, new_head] + body)
    return e["end"] + 1


def set_figure(plan, faction, ctype, models):
    """The faction's figure for character type `ctype`: its strat_model lines name `models` (one per level, as
    many as it has). A strat model the faction has no texture in gets a texture line. Returns the changes made."""
    mod = plan.mod
    path = mod.file("character")
    f = plan.edit(path)
    e = next((x for x in _entries(f) if x["type"] == ctype and faction in x["factions"] and x["models"]), None)
    if e is None:
        raise ValueError("%s has no %s in descr_character.txt" % (faction, ctype))
    kinds = model_types(mod, plan.edit)
    for m in models:
        if m not in kinds:
            raise ValueError("'%s' is not a model of descr_model_strat.txt" % m)
    now = [m for _, m in e["models"]]
    want = list(models)[:len(now)] + now[len(models):]
    if want == now:
        return []
    if len(e["factions"]) > 1:
        head = _own_entry(f, e, faction)
        e = next(x for x in _entries(f) if x["head"] == head)
        plan.note(f, "%s: %s's entry split out of the one it shared with %s" % (
            ctype, faction, ", ".join(x for x in e["factions"] if x != faction) or "others"))
    done = []
    for (i, old), new in zip(e["models"], want):
        if old != new:                                  # only the value: spacing and comment stay
            f.set(i, re.sub(r"^(\s*strat_model\s+)%s" % re.escape(old), lambda m: m.group(1) + new, f.text(i),
                            count=1))
            done.append((old, new))
    for old, new in done:
        plan.note(f, "%s's %s on the campaign map: %s (was %s)" % (faction, ctype, new, old))
        _texture_for(plan, faction, new, kinds)
    return done


def _texture_for(plan, faction, model, kinds):
    """A texture line for the faction in the strat model, when it has none: a copy of the model's first one."""
    info = kinds.get(model)
    if not info or faction in info["textures"] or not info["textures"]:
        return
    f = plan.edit(plan.mod.file("model_strat"))
    a, b = info["span"]
    for i in range(a, b):
        t = tokens(f.text(i))
        if t[:1] == ["texture"] and len(t) >= 3:
            raw = f.raw[i]
            code = strip_comment(raw.rstrip("\r\n"))
            at = code.find(t[1], code.find("texture") + len("texture"))
            line = raw[:at] + faction + raw[at + len(t[1]):]
            f.insert_raw(i + 1, [line])
            plan.note(f, "%s: a texture line for %s (the picture %s's - Replace on the Art tab gives it its own)"
                      % (model, faction, t[1]))
            return


def faction_figures(mod, source, load=None):
    """The figures of another faction to take whole (the Models tab's 'as the faction'): ({character type: [strat
    model per level]}, {strat model: source} - whose texture each takes, its colours)."""
    figs = {fg["type"]: list(fg["models"]) for fg in figures(mod, source, load)}
    return figs, {m: source for ms in figs.values() for m in ms}


def culture_factions(mod, culture, but=None):
    """The culture's factions in descr_sm_factions.txt's order (the rebels and `but` left out)."""
    return [n for n, c in mod.factions() if c == culture and n not in ("slave", but)]


def culture_figures(mod, culture, load=None, but=None):
    """The figures of a culture (the Models tab's culture switch - the user, 2026-10-10: 'the culture: simply the
    first faction of it in the list'): faction_figures of the culture's first faction (but: the faction being
    changed, never its own source); ({}, {}) when the culture has none."""
    facs = culture_factions(mod, culture, but)
    return faction_figures(mod, facs[0], load) if facs else ({}, {})


def apply(plan, faction, wanted, like=None):
    """opts['figures'] = {character type: [strat model per level]}; like = {strat model: faction} - the faction's
    texture in each of those models becomes that faction's (its colours), taken whole from it."""
    for ctype, models in sorted((wanted or {}).items()):
        set_figure(plan, faction, ctype, list(models))
    if like:
        shown = {m for fg in figures(plan.mod, faction, plan.edit) for m in fg["models"]}
        for model, src in sorted(like.items()):
            if model in shown and src != faction:
                _texture_like(plan, faction, model, src)


def _texture_like(plan, faction, model, src):
    """The faction's texture line in the strat model names src's picture (a line of its own made when it has none)."""
    info = model_types(plan.mod, plan.edit).get(model)
    if not info or src not in info["textures"]:
        return
    f = plan.edit(plan.mod.file("model_strat"))
    a, b = info["span"]
    lines = [(i, tokens(f.text(i))) for i in range(a, b)]
    srcl = next((i for i, t in lines if t[:1] == ["texture"] and len(t) >= 3 and t[1] == src), None)
    mine = next((i for i, t in lines if t[:1] == ["texture"] and len(t) >= 3 and t[1] == faction), None)
    ref = tokens(f.text(srcl))[2]
    if mine is not None:
        now = tokens(f.text(mine))[2]
        if now != ref:
            f.set(mine, f.text(mine).replace(now, ref, 1))
            plan.note(f, "%s: %s's texture is %s's now (%s, was %s)" % (model, faction, src, ref, now))
        return
    raw = f.raw[srcl]
    code = strip_comment(raw.rstrip("\r\n"))
    at = code.find(src, code.find("texture") + len("texture"))
    f.insert_raw(srcl + 1, [raw[:at] + faction + raw[at + len(src):]])
    plan.note(f, "%s: a texture line for %s - %s's picture (%s)" % (model, faction, src, ref))


def mesh_info(mod, model, load=None):
    """The strat model as a models.ModelInfo for the 3D view (its textures per faction, its .cas files), or None."""
    from .models import ModelInfo
    got = model_types(mod, load).get(model)
    if not got:
        return None
    info = ModelInfo(model)
    info.textures = {k: (v[5:] if v.lower().startswith("data/") else v) for k, v in got["textures"].items()}
    info.meshes = [m[5:] if m.lower().startswith("data/") else m for m in got["meshes"]]
    return info
