"""The buildings panel: every building chain the faction may build, with the
game's picture of the chosen level, for one settlement at a time."""

import tkinter as tk
from tkinter import ttk

from .buildings import SETTLEMENT_LEVELS, available, ranks_ok

PICTURE = (78, 62)                    # half the game's 156 x 124 building pictures
NONE = "-"


class BuildingsEditor(ttk.Frame):
    def __init__(self, master, pictures):
        super().__init__(master)
        self.pics = pictures
        self.rows = []
        self.on_change = None
        top = ttk.Frame(self, padding=(0, 0, 0, 4))
        top.pack(fill="x")
        self.title = ttk.Label(top, text="Pick a town on the left", font=("", 10, "bold"))
        self.title.pack(side="left")
        self.v_all = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="show levels too big for the settlement", variable=self.v_all,
                        command=self.redraw).pack(side="left", padx=12)
        ttk.Button(top, text="Keep the town's own", command=self.reset).pack(side="right")
        self.info = ttk.Label(self, text="", anchor="w", foreground="#444")
        self.info.pack(fill="x")

        canvas = tk.Canvas(self, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",
                    lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        self.canvas = canvas
        self._width = 0
        canvas.bind("<Configure>", self._resized, add="+")
        self.bpics = None

    def _resized(self, e):
        if abs(e.width - self._width) > 40 and getattr(self, "buildings", None) is not None:
            self._width = e.width
            self.redraw()

    def load(self, region, town_level, buildings, own, picked, culture, faction, template, bpics, on_change):
        """buildings: [Building]; own: the town's buildings now [(chain, level)];
        picked: the hand-set list or None; on_change(list or None)."""
        self.region, self.town_level = region, town_level
        self.buildings, self.own = buildings, list(own)
        self.culture, self.faction, self.template, self.bpics = culture, faction, template, bpics
        self.on_change = on_change
        self.current = dict(picked if picked is not None else own)
        self.edited = picked is not None
        self.title.configure(text="%s - a %s" % (region, town_level))
        self.redraw()

    def chains(self):
        """(building, [levels this faction may build]) for every chain it may build,
        plus chains the town already has."""
        out = []
        for b in self.buildings:
            lv = [l for l in b.levels if available(l, self.faction, self.culture, self.template)]
            if lv or b.name in self.current:
                out.append((b, lv))
        return out

    def redraw(self):
        if getattr(self, "_drawing", False):
            return                      # a resize while drawing: this draw already fits the new width
        self._drawing = True
        try:
            self._redraw()
        finally:
            self._drawing = False

    def _redraw(self):
        for w in self.inner.winfo_children():
            w.destroy()
        rows = [self._row(b, levels) for b, levels in self.chains()]
        self.update_idletasks()
        cell = max((r.winfo_reqwidth() for r in rows), default=300) + 8
        cols = max(1, (self.canvas.winfo_width() - 4) // cell)
        for i, r in enumerate(rows):
            r.grid(row=i // cols, column=i % cols, sticky="nw", padx=4, pady=3)
        self._summary()

    def _row(self, b, levels):
        f = ttk.Frame(self.inner, relief="groove", padding=3)
        now = self.current.get(b.name)
        # the governor's chain shows every level: picking a bigger one grows the settlement
        core = b.name.lower().startswith("core")
        shown = [l for l in levels if core or self.v_all.get() or ranks_ok(l, self.town_level) or l.name == now]
        names = [NONE] + [l.name for l in shown]
        if now and now not in names:
            names.append(now)
        img = self.pics.get(self.bpics.find(self.culture, now), PICTURE) if now else None
        if img is None:                   # an empty slot the picture's size (a Label's width is in characters otherwise)
            if not hasattr(self, "_blank"):
                self._blank = tk.PhotoImage(width=PICTURE[0], height=PICTURE[1])
            img = self._blank
        pic = tk.Label(f, image=img, relief="sunken" if img is getattr(self, "_blank", None) else "flat")
        pic.image = img
        pic.grid(row=0, column=0, rowspan=2)
        ttk.Label(f, text=b.name, font=("", 9, "bold")).grid(row=0, column=1, sticky="w", padx=4)
        v = tk.StringVar(value=now or NONE)
        cb = ttk.Combobox(f, textvariable=v, values=names, state="readonly", width=22)
        cb.grid(row=1, column=1, sticky="w", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.pick(b.name, v.get()))
        lv = b.level(now) if now else None
        tip = ("%s: %s, cost %d, %d turn(s), needs a %s%s" % (b.name, lv.name, lv.cost, lv.turns, lv.settlement_min,
               ("; also " + lv.conditional()) if lv.conditional() else "")) if lv else b.name
        for w in (f, pic, cb):
            w.bind("<Enter>", lambda e, t=tip: self.info.configure(text=t))
        return f

    def _summary(self):
        if not self.edited:
            self.info.configure(text="the town keeps its own buildings (%d) - change any to set them by hand"
                                % len(self.own))

    def pick(self, chain, level):
        if level == NONE:
            self.current.pop(chain, None)
        else:
            self.current[chain] = level
        self.edited = True
        self.on_change(sorted(self.current.items(), key=lambda x: self._order(x[0])))
        self.redraw()

    def _order(self, chain):
        return next((i for i, b in enumerate(self.buildings) if b.name == chain), 999)

    def reset(self):
        self.current = dict(self.own)
        self.edited = False
        self.on_change(None)
        self.redraw()


__all__ = ["BuildingsEditor", "SETTLEMENT_LEVELS"]
