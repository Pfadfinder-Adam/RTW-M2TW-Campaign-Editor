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

from .moddata import _ci, ci_path
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
        p = ci_path(mod.data, cand)
        if p and os.path.isfile(p):
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
class _Gather:
    """What a pack takes: dependency blocks (models, mounts, engines, animals) with every file they name, and
    Medieval II's modeldb models - found by following names the same way for units and for single models."""

    def __init__(self, mod):
        self.mod = mod
        self.deps = {k: (mod.load(p) if p else None) for k, p in
                     ((k, _ci(mod.data, v)) for k, v in DEP_FILES.items())}
        self.dep_blocks = {k: type_blocks(f) if f else {} for k, f in self.deps.items()}
        self.manifest = {"pack": PACK_VERSION, "game": game_kind(mod), "units": [],
                         "blocks": {k: {} for k in DEP_FILES}, "texts": {}, "recruit": [], "files": [],
                         "missing": [], "modeldb": {}}
        self.files = {}
        self.db = None
        if self.manifest["game"] == "medieval2":      # Medieval II reads its battle models from the modeldb
            from . import modeldb as MDB
            src, _ = MDB.find(mod)
            self.db = MDB.load(src) if src else None

    def add_ref(self, ref):
        got = _on_disk(self.mod, ref)
        if got is None:
            if ref not in self.manifest["missing"]:
                self.manifest["missing"].append(ref)
            return
        rel, path = got
        if rel not in self.files:
            with open(path, "rb") as fh:
                self.files[rel] = fh.read()

    def add_files(self, lines):
        for ref in _file_refs(lines):
            self.add_ref(ref)

    def add_dep(self, kind, name):
        """The block kind / name and what it needs; returns the name as the files spell it (or None)."""
        from . import modeldb as MDB
        man = self.manifest
        if not name:
            return None
        if name in man["blocks"][kind] or (kind == "model" and name in man["modeldb"]):
            return name
        in_db = None
        if kind == "model" and self.db is not None:
            m = self.db.model(name)
            if m is not None:
                in_db = m.name
                if m.name not in man["modeldb"]:
                    man["modeldb"][m.name] = MDB.to_dict(m)
                    for ref in MDB.files_of(m):           # paths may hold spaces here
                        self.add_ref(ref)
        span = self.dep_blocks[kind].get(name)
        if span is None:                                   # the game reads these names without case
            low = name.lower()
            real = next((k for k in self.dep_blocks[kind] if k.lower() == low), None)
            if real is not None:
                if real in man["blocks"][kind]:
                    return real
                name, span = real, self.dep_blocks[kind][real]
        if span is None and in_db:
            return in_db
        if span is None:
            man["missing"].append("%s %s" % (DEP_FILES[kind], name))
            return None
        lines = _block_lines(self.deps[kind], span)
        man["blocks"][kind][name] = lines
        self.add_files(lines)
        for v in _values(lines, "model"):                  # a mount's / animal's model
            if kind != "model":
                self.add_dep("model", v[0])
        return in_db or name

    def done(self):
        self.manifest["files"] = sorted(self.files)
        return self.manifest, self.files


def collect(mod, unit_types):
    """The pack's contents for these units: a dict (the manifest) and {data path: bytes}."""
    edu = mod.load(mod.file("edu"))
    blocks = type_blocks(edu)
    g = _Gather(mod)
    manifest, files = g.manifest, g.files
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
                g.add_dep(kind, v[0])
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
    return g.done()


def collect_models(mod, names):
    """(manifest, files) holding battle models only - these and every file they name. Raises when one is not in
    the mod."""
    g = _Gather(mod)
    for n in names:
        if g.add_dep("model", n) is None:
            raise ValueError("no battle model '%s' in %s" % (n, mod.data))
    return g.done()


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
    """[{'unit', 'chain', 'level', 'line'}]: every recruit line naming these units
    (recruit / recruit_pool and REX's retrain lines)."""
    from .editors import building_blocks, chain_tree
    from .roster import recruit_of
    if not mod.file("edb"):
        return []
    f = mod.load(mod.file("edb"))
    want = set(unit_types)
    out = []
    for name, a, b in building_blocks(f):
        tree = chain_tree(f, a, b)
        for lv in tree["levels"]:
            if not lv["capability"]:
                continue
            op, cl = lv["capability"]
            for i in range(op, cl):
                text = f.text(i)
                r = recruit_of(text)
                if r and r[1] in want:
                    out.append({"unit": r[1], "chain": name, "level": lv["name"], "line": text.strip()})
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
        m = re.match(r"^(\s*%s\s+)(%s)(\s*(,|;|$).*)$" % (re.escape(key), re.escape(old)), l, re.I)
        out.append(m.group(1) + new + m.group(3) if m else l)
    return out


