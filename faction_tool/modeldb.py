"""Medieval II battle models: data/unit_models/battle_models.modeldb.

A Boost text archive on one line: every string is written as its length, a space and its characters (so a path
may hold spaces: "60 unit_models/AttachmentSets/Final Heater_england_diff.texture"), numbers as text. A class's
first appearance in the file carries two more numbers (tracking, version); later ones do not. The layout, checked
by reading the vanilla file back byte for byte:

    header: "22 serialization::archive" <archive version> <2 x class info> <model count> <model class info>
    model:  name, scale,
            lods      [class info] count [class info] (mesh, distance)...
            textures  [class info] count [class info] (faction, texture, normal, sprite)...   per faction
            attach    count (faction, texture, normal, sprite)...        the textures' class: never a class info
            mounts    [class info] count [class info] (mount type, primary skeleton, secondary skeleton,
                      primary weapons [class info] count (string)..., secondary weapons count (string)...)...
            torch     bone index [class info] 6 numbers (position and direction)

Vanilla Medieval II reads this file (M2EX too unless `model_battle_source text`, which reads
descr_model_battle.txt). A faction with no texture entry in a model shows its units without their texture, so a
new faction gets copies of its template's entries. Numbers are kept as the file writes them."""

import copy
import os

from .moddata import _ci

REL = os.path.join("unit_models", "battle_models.modeldb")


class ModelDBError(ValueError):
    pass


class _Reader:
    def __init__(self, text):
        self.t, self.p = text, 0

    WS = " \t\r\n"

    def tok(self):
        """The next number (or word): any run of spaces, tabs or line breaks parts them - a modeldb edited by hand
        (a modder's line breaks, two spaces) reads as the game reads it."""
        t, p, n = self.t, self.p, len(self.t)
        while p < n and t[p] in self.WS:
            p += 1
        e = p
        while e < n and t[e] not in self.WS:
            e += 1
        if e == p:
            raise ModelDBError("modeldb: a number expected at %d, the file ends there" % p)
        self.p = e
        return t[p:e]

    def int(self):
        v = self.tok()
        try:
            return int(v)
        except ValueError:
            raise ModelDBError("modeldb: '%s' is not a count (at %d) - the file is not in the form the game "
                               "writes it" % (v, self.p))

    def str(self):
        """A string: its length, ONE parting character (a line break counts as one), then exactly that many
        characters (a path may hold spaces)."""
        n = self.int()
        t, p = self.t, self.p
        if t[p:p + 2] == "\r\n":
            p += 2
        elif p < len(t) and t[p] in self.WS:
            p += 1
        s = t[p:p + n]
        if len(s) != n:
            raise ModelDBError("modeldb: a string runs past the end of the file")
        self.p = p + n
        return s


class Model:
    """One battle model. textures / attach: [[faction, texture, normal, sprite]]; lods: [[mesh, distance]];
    mounts: [{'type', 'primary', 'secondary', 'weapons': [..], 'weapons2': [..]}]; torch: [bone, 6 numbers]."""

    def __init__(self):
        self.name, self.scale = "", "1"
        self.lods, self.textures, self.attach, self.mounts, self.torch = [], [], [], [], []
        self.ci = {}                         # class info met in this model (the first one of the file)

    def factions(self):
        return [t[0] for t in self.textures]


