"""Terrain > Climates > Climate library...: every climate of the mod with how much of the map it covers, and its
passport - what it gives the campaign map (colour, heat, winter, trees, ground textures), the mountains, the battle
map, the weather and sounds - file by file and line by line, pictures shown (climatelib). Looking only: nothing is
written here."""

import tkinter as tk
from tkinter import ttk

from . import climatelib as L
from .gui_util import one_window, tip


@one_window
class ClimateLibrary(tk.Toplevel):
    def __init__(self, app, mod, campaign, pick=None):
        super().__init__(app)
        self.app, self.mod, self.campaign = app, mod, campaign
        from .limits import game_kind
        self.game = game_kind(mod)
        self.title("Climate library")
        self.transient(app)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d" % (min(1100, sw - 40), min(680, sh - 100)))
        self.minsize(min(640, sw - 40), min(360, sh - 100))
        self._photo = None
        bar = ttk.Frame(self, padding=8)
        bar.pack(side="bottom", fill="x")
        self.lbl_free = ttk.Label(bar)
        self.lbl_free.pack(side="left")
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
        panes = ttk.PanedWindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        left = ttk.Frame(panes)
        panes.add(left, weight=1)
        ttk.Label(left, text="Climates of this mod (descr_climates.txt):").pack(anchor="w")
        self.climates = ttk.Treeview(left, columns=("slot", "tiles"), show="tree headings", height=16,
                                     selectmode="browse")
        self.climates.heading("#0", text="climate")
        self.climates.heading("slot", text="slot")
        self.climates.heading("tiles", text="tiles")
        self.climates.column("#0", width=210)
        self.climates.column("slot", width=40, anchor="e", stretch=False)     # the numbers always whole; a long
        self.climates.column("tiles", width=60, anchor="e", stretch=False)    # name is cut, not them
        sb = ttk.Scrollbar(left, orient="vertical", command=self.climates.yview)
        self.climates.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.climates.pack(fill="both", expand=True)
        self.climates.bind("<<TreeviewSelect>>", lambda e: self.show())

        right = ttk.Frame(panes)
        panes.add(right, weight=3)
        self.lbl_head = ttk.Label(right, font=("", 11, "bold"))
        self.lbl_head.pack(anchor="w")
        tip(ttk.Label(right, text="What this climate gives the game, file by file (grey: the game's own file under "
                                  "the mod, not the mod's copy). Pick a row to see its picture.", wraplength=640,
                      foreground="#777"),
            "A climate is not one switch: map_climates.tga picks it by colour (descr_climates.txt), and every file "
            "below finds its own block or line by the climate's NAME. The battle files may use the engine's slot "
            "name instead (the climate's place in descr_climates.txt's 'climates' list) - both are looked for. "
            "'from default': descr_aerial_map_ground_types.txt has no block for this climate, so the game takes "
            "its 'default' block's texture.").pack(anchor="w", fill="x")
        body = ttk.PanedWindow(right, orient="vertical")
        body.pack(fill="both", expand=True, pady=(4, 0))
        tbox = ttk.Frame(body)
        body.add(tbox, weight=3)
        self.rows = ttk.Treeview(tbox, columns=("value", "where"), show="tree headings", selectmode="browse")
        self.rows.heading("#0", text="what")
        self.rows.heading("value", text="value")
        self.rows.heading("where", text="file : line")
        self.rows.column("#0", width=240)
        self.rows.column("value", width=360)
        self.rows.column("where", width=230)
        self.rows.tag_configure("game", foreground="#888")
        self.rows.tag_configure("note", foreground="#a06000")
        sb2 = ttk.Scrollbar(tbox, orient="vertical", command=self.rows.yview)
        self.rows.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self.rows.pack(fill="both", expand=True)
        self.rows.bind("<<TreeviewSelect>>", lambda e: self.picture())
        pbox = ttk.Frame(body, padding=(0, 4))
        body.add(pbox, weight=1)
        self.pic = ttk.Label(pbox, anchor="w")
        self.pic.pack(side="left")
        self.lbl_pic = ttk.Label(pbox, wraplength=420, justify="left")
        self.lbl_pic.pack(side="left", fill="x", expand=True, padx=8)
        self._row_of = {}
        self.fill(pick)
        self.after(60, lambda: panes.sashpos(0, 360))          # the climates' names and counts whole

    def fill(self, pick=None):
        """The climates list: each in its colour, its slot and the tiles of this campaign's map it covers."""
        from . import terrain as T
        path = self.mod.find("descr_climates.txt")
        lines = self.mod.load(path).texts() if path else []
        order = L.listed(lines)
        cover = L.coverage(self.mod, self.campaign)
        first = None
        for name, colour, heat in T.climates(self.mod):
            tag = "c%02x%02x%02x" % colour
            self.climates.tag_configure(tag, background="#%02x%02x%02x" % colour,
                                        foreground="#000" if sum(colour) > 380 else "#fff")
            slot = str(order.index(name) + 1) if name in order else "-"
            self.climates.insert("", "end", iid=name, text=name, values=(slot, str(cover.get(colour, 0))), tags=(tag,))
            first = first or name
        free = L.free_slots(lines, self.game) if lines else []
        self.lbl_free.configure(text=(
            "%d of %d climate slots used; %d free with %s (%s ...)." % (len(order), L.SLOTS, len(free),
                                                                     "M2EX" if self.game == "medieval2" else "REX",
                                                                     free[0][1]) if free else
            "%d climates." % len(order)))
        want = pick if pick and self.climates.exists(pick) else first
        if want:
            self.climates.selection_set(want)
            self.climates.see(want)

    def show(self):
        sel = self.climates.selection()
        if not sel:
            return
        name = sel[0]
        self.rows.delete(*self.rows.get_children())
        self._row_of = {}
        try:
            rows = L.passport(self.mod, name, self.game)
        except Exception as e:                                       # a file the reader chokes on: said, not a crash
            self.lbl_head.configure(text="%s: could not be read (%s)" % (name, e))
            return
        self.lbl_head.configure(text="%s - %d lines in %d files" % (name, len(rows), len({r.file for r in rows})))
        sections, files = {}, {}
        for s in L.SECTIONS:
            if any(r.section == s for r in rows):
                sections[s] = self.rows.insert("", "end", text=s, open=s in ("Campaign map", "Mountains and hills"))
        for r in rows:
            key = (r.section, r.file if r.section != "Mountains and hills" else "")
            parent = sections[r.section]
            if r.section != "Mountains and hills" and r.file not in ("descr_climates.txt",
                                                                     "descr_aerial_map_ground_types.txt"):
                if key not in files:
                    files[key] = self.rows.insert(parent, "end", text=r.file, open=False,
                                                  tags=() if r.own else ("game",))
                parent = files[key]
            iid = self.rows.insert(parent, "end", text=r.what, values=(
                r.value + ("   (%s)" % r.note if r.note else ""), "%s : %d" % (r.file, r.line) if r.line else r.file),
                tags=("note",) if r.note else () if r.own else ("game",))
            self._row_of[iid] = r
        self.pic.configure(image="")
        self.lbl_pic.configure(text="")

    def picture(self):
        sel = self.rows.selection()
        r = self._row_of.get(sel[0]) if sel else None
        self.pic.configure(image="")
        self._photo = None
        if r is None:
            self.lbl_pic.configure(text="")
            return
        where = "%s, line %d (%s)" % (r.file, r.line, "the mod's own file" if r.own else "the game's file") \
            if r.line else r.file
        if not r.picture or r.picture.lower().endswith(".cas"):
            self.lbl_pic.configure(text=where + ("\nA model: View it in 3D on the Maps' 3D tab (Trees)."
                                                 if r.picture else ""))
            return
        im = None
        try:
            from .models import texture_image
            im = texture_image(self.mod, r.picture)
        except Exception:
            im = None
        if im is None:
            self.lbl_pic.configure(text=where + "\n%s: not found in the mod, the game or its packs." % r.picture)
            return
        try:
            from PIL import ImageTk
            size = im.size
            im = im.copy()
            im.thumbnail((160, 160))
            self._photo = ImageTk.PhotoImage(im)
            self.pic.configure(image=self._photo)
            self.lbl_pic.configure(text="%s\n%s (%d x %d)" % (where, r.picture, size[0], size[1]))
        except Exception:
            self.lbl_pic.configure(text=where + "\n" + r.picture)


def open_library(app, mod, campaign, pick=None):
    """The Climate library window (Terrain > Climates)."""
    return ClimateLibrary(app, mod, campaign, pick)
