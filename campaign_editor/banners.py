"""The faction's battle banners (Rome: models/textures/standard_<faction>[_ally].tga.dds - a 256 x 256 texture
holding two banners, the stars of the unit's experience and the pole below them) made new from the game's own blank
white banner (standard_routing - Roman, _barbarian, _eastern: the cloth a routing unit carries): the cloth dyed in
the faction's colour, the symbol painted on it, shaded by the cloth's folds; the allies' banner the same with the
symbol faint, as the game's own are. Nothing of the old banner is cut out (a tester: 'there is a white flag - use it,
dye it, put the emblem on it')."""

import os

TEMPLATES = (("Roman", "standard_routing"), ("barbarian", "standard_routing_barbarian"),
             ("eastern", "standard_routing_eastern"))
CLOTH_PART = 0.72                     # the banners hang in the upper part; the stars and the pole are below
ALLY_STRENGTH = 0.35                  # how strongly the allies' banner shows the symbol


def template_path(mod, kind):
    """The blank banner of that kind in the mod (or the game's data), or None."""
    name = dict(TEMPLATES)[kind] + ".tga.dds"
    for data in (mod.data, getattr(mod, "game_data", None)):
        if not data:
            continue
        folder = os.path.join(data, "models", "textures")
        try:
            for f in os.listdir(folder):
                if f.lower() == name:
                    return os.path.join(folder, f)
        except OSError:
            pass
    return None


def templates(mod):
    """{kind: RGBA picture} of the blank banners the mod has."""
    from PIL import Image
    out = {}
    for kind, _ in TEMPLATES:
        p = template_path(mod, kind)
        if p:
            try:
                out[kind] = Image.open(p).convert("RGBA")
            except Exception:
                pass
    return out


def best_template(blanks, old):
    """The kind of blank banner whose shape is nearest the faction's old banner (by their outlines)."""
    if not blanks:
        return None
    if old is None:
        return next(iter(blanks))
    from PIL import ImageChops
    a = old.convert("RGBA").split()[3].point(lambda v: 255 if v > 128 else 0)

    def score(im):
        b = im.split()[3].point(lambda v: 255 if v > 128 else 0)
        if b.size != a.size:
            b = b.resize(a.size)
        both = sum(ImageChops.multiply(a, b).histogram()[255:])
        either = sum(ImageChops.lighter(a, b).histogram()[255:])
        return both / max(1, either)
    return max(blanks, key=lambda k: score(blanks[k]))


def banner_boxes(im):
    """[(x0, y0, x1, y1)] of the banners: the runs of columns with cloth in the upper part of the texture."""
    w, h = im.size
    alpha = im.split()[3]
    px = alpha.load()
    lim = int(h * CLOTH_PART)
    cols = [any(px[x, y] > 128 for y in range(0, lim, 2)) for x in range(w)]
    out, x = [], 0
    while x < w:
        if not cols[x]:
            x += 1
            continue
        x0 = x
        while x < w and cols[x]:
            x += 1
        if x - x0 >= 12:
            ys = [y for y in range(lim) if any(px[c, y] > 128 for c in range(x0, x, 2))]
            out.append((x0, ys[0], x, ys[-1] + 1))
    return out


def symbol_boxes(im):
    """Where the symbol goes on each banner: a square across most of its width, in its upper middle."""
    out = []
    for x0, y0, x1, y1 in banner_boxes(im):
        bw, bh = x1 - x0, y1 - y0
        side = min(int(bw * 0.72), int(bh * 0.55))
        cx, cy = (x0 + x1) // 2, y0 + int(bh * 0.40)
        out.append((cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side))
    return out


def cloth_mask(blank):
    """'L' mask of the banners' cloth: the pale, colourless pixels joined to the top of the texture (a long banner
    runs down beside the stars; the stars, the pole and a gold fringe are not cloth)."""
    import colorsys
    from PIL import Image, ImageDraw
    w, h = blank.size
    px = blank.load()
    m = Image.new("L", (w, h), 0)
    mp = m.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[1] <= 0.25:
                mp[x, y] = 255
    for y in range(min(12, h)):
        for x in range(w):
            if mp[x, y] == 255:
                ImageDraw.floodfill(m, (x, y), 128)
    return m.point(lambda v: 255 if v == 128 else 0)


