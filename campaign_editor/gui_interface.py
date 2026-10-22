"""Interface (a work of the main window, beside Module builder): the game's menu screens as the game lays them out - every page of
the menu layout file (Rome / Barbarian Invasion / Alexander Rome.lnt, Medieval II mtw2.lnt; lnt.py) drawn on the
1024 x 768 layout with its own pictures and words. A piece is picked with a click, moved by dragging, sized by its
corner, nudged with the arrows (Shift: 10 pixels); its right click holds the rest - place and size, the page it opens,
its words and tooltip, Copy, Rename, Remove (no side panel: the screen gets the room). Copy makes the next numbered piece (the game finds many by their numbers), Remove takes one
out; a double click on a button opens the page it leads to, as in the game. The main window's own buttons act on it as
on every work (the user, 2026-10-16, #296: no buttons of its own beside them): Undo / Redo step its changes, Preview
changes shows them, Apply changes writes the layout file (a backup first; Restore undoes it). The menu backdrop is the
game's video (Rome, Alexander, Medieval II), a picture only in Barbarian Invasion.

The idea and the first map of the format: Wholesome Queen's RTW Sprite & HUD Studio, given to make this editor
better for everyone (CREDITS)."""

import os
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import lnt as L
from . import theme
from .gui_util import Tip

TITLE = "Interface"
WORDS = "#ffdd77"                                    # the menus' gold words (RomeTW.exe: RGB 255, 221, 119)
HANDLE = 7                                   # the corner square that sizes a piece, in screen pixels
SHOWN = (("normal", None), ("mouse over", "highlighted"), ("pressed", "selected"), ("ticked", "checked"))
KINDS = {"UIP_MENU_BUTTON": "a button that opens a page", "UIP_BACK_BUTTON": "the back button",
         "UIP_STATIC_TEXT": "words", "UIP_EMPTY_ART": "a picture"}


