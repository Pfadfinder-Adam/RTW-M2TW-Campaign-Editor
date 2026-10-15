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
  descr_ship.txt          its 'ship' (a fleet's ship type); descr_mounted_engines.txt (Medieval II) its
                          'mounted_engine' (an elephant's cannon)
  descr_projectile(_new)  the projectiles its stat_pri / stat_sec (and its engine) fire, with their model files
                          (a missing one stops the game: "refers to non-existant projectile type")
  export_units.txt        {dict}, {dict}_descr, {dict}_descr_short
  ui/units, ui/unit_info  its card and info picture, per faction
  export_descr_buildings  where it is recruited (chain, level, the recruit line)

Putting a pack in (import_pack) is a Plan like every other change: Preview, a backup,
Restore. Nothing of the target mod is overwritten: a unit or dictionary name that is taken
gets a new one, a model type that exists with other content is added under a new name, a
file that exists with other bytes is kept (and said). Same game only (Rome to Rome - HLR and
REX included -, Medieval II to Medieval II)."""

import json
import os
import re
import zipfile

from .textio import strip_comment, tokens

PACK_VERSION = 1
FILE_EXT = (".cas", ".tga", ".dds", ".spr", ".mesh", ".texture", ".ms3d", ".png", ".bmp")
DEP_FILES = {"model": "descr_model_battle.txt", "mount": "descr_mount.txt",
             "engine": "descr_engines.txt", "animal": "descr_animals.txt", "projectile": "descr_projectile_new.txt",
             "ship": "descr_ship.txt", "mounted_engine": "descr_mounted_engines.txt"}
DEP_KEY = {"projectile": "projectile"}               # the word a block starts with ('type' for the rest)


def dep_file(game, kind):
    """The file a dependency kind lives in: Rome reads descr_projectile_new.txt, Medieval II descr_projectile.txt
    (units.projectile_names reads the same)."""
    if kind == "projectile" and game == "medieval2":
        return "descr_projectile.txt"
    return DEP_FILES[kind]


def _weapon_projectiles(lines):
    """The projectiles a block's stat_pri / stat_sec lines fire (their third value; 'no' = none) and an engine's
    'projectile' line names."""
    out = [v[2] for key in ("stat_pri", "stat_sec") for v in _values(lines, key)
           if len(v) > 2 and v[2] and v[2].lower() != "no"]
    return out + [v[0].split()[0] for v in _values(lines, "projectile") if v[0]]


# ---------------------------------------------------------------------------
# Blocks: 'type <name>' up to the next 'type' line
# ---------------------------------------------------------------------------
def type_blocks(f, key="type"):
    """{name: (start, end)} of a file made of 'type <name>' blocks (EDU, descr_model_battle,
    descr_mount, descr_engines, descr_animals) - or of 'projectile <name>' blocks with key='projectile'.
    Names may hold spaces (descr_mount)."""
    out, cur = {}, None
    for i in range(len(f.raw)):
        t = tokens(f.text(i))
        if t[:1] == [key] and len(t) > 1:
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


def soldiers_block(lines):
    """REX's 'soldiers ...' line followed by a { } block (HLR's units): [(i, role, name)] of its lines naming a
    battle model - role 'skeleton' (the model whose skeleton the men take), 'model' (a 'default { }' or
    'armour N { }' variant). Without such a block: []."""
    out, depth, inside = [], 0, False
    for i, line in enumerate(lines):
        code = strip_comment(line).strip()
        if not inside:
            if code.split(None, 1)[:1] == ["soldiers"]:
                inside, depth = True, 0
            continue
        if not code:
            continue
        if code.startswith("{"):
            depth += 1
            continue
        if code.startswith("}"):
            depth -= 1
            if depth <= 0:
                inside = False
            continue
        if depth == 0:                                 # a plain unit line: no block after 'soldiers'
            inside = False
            continue
        words = code.split()
        if words[0].lower() == "skeleton" and len(words) > 1:
            out.append((i, "skeleton", words[1]))
        elif words[0].lower() in ("default", "armour", "armor"):
            continue
        elif len(words) == 1:
            out.append((i, "model", words[0]))
    return out


def _rename_soldiers(lines, old, new):
    """The soldiers { } block's lines naming model old renamed to new (spacing kept)."""
    out = list(lines)
    for i, _, name in soldiers_block(lines):
        if name.lower() == old.lower():
            out[i] = re.sub(r"(?<![\w])%s(?![\w])" % re.escape(name), new, out[i], count=1)
    return out


UNIT_ORDERS = ("as in the file", "by name", "by kind", "by owner", "by cost")
CATEGORY_ORDER = ("infantry", "cavalry", "siege", "handler", "ship", "non_combatant")


def sorted_units(f, how):
    """The unit types of an EDU file in the order picked (UNIT_ORDERS): as the file has them, by name, by kind
    (infantry, cavalry, siege... then light, heavy, missile...), by owner (the first faction / culture of its
    ownership line) or by cost (the recruit price, cheapest first); each order then by name."""
    spans = type_blocks(f)
    names = list(spans)
    if how not in UNIT_ORDERS[1:]:
        return names

    def first(lines, key):
        got = _values(lines, key)
        return got[0] if got else []

    def key(n):
        lines = _block_lines(f, spans[n])
        if how == "by kind":
            cat = (first(lines, "category") or [""])[0].lower()
            rank = CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else len(CATEGORY_ORDER)
            return (rank, cat, (first(lines, "class") or [""])[0].lower(), n.lower())
        if how == "by owner":
            return ((first(lines, "ownership") or ["~"])[0].lower() or "~", n.lower())
        if how == "by cost":
            cost = first(lines, "stat_cost")
            try:
                price = int(float(cost[1]))
            except (IndexError, ValueError):
                price = 10 ** 9                            # no price read: last
            return (price, n.lower())
        return (n.lower(),)
    return sorted(names, key=key)


def unit_owners(f):
    """{unit type: [the factions / cultures of its ownership line]} of an EDU file - the Faction pick of Bring units
    (a tester, R-20261014-97E905: 'by owner still mixed - let me pick the faction')."""
    spans = type_blocks(f)
    out = {}
    for n, span in spans.items():
        got = _values(_block_lines(f, span), "ownership")
        out[n] = [x for x in (got[0] if got else []) if x]
    return out


def owner_choices(f):
    """Every faction / culture any unit of the EDU file names in its ownership, sorted."""
    return sorted({o for owners in unit_owners(f).values() for o in owners}, key=str.lower)


def _file_refs(lines):
    """Every token of the lines that names a file (by its extension)."""
    refs = []
    for l in lines:
        for part in re.split(r"[,\s]+", strip_comment(l)):
            if part.lower().endswith(FILE_EXT) and "/" in part.replace("\\", "/"):
                refs.append(part.replace("\\", "/"))
    return refs


_ROOTED = re.compile(r"^(?:[^/\s,]+/)+?data/", re.I)


def _data_rel(ref):
    """A file a line names, under data: 'data/x' -> 'x'; a path from the game's root through another data folder
    ('bi/data/x' - Barbarian Invasion's own lines, 'mods/m/data/x') -> 'x' too."""
    ref = ref.replace("\\", "/")
    if ref.lower().startswith("data/"):
        return ref[5:]
    m = _ROOTED.match(ref)
    return ref[m.end():] if m else ref


def _rebase_line(line, game):
    """A block line whose file paths go from the game's root through another data folder ('bi/data/...') written
    the way the receiving mod reads its own: 'data/...' in Rome, under data in Medieval II."""
    def fix(m):
        part = m.group(0)
        if not part.lower().endswith(FILE_EXT) or not _ROOTED.match(part.replace("\\", "/")) or \
                part.lower().startswith("data/"):
            return part
        return ("data/" if game == "rome" else "") + _data_rel(part)
    return re.sub(r"[^,\s]+", fix, line)


def _on_disk(mod, ref):
    """(data-relative path, absolute path) of a file a model line names, or None. Rome
    writes 'data/models_unit/x.tga' and keeps x.tga.dds; Medieval II 'unit_models/...'; Barbarian Invasion
    'bi/data/models_unit/...' (from the game's root)."""
    from .moddata import ci_path
    rel = _data_rel(ref)
    roots = mod.roots() if hasattr(mod, "roots") else [mod.data]       # the mod's own, then the game's under it
    for root in roots:
        for cand in (rel, rel + ".dds"):
            p = ci_path(root, cand)
            if p and os.path.isfile(p):
                return os.path.relpath(p, root).replace("\\", "/"), p
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
        game = game_kind(mod)
        self.deps = {k: (mod.load(p) if p else None) for k, p in
                     ((k, mod.find(dep_file(game, k))) for k in DEP_FILES)}
        self.dep_blocks = {k: type_blocks(f, DEP_KEY.get(k, "type")) if f else {} for k, f in self.deps.items()}
        self.manifest = {"pack": PACK_VERSION, "game": game, "units": [],
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
            man["missing"].append("%s %s" % (dep_file(man["game"], kind), name))
            return None
        lines = [_rebase_line(x, man["game"]) for x in _block_lines(self.deps[kind], span)]
        man["blocks"][kind][name] = lines
        self.add_files(lines)
        for v in _values(lines, "model"):                  # a mount's / animal's model
            if kind not in ("model", "projectile"):
                self.add_dep("model", v[0])
        if kind == "projectile":                           # its burning kind ('flaming <name>': fire arrows)
            for other, sp in self.dep_blocks[kind].items():
                if other not in man["blocks"][kind] and any(
                        v and v[0].split()[0].lower() == name.lower()
                        for v in _values(_block_lines(self.deps[kind], sp), "flaming")):
                    self.add_dep("projectile", other)
        if kind == "engine":                               # what the engine fires, the skeletons it moves by
            for p in _weapon_projectiles(lines):
                self.add_dep("projectile", p)
            for v in _values(lines, "engine_skeleton"):
                self.add_engine_skeleton(v[0])
        if kind == "mount":                                # a chariot's horses and its body's own textures
            for v in _values(lines, "horse_type"):
                self.add_dep("mount", v[0])
            self.add_skins(lines)
        return in_db or name

    def add_engine_skeleton(self, name):
        """An engine's skeleton (descr_engine_skeleton.txt: plain text, its animations loose .cas / .evt files under
        data/animations/engine) with every file it names: manifest['engine_skeletons'] {name: lines}."""
        if not hasattr(self, "_eng_skel"):
            p = self.mod.find("descr_engine_skeleton.txt")
            f = self.mod.load(p) if p else None
            self._eng_skel = (f, type_blocks(f) if f else {})
        f, blocks = self._eng_skel
        real = next((k for k in blocks if k.lower() == (name or "").lower()), None)
        got = self.manifest.setdefault("engine_skeletons", {})
        if real is None or real in got:
            return
        lines = _block_lines(f, blocks[real])
        got[real] = lines
        for line in lines:
            for ref in re.findall(r"data/animations/[^\s,;]+?\.(?:cas|evt)", strip_comment(line).replace("\\", "/"),
                                  re.I):
                self.add_ref(ref)

    def add_skins(self, lines):
        """A chariot's body (descr_mount 'lod' .cas) names its texture itself ('textures\\##chariot_low_poly.tga')
        and the game takes <name>_<faction> for a faction that has one (Rome's ##chariot_low_poly_slave), else the
        plain file: every such file of the source comes along, manifest['skins'] {stem: {faction or '': rel}} -
        put as <name>_<owner> (_put_skins), never over the target's own (a tester, R-20261014-6AD7ED: brought
        Scotti chariots rode the Britons' blue stag chariot)."""
        skins = self.manifest.setdefault("skins", {})
        for v in _values(lines, "lod"):
            got = _on_disk(self.mod, "models_unit/" + v[0].replace("\\", "/"))
            if not got:
                continue
            with open(got[1], "rb") as fh:
                data = fh.read()
            folder = got[0].rsplit("/", 1)[0]
            for ref in sorted(set(re.findall(rb"textures[\\/][^\x00\\/]+?\.tga", data, re.I))):
                stem = folder + "/textures/" + ref.decode("latin-1")[9:-4]
                if stem in skins:
                    continue
                skins[stem] = {}
                head, base = stem.rsplit("/", 1)
                pat = re.compile(r"^%s(?:_([a-z0-9_]+))?\.tga(?:\.dds)?$" % re.escape(base.lower()))
                for root in (self.mod.roots() if hasattr(self.mod, "roots") else [self.mod.data]):
                    from .moddata import ci_path
                    folder_path = ci_path(root, head)
                    if not folder_path or not os.path.isdir(folder_path):
                        continue
                    for fn in sorted(os.listdir(folder_path)):
                        m = pat.match(fn.lower())
                        if m and (m.group(1) or "") not in skins[stem]:
                            rel = head + "/" + fn
                            skins[stem][m.group(1) or ""] = rel
                            self.add_ref(rel)

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
                          ("engine", "engine"), ("animal", "animal"), ("ship", "ship"),
                          ("mounted_engine", "mounted_engine")):
            for v in _values(lines, key):
                g.add_dep(kind, v[0])
        for p in _weapon_projectiles(lines):
            g.add_dep("projectile", p)
        for v in _values(lines, "armour_ug_models"):    # Medieval II: the body of each armour upgrade (a model)
            for name in v:
                g.add_dep("model", name)
        for _, role, name in soldiers_block(lines):     # REX: the models in a soldiers { } block (HLR)
            if role == "model" or any(k.lower() == name.lower() for k in g.dep_blocks["model"]):
                g.add_dep("model", name)
        if d:
            for key in (d, d + "_descr", d + "_descr_short"):
                val = _text_entry(mod, "export_units.txt", key)
                if val is not None:
                    manifest["texts"][key] = val
            for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
                for fac, _ in mod.listing("ui/" + sub):             # the mod's folders and the game's under it
                    p = mod.find("ui/%s/%s/%s" % (sub, fac, pattern % d))     # the card in either
                    if p:
                        with open(p, "rb") as fh:
                            files["ui/%s/%s/%s" % (sub, fac, os.path.basename(p))] = fh.read()
    manifest["recruit"] = _recruit_places(mod, unit_types)
    _carry_effects(g)
    _carry_skeletons(mod, manifest, files)
    _carry_voices(mod, manifest, files)
    _carry_voice_banks(mod, manifest, files)
    return g.done()


def effect_files(mod):
    """[path] of the effect texts the game reads: the files descr_effects.txt lists (the mod's, else the game's)."""
    p = mod.find("descr_effects.txt")
    out = []
    for line in (mod.load(p).texts() if p else []):
        name = strip_comment(line).strip()
        if name.lower().endswith(".txt"):
            q = mod.find(name)
            if q and q not in out:
                out.append(q)
    return out


def effect_blocks(f):
    """[(name, start, end)] of an effect text's top-level 'effect <name> { }' and 'effect_set [< lods >] <name> { }'
    blocks (an effect set may stand several times, one per detail level)."""
    out, i, n = [], 0, len(f.raw)
    while i < n:
        t = tokens(f.text(i))
        if t[:1] and t[0].lower() in ("effect", "effect_set") and len(t) > 1:
            name, depth, j, opened = t[-1], 0, i, False
            while j < n:
                code = strip_comment(f.text(j))
                depth += code.count("{") - code.count("}")
                opened = opened or "{" in code
                j += 1
                if opened and depth <= 0:
                    break
            out.append((name, i, j))
            i = j
            continue
        i += 1
    return out


def effect_index(mod):
    """{effect name lower: [(file name, [lines])]} of every effect the mod's effect texts make."""
    out = {}
    for p in effect_files(mod):
        try:
            f = mod.load(p)
        except (OSError, ValueError):
            continue
        for name, a, b in effect_blocks(f):
            out.setdefault(name.lower(), []).append((os.path.basename(p), [f.text(k) for k in range(a, b)]))
    return out


def _projectile_effects(lines):
    """The effect names a projectile block's '...effect <name>' lines name (effect, end_effect, end_man_effect...)."""
    out = []
    for line in lines:
        t = strip_comment(line).split()
        if len(t) > 1 and t[0].lower().endswith("effect"):
            out.append(t[1])
    return out


def _carry_effects(g):
    """The effects the brought projectiles show (fire trails, explosions) with the effects they are made of and every
    texture / model they name: manifest['effects'] [{'name', 'file', 'lines'}], those first that others name."""
    want = [n for lines in (g.manifest["blocks"].get("projectile") or {}).values() for n in _projectile_effects(lines)]
    if not want:
        return
    index = effect_index(g.mod)
    out, seen = [], set()

    def add(name):
        low = name.lower()
        if low in seen or low not in index:
            return
        seen.add(low)
        for fname, lines in index[low]:
            for tok in {x for line in lines[1:] for x in re.split(r"[\s,{}<>]+", strip_comment(line)) if x}:
                if tok.lower() != low and tok.lower() in index:
                    add(tok)
            g.add_files(lines)
            out.append({"name": name, "file": fname, "lines": lines})
    for name in want:
        add(name)
    if out:
        g.manifest["effects"] = out


def _put_effects(plan, manifest):
    """The brought projectiles' effects this mod lacks, appended to its effect text of the same name (else the first
    one its descr_effects.txt lists); one it has under that name is kept as it is."""
    effects = manifest.get("effects") or []
    if not effects:
        return
    mod = plan.mod
    files = effect_files(mod)
    if not files:
        plan.warn(None, "this mod lists no effect files (descr_effects.txt) - the brought projectiles' effects (%s) "
                        "are not put in" % ", ".join(sorted({e["name"] for e in effects})))
        return
    have = set(effect_index(mod))
    by_name = {os.path.basename(p).lower(): p for p in files}
    put = {}
    for e in effects:                                  # an effect set's every detail level comes under one name
        if e["name"].lower() in have:
            continue
        path = by_name.get(e["file"].lower(), files[0])
        f = plan.edit(path)
        while f.raw and not f.text(len(f.raw) - 1).strip():
            del f.raw[-1]
        f.raw.extend(f.make(x) for x in [""] + e["lines"])
        f.raw.append(f.make(""))
        put.setdefault(path, []).append(e["name"])
    for path, names in put.items():
        plan.note(plan.files[path], "the brought projectiles' effects added: %s" % ", ".join(sorted(set(names))))


SOUND_DIR = "__sounds__/"               # the units' own voice files a pack carries - put by sounds.name_call_from


def _carry_voices(mod, manifest, files):
    """Each unit's own name call (the voice file's Unit_Select blocks naming it, every class and culture / accent)
    with its sound files' bytes (from the source's packs or loose files): manifest['voices'] {unit: [{'group',
    'cls', 'sounds': [[label, file]]}]}, the bytes in files under SOUND_DIR."""
    from . import sounds as S
    try:
        path = S.voice_file(mod)
        if not path:
            return
        events = S.voice_events(mod.load(path))
        index = S.pack_index(mod)
    except (OSError, ValueError):
        return
    out, n = {}, 0
    for u in manifest["units"]:
        for ev in events:
            if ev.vocal != S.NAME_CALL or not ev.says_for(u["type"]):
                continue
            got = []
            for rel in ev.files:
                data = S.sound_bytes(mod, rel, index)
                if data is None:
                    continue
                stash = "%svoice_%d.wav" % (SOUND_DIR, n)
                n += 1
                files[stash] = data
                got.append([rel.rsplit("/", 1)[-1], stash])
            if got:
                out.setdefault(u["type"], []).append({"group": list(ev.group), "cls": ev.cls, "sounds": got})
    if out:
        manifest["voices"] = out
    # the sound texts' 'type' lines naming the unit (a culture's war cry, a chariot's wheels, an elephant's trumpet):
    # kept with the other units of each line, to find the same line in the target
    lists = {}
    try:
        texts = S.sound_texts(mod)
    except OSError:
        texts = {}
    want = {u["type"].lower(): u["type"] for u in manifest["units"]}
    for name, p in texts.items():
        try:
            f = mod.load(p)
        except (OSError, ValueError):
            continue
        for _, names in S.type_lines(f):
            low = [n.lower() for n in names]
            for t in [want[n] for n in low if n in want]:
                lists.setdefault(t, []).append({"file": name, "with": [n for n in names if n.lower() != t.lower()]})
    if lists:
        manifest["sound_lists"] = lists


class _Lines:
    def __init__(self, texts):
        self._t = texts

    def texts(self):
        return self._t


def _carry_voice_banks(mod, manifest, files):
    """The voices a brought unit's class speaks with (its voice_type: 'Light_1', 'Heavy'...) in its owners' accent /
    culture of the source: each class block of the voice file with its sound files' bytes - put where the target's
    voice file has no such class for the new owners (else the unit says nothing there): manifest['voice_banks']
    {class: {'group', 'lines', 'files': [[rel, stash]]}}."""
    from . import sounds as S
    from .units import owner_factions
    try:
        path = S.voice_file(mod)
        if not path:
            return
        f = mod.load(path)
        blocks = S.class_blocks(f)
        index = S.pack_index(mod)
    except (OSError, ValueError):
        return
    texts = f.texts()
    banks, n = {}, 0
    for u in manifest["units"]:
        cls = next((v[0].split()[0] for v in _values(u["lines"], "voice_type") if v and v[0].split()), None)
        if not cls or cls.lower() in (k.lower() for k in banks):
            continue
        owners = [x.strip() for v in _values(u["lines"], "ownership") for x in v]
        keys = [k for k, _ in S.voice_groups(mod, owner_factions(mod, owners)) if k]
        got = next((b for k in keys for b in blocks if b[1].lower() == cls.lower() and
                    k.lower() in (g.lower() for g in b[0])), None)
        got = got or next((b for b in blocks if b[1].lower() == cls.lower()), None)
        if got is None:
            continue
        lines = texts[got[2]:got[3]]
        stash = []
        for rel in S.class_files(lines):
            data = S.sound_bytes(mod, rel, index)
            if data is None:
                continue
            name = "%sbank_%d.wav" % (SOUND_DIR, n)
            n += 1
            files[name] = data
            stash.append([rel, name])
        banks[cls] = {"group": got[0], "lines": lines, "files": stash}
    if banks:
        manifest["voice_banks"] = banks


def _bank_lines(lines, names, engines):
    """A class block as it goes into the target: name calls ('unit a, b' events) kept only for the brought units
    (under their new names) and engines ('engine x') only for the brought ones - a name the target lacks is never
    written into its voice file."""
    from . import sounds as S
    out = list(lines)
    new_of = {o.lower(): n for o, (n, _) in names.items()}
    keep_eng = {e.lower() for e in engines}
    for ev in sorted(S.voice_events(_Lines(out)), key=lambda e: -e.head):
        if ev.target is None:
            continue
        if ev.target == "unit":
            kept = [new_of[x.lower()] for x in ev.names if x.lower() in new_of]
        else:
            kept = [x for x in ev.names if x.lower() in keep_eng]
        if not kept:
            del out[ev.head:ev.end + 1]
            continue
        head = out[ev.head]
        lead = re.match(r"[ \t]*\w+", head).group(0)
        out[ev.head] = lead + " " + ", ".join(kept)
    return out


def _put_voice_banks(plan, manifest, files, names, owners):
    """Each brought class the target's voice file lacks for an accent / culture of the new owners: the source's class
    block put in that group (after its last class), its sound files added where the target has none of that name;
    events.dat / .idx rebuilt. The target's own classes are never touched."""
    from . import sounds as S
    from .units import owner_factions
    banks = manifest.get("voice_banks") or {}
    path = S.voice_file(plan.mod) if banks else None
    if not path:
        return
    mod = plan.mod
    want = {}
    for u in manifest["units"]:
        cls = next((v[0].split()[0] for v in _values(u["lines"], "voice_type") if v and v[0].split()), None)
        if cls and cls in banks:
            want.setdefault(cls, set())
    keys = [k for k, _ in S.voice_groups(mod, owner_factions(mod, owners)) if k]
    engines = list((manifest["blocks"].get("engine") or {}))
    index = S.pack_index(mod)
    put, sounds = [], 0
    for cls in list(want):
        if not banks[cls]["files"]:                    # the source's sound files were not readable: lines naming
            del want[cls]                              # sounds the mod has not would only be noise in its log
    for cls in want:
        for key in keys:
            f = plan.edit(path)
            blocks = S.class_blocks(f)
            mine = [b for b in blocks if key.lower() in (g.lower() for g in b[0])]
            if not mine or any(b[1].lower() == cls.lower() for b in mine):
                continue                               # a group the file lacks, or the class is there already
            at = max(b[3] for b in mine)
            f.insert(at, _bank_lines(banks[cls]["lines"], names, engines))
            put.append("%s (%s)" % (cls, key))
    if not put:
        return
    for cls in {p.split(" ")[0] for p in put}:
        for rel, stash in banks[cls]["files"]:
            if stash not in files or S.find(mod, rel, index):
                continue
            _put(plan, rel[5:] if rel.lower().startswith("data/") else rel, files[stash])
            index[rel.lower()] = None
            sounds += 1
    plan.note(None, "voices the brought units speak with, which this mod lacked for their new owners: %s - "
                    "%d sound file(s) with them" % (", ".join(put), sounds))
    S.rebuild_events(plan)


def _put_sound_lists(plan, manifest, names):
    """Each brought unit added to the target's sound text 'type' line that shares the most units with the line that
    named it in the source (the same war cry, the same wheels); events.dat / .idx rebuilt."""
    from . import sounds as S
    lists = manifest.get("sound_lists") or {}
    if not lists:
        return
    texts = S.sound_texts(plan.mod)
    n = 0
    for old, entries in lists.items():
        new = names.get(old, (old,))[0]
        for e in entries:
            p = texts.get(e["file"])
            if not p:
                continue
            f = plan.edit(p)
            others = {x.lower() for x in e["with"]}
            best = max(S.type_lines(f), key=lambda t: len(others & {x.lower() for x in t[1]}), default=None)
            if best is None or not others & {x.lower() for x in best[1]} or new.lower() in (x.lower() for x in best[1]):
                continue
            line = f.text(best[0])
            code, sep, comment = line.partition(";")
            f.set(best[0], code.rstrip() + ", " + new + ((" " + sep + comment) if sep else ""))
            n += 1
    if n:
        plan.note(None, "the brought units added to %d line(s) of the sound texts beside the units they sound with "
                        "in their own mod (war cries, wheels, animals)" % n)
        S.rebuild_events(plan)


def _say_banners(plan, manifest):
    """Medieval II: a brought unit's 'banner faction / holy <name>' this mod's banner file does not name - said (the
    banners are pictures of a mod's own; the unit then flies none of that kind)."""
    mod = plan.mod
    path = mod.find("descr_banners_new.xml") or mod.find("descr_banners.txt")
    if not path:
        return
    try:
        with open(path, "rb") as fh:
            text = fh.read().decode("latin-1").lower()
    except OSError:
        return
    gone = sorted({v[0].split()[-1] for u in manifest["units"] for v in _values(u["lines"], "banner")
                   if v and v[0].split() and v[0].split()[-1].lower() not in text})
    if gone:
        plan.warn(None, "banner(s) this mod's %s does not name: %s - those units fly none of that kind (add the "
                        "banner to the file, or pick one this mod has in the unit's banner line)"
                  % (os.path.basename(path), ", ".join(gone)))


def _put_voices(plan, manifest, files, names):
    """The brought units' own name calls written for their new names (sounds.name_call_from: new loose files, a
    Unit_Select block each, events.dat / .idx rebuilt) where this mod's voice file has that culture / accent and
    class; the rest said."""
    from . import sounds as S
    voices = manifest.get("voices") or {}
    if not voices or not S.voice_file(plan.mod):
        return
    left = []
    for old, entries in voices.items():
        new = names.get(old, (old,))[0]
        for e in entries:
            sounds = [(label, files[r]) for label, r in e["sounds"] if r in files]
            if not sounds:
                continue
            f = plan.edit(S.voice_file(plan.mod))
            events = S.voice_events(f)
            key = next((g for g in e["group"] if S._layout(f, events, g, e["cls"]) is not None), None)
            if key is None:
                left.append("%s (%s, %s)" % (new, ",".join(e["group"]), e["cls"]))
                continue
            S.name_call_from(plan, new, key, e["cls"], sounds,
                             prefix="%s_%s_name_%s" % (S._slug(key).title(), e["cls"], S._slug(new)))
    if left:
        plan.warn(None, "name calls not brought - this mod's voice file has no such culture / accent and class: %s"
                  % ", ".join(left[:4]) + (" ..." if len(left) > 4 else ""))


ANIM_DIR = "__animations__/"            # the skeletons and animations a pack carries (animpacks) - never put as files


def model_skeletons(blocks, modeldb=None):
    """The skeleton names the model blocks {name: lines} name (skeleton / skeleton_horse ... lines) and Medieval II's
    modeldb models {name: to_dict} (each mount entry's primary and secondary skeleton)."""
    out = []
    for m in (modeldb or {}).values():
        for mt in m.get("mounts") or []:
            out += [s for s in (mt.get("primary"), mt.get("secondary")) if s and s not in out]
    for lines in blocks.values():
        for line in lines:
            code = strip_comment(line).strip().split(None, 1)
            if len(code) == 2 and code[0].lower().startswith("skeleton") and "attachment" not in code[0].lower():
                out += [x.strip() for x in code[1].split(",") if x.strip() and x.strip() not in out]
    return out


def _carry_skeletons(mod, manifest, files):
    """The skeletons of the brought models the source has of its own (a big mod's own animations: HLR's
    fs_hc_spearman_classic...) with their animations, into the pack: manifest['animations'] {'skeletons': {name:
    file}, 'anims': {key: [[idx record (hex), file]]}}, the bytes in files under ANIM_DIR."""
    from . import animpacks
    try:
        got = animpacks.collect(mod, model_skeletons(manifest["blocks"].get("model") or {}, manifest.get("modeldb")))
    except (OSError, ValueError):
        return
    if not got["skeletons"]:
        return
    man = {"skeletons": {}, "anims": {}}
    for i, (name, rec) in enumerate(sorted(got["skeletons"].items())):
        rel = "%sskeleton_%d.rec" % (ANIM_DIR, i)
        files[rel] = rec
        man["skeletons"][name] = rel
    n = 0
    for key, items in got["anims"].items():
        man["anims"][key] = []
        for rec, body in items:
            rel = "%sanim_%d.bin" % (ANIM_DIR, n)
            n += 1
            files[rel] = body
            man["anims"][key].append([rec.hex(), rel])
    # the skeletons' own blocks of descr_skeleton.txt (what a later rebuild of the packs reads: Rome's -util:animdb,
    # Medieval II's first start without packs) - kept with them
    try:
        p = mod.find("descr_skeleton.txt")
        f = mod.load(p) if p else None
    except (OSError, ValueError):
        f = None
    if f is not None:
        blocks = type_blocks(f)
        low = {k.lower(): k for k in blocks}
        man["text"] = {name: _block_lines(f, blocks[low[name.lower()]]) for name in man["skeletons"]
                       if name.lower() in low}
    manifest["animations"] = man


def _put_skeleton_text(plan, manifest, added):
    """The blocks of descr_skeleton.txt of the skeletons put into the target's animation set (animpacks.put), where
    its descr_skeleton.txt lacks them - so a rebuild of the packs keeps the brought men moving."""
    text = (manifest.get("animations") or {}).get("text") or {}
    if not added or not text:
        return
    path = plan.mod.find("descr_skeleton.txt")
    if not path:
        return
    f = plan.edit(path)
    have = {k.lower() for k in type_blocks(f)}
    low = {k.lower(): v for k, v in text.items()}
    put = [n for n in added if n.lower() in low and n.lower() not in have]
    if not put:
        return
    while f.raw and not f.text(len(f.raw) - 1).strip():
        del f.raw[-1]
    for n in put:
        f.raw.extend(f.make(x) for x in [""] + low[n.lower()])
    f.raw.append(f.make(""))
    plan.note(f, "the brought skeletons' own lines added: %s" % ", ".join(put))


def carried_skeletons(manifest, files):
    """The pack's carried skeletons back as animpacks.merged takes them (None when it carries none)."""
    man = manifest.get("animations") or {}
    if not man.get("skeletons"):
        return None
    return {"skeletons": {n: files[r] for n, r in man["skeletons"].items() if r in files},
            "anims": {k: [(bytes.fromhex(h), files[r]) for h, r in v if r in files] for k, v in man["anims"].items()}}


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


def _rename_projectile(lines, old, new):
    """stat_pri / stat_sec lines firing old (their third value) and an engine's 'projectile old' line renamed."""
    out = []
    for l in lines:
        m = re.match(r"^(\s*stat_(?:pri|sec)\s+[^,;]*,[^,;]*,\s*)(%s)(\s*(,|;|$).*)$" % re.escape(old), l, re.I)
        out.append(m.group(1) + new + m.group(3) if m else l)
    return _rename_ref(out, "projectile", old, new)


def _rename_in_list(lines, key, old, new):
    """Every name old on 'key a, b, c' lines (a list of names) renamed to new."""
    out = []
    for l in lines:
        m = re.match(r"^(\s*%s\s+)([^;]*?)(\s*(;.*)?)$" % re.escape(key), l)
        if not m:
            out.append(l)
            continue
        parts = re.split(r"(\s*,\s*)", m.group(2))
        out.append(m.group(1) + "".join(new if p.lower() == old.lower() else p for p in parts) + m.group(3))
    return out


def _rename_ref(lines, key, old, new):
    """'key old, ...' lines naming old renamed to new (the rest of the line kept)."""
    out = []
    for l in lines:
        m = re.match(r"^(\s*%s\s+)(%s)(\s*(,|;|$).*)$" % (re.escape(key), re.escape(old)), l, re.I)
        out.append(m.group(1) + new + m.group(3) if m else l)
    return out


def _factions_here(plan):
    """[faction] of plan.mod - and the faction this same write makes (a faction brought from another mod: its
    units come in the plan that creates it)."""
    names = [n for n, _ in plan.mod.factions()]
    new = getattr(plan, "new", None)
    if isinstance(new, str) and new and new not in names and getattr(plan, "template", None) in names:
        names.append(new)
    return names


def _culture_here(plan, faction):
    try:
        return plan.mod.culture(faction)
    except Exception:
        return plan.mod.culture(plan.template) if faction == getattr(plan, "new", None) else None


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
    facs = _factions_here(plan)
    known = set(facs) | {_culture_here(plan, n) for n in facs if _culture_here(plan, n)} | {"all"}
    bad = [o for o in owners if known and o not in known]
    if bad:
        raise ValueError("no faction or culture %s in this mod" % ", ".join(bad))
    files, moved = unclash_files(mod, manifest, files)
    for old, new in moved.items():
        plan.note(None, "%s: this mod has another file of that name - the brought one goes in as %s" % (old, new))
    plan.carried_files = files
    renamed = _put_blocks(plan, manifest, owners)
    _put_effects(plan, manifest)
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
                          ("engine", "engine"), ("animal", "animal"), ("ship", "ship"),
                          ("mounted_engine", "mounted_engine")):
            for old, new in renamed[kind].items():
                lines = _rename_ref(lines, key, old, new)
                if kind == "model" and key == "soldier":
                    lines = _rename_soldiers(lines, old, new)
                    lines = _rename_in_list(lines, "armour_ug_models", old, new)
        for old, new in renamed.get("projectile", {}).items():
            lines = _rename_projectile(lines, old, new)
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
    factions = [o for o in owners if o in set(_factions_here(plan))]
    dict_of = {u["dictionary"]: names[u["type"]][1] for u in manifest["units"] if u.get("dictionary")}
    _put_files(plan, files, manifest)
    _put_skins(plan, manifest, files, owners)
    for old, new in dict_of.items():
        for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
            src = [(rel, data) for rel, data in files.items()
                   if rel.lower().startswith("ui/%s/" % sub) and rel.split("/")[-1].lower() == (pattern % old).lower()]
            if not src:
                continue
            by_fac = {rel.split("/")[2]: data for rel, data in reversed(src)}
            look = by_fac.get(_first_of(look_order(manifest), by_fac, None), src[0][1])   # the unit's own faction's
            for fac in factions or [src[0][0].split("/")[2]]:
                pick = by_fac.get(fac, look)
                _put(plan, "ui/%s/%s/%s" % (sub, fac, pattern % new), pick)
    # recruiting: the same chain and level as in the source mod, where the target has them
    if manifest.get("recruit") and mod.file("edb"):
        _recruit(plan, manifest, names, owners, recruit_map)
    _put_voice_banks(plan, manifest, files, names, owners)
    _put_voices(plan, manifest, files, names)
    _put_sound_lists(plan, manifest, names)
    _say_banners(plan, manifest)
    _say_missing(plan, manifest)
    return plan


