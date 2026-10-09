"""The garrison picker: unit cards of the template's roster on the left, the
town's garrison on the right. Click a card to add it, click a garrison card to
take it out."""

import tkinter as tk
from tkinter import ttk

from .units import unit_card

try:                                   # pictures need Pillow; without it the cards are text
    from PIL import Image, ImageTk
except ImportError:                    # pragma: no cover - the exe always has it
    Image = ImageTk = None

MAX_UNITS = 20
CARD = (48, 64)                        # RTW unit cards are 48 x 64


class Pictures:
    """Loaded card pictures, kept alive for Tk (it drops images nobody holds)."""

    def __init__(self):
        self.cache = {}

    def missing(self, name, size=CARD):
        """A grey card of the usual size with the unit's name on it: a unit without a picture keeps the grid even
        (it was a wide text button that looked like a broken card)."""
        if Image is None:
            return None
        key = ("missing", name, size)
        if key not in self.cache:
            from PIL import ImageDraw
            im = Image.new("RGBA", size, (128, 128, 128, 255))
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(80, 80, 80, 255))
            words, lines = name.split(), [""]
            for w in words:                                  # a few short lines of the name
                if len(lines[-1]) + len(w) + 1 > 8 and lines[-1]:
                    lines.append(w)
                else:
                    lines[-1] = (lines[-1] + " " + w).strip()
            for i, t in enumerate(lines[:5]):
                d.text((3, 4 + i * 11), t[:9], fill=(255, 255, 255, 255))
            self.cache[key] = ImageTk.PhotoImage(im)
        return self.cache[key]

    def get(self, path, size=CARD):
        if not path or Image is None:
            return None
        key = (path, size)
        if key not in self.cache:
            try:
                im = Image.open(path)
                im.load()
                im = im.convert("RGBA")
                if im.size != size:
                    im.thumbnail(size)
                    if size[1] <= CARD[1] * 2 and im.size != size:   # a card of another size sits in the middle
                        box = Image.new("RGBA", size, (0, 0, 0, 0))      # of the same box: the grid stays even
                        box.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
                        im = box
                self.cache[key] = ImageTk.PhotoImage(im)
            except Exception:
                self.cache[key] = None
        return self.cache[key]


