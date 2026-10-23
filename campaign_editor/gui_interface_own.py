"""Interface: a piece's picture of one's own (the user, 2026-10-17: 'loading our own elements, a library of them, or
Replace on the right click - and it must still do what it did before: pull a knot of the web and the web follows').

Replace picture... - each state of the piece (normal, mouse over, pressed...) takes a picture file of any kind or a
picture of the Picture library; the files go into one new TGA under data/menu/ce_ui/ (the engine reads TGA only) with
a region per state, and the piece gets its own copy of its UI object - what it does (its identifier, the page it
opens, its words, tooltip) stays, as the engine keeps behaviour and pictures apart (rules.md 'Menu layout'). 'Every
piece drawn with this picture' changes the shared object instead. Back to the game's picture is the opposite.

The Picture library: every picture region of the layout file's sheets (the game's own pieces) and the modder's own
pictures, kept in the editor's own folder (CampaignEditor_interface) for every mod.

A message box (the 'Exit program?' box: UIP_ERROR_DIALOG) or a frame (UIP_BORDER) never shows a picture of its own:
the game draws the menus' shared frame data/menu/border_4pix_black_gold2.tga there (menudraw.FRAME_ONLY), so Replace
picture on one changes that frame - for every message box, text box, list, drop-down and border of the menus."""

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import lnt as L
from . import theme

TITLE = "Interface"
THUMB = 72                                                   # a library picture's square, in screen pixels
PICTURES = (("Pictures", "*.png *.tga *.jpg *.jpeg *.bmp *.dds *.gif *.webp"), ("Every file", "*.*"))


def library_dir():
    """The editor's own folder of the modder's interface pictures (beside its settings), for every mod."""
    from . import log
    home = log.home()
    return os.path.join(home, log.SHORT + "_interface") if home else None


def own_library():
    """[file] of the modder's own pictures in the library, by name."""
    d = library_dir()
    if not d or not os.path.isdir(d):
        return []
    return sorted((os.path.join(d, n) for n in os.listdir(d) if not n.startswith(".")), key=str.lower)


def add_to_library(files):
    """The pictures copied into the library (a name taken gets a number); returns the new files."""
    d = library_dir()
    if not d:
        return []
    os.makedirs(d, exist_ok=True)
    out = []
    for f in files:
        stem, ext = os.path.splitext(os.path.basename(f))
        dest, n = os.path.join(d, stem + ext), 2
        while os.path.exists(dest):
            dest, n = os.path.join(d, "%s_%d%s" % (stem, n, ext)), n + 1
        shutil.copyfile(f, dest)
        out.append(dest)
    return out


def piece_size(panel, x):
    """(w, h) the piece is drawn at now in layout pixels (its own size, else its picture's)."""
    art = panel.doc.art(x)
    w = x["width"] or (art[1][2] - art[1][0] + 1 if art else 64)
    h = x["height"] or (art[1][3] - art[1][1] + 1 if art else 32)
    return max(1, int(w)), max(1, int(h))


def region_picture(panel, page, region):
    """A region of a sheet as a Pillow picture (None when its sheet is not found)."""
    tex = panel.doc.textures().get(page)
    box = tex and tex["regions"].get(region)
    sheet = panel._texture(page, tex["path"]) if tex else None
    if sheet is None or box is None:
        return None
    return sheet.crop((box[0], box[1], box[2] + 1, box[3] + 1))


def source_picture(panel, src):
    """The picture a state is given: ('file', path) or ('region', page, region)."""
    try:
        if src[0] == "file":
            from PIL import Image
            return Image.open(src[1]).convert("RGBA")
        return region_picture(panel, src[1], src[2])
    except Exception:
        return None


