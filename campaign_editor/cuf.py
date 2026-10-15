"""The games' own bitmap fonts (.cuf, magic b'CUF0'; modding_knowledge.md 'CUF FONTS') read and drawn, so the
Interface window writes menu words in the game's letters.

Used by Rome: Total War (data/fonts/*.cuf) and Medieval II: Total War (same layout).
Pure Python; Pillow is optional (only to_image needs it).

File layout (all little-endian):
  0    4      b'CUF0'
  4    22     11 x int16 font-wide metrics (see HEADER_NAMES; meanings partly guessed)
  26   2      uint16 n = glyph count
  28   4      uint32 bitmap_size = byte size of the bitmap block
  32   131072 65536 x uint16: UTF-16 code unit -> glyph index (0xFFFF = no glyph)
  +    4*n    per glyph 4 bytes: int8 top, uint8 advance, uint8 width, uint8 height
  +    4*n    per glyph uint32 offset into the bitmap block (0x7FFFFFFF = no bitmap)
  +    bitmap_size  8-bit alpha (0 = clear, 255 = solid), width*height bytes per glyph,
                    rows top to bottom, no padding, no compression
  'top' = rows from the glyph's top edge up to... the font's reference line: the glyph is
  drawn with its top row at (ref - top), where ref is the same for every glyph of the font.
  Rome: ref = baseline (A: top 10, h 10). Medieval II: ref sits a few pixels below
  the baseline (A: top 15, h 10, x: top 12, h 7) - same drawing rule works for both.
  No left bearing: the bitmap starts at the pen x; the pen then moves by 'advance'.
"""
import struct

MAGIC = b"CUF0"
NO_GLYPH = 0xFFFF
NO_BITMAP = 0x7FFFFFFF
# Guessed names; only 'size' (h1, the point size in the file name) is sure.
HEADER_NAMES = ("line_height", "size", "h2", "underline_pos", "underline_thick",
                "h5", "descent", "h7", "h8", "max_top", "max_height")


class Glyph:
    __slots__ = ("index", "top", "advance", "width", "height", "rows")

    def __init__(self, index, top, advance, width, height, rows):
        self.index, self.top, self.advance = index, top, advance
        self.width, self.height, self.rows = width, height, rows  # rows: list of bytes

    def __repr__(self):
        return "Glyph(#%d top=%d adv=%d %dx%d)" % (self.index, self.top, self.advance,
                                                 self.width, self.height)


class Font:
    def __init__(self, header, char_map, glyph_list):
        self.header = header                # dict name -> int
        self.char_map = char_map            # dict code -> glyph index
        self.glyph_list = glyph_list        # list of Glyph
        vis = [g for g in glyph_list if g.height]
        self.ref = max(g.top for g in vis) if vis else 0           # pixels above ref line
        self.below = max(g.height - g.top for g in vis) if vis else 0
        self.line_height = self.ref + self.below

    def glyph(self, ch):
        i = self.char_map.get(ord(ch))
        return None if i is None else self.glyph_list[i]

    @property
    def glyphs(self):
        """char -> (rows, width, height, x_off, y_off_from_line_top, advance)"""
        out = {}
        for code, i in self.char_map.items():
            g = self.glyph_list[i]
            out[chr(code)] = (g.rows, g.width, g.height, 0, self.ref - g.top, g.advance)
        return out


def read(src):
    if isinstance(src, (bytes, bytearray, memoryview)):
        d = bytes(src)
    else:
        with open(src, "rb") as f:
            d = f.read()
    if d[:4] != MAGIC:
        raise ValueError("not a CUF0 font")
    h = struct.unpack_from("<11h", d, 4)
    n, bsize = struct.unpack_from("<HI", d, 26)
    table = struct.unpack_from("<65536H", d, 32)
    mpos = 32 + 131072
    opos = mpos + 4 * n
    bpos = opos + 4 * n
    if bpos + bsize != len(d):
        raise ValueError("CUF0 size mismatch")
    offs = struct.unpack_from("<%dI" % n, d, opos)
    glyphs = []
    for i in range(n):
        top, adv, w, hh = struct.unpack_from("<bBBB", d, mpos + 4 * i)
        o = offs[i]
        rows = []
        if o != NO_BITMAP and w and hh:
            p = bpos + o
            rows = [d[p + y * w:p + y * w + w] for y in range(hh)]
        else:
            w = hh = 0
        glyphs.append(Glyph(i, top, adv, w, hh, rows))
    cmap = {c: g for c, g in enumerate(table) if g != NO_GLYPH}
    return Font(dict(zip(HEADER_NAMES, h)), cmap, glyphs)


def measure(font, text):
    w = x = 0
    for ch in text:
        g = font.glyph(ch) or font.glyph("?")
        if g is None:
            continue
        w = max(w, x + g.width)
        x += g.advance
    return max(w, x)


def render(font, text):
    """-> (width, height, bytes alpha) for one line of text."""
    W, H = measure(font, text), font.line_height
    buf = bytearray(W * H)
    x = 0
    for ch in text:
        g = font.glyph(ch) or font.glyph("?")
        if g is None:
            continue
        y0 = font.ref - g.top
        for y, row in enumerate(g.rows):
            yy = y0 + y
            if 0 <= yy < H:
                base = yy * W + x
                for i, a in enumerate(row):
                    if a and x + i < W and a > buf[base + i]:
                        buf[base + i] = a
        x += g.advance
    return W, H, bytes(buf)


def to_image(font, text):
    from PIL import Image
    w, h, a = render(font, text)
    return Image.frombytes("L", (max(w, 1), h), a if w else bytes(h))
