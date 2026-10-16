"""Files the games and mods keep packed in data/packs - read the way the engines read them (facts from the engine
source's docs/pack_formats.md and io/pack_archive.cpp, no code copied):

- Medieval II's and REX's / M2EX's '.pack' version 3: a header ('PACK', version 0x00030000, files, name table bytes,
  chunks), each file's place in the name table, a size for every 64 KB chunk, then the name table (offset, first
  chunk, size, stored size, name); a chunk is LZO1X compressed, or stored as it is when its stored size is 64 KB
  (the file's last chunk: its own size);
- '.pack' version 4 (REX / M2EX's own, for packs over 4 GB): the same header with flags 0, the places, then the
  records (64-bit offset, size, stored size, codec 0 stored / 2 zstd, name) - one zstd frame a file;
- Rome's '.pak' ('PAK0'): wide names, each file's end offset, the files as they are.
Names are folded as the engines fold them: lower case, '/'.

A pack is read only to take one file out - into a folder of the system's temporary files, kept for the next time
(the same pack, the same date: the same copy)."""

import ctypes
import ctypes.util
import os
import struct
import tempfile
import zlib

CHUNK = 1 << 16
V3, V4 = 0x00030000, 0x00040000

_index = {}                                       # pack path -> (mtime, {name: entry})


def lzo1x_decompress(src, size):
    """LZO1X data (as minilzo's lzo1x_decompress_safe reads it) -> size bytes."""
    out = bytearray()
    ip = 0

    def copy_match(dist, length):
        start = len(out) - dist
        if start < 0:
            raise ValueError("LZO: a match before the start")
        if dist >= length:
            out.extend(out[start:start + length])
        else:
            for k in range(length):
                out.append(out[start + k])

    state = "loop"
    t = 0
    if src[0] > 17:
        t = src[0] - 17
        ip = 1
        out.extend(src[ip:ip + t])
        ip += t
        state = "first" if t >= 4 else "match_read"
    while True:
        if state == "loop":
            t = src[ip]
            ip += 1
            if t >= 16:
                state = "match"
                continue
            if t == 0:
                while src[ip] == 0:
                    t += 255
                    ip += 1
                t += 15 + src[ip]
                ip += 1
            out.extend(src[ip:ip + t + 3])
            ip += t + 3
            state = "first"
            continue
        if state == "first":                      # a literal run just ended: a short far match may follow
            t = src[ip]
            ip += 1
            if t >= 16:
                state = "match"
                continue
            dist = 1 + 0x0800 + (t >> 2) + (src[ip] << 2)
            ip += 1
            copy_match(dist, 3)
            state = "done"
            continue
        if state == "match_read":
            t = src[ip]
            ip += 1
            state = "match"
            continue
        if state == "match":
            if t >= 64:
                dist = 1 + ((t >> 2) & 7) + (src[ip] << 3)
                ip += 1
                copy_match(dist, (t >> 5) + 1)
            elif t >= 32:
                t &= 31
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 31 + src[ip]
                    ip += 1
                dist = 1 + (src[ip] >> 2) + (src[ip + 1] << 6)
                ip += 2
                copy_match(dist, t + 2)
            elif t >= 16:
                far = (t & 8) << 11
                t &= 7
                if t == 0:
                    while src[ip] == 0:
                        t += 255
                        ip += 1
                    t += 7 + src[ip]
                    ip += 1
                dist = far + (src[ip] >> 2) + (src[ip + 1] << 6)
                ip += 2
                if dist == 0:                     # the end mark
                    break
                copy_match(dist + 0x4000, t + 2)
            else:
                dist = 1 + (t >> 2) + (src[ip] << 2)
                ip += 1
                copy_match(dist, 2)
            state = "done"
            continue
        if state == "done":                       # the last two bits of the match: 0-3 literals before the next
            t = src[ip - 2] & 3
            if t == 0:
                state = "loop"
                continue
            out.extend(src[ip:ip + t])
            ip += t
            state = "match_read"
            continue
    if len(out) != size:
        raise ValueError("LZO: %d bytes made, %d expected" % (len(out), size))
    return bytes(out)


def _zstd_lib():
    for name in ("zstd", "libzstd"):
        found = ctypes.util.find_library(name)
        if found:
            try:
                lib = ctypes.CDLL(found)
                lib.ZSTD_decompress.restype = ctypes.c_size_t
                lib.ZSTD_decompress.argtypes = (ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t)
                lib.ZSTD_isError.restype = ctypes.c_uint
                lib.ZSTD_isError.argtypes = (ctypes.c_size_t,)
                return lib
            except (OSError, AttributeError):
                continue
    return None