# the cloth's patterns (a tester: 'tricolours - vertical, horizontal, diagonal, any'): name -> (how many colours,
# which colour a point (u, v) of a banner takes; u across, v down, both 0..1 within that banner)
PATTERNS = {
    "plain": (1, lambda u, v: 0),
    "two stripes, upright": (2, lambda u, v: int(u * 2)),
    "three stripes, upright (tricolour)": (3, lambda u, v: int(u * 3)),
    "two stripes, across": (2, lambda u, v: int(v * 2)),
    "three stripes, across": (3, lambda u, v: int(v * 3)),
    "halves, slanting /": (2, lambda u, v: 0 if u + v < 1 else 1),
    "halves, slanting \\": (2, lambda u, v: 0 if u > v else 1),
    "three bands, slanting": (3, lambda u, v: min(2, int((u + v) * 1.5))),
    "quarters": (2, lambda u, v: (u >= 0.5) ^ (v >= 0.5)),
    "a cross": (2, lambda u, v: 1 if abs(u - 0.5) < 0.1 or abs(v - 0.4) < 0.08 else 0),
    "a slanting cross": (2, lambda u, v: 1 if abs(u - v) < 0.1 or abs(u + v - 1) < 0.1 else 0),
    "a border": (2, lambda u, v: 1 if min(u, 1 - u, v, 1 - v) < 0.1 else 0),
    "a stripe in the middle, upright": (2, lambda u, v: 1 if abs(u - 0.5) < 0.17 else 0),
    "a stripe in the middle, across": (2, lambda u, v: 1 if abs(v - 0.5) < 0.12 else 0),
}


