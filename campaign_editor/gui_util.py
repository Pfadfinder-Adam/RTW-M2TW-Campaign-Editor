"""Small layout helpers shared by the windows, so a smaller window never hides a button.

A packed widget gets its space in packing order: when a window is too small, the widgets packed last lose it
first. So buttons are packed first and long hint labels last, and a form taller than the window scrolls."""

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
        self.bind("<Enter>", lambda e: self._wheel(True))
        self.bind("<Leave>", lambda e: self._wheel(self._inside(e)))

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

    def _wheel(self, on):
        if on:
            self.bind_all("<MouseWheel>", self._on_wheel)
            self.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
            self.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        else:
            for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.unbind_all(ev)

    def _inside(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except KeyError:        # an open Combobox list ('popdown') is not a tkinter widget
            return False
        return w is not None and str(w).startswith(str(self))

    def _on_wheel(self, e):
        if self.bar.winfo_ismapped() and self._inside(e):
            self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")


class HScroll(ttk.Frame):
    """A row (built in .inner) that scrolls left and right when the window is narrower than it: arrows at its
    ends then, and the mouse wheel over it. Nothing in the row is ever cut off for good."""
    STEP = 60

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.back = ttk.Button(self, text="\u25c0", width=2, command=lambda: self.step(-1))
        self.fore = ttk.Button(self, text="\u25b6", width=2, command=lambda: self.step(1))
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, xscrollincrement=self.STEP)
        self.canvas.pack(side="left", fill="x", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self._resize())
        self.canvas.bind("<Configure>", lambda e: self._resize())
        self.bind("<Enter>", lambda e: self._wheel(True))
        self.bind("<Leave>", lambda e: self._wheel(False))

    def _resize(self):
        w, h = self.inner.winfo_reqwidth(), self.inner.winfo_reqheight()
        self.canvas.configure(width=w, height=h, scrollregion=(0, 0, w, h))    # asks for the whole row
        if w > self.canvas.winfo_width() + (self.back.winfo_width() * 2 if self.back.winfo_ismapped() else 0):
            if not self.back.winfo_ismapped():
                # packed before the canvas, so the canvas (asking for the whole row) is the one that shrinks
                self.back.pack(side="left", fill="y", before=self.canvas)
                self.fore.pack(side="right", fill="y", before=self.canvas)
        elif self.back.winfo_ismapped():
            self.back.pack_forget()
            self.fore.pack_forget()
            self.canvas.xview_moveto(0)

    def step(self, d):
        self.canvas.xview_scroll(d, "units")

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

    def _wheel(self, on):
        if on and self.back.winfo_ismapped():
            self.bind_all("<MouseWheel>", lambda e: self.step(-1 if e.delta > 0 else 1))
            self.bind_all("<Shift-MouseWheel>", lambda e: self.step(-1 if e.delta > 0 else 1))
            self.bind_all("<Button-4>", lambda e: self.step(-1))
            self.bind_all("<Button-5>", lambda e: self.step(1))
        else:
            for ev in ("<MouseWheel>", "<Shift-MouseWheel>", "<Button-4>", "<Button-5>"):
                self.unbind_all(ev)


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


def flow(frame):
    """Lay the widgets packed side="left" in `frame` out in rows that wrap at the frame's width, as words in a line
    of text: a toolbar with more buttons than the window is wide goes on to a second row instead of hiding the last
    ones past the edge. Call it once the toolbar is built; it follows the window's width from then on."""
    items = []
    for w in frame.pack_slaves():
        padx = w.pack_info().get("padx", 0)
        if isinstance(padx, (tuple, list)):
            left, right = int(padx[0]), int(padx[-1])
        else:
            left = right = int(padx or 0)
        items.append((w, left, right))
        w.pack_forget()
    state = {"key": None}

    def reflow(_=None):
        width = frame.winfo_width()
        if width <= 1:
            width = max(frame.winfo_toplevel().winfo_width() - 20, 200)
        places, x, y, line = [], 0, 0, 0
        for w, left, right in items:
            need = w.winfo_reqwidth() + left + right
            if x and x + need > width:
                x, y, line = 0, y + line + 2, 0
            h = w.winfo_reqheight()
            places.append((w, x + left, y, h))
            x += need
            line = max(line, h)
        height = y + line + 2
        key = (width, tuple((p[1], p[2]) for p in places))
        if key == state["key"]:
            return
        state["key"] = key
        rows = {}
        for w, px, py, h in places:
            rows[py] = max(rows.get(py, 0), h)
        for w, px, py, h in places:
            w.place(x=px, y=py + (rows[py] - h) // 2)
        frame.configure(height=height)
    frame.bind("<Configure>", reflow, add="+")
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

    def configure(self, cnf=None, **kw):
        if "text" in kw:
            self.full = kw.pop("text") or ""
            short = first_sentence(self.full)
            self.lbl.configure(text=short)
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

