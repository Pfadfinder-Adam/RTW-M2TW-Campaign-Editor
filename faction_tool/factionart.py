"""A faction's pictures: every picture file named after it (buttons, symbols,
logos, banners, the leader's picture, the campaign-select map...), what each
needs (size, depth), replacing any of them, and the campaign-select map
map_<faction>.tga drawn from the faction's start regions.

The campaign-select maps of a campaign (map_<faction>.tga in its folder, vanilla
384 x 237, 24-bit) share one background; each lights its faction's land in a
colour of its own, the ground's texture showing through. The background is what
most of them have at each pixel; the land is map_regions.tga scaled to the
picture; the light is the colour times the ground's brightness (square root),
edges softened by a pixel - within a point or two of the vanilla maps."""

import colorsys
import os
import re

from .clone import ART_ROOTS, _token_hit
from .editors import tga_info
from .moddata import _ci

PICTURE_EXT = (".tga", ".dds", ".png", ".bmp")


# ---------------------------------------------------------------------------
# Every picture of a faction
# ---------------------------------------------------------------------------
def label_of(rel):
    """A plain name for what a picture is, from where it lies."""
    low = rel.replace("\\", "/").lower()
    name = os.path.basename(low)
    if "fe_buttons_24" in low:
        kind = "small campaign-menu button"
    elif "fe_buttons_48" in low:
        kind = "big campaign-menu button"
    elif "/fe_flags" in low or "flag" in name:
        kind = "flag"
    elif low.startswith("loading_screen"):
        kind = "loading-screen logo"
    elif name.startswith("map_"):
        kind = "campaign-select map (its land lit)"
    elif name.startswith("leader_pic"):
        kind = "leader picture (campaign select)"
    elif "faction_icons" in low:
        kind = "faction icon"
    elif "captain" in name:
        kind = "captain's %s" % ("portrait" if "portrait" in name else "card")
    elif "standard" in name or "banner" in low:
        kind = "banner / standard texture"
    elif "/units/" in low or "/unit_info/" in low:
        kind = "unit picture"
    elif "symbol" in name:
        kind = "symbol"
    else:
        kind = "picture"
    for part, word in (("_roll", " (mouse over)"), ("_select", " (selected)"), ("_grey", " (greyed out)"),
                       ("_rebel", " (rebel)")):
        if part in name:
            kind += word
            break
    if "/dead/" in low:
        kind += " (dead)"
    return kind


def faction_pictures(mod, campaign, faction):
    """[{'path', 'rel', 'label', 'size': (w, h, bpp) or None}] of every picture file
    named after the faction under data/ui, data/menu, data/loading_screen, the
    campaign folder, and its banner textures in descr_banners.txt - not the
    unit cards (the unit editor has those)."""
    out, seen = [], set()

    def add(p):
        n = os.path.normcase(os.path.abspath(p))
        if n in seen or not os.path.isfile(p):
            return
        seen.add(n)
        rel = os.path.relpath(p, mod.data).replace("\\", "/")
        out.append({"path": p, "rel": rel, "label": label_of(rel),
                    "size": tga_info(p) if p.lower().endswith(".tga") else None})
    roots = [os.path.join(mod.data, r) for r in ART_ROOTS] + [mod.campaign_dir(campaign)]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            low = dirpath.replace("\\", "/").lower()
            if "/ui/units" in low or "/ui/unit_info" in low:
                dirnames[:] = []
                continue
            for d in dirnames:
                if d.lower() == faction:                      # a folder of its own: all of it
                    for sp, _, fs in os.walk(os.path.join(dirpath, d)):
                        for n in fs:
                            if n.lower().endswith(PICTURE_EXT):
                                add(os.path.join(sp, n))
            dirnames[:] = [d for d in dirnames if d.lower() != faction]
            for n in filenames:
                if n.lower().endswith(PICTURE_EXT) and _token_hit(n, faction):
                    add(os.path.join(dirpath, n))
    banners = mod.file("banners")
    if banners:
        cur = None
        for l in mod.load(banners).texts():
            t = l.split(";")[0].split()
            if len(t) >= 2 and t[0] == "faction":
                cur = t[1]
            elif cur == faction and len(t) >= 2 and t[0].endswith("_texture"):
                p = _ci(mod.data, t[1].replace("\\", "/"))
                if p:
                    add(p)
    out.sort(key=lambda e: (e["label"], e["rel"]))
    return out


