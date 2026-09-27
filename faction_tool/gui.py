"""The window: pick the mod, fill in the faction, preview, create, restore."""

import os
import threading
import traceback
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from .build import build, template_display
from .buildings import BuildingPictures, read_buildings, settlement_info
from .mapdata import CampaignMap, faction_colours
from .moddata import ModData
from .newmod import create_mod, game_root_of
from .edit import edit as edit_faction, read_faction
from .gui_buildings import BuildingsEditor
from .gui_garrison import GarrisonEditor, Pictures
from .gui_map import MapView
from .plan import backups, restore
from .scan import IGNORE_HELP, ignore_path, make_manifest, scan as scan_mod
from .start import balanced_army, unit_name
from .strat import Strat
from .textio import tokens
from .units import faction_units, read_units

APP = "RTW Faction Tool"

# descr_strat.txt: "faction <name>, <economy> <military>" - the words the game knows
AI_ECONOMY = ("balanced", "bureaucrat", "comfortable", "craftsman", "fortified", "religious", "sailor", "trader")
AI_MILITARY = ("caesar", "genghis", "henry", "mao", "napoleon", "smith", "stalin")
AI_CHOICES = ["%s %s" % (e, m) for e in AI_ECONOMY for m in AI_MILITARY]


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
        self.garrisons = {}             # region -> [unit type] picked by hand
        self.field = []                 # [{kind, name, age, units, xy}] armies/agents/fleets to place
        self._units_for, self._units_cache = None, []
        self.buildings_picked = {}      # region -> [(chain, level)] set by hand
        self._edb_for, self._edb, self._bpics = None, [], None
        self.pictures = Pictures()
        self.colours = {"primary": None, "secondary": None}
        self.editing_now = None
        self.char_moves = {}            # "faction:index" -> (x, y) dragged on the map (Edit)
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
        ttk.Button(top, text="New mod folder...", command=self.new_mod).pack(side="left", padx=4)
        ttk.Label(top, text="Campaign").pack(side="left", padx=(12, 2))
        self.v_campaign = tk.StringVar()
        self.cb_campaign = ttk.Combobox(top, textvariable=self.v_campaign, state="readonly", width=24)
        self.cb_campaign.pack(side="left")
        self.cb_campaign.bind("<<ComboboxSelected>>", lambda e: self.load_campaign())
        self.v_mode = tk.StringVar(value="new")
        ttk.Radiobutton(top, text="New faction", value="new", variable=self.v_mode,
                        command=self.mode_changed).pack(side="left", padx=(12, 2))
        ttk.Radiobutton(top, text="Edit faction", value="edit", variable=self.v_mode,
                        command=self.mode_changed).pack(side="left")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, **pad)
        body = ttk.Frame(self.nb, padding=4)
        self.nb.add(body, text="  Faction  ")
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        # --- faction
        lf = self.lf = ttk.LabelFrame(left, text="New faction")
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
        self.lbl_template = lf.grid_slaves(row=row - 1, column=0)[0]
        self.e_name = ttk.Entry(lf, textvariable=self.v["name"])
        field("Internal name", self.e_name)
        field("Name (full)", ttk.Entry(lf, textvariable=self.v["display_name"]))
        field("Name (short)", ttk.Entry(lf, textvariable=self.v["short_name"]))
        field("Adjective", ttk.Entry(lf, textvariable=self.v["adjective"]))
        self.cb_ai = ttk.Combobox(lf, textvariable=self.v["ai"], state="readonly", values=AI_CHOICES)
        field("AI personality", self.cb_ai)
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
        self.chk_triggers = ttk.Checkbutton(lf, text="Copy trait / ancillary triggers", variable=self.v_triggers)
        self.chk_triggers.grid(row=row, column=1, sticky="w")
        row += 1
        self.chk_art = ttk.Checkbutton(lf, text="Copy art named after the template", variable=self.v_art)
        self.chk_art.grid(row=row, column=1, sticky="w")
        row += 1
        df = ttk.Frame(lf)
        self.dip_buttons = [ttk.Radiobutton(df, text="neutral to all", value="neutral", variable=self.v_dip),
                            ttk.Radiobutton(df, text="template's relations", value="template", variable=self.v_dip)]
        for b in self.dip_buttons:
            b.pack(side="left")
        field("Diplomacy", df)
        self.dip_row = [df, lf.grid_slaves(row=row - 1, column=0)[0]]
        ttk.Label(lf, text="Tooltip\n(faction icon)").grid(row=row, column=0, sticky="nw", padx=4)
        self.t_descr = tk.Text(lf, width=34, height=2, wrap="word")
        self.t_descr.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        row += 1
        ttk.Label(lf, text="Full description\n(campaign screen)").grid(row=row, column=0, sticky="nw", padx=4)
        self.t_long = tk.Text(lf, width=34, height=7, wrap="word")
        self.t_long.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        row += 1
        lf.columnconfigure(1, weight=1)

        # --- leaders
        lf2 = self.lf2 = ttk.LabelFrame(left, text="Leader and heir (names must come from the template's name list)")
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
        # the town list and the chosen list share a pane: drag the divider to widen either
        lists = ttk.Panedwindow(tf, orient="horizontal")
        lists.pack(fill="both", expand=True, padx=4)
        left_pane = ttk.Frame(lists)
        cf2 = ttk.Frame(lists)
        lists.add(left_pane, weight=3)
        lists.add(cf2, weight=1)
        ttk.Label(cf2, text="Chosen").pack(anchor="w")
        # Shift/Ctrl select several, like the list on the left; double-click or Delete removes
        self.lb = tk.Listbox(cf2, width=34, height=14, selectmode="extended", exportselection=False)
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<Double-1>", lambda e: self.remove_town())
        self.lb.bind("<Delete>", lambda e: self.remove_town())
        ttk.Label(cf2, text="Capital").pack(anchor="w", pady=(6, 0))
        self.cb_capital = ttk.Combobox(cf2, textvariable=self.v["capital"], state="readonly", width=24)
        self.cb_capital.pack(fill="x")
        self.cb_capital.bind("<<ComboboxSelected>>", lambda e: self.refresh_chosen())
        # Edit: where the towns taken out of Chosen go
        self.give_frame = ttk.Frame(cf2)
        ttk.Label(self.give_frame, text="Removed towns go to").pack(anchor="w", pady=(6, 0))
        self.v_give = tk.StringVar(value="slave")
        self.cb_give = ttk.Combobox(self.give_frame, textvariable=self.v_give, state="readonly", width=24)
        self.cb_give.pack(fill="x")
        mid = ttk.Frame(left_pane)
        mid.pack(side="right", padx=6)
        self.b_add = ttk.Button(mid, text="Add >", command=self.add_town)
        self.b_add.pack(pady=2)
        self.b_remove = ttk.Button(mid, text="< Remove", command=self.remove_town)
        self.b_remove.pack(pady=2)
        ttk.Button(mid, text="Garrison...", command=lambda: self.show_units(self.selected_town())).pack(pady=(14, 2))
        self.tv = ttk.Treeview(left_pane, columns=("town", "owner"), show="tree headings", height=18)
        self.tv.heading("#0", text="Region")
        self.tv.heading("town", text="Settlement")
        self.tv.heading("owner", text="Owner")
        self.tv.column("#0", width=150)
        self.tv.column("town", width=120)
        self.tv.column("owner", width=100)
        sb = ttk.Scrollbar(left_pane, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.bind("<Double-1>", lambda e: self.add_town())

        self._build_units_tab()
        self._build_buildings_tab()
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Map  ")
        self.map_view = MapView(tab)
        self.map_view.pack(fill="both", expand=True)
        self._cmap, self._cmap_for = None, None
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.tab_opened())

        # --- actions
        bar = ttk.Frame(self)
        bar.pack(fill="x", **pad)
        ttk.Button(bar, text="Preview changes", command=self.preview).pack(side="left")
        self.b_create = ttk.Button(bar, text="Create faction", command=self.create)
        self.b_create.pack(side="left", padx=6)
        ttk.Button(bar, text="Restore a backup...", command=self.restore).pack(side="right")
        ttk.Button(bar, text="Scan mod", command=self.scan).pack(side="right", padx=6)
        ttk.Button(bar, text="Game manifest...", command=self.game_manifest).pack(side="right")
        self.status = tk.StringVar(value="Choose the mod's data folder (for example ...\\HLR\\data) and press Load.")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=6, pady=(0, 6))

    def _build_units_tab(self):
        """Units & armies: the chosen towns on the left, their garrisons on the right."""
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Units & armies  ")
        side = ttk.Frame(tab)
        side.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(side, text="Your towns", font=("", 10, "bold")).pack(anchor="w")
        self.lb_units = tk.Listbox(side, width=30, height=12, exportselection=False)
        self.lb_units.pack(fill="both", expand=True)
        self.lb_units.bind("<<ListboxSelect>>", lambda e: (self.lb_field.selection_clear(0, "end"),
                                                           self.load_garrison()))
        ttk.Label(side, text="add towns on the Faction tab", foreground="#666").pack(anchor="w")
        # field armies, agents and fleets, placed on the Map
        ff = ttk.LabelFrame(side, text="Armies, agents & fleets", padding=4)
        ff.pack(fill="x", pady=(8, 0))
        self.lb_field = tk.Listbox(ff, width=30, height=6, exportselection=False)
        self.lb_field.pack(fill="x")
        self.lb_field.bind("<<ListboxSelect>>", lambda e: self.load_field())
        fb = ttk.Frame(ff)
        fb.pack(fill="x", pady=(4, 0))
        for text, kind in (("+ Army", "army"), ("+ Agent", "spy"), ("+ Fleet", "fleet")):
            ttk.Button(fb, text=text, width=8, command=lambda k=kind: self.add_field(k)).pack(side="left", padx=1)
        fb2 = ttk.Frame(ff)
        fb2.pack(fill="x", pady=(2, 0))
        ttk.Button(fb2, text="Place on map", command=self.place_field).pack(side="left", padx=1)
        ttk.Button(fb2, text="Remove", command=self.remove_field).pack(side="left", padx=1)
        opts = self.units_opts = ttk.LabelFrame(side, text="Towns without a garrison of your own", padding=6)
        opts.pack(fill="x", pady=(10, 0))
        ttk.Label(opts, text="Leader's army").grid(row=0, column=0, sticky="w")
        self.v_army = tk.StringVar(value="balanced")
        ttk.Combobox(opts, textvariable=self.v_army, state="readonly", width=12,
                     values=("balanced", "template", "bodyguard")).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(opts, text="balanced = sized like similar factions", foreground="#666").grid(
            row=1, column=0, columnspan=2, sticky="w")
        ttk.Label(opts, text="Old garrisons").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.v_garrison = tk.StringVar(value="replace")
        gf = ttk.Frame(opts)
        gf.grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(gf, text="replace with own units", value="replace", variable=self.v_garrison).pack(side="left")
        ttk.Radiobutton(gf, text="keep", value="keep", variable=self.v_garrison).pack(side="left")
        self.garrison_editor = GarrisonEditor(tab, pictures=self.pictures)
        self.garrison_editor.pack(side="left", fill="both", expand=True)

    def _build_buildings_tab(self):
        """Buildings: the chosen towns on the left, what stands in the selected one on the right."""
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Buildings  ")
        side = ttk.Frame(tab)
        side.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(side, text="Your towns", font=("", 10, "bold")).pack(anchor="w")
        self.lb_build = tk.Listbox(side, width=30, height=12, exportselection=False)
        self.lb_build.pack(fill="both", expand=True)
        self.lb_build.bind("<<ListboxSelect>>", lambda e: self.load_buildings())
        ttk.Label(side, text="add towns on the Faction tab", foreground="#666").pack(anchor="w")
        self.buildings_editor = BuildingsEditor(tab, self.pictures)
        self.buildings_editor.pack(side="left", fill="both", expand=True)

    def load_buildings(self):
        sel = self.lb_build.curselection()
        if not sel or not self.mod or not self.strat or sel[0] >= len(self.chosen):
            return
        region = self.chosen[sel[0]]
        template = self.v["template"].get().strip()
        if not template:
            messagebox.showerror(APP, "pick the template faction first (Faction tab)")
            return
        if self._edb_for != self.mod.data:
            self._edb = read_buildings(self.mod.load(self.mod.file("edb"))) if self.mod.file("edb") else []
            self._bpics = BuildingPictures(self.mod)
            self._edb_for = self.mod.data
        st = self.strat.settlement_of(region)
        town_level, own = settlement_info(self.strat.lines[st.start:st.end]) if st else ("town", [])

        def changed(picked):
            if picked is None:
                self.buildings_picked.pop(region, None)
            else:
                self.buildings_picked[region] = picked
            self.refresh_chosen(keep_units_selection=True)
        self.buildings_editor.load(region, town_level, self._edb, own, self.buildings_picked.get(region),
                                   self.mod.culture(template), self.v["name"].get().strip().lower() or template,
                                   template, self._bpics, changed)

    def tab_opened(self):
        """A town tab with nothing selected opens the capital."""
        tab = self.nb.index("current")
        if tab == 3:
            self.show_map()
            return
        lb, load = {1: (self.lb_units, self.load_garrison), 2: (self.lb_build, self.load_buildings)}.get(tab, (None, None))
        if lb is not None and self.chosen and not lb.curselection():
            capital = self.v["capital"].get() or self.chosen[0]
            lb.selection_set(self.chosen.index(capital) if capital in self.chosen else 0)
            load()

    def editing(self):
        return self.v_mode.get() == "edit"

    def mode_changed(self):
        """New faction (clone a template) or Edit faction (change one in place)."""
        edit = self.editing()
        self.lf.configure(text="Edit faction" if edit else "New faction")
        self.lbl_template.configure(text="Faction (edited)" if edit else "Template (copied)")
        self.lf2.configure(text="Leader and heir (names from the faction's name list)" if edit else
                           "Leader and heir (names must come from the template's name list)")
        self.e_name.configure(state="readonly" if edit else "normal")
        # cloning-only options are hidden in Edit (diplomacy gets its own editor later)
        for w in [self.chk_triggers, self.chk_art] + self.dip_row:
            if edit:
                w.grid_remove()
            else:
                w.grid()
        if edit:
            self.give_frame.pack(fill="x")
        else:
            self.give_frame.pack_forget()
        for w in self.units_opts.winfo_children():
            try:
                w.configure(state="disabled" if edit else "normal")
            except tk.TclError:
                pass
        self.b_create.configure(text="Apply changes" if edit else "Create faction")
        self.garrison_editor.auto_text = ("unchanged - the town keeps its garrison" if edit else None)
        self.chosen, self.garrisons, self.buildings_picked = [], {}, {}
        self.editing_now = None
        self.char_moves = {}
        self.field, self._placing = [], None
        self.refresh_field()
        self.refresh_chosen()
        if edit and self.v["template"].get():
            self.template_changed()
        self.status.set("Edit: pick the faction to change; untouched fields stay as they are." if edit else
                        "New: pick the template to copy.")

    def load_existing(self):
        """Fill the window with the edited faction as it is now."""
        faction = self.v["template"].get().strip()
        try:
            now = read_faction(self.mod, self.v_campaign.get(), faction)
        except Exception as e:
            messagebox.showerror(APP, str(e))
            return
        self.editing_now = now
        self.v["name"].set(faction)
        for k in ("display_name", "short_name", "adjective", "ai"):
            self.v[k].set(now.get(k) or "")
        self.v["denari"].set(str(now.get("denari", "")))
        self.v_playable.set(bool(now.get("playable")))
        for t, k in ((self.t_descr, "description"), (self.t_long, "long_description")):
            t.delete("1.0", "end")
            t.insert("1.0", now.get(k) or "")
        for key, b in (("primary", self.b_primary), ("secondary", self.b_secondary)):
            rgb = now.get(key + "_colour")
            self.colours[key] = rgb
            if rgb:
                b.configure(bg="#%02x%02x%02x" % tuple(rgb))
        for role in ("leader", "heir"):
            who = now.get(role) or {}
            name = who.get("name", "")
            first = name.split(" ")[0] if name else ""
            self.v[role + "_first"].set(first)
            self.v[role + "_last"].set(name[len(first):].strip())
            self.v[role + "_age"].set(str(who.get("age") or ""))
        self.cb_give["values"] = [n for n, _ in self.mod.factions() if n != faction]
        self.v_give.set("slave")
        self.chosen = list(now.get("regions", []))
        self.garrisons, self.buildings_picked = {}, {}
        self.char_moves = {}
        if self.chosen:
            self.v["capital"].set(self.chosen[0])
        self.refresh_chosen()
        self.status.set("Editing %s: %d town(s). Change what you want, Preview, then Apply changes."
                        % (faction, len(self.chosen)))

    def show_map(self):
        """The Map tab: the campaign map with the towns as they would stand after this run."""
        if not self.mod or not self.strat:
            return
        key = (self.mod.data, self.v_campaign.get())
        if self._cmap_for != key:
            self.status.set("Reading the campaign map...")
            self.update_idletasks()
            try:
                self._cmap = CampaignMap(self.mod, self.v_campaign.get())
            except Exception as e:
                messagebox.showerror(APP, "Cannot draw the map: %s" % e)
                return
            self._cmap_for = key
            self._colours_all = faction_colours(self.mod)
            self.status.set("")
        owners = self.strat.owners()
        colours = dict(self._colours_all)
        me = self.v["template"].get().strip() if self.editing() else (self.v["name"].get().strip().lower() or "(new)")
        if not self.editing():
            template = self.v["template"].get().strip()
            colours[me] = tuple(self.colours["primary"] or colours.get(template, (255, 215, 0)))
        elif self.colours["primary"]:
            colours[me] = tuple(self.colours["primary"])
        for r in self.chosen:
            owners[r] = me
        if self.editing() and self.editing_now:
            for r in self.editing_now.get("regions", []):
                if r not in self.chosen:
                    owners[r] = self.v_give.get() or "slave"
        chars, armies_at = [], set()
        for fb in self.strat.factions:
            for i, c in enumerate(fb.characters):
                if not c.xy:
                    continue
                lines = self.strat.lines[c.start:c.end]
                army = any(tokens(l)[:1] == ["army"] for l in lines)
                cid = "%s:%d" % (fb.name, i)
                xy = self.char_moves.get(cid, c.xy)
                chars.append({"id": cid, "faction": fb.name, "name": c.name, "kind": c.kind, "xy": xy,
                              "army": army, "units": sum(1 for l in lines if tokens(l)[:1] == ["unit"]),
                              "from": c.xy})
                if army:
                    armies_at.add(xy)
        from .start import KINDS
        for i, fc in enumerate(self.field):
            if fc.get("xy"):
                rtw_kind, army = KINDS[fc["kind"]]
                chars.append({"id": "new:%d" % i, "faction": me, "name": fc["name"], "kind": rtw_kind,
                              "xy": tuple(fc["xy"]), "army": army, "units": len(fc["units"]), "from": None})
                if army:
                    armies_at.add(tuple(fc["xy"]))
        mine = [ch["id"] for ch in chars if (self.editing() and ch["faction"] == me) or ch["id"].startswith("new:")]
        self._map_chars = {ch["id"]: ch for ch in chars}

        def check(cid, xy):
            ch = self._map_chars[cid]
            return self.mod.tile_problem(self.v_campaign.get(), xy, ch["kind"], ch["army"],
                                         armies_at - {ch["xy"]})

        def moved(cid, xy):
            ch = self._map_chars[cid]
            if cid.startswith("new:"):
                self.field[int(cid[4:])]["xy"] = xy
                self.refresh_field()
                self.show_map()
                return
            if xy == ch["from"]:
                self.char_moves.pop(cid, None)
            else:
                self.char_moves[cid] = xy
            self.status.set("%s: %d character(s) moved on the map - Preview, then Apply changes."
                            % (ch["name"], len(self.char_moves)))
            self.show_map()
        symbols = {}
        folder = os.path.join(self.mod.data, "menu", "symbols", "FE_buttons_24")
        if os.path.isdir(folder):
            for n in os.listdir(folder):
                low = n.lower()
                if low.startswith("symbol24_") and low.endswith(".tga") and "_grey" not in low and \
                        "_roll" not in low and "_select" not in low:
                    symbols[low[9:-4]] = os.path.join(folder, n)
        placing = getattr(self, "_placing", None)

        def place(xy):
            i = self._placing
            fc = self.field[i]
            rtw_kind, army = KINDS[fc["kind"]]
            why = self.mod.tile_problem(self.v_campaign.get(), xy, rtw_kind, army, armies_at)
            if why:
                return why
            fc["xy"] = xy
            self._placing = None
            self.refresh_field(keep=i)
            self.status.set("%s %s placed at %d, %d - drag it to move it." % (fc["kind"], fc["name"], xy[0], xy[1]))
            self.show_map()
            return None
        self.map_view.load(self._cmap, owners, colours, me, self.chosen, on_city=self.map_city, chars=chars,
                           draggable=mine, on_char_move=moved, check_tile=check, symbols=symbols,
                           on_place=place if placing is not None else None)

    def map_city(self, region):
        """A click on a town on the map: add it to Chosen, or take it out."""
        if region in self.chosen:
            self.chosen.remove(region)
            self.garrisons.pop(region, None)
            self.buildings_picked.pop(region, None)
        else:
            self.chosen.append(region)
        self.refresh_chosen()
        self.show_map()
        town = self._cmap.info.get(region, {}).get("settlement", region) if self._cmap else region
        self.status.set("%s %s. %d town(s) chosen." % (town, "added" if region in self.chosen else "taken out",
                                                       len(self.chosen)))

    def selected_town(self):
        sel = self.lb.curselection()
        return self.chosen[sel[0]] if sel else None

    def show_units(self, region=None):
        """Switch to the Units & armies tab, with this town (or the capital) open."""
        if not self.chosen:
            messagebox.showerror(APP, "add a town to Chosen first")
            return
        region = region or self.v["capital"].get() or self.chosen[0]
        self.nb.select(1)
        i = self.chosen.index(region) if region in self.chosen else 0
        self.lb_units.selection_clear(0, "end")
        self.lb_units.selection_set(i)
        self.load_garrison()

    # ------------------------------------------------------------------ loading
    def browse(self):
        d = filedialog.askdirectory(title="The mod's data folder")
        if d:
            self.v_path.set(d)
            self.load()

    def load(self):
        try:
            self.mod = ModData(self.v_path.get())
            self._units_for = self._edb_for = None
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

    def new_mod(self):
        """Make <game>/<name> from the loaded mod (hard links + copied text), then load it."""
        if not self.mod:
            messagebox.showerror(APP, "load the mod (or the game's data folder) to build on first")
            return
        game, base = game_root_of(self.mod.data)
        w = tk.Toplevel(self)
        w.title("New mod folder")
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Based on:  %s" % (base or "the game's own data"), font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="Created in:  %s" % game).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(frm, text="New mod name").grid(row=2, column=0, sticky="w")
        v_name = tk.StringVar(value=(base or "RTW") + "_" + (self.v["name"].get().strip().capitalize() or "New"))
        ttk.Entry(frm, textvariable=v_name, width=30).grid(row=3, column=0, sticky="we", padx=(0, 6))
        v_copy = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Copy every file (no hard links; needs the disk space)", variable=v_copy).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Label(frm, justify="left", wraplength=520, text=(
            "The base stays untouched. Text files are copied; models, textures and sounds are hard links - "
            "the same file under a second name, no extra space. Do not edit a linked texture in place "
            "(an editor that overwrites it changes the base too); tick 'Copy every file' to be fully apart. "
            "A start script Start_<name>.bat is written into the new folder.")).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 8))

        def go():
            name = v_name.get().strip()
            w.destroy()
            self.status.set("Building %s ..." % name)
            result = {}

            def work():
                try:
                    result["data"], result["stats"] = create_mod(
                        self.mod.data, name, v_copy.get(),
                        progress=lambda n: result.__setitem__("n", n))
                except Exception as e:
                    result["error"] = str(e)
            th = threading.Thread(target=work, daemon=True)
            th.start()

            def wait():
                if th.is_alive():
                    self.status.set("Building %s ... %d files" % (name, result.get("n", 0)))
                    self.after(300, wait)
                    return
                if "error" in result:
                    self.status.set("")
                    messagebox.showerror(APP, result["error"])
                    return
                st = result["stats"]
                self.v_path.set(result["data"])
                self.load()
                messagebox.showinfo(APP, (
                    "Made %s\n\n%d file(s) linked, %d copied (%.0f MB)%s.\n\nIt is loaded now: the faction "
                    "you create goes into it. Start the game with %s." % (
                        st["target"], st["linked"], st["copied"], st["bytes_copied"] / 1048576.0,
                        "" if st["hard_links"] else " - no hard links (another drive or 'copy every file')",
                        "Start_%s.bat" % name)))
            wait()
        bar = ttk.Frame(frm)
        bar.grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Button(bar, text="Create", command=go).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

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
        self.garrisons = {}
        self.buildings_picked = {}
        self.field, self._placing = [], None
        self.refresh_field()
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
        if self.editing():
            self.load_existing()
        fb = self.strat.faction(t) if self.strat else None
        if fb:
            parts = fb.header.split(";")[0].split(",", 1)
            self.v["ai"].set(" ".join(parts[1].split()) if len(parts) > 1 else "")
        # the list offers every economy x military pair, plus what this campaign already uses
        # (variants like 'balanced smith random' or REX's 'opportunist')
        seen = {" ".join(x.header.split(";")[0].split(",", 1)[1].split())
                for x in (self.strat.factions if self.strat else []) if "," in x.header}
        self.cb_ai["values"] = AI_CHOICES + sorted(v for v in seen if v and v not in AI_CHOICES)
        pool = self.mod.name_pool(t)
        for a, b in self.cb_names:
            a["values"] = pool.get("characters", [])
            b["values"] = [""] + pool.get("surnames", [])
        disp = template_display(self.mod, t, self.v_campaign.get())
        if self.editing():
            return
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
        for r in sel:
            self.garrisons.pop(r, None)
            self.buildings_picked.pop(r, None)
        self.refresh_chosen()

    def refresh_chosen(self, keep_units_selection=False):
        sel = self.lb_units.curselection()
        self.lb_units.delete(0, "end")
        for r in self.chosen:
            n = len(self.garrisons.get(r, []))
            self.lb_units.insert("end", "%s%s%s" % (r, "  (capital)" if r == (self.v["capital"].get() or
                                 (self.chosen[0] if self.chosen else "")) else "",
                                 "  [%d units]" % n if n else ("  [unchanged]" if self.editing() else "  [automatic]")))
        if keep_units_selection and sel and sel[0] < len(self.chosen):
            self.lb_units.selection_set(sel[0])
        bsel = self.lb_build.curselection()
        self.lb_build.delete(0, "end")
        for r in self.chosen:
            n = len(self.buildings_picked.get(r, []))
            self.lb_build.insert("end", "%s%s" % (r, "  [%d buildings]" % n if r in self.buildings_picked
                                                    else "  [its own]"))
        if keep_units_selection and bsel and bsel[0] < len(self.chosen):
            self.lb_build.selection_set(bsel[0])
        self.lb.delete(0, "end")
        for r in self.chosen:
            owner = self.strat.owners().get(r, "?") if self.strat else "?"
            mark = "  [%d units]" % len(self.garrisons[r]) if r in self.garrisons else ""
            self.lb.insert("end", "%s  (%s)%s" % (r, owner, mark))
        self.cb_capital["values"] = self.chosen
        if self.v["capital"].get() not in self.chosen:
            self.v["capital"].set(self.chosen[0] if self.chosen else "")

    # ---- field armies, agents, fleets ----
    AGENTS = ("spy", "assassin", "diplomat")

    def refresh_field(self, keep=None):
        self.lb_field.delete(0, "end")
        for c in self.field:
            where = "at %d, %d" % tuple(c["xy"]) if c.get("xy") else "not placed"
            units = "  [%d units]" % len(c["units"]) if c["kind"] in ("army", "fleet") else ""
            self.lb_field.insert("end", "%s %s%s  (%s)" % (c["kind"], c["name"], units, where))
        if keep is not None and keep < len(self.field):
            self.lb_field.selection_set(keep)

    def field_faction(self):
        return self.v["template"].get().strip()

    def add_field(self, kind):
        """A small form: kind (agents), name from the faction's name list, age."""
        if not self.mod or not self.field_faction():
            messagebox.showerror(APP, "load a mod and pick the %s first" % ("faction" if self.editing() else "template"))
            return
        pool = self.mod.name_pool(self.field_faction()) or {}
        w = tk.Toplevel(self)
        w.title({"army": "New army", "spy": "New agent", "fleet": "New fleet"}[kind])
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack()
        v_kind = tk.StringVar(value=kind)
        row = 0
        if kind in self.AGENTS:
            ttk.Label(frm, text="Agent").grid(row=row, column=0, sticky="w")
            ttk.Combobox(frm, textvariable=v_kind, values=self.AGENTS, state="readonly", width=14).grid(
                row=row, column=1, sticky="w")
            row += 1
        ttk.Label(frm, text="Name" if kind in self.AGENTS else ("Admiral" if kind == "fleet" else "General")).grid(
            row=row, column=0, sticky="w")
        v_first, v_last, v_age = tk.StringVar(), tk.StringVar(), tk.StringVar(value="30")
        ttk.Combobox(frm, textvariable=v_first, values=pool.get("characters", []), width=16).grid(row=row, column=1)
        ttk.Combobox(frm, textvariable=v_last, values=[""] + pool.get("surnames", []), width=16).grid(row=row, column=2)
        row += 1
        ttk.Label(frm, text="Age").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v_age, width=5).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frm, text="names come from the faction's name list", foreground="#666").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(4, 0))

        def ok():
            first = v_first.get().strip()
            if not first:
                messagebox.showerror(APP, "pick a first name", parent=w)
                return
            self.field.append({"kind": v_kind.get(), "name": (first + " " + v_last.get().strip()).strip(),
                               "age": int(v_age.get()) if v_age.get().isdigit() else 30, "units": [], "xy": None})
            w.destroy()
            self.refresh_field(keep=len(self.field) - 1)
            self.load_field()
        bar = ttk.Frame(frm)
        bar.grid(row=row + 1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(bar, text="Add", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    def selected_field(self):
        sel = self.lb_field.curselection()
        return sel[0] if sel and sel[0] < len(self.field) else None

    def load_field(self):
        """An army or fleet opens in the card picker; an agent has no units."""
        i = self.selected_field()
        if i is None:
            return
        self.lb_units.selection_clear(0, "end")
        c = self.field[i]
        if c["kind"] in self.AGENTS:
            self.garrison_editor.load(self.mod, self.field_faction(), "%s %s - an agent, no units" % (c["kind"], c["name"]),
                                      [], [], lambda t: None)
            return
        units = faction_units(self.mod, self.field_faction(), ships=c["kind"] == "fleet")
        if c["kind"] == "fleet" and units and all(u.mercenary for u in units):
            self.garrison_editor.v_merc.set(True)     # many mods mark every ship a mercenary

        def changed(types, i=i):
            self.field[i]["units"] = types
            self.refresh_field(keep=i)
        self.garrison_editor.load(self.mod, self.field_faction(), "%s %s" % (c["kind"], c["name"]), units,
                                  c["units"], changed)
        if not c.get("xy"):
            self.status.set("Pick the units, then 'Place on map'.")

    def remove_field(self):
        i = self.selected_field()
        if i is not None:
            del self.field[i]
            self.refresh_field()

    def place_field(self):
        """Go to the Map; the next click on a good tile places the selected one."""
        i = self.selected_field()
        if i is None:
            messagebox.showerror(APP, "select an army, agent or fleet in the list first")
            return
        c = self.field[i]
        self._placing = i
        if self.nb.index("current") == 3:
            self.show_map()                 # already there: no tab event, so refresh by hand
        else:
            self.nb.select(3)
        self.status.set("Click the tile for %s %s (%s)." % (c["kind"], c["name"],
                        "sea" if c["kind"] == "fleet" else "land, or a town for an agent"))

    def load_garrison(self):
        """Open the selected town of the Units tab in the garrison editor."""
        sel = self.lb_units.curselection()
        if not sel or not self.mod or sel[0] >= len(self.chosen):
            return
        region = self.chosen[sel[0]]
        template = self.v["template"].get().strip()
        if not template:
            messagebox.showerror(APP, "pick the template faction first (Faction tab)")
            return
        if self._units_for != template:
            self._units_cache = faction_units(self.mod, template)
            self._units_for = template
        units = self._units_cache
        capital = self.v["capital"].get() or self.chosen[0]
        order = [capital] + [r for r in self.chosen if r != capital]      # as the build orders them
        heir_town = order[1] if self.v["heir_first"].get().strip() and len(order) > 1 else None
        held = "leader" if region == capital else "heir" if region == heir_town else False
        if self.editing():
            # whoever of the faction stands in the town with an army: a named one keeps his bodyguard
            xy = self.mod.city_tiles(self.v_campaign.get()).get(region)
            fb = self.strat.faction(template) if self.strat else None
            holder = next((c for c in (fb.characters if fb else []) if c.xy == xy and
                           any(tokens(l)[:1] == ["army"] for l in self.strat.lines[c.start:c.end])), None)
            held = (holder.role or "general") if holder is not None and holder.named else False

        def auto():
            try:
                strat = Strat(self.mod.load(self.mod.campaign_file(self.v_campaign.get(), "descr_strat.txt")))
                upkeep = {u.type: u.upkeep for u in read_units(self.mod.load(self.mod.file("edu")))}
                lines, _, _ = balanced_army(strat, template, len(self.chosen), upkeep, [])
                return [unit_name(l) for l in lines[1:]]           # without the bodyguard
            except Exception:
                return []

        def changed(types):
            if types:
                self.garrisons[region] = types
            else:
                self.garrisons.pop(region, None)
            self.refresh_chosen(keep_units_selection=True)
        self.garrison_editor.load(self.mod, template, region, units, self.garrisons.get(region, []),
                                  changed, auto=auto, held=held)

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
                      "army_mode": self.v_army.get(), "garrison": self.v_garrison.get(),
                      "garrisons": {r: g for r, g in self.garrisons.items() if r in self.chosen},
                      "characters": [dict(c) for c in self.field],
                      "buildings": {r: [list(x) for x in b] for r, b in self.buildings_picked.items()
                                    if r in self.chosen}},
        }
        return v["template"], v["name"].lower(), opts

    def gather_edit(self):
        v = {k: x.get().strip() for k, x in self.v.items()}
        if not v["template"]:
            raise ValueError("pick the faction to edit")
        had = list((self.editing_now or {}).get("regions", []))

        def person(role):
            if not v[role + "_first"]:
                return None
            return {"name": (v[role + "_first"] + " " + v[role + "_last"]).strip(),
                    "age": int(v[role + "_age"]) if v[role + "_age"].isdigit() else None}
        return v["template"], {
            "display_name": v["display_name"], "short_name": v["short_name"], "adjective": v["adjective"],
            "description": self.t_descr.get("1.0", "end").strip(),
            "long_description": self.t_long.get("1.0", "end").strip(),
            "primary_colour": self.colours["primary"], "secondary_colour": self.colours["secondary"],
            "ai": v["ai"], "denari": int(v["denari"]) if v["denari"].isdigit() else None,
            "playable": self.v_playable.get(),
            "take": [r for r in self.chosen if r not in had],
            "give": {r: self.v_give.get() or "slave" for r in had if r not in self.chosen},
            "capital": v["capital"] if self.chosen and v["capital"] in self.chosen else None,
            "leader": person("leader"), "heir": person("heir"),
            "moves": [{"name": self._map_chars[cid]["name"], "from": self._map_chars[cid]["from"], "to": xy}
                      for cid, xy in self.char_moves.items() if cid in getattr(self, "_map_chars", {})],
            "characters": [dict(c) for c in self.field],
            "garrisons": dict(self.garrisons),
            "buildings": {r: [list(x) for x in b] for r, b in self.buildings_picked.items()}}

    def make_plan(self):
        if self.editing():
            if not self.mod:
                raise ValueError("load a mod first")
            faction, opts = self.gather_edit()
            return edit_faction(ModData(self.mod.data), self.v_campaign.get(), faction, opts)
        template, name, opts = self.gather()
        # a fresh read, so a previous preview's edits never leak in
        mod = ModData(self.mod.data)
        return build(mod, self.v_campaign.get(), template, name, opts)

    def show_text(self, title, text, extra=()):
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
        for label, cmd in extra:
            ttk.Button(bar, text=label, command=cmd).pack(side="left", padx=4)
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

    def scan(self):
        """Every mention of the template in the whole mod, in a background thread."""
        if not self.mod:
            messagebox.showerror(APP, "load a mod first")
            return
        faction = self.v["template"].get().strip()
        if not faction:
            messagebox.showerror(APP, "pick the template faction to scan for")
            return
        campaign = self.v_campaign.get()
        self.status.set("Scanning the mod for '%s'..." % faction)
        result = {}

        def work():
            try:
                result["text"] = scan_mod(ModData(self.mod.data), faction, campaign).report()
            except Exception:
                result["text"] = "Scan failed:\n\n" + traceback.format_exc()

        th = threading.Thread(target=work, daemon=True)
        th.start()

        def wait():
            if th.is_alive():
                self.after(200, wait)
                return
            self.status.set("Scan done.")
            self.show_text("Scan: %s - nothing written" % faction, result["text"],
                           extra=[("Ignore list...", self.edit_ignore), ("Scan again", self.scan)])
        wait()

    def game_manifest(self):
        """Fingerprint every file of the game (not of its mods) into rtw_manifest.json.gz."""
        start = game_root_of(self.mod.data)[0] if self.mod else None
        root = filedialog.askdirectory(title="The game folder (the one with RomeTW.exe / REX.exe)",
                                       initialdir=start or "")
        if not root:
            return
        if not messagebox.askyesno(APP, "Fingerprint every game file under\n%s\n\nMod folders in it are left out. "
                                        "For a clean list, let Steam 'Verify integrity of game files' first.\n"
                                        "This reads every file once and can take a minute or two." % root):
            return
        result = {}

        def work():
            try:
                result["out"] = make_manifest(root, progress=lambda n: result.__setitem__("n", n))
            except Exception as e:
                result["error"] = str(e)
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def wait():
            if th.is_alive():
                self.status.set("Fingerprinting the game... %d files" % result.get("n", 0))
                self.after(300, wait)
                return
            if "error" in result:
                self.status.set("")
                messagebox.showerror(APP, result["error"])
                return
            out, n, skipped = result["out"]
            self.status.set("Wrote %s" % out)
            messagebox.showinfo(APP, "Wrote %s\n\n%d game file(s). Mod folders left out: %s" % (
                out, n, ", ".join(skipped) or "none"))
        wait()

    def edit_ignore(self):
        """A small editor for the mod's faction_tool_ignore.txt."""
        path = ignore_path(os.path.dirname(self.mod.data))
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            text = IGNORE_HELP
        w = tk.Toplevel(self)
        w.title("Scan ignore list - " + path)
        w.geometry("700x420")
        bar = ttk.Frame(w, padding=4)
        bar.pack(side="bottom", fill="x")
        t = tk.Text(w, wrap="none", font=("Consolas", 10), undo=True)
        t.pack(fill="both", expand=True)
        t.insert("1.0", text)

        def save():
            with open(path, "w", encoding="utf-8") as f:
                f.write(t.get("1.0", "end-1c").rstrip("\n") + "\n")
            w.destroy()
            self.status.set("Saved %s - press Scan mod again." % path)
        ttk.Button(bar, text="Save", command=save).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)
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
        self.show_text("Done", plan.report() + "\n\nBackup: %s\nStart a NEW campaign to see the %s." % (
            bdir, "changes" if self.editing() else "faction"))
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
