"""Medieval II battle models (.mesh) read and drawn in 3D for Units - with Pillow alone.

A .mesh is a Boost binary archive (a 4-byte length + "serialization::archive", then 03 04 04 04 08 01). What the
tool reads of it (worked out on the 3336 vanilla unit meshes; nothing else is needed to draw a man):

  groups     a linked list of parts, each: name (4-byte length + text: Head, Arms, Legs, Hands, Body, and after an
             "Attachments..." part the weapons and shields: primaryactive0, secondaryactive0/1, shield0 ...),
             material (head_01, arms_Lmail_02, kite pattern_44 ...; the first part has 2 bytes of class info
             after it), a 4-byte triangle count, then 3 x 2-byte vertex numbers per triangle. Several parts of
             one name are the variants the game picks from per man (three heads, four pairs of legs ...).
  vertices   one buffer for every part: streams of a 4-byte kind (+ 2 bytes of class info on a kind's first
             use), the 4-byte vertex count and the values - kind 4 texture u v (2 floats), 1 bone weights
             (2 floats), 0 position x y z (3 floats; y up, the man faces +z, arms out in a T), 2 bone numbers
             (4 bytes), 3 normal / 10 and 11 tangent frame (4 bytes B G R 0 as 0..255 = -1..1, or 3 floats).
  the rest   the skeleton's bone names and the bounding box - not needed here.

The texture u runs over two pictures side by side: u below 0.5 is the unit's texture (modeldb `textures` per
faction) at 2u, u from 0.5 the attachment texture (modeldb `attach`: weapons and shields) at 2u - 1; v as it is
(0 = the picture's top row). Parts from the first "Attachments..." part on are the weapons and shields (and the
teeth). Rome's .cas models: read_cas."""

import math
import os
import re
import struct

try:                                    # the heavy 3D work on arrays when NumPy is there (the exe has it)
    from . import fastmesh as _fast
except ImportError:                     # a Python without NumPy: the pure-Python ways below
    _fast = None

HEADER = b"serialization::archive"
KNOWN = {0, 1, 2, 3, 4, 10, 11}                     # stream kinds seen in the vanilla meshes
SIZES = {0: (12,), 1: (8,), 4: (8,), 2: (4,), 3: (4, 12), 10: (4, 12), 11: (4, 12)}
POS, UV, NORMAL, BONES, WEIGHTS = 0, 4, 3, 2, 1
LIGHT = (-0.35, 0.55, 0.76)
BACK = (46, 48, 54)
PLAIN = (150, 144, 132)                             # a part with no texture: dull steel / leather
# part names that are weapons, shields and gear (every vanilla M2TW mesh read): the "Weapons and shield" box hides them
WEAPON_PARTS = ("primary", "secondary", "shield", "equipment", "ramrod", "cannon ball", "ballista arrow", "sword")


class MeshError(ValueError):
    pass


