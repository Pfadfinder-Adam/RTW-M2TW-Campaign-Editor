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


def _plain(rgb):
    """A colour with no hue to look for: 'dark' (black, near black), 'light' (white, near white), 'grey', or None."""
    if not rgb or coloured(rgb):
        return None
    v = hsv(rgb)[2]
    return "dark" if v < 0.35 else "light" if v > 0.7 else "grey"


def _like(a, b):
    """Whether two faction colours look alike (near hues, or both black / both white / both grey)."""
    pa = _plain(a)
    return _near(a, b) or (pa is not None and pa == _plain(b))


def _plain_mask(S, V, kind):
    """Where a pixel could be painted in a colour of that kind: dark and dull, light and dull, or mid grey."""
    from PIL import ImageChops
    dull = S.point(lambda s: 255 if s < 0.30 * 255 else 0)
    if kind == "dark":
        val = V.point(lambda v: 255 if v < 0.42 * 255 else 0)
    elif kind == "light":
        val = V.point(lambda v: 255 if v > 0.58 * 255 else 0)
    else:
        val = V.point(lambda v: 255 if 0.25 * 255 < v < 0.8 * 255 else 0)
    return ImageChops.multiply(dull, val)


def masks(im, source, others=(), plain=True):
    """[mask of the primary's parts, mask of the secondary's parts] ('L' images, 255 = recolour) of a picture.
    source = (primary, secondary); a source colour without a hue gives an empty mask. others: [(the same picture in
    another faction's colours, that faction's (primary, secondary))] - a pixel counts only where it differs from
    every other copy whose faction does not wear a colour like it (Denmark's red says nothing about England's red)."""
    from PIL import ImageChops
    rgb = im.convert("RGB")
    H, S, V = rgb.convert("HSV").split()
    lit = V.point(lambda v: 255 if v >= VAL_MIN * 255 else 0)
    diffs = []
    # how far a pixel must differ: DIFF in the light, less in the shade (a dark green and a dark blue fold are
    # near in numbers though plainly other colours - the shaded half of a cloak stayed in the old colour)
    need = V.point(lambda v: max(12, min(DIFF, int(v * 0.4))))
    for o, cols in others:
        if o is None or o.size != im.size:
            continue
        d = ImageChops.difference(rgb, o.convert("RGB")).split()
        d = ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2])
        d = ImageChops.subtract(d, need).point(lambda x: 255 if x > 0 else 0)
        diffs.append((d, cols or ()))
    gap = int(HUE_GAP * 255)
    dists = [H.point(_hue_dist_lut(hsv(c)[0])) if c and coloured(c) else None for c in source]
    out = []
    for k, d in enumerate(dists):
        if d is None:
            out.append(_plain_part(im.size, S, V, source[k], diffs if plain else []))
            continue
        smin = max(SAT_MIN, hsv(source[k])[1] * SAT_REL) * 255     # a dull brown is not a bright red
        hue = ImageChops.multiply(lit, d.point(lambda x: 255 if x <= gap else 0))
        m = ImageChops.multiply(hue, S.point(lambda s: 255 if s >= smin else 0))
        # a ruddy face is not a red coat: with no copies to compare (a texture only this faction wears) every skin
        # and hair tone is kept; with copies only the paler skin (an orange-red caparison is the faction's)
        informative = any(not any(_like(source[k], c) for c in cols) for _, cols in diffs)
        skin = None if _skin_colour(source[k]) else _skin(H, S, V, broad=not informative)
        use = [dd for dd, cols in diffs if not any(_like(source[k], c) for c in cols)]
        proven = None                            # differs from every such copy: the faction's colour
        if use:
            proven = use[0]
            for dd in use[1:]:
                proven = ImageChops.multiply(proven, dd)
            if not 0 < proven.histogram()[255] / float(im.size[0] * im.size[1]) <= DIFF_MOST:
                proven = None                    # the copies are other pictures: they prove nothing
        if skin is not None and proven is not None:
            # a face is the same in every copy; what differs in all of them is cloth in the faction's colour, also
            # where its shade is skin-like (a red hood's brown folds stayed red in a black recolour: speckles)
            skin = ImageChops.subtract(skin, proven)
        if skin is not None:
            m = ImageChops.subtract(m, skin)
        # any coloured pixel of the hue - taken only where the other factions' copies show it is the faction's
        # colour (an artist often paints a duller green than the faction's colour says: the cloak came out in patches)
        loose = ImageChops.multiply(hue, S.point(lambda s: 255 if s >= SAT_MIN * 255 else 0))
        if skin is not None:
            loose = ImageChops.subtract(loose, skin)       # faces and hands stay (they differ by the man)
        other = dists[1 - k] if len(dists) > 1 else None
        closer = None
        if other is not None:                    # near both: the nearer one takes it (the primary on a tie)
            closer = ImageChops.subtract(d, other) if k == 0 else ImageChops.subtract(d, other, 1, -1)
            closer = closer.point(lambda x: 255 if x == 0 else 0)
            m = ImageChops.multiply(m, closer)
            loose = ImageChops.multiply(loose, closer)
        same = None
        strict = m
        if use:
            diff = proven if proven is not None else use[0]
            if proven is None:
                for dd in use[1:]:
                    diff = ImageChops.multiply(diff, dd)
            share = diff.histogram()[255] / float(im.size[0] * im.size[1])
            if 0 < share <= DIFF_MOST:
                # differs from most copies (two in three): one other faction whose cloak happens to be of a like
                # shade in places must not leave patches of the old colour
                if len(use) >= 3:
                    many = None
                    for dd in use:
                        one = dd.point(lambda x: 1 if x else 0)
                        many = one if many is None else ImageChops.add(many, one)
                    need = (2 * len(use) + 2) // 3
                    diff = many.point(lambda v: 255 if v >= need else 0)
                m = ImageChops.multiply(loose, diff)
                strict = loose
            # what is the same as in a faction that does not wear this colour is never the faction's colour (a
            # bronze star, a wooden pole, a face) - kept even when most of the picture differs
            # (by most of them: one other faction with a like part by chance must not keep a speck of the old colour)
            votes = None
            for dd in use:
                one = dd.point(lambda x: 0 if x else 1)
                votes = one if votes is None else ImageChops.add(votes, one)
            need = max(1, (len(use) + 1) // 2)
            same = votes.point(lambda v: 255 if v >= need else 0)
            m = ImageChops.subtract(m, same)
            # a cloak another faction happens to wear in a like shade in places would come out in patches: what the
            # comparison kept spreads over the rest of its own colour next to it (never into what most copies share)
            m = _spread(m, ImageChops.subtract(strict, same))
        g = _grow(m, H, S, V, d, gap, closer)
        if skin is not None:
            g = ImageChops.subtract(g, skin)        # the rim grown in never takes a face either
        out.append(ImageChops.subtract(g, same) if same is not None else g)
    if len(out) > 1:                             # grown into each other: the primary keeps its own
        from PIL import ImageChops as _C
        out[1] = _C.subtract(out[1], out[0])
    return out


def _skin_colour(rgb):
    """Whether a faction colour is itself of a skin tone (orange, brown) - then skin cannot be told apart by hue."""
    if not rgb or not coloured(rgb):
        return False
    h, sat, v = hsv(rgb)
    return 0.02 <= h <= 0.11 and sat < 0.75


def _skin(H, S, V, broad=True):
    """Pixels of a skin tone: orange-brown hue, not strongly coloured. broad: hair and the shaded skin too."""
    from PIL import ImageChops
    smax, vmin = (0.62, 0.12) if broad else (0.5, 0.3)
    h = H.point(lambda x: 255 if 0.02 * 255 <= x <= 0.11 * 255 else 0)
    return ImageChops.multiply(ImageChops.multiply(h, S.point(lambda x: 255 if x < smax * 255 else 0)),
                               V.point(lambda x: 255 if x > vmin * 255 else 0))


def _spread(m, inside, rounds=8):
    """m grown step by step over the pixels of 'inside' that touch it (a flood bounded to some pixels a round)."""
    from PIL import ImageChops, ImageFilter
    if not m.getbbox():
        return m
    for _ in range(rounds):
        nxt = ImageChops.lighter(m, ImageChops.multiply(m.filter(ImageFilter.MaxFilter(3)), inside))
        if nxt.histogram()[255] == m.histogram()[255]:
            break
        m = nxt
    return m


def _plain_part(size, S, V, colour, diffs):
    """The parts in a black / white / grey faction colour. No hue tells them apart from iron, cloth or a face, so
    they are found only where the same picture of other factions exists: dull pixels of that lightness that differ
    from every copy whose faction does not wear such a colour too, and not the same as in most of them. Without
    such copies (or when the copies are other pictures) nothing is taken - a black outline is not a black coat."""
    from PIL import Image, ImageChops
    kind = _plain(colour)
    use = [dd for dd, cols in diffs if not any(_like(colour, c) for c in cols)]
    if not kind or not use:
        return Image.new("L", size, 0)
    diff = use[0]
    for dd in use[1:]:
        diff = ImageChops.multiply(diff, dd)
    share = diff.histogram()[255] / float(size[0] * size[1])
    if not 0 < share <= DIFF_MOST:
        return Image.new("L", size, 0)
    from PIL import ImageFilter
    could = _plain_mask(S, V, kind)
    m = ImageChops.multiply(could, diff)
    # specks taken away (a dark shadow pixel that happens to differ is not a black coat), then the parts grown
    # over the rest of the same plain colour next to them (a black field found in pieces is filled)
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    for _ in range(3):
        m = ImageChops.lighter(m, ImageChops.multiply(m.filter(ImageFilter.MaxFilter(3)), could))
    return m


def _grow(m, H, S, V, dist, gap, closer=None, rounds=2):
    """The edges a strict test leaves (a dull or dark rim of a red stripe, a pixel blended with its neighbour)
    taken in: neighbours of the found parts that are somewhat coloured and of a hue somewhat near, twice."""
    from PIL import ImageChops, ImageFilter
    if not m.getbbox():
        return m
    loose = ImageChops.multiply(S.point(lambda s: 255 if s >= SAT_MIN * 0.5 * 255 else 0),
                                V.point(lambda v: 255 if v >= VAL_MIN * 0.6 * 255 else 0))
    loose = ImageChops.multiply(loose, dist.point(lambda x: 255 if x <= gap * 1.5 else 0))
    # past the strict hue gap only a rim is taken - dull or dark pixels; a bright clean colour of its own (the gold
    # of a wreath next to red) stays (a tester's emblem: its gold wolf and laurel turned red)
    rim = ImageChops.lighter(S.point(lambda s: 255 if s < 0.55 * 255 else 0),
                             V.point(lambda v: 255 if v < 0.55 * 255 else 0))
    loose = ImageChops.multiply(loose, ImageChops.lighter(dist.point(lambda x: 255 if x <= gap else 0), rim))
    if closer is not None:                       # never into the other colour's parts (a gold lion on red)
        loose = ImageChops.multiply(loose, closer)
    for _ in range(rounds):
        m = ImageChops.lighter(m, ImageChops.multiply(m.filter(ImageFilter.MaxFilter(3)), loose))
    return m


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


PLAIN_LIGHT = {"dark": 0.22, "light": 0.77}      # the lightness the games' artists give a black / a white part


def _to_plain(im, mask, dst):
    """A coloured part made black / white / grey (dst has no hue) the way the games' own textures do it: no hue, the
    part's average light set to the artists' black (0.22) or white (0.77) - grey: dst's own - and every fold kept (each
    pixel as far from the average as it was). A flat black (lightness scaled to near 0) lost every fold: black shields
    and hoods like holes in battle."""
    from PIL import Image, ImageStat
    H, S, V = im.convert("RGB").convert("HSV").split()
    kind = _plain(dst)
    goal = PLAIN_LIGHT.get(kind, hsv(dst)[2]) * 255.0
    ref = max(ImageStat.Stat(V, mask).mean[0], 12.0)
    S = Image.new("L", im.size, 0)
    if kind == "dark":       # measured against the HRE's own copies: the light scaled down is nearest the artists' black
        k = goal / ref
        V = V.point(lambda v: max(8, min(255, int(v * k))))
    else:                    # against Poland's: the folds kept as they were (moved up) is nearest their white
        add = goal - ref
        V = V.point(lambda v: max(8, min(255, int(v + add))))
    return Image.merge("HSV", (H, S, V)).convert("RGB")


def _shift_plain(im, mask, dst):
    """A black / white / grey part moved to colour dst: dst's hue and saturation, its brightness set by the pixel's
    light against the part's average light (the folds kept; a black coat does not stay black when made red)."""
    from PIL import Image, ImageStat
    H, S, V = im.convert("RGB").convert("HSV").split()
    th, ts, tv = hsv(dst)
    ref = max(ImageStat.Stat(V, mask).mean[0], 12.0)
    H = Image.new("L", im.size, int(round(th * 255)) % 256)
    S = Image.new("L", im.size, int(round(ts * 255)))
    k = tv * 255.0 / ref
    V = V.point(lambda v: min(255, int(v * k)))
    return Image.merge("HSV", (H, S, V)).convert("RGB")


def recolour(im, source, target, others=(), edits=None, plain=True):
    """(new picture, share of pixels changed): im with the parts in the source colours (primary, secondary) in the
    target colours, alpha kept. edits: the hand touch-ups {'p': mask, 's': mask, 'keep': mask} ('L', the picture's
    size) - painted as the new primary / secondary, or kept as they were. plain: black / white / grey faction colours
    are looked for too (only when the other copies are the same drawing - unit cards and textures, not symbols)."""
    from PIL import ImageChops
    ms = masks(im, source, others, plain)
    if edits:
        keep = edits.get("keep")
        for k, key in ((0, "p"), (1, "s")):
            e = edits.get(key)
            if e is not None:
                ms[k] = ImageChops.lighter(ms[k], e)
                ms[1 - k] = ImageChops.subtract(ms[1 - k], e)
            if keep is not None:
                ms[k] = ImageChops.subtract(ms[k], keep)
    rgb = im.convert("RGB")
    out = rgb.copy()
    n = 0
    for m, src, dst in zip(ms, source, target):
        if not dst or not m.getbbox():
            continue
        if _plain(src):
            part = _shift_plain(rgb, m, dst)
        elif _plain(dst):
            part = _to_plain(rgb, m, dst)
        else:
            part = _shift(rgb, src or dst, dst)
        out.paste(part, (0, 0), m)
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
    # a few cards are enough; the factions that matched before are tried first and a card stops at its first
    # match (40 cards x every faction's copy made the window slow to open on Medieval II - a tester)
    for it in [x for x in items if not isinstance(x, str) and x.get("of")][:12]:
        try:
            im = read_picture(it["path"]).convert("RGB")
        except Exception:
            continue
        looked += 1
        pairs = sorted(zip(it["others"], it["of"]), key=lambda pf: -votes.get(pf[1], 0))
        for (p, _), f in pairs:
            try:
                o = read_picture(p).convert("RGB")
            except Exception:
                continue
            if o.size == im.size and max(ImageStat.Stat(ImageChops.difference(im, o)).mean) < 2.0:
                votes[f] = votes.get(f, 0) + 1
                break
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


def _short(f):
    """The short name files use too: romans_julii -> julii (Rome's houses)."""
    return f.split("_", 1)[1] if f.lower().startswith("romans_") else f


def _others_named(path, faction, factions, colours):
    """[(path, colours)] of the same picture named after other factions (england -> france in the name or folder;
    spy_julii -> spy_brutii: the short names too)."""
    out, seen = [], set()
    for mine, theirs in ((faction, lambda f: f), (_short(faction), _short)):
        pat = r"(?i)(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(mine)
        if not re.search(pat, path):
            continue
        for f in factions:
            if f == faction or f not in colours:
                continue
            p = re.sub(pat, theirs(f), path)
            if p != path and p not in seen and os.path.isfile(p):
                seen.add(p)
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

    def add(path, group, label, others=(), crop=None, skip=None, of=(), own=None, alike=True, own_tex=None,
            source=None, own_sprite=None, painted_in=(None, None)):
        k = (os.path.normcase(os.path.abspath(path)), crop)
        if k in seen:
            if own_tex:                                  # one texture worn by several models: all of them follow
                prev = next((o for o in out if (os.path.normcase(os.path.abspath(o["path"])), o["crop"]) == k), None)
                if prev is not None and prev.get("own_tex"):
                    prev["own_tex"]["models"] += own_tex["models"]
            return
        seen.add(k)
        out.append({"path": path, "rel": mod.rel(path), "group": group, "label": label, "others": list(others),
                    "of": list(of), "crop": crop, "skip": skip, "own": own, "faction": faction,
                    "alike": alike, "own_tex": own_tex, "source": source, "own_sprite": own_sprite,
                    "painted": painted_in[0], "painted_by": painted_in[1]})
    for sub, label in (("units", "unit card"), ("unit_info", "unit info picture")):
        d = _ci(mod.find("ui") or "", sub) if mod.find("ui") else None
        own = _ci(d, faction) if d else None
        if not own:
            continue
        for n in sorted(os.listdir(own)):
            if n.lower().endswith(PICTURE_EXT):
                p = os.path.join(own, n)
                fs = [f for f in names if f != faction and f in colours and os.path.isfile(os.path.join(d, f, n))]
                add(p, "unit cards", "%s %s" % (label, n), [(os.path.join(d, f, n), colours[f]) for f in fs],
                    of=fs, source=_copied_from(p, [(os.path.join(d, f, n), f) for f in fs], colours))
    # battle textures: the model's texture for this faction; a file other factions wear too is left alone
    try:
        from .models import catalogue
        from .meshview import on_disk
        cat = catalogue(mod)
    except Exception:
        cat = {}
    # the names of the faction's own copies: one name, one source picture. Two pictures that differ only in the
    # wearer's word (EN_Peasant_Padded_england / _france) would both become ..._<faction> and the one written last
    # would dress every model of the other (a tester: the peasants wore France's blue in battle). The textures the
    # faction wears now count as taken, their source unknown.
    taken, game = {}, {}

    def painted(rel, got, wearers):
        """(colours, wearer) a picture worn by others is painted in: those of the wearer its file is named after
        (EN_Peasant_Padded_france -> France's; the game's own colours for a picture of the game's data, whatever
        the mod made of them since), or (None, None)."""
        stem = rel.replace("\\", "/").rsplit("/", 1)[-1].split(".")[0].lower()
        named = [w for w in wearers if re.search(r"(?:^|(?<=[^a-z0-9]))%s(?=$|[^a-z0-9])" % re.escape(w.lower()), stem)]
        if not named:
            return None, None
        w = max(named, key=len)
        if "cols" not in game:
            game["cols"] = _game_colours(mod)
        theirs = game["cols"].get(w)
        if theirs and theirs != colours.get(w) and _games_own(mod, rel, got[1]):     # read only when they differ
            return theirs, w
        return colours.get(w), w
    users = {}                                           # a texture FILE -> every faction wearing it, any model
    for info in cat.values():
        for r in (info.textures.get(faction), getattr(info, "attach", {}).get(faction)):
            if r:
                taken.setdefault(r.replace("\\", "/").lower(), None)
        for rows in (info.textures, getattr(info, "attach", {})):
            for f, r in rows.items():
                if r:
                    users.setdefault(r.replace("\\", "/").lower(), set()).add(f)

    def needs_copy(rel, got, wearers):
        """The original stays as it is: a texture is recoloured in place only when it is a copy made for the faction
        already (by the clone or an earlier recolour) - in the mod, named after the faction, worn by no other faction
        on any model, and no file of the game's install (the game's own data, Barbarian Invasion's, a Kingdoms
        campaign's, or an unchanged copy of one in the mod). Anything else gets a copy of its own and the faction's
        line points at it (the original, its copy, the copy recoloured, the copy in the mod)."""
        if wearers or users.get(rel.replace("\\", "/").lower(), set()) - {faction}:
            return True
        if not os.path.normcase(os.path.abspath(got[1])).startswith(os.path.normcase(os.path.abspath(mod.data))):
            return True
        from .models import own_texture_ref
        if own_texture_ref(rel, faction) != rel.replace("\\", "/"):
            return True                                  # not named after the faction: someone's original
        return _games_file(mod, got[1]) or _games_own(mod, rel, got[1])
    for name, info in sorted(cat.items()):
        rel = info.textures.get(faction)
        if not rel:
            continue
        got = on_disk(mod, rel)
        wearers = sorted(f for f, r in info.textures.items() if f != faction and r.lower() == rel.lower())
        if not got:
            continue
        # worn by other factions too (a clone wears its template's), only in the game's data, or the game's own
        # file: the faction gets a copy of its own in the mod and its model line points at it - the others' and the
        # game's stay as they are
        own_tex = _own_texture(mod, info, faction, rel, got, wearers, "texture", taken) \
            if needs_copy(rel, got, wearers) else None
        others = [(on_disk(mod, r)[1], colours[f]) for f, r in info.textures.items()
                  if f != faction and f in colours and r.lower() != rel.lower() and on_disk(mod, r)]
        label = "battle texture of %s" % info.name + (" - gets a copy of its own" if own_tex else "")
        add(got[1], "unit textures", label, others[:6], own_tex=own_tex, painted_in=painted(rel, got, wearers))
    # a unit the faction was given (Roster, a new unit, Bring...) whose model has no texture line of the faction:
    # the game dresses it in another faction's texture (the mercenaries' or the first) - the faction gets its own
    # copy, made from an owner's texture and recoloured from that owner's colours (a tester: the units given by the
    # Roster stayed brown in battle while their cards were recoloured)
    worn = []
    for info, src_f in _worn_without_line(mod, faction, cat):
        rel = info.textures[src_f]
        got = on_disk(mod, rel)
        if not got:
            continue
        own_tex = _own_texture(mod, info, faction, rel, got, [src_f], "texture", taken)
        # the colours it is painted in: the owner's (the game's own for a picture of the game's data - a tester's
        # test mod gave France purple, so France's blue peasants were not found to recolour)
        source = painted(rel, got, [src_f])[0] or colours.get(src_f)
        add(got[1], "unit textures", "battle texture of %s - %s's, gets a copy of its own" % (info.name, src_f),
            [], own_tex=own_tex, source=source)
        worn.append((info, src_f, source))
    # Medieval II: the weapons and shields texture beside it (a kite shield carries the faction's arms)
    for name, info in sorted(cat.items()):
        rel = getattr(info, "attach", {}).get(faction)
        got = on_disk(mod, rel) if rel else None
        if not got:
            continue
        wearers = sorted(f for f, r in info.attach.items() if f != faction and r.lower() == rel.lower())
        own_tex = _own_texture(mod, info, faction, rel, got, wearers, "attach", taken) \
            if needs_copy(rel, got, wearers) else None
        others = [(on_disk(mod, r)[1], colours[f]) for f, r in info.attach.items()
                  if f != faction and f in colours and r.lower() != rel.lower() and on_disk(mod, r)]
        label = "weapons and shields of %s" % info.name + (" - gets a copy of its own" if own_tex else "")
        add(got[1], "unit textures", label, others[:6], own_tex=own_tex, painted_in=painted(rel, got, wearers))
    # the far-away sprite a model names for the faction (Medieval II: the texture line's fourth value; Rome: its
    # model_sprite line) - a clone names its template's (england_...spr), so the faction gets its own .spr and pages
    # (<faction>_..._sprite_000.texture / .tga.dds ...) and the line points at them
    from .models import own_sprite_ref
    sprites, jobs = {}, []
    for name, info in sorted(cat.items()):
        rel = getattr(info, "sprites", {}).get(faction)
        if rel and info.textures.get(faction):
            wearers = sorted(f for f, r in info.sprites.items() if f != faction and r.lower() == rel.lower())
            jobs.append((info, rel, wearers or [f for f in names if rel.replace("\\", "/").rsplit("/", 1)[-1]
                                                .lower().startswith(f.lower() + "_")], None))
    # a unit given to the faction (no line of its own yet): the owner's sprite, in the owner's colours, as its texture
    for info, src_f, source in worn:
        rel = getattr(info, "sprites", {}).get(src_f)
        if rel:
            jobs.append((info, rel, [src_f], source))
    for info, rel, wearers, source in jobs:
        ref = own_sprite_ref(rel, faction, wearers)
        if ref == rel:
            continue                                    # its own already: found by its name below
        got = on_disk(mod, rel)
        if not got:
            continue
        if ref in sprites and sprites[ref]["src"] != got[1]:
            # another sprite already has that name (england_x and france_x both -> <faction>_x): this one keeps its
            # source's word (<faction>_france_x)
            ref = own_sprite_ref(rel, faction, [])
        if ref in sprites:
            sprites[ref]["models"].append(info.name)
            continue
        folder = os.path.dirname(got[0].replace("\\", "/"))     # beside the original as it lies on disk, in the mod
        spr = {"models": [info.name], "ref": ref, "src": got[1],
               "path": os.path.join(mod.data, *[x for x in folder.split("/") if x], os.path.basename(ref))}
        sprites[ref] = spr
        stem = os.path.basename(got[1])[:-4]
        folder = os.path.dirname(got[1])
        new_stem = os.path.basename(ref)[:-4]
        for n in sorted(os.listdir(folder)):
            m = re.fullmatch(re.escape(stem) + r"(_\d+\.(?:texture|tga\.dds|dds|tga))", n, re.I)
            if m:
                page = dict(spr, page=os.path.join(os.path.dirname(spr["path"]), new_stem + m.group(1)))
                add(os.path.join(folder, n), "unit sprites (far away)",
                    "far-away sprite of %s - gets a copy of its own" % info.name, own_sprite=page, source=source)
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
        if low.startswith(("campaign-select map", "victory conditions map")) or "leader picture" in low:
            continue                        # maps colour land, not the faction's dress; a leader's face stays
        if e.get("link") and e["link"][0] == "banners" and e["link"][1] in ("routing_texture", "rebels_texture"):
            continue                        # the white banner a fleeing unit shows and the rebels' are not its dress
        skip = own = out_x = None
        x = e.get("extra")
        if x and set(x["users"]) - {faction, faction.lower()}:
            base = os.path.basename(p).lower()
            if x["kind"] == "banner" and not x.get("owner") and base.startswith(("holy_", "special_unit")):
                skip = "a crusade / military order banner, the same for every faction - not its colours"
            else:
                out_x = x                                # the web pulled along: copies for whoever shares it
        elif e.get("shared") and e.get("link"):           # a line names it: the faction gets a copy of its own
            from .factionart import picture_target
            own = {"rel": picture_target(e, faction, faction), "link": e["link"]}
        elif e.get("shared"):
            skip = "shared with %s - give the faction its own picture on the Art tab first" % ", ".join(e["shared"][:4])
        elif e.get("locked") or (e.get("crop") and "shared" in (e.get("note") or "")):
            skip = e.get("note")
        if out_x is not None:
            skip = None
        label = e.get("label") or mod.rel(p)
        if own:
            label += " - shared with %s: gets a copy of its own" % ", ".join(e["shared"][:3])
        if out_x is not None:
            label += " - shared with %s: %s" % (", ".join(sorted(set(out_x["users"]) - {faction})[:3]), (
                "they get copies of their own" if (out_x.get("owner") or "").lower() == faction.lower() else
                "gets a copy of its own"))
        add(p, "symbols and banners", label,
            [] if e.get("crop") else _others_named(p, faction, names, colours), crop=tuple(e["crop"])
            if e.get("crop") else None, skip=skip, own=own, alike=False)
        if out_x is not None:
            out[-1]["share_out"] = out_x
    _more_targets(mod, faction, names, colours, add)
    return out


def _games_own(mod, rel, path):
    """True when the picture is the game's own: in the game's data folder, or a byte-for-byte copy of it in the mod
    (a mod folder made by copying the game's files)."""
    import types
    from .campaignrules import game_data
    from .packs import _on_disk
    if not os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(mod.data))):
        return True
    base = game_data(mod)
    theirs = _on_disk(types.SimpleNamespace(data=base), rel) if base else None
    if not theirs:
        return False
    try:
        if os.path.getsize(theirs[1]) != os.path.getsize(path):
            return False
        with open(theirs[1], "rb") as a, open(path, "rb") as b:
            return a.read() == b.read()
    except OSError:
        return False


