"""A look at a building chain or a unit as the game shows it - for the lists where one is picked (New building /
New unit step by step, Bring from another mod): its pictures, the name and description players read (by culture
for buildings), and what it does in plain words (effects.py), not the file's code. Works on any mod (the other
mod in Bring), both games."""

import os
import tkinter as tk
from tkinter import ttk

from . import editors as E
from . import theme
from .effects import level_words, requires_words
from .textio import strip_comment

try:
    from PIL import Image, ImageTk
except Exception:                                   # the window works without Pillow, only without pictures
    Image = ImageTk = None


def text_value(mod, table, key):
    """{key}'s text in a string table of mod (lines joined), '' when missing."""
    from .gui_newrecord import _text_value
    try:
        return _text_value(mod, table, key)
    except Exception:
        return ""


def _real(text, key):
    """A text players really read: not empty, not the key itself, not the 'DO NOT TRANSLATE' stand-in that both
    games keep under the plain key when the real text lies under <level>_<culture>."""
    t = (text or "").strip()
    return bool(t) and t != key and "DO NOT TRANSLATE" not in t and not t.startswith("WARNING!")


def level_text(mod, level, culture):
    """(name, description) players read for a building level and culture: <level>_<culture>, then <level>, then
    the first other culture's own text (each taken only when it is a real text)."""
    cults = sorted({c for _, c in mod.factions() if c})
    order = [level + "_" + culture, level] + [level + "_" + c for c in cults if c != culture]
    name = next((t for t in (text_value(mod, "export_buildings.txt", k) for k in order) if _real(t, level)), "")
    desc = next((t for t in (text_value(mod, "export_buildings.txt", k + "_desc") for k in order)
                 if _real(t, level)), "")
    return name, desc


def _photo(path, box):
    if not path or Image is None or not os.path.isfile(path):
        return None
    try:
        with Image.open(path) as im:
            im.load()
            im = im.convert("RGBA")
            im.thumbnail(box)
            return ImageTk.PhotoImage(im)
    except Exception:
        return None


