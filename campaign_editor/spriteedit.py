"""Sprite sheets made editable (Wholesome Queen's campaign UI editor showed the wish; the user, 2026-10-21: 'yes,
in order'): a sprite's picture or a whole page replaced, written into the mod's own copy of the page (the game's
own folder is never touched). The page keeps its size and every other sprite's pixels; the sprite takes the box the
sheet gives it (tw / th on an engine's HD sheet). With a binary sheet (.rsd / .sd - the plain games, an engine on
'sd') the page's click mask in the sheet follows the new picture (the game reads the mask there); an .sd.xml sheet
has none (the engine takes it from the picture). Both games."""

import os

from . import spritesheet as SS
from . import symbols as SY


def fit(pic, size, how="stretch"):
    """pic (Pillow) made size: 'stretch' fills the box, 'fit' keeps its shape (the rest clear), 'crop' fills it and
    cuts what is over."""
    from PIL import Image
    pic = pic.convert("RGBA")
    w, h = size
    if how == "stretch" or not pic.width or not pic.height:
        return pic.resize((w, h), Image.LANCZOS)
    scale = (min if how == "fit" else max)(w / pic.width, h / pic.height)
    sw, sh = max(1, round(pic.width * scale)), max(1, round(pic.height * scale))
    big = pic.resize((sw, sh), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(big, ((w - sw) // 2, (h - sh) // 2))
    return out


def put_sprite(page, box, pic, how="stretch"):
    """The page (Pillow RGBA) with pic in the sprite's box (x, y, w, h): the box cleared first, so a picture with
    clear parts leaves nothing of the old one; the rest of the page as it was."""
    from PIL import Image
    x, y, w, h = box
    out = page.convert("RGBA").copy()
    out.paste(Image.new("RGBA", (w, h), (0, 0, 0, 0)), (x, y))
    out.paste(fit(pic, (w, h), how), (x, y))
    return out


def page_target(mod, culture, page):
    """Where the mod's own copy of a page goes: ui/<culture>/interface/<page>, or ui/<page> for a page lying in ui
    itself (culture '')."""
    parts = ["ui", culture, "interface", page] if culture else ["ui", page]
    return os.path.join(mod.data, *parts)


def write(plan, mod, sheet, changes):
    """The changed pages into the plan: changes = {(page, culture): Pillow picture}. Each page the size it was (a
    picture of another size is refused - the sheet's boxes stand on it); a binary sheet gets the new click masks."""
    from .factionart import image_tga
    from .recolour import read_picture
    masks = {}
    for (page, culture), im in sorted(changes.items(), key=lambda kv: kv[0]):
        source = dict(SY.page_cultures(mod, page)).get(culture)
        if source:
            size = read_picture(source).size
            if im.size != size:
                raise ValueError("%s: the page is %d x %d, the picture %d x %d - a page keeps its size"
                                 % (page, size[0], size[1], im.size[0], im.size[1]))
        target = page_target(mod, culture, page)
        if target.lower().endswith((".dds", ".texture")):
            import tempfile
            from .factionart import replace_picture
            with tempfile.TemporaryDirectory() as t:
                tmp = os.path.join(t, "page.png")
                im.save(tmp)
                replace_picture(plan, tmp, target, source)
        else:
            plan.binary(target, image_tga(im, source if source and source.lower().endswith(".tga") else None))
        plan.notes.append((mod.rel(target), "sprite sheet %s: page %s%s replaced" % (
            sheet["name"], page, " (%s)" % culture if culture else "")))
        masks.setdefault(page, im)
    if sheet["kind"] == "binary" and masks:
        with open(sheet["path"], "rb") as fh:
            sh = SS.read(fh.read())
        for page, im in masks.items():
            if sh.page_index(page) is not None:
                SS.set_page(sh, page, im)
        mine = os.path.join(mod.data, "ui", os.path.basename(sheet["path"]))
        plan.binary(mine, SS.write(sh))
        plan.notes.append((mod.rel(mine), "the click masks of %d page(s) follow their new pictures" % len(masks)))
    return plan


__all__ = ["fit", "put_sprite", "page_target", "write"]
