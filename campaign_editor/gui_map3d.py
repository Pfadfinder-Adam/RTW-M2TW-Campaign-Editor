"""Maps > 3D: the campaign map in 3D, drawn by the graphics card the way the games draw it (glmap: the ground grid of
map_heights, the game's blend masks between grounds, its light, the sea sheet) - what the Terrain editor's brushes
painted and not written yet included: the map is made again whenever the tab opens after a change.

Right drag: move over the map (the land follows the mouse); the wheel held down and dragged: turn left / right and
look up / down; the wheel turned: nearer / farther; the arrow keys (or W A S D) move too (the user's own scheme,
2026-10-15 - the left button stays free for picking things later). While the mouse moves the view is drawn at half size,
then sharp again a moment after it stops.

The older picture drawn without the card (terrain3d.render, the models as small pictures on it) was taken out at the
user's word (2026-10-16: 'the old 3D is not needed at all, this one flies and loads faster'); terrain3d.colour_map
stays - the minimap is drawn from it. Without OpenGL 3.3 the bar says why."""

import os
import threading
import time
import tkinter as tk
from tkinter import ttk

from . import theme
from .gui_util import hint

HINT = ("The campaign map in 3D, drawn by the graphics card the way the games draw it: the game's own ground textures "
        "for each climate (descr_aerial_map_ground_types.txt) blended with the game's own masks, the relief of "
        "map_heights, the game's light and sea. What the brushes of Terrain and Coast & "
        "heights painted shows here before it is written. Right drag: move over the map; the wheel held down and "
        "dragged: turn and look up or down; the wheel turned: nearer / farther; the arrow keys or W A S D move too. The relief stands as "
        "high as in the game. The game's mountains, rivers, trees, towns and "
        "armies come in later versions - this shows the ground they stand on.")


