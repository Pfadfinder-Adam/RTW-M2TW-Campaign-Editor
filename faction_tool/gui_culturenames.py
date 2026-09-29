"""Every town's names by culture in one table: sort, filter by culture, see what is set and what is not,
edit a name in place. Changes wait in App.culture_names like the per-town dialog's (one Apply)."""

import tkinter as tk
from tkinter import ttk

from . import culturenames as CN

EMPTY = "-"


class CultureNamesTable:
    def __init__(self, app):
        self.app = app
        mod, camp = app.mod, app.v_campaign.get()
        self.cultures = CN.cultures(mod)
        self.cols = [CN.DEFAULT] + self.cultures
        self.saved = CN.read(mod, camp)                    # what the campaign's script holds now
        self.foreign = CN.foreign(mod, camp)
        self.fcult = dict(mod.factions())
        eng, rex = CN.engine(mod)
        w = self.w = tk.Toplevel(app)
        w.title("Settlement names by culture - %s" % camp)
        w.transient(app)
        w.geometry("1180x640")
        frm = ttk.Frame(w, padding=8)
        frm.pack(fill="both", expand=True)
        about = ("Each town may have a name for each culture of its owner; %s renames it when it changes hands. "
                 "Double click a culture's cell to type a name (Enter keeps it, Esc drops it, an empty cell = no name "
                 "of its own: 'every other' is used, else the game's name). Double click a town's name for its own "
                 "dialog. Shown now = the name under its owner as the next Apply leaves it. Grey rows are renamed by "
                 "the mod's own campaign script - not edited here." % eng) if rex else (
                 "Needs %s: the game folder has no %s.exe, so these names are not written. The table still shows "
                 "and keeps them." % (eng, eng))
        ttk.Label(frm, wraplength=1150, justify="left", foreground="#555" if rex else "#a33",
                  text=about).pack(anchor="w")
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=6)
        ttk.Label(bar, text="Culture").pack(side="left")
        self.v_cult = tk.StringVar(value="(all)")
        cb = ttk.Combobox(bar, textvariable=self.v_cult, values=["(all)", "every other"] + self.cultures,
                          state="readonly", width=16)
        cb.pack(side="left", padx=4)
        ttk.Label(bar, text="Show").pack(side="left", padx=(10, 0))
        self.v_show = tk.StringVar(value="every town")
        ttk.Combobox(bar, textvariable=self.v_show, state="readonly", width=30, values=[
            "every town", "with a name for this culture", "without a name for this culture",
            "with any name by culture", "without any", "changed, waiting for Apply",
            "renamed by the mod's own script"]).pack(side="left", padx=4)
        ttk.Label(bar, text="Owner's culture").pack(side="left", padx=(10, 0))
        self.v_owner = tk.StringVar(value="(all)")
        ttk.Combobox(bar, textvariable=self.v_owner, values=["(all)"] + self.cultures, state="readonly",
                     width=14).pack(side="left", padx=4)
        ttk.Label(bar, text="Search").pack(side="left", padx=(10, 0))
        self.v_q = tk.StringVar()
        ttk.Entry(bar, textvariable=self.v_q, width=16).pack(side="left", padx=4)
        for v in (self.v_cult, self.v_show, self.v_owner, self.v_q):
            v.trace_add("write", lambda *a: self.fill())
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True)
        heads = [("region", "Region", 120), ("town", "Town", 110), ("owner", "Owner", 100),
                 ("oc", "Owner's culture", 100), ("now", "Shown now", 120)] + \
                [("c:" + c, "every other" if c == CN.DEFAULT else c, 95) for c in self.cols]
        self.tv = ttk.Treeview(box, columns=[k for k, _, _ in heads], show="headings")
        self.sort = ("region", False)
        for k, text, width in heads:
            self.tv.heading(k, text=text, command=lambda k=k: self.sort_by(k))
            self.tv.column(k, width=width, stretch=False)
        ys = ttk.Scrollbar(box, command=self.tv.yview)
        xs = ttk.Scrollbar(box, orient="horizontal", command=self.tv.xview)
        self.tv.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tv.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.tv.tag_configure("changed", foreground="#1a6fd0")
        self.tv.tag_configure("foreign", foreground="#999")
        self.tv.bind("<Double-1>", self.dbl)
        low = ttk.Frame(frm)
        low.pack(fill="x", pady=(6, 0))
        self.l_count = ttk.Label(low)
        self.l_count.pack(side="left")
        ttk.Button(low, text="Close", command=w.destroy).pack(side="right")
        ttk.Button(low, text="Clear the town's names", command=self.clear_town).pack(side="right", padx=4)
        self.edit = None
        self.fill()

    # ---- data ----
    def table(self):
        t = {k: dict(v) for k, v in self.saved.items()}
        for k, v in self.app.culture_names.items():
            if v:
                t[k] = dict(v)
            else:
                t.pop(k, None)
        return t

    def rows(self):
        app = self.app
        me = app.v["template"].get().strip() if app.editing() else \
            (app.v["name"].get().strip().lower() or "(new)")
        owners = app.owners_after(me)                      # the towns as the next Apply leaves them
        cultures = dict(self.fcult)
        if me not in cultures:                             # the new faction: its template's culture
            cultures[me] = cultures.get(app.v["template"].get().strip())
        towns = {r: i.get("settlement") for r, i in app.regions.items() if i.get("settlement")}
        towns.update({r["name"]: r["settlement"] for r in app.new_regions if r.get("settlement")})
        table = self.table()
        out = []
        for region, town in towns.items():
            owner = owners.get(region) or "slave"
            oc = cultures.get(owner) or ""
            names = table.get(town) or {}
            now = CN.name_for(names, oc) or CN.shown_name(app.mod, app.v_campaign.get(), town)
            out.append({"region": region, "town": town, "owner": owner, "oc": oc, "now": now, "names": names,
                        "changed": town in app.culture_names, "foreign": town in self.foreign})
        return out

    def fill(self):
        cult = self.v_cult.get()
        key = CN.DEFAULT if cult == "every other" else (None if cult == "(all)" else cult)
        show, oc, q = self.v_show.get(), self.v_owner.get(), self.v_q.get().lower().strip()
        rows = []
        for r in self.rows():
            names = r["names"]
            if oc != "(all)" and r["oc"] != oc:
                continue
            if q and not any(q in str(x).lower() for x in (r["region"], r["town"], r["now"], *names.values())):
                continue
            has = bool(names.get(key)) if key else bool(names)
            if show == "with a name for this culture" and not has:
                continue
            if show == "without a name for this culture" and has:
                continue
            if show == "with any name by culture" and not names:
                continue
            if show == "without any" and names:
                continue
            if show == "changed, waiting for Apply" and not r["changed"]:
                continue
            if show == "renamed by the mod's own script" and not r["foreign"]:
                continue
            rows.append(r)
        k, rev = self.sort
        if k.startswith("c:"):
            c = k[2:]
            rows.sort(key=lambda r: (not r["names"].get(c), (r["names"].get(c) or "").lower(), r["region"]),
                      reverse=rev)
        else:
            rows.sort(key=lambda r: (str(r[k]).lower(), r["region"]), reverse=rev)
        self.tv.delete(*self.tv.get_children())
        for r in rows:
            vals = [r["region"], r["town"], r["owner"], r["oc"], r["now"]] + \
                   [r["names"].get(c) or EMPTY for c in self.cols]
            tags = ("foreign",) if r["foreign"] else ("changed",) if r["changed"] else ()
            self.tv.insert("", "end", iid=r["region"], values=vals, tags=tags)
        n_with = sum(1 for r in rows if (r["names"].get(key) if key else r["names"]))
        self.l_count.configure(text="%d town(s) shown: %d with a name%s, %d without; %d change(s) wait for Apply"
                               % (len(rows), n_with, " for " + cult if key else " by culture", len(rows) - n_with,
                                  len(self.app.culture_names)))

    def sort_by(self, k):
        self.sort = (k, not self.sort[1] if self.sort[0] == k else False)
        self.fill()

    # ---- editing ----
    def dbl(self, e):
        row, col = self.tv.identify_row(e.y), self.tv.identify_column(e.x)
        if not row or not col:
            return
        i = int(col[1:]) - 1
        cols = self.tv["columns"]
        if i >= len(cols):
            return
        k = cols[i]
        town = self.tv.set(row, "town")
        if town in self.foreign:
            self.l_count.configure(text="%s is renamed by the mod's own campaign script (%d line(s)) - change it "
                                        "there, not here" % (town, self.foreign[town]))
            return
        if not k.startswith("c:"):
            self.app.culture_names_dialog(row)
            self.w.after(300, self._wait_dialog)
            return
        self.cell(row, k, town)

    def _wait_dialog(self):
        if not self.w.winfo_exists():
            return
        if any(isinstance(x, tk.Toplevel) and x is not self.w and x.winfo_exists() and x.winfo_viewable()
               for x in self.app.winfo_children()):
            self.w.after(300, self._wait_dialog)
            return
        self.fill()

    def cell(self, row, k, town):
        if self.edit:
            self.edit.destroy()
        box = self.tv.bbox(row, k)
        if not box:
            return
        x, y, wd, ht = box
        v = tk.StringVar(value=(self.table().get(town) or {}).get(k[2:], ""))
        en = self.edit = ttk.Entry(self.tv, textvariable=v)
        en.place(x=x, y=y, width=max(wd, 120), height=ht)
        en.focus_set()
        en.select_range(0, "end")

        def keep(*a):
            self.set_name(town, k[2:], v.get().strip())
            en.destroy()
            self.edit = None

        def drop(*a):
            en.destroy()
            self.edit = None
        en.bind("<Return>", keep)
        en.bind("<KP_Enter>", keep)
        en.bind("<Escape>", drop)
        en.bind("<FocusOut>", keep)

    def set_name(self, town, culture, name):
        names = dict(self.table().get(town) or {})
        if (names.get(culture) or "") == name:
            return
        if name:
            names[culture] = name
        else:
            names.pop(culture, None)
        bad = CN.problems(self.app.mod, {town: names}) if names else []
        if bad:
            self.l_count.configure(text="; ".join(bad), foreground="#a33")
            return
        self.l_count.configure(foreground="")
        self.app.remember()
        self.app.culture_names[town] = names          # {} = the town's names are dropped with the next Apply
        self.app.fill_towns()
        self.app.show_map()
        self.fill()

    def clear_town(self):
        for row in self.tv.selection():
            town = self.tv.set(row, "town")
            if town not in self.foreign:
                self.app.remember()
                self.app.culture_names[town] = {}
        self.app.fill_towns()
        self.app.show_map()
        self.fill()
