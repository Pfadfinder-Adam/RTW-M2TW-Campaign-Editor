"""Settlements (a work of the top row): every region and its town of the campaign - the names in the files, the names players see,
the owner, names by culture - and the places to change them: the names players see (quick, as on the Map), the names
in the files (regionrename: everywhere the mod names them, Preview, a backup), names by the owner's culture (REX /
M2EX). Both games."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import ask
from .gui_util import ShortHint
from .gui_util import scroll_body
from . import log
from . import theme

APP = "RTW & M2TW Campaign Editor"


class SettlementsPanel(ttk.Frame):
    """Settlements (a work of the top row): every region and its town - the names in the files, the names players
    see, the owner, and one column for each culture's name of the town (REX / M2EX rename a town by its owner's
    culture; once a window of its own, Culture names...). A culture's cell is typed in place; the changes wait for
    Apply like the rest of the campaign's work."""
    kind = "settlements"
    EMPTY = "-"

    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app, self.mod = app, None
        self.rows, self.cultures, self.saved, self.foreign = [], [], {}, {}
        self.sort, self.edit = ("region", False), None
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Settlements", font=("", 10, "bold")).pack(side="left")
        ttk.Label(top, text="   Find").pack(side="left")
        self.v_find = tk.StringVar()
        ttk.Entry(top, textvariable=self.v_find, width=20).pack(side="left", padx=4)
        ttk.Label(top, text="Culture").pack(side="left", padx=(10, 0))
        self.v_cult = tk.StringVar(value="(all)")
        self.cb_cult = ttk.Combobox(top, textvariable=self.v_cult, state="readonly", width=16)
        self.cb_cult.pack(side="left", padx=4)
        ttk.Label(top, text="Show").pack(side="left", padx=(10, 0))
        self.v_show = tk.StringVar(value="every town")
        ttk.Combobox(top, textvariable=self.v_show, state="readonly", width=30, values=[
            "every town", "with a name for this culture", "without a name for this culture",
            "with any name by culture", "without any", "changed, waiting for Apply",
            "renamed by the mod's own script"]).pack(side="left", padx=4)
        ttk.Label(top, text="Owner's culture").pack(side="left", padx=(10, 0))
        self.v_owner = tk.StringVar(value="(all)")
        self.cb_owner = ttk.Combobox(top, textvariable=self.v_owner, state="readonly", width=14)
        self.cb_owner.pack(side="left", padx=4)
        for v in (self.v_find, self.v_cult, self.v_show, self.v_owner):
            v.trace_add("write", lambda *a: self.fill())
        self.lbl_n = ttk.Label(top, foreground="#666")
        self.lbl_n.pack(side="left", padx=6)
        self.hint = ShortHint(self, foreground="#666", wraplength=1100, justify="left", text="")
        self.hint.pack(anchor="w", pady=(4, 4))
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        side = ttk.Frame(body, padding=(8, 0))
        side.pack(side="right", fill="y")
        for text, cmd in (("Names players see...", self.shown_names),
                          ("Rename in the files...", self.rename_files),
                          ("Names by culture...", self.by_culture),
                          ("Clear the town's names", self.clear_town),
                          ("Show on the map", self.show_on_map)):
            ttk.Button(side, text=text, command=cmd).pack(anchor="w", pady=2)
        ttk.Label(side, foreground="#666", wraplength=200, justify="left", text=(
            "double click a culture's cell: type the town's name for that culture (Enter keeps it, Esc drops it, "
            "empty = none); elsewhere: the names players see")).pack(anchor="w", pady=(10, 0))
        self.tv = ttk.Treeview(body, show="tree headings")
        self.tv.pack(side="left", fill="both", expand=True)
        self.tv.tag_configure("changed", foreground=theme.ink("#1a6fd0", "field"))
        self.tv.tag_configure("foreign", foreground=theme.ink("#999", "field"))
        self.tv.bind("<Double-1>", self.dbl)

    # ---- what the window asks of a work ----
    def rebind(self, mod):
        self.mod = mod
        self.load()
        return 0

    def dirty(self):
        return False                          # its changes sit in the campaign work (Apply writes them with it)

    def pending(self):
        return 0

    def make_plan(self):
        return self.app._faction_plan()

    # ---- reading ----
    def load(self):
        from . import culturenames as CN
        app = self.app
        self.rows = []
        if not app.mod or not app.strat:
            self.fill()
            return
        camp = app.v_campaign.get()
        self.cultures = CN.cultures(app.mod)
        self.cols = [CN.DEFAULT] + self.cultures
        self.saved = CN.read(app.mod, camp)                # what the campaign's script holds now
        self.foreign = CN.foreign(app.mod, camp)
        self.cb_cult["values"] = ["(all)", "every other"] + self.cultures
        self.cb_owner["values"] = ["(all)"] + self.cultures
        eng, rex = CN.engine(app.mod)
        self.hint.lbl.configure(foreground="#666" if rex else "#a33")
        self.hint.configure(text=(
            "Every region and its town. The names players see are quick to change; the names in the files tie the "
            "game's files together - renaming them changes every file of the mod that names the place (shown "
            "before anything is written). Each culture's column: the town's name when an owner of that culture "
            "holds it - %s renames it when it changes hands ('every other' for the cultures with no name of their "
            "own); Shown now = the name under its owner as the next Apply leaves it; grey rows are renamed by the "
            "mod's own campaign script." % eng) if rex else (
            "Every region and its town. The names by culture need %s: the game folder has no %s.exe, so they are "
            "not written - the table still shows and keeps them." % (eng, eng)))
        heads = [("town", "Town (in the files)", 120), ("shown", "Region - players see", 150),
                 ("town_shown", "Town - players see", 130), ("owner", "Owner", 170), ("oc", "Owner's culture", 100),
                 ("now", "Shown now", 120)] + \
                [("c:" + c, "every other" if c == CN.DEFAULT else c, 95) for c in self.cols]
        import tkinter.font as tkfont
        bold = tkfont.nametofont("TkHeadingFont")
        fit = lambda text, width: max(width, bold.measure(text) + 24)     # a heading never cut
        self.tv.configure(columns=[k for k, _, _ in heads])
        self.tv.heading("#0", text="Region (in the files)", command=lambda: self.sort_by("region"))
        self.tv.column("#0", width=fit("Region (in the files)", 150), stretch=False)
        for k, text, width in heads:
            self.tv.heading(k, text=text, command=lambda k=k: self.sort_by(k))
            self.tv.column(k, width=fit(text, width), stretch=False)
        self.fill()

    def _table(self):
        t = {k: dict(v) for k, v in self.saved.items()}
        for k, v in self.app.culture_names.items():
            if v:
                t[k] = dict(v)
            else:
                t.pop(k, None)
        return t

    def _rows(self):
        from . import culturenames as CN
        from .regionedit import shown_labels
        from .build import faction_label
        app = self.app
        camp = app.v_campaign.get()
        me = app.v["template"].get().strip() if app.editing() else (app.v["name"].get().strip().lower() or "(new)")
        owners = app.owners_after(me)                      # the towns as the next Apply leaves them
        cultures = dict(app.mod.factions())
        if me not in cultures:                             # the new faction: its template's culture
            cultures[me] = cultures.get(app.v["template"].get().strip())
        towns = {r: i.get("settlement") or "" for r, i in app.regions.items()}
        towns.update({r["name"]: r.get("settlement") or "" for r in app.new_regions})
        shown = shown_labels(app.mod, camp, list(towns) + [t for t in towns.values() if t])
        labels = app.shown_names() if hasattr(app, "shown_names") else {}
        table = self._table()
        out = []
        for region, town in towns.items():
            owner = owners.get(region) or "slave"
            oc = cultures.get(owner) or ""
            names = table.get(town) or {}
            now = (CN.name_for(names, oc) or CN.shown_name(app.mod, camp, town)) if town else ""
            out.append({"region": region, "town": town, "shown": shown.get(region, ""),
                        "town_shown": shown.get(town, "") if town else "",
                        "owner": faction_label(owner, labels.get(owner)) if owner != "slave" else "rebels",
                        "oc": oc, "now": now, "names": names, "changed": town in app.culture_names,
                        "foreign": town in self.foreign})
        return out

    def fill(self):
        from . import culturenames as CN
        tv = getattr(self, "tv", None)
        if tv is None or not tv.winfo_exists():
            return
        tv.delete(*tv.get_children())
        if not self.app.mod or not self.app.strat:
            self.lbl_n.configure(text="")
            return
        cult = self.v_cult.get()
        key = CN.DEFAULT if cult == "every other" else (None if cult == "(all)" else cult)
        show, oc, q = self.v_show.get(), self.v_owner.get(), self.v_find.get().lower().strip()
        every = self._rows()
        rows = []
        for r in every:
            names = r["names"]
            if oc != "(all)" and r["oc"] != oc:
                continue
            if q and not any(q in str(x).lower() for x in (r["region"], r["town"], r["shown"], r["town_shown"],
                                                           r["owner"], r["now"], *names.values())):
                continue
            has = bool(names.get(key)) if key else bool(names)
            if (show == "with a name for this culture" and not has or
                    show == "without a name for this culture" and has or
                    show == "with any name by culture" and not names or show == "without any" and names or
                    show == "changed, waiting for Apply" and not r["changed"] or
                    show == "renamed by the mod's own script" and not r["foreign"]):
                continue
            rows.append(r)
        k, rev = self.sort
        if k.startswith("c:"):
            c = k[2:]
            rows.sort(key=lambda r: (not r["names"].get(c), (r["names"].get(c) or "").lower(), r["region"]),
                      reverse=rev)
        else:
            rows.sort(key=lambda r: (str(r[k]).lower(), r["region"].lower()), reverse=rev)
        for r in rows:
            vals = [r["town"], r["shown"], r["town_shown"], r["owner"], r["oc"], r["now"]] + \
                   [r["names"].get(c) or self.EMPTY for c in self.cols]
            tags = ("foreign",) if r["foreign"] else ("changed",) if r["changed"] else ()
            tv.insert("", "end", iid=r["region"], text=r["region"], values=vals, tags=tags)
        self.lbl_n.configure(text="%d of %d; %d name change(s) wait for Apply" % (
            len(rows), len(every), len(self.app.culture_names)))

    def sort_by(self, k):
        self.sort = (k, not self.sort[1] if self.sort[0] == k else False)
        self.fill()

    def picked(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showerror(APP, "Pick a settlement in the list first (a click on its line).", parent=self)
            return None
        return sel[0]

    # ---- editing ----
    def dbl(self, e):
        row, col = self.tv.identify_row(e.y), self.tv.identify_column(e.x)
        if not row:
            return
        cols = self.tv["columns"]
        i = int(col[1:]) - 1 if col and col != "#0" else -1
        k = cols[i] if 0 <= i < len(cols) else ""
        if not k.startswith("c:"):
            self.tv.selection_set(row)
            self.shown_names()
            return
        town = self.tv.set(row, "town")
        if not town:
            return
        if town in self.foreign:
            self.lbl_n.configure(text="%s is renamed by the mod's own campaign script (%d line(s)) - change it "
                                      "there, not here" % (town, self.foreign[town]))
            return
        self.cell(row, k, town)

    def _after_dialog(self):
        """Fills the table again once the dialog a button opened is closed."""
        if not self.winfo_exists():
            return
        if any(isinstance(x, tk.Toplevel) and x.winfo_exists() and x.winfo_viewable()
               for x in self.app.winfo_children()):
            self.after(300, self._after_dialog)
            return
        self.fill()

    def cell(self, row, k, town):
        if self.edit:
            self.edit.destroy()
        self.tv.see(row)
        box = self.tv.bbox(row, k)
        if not box:
            return
        x, y, wd, ht = box
        v = tk.StringVar(value=(self._table().get(town) or {}).get(k[2:], ""))
        en = self.edit = ttk.Entry(self.tv, textvariable=v)
        en.place(x=x, y=y, width=max(wd, 120), height=ht)
        en.focus_set()
        en.select_range(0, "end")

        def keep(*a):
            if self.edit is en:
                self.edit = None
                self.set_name(town, k[2:], v.get().strip())
            en.destroy()

        def drop(*a):
            self.edit = None
            en.destroy()
        en.bind("<Return>", keep)
        en.bind("<KP_Enter>", keep)
        en.bind("<Escape>", drop)
        en.bind("<FocusOut>", keep)

    def set_name(self, town, culture, name):
        from . import culturenames as CN
        names = dict(self._table().get(town) or {})
        if (names.get(culture) or "") == name:
            return
        if name:
            names[culture] = name
        else:
            names.pop(culture, None)
        bad = CN.problems(self.app.mod, {town: names}) if names else []
        if bad:
            self.lbl_n.configure(text="; ".join(bad), foreground=theme.ink("#a33"))
            return
        self.lbl_n.configure(foreground="#666")
        self.app.remember()
        self.app.culture_names[town] = names          # {} = the town's names are dropped with the next Apply
        self.app.fill_towns()
        self.app._mark_work()
        self.fill()

    def clear_town(self):
        for row in self.tv.selection():
            town = self.tv.set(row, "town")
            if town and town not in self.foreign:
                self.app.remember()
                self.app.culture_names[town] = {}
        self.app.fill_towns()
        self.app._mark_work()
        self.fill()

    # ---- actions ----
    def shown_names(self):
        region = self.picked()
        if region:
            self.app.new_region_dialog(edit=region)
            self.after(300, self._after_dialog)

    def by_culture(self):
        region = self.picked()
        if region:
            self.app.culture_names_dialog(region)
            self.after(300, self._after_dialog)

    def show_on_map(self):
        region = self.picked()
        if not region:
            return
        app = self.app
        xy = app.mod.city_tiles(app.v_campaign.get()).get(region)
        app.v_work.set("map")                            # Maps (whatever work was on, nothing is lost)
        app.work_changed()
        app.update()
        if xy:
            app.map_view.centre_on(tuple(xy), zoom=6)

    def rename_files(self):
        region = self.picked()
        if region:
            rename_in_files(self.app, region, self)


def rename_now(app, campaign, region, new_region, new_town, parent):
    """The region's and its town's names in the files changed everywhere the mod names them, written at once
    with a backup (asked first, the whole list of changes shown), the mod read again. -> True when written."""
    from .plan import Plan
    from .regionrename import problems, rename
    town = (app.mod.regions(campaign).get(region) or {}).get("settlement") or ""
    why = problems(app.mod, campaign, region, new_region, new_town)
    if why:
        messagebox.showerror(APP, "\n".join(why), parent=parent)
        return False
    if app.pending_parts():
        messagebox.showerror(APP, "Other changes wait for Apply. Apply (or undo) them first - they were made "
                                  "with the old names.", parent=parent)
        return False
    p = Plan(app.mod, "rename", new_region)
    try:
        rename(p, campaign, region, new_region, new_town)
    except ValueError as e:
        messagebox.showerror(APP, str(e), parent=parent)
        return False
    if not p.changed_files():
        return False
    if p.warnings and not ask(APP, "%s\n\nWrite %d file(s) now? A backup is made first (Tools > Restore undoes "
                                    "it)." % (p.report(), len(p.changed_files())), parent=parent, yes='Write it in', no='Cancel'):
        return False
    bdir = p.apply()
    log.write("Renamed in the files: %s / %s -> %s / %s (backup %s)\n%s" % (
        region, town, new_region, new_town, bdir, p.report()))
    app.load()
    app.status.set("Renamed in the files (backup %s). Check the names players see (Settlements...), then "
                   "start the game - it builds map.rwm again." % bdir)
    return True


def rename_in_files(app, region, parent):
    """The region's and its town's names in the files, changed everywhere the mod names them: a window with the
    new names, Preview (every file and line), then written with a backup at once and the mod read again. The
    Settlements... and Maps (Edit regions) open it."""
    if region not in app.mod.regions(app.v_campaign.get()):
        messagebox.showerror(APP, "%s is not in the campaign's files yet - a new region takes its names in Edit "
                                  "region...; after Apply it can be renamed here." % region, parent=parent)
        return
    from .plan import Plan
    from .regionrename import problems, rename
    campaign = app.v_campaign.get()
    town = (app.mod.regions(campaign).get(region) or {}).get("settlement") or ""
    w = tk.Toplevel(parent)
    w.title("Rename in the files - %s / %s" % (region, town))
    w.transient(parent)
    frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
    ttk.Label(frm, justify="left", wraplength=560, text=(
        "The names the game's files use for this place. Every text file of the mod that names it gets the new "
        "name: descr_regions, descr_strat, the names lookup and texts, mercenaries, win conditions, scripts, "
        "trait and ancillary conditions (SettlementName ...). Words in comments and descriptions stay; a line "
        "that names a faction of the same name stays. map.rwm is removed (the game builds it again). "
        "Letters, digits and _ only.")).grid(row=0, column=0, columnspan=3, sticky="w")
    v_region, v_town = tk.StringVar(value=region), tk.StringVar(value=town)
    for i, (label, var, now) in enumerate((("Region", v_region, region), ("Town", v_town, town))):
        ttk.Label(frm, text=label).grid(row=i + 1, column=0, sticky="w", pady=2)
        ttk.Entry(frm, textvariable=var, width=30).grid(row=i + 1, column=1, sticky="w", padx=6)
        ttk.Label(frm, text="now %s" % now, foreground="#666").grid(row=i + 1, column=2, sticky="w")

    def plan():
        names = (v_region.get().strip(), v_town.get().strip())
        why = problems(app.mod, campaign, region, *names)
        if why:
            messagebox.showerror(APP, "\n".join(why), parent=w)
            return None
        p = Plan(app.mod, "rename", names[0])
        try:
            rename(p, campaign, region, *names)
        except ValueError as e:
            messagebox.showerror(APP, str(e), parent=w)
            return None
        if not p.changed_files():
            messagebox.showinfo(APP, "Nothing to change - the names are as they are.", parent=w)
            return None
        return p

    def preview():
        p = plan()
        if p:
            app.show_text("Rename in the files - nothing written yet", p.report())

    def write():
        if rename_now(app, campaign, region, v_region.get().strip(), v_town.get().strip(), w):
            w.destroy()

    bar = ttk.Frame(frm)
    bar.grid(row=3, column=0, columnspan=3, sticky="e", pady=(10, 0))
    ttk.Button(bar, text="Preview", command=preview).pack(side="left")
    ttk.Button(bar, text="Rename", command=write).pack(side="left", padx=4)
    ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")


def merge_regions(app, keep, gone, parent=None):
    """Merge regions: the region `gone` and its town go from the campaign in every file that ties them, all its land
    (and port) becomes `keep`'s - regiondelete.delete(..., into=keep); `keep` stays as it is. Asked in a few words
    (what goes, what is said about it), written with a backup, the mod read again; the map stays in its Merge mode
    for the next pair."""
    from .plan import Plan
    from .mapedit import ports
    from .regiondelete import delete, problems
    parent = parent or app
    campaign = app.v_campaign.get()
    regions = app.mod.regions(campaign)
    for r in (keep, gone):
        if r not in regions:
            messagebox.showerror(APP, "%s is not in the campaign's files yet - Apply the changes first." % r,
                                 parent=parent)
            return None
    if app.pending_parts():
        messagebox.showerror(APP, "Other changes wait for Apply. Apply (or undo) them first - a merged region would "
                                  "leave them pointing at nothing.", parent=parent)
        return None
    town = lambda r: regions[r].get("settlement") or r
    errors, warns = problems(app.mod, campaign, gone, keep)
    if errors:
        messagebox.showerror(APP, "%s cannot join %s:\n\n- %s" % (gone, keep, "\n- ".join(errors)), parent=parent)
        return None
    p = Plan(app.mod, "merge", "%s_into_%s" % (gone, keep))
    try:
        delete(p, campaign, gone, keep)
    except ValueError as e:
        messagebox.showerror(APP, str(e), parent=parent)
        return None
    text = ("%s (%s) joins %s (%s): its town and region go from every file that ties them (%d file(s)), all its "
            "land%s becomes %s's; %s stays as it is.%s\n\nA backup is made first - Undo this write or Tools > "
            "Restore gives everything back." % (
                gone, town(gone), keep, town(keep), len(p.changed_files()),
                " and its port" if gone in ports(app.mod, campaign) else "", keep, keep,
                ("\n\nGood to know:\n- " + "\n- ".join(warns[:5])) if warns else ""))
    if not ask(APP, text, parent=parent, yes="Merge them", no="Not now"):
        return None
    bdir = p.apply()
    log.write("Merged %s into %s (backup %s)\n%s" % (gone, keep, bdir, p.report()))
    app.load()
    app.status.set("%s joined %s (backup %s) - %d region(s) now. Start the game: it builds map.rwm again." % (
        gone, keep, bdir, len(app.mod.regions(campaign))))
    views = [getattr(app, "map_view", None)] + [getattr(e, "view", None) for e in getattr(app, "editors", {}).values()]
    for view in views:
        if view is not None and hasattr(view, "merged"):
            view.merged()
    return bdir


def _map_of(app):
    """The map the regions are shown on while a Delete window is open: the main window's (the Map tab / Maps),
    when it is drawn."""
    view = getattr(app, "map_view", None)
    try:
        return view if view is not None and getattr(view, "cmap", None) and view.winfo_viewable() else None
    except tk.TclError:
        return None


def _beside(app, w, view, width=640):
    """The window at the main window's right (over the legend), the whole map in sight left of it - not in the
    middle over the regions it marks."""
    if view is None:
        return
    try:
        w._centred = True                             # the app's own centring leaves it where it is put
        left = max(0, app.winfo_rootx() + app.winfo_width() - width)
        w.geometry("+%d+%d" % (left, app.winfo_rooty() + 110))
        w.attributes("-alpha", 1.0)
        cv = view.canvas
        view.fit_beside(free=max(0, cv.winfo_rootx() + cv.winfo_width() - left + 10), margin=10)
    except tk.TclError:
        pass


def _reading(app, what):
    """A few words while the mod's files are read for a deletion (a big mod: thousands of them)."""
    try:
        app.status.set("Reading the mod's files for %s..." % what)
        app.config(cursor="watch")
        app.update_idletasks()
    except (tk.TclError, AttributeError):
        pass


def _read(app):
    try:
        app.config(cursor="")
    except tk.TclError:
        pass


WASTE_WORDS = "stays as a wasteland - the region is kept, nobody's (REX / M2EX)"
WASTE_MEANS = ("No town, no owner, no rebels, no economy: the AI never goes for it, no victory counts it, no neighbour "
               "grows. Armies can still walk over it.")
NO_WASTE = "Only with REX / M2EX - the original game knows no wasteland."


def _land_choice(frm, row, waste_ok, v_land, near_widget, wrap):
    """The two ways of a deleted region's land, one under the other: a wasteland (REX / M2EX, the default there) or a
    neighbour's (the only way of the original exes)."""
    box = ttk.Frame(frm)
    box.grid(row=row, column=0, columnspan=2, sticky="we", pady=(8, 2))
    ttk.Label(box, text="Its land", font=("", 9, "bold")).grid(row=0, column=0, sticky="w")
    rb = ttk.Radiobutton(box, text=WASTE_WORDS, variable=v_land, value="waste")
    rb.grid(row=1, column=0, columnspan=2, sticky="w")
    ttk.Label(box, text=NO_WASTE if not waste_ok else WASTE_MEANS, justify="left", wraplength=wrap,
              foreground="#777777").grid(row=2, column=0, columnspan=2, sticky="w", padx=(22, 0))
    if not waste_ok:
        rb.state(["disabled"])
    ttk.Radiobutton(box, text="goes to a neighbour:" if near_widget is not None else
                    "goes to a neighbour (each to the one it shares the longest border with - another picked on the "
                    "map)", variable=v_land, value="near").grid(row=3, column=0, sticky="w", pady=(4, 0))
    if near_widget is not None:
        near_widget(box).grid(row=3, column=1, sticky="w", padx=6, pady=(4, 0))
    return box


def delete_town(app, region, parent):
    """Delete a town together with its region, asked first with the whole list of changes, written with a backup, the
    mod read again. The Map's right click on a town opens it. Its land (report #154): under REX / M2EX it stays as a
    WASTELAND by default - the region kept, nobody's, no neighbour grows (regiondelete waste) - or it goes to a
    neighbour (the only way of the original exes). While it is open the map shows it: grey = stays as a wasteland,
    red = goes, yellow takes its land, green could take it - a click on a green region gives it the land (report
    R-20261008-7696AA). The mod's files are read once for each way (a big mod has thousands of them)."""
    from .plan import Plan
    from .regiondelete import can_waste, delete, neighbours, problems
    campaign = app.v_campaign.get()
    regions = app.mod.regions(campaign)
    if region not in regions:
        messagebox.showerror(APP, "%s is not in the campaign's files yet - Apply the changes first." % region,
                             parent=parent)
        return
    if app.pending_parts():
        messagebox.showerror(APP, "Other changes wait for Apply. Apply (or undo) them first - a deleted region "
                                  "would leave them pointing at nothing.", parent=parent)
        return
    town = regions[region].get("settlement") or region
    waste_ok = can_waste(app.mod)
    asked = {}

    def check(way):
        if way not in asked:
            _reading(app, town)
            try:
                asked[way] = problems(app.mod, campaign, region, waste=way == "waste")
            finally:
                _read(app)
            app.status.set("")
        return asked[way]
    first = "waste" if waste_ok else "near"
    errors, _ = check(first)
    if errors:
        messagebox.showerror(APP, "%s and its region cannot be deleted:\n\n- %s" % (town, "\n- ".join(errors)),
                             parent=parent)
        return
    near = neighbours(app.mod, campaign, region)
    view = _map_of(app)
    w = tk.Toplevel(parent)
    w.title("Delete %s with its region %s" % (town, region))
    w.transient(parent)
    frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
    ttk.Label(frm, justify="left", wraplength=560, text=(
        "The town goes from the campaign in every file that ties it: its settlement of descr_strat, the rebels in the "
        "town with it (a faction's characters there stay, in the field); the region leaves the mercenary pools and "
        "the win conditions. map.rwm is removed (the game builds it again). A backup is made first; Tools > Restore "
        "gives everything back.")).grid(row=0, column=0, columnspan=2, sticky="w")
    v_land = tk.StringVar(value=first)
    labels = ["%s  (%d tiles of border)" % (r, n) for r, n in near] or ["none - it touches no other region's land"]
    v_into = tk.StringVar(value=labels[0])

    def near_box(box):
        cb = ttk.Combobox(box, textvariable=v_into, values=labels, state="readonly" if near else "disabled",
                          width=max(30, max(len(x) for x in labels) + 2))
        cb.bind("<<ComboboxSelected>>", lambda e: v_land.set("near"))
        return cb
    _land_choice(frm, 1, waste_ok, v_land, near_box, 540)
    hint = ttk.Label(frm, justify="left", wraplength=560)
    if view is not None:
        hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
    lbl_err = ttk.Label(frm, justify="left", wraplength=560, foreground="#c0392b")
    lbl_err.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
    lbl_warn = ttk.Label(frm, justify="left", wraplength=560, foreground="#8a5a00")
    lbl_warn.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def into_now():
        return near[labels.index(v_into.get())][0] if near else None

    def way():
        return v_land.get()

    def show():
        errs, warns = check(way())
        lbl_err.configure(text=("Cannot be deleted this way:\n- " + "\n- ".join(errs)) if errs else "")
        lbl_warn.configure(text=("Good to know:\n- " + "\n- ".join(warns[:6]) + ("\n..." if len(warns) > 6 else ""))
                           if warns else "")
        for b in (b_show, b_go):
            b.configure(state="disabled" if errs else "normal")
        if way() == "waste":
            hint.configure(text="On the map: grey = %s stays as a wasteland (its town goes)." % region)
        else:
            hint.configure(text=(
                "On the map: red = %s goes, yellow = the region that takes its land, green = a neighbour that could "
                "take it - click a green one to give it the land." % town))
        if view is None:
            return
        if way() == "waste":
            marks = {region: "waste"}
        else:
            marks = {r: "can" for r, _ in near}
            marks.update({into_now(): "into", region: "gone"})
        try:
            view.mark_regions(marks, clicked)
        except tk.TclError:
            pass

    def clicked(r):
        names = [n for n, _ in near]
        if r in names:
            v_land.set("near")
            v_into.set(labels[names.index(r)])
        elif r == region:
            view.readout.configure(text="%s - %s" % (town, "its region stays as a wasteland" if way() == "waste"
                                                     else "goes; click a green neighbour to give it the land"))
        else:
            view.readout.configure(text="%s does not touch %s - its land can go only to a green neighbour" % (
                r or "the sea", region))

    def unmark(e=None):
        if e is not None and e.widget is not w:
            return
        if view is not None:
            try:
                view.mark_regions(None)
            except tk.TclError:
                pass
    w.bind("<Destroy>", unmark, add="+")

    def plan():
        errs, warns = check(way())
        if errs:
            return None
        p = Plan(app.mod, "delete", region)
        try:
            delete(p, campaign, region, into_now(), checked=True, waste=way() == "waste")   # read already
        except ValueError as e:
            messagebox.showerror(APP, str(e), parent=w)
            return None
        for x in warns:
            p.warn(None, x)
        return p

    def preview():
        p = plan()
        if p:
            app.show_text("Delete %s with its region - nothing written yet" % town, p.report())

    def write():
        p = plan()
        if not p:
            return
        if way() == "waste":
            text = ("%s\n\nDelete %s now (%d file(s))? Its region %s stays as a wasteland - nobody's land with no "
                    "town (REX / M2EX read it so); no neighbour grows. A backup is made first (Tools > Restore undoes "
                    "it)." % (p.report(), town, len(p.changed_files()), region))
        else:
            text = ("%s\n\nDelete %s and its region %s now (%d file(s))? Every tile of it becomes %s's - no land is "
                    "left without a region (the game wants each tile in one). A backup is made first (Tools > Restore "
                    "undoes it)." % (p.report(), town, region, len(p.changed_files()), into_now()))
        if not ask(APP, text, parent=w, yes='Delete it', no='Keep it', danger=True):
            return
        bdir = p.apply()
        log.write("Deleted %s with its region %s%s (backup %s)\n%s" % (
            town, region, " - a wasteland now" if way() == "waste" else "", bdir, p.report()))
        w.destroy()
        app.load()
        app.status.set("%s deleted%s (backup %s). Start the game - it builds map.rwm again." % (
            town, " - %s is a wasteland now" % region if way() == "waste" else " with its region %s" % region, bdir))

    bar = ttk.Frame(frm)
    bar.grid(row=5, column=0, columnspan=2, sticky="e", pady=(10, 0))
    b_show = ttk.Button(bar, text="Preview", command=preview)
    b_show.pack(side="left")
    b_go = ttk.Button(bar, text="Delete", command=write)
    b_go.pack(side="left", padx=4)
    ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")
    v_land.trace_add("write", lambda *a: show())
    v_into.trace_add("write", lambda *a: show())
    _beside(app, w, view)
    show()
    return w


def delete_towns(app, picked, parent):
    """Many towns deleted with their regions at once - the map's Select, right click (report R-20261008-7696AA): the
    mod's files read once for all of them (regiondelete.refusals). Their land (report #154): under REX / M2EX each
    region stays as a WASTELAND by default (nobody's, no neighbour grows); or each region's land goes to the neighbour
    that stays it shares the longest border with (receivers) - a row picked (or its red region clicked on the map)
    shows its neighbours that could take its land in green, a click gives them it. One plan: one backup, one Undo."""
    from .plan import Plan
    from .regiondelete import can_waste, delete_many, neighbours, receivers, refusals
    campaign = app.v_campaign.get()
    regions = app.mod.regions(campaign)
    gone = sorted(r for r in picked if r in regions)
    if len(gone) == 1:
        return delete_town(app, gone[0], parent)
    if not gone:
        messagebox.showerror(APP, "None of the selected regions is in the campaign's files yet - Apply the changes "
                                  "first.", parent=parent)
        return None
    if app.pending_parts():
        messagebox.showerror(APP, "Other changes wait for Apply. Apply (or undo) them first - a deleted region "
                                  "would leave them pointing at nothing.", parent=parent)
        return None
    town = {r: regions[r].get("settlement") or r for r in gone}
    waste_ok = can_waste(app.mod)
    state = {"chosen": {}, "sel": None, "asked": {}, "near": None}

    def check(way):
        """(refusals, warnings) of a way, the files read once for it."""
        if way not in state["asked"]:
            _reading(app, "%d towns" % len(gone))
            try:
                state["asked"][way] = refusals(app.mod, campaign, gone, waste=way == "waste")
                if way == "near" and state["near"] is None:
                    state["near"] = {r: neighbours(app.mod, campaign, r) for r in gone}
            finally:
                _read(app)
            app.status.set("")
        return state["asked"][way]
    first = "waste" if waste_ok else "near"
    check(first)
    view = _map_of(app)
    w = tk.Toplevel(parent)
    w.title("Delete %d towns with their regions" % len(gone))
    w.transient(parent)
    frm = scroll_body(w, 10)
    frm.columnconfigure(0, weight=1)
    ttk.Label(frm, justify="left", wraplength=600, text=(
        "These towns go from the campaign in every file that ties them, as Delete this town with its region does for "
        "one: the rebels in the towns go with them (a faction's characters there stay, in the field); the regions "
        "leave the mercenary pools and the win conditions. One write, one backup: Undo this write or Tools > Restore "
        "gives everything back.")).grid(row=0, column=0, columnspan=2, sticky="w")
    v_land = tk.StringVar(value=first)
    _land_choice(frm, 1, waste_ok, v_land, None, 580)
    tree = ttk.Treeview(frm, columns=("land",), height=min(12, len(gone)), selectmode="browse")
    tree.heading("#0", text="Town (region) - goes")
    tree.heading("land", text="Its land")
    tree.column("#0", width=280)
    tree.column("land", width=300)
    tree.grid(row=2, column=0, columnspan=2, sticky="we", pady=(8, 0))
    hint = ttk.Label(frm, justify="left", wraplength=600)
    if view is not None:
        hint.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
    lbl_err = ttk.Label(frm, justify="left", wraplength=600, foreground="#c0392b")
    lbl_err.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
    lbl_warn = ttk.Label(frm, justify="left", wraplength=600, foreground="#8a5a00")
    lbl_warn.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))
    bar = ttk.Frame(frm)
    bar.grid(row=6, column=0, columnspan=2, sticky="e", pady=(10, 0))

    def way():
        return v_land.get()

    def worked_out():
        if way() == "waste":
            return {r: None for r in gone}, []
        return receivers(state["near"], gone, state["chosen"])

    def refresh():
        errors, warns = check(way())
        into, stuck = worked_out()
        near = state["near"] or {}
        for r in gone:
            if way() == "waste":
                words = "stays - a wasteland, nobody's"
            elif r in into:
                words = ("%s  (%d tiles of border)" % (into[r], dict(near[r]).get(into[r], 0))
                         if into[r] in dict(near[r]) else "%s  (with the regions deleted beside it)" % into[r])
            else:
                words = "nowhere - see below"
            label = "%s (%s)" % (town[r], r) if town[r] != r else r
            if tree.exists(r):
                tree.item(r, text=label, values=(words,))
            else:
                tree.insert("", "end", iid=r, text=label, values=(words,))
        bad = list(errors) + ["%s touches no region that stays (an island, or only regions deleted with it) - its "
                              "land would belong to no region; leave it out of the selection, give its land to a "
                              "neighbour first (Edit regions) or keep it as a wasteland (REX / M2EX)" % r
                              for r in stuck]
        lbl_err.configure(text=("Cannot be deleted like this:\n- " + "\n- ".join(bad)) if bad else "")
        lbl_warn.configure(text=("Good to know:\n- " + "\n- ".join(warns[:6]) + ("\n..." if len(warns) > 6 else ""))
                           if warns else "")
        b_go.configure(state="disabled" if bad else "normal")
        b_show.configure(state="disabled" if bad else "normal")
        hint.configure(text=(
            "On the map: grey = stays as a wasteland (its town goes). Pick a row (or click a grey region) to find it."
            if way() == "waste" else
            "On the map: red = goes, yellow = takes land. Pick a row (or click a red region): it turns orange and the "
            "neighbours that could take its land green - click a green one to give it the land."))
        if view is not None:
            sel = state["sel"]
            if way() == "waste":
                marks = {r: "waste" for r in gone}
            else:
                marks = {r: "gone" for r in gone}
                marks.update({t: "into" for t in into.values()})
                if sel:
                    marks.update({n: "can" for n, _ in near[sel] if n not in gone and n != into.get(sel)})
            if sel:
                marks[sel] = "this"
            try:
                view.mark_regions(marks, clicked)
            except tk.TclError:
                pass

    def picked_row(e=None):
        sel = tree.selection()
        state["sel"] = sel[0] if sel else None
        refresh()

    def clicked(r):
        sel = state["sel"]
        if r in gone:
            tree.selection_set(r)
            tree.see(r)
            return
        if way() == "near" and sel and r and r in dict(state["near"][sel]):
            state["chosen"][sel] = r
            refresh()
            return
        view.readout.configure(text=(
            "%s is not one of the towns deleted" % (r or "the sea")) if way() == "waste" else (
            "%s does not touch %s - click a green neighbour" % (r or "the sea", sel)) if sel else
            "pick a town first - a row of the list or a red region")

    tree.bind("<<TreeviewSelect>>", picked_row)

    def unmark(e=None):
        if e is not None and e.widget is not w:
            return
        if view is not None:
            try:
                view.mark_regions(None)
            except tk.TclError:
                pass
    w.bind("<Destroy>", unmark, add="+")

    def plan():
        errors, warns = check(way())
        into, stuck = worked_out()
        if stuck or errors:
            return None
        p = Plan(app.mod, "delete", "%d_regions" % len(gone))
        try:
            delete_many(p, campaign, into, warns, waste=way() == "waste")
        except ValueError as e:
            messagebox.showerror(APP, str(e), parent=w)
            return None
        return p, into

    def preview():
        got = plan()
        if got:
            app.show_text("Delete %d towns with their regions - nothing written yet" % len(gone), got[0].report())

    def write():
        got = plan()
        if not got:
            return
        p, into = got
        if way() == "waste":
            text = ("Delete these %d towns now (%d file(s))? Their regions stay as wastelands - nobody's land with no "
                    "town (REX / M2EX read it so); no neighbour grows.\n\nA backup is made first (Undo this write or "
                    "Tools > Restore undoes it)." % (len(gone), len(p.changed_files())))
        else:
            text = ("Delete these %d towns with their regions now (%d file(s))? Their land goes:\n%s\n\nA backup is "
                    "made first (Undo this write or Tools > Restore undoes it)." % (
                        len(gone), len(p.changed_files()), "\n".join("- %s -> %s" % (r, into[r]) for r in gone)))
        if not ask(APP, text, parent=w, yes="Delete them", no="Keep them", danger=True):
            return
        bdir = p.apply()
        log.write("Deleted %d towns (backup %s), %s\n%s" % (
            len(gone), bdir, "their regions wastelands now: " + ", ".join(gone) if way() == "waste" else
            "with their regions: " + ", ".join("%s -> %s" % (r, into[r]) for r in gone), p.report()))
        w.destroy()
        app.load()
        app.status.set("%d towns deleted%s (backup %s). Start the game - it builds map.rwm again." % (
            len(gone), " - their regions are wastelands now" if way() == "waste" else " with their regions", bdir))

    b_show = ttk.Button(bar, text="Preview", command=preview)
    b_show.pack(side="left")
    b_go = ttk.Button(bar, text="Delete them", command=write)
    b_go.pack(side="left", padx=4)
    ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")
    v_land.trace_add("write", lambda *a: refresh())
    _beside(app, w, view)
    refresh()
    return w


