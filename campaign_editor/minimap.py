"""The campaign map seen from above in the game's own ground textures - one picture for the minimap and the
faction-select maps (the user, 2026-10-15: 'make the radar map from a snapshot like ours, the water prettier; the
same picture as the faction's map with its land filled 75 %, crisp smooth borders').

- top_view(): terrain3d.colour_map (the grounds' textures blended into each other, the relief lit, the rivers rounded)
  with the sea drawn the way a painted map shows it: deep blue far out, turquoise shallows along the coast, a pale
  line where the water meets the land, a soft unevenness.
- radar_pictures() / redraw(): the campaign's minimap pictures (radar_map1 / radar_map2 / map_radar2.tga - the map in
  the campaign's bottom-left corner) drawn again from it, each at its own size, its border lines kept (Medieval II's
  radar_map2: a blue line along the top and the right) - never bigger than it was, so the original Rome exe that
  crashes on a too big radar_map1 is safe. redraw(picture=) puts a picture of the modder's own in the same way.
"""

import io
import os

import numpy as np

MINIMAPS = ("radar_map1.tga", "radar_map2.tga", "map_radar2.tga")

DEEP, SHALLOW, FOAM = (22, 62, 105), (58, 140, 160), (200, 225, 225)


_VIEWS = {}


def _view_key(mod, campaign, limit, winter):
    """What the top view is made of: the map's pictures as they stand in memory (a brush may have painted them) and
    the ground textures' list - the same key, the same picture."""
    import hashlib
    from . import terrain3d as T3
    h = hashlib.md5()
    for name in ("map_heights.tga", "map_ground_types.tga", "map_climates.tga", "map_features.tga"):
        pic = T3._picture(mod, campaign, name)
        h.update(name.encode() + (pic.tobytes() if pic is not None else b"-"))
    try:
        p = mod.find_any("descr_aerial_map_ground_types.txt")
        h.update(("%s %s" % (p, os.path.getmtime(p) if p else 0)).encode())
    except OSError:
        pass
    return (os.path.normcase(os.path.abspath(mod.data)), campaign, limit, winter, h.hexdigest())


def top_view(mod, campaign, limit=1600, winter=False):
    """(Pillow RGB picture, land mask 'L' of the same size) of the whole map seen from above, top row first. Raises
    ValueError without map_heights.tga; ImportError without Pillow. Made once for the same map (a tester: a faction
    brought from Barbarian Invasion froze the window 3-6 minutes - Preview, then Apply, each drew the whole map
    again for its faction-select picture)."""
    try:
        key = _view_key(mod, campaign, limit, winter)
    except Exception:
        key = None
    if key is not None and key in _VIEWS:
        a, b = _VIEWS[key]
        return a.copy(), b.copy()
    out = _top_view(mod, campaign, limit, winter)
    if key is not None:
        _VIEWS.clear()                                    # one map at a time: a big picture kept, not many
        _VIEWS[key] = (out[0].copy(), out[1].copy())
    return out


def _card_view(mod, campaign, limit, winter):
    """(rgb float32, water bool) of the map from above as the graphics card draws the 3D map (glmap.top_picture: the
    textures, relief and models the 3D map finds - the user, 2026-10-18: 'the 3D map reads the textures, the
    faction-select map came out in two or three colours'), the sea left for _top_view to paint; None when the card
    cannot (no OpenGL, another thread) - the drawing by hand then."""
    from PIL import Image
    from . import glmap
    from . import terrain3d as T3
    try:
        arr = glmap.top_picture(mod, campaign, limit, winter=winter, sea=False)
        h = T3.heights_metres(mod, campaign)
    except Exception:
        return None
    if arr is None or h is None:
        return None
    hh, ww = arr.shape[:2]
    water = np.asarray(Image.fromarray((h <= 0).astype(np.uint8) * 255).resize((ww, hh), Image.BILINEAR)) >= 128
    return arr.astype(np.float32), water


