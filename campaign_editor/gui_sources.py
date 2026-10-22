"""Tools > Authors and sources of this mod...: whose work the mod holds (sources.py), and the small window that
comes after taking something from another mod or a pack - the source already noted, author / link / asked filled
in there or later. Nothing is checked or blocked: 'Later' keeps the source in the list as it is."""

import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from . import settings, sources as SO
from .gui_util import hint, one_window, tip

PUBLISH_NOTE = ("Going to publish your mod? Ask the author first.\n"
                "Even if not, it is good to ask - and to say whose work it is.")


def _root(app):
    return SO.folder(app.mod.data) if getattr(app, "mod", None) else None


def _form(parent, entry):
    """The fields of one source in `parent` (a grid); returns a function giving the entry as filled in."""
    vs = {k: tk.StringVar(value=entry.get(k, "")) for k in ("source", "author", "link", "what")}
    rows = (("From (mod / pack)", "source", ""), ("Author", "author", "who made it (if you know)"),
            ("Link", "link", "where it is published (if you know)"), ("What was taken", "what", ""))
    for r, (label, key, say) in enumerate(rows):
        ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=2, padx=(0, 8))
        e = ttk.Entry(parent, textvariable=vs[key], width=48)
        e.grid(row=r, column=1, sticky="we", pady=2)
        if say:
            tip(e, say)
    ttk.Label(parent, text="Asked the author?").grid(row=len(rows), column=0, sticky="w", pady=2, padx=(0, 8))
    words = [w for _, w in SO.ASKED]
    v_asked = tk.StringVar(value=SO.ASKED_WORDS.get(entry.get("asked"), words[0]))
    ttk.Combobox(parent, textvariable=v_asked, values=words, state="readonly", width=20).grid(
        row=len(rows), column=1, sticky="w", pady=2)
    parent.columnconfigure(1, weight=1)

    def got():
        out = {k: v.get().strip() for k, v in vs.items()}
        out["asked"] = next((k for k, w in SO.ASKED if w == v_asked.get()), "not_yet")
        return out
    return got


def edit_window(parent, title, entry, on_save, intro=None, note=None, later="Cancel", save="Save", remind_tick=False):
    """One source in a small window: `intro` (a line on top), `note` (the yellow publish note), the fields; Save
    hands the filled entry to on_save. remind_tick: the 'show this after every import' tick."""
    w = tk.Toplevel(parent)
    w.title(title)
    w.transient(parent)
    frm = ttk.Frame(w, padding=12)
    frm.pack(fill="both", expand=True)
    if intro:
        ttk.Label(frm, text=intro, wraplength=460, justify="left").pack(anchor="w")
    if note:
        tk.Label(frm, text=note, justify="left", anchor="w", background="#fff8e1", foreground="#3a3000",
                 relief="solid", borderwidth=1, padx=8, pady=6, wraplength=460).pack(fill="x", pady=(6, 4))
    grid = ttk.Frame(frm)
    grid.pack(fill="x", pady=(6, 0))
    got = _form(grid, entry)
    v_remind = tk.BooleanVar(value=bool(settings.get("sources_remind", True)))
    if remind_tick:
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(8, 0))
        ttk.Checkbutton(row, text="Show this after taking something from another mod",
                        variable=v_remind).pack(side="left")
        hint(row, "Off: the source still goes into Tools > Authors and sources of this mod, without this window. "
                  "Nothing is checked or blocked - this only helps you not forget.").pack(side="left")
    bar = ttk.Frame(frm)
    bar.pack(fill="x", pady=(10, 0))

    def done(keep):
        if remind_tick:
            settings.put("sources_remind", bool(v_remind.get()))
        if keep:
            e = got()
            if not e["source"]:
                messagebox.showinfo(title, "Write where it comes from (the mod or pack's name).", parent=w)
                return
            on_save(e)
        w.destroy()
    ttk.Button(bar, text=later, command=lambda: done(False)).pack(side="left")
    ttk.Button(bar, text=save, command=lambda: done(True), default="active").pack(side="right")
    w.protocol("WM_DELETE_WINDOW", lambda: done(False))
    return w