class Group:
    def __init__(self, name, material, tris, attachment):
        self.name, self.material, self.tris, self.attachment = name, material, tris, attachment

    def __repr__(self):
        return "Group(%s, %s, %d triangles)" % (self.name, self.material, len(self.tris) // 3)


class Mesh:
    """groups [Group]; positions [(x, y, z)], uvs [(u, v)] or None, count = number of vertices. one_texture: u v
    over one picture (Rome) instead of the man's and the attachment texture side by side (Medieval II)."""

    def __init__(self, groups, positions, uvs):
        self.groups, self.uvs = groups, uvs
        self._pos, self._arr = None, None
        if _fast is not None and isinstance(positions, _fast.np.ndarray):
            self._arr = positions               # posed on NumPy: kept as the array, a list only when asked for
        else:
            self._pos = positions
        self.count = len(positions)
        self.one_texture = False
        self.texture_ref = None
        self.skin = None                # Medieval II: [(primary bone, secondary bone, weight, weight)] per point
        self.parents = None             # Medieval II: its skeleton's bone tree (None: a man's, M2_PARENTS)
        self.joints = None              # posed: every bone's place in the model (pose_mesh)
        self.turns = None               # posed: every bone's turn in the model
        self.bone_names = {}            # Medieval II: {bone number: name} as the file lists them

    @property
    def positions(self):
        """[(x, y, z)] of every point (made from the array once when the points were posed on NumPy)."""
        if self._pos is None:
            self._pos = list(map(tuple, self._arr.tolist()))
        return self._pos

    @positions.setter
    def positions(self, value):
        self._pos, self._arr = value, None

    @property
    def arr(self):
        """The points as an (n, 3) NumPy array (made once) - None without NumPy."""
        if self._arr is None and _fast is not None:
            self._arr = _fast.np.asarray(self._pos, dtype=_fast.np.float64).reshape(-1, 3)
        return self._arr

    def parts(self):
        """{part name: [its variants]} in file order."""
        out = {}
        for g in self.groups:
            out.setdefault(g.name, []).append(g)
        return out

    def shown(self, look=0, weapons=True):
        """The groups one man shows: variant `look` (mod the count) of every part; weapons and shields when asked.
        A man holding his primary weapon shows no secondary one (the game swaps them)."""
        parts = self.parts()
        if self.one_texture:           # Rome: parts of one name are all worn (three shoulder pads), not variants
            parts = {id(g): [g] for g in self.groups}
            names = {id(g): g.name for g in self.groups}
        else:
            names = {n: n for n in parts}
        primary = any(n.lower().startswith("primary") for n in names.values())
        out = []
        for key, gs in parts.items():
            name = names[key]
            low = name.lower()
            # weapons and shields by their name: a file may list body parts (legs, heads) after its first
            # "Attachments" part too (vanilla peasants: Legs after Attachments3)
            if low.startswith(WEAPON_PARTS):
                if not weapons or (primary and low.startswith("secondary")):
                    continue
            out.append(gs[look % len(gs)])
        return out

    def variants(self, look=0, weapons=True):
        """[(part, which, of)] of the parts that come in several variants, as `look` shows them - e.g. Head 2 of 4,
        shield 5 of 8 (the game picks each part per man; there is no fixed number of men). Rome: []."""
        if self.one_texture:
            return []
        out = []
        for name, gs in self.parts().items():
            low = name.lower()
            if len(gs) < 2 or (not weapons and low.startswith(WEAPON_PARTS)):
                continue
            label = ("shield" if low.startswith("shield") else "weapon" if low.startswith(("primary", "secondary"))
                     else name.strip())
            out.append((label, look % len(gs) + 1, len(gs)))
        for label in {l for l, _, _ in out}:           # two weapons: first weapon / second weapon
            same = [i for i, (l, _, _) in enumerate(out) if l == label]
            if len(same) > 1:
                for k, i in enumerate(same):
                    out[i] = ("%s %s" % (("first", "second", "third", "fourth")[min(k, 3)], label),) + out[i][1:]
        return out

    def looks(self):
        """How many looks 'Another man' steps through before all repeat (the most variants of one part; Rome:
        one)."""
        if self.one_texture:
            return 1
        return max((len(v) for v in self.parts().values()), default=1)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def _string(d, p):
    if p + 4 > len(d):
        return None
    n = struct.unpack_from("<I", d, p)[0]
    if not 1 <= n <= 200 or p + 4 + n > len(d):
        return None
    b = d[p + 4:p + 4 + n]
    if not all(32 <= c < 127 for c in b):
        return None
    return b.decode("latin-1"), p + 4 + n


def _empty(d, p):
    """An empty string (length 0) at p -> ('', p + 4), else None."""
    if p + 4 <= len(d) and struct.unpack_from("<I", d, p)[0] == 0:
        return "", p + 4
    return None


def _groups(d, empty=False):
    out = []
    p, window, attach = 32, 240, False
    while p < len(d):
        found = None
        for q in range(p, min(p + window, len(d))):
            a = _string(d, q)
            b = a and (_string(d, a[1]) or (empty and _empty(d, a[1])))
            if not b:
                continue
            best = None
            # 2 bytes of class info after the first part's material; a part with no material (the battle
            # banners' 'GenMesh') has 1
            for skip in ((0, 2) if b[0] else (0, 1, 2)):
                r = b[1] + skip
                if r + 4 > len(d):
                    continue
                n = struct.unpack_from("<I", d, r)[0]
                if 1 <= n and r + 4 + 6 * n <= len(d) and (best is None or n < best[1]):
                    best = (r, n)
            if best:
                found = (a[0], b[0]) + best
                break
        if not found:
            break
        name, material, r, n = found
        tris = struct.unpack_from("<%dH" % (3 * n), d, r + 4)
        attach = attach or name.lower().startswith("attachment")
        out.append(Group(name, material, tris, attach))
        p, window = r + 4 + 6 * n, 80
    return out, p


def _kind(d, i):
    """The stream kind before the count at i: 4 bytes, or 4 bytes + 2 of class info on a kind's first use."""
    k6 = struct.unpack_from("<I", d, i - 6)[0] if i >= 6 else 1 << 30
    return k6 if k6 < 64 else struct.unpack_from("<I", d, i - 4)[0]


def _streams(d, start, count):
    key = struct.pack("<I", count)
    cands, p = [], start
    while True:
        i = d.find(key, p)
        if i < 0:
            break
        cands.append(i)
        p = i + 1
    at = set(cands)

    def follow(c):
        chain = [c]
        while True:
            s, k = chain[-1] + 4, _kind(d, chain[-1])
            nxt = None
            for size in SIZES.get(k, (4, 8, 12, 16)):
                e = s + size * count
                nxt = next((e + h for h in range(4, 48) if e + h in at and _kind(d, e + h) in KNOWN), None)
                if nxt:
                    break
            if not nxt:
                return chain
            chain.append(nxt)

    best = []
    for c in cands:              # the longest chain; of equal ones the latest start (a count in a header before
        if _kind(d, c) not in KNOWN:     # the first stream can chain on into the real ones)
            continue
        chain = follow(c)
        if len(chain) >= len(best):
            best = chain
    return {_kind(d, c): c + 4 for c in reversed(best)}      # the first stream of a kind wins


def read(data):
    """A Mesh from a .mesh file's bytes (MeshError when it cannot be read)."""
    if data[4:4 + len(HEADER)] != HEADER:
        raise MeshError("not a Medieval II mesh (no serialization::archive header)")
    groups, end = _groups(data)
    if not groups:                  # a part with no material (the battle banners) - only when nothing else reads
        groups, end = _groups(data, empty=True)
    if not groups:
        raise MeshError("no parts found in the mesh")
    count = max(max(g.tris) for g in groups) + 1
    st = _streams(data, end, count)
    if POS not in st or st[POS] + 12 * count > len(data):
        raise MeshError("the mesh's vertex positions were not found")
    pos = list(struct.iter_unpack("<3f", data[st[POS]:st[POS] + 12 * count]))
    uvs = None
    if UV in st and st[UV] + 8 * count <= len(data):
        uvs = list(struct.iter_unpack("<2f", data[st[UV]:st[UV] + 8 * count]))
    if any(not all(math.isfinite(x) and abs(x) < 1e4 for x in v) for v in pos):
        raise MeshError("the mesh's vertex positions do not look right")
    m = Mesh(groups, pos, uvs)
    if BONES in st and WEIGHTS in st and st[BONES] + 4 * count <= len(data) and st[WEIGHTS] + 8 * count <= len(data):
        # each point's two bones (bytes 0, secondary, primary, 0) and their weights (primary, secondary)
        b = data[st[BONES]:st[BONES] + 4 * count]
        w = list(struct.iter_unpack("<2f", data[st[WEIGHTS]:st[WEIGHTS] + 8 * count]))
        m.skin = [(b[4 * i + 2], b[4 * i + 1], w[i][0], w[i][1]) for i in range(count)]
        m.bone_names = _bone_names(data)
        _animal_tree(m, m.bone_names)
    return m


def _bone_names(data):
    """{bone number: name} from the mesh's list of its skeleton's bones near its end (each a 4-byte length, the name,
    its 4-byte number)."""
    out = {}
    for hit in re.finditer(rb"bone_[A-Za-z0-9_]+", data[-6000:]):
        s, e = hit.start() + len(data) - min(len(data), 6000), hit.end() + len(data) - min(len(data), 6000)
        if s < 4 or e + 4 > len(data) or struct.unpack_from("<I", data, s - 4)[0] != e - s:
            continue
        k = struct.unpack_from("<I", data, e)[0]
        if k < 256:
            out.setdefault(k, data[s:e].decode("latin-1"))
    return out


# Medieval II's horses (fs_horse and its children): the 23 bones in the animations' order (as the mount meshes list
# them) and each one's parent - worked out on a mailed horse running (the leg roots on Spine1 / the saddle stretch
# the mesh least: 0.05 against 0.24 on a man's tree)
HORSE_BONES = ("bone_H_Saddle", "bone_Spine", "bone_Spine1", "bone_Neck", "bone_Head", "bone_RightArm",
               "bone_RightForeArm", "bone_RightHand", "bone_RightFingerBase", "bone_LeftArm", "bone_LeftForeArm",
               "bone_LeftHand", "bone_LeftFingerBase", "bone_Tail1", "bone_Tail2", "bone_RightUpLeg", "bone_RightLeg",
               "bone_RightFoot", "bone_RightToeBase", "bone_LeftUpLeg", "bone_LeftLeg", "bone_LeftFoot",
               "bone_LeftToeBase")
HORSE_PARENTS = (-1, 0, 1, 2, 3, 2, 5, 6, 7, 2, 9, 10, 11, 0, 13, 0, 15, 16, 17, 0, 19, 20, 21)


def _animal_tree(mesh, names):
    """A horse's mesh gets the horse's bone tree, its points' bone numbers put in the animations' order (some files
    list the bones by name - mailed_horse_lod0 - not in that order)."""
    by_name = {n.lower(): k for k, n in names.items()}
    if not all(b.lower() in by_name for b in HORSE_BONES):
        return
    to = {by_name[b.lower()]: i for i, b in enumerate(HORSE_BONES)}
    mesh.skin = [(to.get(b0, 0), to.get(b1, 0), w0, w1) for b0, b1, w0, w1 in mesh.skin]
    mesh.parents = HORSE_PARENTS


# ---------------------------------------------------------------------------
# Rome's .cas
# ---------------------------------------------------------------------------
def _cas_string(d, p, text=True):
    """(bytes, end) of a 4-byte length + bytes at p; text: printable with a closing 0, as names are."""
    if p + 4 > len(d):
        return None
    n = struct.unpack_from("<I", d, p)[0]
    if not (2 if text else 1) <= n <= (80 if text else 200) or p + 4 + n > len(d):
        return None
    b = d[p + 4:p + 4 + n]
    if text and (b[-1] != 0 or not all(32 <= c < 127 for c in b[:-1])):
        return None
    return b, p + 4 + n


def _cas_body(d, r, nbones):
    """The vertex data from r: 2-byte vertex and triangle counts, two flag bytes, [a bone per vertex], positions,
    normals, triangles, [a few bytes], texture u v. None unless the normals are unit long (the check that the
    layout guess is right)."""
    if r + 6 > len(d):
        return None
    nv, nt, one, two = struct.unpack_from("<2H2B", d, r)
    r += 6
    if one != 1 or two > 1 or not nv or not nt:
        return None
    for skinned in (True, False):
        q, vb = r, None
        if skinned:
            if q + 4 * nv > len(d):
                continue
            vb = struct.unpack_from("<%dI" % nv, d, q)
            if max(vb) >= nbones:
                continue
            q += 4 * nv
        extra = next((e for e in (0, 4 * nv)            # a rigid part may keep 4 more bytes a vertex before normals
                      if q + 24 * nv + e + 6 * nt + 8 * nv <= len(d) and sum(
                          abs(x * x + y * y + z * z - 1) < 0.05 for x, y, z in struct.iter_unpack(
                              "<3f", d[q + 12 * nv + e:q + 24 * nv + e])) >= 0.9 * nv), None)
        if extra is None:
            continue
        pos = list(struct.iter_unpack("<3f", d[q:q + 12 * nv]))
        if not all(math.isfinite(x) and abs(x) < 100 for v in pos for x in v):
            continue
        q += 24 * nv + extra
        tris = struct.unpack_from("<%dH" % (3 * nt), d, q)
        if max(tris) >= nv:
            continue
        q += 6 * nt
        for gap in (4, 0, 8, 12, 16):                # u v after a 4-byte 0 in the vanilla files
            if q + gap + 8 * nv > len(d):
                continue
            uv = list(struct.iter_unpack("<2f", d[q + gap:q + gap + 8 * nv]))
            if all(math.isfinite(a) and -4 < a < 4 for v in uv for a in v) and len(set(uv)) > min(2, nv - 1):
                return vb, pos, tris, uv, q + gap + 8 * nv
    return None


def _cas_part(d, p, nbones):
    """A part of a .cas at p (its name's length): (name, bone, transform or None, bones per vertex, positions,
    triangles, uvs, end) or None. After the name come 0 to 2 property texts (Rome 3.05 on: '\\0', 'MESH',
    'GEOM_MESH_KEY_ID = ...'), then (not in the oldest files) the bone it hangs on and 6 or 7 floats - for weapons
    and shields the quaternion x y z w and the place in the model's space."""
    s = _cas_string(d, p)
    if not s:
        return None
    name, q0 = s[0][:-1].decode("latin-1"), s[1]
    starts, q = [q0], q0
    for _ in range(2):
        t = _cas_string(d, q, text=False)
        if not t:
            break
        q = t[1]
        starts.append(q)
    for q in reversed(starts):
        body = _cas_body(d, q, nbones)
        if body:
            return (name, 0, None) + body
        for floats in (7, 6):
            r = q + 4 + 4 * floats
            if r > len(d):
                continue
            bone = struct.unpack_from("<I", d, q)[0]
            if bone >= nbones:
                continue
            body = _cas_body(d, r, nbones)
            if body:
                xf = struct.unpack_from("<7f", d, q + 4) if floats == 7 else None
                if xf and not any(xf):
                    xf = None
                return (name, bone, xf) + body
    return None


def _qrot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def weapon_turn(anim, frame):
    """A weapon skeleton's animation (2 bones: its grip and the weapon) at a frame as one turn in the hand - the
    javelin's throw holds the weapon bone half round (1, 0, 0, 0): point first. Its offsets are not used (the grip
    stays in the hand: its 'default' puts it at the base pose's right hand)."""
    p = Pose.of(anim, frame)
    q = (0.0, 0.0, 0.0, 1.0)
    for r in p.rotations[:2]:
        q = _qmul(q, r)
    return q


def weapon_bones(mesh):
    """{'weapon': [bone numbers], 'shield': [...]} of a man's mesh from its bone names (bone_weapon01 / 02 / 03,
    bone_shield...; the numbers a file gives two names keep the shield's)."""
    out = {"weapon": [], "shield": []}
    shields = {k for k, nm in mesh.bone_names.items() if "shield" in nm.lower()}
    for k, nm in sorted(mesh.bone_names.items()):
        if k < len(M2_PARENTS):
            continue
        part = "shield" if k in shields else "weapon"
        if k not in out[part]:
            out[part].append(k)
    return out


def _qmat(q):
    """A turn (quaternion) as a 3 x 3 matrix, row by row."""
    x, y, z, w = q
    return (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
            2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
            2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y))


