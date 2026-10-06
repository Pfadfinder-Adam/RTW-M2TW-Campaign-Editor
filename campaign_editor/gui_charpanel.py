"""The Character editor's panel: the picked person as the game's character panel shows him - the portrait in a
frame, name, who he is, age, the attributes as pips, the traits by the names players see, the retinue as picture
cards (charpanel reads it all from the files). It only shows; the form beside it edits."""

import math
import tkinter as tk
from tkinter import ttk


PARCHMENT, INK, MUTED, GOLD = "#efe6d2", "#2b2118", "#6b5a45", "#b08d3c"
PIP = {"Command": "#c9a227", "Chivalry": "#3d6fb8", "Dread": "#8a1f1f", "Loyalty": "#3f7f3f",
       "Authority": "#7a2ea0", "Piety": "#9c7a2a", "Influence": "#3d6fb8", "Management": "#3f7f3f",
       "Subterfuge": "#555555", "Charm": "#c05080", "Finance": "#c9a227"}


class CharacterPanel(ttk.Frame):
    def __init__(self, master, on_pip=None):
        super().__init__(master)
        self.on_pip = on_pip                 # on_pip(attribute, value): a click on the pips
        self.cv = tk.Canvas(self, bg=PARCHMENT, highlightthickness=0)
        ys = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Configure>", lambda e: self.redraw())
        self._imgs, self._last = [], None

    def show(self, data, portrait=None, image=None):
        """data: charpanel.panel(...) or None; portrait: the picture file. The pictures are fitted to their boxes,
        small ones made bigger (a retinue card's picture is small in the files)."""
        self._last = (data, portrait, self._fit)
        self.redraw()

    def _fit(self, path, w, h):
        from PIL import Image, ImageTk
        key = (path, w, h)
        cache = self.__dict__.setdefault("_cache", {})
        if key not in cache:
            try:
                with Image.open(path) as im:
                    im = im.convert("RGBA")
                    k = min(w / im.width, h / im.height)
                    cache[key] = ImageTk.PhotoImage(im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))),
                                                              Image.LANCZOS))
            except Exception:
                cache[key] = None
        return cache[key]

    def redraw(self):
        c = self.cv
        c.delete("all")
        self._imgs = []
        if not self._last or not self._last[0]:
            c.create_text(20, 20, anchor="nw", fill=MUTED, text="Pick a person in the list (or on the family tree).")
            return
        d, portrait, image = self._last
        w = max(c.winfo_width(), 360)
        x0, y = 16, 16
        # the portrait in a gold frame
        pw, ph = 104, 144
        img = image(portrait, pw, ph) if image and portrait else None
        c.create_rectangle(x0 - 4, y - 4, x0 + pw + 4, y + ph + 4, outline=GOLD, width=4)
        c.create_rectangle(x0, y, x0 + pw, y + ph, fill="#d8cdb4", outline="")
        if img:
            self._imgs.append(img)
            c.create_image(x0 + pw / 2, y + ph / 2, image=img)
        tx = x0 + pw + 20
        c.create_text(tx, y, anchor="nw", text=d["name"], fill=INK, font=("", 16, "bold"))
        c.create_text(tx, y + 30, anchor="nw", text=d["line"], fill=MUTED, font=("", 10))
        if d.get("age") is not None:
            c.create_text(tx, y + 50, anchor="nw", text="Age %s" % d["age"], fill=INK, font=("", 10))
        ay = y + 76
        for name, value in d["attributes"]:
            c.create_text(tx, ay, anchor="nw", text=name, fill=INK, font=("", 10, "bold"))
            self._pips(tx + 116, ay + 8, value, PIP.get(name, GOLD), name)
            c.create_text(tx + 116 + 10 * 17 + 8, ay, anchor="nw", text=str(value), fill=MUTED, font=("", 9))
            ay += 22
        y = max(y + ph + 20, ay + 10)
        # the traits
        c.create_line(x0, y, w - 16, y, fill=GOLD)
        c.create_text(x0, y + 6, anchor="nw", text="Traits", fill=INK, font=("", 11, "bold"))
        y += 30
        if not d["traits"]:
            c.create_text(x0, y, anchor="nw", text="none", fill=MUTED)
            y += 20
        for shown, trait, level, eff in d["traits"]:
            a = c.create_text(x0, y, anchor="nw", text=shown, fill=INK, font=("", 10, "bold"), width=220)
            b = c.create_text(x0 + 230, y, anchor="nw", fill=MUTED, font=("", 9), width=max(120, w - x0 - 260),
                              text=(eff + "   " if eff else "") + "(%s %d)" % (trait, level))
            # the next row under the taller of the two (a long effect wraps to more lines - they overlapped)
            y = max(c.bbox(a)[3], c.bbox(b)[3], y + 16) + 6
        # the retinue: picture cards
        y += 8
        c.create_line(x0, y, w - 16, y, fill=GOLD)
        c.create_text(x0, y + 6, anchor="nw", text="Retinue", fill=INK, font=("", 11, "bold"))
        y += 30
        if not d["retinue"]:
            c.create_text(x0, y, anchor="nw", text="none" if d["attributes"] else
                          "none (a person off the map has no retinue)", fill=MUTED)
            y += 20
        cw, chh = 112, 168                                   # room for a two-line name and its effects
        x = x0
        for shown, anc, pic, eff in d["retinue"]:
            if x + cw > w - 8 and x > x0:
                x, y = x0, y + chh + 10
            c.create_rectangle(x, y, x + cw - 8, y + chh, outline=GOLD, width=2, fill="#e6dcc3")
            im = image(pic, cw - 16, 96) if image and pic else None
            if im:
                self._imgs.append(im)
                c.create_image(x + (cw - 8) / 2, y + 52, image=im)
            else:
                c.create_text(x + (cw - 8) / 2, y + 52, text="(no picture)", fill=MUTED, font=("", 8))
            t = c.create_text(x + (cw - 8) / 2, y + 104, anchor="n", text=shown, fill=INK, width=cw - 14,
                              font=("", 9, "bold"), justify="center")
            if eff:                                      # under the name, however many lines the name took
                c.create_text(x + (cw - 8) / 2, c.bbox(t)[3] + 1, anchor="n", text=eff, fill=MUTED,
                              width=cw - 14, font=("", 7), justify="center")
            x += cw
        y += chh + 16
        c.configure(scrollregion=(0, 0, w, y))

    def _pips(self, x, y, value, colour, name=None):
        """Ten pips (stars), the first `value` filled; more than ten: all filled. A click on pip k asks for the
        value k (the filled last one again: one less) - the traits are fitted to it."""
        c = self.cv
        if self.on_pip and name:
            tag = "pips_" + name
            c.create_rectangle(x, y - 9, x + 10 * 17 + 4, y + 9, outline="", fill="", tags=tag)
            c.tag_bind(tag, "<Button-1>", lambda e: self.on_pip(
                name, (lambda k: k - 1 if k == value else k)(min(10, max(0, int((e.x - x) // 17) + 1)))))
            c.tag_bind(tag, "<Enter>", lambda e: c.configure(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.configure(cursor=""))
        for k in range(10):
            cx = x + k * 17 + 7
            pts = []
            for j in range(10):
                r = 7 if j % 2 == 0 else 3
                a = -math.pi / 2 + j * math.pi / 5
                pts += [cx + r * math.cos(a), y + r * math.sin(a)]
            c.create_polygon(pts, fill=colour if k < value else "", outline=colour if k < value else "#b9ab8e",
                             tags=("pips_" + name,) if self.on_pip and name else ())
