"""The editor's own look put on its windows, and the mode that edits it (look.py holds the files).

Every widget is seen once, when it first shows (one <Map> binding for all of them - no window needs code of its
own): its English words kept, the language picked in Settings put on, then the modder's own changes (new words,
hover text, width, hidden, moved). Tools > Edit the editor's look: a click picks a button / tick / label (yellow
frame), the left button drags it before or after any other piece of any bar, its right click renames it, gives it
a hover text, a width, hides it, takes it back; a small bar holds Undo, the hidden pieces, Back to how it was,
Save / Load a look.

Moving: Tk never gives a widget another parent, so a piece dropped into a bar inside its own parent's part of the
window moves itself (pack / the wrapping bars of gui_util.flow; a table swaps two pieces); dropped anywhere else a
copy of it stands there - its command, its variable, its bindings the same - while the piece itself is hidden and
the copy follows its state (greyed, words) twice a second."""

import copy
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import look as LK

TITLE = "The editor's look"
PIECES = {"TButton", "TCheckbutton", "TRadiobutton", "TLabel", "TMenubutton", "TCombobox", "TEntry", "TSpinbox",
          "Button", "Checkbutton", "Radiobutton", "Label", "Menubutton", "TScale", "Scale", "Entry", "Spinbox"}
WITH_TEXT = {"TButton", "TCheckbutton", "TRadiobutton", "TLabel", "TMenubutton", "Button", "Checkbutton",
             "Radiobutton", "Label", "Menubutton", "TLabelframe", "Labelframe"}
YELLOW = "#ffd400"
CLONES = {"TButton": ttk.Button, "TCheckbutton": ttk.Checkbutton, "TRadiobutton": ttk.Radiobutton,
          "TLabel": ttk.Label, "TMenubutton": ttk.Menubutton, "TCombobox": ttk.Combobox, "TEntry": ttk.Entry,
          "TSpinbox": ttk.Spinbox, "TScale": ttk.Scale, "Button": tk.Button, "Checkbutton": tk.Checkbutton,
          "Radiobutton": tk.Radiobutton, "Label": tk.Label, "Menubutton": tk.Menubutton, "Entry": tk.Entry,
          "Spinbox": tk.Spinbox, "Scale": tk.Scale}
TAG = "CELookEdit"


