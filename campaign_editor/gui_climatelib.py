"""Terrain > Climates > Climate library...: every climate of the mod with how much of the map it covers, and its
passport - what it gives the campaign map (colour, heat, winter, trees, ground textures), the mountains, the battle
map, the weather and sounds - file by file and line by line, pictures shown (climatelib). New climate from this...
copies the picked one into a free slot under a new name and colour (climatecopy.write_copy); Change... gives a
campaign-map ground slot another picture or a tree line another model, picked from the mod's and the game's own
(climatecopy.pool). Each write: a backup first, Restore undoes it."""

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
        tip(ttk.Button(bar, text="New climate from this...", command=self.new_climate),
            "A new climate made as a copy of the one picked: every block and line the picked one has in every file "
            "is copied under the new name (the battle map crashes on a climate it finds no block for), it takes the "
            "next free slot (32 with REX / M2EX) and a colour of its own - then paint it on the map and change what "
            "should differ here.").pack(side="right", padx=(0, 8))
        self.btn_change = ttk.Button(bar, text="Change...", command=self.change, state="disabled")
        tip(self.btn_change, "Give the picked row another picture (a campaign-map ground texture) or another model "
            "(a campaign-map tree), from the mod's and the game's own. A ground row 'from default' gets the climate "
            "a block of its own, a copy of default, with only this row changed.").pack(side="right", padx=(0, 8))
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
        self.btn_change.configure(state="normal" if r is not None and self._changeable(r) else "disabled")
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


    # ---- writing ----
    @staticmethod
    def _changeable(r):
        return r.file == "descr_aerial_map_ground_types.txt" and r.what.startswith("ground ") or \
            r.file == "descr_climates.txt" and r.what.startswith("trees ")

    def _climate(self):
        sel = self.climates.selection()
        return sel[0] if sel else None

    def _write(self, plan, what):
        """plan written after a yes (a backup first); the editor's copies of the files read again."""
        from tkinter import messagebox
        from . import log
        from .gui_util import ask
        warn = "\n".join("- " + m for _, m in plan.warnings)
        if not ask("Climate library", "%s\n\n%d file(s) change. A backup is made first (Restore undoes it).%s" % (
                what, len(plan.changed_files()) + len(plan.copies), ("\n\n" + warn) if warn else ""),
                   yes="Write it", no="Cancel", parent=self):
            return False
        try:
            bdir = plan.apply()
        except Exception as e:
            messagebox.showerror("Climate library", "Not written: %s" % e, parent=self)
            return False
        log.write("Climate library: %s (backup %s)\n%s" % (what, bdir, plan.report()))
        # the changed texts read again (only those: the Terrain editor keeps its painted pictures in the same cache)
        paths = set(plan.files.keys()) | {f.path for f in plan.files.values()}
        ed = getattr(self.app, "editors", {}).get("terrain") if isinstance(getattr(self.app, "editors", None),
                                                                           dict) else None
        for m in (self.mod, getattr(self.app, "mod", None), getattr(ed, "mod", None)):
            for path in paths:
                getattr(m, "_cache", {}).pop(path, None)
        if ed is not None:
            try:
                ed.fill_palette()
            except Exception:
                pass
        return True

    def new_climate(self):
        from tkinter import colorchooser, messagebox
        from . import climatecopy as C, terrain as T
        from .plan import Plan
        src = self._climate()
        if not src:
            return
        have = {c for _, c, _ in T.climates(self.mod)}
        colour = _free_colour(have)
        path = self.mod.find("descr_climates.txt")
        free = L.free_slots(self.mod.load(path).texts(), self.game) if path else []
        w = tk.Toplevel(self)
        w.title("New climate from %s" % src)
        w.transient(self)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        v_name = tk.StringVar(value=free[0][1] if free else src + "_2")
        v_title = tk.StringVar()
        ttk.Label(f, text="Name in the files").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(f, textvariable=v_name, width=28).grid(row=0, column=1, sticky="w")
        ttk.Label(f, text="Name players read").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(f, textvariable=v_title, width=28).grid(row=1, column=1, sticky="w")
        ttk.Label(f, text="Colour on map_climates.tga").grid(row=2, column=0, sticky="w", pady=2)
        sw = tk.Label(f, width=6, background="#%02x%02x%02x" % colour, relief="groove")
        sw.grid(row=2, column=1, sticky="w")
        pick = [colour]

        def choose():
            got = colorchooser.askcolor(color="#%02x%02x%02x" % pick[0], parent=w)
            if got and got[0]:
                pick[0] = tuple(int(v) for v in got[0])
                sw.configure(background="#%02x%02x%02x" % pick[0])
        ttk.Button(f, text="Colour...", command=choose).grid(row=2, column=2, sticky="w", padx=4)
        ttk.Label(f, text=("Every block and line %s has goes for the new climate too (its trees, ground textures, "
                           "battle ground, plants, water, weather, sounds); it takes slot %s. Small letters, digits "
                           "and _ only. %s" % (src, free[0][0] + 1 if free else "-",
                                                "The engine's own name of that slot (%s) is the safest." % free[0][1]
                                                if free else "")),
                  foreground="#666", wraplength=420, justify="left").grid(row=3, column=0, columnspan=3,
                                                                          sticky="w", pady=(8, 0))

        def go():
            name = v_name.get().strip()
            why = C.problems(self.mod, src, name, pick[0])
            if why:
                messagebox.showerror("Climate library", "Not made: %s" % "; ".join(why), parent=w)
                return
            plan = Plan(self.mod, "climate", name)
            try:
                done = C.write_copy(plan, src, name, pick[0], v_title.get().strip() or None, self.game)
            except (ValueError, OSError) as e:
                messagebox.showerror("Climate library", "Not made: %s" % e, parent=w)
                return
            what = "New climate %s, a copy of %s:\n%s" % (name, src, "\n".join(
                "- %s: %d place(s)" % (f_, n) for f_, n in done))
            if self._write(plan, what):
                w.destroy()
                self.climates.delete(*self.climates.get_children())
                self.fill(name)
                self.app.status.set("Climate %s made from %s - paint it on the map (Terrain > Climates), then "
                                    "change what should differ in the library." % (name, src))
        b = ttk.Frame(f)
        b.grid(row=4, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(b, text="Make it", command=go).pack(side="left", padx=4)
        ttk.Button(b, text="Cancel", command=w.destroy).pack(side="left")

    def change(self):
        from tkinter import messagebox
        from . import climatecopy as C
        from .plan import Plan
        sel = self.rows.selection()
        r = self._row_of.get(sel[0]) if sel else None
        name = self._climate()
        if r is None or not name or not self._changeable(r):
            return
        tree = r.file == "descr_climates.txt"
        folder = "terrain/aerial_map/tree_models" if tree else "terrain/aerial_map/ground_types"
        files = C.pool(self.mod, folder, (".cas",) if tree else (".tga", ".dds", ".texture"))
        if not files:
            messagebox.showinfo("Climate library", "No files in data/%s of the mod or the game." % folder,
                                parent=self)
            return
        w = tk.Toplevel(self)
        w.title("%s - %s" % (name, r.what))
        w.transient(self)
        w.geometry("560x460")
        top = ttk.Frame(w, padding=8)
        top.pack(fill="both", expand=True)
        lb = tk.Listbox(top, exportselection=False, width=34)
        sb = ttk.Scrollbar(top, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")
        for x in files:
            lb.insert("end", x)
        pic = ttk.Label(top, anchor="n")
        pic.pack(side="left", fill="both", expand=True, padx=8)
        now = r.value.split()[0]
        if now in files:
            lb.selection_set(files.index(now))
            lb.see(files.index(now))
        hold = {}

        def show(_e=None):
            s = lb.curselection()
            if not s or tree:
                pic.configure(text="a model - see it in 3D on the Maps' 3D tab" if tree else "", image="")
                return
            try:
                from PIL import ImageTk
                from .models import texture_image
                im = texture_image(self.mod, folder + "/" + files[s[0]])
                if im is None:
                    pic.configure(text="(cannot be shown)", image="")
                    return
                im = im.copy()
                im.thumbnail((240, 240))
                hold["p"] = ImageTk.PhotoImage(im)
                pic.configure(image=hold["p"], text="")
            except Exception:
                pic.configure(text="(cannot be shown)", image="")
        lb.bind("<<ListboxSelect>>", show)
        show()

        def go():
            s = lb.curselection()
            if not s:
                return
            pick = files[s[0]]
            plan = Plan(self.mod, "climate", name)
            try:
                if tree:
                    C.set_tree(plan, name, r.line, pick)
                else:
                    C.set_ground(plan, name, r.what[len("ground "):].replace(" ", "_"), pick)
            except (ValueError, OSError) as e:
                messagebox.showerror("Climate library", "Not changed: %s" % e, parent=w)
                return
            if self._write(plan, "%s: %s -> %s" % (name, r.what, pick)):
                w.destroy()
                self.show()
        b = ttk.Frame(w, padding=8)
        b.pack(side="bottom", fill="x")
        ttk.Button(b, text="Cancel", command=w.destroy).pack(side="right")
        ttk.Button(b, text="Use it", command=go).pack(side="right", padx=4)


def _free_colour(taken):
    """A bright colour no climate has, nor one close to it (map_climates.tga tells them apart by colour, the modder
    by eye)."""
    import colorsys
    for i in range(360):
        h = (i * 0.618033988749895) % 1.0
        c = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(h, 0.85, 0.9))
        if all(sum((a - b) ** 2 for a, b in zip(c, t)) > 60 ** 2 for t in taken):    # one told apart by eye too
            return c
    return (1, 2, 3)


def open_library(app, mod, campaign, pick=None):
    """The Climate library window (Terrain > Climates)."""
    return ClimateLibrary(app, mod, campaign, pick)