def _games_file(mod, path):
    """True when the file is one of the game's install: in the game's own folders (data, bi/data, alexander/data, the
    Kingdoms campaigns' mods/<campaign>), or - by the game's manifests - a file of the install as it came that a mod
    folder copied unchanged."""
    from .newmod import game_of
    from .scan import Origins
    try:
        origins = Origins.for_mod(mod)
        game = game_of(mod.data)
        size = os.path.getsize(path)
    except Exception:
        return False
    if not game:
        return False
    rel = os.path.relpath(path, game).replace("\\", "/")
    low = rel.lower()
    from .gamefix import KINGDOMS_BATS
    if low.startswith(("data/", "bi/data/", "alexander/data/")) or \
            any(low.startswith("mods/%s/" % k) for k in KINGDOMS_BATS):
        return True                                    # the game's own folders (unpacked files are in no manifest)
    if origins is None:
        return False
    keys = [rel, "data/" + os.path.relpath(path, mod.data).replace("\\", "/")]
    return any(not k.startswith("..") and origins.classify(k, path, size) in ("game", "rex") for k in keys)


def _game_colours(mod):
    """faction_colours of the game's own data folder (a mod in mods/ keeps only what it changes), or {}."""
    from .campaignrules import game_data
    from .moddata import ModData
    d = game_data(mod)
    try:
        return faction_colours(ModData(d)) if d else {}
    except Exception:
        return {}