def import_pack(plan, manifest, files, owners, names=None, recruit_map=None):
    """Put the pack into plan.mod: units given to owners (factions or cultures), under names
    {old type: (type, dictionary)} (plan_names by default). recruit_map {(chain, level): (chain, level) or None}:
    where each recruit place of the source goes in this mod (None: not recruited there); a key (unit, chain, level)
    sets it for that unit alone (Bring's 'which building trains it'); by default the same chain and level when this
    mod has them. Everything goes through the plan."""
    mod = plan.mod
    if manifest.get("game") and manifest["game"] != game_kind(mod):
        raise ValueError("this pack is from %s, the mod is %s - packs go between mods of one game" % (
            "Medieval II" if manifest["game"] == "medieval2" else "Rome", "Medieval II" if game_kind(mod) ==
            "medieval2" else "Rome"))
    if not owners:
        raise ValueError("pick at least one faction (or culture) the units go to")
    names = names or plan_names(mod, manifest)
    have = {t.lower() for t in type_blocks(mod.load(mod.file("edu")))}
    for old, (t, d) in names.items():
        if not t or t.lower() in have:
            raise ValueError("a unit '%s' exists in this mod already - give the pack's %s another name" % (t, old))
        if d and (" " in d or not d.strip()):
            raise ValueError("%s: the dictionary name needs letters, digits and _ only" % t)
    facs = [n for n, _ in mod.factions()]
    known = set(facs) | {mod.culture(n) for n in facs if mod.culture(n)} | {"all"}
    bad = [o for o in owners if known and o not in known]
    if bad:
        raise ValueError("no faction or culture %s in this mod" % ", ".join(bad))
    renamed = _put_blocks(plan, manifest, owners)
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
    _put_files(plan, files)
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
        _recruit(plan, manifest, names, owners, recruit_map)
    _say_missing(plan, manifest)
    return plan


def _put_blocks(plan, manifest, owners):
    """The pack's dependency blocks (models, mounts, engines, animals) and modeldb models written into plan.mod:
    the same content is shared, another content under a taken name is added under a free one. Every faction of
    owners gets texture entries on the models. Returns {kind: {old name: new name}}."""
    mod = plan.mod
    facs = [n for n, _ in mod.factions()]
    renamed = {k: {} for k in DEP_FILES}
    owner_facs = [o for o in owners if o in set(facs)]
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
            same_name = next((k for k in have if k.lower() == name.lower()), None)
            if same_name is not None:
                if [strip_comment(x).split() for x in _block_lines(f, have[same_name])] == \
                        [strip_comment(x).split() for x in lines]:
                    if kind == "model":                        # the very same: shared, textured for the owners
                        a, b = have[same_name]
                        got, added = _owner_textures(_block_lines(f, (a, b)), owner_facs)
                        if added:
                            f.raw[a:a + len(_block_lines(f, (a, b)))] = [f.make(x) for x in got]
                            have = type_blocks(f)
                            plan.note(f, "model %s: texture lines for %s" % (same_name, ", ".join(added)))
                    continue
                new = free_name(have, name, sep="_" if kind == "model" else " ")
                renamed[kind][name] = new
                lines = _set_line(lines, "type", new)
                plan.note(f, "%s %s exists with other lines: the pack's is added as %s" % (kind, name, new))
            if kind == "model":                                # every faction the units go to gets a texture
                lines, added = _owner_textures(lines, owner_facs)
                if added:
                    plan.note(f, "model %s: texture lines for %s" % (renamed[kind].get(name, name), ", ".join(added)))
            while f.raw and not f.text(len(f.raw) - 1).strip():
                del f.raw[-1]
            f.raw.extend(f.make(x) for x in [""] + lines + [""])
            have[renamed[kind].get(name, name)] = (0, 0)
            plan.note(f, "%s %s added" % (kind, renamed[kind].get(name, name)))
    # Medieval II: the battle models in battle_models.modeldb, under the names descr_model_battle got
    if manifest.get("modeldb"):
        _modeldb(plan, manifest, renamed, owners)
    return renamed


