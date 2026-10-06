"""The Map tab: the campaign map as a full-window minimap - a
terrain picture, the political colours over it on demand, cities and ports.
Wheel zooms at the mouse, dragging pans, clicking a city picks it."""

import math
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from . import theme
from .mapdata import REBELS

FORT_W = 0.45          # a fort's / watchtower's half size, of a tile: the sign stays inside its tile
ZOOMS = (1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)       # screen pixels per tile
# the map's zoom settings (Tools > Settings > Campaign map): the wheel's step and Ctrl + wheel's in per cent of the
# shown zoom, and the zoom from which armies, agents, fleets and ports are drawn (towns always)
ZOOM_SETTINGS = {"map_zoom_step": 50, "map_zoom_step_fine": 10, "map_signs_from": 300}


def zoom_setting(key):
    from . import settings
    try:
        v = float(settings.get(key) or ZOOM_SETTINGS[key])
    except (TypeError, ValueError):
        v = ZOOM_SETTINGS[key]
    return v if v > 0 else ZOOM_SETTINGS[key]
MODES = (("political", "Political (the owners)"), ("diplomacy", "Diplomacy (towards the faction)"),
         ("religion", "Religion (Medieval II)"), ("none", "None (the ground only)"))



def view_of(base, box, size, resample, field=(0, 0, 0)):
    """The part of base (2 px per tile) under the view box (in tiles) drawn at size: only the pixels on the
    map are taken (a view far wider than a big map once asked Pillow for a 1.3-billion-pixel crop), the rest
    is the empty field around the map (the map is a free canvas), with a thin line along the map's edge."""
    from PIL import ImageDraw
    x0, y0, x1, y1 = (v * 2 for v in box)
    w, h = size
    out = Image.new(base.mode, size, field if base.mode == "RGB" else None)
    sx, sy = w / max(x1 - x0, 1e-9), h / max(y1 - y0, 1e-9)
    cx0, cy0 = max(0, int(x0)), max(0, int(y0))
    cx1, cy1 = min(base.width, int(round(x1))), min(base.height, int(round(y1)))
    if cx1 <= cx0 or cy1 <= cy0:
        return out
    dx0, dy0 = int(round((cx0 - x0) * sx)), int(round((cy0 - y0) * sy))
    dx1, dy1 = int(round((cx1 - x0) * sx)), int(round((cy1 - y0) * sy))
    if dx1 > dx0 and dy1 > dy0:
        out.paste(base.resize((dx1 - dx0, dy1 - dy0), resample, box=(cx0, cy0, cx1, cy1)), (dx0, dy0))
        if base.mode == "RGB":                       # the map's edge, where it shows
            ex0, ey0 = (-x0) * sx - 1, (-y0) * sy - 1
            ex1, ey1 = (base.width - x0) * sx, (base.height - y0) * sy
            ImageDraw.Draw(out).rectangle((ex0, ey0, ex1, ey1), outline=(120, 124, 132))
    return out


# what the box selects, and whether each is ticked at first
SELECT_KINDS = (("towns", True), ("armies", True), ("agents", True), ("fleets", True), ("resources", False),
                ("forts", False))


