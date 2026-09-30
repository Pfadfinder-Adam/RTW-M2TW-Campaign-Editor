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

from .moddata import _ci, ci_path
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
        self.meshes = []
        self.skeletons = []
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
    path = _ci(mod.data, TEXT_FILE)
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
            elif v and v[0]:
                m.textures.setdefault("", v[0])                 # one texture for everyone
        m.meshes = [v[0] for line in lines                  # in the file's order: closest first
                    for key in ("mesh", "model_flexi", "model_flexi_m", "model_flexi_c")
                    for v in _values([line], key) if v and v[0]]
        for v in _values(lines, "skeleton"):                  # the main one (a general's: its foot seat)
            m.skeletons += [x for x in v if x]
            m.seats |= skeleton_seats(v[0])
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
        for r in dm.attach:
            m.attach.setdefault(r[0], r[1])
        m.meshes = [mesh for mesh, _ in dm.lods]
        for mt in dm.mounts:
            t = mt["type"].lower()
            m.seats.add(t if t in SEATS else "none")
            m.skeletons += [x for x in (mt["primary"], mt["secondary"]) if x]
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
    path = _ci(mod.data, "descr_mount.txt")
    if not path:
        return {}
    f = mod.load(path)
    out = {}
    for name, span in type_blocks(f).items():
        c = _values(_block_lines(f, span), "class")
        out[name.lower()] = (c[0][0].lower() if c and c[0] else "")
    return out


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
    """A texture as a picture (Pillow), or None: Rome's x.tga / x.tga.dds, Medieval II's .texture (a 48-byte
    header before a plain DDS)."""
    from PIL import Image
    from .meshview import on_disk
    got = on_disk(mod, rel)
    if not got:
        return None
    with open(got[1], "rb") as fh:
        data = fh.read()
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
        path = _ci(mod.data, TEXT_FILE)
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


__all__ = ["SEATS", "ModelInfo", "source", "catalogue", "skeleton_seats", "unit_lines", "unit_slots",
           "mount_classes", "unit_seat", "fit_problems", "texture_image", "replace"]
