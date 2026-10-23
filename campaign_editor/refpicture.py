"""A reference picture on the campaign map (a real-world map, a sketch, another mod's map): laid over the map, see-
through, moved and sized on the map's own tiles, to trace the coasts and borders by or to look at beside the map.

It is the modder's own picture, nothing of the game: it is never written into the mod. Where it lies, how big, how
see-through, flipped or grey - kept per mod and campaign in the editor's settings, so it is there again next time.

The shortcuts follow PureRef's defaults (a user asked: 'I instinctively use the keyboard shortcuts, like in
PureRef'), so the hands that know PureRef know these; only a key the editor already uses for something else
(Ctrl+Y = Redo) is another one here. Letters go by the key's code, so they work in any keyboard layout."""

import math
import os

try:
    from PIL import Image
except ImportError:                      # the keys below are still read without it (CI's test job has no Pillow)
    Image = None

OPACITY_STEP = 0.1                       # Ctrl+Shift+= / Ctrl+Shift+-: PureRef's opacity keys go by tenths too
LEAST_OPACITY = 0.05                     # never quite gone: a picture at 0 % looks lost, not see-through
SETTINGS_KEY = "map_ref_pictures"

# (keys as shown, what they do, PureRef's name of the same keys) - the window's help is made from this list, and the
# tests check every key here is one the map really answers
SHORTCUTS = (
    ("Ctrl+I", "open a picture", "Open images"),
    ("Ctrl+Shift+Y", "show / hide the picture", "Overlay selection is Ctrl+Y there; Ctrl+Y is Redo here"),
    ("Ctrl+Shift+=  /  Ctrl+Shift+-", "more / less see-through (by 10 %)", "Increase / Decrease opacity"),
    ("Ctrl+Alt+Shift + left drag", "opacity: drag right = more, left = less", "Change opacity"),
    ("Alt+L", "lock / unlock it (unlocked: the left button moves and sizes it)", "Toggle locked"),
    ("left drag (unlocked)", "move the picture", "Move item"),
    ("Shift + left drag (unlocked)", "move it straight across or down", "Axis snapped move item"),
    ("Ctrl+Alt + left drag (unlocked)", "size it, keeping its shape (right = bigger)", "Scale"),
    ("Ctrl+Shift+T", "back on the whole map (stretched to its tiles)", "Reset transform"),
    ("Ctrl+Alt+Down", "its own shape again (one picture pixel square)", "Normalize scale"),
    ("Alt+Shift+H  /  Alt+Shift+V", "mirror it left-right / upside down", "Flip image horizontally / vertically"),
    ("Alt+G", "grey / in colour", "Toggle grayscale"),
    ("Alt+T", "smooth / sharp pixels", "Toggle bilinear sampling"),
    ("Up  /  Down", "over the map's signs / under them", "Send to front / Send to back"),
)