def thumb(im, size=THUMB):
    from PIL import Image, ImageTk
    im = im.copy()
    im.thumbnail((size, size), Image.LANCZOS)
    back = Image.new("RGBA", (size, size), (40, 40, 40, 255))
    back.alpha_composite(im.convert("RGBA"), ((size - im.width) // 2, (size - im.height) // 2))
    return ImageTk.PhotoImage(back)


def make_own(panel, x, sources, size, shared=False):
    """The piece given its pictures: sources {state: ('file', path) | ('region', page, region)}. The files are
    fitted into size and stacked in one new TGA (kept for Apply), the regions used as they are. Returns the object
    used, or raises LntError / OSError."""
    doc = panel.doc
    stem = doc.own_stem(panel.page, x["index"])
    files = [st for st in sources if sources[st][0] == "file"]
    pics, texture = {}, None
    if files:
        from PIL import Image
        rel = "%s\\%s.tga" % (L.OWN_FOLDER, stem)
        w, h = size
        data = L.own_picture_file([Image.open(sources[st][1]) for st in files], size)
        texture = (rel, {"%s_%s" % (stem, st): (0, i * h, w - 1, (i + 1) * h - 1) for i, st in enumerate(files)})
        panel.own_files[panel.own_path(rel)] = data
        panel._tex.pop(rel, None)
        pics.update({st: (rel, "%s_%s" % (stem, st)) for st in files})
    pics.update({st: src[1:] for st, src in sources.items() if src[0] == "region"})
    obj, _ = doc.own_picture(panel.page, x["index"], {st: pics[st] for st in sources}, shared=shared,
                             texture=texture, stem=stem)
    return obj


def frame_only(x):
    """Whether the game draws the menus' shared frame for this piece, never a picture of its own."""
    from . import menudraw as MD
    return bool(x) and (x["identifier"] or "").upper() in MD.FRAME_ONLY


def frame_box(panel, x):
    """(w, h) the game draws the frame at for this piece: a message box from 8 px outside it, a frame on it."""
    w, h = piece_size(panel, x)
    return (w + 16, h + 16) if (x["identifier"] or "").upper() != "UIP_BORDER" else (w, h)


def frame_users(panel):
    """How many pieces of the layout the game draws with the shared frame (message boxes, frames, text boxes,
    lists, drop-downs)."""
    from . import menudraw as MD
    doc = panel.doc
    return sum(1 for page in doc.pages() for x in doc.pieces(page)
               if MD.kind(x["identifier"], x["object"], doc.art(x) is not None) in
               ("border", "dialog", "textbox", "list", "dropdown"))


def take_frame(panel, x, im):
    """The shared frame made from a picture of this piece's whole box; waits for Apply changes. False without
    Pillow or a picture."""
    from . import menudraw as MD
    if im is None:
        return False
    old = panel._part(MD.FRAME)
    sheet = MD.frame_sheet(im, frame_box(panel, x), old=old)
    panel.set_frame(L.own_picture_file([sheet], sheet.size))
    after_change(panel, "The menus' frame is the new picture now (%s and every message box, text box, list, "
                        "drop-down and border). Preview, then Apply changes." % x["name"])
    return True


def ask_frame(panel):
    """Replace picture on a message box / frame: the game draws the menus' shared frame there, so the frame changes
    (said first, with how many pieces show it)."""
    x = panel.current()
    if not x:
        return None
    try:
        import PIL  # noqa: F401
    except ImportError:
        messagebox.showinfo(TITLE, "Own pictures need Pillow (the editor's exe has it).", parent=panel)
        return None
    from . import menudraw as MD
    w, h = frame_box(panel, x)
    if not messagebox.askokcancel(TITLE, (
            "%s is %s. The game never draws a picture of its own for it: it draws the menus' shared frame, "
            "data/menu/%s, around it (that is why a new picture of the piece changed nothing in the game).\n\n"
            "Pick a picture of the whole box as it should look (%d x %d pixels here; any size is fitted): its "
            "corners and edges become the frame's, its middle the inside. The same frame is drawn for every "
            "message box, text box, list, drop-down and border of the menus (%d pieces in this layout file).\n\n"
            "Go on?") % (x["name"], kind_words(x), MD.FRAME, w, h, frame_users(panel)), parent=panel):
        return None
    p = filedialog.askopenfilename(parent=panel, title="A picture of the whole box", filetypes=PICTURES)
    if not p:
        return None
    if not take_frame(panel, x, source_picture(panel, ("file", p))):
        messagebox.showerror(TITLE, "That picture could not be read.", parent=panel)
        return None
    return p


def frame_back(panel):
    """The game's own frame again: a new one waiting is dropped; one the mod has already goes back to the game's at
    Apply changes."""
    x = panel.current()
    panel.set_frame(b"" if panel.frame is None or (panel.frame and panel.own_frame()) else None)
    after_change(panel, "The menus' frame is the game's again%s. Preview, then Apply changes." % (
        " (%s and the rest)" % x["name"] if x else ""))


def ask_picture(panel):
    """Replace picture...: each state its picture (a file or the library), the size, this piece or every one."""
    x = panel.current()
    if not x:
        return None
    if frame_only(x):
        return ask_frame(panel)
    try:
        import PIL  # noqa: F401
    except ImportError:
        messagebox.showinfo(TITLE, "Own pictures need Pillow (the editor's exe has it).", parent=panel)
        return None
    doc = panel.doc
    states = doc.states_of(x)
    base = doc.game_object(x["object"]) or x["object"]
    users = [u for u in doc.users(base)] if base in doc.objects() else []
    d = tk.Toplevel(panel)
    d.title("%s - its own picture" % x["name"])
    d.transient(panel.winfo_toplevel())
    f = ttk.Frame(d, padding=10)
    f.pack(fill="both", expand=True)
    does = [kind_words(x)]
    if x["menu_id"]:
        does.append("opens the page %s" % x["menu_id"])
    if x["text"]:
        does.append("shows the words %s" % x["text"])
    ttk.Label(f, wraplength=520, justify="left", foreground=theme.palette()["muted"], text=(
        "What it does stays: %s. Only its picture changes - a picture file of any kind (written as a TGA under "
        "data/menu/%s, the game reads TGA only) or one from the Picture library, for each of its states."
        % (", ".join(does), L.OWN_FOLDER))).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))
    w0, h0 = piece_size(panel, x)
    sv = (tk.IntVar(value=w0), tk.IntVar(value=h0))
    sz = ttk.Frame(f)
    sz.grid(row=1, column=0, columnspan=5, sticky="w", pady=(0, 6))
    ttk.Label(sz, text="Its size (pixels):").pack(side="left")
    for v in sv:
        ttk.Spinbox(sz, from_=1, to=4096, textvariable=v, width=6).pack(side="left", padx=(4, 0))
    ttk.Label(sz, text="(as it is drawn now; a picture file is fitted into it)",
              foreground=theme.palette()["muted"]).pack(side="left", padx=(6, 0))
    chosen, shown, imgs = {}, {}, {}
    o = doc.objects().get(x["object"] or "")

    def show(st):
        src = chosen.get(st)
        if src is None and o and st in o["regions"]:
            src = ("region",) + tuple(o["regions"][st])
        im = source_picture(panel, src) if src else None
        imgs[st] = thumb(im) if im is not None else None
        shown[st][0].configure(image=imgs[st] or "", text="" if imgs[st] else "(none)")
        shown[st][1].configure(text="new: " + describe(chosen[st]) if st in chosen else "the one it has now")

    def pick_file(st):
        p = filedialog.askopenfilename(parent=d, title="A picture for '%s'" % L.STATES.get(st, st),
                                       filetypes=PICTURES)
        if p:
            chosen[st] = ("file", p)
            show(st)

    def pick_library(st):
        def got(src):
            chosen[st] = src
            show(st)
        Library(panel, on_pick=got, parent=d)

    for r, st in enumerate(states, start=2):
        ttk.Label(f, text="%s (%s)" % (L.STATES.get(st, st), st)).grid(row=r, column=0, sticky="w", padx=(0, 8))
        pic = ttk.Label(f)
        pic.grid(row=r, column=1, pady=2)
        words = ttk.Label(f, foreground=theme.palette()["muted"], width=34)
        words.grid(row=r, column=2, sticky="w", padx=6)
        ttk.Button(f, text="Picture file...", command=lambda s=st: pick_file(s)).grid(row=r, column=3)
        ttk.Button(f, text="From the library...", command=lambda s=st: pick_library(s)).grid(row=r, column=4,
                                                                                          padx=(4, 0))
        shown[st] = (pic, words)
        show(st)
    row = len(states) + 2
    if len(states) > 1:
        def same_for_all():
            first = next((chosen[s] for s in states if s in chosen), None)
            if first is None:
                messagebox.showinfo(TITLE, "Pick a picture for one state first.", parent=d)
                return
            for s in states:
                chosen[s] = first
                show(s)
        ttk.Button(f, text="The same picture for every state", command=same_for_all).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(4, 0))
        row += 1
    v_shared = tk.BooleanVar(value=False)
    many = len(users) > 1
    ttk.Radiobutton(f, text="Only this piece", variable=v_shared, value=False).grid(
        row=row, column=0, columnspan=5, sticky="w", pady=(8, 0))
    rb = ttk.Radiobutton(f, variable=v_shared, value=True, text=(
        "Every piece drawn with this picture (%d: %s%s)" % (len(users), ", ".join(n for _, n in users[:4]),
                                                            " ..." if len(users) > 4 else "")
        if many else "Every piece drawn with this picture (only this one)"))
    rb.grid(row=row + 1, column=0, columnspan=5, sticky="w")
    if not many:
        rb.state(["disabled"])
    v_keep = tk.BooleanVar(value=True)
    ttk.Checkbutton(f, text="Keep the picture files in my library too (for every mod)", variable=v_keep).grid(
        row=row + 2, column=0, columnspan=5, sticky="w", pady=(4, 0))

    def ok(*_):
        if not chosen:
            d.destroy()
            return
        try:
            size = (max(1, int(sv[0].get())), max(1, int(sv[1].get())))
        except (tk.TclError, ValueError):
            messagebox.showerror(TITLE, "The size is two whole numbers.", parent=d)
            return
        want = {st: chosen.get(st) or ("region",) + tuple(o["regions"][st]) for st in states
                if st in chosen or (o and st in o["regions"])}
        files = sorted({src[1] for src in want.values() if src[0] == "file"})
        panel._remember()
        try:
            obj = make_own(panel, x, want, size, shared=v_shared.get() and many)
        except (L.LntError, OSError, ValueError) as e:
            panel._restore(panel.undo.pop())
            messagebox.showerror(TITLE, "The picture could not be taken: %s" % e, parent=d)
            return
        lib = library_dir()
        if v_keep.get() and files and lib:
            try:
                add_to_library([p for p in files if os.path.dirname(os.path.abspath(p)) != os.path.abspath(lib)])
            except OSError:
                pass
        d.destroy()
        after_change(panel, "%s: drawn with %s now - what it does stays. Preview, then Apply changes." % (
            x["name"], obj))
    foot = ttk.Frame(f)
    foot.grid(row=row + 3, column=0, columnspan=5, sticky="we", pady=(10, 0))
    ttk.Button(foot, text="Cancel", command=d.destroy).pack(side="right")
    ttk.Button(foot, text="OK", command=ok).pack(side="right", padx=(0, theme.BUTTON_GAP))
    d.bind("<Escape>", lambda e: d.destroy())
    return d


