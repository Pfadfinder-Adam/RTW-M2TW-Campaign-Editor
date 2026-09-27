"""A minimal TGA reader (no dependencies) for map_regions.tga.

Supports true-colour images, uncompressed (type 2) and RLE (type 10), 24 or 32
bits. Pixels are returned bottom-up, which is the campaign map's own
orientation: pixel (x, y) here is tile (x, y) in descr_strat.txt.
"""

import struct


class Image:
    def __init__(self, width, height, pixels):
        self.width = width
        self.height = height
        self.pixels = pixels          # list of (r, g, b), row-major, bottom row first

    def get(self, x, y):
        return self.pixels[y * self.width + x]


def read_tga(path):
    with open(path, "rb") as f:
        data = f.read()
    id_len, cmap_type, img_type = data[0], data[1], data[2]
    width, height = struct.unpack_from("<HH", data, 12)
    bpp, desc = data[16], data[17]
    if img_type not in (2, 10) or bpp not in (24, 32) or cmap_type != 0:
        raise ValueError("%s: unsupported TGA (type %d, %d bpp)" % (path, img_type, bpp))
    step = bpp // 8
    pos = 18 + id_len
    count = width * height
    out = bytearray(count * step)
    if img_type == 2:
        out[:] = data[pos:pos + count * step]
    else:
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
    pixels = [(out[i + 2], out[i + 1], out[i]) for i in range(0, count * step, step)]
    if desc & 0x20:                     # stored top-down: flip to bottom-up
        rows = [pixels[r * width:(r + 1) * width] for r in range(height)]
        rows.reverse()
        pixels = [p for row in rows for p in row]
    return Image(width, height, pixels)


def patched(path, changes):
    """The TGA's bytes with pixels changed: changes = {(x, y): (r, g, b)} in the
    bottom-up tile coordinates read_tga uses. The header, id field, bit depth
    and row order stay; an RLE image comes back uncompressed (type 2), which
    the game reads the same way."""
    with open(path, "rb") as f:
        data = f.read()
    id_len, cmap_type, img_type = data[0], data[1], data[2]
    width, height = struct.unpack_from("<HH", data, 12)
    bpp, desc = data[16], data[17]
    if img_type not in (2, 10) or bpp not in (24, 32) or cmap_type != 0:
        raise ValueError("%s: unsupported TGA (type %d, %d bpp)" % (path, img_type, bpp))
    step = bpp // 8
    img = read_tga(path)
    top_down = bool(desc & 0x20)
    raw = bytearray(width * height * step)
    for y in range(height):
        row = (height - 1 - y) if top_down else y          # storage row of tile row y
        for x in range(width):
            r, g, b = changes.get((x, y), img.get(x, y))
            o = (row * width + x) * step
            raw[o:o + 3] = bytes((b, g, r))
            if step == 4:
                raw[o + 3] = 255
    # keep the original alpha where there was one
    if step == 4 and img_type == 2:
        src = data[18 + id_len:18 + id_len + len(raw)]
        for i in range(3, len(raw), 4):
            raw[i] = src[i]
    head = bytearray(data[:18 + id_len])
    head[2] = 2
    return bytes(head) + bytes(raw)
