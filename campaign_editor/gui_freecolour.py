"""The window 'Recolour freely': any one picture (a battle texture, a figure's texture, a card, a button...) with
colours the modder picks on it (freecolour.py). A click on the 'now' picture takes a colour and starts a change; its
new colour is picked (or turned with the sliders: hue, saturation, lightness); 'alike' says how far a colour may lie
and still count; the brush on the 'after' picture adds to a change's area or keeps pixels out. Several changes, one
after another. What is made waits for Apply changes by itself as a recipe (gui_util.AutoKeep, as Recolour): the
picture is worked out and written by Preview changes / Apply changes (one backup; Restore gives it back)."""

import os
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from . import freecolour as F
from . import theme
from .gui_util import AutoKeep, ShortHint, hint

TITLE = "Recolour freely"
SIDE = 380
SAVE_WORDS = ("No Save needed: each change is kept by itself (Close keeps it too) - Apply changes in the main "
              "window writes the picture, with a backup")

_OPEN = {}                                     # (picture, crop) -> its window (one window a picture)


def _hex(c):
    return "#%02x%02x%02x" % tuple(c) if c else "#ffffff"


def app_of(widget):
    """The main window (it holds the mod and Apply changes' list) from any widget of the editor."""
    root = widget._root() if widget is not None else None
    return root if getattr(root, "mod", None) is not None and hasattr(root, "session_add") else None


def open_free(widget, path, crop=None, unit=None, title=None):
    """The window for the picture at path (crop: a part of a sheet; unit (unit, key, index, faction, words): the
    texture of one unit's line - 'only this unit' offered). The open one comes forward. Said in words when the picture
    is no file on disk (inside the game's packs) or cannot be read."""
    app = app_of(widget)
    parent = widget.winfo_toplevel() if widget is not None else None
    if app is None:
        messagebox.showinfo(TITLE, "Open a mod first.", parent=parent)
        return None
    if not path or not os.path.isfile(path):
        messagebox.showinfo(TITLE, "%s is inside the game's packs, not a file of its own - Save a copy... (or Your "
                                   "own files... for a battle model) brings it out first." % os.path.basename(
                                       path or "This picture"), parent=parent)
        return None
    key = (os.path.normcase(os.path.abspath(path)), tuple(crop) if crop else None)
    w = _OPEN.get(key)
    if w is not None:
        try:
            if w.winfo_exists():
                w.deiconify()
                w.lift()
                return w
        except tk.TclError:
            pass
    try:
        w = FreeRecolourWindow(app, path, crop=crop, unit=unit, title=title, parent=parent)
    except Exception as e:                       # no Pillow, or a file it cannot read
        messagebox.showinfo(TITLE, "%s cannot be recoloured here: %s" % (os.path.basename(path), e), parent=parent)
        return None
    _OPEN[key] = w
    return w