def _target_bytes(mod, rel):
    """The bytes of data path rel as the target mod reads it (its own folder, then the game's under it), or None."""
    from .moddata import ci_path
    for root in (mod.roots() if hasattr(mod, "roots") else [mod.data]):
        p = ci_path(root, rel)
        if p and os.path.isfile(p):
            with open(p, "rb") as fh:
                return fh.read()
    return None


def _clash_name(mod, rel, taken):
    """rel with _2, _3... before its first dot of the file name: free in the mod, the game and taken."""
    head, base = rel.rsplit("/", 1) if "/" in rel else ("", rel)
    stem, dot, ext = base.partition(".")
    n = 2
    while True:
        new = "%s%s_%d%s%s" % (head + "/" if head else "", stem, n, dot, ext)
        if new.lower() not in taken and _target_bytes(mod, new) is None:
            return new
        n += 1


def unclash_files(mod, manifest, files):
    """The pack's files that the target mod (or the game under it) has at the same path with OTHER bytes get a
    path of their own (name_2.tga...), and every block / modeldb model naming them follows - so the brought unit
    wears the source mod's look, never the one already here (a tester, R-20261014-6CD955: brought chariots showed
    the Britons' chariots - 'the mod's own is kept' left the old texture under the same name), and nothing the mod
    has changes. The blocks whose lines change no longer match the mod's ones of the same name, so _put_blocks
    adds them under a free name. -> (files, {old rel: new rel}); manifest changed in place."""
    moved = {}
    taken = {r.lower() for r in files}
    skin_files = _skin_files(manifest)
    for rel in sorted(files):
        parts = rel.split("/")
        if rel.startswith((ANIM_DIR, SOUND_DIR)):
            continue                                       # carried skeletons / voices: put by animpacks / sounds
        if len(parts) == 4 and parts[0].lower() == "ui" and parts[1].lower() in ("units", "unit_info"):
            continue                                       # cards: named after the (new) dictionary anyway
        if rel in skin_files:
            continue                                       # a .cas names it: it goes in as <name>_<owner>
        have = _target_bytes(mod, rel)
        if have is not None and have != files[rel]:
            new = _clash_name(mod, rel, taken)
            taken.add(new.lower())
            moved[rel] = new
    if not moved:
        return files, moved
    files = {moved.get(r, r): d for r, d in files.items()}
    low = {}
    for old, new in moved.items():                         # a line names 'data/x.tga' for the file x.tga.dds
        low[old.lower()] = new
        if old.lower().endswith(".dds"):
            low[old[:-4].lower()] = new[:-4]

    def fix(ref):
        pre = ref[:5] if ref.lower().startswith("data/") else ""
        got = low.get(ref[len(pre):].replace("\\", "/").lower())
        return pre + got if got else ref

    def fix_line(line):
        return re.sub(r"[^,\s;]+", lambda m: fix(m.group(0)) if "/" in m.group(0) else m.group(0), line)
    for kind, blocks in manifest["blocks"].items():
        for name in list(blocks):
            blocks[name] = [fix_line(x) if ";" not in x else fix_line(x.split(";", 1)[0]) + ";" + x.split(";", 1)[1]
                            for x in blocks[name]]

    def walk(v):
        if isinstance(v, str):
            return fix(v) if "/" in v else v
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    for name in list(manifest.get("modeldb") or {}):
        manifest["modeldb"][name] = walk(manifest["modeldb"][name])
    # an engine's skeleton names its animation files, an effect its textures / models: they follow too (a tester's
    # question, 2026-10-15: a renamed animation not followed = the engine moving by the mod's own file of that name)
    for name, lines in list((manifest.get("engine_skeletons") or {}).items()):
        manifest["engine_skeletons"][name] = [fix_line(x) for x in lines]
    for e in manifest.get("effects") or []:
        e["lines"] = [fix_line(x) for x in e["lines"]]
    manifest["files"] = sorted(files)
    return files, moved


