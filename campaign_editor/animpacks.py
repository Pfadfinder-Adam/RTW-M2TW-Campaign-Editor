"""Skeletons and their animations carried from one mod into another (Bring units) - Rome, Barbarian Invasion and REX.

The game loads ONE set of four files (exe study, open.md 'BRING EVERYTHING A UNIT NEEDS'): the mod's own
data/animations/pack.idx + pack.dat + skeletons.idx + skeletons.dat when it has all four, else the game's own -
descr_skeleton.txt and loose .cas files are read only when no set loads. So a skeleton a mod like HLR has of its own
reaches another mod only inside that mod's set: the target's set (its own, or the game's for a mod that keeps only
its changes) written into the target mod's folder with the source's skeleton records and every animation they name
appended.

skeletons.idx / .dat: 'SKEL.PACK', 3 stamp bytes, a version (u32; Rome 3), the count (u32) at byte 16; idx records
= u32 name length + 1, u32 offset, u32 size, the name + NUL; the dat holds the records one after another from byte
20. A record names its animations by path ('data/animations/...cas') and holds no offsets of its own - the same
bytes stand at other places in Rome's and Barbarian Invasion's files - so it is copied as it is.
pack.idx / .dat: 'ANIM.PACK', the version and the count at 16 the same way; idx records = u32 (name length + 10), u32
offset, u32 size, f32 scale, u16 frames, u16 bones, u8 kind, the name + NUL (animations.read_index); Rome keeps most
animations twice (scale 1.0 and 1.1), each its own bytes in the dat.
Medieval II's skeletons.idx has another head (not decoded) - its skeletons are not carried (the nearest is taken)."""

import os
import re
import struct

from .moddata import ci_path

FILES = ("pack.idx", "pack.dat", "skeletons.idx", "skeletons.dat")
RE_ANIM = re.compile(rb"data/animations/[^\x00\r\n]{1,240}?\.cas", re.I)
CACHE = "aninterp.cache"                   # REX's own cache of the animations: made again when it is gone


def _key(name):
    return name.replace("\\", "/").lower()


class AnimSet:
    """One set of the four files (bytes read once)."""

    def __init__(self, folder):
        self.folder = folder
        self.data = {}
        for name in FILES:
            p = ci_path(folder, name)
            with open(p, "rb") as fh:
                self.data[name] = fh.read()

    @classmethod
    def at(cls, folder):
        """The set in folder, or None when one of the four is missing or it is not a set this module reads."""
        if not folder or not all(ci_path(folder, n) for n in FILES):
            return None
        try:
            s = cls(folder)
            s.skeletons()
            s.anims()
        except (OSError, ValueError, struct.error):
            return None
        return s

    # ---- reading ----
    def skeletons(self):
        """{name: (offset, size)} of skeletons.idx (ValueError when it is not a Rome one)."""
        d = self.data["skeletons.idx"]
        if not d.startswith(b"SKEL.PACK") or struct.unpack_from("<I", d, 12)[0] != 3:
            raise ValueError("not a Rome skeleton pack")
        n = struct.unpack_from("<I", d, 16)[0]
        out, p = {}, 20
        for _ in range(n):
            ln, off, size = struct.unpack_from("<III", d, p)
            out[d[p + 12:p + 11 + ln].decode("latin-1")] = (off, size)
            p += 12 + ln
        return out

    def record(self, name):
        got = next((v for k, v in self.skeletons().items() if k.lower() == name.lower()), None)
        if got is None:
            return None
        return self.data["skeletons.dat"][got[0]:got[0] + got[1]]

    def anims(self):
        """[(key, idx record bytes, offset, size)] of pack.idx, in its order."""
        d = self.data["pack.idx"]
        if not d.startswith(b"ANIM.PACK"):
            raise ValueError("not an animation pack")
        n = struct.unpack_from("<I", d, 16)[0]
        out, p = [], 20
        for _ in range(n):
            ln, off, size = struct.unpack_from("<III", d, p)
            end = p + 21 + (ln - 10)
            if d[end:end + 1] != b"\0":
                raise ValueError("an animation record of another form")
            out.append((_key(d[p + 21:end].decode("latin-1")), d[p:end + 1], off, size))
            p = end + 1
        return out

    def anim_bytes(self, key):
        """[(idx record, data)] of every animation of this name (each scale)."""
        dat = self.data["pack.dat"]
        return [(rec, dat[off:off + size]) for k, rec, off, size in self.anims() if k == key]


def anim_paths(record):
    """The animations a skeleton record names, each once, in their order."""
    out = []
    for m in RE_ANIM.finditer(record):
        k = _key(m.group(0).decode("latin-1"))
        if k not in out:
            out.append(k)
    return out


def loaded_set(mod):
    """The set the game loads for this mod: its own folder's four files, else the game's under it."""
    for folder in mod.dirs("animations"):
        s = AnimSet.at(folder)
        if s is not None:
            return s
    return None


def game_set(mod):
    """The game's own set (the game folder's data/animations), to tell a mod's own skeletons from the game's."""
    from .newmod import game_of
    try:
        root = ci_path(game_of(mod.data), "data")
    except Exception:
        return None
    return AnimSet.at(ci_path(root, "animations")) if root else None