class InterfacePanel(ttk.Frame):
    """A work of the main window (the user, 2026-10-15: not a window of its own), like the Module builder."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app, self.mod = app, None
        self._path, self.doc = None, None
        self.saved = b""
        self._sig, self.video = None, True
        self.words = {}
        self.undo, self.redo = [], []
        self.page, self.picked = None, None
        self.hover = None                    # the button under the mouse: drawn as the game shows it, 'mouse over'
        self.zoom, self.pan = 1.0, [0.0, 0.0]   # the wheel zooms (1 = the whole screen fits), the held wheel moves it
        self._panning, self._draw_due = None, False
        self._pics, self._tex, self._fonts = {}, {}, {}
        self._pil = {}                       # Pillow pictures at the layout's size: words, pieces the game draws
        self._gpu = None                     # the graphics card draws the page (glmenu): None = not asked yet
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
        self._path = L.find(mod) if mod else None
        self.doc = L.Lnt.load(self._path) if self._path else None
        self.saved = self.doc.dump() if self.doc else b""
        self._sig = self._signature()
        self.video = self._video_shown(mod)
        self.words = L.menu_texts(mod) if self.doc else {}
        self.undo, self.redo = [], []
        self.page, self.picked = None, None
        self._pics, self._tex, self._fonts, self._pil = {}, {}, {}, {}
        self.own_files = {}                             # own pictures made here {file: TGA bytes}, written by Apply
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
        """The mod loaded again: changes waiting here stay while their file is unchanged (another work written
        meanwhile); else its menus are read again and the changes go (said). After its own write it reads afresh."""
        if self.mod is None and self.sprites is not None:     # its own write (App._write): the pictures are in
            self.sprites.forget()
        if self.mod is not None and self.dirty() and self._path and mod.data == self.mod.data and \
                self._signature() == self._sig:
            self.mod = mod
            return 0
        lost = 1 if self.mod is not None and self.dirty() else 0
        self.load()
        if self.sprites is not None and self.nb.index(self.nb.select()) == 1:
            self.sprites.load()
        if self.hud is not None and self.nb.index(self.nb.select()) == 2:
            self.hud.load()
        return lost

    kind = "Interface"

    def dirty(self):
        """Changes wait for Apply changes (the main window's): the menu screens' or the sprite sheets' pictures."""
        return self._menus_dirty() or self._sprites_dirty()

    def _menus_dirty(self):
        return bool(self.doc) and self.doc.dump() != self.saved

    def _sprites_dirty(self):
        return self.sprites is not None and self.sprites.dirty()

    def pending(self):
        return ((max(1, len(self.undo)) if self._menus_dirty() else 0) +
                (self.sprites.pending() if self._sprites_dirty() else 0))

    def path(self):
        return self._path

    def _signature(self):
        """What the file is now (its bytes' md5): the changes wait on the lines as they were read."""
        import hashlib
        try:
            with open(self._path, "rb") as fh:
                return hashlib.md5(fh.read()).hexdigest()
        except (OSError, TypeError):
            return None

    def make_plan(self):
        if not self.doc and not self._sprites_dirty():
            raise ValueError("Interface: this game / mod has no menu layout file.")
        if not self.dirty():                # the tester, 2026-10-22: Apply with no change gave an empty backup + 'Done'
            raise ValueError("Nothing to write yet from Interface: no picture, sprite or box was changed (or it is "
                             "written already). Make the change - it is kept at once - then Apply changes writes it.")
        from .plan import Plan
        plan = Plan(self.mod, "interface", "interface", {})
        if self._sprites_dirty():
            self.sprites.plan_into(plan)
        if not self.doc:
            return plan
        L.plan_write(plan, self._path, self.doc)
        used = {os.path.normcase(self.own_path(t)) for t in self.doc.textures()}
        for path, data in self.own_files.items():          # the own pictures the layout names now
            if os.path.normcase(path) in used:
                plan.binary(path, data)
        folder = os.path.join(os.path.dirname(self._path), L.OWN_FOLDER)
        if os.path.isdir(folder):                           # own pictures written before and no longer named
            for n in os.listdir(folder):
                p = os.path.join(folder, n)
                if os.path.normcase(p) not in used and n.lower().endswith(".tga"):
                    plan.delete(p, "an own menu picture no piece shows any more")
        return plan

    def _on_sprites(self):
        return self.sprites is not None and self.nb.index(self.nb.select()) in (1, 2)    # the HUD works through it

    def undo_step(self):
        """The main window's Undo (and Ctrl+Z) on this work - on the tab on show."""
        if self._on_sprites():
            self._said(self.sprites.step(True), "Undone.", "Nothing to undo here.", None)
            return
        self._said(self.do_undo(), "Undone (%d more step(s) back).", "Nothing to undo here.", len(self.undo))

    def redo_step(self):
        if self._on_sprites():
            self._said(self.sprites.step(False), "Redone.", "Nothing to redo here.", None)
            return
        self._said(self.do_redo(), "Redone.", "Nothing to redo here.", None)

    def _said(self, done, yes, no, n):
        status = getattr(self.app, "status", None)
        if status is not None:
            status.set((yes % n if n is not None else yes) if done else no)

    def may_close(self):
        """The editor is closing: changes not written are never thrown away silently."""
        from .gui_util import ask_choice
        if not self.dirty():
            return True
        k = ask_choice(self, TITLE, "The menu screens have changes not written yet.\n\nKeep working (then Apply "
                                    "changes writes them), or throw them away?",
                       ["Keep working", "Throw them away"], default=0, cancel=0, danger=1)
        return k == 1

    # ---- the window ----
    def _build(self):
        # two tabs: the menu screens (the .lnt pages) and the sprite sheets the game takes its interface pictures from
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        screens = ttk.Frame(self.nb)
        self.nb.add(screens, text="Menu screens")
        self.sprites = None
        self._sprite_tab = ttk.Frame(self.nb)
        self.nb.add(self._sprite_tab, text="Sprite sheets")
        self.hud = None                                 # the campaign map's bottom panel (gui_hud), on its own tab
        self._hud_tab = ttk.Frame(self.nb)
        self.nb.add(self._hud_tab, text="Campaign HUD")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._tab_changed())
        # no title, hint line or bottom bar of its own (the user, 2026-10-16, #296: their room goes to the screen; the
        # main window's Preview changes / Apply changes / Undo / Redo act on this work): the help sits in a '?'
        help_text = (
            "Every screen of the game's menus as the game lays it out (1024 x 768); the wheel zooms, the held wheel moves "
            "it, Fit shows it whole. Click a piece to pick it, drag it "
            "to move it, drag its corner to size it, the arrows nudge it (Shift: 10 pixels). A double click on a "
            "button opens the page it leads to. A right click on a piece: its values, Copy, Rename, Remove. Copy makes the next numbered piece - the game finds many pieces by "
            "their numbers (more faction buttons: copy the last one). Pieces with no picture of their own (empty_...) "
            "are drawn by the game itself; here they show as frames with their words. A button under the mouse shows its "
            "'mouse over' picture as in the game; Buttons shown draws every button pressed, ticked...; a piece's right "
            "click > Pictures of its states sets the picture of each; Replace picture... gives a piece a picture of "
            "your own (a file, or one from the Picture library - the game's own pieces and your own pictures) and "
            "keeps what it does (the page it opens, its words); Back to the game's picture undoes it. The menu backdrop is the game's video "
            "(Rome, Alexander, Medieval II; a picture only in Barbarian Invasion) - shown as a dark screen with its "
            "file's name. Undo / Redo, Preview changes and Apply changes are the main window's (a backup first).")
        body = ttk.Panedwindow(screens, orient="horizontal")
        body.pack(fill="both", expand=True, padx=6, pady=(4, 2))
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
        c.bind("<Motion>", self._hover)
        # as on the map: the wheel zooms round the mouse, the held wheel (middle button) moves the screen
        c.bind("<MouseWheel>", lambda e: self._wheel(e, 1 if e.delta > 0 else -1))
        c.bind("<Button-4>", lambda e: self._wheel(e, 1))
        c.bind("<Button-5>", lambda e: self._wheel(e, -1))
        c.bind("<ButtonPress-2>", self._pan_start)
        c.bind("<B2-Motion>", self._pan_move)
        c.bind("<ButtonRelease-2>", lambda e: setattr(self, "_panning", None))
        c.bind("<Leave>", lambda e: self._set_hover(None))
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
        # every button drawn in one state, as the game shows it then (the one under the mouse: 'mouse over')
        ttk.Label(mb, text="Buttons shown").pack(side="left", padx=(theme.BUTTON_GAP * 2, 4))
        self.v_state = tk.StringVar(value=SHOWN[0][0])
        cb = ttk.Combobox(mb, textvariable=self.v_state, state="readonly", width=11, values=[w for w, _ in SHOWN])
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.draw())
        q = ttk.Label(mb, text=" ? ", foreground="#2050c0", cursor="question_arrow", font=("", 9, "bold"))
        q.pack(side="right")
        Tip(q, lambda: help_text, width=560)
        ttk.Button(mb, text="Fit", command=self.fit).pack(side="right", padx=(0, theme.BUTTON_GAP))
        self.lbl_way = ttk.Label(mb, foreground=theme.palette()["muted"])
        self.lbl_way.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        # the piece picked, in one line under the screen; everything done to it is on its right click (the user,
        # 2026-10-15: no side panel - the buttons and values in the context menu, the screen gets the room)
        line = ttk.Frame(mid)
        line.pack(fill="x", pady=(2, 0))
        self.lbl_status = ttk.Label(line, foreground=theme.palette()["muted"])     # the file, the page, its pieces
        self.lbl_status.pack(side="right")
        self.lbl_info = ttk.Label(line, foreground=theme.palette()["muted"])
        self.lbl_info.pack(side="left", fill="x", expand=True)
        c.bind("<Button-3>", self._menu)
        self.tv.bind("<Button-3>", self._tree_menu)

    def _tab_changed(self):
        """Sprite sheets / the campaign HUD read when their tab is first opened (and again for another mod)."""
        tab = self.nb.index(self.nb.select())
        if tab == 1:
            self.ensure_sprites()
        elif tab == 2:
            if self.hud is None:
                from .gui_hud import HudPanel
                self.hud = HudPanel(self._hud_tab, self.app, self)
                self.hud.pack(fill="both", expand=True)
            self.hud.load()

    def ensure_sprites(self):
        """The Sprite sheets tab's panel, made and read for the mod loaded now (the HUD tab works through it: one
        place for the pictures' changes)."""
        if self.sprites is None:
            from .gui_sprites import SpriteSheetsPanel
            self.sprites = SpriteSheetsPanel(self._sprite_tab, self.app)
            self.sprites.pack(fill="both", expand=True)
        self.sprites.load()
        return self.sprites

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
        if x["object"] in self.doc.objects():
            m.add_command(label="Pictures of its states (normal, mouse over, pressed)...", command=self.ask_states)
        from . import gui_interface_own as OWN
        m.add_command(label="Replace picture... (what it does stays)", command=lambda: OWN.ask_picture(self))
        if self.doc.game_object(x["object"]) is not None:
            m.add_command(label="Back to the game's picture", command=lambda: OWN.back_to_game(self))
        m.add_command(label="Picture library...", command=lambda: OWN.Library(self))
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

    def ask_states(self):
        """The picture of each state of the picked piece's UI object (normal, mouse over, pressed, ticked): a texture
        and a region of it; a state added, one taken out. Every piece drawn with the object changes with it."""
        x = self.current()
        obj = x and x["object"]
        o = self.doc.objects().get(obj) if obj else None
        if o is None:
            return
        old = getattr(self, "_states_win", None)
        if old is not None and old.winfo_exists():
            old.destroy()                                   # one at a time: the newest piece picked
        d = self._states_win = tk.Toplevel(self)
        d.title("%s - pictures of its states" % obj)
        d.transient(self.winfo_toplevel())
        f = ttk.Frame(d, padding=10)
        f.pack(fill="both", expand=True)
        users = self.doc.users(obj)
        ttk.Label(f, foreground=theme.palette()["muted"], wraplength=520, justify="left", text=(
            "UI object %s (%s) - %d piece(s) are drawn with it%s; a change shows on all of them." % (
                obj, o["type"] or "?", len(users), (": " + ", ".join(n for _, n in users[:4]) +
                                                    (" ..." if len(users) > 4 else "")) if users else ""))).grid(
            row=0, column=0, columnspan=5, sticky="w", pady=(0, 6))
        textures = self.doc.textures()
        rows = {}

        def regions_of(page):
            return sorted(textures.get(page, {}).get("regions", {}))

        def add_row(state, page, region):
            r = len(rows) + 1
            ttk.Label(f, text="%s (%s)" % (L.STATES.get(state, state), state)).grid(row=r, column=0, sticky="w")
            vp, vr = tk.StringVar(value=page), tk.StringVar(value=region)
            cp = ttk.Combobox(f, textvariable=vp, values=sorted(textures), width=30, state="readonly")
            cp.grid(row=r, column=1, padx=4, pady=2)
            cr = ttk.Combobox(f, textvariable=vr, values=regions_of(page), width=26, state="readonly")
            cr.grid(row=r, column=2, padx=4, pady=2)
            cp.bind("<<ComboboxSelected>>", lambda e: cr.configure(values=regions_of(vp.get())))
            out = ttk.Button(f, text="Take out", command=lambda: take_out(state))
            out.grid(row=r, column=3, padx=(4, 0))
            rows[state] = (vp, vr, [cp, cr, out], f.grid_slaves(row=r, column=0))

        def take_out(state):
            if len([k for k, v in rows.items() if v is not None]) < 2:
                messagebox.showinfo(TITLE, "The object's only picture stays.", parent=d)
                return
            for w in rows[state][2] + rows[state][3]:
                w.destroy()
            rows[state] = None

        for state, (page, region) in o["regions"].items():
            add_row(state, page, region)
        foot = ttk.Frame(f)
        foot.grid(row=99, column=0, columnspan=5, sticky="we", pady=(8, 0))
        free = [st for st in L.STATES if st not in o["regions"]]
        v_new = tk.StringVar(value=free[0] if free else "")
        if free:
            ttk.Combobox(foot, textvariable=v_new, values=free, width=12, state="readonly").pack(side="left")

            def add():
                st = v_new.get()
                if st and rows.get(st) is None:
                    first = next((v for v in rows.values() if v is not None), None)
                    add_row(st, first[0].get() if first else "", first[1].get() if first else "")
            ttk.Button(foot, text="Add this state", command=add).pack(side="left", padx=(4, 0))

        def ok(*_):
            want = {k: (v[0].get(), v[1].get()) for k, v in rows.items() if v is not None}
            gone = [k for k in o["regions"] if k not in want]
            changed = gone or any(o["regions"].get(k) != pr for k, pr in want.items())
            d.destroy()
            if not changed:
                return
            self._remember()
            try:
                for k, (page, region) in want.items():
                    if o["regions"].get(k) != (page, region):
                        self.doc.set_state(obj, k, page, region)
                for k in gone:
                    self.doc.remove_state(obj, k)
            except L.LntError as e:
                self._restore(self.undo.pop())
                messagebox.showerror(TITLE, str(e), parent=self)
                return
            self._pics.clear()
            self.fill_form()
            self.draw()
        ttk.Button(foot, text="Cancel", command=d.destroy).pack(side="right")
        ttk.Button(foot, text="OK", command=ok).pack(side="right", padx=(0, theme.BUTTON_GAP))
        d.bind("<Escape>", lambda e: d.destroy())
        return d

    # ---- drawing ----
    def _scale(self):
        w, h = self.doc.size()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        s = min(cw / w, ch / h) * self.zoom
        return s, (cw - w * s) / 2 + self.pan[0], (ch - h * s) / 2 + self.pan[1]

    def _wheel(self, e, d):
        """The wheel zooms round the point under the mouse (as on the map)."""
        if not self.doc or not self.page:
            return
        s, ox, oy = self._scale()
        lx, ly = (e.x - ox) / s, (e.y - oy) / s              # the layout point under the mouse stays under it
        self.zoom = max(0.25, min(8.0, self.zoom * (1.2 if d > 0 else 1 / 1.2)))
        s2, ox2, oy2 = self._scale()
        self.pan[0] += e.x - (ox2 + lx * s2)
        self.pan[1] += e.y - (oy2 + ly * s2)
        self.draw()

    def _pan_start(self, e):
        self._panning = (e.x, e.y, list(self.pan))

    def _pan_move(self, e):
        if self._panning:
            x0, y0, pan = self._panning
            self.pan = [pan[0] + e.x - x0, pan[1] + e.y - y0]
            self.draw()

    def fit(self):
        """The whole screen in the window again."""
        self.zoom, self.pan = 1.0, [0.0, 0.0]
        self.draw()

    def own_path(self, rel):
        """The file of a picture named under data/menu/ as the layout file names it, beside the layout file."""
        return os.path.join(os.path.dirname(self._path), *rel.replace("/", "\\").split("\\"))

    def _texture(self, page, folder=""):
        if page not in self._tex:
            self._tex[page] = None
            mine = self.own_files.get(self.own_path(page)) if self._path else None
            if mine is not None:                        # an own picture not written yet
                try:
                    import io
                    from PIL import Image
                    self._tex[page] = Image.open(io.BytesIO(mine)).convert("RGBA")
                except Exception:
                    pass
                return self._tex[page]
            p = L.texture_file(self.mod, self._path, page, folder)
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
            p = L.texture_file(self.mod, self._path, name)
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
        col = self._words_pil(words, font_id, box_w / s, colour, shadow)
        if col is None:
            return None
        try:
            from PIL import Image, ImageTk
            W, H = col.size
            col = col.resize((max(1, int(W * s)), max(1, int(H * s))), Image.LANCZOS)
            self._pics[key] = ImageTk.PhotoImage(col)
        except Exception:
            self._pics[key] = None
        return self._pics[key]

    def _words_pil(self, words, font_id, box_w, colour=(232, 220, 176), shadow=False):
        """The words as an RGBA picture at the layout's own size (box_w: the piece's width there), cached; None
        without Pillow / a font."""
        key = ("words", words, font_id, int(box_w), colour, shadow)
        if key in self._pil:
            return self._pil[key]
        self._pil[key] = None
        f = self._font(font_id)
        if f is None:
            return None
        try:
            from PIL import Image, ImageDraw
            from . import cuf

            def line_img(text):
                if f[0] == "cuf":
                    return cuf.to_image(f[1], text)
                l, t, r, b = f[1].getbbox(text or " ")
                im = Image.new("L", (max(1, r), max(1, b)), 0)
                ImageDraw.Draw(im).text((0, 0), text, font=f[1], fill=255)
                return im
            limit = max(8, box_w - 4)
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
            self._pil[key] = col
        except Exception:
            self._pil[key] = None
        return self._pil[key]

    def _state(self, x):
        """The state a piece is drawn in: 'mouse over' under the mouse, else the one picked under the screen."""
        if x["index"] == self.hover:
            return "highlighted"
        return dict(SHOWN).get(self.v_state.get())

    def _picture(self, x, s, state=None):
        art = self.doc.art(x, state)
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
        """Drawn once the mouse and the keys are quiet (a drag sends many moves a frame: each used to draw the whole
        screen again - it lagged)."""
        if not self._draw_due:
            self._draw_due = True
            self.after_idle(self._draw_now)

    def _draw_now(self):
        self._draw_due = False
        if len(self._pics) > 3000:                     # sizes seen while zooming / sizing: drop the old ones
            self._pics.clear()
        c = self.canvas
        c.delete("all")
        if not self.doc or not self.page:
            return
        if self._gpu is None:                           # the card's picture is shown through Pillow: both needed
            try:
                from PIL import ImageTk  # noqa: F401
                from . import glmenu
                self._gpu = glmenu.available()
            except Exception:
                self._gpu = False
        if self._gpu:
            try:
                self._draw_gpu()
                self._status()
                return
            except Exception:                           # the card failed: the drawing below, never a crash
                self._gpu = False
                c.delete("all")
        s, ox, oy = self._scale()
        lw, lh = self.doc.size()
        c.create_rectangle(ox, oy, ox + lw * s, oy + lh * s, fill="#101010", outline="#606060")
        pal_sel = "#ffd400"
        # the game draws its 'background' page (the backdrop) under every menu page
        if self.v_back.get() and self.page != "background" and "background" in self.doc.pages():
            back = self.doc.pieces("background")
            films = [i for i, x in enumerate(back) if self._film(x)]
            for x in back[films[-1]:] if films else back:     # what lies under the video is never seen
                if self._film(x):
                    self._draw_film(x)
                    continue
                pic = self._picture(x, s)
                if pic is not None:
                    x0, y0, _, _ = self._rect(x)
                    c.create_image(x0, y0, image=pic, anchor="nw")
        from . import menudraw as MD
        for x in self.doc.pieces(self.page):
            x0, y0, x1, y1 = self._rect(x)
            if self.v_back.get() and self._film(x):
                self._draw_film(x)
            state = self._state(x)
            pic = self._picture(x, s, state) if self.v_back.get() else None
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
                colour, shadow = MD.text_colour(k)
                if state in ("highlighted", "selected") and k in ("art", "button"):
                    colour = (255, 255, 255)              # the game's words on a button under the mouse / pressed
                img = self._words_image(words, x["font"], s, x1 - x0, colour, shadow)
                if img is not None:                         # in the game's own letters
                    c.create_image(tx, (y0 + y1) / 2, image=img, anchor=anchor)
                else:
                    c.create_text(tx, (y0 + y1) / 2, text=words, fill=WORDS, anchor=anchor,
                                  width=max(10, x1 - x0 - 4), font=("", max(7, int(10 * s))))
            if x["index"] == self.picked:
                c.create_rectangle(x0, y0, x1, y1, outline=pal_sel, width=2)
                c.create_rectangle(x1 - HANDLE, y1 - HANDLE, x1, y1, fill=pal_sel, outline="")
        self._status()

    def _status(self):
        arts = [self.doc.art(x) for x in self.doc.pieces(self.page)]
        unseen = [a for a in arts if a and self._texture(a[0], a[2]) is None]
        self.lbl_status.configure(text="%s - page %s - %d pieces%s" % (
            self.mod.rel(self._path), self.page, len(self.doc.pieces(self.page)), ("  - %d picture(s) not found as files (Medieval II keeps them in its .pack files until the game "
                      "is unpacked): shown as frames" % len(unseen)) if unseen else ""))

    def _drawn_pil(self, k, w, h):
        """(RGBA picture, offset) of a piece the game draws itself at the layout's size (w, h), cached."""
        key = ("drawn", k, int(w), int(h))
        if key not in self._pil:
            self._pil[key] = (None, 0)
            try:
                from . import menudraw as MD
                self._pil[key] = MD.piece_image(self._part, k, w, h)
            except Exception:
                pass
        return self._pil[key]

    def _draw_gpu(self):
        """The page drawn by the graphics card as one picture (glmenu): the sheets go onto the card once, each piece
        is a square cut out of its sheet - nothing is resized again while a piece is dragged or the page zoomed. The
        frames, the picked piece and the video's words are drawn over it on the canvas."""
        from PIL import Image, ImageTk
        from . import glmenu as G
        from . import menudraw as MD
        c = self.canvas
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        s, ox, oy = self._scale()
        lw, lh = self.doc.size()
        ops = [(None, G.quad(ox, oy, ox + lw * s, oy + lh * s, rgba=(16 / 255, 16 / 255, 16 / 255, 1.0)))]
        over = []                                       # canvas items over the picture: (kind, what)

        def film(x):
            x0, y0, x1, y1 = self._rect(x)
            ops.append((None, G.quad(x0, y0, x1, y1, rgba=(12 / 255, 12 / 255, 20 / 255, 1.0))))
            over.append(("film", x))

        def art(x, state=None):
            a = self.doc.art(x, state)
            if not a:
                return False
            page, box, folder = a
            tex = self._texture(page, folder)
            if tex is None:
                return False
            x0, y0, _, _ = self._rect(x)
            w = (x["width"] or box[2] - box[0]) * s
            h = (x["height"] or box[3] - box[1]) * s
            ops.append((tex, G.picture_quad(tex, box, (x0, y0, x0 + w, y0 + h))))
            return True
        # the game draws its 'background' page (the backdrop) under every menu page
        if self.v_back.get() and self.page != "background" and "background" in self.doc.pages():
            back = self.doc.pieces("background")
            films = [i for i, x in enumerate(back) if self._film(x)]
            for x in back[films[-1]:] if films else back:     # what lies under the video is never seen
                if self._film(x):
                    film(x)
                else:
                    art(x)
        for x in self.doc.pieces(self.page):
            x0, y0, x1, y1 = self._rect(x)
            if self.v_back.get() and self._film(x):
                film(x)
            state = self._state(x)
            k = MD.kind(x["identifier"], x["object"], self.doc.art(x) is not None)
            if not (self.v_back.get() and art(x, state)):
                img, off = self._drawn_pil(k, (x1 - x0) / s, (y1 - y0) / s) if self.v_back.get() else (None, 0)
                if img is not None:                     # what the game draws itself, from its own parts
                    left, top = x0 - off * s, y0 - off * s
                    ops.append((img, G.quad(left, top, left + img.width * s, top + img.height * s)))
                if self.v_frames.get() or x["index"] == self.picked:
                    over.append(("frame", (x0, y0, x1, y1)))
            words = self.words.get((x["text"] or "").upper())
            if words:
                anchor = {"left": "w", "right": "e"}.get(x["align"] or "", "center")
                tx = {"w": x0 + 3, "e": x1 - 3}.get(anchor, (x0 + x1) / 2)
                colour, shadow = MD.text_colour(k)
                if state in ("highlighted", "selected") and k in ("art", "button"):
                    colour = (255, 255, 255)              # the game's words on a button under the mouse / pressed
                img = self._words_pil(words, x["font"], (x1 - x0) / s, colour, shadow)
                if img is not None:                     # in the game's own letters
                    w, h = img.width * s, img.height * s
                    left = {"w": tx, "e": tx - w}.get(anchor, tx - w / 2)
                    top = (y0 + y1) / 2 - h / 2
                    ops.append((img, G.quad(left, top, left + w, top + h)))
                else:
                    over.append(("words", (tx, (y0 + y1) / 2, words, anchor, max(10, x1 - x0 - 4), s)))
            if x["index"] == self.picked:
                over.append(("picked", (x0, y0, x1, y1)))
        arr = G.draw(cw, ch, (0x20, 0x20, 0x20), ops)
        self._photo = ImageTk.PhotoImage(Image.fromarray(arr))
        c.create_image(0, 0, image=self._photo, anchor="nw")
        c.create_rectangle(ox, oy, ox + lw * s, oy + lh * s, outline="#606060")
        for kind, a in over:
            if kind == "film":
                fx0, _, _, fy1 = self._rect(a)
                c.create_text(fx0 + 8, fy1 - 8, anchor="sw", fill="#8a8fa0", font=("", 9),
                              text="▶ the game's video plays here: %s" % self._film(a))
            elif kind == "frame":
                c.create_rectangle(*a, outline="#5a7fa8")
            elif kind == "words":
                tx, ty, words, anchor, width, sc = a
                c.create_text(tx, ty, text=words, fill=WORDS, anchor=anchor, width=width,
                              font=("", max(7, int(10 * sc))))
            else:
                x0, y0, x1, y1 = a
                c.create_rectangle(x0, y0, x1, y1, outline="#ffd400", width=2)
                c.create_rectangle(x1 - HANDLE, y1 - HANDLE, x1, y1, fill="#ffd400", outline="")

    # ---- the mouse and the keys ----
    def _film(self, x):
        """The video the game plays in this piece (its <fmv> file), or None - none in Barbarian Invasion (the user,
        2026-10-16: the menu backdrop is a video in both games, Barbarian Invasion shows its picture)."""
        return self.doc.videos().get(x["object"] or "") if self.video else None

    def _draw_film(self, x):
        x0, y0, x1, y1 = self._rect(x)
        c = self.canvas
        c.create_rectangle(x0, y0, x1, y1, fill="#0c0c14", outline="")
        c.create_text(x0 + 8, y1 - 8, anchor="sw", fill="#8a8fa0", font=("", 9),
                      text="\u25b6 the game's video plays here: %s" % self._film(x))

    @staticmethod
    def _video_shown(mod):
        """Whether the game plays the menu video: Rome, Alexander, Medieval II; not Barbarian Invasion."""
        if mod is None:
            return True
        from .emergence import is_bi
        try:
            return not is_bi(mod)
        except Exception:
            return True

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

    def _hover(self, e):
        """The button under the mouse is drawn as the game shows it then (its 'mouse over' picture, white words)."""
        if not self.doc or not self.page or self._drag:
            return
        name, _ = self._hit(e)
        x = self.doc.piece(self.page, name) if name is not None else None
        self._set_hover(name if x is not None and self._is_button(x) else None)

    def _is_button(self, x):
        """A piece that answers the mouse: a push / toggle button by its UI object (empty_push_button - the Quit and
        Continue buttons are UIP_QUIT_DIALOG / UIP_MAIN_CONTINUE, no 'BUTTON' in the name), or a picture with a
        'mouse over' state."""
        obj = (x["object"] or "").lower()
        o = self.doc.objects().get(x["object"] or "", {})
        return obj in ("empty_push_button", "empty_toggle_button") or o.get("type") in ("push_button",
                                                                                           "toggle_button") or \
            "BUTTON" in (x["identifier"] or "").upper() or "highlighted" in o.get("regions", {})

    def _set_hover(self, name):
        if name != self.hover:
            self.hover = name
            self.draw()

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
        self.after_idle(self._marked)

    def _marked(self):
        """The work button's * and Apply changes' words follow the changes waiting here."""
        for name in ("_mark_work", "update_actions"):
            f = getattr(self.app, name, None)
            if f is not None:
                f()

    def _restore(self, state):
        lines, page, picked = state
        self.doc.lines = list(lines)
        self.doc.parse()
        self.fill_pages()
        self.show_page(page if page in self.doc.pages() else self.doc.pages()[0], picked)

    def do_undo(self):
        if not self.undo:
            return False
        self.redo.append((list(self.doc.lines), self.page, self.picked))
        self._restore(self.undo.pop())
        self._marked()
        return True

    def do_redo(self):
        if not self.redo:
            return False
        self.undo.append((list(self.doc.lines), self.page, self.picked))
        self._restore(self.redo.pop())
        self._marked()
        return True

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
        self.lbl_status.configure(text="%d slot(s) added on %s - their grid continued; Apply changes writes them"
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

    # ---- writing: the main window's Preview changes / Apply changes (make_plan) ----
    def _unwritten(self):
        return self.dirty()


def open_interface(app):
    """The Interface work shown in the main window (the work bar's 'Interface')."""
    app.v_work.set("interface")
    app.work_changed()
    return app.editors["interface"]


__all__ = ["InterfacePanel", "open_interface"]