def _put_blocks(plan, manifest, owners):
    """The pack's dependency blocks (models, mounts, engines, animals) and modeldb models written into plan.mod:
    the same content is shared, another content under a taken name is added under a free one. Every faction of
    owners gets texture entries on the models. Returns {kind: {old name: new name}}."""
    mod = plan.mod
    facs = _factions_here(plan)
    renamed = {k: {} for k in DEP_FILES}
    owner_facs = [o for o in owners if o in set(facs)]
    game = game_kind(mod)
    from .animations import skeletons
    from . import animpacks
    # the source's own skeletons this mod lacks come first, into this mod's animation set (the user, 2026-10-14:
    # 'what the target lacks must come along'); what is still missing then takes the nearest one
    added = animpacks.put(plan, carried_skeletons(manifest, plan.carried_files)) if getattr(
        plan, "carried_files", None) is not None else []
    _put_skeleton_text(plan, manifest, added)
    known = set(skeletons(mod)) | animpacks.skeleton_names(mod) | {a.lower() for a in added}
    swapped, left = {}, set()
    eng_skel = _engine_skeleton_names(plan, manifest)
    for kind in ("model", "mount", "projectile", "engine", "animal", "ship", "mounted_engine"):   # projectiles first
        want = manifest["blocks"].get(kind) or {}
        if not want:
            continue
        path = mod.find(dep_file(game, kind))
        if not path:
            raise ValueError("%s is missing in this mod" % dep_file(game, kind))
        f = plan.edit(path)
        key = DEP_KEY.get(kind, "type")
        have = type_blocks(f, key)
        for name, lines in want.items():
            if kind == "model" and known:
                lines, got, unfit = _fit_skeletons(lines, known)
                swapped.update(got)
                left.update(unfit)
            if kind == "mount" or kind == "animal":
                for old, new in renamed["model"].items():
                    lines = _rename_ref(lines, "model", old, new)
            if kind == "engine":
                for old, new in renamed["projectile"].items():
                    lines = _rename_projectile(lines, old, new)
                for old, new in eng_skel.items():
                    lines = _rename_ref(lines, "engine_skeleton", old, new)
            same_name = next((k for k in have if k.lower() == name.lower()), None)
            if same_name is not None:
                if [strip_comment(x).split() for x in _block_lines(f, have[same_name])] == \
                        [strip_comment(x).split() for x in lines]:
                    if kind == "model":                        # the very same: shared, textured for the owners
                        a, b = have[same_name]
                        got, added = _owner_textures(_block_lines(f, (a, b)), owner_facs, look_order(manifest))
                        if added:
                            f.raw[a:a + len(_block_lines(f, (a, b)))] = [f.make(x) for x in got]
                            have = type_blocks(f, key)
                            plan.note(f, "model %s: texture lines for %s" % (same_name, ", ".join(added)))
                    continue
                new = free_name(have, name, sep=" " if kind in ("mount", "engine", "animal", "ship") else "_")
                renamed[kind][name] = new
                lines = _set_line(lines, key, new)
                plan.note(f, "%s %s exists with other lines: the pack's is added as %s" % (kind, name, new))
            if kind == "model":                                # every faction the units go to gets a texture
                lines, added = _owner_textures(lines, owner_facs, look_order(manifest))
                if added:
                    plan.note(f, "model %s: texture lines for %s" % (renamed[kind].get(name, name), ", ".join(added)))
            while f.raw and not f.text(len(f.raw) - 1).strip():
                del f.raw[-1]
            f.raw.extend(f.make(x) for x in [""] + lines + [""])
            have[renamed[kind].get(name, name)] = (0, 0)
            plan.note(f, "%s %s added" % (kind, renamed[kind].get(name, name)))
    _put_engine_skeletons(plan, manifest, eng_skel)
    if swapped:
        plan.warn(None, "%d skeleton(s) of the brought models are not in this mod (the source has its own "
                        "animations) - its nearest ones move the men instead, so they may move a little "
                        "differently: %s" % (len(swapped), ", ".join("%s -> %s" % kv for kv in sorted(swapped.items()))))
    if left:
        plan.warn(None, "skeleton(s) this mod lacks and has nothing near to: %s - the game stops on them "
                        "(\"Unable to find skeleton\"); give the model a skeleton of this mod's descr_skeleton.txt "
                        "in the Unit editor's model, or bring the source's animations" % ", ".join(sorted(left)))
    # Medieval II: the battle models in battle_models.modeldb, under the names descr_model_battle got
    if manifest.get("modeldb"):
        _modeldb(plan, manifest, renamed, owners)
    return renamed