POSES = ("t", "frame")                              # Rome: the T pose (the skeleton at rest), the file's first frame


class Pose:
    """A frame of an animation (animations.Anim): each bone's own turn and the offsets of its first bones (Rome: the
    pelvis alone, as a rule) - the bones in the animation's order (Rome: the model's without its Scene Root)."""

    def __init__(self, rotations, offsets=()):
        self.rotations, self.offsets = list(rotations), list(offsets)

    @classmethod
    def of(cls, anim, frame):
        """Frame `frame` of the animation; a frame between two (2.4) is laid between them - the turns blended on the
        shortest way, the offsets in a line - so the move plays smoothly at any drawing speed (past the last frame it
        blends into the first: the walking and running ones go round)."""
        k = int(math.floor(frame))
        t = frame - k
        if t < 1e-6 or anim.frames < 2:
            return cls(anim.rotations(k), anim.offsets(k))
        k %= anim.frames
        n = (k + 1) % anim.frames
        rots = [_blend(a, b, t) for a, b in zip(anim.rotations(k), anim.rotations(n))]
        offs = [tuple(a[i] + (b[i] - a[i]) * t for i in range(3)) for a, b in zip(anim.offsets(k), anim.offsets(n))]
        return cls(rots, offs)


def _blend(a, b, t):
    """Two turns (quaternions) blended by t, the shorter way round, kept a turn (length 1)."""
    if a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3] < 0:
        b = (-b[0], -b[1], -b[2], -b[3])
    q = tuple(a[i] + (b[i] - a[i]) * t for i in range(4))
    n = math.sqrt(sum(x * x for x in q)) or 1.0
    return tuple(x / n for x in q)