class RefPicture:
    """Where the picture lies: x, y = its top left corner and w, h = its size, in tiles, counted as the map view
    counts them (x from the left, y from the TOP row down - MapView.ox / oy), so it lies on the tiles exactly."""

    def __init__(self):
        self.path = None
        self.src = None                  # the picture as read (RGBA), or None
        self.x = self.y = 0.0
        self.w = self.h = 0.0
        self.opacity = 0.5
        self.shown = True
        self.locked = True               # locked: the map's tools work as always; unlocked: the left button is its
        self.front = False               # over the signs (towns, armies) or under them, laid into the map's picture
        self.flip_h = self.flip_v = self.grey = False
        self.smooth = True
        self._prep, self._prep_key = None, None

    # ---- the picture ----
    def open(self, path, map_w, map_h):
        """Read a picture (png, jpg, bmp, tga, dds, tif...) and lay it over the whole map. Raises OSError / ValueError
        when it cannot be read."""
        with Image.open(path) as im:
            src = im.convert("RGBA")
        self.path, self.src, self._prep_key = os.path.abspath(path), src, None
        self.shown = True
        self.fit(map_w, map_h)

    def loaded(self):
        return self.src is not None

    def visible(self):
        return self.src is not None and self.shown

    def clear(self):
        self.__init__()

    # ---- where it lies ----
    def fit(self, map_w, map_h):
        """The whole map, edge to edge (a picture of the same land then lies where the map does)."""
        self.x, self.y, self.w, self.h = 0.0, 0.0, float(map_w), float(map_h)

    def own_shape(self):
        """Its own shape again, keeping its width and its middle (a stretched picture back square)."""
        if not self.src:
            return
        cx, cy = self.x + self.w / 2, self.y + self.h / 2
        self.h = self.w * self.src.height / float(self.src.width)
        self.x, self.y = cx - self.w / 2, cy - self.h / 2

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def scale(self, k, at):
        """k times bigger, the point `at` (in tiles) staying where it is - as a picture pulled at under the mouse."""
        k = max(1e-3, k)
        ax, ay = at
        w, h = self.w * k, self.h * k
        if w < 1e-3 or h < 1e-3 or w > 1e6 or h > 1e6:
            return
        self.x, self.y = ax - (ax - self.x) * k, ay - (ay - self.y) * k
        self.w, self.h = w, h

    def set_opacity(self, v):
        self.opacity = min(1.0, max(LEAST_OPACITY, float(v)))

    def nudge_opacity(self, step):
        """One step up or down, onto the next whole tenth (0.45 + 0.1 = 0.5, not 0.55)."""
        tenths = self.opacity / OPACITY_STEP
        n = math.floor(tenths + 1e-6) + 1 if step > 0 else math.ceil(tenths - 1e-6) - 1
        self.set_opacity(n * OPACITY_STEP)

    def under(self, tx, ty):
        """Whether the tile point (top-down) lies on the picture."""
        return self.x <= tx < self.x + self.w and self.y <= ty < self.y + self.h

    # ---- drawing ----
    def _prepared(self):
        key = (id(self.src), self.flip_h, self.flip_v, self.grey)
        if self._prep_key != key:
            im = self.src
            if self.flip_h:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            if self.flip_v:
                im = im.transpose(Image.FLIP_TOP_BOTTOM)
            if self.grey:
                a = im.getchannel("A")
                im = im.convert("L").convert("RGBA")
                im.putalpha(a)
            self._prep, self._prep_key = im, key
        return self._prep

    def view(self, ox, oy, z, size):
        """The picture as the map view shows it: an RGBA picture of `size` (the canvas), see-through as set, or None
        when none of it is in sight. ox, oy = the view's top left in tiles, z = screen pixels a tile. Only the part in
        sight is taken and sized, so a big picture far zoomed in costs no more than the view."""
        if not self.visible() or self.w <= 0 or self.h <= 0:
            return None
        cw, ch = size
        sx0, sy0 = (self.x - ox) * z, (self.y - oy) * z          # where it lies on the screen
        sx1, sy1 = sx0 + self.w * z, sy0 + self.h * z
        vx0, vy0 = max(0, int(math.floor(sx0))), max(0, int(math.floor(sy0)))
        vx1, vy1 = min(cw, int(math.ceil(sx1))), min(ch, int(math.ceil(sy1)))
        if vx1 <= vx0 or vy1 <= vy0:
            return None
        im = self._prepared()
        kx, ky = im.width / (sx1 - sx0), im.height / (sy1 - sy0)   # picture pixels a screen pixel
        box = ((vx0 - sx0) * kx, (vy0 - sy0) * ky, (vx1 - sx0) * kx, (vy1 - sy0) * ky)
        box = (max(0.0, box[0]), max(0.0, box[1]), min(float(im.width), box[2]), min(float(im.height), box[3]))
        if box[2] <= box[0] or box[3] <= box[1]:
            return None
        part = im.resize((vx1 - vx0, vy1 - vy0), Image.BILINEAR if self.smooth else Image.NEAREST, box=box)
        a = part.getchannel("A").point(lambda v, o=self.opacity: int(v * o + 0.5))
        part.putalpha(a)
        out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        out.paste(part, (vx0, vy0))
        return out

    def onto(self, pic, ox, oy, z):
        """The map's own view picture (RGB) with the picture laid over it - the 'under the signs' way."""
        layer = self.view(ox, oy, z, pic.size)
        if layer is None:
            return pic
        return Image.alpha_composite(pic.convert("RGBA"), layer).convert(pic.mode)

    # ---- kept between starts ----
    STATE = ("x", "y", "w", "h", "opacity", "shown", "front", "flip_h", "flip_v", "grey", "smooth")

    def state(self):
        d = {k: getattr(self, k) for k in self.STATE}
        d["path"] = self.path
        return d

    def restore(self, d):
        """Back as it was kept (the picture read again from its file); False when the file is gone or unreadable."""
        if not isinstance(d, dict) or not d.get("path"):
            return False
        try:
            with Image.open(d["path"]) as im:
                src = im.convert("RGBA")
        except (OSError, ValueError):
            return False
        self.clear()
        self.path, self.src = d["path"], src
        for k in self.STATE:
            v = d.get(k)
            if isinstance(v, (bool, int, float)) and not (isinstance(v, float) and math.isnan(v)):
                setattr(self, k, type(getattr(self, k))(v))
        self.set_opacity(self.opacity)
        self.locked = True                                          # never opens grabbing the left button
        return True


