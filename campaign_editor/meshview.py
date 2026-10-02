"""Medieval II battle models (.mesh) read and drawn in 3D for the Unit editor - with Pillow alone.

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

HEADER = b"serialization::archive"
KNOWN = {0, 1, 2, 3, 4, 10, 11}                     # stream kinds seen in the vanilla meshes
SIZES = {0: (12,), 1: (8,), 4: (8,), 2: (4,), 3: (4, 12), 10: (4, 12), 11: (4, 12)}
POS, UV, NORMAL = 0, 4, 3
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
        self.groups, self.positions, self.uvs = groups, positions, uvs
        self.count = len(positions)
        self.one_texture = False
        self.texture_ref = None

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


def _groups(d):
    out = []
    p, window, attach = 32, 240, False
    while p < len(d):
        found = None
        for q in range(p, min(p + window, len(d))):
            a = _string(d, q)
            b = a and _string(d, a[1])
            if not b:
                continue
            best = None
            for skip in (0, 2):                     # 2 bytes of class info after the first part's material
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
    return Mesh(groups, pos, uvs)


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


def read_cas(data):
    """A Mesh from a Rome .cas file's bytes (worked out on the 807 vanilla unit, mount and animal models, versions
    2.22 to 3.2 in the first 4 bytes as a float). The file: a header (the bone count, then each bone's parent),
    the animation's frame count and times, one record per bone ('Scene Root', bone_pelvis ... - frame counts and
    offsets into the rotations and positions after the records), the bones' places at rest (from the parent), then
    the parts - weapons and shields (each with the bone it hangs on and its place), then the body parts (each vertex
    tied to one bone, its point given from that bone). The model is put together in the first frame's pose (the
    arms out, as the files keep it); u v over the one texture of the unit."""
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
        q = struct.unpack_from("<4f", data, base + qo) if nq else (0.0, 0.0, 0.0, 1.0)
        t = struct.unpack_from("<3f", data, base + po) if npos else rest[i]
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
            if xf:                                  # a weapon / shield: its own place in the model
                o = _qrot(xf[:4], v)
                positions.append((o[0] + xf[4], o[1] + xf[5], o[2] + xf[6]))
            else:
                b = vb[k] if vb else bone
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
        m.texture_ref = "data/models_unit/" + hit.group()[:-1].decode("latin-1").replace("\\", "/")
    return m


_CACHE = {}


def read_file(path):
    """read() of a file (.mesh or Rome's .cas), kept while the file is unchanged."""
    key = os.path.normcase(os.path.abspath(path))
    stamp = os.path.getmtime(path)
    if key not in _CACHE or _CACHE[key][0] != stamp:
        with open(path, "rb") as fh:
            data = fh.read()
        _CACHE[key] = (stamp, read_cas(data) if path.lower().endswith(".cas") else read(data))
        while len(_CACHE) > 24:
            _CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key][1]


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
def _sampler(img, side=256):
    """A fast colour lookup (u, v) -> (r, g, b) on a small copy of a texture."""
    if img is None:
        return None
    small = img.convert("RGB").resize((side, side))
    px = small.load()
    top = side - 1

    def get(u, v):
        return px[min(top, max(0, int(u * top))), int((v % 1.0) * top)]
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


def combine(rider, rider_groups, mount, mount_groups, mount_one=None):
    """One Mesh of a rider and his mount standing side by side, as the files keep them (two models, both standing:
    the game seats the rider and bends his legs with its animations - a seat drawn here only looked wrong): their
    lowest points on one ground, the rider beside the mount's middle, a little apart. The mount's groups take
    pictures 2 and 3 (render's `more`); mount_one: its uv over one picture (a mount with no attachment texture)."""
    RP = [rider.positions[i] for g in rider_groups for i in g.tris] or rider.positions or [(0.0, 0.0, 0.0)]
    MP = [mount.positions[i] for g in mount_groups for i in g.tris] or mount.positions or [(0.0, 0.0, 0.0)]
    dx = max(p[0] for p in MP) - min(p[0] for p in RP) + 0.15
    dy = min(p[1] for p in MP) - min(p[1] for p in RP)
    dz = (min(p[2] for p in MP) + max(p[2] for p in MP)) / 2 - (min(p[2] for p in RP) + max(p[2] for p in RP)) / 2
    pos = [(x + dx, y + dy, z + dz) for x, y, z in rider.positions] + list(mount.positions)
    n = rider.count
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
    out = Mesh(groups, pos, ru + mu)
    out.texture_ref = rider.texture_ref
    return out


def render(mesh, size=(360, 440), yaw=35.0, pitch=8.0, zoom=1.0, texture=None, attach=None, groups=None,
           quality=2, background=BACK, textured=True, more=None):
    """The mesh drawn as a Pillow picture, turned by yaw (round the up axis) and pitch (degrees) and lit from the
    upper left. textured: the pictures laid on every triangle (a still picture); else one colour per triangle
    (quick, for turning it with the mouse). texture = the man's picture, attach = weapons and shields; a part
    without its picture is plain grey. quality 2 draws twice as big and shrinks it (smooth edges). The game's
    space is left-handed, so x is mirrored to show the man as he stands in the game."""
    from PIL import Image, ImageChops, ImageDraw
    groups = groups if groups is not None else mesh.shown()
    W, H = size[0] * quality, size[1] * quality
    img = Image.new("RGB", (W, H), background)
    used = sorted({i for g in groups for i in g.tris})
    if not used:
        return img.resize(size) if quality > 1 else img
    P = mesh.positions
    lo = [min(P[i][k] for i in used) for k in range(3)]
    hi = [max(P[i][k] for i in used) for k in range(3)]
    c = [(lo[k] + hi[k]) / 2 for k in range(3)]
    radius = max(math.sqrt(sum((P[i][k] - c[k]) ** 2 for k in range(3))) for i in used) or 1.0
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
    pics = {0: texture.convert("RGB") if texture is not None else None,
            1: attach.convert("RGB") if attach is not None else None}
    for k, im in (more or {}).items():                   # a mount's texture (2) and attachment (3)
        pics[k] = im.convert("RGB") if im is not None else None
    if textured:
        for k, im in pics.items():
            if im is not None and max(im.size) > 512:
                pics[k] = im.resize((512, 512 * im.size[1] // im.size[0]))
    getters = {k: _sampler(im) for k, im in pics.items()}
    uvs = mesh.uvs
    tris = []
    for g in groups:
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
            tris.append((a[2] + b[2] + e[2], ((a[0], a[1]), (b[0], b[1]), (e[0], e[1])), shade, half, src))
    tris.sort(key=lambda x: x[0])
    draw = ImageDraw.Draw(img)
    if not textured:
        for _, pts, shade, half, src in tris:
            get = getters[half]
            col = PLAIN
            if get and src:
                mu, mv = sum(q[0] for q in src) / 3, sum(q[1] for q in src) / 3
                cols = [get(mu, mv)] + [get((mu * 2 + q[0]) / 3, (mv * 2 + q[1]) / 3) for q in src]
                col = tuple(sum(cc[k] for cc in cols) // 4 for k in range(3))
            col = tuple(min(255, int(v * shade)) for v in col)
            draw.polygon(pts, fill=col, outline=col)
    else:
        light = Image.new("L", (W, H), 255)
        ldraw = ImageDraw.Draw(light)
        for _, pts, shade, half, src in tris:
            pic = pics[half]
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
