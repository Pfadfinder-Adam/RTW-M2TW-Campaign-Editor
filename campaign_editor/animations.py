"""The games' battle animations, read from their packs (data/animations/pack.idx + pack.dat - Rome, Barbarian
Invasion, Medieval II) to pose a battle model in the 3D view and play it, and the skeletons they play on - read the
way the game reads them (the engine source: SKELETON::unpack, SKELETON_BASE::open, ANIM_DATA_PACK), so any mod's
bones are placed as in the game, whatever their number, order and names.

pack.idx: 'ANIM.PACK', a version (4 Rome / BI, 9 Medieval II) and the count at byte 16; from byte 20 one record per
animation: its record size, offset into pack.dat, size, scale (Rome keeps most twice, at 1.0 and 1.1), frames,
bones, kind, then the name ('data/animations/...cas'). An animation in pack.dat: frames, bones, kind again, then for
every frame each bone's own turn (a quaternion x y z w, from its parent), then for every frame the offsets of the
`kind` bones that carry one (x y z from the parent), the root's moves and lengths, and last a bit mask saying WHICH
bones those are (one bit a bone): the pelvis alone is Rome's usual and every bone Medieval II's, but a camel's swim,
an elephant's moves, a crossbow's string and many a mod's own animations carry some bones and not others - a bone
with no offset of its own stands where its skeleton's base pose puts it (read as 'the first `kind` bones', a mod's
men fell together: 'they look crushed'). XIDX (the Europa Barbarorum team's pack tool) reads the records the same way.

Skeletons (Skeleton): Medieval II's skeletons.dat record of each skeleton holds its bones - each one's name, parent
and base pose (its place from the parent) and the inverse of its place in the pose the meshes are made in (the
skin's bind, from the skeleton's 'default' animation). A mod living on descr_skeleton.txt alone (no set loads) has
its skeleton built from the type's first .cas file, as the game does. A Rome model's bones are its own
(meshview.read_cas).

descr_skeleton.txt names each skeleton's animations: 'type <skeleton>', then 'anim <what> <file> ...' lines."""

import os
import re
import struct

from .moddata import _ci

FPS = 20                        # frames a second the 3D view plays (the games' own rate is not written anywhere)
HEADER = b"ANIM.PACK"


class Entry:
    def __init__(self, name, scale, frames, bones, kind, offset, size):
        self.name, self.scale, self.frames, self.bones, self.kind = name, scale, frames, bones, kind
        self.offset, self.size = offset, size


class Anim:
    """One animation: frames, bones, kind; rotations(k) = each bone's own turn in frame k, offsets(k) = each bone's
    offset from its parent in frame k - None for a bone the animation carries none for (it stands at its skeleton's
    base pose); moved = the bones that carry one (the record's bit mask)."""

    def __init__(self, name, frames, bones, kind, data, version=None):
        self.name, self.frames, self.bones, self.kind, self.data = name, frames, bones, kind, data
        need = 5 + 16 * frames * bones + 12 * frames * kind
        if frames < 1 or bones < 1 or len(data) < need:
            raise ValueError("%s: not an animation the editor can read" % name)
        self.moved = moved_bones(data, frames, bones, kind, version)

    def rotations(self, k):
        k = max(0, min(self.frames - 1, k))
        return list(struct.iter_unpack("<4f", self.data[5 + 16 * k * self.bones:5 + 16 * (k + 1) * self.bones]))

    def offsets(self, k):
        k = max(0, min(self.frames - 1, k))
        at = 5 + 16 * self.frames * self.bones + 12 * k * self.kind
        out = [None] * self.bones
        for b, t in zip(self.moved, struct.iter_unpack("<3f", self.data[at:at + 12 * self.kind])):
            out[b] = t
        return out


# what stands between an animation's offsets and its bit mask, by the pack's version: Medieval II (9) keeps the
# root's moves for every frame (8 bytes) and the distances to the end (4), Rome (4) every second frame (12 + 4);
# then both the root's offsets (12 a frame) and six numbers (length in time and distance, the move, three speeds)
_BETWEEN = {9: lambda f: 24 * f + 32, 4: lambda f: 16 * (f >> 1) + 12 * f + 32}


