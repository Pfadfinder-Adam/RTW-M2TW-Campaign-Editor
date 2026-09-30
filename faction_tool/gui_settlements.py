"""The Settlements tab: every region and its town of the campaign - the names in the files, the names players see,
the owner, names by culture - and the places to change them: the names players see (quick, as on the Map), the names
in the files (regionrename: everywhere the mod names them, Preview, a backup), names by the owner's culture (REX /
M2EX). Both games."""

import tkinter as tk
from tkinter import messagebox, ttk

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
        ttk.Label(self, foreground="#666", wraplength=1100, justify="left", text=(
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
        """The region's and its town's names in the files, changed everywhere the mod names them: a window with the
        new names, Preview (every file and line), then written with a backup at once and the mod read again."""
        region = self.picked()
        if not region:
            return
        app = self.app
        from .plan import Plan
        from .regionrename import problems, rename
        campaign = app.v_campaign.get()
        town = (app.mod.regions(campaign).get(region) or {}).get("settlement") or ""
        w = tk.Toplevel(self)
        w.title("Rename in the files - %s / %s" % (region, town))
        w.transient(self)
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
            if app.pending_parts():
                messagebox.showerror(APP, "Other changes wait for Apply. Apply (or undo) them first - they were made "
                                          "with the old names.", parent=w)
                return
            p = plan()
            if not p or not messagebox.askyesno(APP, "%s\n\nWrite %d file(s)? A backup is made first (Tools > Restore "
                                                     "undoes it)." % (p.report(), len(p.changed_files())), parent=w):
                return
            bdir = p.apply()
            log.write("Renamed in the files: %s / %s -> %s / %s (backup %s)\n%s" % (
                region, town, v_region.get().strip(), v_town.get().strip(), bdir, p.report()))
            w.destroy()
            app.load()
            app.status.set("Renamed in the files (backup %s). Check the names players see (Settlements tab), then "
                           "start the game - it builds map.rwm again." % bdir)
        bar = ttk.Frame(frm)
        bar.grid(row=3, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(bar, text="Preview", command=preview).pack(side="left")
        ttk.Button(bar, text="Rename", command=write).pack(side="left", padx=4)
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left")
