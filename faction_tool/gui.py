"""The window: pick the mod, fill in the faction, preview, create, restore."""

import copy
import os
import re
import threading
import traceback
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import log
from .build import build, template_display
from .buildings import (POP_MIN, SETTLEMENT_LEVELS, BuildingPictures, core_need, population_of, rank,
                        read_buildings, settlement_info)
from .mapdata import CampaignMap, faction_colours
from .moddata import ModData
from .mapedit import orig as place_orig, place_problem, port_fleets, sea_spot
from .newmod import create_mod, game_root_of
from .edit import edit as edit_faction, read_faction
from .gui_buildings import BuildingsEditor
from .gui_diplomacy import DiplomacyEditor, colour as dip_colour
from .gui_garrison import GarrisonEditor, Pictures
from .gui_map import MapView
from .plan import Plan, backups, restore
from .scan import IGNORE_HELP, ignore_path, make_manifest, scan as scan_mod
from .start import balanced_army, unit_name
from .strat import Strat
from .textio import tokens
from .units import faction_units, read_units

VERSION = "0.1.2"
APP = "RTW Campaign Editor"

HELP = """RTW Campaign Editor - how to use it

START
  1. Close the game. Browse... to the mod's data folder (for example ...\\HLR\\data), press Load.
     Better: New mod folder... makes a copy of the mod to work on; the base stays untouched.
  2. Pick the campaign (usually imperial_campaign).
  3. New faction: pick a template to copy.   Edit faction: pick the faction to change.

THE TABS (in the order that works best)
  Faction      names, texts, colours, AI, money, playable; the towns it starts with
               (double-click in the list, or click towns on the Map); capital, leader, heir.
  Units & armies
               the garrison of each town (click cards to add, click the garrison to take out);
               new armies, agents and fleets (+ Army / + Agent / + Fleet, then Place on map);
               in Edit also the faction's armies, fleets and agents already on the map.
  Buildings    what stands in each town; settlement level and population. A bigger
               governor's building grows the settlement by itself.
  Map          left drag moves the map, a click on a town takes it / gives it back;
               right drag (or Ctrl + left drag) moves your characters, towns and ports;
               Political, Diplomacy and the other switches change what is shown.
  Diplomacy    how the faction and every other one feel about each other at the start.

  Only the map (regions, towns, ports)? In New faction mode with no faction named the
  buttons read "Preview map changes" / "Apply map changes" and write the map alone.
  Check mod, Scan mod, Restore a backup, Game manifest and Log are under Tools.

  4. Preview changes (Ctrl+P) shows every file and line that would change. Nothing is written.
  5. Create faction / Apply changes (Ctrl+S) writes it, with a backup first.
  6. Start a NEW campaign in the game - old saves do not see the changes.
  Something wrong? Restore a backup... puts the files back exactly (newest first).

KEYS
  Ctrl+Z undo, Ctrl+Y (or Ctrl+Shift+Z) redo - towns, garrisons, buildings, map moves,
  armies, diplomacy (in a text box Ctrl+Z undoes the typing instead)
  Ctrl+P preview    Ctrl+S apply / create    F5 load the mod again    F1 this help
  Ctrl+1 .. Ctrl+5 the tabs    Map: wheel zooms, left drag moves the map, right drag moves a marker

WHEN SOMETHING GOES WRONG
  Log shows what the tool did and every error (faction_tool.log next to the exe).
  Check mod reads the whole mod and reports anything it cannot make sense of.
  Send faction_tool.log and the game's system.log.txt.
"""

_showerror = messagebox.showerror


def _logged_error(title=None, message=None, **kw):
    """Every error box also goes to faction_tool.log."""
    log.error(message)
    return _showerror(title, message, **kw)


messagebox.showerror = _logged_error

