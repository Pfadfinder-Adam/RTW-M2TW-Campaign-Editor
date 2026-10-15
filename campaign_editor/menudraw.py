"""The menu pieces the game draws itself (no picture of their own: empty_push_button, empty_toggle_button, sliders,
text boxes, drop-downs, lists, borders) drawn the game's way, from its own parts in data/menu (rules.md 'MENU PIECES
THE ENGINE DRAWS ITSELF', read in RomeTW.exe; Medieval II runs the same code).

Every part picture is a 4 x 4 grid of cells (cell n = column n % 4, row n // 4), a cell STRETCHED to the box it is
drawn in. Frames are 9-slices (corners 0 / 3 / 12 / 15, edges 1 / 13 / 4 / 7, centre 5); a tick box is one cell of
buttons_composite2 as a square of the piece's width; a slider is arrows 12 / 13, a track 1 | 2 | 3 and a knob 7 of
slider_composite2. Pillow does the drawing; every function takes a parts(name) -> RGBA image or None.
"""

BUTTON_TEXT = (255, 221, 119)            # piece texts, normal (highlighted / pressed: white; disabled: grey 128)
STATIC_TEXT = (255, 223, 127)            # UIP_STATIC_TEXT, list rows - with a black shadow 1 px left, 1 px down
HIGHLIGHT = (255, 247, 119, 164)         # yellow_highlight: a list's chosen row
FRAME = "border_4pix_black_gold2.tga"
TICKS = "buttons_composite2.tga"
SLIDER = "slider_composite2.tga"


def kind(identifier, object_id, has_art):
    """How the game draws a piece: 'art' (its own picture), 'tick', 'slider', 'textbox', 'dropdown', 'list',
    'border', 'static' (words with a shadow), 'button' (words only), or 'none' (empty_art)."""
    ident = (identifier or "").upper()
    obj = (object_id or "").lower()
    if has_art:
        return "art"
    if "SLIDER" in ident:
        return "slider"
    if "DROPDOWN" in ident or ident.endswith("_PROVIDER"):
        return "dropdown"
    if "TEXTBOX" in ident:
        return "textbox"
    if ident == "UIP_BORDER" or "ERROR_DIALOG" in ident:
        return "border"
    if "LIST" in ident or ident.endswith("_DESCRIPTION"):
        return "list"
    if obj == "empty_toggle_button":
        return "tick"
    if "STATIC_TEXT" in ident or "MEDIUM_TEXT" in ident:
        return "static"
    if obj == "empty_push_button":
        return "button"
    return "none"


def cell(img, n, size):
    """Cell n of a 4 x 4 part picture, stretched to size (w, h)."""
    from PIL import Image
    cw, ch = img.width // 4, img.height // 4
    box = (cw * (n % 4), ch * (n // 4), cw * (n % 4 + 1), ch * (n // 4 + 1))
    return img.crop(box).resize((max(1, int(size[0])), max(1, int(size[1]))), Image.BILINEAR)


def nine_slice(img, w, h, b):
    """A frame w x h from a part picture: corners b x b, edges and the centre stretched (FUN_00d3771f)."""
    from PIL import Image
    w, h, b = max(1, int(w)), max(1, int(h)), int(min(b, w // 2, h // 2)) or 1
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mid_w, mid_h = max(1, w - 2 * b), max(1, h - 2 * b)
    for n, x, y, cw, ch in ((0, 0, 0, b, b), (1, b, 0, mid_w, b), (3, w - b, 0, b, b),
                            (4, 0, b, b, mid_h), (5, b, b, mid_w, mid_h), (7, w - b, b, b, mid_h),
                            (12, 0, h - b, b, b), (13, b, h - b, mid_w, b), (15, w - b, h - b, b, b)):
        part = cell(img, n, (cw, ch))
        out.alpha_composite(part, (x, y))
    return out


def tick(parts, w, ticked=False, radio=False):
    """A tick box (or a radio button): one cell as a square of the piece's width."""
    img = parts(TICKS)
    if img is None:
        return None
    return cell(img, (4 if radio else 0) + (1 if ticked else 0), (w, w))


def slider(parts, w, h, value=0.5):
    """A slider: arrows at the ends, the track between, the knob at value (0..1)."""
    from PIL import Image
    img = parts(SLIDER)
    if img is None:
        return None
    w, h = max(2, int(w)), max(2, int(h))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if w >= h:
        e = h
        out.alpha_composite(cell(img, 12, (e, e)), (0, 0))
        track = max(1, w - 4 * e)
        out.alpha_composite(cell(img, 1, (e, e)), (e, 0))
        out.alpha_composite(cell(img, 2, (track, e)), (2 * e, 0))
        out.alpha_composite(cell(img, 3, (e, e)), (min(w - e, 2 * e + track), 0))
        out.alpha_composite(cell(img, 13, (e, e)), (w - e, 0))
        knob = e + int(round(max(0, w - 3 * e) * value))
        out.alpha_composite(cell(img, 7, (e, e)), (min(w - e, knob), 0))
    else:
        e = w
        out.alpha_composite(cell(img, 5, (e, e)), (0, 0))
        track = max(1, h - 4 * e)
        out.alpha_composite(cell(img, 0, (e, e)), (0, e))
        out.alpha_composite(cell(img, 4, (e, track)), (0, 2 * e))
        out.alpha_composite(cell(img, 8, (e, e)), (0, min(h - e, 2 * e + track)))
        out.alpha_composite(cell(img, 9, (e, e)), (0, h - e))
        knob = e + int(round(max(0, h - 3 * e) * value))
        out.alpha_composite(cell(img, 7, (e, e)), (0, min(h - e, knob)))
    return out


def framed(parts, w, h, around=8, edge=16):
    """The frame of a text box / drop-down / list: 9-slice, edge 16, from 8 px outside the piece (the gold line on
    the piece's own edge) -> (image, offset): the image is drawn at (x - offset, y - offset)."""
    img = parts(FRAME)
    if img is None:
        return None, 0
    return nine_slice(img, w + 2 * around, h + 2 * around, edge), around


def piece_image(parts, k, w, h):
    """(image, offset) of what the game draws for a piece of kind k (no words) - None when nothing / no parts."""
    if k == "tick":
        return tick(parts, w), 0
    if k == "slider":
        return slider(parts, w, h), 0
    if k in ("textbox", "dropdown", "list"):
        img, off = framed(parts, w, h)
        if img is not None and k == "dropdown":
            arrow = parts(TICKS)
            if arrow is not None:
                e = max(8, int(h))
                img.alpha_composite(cell(arrow, 13, (e, e)), (int(off + w - e), int(off)))
        return img, off
    if k == "border":
        img = parts(FRAME)
        return (nine_slice(img, w, h, 16), 0) if img is not None else (None, 0)
    return None, 0


def text_colour(k):
    """(colour, shadow?) of a piece's words as the game writes them."""
    if k in ("static", "list"):
        return STATIC_TEXT, True
    return BUTTON_TEXT, False


__all__ = ["kind", "cell", "nine_slice", "tick", "slider", "framed", "piece_image", "text_colour", "BUTTON_TEXT",
           "STATIC_TEXT", "HIGHLIGHT"]
