"""The window for the faction's battle banners, both games. Rome (banners.py): which of the game's blank white
banners (Roman, barbarian, eastern); Medieval II (banners_m2.py): the white template taken from the mod's own banner
sheets, every banner and pennant of the sheet a panel of its own. Then the cloth's pattern (plain, stripes - a
tricolour upright, across or slanting - quarters, a cross, a border...) and its colours, the symbol on or off (any
picture, its plain background cleared), and where the symbol goes - dragged with the left mouse button (snapped to
a grid of the banner if one is picked), the wheel over it makes it bigger or smaller. Or the player's own
drawing: the template saved to draw on in any program, the drawing put back in. Rome shows the allies' banner beside
it (the symbol faint), Medieval II the banner in 3D on its mesh."""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import banners as B
from .gui_util import ShortHint

VIEW = 384                     # the longer side of the big view (Rome's square banners)
VIEW_WIDE = 640                # ... for a wide sheet (Medieval II: 1024 x 512)


class BannerWindow(tk.Toplevel):
    def __init__(self, master, blanks, symbol, settings, on_done, title="Battle banners"):
        """blanks: Rome's {kind: blank banner} or a kit (banners.Kit / banners_m2.Kit); symbol: a picture or None
        (one can be loaded in the window); on_done(settings) - the settings carry 'symbol' (the picture shown)."""
        super().__init__(master)
        self.title(title)
        self.transient(master.winfo_toplevel())
        self.kit = B.Kit(blanks) if isinstance(blanks, dict) else blanks
        self.symbol, self.on_done = symbol, on_done
        self.s = dict(settings or {})
        self.s.pop("symbol", None)
        self.undo = []
        self._build()
        self.redraw()

    # ---- the window ----
    def _build(self):
        rome = self.kit.game == "Rome"
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        ShortHint(frm, text=(
            "The banners are made from the game's own blank white banner (the one a fleeing unit's banner turns "
            "into - it stays as it is): its cloth dyed in a pattern of your colours - plain, a tricolour upright, "
            "across or slanting, quarters, a cross, a border - and the symbol painted on it with the cloth's folds. "
            "Drag the symbol with the left mouse button (a click on another banner puts it there); the wheel over it "
            "makes it bigger or smaller; Snap lays a grid on each banner. Right: the allies' banner, the symbol faint like the "
            "game's own." if rome else
            "Medieval II has no white banner, so the white template is taken from the mod's own banner pictures: "
            "every faction's picture holds the same banners in the same places, so what they all share (the cloth's "
            "folds, the tooth edges, the poles) stays and each faction's heraldry goes. Its cloth is dyed in a "
            "pattern of your colours on each banner and pennant on its own, the symbol painted on with the folds. "
            "Drag the symbol with the left mouse button (a click on another banner or pennant puts it there); the wheel "
            "over it makes it bigger or smaller; Snap lays a grid on each banner. Right: the banner in 3D as the game "
            "hangs it.")).pack(
            anchor="w")
        from PIL import Image, ImageTk
        self._thumbs = []
        self.v_kind = tk.StringVar(value=self.s.get("kind") or next(iter(self.kit.shapes)))
        if rome:
            # the three blank banners side by side - any of them for any faction, whatever its culture
            shapes = ttk.Frame(frm)
            shapes.pack(anchor="w", pady=(6, 0))
            ttk.Label(shapes, text="Banner shape\n(any, for any faction)").pack(side="left", padx=(0, 8))
            for kind, im in self.kit.shapes.items():
                bg = Image.new("RGBA", im.size, (90, 90, 90, 255))
                bg.alpha_composite(im.convert("RGBA"))
                ph = ImageTk.PhotoImage(bg.resize((72, 72), Image.LANCZOS))
                self._thumbs.append(ph)
                ttk.Radiobutton(shapes, text=kind, image=ph, compound="top", value=kind, variable=self.v_kind,
                                command=self._kind).pack(side="left", padx=4)
        top = ttk.Frame(frm)
        top.pack(anchor="w", pady=6)
        ttk.Label(top, text="Pattern").pack(side="left")
        self.v_pat = tk.StringVar(value=self.s.get("pattern") or "plain")
        cp = ttk.Combobox(top, textvariable=self.v_pat, values=list(B.PATTERNS), state="readonly", width=32)
        cp.pack(side="left", padx=6)
        cp.bind("<<ComboboxSelected>>", lambda e: self._set("pattern", self.v_pat.get()))
        row2 = ttk.Frame(frm)
        row2.pack(anchor="w")
        ttk.Label(row2, text="Colours").pack(side="left")
        if not self.s.get("colours"):
            self.s["colours"] = [tuple(self.s.get("colour") or (200, 200, 200))[:3], (240, 240, 240), (30, 30, 30)]
        self.b_cols = []
        for i in range(3):
            b = tk.Button(row2, width=4, command=lambda i=i: self._colour(i))
            b.pack(side="left", padx=3)
            self.b_cols.append(b)
        self.v_sym = tk.BooleanVar(value=not self.s.get("no_symbol"))
        self.c_sym = ttk.Checkbutton(row2, text="the symbol on it", variable=self.v_sym,
                                     command=lambda: self._set("no_symbol", not self.v_sym.get()))
        self.c_sym.pack(side="left", padx=(12, 0))
        ttk.Button(row2, text="Symbol picture...", command=self._pick_symbol).pack(side="left", padx=4)
        ttk.Button(row2, text="Undo", command=self._undo).pack(side="left", padx=(12, 0))
        ttk.Button(row2, text="Symbol back in the middle", command=self._reset).pack(side="left", padx=4)
        from . import settings as _settings
        ttk.Label(row2, text="Snap").pack(side="left", padx=(12, 0))
        grids = list(B.GRIDS)
        self.v_grid = tk.StringVar(value=_settings.get("banner_grid") if _settings.get("banner_grid") in B.GRIDS
                                   else grids[0])
        cg = ttk.Combobox(row2, textvariable=self.v_grid, values=grids, state="readonly", width=28)
        cg.pack(side="left", padx=4)
        cg.bind("<<ComboboxSelected>>", lambda e: (_settings.put("banner_grid", self.v_grid.get()), self.redraw()))
        row3 = ttk.Frame(frm)
        row3.pack(anchor="w", pady=(6, 0))
        from .gui_util import tip
        tip(ttk.Button(row3, text="Save the template...", command=self._save_template),
            "The white banner as a PNG of the game's size, each banner outlined in red: paint it in any program "
            "(keep the banners where they are), then 'Put in my own drawing'.").pack(side="left")
        tip(ttk.Button(row3, text="Put in my own drawing...", command=self._drawing),
            "A banner picture you painted (best on the saved template, the same size): it takes the place of the "
            "dyed cloth; the symbol can still go on it.").pack(side="left", padx=4)
        self.b_dye = ttk.Button(row3, text="Back to the dyed cloth", command=lambda: self._set("drawing", None))
        self.b_dye.pack(side="left", padx=4)
        self.lbl_draw = ttk.Label(row3, text="", foreground="#555")
        self.lbl_draw.pack(side="left", padx=6)
        body = ttk.Frame(frm)
        body.pack()
        w, h = self.kit.blank(self.s).size
        k = self._k()
        self.cv = tk.Canvas(body, width=round(w * k), height=round(h * k), highlightthickness=1,
                            highlightbackground="#999", cursor="fleur")
        self.cv.pack(side="left")
        side = ttk.Frame(body)
        side.pack(side="left", anchor="n", padx=8)
        ttk.Label(side, text=self.kit.side_label, foreground="#555").pack(anchor="w")
        if rome:
            self.side_size = (VIEW // 2, VIEW // 2)
        else:
            self.side_size = (220, 300)
            meshes = list(getattr(self.kit, "meshes", {}))
            if meshes:
                self.v_mesh = tk.StringVar(value=self.kit.mesh)
                cm = ttk.Combobox(side, textvariable=self.v_mesh, values=meshes, state="readonly", width=18)
                cm.pack(anchor="w", pady=(0, 4))
                cm.bind("<<ComboboxSelected>>", lambda e: self._mesh())
        self.cv2 = tk.Canvas(side, width=self.side_size[0], height=self.side_size[1], highlightthickness=1,
                             highlightbackground="#999")
        self.cv2.pack(anchor="w")
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Done", command=self._done).pack(side="left")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<MouseWheel>", lambda e: self._wheel(e, 1 if e.delta > 0 else -1))
        self.cv.bind("<Button-4>", lambda e: self._wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self._wheel(e, -1))

    def blank(self):
        return self.kit.blank(self.s)

    def boxes(self):
        return self.kit.symbol_boxes(self.s)

    def _k(self):
        """Canvas pixels per picture pixel."""
        w, h = self.blank().size
        return (VIEW_WIDE if w >= 1.5 * h else VIEW) / max(w, h)

    # ---- changes ----
    def _remember(self):
        self.undo.append((dict(self.s), self.symbol))
        del self.undo[:-20]

    def _set(self, key, value):
        self._remember()
        self.s[key] = value
        self.redraw()

    def _undo(self):
        if self.undo:
            self.s, self.symbol = self.undo.pop()
            self.v_kind.set(self.s.get("kind") or next(iter(self.kit.shapes)))
            self.v_pat.set(self.s.get("pattern") or "plain")
            self.v_sym.set(not self.s.get("no_symbol"))
            self.redraw()

    def _kind(self):
        self._remember()
        self.s.update(kind=self.v_kind.get(), boxes=None)       # another shape: the symbol back in its middle
        self.redraw()

    def _mesh(self):
        self.kit.mesh = self.v_mesh.get()
        self.redraw()

    def _reset(self):
        self._remember()
        self.s["boxes"] = None
        self.redraw()

    def _colour(self, i):
        cols = list(self.s["colours"])
        got = colorchooser.askcolor(color="#%02x%02x%02x" % tuple(cols[i][:3]), parent=self,
                                    title="Colour %d of the cloth" % (i + 1))
        if got and got[0]:
            self._remember()
            cols[i] = tuple(int(v) for v in got[0])
            self.s["colours"] = cols
            self.redraw()

    def _pick_symbol(self):
        src = filedialog.askopenfilename(parent=self, title="The symbol (best: a PNG with a clear background)",
                                         filetypes=[("Pictures", "*.png *.tga *.dds *.jpg *.jpeg *.bmp"),
                                                    ("All files", "*.*")])
        if not src:
            return
        try:
            from .emblem_edit import clear_background
            from .recolour import read_picture
            im = read_picture(src).convert("RGBA")
            clear_background(im)                             # a white or plain square round it made clear
        except Exception as e:
            messagebox.showerror("Symbol", "Cannot read %s: %s" % (src, e), parent=self)
            return
        self._remember()
        self.symbol = im
        self.s["no_symbol"] = False
        self.v_sym.set(True)
        self.redraw()

    def _save_template(self):
        name = "banner_template_%s.png" % ("medieval2" if self.kit.game != "Rome" else
                                           (self.s.get("kind") or "rome").lower())
        dst = filedialog.asksaveasfilename(parent=self, title="Save the white banner to draw on",
                                           defaultextension=".png", initialfile=name,
                                           filetypes=[("PNG picture", "*.png")])
        if not dst:
            return
        try:
            self.kit.template(self.s).save(dst)
        except OSError as e:
            messagebox.showerror("Save the template", str(e), parent=self)
            return
        w, h = self.blank().size
        looks = getattr(getattr(self.kit, "sheet", None), "copies", None)
        messagebox.showinfo("Save the template", "Saved %s (%d x %d).\n\nPaint the banners inside the red lines "
                            "in any program, keep the size, then 'Put in my own drawing'.%s" % (
                                os.path.basename(dst), w, h, "\n\nThe grey lines are the small pennants' other "
                                "looks: the editor copies each first pennant there." if looks else ""), parent=self)

    def _drawing(self):
        src = filedialog.askopenfilename(parent=self, title="Your banner picture",
                                         filetypes=[("Pictures", "*.png *.tga *.dds *.jpg *.jpeg *.bmp"),
                                                    ("All files", "*.*")])
        if not src:
            return
        try:
            from .recolour import read_picture
            got = read_picture(src).size
        except Exception as e:
            messagebox.showerror("Your drawing", "Cannot read %s: %s" % (src, e), parent=self)
            return
        want = self.blank().size
        if tuple(got) != tuple(want) and not messagebox.askyesno(
                "Your drawing", "%s is %d x %d; the banner picture is %d x %d.\n\nStretch it to %d x %d?" % (
                    (os.path.basename(src),) + tuple(got) + tuple(want) + tuple(want)), parent=self):
            return
        self._set("drawing", src)

    # ---- the mouse: the symbol dragged, the wheel sizes it, a grid to snap to ----
    def _xy(self, e):
        k = self._k()
        return e.x / k, e.y / k

    def _cells(self):
        return B.GRIDS.get(self.v_grid.get(), 0)

    def _movable(self):
        return self.symbol is not None and not self.s.get("no_symbol")

    def _box_at(self, x, y):
        """The number of the symbol under the point, else of the banner under it, or None."""
        boxes = self.boxes()
        on = [i for i, b in enumerate(boxes) if b[0] <= x < b[2] and b[1] <= y < b[3]]
        if on:
            return min(on, key=lambda i: (boxes[i][2] - boxes[i][0]) * (boxes[i][3] - boxes[i][1]))
        return B.banner_at(self.kit.banners(self.s), x, y)

    def _press(self, e):
        self._grab = None
        if not self._movable():
            return
        x, y = self._xy(e)
        i = self._box_at(x, y)
        boxes, banners = list(self.boxes()), self.kit.banners(self.s)
        if i is None or i >= len(boxes) or i >= len(banners):
            return
        b = boxes[i]
        inside = b[0] <= x < b[2] and b[1] <= y < b[3]
        # grabbed where it was held; a click on the banner beside it brings its middle to the click
        off = ((b[0] + b[2]) / 2 - x, (b[1] + b[3]) / 2 - y) if inside else (0, 0)
        self._grab = {"i": i, "off": off, "box": b, "start": b}
        from PIL import Image, ImageTk
        k = self._k()
        size = (max(1, round((b[2] - b[0]) * k)), max(1, round((b[3] - b[1]) * k)))
        self._ghost = ImageTk.PhotoImage(self.symbol.convert("RGBA").resize(size, Image.LANCZOS))
        self._drag(e)

    def _drag(self, e):
        g = getattr(self, "_grab", None)
        if not g:
            return
        x, y = self._xy(e)
        banner = self.kit.banners(self.s)[g["i"]]
        g["box"] = B.place_box(g["start"], x + g["off"][0], y + g["off"][1], banner, self._cells())
        k, b = self._k(), g["box"]
        self.cv.delete("ghost")
        self.cv.create_image(b[0] * k, b[1] * k, image=self._ghost, anchor="nw", tags="ghost")
        self.cv.create_rectangle(b[0] * k, b[1] * k, b[2] * k, b[3] * k, outline="#ffd400", width=2, tags="ghost")

    def _release(self, e):
        g, self._grab = getattr(self, "_grab", None), None
        if not g or g["box"] == g["start"]:
            self.cv.delete("ghost")
            return
        self._remember()
        boxes = list(self.boxes())
        boxes[g["i"]] = g["box"]
        self.s["boxes"] = boxes
        self.redraw()

    def _wheel(self, e, step):
        if not self._movable():
            return
        x, y = self._xy(e)
        i = self._box_at(x, y)
        boxes, banners = list(self.boxes()), self.kit.banners(self.s)
        if i is None or i >= len(boxes) or i >= len(banners):
            return
        import time
        if time.time() - getattr(self, "_wheel_at", 0) > 0.8:      # one Undo step for a turn of the wheel
            self._remember()
        self._wheel_at = time.time()
        boxes[i] = B.scale_box(boxes[i], 1.1 if step > 0 else 1 / 1.1, banners[i])
        self.s["boxes"] = boxes
        self.redraw()

    # ---- drawing ----
    def redraw(self):
        from PIL import Image, ImageTk
        cols = self.s["colours"]
        drawing = self.s.get("drawing")
        used = 0 if drawing else B.PATTERNS.get(self.s.get("pattern") or "plain", B.PATTERNS["plain"])[0]
        for i, b in enumerate(self.b_cols):              # only as many colours as the pattern takes
            b.configure(bg="#%02x%02x%02x" % tuple(cols[i][:3]), state="normal" if i < used else "disabled",
                        relief="raised" if i < used else "flat")
        self.c_sym.configure(state="normal" if self.symbol is not None else "disabled")
        self.b_dye.configure(state="normal" if drawing else "disabled")
        self.lbl_draw.configure(text="your drawing: %s" % os.path.basename(drawing) if drawing else "")
        im = self.kit.make(self.s, self.symbol)
        bg = Image.new("RGBA", im.size, (90, 90, 90, 255))
        bg.alpha_composite(im)
        k = self._k()
        main = ImageTk.PhotoImage(bg.resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS))
        side = self.kit.side(self.s, self.symbol, self.side_size)
        views = [main]
        self.cv.delete("all")
        self.cv.create_image(0, 0, image=main, anchor="nw")
        self.cv2.delete("all")
        if side is not None:
            sb = Image.new("RGBA", side.size, (90, 90, 90, 255))
            sb.alpha_composite(side.convert("RGBA"))
            ph = ImageTk.PhotoImage(sb)
            views.append(ph)
            self.cv2.create_image(0, 0, image=ph, anchor="nw")
        self._ph = views
        cells = self._cells()
        if cells and self._movable():
            for ban in self.kit.banners(self.s):              # the grid of each banner, faint
                xs, ys = B.grid_lines(ban, cells)
                for gx in xs:
                    self.cv.create_line(gx * k, ban[1] * k, gx * k, ban[3] * k, fill="#7fd0ff", dash=(2, 4))
                for gy in ys:
                    self.cv.create_line(ban[0] * k, gy * k, ban[2] * k, gy * k, fill="#7fd0ff", dash=(2, 4))
        for b in (self.boxes() if self._movable() else []):
            self.cv.create_rectangle(b[0] * k, b[1] * k, b[2] * k, b[3] * k, outline="#ffd400", dash=(4, 3))

    def _done(self):
        self.s["kind"] = self.v_kind.get()
        got = dict(self.s, symbol=self.symbol)
        self.destroy()
        self.on_done(got)

