"""Fitting a picture into the faction's emblem by hand (a tester: 'the emblem needs an editor of its own, to fit the
picture into a circle like all the other icons'): the picture's place and size, a shape it is cut to (the old
emblem's own outline - most are a disc - a circle, a square, or none), a ground inside the shape (clear, the
faction's colours, any colour), and two tools from every picture editor: the magic wand (a click clears the area of
like colour - a white background gone) and the paint bucket (a click fills an area of like colour). The result is one
square master picture; emblem.build makes every emblem picture of the faction from it, each in its own size."""

MASTER = 256                                     # the master picture's side


def frame_mask(pics, olds, size=MASTER):
    """The old emblem's outline ('L', size x size, 255 inside): the alpha of its biggest normal picture, scaled -
    the shape the game's own emblems have (most a disc). None when there is none to take."""
    from PIL import Image
    from .emblem import EMBLEM_KINDS, variant_of
    best = None
    for p in pics:
        im = olds.get(p["rel"])
        if im is None or variant_of(p["label"]) is not None or not p["label"].startswith(EMBLEM_KINDS):
            continue
        if best is None or im.size[0] * im.size[1] > best.size[0] * best.size[1]:
            best = im
    if best is None:
        return None
    a = best.split()[3].point(lambda v: 255 if v >= 40 else 0)
    box = a.getbbox()
    if not box:
        return None
    a = a.crop(box)
    side = max(a.size)
    sq = Image.new("L", (side, side), 0)
    sq.paste(a, ((side - a.size[0]) // 2, (side - a.size[1]) // 2))
    return sq.resize((size, size), Image.LANCZOS)


def shape_mask(shape, frame=None, size=MASTER):
    """'L' mask of the shape the picture is cut to: 'old' (the old emblem's outline, a circle when there is none),
    'circle', 'square' or None (not cut)."""
    from PIL import Image, ImageDraw
    if shape in (None, "none"):
        return None
    if shape == "old" and frame is not None:
        return frame.resize((size, size)) if frame.size != (size, size) else frame
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    if shape == "square":
        d.rectangle((2, 2, size - 3, size - 3), fill=255)
    else:
        d.ellipse((2, 2, size - 3, size - 3), fill=255)
    return m


def auto_place(src, size=MASTER, margin=0.08):
    """(scale, dx, dy) that fit the picture's solid part into the master square with a small margin."""
    from .emblem import footprint
    box = footprint(src.convert("RGBA")) or (0, 0, src.size[0], src.size[1])
    k = (1 - 2 * margin) * size / max(box[2], box[3], 1)
    return k, 0.0, 0.0


def compose(src, state, size=MASTER):
    """The master picture (RGBA, size x size) from the source and state: {'scale', 'dx', 'dy' (pixels of the
    master), 'angle' (degrees), 'shape', 'frame' (mask or None), 'ground' (rgb or None)}."""
    from PIL import Image
    from .emblem import footprint
    im = src.convert("RGBA")
    box = footprint(im)
    if box:
        x, y, w, h = box
        im = im.crop((x, y, x + w, y + h))
    k = state.get("scale") or auto_place(src, size)[0]
    im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
    if state.get("angle"):
        im = im.rotate(state["angle"], resample=Image.BICUBIC, expand=True)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ground = state.get("ground")
    mask = shape_mask(state.get("shape"), state.get("frame"), size)
    if ground:
        g = Image.new("RGBA", (size, size), tuple(ground) + (255,))
        out.paste(g, (0, 0), mask if mask is not None else None)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    layer.paste(im, (int(round((size - im.size[0]) / 2 + state.get("dx", 0))),
                     int(round((size - im.size[1]) / 2 + state.get("dy", 0)))), im)
    out.alpha_composite(layer)
    if mask is not None:
        a = out.split()[3]
        from PIL import ImageChops
        out.putalpha(ImageChops.multiply(a, mask))
    return out


def like_area(im, xy, tolerance):
    """The quick select of every picture editor: the set of pixels (x, y) of the area of like colour joined to xy by
    its sides (each colour channel within tolerance of the clicked pixel; clear pixels only join clear ones) - the
    picture itself is not changed (Recolour's touch-ups paint that area)."""
    w, h = im.size
    x0, y0 = int(xy[0]), int(xy[1])
    if not (0 <= x0 < w and 0 <= y0 < h):
        return set()
    rgba = im.convert("RGBA")
    px = rgba.load()
    ref = px[x0, y0]

    def like(c):
        if ref[3] == 0:
            return c[3] == 0
        return c[3] > 0 and all(abs(c[i] - ref[i]) <= tolerance for i in range(3))
    got, todo, seen = set(), [(x0, y0)], {(x0, y0)}
    while todo:
        x, y = todo.pop()
        if not like(px[x, y]):
            continue
        got.add((x, y))
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < w and 0 <= b < h and (a, b) not in seen:
                seen.add((a, b))
                todo.append((a, b))
    return got


def flood(im, xy, tolerance, fill=None):
    """The magic wand / paint bucket on a picture (RGBA, changed in place): the area of like colour joined to xy
    (each channel within tolerance of the clicked pixel, edges by sides) made clear (fill None) or filled with fill
    (rgb). -> the number of pixels changed."""
    w, h = im.size
    x0, y0 = int(xy[0]), int(xy[1])
    if not (0 <= x0 < w and 0 <= y0 < h):
        return 0
    px = im.load()
    ref = px[x0, y0]
    if ref[3] == 0 and fill is None:
        return 0

    def like(c):
        if ref[3] == 0:
            return c[3] == 0
        return c[3] > 0 and all(abs(c[i] - ref[i]) <= tolerance for i in range(3))
    new = (0, 0, 0, 0) if fill is None else tuple(fill)[:3] + (255,)
    seen = {(x0, y0)}
    todo = [(x0, y0)]
    n = 0
    while todo:
        x, y = todo.pop()
        if not like(px[x, y]):
            continue
        px[x, y] = new
        n += 1
        for a, b in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= a < w and 0 <= b < h and (a, b) not in seen:
                seen.add((a, b))
                todo.append((a, b))
    return n


def clear_background(im, tolerance=30):
    """A picture with a plain background (a white or one-coloured square round the symbol, its four corners alike
    and solid) made clear there - flooded from the corners, like the magic wand clicked on each (changed in place).
    -> the number of pixels cleared (0 when the picture already has a clear background or none to tell)."""
    w, h = im.size
    if w < 4 or h < 4:
        return 0
    px = im.load()
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    cols = [px[c] for c in corners]
    if any(c[3] < 250 for c in cols):
        return 0
    ref = cols[0]
    if any(max(abs(c[i] - ref[i]) for i in range(3)) > tolerance for c in cols):
        return 0
    n = 0
    for c in corners:
        if px[c][3]:
            n += flood(im, c, tolerance)
    return n if n < w * h * 0.97 else 0


def to_source(state, src_size, xy, size=MASTER):
    """A point of the master picture -> the same point of the source picture (for the wand / bucket clicks), or
    None when it lies outside the source."""
    import math
    k = state.get("scale") or 1.0
    ang = math.radians(state.get("angle") or 0)
    # the master's centre is the (rotated, scaled, cropped) source's centre moved by dx, dy
    cx, cy = size / 2 + state.get("dx", 0), size / 2 + state.get("dy", 0)
    x, y = (xy[0] - cx) / k, (xy[1] - cy) / k
    # PIL rotates counter-clockwise for a positive angle: undo it
    rx = x * math.cos(-ang) + y * math.sin(-ang)
    ry = -x * math.sin(-ang) + y * math.cos(-ang)
    box = state.get("_box") or (0, 0) + tuple(src_size)
    sx, sy = box[0] + box[2] / 2 + rx, box[1] + box[3] / 2 + ry
    if 0 <= sx < src_size[0] and 0 <= sy < src_size[1]:
        return int(sx), int(sy)
    return None