def _put_files(plan, files):
    """The pack's files at their paths (cards and info pictures are per owner - the unit import places them)."""
    for rel, data in sorted(files.items()):
        parts = rel.split("/")
        if len(parts) == 4 and parts[0].lower() == "ui" and parts[1].lower() in ("units", "unit_info"):
            continue
        _put(plan, rel, data)


def _say_missing(plan, manifest):
    missing = manifest.get("missing") or []
    if missing:
        plan.warn(None, "%d file(s) the source names were not in the source mod, so not brought over either "
                        "(the game may take them from its own data): %s%s" % (
                            len(missing), ", ".join(missing[:4]), " ..." if len(missing) > 4 else ""))


def import_models(plan, manifest, files, owners):
    """Battle models gathered by collect_models put into plan.mod (same rules as a unit pack's models).
    Returns {old name: name in this mod}."""
    if manifest.get("game") and manifest["game"] != game_kind(plan.mod):
        raise ValueError("models go between mods of one game (this one is %s, the model's %s)" % (
            game_kind(plan.mod), manifest["game"]))
    renamed = _put_blocks(plan, manifest, owners)
    _put_files(plan, files)
    _say_missing(plan, manifest)
    names = list(manifest["blocks"]["model"]) + [n for n in manifest["modeldb"] if n not in manifest["blocks"]["model"]]
    return {n: renamed["model"].get(n, n) for n in names}


def _modeldb(plan, manifest, renamed, owners):
    """The pack's modeldb models added to the mod's battle_models.modeldb (a copy of the game's goes into the
    mod when it has none): a model with the same content is shared, another one with a taken name is added under
    a free name (the units follow it), and every faction the units go to gets a texture entry."""
    from . import modeldb as MDB
    mod = plan.mod
    src, dst = MDB.find(mod)
    if not src:
        plan.warn(None, "no battle_models.modeldb found: the units' models are only in descr_model_battle.txt")
        return
    db = MDB._db_in_plan(plan, src, dst)
    factions = [o for o in owners if o in {n for n, _ in mod.factions()}]
    n = 0
    for name, d in manifest["modeldb"].items():
        m = MDB.from_dict(d)
        want = renamed["model"].get(name, name)
        have = db.model(want)
        if have is not None and MDB.same(have, m) and not [f for f in factions if f not in have.factions()]:
            continue                                               # the very same, textured for the owners
        if have is not None and not MDB.same(have, m):
            new = free_name([x.name for x in db.models], want)
            renamed["model"][name] = new
            plan.warn(None, "battle model %s exists with other content - the pack's is added as %s" % (want, new))
            want, have = new, None
        if have is None:
            have = db.add_model(m, want)
            n += 1
        added = MDB.give_owners(have, factions)
        if added:
            plan.notes.append((mod.rel(dst), "battle model %s: texture entries for %s (copied from its %s)" % (
                want, ", ".join(added), "mercenaries'" if "merc" in {r[0] for r in m.textures} else "first")))
    plan.binary(dst, db.dump().encode("latin-1"))
    plan.notes.append((mod.rel(dst), "%d battle model(s) added%s" % (
        n, "" if src == dst else " (a copy of the game's modeldb, now the mod's own)")))


def _owner_textures(lines, facs):
    """A model block's lines with a 'texture <faction>, ...' line for every faction that has none, copied from
    the mercenaries' line (else the first faction's): (lines, [factions added]). A model with no per-faction
    texture lines is left as it is (one texture for everyone)."""
    tex = [(i, l) for i, l in enumerate(lines) if strip_comment(l).split(None, 1)[:1] == ["texture"]
           and len(_values([l], "texture")[0]) > 1 and "/" not in _values([l], "texture")[0][0]]
    if not tex:
        return lines, []
    have = {_values([l], "texture")[0][0] for _, l in tex}
    src = next((l for _, l in tex if _values([l], "texture")[0][0] == "merc"), tex[0][1])
    src_f = _values([src], "texture")[0][0]
    add = [f for f in facs if f not in have]
    new = [re.sub(r"(texture\s+)%s(\s*,)" % re.escape(src_f), lambda m, f=f: m.group(1) + f + m.group(2), src,
                  count=1) for f in add]
    at = tex[-1][0] + 1
    return lines[:at] + new + lines[at:], add


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


