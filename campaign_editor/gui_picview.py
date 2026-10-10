"""A picture looked at closely (the user, 2026-10-09: 'click a picture and it opens big in a window of its own, to look
at it'): any picture the editor shows - TGA, DDS, Medieval II's .texture, PNG - in a window as big as the screen
allows, the wheel zooms in and out round the mouse (small pictures pixel by pixel, sharp), the left or right button
drags it, a checkerboard shows through where it is see-through; its file, size and format under it. One window a
picture: a second click brings the open one forward."""

import os
import tkinter as tk
from tkinter import ttk

_OPEN = {}                                    # the picture's path (+ its crop) -> its open window

STEPS = (0.125, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32)


def first_zoom(w, h, room_w, room_h):
    """The zoom a picture opens at: as big as the room takes - a small one (a 24 px button) enlarged by whole steps so
    every pixel stays sharp, a big one made smaller to fit."""
    fit = min(room_w / max(w, 1), room_h / max(h, 1))
    fitting = [z for z in STEPS if z <= fit]
    return fitting[-1] if fitting else STEPS[0]


def next_zoom(z, up):
    """The next zoom step up or down from z."""
    if up:
        return next((s for s in STEPS if s > z + 1e-9), STEPS[-1])
    return next((s for s in reversed(STEPS) if s < z - 1e-9), STEPS[0])


def describe(path, im):
    """'name - 48 x 64 px, 32-bit TGA' for the line under the picture."""
    size = "%d x %d px" % im.size
    low = path.lower()
    try:
        from .factionart import picture_info
        info = picture_info(path)
    except Exception:
        info = None
    if low.endswith(".tga") and info:
        kind = "%d-bit TGA" % info[2]
    elif low.endswith((".dds", ".texture")) and info:
        kind = "%s DDS%s" % (info[2], " in a Medieval II .texture" if low.endswith(".texture") else "")
    else:
        kind = os.path.splitext(path)[1].lstrip(".").upper() or "picture"
    return "%s - %s, %s" % (os.path.basename(path), size, kind)


def view_picture(parent, path, title=None, crop=None):
    """Open path (crop = (x, y, w, h) of a sheet) big in a window of its own; the open one of the same picture comes
    forward. Returns the window, or None when the picture cannot be read (said in the window's place)."""
    key = (os.path.normcase(os.path.abspath(path)), tuple(crop) if crop else None)
    old = _OPEN.get(key)
    if old is not None:
        try:
            old.deiconify()
            old.lift()
            old.focus_force()
            return old
        except tk.TclError:
            _OPEN.pop(key, None)
    try:
        from PIL import ImageTk
        from .recolour import read_picture
        im = read_picture(path).convert("RGBA")
        if crop:
            x, y, w, h = crop
            im = im.crop((x, y, x + w, y + h))
    except Exception as e:                      # no Pillow, or a file it cannot read
        from tkinter import messagebox
        messagebox.showinfo("Picture", "%s cannot be shown here: %s" % (os.path.basename(path), e), parent=parent)
        return None
    win = PictureWindow(parent, path, im, title, ImageTk)
    _OPEN[key] = win
    win.bind("<Destroy>", lambda e: _OPEN.pop(key, None) if e.widget is win else None, add="+")
    return win