class Look:
    """The look of one editor run: the file's changes, the language's words, the widgets seen."""
    _styles = 0                                   # pieces' own ttk styles made (each a new name: CE<n>.<style>)

    def __init__(self, root):
        self.root = root
        self.own = LK.load()                      # the modder's own changes (CampaignEditor_look.json)
        self.snips = LK.snippets()                # sets of changes switched on / off, under the own ones
        self.data = LK.layered(self.own, self.snips)   # the look in force
        self.words = {}
        self.seen_words = set()                   # English words seen in the windows (for 'Words to translate')
        self.by_key = {}                          # key -> widget (the newest of that key)
        self.counts = {}                          # (window, base key) -> pieces of it seen
        self.clones = {}                          # str(original) -> its copy standing where it was dropped
        self.waiting = []                         # keys moved whose target has not shown yet
        self.editing, self.picked, self.undo, self.redo = False, None, [], []
        self.on_change = []                       # called with the key after every change (the layout board)
        self._frame, self._mark, self._bar, self._drag = [], None, None, None
        from . import settings
        self.set_language(settings.get("language") or "")
        root.bind_all("<Map>", self._mapped, add="+")
        root.bind_class("Menu", "<Map>", self._menu_mapped, add="+")
        self._sync()

    # ---- the language ----
    def set_language(self, name):
        """The words of a language put on every window now open and every one opened later ('' = English)."""
        path = LK.languages().get(name) if name else None
        got = LK.read_language(path) if path else None
        self.words = got["words"] if got else {}
        self.language = got["language"] if got else ""
        for w in list(self.by_key.values()):
            try:
                if w.winfo_exists():
                    self._words_on(w)
            except tk.TclError:
                pass
        for w in all_widgets(self.root):                 # the windows' titles, the tabs' words
            try:
                if isinstance(w, (tk.Tk, tk.Toplevel)) and hasattr(w, "_look_title"):
                    self._title(w)
                elif hasattr(w, "_look_tabs"):
                    self._words_on(w)
            except tk.TclError:
                pass

    def word(self, text):
        """The words shown for English words: the language's, else the words themselves."""
        if not isinstance(text, str) or not text:
            return text
        self.seen_words.add(text)
        return self.words.get(text, text)

    # ---- seeing a widget ----
    def _mapped(self, e):
        w = e.widget
        if not isinstance(w, tk.Misc) or getattr(w, "_look_skip", False):
            return
        try:
            if isinstance(w, (tk.Tk, tk.Toplevel)):
                self._title(w)
                return
            if getattr(w, "_look_seen", False):
                self._keep(w)
                return
            w._look_seen = True
            self._first(w)
        except tk.TclError:
            pass

    def _title(self, top):
        if not hasattr(top, "_look_title"):
            top._look_title = top.title()
        t = self.word(top._look_title)
        if t != top.title():
            top.title(t)

    def _first(self, w):
        cls = w.winfo_class()
        if cls in WITH_TEXT:
            w._look_text = str(w.cget("text"))
            try:
                w._look_width0 = w.cget("width")
            except tk.TclError:
                pass
        if cls == "TNotebook":
            w._look_tabs = {}
        if cls == "Treeview":
            w._look_heads = {}
        key = piece_key(self, w)
        w._look_key = key
        self.by_key[key] = w
        self._words_on(w)
        if self.editing:
            self._tag(w, True)
        if key in self.data["pieces"]:
            self._put_on(w)
        self._try_waiting()

    def _keep(self, w):
        """Shown again (the code packed it anew): a hidden or moved piece stays where the look put it."""
        if self.editing:
            self._tag(w, True)
        e = self.data["pieces"].get(getattr(w, "_look_key", None), {})
        if (e.get("hidden") or str(w) in self.clones) and w.winfo_manager():
            self._forget(w)
        elif "xy" in e and not e.get("hidden") and w.winfo_manager() != "place":
            self._free(w, e)                           # the code packed it anew: free where the look put it
        if w.winfo_class() == "TNotebook":
            self._words_on(w)

    def _words_on(self, w):
        cls = w.winfo_class()
        e = self.data["pieces"].get(getattr(w, "_look_key", None), {})
        if hasattr(w, "_look_text"):
            want = LK.shown_words(e, self.word(w._look_text))
            cur = str(w.cget("text"))
            shown = getattr(w, "_look_shown", w._look_text)
            if cur == shown and want != cur:          # never over words the code put there since
                w.configure(text=want)
            w._look_shown = want if cur == shown else cur
        if cls == "TNotebook":
            for tab in w.tabs():
                orig = w._look_tabs.setdefault(tab, str(w.tab(tab, "text")))
                t = self.word(orig)
                if str(w.tab(tab, "text")) != t:
                    w.tab(tab, text=t)
        if cls == "Treeview":
            for col in ("#0",) + tuple(w.cget("columns") or ()):
                try:
                    orig = w._look_heads.setdefault(col, str(w.heading(col, "text")))
                    if orig and str(w.heading(col, "text")) != self.word(orig):
                        w.heading(col, text=self.word(orig))
                except tk.TclError:
                    pass

    def _menu_mapped(self, e):
        m = e.widget
        try:
            end = m.index("end")
        except tk.TclError:
            return
        if end is None:
            return
        orig = getattr(m, "_look_labels", None)
        if orig is None:
            orig = m._look_labels = {}
        for i in range(end + 1):
            try:
                if m.type(i) not in ("command", "checkbutton", "radiobutton", "cascade"):
                    continue
                label = orig.setdefault(i, str(m.entrycget(i, "label")))
                t = self.word(label)
                if str(m.entrycget(i, "label")) != t:
                    m.entryconfigure(i, label=t)
            except tk.TclError:
                pass

    # ---- putting a piece's change on ----
    def _put_on(self, w):
        e = self.data["pieces"].get(w._look_key, {})
        self._words_on(w)
        self._paint(w, e)
        if "width" in e:
            try:
                w.configure(width=e["width"])
            except tk.TclError:
                pass
        if e.get("size") and "xy" not in e and not e.get("hidden"):
            self._home(w)
            self._size_on(w, e["size"])
        if e.get("tip"):
            w._look_tip = e["tip"]
            if not getattr(w, "_look_tipped", False):
                w._look_tipped = True
                from .gui_util import Tip
                Tip(w, lambda: getattr(w, "_look_tip", ""))
        if e.get("hidden"):
            self._home(w)
            self._forget(w)
        elif "xy" in e:
            self._home(w)
            self._free(w, e)
        elif "to" in e:
            if not self._move_now(w, e["to"], e.get("where", "after")):
                if w._look_key not in self.waiting:
                    self.waiting.append(w._look_key)

    def _paint(self, w, e):
        """The piece's own colours and font (a ttk piece gets a style of its own built on the one it has, so the
        theme's look stays under it; a tk one its options); none asked: nothing."""
        bg, fg = e.get("bg"), e.get("fg")
        if not (bg or fg or e.get("font")):
            return
        from tkinter import font as tkfont
        try:
            if isinstance(w, ttk.Widget):
                st = ttk.Style(w)
                if not hasattr(w, "_look_style0"):
                    w._look_style0 = str(w.cget("style"))
                base = w._look_style0 or w.winfo_class()
                now = tkfont.Font(root=w, font=st.lookup(base, "font") or "TkDefaultFont").actual()
                Look._styles += 1
                name = "CE%d.%s" % (Look._styles, base)
                kw, mp = {}, {}
                if bg:
                    kw.update(background=bg, fieldbackground=bg)
                    deep = LK.deeper(_rgb(w, bg))
                    mp["background"] = [("pressed", deep), ("active", deep)]
                if fg:
                    kw["foreground"] = fg
                    mp["foreground"] = [("active", fg)]
                font = LK.font_of(e.get("font"), (now["family"], now["size"]))
                if font:
                    kw["font"] = font
                st.configure(name, **kw)
                if mp:
                    st.map(name, **mp)
                w.configure(style=name)
            else:
                opts = [o for o in ("background", "foreground", "activebackground", "activeforeground", "font")
                        if o in w.keys()]
                if not hasattr(w, "_look_paint0"):
                    w._look_paint0 = {o: w.cget(o) for o in opts}
                now = tkfont.Font(root=w, font=w._look_paint0.get("font") or "TkDefaultFont").actual()
                kw = {}
                if bg:
                    kw.update(background=bg, activebackground=LK.deeper(_rgb(w, bg)))
                if fg:
                    kw.update(foreground=fg, activeforeground=fg)
                font = LK.font_of(e.get("font"), (now["family"], now["size"]))
                if font:
                    kw["font"] = font
                w.configure(**{k: v for k, v in kw.items() if k in opts})
                from . import theme
                theme.leave_alone(w)                      # the dark look never recolours the modder's colours
        except tk.TclError:
            pass

    def _unpaint(self, w):
        """The piece's own colours and font taken off (the theme's again)."""
        try:
            if hasattr(w, "_look_style0"):
                w.configure(style=w._look_style0)
                del w._look_style0
            if hasattr(w, "_look_paint0"):
                w.configure(**w._look_paint0)
                del w._look_paint0
                from . import theme
                theme._state.get("keep", set()).discard(str(w))
        except tk.TclError:
            pass

    def _free(self, w, e):
        """The piece free at x, y of its own box (up 0) or of the box `up` boxes around it (a copy stands there: Tk
        gives a widget no other parent), its size kept or the look's."""
        x, y = (int(v) for v in e["xy"][:2])
        kw = dict(x=x, y=y)
        if e.get("size"):
            kw.update(width=int(e["size"][0]), height=int(e["size"][1]))
        box, up = w.master, int(e.get("up") or 0)
        for _ in range(up):
            if isinstance(box, (tk.Tk, tk.Toplevel)) or box.master is None:
                break
            box = box.master
        self._forget(w)
        piece = w
        if box is not w.master:
            old = self.clones.pop(str(w), None)
            if old is not None:
                old.destroy()
            piece = make_copy(w, box)
            self.clones[str(w)] = piece
        piece.place(in_=box, **kw)
        piece.lift()

    def _size_on(self, w, size):
        """A piece in a row made width x height pixels: wider / taller by inner padding, narrower by its width in
        letters (Tk sizes a button by its words); a wrapping bar (gui_util.flow) gives it the size itself."""
        want_w, want_h = int(size[0]), int(size[1])
        m = w.master
        if getattr(m, "_flow_items", None) is not None and any(it[0] is w for it in m._flow_items):
            w._look_size = (want_w, want_h)
            m._flow_reflow(again=True)
            return
        req_w, req_h = w.winfo_reqwidth(), w.winfo_reqheight()
        if want_w < req_w and "width" in w.keys():
            try:
                from tkinter import font as tkfont
                f = tkfont.nametofont(str(w.cget("font")) or "TkDefaultFont")
                letters = max(1, want_w // max(f.measure("0"), 1))
            except (tk.TclError, ValueError):
                letters = max(1, want_w // 7)
            try:
                w.configure(width=letters)
            except tk.TclError:
                pass
        pad = dict(ipadx=max(0, (want_w - req_w) // 2), ipady=max(0, (want_h - req_h) // 2))
        mgr = w.winfo_manager()
        try:
            if mgr == "pack":
                w.pack_configure(**pad)
            elif mgr == "grid":
                w.grid_configure(**pad)
        except tk.TclError:
            pass

    def _try_waiting(self):
        for key in list(self.waiting):
            w = self.by_key.get(key)
            e = self.data["pieces"].get(key, {})
            if w is None or "to" not in e:
                self.waiting.remove(key)
            elif e["to"] in self.by_key and self._move_now(w, e["to"], e.get("where", "after")):
                self.waiting.remove(key)

    def _move_now(self, w, to_key, where):
        t = self.by_key.get(to_key)
        try:
            if t is None or not t.winfo_exists() or not w.winfo_exists() or not t.winfo_manager():
                return False
            return move(self, w, t, where) is None
        except tk.TclError:
            return False

    # ---- where a piece stands ----
    def _home(self, w):
        """Where the code put the piece, kept the first time the look moves or hides it."""
        if hasattr(w, "_look_home"):
            return
        m = w.master
        items = getattr(m, "_flow_items", None)
        if items is not None and any(it[0] is w for it in items):
            i = next(i for i, it in enumerate(items) if it[0] is w)
            if not hasattr(m, "_look_flow0"):              # the bar's own order, before the look changed it
                m._look_flow0 = [it[0] for it in items]
            w._look_home = ("flow", m, i, items[i])
            return
        mgr = w.winfo_manager()
        if mgr == "pack":
            info = dict(w.pack_info())
            slaves = info["in"].pack_slaves()
            i = slaves.index(w)
            if i + 1 < len(slaves):
                info["before"] = slaves[i + 1]
            w._look_home = ("pack", info)
        elif mgr == "grid":
            w._look_home = ("grid", dict(w.grid_info()))
        elif mgr == "place":
            w._look_home = ("place", dict(w.place_info()))
        else:
            w._look_home = ("none", None)

    def _forget(self, w):
        m = w.master
        items = getattr(m, "_flow_items", None)
        if items is not None:
            for it in list(items):
                if it[0] is w:
                    items.remove(it)
            w.place_forget()
            m._flow_reflow(again=True)
            return
        mgr = w.winfo_manager()
        if mgr == "pack":
            w.pack_forget()
        elif mgr == "grid":
            w.grid_remove()
        elif mgr == "place":
            w.place_forget()

    def back_home(self, w):
        """The piece where the code put it, with its own words and width (its copy, if any, taken away)."""
        clone = self.clones.pop(str(w), None)
        if clone is not None:
            try:
                clone.destroy()
            except tk.TclError:
                pass
        if hasattr(w, "_look_text"):
            cur, shown = str(w.cget("text")), getattr(w, "_look_shown", w._look_text)
            if cur == shown:
                w.configure(text=self.word(w._look_text))
            w._look_shown = self.word(w._look_text)
        if hasattr(w, "_look_width0"):
            try:
                w.configure(width=w._look_width0)
            except tk.TclError:
                pass
        w._look_tip = ""
        self._unpaint(w)
        if hasattr(w, "_look_size"):
            del w._look_size
        home = getattr(w, "_look_home", None)
        if home is None:
            return
        del w._look_home
        self._forget(w)
        kind = home[0]
        if kind == "flow":
            _, m, i, item = home
            order0 = getattr(m, "_look_flow0", [])
            if w in order0:                                # before the first piece that came after it
                later = order0[order0.index(w) + 1:]
                i = next((j for j, it in enumerate(m._flow_items) if it[0] in later), len(m._flow_items))
            m._flow_items.insert(min(i, len(m._flow_items)), item)
            m._flow_reflow(again=True)
        elif kind == "pack":
            info = home[1]
            before = info.pop("before", None)
            kw = {k: v for k, v in info.items() if k in ("in", "side", "fill", "expand", "padx", "pady", "ipadx",
                                                         "ipady", "anchor")}
            kw["in_"] = kw.pop("in")
            if before is not None and before.winfo_exists() and before.winfo_manager() == "pack":
                kw["before"] = before
            w.pack(**kw)
        elif kind == "grid":
            info = home[1]
            info["in_"] = info.pop("in")
            w.grid(**info)
        elif kind == "place":
            info = home[1]
            info["in_"] = info.pop("in")
            w.place(**{k: v for k, v in info.items() if v not in ("", None)})

    # ---- the copies standing where a piece was dropped ----
    def _sync(self):
        if self.words or self.data["pieces"]:          # words the code put back: the language's / the own again
            for w in list(self.by_key.values()):
                try:
                    if not hasattr(w, "_look_text") or not w.winfo_exists():
                        continue
                    cur = str(w.cget("text"))
                    if cur == getattr(w, "_look_shown", None):
                        continue
                    if cur == w._look_text:
                        want = self.data["pieces"].get(w._look_key, {}).get("text") or self.word(cur)
                    else:
                        want = self.words.get(cur, cur)
                    if want != cur:
                        w.configure(text=want)
                    w._look_shown = want
                except tk.TclError:
                    pass
        for path, clone in list(self.clones.items()):
            try:
                w = self.root.nametowidget(path)
                if not w.winfo_exists() or not clone.winfo_exists():
                    raise tk.TclError
                follow(w, clone)
            except (tk.TclError, KeyError):
                self.clones.pop(path, None)
        self.root.after(500, self._sync)

    # ---- changing (the edit mode and its menu call these) ----
    def change(self, w, **kw):
        """A piece's change (text / tip / width / hidden / to + where; None takes that part out), kept and put on."""
        self.change_key(w._look_key, **kw)

    def change_key(self, key, **kw):
        """change() by the piece's key: its widget need not be open (put on when its window opens)."""
        old = copy.deepcopy(self.data["pieces"].get(key))
        new = dict(old or {})
        for k, v in kw.items():
            if v is None:
                new.pop(k, None)
            else:
                new[k] = v
        self.undo.append((key, old))
        self.redo.clear()
        self._set(key, new)

    def _set(self, key, entry):
        base = LK.layered({"pieces": {}, "order": []}, self.snips)["pieces"].get(key) if self.snips else None
        LK.set_entry(self.own, key, LK.own_part(base, entry))
        LK.save(self.own)
        self.data = LK.layered(self.own, self.snips)
        w = self.by_key.get(key)
        try:
            if w is not None and w.winfo_exists():
                self.back_home(w)
                self._put_on(w)
        except tk.TclError:
            pass
        self._frame_on(self.picked)
        for f in list(self.on_change):
            f(key)

    def do_undo(self):
        if not self.undo:
            return False
        key, old = self.undo.pop()
        self.redo.append((key, copy.deepcopy(self.data["pieces"].get(key))))
        self._set(key, old)
        return True

    def do_redo(self):
        if not self.redo:
            return False
        key, new = self.redo.pop()
        self.undo.append((key, copy.deepcopy(self.data["pieces"].get(key))))
        self._set(key, new)
        return True

    def relayer(self):
        """The snippets read again (one switched on / off, added, deleted): every piece whose look changed put
        back and its new look put on."""
        old = self.data["pieces"]
        self.snips = LK.snippets()
        self.data = LK.layered(self.own, self.snips)
        new = self.data["pieces"]
        for key in [k for k in set(old) | set(new) if old.get(k) != new.get(k)]:
            w = self.by_key.get(key)
            try:
                if w is not None and w.winfo_exists():
                    self.back_home(w)
                    self._put_on(w)
            except tk.TclError:
                pass
            for f in list(self.on_change):
                f(key)
        self._try_waiting()

    def own_to_snippet(self, name):
        """The modder's own changes moved into a new snippet (switched on: nothing changes on the screen) -> its
        path or None."""
        path = LK.save_snippet(name, self.own, on=True)
        if path:
            self.own = {"pieces": {}, "order": []}
            LK.save(self.own)
            self.undo.clear()
            self.redo.clear()
            self.relayer()
        return path

    def back_all(self):
        """Every change of the look taken back (one Undo step each)."""
        for key in list(self.data["pieces"]):
            self.undo.append((key, copy.deepcopy(self.data["pieces"][key])))
            self._set(key, None)

    # ---- the edit mode ----
    def edit(self, on=True):
        self.editing = on
        for w in all_widgets(self.root):
            self._tag(w, on)
        if on:
            self._edit_bar()
        else:
            self.pick(None)
            if self._bar is not None and self._bar.winfo_exists():
                self._bar.destroy()
            self._bar = None

    def _tag(self, w, on):
        if getattr(w, "_look_skip", False):
            return
        try:
            tags = list(w.bindtags())
            if on and TAG not in tags:
                w.bindtags([TAG] + tags)
            elif not on and TAG in tags:
                tags.remove(TAG)
                w.bindtags(tags)
        except tk.TclError:
            pass

    def pick(self, w):
        self.picked = w
        self._frame_on(w)

    def _frame_on(self, w):
        for f in self._frame:
            try:
                f.destroy()
            except tk.TclError:
                pass
        self._frame = []
        if w is not None and str(w) in self.clones:           # moved where a copy stands: frame the copy
            w = self.clones[str(w)]
        if w is None or not w.winfo_exists() or not w.winfo_ismapped():
            return
        top = w.winfo_toplevel()
        for kw in (dict(relx=0, rely=0, relwidth=1, height=2), dict(relx=0, rely=1, relwidth=1, height=2, y=-2),
                   dict(relx=0, rely=0, relheight=1, width=2), dict(relx=1, rely=0, relheight=1, width=2, x=-2)):
            f = tk.Frame(top, background=YELLOW)
            f._look_skip = True
            f.place(in_=w, **kw)
            f.lift()
            self._frame.append(f)

    def _edit_bar(self):
        if self._bar is not None and self._bar.winfo_exists():
            self._bar.lift()
            return
        b = self._bar = tk.Toplevel(self.root)
        b._look_skip = True
        b.title(TITLE)
        b.attributes("-topmost", True)
        b.resizable(False, False)
        f = ttk.Frame(b, padding=8)
        f.pack(fill="both", expand=True)
        rows = [ttk.Label(f, wraplength=420, justify="left", text=(
            "Editing the editor's look: a click picks a button, tick or label (yellow frame); drag it with the left "
            "button before or after any other piece, in any bar; its right click renames it, gives it a hover "
            "text, a width, hides it or takes it back. Kept for every start (CampaignEditor_look.json)."))]
        row = ttk.Frame(f)
        rows.append(row)
        for text, cmd in (("Undo", self.do_undo), ("Hidden pieces...", self.hidden_window),
                          ("Back to how it was", self._ask_back_all), ("Save my look...", self.save_as),
                          ("Load a look...", self.load_from), ("Done", lambda: self.edit(False))):
            ttk.Button(row, text=text, command=cmd).pack(side="left", padx=(0, 4))
        for r in rows:
            r.pack(anchor="w", pady=(0, 6))
        for w in all_widgets(b):
            w._look_skip = True
        b.bind("<Escape>", lambda e: self.edit(False))
        b.protocol("WM_DELETE_WINDOW", lambda: self.edit(False))

    def _ask_back_all(self):
        if messagebox.askyesno(TITLE, "Every button, tick and label back where the editor puts it, with its own "
                                      "words? (Undo takes it back step by step.)", parent=self._bar):
            self.back_all()

    def hidden_window(self):
        d = tk.Toplevel(self._bar or self.root)
        d._look_skip = True
        d.title("Hidden pieces")
        f = ttk.Frame(d, padding=8)
        f.pack(fill="both", expand=True)
        keys = [k for k, v in self.data["pieces"].items() if v.get("hidden")]
        if not keys:
            ttk.Label(f, text="Nothing is hidden.").pack(anchor="w")
        lb = tk.Listbox(f, width=70, height=min(14, max(3, len(keys))))
        for k in keys:
            lb.insert("end", k.replace("|", "  >  "))
        lb.pack(fill="both", expand=True)

        def show():
            for i in lb.curselection()[::-1]:
                key = keys[i]
                self.undo.append((key, copy.deepcopy(self.data["pieces"].get(key))))
                e = dict(self.data["pieces"].get(key) or {})
                e.pop("hidden", None)
                self._set(key, e)
                lb.delete(i)
                keys.pop(i)
        ttk.Button(f, text="Show it again", command=show).pack(anchor="e", pady=(6, 0))
        for w in all_widgets(d):
            w._look_skip = True

    def save_as(self):
        p = filedialog.asksaveasfilename(parent=self._bar, title="Save my look", defaultextension=".json",
                                         initialfile="CampaignEditor_look.json", filetypes=(("Look", "*.json"),))
        if p:
            LK.save(self.data, p)

    def load_from(self):
        p = filedialog.askopenfilename(parent=self._bar, title="Load a look", filetypes=(("Look", "*.json"),))
        if not p:
            return
        got = LK.load(p)
        self.back_all()
        for key in got["order"] + [k for k in got["pieces"] if k not in got["order"]]:
            self.undo.append((key, None))
            self._set(key, got["pieces"][key])

    # the mouse in the edit mode (TAG goes first on every widget: 'break' keeps the click from the widget itself)
    def press(self, e):
        w = piece_of(e.widget)
        if w is None:
            return None
        self.pick(w)
        self._drag = (w, e.x_root, e.y_root, False)
        return "break"

    def motion(self, e):
        if self._drag is None:
            return "break"
        w, x0, y0, moving = self._drag
        if not moving and abs(e.x_root - x0) + abs(e.y_root - y0) < 6:
            return "break"
        self._drag = (w, x0, y0, True)
        target, where = self._target(w, e.x_root, e.y_root)
        self._mark_on(target, where)
        return "break"

    def release(self, e):
        if self._drag is None:
            return "break"
        w, _, _, moving = self._drag
        self._drag = None
        self._mark_on(None, None)
        if not moving:
            return "break"
        target, where = self._target(w, e.x_root, e.y_root)
        if target is not None:
            why = can_move(w, target)
            if why:
                messagebox.showinfo(TITLE, why, parent=w.winfo_toplevel())
            else:
                self.change(w, to=target._look_key, where=where, hidden=None)
        return "break"

    def menu(self, e):
        w = piece_of(e.widget)
        if w is None:
            return None
        self.pick(w)
        e_ = self.data["pieces"].get(w._look_key, {})
        m = tk.Menu(w, tearoff=False)
        m.add_command(label=(getattr(w, "_look_text", "") or w.winfo_class())[:60], state="disabled")
        m.add_separator()
        if hasattr(w, "_look_text"):
            m.add_command(label="Rename...", command=lambda: self._rename(w))
        m.add_command(label="Hover text...", command=lambda: self._tip(w))
        m.add_command(label="Width...", command=lambda: self._width(w))
        m.add_command(label="Colours, font and emoji...", command=lambda: self._style_dialog(w))
        m.add_command(label="Hide", command=lambda: self.change(w, hidden=True))
        m.add_separator()
        m.add_command(label="Back to how it was", command=lambda: self._back_one(w),
                      state="normal" if e_ else "disabled")
        m._look_skip = True
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()
        return "break"

    def _back_one(self, w):
        self.undo.append((w._look_key, copy.deepcopy(self.data["pieces"].get(w._look_key))))
        self._set(w._look_key, None)

    def _rename(self, w):
        now = self.data["pieces"].get(w._look_key, {}).get("text") or self.word(w._look_text)
        got = simpledialog.askstring(TITLE, "Its words (empty: the editor's own '%s'):" % w._look_text,
                                     initialvalue=now, parent=w.winfo_toplevel())
        if got is not None:
            self.change(w, text=got.strip() or None)

    def _tip(self, w):
        now = self.data["pieces"].get(w._look_key, {}).get("tip", "")
        got = simpledialog.askstring(TITLE, "Its hover text (shown with its own; empty: none):", initialvalue=now,
                                     parent=w.winfo_toplevel())
        if got is not None:
            self.change(w, tip=got.strip() or None)

    def _width(self, w):
        now = self.data["pieces"].get(w._look_key, {}).get("width", "")
        got = simpledialog.askstring(TITLE, "Its width in letters (empty: as wide as its words):",
                                     initialvalue=str(now), parent=w.winfo_toplevel())
        if got is None:
            return
        got = got.strip()
        if got and not got.lstrip("-").isdigit():
            messagebox.showinfo(TITLE, "A whole number of letters, or nothing.", parent=w.winfo_toplevel())
            return
        self.change(w, width=int(got) if got else None)

    def _style_dialog(self, w):
        e = self.data["pieces"].get(w._look_key, {})
        got = ask_style(w.winfo_toplevel(), e, getattr(w, "_look_text", "") or w.winfo_class())
        if got is not None:
            self.change(w, **got)

    def _target(self, w, x, y):
        """(the piece under the mouse, 'before' / 'after' by which half of it) - not the dragged one."""
        under = self.root.winfo_containing(x, y)
        if under is not None and getattr(under, "_look_of", None) is not None:
            return None, None                         # a copy is not a place to drop on (its piece is hidden)
        t = piece_of(under) if under is not None else None
        if t is None or t is w or str(t).startswith(str(w) + "."):
            return None, None
        mid = t.winfo_rootx() + t.winfo_width() / 2
        return t, ("before" if x < mid else "after")

    def _mark_on(self, t, where):
        if self._mark is not None:
            try:
                self._mark.destroy()
            except tk.TclError:
                pass
            self._mark = None
        if t is None:
            return
        f = self._mark = tk.Frame(t.winfo_toplevel(), background=YELLOW)
        f._look_skip = True
        f.place(in_=t, relx=0 if where == "before" else 1, x=-2 if where == "before" else -1, rely=0,
                relheight=1, width=3)
        f.lift()


# ---- the pieces ----
def all_widgets(root):
    out, todo = [], [root]
    while todo:
        w = todo.pop()
        out.append(w)
        try:
            todo.extend(w.winfo_children())
        except tk.TclError:
            pass
    return out


def piece_of(w):
    """The button / tick / label a click landed on (itself, or the one it is part of), or None."""
    while w is not None:
        if getattr(w, "_look_skip", False):
            return None
        try:
            if getattr(w, "_look_of", None) is not None:          # a copy stands for its piece
                return w._look_of
            if w.winfo_class() in PIECES and getattr(w, "_look_key", None):
                return w
        except tk.TclError:
            return None
        w = getattr(w, "master", None)
        if isinstance(w, (tk.Tk, tk.Toplevel)):
            return None
    return None


def window_key(w):
    top = w.winfo_toplevel()
    if isinstance(top, tk.Tk):
        return "main"
    name = type(top).__name__
    return name if name != "Toplevel" else getattr(top, "_look_title", None) or top.title()


def scope_of(w):
    """The named boxes around a piece, nearest first: a framed box's words, a tab's words."""
    out, child, m = [], w, w.master
    while m is not None and not isinstance(m, (tk.Tk, tk.Toplevel)):
        try:
            cls = m.winfo_class()
            if cls in ("TLabelframe", "Labelframe"):
                out.append(getattr(m, "_look_text", None) or str(m.cget("text")))
            elif cls == "TNotebook":
                tabs = getattr(m, "_look_tabs", {})
                t = tabs.get(str(child)) or (str(m.tab(child, "text")) if str(child) in m.tabs() else "")
                if t:
                    out.append(t)
        except tk.TclError:
            pass
        child, m = m, m.master
        if len(out) >= 2:
            break
    return "/".join(out)


def piece_key(look, w):
    """'window|boxes|class:words#n' - a piece named by where it is and its own English words; a piece without words
    by the words just before it in its row. n counts pieces of one name in a window (the second 'Rename...')."""
    cls = w.winfo_class()
    text = getattr(w, "_look_text", None)
    if not text:
        text = "after:" + _words_before(w)
    base = "%s|%s|%s:%s" % (window_key(w), scope_of(w), cls, text)
    count = (str(w.winfo_toplevel()), base)            # counted in each open window, from 1 when it opens again
    n = look.counts.get(count, 0) + 1
    look.counts[count] = n
    return base if n == 1 else "%s#%d" % (base, n)


def _words_before(w):
    """The words of the nearest piece before w in its box that has words, kept on w: a piece without words before it
    has the same words before it, so the walk back stops there (a box of a thousand pictures - Recolour's - walked
    every one before each one: a tab took seconds to open, report #411)."""
    out, passed = "", [w]
    try:
        kids = list(w.master.children.values())          # tkinter's own list, in the order they were made
        for k in reversed(kids[:kids.index(w)]):
            got = getattr(k, "_look_before", None)
            if got is not None and not getattr(k, "_look_text", None):
                out = got
                break
            t = getattr(k, "_look_text", None)
            if t is None and k.winfo_class() in WITH_TEXT:
                t = str(k.cget("text"))
            if t:
                out = t
                break
            passed.append(k)                             # no words: the same words before it
    except (tk.TclError, ValueError, AttributeError):
        pass
    for k in passed:
        k._look_before = out
    return out


def container(t):
    """(the bar / box a piece stands in, how it lays out: 'flow' / 'pack' / 'grid') or (None, None)."""
    m = t.master
    if getattr(m, "_flow_items", None) is not None and any(it[0] is t for it in m._flow_items):
        return m, "flow"
    mgr = t.winfo_manager()
    if mgr == "pack":
        return t.pack_info()["in"], "pack"
    if mgr == "grid":
        return t.grid_info()["in"], "grid"
    return None, None


def can_move(w, t):
    """Why the piece cannot go beside t, or None."""
    c, how = container(t)
    if c is None:
        return "That place is drawn by its own window - drop it beside a button or tick in a bar."
    if how == "grid" and (container(w)[0] is not c):
        return ("That place is a table: a piece goes there only from the same table (the two change places) - drop "
                "it beside a button in a row.")
    return None


def _inside(c, parent):
    s, p = str(c), str(parent)
    return s == p or s.startswith(p + ".") or p == "."


def move(look, w, t, where):
    """The piece put before / after t (look.change keeps it). Returns why not, or None."""
    why = can_move(w, t)
    if why:
        return why
    c, how = container(t)
    look._home(w)
    clone = look.clones.pop(str(w), None)
    if clone is not None:
        clone.destroy()
    piece = w
    if not _inside(c, w.master):                     # Tk gives no new parent: a copy stands there
        look._forget(w)
        piece = make_copy(w, c)
        look.clones[str(w)] = piece
    elif piece.winfo_manager() or getattr(piece.master, "_flow_items", None) is not None:
        if how != "grid":
            look._forget(piece)
    if how == "flow":
        items = c._flow_items
        i = next(i for i, it in enumerate(items) if it[0] is t)
        side = items[i][3]
        items.insert(i if where == "before" else i + 1, (piece, 4, 0, side))
        piece.bind("<Configure>", c._flow_reflow, add="+")
        c._flow_reflow(again=True)
    elif how == "pack":
        info = t.pack_info()
        kw = {k: info[k] for k in ("side", "padx", "pady", "anchor") if k in info}
        kw[where] = t
        piece.pack(in_=c, **kw)
    else:                                            # a table: the two change places
        a, b = dict(w.grid_info()), dict(t.grid_info())
        for info, wid in ((b, w), (a, t)):
            info["in_"] = info.pop("in")
            wid.grid(**info)
    return None


def make_copy(w, master):
    """A piece of the same kind under master, with w's command, variable, words and bindings."""
    cls = CLONES.get(w.winfo_class())
    if cls is None:
        raise tk.TclError("no copy for %s" % w.winfo_class())
    c = cls(master)
    for k in w.keys():
        if k in ("class", "name"):
            continue
        try:
            v = w.cget(k)
            if str(v) != "":
                c.configure(**{k: v})
        except tk.TclError:
            pass
    for seq in w.bind():
        try:
            c.bind(seq, w.bind(seq))
        except tk.TclError:
            pass
    c._look_seen, c._look_key, c._look_of = True, None, w      # the copy is not a piece of its own
    follow(w, c)
    return c


def follow(w, c):
    """The copy shows what the piece shows now: its words, greyed or not."""
    try:
        if "text" in w.keys() and str(c.cget("text")) != str(w.cget("text")):
            c.configure(text=w.cget("text"))
        if hasattr(w, "state") and hasattr(c, "state") and isinstance(w, ttk.Widget):
            want = set(w.state())
            have = set(c.state())
            for flag in ("disabled", "selected", "alternate"):
                if (flag in want) != (flag in have):
                    c.state([flag if flag in want else "!" + flag])
        elif "state" in w.keys() and str(c.cget("state")) != str(w.cget("state")):
            c.configure(state=w.cget("state"))
    except tk.TclError:
        pass


def _rgb(w, colour):
    try:
        r, g, b = w.winfo_rgb(colour)
        return r >> 8, g >> 8, b >> 8
    except tk.TclError:
        return (128, 128, 128)


# emoji a Windows font draws in Tk (one colour, as the words); the field takes any other one typed or pasted
EMOJI = ("❓", "❗", "⭐", "✔", "✖", "➕", "➖", "⚙", "⚔", "⚑", "⚠", "⚓", "☠", "♛", "♜", "☀", "☁", "✎",
         "✉", "⌛", "⏩", "⏪", "↺", "↻", "⬆", "⬇", "⬅", "➡", "♻", "☰", "🏰", "🗺", "🛡", "📜", "💾", "📂",
         "🔍", "🎨", "🖌", "🧭", "👑", "🐎", "🏹", "⛵", "🔥", "💰", "📦", "🧪", "🔧", "🗑", "▶", "■", "●", "◆")
FONT_STYLES = (("plain", ""), ("bold", "bold"), ("italic", "italic"), ("bold italic", "bold italic"))


def ask_style(parent, entry, words):
    """A small window for a piece's colours, font and emoji, a preview of it in the middle (entry: its look now).
    -> {'bg', 'fg', 'font', 'emoji'} (None = the editor's own) or None when closed without OK."""
    from tkinter import colorchooser
    from tkinter import font as tkfont
    win = tk.Toplevel(parent)
    win.title("Colours, font and emoji")
    win.transient(parent)
    win._look_skip = True
    now = {"bg": entry.get("bg"), "fg": entry.get("fg")}
    spec = (list(entry.get("font") or []) + ["", 0, ""])[:3]
    v_family = tk.StringVar(win, value=spec[0] or "(the editor's)")
    v_size = tk.StringVar(win, value=str(spec[1] or ""))
    v_style = tk.StringVar(win, value=next((n for n, s in FONT_STYLES if s == (spec[2] or "")), "plain"))
    v_emoji = tk.StringVar(win, value=entry.get("emoji") or "")
    got = {}
    outer = ttk.Frame(win, padding=10)
    outer.pack(fill="both", expand=True)
    body = ttk.Frame(outer)
    body.pack(anchor="w")
    preview = tk.Label(body, text=words, relief="raised", padx=10, pady=4)
    preview.grid(row=0, column=0, columnspan=4, pady=(0, 10))
    from . import theme
    theme.leave_alone(preview)
    plain = {"bg": preview.cget("background"), "fg": preview.cget("foreground")}
    base_font = tkfont.nametofont("TkDefaultFont").actual()

    def show(*_):
        size = v_size.get().strip()
        family = v_family.get()
        f = LK.font_of([("" if family.startswith("(") else family), int(size) if size.isdigit() else 0,
                        dict(FONT_STYLES).get(v_style.get(), "")], (base_font["family"], base_font["size"]))
        preview.configure(text=LK.shown_words({"emoji": v_emoji.get().strip()}, words),
                          background=now["bg"] or plain["bg"], foreground=now["fg"] or plain["fg"],
                          font=f or "TkDefaultFont")

    def colour(which, label):
        c = colorchooser.askcolor(color=now[which] or None, parent=win, title=label)
        if c and c[1]:
            now[which] = c[1]
            show()

    def no_colour(which):
        now[which] = None
        show()

    for row, (which, label) in enumerate((("bg", "Background"), ("fg", "Words' colour")), start=1):
        ttk.Label(body, text=label).grid(row=row, column=0, sticky="w")
        ttk.Button(body, text="Pick...", command=lambda w_=which, l_=label: colour(w_, l_)).grid(row=row, column=1)
        ttk.Button(body, text="The theme's", command=lambda w_=which: no_colour(w_)).grid(row=row, column=2)
    ttk.Label(body, text="Font").grid(row=3, column=0, sticky="w", pady=(8, 0))
    families = ["(the editor's)"] + sorted(f for f in set(tkfont.families(win)) if not f.startswith("@"))
    cb = ttk.Combobox(body, textvariable=v_family, values=families, width=24)
    cb.grid(row=3, column=1, columnspan=2, sticky="we", pady=(8, 0))
    sb = ttk.Spinbox(body, from_=0, to=72, textvariable=v_size, width=4)
    sb.grid(row=3, column=3, padx=(4, 0), pady=(8, 0))
    st = ttk.Combobox(body, textvariable=v_style, values=[n for n, _ in FONT_STYLES], width=12, state="readonly")
    st.grid(row=4, column=1, sticky="w")
    ttk.Label(body, text="size (empty: the editor's)").grid(row=4, column=2, columnspan=2, sticky="w")
    ttk.Label(body, text="Emoji before its words").grid(row=5, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(body, textvariable=v_emoji, width=8).grid(row=5, column=1, sticky="w", pady=(8, 0))
    ttk.Button(body, text="None", command=lambda: v_emoji.set("")).grid(row=5, column=2, sticky="w", pady=(8, 0))
    grid = ttk.Frame(outer)                               # its own box: the form's columns keep their width
    grid.pack(anchor="w", pady=(4, 0))
    for i, em in enumerate(EMOJI):
        tk.Button(grid, text=em, width=2, relief="flat", command=lambda e_=em: v_emoji.set(e_)).grid(
            row=i // 14, column=i % 14)
    for v in (v_family, v_size, v_style, v_emoji):
        v.trace_add("write", show)
    bar = ttk.Frame(outer)
    bar.pack(anchor="e", pady=(10, 0))

    def ok():
        size = v_size.get().strip()
        family = v_family.get().strip()
        font = ["" if family.startswith("(") else family, int(size) if size.isdigit() else 0,
                dict(FONT_STYLES).get(v_style.get(), "")]
        got.update(bg=now["bg"], fg=now["fg"], font=font if any(font) else None,
                   emoji=v_emoji.get().strip() or None)
        win.destroy()

    def all_back():
        got.update({k: None for k in LK.STYLE_KEYS})
        win.destroy()

    ttk.Button(bar, text="All the editor's own", command=all_back).pack(side="left", padx=(0, 12))
    ttk.Button(bar, text="OK", command=ok).pack(side="left", padx=(0, 4))
    ttk.Button(bar, text="Cancel", command=win.destroy).pack(side="left")
    win.bind("<Escape>", lambda e: win.destroy())
    show()
    win.grab_set()
    win.wait_window()
    return got or None


def install(root):
    """The look on every window from now on; the edit mode's mouse on the tag every widget gets while it is on."""
    look = root.look = Look(root)
    root.bind_class(TAG, "<ButtonPress-1>", look.press)
    root.bind_class(TAG, "<B1-Motion>", look.motion)
    root.bind_class(TAG, "<ButtonRelease-1>", look.release)
    root.bind_class(TAG, "<ButtonPress-3>", look.menu)
    for seq in ("<Double-Button-1>", "<ButtonRelease-3>", "<KeyPress-space>", "<KeyPress-Return>"):
        root.bind_class(TAG, seq, lambda e: "break" if piece_of(e.widget) is not None else None)
    return look


def word(text):
    """The language's words for English ones, wherever the editor builds words itself (hover texts)."""
    root = tk._default_root
    look = getattr(root, "look", None)
    return look.word(text) if look is not None else text


__all__ = ["install", "Look", "piece_key", "move", "make_copy", "word", "ask_style", "EMOJI"]