def moved_bones(data, frames, bones, kind, version=None):
    """The bones an animation in pack.dat carries offsets for, in order: its record's last bytes, one bit a bone
    (ANIM_DATA_PACK's trans_array: 4 to 12 bytes); the first `kind` bones when no mask reads."""
    start = 5 + 16 * frames * bones + 12 * frames * max(kind, 1)
    for v in ([version] if version in _BETWEEN else []) + [v for v in _BETWEEN if v != version]:
        at = start + _BETWEEN[v](frames)
        rest = len(data) - at
        if 4 <= rest <= 12 and rest % 4 == 0:
            bits = int.from_bytes(data[at:], "little")
            got = tuple(b for b in range(bones) if bits >> b & 1)
            if len(got) == kind and bits >> bones == 0:
                return got
    return tuple(range(min(kind, bones)))


def read_index(data):
    """[Entry] of a pack.idx's bytes (ValueError when it is not one)."""
    return _read_index(data)[1]


def _read_index(data):
    """(the pack's version, [Entry]) of a pack.idx's bytes."""
    if not data.startswith(HEADER) or len(data) < 20:
        raise ValueError("not an animation pack index")
    count = struct.unpack_from("<I", data, 16)[0]
    out, p = [], 20
    for _ in range(count):
        if p + 21 > len(data):
            break
        _, off, size, scale = struct.unpack_from("<IIIf", data, p)
        frames, bones, kind = struct.unpack_from("<HHB", data, p + 16)
        end = data.find(b"\0", p + 21)
        if end < 0:
            break
        out.append(Entry(data[p + 21:end].decode("latin-1"), scale, frames, bones, kind, off, size))
        p = end + 1
    return struct.unpack_from("<I", data, 12)[0], out


def key(name):
    """An animation's name as packs and descr_skeleton meet: data/animations/x.cas, any case, either slash. A pack the
    game built while running a mod names each animation by the path it opened it at, the mod's folder in front
    (Europa Barbarorum II: 'mods/EBII/data/animations/eb_hoplite/...cas') - its descr_skeleton.txt and skeletons.dat
    say 'data/animations/...': the mod's folder is left out."""
    n = _MOD_DIR.sub("", name.strip().strip('"').replace("\\", "/").lower().lstrip("/"))
    return n if n.startswith("data/") else "data/" + n


_MOD_DIR = re.compile(r"^(?:data/)?mods/[^/]+/(?=data/)", re.I)


class Pack:
    def __init__(self, folder):
        self.folder = folder
        self.idx, self.dat = _ci(folder, "pack.idx"), _ci(folder, "pack.dat")
        self._entries, self.version = None, None

    @property
    def entries(self):
        """{key: [Entry, ...]} - the scales of one animation together, 1.0 first."""
        if self._entries is None:
            with open(self.idx, "rb") as fh:
                self.version, found = _read_index(fh.read())
            self._entries = {}
            for e in found:
                self._entries.setdefault(key(e.name), []).append(e)
            for es in self._entries.values():
                es.sort(key=lambda e: abs(e.scale - 1.0))
        return self._entries

    def anim(self, name, scale=None):
        """The animation of this name - at the scale nearest `scale` (its skeleton's: Rome keeps several), else 1.0's."""
        es = self.entries.get(key(name))
        if not es or not self.dat:
            return None
        e = es[0] if scale is None else min(es, key=lambda e: abs(e.scale - scale))
        with open(self.dat, "rb") as fh:
            fh.seek(e.offset)
            data = fh.read(e.size)
        return Anim(e.name, e.frames, e.bones, e.kind, data, self.version)


_PACKS = {}


