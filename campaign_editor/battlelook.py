"""A building's look on the battle map (Rome, Barbarian Invasion, REX), taken along when a building chain is brought
from another mod (report R-20261014-6E55CD: a brought church stood in town as the game's stand-in model).

What the game follows, four knots of one web:
  descr_settlement_plan.txt      a 'variant' inside a named slot ('slot slot_160x128_religious') names
                                 'exact <chain> <level>' and the battle building to stand there
                                 ('BI_christian_church, 0, 0, 0, 0'); 'primary' lists the battle buildings that are a
                                 campaign building's body (damage counts there)
  descr_building_battle(/dbb_*)  that battle building: its levels -> 'item <name>', physical_info, transition
  descr_items(/di_*)             'type <item>': its lod models (.cas); descr_items.db is the game's compiled copy -
                                 the game writes it again from the .txt when it is gone (RomeTW.exe FUN_00ade962)
  the files                      the models and textures they name

Taking out (collect): every variant naming a picked chain, with its slot's name, the battle buildings and items they
use (each by name, through the includes), and the files named by plain paths. Putting in (put): the variants into
the same-named slots of this mod's plan (chain / level renamed with the building), the battle buildings into
descr_building_battle/dbb_campaign_editor.txt and the items into descr_items/di_campaign_editor.txt (each included
once from its main file), descr_items.db removed. A name this mod has with the same lines is shared, with other
lines added under a free name and every line naming it follows. Paths starting '../' (BI's models read from
bi/data) stay as they are: they point into the same game folder. Medieval II: not yet (its plans differ)."""

import os
import re

from .textio import strip_comment

OWN_DBB = "dbb_campaign_editor.txt"
OWN_DI = "di_campaign_editor.txt"


def _code(line):
    return strip_comment(line).strip()


def children(texts, a=0, b=None):
    """[(header tokens, header line, close line)] of the blocks directly inside texts[a:b] - a header is the last
    code line before a '{' (or the words before '{' on its own line)."""
    b = len(texts) if b is None else b
    out, depth, head, start = [], 0, None, None
    for i in range(a, b):
        code = _code(texts[i])
        if not code:
            continue
        for part in re.split(r"([{}])", code):
            part = part.strip()
            if not part:
                continue
            if part == "{":
                if depth == 0:
                    start = head
                depth += 1
            elif part == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    out.append((start[0], start[1], i))
                    start = None
                if depth < 0:
                    depth = 0
            elif depth == 0:
                head = (part.split(), i)
    return out


def _body(texts, a):
    """The first line inside the block whose header is line a (after its '{')."""
    for i in range(a, len(texts)):
        if "{" in _code(texts[i]):
            return i + 1
    return a + 1


def _includes(mod, main, folder):
    """[path] of the main file and every file its 'include' lines name (in data/<folder>/), as the game reads them."""
    p = mod.find(main)
    if not p:
        return []
    out = [p]
    for line in mod.load(p).texts():
        t = _code(line).split()
        if len(t) == 2 and t[0] == "include":
            q = mod.find("%s/%s" % (folder, t[1]))
            if q:
                out.append(q)
    return out


def battle_buildings(mod):
    """{name: (path, header line, close line)} of every battle building of descr_building_battle and its includes."""
    out = {}
    for p in _includes(mod, "descr_building_battle.txt", "descr_building_battle"):
        texts = mod.load(p).texts()
        for head, a, b in children(texts):
            if len(head) == 1:
                out.setdefault(head[0], (p, a, b))
    return out


def items(mod):
    """{name: (path, first line, end)} of every 'type <name>' item of descr_items and its includes."""
    from .packs import type_blocks
    out = {}
    for p in _includes(mod, "descr_items.txt", "descr_items"):
        for name, span in type_blocks(mod.load(p)).items():
            out.setdefault(name, (p,) + span)
    return out


def _block(mod, where, closed):
    p, a, b = where
    texts = mod.load(p).texts()
    lines = texts[a:b + 1] if closed else texts[a:b]
    while lines and not _code(lines[-1]):
        lines.pop()
    return lines


def _plan_parts(texts):
    """{'primary': (a, b), 'slots': {slot name: (header, close, section)}} of a settlement plan."""
    out = {"primary": None, "slots": {}}
    for head, a, b in children(texts):
        if head == ["primary"]:
            out["primary"] = (a, b)
        elif head and head[0] in ("slots", "gateway_slots"):
            for h, x, y in children(texts, _body(texts, a), b):
                if len(h) == 2 and h[0] in ("slot", "gateway_slot"):
                    out["slots"].setdefault(h[1], (x, y, head[0]))
    return out