def skeleton_names(mod):
    """The skeleton names the game knows for this mod: its loaded set's (lower case); empty when none is read."""
    s = loaded_set(mod)
    return {k.lower() for k in s.skeletons()} if s else set()


# ---------------------------------------------------------------------------
# Taking out (with the units) and putting in
# ---------------------------------------------------------------------------
def collect(mod, names):
    """The skeletons of names this mod has of its OWN (not in the game's set, or other bytes there) with every
    animation they name: {'skeletons': {name: record}, 'anims': {key: [(idx record, data)]}}; empty when the mod
    loads the game's own set or reads none."""
    src = loaded_set(mod)
    out = {"skeletons": {}, "anims": {}}
    if src is None:
        return out
    base = game_set(mod)
    if base is not None and os.path.normcase(os.path.abspath(base.folder)) == \
            os.path.normcase(os.path.abspath(src.folder)):
        return out
    for name in names:
        rec = src.record(name)
        if rec is None:
            continue
        if base is not None and base.record(name) == rec:
            continue                                        # the game's own: every mod of the game has it
        real = next(k for k in src.skeletons() if k.lower() == name.lower())
        out["skeletons"][real] = rec
        for key in anim_paths(rec):
            if key not in out["anims"]:
                # one the mod's set lacks taken from the game's own (BI's set names 32 it lacks, 29 of them in
                # Rome's - BI seems to take them from the game under it)
                out["anims"][key] = src.anim_bytes(key) or (base.anim_bytes(key) if base is not None else [])
    return out


def merged(target, carried):
    """(the four files' new bytes {name: bytes}, [skeletons added], [animations added]) of target's set with the
    carried skeletons it lacks and the animations they name that it lacks appended (counts raised, heads kept)."""
    have = {k.lower() for k in target.skeletons()}
    new_sk = [(n, r) for n, r in carried["skeletons"].items() if n.lower() not in have]
    if not new_sk:
        return None, [], ([], [])
    anims_have = {k for k, _, _, _ in target.anims()}
    want = []
    for _, rec in new_sk:
        want += [k for k in anim_paths(rec) if k not in anims_have and k not in want]
    data = dict(target.data)
    # animations: appended to pack.dat, their idx records with the new offsets
    pdat, pidx = bytearray(data["pack.dat"]), bytearray(data["pack.idx"])
    added = 0
    for key in want:
        for rec, body in carried["anims"].get(key, []):
            rec = bytearray(rec)
            struct.pack_into("<I", rec, 4, len(pdat))
            pidx += rec
            pdat += body
            added += 1
    for buf in (pidx, pdat):
        struct.pack_into("<I", buf, 16, struct.unpack_from("<I", buf, 16)[0] + added)
    sdat, sidx = bytearray(data["skeletons.dat"]), bytearray(data["skeletons.idx"])
    for name, rec in new_sk:
        raw = name.encode("latin-1")
        sidx += struct.pack("<III", len(raw) + 1, len(sdat), len(rec)) + raw + b"\0"
        sdat += rec
    for buf in (sidx, sdat):
        struct.pack_into("<I", buf, 16, struct.unpack_from("<I", buf, 16)[0] + len(new_sk))
    data.update({"pack.idx": bytes(pidx), "pack.dat": bytes(pdat), "skeletons.idx": bytes(sidx),
                 "skeletons.dat": bytes(sdat)})
    missing = [k for k in want if not carried["anims"].get(k)]
    return data, [n for n, _ in new_sk], (want, missing)


def put(plan, carried):
    """The carried skeletons the target lacks written into the target mod's own set (a copy of the one it loads,
    with them appended); REX's animation cache beside it taken away. -> [skeleton names added]."""
    if not carried or not carried.get("skeletons"):
        return []
    mod = plan.mod
    target = loaded_set(mod)
    if target is None:
        plan.warn(None, "the brought units' own skeletons (%s) were not carried: this mod reads no animation set the "
                        "editor knows (the nearest skeletons are taken)" % ", ".join(sorted(carried["skeletons"])))
        return []
    data, added, (anims, missing) = merged(target, carried)
    if not added:
        return []
    own = ci_path(mod.data, "animations") or os.path.join(mod.data, "animations")
    for name in FILES:
        path = ci_path(own, name) if os.path.isdir(own) else None
        plan.binary(path or os.path.join(own, name), data[name])
    cache = ci_path(own, CACHE) if os.path.isdir(own) else None
    if cache:
        plan.delete(cache, "REX's cache of the animations - it makes it again")
    plan.note(None, "data/animations: %d skeleton(s) of the brought units added to this mod's animation set (%s) with "
                    "%d animation(s) they move by%s" % (len(added), ", ".join(added), len(anims),
                                                     "" if os.path.normcase(target.folder) == os.path.normcase(own)
                                                     else " - the set the game read is copied into this mod first"))
    if missing:                                   # the games' own sets name some they lack too (BI: 32) - no harm
        plan.note(None, "%d animation(s) the brought skeletons name are not in the source's set either (the games' "
                        "own sets have such names too): %s%s" % (len(missing), ", ".join(missing[:3]),
                                                                 " ..." if len(missing) > 3 else ""))
    return added