def recruit_levels(mod):
    """[(chain, level)] of every building level in the mod, in file order: where a unit may be recruited."""
    from .editors import building_blocks, chain_tree
    if not mod.file("edb"):
        return []
    f = mod.load(mod.file("edb"))
    return [(name, lv["name"]) for name, a, b in building_blocks(f) for lv in chain_tree(f, a, b)["levels"]]


def default_recruit_map(mod, manifest):
    """{(chain, level): (chain, level) or None}: each recruit place of the pack, the same place in this mod when it
    has it, else None (to be picked)."""
    have = set(recruit_levels(mod))
    out = {}
    for r in manifest.get("recruit", []):
        key = (r["chain"], r["level"])
        out[key] = key if key in have else None
    return out


def known_conditions(mod):
    """What this mod knows of the names a requires line or a capability line may use: {'hidden_resource': set or
    None, 'resource': set or None, 'religion': set or None} (religion None = the game has no religions / beliefs at
    all; the others None = the list was not found, so not checked)."""
    from .check import hidden_resources
    from . import resources, religions
    # a list the mod does not have (no hidden_resources line, no descr_sm_resources.txt found) is unknown (None):
    # nothing is taken out or reported for it
    hidden = {h.lower() for h in hidden_resources(mod)} if mod.file("edb") else set()
    res = {r.lower() for r in resources.types(mod)}
    hidden, res = hidden or None, res or None
    rel = {r.lower() for r in religions.names(mod)}
    beliefs = _ci(mod.data, "descr_beliefs.txt")
    if beliefs:
        for l in mod.load(beliefs).texts():
            w = strip_comment(l).strip()
            if w and " " not in w and "/" not in w and w != w.upper():
                rel.add(w.lower())
    return {"hidden_resource": hidden, "resource": res, "religion": rel or None}


_COND = re.compile(r"(?<![A-Za-z0-9_])(not\s+)?(hidden_resource|resource)\s+([A-Za-z0-9_]+)")


def fit_line(text, known):
    """(text, [what was taken out]) - a building line from another mod made fit for this one: conditions naming a
    hidden resource or a resource this mod does not have are taken out of its requires part (the game stops at
    start on them: 'Hidden resource condition, unrecognised hidden resource'), and a religious_belief line for a
    religion this game does not have is dropped whole (text None). Lines with REX brackets are left as they are."""
    body = strip_comment(text)
    t = body.split()
    if t[:1] == ["religious_belief"] and len(t) > 1:
        rel = known.get("religion")
        if rel is None or t[1].lower() not in rel:
            return None, ["religious_belief %s" % t[1]]
    m = re.search(r"(?<![A-Za-z0-9_])requires(?![A-Za-z0-9_])", body)
    if not m or "(" in body[m.end():]:
        return text, []
    head, conds = text[:m.start()], body[m.end():]
    tail = text[len(body):]                     # the comment, if any
    parts = re.split(r"\s+(and|or)\s+", " " + conds.strip())
    keep, gone = [], []
    for i in range(0, len(parts), 2):
        cond = parts[i].strip()
        op = parts[i - 1] if i else None
        c = _COND.fullmatch(cond)
        have = known.get(c.group(2)) if c else None
        if c and have is not None and c.group(3).lower() not in have:
            gone.append(cond)
            continue
        keep.append((op, cond))
    if not gone:
        return text, []
    out = ""
    for op, cond in keep:
        out += (" %s " % op if out and op else (" and " if out else "")) + cond
    line = head.rstrip() + (" requires " + out if out else "")
    return line + (" " + tail.strip() if tail.strip() else ""), gone


