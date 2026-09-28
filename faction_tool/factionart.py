"""A faction's pictures: every picture file named after it (buttons, symbols,
logos, banners, the leader's picture, the campaign-select map...), what each
needs (size, depth), replacing any of them, and the campaign-select map
map_<faction>.tga drawn from the faction's start regions.

The campaign-select maps of a campaign (map_<faction>.tga in its folder, vanilla
384 x 237, 24-bit) share one background; each lights its faction's land in a
colour of its own, the ground's texture showing through. The background is what
most of them have at each pixel; the land is map_regions.tga scaled to the
picture; the light is the colour times the ground's brightness (to the power 0.3), a crisp
edge softened by half a pixel - denser than vanilla's, by the user's choice."""

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
# (test on the path, what it is, where the game shows it) - the first that fits wins
PICTURE_KINDS = (
    (lambda low, name: "fe_buttons_24" in low, "small campaign-menu button",
     "the small faction button of the campaign menus"),
    (lambda low, name: "fe_buttons_48" in low, "big campaign-menu button",
     "the big faction button of the campaign-select screen"),
    (lambda low, name: "battlefield_pics" in low, "battle-select picture",
     "the custom / historical battle screen, behind the faction's name"),
    (lambda low, name: "fe_faction_units" in low, "units picture on the faction screen",
     "the faction-select screen, the soldiers standing under the faction's name"),
    (lambda low, name: "fe_symbols_80" in low, "symbol on the faction screen",
     "the faction-select screen, the faction's symbol (80 px)"),
    (lambda low, name: "faction_symbols" in low, "faction symbol (in-game panels)",
     "the campaign's panels: settlement, character and diplomacy scrolls"),
    (lambda low, name: "/fe_flags" in low or "flag" in name, "flag",
     "the front-end menus, next to the faction's name"),
    (lambda low, name: low.startswith("loading_screen"), "loading-screen logo",
     "the loading screen while the campaign loads"),
    (lambda low, name: name.startswith("map_"), "campaign-select map (its land lit)",
     "the campaign-select screen: the map with the faction's land lit"),
    (lambda low, name: name.startswith("vcs_"), "victory conditions map (short campaign)",
     "the campaign-select screen, the regions to take in the short campaign"),
    (lambda low, name: name.startswith("vc_"), "victory conditions map",
     "the campaign-select screen, the regions to take to win"),
    (lambda low, name: name.startswith("leader_pic"), "leader picture (campaign select)",
     "the campaign-select screen, the faction leader's face"),
    (lambda low, name: "faction_icons" in low, "faction icon",
     "the campaign map's top bar and the faction lists"),
    (lambda low, name: "captain" in name and "portrait" in name, "captain's portrait",
     "the army panel of an army led by a captain (no named general)"),
    (lambda low, name: "captain" in name, "captain's card",
     "the unit card of a captain's bodyguard in the army panel"),
    (lambda low, name: "standard" in name or "banner" in low, "banner / standard texture",
     "the banners carried over the faction's units in battle"),
    (lambda low, name: "/units/" in low or "/unit_info/" in low, "unit picture",
     "the unit cards and the unit information scroll"),
    (lambda low, name: "symbol" in name, "symbol",
     "the faction's symbol in the menus"),
)


def _picture_kind(rel):
    low = rel.replace("\\", "/").lower()
    name = os.path.basename(low)
    for test, kind, where in PICTURE_KINDS:
        if test(low, name):
            return low, name, kind, where
    folder = os.path.dirname(low)
    return low, name, "picture in %s" % (folder or "data"), None


def label_of(rel):
    """A plain name for what a picture is, from where it lies."""
    low, name, kind, _ = _picture_kind(rel)
    for part, word in (("_roll", " (mouse over)"), ("_select", " (selected)"), ("_grey", " (greyed out)"),
                       ("_rebel", " (rebel)")):
        if part in name:
            kind += word
            break
    if "/dead/" in low:
        kind += " (dead)"
    return kind


