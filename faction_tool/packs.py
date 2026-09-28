"""Unit packs: units taken out of one mod with everything they need, and put into another.

A pack is one .zip:
  manifest.json   what is in it (game, units, blocks, texts, recruit places, files)
  files/<path>    the files the units use, at their path under data/ (models, textures,
                  sprites, cards, info pictures)

What a unit needs, found by following its lines (the same in Rome and Medieval II):
  export_descr_unit.txt   the unit's block
  descr_model_battle.txt  the models its 'soldier' and 'officer' lines name (and its mount's /
                          animals' models), with every file those blocks name (.cas, .tga -
                          Rome keeps them as .tga.dds -, .spr, .mesh, .texture, ...)
  descr_mount.txt         its 'mount'; descr_engines.txt its 'engine'; descr_animals.txt its 'animal'
  export_units.txt        {dict}, {dict}_descr, {dict}_descr_short
  ui/units, ui/unit_info  its card and info picture, per faction
  export_descr_buildings  where it is recruited (chain, level, the recruit line)

Putting a pack in (import_pack) is a Plan like every other change: Preview, a backup,
Restore. Nothing of the target mod is overwritten: a unit or dictionary name that is taken
gets a new one, a model type that exists with other content is added under a new name, a
file that exists with other bytes is kept (and said). Same game only (Rome to Rome - HLR and
REX included -, Medieval II to Medieval II)."""

import io
import json
import os
import re
import zipfile

from .moddata import _ci
from .textio import TextFile, strip_comment, tokens

PACK_VERSION = 1
FILE_EXT = (".cas", ".tga", ".dds", ".spr", ".mesh", ".texture", ".ms3d", ".png", ".bmp")
DEP_FILES = {"model": "descr_model_battle.txt", "mount": "descr_mount.txt",
             "engine": "descr_engines.txt", "animal": "descr_animals.txt"}


# ---------------------------------------------------------------------------
# Blocks: 'type <name>' up to the next 'type' line
# ---------------------------------------------------------------------------
def type_blocks(f):
    """{name: (start, end)} of a file made of 'type <name>' blocks (EDU, descr_model_battle,
    descr_mount, descr_engines, descr_animals). Names may hold spaces (descr_mount)."""
    out, cur = {}, None
    for i in range(len(f.raw)):
        t = tokens(f.text(i))
        if t[:1] == ["type"] and len(t) > 1:
            if cur:
                out[cur[0]] = (cur[1], i)
            cur = (" ".join(strip_comment(f.text(i)).split()[1:]), i)
    if cur:
        out[cur[0]] = (cur[1], len(f.raw))
    return out


def _block_lines(f, span):
    lines = [f.text(i) for i in range(*span)]
    while lines and not strip_comment(lines[-1]).strip():
        lines.pop()                                    # the blank lines between blocks stay behind
    return lines


def _values(lines, key):
    """The values of every 'key a, b, c' line (comment stripped), as lists."""
    out = []
    for l in lines:
        code = strip_comment(l).strip()
        if code.split(None, 1)[:1] == [key]:
            rest = code[len(key):].strip()
            out.append([x.strip() for x in rest.split(",")])
    return out


def _file_refs(lines):
    """Every token of the lines that names a file (by its extension)."""
    refs = []
    for l in lines:
        for part in re.split(r"[,\s]+", strip_comment(l)):
            if part.lower().endswith(FILE_EXT) and "/" in part.replace("\\", "/"):
                refs.append(part.replace("\\", "/"))
    return refs


def _on_disk(mod, ref):
    """(data-relative path, absolute path) of a file a model line names, or None. Rome
    writes 'data/models_unit/x.tga' and keeps x.tga.dds; Medieval II 'unit_models/...'."""
    rel = ref[5:] if ref.lower().startswith("data/") else ref
    for cand in (rel, rel + ".dds"):
        folder, name = os.path.split(os.path.join(mod.data, *cand.split("/")))
        p = _ci(folder, name) if os.path.isdir(folder) else None
        if p:
            return os.path.relpath(p, mod.data).replace("\\", "/"), p
    return None


def game_kind(mod):
    """'medieval2' or 'rome' - packs go between mods of the same game."""
    from .newmod import game_of, is_medieval2
    try:
        if is_medieval2(game_of(mod.data)):
            return "medieval2"
    except Exception:
        pass
    return "medieval2" if os.path.isdir(os.path.join(mod.data, "unit_models")) else "rome"


