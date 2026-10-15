"""Maps > 3D: the campaign map in 3D in the game's own ground textures (terrain3d draws it) - what the Terrain editor's
brushes painted and not written yet included: the picture is made again whenever the tab opens after a change.

Left drag: move over the map (the land follows the mouse); right drag: turn left / right and look up / down; the
wheel: nearer / farther; the arrow keys (or W A S D) move too. While the mouse moves the view is drawn at half size,
then sharp again a moment after it stops."""

import threading
import time
import tkinter as tk
from tkinter import ttk

from . import theme
from .gui_util import hint

HINT = ("The campaign map in 3D, laid with the game's own ground textures for each climate (descr_aerial_map_ground_"
        "types.txt) - the relief of map_heights, the water, the rivers. What the brushes of Terrain and Coast & "
        "heights painted shows here before it is written. Left drag: move over the map; right drag: turn and look up "
        "or down; the wheel: nearer / farther; the arrow keys or W A S D move too. 'Heights x' makes the relief "
        "taller or flatter (only here, nothing is written). The game's own 3D map has trees, towns and its own light "
        "on top - this shows the ground it lies on.")


class Map3DView(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.cmap, self.cam, self._for, self._building = None, None, None, False
        self._drag, self._sharp_job, self._photo = None, None, None
        bar = ttk.Frame(self, padding=(4, 4))
        bar.pack(fill="x")
        self.v_winter = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Winter", variable=self.v_winter, command=self.rebuild).pack(side="left")
        ttk.Label(bar, text="Heights x").pack(side="left", padx=(theme.BUTTON_GAP * 2, 2))
        self.v_exag = tk.DoubleVar(value=1.0)
        sc = ttk.Scale(bar, from_=0.3, to=4.0, variable=self.v_exag, length=140,
                       command=lambda v: self._changed_view())
        sc.pack(side="left")
        ttk.Button(bar, text="Whole map", command=self.reset_view).pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        ttk.Button(bar, text="Draw it again", command=self.rebuild).pack(side="left", padx=(theme.BUTTON_GAP, 0))
        hint(bar, HINT, width=460).pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        self.lbl = ttk.Label(bar, foreground=theme.palette()["muted"])
        self.lbl.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        self.canvas = tk.Canvas(self, background="#9db8cf", highlightthickness=0, takefocus=1)
        self.canvas.pack(fill="both", expand=True)
        c = self.canvas
        c.bind("<Configure>", lambda e: self.draw())
        c.bind("<ButtonPress-1>", lambda e: self._press(e, "move"))
        c.bind("<ButtonPress-3>", lambda e: self._press(e, "turn"))
        c.bind("<B1-Motion>", self._motion)
        c.bind("<B3-Motion>", self._motion)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<ButtonRelease-3>", self._release)
        c.bind("<MouseWheel>", lambda e: self._zoom(-1 if e.delta > 0 else 1))
        c.bind("<Button-4>", lambda e: self._zoom(-1))
        c.bind("<Button-5>", lambda e: self._zoom(1))
        for keys, fwd, right in ((("<Up>", "w"), 1, 0), (("<Down>", "s"), -1, 0), (("<Left>", "a"), 0, -1),
                                 (("<Right>", "d"), 0, 1)):
            for k in keys:
                c.bind(k if k.startswith("<") else "<KeyPress-%s>" % k, lambda e, f=fwd, r=right: self._key(f, r))

    # ---- the data ----
    def _stamp(self):
        """What the picture was made from: the mod, the campaign, the brushes' changes (their Undo list), winter."""
        mod = self.app.mod
        ed = getattr(self.app, "editors", {}).get("terrain")
        work = (len(getattr(ed, "_undo", ())), len(getattr(ed, "_redo", ()))) if ed is not None else (0, 0)
        return (getattr(mod, "data", None), self.app.v_campaign.get(), work, self.v_winter.get())

    def load(self):
        """The tab opened: the picture made again when anything it shows changed since."""
        if self.app.mod is None:
            self.lbl.configure(text="load a mod first")
            return
        if self._stamp() != self._for:
            self.rebuild()
        else:
            self.draw()

    def rebuild(self):
        if self.app.mod is None or self._building:
            return
        try:
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.lbl.configure(text="the 3D map needs NumPy and Pillow (the editor's exe has both)")
            return
        from . import terrain3d as T3
        stamp, mod, campaign, winter = self._stamp(), self.app.mod, self.app.v_campaign.get(), self.v_winter.get()
        self._building = True
        self.lbl.configure(text="laying the game's textures on the map...")
        got = {}

        def work():
            t = time.time()
            try:
                got["cmap"] = T3.colour_map(mod, campaign, winter=winter)
            except Exception as e:                       # said in the bar, never a crash
                got["error"] = str(e)
            got["time"] = time.time() - t

        def done():
            if th.is_alive():                            # looked at rarely: the work keeps Python to itself
                self.after(250, done)
                return
            self._building = False
            if not self.winfo_exists():
                return
            if "error" in got:
                self.lbl.configure(text="cannot draw it: %s" % got["error"])
                return
            old = self.cmap
            self.cmap = got["cmap"]
            self._for = stamp
            if self.cam is None or old is None or old.rgb.shape != self.cmap.rgb.shape:
                self.reset_view(draw=False)
            notes = "; ".join(self.cmap.notes)
            self.lbl.configure(text="made in %.1f s%s" % (got["time"], (" - " + notes) if notes else ""))
            self.draw()
        th = threading.Thread(target=work, daemon=True)
        th.start()
        self.after(250, done)

    def reset_view(self, draw=True):
        if self.cmap is None:
            return
        from . import terrain3d as T3
        self.cam = T3.Camera(self.cmap)
        self.cam.exaggerate = self.v_exag.get()
        if draw:
            self.draw()

    # ---- drawing ----
    def draw(self, half=False):
        if self.cmap is None or self.cam is None:
            return
        from PIL import Image, ImageTk
        from . import terrain3d as T3
        W, H = max(50, self.canvas.winfo_width()), max(50, self.canvas.winfo_height())
        f = 2 if half else 1
        self.cam.exaggerate = self.v_exag.get()
        arr = T3.render(self.cmap, self.cam, W // f, H // f, steps=None if not half else 300)
        im = Image.fromarray(arr)
        if f > 1:
            im = im.resize((W, H), Image.BILINEAR)
        self._photo = ImageTk.PhotoImage(im)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

    def _changed_view(self):
        self.draw(half=True)
        self._sharp_later()

    def _sharp_later(self):
        if self._sharp_job is not None:
            self.after_cancel(self._sharp_job)
        self._sharp_job = self.after(180, self._sharp)

    def _sharp(self):
        self._sharp_job = None
        self.draw()

    # ---- the mouse and keys ----
    def _press(self, e, how):
        self.canvas.focus_set()
        self._drag = (how, e.x, e.y)

    def _motion(self, e):
        if self._drag is None or self.cam is None:
            return
        how, x0, y0 = self._drag
        dx, dy = e.x - x0, e.y - y0
        self._drag = (how, e.x, e.y)
        cam = self.cam
        if how == "move":                               # the land follows the mouse
            per = (cam.alt + 40) / max(200.0, self.canvas.winfo_height()) * 3.0
            cam.moved(dy * per, -dx * per)
        else:                                           # turn, and look up / down
            cam.yaw += dx * 0.006
            cam.horizon = min(0.9, max(-0.6, cam.horizon + dy * 0.002))
        self._changed_view()

    def _release(self, e):
        self._drag = None
        self._sharp_later()

    def _zoom(self, way):
        if self.cam is None:
            return
        cam = self.cam
        f = 1.15 if way > 0 else 1 / 1.15
        cam.alt = min(max(self.cmap.height.shape) * 0.6, max(4.0, cam.alt * f))
        cam.far = min(max(self.cmap.height.shape) * 1.2, max(120.0, cam.far * (f ** 0.7)))
        self._changed_view()

    def _key(self, fwd, right):
        if self.cam is None:
            return
        step = (self.cam.alt + 40) * 0.25
        self.cam.moved(fwd * step, right * step)
        self._changed_view()


__all__ = ["Map3DView"]
