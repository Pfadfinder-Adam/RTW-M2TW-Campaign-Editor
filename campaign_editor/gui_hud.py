"""Interface > Campaign HUD: the strategy map's bottom panel as the game draws it (hudlayout - the engines' own places,
both games), from the mod's own pictures and with the changes waiting on the Sprite sheets tab. Hover names a piece;
its right click replaces its picture or sets its place and size (the Sprite sheets tab's own ways - one place for
the changes, Apply writes them), shows it on its sheet, or saves the whole HUD as a PNG. 'Screen' stretches the
1024 x 768 layout as the game does on a bigger screen (x and y apart)."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import hudlayout as H
from . import theme

TITLE = "Campaign HUD"
SCREENS = ["1024 x 768 (the layout)", "1280 x 1024", "1600 x 900", "1920 x 1080", "2560 x 1440"]


class HudPanel(ttk.Frame):
    def __init__(self, master, app, interface):
        super().__init__(master)
        self.app, self.interface = app, interface
        self.mod, self.items, self.picked, self.hover = None, [], None, None
        self._img, self._photo, self._scale = None, None, 1.0
        bar = ttk.Frame(self, padding=(10, 8, 10, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="Screen").pack(side="left")
        self.v_screen = tk.StringVar(value=SCREENS[0])
        cb = ttk.Combobox(bar, textvariable=self.v_screen, values=SCREENS, state="readonly", width=24)
        cb.pack(side="left", padx=(4, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self.redraw())
        ttk.Button(bar, text="Draw again", command=self.redraw).pack(side="left")
        from .gui_util import hint
        hint(bar, "The campaign map's bottom panel (HUD) as the game draws it: the places are the game's own, the "
                  "pictures the mod's (and your changes waiting for Apply). Everything is laid out on 1024 x 768 and "
                  "the whole of it is stretched to the screen - 'Screen' shows how it looks on a bigger one. Right "
                  "click a piece: replace its picture, set its place and size on its sheet, show it on the Sprite "
                  "sheets tab, save the whole HUD as a PNG. Unit cards, the radar map and the words are shown "
                  "as examples.", width=560).pack(side="left", padx=6)
        self.lbl = ttk.Label(self, foreground=theme.palette()["muted"], padding=(10, 0))
        self.lbl.pack(fill="x")
        self.c = tk.Canvas(self, background="#202020", highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.c.bind("<Configure>", lambda e: self.show())
        self.c.bind("<Motion>", self._motion)
        self.c.bind("<Button-1>", self._click)
        self.c.bind("<Button-3>", self._menu)

    # ---- drawing ----
    def load(self):
        self.mod = self.app.mod
        self.redraw()

    def _screen(self):
        txt = self.v_screen.get().split("(")[0]
        w, h = (int(v) for v in txt.replace(" ", "").split("x"))
        return w, h

    def redraw(self):
        """The HUD composed again (the mod's pictures, the Sprite sheets tab's changes)."""
        if not self.mod:
            self.lbl.configure(text="Load a mod first.")
            return
        sp = self.interface.ensure_sprites()
        try:
            self.items = H.pieces(self.mod)
            self._img = H.compose(self.mod, self.app.v_campaign.get() if hasattr(self.app, "v_campaign") else None,
                                  page_picture=sp.changed_page, boxes=sp.changed_boxes(), screen=self._screen())
        except Exception as e:
            self._img = None
            self.lbl.configure(text="The HUD cannot be drawn: %s" % e)
            self.show()
            return
        gone = H.missing(self.mod)
        self.lbl.configure(text=("Not in this mod's sheets: " + ", ".join("%s (%s)" % (s, sh) for sh, s in gone))
                           if gone else "Hover over a piece to see what it is; right click for what you can do.")
        self.show()

    def show(self):
        c = self.c
        c.delete("all")
        if self._img is None:
            return
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        iw, ih = self._img.size
        self._scale = min(cw / iw, ch / ih)
        from PIL import ImageTk
        shown = self._img.resize((max(1, int(iw * self._scale)), max(1, int(ih * self._scale))))
        self._photo = ImageTk.PhotoImage(shown)
        c.create_image(0, 0, image=self._photo, anchor="nw")
        sx, sy = self._factor()
        for p, colour in ((self.hover, "#ffffff"), (self.picked, "#ffd24a")):
            if p is not None:
                x, y, w, h = p["box"]
                c.create_rectangle(x * sx, y * sy, (x + w) * sx, (y + h) * sy, outline=colour, width=2)

    def _factor(self):
        """Canvas pixels per layout pixel, x and y (the screen stretches them apart)."""
        sw, sh = self._screen()
        return sw / H.CANVAS[0] * self._scale, sh / H.CANVAS[1] * self._scale

    def _at(self, e):
        sx, sy = self._factor()
        if not sx or not sy:
            return None
        return H.piece_at(self.mod, e.x / sx, e.y / sy, self.items)

    def _motion(self, e):
        p = self._at(e)
        if p is not self.hover:
            self.hover = p
            if p:
                self.lbl.configure(text="%s%s" % (p["piece"], "  -  %s on %s (%s)" % (p["sprite"], p["page"], p["sheet"])
                                                  if p.get("sprite") else ""))
            self.show()

    def _click(self, e):
        self.picked = self._at(e)
        self.show()

    # ---- the right click ----
    def _menu(self, e):
        self.picked = self._at(e)
        self.show()
        m = tk.Menu(self, tearoff=False)
        p = self.picked
        if p and p.get("sprite"):
            m.add_command(label=p["piece"], state="disabled")
            m.add_separator()
            m.add_command(label="Replace its picture...", command=lambda: self._on_sheet(p, "replace"))
            m.add_command(label="Place and size on its sheet...", command=lambda: self._on_sheet(p, "place"))
            m.add_command(label="Show it on the Sprite sheets tab", command=lambda: self._on_sheet(p, "show"))
            m.add_separator()
        elif p:
            m.add_command(label="%s - drawn by the game, not a sprite" % p["piece"], state="disabled")
            m.add_separator()
        m.add_command(label="Save the whole HUD as PNG...", command=self.save_png)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _on_sheet(self, p, what):
        sp = self.interface.ensure_sprites()
        sheet = next((s for s in sp.sheets if s["name"].lower() == p["sheet"]), None)
        if sheet is None:
            messagebox.showinfo(TITLE, "The sheet %s was not found." % p["sheet"], parent=self)
            return
        sp.show(sheet["name"], p["page"], pick=p["sprite"])
        if what == "show":
            self.interface.nb.select(1)
            return
        if what == "replace":
            sp.replace_sprite()
        else:
            w = sp.place_window()
            if w is not None:
                self.wait_window(w)
        self.redraw()

    def save_png(self):
        if self._img is None:
            return
        out = filedialog.asksaveasfilename(parent=self, title="Save the HUD as PNG", defaultextension=".png",
                                           initialfile="campaign_hud.png", filetypes=[("PNG picture", "*.png")])
        if out:
            try:
                self._img.save(out, "PNG")
            except OSError as e:
                messagebox.showerror(TITLE, "%s could not be saved: %s" % (out, e), parent=self)


__all__ = ["HudPanel"]
