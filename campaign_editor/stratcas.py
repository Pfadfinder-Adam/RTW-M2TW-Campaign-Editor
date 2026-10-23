"""The campaign map's own .cas models (tile models: hills, mountains, rivers, cliffs, volcanoes; later towns and
trees) read the way the engines read them - chunk by chunk (facts from the engine source's cas_loader, editor-notes
strat_tile_models.md section 6; no code copied). meshview.read_cas reads the battle men by guessing their layout;
these files are plainer and carry what the battle reader never needed: untextured parts with vertex colours (the
hills), several materials named per part (cliffs: dummy.tga + cliff.tga).

The file: a float version, then chunks - each a u32 size (counted from its own first byte) and a class id: 1 RIGID
(the parts), 5 MATERIAL (the texture names), the rest skipped. A RIGID part: its name, (3.03 on) a properties text,
(3.01 on) a group name, the node, (2.24 on) a turn and a place (28 bytes, not used for tile models), vertex and
face counts, two flags (textured, vertex colours), positions, normals, faces, (2.22 on) its material, the u v when
textured, the colours (r g b, 3.02 on also a), then (2.11 on) one byte (before 3.17) or a counted list of ints."""

import struct


class Part:
    def __init__(self, name, positions, normals, faces, uvs, colours, material):
        self.name, self.positions, self.normals, self.faces = name, positions, normals, faces
        self.uvs, self.colours, self.material = uvs, colours, material
        self.texture = None                       # the material's first texture name, set once the file is read
        self.image = None                         # its picture's TGA bytes when the file keeps it inside (wool)


class CasError(ValueError):
    pass


def _name(d, p):
    n = struct.unpack_from("<i", d, p)[0]
    if not 0 <= n < 4096 or p + 4 + n > len(d):
        raise CasError("a name out of the file")
    return d[p + 4:p + 4 + n].split(b"\0", 1)[0].decode("latin-1"), p + 4 + n


def _rigid(d, p, end, ver):
    count = struct.unpack_from("<i", d, p)[0]
    p += 4
    parts = []
    for _ in range(max(0, count)):
        name, p = _name(d, p)
        if ver >= 3.03:
            _, p = _name(d, p)                    # properties text
        if ver >= 3.01:
            _, p = _name(d, p)                    # group
        p += 4                                    # node
        if ver >= 2.24:
            p += 28
        nv, nf, textured, coloured = struct.unpack_from("<HHBB", d, p)
        p += 6
        pos = struct.unpack_from("<%df" % (3 * nv), d, p)
        p += 12 * nv
        nor = struct.unpack_from("<%df" % (3 * nv), d, p)
        p += 12 * nv
        faces = struct.unpack_from("<%dH" % (3 * nf), d, p)
        p += 6 * nf
        mat = -1
        if ver >= 2.22:
            mat = struct.unpack_from("<i", d, p)[0]
            p += 4
        uvs = None
        if textured:
            uvs = struct.unpack_from("<%df" % (2 * nv), d, p)
            p += 8 * nv
        cols = None
        if coloured:
            k = 4 if ver >= 3.02 else 3
            cols = d[p:p + k * nv]
            if k == 3:                            # always r g b a
                cols = bytes(b for i in range(nv) for b in cols[3 * i:3 * i + 3] + b"\xff")
            p += k * nv
        if ver >= 2.11:
            if ver < 3.17:
                p += 1
            else:
                n = struct.unpack_from("<i", d, p)[0]
                p += 4 + 4 * max(0, n)
        if p > end:
            raise CasError("part %s runs past its chunk" % name)
        if name != "CaozSceneCustomAttribNode":
            parts.append(Part(name, pos, nor, faces, uvs, cols, mat))
    return parts


def _tga_length(d, p):
    """The length of a TGA picture starting at d[p] (a texture a .cas file keeps inside it, right after its name -
    the engine reads it there, cas_material_data: 'TGA stored in CAS file'): the header, its id, colour map and the
    pixels - plain (types 1-3) or run-length packed (9-11, walked packet by packet)."""
    id_len, cmap_type, img_type = d[p], d[p + 1], d[p + 2]
    cmap_len, cmap_bits = struct.unpack_from("<H", d, p + 5)[0], d[p + 7]
    w, h = struct.unpack_from("<HH", d, p + 12)
    step = (d[p + 16] + 7) // 8
    q = p + 18 + id_len + (cmap_len * ((cmap_bits + 7) // 8) if cmap_type else 0)
    if img_type in (1, 2, 3):
        q += w * h * step
    elif img_type in (9, 10, 11):
        left = w * h
        while left > 0:
            head = d[q]
            n = (head & 0x7F) + 1
            q += 1 + (step if head & 0x80 else n * step)
            left -= n
    else:
        raise CasError("a picture inside the file of a kind this reader does not know (TGA type %d)" % img_type)
    if q > len(d):
        raise CasError("a picture inside the file runs past its end")
    return q - p


def _materials(d, p):
    """[[(texture name, TGA bytes kept inside the file or None)]] of each material."""
    count = struct.unpack_from("<i", d, p)[0]
    p += 4
    out = []
    for _ in range(max(0, count)):
        nt = struct.unpack_from("<i", d, p)[0]
        p += 4
        if nt > 1:
            p += 8
        names = []
        for _ in range(max(0, nt)):
            if nt > 1:
                p += 4
            embedded = d[p]
            p += 1
            e = d.index(b"\0", p)
            name = d[p:e].decode("latin-1")
            p = e + 1
            image = None
            if embedded:                          # vanilla Medieval II's resource_wool.cas (report #419: white)
                n = _tga_length(d, p)
                image, p = bytes(d[p:p + n]), p + n
            names.append((name, image))
        p += 4 + 13 * 4 + 1
        out.append(names)
    return out


def read(data):
    """[Part] of a campaign-map .cas file's bytes; CasError when it is not one this reader knows."""
    if len(data) < 12:
        raise CasError("too short for a .cas file")
    ver = round(struct.unpack_from("<f", data, 0)[0], 2)
    if not 2.16 <= ver < 10:
        raise CasError("not a .cas file of a version this reader knows (%s)" % ver)
    p, parts, mats = 4, [], []
    try:
        while p + 8 <= len(data):
            size, cid = struct.unpack_from("<Ii", data, p)
            if size < 8 or p + size > len(data):
                break
            if cid == 1:
                parts += _rigid(data, p + 8, p + size, ver)
            elif cid == 5:
                mats = _materials(data, p + 8)
            p += size
    except (struct.error, ValueError, IndexError) as e:
        raise CasError(str(e)) from e
    for part in parts:
        if 0 <= part.material < len(mats) and mats[part.material]:
            name, part.image = mats[part.material][0]
            part.texture = name.replace("\\", "/").rsplit("/", 1)[-1]
    if not parts:
        raise CasError("no parts in the file")
    return parts


__all__ = ["read", "Part", "CasError"]
