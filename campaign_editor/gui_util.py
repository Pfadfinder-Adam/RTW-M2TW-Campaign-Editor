"""Small layout helpers shared by the windows, so a smaller window never hides a button.

A packed widget gets its space in packing order: when a window is too small, the widgets packed last lose it
first. So buttons are packed first and long hint labels last, and a form taller than the window scrolls."""

import itertools
import os
import tkinter as tk
from tkinter import ttk


def first(*widgets):
    """Move packed widgets to the front of their parent's packing order, the last one named first - so they keep
    their room and a hint label packed after them is the one that is cut. Only for widgets packed on the same
    side (moving a side="left" widget also moves it to the left edge)."""
    for w in widgets:
        slaves = w.master.pack_slaves()
        if slaves and slaves[0] is not w:
            w.pack_configure(before=slaves[0])


# ---------------------------------------------------------------------------
# Tcl command names that never come back
# ---------------------------------------------------------------------------
_TCL_SERIAL = itertools.count(1)


def unique_tcl_names():
    """tkinter names the Tcl command of every Python callback after the address of a wrapper object; once the command
    is deleted (its widget gone) Python reuses the address and a new callback can get the old name - a stale reference
    (a call already scheduled, an option of a widget being torn down) then runs the wrong function ("<lambda>()
    missing 1 required positional argument: 'e'", once in thousands of clicks of the click test). A running number
    in every name keeps a deleted command's name from coming back: a stale reference just finds no command."""
    if getattr(tk.Misc, "_ce_unique_names", False):
        return
    real = tk.Misc._register

    def _register(self, func, subst=None, needcleanup=1):
        name = real(self, func, subst, needcleanup)
        new = "ce%d_%s" % (next(_TCL_SERIAL), name)
        self.tk.call("rename", name, new)
        if needcleanup and self._tclCommands and self._tclCommands[-1] == name:
            self._tclCommands[-1] = new
        return new
    tk.Misc._register = tk.Misc.register = _register
    tk.Misc._ce_unique_names = True


# ---------------------------------------------------------------------------
# The mouse wheel: one handler for the whole application
# ---------------------------------------------------------------------------
_WHEEL = {}                        # {widget path: fn(step) -> True when it scrolled}
_WHEEL_ON = set()                  # the Tk interpreters the handler is bound in
WHEEL_KEYS = ("<MouseWheel>", "<Button-4>", "<Button-5>")
SELF_SCROLLING = ("Listbox", "Text", "Treeview")


def wheel(widget, fn):
    """The mouse wheel over widget (or anything inside it) calls fn(step): step -1 = up / back, 1 = down / on;
    fn returns True when it scrolled, else the wheel goes on to the next such widget outside it.
    One handler for the whole application finds the nearest one under the mouse - each window used to bind the wheel
    for everyone on <Enter> and drop it on <Leave>, and a window closed under the mouse left the wheel pointing at a
    widget that was gone. A widget with a wheel of its own (the map's zoom) and a list or text that can scroll itself
    keep theirs. Every wheel turn is one step, however small (a touchpad's): the old int(-delta / 120) made 0."""
    key = str(widget)
    _WHEEL[key] = fn
    widget.bind("<Destroy>", lambda e: _WHEEL.pop(key, None) if str(e.widget) == key else None, add="+")
    interp = id(widget.tk)
    if interp not in _WHEEL_ON:
        _WHEEL_ON.add(interp)
        for seq in WHEEL_KEYS:
            widget.bind_all(seq, _route, add="+")
    return widget


def scroll_y(canvas):
    """A wheel fn for a canvas (or any widget with yview) that scrolls up and down when there is more to see."""
    def fn(step):
        if tuple(canvas.yview()) == (0.0, 1.0):
            return False
        canvas.yview_scroll(step, "units")
        return True
    return fn


def _step(e):
    if getattr(e, "num", None) == 4:
        return -1
    if getattr(e, "num", None) == 5:
        return 1
    d = getattr(e, "delta", 0) or 0
    return 0 if not d else (-1 if d > 0 else 1)


def _route(e):
    step = _step(e)
    if not step:
        return None
    root = e.widget if not isinstance(e.widget, str) else tk._default_root
    try:
        w = root.winfo_containing(e.x_root, e.y_root)
    except (KeyError, tk.TclError, AttributeError):       # an open Combobox list ('popdown') is no tkinter widget
        return None
    if w is None:
        return None
    try:
        if any(w.bind(seq) for seq in WHEEL_KEYS):
            return None                                   # its own wheel (a zoom) did it
        if w.winfo_class() in SELF_SCROLLING and tuple(w.yview()) != (0.0, 1.0):
            return None                                   # the list scrolls itself
    except (tk.TclError, AttributeError):
        pass
    while w is not None:
        fn = _WHEEL.get(str(w))
        if fn is not None:
            try:
                if w.winfo_exists() and fn(step):
                    return "break"
            except tk.TclError:
                _WHEEL.pop(str(w), None)
        w = getattr(w, "master", None)
    return None