def packs(mod):
    """The animation packs the game reads for this mod. Medieval II loads ONE pack (anim_db load_anims: the mod's
    own, else the game's - never both) and only with skeletons it lets in beside it (_m2_folders); none loaded, it
    reads the loose .cas files descr_skeleton.txt names - so do these: [the pack] or []. Rome: every pack there is,
    the mod's own first."""
    m2 = _m2_folders(mod)
    folders = ([m2[0]] if m2[0] else []) if m2 is not None else \
        [f for f in mod.dirs("animations") if _ci(f, "pack.idx") and _ci(f, "pack.dat")]
    out = []
    for folder in folders:
        k = (os.path.normcase(os.path.abspath(folder)), os.path.getmtime(_ci(folder, "pack.idx")))
        if k not in _PACKS:
            _PACKS[k] = Pack(folder)
        out.append(_PACKS[k])
    return out


SKEL_PACK_VERSION = 24          # Medieval II's skeletons.idx / .dat version: (24 << 16) | descr_skeleton.txt's Version


def _pair(folder, base, tag):
    """The version of a pack's .idx + .dat pair as the game takes it (pack_file load_pack_file: both there, the
    same tag, version and count), else None."""
    heads = []
    for ext in (".idx", ".dat"):
        p = _ci(folder, base + ext)
        if not p:
            return None
        try:
            with open(p, "rb") as fh:
                d = fh.read(20)
        except OSError:
            return None
        if len(d) < 20 or not d.startswith(tag):
            return None
        heads.append(struct.unpack_from("<II", d, 12))
    return heads[0][0] if heads[0] == heads[1] else None


def descr_version(mod):
    """descr_skeleton.txt's 'Version' number (anim_db read_version: its first Version line), 0 without one."""
    try:
        path = mod.find("descr_skeleton.txt") or mod.find_any("descr_skeleton.txt")
    except (OSError, ValueError, AttributeError):
        path = None
    if not path:
        return 0
    with open(path, "rb") as fh:
        for line in fh.read().decode("latin-1").splitlines():
            m = re.match(r"\s*version\s+(-?\d+)", line.split(";", 1)[0], re.I)
            if m:
                return int(m.group(1))
    return 0


_M2 = {}


def _m2_folders(mod):
    """Medieval II: (pack folder, skeletons folder) the game loads - each the mod's own, else the game's, that its
    version lets in (the pack 9; the skeletons (24 << 16) | descr_skeleton.txt's Version: with a descr_skeleton.txt
    of another Version the set is not loaded), (None, None) when either is missing: the game then builds every
    skeleton from descr_skeleton.txt and the loose .cas files (anim_db load_anims). None for Rome (packs of version
    4, read as they are)."""
    dirs = mod.dirs("animations")
    try:
        descr = mod.find("descr_skeleton.txt")
    except (OSError, ValueError, AttributeError):
        descr = None
    stamp = tuple((f, tuple(os.path.getmtime(p) if p else 0 for p in (_ci(f, n) for n in (
        "pack.idx", "pack.dat", "skeletons.idx", "skeletons.dat")))) for f in dirs)
    k = (stamp, descr, os.path.getmtime(descr) if descr else 0)
    if k not in _M2:
        versions = [(f, _pair(f, "pack", HEADER)) for f in dirs]
        if any(v == 4 for _, v in versions):
            _M2[k] = None
        else:
            pack = next((f for f, v in versions if v == 9), None)
            want = (SKEL_PACK_VERSION << 16) | (descr_version(mod) & 0xFFFF)
            skel = next((f for f in dirs if _pair(f, "skeletons", b"SKEL.PACK") == want), None)
            _M2[k] = (pack, skel) if pack and skel else (None, None)
    return _M2[k]


class LooseAnim:
    """A man's animation kept as a loose .cas file (no pack holds it) read like Anim: Medieval II reads such files by
    their path when no pack has them (anim_db load_anim_file - SS 6.3's mangonel crew, report R-20261018-D47E51), so
    View in 3D plays them too. The .cas skeleton's 'Scene Root' is left out; every bone's offset is kept (kind =
    bones)."""

    def __init__(self, cas, name):
        skip = 1 if cas.names and cas.names[0].lower().replace(" ", "") == "sceneroot" else 0
        self.name, self.frames, self._cas, self._skip = name, cas.frames, cas, skip
        self.bones = self.kind = cas.bones - skip
        self.moved = tuple(range(self.bones))
        # its skeleton as the game builds one from a .cas (SKELETON_BASE::open): the Scene Root left out, each bone's
        # parent one less, the first the root
        self.names = list(cas.names[skip:])
        self.parents = tuple(-1 if i == 0 else max(-1, cas.parents[i + skip] - skip) for i in range(self.bones))
        self.rest = list(cas.rest[skip:])

    def rotations(self, k):
        return self._cas.rotations(k)[self._skip:]

    def offsets(self, k):
        return self._cas.offsets(k)[self._skip:]


