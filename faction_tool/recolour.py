"""Recolour a faction's pictures: the parts painted in one faction's colours (its primary and secondary colour in
descr_sm_factions.txt) get another faction's colours, the light and shade kept. Both games, every picture that
carries the colours: unit cards and info pictures, battle textures of the units, campaign-map figures, symbols,
banners, captain banners, loading-screen symbols.

How a part is found: a pixel is a 'colour part' when it is coloured (saturation, not too dark) and its hue is near
the source primary or secondary colour; where the same picture exists for other factions (the same unit card or
texture in another faction's colours), only the pixels that differ between them count - faces, metal and leather
stay as they are. The new colour takes the target's hue; saturation and brightness move by the ratio between the
target and the source colour, so a dark fold of a red cloak becomes a dark fold of a blue one.

Pillow only (the exe has no numpy): the work is done on whole bands with lookup tables, a 1024 x 1024 texture in
well under a second."""

import colorsys
import os
import re

from .textio import tokens

RE_RGB = re.compile(r"red\s+(\d+)\s*,\s*green\s+(\d+)\s*,\s*blue\s+(\d+)", re.I)
SAT_MIN = 0.28          # below: grey, white, skin - not a faction colour
SAT_REL = 0.5           # a part must be at least this share as saturated as the source colour
VAL_MIN = 0.10          # below: shadow
HUE_GAP = 0.10          # how far (of the colour wheel, 0..0.5) a pixel's hue may lie from the source colour
DIFF = 40               # a pixel that differs from the other factions' copy by more counts as a colour part
DIFF_MOST = 0.45        # over this share of differing pixels the copies are different pictures: hue alone


def faction_colours(mod):
    """{faction: (primary (r, g, b), secondary (r, g, b) or None)} from descr_sm_factions.txt."""
    out, cur = {}, None
    p = mod.file("sm_factions")
    for l in mod.load(p).texts() if p else []:
        t = tokens(l)
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1]
            out[cur] = [None, None]
        elif cur and t[:1] in (["primary_colour"], ["secondary_colour"]):
            m = RE_RGB.search(l)
            if m:
                out[cur][0 if t[0] == "primary_colour" else 1] = tuple(int(x) for x in m.groups())
    return {k: (v[0], v[1]) for k, v in out.items() if v[0]}


def hsv(rgb):
    return colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])


def coloured(rgb):
    """Whether a colour has a hue to look for (not white, grey or black)."""
    h, s, v = hsv(rgb)
    return s >= SAT_MIN and v >= VAL_MIN


def _hue_dist_lut(h0):
    """A lookup table: Pillow hue (0..255) -> distance to h0 on the wheel, 0..128."""
    c = int(round(h0 * 255))
    return [min(abs(h - c), 256 - abs(h - c)) for h in range(256)]


def _near(a, b):
    """Whether two colours have hues near each other (both coloured)."""
    if not a or not b or not coloured(a) or not coloured(b):
        return False
    d = abs(hsv(a)[0] - hsv(b)[0]) % 1.0
    return min(d, 1 - d) <= HUE_GAP * 1.5


def masks(im, source, others=()):
    """[mask of the primary's parts, mask of the secondary's parts] ('L' images, 255 = recolour) of a picture.
    source = (primary, secondary); a source colour without a hue gives an empty mask. others: [(the same picture in
    another faction's colours, that faction's (primary, secondary))] - a pixel counts only where it differs from
    every other copy whose faction does not wear a colour like it (Denmark's red says nothing about England's red)."""
    from PIL import Image, ImageChops
    rgb = im.convert("RGB")
    H, S, V = rgb.convert("HSV").split()
    lit = V.point(lambda v: 255 if v >= VAL_MIN * 255 else 0)
    diffs = []
    for o, cols in others:
        if o is None or o.size != im.size:
            continue
        d = ImageChops.difference(rgb, o.convert("RGB")).split()
        d = ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2]).point(lambda x: 255 if x > DIFF else 0)
        diffs.append((d, cols or ()))
    gap = int(HUE_GAP * 255)
    dists = [H.point(_hue_dist_lut(hsv(c)[0])) if c and coloured(c) else None for c in source]
    out = []
    for k, d in enumerate(dists):
        if d is None:
            out.append(Image.new("L", im.size, 0))
            continue
        smin = max(SAT_MIN, hsv(source[k])[1] * SAT_REL) * 255     # a dull brown is not a bright red
        m = ImageChops.multiply(lit, S.point(lambda s: 255 if s >= smin else 0))
        m = ImageChops.multiply(m, d.point(lambda x: 255 if x <= gap else 0))
        other = dists[1 - k] if len(dists) > 1 else None
        if other is not None:                    # near both: the nearer one takes it (the primary on a tie)
            closer = ImageChops.subtract(d, other) if k == 0 else ImageChops.subtract(d, other, 1, -1)
            m = ImageChops.multiply(m, closer.point(lambda x: 255 if x == 0 else 0))
        use = [dd for dd, cols in diffs if not any(_near(source[k], c) for c in cols)]
        if use:
            diff = use[0]
            for dd in use[1:]:
                diff = ImageChops.multiply(diff, dd)
            share = diff.histogram()[255] / float(im.size[0] * im.size[1])
            if 0 < share <= DIFF_MOST:
                m = ImageChops.multiply(m, diff)
        out.append(m)
    return out


