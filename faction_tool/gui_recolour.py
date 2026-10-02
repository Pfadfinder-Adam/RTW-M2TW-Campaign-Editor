"""The window 'Recolour the faction's pictures': every picture of a faction that carries its colours (unit cards,
battle textures, symbols, banners, captain cards...) moved from the colours they carry now (the template's, for a
cloned faction - guessed, can be changed) to the faction's own colours (descr_sm_factions.txt, can be changed).
Before / after of the picked picture; Write it makes one backup (Restore undoes it)."""

import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from . import recolour as R
from .gui_util import ShortHint, hint

TITLE = "Recolour the faction's pictures"
SIDE = 360
CUSTOM = "(colours picked here)"


def _hex(c):
    return "#%02x%02x%02x" % c if c else "#ffffff"


class RecolourWindow(tk.Toplevel):
    def __init__(self, app, faction):
        super().__init__(app)
        self.app, self.mod, self.faction = app, app.mod, faction
        self.camp = app.v_campaign.get()
        self.title("%s - %s" % (TITLE, faction))
        self.transient(app)
        self.minsize(820, 520)
        # the 'now' and 'after' pictures fit the screen (a tester: 'after' went past the window's edge)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.side = max(180, min(SIDE, (min(sw, 1400) - 620) // 2, sh - 470))
        self.geometry("%dx%d" % (min(sw - 40, 600 + 2 * self.side + 60), min(sh - 80, 720)))
        self.colours = R.faction_colours(self.mod)
        self.items = R.targets(self.mod, self.camp, faction)
        paths = [it for it in self.items if it["group"] != "symbols and banners" and not it["skip"]] or \
            [it for it in self.items if not it["skip"]]
        (self.source, self.source_of) = R.guess_source(self.mod, faction, paths, self.colours) if paths else \
            (self.colours.get(faction, ((200, 0, 0), None)), faction)
        self.target = list(self.colours.get(faction, ((200, 0, 0), None)))
        self.source = list(self.source)
        self._cache, self._photos = {}, []
        self._build()
        self.fill()

    # ---- the window ----
    def _build(self):
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill="both", expand=True)
        ShortHint(outer, text=(
            "Moves the faction's pictures from the colours they carry now to new ones. A part counts as the "
            "faction's colour when it is coloured and its hue is near the 'from' colour; where the same picture "
            "exists for other factions (a unit card, a battle texture), only what differs between them changes - "
            "faces, horses, metal and leather stay. Light and shade are kept. White, grey and black 'from' colours "
            "have no hue and are left as they are. A picture other factions use too is left alone (said in the "
            "list). Only the ticked pictures are written, with a backup; Restore gives them back.")).pack(
            anchor="w", pady=(0, 6))
        bar = ttk.Frame(outer)
        bar.pack(fill="x")
        ttk.Label(bar, text="From the colours of").pack(side="left")
        names = sorted(self.colours) + [CUSTOM]
        self.v_from = tk.StringVar(value=self.source_of)
        cb = ttk.Combobox(bar, textvariable=self.v_from, values=names, state="readonly", width=18)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._from_picked())
        self.sw_from = [self._swatch(bar, "from", 0), self._swatch(bar, "from", 1)]
        hint(bar, "Guessed from the pictures: the faction whose colours they show most (for a faction cloned from "
                  "a template: the template's). Click a colour to pick another.").pack(side="left")
        ttk.Label(bar, text="    to").pack(side="left")
        self.sw_to = [self._swatch(bar, "to", 0), self._swatch(bar, "to", 1)]
        hint(bar, "The faction's own primary and secondary colour (descr_sm_factions.txt). Click to pick others; "
                  "with the box beside ticked they become the faction's colours too (the flags on the campaign "
                  "map, the political map, the Faction tab follow).").pack(side="left")
        self.v_set = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="make them the faction's colours", variable=self.v_set).pack(side="left", padx=8)
        panes = ttk.PanedWindow(outer, orient="horizontal")
        panes.pack(fill="both", expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        self.tree = ttk.Treeview(left, columns=("what", "note"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Write")
        self.tree.heading("what", text="Picture")
        self.tree.heading("note", text="Note")
        self.tree.column("#0", width=150, stretch=False)
        self.tree.column("what", width=260)
        self.tree.column("note", width=200)
        sb = ttk.Scrollbar(left, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show())
        self.tree.bind("<Button-1>", self._click, add="+")
        self.tree.tag_configure("skip", foreground="#888")
        panes.add(left, weight=1)
        right = ttk.Frame(panes, padding=(8, 0, 0, 0))
        self.lbl_pic = ttk.Label(right, text="", foreground="#333", wraplength=520, justify="left")
        self.lbl_pic.pack(anchor="w")
        pics = ttk.Frame(right)
        pics.pack(anchor="w", pady=6)
        self.before = tk.Label(pics, relief="sunken")
        self.after = tk.Canvas(pics, width=self.side, height=self.side, highlightthickness=1, highlightbackground="#999",
                               cursor="crosshair")
        ttk.Label(pics, text="now").grid(row=0, column=0)
        ttk.Label(pics, text="after").grid(row=0, column=1)
        self.before.grid(row=1, column=0, padx=4)
        self.after.grid(row=1, column=1, padx=4)
        # touch-ups by hand on the 'after' picture: what the colour test missed (or took wrongly)
        tools = ttk.LabelFrame(right, text="Touch up by hand - paint on the 'after' picture", padding=6)
        tools.pack(anchor="w", fill="x", pady=(4, 0))
        self.v_brush = tk.StringVar(value="p")
        for text, val in (("new primary colour", "p"), ("new secondary colour", "s"), ("keep as it was", "keep")):
            ttk.Radiobutton(tools, text=text, value=val, variable=self.v_brush).pack(side="left", padx=(0, 8))
        row2 = ttk.Frame(right)
        row2.pack(anchor="w", pady=(4, 0))
        ttk.Label(row2, text="brush (pixels)").pack(side="left")
        self.v_size = tk.IntVar(value=2)
        ttk.Spinbox(row2, from_=1, to=40, textvariable=self.v_size, width=4).pack(side="left", padx=2)
        ttk.Button(row2, text="Clear my touch-ups", command=self.clear_edits).pack(side="left", padx=8)
        ttk.Label(row2, text="wheel: zoom, right drag: move", foreground="#666").pack(side="left")
        hint(row2, "Left drag on the 'after' picture paints: 'new primary' / 'new secondary' recolours what you "
                    "paint (a red line the test missed), 'keep as it was' gives the old pixels back (a face or a "
                    "horse it took). The brush size is in the picture's own pixels. Mouse wheel: zoom. The touch-ups "
                    "are kept for that picture until Write it or Clear.").pack(side="left")
        self.edits, self.zoom = {}, {}
        a = self.after
        a.bind("<ButtonPress-1>", self._paint)
        a.bind("<B1-Motion>", self._paint)
        a.bind("<ButtonRelease-1>", lambda e: self._painted())
        for seq, step in (("<MouseWheel>", None), ("<Button-4>", 1), ("<Button-5>", -1)):
            a.bind(seq, lambda e, st=step: self._wheel(e, st))
        a.bind("<ButtonPress-3>", lambda e: a.scan_mark(e.x, e.y))
        a.bind("<B3-Motion>", lambda e: a.scan_dragto(e.x, e.y, gain=1))
        panes.add(right, weight=1)
        bot = ttk.Frame(outer)
        bot.pack(fill="x", pady=(8, 0))
        ttk.Button(bot, text="Tick all", command=lambda: self._tick_all(True)).pack(side="left")
        ttk.Button(bot, text="Untick all", command=lambda: self._tick_all(False)).pack(side="left", padx=4)
        ttk.Button(bot, text="Preview", command=self.preview).pack(side="left", padx=(16, 0))
        ttk.Button(bot, text="Write it", command=self.write).pack(side="left", padx=4)
        self.status = ttk.Label(bot, foreground="#555")
        self.status.pack(side="left", padx=8)
        ttk.Button(bot, text="Close", command=self.destroy).pack(side="right")

    def _swatch(self, parent, side, k):
        b = tk.Button(parent, width=3, relief="raised", command=lambda: self._pick(side, k))
        b.pack(side="left", padx=2)
        return b

    def _paint_swatches(self):
        for b, c in zip(self.sw_from, self.source):
            b.configure(bg=_hex(c), activebackground=_hex(c), text="" if c and R.coloured(c) else "-")
        for b, c in zip(self.sw_to, self.target):
            b.configure(bg=_hex(c), activebackground=_hex(c), text="")

    def _pick(self, side, k):
        cols = self.source if side == "from" else self.target
        got = colorchooser.askcolor(color=_hex(cols[k]), parent=self,
                                    title="%s colour (%s)" % ("Primary" if k == 0 else "Secondary", side))
        if got and got[0]:
            cols[k] = tuple(int(v) for v in got[0])
            if side == "from":
                self.v_from.set(CUSTOM)
            self._changed()

    def _from_picked(self):
        f = self.v_from.get()
        if f in self.colours:
            self.source = list(self.colours[f])
            self._changed()

    def _changed(self):
        self._cache = {}
        self._paint_swatches()
        self.show()

    # ---- the list ----
    def fill(self):
        self._paint_swatches()
        t = self.tree
        t.delete(*t.get_children(""))
        self.ticked = {}
        groups = {}
        for i, it in enumerate(self.items):
            g = groups.get(it["group"])
            if g is None:
                g = groups[it["group"]] = t.insert("", "end", text=it["group"], open=it["group"] != "unit cards")
            iid = "i%d" % i
            self.ticked[iid] = not it["skip"]
            t.insert(g, "end", iid=iid, text=self._mark(iid), values=(it["label"], it["skip"] or ""),
                     tags=("skip",) if it["skip"] else ())
        for g, gid in groups.items():
            n = sum(1 for it in self.items if it["group"] == g)
            t.item(gid, text="%s (%d)" % (g, n))
        if not self.items:
            self.status.configure(text="no picture of %s carries a faction colour" % self.faction)
        kids = [c for g in t.get_children("") for c in t.get_children(g)]
        if kids:
            t.selection_set(kids[0])

    def _mark(self, iid):
        it = self.items[int(iid[1:])]
        return "-  left" if it["skip"] else ("[x] write" if self.ticked.get(iid) else "[ ] keep")

    def _click(self, e):
        iid = self.tree.identify_row(e.y)
        if iid in self.ticked and self.tree.identify_column(e.x) == "#0" and not self.items[int(iid[1:])]["skip"]:
            self.ticked[iid] = not self.ticked[iid]
            self.tree.item(iid, text=self._mark(iid))

    def _tick_all(self, on):
        for iid in self.ticked:
            if not self.items[int(iid[1:])]["skip"]:
                self.ticked[iid] = on
                self.tree.item(iid, text=self._mark(iid))

    # ---- before / after ----
    def _key(self, it):
        return it["path"], it.get("crop")

    def _pair(self, it):
        key = self._key(it)
        if key not in self._cache:
            im = R.read_picture(it["path"])
            if it.get("crop"):
                x, y, w, h = it["crop"]
                im = im.crop((x, y, x + w, y + h))
                others = []
            else:
                others = []
                for p, c in it.get("others") or []:
                    try:
                        others.append((R.read_picture(p), c))
                    except Exception:
                        pass
            new, share = R.recolour(im, self.source, self.target, others, edits=self.edits.get(key))
            self._cache[key] = (im, new, share)
        return self._cache[key]

    def show(self):
        sel = self.tree.selection()
        if not sel or sel[0] not in self.ticked:
            self._shown = None                     # a group line: no picture to touch up
            return
        it = self.items[int(sel[0][1:])]
        try:
            im, new, share = self._pair(it)
        except Exception as e:
            self.lbl_pic.configure(text="%s - cannot be read (%s)" % (it["rel"], e))
            return
        from PIL import Image, ImageTk
        self._shown = it
        fit = min(self.side / im.size[0], self.side / im.size[1], 6.0)
        k = self.k = fit * self.zoom.get(self._key(it), 1.0)
        size = (max(1, int(im.size[0] * fit)), max(1, int(im.size[1] * fit)))
        big = (max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k)))
        self._photos = [ImageTk.PhotoImage(im.resize(size, Image.NEAREST)),
                        ImageTk.PhotoImage(new.resize(big, Image.NEAREST))]
        self.before.configure(image=self._photos[0])
        a = self.after
        a.delete("all")
        a.create_image(0, 0, image=self._photos[1], anchor="nw")
        a.configure(scrollregion=(0, 0, big[0], big[1]))
        self.lbl_pic.configure(text="%s\n%s - %.0f%% of it is the faction's colour%s" % (
            it["label"], it["rel"], 100 * share, ("\nleft as it is: " + it["skip"]) if it["skip"] else ""))

    # ---- touch-ups ----
    def _paint(self, e):
        it = getattr(self, "_shown", None)
        if it is None or it.get("skip"):
            return
        a = self.after
        x, y = a.canvasx(e.x), a.canvasy(e.y)
        r = max(1, self.v_size.get()) * self.k / 2.0
        colour = {"p": _hex(self.target[0]), "s": _hex(self.target[1] or (255, 255, 255))}.get(
            self.v_brush.get(), "#ff00ff")
        a.create_oval(x - r, y - r, x + r, y + r, outline=colour, fill=colour, tags="stroke")
        self._stroke = getattr(self, "_stroke", []) + [(x / self.k, y / self.k)]

    def _painted(self):
        pts = getattr(self, "_stroke", [])
        self._stroke = []
        it = getattr(self, "_shown", None)
        if not pts or it is None:
            return
        from PIL import Image, ImageDraw
        key = self._key(it)
        try:
            im = self._pair(it)[0]                 # read again when the colours changed since it was shown
        except Exception:
            return
        ed = self.edits.setdefault(key, {})
        which = self.v_brush.get()
        r = max(1, self.v_size.get()) / 2.0
        for name in ("p", "s", "keep"):
            m = ed.get(name) or Image.new("L", im.size, 0)
            d = ImageDraw.Draw(m)
            for x, y in pts:
                d.ellipse((x - r, y - r, x + r - 1, y + r - 1), fill=255 if name == which else 0)
            ed[name] = m
        it["edits"] = ed
        iid = "i%d" % self.items.index(it)
        if iid in self.ticked and not self.ticked[iid]:
            self.ticked[iid] = True
            self.tree.item(iid, text=self._mark(iid))
        self._cache.pop(key, None)
        self.show()

    def clear_edits(self):
        it = getattr(self, "_shown", None)
        if it is None:
            return
        self.edits.pop(self._key(it), None)
        it.pop("edits", None)
        self._cache.pop(self._key(it), None)
        self.show()

    def _wheel(self, e, step):
        it = getattr(self, "_shown", None)
        if it is None:
            return
        up = (step or (1 if e.delta > 0 else -1)) > 0
        key = self._key(it)
        z = self.zoom.get(key, 1.0)
        self.zoom[key] = min(8.0, z * 1.5) if up else max(1.0, z / 1.5)
        self.show()

    # ---- writing ----
    def picked(self):
        return [self.items[int(i[1:])] for i, on in self.ticked.items() if on]

    def _plan(self):
        from .plan import Plan
        items = self.picked()
        if not items:
            raise ValueError("Tick at least one picture.")
        plan = Plan(self.mod, "recolour", "recolour_%s" % self.faction, {})
        self.status.configure(text="recolouring %d picture(s)..." % len(items))
        self.update_idletasks()
        done = R.plan_recolour(plan, items, self.source, self.target)
        now = tuple(tuple(c) if c else None for c in self.colours.get(self.faction, (None, None)))
        if self.v_set.get() and tuple(tuple(c) for c in self.target) != now:
            # the pictures and the faction's own colour lines move together (our rule: a change pulls along
            # what is tied to it - a tester found the colours unchanged after a recolour)
            from .edit import set_faction_colours
            set_faction_colours(plan, self.faction, tuple(self.target[0]),
                                tuple(self.target[1]) if self.target[1] else None)
        for it, how in done:
            if not isinstance(how, float):
                plan.warn(None, "%s: %s" % (it["rel"], how))
            elif how == 0:
                plan.note(None, "%s: no part in the 'from' colours - unchanged" % it["rel"])
        return plan

    def preview(self):
        try:
            plan = self._plan()
        except ValueError as e:
            messagebox.showinfo(TITLE, str(e), parent=self)
            return
        self.status.configure(text="")
        self.app.show_text("Preview - " + TITLE, plan.report(), wrap="word")

    def write(self):
        try:
            plan = self._plan()
        except ValueError as e:
            messagebox.showinfo(TITLE, str(e), parent=self)
            return
        bdir = plan.apply()
        from . import log
        log.write("%s %s (backup %s)\n%s" % (TITLE, self.faction, bdir, plan.report()))
        n = len(plan.binaries)
        self.status.configure(text="%d picture(s) written (backup %s) - Restore undoes it" % (n, bdir))
        self.app.status.set("%s: %d picture(s) of %s recoloured (backup %s)." % (TITLE, n, self.faction, bdir))
        self._cache, self.edits = {}, {}
        if self.v_set.get():
            self.app.load()                         # the faction's colours are read again everywhere
            self.mod = self.app.mod
            self.colours = R.faction_colours(self.mod)
        self.items = R.targets(self.mod, self.camp, self.faction)
        self.source = list(self.target)
        self.v_from.set(self.faction if tuple(self.target) == tuple(self.colours.get(self.faction, ())) else CUSTOM)
        self.fill()


__all__ = ["RecolourWindow"]
