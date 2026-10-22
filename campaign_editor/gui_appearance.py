"""Appearance: the colours and the font of the whole editor at once, as Obsidian's Settings > Appearance (the user,
2026-10-22: 'change the background not piece by piece but the colour of the whole thing'). A panel of swatches - one
per colour of the light / dark look (theme.NAMES) and one per button with a colour of its own (theme.COLOURED_NAMES) -
a click picks a new colour, its arrow takes it back; a font and a size for every window; Light / Dark. Each change is
put on every window at once (theme.set_custom) and kept for every start. The layout board shows it at its side."""

import tkinter as tk
from tkinter import colorchooser, ttk
from tkinter import font as tkfont

from . import settings, theme

TITLE = "Appearance"
OWN_FONT = "(the system's)"


class AppearancePanel(ttk.Frame):
    """The swatches; on_change() is called after every change (the board takes its pictures again)."""

    def __init__(self, master, root, on_change=None):
        super().__init__(master, padding=(8, 6))
        self.root, self.on_change = root, on_change
        self.v_dark = tk.BooleanVar(self, value=theme.dark())
        colours, font = theme.custom()
        font = (list(font or []) + ["", 0])[:2]
        self.v_family = tk.StringVar(self, value=font[0] or OWN_FONT)
        self.v_size = tk.StringVar(self, value=str(font[1] or ""))
        self.buttons_open = bool(colours and any(k in theme.COLOURED for k in colours))
        self._build()

    def _build(self):
        head = ttk.Frame(self)
        head.pack(fill="x")
        ttk.Label(head, text=TITLE, font=("", 11, "bold")).pack(side="left")
        ttk.Button(head, text="Themes...", command=self._themes).pack(side="right")
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(4, 6))
        ttk.Radiobutton(row, text="Light", variable=self.v_dark, value=False, command=self._base).pack(side="left")
        ttk.Radiobutton(row, text="Dark", variable=self.v_dark, value=True, command=self._base).pack(side="left",
                                                                                                    padx=(8, 0))
        f = ttk.Frame(self)
        f.pack(fill="x", pady=(0, 4))
        ttk.Label(f, text="Font of every window").grid(row=0, column=0, columnspan=2, sticky="w")
        families = [OWN_FONT] + sorted(x for x in set(tkfont.families(self)) if not x.startswith("@"))
        cb = ttk.Combobox(f, textvariable=self.v_family, values=families, width=22)
        cb.grid(row=1, column=0, sticky="we")
        sb = ttk.Spinbox(f, from_=0, to=24, textvariable=self.v_size, width=4, command=self._font)
        sb.grid(row=1, column=1, padx=(4, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self._font())
        for w in (cb, sb):
            w.bind("<Return>", lambda e: self._font())
            w.bind("<FocusOut>", lambda e: self._font())
        self.rows = ttk.Frame(self)
        self.rows.pack(fill="x")
        ttk.Button(self, text="All back to the look as it comes", command=self._all_back).pack(anchor="w",
                                                                                            pady=(10, 0))
        self._fill()

    def _fill(self):
        for w in self.rows.winfo_children():
            w.destroy()
        colours, _ = theme.custom()
        pal = theme.palette()
        r = 0
        for head, names, now in (("Colours", theme.NAMES, lambda k: pal[k]),
                                 ("Buttons with a colour of their own", theme.COLOURED_NAMES,
                                  lambda k: colours.get(k) or theme.COLOURED[k][0])):
            if names is theme.NAMES:
                ttk.Label(self.rows, text=head, font=("", 9, "bold")).grid(row=r, column=0, columnspan=3,
                                                                          sticky="w", pady=(6, 2))
            else:                                          # folded away: rarely changed
                ttk.Button(self.rows, text=("▾ " if self.buttons_open else "▸ ") + head,
                           command=self._fold).grid(row=r, column=0, columnspan=3, sticky="w", pady=(6, 2))
                if not self.buttons_open:
                    break
            r += 1
            for key, name in names.items():
                c = now(key)
                b = ttk.Button(self.rows, text="  ", width=3, command=lambda k=key, n=name: self._pick(k, n))
                theme.paint(b, c)
                b.grid(row=r, column=0, sticky="w", pady=1)
                ttk.Label(self.rows, text=name + ("  *" if key in colours else "")).grid(row=r, column=1,
                                                                                          sticky="w", padx=(6, 6))
                if key in colours:
                    ttk.Button(self.rows, text="↺", width=2, command=lambda k=key: self._set(k, None)).grid(
                        row=r, column=2, sticky="w")
                r += 1

    def _themes(self):
        from .gui_themes import open_themes
        open_themes(self.root)

    def sync(self):
        """Shown again after the whole look changed elsewhere (a theme put on)."""
        colours, font = theme.custom()
        font = (list(font or []) + ["", 0])[:2]
        self.v_dark.set(theme.dark())
        self.v_family.set(font[0] or OWN_FONT)
        self.v_size.set(str(font[1] or ""))
        self._fill()

    def _fold(self):
        self.buttons_open = not self.buttons_open
        self._fill()

    def _pick(self, key, name):
        now = theme.custom()[0].get(key) or (theme.palette().get(key) or theme.COLOURED.get(key, ("#808080",))[0])
        got = colorchooser.askcolor(color=now, parent=self.winfo_toplevel(), title=name)
        if got and got[1]:
            self._set(key, got[1])

    def _set(self, key, colour):
        colours, font = theme.custom()
        if colour:
            colours[key] = colour
        else:
            colours.pop(key, None)
        theme.set_custom(self.root, colours, font)
        self._done()

    def _font(self):
        family = self.v_family.get().strip()
        size = self.v_size.get().strip()
        want = ["" if family in ("", OWN_FONT) else family, int(size) if size.isdigit() else 0]
        colours, font = theme.custom()
        if (list(font or []) + ["", 0])[:2] == want:
            return
        theme.set_custom(self.root, colours, want)
        self._done()

    def _base(self):
        if self.v_dark.get() != theme.dark():
            theme.apply(self.root, self.v_dark.get())
            settings.put("theme", "dark" if theme.dark() else "light")
            self._done()

    def _all_back(self):
        theme.set_custom(self.root, {}, None)
        self.v_family.set(OWN_FONT)
        self.v_size.set("")
        self._done()

    def _done(self):
        self._fill()
        if self.on_change:
            self.on_change()


__all__ = ["AppearancePanel"]
