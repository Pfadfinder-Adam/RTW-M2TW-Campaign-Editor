"""Recolour freely (a modder on Discord, 2026-10-22: 'recolour the textures through the tool'): ANY picture of either
game - a battle texture, a campaign-map figure's texture, a unit card, a button - with colours the modder picks on
it, not only the faction's colours (Recolour does those). One change = a colour clicked on the picture ('from'), how
alike a colour may be and still count, everywhere or only the area joined to the click, and the new colour ('to');
several changes in a row (a red tunic blue, a brown shield green), each worked out on the picture as it came, so
two changes never chain. Light and shade are kept the way Recolour keeps them (recolour._shift and its black /
white helpers): a dark fold of a red cloak becomes a dark fold of a blue one. Brush touch-ups add to a change's area
or keep pixels out of it.

Written as the picture was (format, depth, DDS compression and mipmaps, Medieval II's 48-byte .texture head -
recolour.picture_bytes). Where: the picture itself in the mod (a file of the game's data under a mod with only its
changes: the mod's own copy, the game's file untouched - plan.binary); a battle texture that is the game's own
original is never written over (rules.md, the tester's 'bare skeletons'): a copy beside it, every model line naming
it pointed at the copy; or only for one unit's soldiers / officer: a model of its own (models.own_files), the other
units keep their look. Pillow only, whole bands with lookup tables."""

import os

from . import recolour as R

ALIKE = 30                      # the default 'alike' (0..100)
PLAIN_SAT = 0.18                # a picked colour less saturated than this has no hue to look for: grey, white, black


def _gap(alike):
    """How far (of the colour wheel, 0..0.5) a hue may lie from the picked one at this 'alike'."""
    return 0.01 + 0.19 * max(0, min(100, alike)) / 100.0


def pick_mask(im, colour, alike=ALIKE, at=None):
    """The 'L' mask (255 = changed, soft at the edge) of the pixels of im like colour: a coloured pick takes every
    pixel of a near hue that is coloured enough (its shades and folds: the light and dark of a red tunic; skin left
    out unless the pick is a skin tone itself), a grey /
    white / black pick the dull pixels of a near lightness. at (x, y): only the area joined to that point. Clear
    pixels never count."""
    from PIL import Image, ImageChops, ImageDraw
    rgba = im.convert("RGBA")
    H, S, V = rgba.convert("RGB").convert("HSV").split()
    h0, s0, v0 = R.hsv(colour)
    a = max(0, min(100, alike)) / 100.0
    if s0 >= PLAIN_SAT:
        gap = _gap(alike) * 255
        c = int(round(h0 * 255))
        soft = gap * 0.3

        def hue(h):
            d = min(abs(h - c), 256 - abs(h - c))
            if d <= gap - soft:
                return 255
            return 0 if d >= gap else int(255 * (gap - d) / max(soft, 1))
        floor = max(0.06, s0 * (0.55 - 0.45 * a)) * 255        # duller than this: not this colour any more
        m = ImageChops.multiply(H.point(hue), S.point(lambda s: 255 if s >= floor else int(255 * s / max(floor, 1))))
        m = ImageChops.multiply(m, V.point(lambda v: 255 if v >= 0.05 * 255 else 0))
        if not R._skin_colour(colour):                          # faces and hands stay (a red near an orange skin)
            m = ImageChops.subtract(m, R._skin(H, S, V))
    else:
        top = (PLAIN_SAT + 0.25 * a) * 255
        reach = (0.08 + 0.5 * a) * 255
        vv = v0 * 255
        m = ImageChops.multiply(S.point(lambda s: 255 if s <= top else 0),
                                V.point(lambda v: 255 if abs(v - vv) <= reach else 0))
    m = ImageChops.multiply(m, rgba.split()[3].point(lambda x: 255 if x else 0))
    if at is not None:
        x, y = int(at[0]), int(at[1])
        w, h = m.size
        if not (0 <= x < w and 0 <= y < h) or not m.getpixel((x, y)):
            return Image.new("L", m.size, 0)
        solid = m.point(lambda v: 255 if v else 0)
        ImageDraw.floodfill(solid, (x, y), 128)                 # the joined area by its sides
        joined = solid.point(lambda v: 255 if v == 128 else 0)
        m = ImageChops.multiply(m, joined)
    return m


