"""The faction's symbol painted on its battle banners (Rome: models/textures/standard_<faction>[_ally].tga.dds - a
256 x 256 texture holding two banners, the stars of the unit's experience and the pole below them): on each banner
the old symbol is found (what differs from the cloth in the banner's middle), the cloth is filled in over it from
its edges inwards (the way a picture editor's healing brush does), and the new symbol is put where the old one was,
shaded by the cloth's own folds - the game drapes the texture on its 3D banner models (a tester's wish: the new
emblem on every 3D flag, not only on the icons).

Medieval II's banners are heraldic sheets of many pieces (Faction_banner_<faction>.texture) - not done here yet."""


def _banners(alpha, h_limit):
    """[(x0, y0, x1, y1)] of the banners: the columns with cloth in the upper part of the texture, each with its
    own top and bottom."""
    w, h = alpha.size
    px = alpha.load()
    cols = [any(px[x, y] > 128 for y in range(0, h_limit)) for x in range(w)]
    out, x = [], 0
    while x < w:
        if not cols[x]:
            x += 1
            continue
        x0 = x
        while x < w and cols[x]:
            x += 1
        if x - x0 >= 12:
            ys = [y for y in range(h_limit) if any(px[c, y] > 128 for c in range(x0, x))]
            out.append((x0, ys[0], x, ys[-1] + 1))
    return out


