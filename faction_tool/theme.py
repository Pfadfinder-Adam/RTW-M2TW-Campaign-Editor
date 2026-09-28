"""Light and dark look of the window. ttk widgets take the colours from one
'clam' style; plain tk widgets (lists, text boxes, canvases, buttons) are
recoloured one by one, also those made later (a <Map> binding on every widget):
neutral light colours become the dark palette's, dark text becomes light, and
colours that mean something (a changed field's yellow, a faction's colour) stay.
The choice is kept in faction_tool_settings.json ('theme')."""

import tkinter as tk
from tkinter import ttk

from . import settings

LIGHT = {"bg": "#f0f0f0", "fg": "#1e1e1e", "field": "#ffffff", "muted": "#555555", "border": "#b4b4b4",
         "select": "#3874d8", "selectfg": "#ffffff", "accent": "#cfe3ff", "tab": "#dcdcdc", "trough": "#e2e2e2",
         "button": "#e6e6e6", "active": "#d5e4f7"}
DARK = {"bg": "#2b2d31", "fg": "#e3e3e3", "field": "#1e1f22", "muted": "#a9adb3", "border": "#4b4e55",
        "select": "#3d6fb8", "selectfg": "#ffffff", "accent": "#35598c", "tab": "#35373c", "trough": "#232428",
        "button": "#3a3d43", "active": "#46505e"}

# colours the window sets by hand that belong to the palette, not to a meaning
NAMED = {"#cfe3ff": "accent"}

BG_KEYS = ("field", "bg", "tab", "button", "trough", "accent", "active", "select")
FG_KEYS = ("fg", "muted", "selectfg")
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


def _rgb(root, colour):
    try:
        r, g, b = root.winfo_rgb(colour)
        return r >> 8, g >> 8, b >> 8
    except tk.TclError:
        return None


def _neutral(rgb):
    return rgb is not None and max(rgb) - min(rgb) <= 24


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def _translate(root, opt, value, bg_orig):
    """The dark palette's colour for a light one, or None to keep it."""
    if not value:
        return None
    rgb = _rgb(root, value)
    if rgb is None:
        return None
    cur = palette()
    hx = _hex(rgb)
    # a palette colour (set while the other look was on) becomes this palette's
    for k in (BG_KEYS if opt in BG_OPTS else FG_KEYS):
        for pal in (LIGHT, DARK):
            if _hex(_rgb(root, pal[k])) == hx:
                return cur[k]
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
    for opt, value in now.items():
        new = _translate(root, opt, value, bg)
        if new is not None and new != value:
            try:
                w.configure(**{opt: new})
            except tk.TclError:
                pass


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
    st.configure("TButton", background=p["button"], padding=(8, 3))
    st.map("TButton", background=[("pressed", p["accent"]), ("active", p["active"])])
    st.configure("TMenubutton", background=p["button"])
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
    # the tabs stand out: bigger, bold, the one open coloured like the work bar's button
    st.configure("TNotebook", background=p["bg"], tabmargins=(2, 4, 2, 0))
    st.configure("TNotebook.Tab", background=p["tab"], foreground=p["fg"], padding=(16, 6),
                 font=("", 10, "bold"))
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