def dye(blank, colour, pattern="plain"):
    """The blank banner's cloth (cloth_mask) in the colour(s) - one colour, or a list for a pattern of PATTERNS laid
    on each banner on its own - its folds kept; the trim, the stars and the pole as they are."""
    out = blank.copy()
    w, h = out.size
    px = out.load()
    mp = cloth_mask(blank).load()
    cloth = [px[x, y] for y in range(0, h, 3) for x in range(0, w, 3) if mp[x, y]]
    lums = sorted(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in cloth) or [200]
    base = max(1.0, lums[len(lums) * 3 // 4])                          # the cloth's own light
    colours = [colour] if isinstance(colour[0], int) else list(colour)
    n, which = PATTERNS.get(pattern, PATTERNS["plain"])
    boxes = banner_boxes(blank) if n > 1 else []
    for y in range(h):
        for x in range(w):
            if not mp[x, y]:
                continue
            i = 0
            for x0, y0, x1, y1 in boxes:
                if x0 <= x < x1:
                    i = which((x - x0) / max(1, x1 - x0), min(0.999, (y - y0) / max(1, y1 - y0)))
                    break
            c = colours[min(int(i), len(colours) - 1)]
            r, g, b, a = px[x, y]
            k = (0.299 * r + 0.587 * g + 0.114 * b) / base
            px[x, y] = tuple(min(255, int(v * k)) for v in c[:3]) + (a,)
    return out


def paint(blank, colour, symbol, boxes=None, strength=1.0, pattern="plain"):
    """The new banner texture: blank dyed in colour (one, or a list for the pattern), symbol (RGBA, a clear
    background; None = no symbol) in each box, shaded by the cloth's folds; strength < 1 for the allies' faint
    symbol."""
    out = dye(blank.convert("RGBA"), colour, pattern)
    if symbol is None:
        return out
    keep = out.split()[3]
    put_symbol(out, blank.convert("L"), symbol, boxes if boxes is not None else symbol_boxes(blank), strength)
    out.putalpha(keep)                                    # the banner's own outline stays
    return out


def put_symbol(out, light, symbol, boxes, strength=1.0):
    """symbol (RGBA, a clear background) fitted into each box of out (RGBA, changed in place), shaded by the
    cloth's light under it ('L' of out's size: its folds); strength < 1 = faint. Rome's and Medieval II's banners."""
    from PIL import Image, ImageChops, ImageStat
    from .emblem import footprint
    sym = symbol.convert("RGBA")
    fb = footprint(sym)
    if fb:
        sym = sym.crop((fb[0], fb[1], fb[0] + fb[2], fb[1] + fb[3]))
    for bx0, by0, bx1, by1 in boxes:
        bw, bh = bx1 - bx0, by1 - by0
        if bw < 2 or bh < 2:
            continue
        k = min(bw / sym.size[0], bh / sym.size[1])
        s = sym.resize((max(1, round(sym.size[0] * k)), max(1, round(sym.size[1] * k))), Image.LANCZOS)
        at = (bx0 + (bw - s.size[0]) // 2, by0 + (bh - s.size[1]) // 2)
        under = light.crop((at[0], at[1], at[0] + s.size[0], at[1] + s.size[1]))
        base = max(1.0, ImageStat.Stat(under).mean[0])
        shade = under.point(lambda v: min(255, int(255 * min(1.6, max(0.4, v / base)) / 1.6)))
        r, g, b, a = s.split()
        lit = [ImageChops.multiply(c, shade).point(lambda v: min(255, int(v * 1.6))) for c in (r, g, b)]
        if strength < 1:
            a = a.point(lambda v: int(v * strength))
        s = Image.merge("RGBA", lit + [a])
        layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        layer.paste(s, at)                                 # (a mask too would square the alpha)
        out.alpha_composite(layer)
    return out


def own_drawing(path, size):
    """A banner drawn in any program (on the saved template) as an RGBA picture of the banner texture's size."""
    from PIL import Image
    from .recolour import read_picture
    im = read_picture(path).convert("RGBA")
    return im if im.size == tuple(size) else im.resize(tuple(size), Image.LANCZOS)


def make(blank, s, symbol=None, strength=1.0):
    """A banner texture from the window's settings s ({'colours', 'pattern', 'boxes', 'no_symbol', 'drawing'}):
    the blank dyed in the pattern, or the player's own drawing ('drawing': a picture file) in its place; the
    symbol on it unless 'no_symbol'; the blank's outline kept."""
    sym = None if s.get("no_symbol") else symbol
    boxes = s.get("boxes")
    if not s.get("drawing"):
        return paint(blank, s.get("colours") or s.get("colour") or (200, 200, 200), sym, boxes, strength,
                     s.get("pattern") or "plain")
    out = own_drawing(s["drawing"], blank.size)
    keep = blank.convert("RGBA").getchannel("A")
    if sym is not None:
        put_symbol(out, blank.convert("L"), sym, boxes if boxes is not None else symbol_boxes(blank), strength)
    out.putalpha(keep)
    return out


def template_picture(blank):
    """The blank banner to draw on in any program: each banner's outline marked in thin red (on the see-through
    part, where the game shows nothing)."""
    from PIL import ImageDraw
    im = blank.convert("RGBA").copy()
    dr = ImageDraw.Draw(im)
    for x0, y0, x1, y1 in banner_boxes(im):
        dr.rectangle((x0 - 1, y0 - 1, x1, y1), outline=(220, 30, 30, 255))
    return im


class Kit:
    """What the banner window works with, for Rome: the blank banners (shapes), where banners and symbols are, the
    banner made from the settings; the second view = the allies' banner (the symbol faint)."""
    game = "Rome"
    side_label = "the allies' banner"

    def __init__(self, blanks):
        self.shapes = dict(blanks)

    def blank(self, s):
        return self.shapes.get(s.get("kind")) or next(iter(self.shapes.values()))

    def banners(self, s):
        return banner_boxes(self.blank(s))

    def symbol_boxes(self, s):
        return s.get("boxes") or symbol_boxes(self.blank(s))

    def make(self, s, symbol=None, strength=1.0):
        return make(self.blank(s), s, symbol, strength)

    def side(self, s, symbol=None, size=None):
        im = self.make(s, symbol, ALLY_STRENGTH)
        return im.resize(size) if size else im

    def template(self, s):
        return template_picture(self.blank(s))


# snapping the symbol: its middle goes to the lines of a grid laid over its own banner (a part of the banner's
# width / height), so it lands on the middle, a quarter, an eighth... - 0 = no grid, moved freely
GRIDS = {"No grid - move it freely": 0, "Grid: big cells (quarters)": 4, "Grid: medium cells (eighths)": 8,
         "Grid: small cells (sixteenths)": 16}
MIN_SYMBOL = 8


def banner_at(banners, x, y):
    """The number of the banner under a point (the smallest holding it), or None."""
    hit = [i for i, b in enumerate(banners) if b[0] <= x < b[2] and b[1] <= y < b[3]]
    return min(hit, key=lambda i: (banners[i][2] - banners[i][0]) * (banners[i][3] - banners[i][1])) if hit else None


def grid_lines(banner, cells):
    """([x...], [y...]) of a banner's grid lines (inside it), [] without a grid."""
    if not cells:
        return [], []
    x0, y0, x1, y1 = banner
    return ([x0 + (x1 - x0) * i / cells for i in range(1, cells)],
            [y0 + (y1 - y0) * i / cells for i in range(1, cells)])


def place_box(box, cx, cy, banner, cells=0):
    """The symbol's box (same size) with its middle at (cx, cy) - snapped to the banner's grid when cells - and kept
    on the banner as far as its size lets it."""
    w, h = box[2] - box[0], box[3] - box[1]
    x0, y0, x1, y1 = banner
    if cells:
        sx, sy = (x1 - x0) / cells, (y1 - y0) / cells
        cx = x0 + round((cx - x0) / sx) * sx
        cy = y0 + round((cy - y0) / sy) * sy
    left = min(max(cx - w / 2, x0), max(x0, x1 - w)) if w <= x1 - x0 else cx - w / 2
    top = min(max(cy - h / 2, y0), max(y0, y1 - h)) if h <= y1 - y0 else cy - h / 2
    left, top = int(round(left)), int(round(top))
    return (left, top, left + w, top + h)


def scale_box(box, factor, banner):
    """The symbol's box made bigger / smaller round its middle (never under MIN_SYMBOL, never wider or taller than
    its banner)."""
    w, h = box[2] - box[0], box[3] - box[1]
    k = max(MIN_SYMBOL / max(1, min(w, h)), min(factor, (banner[2] - banner[0]) / max(1, w),
                                                 (banner[3] - banner[1]) / max(1, h)))
    nw, nh = max(MIN_SYMBOL, int(round(w * k))), max(MIN_SYMBOL, int(round(h * k)))
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return place_box((0, 0, nw, nh), cx, cy, banner)
