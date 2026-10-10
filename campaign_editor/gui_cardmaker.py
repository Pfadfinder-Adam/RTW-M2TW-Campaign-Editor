"""Make a card... / Make a picture... of View in 3D (a unit's battle model): the view as it stands - turned, zoomed, in
the animation's frame picked - framed as the game's own (cardmaker.py), on the ground picked (see-through as the
game's cards, a colour, or a picture of one's own - kept for next time), seen at its size and bigger, then given to
the unit: it waits for Preview / Apply in the Units editor like an imported picture (a backup first)."""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import cardmaker as CM
from . import settings

GROUNDS = (("clear", "see-through (as the game's own)"), ("colour", "a colour"), ("picture", "a picture of mine"))


class CardMaker(tk.Toplevel):
    def __init__(self, viewer, info):
        super().__init__(viewer)
        self.viewer, self.info = viewer, info
        what = "description picture" if info else "card"
        self.what = what
        make = viewer.make
        self.title("Make a %s - %s" % (what, make.get("unit", viewer.info.name)))
        self.transient(viewer)
        from .models import game_kind
        self.size = CM.picture_size(game_kind(viewer.mod), (make.get("need") or {}).get(info), info)
        self.figure, self.box = None, None
        self.area = None                # my own frame (x, y, w, h on the figure), dragged on the man; None: the preset
        self._fit, self._grab = None, None
        self._photos = []
        self.v_part = tk.StringVar(value=CM.PICTURE_PART if info else CM.CARD_PART)
        self.v_scale = tk.DoubleVar(value=100.0)
        self.v_up = tk.DoubleVar(value=0.0)
        self.v_side = tk.DoubleVar(value=0.0)
        self.v_ground = tk.StringVar(value=settings.get("card_ground", "clear"))
        self.colour = tuple(settings.get("card_colour", [58, 64, 52]))[:3]
        self.ground_pic = None

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        from .gui_util import ShortHint
        ShortHint(frm, text=(
            "The man as the 3D view shows him now. Turn him, zoom, pick an animation and stop it on the frame you like "
            "in the 3D view, then 'Take the 3D view again'. The frame on the man (left) is what becomes the picture: "
            "pick how much of him, or drag the frame anywhere on him, its corner to size it (the wheel too). The game's own cards are the man alone on a see-through "
            "ground (the game draws the card's frame and ground behind him) - from his head to his thighs, a "
            "horseman with the front of his horse; the description pictures show the whole man. Use it gives it to "
            "the unit: Preview, then Apply writes it into every faction folder the unit's card goes to (a backup "
            "first).")).pack(anchor="w")
        body = ttk.Frame(frm)
        body.pack(fill="both", expand=True, pady=(6, 0))
        self.canvas = tk.Canvas(body, highlightthickness=0, background="#2e3036")
        self.canvas.pack(side="left", fill="both", expand=True)
        side = ttk.Frame(body, padding=(10, 0))
        side.pack(side="left", fill="y")
        ttk.Label(side, text="%s, %d x %d" % (what.capitalize(), self.size[0], self.size[1]),
                  font=("", 10, "bold")).pack(anchor="w")
        ttk.Button(side, text="Take the 3D view again", command=self.take).pack(anchor="w", pady=(6, 0))
        ttk.Label(side, text="How much of him").pack(anchor="w", pady=(8, 0))
        for key, words, _ in CM.PARTS + (("own", "my own frame (drag it on the man)", None),):
            ttk.Radiobutton(side, text=words, value=key, variable=self.v_part, command=self._part_picked).pack(
                anchor="w")
        for label, var, lo, hi in (("Nearer / farther", self.v_scale, 50, 200), ("Up / down", self.v_up, -50, 50),
                                   ("Right / left", self.v_side, -50, 50)):
            ttk.Label(side, text=label).pack(anchor="w", pady=(6, 0))
            ttk.Scale(side, from_=lo, to=hi, variable=var, orient="horizontal", length=200,
                      command=lambda v: self._slid()).pack(anchor="w")
        ttk.Button(side, text="Back to the start", command=self.reset).pack(anchor="w", pady=(4, 0))
        ttk.Label(side, text="Ground").pack(anchor="w", pady=(8, 0))
        for key, words in GROUNDS:
            row = ttk.Frame(side)
            row.pack(anchor="w", fill="x")
            ttk.Radiobutton(row, text=words, value=key, variable=self.v_ground, command=self.show).pack(side="left")
            if key == "colour":
                ttk.Button(row, text="Colour...", command=self.pick_colour).pack(side="left", padx=4)
            elif key == "picture":
                ttk.Button(row, text="Pick...", command=self.pick_ground).pack(side="left", padx=4)
        self.lbl_ground = ttk.Label(side, foreground="#555")
        self.lbl_ground.pack(anchor="w")
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Use it for %s" % make.get("unit", "the unit"), command=self.use).pack(side="left")
        ttk.Button(bar, text="Save a copy...", command=self.save_copy).pack(side="left", padx=4)
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        self.canvas.bind("<Configure>", lambda e: self.show())
        # the frame on the man (left): drag inside it to move it, its corner to size it, the wheel too - any part of
        # him (the user, 2026-10-10: 'let us choose which part becomes the card ourselves - that freedom')
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "_grab", None))
        self.canvas.bind("<MouseWheel>", lambda e: self._wheel(1 if e.delta > 0 else -1))
        self.canvas.bind("<Button-4>", lambda e: self._wheel(1))
        self.canvas.bind("<Button-5>", lambda e: self._wheel(-1))
        self.geometry("900x620")
        self._load_ground()
        self.take()

    # ---- the figure, the ground ----
    def take(self):
        """The 3D view as it stands, drawn big and cut out."""
        try:
            self.config(cursor="watch")
            self.update_idletasks()
            self.figure, self.box = self.viewer.snapshot()
        except Exception as e:
            messagebox.showerror("Make a %s" % self.what, "The 3D view could not be drawn: %s" % e, parent=self)
            self.figure, self.box = None, None
        finally:
            self.config(cursor="")
        self.show()

    def reset(self):
        self.v_scale.set(100.0)
        self.v_up.set(0.0)
        self.v_side.set(0.0)
        self.area = None
        if self.v_part.get() == "own":
            self.v_part.set(CM.PICTURE_PART if self.info else CM.CARD_PART)
        self.show()

    # ---- the frame: a preset with its sliders, or my own dragged on the man ----
    def current(self):
        """The frame on the figure now (x, y, w, h), or None."""
        if self.figure is None:
            return None
        if self.v_part.get() == "own" and self.area:
            return self.area
        part = self.v_part.get() if self.v_part.get() != "own" else (CM.PICTURE_PART if self.info else CM.CARD_PART)
        return CM.region(self.figure, self.size, part, self.v_scale.get() / 100.0, self.v_up.get() / 100.0,
                         self.v_side.get() / 100.0, box=self.box if part != "whole" else None)   # the whole man: his spear too

    def _part_picked(self):
        if self.v_part.get() == "own":
            if not self.area:                       # my own starts where the preset stands
                self.v_part.set(CM.PICTURE_PART if self.info else CM.CARD_PART)
                self.area = self.current()
                self.v_part.set("own")
        else:
            self.area = None
        self.show()

    def _slid(self):
        if self.v_part.get() == "own":              # the sliders work on the presets: back to the last one
            self.v_part.set(CM.PICTURE_PART if self.info else CM.CARD_PART)
            self.area = None
        self.show()

    def _own(self, area):
        self.area = area
        self.v_part.set("own")
        self.show()

    def _press(self, e):
        a, fit = self.current(), self._fit
        if not a or not fit:
            return
        k, ox, oy = fit
        x0, y0, x1, y1 = ox + a[0] * k, oy + a[1] * k, ox + (a[0] + a[2]) * k, oy + (a[1] + a[3]) * k
        if abs(e.x - x1) <= 10 and abs(e.y - y1) <= 10:
            self._grab = ("size", e.x, e.y, a)
        elif x0 <= e.x <= x1 and y0 <= e.y <= y1:
            self._grab = ("move", e.x, e.y, a)
        else:                                       # a click on the man outside it: the frame comes there
            self._grab = ("move", e.x, e.y, (a[0] + ((e.x - ox) / k - (a[0] + a[2] / 2)),
                                             a[1] + ((e.y - oy) / k - (a[1] + a[3] / 2)), a[2], a[3]))
            self._own(self._grab[3])

    def _drag(self, e):
        if not self._grab or not self._fit:
            return
        how, sx, sy, a = self._grab
        k = self._fit[0]
        dx, dy = (e.x - sx) / k, (e.y - sy) / k
        if how == "move":
            self._own((a[0] + dx, a[1] + dy, a[2], a[3]))
        else:                                       # the corner: bigger / smaller, the picture's shape kept
            aspect = self.size[0] / self.size[1]
            h = max(8.0, a[3] + max(dy, dx / aspect))
            self._own((a[0], a[1], h * aspect, h))

    def _wheel(self, step):
        a = self.current()
        if not a:
            return
        f = 1 / 1.1 if step > 0 else 1.1             # the wheel up: nearer (a smaller frame)
        w, h = a[2] * f, a[3] * f
        self._own((a[0] + (a[2] - w) / 2, a[1] + (a[3] - h) / 2, w, h))

    def _load_ground(self):
        path = settings.get("card_picture", "")
        self.ground_pic = None
        if path and os.path.isfile(path):
            try:
                from PIL import Image
                with Image.open(path) as im:
                    self.ground_pic = im.convert("RGBA")
            except Exception:
                self.ground_pic = None
        self.lbl_ground.configure(text=os.path.basename(path) if self.ground_pic is not None else "")

    def pick_colour(self):
        got = colorchooser.askcolor(color="#%02x%02x%02x" % self.colour, parent=self, title="The ground's colour")
        if got and got[0]:
            self.colour = tuple(int(c) for c in got[0])[:3]
            settings.put("card_colour", list(self.colour))
            self.v_ground.set("colour")
            self.show()

    def pick_ground(self):
        path = filedialog.askopenfilename(parent=self, title="A picture for the ground", filetypes=[
            ("Pictures", "*.png *.jpg *.jpeg *.tga *.bmp *.dds"), ("All files", "*.*")])
        if not path:
            return
        settings.put("card_picture", path)
        self._load_ground()
        if self.ground_pic is None:
            messagebox.showerror("Make a %s" % self.what, "Cannot read %s as a picture." % path, parent=self)
            return
        self.v_ground.set("picture")
        self.show()

    def picture(self):
        """The picture as it will be given (RGBA, the mod's own size), or None."""
        if self.figure is None:
            return None
        pic = CM.cut(self.figure, self.current(), self.size)
        g = self.v_ground.get()
        settings.put("card_ground", g)
        if g == "colour":
            return CM.on_ground(pic, self.colour)
        if g == "picture" and self.ground_pic is not None:
            return CM.on_ground(pic, self.ground_pic)
        return pic

    # ---- seeing it ----
    def show(self):
        from PIL import Image, ImageTk
        c = self.canvas
        c.delete("all")
        self._photos = []
        pic = self.picture()
        if pic is None:
            c.create_text(20, 20, anchor="nw", fill="#ddd", text="nothing drawn in the 3D view")
            return
        W, H = max(50, c.winfo_width()), max(50, c.winfo_height())
        # left: the whole man with the frame on him; right: the picture at its size and bigger
        fw = max(60, int(W * 0.42))
        fig = self.figure
        bb = fig.getchannel("A").getbbox() or (0, 0, fig.width, fig.height)      # the man and a little room round
        pad = 0.12 * max(bb[2] - bb[0], bb[3] - bb[1])
        vx0, vy0 = max(0, int(bb[0] - pad)), max(0, int(bb[1] - pad))
        vx1, vy1 = min(fig.width, int(bb[2] + pad)), min(fig.height, int(bb[3] + pad))
        view = fig.crop((vx0, vy0, vx1, vy1))
        k = min((fw - 20) / view.width, (H - 34) / view.height)
        shown = view.resize((max(1, int(view.width * k)), max(1, int(view.height * k))), Image.LANCZOS)
        ph = ImageTk.PhotoImage(shown)
        self._photos.append(ph)
        ox, oy = 10 - vx0 * k, 24 - vy0 * k              # a point of the figure: (ox + x * k, oy + y * k)
        self._fit = (k, ox, oy)
        c.create_image(10, 24, anchor="nw", image=ph)
        c.create_text(10, 6, anchor="nw", fill="#ddd", text="drag the frame")
        a = self.current()
        if a:
            x0, y0, x1, y1 = ox + a[0] * k, oy + a[1] * k, ox + (a[0] + a[2]) * k, oy + (a[1] + a[3]) * k
            cl = lambda v, lo, hi: max(lo, min(hi, v))           # kept on the man's side of the window
            right, low = 10 + shown.width, 24 + shown.height
            c.create_rectangle(cl(x0, 2, right), cl(y0, 2, low), cl(x1, 2, right), cl(y1, 2, low),
                               outline="#ffd24a", width=2)
            if x1 <= right + 6 and y1 <= low + 6:
                c.create_rectangle(x1 - 6, y1 - 6, x1 + 6, y1 + 6, outline="#ffd24a", fill="#ffd24a")
        left = fw + 10
        big = max(1, min((W - left - pic.width - 40) // pic.width, (H - 34) // pic.height))  # pixel by pixel, sharp
        x = left
        for k, label in [(1, "its size")] + ([(big, "x %d" % big)] if big > 1 else []):
            im = pic.resize((pic.width * k, pic.height * k), Image.NEAREST) if k > 1 else pic
            board = self._board(im.size)
            board.alpha_composite(im)
            ph = ImageTk.PhotoImage(board)
            self._photos.append(ph)
            c.create_image(x, 24, anchor="nw", image=ph)
            c.create_text(x, 6, anchor="nw", fill="#ddd", text=label)
            x += im.width + 20

    def _board(self, size):
        """A checkerboard: where the picture is see-through."""
        from PIL import Image
        board = Image.new("RGBA", size, (200, 200, 200, 255))
        dark = Image.new("RGBA", (6, 6), (150, 150, 150, 255))
        for y in range(0, size[1], 6):
            for x in range((y // 6) % 2 * 6, size[0], 12):
                board.paste(dark, (x, y))
        return board

    # ---- giving it ----
    def use(self):
        pic = self.picture()
        if pic is None:
            return
        try:
            self.viewer.make["write"](self.info, pic)
        except Exception as e:
            messagebox.showerror("Make a %s" % self.what, str(e), parent=self)
            return
        self.destroy()

    def save_copy(self):
        pic = self.picture()
        if pic is None:
            return
        out = filedialog.asksaveasfilename(parent=self, title="Save the %s" % self.what, defaultextension=".png",
                                           filetypes=[("PNG", "*.png"), ("TGA", "*.tga")])
        if out:
            pic.save(out)