def swap(frm, to, alike=ALIKE, at=None):
    """One change: from the colour frm (picked on the picture) to the colour to; at: only the area joined there."""
    return {"from": tuple(frm), "to": tuple(to), "alike": int(alike), "at": tuple(at) if at else None,
            "add": None, "keep": None}


def mask_of(im, sw):
    """The change's area on the picture as it came: its colour test, + what the brush added, - what it kept out."""
    from PIL import ImageChops
    m = pick_mask(im, sw["from"], sw.get("alike", ALIKE), sw.get("at"))
    if sw.get("add") is not None:
        m = ImageChops.lighter(m, sw["add"])
    if sw.get("keep") is not None:
        m = ImageChops.subtract(m, sw["keep"])
    return m


def changed(im, swaps):
    """(new picture, share of pixels changed): every change laid on im in turn, each one's area found on im as it
    came (red -> blue and blue -> red swap the two); alpha kept."""
    from PIL import Image, ImageChops
    rgb = im.convert("RGB")
    out = rgb.copy()
    took = Image.new("L", im.size, 0)
    for sw in swaps:
        frm, to = sw["from"], sw["to"]
        if tuple(frm) == tuple(to):
            continue
        m = mask_of(im, sw)
        if not m.getbbox():
            continue
        if R._plain(to) and R._plain(frm) != R._plain(to):
            part = R._to_plain(rgb, m, to, frm)
        elif R._plain(to):
            part = _same_kind_plain(rgb, frm, to)
        elif R.hsv(frm)[1] < PLAIN_SAT:
            part = R._shift_plain(rgb, m, to)
        else:
            part = R._shift(rgb, frm, to)
        out.paste(part, (0, 0), m)
        if sw.get("add") is not None and not R._plain(to) and R.hsv(frm)[1] >= PLAIN_SAT:
            # a grey or white the brush took in has no hue to turn: it is given the new colour, its light kept
            dull = ImageChops.multiply(sw["add"], rgb.convert("HSV").split()[1].point(
                lambda v: 255 if v < PLAIN_SAT * 255 else 0))
            if sw.get("keep") is not None:
                dull = ImageChops.subtract(dull, sw["keep"])
            if dull.getbbox():
                out.paste(R._shift_plain(rgb, dull, to), (0, 0), dull)
        took = ImageChops.lighter(took, m)
    if im.mode in ("RGBA", "LA", "P"):
        out = out.convert("RGBA")
        out.putalpha(im.convert("RGBA").split()[3])
    n = sum(took.point(lambda v: 255 if v >= 128 else 0).histogram()[255:])
    return out, n / float(im.size[0] * im.size[1])


def _same_kind_plain(rgb, frm, to):
    """Grey to another grey (a white made greyer, a black lighter): the light scaled, no hue."""
    from PIL import Image
    H, S, V = rgb.convert("HSV").split()
    k = R.hsv(to)[2] / max(R.hsv(frm)[2], 0.05)
    return Image.merge("HSV", (H, Image.new("L", rgb.size, 0), V.point(lambda v: min(255, int(v * k))))).convert("RGB")


def hsl_target(frm, hue=0, sat=100, light=100):
    """The 'to' colour made from frm by the sliders: the hue turned by hue degrees, the saturation and the lightness
    as a share (%) of frm's."""
    import colorsys
    h, s, v = R.hsv(frm)
    h = (h + hue / 360.0) % 1.0
    s = max(0.0, min(1.0, s * sat / 100.0))
    v = max(0.0, min(1.0, v * light / 100.0))
    return tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, s, v))


# ---- where the picture is written ----
def _data_rel(mod, path):
    """The picture's path inside a data folder (the mod's, else the game's), '/'-separated, or None."""
    from .campaignrules import game_data
    for base in (mod.data, game_data(mod)):
        if not base:
            continue
        rel = os.path.relpath(os.path.abspath(path), os.path.abspath(base))
        if not rel.startswith("..") and not os.path.isabs(rel):
            return rel.replace("\\", "/")
    return None