def _shift(im, src, dst):
    """The whole picture moved from colour src to colour dst (hue set, saturation and brightness scaled)."""
    from PIL import Image
    H, S, V = im.convert("RGB").convert("HSV").split()
    sh, ss, sv = hsv(src)
    th, ts, tv = hsv(dst)
    ks = ts / max(ss, 0.05)
    kv = tv / max(sv, 0.05)
    H = Image.new("L", im.size, int(round(th * 255)) % 256)
    S = S.point(lambda s: min(255, int(s * ks)))
    V = V.point(lambda v: min(255, int(v * kv)))
    return Image.merge("HSV", (H, S, V)).convert("RGB")


def recolour(im, source, target, others=()):
    """(new picture, share of pixels changed): im with the parts in the source colours (primary, secondary) in the
    target colours, alpha kept."""
    from PIL import Image
    ms = masks(im, source, others)
    rgb = im.convert("RGB")
    out = rgb.copy()
    n = 0
    for m, src, dst in zip(ms, source, target):
        if not src or not dst or not m.getbbox():
            continue
        out.paste(_shift(rgb, src, dst), (0, 0), m)
        n += m.histogram()[255]
    if im.mode in ("RGBA", "LA", "P"):
        a = im.convert("RGBA").split()[3]
        out = out.convert("RGBA")
        out.putalpha(a)
    return out, n / float(im.size[0] * im.size[1])


def guess_source(mod, faction, items, colours=None):
    """The faction whose colours the pictures carry now ((primary, secondary), name). A faction cloned from a
    template has copies of the template's unit cards (the same pictures, byte for byte or nearly): the faction whose
    cards most of ours equal is the source. When none does, the pictures are the faction's own: its own colours."""
    from PIL import ImageChops, ImageStat
    colours = colours or faction_colours(mod)
    votes, looked = {}, 0
    for it in [x for x in items if not isinstance(x, str) and x.get("of")][:40]:
        try:
            im = read_picture(it["path"]).convert("RGB")
        except Exception:
            continue
        looked += 1
        for (p, _), f in zip(it["others"], it["of"]):
            try:
                o = read_picture(p).convert("RGB")
            except Exception:
                continue
            if o.size == im.size and max(ImageStat.Stat(ImageChops.difference(im, o)).mean) < 2.0:
                votes[f] = votes.get(f, 0) + 1
    if votes:
        f, n = max(votes.items(), key=lambda kv: kv[1])
        if n >= max(2, looked * 0.3) and f in colours and colours[f] != colours.get(faction):
            return colours[f], f
    return colours.get(faction, ((200, 0, 0), None)), faction


__all__ = ["faction_colours", "masks", "recolour", "guess_source", "coloured"]


# ---------------------------------------------------------------------------
# Which pictures of a faction carry its colours, and writing them back in their own format
# ---------------------------------------------------------------------------
PICTURE_EXT = (".tga", ".dds", ".texture", ".png")


def read_picture(path):
    """A picture file as a Pillow image (RGBA): .tga, .dds, .tga.dds, Medieval II's .texture (48 bytes, then DDS)."""
    import io
    from PIL import Image
    with open(path, "rb") as fh:
        data = fh.read()
    if path.lower().endswith(".texture") and data[48:52] == b"DDS ":
        data = data[48:]
    return Image.open(io.BytesIO(data)).convert("RGBA")


def picture_bytes(im, like):
    """im as the bytes of a file like `like` (same format, depth, DDS compression and mipmaps; a .texture keeps
    its 48-byte header)."""
    import os as _os
    import tempfile
    from .factionart import image_dds, image_tga
    low = like.lower()
    if low.endswith(".texture"):
        with open(like, "rb") as fh:
            data = fh.read()
        head, dds = data[:48], data[48:]
        fd, tmp = tempfile.mkstemp(suffix=".dds")
        try:
            with _os.fdopen(fd, "wb") as fh:
                fh.write(dds)
            return head + image_dds(im, tmp)
        finally:
            _os.remove(tmp)
    if low.endswith(".dds"):
        return image_dds(im, like)
    if low.endswith(".png"):
        import io
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()
    return image_tga(im, like)