# A model's skeleton the target lacks stops the game at once ("Unable to find skeleton ..."): a mod like HLR has
# skeletons of its own in its own animation packs. Rome's men share one bone tree, so the target's nearest skeleton
# moves the brought men (with the target's animations) - the names the big mods give their own ones, read as the
# target's kind of man.
SKELETON_WORDS = (("thp_m_spearman", "spearman"), ("phalanx_pikeman", "spearman"), ("pikeman", "spearman"),
                  ("hoplite", "spearman"), ("barbswordsman", "swordsman"), ("gladius", "swordsman"),
                  ("m_bearer", "standard_bearer"))
SKELETON_SPEEDS = ("semi_fast_", "slow_", "fast_")


def near_skeleton(name, known):
    """The skeleton of known (lower case names) nearest to name: itself, else the name without the big mods'
    marks (_classic, s1_) and with their kinds read as the game's (gladius = swordsman...), else without its speed,
    else without 'hc_', else any of the same kind (spearman, archer...). None when none is of its kind."""
    n = (name or "").lower()
    if n in known:
        return n
    s = n.replace("_classic", "").replace("fs_s1_", "fs_")
    for old, new in SKELETON_WORDS:
        s = s.replace(old, new)
    speed = next((p for p in SKELETON_SPEEDS if s.startswith("fs_" + p) or s.startswith("fs_hc_" + p)), "")
    plain = s.replace(speed, "", 1) if speed else s
    for c in (s, plain, plain.replace("fs_hc_", "fs_", 1), s.replace("fs_hc_", "fs_", 1)):
        if c in known:
            return c
    word = plain[3:] if plain.startswith("fs_") else plain
    word = word[3:] if word.startswith("hc_") else word
    same = [k for k in known if k == "fs_" + word or k.endswith("_" + word)]
    if not same:
        return None
    return min(same, key=lambda k: (speed not in k, ("hc_" in s) != ("hc_" in k), len(k), k))


