"""The window for the faction's battle banners (banners.py): which of the game's blank white banners (Roman,
barbarian, eastern), the cloth's colour, and where the symbol goes - a box drawn on a banner. The own banner and the
allies' (the symbol faint) are shown side by side."""

import tkinter as tk
from tkinter import colorchooser, ttk

from . import banners as B
from .gui_util import ShortHint

VIEW = 384


class BannerWindow(tk.Toplevel):
    def __init__(self, master, blanks, symbol, settings, on_done, title="Battle banners"):
        super().__init__(master)
        self.title(title)
        self.transient(master.winfo_toplevel())
        self.blanks, self.symbol, self.on_done = blanks, symbol, on_done
        self.s = dict(settings)
        self.undo = []
        self._build()
        self.redraw()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        ShortHint(frm, text=(
            "The banners are made from the game's own blank white banner: its cloth dyed in the colour picked, the "
            "symbol painted on it with the cloth's folds. Draw a box on a banner to put the symbol there. Right: "
            "the allies' banner, the symbol faint like the game's own.")).pack(anchor="w")
        top = ttk.Frame(frm)
        top.pack(anchor="w", pady=6)
        ttk.Label(top, text="Blank banner").pack(side="left")
        self.v_kind = tk.StringVar(value=self.s.get("kind") or next(iter(self.blanks)))
        cb = ttk.Combobox(top, textvariable=self.v_kind, values=list(self.blanks), state="readonly", width=12)
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._kind())
        ttk.Label(top, text="Cloth colour").pack(side="left", padx=(12, 0))
        self.b_col = tk.Button(top, width=4, command=self._colour)
        self.b_col.pack(side="left", padx=6)
        ttk.Button(top, text="Undo", command=self._undo).pack(side="left", padx=(12, 0))
        ttk.Button(top, text="Symbol back in the middle", command=self._reset).pack(side="left", padx=4)
        body = ttk.Frame(frm)
        body.pack()
        self.cv = tk.Canvas(body, width=VIEW, height=VIEW, highlightthickness=1, highlightbackground="#999",
                            cursor="crosshair")
        self.cv.pack(side="left")
        self.cv2 = tk.Canvas(body, width=VIEW // 2, height=VIEW // 2, highlightthickness=1,
                             highlightbackground="#999")
        self.cv2.pack(side="left", anchor="n", padx=8)
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Done", command=self._done).pack(side="left")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)

    def blank(self):
        return self.blanks[self.v_kind.get()]

    def boxes(self):
        return self.s.get("boxes") or B.symbol_boxes(self.blank())

    # ---- changes ----
    def _remember(self):
        self.undo.append(dict(self.s))
        del self.undo[:-20]

    def _undo(self):
        if self.undo:
            self.s = self.undo.pop()
            self.v_kind.set(self.s.get("kind"))
            self.redraw()

    def _kind(self):
        self._remember()
        self.s.update(kind=self.v_kind.get(), boxes=None)       # another shape: the symbol back in its middle
        self.redraw()

    def _reset(self):
        self._remember()
        self.s["boxes"] = None
        self.redraw()

    def _colour(self):
        got = colorchooser.askcolor(color="#%02x%02x%02x" % tuple(self.s["colour"][:3]), parent=self,
                                    title="The banner's cloth")
        if got and got[0]:
            self._remember()
            self.s["colour"] = tuple(int(v) for v in got[0])
            self.redraw()

    # ---- the mouse: a box on a banner ----
    def _xy(self, e):
        k = self.blank().size[0] / VIEW
        return int(e.x * k), int(e.y * k)

    def _press(self, e):
        self._from = self._xy(e)

    def _drag(self, e):
        if not getattr(self, "_from", None):
            return
        k = VIEW / self.blank().size[0]
        x, y = self._xy(e)
        self.cv.delete("newbox")
        self.cv.create_rectangle(self._from[0] * k, self._from[1] * k, x * k, y * k, outline="#ffd400", width=2,
                                 tags="newbox")

    def _release(self, e):
        start, self._from = getattr(self, "_from", None), None
        if not start:
            return
        x, y = self._xy(e)
        box = (min(start[0], x), min(start[1], y), max(start[0], x), max(start[1], y))
        if box[2] - box[0] < 4 or box[3] - box[1] < 4:
            return
        banners = B.banner_boxes(self.blank())
        cx = (box[0] + box[2]) / 2
        which = next((i for i, b in enumerate(banners) if b[0] <= cx < b[2]), None)
        if which is None:
            self.redraw()
            return
        self._remember()
        boxes = list(self.boxes())
        boxes[which] = box
        self.s["boxes"] = boxes
        self.redraw()

    # ---- drawing ----
    def redraw(self):
        from PIL import Image, ImageTk
        col = tuple(self.s["colour"][:3])
        self.b_col.configure(bg="#%02x%02x%02x" % col)
        views = []
        for cv, size, strength in ((self.cv, VIEW, 1.0), (self.cv2, VIEW // 2, B.ALLY_STRENGTH)):
            im = B.paint(self.blank(), col, self.symbol, self.boxes(), strength)
            bg = Image.new("RGBA", im.size, (90, 90, 90, 255))
            bg.alpha_composite(im)
            ph = ImageTk.PhotoImage(bg.resize((size, size), Image.LANCZOS))
            views.append(ph)
            cv.delete("all")
            cv.create_image(0, 0, image=ph, anchor="nw")
        self._ph = views
        k = VIEW / self.blank().size[0]
        for b in self.boxes():
            self.cv.create_rectangle(b[0] * k, b[1] * k, b[2] * k, b[3] * k, outline="#ffd400", dash=(4, 3))

    def _done(self):
        self.s["kind"] = self.v_kind.get()
        got = dict(self.s)
        self.destroy()
        self.on_done(got)