def _copied_from(path, copies, colours):
    """The colours of the faction whose copy this picture is (byte for byte), or None: a card the faction got from
    another faction (Roster, a new unit made from another's) carries that faction's colours, not the template's."""
    try:
        with open(path, "rb") as fh:
            mine = fh.read()
    except OSError:
        return None
    for p, f in copies:
        try:
            with open(p, "rb") as fh:
                if fh.read() == mine:
                    return colours.get(f)
        except OSError:
            continue
    return None


def _worn_without_line(mod, faction, cat):
    """[(model info, the faction whose texture it is made from)] of the battle models the faction's units wear that
    have per-faction texture lines but none of the faction: the texture of an owner of the unit, else the
    mercenaries', else the first."""
    from .models import unit_lines, unit_slots
    from .roster import _find_unit, ownership, roster
    from .units import owner_factions
    out, seen = [], set()
    try:
        units = [u["type"] for u in roster(mod, faction)["units"] if u["has"]]
        edu = mod.load(mod.file("edu"))
    except Exception:
        return out
    for u in units:
        lines = unit_lines(mod, u) or []
        for _, _, model in unit_slots(lines):
            info = cat.get(model.lower())
            if info is None or info.name.lower() in seen or faction in info.textures or \
                    not [f for f in info.textures if f]:
                continue
            seen.add(info.name.lower())
            try:
                owners = owner_factions(mod, ownership(edu, _find_unit(edu, u)))
            except Exception:
                owners = []
            src = next((f for f in owners if f in info.textures and f != faction), None) or \
                ("merc" if "merc" in info.textures else next(f for f in info.textures if f))
            out.append((info, src))
    return out


