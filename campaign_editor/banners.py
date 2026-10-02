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
    from PIL import Image, ImageChops, ImageStat
    from .emblem import footprint
    out = dye(blank.convert("RGBA"), colour, pattern)
    if symbol is None:
        return out
    sym = symbol.convert("RGBA")
    fb = footprint(sym)
    if fb:
        sym = sym.crop((fb[0], fb[1], fb[0] + fb[2], fb[1] + fb[3]))
    keep = out.split()[3]
    for bx0, by0, bx1, by1 in (boxes if boxes is not None else symbol_boxes(blank)):
        bw, bh = bx1 - bx0, by1 - by0
        if bw < 2 or bh < 2:
            continue
        k = min(bw / sym.size[0], bh / sym.size[1])
        s = sym.resize((max(1, round(sym.size[0] * k)), max(1, round(sym.size[1] * k))), Image.LANCZOS)
        at = (bx0 + (bw - s.size[0]) // 2, by0 + (bh - s.size[1]) // 2)
        under = blank.convert("RGBA").crop((at[0], at[1], at[0] + s.size[0], at[1] + s.size[1])).convert("L")
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
    out.putalpha(keep)                                    # the banner's own outline stays
    return out