def _named(texts, a, b):
    """The chain / level pairs a variant's 'buildings' block names: [(line, chain, level)]."""
    out = []
    for h, x, y in children(texts, _body(texts, a), b):
        if h == ["buildings"]:
            for i in range(_body(texts, x), y):
                t = _code(texts[i]).replace("{", " ").replace("}", " ").split()
                if t and t[0] == "exact":
                    t = t[1:]
                if len(t) >= 2:
                    out.append((i, t[0], t[1]))
                elif len(t) == 1:
                    out.append((i, t[0], None))
    return out


def _uses(lines):
    """The battle buildings a variant places: the first word of its 'name, x, z, angle, height' lines."""
    out = []
    for line in lines:
        code = _code(line)
        if "," in code and "{" not in code:
            name = code.split(",")[0].strip()
            if name and " " not in name and name not in out:
                out.append(name)
    return out


def collect(mod, chains, files):
    """{'variants': [{'slot', 'lines'}], 'buildings': {name: lines}, 'items': {name: lines}, 'primary': [names]}
    for these chains (files gets the models / textures named by plain paths). None when the mod has no plan."""
    from .packs import _file_refs, _on_disk
    p = mod.find("descr_settlement_plan.txt")
    if not p:
        return None
    texts = mod.load(p).texts()
    parts = _plan_parts(texts)
    want = {c.lower() for c in chains}
    out = {"variants": [], "buildings": {}, "items": {}, "primary": [], "missing": []}
    used = []
    for slot, (a, b, _) in parts["slots"].items():
        for h, x, y in children(texts, _body(texts, a), b):
            if h != ["variant"]:
                continue
            named = _named(texts, x, y)
            if named and any(c.lower() in want for _, c, _ in named):
                lines = texts[x:y + 1]
                out["variants"].append({"slot": slot, "lines": lines})
                used += [u for u in _uses(lines) if u not in used]
    if not out["variants"]:
        return out
    if parts["primary"]:
        a, b = parts["primary"]
        prim = {_code(t) for t in texts[_body(texts, a):b]}
        out["primary"] = [u for u in used if u in prim]
    bb, it = battle_buildings(mod), items(mod)
    refs = []
    for name in used:
        if name not in bb:
            out["missing"].append("battle building %s" % name)
            continue
        lines = _block(mod, bb[name], True)
        out["buildings"][name] = lines
        refs += lines
        for line in lines:
            t = _code(line).split()
            if len(t) == 2 and t[0] == "item" and t[1] not in out["items"]:
                if t[1] in it:
                    out["items"][t[1]] = _block(mod, it[t[1]], False)
                    refs += out["items"][t[1]]
                else:
                    out["missing"].append("item %s" % t[1])
    for ref in _file_refs(refs):
        if ref.startswith(".."):
            continue                                   # BI's '../../bi/data/...': the same game folder
        got = _on_disk(mod, ref)
        if got and got[0] not in files:
            with open(got[1], "rb") as fh:
                files[got[0]] = fh.read()
    return out


def _same(a, b):
    return [_code(x).split() for x in a if _code(x)] == [_code(x).split() for x in b if _code(x)]


def _rename_words(lines, names):
    """Whole words of lines renamed {old: new} (code only; comments kept)."""
    if not names:
        return lines
    pat = re.compile(r"(?<![A-Za-z0-9_])(%s)(?![A-Za-z0-9_])" % "|".join(re.escape(k) for k in
                                                                        sorted(names, key=len, reverse=True)))
    out = []
    for line in lines:
        code, sep, rest = line.partition(";")
        out.append(pat.sub(lambda m: names[m.group(1)], code) + sep + rest)
    return out