def zstd_decompress(frame, size):
    """One zstd frame -> size bytes: Python's own zstd (3.14), the zstandard package (the exe has it), or the
    system's libzstd; ValueError when none is there."""
    try:
        from compression import zstd
        return zstd.decompress(frame)
    except ImportError:
        pass
    try:
        import zstandard
        return zstandard.ZstdDecompressor().decompress(frame, max_output_size=size)
    except ImportError:
        pass
    lib = _zstd_lib()
    if lib is None:
        raise ValueError("no zstd here to open this pack (version 4)")
    buf = ctypes.create_string_buffer(max(size, 1))
    got = lib.ZSTD_decompress(buf, size, frame, len(frame))
    if lib.ZSTD_isError(got) or got != size:
        raise ValueError("zstd: the file did not unpack")
    return buf.raw[:size]


def fold(name):
    return name.replace("\\", "/").lower()


def read_index(path):
    """{folded name: entry} of a .pack / .pak (cached while the file stays the same); {} when it is none."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    got = _index.get(path)
    if got and got[0] == mtime:
        return got[1]
    out = {}
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            if magic == b"PACK":
                out = _pack_index(f, path)
            elif magic == b"PAK0":
                out = _pak_index(f)
    except (OSError, struct.error, ValueError):
        out = {}
    _index[path] = (mtime, out)
    return out


def _pack_index(f, path):
    version, files, names_size, chunks = struct.unpack("<4I", f.read(16))
    if version not in (V3, V4) or (version == V4 and chunks):
        return {}
    places = struct.unpack("<%dI" % files, f.read(4 * files))
    sizes = struct.unpack("<%dI" % chunks, f.read(4 * chunks)) if version == V3 else ()
    table = f.read(names_size)
    fixed = 17 if version == V4 else 16
    out = {}
    for off in places:
        end = table.index(b"\0", off + fixed)
        name = fold(table[off + fixed:end].decode("latin-1"))
        if version == V4:
            data, size, stored, codec = struct.unpack_from("<QIIB", table, off)
            out[name] = ("v4", data, size, stored, codec)
        else:
            data, first, size, stored = struct.unpack_from("<4I", table, off)
            n = (size - 1) // CHUNK + 1 if size else 0
            out[name] = ("v3", data, size, stored, sizes[first:first + n])
    return out


def _pak_index(f):
    blob_len, count = struct.unpack("<2I", f.read(8))
    names = f.read(blob_len * 2).decode("utf-16-le").split("\0")[:count]
    ends = struct.unpack("<%dI" % count, f.read(4 * count))
    start = 12 + blob_len * 2 + 4 * count
    out = {}
    for name, end in zip(names, ends):
        out[fold(name)] = ("pak", start, end - start)
        start = end
    return out


def read_file(path, entry):
    """The bytes of one file of a pack (an entry of read_index)."""
    with open(path, "rb") as f:
        f.seek(entry[1])
        if entry[0] == "pak":
            return f.read(entry[2])
        if entry[0] == "v4":
            _, _, size, stored, codec = entry
            raw = f.read(stored)
            if codec == 0:
                return raw
            if codec == 2:
                return zstd_decompress(raw, size)
            raise ValueError("unknown codec %d" % codec)
        _, _, size, _, comp = entry
        out, left = [], size
        for c in comp:
            want = min(left, CHUNK)
            raw = f.read(c)
            out.append(raw if c == want else lzo1x_decompress(raw, want))
            left -= want
        return b"".join(out)


def packs(roots):
    """Every .pack / .pak the game reads beside these data folders (the mod's first): data/packs (REX / M2EX mods)
    and packs beside data (Medieval II's own <game>/packs), each folder's in name order."""
    out = []
    for root in roots:
        for base in (root, os.path.dirname(os.path.abspath(root))):
            folder = next((os.path.join(base, d) for d in ("packs", "Packs", "PACKS")
                           if os.path.isdir(os.path.join(base, d))), None)
            if folder:
                out += [os.path.join(folder, n) for n in sorted(os.listdir(folder))
                        if n.lower().endswith((".pack", ".pak")) and os.path.join(folder, n) not in out]
    return out


def unpacked(roots, rel):
    """A file under data/ taken out of the packs into the temporary folder (once): its path, or None when no pack
    holds it (or it does not open)."""
    key = fold(rel).lstrip("/")
    if key.startswith("data/"):
        key = key[5:]
    for pack in packs(roots):
        index = read_index(pack)
        entry = index.get(key) or index.get("data/" + key)
        if entry is None:
            continue
        tag = "%08x" % (zlib.crc32(("%s|%s" % (pack, os.path.getmtime(pack))).encode("utf-8")) & 0xffffffff)
        dest = os.path.join(tempfile.gettempdir(), "campaign_editor_packs", tag, *key.split("/"))
        if os.path.isfile(dest):
            return dest
        try:
            data = read_file(pack, entry)
        except (OSError, ValueError, IndexError, struct.error):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest + ".part", "wb") as f:
            f.write(data)
        os.replace(dest + ".part", dest)
        return dest
    return None


__all__ = ["lzo1x_decompress", "zstd_decompress", "read_index", "read_file", "packs", "unpacked", "fold"]
