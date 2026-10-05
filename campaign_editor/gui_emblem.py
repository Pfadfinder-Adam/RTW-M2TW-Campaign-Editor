"""The window that fits a picture into the faction's emblem (emblem_edit.py): drag to move, the wheel to make it
bigger or smaller, a turn, the shape it is cut to, the ground inside, the magic wand and the paint bucket. Its
master picture goes on to the window that shows every emblem picture made from it, with the bare symbol (no
shape, no ground) for the flags and banners."""

import tkinter as tk
from tkinter import colorchooser, ttk

from . import emblem_edit as EE, theme
from .gui_util import ShortHint, hint

VIEW = 320
SHAPES = (("like the old emblem", "old"), ("circle", "circle"), ("square", "square"), ("not cut", "none"))


class EmblemFitter(tk.Toplevel):
    def __init__(self, master, src, frame, colours, on_done, title="Faction emblem"):
        super().__init__(master)
        self.title(title + " - fit the picture")
        self.transient(master.winfo_toplevel())
        self.src0 = src.convert("RGBA")
        self.src = self.src0.copy()
        # a plain background (a white square) goes at once - else it shows on the flags and banners as a square
        self.cleared = EE.clear_background(self.src)
        self.frame, self.colours, self.on_done = frame, colours, on_done
        k, dx, dy = EE.auto_place(self.src)
        self.state = {"scale": k, "dx": dx, "dy": dy, "angle": 0.0, "shape": "old" if frame is not None else "circle",
                      "frame": frame, "ground": None}
        self.undo = []
        self._build()
        if self.cleared:
            self.lbl.configure(text="Its plain background was cleared (%d pixels) - Start over brings it back." %
                                    self.cleared)
        self.redraw()

    def _build(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        ShortHint(frm, text=(
            "Fit the picture into the emblem: drag it to move, the mouse wheel makes it bigger or smaller. The "
            "shape cuts it like the old emblem (most are a disc) or as you pick; the ground fills the shape behind "
            "it. The magic wand clears an area of like colour where you click (a white background), the paint "
            "bucket fills one with the colour picked. Next shows every place the game shows the emblem.")).pack(
            anchor="w")
        body = ttk.Frame(frm)
        body.pack(fill="both", expand=True, pady=6)
        self.cv = tk.Canvas(body, width=VIEW, height=VIEW, highlightthickness=1, highlightbackground="#999",
                            cursor="fleur")
        self.cv.pack(side="left")
        side = ttk.Frame(body, padding=(10, 0))
        side.pack(side="left", fill="y")
        ttk.Label(side, text="Shape").grid(row=0, column=0, sticky="w")
        self.v_shape = tk.StringVar(value=dict((v, k) for k, v in SHAPES)[self.state["shape"]])
        cb = ttk.Combobox(side, textvariable=self.v_shape, values=[k for k, _ in SHAPES], state="readonly", width=20)
        cb.grid(row=0, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self._set("shape", dict(SHAPES)[self.v_shape.get()]))
        ttk.Label(side, text="Ground").grid(row=1, column=0, sticky="w", pady=(6, 0))
        grounds = ["clear"] + [n for n, c in (("faction's primary colour", self.colours[0]),
                                             ("faction's secondary colour", self.colours[1])) if c] + ["a colour..."]
        self.v_ground = tk.StringVar(value="clear")
        cg = ttk.Combobox(side, textvariable=self.v_ground, values=grounds, state="readonly", width=20)
        cg.grid(row=1, column=1, sticky="w", pady=(6, 0))
        cg.bind("<<ComboboxSelected>>", lambda e: self._ground())
        ttk.Label(side, text="Turn").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.v_angle = tk.DoubleVar(value=0)
        ttk.Scale(side, from_=-180, to=180, variable=self.v_angle, orient="horizontal", length=170,
                  command=lambda v: self._set("angle", -float(v), remember=False)).grid(
            row=2, column=1, sticky="w", pady=(6, 0))
        ttk.Label(side, text="Size").grid(row=3, column=0, sticky="w", pady=(6, 0))
        sz = ttk.Frame(side)
        sz.grid(row=3, column=1, sticky="w", pady=(6, 0))
        ttk.Button(sz, text="-", command=lambda: self._zoom(1 / 1.08)).pack(side="left")
        ttk.Button(sz, text="+", command=lambda: self._zoom(1.08)).pack(side="left", padx=4)
        ttk.Separator(side).grid(row=4, column=0, columnspan=2, sticky="we", pady=8)
        ttk.Label(side, text="A click on the picture").grid(row=5, column=0, columnspan=2, sticky="w")
        self.v_tool = tk.StringVar(value="move")
        for r, (text, val) in enumerate((("moves it (drag)", "move"), ("magic wand: clears the area", "wand"),
                                         ("paint bucket: fills the area", "bucket")), start=6):
            ttk.Radiobutton(side, text=text, value=val, variable=self.v_tool,
                            command=self._cursor).grid(row=r, column=0, columnspan=2, sticky="w")
        tol = ttk.Frame(side)
        tol.grid(row=9, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(tol, text="like colour within").pack(side="left")
        self.v_tol = tk.IntVar(value=32)
        ttk.Spinbox(tol, from_=0, to=255, textvariable=self.v_tol, width=4).pack(side="left", padx=4)
        hint(tol, "How far a colour may be from the clicked one to count as the same area (0 = only that exact "
                  "colour; 30-40 takes a background with soft shading).").pack(side="left")
        self.fill = (255, 255, 255)
        fb = ttk.Frame(side)
        fb.grid(row=10, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(fb, text="bucket colour").pack(side="left")
        self.b_fill = ttk.Button(fb, width=3, command=self._pick_fill)
        theme.paint(self.b_fill, "#ffffff")
        self.b_fill.pack(side="left", padx=4)
        ttk.Separator(side).grid(row=11, column=0, columnspan=2, sticky="we", pady=8)
        bb = ttk.Frame(side)
        bb.grid(row=12, column=0, columnspan=2, sticky="w")
        ttk.Button(bb, text="Undo", command=self._undo).pack(side="left")
        ttk.Button(bb, text="Fit again", command=self._refit).pack(side="left", padx=4)
        ttk.Button(bb, text="Start over", command=self._reset).pack(side="left")
        self.lbl = ttk.Label(side, foreground="#666", wraplength=230, justify="left")
        self.lbl.grid(row=13, column=0, columnspan=2, sticky="w", pady=(8, 0))
        bar = ttk.Frame(frm)
        bar.pack(fill="x")
        ttk.Button(bar, text="Next: every picture >", command=self._next).pack(side="left")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        c = self.cv
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._drag)
        for seq, step in (("<MouseWheel>", None), ("<Button-4>", 1), ("<Button-5>", -1)):
            c.bind(seq, lambda e, st=step: self._zoom(1.08 if (st or (1 if e.delta > 0 else -1)) > 0 else 1 / 1.08))

    # ---- state ----
    def _remember(self):
        self.undo.append((dict(self.state), self.src.copy()))
        del self.undo[:-30]

    def _set(self, key, value, remember=True):
        if remember:
            self._remember()
        self.state[key] = value
        self.redraw()

    def _ground(self):
        g = self.v_ground.get()
        if g == "clear":
            col = None
        elif g.startswith("faction's primary"):
            col = self.colours[0]
        elif g.startswith("faction's secondary"):
            col = self.colours[1]
        else:
            got = colorchooser.askcolor(parent=self, title="The ground's colour")
            if not got or not got[0]:
                return
            col = tuple(int(v) for v in got[0])
        self._set("ground", col)

    def _pick_fill(self):
        got = colorchooser.askcolor(parent=self, title="The paint bucket's colour")
        if got and got[0]:
            self.fill = tuple(int(v) for v in got[0])
            theme.paint(self.b_fill, self.fill)

    def _cursor(self):
        self.cv.configure(cursor="fleur" if self.v_tool.get() == "move" else "crosshair")

    def _zoom(self, k):
        self._remember()
        self.state["scale"] = max(0.01, self.state["scale"] * k)
        self.redraw()

    def _undo(self):
        if self.undo:
            self.state, self.src = self.undo.pop()
            self.redraw()

    def _refit(self):
        self._remember()
        k, dx, dy = EE.auto_place(self.src)
        self.state.update(scale=k, dx=dx, dy=dy, angle=0.0)
        self.v_angle.set(0)
        self.redraw()

    def _reset(self):
        self._remember()
        self.src = self.src0.copy()
        self.lbl.configure(text="")
        self._refit()

    # ---- the mouse ----
    def _master_xy(self, e):
        return e.x * EE.MASTER / VIEW, e.y * EE.MASTER / VIEW

    def _press(self, e):
        tool = self.v_tool.get()
        if tool == "move":
            self._remember()
            self._from = (e.x, e.y, self.state["dx"], self.state["dy"])
            return
        from .emblem import footprint
        self.state["_box"] = footprint(self.src) or (0, 0) + self.src.size
        p = EE.to_source(self.state, self.src.size, self._master_xy(e))
        if p is None:
            self.lbl.configure(text="That is outside the picture.")
            return
        self._remember()
        n = EE.flood(self.src, p, int(self.v_tol.get() or 0), None if tool == "wand" else self.fill)
        self.lbl.configure(text="%d pixel(s) %s." % (n, "cleared" if tool == "wand" else "filled"))
        self.redraw()

    def _drag(self, e):
        if self.v_tool.get() != "move" or not getattr(self, "_from", None):
            return
        x0, y0, dx, dy = self._from
        k = EE.MASTER / VIEW
        self.state["dx"], self.state["dy"] = dx + (e.x - x0) * k, dy + (e.y - y0) * k
        self.redraw()

    # ---- drawing ----
    def picture(self):
        st = dict(self.state)
        st.pop("_box", None)
        return EE.compose(self.src, st)

    def symbol(self):
        """The picture as placed and turned, without the shape's cut and the ground: the symbol a flag or a
        banner carries on its own cloth."""
        st = dict(self.state)
        st.pop("_box", None)
        st.update(shape=None, ground=None)
        return EE.compose(self.src, st)

    def redraw(self):
        from PIL import Image, ImageDraw, ImageTk
        m = self.picture()
        bg = Image.new("RGBA", m.size, (200, 200, 200, 255))
        d = ImageDraw.Draw(bg)
        for y in range(0, m.size[1], 16):                        # a checkerboard: what is clear shows
            for x in range(0, m.size[0], 16):
                if (x // 16 + y // 16) % 2:
                    d.rectangle((x, y, x + 15, y + 15), fill=(160, 160, 160, 255))
        bg.alpha_composite(m)
        view = bg.resize((VIEW, VIEW), Image.LANCZOS)
        self._ph = ImageTk.PhotoImage(view)
        c = self.cv
        c.delete("all")
        c.create_image(0, 0, image=self._ph, anchor="nw")
        if self.frame is not None:                               # the old emblem's outline, as a guide
            edge = self.frame.resize((VIEW, VIEW)).point(lambda v: 255 if v > 127 else 0)
            from PIL import ImageFilter
            ring = edge.filter(ImageFilter.FIND_EDGES)
            box = ring.getbbox()
            if box:
                c.create_oval(box[0], box[1], box[2], box[3], outline="#ffd400", dash=(4, 3))

    def _next(self):
        m, sym = self.picture(), self.symbol()
        self.destroy()
        self.on_done(m, sym)