def _fit_skeletons(lines, known):
    """A model block's 'skeleton' / 'skeleton_horse' ... lines with every skeleton known lacks put to its nearest
    (near_skeleton). -> (lines, [(old, new)], [names with no near one])."""
    out, swapped, left = [], [], []
    for l in lines:
        m = re.match(r"^(\s*skeleton\w*\s+)([^;\r\n]*?)(\s*(;.*)?\r?)$", l, re.I)
        if not m or "attachment" in m.group(1).lower():
            out.append(l)
            continue
        names = [x.strip() for x in m.group(2).split(",")]
        new = []
        for x in names:
            near = near_skeleton(x, known) if x else x
            if near is None:
                left.append(x)
                near = x
            elif near != x.lower():
                swapped.append((x, near))
            else:
                near = x
            new.append(near)
        out.append(m.group(1) + ", ".join(new) + m.group(3))
    return out, swapped, left


def _engine_skeleton_names(plan, manifest):
    """{brought engine skeleton: name it goes in under} for those this mod's descr_engine_skeleton.txt has with OTHER
    lines (a free name: the brought engine moves by its own, the mod's engines keep theirs)."""
    want = manifest.get("engine_skeletons") or {}
    path = plan.mod.find("descr_engine_skeleton.txt") if want else None
    if not path:
        return {}
    f = plan.mod.load(path)
    have = type_blocks(f)
    low = {k.lower(): k for k in have}
    out = {}
    for name, lines in want.items():
        real = low.get(name.lower())
        if real is None:
            continue
        if [strip_comment(x).split() for x in _block_lines(f, have[real])][1:] != \
                [strip_comment(x).split() for x in lines][1:]:
            out[name] = free_name(have, name, sep="_")
    return out


