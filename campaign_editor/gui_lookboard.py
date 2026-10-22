"""The layout board: every page of the editor laid out side by side on one canvas, its buttons moved and sized there
(the user, 2026-10-22: 'a window where my editor lies on a canvas, every page and window already laid out, so I need
not click to each one; buttons dragged, sized, a right click for the rest').

Tools > Layout board opens it. The first time (and on Refresh) the editor shows each page in turn - every work of
the main window, the tabs of Maps and of Edit / New faction, the windows of Tools - takes its picture and where
each piece of it stands (gui_look's keys), and keeps both (look.board_dir: pages.json + a PNG each), so the board
opens laid out the next time. On the board:
- the wheel zooms round the mouse, the middle button (or the left one on the empty board) moves it;
- a click picks a piece (yellow frame); dragged with the left button it goes exactly where it is dropped (the
  user, 2026-10-22: 'fully free, not rows - a grid to turn on, and it sticks to the line another piece stands on,
  as in Obsidian'): its edges and middle stick to the other pieces' edges and middles and to the window's (pink
  guide lines), and with Grid ticked to the grid; with Alt (or 'In a row' ticked) it goes before / after the
  piece nearest to where it is dropped, in a row; its corners size it (sticking the same way); the arrows nudge it;
- its right click: rename, hover text, size, width in letters, hide, back into its row, back to how it was, show it
  in the editor; a page's: refresh it, show it in the editor, its pieces back to how they were.
The board is a DRAFT (his word: 'you lay it out, press Accept, and it rebuilds the buttons that way'): each change
is drawn on the board at once (the piece's picture where it goes, its old place greyed), Undo / Redo step through
the draft, and Accept puts them all on the editor (gui_look's look: CampaignEditor_look.json, Undo / Redo and Back
to how it was there too); Discard drops them. The page's picture is taken again after Accept, so the board shows the
editor as it is.
Not on it: the questions and file pickers Windows draws itself (not the editor's windows)."""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import board as B
from . import look as LK
from .gui_look import PIECES, YELLOW, all_widgets, ask_style, can_move

TITLE = "Layout board"
# the windows of Tools laid out with the works: (App method, title on the board)
WINDOWS = (("settings_window", "Settings"), ("show_help", "Help"), ("mod_zero_window", "A mod from zero"),
           ("game_log_window", "The game's log in plain words"), ("show_log", "Log"),
           ("credits_window", "Credits"))          # (Game manifest asks for a folder first: not gathered)
TAB_WORKS = ("map", "edit", "new")             # works whose tabs are pages of their own
SKIP_TABS = ("3D",)                            # starts the graphics card's map: shown when opened, not gathered
WAIT_WORK, WAIT_TAB, WAIT_WINDOW = 350, 220, 450   # ms a page is given to draw itself before its picture
HANDLE = 5                                     # px (on the screen) of a corner handle
ZOOMS = (0.08, 0.1, 0.125, 0.16, 0.2, 0.25, 0.32, 0.4, 0.5, 0.63, 0.8, 1.0, 1.25, 1.6, 2.0)
CHANGED = "#ff8a00"                            # the dot on a piece the look changed
HELP = ("Every page of the editor side by side. The wheel zooms, the middle button (or the left one on the empty "
        "board) moves the board. Click a button, tick or label to pick it; drag it with the left button and it "
        "stays exactly where you drop it: its edges stick to the lines the other pieces stand on (pink lines), "
        "and to the grid when Grid is ticked. Hold Alt (or tick In a row) to put it into the row beside the piece "
        "nearest to where you drop it. Drag its corners to size it; the arrows move it a pixel (Shift: 10). Right "
        "click a piece or a page for the rest: rename, hover text, size, hide, back to how it was, show it in the "
        "editor. Your changes are a draft drawn on the board: Accept puts them all on the editor (kept for every "
        "start in CampaignEditor_look.json), Discard drops them, Undo / Redo step through them. Refresh takes the "
        "pages' pictures again (after you loaded a mod, for example). The questions and file pickers Windows "
        "draws itself are not on the board.")
GUIDE = "#ff3fa4"                              # the pink guide line: a piece stands on another's line
GRID_INK = "#8fb4ff"                           # the grid's lines over a page
GRID_STEPS = ("4", "8", "16", "32")            # px of the editor's window between two grid lines


def _alt(e):
    return bool(e.state & (0x20000 if sys.platform == "win32" else 0x0008))


def _words(key):
    """A piece's own words from its key ('window|boxes|class:words#n')."""
    return key.split("|")[-1].partition(":")[2] or key


class _quiet:
    """While a Tools window is opened for its picture, the questions it would ask first are answered 'not now'
    (nothing picked, nothing written) instead of stopping the board."""
    NAMES = ((messagebox, ("askyesno", "askokcancel", "askyesnocancel", "showinfo", "showwarning", "showerror")),
             (filedialog, ("askopenfilename", "askopenfilenames", "asksaveasfilename", "askdirectory")))

    def __enter__(self):
        from . import gui, gui_util
        self.kept = []
        for mod, names in self.NAMES + ((gui_util, ("ask", "ask_choice")), (gui, ("ask", "ask_choice"))):
            for n in names:
                if hasattr(mod, n):
                    self.kept.append((mod, n, getattr(mod, n)))
                    setattr(mod, n, lambda *a, **k: None)
        return self

    def __exit__(self, *exc):
        for mod, n, f in self.kept:
            setattr(mod, n, f)
        return False


def _pil():
    try:
        from PIL import Image, ImageTk
        return Image, ImageTk
    except Exception:
        return None, None


# ---- a page's picture ----
def snap(top):
    """A picture (PIL) of what the window top shows now, or None (no Pillow, nothing on the screen). On Windows the
    window's own drawing (PrintWindow: right even under another window), else the screen where it stands."""
    Image, _ = _pil()
    if Image is None:
        return None
    try:
        top.update_idletasks()
        x, y, w, h = top.winfo_rootx(), top.winfo_rooty(), top.winfo_width(), top.winfo_height()
    except tk.TclError:
        return None
    if w < 2 or h < 2:
        return None
    if sys.platform == "win32":
        got = _print_window(top, x, y, w, h)
        if got is not None:
            return got
    try:
        top.lift()
        top.update()
        from PIL import ImageGrab
        got = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        return got.convert("RGB") if got.size == (w, h) else got.convert("RGB").resize((w, h))
    except Exception:
        return None