class ScrollFrame(ttk.Frame):
    """A frame whose contents (built in .inner) scroll up and down when the window is lower than they are.
    The inner frame is as wide as the visible area, so rows still fill the width; its height is what its
    contents ask for (an expanding list inside does not grow past that)."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._bar_set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self._resize())
        self.canvas.bind("<Configure>", lambda e: self._resize())
        wheel(self, lambda step: bool(self.bar.winfo_ismapped()) and scroll_y(self.canvas)(step))

    def _resize(self):
        # the contents keep the height they ask for (a fixed height would not follow them when they grow)
        cw = self.canvas.winfo_width()
        self.canvas.itemconfigure(self._win, width=cw)
        self.canvas.configure(scrollregion=(0, 0, cw, self.inner.winfo_reqheight()))

    def _bar_set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y", before=self.canvas)
        self.bar.set(lo, hi)



def window_body(w, width=700, height=640, padding=12):
    """A window's room the way every window of the editor should have it: resizable, never taller than the screen,
    the buttons on a bar at the bottom that always stays in sight (.pack into the returned bar), everything else in
    a frame that scrolls when the window is lower than it, its texts wrapping to the window's width as it is
    dragged wider or narrower (the x3 window's buttons slid out of sight as its text grew). -> (frame, bar)."""
    w.resizable(True, True)
    sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
    w.geometry("%dx%d" % (min(width, sw - 40), min(height, sh - 100)))
    w.minsize(min(420, sw - 40), min(300, sh - 100))
    bar = ttk.Frame(w, padding=(padding, 6, padding, padding))
    bar.pack(side="bottom", fill="x")
    sf = ScrollFrame(w)
    sf.pack(fill="both", expand=True)
    frm = ttk.Frame(sf.inner, padding=padding)
    frm.pack(fill="both", expand=True)

    def rewrap(e=None, box=frm):
        width_now = max(200, sf.canvas.winfo_width() - 2 * padding - 20)
        stack = [box]
        while stack:
            x = stack.pop()
            stack.extend(x.winfo_children())
            if x.winfo_class() == "TLabel":
                try:
                    if int(str(x.cget("wraplength")) or 0) > 0:
                        x.configure(wraplength=width_now)
                except (tk.TclError, ValueError):
                    pass
    sf.canvas.bind("<Configure>", lambda e: (sf._resize(), rewrap()), add="+")
    return frm, bar


def scroll_body(w, padding=10):
    """The frame a dialog builds its contents in, inside a frame that scrolls: the window opens as big as its
    contents (never bigger than the screen), can be dragged to any size, and what does not fit scrolls - no
    button or text out of reach. Packed already."""
    sf = ScrollFrame(w)
    sf.pack(fill="both", expand=True)
    frm = ttk.Frame(sf.inner, padding=padding)
    frm.pack(fill="both", expand=True)
    state = {"sized": False}

    def size(e=None):
        # once, on the first showing: sized again on every change, the canvas, its scrollbar and the wrapping texts
        # could chase each other for ever (a window that never settles = an editor that does not respond)
        if state["sized"]:
            return
        state["sized"] = True
        try:
            sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
            rw, rh = frm.winfo_reqwidth(), frm.winfo_reqheight()
            sf.canvas.configure(width=min(rw, sw - 60), height=min(rh, sh - 160))
        except tk.TclError:
            pass
    frm.bind("<Configure>", size, add="+")
    return frm


def keep_on_screen(w):
    """Every window (bound to the class at start): resizable, and never bigger than the screen - a window whose
    contents grow is shrunk to the screen with its title bar in sight. Once per window, on its first showing only,
    never a borderless one (hover tips, menus, the splash): on Windows a style change re-shows a window, and done on
    every showing (with update_idletasks inside the event) it looped for ever - the editor froze ('not responding')."""
    try:
        if not isinstance(w, tk.Toplevel) or getattr(w, "_kept_on_screen", False):
            return
        w._kept_on_screen = True
        if w.overrideredirect():
            return
        if w.resizable() != (True, True):
            w.resizable(True, True)
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        ww, wh = w.winfo_width(), w.winfo_height()
        if ww > sw - 20 or wh > sh - 80:
            w.geometry("%dx%d+%d+%d" % (min(ww, sw - 20), min(wh, sh - 80), 10, 10))
    except tk.TclError:
        pass


class HScroll(ttk.Frame):
    """A row (built in .inner) that scrolls left and right when the window is narrower than it: the mouse wheel
    over it and a press dragged sideways (the row follows the mouse smoothly; a click without a drag is a click) -
    no arrows, no scrollbar taking a line of its own (a tester found arrows slow; the author wants no extra line).
    Nothing in the row is ever cut off for good."""
    STEP = 60
    DRAG = 6                                     # pixels the mouse moves before a press is a drag, not a click

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, xscrollincrement=0)
        self.canvas.pack(side="top", fill="x", expand=True)
        self._wider = False
        self.inner = ttk.Frame(self.canvas)
        self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self._resize())
        self.canvas.bind("<Configure>", lambda e: self._resize())
        wheel(self, lambda step: self.wider() and (self.step(step) or True))
        self._drag = None
        for w in (self.canvas, self.inner):
            self.grab(w)

    def grab(self, w):
        """w (in the row) takes the drag: pressed and moved sideways, the row scrolls with the mouse; a button
        released without a drag is clicked as usual (its own press / release are replaced, so a drag that ends on
        it never clicks it)."""
        w.bind("<ButtonPress-1>", lambda e: self._down(e, w))
        w.bind("<B1-Motion>", self._move)
        w.bind("<ButtonRelease-1>", lambda e: self._up(e, w))

    def _down(self, e, w):
        self._drag = {"x": e.x_root, "moved": False, "w": w}
        self.canvas.scan_mark(e.x_root, 0)
        return "break"

    def _move(self, e):
        d = self._drag
        if not d:
            return "break"
        if not d["moved"] and abs(e.x_root - d["x"]) < self.DRAG:
            return "break"
        d["moved"] = True
        if self.wider():                               # only a row wider than the window moves
            self.canvas.scan_dragto(e.x_root, 0, gain=1)
        return "break"

    def _up(self, e, w):
        d, self._drag = self._drag, None
        if d and not d["moved"] and d["w"] is w and hasattr(w, "invoke"):
            x, y = e.x_root - w.winfo_rootx(), e.y_root - w.winfo_rooty()
            if 0 <= x < w.winfo_width() and 0 <= y < w.winfo_height():
                w.invoke()
        return "break"

    def wider(self):
        """Whether the row is wider than the window (it scrolls then)."""
        return self._wider

    def _resize(self):
        w, h = self.inner.winfo_reqwidth(), self.inner.winfo_reqheight()
        self.canvas.configure(width=w, height=h, scrollregion=(0, 0, w, h))    # asks for the whole row
        wider = w > self.canvas.winfo_width()
        if self._wider and not wider:
            self.canvas.xview_moveto(0)
        self._wider = wider

    def step(self, d):
        total = max(self.inner.winfo_reqwidth(), 1)
        self.canvas.xview_moveto(self.canvas.xview()[0] + d * self.STEP / float(total))

    def show(self, widget):
        """Scroll so that widget (in .inner) is in sight."""
        self.update_idletasks()
        total = max(self.inner.winfo_reqwidth(), 1)
        lo, hi = self.canvas.xview()
        x0, x1 = widget.winfo_x() / total, (widget.winfo_x() + widget.winfo_width()) / total
        if x0 < lo:
            self.canvas.xview_moveto(x0)
        elif x1 > hi:
            self.canvas.xview_moveto(x1 - (hi - lo))



