"""Board: a tkinter canvas that is an endless sheet, as on Obsidian Canvas (board.py has the maths and why). One for
every board-like window - the Campaign HUD (the game's panel and a screenshot as cards) and the editor's own layout
board - so they move the same way:

- the wheel zooms in and out at the mouse (Shift: in small steps; Ctrl + wheel the same - Obsidian's own);
- the middle button, or Space + the left one, drags the sheet; with pan_right the right button too (a click without
  moving is the owner's on_right_click, the map's way); the arrow keys move it;
- Shift+1 everything in view (the owner's content_box()), Shift+2 the picked thing (selection_box()), Shift+0 100 %.

The left button stays the owner's (picking, dragging cards). After every change of view on_view() is called and the
owner draws its things again with to_screen / picture(); the grid (grid=True) is drawn under them by the board."""

import tkinter as tk

from . import board as B


GRID_RGB = (78, 78, 78, 255)
GRID_DOT = "#4e4e4e"


class Board(tk.Canvas):
    def __init__(self, master, grid=True, pan_right=False, on_view=None, on_right_click=None,
                 content_box=None, selection_box=None, **kw):
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("background", "#202020")
        super().__init__(master, **kw)
        self.view = B.View()
        self.grid_on, self.pan_right = grid, pan_right
        self.on_view, self.on_right_click = on_view, on_right_click
        self.content_box, self.selection_box = content_box, selection_box
        self._pan, self._space, self._photos, self._fitted = None, False, {}, False
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind(seq, self._wheel)
        self.bind("<ButtonPress-2>", lambda e: self._pan_start(e, 2))
        self.bind("<B2-Motion>", self._pan_move)
        self.bind("<ButtonRelease-2>", self._pan_end)
        if pan_right:
            self.bind("<ButtonPress-3>", lambda e: self._pan_start(e, 3))
            self.bind("<B3-Motion>", self._pan_move)
            self.bind("<ButtonRelease-3>", self._pan_end)
        # the left button: Space held = the board's drag, else the owner's on_press / on_drag / on_release(e)
        self.on_press = self.on_drag = self.on_release = None
        self.bind("<ButtonPress-1>", self._left_press)
        self.bind("<B1-Motion>", self._left_motion)
        self.bind("<ButtonRelease-1>", self._left_release)
        self.bind("<KeyPress-space>", self._space_down)
        self.bind("<KeyRelease-space>", self._space_up)
        self.bind("<Enter>", lambda e: self.focus_set(), add="+")
        self.bind("<Configure>", self._configured, add="+")
        for key, (dx, dy) in (("Left", (60, 0)), ("Right", (-60, 0)), ("Up", (0, 60)), ("Down", (0, -60))):
            self.bind("<%s>" % key, lambda e, dx=dx, dy=dy: self.pan(dx, dy))
        self.bind("<Shift-Key-1>", lambda e: self.fit_content())
        self.bind("<exclam>", lambda e: self.fit_content())
        self.bind("<Shift-Key-2>", lambda e: self.fit_selection())
        self.bind("<at>", lambda e: self.fit_selection())
        self.bind("<quotedbl>", lambda e: self.fit_selection())     # Shift+2 on a German / Russian layout
        self.bind("<Shift-Key-0>", lambda e: self.actual_size())
        self.bind("<parenright>", lambda e: self.actual_size())
        self.bind("<equal>", lambda e: self.zoom_step(True))
        self.bind("<plus>", lambda e: self.zoom_step(True))
        self.bind("<minus>", lambda e: self.zoom_step(False))

    # ---- the view ----
    @property
    def zoom(self):
        return self.view.zoom

    def to_screen(self, x, y):
        return self.view.to_screen(x, y)

    def to_world(self, sx, sy):
        return self.view.to_world(sx, sy)

    def size(self):
        return max(1, self.winfo_width()), max(1, self.winfo_height())

    def changed(self):
        """The view moved: the grid again, then the owner's things."""
        self.delete("board-grid")
        if self.grid_on:
            self._draw_grid()
        if self.on_view:
            self.on_view()
        self.tag_lower("board-grid")

    def pan(self, dx, dy):
        self.view.pan(dx, dy)
        self.changed()

    def zoom_step(self, up, at=None, fine=False):
        self.view.zoom_at(up, at or tuple(v / 2 for v in self.size()), fine=fine)
        self.changed()

    def set_zoom(self, z, at=None):
        self.view.set_zoom(z, at or tuple(v / 2 for v in self.size()))
        self.changed()

    def actual_size(self):
        """100 % (one world unit = one screen pixel), the middle of the window staying where it is."""
        self.set_zoom(1.0)

    def fit(self, x0, y0, x1, y1, most=None):
        """The world box (x0, y0) - (x1, y1) as big as the window takes; most caps the zoom (1 = 100 %)."""
        self.view.fit((x0, y0, x1, y1), *self.size(), most=most)
        self._fitted = True
        self.changed()

    def fit_content(self):
        box = self.content_box() if self.content_box else None
        if box:
            self.fit(*box)

    def fit_selection(self):
        box = self.selection_box() if self.selection_box else None
        if box:
            self.fit(*box, most=B.ZOOMS[-1])

    def _configured(self, e):
        if not self._fitted and self.content_box and self.content_box():
            self.fit_content()                     # the first time it is seen: everything in view
        else:
            self.changed()

    # ---- drawing ----
    def _draw_grid(self):
        """The grid's dots: one picture drawn by Pillow when it is there (thousands of canvas ovals would make every
        zoom step slow), else ovals a little further apart."""
        w, h = self.size()
        try:
            from PIL import Image, ImageDraw, ImageTk
        except ImportError:
            Image = None
        if Image is None:
            for sx, sy in self.view.grid_points(w, h, least_px=24)[1]:
                self.create_oval(sx - 1, sy - 1, sx + 1, sy + 1, fill=GRID_DOT, outline="", tags="board-grid")
            return
        step, pts = self.view.grid_points(w, h)
        sheet = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dots = [(int(round(x)), int(round(y))) for x, y in pts]
        if step * self.zoom >= 24:                            # far enough apart: 2 x 2 dots, easier to see
            dots += [(x + dx, y + dy) for x, y in dots for dx, dy in ((1, 0), (0, 1), (1, 1))]
        ImageDraw.Draw(sheet).point(dots, fill=GRID_RGB)
        self._grid_photo = ImageTk.PhotoImage(sheet)
        self.create_image(0, 0, image=self._grid_photo, anchor="nw", tags="board-grid")

    def picture(self, img, x, y, tag, size=None, alpha=None):
        """Pillow picture img laid on the sheet with its top-left at world (x, y), size world units big (its own
        pixel size when None), alpha 0..1 how much of it shows. Only the part in the window is resized (a 2560 x 1440
        HUD at 800 % would be 20480 pixels wide); pixels stay sharp from 200 % up. Returns the canvas item or None."""
        from PIL import Image, ImageTk
        w, h = size or img.size
        if w <= 0 or h <= 0:
            return None
        cw, ch = self.size()
        sx0, sy0 = self.to_screen(x, y)
        sx1, sy1 = self.to_screen(x + w, y + h)
        vx0, vy0, vx1, vy1 = max(sx0, 0), max(sy0, 0), min(sx1, cw), min(sy1, ch)
        if vx1 - vx0 < 1 or vy1 - vy0 < 1:
            self._photos.pop(tag, None)
            return None
        kx, ky = img.size[0] / (sx1 - sx0), img.size[1] / (sy1 - sy0)          # picture pixels per screen pixel
        crop = img.crop((int((vx0 - sx0) * kx), int((vy0 - sy0) * ky),
                         max(int((vx0 - sx0) * kx) + 1, int(round((vx1 - sx0) * kx))),
                         max(int((vy0 - sy0) * ky) + 1, int(round((vy1 - sy0) * ky)))))
        out = (max(1, int(round(vx1 - vx0))), max(1, int(round(vy1 - vy0))))
        crop = crop.resize(out, Image.NEAREST if kx <= 0.5 else Image.BILINEAR)
        if alpha is not None and alpha < 1:
            crop = crop.convert("RGBA")
            a = crop.getchannel("A").point(lambda v: int(v * max(0.0, alpha)))
            crop.putalpha(a)
        photo = ImageTk.PhotoImage(crop)
        self._photos[tag] = photo
        return self.create_image(vx0, vy0, image=photo, anchor="nw", tags=tag)

    def box(self, x, y, w, h, **kw):
        """A rectangle round the world box (x, y, w, h)."""
        sx0, sy0 = self.to_screen(x, y)
        sx1, sy1 = self.to_screen(x + w, y + h)
        return self.create_rectangle(sx0, sy0, sx1, sy1, **kw)

    # ---- the mouse ----
    def _wheel(self, e):
        if getattr(e, "num", None) in (4, 5):
            up = e.num == 4
        else:
            up = (getattr(e, "delta", 0) or 0) > 0
        self.zoom_step(up, (e.x, e.y), fine=bool((getattr(e, "state", 0) or 0) & 0x0001))
        return "break"

    def _space_down(self, e):
        self._space = True
        self.configure(cursor="fleur")
        return "break"

    def _space_up(self, e):
        self._space = False
        if self._pan is None:
            self.configure(cursor="")
        return "break"

    def _left_press(self, e):
        self.focus_set()
        if self._space:
            return self._pan_start(e, 1)
        return self.on_press(e) if self.on_press else None

    def _left_motion(self, e):
        if self._pan is not None and self._pan[0] == 1:
            return self._pan_move(e)
        return self.on_drag(e) if self.on_drag else None

    def _left_release(self, e):
        if self._pan is not None and self._pan[0] == 1:
            return self._pan_end(e)
        return self.on_release(e) if self.on_release else None

    def _pan_start(self, e, button):
        self._pan = (button, e.x, e.y, False)
        self.configure(cursor="fleur")
        return "break"

    def _pan_move(self, e):
        if self._pan is None:
            return None
        button, x, y, moved = self._pan
        if not moved and abs(e.x - x) + abs(e.y - y) < 4:
            return "break"                       # a click, not a drag yet
        self._pan = (button, e.x, e.y, True)
        self.pan(e.x - x, e.y - y)
        return "break"

    def _pan_end(self, e):
        if self._pan is None:
            return None
        button, _, _, moved = self._pan
        self._pan = None
        self.configure(cursor="fleur" if self._space else "")
        if button == 3 and not moved and self.on_right_click:
            self.on_right_click(e)
        return "break"


__all__ = ["Board"]
