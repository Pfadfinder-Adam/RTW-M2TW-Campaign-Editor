"""Light and dark look of the window. ttk widgets take the colours from one
'clam' style; plain tk widgets (lists, text boxes, canvases, buttons) are
recoloured one by one, also those made later (a <Map> binding on every widget):
neutral light colours become the dark palette's, dark text becomes light, and
colours that mean something (a changed field's yellow, a faction's colour) stay.
The choice is kept in CampaignEditor_settings.json ('theme')."""

import tkinter as tk
from tkinter import ttk

from . import settings

LIGHT = {"bg": "#f0f0f0", "fg": "#1e1e1e", "field": "#ffffff", "muted": "#555555", "border": "#b4b4b4",
         "select": "#3874d8", "selectfg": "#ffffff", "accent": "#cfe3ff", "tab": "#dcdcdc", "trough": "#e2e2e2",
         "button": "#e6e6e6", "active": "#d5e4f7", "link": "#2050c0"}
DARK = {"bg": "#2b2d31", "fg": "#e3e3e3", "field": "#1e1f22", "muted": "#a9adb3", "border": "#4b4e55",
        "select": "#3d6fb8", "selectfg": "#ffffff", "accent": "#35598c", "tab": "#35373c", "trough": "#232428",
        "button": "#3a3d43", "active": "#46505e", "link": "#8ab8ff"}

# colours the window sets by hand that belong to the palette, not to a meaning
# EVERY button has one look (a tester's rule, 2026-10-05: 'all buttons alike, 1.5 x smaller, the same gaps; only
# the colour may differ'): one size, one frame, one gap - set here, nowhere else
BUTTON_PADX = 4     # px from a button's words to its edge, each side (no wider than its words need - everywhere)
BUTTON_PADY = 0     # px above and below the words: the button about 1.5 x lower than before (21 / 29 px)
BUTTON_GAP = 4      # px between two buttons side by side
# buttons with a colour of their own (the same size and frame): style name -> (background, when pressed / hovered);
# white words in either look - the links (Ko-fi, Discord, YouTube, GitHub) in their own sites' colours
COLOURED = {"Play.TButton": ("#2e7d32", "#256628"), "Kofi.TButton": ("#ff5e5b", "#e14b48"),
            "Discord.TButton": ("#5865f2", "#4752c4"), "YouTube.TButton": ("#e00000", "#b80000"),
            "GitHub.TButton": ("#1b1f24", "#0d1117")}
NAMED = {"#cfe3ff": "accent"}

BG_KEYS = ("field", "bg", "tab", "button", "trough", "accent", "active", "select")
FG_KEYS = ("fg", "muted", "selectfg", "link")      # link: the hover '?' marks
BG_OPTS = ("background", "activebackground", "highlightbackground", "troughcolor", "selectcolor",
           "readonlybackground", "disabledbackground")
FG_OPTS = ("foreground", "activeforeground", "insertbackground", "disabledforeground", "highlightcolor")

_state = {"dark": False, "root": None, "done": {}, "base": None}


def dark():
    return _state["dark"]


def palette():
    return DARK if _state["dark"] else LIGHT


def field():
    """The background of an entry that shows nothing special."""
    return palette()["field"]


_RGB = {}
_PAL_HEX = {}                                    # {key group: {hex of a LIGHT or DARK colour: its key}}


def _rgb(root, colour):
    """A colour's (r, g, b), remembered: a window of 900 widgets asked Tk 50 000 times (2 s - a report's lag)."""
    if colour in _RGB:
        return _RGB[colour]
    try:
        r, g, b = root.winfo_rgb(colour)
        got = r >> 8, g >> 8, b >> 8
    except tk.TclError:
        got = None
    _RGB[colour] = got
    return got


def _neutral(rgb):
    return rgb is not None and max(rgb) - min(rgb) <= 24


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def _lum(rgb):
    """Relative luminance (WCAG) of an (r, g, b) of 0..255."""
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def on_colour(fill):
    """'black' or 'white' for a letter or a picture drawn on the colour fill ('#rrggbb' or (r, g, b)): whichever
    stands out more - the one rule for every coloured sign (map signs, colour buttons)."""
    if isinstance(fill, str):
        fill = tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
    return "black" if contrast(fill[:3], (0, 0, 0)) >= contrast(fill[:3], (255, 255, 255)) else "white"


