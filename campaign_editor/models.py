"""A unit's battle models: which model its soldiers and officers use, what each model of the mod is, and
replacing one with another (from this mod or from another mod of the same game).

Where the game reads battle models:
  Rome                      descr_model_battle.txt (type, skeleton, texture <faction>, model_flexi ...)
  Medieval II               data/unit_models/battle_models.modeldb (modeldb.py) - or descr_model_battle.txt when
                            M2EX's descr_caps_ex.txt says `model_battle_source text`. Vanilla ships both with the
                            same 701 models, so a change goes into both where the model is in both.
The unit names them in export_descr_unit.txt: `soldier <model>, men, extras, mass` and `officer <model>` lines
(names read without case, as the game does).

How a model sits - on foot, on a horse, camel, elephant or chariot - must match the unit's `mount` (its class in
descr_mount.txt; no mount = on foot). Medieval II's modeldb says it per model (mount types None / horse / camel /
elephant, general models carry several); the text file says it by skeleton: the main `skeleton` (MTW2_HR_* and
Rome's fs_hc_* = riders, *_Elephant_* / *elephant_rider = elephant crews, *chariot* = chariots) and
`skeleton_horse / _camel / _elephant / _chariot` lines for the other seats of a general's model. A foot model on a
horse unit (or the other way) makes the soldiers stand wrong in Rome and very likely crashes Medieval II."""

import io
import os
import re

from .textio import strip_comment

SEATS = ("none", "horse", "camel", "elephant", "chariot")
RIDERS = {"horse", "camel"}      # one rider skeleton for both: vanilla Medieval II's camel units use 'Horse' models
SEAT_WORDS = {"none": "on foot", "horse": "on a horse", "camel": "on a camel", "elephant": "on an elephant",
              "chariot": "on a chariot"}
TEXT_FILE = "descr_model_battle.txt"


class ModelInfo:
    """One battle model as the tool sees it. textures {faction: data-relative texture}; seats: the ways it can
    sit (SEATS); exact: seats read from the modeldb (else guessed from skeleton names); where: {'text', 'modeldb'}."""

    def __init__(self, name):
        self.name = name
        self.where = set()
        self.textures = {}
        self.attach = {}                # Medieval II: {faction: the weapons and shields texture}
        self.sprites = {}               # Medieval II: {faction: its far-away sprite (unit_sprites/....spr)}
        self.meshes = []
        self.skeletons = []
        self.weapons = {}               # Medieval II: {skeleton (lower): [its weapons' and shield's skeletons]}
        self.seats = set()
        self.exact = False

    @property
    def factions(self):
        return list(self.textures)

    def seat_words(self):
        w = [SEAT_WORDS[s] for s in SEATS if s in self.seats]
        return (", ".join(w[:-1]) + " or " + w[-1]) if len(w) > 1 else (w[0] if w else "not known")


def game_kind(mod):
    from .packs import game_kind as gk
    return gk(mod)


def source(mod):
    """'modeldb' when the game reads battle_models.modeldb, else 'text' (descr_model_battle.txt)."""
    from . import modeldb as MDB
    if game_kind(mod) != "medieval2":
        return "text"
    src, _ = MDB.find(mod)
    return "modeldb" if src and not MDB.text_source(mod) else "text"


def skeleton_seats(name):
    """The seats a skeleton name stands for: riders sit a horse or a camel (both games use the same rider
    skeletons for them - vanilla Medieval II's camel units ride 'Horse' models), crews an elephant, chariot skeletons a chariot, the rest stand on foot."""
    low = (name or "").lower()
    if not low:
        return set()
    if "elephant" in low:
        return {"elephant"}
    if "chariot" in low:
        return {"chariot"}
    if "camel" in low:
        return {"camel"}
    if re.search(r"(^|_)(hr|hc|cr)(_|$)", low) or "horse" in low or "cavalry" in low:
        return {"horse", "camel"}
    return {"none"}


def _text_models(mod):
    """{lower name: ModelInfo} of descr_model_battle.txt."""
    from .packs import _block_lines, _values, type_blocks
    path = mod.find(TEXT_FILE)
    out = {}
    if not path:
        return out
    f = mod.load(path)
    for name, span in type_blocks(f).items():
        lines = _block_lines(f, span)
        m = ModelInfo(name)
        m.where.add("text")
        for v in _values(lines, "texture"):
            if len(v) > 1 and "/" not in v[0]:
                m.textures.setdefault(v[0], v[1])
                if len(v) > 3 and v[3].lower().endswith(".spr"):
                    m.sprites.setdefault(v[0], v[3])
            elif v and v[0]:
                m.textures.setdefault("", v[0])                 # one texture for everyone
        for v in _values(lines, "model_sprite"):                # Rome: model_sprite <faction>, distance, file
            if len(v) > 2 and "/" not in v[0] and v[2].lower().endswith(".spr"):
                m.sprites.setdefault(v[0], v[2])
        for v in _values(lines, "texture_attachments"):         # Medieval II: weapons / shields, per faction
            if len(v) > 1 and "/" not in v[0]:
                m.attach.setdefault(v[0], v[1])
        m.meshes = [v[0] for line in lines                  # in the file's order: closest first
                    for key in ("mesh", "model_flexi", "model_flexi_m", "model_flexi_c")
                    for v in _values([line], key) if v and v[0]]
        for v in _values(lines, "skeleton"):                  # the main one (a general's: its foot seat)
            m.skeletons += [x for x in v if x]
            m.seats |= skeleton_seats(v[0])
        for i, part in enumerate(("primary", "secondary")):   # the weapons' own skeletons (their moves in the hand)
            held = [v[0] for v in _values(lines, "skeleton_attachment_" + part) if v and v[0]]
            if held and i < len(m.skeletons):
                m.weapons.setdefault(m.skeletons[i].lower(), held)
        for seat in ("horse", "camel", "elephant", "chariot"):  # a general's other seats
            if _values(lines, "skeleton_" + seat):
                m.seats.add(seat)
        out[name.lower()] = m
    return out