class ModelDB:
    def __init__(self, text):
        self.text = text
        r = _Reader(text)
        if r.str() != "serialization::archive":
            raise ModelDBError("not a battle_models.modeldb (no serialization::archive header)")
        head = [r.tok() for _ in range(5)]            # archive version + class info of the database
        count = r.int()
        self.head = head
        self.model_ci = [r.tok(), r.tok()]
        seen = set()
        self.models = []
        for _ in range(count):
            self.models.append(self._model(r, seen))
        if text[r.p:].strip():
            raise ModelDBError("modeldb: %d characters left after %d models" % (len(text) - r.p, count))

    @staticmethod
    def _ci(r, seen, key, m):
        if key not in seen:
            seen.add(key)
            m.ci[key] = [r.tok(), r.tok()]

    def _model(self, r, seen):
        m = Model()
        m.name, m.scale = r.str(), r.tok()
        self._ci(r, seen, "lodvec", m)
        n = r.int()
        if n:
            self._ci(r, seen, "lod", m)
        m.lods = [[r.str(), r.tok()] for _ in range(n)]
        self._ci(r, seen, "texvec", m)
        n = r.int()
        if n:
            self._ci(r, seen, "tex", m)
        m.textures = [[r.str() for _ in range(4)] for _ in range(n)]
        n = r.int()                                   # attachments: the textures' own classes
        if n:
            self._ci(r, seen, "tex", m)
        m.attach = [[r.str() for _ in range(4)] for _ in range(n)]
        self._ci(r, seen, "mountvec", m)
        n = r.int()
        if n:
            self._ci(r, seen, "mount", m)
        for _ in range(n):
            mt = {"type": r.str(), "primary": r.str(), "secondary": r.str()}
            self._ci(r, seen, "weapons", m)
            mt["weapons"] = [r.str() for _ in range(r.int())]
            mt["weapons2"] = [r.str() for _ in range(r.int())]
            m.mounts.append(mt)
        m.torch = [r.tok()]
        self._ci(r, seen, "torch", m)
        m.torch += [r.tok() for _ in range(6)]
        return m

    # ---- writing ----
    @staticmethod
    def _s(s):
        return "%d %s" % (len(s), s)

    def _write_model(self, m, out):
        s, ci = self._s, m.ci
        out += [s(m.name), m.scale]
        out += ci.get("lodvec", [])
        out.append(str(len(m.lods)))
        out += ci.get("lod", [])
        for mesh, dist in m.lods:
            out += [s(mesh), dist]
        out += ci.get("texvec", [])
        out.append(str(len(m.textures)))
        tex_ci = ci.get("tex", []) if m.textures else []
        out += tex_ci
        for e in m.textures:
            out += [s(x) for x in e]
        out.append(str(len(m.attach)))
        if m.attach and not tex_ci:
            out += ci.get("tex", [])
        for e in m.attach:
            out += [s(x) for x in e]
        out += ci.get("mountvec", [])
        out.append(str(len(m.mounts)))
        if m.mounts:
            out += ci.get("mount", [])
        for mt in m.mounts:
            out += [s(mt["type"]), s(mt["primary"]), s(mt["secondary"])]
            out += ci.get("weapons", [])
            out.append(str(len(mt["weapons"])))
            out += [s(x) for x in mt["weapons"]]
            out.append(str(len(mt["weapons2"])))
            out += [s(x) for x in mt["weapons2"]]
        out.append(m.torch[0])
        out += ci.get("torch", [])
        out += m.torch[1:]

    @classmethod
    def dump_models(cls, models):
        """The text of these models (as a file writes them after its header)."""
        out = []
        for m in models:
            cls._write_model(cls, m, out)
        return out

    def dump(self):
        out = [self._s("serialization::archive")] + self.head + [str(len(self.models))] + self.model_ci
        for m in self.models:
            self._write_model(m, out)
        return " ".join(out)

    # ---- questions and changes ----
    def model(self, name):
        low = name.lower()
        return next((m for m in self.models if m.name.lower() == low), None)

    def add_faction(self, template, new):
        """Every model with texture / attachment entries for the template gets copies for the new faction
        (none added where the new one has its own already). Returns the number of models changed."""
        n = 0
        for m in self.models:
            done = False
            for key in ("textures", "attach"):
                rows = getattr(m, key)
                have = {r[0] for r in rows}
                if new in have:
                    continue
                add = [[new] + r[1:] for r in rows if r[0] == template]
                if add:
                    rows.extend(add)
                    done = True
            n += done
        return n

    def add_model(self, m, name=None):
        """A copy of model m (from this or another file) appended under name (default its own)."""
        c = copy.deepcopy(m)
        c.ci = {}
        if name:
            c.name = name
        if self.model(c.name):
            raise ModelDBError("a model called %s is in the modeldb already" % c.name)
        self.models.append(c)
        return c

    def remove_faction(self, faction):
        n = 0
        for m in self.models:
            before = len(m.textures) + len(m.attach)
            m.textures = [r for r in m.textures if r[0] != faction]
            m.attach = [r for r in m.attach if r[0] != faction]
            n += before != len(m.textures) + len(m.attach)
        return n