PICTURE_EXT = (".tga", ".dds", ".png", ".jpg", ".jpeg", ".bmp")


def save_copy(parent, path, what="the file"):
    """'Save a copy...' beside an Import / Replace: the file as it is now, saved where the user picks - as it is,
    or as a PNG for a picture (to edit it and bring it back with Import). Never writes into the mod."""
    import shutil
    from tkinter import filedialog, messagebox
    if not path or not os.path.isfile(path):
        messagebox.showerror("Save a copy", "There is no file for %s yet." % what, parent=parent)
        return None
    ext = os.path.splitext(path)[1].lower()
    types = [("As it is (%s)" % ext, "*" + ext)]
    if ext in PICTURE_EXT and ext != ".png":
        types.append(("PNG picture (to edit)", "*.png"))
    out = filedialog.asksaveasfilename(parent=parent, title="Save a copy of %s" % what, initialfile=os.path.basename(
        path), defaultextension=ext, filetypes=types + [("All files", "*.*")])
    if not out:
        return None
    try:
        if os.path.normcase(os.path.abspath(out)) == os.path.normcase(os.path.abspath(path)):
            raise OSError("that is the file itself - pick another folder")
        if out.lower().endswith(".png") and ext != ".png":
            from PIL import Image
            with Image.open(path) as im:
                im.save(out)
        else:
            shutil.copyfile(path, out)
    except Exception as e:
        messagebox.showerror("Save a copy", "Could not save %s: %s" % (out, e), parent=parent)
        return None
    from . import log
    log.write("Saved a copy of %s to %s" % (path, out))
    return out


def fit_first_pane(panes, inner, extra=20):
    """Set a horizontal Panedwindow's first sash to the width its first pane's contents ask for, once, when the
    window first shows it (a ScrollFrame asks for no width of its own)."""
    def fit(e):
        panes.unbind("<Map>")
        panes.update_idletasks()
        panes.sashpos(0, inner.winfo_reqwidth() + extra)
    panes.bind("<Map>", fit)


