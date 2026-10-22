"""Appearance: the colours and the font of the whole editor at once, as Obsidian's Settings > Appearance (the user,
2026-10-22: 'change the background not piece by piece but the colour of the whole thing'). A panel of swatches - one
per colour of the light / dark look (theme.NAMES) and one per button with a colour of its own (theme.COLOURED_NAMES) -
a click picks a new colour, its arrow takes it back; a font and a size for every window; Light / Dark. Each change is
put on every window at once (theme.set_custom) and kept for every start. The layout board shows it at its side."""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
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
        self.snip_box = ttk.Frame(self)
        self.snip_box.pack(fill="x", pady=(12, 0))
        self._fill()
        self._snippets()

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

    # ---- snippets: sets of button changes switched on and off (Obsidian's CSS snippets) ----
    def _snippets(self):
        box = self.snip_box
        for w in box.winfo_children():
            w.destroy()
        look = getattr(self.root, "look", None)
        if look is None:
            return
        from . import look as LK
        ttk.Label(box, text="Snippets - sets of button changes", font=("", 9, "bold")).pack(anchor="w")
        snips = LK.snippets()
        if not snips:
            ttk.Label(box, text="None yet: move your changes into one below.", foreground=theme.palette()["muted"]
                      ).pack(anchor="w")
        for s in snips:
            row = ttk.Frame(box)
            row.pack(fill="x")
            v = tk.BooleanVar(row, value=s["on"])
            ttk.Checkbutton(row, text="%s  (%d)" % (s["name"], len(s["pieces"])), variable=v,
                            command=lambda s_=s, v_=v: self._switch(s_, v_.get())).pack(side="left")
            ttk.Button(row, text="✕", width=2, command=lambda s_=s: self._drop(s_)).pack(side="right")
            ttk.Button(row, text="Export...", command=lambda s_=s: self._export(s_)).pack(side="right", padx=(0, 4))
        row = ttk.Frame(box)
        row.pack(fill="x", pady=(4, 0))
        ttk.Button(row, text="Move my changes into a snippet...", command=self._own_to_snippet).pack(side="left")
        ttk.Button(row, text="Import...", command=self._import).pack(side="left", padx=(4, 0))

    def _switch(self, s, on):
        from . import look as LK
        LK.set_snippet_on(s["path"], on)
        self.root.look.relayer()
        self._snippets()

    def _drop(self, s):
        if not messagebox.askyesno(TITLE, "Delete the snippet '%s'? Its changes go with it." % s["name"],
                                   parent=self.winfo_toplevel()):
            return
        import os
        try:
            os.remove(s["path"])
        except OSError:
            pass
        self.root.look.relayer()
        self._snippets()

    def _export(self, s):
        import shutil
        path = filedialog.asksaveasfilename(parent=self.winfo_toplevel(), title="Export a snippet",
                                            defaultextension=".json", initialfile=os.path.basename(s["path"]),
                                            filetypes=(("Snippet", "*.json"),))
        if path:
            try:
                shutil.copyfile(s["path"], path)
            except OSError as e:
                messagebox.showerror(TITLE, "It could not be written: %s" % e, parent=self.winfo_toplevel())

    def _import(self):
        from . import look as LK
        path = filedialog.askopenfilename(parent=self.winfo_toplevel(), title="Import a snippet",
                                          filetypes=(("Snippet or look", "*.json"),))
        if not path:
            return
        got = LK.load(path)
        if not got["pieces"]:
            messagebox.showinfo(TITLE, "There are no button changes in that file.", parent=self.winfo_toplevel())
            return
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            import json
            with open(path, encoding="utf-8") as fh:
                name = json.load(fh).get("name") or name
        except (OSError, ValueError, AttributeError):
            pass
        LK.save_snippet(str(name), got, on=True)
        self.root.look.relayer()
        self._snippets()

    def _own_to_snippet(self):
        look = self.root.look
        if not look.own["pieces"]:
            messagebox.showinfo(TITLE, "You have no button changes of your own now (they may all be in snippets "
                                       "already).", parent=self.winfo_toplevel())
            return
        name = simpledialog.askstring(TITLE, "The snippet's name (your %d button changes go into it; switch it "
                                             "off to see the editor without them):" % len(look.own["pieces"]),
                                      parent=self.winfo_toplevel())
        if name and name.strip():
            if look.own_to_snippet(name.strip()) is None:
                messagebox.showerror(TITLE, "The snippet could not be written.", parent=self.winfo_toplevel())
            self._snippets()

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