def _put_engine_skeletons(plan, manifest, renamed=None):
    """The brought engines' skeletons this mod's descr_engine_skeleton.txt lacks, appended (their animation files
    come with the pack's files); one it has with other lines under the name _engine_skeleton_names gave it."""
    renamed = renamed or {}
    want = manifest.get("engine_skeletons") or {}
    if not want:
        return
    path = plan.mod.find("descr_engine_skeleton.txt")
    if not path:
        plan.warn(None, "no descr_engine_skeleton.txt in this mod - the brought engines' skeletons (%s) were not "
                        "written" % ", ".join(sorted(want)))
        return
    f = plan.edit(path)
    have = {k.lower() for k in type_blocks(f)}
    new = []
    for n, lines in want.items():
        if n in renamed:
            lines = _set_line(lines, "type", renamed[n])
            n = renamed[n]
            plan.note(f, "engine skeleton %s exists here with other lines: the brought one is added as %s" % (
                [k for k, v in renamed.items() if v == n][0], n))
        if n.lower() not in have:
            new.append((n, lines))
    if not new:
        return
    while f.raw and not f.text(len(f.raw) - 1).strip():
        del f.raw[-1]
    for n, lines in new:
        f.raw.extend(f.make(x) for x in [""] + lines)
    f.raw.append(f.make(""))
    plan.note(f, "engine skeleton(s) added: %s" % ", ".join(n for n, _ in new))


