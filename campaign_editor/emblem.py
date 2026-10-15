"""The faction's emblem: one picture the game shows in many places and sizes - the campaign-menu buttons (24 / 48,
each normal, mouse over, selected, greyed out), the loading-screen logo (128), the faction-screen symbol (M2TW 80),
the in-game panels' symbol (M2TW ui/faction_symbols), the faction logo and small logo (Rome, on sprite sheets).
Replacing it once gives every one of them, each in its own size, and the button states are made the way the
mod's own are: mouse over = brighter, selected = brighter with the old picture's glow round it, greyed out = grey
and darker - by how much is measured from the faction's old pictures (a mod with other buttons keeps its look)."""

import os
import statistics

EMBLEM_KINDS = ("small campaign-menu button", "big campaign-menu button", "loading-screen logo",
                "symbol on the faction screen", "faction symbol (in-game panels)", "faction logo (faction button)",
                "small faction logo")
SYMBOL_KINDS = ("flag symbol on the campaign map",)         # the bare symbol, no disc or ground round it
# made from the new battle banner (Rome): the same texture on its towns' flagpoles, its square flag as the 3D symbol
# on the campaign map, its flag on the captains' cards and portraits (the dead card grey)
FLAG_KINDS = ("flag on its towns in battle", "faction symbol (3D) texture", "captain's card", "captain's portrait")
BANNER_FIELDS = ("standard_texture", "ally_texture")       # Rome's battle banners (descr_banners.txt)
VARIANTS = (("(mouse over)", "roll"), ("(selected)", "select"), ("(greyed out)", "grey"))
DEFAULT = {"roll": 1.4, "grey": 0.75}


# what the game makes from the emblem by itself - no picture of the faction to write (Rome: descr_standards.txt names
# ONE white flag for every army (banners/strat_flag) and fleet (banners/navy_banner -> navy_julii.tga); the game dyes
# it in the faction's primary / secondary colours and lays the faction's slot of banners/symbolsN on it; descr_banners
# gives the general's, the unit's and the mini banner the same standard_texture)
GAME_MADE = {"rome": "The flags over its armies and fleets on the campaign map are made by the game itself: one white "
                     "flag dyed in the faction's two colours with the flag symbol made here; its generals' and small "
                     "banners in battle are the battle banner."}


def game_made(game):
    """The sentence saying which flags the game makes from the emblem by itself, for 'rome' / 'medieval2'; ''."""
    return GAME_MADE.get(game, "")


def variant_of(label):
    for word, v in VARIANTS:
        if word in label:
            return v
    return None


def is_banner(p):
    return bool(p.get("link")) and p["link"][0] == "banners" and p["link"][1] in BANNER_FIELDS


def emblem_pictures(pics):
    """The Art tab's pictures (factionart.faction_pictures) that show the emblem, not locked: the emblem itself,
    the flag symbol on the campaign map and the battle banners that carry the symbol."""
    return [p for p in pics if not p.get("locked") and (
        any(p["label"].startswith(k) for k in EMBLEM_KINDS + SYMBOL_KINDS + FLAG_KINDS) or is_banner(p))
            and "(rebel)" not in p["label"] and ("(dead)" not in p["label"] or p["label"].startswith("captain's"))
            and not (_rebels_flag(p))]


def _rebels_flag(p):
    """A flag or banner of the rebels (the slave faction): the rebel flag every faction's rebels carry - never
    touched (the user, 2026-10-15: the routing and the rebel flags stay as they are)."""
    name = os.path.basename(p.get("rel") or "").lower()
    flaggy = is_banner(p) or any(p["label"].startswith(k) for k in FLAG_KINDS + SYMBOL_KINDS)
    return flaggy and any(w in name for w in ("slave", "rebel"))


