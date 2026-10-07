"""Events... (top row): the campaign's events (descr_events.txt) - their date, place, the title and
text players see; new ones, removed ones; Show on the map. Below them, the factions that appear later in the
campaign (emergence.py: by an event, a faction's shadow, split off in a revolt) - shown and changed. Preview /
Write it in, with a backup like every write."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .gui_util import one_window, ShortHint
from .gui_util import scroll_body
from . import events as EV
from .plan import Plan

TITLE = "Events and later factions"


@one_window
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
                "years from the start, or two - the game picks one between them, like '210 220'"))).pack(fill="x")
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
        from . import emergence as EM
        ShortHint(later, foreground="#555", justify="left", wraplength=1000, text=(
            "Factions that start dead and come in later: by an event, as the shadow of a faction (its civil war) "
            "or splitting off a faction in a revolt. " + EM.HOW)).pack(anchor="w")
        lt = ttk.Frame(later)
        lt.pack(fill="x")
        lb = ttk.Frame(lt)                   # the buttons first: the list takes what is left, the buttons stay whole
        lb.pack(side="right", fill="y", padx=(6, 0))
        self.b_change = ttk.Button(lb, text="Change...", command=self.change_later, state="disabled")
        self.b_change.pack(fill="x")                 # greyed out until a faction of the list is picked
        ttk.Button(lb, text="Another faction...", command=lambda: self.change_later(new=True)).pack(fill="x", pady=4)
        self.ltv = ttk.Treeview(lt, columns=("faction", "how", "back", "when"), show="headings", height=5,
                                selectmode="browse")
        for c, t, w in (("faction", "faction", 140), ("how", "comes in", 260), ("back", "may come back", 130),
                        ("when", "event / campaign script", 360)):
            self.ltv.heading(c, text=t)
            self.ltv.column(c, width=w, minwidth=w if c == "back" else 60, stretch=c == "when")
        self.ltv.pack(side="left", fill="x", expand=True)
        self.ltv.bind("<Double-1>", lambda e: self.change_later())
        self.ltv.bind("<<TreeviewSelect>>", lambda e: self.b_change.configure(
            state="normal" if self.ltv.selection() else "disabled"))
        self.later = {}                      # {faction: {'way', 'of', 're_emergent', 'date', 'region'}} not written yet
        bar = ttk.Frame(top)
        bar.pack(fill="x", pady=(6, 0))
        self.lbl = ttk.Label(bar, text="", foreground="#555")
        self.lbl.pack(side="left")
        from .gui_util import close_guard               # never closes over unwritten changes silently
        close = close_guard(self, "Events", lambda: bool(self.edits or self.removed or self.new or self.texts
                                                         or self.pictures or self.later), self.write)
        ttk.Button(bar, text="Close", command=close).pack(side="right")
        ttk.Button(bar, text="Write it in", command=self.write).pack(side="right", padx=4)
        ttk.Button(bar, text="Preview", command=self.preview).pack(side="right")
        self.reload()

    # ---- factions that appear later ----
    def fill_later(self):
        from . import emergence as EM
        self.ltv.delete(*self.ltv.get_children())
        if hasattr(self, "b_change"):
            self.b_change.configure(state="disabled")
        rows = {r["faction"]: r for r in EM.later_rows(self.mod, self.campaign)}
        for fac, ch in self.later.items():
            rows[fac] = dict(faction=fac, way=ch["way"], of=ch.get("of"), re_emergent=ch.get("re_emergent"),
                             event={"date": ch.get("date"), "region": ch.get("region")} if ch["way"] == "event"
                             else None, script=[], changed=True)
        for fac, r in rows.items():
            ev = r.get("event")
            when = ("event: %s%s" % (ev.get("date") or "", " in %s" % ev["region"] if ev.get("region") else
                                     " at %s, %s" % ev["position"] if ev.get("position") else "")) if ev else \
                ("script: " + "; ".join(r.get("script") or [])) if r.get("script") else \
                ("no event - the engine's own events only" if r["way"] == "event" else "")
            if r["way"] != "map":
                how = EM.describe(r["way"], r.get("of"), short=True)
            elif r.get("changed"):
                how = "on the map from the start (no longer later)"
            else:
                how = "dead at the start (no way in named)"
            self.ltv.insert("", "end", iid=fac, values=(fac + (" *" if r.get("changed") else ""), how,
                                                        "yes" if r.get("re_emergent") else "", when))

    def change_later(self, new=False):
        """A faction's way into the campaign: on the map, by an event, shadow, split-off (written with Write it in)."""
        from . import emergence as EM
        from .gui import WAY_KEYS, WAY_LABELS
        from .gui_util import FactionBox
        sel = self.ltv.selection()
        if not new and not sel:
            messagebox.showinfo(TITLE, "Click a faction in the list first, then Change... - or Another faction... for one not listed.", parent=self)
            return
        facs = [n for n, _ in self.mod.factions() if n != "slave"]
        fac0 = sel[0] if sel and not new else ""
        tie = EM.ties(self.mod)
        st = EM.strat_state(self.mod, self.campaign).get(fac0, {})
        way0, of0 = EM.way_of(self.mod, fac0, tie) if fac0 else ("event", None)
        ev0 = EM.emergent_events(self.mod, self.campaign).get(fac0) or {}
        ch = self.later.get(fac0) or {"way": way0 if (way0 != "map" or not st.get("dead")) else "event", "of": of0,
                                      "re_emergent": st.get("re_emergent", True), "date": ev0.get("date") or "",
                                      "region": ev0.get("region") or ""}
        w = tk.Toplevel(self)
        w.title("How a faction comes into the campaign")
        w.transient(self)
        fr = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
        v_fac, v_way = tk.StringVar(value=fac0), tk.StringVar(value=WAY_LABELS[WAY_KEYS.index(ch["way"])])
        v_of, v_date, v_reg = tk.StringVar(value=ch.get("of") or ""), tk.StringVar(value=ch.get("date") or ""), \
            tk.StringVar(value=ch.get("region") or "")
        v_back = tk.BooleanVar(value=bool(ch.get("re_emergent")))
        from .limits import engine_of
        engine = engine_of(self.mod)
        v_home = tk.BooleanVar(value=bool(ch.get("homeless", EM.homeless(self.mod, fac0) if fac0 else False)))
        ttk.Label(fr, text="Faction").grid(row=0, column=0, sticky="w", pady=2)
        cb = FactionBox(fr, v_fac, state="readonly" if new else "disabled", width=30)
        cb["values"] = facs
        cb.grid(row=0, column=1, sticky="w")
        ttk.Label(fr, text="Comes in").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Combobox(fr, textvariable=v_way, values=[WAY_LABELS[WAY_KEYS.index(k)] for k in EM.ways_for(self.mod)],
                     state="readonly", width=48).grid(row=1, column=1, sticky="w")
        ttk.Label(fr, text="of (shadow / splits off)").grid(row=2, column=0, sticky="w", pady=2)
        cbo = FactionBox(fr, v_of, state="readonly", width=30)
        cbo["values"] = facs
        cbo.grid(row=2, column=1, sticky="w")
        ttk.Label(fr, text="event date").grid(row=3, column=0, sticky="w", pady=2)
        dr = ttk.Frame(fr)
        dr.grid(row=3, column=1, sticky="w")
        ttk.Entry(dr, textvariable=v_date, width=14).pack(side="left")
        self._when(dr, v_date)
        ttk.Label(fr, text="event region (a rebel one)").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Combobox(fr, textvariable=v_reg, values=EM.rising_regions(self.mod, self.campaign), state="readonly",
                     width=30).grid(row=4, column=1, sticky="w")
        ttk.Checkbutton(fr, text="may come back after it dies (re_emergent)", variable=v_back).grid(
            row=5, column=1, sticky="w", pady=2)
        hb = ttk.Checkbutton(fr, text="lives without towns - stays in the game with none (can_homeless, %s)" % (
            engine.replace(".exe", "") if engine else "REX / M2EX only"), variable=v_home)
        hb.grid(row=8, column=1, sticky="w", pady=2)
        if not engine:
            hb.state(["disabled"])
        ttk.Label(fr, foreground="#666", wraplength=460, justify="left", text=(
            "A faction that comes in later must hold no towns and no characters (give them away first). The date is "
            "%s. Written with Write it in below." % ("years from the start and optionally summer or winter" if
                                                     self.rome else "years from the start, or two"))).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))

        def ok():
            fac = v_fac.get()
            way = WAY_KEYS[WAY_LABELS.index(v_way.get())]
            if not fac:
                messagebox.showerror(TITLE, "Pick the faction.", parent=w)
                return
            got = {"way": way, "of": v_of.get() or None, "re_emergent": v_back.get(), "date": v_date.get().strip(),
                   "region": v_reg.get() or None, "homeless": v_home.get() if engine else None}
            try:                                     # refused now, not at Write: the same checks on a throw-away plan
                EM.apply(Plan(self.mod, "later", fac, {}), self.campaign, fac, **got)
            except Exception as e:
                messagebox.showerror(TITLE, str(e), parent=w)
                return
            self.later[fac] = got
            w.destroy()
            self.fill_later()
            self.lbl.configure(text="%s: changed - Preview / Write it in" % fac)
        bb = ttk.Frame(fr)
        bb.grid(row=9, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(bb, text="Cancel", command=w.destroy).pack(side="right")
        ttk.Button(bb, text="OK", command=ok).pack(side="right", padx=4)

    # ---- reading ----
    def reload(self):
        from .strtables import strings
        path = EV.path_of(self.mod, self.campaign)
        self.events = EV.read(self.mod.load(path)) if path else []
        self.shown = strings(self.mod, "historic_events.txt")
        self.fill()
        self.fill_later()

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
        ttk.Label(r, text="  years from the start (Rome: a word summer / winter may follow)" if self.rome
                  else "  years from the start", foreground="#555").pack(side="left")
        self._when(r, v_date)
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
        mine = self.pictures.get(EV.picture_name(name, kind))
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
        ttk.Button(side, text="Picture...", command=lambda: self.pick_picture(EV.picture_name(name, kind))).pack(
            anchor="w", pady=4)
        if kind != "historic":
            ttk.Label(side, text="The game shows one picture for every %s - a new one here is shown for all of them "
                                 "(disaster_%s.tga)." % (kind, kind),
                      foreground="#555", wraplength=300, justify="left").pack(anchor="w")
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
        self.new.append({"kind": kind.strip(), "name": name, "date": EV.turn_date(self.mod, self.campaign, 2),
                         "position": None})
        self.fill(name)

    def _when(self, parent, var):
        """A label beside a date: the turn and the year it means (start_date / timescale of descr_strat.txt)."""
        lbl = ttk.Label(parent, foreground="#555")
        lbl.pack(side="left", padx=6)

        def show(*_):
            w = EV.when(self.mod, self.campaign, var.get().strip())
            lbl.configure(text=("= " + w) if w else "")
        var.trace_add("write", show)
        show()
        return lbl

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
        from . import emergence as EM
        for fac, ch in sorted(self.later.items()):
            EM.apply(plan, self.campaign, fac, **ch)
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
        self.later = {}
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
