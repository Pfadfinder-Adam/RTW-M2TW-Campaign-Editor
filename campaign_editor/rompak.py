"""Rome's data/packs/*.pak, read (never written): the game keeps many pictures only there - unit textures
(models_unit_textures.pak), ui pictures, sprites. A file the tool looks for that is not loose on disk is taken
from the packs of the mod's or the game's data folder.

    'PAK0', u32 length of the name table in UTF-16 characters, u32 count; the names (UTF-16LE, upper case,
    'DATA\\MODELS_UNIT\\TEXTURES\\X.TGA.DDS', each ended by \\0); u32 END offset of each entry; then the files,
    stored raw one after another, the first right after the offsets.

Checked on all 9 vanilla paks (to the last byte). The reading itself (and Medieval II's / REX's .pack, lzo / zstd)
lives in gamepacks - one place for every pack."""

from .gamepacks import fold, read_file
from .gamepacks import packs as _packs
from .gamepacks import read_index


def _paks(mod):
    from .campaignrules import game_data
    roots = [mod.data] + [d for d in (game_data(mod),) if d]
    return _packs(roots)


def has(mod, rel):
    """Whether data/<rel> (or <rel>.dds) is in one of the packs - without reading it."""
    rel = fold(rel)
    rel = rel[5:] if rel.startswith("data/") else rel
    return any(("data/" + rel) in idx or ("data/" + rel + ".dds") in idx
               for idx in (read_index(p) for p in _paks(mod)))


def find(mod, rel):
    """The bytes of data/<rel> from a pack (rel like 'models_unit/textures/x.tga'; x.tga.dds is found too), or
    None."""
    rel = fold(rel)
    rel = rel[5:] if rel.startswith("data/") else rel
    for pak in _paks(mod):
        idx = read_index(pak)
        for cand in ("data/" + rel, "data/" + rel + ".dds"):
            got = idx.get(cand)
            if got:
                try:
                    return read_file(pak, got)
                except (OSError, ValueError, IndexError):
                    return None
    return None


__all__ = ["read_index", "has", "find"]
