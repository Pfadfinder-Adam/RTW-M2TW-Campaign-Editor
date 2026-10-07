"""Hover a unit or a building in ANY list or table of the editor: its card shows beside the mouse - the picture
the game shows and a line of what it is (the user, 2026-10-07: 'in any table, in any list, so we can see what it
is'). One binding for every Treeview and Listbox (bind_class); a row is matched by the words in its cells, so no
window needs its own code."""

import tkinter as tk
from tkinter import ttk

DELAY = 450                     # ms the mouse rests on a row before the card shows


class Cards:
    """What the loaded mod knows: unit types and building levels / chains by name, read once per mod."""

    def __init__(self, mod, culture=None):
        self.mod = mod
        self.culture = culture or (lambda: None)   # () -> the culture of the faction picked now (its pictures first)
        self.units, self.levels, self.chains = {}, {}, {}
        self._bpics = None
        try:
            from .units import read_units
            edu = mod.file("edu")
            for u in (read_units(mod.load(edu)) if edu else []):
                self.units.setdefault(u.type, u)
        except Exception:
            pass
        try:
            from .buildings import read_buildings
            edb = mod.file("edb")
            for b in (read_buildings(mod.load(edb)) if edb else []):
                self.chains.setdefault(b.name, b)
                for lv in b.levels:
                    self.levels.setdefault(lv.name, (b, lv))
        except Exception:
            pass

    def _words(self, text):
        """The names a cell may hold: the whole text, then its pieces ('chain / level', 'name (tag)', 'x - y')."""
        text = str(text or "").strip()
        out = [text]
        for sep in (" / ", " (", " - ", ": ", ", "):
            for piece in text.split(sep):
                piece = piece.strip(" )")
                if piece and piece not in out:
                    out.append(piece)
        return out

    def find(self, texts):
        """(kind, name) of the first unit / building level / chain named in texts (unit types first)."""
        for t in texts:
            for w in self._words(t):
                if w in self.units:
                    return "unit", w
        for t in texts:
            for w in self._words(t):
                if w in self.levels:
                    return "level", w
                if w in self.chains:
                    return "chain", w
        return None

    def unit_card(self, name):
        from .units import card_path
        u = self.units[name]
        path = card_path(self.mod, None, u.dictionary) if u.dictionary else None
        return path, u.summary()

    def building_card(self, kind, name):
        from .buildings import BuildingPictures
        if self._bpics is None:
            self._bpics = BuildingPictures(self.mod)
        if kind == "chain":
            b = self.chains[name]
            lv = b.levels[0] if b.levels else None
        else:
            b, lv = self.levels[name]
        path = None
        if lv is not None:
            for culture in self._cultures():
                path = self._bpics.find(culture, lv.name)
                if path:
                    break
        words = "%s - building %s" % (name, b.name)
        if lv is not None:
            words += ", level %s" % lv.name
            if getattr(lv, "cost", 0):
                words += ", costs %d" % lv.cost
            if getattr(lv, "turns", 0):
                words += ", %d turn(s) to build" % lv.turns
        if kind == "chain" and b.levels:
            words += " (levels: %s)" % ", ".join(x.name for x in b.levels[:8])
        return path, words

    def _cultures(self):
        """Every culture folder the pictures sit in (ui/<culture>/buildings) - the first one holding the level."""
        first = self.culture()
        rest = sorted(self._bpics.index) if self._bpics else []
        return ([first] if first else []) + [c for c in rest if c != first]


def install(root, mod_of, pictures, culture=None):
    """Every Treeview and Listbox shows the card of the unit / building its hovered row names. mod_of() -> the
    loaded ModData (or None); pictures = the app's card cache (gui_garrison.Pictures)."""
    state = {"job": None, "win": None, "row": None, "cards": None, "for": None}

    def cards():
        mod = mod_of()
        if mod is None:
            return None
        if state["for"] is not mod:
            state["cards"], state["for"] = Cards(mod, culture), mod
        return state["cards"]

    def hide(_=None):
        if state["job"]:
            try:
                root.after_cancel(state["job"])
            except tk.TclError:
                pass
            state["job"] = None
        if state["win"] is not None:
            try:
                state["win"].destroy()
            except tk.TclError:
                pass
            state["win"] = None
        state["row"] = None

    def texts_at(w, y):
        try:
            if isinstance(w, ttk.Treeview):
                row = w.identify_row(y)
                if not row:
                    return None, []
                return row, [w.item(row, "text")] + [str(v) for v in (w.item(row, "values") or ())]
            i = w.nearest(y)
            if i < 0 or i >= w.size():
                return None, []
            bbox = w.bbox(i)
            if not bbox or not (bbox[1] <= y <= bbox[1] + bbox[3]):
                return None, []
            return i, [w.get(i)]
        except tk.TclError:
            return None, []

    def show(w, x, y, hit):
        state["job"] = None
        c = cards()
        if c is None:
            return
        try:
            kind, name = hit
            path, words = c.unit_card(name) if kind == "unit" else c.building_card(kind, name)
        except Exception:
            return
        from . import theme
        pal = theme.palette()
        win = tk.Toplevel(root)
        win.wm_overrideredirect(True)
        try:
            win.attributes("-alpha", 1.0)
        except tk.TclError:
            pass
        frm = tk.Frame(win, background=pal.get("field", "#ffffff"), borderwidth=1, relief="solid")
        frm.pack()
        size = (48, 64) if kind == "unit" else (78, 62)
        img = pictures.get(path, size=size) if path else None
        if img is not None:
            lbl = tk.Label(frm, image=img, background=pal.get("field", "#ffffff"))
            lbl.image = img
            lbl.pack(side="left", padx=4, pady=4)
        tk.Label(frm, text=words, justify="left", wraplength=320, background=pal.get("field", "#ffffff"),
                 foreground=pal.get("fg", "#000000")).pack(side="left", padx=(2, 6), pady=4)
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        px = min(x + 18, sw - win.winfo_reqwidth() - 4)
        win.wm_geometry("+%d+%d" % (max(0, px), y + 14))
        state["win"] = win

    def motion(e):
        w = e.widget
        if not isinstance(w, (ttk.Treeview, tk.Listbox)):
            return
        row, texts = texts_at(w, e.y)
        if row == state["row"] and (state["win"] is not None or state["job"]):
            return
        hide()
        if row is None:
            return
        c = cards()
        hit = c.find(texts) if c is not None else None
        if hit is None:
            return
        state["row"] = row
        x, y = e.x_root, e.y_root
        state["job"] = root.after(DELAY, lambda: show(w, x, y, hit))

    for cls in ("Treeview", "Listbox"):
        root.bind_class(cls, "<Motion>", motion, add="+")
        root.bind_class(cls, "<Leave>", hide, add="+")
        root.bind_class(cls, "<ButtonPress>", hide, add="+")
        root.bind_class(cls, "<MouseWheel>", hide, add="+")