def _modeldb_models(mod):
    from . import modeldb as MDB
    src, _ = MDB.find(mod)
    out = {}
    if not src:
        return out
    for dm in MDB.load(src).models:
        m = ModelInfo(dm.name)
        m.where.add("modeldb")
        m.exact = True
        for r in dm.textures:
            m.textures.setdefault(r[0], r[1])
            if len(r) > 3 and str(r[3]).lower().endswith(".spr"):
                m.sprites.setdefault(r[0], r[3])
        for r in dm.attach:
            m.attach.setdefault(r[0], r[1])
        m.meshes = [mesh for mesh, _ in dm.lods]
        for mt in dm.mounts:
            t = mt["type"].lower()
            m.seats.add(t if t in SEATS else "none")
            m.skeletons += [x for x in (mt["primary"], mt["secondary"]) if x]
            for sk, held in ((mt["primary"], mt["weapons"]), (mt["secondary"], mt["weapons2"])):
                if sk and held:
                    m.weapons.setdefault(sk.lower(), [x for x in held if x])
        out[dm.name.lower()] = m
    return out


def catalogue(mod):
    """{lower name: ModelInfo} of every battle model the game reads (Medieval II: the modeldb's, merged with the
    text file's where both have it - where = both - and the modeldb's seats win, being exact)."""
    kind = source(mod)
    text = _text_models(mod)
    if game_kind(mod) != "medieval2":
        return text
    db = _modeldb_models(mod)
    read, other = (db, text) if kind == "modeldb" else (text, db)
    for key, m in read.items():
        o = other.get(key)
        if o is not None:
            m.where |= o.where
            if o.exact and not m.exact:
                m.seats, m.exact = set(o.seats), True
            for f, t in o.attach.items():            # weapons / shields textures the read file lacks
                m.attach.setdefault(f, t)
            for f, t in o.sprites.items():
                m.sprites.setdefault(f, t)
    return read


# ---------------------------------------------------------------------------
# The unit's side
# ---------------------------------------------------------------------------
def unit_lines(mod, unit, f=None):
    """The unit's block lines in export_descr_unit.txt (f: a loaded / planned file), or None."""
    from .packs import _block_lines, type_blocks
    f = f or mod.load(mod.file("edu"))
    span = type_blocks(f).get(unit)
    return _block_lines(f, span) if span else None


def unit_slots(lines):
    """[(key, index, model)]: the unit's soldier line and each officer line, with the model each names."""
    from .packs import _values
    out = []
    for key in ("soldier", "officer"):
        for i, v in enumerate(_values(lines, key)):
            if v and v[0]:
                out.append((key, i, v[0]))
    return out


def mount_classes(mod):
    """{mount type (lower): class} of descr_mount.txt."""
    from .packs import _block_lines, _values, type_blocks
    path = mod.find("descr_mount.txt")
    if not path:
        return {}
    f = mod.load(path)
    out = {}
    for name, span in type_blocks(f).items():
        c = _values(_block_lines(f, span), "class")
        out[name.lower()] = (c[0][0].lower() if c and c[0] else "")
    return out


def unit_mount(mod, lines):
    """(mount type, its battle model) of the unit's mount line (descr_mount.txt `model`), or (None, None)."""
    from .packs import _block_lines, _values, type_blocks
    mounts = _values(lines, "mount")
    if not mounts or not mounts[0] or not mounts[0][0]:
        return None, None
    kind = mounts[0][0]
    path = mod.find("descr_mount.txt")
    if not path:
        return kind, None
    f = mod.load(path)
    span = next((sp for name, sp in type_blocks(f).items() if name.lower() == kind.lower()), None)
    model = _values(_block_lines(f, span), "model") if span else None
    return kind, (model[0][0] if model and model[0] else None)


def chariot_of(mod, lines):
    """A Rome chariot or scorpion cart the unit rides (descr_mount.txt class chariot / scorpion_cart - no 'model'
    line, its own lods): {'type', 'class', 'info' (a ModelInfo of the chariot: its lod .cas files), 'horse' (the
    horse_type's model name or None), 'horses' [(x, z)], 'riders' [(x, y, z)]} or None."""
    from .packs import _block_lines, _values, type_blocks
    mounts = _values(lines, "mount")
    if not mounts or not mounts[0] or not mounts[0][0]:
        return None
    kind = mounts[0][0]
    path = mod.find("descr_mount.txt")
    if not path:
        return None
    f = mod.load(path)
    blocks = type_blocks(f)
    span = next((sp for name, sp in blocks.items() if name.lower() == kind.lower()), None)
    if not span:
        return None
    bl = _block_lines(f, span)
    cls = (_values(bl, "class") or [[""]])[0][0].lower()
    if cls not in ("chariot", "scorpion_cart"):
        return None

    def nums(v):
        out = []
        for t in " ".join(v).replace(",", " ").split():
            try:
                out.append(float(t))
            except ValueError:
                pass
        return out
    info = ModelInfo(kind)
    info.meshes = ["data/models_unit/%s" % v[0].rstrip(",") for v in _values(bl, "lod") if v and v[0]]
    horse = None
    ht = _values(bl, "horse_type")
    if ht and ht[0]:
        hspan = next((sp for name, sp in blocks.items() if name.lower() == " ".join(ht[0]).lower()), None)
        hm = _values(_block_lines(f, hspan), "model") if hspan else None
        horse = hm[0][0] if hm and hm[0] else None
    return {"type": kind, "class": cls, "info": info, "horse": horse,
            "horses": [tuple(nums(v)[:2]) for v in _values(bl, "horse_offset") if len(nums(v)) >= 2],
            "riders": [tuple(nums(v)[:3]) for v in _values(bl, "rider_offset") if len(nums(v)) >= 3]}