def key_of(cmap):
    """The settings key of a map: its mod's data folder and campaign (each mod and campaign has its own picture)."""
    mod = getattr(cmap, "mod", None)
    data = getattr(mod, "data", None) or ""
    return "%s|%s" % (os.path.normcase(os.path.abspath(data)) if data else "", getattr(cmap, "campaign", "") or "")


def kept(cmap):
    from . import settings
    return (settings.get(SETTINGS_KEY, {}) or {}).get(key_of(cmap))


def keep(cmap, ref):
    from . import settings
    allk = dict(settings.get(SETTINGS_KEY, {}) or {})
    if ref.loaded():
        allk[key_of(cmap)] = ref.state()
    else:
        allk.pop(key_of(cmap), None)
    settings.put(SETTINGS_KEY, allk)


# ---- the keys (layout-free: the key's code, as App.LAYOUT_KEYS) ----
# Windows virtual key codes; Tk on X11 gives other codes, so the key's own name is tried first
VK = {"I": 73, "Y": 89, "T": 84, "L": 76, "H": 72, "V": 86, "G": 71}
VK_PLUS, VK_MINUS = (187, 107), (189, 109)       # = / + on the main keys and the number pad; - / the pad's -


def _letter(e):
    ks = getattr(e, "keysym", "") or ""
    if len(ks) == 1 and ks.isascii() and ks.isalpha():
        return ks.upper()
    code = getattr(e, "keycode", None)
    return next((k for k, v in VK.items() if v == code), None)


def action_of(e, ctrl, shift, alt):
    """The key event -> the name of what it does to the picture, or None (the key is not one of the picture's)."""
    ks = getattr(e, "keysym", "") or ""
    code = getattr(e, "keycode", None)
    if ctrl and shift and not alt:
        if ks in ("plus", "equal", "KP_Add") or code in VK_PLUS:
            return "more"
        if ks in ("minus", "underscore", "KP_Subtract") or code in VK_MINUS:
            return "less"
    let = _letter(e)
    if ctrl and not shift and not alt and let == "I":
        return "open"
    if ctrl and shift and not alt:
        return {"Y": "show", "T": "fit"}.get(let)
    if ctrl and alt and not shift and ks == "Down":
        return "own_shape"
    if alt and not ctrl:
        if shift:
            return {"H": "flip_h", "V": "flip_v"}.get(let)
        return {"L": "lock", "G": "grey", "T": "smooth"}.get(let)
    if not (ctrl or alt or shift) and ks in ("Up", "Down"):
        return "front" if ks == "Up" else "back"
    return None