def to_dict(m):
    return {"name": m.name, "scale": m.scale, "lods": m.lods, "textures": m.textures, "attach": m.attach,
            "mounts": m.mounts, "torch": m.torch}


def from_dict(d):
    m = Model()
    m.name, m.scale = d["name"], d["scale"]
    m.lods, m.textures, m.attach = [list(x) for x in d["lods"]], [list(x) for x in d["textures"]], \
        [list(x) for x in d["attach"]]
    m.mounts, m.torch = copy.deepcopy(d["mounts"]), list(d["torch"])
    return m


def same(a, b):
    """The same model but for its name (and the file's class info)."""
    da, db = to_dict(a), to_dict(b)
    da.pop("name"), db.pop("name")
    return da == db


def files_of(m):
    """The data-relative files a model names (meshes, textures, normal maps, sprites)."""
    out = [mesh for mesh, _ in m.lods] + [x for r in m.textures + m.attach for x in r[1:]]
    return [x for x in dict.fromkeys(out) if x and "/" in x]


def give_owners(m, factions):
    """Texture entries for factions the model has none for, copied from its mercenaries' (else its first) -
    a unit given to a faction with no entry shows no texture. Returns the factions added."""
    added = []
    for key in ("textures", "attach"):
        rows = getattr(m, key)
        if not rows:
            continue
        have = {r[0] for r in rows}
        src = next((r for r in rows if r[0] == "merc"), rows[0])
        for f in factions:
            if f not in have:
                rows.append([f] + src[1:])
                if f not in added:
                    added.append(f)
    return added


def find(mod):
    """(path the mod's game reads, path to write) - the mod's own data/unit_models/battle_models.modeldb, else
    the game's (a mod folder that lacks one reads the game's; the edited copy then goes into the mod)."""
    own = _ci(os.path.join(mod.data, "unit_models"), "battle_models.modeldb") if \
        os.path.isdir(os.path.join(mod.data, "unit_models")) else None
    if own:
        return own, own
    try:
        from .newmod import game_of
        game = game_of(mod.data)
    except Exception:
        game = None
    if game:
        for data in (os.path.join(game, "data"),):
            p = _ci(os.path.join(data, "unit_models"), "battle_models.modeldb") if \
                os.path.isdir(os.path.join(data, "unit_models")) else None
            if p and os.path.normcase(os.path.abspath(p)) != os.path.normcase(os.path.abspath(
                    os.path.join(mod.data, REL))):
                return p, os.path.join(mod.data, REL)
    return None, None


def load(path):
    with open(path, "rb") as fh:
        return ModelDB(fh.read().decode("latin-1"))


def text_source(mod):
    """True when the game reads descr_model_battle.txt instead (M2EX `model_battle_source text`)."""
    from .limits import ex_file
    from .textio import strip_comment, tokens
    p = ex_file(mod, "descr_caps_ex.txt")
    if p:
        with open(p, "rb") as fh:
            for line in fh.read().decode("latin-1").splitlines():
                t = tokens(strip_comment(line))
                if t[:1] == ["model_battle_source"] and len(t) > 1:
                    return t[1].lower() == "text"
    return False


def plan_add_faction(plan, template, new):
    """The clone's modeldb part: the template's texture entries copied for the new faction (Medieval II)."""
    src, dst = find(plan.mod)
    if not src:
        return
    db = _db_in_plan(plan, src, dst)
    n = db.add_faction(template, new)
    if not n:
        plan.warn(None, "battle_models.modeldb: %s has no texture entries to copy" % template)
        return
    plan.binary(dst, db.dump().encode("latin-1"))
    plan.notes.append((plan.mod.rel(dst), "%d battle model(s) get %s's textures for %s%s" % (
        n, template, new, "" if src == dst else " (a copy of the game's modeldb, now the mod's own)")))


def _db_in_plan(plan, src, dst):
    if dst in plan.binaries:
        return ModelDB(plan.binaries[dst].decode("latin-1"))
    return load(src)