# ---------------------------------------------------------------------------
# Taking units out
# ---------------------------------------------------------------------------
def collect(mod, unit_types):
    """The pack's contents for these units: a dict (the manifest) and {data path: bytes}."""
    edu = mod.load(mod.file("edu"))
    blocks = type_blocks(edu)
    deps = {k: (mod.load(p) if p else None) for k, p in
            ((k, _ci(mod.data, v)) for k, v in DEP_FILES.items())}
    dep_blocks = {k: type_blocks(f) if f else {} for k, f in deps.items()}
    manifest = {"pack": PACK_VERSION, "game": game_kind(mod), "units": [], "blocks": {k: {} for k in DEP_FILES},
                "texts": {}, "recruit": [], "files": [], "missing": []}
    files = {}

    def add_files(lines):
        for ref in _file_refs(lines):
            got = _on_disk(mod, ref)
            if got is None:
                if ref not in manifest["missing"]:
                    manifest["missing"].append(ref)
                continue
            rel, path = got
            if rel not in files:
                with open(path, "rb") as fh:
                    files[rel] = fh.read()

    def add_dep(kind, name):
        if not name or name in manifest["blocks"][kind]:
            return
        span = dep_blocks[kind].get(name)
        if span is None:
            manifest["missing"].append("%s %s" % (DEP_FILES[kind], name))
            return
        lines = _block_lines(deps[kind], span)
        manifest["blocks"][kind][name] = lines
        add_files(lines)
        for v in _values(lines, "model"):                  # a mount's / animal's model
            if kind != "model":
                add_dep("model", v[0])

    for t in unit_types:
        span = blocks.get(t)
        if span is None:
            raise ValueError("no unit '%s' in export_descr_unit.txt" % t)
        lines = _block_lines(edu, span)
        d = next((v[0] for v in _values(lines, "dictionary")), None)
        manifest["units"].append({"type": t, "dictionary": d, "lines": lines})
        for key, kind in (("soldier", "model"), ("officer", "model"), ("mount", "mount"),
                          ("engine", "engine"), ("animal", "animal")):
            for v in _values(lines, key):
                add_dep(kind, v[0])
        if d:
            for key in (d, d + "_descr", d + "_descr_short"):
                val = _text_entry(mod, "export_units.txt", key)
                if val is not None:
                    manifest["texts"][key] = val
            for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
                folder = os.path.join(mod.data, "ui", sub)
                if not os.path.isdir(folder):
                    continue
                for fac in sorted(os.listdir(folder)):
                    p = _ci(os.path.join(folder, fac), pattern % d) if os.path.isdir(os.path.join(folder, fac)) else None
                    if p:
                        with open(p, "rb") as fh:
                            files[os.path.relpath(p, mod.data).replace("\\", "/")] = fh.read()
    manifest["recruit"] = _recruit_places(mod, unit_types)
    manifest["files"] = sorted(files)
    return manifest, files


def _text_entry(mod, table, key):
    """The whole value of {key} in a string table (lines after the first kept), or None."""
    from .clone import entry_end_in
    path = mod.text_file(table)
    if not path:
        return None
    f = mod.load(path)
    low = key.lower()
    for i in range(len(f.raw)):
        s = f.text(i).lstrip()
        if s.startswith("{") and "}" in s and s[1:s.index("}")].lower() == low:
            end = entry_end_in(f, i)
            return [s[s.index("}") + 1:]] + [f.text(k) for k in range(i + 1, end)]
    return None


def _recruit_places(mod, unit_types):
    """[{'unit', 'chain', 'level', 'line'}]: every recruit line naming these units."""
    from .editors import building_blocks, chain_tree
    if not mod.file("edb"):
        return []
    f = mod.load(mod.file("edb"))
    want = {'"%s"' % t: t for t in unit_types}
    out = []
    for name, a, b in building_blocks(f):
        tree = chain_tree(f, a, b)
        for lv in tree["levels"]:
            if not lv["capability"]:
                continue
            op, cl = lv["capability"]
            for i in range(op, cl):
                text = f.text(i)
                if tokens(text)[:1] == ["recruit"]:
                    for q, t in want.items():
                        if q in text:
                            out.append({"unit": t, "chain": name, "level": lv["name"], "line": text.strip()})
    return out


def export_pack(mod, unit_types, path):
    """Write the pack .zip for these units; returns the manifest."""
    manifest, files = collect(mod, unit_types)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=1))
        for rel, data in sorted(files.items()):
            z.writestr("files/" + rel, data)
    return manifest


def read_pack(path):
    """(manifest, {data path: bytes}) of a pack .zip."""
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
        files = {n[6:]: z.read(n) for n in z.namelist() if n.startswith("files/") and not n.endswith("/")}
    if manifest.get("pack") != PACK_VERSION:
        raise ValueError("not a unit pack of this tool (or a newer one)")
    return manifest, files