def wearers(mod, path):
    """[(model info, faction or '', kind 'texture' / 'attach')] of every battle model line naming the picture."""
    from .models import catalogue
    want = os.path.normcase(os.path.abspath(path))
    out = []
    for info in catalogue(mod).values():
        for kind, table in (("texture", info.textures), ("attach", info.attach)):
            for f, ref in table.items():
                got = R._texture_file(mod, ref) if ref else None
                if not got:
                    from .meshview import on_disk
                    disk = on_disk(mod, ref) if ref else None
                    got = disk[1] if disk else None
                if got and os.path.normcase(os.path.abspath(got)) == want:
                    out.append((info, f, kind))
    return out


def _free_copy(mod, path):
    """(path of the copy in the mod, the word added to the name: '_own', '_own_2'...) beside a game's own texture."""
    rel = _data_rel(mod, path) or os.path.basename(path)
    folder, base = rel.rsplit("/", 1) if "/" in rel else ("", rel)
    stem, dot, ext = base.partition(".")
    n, add = 1, "_own"

    def at(a):
        return os.path.join(mod.data, *[p for p in (folder + "/" + stem + a + dot + ext).split("/") if p])
    while os.path.exists(at(add)):
        n += 1
        add = "_own_%d" % n
    return at(add), add


def _renamed(ref, add):
    """ref (as a model line writes it) with add after its name's stem: x.tga -> x_own.tga, the folder kept."""
    ref = ref.replace("\\", "/")
    folder, base = ref.rsplit("/", 1) if "/" in ref else ("", ref)
    stem, dot, ext = base.partition(".")
    return (folder + "/" if folder else "") + stem + add + dot + ext


def plan_free(plan, path, swaps, crop=None, unit=None):
    """The recoloured picture into the plan (backup, Restore). crop (x, y, w, h): a part of a sheet, the rest kept.
    unit (unit, 'soldier' / 'officer', index, faction or '*'): only that unit's line wears it - a model of its own
    (models.own_files). -> the share of the picture changed (0: nothing in it took a change - nothing written)."""
    import tempfile
    mod = plan.mod
    whole = R.read_picture(path)
    im = whole.crop((crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3])) if crop else whole
    new, share = changed(im, swaps)
    if share <= 0:
        plan.note(None, "%s: no part took a change - nothing written" % os.path.basename(path))
        return 0.0
    if crop:
        whole = whole.copy()
        whole.paste(new, (crop[0], crop[1]))
        new = whole
    words = "; ".join("%s -> %s" % (R._words([s["from"]]), R._words([s["to"]])) for s in swaps)
    if unit:
        from .models import own_files
        u, key, idx, fac = unit
        tmp = os.path.join(tempfile.mkdtemp(prefix="freecolour_"), "picture.png")
        new.save(tmp)
        kinds = {k for _, f, k in wearers(mod, path)}
        if kinds == {"attach"}:
            own_files(plan, u, key, idx, attach=tmp)
        else:
            own_files(plan, u, key, idx, textures={fac or "*": tmp})
        plan.note(None, "%s recoloured for %s only (%s)" % (os.path.basename(path), u, words))
        return share
    data = R.picture_bytes(new, path)
    worn = wearers(mod, path)
    inside = os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(mod.data)) + os.sep)
    if worn and (not inside or R._games_file(mod, path)):
        # the game's own battle texture: a copy beside it, every line naming it pointed there (never written over)
        from .models import _set_shared_texture, set_faction_texture
        dest, add = _free_copy(mod, path)
        plan.binary(dest, data)
        for info, f, kind in worn:
            ref = _renamed((info.textures if kind == "texture" else info.attach)[f], add)
            if f:
                set_faction_texture(plan, info, f, ref, kind)
            else:
                _set_shared_texture(plan, info, ref, kind)
        plan.note(None, "%s recoloured as a copy, %s (%s); the game's own file stays as it was" % (
            os.path.basename(path), os.path.basename(dest), words))
    else:
        plan.binary(path, data)
        plan.note(None, "%s recoloured (%s)" % (os.path.basename(path), words))
    return share


__all__ = ["pick_mask", "swap", "mask_of", "changed", "hsl_target", "wearers", "plan_free"]