# ---------------------------------------------------------------------------
# The campaign-select map
# ---------------------------------------------------------------------------
def map_name(campaign_dir, faction):
    """The campaign-select map of a faction in the campaign folder (existing case), or the
    name a new one gets."""
    return _ci(campaign_dir, "map_%s.tga" % faction) or os.path.join(campaign_dir, "map_%s.tga" % faction)


def _pixels(im):
    """The pixels of a Pillow image as a list (get_flattened_data where Pillow has it)."""
    return list(getattr(im, "get_flattened_data", im.getdata)())


def default_map_colour(primary):
    """The light a faction's land gets on the campaign-select map: its primary colour's
    hue, lighter and softer (vanilla picks each by hand; this lands near them)."""
    if not primary:
        return (200, 200, 200)
    h, s, v = colorsys.rgb_to_hsv(*[c / 255.0 for c in primary])
    if s < 0.08:                                            # black, grey, white: a light grey
        return (215, 215, 212)
    r, g, b = colorsys.hsv_to_rgb(h, min(max(s, 0.35), 0.6), 0.82)
    return int(r * 255), int(g * 255), int(b * 255)


def select_background(mod, campaign):
    """(Pillow RGB image, the file it copies the layout of) - what most of the
    campaign's map_*.tga have at each pixel; None with fewer than three maps."""
    key = ("select_bg", campaign)
    if key in mod._cache:
        return mod._cache[key]
    try:
        from PIL import Image
    except ImportError:                     # without Pillow (python + the standard library only): no drawing
        return None
    folder = mod.campaign_dir(campaign)
    maps = []
    if os.path.isdir(folder):
        for n in sorted(os.listdir(folder)):
            if re.match(r"map_.+\.tga$", n, re.I) and "radar" not in n.lower():
                try:
                    im = Image.open(os.path.join(folder, n)).convert("RGB")
                except Exception:
                    continue
                maps.append((n, im))
    sizes = {}
    for n, im in maps:
        sizes.setdefault(im.size, []).append((n, im))
    group = max(sizes.values(), key=len) if sizes else []
    if len(group) < 3:
        mod._cache[key] = None
        return None
    w, h = group[0][1].size
    datas = [_pixels(im) for _, im in group]
    half = len(datas) // 2
    out = []
    for i in range(w * h):
        vals = sorted(d[i] for d in datas)                  # the middle value: what most have
        out.append(vals[half])
    bg = Image.new("RGB", (w, h))
    bg.putdata(out)
    mod._cache[key] = (bg, os.path.join(folder, group[0][0]))
    return mod._cache[key]


def draw_select_map(mod, campaign, regions, colour):
    """Pillow RGB image: the background with the land of these regions lit in colour;
    None when the campaign has no background to start from (or Pillow is missing)."""
    got = select_background(mod, campaign)
    if not got:
        return None
    from PIL import Image, ImageFilter
    bg, _ = got
    img = mod.region_map(campaign)
    info = mod.regions(campaign)
    cols = {info[r]["colour"] for r in regions if r in info}
    mask = Image.new("L", (img.width, img.height))
    px = mask.load()
    for y in range(img.height):
        for x in range(img.width):
            if img.get(x, y) in cols:
                px[x, img.height - 1 - y] = 255             # map_regions rows run bottom-up
    mask = mask.resize(bg.size, Image.NEAREST).filter(ImageFilter.GaussianBlur(1))
    lum = bg.convert("L")
    m, l = _pixels(mask), _pixels(lum)
    inside = [l[i] for i in range(len(m)) if m[i] > 128]
    mean = (sum(inside) / len(inside)) if inside else 128.0
    out = _pixels(bg)
    cr, cg, cb = colour
    for i, a in enumerate(m):
        if not a:
            continue
        t = (l[i] / mean) ** 0.5 if mean else 1.0
        lit = (min(255, cr * t), min(255, cg * t), min(255, cb * t))
        k = a / 255.0
        o = out[i]
        out[i] = tuple(int(round(o[j] * (1 - k) + lit[j] * k)) for j in range(3))
    res = Image.new("RGB", bg.size)
    res.putdata(out)
    return res


