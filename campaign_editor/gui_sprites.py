"""Interface > Sprite sheets: every sprite sheet of the mod as the game reads it (symbols.all_sheets - the binary
.rsd / .sd of the plain games, the .sd.xml of an engine on 'sprite_format xml'), page by page, with the page's picture
of each culture and the box of every sprite on it. Find looks through every sheet; a sprite's right click opens it big
or saves it (or the whole page) as a PNG, or replaces its picture (or the whole page's) - kept for the main window's
Apply changes, written into the mod's own copy of the page (spriteedit)."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import symbols as SY
from . import theme
from .gui_util import ShortHint

TITLE = "Sprite sheets"


class SpriteSheetsPanel(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app, self.mod = app, None
        self.sheets, self.sheet, self.page, self.culture = [], None, None, None
        self.picked, self.hover = None, None
        self._img, self._shown, self._photo, self._cultures = None, None, None, []
        self.changes, self.undo, self.redo = {}, [], []     # {(page, culture): new page picture}; steps back / on
        self.box_changes = {}                               # {(sheet, sprite): ((x, y, w, h), shown (w, h) or None)}
        self._build()

    # ---- reading ----
    def load(self, force=False):
        """The mod loaded now read (again only when it is another mod)."""
        mod = self.app.mod
        if mod is self.mod and not force:
            return
        if self.mod is None or mod is None or mod.data != self.mod.data:
            self.changes, self.undo, self.redo = {}, [], []     # another mod: its pages are others
            self.box_changes = {}
        self.mod = mod
        self.sheets = SY.all_sheets(mod) if mod else []
        self.cb_sheet.configure(values=[self._sheet_label(s) for s in self.sheets])
        if self.sheets:
            first = next((s for s in self.sheets if s["pages"]), self.sheets[0])
            self.show(first["name"])
        else:
            self.sheet = None
            self.v_sheet.set("")
            self.lbl_info.configure(text="Load a mod first." if not mod else "This game / mod has no sprite sheets "
                                                                           "in its ui folder.")
            self.fill_sprites()
            self.draw()

    @staticmethod
    def _sheet_label(s):
        return "%s  (%s, %d page(s))" % (s["name"], os.path.basename(s["path"]), len(s["pages"]))

    def _sheet(self, name):
        return next((s for s in self.sheets if s["name"] == name), None)

    def show(self, sheet, page=None, pick=None):
        """The sheet (its name) on show, its page (default the first) and the sprite picked."""
        sh = self._sheet(sheet)
        if sh is None:
            return
        self.sheet = sh
        self.v_sheet.set(self._sheet_label(sh))
        pages = [p for p, _ in sh["pages"]]
        self.cb_page.configure(values=["%s  (%d)" % (p, len(b)) for p, b in sh["pages"]])
        self.page = page if page in pages else (pages[0] if pages else None)
        self.v_page.set(next(("%s  (%d)" % (p, len(b)) for p, b in sh["pages"] if p == self.page), ""))
        self._cultures = SY.page_cultures(self.mod, self.page) if self.page else []
        self.cb_cult.configure(values=[c or "(ui)" for c, _ in self._cultures])
        names = [c for c, _ in self._cultures]
        if self.culture not in names:
            self.culture = names[0] if names else None
        self.v_cult.set((self.culture or "(ui)") if self._cultures else "")
        self.picked = pick
        self._read_picture()
        self.fill_sprites()
        self.say()
        self.draw()

    def _read_picture(self):
        """The page's picture of the culture picked, and the same on a chequer for the screen (its see-through parts
        shown as picture tools show them)."""
        self._img = self._shown = None
        path = dict(self._cultures).get(self.culture)
        changed = self.changes.get((self.page, self.culture))
        if not path and changed is None:
            return
        try:
            from PIL import Image
            from .recolour import read_picture
            self._img = changed.copy() if changed is not None else read_picture(path).convert("RGBA")
            w, h = self._img.size
            bg = Image.new("RGBA", (w, h), (60, 60, 60, 255))
            for y in range(0, h, 16):
                for x in range((y // 16) % 2 * 16, w, 32):
                    bg.paste((80, 80, 80, 255), (x, y, min(w, x + 16), min(h, y + 16)))
            bg.alpha_composite(self._img)
            self._shown = bg
        except Exception:
            self._img = self._shown = None

    def boxes(self):
        """[(sprite, (x, y, w, h))] of the page on show, with the boxes moved / sized here."""
        if not self.sheet:
            return []
        got = dict(self.sheet["pages"]).get(self.page, [])
        mine = self.box_changes
        return [(n, mine[(self.sheet["name"], n)][0] if (self.sheet["name"], n) in mine else b) for n, b in got]

    # ---- the window ----
    def _build(self):
        top = ttk.Frame(self, padding=(10, 8, 10, 0))
        top.pack(fill="x")
        ttk.Label(top, text="Sheet").pack(side="left")
        self.v_sheet = tk.StringVar()
        self.cb_sheet = ttk.Combobox(top, textvariable=self.v_sheet, state="readonly", width=34)
        self.cb_sheet.pack(side="left", padx=(4, 10))
        self.cb_sheet.bind("<<ComboboxSelected>>", lambda e: self.show(
            self.sheets[self.cb_sheet.current()]["name"]))
        ttk.Label(top, text="Page").pack(side="left")
        self.v_page = tk.StringVar()
        self.cb_page = ttk.Combobox(top, textvariable=self.v_page, state="readonly", width=26)
        self.cb_page.pack(side="left", padx=(4, 10))
        self.cb_page.bind("<<ComboboxSelected>>", lambda e: self.show(
            self.sheet["name"], self.sheet["pages"][self.cb_page.current()][0]))
        ttk.Label(top, text="Culture").pack(side="left")
        self.v_cult = tk.StringVar()
        self.cb_cult = ttk.Combobox(top, textvariable=self.v_cult, state="readonly", width=20)
        self.cb_cult.pack(side="left", padx=(4, 10))
        self.cb_cult.bind("<<ComboboxSelected>>", lambda e: self._culture_picked())
        ttk.Label(top, text="Find").pack(side="left")
        self.v_find = tk.StringVar()
        ttk.Entry(top, textvariable=self.v_find, width=22).pack(side="left", padx=4)
        self.v_find.trace_add("write", lambda *a: self.fill_sprites())
        hint = ttk.Frame(self, padding=(10, 4, 10, 0))
        hint.pack(fill="x")
        ShortHint(hint, text=(
            "Every interface picture the game takes from its sprite sheets: the sheet the game reads (the binary "
            ".rsd / .sd, or the .sd.xml under REX / M2EX with 'sprite_format xml'), its pages, and the box of each "
            "sprite on the page's picture of the culture picked. Find looks through every sheet. A double click "
            "opens a sprite big; its right click saves it or the whole page as a PNG. Nothing here writes the "
            "mod.")).pack(fill="x")
        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=6)
        left = ttk.Frame(body)
        body.add(left, weight=1)
        self.tv = ttk.Treeview(left, columns=("where", "x", "y", "w", "h"), show="tree headings")
        self.tv.heading("#0", text="sprite")
        self.tv.heading("where", text="sheet / page")
        self.tv.column("#0", width=200)
        self.tv.column("where", width=0, stretch=False)
        for c, t in (("x", "x"), ("y", "y"), ("w", "width"), ("h", "height")):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=46, anchor="e", stretch=False)
        sb = ttk.Scrollbar(left, command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.bind("<<TreeviewSelect>>", lambda e: self._tree_picked())
        self.tv.bind("<Double-1>", lambda e: self.open_big())
        self.tv.bind("<Button-3>", self._tree_menu)
        mid = ttk.Frame(body)
        body.add(mid, weight=4)
        self.canvas = tk.Canvas(mid, background="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        c = self.canvas
        c.bind("<Configure>", lambda e: self.draw())
        c.bind("<Motion>", self._motion)
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<Double-Button-1>", lambda e: self.open_big())
        c.bind("<Button-3>", self._canvas_menu)
        self.lbl_info = ttk.Label(mid, foreground=theme.palette()["muted"])
        self.lbl_info.pack(fill="x", pady=(2, 0))

    def _culture_picked(self):
        k = self.cb_cult.current()
        if 0 <= k < len(self._cultures):
            self.culture = self._cultures[k][0]
            self._read_picture()
            self.say()
            self.draw()

    # ---- the list ----
    def fill_sprites(self):
        """The sprites of the page on show; with words in Find: every sprite of every sheet whose name holds them."""
        self.tv.delete(*self.tv.get_children())
        want = self.v_find.get().strip().lower()
        rows = []
        if want:
            for sh in self.sheets:
                for page, boxes in sh["pages"]:
                    rows += [(sh["name"], page, n, b) for n, b in boxes if want in n.lower()]
        elif self.sheet:
            rows = [(self.sheet["name"], self.page, n, b) for n, b in self.boxes()]
        self.tv.column("where", width=170 if want else 0)
        self._rows = {}
        for i, (sheet, page, name, b) in enumerate(rows):
            iid = str(i)
            self._rows[iid] = (sheet, page, name)
            self.tv.insert("", "end", iid=iid, text=name, values=("%s / %s" % (sheet, page),) + tuple(b))
            if (sheet, page, name) == (self.sheet and self.sheet["name"], self.page, self.picked):
                self.tv.selection_set(iid)
                self.tv.see(iid)

    def _tree_picked(self):
        sel = self.tv.selection()
        if not sel:
            return
        sheet, page, name = self._rows[sel[0]]
        if self.sheet is None or sheet != self.sheet["name"] or page != self.page:
            find = self.v_find.get()
            self.show(sheet, page, name)
            if find:
                self.v_find.set(find)
            return
        if name != self.picked:
            self.picked = name
            self.say()
            self.draw()

    # ---- the picture ----
    def _scale(self):
        if self._img is not None:
            w, h = self._img.size
        else:
            w = max([b[0] + b[2] for _, b in self.boxes()] or [256])
            h = max([b[1] + b[3] for _, b in self.boxes()] or [256])
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        s = min(cw / w, ch / h, 4.0)
        return s, (cw - w * s) / 2, (ch - h * s) / 2, w, h

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self.sheet or not self.page:
            return
        s, ox, oy, w, h = self._scale()
        if self._shown is not None:
            try:
                from PIL import Image, ImageTk
                pic = self._shown.resize((max(1, int(w * s)), max(1, int(h * s))),
                                Image.NEAREST if s >= 1 else Image.BILINEAR)
                self._photo = ImageTk.PhotoImage(pic)
                c.create_image(ox, oy, image=self._photo, anchor="nw")
            except Exception:
                self._photo = None
        else:
            c.create_rectangle(ox, oy, ox + w * s, oy + h * s, outline="#555")
            c.create_text(ox + 8, oy + 8, anchor="nw", fill="#aaa",
                          text="no picture of this page found (or no Pillow) - the boxes only")
        line = "#e0b040"
        for name, (x, y, bw, bh) in self.boxes():
            if name in (self.picked, self.hover):
                continue
            c.create_rectangle(ox + x * s, oy + y * s, ox + (x + bw) * s, oy + (y + bh) * s, outline=line)
        for name, colour, width in ((self.hover, "#ffffff", 1), (self.picked, "#40c0ff", 2)):
            b = dict(self.boxes()).get(name)
            if b:
                x, y, bw, bh = b
                c.create_rectangle(ox + x * s, oy + y * s, ox + (x + bw) * s, oy + (y + bh) * s, outline=colour,
                                   width=width)

    def _at(self, e):
        s, ox, oy, _, _ = self._scale()
        px, py = (e.x - ox) / s, (e.y - oy) / s
        hits = [(bw * bh, n) for n, (x, y, bw, bh) in self.boxes() if x <= px < x + bw and y <= py < y + bh]
        return min(hits)[1] if hits else None            # the smallest box under the mouse: the one meant

    def _motion(self, e):
        n = self._at(e)
        if n != self.hover:
            self.hover = n
            self.say()
            self.draw()

    def _press(self, e):
        n = self._at(e)
        if n is not None and n != self.picked:
            self.picked = n
            self.fill_sprites()
            self.say()
            self.draw()

    def say(self):
        """The line under the picture: the sprite under the mouse, else the one picked, else the sheet."""
        if not self.sheet:
            return
        name = self.hover or self.picked
        b = dict(self.boxes()).get(name)
        if b:
            text = "%s  |  x %d, y %d, %d x %d  |  %s, page %s" % ((name,) + tuple(b) + (self.sheet["name"],
                                                                                        self.page))
        else:
            text = "%s: %d sprite(s) on this page; the game reads %s%s" % (
                self.page, len(self.boxes()), self.mod.rel(self.sheet["path"]) if self.mod else self.sheet["path"],
                (" (not %s)" % os.path.basename(self.sheet["other"])) if self.sheet["other"] else "")
        if self.sheet["error"]:
            text = self.sheet["error"]
        self.lbl_info.configure(text=text)

    # ---- the right click ----
    def _tree_menu(self, e):
        row = self.tv.identify_row(e.y)
        if row:
            self.tv.selection_set(row)
            self._tree_picked()
        self._popup(e)

    def _canvas_menu(self, e):
        n = self._at(e)
        if n is not None and n != self.picked:
            self.picked = n
            self.fill_sprites()
            self.say()
            self.draw()
        self._popup(e)

    def _popup(self, e):
        if not self.sheet or not self.page:
            return
        m = tk.Menu(self, tearoff=False)
        if self.picked:
            m.add_command(label=self.picked, state="disabled")
            m.add_separator()
            m.add_command(label="Open big", command=self.open_big)
            m.add_command(label="Save this sprite as PNG...", command=lambda: self.save_png(True))
            m.add_command(label="Copy its name", command=self.copy_name)
            m.add_separator()
        m.add_command(label="Save the whole page as PNG...", command=lambda: self.save_png(False))
        m.add_separator()
        if self.picked:
            m.add_command(label="Replace this sprite's picture...", command=self.replace_sprite)
            m.add_command(label="Place and size of this sprite...", command=self.place_window)
        m.add_command(label="Replace the whole page's picture...", command=self.replace_page)
        if (self.page, self.culture) in self.changes:
            m.add_command(label="Back to the page as it is in the files", command=self.page_back)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _crop(self):
        return dict(self.boxes()).get(self.picked) if self.picked else None

    def open_big(self):
        path = dict(self._cultures).get(self.culture)
        box = self._crop()
        if path and box:
            from .gui_picview import view_picture
            view_picture(self, path, title="%s (%s)" % (self.picked, self.page), crop=box)

    def copy_name(self):
        if self.picked:
            self.clipboard_clear()
            self.clipboard_append(self.picked)

    def save_png(self, sprite):
        if self._img is None:
            messagebox.showinfo(TITLE, "No picture of this page was found to save.", parent=self)
            return
        box = self._crop() if sprite else None
        if sprite and not box:
            return
        name = (self.picked if sprite else os.path.splitext(self.page)[0]) + ".png"
        out = filedialog.asksaveasfilename(parent=self, title="Save as PNG", defaultextension=".png",
                                           initialfile=name, filetypes=[("PNG picture", "*.png")])
        if not out:
            return
        im = self._img
        if box:
            x, y, w, h = box
            im = im.crop((x, y, x + w, y + h))
        try:
            im.save(out, "PNG")
        except OSError as e:
            messagebox.showerror(TITLE, "%s could not be saved: %s" % (out, e), parent=self)
            return
        self.lbl_info.configure(text="Saved %s" % out)

    # ---- changes (kept for Apply changes) ----
    def _set(self, im):
        key = (self.page, self.culture)
        self.undo.append(("pic", key, self.changes.get(key)))
        self.redo = []
        if im is None:
            self.changes.pop(key, None)
        else:
            self.changes[key] = im
        self._read_picture()
        self.draw()
        self.app.update_actions() if hasattr(self.app, "update_actions") else None

    def _pick_file(self):
        return filedialog.askopenfilename(parent=self, title="A picture", filetypes=[
            ("Pictures", "*.png *.tga *.dds *.jpg *.jpeg *.bmp"), ("All files", "*.*")])

    def replace_sprite(self):
        """The sprite's picture: a file of yours put in its box (stretched, kept in shape or filled), the rest of the
        page as it was."""
        box = self._crop()
        if self._img is None or not box:
            messagebox.showinfo(TITLE, "No picture of this page was found.", parent=self)
            return
        src = self._pick_file()
        if not src:
            return
        from .gui_util import ask_choice
        k = ask_choice(self, TITLE, "%s is %d x %d on the page. Your picture:" % (self.picked, box[2], box[3]),
                       ["Stretch it to the box", "Keep its shape (the rest clear)", "Fill the box (cut what is over)",
                        "Cancel"], default=0, cancel=3)
        if k == 3 or k is None:
            return
        from . import spriteedit
        from .recolour import read_picture
        try:
            pic = read_picture(src)
        except Exception as e:
            messagebox.showerror(TITLE, "%s cannot be read: %s" % (src, e), parent=self)
            return
        self._set(spriteedit.put_sprite(self._img, box, pic, ("stretch", "fit", "crop")[k]))
        self.lbl_info.configure(text="%s replaced - Apply changes writes the page (%s) into the mod" % (
            self.picked, self.page))

    def replace_page(self):
        """The whole page's picture: a file of yours, made the page's size (the sprites' boxes stay where they are)."""
        if self._img is None:
            messagebox.showinfo(TITLE, "No picture of this page was found.", parent=self)
            return
        src = self._pick_file()
        if not src:
            return
        from . import spriteedit
        from .recolour import read_picture
        try:
            pic = read_picture(src)
        except Exception as e:
            messagebox.showerror(TITLE, "%s cannot be read: %s" % (src, e), parent=self)
            return
        self._set(spriteedit.fit(pic, self._img.size))
        self.lbl_info.configure(text="Page %s replaced - Apply changes writes it into the mod" % self.page)

    def page_back(self):
        self._set(None)
        self.lbl_info.configure(text="Page %s: as it is in the files" % self.page)

    def step(self, back=True):
        """Undo (back) / Redo of the picture changes. True when there was a step."""
        src, dst = (self.undo, self.redo) if back else (self.redo, self.undo)
        if not src:
            return False
        kind, key, was = src.pop()
        held = self.changes if kind == "pic" else self.box_changes
        dst.append((kind, key, held.get(key)))
        if was is None:
            held.pop(key, None)
        else:
            held[key] = was
        if kind == "pic":
            self._read_picture()
        self.fill_sprites()
        self.say()
        self.draw()
        return True

    def dirty(self):
        return bool(self.changes or self.box_changes)

    def changed_page(self, page):
        """The page's picture changed here (its base culture's - the one the game falls back to), or None."""
        got = SY.page_cultures(self.mod, page) if self.mod else []
        return self.changes.get((page, got[0][0])) if got else None

    def changed_boxes(self):
        """{(sheet, sprite): (x, y, w, h)} of the boxes moved / sized here."""
        return {k: v[0] for k, v in self.box_changes.items()}

    def pending(self):
        return len(self.changes) + len(self.box_changes)

    def forget(self):
        """The changes written (or thrown away): the sheets read again the next time they are shown."""
        self.changes, self.undo, self.redo = {}, [], []
        self.box_changes = {}
        self.mod = None

    def plan_into(self, plan):
        """The changed pages written by plan (spriteedit.write), sheet by sheet."""
        from . import spriteedit
        for sh in self.sheets:
            mine = {k: v for k, v in self.changes.items() if k[0] in dict(sh["pages"])}
            if mine:
                spriteedit.write(plan, self.mod, sh, mine)
            for (name, sprite), (box, shown) in sorted(self.box_changes.items()):
                if name == sh["name"]:
                    spriteedit.set_box(plan, self.mod, sh, sprite, box, shown)

    def place_window(self):
        """The sprite's place and size on its page (its box: the picture it shows) and, on an .sd.xml sheet, the
        size the game shows it at (an engine stretches the picture to it) - kept for Apply changes."""
        box = self._crop()
        if not self.sheet or not box:
            return None
        key = (self.sheet["name"], self.picked)
        xml = self.sheet["kind"] == "text"
        shown = (self.box_changes.get(key) or (None, None))[1] or next(
            (sp["shown"] for sp in self._xml_sprites() if sp["name"] == self.picked), None) if xml else None
        w = tk.Toplevel(self)
        w.title("%s - place and size" % self.picked)
        w.transient(self)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        vs = {}
        rows = [("x", box[0], "from the page's left edge, pixels"), ("y", box[1], "from its top"),
                ("w", box[2], "the picture's width on the page"), ("h", box[3], "its height")]
        if xml:
            rows += [("shown w", (shown or box[2:])[0], "the width the game shows it at (the engine stretches it)"),
                     ("shown h", (shown or box[2:])[1], "the height the game shows it at")]
        for r, (k, val, why) in enumerate(rows):
            ttk.Label(f, text=k).grid(row=r, column=0, sticky="w", pady=2)
            vs[k] = tk.StringVar(value=str(val))
            ttk.Spinbox(f, from_=0, to=8192, textvariable=vs[k], width=7).grid(row=r, column=1, padx=6, pady=2)
            ttk.Label(f, text=why, foreground=theme.palette()["muted"]).grid(row=r, column=2, sticky="w")
        size = self._img.size if self._img is not None else None
        ttk.Label(f, text=("The page is %d x %d." % size) if size else "", foreground=theme.palette()["muted"]
                  ).grid(row=len(rows), column=0, columnspan=3, sticky="w", pady=(6, 0))

        def ok():
            try:
                nb = tuple(int(vs[k].get()) for k in ("x", "y", "w", "h"))
                ns = (int(vs["shown w"].get()), int(vs["shown h"].get())) if xml else None
            except ValueError:
                messagebox.showerror(TITLE, "Whole numbers only.", parent=w)
                return
            if nb[2] < 1 or nb[3] < 1 or (size and (nb[0] + nb[2] > size[0] or nb[1] + nb[3] > size[1])):
                messagebox.showerror(TITLE, "The box must lie on the page (%d x %d) and be at least 1 x 1." % size
                                     if size else "The box must be at least 1 x 1.", parent=w)
                return
            self.undo.append(("box", key, self.box_changes.get(key)))
            self.redo = []
            self.box_changes[key] = (nb, ns)
            w.destroy()
            self.fill_sprites()
            self.say()
            self.draw()
            self.lbl_info.configure(text="%s: at %d, %d, %d x %d - Apply changes writes it" % ((self.picked,) + nb))
            self.app.update_actions() if hasattr(self.app, "update_actions") else None
        b = ttk.Frame(f)
        b.grid(row=len(rows) + 1, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(b, text="OK", command=ok).pack(side="left", padx=4)
        ttk.Button(b, text="Cancel", command=w.destroy).pack(side="left")
        return w

    def _xml_sprites(self):
        try:
            with open(self.sheet["path"], "rb") as fh:
                return SY.sprite_list(fh.read().decode("latin-1"))
        except OSError:
            return []
