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

    def __init__(self, root):
        self.root = root
        self.data = LK.load()
        self.words = {}
        self.seen_words = set()                   # English words seen in the windows (for 'Words to translate')
        self.by_key = {}                          # key -> widget (the newest of that key)
        self.counts = {}                          # (window, base key) -> pieces of it seen
        self.clones = {}                          # str(original) -> its copy standing where it was dropped
        self.waiting = []                         # keys moved whose target has not shown yet
        self.editing, self.picked, self.undo = False, None, []
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
        if w.winfo_class() == "TNotebook":
            self._words_on(w)

    def _words_on(self, w):
        cls = w.winfo_class()
        e = self.data["pieces"].get(getattr(w, "_look_key", None), {})
        if hasattr(w, "_look_text"):
            want = e.get("text") or self.word(w._look_text)
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
        if "width" in e:
            try:
                w.configure(width=e["width"])
            except tk.TclError:
                pass
        if e.get("tip"):
            w._look_tip = e["tip"]
            if not getattr(w, "_look_tipped", False):
                w._look_tipped = True
                from .gui_util import Tip
                Tip(w, lambda: getattr(w, "_look_tip", ""))
        if e.get("hidden"):
            self._home(w)
            self._forget(w)
        elif "to" in e:
            if not self._move_now(w, e["to"], e.get("where", "after")):
                if w._look_key not in self.waiting:
                    self.waiting.append(w._look_key)

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
        home = getattr(w, "_look_home", None)
        if home is None:
            return
        del w._look_home
        self._forget(w)
        kind = home[0]
        if kind == "flow":
            _, m, i, item = home
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
        key = w._look_key
        old = copy.deepcopy(self.data["pieces"].get(key))
        new = dict(old or {})
        for k, v in kw.items():
            if v is None:
                new.pop(k, None)
            else:
                new[k] = v
        self.undo.append((key, old))
        self._set(key, new)

    def _set(self, key, entry):
        LK.set_entry(self.data, key, entry)
        LK.save(self.data)
        w = self.by_key.get(key)
        if w is not None and w.winfo_exists():
            self.back_home(w)
            self._put_on(w)
        self._frame_on(self.picked)

    def do_undo(self):
        if not self.undo:
            return False
        key, old = self.undo.pop()
        self._set(key, old)
        return True

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
    try:
        kids = w.master.winfo_children()
        for k in reversed(kids[:kids.index(w)]):
            t = getattr(k, "_look_text", None)
            if t is None and k.winfo_class() in WITH_TEXT:
                t = str(k.cget("text"))
            if t:
                return t
    except (tk.TclError, ValueError):
        pass
    return ""


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


__all__ = ["install", "Look", "piece_key", "move", "make_copy", "word"]
