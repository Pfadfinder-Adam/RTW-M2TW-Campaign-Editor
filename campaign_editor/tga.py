"""A minimal TGA reader (no dependencies) for map_regions.tga.

Supports true-colour images, uncompressed (type 2) and RLE (type 10), 24 or 32
bits. Pixels are returned bottom-up, which is the campaign map's own
orientation: pixel (x, y) here is tile (x, y) in descr_strat.txt.
"""

import struct


class Image:
    """A picture's pixels as bytes, 3 per pixel (r, g, b), bottom row first - 3 bytes a pixel instead of a
    Python tuple each (a 4080 x 2496 map's 2x+1 files took gigabytes as lists)."""

    def __init__(self, width, height, pixels=None, raw=None):
        self.width = width
        self.height = height
        if raw is None:
            raw = bytearray(width * height * 3)
            if pixels is not None:
                for i, p in enumerate(pixels):
                    raw[3 * i:3 * i + 3] = bytes(p[:3])
        self.raw = raw

    def get(self, x, y):
        o = (y * self.width + x) * 3
        r = self.raw
        return (r[o], r[o + 1], r[o + 2])

    def set(self, x, y, colour):
        o = (y * self.width + x) * 3
        self.raw[o:o + 3] = bytes(colour[:3])

    @property
    def pixels(self):
        """The pixels as a sequence of (r, g, b), row-major, bottom row first (made on the fly)."""
        return _Pixels(self)

    def find(self, colour):
        """(x, y) of every pixel of this colour, bottom row first."""
        key, raw, w = bytes(colour[:3]), self.raw, self.width
        i = raw.find(key)
        while i >= 0:
            if i % 3 == 0:
                n = i // 3
                yield n % w, n // w
                i = raw.find(key, i + 3)
            else:
                i = raw.find(key, i + 1)

    def colours(self):
        """The set of colours the picture has."""
        r = self.raw
        return set(zip(r[0::3], r[1::3], r[2::3]))

    def rgb_top_down(self):
        """The pixels as RGB bytes, top row first (what Pillow's frombytes takes)."""
        row = self.width * 3
        r = self.raw
        return b"".join(bytes(r[y * row:(y + 1) * row]) for y in range(self.height - 1, -1, -1))


class _Pixels:
    def __init__(self, img):
        self.img = img

    def __len__(self):
        return self.img.width * self.img.height

    def __getitem__(self, i):
        if i < 0:
            i += len(self)
        r = self.img.raw
        return (r[3 * i], r[3 * i + 1], r[3 * i + 2])

    def __setitem__(self, i, colour):
        self.img.raw[3 * i:3 * i + 3] = bytes(colour[:3])

    def __iter__(self):
        r = self.img.raw
        return zip(r[0::3], r[1::3], r[2::3])


def read_tga(path):
    with open(path, "rb") as f:
        data = f.read()
    return read_tga_bytes(data, path)


def _decode(data, path="(picture)"):
    """(width, height, bytes per pixel, top_down, image type, the pixel bytes as stored - B G R [A], RLE undone)."""
    id_len, cmap_type, img_type = data[0], data[1], data[2]
    width, height = struct.unpack_from("<HH", data, 12)
    bpp, desc = data[16], data[17]
    if img_type in (1, 9) and cmap_type == 1 and bpp == 8:
        return _decode_palette(data, path)
    if img_type not in (2, 10) or bpp not in (24, 32) or cmap_type != 0:
        raise ValueError("%s: unsupported TGA (type %d, %d bpp)" % (path, img_type, bpp))
    step = bpp // 8
    pos = 18 + id_len
    count = width * height
    if img_type == 2:
        out = bytearray(data[pos:pos + count * step])
    else:
        out = bytearray(count * step)
        o = 0
        total = count * step
        while o < total:
            head = data[pos]
            pos += 1
            n = (head & 0x7F) + 1
            if head & 0x80:
                px = data[pos:pos + step]
                pos += step
                out[o:o + n * step] = px * n
            else:
                out[o:o + n * step] = data[pos:pos + n * step]
                pos += n * step
            o += n * step
    return width, height, step, bool(desc & 0x20), img_type, out