def _own_texture(mod, info, faction, rel, got, wearers, kind, taken=None):
    """Where the faction's own copy of a battle texture goes: {'model', 'kind', 'ref' (as the model names it),
    'path' (in the mod's data, the file's own extension kept: x.tga -> x.tga.dds on Rome)}. taken: {copy name
    (lower): the source picture it is made from, or None when unknown} - a name another source holds is not
    reused: the copy keeps its source's word (x_france -> x_france_<faction>), then a number."""
    from .clone import disk_tail
    from .models import own_texture_ref
    ref = own_texture_ref(rel, faction, wearers)
    if ref.lower() == rel.replace("\\", "/").lower():  # named after the faction already (its own original): the
        stem, dot, ext = ref.rpartition("/")[2].partition(".")     # copy is <name>_own beside it
        ref = ref[:len(ref) - len(ref.rpartition("/")[2])] + stem + "_own" + dot + ext
    if taken is not None:
        src = os.path.normcase(os.path.abspath(got[1]))
        holds = lambda r: r.lower() in taken and taken[r.lower()] != src
        if holds(ref) and ref.lower() != rel.replace("\\", "/").lower():   # named after it already: its own name
            ref = own_texture_ref(rel, faction)
            stem, dot, ext = ref.rpartition("/")[2].partition(".")
            head = ref[:len(ref) - len(ref.rpartition("/")[2])]
            n = 2
            while holds(ref):
                ref = "%s%s_%d%s%s" % (head, stem, n, dot, ext)
                n += 1
        taken[ref.lower()] = src
    # beside the original as it lies on disk (got[0]: its data-relative path in the disk's own letter case), in the
    # mod's own data even when the original is the game's
    folder = os.path.dirname(got[0].replace("\\", "/"))
    name = ref.replace("\\", "/").rsplit("/", 1)[-1] + disk_tail(rel, got[1])
    return {"models": [(info.name, kind)], "ref": ref,
            "path": os.path.join(mod.data, *[p for p in folder.split("/") if p], name)}


