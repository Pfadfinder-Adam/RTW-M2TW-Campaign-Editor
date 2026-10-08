"""The Settlements tab: every region and its town of the campaign - the names in the files, the names players see,
the owner, names by culture - and the places to change them: the names players see (quick, as on the Map), the names
in the files (regionrename: everywhere the mod names them, Preview, a backup), names by the owner's culture (REX /
M2EX). Both games."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import ask
from .gui_util import ShortHint
from .gui_util import scroll_body
from . import log

APP = "RTW & M2TW Campaign Editor"


class SettlementsPanel(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        self.rows = []
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Settlements", font=("", 10, "bold")).pack(side="left")
        ttk.Label(top, text="   Find").pack(side="left")
        self.v_find = tk.StringVar()
        ttk.Entry(top, textvariable=self.v_find, width=24).pack(side="left", padx=4)
        self.v_find.trace_add("write", lambda *a: self.fill())
        self.lbl_n = ttk.Label(top, foreground="#666")
        self.lbl_n.pack(side="left", padx=6)
        ShortHint(self, foreground="#666", wraplength=1100, justify="left", text=(
            "Every region and its town. The names players see are quick to change (also on the Map: Edit region). "
            "The names in the files tie the game's files together - renaming them changes every file of the mod "
            "that names the place (shown before anything is written). Tip: keep the name players see and the name "
            "in the files alike - one name for a place everywhere is easiest to read and fix.")).pack(
            anchor="w", pady=(4, 4))
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        cols = ("town", "shown", "town_shown", "owner", "culture")
        self.tv = ttk.Treeview(body, columns=cols, show="tree headings", height=20)
        for c, text, w in (("#0", "Region (in the files)", 170), ("town", "Town (in the files)", 140),
                           ("shown", "Region - players see", 170), ("town_shown", "Town - players see", 150),
                           ("owner", "Owner", 140), ("culture", "Names by culture", 120)):
            self.tv.heading(c, text=text)
            self.tv.column(c, width=w)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.bind("<Double-1>", lambda e: self.shown_names() if self.tv.identify_row(e.y) else None)
        side = ttk.Frame(body, padding=(8, 0))
        side.pack(side="left", fill="y")
        for text, cmd in (("Names players see...", self.shown_names),
                          ("Rename in the files...", self.rename_files),
                          ("Names by culture...", self.by_culture),
                          ("All towns' names...", lambda: self.app.culture_names_table()),
                          ("Show on the map", self.show_on_map)):
            ttk.Button(side, text=text, command=cmd).pack(anchor="w", pady=2)
        ttk.Label(side, foreground="#666", wraplength=200, justify="left", text=(
            "double click: the names players see\nNames by culture: REX (Rome) / M2EX (Medieval II) rename a town "
            "by its owner's culture while the campaign runs")).pack(anchor="w", pady=(10, 0))

    # ---- reading ----
    def load(self):
        app = self.app
        self.rows = []
        if not app.mod or not app.strat:
            self.fill()
            return
        from .culturenames import read as read_cultures
        from .regionedit import shown_labels
        campaign = app.v_campaign.get()
        regions = app.mod.regions(campaign)
        keys = list(regions) + [v.get("settlement") for v in regions.values() if v.get("settlement")]
        shown = shown_labels(app.mod, campaign, keys)
        owners = app.strat.owners()
        try:
            table = read_cultures(app.mod, campaign)
        except Exception:
            table = {}
        labels = app.shown_names() if hasattr(app, "shown_names") else {}
        from .build import faction_label
        for r in sorted(regions, key=str.lower):
            town = regions[r].get("settlement") or ""
            owner = owners.get(r)
            self.rows.append((r, town, shown.get(r, ""), shown.get(town, ""),
                              faction_label(owner, labels.get(owner)) if owner else "rebels (village)",
                              ", ".join(sorted(table.get(town, {}))) if town in table else ""))
        self.fill()

    def fill(self):
        q = self.v_find.get().strip().lower()
        self.tv.delete(*self.tv.get_children())
        n = 0
        for row in self.rows:
            if q and not any(q in str(x).lower() for x in row):
                continue
            self.tv.insert("", "end", iid=row[0], text=row[0], values=row[1:])
            n += 1
        self.lbl_n.configure(text="%d of %d" % (n, len(self.rows)))

    def picked(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showerror(APP, "Pick a settlement in the list first (a click on its line).", parent=self)
            return None
        return sel[0]

    # ---- actions ----
    def shown_names(self):
        region = self.picked()
        if region:
            self.app.new_region_dialog(edit=region)

    def by_culture(self):
        region = self.picked()
        if region:
            self.app.culture_names_dialog(region)

    def show_on_map(self):
        region = self.picked()
        if not region:
            return
        app = self.app
        xy = app.mod.city_tiles(app.v_campaign.get()).get(region)
        tabs = [app.nb.tab(t, "text").strip() for t in app.nb.tabs()]
        app.nb.select(tabs.index("Map"))
        app.show_map()
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
    app.status.set("Renamed in the files (backup %s). Check the names players see (Settlements tab), then "
                   "start the game - it builds map.rwm again." % bdir)
    return True


def rename_in_files(app, region, parent):
    """The region's and its town's names in the files, changed everywhere the mod names them: a window with the
    new names, Preview (every file and line), then written with a backup at once and the mod read again. The
    Settlements tab and the Map (Edit regions) open it."""
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
    """The map the regions are shown on while a Delete window is open: the main window's (the Map tab / Map editor),
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