# ---------------------------------------------------------------------------
# Putting units in
# ---------------------------------------------------------------------------
def free_name(taken, name, sep="_"):
    """name, or name + _2, _3... when taken (compared without case)."""
    low = {x.lower() for x in taken}
    if name.lower() not in low:
        return name
    n = 2
    while ("%s%s%d" % (name, sep, n)).lower() in low:
        n += 1
    return "%s%s%d" % (name, sep, n)


def plan_names(mod, manifest):
    """{old type: (new type, new dictionary)}: the pack's names, or free ones where the target
    mod has them already."""
    edu = mod.load(mod.file("edu"))
    types = set(type_blocks(edu))
    dicts = set()
    for name, (a, b) in type_blocks(edu).items():
        dicts |= {v[0] for v in _values(_block_lines(edu, (a, b)), "dictionary")}
    out = {}
    for u in manifest["units"]:
        t = free_name(types, u["type"], sep=" ")
        d = free_name(dicts, u["dictionary"]) if u.get("dictionary") else None
        types.add(t)
        if d:
            dicts.add(d)
        out[u["type"]] = (t, d)
    return out


def _set_line(lines, key, value):
    """lines with the first 'key ...' line's value replaced (the key's spacing kept)."""
    out, done = [], False
    for l in lines:
        m = re.match(r"^(\s*%s\s+)([^;]*?)(\s*(;.*)?)$" % re.escape(key), l)
        if m and not done:
            out.append(m.group(1) + value + m.group(3))
            done = True
        else:
            out.append(l)
    return out


def _rename_ref(lines, key, old, new):
    """'key old, ...' lines naming old renamed to new (the rest of the line kept)."""
    out = []
    for l in lines:
        m = re.match(r"^(\s*%s\s+)(%s)(\s*(,|;|$).*)$" % (re.escape(key), re.escape(old)), l)
        out.append(m.group(1) + new + m.group(3) if m else l)
    return out


