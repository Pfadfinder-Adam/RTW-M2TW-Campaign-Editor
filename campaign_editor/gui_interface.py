"""Interface (a work of the main window, beside Module builder): the game's menu screens as the game lays them out - every page of
the menu layout file (Rome / Barbarian Invasion / Alexander Rome.lnt, Medieval II mtw2.lnt; lnt.py) drawn on the
1024 x 768 layout with its own pictures and words. A piece is picked with a click, moved by dragging, sized by its
corner, nudged with the arrows (Shift: 10 pixels); its right click holds the rest - place and size, the page it opens,
its words and tooltip, Copy, Rename, Remove (no side panel: the screen gets the room). Copy makes the next numbered piece (the game finds many by their numbers), Remove takes one
out; a double click on a button opens the page it leads to, as in the game. Undo / Redo; nothing is written before
'Keep for Apply' and then Apply changes in the main window (a backup first; Restore undoes it).

The idea and the first map of the format: Wholesome Queen's RTW Sprite & HUD Studio, given to make this editor
better for everyone (CREDITS)."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import lnt as L
from . import theme
from .gui_util import ShortHint

TITLE = "Interface"
WORDS = "#ffdd77"                                    # the menus' gold words (RomeTW.exe: RGB 255, 221, 119)
HANDLE = 7                                   # the corner square that sizes a piece, in screen pixels
KINDS = {"UIP_MENU_BUTTON": "a button that opens a page", "UIP_BACK_BUTTON": "the back button",
         "UIP_STATIC_TEXT": "words", "UIP_EMPTY_ART": "a picture"}


class InterfacePanel(ttk.Frame):
    """A work of the main window (the user, 2026-10-15: not a window of its own), like the Module builder."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app, self.mod = app, None
        self.path, self.doc = None, None
        self.saved = self.kept = b""
        self.words = {}
        self.undo, self.redo = [], []
        self.page, self.picked = None, None
        self._pics, self._tex, self._fonts = {}, {}, {}
        self._drag = None
        self._build()
        self.load()

    def load(self):
        """The mod loaded now read (again only when it is another mod - work not kept stays while you look at other
        works)."""
        mod = self.app.mod
        if mod is self.mod and self.doc is not None:
            return
        self.mod = mod
        self.path = L.find(mod) if mod else None
        self.doc = L.Lnt.load(self.path) if self.path else None
        self.saved = self.doc.dump() if self.doc else b""
        self.kept = self.saved
        self.words = L.menu_texts(mod) if self.doc else {}
        self.undo, self.redo = [], []
        self.page, self.picked = None, None
        self._pics, self._tex, self._fonts = {}, {}, {}
        self.lbl_title.configure(text="The game's menu screens" + (" - %s" % mod.rel(self.path) if self.path else ""))
        self.lb_pages.delete(0, "end")
        self.tv.delete(*self.tv.get_children())
        if self.doc:
            self.lbl_status.configure(text="")
            self.fill_pages()
            first = self.doc.pages()[0] if self.doc.pages() else None
            if first:
                self.show_page(first)
        else:
            self.lbl_status.configure(text="Load a mod first." if not mod else (
                "This game / mod has no menu layout file (data/menu/Rome.lnt or mtw2.lnt) - nothing to show."))
            self.draw()

    # ---- a work of the main window (App.editor) ----
    def rebind(self, mod):
        """Another mod loaded: its menus are read; changes not kept for Apply are dropped (said)."""
        lost = 1 if self.doc is not None and self._unwritten() else 0
        self.load()
        return lost

    kind = "Interface"

    def dirty(self):
        return False                     # 'Keep for Apply' hands its changes to Apply, nothing waits here

    def pending(self):
        return 0

    def make_plan(self):
        raise ValueError("Interface: press 'Keep for Apply' under the screen first - then Apply changes writes it.")

    def may_close(self):
        """The editor is closing: changes not kept for Apply are never thrown away silently."""
        from .gui_util import ask_choice
        if not self.doc or not self._unwritten():
            return True
        k = ask_choice(self, TITLE, "The menu screens have changes not kept for Apply yet.\n\nKeep them for Apply, "
                                    "keep working, or throw them away?",
                       ["Keep for Apply", "Keep working", "Throw them away"], default=0, cancel=1, danger=2)
        if k in (1, None):
            return False
        if k == 0:
            self.write()
            return not self._unwritten()
        return True

    # ---- the window ----
    def _build(self):
        bar = ttk.Frame(self, padding=(10, 4, 10, 10))
        bar.pack(side="bottom", fill="x")
        self.lbl_status = ttk.Label(bar, foreground=theme.palette()["muted"])
        self.lbl_status.pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Keep for Apply", command=self.write).pack(side="right", padx=(0, theme.BUTTON_GAP))
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right", padx=(0, theme.BUTTON_GAP))
        top = ttk.Frame(self, padding=(10, 8, 10, 0))
        top.pack(fill="x")
        self.lbl_title = ttk.Label(top, font=("", 12, "bold"))
        self.lbl_title.pack(anchor="w")
        ShortHint(top, text=(
            "Every screen of the game's menus as the game lays it out (1024 x 768). Click a piece to pick it, drag it "
            "to move it, drag its corner to size it, the arrows nudge it (Shift: 10 pixels). A double click on a "
            "button opens the page it leads to. A right click on a piece: its values, Copy, Rename, Remove. Copy makes the next numbered piece - the game finds many pieces by "
            "their numbers (more faction buttons: copy the last one). Pieces with no picture of their own (empty_...) "
            "are drawn by the game itself; here they show as frames with their words. Nothing is written before "
            "Keep for Apply, then Apply changes (a backup first).")).pack(fill="x")
        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=6)
        # left: the pages and the pieces of the page on show
        left = ttk.Frame(body)
        body.add(left, weight=1)
        ttk.Label(left, text="Pages").pack(anchor="w")
        self.v_find = tk.StringVar()
        ent = ttk.Entry(left, textvariable=self.v_find)
        ent.pack(fill="x")
        self.v_find.trace_add("write", lambda *a: self.fill_pages())
        pf = ttk.Frame(left)
        pf.pack(fill="both", expand=True)
        self.lb_pages = tk.Listbox(pf, exportselection=False, height=12)
        sb = ttk.Scrollbar(pf, command=self.lb_pages.yview)
        self.lb_pages.configure(yscrollcommand=sb.set)
        self.lb_pages.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.lb_pages.bind("<<ListboxSelect>>", lambda e: self._page_picked())
        ttk.Label(left, text="Pieces of this page").pack(anchor="w", pady=(6, 0))
        tf = ttk.Frame(left)
        tf.pack(fill="both", expand=True)
        self.tv = ttk.Treeview(tf, columns=("x", "y", "w", "h"), show="tree headings", height=12)
        self.tv.heading("#0", text="piece")
        for c, t in (("x", "x"), ("y", "y"), ("w", "width"), ("h", "height")):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=46, anchor="e", stretch=False)
        self.tv.column("#0", width=180)
        sb2 = ttk.Scrollbar(tf, command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb2.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb2.pack(side="left", fill="y")
        self.tv.bind("<<TreeviewSelect>>", lambda e: self._tree_picked())
        # middle: the screen
        mid = ttk.Frame(body)
        body.add(mid, weight=4)
        self.canvas = tk.Canvas(mid, background="#202020", highlightthickness=0, takefocus=1)
        self.canvas.pack(fill="both", expand=True)
        c = self.canvas
        c.bind("<Configure>", lambda e: self.draw())
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._motion)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Double-Button-1>", self._double)
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            c.bind("<%s>" % key, lambda e, dx=dx, dy=dy: self.nudge(dx, dy, e))
        self.v_back = tk.BooleanVar(value=True)
        mb = ttk.Frame(mid)
        mb.pack(fill="x", pady=(4, 0))
        ttk.Checkbutton(mb, text="Pictures", variable=self.v_back, command=self.draw).pack(side="left")
        self.v_frames = tk.BooleanVar(value=False)       # the game's own look first; frames on a tick
        ttk.Checkbutton(mb, text="Frames of every piece", variable=self.v_frames, command=self.draw).pack(
            side="left", padx=(theme.BUTTON_GAP * 2, 0))
        ttk.Button(mb, text="Redo", command=self.do_redo).pack(side="right")
        ttk.Button(mb, text="Undo", command=self.do_undo).pack(side="right", padx=(0, theme.BUTTON_GAP))
        self.lbl_way = ttk.Label(mb, foreground=theme.palette()["muted"])
        self.lbl_way.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        # the piece picked, in one line under the screen; everything done to it is on its right click (the user,
        # 2026-10-15: no side panel - the buttons and values in the context menu, the screen gets the room)
        self.lbl_info = ttk.Label(mid, foreground=theme.palette()["muted"])
        self.lbl_info.pack(fill="x", pady=(2, 0))
        c.bind("<Button-3>", self._menu)
        self.tv.bind("<Button-3>", self._tree_menu)

    # ---- pages and pieces ----
    def fill_pages(self):
        want = self.v_find.get().strip().lower()
        self.lb_pages.delete(0, "end")
        self._shown_pages = [p for p in self.doc.pages() if not want or want in p.lower()]
        for p in self._shown_pages:
            self.lb_pages.insert("end", "%s  (%d)" % (p, len(self.doc.pieces(p))))
            if p == self.page:
                self.lb_pages.selection_set("end")

    def _page_picked(self):
        sel = self.lb_pages.curselection()
        if sel:
            self.show_page(self._shown_pages[sel[0]])

    def show_page(self, page, pick=None):
        self.page, self.picked = page, pick
        self.fill_pieces()
        way = self.doc.opened_by().get(page)
        self.lbl_way.configure(text=("opened from: " + ", ".join("%s (%s)" % w for w in way[:3])) if way else "")
        self.fill_form()
        self.draw()

    def fill_pieces(self):
        self.tv.delete(*self.tv.get_children())
        for x in self.doc.pieces(self.page):
            self.tv.insert("", "end", iid=str(x["index"]), text=x["name"],
                           values=tuple("" if x[k] is None else x[k] for k in L.PARAMS))
        if self.picked is not None and self.tv.exists(str(self.picked)):
            self.tv.selection_set(str(self.picked))
            self.tv.see(str(self.picked))

    def _tree_picked(self):
        sel = self.tv.selection()
        if sel and int(sel[0]) != self.picked:
            self.picked = int(sel[0])
            self.fill_form()
            self.draw()

    def current(self):
        # pieces are picked by their place on the page: a page may hold two of one name (Medieval II's main menu)
        return self.doc.piece(self.page, self.picked) if self.doc and self.page and self.picked is not None else None

    def fill_form(self):
        """The line under the screen: the piece picked - its name, kind, place, words, picture."""
        x = self.current()
        if not x:
            self.lbl_info.configure(text="Click a piece to pick it; right click it for its values and Copy / Rename / "
                                         "Remove.")
            return
        parts = [x["name"], x["identifier"] + ((" (" + KINDS[x["identifier"]] + ")") if x["identifier"] in KINDS
                                               else ""),
                 "x %s, y %s, %s x %s" % tuple("-" if x[k] is None else x[k] for k in L.PARAMS)]
        words = self.words.get((x["text"] or "").upper())
        if words:
            parts.append('shows "%s"' % words)
        if x["menu_id"]:
            parts.append("opens %s" % x["menu_id"])
        art = self.doc.art(x)
        parts.append(("picture %s" % art[0]) if art else "drawn by the game")
        self.lbl_info.configure(text="  |  ".join(parts))

    # ---- the right click ----
    def _menu(self, e):
        if not self.doc or not self.page:
            return
        name, _ = self._hit(e)
        if name is not None and name != self.picked:
            self.picked = name
            self.fill_pieces()
            self.fill_form()
            self.draw()
        self._popup(e)

    def _tree_menu(self, e):
        row = self.tv.identify_row(e.y)
        if row:
            self.tv.selection_set(row)
            self.picked = int(row)
            self.fill_form()
            self.draw()
            self._popup(e)

    def _popup(self, e):
        x = self.current()
        if not x:
            return
        m = tk.Menu(self, tearoff=False)
        m.add_command(label=x["name"], state="disabled")
        m.add_separator()
        m.add_command(label="Place and size (x %s, y %s, %s x %s)..." % tuple(
            "-" if x[k] is None else x[k] for k in L.PARAMS), command=self.ask_place)
        m.add_command(label="Opens the page: %s..." % (x["menu_id"] or "none"),
                      command=lambda: self.ask_value("menu_id", "The page this button opens (a page name):"))
        if x["text"] is not None:
            m.add_command(label="Words (text key): %s..." % x["text"],
                          command=lambda: self.ask_value("text", "The text key of its words (menu_english.txt):"))
        m.add_command(label="Tooltip (text key): %s..." % (x["tooltip"] or "none"),
                      command=lambda: self.ask_value("tooltip", "The text key of its tooltip:"))
        m.add_separator()
        m.add_command(label="Copy (the next number)", command=self.copy_piece)
        slot = L.RE_SLOT.match(x["name"] or "")
        if slot:
            have = len(L.slot_rows(self.doc).get((self.page, slot.group(1)), []))
            m.add_command(label="Faction slots on this page: %d - more..." % have,
                          command=lambda: self.more_slots(slot.group(1)))
        m.add_command(label="Rename...", command=self.rename_piece)
        m.add_command(label="Remove", command=self.remove_piece)
        if x["menu_id"] in self.doc.pages():
            m.add_separator()
            m.add_command(label="Open the page %s" % x["menu_id"], command=self.open_target)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def ask_value(self, key, prompt):
        x = self.current()
        if not x:
            return
        got = simpledialog.askstring(TITLE, prompt, initialvalue=x.get(key) or "", parent=self)
        if got is not None:
            self.set_value(key, got)

    def ask_place(self):
        """x, y, width and height of the piece picked in one small window."""
        x = self.current()
        if not x:
            return
        d = tk.Toplevel(self)
        d.title("%s - place and size" % x["name"])
        d.transient(self.winfo_toplevel())
        f = ttk.Frame(d, padding=10)
        f.pack(fill="both", expand=True)
        vs = {}
        for i, (key, label) in enumerate(zip(L.PARAMS, ("x (left)", "y (top)", "width", "height"))):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky="w", pady=2)
            vs[key] = tk.StringVar(value="" if x[key] is None else str(x[key]))
            ttk.Entry(f, textvariable=vs[key], width=10).grid(row=i, column=1, sticky="w", padx=(8, 0), pady=2)

        def ok(*_):
            try:
                vals = {k: int(v.get()) for k, v in vs.items() if v.get().strip()}
            except ValueError:
                messagebox.showerror(TITLE, "Whole numbers only (pixels on the 1024 x 768 layout).", parent=d)
                return
            d.destroy()
            if any(vals.get(k) != x[k] for k in vals):
                self._remember()
                self.doc.move(self.page, x["index"], **vals)
                self.fill_pieces()
                self.fill_form()
                self.draw()
        b = ttk.Frame(f)
        b.grid(row=4, column=0, columnspan=2, pady=(8, 0), sticky="e")
        ttk.Button(b, text="OK", command=ok).pack(side="left")
        ttk.Button(b, text="Cancel", command=d.destroy).pack(side="left", padx=(theme.BUTTON_GAP, 0))
        d.bind("<Return>", ok)
        d.bind("<Escape>", lambda e: d.destroy())
        return d

    # ---- drawing ----
    def _scale(self):
        w, h = self.doc.size()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        s = min(cw / w, ch / h)
        return s, (cw - w * s) / 2, (ch - h * s) / 2

    def _texture(self, page, folder=""):
        if page not in self._tex:
            self._tex[page] = None
            p = L.texture_file(self.mod, self.path, page, folder)
            if p:
                try:
                    from .recolour import read_picture
                    self._tex[page] = read_picture(p)
                except Exception:
                    pass
        return self._tex[page]

    def _font(self, font_id):
        """The game's letters for a font name (lnt.font_source): a Pillow TrueType font or a .cuf font, cached."""
        if font_id not in self._fonts:
            self._fonts[font_id] = None
            src = L.font_source(self.mod, self.doc, font_id)
            try:
                if src and src[0] == "ttf":
                    from PIL import ImageFont
                    self._fonts[font_id] = ("ttf", ImageFont.truetype(src[1], src[2]))
                elif src:
                    from . import cuf
                    self._fonts[font_id] = ("cuf", cuf.read(src[1]))
            except Exception:
                pass
        return self._fonts[font_id]

    def _part(self, name):
        """A part picture of data/menu (buttons_composite2.tga...) as RGBA, cached; None when not there."""
        if name not in self._tex:
            self._tex[name] = None
            p = L.texture_file(self.mod, self.path, name)
            if p:
                try:
                    from .recolour import read_picture
                    self._tex[name] = read_picture(p)
                except Exception:
                    pass
        return self._tex[name]

    def _drawn(self, k, w, h, s):
        """(PhotoImage, offset in layout pixels) of a piece the game draws itself, at the screen's scale."""
        key = ("drawn", k, int(w), int(h))
        if key not in self._pics:
            self._pics[key] = None
            try:
                from PIL import Image, ImageTk
                from . import menudraw as MD
                img, off = MD.piece_image(self._part, k, w / s, h / s)
                if img is not None:
                    img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)
                    self._pics[key] = (ImageTk.PhotoImage(img), off)
            except Exception:
                pass
        return self._pics[key]

    def _words_image(self, words, font_id, s, box_w, colour=(232, 220, 176), shadow=False):
        """The words in the game's letters and colour at the screen's scale (lines broken to the piece's width as
        the game does; static texts with the game's black shadow 1 px left and down), or None without Pillow /
        a font."""
        key = (words, font_id, round(s, 3), int(box_w), colour, shadow)
        if key in self._pics:
            return self._pics[key]
        self._pics[key] = None
        f = self._font(font_id)
        if f is None:
            return None
        try:
            from PIL import Image, ImageDraw, ImageTk
            from . import cuf

            def line_img(text):
                if f[0] == "cuf":
                    return cuf.to_image(f[1], text)
                l, t, r, b = f[1].getbbox(text or " ")
                im = Image.new("L", (max(1, r), max(1, b)), 0)
                ImageDraw.Draw(im).text((0, 0), text, font=f[1], fill=255)
                return im
            limit = max(8, box_w / s - 4)
            lines, cur = [], ""
            for w in words.split():
                trial = (cur + " " + w).strip()
                if cur and line_img(trial).width > limit:
                    lines.append(cur)
                    cur = w
                else:
                    cur = trial
            lines.append(cur)
            imgs = [line_img(t) for t in lines]
            W, H = max(i.width for i in imgs), sum(i.height for i in imgs)
            mask = Image.new("L", (W, H), 0)
            y = 0
            for i in imgs:
                mask.paste(i, ((W - i.width) // 2, y))
                y += i.height
            col = Image.new("RGBA", (W + 1, H + 1), (0, 0, 0, 0))
            if shadow:
                black = Image.new("RGBA", mask.size, (0, 0, 0, 255))
                black.putalpha(mask)
                col.alpha_composite(black, (0, 1))
            front = Image.new("RGBA", mask.size, tuple(colour) + (255,))
            front.putalpha(mask)
            col.alpha_composite(front, (1, 0))
            W, H = col.size
            col = col.resize((max(1, int(W * s)), max(1, int(H * s))), Image.LANCZOS)
            self._pics[key] = ImageTk.PhotoImage(col)
        except Exception:
            self._pics[key] = None
        return self._pics[key]

    def _picture(self, x, s):
        art = self.doc.art(x)
        if not art:
            return None
        page, box, folder = art
        w = int(round((x["width"] or box[2] - box[0]) * s))
        h = int(round((x["height"] or box[3] - box[1]) * s))
        key = (page, box, w, h)
        if key not in self._pics:
            self._pics[key] = None
            tex = self._texture(page, folder)
            if tex is not None and w > 0 and h > 0:
                try:
                    from PIL import Image, ImageTk
                    im = tex.crop(box).resize((w, h), Image.LANCZOS)
                    self._pics[key] = ImageTk.PhotoImage(im)
                except Exception:
                    pass
        return self._pics[key]

    def _rect(self, x):
        s, ox, oy = self._scale()
        art = self.doc.art(x)
        w = x["width"] if x["width"] is not None else (art[1][2] - art[1][0] if art else 40)
        h = x["height"] if x["height"] is not None else (art[1][3] - art[1][1] if art else 20)
        x0, y0 = ox + (x["x"] or 0) * s, oy + (x["y"] or 0) * s
        return x0, y0, x0 + w * s, y0 + h * s

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self.doc or not self.page:
            return
        s, ox, oy = self._scale()
        lw, lh = self.doc.size()
        c.create_rectangle(ox, oy, ox + lw * s, oy + lh * s, fill="#101010", outline="#606060")
        pal_sel = "#ffd400"
        # the game draws its 'background' page (the backdrop) under every menu page
        if self.v_back.get() and self.page != "background" and "background" in self.doc.pages():
            for x in self.doc.pieces("background"):
                pic = self._picture(x, s)
                if pic is not None:
                    x0, y0, _, _ = self._rect(x)
                    c.create_image(x0, y0, image=pic, anchor="nw")
        from . import menudraw as MD
        for x in self.doc.pieces(self.page):
            x0, y0, x1, y1 = self._rect(x)
            pic = self._picture(x, s) if self.v_back.get() else None
            k = MD.kind(x["identifier"], x["object"], self.doc.art(x) is not None)
            if pic is not None:
                c.create_image(x0, y0, image=pic, anchor="nw")
            else:
                drawn = self._drawn(k, x1 - x0, y1 - y0, s) if self.v_back.get() else None
                if drawn is not None:                       # what the game draws itself, from its own parts
                    img, off = drawn
                    c.create_image(x0 - off * s, y0 - off * s, image=img, anchor="nw")
                if self.v_frames.get() or x["index"] == self.picked:
                    c.create_rectangle(x0, y0, x1, y1, outline="#5a7fa8")
            words = self.words.get((x["text"] or "").upper())
            if words:
                anchor = {"left": "w", "right": "e"}.get(x["align"] or "", "center")
                tx = {"w": x0 + 3, "e": x1 - 3}.get(anchor, (x0 + x1) / 2)
                img = self._words_image(words, x["font"], s, x1 - x0, *MD.text_colour(k))
                if img is not None:                         # in the game's own letters
                    c.create_image(tx, (y0 + y1) / 2, image=img, anchor=anchor)
                else:
                    c.create_text(tx, (y0 + y1) / 2, text=words, fill=WORDS, anchor=anchor,
                                  width=max(10, x1 - x0 - 4), font=("", max(7, int(10 * s))))
            if x["index"] == self.picked:
                c.create_rectangle(x0, y0, x1, y1, outline=pal_sel, width=2)
                c.create_rectangle(x1 - HANDLE, y1 - HANDLE, x1, y1, fill=pal_sel, outline="")
        arts = [self.doc.art(x) for x in self.doc.pieces(self.page)]
        unseen = [a for a in arts if a and self._texture(a[0], a[2]) is None]
        self.lbl_status.configure(text="page %s - %d pieces%s%s" % (
            self.page, len(self.doc.pieces(self.page)), "  (changes not kept for Apply yet)" if self._unwritten()
            else "", ("  - %d picture(s) not found as files (Medieval II keeps them in its .pack files until the game "
                      "is unpacked): shown as frames" % len(unseen)) if unseen else ""))

    # ---- the mouse and the keys ----
    def _hit(self, e):
        """(piece's place on the page, 'size' on its corner / 'move') under the mouse - the smallest piece first."""
        best = None
        for x in self.doc.pieces(self.page):
            x0, y0, x1, y1 = self._rect(x)
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                area = (x1 - x0) * (y1 - y0)
                if x["index"] == self.picked and e.x >= x1 - HANDLE and e.y >= y1 - HANDLE:
                    return x["index"], "size"
                if best is None or area < best[0]:
                    best = (area, x["index"])
        return (best[1], "move") if best else (None, None)

    def _press(self, e):
        self.canvas.focus_set()
        if not self.doc or not self.page:
            return
        name, how = self._hit(e)
        if name != self.picked:
            self.picked = name
            self.fill_pieces()
            self.fill_form()
            self.draw()
        x = self.current()
        self._drag = (how, e.x, e.y, dict(x), False) if x else None

    def _motion(self, e):
        if not self._drag:
            return
        how, sx, sy, start, moved = self._drag
        s, _, _ = self._scale()
        dx, dy = int(round((e.x - sx) / s)), int(round((e.y - sy) / s))
        if not moved and (dx or dy):
            self._remember()
            self._drag = (how, sx, sy, start, True)
        if how == "move":
            self.doc.move(self.page, start["index"], x=(start["x"] or 0) + dx, y=(start["y"] or 0) + dy)
        else:
            r = self._rect(start)
            w0, h0 = (r[2] - r[0]) / s, (r[3] - r[1]) / s
            self.doc.move(self.page, start["index"], width=max(1, w0 + dx), height=max(1, h0 + dy))
        self.fill_form()
        self.draw()

    def _release(self, e):
        if self._drag and self._drag[4]:
            self.fill_pieces()
        self._drag = None

    def _double(self, e):
        name, _ = self._hit(e)
        x = self.doc.piece(self.page, name) if name is not None else None
        if x and x["menu_id"] and x["menu_id"] in self.doc.pages():
            self.show_page(x["menu_id"])
            self.fill_pages()

    def nudge(self, dx, dy, e=None):
        x = self.current()
        if not x:
            return "break"
        step = 10 if e is not None and (e.state & 0x1) else 1
        self._remember()
        self.doc.move(self.page, x["index"], x=(x["x"] or 0) + dx * step, y=(x["y"] or 0) + dy * step)
        self.fill_pieces()
        self.fill_form()
        self.draw()
        return "break"

    # ---- changes ----
    def _remember(self):
        self.undo.append((list(self.doc.lines), self.page, self.picked))
        self.redo.clear()

    def _restore(self, state):
        lines, page, picked = state
        self.doc.lines = list(lines)
        self.doc.parse()
        self.fill_pages()
        self.show_page(page if page in self.doc.pages() else self.doc.pages()[0], picked)

    def do_undo(self):
        if self.undo:
            self.redo.append((list(self.doc.lines), self.page, self.picked))
            self._restore(self.undo.pop())

    def do_redo(self):
        if self.redo:
            self.undo.append((list(self.doc.lines), self.page, self.picked))
            self._restore(self.redo.pop())

    def set_value(self, key, value):
        x = self.current()
        if not x:
            return
        value = str(value).strip()
        old = "" if x.get(key) is None else str(x[key])
        if value == old:
            return
        try:
            if key in L.PARAMS:
                value = int(value)
            self._remember()
            if key == "text":
                self.doc.set_text(self.page, x["index"], value)
            elif key == "tooltip":
                self.doc.set_param(self.page, x["index"], "tool_tip_id", value)
            else:
                self.doc.set_param(self.page, x["index"], key, value)
        except (ValueError, L.LntError) as err:
            if self.undo:
                self.undo.pop()
            messagebox.showerror(TITLE, "Not changed: %s" % err, parent=self)
            self.fill_form()
            return
        self.fill_pieces()
        self.fill_form()
        self.draw()

    def copy_piece(self):
        x = self.current()
        if not x:
            return
        new = L.free_name(self.doc, self.page, x["name"])
        self._remember()
        self.picked = self.doc.copy_piece(self.page, x["index"], new, dx=10, dy=10)
        self.fill_pieces()
        self.fill_form()
        self.fill_pages()
        self.draw()

    def playable_count(self):
        """The playable (and unlockable) factions of the campaign on show, or None."""
        try:
            from .strat import Strat
            camp = self.app.v_campaign.get()
            s = Strat(self.mod.load(self.mod.campaign_file(camp, "descr_strat.txt")))
            return sum(len(lst["items"]) for lst in (s.playable, getattr(s, "unlockable", None)) if lst)
        except Exception:
            return None

    def more_slots(self, stem):
        """The faction slots of this page made up to a number: copies of the last one under the next numbers, on its
        grid continued - the faction-select screen shows a faction only in a slot the file has."""
        have = len(L.slot_rows(self.doc).get((self.page, stem), []))
        want = self.playable_count()
        total = simpledialog.askinteger(
            TITLE, "%s slots on this page: %d.%s\n\nHow many should there be?" % (
                stem + "N", have, (" The campaign has %d playable faction(s)." % want) if want else ""),
            initialvalue=max(have, want or have), minvalue=have, maxvalue=200, parent=self)
        if not total or total <= have:
            return
        self._remember()
        try:
            n = L.add_slots(self.doc, self.page, stem, total)
        except L.LntError as err:
            self.undo.pop()
            messagebox.showerror(TITLE, "Not changed: %s" % err, parent=self)
            return
        self.fill_pieces()
        self.fill_form()
        self.draw()
        self.lbl_status.configure(text="%d slot(s) added on %s - their grid continued; Keep for Apply writes them"
                                       % (n, self.page))

    def rename_piece(self):
        x = self.current()
        if not x:
            return
        new = simpledialog.askstring(TITLE, "A new name for %s (the game finds some pieces by their name):" %
                                     x["name"], initialvalue=x["name"], parent=self)
        if not new or new.strip() == x["name"]:
            return
        try:
            if self.doc.piece(self.page, new.strip()):
                raise L.LntError("this page has a piece %s already" % new.strip())
            self._remember()
            self.doc.rename_piece(self.page, x["index"], new.strip())
        except L.LntError as err:
            messagebox.showerror(TITLE, str(err), parent=self)
            return
        self.fill_pieces()
        self.fill_form()
        self.draw()

    def remove_piece(self):
        x = self.current()
        if not x:
            return
        self._remember()
        self.doc.remove_piece(self.page, x["index"])
        self.picked = None
        self.fill_pieces()
        self.fill_form()
        self.fill_pages()
        self.draw()

    def open_target(self):
        x = self.current()
        if x and x["menu_id"] in self.doc.pages():
            self.show_page(x["menu_id"])
            self.fill_pages()

    # ---- writing ----
    def _unwritten(self):
        return bool(self.doc) and self.doc.dump() != self.kept

    def _plan(self):
        from .plan import Plan
        plan = Plan(self.mod, "interface", "interface", {})
        L.plan_write(plan, self.path, self.doc)
        return plan

    def preview(self):
        if not self.doc or self.doc.dump() == self.saved:
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        self.app.show_text("Interface - every change (nothing written yet)", self._plan().report())

    def write(self):
        from .gui_util import keep_for_apply
        if not self.doc:
            return False

        def after(bdir):
            from . import log
            log.write("Menu layout changed (backup %s)" % bdir)
        got = keep_for_apply(self, "interface", "The game's menu screens", self._plan, after, TITLE)
        if got:
            self.kept = self.doc.dump()
            self.draw()
        return got



def open_interface(app):
    """The Interface work shown in the main window (the work bar's 'Interface')."""
    app.v_work.set("interface")
    app.work_changed()
    return app.editors["interface"]


__all__ = ["InterfacePanel", "open_interface"]