def _others_named(path, faction, factions, colours):
    """[(path, colours)] of the same picture named after other factions (england -> france in the name or folder)."""
    out = []
    for f in factions:
        if f == faction or f not in colours:
            continue
        p = re.sub(r"(?i)(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(faction), f, path)
        if p != path and os.path.isfile(p):
            out.append((p, colours[f]))
    return out


def targets(mod, campaign, faction):
    """[{'path', 'rel', 'group', 'label', 'others': [(path, colours)], 'crop': box or None, 'skip': why or None}]:
    every picture of the faction that carries its colours. Groups: 'unit cards', 'unit textures', 'symbols and
    banners' (the Art tab's pictures: flags, banners, campaign-map figures, loading symbols...)."""
    from .moddata import _ci
    colours = faction_colours(mod)
    names = [n for n, _ in mod.factions()]
    out, seen = [], set()

    def add(path, group, label, others=(), crop=None, skip=None, of=()):
        k = (os.path.normcase(os.path.abspath(path)), crop)
        if k in seen:
            return
        seen.add(k)
        out.append({"path": path, "rel": mod.rel(path), "group": group, "label": label, "others": list(others),
                    "of": list(of), "crop": crop, "skip": skip})
    for sub, label in (("units", "unit card"), ("unit_info", "unit info picture")):
        d = _ci(_ci(mod.data, "ui") or "", sub) if _ci(mod.data, "ui") else None
        own = _ci(d, faction) if d else None
        if not own:
            continue
        for n in sorted(os.listdir(own)):
            if n.lower().endswith(PICTURE_EXT):
                p = os.path.join(own, n)
                fs = [f for f in names if f != faction and f in colours and os.path.isfile(os.path.join(d, f, n))]
                add(p, "unit cards", "%s %s" % (label, n), [(os.path.join(d, f, n), colours[f]) for f in fs],
                    of=fs)
    # battle textures: the model's texture for this faction; a file other factions wear too is left alone
    try:
        from .models import catalogue
        from .meshview import on_disk
        cat = catalogue(mod)
    except Exception:
        cat = {}
    for name, info in sorted(cat.items()):
        rel = info.textures.get(faction)
        if not rel:
            continue
        got = on_disk(mod, rel)
        wearers = sorted(f for f, r in info.textures.items() if f != faction and r.lower() == rel.lower())
        if not got:
            continue
        inside = os.path.normcase(os.path.abspath(got[1])).startswith(os.path.normcase(os.path.abspath(mod.data)))
        skip = ("worn by %s too - recolouring it would change them as well" % ", ".join(wearers[:4])) if wearers else \
            (None if inside else "the game's own file (not in this mod) - copy the model into the mod first")
        others = [(on_disk(mod, r)[1], colours[f]) for f, r in info.textures.items()
                  if f != faction and f in colours and r.lower() != rel.lower() and on_disk(mod, r)]
        add(got[1], "unit textures", "battle texture of %s" % info.name, others[:6], skip=skip)
    # the Art tab's pictures
    try:
        from .factionart import faction_pictures
        arts = faction_pictures(mod, campaign, faction)
    except Exception:
        arts = []
    for e in arts:
        p = e.get("path")
        if not p or not os.path.isfile(p) or not p.lower().endswith(PICTURE_EXT):
            continue
        low = (e.get("label") or "").lower()
        if " map" in low or low.startswith("map") or "leader picture" in low:
            continue                        # maps colour land, not the faction's dress; a leader's face stays
        skip = None
        if e.get("shared"):
            skip = "shared with %s - give the faction its own picture on the Art tab first" % ", ".join(e["shared"][:4])
        elif e.get("locked") or (e.get("crop") and "shared" in (e.get("note") or "")):
            skip = e.get("note")
        add(p, "symbols and banners", e.get("label") or mod.rel(p),
            [] if e.get("crop") else _others_named(p, faction, names, colours), crop=tuple(e["crop"])
            if e.get("crop") else None, skip=skip)
    return out


def plan_recolour(plan, items, source, target):
    """Write every item (from targets()) recoloured from source to target colours into the plan (backup, Restore).
    Returns [(item, share changed or the reason it was left)]."""
    from PIL import Image
    done = []
    sheets = {}
    for it in items:
        if it.get("skip"):
            done.append((it, it["skip"]))
            continue
        try:
            if it.get("crop"):
                sheet = sheets.get(it["path"]) or read_picture(it["path"])
                x, y, w, h = it["crop"]
                part = sheet.crop((x, y, x + w, y + h))
                new, share = recolour(part, source, target)
                sheet.paste(new, (x, y))
                sheets[it["path"]] = sheet
            else:
                im = read_picture(it["path"])
                others = []
                for p, c in it.get("others") or []:
                    try:
                        others.append((read_picture(p), c))
                    except Exception:
                        pass
                new, share = recolour(im, source, target, others)
                if share > 0:
                    plan.binary(it["path"], picture_bytes(new, it["path"]))
            done.append((it, share))
        except Exception as e:
            done.append((it, "could not be read or written (%s)" % e))
    for path, sheet in sheets.items():
        plan.binary(path, picture_bytes(sheet, path))
    n = sum(1 for _, s in done if isinstance(s, float) and s > 0)
    plan.note(None, "%d picture(s) recoloured: %s -> %s" % (n, _words(source), _words(target)))
    return done


def _words(cols):
    return " / ".join("%d,%d,%d" % c for c in cols if c)


__all__ += ["targets", "plan_recolour", "read_picture", "picture_bytes"]