def _rel(name):
    n = _MOD_DIR.sub("", name.replace("\\", "/").lstrip("/"))
    return n[5:] if n.lower().startswith("data/") else n


def loose(mod, name):
    """The LooseAnim of a loose .cas file at this path (mod, game, packs), or None."""
    from . import meshview as MV
    try:
        p = mod.find_any(_rel(name))
        if not p:
            return None
        with open(p, "rb") as fh:
            return LooseAnim(MV.CasAnim(fh.read(), name), name)
    except (OSError, ValueError, AttributeError):
        return None


def find(mod, name, scale=None):
    """The Anim of this name from the first pack holding it (at the scale nearest `scale`: its skeleton's), else its
    loose .cas file (LooseAnim), or None."""
    for p in packs(mod):
        try:
            got = p.anim(name, scale)
        except (OSError, ValueError):
            got = None
        if got is not None:
            return got
    return loose(mod, name)


def _loose_here(mod, name):
    try:
        return bool(mod.find(_rel(name)))
    except (OSError, ValueError, AttributeError):
        return False


def skeletons(mod, name="descr_skeleton.txt"):
    """{skeleton (lower case): [(what, file)]} from descr_skeleton.txt - each skeleton's animations in its order; a
    skeleton with a 'parent' (Medieval II: MTW2_Fast_Bowman's parent MTW2_Bowman) has the parent's, its own lines
    taking the place of the parent's of the same name. name: another file of the same form (Medieval II's siege
    engines: descr_engine_skeleton.txt). Two skeletons named alike but for the letter case: the first one's (look
    one up with skeleton_anims, which tells them apart)."""
    out = {}
    for k, v in _skeleton_table(mod, name).items():
        out.setdefault(k.lower(), v)
    return out


def skeleton_anims(mod, skeleton, name="descr_skeleton.txt"):
    """[(what, file)] of one skeleton: the one of exactly this name, else one named alike in another letter case.
    The games tell names apart by their letter case (RESOURCE_ID: strcmp): Medieval II's own descr_skeleton.txt has
    the halberdier MTW2_Halberd_Primary and the halberd's MTW2_Halberd_primary - read as one, the man took the
    halberd's two-bone base pose and stood in the T pose (report R-20261022-948516: 'the animations don't play')."""
    table = _skeleton_table(mod, name)
    got = table.get(skeleton or "")
    if got is None:
        low = (skeleton or "").lower()
        got = next((v for k, v in table.items() if k.lower() == low), [])
    return got


def _skeleton_table(mod, name):
    """{skeleton (as written): [(what, file)]} - skeletons()'s reading, the letter case kept."""
    path = mod.find(name)
    own, parent = {}, {}
    if not path:
        return {}
    with open(path, "rb") as fh:
        text = fh.read().decode("latin-1")
    cur = None
    for line in text.splitlines():
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        m = re.match(r"type\s+(\S+)", line, re.I)
        if m:
            cur = m.group(1)
            own.setdefault(cur, [])
            continue
        m = re.match(r"parent\s+(\S+)", line, re.I)
        if m and cur is not None:
            parent[cur] = m.group(1)
            continue
        m = re.match(r"anim\s+(\S+)\s+(.+?\.cas)\b", line, re.I)
        if m and cur is not None:
            own[cur].append((m.group(1), m.group(2).strip()))
    out = {}
    low = {}
    for k in own:
        low.setdefault(k.lower(), k)

    def real(name):
        """A parent as the game finds it: this very name, else one alike but for the letter case."""
        return name if name in own else low.get((name or "").lower())

    def whole(name, seen=()):
        if name in out:
            return out[name]
        par = real(parent.get(name))
        lst = list(whole(par, seen + (name,))) if par is not None and par not in seen + (name,) else []
        for what, f in own.get(name, []):
            at = next((i for i, (w, _) in enumerate(lst) if w.lower() == what.lower()), None)
            if at is None:
                lst.append((what, f))
            else:
                lst[at] = (what, f)
        out[name] = lst
        return lst
    for name in own:
        whole(name)
    return out


