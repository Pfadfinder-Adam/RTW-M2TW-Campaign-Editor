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


def patched(path, changes):
    """The TGA's bytes with pixels changed: changes = {(x, y): (r, g, b)} in the
    bottom-up tile coordinates read_tga uses. The header, id field, bit depth,
    alpha and row order stay; an RLE image comes back uncompressed (type 2),
    which the game reads the same way."""
    with open(path, "rb") as f:
        data = f.read()
    width, height, step, top_down, _, raw = _decode(data, path)
    id_len = data[0]
    for (x, y), (r, g, b) in changes.items():
        row = (height - 1 - y) if top_down else y          # storage row of tile row y
        o = (row * width + x) * step
        raw[o:o + 3] = bytes((b, g, r))
    head = bytearray(data[:18 + id_len])
    head[2] = 2
    return bytes(head) + bytes(raw)