def _decode_palette(data, path):
    """A colour-mapped TGA (type 1, or 9 run-length; 8-bit indexes into a 15/16/24/32-bit colour map) as _decode gives
    a true-colour one: B G R [A] per pixel (3 bytes, 4 when the colour map has alpha). Some mod tools write the map
    pictures this way (a map generator's map_regions / map_features / map_ground_types - the editor could not open
    them)."""
    id_len, img_type = data[0], data[2]
    first, length, entry = struct.unpack_from("<HHB", data, 3)
    width, height = struct.unpack_from("<HH", data, 12)
    desc = data[17]
    pos = 18 + id_len
    size = (entry + 7) // 8
    table = []
    for i in range(length):
        e = data[pos + i * size:pos + (i + 1) * size]
        if size == 2:                               # 15 / 16 bit: A RRRRR GGGGG BBBBB
            v = e[0] | (e[1] << 8)
            r, g, b = (v >> 10) & 31, (v >> 5) & 31, v & 31
            table.append(bytes(((b << 3) | (b >> 2), (g << 3) | (g >> 2), (r << 3) | (r >> 2))))
        else:
            table.append(bytes(e[:4] if size == 4 else e[:3]))
    step = 4 if size == 4 else 3
    pos += length * size
    count = width * height
    if img_type == 1:
        idx = data[pos:pos + count]
    else:
        idx = bytearray()
        while len(idx) < count:
            head = data[pos]
            pos += 1
            n = (head & 0x7F) + 1
            if head & 0x80:
                idx += bytes((data[pos],)) * n
                pos += 1
            else:
                idx += data[pos:pos + n]
                pos += n
    blank = bytes(step)
    out = bytearray(b"".join(table[i - first] if 0 <= i - first < length else blank for i in idx[:count]))
    if len(out) != count * step:
        raise ValueError("%s: a cut palette TGA" % path)
    return width, height, step, bool(desc & 0x20), img_type, out


def true_colour_head(data, step, width=None, height=None):
    """The header (with its id field) for these pixels written as an uncompressed true-colour TGA (type 2): the
    file's own id, size and row order kept; a colour-mapped file loses its map (the pixels carry the colours now)."""
    id_len = data[0]
    head = bytearray(data[:18 + id_len])
    head[1] = 0                                     # no colour map
    head[2] = 2
    head[3:8] = bytes(5)
    if width is not None:
        struct.pack_into("<HH", head, 12, width, height)
    head[16] = step * 8
    head[17] = (head[17] & 0x30) | (8 if step == 4 else 0)
    return head


def read_tga_bytes(data, path="(picture)"):
    """read_tga from bytes already in memory (a picture a plan is about to write)."""
    width, height, step, top_down, _, out = _decode(data, path)
    count = width * height
    rgb = bytearray(count * 3)
    rgb[0::3] = out[2::step]
    rgb[1::3] = out[1::step]
    rgb[2::3] = out[0::step]
    if top_down:                        # stored top-down: flip to bottom-up
        row = width * 3
        rgb = bytearray(b"".join(bytes(rgb[r * row:(r + 1) * row]) for r in range(height - 1, -1, -1)))
    return Image(width, height, raw=rgb)


def patched(path, changes, data=None):
    """The TGA's bytes with pixels changed: changes = {(x, y): (r, g, b)} in the
    bottom-up tile coordinates read_tga uses. The header, id field, bit depth,
    alpha and row order stay; an RLE image comes back uncompressed (type 2),
    which the game reads the same way. data: the bytes to start from (a picture
    an earlier part of the same write already changed), else the file's."""
    if data is None:
        with open(path, "rb") as f:
            data = f.read()
    width, height, step, top_down, _, raw = _decode(data, path)
    for (x, y), (r, g, b) in changes.items():
        row = (height - 1 - y) if top_down else y          # storage row of tile row y
        o = (row * width + x) * step
        raw[o:o + 3] = bytes((b, g, r))
    return bytes(true_colour_head(data, step)) + bytes(raw)
