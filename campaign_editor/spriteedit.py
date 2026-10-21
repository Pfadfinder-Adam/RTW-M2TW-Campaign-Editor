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
        mine = os.path.join(mod.data, "ui", os.path.basename(sheet["path"]))
        sh = SS.read(_sheet_now(plan, mine, sheet["path"]))
        for page, im in masks.items():
            if sh.page_index(page) is not None:
                SS.set_page(sh, page, im)
        plan.binary(mine, SS.write(sh))
        plan.notes.append((mod.rel(mine), "the click masks of %d page(s) follow their new pictures" % len(masks)))
    return plan


def _now(plan, path):
    """A file's bytes as the plan leaves them (a change queued before), else as on the disk."""
    if path in plan.binaries:
        return plan.binaries[path]
    with open(path, "rb") as fh:
        return fh.read()


def _sheet_now(plan, mine, path):
    """A sheet as the plan leaves it: the mod's own copy (queued or on the disk), else the one read (the game's)."""
    return _now(plan, mine) if (mine in plan.binaries or os.path.exists(mine)) else _now(plan, path)


def _xml_box(text, name, box, shown):
    """The sprite tag of name in an .sd.xml text with its place and size: x / y, w / h the size shown, tw / th the
    picture's box (written only when it differs from the size shown, taken out else); the other attributes and
    every other byte as they were."""
    import re
    x, y, w, h = box
    sw, sh = shown or (w, h)

    def fix(m):
        tag = m.group(0)

        def put(tag, key, val):
            pat = re.compile(r'(\b%s\s*=\s*")[^"]*(")' % key)
            if val is None:
                return re.sub(r'\s+%s\s*=\s*"[^"]*"' % key, "", tag)
            if pat.search(tag):
                return pat.sub(lambda k: k.group(1) + str(val) + k.group(2), tag, count=1)
            end = tag.rstrip("/>").rstrip()
            return end + ' %s="%s"' % (key, val) + tag[len(end):]
        for key, val in (("x", x), ("y", y), ("w", sw), ("h", sh)):
            tag = put(tag, key, val)
        same = (sw, sh) == (w, h)
        tag = put(tag, "tw", None if same else w)
        tag = put(tag, "th", None if same else h)
        return tag
    pat = re.compile(r'<sprite\b[^>]*\bname="%s"[^>]*/?>' % re.escape(name))
    new, n = pat.subn(fix, text, count=1)
    if not n:
        raise ValueError("no sprite %s in the sheet" % name)
    return new


def set_box(plan, mod, sheet, name, box, shown=None):
    """The sprite name's box on its page (x, y, w, h - the picture it shows) and, on an .sd.xml sheet, the size the
    game shows it at (shown: (w, h); the engines stretch the picture to it - Medieval II with M2EX, Rome with REX in
    'sprite_format xml'). The sheet the game reads is changed, and its twin (the other of .rsd / .sd.xml) when the
    sprite is in it too, so a switch of sprite_format finds it the same. Written into the mod's own ui folder."""
    files = [sheet["path"]] + ([sheet["other"]] if sheet.get("other") else [])
    done = 0
    for path in files:
        mine = os.path.join(mod.data, "ui", os.path.basename(path))
        data = _sheet_now(plan, mine, path)
        if path.lower().endswith(".xml"):
            try:
                text = _xml_box(data.decode("latin-1"), name, box, shown)
            except ValueError:
                continue
            plan.binary(mine, text.encode("latin-1"))
        else:
            sh = SS.read(data)
            s = next((s for s in sh.sprites if s["name"] == name), None)
            if s is None:
                continue
            SS.set_sprite(sh, name, s["page"], *box)
            plan.binary(mine, SS.write(sh))
        done += 1
        plan.notes.append((mod.rel(mine), "sprite %s: at %d, %d, %d x %d%s" % (
            name, box[0], box[1], box[2], box[3], " shown %d x %d" % tuple(shown) if shown and tuple(shown) !=
            tuple(box[2:]) else "")))
    if not done:
        raise ValueError("no sprite %s in %s" % (name, sheet["name"]))
    return plan


__all__ = ["fit", "put_sprite", "page_target", "write", "set_box"]