def _put_files(plan, files, manifest=None):
    """The pack's files at their paths (cards and info pictures are per owner - the unit import places them; a
    chariot body's textures per owner too - _put_skins)."""
    skin_files = _skin_files(manifest or {})
    for rel, data in sorted(files.items()):
        parts = rel.split("/")
        if len(parts) == 4 and parts[0].lower() == "ui" and parts[1].lower() in ("units", "unit_info"):
            continue
        if rel in skin_files or rel.startswith((ANIM_DIR, SOUND_DIR)):
            continue
        _put(plan, rel, data)


def _skin_files(manifest):
    return {rel for have in (manifest.get("skins") or {}).values() for rel in have.values()}


def _put_skins(plan, manifest, files, owners):
    """Every faction the units go to wears the source's chariot body (add_skins): <name>_<faction> written with
    the look faction's file of the source (look_order, else its plain one) when the target would show another
    one; the target's own <name>_<faction> is kept, its plain file never touched."""
    mod = plan.mod
    facs = _factions_here(plan)
    want = [f for f in facs if f in owners or "all" in owners or (_culture_here(plan, f) and
                                                                  _culture_here(plan, f) in owners)]
    for stem, have in sorted((manifest.get("skins") or {}).items()):
        order = look_order(manifest)                      # the owners' own, else the plain one every faction wears
        own = [f for f in order if f not in ("merc", "slave") or f == manifest.get("look")]
        src_f = _first_of(own, have, "" if "" in have else _first_of(order, have, ""))
        if src_f not in have or have[src_f] not in files:
            continue
        data = files[have[src_f]]
        ext = have[src_f][len(stem) + (len(src_f) + 1 if src_f else 0):]
        for f in want:
            own = next((b for b in (_target_bytes(mod, "%s_%s%s" % (stem, f, e)) for e in (".tga", ".tga.dds"))
                        if b is not None), None)
            if own is not None:
                if own != data:
                    plan.note(None, "%s_%s: %s's own chariot look is kept" % (stem, f, f))
                continue
            plain = next((b for b in (_target_bytes(mod, stem + e) for e in (".tga", ".tga.dds")) if b is not None),
                         None)
            if plain == data:
                continue
            _put(plan, "%s_%s%s" % (stem, f, ext), data)
            plan.note(None, "%s_%s%s: %s's chariots on this body now wear the brought look" % (stem, f, ext, f))


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
    files, _ = unclash_files(plan.mod, manifest, files)
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
    factions = [o for o in owners if o in set(_factions_here(plan))]
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
        added = MDB.give_owners(have, factions, look_order(manifest))
        if added:
            src_f = _first_of(look_order(manifest), {r[0] for r in m.textures}, None)
            plan.notes.append((mod.rel(dst), "battle model %s: texture entries for %s (copied from its %s)" % (
                want, ", ".join(added), "%s'" % src_f if src_f else "first")))
    plan.binary(dst, db.dump().encode("latin-1"))
    plan.notes.append((mod.rel(dst), "%d battle model(s) added%s" % (
        n, "" if src == dst else " (a copy of the game's modeldb, now the mod's own)")))


def look_order(manifest):
    """The factions whose look (texture, card) a brought unit copies for a new owner, best first: the modder's pick
    (manifest['look']), then the units' own factions (their ownership), the mercenaries and the rebels last - a BI
    unit owned by 'slave, saxons' took the rebels' blue (a report: its first texture line was copied)."""
    out = [manifest["look"]] if manifest.get("look") else []
    for u in manifest.get("units") or []:
        for l in u.get("lines") or []:
            if strip_comment(l).split(None, 1)[:1] == ["ownership"]:
                for f in [x.strip() for x in strip_comment(l).split(None, 1)[1].split(",") if x.strip()]:
                    if f not in ("slave", "merc") and f not in out:
                        out.append(f)
    return out + [f for f in ("merc", "slave") if f not in out]


def _first_of(order, have, default):
    """The first of order that have holds, else default."""
    return next((f for f in order or () if f in have), default)


def _owner_textures(lines, facs, order=None):
    """A model block's lines with a 'texture <faction>, ...' line for every faction that has none, copied from
    the first of order that has one (look_order), else the mercenaries' line (else the first faction's), and - Medieval II - a 'texture_attachments' line for every one
    of them that has a texture line but no such line (a faction given its texture by an older version, a hand edit
    or another tool: its men looked like bare skeletons in battle): (lines, [factions given a line]). A model with
    no per-faction texture lines is left as it is (one texture for everyone)."""
    tex = [(i, l) for i, l in enumerate(lines) if strip_comment(l).split(None, 1)[:1] == ["texture"]
           and len(_values([l], "texture")[0]) > 1 and "/" not in _values([l], "texture")[0][0]]
    if not tex:
        return lines, []
    have = {_values([l], "texture")[0][0] for _, l in tex}
    by_f = {_values([l], "texture")[0][0]: l for _, l in reversed(tex)}
    src = by_f[_first_of(order, by_f, None)] if _first_of(order, by_f, None) else \
        next((l for _, l in tex if _values([l], "texture")[0][0] == "merc"), tex[0][1])
    src_f = _values([src], "texture")[0][0]
    add = [f for f in facs if f not in have]
    new = [re.sub(r"(texture\s+)%s(\s*,)" % re.escape(src_f), lambda m, f=f: m.group(1) + f + m.group(2), src,
                  count=1) for f in add]
    at = tex[-1][0] + 1
    lines = lines[:at] + new + lines[at:]
    # Medieval II: the weapons / shields texture of the same faction too - the figure takes half its picture from
    # it (no line = men like bare skeletons in battle)
    att = [(i, l) for i, l in enumerate(lines) if strip_comment(l).split(None, 1)[:1] == ["texture_attachments"]
           and len(_values([l], "texture_attachments")[0]) > 1]
    if att:
        have_a = {_values([l], "texture_attachments")[0][0] for _, l in att}
        src_a = next((l for _, l in att if _values([l], "texture_attachments")[0][0] == src_f), att[0][1])
        f_a = _values([src_a], "texture_attachments")[0][0]
        bare = [f for f in facs if f not in have_a and (f in have or f in add)]
        more = [re.sub(r"(texture_attachments\s+)%s(\s*,)" % re.escape(f_a),
                       lambda m, f=f: m.group(1) + f + m.group(2), src_a, count=1) for f in bare]
        at = att[-1][0] + 1
        lines = lines[:at] + more + lines[at:]
        add = add + [f for f in bare if f not in add]
    return lines, add


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


def missing_chains(mod, manifest):
    """{unit: [chain]}: the building chains of the other mod that train each unit and that this mod has not at all
    (a tester: 'what if the mod we bring the unit to has no such building?')."""
    from .editors import building_blocks
    here = {b[0].lower() for b in building_blocks(mod.load(mod.file("edb")))} if mod.file("edb") else set()
    out = {}
    for r in manifest.get("recruit", []):
        if r["chain"].lower() not in here and r["chain"] not in out.setdefault(r["unit"], []):
            out[r["unit"]].append(r["chain"])
    return {u: c for u, c in out.items() if c}