def noted(app, src, what):
    """After something was taken from another mod or a pack (`src`: its data folder or the pack's path): the source
    goes into the mod's list at once (nothing forgotten) and, unless turned off, a small window asks for the author
    and link with the publish note. Nothing on the game's own data or when the mod has no folder of its own."""
    root = _root(app)
    if not root or not src or SO.is_game_own(src):
        return None
    name = SO.source_name(src)
    try:
        items, i = SO.noted(SO.load(root), name, what)
        SO.save(root, items)
    except OSError as e:
        app.status.set("Authors and sources: the list could not be written (%s)." % e)
        return None
    if not settings.get("sources_remind", True) or items[i]["asked"] in ("yes", "not_needed"):
        app.status.set("%s noted in Tools > Authors and sources of this mod." % name)
        return None

    def save(e):
        cur = SO.load(root)
        j = SO.find(cur, name)
        if j is None:
            cur.append(e)
        else:
            cur[j] = e
        SO.save(root, cur)
        app.status.set("%s noted in Tools > Authors and sources of this mod (%s)." % (e["source"], SO.TEXT_NAME))
    return edit_window(app, "Whose work is this?", items[i], save,
                       intro="You took %s from %s. It is noted in Authors and sources of this mod." % (what, name),
                       note=PUBLISH_NOTE, later="Later", save="Save", remind_tick=True)


@one_window
class SourcesWindow(tk.Toplevel):
    """The mod's list: what was taken, from where, the author, the link, asked or not - Add / Edit / Remove,
    the link in the browser, the text file the players see."""
    COLS = (("what", "What was taken", 220), ("source", "From (mod / pack)", 150), ("author", "Author", 130),
            ("link", "Link", 170), ("asked", "Asked the author?", 120))

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.root_dir = _root(app)
        self.title("Authors and sources" + (" - " + SO.source_name(app.mod.data) if self.root_dir else ""))
        self.transient(app)
        self.geometry("860x380")
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        top = ttk.Frame(frm)
        top.pack(fill="x")
        say = ("Whose work is in your mod. The editor keeps this list in %s in the mod folder, so players and "
               "whoever shares the mod see it too." % SO.TEXT_NAME if self.root_dir else
               "This is the game's own data: make your own mod folder first (New mod folder...) - its list of "
               "authors and sources is kept there.")
        ttk.Label(top, text=say, wraplength=760, justify="left").pack(side="left")
        hint(top, "When you take units, a faction, a battle model or a pack from another mod, the editor notes it "
                  "here by itself and asks for the author and the link. If you are going to publish your mod, ask "
                  "the author first; even if not, it is good to ask. Nothing is checked or blocked.").pack(side="left")
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True, pady=8)
        self.tv = ttk.Treeview(box, columns=[c for c, _, _ in self.COLS], show="headings", selectmode="browse")
        for c, label, width in self.COLS:
            self.tv.heading(c, text=label)
            self.tv.column(c, width=width, stretch=True)
        sb = ttk.Scrollbar(box, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tv.pack(fill="both", expand=True)
        self.tv.bind("<Double-1>", lambda e: self.edit())
        bar = ttk.Frame(frm)
        bar.pack(fill="x")
        state = "normal" if self.root_dir else "disabled"
        for text, cmd in (("Add...", self.add), ("Edit...", self.edit), ("Remove", self.remove),
                          ("Open link", self.open_link)):
            ttk.Button(bar, text=text, command=cmd, state=state).pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Show %s" % SO.TEXT_NAME, command=self.show_text, state=state).pack(side="right",
                                                                                               padx=6)
        self.fill()

    def fill(self):
        self.items = SO.load(self.root_dir)
        self.tv.delete(*self.tv.get_children())
        for i, e in enumerate(self.items):
            self.tv.insert("", "end", iid=str(i), values=(e["what"], e["source"], e["author"] or "who?", e["link"],
                                                          SO.ASKED_WORDS[e["asked"]]))

    def _picked(self):
        sel = self.tv.selection()
        return int(sel[0]) if sel else None

    def _write(self, items):
        try:
            SO.save(self.root_dir, items)
        except OSError as e:
            messagebox.showerror(self.title(), "The list could not be written: %s" % e, parent=self)
        self.fill()

    def add(self):
        edit_window(self, "Add a source", {"asked": "not_yet"}, lambda e: self._write(self.items + [e]))

    def edit(self):
        i = self._picked()
        if i is None or not self.root_dir:
            return

        def save(e):
            items = list(self.items)
            items[i] = e
            self._write(items)
        edit_window(self, "Edit a source", self.items[i], save)

    def remove(self):
        i = self._picked()
        if i is not None:
            self._write(self.items[:i] + self.items[i + 1:])

    def open_link(self):
        i = self._picked()
        link = self.items[i]["link"] if i is not None else ""
        if link:
            webbrowser.open(link if "://" in link else "https://" + link)

    def show_text(self):
        self.app.show_text(SO.TEXT_NAME, SO.text(self.items, SO.source_name(self.app.mod.data)).replace("\r", ""),
                           wrap="word")


def open_sources(app):
    """Tools > Authors and sources of this mod... (App.sources_window)."""
    if not getattr(app, "mod", None):
        messagebox.showinfo("Authors and sources", "Load a mod first (Mod or Browse..., then Load).", parent=app)
        return None
    return SourcesWindow(app)