def rider_offset(mod, kind):
    """descr_mount.txt's rider_offset (x, up, forward) of a mount type ('heavy horse'): where its rider sits from
    its saddle bone - (0, 0, 0) when not given (the 3D view's riding animations, meshview.seat_of)."""
    from .packs import _block_lines, _values, type_blocks
    path = mod.find("descr_mount.txt")
    if not path or not kind:
        return (0.0, 0.0, 0.0)
    f = mod.load(path)
    span = next((sp for name, sp in type_blocks(f).items() if name.lower() == kind.lower()), None)
    for v in _values(_block_lines(f, span), "rider_offset") if span else ():
        try:
            got = [float(t) for t in " ".join(v).replace(",", " ").split()[:3]]
        except ValueError:
            continue
        if len(got) == 3:
            return tuple(got)
    return (0.0, 0.0, 0.0)


def engine_of(mod, lines):
    """The siege engine the unit's crew works (EDU `engine <type>`, descr_engines.txt): a ModelInfo of its 'normal'
    models (Rome's engine_model / Medieval II's engine_mesh lines, closest first; Medieval II's engine_skeleton), or
    None. Medieval II's meshes name their own texture (meshview.read: texture_ref)."""
    from .packs import _values
    eng = _values(lines, "engine")
    if not eng or not eng[0] or not eng[0][0]:
        return None
    kind = eng[0][0]
    path = mod.find("descr_engines.txt")
    if not path:
        return None
    info, cur, group = None, None, None
    for line in mod.load(path).texts():
        t = line.split(";")[0].replace(",", " ").split()
        if not t:
            continue
        if t[0] == "type":
            cur, group = (t[1] if len(t) > 1 else None), None
        elif t[0] == "engine_model_group":
            group = t[1] if len(t) > 1 else None
        elif t[0] in ("engine_model", "engine_mesh") and cur and cur.lower() == kind.lower() and \
                group in (None, "normal") and len(t) > 1:
            info = info or ModelInfo(kind)              # Rome's engine_model .cas, Medieval II's engine_mesh .mesh
            info.meshes.append(t[1])
        elif t[0] == "engine_skeleton" and cur and cur.lower() == kind.lower() and group in (None, "normal") and \
                len(t) > 1:
            info = info or ModelInfo(kind)
            info.skeletons.append(t[1])
    return info


def is_ship(lines):
    """A ship (category ship): the game fights at sea by auto-resolve - no battle model, no voice; its soldier and
    voice lines are only what the file's form asks for."""
    from .packs import _values
    cat = _values(lines, "category")
    return bool(cat and cat[0] and cat[0][0].lower() == "ship")


def unit_seat(mod, lines):
    """How the unit's men sit: its mount's class (horse / camel / elephant / chariot), else 'none'."""
    from .packs import _values
    mounts = _values(lines, "mount")
    if not mounts or not mounts[0] or not mounts[0][0]:
        return "none"
    cls = mount_classes(mod).get(mounts[0][0].lower(), "")
    return cls if cls in SEATS else "none"


def fit_problems(mod, info, seat):
    """[(serious, message)] about putting model info on a unit that sits so (SEATS)."""
    out = []
    if info is None:
        return [(True, "no such battle model in this mod")]
    if info.seats and seat not in info.seats and not (seat in RIDERS and info.seats & RIDERS):
        m2 = game_kind(mod) == "medieval2"
        out.append((m2, "the unit is %s, the model is made %s%s - %s" % (
            SEAT_WORDS.get(seat, seat), info.seat_words(), "" if info.exact else " (by its skeleton)",
            "Medieval II is likely to crash when the unit takes the field" if m2 else
            "its men will stand and move wrong in battle")))
    if game_kind(mod) == "medieval2" and source(mod) == "modeldb" and "modeldb" not in info.where:
        out.append((True, "the game reads battle_models.modeldb and this model is only in %s" % TEXT_FILE))
    return out


def texture_image(mod, rel):
    """A texture as a picture (Pillow), or None: Rome's x.tga / x.tga.dds (loose, else from data/packs/*.pak),
    Medieval II's .texture (a 48-byte header before a plain DDS)."""
    from PIL import Image
    from .meshview import on_disk
    got = on_disk(mod, rel)
    if got:
        with open(got[1], "rb") as fh:
            data = fh.read()
    else:
        from .rompak import find                    # Rome keeps many textures only in data/packs/*.pak
        data = find(mod, rel)
        if data is None:
            return None
        got = (rel, rel)
    if got[1].lower().endswith(".texture") and data[48:52] == b"DDS ":
        data = data[48:]
    try:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Replacing
# ---------------------------------------------------------------------------
def _swap_first_value(line, key, new):
    m = re.match(r"^(\s*%s\s+)([^,;]*?)(\s*(,.*|;.*)?)$" % re.escape(key), line)
    return m.group(1) + new + (m.group(3) or "") if m else line


