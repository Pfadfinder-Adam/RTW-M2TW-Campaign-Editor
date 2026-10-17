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
        "map_heights, the game's light and sea, the beach and the surf rolling in along the coast, the game's own "
        "mountains, hills, volcanoes and rivers (descr_aerial_map_tile_models.txt: placed as the game places them, the "
        "pieces picked by the tile - the game picks with its own dice). Layers shows or leaves out each of them "
        "(the sea left out shows the sea floor; the surf can stand still). What the brushes of Terrain and Coast & "
        "heights painted shows here before it is written. Right drag: move over the map; the wheel held down and "
        "dragged: turn and look up or down; the wheel turned: nearer / farther; the arrow keys or W A S D move too. "
        "Heights brush: the left button raises or lowers the land under the circle while held (Ctrl + wheel or [ ] "
        "for its size) - the brush of Coast & heights, its Undo and Apply shared. The relief stands as "
        "high as in the game; the towns, ports, resources, armies, agents and fleets stand as descr_strat.txt will have them (what the Map moved or added before the write included), with the roads and region borders.")


class Map3DView(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._for, self._building, self._strat_for = None, False, None
        self._drag, self._sharp_job, self._photo = None, None, None
        bar = ttk.Frame(self, padding=(4, 4))
        bar.pack(fill="x")
        self.v_winter = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Winter", variable=self.v_winter, command=self.rebuild).pack(side="left")
        self.gl, self.gcam, self._anim_job = None, None, None
        # Layers: each thing on the map shown or left out (the sea off shows the sea floor); the surf moving or still
        from .glmap import LAYERS
        from .gui_util import DropPanel
        self.v_show = {key: tk.BooleanVar(value=True) for key, _ in LAYERS}
        self.v_moving = tk.BooleanVar(value=True)

        def build_layers(f):
            for key, label in LAYERS:
                ttk.Checkbutton(f, text=label, variable=self.v_show[key], command=self._layers_changed).pack(anchor="w")
            ttk.Checkbutton(f, text="The surf and the trees move", variable=self.v_moving,
                            command=self._layers_changed).pack(anchor="w")
        lb = ttk.Button(bar, text="Layers \u25be")
        lb.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        self._layers_panel = DropPanel(lb, build_layers)
        # the heights brush right on the 3D map: the Terrain editor's own (its strokes, Undo and Apply shared), the
        # land changing under the circle while the button is held, not when the stroke ends
        self.v_brush_on = tk.BooleanVar(value=False)
        self._paint, self._mouse, self._ring = False, None, None
        from .gui_util import tip as _tip
        _tip(ttk.Checkbutton(bar, text="Heights brush", variable=self.v_brush_on, command=self._brush_toggled),
             "The left button raises (or lowers, smooths, levels) the land under the circle, like the heights brush "
             "of Coast & heights - the same brush: its strokes, Undo and Apply are shared. Held longer, it does "
             "more; the map changes while you hold it. Ctrl + the wheel, or [ and ], make the circle smaller or "
             "bigger; 'brush' beside it has the rest.").pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        bb = ttk.Button(bar, text="brush \u25be")
        bb.pack(side="left", padx=(2, 0))
        self._brush_panel = DropPanel(bb, self._build_brush)
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
        c.bind("<Motion>", self._hover)
        c.bind("<ButtonPress-1>", self._paint_start)
        c.bind("<B1-Motion>", self._hover)
        c.bind("<ButtonRelease-1>", self._paint_end)
        c.bind("<Leave>", lambda e: self._hover(None))
        c.bind("<Control-MouseWheel>", lambda e: self._resize(1 if e.delta > 0 else -1))
        c.bind("<Control-Button-4>", lambda e: self._resize(1))
        c.bind("<Control-Button-5>", lambda e: self._resize(-1))
        c.bind("<KeyPress-bracketright>", lambda e: self._resize(1))
        c.bind("<KeyPress-bracketleft>", lambda e: self._resize(-1))
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

    def _strat(self):
        """(descr_strat as Apply will leave it - the Map's armies, agents, fleets, towns and resources added, moved
        or taken away and the other windows' changes kept - as a Strat, a key telling it apart) or (None, None):
        the file as it is."""
        app = self.app
        try:
            from .plan import kept_texts
            from .strat import Strat
            plans = [p["plan"] for p in app.session_parts().values() if p.get("plan") is not None]
            if app.faction_pending():
                plans.append(app._faction_plan())
            want = os.path.normcase(os.path.abspath(app.mod.campaign_file(app.v_campaign.get(), "descr_strat.txt")))
            f = next((f for p, f in kept_texts(plans).items() if os.path.normcase(os.path.abspath(p)) == want), None)
            if f is None:
                return None, None
            return Strat(f), hash(f.dump())
        except Exception:                                # nothing to write yet, a half-made change: the file
            return None, None

    def load(self):
        """The tab opened: the picture made again when anything it shows changed since; when only descr_strat did
        (the Map's armies moved), only what stands on the map is laid again."""
        if self.app.mod is None:
            self.lbl.configure(text="load a mod first")
            return
        strat, key = self._strat()
        if self._stamp() != self._for:
            self.rebuild(strat, key)
            return
        if self.gl is not None and key != self._strat_for:
            try:
                self.gl.data.set_strat(self._source(), self.app.v_campaign.get(), strat)
                self.gl.models_placed()
                self._strat_for = key
            except Exception as e:                       # said in the bar, never a crash
                self.lbl.configure(text="the towns and armies could not be laid again: %s" % e)
        self.draw()

    def rebuild(self, strat=None, key=None):
        if self.app.mod is None or self._building:
            return
        if strat is None and key is None:
            strat, key = self._strat()
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
                got["data"] = glmap.MapData(mod, campaign, winter=winter, strat=strat)
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
            if self._gpu_ready(got["data"], stamp, got["time"]):
                self._strat_for = key
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
        self._animate()
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
        t = (time.monotonic() * 0.2) % 1.0 if self.v_moving.get() else 0.3    # a wave every 5 s, as the game
        try:
            arr = self.gl.render(self.gcam, W // f, H // f, t, {k: v.get() for k, v in self.v_show.items()},
                                 clock=time.monotonic() if self.v_moving.get() else 0.0)
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
        self._draw_ring()

    def _layers_changed(self):
        self.draw()
        self._animate()

    def _animate(self):
        """The surf rolls in (a frame every 0.1 s) while the tab is seen, the coast shown and the surf ticked to
        move - nothing runs otherwise."""
        if self._anim_job is not None:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        if not (self._on() and self.v_moving.get() and (self.v_show["coast"].get() or self.v_show["trees"].get())):
            return
        try:
            seen = self.winfo_viewable()
        except tk.TclError:
            return
        if seen and self._drag is None and self._sharp_job is None:
            self.draw()
        self._anim_job = self.after(100 if seen else 600, self._animate)

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

    # ---- the heights brush ----
    def _terrain(self):
        """The Terrain editor (made and bound to the mod the first time, without showing its tab), or None."""
        app = self.app
        if app.mod is None:
            return None
        ed = app.editors.get("terrain")
        if ed is None:
            from .gui_terrain import TerrainEditor
            ed = app.editors["terrain"] = TerrainEditor(app.nb, app)
        if ed.mod is None or os.path.normcase(os.path.abspath(ed.mod.data)) != \
                os.path.normcase(os.path.abspath(app.mod.data)):
            app._rebind(ed)
        return ed if ed._bound() else None

    def _build_brush(self, f):
        ed = self._terrain()
        if ed is None:
            ttk.Label(f, text="load a mod first").pack(anchor="w")
            return
        for val, text in (("raise", "Raise"), ("lower", "Lower"), ("smooth", "Smooth"), ("level", "Level to height")):
            ttk.Radiobutton(f, text=text, value=val, variable=ed.v_tool).pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(4, 0))
        ttk.Label(row, text="height to level to (0-255)").pack(side="left")
        ttk.Spinbox(row, from_=0, to=255, width=4, textvariable=ed.v_level).pack(side="left", padx=(4, 0))
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(4, 0))
        ttk.Label(row, text="size (heights points across - 2 a tile)").pack(side="left")
        ttk.Spinbox(row, from_=1, to=80, width=4, textvariable=ed.v_brush,
                    command=self._draw_ring).pack(side="left", padx=(4, 0))
        row = ttk.Frame(f)
        row.pack(anchor="w", pady=(4, 0))
        ttk.Label(row, text="strength").pack(side="left")
        s = ttk.Scale(row, from_=1, to=10, orient="horizontal", length=140,
                      command=lambda v: ed.v_strength.set(int(float(v))))
        s.set(ed.v_strength.get())
        s.pack(side="left", padx=(4, 0))

    def _brush_toggled(self):
        if self.v_brush_on.get() and self._terrain() is None:
            self.lbl.configure(text="the heights brush needs a mod loaded")
            self.v_brush_on.set(False)
        self._draw_ring()

    def _resize(self, way):
        ed = self._terrain()
        if ed is None:
            return
        try:
            n = int(ed.v_brush.get())
        except (tk.TclError, ValueError):
            n = 4
        n = max(1, min(80, n + way * max(1, n // 6)))
        ed.v_brush.set(n)
        self.lbl.configure(text="brush size %d (heights points across - %.1f tiles)" % (n, n / 2.0))
        self._draw_ring()

    def _point(self, x, y):
        """The map point under canvas (x, y) as (world point, map_heights point px, py bottom-up), or None."""
        if not self._on() or x is None:
            return None
        W, H = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        p = self.gl.ground_at(x / W, y / H)
        if p is None:
            return None
        return p, (2.0 * p[0], (self.gl.data.rows - 1) - 2.0 * p[2])

    def _hover(self, e):
        self._mouse = None if e is None else (e.x, e.y)
        self._draw_ring()

    def _draw_ring(self):
        """The brush's circle on the ground under the mouse (its size as it works)."""
        c = self.canvas
        c.delete("ring")
        if not (self.v_brush_on.get() and self._mouse and self._on()):
            return
        got = self._point(*self._mouse)
        ed = self.app.editors.get("terrain")
        if got is None or ed is None:
            return
        import math
        import numpy as np
        try:
            n = max(1, int(ed.v_brush.get()))
        except (tk.TclError, ValueError):
            return
        (x, _, z), r = got[0], n / 4.0                   # n points across, a point half a tile
        d = self.gl.data
        ring = [(x + r * math.cos(a), 0.0, z + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 49)]
        ring = [(px, d.ground_height(px, pz), pz) for px, _, pz in ring]
        s = self.gl.to_screen(ring)
        if s is None:
            return
        W, H = c.winfo_width(), c.winfo_height()
        flat = [v for a, b in s for v in (a * W, b * H)]
        c.create_line(*flat, fill="#000000", width=3, tags="ring")
        c.create_line(*flat, fill="#ffffff", width=1, tags="ring")

    def _paint_start(self, e):
        self.canvas.focus_set()
        if not self.v_brush_on.get() or not self._on():
            return
        ed = self._terrain()
        if ed is None:
            return
        ed._stroke()                                     # one Undo step a stroke, as on the 2D map
        self._paint, self._mouse = True, (e.x, e.y)
        self._puff()

    def _paint_end(self, e):
        if self._paint:
            self._paint = False
            self._for = self._stamp()                    # the card already shows what was painted
            self._lay_models()                           # the mountains and hills laid again on the new relief
            self._sharp_later()

    def _lay_models(self):
        """The tile models placed again in a thread (a big map takes seconds), taken by the card when done."""
        gl = self.gl
        if gl is None or not gl.models_stale or getattr(self, "_laying", False):
            return
        self._laying, got = True, {}

        def work():
            try:
                gl.data.place_models()
            except Exception as e:                       # said in the bar, never a crash
                got["error"] = str(e)

        def done():
            if th.is_alive():
                self.after(200, done)
                return
            self._laying = False
            if self.gl is not gl or not self.winfo_exists():
                return
            if "error" in got:
                self.lbl.configure(text="the mountains and hills could not be laid again: %s" % got["error"])
                return
            gl.models_placed()
            self.draw()
            if gl.models_stale:                          # painted again meanwhile
                self._lay_models()
        gl.models_stale = False
        th = threading.Thread(target=work, daemon=True)
        th.start()
        self.after(200, done)

    def _puff(self):
        """One puff of the brush where the mouse is (every 0.05 s while held): the Terrain editor paints its copy
        of map_heights, the card takes the same points at once."""
        if not self._paint:
            return
        ed = self.app.editors.get("terrain")
        got = self._point(*self._mouse) if self._mouse else None
        if ed is not None and got is not None and ed.spray(*got[1]):
            self._send_heights(ed, got[1])
            self.draw(half=True)
        self.after(50, self._puff)

    def _send_heights(self, ed, at):
        """The points the brush can have changed, read from the Terrain editor's map_heights, sent to the card."""
        import numpy as np
        from . import terrain as T, terrain3d as T3
        img = ed._img("map_heights.tga")
        d = self.gl.data
        _, r, _ = T.spray_footprint(at, ed.v_brush.get())
        k = int(r) + 2
        x0, x1 = max(0, int(at[0]) - k), min(d.cols - 1, int(at[0]) + k + 1)
        y0, y1 = max(0, int(at[1]) - k), min(d.rows - 1, int(at[1]) + k + 1)
        if img is None or x1 < x0 or y1 < y0:
            return
        rgb = np.array([[img.get(x, y) for x in range(x0, x1 + 1)] for y in range(y1, y0 - 1, -1)], np.uint8)
        camp = self.app.v_campaign.get()
        if getattr(self, "_limits", None) is None or self._limits[0] != camp:
            self._limits = (camp, T.max_land_height(ed.mod, camp), T.min_sea_height(ed.mod, camp))
        metres = T3.metres_of(rgb, self._limits[1], self._limits[2])
        self.gl.set_heights((d.rows - 1) - y1, x0, metres)

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
