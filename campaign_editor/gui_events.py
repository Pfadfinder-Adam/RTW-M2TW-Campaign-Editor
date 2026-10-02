"""Tools > Events and later factions: the campaign's events (descr_events.txt) - their date, place, the title and
text players see; new ones, removed ones; Show on the map. Below them, the factions that appear later in the
campaign (descr_strat's dead_until_resurrected, woken by the campaign script) - shown, not changed. Preview /
Write it in, with a backup like every write."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .gui_util import ShortHint
from . import events as EV
from .plan import Plan

TITLE = "Events and later factions"


class EventsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.mod = app, app.mod
        self.campaign = app.v_campaign.get()
        self.title("%s - %s" % (TITLE, self.campaign))
        self.geometry("1100x760")
        self.transient(app)
        self.edits, self.removed, self.new, self.texts = {}, [], [], {}
        self.pictures = {}                   # {event name: picture file} - its scroll picture, every culture
        from .limits import game_kind
        self.rome = game_kind(self.mod) != "medieval2"
        top = ttk.Frame(self, padding=8)
        top.pack(fill="both", expand=True)
        ShortHint(top, foreground="#555", justify="left", wraplength=1020, text=(
            "The campaign's events (descr_events.txt): a historic message, or a plague, volcano, earthquake ... at a "
            "place. The date is %s. The title and text players see are in historic_events.txt. Preview, then "
            "Write it in (a backup first, Tools > Restore undoes it)." % (
                "years from the start and optionally summer or winter, like '14 winter'" if self.rome else
                "a turn, or two turns - the game picks one between them, like '210 220'"))).pack(fill="x")
        body = ttk.Frame(top)
        body.pack(fill="both", expand=True, pady=6)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        self.tv = ttk.Treeview(left, columns=("name", "kind", "date", "title"), show="headings", height=18,
                               selectmode="browse")
        for c, t, w in (("name", "event", 170), ("kind", "kind", 80), ("date", "date", 80), ("title", "title", 200)):
            self.tv.heading(c, text=t)
            self.tv.column(c, width=w, stretch=c == "title")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        bb = ttk.Frame(left)
        bb.pack(side="bottom", fill="x", pady=(4, 0))
        ttk.Button(bb, text="New event...", command=self.add).pack(side="left")
        ttk.Button(bb, text="Remove", command=self.remove).pack(side="left", padx=4)
        sb.pack(side="right", fill="y")
        self.tv.pack(side="left", fill="both", expand=True)
        self.tv.bind("<<TreeviewSelect>>", lambda e: self.show())
        self.form = ttk.LabelFrame(body, text="Event", padding=8)
        self.form.pack(side="left", fill="both", expand=True, padx=(10, 0))
        later = ttk.LabelFrame(top, text="Factions that appear later in the campaign", padding=6)
        later.pack(fill="x")
        rows = EV.later_factions(self.mod, self.campaign)
        ShortHint(later, foreground="#555", justify="left", wraplength=1000, text=(
            "\n".join("%s - dead at the start (dead_until_resurrected in descr_strat.txt); %s" % (
                f, ("woken by the campaign script: " + "; ".join(lines)) if lines else
                "no line of the campaign script wakes it (it may never appear)") for f, lines in rows)
            if rows else "None in this campaign: every faction is there from the start.")).pack(anchor="w")
        bar = ttk.Frame(top)
        bar.pack(fill="x", pady=(6, 0))
        self.lbl = ttk.Label(bar, text="", foreground="#555")
        self.lbl.pack(side="left")
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Write it in", command=self.write).pack(side="right", padx=4)
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right")
        self.reload()

    # ---- reading ----
    def reload(self):
        from .strtables import strings
        path = EV.path_of(self.mod, self.campaign)
        self.events = EV.read(self.mod.load(path)) if path else []
        self.shown = strings(self.mod, "historic_events.txt")
        self.fill()

    def text(self, key):
        return self.texts[key] if key in self.texts else self.shown.get(key.upper(), "")

    def rows(self):
        out = [dict(e) for e in self.events if e["id"] not in self.removed]
        for e in out:
            e.update(self.edits.get(e["id"], {}))
        return out + [dict(e, new=True, id=e["name"]) for e in self.new]

    def fill(self, pick=None):
        cur = pick or (self.tv.selection() or [None])[0]
        self.tv.delete(*self.tv.get_children())
        for e in self.rows():
            mark = " (new)" if e.get("new") else (" *" if e["id"] in self.edits else "")
            self.tv.insert("", "end", iid=e["id"], values=(
                e["id"] + mark, e["kind"], e["date"], self.text(e["name"] + "_TITLE")))
        if cur and self.tv.exists(cur):
            self.tv.selection_set(cur)
            self.tv.see(cur)
        self.show()
        n = len(self.edits) + len(self.removed) + len(self.new) + len(self.texts) + len(self.pictures)
        self.lbl.configure(text="%d change(s) - Preview, then Write it in." % n if n else "Nothing changed yet.")

    # ---- the form ----
    def show(self):
        for w in self.form.winfo_children():
            w.destroy()
        name = (self.tv.selection() or [None])[0]
        e = next((x for x in self.rows() if x["id"] == name), None)
        if not e:
            ttk.Label(self.form, text="Pick an event on the left.", foreground="#555").pack(anchor="w")
            return
        self.form.configure(text="Event: %s (%s)" % (name, e["kind"]))
        key = e["name"]                                  # its texts: by name (two uses of a name share them)
        r = ttk.Frame(self.form)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text="Date", width=14).pack(side="left")
        v_date = tk.StringVar(value=e["date"])
        ttk.Entry(r, textvariable=v_date, width=14).pack(side="left")
        ttk.Label(r, text="  years [summer|winter]" if self.rome else "  turn [turn]", foreground="#555").pack(
            side="left")
        r = ttk.Frame(self.form)
        r.pack(fill="x", pady=2)
        ttk.Label(r, text="Place (x, y)", width=14).pack(side="left")
        pos = e.get("position")
        v_x, v_y = tk.StringVar(value=str(pos[0]) if pos else ""), tk.StringVar(value=str(pos[1]) if pos else "")
        ttk.Entry(r, textvariable=v_x, width=6).pack(side="left")
        ttk.Entry(r, textvariable=v_y, width=6).pack(side="left", padx=4)
        ttk.Button(r, text="Show on the map", command=lambda: self.show_on_map(v_x.get(), v_y.get())).pack(
            side="left", padx=6)
        ttk.Label(self.form, text="Title players see").pack(anchor="w", pady=(8, 0))
        v_title = tk.StringVar(value=self.text(key + "_TITLE"))
        ttk.Entry(self.form, textvariable=v_title, width=70).pack(fill="x")
        ttk.Label(self.form, text="Text players see").pack(anchor="w", pady=(8, 0))
        t = tk.Text(self.form, height=6, width=60, wrap="word")
        t.insert("1.0", self.text(key + "_BODY"))
        t.pack(fill="both", expand=True)
        if e.get("movie"):
            ttk.Label(self.form, text="movie: %s" % e["movie"], foreground="#555").pack(anchor="w")
        self._picture_part(e)
        ttk.Label(self.form, text="What it does in the game", font=("", 9, "bold")).pack(anchor="w", pady=(8, 0))
        ttk.Label(self.form, text=EV.what_it_does(e["kind"]), foreground="#555", wraplength=480,
                  justify="left").pack(anchor="w")

        def keep(*_):
            ch = {}
            if v_date.get().strip() != e["date"]:
                ch["date"] = v_date.get().strip()
            x, y = v_x.get().strip(), v_y.get().strip()
            want = (int(x), int(y)) if x.lstrip("-").isdigit() and y.lstrip("-").isdigit() else None
            if want != (tuple(pos) if pos else None):
                ch["position"] = list(want) if want else None
            if e.get("new"):
                n = next(x for x in self.new if x["name"] == name)
                n["date"] = v_date.get().strip()
                n["position"] = list(want) if want else None
            elif ch:
                base = next(x for x in self.events if x["id"] == name)
                ch = {k: v for k, v in ch.items() if (v != base["date"] if k == "date" else
                                                       v != (list(base["position"]) if base["position"] else None))}
                if ch:
                    self.edits[name] = ch
                else:
                    self.edits.pop(name, None)
            else:
                self.edits.pop(name, None)
            for k, value in ((key + "_TITLE", v_title.get()), (key + "_BODY", t.get("1.0", "end").rstrip("\n"))):
                if value == self.shown.get(k.upper(), ""):
                    self.texts.pop(k, None)
                else:
                    self.texts[k] = value
            n = len(self.edits) + len(self.removed) + len(self.new) + len(self.texts) + len(self.pictures)
            self.lbl.configure(text="%d change(s) - Preview, then Write it in." % n if n else "Nothing changed yet.")
        for v in (v_date, v_x, v_y, v_title):
            v.trace_add("write", keep)
        t.bind("<KeyRelease>", keep)

    def _picture_part(self, e):
        """The picture players see on the scroll (the first culture's, the others counted) and Picture... to put
        one's own in (a historic event: its own, written for every culture; a disaster: shared by its kind)."""
        name, kind = e["name"], e["kind"]
        row = ttk.Frame(self.form)
        row.pack(fill="x", pady=(8, 0))
        pic = tk.Label(row)
        pic.pack(side="left")
        side = ttk.Frame(row)
        side.pack(side="left", fill="x", padx=8, anchor="n")
        files = EV.picture_files(self.mod, name, kind)
        mine = self.pictures.get(name)
        shown = mine or next((p for p in files.values() if p), None)
        have = [c for c, p in files.items() if p]
        if mine:
            what = "your picture - written for every culture with Write it in"
        elif shown:
            what = "%s.tga - %s" % (EV.picture_name(name, kind), ", ".join(have))
        else:
            what = "no picture (ui/<culture>/eventpics/%s.tga is not there): the scroll shows none" % name
        ttk.Label(side, text="Picture players see", font=("", 9, "bold")).pack(anchor="w")
        ttk.Label(side, text=what, foreground="#555", wraplength=300, justify="left").pack(anchor="w")
        if kind == "historic":
            ttk.Button(side, text="Picture...", command=lambda: self.pick_picture(name)).pack(anchor="w", pady=4)
        else:
            ttk.Label(side, text="every %s event shows this one (disaster_%s.tga)" % (kind, kind),
                      foreground="#555").pack(anchor="w")
        if shown:
            try:
                from PIL import Image, ImageTk
                with Image.open(shown) as im:
                    im = im.convert("RGB")
                    im.thumbnail((240, 110))
                    self._ph = ImageTk.PhotoImage(im)
                pic.configure(image=self._ph)
            except Exception:
                pic.configure(text="(cannot be shown)")

    def pick_picture(self, name):
        from tkinter import filedialog
        path = filedialog.askopenfilename(parent=self, title="The picture for %s" % name, filetypes=[
            ("Pictures", "*.png *.jpg *.jpeg *.tga *.bmp *.dds"), ("All files", "*.*")])
        if not path:
            return
        self.pictures[name] = path
        self.show()
        n = len(self.edits) + len(self.removed) + len(self.new) + len(self.texts) + len(self.pictures)
        self.lbl.configure(text="%d change(s) - Preview, then Write it in." % n)

    def show_on_map(self, x, y):
        if not (x.strip().lstrip("-").isdigit() and y.strip().lstrip("-").isdigit()):
            messagebox.showinfo(TITLE, "This event has no place - it is a message only.", parent=self)
            return
        app = self.app
        if hasattr(app, "show_map"):
            app.v_work.set(app.v_mode.get())
            app.work_changed()
            app.nb.select(3)
            app.show_map()
            app.update()
            app.map_view.centre_on((int(x), int(y)), zoom=8)

    # ---- changes ----
    def add(self):
        name = simpledialog.askstring(TITLE, "Name of the new event (letters, digits and _ - also the key of its "
                                             "texts):", parent=self)
        if not name:
            return
        name = name.strip()
        if not EV.RE_NAME.match(name) or name.lower() in {e["name"].lower() for e in self.rows()}:
            messagebox.showerror(TITLE, "'%s': letters, digits and _ only, and not the name of another event." % name,
                                 parent=self)
            return
        kind = simpledialog.askstring(TITLE, "Kind of event (%s):" % ", ".join(EV.KINDS), initialvalue="historic",
                                      parent=self)
        if not kind:
            return
        self.new.append({"kind": kind.strip(), "name": name, "date": "1" if not self.rome else "1 summer",
                         "position": None})
        self.fill(name)

    def remove(self):
        name = (self.tv.selection() or [None])[0]
        if not name:
            return
        if any(x["name"] == name for x in self.new):
            self.new = [x for x in self.new if x["name"] != name]
        else:
            self.removed.append(name)
            self.edits.pop(name, None)
        self.fill()

    def _plan(self):
        plan = Plan(self.mod, "events", "events", {})
        new = []
        for x in self.new:
            n = dict(x)
            n["title"] = self.texts.get(x["name"] + "_TITLE")
            n["body"] = self.texts.get(x["name"] + "_BODY")
            new.append(n)
        texts = {k: v for k, v in self.texts.items() if not any(k.startswith(x["name"] + "_") for x in self.new)}
        EV.apply(plan, self.campaign, {"edit": self.edits, "remove": self.removed, "new": new, "texts": texts,
                                       "pictures": self.pictures})
        return plan

    def preview(self):
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        if not plan.changed_files():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        self.app.show_text("Events - preview (nothing written)", plan.report())

    def write(self):
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        if not plan.changed_files():
            messagebox.showinfo(TITLE, "Nothing changed yet.", parent=self)
            return
        if self.app.pending_parts():
            messagebox.showerror(TITLE, "Other changes of the window wait for Apply - Apply (or undo) them first: "
                                        "the mod is read again after this write.", parent=self)
            return
        if not messagebox.askyesno(TITLE, "%s\n\nWrite it? A backup is made first (Tools > Restore undoes it)."
                                   % plan.report()[:1500], parent=self):
            return
        bdir = plan.apply()
        from . import log
        log.write("Events changed (backup %s)\n%s" % (bdir, plan.report()))
        self.app.load()
        self.mod = self.app.mod
        self.edits, self.removed, self.new, self.texts, self.pictures = {}, [], [], {}, {}
        self.reload()
        self.app.status.set("Events written (backup %s)." % bdir)


def open_events(app):
    if not app.mod:
        messagebox.showinfo(TITLE, "Load a mod first (Mod or Browse..., then Load).", parent=app)
        return
    if not EV.path_of(app.mod, app.v_campaign.get()):
        messagebox.showinfo(TITLE, "The campaign %s has no descr_events.txt." % app.v_campaign.get(), parent=app)
        return
    EventsWindow(app)