def read_cas(data, pose="t"):
    """A Mesh from a Rome .cas file's bytes (worked out on the 807 vanilla unit, mount and animal models, versions
    2.22 to 3.2 in the first 4 bytes as a float). The file: a header (the bone count, then each bone's parent),
    the animation's frame count and times, one record per bone ('Scene Root', bone_pelvis ... - frame counts and
    offsets into the rotations and positions after the records), the bones' places at rest (from the parent), then
    the parts - weapons and shields (each with the bone it hangs on and its place), then the body parts (each vertex
    tied to one bone, its point given from that bone). The parts that hang on one bone (weapons, shields, crests,
    the pieces of a siege engine) keep their points from that bone too - their 7 floats are not a place in the
    model (read as one, a crest floated off the helmet and a ballista fell apart: a report). pose 't': the
    skeleton at rest, every bone unturned - the T pose, arms out (the user's wish: the same for every model);
    'frame': the file's first animation frame (how the man stands). u v over the one texture of the unit."""
    if len(data) < 60:
        raise MeshError("not a Rome model (too short)")
    root = data.find(b"Scene Root\x00")
    if root < 8:
        raise MeshError("not a Rome model (no skeleton)")
    # before the bone records: the frame count and the frame times; before those each bone's parent, and before
    # those the bone count (at byte 50, or 49 in the 3.02 files - found from the end, not the start)
    at = next((root - 8 - 4 * n for n in range(0, 5000)
               if root - 8 - 4 * n >= 0 and struct.unpack_from("<I", data, root - 8 - 4 * n)[0] == n), None)
    def fits(n):          # the count's byte just before the parents (1 or 2 bytes before), every parent earlier
        if at is None or at - 4 * n - 2 < 0 or n not in (data[at - 4 * n - 1], data[at - 4 * n - 2]):
            return False
        ps = struct.unpack_from("<%dI" % n, data, at - 4 * n)
        return all(ps[i] < i for i in range(1, n))
    nb = next((n for n in range(1, 201) if fits(n)), None)
    if not nb:
        raise MeshError("the model's bone count does not look right")
    parents = struct.unpack_from("<%dI" % nb, data, at - 4 * nb)
    p, bones = root - 4, []
    for _ in range(nb):
        s = _cas_string(data, p)
        if not s or s[1] + 20 > len(data):
            raise MeshError("the model's bones could not be read")
        bones.append(struct.unpack_from("<4I", data, s[1]))           # rotations, positions, their offsets
        p = s[1] + 20
        if not _cas_string(data, p) and data[p:p + 5] == b"\x01\x00\x00\x00\x00":
            p += 5                                                     # 3.18: 5 more bytes after each record
    base = p
    last = max(bones, key=lambda b: b[3])
    rest_at = base + last[3] + 12 * last[1]
    if rest_at + 12 * nb > len(data):
        raise MeshError("the model's skeleton could not be read")
    rest = [struct.unpack_from("<3f", data, rest_at + 12 * i) for i in range(nb)]
    rot, where = [], []
    for i, (nq, npos, qo, po) in enumerate(bones):
        q = struct.unpack_from("<4f", data, base + qo) if nq and pose == "frame" else (0.0, 0.0, 0.0, 1.0)
        t = struct.unpack_from("<3f", data, base + po) if npos else rest[i]
        if isinstance(pose, Pose) and 1 <= i <= len(pose.rotations):   # an animation's frame: bone 0 = Scene Root
            q = pose.rotations[i - 1]
            if i - 1 < len(pose.offsets):
                t = pose.offsets[i - 1]
        par = parents[i] if i and parents[i] < i else None
        if par is None:
            rot.append(q)
            where.append(t)
        else:
            off = _qrot(rot[par], t)
            where.append(tuple(where[par][k] + off[k] for k in range(3)))
            rot.append(_qmul(rot[par], q))
    positions, uvs, groups = [], [], []
    p = rest_at + 12 * nb
    while p < len(data) - 8:
        got = _cas_part(data, p, nb)
        if not got:
            p += 1
            continue
        name, bone, xf, vb, pos, tris, uv, end = got
        first = len(positions)
        for k, v in enumerate(pos):
            b = vb[k] if vb else bone                # every point from its bone (a weapon: the one it hangs on)
            o = _qrot(rot[b], v)
            positions.append(tuple(where[b][j] + o[j] for j in range(3)))
        uvs.extend(uv)
        groups.append(Group(name, "", tuple(first + t for t in tris), bool(xf)))
        p = end
    if not groups:
        raise MeshError("no parts found in the model")
    m = Mesh(groups, positions, uvs)
    m.one_texture = True
    # the texture the file itself names (textures\x.tga, from models_unit): the game's pick when the model's
    # descr_model_battle block has no texture line (the female peasants)
    for hit in re.finditer(rb"[ -~]{1,120}?\.tga\x00", data[-400:]):
        m.texture_name = hit.group()[:-1].decode("latin-1").replace("\\", "/")
        m.texture_ref = "data/models_unit/" + m.texture_name
    return m


