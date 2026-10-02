"""The window that puts right by hand where the new symbol goes on a battle banner (banners.py finds the old symbol
on its own; a cloth of two colours or a symbol touching the trim can fool it): a brush marks more of the old symbol
to fill over (or less), and a box drawn on a banner is where the new symbol goes. The allies' banner takes the
same places."""

import tkinter as tk
from tkinter import ttk

from . import banners as B
from .gui_util import ShortHint

VIEW = 512


class BannerFixer(tk.Toplevel):
    def __init__(self, master, old, symbol, found, on_done, title="Battle banner"):
        super().__init__(master)
        self.title(title + " - put the symbol right")
        self.transient(master.winfo_toplevel())
        self.old = old.convert("RGBA")
        self.symbol = symbol
        self.k = VIEW / max(self.old.size)
        self.found = [[f[0].copy(), tuple(f[1])] for f in (found or [])]
        self.undo = []
        self.on_done = on_done
        self._build()
        self.redraw()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        ShortHint(frm, text=(
            "Coloured over = the old symbol, filled over with the cloth round it; the dashed box = where the new symbol goes. "
            "The brush marks more of the old symbol (or less, with 'keep'); drawing a box on a banner moves the new "
            "symbol there. The allies' banner gets the same places.")).pack(anchor="w")
        body = ttk.Frame(frm)
        body.pack(fill="both", expand=True, pady=6)
        w, h = (round(s * self.k) for s in self.old.size)
        self.cv = tk.Canvas(body, width=w, height=h, highlightthickness=1, highlightbackground="#999",
                            cursor="crosshair")
        self.cv.pack(side="left")
        side = ttk.Frame(body, padding=(10, 0))
        side.pack(side="left", fill="y")
        self.v_show = tk.StringVar(value="before")
        ttk.Label(side, text="Show").pack(anchor="w")
        for text, val in (("the old symbol marked", "before"), ("the banner after", "after")):
            ttk.Radiobutton(side, text=text, value=val, variable=self.v_show, command=self.redraw).pack(anchor="w")
        ttk.Separator(side).pack(fill="x", pady=8)
        ttk.Label(side, text="A drag on the banner").pack(anchor="w")
        self.v_tool = tk.StringVar(value="add")
        for text, val in (("brush: the old symbol (fill over)", "add"), ("brush: keep (not the symbol)", "keep"),
                          ("box: the new symbol's place", "box")):
            ttk.Radiobutton(side, text=text, value=val, variable=self.v_tool).pack(anchor="w")
        row = ttk.Frame(side)
        row.pack(anchor="w", pady=(4, 0))
        ttk.Label(row, text="brush size").pack(side="left")
        self.v_size = tk.IntVar(value=6)
        ttk.Spinbox(row, from_=1, to=40, textvariable=self.v_size, width=4).pack(side="left", padx=4)
        ttk.Separator(side).pack(fill="x", pady=8)
        bb = ttk.Frame(side)
        bb.pack(anchor="w")
        ttk.Button(bb, text="Undo", command=self._undo).pack(side="left")
        ttk.Button(bb, text="Find it again", command=self._auto).pack(side="left", padx=4)
        bar = ttk.Frame(frm)
        bar.pack(fill="x")
        ttk.Button(bar, text="Done", command=self._done).pack(side="left")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)

    # ---- state ----
    def _remember(self):
        self.undo.append([[m.copy(), b] for m, b in self.found])
        del self.undo[:-20]

    def _undo(self):
        if self.undo:
            self.found = self.undo.pop()
            self.redraw()

    def _auto(self):
        self._remember()
        self.found = [[f[0], f[1]] for f in B.find_symbols(self.old)]
        self.redraw()

    def _xy(self, e):
        return int(e.x / self.k), int(e.y / self.k)

    def _banner_at(self, xy):
        """The index into found of the banner holding xy, a new entry made when the banner has none."""
        for x0, y0, x1, y1 in B._banners(self.old.split()[3], int(self.old.size[1] * 0.72)):
            if x0 <= xy[0] < x1 and y0 <= xy[1] < y1:
                for i, (m, b) in enumerate(self.found):
                    if b and x0 <= (b[0] + b[2]) / 2 < x1:
                        return i
                from PIL import Image
                self.found.append([Image.new("L", self.old.size, 0), (x0 + 10, y0 + 10, x1 - 10, y1 - 30)])
                return len(self.found) - 1
        return None

    # ---- the mouse ----
    def _press(self, e):
        xy = self._xy(e)
        i = self._banner_at(xy)
        if i is None:
            self._at = None
            return
        self._remember()
        self._at = (i, xy)
        if self.v_tool.get() != "box":
            self._paint(i, xy)

    def _paint(self, i, xy):
        from PIL import ImageDraw
        r = int(self.v_size.get() or 6)
        ImageDraw.Draw(self.found[i][0]).ellipse((xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r),
                                                 fill=255 if self.v_tool.get() == "add" else 0)
        k = self.k
        self.cv.create_oval((xy[0] - r) * k, (xy[1] - r) * k, (xy[0] + r) * k, (xy[1] + r) * k,
                            outline="", fill="#ff3030" if self.v_tool.get() == "add" else "#30c030",
                            stipple="gray50", tags="stroke")

    def _drag(self, e):
        if not getattr(self, "_at", None):
            return
        i, start = self._at
        xy = self._xy(e)
        if self.v_tool.get() == "box":
            k = self.k
            self.cv.delete("newbox")
            self.cv.create_rectangle(start[0] * k, start[1] * k, xy[0] * k, xy[1] * k, outline="#ffd400",
                                     width=2, tags="newbox")
        else:
            self._paint(i, xy)

    def _release(self, e):
        if not getattr(self, "_at", None):
            return
        i, start = self._at
        self._at = None
        if self.v_tool.get() == "box":
            xy = self._xy(e)
            box = (min(start[0], xy[0]), min(start[1], xy[1]), max(start[0], xy[0]), max(start[1], xy[1]))
            if box[2] - box[0] >= 4 and box[3] - box[1] >= 4:
                self.found[i][1] = box
        self.redraw()

    # ---- drawing ----
    def places(self):
        """[(mask, box)] as banners.paint_symbol takes them (banners with nothing marked and no box left out)."""
        return [(m, b) for m, b in self.found if b]

    def _mark_colour(self):
        """A colour far from the cloth's (red on a red banner would not show)."""
        from PIL import ImageStat
        r, g, b = ImageStat.Stat(self.old.convert("RGB"), self.old.split()[3]).mean[:3]
        return (0, 220, 255, 255) if r >= max(g, b) else (255, 40, 200, 255) if g >= b else (255, 140, 0, 255)

    def redraw(self):
        from PIL import Image, ImageTk
        if self.v_show.get() == "after":
            im = B.paint_symbol(self.old, self.symbol, self.places()) or self.old
        else:
            im = self.old.copy()
            red = Image.new("RGBA", im.size, self._mark_colour())
            for m, _ in self.found:
                im.paste(red, (0, 0), m.point(lambda v: v * 150 // 255))
        bg = Image.new("RGBA", im.size, (90, 90, 90, 255))
        bg.alpha_composite(im)
        view = bg.resize((round(im.size[0] * self.k), round(im.size[1] * self.k)), Image.LANCZOS)
        self._ph = ImageTk.PhotoImage(view)
        c = self.cv
        c.delete("all")
        c.create_image(0, 0, image=self._ph, anchor="nw")
        k = self.k
        for _, b in self.found:
            if b:
                c.create_rectangle(b[0] * k, b[1] * k, b[2] * k, b[3] * k, outline="#ffd400", dash=(4, 3))

    def _done(self):
        got = self.places()
        self.destroy()
        self.on_done(got)