class GarrisonEditor(ttk.Frame):
    """Roster cards on the left, the town's garrison on the right. Every change
    goes straight to on_change(list of unit types)."""

    def __init__(self, master, pictures=None):
        super().__init__(master)
        self.pics = pictures or Pictures()
        self.mod = self.faction = None
        self.units, self.by_type, self.garrison = [], {}, []
        self.on_change = self.auto = None
        self.held = False

        # the town's name on a line of its own that wraps (it was cut in a narrow window), the choices below it
        self.title = ttk.Label(self, text="Pick a town on the left", font=("", 10, "bold"), justify="left")
        self.title.pack(fill="x", anchor="w")
        self.title.bind("<Configure>", lambda e: self.title.configure(wraplength=max(120, e.width - 4)), add="+")
        top = ttk.Frame(self, padding=(0, 0, 0, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Show").pack(side="left")
        self.v_cat = tk.StringVar(value="all")
        self.cb_cat = ttk.Combobox(top, textvariable=self.v_cat, values=["all"], state="readonly", width=12)
        self.cb_cat.pack(side="left", padx=4)
        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self.fill_roster())
        # whose units: the faction's own, the mercenaries it may hire, or both
        self.v_whose = tk.StringVar(value="own units")
        cb = ttk.Combobox(top, textvariable=self.v_whose, values=["own units", "mercenaries", "own + mercenaries"],
                          state="readonly", width=16)
        cb.pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill_roster())
        self.v_gen = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="general's units", variable=self.v_gen, command=self.fill_roster).pack(side="left")
        from .gui_util import first

        self.info = ttk.Label(self, text="", anchor="w", foreground="#444")
        self.info.pack(fill="x")
        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.LabelFrame(body, text="Roster - click to add")
        right = ttk.LabelFrame(body, text="Garrison - click to take out")
        body.add(left, weight=3)
        body.add(right, weight=2)
        self.roster = self._scroll(left)
        self.chosen = self._scroll(right)

        bar = ttk.Frame(self, padding=(0, 4, 0, 0))
        bar.pack(fill="x")
        self.total = ttk.Label(bar, text="", font=("", 10, "bold"), justify="left")
        self.total.pack(side="left", fill="x", expand=True)
        self.total.bind("<Configure>", lambda e: self.total.configure(wraplength=max(120, e.width - 4)), add="+")
        # Suggest draws a garrison / an army by the numbers beside it - how many units, their upkeep together at
        # most (a tester, 2026-10-09: 'Suggest does nothing, and we cannot say how much upkeep'); kept for next time.
        # Automatic (empty = the tool picks when it builds) only where that means something: New / Edit faction
        from . import settings
        self.v_lo = tk.StringVar(value=str(settings.get("suggest_units_lo", 3)))
        self.v_hi = tk.StringVar(value=str(settings.get("suggest_units_hi", 6)))
        self.v_cap = tk.StringVar(value=str(settings.get("suggest_upkeep", 2000)))
        self.b_auto = ttk.Button(bar, text="Automatic", command=self.clear)
        self.b_auto.pack(side="right", padx=4)
        self.sugg = ttk.Frame(bar)
        self.sugg.pack(side="right", padx=4)
        ttk.Label(self.sugg, text="units").pack(side="left")
        for v, w in ((self.v_lo, 3), (self.v_hi, 3)):
            ttk.Spinbox(self.sugg, from_=1, to=MAX_UNITS, textvariable=v, width=w).pack(side="left", padx=(2, 0))
            if v is self.v_lo:
                ttk.Label(self.sugg, text="to").pack(side="left", padx=(2, 0))
        ttk.Label(self.sugg, text="  upkeep up to").pack(side="left")
        ttk.Spinbox(self.sugg, from_=0, to=100000, increment=100, textvariable=self.v_cap, width=7).pack(
            side="left", padx=(2, 4))
        b = ttk.Button(self.sugg, text="Suggest", command=self.suggest)
        b.pack(side="left")
        from .gui_util import tip
        tip(b, "A garrison drawn at random from the units this faction trains: that many units, their upkeep "
               "together at most this much (0: no limit). Press again for another.")
        first(self.b_auto, self.sugg)             # Automatic, Suggest before the total

    def load(self, mod, faction, region, units, current, on_change, auto=None, held=False, unchanged=False,
             automatic=False):
        """unchanged: current is what stands in the town now, shown until the first click. auto(lo, hi, cap): the
        unit types Suggest draws (none: no Suggest); automatic: the Automatic button (empty = the tool picks)."""
        self.unchanged = unchanged
        if automatic:
            self.b_auto.pack(side="right", padx=4, before=self.sugg)
        else:
            self.b_auto.pack_forget()
        if auto:
            self.sugg.pack(side="right", padx=4)
        else:
            self.sugg.pack_forget()
        self.mod, self.faction, self.units = mod, faction, units
        self.by_type = {u.type: u for u in units}
        self.garrison = [t for t in current if t in self.by_type]
        self.on_change, self.auto, self.held = on_change, auto, held
        # held: the name of whoever holds the town (a garrison), or True for a general's own army (his bodyguard
        # stays - no town to name; it read "the True's town")
        self.title.configure(text="%s%s" % (region, " - the %s's town" % held if isinstance(held, str) and held else ""))
        self.cb_cat["values"] = ["all"] + sorted({u.category for u in units if u.category})
        self.fill_roster()
        self.fill_chosen()

    # ---- layout helpers ----
    def _scroll(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        def region(e=None):
            # never smaller than the pane, anchored at the top: short lists sit at the top, not adrift
            box = canvas.bbox("all") or (0, 0, 0, 0)
            canvas.configure(scrollregion=(0, 0, box[2], max(box[3], canvas.winfo_height())))
        inner.bind("<Configure>", region)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner.canvas = canvas
        inner.cols = 0
        canvas.bind("<Configure>", lambda e: self._reflow(inner), add="+")
        from .gui_util import scroll_y, wheel
        wheel(canvas, scroll_y(canvas))
        return inner

    def _card(self, parent, unit, command):
        path = unit_card(self.mod, unit, self.faction)
        img = self.pics.get(path) or self.pics.missing(unit.type)     # no picture: a grey card with its name
        text = unit.type if img is None else str(unit.upkeep)          # upkeep under the card
        b = tk.Button(parent, image=img, text=text, compound="top", wraplength=90, width=None if img else 12,
                      relief="flat", command=command, cursor="hand2", font=("", 8), pady=0)
        b.image = img
        b.bind("<Enter>", lambda e: self.info.configure(text=unit.summary()))
        b.bind("<Leave>", lambda e: self.info.configure(text=""))
        return b

    def _reflow(self, inner):
        """Lay the cards out in as many columns as the pane is wide."""
        kids = inner.winfo_children()
        cell = (kids[0].winfo_reqwidth() + 2) if kids else 58
        width = inner.canvas.winfo_width()
        if width <= 1:                       # not laid out yet: as wide as it asks, never one column of 500 cards
            width = max(inner.canvas.winfo_reqwidth(), 600)  # (46 000 pixels tall - report #155, slow to open)
        cols = max(1, (width - 4) // cell)
        if cols == inner.cols and inner.winfo_children():
            return
        inner.cols = cols
        for i, w in enumerate(inner.winfo_children()):
            w.grid(row=i // cols, column=i % cols, padx=1, pady=1)

    # ---- content ----
    def visible(self):
        cat = self.v_cat.get()
        out = []
        owners = self._owners()
        for u in self.units:
            if cat != "all" and u.category != cat:
                continue
            whose = self.v_whose.get()
            own = not u.mercenary or bool(owners & set(u.ownership))
            if not own and whose == "own units" or not u.mercenary and whose == "mercenaries":
                continue
            if u.general and not self.v_gen.get():
                continue
            out.append(u)
        return sorted(out, key=lambda u: (u.category, u.upkeep, u.type))

    def _owners(self):
        """The names an ownership line lets this faction in by: its own, its culture, all."""
        culture = dict(self.mod.factions()).get(self.faction) if self.mod and self.faction else None
        return {x for x in (self.faction, culture, "all") if x}

    def fill_roster(self):
        for w in self.roster.winfo_children():
            w.destroy()
        for u in self.visible():
            self._card(self.roster, u, lambda u=u: self.add(u))
        self.roster.cols = 0
        self._reflow(self.roster)
        self.roster.canvas.yview_moveto(0)

    def fill_chosen(self):
        for w in self.chosen.winfo_children():
            w.destroy()
        for i, t in enumerate(self.garrison):
            self._card(self.chosen, self.by_type[t], lambda i=i: self.take(i))
        self.chosen.cols = 0
        self._reflow(self.chosen)
        if not self.units:
            self.total.configure(text="")
            return
        if not self.garrison:
            self.total.configure(text=getattr(self, "auto_text", None) or
                                 "automatic - the tool picks (see 'Leader's army' / 'Old garrisons')")
            return
        room = MAX_UNITS - (1 if self.held else 0)
        cost = sum(self.by_type[t].price for t in self.garrison)
        upkeep = sum(self.by_type[t].upkeep for t in self.garrison)
        self.total.configure(text="%s%d / %d units%s   cost %d   upkeep %d" % (
            "as it stands now (unchanged): " if getattr(self, "unchanged", False) else "",
            len(self.garrison), room, " (+ the bodyguard)" if self.held else "", cost, upkeep))

    # ---- actions ----
    def changed(self):
        self.unchanged = False
        self.fill_chosen()
        if self.on_change:
            self.on_change(list(self.garrison))

    def add(self, unit):
        if len(self.garrison) >= MAX_UNITS - (1 if self.held else 0):
            self.bell()
            return
        self.garrison.append(unit.type)
        self.changed()

    def take(self, i):
        del self.garrison[i]
        self.changed()

    def clear(self):
        self.cleared = True                        # 'Automatic': back to the town as it stands
        self.garrison = []
        self.changed()
        self.cleared = False

    def limits(self):
        """(lo, hi, cap) from the fields by Suggest - wrong or empty numbers read as the defaults, lo <= hi, hi
        within the room (a named general's bodyguard takes one); cap None for no limit. Kept for next time."""
        def num(v, default):
            try:
                return max(0, int(float(v.get())))
            except (ValueError, tk.TclError):
                return default
        room = MAX_UNITS - (1 if self.held else 0)
        lo, hi, cap = num(self.v_lo, 3), num(self.v_hi, 6), num(self.v_cap, 2000)
        hi = max(1, min(hi, room))
        lo = max(1, min(lo, hi))
        from . import settings
        for k, v in (("suggest_units_lo", lo), ("suggest_units_hi", hi), ("suggest_upkeep", cap)):
            settings.put(k, v)
        return lo, hi, (cap or None)

    def suggest(self):
        if self.auto:
            got = [t for t in self.auto(*self.limits()) if t in self.by_type]
            if not got:
                self.bell()
                self.total.configure(text="Suggest found nothing to draw from: no unit of this faction trains, or "
                                          "none fits under the upkeep limit")
                return
            self.garrison = got
            self.changed()