# Medieval II's 20 animated bones (pelvis, rthigh, rlowerleg, rfoot, abs, torso, head, jaw, eyebrow, rclavical,
# rupperarm, relbow, rhand, lclavical, lupperarm, lelbow, lhand, lthigh, llowerleg, lfoot) and each one's parent;
# a mesh's bones 20 on (weapons, shield) are held by the hand each of their points names as its second bone
M2_PARENTS = (-1, 0, 1, 2, 0, 4, 5, 6, 6, 5, 9, 10, 11, 5, 13, 14, 15, 0, 17, 18)


def _world(rotations, offsets, parents=M2_PARENTS):
    """Every bone's turn and place in the model from their own turns and offsets (Medieval II's tree: a man's, or
    the skeleton's own - a horse's)."""
    rot, where = [], []
    for b, par in enumerate(parents):
        q, t = rotations[b], offsets[b]
        if par < 0:
            rot.append(q)
            where.append(t)
        else:
            o = _qrot(rot[par], t)
            where.append(tuple(where[par][k] + o[k] for k in range(3)))
            rot.append(_qmul(rot[par], q))
    return rot, where


def pose_mesh(mesh, pose, base, held=None):
    """A Medieval II mesh in an animation's frame (a Pose): each point taken from its bones' place in the base pose
    (base = (rotations, offsets): the skeleton's default animation, the pose the mesh is made in) to their place in
    the frame, by its two weights. None when the mesh has no bones or the animation another skeleton's count.
    held {weapon bone number (20 on): turn}: a weapon's own move in the hand (its skeleton's animation of the same
    name - weapon_turn), laid on it at the hand: a javelin turned point first for the throw (without it a
    skirmisher threw it blunt end first - the user). A weapon bone not in held stays as the hand holds it."""
    parents = mesh.parents or M2_PARENTS
    n = len(parents)
    if not mesh.skin or len(pose.rotations) < n or len(base[0]) < n or len(base[1]) < n:
        return None
    offsets = list(pose.offsets[:n]) + list(base[1][len(pose.offsets):n])    # bones the frame does not move
    brot, bwhere = _world(base[0], base[1], parents)
    rot, where = _world(pose.rotations, offsets, parents)
    # each bone's move from the base pose to the frame as one matrix + shift, made once (the point by point
    # quaternion turns took twice as long - the play has to be quick)
    mats = {}
    for b in range(n):
        q = _qmul(rot[b], (-brot[b][0], -brot[b][1], -brot[b][2], brot[b][3]))
        m = _qmat(q)
        bw = bwhere[b]
        mats[b] = m + tuple(where[b][k] - (m[3 * k] * bw[0] + m[3 * k + 1] * bw[1] + m[3 * k + 2] * bw[2])
                            for k in range(3))
    if _fast is not None and not getattr(mesh, "pure", False):
        held_mats = {}
        for wb, h in _weapon_pairs(mesh, n):
            if held and wb in held:
                q = _qmul(_qmul(rot[h], (-brot[h][0], -brot[h][1], -brot[h][2], brot[h][3])), held[wb])
                m3, bw = _qmat(q), bwhere[h]
                held_mats[(wb, h)] = m3 + tuple(where[h][k] - (m3[3 * k] * bw[0] + m3[3 * k + 1] * bw[1] +
                                                               m3[3 * k + 2] * bw[2]) for k in range(3))
        out = _fast.pose(mesh, n, mats, held_mats)
    else:
        out = _pose_points(mesh, n, mats, held, rot, brot, where, bwhere)
    m = Mesh(mesh.groups, out, mesh.uvs)
    m.one_texture, m.texture_ref, m.skin, m.parents = mesh.one_texture, mesh.texture_ref, mesh.skin, mesh.parents
    m.bone_names = mesh.bone_names
    m.joints, m.turns = where, rot
    return m


def _weapon_pairs(mesh, n):
    """The (weapon bone, the hand holding it) pairs of a mesh's points, found once."""
    got = getattr(mesh, "_pairs", None)
    if got is None or got[0] != n:
        got = mesh._pairs = (n, sorted({(b0, b1 if b1 < n else 0) for b0, b1, _, _ in mesh.skin if b0 >= n}))
    return got[1]


def _pose_points(mesh, n, mats, held, rot, brot, where, bwhere):
    """pose_mesh's points one by one (no NumPy)."""
    out = []
    for v, (b0, b1, w0, w1) in zip(mesh.positions, mesh.skin):
        if b0 >= n and held and b0 in held:          # a weapon with a move of its own in the hand holding it
            h = b1 if b1 < n else 0
            a = mats.get((b0, h))
            if a is None:
                q = _qmul(_qmul(rot[h], (-brot[h][0], -brot[h][1], -brot[h][2], brot[h][3])), held[b0])
                m3, bw = _qmat(q), bwhere[h]
                a = mats[(b0, h)] = m3 + tuple(where[h][k] - (m3[3 * k] * bw[0] + m3[3 * k + 1] * bw[1] +
                                                              m3[3 * k + 2] * bw[2]) for k in range(3))
            x, y, z = v
            out.append((a[0] * x + a[1] * y + a[2] * z + a[9], a[3] * x + a[4] * y + a[5] * z + a[10],
                        a[6] * x + a[7] * y + a[8] * z + a[11]))
            continue
        if b0 >= n:                                  # a weapon's or the shield's point: the hand holding it
            b0 = b1 if b1 < n else 0
        if b1 >= n:
            b1 = b0
        if w0 <= 0 and w1 <= 0:                      # no weights (a shield, a quiver): all on its bone
            w0 = 1.0
        x, y, z = v
        if w1 <= 0 or b1 == b0:
            a = mats[b0]
            out.append((a[0] * x + a[1] * y + a[2] * z + a[9], a[3] * x + a[4] * y + a[5] * z + a[10],
                        a[6] * x + a[7] * y + a[8] * z + a[11]))
            continue
        if w0 <= 0:
            w0 = 0.0
        tw = w0 + w1
        a, c = mats[b0], mats[b1]
        p, r = w0 / tw, w1 / tw
        out.append((p * (a[0] * x + a[1] * y + a[2] * z + a[9]) + r * (c[0] * x + c[1] * y + c[2] * z + c[9]),
                    p * (a[3] * x + a[4] * y + a[5] * z + a[10]) + r * (c[3] * x + c[4] * y + c[5] * z + c[10]),
                    p * (a[6] * x + a[7] * y + a[8] * z + a[11]) + r * (c[6] * x + c[7] * y + c[8] * z + c[11])))
    return out


