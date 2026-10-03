"""Medieval II's battle banners made new from a white template, as Rome's are made from its blank routing banner
(banners.py). M2TW has no white banner (every one of the 37 vanilla sheets carries heraldry: the rebels a white
cross, the multiplayer ally0-5 / enemy0-6 sheets numerals), but every faction shares ONE sheet layout:
banners/textures/faction_banner_<faction>.texture (1024 x 512; the _trans translucency map beside it is left alone),
and the banner meshes of descr_banners_new.xml (main_infantry, main_spear, main_cavalry, main_missile, main_general,
main_royal, the mini_* pennants) lay their cloth on the same places of every sheet.

So the white template is taken from the mod's own sheets, whatever mod it is: per pixel, the light of each sheet
measured against its own neighbourhood (the cloth's colour taken out, its folds and stitching kept), and the MEDIAN
of all sheets - each faction's heraldry is somewhere else, so it vanishes, while what all sheets share (the tooth
edges, the holes, the folds) stays. Pixels alike in nearly every sheet (the wood, the glass finials, the trim) are
kept in their colour. The cloth = what the banner meshes show of the sheet, less those. Pillow alone (the exe has
no numpy): about a second for 23 sheets, kept per mod while the files are unchanged."""

import os
import re

BLOCK = 48                     # the neighbourhood the cloth's own light is measured against (px)
SAME_WITHIN = 18               # a pixel this close (max channel) to the median in ...
SAME_SHARE = 0.70              # ... this share of the sheets is not cloth: kept in its colour
WHITE = 210                    # the template's white (the light 1.0); folds go darker, highlights up to 255
NOT_FACTIONS = ("ally", "enemy", "test_", "_trans")
MIN_PANEL = 0.004              # a piece of cloth smaller than this share of the sheet is no panel of its own
_CACHE = {}


# ---------------------------------------------------------------------------
# The mod's banner sheets and meshes (descr_banners_new.xml)
# ---------------------------------------------------------------------------
def _xml(mod):
    from .factionart import _ci
    p = _ci(mod.data, "descr_banners_new.xml")
    if not p:
        return None, ""
    with open(p, encoding="latin-1") as fh:
        return p, fh.read()


def _texture(mod, ref):
    """The picture a DiffuseMap names, on disk (the mod's, else the game's), or None."""
    from .meshview import on_disk
    ref = ref.replace("\\", "/")
    ref = ref[5:] if ref.lower().startswith("data/") else ref
    got = on_disk(mod, ref)
    return got[1] if got else None


def faction_sheet(name):
    """True for a faction's own banner sheet name (not the multiplayer ally / enemy sheets, not a test)."""
    low = os.path.basename(name.replace("\\", "/")).lower()
    return low.startswith("faction_banner_") and not any(k in low for k in NOT_FACTIONS)


def sheets(mod):
    """[path] of the faction banner sheets the mod names (descr_banners_new.xml DiffuseMap), of one size - the
    ones the template is taken from."""
    _, text = _xml(mod)
    seen, out = set(), []
    for ref in re.findall(r'DiffuseMap="([^"]+)"', text):
        if not faction_sheet(ref) or ref.lower() in seen:
            continue
        seen.add(ref.lower())
        p = _texture(mod, ref)
        if p:
            out.append(p)
    return out


def meshes(mod):
    """[path] of the banner meshes that carry the faction sheets (MainMesh / MiniMesh / GeneralMesh /
    BuildingMesh of every <Banner> whose textures are faction banner sheets) - their u v say where the cloth is."""
    from .meshview import mesh_path
    _, text = _xml(mod)
    out = []
    for m in re.finditer(r"<Banner\b([^>]*)>(.*?)</Banner>", text, re.S):
        if not any(faction_sheet(r) for r in re.findall(r'DiffuseMap="([^"]+)"', m.group(2))):
            continue
        for ref in re.findall(r'(?:Main|Mini|General|Building)Mesh="([^"]+)"', m.group(1)):
            ref = ref.replace("\\", "/")
            ref = ref[5:] if ref.lower().startswith("data/") else ref
            p = mesh_path(mod, ref)
            if p and p not in out:
                out.append(p)
    return out


def main_mesh(mod):
    """The mesh the window shows the banner on in 3D: main_infantry (the most common), else the first one."""
    ms = meshes(mod)
    return next((p for p in ms if os.path.basename(p).lower() == "main_infantry.mesh"), ms[0] if ms else None)


