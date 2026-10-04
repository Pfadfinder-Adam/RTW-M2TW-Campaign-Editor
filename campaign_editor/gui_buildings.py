"""The buildings panel: every building chain the faction may build, with the
game's picture of the chosen level, for one settlement at a time."""

import tkinter as tk
from tkinter import ttk

from .buildings import SETTLEMENT_LEVELS, available, core_level_for, core_settlement, ranks_ok

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
        # on a line of its own under the town's row: beside the name it was cut in a narrow window
        under = ttk.Frame(self)
        ttk.Checkbutton(under, text="show levels too big for the settlement", variable=self.v_all,
                        command=self.redraw).pack(side="left")
        self.b_keep = ttk.Button(top, text="Keep the town's own", command=self.reset)
        self.b_keep.pack(side="right")
        from .gui_util import first
        first(self.b_keep)
        # Medieval II: a city or a castle (shown only where the game has castles)
        self.kind_box = ttk.Frame(top)
        ttk.Label(self.kind_box, text="Settlement is a").pack(side="left")
        self.v_kind = tk.StringVar(value="city")
        self.cb_kind = ttk.Combobox(self.kind_box, textvariable=self.v_kind, values=("city", "castle"),
                                    state="readonly", width=9)
        self.cb_kind.pack(side="left", padx=4)
        self.cb_kind.bind("<<ComboboxSelected>>", lambda e: self.on_kind and self.on_kind(self.v_kind.get()))
        self.kind = None
        self.on_kind = None
        under.pack(fill="x")
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
        from .gui_util import scroll_y, wheel
        wheel(canvas, scroll_y(canvas))
        self.canvas = canvas
        self._width = 0
        canvas.bind("<Configure>", self._resized, add="+")
        self.bpics = None
        self.roster = {}                  # {(chain, level): give?} from the Roster tab
        # nothing picked yet: the buttons and the check box above work on an empty editor (a click before a town
        # was picked raised AttributeError 'own' / 'buildings' - a report from 0.25.0)
        self.buildings, self.own, self.current, self.edited = None, [], {}, False
        self.region = self.town_level = self.culture = self.faction = self.template = None

    def _resized(self, e):
        if abs(e.width - self._width) > 40 and getattr(self, "buildings", None) is not None:
            self._width = e.width
            self.redraw()

    def load(self, region, town_level, buildings, own, picked, culture, faction, template, bpics, on_change,
             kind=None, on_kind=None):
        """buildings: [Building]; own: the town's buildings now [(chain, level)];
        picked: the hand-set list or None; on_change(list or None); kind: Medieval II 'city' / 'castle' (None
        in Rome) - the chains offer only that kind's levels; on_kind(kind) when it is switched."""
        self.kind, self.on_kind = kind, on_kind
        if kind:
            self.v_kind.set(kind)
            self.kind_box.pack(side="right", padx=12, after=self.b_keep)
        else:
            self.kind_box.pack_forget()
        self.region, self.town_level = region, town_level
        self.buildings, self.own = buildings, list(own)
        self.culture, self.faction, self.template, self.bpics = culture, faction, template, bpics
        self.on_change = on_change
        self.current = dict(picked if picked is not None else own)
        self.edited = picked is not None
        self.set_level(town_level)

    def set_level(self, level):
        """The settlement level the chains offer their levels for: the one picked or
        grown in the window, not only the one in the file."""
        self.town_level = level
        self.title.configure(text="%s - a %s%s" % (self.region, level, " castle" if self.kind == "castle" else ""))
        self.redraw()

    def core_for(self, level):
        """(chain, level) of the governor's building that fits a settlement level:
        the biggest level of the core chain (the one the town has, else the first
        the faction may build) that the settlement allows; or None."""
        cores = [(b, lv) for b, lv in self.chains() if b.name.lower().startswith("core") and lv]
        if not cores:
            return None
        b, levels = next(((b, lv) for b, lv in cores if b.name in self.current), cores[0])
        lv = core_level_for(b, level)          # the game wants exactly this one (none in a village)
        return (b.name, lv.name if lv else None)

    def chains(self):
        """(building, [levels this faction may build]) for every chain it may build,
        plus chains the town already has."""
        out = []
        for b in self.buildings or ():
            # a level given or taken on the Roster tab counts as the faction's list will be
            lv = [l for l in b.levels if self.roster.get((b.name, l.name),
                                                         available(l, self.faction, self.culture, self.template))
                  and (self.kind is None or l.kind in (None, self.kind))]     # a castle offers castle levels
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
        missing = bool(now) and img is None
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
        need = ("the governor's building of a %s" % core_settlement(b, lv.name)) if lv and core else \
            ("needs a %s" % lv.settlement_min if lv else "")
        tip = ("%s: %s, cost %d, %d turn(s), %s%s" % (b.name, lv.name, lv.cost, lv.turns, need,
               ("; also " + lv.conditional()) if lv.conditional() else "")) if lv else b.name
        if missing:
            tip += "\nno picture for the %s culture (ui/%s/buildings) (nor in the cultures descr_ui_buildings.txt sends it to)" % (
                self.culture, self.culture)
        for w in (f, pic, cb):
            w.bind("<Enter>", lambda e, t=tip: self.info.configure(text=t))
        return f

    def _summary(self):
        if not self.edited:
            self.info.configure(text="the town keeps its own buildings (%d) - change any to set them by hand"
                                % len(self.own))

    def fit_down(self, level):
        """Every picked building too big for a settlement of this level drops to the
        biggest level of its chain that fits (or goes). [(chain, old, new or None)]."""
        done = []
        levels = dict((b.name, lv) for b, lv in self.chains())
        for chain, name in list(self.current.items()):
            if chain.lower().startswith("core"):
                continue
            b = next((x for x in self.buildings if x.name == chain), None)
            lv = b.level(name) if b else None
            if lv is None or ranks_ok(lv, level):
                continue
            fit = [l for l in levels.get(chain, []) if ranks_ok(l, level)]
            if fit:
                self.current[chain] = fit[-1].name
                done.append((chain, name, fit[-1].name))
            else:
                del self.current[chain]
                done.append((chain, name, None))
        if done:
            self.edited = True
            self.last_pick = None
            self.on_change(sorted(self.current.items(), key=lambda x: self._order(x[0])))
        return done

    def pick(self, chain, level):
        self.last_pick = (chain, level)
        if level == NONE:
            self.current.pop(chain, None)
        else:
            from .buildings import other_temple
            old = other_temple(self.current, chain)
            if old:                                  # one temple per town (the games' rule): the new one replaces it
                self.current.pop(old, None)
            self.current[chain] = level
            if old:
                self.after_idle(lambda: self.info.configure(text="%s replaces %s - a town holds one temple only "
                                                                  "(as in the game)" % (chain, old)))
        self.edited = True
        self.on_change(sorted(self.current.items(), key=lambda x: self._order(x[0])))
        self.redraw()

    def _order(self, chain):
        return next((i for i, b in enumerate(self.buildings) if b.name == chain), 999)

    def reset(self):
        if self.buildings is None:
            return                      # no town picked yet
        self.current = dict(self.own)
        self.edited = False
        if self.on_change:
            self.on_change(None)
        self.redraw()


__all__ = ["BuildingsEditor", "SETTLEMENT_LEVELS"]