def _texture_file(mod, rel):
    """A texture named as the game names it (x.tga for x.tga.dds, any case) -> its path in the mod, or None."""
    from .packs import _on_disk
    rel = rel.replace("\\", "/")
    for r in (rel, rel + ".dds", rel[:-4] + ".texture" if rel.lower().endswith(".tga") else None):
        got = _on_disk(mod, r) if r else None
        if got:
            return got[1]
    return None


def _shared_skip(users, faction):
    others = sorted(set(users) - {faction})
    return ("shared with %s - recolouring it would change them as well" % ", ".join(others[:4])) if others else None


def _more_targets(mod, faction, names, colours, add):
    """The faction's pictures beyond the cards, battle textures and the Art tab: the units' far-away sprites, the
    faction symbol's texture (the 3D symbol of descr_sm_factions), the flag on its towns in battle (Rome's
    descr_building_battle), the battle banners (Medieval II's descr_banners_new.xml). The campaign map's flags need
    nothing: the game paints them in the faction's colours itself."""
    from .moddata import _ci
    # far-away sprites: <faction>_<unit>_sprite_NNN in data/sprites (Rome) or data/unit_sprites (Medieval II)
    for sub in ("sprites", "unit_sprites"):
        d = mod.find(sub)
        if not d:
            continue
        pre = faction.lower() + "_"
        longer = [f.lower() + "_" for f in names if f.lower().startswith(pre) and f != faction]
        for n in sorted(os.listdir(d)):
            low = n.lower()
            if not low.startswith(pre) or any(low.startswith(l) for l in longer) or \
                    not low.endswith((".dds", ".texture", ".tga")):
                continue
            rest = n[len(pre):]
            others = [(os.path.join(d, f + "_" + rest), colours[f]) for f in names
                      if f != faction and f in colours and os.path.isfile(os.path.join(d, f + "_" + rest))]
            add(os.path.join(d, n), "unit sprites (far away)", "sprite %s" % rest, others[:6])
    # Medieval II's own siege engines named after the faction (the carroccio: siege_engines/textures/
    # great_bell_tower_milan.texture); the normal / bump maps beside them are no pictures to recolour
    d = _ci(mod.find("siege_engines") or "", "textures") if mod.find("siege_engines") else None
    if d:
        tail = "_" + faction.lower() + ".texture"
        for n in sorted(os.listdir(d)):
            low = n.lower()
            if low.endswith(tail) and not low[:-len(tail)].endswith(("_normal", "_bump")):
                add(os.path.join(d, n), "unit textures", "siege engine %s" % n[:-8], ())
    # the faction symbol's texture, its towns' flag in battle, battle banners: found where the Art tab finds them
    from .factionart import extra_pictures
    for e in extra_pictures(mod, faction):
        add(e["path"], "symbols and banners", e["label"], _others_named(e["path"], faction, names, colours),
            skip=_shared_skip(e["users"], faction), alike=False)


