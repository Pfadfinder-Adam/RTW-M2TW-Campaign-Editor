"""Interface... (the work bar, beside Module builder): the game's menu screens as the game lays them out - every page of
the menu layout file (Rome / Barbarian Invasion / Alexander Rome.lnt, Medieval II mtw2.lnt; lnt.py) drawn on the
1024 x 768 layout with its own pictures and words. A piece is picked with a click, moved by dragging, sized by its
corner, nudged with the arrows (Shift: 10 pixels); its name, place, size, the page it opens, its words and tooltip
are set on the right. Copy makes the next numbered piece (the game finds many by their numbers), Remove takes one
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
HANDLE = 7                                   # the corner square that sizes a piece, in screen pixels
KINDS = {"UIP_MENU_BUTTON": "a button that opens a page", "UIP_BACK_BUTTON": "the back button",
         "UIP_STATIC_TEXT": "words", "UIP_EMPTY_ART": "a picture"}


class InterfaceWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.mod = app, app.mod
        self.title(TITLE)
        self.transient(app)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d" % (min(1500, sw - 40), min(900, sh - 80)))
        self.minsize(min(900, sw - 40), min(560, sh - 100))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.path = L.find(self.mod)
        self.doc = L.Lnt.load(self.path) if self.path else None
        self.saved = self.doc.dump() if self.doc else b""
        self.kept = self.saved
        self.words = L.menu_texts(self.mod) if self.doc else {}
        self.undo, self.redo = [], []
        self.page, self.picked = None, None
        self._pics, self._tex = {}, {}
        self._drag = None
        self._build()
        if self.doc:
            self.fill_pages()
            first = self.doc.pages()[0] if self.doc.pages() else None
            if first:
                self.show_page(first)

    # ---- the window ----
    def _build(self):
        bar = ttk.Frame(self, padding=(10, 4, 10, 10))
        bar.pack(side="bottom", fill="x")
        self.lbl_status = ttk.Label(bar, foreground=theme.palette()["muted"])
        self.lbl_status.pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Keep for Apply", command=self.write).pack(side="right", padx=(0, theme.BUTTON_GAP))
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right", padx=(0, theme.BUTTON_GAP))
        top = ttk.Frame(self, padding=(10, 8, 10, 0))
        top.pack(fill="x")
        ttk.Label(top, text="The game's menu screens" + (" - %s" % self.mod.rel(self.path) if self.path else ""),
                  font=("", 12, "bold")).pack(anchor="w")
        ShortHint(top, text=(
            "Every screen of the game's menus as the game lays it out (1024 x 768). Click a piece to pick it, drag it "
            "to move it, drag its corner to size it, the arrows nudge it (Shift: 10 pixels). A double click on a "
            "button opens the page it leads to. Copy makes the next numbered piece - the game finds many pieces by "
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
        self.v_frames = tk.BooleanVar(value=True)
        ttk.Checkbutton(mb, text="Frames of every piece", variable=self.v_frames, command=self.draw).pack(
            side="left", padx=(theme.BUTTON_GAP * 2, 0))
        ttk.Button(mb, text="Redo", command=self.do_redo).pack(side="right")
        ttk.Button(mb, text="Undo", command=self.do_undo).pack(side="right", padx=(0, theme.BUTTON_GAP))
        self.lbl_way = ttk.Label(mb, foreground=theme.palette()["muted"])
        self.lbl_way.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        # right: the piece picked
        right = ttk.Frame(body, padding=(8, 0, 0, 0))
        body.add(right, weight=1)
        self.lbl_piece = ttk.Label(right, font=("", 11, "bold"), wraplength=260)
        self.lbl_piece.pack(anchor="w")
        self.lbl_kind = ttk.Label(right, foreground=theme.palette()["muted"], wraplength=260)
        self.lbl_kind.pack(anchor="w")
        form = ttk.Frame(right)
        form.pack(fill="x", pady=6)
        self.vars = {}
        for i, (key, label) in enumerate((("x", "x (left)"), ("y", "y (top)"), ("width", "width"),
                                          ("height", "height"), ("menu_id", "opens the page"),
                                          ("text", "words (text key)"), ("tooltip", "tooltip (text key)"))):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=1)
            v = tk.StringVar()
            e = ttk.Entry(form, textvariable=v, width=22)
            e.grid(row=i, column=1, sticky="we", pady=1)
            e.bind("<Return>", lambda ev, k=key: self.set_field(k))
            e.bind("<FocusOut>", lambda ev, k=key: self.set_field(k))
            self.vars[key] = v
        form.columnconfigure(1, weight=1)
        self.lbl_words = ttk.Label(right, wraplength=260, justify="left")
        self.lbl_words.pack(anchor="w", pady=(2, 6))
        self.lbl_art = ttk.Label(right, foreground=theme.palette()["muted"], wraplength=260, justify="left")
        self.lbl_art.pack(anchor="w")
        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=8)
        for text, cmd in (("Copy", self.copy_piece), ("Rename...", self.rename_piece), ("Remove", self.remove_piece),
                          ("Open its page", self.open_target)):
            ttk.Button(btns, text=text, command=cmd).pack(fill="x", pady=1)
        if not self.doc:
            self.lbl_status.configure(text="This game / mod has no menu layout file (data/menu/Rome.lnt or "
                                           "mtw2.lnt) - nothing to show.")

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
            self.tv.insert("", "end", iid=x["name"], text=x["name"],
                           values=tuple("" if x[k] is None else x[k] for k in L.PARAMS))
        if self.picked and self.tv.exists(self.picked):
            self.tv.selection_set(self.picked)
            self.tv.see(self.picked)

    def _tree_picked(self):
        sel = self.tv.selection()
        if sel and sel[0] != self.picked:
            self.picked = sel[0]
            self.fill_form()
            self.draw()

    def current(self):
        return self.doc.piece(self.page, self.picked) if self.doc and self.page and self.picked else None

    def fill_form(self):
        x = self.current()
        for k, v in self.vars.items():
            v.set("" if not x or x.get(k) is None else str(x[k]))
        if not x:
            self.lbl_piece.configure(text="(click a piece)")
            for w in (self.lbl_kind, self.lbl_words, self.lbl_art):
                w.configure(text="")
            return
        self.lbl_piece.configure(text=x["name"])
        self.lbl_kind.configure(text="%s%s" % (x["identifier"], (" - " + KINDS[x["identifier"]])
                                               if x["identifier"] in KINDS else ""))
        words = self.words.get((x["text"] or "").upper())
        self.lbl_words.configure(text=("shows: %s" % words) if words else "")
        art = self.doc.art(x)
        self.lbl_art.configure(text=("picture: %s, %s" % (x["object"], art[0])) if art else
                               "picture: %s (drawn by the game)" % (x["object"] or "none"))

    # ---- drawing ----
    def _scale(self):
        w, h = self.doc.size()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        s = min(cw / w, ch / h)
        return s, (cw - w * s) / 2, (ch - h * s) / 2

    def _texture(self, page):
        if page not in self._tex:
            self._tex[page] = None
            p = L.texture_file(self.mod, self.path, page)
            if p:
                try:
                    from .recolour import read_picture
                    self._tex[page] = read_picture(p)
                except Exception:
                    pass
        return self._tex[page]

    def _picture(self, x, s):
        art = self.doc.art(x)
        if not art:
            return None
        page, box, _ = art
        w = int(round((x["width"] or box[2] - box[0]) * s))
        h = int(round((x["height"] or box[3] - box[1]) * s))
        key = (page, box, w, h)
        if key not in self._pics:
            self._pics[key] = None
            tex = self._texture(page)
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
        for x in self.doc.pieces(self.page):
            x0, y0, x1, y1 = self._rect(x)
            pic = self._picture(x, s) if self.v_back.get() else None
            if pic is not None:
                c.create_image(x0, y0, image=pic, anchor="nw")
            elif self.v_frames.get() or x["name"] == self.picked:
                c.create_rectangle(x0, y0, x1, y1, outline="#5a7fa8")
            words = self.words.get((x["text"] or "").upper())
            if words:
                anchor = {"left": "w", "right": "e"}.get(x["align"] or "", "center")
                tx = {"w": x0 + 3, "e": x1 - 3}.get(anchor, (x0 + x1) / 2)
                c.create_text(tx, (y0 + y1) / 2, text=words, fill="#e8dcb0", anchor=anchor,
                              width=max(10, x1 - x0 - 4), font=("", max(7, int(10 * s))))
            if x["name"] == self.picked:
                c.create_rectangle(x0, y0, x1, y1, outline=pal_sel, width=2)
                c.create_rectangle(x1 - HANDLE, y1 - HANDLE, x1, y1, fill=pal_sel, outline="")
        self.lbl_status.configure(text="page %s - %d pieces%s" % (
            self.page, len(self.doc.pieces(self.page)), "  (changes not kept for Apply yet)" if self._unwritten()
            else ""))

    # ---- the mouse and the keys ----
    def _hit(self, e):
        """(piece name, 'size' on its corner / 'move') under the mouse - the smallest piece there first."""
        best = None
        for x in self.doc.pieces(self.page):
            x0, y0, x1, y1 = self._rect(x)
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                area = (x1 - x0) * (y1 - y0)
                if x["name"] == self.picked and e.x >= x1 - HANDLE and e.y >= y1 - HANDLE:
                    return x["name"], "size"
                if best is None or area < best[0]:
                    best = (area, x["name"])
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
            self.doc.move(self.page, start["name"], x=(start["x"] or 0) + dx, y=(start["y"] or 0) + dy)
        else:
            r = self._rect(start)
            w0, h0 = (r[2] - r[0]) / s, (r[3] - r[1]) / s
            self.doc.move(self.page, start["name"], width=max(1, w0 + dx), height=max(1, h0 + dy))
        self.fill_form()
        self.draw()

    def _release(self, e):
        if self._drag and self._drag[4]:
            self.fill_pieces()
        self._drag = None

    def _double(self, e):
        name, _ = self._hit(e)
        x = self.doc.piece(self.page, name) if name else None
        if x and x["menu_id"] and x["menu_id"] in self.doc.pages():
            self.show_page(x["menu_id"])
            self.fill_pages()

    def nudge(self, dx, dy, e=None):
        x = self.current()
        if not x:
            return "break"
        step = 10 if e is not None and (e.state & 0x1) else 1
        self._remember()
        self.doc.move(self.page, x["name"], x=(x["x"] or 0) + dx * step, y=(x["y"] or 0) + dy * step)
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

    def set_field(self, key):
        x = self.current()
        if not x:
            return
        value = self.vars[key].get().strip()
        old = "" if x.get(key) is None else str(x[key])
        if value == old:
            return
        try:
            if key in L.PARAMS:
                value = int(value)
            self._remember()
            if key == "text":
                self.doc.set_text(self.page, x["name"], value)
            elif key == "tooltip":
                self.doc.set_param(self.page, x["name"], "tool_tip_id", value)
            else:
                self.doc.set_param(self.page, x["name"], key, value)
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
        self.doc.copy_piece(self.page, x["name"], new, dx=10, dy=10)
        self.picked = new
        self.fill_pieces()
        self.fill_form()
        self.fill_pages()
        self.draw()

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
            self.doc.rename_piece(self.page, x["name"], new.strip())
        except L.LntError as err:
            messagebox.showerror(TITLE, str(err), parent=self)
            return
        self.picked = new.strip()
        self.fill_pieces()
        self.fill_form()
        self.draw()

    def remove_piece(self):
        x = self.current()
        if not x:
            return
        self._remember()
        self.doc.remove_piece(self.page, x["name"])
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

    def close(self):
        from .gui_util import close_guard
        close_guard(self, TITLE, self._unwritten, self.write, after=self._forget)()

    def _forget(self):
        if getattr(self.app, "_interface_window", None) is self:
            self.app._interface_window = None


def open_interface(app):
    """One window: opened again it comes to the front."""
    if not app.mod:
        messagebox.showinfo(TITLE, "Load a mod first.")
        return None
    w = getattr(app, "_interface_window", None)
    if w is None or not w.winfo_exists() or w.mod is not app.mod:
        if w is not None and w.winfo_exists():
            w.destroy()
        w = app._interface_window = InterfaceWindow(app)
    w.lift()
    return w


__all__ = ["InterfaceWindow", "open_interface"]
