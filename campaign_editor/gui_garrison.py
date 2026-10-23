"""The garrison picker: unit cards of the template's roster on the left, the
town's garrison on the right. Click a card to add it, click a garrison card to
take it out."""

import tkinter as tk
from tkinter import ttk

from .strat import entry_label, entry_stats, entry_type, with_stats
from .units import unit_card

try:                                   # pictures need Pillow; without it the cards are text
    from PIL import Image, ImageTk
except ImportError:                    # pragma: no cover - the exe always has it
    Image = ImageTk = None

from .start import ENGINE_UNITS, army_cap

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


def stats_marks(entry):
    """The marks under a card for a unit's numbers above 0: 'xp3 a1 w2' (the game shows chevrons and dots)."""
    e, a, w = entry_stats(entry)
    return " ".join(x for x in (("xp%d" % e) if e else "", ("a%d" % a) if a else "", ("w%d" % w) if w else "") if x)


class GarrisonEditor(ttk.Frame):
    """Roster cards on the left, the town's garrison on the right. Every change
    goes straight to on_change(list of units: a type, or a type with its exp / armour / weapon - strat.unit_entry).
    Left click adds / takes out; the right click opens a menu (the user, 2026-10-16: 'правый клик становится
    контекстным меню'): a unit's experience, armour, weapon, one more like it, all like it out, replace it; on the
    roster add several or with experience."""

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
        self.info = ttk.Label(self, text="", anchor="w", foreground="#444")
        self.info.pack(fill="x")
        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.LabelFrame(body, text="Roster - click to add, right click for more")
        right = ttk.LabelFrame(body, text="Garrison - click to take out, right click for more")
        body.add(left, weight=3)
        body.add(right, weight=2)
        self.roster = self._scroll(left)
        self.chosen = self._scroll(right)

        # the total on a line of its own: beside Suggest's numbers it had some 70 px and showed 'as it stand: (unchange'
        self.total = ttk.Label(self, text="", font=("", 10, "bold"), justify="left")
        self.total.pack(fill="x", pady=(4, 0))
        bar = ttk.Frame(self, padding=(0, 2, 0, 0))
        bar.pack(fill="x")
        self.total.bind("<Configure>", lambda e: self.total.configure(wraplength=max(120, e.width - 4)), add="+")
        # Suggest draws a garrison / an army by the numbers beside it - how many units, their upkeep together at
        # most (a tester, 2026-10-09: 'Suggest does nothing, and we cannot say how much upkeep'); kept for next time.
        # 'As it was' (once 'Automatic' - a tester: 'with Suggest, why Automatic?'): back to the garrison as it stands
        # in the files - only where there is one (an existing town); in New faction an empty garrison already means
        # 'the tool picks' (take every card out)
        from . import settings
        self.v_lo = tk.StringVar(value=str(settings.get("suggest_units_lo", 3)))
        self.v_hi = tk.StringVar(value=str(settings.get("suggest_units_hi", 6)))
        self.v_cap = tk.StringVar(value=str(settings.get("suggest_upkeep", 2000)))
        self.b_auto = ttk.Button(bar, text="As it was", command=self.clear)
        self.b_auto.pack(side="right", padx=4)
        self.sugg = ttk.Frame(bar)
        self.sugg.pack(side="right", padx=4)
        ttk.Label(self.sugg, text="units").pack(side="left")
        for v, w in ((self.v_lo, 3), (self.v_hi, 3)):
            ttk.Spinbox(self.sugg, from_=1, to=ENGINE_UNITS, textvariable=v, width=w).pack(side="left", padx=(2, 0))
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
        tip(self.b_auto, "Back to the garrison as it stands in the game's files now (your changes to it dropped).")


    def cap(self):
        """Units a stack holds here: 20, 40 with REX / M2EX (start.army_cap)."""
        return army_cap(self.mod) if self.mod is not None else 20

    def load(self, mod, faction, region, units, current, on_change, auto=None, held=False, unchanged=False,
             as_was=False, general=None):
        """unchanged: current is what stands in the town now, shown until the first click. auto(lo, hi, cap): the
        unit types Suggest draws (none: no Suggest); as_was: the As it was button (back to the town as it stands);
        general: (picture, words) of the general's own unit - his portrait card, first, as the game shows it (it
        stays: his bodyguard goes with him, not by a click)."""
        self.general = general
        self.unchanged = unchanged
        if auto:
            self.sugg.pack(side="right", padx=4)
        else:
            self.sugg.pack_forget()
        if as_was:                                # right of Suggest; packed 'before' only a packed one (TclError)
            self.b_auto.pack(side="right", padx=4, **({"before": self.sugg} if auto else {}))
        else:
            self.b_auto.pack_forget()
        self.mod, self.faction, self.units = mod, faction, units
        self.by_type = {u.type: u for u in units}
        self.garrison = [t for t in current if entry_type(t) in self.by_type]
        self.replacing = None
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

    def _card(self, parent, unit, command, entry=None, menu=None):
        path = unit_card(self.mod, unit, self.faction)
        img = self.pics.get(path) or self.pics.missing(unit.type)     # no picture: a grey card with its name
        text = unit.type if img is None else str(unit.upkeep)          # upkeep under the card
        marks = stats_marks(entry) if entry is not None else ""
        if marks:                                    # exp / armour / weapon above 0: shown under the card
            text = marks if img is not None else "%s\n%s" % (text, marks)
        b = tk.Button(parent, image=img, text=text, compound="top", wraplength=90, width=None if img else 12,
                      relief="flat", command=command, cursor="hand2", font=("", 8), pady=0)
        b.image = img
        words = unit.summary() + ((" - " + entry_label(entry)[len(unit.type):].strip(" ()")) if marks else "")
        b.bind("<Enter>", lambda e: self.info.configure(text=words))
        b.bind("<Leave>", lambda e: self.info.configure(text=""))
        if menu is not None:
            b.bind("<Button-3>", lambda e: menu(e))
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
            self._card(self.roster, u, lambda u=u: self.add(u), menu=lambda e, u=u: self.roster_menu(e, u))
        self.roster.cols = 0
        self._reflow(self.roster)
        self.roster.canvas.yview_moveto(0)

    def fill_chosen(self):
        for w in self.chosen.winfo_children():
            w.destroy()
        if getattr(self, "general", None) and self.held is True:
            path, words = self.general
            img = self.pics.get(path)
            if img is not None:                             # his face, not a cavalry card - the game's way
                g = tk.Label(self.chosen, image=img, text="general", compound="top", font=("", 8), pady=0)
                g.image = img
                g.bind("<Enter>", lambda e: self.info.configure(text=words))
                g.bind("<Leave>", lambda e: self.info.configure(text=""))
        for i, t in enumerate(self.garrison):
            self._card(self.chosen, self.by_type[entry_type(t)], lambda i=i: self.take(i), entry=t,
                       menu=lambda e, i=i: self.chosen_menu(e, i))
        self.chosen.cols = 0
        self._reflow(self.chosen)
        if not self.units:
            self.total.configure(text="")
            return
        if not self.garrison:
            self.total.configure(text=getattr(self, "auto_text", None) or
                                 "empty - the tool picks one (or press Suggest)")
            return
        room = self.cap() - (1 if self.held else 0)
        cost = sum(self.by_type[entry_type(t)].price for t in self.garrison)
        upkeep = sum(self.by_type[entry_type(t)].upkeep for t in self.garrison)
        self.total.configure(text="%s%d / %d units%s   cost %d   upkeep %d" % (
            "as it stands now (unchanged): " if getattr(self, "unchanged", False) else "",
            len(self.garrison), room, " (+ the bodyguard)" if self.held else "", cost, upkeep))

    # ---- actions ----
    def changed(self):
        self.unchanged = False
        self.fill_chosen()
        if self.on_change:
            self.on_change(list(self.garrison))

    def room(self):
        return self.cap() - (1 if self.held else 0) - len(self.garrison)

    def add(self, unit, n=1, exp=0):
        if self.replacing is not None:               # 'Replace with...' picked: this card takes its place
            i, self.replacing = self.replacing, None
            if 0 <= i < len(self.garrison):
                old = self.garrison[i]
                self.garrison[i] = with_stats(unit.type, *entry_stats(old))
                self.changed()
            return
        n = min(n, self.room())
        if n <= 0:
            self.bell()
            return
        self.garrison += [with_stats(unit.type, exp)] * n
        self.changed()

    # ---- the right click ----
    def _popup(self, e, m):
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def chosen_menu(self, e, i):
        """A unit of the garrison: its numbers, more like it, all like it out, replace it."""
        if not 0 <= i < len(self.garrison):
            return
        entry = self.garrison[i]
        t = entry_type(entry)
        ex, ar, we = entry_stats(entry)
        m = tk.Menu(self, tearoff=False)
        m.add_command(label=entry_label(entry), state="disabled")
        m.add_separator()
        for key, label, now, top in (("exp", "Experience", ex, 9), ("armour", "Armour", ar, max(ar, self._armour_top(t))),
                                     ("weapon", "Weapon", we, 3)):
            sub = tk.Menu(m, tearoff=False)
            sub.var = tk.IntVar(value=now)                       # kept with its menu (a lost one shows no dot)
            for v in range(top + 1):
                sub.add_radiobutton(label=str(v), value=v, variable=sub.var,
                                    command=lambda k=key, v=v: self.set_stats(i, **{k: v}))
            sub.add_separator()
            sub.add_command(label="Every %s here gets %d" % (t, now),
                            command=lambda k=key, v=now: self.set_stats(i, every=True, **{k: v}))
            m.add_cascade(label="%s: %d" % (label, now), menu=sub)
        m.add_separator()
        m.add_command(label="One more like it", command=lambda: self.more(i, 1))
        m.add_command(label="5 more like it", command=lambda: self.more(i, 5))
        m.add_command(label="Take out every %s" % t, command=lambda: self.take_all(t))
        m.add_command(label="Replace with... (then click a card on the left)", command=lambda: self.replace(i))
        m.add_separator()
        self._unit_items(m, t)
        m.add_separator()
        m.add_command(label="Take it out", command=lambda: self.take(i))
        self._popup(e, m)

    def _armour_top(self, unit):
        """The highest armour upgrade the unit has (its armour_ug_levels); 3 when its EDU block cannot be read."""
        tops = self.__dict__.setdefault("_tops", {})
        if (self.mod, unit) not in tops:
            from .models import armour_tiers, unit_lines
            try:
                lines = unit_lines(self.mod, unit) if self.mod else None
                n = armour_tiers(lines) if lines else None
            except Exception:  # a broken EDU: offer what the game's own cap allows
                n = None
            tops[(self.mod, unit)] = n - 1 if n else 3
        return tops[(self.mod, unit)]

    def _unit_items(self, m, unit):
        """The unit itself: in the Unit editor, in 3D, where it is recruited (BACKLOG A1)."""
        app = self._app_of()
        if app is None:
            return
        m.add_command(label="Open in the Unit editor", command=lambda: app.open_unit(unit))
        m.add_command(label="View in 3D...", command=lambda: app.open_unit(unit, view3d=True))
        m.add_command(label="Where it is recruited...", command=lambda: self._where(app, unit))

    def _app_of(self):
        w = self
        while w is not None:
            if hasattr(w, "open_unit"):
                return w
            w = getattr(w, "master", None)
        return None

    def _where(self, app, unit):
        from types import SimpleNamespace
        from .buildwhere import open_where
        return open_where(SimpleNamespace(app=app, mod=app.mod, kind="unit"), unit, parent=self.winfo_toplevel())

    def roster_menu(self, e, unit):
        """A roster card: add several, add with experience."""
        m = tk.Menu(self, tearoff=False)
        m.add_command(label=unit.type, state="disabled")
        m.add_separator()
        for n in (1, 2, 5):
            m.add_command(label="Add %d" % n, command=lambda n=n: self.add(unit, n))
        m.add_command(label="Add to fill the army (%d)" % max(0, self.room()), command=lambda: self.add(unit, self.room()))
        sub = tk.Menu(m, tearoff=False)
        for v in range(1, 10):
            sub.add_command(label="Experience %d" % v, command=lambda v=v: self.add(unit, 1, v))
        m.add_cascade(label="Add with experience", menu=sub)
        m.add_separator()
        self._unit_items(m, unit.type)
        self._popup(e, m)

    def set_stats(self, i, every=False, **values):
        """exp / armour / weapon of the unit at i - or, every: of every unit of its type here."""
        if not 0 <= i < len(self.garrison):
            return
        t = entry_type(self.garrison[i])
        for k in range(len(self.garrison)):
            if k == i or every and entry_type(self.garrison[k]) == t:
                self.garrison[k] = with_stats(self.garrison[k], **values)
        self.changed()

    def more(self, i, n):
        n = min(n, self.room())
        if n <= 0 or not 0 <= i < len(self.garrison):
            self.bell()
            return
        self.garrison[i + 1:i + 1] = [self.garrison[i]] * n
        self.changed()

    def take_all(self, t):
        self.garrison = [x for x in self.garrison if entry_type(x) != t]
        self.changed()

    def replace(self, i):
        self.replacing = i
        self.total.configure(text="Replace %s: click the unit to put in its place on the left (it keeps the "
                                  "numbers)" % entry_type(self.garrison[i]))

    def take(self, i):
        self.replacing = None
        del self.garrison[i]
        self.changed()

    def clear(self):
        self.cleared = True                        # 'As it was': back to the town as it stands
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
        room = self.cap() - (1 if self.held else 0)
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
