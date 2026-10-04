"""The Settlements tab: every region and its town of the campaign - the names in the files, the names players see,
the owner, names by culture - and the places to change them: the names players see (quick, as on the Map), the names
in the files (regionrename: everywhere the mod names them, Preview, a backup), names by the owner's culture (REX /
M2EX). Both games."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import ShortHint
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
            ttk.Button(side, text=text, command=cmd, width=24).pack(anchor="w", pady=2)
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
    if not messagebox.askyesno(APP, "%s\n\nWrite %d file(s) now? A backup is made first (Tools > Restore undoes "
                                    "it)." % (p.report(), len(p.changed_files())), parent=parent):
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
    frm = ttk.Frame(w, padding=10)
    frm.pack(fill="both", expand=True)
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


def delete_town(app, region, parent):
    """Delete a town together with its region (regiondelete: its land to a neighbour, every file that ties them),
    asked first with the whole list of changes, written with a backup, the mod read again. The Map's right click
    on a town opens it."""
    from .plan import Plan
    from .regiondelete import delete, neighbours, problems
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
    errors, warns = problems(app.mod, campaign, region)
    if errors:
        messagebox.showerror(APP, "%s and its region cannot be deleted:\n\n- %s" % (town, "\n- ".join(errors)),
                             parent=parent)
        return
    near = neighbours(app.mod, campaign, region)
    w = tk.Toplevel(parent)
    w.title("Delete %s with its region %s" % (town, region))
    w.transient(parent)
    frm = ttk.Frame(w, padding=10)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, justify="left", wraplength=560, text=(
        "The town and its region go from the campaign in every file that ties them: the region's land (and its "
        "port) becomes a neighbour's, its block of descr_regions and its settlement of descr_strat go, the rebels "
        "in the town go with it (a faction's characters there stay, in the field), it leaves the mercenary pools, "
        "the win conditions and the music lists. map.rwm is removed (the game builds it again). A backup is made "
        "first; Tools > Restore gives everything back.")).grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(frm, text="Its land goes to").grid(row=1, column=0, sticky="w", pady=(8, 2))
    labels = ["%s  (%d tiles of border)" % (r, n) for r, n in near]
    v_into = tk.StringVar(value=labels[0])
    ttk.Combobox(frm, textvariable=v_into, values=labels, state="readonly",
                 width=max(30, max(len(x) for x in labels) + 2)).grid(row=1, column=1, sticky="w", padx=6,
                                                                       pady=(8, 2))
    if warns:
        ttk.Label(frm, justify="left", wraplength=560, foreground="#8a5a00", text=(
            "Good to know:\n- " + "\n- ".join(warns[:6]) + ("\n..." if len(warns) > 6 else ""))).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def plan():
        into = near[labels.index(v_into.get())][0]
        p = Plan(app.mod, "delete", region)
        try:
            delete(p, campaign, region, into)
        except ValueError as e:
            messagebox.showerror(APP, str(e), parent=w)
            return None
        return p

    def preview():
        p = plan()
        if p:
            app.show_text("Delete %s with its region - nothing written yet" % town, p.report())

    def write():
        p = plan()
        into = near[labels.index(v_into.get())][0] if p else None
        if not p or not messagebox.askyesno(APP, "%s\n\nDelete %s and its region %s now (%d file(s))? Every tile of "
                                                 "it becomes %s's - no land is left without a region (the game wants "
                                                 "each tile in one). A backup is made first (Tools > Restore undoes "
                                                 "it)." % (p.report(), town, region, len(p.changed_files()), into),
                                            parent=w):
            return
        bdir = p.apply()
        log.write("Deleted %s with its region %s (backup %s)\n%s" % (town, region, bdir, p.report()))
        w.destroy()
        app.load()
        app.status.set("%s and its region %s deleted (backup %s). Start the game - it builds map.rwm again."
                       % (town, region, bdir))

    bar = ttk.Frame(frm)
    bar.grid(row=3, column=0, columnspan=2, sticky="e", pady=(10, 0))
    ttk.Button(bar, text="Preview", command=preview).pack(side="left")
    ttk.Button(bar, text="Delete", command=write).pack(side="left", padx=4)
    ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")