def kind_words(x):
    from .gui_interface import KINDS
    return KINDS.get(x["identifier"], x["identifier"] or "a piece")


def describe(src):
    return os.path.basename(src[1]) if src[0] == "file" else "%s (%s)" % (src[2], os.path.basename(
        src[1].replace("\\", "/")))


def after_change(panel, words):
    panel._pics.clear()
    panel.fill_pieces()
    panel.fill_form()
    panel.draw()
    status = getattr(panel.app, "status", None)
    if status is not None:
        status.set(words)


def back_to_game(panel):
    """The opposite of Replace picture: the game's picture again (the own one taken out once nothing shows it)."""
    x = panel.current()
    if not x or panel.doc.game_object(x["object"]) is None:
        return
    panel._remember()
    try:
        panel.doc.back_to_game(panel.page, x["index"])
    except L.LntError as e:
        panel._restore(panel.undo.pop())
        messagebox.showerror(TITLE, str(e), parent=panel)
        return
    after_change(panel, "%s: the game's picture again. Preview, then Apply changes." % x["name"])


class Library(tk.Toplevel):
    """The Picture library: the game's pieces (every region of the layout file's sheets, one sheet at a time) and
    my own pictures. A click picks one - for the state being chosen (on_pick), else for the piece picked on the
    screen (every state the same)."""

    def __init__(self, panel, on_pick=None, parent=None):
        super().__init__(parent or panel)
        self.panel, self.on_pick, self._imgs = panel, on_pick, []
        self.title("Picture library")
        self.transient((parent or panel).winfo_toplevel())
        self.geometry("760x560")
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(fill="x")
        textures = panel.doc.textures() if panel.doc else {}
        self.sheets = ["My own pictures"] + sorted(textures, key=str.lower)
        game = [t for t in self.sheets[1:] if not t.replace("/", "\\").lower().startswith(L.OWN_FOLDER + "\\")]
        self.v_sheet = tk.StringVar(value=(game or self.sheets)[0])         # the game's pieces first
        ttk.Label(bar, text="Show:").pack(side="left")
        cb = ttk.Combobox(bar, textvariable=self.v_sheet, values=self.sheets, state="readonly", width=40)
        cb.pack(side="left", padx=(4, 0))
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill())
        self.b_add = ttk.Button(bar, text="Add pictures...", command=self.add)
        self.b_add.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        self.lbl = ttk.Label(bar, foreground=theme.palette()["muted"])
        self.lbl.pack(side="left", padx=(theme.BUTTON_GAP * 2, 0))
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(body, highlightthickness=0, background=theme.palette().get("bg", "#202020"))
        sb = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.fill())
        for seq, way in (("<MouseWheel>", None), ("<Button-4>", -1), ("<Button-5>", 1)):
            self.canvas.bind(seq, lambda e, w=way: self.canvas.yview_scroll(
                w if w is not None else (-1 if e.delta > 0 else 1), "units"))
        self.bind("<Escape>", lambda e: self.destroy())
        self.fill()

    def items(self):
        """[(name, picture, source)] of the sheet on show."""
        sheet = self.v_sheet.get()
        out = []
        if sheet == self.sheets[0]:
            for p in own_library():
                im = source_picture(self.panel, ("file", p))
                if im is not None:
                    out.append((os.path.basename(p), im, ("file", p)))
            return out
        for region in sorted(self.panel.doc.textures().get(sheet, {}).get("regions", {}), key=str.lower):
            im = region_picture(self.panel, sheet, region)
            if im is not None:
                out.append((region, im, ("region", sheet, region)))
        return out

    def fill(self):
        c = self.canvas
        c.delete("all")
        self._imgs = []
        own = self.v_sheet.get() == self.sheets[0]
        self.b_add.state(["!disabled"] if own else ["disabled"])
        got = self.items()
        self.lbl.configure(text="%d picture(s)%s - a click picks one" % (len(got), (
            " (your own, for every mod: %s)" % library_dir()) if own else ""))
        if not got and not own:
            c.create_text(12, 12, anchor="nw", fill="#b0b0b0", text="This sheet's picture file is not found "
                          "(Medieval II keeps them in its .pack files until the game is unpacked).")
        cell = THUMB + 24
        cols = max(1, (c.winfo_width() - 8) // cell)
        for i, (name, im, src) in enumerate(got):
            x0, y0 = 8 + (i % cols) * cell, 8 + (i // cols) * (cell + 8)
            ph = thumb(im)
            self._imgs.append(ph)
            tag = "p%d" % i
            c.create_image(x0 + 12, y0, image=ph, anchor="nw", tags=(tag,))
            c.create_text(x0 + cell / 2, y0 + THUMB + 4, text=name[:16], anchor="n", fill="#d0d0d0",
                          font=("", 8), tags=(tag,))
            c.tag_bind(tag, "<Button-1>", lambda e, s=src: self.pick(s))
            if own:
                c.tag_bind(tag, "<Button-3>", lambda e, p=src[1]: self.forget(e, p))
        rows = (len(got) + cols - 1) // cols
        c.configure(scrollregion=(0, 0, cols * cell + 16, rows * (cell + 8) + 16))

    def add(self):
        files = filedialog.askopenfilenames(parent=self, title="Pictures for my library", filetypes=PICTURES)
        if files:
            add_to_library(files)
            self.fill()

    def forget(self, e, path):
        m = tk.Menu(self, tearoff=False)
        m.add_command(label="Take %s out of my library" % os.path.basename(path),
                      command=lambda: (os.remove(path), self.fill()))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def pick(self, src):
        if self.on_pick is not None:
            self.destroy()
            self.on_pick(src)
            return
        panel = self.panel
        x = panel.current()
        if not x:
            messagebox.showinfo(TITLE, "Pick a piece on the screen first.", parent=self)
            return
        if frame_only(x):                            # a message box / frame: the menus' shared frame
            self.destroy()
            if not take_frame(panel, x, source_picture(panel, src)):
                messagebox.showerror(TITLE, "That picture could not be read.", parent=panel)
            return
        states = panel.doc.states_of(x)
        panel._remember()
        try:
            obj = make_own(panel, x, {st: src for st in states}, piece_size(panel, x))
        except (L.LntError, OSError, ValueError) as e:
            panel._restore(panel.undo.pop())
            messagebox.showerror(TITLE, "The picture could not be taken: %s" % e, parent=self)
            return
        after_change(panel, "%s: drawn with %s now (every state) - what it does stays. Preview, then Apply "
                            "changes." % (x["name"], obj))


__all__ = ["ask_picture", "ask_frame", "frame_back", "frame_only", "frame_box", "take_frame", "back_to_game", "Library", "make_own", "library_dir", "add_to_library", "own_library"]