def of_skeleton(mod, skeleton):
    """[(what, file)] of a skeleton's animations that are in the packs (the same file once, its first name)."""
    names = set()
    for p in packs(mod):
        try:
            names |= set(p.entries)
        except (OSError, ValueError):
            continue
    out, seen = [], set()
    for what, f in skeleton_anims(mod, skeleton):
        if (key(f) in names or _loose_here(mod, f)) and (what, key(f)) not in seen:     # a loose .cas plays too
            seen.add((what, key(f)))
            out.append((what, f))
    # the compiled set the game loads (data/animations/skeletons.dat) has the rest: a skeleton descr_skeleton.txt
    # does not have (HLR keeps its own only there), or one whose text lists only its few own lines and leaves the
    # rest to a parent the text does not hold (#347: a mod's bowman showed only its swimming moves). Its record names
    # its animations by file, and the files say what they are ('LIS 01 Stand Idle') - the file's name shown for each
    files = {key(f) for _, f in out}
    for f in _set_record_anims(mod, skeleton):
        if (key(f) in names or _loose_here(mod, f)) and key(f) not in files:
            files.add(key(f))
            out.append((os.path.splitext(os.path.basename(f))[0], f))
    return out


def why_none(mod, skeleton):
    """Why of_skeleton finds no animation for this skeleton, in plain words - View in 3D says it where the Animation
    list would be."""
    listed = list(dict.fromkeys(key(f) for f in [f for _, f in skeleton_anims(mod, skeleton)] +
                                _set_record_anims(mod, skeleton)))
    if not listed:
        return ("the skeleton %s is neither in descr_skeleton.txt nor in the animation set (data/animations/"
                "skeletons.dat)" % skeleton)
    if packs(mod):
        return "%s: none of its %d animation files is in the animation packs or loose (the first: %s)" % (
            skeleton, len(listed), listed[0])
    return ("%s: there is no animation pack (data/animations/pack.idx, pack.dat) and none of its %d animation "
            "files is loose (the first: %s)" % (skeleton, len(listed), listed[0]))


_SETS = {}


def _set_record_anims(mod, skeleton):
    """The animations a skeleton's record in the animation set the game loads (skeletons.idx / .dat) names."""
    from . import animpacks
    s = _anim_set(mod)
    if s is None:
        return []
    try:
        rec = s.record(skeleton or "")
    except (ValueError, KeyError):
        rec = None
    return animpacks.anim_paths(rec) if rec else []