def _top_view(mod, campaign, limit=1600, winter=False):
    from PIL import Image, ImageFilter
    from . import terrain3d as T3
    # drawn by hand first (the user, 2026-10-18, the two side by side: 'this one is better, the land is painted' -
    # its rivers and colours); the graphics card's picture of the 3D map only where the hand found no texture for a
    # ground (its plain colour: 'two or three colours') and the 3D map can do better
    cm = T3.colour_map(mod, campaign, winter=winter, limit=limit)
    got = _card_view(mod, campaign, limit, winter) if any("not found" in n or "plain colour" in n
                                                         for n in cm.notes) else None
    if got is not None:
        rgb, water = got
    else:
        rgb = np.asarray(cm.rgb, dtype=np.float32).copy()
        water = np.asarray(cm.height) <= 0
    h, w = water.shape
    land = Image.fromarray(((~water) * 255).astype(np.uint8))
    near = np.asarray(land.filter(ImageFilter.GaussianBlur(w / 90)), dtype=np.float32) / 255      # the shallows
    shore = np.asarray(land.filter(ImageFilter.GaussianBlur(max(0.8, w / 600))), dtype=np.float32) / 255
    t = np.clip(near * 2.2, 0, 1)[..., None]
    rng = np.random.default_rng(11)
    noise = np.asarray(Image.fromarray(rng.integers(0, 255, (h, w), dtype=np.uint8)).filter(
        ImageFilter.GaussianBlur(3)), dtype=np.float32)[..., None] - 128
    sea = np.array(DEEP) * (1 - t) + np.array(SHALLOW) * t + noise * 0.15
    f = np.clip(shore * 1.6, 0, 1)[..., None] * 0.55
    sea = sea * (1 - f) + np.array(FOAM) * f
    rgb[water] = sea[water]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)), land


def radar_pictures(mod, campaign):
    """[path] of the campaign's minimap pictures there are (the mod's own folder, else the game's under it)."""
    out = []
    for name in MINIMAPS:
        p = mod.campaign_file(campaign, name)
        if p and os.path.isfile(p) and os.path.dirname(p) not in [os.path.dirname(x) for x in out if
                                                                    os.path.basename(x) == name]:
            out.append(p)
    return out


def radar_from(view, data):
    """TGA bytes: the minimap picture `data` (its bytes) drawn again from view (top_view's picture) - its own size,
    depth and border lines kept, its alpha (Medieval II's radar_map1) kept as it was."""
    from PIL import Image
    from .mapresize import radar_frame
    old = Image.open(io.BytesIO(data))
    old.load()
    t, b, left, right, _ = radar_frame(old)
    iw, ih = old.width - left - right, old.height - t - b
    if iw < 2 or ih < 2:
        raise ValueError("the minimap picture is all border")
    new = old.convert("RGBA")
    inner = view.convert("RGB").resize((iw, ih), Image.LANCZOS).convert("RGBA")
    if old.mode == "RGBA":
        inner.putalpha(old.getchannel("A").crop((left, t, left + iw, t + ih)))
    new.paste(inner, (left, t))
    mode = "RGBA" if len(data) > 16 and data[16] == 32 else "RGB"   # the file's own depth
    buf = io.BytesIO()
    new.convert(mode).save(buf, format="TGA", rle=False, orientation=-1)
    return buf.getvalue()


def redraw(plan, campaign, source=None, picture=None):
    """The campaign's minimap pictures drawn again from the map (source: the mod to read the map from - the Terrain
    editor's copy with its unwritten brush work; plan.mod by default), into plan as binaries. -> how many.
    picture: a picture file of the modder's own (report #288: 'give a button so they can put their own') put in
    instead, fitted to each minimap's size inside its border."""
    mod = plan.mod
    if picture:
        from PIL import Image
        with Image.open(picture) as im:
            view = im.convert("RGB")
    else:
        view, _ = top_view(source or mod, campaign)
    n = 0
    for p in radar_pictures(mod, campaign):
        with open(p, "rb") as fh:
            data = fh.read()
        dst = mod.own(p) if hasattr(mod, "own") else p
        plan.binary(dst, radar_from(view, data))
        plan.note(None, ("%s: your picture %s put in (its size %s kept)" % (
            mod.rel(dst), os.path.basename(picture), "x".join(str(x) for x in _size(data)))) if picture else
            "%s drawn again from the map (its size %s kept; the ground's textures, relief, rivers, the sea's depths)"
            % (mod.rel(dst), "x".join(str(x) for x in _size(data))))
        n += 1
    if not n:
        raise ValueError("this campaign has no minimap picture (radar_map1 / radar_map2.tga) to draw again")
    return n


def _size(data):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        return im.size


__all__ = ["top_view", "radar_pictures", "radar_from", "redraw", "MINIMAPS"]