def _recruit(plan, manifest, names, owners, recruit_map=None):
    from .editors import building_blocks, chain_tree, line_place
    f = plan.edit(plan.mod.file("edb"))
    n, missing, done, gone = 0, set(), set(), []
    known = known_conditions(plan.mod)
    for r in manifest["recruit"]:
        src = (r["chain"], r["level"])
        # a pick for this unit alone (unit, chain, level) wins over one for the place
        if recruit_map is not None and (r["unit"],) + src in recruit_map:
            dst = recruit_map[(r["unit"],) + src]
        else:
            dst = recruit_map.get(src, src) if recruit_map is not None else src
        if dst is None:
            missing.add("%s %s" % src)
            continue
        if (r["unit"], dst) in done:          # two source places sent to one level: one line is enough
            continue
        done.add((r["unit"], dst))
        blocks = {b[0]: b for b in building_blocks(f)}
        blk = blocks.get(dst[0])
        tree = chain_tree(f, blk[1], blk[2]) if blk else None
        if not tree or not any(lv["name"] == dst[1] for lv in tree["levels"]):
            missing.add("%s %s" % dst)
            continue
        r = dict(r, chain=dst[0], level=dst[1])
        line = r["line"].replace('"%s"' % r["unit"], '"%s"' % names[r["unit"]][0], 1)
        # every factions list (REX lines may carry several groups) names the pack's owners here
        line = re.sub(r"(?<![A-Za-z0-9_])factions\s*\{[^}]*\}", "factions { %s, }" % ", ".join(owners), line)
        line, out = fit_line(line, known)
        gone += [c for c in out if c not in gone]
        at, make = line_place(f, "building", blk, "capability", r["level"], line.split()[0])
        f.insert(at, make(line))
        n += 1
    if n:
        plan.note(f, "%d recruit line(s) added" % n)
    if gone:
        plan.warn(f, "taken out of the recruit lines, this mod does not have them (the game would stop at start): "
                     "%s" % ", ".join(gone))
    for m in sorted(missing):
        plan.warn(f, "not recruited at %s (not in this mod or left out): recruit the units by hand where you want "
                     "them (Building editor: Add line)" % m)


__all__ = ["recruit_levels", "default_recruit_map", "collect_buildings", "building_names", "import_buildings",
           "type_blocks", "collect", "collect_models", "export_pack", "read_pack", "plan_names", "import_pack",
           "import_models", "game_kind"]


# ---------------------------------------------------------------------------
# Buildings: a chain with its levels, texts and pictures, from one mod into another
# ---------------------------------------------------------------------------
def collect_buildings(mod, chains):
    """(manifest, files) for these building chains: each chain's block, every export_buildings.txt entry made of a
    level's name (<level>, <level>_desc, <level>_<culture>...), the level pictures
    (ui/<culture>/buildings/#<culture>_<level>[_constructed].tga) and the units its recruit lines name."""
    from .editors import building_blocks, chain_tree
    from .roster import recruit_of
    edb = mod.load(mod.file("edb"))
    blocks = {b[0]: b for b in building_blocks(edb)}
    man = {"pack": PACK_VERSION, "kind": "buildings", "game": game_kind(mod), "buildings": [], "texts": {}}
    files = {}
    table = mod.text_file("export_buildings.txt")
    keys = []
    if table:
        for s in mod.load(table).texts():
            s = s.lstrip()
            if s.startswith("{") and "}" in s:
                keys.append(s[1:s.index("}")])
    ui = os.path.join(mod.data, "ui")
    for ch in chains:
        blk = blocks.get(ch)
        if blk is None:
            raise ValueError("no building chain '%s' in %s" % (ch, mod.data))
        _, a, b = blk
        levels = [lv["name"] for lv in chain_tree(edb, a, b)["levels"]]
        lines = [edb.text(i) for i in range(a, b)]
        units = []
        for l in lines:
            r = recruit_of(l)
            if r and r[1] not in units:
                units.append(r[1])
        man["buildings"].append({"chain": ch, "levels": levels, "lines": lines, "units": units})
        for k in keys:
            low = k.lower()
            if any(low == lv.lower() or low.startswith(lv.lower() + "_") for lv in levels):
                val = _text_entry(mod, "export_buildings.txt", k)
                if val is not None:
                    man["texts"][k] = val
        if os.path.isdir(ui):
            for cult in sorted(os.listdir(ui)):
                folder = os.path.join(ui, cult, "buildings")
                if not os.path.isdir(folder):
                    continue
                for lv in levels:
                    for tail in (".tga", "_constructed.tga"):
                        p = _ci(folder, "#%s_%s%s" % (cult, lv, tail))
                        if p:
                            with open(p, "rb") as fh:
                                files[os.path.relpath(p, mod.data).replace("\\", "/")] = fh.read()
    return man, files


