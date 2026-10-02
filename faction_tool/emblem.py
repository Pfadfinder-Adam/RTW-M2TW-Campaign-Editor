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
BANNER_FIELDS = ("standard_texture", "ally_texture")       # Rome's battle banners (descr_banners.txt)
VARIANTS = (("(mouse over)", "roll"), ("(selected)", "select"), ("(greyed out)", "grey"))
DEFAULT = {"roll": 1.4, "grey": 0.75}


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
        any(p["label"].startswith(k) for k in EMBLEM_KINDS + SYMBOL_KINDS) or is_banner(p))
            and "(rebel)" not in p["label"] and "(dead)" not in p["label"]]


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
    for p in pics:
        if is_banner(p):
            if banner and banner.get("blank") is not None and (banner.get("colours") or banner.get("colour")):
                out[p["rel"]] = B.paint(banner["blank"], banner.get("colours") or banner["colour"],
                                        None if banner.get("no_symbol") else symbol, banner.get("boxes"),
                                        B.ALLY_STRENGTH if p["link"][1] == "ally_texture" else 1.0,
                                        banner.get("pattern") or "plain")
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


__all__ = ["EMBLEM_KINDS", "SYMBOL_KINDS", "is_banner", "emblem_pictures", "build", "save_all", "variant_of", "measure", "fit"]