def colour_style(colour, base="TButton"):
    """The style of a button with a colour of its own (a colour picker's swatch, a palette entry): `base` - the
    same size, frame and gap as every other button - with this background and words that read on it ('#rrggbb' or
    (r, g, b)); made once per colour, it keeps its colour in either look."""
    if not isinstance(colour, str):
        colour = "#%02x%02x%02x" % tuple(int(v) for v in colour[:3])
    name = "C%s.%s" % (colour.lstrip("#").lower(), base)
    if name not in _STYLES:
        st = ttk.Style()
        words = on_colour(colour)
        st.configure(name, background=colour, foreground=words)
        st.map(name, background=[("disabled", "#9a9a9a"), ("pressed", colour), ("active", colour),
                                 ("selected", colour)],
               foreground=[("disabled", "#d0d0d0")], bordercolor=[("selected", words), ("focus", words)],
               relief=[("pressed", "sunken"), ("selected", "sunken")])   # the picked palette colour stands out
        _STYLES.add(name)
    return name


def paint(button, colour, **kw):
    """Give a ttk button (or a Toolbutton radio) a colour of its own (colour_style), with any other options."""
    base = "Toolbutton" if button.winfo_class() in ("TRadiobutton", "Toolbutton") else "TButton"
    button.configure(style=colour_style(colour, base), **kw)


_STYLES = set()


def contrast(a, b):
    """WCAG contrast ratio of two (r, g, b): 1 (none) .. 21 (black on white); text wants 4.5."""
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


READABLE = 4.5


def readable(rgb, bg):
    """The text colour rgb, or the nearest colour of the same hue that reads on bg (4.5:1): darker on a light
    ground, lighter on a dark one. None when rgb reads already."""
    if contrast(rgb, bg) >= READABLE:
        return None
    to = (0, 0, 0) if contrast((0, 0, 0), bg) >= contrast((255, 255, 255), bg) else (255, 255, 255)
    for k in range(1, 21):
        t = k / 20.0
        c = tuple(int(round(v + (w - v) * t)) for v, w in zip(rgb, to))
        if contrast(c, bg) >= READABLE:
            return _hex(c)
    return _hex(to)


def ink(colour, ground="bg"):
    """A text colour the window sets itself after a widget is made (a status line's red, a list's grey, a tag's
    blue): the same colour, made readable on the look's ground - 'bg' for labels, 'field' for lists, trees and
    text boxes (the dark look once showed dark red and dark blue on its dark grey)."""
    root = _state["root"]
    if root is None or not colour:
        return colour
    rgb, bg = _rgb(root, colour), _rgb(root, palette()[ground])
    if rgb is None or bg is None:
        return colour
    return readable(rgb, bg) or colour


def _translate(root, opt, value, bg_orig, bg_now=None):
    """The look's colour for a colour the window set, or None to keep it. Text (foreground) is always made
    readable on bg_now - the background the widget has in this look (a palette colour, or a colour that means
    something, like the Module builder's IF block or a ground type's swatch)."""
    new = _translate_one(root, opt, value, bg_orig)
    if opt not in ("foreground", "activeforeground"):
        return new
    fg = _rgb(root, new or value) if (new or value) else None
    bg = _rgb(root, bg_now) if bg_now else None
    if fg is None or bg is None:
        return new
    return readable(fg, bg) or new


