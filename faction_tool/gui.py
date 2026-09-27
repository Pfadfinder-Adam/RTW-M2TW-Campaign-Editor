"""The window: pick the mod, fill in the faction, preview, create, restore."""

import os
import traceback
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from .build import build, template_display
from .moddata import ModData
from .plan import backups, restore
from .strat import Strat

APP = "RTW Faction Tool"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry("1200x800")
        self.minsize(900, 640)
        self.mod = None
        self.strat = None
        self.regions = {}
        self.chosen = []
        self.colours = {"primary": None, "secondary": None}
        self._build()

    # ------------------------------------------------------------------ layout
    def _build(self):
        pad = {"padx": 6, "pady": 3}
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Mod data folder").pack(side="left")
        self.v_path = tk.StringVar()
        ttk.Entry(top, textvariable=self.v_path).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Browse...", command=self.browse).pack(side="left")
        ttk.Button(top, text="Load", command=self.load).pack(side="left", padx=4)
        ttk.Label(top, text="Campaign").pack(side="left", padx=(12, 2))
        self.v_campaign = tk.StringVar()
        self.cb_campaign = ttk.Combobox(top, textvariable=self.v_campaign, state="readonly", width=24)
        self.cb_campaign.pack(side="left")
        self.cb_campaign.bind("<<ComboboxSelected>>", lambda e: self.load_campaign())

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, **pad)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # --- faction
        lf = ttk.LabelFrame(left, text="New faction")
        lf.pack(fill="x")
        self.v = {k: tk.StringVar() for k in ("template", "name", "display_name", "short_name", "adjective",
                                              "ai", "denari", "leader_first", "leader_last", "leader_age",
                                              "heir_first", "heir_last", "heir_age", "capital")}
        self.v["denari"].set("5000")
        self.v["leader_age"].set("40")
        self.v["heir_age"].set("22")
        row = 0
        def field(label, widget):
            nonlocal row
            ttk.Label(lf, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=2)
            widget.grid(row=row, column=1, sticky="we", padx=4, pady=2)
            row += 1
        self.cb_template = ttk.Combobox(lf, textvariable=self.v["template"], state="readonly", width=28)
        self.cb_template.bind("<<ComboboxSelected>>", lambda e: self.template_changed())
        field("Template (copied)", self.cb_template)
        field("Internal name", ttk.Entry(lf, textvariable=self.v["name"]))
        field("Name (full)", ttk.Entry(lf, textvariable=self.v["display_name"]))
        field("Name (short)", ttk.Entry(lf, textvariable=self.v["short_name"]))
        field("Adjective", ttk.Entry(lf, textvariable=self.v["adjective"]))
        field("AI personality", ttk.Entry(lf, textvariable=self.v["ai"]))
        field("Starting denari", ttk.Entry(lf, textvariable=self.v["denari"]))
        cf = ttk.Frame(lf)
        self.b_primary = tk.Button(cf, text="primary", width=10, command=lambda: self.pick_colour("primary"))
        self.b_primary.pack(side="left")
        self.b_secondary = tk.Button(cf, text="secondary", width=10, command=lambda: self.pick_colour("secondary"))
        self.b_secondary.pack(side="left", padx=4)
        field("Colours", cf)
        self.v_playable = tk.BooleanVar(value=True)
        self.v_triggers = tk.BooleanVar(value=True)
        self.v_art = tk.BooleanVar(value=True)
        self.v_dip = tk.StringVar(value="neutral")
        ttk.Checkbutton(lf, text="Playable", variable=self.v_playable).grid(row=row, column=0, sticky="w", padx=4)
        ttk.Checkbutton(lf, text="Copy trait / ancillary triggers", variable=self.v_triggers).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Checkbutton(lf, text="Copy art named after the template", variable=self.v_art).grid(row=row, column=1, sticky="w")
        row += 1
        df = ttk.Frame(lf)
        ttk.Radiobutton(df, text="neutral to all", value="neutral", variable=self.v_dip).pack(side="left")
        ttk.Radiobutton(df, text="template's relations", value="template", variable=self.v_dip).pack(side="left")
        field("Diplomacy", df)
        ttk.Label(lf, text="Tooltip\n(faction icon)").grid(row=row, column=0, sticky="nw", padx=4)
        self.t_descr = tk.Text(lf, width=34, height=2, wrap="word")
        self.t_descr.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        row += 1
        ttk.Label(lf, text="Full description\n(campaign screen)").grid(row=row, column=0, sticky="nw", padx=4)
        self.t_long = tk.Text(lf, width=34, height=7, wrap="word")
        self.t_long.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        row += 1
        self.v_army = tk.StringVar(value="balanced")
        af = ttk.Frame(lf)
        ttk.Combobox(af, textvariable=self.v_army, state="readonly", width=12,
                     values=("balanced", "template", "bodyguard")).pack(side="left")
        ttk.Label(af, text="balanced = sized like similar factions").pack(side="left", padx=4)
        field("Leader's army", af)
        self.v_garrison = tk.StringVar(value="replace")
        gf = ttk.Frame(lf)
        ttk.Radiobutton(gf, text="replace with own units", value="replace", variable=self.v_garrison).pack(side="left")
        ttk.Radiobutton(gf, text="keep", value="keep", variable=self.v_garrison).pack(side="left")
        field("Old garrisons", gf)
        lf.columnconfigure(1, weight=1)

        # --- leaders
        lf2 = ttk.LabelFrame(left, text="Leader and heir (names must come from the template's name list)")
        lf2.pack(fill="x", pady=(8, 0))
        self.cb_names = []
        for r, who in enumerate(("leader", "heir")):
            ttk.Label(lf2, text=who.capitalize()).grid(row=r, column=0, sticky="w", padx=4, pady=2)
            a = ttk.Combobox(lf2, textvariable=self.v[who + "_first"], width=16)
            b = ttk.Combobox(lf2, textvariable=self.v[who + "_last"], width=16)
            a.grid(row=r, column=1, padx=2)
            b.grid(row=r, column=2, padx=2)
            ttk.Entry(lf2, textvariable=self.v[who + "_age"], width=4).grid(row=r, column=3, padx=2)
            self.cb_names.append((a, b))
        ttk.Label(lf2, text="first name / surname / age - leave the heir empty for none").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=4)

        # --- towns
        tf = ttk.LabelFrame(right, text="Starting settlements")
        tf.pack(fill="both", expand=True)
        flt = ttk.Frame(tf)
        flt.pack(fill="x", padx=4, pady=4)
        ttk.Label(flt, text="Search").pack(side="left")
        self.v_search = tk.StringVar()
        self.v_search.trace_add("write", lambda *a: self.fill_towns())
        ttk.Entry(flt, textvariable=self.v_search, width=20).pack(side="left", padx=4)
        ttk.Label(flt, text="Owner").pack(side="left", padx=(10, 2))
        self.v_owner = tk.StringVar(value="(all)")
        self.cb_owner = ttk.Combobox(flt, textvariable=self.v_owner, state="readonly", width=18)
        self.cb_owner.pack(side="left")
        self.cb_owner.bind("<<ComboboxSelected>>", lambda e: self.fill_towns())
        lists = ttk.Frame(tf)
        lists.pack(fill="both", expand=True, padx=4)
        # the chosen list and the buttons are packed first (right side) so they never get squeezed
        cf2 = ttk.Frame(lists)
        cf2.pack(side="right", fill="y")
        ttk.Label(cf2, text="Chosen").pack(anchor="w")
        self.lb = tk.Listbox(cf2, width=20, height=14)
        self.lb.pack(fill="both", expand=True)
        ttk.Label(cf2, text="Capital").pack(anchor="w", pady=(6, 0))
        self.cb_capital = ttk.Combobox(cf2, textvariable=self.v["capital"], state="readonly", width=18)
        self.cb_capital.pack(fill="x")
        mid = ttk.Frame(lists)
        mid.pack(side="right", padx=6)
        ttk.Button(mid, text="Add >", command=self.add_town).pack(pady=2)
        ttk.Button(mid, text="< Remove", command=self.remove_town).pack(pady=2)
        self.tv = ttk.Treeview(lists, columns=("town", "owner"), show="tree headings", height=18)
        self.tv.heading("#0", text="Region")
        self.tv.heading("town", text="Settlement")
        self.tv.heading("owner", text="Owner")
        self.tv.column("#0", width=150)
        self.tv.column("town", width=120)
        self.tv.column("owner", width=100)
        sb = ttk.Scrollbar(lists, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.bind("<Double-1>", lambda e: self.add_town())

        # --- actions
        bar = ttk.Frame(self)
        bar.pack(fill="x", **pad)
        ttk.Button(bar, text="Preview changes", command=self.preview).pack(side="left")
        ttk.Button(bar, text="Create faction", command=self.create).pack(side="left", padx=6)
        ttk.Button(bar, text="Restore a backup...", command=self.restore).pack(side="right")
        self.status = tk.StringVar(value="Choose the mod's data folder (for example ...\\HLR\\data) and press Load.")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=6, pady=(0, 6))

    # ------------------------------------------------------------------ loading
    def browse(self):
        d = filedialog.askdirectory(title="The mod's data folder")
        if d:
            self.v_path.set(d)
            self.load()

    def load(self):
        try:
            self.mod = ModData(self.v_path.get())
        except Exception as e:
            messagebox.showerror(APP, str(e))
            return
        self.v_path.set(self.mod.data)
        camps = self.mod.campaigns()
        self.cb_campaign["values"] = camps
        self.v_campaign.set("imperial_campaign" if "imperial_campaign" in camps else (camps[0] if camps else ""))
        names = [n for n, _ in self.mod.factions() if n != "slave"]
        self.cb_template["values"] = names
        self.load_campaign()
        self.status.set("%d factions, %d campaign(s)." % (len(names) + 1, len(camps)))

    def load_campaign(self):
        c = self.v_campaign.get()
        if not self.mod or not c:
            return
        try:
            self.strat = Strat(self.mod.load(self.mod.campaign_file(c, "descr_strat.txt")))
            self.regions = self.mod.regions(c)
            self.mod.city_tiles(c)
        except Exception as e:
            messagebox.showerror(APP, "Could not read the campaign: %s" % e)
            return
        owners = sorted(set(self.strat.owners().values()))
        self.cb_owner["values"] = ["(all)"] + owners
        self.chosen = []
        self.refresh_chosen()
        self.fill_towns()

    def fill_towns(self):
        if not self.strat:
            return
        self.tv.delete(*self.tv.get_children())
        q = self.v_search.get().lower().strip()
        want = self.v_owner.get()
        for region, owner in sorted(self.strat.owners().items(), key=lambda x: (x[1] != "slave", x[1], x[0])):
            town = self.regions.get(region, {}).get("settlement", "")
            if want not in ("", "(all)") and owner != want:
                continue
            if q and q not in region.lower() and q not in town.lower():
                continue
            self.tv.insert("", "end", iid=region, text=region, values=(town, owner))

    def template_changed(self):
        t = self.v["template"].get()
        if not t or not self.mod:
            return
        fb = self.strat.faction(t) if self.strat else None
        if fb:
            parts = fb.header.split(",", 1)
            self.v["ai"].set(parts[1].strip() if len(parts) > 1 else "")
        pool = self.mod.name_pool(t)
        for a, b in self.cb_names:
            a["values"] = pool.get("characters", [])
            b["values"] = [""] + pool.get("surnames", [])
        disp = template_display(self.mod, t)
        self.status.set("Template %s: %s. Its units, buildings, names, traits and art are copied." %
                        (t, disp.get("display_name", t)))

    def pick_colour(self, which):
        c = colorchooser.askcolor(title=which + " colour")
        if c and c[0]:
            rgb = tuple(int(x) for x in c[0])
            self.colours[which] = rgb
            btn = self.b_primary if which == "primary" else self.b_secondary
            btn.configure(bg="#%02x%02x%02x" % rgb)

    def add_town(self):
        for iid in self.tv.selection():
            if iid not in self.chosen:
                self.chosen.append(iid)
        self.refresh_chosen()

    def remove_town(self):
        sel = [self.lb.get(i).split(" ")[0] for i in self.lb.curselection()]
        self.chosen = [r for r in self.chosen if r not in sel]
        self.refresh_chosen()

    def refresh_chosen(self):
        self.lb.delete(0, "end")
        for r in self.chosen:
            owner = self.strat.owners().get(r, "?") if self.strat else "?"
            self.lb.insert("end", "%s  (%s)" % (r, owner))
        self.cb_capital["values"] = self.chosen
        if self.v["capital"].get() not in self.chosen:
            self.v["capital"].set(self.chosen[0] if self.chosen else "")

    # ------------------------------------------------------------------ actions
    def gather(self):
        if not self.mod:
            raise ValueError("load a mod first")
        v = {k: x.get().strip() for k, x in self.v.items()}
        if not v["template"]:
            raise ValueError("pick a template faction")
        def who(prefix):
            first = v[prefix + "_first"]
            if not first:
                return None
            name = (first + " " + v[prefix + "_last"]).strip()
            return {"name": name, "age": int(v[prefix + "_age"] or 30)}
        leader = who("leader")
        if not leader:
            raise ValueError("the faction needs a leader - pick a first name")
        opts = {
            "display_name": v["display_name"], "short_name": v["short_name"], "adjective": v["adjective"],
            "description": self.t_descr.get("1.0", "end").strip(),
            "long_description": self.t_long.get("1.0", "end").strip(),
            "primary_colour": self.colours["primary"], "secondary_colour": self.colours["secondary"],
            "copy_triggers": self.v_triggers.get(), "copy_art": self.v_art.get(),
            "start": {"regions": list(self.chosen), "capital": v["capital"], "leader": leader,
                      "heir": who("heir"), "denari": int(v["denari"] or 0), "ai": v["ai"] or None,
                      "playable": self.v_playable.get(), "diplomacy": self.v_dip.get(),
                      "army_mode": self.v_army.get(), "garrison": self.v_garrison.get()},
        }
        return v["template"], v["name"].lower(), opts

    def make_plan(self):
        template, name, opts = self.gather()
        # a fresh read, so a previous preview's edits never leak in
        mod = ModData(self.mod.data)
        return build(mod, self.v_campaign.get(), template, name, opts)

    def show_text(self, title, text):
        w = tk.Toplevel(self)
        w.title(title)
        w.geometry("900x600")

        def copy_all():
            w.clipboard_clear()
            w.clipboard_append(text)
            status.configure(text="Copied to the clipboard")

        def save_as():
            path = filedialog.asksaveasfilename(parent=w, defaultextension=".txt",
                                                initialfile="faction_tool_report.txt",
                                                filetypes=[("Text", "*.txt"), ("All files", "*.*")])
            if path:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                status.configure(text="Saved to " + path)

        bar = ttk.Frame(w, padding=4)
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text="Copy all", command=copy_all).pack(side="left")
        ttk.Button(bar, text="Save as...", command=save_as).pack(side="left", padx=4)
        status = ttk.Label(bar, text="")
        status.pack(side="left", padx=8)

        t = tk.Text(w, wrap="none", font=("Consolas", 10))
        sb = ttk.Scrollbar(w, orient="vertical", command=t.yview)
        hb = ttk.Scrollbar(w, orient="horizontal", command=t.xview)
        t.configure(yscrollcommand=sb.set, xscrollcommand=hb.set)
        sb.pack(side="right", fill="y")
        hb.pack(side="bottom", fill="x")
        t.pack(fill="both", expand=True)
        t.insert("1.0", text)
        # Read-only but still selectable. Ctrl+A / Ctrl+C go by Windows keycode so they
        # also work with a non-Latin keyboard layout.
        def on_key(e):
            if e.state & 0x4 and (e.keycode == 65 or e.keysym.lower() == "a"):
                t.tag_add("sel", "1.0", "end-1c")
            elif e.state & 0x4 and (e.keycode == 67 or e.keysym.lower() == "c"):
                t.event_generate("<<Copy>>")
            elif e.keysym in ("Up", "Down", "Left", "Right", "Prior", "Next", "Home", "End"):
                return None
            return "break"

        t.bind("<Key>", on_key)
        t.bind("<<Paste>>", lambda e: "break")
        t.bind("<<Cut>>", lambda e: "break")
        t.focus_set()

    def preview(self):
        try:
            plan = self.make_plan()
        except Exception as e:
            messagebox.showerror(APP, str(e))
            return
        self.show_text("Preview - nothing written yet", plan.report())

    def create(self):
        try:
            plan = self.make_plan()
        except Exception as e:
            messagebox.showerror(APP, str(e))
            return
        warn = "\n".join("- " + m for _, m in plan.warnings)
        msg = "Write %d file(s) and copy %d art item(s)?\nA backup is made first.%s" % (
            len(plan.changed_files()), len(plan.copies), ("\n\nWarnings:\n" + warn) if warn else "")
        if not messagebox.askyesno(APP, msg):
            return
        try:
            bdir = plan.apply()
        except Exception as e:
            messagebox.showerror(APP, "Writing failed: %s\n\n%s" % (e, traceback.format_exc()))
            return
        self.show_text("Done", plan.report() + "\n\nBackup: %s\nStart a NEW campaign to see the faction." % bdir)
        self.load()

    def restore(self):
        if not self.mod:
            return
        bs = backups(self.mod)
        if not bs:
            messagebox.showinfo(APP, "No backups yet.")
            return
        w = tk.Toplevel(self)
        w.title("Restore a backup")
        lb = tk.Listbox(w, width=70, height=10)
        for b in bs:
            lb.insert("end", os.path.basename(b))
        lb.pack(fill="both", expand=True, padx=6, pady=6)
        def go():
            sel = lb.curselection()
            if not sel:
                return
            b = bs[sel[0]]
            if sel[0] != 0:
                messagebox.showwarning(APP, "Restore the newest backup first - backups undo each other in order.")
                return
            if not messagebox.askyesno(APP, "Undo %s?\nFiles are put back as they were before it." % os.path.basename(b)):
                return
            m = restore(self.mod, b)
            messagebox.showinfo(APP, "Restored %d file(s), removed %d copied item(s)." % (len(m["modified"]), len(m["created"])))
            w.destroy()
            self.load()
        ttk.Button(w, text="Restore", command=go).pack(pady=(0, 6))


def main():
    App().mainloop()
