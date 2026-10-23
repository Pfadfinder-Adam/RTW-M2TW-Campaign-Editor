"""Interface > Campaign HUD: the strategy map's bottom panel as the game draws it (hudlayout - the engines' own places,
both games), from the mod's own pictures and with the changes waiting on the Sprite sheets tab. Hover names a piece;
its right click replaces its picture or sets its place and size (the Sprite sheets tab's own ways - one place for
the changes, Apply writes them), shows it on its sheet, or saves the whole HUD as a PNG. 'Screen' stretches the
1024 x 768 layout as the game does on a bigger screen (x and y apart).
The HUD lies on an endless board as on Obsidian Canvas (the user, 2026-10-22; gui_board): the wheel zooms at the
mouse, the middle or right button (or Space + left) drags the board, Shift+1 shows it all; a screenshot is a card of
its own - laid exactly over the HUD first, dragged aside to compare, sticking to the grid and the HUD's edges (Alt:
anywhere)."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import board as B
from . import hudlayout as H
from . import theme
from .gui_board import Board, alt_held
from .gui_util import tip

TITLE = "Campaign HUD"
SCREENS = ["1024 x 768 (the layout)", "1280 x 1024", "1600 x 900", "1920 x 1080", "2560 x 1440"]


def is_whole_screen(w, h):
    """A screenshot of a whole game screen (the games start at 800 x 600) - not a part cut out of one."""
    return w >= 800 and h >= 600


class HudPanel(ttk.Frame):
    def __init__(self, master, app, interface):
        super().__init__(master)
        self.app, self.interface = app, interface
        self.mod, self.items, self.picked, self.hover = None, [], None, None
        self._img, self._drawn = None, None             # the HUD picture; (it, the view) it was last drawn for
        self._shot = None                               # the screenshot laid over (Pillow RGBA), or None
        bar = ttk.Frame(self, padding=(10, 8, 10, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="Screen").pack(side="left")
        self.v_screen = tk.StringVar(value=SCREENS[0])
        cb = ttk.Combobox(bar, textvariable=self.v_screen, values=SCREENS, state="readonly", width=24)
        cb.pack(side="left", padx=(4, 10))
        cb.bind("<<ComboboxSelected>>", lambda e: self.redraw())
        ttk.Button(bar, text="Draw again", command=self.redraw).pack(side="left")
        # a screenshot of the game over the HUD (Wholesome Queen's overlay, the user's 'yes, in order'): the modder's own,
        # stretched to the screen picked as the game stretches its layout; how much of it shows; O toggles it
        ttk.Button(bar, text="Screenshot over it...", command=self.pick_shot).pack(side="left", padx=(10, 0))
        self.v_shot = tk.BooleanVar(value=False)
        self.chk_shot = ttk.Checkbutton(bar, text="show (O)", variable=self.v_shot, command=self.show)
        self.chk_shot.pack(side="left", padx=4)
        self.v_alpha = tk.IntVar(value=50)
        ttk.Scale(bar, from_=0, to=100, variable=self.v_alpha, orient="horizontal", length=110,
                  command=lambda v: self.show()).pack(side="left")
        ttk.Label(bar, text="% of it").pack(side="left", padx=(2, 0))
        from .gui_util import hint
        hint(bar, "The campaign map's bottom panel (HUD) as the game draws it: the places are the game's own, the "
                  "pictures the mod's (and your changes waiting for Apply). Everything is laid out on 1024 x 768 and "
                  "the whole of it is stretched to the screen - 'Screen' shows how it looks on a bigger one. Right "
                  "click a piece: replace its picture, set its place and size on its sheet, show it on the Sprite "
                  "sheets tab, save the whole HUD as a PNG. Unit cards, the radar map and the words are shown "
                  "as examples. It lies on a board: the wheel zooms, the middle or right button (or Space + left) "
                  "moves it, Shift+1 shows everything; a screenshot can be dragged aside to compare.", width=560).pack(side="left", padx=6)
        self.lbl = ttk.Label(self, foreground=theme.palette()["muted"], padding=(10, 0))
        self.lbl.pack(fill="x")
        self.c = Board(self, pan_right=True, on_view=self.show, on_right_click=self._menu,
                       content_box=self._everything, selection_box=self._picked_box)
        self.c.pack(fill="both", expand=True)
        self.c.on_press, self.c.on_drag, self.c.on_release = self._press, self._drag, self._release
        self.c.bind("<Motion>", self._motion)
        self.c.bind("o", lambda e: (self.v_shot.set(not self.v_shot.get()), self.show()))
        self.c.bind("[", lambda e: self._nudge_alpha(-10))
        self.c.bind("]", lambda e: self._nudge_alpha(10))
        self._shot_xy, self._dragging, self._stuck = (0, 0), None, []
        # the zoom's own buttons in the board's corner, as on Obsidian Canvas; 'snap to grid' as its settings
        zb = ttk.Frame(self.c, padding=2)
        zb.place(relx=1.0, x=-8, y=8, anchor="ne")
        for text, fn, about in (("+", lambda: self.c.zoom_step(True), "Zoom in (the wheel, + )"),
                              ("-", lambda: self.c.zoom_step(False), "Zoom out (the wheel, - )"),
                              ("1:1", self.c.actual_size, "100 %: one screen pixel = one HUD pixel (Shift+0)"),
                              ("Fit", self.c.fit_content, "Everything in view (Shift+1)")):
            btn = ttk.Button(zb, text=text, width=len(text) + 2, command=lambda fn=fn: (fn(), self.c.focus_set()))
            btn.pack(side="left")
            tip(btn, about)
        self.lbl_zoom = ttk.Label(zb, width=6, anchor="center")
        self.lbl_zoom.pack(side="left", padx=(4, 0))
        self.v_snap = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(zb, text="Snap to grid", variable=self.v_snap)
        chk.pack(side="left", padx=(6, 0))
        tip(chk, "A screenshot dragged on the board lands on the grid's dots and sticks to the HUD's edges and "
                     "middle. Hold Alt while dragging to put it anywhere.")

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

    def _hud_size(self):
        """The HUD's card on the board: at (0, 0), as big as the screen picked (one world unit = one screen pixel)."""
        return self._img.size if self._img is not None else self._screen()

    def _shot_box(self):
        """(x, y, w, h) of the screenshot's card, None when there is none or it is hidden."""
        if self._shot is None or not self.v_shot.get():
            return None
        return self._shot_xy + self._shot.size

    def _everything(self):
        w, h = self._hud_size()
        x0, y0, x1, y1 = 0, 0, w, h
        sb = self._shot_box()
        if sb:
            x0, y0 = min(x0, sb[0]), min(y0, sb[1])
            x1, y1 = max(x1, sb[0] + sb[2]), max(y1, sb[1] + sb[3])
        return x0, y0, x1, y1

    def _picked_box(self):
        p = self.picked or self.hover
        if p is None:
            return None
        fx, fy = self._factor()
        x, y, w, h = p["box"]
        return x * fx - 8, y * fy - 8, (x + w) * fx + 8, (y + h) * fy + 8

    def show(self):
        """The pictures drawn again only when the view, the HUD or the screenshot changed - a hover over a piece only
        moves its frame (it drew the whole HUD again at every piece the mouse crossed: report #409's lag)."""
        c = self.c
        self.lbl_zoom.configure(text="%d %%" % round(c.zoom * 100))
        sb = self._shot_box()
        key = (c.zoom, c.view.ox, c.view.oy, c.size(), sb, self.v_alpha.get() if sb else None)
        if self._img is None or self._drawn is None or self._drawn[0] is not self._img or self._drawn[1] != key \
                or not c.find_withtag("hud"):
            c.delete("hud")
            self._drawn = None
            if self._img is None:
                c.delete("hud-mark")
                return
            w, h = self._img.size
            c.picture(self._img, 0, 0, "hud")
            if sb:
                x, y, sw, sh = sb
                over = x < w and y < h and x + sw > 0 and y + sh > 0     # over the HUD: see-through; beside it: whole
                c.picture(self._shot, x, y, "hud",
                          alpha=max(0, min(100, self.v_alpha.get())) / 100.0 if over else None)
            self._drawn = (self._img, key)
        c.delete("hud-mark")
        if sb:
            c.box(*sb, outline="#6fa8dc", width=1, tags="hud-mark")
        fx, fy = self._factor()
        for p, colour in ((self.hover, "#ffffff"), (self.picked, "#ffd24a")):
            if p is not None:
                x, y, pw, ph = p["box"]
                c.box(x * fx, y * fy, pw * fx, ph * fy, outline=colour, width=2, tags="hud-mark")
        for o in self._stuck:                                  # the guide lines of what the screenshot stuck to
            c.box(*o, outline="#ff5ec4", width=1, dash=(4, 3), tags="hud-mark")

    def _factor(self):
        """World units (screen pixels) per layout pixel, x and y (the screen stretches them apart)."""
        sw, sh = self._hud_size()
        return sw / H.CANVAS[0], sh / H.CANVAS[1]

    def _layout(self, e):
        """The 1024 x 768 layout point under the mouse, None off the HUD."""
        wx, wy = self.c.to_world(e.x, e.y)
        w, h = self._hud_size()
        if not (0 <= wx < w and 0 <= wy < h):
            return None
        fx, fy = self._factor()
        return wx / fx, wy / fy

    def _at(self, e):
        at = self._layout(e)
        return H.piece_at(self.mod, at[0], at[1], self.items) if at and self.mod else None

    def _motion(self, e):
        p = self._at(e)
        if p is not self.hover:
            self.hover = p
            if p:
                self.lbl.configure(text="%s%s" % (p["piece"], "  -  %s on %s (%s)" % (p["sprite"], p["page"], p["sheet"])
                                                  if p.get("sprite") else ""))
            self.show()

    def _press(self, e):
        """A press on the screenshot may become its drag; a click (no move) picks the piece under it."""
        sb = self._shot_box()
        wx, wy = self.c.to_world(e.x, e.y)
        on_shot = sb and sb[0] <= wx < sb[0] + sb[2] and sb[1] <= wy < sb[1] + sb[3]
        self._dragging = (e.x, e.y, self._shot_xy, False) if on_shot else None

    def _drag(self, e):
        if self._dragging is None:
            return
        x0, y0, (sx, sy), moved = self._dragging
        if not moved and abs(e.x - x0) + abs(e.y - y0) < 4:
            return
        z = self.c.zoom
        x, y = sx + (e.x - x0) / z, sy + (e.y - y0) / z
        if alt_held(e):
            self._stuck = []
        else:
            hud = (0, 0) + self._hud_size()
            x, y, stuck = B.snap_box((x, y) + self._shot.size, [hud], zoom=z, to_grid=self.v_snap.get())
            self._stuck = stuck
        self._shot_xy = (round(x), round(y))
        self._dragging = (x0, y0, (sx, sy), True)
        self.c.configure(cursor="fleur")
        self.show()

    def _release(self, e):
        moved = self._dragging is not None and self._dragging[3]
        self._dragging, self._stuck = None, []
        self.c.configure(cursor="")
        if not moved:
            self.picked = self._at(e)
        self.show()

    # ---- a screenshot over it ----
    def pick_shot(self):
        """A screenshot of the game (any size: it is stretched to the screen picked, as the game stretches its
        1024 x 768 layout) shown over the HUD to compare."""
        path = filedialog.askopenfilename(parent=self, title="A screenshot of the campaign map", filetypes=[
            ("Pictures", "*.png *.jpg *.jpeg *.bmp *.tga"), ("All files", "*.*")])
        if not path:
            return
        try:
            from PIL import Image
            with Image.open(path) as im:
                self._shot = im.convert("RGBA")
                self._drawn = None
        except Exception as e:
            messagebox.showerror(TITLE, "%s cannot be read: %s" % (path, e), parent=self)
            return
        w, h = self._shot.size
        whole = is_whole_screen(w, h)
        if whole:
            self.v_screen.set("%d x %d" % (w, h))       # the HUD stretched to the screenshot's own screen
        self.v_shot.set(True)
        sw, sh = self._screen()
        # a whole screen lies exactly over the HUD; a cut-out piece (the HUD alone) over its bottom, the Screen kept
        # (report #413: a 693 x 236 cut-out made the HUD a 693 x 236 'screen')
        self._shot_xy = (0, 0) if whole else ((sw - w) // 2, sh - h)
        self.redraw()
        self.c.fit_content()
        self.lbl.configure(text=("Your screenshot (%d x %d) over the HUD - O shows / hides it, [ ] or the slider: how "
                                 "much of it shows; drag it aside to compare them side by side" % (w, h)) + (
            "" if whole else ". It is a part of a screen, so 'Screen' stays %d x %d - pick the screen it was taken "
                             "on there" % (sw, sh)))

    def _shot_back(self):
        self._shot_xy = (0, 0)
        self.v_shot.set(True)
        self.show()

    def _shot_away(self):
        self._shot = None
        self._drawn = None
        self.v_shot.set(False)
        self.show()

    def _nudge_alpha(self, step):
        self.v_alpha.set(max(0, min(100, self.v_alpha.get() + step)))
        self.show()

    # ---- the right click ----
    def _menu(self, e):
        self.picked = self._at(e)
        self.show()
        m = tk.Menu(self, tearoff=False)
        p = self.picked
        at = self._layout(e)
        under = [q for q in (H.pieces_at(self.mod, at[0], at[1], self.items) if at and self.mod else [])
                 if q.get("sprite")]
        for q in under:                     # the piece on top and those under it (a ring over its button's picture)
            also = H.sharing(q, self.items)
            m.add_command(label=q["piece"] + ("  (also the %s - a new picture changes both)" % ", ".join(
                x["piece"] for x in also) if also else ""), state="disabled")
            m.add_command(label="    Replace its picture...", command=lambda q=q: self._on_sheet(q, "replace"))
            m.add_command(label="    Place and size on its sheet...", command=lambda q=q: self._on_sheet(q, "place"))
            m.add_command(label="    Show it on the Sprite sheets tab", command=lambda q=q: self._on_sheet(q, "show"))
            m.add_separator()
        if p and not under:
            m.add_command(label="%s - drawn by the game, not a sprite" % p["piece"], state="disabled")
            m.add_separator()
        if self._shot is not None:
            m.add_command(label="Screenshot: back over the HUD", command=self._shot_back)
            m.add_command(label="Screenshot: take it away", command=self._shot_away)
            m.add_separator()
        m.add_command(label="Everything in view (Shift+1)", command=self.c.fit_content)
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