def _median(vals):
    vals = sorted(vals)
    return vals[len(vals) // 2] if vals else 0


def _count(mask):
    return sum(mask.histogram()[128:])


def grow(seeds, within, steps=80):
    """seeds grown into the joined pixels of within (both 'L' masks) - the strong parts of a symbol take its faint
    parts along, the cloth's folds (faint, with no strong part) stay out."""
    from PIL import ImageChops, ImageFilter
    cur = ImageChops.multiply(seeds, within)
    for _ in range(steps):
        nxt = ImageChops.multiply(cur.filter(ImageFilter.MaxFilter(3)), within)
        if ImageChops.difference(nxt, cur).getbbox() is None:
            break
        cur = nxt
    return cur


def find_symbols(im):
    """[(mask ('L', the texture's size, 255 on the old symbol), its box, the cloth colour)] - one per banner whose
    middle has a symbol."""
    from PIL import Image, ImageFilter
    rgba = im.convert("RGBA")
    w, h = rgba.size
    out = []
    px = rgba.load()
    soft = rgba.filter(ImageFilter.GaussianBlur(1.2)).load()     # the weave's grain smoothed away
    for x0, y0, x1, y1 in _banners(rgba.split()[3], int(h * 0.72)):
        bw, bh = x1 - x0, y1 - y0
        ix0, ix1 = x0 + int(bw * 0.10), x1 - int(bw * 0.10)
        iy0, iy1 = y0 + int(bh * 0.07), y1 - int(bh * 0.13)
        if ix1 - ix0 < 8 or iy1 - iy0 < 8:
            continue
        # the cloth: the commonest colour of the banner's middle (a ring round it can cross a second colour of a
        # two-coloured cloth; the whole banner can be mostly its dark frame)
        cells = [soft[x, y] for y in range(iy0, iy1, 2) for x in range(ix0, ix1, 2) if px[x, y][3] > 128]
        if not cells:
            continue
        buckets = {}
        for p in cells:
            buckets.setdefault((p[0] // 40, p[1] // 40, p[2] // 40), []).append(p)
        top = max(buckets.values(), key=len)
        cloth = tuple(_median([p[i] for p in top]) for i in range(3))

        def far(p):
            return max(abs(p[i] - cloth[i]) for i in range(3))
        # how much the cloth itself varies (folds, weave) - the symbol must stand out more than that; the
        # allies' banners carry their symbol faintly, a shade of the cloth
        near = sorted(d for d in (far(p) for p in cells) if d < 60)
        noise = near[int(len(near) * 0.75)] if near else 20
        hi, lo = max(45, min(90, 3.0 * noise)), max(20, min(60, 1.6 * noise))
        strong = Image.new("L", (w, h), 0)
        weak = Image.new("L", (w, h), 0)
        sp, wp = strong.load(), weak.load()
        n = 0
        # the strong parts are looked for in the banner's middle; the faint parts may run on nearly to its edge (a
        # handle, a word under the picture), never onto the trim round it
        gx0, gx1 = x0 + int(bw * 0.05), x1 - int(bw * 0.05)
        gy0, gy1 = y0 + int(bh * 0.04), y1 - int(bh * 0.09)
        for y in range(gy0, gy1):
            for x in range(gx0, gx1):
                if px[x, y][3] <= 128:
                    continue
                d = far(soft[x, y])
                if d > lo:
                    wp[x, y] = 255
                    if d > hi and ix0 <= x < ix1 and iy0 <= y < iy1:
                        sp[x, y] = 255
                        n += 1
        area = (ix1 - ix0) * (iy1 - iy0)
        if n < 0.01 * area:
            continue
        strong = strong.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))   # lone specks out
        mask = grow(strong, weak)
        if mask.getbbox() is None or _count(mask) > 0.75 * area:
            continue
        mask = mask.filter(ImageFilter.MaxFilter(5))                  # its soft edge too
        box = mask.getbbox()
        out.append((mask, box, cloth))
    return out


def heal(im, mask):
    """The pixels under mask filled from their neighbours, ring by ring from the edge inwards (RGBA, in place)."""
    w, h = im.size
    px = im.load()
    mp = mask.load()
    todo = {(x, y) for y in range(h) for x in range(w) if mp[x, y] and px[x, y][3] > 0}
    for _ in range(max(w, h)):
        if not todo:
            break
        done = {}
        for (x, y) in todo:
            got = [px[a, b] for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1),
                                         (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1))
                   if 0 <= a < w and 0 <= b < h and (a, b) not in todo and px[a, b][3] > 0]
            if len(got) >= 2:
                done[(x, y)] = tuple(sum(c[i] for c in got) // len(got) for i in range(3)) + (px[x, y][3],)
        if not done:
            break
        for p, c in done.items():
            px[p[0], p[1]] = c
        todo -= set(done)


def paint_symbol(old, symbol, found=None):
    """The banner texture with its symbols replaced by symbol (RGBA, a clear background), or None when no symbol
    is found on it. found: [(mask, box, ...)] to use instead of looking (the faction's own banner's places for its
    allies' banner, which carries the same symbol faintly at the same place; or places corrected by hand)."""
    from PIL import Image, ImageChops, ImageStat
    from .emblem import footprint
    found = find_symbols(old) if found is None else found
    if not found:
        return None
    out = old.convert("RGBA").copy()
    sym = symbol.convert("RGBA")
    fb = footprint(sym)
    if fb:
        sym = sym.crop((fb[0], fb[1], fb[0] + fb[2], fb[1] + fb[3]))
    for f in found:
        mask, box = f[0], f[1]
        heal(out, mask)
        bx0, by0, bx1, by1 = box
        bw, bh = bx1 - bx0, by1 - by0
        k = min(bw / sym.size[0], bh / sym.size[1])
        s = sym.resize((max(1, round(sym.size[0] * k)), max(1, round(sym.size[1] * k))), Image.LANCZOS)
        at = (bx0 + (bw - s.size[0]) // 2, by0 + (bh - s.size[1]) // 2)
        # the cloth's folds: its light under the symbol against its average light there
        under = out.crop((at[0], at[1], at[0] + s.size[0], at[1] + s.size[1])).convert("L")
        base = max(1.0, ImageStat.Stat(under).mean[0])
        shade = under.point(lambda v: min(255, int(255 * min(1.6, max(0.4, v / base)) / 1.6)))
        r, g, b, a = s.split()
        lit = [ImageChops.multiply(c, shade).point(lambda v: min(255, int(v * 1.6))) for c in (r, g, b)]
        s = Image.merge("RGBA", lit + [a])
        layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        layer.paste(s, at, s)
        keep = out.split()[3]
        out.alpha_composite(layer)
        out.putalpha(keep)                                    # the banner's own outline stays
    return out