_CACHE = {}
_BYTES = {}


def read_posed(path, pose):
    """A Rome .cas in an animation's frame (a Pose) - the file's bytes kept while it is unchanged."""
    k = os.path.normcase(os.path.abspath(path))
    stamp = os.path.getmtime(path)
    if k not in _BYTES or _BYTES[k][0] != stamp:
        with open(path, "rb") as fh:
            _BYTES[k] = (stamp, fh.read())
        while len(_BYTES) > 8:
            _BYTES.pop(next(iter(_BYTES)))
    m = read_cas(_BYTES[k][1], pose)
    m.texture_ref = read_file(path).texture_ref
    return m


def read_file(path, pose="t"):
    """read() of a file (.mesh or Rome's .cas, in that pose), kept while the file is unchanged. A .cas names its
    texture beside itself: textures/x.tga of its own folder (models_unit, models_engine, models_strat ...)."""
    key = (os.path.normcase(os.path.abspath(path)), pose)
    stamp = os.path.getmtime(path)
    if key not in _CACHE or _CACHE[key][0] != stamp:
        with open(path, "rb") as fh:
            data = fh.read()
        if path.lower().endswith(".cas"):
            m = read_cas(data, pose)
            folder = os.path.basename(os.path.dirname(path))
            if getattr(m, "texture_name", None) and folder:
                m.texture_ref = "data/%s/%s" % (folder, m.texture_name)
        else:
            m = read(data)
        _CACHE[key] = (stamp, m)
        while len(_CACHE) > 24:
            _CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key][1]


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
_SAMPLERS = {}
_COLOURS = {}
_COMBINED = {}
_RGB = {}