class Skeleton:
    """A skeleton as the game holds it: each bone's name, its parent (-1: the root), its base pose (its place from
    the parent - where a bone the animation carries no offset for stands), the inverse of its place in the model in
    the pose the meshes are made in (binds: 12 numbers each, 3 rows of a turn and a shift - a point of the mesh times
    its bone's bind, then the bone's place in a frame, is where the point goes: the game's skinning) and the scale
    its animations are kept at."""

    def __init__(self, name, parents, rest, names=None, binds=None, scale=1.0):
        self.name, self.parents, self.rest, self.scale = name, tuple(parents), list(rest), scale
        self.names = list(names or [""] * len(self.parents))
        self.binds = binds if binds is not None else _binds(self.parents, [(0.0, 0.0, 0.0, 1.0)] * len(self.parents),
                                                                self.rest)
        self.index = {}
        for i, n in enumerate(self.names):
            self.index.setdefault(n.lower(), i)

    def __len__(self):
        return len(self.parents)

    def bone(self, name):
        """The number of the bone of this name (any letter case), or None."""
        return self.index.get((name or "").lower())

    @classmethod
    def from_record(cls, name, rec):
        """A Medieval II skeleton from its record in skeletons.dat (SKELETON::pack: the scale, the bone count, the
        IK share; per bone its kind, base pose, parent, two flags and the IK controller (28 bytes), its bind (48) and
        its name), or None when the record is not of that form."""
        try:
            scale, n = struct.unpack_from("<fH", rec, 0)
            if not 0 < n <= 255 or not 0.01 < scale < 100:
                return None
            p, parents, rest, binds, names = 10, [], [], [], []
            for i in range(n):
                _, x, y, z, par = struct.unpack_from("<i3fi", rec, p)
                m = struct.unpack_from("<12f", rec, p + 28)
                end = rec.index(b"\0", p + 76, p + 76 + 100)
                parents.append(-1 if i == 0 else par)
                rest.append((x, y, z))
                binds.append(m)
                names.append(rec[p + 76:end].decode("latin-1"))
                p = end + 1
        except (struct.error, ValueError):
            return None
        if any(not 0 <= parents[i] < i for i in range(1, n)) or not all(_turn_ok(m) for m in binds):
            return None
        return cls(name, parents, rest, names, binds, scale)

    @classmethod
    def from_anim(cls, name, first, default=None):
        """A skeleton built from a .cas animation's own bones (the game's way with descr_skeleton.txt alone: the
        type's first file), its binds from its 'default' animation's first frame (SKELETON::finalise)."""
        sk = cls(name, first.parents, first.rest, first.names)
        if default is not None and default.bones >= len(sk):
            rots = default.rotations(0)
            sk.binds = _binds(sk.parents, rots, sk.offsets(default.offsets(0)))
        return sk

    def offsets(self, given):
        """Each bone's offset: the given one (an animation's frame), else its base pose."""
        return [given[b] if b < len(given) and given[b] is not None else self.rest[b] for b in range(len(self))]


def _turn_ok(m):
    """Whether a bind's turn is a turn (each row of length 1, finite) - a record with a bind never made (a skeleton
    with no 'default' or 'stand_a_idle' is left unmade by the game) holds zeros there."""
    try:
        return all(abs(m[4 * r] ** 2 + m[4 * r + 1] ** 2 + m[4 * r + 2] ** 2 - 1.0) < 0.01 for r in range(3)) and \
            all(abs(v) < 1e4 for v in m)
    except (TypeError, OverflowError):
        return False


def world(parents, rotations, offsets):
    """Every bone's turn and place in the model from their own turns and offsets from their parents."""
    from .meshview import _qmul, _qrot
    rot, where = [], []
    for b, par in enumerate(parents):
        q, t = rotations[b], offsets[b]
        if par < 0:
            rot.append(tuple(q))
            where.append(tuple(t))
        else:
            o = _qrot(rot[par], t)
            where.append(tuple(where[par][k] + o[k] for k in range(3)))
            rot.append(_qmul(rot[par], q))
    return rot, where


def _binds(parents, rotations, offsets):
    """Each bone's bind (3 rows of 4: turn and shift): the inverse of its place in the model in this pose."""
    from .meshview import _qmat
    rot, where = world(parents, rotations, offsets)
    out = []
    for q, t in zip(rot, where):
        m = _qmat(q)                                # the inverse turn: the turn's rows read as columns
        inv = (m[0], m[3], m[6], m[1], m[4], m[7], m[2], m[5], m[8])
        sh = tuple(-(inv[3 * r] * t[0] + inv[3 * r + 1] * t[1] + inv[3 * r + 2] * t[2]) for r in range(3))
        out.append((inv[0], inv[1], inv[2], sh[0], inv[3], inv[4], inv[5], sh[1], inv[6], inv[7], inv[8], sh[2]))
    return out


class _SkelSet:
    """skeletons.idx + .dat of one folder (animpacks.AnimSet's skeletons and record without the 50 MB pack)."""

    def __init__(self, folder):
        from . import animpacks
        self.folder, self.data = folder, {}
        for n in ("skeletons.idx", "skeletons.dat"):
            with open(_ci(folder, n), "rb") as fh:
                self.data[n] = fh.read()
        self.skeletons = lambda: animpacks.AnimSet.skeletons(self)
        self.record = lambda name: animpacks.AnimSet.record(self, name)