def building_names(mod, manifest):
    """({old chain: new chain}, {old level: new level}): the pack's names, or free ones where this mod has them."""
    from .editors import building_blocks, fields
    edb = mod.load(mod.file("edb"))
    chains, levels = set(), set()
    for name, a, b in building_blocks(edb):
        chains.add(name)
        for fd in fields(edb, a, b):
            if fd.key == "levels":
                levels.update(fd.value.split())
    cmap, lmap = {}, {}
    for bd in manifest["buildings"]:
        c = free_name(chains, bd["chain"])
        chains.add(c)
        cmap[bd["chain"]] = c
        for lv in bd["levels"]:
            n = free_name(levels, lv)
            levels.add(n)
            lmap[lv] = n
    return cmap, lmap


def import_buildings(plan, manifest, files, factions, chain_names=None, level_names=None, unit_map=None):
    """Put building chains into plan.mod: renamed (building_names by default), every level allowed to factions
    (factions or cultures of this mod), recruit lines naming unit_map's target unit (a unit this mod lacks and
    unit_map does not send anywhere: its line left out, said), texts and pictures with them."""
    import re as _re
    from .editors import building_blocks, renamed_chain_lines, fields
    from .roster import recruit_of, factions_groups, with_factions
    mod = plan.mod
    if manifest.get("game") and manifest["game"] != game_kind(mod):
        raise ValueError("these buildings are from %s, the mod is %s - buildings go between mods of one game" % (
            "Medieval II" if manifest["game"] == "medieval2" else "Rome",
            "Medieval II" if game_kind(mod) == "medieval2" else "Rome"))
    if not factions:
        raise ValueError("pick at least one faction (or culture) that may build them")
    facs = [n for n, _ in mod.factions()]
    known = set(facs) | {mod.culture(n) for n in facs if mod.culture(n)} | {"all"}
    bad = [o for o in factions if o not in known]
    if bad:
        raise ValueError("no faction or culture %s in this mod" % ", ".join(bad))
    dflt = building_names(mod, manifest)
    chain_names = chain_names or dflt[0]
    level_names = level_names or dflt[1]
    f = plan.edit(mod.file("edb"))
    blocks = building_blocks(f)
    taken_chains = {b[0].lower() for b in blocks}
    taken_levels = set()
    for name, a, b in blocks:
        for fd in fields(f, a, b):
            if fd.key == "levels":
                taken_levels.update(x.lower() for x in fd.value.split())
    for old, new in list(chain_names.items()) + list(level_names.items()):
        if not _re.match(r"^[A-Za-z0-9_]+$", new or ""):
            raise ValueError("'%s': letters, digits and _ only" % new)
    for old, new in chain_names.items():
        if new.lower() in taken_chains:
            raise ValueError("a building chain '%s' exists in this mod already" % new)
    for old, new in level_names.items():
        if new.lower() in taken_levels:
            raise ValueError("a building level '%s' exists in this mod already" % new)
    units_here = {t.lower(): t for t in type_blocks(mod.load(mod.file("edu")))}
    unit_map = dict(unit_map or {})
    dropped, gone = [], []
    conds = known_conditions(mod)
    at = blocks[-1][2] if blocks else len(f.raw)
    out = []
    for bd in manifest["buildings"]:
        lv_names = {lv: level_names.get(lv, lv) for lv in bd["levels"]}
        lines = renamed_chain_lines(bd["lines"], bd["chain"], chain_names.get(bd["chain"], bd["chain"]), lv_names)
        new_levels = set(lv_names.values())
        kept = []
        for text in lines:
            r = recruit_of(text)
            if r:
                target = unit_map.get(r[1], units_here.get(r[1].lower()))
                if not target:
                    d = "%s (%s)" % (r[1], chain_names.get(bd["chain"], bd["chain"]))
                    if d not in dropped:
                        dropped.append(d)
                    continue
                text = text.replace('"%s"' % r[1], '"%s"' % target, 1)
            head = strip_comment(text).strip().split()[:1]
            if (r or (head and head[0] in new_levels and "requires" in text)) and factions_groups(text):
                if len(factions_groups(text)) == 1:
                    text = with_factions(text, list(factions))
                else:
                    plan.warn(f, "%s: a line with several factions groups (REX) kept as it is - check it in the "
                                 "Building editor" % (head[0] if head else "?"))
            text, out_ = fit_line(text, conds)
            gone += [c for c in out_ if c not in gone]
            if text is None:
                continue
            kept.append(text)
        out += [""] + kept
        plan.note(f, "building %s added (levels %s), may be built by %s" % (
            chain_names.get(bd["chain"], bd["chain"]), ", ".join(lv_names[lv] for lv in bd["levels"]),
            ", ".join(factions)))
    f.insert(at, out)
    if gone:
        plan.warn(f, "taken out, this mod does not have them (the game would stop at start): %s" % ", ".join(gone))
    if dropped:
        plan.warn(f, "recruit line(s) left out - the unit is not in this mod: %s (bring the unit too, or add a "
                     "recruit line in the Building editor)" % ", ".join(dropped))
    # what the levels need from this mod: other chains named in their requires lines
    have_chains = {b[0] for b in blocks} | set(chain_names.values())
    for bd in manifest["buildings"]:
        for text in bd["lines"]:
            m = _re.match(r"\s*convert_to\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", strip_comment(text))
            if m and m.group(1) not in have_chains:
                plan.warn(f, "%s turns into '%s' when a city becomes a castle (or back) - this mod has no such "
                             "building; change its convert_to line in the Building editor" % (
                                 chain_names.get(bd["chain"], bd["chain"]), m.group(1)))
            for m in _re.finditer(r"building_present(?:_min_level)?\s+([A-Za-z0-9_]+)", strip_comment(text)):
                if m.group(1) not in have_chains and m.group(1) not in chain_names:
                    plan.warn(f, "%s needs the building '%s', which this mod has not - the game may refuse it; "
                                 "change that requires line in the Building editor" % (
                                     chain_names.get(bd["chain"], bd["chain"]), m.group(1)))
    # texts
    table = mod.text_file("export_buildings.txt")
    if table and manifest.get("texts"):
        tf = plan.edit(table)
        while tf.raw and not tf.text(len(tf.raw) - 1).strip():
            del tf.raw[-1]
        n = 0
        for key, value in manifest["texts"].items():
            new = key
            for old, nl in sorted(level_names.items(), key=lambda kv: -len(kv[0])):
                if key.lower() == old.lower() or key.lower().startswith(old.lower() + "_"):
                    new = nl + key[len(old):]
                    break
            tf.raw.extend(tf.make(x) for x in ["{%s}%s" % (new, value[0])] + value[1:])
            n += 1
        tf.raw.append(tf.make(""))
        plan.note(tf, "%d building name(s) and description(s) added" % n)
    # pictures: under each culture they came from; the cultures of the new owners get one too
    ui = os.path.join(mod.data, "ui")
    cults_here = {c.lower(): c for c in os.listdir(ui)} if os.path.isdir(ui) else {}
    owners_cults = set()
    for o in factions:
        owners_cults.add(o if o in cults_here.values() else mod.culture(o) or "")
    owners_cults.discard("")
    put = set()
    by_level = {}
    for rel, data in files.items():
        parts = rel.split("/")
        if len(parts) != 4 or parts[0].lower() != "ui" or parts[2].lower() != "buildings":
            continue
        cult, name = parts[1], parts[3]
        for old, new in level_names.items():
            for tail in (".tga", "_constructed.tga"):
                if name.lower() == ("#%s_%s%s" % (cult, old, tail)).lower():
                    by_level.setdefault((new, tail), {})[cult] = data
    for (new, tail), per in by_level.items():
        for cult in set(per) | owners_cults:
            if cult.lower() not in cults_here and cult not in per:
                continue
            data = per.get(cult) or next(iter(per.values()))
            rel = "ui/%s/buildings/#%s_%s%s" % (cults_here.get(cult.lower(), cult), cult, new, tail)
            if rel.lower() not in put:
                put.add(rel.lower())
                _put(plan, rel, data)
    return plan