def item_source(it, source, source_of=None):
    """The colours an item is recoloured from: its own (a card copied from another faction, a unit given to the
    faction), else - for a picture named after another faction than the one the colours come from (source_of; the
    window's 'from'; '*' = colours picked by hand, for every picture) - that faction's (EN_Peasant_Padded_france
    given to a clone of England is France's blue), else source."""
    if it.get("source"):
        return it["source"]
    if it.get("painted") and it.get("painted_by") and source_of != "*" and it["painted_by"] != source_of:
        return it["painted"]
    return source


def plan_recolour(plan, items, source, target, source_of=None):
    """Write every item (from targets()) recoloured from source to target colours into the plan (backup, Restore).
    source_of: the faction source is (item_source). Returns [(item, share changed or the reason it was left)]."""
    done = []
    sheets = {}
    cat = None
    for it in items:
        if it.get("skip"):
            done.append((it, it["skip"]))
            continue
        try:
            if it.get("crop"):
                sheet = sheets.get(it["path"]) or read_picture(it["path"])
                x, y, w, h = it["crop"]
                part = sheet.crop((x, y, x + w, y + h))
                new, share = recolour(part, item_source(it, source, source_of), target, edits=it.get("edits"))
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
                new, share = recolour(im, item_source(it, source, source_of), target, others, edits=it.get("edits"),
                                      plain=it.get("alike", True))
                if share > 0 and it.get("own_tex"):
                    # the faction's own copy in the mod, its model line pointed at it (both games, text + modeldb)
                    from .models import catalogue, set_faction_texture
                    o = it["own_tex"]
                    if cat is None:
                        cat = catalogue(plan.mod)
                    plan.binary(o["path"], picture_bytes(new, it["path"]))
                    for model, kind in o["models"]:
                        if model.lower() in cat:
                            set_faction_texture(plan, cat[model.lower()], it["faction"], o["ref"], kind)
                elif it.get("own_sprite"):
                    # the faction's own far-away sprite: every page under the new name (recoloured, or as it was
                    # when it holds none of the colours - the game wants them all), the .spr copied once (it holds
                    # no names), every model's line pointed at it
                    from .models import catalogue, set_faction_sprite
                    o = it["own_sprite"]
                    if cat is None:
                        cat = catalogue(plan.mod)
                    plan.binary(o["page"], picture_bytes(new, it["path"]))
                    if o["path"] not in plan.binaries:
                        with open(o["src"], "rb") as fh:
                            plan.binary(o["path"], fh.read())
                        for model in o["models"]:
                            if model.lower() in cat:
                                set_faction_sprite(plan, cat[model.lower()], it["faction"], o["ref"])
                elif share > 0 and it.get("own"):
                    import tempfile
                    from .factionart import write_art
                    tmp = os.path.join(tempfile.mkdtemp(prefix="recolour_"), "own.png")
                    new.save(tmp)
                    write_art(plan, it["faction"], it["own"]["rel"], {"src": tmp, "link": it["own"]["link"]})
                elif share > 0 and it.get("share_out"):
                    from .factionart import share_out
                    plan.binary(share_out(plan, it["share_out"], it["faction"]), picture_bytes(new, it["path"]))
                elif share > 0:
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


__all__ += ["targets", "plan_recolour", "item_source", "read_picture", "picture_bytes"]