def _own_file(plan, main, folder, own, blocks, note):
    """blocks (lists of lines) into data/<folder>/<own> (made or added to), included once from the main file."""
    mod = plan.mod
    have = mod.find("%s/%s" % (folder, own))
    if have:
        f = plan.edit(have)
        while f.raw and not f.text(len(f.raw) - 1).strip():
            del f.raw[-1]
        for b in blocks:
            f.raw.extend(f.make(x) for x in [""] + b)
        f.raw.append(f.make(""))
        plan.note(f, note)
    else:
        path = os.path.join(mod.data, folder, own)
        body = ["; %s - brought by RTW & M2TW Campaign Editor (Bring from another mod); included from %s" % (
            own, main)]
        for b in blocks:
            body += [""] + b
        plan.binary(path, ("\r\n".join(body + [""])).encode("latin-1", "replace"))
        plan.notes.append((mod.rel(path), note))
    mp = mod.find(main)
    f = plan.edit(mp)
    texts = f.texts()
    if any(_code(t).split() == ["include", own] for t in texts):
        return
    last = max((i for i, t in enumerate(texts) if _code(t).split()[:1] == ["include"]), default=None)
    at = last + 1 if last is not None else len(texts)
    f.insert(at, ["include %s" % own])
    plan.note(f, "include %s" % own)


def put(plan, look, chain_names, level_names):
    """The battle look of brought chains into plan.mod (see the module's text). Says what it could not place."""
    from .packs import free_name
    mod = plan.mod
    if not look or not look.get("variants"):
        return
    p = mod.find("descr_settlement_plan.txt")
    if not p:
        plan.warn(None, "no descr_settlement_plan.txt in this mod - the brought buildings show the game's stand-in "
                        "model in battle")
        return
    # names: the same lines shared, other lines under a free name
    bb_here, it_here = battle_buildings(mod), items(mod)
    item_names, new_items = {}, []
    for name, lines in look["items"].items():
        if name in it_here:
            if _same(_block(mod, it_here[name], False), lines):
                continue
            item_names[name] = free_name(set(it_here) | set(item_names.values()), name)
        new_items.append(name)
    bb_names, new_bb = {}, []
    for name, lines in look["buildings"].items():
        lines = _rename_words(lines, item_names)
        if name in bb_here:
            if _same(_block(mod, bb_here[name], True), lines):
                continue
            bb_names[name] = free_name(set(bb_here) | set(bb_names.values()), name)
        new_bb.append(name)
    if new_items:
        blocks = []
        for name in new_items:
            lines = look["items"][name]
            if name in item_names:
                lines = [re.sub(r"^(\s*type\s+)%s\b" % re.escape(name), r"\g<1>" + item_names[name], lines[0])] + \
                    lines[1:]
            blocks.append(lines)
        _own_file(plan, "descr_items.txt", "descr_items", OWN_DI, blocks, "%d battle item(s) added: %s" % (
            len(new_items), ", ".join(item_names.get(n, n) for n in new_items)))
        db = mod.find("descr_items.db")
        if db:
            plan.delete(db, "the game writes it again from descr_items.txt on the next start")
    if new_bb:
        blocks = [_rename_words(_rename_words(look["buildings"][n], item_names), bb_names) for n in new_bb]
        _own_file(plan, "descr_building_battle.txt", "descr_building_battle", OWN_DBB, blocks,
                  "%d battle building(s) added: %s" % (len(new_bb), ", ".join(bb_names.get(n, n) for n in new_bb)))
    # the plan: each variant into its slot, the chain and levels renamed with the building
    f = plan.edit(p)
    names = dict(bb_names)
    words = {}
    words.update({k: v for k, v in chain_names.items() if k != v})
    words.update({k: v for k, v in level_names.items() if k != v})
    words.update(names)
    by_slot = {}
    for v in look["variants"]:
        by_slot.setdefault(v["slot"], []).append(_rename_words(v["lines"], words))
    placed, lost = 0, []
    for slot, variants in by_slot.items():
        parts = _plan_parts(f.texts())
        if slot not in parts["slots"]:
            lost.append(slot)
            continue
        a, b, _ = parts["slots"][slot]
        ins = []
        for v in variants:
            ins += v
            placed += 1
        f.insert(b, ins)
    if look.get("primary"):
        parts = _plan_parts(f.texts())
        if parts["primary"]:
            a, b = parts["primary"]
            have = {_code(t) for t in f.texts()[_body(f.texts(), a):b]}
            add = [names.get(n, n) for n in look["primary"] if names.get(n, n) not in have]
            if add:
                f.insert(b, ["\t%s" % n for n in add])
    if placed:
        plan.note(f, "%d place(s) in town plans for the brought buildings (their look on the battle map)" % placed)
    if lost:
        plan.warn(f, "this mod's town plans have no slot %s - the brought buildings standing there show the game's "
                     "stand-in model in battle" % ", ".join(lost))
    if look.get("missing"):
        plan.warn(None, "not found in the source mod, so not brought: %s" % ", ".join(look["missing"]))
