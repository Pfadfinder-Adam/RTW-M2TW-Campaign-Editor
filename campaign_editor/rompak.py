"""Rome's data/packs/*.pak, read (never written): the game keeps many pictures only there - unit textures
(models_unit_textures.pak), ui pictures, sprites. A file the tool looks for that is not loose on disk is taken
from the packs of the mod's or the game's data folder.

    'PAK0', u32 length of the name table in UTF-16 characters, u32 count; the names (UTF-16LE, upper case,
    'DATA\\MODELS_UNIT\\TEXTURES\\X.TGA.DDS', each ended by \\0); u32 END offset of each entry; then the files,
    stored raw one after another, the first right after the offsets.

Checked on all 9 vanilla paks (to the last byte). Medieval II's .pack files (lzo / zstd) are not read here."""

import os
import struct

_index = {}


def read_index(path):
    """{name lower with / : (offset, size)} of a .pak; {} when it is not one. Cached by the file's time."""
    try:
        key = (path, os.path.getmtime(path))
    except OSError:
        return {}
    if key in _index:
        return _index[key]
    out = {}
    with open(path, "rb") as fh:
        head = fh.read(12)
        if len(head) == 12 and head[:4] == b"PAK0":
            chars, count = struct.unpack_from("<II", head, 4)
            names = fh.read(chars * 2).decode("utf-16-le", "replace").split("\0")[:count]
            ends = struct.unpack("<%dI" % count, fh.read(4 * count))
            start = 12 + chars * 2 + 4 * count
            for name, end in zip(names, ends):
                out[name.replace("\\", "/").lower()] = (start, end - start)
                start = end
    _index[key] = out
    return out


def _paks(mod):
    from .campaignrules import game_data
    seen, out = set(), []
    for data in (mod.data, game_data(mod)):
        if not data:
            continue
        folder = os.path.join(data, "packs")
        if os.path.isdir(folder) and os.path.normcase(folder) not in seen:
            seen.add(os.path.normcase(folder))
            out += [os.path.join(folder, n) for n in sorted(os.listdir(folder)) if n.lower().endswith(".pak")]
    return out


def has(mod, rel):
    """Whether data/<rel> (or <rel>.dds) is in one of the packs - without reading it."""
    rel = rel.replace("\\", "/").lower()
    rel = rel[5:] if rel.startswith("data/") else rel
    return any(("data/" + rel) in idx or ("data/" + rel + ".dds") in idx
               for idx in (read_index(p) for p in _paks(mod)))


def find(mod, rel):
    """The bytes of data/<rel> from a pack (rel like 'models_unit/textures/x.tga'; x.tga.dds is found too), or
    None."""
    rel = rel.replace("\\", "/").lower()
    rel = rel[5:] if rel.startswith("data/") else rel
    for pak in _paks(mod):
        idx = read_index(pak)
        for cand in ("data/" + rel, "data/" + rel + ".dds"):
            got = idx.get(cand)
            if got:
                with open(pak, "rb") as fh:
                    fh.seek(got[0])
                    return fh.read(got[1])
    return None