def replace(plan, unit, key, index, model, src_mod=None):
    """The unit's soldier line (key 'soldier') or its index-th officer line names model instead. From src_mod
    (another mod folder of the same game) the model comes in with every file it names; either way every faction
    that owns the unit gets texture entries on it where it has none. Returns the model's name in this mod."""
    from .packs import _block_lines, collect_models, import_models, type_blocks
    from .units import owner_factions
    mod = plan.mod
    edu = plan.edit(mod.file("edu"))
    span = type_blocks(edu).get(unit)
    if span is None:
        raise ValueError("no unit '%s' in export_descr_unit.txt" % unit)
    lines = _block_lines(edu, span)
    slots = [s for s in unit_slots(lines) if s[0] == key]
    if index >= len(slots):
        raise ValueError("%s has no %s line %d" % (unit, key, index + 1))
    from .packs import _values
    owners = owner_factions(mod, (_values(lines, "ownership") or [[]])[0])
    seat = unit_seat(mod, lines)
    if src_mod is not None and os.path.normcase(os.path.abspath(src_mod.data)) != \
            os.path.normcase(os.path.abspath(mod.data)):
        if game_kind(src_mod) != game_kind(mod):
            raise ValueError("a model goes between mods of one game - this mod is %s, the other %s" % (
                _game_word(mod), _game_word(src_mod)))
        info = catalogue(src_mod).get(model.lower())
        if info is None:
            raise ValueError("no battle model '%s' in %s" % (model, src_mod.data))
        manifest, files = collect_models(src_mod, [info.name])
        names = import_models(plan, manifest, files, owners)
        new = names.get(info.name, info.name)
        plan.notes.append(("", "battle model %s brought from %s%s" % (
            info.name, src_mod.data, "" if new == info.name else " (as %s: the name was taken here)" % new)))
    else:
        info = catalogue(mod).get(model.lower())
        if info is None:
            raise ValueError("no battle model '%s' in this mod" % model)
        new = info.name
        _give_textures(plan, info, owners)
    for serious, msg in fit_problems(mod, info, seat):
        plan.warn(None, "%s: %s%s" % (unit, "WARNING - " if serious else "", msg))
    # the EDU line
    n = -1
    for i in range(*span):
        code = strip_comment(edu.text(i)).strip()
        if code.split(None, 1)[:1] == [key]:
            n += 1
            if n == index:
                old = code.split(None, 1)[1].split(",")[0].strip()
                edu.set(i, _swap_first_value(edu.text(i), key, new))
                plan.note(edu, "%s: %s model %s -> %s" % (
                    unit, "soldiers'" if key == "soldier" else "officer %d's" % (index + 1), old, new))
                break
    return new


def _game_word(mod):
    return "Medieval II" if game_kind(mod) == "medieval2" else "Rome"


def _give_textures(plan, info, factions):
    """Texture entries for the owning factions that have none, in every place the model is (text and modeldb)."""
    from . import modeldb as MDB
    from .packs import _block_lines, _owner_textures, type_blocks
    mod = plan.mod
    if not factions:
        return
    if "text" in info.where:
        path = mod.find(TEXT_FILE)
        f = plan.edit(path)
        blocks = type_blocks(f)
        name = next((k for k in blocks if k.lower() == info.name.lower()), None)
        if name:
            a, b = blocks[name]
            now = _block_lines(f, (a, b))
            got, added = _owner_textures(now, factions)
            if added:
                f.raw[a:a + len(now)] = [f.make(x) for x in got]
                plan.note(f, "model %s: texture lines for %s" % (name, ", ".join(added)))
    if "modeldb" in info.where:
        src, dst = MDB.find(mod)
        db = MDB._db_in_plan(plan, src, dst)
        m = db.model(info.name)
        added = MDB.give_owners(m, factions) if m else []
        if added:
            plan.binary(dst, db.dump().encode("latin-1"))
            plan.notes.append((mod.rel(dst), "battle model %s: texture entries for %s%s" % (
                m.name, ", ".join(added), "" if src == dst else " (a copy of the game's modeldb, now the mod's own)")))


def own_texture_ref(ref, faction, wearers=()):
    """The name of a faction's own copy of a battle texture it shares (or that only the game's data holds): the
    word naming a wearer swapped for the faction (roman_hastati_julii -> roman_hastati_ce_test, the last such word),
    else _<faction> added before the extension; the folder stays."""
    ref = ref.replace("\\", "/")
    folder, base = ref.rsplit("/", 1) if "/" in ref else ("", ref)
    stem, dot, ext = base.partition(".")

    def word(w):
        return r"(?i)(?:^|(?<=[^a-z0-9]))%s(?=$|[^a-z0-9])" % re.escape(w)
    if re.search(word(faction), stem):
        return ref                                     # already named after it (a copy only the game's data holds)
    keys = [w for w in wearers] + [part for w in wearers for part in w.lower().split("_") if len(part) >= 4]
    for k in keys:
        hits = list(re.finditer(word(k), stem))
        if hits:
            h = hits[-1]
            stem = stem[:h.start()] + faction + stem[h.end():]
            break
    else:
        stem = "%s_%s" % (stem, faction)
    return (folder + "/" if folder else "") + stem + dot + ext


def _same_folder(old, ref):
    """ref's file name in old's folder, written as old writes it (data/... in Rome's text, none in the modeldb)."""
    old = old.replace("\\", "/")
    return (old.rsplit("/", 1)[0] + "/" if "/" in old else "") + ref.replace("\\", "/").rsplit("/", 1)[-1]