class MapView(ttk.Frame):
    def __init__(self, master, status=None, on_layers=None):
        super().__init__(master)
        self.on_layers = on_layers                      # the window redraws when a layer that needs it changes
        self.cmap = None
        self.owners, self.colours, self.faction, self.chosen = {}, {}, None, set()
        self.labels = {}
        self.on_city = None
        self.status = status
        bar = ttk.Frame(self, padding=(0, 0, 0, 4))
        bar.pack(fill="x")
        # the switches wrap onto a second row when the window is narrow (the zoom buttons stay on the right)
        lbar = ttk.Frame(bar)
        lbar.pack(side="left", fill="x", expand=True)
        # the layers, in one menu: what is drawn on the map
        self.v_pol = tk.BooleanVar(value=True)
        self.v_borders = tk.BooleanVar(value=True)
        self.v_names = tk.BooleanVar(value=True)
        self.v_ports = tk.BooleanVar(value=True)
        self.v_chars = tk.BooleanVar(value=True)
        self.v_res = tk.BooleanVar(value=False)
        # forts, watchtowers and wonders: always picked, moved (right drag) and deleted (right click) on the Map; new
        # ones come from the legend (fort, watchtower) or the right click (a wonder) - no mode of their own (the user)
        self.v_forts = tk.BooleanVar(value=True)
        self.v_dip = tk.BooleanVar(value=False)
        self.v_rel = tk.BooleanVar(value=False)         # religion colours (Medieval II)
        self.v_regions = tk.BooleanVar(value=False)
        # the land's colours: one mode at a time (they would hide each other): political / diplomacy / religion
        self.v_mode = tk.StringVar(value="political")
        self.tint, self.tint_legend, self._religion_ok = None, [], False
        # the legend is a palette too: a click on a sign picks it as a tool (the next click on the map makes one);
        # tools {key: True} the window offers, tool = the picked one, on_tool(key or None) tells the window
        self.tools, self.tool, self.on_tool, self.res_types = {}, None, None, []
        # how the ground is drawn (kept between starts): relief, rivers, the tile grid up close. The ground itself is
        # always one colour per tile - what the game and every brush work with (the blurred 'detailed picture' of
        # older versions hid where a tile ends; an older settings file's "ground" is not read)
        from . import settings
        look = settings.get("map_look") or {}
        self.v_relief = tk.BooleanVar(value=bool(look.get("relief", True)))
        self.v_rivers = tk.BooleanVar(value=bool(look.get("rivers", True)))
        self.v_grid = tk.BooleanVar(value=bool(look.get("grid", True)))

        def look_changed():
            settings.put("map_look", {"relief": self.v_relief.get(),
                                      "rivers": self.v_rivers.get(), "grid": self.v_grid.get()})
            self.render()
        relayer = lambda: self.on_layers() if self.on_layers else self.render()
        lb = ttk.Menubutton(lbar, text="Layers")
        lm = tk.Menu(lb, tearoff=False)
        self._relayer = relayer
        for key, label in MODES:
            lm.add_radiobutton(label="Colours: " + label, variable=self.v_mode, value=key,
                               command=self._mode_changed)
        self._menu = lm
        lm.add_separator()

        def stay(cmd):
            """A tick in Layers keeps the menu open (it closed after each one): done, the menu is shown again
            where it was, below its button."""
            def run():
                cmd()

                def again():
                    try:
                        if lb.winfo_ismapped():
                            lm.post(lb.winfo_rootx(), lb.winfo_rooty() + lb.winfo_height())
                    except tk.TclError:
                        pass
                lb.after(30, again)
            return run
        for label, var, cmd in (("Borders", self.v_borders, relayer),
                                ("Town names", self.v_names, self.render), ("Ports", self.v_ports, self.render),
                                ("Characters", self.v_chars, self.render), ("Resources", self.v_res, relayer)):
            lm.add_checkbutton(label=label, variable=var, command=stay(cmd))
        lm.add_separator()
        for label, var in (("Relief (map_heights)", self.v_relief),
                           ("Rivers, fords, cliffs (map_features)", self.v_rivers),
                           ("Tile grid when zoomed in", self.v_grid)):
            lm.add_checkbutton(label=label, variable=var, command=stay(look_changed))
        lb["menu"] = lm
        lb.pack(side="left")
        # the colour mode, in sight on the bar (also in Layers)
        ttk.Label(lbar, text="Colours").pack(side="left", padx=(10, 2))
        self.cb_mode = ttk.Combobox(lbar, state="readonly", width=19)
        self.cb_mode.pack(side="left")
        self.cb_mode.bind("<<ComboboxSelected>>", lambda e: self._mode_picked())
        self._fill_modes()
        # the two modes that change what a click does, as switches of their own
        ttk.Checkbutton(lbar, text="Edit regions", variable=self.v_regions,
                        command=self._regions_toggled).pack(side="left", padx=(12, 4))
        # resources: no switch of their own on the bar - Layers > Resources shows them (and then they are dragged,
        # deleted by a right click; new ones come from the legend on the right)
        # Select (as in a strategy game): drag a box with the left button - everything of the ticked kinds inside is
        # added to the selection (Shift takes away), a click adds one thing (Shift + click takes it away), a right click acts on them all; the
        # right button drags the map meanwhile. Towns picked show yellow on the ground alone.
        self.v_pick = tk.BooleanVar(value=False)
        self.picked, self.on_pick_menu, self._before_pick = set(), None, None
        self.sel_chars, self.sel_res, self._box = set(), set(), None
        self.v_sel = {k: tk.BooleanVar(value=on) for k, on in SELECT_KINDS}
        from .gui_util import tip
        tip(ttk.Checkbutton(lbar, text="Select", variable=self.v_pick, command=self._pick_toggled),
            "Select things on the map, as in a strategy game: drag a box with the left button - everything of the "
            "kinds ticked in 'what...' inside it is added to the selection (hold Shift to take it away instead); "
            "a click adds one (Shift + click takes it away), a click on nothing clears it all; a right click acts on "
            "them all (a building, garrisons or another owner for the towns, "
            "the characters or resources taken off the map). The right button drags the map meanwhile.").pack(
            side="left", padx=(4, 0))
        mb = ttk.Menubutton(lbar, text="what...")
        menu = tk.Menu(mb, tearoff=0)
        for k, _ in SELECT_KINDS:
            menu.add_checkbutton(label=k, variable=self.v_sel[k], command=self._sel_kinds_changed)
        mb["menu"] = menu
        mb.pack(side="left", padx=(2, 4))
        self.lbl_layers = ttk.Label(lbar, text="", foreground="#666")
        self.lbl_layers.pack(side="left", padx=8)
        for v in (self.v_pol, self.v_borders, self.v_names, self.v_ports, self.v_chars, self.v_res, self.v_dip,
                  self.v_regions, self.v_mode):
            v.trace_add("write", lambda *a: self._layers_label())
        self._layers_label()
        ttk.Button(bar, text="Fit", command=self.fit).pack(side="right")
        ttk.Button(bar, text="+", command=lambda: self.zoom_by(1, by=50)).pack(side="right", padx=2)
        b = ttk.Button(bar, text="-", command=lambda: self.zoom_by(-1, by=50))
        b.pack(side="right")
        # the zoom as a browser shows it: 100% = the whole map in the window (Fit) (report #127)
        self.lbl_zoom = ttk.Label(bar, text="", width=6, anchor="e")
        self.lbl_zoom.pack(side="right", padx=(0, 4))
        from .gui_util import first
        first(b, self.lbl_zoom, *bar.pack_slaves()[-4:-2][::-1])  # the zoom buttons keep their room
        from .gui_util import hint
        hint(bar, "Wheel: zoom (100% = the whole map in the window, as Fit).   Right drag: move the map.   Left drag: "
                  "move markers (characters, towns, ports).   Click a town: take / give it.   Right click: what can "
                  "be done there.").pack(side="right", padx=4)
        from . import settings
        self.v_legend = tk.BooleanVar(value=bool(settings.get("map_legend", True)))
        ttk.Checkbutton(lbar, text="Legend", variable=self.v_legend, command=self._legend_toggled).pack(
            side="left", padx=(4, 0), before=self.lbl_layers)
        # Find: a town, port, army, agent, fleet, unit, fort or resource by any part of its name
        self.v_find = tk.StringVar()
        ttk.Label(lbar, text="Find:").pack(side="left", padx=(12, 2), before=self.lbl_layers)
        self.find_entry = ttk.Entry(lbar, textvariable=self.v_find, width=22)
        self.find_entry.pack(side="left", before=self.lbl_layers)
        self.find_entry.bind("<KeyRelease>", self._find_typed)
        self.find_entry.bind("<Return>", lambda e: self._find_go(0))
        self.find_entry.bind("<Down>", lambda e: self._find_focus())
        self.find_entry.bind("<Escape>", lambda e: self._find_close())
        from .gui_util import flow
        flow(lbar)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self._body = body
        self.find_list = tk.Listbox(body, height=12, width=90, activestyle="dotbox", exportselection=False)
        self.find_list.bind("<Return>", lambda e: self._find_go(None))
        self.find_list.bind("<Double-Button-1>", lambda e: self._find_go(None))
        self.find_list.bind("<ButtonRelease-1>", lambda e: self._find_go(None))
        self.find_list.bind("<Escape>", lambda e: self._find_close())
        self._found = []
        self.canvas = tk.Canvas(body, background="#1d2b3a", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(side="left", fill="both", expand=True)
        # the legend: what every sign means, on the right; shown or hidden as last time
        self.legend = ttk.Frame(body, padding=(6, 0, 0, 0))
        self.legend_canvas = tk.Canvas(self.legend, width=250, background="#f4f1ea", highlightthickness=1,
                                       highlightbackground="#bbb")
        lsb = ttk.Scrollbar(self.legend, orient="vertical", command=self.legend_canvas.yview)
        self.legend_canvas.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right", fill="y")
        self.legend_canvas.pack(side="left", fill="y", expand=True)
        for seq, step in (("<MouseWheel>", None), ("<Button-4>", -1), ("<Button-5>", 1)):
            self.legend_canvas.bind(seq, lambda e, st=step: self.legend_canvas.yview_scroll(
                st if st is not None else int(-e.delta / 120), "units"))
        lc = self.legend_canvas
        lc.tag_bind("tool", "<Button-1>", self._tool_click)
        lc.tag_bind("tool", "<Enter>", lambda e: lc.configure(cursor="hand2"))
        lc.tag_bind("tool", "<Leave>", lambda e: lc.configure(cursor=""))
        if self.v_legend.get():
            self.legend.pack(side="right", fill="y")
        row = ttk.Frame(self)                            # under the map: its size (fixed, left), then the tile read
        row.pack(fill="x")
        self.size_label = ttk.Label(row, text="", anchor="w", font=("", 9, "bold"))
        self.size_label.pack(side="left", padx=(0, 4))
        self.on_resize = None                            # () -> the Map size window (tiles added / cut at the edges)
        self.b_resize = ttk.Button(row, text="Change size...", command=lambda: self.on_resize and self.on_resize())
        self.b_resize.pack(side="left", padx=(0, 4))
        ttk.Button(row, text="Save picture...", command=self.save_picture).pack(side="left", padx=(0, 12))
        self.readout = ttk.Label(row, text="", anchor="w")
        self.readout.pack(side="left", fill="x", expand=True)
        self.z, self.ox, self.oy = 2, 0.0, 0.0           # zoom; top-left corner in top-down tile units
        self._photo = None
        self._pending = None
        self._drag = None
        self._cdrag = None
        self._pdrag = None               # a town or port being dragged
        # the Regions mode: left drag paints tiles to a region, right click picks one
        self.region_mode, self.paint_overlay, self.region_points = False, {}, []
        self.region_painted, self.region_colours = {}, {}
        self.on_paint = self.on_pick = None
        self.on_menu = None              # (tile, town region or None, character id or None) -> [(label, fn)]
        self._menu_press = None
        self.brush, self._painting, self._rclick = 1, False, False
        # a spray brush (the Terrain editor's heights): on_spray(px, py) is called again and again while the
        # left button is held - the longer, the more it does; px, py = map_heights pixels (bottom-up, fractions)
        self.on_spray, self._spray = None, None
        self.chars, self.draggable, self.symbols = [], set(), {}
        self.on_char_move = self.check_tile = None
        # resources: [{id, kind, xy}]; check_res(id, xy) -> None or why; on_res_move(id, xy); on_res_click(id)
        self.resources, self.check_res, self.on_res_move, self.on_res_click = [], None, None, None
        self.res_sel, self._rdrag, self._rpress = None, None, None
        self.forts, self.labels = [], {}
        self.shown_names = {}                            # {region / town file name: the name players read}
        self._symimg = {}
        c = self.canvas
        c.bind("<Configure>", lambda e: self.render())
        c.bind("<MouseWheel>", self._wheel)
        c.bind("<Button-4>", lambda e: self._wheel(e, 1))
        c.bind("<Button-5>", lambda e: self._wheel(e, -1))
        # left button: the map moves (a click picks a town); right button - or Ctrl + left
        # on a touchpad - moves characters, towns and ports, so nothing moves by accident
        # the right button drags the map everywhere (a click without moving opens the menu); the left one does all
        # the rest - picks, drags a sign, draws a box, paints (report #128)
        c.bind("<ButtonPress-1>", lambda e: self._press(e, icons=True))
        c.bind("<Control-ButtonPress-1>", lambda e: self._press(e, icons=True))
        c.bind("<B1-Motion>", self._move)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<ButtonPress-3>", lambda e: self._press(e, icons=True))
        c.bind("<B3-Motion>", self._move)
        c.bind("<ButtonRelease-3>", self._release)
        c.bind("<Motion>", self._hover)
        c.bind("<Double-Button-1>", self._double)          # a wonder opens its window, as in the game
        self.on_wonder = None                            # (type) -> the wonder's window
        self.on_town = None                              # (region) -> the town's own page (a double click)
        self.on_char_double = None                       # (char id) -> its units' window (a double click)
        self.on_place_stop = None                        # () -> what hangs under the mouse is dropped (Esc / right)
        self.waiting = False                             # something picked waits for its click (Edit regions too)
        self.canvas.winfo_toplevel().bind("<Escape>", lambda e: (self.on_place or self.waiting) and
                                          self.on_place_stop and self.on_place_stop(), add="+")
        self.on_fort_double = None                       # (Fort) -> its garrison's window (a double click)
        c.bind("<Leave>", lambda e: (self._grow(None), c.delete("tile_outline")))
        self._hot = None                                # the marker under the mouse, drawn bigger
        self._hot_k = 1.0                               # ... by how much now

    def _tool_click(self, e):
        """A click on a tool of the legend: picked (a second click puts it down again)."""
        lc = self.legend_canvas
        x, y = lc.canvasx(e.x), lc.canvasy(e.y)
        for item in reversed(lc.find_overlapping(x, y, x, y)):
            for tag in lc.gettags(item):
                if tag.startswith("tool:"):
                    key = tag[5:]
                    self.set_tool(None if key == self.tool else key)
                    if self.on_tool:
                        self.on_tool(self.tool)
                    return

    def set_tool(self, key):
        """The legend's picked tool (None: none), drawn highlighted."""
        if key != self.tool:
            self.tool = key
            self._legend_key = None
            self._draw_legend()

    def _modes(self):
        return [(k, l) for k, l in MODES if k != "religion" or self._religion_ok]

    def _fill_modes(self):
        modes = self._modes()
        self.cb_mode["values"] = [l for _, l in modes]
        if self.v_mode.get() not in dict(modes):
            self.v_mode.set("political")
            self._mode_changed(redraw=False)
        self.cb_mode.set(dict(modes)[self.v_mode.get()])
        end = self._menu.index("end")
        for i in range(end + 1):                         # Layers: the religion item only where there are religions
            try:
                if self._menu.entrycget(i, "value") == "religion":
                    self._menu.entryconfigure(i, state="normal" if self._religion_ok else "disabled")
            except tk.TclError:
                pass

    def allow_religion(self, ok):
        """Religion colours only where the game has religions (Medieval II)."""
        if bool(ok) != self._religion_ok:
            self._religion_ok = bool(ok)
            self._fill_modes()

    def _mode_picked(self):
        label = self.cb_mode.get()
        self.v_mode.set(next(k for k, l in self._modes() if l == label))
        self._mode_changed()

    def _mode_changed(self, redraw=True):
        m = self.v_mode.get()
        self.v_pol.set(m != "none")
        self.v_dip.set(m == "diplomacy")
        self.v_rel.set(m == "religion")
        if hasattr(self, "cb_mode"):
            self.cb_mode.set(dict(self._modes()).get(m, ""))
        self._legend_key = None
        if redraw:
            self._relayer()

    def _layers_label(self):
        mode = {"political": "political", "diplomacy": "diplomacy", "religion": "religion"}.get(
            self.v_mode.get()) if self.v_pol.get() else None
        on = ([mode] if mode else []) + [n for n, v in (
            ("borders", self.v_borders), ("names", self.v_names), ("ports", self.v_ports),
            ("characters", self.v_chars), ("resources", self.v_res)) if v.get()]
        self.lbl_layers.configure(text="shown: " + (", ".join(on) or "the ground only"))

    def _pick_toggled(self):
        """Select on: the political colours and borders go (picked towns show yellow on the ground), the characters,
        resources and forts show as their kinds are ticked; all comes back as it was after."""
        if self.v_pick.get():
            if self.v_regions.get():
                self.v_regions.set(False)
                self._regions_toggled()
            self._before_pick = (self.v_mode.get(), self.v_borders.get(), self.v_chars.get(), self.v_res.get(),
                                 self.v_forts.get())
            self.v_mode.set("none")
            self.v_borders.set(False)
            self._show_sel_kinds()
            self._mode_changed(redraw=False)
            self.readout.configure(text="Select: drag a box with the left button (it adds; Shift takes away), or click things; "
                                        "then a right click")
        elif self._before_pick:
            mode, borders, chars, res, forts = self._before_pick
            self._before_pick = None
            self.v_mode.set(mode)
            self.v_borders.set(borders)
            self.v_chars.set(chars)
            self.v_res.set(res)
            self.v_forts.set(forts)
            self._mode_changed(redraw=False)
        if not self.v_pick.get() and (self.picked or self.sel_chars or self.sel_res):   # off: nothing stays picked
            self.picked, self.sel_chars, self.sel_res = set(), set(), set()
            self.readout.configure(text="Select off - nothing selected")
        self._relayer()

    def _show_sel_kinds(self):
        """The layers the ticked kinds need: characters, resources, forts."""
        self.v_chars.set(any(self.v_sel[k].get() for k in ("armies", "agents", "fleets")))
        self.v_res.set(self.v_sel["resources"].get())
        self.v_forts.set(self.v_sel["forts"].get() or bool(self._before_pick and self._before_pick[4]))

    def _sel_kinds_changed(self):
        """A kind unticked: what of it was selected is dropped; in Select its layer follows."""
        if not self.v_sel["towns"].get():
            self.picked = set()
        self.sel_chars = {c for c in self.sel_chars if self._char_kind(c) and self.v_sel[self._char_kind(c)].get()}
        self.sel_res = {r for r in self.sel_res if self.v_sel["forts" if r[:1] in ("f", "g") else "resources"].get()}
        if self.v_pick.get():
            self._show_sel_kinds()
            self._relayer()
        self._picked_changed()

    def _char_kind(self, cid):
        """'armies' / 'agents' / 'fleets' of a character's id (None: not one on the map)."""
        ch_ = next((c for c in self.chars if c["id"] == cid), None)
        if ch_ is None:
            return None
        if ch_["kind"] in ("admiral", "fleet"):
            return "fleets"
        return "armies" if ch_.get("army") else "agents"

    def select_box(self, a, b, remove=False):
        """Everything of the ticked kinds whose tile lies between screen points a and b (a box dragged with the
        left button) is added to what is selected - with Shift held it is taken out of it instead (the user's
        wish: adding is the default, Shift takes away)."""
        (x0, y0), (x1, y1) = self.to_tile(*a), self.to_tile(*b)
        lo_x, hi_x, lo_y, hi_y = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)

        def inside(xy):
            return lo_x <= xy[0] <= hi_x and lo_y <= xy[1] <= hi_y
        towns, chars, res = set(), set(), set()
        if self.v_sel["towns"].get() and self.cmap:
            towns = {r for r, xy in self.cmap.cities.items()
                     if r in self.owners and inside(self.places.get(("city", r), xy))}
        for c in self.chars:
            k = self._char_kind(c["id"])
            if k and self.v_sel[k].get() and c.get("xy") and inside(tuple(c["xy"])):
                chars.add(c["id"])
        for r in self.resources:
            kind = "forts" if r["id"][:1] in ("f", "g") else "resources"
            if self.v_sel[kind].get() and inside(tuple(r["xy"])):
                res.add(r["id"])
        if remove:
            self.picked -= towns
            self.sel_chars -= chars
            self.sel_res -= res
        else:
            self.picked |= towns
            self.sel_chars |= chars
            self.sel_res |= res
        self._picked_changed()

    def _click_select(self, sx, sy, remove=False):
        """A click in Select (no box): the character, resource / fort or town under it added to what is selected
        (Shift: taken out of it); a click on nothing clears the selection."""
        def put(group, key):
            if remove:
                group.discard(key)
            else:
                group.add(key)
        cid = self._char_under(sx, sy)
        if cid is not None and self._char_kind(cid) and self.v_sel[self._char_kind(cid)].get():
            put(self.sel_chars, cid)
            return self._picked_changed()
        rid = self._res_under(sx, sy)
        if rid is not None and self.v_sel["forts" if rid[:1] in ("f", "g") else "resources"].get():
            put(self.sel_res, rid)
            return self._picked_changed()
        town = self._town_under(sx, sy)
        if town and self.v_sel["towns"].get():
            put(self.picked, town[0])
            return self._picked_changed()
        if not remove:
            self.picked, self.sel_chars, self.sel_res = set(), set(), set()
            self._picked_changed()

    def selected_count(self):
        return len(self.picked) + len(self.sel_chars) + len(self.sel_res)

    def _sel_marks(self):
        """A yellow frame round each selected character, resource and fort."""
        c = self.canvas
        for tag in ["char:%s" % x for x in self.sel_chars] + ["res:%s" % x for x in self.sel_res]:
            box = c.bbox(tag)
            if box:
                c.create_rectangle(box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2, outline="#ffd400", width=2,
                                   tags=("selmark",))

    def toggle_pick(self, region):
        self.picked ^= {region}
        self._picked_changed()

    def pick_many(self, regions):
        """Pick these towns too (None: unpick all - the characters and resources selected too)."""
        if regions is None:
            self.picked, self.sel_chars, self.sel_res = set(), set(), set()
        else:
            self.picked |= set(regions)
        self._picked_changed()

    def _picked_changed(self):
        self.render()
        self.readout.configure(text="selected: %d town(s), %d character(s), %d resource(s) / fort(s) - a right "
                                    "click acts on them all" % (len(self.picked), len(self.sel_chars),
                                                                len(self.sel_res)))

    def _regions_toggled(self):
        """Regions mode colours the land by region: the political colours and the
        borders are switched off meanwhile, and come back as they were after."""
        if self.v_regions.get():
            self._before_regions = (self.v_pol.get(), self.v_borders.get())
            self.v_pol.set(False)
            self.v_borders.set(False)
        elif getattr(self, "_before_regions", None):
            self.v_pol.set(self._before_regions[0])
            self.v_borders.set(self._before_regions[1])
            self._before_regions = None
        if self.on_layers:
            self.on_layers()
        else:
            self.render()

    # ---- the legend ----
    def _legend_toggled(self):
        from . import settings
        settings.put("map_legend", bool(self.v_legend.get()))
        if self.v_legend.get():
            self.legend.pack(side="right", fill="y")
            self._draw_legend()
        else:
            self.legend.pack_forget()
            if self.tool:                                # the legend hidden: its picked tool is put down too
                self.set_tool(None)
                if self.on_tool:
                    self.on_tool(None)

    LEGEND_RED = (190, 40, 40)

    def _draw_legend(self):
        """Every sign the map draws, with what it means (drawn by the map's own code)."""
        if not self.v_legend.get():
            return
        lc = self.legend_canvas
        lc.delete("all")
        main, self.canvas = self.canvas, lc            # the drawing helpers draw on self.canvas
        colours = self.colours
        self.colours = dict(colours, __legend__=self.LEGEND_RED)
        try:
            y = [14]

            def head(text):
                y[0] += 6
                lc.create_text(8, y[0], text=text, anchor="w", font=("", 9, "bold"), fill=theme.palette()["fg"])
                y[0] += 20

            def row(text, draw, tool=None):
                """A sign and its meaning; with a tool the window offers, a button: a click picks it."""
                on = tool is not None and tool in self.tools
                if on:                                  # a button: raised; the picked one yellow
                    picked = tool == self.tool
                    lc.create_rectangle(3, y[0] - 11, 245, y[0] + 11, fill="#ffd400" if picked else "#e4dccb",
                                        outline="#a08000" if picked else "#a89c84", width=2 if picked else 1)
                draw(22, y[0])
                lc.create_text(44, y[0], text=text + ("  +" if on else ""), anchor="w", font=("", 9),
                               fill="#000000" if on else theme.palette()["fg"])
                if on:
                    hit = lc.create_rectangle(2, y[0] - 12, 246, y[0] + 12, outline="", fill="",
                                              tags=("tool", "tool:" + tool))
                    lc.tag_raise(hit)
                y[0] += 24

            def town(fill, outline, width, hollow=False):
                def d(x, yy):
                    r = 9
                    lc.create_rectangle(x - r, yy - r, x + r, yy + r, fill="" if hollow else fill, outline=outline,
                                        width=width)
                    if not hollow:
                        self._hall(x, yy, r, self.LEGEND_RED, ())
                return d

            def port(x, yy):
                r = 8
                lc.create_oval(x - r, yy - r, x + r, yy + r, fill="#2a6fdb", outline="white")
                self._anchor(x, yy, r, ())

            def char(kind, army=False, mine=False):
                def d(x, yy):
                    self._draw_char({"id": "legend" if not mine else "legend_mine", "faction": "__legend__",
                                     "kind": kind, "army": army, "name": ""}, x, yy, 20)
                return d
            if self.tools:
                lc.create_text(8, y[0], anchor="w", width=236, font=("", 8), fill=theme.palette()["muted"],
                               text="Signs on a button (+) are tools: click one, then click the map to make one there; "
                                    "click it again to stop")
                y[0] += 22
            head("Towns and ports")
            red = "#%02x%02x%02x" % self.LEGEND_RED
            row("a town (its owner's colour)", town(red, "black", 1), "town")
            if not getattr(self, "everyone", False):          # the Map editor: no faction is 'yours'
                row("one of your towns", town(red, "#ffd400", 3))
            row("rebel village (no town yet)", town("", "black", 1, hollow=True))
            row("an army in it: a flag on its roof", lambda x, yy: self._roof_flag(x - 6, yy + 5, 13, "__legend__", ()))
            row("a port (click the coast)", port, "port")
            row("a fort (owner's colour)",
                lambda x, yy: self._fort_icon(lc, x, yy + 2, 7, "#%02x%02x%02x" % self.LEGEND_RED, (), 2), "fort")
            row("a watchtower (the same)",
                lambda x, yy: self._fort_icon(lc, x, yy + 2, 6, "#%02x%02x%02x" % self.LEGEND_RED, (), 2,
                                              "watchtower"), "watchtower")
            if any(fo.kind == "landmark" for fo in self.forts):
                row("a wonder (landmark): right drag",
                    lambda x, yy: self._wonder_icon(lc, x, yy, 8, "", ()))
            head("Characters")
            keep = self.draggable
            self.draggable = set(keep) | {"legend_mine"}
            row("a general / an army", char("general", army=True), "army")
            if not getattr(self, "everyone", False):
                row("yours: drag it", char("general", army=True, mine=True))
            for mark, label in (("crown", "flag: the faction's leader in it"), ("small crown", "flag: his heir"),
                                ("diamond", "flag: a family member"),
                                ("chevron", "flag: a captain (no family)")):
                row(label, lambda x, yy, m=mark: self._roof_flag(x - 9, yy + 10, 22, "__legend__", (), mark=m,
                                                                 field=True))
            row("a fleet (admiral)", char("admiral", army=True), "fleet")
            for k, label in (("spy", "spy"), ("assassin", "assassin"), ("diplomat", "diplomat"),
                             ("merchant", "merchant"), ("priest", "priest"), ("princess", "princess"),
                             ("inquisitor", "inquisitor"), ("heretic", "heretic"), ("witch", "witch")):
                row(label, char(k), k)
            self.draggable = keep
            head("Map")
            if self.tint is not None and self.tint_legend:
                for label, rgb in self.tint_legend:
                    row(label, lambda x, yy, rgb=rgb: lc.create_rectangle(
                        x - 9, yy - 7, x + 9, yy + 7, fill="#%02x%02x%02x" % tuple(rgb), outline="#303030"))
            else:
                row("political: land in its owner's colour", lambda x, yy: lc.create_rectangle(
                    x - 9, yy - 7, x + 9, yy + 7, fill=red, outline="#401010", width=2))
                row("rebel land: barely tinted", lambda x, yy: lc.create_rectangle(
                    x - 9, yy - 7, x + 9, yy + 7, fill="#9a9a9a", outline=""))
            row("the tile under the mouse", lambda x, yy: lc.create_rectangle(
                x - 8, yy - 8, x + 8, yy + 8, outline="white", width=2))
            row("drop here: fine", lambda x, yy: lc.create_rectangle(
                x - 8, yy - 8, x + 8, yy + 8, outline="#30ff60", width=2))
            row("drop here: refused (why below)", lambda x, yy: lc.create_rectangle(
                x - 8, yy - 8, x + 8, yy + 8, outline="#ff3030", width=2))
            # forts, watchtowers and Rome's wonders (landmark lines) have rows of their own above - 'landmark' among
            # the resources meant nothing to a modder (report #103)
            kinds = sorted(({r["kind"] for r in self.resources} | set(self.res_types)) - {"fort", "watchtower",
                                                                                         "landmark"})
            if kinds and self.v_res.get():           # with Layers > Resources on, every type a tool (+): a click
                head("Resources (first letters)")  # picks it, the next click on the map puts one there
                for k in kinds:
                    def d(x, yy, k=k):
                        lc.create_rectangle(x - 9, yy - 9, x + 9, yy + 9, fill=self.res_colour(k), outline="black")
                        lc.create_text(x, yy, text=k[:2].capitalize(), font=("", 8, "bold"),
                                       fill=self.text_on(self.res_colour(k)))
                    row(k, d, "res:" + k)
            lc.configure(scrollregion=(0, 0, 250, y[0] + 10))
        finally:
            self.canvas, self.colours = main, colours

    # ---- data ----
    def load(self, cmap, owners, colours, faction=None, chosen=(), on_city=None, chars=(), draggable=(),
             on_char_move=None, check_tile=None, symbols=None, on_place=None,
             places=None, check_place=None, on_place_move=None,
             region_mode=False, paint_overlay=None, on_paint=None, on_pick=None, brush=1, region_points=(),
             region_painted=None, region_colours=None, borders=True, ghost=None, locked=None,
             resources=None, check_res=None, on_res_move=None, on_res_click=None, res_sel=None, new_land=None,
             plain=False, labels=None, forts=None, tint=None, tint_legend=None, everyone=False):
        """chars: [{id, faction, name, kind, xy, army, units}]; draggable: ids that may be moved;
        everyone: the Map editor - every faction's things may be moved, none is 'yours' (no yellow edge: a map of
        yellow rings and flags looked as if all of it were selected - reports #99 #101);
        check_tile(id, xy) -> None or why not; on_char_move(id, xy) after a valid drop;
        symbols: {faction: path of its small symbol picture}."""
        first = self.cmap is None or self.cmap is not cmap
        self.cmap, self.owners, self.colours = cmap, dict(owners), colours
        self.everyone = bool(everyone)
        # a colour mode's own land colours {region: rgb} (religion), drawn in place of the owners'
        self.tint, self.tint_legend = (dict(tint) if tint else None), list(tint_legend or [])
        self.faction, self.chosen, self.on_city = faction, set(chosen), on_city
        self.chars, self.draggable = list(chars), set(draggable)
        self.on_char_move, self.check_tile = on_char_move, check_tile
        self.symbols = symbols or {}
        self.on_place = on_place            # on_place(xy) -> None, or why not: the next click places
        # towns and ports dragged to new tiles: {(what, region): xy}; check_place(what, region, xy)
        # -> None or why not; on_place_move(what, region, xy) after a good drop
        self.places = dict(places or {})
        self.check_place, self.on_place_move = check_place, on_place_move
        # Regions mode: paint_overlay {(x, y): (r, g, b)} tiles given to another region;
        # on_paint([tiles]) -> the tiles it took; on_pick(xy); region_points [(xy, 'city'|'port', rgb)]
        self.region_mode, self.paint_overlay = region_mode, dict(paint_overlay or {})
        self.on_paint, self.on_pick, self.brush = on_paint, on_pick, brush
        self.region_points = list(region_points)
        # outside the Regions mode: the land of new regions {(x, y): rgb}, drawn until Apply
        self.new_land = dict(new_land or {})
        # the window's own dict: a stroke shows as soon as it ends
        self.region_painted = region_painted if region_painted is not None else {}
        self.region_colours, self.borders = dict(region_colours or {}), borders
        # ghost = {'kind': 'city'|'port'|'army'|'agent'|'fleet', 'check': fn(xy) -> None or why}:
        # a see-through marker under the mouse while placing
        self.ghost = ghost
        # locked(char) -> why this character cannot be dragged here (shown when one tries)
        self.locked = locked
        self.resources = list(resources or [])
        self.check_res, self.on_res_move, self.on_res_click = check_res, on_res_move, on_res_click
        self.res_sel = res_sel
        self.labels = dict(labels or {})     # {region: name} the town shows for its owner (names by culture)
        self.forts = list(forts or [])       # [strat.Fort] of descr_strat: drawn, and no one may start on them
        self.plain = plain                  # the Terrain editor: the ground alone, no political or region colours
        if first:
            self.fit()
        else:
            self.render()

    # ---- geometry ----
    def to_screen(self, x, y):
        """Tile (x, y) (y up) -> the canvas point at the tile's centre."""
        return (x - self.ox + 0.5) * self.z, ((self.cmap.h - 1 - y) - self.oy + 0.5) * self.z

    def to_tile(self, sx, sy):
        x = math.floor(self.ox + sx / self.z)          # floor: left of / above the map are tiles -1, -2 ...
        row = math.floor(self.oy + sy / self.z)
        return x, self.cmap.h - 1 - row

    def fit(self):
        if not self.cmap:
            return
        cw, ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        self.z = min(cw / self.cmap.w, ch / self.cmap.h)
        self.ox, self.oy = (self.cmap.w - cw / self.z) / 2, (self.cmap.h - ch / self.z) / 2      # in the middle
        self.render()

    def centre_on(self, xy, zoom=16):
        """Put tile xy in the middle, zoomed in to at least `zoom` pixels a tile, and mark it."""
        if not self.cmap:
            return
        cw, ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        self.z = max(self.z, zoom)
        self.ox = xy[0] + 0.5 - cw / 2 / self.z
        self.oy = (self.cmap.h - 1 - xy[1]) + 0.5 - ch / 2 / self.z
        self.render()
        self._flash = xy
        self._flash_n = getattr(self, "_flash_n", 0) + 1        # a newer find stops the older one's blinking
        self.after(60, lambda n=self._flash_n: self._mark_flash(n, 0))

    def _mark_flash(self, n, step):
        """A ring round the found tile, blinking for about 4 seconds (dark and yellow, seen on any ground)."""
        xy = getattr(self, "_flash", None)
        if not xy or not self.cmap or n != getattr(self, "_flash_n", 0):
            return
        self.canvas.delete("flash")
        if step >= 10:
            return
        if step % 2 == 0:
            sx, sy = self.to_screen(*xy)
            r = max(self.z * 1.2, 14)
            self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, outline="#000000", width=7, tags=("flash",))
            self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, outline="#ffd400", width=4, tags=("flash",))
        self.after(400, lambda: self._mark_flash(n, step + 1))

    def _fit_z(self):
        cw, ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        return min(cw / self.cmap.w, ch / self.cmap.h)

    def pct(self):
        """The zoom as the window shows it: 100 % = the whole map fits the view."""
        return 100.0 * self.z / self._fit_z() if self.cmap else 100.0

    def zoom_by(self, step, at=None, by=None):
        """One wheel notch in (step > 0) or out: the shown zoom moves to the next whole multiple of `by` per cent
        (the settings' wheel step, 10 by default; Ctrl + wheel the fine step, 5) - 100, 110, 120 ... %."""
        if not self.cmap:
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        sx, sy = at or (cw / 2, ch / 2)
        tx, ty = self.ox + sx / self.z, self.oy + sy / self.z
        fit = self._fit_z()
        by = by or zoom_setting("map_zoom_step")
        now = 100.0 * self.z / fit
        if step > 0:
            pct = (math.floor(now / by + 1e-6) + 1) * by
        elif step < 0:
            pct = (math.ceil(now / by - 1e-6) - 1) * by
        else:
            pct = now
        least = min(25.0, 100.0 * ZOOMS[0] / fit)          # out to a quarter of the view: the field around it
        most = 100.0 * ZOOMS[-1] / fit
        self.z = fit * max(least, min(most, pct)) / 100.0
        self.ox, self.oy = tx - sx / self.z, ty - sy / self.z
        self.render()

    def _clamp(self):
        """The map is a free canvas: it may be dragged past its edges and zoomed out smaller than the view, with
        the empty field around it - only a strip of it always stays in sight (a quarter of the smaller of the
        view and the map), so it is never lost."""
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        vw, vh = cw / self.z, ch / self.z
        kx, ky = min(vw, self.cmap.w) / 4, min(vh, self.cmap.h) / 4
        self.ox = min(max(self.ox, kx - vw), self.cmap.w - kx)
        self.oy = min(max(self.oy, ky - vh), self.cmap.h - ky)

    @staticmethod
    def _field():
        """The empty field around the map: a little darker than the window."""
        return (24, 25, 28) if theme.dark() else (168, 172, 178)

    def inside(self, xy):
        """Whether tile xy is on the map (a click on the field around it is not)."""
        return bool(self.cmap) and 0 <= xy[0] < self.cmap.w and 0 <= xy[1] < self.cmap.h

    def _outside(self, xy):
        return None if self.inside(xy) else "outside the map"

    # ---- drawing ----
    def _zoom_label(self):
        lab = getattr(self, "lbl_zoom", None)
        if lab is None or not self.cmap:
            return
        cw, ch = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        fit = min(cw / self.cmap.w, ch / self.cmap.h)
        lab.configure(text="%d%%" % round(100 * self.z / fit) if fit else "")

    def render(self):
        if self._pending is None:
            self._pending = self.after(15, self._render)

    def _render(self):
        self._pending = None
        c = self.canvas
        c.delete("all")
        self._hot, self._hot_k = None, 1.0
        if not self.cmap:
            c.create_text(20, 20, anchor="nw", fill="#ccc", text="Load a mod: the campaign map shows here.")
            return
        self._clamp()
        self._zoom_label()
        cw, ch = c.winfo_width(), c.winfo_height()
        vw, vh = cw / self.z, ch / self.z
        box = (self.ox, self.oy, self.ox + vw, self.oy + vh)
        base = self._base()                                           # 2 px per tile, colours laid on once
        # sharp tiles always, still or dragged: the smoothed picture at rest looked blurred beside the sharp one while
        # dragging (report #100) - the map is by tiles, as the game's files are
        pic = view_of(base, box, (cw, ch), Image.NEAREST, self._field())
        self._photo = ImageTk.PhotoImage(pic)
        c.create_image(0, 0, anchor="nw", image=self._photo, tags=("bg",))
        self._drawn_at = (self.ox, self.oy)
        if self.v_grid.get() and self.z >= 10:
            self._grid(cw, ch)
        self._markers(cw, ch)
        if self.v_pick.get() and (self.sel_chars or self.sel_res):
            self._sel_marks()
        key = (tuple(sorted({r["kind"] for r in self.resources})), self.v_res.get(), self.v_forts.get(),
               tuple(self.tint_legend) if self.tint is not None else None, tuple(sorted(self.tools)), self.tool,
               tuple(self.res_types))
        if key != getattr(self, "_legend_key", None):
            self._legend_key = key
            self._draw_legend()

    def _pan(self):
        """While the map is dragged: a new background, the markers only shifted (drawing
        a couple of thousand of them again is the slow part); all is redrawn on release."""
        self._pending = None
        c = self.canvas
        if not self.cmap or not c.find_withtag("bg"):
            return self._render()
        self._clamp()
        cw, ch = c.winfo_width(), c.winfo_height()
        box = (self.ox, self.oy, self.ox + cw / self.z, self.oy + ch / self.z)
        pic = view_of(self._base(), box, (cw, ch), Image.NEAREST, self._field())
        self._photo = ImageTk.PhotoImage(pic)
        c.itemconfigure("bg", image=self._photo)
        ox, oy = self._drawn_at
        dx, dy = (ox - self.ox) * self.z, (oy - self.oy) * self.z
        c.move("all", dx, dy)
        c.move("bg", -dx, -dy)
        self._drawn_at = (self.ox, self.oy)

    PICTURE_PX = 8                                      # Save picture...: pixels per tile

    def save_picture(self, path=None):
        """The whole map as it is drawn now (the layers, colours and borders that are on; not the signs) saved as a
        picture, PICTURE_PX pixels a tile - for a forum post or a plan. Returns the path or None."""
        if not self.cmap:
            return None
        if path is None:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".png", initialfile="campaign_map.png",
                                                filetypes=[("PNG picture", "*.png"), ("TGA picture", "*.tga")])
            if not path:
                return None
        pic = self._base().convert("RGB")
        k = self.PICTURE_PX // 2                          # the base is 2 px a tile
        pic = pic.resize((pic.width * k, pic.height * k), Image.NEAREST)
        pic.save(path)
        self.readout.configure(text="the map saved as a picture: %s (%d x %d px)" % (path, pic.width, pic.height))
        return path

    def _base(self):
        """The background with the political colours laid on, at 2 px per tile,
        made again only when the colours change - moving the map only crops it."""
        bg = self.cmap.background(self.v_relief.get(), self.v_rivers.get())
        if getattr(self, "plain", False):
            return bg
        land = () if self.region_mode else tuple(sorted(self.new_land.items()))
        if self.v_pick.get() and self.picked and not self.region_mode:
            # Pick towns: the picked towns' regions see-through yellow (a tester: the towns alone were hard to see)
            pol = self.cmap.political({r: "picked" for r in self.picked}, {"picked": (255, 212, 0)}, None,
                                      alpha=110, borders=True)
        elif self.region_mode:
            pol = self.cmap.regions_layer(self.region_painted, self.region_colours, borders=self.v_borders.get())
        elif not self.v_pol.get() and not self.v_borders.get() and not land:
            return bg
        elif not self.v_pol.get() and not self.v_borders.get():
            pol = Image.new("RGBA", (self.cmap.w, self.cmap.h), (0, 0, 0, 0))
        else:
            if self.v_pol.get() and self.tint is not None:
                pol = self.cmap.political({r: r for r in self.tint}, self.tint, None, borders=self.v_borders.get())
            elif self.v_pol.get():
                pol = self.cmap.political(self.owners, self.colours, self.faction, borders=self.v_borders.get(),
                                          painted=self.region_painted)
            else:                                   # the borders alone
                pol = self.cmap.political(self.owners, self.colours, None, alpha=0, borders=True,
                                          painted=self.region_painted)
        key = (id(bg), id(pol), land)
        if getattr(self, "_base_key", None) != key:
            if land:                                    # a new region's land, in its colour, until Apply
                pol = pol.copy()
                px = pol.load()
                for (x, y), rgb in land:
                    if 0 <= x < pol.width and 0 <= y < pol.height:
                        px[x, pol.height - 1 - y] = tuple(rgb) + (215,)
            over = pol.resize((pol.width * 2, pol.height * 2), Image.NEAREST)
            if over.size != bg.size:
                over = over.resize(bg.size, Image.NEAREST)
            self._base_img = Image.alpha_composite(bg.convert("RGBA"), over).convert("RGB")
            self._base_key = key
        return self._base_img

    def _grid(self, cw, ch):
        """Thin lines between the tiles up close: what is placed or painted is one square (on the map only, not
        on the field around it)."""
        c, z = self.canvas, self.z
        col = "#000000"
        left, top = max(0.0, -self.ox * z), max(0.0, -self.oy * z)
        right, bottom = min(cw, (self.cmap.w - self.ox) * z), min(ch, (self.cmap.h - self.oy) * z)
        if right <= left or bottom <= top:
            return
        x0 = max(int(self.ox) - 1, 0)
        while x0 <= self.cmap.w and (x0 - self.ox) * z <= right:
            sx = (x0 - self.ox) * z
            if sx >= left:
                c.create_line(sx, top, sx, bottom, fill=col, stipple="gray50", tags=("grid",))
            x0 += 1
        y0 = max(int(self.oy) - 1, 0)
        while y0 <= self.cmap.h and (y0 - self.oy) * z <= bottom:
            sy = (y0 - self.oy) * z
            if sy >= top:
                c.create_line(left, sy, right, sy, fill=col, stipple="gray50", tags=("grid",))
            y0 += 1

    def _painted(self, cw, ch):
        """Tiles given to another region, in that region's colour, and the new towns and ports."""
        c, z = self.canvas, self.z                      # painted tiles are in the regions layer itself
        size = max(4, min(z * 0.9, 60))
        for (x, y), what, rgb in self.region_points:
            sx, sy = self.to_screen(x, y)
            r = size / 2
            if what == "city":
                c.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill="#%02x%02x%02x" % rgb, outline="#ffd400",
                                   width=3)
                if r >= 6:
                    self._hall(sx, sy, r, rgb, ("newtown",))
            else:
                c.create_oval(sx - r * 0.9, sy - r * 0.9, sx + r * 0.9, sy + r * 0.9, fill="#2a6fdb", outline="#ffd400",
                              width=3)
                if r >= 5:
                    self._anchor(sx, sy, r * 0.9, ("newport",))

    def _paint_at(self, e):
        x, y = self.to_tile(e.x, e.y)
        b = self.brush - 1
        tiles = [(x + dx, y + dy) for dx in range(-b, b + 1) for dy in range(-b, b + 1)
                 if self.inside((x + dx, y + dy))]
        took = self.on_paint(tiles) if self.on_paint and tiles else []
        z, c = self.z, self.canvas
        for (tx, ty), rgb in took:
            self.paint_overlay[(tx, ty)] = rgb
            sx, sy = self.to_screen(tx, ty)
            # solid, with a thin yellow edge when the tiles are big enough: a see-through (stippled) fill was
            # invisible on a like colour and shimmered on the coast (testers' reports); until the stroke ends
            c.create_rectangle(sx - z / 2, sy - z / 2, sx + z / 2, sy + z / 2, fill="#%02x%02x%02x" % rgb,
                               outline="#ffd400" if z >= 6 else "", width=1, tags=("paint",))

    def _markers(self, cw, ch):
        c, cm = self.canvas, self.cmap
        if self.region_mode or self.region_points:       # new towns and ports show until Apply
            self._painted(cw, ch)
        size = max(3, min(self.z * 0.9, 60))           # a town fills its tile
        font = ("", 8 if self.z < 10 else 9)
        signs = self.pct() >= zoom_setting("map_signs_from") - 1e-6   # far out: towns only (the settings' zoom)
        if self.v_ports.get() and signs:              # far out: towns only - less to draw, less clutter
            new = {r: xy for (w, r), xy in self.places.items() if w == "port" and r not in cm.ports}
            for region, (x, y) in list(cm.ports.items()) + list(new.items()):     # a new port too (not written yet)
                if region in getattr(self, "ports_gone", ()):
                    continue                            # taken off the map (written with the next Apply)
                x, y = self.places.get(("port", region), (x, y))
                sx, sy = self.to_screen(x, y)
                if -10 < sx < cw + 10 and -10 < sy < ch + 10:
                    r = size * 0.45
                    tags = ("port", "port:" + region)
                    c.create_oval(sx - r, sy - r, sx + r, sy + r, fill="#2a6fdb", outline="white", width=1, tags=tags)
                    if r >= 5:
                        self._anchor(sx, sy, r, tags)
        if self._marks_on():
            self._resources(cw, ch)
        self._forts(cw, ch)
        for region, (x, y) in cm.cities.items():
            x, y = self.places.get(("city", region), (x, y))
            sx, sy = self.to_screen(x, y)
            if not (-40 < sx < cw + 40 and -20 < sy < ch + 20):
                continue
            owner = self.owners.get(region)
            rgb = REBELS if owner in (None, "slave") else self.colours.get(owner, REBELS)
            mine = region in self.chosen and not getattr(self, "everyone", False)
            picking = self.v_pick.get()
            if picking:                                  # Pick towns: the picked ones yellow, the ring is theirs
                mine = region in self.picked
                if mine:
                    rgb = (255, 212, 0)
            r = size / 2 + (2 if mine else 0)
            c.create_rectangle(sx - r, sy - r, sx + r, sy + r,
                               fill="" if owner is None else "#%02x%02x%02x" % rgb,    # hollow: no town at the start
                               outline=("black" if picking else "#ffd400") if mine else "black",
                               width=3 if mine else 1, tags=("city", "city:" + region))
            if r >= 6:
                self._hall(sx, sy, size / 2, rgb, ("city", "city:" + region))
            if self.v_names.get() and (self.z >= 4 or mine):
                name = self.labels.get(region) or cm.info.get(region, {}).get("settlement", region)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1)):     # a black edge all round: white
                    c.create_text(sx + r + 2 + dx, sy + dy, text=name, anchor="w", fill="black", font=font)
                c.create_text(sx + r + 2, sy, text=name, anchor="w", fill="white", font=font)   # reads on any land
        if self.v_chars.get() and signs and not self.region_mode:
            self._characters(cw, ch, size)
        self._size_badge()

    def _size_badge(self):
        """The map's real size, under the map at its bottom left (never over the map, never moving): tiles
        (= map_regions.tga pixels) and the 2x+1 pictures."""
        w, h = self.cmap.w, self.cmap.h
        self.size_label.configure(text="Map %d x %d tiles (map_regions.tga) - heights %d x %d px"
                                  % (w, h, 2 * w + 1, 2 * h + 1))

    def _anchor(self, sx, sy, r, tags):
        """An anchor inside the port's circle: ring, shank, stock and flukes."""
        c, w = self.canvas, max(1, int(r / 6))
        k = r * 0.14
        c.create_oval(sx - k, sy - r * 0.72 - k, sx + k, sy - r * 0.72 + k, outline="white", width=w, tags=tags)
        c.create_line(sx, sy - r * 0.58, sx, sy + r * 0.62, fill="white", width=w, tags=tags)
        c.create_line(sx - r * 0.35, sy - r * 0.35, sx + r * 0.35, sy - r * 0.35, fill="white", width=w, tags=tags)
        a = r * 0.5                                   # the flukes: an arc that stays inside the circle
        c.create_arc(sx - a, sy + r * 0.12 - a, sx + a, sy + r * 0.12 + a, start=200, extent=140,
                     style="arc", outline="white", width=w, tags=tags)

    def _hall(self, sx, sy, r, rgb, tags):
        """A town hall inside the town's square: roof, three columns, steps -
        light on a dark owner colour, dark on a light one."""
        c = self.canvas
        ink = "#202020" if self.text_on(rgb) == "black" else "#f4f0e0"
        # roof (pediment) and the beam under it
        c.create_polygon(sx - r * 0.8, sy - r * 0.38, sx, sy - r * 0.82, sx + r * 0.8, sy - r * 0.38,
                         fill=ink, outline="", tags=tags)
        c.create_rectangle(sx - r * 0.72, sy - r * 0.34, sx + r * 0.72, sy - r * 0.24, fill=ink, outline="", tags=tags)
        for cx in (-0.48, 0, 0.48):                   # three columns
            c.create_rectangle(sx + r * (cx - 0.1), sy - r * 0.2, sx + r * (cx + 0.1), sy + r * 0.42,
                               fill=ink, outline="", tags=tags)
        c.create_rectangle(sx - r * 0.72, sy + r * 0.46, sx + r * 0.72, sy + r * 0.58, fill=ink, outline="", tags=tags)
        c.create_rectangle(sx - r * 0.84, sy + r * 0.62, sx + r * 0.84, sy + r * 0.76, fill=ink, outline="", tags=tags)

    # ---- characters ----
    AGENT_LETTER = {"spy": "S", "diplomat": "D", "assassin": "A", "merchant": "M", "priest": "P",
                    "princess": "Q", "inquisitor": "I", "heretic": "H", "witch": "W"}

    def _glyph(self, k, sx, sy, r, tags):
        """An agent kind's sign inside its disc (r = the disc's radius): white on a dark faction colour, black on a
        bright one."""
        c, ink = self.canvas, self.text_on(getattr(self, "_fill_of_disc", "#000000"))
        w = max(1, int(r / 4))
        if k == "spy":                                  # an eye
            c.create_oval(sx - r * 0.7, sy - r * 0.38, sx + r * 0.7, sy + r * 0.38, outline=ink, width=w, tags=tags)
            c.create_oval(sx - r * 0.2, sy - r * 0.2, sx + r * 0.2, sy + r * 0.2, fill=ink, outline="", tags=tags)
        elif k == "assassin":                           # an upright dagger, the point down: pommel, grip, a short
            c.create_oval(sx - r * 0.12, sy - r * 0.8, sx + r * 0.12, sy - r * 0.56, fill=ink, outline="",  # thin
                          tags=tags)                                                                  # guard, blade
            c.create_line(sx, sy - r * 0.6, sx, sy - r * 0.28, fill=ink, width=w + 1, tags=tags)
            c.create_line(sx - r * 0.26, sy - r * 0.24, sx + r * 0.26, sy - r * 0.24, fill=ink, width=max(1, w - 1),
                          tags=tags)
            c.create_polygon(sx - r * 0.15, sy - r * 0.2, sx + r * 0.15, sy - r * 0.2, sx, sy + r * 0.82, fill=ink,
                             outline="", tags=tags)
        elif k == "diplomat":                           # a scroll
            c.create_rectangle(sx - r * 0.5, sy - r * 0.6, sx + r * 0.5, sy + r * 0.6, outline=ink, width=w, tags=tags)
            for dy in (-0.25, 0.05, 0.35):
                c.create_line(sx - r * 0.3, sy + r * dy, sx + r * 0.3, sy + r * dy, fill=ink, tags=tags)
        elif k == "merchant":                           # a coin with the euro sign on it
            c.create_oval(sx - r * 0.66, sy - r * 0.66, sx + r * 0.66, sy + r * 0.66, outline=ink, width=w,
                          tags=tags)
            c.create_text(sx, sy, text="\u20ac", fill=ink, font=("", max(6, int(r * 0.95)), "bold"), tags=tags)
        elif k == "priest":                             # an open book (no faith's own sign: imams are priests too)
            c.create_polygon(sx - r * 0.7, sy - r * 0.4, sx, sy - r * 0.25, sx, sy + r * 0.55, sx - r * 0.7,
                             sy + r * 0.4, fill=ink, outline="", tags=tags)
            c.create_polygon(sx + r * 0.7, sy - r * 0.4, sx, sy - r * 0.25, sx, sy + r * 0.55, sx + r * 0.7,
                             sy + r * 0.4, fill=ink, outline="", tags=tags)
            c.create_line(sx, sy - r * 0.25, sx, sy + r * 0.55, fill=self._fill_of_disc, width=max(1, w - 1),
                          tags=tags)
        elif k == "princess":                           # a heart (the crowns mark the king and his heir)
            self._heart(sx, sy + r * 0.05, r * 0.62, ink, tags)
        elif k == "inquisitor":                         # scales: judgement
            c.create_line(sx, sy - r * 0.6, sx, sy + r * 0.5, fill=ink, width=w, tags=tags)
            c.create_line(sx - r * 0.6, sy - r * 0.35, sx + r * 0.6, sy - r * 0.35, fill=ink, width=w, tags=tags)
            for dx in (-0.45, 0.45):
                c.create_polygon(sx + r * (dx - 0.25), sy + r * 0.05, sx + r * (dx + 0.25), sy + r * 0.05,
                                 sx + r * dx, sy + r * 0.3, fill=ink, outline="", tags=tags)
            c.create_line(sx - r * 0.3, sy + r * 0.55, sx + r * 0.3, sy + r * 0.55, fill=ink, width=w, tags=tags)
        elif k == "witch":                              # a pointed hat
            c.create_polygon(sx - r * 0.3, sy + r * 0.25, sx, sy - r * 0.75, sx + r * 0.3, sy + r * 0.25,
                             fill=ink, outline="", tags=tags)
            c.create_oval(sx - r * 0.7, sy + r * 0.15, sx + r * 0.7, sy + r * 0.45, fill=ink, outline="", tags=tags)
        elif k == "heretic":                            # a lightning bolt
            c.create_polygon(sx + r * 0.2, sy - r * 0.78, sx - r * 0.42, sy + r * 0.08, sx - r * 0.02, sy + r * 0.08,
                             sx - r * 0.2, sy + r * 0.78, sx + r * 0.42, sy - r * 0.08, sx + r * 0.02, sy - r * 0.08,
                             fill=ink, outline="", tags=tags)
        else:
            c.create_text(sx, sy, text=self.AGENT_LETTER.get(k, k[:1].upper()), fill=ink,
                          font=("", max(6, int(r)), "bold"), tags=tags)

    def _characters(self, cw, ch, size):
        cm = self.cmap
        towns = {self.places.get(("city", r), xy) for r, xy in cm.cities.items()}
        busy = towns | {self.places.get(("port", r), xy) for r, xy in cm.ports.items()}
        tile = max(self.z * 0.9, 6)                    # a character fills its tile...
        town_of = {self.places.get(("city", r), xy): r for r, xy in cm.cities.items()}
        seen, flags = {}, set()
        forts = self.fort_spots()
        rank = {"crown": 3, "small crown": 2, "diamond": 1.5, "star": 1, "chevron": 0.5}
        best = {}                                      # a town's / fort's flag shows the highest who stays there
        for c_ in self.chars:
            m = self.leader_mark(c_) if c_["kind"] in ("general", "named character") else None
            if m and rank[m] > rank.get(best.get(tuple(c_["xy"])), 0):
                best[tuple(c_["xy"])] = m
        for ch_ in sorted(self.chars, key=lambda c: not c["army"]):     # the garrison first
            x, y = ch_["xy"]
            sx, sy = self.to_screen(x, y)
            if not (-30 < sx < cw + 30 and -30 < sy < ch + 30):
                continue
            one = tile
            if (x, y) in towns and ch_["kind"] in ("general", "named character"):
                # an army in a town: ONE flag on the town's roof, part of the town's sign (it grows with it and is
                # never dragged - the army leaves by the right click's 'Take the army out'); it only says that an
                # army is there (the user's choice, report #104)
                if (x, y) not in flags:
                    flags.add((x, y))
                    self._roof_flag(sx + size / 2, sy - size / 2, max(tile * 0.8, 8), ch_["faction"],
                                    ("city", "city:" + town_of.get((x, y), "")), mark=best.get((x, y)))
                continue
            if (x, y) in forts and ch_["kind"] in ("general", "named character"):
                # an army in a fort or a watchtower: the same flag as on a town's roof, on the sign's upper right
                # corner, part of the sign (the army leaves by the right click's 'Take the army out')
                if (x, y) not in flags:
                    flags.add((x, y))
                    w = max(2.0, min(self.z * FORT_W, 36))
                    self._roof_flag(sx + w, sy - w, max(tile * 0.8, 8), ch_["faction"], forts[(x, y)],
                                    mark=best.get((x, y)))
                continue
            elif (x, y) in busy:                       # ...an agent or a ship stands small beside the town /
                n = seen.get((x, y), 0)                # port, to its left (the name is on the right), in a row
                seen[(x, y)] = n + 1
                one = max(tile * 0.6, 3)
                sx = sx - tile * 0.5 - one * 0.45 - n * one * 0.75
            else:
                n = seen.get((x, y), 0)
                seen[(x, y)] = n + 1
                sx += n * one * 0.5
            self._draw_char(ch_, sx, sy, one)

    def fort_spots(self):
        """{tile: the tags of its sign} of every fort and watchtower where it stands now (moved ones, added ones in
        the Map editor - drawn there as movable signs)."""
        if self._marks_on():
            return {tuple(r["xy"]): ("res", "res:%s" % r["id"]) for r in self.resources
                    if r.get("kind") in ("fort", "watchtower")}
        return {tuple(fo.xy): ("fort", "fort:%d" % fo.line) for fo in (self.forts or []) if fo.kind != "landmark"}

    def _roof_flag(self, cx, cy, h, faction, tags, edge="black", width=1, mark=None, field=False):
        """An army's flag: on a town's sign the cloth's lower left corner on the sign's upper right corner (cx, cy),
        its pole only along the cloth's left edge; a square cloth in the army's colour with a triangle cut into its
        right edge, a thin black edge - nothing yellow (the user's choice, report #104). In the field the same flag
        (cx, cy = the pole's foot) with who leads it on the cloth (mark)."""
        c = self.canvas
        rgb = REBELS if faction == "slave" else self.colours.get(faction, REBELS)
        fill = "#%02x%02x%02x" % rgb
        w, ch = h * 0.8, h * 0.6
        if field:                                                       # in the field: the pole down to the tile
            foot, top = cy, cy - h
            c.create_line(cx, foot, cx, top - h * 0.05, fill="black", width=2, tags=tags)
            c.create_polygon(cx, top, cx + w, top, cx + w * 0.7, top + ch / 2, cx + w, top + ch, cx, top + ch,
                             fill=fill, outline=edge, width=width, tags=tags)
            if mark and h >= 7:
                self._mark(mark, cx + w * 0.4, top + ch / 2, ch * 0.42, self.text_on(fill), tags)
            return
        top = cy - ch
        c.create_polygon(cx, top, cx + w, top, cx + w * 0.7, top + ch / 2, cx + w, cy, cx, cy,
                         fill=fill, outline="black", width=1, tags=tags)
        c.create_line(cx, cy, cx, top - h * 0.12, fill="black", width=2, tags=tags)
        if mark and h >= 7:
            self._mark(mark, cx + w * 0.4, top + ch / 2, ch * 0.42, self.text_on(fill), tags)

    def _draw_char(self, ch_, sx, sy, size):
        c = self.canvas
        rgb = REBELS if ch_["faction"] == "slave" else self.colours.get(ch_["faction"], REBELS)
        fill = "#%02x%02x%02x" % rgb
        mine = ch_["id"] in self.draggable and not getattr(self, "everyone", False)
        edge = "#ffd400" if mine else "black"
        tags = ("char", "char:%s" % ch_["id"])
        k = ch_["kind"]
        if k not in ("admiral", "general", "named character"):          # an agent: a disc with its sign
            r = max(size * 0.5, 1.5)                   # shrinks with the zoom like armies and towns (report #119)
            c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=fill, outline=edge, width=2 if mine else 1, tags=tags)
            if size >= 8:
                self._fill_of_disc = fill
                self._glyph(k, sx, sy, r, tags)
        elif k == "admiral":
            # a ship: its keel one pixel above the tile's lower edge, the hull in the owner's colour, a mast and a
            # white sail
            w = size * 0.5                              # the keel by the sign's own size (the legend draws it at
            keel = sy + size * 0.55 - 1                 # another zoom than the map's - it moved there)
            deck = keel - w * 0.55
            c.create_polygon(sx - w, deck, sx + w, deck, sx + w * 0.6, keel, sx - w * 0.6, keel,
                             fill=fill, outline=edge, width=2 if mine else 1, tags=tags)
            top = deck - w * 1.3
            c.create_line(sx, deck, sx, top, fill="black", width=max(1, int(w / 5)), tags=tags)
            c.create_polygon(sx + w * 0.08, top + w * 0.1, sx + w * 0.75, deck - w * 0.15, sx + w * 0.08,
                             deck - w * 0.15, fill="#f4efe2", outline="black", width=1, tags=tags)
        else:
            # an army - and a family member without units too: the game shows every named character on the map
            # as a general with his flag (a tester: a sign of its own meant nothing in the game). The flag as on a
            # town's roof; who leads it on the cloth: the king a crown, his heir a small crown, a family member a
            # diamond, a captain (no family member leads it) a chevron
            h = size                                       # pole and cloth inside the tile
            sx -= h * 0.35
            self._roof_flag(sx, sy + h * 0.5, h * 0.95, ch_["faction"], tags, edge=edge, width=2 if mine else 1,
                            mark=self.leader_mark(ch_), field=True)
            if mine:
                c.create_rectangle(sx - 2, sy + h * 0.5 - 2, sx + 2, sy + h * 0.5 + 2, fill="#ffd400", outline="",
                                   tags=tags)

    @staticmethod
    def leader_mark(ch_):
        """'crown' (the faction's leader), 'small crown' (its heir), 'diamond' (a family member), 'chevron' (a
        captain: descr_strat's 'general' - an army no family member leads; in the game its first unit's captain
        leads it)."""
        role = ch_.get("role")
        if role == "leader":
            return "crown"
        if role == "heir":
            return "small crown"
        if ch_.get("kind") == "named character" or ch_.get("named"):
            return "diamond"
        return "chevron"                               # a captain: a soldier's rank chevron

    def _mark(self, mark, cx, cy, r, ink, tags):
        """A leader's mark at (cx, cy), r about half its width."""
        c = self.canvas
        if mark == "star":
            pts = []
            for i in range(10):
                a = -math.pi / 2 + i * math.pi / 5
                rr = r if i % 2 == 0 else r * 0.45
                pts += [cx + rr * math.cos(a), cy + rr * math.sin(a)]
            c.create_polygon(*pts, fill=ink, outline="", tags=tags)
        elif mark == "diamond":                       # a family member: a white rhombus, taller than wide (a thin
            c.create_polygon(cx, cy - r, cx + r * 0.7, cy, cx, cy + r, cx - r * 0.7, cy, fill="white",  # dark edge
                             outline="#202020" if ink == "black" else "", tags=tags)   # where the cloth is light)
        elif mark == "chevron":                       # a wide chevron, its point up
            c.create_line(cx - r, cy + r * 0.45, cx, cy - r * 0.45, cx + r, cy + r * 0.45, fill=ink,
                          width=max(2, int(r * 0.45)), joinstyle="miter", tags=tags)
        elif mark == "crown":                         # the king: a full crown, three tall teeth, filled
            tooth = r * 0.95
            base, band = cy + r * 0.6, cy + r * 0.1
            c.create_polygon(cx - r, base, cx - r, band - tooth, cx - r * 0.5, band, cx, band - tooth,
                             cx + r * 0.5, band, cx + r, band - tooth, cx + r, base, fill=ink, outline="", tags=tags)
        elif mark == "small crown":                   # the heir: a narrow coronet - a band, three short teeth,
            rr = r * 0.7                                # only outlined (told apart from the king's at a glance)
            base, band = cy + r * 0.45, cy + r * 0.05
            c.create_polygon(cx - rr, base, cx - rr, band - rr * 0.45, cx - rr * 0.5, band, cx, band - rr * 0.45,
                             cx + rr * 0.5, band, cx + rr, band - rr * 0.45, cx + rr, base, fill="", outline=ink,
                             width=max(1, int(r * 0.22)), tags=tags)

    def _heart(self, cx, cy, r, ink, tags):
        pts = []
        for i in range(24):
            t = 2 * math.pi * i / 24
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts += [cx + x * r / 16, cy - y * r / 16]
        self.canvas.create_polygon(*pts, fill=ink, outline="", smooth=True, tags=tags)

    def _symbol(self, faction, px):
        path = self.symbols.get(faction)
        if not path:
            return None
        key = (faction, px)
        if key not in self._symimg:
            try:
                im = Image.open(path).convert("RGBA")
                im.thumbnail((px, px))
                self._symimg[key] = ImageTk.PhotoImage(im)
            except Exception:
                self._symimg[key] = None
        return self._symimg[key]

    # ---- resources ----
    RES_COLOURS = {"gold": "#f2c200", "silver": "#c8ccd4", "iron": "#5a5f66", "copper": "#c8743a", "tin": "#9aa3a8",
                   "lead": "#6f7488", "marble": "#f4f1ea", "wine": "#8a1f5a", "olive_oil": "#9aa832",
                   "grain": "#e6c56a", "timber": "#7a4b21", "furs": "#9b6a44", "hides": "#b3875a",
                   "slaves": "#7a1010", "pottery": "#d0612e", "glass": "#7fd6e0", "purple_dye": "#7a2ea0",
                   "dogs": "#6b5337", "elephants": "#8f8f8f", "camels": "#d9b47a", "incense": "#e8a0c0",
                   "silk": "#e04a86", "spices": "#e0621c", "textiles": "#4a78d0", "amber": "#ffa31a",
                   "wild_animals": "#4e8a3a", "fish": "#3a8fd0", "salt": "#ffffff", "coal": "#222222",
                   "sugar": "#f5f5dc", "sulfur": "#e8e04a", "tobacco": "#6b8e23", "chocolate": "#5c3317"}

    @staticmethod
    def res_colour(kind):
        """A steady colour per resource type: a fitting one for the common types,
        else one made from the name (the same type, the same colour)."""
        if kind in MapView.RES_COLOURS:
            return MapView.RES_COLOURS[kind]
        import colorsys
        h = (sum(ord(ch) * (i + 7) for i, ch in enumerate(kind)) % 360) / 360.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.85)
        return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

    @staticmethod
    def text_on(fill):
        """Black on a bright colour, white on a dark one (theme.on_colour - the one rule for every sign's letter or
        picture: a town's hall, an agent's sign, a resource's letters; Egypt's white disc hid its agents' signs)."""
        from .theme import on_colour
        return on_colour(fill)

    def _forts(self, cw, ch):
        """A fort: a small brown tower with battlements in the owner's colour (a watchtower: thinner)."""
        c = self.canvas
        editing = {r["id"] for r in self.resources} if self._marks_on() else set()
        for fo in self.forts:
            if "f%d" % fo.line in editing:              # drawn as a movable sign by the resources' code
                continue
            sx, sy = self.to_screen(*fo.xy)
            if not (-20 < sx < cw + 20 and -20 < sy < ch + 20):
                continue
            if fo.kind == "landmark":
                self._wonder_icon(c, sx, sy, max(2.5, min(self.z * 0.45, 40)), fo.type, ("fort", "fort:%d" % fo.line))
                continue
            col = self.colours.get(fo.owner) if fo.owner else None
            edge = "#%02x%02x%02x" % tuple(col) if col else "#222222"
            w = max(2.0, min(self.z * FORT_W, 36))            # inside its tile (report #125)
            self._fort_icon(c, sx, sy, w, edge, ("fort", "fort:%d" % fo.line), 2 if col else 1, fo.kind)

    @staticmethod
    def _fort_icon(c, sx, sy, w, edge, tags, width=1, kind="fort"):
        """Inside its tile: the square sx +- w, sy +- w (w = about half a tile - report #125). A fort: a stone wall
        between two square towers, the towers' battlements in the owner's colour (edge), an arched gate - no roofs,
        or it reads as a castle (report #126). A watchtower: a wooden lookout on legs, its roof in the owner's
        colour."""
        top, bottom = sy - w, sy + w
        line = max(1, width) if w >= 6 else 1                   # a thick outline would eat a small sign
        if kind == "watchtower":
            leg = max(1, int(w / 5))
            wood, dark = "#9a6a38", "#4a3018"
            for a, b in ((-0.6, -0.3), (0.6, 0.3)):             # the legs, a little apart at the foot
                c.create_line(sx + a * w, bottom, sx + b * w, sy, fill=dark, width=leg, tags=tags)
            if w >= 4:                                           # the cross brace
                c.create_line(sx - w * 0.5, bottom - w * 0.2, sx + w * 0.35, sy + w * 0.2, fill=dark, tags=tags)
                c.create_line(sx + w * 0.5, bottom - w * 0.2, sx - w * 0.35, sy + w * 0.2, fill=dark, tags=tags)
            c.create_rectangle(sx - w * 0.5, sy - w * 0.45, sx + w * 0.5, sy + w * 0.05, fill=wood, outline="black",
                               width=line, tags=tags)            # the lookout
            if w >= 4:
                c.create_rectangle(sx - w * 0.18, sy - w * 0.32, sx + w * 0.18, sy - w * 0.1, fill="#2a1f14",
                                   outline="", tags=tags)        # its window
            c.create_polygon(sx - w * 0.7, sy - w * 0.45, sx + w * 0.7, sy - w * 0.45, sx, top, fill=edge,
                             outline="black", width=line, tags=tags)   # the roof
            return
        stone, dark = "#b3ab9f", "#3a332c"
        if w < 4:                                                # far away: a block with the owner's top
            c.create_rectangle(sx - w, sy - w * 0.4, sx + w, bottom, fill=stone, outline=dark, tags=tags)
            c.create_rectangle(sx - w, top, sx + w, sy - w * 0.4, fill=edge, outline=dark, tags=tags)
            return
        c.create_rectangle(sx - w * 0.6, sy - w * 0.25, sx + w * 0.6, bottom, fill=stone, outline=dark,
                           width=line, tags=tags)                # the wall
        for k in (-1, 0, 1):                                     # its battlements
            bx = sx + k * w * 0.3
            c.create_rectangle(bx - w * 0.09, sy - w * 0.42, bx + w * 0.09, sy - w * 0.25, fill=stone, outline=dark,
                               tags=tags)
        for k in (-1, 1):                                        # the towers, their battlements as the wall's:
            x0, x1 = (sx - w, sx - w * 0.52) if k < 0 else (sx + w * 0.52, sx + w)     # stone, as long
            c.create_rectangle(x0, sy - w * 0.62, x1, bottom, fill=stone, outline=dark, width=line, tags=tags)
            m = (x1 - x0) / 5
            for n in (0, 2, 4):
                c.create_rectangle(x0 + n * m, sy - w * 0.79, x0 + (n + 1) * m, sy - w * 0.62, fill=stone,
                                   outline=dark, tags=tags)
            c.create_rectangle((x0 + x1) / 2 - w * 0.06, sy - w * 0.35, (x0 + x1) / 2 + w * 0.06, sy - w * 0.1,
                               fill="#2a1f14", outline="", tags=tags)          # an arrow slit
        r = w * 0.24                                             # the arched gate, in the owner's colour
        c.create_rectangle(sx - r, sy + w * 0.35, sx + r, bottom, fill=edge, outline="", tags=tags)
        c.create_arc(sx - r, sy + w * 0.35 - r, sx + r, sy + w * 0.35 + r, start=0, extent=180, fill=edge,
                     outline="", tags=tags)

    def _wonder_icon(self, c, sx, sy, w, kind, tags, sel=False):
        """A wonder (Rome's landmark): a golden pyramid, its type written beside it up close."""
        c.create_polygon(sx - w, sy + w * 0.7, sx + w, sy + w * 0.7, sx, sy - w, fill="#e8c34a",
                         outline="#ffd400" if sel else "#5a4300", width=3 if sel else 1, tags=tags)
        if self.z >= 10 and kind:
            c.create_text(sx + w + 3, sy, text=kind.replace("_", " "), anchor="w", fill="#3a2a00",
                          font=("", 8, "bold"), tags=tags)

    def _fort_under(self, x, y):
        return next((fo for fo in self.forts if tuple(fo.xy) == (x, y)), None)

    def _resources(self, cw, ch):
        """A small square in the type's colour with its first two letters; on a town's
        tile it sits in the tile's corner. Far out only a dot."""
        c = self.canvas
        towns = {self.places.get(("city", r), xy) for r, xy in self.cmap.cities.items()}
        for res in self.resources:
            x, y = res["xy"]
            sx, sy = self.to_screen(x, y)
            if not (-20 < sx < cw + 20 and -20 < sy < ch + 20):
                continue
            tags = ("res", "res:%s" % res["id"])
            sel = res["id"] == self.res_sel
            if res["kind"] == "landmark":
                self._wonder_icon(c, sx, sy, max(2.5, min(self.z * 0.45, 40)), res.get("type", ""), tags, sel)
                continue
            if res["kind"] in ("fort", "watchtower"):          # a fort keeps its tower, picked: a yellow frame
                w = max(2.0, min(self.z * FORT_W, 36))
                col = self.colours.get(res.get("owner")) if res.get("owner") else None   # battlements: the owner's
                self._fort_icon(c, sx, sy, w, "#%02x%02x%02x" % tuple(col) if col else "#222222", tags, 2 if col else 1,
                                res["kind"])
                if sel:
                    c.create_rectangle(sx - w - 2, sy - w - 2, sx + w + 2, sy + w + 2, outline="#ffd400",
                                       width=3, tags=tags)
                continue
            fill = self.res_colour(res["kind"])
            if self.z < 6:
                r = max(2, self.z * 0.35)
                c.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill=fill, outline="#ffd400" if sel else "",
                                   tags=tags)
                continue
            r = min(self.z * 0.42, 40)                 # grows with the tile (a tester: it looked to shrink)
            if (x, y) in towns:                        # beside the town, at the tile's corner
                sx, sy = sx + self.z * 0.35, sy - self.z * 0.35
                r *= 0.6
            c.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill=fill,
                               outline="#ffd400" if sel else "black", width=3 if sel else 1, tags=tags)
            if r >= 5:
                c.create_text(sx, sy, text=res["kind"][:2].capitalize(), fill=self.text_on(fill),
                              font=("", max(6, int(r * 0.8)), "bold"), tags=tags)

    def _marks_on(self):
        """Edit resources (or the forts, always): their markers are drawn to be picked, moved and placed."""
        return self.v_res.get() or self.v_forts.get()

    def _fort_line_under(self, sx, sy):
        """The descr_strat line of the fort / watchtower / wonder sign under the mouse (screen point), or None."""
        for item in reversed(self.canvas.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("fort:"):
                    try:
                        return int(tag[5:])
                    except ValueError:
                        return None
        return None

    def _double(self, e):
        town = self._town_under(e.x, e.y)
        if town and self.on_town and not self.v_pick.get():
            self.on_town(town[0])                        # a town: straight to its own window (a tester)
            return
        cid = self._char_under(e.x, e.y)
        if cid and self.on_char_double and not self.v_pick.get():
            self.on_char_double(cid)                     # an army / fleet: its units (reports #102 #104)
            return
        line = self._fort_line_under(e.x, e.y)
        fo = next((f for f in (self.forts or []) if f.line == line), None) if line is not None else None
        if fo is None:                                   # drawn as a movable sign (forts are always movable on the
            rid = self._res_under(e.x, e.y)              # Map editor): its resource-layer id, f<line> / g<new one>
            r = next((r for r in self.resources if r["id"] == rid), None) if rid and rid[:1] in ("f", "g") else None
            if r is not None:
                fo = next((f for f in (self.forts or []) if "f%d" % f.line == rid), None)
                if fo is None:
                    from types import SimpleNamespace
                    fo = SimpleNamespace(kind=r.get("kind"), type=r.get("type", ""), xy=tuple(r["xy"]), line=None,
                                         owner=r.get("owner"))
        if fo is not None and fo.kind == "landmark" and self.on_wonder:
            self.on_wonder(fo.type)
        elif fo is not None and self.on_fort_double:
            self.on_fort_double(fo)                      # a fort: the army that holds it

    def _res_under(self, sx, sy):
        if not self._marks_on():
            return None
        for item in reversed(self.canvas.find_overlapping(sx - 2, sy - 2, sx + 2, sy + 2)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("res:"):
                    return tag[4:]
        return None

    def _char_under(self, sx, sy):
        for item in reversed(self.canvas.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("char:"):
                    return tag[5:]
        return None

    def _marker_under(self, sx, sy):
        """The tag of the town or character under the mouse: 'char:<id>' or 'city:<region>'."""
        for item in reversed(self.canvas.find_overlapping(sx - 3, sy - 3, sx + 3, sy + 3)):
            for tag in self.canvas.gettags(item):
                if tag.startswith(("char:", "city:")):
                    return tag
        return None

    GROW = 1.6

    def _aura(self):
        """How far (screen pixels) round a sign the mouse already makes it grow: wider when the map is far out and
        the signs are small (a tester: one should not have to hit the sign itself)."""
        return max(8.0, min(28.0, 34.0 - self.z * 1.2))

    def _marker_near(self, sx, sy):
        """(tag, how near 0..1) of the town, port or character sign nearest the mouse within its aura, or (None, 0)
        (a tester: the port's anchor did not grow like the rest)."""
        r = self._aura()
        c = self.canvas
        best = None
        if self._hot:                                    # the grown sign: measured at its normal size
            hb = c.bbox(self._hot)
        for item in c.find_overlapping(sx - r, sy - r, sx + r, sy + r):
            for tag in c.gettags(item):
                if not tag.startswith(("char:", "city:", "port:")):
                    continue
                box = c.bbox(tag)
                if not box:
                    continue
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                half = max(box[2] - box[0], box[3] - box[1]) / 2
                if tag == self._hot and hb:
                    half /= self._hot_k or 1
                d = max(0.0, ((cx - sx) ** 2 + (cy - sy) ** 2) ** 0.5 - half)
                if d <= r and (best is None or d < best[1]):
                    best = (tag, d)
        if not best:
            return None, 0.0
        return best[0], 1.0 - best[1] / r

    def _ghost(self, sx, sy):
        """What is being placed, under the mouse: green frame where it may go, red where not."""
        c = self.canvas
        c.delete("ghost")
        g = self.ghost
        if not g or not self.cmap:
            return
        xy = self.to_tile(sx, sy)
        why = self._outside(xy) or (g["check"](xy) if g.get("check") else None)
        cx, cy = self.to_screen(*xy)
        size = max(8, min(self.z * 0.9, 60))
        r = size / 2
        edge = "#ff3030" if why else "#30ff60"
        tags = ("ghost",)
        kind = g.get("kind")
        if kind == "city":
            c.create_rectangle(cx - r, cy - r, cx + r, cy + r, fill="#d8c080", stipple="gray50", outline=edge,
                               width=2, tags=tags)
            if r >= 6:
                self._hall(cx, cy, r, (216, 192, 128), tags)
        elif kind == "port":
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#2a6fdb", stipple="gray50", outline=edge, width=2,
                          tags=tags)
            if r >= 5:
                self._anchor(cx, cy, r, tags)
        elif kind in ("army", "fleet"):
            h = size
            c.create_line(cx - h * 0.3, cy + h * 0.5, cx - h * 0.3, cy - h * 0.5, fill=edge, width=2, tags=tags)
            c.create_polygon(cx - h * 0.3, cy - h * 0.5, cx + h * 0.4, cy - h * 0.25, cx - h * 0.3, cy,
                             fill=edge, stipple="gray50", outline=edge, tags=tags)
        elif kind in ("fort", "watchtower"):            # held in the hand: the sign itself, framed green / red
            w = max(4.0, min(self.z * FORT_W, 36))
            self._fort_icon(c, cx, cy, w, "#222222", tags, 1, kind)
            c.create_rectangle(cx - w - 2, cy - w - 2, cx + w + 2, cy + w + 2, outline=edge, width=2, tags=tags)
        elif kind == "landmark":
            rr = max(5, min(self.z * 0.45, 40))
            self._wonder_icon(c, cx, cy, rr, g.get("type", ""), tags, False)
            c.create_rectangle(cx - rr - 3, cy - rr - 3, cx + rr + 3, cy + rr + 3, outline=edge, width=2, tags=tags)
        elif kind == "resource":
            rr = max(5, min(self.z * 0.42, 40))
            fill = self.res_colour(g.get("type", ""))
            c.create_rectangle(cx - rr, cy - rr, cx + rr, cy + rr, fill=fill, outline=edge, width=2, tags=tags)
            c.create_text(cx, cy, text=(g.get("type") or "")[:2].capitalize(), fill=self.text_on(fill),
                          font=("", max(6, int(rr * 0.8)), "bold"), tags=tags)
        elif g.get("char"):                              # an agent: its own sign (spy, priest...)
            self._draw_char({"id": "ghost", "faction": g.get("faction") or "slave", "kind": g["char"],
                             "army": False, "name": ""}, cx, cy, max(14, min(self.z * 0.9, 40)))
            for item in c.find_withtag("char:ghost"):
                c.addtag_withtag("ghost", item)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=edge, width=2, tags=tags)
        else:
            c.create_oval(cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6, fill=edge, stipple="gray50",
                          outline=edge, width=2, tags=tags)
        if why:
            c.create_text(cx + r + 4, cy, text=why, anchor="w", fill="#ff5050", font=("", 9, "bold"), tags=tags)

    def _outline(self, sx, sy):
        """The edges of the tile under the mouse, like a block outline in Minecraft."""
        c = self.canvas
        c.delete("tile_outline")
        if not self.cmap or self.z < 3:
            return
        x, y = self.to_tile(sx, sy)
        cx, cy = self.to_screen(x, y)
        h = self.z / 2
        c.create_rectangle(cx - h, cy - h, cx + h, cy + h, outline="white", width=2 if self.z >= 12 else 1,
                           tags="tile_outline")
        c.tag_lower("tile_outline", "city") if c.find_withtag("city") else None

    def _grow(self, tag, near=1.0):
        """Draw the marker near the mouse bigger (and on top) - the nearer, the bigger, softly (near 0..1 within its
        aura); put the last one back."""
        k = 1.0 + (self.GROW - 1.0) * max(0.0, min(1.0, near)) if tag else 1.0
        old = getattr(self, "_hot_k", 1.0) or 1.0
        if tag == self._hot and abs(k - old) < 0.04:
            return
        c = self.canvas
        if self._hot and (tag != self._hot):
            box = c.bbox(self._hot)
            if box:
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                c.scale(self._hot, cx, cy, 1 / old, 1 / old)
            old = 1.0
        self._hot = tag
        self._hot_k = k if tag else 1.0
        if tag:
            box = c.bbox(tag)
            if box:
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                c.scale(tag, cx, cy, k / old, k / old)
                c.tag_raise(tag)

    # ---- mouse ----
    # ---- Find ----
    def find_items(self):
        """[(text, xy, name)] of everything on the map one may look for: towns (the shown name too), ports,
        characters with their faction and the units of their army, forts, resources. name: what the thing
        is called (a hit there comes first)."""
        if not self.cmap:
            return []
        out = []
        read = getattr(self, "shown_names", {}) or {}   # the names players read ({Roma} Roma) beside the files'
        for region, xy in self.cmap.cities.items():
            town = self.cmap.info.get(region, {}).get("settlement", "")
            shown = self.labels.get(region) or read.get(town)
            land = read.get(region)
            owner = self.owners.get(region)
            out.append(("town %s%s - region %s%s%s" % (
                town, " (shown: %s)" % shown if shown and shown != town else "", region,
                " (shown: %s)" % land if land and land != region else "", ", %s" % owner if owner else ""),
                tuple(xy), " ".join(x for x in (town, shown or "", region, land or "") if x)))
        for region, xy in self.cmap.ports.items():
            town = self.cmap.info.get(region, {}).get("settlement", region)
            out.append(("port of %s (%s)" % (town, region), tuple(xy), "%s %s" % (town, region)))
        for c in self.chars:
            what = "fleet" if c["kind"] == "admiral" else "army" if c["army"] else c["kind"]
            units = c.get("unit_names") or []
            text = "%s - %s of %s" % (c["name"] or "(no name)", what, c["faction"])
            if units:
                text += " - " + ", ".join(units)
            out.append((text, tuple(c["xy"]), c["name"] or ""))
        for f in self.forts:
            out.append(("%s%s of %s" % (f.kind, " '%s'" % f.name if f.name else "", f.owner or "no faction"),
                        tuple(f.xy), f.name or f.kind))
        for r in self.resources:
            out.append(("resource %s - %s" % (r["kind"], self.cmap.region_at(*r["xy"]) or ""), tuple(r["xy"]),
                        r["kind"]))
        return out

    def _find_typed(self, e=None):
        if e is not None and e.keysym in ("Return", "Down", "Escape", "Up"):
            return
        words = self.v_find.get().lower().split()
        if not words:
            return self._find_close()
        hits = [h for h in self.find_items() if all(w in h[0].lower() for w in words)]

        def rank(h):
            name = h[2].lower().replace("_", " ").split()
            text = h[0].lower().replace("-", " ").replace("_", " ").split()
            # the name itself first (typing "rom" finds the town Roma before the Romans' armies), then a word
            # starting so, then the rest
            return (0 if any(p.startswith(words[0]) for p in name) else
                    1 if any(p.startswith(words[0]) for p in text) else 2,
                    not h[0].startswith("town "), h[0].lower())     # a town before its own port
        hits.sort(key=rank)
        self._found = [(t, xy) for t, xy, _ in hits[:200]]
        lb = self.find_list
        lb.delete(0, "end")
        if not hits:
            lb.insert("end", "nothing on the map is called so")
        for t, xy in self._found:
            lb.insert("end", "%s   (%d, %d)" % (t, xy[0], xy[1]))
        if len(hits) > len(self._found):
            lb.insert("end", "... %d more - type more of the name" % (len(hits) - len(self._found)))
        lb.configure(height=min(12, max(1, lb.size())))
        lb.place(x=4, y=4)
        lb.lift()

    def _find_focus(self):
        if self._found and self.find_list.winfo_ismapped():
            self.find_list.focus_set()
            self.find_list.selection_clear(0, "end")
            self.find_list.selection_set(0)
            self.find_list.activate(0)

    def _find_go(self, index):
        if index is None:
            sel = self.find_list.curselection()
            index = sel[0] if sel else None
        if index is None or index >= len(self._found):
            return
        text, xy = self._found[index]
        self._find_close()
        self.centre_on(xy, zoom=32)                     # close enough to see the flag, the town and its tile
        self.readout.configure(text="found: %s at %d, %d" % (text, xy[0], xy[1]))

    def _find_close(self):
        self.find_list.place_forget()

    def _wheel(self, e, direction=None):
        d = direction if direction is not None else (1 if e.delta > 0 else -1)
        state = getattr(e, "state", 0) or 0
        if state & 0x0001:                              # Shift: slow and smooth - small steps, drawn one by one
            self._glide(d, (e.x, e.y))
            return
        self.zoom_by(d, (e.x, e.y), by=zoom_setting("map_zoom_step_fine") if state & 0x0004 else None)

    def _glide(self, d, at):
        """Shift + wheel: the zoom slides 1 % at a time over a few frames, so it moves slowly and smoothly."""
        left = getattr(self, "_glide_left", 0)
        self._glide_left = left + 3 * d if (left == 0 or (left > 0) == (d > 0)) else 3 * d
        if left:
            return                                      # already sliding: it goes on with the new notches

        def tick():
            n = self._glide_left
            if not n or not self.winfo_exists():
                self._glide_left = 0
                return
            one = 1 if n > 0 else -1
            self._glide_left = n - one
            self.zoom_by(one, at, by=1)
            self.after(16, tick)
        tick()

    def _place_under(self, sx, sy):
        """('city' | 'port', region) of the town or port under the mouse, or None."""
        for item in reversed(self.canvas.find_overlapping(sx - 2, sy - 2, sx + 2, sy + 2)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("char:"):
                    return None
                if tag.startswith(("city:", "port:")):
                    return tag[:4], tag[5:]
        return None

    def _show_menu(self, e):
        """The right-click menu: what can be done at that spot (a town, a character, an empty tile)."""
        xy = self.to_tile(e.x, e.y)
        if not self.inside(xy):
            return
        town = self._town_under(e.x, e.y)
        if self.v_pick.get() and self.on_pick_menu:
            items = self.on_pick_menu(self.picked, town[0] if town else None) or []
        else:
            cid = self._char_under(e.x, e.y)
            self.menu_res = self._res_under(e.x, e.y)          # a resource / fort / tower under the mouse
            self.menu_fort = self._fort_line_under(e.x, e.y)        # a fort / tower / wonder sign (also when not editing)
            under = self._place_under(e.x, e.y)
            self.menu_port = under[1] if under and under[0] == "port" else None
            items = self.on_menu(town[1] if town else xy, town[0] if town else None, cid) or []
        m = tk.Menu(self, tearoff=0)
        for label, fn in items:
            if label is None:
                m.add_separator()
            elif isinstance(fn, list):                   # a sub-menu: [(label, command)]
                sub = tk.Menu(m, tearoff=0)
                for sl, sf in fn:
                    sub.add_command(label=sl, command=sf)
                m.add_cascade(label=label, menu=sub)
            else:
                m.add_command(label=label, command=fn, state="normal" if fn else "disabled")
        if items:
            m.add_separator()
        m.add_command(label="Centre the map here", command=lambda: self.centre_on(xy, zoom=self.z))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def place_at(self, xy):
        """What a click does while a tool is picked: place it on tile xy (a character that may not stand
        there goes to the nearest good tile). Returns True when it was placed."""
        if not self.on_place:
            return False
        if not self.inside(xy):
            self.readout.configure(text="cannot place here - outside the map")
            return False
        why = self.on_place(xy)
        if why and self.ghost and self.ghost.get("kind") in ("army", "agent", "fleet") and self.ghost.get("check"):
            alt = self.nearest(self.ghost["check"], xy)       # a character: the nearest good tile
            if alt is not None and not self.on_place(alt):
                self.readout.configure(text="tile %d, %d: %s - placed on the nearest good tile %d, %d" % (
                    xy[0], xy[1], why, alt[0], alt[1]))
                return True
        if why:
            self.readout.configure(text="cannot place here - " + why)
            return False
        return True

    def _town_under(self, sx, sy):
        """(region, its town tile) when a town's sign is under the screen point, else None: a character
        dropped on the sign goes into the town even when the sign is drawn bigger than its tile."""
        if not self.cmap:
            return None
        for item in reversed(self.canvas.find_overlapping(sx - 2, sy - 2, sx + 2, sy + 2)):
            for tag in self.canvas.gettags(item):
                if tag.startswith("city:") and tag[5:] in self.cmap.cities:
                    r = tag[5:]
                    return r, tuple(self.places.get(("city", r), self.cmap.cities[r]))
        return None

    def _char_target(self, cid, sx, sy):
        """The tile a dragged character goes to: the town under it when it may stand there, else the tile."""
        town = self._town_under(sx, sy)
        if town and not (self.check_tile and self.check_tile(cid, town[1])):
            return town[1], town[0]
        return self.to_tile(sx, sy), None

    def _press(self, e, icons=False):
        right = getattr(e, "num", None) == 3
        self._nopan = False
        # a right click that does not move opens the menu of what can be done there (see _release)
        self._menu_press = (e.x, e.y) if right and not self.region_mode else None
        if right and not self.region_mode:                # the right button drags the map, everywhere
            self._drag = (e.x, e.y, self.ox, self.oy, False)
            return
        if self.v_pick.get() and self.cmap and not self.region_mode and not self.on_place:
            cid = self._char_under(e.x, e.y)              # Select: the left button drags a sign of one's own,
            if cid is None or cid not in self.draggable:  # else draws a box (it adds; Shift takes away)
                self._box = [e.x, e.y, False, bool(getattr(e, "state", 0) & 0x1)]
                return
            self._cdrag = (cid, e.x, e.y)
            return
        if self.region_mode and self.cmap:
            icons = right                                 # the region tools: left paints, right as before
            if not icons and not self.on_place:           # left: paint
                if getattr(self, "on_stroke", None):
                    self.on_stroke()                      # one Undo step per stroke
                if self.on_spray:
                    self._spray = (e.x, e.y)
                    self._spray_tick()
                    return
                self._painting = True
                self._paint_at(e)
                return
            if icons:                                     # right: drag the map, or a click picks the region
                self._rclick = True
                self._drag = (e.x, e.y, self.ox, self.oy, False)
                return
        if icons and self.cmap and self.on_res_move:
            rid = self._res_under(e.x, e.y)
            if rid is not None:
                self._rdrag = [rid, e.x, e.y, False]
                return
        if self.cmap:
            self._rpress = self._res_under(e.x, e.y)      # a click (no drag) on a resource picks it
        cid = self._char_under(e.x, e.y) if self.cmap and not self.on_place else None
        if cid is not None and cid in self.draggable:
            self._cdrag = (cid, e.x, e.y)
            return
        if cid is not None and self.locked:
            ch_ = next((c for c in self.chars if c["id"] == cid), None)
            if ch_:
                self.readout.configure(text=self.locked(ch_))
        pl = self._place_under(e.x, e.y) if self.cmap and self.on_place_move and not self.on_place else None
        if pl:
            self._pdrag = [pl[0], pl[1], e.x, e.y, False]          # nothing happens unless the mouse moves
            return
        self._nopan = True                                # a left click: a pick, the map stays where it is
        self._drag = (e.x, e.y, self.ox, self.oy, False)

    def _spray_at(self, sx, sy):
        """Canvas point -> map_heights pixel (bottom-up, with fractions): tile x spans pixels 2x..2x+2."""
        fx = self.ox + sx / self.z
        fr = self.oy + sy / self.z
        return 2 * fx, 2 * (self.cmap.h - fr)

    def _spray_tick(self):
        if not self._spray or not self.cmap or not self.on_spray:
            self._spray = None
            return
        if self.on_spray(*self._spray_at(*self._spray)):
            self._refresh_bg()
        self.after(50, self._spray_tick)

    def _refresh_bg(self):
        """Only the background again (the markers stay): quick enough to follow a spraying brush."""
        c = self.canvas
        if not self.cmap or not c.find_withtag("bg"):
            return self.render()
        cw, ch = c.winfo_width(), c.winfo_height()
        box = (self.ox, self.oy, self.ox + cw / self.z, self.oy + ch / self.z)
        pic = view_of(self._base(), box, (cw, ch), Image.NEAREST, self._field())
        self._photo = ImageTk.PhotoImage(pic)
        c.itemconfigure("bg", image=self._photo)

    def _move(self, e):
        if self._box:
            x0, y0, moved, add = self._box
            if moved or abs(e.x - x0) + abs(e.y - y0) > 3:
                self._box[2] = True
                self.canvas.delete("selbox")
                self.canvas.create_rectangle(x0, y0, e.x, e.y, outline="#ffd400", dash=(4, 3), width=2,
                                             tags=("selbox",))
            return
        if self._spray:
            self._spray = (e.x, e.y)
            return
        if self._painting:
            self._paint_at(e)
            return
        if self._rdrag:
            rid, lx, ly, started = self._rdrag
            if not started and abs(e.x - lx) + abs(e.y - ly) <= 3:
                return
            self.canvas.move("res:" + rid, e.x - lx, e.y - ly)
            self._rdrag = [rid, e.x, e.y, True]
            x, y = self.to_tile(e.x, e.y)
            why = self._outside((x, y)) or (self.check_res(rid, (x, y)) if self.check_res else None)
            self.canvas.delete("target")
            ax, ay = self.to_screen(x, y)
            r = max(self.z / 2, 4)
            self.canvas.create_rectangle(ax - r, ay - r, ax + r, ay + r, outline="#ff3030" if why else "#30ff60",
                                         width=2, tags=("target",))
            self.readout.configure(text="resource to tile %d, %d: %s" % (x, y, why or "fine - drop it here"))
            return
        if getattr(self, "_pdrag", None):
            what, region, lx, ly, started = self._pdrag
            if not started and abs(e.x - lx) + abs(e.y - ly) <= 3:
                return
            self._grow(None)
            self.canvas.move("%s:%s" % (what, region), e.x - lx, e.y - ly)
            self._pdrag = [what, region, e.x, e.y, True]
            x, y = self.to_tile(e.x, e.y)
            why = self.check_place(what, region, (x, y)) if self.check_place else None
            self.canvas.delete("target")
            ax, ay = self.to_screen(x, y)
            r = max(self.z / 2, 4)
            self.canvas.create_rectangle(ax - r, ay - r, ax + r, ay + r, outline="#ff3030" if why else "#30ff60",
                                         width=2, tags=("target",))
            self.readout.configure(text=("%s of %s to tile %d, %d: " % ("town" if what == "city" else "port",
                                   region, x, y)) + (why or "fine - drop it here"))
            return
        if self._cdrag:
            cid, lx, ly = self._cdrag
            self.canvas.move("char:" + cid, e.x - lx, e.y - ly)
            self._cdrag = (cid, e.x, e.y)
            (x, y), town = self._char_target(cid, e.x, e.y)
            why = self.check_tile(cid, (x, y)) if self.check_tile else None
            self.canvas.delete("target")
            ax, ay = self.to_screen(x, y)
            r = max(self.z / 2, 4)
            self.canvas.create_rectangle(ax - r, ay - r, ax + r, ay + r, outline="#ff3030" if why else "#30ff60",
                                         width=2, tags=("target",))
            self.readout.configure(text=("tile %d, %d: " % (x, y)) + (
                why + " - dropped here it goes to the nearest good tile" if why else
                "into the town of %s - drop it here" % town if town else "fine - drop it here"))
            return
        if not self._drag or not self.cmap:
            return
        x0, y0, ox, oy, _ = self._drag
        if getattr(self, "_nopan", False):
            return
        if abs(e.x - x0) + abs(e.y - y0) > 3:
            self._drag = (x0, y0, ox, oy, True)
            self.ox, self.oy = ox - (e.x - x0) / self.z, oy - (e.y - y0) / self.z
            if self._pending is None:
                self._pending = self.after(15, self._pan)

    def _release(self, e):
        if self._box:
            x0, y0, moved, add = self._box
            self._box = None
            self.canvas.delete("selbox")
            if moved:
                self.select_box((x0, y0), (e.x, e.y), remove=add)       # (Shift held: take away)
            else:
                self._click_select(e.x, e.y, remove=add)
            return
        if self._spray:
            self._spray = None
            self.render()
            return
        if self._painting:
            self._painting = False
            self.render()
            return
        mp, self._menu_press = self._menu_press, None
        if getattr(e, "num", None) == 3 and not self.region_mode:     # the right button: the map was dragged, or
            moved = self._drag and self._drag[4]                       # a click - the menu / stop placing
            self._drag = None
            if moved:
                self.render()
                return
            if mp and self.on_place and self.on_place_stop:            # a right click stops what hangs under the mouse
                self.on_place_stop()
            elif mp and self.on_menu and self.cmap:
                self._cdrag = self._rdrag = self._pdrag = None
                self.canvas.delete("target")
                self._show_menu(e)
            return
        if self._rclick:
            self._rclick = False
            moved = self._drag and self._drag[4]
            self._drag = None
            if moved:
                self.render()
            elif self.waiting and self.on_place_stop:  # a town / port waiting for its click: put back
                self.on_place_stop()
            elif self.on_pick and self.inside(self.to_tile(e.x, e.y)):
                self.on_pick(self.to_tile(e.x, e.y))
            return
        if self._rdrag:
            rid, _, _, started = self._rdrag
            self._rdrag = None
            if started:
                xy = self.to_tile(e.x, e.y)
                why = self._outside(xy) or (self.check_res(rid, xy) if self.check_res else None)
                if why:
                    self.readout.configure(text="not moved - " + why)
                    self.render()
                else:
                    self.on_res_move(rid, xy)
            elif self.on_res_click:
                self.on_res_click(rid)
            return
        rpress, self._rpress = self._rpress, None
        if getattr(self, "_pdrag", None):
            what, region, _, _, started = self._pdrag
            self._pdrag = None
            if started:
                xy = self.to_tile(e.x, e.y)
                why = self._outside(xy) or (self.check_place(what, region, xy) if self.check_place else None)
                if why:
                    self.readout.configure(text="not moved - " + why)
                    self.render()
                else:
                    self.on_place_move(what, region, xy)
                return
            return
        if self._cdrag:
            cid = self._cdrag[0]
            self._cdrag = None
            xy, town = self._char_target(cid, e.x, e.y)
            why = self._outside(xy) or (self.check_tile(cid, xy) if self.check_tile else None)
            note = None
            if why:
                alt = self.nearest(lambda p: self._outside(p) or self.check_tile(cid, p), xy)
                if alt is None:
                    self.readout.configure(text="not moved - " + why)
                    self.render()
                    return
                note = "tile %d, %d: %s - put on the nearest good tile %d, %d" % (xy[0], xy[1], why, alt[0], alt[1])
                xy = alt
            if self.on_char_move:
                self.on_char_move(cid, xy)
            self.render()
            if note:
                self.readout.configure(text=note)
            return
        moved = self._drag and self._drag[4]
        self._drag = None
        if moved:
            self.render()                                # the smooth picture once the map stops
        if moved or not self.cmap:
            return
        if rpress is not None and self.on_res_click and not self.on_place:
            self.on_res_click(rpress)
            return
        if self.on_place:
            self.place_at(self.to_tile(e.x, e.y))
            return
        hit = self.canvas.find_overlapping(e.x - 2, e.y - 2, e.x + 2, e.y + 2)
        if self.v_pick.get():                           # (a double click's second press comes here)
            self._click_select(e.x, e.y)
            return
        for item in reversed(hit):
            for tag in self.canvas.gettags(item):
                if tag.startswith("city:") and self.on_city:
                    self.on_city(tag[5:])
                    return

    @staticmethod
    def nearest(check, xy, reach=3):
        """The nearest tile to xy (ring by ring, the four sides first) that check() accepts, or None."""
        x, y = xy
        for d in range(1, reach + 1):
            ring = [(dx, dy) for dx in range(-d, d + 1) for dy in range(-d, d + 1) if max(abs(dx), abs(dy)) == d]
            ring.sort(key=lambda t: abs(t[0]) + abs(t[1]))
            for dx, dy in ring:
                p = (x + dx, y + dy)
                if not check(p):
                    return p
        return None

    def _hover(self, e):
        if self.cmap and self.on_place and not self._cdrag:
            self._outline(e.x, e.y)
            self._ghost(e.x, e.y)
            x, y = self.to_tile(e.x, e.y)
            self.canvas.config(cursor="hand2")
            self.readout.configure(text="click to place   " + self.cmap.describe(x, y, self.owners))
            return
        self.canvas.config(cursor="crosshair")
        self.canvas.delete("ghost")
        self._outline(e.x, e.y)
        if self.cmap and not self._cdrag:
            self._grow(*self._marker_near(e.x, e.y))
            rid = self._res_under(e.x, e.y)
            res = next((r for r in self.resources if r["id"] == rid), None) if rid else None
            if res:
                x, y = res["xy"]
                self.readout.configure(text="%s at %d, %d - %s   (click: pick it; right drag: move it)" % (
                    res["kind"], x, y, self.cmap.region_at(x, y) or next(
                        (r for r, t in self.cmap.cities.items() if t == (x, y)), "no region")))
                return
            cid = self._char_under(e.x, e.y)
            ch_ = next((c for c in self.chars if c["id"] == cid), None) if cid else None
            if ch_:
                self.readout.configure(text="%s - %s of %s%s%s" % (
                    ch_["name"], ch_["kind"], ch_["faction"],
                    ", %d unit(s)" % ch_["units"] if ch_["army"] else "",
                    "   (drag to move)" if cid in self.draggable else ""))
                return
            x, y = self.to_tile(e.x, e.y)
            text = self.cmap.describe(x, y, self.owners)
            fo = self._fort_under(x, y)
            if fo:
                text += "   %s%s%s of %s%s" % (fo.kind, " '%s'" % fo.name if fo.name else "",
                                            " (permanent)" if fo.permanent else "", fo.owner or "no faction",
                                            " - no one may start on it")
            here = [c for c in self.chars if tuple(c["xy"]) == (x, y)]
            if here:                                   # who is in the town: army first, then agents
                here.sort(key=lambda c: not c["army"])
                text += "   in it: " + ", ".join("%s (%s%s)" % (c["name"], c["kind"], ", %d units" % c["units"]
                                                             if c["army"] else "") for c in here)
            self.readout.configure(text=text)