class FreeRecolourWindow(AutoKeep, tk.Toplevel):
    _ak_fields = ("swaps", "scope")

    def __init__(self, app, path, crop=None, unit=None, title=None, parent=None):
        from .recolour import read_picture
        im = read_picture(path)
        if crop:
            x, y, w, h = crop
            im = im.crop((x, y, x + w, y + h))
        tk.Toplevel.__init__(self, parent or app)
        self.app, self.mod, self.path, self.crop, self.unit = app, app.mod, path, crop, unit
        self.im = im
        self.swaps, self.cur, self.scope = [], None, "all"
        self.zoom, self._photos, self._new = 1.0, [], None
        self._ak_busy = True
        self.title("%s - %s" % (TITLE, title or os.path.basename(path)))
        self.transient(parent or app)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.side = max(200, min(SIDE, (min(sw, 1500) - 520) // 2, sh - 430))
        self.minsize(760, 520)
        self._build()
        self.show()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())
        self.ak_start()

    # ---- the window ----
    def _build(self):
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill="both", expand=True)
        ShortHint(outer, text=(
            "Any colour of this picture made another. Click a colour on the 'now' picture: every part of a colour "
            "like it changes (its light and dark shades too - the folds stay), faces and hands are left alone. Pick "
            "the new colour, or turn it with the sliders. Several changes one after another; the brush on 'after' "
            "adds to a change or keeps pixels as they were. Written in the picture's own format, with a backup - "
            "Restore gives it back.")).pack(anchor="w", pady=(0, 6))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(left, text="Changes", font=("", 9, "bold")).pack(anchor="w")
        lst = ttk.Frame(left)
        lst.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(lst, columns=("to", "where"), show="tree headings", height=8, selectmode="browse")
        self.tree.heading("#0", text="From")
        self.tree.heading("to", text="To")
        self.tree.heading("where", text="Where")
        for c, w in (("#0", 80), ("to", 80), ("where", 140)):
            self.tree.column(c, width=w, stretch=False)
        sb = ttk.Scrollbar(lst, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._selected())
        self.tree.bind("<Delete>", lambda e: self.remove())
        btns = ttk.Frame(left)
        btns.pack(anchor="w", pady=(4, 0))
        ttk.Button(btns, text="Remove", command=self.remove).pack(side="left")
        ttk.Button(btns, text="Remove all", command=self.clear).pack(side="left", padx=4)
        # the picked change's colours and reach
        box = ttk.LabelFrame(left, text="The picked change", padding=6)
        box.pack(fill="x", pady=(8, 0))
        row = ttk.Frame(box)
        row.pack(anchor="w")
        ttk.Label(row, text="from").pack(side="left")
        self.sw_from = ttk.Button(row, width=3, command=lambda: self._choose("from"))
        self.sw_from.pack(side="left", padx=(2, 10))
        ttk.Label(row, text="to").pack(side="left")
        self.sw_to = ttk.Button(row, width=3, command=lambda: self._choose("to"))
        self.sw_to.pack(side="left", padx=2)
        hint(row, "'from': the colour clicked on the 'now' picture (a click on its swatch picks another by hand). "
                  "'to': the new colour - a click on its swatch picks it; the sliders below turn it from 'from' "
                  "(hue round the colour wheel, saturation and lightness as a share of the old one's).").pack(
            side="left", padx=4)
        self.v_hue, self.v_sat, self.v_light, self.v_alike = (tk.IntVar(value=v) for v in (0, 100, 100, F.ALIKE))
        for text, var, a, b in (("hue", self.v_hue, -180, 180), ("saturation %", self.v_sat, 0, 200),
                                ("lightness %", self.v_light, 0, 200), ("alike", self.v_alike, 0, 100)):
            r = ttk.Frame(box)
            r.pack(fill="x", pady=1)
            ttk.Label(r, text=text, width=12).pack(side="left")
            ttk.Scale(r, from_=a, to=b, variable=var, orient="horizontal", length=150,
                      command=lambda v, var=var: self._slid(var)).pack(side="left")
            ttk.Label(r, textvariable=var, width=4).pack(side="left", padx=2)
        hint(box, "'alike': how far a colour may lie from 'from' and still change - more takes more shades (and "
                  "at last neighbouring colours), less only the clicked colour itself.").pack(anchor="w")
        self.v_joined = tk.BooleanVar(value=False)
        ttk.Checkbutton(box, text="only the area joined to the click", variable=self.v_joined,
                        command=self._joined).pack(anchor="w", pady=(4, 0))
        self.v_show = tk.BooleanVar(value=False)
        ttk.Checkbutton(box, text="show its area on 'after'", variable=self.v_show, command=self.show).pack(
            anchor="w")
        # where it is written
        self.v_scope = tk.StringVar(value=self.scope)
        if self.unit:
            sc = ttk.LabelFrame(left, text="Written for", padding=6)
            sc.pack(fill="x", pady=(8, 0))
            ttk.Radiobutton(sc, text="everyone wearing this texture", value="all", variable=self.v_scope,
                            command=self._scoped).pack(anchor="w")
            ttk.Radiobutton(sc, text="only %s" % self.unit[4], value="unit", variable=self.v_scope,
                            command=self._scoped).pack(anchor="w")
            hint(sc, "Everyone: the texture itself changes - every unit and faction wearing it sees the new colours "
                     "(a texture that is the game's own is copied, the model's lines pointed at the copy). Only "
                     "this unit: it gets a model of its own with the recoloured texture (as Your own files...), "
                     "the other units keep their look.", width=360).pack(anchor="w")
        # the pictures
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        pics = ttk.Frame(right)
        pics.pack(anchor="w")
        ttk.Label(pics, text="now - click a colour").grid(row=0, column=0)
        ttk.Label(pics, text="after - the brush paints here").grid(row=0, column=1)
        self.now_pic = tk.Canvas(pics, width=self.side, height=self.side, highlightthickness=1,
                                 highlightbackground="#999", cursor="crosshair")
        self.after_pic = tk.Canvas(pics, width=self.side, height=self.side, highlightthickness=1,
                                   highlightbackground="#999", cursor="pencil")
        self.now_pic.grid(row=1, column=0, padx=4)
        self.after_pic.grid(row=1, column=1, padx=4)
        n, a = self.now_pic, self.after_pic
        n.bind("<ButtonPress-1>", self._eyedrop)
        n.bind("<Shift-ButtonPress-1>", lambda e: self._eyedrop(e, again=True))
        a.bind("<ButtonPress-1>", self._paint)
        a.bind("<B1-Motion>", self._paint)
        a.bind("<ButtonRelease-1>", lambda e: self._painted())
        for c in (n, a):
            for seq, step in (("<MouseWheel>", None), ("<Button-4>", 1), ("<Button-5>", -1)):
                c.bind(seq, lambda e, st=step: self._wheel(e, st))
            c.bind("<ButtonPress-3>", lambda e: self._scan(e, True))
            c.bind("<B3-Motion>", lambda e: self._scan(e, False))
        tools = ttk.Frame(right)
        tools.pack(anchor="w", pady=(6, 0))
        ttk.Label(tools, text="Brush:").pack(side="left")
        self.v_brush = tk.StringVar(value="add")
        ttk.Radiobutton(tools, text="add to the change", value="add", variable=self.v_brush).pack(side="left", padx=4)
        ttk.Radiobutton(tools, text="keep as it was", value="keep", variable=self.v_brush).pack(side="left", padx=4)
        self.v_size = tk.IntVar(value=4)
        ttk.Spinbox(tools, from_=1, to=60, textvariable=self.v_size, width=4).pack(side="left", padx=(8, 2))
        ttk.Label(tools, text="px").pack(side="left")
        hint(tools, "A click on 'now' starts a new change with the colour under the mouse (Shift + click: the picked "
                    "change takes that colour instead). Left drag on 'after' paints the picked change's area: 'add' "
                    "takes in what the colour test missed, 'keep as it was' gives pixels back. The brush size is in "
                    "the picture's own pixels. Wheel: zoom (both pictures), right drag: move.").pack(
            side="left", padx=6)
        self.lbl = ttk.Label(right, foreground="#555", justify="left", wraplength=2 * self.side)
        self.lbl.pack(anchor="w", pady=(6, 0))
        bot = ttk.Frame(outer)
        bot.pack(fill="x", pady=(8, 0))
        self.status = ttk.Label(bot, foreground="#555")
        self.status.pack(side="left")
        self._ak_line = ttk.Label(bot, foreground="#a33")
        self._ak_line.pack(side="left", padx=8)
        ttk.Button(bot, text="Close", command=self.close).pack(side="right")
        # no Save button by design (AutoKeep) - said where the modder looks for one (report #425: 'where is Save?')
        ttk.Label(bot, text=SAVE_WORDS, foreground="#555").pack(side="right", padx=8)

    # ---- the list of changes ----
    def fill(self):
        t = self.tree
        t.delete(*t.get_children(""))
        for i, sw in enumerate(self.swaps):
            where = ("joined area" if sw.get("at") else "everywhere") + (" + brush" if sw.get("add") or
                                                                          sw.get("keep") else "")
            t.insert("", "end", iid=str(i), text=_hex(sw["from"]), values=(_hex(sw["to"]), where))
        if self.cur is not None and self.cur < len(self.swaps):
            t.selection_set(str(self.cur))
        self._paint_controls()

    def _selected(self):
        sel = self.tree.selection()
        self.cur = int(sel[0]) if sel else None
        self._paint_controls()
        self.show()

    def _now(self):
        return self.swaps[self.cur] if self.cur is not None and self.cur < len(self.swaps) else None

    def _paint_controls(self):
        sw = self._now()
        self._quiet = True
        try:
            theme.paint(self.sw_from, _hex(sw["from"]) if sw else "#dddddd", text="" if sw else "-")
            theme.paint(self.sw_to, _hex(sw["to"]) if sw else "#dddddd", text="" if sw else "-")
            hsl = (sw or {}).get("hsl") or (0, 100, 100)
            for var, v in zip((self.v_hue, self.v_sat, self.v_light), hsl):
                var.set(v)
            self.v_alike.set(sw.get("alike", F.ALIKE) if sw else F.ALIKE)
            self.v_joined.set(bool(sw and sw.get("at")))
        finally:
            self._quiet = False

    def remove(self):
        if self._now() is None:
            return
        del self.swaps[self.cur]
        self.cur = min(self.cur, len(self.swaps) - 1) if self.swaps else None
        self._changed()

    def clear(self):
        if self.swaps:
            self.swaps, self.cur = [], None
            self._changed()

    def _changed(self):
        self.fill()
        self.show()
        self.ak_changed()

    # ---- colours ----
    def _xy(self, canvas, e):
        return canvas.canvasx(e.x) / self.k, canvas.canvasy(e.y) / self.k

    def _eyedrop(self, e, again=False):
        x, y = self._xy(self.now_pic, e)
        if not (0 <= x < self.im.size[0] and 0 <= y < self.im.size[1]):
            return "break"
        px = self.im.getpixel((int(x), int(y)))
        if len(px) > 3 and px[3] == 0:
            self.status.configure(text="see-through there - no colour to take")
            return "break"
        rgb = tuple(px[:3])
        sw = self._now()
        if again and sw is not None:                  # Shift + click: the picked change takes this colour
            sw["from"] = rgb
            sw["click"] = (int(x), int(y))
            if sw.get("at"):
                sw["at"] = sw["click"]
            sw["to"] = F.hsl_target(rgb, *(sw.get("hsl") or (0, 100, 100)))
        else:
            last = self.swaps[-1] if self.swaps else None
            hsl = (last.get("hsl") if last else None) or (120, 100, 100)
            sw = F.swap(rgb, F.hsl_target(rgb, *hsl), self.v_alike.get(),
                        (int(x), int(y)) if self.v_joined.get() else None)
            sw["hsl"], sw["click"] = hsl, (int(x), int(y))       # the point 'only the joined area' starts from
            self.swaps.append(sw)
            self.cur = len(self.swaps) - 1
        self.status.configure(text="colour %s taken at %d, %d" % (_hex(rgb), x, y))
        self._changed()
        return "break"

    def _choose(self, side):
        sw = self._now()
        if sw is None:
            self.status.configure(text="click a colour on the 'now' picture first")
            return
        got = colorchooser.askcolor(color=_hex(sw[side]), parent=self, title="'%s' colour" % side)
        if not got or not got[0]:
            return
        sw[side] = tuple(int(v) for v in got[0])
        if side == "to":
            sw["hsl"] = None                           # picked by hand: the sliders start again from it
        else:
            sw["to"] = F.hsl_target(sw["from"], *(sw.get("hsl") or (0, 100, 100))) if sw.get("hsl") else sw["to"]
        self._changed()

    def _slid(self, var):
        var.set(int(round(float(var.get()))))
        sw = self._now()
        if getattr(self, "_quiet", False) or sw is None:
            return
        if var is self.v_alike:
            sw["alike"] = self.v_alike.get()
        else:
            sw["hsl"] = (self.v_hue.get(), self.v_sat.get(), self.v_light.get())
            sw["to"] = F.hsl_target(sw["from"], *sw["hsl"])
        self._soon_show()

    def _soon_show(self):
        """A slider moved: the pictures again a moment later (a 1024 px texture at every step was slow)."""
        if getattr(self, "_job", None):
            self.after_cancel(self._job)
        self._job = self.after(120, self._slid_done)

    def _slid_done(self):
        self._job = None
        self.fill()
        self.show()
        self.ak_changed()

    def _joined(self):
        sw = self._now()
        if sw is None:
            return
        if self.v_joined.get():
            sw["at"] = sw.get("click") or self._first_at(sw)
        else:
            sw["click"], sw["at"] = sw.get("at"), None
        self._changed()

    def _first_at(self, sw):
        """A point of the change's colour (the joined area needs one): the first pixel of its mask."""
        m = F.pick_mask(self.im, sw["from"], sw.get("alike", F.ALIKE))
        box = m.getbbox()
        if not box:
            return None
        px = m.load()
        for y in range(box[1], box[3]):
            for x in range(box[0], box[2]):
                if px[x, y] >= 128:
                    return (x, y)
        return None

    def _scoped(self):
        self.scope = self.v_scope.get()
        self.ak_changed()

    # ---- the pictures ----
    def show(self):
        from PIL import Image, ImageTk
        im = self.im
        try:
            new, share = F.changed(im, self.swaps)
        except Exception as e:
            self.lbl.configure(text="cannot be worked out: %s" % e)
            return
        self._new = new
        fit = min(self.side / im.size[0], self.side / im.size[1], 8.0)
        k = self.k = fit * self.zoom
        big = (max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k)))
        shown = new
        sw = self._now()
        if self.v_show.get() and sw is not None:
            m = F.mask_of(im, sw)
            tint = Image.new("RGBA", im.size, (255, 0, 255, 255))
            shown = new.convert("RGBA").copy()
            shown.paste(tint, (0, 0), m.point(lambda v: v * 3 // 5))
        rs = Image.NEAREST if k >= 1 else Image.LANCZOS
        self._photos = [ImageTk.PhotoImage(self._board(im.resize(big, rs))),
                        ImageTk.PhotoImage(self._board(shown.resize(big, rs)))]
        for c, ph in zip((self.now_pic, self.after_pic), self._photos):
            c.delete("all")
            c.create_image(0, 0, image=ph, anchor="nw")
            c.configure(scrollregion=(0, 0, big[0], big[1]))
        from .gui_picview import describe
        self.lbl.configure(text="%s%s\n%d change(s), %.0f%% of the picture changed%s" % (
            describe(self.path, self.im), " (a part of the sheet)" if self.crop else "", len(self.swaps),
            100 * share, "" if self.swaps else " - click a colour on 'now' to start"))

    @staticmethod
    def _board(im):
        """See-through parts shown over a checkerboard (8 px squares)."""
        from PIL import Image
        im = im.convert("RGBA")
        cw, ch = im.size[0] // 8 + 1, im.size[1] // 8 + 1
        small = Image.new("L", (cw, ch))
        small.putdata([200 if (x + y) % 2 == 0 else 150 for y in range(ch) for x in range(cw)])
        board = small.resize((cw * 8, ch * 8), Image.NEAREST).crop((0, 0) + im.size).convert("RGBA")
        board.alpha_composite(im)
        return board

    def _wheel(self, e, step):
        up = (step or (1 if getattr(e, "delta", 0) > 0 else -1)) > 0
        self.zoom = min(8.0, self.zoom * 1.5) if up else max(1.0, self.zoom / 1.5)
        self.show()
        return "break"

    def _scan(self, e, start):
        for c in (self.now_pic, self.after_pic):           # both move together: the same spot in each
            if start:
                c.scan_mark(e.x, e.y)
            else:
                c.scan_dragto(e.x, e.y, gain=1)

    # ---- the brush ----
    def _paint(self, e):
        if self._now() is None:
            if str(e.type) in ("ButtonPress", "4"):
                self.status.configure(text="click a colour on the 'now' picture first - the brush paints a change")
            return
        a = self.after_pic
        x, y = a.canvasx(e.x), a.canvasy(e.y)
        r = max(1, self.v_size.get()) * self.k / 2.0
        colour = "#ff00ff" if self.v_brush.get() == "add" else "#00c0ff"
        a.create_oval(x - r, y - r, x + r, y + r, outline=colour, fill=colour)
        self._stroke = getattr(self, "_stroke", []) + [(x / self.k, y / self.k)]

    def _painted(self):
        pts, self._stroke = getattr(self, "_stroke", []), []
        sw = self._now()
        if not pts or sw is None:
            return
        from PIL import Image, ImageDraw
        from .recolour import dab
        which = self.v_brush.get()
        size = self.v_size.get()
        for name in ("add", "keep"):
            m = sw.get(name) or Image.new("L", self.im.size, 0)
            d = ImageDraw.Draw(m)
            for x, y in pts:
                d.ellipse(dab(x, y, size), fill=255 if name == which else 0)
            sw[name] = m if m.getbbox() else None
        self._changed()

    # ---- kept by itself, as a recipe (gui_util.AutoKeep) ----
    def _ak_key(self):
        return "freecolour:%s%s" % (os.path.normcase(os.path.abspath(self.path)),
                                    ":%d,%d,%d,%d" % tuple(self.crop) if self.crop else "")

    def _ak_label(self):
        return "%s: %s (%d change(s)%s)" % (TITLE, os.path.basename(self.path), len(self.swaps),
                                            ", only %s" % self.unit[4] if self.unit and self.scope == "unit" else "")

    def _ak_set(self, st):
        import pickle
        for a, v in zip(self._ak_fields, pickle.loads(st)):
            setattr(self, a, v)
        self.v_scope.set(self.scope)
        self.cur = (min(self.cur, len(self.swaps) - 1) if self.cur is not None else len(self.swaps) - 1) \
            if self.swaps else None
        self.fill()
        self.show()

    def _plan(self):
        from .plan import Plan
        from .moddata import ModData
        mod = ModData(self.app.mod.data)               # the files as the parts before it left them
        plan = Plan(mod, "recolour", "free_recolour", {})
        unit = self.unit[:4] if self.unit and self.scope == "unit" else None
        F.plan_free(plan, self.path, [dict(s) for s in self.swaps], crop=self.crop, unit=unit)
        return plan

    def ak_keep(self):
        """The recipe into Apply changes' list - the picture is worked out when Preview / Apply builds it (a DXT
        texture takes a moment: never at every click); no change takes it out."""
        self._ak_job = None
        key = self._ak_key()
        if not any(s["from"] != s["to"] for s in self.swaps):
            self.app.session_drop(key)
            self._ak_saw(None)
            return
        self.app.session_add(key, self._ak_label(), None, self._ak_after, build=self._plan, quiet=True)
        self.app.__dict__.setdefault("_ak_windows", {})[key] = self
        self._ak_saw(self._ak_last)

    def _ak_after(self, bdir):
        from . import log
        from .recolour import read_picture
        log.write("%s %s (backup %s)" % (TITLE, self.path, bdir))
        try:
            if not self.winfo_exists():
                return
            if not self.winfo_viewable():                  # closed: it only held the recipe
                self.destroy()
                return
        except tk.TclError:
            return
        self.mod = self.app.mod
        if self.scope == "all" and os.path.isfile(self.path):
            im = read_picture(self.path)                   # written over: the new picture is 'now'
            self.im = im.crop((self.crop[0], self.crop[1], self.crop[0] + self.crop[2],
                               self.crop[1] + self.crop[3])) if self.crop else im
        self._ak_busy = True
        self.swaps, self.cur = [], None
        self.fill()
        self.show()
        self.ak_start()
        self.status.configure(text="written (backup %s)" % bdir)

    def ak_dropped(self):
        self._ak_saw(None)
        try:
            if self.winfo_exists() and not self.winfo_viewable():
                self.destroy()
                return
        except tk.TclError:
            return
        self._ak_busy = True
        self.swaps, self.cur = [], None
        self.fill()
        self.show()
        self.ak_start()

    def close(self):
        """Closing: the changes stay waiting for Apply changes - the window only hides then (it holds the recipe)."""
        self.ak_close()
        if self._ak_key() in (self.app.session_parts() if hasattr(self.app, "session_parts") else {}):
            self.withdraw()
        else:
            self.destroy()


__all__ = ["FreeRecolourWindow", "open_free", "app_of"]