def square_flag(banner):
    """The square flag of a Rome banner texture (the right one of its two banners - the pennant is the narrow one):
    (x0, y0, x1, y1) or None."""
    from . import banners as B
    boxes = B.banner_boxes(banner)
    if not boxes:
        return None
    x0, y0, x1, y1 = max(boxes, key=lambda b: b[2] - b[0])
    # the cloth alone: from its first row that is nearly whole (below the top's loops), a square at most - the
    # fringe and the stars under it left out
    a = banner.convert("RGBA").getchannel("A").load()
    w = x1 - x0
    top = next((y for y in range(y0, y1) if sum(1 for x in range(x0, x1) if a[x, y] > 200) >= 0.9 * w), y0)
    return x0, top, x1, min(y1, top + w)


def cloth_box(card, cloth):
    """(x0, y0, x1, y1) of the flag's cloth on a captain's card / portrait: the pixels of the cloth's colour (within a
    distance), their bounding box; None when too few."""
    px = card.convert("RGB").load()
    w, h = card.size
    hits = [(x, y) for y in range(h) for x in range(w)
            if sum(abs(a - b) for a, b in zip(px[x, y], cloth)) < 90]
    if len(hits) < max(12, w * h // 40):
        return None
    xs, ys = [x for x, _ in hits], [y for _, y in hits]
    xs.sort()
    ys.sort()
    k = len(xs) // 50                                  # a few stray pixels of that colour elsewhere left out
    return xs[k], ys[k], xs[-1 - k] + 1, ys[-1 - k] + 1


def cloth_colour(old_banner):
    """The cloth's own colour of the faction's old battle banner: the median of its square flag's opaque pixels."""
    box = square_flag(old_banner)
    if box is None:
        return None
    part = old_banner.crop(box)
    pix = [q[:3] for q in part.getdata() if q[3] > 200]
    if len(pix) < 20:
        return None
    return tuple(int(statistics.median(c[i] for c in pix)) for i in range(3))


def white_square(blank):
    """The square flag of the game's blank white banner (the routing one): the white cloth with its folds, no symbol -
    the template of every square flag of the faction (the 3D symbol, the captains' flags)."""
    box = square_flag(blank)
    return blank.convert("RGBA").crop(box) if box else None


def white_template(old, cloth, square):
    """(template, cloth mask 'L', the symbol's box) of a captain's card / portrait: the old picture with its flag's
    cloth made the blank white cloth (the white square laid over the cloth's place, any cloth round it - a torn
    barbarian edge - turned white by its own light), the pole, fringe, sky and frame as they are. None when the
    cloth is not found."""
    from PIL import Image
    where = cloth_box(old, cloth)
    if where is None or square is None:
        return None
    w, h = where[2] - where[0], where[3] - where[1]
    tpl = old.convert("RGBA").copy()
    mask = Image.new("L", old.size, 0)
    piece = square.resize((w, h), Image.LANCZOS)
    tpl.paste(piece, where[:2], piece)
    mask.paste(piece.getchannel("A"), where[:2])
    lum0 = max(1.0, 0.299 * cloth[0] + 0.587 * cloth[1] + 0.114 * cloth[2])
    po, pt, pm = old.convert("RGBA").load(), tpl.load(), mask.load()
    for y in range(old.size[1]):
        for x in range(old.size[0]):
            if where[0] <= x < where[2] and where[1] <= y < where[3]:
                continue
            q = po[x, y]
            if q[3] > 0 and sum(abs(c - d) for c, d in zip(q[:3], cloth)) < 90:
                v = max(0, min(255, int(225 * (0.299 * q[0] + 0.587 * q[1] + 0.114 * q[2]) / lum0)))
                pt[x, y] = (v, v, v, q[3])
                pm[x, y] = 255
    side = int(min(w, h) * 0.72)
    cx, cy = where[0] + w // 2, where[1] + int(h * 0.45)
    return tpl, mask, (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)


def paint_template(tpl, mask, colour, symbol, box, pattern="plain"):
    """A white template (white_template / white_square) made the faction's: its cloth (mask) dyed in the colour(s),
    the folds kept; the symbol in box, shaded by the folds. The rest of the picture untouched."""
    from . import banners as B
    out = tpl.convert("RGBA").copy()
    px, mp = out.load(), mask.load()
    w, h = out.size
    cloth = [px[x, y] for y in range(h) for x in range(w) if mp[x, y] > 128]
    lums = sorted(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in cloth) or [200]
    base = max(1.0, lums[len(lums) * 3 // 4])
    colours = [colour] if isinstance(colour[0], int) else list(colour)
    n, which = B.PATTERNS.get(pattern, B.PATTERNS["plain"])
    box_all = mask.getbbox() or (0, 0, w, h)
    for y in range(h):
        for x in range(w):
            if mp[x, y] <= 128:
                continue
            u = (x - box_all[0]) / max(1, box_all[2] - box_all[0])
            v = min(0.999, (y - box_all[1]) / max(1, box_all[3] - box_all[1]))
            c = colours[min(int(which(u, v)) if n > 1 else 0, len(colours) - 1)]
            r, g, b, a = px[x, y]
            k = (0.299 * r + 0.587 * g + 0.114 * b) / base
            px[x, y] = tuple(min(255, int(t * k)) for t in c[:3]) + (a,)
    if symbol is not None and box:
        keep = out.getchannel("A")
        B.put_symbol(out, tpl.convert("L"), symbol, [box])
        out.putalpha(keep)
    return out


def flag_pictures(p, old, blank, settings, symbol, old_standard):
    """A picture of FLAG_KINDS made from a white template (the user, 2026-10-15: 'do not repaint - make white
    templates like the routing flags, easy to fill, and lay the symbol on them'): the town flag's template is the
    blank banner itself, the 3D symbol's its white square flag, a captain's card's / portrait's the old one with its
    flag's cloth made that white cloth; each then dyed in the faction's colour(s) with the symbol. None when it
    cannot be placed."""
    from PIL import Image
    from . import banners as B
    label = p["label"]
    if old is None or blank is None:
        return None
    colours = settings.get("colours") or settings.get("colour") or (200, 200, 200)
    pattern = settings.get("pattern") or "plain"
    sym = None if settings.get("no_symbol") else symbol
    if label.startswith("flag on its towns in battle"):
        return B.make(blank, settings, symbol, 1.0).resize(old.size, Image.LANCZOS)
    square = white_square(blank)
    if square is None:
        return None
    if label.startswith("faction symbol (3D) texture"):
        tpl = square.resize(old.size, Image.LANCZOS)
        side = int(min(old.size) * 0.72)
        box = ((old.size[0] - side) // 2, int(old.size[1] * 0.45) - side // 2,
               (old.size[0] + side) // 2, int(old.size[1] * 0.45) + side // 2)
        return paint_template(tpl, tpl.getchannel("A").point(lambda v: 255 if v > 128 else 0), colours, sym, box,
                              pattern)
    cloth = cloth_colour(old_standard) if old_standard is not None else None
    got = white_template(old, cloth, square) if cloth else None
    if got is None:
        return None
    tpl, mask, box = got
    return paint_template(tpl, mask, colours, sym, box, pattern)


def _old(p):
    from .recolour import read_picture
    try:
        im = read_picture(p["path"]).convert("RGBA")
    except Exception:
        return None
    if p.get("crop"):
        x, y, w, h = p["crop"]
        im = im.crop((x, y, x + w, y + h))
    return im


def _family(p):
    """The normal picture's key for a button state: the path without _roll / _select / _grey."""
    low = p["rel"].lower()
    for v in ("_roll", "_select", "_grey"):
        low = low.replace(v + ".", ".")
    return low


def measure(normal, other, variant):
    """How much brighter (roll / select) or how grey-dark (grey) `other` is than `normal` - the median over the
    pixels both cover; None when it cannot be told."""
    if normal is None or other is None or normal.size != other.size:
        return None
    vals = []
    for p, q in zip(normal.getdata(), other.getdata()):
        if p[3] > 200 and q[3] > 200:
            if variant == "grey":
                lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
                if lum > 20:
                    vals.append(q[0] / lum)
            elif sum(p[:3]) > 60:
                vals.append(sum(q[:3]) / float(sum(p[:3])))
    return statistics.median(vals) if len(vals) > 20 else None


def footprint(old):
    """Where the old picture's emblem lies (its solid part): (x, y, w, h), or None."""
    if old is None:
        return None
    box = old.split()[3].point(lambda a: 255 if a >= 40 else 0).getbbox()
    return (box[0], box[1], box[2] - box[0], box[3] - box[1]) if box else None


def fit(src, size, box=None):
    """src made size, its shape kept: fitted into box (the old emblem's place - the margins and a selected
    button's glow stay free) or the whole picture, centred, on a clear ground."""
    from PIL import Image
    im = src.convert("RGBA")
    solid = footprint(im)
    if solid:                                    # the source's own clear margins left out
        x, y, w, h = solid
        im = im.crop((x, y, x + w, y + h))
    bx, by, bw, bh = box or (0, 0, size[0], size[1])
    k = min(bw / im.size[0], bh / im.size[1])
    new = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
    out = Image.new("RGBA", tuple(size), (0, 0, 0, 0))
    out.paste(new, (bx + (bw - new.size[0]) // 2, by + (bh - new.size[1]) // 2))
    return out


def _bright(im, k):
    from PIL import Image
    r, g, b, a = im.split()
    r, g, b = (c.point(lambda x: min(255, int(x * k + 0.5))) for c in (r, g, b))
    return Image.merge("RGBA", (r, g, b, a))


def _grey(im, k):
    from PIL import Image
    r, g, b, a = im.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L").point(lambda x: min(255, int(x * k + 0.5)))
    return Image.merge("RGBA", (lum, lum, lum, a))


def _glow(old_normal, old_select, new):
    """The glow of a selected button round the NEW emblem's shape: its colour, strength and width taken from the
    old selected picture's glow (where the old normal one is clear)."""
    from PIL import Image, ImageChops, ImageFilter, ImageStat
    if old_normal is None or old_select is None or old_normal.size != old_select.size:
        return None
    clear = old_normal.split()[3].point(lambda a: 255 if a < 40 else 0)
    halo = ImageChops.multiply(old_select.split()[3], clear)
    if not halo.getbbox():
        return None
    st = ImageStat.Stat(old_select.convert("RGB"), halo.point(lambda a: 255 if a > 30 else 0))
    colour = tuple(int(c) for c in st.mean)
    strength = max(halo.getextrema()[1], 1)
    width = max(1, int(round(halo.point(lambda a: 255 if a > 30 else 0).histogram()[255] /
                             max(1.0, 2.0 * (old_normal.size[0] + old_normal.size[1])))))
    shape = new.split()[3].point(lambda a: 255 if a >= 40 else 0)
    grown = shape.filter(ImageFilter.MaxFilter(2 * width + 1)).filter(ImageFilter.GaussianBlur(width * 0.7))
    glow = Image.new("RGBA", new.size, colour + (0,))
    glow.putalpha(grown.point(lambda a: a * strength // 255))
    return glow


def build(src, pics, symbol=None, banner=None):
    """{rel of the Art picture: new picture (RGBA, its size)} for every emblem picture, from one source picture
    (a Pillow image). pics: emblem_pictures(...). symbol: the bare symbol (no disc, no ground) for the flag symbol
    and the banners - src when not given. banner: {'blank': the blank white banner (banners.templates), 'colour':
    the cloth's colour, 'boxes': where the symbol goes or None} - the battle banners are made from it; without it
    they are left as they are."""
    from PIL import Image
    from . import banners as B
    symbol = symbol or src
    olds = {p["rel"]: _old(p) for p in pics}
    normals = {_family(p): p for p in pics if variant_of(p["label"]) is None}
    out = {}
    old_standard = None
    std = next((q for q in pics if is_banner(q) and q["link"][1] == "standard_texture"), None)
    if std is not None:
        old_standard = olds.get(std["rel"])
    alive = next((q for q in pics if q["label"] == "captain's card"), None)
    dead = next((q for q in pics if q["label"] == "captain's card (dead)"), None)
    grey_k = measure(olds.get(alive["rel"]) if alive else None, olds.get(dead["rel"]) if dead else None, "grey")
    for p in pics:
        if any(p["label"].startswith(k) for k in FLAG_KINDS):
            if "(dead)" in p["label"]:
                continue                                # made from the living card below
            got = flag_pictures(p, olds.get(p["rel"]), banner.get("blank") if banner else None, banner or {},
                                banner.get("symbol") or symbol if banner else symbol, old_standard)
            if got is not None:
                out[p["rel"]] = got
            continue
        if is_banner(p):
            if banner and banner.get("blank") is not None and (banner.get("colours") or banner.get("colour") or
                                                                banner.get("drawing")):
                out[p["rel"]] = B.make(banner["blank"], banner, banner.get("symbol") or symbol,
                                       B.ALLY_STRENGTH if p["link"][1] == "ally_texture" else 1.0)
            continue
        if any(p["label"].startswith(k) for k in SYMBOL_KINDS):
            old = olds.get(p["rel"])
            if old is not None:
                out[p["rel"]] = fit(symbol, old.size, footprint(old))
            continue
        size = tuple(p["size"][:2]) if p.get("size") else (olds[p["rel"]].size if olds[p["rel"]] else None)
        if not size:
            continue
        v = variant_of(p["label"])
        n0 = normals.get(_family(p))
        ref = olds.get(n0["rel"]) if n0 else olds[p["rel"]]
        box = footprint(ref) if ref is not None and ref.size == size else None
        base = fit(src, size, box)
        if v is None:
            out[p["rel"]] = base
            continue
        n = normals.get(_family(p))
        old_n = olds.get(n["rel"]) if n else None
        old_v = olds[p["rel"]]
        if v == "grey":
            out[p["rel"]] = _grey(base, measure(old_n, old_v, "grey") or DEFAULT["grey"])
            continue
        lit = _bright(base, measure(old_n, old_v, "roll") or DEFAULT["roll"])
        if v == "select":
            glow = _glow(old_n, old_v, lit)
            if glow is not None:
                under = Image.new("RGBA", size, (0, 0, 0, 0))
                under.alpha_composite(glow)
                under.alpha_composite(lit)
                lit = under
        out[p["rel"]] = lit
    if dead is not None and alive is not None and alive["rel"] in out:   # the dead captain's card: the new one grey
        old_dead = olds.get(dead["rel"])
        card = out[alive["rel"]]
        if old_dead is not None and old_dead.size != card.size:
            card = card.resize(old_dead.size, Image.LANCZOS)
        out[dead["rel"]] = _grey(card, grey_k or DEFAULT["grey"])
    return out


def save_all(made, folder):
    """The made pictures saved as PNG files in folder -> {rel: path} (what the Art tab's picks take)."""
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for k, (rel, im) in enumerate(sorted(made.items())):
        name = "%02d_%s.png" % (k, rel.replace(":", "_").replace("/", "_").replace("\\", "_")[-60:])
        p = os.path.join(folder, name)
        im.save(p)
        paths[rel] = p
    return paths


__all__ = ["EMBLEM_KINDS", "SYMBOL_KINDS", "game_made", "is_banner", "emblem_pictures", "build", "save_all", "variant_of", "measure", "fit"]