def bring_with_buildings(plan, src, manifest, files, owners, names=None, recruit_map=None, chains=()):
    """import_pack, then the other mod's building chains this mod lacks (chains) come along: every level, text and
    picture (import_buildings), their recruit lines pointing at the units brought now (the others this mod has by
    name kept, the rest left out - said), built by the same owners. The brought units' places in those chains are
    not written twice: their lines come with the building."""
    names = names or plan_names(plan.mod, manifest)
    rmap = dict(recruit_map or default_recruit_map(plan.mod, manifest))
    chains = [c for c in chains]
    for r in manifest.get("recruit", []):
        if r["chain"] in chains:
            rmap[(r["unit"], r["chain"], r["level"])] = False
    import_pack(plan, manifest, files, owners, names, rmap)
    if chains:
        bman, bfiles = collect_buildings(src, chains)
        cn, ln = building_names(plan.mod, bman)
        import_buildings(plan, bman, bfiles, owners, cn, ln, {old: new for old, (new, _) in names.items()})
    return plan


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
    beliefs = mod.find("descr_beliefs.txt")
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
        if dst is False:                      # its building comes along with it (bring_with_buildings)
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
                     "them (Buildings: Add line)" % m)


__all__ = ["recruit_levels", "default_recruit_map", "missing_chains", "bring_with_buildings", "collect_buildings", "building_names", "import_buildings",
           "type_blocks", "collect", "collect_models", "export_pack", "read_pack", "plan_names", "import_pack",
           "import_models", "game_kind"]


# ---------------------------------------------------------------------------
# Buildings: a chain with its levels, texts and pictures, from one mod into another
# ---------------------------------------------------------------------------
def collect_buildings(mod, chains):
    """(manifest, files) for these building chains: each chain's block, every export_buildings.txt entry made of a
    level's name (<level>, <level>_desc, <level>_<culture>...), the level pictures
    (ui/<culture>/buildings[/construction]/#<culture>_<level>[_constructed].tga) and the units its recruit lines name."""
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
    cultures = [c for c, _ in mod.listing("ui") if mod.dirs("ui/%s/buildings" % c)]    # the mod's and the game's
    from .buildings import BuildingPictures
    names = BuildingPictures(mod).names
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
            if low == ch.lower() + "_name" or any(low == lv.lower() or low.startswith(lv.lower() + "_")
                                                  for lv in levels):
                val = _text_entry(mod, "export_buildings.txt", k)
                if val is not None:
                    man["texts"][k] = val
        for cult in cultures:
            for sub in ("", "/construction"):          # Rome / BI: the build-queue icons in buildings/construction/
                pics = {n.lower(): (n, p) for n, p in mod.listing("ui/%s/buildings%s" % (cult, sub))}
                for lv in levels:
                    for tail in (".tga", "_constructed.tga"):
                        # the level's own picture, else the one descr_ui_buildings.txt names for it (Rome's
                        # temple_of_battle_shrine -> #roman_shrine.tga) - packed under the level's own name, so the
                        # mod it goes to needs no line of its own (the game showed its generic picture without)
                        got = next((pics[k] for k in (("#%s_%s%s" % (cult, n, tail)).lower() for n in names(lv))
                                    if k in pics), None)
                        if got:
                            with open(got[1], "rb") as fh:
                                files["ui/%s/buildings%s/#%s_%s%s" % (cult, sub, cult, lv, tail)] = fh.read()
    if man["game"] == "rome":                          # its look on the battle map (town plan, battle building, items)
        from . import battlelook
        man["battle"] = battlelook.collect(mod, chains, files)
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
    # who may own each unit (export_descr_unit's ownership, units brought in the same plan too): a recruit line
    # names only those owners - a line for a unit its faction may not own is a warning of the game's on every start
    # ('unit(...) does not match up to the ownership for faction(...)': 159 of them in a test mod)
    from .units import owner_factions, read_units
    edu_path = mod.file("edu")
    edu_now = plan.files.get(edu_path) or mod.load(edu_path)     # the plan's copy when units came in with it
    owners_of = {u.type.lower(): set(owner_factions(mod, u.ownership)) | set(u.ownership) for u in read_units(edu_now)}
    units_here.update({t: u for t, u in ((u.type.lower(), u.type) for u in read_units(edu_now))})
    cult = {n: mod.culture(n) for n in facs}

    def may_own(o, unit):
        own = owners_of.get(unit.lower())
        if own is None or o == "all" or "all" in own:
            return True
        return o in own or any(c == o and n in own for n, c in cult.items())
    unit_map = dict(unit_map or {})
    dropped, gone, unowned = [], [], []
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
            who = list(factions)
            if r:
                who = [o for o in factions if may_own(o, target)]
                if not who:
                    if target not in unowned:
                        unowned.append(target)
                    continue
            if (r or (head and head[0] in new_levels and "requires" in text)) and factions_groups(text):
                if len(factions_groups(text)) == 1:
                    text = with_factions(text, who)
                else:
                    plan.warn(f, "%s: a line with several factions groups (REX) kept as it is - check it in the "
                                 "Buildings" % (head[0] if head else "?"))
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
    if unowned:
        plan.note(f, "recruit line(s) left out - %s may not own the unit (export_descr_unit.txt's ownership; give it "
                     "in Roster first): %s" % (", ".join(factions), ", ".join(unowned)))
    if dropped:
        plan.warn(f, "recruit line(s) left out - the unit is not in this mod: %s (bring the unit too, or add a "
                     "recruit line in Buildings)" % ", ".join(dropped))
    # what the levels need from this mod: other chains named in their requires lines
    have_chains = {b[0] for b in blocks} | set(chain_names.values())
    for bd in manifest["buildings"]:
        for text in bd["lines"]:
            m = _re.match(r"\s*convert_to\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", strip_comment(text))
            if m and m.group(1) not in have_chains:
                plan.warn(f, "%s turns into '%s' when a city becomes a castle (or back) - this mod has no such "
                             "building; change its convert_to line in Buildings" % (
                                 chain_names.get(bd["chain"], bd["chain"]), m.group(1)))
            for m in _re.finditer(r"building_present(?:_min_level)?\s+([A-Za-z0-9_]+)", strip_comment(text)):
                if m.group(1) not in have_chains and m.group(1) not in chain_names:
                    plan.warn(f, "%s needs the building '%s', which this mod has not - the game may refuse it; "
                                 "change that requires line in Buildings" % (
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
            chain = next((c for c in chain_names if key.lower() == c.lower() + "_name"), None)
            if chain is not None:                       # the chain's own name follows the chain's new name
                new = chain_names[chain] + "_name"
            for old, nl in sorted(level_names.items(), key=lambda kv: -len(kv[0])) if chain is None else ():
                if key.lower() == old.lower() or key.lower().startswith(old.lower() + "_"):
                    new = nl + key[len(old):]
                    break
            tf.raw.extend(tf.make(x) for x in ["{%s}%s" % (new, value[0])] + value[1:])
            n += 1
        tf.raw.append(tf.make(""))
        plan.note(tf, "%d building name(s) and description(s) added" % n)
    # pictures: under each culture they came from; the cultures of the new owners get one too
    cults_here = {c.lower(): c for c, _ in mod.listing("ui")}       # the mod's culture folders and the game's
    owners_cults = set()
    for o in factions:
        owners_cults.add(o if o in cults_here.values() else mod.culture(o) or "")
    owners_cults.discard("")
    put = set()
    by_level = {}
    for rel, data in files.items():
        parts = rel.split("/")
        if parts[0].lower() != "ui" or len(parts) < 4 or parts[2].lower() != "buildings" or \
                len(parts) not in (4, 5) or len(parts) == 5 and parts[3].lower() != "construction":
            continue
        cult, name, sub = parts[1], parts[-1], "/construction" if len(parts) == 5 else ""
        for old, new in level_names.items():
            for tail in (".tga", "_constructed.tga"):
                if name.lower() == ("#%s_%s%s" % (cult, old, tail)).lower():
                    by_level.setdefault((new, tail, sub), {})[cult] = data
    for (new, tail, sub), per in by_level.items():
        for cult in set(per) | owners_cults:
            if cult.lower() not in cults_here and cult not in per:
                continue
            data = per.get(cult) or next(iter(per.values()))
            rel = "ui/%s/buildings%s/#%s_%s%s" % (cults_here.get(cult.lower(), cult), sub, cult, new, tail)
            if rel.lower() not in put:
                put.add(rel.lower())
                _put(plan, rel, data)
    # the look on the battle map: town-plan places, battle buildings, items and their models
    if manifest.get("battle"):
        from . import battlelook
        battlelook.put(plan, manifest["battle"], chain_names, level_names)
        _put_files(plan, {r: d for r, d in files.items() if not r.lower().startswith("ui/")})
    return plan