def set_faction_texture(plan, info, faction, ref, kind="texture"):
    """The faction's texture (kind 'texture') or weapons / shields texture ('attach', Medieval II's modeldb) of a
    battle model pointed at ref, in every place the model is: descr_model_battle.txt (its 'texture <faction>, ...'
    line, made from the model's other line when it has none) and the modeldb."""
    from . import modeldb as MDB
    from .packs import _block_lines, _owner_textures, _values, type_blocks
    mod = plan.mod
    key = "texture" if kind == "texture" else "texture_attachments"
    if "text" in info.where:
        path = mod.find(TEXT_FILE)
        f = plan.edit(path)
        blocks = type_blocks(f)
        name = next((k for k in blocks if k.lower() == info.name.lower()), None)
        if name:
            a, b = blocks[name]
            now = _block_lines(f, (a, b))
            got, _ = _owner_textures(now, [faction])
            out = []
            for line in got:
                v = _values([line], key)[0] if strip_comment(line).split(None, 1)[:1] == [key] else None
                if v and len(v) > 1 and v[0] == faction:
                    line = line.replace(v[1], _same_folder(v[1], ref), 1)
                out.append(line)
            f.raw[a:a + len(now)] = [f.make(x) for x in out]
            plan.note(f, "model %s: %s's %s -> %s" % (name, faction, "texture" if kind == "texture" else
                                                      "weapons texture", ref))
    if "modeldb" in info.where:
        src, dst = MDB.find(mod)
        db = MDB._db_in_plan(plan, src, dst)
        m = db.model(info.name)
        if m is not None:
            MDB.give_owners(m, [faction])
            for r in getattr(m, "textures" if kind == "texture" else "attach"):
                if r[0] == faction:
                    r[1] = _same_folder(r[1], ref)
            plan.binary(dst, db.dump().encode("latin-1"))
            plan.notes.append((mod.rel(dst), "battle model %s: %s's %s -> %s" % (
                m.name, faction, "texture" if kind == "texture" else "weapons texture", ref)))


def own_sprite_ref(ref, faction, wearers=()):
    """The faction's own copy of a far-away sprite it shares: unit_sprites/england_x_sprite.spr ->
    unit_sprites/<faction>_x_sprite.spr (the wearer's name at the front swapped; else the faction put in front).
    The game finds the pictures by the .spr's name + _000, _001... - the .spr holds no names."""
    ref = ref.replace("\\", "/")
    folder, base = ref.rsplit("/", 1) if "/" in ref else ("", ref)
    if base.lower().startswith(faction.lower() + "_"):
        return ref
    for w in sorted(wearers, key=len, reverse=True):
        if base.lower().startswith(w.lower() + "_"):
            base = base[len(w) + 1:]
            break
    return (folder + "/" if folder else "") + "%s_%s" % (faction, base)


def set_faction_sprite(plan, info, faction, ref):
    """The faction's far-away sprite of a battle model pointed at ref: Medieval II's fourth value of its
    'texture <faction>, ...' line in descr_model_battle.txt and its modeldb entry; Rome's 'model_sprite <faction>,
    distance, file' line."""
    from . import modeldb as MDB
    from .packs import _block_lines, _values, type_blocks
    mod = plan.mod
    if "text" in info.where:
        f = plan.edit(mod.find(TEXT_FILE))
        blocks = type_blocks(f)
        name = next((k for k in blocks if k.lower() == info.name.lower()), None)
        if name:
            a, b = blocks[name]
            now = _block_lines(f, (a, b))
            for i, line in enumerate(now):
                key = (strip_comment(line).split(None, 1) or [""])[0]
                v = _values([line], key)[0] if key in ("texture", "model_sprite") else None
                at = 3 if key == "texture" else 2               # Rome: model_sprite <faction>, distance, file
                if v and len(v) > at and v[0] == faction and v[at].lower().endswith(".spr") and v[at] != ref:
                    f.raw[a + i] = f.make(line.replace(v[at], ref, 1))
    if "modeldb" in info.where:
        src, dst = MDB.find(mod)
        db = MDB._db_in_plan(plan, src, dst)
        m = db.model(info.name)
        if m is not None:
            for r in m.textures:
                if r[0] == faction and len(r) > 3:
                    r[3] = ref
            plan.binary(dst, db.dump().encode("latin-1"))
    plan.notes.append((ref, "battle model %s: %s's far-away sprite -> its own" % (info.name, faction)))


__all__ = ["SEATS", "ModelInfo", "source", "catalogue", "skeleton_seats", "unit_lines", "unit_slots",
           "mount_classes", "unit_seat", "fit_problems", "texture_image", "replace"]


def model_files(mod, info):
    """[(data-relative path, file on disk)] of a battle model: its meshes (every detail level), its textures for
    every faction and its weapons textures - the mod's own, else the game's (Save its files...)."""
    from .meshview import on_disk
    refs = list(info.meshes) + list(info.textures.values()) + list(info.attach.values())
    out, seen = [], set()
    for ref in refs:
        got = on_disk(mod, ref)
        if got and got[0].lower() not in seen:
            seen.add(got[0].lower())
            out.append(got)
    return out



# ---------------------------------------------------------------------------
# The modder's own files in place of a model's (the user, 2026-10-07: 'we never draw 3D models, but replacing the
# existing ones is the whole program - take everything out and put one's own in'): textures and meshes made
# elsewhere, put where the game reads them under names of their own, the lines written, Restore takes them out.
# ---------------------------------------------------------------------------
PICTURES = (".png", ".tga", ".dds", ".texture", ".jpg", ".jpeg", ".bmp")


def mesh_kind(mod):
    """The model file this game reads: ('.cas', 'Rome .cas') or ('.mesh', 'Medieval II .mesh')."""
    return (".mesh", "Medieval II .mesh") if game_kind(mod) == "medieval2" else (".cas", "Rome .cas")