def import_pack(plan, manifest, files, owners, names=None):
    """Put the pack into plan.mod: units given to owners (factions or cultures), under names
    {old type: (type, dictionary)} (plan_names by default). Everything goes through the plan."""
    mod = plan.mod
    if manifest.get("game") and manifest["game"] != game_kind(mod):
        raise ValueError("this pack is from %s, the mod is %s - packs go between mods of one game" % (
            "Medieval II" if manifest["game"] == "medieval2" else "Rome", "Medieval II" if game_kind(mod) ==
            "medieval2" else "Rome"))
    if not owners:
        raise ValueError("pick at least one faction (or culture) the units go to")
    names = names or plan_names(mod, manifest)
    facs = [n for n, _ in mod.factions()]
    known = set(facs) | {mod.culture(n) for n in facs if mod.culture(n)} | {"all"}
    bad = [o for o in owners if known and o not in known]
    if bad:
        raise ValueError("no faction or culture %s in this mod" % ", ".join(bad))
    # dependency blocks: the same content is shared, another content with the same name is renamed
    renamed = {k: {} for k in DEP_FILES}
    for kind in ("model", "mount", "engine", "animal"):
        want = manifest["blocks"].get(kind) or {}
        if not want:
            continue
        path = _ci(mod.data, DEP_FILES[kind])
        if not path:
            raise ValueError("%s is missing in this mod" % DEP_FILES[kind])
        f = plan.edit(path)
        have = type_blocks(f)
        for name, lines in want.items():
            if kind == "mount" or kind == "animal":
                for old, new in renamed["model"].items():
                    lines = _rename_ref(lines, "model", old, new)
            if name in have:
                if [strip_comment(x).split() for x in _block_lines(f, have[name])] == \
                        [strip_comment(x).split() for x in lines]:
                    continue                                   # the very same: shared
                new = free_name(have, name, sep="_" if kind == "model" else " ")
                renamed[kind][name] = new
                lines = _set_line(lines, "type", new)
                plan.note(f, "%s %s exists with other lines: the pack's is added as %s" % (kind, name, new))
            while f.raw and not f.text(len(f.raw) - 1).strip():
                del f.raw[-1]
            f.raw.extend(f.make(x) for x in [""] + lines + [""])
            have[renamed[kind].get(name, name)] = (0, 0)
            plan.note(f, "%s %s added" % (kind, renamed[kind].get(name, name)))
    # the units
    edu = plan.edit(mod.file("edu"))
    while edu.raw and not edu.text(len(edu.raw) - 1).strip():
        del edu.raw[-1]
    text_renames = {}
    for u in manifest["units"]:
        t, d = names[u["type"]]
        lines = _set_line(u["lines"], "type", t)
        if d:
            lines = _set_line(lines, "dictionary", d)
        for key, kind in (("soldier", "model"), ("officer", "model"), ("mount", "mount"),
                          ("engine", "engine"), ("animal", "animal")):
            for old, new in renamed[kind].items():
                lines = _rename_ref(lines, key, old, new)
        lines = _set_line(lines, "ownership", ", ".join(owners))
        edu.raw.extend(edu.make(x) for x in [""] + lines)
        plan.note(edu, "unit %s added (dictionary %s), owned by %s" % (t, d, ", ".join(owners)))
        if d and u.get("dictionary"):
            for suffix in ("", "_descr", "_descr_short"):
                text_renames[u["dictionary"] + suffix] = d + suffix
    edu.raw.append(edu.make(""))
    # texts
    table = mod.text_file("export_units.txt")
    if table and manifest.get("texts"):
        tf = plan.edit(table)
        while tf.raw and not tf.text(len(tf.raw) - 1).strip():
            del tf.raw[-1]
        n = 0
        for key, value in manifest["texts"].items():
            new = text_renames.get(key, key)
            tf.raw.extend(tf.make(x) for x in ["{%s}%s" % (new, value[0])] + value[1:])
            n += 1
        tf.raw.append(tf.make(""))
        plan.note(tf, "%d name(s) and description(s) added" % n)
    # files: models, textures, sprites as they are; cards and info pictures for each owner faction
    factions = [o for o in owners if o in {n for n, _ in mod.factions()}]
    dict_of = {u["dictionary"]: names[u["type"]][1] for u in manifest["units"] if u.get("dictionary")}
    for rel, data in sorted(files.items()):
        parts = rel.split("/")
        if len(parts) == 4 and parts[0].lower() == "ui" and parts[1].lower() in ("units", "unit_info"):
            continue                                           # cards: below, per owner
        _put(plan, rel, data)
    for old, new in dict_of.items():
        for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
            src = [(rel, data) for rel, data in files.items()
                   if rel.lower().startswith("ui/%s/" % sub) and rel.split("/")[-1].lower() == (pattern % old).lower()]
            if not src:
                continue
            for fac in factions or [src[0][0].split("/")[2]]:
                pick = next((data for rel, data in src if rel.split("/")[2] == fac), src[0][1])
                _put(plan, "ui/%s/%s/%s" % (sub, fac, pattern % new), pick)
    # recruiting: the same chain and level as in the source mod, where the target has them
    if manifest.get("recruit") and mod.file("edb"):
        _recruit(plan, manifest, names, owners)
    missing = manifest.get("missing") or []
    if missing:
        plan.warn(None, "%d file(s) the units name were not in the source mod, so not in the pack either "
                        "(the game may take them from its own data): %s%s" % (
                            len(missing), ", ".join(missing[:4]), " ..." if len(missing) > 4 else ""))
    # a model with a texture per faction: say which owners it has none for
    for name, lines in (manifest["blocks"].get("model") or {}).items():
        textured = {v[0] for v in _values(lines, "texture") if len(v) > 1}
        lack = [o for o in factions if textured and o not in textured]
        if lack:
            plan.warn(None, "model %s has no texture line for %s - the game shows another faction's "
                            "texture (a recolour for them is planned)" % (renamed["model"].get(name, name),
                                                                         ", ".join(lack)))
    return plan


def _put(plan, rel, data):
    path = os.path.join(plan.mod.data, *rel.split("/"))
    if os.path.exists(path):
        with open(path, "rb") as fh:
            if fh.read() == data:
                return
        plan.warn(None, "%s exists with other content - the mod's own is kept" % rel)
        return
    plan.binary(path, data)
    plan.notes.append((plan.mod.rel(path), "from the pack"))


def _recruit(plan, manifest, names, owners):
    from .editors import building_blocks, chain_tree, line_place
    f = plan.edit(plan.mod.file("edb"))
    n, missing = 0, set()
    for r in manifest["recruit"]:
        blocks = {b[0]: b for b in building_blocks(f)}
        blk = blocks.get(r["chain"])
        tree = chain_tree(f, blk[1], blk[2]) if blk else None
        if not tree or not any(lv["name"] == r["level"] for lv in tree["levels"]):
            missing.add("%s %s" % (r["chain"], r["level"]))
            continue
        line = r["line"].replace('"%s"' % r["unit"], '"%s"' % names[r["unit"]][0], 1)
        line = re.sub(r"factions\s*\{[^}]*\}", "factions { %s, }" % ", ".join(owners), line, count=1)
        at, make = line_place(f, "building", blk, "capability", r["level"], "recruit")
        f.insert(at, make(line))
        n += 1
    if n:
        plan.note(f, "%d recruit line(s) added" % n)
    for m in sorted(missing):
        plan.warn(f, "no %s in this mod: recruit the units there by hand (Building editor)" % m)


__all__ = ["type_blocks", "collect", "export_pack", "read_pack", "plan_names", "import_pack", "game_kind"]