def _anim_set(mod):
    """The skeletons the game loads for this mod - Medieval II: the skeletons.dat its version lets in, with a pack
    (_m2_folders); Rome: its own four files, else the game's - read once, or None (the game builds them from
    descr_skeleton.txt and the .cas files)."""
    from . import animpacks
    m2 = _m2_folders(mod)
    for folder in ([m2[1]] if m2[1] else []) if m2 is not None else mod.dirs("animations"):
        idx = _ci(folder, "skeletons.idx")
        if not idx:
            continue
        k = (os.path.normcase(os.path.abspath(folder)), os.path.getmtime(idx), m2 is not None)
        if k not in _SETS:
            try:
                _SETS[k] = _SkelSet(folder) if m2 is not None else animpacks.AnimSet.at(folder)
            except (OSError, ValueError):
                _SETS[k] = None
        if _SETS[k] is not None:
            return _SETS[k]
    return None


def skeleton(mod, name):
    """The Skeleton of this name as the game has it: its record in the set the game loads (skeletons.dat - the name
    as written, else alike but for the letter case), else built from its first .cas file (descr_skeleton.txt; a
    'parent' gives its skeleton), its binds from its 'default' animation. None when neither is there (the game could
    not play it either)."""
    s = _anim_set(mod)
    rec = None
    if s is not None:
        try:
            rec = s.record(name or "")
        except (ValueError, KeyError):
            rec = None
    got = Skeleton.from_record(name, rec) if rec else None
    if got is None:
        anims = skeleton_anims(mod, name)
        first = next((a for a in (find(mod, f) for _, f in anims[:1]) if a is not None), None)
        if first is not None and getattr(first, "parents", None):
            default = next((find(mod, f) for what, f in anims if what.lower() == "default"), None)
            got = Skeleton.from_anim(name, first, default)
    return got


DEBUG_CAP = 2 * 1024 * 1024        # the files a report takes along from the 3D view, at most (the zip's cap is 4 MB)


def _head(path):
    """'tag, version, count, size' of a pack / skeleton file's first 20 bytes."""
    try:
        with open(path, "rb") as fh:
            d = fh.read(20)
        tag = d[:9].decode("latin-1", "replace")
        ver, count = struct.unpack_from("<II", d, 12) if len(d) >= 20 else (None, None)
        return "%s version %s (0x%x) count %s, %d bytes" % (tag, ver, ver or 0, count, os.path.getsize(path))
    except (OSError, struct.error) as e:
        return "unreadable: %s" % e


def _block(mod, skeleton, name="descr_skeleton.txt"):
    """The lines of a skeleton's 'type' block in descr_skeleton.txt as written (its parent's too), or ''."""
    path = mod.find(name)
    if not path:
        return ""
    with open(path, "rb") as fh:
        lines = fh.read().decode("latin-1").splitlines()
    out, keep, want = [], False, [(skeleton or "").lower()]
    for line in lines:
        m = re.match(r"\s*type\s+(\S+)", line, re.I)
        if m:
            keep = m.group(1).lower() in want
        elif keep:
            pm = re.match(r"\s*parent\s+(\S+)", line, re.I)
            if pm and pm.group(1).lower() not in want:
                want.append(pm.group(1).lower())
        if keep:
            out.append(line)
    return "\n".join(out)


