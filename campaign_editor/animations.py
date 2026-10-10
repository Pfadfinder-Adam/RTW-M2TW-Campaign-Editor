"""The games' battle animations, read from their packs (data/animations/pack.idx + pack.dat - Rome, Barbarian
Invasion, Medieval II) to pose a battle model in the 3D view and play it.

pack.idx: 'ANIM.PACK', a version (4 Rome / BI, 9 Medieval II) and the count at byte 16; from byte 20 one record per
animation: its record size, offset into pack.dat, size, scale (Rome keeps most twice, at 1.0 and 1.1), frames,
bones, kind, then the name ('data/animations/...cas'). An animation in pack.dat: frames, bones, kind again, then for
every frame each bone's own turn (a quaternion x y z w, from its parent), then for every frame the offsets of the
first `kind` bones (x y z from the parent): kind 1 = the pelvis alone (Rome's usual), kind = bones (Medieval II's
usual: every bone). XIDX (the Europa Barbarorum team's pack tool) reads the records the same way.

descr_skeleton.txt names each skeleton's animations: 'type <skeleton>', then 'anim <what> <file> ...' lines.
A Rome model's bones are its own (meshview.read_cas); a Medieval II mesh is made in the pose of its skeleton's
'default' animation (the base pose) - meshview.pose_mesh turns it from there."""

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
    """One animation: frames, bones, kind; rotations(k) = each bone's own turn in frame k, offsets(k) = the offsets
    of its first `kind` bones from their parents (kind 1: the pelvis alone)."""

    def __init__(self, name, frames, bones, kind, data):
        self.name, self.frames, self.bones, self.kind, self.data = name, frames, bones, kind, data
        need = 5 + 16 * frames * bones + 12 * frames * kind
        if frames < 1 or bones < 1 or len(data) < need:
            raise ValueError("%s: not an animation the editor can read" % name)

    def rotations(self, k):
        k = max(0, min(self.frames - 1, k))
        return list(struct.iter_unpack("<4f", self.data[5 + 16 * k * self.bones:5 + 16 * (k + 1) * self.bones]))

    def offsets(self, k):
        k = max(0, min(self.frames - 1, k))
        at = 5 + 16 * self.frames * self.bones + 12 * k * self.kind
        return list(struct.iter_unpack("<3f", self.data[at:at + 12 * self.kind]))


def read_index(data):
    """[Entry] of a pack.idx's bytes (ValueError when it is not one)."""
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
    return out


def key(name):
    """An animation's name as packs and descr_skeleton meet: data/animations/x.cas, any case, either slash."""
    n = name.strip().strip('"').replace("\\", "/").lower()
    return n if n.startswith("data/") else "data/" + n.lstrip("/")


class Pack:
    def __init__(self, folder):
        self.folder = folder
        self.idx, self.dat = _ci(folder, "pack.idx"), _ci(folder, "pack.dat")
        self._entries = None

    @property
    def entries(self):
        """{key: [Entry, ...]} - the scales of one animation together, 1.0 first."""
        if self._entries is None:
            with open(self.idx, "rb") as fh:
                found = read_index(fh.read())
            self._entries = {}
            for e in found:
                self._entries.setdefault(key(e.name), []).append(e)
            for es in self._entries.values():
                es.sort(key=lambda e: abs(e.scale - 1.0))
        return self._entries

    def anim(self, name):
        es = self.entries.get(key(name))
        if not es or not self.dat:
            return None
        e = es[0]
        with open(self.dat, "rb") as fh:
            fh.seek(e.offset)
            data = fh.read(e.size)
        return Anim(e.name, e.frames, e.bones, e.kind, data)


_PACKS = {}


def packs(mod):
    """The animation packs the game reads for this mod, its own first (data/animations, any case)."""
    out = []
    for folder in mod.dirs("animations"):
        if _ci(folder, "pack.idx") and _ci(folder, "pack.dat"):
            k = (os.path.normcase(os.path.abspath(folder)), os.path.getmtime(_ci(folder, "pack.idx")))
            if k not in _PACKS:
                _PACKS[k] = Pack(folder)
            out.append(_PACKS[k])
    return out


def find(mod, name):
    """The Anim of this name from the first pack holding it, or None."""
    for p in packs(mod):
        try:
            got = p.anim(name)
        except (OSError, ValueError):
            got = None
        if got is not None:
            return got
    return None


def skeletons(mod):
    """{skeleton (lower case): [(what, file)]} from descr_skeleton.txt - each skeleton's animations in its order; a
    skeleton with a 'parent' (Medieval II: MTW2_Fast_Bowman's parent MTW2_Bowman) has the parent's, its own lines
    taking the place of the parent's of the same name."""
    path = mod.find("descr_skeleton.txt")
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
        m = re.match(r"type\s+(\S+)", line)
        if m:
            cur = m.group(1).lower()
            own.setdefault(cur, [])
            continue
        m = re.match(r"parent\s+(\S+)", line)
        if m and cur is not None:
            parent[cur] = m.group(1).lower()
            continue
        m = re.match(r"anim\s+(\S+)\s+(.+?\.cas)\b", line, re.I)
        if m and cur is not None:
            own[cur].append((m.group(1), m.group(2).strip()))
    out = {}

    def whole(name, seen=()):
        if name in out:
            return out[name]
        lst = list(whole(parent[name], seen + (name,))) if parent.get(name) in own and \
            parent[name] not in seen + (name,) else []
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
    for what, f in skeletons(mod).get((skeleton or "").lower(), []):
        if key(f) in names and (what, key(f)) not in seen:
            seen.add((what, key(f)))
            out.append((what, f))
    return out


def base_pose(mod, skeleton):
    """Medieval II: the skeleton's base pose (its 'default' animation, frame 0) as (rotations, offsets) - the pose its
    meshes are made in - with every bone's offset (the base pose holds the pelvis's alone: the others from the first
    of the skeleton's animations that has them all). None when not found."""
    anims = skeletons(mod).get((skeleton or "").lower(), [])
    base = next((find(mod, f) for what, f in anims if what.lower() == "default"), None)
    if base is None:
        return None
    offsets = base.offsets(0)
    if len(offsets) < base.bones:
        full = None
        for _, f in anims:
            a = find(mod, f)
            if a is not None and a.kind >= base.bones:
                full = a
                break
        if full is None:
            return None
        offsets = offsets + full.offsets(0)[len(offsets):base.bones]
    return base.rotations(0), offsets


__all__ = ["FPS", "Anim", "Pack", "read_index", "key", "packs", "find", "skeletons", "of_skeleton", "base_pose"]