def users_of(mod, model, f=None):
    """[(unit, key, index)] of every soldier / officer line in export_descr_unit.txt naming the model."""
    from .packs import _block_lines, type_blocks
    f = f or mod.load(mod.file("edu"))
    low = model.lower()
    out = []
    for unit, span in type_blocks(f).items():
        for key, idx, m in unit_slots(_block_lines(f, span)):
            if m.lower() == low:
                out.append((unit, key, idx))
    return out


def check_mesh(mod, path):
    """The model file read as the game would (meshview: Rome .cas / Medieval II .mesh) - ValueError in plain
    words when it is not one this game takes."""
    from . import meshview as MV
    ext, word = mesh_kind(mod)
    if not path.lower().endswith(ext):
        raise ValueError("%s: this game takes a %s file for a battle model" % (os.path.basename(path), word))
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        mesh = MV.read(data) if ext == ".mesh" else MV.read_cas(data)
    except Exception as e:
        raise ValueError("%s cannot be read as a %s model (%s)" % (os.path.basename(path), word, e))
    del mesh
    return data


def _picture(path):
    """A picture file of the modder's as a Pillow image (a Medieval II .texture: the DDS after its 48 bytes)."""
    from PIL import Image
    with open(path, "rb") as fh:
        data = fh.read()
    if path.lower().endswith(".texture") and data[48:52] == b"DDS ":
        data = data[48:]
    try:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception as e:
        raise ValueError("%s cannot be read as a picture (%s)" % (os.path.basename(path), e))


def _pow2(n):
    return n > 0 and not n & (n - 1)


def texture_bytes(mod, picture, like_ref):
    """(bytes, the file's ending on disk, [notes]) for the modder's picture put in place of the texture like_ref
    names: the same kind of file as the game's (Rome .tga.dds DXT with mipmaps, Medieval II .texture with its
    48-byte head), any picture converted; a file already of that kind is taken as it is."""
    import shutil
    import tempfile
    from .meshview import on_disk
    from .recolour import picture_bytes
    notes = []
    got = on_disk(mod, like_ref)
    tmp_dir = None
    try:
        if got:
            like = got[1]
        else:                                   # Rome keeps many textures only in data/packs/*.pak
            from .rompak import find
            data = find(mod, like_ref)
            like = None
            if data is not None:
                tmp_dir = tempfile.mkdtemp(prefix="ce_like_")
                like = os.path.join(tmp_dir, "like" + (".tga.dds" if data[:4] == b"DDS " else ".tga"))
                with open(like, "wb") as fh:
                    fh.write(data)
        low_like = (like or like_ref).lower()
        ending = ".texture" if low_like.endswith(".texture") else \
            (".tga.dds" if low_like.endswith(".dds") else os.path.splitext(low_like)[1] or ".tga")
        low = picture.lower()
        same = (ending == ".texture" and low.endswith(".texture")) or \
            (ending.endswith(".dds") and low.endswith(".dds"))
        im = _picture(picture)                   # read in any case: a file the game cannot read is refused here
        if same or (ending == ".texture" and low.endswith(".dds") and like):
            with open(picture, "rb") as fh:
                data = fh.read()
            if not same:                        # a plain DDS: the .texture's 48-byte head before it
                with open(like, "rb") as fh:
                    data = fh.read(48) + data
            return data, ending, ["%s put in as it is" % os.path.basename(picture)]
        if not (_pow2(im.size[0]) and _pow2(im.size[1])):
            want = None
            if like:
                try:
                    want = _picture(like).size
                except ValueError:
                    want = None
            if not want:
                want = tuple(1 << max(0, (v - 1).bit_length()) for v in im.size)
            notes.append("%s is %d x %d - the game takes sides of 64, 128, 256, 512, 1024...: made %d x %d" % (
                os.path.basename(picture), im.size[0], im.size[1], want[0], want[1]))
            from PIL import Image
            im = im.resize(want, Image.LANCZOS)
        if like:
            data = picture_bytes(im, like)
        else:
            from .factionart import image_dds, image_tga
            data = image_dds(im) if ending.endswith(".dds") else image_tga(im)
        notes.append("%s converted to the game's %s form" % (os.path.basename(picture), ending))
        return data, ending, notes
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _ref_named(old_ref, stem, ending):
    """A reference in old_ref's folder (written as old_ref writes it) to <stem><ending> - ending '.tga.dds' is
    named '.tga' in the lines, as Rome's own lines name their .tga.dds files."""
    shown = ending[:-4] if ending == ".tga.dds" and not old_ref.lower().endswith(".dds") else ending
    folder = old_ref.replace("\\", "/").rsplit("/", 1)[0] + "/" if "/" in old_ref else ""
    return folder + stem + shown


def _disk_of(mod, ref, ending):
    """Where a new file a model line names goes in the mod (Rome's 'data/' taken off; a .tga line's .tga.dds)."""
    from .moddata import _ci
    rel = ref[5:] if ref.lower().startswith("data/") else ref
    if ending == ".tga.dds" and not rel.lower().endswith(".dds"):
        rel += ".dds"
    cur = mod.data
    parts = [x for x in rel.replace("\\", "/").split("/") if x]
    for part in parts[:-1]:                     # the folders as the disk spells them ('_Units' -> '_units')
        cur = _ci(cur, part) or os.path.join(cur, part)
    return os.path.join(cur, parts[-1])


def free_model_name(mod, want):
    """want, or want_2, _3... when a battle model of that name exists (text file or modeldb)."""
    from .packs import free_name
    return free_name(list(catalogue(mod)) + [m.name for m in _text_models(mod).values()], want)


