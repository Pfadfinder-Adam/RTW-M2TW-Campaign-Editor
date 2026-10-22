"""Maps > 3D: the campaign map in 3D, drawn by the graphics card the way the games draw it (glmap: the ground grid of
map_heights, the game's blend masks between grounds, its light, the sea sheet) - what the Terrain editor's brushes
painted and not written yet included: the map is made again whenever the tab opens after a change.

Right drag: move over the map (the land follows the mouse); the wheel held down and dragged: turn left / right and
look up / down; the wheel turned: nearer / farther; the arrow keys (or W A S D) move too (the user's own scheme,
2026-10-15); the left button carries an army, agent or fleet to another tile as on the Map (a white tile frame under the
mouse; an army in a town stands on its roofs, as in the game's own editor). While the mouse moves the view is drawn at half size,
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
        "Paint: the left button raises or lowers the land under the circle while held (Ctrl + wheel or [ ] "
        "for its size), or paints the ground, rivers and cliffs, climates, land or sea tile by tile ('brush' picks "
        "which) - the brushes of Terrain and Coast & heights, their Undo and Apply shared; what is painted shows at "
        "once. The relief stands as "
        "high as in the game; the towns, ports, resources, armies, agents and fleets stand as descr_strat.txt will have them (what the Map moved or added before the write included), with the roads and region borders. "
        "The mouse resting on an army, agent, fleet, town, port, resource or fort shows its name beside it. "
        "The left button held and moved carries an army, agent or fleet (one in a town stands on its roofs) to another "
        "tile (a click alone moves nothing): a white "
        "frame shows the tile it goes to; the same move as on the Map (Undo, Preview, Apply), refused where the game "
        "would not take it; Esc puts it back.")


# colours laid over the map to see what is painted (Layers)
TINTS = (("none", "None"), ("climates", "Climates (the sea's too)"), ("regions", "Regions"))
TINT_TIPS = {"climates": "Each tile in its climate's colour (map_climates.tga, descr_climates.txt's colours), the "
                         "sea's too: land raised there takes the climate most land round it has, unless one was "
                         "painted on that water first.",
             "regions": "Each land tile in its region's colour (map_regions.tga): the region it belongs to."}

# what Paint paints on the 3D map: the heights (by point), or one of the Terrain editor's tile brushes
PAINTS = (("heights", "Heights"), ("ground", "Ground"), ("features", "Rivers, cliffs, volcanoes..."),
          ("climate", "Climates"), ("regions", "Regions"), ("land", "Land (tiles)"), ("sea", "Sea (tiles)"))
SWATCHED = ("ground", "features", "climate")       # these paint a colour picked from the Terrain editor's palette


def tile_of(hx, hy):
    """The tile (x, y bottom-up, as descr_strat) of a map_heights point (px, py bottom-up): its middle is 2x+1, 2y+1."""
    return int(hx // 2), int(hy // 2)


class Map3DView(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._for, self._building, self._strat_for = None, False, None
        self._drag, self._sharp_job, self._photo = None, None, None
        host = app.tab_tools(app.MAP3D_TAB) if hasattr(app, "tab_tools") else None    # the tab row (#337 / #338)
        bar = ttk.Frame(host if host is not None else self, padding=(0, 0) if host is not None else (4, 4))
        if host is not None:
            bar.pack(side="left", fill="x")
        else:
            bar.pack(fill="x")
        self.v_winter = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Winter", variable=self.v_winter, command=self.rebuild).pack(side="left")
        self.gl, self.gcam, self._anim_job = None, None, None
        # Layers: each thing on the map shown or left out (the sea off shows the sea floor); the surf moving or still
        from .glmap import LAYERS
        from .gui_util import DropPanel
        self.v_show = {key: tk.BooleanVar(value=True) for key, _ in LAYERS}
        self.v_moving = tk.BooleanVar(value=True)
        self.v_tint = tk.StringVar(value="none")        # colours over the map: 'none' | 'climates' | 'regions'

        def build_layers(f):
            for key, label in LAYERS:
                ttk.Checkbutton(f, text=label, variable=self.v_show[key], command=self._layers_changed).pack(anchor="w")
            ttk.Checkbutton(f, text="The surf and the trees move", variable=self.v_moving,
                            command=self._layers_changed).pack(anchor="w")
            ttk.Separator(f).pack(fill="x", pady=4)
            ttk.Label(f, text="colours over the map:").pack(anchor="w")
            from .gui_util import tip as tip_
            for val, text in TINTS:
                tip_(ttk.Radiobutton(f, text=text, value=val, variable=self.v_tint, command=self._send_tint),
                     TINT_TIPS.get(val, "")).pack(anchor="w")
        lb = ttk.Button(bar, text="Layers \u25be")
        lb.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        self._layers_panel = DropPanel(lb, build_layers)
        # the heights brush right on the 3D map: the Terrain editor's own (its strokes, Undo and Apply shared), the
        # land changing under the circle while the button is held, not when the stroke ends
        self.v_brush_on = tk.BooleanVar(value=False)
        self.v_how = tk.StringVar(value="grab")         # 'grab': the game's (hold and move up / down); 'spray'
        # what the brush paints: the heights, or the Terrain editor's tile brushes - each with its own pick here
        self.v_paint = tk.StringVar(value="heights")
        self.v_pick = {k: tk.StringVar() for k, _ in PAINTS if k in SWATCHED}
        self._paint, self._mouse, self._ring, self._grab, self._carry = False, None, None, None, None
        from .gui_util import tip as _tip
        _tip(ttk.Checkbutton(bar, text="Paint", variable=self.v_brush_on, command=self._brush_toggled),
             "Paint right on the 3D map - 'brush' picks what: the heights, the ground, rivers / cliffs / volcanoes, "
             "the climates, or land and sea tile by tile; what is painted shows at once. Heights - grab and drag (the game's own): press the left button where the land should rise or sink and move "
             "the mouse up or down while holding it - the land under the circle goes with it, most in the middle. "
             "Spray: the left button raises (or lowers, smooths, levels) the land while held. Both work on the "
             "water too: the sea's floor raised out of the water becomes land (its tile joins a region), land "
             "lowered under it becomes water, as in the game. The same strokes, Undo and Apply as Coast & heights. "
             "Ctrl + the wheel, or [ and ], make the circle smaller or bigger; 'brush' beside it has the rest.").pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
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
        # what was made and how long a frame takes: a row under the map, as the Map's tile readout (the switches are
        # in the tab row - reports #337 / #338)
        under = ttk.Frame(self)
        under.pack(side="bottom", fill="x")
        self.lbl = ttk.Label(under, foreground=theme.palette()["muted"], anchor="w")
        self.lbl.pack(side="left", fill="x", expand=True)
        self.lbl_frame = ttk.Label(under, foreground=theme.palette()["muted"], anchor="e")
        self.lbl_frame.pack(side="right", padx=(theme.BUTTON_GAP * 2, 0))
        tip(self.lbl_frame, "Where a frame's time goes (the mean of the last 10 frames; half size while the map is "
                            "moved). Send these numbers with a report when the map lags.")
        self._clock, self._clock_said = None, 0.0
        self.canvas = tk.Canvas(self, background="#9db8cf", highlightthickness=0, takefocus=1)
        self.canvas.pack(fill="both", expand=True)
        c = self.canvas
        # the card draws straight into this frame when it can (glwindow, Windows): laid over the canvas, the
        # canvas's own mouse and keys bound to it too; no background of its own, so Tk never paints over the map
        self.glframe = tk.Frame(self, background="", takefocus=1)
        self._win, self._lines = None, []
        c.bind("<Configure>", lambda e: self.draw())
        c.bind("<ButtonPress-3>", lambda e: self._press(e, "move"))
        c.bind("<ButtonPress-2>", lambda e: self._press(e, "turn"))
        c.bind("<B3-Motion>", self._motion)
        c.bind("<B2-Motion>", self._motion)
        c.bind("<ButtonRelease-3>", self._release)
        c.bind("<ButtonRelease-2>", self._release)
        c.bind("<Motion>", self._hover)
        c.bind("<ButtonPress-1>", self._paint_start)
        c.bind("<Alt-ButtonPress-1>", self._eyedrop)
        c.bind("<B1-Motion>", self._drag_paint)
        c.bind("<ButtonRelease-1>", self._paint_end)
        c.bind("<Leave>", lambda e: self._hover(None))
        self.bind("<Unmap>", lambda e: self._tip_hide(), add="+")     # another tab: the hover's box goes too
        c.bind("<Escape>", lambda e: self._carry_stop())
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
        painted = tuple(sorted((getattr(self.app, "region_paint", None) or {}).items()))     # Edit regions'
        return (getattr(mod, "data", None), self.app.v_campaign.get(), work, self.v_winter.get(), hash(painted))

    def _strat(self):
        """(descr_strat as Apply will leave it - the Map's armies, agents, fleets, towns and resources added, moved
        or taken away and the other windows' changes kept - as a Strat, a key telling it apart) or (None, None):
        the file as it is."""
        app = self.app
        self._moved = dict(getattr(app, "place_moves", None) or {})     # towns / ports the Map moved, not written
        moved = tuple(sorted(self._moved.items())) or None
        try:
            from .plan import kept_texts
            from .strat import Strat
            plans = [p["plan"] for p in app.session_parts().values() if p.get("plan") is not None]
            if app.faction_pending():
                plans.append(app._faction_plan())
            want = os.path.normcase(os.path.abspath(app.mod.campaign_file(app.v_campaign.get(), "descr_strat.txt")))
            f = next((f for p, f in kept_texts(plans).items() if os.path.normcase(os.path.abspath(p)) == want), None)
            if f is None:
                return None, moved
            return Strat(f), (hash(f.dump()), moved)
        except Exception as e:                           # a half-made change: the file - said, else the 3D map
            if "Nothing to write" not in str(e):         # and the Map disagree unseen (a tester: an army shown back
                self.lbl.configure(text="the Map's changes are not shown here: %s" % e)    # in its town)
            return None, moved

    def load(self):
        """The tab opened: the picture made again when anything it shows changed since; when only descr_strat did
        (the Map's armies moved), only what stands on the map is laid again."""
        self._hover_gen = getattr(self, "_hover_gen", 0) + 1   # the hover's list read anew
        if self.app.mod is None:
            self.lbl.configure(text="load a mod first")
            return
        strat, key = self._strat()
        if self._stamp() != self._for:
            self.rebuild(strat, key)
            return
        if self.gl is not None and key != self._strat_for:
            try:
                self.gl.data.set_strat(self._source(), self.app.v_campaign.get(), strat, self._moved)
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
        moved = dict(getattr(self, "_moved", None) or {})
        self._building = True
        self.lbl.configure(text="laying the game's textures on the map...")
        got = {}

        def work():                                      # the arrays the card needs (no OpenGL in this thread)
            t = time.time()
            try:
                got["data"] = glmap.MapData(mod, campaign, winter=winter, strat=strat, moved=moved)
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
                self.after(100, self._lists_later)
        th = threading.Thread(target=work, daemon=True)
        th.start()
        self.after(250, done)

    def _lists_later(self):
        """The Map's lists read once the picture shows, so the first hover's names and the first carry do not wait
        for them."""
        try:
            if self.app.mod is not None and self.winfo_viewable():
                self._map_lists()
        except Exception:                                # the hover then shows nothing until the Map is read
            pass

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
        missing = getattr(data, "objects_missing", None)
        if missing:                                      # drawn white on the map: each named for a report
            try:
                from . import log
                log.write("Maps > 3D: %d model(s) / texture(s) of what stands on the map not found (drawn white or "
                          "left out): %s" % (len(missing), ", ".join(missing)))
            except Exception:
                pass
        if self.v_tint.get() != "none":
            self._send_tint(draw=False)
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

    def _window(self):
        """The card drawing straight into the window (glwindow), made once; None where it cannot (drawn as before)."""
        if self._win is None:
            self._win = False
            try:
                from . import glmap, glwindow
                win = glwindow.WindowGL(glmap.context())
                self.glframe.update_idletasks()
                if win.attach(self.glframe.winfo_id()):
                    c = self.canvas
                    for seq in c.bind():                    # the canvas's mouse and keys, the same handlers
                        self.glframe.bind(seq, c.bind(seq))
                    self.glframe.bind("<Expose>", lambda e: self._present(), add="+")    # shown again: the frame
                    self.glframe.place(in_=c, x=0, y=0, relwidth=1, relheight=1)
                    self._win = win
            except Exception:
                self._win = False
        return self._win or None

    def _window_failed(self):
        self._win = False
        self.glframe.place_forget()

    def _present(self):
        """The frame on the card shown in the window again, with the ring / tile frame over it (no new drawing)."""
        win = self._win
        if not win or self.gl is None or self.gl.fbo is None:
            return 0.0
        W, H = self.gl.fbo_size
        t = time.perf_counter()
        try:
            win.present(self.gl.fbo, W, H, self._lines)
        except Exception:                                # drawn as before from the next frame
            self._window_failed()
            self.draw()
        return time.perf_counter() - t

    def draw(self, half=False):
        if not self._on():
            return
        W, H = max(50, self.canvas.winfo_width()), max(50, self.canvas.winfo_height())
        t = (time.monotonic() * 0.2) % 1.0 if self.v_moving.get() else 0.3
        if self._window():                               # straight into the window: always the whole size
            try:
                self.gl.render(self.gcam, W, H, t, {k: v.get() for k, v in self.v_show.items()},
                               clock=time.monotonic() if self.v_moving.get() else 0.0, read=False)
            except Exception as e:                       # the card failed now: said in the bar, never a crash
                self.lbl.configure(text="the graphics card stopped drawing: %s" % e)
                self.gl.release()
                self.gl, self._for = None, None
                return
            self._lines = self._ring_lines()
            self._clocked(self._present(), (W, H))
            return
        from PIL import Image, ImageTk
        f = 2 if half else 1
        try:
            arr = self.gl.render(self.gcam, W // f, H // f, t, {k: v.get() for k, v in self.v_show.items()},
                                 clock=time.monotonic() if self.v_moving.get() else 0.0)
        except Exception as e:                           # the card failed now: said in the bar, never a crash
            self.lbl.configure(text="the graphics card stopped drawing: %s" % e)
            self.gl.release()
            self.gl, self._for = None, None
            return
        shown = time.perf_counter()
        im = Image.fromarray(arr)
        if f > 1:
            im = im.resize((W, H), Image.BILINEAR)
        self._photo = ImageTk.PhotoImage(im)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        self._draw_ring()
        self._clocked(time.perf_counter() - shown, (W // f, H // f))

    def _clocked(self, window, size):
        """The frame's parts into the line under the buttons, at most twice a second."""
        from .glmap import FrameClock
        if self._clock is None:
            self._clock = FrameClock()
        card, back = getattr(self.gl, "took", (0.0, 0.0))
        self._clock.add(card, back, window, size)
        now = time.monotonic()
        if now - self._clock_said > 0.5:
            self._clock_said = now
            self.lbl_frame.configure(text=self._clock.text())

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
        ttk.Label(f, text="paint:").pack(anchor="w")
        row = ttk.Frame(f)
        row.pack(anchor="w")
        body = ttk.Frame(f)

        def picked():
            tint = {"climate": "climates", "regions": "regions"}.get(self.v_paint.get())
            if tint and self.v_tint.get() != tint:
                self.v_tint.set(tint)                    # what is painted is seen (the climates on the sea too)
                self._send_tint()
            for w in body.winfo_children():
                w.destroy()
            self._brush_body(body, ed)
            self._draw_ring()
        for val, text in PAINTS:
            ttk.Radiobutton(row, text=text, value=val, variable=self.v_paint, command=picked).pack(side="left", padx=2)
        ttk.Separator(f).pack(fill="x", pady=4)
        body.pack(anchor="w", fill="x")
        self._brush_body(body, ed)

    def _brush_body(self, f, ed):
        """The choices of the brush picked: the heights' ways, or the palette of a tile brush (the Terrain editor's
        own list), the land brush's region and climate."""
        what = self.v_paint.get()
        if what != "heights":
            if what == "regions":
                self._map_lists()                        # the Map's regions read (its Edit regions brush)
                app = self.app
                _, _, cols = app.region_brush()
                from .regionedit import SEA
                new = [r["name"] + "  (new)" for r in getattr(app, "new_regions", [])]
                ttk.Label(f, text="paint with (Alt + click on the map picks a tile's region):").pack(anchor="w")
                ttk.Combobox(f, textvariable=app.v_paint, state="readonly", width=30,
                             values=new + sorted(c for c in cols if c != SEA) + [SEA]).pack(anchor="w")
                ttk.Label(f, text="the Map's Edit regions brush: towns and ports keep their tiles; Apply writes it",
                          foreground=theme.palette()["muted"]).pack(anchor="w")
            elif what in SWATCHED:
                var = self.v_pick[what]
                values = []
                for label, colours in ed.swatches(what):
                    ttk.Label(f, text=label + ":").pack(anchor="w")
                    box = ttk.Frame(f)
                    box.pack(anchor="w", fill="x")
                    for c, name, look in colours:
                        b = ttk.Radiobutton(box, text=name, value="%d,%d,%d" % c, variable=var, cursor="hand2",
                                            style=theme.colour_style("#%02x%02x%02x" % look, "Toolbutton"))
                        b.pack(side="left", padx=1, pady=1)
                        values.append(b.cget("value"))
                    from .gui_util import flow
                    flow(box)
                if values and var.get() not in values:
                    var.set(values[0])
                if not values:
                    ttk.Label(f, text="this mod has none to paint").pack(anchor="w")
            else:
                ttk.Label(f, text="new land joins: %s (Coast & heights > Land and sea)" %
                          ed.v_coast_region.get()).pack(anchor="w")
                ttk.Checkbutton(f, text="New land: neighbours' climate", variable=ed.v_land_climate).pack(anchor="w")
            row = ttk.Frame(f)
            row.pack(anchor="w", pady=(4, 0))
            ttk.Label(row, text="size (tiles: 1 one tile, 2 a square of 3 x 3...)").pack(side="left")
            ttk.Spinbox(row, from_=1, to=24, width=4, textvariable=ed.v_brush,
                        command=self._draw_ring).pack(side="left", padx=(4, 0))
            return
        for val, text in (("grab", "Grab and drag (the game's): press, move the mouse up / down"),
                          ("spray", "Spray: works while the button is held")):
            ttk.Radiobutton(f, text=text, value=val, variable=self.v_how).pack(anchor="w")
        ttk.Separator(f).pack(fill="x", pady=4)
        ttk.Label(f, text="the spray:").pack(anchor="w")
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
        if e is not None and self._carry is None and self.v_brush_on.get() and self.v_paint.get() != "heights" \
                and not self._paint:
            t = self._tile(e.x, e.y) if self._on() else None
            text = self._paint_tip(t) if t is not None else ""
            if text:
                self._tip_show(e, text)
            else:
                self._tip_hide()
            return
        if e is None or self._carry is not None or self.v_brush_on.get():
            self._tip_hide()
            return
        got = getattr(self, "_hover_at", None)           # what _hover_frame found under the mouse just now
        here = got[2] if got is not None and self._on() else []
        self._tip_show(e, self._tip_text(here))

    def _tip_text(self, here):
        """What the mouse rests on in a few lines, as the Map's name beside the mouse: a character's name (an army
        with no named man: its captain), what he is, of which faction, his army's units; a town's name and owner; a
        resource's name; a fort's owner."""
        from .gui_map import hover_name
        app = self.app
        mv = getattr(app, "map_view", None)
        cm = getattr(mv, "cmap", None)
        lines = []
        for what, key, name in here:
            if what == "char":
                ch = (getattr(app, "_map_chars", None) or {}).get(key) or {}
                lines.append(hover_name(ch) or name)
                lines.append("   %s of %s%s" % (ch.get("kind") or "character", ch.get("faction") or "?",
                                                ", %d unit(s)" % ch["units"] if ch.get("army") and ch.get("units")
                                                else ""))
            elif what == "place":
                kind, region = key
                info = (getattr(cm, "info", None) or {}).get(region, {}) if cm is not None else {}
                town = info.get("settlement") or region
                owner = (getattr(mv, "owners", None) or {}).get(region)
                lines.append("%s%s - %s" % (town, " (%s)" % region if town != region else "",
                                            "town" if kind == "city" else "port"))
                if owner:
                    lines.append("   owner %s" % owner)
            elif what == "res":
                r = next((r for r in app.res_shown() if r["id"] == key), None) if hasattr(app, "res_shown") else None
                if r is not None and str(key).startswith(("r", "n")):
                    from .resources import shown_name
                    try:
                        lines.append("%s (resource)" % shown_name(app.mod, r["kind"]))
                    except Exception:
                        lines.append("%s (resource)" % r["kind"])
                elif r is not None:
                    lines.append("%s%s" % (r.get("type") if r["kind"] == "landmark" and r.get("type") else r["kind"],
                                           " of %s" % r["owner"] if r.get("owner") else ""))
                else:
                    lines.append(name)
            else:
                lines.append(name)
        return "\n".join(lines)

    def _tip_show(self, e, text):
        """The words beside the mouse in a small box (the Map's look); none: the box goes. A window of its own: the
        card draws over the canvas, so nothing drawn on the canvas would show."""
        if not text:
            self._tip_hide()
            return
        tw = getattr(self, "_tipwin", None)
        try:
            if tw is None or not tw.winfo_exists():
                tw = self._tipwin = tk.Toplevel(self)
                tw.wm_overrideredirect(True)
                try:
                    tw.wm_attributes("-topmost", True)
                except tk.TclError:
                    pass
                tw.configure(background="#8a7a52")
                self._tiplbl = tk.Label(tw, justify="left", background="#2a2418", foreground="#f4ecd0",
                                        font=("", 9, "bold"), padx=4, pady=2)
                self._tiplbl.pack(padx=1, pady=1)
            if self._tiplbl.cget("text") != text:
                self._tiplbl.configure(text=text)
            x, y = e.x_root + 14, e.y_root + 20
            tw.update_idletasks()
            sw, sh = tw.winfo_screenwidth(), tw.winfo_screenheight()
            w, h = tw.winfo_reqwidth(), tw.winfo_reqheight()
            x, y = min(x, sw - w - 4), (y if y + h < sh - 4 else e.y_root - h - 14)     # kept on the screen
            tw.wm_geometry("+%d+%d" % (x, y))
            tw.deiconify()
        except tk.TclError:
            self._tipwin = None

    def _tip_hide(self):
        tw = getattr(self, "_tipwin", None)
        if tw is not None:
            try:
                tw.withdraw()
            except tk.TclError:
                self._tipwin = None

    def _tile(self, x, y):
        got = self._point(x, y)
        return None if got is None else tile_of(*got[1])

    # a town or a port is wider than its tile: its frame grows this much on every side, so it shows round the model
    # (the user: 'bigger for a town or a port, not hidden under its texture')
    TOWN_FRAME = 0.2

    def _draw_frame(self, t=None, grow=0.0):
        """The white frame of a tile lying on the ground - the tile under the mouse while a figure is carried, or the
        one given (what the mouse rests on); grow: tiles more on every side."""
        if t is None:
            t = self._tile(*self._mouse) if self._mouse else None
        if t is None:
            return
        d = self.gl.data
        x0, z0 = t[0] - grow, (d.rows - 1) // 2 - 1 - t[1] - grow
        side = 1.0 + 2 * grow
        n = 8 + int(8 * grow)
        steps = [side * i / n for i in range(n + 1)]
        edge = ([(x0 + a, z0) for a in steps] + [(x0 + side, z0 + a) for a in steps[1:]] +
                [(x0 + side - a, z0 + side) for a in steps[1:]] + [(x0, z0 + side - a) for a in steps[1:]])
        s = self.gl.to_screen([(px, d.ground_height(px, pz), pz) for px, pz in edge])
        if s is None:
            return
        return self._outline(s, 4, 2)

    def _hover_frame(self):
        """What the mouse rests on and the left button would carry: the same white tile frame (bigger round a town
        or a port), the hand cursor; nothing there: none."""
        t = self._tile(*self._mouse)
        got = getattr(self, "_hover_at", None)            # the same tile as the last move: its list again
        if got is not None and got[0] == t and got[1] == getattr(self, "_hover_gen", 0):
            here = got[2]
        else:
            here = self._things_at(t) if t is not None else []
            self._hover_at = (t, getattr(self, "_hover_gen", 0), here)
        try:
            self.canvas.configure(cursor="hand2" if here else "")
        except tk.TclError:
            pass
        if not here:
            return []
        # a town's tile (an army in it too - it stands on the roofs): the bigger frame round the town
        return self._draw_frame(t, self.TOWN_FRAME if any(o[0] == "place" for o in here) else 0.0) or []

    def _things_at(self, tile):
        """[(what, key, name)] standing on a tile, as the Map moves them: 'char' (an army before an agent), 'place'
        (('city' | 'port', region): a town, a port), 'res' (a resource, fort, watchtower or wonder: the Map's id)."""
        app = self.app
        chars = [ch for ch in (getattr(app, "_map_chars", None) or {}).values() if tuple(ch["xy"]) == tile]
        chars.sort(key=lambda ch: not ch.get("army"))
        out = [("char", ch["id"], ch["name"]) for ch in chars]
        mv = getattr(app, "map_view", None)
        cm = getattr(mv, "cmap", None)
        if cm is not None and getattr(mv, "on_place_move", None):
            places = getattr(mv, "places", None) or {}
            for what, table in (("city", cm.cities), ("port", cm.ports)):
                for region, xy in table.items():
                    if tuple(places.get((what, region), xy)) == tile:
                        out.append(("place", (what, region), "%s %s" % (region, "town" if what == "city" else "port")))
            for p in getattr(mv, "region_points", None) or []:      # a new region's town / port, not written yet
                if len(p) > 3 and tuple(p[0]) == tile and ("place", (p[1], p[3])) not in [o[:2] for o in out]:
                    out.append(("place", (p[1], p[3]), "%s %s" % (p[3], "town" if p[1] == "city" else "port")))
        if hasattr(app, "res_shown"):
            out += [("res", r["id"], r["type"] if r["kind"] == "landmark" and r.get("type") else r["kind"])
                    for r in app.res_shown() if tuple(r["xy"]) == tile]
        if mv is not None and getattr(mv, "on_special_move", None):     # special places (engine-drawn models)
            out += [("special", sp["id"], sp.get("title") or "special place") for sp in getattr(mv, "special", None) or []
                    if tuple(sp["xy"]) == tile]
        return out

    @staticmethod
    def _picks(what, key, tile):
        """pick(object) -> True for the 3D map's objects (mapobjects3d.objects) of the thing carried."""
        kinds = {"char": ("character",), "res": ("resource", "fort", "watchtower", "landmark"),
                 "special": ()}.get(what, ())
        if what == "place":
            kinds = ("town", "wall") if key[0] == "city" else ("port", "port_sea")
        return lambda o: o["kind"] in kinds and tuple(o["xy"]) == tile

    # the mouse moves this many pixels with the left button held before a figure is lifted: a click alone lifts
    # nothing (a tester: a stall at every click on a resource)
    DRAG_START = 4

    def _map_lists(self):
        """The Map's lists of what stands where and its moves, read once (the 3D map's hover and carry use them)."""
        app = self.app
        if getattr(app, "_map_moved", None) is None or getattr(getattr(app, "map_view", None), "cmap", None) is None:
            app.show_map()

    def _carry_press(self, e):
        """The left button pressed: what stands on that tile is remembered; it is lifted only once the mouse moves
        with the button held (_carry_start)."""
        tile = self._tile(e.x, e.y)
        self._pressed = None
        if tile is None:
            return
        self._map_lists()
        here = self._things_at(tile)
        if here:
            self._pressed = (e.x, e.y, here[0], tile)

    def _carry_start(self, e):
        """The left button held on anything the Map moves - an army, agent or fleet (an army in a town: on the town),
        a town, a port, a resource, a fort - and the mouse moved: it is lifted and goes with the mouse, drawn where it
        would stand, until let go (report #331: everything on the map, as on the Map; following the mouse, no wait)."""
        x0, y0, (what, key, name), tile = self._pressed
        self._pressed = None
        self._carry, self._mouse = (what, key, name, tile), (e.x, e.y)
        self.gl.ghost_shift = (0.0, 0.0, 0.0)
        if self.gl.data.lift_out(self._picks(what, key, tile)):
            self.gl._objects()                           # only what stands on the map: the ground stays as it is
        self.lbl.configure(text="%s: let go on the tile where it goes (Esc: it stays)" % name)
        self._draw_ring()

    def _carry_follow(self, e):
        """The carried thing drawn on the tile under the mouse, standing on its ground - at once, every move."""
        self._mouse = (e.x, e.y)
        t = self._tile(e.x, e.y)
        if t is not None and self._carry is not None:
            d = self.gl.data
            fx, fy = self._carry[3]
            H = (d.rows - 1) // 2
            dy = d.ground_height(t[0] + 0.5, H - t[1] - 0.5) - d.ground_height(fx + 0.5, H - fy - 0.5)
            self.gl.ghost_shift = (float(t[0] - fx), dy, float(fy - t[1]))
        if getattr(self, "_follow_job", None) is None:  # drawn once the window is free: the newest place only
            self._follow_job = self.after_idle(self._follow_draw)

    def _follow_draw(self):
        self._follow_job = None
        if self._carry is not None:
            self.draw(half=True)
            self._draw_ring()

    def _carry_stop(self, back=True):
        if self._carry is not None:
            self._carry = None
            self.lbl.configure(text="")
            if back and self.gl is not None:
                self.gl.ghost_shift = (0.0, 0.0, 0.0)
                self.gl.data.put_back()
                self.gl._objects()
                self.draw()
            self._draw_ring()

    def _carry_end(self, e):
        """Let go: it moves there as the Map moves it (its check, Undo, Apply) and the 3D map lays it there; a tile the
        game would not take is said and it goes back."""
        app, carried, tile = self.app, self._carry, self._tile(e.x, e.y)
        if carried is None:
            return
        what, key, name, start = carried
        if tile is None or tile == start:
            self._carry_stop()
            return
        mv = getattr(app, "map_view", None)
        if what == "char":
            why = app._map_check(key, tile)
        elif what == "place":
            why = mv.check_place(key[0], key[1], tile) if getattr(mv, "check_place", None) else None
        elif what == "special":
            why = mv._outside(tile) if hasattr(mv, "_outside") else None
        else:
            why = app.res_check(key, tile)
        if why:
            self._carry_stop()
            app.status.set("%s cannot stand at %d, %d: %s" % (name, tile[0], tile[1], why))
            return
        self._carry_stop(back=False)
        self._did("app")                                 # the Map's move: the window's own Undo takes it back
        self._hover_gen = getattr(self, "_hover_gen", 0) + 1   # what stands where has changed
        if what == "char":
            app._map_moved(key, tile)
        elif what == "place":
            mv.on_place_move(key[0], key[1], tile)
        elif what == "special":
            mv.on_special_move(key, tile)
        else:
            app.res_moved(key, tile)
        # an army, agent, fleet or resource: only it is laid again where it was let go - the whole map is not (a
        # tester: a short stall at every let go); a town or port pulls its roads along: laid again as before
        if what in ("char", "res") and getattr(self, "gl", None) is not None and self.gl.data.put_down(tile):
            self.gl.ghost_shift = (0.0, 0.0, 0.0)
            self.gl._objects()
            self._strat_for = self._strat()[1]           # in step with the Map's change: load() lays nothing again
            self.draw()
            return
        self.load()

    def _outline(self, s, wide, thin):
        """Screen fractions -> a white line with a black edge: [(points in pixels, width, rgba)]."""
        c = self.canvas
        W, H = c.winfo_width(), c.winfo_height()
        pts = [(a * W, b * H) for a, b in s]
        return [(pts, wide, (0.0, 0.0, 0.0, 1.0)), (pts, thin, (1.0, 1.0, 1.0, 1.0))]

    def _draw_ring(self):
        """The brush's circle on the ground under the mouse (its size as it works); the tile frame while a figure is
        carried - on the card when it draws straight into the window, else on the canvas."""
        lines = self._ring_lines()
        if self._win:
            self._lines = lines
            self._present()
            return
        c = self.canvas
        c.delete("ring")
        for pts, width, rgba in lines:
            c.create_line(*[v for p in pts for v in p], width=width, tags="ring",
                          fill="#%02x%02x%02x" % tuple(int(v * 255) for v in rgba[:3]))

    def _ring_lines(self):
        if self._carry is not None and self._mouse and self._on():
            return self._draw_frame(grow=self.TOWN_FRAME if self._carry[0] == "place" else 0.0) or []
        if not self.v_brush_on.get() and self._mouse and self._on():
            return self._hover_frame()
        if not (self.v_brush_on.get() and self._mouse and self._on()):
            return []
        got = self._point(*self._mouse)
        ed = self.app.editors.get("terrain")
        if got is None or ed is None:
            return []
        if self.v_paint.get() != "heights":              # the tile brush: the square of tiles it paints
            return self._draw_frame(tile_of(*got[1]), grow=self._tiles_brush(ed) - 1) or []
        import math
        import numpy as np
        try:
            n = max(1, int(ed.v_brush.get()))
        except (tk.TclError, ValueError):
            return []
        (x, _, z), r = got[0], n / 4.0                   # n points across, a point half a tile
        d = self.gl.data
        ring = [(x + r * math.cos(a), 0.0, z + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 49)]
        ring = [(px, d.ground_height(px, pz), pz) for px, _, pz in ring]
        s = self.gl.to_screen(ring)
        return [] if s is None else self._outline(s, 4, 2)      # the white wide enough to show on sand (the tester)

    def _paint_start(self, e):
        self.canvas.focus_set()
        self._tip_hide()
        if not self._on():
            return
        if not self.v_brush_on.get():
            self._carry_press(e)
            return
        ed = self._terrain()
        if ed is None:
            return
        if self.v_paint.get() == "regions":              # the Map's own Undo (region_paint is one of its steps)
            self.app.remember()
            self._did("app")
        else:
            ed._stroke()                                 # one Undo step a stroke, as on the 2D map
            self._did("terrain")
        self._paint, self._mouse = True, (e.x, e.y)
        self.gl.coast_frozen = True                      # the whole shore is not traced at every tick, only at the end
        self._coast_was = self._coast_now(ed)
        if self.v_paint.get() != "heights":              # a tile brush: the tiles under it now, then as it moves
            self._last_tile = None
            if self.v_paint.get() == "regions":          # the Map's Edit regions brush, made once a stroke
                self._map_lists()
                self._regions = self.app.region_brush()[0] if getattr(self.app, "_cmap", None) is not None else None
            self._tiles_tick()
            return
        if self.v_how.get() == "grab":                   # the game's: the land under the circle held, then moved
            got = self._point(e.x, e.y)
            self._grab = (e.y, got[1]) if got is not None and ed.grab(*got[1]) else None
            return
        self._puff()

    def _drag_paint(self, e):
        """The mouse moved with the left button held: the grabbed land goes up or down with it (the higher the mouse,
        the higher the land - as smooth as the mouse), else the spray follows the mouse; a carried figure's frame too."""
        if self._paint and self.v_paint.get() != "heights":
            self._mouse = (e.x, e.y)                     # the newest place only: done when the window is free
            if getattr(self, "_tiles_job", None) is None:
                self._tiles_job = self.after_idle(self._tiles_tick)
            return
        if self._paint and self._grab is not None:
            self._grab_y = e.y                           # the newest place only: done when the window is free
            if getattr(self, "_grab_job", None) is None:
                self._grab_job = self.after_idle(self._grab_tick)
            return
        pressed = getattr(self, "_pressed", None)
        if pressed is not None and max(abs(e.x - pressed[0]), abs(e.y - pressed[1])) >= self.DRAG_START:
            self._tip_hide()
            self._carry_start(e)
        if self._carry is not None:
            self._carry_follow(e)
            return
        self._hover(e)

    def _grab_tick(self):
        """The grabbed land moved to where the mouse is now (report #331: the land follows the mouse, no queue of
        old moves to catch up on)."""
        self._grab_job = None
        if not (self._paint and self._grab is not None):
            return
        ed = self.app.editors.get("terrain")
        sc = ed._shape_coast() if ed is not None else None
        if sc is None:
            return
        y0, at = self._grab
        try:
            k = max(1, min(10, ed.v_strength.get())) / 5.0
        except tk.TclError:
            k = 1.0
        if ed.pull((y0 - self._grab_y) * 0.3 * k * sc.grey):        # a third of a grey step a pixel at strength 5
            self._send_heights(ed, at)
            self.draw(half=True)

    def _paint_end(self, e):
        self._pressed = None                             # a click alone: nothing lifted, nothing laid again
        if self._carry is not None:
            self._carry_end(e)
            return
        if self._paint:
            self._paint, self._grab = False, None
            if self.gl is not None:
                self.gl.coast_frozen = False             # the shore traced again at the next frame
            ed = self.app.editors.get("terrain")
            if self.v_paint.get() != "heights" or \
                    ed is not None and self._coast_now(ed) != getattr(self, "_coast_was", None):
                # land out of the water (or under it): its ground and climate were shown while painting; what the
                # mountains, trees and borders stand on read again in the thread - the map not made again (the
                # user, 2026-10-22: a lag at the stroke's end, then the new land's texture popping in)
                self._ground_stale = True
                if self.gl is not None:
                    self.gl.models_stale = True
            self._for = self._stamp()                    # the card already shows what was painted
            self._lay_models()                           # the mountains and hills laid again on the new relief
            self._sharp_later()

    @staticmethod
    def _coast_now(ed):
        """What a stroke can change beyond the heights: the ground and region points the coast moved."""
        cpx = getattr(ed, "cpx", {}) or {}
        return (tuple(sorted((cpx.get("ground") or {}).items())), tuple(sorted((cpx.get("regions") or {}).items())))

    def _lay_models(self):
        """The tile models placed again in a thread (a big map takes seconds), taken by the card when done."""
        gl = self.gl
        if gl is None or not gl.models_stale or getattr(self, "_laying", False):
            return
        self._laying, got = True, {}
        ground, self._ground_stale = getattr(self, "_ground_stale", False), False
        mod, camp = self._source(), self.app.v_campaign.get()
        painted = dict(getattr(self.app, "region_paint", None) or {})

        def work():
            try:
                if ground:
                    got["layers"] = gl.data.refresh_ground(mod, camp, painted)
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
            if "layers" in got:
                gl.set_layers(0, 0, got["layers"])
                gl.coast_dirty = True                    # rivers and cliffs painted: the shore's strips leave them
            gl.models_placed()
            self.draw()
            if gl.models_stale or getattr(self, "_ground_stale", False):     # painted again meanwhile
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
        if ed is not None and got is not None and ed.heights_puff(*got[1]):
            self._send_heights(ed, got[1])
            self.draw(half=True)
        self.after(50, self._puff)

    def _did(self, kind):
        """A step done here, for Ctrl+Z / Ctrl+Y on this tab: 'terrain' (the Terrain editor's stroke) or 'app' (the
        window's own Undo: regions painted, a figure carried)."""
        self._kinds = getattr(self, "_kinds", [])[-299:] + [kind]
        self._kinds_redo = []

    def undo_step(self, redo=False):
        """Ctrl+Z / Ctrl+Y (or the bottom Undo / Redo) on the 3D tab: the newest step done here taken back (or done
        again) where it was kept - True when done here, False: the window's own Undo does it (then the map follows)."""
        back, fwd = (getattr(self, "_kinds_redo", []), getattr(self, "_kinds", [])) if redo else \
            (getattr(self, "_kinds", []), getattr(self, "_kinds_redo", []))
        if not back:
            self.after_idle(self._after_undo)
            return False
        kind = back.pop()
        fwd.append(kind)
        ed = self.app.editors.get("terrain")
        if kind == "terrain" and ed is not None:
            (ed.redo_stroke if redo else ed.undo_stroke)()
            self.after_idle(self.load)                   # the strokes' pictures back: the map made from them
            return True
        self.after_idle(self._after_undo)
        return False

    def _after_undo(self):
        """The window's Undo / Redo took back regions painted or a figure carried: the borders and colours over the
        map follow, what stands on the map is laid again - the map itself not made again."""
        if self.gl is None or not self.winfo_exists():
            return
        self._ground_stale, self.gl.models_stale = True, True
        self._for = self._stamp()
        self._lay_models()
        if self.v_tint.get() != "none":
            self._send_tint(draw=False)
        self.load()

    def _paint_tip(self, t):
        """What a tile is, beside the mouse while a tile brush is in hand: its ground, climate and region (as the
        brushes left them, not written yet)."""
        from . import terrain as T
        ed = self.app.editors.get("terrain")
        cm = getattr(ed, "cmap", None)
        if cm is None or not (0 <= t[0] < cm.w and 0 <= t[1] < cm.h):
            return ""
        got = getattr(self, "_climate_names", None)
        if got is None or got[0] is not ed.mod:          # read once a mod, not at every move
            self._climate_names = (ed.mod, {tuple(c): n for n, c, _ in T.climates(ed.mod)} if ed.mod else {})
        climates = self._climate_names[1]
        g, c = cm.ground_at(*t), cm.climate_at(*t)
        region = (getattr(self.app, "region_paint", None) or {}).get(tuple(t)) or cm.region_at(*t)
        lines = ["tile %d, %d" % tuple(t), "ground: %s" % T.GROUND.get(g, "?" if g is None else "%d %d %d" % g[:3])]
        if c is not None:
            lines.append("climate: %s" % climates.get(tuple(c[:3]), "%d %d %d" % tuple(c[:3])))
        lines.append("region: %s" % (region or "the sea"))
        return "\n".join(lines)

    def _eyedrop(self, e):
        """Alt + click: the brush picks the tile's own - its region (Regions), ground, mark or climate."""
        self.canvas.focus_set()
        what = self.v_paint.get()
        t = self._tile(e.x, e.y) if self._on() else None
        if t is None or not self.v_brush_on.get():
            return
        if what == "regions":
            self._map_lists()
            if getattr(self.app, "_cmap", None) is not None:
                self.app.region_brush()[1](t)
                self.lbl.configure(text="painting with %s" % self.app.v_paint.get())
        elif what in SWATCHED:
            ed = self._terrain()
            c = ed._current(what, t) if ed is not None else None
            if c is not None:
                self.v_pick[what].set("%d,%d,%d" % tuple(c[:3]))
                self.lbl.configure(text="picked %d,%d,%d" % tuple(c[:3]))

    @staticmethod
    def _tiles_brush(ed):
        """The tile brush's size: 1 one tile, n a square of 2n - 1 tiles across (as on the 2D map)."""
        try:
            return max(1, min(24, int(ed.v_brush.get())))
        except (tk.TclError, ValueError):
            return 1

    def _tiles_tick(self):
        """The tile brush where the mouse is now: the Terrain editor paints the tiles (its Undo, Preview and Apply),
        the card takes their points' heights, ground and climate at once."""
        self._tiles_job = None
        ed = self.app.editors.get("terrain")
        got = self._point(*self._mouse) if self._paint and self._mouse and ed is not None else None
        if got is None:
            return
        t = tile_of(*got[1])
        if t == getattr(self, "_last_tile", None):
            return
        self._last_tile = t
        b = self._tiles_brush(ed) - 1
        tiles = [(t[0] + dx, t[1] + dy) for dx in range(-b, b + 1) for dy in range(-b, b + 1)]
        what = self.v_paint.get()
        if what == "regions":
            paint = getattr(self, "_regions", None)
            took = paint(tiles) if paint is not None else []
            if took:
                self._send_tint(draw=False)
                self.draw(half=True)
            return
        if what in ("land", "sea"):
            took = ed.paint_coast(tiles, mode=what)
        else:
            pick = self.v_pick[what].get()
            if not pick:
                self.lbl.configure(text="pick what to paint in 'brush'")
                return
            took = ed.paint(tiles, what=what, colour=tuple(int(v) for v in pick.split(",")))
        if took:
            xs, ys = [x for (x, _), _ in took], [y for (_, y), _ in took]
            # a turned tile (land / sea, or a sea ground on land) changes the shore round it too: a tile more round
            k = 1
            self._send_points(ed, 2 * (min(xs) - k), 2 * (max(xs) + k) + 2, 2 * (min(ys) - k), 2 * (max(ys) + k) + 2)
            self.draw(half=True)

    def _send_heights(self, ed, at):
        """The points the brush can have changed, read from the Terrain editor's map_heights, sent to the card."""
        from . import terrain as T
        _, r, _ = T.spray_footprint(at, ed.v_brush.get())
        k = int(r) + 2
        self._send_points(ed, int(at[0]) - k, int(at[0]) + k + 1, int(at[1]) - k, int(at[1]) + k + 1)

    def _send_points(self, ed, x0, x1, y0, y1):
        """The map_heights points x0..x1, y0..y1 (bottom-up) as the Terrain editor holds them now - their heights,
        ground and climate - sent to the card."""
        import numpy as np
        from . import terrain as T, terrain3d as T3
        img = ed._img("map_heights.tga")
        d = self.gl.data
        x0, x1, y0, y1 = max(0, x0), min(d.cols - 1, x1), max(0, y0), min(d.rows - 1, y1)
        if img is None or x1 < x0 or y1 < y0:
            return
        sc = ed._shape_coast()
        if sc is not None:                               # the heights as the game reads them: exact, no 29 m steps
            metres = np.array([[sc.metres(x, y) or 0.0 for x in range(x0, x1 + 1)] for y in range(y1, y0 - 1, -1)],
                              np.float32)
        else:
            rgb = np.array([[img.get(x, y) for x in range(x0, x1 + 1)] for y in range(y1, y0 - 1, -1)], np.uint8)
            camp = self.app.v_campaign.get()
            if getattr(self, "_limits", None) is None or self._limits[0] != camp:
                self._limits = (camp, T.max_land_height(ed.mod, camp), T.min_sea_height(ed.mod, camp))
            metres = T3.metres_of(rgb, self._limits[1], self._limits[2])
        self.gl.set_heights((d.rows - 1) - y1, x0, metres)
        # the same points' ground and climate as the brush leaves them (land out of the water takes its
        # neighbours' ground and climate): shown at once, never popping in after the stroke
        pics = [ed._img(n) for n in ("map_ground_types.tga", "map_climates.tga")]
        blocks = [None if p is None or (p.width, p.height) != (d.cols, d.rows) else
                  np.frombuffer(p.raw, np.uint8).reshape(p.height, p.width, 3)[y0:y1 + 1, x0:x1 + 1][::-1]
                  for p in pics]
        self.gl.set_layers((d.rows - 1) - y1, x0, d.layers_of(blocks[0], blocks[1], metres <= 0))
        if self.v_tint.get() != "none":
            self._send_tint(draw=False)

    def _send_tint(self, draw=True):
        """The colours over the map (Layers: climates, regions, none) from the pictures as the brushes leave them,
        to the card."""
        if self.gl is None:
            return
        import numpy as np
        from . import terrain3d as T3
        kind, mod, camp = self.v_tint.get(), self._source(), self.app.v_campaign.get()
        rgba = None
        try:
            if kind == "climates":
                rgba = self.gl.data.tint_of(kind, climate=T3._picture(mod, camp, "map_climates.tga"))
            elif kind == "regions":
                img = mod.region_map(camp)
                regions = np.frombuffer(bytes(img.raw), np.uint8).reshape(img.height, img.width, 3)[::-1].copy()
                painted = getattr(self.app, "region_paint", None) or {}
                if painted:                              # the Map's Edit regions, not written yet: as Apply leaves it
                    cols = self.app._region_colours()
                    for (x, y), name in painted.items():
                        if name in cols and 0 <= y < img.height and 0 <= x < img.width:
                            regions[img.height - 1 - y, x] = cols[name]
                rgba = self.gl.data.tint_of(kind, regions=regions)
        except Exception as e:                           # said in the bar, the map still drawn
            self.lbl.configure(text="the colours over the map cannot be shown: %s" % e)
        self.gl.set_tint(rgba)
        if draw:
            self.draw()

    # ---- the mouse and keys ----
    def _press(self, e, how):
        self.canvas.focus_set()
        self._tip_hide()
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