def _rgb(img, big=None):
    """The picture in RGB (no larger than `big` across), kept while the picture lives - the play draws the same
    textures many times a second."""
    if img is None:
        return None
    key = (id(img), big)
    got = _RGB.get(key)
    if got is None or got[0] is not img:
        out = img.convert("RGB")
        if big and max(out.size) > big:
            out = out.resize((big, big * out.size[1] // out.size[0]))
        _RGB[key] = got = (img, out)
        while len(_RGB) > 16:
            _RGB.pop(next(iter(_RGB)))
    return got[1]


def _sampler(img, side=256):
    """A fast colour lookup (u, v) -> (r, g, b) on a small copy of a texture (made once per picture)."""
    if img is None:
        return None
    got = _SAMPLERS.get(id(img))
    if got is not None and got[0] is img:
        return got[1]
    small = img.convert("RGB").resize((side, side))
    px = small.load()
    top = side - 1

    def get(u, v):
        return px[min(top, max(0, int(u * top))), int((v % 1.0) * top)]
    _SAMPLERS[id(img)] = (img, get)
    while len(_SAMPLERS) > 16:
        _SAMPLERS.pop(next(iter(_SAMPLERS)))
    return get


def _affine(src, dst):
    """Pillow AFFINE data taking output points dst to input points src (3 each), or None when flat."""
    (x0, y0), (x1, y1), (x2, y2) = dst
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(det) < 1e-9:
        return None
    out = []
    for k in range(2):
        s0, s1, s2 = src[0][k], src[1][k], src[2][k]
        a = ((s1 - s0) * (y2 - y0) - (s2 - s0) * (y1 - y0)) / det
        b = ((s2 - s0) * (x1 - x0) - (s1 - s0) * (x2 - x0)) / det
        out += [a, b, s0 - a * x0 - b * y0]
    return tuple(out)


def whole_picture(mesh):
    """True when the mesh's own parts (not its weapons) lay their u past the middle of the picture - a Medieval II
    mount: the horse takes its whole texture, not the man's half of it (a tester: horses shown half white)."""
    if mesh.one_texture or not mesh.uvs:
        return mesh.one_texture
    us = [mesh.uvs[i][0] for g in mesh.groups if not g.name.lower().startswith(WEAPON_PARTS) for i in g.tris
          if i < len(mesh.uvs)]
    return bool(us) and max(us) > 0.55


def one_picture(groups):
    """Copies of groups drawn with their uv over one picture (render: Group.one)."""
    out = []
    for g in groups:
        h = Group(g.name, g.material, g.tris, g.attachment)
        h.pic, h.one = getattr(g, "pic", 0), True
        out.append(h)
    return out


def combine(rider, rider_groups, mount, mount_groups, mount_one=None, seat=None):
    """One Mesh of a rider and his mount. seat None: standing side by side, as the files keep them (the T pose:
    the game seats the rider and bends his legs with its animations - a seat drawn here only looked wrong): their
    lowest points on one ground, the rider beside the mount's middle, a little apart. seat (x, y, z): the rider in a
    riding animation's frame, his pelvis put there (the mount's saddle in the same frame + descr_mount's
    rider_offset - seat_of). The mount's groups take pictures 2 and 3 (render's `more`); mount_one: its uv over one
    picture (a mount with no attachment texture)."""
    if seat is not None:
        dx, dy, dz = seat
    else:
        RP = [rider.positions[i] for g in rider_groups for i in g.tris] or rider.positions or [(0.0, 0.0, 0.0)]
        MP = [mount.positions[i] for g in mount_groups for i in g.tris] or mount.positions or [(0.0, 0.0, 0.0)]
        dx = max(p[0] for p in MP) - min(p[0] for p in RP) + 0.15
        dy = min(p[1] for p in MP) - min(p[1] for p in RP)
        dz = (min(p[2] for p in MP) + max(p[2] for p in MP)) / 2 - (min(p[2] for p in RP) + max(p[2] for p in RP)) / 2
    if _fast is not None:
        pos = _fast.np.concatenate([rider.arr + (dx, dy, dz), mount.arr])
    else:
        pos = [(x + dx, y + dy, z + dz) for x, y, z in rider.positions] + list(mount.positions)
    n = rider.count
    # the parts and the u v are the same at every frame of a play: made once (render keeps its colours by them)
    key = (id(rider.uvs), id(mount.uvs), tuple(id(g) for g in rider_groups), tuple(id(g) for g in mount_groups),
           n, mount.count, rider.one_texture, mount.one_texture, mount_one)
    got = _COMBINED.get(key)
    if got is None or got[0] is not rider.uvs or got[1] is not mount.uvs:
        ru = rider.uvs or [(0.0, 0.0)] * rider.count
        mu = mount.uvs or [(0.0, 0.0)] * mount.count
        groups = []
        for g in rider_groups:
            h = Group(g.name, g.material, g.tris, g.attachment)
            h.pic, h.one = 0, rider.one_texture
            groups.append(h)
        for g in mount_groups:
            h = Group(g.name, g.material, [i + n for i in g.tris], g.attachment)
            h.pic, h.one = 2, mount.one_texture if mount_one is None else mount_one
            groups.append(h)
        got = _COMBINED[key] = (rider.uvs, mount.uvs, groups, ru + mu, rider_groups, mount_groups)
        while len(_COMBINED) > 8:
            _COMBINED.pop(next(iter(_COMBINED)))
    groups = got[2]
    out = Mesh(groups, pos, got[3])
    out.texture_ref = rider.texture_ref
    return out


def assemble(pieces):
    """One Mesh put together from pieces [(mesh, groups, (dx, dy, dz), picture number, one texture)]: each piece
    moved by its offset, its groups taking that picture of render's (0 / 1: the man, 2 / 3, 4 / 5 ...: more)."""
    pos, uvs, groups = [], [], []
    for mesh, gs, (dx, dy, dz), pic, one in pieces:
        n = len(pos)
        pos.extend((x + dx, y + dy, z + dz) for x, y, z in mesh.positions)
        uvs.extend(mesh.uvs or [(0.0, 0.0)] * mesh.count)
        for g in gs:
            h = Group(g.name, g.material, [i + n for i in g.tris], g.attachment)
            h.pic, h.one = pic, one
            groups.append(h)
    out = Mesh(groups, pos, uvs)
    out.one_texture = True
    return out


def seat_of(rider, mount, rider_offset=(0.0, 0.0, 0.0)):
    """Where a posed rider goes on his posed mount (pose_mesh of both, the same animation key and frame): his
    pelvis (which the riding animations keep at nought) on the mount's saddle bone, moved by descr_mount's
    rider_offset (x, up, forward) - seen right on a mailed knight's horse (0, 0.38, 0.70): without the forward part
    he sat on its rump, without the up part sunk into it. The offset turns with the saddle (a rearing horse's back
    slopes up: an unturned offset sank him into it - the user), the rider himself is only moved, never turned with
    it (a horse falling dead turned him head down). None when either is not posed."""
    if not rider.joints or not mount.joints:
        return None
    s, p = mount.joints[0], rider.joints[0]
    o = _qrot(mount.turns[0], rider_offset) if mount.turns else tuple(rider_offset)
    return tuple(s[k] + o[k] - p[k] for k in range(3))


def chariot(crew, crew_groups, car, horse, horses, riders):
    """A Rome chariot as the game sets it: the car (picture 2) on the ground, its horses (picture 4) at the
    horse_offset places (x, z: in front of it), its crew (the man, picture 0) at the rider_offset places (x, y, z
    from the car's root) - the game's own numbers from descr_mount.txt."""
    cg = car.shown(0, True)
    wheels = [g for g in cg if "wheel" in g.name.lower()] or cg
    ground = -min(car.positions[i][1] for g in wheels for i in g.tris)
    pieces = [(car, cg, (0.0, ground, 0.0), 2, True)]
    if horse is not None:
        hg = horse.shown(0, True)
        hy = -min(horse.positions[i][1] for g in hg for i in g.tris)
        for x, z in horses:
            pieces.append((horse, hg, (x, hy, z), 4, True))
    cy = -min(crew.positions[i][1] for g in crew_groups for i in g.tris)
    for x, y, z in riders:
        pieces.append((crew, crew_groups, (x, ground + y + cy - 0.0, z), 0, crew.one_texture))
    return assemble(pieces)


def render(mesh, size=(360, 440), yaw=35.0, pitch=8.0, zoom=1.0, texture=None, attach=None, groups=None,
           quality=2, background=BACK, textured=True, more=None, fit=None):
    """The mesh drawn as a Pillow picture, turned by yaw (round the up axis) and pitch (degrees) and lit from the
    upper left. textured: the pictures laid on every triangle (a still picture); else one colour per triangle
    (quick, for turning it with the mouse). texture = the man's picture, attach = weapons and shields; a part
    without its picture is plain grey. quality 2 draws twice as big and shrinks it (smooth edges). The game's
    space is left-handed, so x is mirrored to show the man as he stands in the game. fit: the groups the view is
    sized and centred on (default the ones drawn) - two drawings of other parts then lie on each other."""
    from PIL import Image, ImageChops, ImageDraw
    groups = groups if groups is not None else mesh.shown()
    W, H = size[0] * quality, size[1] * quality
    if _fast is not None and not getattr(mesh, "pure", False):
        pics = {0: texture, 1: attach}
        pics.update(more or {})
        arr = _fast.draw(mesh, groups, fit, W, H, yaw, pitch, zoom, pics, textured, background, LIGHT, PLAIN)
        img = Image.fromarray(arr, "RGB")
        return img.reduce(quality) if quality > 1 else img      # each 2 x 2 averaged: the smooth edges
    img = Image.new("RGB", (W, H), background)
    used = sorted({i for g in groups for i in g.tris})
    if not used:
        return img.resize(size) if quality > 1 else img
    P = mesh.positions
    sized = sorted({i for g in fit for i in g.tris}) if fit else used
    lo = [min(P[i][k] for i in sized) for k in range(3)]
    hi = [max(P[i][k] for i in sized) for k in range(3)]
    c = [(lo[k] + hi[k]) / 2 for k in range(3)]
    radius = max(math.sqrt(sum((P[i][k] - c[k]) ** 2 for k in range(3))) for i in sized) or 1.0
    scale = zoom * 0.95 * min(W, H) / (2 * radius)
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    view = {}
    for i in used:
        x, y, z = c[0] - P[i][0], P[i][1] - c[1], P[i][2] - c[2]        # x mirrored: left-handed to right-handed
        x, z = x * cy + z * sy, -x * sy + z * cy                    # yaw
        y, z = y * cp - z * sp, y * sp + z * cp                    # pitch
        view[i] = (W / 2 + x * scale, H / 2 - y * scale, z)
    L = LIGHT
    ln = math.sqrt(sum(a * a for a in L))
    L = [a / ln for a in L]
    big = 512 if textured else None
    pics = {0: _rgb(texture, big), 1: _rgb(attach, big)}
    for k, im in (more or {}).items():                   # a mount's texture (2) and attachment (3)
        pics[k] = _rgb(im, big)
    getters = {k: _sampler(im) for k, im in pics.items()}
    uvs = mesh.uvs
    tris = []
    for gi, g in enumerate(groups):
        t = g.tris
        base, one = getattr(g, "pic", 0), getattr(g, "one", mesh.one_texture)
        for j in range(0, len(t) - 2, 3):
            a, b, e = view[t[j]], view[t[j + 1]], view[t[j + 2]]
            # screen y runs down, and x was mirrored: the outward side is the one turning clockwise on screen
            ux, uy, uz = b[0] - a[0], a[1] - b[1], b[2] - a[2]
            vx, vy, vz = e[0] - a[0], a[1] - e[1], e[2] - a[2]
            nx, ny, nz = -(uy * vz - uz * vy), -(uz * vx - ux * vz), -(ux * vy - uy * vx)
            if nz <= 0:                                           # facing away (the game does not draw it either)
                continue
            n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            shade = 0.32 + 0.68 * max(0.0, (nx * L[0] + ny * L[1] + nz * L[2]) / n)
            half, src = 0, None
            if uvs:
                ua, ub, uc = uvs[t[j]], uvs[t[j + 1]], uvs[t[j + 2]]
                if one:
                    src = [(q[0], q[1]) for q in (ua, ub, uc)]
                else:
                    half = 1 if (ua[0] + ub[0] + uc[0]) / 3 >= 0.5 else 0      # which of the two pictures
                    src = [(q[0] * 2 - half, q[1]) for q in (ua, ub, uc)]
                half += base
            tris.append((a[2] + b[2] + e[2], ((a[0], a[1]), (b[0], b[1]), (e[0], e[1])), shade, half, src, (gi, j)))
    tris.sort(key=lambda x: x[0])
    draw = ImageDraw.Draw(img)
    if not textured:
        # a triangle's colour from its texture does not change with the pose: worked out once per model and
        # pictures (the play draws the same man many times a second)
        key = (id(mesh.uvs), tuple(id(g) for g in groups), tuple(sorted((k, id(v)) for k, v in pics.items())))
        cache = _COLOURS.get(key)
        if cache is None or cache[0] is not mesh.uvs:
            cache = _COLOURS[key] = (mesh.uvs, {})
            while len(_COLOURS) > 8:
                _COLOURS.pop(next(iter(_COLOURS)))
        known = cache[1]
        for _, pts, shade, half, src, at in tris:
            col = known.get(at)
            if col is None:
                get = getters.get(half)
                col = PLAIN
                if get and src:
                    mu, mv = sum(q[0] for q in src) / 3, sum(q[1] for q in src) / 3
                    cols = [get(mu, mv)] + [get((mu * 2 + q[0]) / 3, (mv * 2 + q[1]) / 3) for q in src]
                    col = tuple(sum(cc[k] for cc in cols) // 4 for k in range(3))
                known[at] = col
            col = (min(255, int(col[0] * shade)), min(255, int(col[1] * shade)), min(255, int(col[2] * shade)))
            draw.polygon(pts, fill=col, outline=col)
    else:
        light = Image.new("L", (W, H), 255)
        ldraw = ImageDraw.Draw(light)
        for _, pts, shade, half, src, _at in tris:
            pic = pics.get(half)
            x0, y0 = int(min(p[0] for p in pts)), int(min(p[1] for p in pts))
            x1, y1 = int(max(p[0] for p in pts)) + 2, int(max(p[1] for p in pts)) + 2
            data = None
            if pic is not None and src:
                pw, ph = pic.size
                data = _affine([(q[0] * pw, q[1] * ph) for q in src], [(p[0] - x0, p[1] - y0) for p in pts])
            if data is None:
                draw.polygon(pts, fill=PLAIN if pic is None or not src else getters[half](
                    sum(q[0] for q in src) / 3, sum(q[1] for q in src) / 3), outline=None)
            else:
                patch = pic.transform((x1 - x0, y1 - y0), Image.AFFINE, data, resample=Image.BILINEAR)
                mask = Image.new("L", (x1 - x0, y1 - y0), 0)
                ImageDraw.Draw(mask).polygon([(p[0] - x0, p[1] - y0) for p in pts], fill=255, outline=255)
                img.paste(patch, (x0, y0), mask)
            ldraw.polygon(pts, fill=int(255 * shade), outline=int(255 * shade))
        img = ImageChops.multiply(img, Image.merge("RGB", (light,) * 3))
        if background != (0, 0, 0):
            bg = Image.new("RGB", (W, H), background)
            cover = Image.new("L", (W, H), 0)
            cdraw = ImageDraw.Draw(cover)
            for _, pts, *_ in tris:
                cdraw.polygon(pts, fill=255, outline=255)
            img = Image.composite(img, bg, cover)
    if quality > 1:
        img = img.resize(size, Image.LANCZOS)
    return img


def on_disk(mod, rel):
    """(data-relative path, absolute path) of a model file: the mod's, else the game's own data folder (a mod
    folder keeps only what it changes), or None."""
    import types
    from .packs import _on_disk
    from .campaignrules import game_data
    if not rel:
        return None
    got = _on_disk(mod, rel)
    base = None if got else game_data(mod)
    return got or (_on_disk(types.SimpleNamespace(data=base), rel) if base else None)


def mesh_path(mod, rel):
    """The mesh file on disk (the mod's, else the game's), or None."""
    got = on_disk(mod, rel)
    return got[1] if got else None