def _point_slot(plan, unit, key, index, new):
    """The unit's soldier (or index-th officer) line in export_descr_unit.txt names model new."""
    from .packs import type_blocks
    edu = plan.edit(plan.mod.file("edu"))
    span = type_blocks(edu).get(unit)
    n = -1
    for i in range(*span):
        code = strip_comment(edu.text(i)).strip()
        if code.split(None, 1)[:1] == [key]:
            n += 1
            if n == index:
                old = code.split(None, 1)[1].split(",")[0].strip()
                if old != new:
                    edu.set(i, _swap_first_value(edu.text(i), key, new))
                    plan.note(edu, "%s: %s model %s -> %s" % (
                        unit, "soldiers'" if key == "soldier" else "officer %d's" % (index + 1), old, new))
                return


def _copy_text_block(plan, info, new, meshes, refs, owners=()):
    """descr_model_battle.txt: the model's block copied under new at the file's end; meshes [(ref, ending)]
    replace its detail levels (the first ones keep their distances, the last takes the old last's - 'max'), refs
    {(key, faction): ref} its texture / texture_attachments lines."""
    from .packs import _block_lines, _owner_textures, _set_line, _values, type_blocks
    f = plan.edit(plan.mod.find(TEXT_FILE))
    blocks = type_blocks(f)
    name = next((k for k in blocks if k.lower() == info.name.lower()), None)
    if name is None:
        return
    lines = _set_line(_block_lines(f, blocks[name]), "type", new)
    lines, _ = _owner_textures(lines, [o for o in owners if o])      # the unit's factions wear it too
    mesh_keys = ("mesh", "model_flexi", "model_flexi_m", "model_flexi_c")
    at = [i for i, l in enumerate(lines) if (strip_comment(l).split(None, 1) or [""])[0] in mesh_keys]
    if meshes and at:
        tmpl = [lines[at[i]] if i < len(meshes) - 1 and i < len(at) - 1 else lines[at[-1]]
                for i in range(len(meshes))]
        made = []
        for (ref, _), line in zip(meshes, tmpl):
            key = strip_comment(line).split(None, 1)[0]
            old = _values([line], key)[0][0]
            made.append(line.replace(old, ref, 1))
        lines = lines[:at[0]] + made + [l for i, l in enumerate(lines) if i > at[0] and i not in at]
    out = []
    for line in lines:
        key = (strip_comment(line).split(None, 1) or [""])[0]
        if key in ("texture", "texture_attachments"):
            v = _values([line], key)[0]
            fac = v[0] if len(v) > 1 and "/" not in v[0] else ""
            ref = refs.get(("texture" if key == "texture" else "attach", fac)) or \
                (refs.get(("texture" if key == "texture" else "attach", "*")) if fac or len(v) == 1 else None)
            if ref:
                line = line.replace(v[1] if fac else v[0], ref, 1)
        out.append(line)
    while f.raw and not f.text(len(f.raw) - 1).strip():
        del f.raw[-1]
    f.raw.extend(f.make(x) for x in [""] + out + [""])
    plan.note(f, "model %s added: a copy of %s%s" % (new, name, " with your model file(s)" if meshes else ""))


def _copy_db_model(plan, info, new, meshes, refs, owners=()):
    from . import modeldb as MDB
    mod = plan.mod
    src, dst = MDB.find(mod)
    if not src:
        return
    db = MDB._db_in_plan(plan, src, dst)
    m = db.model(info.name)
    if m is None:
        return
    c = db.add_model(m, new)
    MDB.give_owners(c, [o for o in owners if o])
    if meshes:
        old = c.lods
        c.lods = [[ref, (old[i] if i < len(meshes) - 1 and i < len(old) - 1 else old[-1])[1]]
                  for i, (ref, _) in enumerate(meshes)]
    for kind, rows in (("texture", c.textures), ("attach", c.attach)):
        for r in rows:
            ref = refs.get((kind, r[0])) or refs.get((kind, "*"))
            if ref:
                r[1] = ref
    plan.binary(dst, db.dump().encode("latin-1"))
    plan.notes.append((mod.rel(dst), "battle model %s added: a copy of %s%s" % (
        new, m.name, "" if src == dst else " (a copy of the game's modeldb, now the mod's own)")))