def _translate_one(root, opt, value, bg_orig):
    """The dark palette's colour for a light one, or None to keep it."""
    if not value:
        return None
    rgb = _rgb(root, value)
    if rgb is None:
        return None
    cur = palette()
    hx = _hex(rgb)
    # a palette colour (set while the other look was on) becomes this palette's
    keys = BG_KEYS if opt in BG_OPTS else FG_KEYS
    known = _PAL_HEX.get(keys)
    if known is None:
        known = _PAL_HEX[keys] = {}
        for k in reversed(keys):                 # the first key wins, as the loop it replaces
            for pal in (DARK, LIGHT):
                c = _rgb(root, pal[k])
                if c is not None:
                    known[_hex(c)] = k
    if hx in known:
        return cur[known[hx]]
    if not _state["dark"]:
        return None
    p = DARK
    if hx in NAMED:
        return p[NAMED[hx]]
    lum = sum(rgb) / 3.0
    if opt in BG_OPTS:
        if not _neutral(rgb):
            return None                                  # a colour that means something
        if lum >= 250:
            return p["field"]
        if lum >= 170:
            return p["bg"] if opt != "troughcolor" else p["trough"]
        return None
    if opt in FG_OPTS:
        brgb = _rgb(root, bg_orig) if bg_orig else None
        if brgb is not None and not _neutral(brgb) and sum(brgb) / 3.0 > 150:
            return None                                  # dark text on a light meaning colour stays readable
        if not _neutral(rgb):
            return None
        if lum < 60:
            return p["fg"]
        if lum < 150:
            return p["muted"]
    return None


def recolour(w, force=False):
    """One widget to the look now in force, from the colours it has now (done once
    per look: a colour the window sets later, like a changed field's, is left alone)."""
    root = _state["root"]
    if root is None:
        return
    key = str(w)
    if key in _state.get("keep", ()):
        return
    if not force and _state["done"].get(key) == _state["dark"]:
        return
    _state["done"][key] = _state["dark"]
    try:
        names = w.keys()
        cls = w.winfo_class()
    except tk.TclError:
        return
    is_ttk = cls.startswith("T") and cls not in ("Toplevel", "Text", "Tk")
    now = {}
    for opt in (BG_OPTS + FG_OPTS) if not is_ttk else ("foreground",):
        if opt in names:
            try:
                now[opt] = str(w.cget(opt))
            except tk.TclError:
                pass
    bg = now.get("background")
    if is_ttk:                                   # a ttk widget's ground is its style's
        try:
            st = ttk.Style(root)
            bg_now = st.lookup(str(w.cget("style") or cls), "background") or st.lookup(".", "background")
        except tk.TclError:
            bg_now = None
    else:
        bg_now = (_translate(root, "background", bg, bg) or bg) if bg else None
    for opt, value in now.items():
        new = _translate(root, opt, value, bg, bg_now)
        if new is not None and new != value:
            try:
                w.configure(**{opt: new})
            except tk.TclError:
                pass


def leave_alone(*widgets):
    """Widgets that keep their own colours in every look (the yellow hover box: dark text on light yellow - the
    dark look once turned its text light, white on yellow, a tester's report)."""
    for w in widgets:
        _state.setdefault("keep", set()).add(str(w))


def _walk(w):
    recolour(w, force=True)
    for c in w.winfo_children():
        _walk(c)


def _mapped(e):
    w = e.widget
    if isinstance(w, str) or _state["root"] is None:
        return
    recolour(w)