class PictureWindow(tk.Toplevel):
    def __init__(self, parent, path, im, title, ImageTk):
        super().__init__(parent)
        self.title(title or os.path.basename(path))
        self.im, self._tk, self._photo = im, ImageTk, None
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        room_w, room_h = int(sw * 0.8), int(sh * 0.75)
        self.z = first_zoom(im.width, im.height, room_w, room_h)
        cw = max(320, min(room_w, int(im.width * self.z) + 40))
        ch = max(200, min(room_h, int(im.height * self.z) + 40))
        self.canvas = tk.Canvas(self, width=cw, height=ch, highlightthickness=0, background="#3c3c3c")
        self.canvas.pack(fill="both", expand=True)
        bar = ttk.Frame(self, padding=(8, 4))
        bar.pack(fill="x")
        self.v_line = tk.StringVar()
        ttk.Label(bar, textvariable=self.v_line).pack(side="left")
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Fit", command=self.fit).pack(side="right", padx=4)
        ttk.Button(bar, text="1 : 1", command=lambda: self.set_zoom(1)).pack(side="right")
        self.about = describe(path, im)
        self.cx, self.cy = cw / 2, ch / 2         # where the picture's middle stands on the canvas
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):         # a wheel of its own: zoom
            self.canvas.bind(seq, self._wheel)
        for b in (1, 3):
            self.canvas.bind("<ButtonPress-%d>" % b, self._press)
            self.canvas.bind("<B%d-Motion>" % b, self._drag)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<plus>", lambda e: self.set_zoom(next_zoom(self.z, True)))
        self.bind("<minus>", lambda e: self.set_zoom(next_zoom(self.z, False)))
        self.transient(parent.winfo_toplevel())
        self.draw()

    def fit(self):
        self.update_idletasks()
        self.cx, self.cy = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        self.set_zoom(first_zoom(self.im.width, self.im.height, self.canvas.winfo_width() - 20,
                                 self.canvas.winfo_height() - 20))

    def set_zoom(self, z, at=None):
        """z, keeping the picture's point under at (canvas x, y; the middle when None) where it is."""
        if at is None:
            at = (self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)
        k = z / self.z
        self.cx = at[0] + (self.cx - at[0]) * k
        self.cy = at[1] + (self.cy - at[1]) * k
        self.z = z
        self.draw()

    def _wheel(self, e):
        up = getattr(e, "num", None) == 4 or (getattr(e, "delta", 0) or 0) > 0
        self.set_zoom(next_zoom(self.z, up), (e.x, e.y))
        return "break"

    def _press(self, e):
        self._grab = (e.x, e.y, self.cx, self.cy)

    def _drag(self, e):
        x, y, cx, cy = self._grab
        self.cx, self.cy = cx + e.x - x, cy + e.y - y
        self.draw()

    def _board(self, size):
        """A checkerboard at least size big, made once (and again only when the window grows past it)."""
        from PIL import Image
        have = getattr(self, "_checks", None)
        if have is None or have.width < size[0] or have.height < size[1]:
            w, h = max(size[0], 64), max(size[1], 64)
            tile = Image.new("RGBA", (16, 16), (200, 200, 200, 255))
            tile.paste(Image.new("RGBA", (8, 8), (150, 150, 150, 255)), (0, 0))
            tile.paste(Image.new("RGBA", (8, 8), (150, 150, 150, 255)), (8, 8))
            have = Image.new("RGBA", (w, h))
            for yy in range(0, h, 16):
                for xx in range(0, w, 16):
                    have.paste(tile, (xx, yy))
            self._checks = have
        return have.crop((0, 0, size[0], size[1]))

    def draw(self):
        from PIL import Image
        c = self.canvas
        c.delete("all")
        w, h = max(1, int(self.im.width * self.z)), max(1, int(self.im.height * self.z))
        x0, y0 = self.cx - w / 2, self.cy - h / 2
        # only the part on the canvas is scaled (a 2048 px texture at x 8 would be 16384 px wide)
        vw, vh = max(1, c.winfo_width()), max(1, c.winfo_height())
        left, top = max(0, -x0), max(0, -y0)
        right, bottom = min(w, vw - x0), min(h, vh - y0)
        if right > left and bottom > top:
            src = (left / self.z, top / self.z, right / self.z, bottom / self.z)
            size = (max(1, int(right - left)), max(1, int(bottom - top)))
            part = self.im.resize(size, Image.NEAREST if self.z >= 1 else Image.LANCZOS, box=src)
            board = self._board(size).copy()                      # see-through shows as a checkerboard
            board.alpha_composite(part)
            self._photo = self._tk.PhotoImage(board)
            c.create_image(x0 + left, y0 + top, image=self._photo, anchor="nw")
        self.v_line.set("%s   zoom %s%%   (wheel: zoom, drag: move)" % (self.about, int(round(self.z * 100))))