def wasteland_town(app, region, xy, parent):
    """The opposite of a town deleted as a wasteland: the wasteland gets its town on the tile right-clicked on the Map
    (regiondelete.wasteland_town - its descr_regions block, the town pixel, a village in descr_strat for the owner
    picked, the names). Asked with Preview, written with a backup (Tools > Restore takes it back), the mod read
    again."""
    from .gui_mapadd import factions_here
    from .gui_util import FactionBox
    from .plan import Plan
    from .regiondelete import town_problem
    from .regiondelete import wasteland_town as write_town
    campaign = app.v_campaign.get()
    if app.pending_parts():
        messagebox.showerror(APP, "Other changes wait for Apply. Apply (or undo) them first.", parent=parent)
        return None
    why = town_problem(app.mod, campaign, region, xy)
    if why:
        messagebox.showerror(APP, "%s cannot get its town at %d, %d: %s" % (region, xy[0], xy[1], why), parent=parent)
        return None
    w = tk.Toplevel(parent)
    w.title("%s gets its town" % region)
    w.transient(parent)
    frm = scroll_body(w, 10)
    ttk.Label(frm, justify="left", wraplength=520, text=(
        "%s is a wasteland now - no town, nobody's. Its town goes on tile %d, %d: the region's block of "
        "descr_regions names it again, the map gets its town pixel, descr_strat a village of the owner below (400 "
        "people, no buildings, as the game makes it). map.rwm is removed (the game builds it again)." % (
            region, xy[0], xy[1]))).grid(row=0, column=0, columnspan=3, sticky="w")
    base = region[:-2] if region.endswith("_R") else region[:-9] if region.endswith("_Province") else region + "_town"
    v_name = tk.StringVar(value=base)
    v_label = tk.StringVar(value=base.replace("_", " "))
    ttk.Label(frm, text="Its name in the files").grid(row=1, column=0, sticky="w", pady=(8, 2))
    ttk.Entry(frm, textvariable=v_name, width=28).grid(row=1, column=1, sticky="w", padx=6, pady=(8, 2))
    ttk.Label(frm, text="The name players see").grid(row=2, column=0, sticky="w")
    ttk.Entry(frm, textvariable=v_label, width=28).grid(row=2, column=1, sticky="w", padx=6)
    facs = factions_here(app)
    v_owner = tk.StringVar(value="slave" if "slave" in facs else (facs[0] if facs else ""))
    ttk.Label(frm, text="Owner").grid(row=3, column=0, sticky="w", pady=2)
    shown = app.shown_names() if hasattr(app, "shown_names") else {}
    FactionBox(frm, v_owner, facs, shown, state="readonly", width=28).grid(row=3, column=1, sticky="w", padx=6, pady=2)
    lbl = ttk.Label(frm, foreground="#c0392b", justify="left", wraplength=520)
    lbl.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def plan():
        name = v_name.get().strip()
        why = town_problem(app.mod, campaign, region, xy, name)
        lbl.configure(text=why or "")
        if why:
            return None
        p = Plan(app.mod, "town", region)
        try:
            write_town(p, campaign, region, xy, name, v_owner.get(), v_label.get().strip() or None)
        except ValueError as e:
            lbl.configure(text=str(e))
            return None
        return p

    def preview():
        p = plan()
        if p:
            app.show_text("%s gets its town - nothing written yet" % region, p.report())

    def write():
        p = plan()
        if not p:
            return
        bdir = p.apply()
        log.write("%s got its town %s at %d, %d (backup %s)\n%s" % (region, v_name.get().strip(), xy[0], xy[1], bdir,
                                                                    p.report()))
        w.destroy()
        app.load()
        app.status.set("%s has its town %s again (backup %s) - double click it on the Map to change it. Start the "
                       "game - it builds map.rwm again." % (region, v_name.get().strip(), bdir))

    bar = ttk.Frame(frm)
    bar.grid(row=5, column=0, columnspan=3, sticky="e", pady=(10, 0))
    ttk.Button(bar, text="Preview", command=preview).pack(side="left")
    ttk.Button(bar, text="Write its town", command=write).pack(side="left", padx=4)
    ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")
    return w