def image_tga(im, like=None):
    """A Pillow image as TGA bytes in the depth of `like` (a TGA file: 24 or 32 bit),
    uncompressed, rows bottom-up as the game's own."""
    import io
    info = tga_info(like) if like else None
    mode = "RGB" if info and info[2] == 24 else "RGBA"
    buf = io.BytesIO()
    im.convert(mode).save(buf, format="TGA", rle=False, orientation=-1)
    return buf.getvalue()


def write_select_map(plan, campaign, faction, regions, colour):
    """map_<faction>.tga drawn from its regions (a note says so); False when the
    campaign has no maps to learn the background from."""
    mod = plan.mod
    im = draw_select_map(mod, campaign, regions, tuple(colour))
    if im is None:
        return False
    target = map_name(mod.campaign_dir(campaign), faction)
    _, like = select_background(mod, campaign)
    plan.binary(target, image_tga(im, like))
    plan.notes.append((mod.rel(target), "campaign-select map drawn: %d region(s) lit in %d %d %d" % (
        (len(regions),) + tuple(colour))))
    return True


# ---------------------------------------------------------------------------
# Writing: pictures replaced by hand, the campaign-select map drawn
# ---------------------------------------------------------------------------
def replace_picture(plan, src, target, like=None):
    """src (PNG, JPG, TGA...) written over target in the size and depth of `like`
    (the file it replaces, or the template's picture it is copied from)."""
    from PIL import Image
    info = tga_info(like) if like and like.lower().endswith(".tga") else None
    im = Image.open(src)
    size = info[:2] if info else None
    if size and im.size != tuple(size):
        im = im.resize(tuple(size), Image.LANCZOS)
    plan.binary(target, image_tga(im, like))
    plan.notes.append((plan.mod.rel(target), "picture replaced by %s%s" % (
        os.path.basename(src), " (%d x %d, %d-bit)" % info if info else "")))


def apply_opts(plan, campaign, faction, regions, primary, towns_changed):
    """opts['art'] = {path under data: picture to put there}; opts['select_map'] =
    {'colour': [r, g, b]} or {'off': True}: the campaign-select map is drawn for a new
    faction and when an edited one's towns change (or its colour is set)."""
    mod = plan.mod
    for rel, src in sorted((plan.opts.get("art") or {}).items()):
        target = os.path.join(mod.data, *rel.replace("\\", "/").split("/"))
        like = target if os.path.exists(target) else next(
            (s for s, d in plan.copies if os.path.normcase(d) == os.path.normcase(target)), None)
        replace_picture(plan, src, target, like)
    sel = plan.opts.get("select_map") or {}
    if sel.get("off"):
        return
    if not (towns_changed or sel.get("colour")):
        return
    target = map_name(mod.campaign_dir(campaign), faction)
    rel = os.path.relpath(target, mod.data).replace("\\", "/")
    if rel in (plan.opts.get("art") or {}):
        return                                              # a picture of its own was given
    colour = tuple(sel.get("colour") or default_map_colour(primary))
    if not write_select_map(plan, campaign, faction, regions, colour) and sel.get("colour"):
        plan.warn(None, "fewer than three campaign-select maps (map_<faction>.tga) in the campaign folder: "
                        "%s's cannot be drawn - replace it by hand" % faction)