class _Base(ttk.Frame):
    def __init__(self, master, mod=None):
        super().__init__(master, padding=(8, 0))
        self.mod = mod
        self._photos = []
        self.title = ttk.Label(self, font=("", 10, "bold"), wraplength=360, justify="left")
        self.title.pack(anchor="w")
        self.bar = ttk.Frame(self)
        self.bar.pack(fill="x", pady=(2, 4))
        self.pics = ttk.Frame(self)
        self.pics.pack(anchor="w")
        box = ttk.Frame(self)
        box.pack(fill="both", expand=True, pady=(4, 0))
        self.text = tk.Text(box, wrap="word", height=12, width=46, relief="flat", font=("", 9))
        sb = ttk.Scrollbar(box, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.text.tag_configure("h", font=("", 9, "bold"))
        self.text.tag_configure("dim", foreground=theme.ink("#777", "field"))

    def _pic(self, path, box, label):
        f = ttk.Frame(self.pics)
        f.pack(side="left", padx=(0, 10))
        ph = _photo(path, box)
        if ph:
            self._photos.append(ph)
            ttk.Label(f, image=ph).pack()
        else:
            ttk.Label(f, text="(no picture)", foreground="#888", width=14, anchor="center").pack(pady=10)
        ttk.Label(f, text=label, foreground="#666").pack()

    def _write(self, parts):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        for text, tag in parts:
            self.text.insert("end", text, tag or ())
        self.text.configure(state="disabled")

    def _clear(self):
        for w in self.pics.winfo_children() + self.bar.winfo_children():
            w.destroy()
        self._photos = []


class BuildingPreview(_Base):
    """A chain: pick a level and a culture; its pictures (in town, when built), the name and description players
    read for that culture, who may build it and what it does."""

    def __init__(self, master, mod=None):
        super().__init__(master, mod)
        self.chain = None
        self.v_level, self.v_cult = tk.StringVar(), tk.StringVar()
        self._pics = None

    def show(self, chain, mod=None):
        if mod is not None and mod is not self.mod:
            self.mod, self._pics = mod, None
        self.chain = chain
        self._clear()
        if not chain or not self.mod or not self.mod.file("edb"):
            self.title.configure(text="")
            self._write([])
            return
        from .buildings import BuildingPictures
        f = self.mod.load(self.mod.file("edb"))
        blk = next((b for b in E.building_blocks(f) if b[0] == chain), None)
        if blk is None:
            return
        self.f, self.tree = f, E.chain_tree(f, blk[1], blk[2])
        levels = [lv["name"] for lv in self.tree["levels"]]
        if self._pics is None:
            self._pics = BuildingPictures(self.mod)
        cults = sorted({c for _, c in self.mod.factions() if c})
        if self.v_level.get() not in levels:
            self.v_level.set(levels[0] if levels else "")
        if self.v_cult.get() not in cults:
            # the first culture that has a picture of the first level
            self.v_cult.set(next((c for c in cults if levels and self._pics.find(c, levels[0])),
                                 cults[0] if cults else ""))
        ttk.Label(self.bar, text="Level").pack(side="left")
        cb = ttk.Combobox(self.bar, textvariable=self.v_level, values=levels, state="readonly", width=22)
        cb.pack(side="left", padx=4)
        ttk.Label(self.bar, text="Culture").pack(side="left", padx=(6, 0))
        cc = ttk.Combobox(self.bar, textvariable=self.v_cult, values=cults, state="readonly", width=14)
        cc.pack(side="left", padx=4)
        for w in (cb, cc):
            w.bind("<<ComboboxSelected>>", lambda e: self.show(self.chain))
        self.title.configure(text="building %s" % chain)
        self._level()

    def _level(self):
        lv = next((x for x in self.tree["levels"] if x["name"] == self.v_level.get()), None)
        if lv is None:
            return
        name, cult = lv["name"], self.v_cult.get()
        self._pic(self._pics.find(cult, name), (110, 90), "in the town")
        self._pic(self._pics.find(cult, name, True), (200, 90), "when built")
        shown, desc = level_text(self.mod, name, cult)
        parts = [(shown or name.replace("_", " "), "h"), ("\n", None)]
        if desc:
            parts += [(desc.strip() + "\n", None)]
        parts += [("\nWho may build it: ", "h"), (requires_words(self.f.text(lv["head"])) + "\n", None)]
        lines = [self.f.text(i) for i in range(lv["open"], lv["close"] + 1)]
        for key, label in (("construction", "turns to build"), ("cost", "cost"), ("settlement_min", "town at least")):
            for l in lines:
                t = strip_comment(l).split()
                if t[:1] == [key] and len(t) > 1:
                    parts += [("%s: " % label, "h"), (t[1] + "\n", None)]
        if lv["capability"]:
            words = level_words(self.f.text(i) for i in range(lv["capability"][0], lv["capability"][1] + 1))
            parts += [("\nWhat it does:\n", "h")] + [("  - %s\n" % w, None) for w in words]
        up = lv["upgrades"]
        if up:
            nxt = [strip_comment(self.f.text(i)).strip() for i in range(up[0] + 1, up[1])]
            nxt = [x for x in nxt if x and x not in "{}"]
            if nxt:
                parts += [("\nUpgrades to: ", "h"), (", ".join(nxt) + "\n", None)]
        self._write(parts)


class UnitPreview(_Base):
    """A unit: its card and description picture, the name and short description players read, and its numbers in
    plain words."""

    def show(self, unit, mod=None):
        if mod is not None:
            self.mod = mod
        self._clear()
        if not unit or not self.mod or not self.mod.file("edu"):
            self.title.configure(text="")
            self._write([])
            return
        from .packs import type_blocks
        from .units import card_path
        f = self.mod.load(self.mod.file("edu"))
        span = type_blocks(f).get(unit)
        if not span:
            return
        lines = [f.text(i) for i in range(*span)]

        def val(key):
            for l in lines:
                t = strip_comment(l).split(None, 1)
                if t[:1] == [key]:
                    return t[1].strip() if len(t) > 1 else ""
            return ""

        def nums(key):
            return [x.strip() for x in val(key).split(",")]
        dic = val("dictionary") or unit.replace(" ", "_")
        owners = [x.strip() for x in val("ownership").split(",") if x.strip()]
        first = owners[0] if owners else ""
        self.title.configure(text="unit %s" % unit)
        from .units import owner_factions
        facs = owner_factions(self.mod, owners)
        merc = "mercenary_unit" in val("attributes").replace(",", " ").split()
        self._pic(card_path(self.mod, facs[0] if facs else first, dic, owners=facs, mercenary=merc), (60, 80), "card")
        self._pic(card_path(self.mod, facs[0] if facs else first, dic, True, owners=facs, mercenary=merc),
                  (120, 160), "description")
        name = text_value(self.mod, "export_units.txt", dic) or unit
        short = text_value(self.mod, "export_units.txt", dic + "_descr_short")
        parts = [(name + "\n", "h")]
        if short:
            parts.append((short.strip() + "\n", None))
        sol = nums("soldier")
        pri = nums("stat_pri")
        arm = nums("stat_pri_armour")
        cost = nums("stat_cost")
        rows = [("kind", "%s %s" % (val("class"), val("category"))),
                ("men", sol[1] if len(sol) > 1 else ""),
                ("rides", val("mount")),
                ("attack / charge", "%s / %s" % (pri[0], pri[1]) if len(pri) > 1 else ""),
                ("range / ammunition", "%s / %s" % (pri[3], pri[4]) if len(pri) > 4 and pri[3] not in ("0", "") else ""),
                ("armour / defence / shield", " / ".join(arm[:3]) if len(arm) > 2 else ""),
                ("hit points", val("stat_health")),
                ("morale", nums("stat_mental")[0] if val("stat_mental") else ""),
                ("cost / upkeep", "%s / %s" % (cost[1], cost[2]) if len(cost) > 2 else ""),
                ("turns to train", cost[0] if cost and cost[0] else ""),
                ("owned by", ", ".join(owners)),
                ("abilities", val("attributes"))]
        parts.append(("\n", None))
        for label, v in rows:
            if v and v.strip(" /"):
                parts += [("%s: " % label, "h"), (v + "\n", None)]
        self._write(parts)