class FactionBox(ttk.Combobox):
    """A faction picker showing 'turks - Ryazan' (the internal name and the one players see) while its variable
    keeps the internal name, so the code reading it is unchanged. Other values ('(all)', ...) pass as they are."""

    def __init__(self, master, variable, names=(), shown=None, **kw):
        self._real = variable
        self._shown = tk.StringVar()
        self._labels = {}
        self._busy = False
        super().__init__(master, textvariable=self._shown, **kw)
        variable.trace_add("write", self._from_real)
        self._shown.trace_add("write", self._from_shown)
        self.set_names(names, shown or {})

    def set_names(self, names, shown=None):
        from .build import faction_label
        shown = shown or {}
        self._labels = {n: faction_label(n, shown.get(n)) for n in names}
        self["values"] = [self._labels[n] for n in names]
        self._from_real()

    def _from_real(self, *_):
        if self._busy:
            return
        self._busy = True
        try:
            v = self._real.get()
            self._shown.set(self._labels.get(v, v))
        finally:
            self._busy = False

    def _from_shown(self, *_):
        if self._busy:
            return
        self._busy = True
        try:
            s = self._shown.get()
            self._real.set(next((n for n, l in self._labels.items() if l == s), s))
        finally:
            self._busy = False


def flow_places(items, width, gap_y=2):
    """Where flow() puts each widget: items = [(width, height, pad_left, pad_right, side)] in their order on the screen
    (side 'left' or 'right'); -> ([(x, y)] for each item, height of the whole). All on one row when they fit: the
    'left' ones from the left edge, the 'right' ones up to the right edge. Else they wrap as words in a line of text:
    the 'left' ones from the left, then the 'right' ones from a row of their own, each row up to the right edge."""
    need = [w + a + b for w, _, a, b, _ in items]
    places, rows = [None] * len(items), []            # rows: [index, ...] with their side
    lefts = [i for i, it in enumerate(items) if it[4] != "right"]
    rights = [i for i, it in enumerate(items) if it[4] == "right"]
    if sum(need) <= width:
        rows = [(lefts + rights, None)]
    else:
        for group, side in ((lefts, "left"), (rights, "right")):
            row, used = [], 0
            for i in group:
                if row and used + need[i] > width:
                    rows.append((row, side))
                    row, used = [], 0
                row.append(i)
                used += need[i]
            if row:
                rows.append((row, side))
    y = 0
    for row, side in rows:
        line = max(items[i][1] for i in row)
        if side is None:                                # one row: lefts from the left, rights up to the right
            x = 0
            for i in row:
                if items[i][4] == "right":
                    continue
                places[i] = (x + items[i][2], y + (line - items[i][1]) // 2)
                x += need[i]
            x = width - sum(need[i] for i in row if items[i][4] == "right")
        else:
            x = 0 if side == "left" else width - sum(need[i] for i in row)
        for i in row:
            if places[i] is None:
                places[i] = (max(x, 0) + items[i][2], y + (line - items[i][1]) // 2)
                x += need[i]
        y += line + gap_y
    return places, max(y, 1)


def flow(frame):
    """Lay the widgets packed in `frame` out in rows that wrap at the frame's width, as words in a line of text: a
    toolbar with more buttons than the window is wide goes on to a second row instead of hiding the last ones past
    the edge (and never one over another). Those packed side="right" keep to the right edge, in the order they show.
    Call it once the toolbar is built; it follows the window's width - and a button whose words change - from then
    on (flow_places)."""
    items = []
    lefts, rights = [], []
    for w in frame.pack_slaves():
        info = w.pack_info()
        padx = info.get("padx", 0)
        if isinstance(padx, (tuple, list)):
            left, right = int(padx[0]), int(padx[-1])
        else:
            left = right = int(padx or 0)
        (rights if info.get("side") == "right" else lefts).append((w, left, right, info.get("side")))
        w.pack_forget()
    items = lefts + rights[::-1]                    # packed side="right" = the last one packed shows leftmost
    state = {"key": None}

    def reflow(_=None):
        width = frame.winfo_width()
        if width <= 1:
            width = max(frame.winfo_toplevel().winfo_width() - 20, 200)
        live = [it for it in items if it[0].winfo_exists()]
        sizes = [(w.winfo_reqwidth(), w.winfo_reqheight(), a, b, side) for w, a, b, side in live]
        key = (width, tuple(sizes))
        if key == state["key"]:
            return
        state["key"] = key
        places, height = flow_places(sizes, width)
        for (w, _, _, _), (px, py) in zip(live, places):
            w.place(x=px, y=py)
        frame.configure(height=height)
    frame.bind("<Configure>", reflow, add="+")
    for w, _, _, _ in items:                        # new words on a button: its width changes
        w.bind("<Configure>", reflow, add="+")
    frame.after_idle(reflow)


def one_window(cls):
    """Class decorator: a window of which one copy is open at a time - made again while it is open, the open one
    comes to the front (a tester: Settings opened again and again; checked for every tool window)."""
    plain_init = cls.__init__

    def __new__(c, *a, **kw):
        w = c.__dict__.get("_open_one")
        try:
            if w is not None and w.winfo_exists():
                w._reused = True
                return w
        except tk.TclError:
            pass
        return tk.Toplevel.__new__(c)

    def __init__(self, *a, **kw):
        if self.__dict__.pop("_reused", False):
            try:
                self.deiconify()
                self.lift()
                self.focus_force()
            except tk.TclError:
                pass
            return
        plain_init(self, *a, **kw)
        type(self)._open_one = self

    cls.__new__ = __new__
    cls.__init__ = __init__
    return cls


class Tip:
    """A text shown beside a widget while the mouse rests on it - the long explanations live here instead of
    in labels, so the window keeps its room (and longer words of other languages still fit)."""

    def __init__(self, widget, text, delay=400, width=420):
        self.widget, self.text, self.delay, self.width = widget, text, delay, width
        self.win = self.job = None
        widget.bind("<Enter>", self._wait, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _wait(self, ev=None):
        self._hide()
        self.job = self.widget.after(self.delay, self._show)

    def _show(self):
        self.job = None
        text = self.text() if callable(self.text) else self.text
        if not text or not self.widget.winfo_exists():
            return
        self.win = popup_text(self.widget, text, self.width)

    def _hide(self, ev=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.win:
            self.win.destroy()
            self.win = None


def popup_text(widget, text, width=420):
    """A yellow hover box with text under widget, kept inside the screen (above the widget when there is no room
    below, moved left at the right edge). -> the box (a Toplevel)."""
    tw = tk.Toplevel(widget)
    tw.wm_overrideredirect(True)
    lbl = tk.Label(tw, text=text, justify="left", background="#ffffe0", foreground="#1e1e1e", relief="solid",
                   borderwidth=1, wraplength=width, padx=6, pady=4)
    from .theme import leave_alone
    leave_alone(tw, lbl)
    lbl.pack()
    tw.update_idletasks()
    w, h = tw.winfo_reqwidth(), tw.winfo_reqheight()
    sw, sh = widget.winfo_screenwidth(), widget.winfo_screenheight()
    x = widget.winfo_rootx() + 12
    y = widget.winfo_rooty() + widget.winfo_height() + 4
    if y + h > sh - 40:                                   # the taskbar too
        y = max(0, widget.winfo_rooty() - h - 4)
    x = max(0, min(x, sw - w - 4))
    tw.wm_geometry("+%d+%d" % (x, y))
    return tw


def install_window_helpers(root):
    """Things every window of the editor gets, in one place (the testers' reports of 2026-10-02):
    - a new window opens in the middle of the screen (not at the top left);
    - a drop-down list is as wide as its longest line (no cut names);
    - an entry or drop-down whose text is longer than the box shows it whole when the mouse rests on it."""
    import tkinter.font as tkfont

    def seen(w):
        try:
            w.attributes("-alpha", 1.0)
        except tk.TclError:
            pass

    def centre(ev):
        w = ev.widget
        if not isinstance(w, tk.Toplevel) or getattr(w, "_centred", False):
            return
        w._centred = True
        try:
            if w.wm_overrideredirect() or w.winfo_class() != "Toplevel":
                return
            w.update_idletasks()
            ww, wh = max(w.winfo_width(), w.winfo_reqwidth()), max(w.winfo_height(), w.winfo_reqheight())
            sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
            w.wm_geometry("+%d+%d" % (max(0, (sw - ww) // 2), max(0, (sh - wh) // 2 - 20)))
            w.update_idletasks()
        except tk.TclError:
            pass
        finally:
            seen(w)
    root.bind_class("Toplevel", "<Map>", centre, add="+")
    # a new window is see-through until it stands in the middle: it no longer shows at the top left for a moment
    # and then jumps (a tester's report); shown in any case after a moment
    if not getattr(tk.Toplevel, "_hidden_until_centred", False):
        plain_init = tk.Toplevel.__init__

        def init(self, *a, **kw):
            plain_init(self, *a, **kw)
            try:
                self.attributes("-alpha", 0.0)
                self.after(800, lambda: self.winfo_exists() and seen(self))
            except tk.TclError:
                pass
        tk.Toplevel.__init__ = init
        tk.Toplevel._hidden_until_centred = True

    def widen(ev):
        cb = ev.widget

        def later():
            try:
                values = cb.cget("values")
                if not values or not cb.winfo_exists():
                    return
                pop = cb.tk.call("ttk::combobox::PopdownWindow", cb)
                if not cb.tk.call("winfo", "ismapped", pop):
                    return
                font = tkfont.nametofont("TkDefaultFont")
                need = max(font.measure(str(v)) for v in cb.tk.splitlist(values)) + 40
                have = cb.winfo_width()
                if need <= have:
                    return
                sw = cb.winfo_screenwidth()
                need = min(need, sw - 8)
                x = min(cb.winfo_rootx(), sw - need - 4)
                y = int(cb.tk.call("winfo", "rooty", pop))
                h = int(cb.tk.call("winfo", "height", pop))
                cb.tk.call("wm", "geometry", pop, "%dx%d+%d+%d" % (need, h, x, y))
            except tk.TclError:
                pass
        cb.after(1, later)
    root.bind_class("TCombobox", "<Button-1>", widen, add="+")

    # the wheel over a closed list box scrolls the page it sits in and never changes the value: a column of boxes
    # (the Bring window's 'The units they recruit') turned each box it passed and the page never moved (report #109)
    def box_wheel(e):
        _route(e)
        return "break"
    for seq in WHEEL_KEYS:
        root.bind_class("TCombobox", seq, box_wheel)

    state = {"job": None, "win": None}

    def hide(ev=None):
        if state["job"]:
            try:
                root.after_cancel(state["job"])
            except tk.TclError:
                pass
            state["job"] = None
        if state["win"] is not None:
            try:
                state["win"].destroy()
            except tk.TclError:
                pass
            state["win"] = None

    def enter(ev):
        hide()
        w = ev.widget

        def show():
            state["job"] = None
            try:
                text = w.get()
                if not text or not w.winfo_exists():
                    return
                font = tkfont.nametofont("TkTextFont")
                if font.measure(text) <= w.winfo_width() - (28 if w.winfo_class() == "TCombobox" else 8):
                    return
                state["win"] = popup_text(w, text, 560)
            except (tk.TclError, AttributeError):
                pass
        state["job"] = root.after(600, show)
    # a click anywhere but a text field takes the typing cursor out of the field it was in (it kept blinking in the
    # map's Find field after a click on the map)
    def away(ev):
        try:
            w = ev.widget
            if not isinstance(w, tk.Misc) or w.winfo_class() in ("TEntry", "Entry", "TCombobox", "TSpinbox",
                                                                   "Spinbox", "Text", "Menu"):
                return
            now = w.focus_get()
            if now is not None and now is not w and now.winfo_class() in ("TEntry", "Entry", "TCombobox",
                                                                           "TSpinbox", "Spinbox", "Text"):
                w.focus_set()
        except (tk.TclError, KeyError, AttributeError):
            pass
    root.bind_all("<ButtonPress-1>", away, add="+")
    for cls in ("TEntry", "TCombobox", "Entry"):
        root.bind_class(cls, "<Enter>", enter, add="+")
        root.bind_class(cls, "<Leave>", hide, add="+")
        root.bind_class(cls, "<ButtonPress>", hide, add="+")
        root.bind_class(cls, "<KeyPress>", hide, add="+")


def tip(widget, text, **kw):
    """Give a widget a hover text (see Tip); returns the widget."""
    Tip(widget, text, **kw)
    return widget


def hint(parent, text, **kw):
    """A small '?' that shows `text` when the mouse rests on it - in place of a long hint label."""
    lbl = ttk.Label(parent, text=" ? ", foreground="#2050c0", cursor="question_arrow", font=("", 9, "bold"))
    Tip(lbl, text, **kw)
    return lbl


def first_sentence(text, most=160):
    """The text's first sentence (up to `most` characters) - the short line a hint shows."""
    text = " ".join(str(text or "").split())
    for end in (". ", "; ", " - "):
        i = text.find(end)
        if 0 < i < most:
            return text[:i + (1 if end == ". " else 0)]
    return text if len(text) <= most else text[:most].rsplit(" ", 1)[0] + "..."


class ShortHint(ttk.Frame):
    """A one-line hint with a '?' beside it: the first sentence shows, the whole text when the mouse rests on the
    '?' or the line (our rule: long explanations in hover texts, the window keeps its room). Drop-in for a Label:
    configure(text=...)."""

    def __init__(self, master, text="", **kw):
        super().__init__(master)              # a Label's other options (wraplength, justify...) are not needed
        self.full = ""
        self.lbl = ttk.Label(self, foreground=kw.get("foreground", "#555"))
        self.lbl.pack(side="left")
        self.q = ttk.Label(self, text=" ? ", foreground="#2050c0", cursor="question_arrow", font=("", 9, "bold"))
        self.q.pack(side="left")
        Tip(self.q, lambda: self.full, width=560)
        Tip(self.lbl, lambda: self.full, width=560)
        if text:
            self.configure(text=text)
        master.bind("<Configure>", self._fit, add="+")      # the line wraps instead of running past the edge

    def _fit(self, _=None):
        """Wrap the shown sentence at the room the parent gives it (none when it fits on one line)."""
        try:
            from tkinter import font as tkfont
            avail = self.master.winfo_width() - (self.q.winfo_reqwidth() if self.q.winfo_manager() else 0) - 28
            if avail < 80:
                return
            f = tkfont.Font(font=self.lbl.cget("font") or "TkDefaultFont")
            want = avail if f.measure(self.lbl.cget("text")) > avail else 0
            if int(str(self.lbl.cget("wraplength")).strip() or 0) != want:
                self.lbl.configure(wraplength=want, justify="left")
        except Exception:
            pass

    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self.full = kw.pop("text") or ""
            short = first_sentence(self.full)
            self.lbl.configure(text=short)
            self.after_idle(self._fit)
            if short.strip() == self.full.strip():
                self.q.pack_forget()
            elif not self.q.winfo_ismapped():
                self.q.pack(side="left")
        if kw or cnf:
            super().configure(cnf, **kw)
    config = configure


class StepWindow(tk.Toplevel):
    """A window that walks through steps: '1 Start  [2 Names]  3 ...' on top, the step's title, its body, and
    < Back / Next > below (Back and Next keep what was typed). A subclass gives steps [(title, fn)] to
    make_steps; fn fills self.body; self._collect (set by a step) reads its widgets back before leaving it;
    leaving(step) runs after that; the last step's Next is finish_text and calls finish()."""
    finish_text = "Finish"

    def make_steps(self, steps):
        self.step, self.steps = 0, steps
        self._collect = None
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)
        self.crumbs = ttk.Label(outer, foreground="#555")
        self.crumbs.pack(anchor="w")
        self.head = ttk.Label(outer, font=("", 12, "bold"))
        self.head.pack(anchor="w", pady=(2, 6))
        self.body = ttk.Frame(outer)
        self.body.pack(fill="both", expand=True)
        nav = ttk.Frame(outer)
        nav.pack(fill="x", pady=(8, 0))
        self.b_back = ttk.Button(nav, text="< Back", command=lambda: self.go(-1))
        self.b_back.pack(side="left")
        self.b_next = ttk.Button(nav, text="Next >", command=lambda: self.go(1))
        self.b_next.pack(side="left", padx=4)
        ttk.Button(nav, text="Cancel", command=self.destroy).pack(side="right")

    def collect(self):
        """What the step on show holds, into the window's state (called before leaving it)."""
        fn = self._collect
        self._collect = None
        if fn:
            fn()

    def leaving(self, step):
        """Called after a step's widgets were read, before moving on."""

    def finish(self):
        """The last step's button."""

    def go(self, d):
        self.collect()
        if self.leaving(self.step) is False:          # the step said no: stay (it told the user why)
            return self.show()
        if d > 0 and self.step == len(self.steps) - 1:
            return self.finish()
        self.step = max(0, min(len(self.steps) - 1, self.step + d))
        self.show()

    def show(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.crumbs.configure(text="   ".join(("[%d %s]" if i == self.step else "%d %s") % (i + 1, t)
                                            for i, (t, _) in enumerate(self.steps)))
        title, fn = self.steps[self.step]
        self.head.configure(text="Step %d of %d: %s" % (self.step + 1, len(self.steps), title))
        self.b_back.state(["disabled"] if self.step == 0 else ["!disabled"])
        self.b_next.configure(text=self.finish_text if self.step == len(self.steps) - 1 else "Next >")
        self.b_next.state(["!disabled"])
        fn()

    def _note(self, text):
        ttk.Label(self.body, text=text, wraplength=780, justify="left", foreground="#555").pack(anchor="w",
                                                                                                pady=(0, 6))


EXPERIMENTAL = ("Experimental - try it at your own risk (a backup is made first, Restore undoes it). If you tried "
                "it, please send a report: Report a bug / Suggest.")


def experimental(parent):
    """The red line of a window whose feature is still experimental (Campaign rules, Module builder): readable in
    both looks (theme.ink), wrapping to the window's width - never cut at the edge."""
    from . import theme
    lab = ttk.Label(parent, text=EXPERIMENTAL, foreground=theme.ink("#c00000"), justify="left",
                    font=("", 9, "bold"))
    lab.bind("<Configure>", lambda e: lab.configure(wraplength=max(e.width - 4, 200)))
    return lab


def owner_tint(rgb):
    """A list row's background in the muted colour of the faction owning it (its primary colour, softened toward the
    window's own) - who holds a town is seen at a glance; the text stays readable."""
    from . import theme
    if not rgb:
        return None
    base = (40, 42, 46) if theme.dark() else (255, 255, 255)
    k = 0.3 if theme.dark() else 0.32
    return "#%02x%02x%02x" % tuple(int(b + (c - b) * k) for c, b in zip(rgb[:3], base))


def tint_owners(tree, rows, mod):
    """Each Treeview row {iid: owner faction} gets its owner's muted colour (owner_tint) as a tag 'own:<faction>'."""
    from .mapdata import faction_colours
    try:
        colours = faction_colours(mod)
    except Exception:
        return
    for iid, owner in rows.items():
        tag = "own:%s" % owner
        bg = owner_tint(colours.get(owner))
        if not bg or not tree.exists(iid):
            continue
        tree.tag_configure(tag, background=bg)
        tree.item(iid, tags=tuple(t for t in tree.item(iid, "tags") if not str(t).startswith("own:")) + (tag,))


def ask_choice(parent, title, text, choices, default=0, cancel=None, danger=None):
    """A question whose buttons answer it in words (not Yes / No - Microsoft's writing guidelines: the buttons answer
    the title's question); choices = [words, ...] left to right, danger = the index of a destructive one, set apart on
    the left so a hurried click never lands on it (NN/g: destructive next to confirming = slips). Enter picks
    default, Esc / closing the window gives cancel. Returns the index picked (or cancel)."""
    w = tk.Toplevel(parent)
    w.title(title)
    w.transient(parent.winfo_toplevel() if parent is not None else None)
    w.resizable(False, False)
    out = {"k": cancel}
    frm = ttk.Frame(w, padding=14)
    frm.pack(fill="both", expand=True)
    bar = ttk.Frame(frm)                    # the buttons first, at the bottom: never pushed off the screen
    bar.pack(side="bottom", fill="x", pady=(14, 0))
    if len(text) > 900 or text.count("\n") > 18:   # a long text scrolls (a tester's set-up list ran off the screen
        w.resizable(True, True)                     # and the window could not be closed)
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True)
        t = tk.Text(box, wrap="word", width=90, height=min(24, max(8, w.winfo_screenheight() // 40)),
                    relief="flat", font=("", 9))
        sb = ttk.Scrollbar(box, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        t.insert("1.0", text)
        t.configure(state="disabled")
    else:
        ttk.Label(frm, text=text, justify="left", wraplength=480).pack(anchor="w")

    def pick(k):
        out["k"] = k
        w.destroy()
    for k in reversed(range(len(choices))):
        if k == danger:
            continue
        b = ttk.Button(bar, text=choices[k], command=lambda k=k: pick(k))
        b.pack(side="right", padx=(6, 0))
        if k == default:
            b.focus_set()
    if danger is not None:
        ttk.Button(bar, text=choices[danger], command=lambda: pick(danger)).pack(side="left")
    w.bind("<Return>", lambda e: pick(default))
    w.bind("<Escape>", lambda e: pick(cancel))
    w.protocol("WM_DELETE_WINDOW", lambda: pick(cancel))
    w.update_idletasks()
    try:
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w.geometry("+%d+%d" % (px + max(0, (pw - w.winfo_reqwidth()) // 2),
                               py + max(0, (ph - w.winfo_reqheight()) // 3)))
    except tk.TclError:
        pass
    try:
        w.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(w)
    return out["k"]


def close_guard(w, title, dirty, write, after=None):
    """Closing a window never throws its work away silently (NN/g 'close-as-discard'): dirty() -> words of what is
    neither written nor kept for the write (or '' / None); with it, Close asks 'Keep for Apply / Keep editing /
    Throw the changes away' - the throw-away apart on the left, Enter keeps, Esc keeps editing. write() is the
    window's own keep (it may still refuse - then the window stays). after() runs before the window goes (its app
    slot cleared). Returns the close function for the window's Close button; the title bar's X does the same."""
    def close():
        try:
            what = dirty()
        except Exception:
            what = "changes"
        if what:
            k = ask_choice(w, title, "The changes made here are not kept for the write yet%s.\n\nKeep them (Apply "
                                     "changes in the main window writes them with everything else), keep editing, or "
                                     "throw them away?" % ((" (%s)" % what) if isinstance(what, str) else ""),
                           ["Keep for Apply", "Keep editing", "Throw the changes away"], default=0, cancel=1, danger=2)
            if k == 1 or k is None:
                return
            if k == 0:
                write()
                try:
                    if not w.winfo_exists() or dirty():
                        return                     # not kept (refused): keep the window
                except tk.TclError:
                    return
        if after:
            after()
        try:
            w.destroy()
        except tk.TclError:
            pass
    w.protocol("WM_DELETE_WINDOW", close)
    return close


def _plan_content(plan):
    return ({p: f.dump() for p, f in plan.files.items() if f.dump() != plan.originals.get(p)},
            dict(plan.binaries), list(plan.copies), list(plan.deletions))


def kept_or_not(app, key, make_plan):
    """Words of what a window holds that is neither unchanged nor exactly what it kept for the write, or ''."""
    try:
        plan = make_plan()
    except Exception:
        return "changes"
    files = plan.changed_files()
    if not files:
        return ""
    part = app.session_parts().get(key) if hasattr(app, "session_parts") else None
    if part is not None and _plan_content(part["plan"]) == _plan_content(plan):
        return ""
    return "%d file(s) to change" % len(files)


def keep_for_apply(win, key, label, make_plan, after=None, title=None):
    """A window's 'Keep for Apply': its changes made into a plan now (a mistake said at once) and put in the session's
    list (App.session_add) - written by the main window's Apply changes with everything else, in one go. False when
    nothing changed or the plan refused."""
    from tkinter import messagebox
    try:
        plan = make_plan()
    except Exception as e:
        messagebox.showerror(title or label, str(e), parent=win)
        return False
    if not plan.changed_files():
        messagebox.showinfo(title or label, "Nothing changed yet.", parent=win)
        return False
    win.app.session_add(key, label, plan, after)
    return True
