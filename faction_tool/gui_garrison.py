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
COLUMNS = 8


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


class GarrisonWindow(tk.Toplevel):
    def __init__(self, master, mod, faction, region, units, current, on_ok, auto=None, held=False, pictures=None):
        """units: [Unit] to choose from; current: [unit type]; on_ok(list of types);
        auto(): a suggested list; held: the leader/heir's bodyguard comes on top."""
        super().__init__(master)
        self.title("Garrison of %s" % region)
        self.geometry("980x640")
        self.mod, self.faction, self.units = mod, faction, units
        self.by_type = {u.type: u for u in units}
        self.garrison = [t for t in current if t in self.by_type]
        self.on_ok, self.auto, self.held = on_ok, auto, held
        self.pics = pictures or Pictures()

        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Show").pack(side="left")
        self.v_cat = tk.StringVar(value="all")
        cats = ["all"] + sorted({u.category for u in units if u.category})
        cb = ttk.Combobox(top, textvariable=self.v_cat, values=cats, state="readonly", width=12)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill_roster())
        self.v_merc = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="mercenaries", variable=self.v_merc, command=self.fill_roster).pack(side="left", padx=8)
        self.v_gen = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="general's units", variable=self.v_gen, command=self.fill_roster).pack(side="left")
        self.info = ttk.Label(top, text="", anchor="e")
        self.info.pack(side="right", fill="x", expand=True)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6)
        left = ttk.LabelFrame(body, text="Roster - click to add")
        right = ttk.LabelFrame(body, text="Garrison - click to take out")
        body.add(left, weight=3)
        body.add(right, weight=2)
        self.roster = self._scroll(left)
        self.chosen = self._scroll(right)

        bar = ttk.Frame(self, padding=6)
        bar.pack(fill="x")
        self.total = ttk.Label(bar, text="", font=("", 10, "bold"))
        self.total.pack(side="left")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="OK", command=self.ok).pack(side="right", padx=4)
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="right", padx=4)
        if auto:
            ttk.Button(bar, text="Suggest", command=self.suggest).pack(side="right", padx=4)
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
        for i, u in enumerate(self.visible()):
            b = self._card(self.roster, u, lambda u=u: self.add(u))
            b.grid(row=i // COLUMNS, column=i % COLUMNS, padx=1, pady=1)

    def fill_chosen(self):
        for w in self.chosen.winfo_children():
            w.destroy()
        cols = COLUMNS // 2 + 1
        for i, t in enumerate(self.garrison):
            b = self._card(self.chosen, self.by_type[t], lambda i=i: self.take(i))
            b.grid(row=i // cols, column=i % cols, padx=1, pady=1)
        room = MAX_UNITS - (1 if self.held else 0)
        cost = sum(self.by_type[t].price for t in self.garrison)
        upkeep = sum(self.by_type[t].upkeep for t in self.garrison)
        self.total.configure(text="%d / %d units%s   cost %d   upkeep %d" % (
            len(self.garrison), room, " (+ the bodyguard)" if self.held else "", cost, upkeep))

    # ---- actions ----
    def add(self, unit):
        if len(self.garrison) >= MAX_UNITS - (1 if self.held else 0):
            self.bell()
            return
        self.garrison.append(unit.type)
        self.fill_chosen()

    def take(self, i):
        del self.garrison[i]
        self.fill_chosen()

    def clear(self):
        self.garrison = []
        self.fill_chosen()

    def suggest(self):
        self.garrison = [t for t in self.auto() if t in self.by_type]
        self.fill_chosen()

    def ok(self):
        self.on_ok(list(self.garrison))
        self.destroy()
