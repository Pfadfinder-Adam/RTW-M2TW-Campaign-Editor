"""The themes window: every theme as a card with a picture - the editor's own and the modder's -, Use puts it on the
whole editor at once, Export... writes one .zip to send, Import a theme... takes one sent, Save the look now as a
theme... keeps the colours and font now in force with a picture of the editor (Obsidian's theme browser, the user
2026-10-22). themes.py holds the files."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import theme, themes

TITLE = "Themes"
CARD_W, CARD_H = 220, 130


def _is_now(t):
    colours, font = theme.custom()
    return t["colours"] == colours and (t["font"] or None) == (font or None) and \
        (t["base"] == "dark") == theme.dark()


def draw_sample(cv, t, w=CARD_W, h=CARD_H):
    """A theme with no picture drawn from its colours: a window with a bar of buttons, a list, words and Play."""
    pal = dict(theme.DARK if t["base"] == "dark" else theme.LIGHT, **{k: v for k, v in t["colours"].items()
                                                                      if k in theme.LIGHT})
    play = t["colours"].get("Play.TButton") or theme.COLOURED["Play.TButton"][0]
    cv.create_rectangle(0, 0, w, h, fill=pal["bg"], outline=pal["border"])
    for i, x in enumerate((8, 58, 108)):
        cv.create_rectangle(x, 8, x + 44, 24, fill=pal["accent"] if i == 0 else pal["button"],
                            outline=pal["border"])
    cv.create_rectangle(158, 8, w - 8, 24, fill=play, outline="")
    cv.create_text((158 + w - 8) / 2, 16, text="Play", fill=theme.on_colour(play), font=("", 8, "bold"))
    cv.create_rectangle(8, 34, 110, h - 8, fill=pal["field"], outline=pal["border"])
    cv.create_rectangle(9, 52, 109, 66, fill=pal["select"], outline="")
    for j, y in enumerate((43, 59, 75, 91)):
        cv.create_text(14, y, text="Faction %d" % (j + 1), anchor="w", font=("", 8),
                       fill=pal["selectfg"] if j == 1 else pal["fg"])
    cv.create_text(120, 44, text="Words", anchor="w", fill=pal["fg"], font=("", 9, "bold"))
    cv.create_text(120, 62, text="quiet words", anchor="w", fill=pal["muted"], font=("", 8))
    cv.create_text(120, 80, text="a link  ?", anchor="w", fill=pal["link"], font=("", 8, "underline"))


class ThemesWindow(tk.Toplevel):
    def __init__(self, app, on_change=None):
        super().__init__(app)
        self.app, self.on_change = app, on_change
        self.title(TITLE)
        self.geometry("800x600")
        self._photos = []
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(fill="x", side="bottom")
        for text, cmd in (("Save the look now as a theme...", self.save_now), ("Import a theme...", self.import_),
                          ("Close", self.destroy)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left" if text != "Close" else "right", padx=(0, 6))
        ttk.Label(self, padding=(8, 6, 8, 0), wraplength=720,
                  text="Every theme colours the whole editor at once (its own colours over Light or Dark, and a "
                       "font). Use puts it on; Export... writes it into one .zip to send - Import a theme... takes "
                       "one sent to you. Layout board > Appearance changes any colour of the theme in use.").pack(
            fill="x")
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        self.cv = tk.Canvas(outer, highlightthickness=0)
        ys = ttk.Scrollbar(outer, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.cv.pack(fill="both", expand=True)
        self.grid_ = ttk.Frame(self.cv)
        self.cv.create_window(0, 0, window=self.grid_, anchor="nw")
        self.grid_.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.fill()

    def fill(self):
        for w in self.grid_.winfo_children():
            w.destroy()
        self._photos = []
        for i, t in enumerate(themes.available()):
            card = ttk.Frame(self.grid_, padding=6, relief="groove" if not _is_now(t) else "solid", borderwidth=2)
            card.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="n")
            pic = tk.Canvas(card, width=CARD_W, height=CARD_H, highlightthickness=0)
            theme.leave_alone(pic)
            pic.pack()
            if not self._picture(pic, t):
                draw_sample(pic, t)
            ttk.Label(card, text=t["name"] + ("   (in use)" if _is_now(t) else ""), font=("", 9, "bold")).pack(
                anchor="w", pady=(4, 0))
            ttk.Label(card, text=("by " + t["by"] if t["by"] else "") + ("  - yours" if t["own"] else "")).pack(
                anchor="w")
            row = ttk.Frame(card)
            row.pack(anchor="w", pady=(4, 0))
            ttk.Button(row, text="Use", command=lambda t_=t: self.use(t_)).pack(side="left")
            ttk.Button(row, text="Export...", command=lambda t_=t: self.export(t_)).pack(side="left", padx=(4, 0))
            if t["own"]:
                ttk.Button(row, text="Delete", command=lambda t_=t: self.delete(t_)).pack(side="left", padx=(4, 0))

    def _picture(self, cv, t):
        if not t.get("picture"):
            return False
        try:
            from PIL import Image, ImageTk
            with Image.open(t["picture"]) as im:
                im = im.convert("RGB")
                im.thumbnail((CARD_W, CARD_H))
                photo = ImageTk.PhotoImage(im, master=cv)
        except Exception:                                  # noqa: BLE001 - no Pillow, a broken picture
            return False
        self._photos.append(photo)
        cv.create_image(CARD_W / 2, CARD_H / 2, image=photo)
        return True

    def use(self, t):
        theme.set_custom(self.app, t["colours"], t["font"], t["base"] == "dark")
        self.fill()
        if self.on_change:
            self.on_change()
        board = getattr(self.app, "_layout_board", None)         # an open layout board follows the new look
        try:
            if board is not None and board.winfo_exists():
                if board.side is not None:
                    board.side.sync()
                board._look_changed()
        except tk.TclError:
            pass

    def export(self, t):
        path = filedialog.asksaveasfilename(parent=self, title="Export a theme", defaultextension=".zip",
                                            initialfile=themes.folder_name(t["name"]) + ".zip",
                                            filetypes=(("Theme", "*.zip"),))
        if path and not themes.export(t, path):
            messagebox.showerror(TITLE, "It could not be written to %s." % path, parent=self)

    def import_(self):
        path = filedialog.askopenfilename(parent=self, title="Import a theme",
                                          filetypes=(("Theme", "*.zip *.json"), ("All files", "*.*")))
        if not path:
            return
        name, why = themes.import_file(path)
        if name is None:
            messagebox.showinfo(TITLE, "That file was not taken: %s." % why, parent=self)
            return
        self.fill()

    def delete(self, t):
        if messagebox.askyesno(TITLE, "Delete your theme '%s'?" % t["name"], parent=self):
            themes.delete(t)
            self.fill()

    def save_now(self):
        name = simpledialog.askstring(TITLE, "The theme's name:", parent=self)
        if not name or not name.strip():
            return
        by = simpledialog.askstring(TITLE, "Made by (your name or nick, may stay empty):", parent=self) or ""
        from .gui_lookboard import snap
        try:
            self.app.update_idletasks()
            picture = snap(self.app)
        except Exception:                                  # noqa: BLE001
            picture = None
        colours, font = theme.custom()
        if themes.save(name.strip(), by.strip(), "dark" if theme.dark() else "light", colours, font,
                       picture) is None:
            messagebox.showerror(TITLE, "The theme could not be written.", parent=self)
            return
        self.fill()


def open_themes(app, on_change=None):
    w = getattr(app, "_themes_window", None)
    try:
        if w is not None and w.winfo_exists():
            w.lift()
            return w
    except tk.TclError:
        pass
    w = app._themes_window = ThemesWindow(app, on_change)
    return w


__all__ = ["ThemesWindow", "open_themes", "draw_sample"]