def _print_window(top, x, y, w, h):
    """Windows: the window drawn into a picture by itself (PrintWindow, PW_RENDERFULLCONTENT), its inside cut out."""
    try:
        import ctypes
        from ctypes import wintypes
        from PIL import Image
        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        vp = ctypes.c_void_p
        u.GetParent.restype, u.GetParent.argtypes = vp, [vp]
        u.GetDC.restype, u.GetDC.argtypes = vp, [vp]
        u.ReleaseDC.argtypes = [vp, vp]
        u.PrintWindow.argtypes = [vp, vp, ctypes.c_uint]
        u.GetWindowRect.argtypes = [vp, ctypes.POINTER(wintypes.RECT)]
        g.CreateCompatibleDC.restype, g.CreateCompatibleDC.argtypes = vp, [vp]
        g.CreateCompatibleBitmap.restype, g.CreateCompatibleBitmap.argtypes = vp, [vp, ctypes.c_int, ctypes.c_int]
        g.SelectObject.restype, g.SelectObject.argtypes = vp, [vp, vp]
        g.DeleteObject.argtypes = g.DeleteDC.argtypes = [vp]
        g.GetDIBits.argtypes = [vp, vp, ctypes.c_uint, ctypes.c_uint, vp, vp, ctypes.c_uint]
        hwnd = u.GetParent(int(top.winfo_id())) or int(top.winfo_id())     # Tk's frame round the window
        rect = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(rect))
        fw, fh = rect.right - rect.left, rect.bottom - rect.top
        if fw < w or fh < h:
            return None
        dc = u.GetDC(hwnd)
        mem = g.CreateCompatibleDC(dc)
        bmp = g.CreateCompatibleBitmap(dc, fw, fh)
        old = g.SelectObject(mem, bmp)
        ok = u.PrintWindow(hwnd, mem, 2)

        class Head(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("w", ctypes.c_long), ("h", ctypes.c_long),
                        ("planes", wintypes.WORD), ("bits", wintypes.WORD), ("comp", wintypes.DWORD),
                        ("image", wintypes.DWORD), ("xm", ctypes.c_long), ("ym", ctypes.c_long),
                        ("used", wintypes.DWORD), ("important", wintypes.DWORD)]
        head = Head(ctypes.sizeof(Head), fw, -fh, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(fw * fh * 4)
        g.GetDIBits(mem, bmp, 0, fh, buf, ctypes.byref(head), 0)
        g.SelectObject(mem, old)
        g.DeleteObject(bmp)
        g.DeleteDC(mem)
        u.ReleaseDC(hwnd, dc)
        if not ok:
            return None
        whole = Image.frombuffer("RGB", (fw, fh), buf, "raw", "BGRX", 0, 1)
        ox, oy = x - rect.left, y - rect.top
        got = whole.crop((ox, oy, ox + w, oy + h))
        if all(lo == hi for lo, hi in got.getextrema()):      # drawn nothing (an old Windows, a hidden window)
            return None
        return got
    except Exception:
        return None


def pieces_of(look, top):
    """The pieces the window top shows now: [{'key', 'cls', 'text', 'box', 'boxes'}] (boxes in the window's own
    pixels: its box, then the boxes round it from its own up to the window - where a free piece may go), and the
    keys of its pieces the look hides."""
    try:
        tx, ty, tw, th = top.winfo_rootx(), top.winfo_rooty(), top.winfo_width(), top.winfo_height()
    except tk.TclError:
        return [], []
    out, hidden = [], []
    for key, w in list(look.by_key.items()):
        try:
            if not w.winfo_exists() or w.winfo_toplevel() is not top or w.winfo_class() not in PIECES:
                continue
            shown = look.clones.get(str(w), w)
            e = look.data["pieces"].get(key, {})
            if e.get("hidden"):
                if w.master.winfo_viewable():
                    hidden.append(key)
                continue
            if not shown.winfo_exists() or not shown.winfo_viewable():
                continue
            box = [shown.winfo_rootx() - tx, shown.winfo_rooty() - ty, shown.winfo_width(), shown.winfo_height()]
            if box[2] < 2 or box[3] < 2 or box[0] >= tw or box[1] >= th or box[0] + box[2] <= 0 or \
                    box[1] + box[3] <= 0:
                continue
            boxes, m = [], w.master
            while m is not None:
                boxes.append([m.winfo_rootx() - tx, m.winfo_rooty() - ty, m.winfo_width(), m.winfo_height()])
                if m is top:
                    break
                m = m.master
            out.append({"key": key, "cls": w.winfo_class(), "text": getattr(w, "_look_text", "") or "",
                        "box": box, "boxes": boxes})
        except (tk.TclError, AttributeError):
            continue
    return out, hidden


class LayoutBoard(tk.Toplevel):
    """The board window (one per editor: App.layout_board brings it to the front)."""

    def __init__(self, app):
        super().__init__(app)
        self.app, self.look = app, app.look
        self._look_skip = True
        self.title(TITLE)
        self.geometry("1200x800+%d+%d" % (app.winfo_rootx() + 40, app.winfo_rooty() + 40))
        self.pages = LK.load_board()
        self.pictures = {}                     # page id -> PIL picture
        self._shown = {}                       # page id -> (zoom, PhotoImage)
        self.zoom = 0.2
        self.picked = None                     # (page id, piece) or (page id, None) for a page
        self._drag = self._busy = self._job = None
        self._dirty = set()
        self.v_row = tk.BooleanVar(self, value=False)     # Alt does the same: into a row, not where dropped
        self.v_snap = tk.BooleanVar(self, value=True)     # stick to the other pieces' lines
        self.v_grid = tk.BooleanVar(self, value=False)
        self.v_step = tk.StringVar(self, value="8")
        self.v_frames = tk.BooleanVar(self, value=True)
        self.draft = {}                        # piece key -> its change waiting for Accept (None: that part out)
        self.draft_at = {}                     # piece key -> (page id, piece) the change was made on
        self.accepted = {}                     # the same, accepted: drawn until its page's picture is taken again
        self.draft_undo, self.draft_redo = [], []
        self._draft_photos = []
        self._build()
        self._read_pictures()
        for w in all_widgets(self):
            w._look_skip = True
        self.look.on_change.append(self._changed)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self._cancel_drag())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Delete>", lambda e: self._hide_picked())
        for k, d in (("Left", (-1, 0)), ("Right", (1, 0)), ("Up", (0, -1)), ("Down", (0, 1))):
            self.bind("<%s>" % k, lambda e, d=d: self._nudge(*d, big=bool(e.state & 1)))
        if self.pages:
            self.after(50, self.fit)
        else:
            self.after(150, self.refresh)

    # ---- the window ----
    def _build(self):
        bar = ttk.Frame(self, padding=(6, 4))
        bar.pack(fill="x")
        for text, cmd in (("Refresh all pages", self.refresh), ("Undo", self.undo), ("Redo", self.redo),
                          ("Fit", self.fit)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=(0, 4))
        self.b_accept = ttk.Button(bar, text="Accept", command=self.accept, state="disabled", style="Play.TButton")
        self.b_accept.pack(side="left", padx=(4, 4))
        self.b_discard = ttk.Button(bar, text="Discard", command=self.discard, state="disabled")
        self.b_discard.pack(side="left", padx=(0, 4))
        ttk.Checkbutton(bar, text="Stick to lines", variable=self.v_snap).pack(side="left", padx=(8, 4))
        ttk.Checkbutton(bar, text="Grid", variable=self.v_grid, command=self._marks).pack(side="left")
        step = ttk.Combobox(bar, textvariable=self.v_step, values=GRID_STEPS, width=3, state="readonly")
        step.pack(side="left", padx=(2, 4))
        step.bind("<<ComboboxSelected>>", lambda e: self._marks())
        ttk.Checkbutton(bar, text="In a row (or hold Alt)", variable=self.v_row).pack(side="left", padx=(4, 4))
        ttk.Checkbutton(bar, text="Frames round the pieces", variable=self.v_frames,
                        command=self.draw).pack(side="left", padx=(0, 8))
        for text, cmd in (("Done", self.close), ("Edit in the windows instead", self._in_windows),
                          ("Load a look...", self.load_from), ("Save my look...", self.save_as),
                          ("Back to how it was...", self.back_all)):
            ttk.Button(bar, text=text, command=cmd).pack(side="right", padx=(4, 0))
        from .gui_util import ShortHint
        ShortHint(self, text=HELP).pack(fill="x", padx=8)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        from . import theme
        self.ground = "#25272b" if theme.dark() else "#c9ccd2"
        self.cv = tk.Canvas(body, background=self.ground, highlightthickness=0, cursor="arrow")
        theme.leave_alone(self.cv)
        ys = ttk.Scrollbar(body, orient="vertical", command=self.cv.yview)
        xs = ttk.Scrollbar(body, orient="horizontal", command=self.cv.xview)
        self.cv.configure(yscrollcommand=lambda *a: (ys.set(*a), self._later_pictures()),
                          xscrollcommand=lambda *a: (xs.set(*a), self._later_pictures()))
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        self.cv.pack(fill="both", expand=True)
        self.title_ink = "#eeeeee" if theme.dark() else "#111111"
        self.hidden_ink = "#ffb070" if theme.dark() else "#7a2e00"
        self.v_line = tk.StringVar(self, value="")
        ttk.Label(self, textvariable=self.v_line, padding=(8, 2)).pack(fill="x")
        cv = self.cv
        cv.bind("<ButtonPress-1>", self._press)
        cv.bind("<B1-Motion>", self._motion)
        cv.bind("<ButtonRelease-1>", self._release)
        cv.bind("<ButtonPress-3>", self._menu)
        cv.bind("<Motion>", self._hover)
        cv.bind("<ButtonPress-2>", lambda e: cv.scan_mark(e.x, e.y))
        cv.bind("<B2-Motion>", lambda e: cv.scan_dragto(e.x, e.y, gain=1))
        cv.bind("<MouseWheel>", lambda e: self._wheel(e, 1 if e.delta > 0 else -1))
        cv.bind("<Button-4>", lambda e: self._wheel(e, 1))
        cv.bind("<Button-5>", lambda e: self._wheel(e, -1))
        cv.bind("<Configure>", lambda e: self._later_pictures())

    def close(self):
        if self.draft:
            got = messagebox.askyesnocancel(TITLE, "Put your %d changes on the editor before the board closes? "
                                                   "(No drops them.)" % len(self.draft), parent=self)
            if got is None:
                return
            if got:
                self.accept()
        if self._changed in self.look.on_change:
            self.look.on_change.remove(self._changed)
        self.destroy()

    def _in_windows(self):
        self.look.edit(True)
        self.app.lift()

    # ---- the pages ----
    def _page(self, pid):
        return next((p for p in self.pages if p["id"] == pid), None)

    def _read_pictures(self):
        Image, _ = _pil()
        folder = LK.board_dir()
        if Image is None or not folder:
            return
        for p in self.pages:
            path = os.path.join(folder, p.get("picture") or "")
            if p.get("picture") and os.path.isfile(path):
                try:
                    with Image.open(path) as im:
                        self.pictures[p["id"]] = im.convert("RGB")
                except Exception:
                    pass

    def _keep(self, page, picture):
        folder = LK.board_dir()
        page["picture"] = None
        if picture is not None and folder:
            name = "".join(c if c.isalnum() else "_" for c in page["id"]) + ".png"
            try:
                os.makedirs(folder, exist_ok=True)
                picture.save(os.path.join(folder, name))
                page["picture"] = name
            except Exception:
                pass
        self.pictures[page["id"]] = picture
        self._shown.pop(page["id"], None)

    def _steps(self):
        """[(page id, title, group)] of the pages to gather (the tabs of a work found when it is open)."""
        app = self.app
        out = []
        for group in app.WORK_ROW:
            for k in group:
                if k == "faction":                    # its tabs hold both sides (Edit / New faction)
                    out.append(("work:edit", "Factions", "Works"))
                elif k == "recolour" and getattr(app, "mod", None) is not None:
                    continue                           # with a mod loaded it opens a window of its own
                else:
                    out.append(("work:" + k, app.WORK_TITLES.get(k, k), "Works"))
        out += [("window:" + m, t, "Windows") for m, t in WINDOWS if hasattr(app, m)]
        return out

    def _open(self, pid):
        """The page shown in the editor: a work (and its tab), or a Tools window (-> the window, or None)."""
        app = self.app
        kind, _, name = pid.partition(":")
        if kind == "work":
            work, _, tab = name.partition("#")
            if work in ("edit", "new"):
                app._faction_side = work
                app.v_bar.set("faction")
            else:
                app.v_bar.set(work)
            app._bar_pressed()
            if tab:
                for t in app.nb.tabs():
                    if app.nb.tab(t, "text").strip() == tab and app.nb.tab(t, "state") != "hidden":
                        app.nb.select(t)
                        break
            return app
        before = {str(w) for w in app.winfo_children()}
        fn = getattr(app, name, None)
        if fn is None:
            return None
        with _quiet():                                   # a window that would ask first (no game log yet): not shown
            app.once(name, fn)()
        for w in app.winfo_children():
            if isinstance(w, tk.Toplevel) and not w.wm_overrideredirect() and w is not self and \
                    (str(w) not in before or w in app._once.get(name, [])):
                w._board_new = str(w) not in before
                return w
        return None

    def _where(self):
        app = self.app
        try:
            tab = app.tab_name() if app.nb.winfo_ismapped() else ""
        except tk.TclError:
            tab = ""
        return app.v_work.get(), tab

    def _back_to(self, where):
        app = self.app
        work, tab = where
        try:
            if app.v_work.get() != work:
                self._open("work:" + work)
            if tab and app.tab_name() != tab:
                self._open("work:%s#%s" % (work, tab))
        except Exception:
            pass

    def refresh(self, only=None):
        """The pages' pictures and pieces taken again (only: those page ids), one page after another."""
        if self._busy:
            return
        self._busy = True
        self._run(self._gather(only))

    def _run(self, gen):
        try:
            wait = next(gen)
        except StopIteration:
            return
        except Exception as e:                           # never leave the board busy for good
            self._busy = None
            self.v_line.set("The pages could not all be laid out: %s" % e)
            return
        self.after(wait, lambda: self._run(gen))

    def _gather(self, only=None):
        app = self.app
        where = self._where()
        steps = self._steps()
        if only:                                         # a tab of a work: its work's step finds it
            works = {pid.partition("#")[0] for pid in only}
            steps = [s for s in steps if s[0] in works or s[0] in only]
        new = [] if only is None else None
        done, errors = 0, []
        for pid, title, group in steps:
            done += 1
            self.v_line.set("Laying out the pages: %d / %d - %s" % (done, len(steps), title))
            try:
                top = self._open(pid)
            except Exception as e:
                errors.append("%s: %s" % (title, e))
                continue
            if top is None:
                continue
            yield WAIT_WORK if top is app else WAIT_WINDOW
            pages = [(pid, title, group, None)]
            work = pid.partition(":")[2]
            if top is app and work in TAB_WORKS:
                pages = []
                for t in app.nb.tabs():
                    name = app.nb.tab(t, "text").strip()
                    if app.nb.tab(t, "state") == "hidden" or name in SKIP_TABS:
                        continue
                    tid = "%s#%s" % (pid, name)
                    if only is None or tid in only or pid in only:
                        pages.append((tid, name, title, t))
            for tid, ttitle, tgroup, tab in pages:
                if tab is not None:
                    try:
                        app.nb.select(tab)
                    except tk.TclError:
                        continue
                    yield WAIT_TAB
                self._take(tid, ttitle, tgroup, top, new)
            if top is not app and getattr(top, "_board_new", False):
                try:
                    top.destroy()
                except tk.TclError:
                    pass
        self._back_to(where)
        if new is not None:
            self.pages = new
        LK.save_board(self.pages)
        self._busy = None
        self.lift()
        self.v_line.set("%d pages laid out." % len(self.pages) + (" Not laid out: " + "; ".join(errors)
                                                                   if errors else ""))
        if self.picked:                                  # the picked piece picked again in the new pieces
            pid, pc = self.picked
            page = self._page(pid)
            new_pc = next((q for q in page["pieces"] if pc and q["key"] == pc["key"]), None) if page else None
            self.picked = (pid, new_pc) if page and (new_pc or not pc) else None
        self.draw()
        if only is None:
            self.fit()

    def _take(self, pid, title, group, top, new):
        try:
            top.update()
        except tk.TclError:
            return
        picture = snap(top)
        pieces, hidden = pieces_of(self.look, top)
        page = {"id": pid, "title": title, "group": group, "size": [top.winfo_width(), top.winfo_height()],
                "pieces": pieces, "hidden": hidden}
        self._keep(page, picture)
        for key in [k for k, (pid_, _) in self.accepted.items() if pid_ == pid]:
            del self.accepted[key]
        for pc in pieces:                                # a draft made before the picture: drawn over it again
            if pc["key"] in self.draft:
                old = (self.draft_at.get(pc["key"]) or (None, None))[1]
                pc["was"] = list(pc["box"])
                if old is not None:
                    pc["box"] = list(old["box"])
                self.draft_at[pc["key"]] = (pid, pc)
                self.draft_undo.clear()                  # its steps were on the pieces as they stood before
                self.draft_redo.clear()
        if new is not None:
            new.append(page)
        else:
            old = self._page(pid)
            if old is None:
                self.pages.append(page)
            else:
                self.pages[self.pages.index(old)] = page
        self.update_idletasks()

    # ---- drawing ----
    def _places(self):
        groups, order = [], []
        for p in self.pages:
            if p["group"] not in order:
                order.append(p["group"])
                groups.append([])
            groups[order.index(p["group"])].append((p["id"], p["size"][0], p["size"][1] + 24 * bool(p["hidden"])))
        places, total, tops = LK.lay_cards(groups)
        return places, total, list(zip(order, tops))

    def draw(self):
        cv, z = self.cv, self.zoom
        cv.delete("all")
        self._shown.clear()
        places, total, heads = self._places()
        self.places = places
        title_px = max(7, min(14, int(36 * z)))
        for name, top in heads:                          # above its first row's card titles, whatever the zoom
            first = (top + 2 * LK.CARD_HEAD) * z - title_px * 2 - 8
            cv.create_text(0, first, text=name, anchor="sw", fill=self.title_ink,
                           font=("", max(9, min(22, int(60 * z))), "bold"))
        cv.configure(scrollregion=(-200 * z, -200 * z, (total[0] + 200) * z, (total[1] + 200) * z))
        changed = self.look.data["pieces"]
        for p in self.pages:
            x, y = places[p["id"]]
            w, h = p["size"]
            cv.create_text(x * z, y * z - 3, text=p["title"], anchor="sw", fill=self.title_ink, width=max(w * z, 20),
                           font=("", title_px))
            cv.create_rectangle(x * z, y * z, (x + w) * z, (y + h) * z, fill="#f0f0f0", outline="#777777",
                                tags=("card", "card:" + p["id"]))
            if p["id"] not in self.pictures or self.pictures[p["id"]] is None:
                for pc in p["pieces"]:                   # no picture: each piece drawn as a box with its words
                    bx, by, bw, bh = pc.get("was") or pc["box"]     # where the editor has it
                    cv.create_rectangle((x + bx) * z, (y + by) * z, (x + bx + bw) * z, (y + by + bh) * z,
                                        fill="#e1e1e1", outline="#9a9a9a")
                    if pc["text"] and z >= 0.3:
                        cv.create_text((x + bx + bw / 2) * z, (y + by + bh / 2) * z, text=pc["text"][:30],
                                       font=("", max(6, int(9 * z * 1.6))), fill="#222222")
            if self.v_frames.get():
                for pc in p["pieces"]:
                    bx, by, bw, bh = pc["box"]
                    cv.create_rectangle((x + bx) * z, (y + by) * z, (x + bx + bw) * z, (y + by + bh) * z,
                                        outline="#3c8cff", dash=(2, 2) if z < 0.5 else (3, 2), tags="frame")
            for pc in p["pieces"]:
                if pc["key"] in changed:
                    bx, by = pc["box"][:2]
                    cv.create_oval((x + bx) * z - 3, (y + by) * z - 3, (x + bx) * z + 3, (y + by) * z + 3,
                                   fill=CHANGED, outline="")
            hx = x
            for key in p["hidden"]:                      # the hidden pieces in a strip under the page
                words = _words(key)[:24]
                t = cv.create_text((hx + 6) * z, (y + h + 12) * z, text="hidden: " + words, anchor="w",
                                   fill=self.hidden_ink,
                                   font=("", max(6, int(10 * min(1, z * 2.5)))), tags=("hidden", "hidden:" + key))
                bb = cv.bbox(t)
                hx += max(140, (bb[2] - bb[0]) / z + 20) if bb else 160
        self._draft_marks()
        self._marks()
        self._later_pictures()

    def _later_pictures(self):
        if self._job is None:
            self._job = self.after(40, self._pictures)

    def _pictures(self):
        """The pictures of the pages in sight drawn at this zoom (the others when they come into sight)."""
        self._job = None
        Image, ImageTk = _pil()
        if ImageTk is None or not hasattr(self, "places"):
            return
        cv, z = self.cv, self.zoom
        x0, y0 = cv.canvasx(0), cv.canvasy(0)
        x1, y1 = x0 + cv.winfo_width(), y0 + cv.winfo_height()
        for p in self.pages:
            pic = self.pictures.get(p["id"])
            if pic is None:
                continue
            x, y = self.places[p["id"]]
            w, h = p["size"]
            seen = x * z < x1 and (x + w) * z > x0 and y * z < y1 and (y + h) * z > y0
            have = self._shown.get(p["id"])
            if not seen or (have and have[0] == z):
                continue
            size = (max(1, int(w * z)), max(1, int(h * z)))
            small = pic.resize(size, Image.BILINEAR if z < 1 else Image.NEAREST) if size != pic.size else pic
            photo = ImageTk.PhotoImage(small, master=cv)
            cv.delete("pic:" + p["id"])
            item = cv.create_image(x * z, y * z, image=photo, anchor="nw", tags=("pic", "pic:" + p["id"]))
            cv.tag_raise(item, "card:" + p["id"])
            self._shown[p["id"]] = (z, photo)
        cv.tag_raise("frame")
        cv.tag_raise("draft")
        cv.tag_raise("grid")
        cv.tag_raise("mark")
        cv.tag_raise("ghost")

    def _draft_marks(self):
        """The changes not yet on the editor's pictures (the draft, and those accepted until the page is taken
        again): the old place greyed, the piece's picture where it goes, its new words, a cross on a hidden one."""
        cv, z = self.cv, self.zoom
        cv.delete("draft")
        self._draft_photos = []
        if not hasattr(self, "places"):
            return
        Image, ImageTk = _pil()
        from . import theme
        ground = theme.palette()["bg"]
        shown = [(k, at) for k, at in self.accepted.items() if k not in self.draft_at] + list(self.draft_at.items())
        for key, (pid, pc) in shown:
            if pc is None or pid not in self.places:
                continue
            x, y = self.places[pid]
            entry = LK.merged(self.look.data["pieces"].get(key), self.draft.get(key))
            was = pc.get("was") or pc["box"]
            wx, wy, ww, wh = was
            cv.create_rectangle((x + wx) * z, (y + wy) * z, (x + wx + ww) * z, (y + wy + wh) * z, fill=ground,
                                outline="", stipple="gray75" if entry.get("hidden") else "", tags="draft")
            if entry.get("hidden"):
                for a, b, c, d in ((wx, wy, wx + ww, wy + wh), (wx, wy + wh, wx + ww, wy)):
                    cv.create_line((x + a) * z, (y + b) * z, (x + c) * z, (y + d) * z, fill="#d02020", width=2,
                                   tags="draft")
                continue
            nx, ny, nw, nh = pc["box"]
            pic = self.pictures.get(pid)
            if pic is not None and ImageTk is not None and ww > 0 and wh > 0:
                part = pic.crop((wx, wy, wx + ww, wy + wh)).resize((max(1, int(nw * z)), max(1, int(nh * z))))
                photo = ImageTk.PhotoImage(part, master=cv)
                self._draft_photos.append(photo)
                cv.create_image((x + nx) * z, (y + ny) * z, image=photo, anchor="nw", tags="draft")
            elif pic is None:                            # no picture: the piece as a box with its words
                cv.create_rectangle((x + nx) * z, (y + ny) * z, (x + nx + nw) * z, (y + ny + nh) * z,
                                    fill="#e1e1e1", outline="#9a9a9a", tags="draft")
                if pc["text"] and z >= 0.3:
                    cv.create_text((x + nx + nw / 2) * z, (y + ny + nh / 2) * z, text=pc["text"][:30],
                                   font=("", max(6, int(9 * z * 1.6))), fill="#222222", tags="draft")
            if any(entry.get(k) for k in ("text",) + LK.STYLE_KEYS) or \
                    any(k in (self.draft.get(key) or {}) for k in ("text",) + LK.STYLE_KEYS):
                words = LK.shown_words(entry, self.look.word(pc["text"]) if pc["text"] else "")
                font = LK.font_of(entry.get("font"), ("", 9)) or ("", 9)
                font = (font[0], max(5, int(abs(font[1]) * z * 1.4))) + tuple(font[2:])
                cv.create_rectangle((x + nx) * z, (y + ny) * z, (x + nx + nw) * z, (y + ny + nh) * z,
                                    fill=entry.get("bg") or ground, outline="#9a9a9a", tags="draft")
                if words:
                    cv.create_text((x + nx + nw / 2) * z, (y + ny + nh / 2) * z, text=words[:40], font=font,
                                   fill=entry.get("fg") or theme.palette()["fg"], tags="draft")
            cv.create_rectangle((x + nx) * z, (y + ny) * z, (x + nx + nw) * z, (y + ny + nh) * z, outline=CHANGED,
                                dash=(3, 2), tags="draft")

    def _grid_on(self, pid):
        """The grid's lines over one page (the picked one, the one a piece is dragged on)."""
        cv, z = self.cv, self.zoom
        cv.delete("grid")
        step = self._step()
        p = self._page(pid)
        if not self.v_grid.get() or p is None or pid not in self.places or step * z < 6:
            return
        x, y = self.places[pid]
        w, h = p["size"]
        for gx in range(0, int(w) + 1, step):
            cv.create_line((x + gx) * z, y * z, (x + gx) * z, (y + h) * z, fill=GRID_INK, stipple="gray50",
                           tags="grid")
        for gy in range(0, int(h) + 1, step):
            cv.create_line(x * z, (y + gy) * z, (x + w) * z, (y + gy) * z, fill=GRID_INK, stipple="gray50",
                           tags="grid")

    def _step(self):
        try:
            return max(2, int(self.v_step.get()))
        except ValueError:
            return 8

    def _marks(self):
        """The picked piece's yellow frame and corner handles (and the grid over its page)."""
        cv, z = self.cv, self.zoom
        cv.delete("mark")
        cv.delete("grid")
        if not self.picked:
            return
        pid, pc = self.picked
        p = self._page(pid)
        if p is None or pid not in self.places:
            return
        self._grid_on(pid)
        x, y = self.places[pid]
        bx, by, bw, bh = pc["box"] if pc else (0, 0, p["size"][0], p["size"][1])
        a, b, c, d = (x + bx) * z, (y + by) * z, (x + bx + bw) * z, (y + by + bh) * z
        cv.create_rectangle(a - 1, b - 1, c + 1, d + 1, outline=YELLOW, width=2, tags="mark")
        if pc:
            for hx, hy in ((a, b), (c, b), (a, d), (c, d)):
                cv.create_rectangle(hx - HANDLE, hy - HANDLE, hx + HANDLE, hy + HANDLE, fill=YELLOW,
                                    outline="#000000", tags="mark")

    # ---- the view ----
    def fit(self):
        if not self.pages:
            return
        self.update_idletasks()
        _, total, _ = self._places()
        w, h = max(self.cv.winfo_width(), 200), max(self.cv.winfo_height(), 200)
        want = min(w / (total[0] + 400), h / (total[1] + 400))
        self.zoom = max([s for s in ZOOMS if s <= want] or [ZOOMS[0]])
        self.draw()
        self.cv.xview_moveto(0)
        self.cv.yview_moveto(0)

    def _wheel(self, e, step):
        i = min(range(len(ZOOMS)), key=lambda k: abs(ZOOMS[k] - self.zoom))
        j = max(0, min(len(ZOOMS) - 1, i + step))
        if j == i:
            return
        wx, wy = self.cv.canvasx(e.x) / self.zoom, self.cv.canvasy(e.y) / self.zoom
        self.zoom = ZOOMS[j]
        self.draw()
        x0 = float(self.cv.cget("scrollregion").split()[0])
        y0 = float(self.cv.cget("scrollregion").split()[1])
        r = [float(v) for v in self.cv.cget("scrollregion").split()]
        self.cv.xview_moveto((wx * self.zoom - e.x - x0) / max(r[2] - r[0], 1))
        self.cv.yview_moveto((wy * self.zoom - e.y - y0) / max(r[3] - r[1], 1))

    def _world(self, e):
        return self.cv.canvasx(e.x) / self.zoom, self.cv.canvasy(e.y) / self.zoom

    def _hit(self, wx, wy):
        """(page, piece or None, x and y in the page) under a board point, or (None, None, 0, 0)."""
        for p in self.pages:
            x, y = self.places.get(p["id"], (0, 0))
            if x <= wx < x + p["size"][0] and y <= wy < y + p["size"][1]:
                return p, LK.piece_at(p["pieces"], wx - x, wy - y), wx - x, wy - y
        return None, None, 0, 0

    def _hidden_at(self, e):
        for item in self.cv.find_overlapping(self.cv.canvasx(e.x) - 2, self.cv.canvasy(e.y) - 2,
                                             self.cv.canvasx(e.x) + 2, self.cv.canvasy(e.y) + 2):
            for t in self.cv.gettags(item):
                if t.startswith("hidden:"):
                    return t[len("hidden:"):]
        return None

    def _hover(self, e):
        if self._drag or self._busy:
            return
        p, pc, _, _ = self._hit(*self._world(e))
        if pc:
            self.v_line.set("%s  -  %s%s" % (p["title"], pc["text"] or pc["cls"],
                                              "  (changed)" if pc["key"] in self.look.data["pieces"] else ""))
        elif p:
            self.v_line.set(p["title"] + "  -  right click: refresh it, show it in the editor")

    # ---- the mouse ----
    def _corner(self, e):
        """The picked piece's corner under the mouse: 'nw' / 'ne' / 'sw' / 'se', or None."""
        if not self.picked or not self.picked[1]:
            return None
        pid, pc = self.picked
        x, y = self.places[pid]
        z = self.zoom
        bx, by, bw, bh = pc["box"]
        mx, my = self.cv.canvasx(e.x), self.cv.canvasy(e.y)
        for name, hx, hy in (("nw", bx, by), ("ne", bx + bw, by), ("sw", bx, by + bh), ("se", bx + bw, by + bh)):
            if abs(mx - (x + hx) * z) <= HANDLE + 1 and abs(my - (y + hy) * z) <= HANDLE + 1:
                return name
        return None

    def _press(self, e):
        self.cv.focus_set()
        if self._busy:
            return
        corner = self._corner(e)
        wx, wy = self._world(e)
        if corner:
            self._drag = {"kind": "size", "corner": corner, "page": self.picked[0], "piece": self.picked[1],
                          "start": (wx, wy), "box": list(self.picked[1]["box"]), "moved": False}
            return
        p, pc, px, py = self._hit(wx, wy)
        if p is None:
            self.picked = None
            self._marks()
            self.cv.scan_mark(e.x, e.y)
            self._drag = {"kind": "pan"}
            return
        self.picked = (p["id"], pc)
        self._marks()
        if pc:
            self._drag = {"kind": "move", "page": p["id"], "piece": pc, "start": (wx, wy),
                          "box": list(pc["box"]), "moved": False}

    def _motion(self, e):
        d = self._drag
        if not d:
            return
        if d["kind"] == "pan":
            self.cv.scan_dragto(e.x, e.y, gain=1)
            return
        wx, wy = self._world(e)
        dx, dy = wx - d["start"][0], wy - d["start"][1]
        if not d["moved"] and abs(dx) * self.zoom + abs(dy) * self.zoom < 5:
            return
        d["moved"] = True
        bx, by, bw, bh = d["box"]
        page = self._page(d["page"])
        pw, ph = page["size"]
        others = self._others(page, d["piece"]) if self.v_snap.get() else []
        grid, step = self.v_grid.get(), self._step()
        if d["kind"] == "size":
            c = d["corner"]
            x0, y0, x1, y1 = bx, by, bx + bw, by + bh
            xs, ys = B.lines_of(others)
            if "w" in c:
                x0 = min(B.snap_edge(x0 + dx, xs, step, self.zoom, to_grid=grid)[0], x1 - 8)
            else:
                x1 = max(B.snap_edge(x1 + dx, xs, step, self.zoom, to_grid=grid)[0], x0 + 8)
            if "n" in c:
                y0 = min(B.snap_edge(y0 + dy, ys, step, self.zoom, to_grid=grid)[0], y1 - 8)
            else:
                y1 = max(B.snap_edge(y1 + dy, ys, step, self.zoom, to_grid=grid)[0], y0 + 8)
            d["new"] = [int(round(x0)), int(round(y0)), int(round(x1 - x0)), int(round(y1 - y0))]
        else:
            d["free"] = not (self.v_row.get() or _alt(e))
            nx, ny = bx + dx, by + dy
            if d["free"]:
                nx, ny, _ = B.snap_box((nx, ny, bw, bh), others, grid=step, zoom=self.zoom, to_grid=grid)
            d["new"] = [int(round(max(0, min(nx, pw - bw)))), int(round(max(0, min(ny, ph - bh)))), bw, bh]
        d["guides"] = B.guide_lines(d["new"], others) if others and d.get("free", True) else ([], [])
        self._ghost(d)

    def _others(self, page, pc):
        """The boxes a piece of page may stick to: its other pieces (not one it holds or is held by) and the
        window's own edges."""
        mb = pc["box"]
        out = [q["box"] for q in page["pieces"] if q is not pc and q["key"] != pc["key"]
               and not LK._holds(q["box"], mb) and not LK._holds(mb, q["box"])]
        return out + [[0, 0, page["size"][0], page["size"][1]]]

    def _ghost(self, d):
        """The piece's picture where it would go, and (in a row) the yellow line where it would stand."""
        cv, z = self.cv, self.zoom
        cv.delete("ghost")
        x, y = self.places[d["page"]]
        nx, ny, nw, nh = d["new"]
        pic = self.pictures.get(d["page"])
        Image, ImageTk = _pil()
        if pic is not None and ImageTk is not None:
            bx, by, bw, bh = d["piece"].get("was") or d["box"]     # where the piece is in the picture
            part = pic.crop((bx, by, bx + bw, by + bh)).resize((max(1, int(nw * z)), max(1, int(nh * z))))
            d["photo"] = ImageTk.PhotoImage(part, master=cv)
            cv.create_image((x + nx) * z, (y + ny) * z, image=d["photo"], anchor="nw", tags="ghost")
        cv.create_rectangle((x + nx) * z, (y + ny) * z, (x + nx + nw) * z, (y + ny + nh) * z, outline=YELLOW,
                            width=2, dash=(4, 2), tags="ghost")
        self._grid_on(d["page"])
        pw, ph = self._page(d["page"])["size"]
        gx, gy = d.get("guides") or ([], [])
        for v in gx:
            cv.create_line((x + v) * z, y * z, (x + v) * z, (y + ph) * z, fill=GUIDE, width=2, tags="ghost")
        for v in gy:
            cv.create_line(x * z, (y + v) * z, (x + pw) * z, (y + v) * z, fill=GUIDE, width=2, tags="ghost")
        d["target"] = None
        if d["kind"] == "move" and not d.get("free"):
            page = self._page(d["page"])
            cx, cy = nx + nw / 2, ny + nh / 2
            t, where = LK.drop_beside(page["pieces"], d["piece"], cx, cy)
            if t is not None:
                d["target"] = (t, where)
                tx, ty, tw, th = t["box"]
                lx = tx - 2 if where == "before" else tx + tw + 1
                cv.create_rectangle((x + lx) * z - 2, (y + ty) * z, (x + lx) * z + 2, (y + ty + th) * z,
                                    fill=YELLOW, outline="", tags="ghost")

    def _release(self, e):
        d, self._drag = self._drag, None
        self.cv.delete("ghost")
        self._marks()
        if not d or d["kind"] == "pan" or not d.get("moved"):
            return
        pc, page = d["piece"], self._page(d["page"])
        if d["kind"] == "size":
            nx, ny, nw, nh = d["new"]
            e_ = self._entry(pc["key"])
            kw = {"size": [nw, nh]}
            if "xy" in e_:                               # a free piece: its corner moves with it
                ox, oy = e_["xy"][:2]
                kw["xy"] = [int(ox + nx - pc["box"][0]), int(oy + ny - pc["box"][1])]
            self._apply(page, pc, d["new"], **kw)
        elif d.get("free"):
            nx, ny, nw, nh = d["new"]
            up, fx, fy = LK.free_spot(pc["boxes"], nx, ny, nw, nh)
            self._apply(page, pc, d["new"], xy=[fx, fy], up=up or None, to=None, where=None, hidden=None)
        elif d.get("target"):
            t, where = d["target"]
            w, tw = self.look.by_key.get(pc["key"]), self.look.by_key.get(t["key"])
            try:
                why = can_move(w, tw) if w is not None and tw is not None and w.winfo_exists() and \
                    tw.winfo_exists() and tw.winfo_manager() else None
            except tk.TclError:
                why = None
            if why:
                messagebox.showinfo(TITLE, why, parent=self)
                return
            self._apply(page, pc, d["new"], to=t["key"], where=where, xy=None, up=None, hidden=None)

    def _cancel_drag(self):
        self._drag = None
        self.cv.delete("ghost")
        self._marks()

    # ---- the draft ----
    def _entry(self, key):
        """A piece's look as the board shows it: the editor's with the draft over it."""
        return LK.merged(self.look.data["pieces"].get(key), self.draft.get(key))

    def _apply(self, page, pc, box=None, key=None, **kw):
        """A change of one piece into the draft (drawn on the board at once, put on the editor by Accept)."""
        key = key or pc["key"]
        self.draft_undo.append(self._draft_state(key, pc))
        self.draft_redo.clear()
        if pc is not None:
            pc.setdefault("was", list(pc["box"]))
            if box is not None:
                pc["box"] = list(box)
        self.draft[key] = dict(self.draft.get(key) or {}, **kw)
        self.draft_at[key] = (page["id"] if page else None, pc)
        self._draft_shown()

    def _draft_state(self, key, pc):
        return (key, pc, None if pc is None else list(pc["box"]), dict(self.draft[key]) if key in self.draft
                else None, self.draft_at.get(key))

    def _draft_back(self, state):
        key, pc, box, change, at = state
        if pc is not None and box is not None:
            pc["box"] = list(box)
        if change is None:
            self.draft.pop(key, None)
            self.draft_at.pop(key, None)
            if pc is not None and key not in self.accepted:
                pc.pop("was", None)
        else:
            self.draft[key] = change
            self.draft_at[key] = at

    def _draft_shown(self):
        n = len(self.draft)
        self.b_accept.configure(text="Accept (%d)" % n if n else "Accept", state="normal" if n else "disabled")
        self.b_discard.configure(state="normal" if n else "disabled")
        if n:
            self.v_line.set("%d changes drawn on the board - Accept puts them on the editor." % n)
        if hasattr(self, "places"):
            self.draw()

    def accept(self):
        """The draft put on the editor, piece after piece (each one Undo step there); the pages' pictures taken
        again a moment later."""
        draft, at = self.draft, self.draft_at
        self.draft, self.draft_at = {}, {}
        self.draft_undo.clear()
        self.draft_redo.clear()
        for key, change in draft.items():
            self.look.change_key(key, **change)
            if at.get(key) and at[key][1] is not None:
                self.accepted[key] = at[key]             # drawn over the old picture until it is taken again
        self._draft_shown()
        self.v_line.set("%d changes put on the editor." % len(draft))

    def discard(self):
        if not self.draft:
            return
        while self.draft_undo:                           # step by step back to before the first change
            self._draft_back(self.draft_undo.pop())
        self.draft, self.draft_at = {}, {}
        self.draft_redo.clear()
        self._draft_shown()
        self.v_line.set("The changes on the board dropped.")

    def _changed(self, key):
        """The look changed a piece (here, by Undo, or in the windows): its page's picture taken again soon."""
        for p in self.pages:
            if any(pc["key"] == key for pc in p["pieces"]) or key in p["hidden"]:
                self._dirty.add(p["id"])
        if self._dirty and not self._busy:
            if getattr(self, "_again", None):
                self.after_cancel(self._again)
            self._again = self.after(700, self._take_again)

    def _take_again(self):
        self._again = None
        if self._busy:
            self._again = self.after(700, self._take_again)
            return
        only, self._dirty = set(self._dirty), set()
        if only:
            self.refresh(only)

    def _nudge(self, dx, dy, big=False):
        """The arrows move a free piece a pixel (Shift: 10)."""
        if not self.picked or not self.picked[1]:
            return
        pc = self.picked[1]
        e_ = self._entry(pc["key"])
        n = 10 if big else 1
        box = list(pc["box"])
        box[0] += dx * n
        box[1] += dy * n
        if "xy" in e_:
            self._apply(self._page(self.picked[0]), pc, box, xy=[e_["xy"][0] + dx * n, e_["xy"][1] + dy * n])
            return
        up, fx, fy = LK.free_spot(pc["boxes"], *box)    # a piece in a row: from now on free, where it stands
        self._apply(self._page(self.picked[0]), pc, box, xy=[fx, fy], up=up or None, to=None, where=None)

    def _hide_picked(self):
        if self.picked and self.picked[1]:
            self._apply(self._page(self.picked[0]), self.picked[1], hidden=True)

    # ---- the right click ----
    def _menu(self, e):
        if self._busy:
            return
        m = tk.Menu(self, tearoff=False)
        m._look_skip = True
        key = self._hidden_at(e)
        p, pc, _, _ = self._hit(*self._world(e))
        if key and not pc:
            m.add_command(label=_words(key)[:60], state="disabled")
            m.add_separator()
            m.add_command(label="Show it again", command=lambda: self._show_again(key))
        elif pc:
            self.picked = (p["id"], pc)
            self._marks()
            e_ = self._entry(pc["key"])
            m.add_command(label=(pc["text"] or pc["cls"])[:60], state="disabled")
            m.add_separator()
            if pc["text"]:
                m.add_command(label="Rename...", command=lambda: self._rename(p, pc))
            m.add_command(label="Hover text...", command=lambda: self._tip(p, pc))
            m.add_command(label="Size in pixels...", command=lambda: self._size(p, pc))
            m.add_command(label="Width in letters...", command=lambda: self._width(p, pc))
            m.add_command(label="Colours, font and emoji...", command=lambda: self._style(p, pc))
            m.add_command(label="Copy its look", command=lambda: self._copy_look(pc))
            m.add_command(label="Paste the look", command=lambda: self._apply(p, pc, **self._copied),
                          state="normal" if getattr(self, "_copied", None) else "disabled")
            m.add_command(label="Hide", command=lambda: self._apply(p, pc, hidden=True))
            if "xy" in e_:
                m.add_command(label="Back into its row", command=lambda: self._apply(p, pc, pc.get("was"), xy=None,
                                                                                       up=None, size=None))
            m.add_separator()
            m.add_command(label="Back to how it was", command=lambda: self._back_one(p, pc),
                          state="normal" if e_ else "disabled")
            m.add_command(label="Show it in the editor", command=lambda: self._show(p, pc))
        elif p:
            self.picked = (p["id"], None)
            self._marks()
            m.add_command(label=p["title"], state="disabled")
            m.add_separator()
            m.add_command(label="Refresh this page", command=lambda: self.refresh({p["id"]}))
            m.add_command(label="Show this page in the editor", command=lambda: self._show(p, None))
            m.add_command(label="Its pieces back to how they were...", command=lambda: self._back_page(p))
        else:
            m.add_command(label="Refresh all pages", command=self.refresh)
            m.add_command(label="Fit", command=self.fit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _ask(self, text, now):
        return simpledialog.askstring(TITLE, text, initialvalue=now, parent=self)

    def _rename(self, p, pc):
        now = self._entry(pc["key"]).get("text") or self.look.word(pc["text"])
        got = self._ask("Its words (empty: the editor's own '%s'):" % pc["text"], now)
        if got is not None:
            self._apply(p, pc, text=got.strip() or None)

    def _tip(self, p, pc):
        got = self._ask("Its hover text (shown with its own; empty: none):",
                        self._entry(pc["key"]).get("tip", ""))
        if got is not None:
            self._apply(p, pc, tip=got.strip() or None)

    def _size(self, p, pc):
        now = self._entry(pc["key"]).get("size") or pc["box"][2:]
        got = self._ask("Its size in pixels, width x height (empty: as big as its words need):",
                        "%d x %d" % tuple(now[:2]))
        if got is None:
            return
        got = got.lower().replace("*", "x").replace(",", "x")
        if not got.strip():
            self._apply(p, pc, size=None)
            return
        try:
            w, h = (int(v) for v in got.split("x")[:2])
        except ValueError:
            messagebox.showinfo(TITLE, "Two whole numbers, as 120 x 24, or nothing.", parent=self)
            return
        self._apply(p, pc, [pc["box"][0], pc["box"][1], max(4, w), max(4, h)], size=[max(4, w), max(4, h)])

    def _style(self, p, pc):
        got = ask_style(self, self._entry(pc["key"]), self.look.word(pc["text"]) if pc["text"] else pc["cls"])
        if got is not None:
            self._apply(p, pc, **got)

    def _copy_look(self, pc):
        """Its colours, font and emoji kept to put on other pieces (Paste the look)."""
        e = self._entry(pc["key"])
        self._copied = {k: e.get(k) for k in LK.STYLE_KEYS}
        self.v_line.set("Its look copied - right click another piece > Paste the look.")

    def _width(self, p, pc):
        now = self._entry(pc["key"]).get("width", "")
        got = self._ask("Its width in letters (empty: as wide as its words):", str(now))
        if got is None:
            return
        got = got.strip()
        if got and not got.lstrip("-").isdigit():
            messagebox.showinfo(TITLE, "A whole number of letters, or nothing.", parent=self)
            return
        self._apply(p, pc, width=int(got) if got else None)

    def _back_one(self, p, pc):
        old = self._entry(pc["key"])
        if old:
            self._apply(p, pc, pc.get("was"), **{k: None for k in LK.KEYS})

    def _show_again(self, key):
        p = next((q for q in self.pages if key in q["hidden"]), None)
        self._apply(p, None, key=key, hidden=None)

    def _back_page(self, p):
        keys = [pc["key"] for pc in p["pieces"] if pc["key"] in self.look.data["pieces"]] + list(p["hidden"])
        if not keys:
            messagebox.showinfo(TITLE, "Nothing on this page was changed.", parent=self)
            return
        if messagebox.askyesno(TITLE, "%d pieces of '%s' back where the editor puts them, with their own words? "
                                      "(Undo takes it back step by step.)" % (len(keys), p["title"]), parent=self):
            for k in keys:
                pc = next((q for q in p["pieces"] if q["key"] == k), None)
                self._apply(p, pc, key=k, **{a: None for a in LK.KEYS})

    def _show(self, p, pc):
        """The page shown in the editor (and the piece framed yellow for a few seconds)."""
        top = self._open(p["id"])
        if top is None:
            return
        top.lift()
        w = self.look.by_key.get(pc["key"]) if pc else None
        if w is not None:
            self.look.pick(w)
            self.after(3000, lambda: self.look.pick(None) if self.look.picked is w else None)

    # ---- the whole look ----
    def undo(self):
        if self.draft_undo:
            state = self.draft_undo.pop()
            self.draft_redo.append(self._draft_state(state[0], state[1]))
            self._draft_back(state)
            self._draft_shown()
        elif not self.look.do_undo():
            self.v_line.set("Nothing to undo.")

    def redo(self):
        if self.draft_redo:
            state = self.draft_redo.pop()
            self.draft_undo.append(self._draft_state(state[0], state[1]))
            self._draft_back(state)
            self._draft_shown()
        elif not self.look.do_redo():
            self.v_line.set("Nothing to redo.")

    def _draft_first(self):
        """Before a whole-look step (save, load, all back): the draft accepted or dropped (False: not now)."""
        if not self.draft:
            return True
        got = messagebox.askyesnocancel(TITLE, "Put your %d changes on the editor first? (No drops them.)"
                                        % len(self.draft), parent=self)
        if got is None:
            return False
        self.accept() if got else self.discard()
        return True

    def back_all(self):
        if not self._draft_first():
            return
        if not self.look.data["pieces"]:
            messagebox.showinfo(TITLE, "The editor looks as it comes: nothing was changed.", parent=self)
            return
        if messagebox.askyesno(TITLE, "Every button, tick and label back where the editor puts it, with its own "
                                      "words? (Undo takes it back step by step.)", parent=self):
            self.look.back_all()

    def save_as(self):
        if not self._draft_first():
            return
        p = filedialog.asksaveasfilename(parent=self, title="Save my look", defaultextension=".json",
                                         initialfile="CampaignEditor_look.json", filetypes=(("Look", "*.json"),))
        if p:
            LK.save(self.look.data, p)

    def load_from(self):
        if not self._draft_first():
            return
        p = filedialog.askopenfilename(parent=self, title="Load a look", filetypes=(("Look", "*.json"),))
        if not p:
            return
        got = LK.load(p)
        self.look.back_all()
        for key in got["order"] + [k for k in got["pieces"] if k not in got["order"]]:
            self.look.change_key(key, **got["pieces"][key])


def open_board(app):
    """The board (one per editor), brought to the front when it is open."""
    b = getattr(app, "_layout_board", None)
    try:
        if b is not None and b.winfo_exists():
            b.deiconify()
            b.lift()
            return b
    except tk.TclError:
        pass
    b = app._layout_board = LayoutBoard(app)
    return b


__all__ = ["LayoutBoard", "open_board", "snap", "pieces_of", "WINDOWS"]