class Map3DView(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._for, self._building = None, False
        self._drag, self._sharp_job, self._photo = None, None, None
        bar = ttk.Frame(self, padding=(4, 4))
        bar.pack(fill="x")
        self.v_winter = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Winter", variable=self.v_winter, command=self.rebuild).pack(side="left")
        self.gl, self.gcam = None, None
        from .gui_util import tip
        ttk.Button(bar, text="Whole map", command=self.reset_view).pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        ttk.Button(bar, text="Draw it again", command=self.rebuild).pack(side="left", padx=(theme.BUTTON_GAP, 0))
        b_mini = ttk.Button(bar, text="Make the minimap from it", command=self.make_minimap)
        b_mini.pack(side="left", padx=(theme.BUTTON_GAP, 0))
        tip(b_mini, "The campaign's minimap (radar_map1 / radar_map2.tga - the small map in the game's bottom-left "
                    "corner) drawn again from this map seen from above: the ground's textures, relief, rivers, the "
                    "sea's depths; each picture keeps its size and border. Kept for Apply (Preview shows it).")
        b_own = ttk.Button(bar, text="Own minimap...", command=self.own_minimap)
        b_own.pack(side="left", padx=(theme.BUTTON_GAP, 0))
        tip(b_own, "A picture of your own (any size, .tga / .png / .jpg...) as the campaign's minimap: fitted into "
                   "each minimap picture, its size and border kept. Kept for Apply; Restore takes it back.")
        hint(bar, HINT, width=460).pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        self.lbl = ttk.Label(bar, foreground=theme.palette()["muted"])
        self.lbl.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        self.canvas = tk.Canvas(self, background="#9db8cf", highlightthickness=0, takefocus=1)
        self.canvas.pack(fill="both", expand=True)
        c = self.canvas
        c.bind("<Configure>", lambda e: self.draw())
        c.bind("<ButtonPress-3>", lambda e: self._press(e, "move"))
        c.bind("<ButtonPress-2>", lambda e: self._press(e, "turn"))
        c.bind("<B3-Motion>", self._motion)
        c.bind("<B2-Motion>", self._motion)
        c.bind("<ButtonRelease-3>", self._release)
        c.bind("<ButtonRelease-2>", self._release)
        c.bind("<MouseWheel>", lambda e: self._zoom(-1 if e.delta > 0 else 1))
        c.bind("<Button-4>", lambda e: self._zoom(-1))
        c.bind("<Button-5>", lambda e: self._zoom(1))
        for keys, fwd, right in ((("<Up>", "w"), 1, 0), (("<Down>", "s"), -1, 0), (("<Left>", "a"), 0, -1),
                                 (("<Right>", "d"), 0, 1)):
            for k in keys:
                c.bind(k if k.startswith("<") else "<KeyPress-%s>" % k, lambda e, f=fwd, r=right: self._key(f, r))

    # ---- the data ----
    def _source(self):
        """The mod as the Terrain editor holds it: its own copy whose pictures the brushes paint into (heights,
        ground, climates, rivers, the coast) - else the loaded mod as the files have it."""
        mod = self.app.mod
        ed = getattr(self.app, "editors", {}).get("terrain")
        own = getattr(ed, "mod", None)
        if own is not None and mod is not None and os.path.normcase(os.path.abspath(own.data)) == \
                os.path.normcase(os.path.abspath(mod.data)):
            return own
        return mod

    def own_minimap(self):
        """'Own minimap...': a picture of the modder's own as the campaign's minimap (minimap.redraw picture=)."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(parent=self, title="Own minimap picture", filetypes=[
            ("Pictures", "*.tga *.png *.jpg *.jpeg *.bmp *.dds"), ("All files", "*.*")])
        if path:
            self.make_minimap(picture=path)

    def make_minimap(self, picture=None):
        """'Make the minimap from it': the campaign's minimap pictures drawn again from the map as the brushes
        leave it (minimap.redraw on the Terrain editor's copy), kept for Apply."""
        from tkinter import messagebox
        from . import minimap as MM
        from .gui_util import keep_for_apply
        from .plan import Plan
        app, camp = self.app, self.app.v_campaign.get()
        if app.mod is None or not camp:
            self.lbl.configure(text="load a mod first")
            return
        self.lbl.configure(text="drawing the minimap...")
        self.update_idletasks()

        def make():
            plan = Plan(app.mod, "minimap", "minimap", {})
            MM.redraw(plan, camp, source=self._source(), picture=picture)
            return plan
        what = ("The minimap of %s from %s" % (camp, os.path.basename(picture)) if picture else
                "The minimap of %s drawn from the map" % camp)
        try:
            if keep_for_apply(app, "minimap:%s" % camp, what, make,
                              title="Minimap"):
                self.lbl.configure(text="minimap kept - Preview, then Apply changes")
        except ImportError:
            messagebox.showerror("Minimap", "drawing pictures needs Pillow")
        except (OSError, ValueError) as e:
            messagebox.showerror("Minimap", "That picture cannot be used: %s" % e, parent=self)
            self.lbl.configure(text="")

    def _stamp(self):
        """What the picture was made from: the mod, the campaign, the brushes' changes (their Undo list and the
        points they changed), winter."""
        mod = self.app.mod
        ed = getattr(self.app, "editors", {}).get("terrain")
        work = ()
        if ed is not None:
            work = (len(getattr(ed, "_undo", ())), len(getattr(ed, "_redo", ())),
                    tuple(len(getattr(ed, k, ())) for k in ("heights", "ground", "features", "climate", "coast")),
                    tuple(len(v) for v in (getattr(ed, "cpx", {}) or {}).values()), id(getattr(ed, "mod", None)))
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
        from . import glmap
        ok, why = glmap.available()
        if not ok:
            self.lbl.configure(text="the 3D map needs a graphics card with OpenGL 3.3: %s" % why)
            return
        stamp, mod, campaign, winter = self._stamp(), self._source(), self.app.v_campaign.get(), self.v_winter.get()
        self._building = True
        self.lbl.configure(text="laying the game's textures on the map...")
        got = {}

        def work():                                      # the arrays the card needs (no OpenGL in this thread)
            t = time.time()
            try:
                got["data"] = glmap.MapData(mod, campaign, winter=winter)
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
            self._gpu_ready(got["data"], stamp, got["time"])
        th = threading.Thread(target=work, daemon=True)
        th.start()
        self.after(250, done)

    def _gpu_ready(self, data, stamp, took):
        """The card takes the map (main thread: OpenGL lives here) - False when it cannot (said in the bar)."""
        from . import glmap
        old_gl = self.gl
        try:
            gl = glmap.GLMap(data)
        except Exception as e:
            self.lbl.configure(text="the graphics card cannot draw it: %s" % e)
            return False
        if old_gl is not None:
            old_gl.release()
        same = old_gl is not None and old_gl.data.heights.shape == data.heights.shape
        self.gl, self._for = gl, stamp
        if self.gcam is None or not same:
            self.gcam = glmap.Camera(data)
        notes = "; ".join(data.notes)
        self.lbl.configure(text="made in %.1f s%s" % (took, (" - " + notes) if notes else ""))
        self.draw()
        return True

    def reset_view(self, draw=True):
        if self.gl is None:
            return
        from . import glmap
        self.gcam = glmap.Camera(self.gl.data)
        if draw:
            self.draw()

    # ---- drawing ----
    def _on(self):
        return self.gl is not None and self.gcam is not None

    def draw(self, half=False):
        if not self._on():
            return
        from PIL import Image, ImageTk
        W, H = max(50, self.canvas.winfo_width()), max(50, self.canvas.winfo_height())
        f = 2 if half else 1
        try:
            arr = self.gl.render(self.gcam, W // f, H // f)
        except Exception as e:                           # the card failed now: said in the bar, never a crash
            self.lbl.configure(text="the graphics card stopped drawing: %s" % e)
            self.gl.release()
            self.gl, self._for = None, None
            return
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
        if self._drag is None or not self._on():
            return
        how, x0, y0 = self._drag
        dx, dy = e.x - x0, e.y - y0
        self._drag = (how, e.x, e.y)
        cam = self.gcam
        if how == "move":                               # the land follows the mouse
            per = cam.dist / max(200.0, self.canvas.winfo_height()) * 1.1
            cam.moved(dy * per, -dx * per)
        else:                                           # turn, and look up / down
            cam.yaw += dx * 0.006
            cam.pitch = min(1.55, max(0.15, cam.pitch + dy * 0.004))
        self._changed_view()

    def _release(self, e):
        self._drag = None
        self._sharp_later()

    def _zoom(self, way):
        if self._on():
            self.gcam.zoom(1.15 if way > 0 else 1 / 1.15)
            self._changed_view()

    def _key(self, fwd, right):
        if self._on():
            step = self.gcam.dist * 0.08
            self.gcam.moved(fwd * step, right * step)
            self._changed_view()


__all__ = ["Map3DView"]