# descr_strat.txt: "faction <name>, <economy> <military>" - the words the game knows
AI_ECONOMY = ("balanced", "bureaucrat", "comfortable", "craftsman", "fortified", "religious", "sailor", "trader")
AI_MILITARY = ("caesar", "genghis", "henry", "mao", "napoleon", "smith", "stalin")
AI_CHOICES = ["%s %s" % (e, m) for e in AI_ECONOMY for m in AI_MILITARY]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("%s %s" % (APP, VERSION))
        self.geometry("1200x800")
        self.minsize(900, 640)
        self.mod = None
        self.strat = None
        self.regions = {}
        self.chosen = []
        self.garrisons = {}             # region -> [unit type] picked by hand
        self.field = []                 # [{kind, name, age, units, xy}] armies/agents/fleets to place
        self.removed_existing = []      # Edit: [{name, from}] characters taken off the map
        self.place_moves = {}           # {('city' | 'port', region): (x, y)} towns and ports moved on the map
        self.dip_set = {}               # {(kind, from, to): value or None} picked on the Diplomacy tab ('me' = the faction)
        self.region_paint = {}          # {(x, y): region} tiles painted to another region (Regions mode)
        self.new_regions = []           # [{name, settlement, creator, rebels, resources, colour, city, port, owner, level}]
        self._region_point = None       # ('city' | 'port', region) waiting for a click
        self.undo_stack, self.redo_stack = [], []   # snapshots of what the window keeps (Ctrl+Z / Ctrl+Y)
        self.sizes = {}                 # {region: {'level', 'population'}} set by hand on the Buildings tab
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
        self.region_bar = ttk.Frame(tab, padding=(0, 0, 0, 4))
        rb = self.region_bar
        ttk.Label(rb, text="Paint with", font=("", 9, "bold")).pack(side="left")
        self.v_paint = tk.StringVar()
        self.cb_paint = ttk.Combobox(rb, textvariable=self.v_paint, width=24)
        self.cb_paint.pack(side="left", padx=4)
        ttk.Label(rb, text="brush").pack(side="left", padx=(8, 2))
        self.v_brush = tk.IntVar(value=1)
        ttk.Spinbox(rb, from_=1, to=6, width=3, textvariable=self.v_brush,
                    command=lambda: setattr(self.map_view, "brush", self.v_brush.get())).pack(side="left")
        ttk.Button(rb, text="New region...", command=self.new_region_dialog).pack(side="left", padx=(12, 2))
        ttk.Button(rb, text="Place its town", command=lambda: self.region_point("city")).pack(side="left", padx=2)
        ttk.Button(rb, text="Place its port", command=lambda: self.region_point("port")).pack(side="left", padx=2)
        ttk.Button(rb, text="Delete this new region", command=self.drop_region).pack(side="left", padx=2)
        self.v_borders = tk.BooleanVar(value=True)
        ttk.Checkbutton(rb, text="Borders", variable=self.v_borders, command=self.show_map).pack(side="left", padx=8)
        ttk.Label(rb, text="left drag paints, right click picks a region, right drag moves the map",
                  foreground="#666").pack(side="left", padx=10)
        self.map_view = MapView(tab, on_layers=lambda: self.show_map())
        self.map_view.pack(fill="both", expand=True)
        self.map_view.on_stroke = self.remember
        self._cmap, self._cmap_for = None, None
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Diplomacy  ")
        self.dip_editor = DiplomacyEditor(tab)
        self.dip_editor.pack(fill="both", expand=True)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.tab_opened())
        self._keys()

        # --- actions
        bar = ttk.Frame(self)
        bar.pack(fill="x", **pad)
        self.b_preview = ttk.Button(bar, text="Preview changes", command=self.preview)
        self.b_preview.pack(side="left")
        self.b_create = ttk.Button(bar, text="Create faction", command=self.create)
        self.b_create.pack(side="left", padx=6)
        ttk.Button(bar, text="Undo", width=6, command=self.undo).pack(side="left", padx=(12, 0))
        ttk.Button(bar, text="Redo", width=6, command=self.redo).pack(side="left", padx=4)
        ttk.Button(bar, text="Help", command=self.show_help).pack(side="right", padx=(6, 0))
        tools = ttk.Menubutton(bar, text="Tools")
        menu = tk.Menu(tools, tearoff=False)
        menu.add_command(label="Check mod", command=self.check)
        menu.add_command(label="Scan mod (every mention of the faction)", command=self.scan)
        menu.add_command(label="Restore a backup...", command=self.restore)
        menu.add_separator()
        menu.add_command(label="Game manifest...", command=self.game_manifest)
        menu.add_command(label="Log", command=self.show_log)
        tools["menu"] = menu
        tools.pack(side="right")
        self.status = tk.StringVar(value="Choose the mod's data folder (for example ...\\HLR\\data) and press Load.")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=6, pady=(0, 6))
        self.status.trace_add("write", lambda *a: self._log_status())
        for k in ("name", "template"):
            self.v[k].trace_add("write", lambda *a: self.update_actions())
        self.update_actions()

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
        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(right, padding=(0, 0, 0, 6))
        bar.pack(fill="x")
        ttk.Label(bar, text="Settlement level").pack(side="left")
        self.v_level = tk.StringVar()
        self.cb_level = ttk.Combobox(bar, textvariable=self.v_level, values=SETTLEMENT_LEVELS, state="readonly",
                                     width=12)
        self.cb_level.pack(side="left", padx=(4, 12))
        self.cb_level.bind("<<ComboboxSelected>>", lambda e: self.level_picked())
        ttk.Label(bar, text="Population").pack(side="left")
        self.v_pop = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.v_pop, width=8)
        e.pack(side="left", padx=(4, 12))
        e.bind("<KeyRelease>", lambda ev: self.size_changed())
        self.lbl_size = ttk.Label(bar, text="", foreground="#666")
        self.lbl_size.pack(side="left")
        self.buildings_editor = BuildingsEditor(right, self.pictures)
        self.buildings_editor.pack(fill="both", expand=True)

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
        town_level, own = settlement_info(self.strat.lines[st.start:st.end]) if st else ("village", [])
        pop = population_of(self.strat.lines[st.start:st.end]) if st else 400
        self._size_region, self._size_now = region, (town_level, pop)
        size = self.sizes.get(region, {})
        self.v_level.set(size.get("level") or town_level)
        self.v_pop.set(str(size.get("population") if size.get("population") is not None else (pop or "")))
        self._size_hint()

        def changed(picked):
            self.remember()
            if picked is None:
                self.buildings_picked.pop(region, None)
            else:
                self.buildings_picked[region] = picked
            # a governor's building bigger than a level set by hand wins: the level grows to it
            hand = self.sizes.get(region, {}).get("level")
            if hand and rank(self._grown_level(picked, hand)) > rank(hand):
                self.sizes[region].pop("level")
                if self.sizes[region].get("population", 0) < POP_MIN.get(self._grown_level(picked, hand), 0):
                    self.sizes[region].pop("population", None)     # too small for the grown level
                if not self.sizes[region]:
                    self.sizes.pop(region)
            # show what a bigger governor's building does to the settlement (unless set by hand)
            if "level" not in self.sizes.get(region, {}):
                level = self._grown_level(picked, town_level)
                self.v_level.set(level)
                if level != town_level and pop is not None and pop < POP_MIN.get(level, 0) and \
                        "population" not in self.sizes.get(region, {}):
                    self.v_pop.set(str(POP_MIN[level]))
                elif "population" not in self.sizes.get(region, {}):
                    self.v_pop.set(str(pop or ""))
                if self.buildings_editor.town_level != level:
                    self.buildings_editor.after_idle(lambda: self.buildings_editor.set_level(level))
            self.refresh_chosen(keep_units_selection=True)
        # the chains offer the levels of the settlement as it will be: set by hand, grown
        # by a picked governor's building, or as the file has it
        shown = size.get("level") or self._grown_level(self.buildings_picked.get(region), town_level)
        self.buildings_editor.load(region, shown, self._edb, own, self.buildings_picked.get(region),
                                   self.mod.culture(template), self.v["name"].get().strip().lower() or template,
                                   template, self._bpics, changed)

    def _grown_level(self, picked, town_level):
        """The level a settlement gets from its picked governor's building (never smaller)."""
        need = core_need(picked or [], {b.name: b for b in self._edb})
        return need if need and rank(need) > rank(town_level) else town_level

    def level_picked(self):
        """A settlement level picked by hand: the governor's building follows it (the
        biggest that level allows), the chains offer that level's buildings, and the
        population rises to the level's threshold if it is below."""
        region = getattr(self, "_size_region", None)
        if not region:
            return
        level = self.v_level.get()
        ed = self.buildings_editor
        pop = self.v_pop.get().strip()
        bigger = SETTLEMENT_LEVELS[rank(level) + 1] if 0 <= rank(level) < len(SETTLEMENT_LEVELS) - 1 else None
        if pop.isdigit() and (int(pop) < POP_MIN.get(level, 0) or bigger and int(pop) >= POP_MIN[bigger]):
            self.v_pop.set(str(POP_MIN[level]))       # into the level's range, else it grows or shrinks at once
        self.size_changed()
        core = ed.core_for(level)
        if core and ed.current.get(core[0]) != core[1]:
            ed.town_level = level
            ed.title.configure(text="%s - a %s" % (region, level))
            ed.pick(core[0], core[1])                 # remembers for Undo and redraws
            self.status.set("%s: %s -> governor's building %s" % (region, level, core[1]))
        else:
            ed.set_level(level)

    def size_changed(self):
        """Level / population typed for the selected town; the same as now means unchanged."""
        self.remember()
        region = getattr(self, "_size_region", None)
        if not region:
            return
        level_now, pop_now = self._size_now
        level = self.v_level.get()
        pop = self.v_pop.get().strip()
        size = {}
        if level and level != level_now:
            size["level"] = level
        if pop.isdigit() and int(pop) != pop_now:
            size["population"] = int(pop)
        if size:
            self.sizes[region] = size
        else:
            self.sizes.pop(region, None)
        self._size_hint()
        self.refresh_chosen(keep_units_selection=True)

    def _size_hint(self):
        level_now, pop_now = self._size_now
        self.lbl_size.configure(text="now: %s, %s people (the level and the governor's building follow each other)"
                                     % (level_now, pop_now))

    def tab_opened(self):
        """A town tab with nothing selected opens the capital."""
        tab = self.nb.index("current")
        if tab == 3:
            self.show_map()
            return
        if tab == 4:
            self.load_diplomacy()
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
        self.update_actions()
        self.garrison_editor.auto_text = ("unchanged - the town keeps its garrison" if edit else None)
        self.chosen, self.garrisons, self.buildings_picked, self.sizes = [], {}, {}, {}
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
        self.garrisons, self.buildings_picked, self.sizes = {}, {}, {}
        self.char_moves = {}
        self.field, self.removed_existing, self._placing = self._existing_field(faction), [], None
        self.dip_set.clear()
        self.refresh_field()
        if self.chosen:
            self.v["capital"].set(self.chosen[0])
        self.refresh_chosen()
        self.status.set("Editing %s: %d town(s). Change what you want, Preview, then Apply changes."
                        % (faction, len(self.chosen)))

    def _existing_field(self, faction):
        """The faction's armies, fleets and agents already on the map, for the
        Armies, agents & fleets list (their units can change, the unnamed can go)."""
        fb = self.strat.faction(faction) if self.strat else None
        out = []
        for i, c in enumerate(fb.characters if fb else []):
            if not c.xy:
                continue
            lines = self.strat.lines[c.start:c.end]
            units = [unit_name(l) for l in lines if tokens(l)[:1] == ["unit"]]
            if c.kind == "admiral":
                kind = "fleet"
            elif c.kind in ("spy", "assassin", "diplomat", "merchant"):
                kind = c.kind
            elif units:
                kind = "army"
            else:
                continue                               # a family member without an army
            out.append({"kind": kind, "name": c.name, "units": units[1:] if c.named and units else units,
                        "xy": c.xy, "from": c.xy, "existing": True, "cid": "%s:%d" % (faction, i),
                        "named": c.named, "changed": False})
        return out

    # ------------------------------------------------------------------ undo / redo
    UNDO_KEYS = ("chosen", "garrisons", "buildings_picked", "sizes", "place_moves", "char_moves", "field",
                 "removed_existing", "dip_set", "region_paint", "new_regions")

    def snapshot(self):
        st = {k: copy.deepcopy(getattr(self, k)) for k in self.UNDO_KEYS}
        st["capital"] = self.v["capital"].get()
        return st

    def remember(self):
        """Called before every change the window keeps (towns, garrisons, buildings,
        sizes, map moves, armies, diplomacy): Undo puts the state back."""
        st = self.snapshot()
        if not self.undo_stack or self.undo_stack[-1] != st:
            self.undo_stack.append(st)
            del self.undo_stack[:-300]
            self.redo_stack.clear()

    def _restore(self, st):
        for k in self.UNDO_KEYS:
            if k == "dip_set":                    # the diplomacy tab holds this very dict
                self.dip_set.clear()
                self.dip_set.update(st[k])
            else:
                setattr(self, k, copy.deepcopy(st[k]))
        self.v["capital"].set(st["capital"])
        self.refresh_chosen()
        self.refresh_field()
        tab = self.nb.index("current")
        if tab == 1 and self.lb_units.curselection():
            self.load_garrison()
        elif tab == 1 and self.lb_field.curselection():
            self.load_field()
        elif tab == 2 and self.lb_build.curselection():
            self.load_buildings()
        elif tab == 3:
            self.show_map()
        elif tab == 4:
            self.load_diplomacy()

    def undo(self, e=None):
        if self._typing():
            return None
        while self.undo_stack:
            st = self.undo_stack.pop()
            now = self.snapshot()
            if st == now:
                continue
            self.redo_stack.append(now)
            self._restore(st)
            self.status.set("Undone (%d more step(s) back)." % len(self.undo_stack))
            return "break"
        self.status.set("Nothing to undo.")
        return "break"

    def redo(self, e=None):
        if self._typing():
            return None
        if not self.redo_stack:
            self.status.set("Nothing to redo.")
            return "break"
        self.undo_stack.append(self.snapshot())
        self._restore(self.redo_stack.pop())
        self.status.set("Redone.")
        return "break"

    def _typing(self):
        """In a text box Ctrl+Z belongs to the box."""
        w = self.focus_get()
        return w is not None and w.winfo_class() in ("Text",)

    def _keys(self):
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-Z>", self.redo)                  # Ctrl+Shift+Z
        self.bind_all("<Control-y>", self.redo)
        self.bind_all("<Control-p>", lambda e: self.preview())
        self.bind_all("<Control-s>", lambda e: self.create())
        self.bind_all("<F1>", lambda e: self.show_help())
        self.bind_all("<F5>", lambda e: self.load())
        for i in range(5):
            self.bind_all("<Control-Key-%d>" % (i + 1), lambda e, i=i: self.nb.select(i))

    def show_help(self):
        self.show_text("Help", HELP)

    def diplomacy_base(self):
        """(me, {(kind, from, to): value}) as the start stands without the picks:
        the file for an edited faction; for a new one its template's relations
        (or only the rebels' 600) as the build writes them."""
        from .diplomacy import KINDS, read
        rel = read(self.strat)
        if self.editing():
            me = self.v["template"].get().strip()
            src = me
        else:
            me = self.v["name"].get().strip().lower() or "(new)"
            src = self.v["template"].get().strip() if self.v_dip.get() == "template" else None
        base = {}
        for kind in KINDS:
            for (a, b), v in rel[kind].items():
                if src and a == src and b != me:
                    base[(kind, "me", b)] = v
                elif src and b == src and a != me:
                    base[(kind, a, "me")] = v
            if not src and rel[kind]:
                base[(kind, "me", "slave")] = base[(kind, "slave", "me")] = 600
        return me, base

    def load_diplomacy(self):
        if not self.mod or not self.strat or not self.v["template"].get().strip():
            return
        me, base = self.diplomacy_base()
        others = [fb.name for fb in self.strat.factions if fb.name != me]
        names = dict(self.mod.factions())
        self.dip_editor.before = self.remember
        self.dip_editor.load(me, others, base, self.dip_set, names,
                             lambda: self.status.set("%d diplomacy change(s) - Preview, then %s." % (
                                 len(self.dip_set), "Apply changes" if self.editing() else "Create faction")))

    # ------------------------------------------------------------------ regions
    def _region_colours(self):
        cols = {r: v["colour"] for r, v in self.regions.items()}
        cols.update({r["name"]: tuple(r["colour"]) for r in self.new_regions})
        return cols

    def _region_view(self, place):
        """The Map's Regions mode: paint overlay, callbacks, new towns and ports."""
        on = self.map_view.v_regions.get()
        if on:
            self.region_bar.pack(fill="x", before=self.map_view)
        else:
            self.region_bar.pack_forget()
            return {"region_mode": False}
        cols = self._region_colours()
        names = sorted(cols)
        self.cb_paint["values"] = [r["name"] + "  (new)" for r in self.new_regions] + names
        points = []
        for r in self.new_regions:
            for what in ("city", "port"):
                if r.get(what):
                    points.append((tuple(r[what]), what, tuple(r["colour"])))
        cm = self._cmap

        def paint(tiles):
            target = self.v_paint.get().replace("  (new)", "").strip()
            if target not in cols:
                self.status.set("Pick the region to paint with (right click on it, or the list), or make a New region.")
                return []
            took = []
            for t in tiles:
                x, y = t
                if not (0 <= x < cm.w and 0 <= y < cm.h):
                    continue
                px = cm.regions_img.get(x, y)
                was = cm.region_at(x, y)
                if was is None or px in ((0, 0, 0), (255, 255, 255)):
                    continue                              # sea, towns and ports keep their region
                if any(tuple(r.get(k) or ()) == t for r in self.new_regions for k in ("city", "port")):
                    continue
                if was == target:
                    self.region_paint.pop(t, None)
                elif self.region_paint.get(t) != target:
                    self.region_paint[t] = target
                    took.append((t, cols[target]))
            self.status.set("%d tile(s) painted to other regions." % len(self.region_paint))
            return took

        def pick(xy):
            r = self.region_paint.get(tuple(xy)) or cm.region_at(*xy)
            if r:
                new = any(n["name"] == r for n in self.new_regions)
                self.v_paint.set(r + ("  (new)" if new else ""))
                self.status.set("Painting with %s." % r)
        overlay = {t: cols[r] for t, r in self.region_paint.items() if r in cols}
        on_place = place if self._placing is not None else None
        ghost = None
        if self._region_point:
            on_place = self.place_region_point
            ghost = {"kind": self._region_point[0], "check": self.region_point_problem}
        return {"region_mode": True, "paint_overlay": overlay, "on_paint": paint, "on_pick": pick,
                "brush": self.v_brush.get(), "region_points": points, "on_place": on_place,
                "region_painted": self.region_paint, "region_colours": cols,
                "borders": self.v_borders.get(), "ghost": ghost}

    def _new_region(self, name):
        return next((r for r in self.new_regions if r["name"] == name), None)

    def region_point(self, what):
        """The next click on the map puts the town (or port) of the new region being painted."""
        name = self.v_paint.get().replace("  (new)", "").strip()
        if not self._new_region(name):
            messagebox.showerror(APP, "pick a new region in 'Paint with' first (New region... makes one)")
            return
        self._region_point = (what, name)
        self.status.set("Click the tile for the %s of %s (on its own land%s)." % (
            "town" if what == "city" else "port", name, ", by the sea" if what == "port" else ""))
        self.show_map()

    def region_point_problem(self, xy):
        what, name = self._region_point
        cm = self._cmap
        if not (0 <= xy[0] < cm.w and 0 <= xy[1] < cm.h):
            return "off the map"
        own = self.region_paint.get(tuple(xy)) or cm.region_at(*xy)
        if own != name:
            return "not %s's land - paint it first" % name
        if cm.regions_img.get(*xy) in ((0, 0, 0), (255, 255, 255)):
            return "another town or port stands there"
        if what == "port" and not any(cm.is_sea(xy[0] + dx, xy[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            return "a port needs the sea next to it"
        r = self._new_region(name)
        other = "port" if what == "city" else "city"
        if tuple(r.get(other) or ()) == tuple(xy):
            return "the town and the port need different tiles"
        return None

    def place_region_point(self, xy):
        why = self.region_point_problem(xy)
        if why:
            return why
        what, name = self._region_point
        r = self._new_region(name)
        self.remember()
        r[what] = tuple(xy)
        self._region_point = None
        self.status.set("%s of %s at %d, %d." % ("Town" if what == "city" else "Port", name, xy[0], xy[1]))
        self.show_map()
        return None

    def drop_region(self):
        name = self.v_paint.get().replace("  (new)", "").strip()
        if not self._new_region(name):
            messagebox.showerror(APP, "pick a new region in 'Paint with' first")
            return
        self.remember()
        self.new_regions = [r for r in self.new_regions if r["name"] != name]
        self.region_paint = {t: r for t, r in self.region_paint.items() if r != name}
        self.v_paint.set("")
        self.show_map()

    def new_region_dialog(self):
        if not self.mod or not self.strat:
            return
        from .regionedit import free_colour
        w = tk.Toplevel(self)
        w.title("New region")
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        facs = [fb.name for fb in self.strat.factions]
        rebels = sorted({v.get("rebels") for v in self.regions.values() if v.get("rebels")})
        res = sorted({x.strip() for v in self.regions.values() for x in (v.get("resources") or "").split(",")
                      if x.strip() and x.strip() != "none"})
        me = self.v["template"].get().strip()
        fields = [("Region - name in the files", "name", "", "letters, digits, _ ; no spaces (Tribus_Novus)"),
                  ("Region - name shown in the game", "label", "", "empty = the file name without _"),
                  ("Town - name in the files", "settlement", "", "must differ from the region's (Novus_Oppidum)"),
                  ("Town - name shown in the game", "settlement_label", "", "may be the same as the region's"),
                  ("Built by (culture of its buildings)", "creator", me or (facs[0] if facs else ""),
                   "the faction whose style the town's buildings have"),
                  ("Rebels there", "rebels", rebels[0] if rebels else "",
                   "who rises up / holds it as rebels (a rebel type of this mod)"),
                  ("Resources", "resources", "", "comma list; empty = those of the land it is cut from. "
                   "In HLR these tags also open local units"),
                  ("Triumph value", "triumph", "5", "how much taking it counts for a triumph; most use 5"),
                  ("Farming level", "farming", "3", "food from the land: 1 poor ... 5 rich; most use 2-4"),
                  ("Owner at the start", "owner", "(rebel village - no settlement written)",
                   "a faction gets a settlement; none = the game makes a rebel village"),
                  ("Town size at the start", "level", "village", "for an owner only")]
        vs = {}
        for i, (label, key, default, hint) in enumerate(fields):
            ttk.Label(frm, text=hint, foreground="#666").grid(row=i, column=2, sticky="w")
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=1)
            v = tk.StringVar(value=default)
            vs[key] = v
            if key in ("creator", "owner"):
                vals = facs if key == "creator" else ["(rebel village - no settlement written)"] + facs
                ttk.Combobox(frm, textvariable=v, values=vals, width=34).grid(row=i, column=1, sticky="we", padx=6)
            elif key == "rebels":
                ttk.Combobox(frm, textvariable=v, values=rebels, width=34).grid(row=i, column=1, sticky="we", padx=6)
            elif key == "level":
                ttk.Combobox(frm, textvariable=v, values=SETTLEMENT_LEVELS, state="readonly",
                             width=34).grid(row=i, column=1, sticky="we", padx=6)
            else:
                ttk.Entry(frm, textvariable=v, width=36).grid(row=i, column=1, sticky="we", padx=6)
        ttk.Label(frm, text="resources in this mod: " + ", ".join(res), foreground="#666", wraplength=420,
                  justify="left").grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(4, 0))

        def ok():
            from .regionedit import _ok_name
            d = {k: v.get().strip() for k, v in vs.items()}
            if not _ok_name(d["name"]) or not _ok_name(d["settlement"]):
                messagebox.showerror(APP, "names: letters, digits and _ only (like Tribus_Novus)", parent=w)
                return
            if d["name"] == d["settlement"]:
                messagebox.showerror(APP, "the region and its settlement need different names "
                                          "(like Tribus_Novus and Novus_Oppidum); their labels may be the same",
                                     parent=w)
                return
            taken = set(self._region_colours()) | {v.get("settlement") for v in self.regions.values()} | \
                {r["settlement"] for r in self.new_regions}
            clash = [n for n in (d["name"], d["settlement"]) if n in taken]
            if clash:
                messagebox.showerror(APP, "%s is taken already by a region or settlement" % clash[0], parent=w)
                return
            self.remember()
            colour = free_colour(self.mod, self.v_campaign.get(), self._region_colours().values())
            owner = d["owner"] if d["owner"] in facs else None
            self.new_regions.append({
                "name": d["name"], "settlement": d["settlement"], "label": d["label"] or None,
                "settlement_label": d["settlement_label"] or None, "creator": d["creator"] or me,
                "rebels": d["rebels"], "resources": [x.strip() for x in d["resources"].split(",") if x.strip()],
                "triumph": int(d["triumph"]) if d["triumph"].isdigit() else 5,
                "farming": int(d["farming"]) if d["farming"].isdigit() else 3,
                "colour": colour, "city": None, "port": None, "owner": owner, "level": d["level"] or "village"})
            w.destroy()
            self.v_paint.set(d["name"] + "  (new)")
            self.status.set("Paint %s's land (left drag), then 'Place its town' (and 'Place its port')." % d["name"])
            self.show_map()
        bar = ttk.Frame(frm)
        bar.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(bar, text="Add", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    def _regions_opts(self):
        if not self.region_paint and not self.new_regions:
            return None
        return {"painted": dict(self.region_paint), "new": [dict(r) for r in self.new_regions]}

    def _relations(self):
        return [{"kind": k, "from": a, "to": b, "value": v} for (k, a, b), v in self.dip_set.items()]

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
        owners = self.town_owners()
        colours = dict(self._colours_all)
        me = self.v["template"].get().strip() if self.editing() else (self.v["name"].get().strip().lower() or "(new)")
        dip_view = self.map_view.v_dip.get() and self.v["template"].get().strip()
        if dip_view:                         # every owner in the colour of how the faction stands towards it
            _, base = self.diplomacy_base()
            for other in {fb.name for fb in self.strat.factions}:
                key = ("core_attitudes", "me", other)
                v = self.dip_set[key] if key in self.dip_set else base.get(key)
                colours[other] = tuple(int(dip_colour(v)[i:i + 2], 16) for i in (1, 3, 5))
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
        tiles = self.mod.city_tiles(self.v_campaign.get())
        town_moves = {tiles[r]: xy for (w, r), xy in self.place_moves.items() if w == "city" and r in tiles}
        fleet_moves = {}                      # fleets by a moved port sail with it (as apply_places does)
        taken = {c.xy for fb in self.strat.factions for c in fb.characters if c.xy}
        for (w, r), to in self.place_moves.items():
            if w == "port":
                for c in port_fleets(self.strat, place_orig(self.mod, self.v_campaign.get(), w, r)):
                    dest = sea_spot(self.mod, self.v_campaign.get(), to, taken)
                    if dest:
                        taken.discard(c.xy)
                        taken.add(dest)
                        fleet_moves[c.start] = dest
        for fb in self.strat.factions:
            for i, c in enumerate(fb.characters):
                if not c.xy:
                    continue
                lines = self.strat.lines[c.start:c.end]
                army = any(tokens(l)[:1] == ["army"] for l in lines)
                cid = "%s:%d" % (fb.name, i)
                xy = self.char_moves.get(cid, town_moves.get(c.xy) or fleet_moves.get(c.start) or c.xy)
                chars.append({"id": cid, "faction": fb.name, "name": c.name, "kind": c.kind, "xy": xy,
                              "army": army, "units": sum(1 for l in lines if tokens(l)[:1] == ["unit"]),
                              "from": c.xy})
                if army:
                    armies_at.add(xy)
        from .start import KINDS
        for i, fc in enumerate(self.field):
            if fc.get("xy") and not fc.get("existing"):         # those are drawn from descr_strat
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
            self.remember()
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
            self.refresh_field()
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
            self.remember()
            fc["xy"] = xy
            self._placing = None
            self.refresh_field(keep=i)
            self.status.set("%s %s placed at %d, %d - drag it to move it." % (fc["kind"], fc["name"], xy[0], xy[1]))
            self.show_map()
            return None
        def check_place(what, region, xy):
            return place_problem(self.mod, self.v_campaign.get(), what, region, xy,
                                 {k: v for k, v in self.place_moves.items() if k != (what, region)})

        def place_moved(what, region, xy):
            self.remember()
            if xy == place_orig(self.mod, self.v_campaign.get(), what, region):
                self.place_moves.pop((what, region), None)
            else:
                self.place_moves[(what, region)] = xy
            self.status.set("%s of %s to %d, %d - %d town(s)/port(s) moved; Preview, then %s." % (
                "Town" if what == "city" else "Port", region, xy[0], xy[1], len(self.place_moves),
                "Apply changes" if self.editing() else "Create faction"))
            self.show_map()
        region_kw = self._region_view(place)
        on_place = region_kw.pop("on_place", place if placing is not None else None)
        if placing is not None and not region_kw.get("ghost") and placing < len(self.field):
            fc = self.field[placing]
            rtw_kind, army = KINDS[fc["kind"]]
            region_kw["ghost"] = {"kind": fc["kind"] if fc["kind"] in ("army", "fleet") else "agent",
                                  "check": lambda xy: self.mod.tile_problem(self.v_campaign.get(), xy, rtw_kind, army,
                                                                            armies_at)}
        self.map_view.load(self._cmap, owners, colours, me, self.chosen, on_city=self.map_city, chars=chars,
                           draggable=mine, on_char_move=moved, check_tile=check, symbols=symbols,
                           on_place=on_place,
                           places=self.place_moves, check_place=check_place, on_place_move=place_moved,
                           locked=self._locked_hint, **region_kw)

    def _locked_hint(self, ch):
        """Why a character on the map cannot be dragged, and what to do instead."""
        if ch["faction"] == "slave":
            return "%s is a rebel - rebels leave with their town (add it to Chosen)" % ch["name"]
        if self.editing():
            return "%s belongs to %s - pick %s in Edit faction to move it" % (ch["name"], ch["faction"], ch["faction"])
        return "%s belongs to %s - in New faction only the new faction's characters move; switch to " \
               "Edit faction and pick %s to move it" % (ch["name"], ch["faction"], ch["faction"])

    def map_city(self, region):
        """A click on a town on the map: add it to Chosen, or take it out."""
        self.remember()
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
        log.write("Load %s" % self.mod.data)
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
        self.sizes = {}
        self.field, self._placing = [], None
        self.editing_now, self.char_moves = None, {}
        self.place_moves = {}
        self.dip_set.clear()
        self.region_paint, self.new_regions, self._region_point = {}, [], None
        self._cmap_for = None                  # the map is read again: after Apply towns may stand elsewhere
        self.undo_stack, self.redo_stack = [], []
        self.refresh_field()
        self.refresh_chosen()
        self.fill_towns()
        # after Apply (which reloads) or a campaign change, the edited faction is read
        # afresh: its towns as they are now, never a stale list from before
        t = self.v["template"].get().strip()
        if self.editing() and t and self.strat.faction(t):
            self.load_existing()
        # an open Map (or Diplomacy) tab shows the files as they are now - after Apply,
        # Restore or a campaign change - not the picture read before
        if self.nb.index("current") in (3, 4):
            self.tab_opened()

    def villages(self):
        """Regions descr_strat.txt leaves out: the game makes each a rebel village."""
        if not self.strat or not self.mod:
            return set()
        owners = self.strat.owners()
        tiles = self.mod.city_tiles(self.v_campaign.get())
        return {r for r in self.regions if r not in owners and tiles.get(r)}

    def town_owners(self):
        """{region: owner} with those villages as the rebels'."""
        owners = self.strat.owners() if self.strat else {}
        owners.update({r: "slave" for r in self.villages()})
        return owners

    def fill_towns(self):
        if not self.strat:
            return
        self.tv.delete(*self.tv.get_children())
        q = self.v_search.get().lower().strip()
        want = self.v_owner.get()
        villages = self.villages()
        for region, owner in sorted(self.town_owners().items(), key=lambda x: (x[1] != "slave", x[1], x[0])):
            town = self.regions.get(region, {}).get("settlement", "")
            if want not in ("", "(all)") and owner != want:
                continue
            if q and q not in region.lower() and q not in town.lower():
                continue
            self.tv.insert("", "end", iid=region, text=region,
                           values=(town + (" (village, not in descr_strat)" if region in villages else ""), owner))

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
        if not self.editing():                 # names left from another faction are not in this one's lists
            for role in ("leader", "heir"):
                if self.v[role + "_first"].get() and self.v[role + "_first"].get() not in pool.get("characters", []):
                    self.v[role + "_first"].set("")
                    self.v[role + "_last"].set("")
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
        self.remember()
        for iid in self.tv.selection():
            if iid not in self.chosen:
                self.chosen.append(iid)
        self.refresh_chosen()

    def remove_town(self):
        self.remember()
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
                                 "  [%d units]" % n if r in self.garrisons else
                                 ("  [unchanged]" if self.editing() else "  [automatic]")))
        if keep_units_selection and sel and sel[0] < len(self.chosen):
            self.lb_units.selection_set(sel[0])
        bsel = self.lb_build.curselection()
        self.lb_build.delete(0, "end")
        for r in self.chosen:
            n = len(self.buildings_picked.get(r, []))
            size = self.sizes.get(r, {})
            self.lb_build.insert("end", "%s%s%s" % (r, "  [%d buildings]" % n if r in self.buildings_picked
                                                    else "  [its own]",
                                                    "  " + " ".join(str(v) for v in (size.get("level"),
                                                    size.get("population")) if v is not None) if size else ""))
        if keep_units_selection and bsel and bsel[0] < len(self.chosen):
            self.lb_build.selection_set(bsel[0])
        self.lb.delete(0, "end")
        for r in self.chosen:
            owner = self.town_owners().get(r, "?") if self.strat else "?"
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
            xy = self.char_moves.get(c["cid"], c["xy"]) if c.get("existing") else c.get("xy")
            where = "at %d, %d" % tuple(xy) if xy else "not placed"
            units = "  [%d units%s]" % (len(c["units"]), " + bodyguard" if c.get("named") else "") \
                if c["kind"] in ("army", "fleet") else ""
            tag = ("  - changed" if c.get("changed") else "  - on the map") if c.get("existing") else "  - new"
            self.lb_field.insert("end", "%s %s%s  (%s)%s" % (c["kind"], c["name"], units, where, tag))
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
            self.remember()
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
        units = faction_units(self.mod, self.field_faction(), ships=c["kind"] == "fleet", mercs=True)
        own = [u for u in units if not set(u.ownership) <= {"slave"}]
        if c["kind"] == "fleet" and own and all(u.mercenary for u in own):
            self.garrison_editor.v_merc.set(True)     # many mods mark every ship a mercenary
        units = self._with_types(units, c["units"])

        def changed(types, i=i):
            self.remember()
            self.field[i]["units"] = types
            if self.field[i].get("existing"):
                self.field[i]["changed"] = True
            self.refresh_field(keep=i)
        self.garrison_editor.load(self.mod, self.field_faction(), "%s %s" % (c["kind"], c["name"]), units,
                                  c["units"], changed, held=bool(c.get("named")),
                                  unchanged=bool(c.get("existing")) and not c.get("changed"))
        if not c.get("xy"):
            self.status.set("Pick the units, then 'Place on map'.")

    def remove_field(self):
        self.remember()
        i = self.selected_field()
        if i is None:
            return
        c = self.field[i]
        if c.get("existing"):
            if c.get("named"):
                messagebox.showerror(APP, "%s is a member of the family - the tool does not remove those "
                                          "(the family tree names them)." % c["name"])
                return
            if not messagebox.askyesno(APP, "Remove %s %s from the map?" % (c["kind"], c["name"])):
                return
            self.removed_existing.append({"name": c["name"], "from": c["from"]})
            self.char_moves.pop(c["cid"], None)
        del self.field[i]
        self.refresh_field()

    def place_field(self):
        """Go to the Map; the next click on a good tile places the selected one."""
        i = self.selected_field()
        if i is None:
            messagebox.showerror(APP, "select an army, agent or fleet in the list first")
            return
        c = self.field[i]
        if c.get("existing"):
            messagebox.showinfo(APP, "%s is on the map already: drag it on the Map tab to move it." % c["name"])
            return
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
            self._units_cache = faction_units(self.mod, template, mercs=True)
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
            now = []
            if holder is not None:
                now = [unit_name(l) for l in self.strat.lines[holder.start:holder.end] if tokens(l)[:1] == ["unit"]]
                now = now[1:] if holder.named else now                 # without the bodyguard
            units = self._with_types(units, now)

        def auto():
            try:
                strat = Strat(self.mod.load(self.mod.campaign_file(self.v_campaign.get(), "descr_strat.txt")))
                upkeep = {u.type: u.upkeep for u in read_units(self.mod.load(self.mod.file("edu")))}
                lines, _, _ = balanced_army(strat, template, len(self.chosen), upkeep, [])
                return [unit_name(l) for l in lines[1:]]           # without the bodyguard
            except Exception:
                return []

        def changed(types):
            self.remember()
            if types:
                self.garrisons[region] = types
            elif self.editing() and not getattr(self.garrison_editor, "cleared", False):
                self.garrisons[region] = []            # every unit taken out: the town is left empty
            else:
                self.garrisons.pop(region, None)
                if self.editing():                     # 'Automatic': back to the town as it stands
                    self.after_idle(self.load_garrison)
            self.refresh_chosen(keep_units_selection=True)
        if self.editing() and region not in self.garrisons:
            self.garrison_editor.load(self.mod, template, region, units, now, changed, auto=auto, held=held,
                                      unchanged=True)
            return
        self.garrison_editor.load(self.mod, template, region, units, self.garrisons.get(region, []),
                                  changed, auto=auto, held=held)

    def _with_types(self, units, types):
        """The roster plus any unit these types name that it lacks (another faction's,
        a mercenary): a garrison as it stands must show whole."""
        have = {u.type for u in units}
        missing = set(types) - have
        if not missing:
            return units
        edu = self.mod.file("edu")
        extra = [u for u in read_units(self.mod.load(edu)) if u.type in missing] if edu else []
        return list(units) + extra

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
                                    if r in self.chosen},
                      "sizes": {r: dict(v) for r, v in self.sizes.items() if r in self.chosen}},
            "places": self._places(),
            "relations": self._relations(),
            "regions": self._regions_opts(),
        }
        return v["template"], v["name"].lower(), opts

    def gather_edit(self):
        v = {k: x.get().strip() for k, x in self.v.items()}
        if not v["template"]:
            raise ValueError("pick the faction to edit")
        had = list((self.editing_now or {}).get("regions", []))
        if had and not self.chosen:
            raise ValueError("the faction would be left without towns - keep or add at least one (Faction tab)")

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
            "characters": [dict(c) for c in self.field if not c.get("existing")],
            "army_units": [{"name": c["name"], "from": c["from"], "units": list(c["units"])}
                           for c in self.field if c.get("existing") and c.get("changed")],
            "remove": list(self.removed_existing),
            "garrisons": dict(self.garrisons),
            "places": self._places(),
            "relations": self._relations(),
            "regions": self._regions_opts(),
            "sizes": {r: dict(v) for r, v in self.sizes.items() if r in self.chosen},
            "buildings": {r: [list(x) for x in b] for r, b in self.buildings_picked.items()}}

    def _places(self):
        return [{"what": w, "region": r, "to": xy} for (w, r), xy in self.place_moves.items()]

    def map_only(self):
        """New faction mode with no faction named yet: the buttons write the map's changes alone."""
        return not self.editing() and not (self.v["template"].get().strip() and self.v["name"].get().strip())

    def update_actions(self):
        if self.editing():
            p, a = "Preview changes", "Apply changes"
        elif self.map_only():
            p, a = "Preview map changes", "Apply map changes"
        else:
            p, a = "Preview changes", "Create faction"
        self.b_preview.configure(text=p)
        self.b_create.configure(text=a)

    def make_plan(self):
        if self.map_only():
            places, regions = self._places(), self._regions_opts()
            if not places and not regions:
                raise ValueError("nothing to write: move a town or port, or paint regions on the Map "
                                 "(or name a new faction on the Faction tab)")
            mod = ModData(self.mod.data)
            plan = Plan(mod, "map", "map", {})
            from .mapedit import apply_places
            from .regionedit import apply_regions
            if places:
                apply_places(plan, self.v_campaign.get(), places)
            if regions:
                apply_regions(plan, self.v_campaign.get(), regions["painted"], regions["new"])
            return plan
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
        log.write("Preview\n" + plan.report())
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
        log.write("Written (backup %s)\n%s" % (bdir, plan.report()))
        self.show_text("Done", plan.report() + "\n\nBackup: %s\nStart a NEW campaign to see the %s." % (
            bdir, "changes" if self.editing() or self.map_only() else "faction"))
        self.load()

    def check(self):
        """Read every file the tool uses and report; the deep check also rehearses the
        tool's work for every faction in memory (minutes on a big mod). Nothing is written."""
        if not self.mod:
            messagebox.showerror(APP, "load a mod first")
            return
        deep = messagebox.askyesnocancel(APP, "Check the mod (nothing is written).\n\n"
                                              "Also rehearse an edit and a new faction for every faction?\n"
                                              "Yes = deep check (a few minutes, longer on a big mod)\n"
                                              "No = quick check (seconds)")
        if deep is None:
            return
        from .check import check_mod
        result, data, campaign = {}, self.mod.data, self.v_campaign.get()

        def work():
            try:
                result["text"] = check_mod(ModData(data), campaign, deep=deep,
                                           progress=lambda m: result.__setitem__("step", m))
            except Exception as e:
                result["text"] = "The check stopped: %s\n\n%s" % (e, traceback.format_exc())
        th = threading.Thread(target=work, daemon=True)
        th.start()

        def wait():
            if th.is_alive():
                self.status.set("Checking the mod... %s" % result.get("step", ""))
                self.after(300, wait)
                return
            self.status.set("Check finished.")
            log.write("Check mod\n" + result["text"])
            self.show_text("Check mod", result["text"])
        wait()

    def _log_status(self):
        """Status lines go to the log, but one of a kind in a row (painting sends many)."""
        text = self.status.get()
        shape = re.sub(r"\d+", "#", text)
        if text and shape != getattr(self, "_last_status_shape", None):
            log.write(text)
        self._last_status_shape = shape

    def show_log(self):
        """The tool's log - send faction_tool.log along with the game's system.log.txt."""
        self.show_text("Log - %s" % (log.path() or "no log file"), log.tail() or "(empty)")

    def report_callback_exception(self, exc, val, tb):
        """A crash inside the window: logged with its traceback and shown, never silent."""
        text = "".join(traceback.format_exception(exc, val, tb))
        log.write("ERROR (unexpected)\n" + text)
        _showerror(APP, "Something went wrong: %s\n\nThe details are in the log (Log button)." % val)

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
            log.write("Restored %s: %d file(s) back, %d copied item(s) removed"
                      % (b, len(m["modified"]), len(m["created"])))
            messagebox.showinfo(APP, "Restored %d file(s), removed %d copied item(s)." % (len(m["modified"]), len(m["created"])))
            w.destroy()
            self.load()
        ttk.Button(w, text="Restore", command=go).pack(pady=(0, 6))


def main():
    log.write("Start %s" % APP)
    App().mainloop()