# ---------------------------------------------------------------------------
# The white template
# ---------------------------------------------------------------------------
class Sheet:
    """The white template of a mod's banner sheets: blank (RGBA: the cloth white with its folds, the rest in its
    colour), shade ('L', the cloth's light, WHITE = 1.0), cloth ('L' mask), panels [(x0, y0, x1, y1)] - each
    piece of cloth one banner or pennant shows."""

    def __init__(self, blank, shade, cloth, panels, count):
        self.blank, self.shade, self.cloth, self.panels, self.count = blank, shade, cloth, panels, count

    @property
    def size(self):
        return self.blank.size


def _light(im):
    """'L': the sheet's light against its own neighbourhood, 128 = as light as the cloth round it."""
    from PIL import Image, ImageMath
    lum = im.convert("L")
    w, h = lum.size
    near = lum.resize((max(1, w // BLOCK), max(1, h // BLOCK)), Image.BOX).resize((w, h), Image.BILINEAR)
    if hasattr(ImageMath, "lambda_eval"):                  # Pillow 10.3 and later
        return ImageMath.lambda_eval(lambda e: e["convert"](e["a"] * 128 / e["max"](e["b"], 8), "L"), a=lum, b=near)
    return ImageMath.eval("convert(a * 128 / max(b, 8), 'L')", a=lum, b=near)


def _median(bands):
    """Per pixel the median of the 'L' pictures (all one size)."""
    from PIL import Image
    n = len(bands)
    if n == 1:
        return bands[0].copy()
    mid = n // 2
    data = bytes(sorted(t)[mid] for t in zip(*(b.tobytes() for b in bands)))
    return Image.frombytes("L", bands[0].size, data)


def cloth_of_meshes(paths, size):
    """'L' mask of the sheet the banner meshes show (their triangles laid out by u v)."""
    return _union([_mesh_mask(p, size) for p in paths], size)


def _mesh_mask(path, size):
    from PIL import Image, ImageDraw
    from .meshview import read_file
    w, h = size
    m = Image.new("L", size, 0)
    try:
        mesh = read_file(path)
    except Exception:
        return m
    if not mesh.uvs:
        return m
    dr = ImageDraw.Draw(m)
    for g in mesh.groups:
        t = g.tris
        for i in range(0, len(t) - 2, 3):
            dr.polygon([(mesh.uvs[k][0] * w, mesh.uvs[k][1] * h) for k in t[i:i + 3]], fill=255)
    return m


def _union(masks, size):
    from PIL import Image, ImageChops
    out = Image.new("L", size, 0)
    for m in masks:
        out = ImageChops.lighter(out, m)
    return out


def _clean(mask):
    """Specks and hairlines out (an opening), then pinholes shut (a closing) - a mask of whole pieces of cloth."""
    from PIL import ImageFilter
    m = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
    return m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))


def own_cloth(masks, same, size):
    """(cloth mask, panels) from the meshes' masks: what one mesh alone shows (the pole and the fittings every
    banner hangs on are shown by them all), less the pixels alike in every sheet; one panel per mesh (the box of
    its biggest piece of cloth), the same box twice kept once."""
    from PIL import Image, ImageChops
    if not masks:
        return Image.new("L", size, 0), []
    count = Image.new("L", size, 0)
    for m in masks:
        count = ImageChops.add(count, m.point(lambda v: 1 if v > 128 else 0))
    single = count.point(lambda v: 255 if v == 1 else 0)
    keep = ImageChops.subtract(single, same)
    owns, panels = [], []
    for m in masks:
        own = _clean(ImageChops.multiply(m, keep))
        boxes = panels_of(own)
        if not boxes:
            continue
        box = Image.new("L", size, 0)
        box.paste(255, boxes[0])
        owns.append(ImageChops.multiply(own, box))          # specks beside the banner (on the pole) left out
        if boxes[0] not in panels:
            panels.append(boxes[0])
    return _union(owns, size), panels


def panels_of(cloth):
    """[(x0, y0, x1, y1)] of the pieces of cloth (joined regions of the mask, found on a picture 8 times smaller),
    biggest first; specks left out."""
    from PIL import Image
    w, h = cloth.size
    k = 8
    sw, sh = max(1, w // k), max(1, h // k)
    small = cloth.resize((sw, sh), Image.BOX).point(lambda v: 1 if v >= 96 else 0)
    px = list(small.tobytes())
    seen = [False] * len(px)
    out = []
    for start in range(len(px)):
        if not px[start] or seen[start]:
            continue
        stack, n = [start], 0
        seen[start] = True
        x0, y0, x1, y1 = sw, sh, 0, 0
        while stack:
            i = stack.pop()
            n += 1
            x, y = i % sw, i // sw
            x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
            for j in (i - 1 if x else -1, i + 1 if x + 1 < sw else -1, i - sw, i + sw):
                if 0 <= j < len(px) and px[j] and not seen[j]:
                    seen[j] = True
                    stack.append(j)
        if n >= MIN_PANEL * sw * sh:
            out.append((n, (x0 * k, y0 * k, min(w, (x1 + 1) * k), min(h, (y1 + 1) * k))))
    return [b for _, b in sorted(out, key=lambda t: -t[0])]


def make_sheet(pictures, mesh_paths=()):
    """The white template (Sheet) from the faction sheets (RGBA pictures; those of the first one's size)."""
    from PIL import Image, ImageChops
    pics = [p.convert("RGBA") for p in pictures]
    pics = [p for p in pics if p.size == pics[0].size]
    size = pics[0].size
    shade = _median([_light(p) for p in pics]).point(lambda v: min(255, v * WHITE // 128))
    bands = [_median([p.getchannel(c) for p in pics]) for c in range(4)]
    med = Image.merge("RGBA", bands)
    # alike in nearly every sheet: the wood, the finials, the trim - not cloth
    need = max(1, round(SAME_SHARE * len(pics)))
    count = Image.new("L", size, 0)
    rgb = med.convert("RGB")
    for p in pics:
        d = ImageChops.difference(p.convert("RGB"), rgb).split()
        far = ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2])
        count = ImageChops.add(count, far.point(lambda v: 1 if v < SAME_WITHIN else 0))
    same = count.point(lambda v: 255 if v >= need else 0) if len(pics) > 2 else Image.new("L", size, 0)
    masks = [m for m in (_mesh_mask(p, size) for p in mesh_paths) if m.getbbox()]
    cloth, panels = own_cloth(masks, same, size)
    if not panels:                       # no meshes read: whatever is not see-through and not alike everywhere
        cloth = _clean(ImageChops.subtract(bands[3].point(lambda v: 255 if v > 128 else 0), same))
        panels = panels_of(cloth)
    white = Image.merge("RGBA", (shade, shade, shade, bands[3]))
    blank = Image.composite(white, med, cloth)
    return Sheet(blank, shade, cloth, panels, len(pics))


def sheet_blank(mod):
    """The mod's white template (Sheet), or None when it has no faction banner sheets (not Medieval II). Kept
    while the sheets and meshes are unchanged."""
    from .recolour import read_picture
    paths = sheets(mod)
    if not paths:
        return None
    ms = meshes(mod)
    key = tuple((p, os.path.getmtime(p)) for p in paths + ms)
    if _CACHE.get("key") != key:
        pics = []
        for p in paths:
            try:
                pics.append(read_picture(p))
            except Exception:
                pass
        _CACHE.clear()
        _CACHE.update(key=key, sheet=make_sheet(pics, ms) if pics else None)
    return _CACHE["sheet"]


# ---------------------------------------------------------------------------
# Painting
# ---------------------------------------------------------------------------
def symbol_boxes(sheet):
    """Where the symbol goes on each panel: a square across most of its width, in its upper middle (as Rome's)."""
    out = []
    for x0, y0, x1, y1 in sheet.panels:
        bw, bh = x1 - x0, y1 - y0
        side = min(int(bw * 0.6), int(bh * 0.5))
        cx, cy = (x0 + x1) // 2, y0 + int(bh * 0.42)
        out.append((cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side))
    return out


def _colour_layer(sheet, colours, pattern):
    """RGB picture of the cloth's colours: the pattern laid on each panel on its own (worked out on a picture 4
    times smaller, then blown up)."""
    from PIL import Image
    from .banners import PATTERNS
    n, which = PATTERNS.get(pattern, PATTERNS["plain"])
    layer = Image.new("RGB", sheet.size, tuple(colours[0][:3]))
    if n == 1:
        return layer
    for x0, y0, x1, y1 in sheet.panels:
        bw, bh = max(1, (x1 - x0) // 4), max(1, (y1 - y0) // 4)
        small = Image.new("RGB", (bw, bh))
        sp = small.load()
        for y in range(bh):
            for x in range(bw):
                i = min(int(which(x / bw, min(0.999, y / bh))), len(colours) - 1)
                sp[x, y] = tuple(colours[i][:3])
        layer.paste(small.resize((x1 - x0, y1 - y0), Image.NEAREST), (x0, y0))
    return layer


def paint(sheet, colours, symbol=None, boxes=None, pattern="plain", alpha=None, strength=1.0):
    """A faction's banner sheet from the white template: the cloth dyed (one colour, or a list for a pattern of
    banners.PATTERNS on each panel), its folds kept; the symbol (RGBA, clear background; None = none) in each box,
    shaded by the cloth; alpha: the faction's old sheet's alpha ('L'), kept (else the template's)."""
    from PIL import Image, ImageChops
    from .banners import put_symbol
    colours = [colours] if isinstance(colours[0], int) else list(colours)
    col = _colour_layer(sheet, colours, pattern)
    shade = Image.merge("RGB", (sheet.shade,) * 3)
    dyed = ImageChops.multiply(col, shade).point(lambda v: min(255, v * 255 // WHITE))
    out = sheet.blank.copy()
    out.paste(dyed, (0, 0), sheet.cloth)
    if symbol is not None:
        put_symbol(out, sheet.shade, symbol, boxes if boxes is not None else symbol_boxes(sheet), strength)
    out.putalpha(alpha if alpha is not None and alpha.size == out.size else sheet.blank.getchannel("A"))
    return out


def template_picture(sheet):
    """The white template to draw on in any program: the blank with each panel's outline (thin red lines just
    outside the cloth do no harm - the game shows only the cloth)."""
    from PIL import ImageDraw
    im = sheet.blank.copy()
    dr = ImageDraw.Draw(im)
    for x0, y0, x1, y1 in sheet.panels:
        dr.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(220, 30, 30, 255))
    return im


def look_3d(mesh_file, picture, size=(220, 300)):
    """The painted sheet on a banner mesh, as the game hangs it, seen from the front (a still picture), or None."""
    from . import meshview as MV
    try:
        mesh = MV.read_file(mesh_file)
    except Exception:
        return None
    mesh.one_texture = True
    try:
        return MV.render(mesh, size=size, yaw=155.0, pitch=5.0, zoom=1.8, texture=picture.convert("RGB"))
    except Exception:
        return None


def make(sheet, s, symbol=None, alpha=None, strength=1.0):
    """A faction's sheet from the window's settings s (as banners.make): dyed in the pattern, or the player's own
    drawing in its place; the symbol unless 'no_symbol'; alpha: the faction's old sheet's, kept."""
    from .banners import own_drawing, put_symbol
    sym = None if s.get("no_symbol") else symbol
    boxes = s.get("boxes") or symbol_boxes(sheet)
    if not s.get("drawing"):
        return paint(sheet, s.get("colours") or [(200, 200, 200)], sym, boxes, s.get("pattern") or "plain", alpha,
                     strength)
    out = own_drawing(s["drawing"], sheet.size)
    if sym is not None:
        put_symbol(out, sheet.shade, sym, boxes, strength)
    out.putalpha(alpha if alpha is not None and alpha.size == out.size else sheet.blank.getchannel("A"))
    return out


class Kit:
    """What the banner window works with, for Medieval II: one white template (every faction's sheet has the same
    layout), its panels, the sheet made from the settings; the second view = the banner in 3D on its mesh."""
    game = "Medieval II"
    side_label = "in the game (3D)"

    def __init__(self, sheet, mesh_files=(), alpha=None):
        self.sheet, self.alpha = sheet, alpha
        self.meshes = {os.path.splitext(os.path.basename(p))[0]: p for p in mesh_files
                       if os.path.basename(p).lower().startswith("main_")}
        self.mesh = "main_infantry" if "main_infantry" in self.meshes else next(iter(self.meshes), None)
        self.shapes = {"Medieval II": sheet.blank}

    def blank(self, s):
        return self.sheet.blank

    def banners(self, s):
        return self.sheet.panels

    def symbol_boxes(self, s):
        return s.get("boxes") or symbol_boxes(self.sheet)

    def make(self, s, symbol=None, strength=1.0):
        return make(self.sheet, s, symbol, self.alpha, strength)

    def side(self, s, symbol=None, size=(220, 300)):
        if not self.mesh:
            return None
        return look_3d(self.meshes[self.mesh], self.make(s, symbol), size)

    def template(self, s):
        return template_picture(self.sheet)


__all__ = ["sheets", "meshes", "main_mesh", "Sheet", "make_sheet", "sheet_blank", "panels_of", "symbol_boxes",
           "paint", "template_picture", "look_3d", "faction_sheet", "make", "Kit"]
