"""The garrison picker: unit cards of the template's roster on the left, the
town's garrison on the right. Click a card to add it, click a garrison card to
take it out."""

import tkinter as tk
from tkinter import ttk

from .units import card_path

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

        top = ttk.Frame(self, padding=(0, 0, 0, 4))
        top.pack(fill="x")
        self.title = ttk.Label(top, text="Pick a town on the left", font=("", 10, "bold"))
        self.title.pack(side="left")
        ttk.Label(top, text="   Show").pack(side="left")
        self.v_cat = tk.StringVar(value="all")
        self.cb_cat = ttk.Combobox(top, textvariable=self.v_cat, values=["all"], state="readonly", width=12)
        self.cb_cat.pack(side="left", padx=4)
        self.cb_cat.bind("<<ComboboxSelected>>", lambda e: self.fill_roster())
        self.v_merc = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="mercenaries", variable=self.v_merc, command=self.fill_roster).pack(side="left", padx=8)
        self.v_gen = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="general's units", variable=self.v_gen, command=self.fill_roster).pack(side="left")

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
        self.total = ttk.Label(bar, text="", font=("", 10, "bold"))
        self.total.pack(side="left")
        ttk.Button(bar, text="Automatic", command=self.clear).pack(side="right", padx=4)
        ttk.Button(bar, text="Suggest", command=self.suggest).pack(side="right", padx=4)

    def load(self, mod, faction, region, units, current, on_change, auto=None, held=False, unchanged=False):
        """unchanged: current is what stands in the town now, shown until the first click."""
        self.unchanged = unchanged
        self.mod, self.faction, self.units = mod, faction, units
        self.by_type = {u.type: u for u in units}
        self.garrison = [t for t in current if t in self.by_type]
        self.on_change, self.auto, self.held = on_change, auto, held
        self.title.configure(text="%s%s" % (region, " - the %s's town" % held if held else ""))
        self.cb_cat["values"] = ["all"] + sorted({u.category for u in units if u.category})
        self.fill_roster()
        self.fill_chosen()

    # ---- layout helpers ----
    def _scroll(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner.canvas = canvas
        inner.cols = 0
        canvas.bind("<Configure>", lambda e: self._reflow(inner), add="+")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>",
                    lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        return inner

    def _card(self, parent, unit, command):
        path = card_path(self.mod, self.faction, unit.dictionary)
        img = self.pics.get(path)
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
        cols = max(1, (inner.canvas.winfo_width() - 4) // cell)
        if cols == inner.cols and inner.winfo_children():
            return
        inner.cols = cols
        for i, w in enumerate(inner.winfo_children()):
            w.grid(row=i // cols, column=i % cols, padx=1, pady=1)

    # ---- content ----
    def visible(self):
        cat = self.v_cat.get()
        out = []
        for u in self.units:
            if cat != "all" and u.category != cat:
                continue
            if u.mercenary and not self.v_merc.get():
                continue
            if u.general and not self.v_gen.get():
                continue
            out.append(u)
        return sorted(out, key=lambda u: (u.category, u.upkeep, u.type))

    def fill_roster(self):
        for w in self.roster.winfo_children():
            w.destroy()
        for u in self.visible():
            self._card(self.roster, u, lambda u=u: self.add(u))
        self.roster.cols = 0
        self._reflow(self.roster)

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
        self.garrison = []
        self.changed()

    def suggest(self):
        if self.auto:
            self.garrison = [t for t in self.auto() if t in self.by_type]
            self.changed()