def debug_files(mod, skeletons, anims, meshes):
    """[(name in a report's zip, bytes)] of what View in 3D drew a model with - so a model that looks wrong in a
    mod can be drawn again the same way by the author (the user, 2026-10-23: a mod's knights crushed, its files out
    of reach): view.txt (the animation folders' four files' heads - which set the game loads -, each skeleton as read
    and where from, each animation's pack record, its descr_skeleton.txt lines), each skeleton's own record, each
    animation's bytes (pack record or loose .cas) and the meshes. skeletons: names; anims: animation files; meshes:
    paths on disk."""
    lines, out, size = ["View in 3D: what the model was drawn with", ""], [], 0

    def take(name, data):
        nonlocal size
        if size + len(data) > DEBUG_CAP:
            lines.append("  (%s left out: %d KB over the report's room)" % (name, len(data) // 1024))
            return
        size += len(data)
        out.append(("3d_view/" + name, data))

    def safe(n):
        return re.sub(r"[^\w.-]+", "_", n)[:80]
    loaded, m2 = _anim_set(mod), _m2_folders(mod)
    if m2 is not None:
        lines.append("Medieval II: descr_skeleton.txt Version %d - the game loads the pack of %s and the skeletons of "
                     "%s%s" % (descr_version(mod), m2[0], m2[1], "" if m2[0] else
                               " (none: it builds them from descr_skeleton.txt and the loose .cas files)"))
    for folder in mod.dirs("animations"):
        lines.append("folder %s%s" % (folder, " - its skeletons read" if loaded is not None and
                                      os.path.normcase(loaded.folder) == os.path.normcase(folder) else ""))
        for n in ("pack.idx", "pack.dat", "skeletons.idx", "skeletons.dat"):
            p = _ci(folder, n)
            lines.append("  %s: %s" % (n, _head(p) if p else "none"))
    lines.append("")
    for sk in dict.fromkeys(k for k in skeletons if k):
        rec = None
        if loaded is not None:
            try:
                rec = loaded.record(sk)
            except (ValueError, KeyError):
                rec = None
        got = Skeleton.from_record(sk, rec) if rec else None
        lines.append("skeleton %s: record %s%s" % (sk, "%d bytes" % len(rec) if rec else "none",
                                                    "" if not rec else " - read" if got else " - NOT read"))
        if rec:
            take("skeleton_%s.rec" % safe(sk), rec)
        use = got or skeleton(mod, sk)
        if use is not None:
            lines.append("  used: %s, %d bones, scale %g" % ("its record" if got else "its first .cas", len(use),
                                                            use.scale))
            for b in range(len(use)):
                lines.append("    %2d %-24s parent %2d rest %s" % (b, use.names[b], use.parents[b],
                                                                    ", ".join("%.4f" % v for v in use.rest[b])))
        else:
            lines.append("  used: none (no record, no first .cas)")
        block = _block(mod, sk)
        if block:
            take("descr_skeleton_%s.txt" % safe(sk), block.encode("latin-1", "replace"))
    lines.append("")
    for f in dict.fromkeys(a for a in anims if a):
        lines.append("animation %s" % f)
        for p in packs(mod):
            try:
                es = p.entries.get(key(f)) or []
            except (OSError, ValueError):
                es = []
            for e in es:
                lines.append("  in %s (version %s): scale %g frames %d bones %d kind %d, %d bytes" % (
                    p.folder, p.version, e.scale, e.frames, e.bones, e.kind, e.size))
                try:
                    with open(p.dat, "rb") as fh:
                        fh.seek(e.offset)
                        data = fh.read(e.size)
                    lines.append("    moved bones: %s" % (moved_bones(data, e.frames, e.bones, e.kind, p.version),))
                    take("anim_%s_%g_%d.bin" % (safe(os.path.basename(e.name)), e.scale, len(out)), data)
                except (OSError, ValueError, struct.error) as err:
                    lines.append("    unreadable: %s" % err)
        try:
            lp = mod.find(_rel(f))
        except (OSError, ValueError, AttributeError):
            lp = None
        if lp:
            lines.append("  loose: %s" % lp)
            with open(lp, "rb") as fh:
                take("loose_" + safe(os.path.basename(lp)), fh.read())
    lines.append("")
    for m in dict.fromkeys(x for x in meshes if x):
        lines.append("mesh %s" % m)
        try:
            with open(m, "rb") as fh:
                take(safe(os.path.basename(m)), fh.read())
        except OSError as e:
            lines.append("  unreadable: %s" % e)
    return [("3d_view/view.txt", "\n".join(lines).encode("utf-8"))] + out


__all__ = ["FPS", "Anim", "Pack", "read_index", "key", "packs", "find", "skeletons", "skeleton_anims", "of_skeleton",
           "why_none", "debug_files", "Skeleton", "skeleton", "world", "moved_bones"]