def _style(root):
    p = palette()
    st = ttk.Style(root)
    if _state["base"] is None:
        _state["base"] = st.theme_use()
    st.theme_use("clam")
    st.configure(".", background=p["bg"], foreground=p["fg"], fieldbackground=p["field"],
                 bordercolor=p["border"], darkcolor=p["bg"], lightcolor=p["bg"], troughcolor=p["trough"],
                 selectbackground=p["select"], selectforeground=p["selectfg"], insertcolor=p["fg"],
                 focuscolor=p["select"])
    st.map(".", background=[("disabled", p["bg"]), ("active", p["active"])],
           foreground=[("disabled", p["muted"])])
    # a button no wider than its words and about two spaces each side (no minimum width of 11 letters - clam's own
    # - which made '+' or 'OK' as wide as 'Browse...')
    # one size for every kind of button: no focus ring (it made them taller) - a focused button shows a coloured
    # frame instead
    for kind in ("TButton", "TMenubutton", "Toolbutton"):
        st.configure(kind, background=p["button"], padding=(BUTTON_PADX, BUTTON_PADY), width=0, focusthickness=0,
                     borderwidth=1, relief="raised")       # one frame: a toggle has it too, not only when picked
        st.map(kind, bordercolor=[("focus", p["select"])], relief=[("pressed", "sunken"), ("selected", "sunken")])
    st.map("TButton", background=[("pressed", p["accent"]), ("active", p["active"])])
    st.map("Toolbutton", background=[("selected", p["accent"]), ("pressed", p["accent"]), ("active", p["active"])])
    for name, (colour, deep) in COLOURED.items():
        st.configure(name, background=colour, foreground="#ffffff")
        st.map(name, background=[("pressed", deep), ("active", deep)], foreground=[("disabled", "#dddddd")])
    st.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"])
    st.configure("TSpinbox", fieldbackground=p["field"], foreground=p["fg"], arrowcolor=p["fg"])
    st.configure("TCombobox", fieldbackground=p["field"], foreground=p["fg"], arrowcolor=p["fg"],
                 background=p["button"])
    st.map("TCombobox", fieldbackground=[("readonly", p["field"])], foreground=[("readonly", p["fg"])],
           selectbackground=[("readonly", p["field"])], selectforeground=[("readonly", p["fg"])])
    st.configure("TCheckbutton", indicatorbackground=p["field"], indicatorforeground=p["fg"])
    st.configure("TRadiobutton", indicatorbackground=p["field"], indicatorforeground=p["fg"])
    st.configure("Treeview", background=p["field"], fieldbackground=p["field"], foreground=p["fg"])
    st.map("Treeview", background=[("selected", p["select"])], foreground=[("selected", p["selectfg"])])
    st.configure("Treeview.Heading", background=p["tab"], foreground=p["fg"])
    st.configure("TLabelframe", background=p["bg"], bordercolor=p["border"])
    st.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"])
    st.configure("TScrollbar", background=p["button"], arrowcolor=p["fg"])
    # the line between two panes, dragged to resize: drawn in the text's colour so it stands out on either look
    st.configure("Sash", sashthickness=8, gripcount=60, background=p["muted"], lightcolor=p["fg"],
                 darkcolor=p["fg"], bordercolor=p["border"])
    # the tabs: as low as the buttons (BUTTON_PADY), bold, the one open coloured like the work bar's button
    st.configure("TNotebook", background=p["bg"], tabmargins=(2, 2, 2, 0))
    st.configure("TNotebook.Tab", background=p["tab"], foreground=p["fg"],
                 padding=(BUTTON_PADX * 3, BUTTON_PADY + 1), font=("", 9, "bold"))
    st.map("TNotebook.Tab", background=[("selected", p["accent"]), ("active", p["active"])],
           expand=[("selected", (2, 2, 2, 0))])
    for opt, val in (("*Listbox.background", p["field"]), ("*Listbox.foreground", p["fg"]),
                     ("*Listbox.selectBackground", p["select"]), ("*Listbox.selectForeground", p["selectfg"]),
                     ("*TCombobox*Listbox.background", p["field"]), ("*TCombobox*Listbox.foreground", p["fg"]),
                     ("*Text.background", p["field"]), ("*Text.foreground", p["fg"]),
                     ("*Text.insertBackground", p["fg"]), ("*Entry.background", p["field"]),
                     ("*Entry.foreground", p["fg"]), ("*Canvas.background", p["bg"]),
                     ("*Menu.background", p["button"]), ("*Menu.foreground", p["fg"]),
                     ("*Toplevel.background", p["bg"])):
        root.option_add(opt, val)


def apply(root, is_dark=None):
    """Put the look on the window (the kept choice when is_dark is None)."""
    if is_dark is None:
        is_dark = settings.get("theme") == "dark"
    first = _state["root"] is None
    _state["root"], _state["dark"] = root, bool(is_dark)
    _style(root)
    if first:
        root.bind_all("<Map>", _mapped, add="+")
        root.bind_all("<Destroy>", lambda e: isinstance(e.widget, str) or _state["done"].pop(str(e.widget), None),
                      add="+")
    try:
        root.configure(background=palette()["bg"])
    except tk.TclError:
        pass
    _walk(root)


def toggle(root):
    apply(root, not _state["dark"])
    settings.put("theme", "dark" if _state["dark"] else "light")
    return _state["dark"]