def own_files(plan, unit, key, index, textures=None, attach=None, meshes=None, name=None):
    """The modder's own files for the model of the unit's soldier line (key 'soldier') or index-th officer line:
    textures {faction or '*' (every faction wearing it): picture file}, attach (Medieval II's weapons and shields
    texture: a picture for every faction), meshes [model files, closest detail first] (Rome .cas, Medieval II
    .mesh). The unit gets a model of its own (a copy of the one it uses, under name) - other units of that model
    keep their look; a model only this unit uses is changed in place when only textures come. Every file is
    written under a name of its own beside the model's old ones (the old files stay: other models may use them).
    Returns the model's name."""
    from .packs import _block_lines, _values, type_blocks
    from .units import owner_factions
    mod = plan.mod
    textures = {k: v for k, v in (textures or {}).items() if v}
    meshes = [m for m in (meshes or []) if m]
    if not textures and not attach and not meshes:
        raise ValueError("pick a picture or a model file first")
    edu = plan.edit(mod.file("edu"))
    span = type_blocks(edu).get(unit)
    if span is None:
        raise ValueError("no unit '%s' in export_descr_unit.txt" % unit)
    lines = _block_lines(edu, span)
    slots = [s for s in unit_slots(lines) if s[0] == key]
    if index >= len(slots):
        raise ValueError("%s has no %s line %d" % (unit, key, index + 1))
    model = slots[index][2]
    info = catalogue(mod).get(model.lower())
    if info is None:
        raise ValueError("%s's model %s is not in this mod's battle models" % (unit, model))
    if attach and game_kind(mod) != "medieval2":
        raise ValueError("a weapons and shields texture of its own is Medieval II's (Rome draws them from the "
                         "model's one texture)")
    owners = owner_factions(mod, (_values(lines, "ownership") or [[]])[0])
    for fac in textures:
        if fac != "*" and fac not in info.textures and "" not in info.textures and fac not in owners:
            raise ValueError("%s wears no texture of %s" % (fac, model))
    others = [u for u in users_of(mod, model, edu) if (u[0], u[1], u[2]) != (unit, key, index)]
    copy = bool(meshes) or bool(others)
    dictionary = ((_values(lines, "dictionary") or [[""]])[0] or [""])[0] or unit.replace(" ", "_")
    new = info.name
    if copy:
        want = (name or "").strip() or (dictionary.lower() if dictionary.lower() != info.name.lower() else
                                         info.name + "_own")
        if re.search(r"[\s,;]", want):
            raise ValueError("a model's name takes letters, digits and _ only: '%s'" % want)
        new = free_model_name(mod, want)
        if game_kind(mod) == "medieval2":
            new = new.lower()                           # the games' own modeldb names are lower case
    # the files: meshes
    mesh_refs = []
    for i, path in enumerate(meshes):
        data = check_mesh(mod, path)
        ext = mesh_kind(mod)[0]
        old = info.meshes[min(i, len(info.meshes) - 1)] if info.meshes else \
            ("data/models_unit/x.cas" if ext == ".cas" else "unit_models/_Units/x.mesh")
        stem = new if len(meshes) == 1 else "%s_lod%d" % (new, i)
        ref = _ref_named(old, stem, ext)
        plan.binary(_disk_of(mod, ref, ext), data)
        plan.note(None, "%s -> %s (your model file)" % (os.path.basename(path), ref))
        mesh_refs.append((ref, ext))
    # the files: textures (and Medieval II's weapons / shields)
    refs = {}
    wearers = [f for f in info.textures if f] or [""]
    if wearers != [""]:
        wearers += [o for o in owners if o not in wearers]    # the unit's factions without a texture on it yet
    jobs = []                                   # (kind, [factions], picture, word in the file's name)
    if textures.get("*"):
        rest = [f for f in wearers if f not in textures]
        if rest:
            jobs.append(("texture", rest, textures["*"], ""))
    for fac, pic in textures.items():
        if fac != "*":
            jobs.append(("texture", [fac], pic, fac))
    if attach:
        held = [f for f in info.attach if f]
        jobs.append(("attach", (held + [o for o in owners if o not in held]) if held else [""], attach, "attach"))
    for kind, facs, pic, word in jobs:
        table = info.textures if kind == "texture" else info.attach
        old = next((table[f] for f in facs if table.get(f)), None) or table.get("merc") or table.get("") or \
            next(iter(table.values()), None)
        if not old:
            raise ValueError("%s has no %s to put a picture in place of" % (
                model, "texture" if kind == "texture" else "weapons texture"))
        data, ending, notes = texture_bytes(mod, pic, old)
        ref = _ref_named(old, "%s%s" % (new, ("_" + word) if word else ""), ending)
        plan.binary(_disk_of(mod, ref, ending), data)
        for n in notes:
            plan.note(None, n)
        plan.note(None, "%s -> %s (%s %s)" % (
            os.path.basename(pic), ref, "%s's" % facs[0] if len(facs) == 1 and facs[0] else "every faction's",
            "texture" if kind == "texture" else "weapons and shields texture"))
        for f in facs:
            refs[(kind, f)] = ref
    if copy:
        if "text" in info.where:
            _copy_text_block(plan, info, new, mesh_refs, refs, owners)
        if "modeldb" in info.where:
            _copy_db_model(plan, info, new, mesh_refs, refs, owners)
        _point_slot(plan, unit, key, index, new)
        if others:
            plan.note(None, "%s keeps the old model for %d other unit line(s) (%s)" % (
                info.name, len(others), ", ".join(sorted({u for u, _, _ in others})[:4]) +
                (" ..." if len({u for u, _, _ in others}) > 4 else "")))
        if meshes:
            plan.warn(None, "far away the game draws the old model's sprites (pictures of it) until you give the "
                            "new model sprites of its own")
    else:
        _give_textures(plan, info, [o for o in owners if o])
        for (kind, f), ref in refs.items():
            if f:
                set_faction_texture(plan, info, f, ref, kind=kind)
            else:                                    # one texture for everyone: the model's only texture line
                _set_shared_texture(plan, info, ref, kind)
    for serious, msg in fit_problems(mod, info, unit_seat(mod, lines)):
        plan.warn(None, "%s: %s%s" % (unit, "WARNING - " if serious else "", msg))
    return new


def _set_shared_texture(plan, info, ref, kind):
    """A model with one texture for everyone ('texture <file>'): that line names ref."""
    from .packs import _block_lines, _values, type_blocks
    key = "texture" if kind == "texture" else "texture_attachments"
    if "text" not in info.where:
        return
    f = plan.edit(plan.mod.find(TEXT_FILE))
    blocks = type_blocks(f)
    name = next((k for k in blocks if k.lower() == info.name.lower()), None)
    if name is None:
        return
    a, b = blocks[name]
    for i in range(a, a + len(_block_lines(f, (a, b)))):
        line = f.text(i)
        if (strip_comment(line).split(None, 1) or [""])[0] == key:
            v = _values([line], key)[0]
            if len(v) == 1:
                f.set(i, line.replace(v[0], ref, 1))
                plan.note(f, "model %s: its texture -> %s" % (name, ref))