def where_shown(rel):
    """Where the game shows the picture, or None when the tool does not know."""
    return _picture_kind(rel)[3]


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
        out.append({"path": p, "rel": rel, "label": label_of(rel), "where": where_shown(rel),
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
    # only map_<faction>.tga of real factions (their front-end names too): the campaign folder
    # may also hold map_regions, map_heights, map_ground_types... (HLR keeps them there)
    from .clone import FE_NAMES
    names = set()
    for n, _ in mod.factions():
        names.add(n.lower())
        if FE_NAMES.get(n):
            names.add(FE_NAMES[n].lower())
    names |= {n.split("_", 1)[-1] for n in names if n.startswith("romans_")}      # map_julii
    if os.path.isdir(folder):
        for n in sorted(os.listdir(folder)):
            m = re.match(r"map_(.+)\.tga$", n, re.I)
            if m and m.group(1).lower() in names:
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


def _map_mask(mod, campaign, keep):
    """An L image the size of map_regions.tga, top row first: 255 where keep(rgb)."""
    from PIL import Image
    img = mod.region_map(campaign)
    w, h = img.width, img.height
    hit = {}
    data = bytearray(w * h)
    for y in range(h):                                      # map_regions rows run bottom-up
        row = (h - 1 - y) * w
        for x in range(w):
            c = img.pixels[y * w + x]
            v = hit.get(c)
            if v is None:
                v = hit[c] = 255 if keep(c) else 0
            data[row + x] = v
    return Image.frombytes("L", (w, h), bytes(data))


def _place(mask, frame, size):
    """The map-sized mask scaled and set where the map lies in the picture."""
    from PIL import Image
    s, dx, dy = frame
    big = mask.resize((max(1, round(mask.width * s)), max(1, round(mask.height * s))), Image.NEAREST)
    out = Image.new("L", size)
    out.paste(big, (dx, dy))
    return out


def select_frame(mod, campaign, size=None):
    """(scale, dx, dy): where the map lies in the campaign's select pictures - a map pixel
    x, y (top row first) is picture pixel x * scale + dx, y * scale + dy. Rome's pictures are
    the whole map stretched; Medieval II's are the map scaled 1.32 and shifted inside a
    decorated frame, the Americas cut off. Learnt from the pictures themselves: the land of
    map_regions laid over the background where land and sea differ the most."""
    key = ("select_frame", campaign)
    if key in mod._cache:
        return mod._cache[key]
    got = select_background(mod, campaign)
    img = mod.region_map(campaign)
    if not got:
        return None
    bg, _ = got
    pw, ph = size or bg.size
    W, H = img.width, img.height
    stretch = (pw / W, 0, 0)
    if abs((pw / W) / (ph / H) - 1) < 0.03:
        mod._cache[key] = stretch                  # the same shape as the map: the whole map stretched (Rome)
        return stretch
    info = mod.regions(campaign)
    cols = {r["colour"] for r in info.values()} | {(0, 0, 0), (255, 255, 255)}
    land = _map_mask(mod, campaign, lambda c: c in cols)
    # the fit takes seconds: kept in the settings, per mod, campaign and sizes
    from . import settings
    skey = "%s|%s|%dx%d|%dx%d" % (os.path.normcase(os.path.abspath(mod.data)), campaign, pw, ph, W, H)
    known = settings.get("select_frames", {}) or {}
    if isinstance(known.get(skey), list) and len(known[skey]) == 3:
        frame = tuple(known[skey])
    else:
        frame = _fit(bg.convert("L"), land, stretch)
        known = dict(known)
        known[skey] = list(frame)
        settings.put("select_frames", known)
    mod._cache[key] = frame
    return frame


def _fit(pic, land, stretch):
    from PIL import Image, ImageChops, ImageOps, ImageStat
    sea = ImageOps.invert(land)

    def score(p, lm, sm, frame):
        # how much lighter the picture is on the map's land than on its sea, summed over the
        # map's place and set against its size (a cross-correlation of the land mask)
        a, b = _place(lm, frame, p.size), _place(sm, frame, p.size)
        na, nb = ImageStat.Stat(a).sum[0] / 255, ImageStat.Stat(b).sum[0] / 255
        if na < 50 or nb < 50:
            return -1e18
        la = ImageStat.Stat(ImageChops.multiply(p, a)).sum[0]
        lb = ImageStat.Stat(ImageChops.multiply(p, b)).sum[0]
        n = na + nb
        if n < 0.6 * p.width * p.height:
            return -1e18                                   # the map covers most of the picture
        q = squares[p.size]
        sq = (ImageStat.Stat(ImageChops.multiply(q, a)).sum[0] + ImageStat.Stat(ImageChops.multiply(q, b)).sum[0])
        m = (la + lb) / n
        var = sq * 255.0 / n - m * m
        if var <= 0:
            return -1e18
        # Pearson's r of the picture's brightness and the land mask over the part the map covers
        return abs(la / na - lb / nb) * (na * nb) ** 0.5 / n / var ** 0.5
    # coarse: a quarter of the size, every scale and place
    k = 4
    small = pic.resize((max(1, pic.width // k), max(1, pic.height // k)), Image.BILINEAR)
    squares = {p.size: ImageChops.multiply(p, p) for p in (pic, small)}
    W, H = land.size
    base = min(pic.width / W, pic.height / H)
    best = (score(pic, land, sea, stretch), stretch)
    scales = [base * (0.9 + 0.03 * i) for i in range(24)]
    coarse = (-1, None)
    for sc in scales:
        w, h = W * sc / k, H * sc / k
        xs = range(int(min(0, small.width - w)) - 3, int(max(0, small.width - w)) + 4)
        ys = range(int(min(0, small.height - h)) - 3, int(max(0, small.height - h)) + 4)
        for dx in xs:
            for dy in ys:
                v = score(small, land, sea, (sc / k, dx, dy))
                if v > coarse[0]:
                    coarse = (v, (sc, dx * k, dy * k))
    if coarse[1]:
        sc0, dx0, dy0 = coarse[1]
        for i in range(-4, 5):
            sc = sc0 * (1 + 0.005 * i)
            for dx in range(dx0 - 5, dx0 + 6):
                for dy in range(dy0 - 5, dy0 + 6):
                    v = score(pic, land, sea, (sc, dx, dy))
                    if v > best[0] * 1.02:                  # the plain stretch unless clearly worse
                        best = (v, (sc, dx, dy))
    return best[1]


def _region_mask(mod, campaign, regions, size):
    """An L image of `size`: 255 on these regions' land, map_regions.tga laid where the
    map lies in the select pictures (select_frame)."""
    img = mod.region_map(campaign)
    info = mod.regions(campaign)
    cols = {info[r]["colour"] for r in regions if r in info}
    mask = _map_mask(mod, campaign, lambda c: c in cols)
    px = mask.load()
    # the town (black) and port (white) pixels are the region's land too - else a hole at each town
    from .mapedit import ports
    towns, harbours = mod.city_tiles(campaign), ports(mod, campaign)
    for r in regions:
        for xy in (towns.get(r), harbours.get(r)):
            if xy:
                px[xy[0], img.height - 1 - xy[1]] = 255
    frame = select_frame(mod, campaign, size) or (size[0] / img.width, 0, 0)
    if frame[1:] == (0, 0) and abs(frame[0] - size[0] / img.width) < 1e-9:
        from PIL import Image
        return mask.resize(size, Image.NEAREST)          # the whole map stretched (Rome)
    return _place(mask, frame, size)


def draw_select_map(mod, campaign, regions, colour):
    """Pillow RGB image: the background with the land of these regions lit in colour;
    None when the campaign has no background to start from (or Pillow is missing)."""
    got = select_background(mod, campaign)
    if not got:
        return None
    from PIL import Image, ImageFilter
    bg, _ = got
    # a crisp edge (half a pixel of softening) and a dense light: the ground's texture shows
    # only faintly through (the user's choice, a little stronger than vanilla's)
    mask = _region_mask(mod, campaign, regions, bg.size).filter(ImageFilter.GaussianBlur(0.5))
    lum = bg.convert("L")
    m, l = _pixels(mask), _pixels(lum)
    inside = [l[i] for i in range(len(m)) if m[i] > 128]
    mean = (sum(inside) / len(inside)) if inside else 128.0
    out = _pixels(bg)
    grey = sum(colour) / 3.0
    cr, cg, cb = (min(255.0, max(0.0, grey + (c - grey) * 1.2)) for c in colour)     # a touch more saturated
    for i, a in enumerate(m):
        if not a:
            continue
        t = (l[i] / mean) ** 0.3 if mean else 1.0
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


def future(plan, campaign):
    """The mod as it will be once the plan is written, for drawing: map_regions.tga and
    descr_regions.txt as the plan leaves them (new regions, painted borders); the
    background learnt from the files on disk."""
    from .moddata import ModData
    from .tga import read_tga_bytes
    mod = plan.mod
    fut = ModData(mod.data)
    rp = mod.campaign_file(campaign, "map_regions.tga")
    if rp in plan.binaries:
        fut._cache[("map", campaign)] = read_tga_bytes(plan.binaries[rp], rp)
    dr = mod.campaign_file(campaign, "descr_regions.txt")
    if dr in plan.files:
        fut._cache[dr] = plan.files[dr]
    fut._cache[("select_bg", campaign)] = select_background(mod, campaign)
    fut._cache[("select_frame", campaign)] = select_frame(mod, campaign)     # where the map lies: from disk too
    return fut


def write_select_map(plan, campaign, faction, regions, colour):
    """map_<faction>.tga drawn from its regions (a note says so), on the map as the plan
    leaves it; False when the campaign has no maps to learn the background from."""
    mod = plan.mod
    im = draw_select_map(future(plan, campaign), campaign, regions, tuple(colour))
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


def colour_on_map(mod, campaign, faction, regions):
    """The colour a faction's land has on its own campaign-select map now (the mean
    of the lit pixels), or None."""
    got = select_background(mod, campaign)
    path = _ci(mod.campaign_dir(campaign), "map_%s.tga" % faction)
    if not got or not path:
        return None
    from PIL import Image
    bg, _ = got
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    if im.size != bg.size:
        return None
    a, b = _pixels(im), _pixels(bg)
    mask = _pixels(_region_mask(mod, campaign, regions, bg.size)) if regions else None
    if mask:                                 # inside its land (the edges and texture average out as drawn)
        pairs = [(p, q) for p, q, k in zip(a, b, mask) if k > 128]
        # land that is not lit at all (the map shows no light there): no colour to learn
        if pairs and sum(abs(p[i] - q[i]) for p, q in pairs for i in range(3)) / len(pairs) < 30:
            return None
        lit = [p for p, _ in pairs]
    else:
        lit = [p for p, q in zip(a, b) if abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) > 60]
    if not lit:
        return None
    n = len(lit)
    return tuple(int(sum(p[i] for p in lit) / n) for i in range(3))


def region_factions(plan, campaign):
    """The factions (owners after the plan) of every region whose land the plan changes:
    painted tiles (the region they go to and the one they come from) and new regions."""
    from .strat import Strat
    regions = plan.opts.get("regions") or {}
    painted = {tuple(k) if not isinstance(k, str) else tuple(int(v) for v in k.split(",")): r
               for k, r in (regions.get("painted") or {}).items()}
    new = regions.get("new") or []
    if not painted and not new:
        return set()
    mod = plan.mod
    img = mod.region_map(campaign)
    by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}
    touched = set(painted.values()) | {r["name"] for r in new}
    for xy in painted:
        was = by_colour.get(img.get(*xy)) if 0 <= xy[0] < img.width and 0 <= xy[1] < img.height else None
        if was:
            touched.add(was)
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    owners = Strat(plan.files[sp] if sp in plan.files else mod.load(sp)).owners()
    return {owners[r] for r in touched if owners.get(r) and owners[r] != "slave"}


def redraw_map_changes(plan, campaign):
    """For a run that only changes the map: the select maps of the factions whose land
    changed, in their own colours."""
    if select_background(plan.mod, campaign):
        redraw_others(plan, campaign, region_factions(plan, campaign), force=True)


def redraw_others(plan, campaign, changed_factions, force=False):
    """The campaign-select maps of the other factions whose towns changed (taken
    from them, given to them), in the colour their own map has."""
    from .strat import Strat
    mod = plan.mod
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    if not select_background(mod, campaign):
        return
    before = Strat(mod.load(sp)).owners()
    after = Strat(plan.files[sp]).owners() if sp in plan.files else before
    for fac in sorted(changed_factions):
        if fac == "slave" or not _ci(mod.campaign_dir(campaign), "map_%s.tga" % fac):
            continue
        old = [r for r, o in before.items() if o == fac]
        new = [r for r, o in after.items() if o == fac]
        if sorted(old) == sorted(new) and not force:
            continue
        colour = colour_on_map(mod, campaign, fac, old)
        if not colour:                              # its map shows no light: one from its colours
            from .edit import read_faction
            try:
                colour = default_map_colour(read_faction(mod, campaign, fac).get("primary_colour"))
            except Exception:
                colour = default_map_colour(None)
        write_select_map(plan, campaign, fac, new, colour)


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
    from .strat import Strat
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    if sp in plan.files:                            # its land as the plan leaves it (new regions too)
        regions = [r for r, o in Strat(plan.files[sp]).owners().items() if o == faction] or regions
    shaped = region_factions(plan, campaign)        # owners of land that changed hands on the map
    if faction in shaped:
        towns_changed = True
    if shaped - {faction}:
        redraw_others(plan, campaign, shaped - {faction}, force=True)
    if towns_changed:
        # the factions that lost (or got) towns: their maps too, in their own colour
        from .strat import Strat
        sp = mod.campaign_file(campaign, "descr_strat.txt")
        if sp in plan.files:
            before = Strat(mod.load(sp)).owners()
            after = Strat(plan.files[sp]).owners()
            others = {o for r, o in before.items() if after.get(r) != o} | \
                {o for r, o in after.items() if before.get(r) != o}
            redraw_others(plan, campaign, others - {faction})
    if sel.get("off"):
        return
    if not (towns_changed or sel.get("colour")):
        return
    target = map_name(mod.campaign_dir(campaign), faction)
    rel = os.path.relpath(target, mod.data).replace("\\", "/")
    if rel in (plan.opts.get("art") or {}):
        return                                              # a picture of its own was given
    colour = sel.get("colour")
    if not colour and not plan.opts.get("_primary_changed", bool(plan.opts.get("primary_colour"))):
        # no colour of its own picked: the light the template's (or its own) map already has
        from .strat import Strat
        src = plan.template
        owned = [st.region for st in (Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).faction(src)
                                      or type("x", (), {"settlements": []})).settlements]
        colour = colour_on_map(mod, campaign, src, owned)
    colour = tuple(colour or default_map_colour(primary))
    if not write_select_map(plan, campaign, faction, regions, colour) and sel.get("colour"):
        plan.warn(None, "fewer than three campaign-select maps (map_<faction>.tga) in the campaign folder: "
                        "%s's cannot be drawn - replace it by hand" % faction)
