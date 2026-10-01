"""The window: pick the mod, fill in the faction, preview, create, restore."""

import copy
import datetime
import os
import re
import sys
import threading
import traceback
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import log, settings
from .build import build, template_display
from .buildings import (POP_MIN, SETTLEMENT_LEVELS, BuildingPictures, core_need, core_settlement, population_of, rank,
                        castles_allowed, convert, kind_problem, read_buildings, settlement_info, settlement_kind)
from .mapdata import CampaignMap, faction_colours
from .moddata import ModData
from .mapedit import orig as place_orig, place_problem, port_fleets, sea_spot
from .newmod import create_mod, game_of, game_root_of, is_game, is_medieval2, list_mods, mod_target
from .edit import edit as edit_faction, read_faction
from .gui_buildings import NONE, BuildingsEditor
from .gui_diplomacy import DiplomacyEditor, colour as dip_colour
from .gui_garrison import GarrisonEditor, Pictures
from .gui_map import MapView
from .plan import Plan, backup_label, backups, restore_to
from .scan import IGNORE_HELP, ignore_path, make_manifest, scan as scan_mod
from .start import balanced_army, unit_name
from .strat import FEMALE_KINDS, Strat, first_names
from .textio import tokens
from .units import faction_units, read_units

VERSION = "0.23.0"
KOFI = "https://ko-fi.com/pfadfinder"
APP = "RTW & M2TW Campaign Editor"

HELP = """RTW & M2TW Campaign Editor - how to use it

Nothing is written until you press Apply, and every Apply makes a backup first:
Tools > Restore a backup puts your files back exactly as they were. So try things freely.

I WANT TO...  (pick the work in the row at the top, then use the tabs)
  make a new faction ............ New faction: pick a faction to copy (the template),
                                  type the new one's name on the Faction tab
  change a faction that exists .. Edit faction: pick the faction, change what you want
                                  (in New faction the faction you pick is only the template -
                                  nothing is written for it; use Edit faction to change it)
  give / take towns, armies ..... Edit faction: Map (a click on a town), Units & armies (garrisons,
                                  armies, agents, fleets), Map (click towns, drag characters)
  change the campaign map ....... Map tab (move towns and ports, paint regions, resources)
                                  and the Terrain editor (ground, rivers, climates, heights)
  change a unit or a building ... Unit editor / Building editor
  make a new unit or building ... Unit / Building editor: New unit (New building) step by step...
  change a unit's look .......... Unit editor: Battle model - View in 3D..., Replace model...
  hear a unit, give it a voice .. Unit editor: Voice in battle - Play, Put in my own...
  edit characters and families .. Character editor (or the Faction tab in Edit faction)
  put in a mod made by others ... Tools > Check and install a pack...
  change the campaign's rules ... Tools > Campaign rules... (ages, agents, towns, diplomacy, unit sizes)
  add a religion ................ Tools > New religion... (Medieval II; Rome has no religions)
  add Sack Settlement ........... Add-ons (Rome + REX): who may sack, reward, what stays standing
  rename a region or its town ... Settlements tab: Rename... (names players see), Rename in the
                                  files... (the system names, everywhere)
  make a copy of the mod to work on  New mod folder... (the base mod stays untouched)

START
  1. Close the game. Browse... to the mod's data folder (for example ...\\HLR\\data) and press
     Load. The Mod list at the top remembers every mod of that game folder for next time.
  2. Pick the campaign (usually imperial_campaign).
  3. Pick the work at the top, make the changes, then:
  4. Preview changes (Ctrl+P) shows every file and line that would change. Nothing is written.
  5. Apply changes (Ctrl+S) writes it, with a backup first.
  6. Start a NEW campaign in the game - old saves do not see the changes.

THE TABS
  Faction      names, texts, colours, AI, money, playable, religion (Medieval II), capital, leader,
               heir; beside them the faction's family tree and characters (Edit). Its towns are
               given and taken with a click on the Map.
               Name list...: a faction's own men's names, surnames and women's names.
  Units & armies
               each town's garrison (click a card to add, click the garrison to take out);
               + Army / + Agent / + Fleet, then Place on map; in Edit also everything the
               faction already has on the map (double click: show it on the map).
  Buildings    what stands in each town, its level and population (they follow each other);
               Medieval II: a town can be made a castle or a city.
  Map          left drag moves the map, the wheel zooms, a click on a town takes or gives it;
               right drag (or Ctrl + left drag) moves characters, towns and ports;
               Find: type a town, army, unit, fort or resource and jump to it;
               Layers: what is shown; Legend: what every sign means.
               Edit regions: paint borders, New region, Edit region..., Religions... and
               New religion... (Medieval II; also in Tools). Resources: place, move, delete.
               Characters stand on any land but sea, mountains, dense forest and rivers;
               dropped on a bad tile they go to the nearest good one.
  Diplomacy    how the faction and every other one feel about each other at the start.
  Art          every picture of the faction with where the game shows it: Replace... takes any
               picture and makes it the right size and format; Back to the original.
  Roster       (Edit) every unit and building level and whether the faction has it:
               Give / Take away - everything tied to it (recruit lines, cards...) follows.

UNIT EDITOR / BUILDING EDITOR
  Pick a unit (a building chain) on the left; every line is a field - change it, it turns
  yellow. Import... puts a picture (PNG, JPG, TGA) in the right size wherever the game reads it.
  New unit / New building step by step...: a new one starts as a copy of one that works in the
    game, then steps with Back / Next - names and texts players read, who owns it (who may
    build it), its main numbers, pictures of your own - and last everything it will change.
  Battle model (units): each soldier / officer model, how it sits (foot, horse, camel...),
    View in 3D... (both games: turn it with the mouse, the wheel zooms, pick a faction's
    texture; Medieval II: "Another man" shows the next mix of heads and bodies) and Replace model...
    (from this mod or another mod of the same game - it comes with its files).
  Voice in battle (units): what the unit says, for each accent (Medieval II) or culture (Rome)
    of its owners - Play its name call ("Khan's Guard!") and any of its orders; Put in my own...
    gives it your .wav files as its name call (a new unit gets one of its own). The voice class
    is the voice_type line. Then start the game: it builds data/sounds/events.dat again.
  Add line... / x: add or remove a line. Renames follow everywhere they are used.
  Export pack... / Import pack...: take units with everything they need into another mod.

CHARACTER EDITOR
  Any faction's characters on the map and family off the map, with the family tree and the
  portraits the game shows: names, ages, traits, ancillaries; Give a wife, Add a child.
  Portrait library...: every portrait of a culture; Add portraits... puts new ones in.

TERRAIN EDITOR
  Paint the campaign map tile by tile: Ground (fertile land, forest, hills, mountains, swamp,
  seas), Rivers, fords, cliffs, Climates, and Heights (a brush like a spray can: raise, lower,
  smooth, level). Left drag paints, right click picks a tile's own, right drag moves the map.
  Nothing the game refuses is put under a town, port or army. The game rebuilds its map on
  the next start.

TOOLS
  Check mod: reads the whole mod and says in plain words what the game would stumble on.
  Check mod with a faction picked also lists every place the faction is named (game, REX and mod files told apart).
  Check and install a pack: a "copy these files over data" mod checked file by file first -
    what is new, what it replaces and what that would lose (REX's own files, pictures of
    another size); pick for each file, then install with a backup.
  Campaign rules: every value of the campaign's settings files (Medieval II descr_campaign_db,
    town growth / order / income, diplomacy, recruitment; Rome + REX the people each town
    level needs; REX / M2EX the Unit size choices) with a plain explanation and the game's own
    value beside a changed one. Change, Preview, Write it in.
  Restore a backup: undo any Apply (and every later one) exactly.

ADD-ONS
  Ready-made scripts that add something new. Pick the settings, Preview, Put it in (a backup
  first; Take it out removes it). Sack Settlement (Rome + REX): a 4th choice when a town is
  taken - it is torn down to its walls and roads, you get a reward, the rebels get the ruins.
  Who may sack: only the player, everyone, hordes (factions without a town), picked factions.
  Report a bug / Suggest: a problem (with the logs, your names cut out - Show what is sent) or an idea, a few
    words and screenshots go to the author in one click, no account needed. Log / Save logs (zip): the same zip to send yourself.

KEYS
  Ctrl+Z undo, Ctrl+Y redo    Ctrl+P preview    Ctrl+S apply    F5 load again    F1 this help
  Ctrl+1 .. Ctrl+5 the tabs    Map: wheel zooms, left drag moves, right drag moves a marker

THE GAMES
  Rome: Total War, Barbarian Invasion, Alexander - plain or with REX.
  Medieval II and Kingdoms - plain or with M2EX (a plain game from Steam is unpacked by the
  tool on Load, with your yes). Limits of the original games apply only without REX / M2EX.

SUPPORT
  The tool is free. If it helps you, a coffee keeps new features coming:
  https://ko-fi.com/pfadfinder  (the Support on Ko-fi button)
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


def colour_look(rgb):
    """A colour button's background and a text colour that reads on it."""
    rgb = tuple(int(v) for v in rgb)
    light = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] > 140
    return {"bg": "#%02x%02x%02x" % rgb, "fg": "#000000" if light else "#ffffff",
            "activebackground": "#%02x%02x%02x" % rgb, "activeforeground": "#000000" if light else "#ffffff"}


class FieldTable(ttk.Frame):
    """The armies, agents and fleets as a table (kind, name, units, tile, state),
    with the few Listbox calls the window uses. A row keeps its place in the
    window's list (its iid), so the Show filter and sorting by a column (click
    its heading) never mix them up."""
    COLS = (("kind", "Kind", 70), ("name", "Name", 130), ("units", "Units", 80), ("tile", "Tile", 70),
            ("state", "", 60))
    SHOW = ("all", "armies", "fleets", "agents")

    def __init__(self, master):
        super().__init__(master)
        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x", pady=(0, 2))
        ttk.Label(bar, text="Show").pack(side="left")
        self.v_show = tk.StringVar(value="all")
        cb = ttk.Combobox(bar, textvariable=self.v_show, values=self.SHOW, state="readonly", width=10)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._draw())
        ttk.Label(bar, text="click a heading to sort", foreground="#666").pack(side="left", padx=6)
        self.tv = ttk.Treeview(self, columns=[c[0] for c in self.COLS], show="headings", height=10,
                               selectmode="browse")
        for n, (key, head, width) in enumerate(self.COLS):
            self.tv.heading(key, text=head, command=lambda n=n: self._sort_by(n))
            self.tv.column(key, width=width, stretch=key == "name")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tv.tag_configure("new", foreground="#0050c0")
        self.tv.tag_configure("changed", foreground="#a05000")
        self.rows, self.sort = [], None          # [values], (column, reverse)

    def _shown(self, values):
        want = self.v_show.get()
        kind = values[0]
        return (want == "all" or want == "armies" and kind == "army" or want == "fleets" and kind == "fleet"
                or want == "agents" and kind not in ("army", "fleet"))

    def _draw(self):
        sel = self.curselection()
        self.tv.delete(*self.tv.get_children())
        order = list(range(len(self.rows)))
        if self.sort:
            col, rev = self.sort
            order.sort(key=lambda i: str(self.rows[i][col]).lower(), reverse=rev)
        for i in order:
            if self._shown(self.rows[i]):
                self.tv.insert("", "end", iid=str(i), values=self.rows[i], tags=(self.rows[i][-1],))
        if sel:
            self.selection_set(sel[0])

    def _sort_by(self, col):
        self.sort = (col, not self.sort[1]) if self.sort and self.sort[0] == col else (col, False)
        self._draw()

    def delete(self, *a):
        self.rows = []
        self.tv.delete(*self.tv.get_children())

    def insert(self, _where, values):
        self.rows.append(values)
        if self._shown(values):
            if self.sort:
                self._draw()
            else:
                self.tv.insert("", "end", iid=str(len(self.rows) - 1), values=values, tags=(values[-1],))

    def curselection(self):
        return tuple(int(i) for i in self.tv.selection())

    def selection_set(self, i):
        if self.tv.exists(str(i)):
            self.tv.selection_set(str(i))
            self.tv.see(str(i))

    def selection_clear(self, *a):
        if self.tv.selection():
            self.tv.selection_remove(*self.tv.selection())

    def bind(self, seq, fn, add=None):
        self.tv.bind("<<TreeviewSelect>>" if seq == "<<ListboxSelect>>" else seq, fn, add)


AS_LAND = "(as the land it is cut from)"


def assets_dir():
    """The tool's own pictures (assets/ in the source, 'assets' inside the exe)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("%s %s" % (APP, VERSION))
        self._set_icon()
        self.geometry("1200x800")
        self.minsize(1024, 640)
        self.mod = None
        self.strat = None
        self.regions = {}
        self.chosen = []
        self.garrisons = {}             # region -> [unit type] picked by hand
        self.field = []                 # [{kind, name, age, units, xy}] armies/agents/fleets to place
        self._limit_raise = None        # the mod whose max_factions the user agreed to raise
        self.removed_existing = []      # Edit: [{name, from}] characters taken off the map
        self.place_moves = {}           # {('city' | 'port', region): (x, y)} towns and ports moved on the map
        self.dip_set = {}               # {(kind, from, to): value or None} picked on the Diplomacy tab ('me' = the faction)
        self.region_paint = {}          # {(x, y): region} tiles painted to another region (Regions mode)
        self.region_edits = {}          # {region: {creator, rebels, resources, triumph, farming}} of regions there are
        self.new_regions = []           # [{name, settlement, creator, rebels, resources, colour, city, port, owner, level}]
        self.region_religions = {}      # {region: {religion: percent}} set by hand (Medieval II)
        self.new_religions = []         # Medieval II: new religions waiting for Apply (religions.py specs)
        self.culture_names = {}         # {settlement: {culture or '*': name}} (REX renames the town for its owner)
        self.name_list = {}             # {faction or '(new)': {pool: [names]}} a name list of its own (Name list...)
        # resources on the map: moved {index: (x, y)}, removed [index], added [{type, xy}], region tags {region: text}
        self.res_moves, self.res_removed, self.res_added, self.region_tags = {}, [], [], {}
        # forts and watchtowers the same way: moved {line: (x, y)}, removed [line], added [{kind, xy}] (forts.py)
        self.fort_moves, self.fort_removed, self.fort_added = {}, [], []
        self._res_placing, self._res_sel = None, None
        self.art_replace, self.sel_map = {}, {}      # Art tab: {path under data: picture}, {on, colour}
        self.figures = {}                           # Art tab: {character type: [strat model per level]}
        self.family_set = {}            # Family tab: {'people': {key: changes}, 'new': [...], 'remove': [...], 'tree'}
        self.roster_set = {}            # Roster tab: {'unit:<type>' | 'building:<chain>:<level>': give?}
        self._region_point = None       # ('city' | 'port', region) waiting for a click
        self._town_auto = False         # a town from the legend: its land is painted around the click
        self.undo_stack, self.redo_stack = [], []   # snapshots of what the window keeps (Ctrl+Z / Ctrl+Y)
        self.sizes = {}                 # {region: {'level', 'population'}} set by hand on the Buildings tab
        self.kinds = {}                 # Medieval II: {region: 'city' | 'castle'} changed on the Buildings tab
        self._units_for, self._units_cache = None, []
        self.buildings_picked = {}      # region -> [(chain, level)] set by hand
        self._edb_for, self._edb, self._bpics = None, [], None
        self.pictures = Pictures()
        self.colours = {"primary": None, "secondary": None}
        self.editing_now = None
        self.char_moves = {}            # "faction:index" -> (x, y) dragged on the map (Edit)
        self._build()

    def _set_icon(self):
        """The window's (and every dialog's) icon; the exe carries the same picture for Explorer."""
        try:
            self._icons = [tk.PhotoImage(file=os.path.join(assets_dir(), "icon_%d.png" % n))
                           for n in (256, 48, 32, 16)]
            self.iconphoto(True, *self._icons)
        except (tk.TclError, OSError):
            pass                        # no icon is no reason to stop

    # ------------------------------------------------------------------ layout

    def _build(self):
        from . import theme
        theme.apply(self)                          # light or dark, as last chosen
        pad = {"padx": 6, "pady": 3}
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Mod").pack(side="left")
        # the mods of the game folder last used; picking one loads it
        self.v_modpick = tk.StringVar()
        self.cb_mods = ttk.Combobox(top, textvariable=self.v_modpick, state="readonly", width=18)
        self.cb_mods.pack(side="left", padx=(4, 8))
        self.cb_mods.bind("<<ComboboxSelected>>", lambda e: self.mod_picked())
        self._mods = []
        ttk.Label(top, text="data folder").pack(side="left")
        self.v_path = tk.StringVar()
        ttk.Entry(top, textvariable=self.v_path, width=8).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Browse...", command=self.browse).pack(side="left")
        ttk.Button(top, text="Load", command=self.load).pack(side="left", padx=4)
        ttk.Button(top, text="New mod folder...", command=self.new_mod).pack(side="left", padx=4)
        ttk.Label(top, text="Campaign").pack(side="left", padx=(12, 2))
        self.v_campaign = tk.StringVar()
        self.cb_campaign = ttk.Combobox(top, textvariable=self.v_campaign, state="readonly", width=20)
        self.cb_campaign.pack(side="left")
        self.cb_campaign.bind("<<ComboboxSelected>>", lambda e: self.campaign_picked())
        # a narrow window shortens the data folder field, never the campaign
        from .gui_util import first
        for w in top.pack_slaves()[-2:]:
            w.pack_configure(side="right")
        first(top.pack_slaves()[-2], self.cb_campaign)
        self.v_mode = tk.StringVar(value="new")
        # what the window works on: a new faction, an existing one, the units, the buildings
        # the work buttons scroll left / right when the window is narrower than they are (more come)
        from .gui_util import HScroll, tip
        work = ttk.Frame(self)
        work.pack(fill="x", padx=6, pady=(4, 0))
        self.b_theme = ttk.Button(work, text="", command=self.toggle_theme)
        self.b_theme.pack(side="right", padx=(6, 0))
        self.work_row = HScroll(work)
        self.work_row.pack(side="left", fill="x", expand=True)
        self.v_work = tk.StringVar(value="new")
        self.work_buttons = {}
        for val, text in self.WORK_TITLES.items():
            b = tk.Radiobutton(self.work_row.inner, text=text, value=val, variable=self.v_work, indicatoron=0,
                               command=self.work_changed, padx=16, pady=5, font=("", 10, "bold"),
                               selectcolor="#cfe3ff", relief="raised", offrelief="groove", cursor="hand2")
            b.pack(side="left", padx=(0, 4))
            self.work_buttons[val] = b
            tip(b, self.WORK_HINTS.get(val, ""))         # what each work is: shown on hover, takes no room
        tip(self.b_theme, "light or dark window")
        self.work_row.pack_configure(expand=False)
        # beside them only a warning that needs to be seen (New faction with a faction picked); cut first when narrow
        self.lbl_work = ttk.Label(work, text="", foreground="#555")
        self.lbl_work.pack(side="left", padx=10)
        tip(self.lbl_work, lambda: self.lbl_work.cget("text"))
        self._theme_label()
        self.editors = {}

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, **pad)
        body = ttk.Frame(self.nb, padding=4)
        self.nb.add(body, text="  Faction  ")
        # the Faction tab is the faction itself: the form, and its family tree beside it. Its towns are given and
        # taken on the Map (a click on a town), their buildings on Buildings, garrisons on Units & armies - the
        # old town list (below) is kept only as the window's own record of the picked towns, never shown
        # (the user, 2026-09-30: "a third way to add towns makes no sense")
        # the form, or (a click on the Family tree button) the family tree in its place - folded away by default so
        # the form has the room (the user, 2026-10-01); the form scrolls in a low window
        from .gui_util import ScrollFrame
        fbar = ttk.Frame(body)
        fbar.pack(fill="x", pady=(0, 4))
        self.b_family = ttk.Button(fbar, command=self.toggle_family)
        self.b_family.pack(side="left")
        self.l_family = ttk.Label(fbar, foreground="#666")
        self.l_family.pack(side="left", padx=8)
        lsf = self._form_view = ScrollFrame(body)
        lsf.pack(fill="both", expand=True)
        left = lsf.inner
        self._family_host = ttk.Frame(body)               # packed only while the family tree is open
        self._family_open = False
        right = ttk.Frame(self)                   # never packed: the picked towns' list lives on, unseen

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
        from .gui_util import FactionBox
        self.cb_template = FactionBox(lf, self.v["template"], state="readonly", width=28)
        self.cb_template.bind("<<ComboboxSelected>>", lambda e: self.template_changed())
        field("Template (copied)", self.cb_template)
        self.lbl_template = lf.grid_slaves(row=row - 1, column=0)[0]
        self.e_name = ttk.Entry(lf, textvariable=self.v["name"])
        field("Internal name", self.e_name)
        field("Name (full)", ttk.Entry(lf, textvariable=self.v["display_name"]))
        field("Name (short)", ttk.Entry(lf, textvariable=self.v["short_name"]))
        # Rome only: Medieval II's texts have no short name ({ST_...}) nor the faction icon's tooltip
        # ({..._DESCR}) - the rows are hidden there (_game_rows)
        self.rome_rows = [lf.grid_slaves(row=row - 1, column=c)[0] for c in (0, 1)]
        field("Adjective", ttk.Entry(lf, textvariable=self.v["adjective"]))
        # Medieval II's faction screen texts, shown only when the faction has them
        self.extra_rows = {}
        for k, label in (("strength", "Strengths\n(faction screen)"), ("weakness", "Weaknesses\n(faction screen)"),
                         ("unit_text", "Famous unit\n(faction screen)")):
            self.v[k] = tk.StringVar()
            field(label, ttk.Entry(lf, textvariable=self.v[k]))
            self.extra_rows[k] = [lf.grid_slaves(row=row - 1, column=c)[0] for c in (0, 1)]
            for w in self.extra_rows[k]:
                w.grid_remove()
        self.cb_ai = ttk.Combobox(lf, textvariable=self.v["ai"], state="readonly", values=AI_CHOICES)
        field("AI personality", self.cb_ai)
        # Medieval II: the faction's religion (descr_sm_factions.txt); Rome has none - the row is hidden there
        self.v["religion"] = tk.StringVar()
        self.cb_religion = ttk.Combobox(lf, textvariable=self.v["religion"], state="readonly")
        field("Religion", self.cb_religion)
        self.m2_rows = [lf.grid_slaves(row=row - 1, column=c)[0] for c in (0, 1)]
        field("Starting denari", ttk.Entry(lf, textvariable=self.v["denari"]))
        # its towns: a click on a town on the Map gives or takes it; the capital is one of them
        self.cb_capital = ttk.Combobox(lf, textvariable=self.v["capital"], state="readonly")
        self.cb_capital.bind("<<ComboboxSelected>>", lambda e: self.refresh_chosen())
        field("Capital", self.cb_capital)
        self.lbl_towns = ttk.Label(lf, foreground="#666", text="", wraplength=330, justify="left")
        self.lbl_towns.grid(row=row, column=1, sticky="w", padx=4)
        row += 1
        # Edit: where the towns taken from it go
        self.v_give = tk.StringVar(value="slave")
        self.cb_give = FactionBox(lf, self.v_give, state="readonly")
        field("Removed towns go to", self.cb_give)
        self.give_row = [lf.grid_slaves(row=row - 1, column=c)[0] for c in (0, 1)]
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
        self.chk_playable = ttk.Checkbutton(lf, text="Playable", variable=self.v_playable)
        self.chk_playable.grid(row=row, column=0, sticky="w", padx=4)
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
        self.rome_rows += [lf.grid_slaves(row=row, column=c)[0] for c in (0, 1)]
        row += 1
        ttk.Label(lf, text="Full description\n(campaign screen)").grid(row=row, column=0, sticky="nw", padx=4)
        self.t_long = tk.Text(lf, width=34, height=7, wrap="word")
        self.t_long.grid(row=row, column=1, sticky="we", padx=4, pady=2)
        row += 1
        lf.columnconfigure(1, weight=1)

        # --- leaders
        lf2 = self.lf2 = ttk.LabelFrame(left, text="Leader and heir (names come from the faction's name list)")
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
        nl = ttk.Frame(lf2)
        nl.grid(row=3, column=0, columnspan=4, sticky="w", padx=4, pady=(2, 4))
        ttk.Button(nl, text="Name list...", command=self.name_list_dialog).pack(side="left")
        self.l_name_list = ttk.Label(nl, foreground="#666", text="its own men's names, surnames and women's names")
        self.l_name_list.pack(side="left", padx=6)

        # --- victory: what the player must do to win (descr_win_conditions.txt)
        from .gui_wincond import VictoryBox
        self.victory = VictoryBox(left, on_change=self._victory_changed, before=self.remember)
        self.victory.pack(fill="x", pady=(8, 0))

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
        self.cb_owner = FactionBox(flt, self.v_owner, ["(all)"], state="readonly", width=18)
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
        mid = ttk.Frame(left_pane)
        mid.pack(side="right", padx=6)
        self.b_add = ttk.Button(mid, text="Add >", command=self.add_town)
        self.b_add.pack(pady=2)
        self.b_remove = ttk.Button(mid, text="< Remove", command=self.remove_town)
        self.b_remove.pack(pady=2)
        ttk.Button(mid, text="Garrison...", command=lambda: self.show_units(self.selected_town())).pack(pady=(14, 2))
        ttk.Button(mid, text="Rename...", command=self.rename_town).pack(pady=2)
        ttk.Button(mid, text="Edit region...", command=lambda: self.new_region_dialog(
            edit=(self.tv.selection() or [""])[0] or self.selected_town())).pack(pady=2)
        ttk.Button(mid, text="Names by culture...", command=lambda: self.culture_names_dialog(
            (self.tv.selection() or [""])[0] or self.selected_town())).pack(pady=2)
        ttk.Button(mid, text="All towns' names...", command=self.culture_names_table).pack(pady=2)
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
        # a double click renames (the user: it moving the town to Chosen was not wanted); Add > / Enter adds
        self.tv.bind("<Double-1>", lambda e: self.rename_town() if self.tv.identify_row(e.y) else None)
        self.tv.bind("<Return>", lambda e: self.add_town())
        # right click: the region's own menu (rename it, edit it, add it)
        town_menu = tk.Menu(self.tv, tearoff=False)
        town_menu.add_command(label="Rename (the names players see)...", command=self.rename_town)
        town_menu.add_command(label="Edit region...", command=lambda: self.new_region_dialog(
            edit=(self.tv.selection() or [""])[0]))
        town_menu.add_command(label="Add to Chosen", command=self.add_town)

        def town_menu_at(e):
            row = self.tv.identify_row(e.y)
            if row:
                self.tv.selection_set(row)
                town_menu.tk_popup(e.x_root, e.y_root)
        self.tv.bind("<Button-3>", town_menu_at)

        self._build_units_tab()
        self._build_buildings_tab()
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Map  ")
        from .gui_util import flow
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
        ttk.Button(rb, text="Edit region...", command=lambda: self.new_region_dialog(
            edit=self.v_paint.get().replace("  (new)", "").strip())).pack(side="left", padx=2)
        ttk.Button(rb, text="Rename...", command=self._rename_painted).pack(side="left", padx=2)
        ttk.Button(rb, text="Rename in the files...", command=self._rename_painted_files).pack(side="left", padx=2)
        ttk.Button(rb, text="Place its town", command=lambda: self.region_point("city")).pack(side="left", padx=2)
        ttk.Button(rb, text="Place its port", command=lambda: self.region_point("port")).pack(side="left", padx=2)
        ttk.Button(rb, text="Delete this new region", command=self.drop_region).pack(side="left", padx=2)
        ttk.Button(rb, text="Religions...", command=self.religions_dialog).pack(side="left", padx=2)
        ttk.Button(rb, text="New religion...", command=self.new_religion_dialog).pack(side="left", padx=2)
        ttk.Button(rb, text="Names by culture...", command=lambda: self.culture_names_dialog(
            self.v_paint.get().replace("  (new)", "").strip())).pack(side="left", padx=2)
        ttk.Label(rb, text="left drag paints, right click picks a region, right drag moves the map",
                  foreground="#666").pack(side="left", padx=10)
        flow(rb)
        # Edit resources and Edit forts: a bar each (type, Place new, Delete picked) with its how-to under it
        self.res_bar = ttk.Frame(tab, padding=(0, 0, 0, 4))
        xb = ttk.Frame(self.res_bar)
        xb.pack(fill="x")
        ttk.Label(xb, text="Resource", font=("", 9, "bold")).pack(side="left")
        self.v_res_type = tk.StringVar()
        self.cb_res_type = ttk.Combobox(xb, textvariable=self.v_res_type, width=16, state="readonly")
        self.cb_res_type.pack(side="left", padx=4)
        ttk.Button(xb, text="Place new", command=lambda: self.res_place_new(self.v_res_type.get())).pack(
            side="left", padx=2)
        ttk.Button(xb, text="Delete picked", command=self.res_delete).pack(side="left", padx=2)
        ttk.Button(xb, text="Region tags (hidden resources)...", command=self.region_tags_dialog).pack(side="left", padx=(12, 2))
        flow(xb)
        self._how(self.res_bar, "New: pick the resource above, press Place new, then click a land tile on the map.  "
                                "Move: drag a resource with the right mouse button.  Remove: click it, then Delete "
                                "picked.  A region's resources are the ones on its land.")
        self.fort_bar = ttk.Frame(tab, padding=(0, 0, 0, 4))
        fb = ttk.Frame(self.fort_bar)
        fb.pack(fill="x")
        ttk.Label(fb, text="Fort / watchtower", font=("", 9, "bold")).pack(side="left")
        from .forts import KINDS as FORT_KINDS
        self.v_fort_type = tk.StringVar(value=FORT_KINDS[0])
        ttk.Combobox(fb, textvariable=self.v_fort_type, width=12, state="readonly", values=FORT_KINDS).pack(
            side="left", padx=4)
        ttk.Button(fb, text="Place new", command=lambda: self.res_place_new(self.v_fort_type.get())).pack(
            side="left", padx=2)
        ttk.Button(fb, text="Delete picked", command=self.res_delete).pack(side="left", padx=2)
        flow(fb)
        self._how(self.fort_bar, "New: pick fort or watchtower, press Place new, then click a land tile on the map "
                                 "(it copies the line of the nearest one the campaign has).  Move: drag one with "
                                 "the right mouse button.  Remove: click it, then Delete picked.")
        self.lbl_fort_new = ttk.Label(self.fort_bar, text="", foreground="#b05a00", justify="left")
        self.lbl_fort_new.pack(fill="x", anchor="w")
        self.fort_bar.bind("<Configure>", lambda e: self.lbl_fort_new.configure(wraplength=max(200, e.width - 8)),
                           add="+")
        self.map_view = MapView(tab, on_layers=lambda: self.show_map())
        self.map_view.on_tool = self.map_tool
        self.v_borders = self.map_view.v_borders
        self.map_view.pack(fill="both", expand=True)
        self.map_view.on_stroke = self.remember
        self._cmap, self._cmap_for = None, None
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Diplomacy  ")
        self.dip_editor = DiplomacyEditor(tab)
        self.dip_editor.pack(fill="both", expand=True)
        from .gui_art import ArtEditor
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  Art  ")
        self.art_editor = ArtEditor(tab, self)
        self.art_editor.pack(fill="both", expand=True)
        from .gui_roster import RosterEditor
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  Roster  ")
        self.roster_editor = RosterEditor(tab, self)
        self.roster_editor.pack(fill="both", expand=True)
        from .gui_family import FamilyEditor
        self.family_editor = FamilyEditor(self._family_host, self)
        self.family_editor.pack(fill="both", expand=True)
        from .gui_settlements import SettlementsPanel
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="  Settlements  ")
        self.settlements = SettlementsPanel(tab, self)
        self.settlements.pack(fill="both", expand=True)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.tab_opened())
        self._keys()

        # --- actions
        # the status line and the buttons are packed at the bottom before the tabs: a tab taller than
        # the window then shrinks, the Apply buttons never go off the window's edge
        self.status_line = ttk.Label(self, anchor="w")
        self.status_line.pack(side="bottom", fill="x", padx=6, pady=(0, 6), before=self.nb)
        bar = self.bottom_bar = ttk.Frame(self)
        bar.pack(side="bottom", fill="x", before=self.nb, **pad)
        self.b_preview = ttk.Button(bar, text="Preview changes", command=self.preview)
        self.b_preview.pack(side="left")
        self.b_create = ttk.Button(bar, text="Create faction", command=self.create)
        self.b_create.pack(side="left", padx=6)
        ttk.Button(bar, text="Undo", width=6, command=self.undo).pack(side="left", padx=(12, 0))
        ttk.Button(bar, text="Redo", width=6, command=self.redo).pack(side="left", padx=4)
        tk.Button(bar, text="\u2615  Support on Ko-fi", command=self.support, bg="#ff5e5b", fg="white",
                  activebackground="#e14b48", activeforeground="white", relief="flat", cursor="hand2",
                  font=("", 9, "bold"), padx=10).pack(side="right", padx=(8, 0))
        ttk.Button(bar, text="Help", command=self.show_help).pack(side="right", padx=(6, 0))
        ttk.Button(bar, text="Report a bug / Suggest", command=self.send_report).pack(side="right", padx=(6, 0))
        tools = ttk.Menubutton(bar, text="Tools")
        menu = tk.Menu(tools, tearoff=False)
        menu.add_command(label="Check mod", command=self.check)
        menu.add_command(label="Settlement names by culture (every town)...", command=self.culture_names_table)
        menu.add_command(label="Check and install a pack...", command=self.install_pack)
        menu.add_command(label="Campaign rules (ages, agents, towns, diplomacy, unit sizes)...",
                         command=self.campaign_rules)
        menu.add_command(label="Traits and retinue (what they give, their names, new ones)...",
                         command=self.traits_window)
        menu.add_command(label="Events and later factions (plagues, volcanoes, historic messages)...",
                         command=self.events_window)
        menu.add_command(label="New religion... (Medieval II)", command=lambda: self.religions_from_menu(True))
        menu.add_command(label="Religions of a region... (Medieval II)", command=lambda: self.religions_from_menu(False))
        menu.add_command(label="Restore a backup...", command=self.restore)
        menu.add_separator()
        menu.add_command(label="Game manifest...", command=self.game_manifest)
        menu.add_command(label="Log", command=self.show_log)
        menu.add_command(label="Save logs (zip)...", command=self.save_logs)
        menu.add_command(label="Report a bug...", command=self.send_report)
        menu.add_command(label="Suggest an idea...", command=lambda: self.send_report(kind="suggestion"))
        tools["menu"] = menu
        tools.pack(side="right")
        self.status = tk.StringVar(value="Pick the Mod, or Browse... to its data folder (for example ...\\HLR\\data) "
                                         "and press Load.")
        self.status_line.configure(textvariable=self.status)
        self.status.trace_add("write", lambda *a: self._log_status())
        for k in ("name", "template"):
            self.v[k].trace_add("write", lambda *a: self.update_actions())
        self.update_actions()
        self.after(50, self.load_last)

    def _build_units_tab(self):
        """Units & armies: the chosen towns on the left, their garrisons on the right."""
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Units & armies  ")
        # the towns and armies | the garrison: the line between them can be dragged
        panes = ttk.Panedwindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        side = ttk.Frame(panes, padding=(0, 0, 6, 0))
        panes.add(side, weight=0)
        # towns above, armies/agents/fleets below; the sash between them can be dragged
        split = ttk.PanedWindow(side, orient="vertical")
        split.pack(fill="both", expand=True)
        top = ttk.Frame(split)
        split.add(top, weight=1)
        ttk.Label(top, text="Your towns", font=("", 10, "bold")).pack(anchor="w")
        # the hints and buttons are packed before the lists: a lower window shrinks the lists, never them
        ttk.Label(top, text="give it towns on the Map (a click on a town)", foreground="#666").pack(side="bottom", anchor="w")
        self.lb_units = tk.Listbox(top, width=30, height=8, exportselection=False)
        self.lb_units.pack(fill="both", expand=True)
        self.lb_units.bind("<<ListboxSelect>>", lambda e: (self.lb_field.selection_clear(0, "end"),
                                                           self.load_garrison()))
        # field armies, agents and fleets, placed on the Map
        ff = ttk.LabelFrame(split, text="Armies, agents & fleets  (drag the line above to resize)", padding=4)
        split.add(ff, weight=2)
        ttk.Label(ff, text="double click: show it on the map", foreground="#666").pack(side="bottom", anchor="w")
        fb = ttk.Frame(ff)
        fb.pack(side="bottom", fill="x", pady=(4, 0))
        self.lb_field = FieldTable(ff)
        self.lb_field.pack(fill="both", expand=True)
        self.lb_field.bind("<<ListboxSelect>>", lambda e: self.lb_field.curselection() and (
            self.lb_units.selection_clear(0, "end"), self.load_field()))
        self.lb_field.bind("<Double-1>", lambda e: self.field_on_map())
        for text, kind in (("+ Army", "army"), ("+ Agent", "agent"), ("+ Fleet", "fleet")):
            ttk.Button(fb, text=text, width=8, command=lambda k=kind: self.add_field(k)).pack(side="left", padx=1)
        ttk.Button(fb, text="Place on map", command=self.place_field).pack(side="left", padx=(8, 1))
        ttk.Button(fb, text="Remove", command=self.remove_field).pack(side="left", padx=1)
        opts = self.units_opts = ttk.LabelFrame(side, text="Towns without a garrison of your own", padding=6)
        opts.pack(side="bottom", fill="x", pady=(10, 0), before=split)
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
        self.garrison_editor = GarrisonEditor(panes, pictures=self.pictures)
        panes.add(self.garrison_editor, weight=1)

    def _build_buildings_tab(self):
        """Buildings: the chosen towns on the left, what stands in the selected one on the right."""
        tab = ttk.Frame(self.nb, padding=4)
        self.nb.add(tab, text="  Buildings  ")
        # the towns | the buildings: the line between them can be dragged
        panes = ttk.Panedwindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        side = ttk.Frame(panes, padding=(0, 0, 6, 0))
        panes.add(side, weight=0)
        ttk.Label(side, text="Your towns", font=("", 10, "bold")).pack(anchor="w")
        ttk.Label(side, text="give it towns on the Map (a click on a town)", foreground="#666").pack(side="bottom", anchor="w")
        self.lb_build = tk.Listbox(side, width=30, height=12, exportselection=False)
        self.lb_build.pack(fill="both", expand=True)
        self.lb_build.bind("<<ListboxSelect>>", lambda e: self.load_buildings())
        right = ttk.Frame(panes, padding=(6, 0, 0, 0))
        panes.add(right, weight=1)
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
        self.lbl_size.pack(side="left", fill="x", expand=True)
        self.buildings_editor = BuildingsEditor(right, self.pictures)
        self.buildings_editor.pack(fill="both", expand=True)

    def _faction_for(self, region):
        """Whose buildings and units a town's tabs offer: the faction picked in the Faction tab, else the town's
        owner now (no need to pick one first), else the rebels."""
        picked = self.v["template"].get().strip()
        if picked:
            return picked
        owner = (self.strat.owners().get(region) if self.strat else None) or "slave"
        self.status.set("No faction picked - showing what %s (the owner of %s) may build and recruit." % (
            owner, region))
        return owner

    def load_buildings(self):
        sel = self.lb_build.curselection()
        if not sel or not self.mod or not self.strat or sel[0] >= len(self.chosen):
            return
        region = self.chosen[sel[0]]
        template = self._faction_for(region)
        if self._edb_for != self.mod.data:
            self._edb = read_buildings(self.mod.load(self.mod.file("edb"))) if self.mod.file("edb") else []
            self._bpics = BuildingPictures(self.mod)
            self._edb_for = self.mod.data
        st = self.strat.settlement_of(region)
        town_level, own = settlement_info(self.strat.lines[st.start:st.end]) if st else ("village", [])
        pop = population_of(self.strat.lines[st.start:st.end]) if st else 400
        new = self._new_region(region)
        if new and not st:                          # a new region: the size picked in its dialog
            town_level, pop = new.get("level") or "village", POP_MIN.get(new.get("level") or "village", 400) or 400
        self._size_region, self._size_now = region, (town_level, pop)
        file_kind = settlement_kind(self.strat.lines[st.start:st.end]) if st else "city"
        self._kind_now = file_kind
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
            # a smaller governor's building picked by hand: the settlement shrinks to it and
            # the other buildings with it
            ed = self.buildings_editor
            last, ed.last_pick = getattr(ed, "last_pick", None), None
            if last and last[0].lower().startswith("core") and last[1] != "-":
                b = next((x for x in self._edb if x.name == last[0]), None)
                lv = b.level(last[1]) if b else None
                now = self.v_level.get() or town_level
                fit = ed.core_for(now)
                fit_lv = b.level(fit[1]) if b and fit and fit[0] == last[0] and fit[1] else None
                if lv and fit_lv and rank(core_settlement(b, lv.name)) < rank(core_settlement(b, fit_lv.name)):
                    self.after_idle(lambda: self._level_to(core_settlement(b, lv.name), sync_core=False))
        # the chains offer the levels of the settlement as it will be: set by hand, grown
        # by a picked governor's building, or as the file has it
        shown = size.get("level") or self._grown_level(self.buildings_picked.get(region), town_level)
        self.buildings_editor.roster = self._roster_levels()
        known = {b.name: b for b in self._edb}
        self.buildings_editor.load(region, shown, self._edb, own, self.buildings_picked.get(region),
                                   self.mod.culture(template), self.v["name"].get().strip().lower() or template,
                                   template, self._bpics, changed,
                                   kind=self.kinds.get(region, file_kind) if castles_allowed(self.mod, known) else None,
                                   on_kind=lambda k: self.set_kind(region, k))

    def set_kind(self, region, kind):
        """Medieval II: the town becomes a city or a castle - its buildings converted the game's way (each level's
        convert_to), the governor's building fitted to the settlement level; written with the next Apply."""
        known = {b.name: b for b in self._edb}
        st = self.strat.settlement_of(region)
        town_level, own = settlement_info(self.strat.lines[st.start:st.end]) if st else ("village", [])
        level = self.sizes.get(region, {}).get("level") or self._grown_level(self.buildings_picked.get(region),
                                                                              town_level)
        now = self.kinds.get(region, self._kind_now)
        if kind == now:
            return
        bad = kind_problem(known, kind, level)
        if bad:
            messagebox.showerror(APP, "%s: %s." % (region, bad))
            self.load_buildings()
            return
        self.remember()
        base = self.buildings_picked.get(region)
        items, changes = convert(list(base) if base is not None else own, kind, known, level)
        if kind == self._kind_now and base is None:
            self.kinds.pop(region, None)
        else:
            self.kinds[region] = kind
            self.buildings_picked[region] = items
        if kind == self._kind_now and self.buildings_picked.get(region) == own:
            self.buildings_picked.pop(region, None)
        gone = [o[1] for o, n in changes if o and not n]
        moved = ["%s -> %s" % (o[1], n[1]) for o, n in changes if o and n]
        self.status.set("%s is now a %s (written with Apply)%s%s" % (
            region, kind, "; " + ", ".join(moved) if moved else "",
            "; gone (a %s has none): %s" % (kind, ", ".join(gone)) if gone else ""))
        self.refresh_chosen(keep_units_selection=True)
        self.load_buildings()

    def _grown_level(self, picked, town_level):
        """The level a settlement gets from its picked governor's building (never smaller)."""
        need = core_need(picked or [], {b.name: b for b in self._edb})
        return need if need and rank(need) > rank(town_level) else town_level

    def level_picked(self):
        region = getattr(self, "_size_region", None)
        if region and self.buildings_editor.kind == "castle":
            bad = kind_problem({b.name: b for b in self._edb}, "castle", self.v_level.get())
            if bad:                               # a castle ends at the citadel: the level goes back
                messagebox.showerror(APP, "%s: %s. Make it a city first (Settlement is a: city)." % (region, bad))
                self.v_level.set(self.buildings_editor.town_level)
                return
        self._level_to(self.v_level.get())

    def _level_to(self, level, sync_core=True):
        """A settlement level picked by hand (or a smaller governor's building): the
        governor's building follows it (the biggest that level allows), buildings too
        big for it drop to the biggest level that fits, the chains offer that level's
        buildings, and the population moves into the level's range."""
        region = getattr(self, "_size_region", None)
        if not region:
            return
        self.v_level.set(level)
        ed = self.buildings_editor
        pop = self.v_pop.get().strip()
        bigger = SETTLEMENT_LEVELS[rank(level) + 1] if 0 <= rank(level) < len(SETTLEMENT_LEVELS) - 1 else None
        if pop.isdigit() and (int(pop) < POP_MIN.get(level, 0) or bigger and int(pop) >= POP_MIN[bigger]):
            self.v_pop.set(str(POP_MIN[level]))       # into the level's range, else it grows or shrinks at once
        self.size_changed()
        core = ed.core_for(level) if sync_core else None
        ed.town_level = level
        ed.title.configure(text="%s - a %s%s" % (region, level, " castle" if ed.kind == "castle" else ""))
        said = []
        if core and core[1] and ed.current.get(core[0]) != core[1]:
            ed.pick(core[0], core[1])                 # remembers for Undo and redraws
            ed.last_pick = None
            said.append("governor's building %s" % core[1])
        elif core and not core[1] and core[0] in ed.current:
            ed.pick(core[0], NONE)                    # a village has no governor's building
            ed.last_pick = None
            said.append("no governor's building")
        down = ed.fit_down(level)
        said += ["%s %s -> %s" % (c, o, n or "none") for c, o, n in down]
        ed.set_level(level)
        if said:
            self.status.set("%s: %s - %s" % (region, level, "; ".join(said)))

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

    def tab_name(self):
        """The name of the faction tab on show ('Faction', 'Settlements', 'Map' ...), '' when none."""
        cur = self.nb.select()
        return self.nb.tab(cur, "text").strip() if cur else ""

    def select_tab(self, name):
        self.nb.select([self.nb.tab(t, "text").strip() for t in self.nb.tabs()].index(name))

    def tab_opened(self):
        """A town tab with nothing selected opens the capital."""
        tab = self.tab_name()
        if tab == "Map":
            self.show_map()
            return
        if tab == "Diplomacy":
            self.load_diplomacy()
            return
        if tab == "Art":
            self.art_editor.load()
            return
        if tab == "Roster":
            self.roster_editor.load()
            return
        if tab == "Faction":
            self.show_family_button()
            if self._family_open:
                self.family_editor.load()
            return
        if tab == "Settlements":
            self.settlements.load()
            return
        lb, load = {"Units & armies": (self.lb_units, self.load_garrison),
                    "Buildings": (self.lb_build, self.load_buildings)}.get(tab, (None, None))
        if lb is not None and self.chosen and not lb.curselection():
            capital = self.v["capital"].get() or self.chosen[0]
            lb.selection_set(self.chosen.index(capital) if capital in self.chosen else 0)
            load()

    WORK_TITLES = {"new": "New faction", "edit": "Edit faction", "units": "Unit editor",
                   "buildings": "Building editor", "characters": "Character editor",
                   "terrain": "Terrain editor", "addons": "Add-ons", "religions": "Religions"}
    WORK_HINTS = {"religions": "the game's religions and each region's shares (Medieval II)", "addons": "ready-made scripts that add something new to the game (Sack Settlement...)","new": "make a new faction from a template", "edit": "change a faction that is in the game",
                  "units": "every line of a unit in export_descr_unit.txt, its card and picture",
                  "buildings": "every line of a building chain in export_descr_buildings.txt, its pictures",
                  "characters": "any faction's characters: names, ages, traits, ancillaries, portraits, family tree",
                  "terrain": "paint the campaign map's ground, rivers, fords and cliffs"}

    def work_changed(self):
        """New / Edit faction share the campaign tabs; the unit and building editors
        take the window's middle instead."""
        w = self.v_work.get()
        if w in self.work_buttons:
            self.work_row.show(self.work_buttons[w])
        if w in ("new", "edit"):
            for ed in self.editors.values():
                ed.pack_forget()
            if self.v_mode.get() != w and self.undo_stack and not messagebox.askyesno(
                    APP, "Switch to %s? The changes not written yet (towns, garrisons, map, diplomacy...) "
                         "are dropped." % ("Edit faction" if w == "edit" else "New faction")):
                self.v_work.set(self.v_mode.get())         # stay where the work is
                return
            self.nb.pack(fill="both", expand=True, padx=6, pady=3, after=self.bottom_bar)
            if self.v_mode.get() != w:
                self.v_mode.set(w)
                self.mode_changed()
            self.update_actions()
            return
        self.nb.pack_forget()
        for k, ed in self.editors.items():
            if k != w:
                ed.pack_forget()
        ed = self.editor()
        ed.pack(fill="both", expand=True, padx=6, pady=3, after=self.bottom_bar)
        if self.mod and ed.mod is not self.mod:
            self._rebind(ed)
        elif w == "religions":
            ed.fill()                          # the shares may have changed on the Map since
        self.update_actions()
        self._mark_work()

    def editor(self):
        """The unit, building or character editor on show, made the first time; None for the faction work."""
        w = self.v_work.get()
        if w not in ("units", "buildings", "characters", "terrain", "addons", "religions"):
            return None
        if w not in self.editors:
            if w == "religions":
                from .gui_religions import ReligionsPanel
                self.editors[w] = ReligionsPanel(self, self)
            elif w == "addons":
                from .gui_addons import AddonsPanel
                self.editors[w] = AddonsPanel(self, self)
            elif w == "terrain":
                from .gui_terrain import TerrainEditor
                self.editors[w] = TerrainEditor(self, self)
            elif w == "characters":
                from .gui_family import FamilyEditor
                self.editors[w] = FamilyEditor(self, self, standalone=True)
            else:
                from .gui_editors import RecordEditor
                self.editors[w] = RecordEditor(self, self, "unit" if w == "units" else "building")
        return self.editors[w]

    def select_map_opts(self):
        """The Art tab's campaign-select map wish; {} while that part is put away (gui_art.MAP_PART)."""
        from .gui_art import MAP_PART
        return dict(self.sel_map) if MAP_PART else {}

    def editing(self):
        return self.v_mode.get() == "edit"

    def _theme_label(self):
        from . import theme
        self.b_theme.configure(text="\u2600  Light" if theme.dark() else "\u263e  Dark")

    def toggle_theme(self):
        """Light / Dark look, kept for the next start."""
        from . import theme
        theme.toggle(self)
        self._theme_label()
        try:
            self.map_view._draw_legend()
        except Exception:
            pass

    def _lock_frame(self, frame, locked):
        """Every entry / list in the frame greyed out (locked) or back to its own state."""
        saved = self.__dict__.setdefault("_locked_states", {})
        for w in frame.winfo_children():
            self._lock_frame(w, locked)
            try:
                if locked:
                    saved.setdefault(str(w), str(w.cget("state")))
                    w.configure(state="disabled")
                elif str(w) in saved:
                    w.configure(state=saved.pop(str(w)))
            except tk.TclError:
                pass

    def fill_faction_list(self):
        """The factions to pick: a template (New - never the rebels) or the faction to change (Edit - the
        rebels too: their armies, fleets, garrisons, towns and units are edited like any faction's)."""
        if not self.mod:
            return
        names = [n for n, _ in self.mod.factions() if n != "slave"]
        if self.editing() and "slave" in [n for n, _ in self.mod.factions()]:
            names.append("slave")
        self.cb_template.set_names(names, self.shown_names())
        if not self.editing() and self.v["template"].get().strip() == "slave":
            self.v["template"].set("")

    def mode_changed(self):
        """New faction (clone a template) or Edit faction (change one in place)."""
        edit = self.editing()
        self.fill_faction_list()
        self.chk_playable.configure(state="normal")
        self._lock_frame(self.lf2, False)
        self.lf.configure(text="Edit faction" if edit else "New faction")
        self.lbl_template.configure(text="Faction (edited)" if edit else "Template (copied)")
        self.lf2.configure(text="Leader and heir (names from the faction's name list)" if edit else
                           "Leader and heir (names must come from the template's name list)")
        self.e_name.configure(state="readonly" if edit else "normal")
        for ws in self.extra_rows.values():             # shown again by load_existing when the faction has them
            for w in ws:
                w.grid_remove()
        # cloning-only options are hidden in Edit (diplomacy gets its own editor later)
        for w in [self.chk_triggers, self.chk_art] + self.dip_row:
            if edit:
                w.grid_remove()
            else:
                w.grid()
        if edit:
            for w in self.give_row:
                w.grid()
        else:
            for w in self.give_row:
                w.grid_remove()
        for w in self.units_opts.winfo_children():
            try:
                w.configure(state="disabled" if edit else "normal")
            except tk.TclError:
                pass
        self.update_actions()
        self.garrison_editor.auto_text = ("unchanged - the town keeps its garrison" if edit else None)
        self.chosen, self.garrisons, self.buildings_picked, self.sizes = [], {}, {}, {}
        self.kinds = {}
        self.art_replace, self.sel_map = {}, {}
        self.figures = {}
        self.roster_set = {}
        self.family_set = {}
        self.editing_now = None
        self.char_moves = {}
        self.field, self._placing = [], None
        self.refresh_field()
        self.refresh_chosen()
        if edit and self.v["template"].get() and self.strat and self.strat.faction(self.v["template"].get().strip()):
            self.template_changed()
        if self.tab_name() == "Faction" and self._family_open:
            self.family_editor.load()
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
        for k in ("display_name", "short_name", "adjective", "ai", "religion"):
            self.v[k].set(now.get(k) or "")
        for k, ws in self.extra_rows.items():
            self.v[k].set(now.get(k) or "")
            for w in ws:
                (w.grid if k in now else w.grid_remove)()
        self.v["denari"].set(str(now.get("denari", "")))
        self.v_playable.set(bool(now.get("playable")))
        # the rebels are never playable; they have no capital, leader or heir
        self.chk_playable.configure(state="disabled" if faction == "slave" else "normal")
        self._lock_frame(self.lf2, faction == "slave")
        for t, k in ((self.t_descr, "description"), (self.t_long, "long_description")):
            t.delete("1.0", "end")
            t.insert("1.0", now.get(k) or "")
        for key, b in (("primary", self.b_primary), ("secondary", self.b_secondary)):
            rgb = now.get(key + "_colour")
            self.colours[key] = rgb
            if rgb:
                b.configure(**colour_look(rgb))
        for role in ("leader", "heir"):
            who = now.get(role) or {}
            name = who.get("name", "")
            first = name.split(" ")[0] if name else ""
            self.v[role + "_first"].set(first)
            self.v[role + "_last"].set(name[len(first):].strip())
            self.v[role + "_age"].set(str(who.get("age") or ""))
        self.cb_give.set_names([n for n, _ in self.mod.factions() if n != faction], self.shown_names())
        self.v_give.set("slave")
        self.chosen = list(now.get("regions", []))
        self.garrisons, self.buildings_picked, self.sizes = {}, {}, {}
        self.kinds = {}
        self.char_moves, self.roster_set = {}, {}
        self.family_set = {}
        self.name_list = {}
        self.roster_editor.forget()
        self.family_editor.forget()
        self.field, self.removed_existing, self._placing = self._existing_field(faction), [], None
        self.dip_set.clear()
        self.refresh_field()
        if self.chosen:
            self.v["capital"].set(self.chosen[0])
        self.refresh_chosen()
        self.undo_stack, self.redo_stack = [], []      # Undo never reaches back into another faction
        now["_faction"] = faction
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
            elif c.kind not in ("general", "named character"):
                kind = c.kind                           # an agent: spy, merchant, priest, princess...
            elif units:
                kind = "army"
            else:
                continue                               # a family member without an army
            out.append({"kind": kind, "name": c.name, "units": units[1:] if c.named and units else units,
                        "xy": c.xy, "from": c.xy, "existing": True, "cid": "%s:%d" % (faction, i),
                        "named": c.named, "changed": False})
        return out

    # ------------------------------------------------------------------ undo / redo
    UNDO_KEYS = ("chosen", "garrisons", "buildings_picked", "sizes", "kinds", "place_moves", "char_moves", "field",
                 "removed_existing", "dip_set", "region_paint", "new_regions", "region_religions", "new_religions", "region_edits",
                 "culture_names", "name_list", "res_moves", "res_removed", "res_added", "region_tags", "fort_moves", "fort_removed", "fort_added", "art_replace", "sel_map", "figures", "roster_set",
                 "family_set")

    def snapshot(self):
        st = {k: copy.deepcopy(getattr(self, k)) for k in self.UNDO_KEYS}
        st["capital"] = self.v["capital"].get()
        st["victory"] = (self.victory.faction, copy.deepcopy(self.victory.cond))
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
        fac, cond = st.get("victory") or (None, None)
        if cond is not None and fac == self.victory.faction:     # another faction's conditions never come back
            self.victory.cond = copy.deepcopy(cond)
            self.victory.show()
        self.refresh_chosen()
        self.refresh_name_combos()
        self.refresh_field()
        self.fill_towns()
        tab = self.tab_name()
        if tab == "Units & armies" and self.lb_units.curselection():
            self.load_garrison()
        elif tab == "Units & armies" and self.lb_field.curselection():
            self.load_field()
        elif tab == "Buildings" and self.lb_build.curselection():
            self.load_buildings()
        elif tab == "Map":
            self.show_map()
        elif tab == "Diplomacy":
            self.load_diplomacy()
        elif tab == "Roster":
            self.roster_editor.redraw()
        elif tab == "Faction" and self._family_open:
            self.family_editor.redraw()

    def roster_changed(self):
        """A unit or building level given or taken on the Roster tab: the garrison and
        building pickers offer what the faction will have, not only what the files say."""
        self.status.set("Roster: %d change(s) - Preview, then Apply changes." % len(self.roster_set))

    def _roster_units(self, units):
        """The faction's units as the Roster leaves them: given ones added, taken ones out."""
        if not self.editing() or not self.roster_set:
            return units
        taken = {k[5:] for k, v in self.roster_set.items() if k.startswith("unit:") and v is False}
        given = {k[5:] for k, v in self.roster_set.items() if k.startswith("unit:") and v is True}
        have = {u.type for u in units}
        out = [u for u in units if u.type not in taken]
        if given - have and self.mod.file("edu"):
            out += [u for u in read_units(self.mod.load(self.mod.file("edu"))) if u.type in given - have]
        return out

    def _roster_levels(self):
        """{(chain, level): give?} picked on the Roster tab (Edit only)."""
        if not self.editing():
            return {}
        return {tuple(k.split(":", 2)[1:]): v for k, v in self.roster_set.items() if k.startswith("building:")}

    def _in_editor(self, redo=False):
        """The editors keep their own changes: Undo / Redo there go to the editor on show when it has
        steps of its own (the Terrain editor's strokes), never to the faction tabs' work unseen; the others
        say what to use instead (the user clicked the bottom Undo in the Terrain editor and nothing said so)."""
        ed = self.editor()
        if ed is None:
            return False
        step = getattr(ed, "redo_step" if redo else "undo_step", None)
        if step:
            step()
            return True
        self.status.set("In the %s: 'Undo all changes here' drops its changes; a field goes back when you type "
                        "its old value." % self.WORK_TITLES.get(self.v_work.get(), "editor"))
        return True

    def undo(self, e=None):
        if self._typing():
            return None
        if self._in_editor():
            return "break"
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
        if self._in_editor(redo=True):
            return "break"
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

    def support(self):
        """The Ko-fi page in the browser: donations keep the work on the tool going."""
        import webbrowser
        webbrowser.open(KOFI)
        self.status.set("Thank you! %s opened in your browser." % KOFI)

    def show_help(self):
        self.show_text("Help", HELP)

    def diplomacy_base(self):
        """(me, {(kind, from, to): value}) as the start stands without the picks:
        the file for an edited faction; for a new one its template's relations
        (or only the rebels' line, as the game's own factions have it) as the build writes them."""
        from .diplomacy import KINDS, read, rebels
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
        if not src:
            for kind, pairs in rebels(self.strat, "me").items():
                for (a, b), v in pairs.items():
                    base[(kind, a, b)] = v
        return me, base

    def load_diplomacy(self):
        if not self.mod or not self.strat or not self.v["template"].get().strip():
            return
        me, base = self.diplomacy_base()
        others = [fb.name for fb in self.strat.factions if fb.name != me]
        names = dict(self.mod.factions())
        self.dip_editor.before = self.remember
        from .diplomacy import is_medieval, kinds
        self.dip_editor.load(me, others, base, self.dip_set, names,
                             lambda: self.status.set("%d diplomacy change(s) - Preview, then %s." % (
                                 len(self.dip_set), "Apply changes" if self.editing() else "Create faction")),
                             kinds=kinds(self.strat), medieval=is_medieval(self.strat))

    # ------------------------------------------------------------------ regions
    def _region_colours(self):
        cols = {r: v["colour"] for r, v in self.regions.items()}
        cols.update({r["name"]: tuple(r["colour"]) for r in self.new_regions})
        return cols

    def _region_view(self, place):
        """The Map's Regions mode: paint overlay, callbacks, new towns and ports."""
        on = self.map_view.v_regions.get()
        points = []
        for r in self.new_regions:
            for what in ("city", "port"):
                if r.get(what):
                    points.append((tuple(r[what]), what, tuple(r["colour"])))
        if on:
            self.region_bar.pack(fill="x", before=self.map_view)
        else:
            self.region_bar.pack_forget()
            # the political colours show the painted land too (the map as it will be); a new
            # region's land, town and port show in its own colour until Apply
            new = {r["name"]: tuple(r["colour"]) for r in self.new_regions}
            land = {t: new[r] for t, r in self.region_paint.items() if r in new}
            return {"region_mode": False, "region_painted": self.region_paint, "region_points": points,
                    "new_land": land}
        cols = self._region_colours()
        names = sorted(cols)
        self.cb_paint["values"] = [r["name"] + "  (new)" for r in self.new_regions] + names
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

    def _map_tools(self):
        """The legend's tools the map offers now: towns, forts, watchtowers and resources always; armies, fleets
        and agents for the faction being made or edited."""
        if not self.mod or not self.strat:
            return {}
        from .resources import types
        tools = {"town": True, "fort": True, "watchtower": True}
        tools.update({"res:" + t: True for t in types(self.mod)})
        if self.v_mode.get() in ("new", "edit") and self.field_faction() and not self.map_only():
            tools.update({k: True for k in ("army", "fleet")})
            tools.update({k: True for k in self.AGENTS})
        return tools

    def map_tool(self, key):
        """A tool picked in the Map's legend: the next click on the map makes one there (a town first asks for
        its region's names, then its land around the click is the region's)."""
        from . import forts as FT
        mv = self.map_view
        self._res_placing = None
        self._region_point, self._town_auto = None, False
        if key is None:
            self._placing = None
            self.status.set("")
            self.show_map()
            return
        if key in FT.KINDS:
            alive = [fo for fo in (self.strat.forts if self.strat else []) if fo.line not in self.fort_removed]
            if not any(fo.kind == key for fo in alive):
                mv.set_tool(None)
                messagebox.showinfo(APP, "No new %s here: %s." % (key, FT.no_example(key)))
                return
            mv.v_forts.set(True)
            self.v_fort_type.set(key)
            self.res_place_new(key)
        elif key.startswith("res:"):
            mv.v_res.set(True)
            self.v_res_type.set(key[4:])
            self.res_place_new(key[4:])
        elif key == "town":
            self.new_region_dialog(then=self._start_town, cancelled=lambda: mv.set_tool(None))
        elif key in ("army", "fleet"):
            self.add_field(key, then_place=True)
        else:
            self.add_field("agent", preset=key, then_place=True)

    def _start_town(self, name):
        """After New region... from the legend: the next click puts its town; the land around it becomes the new
        region's (painted in Edit regions, which is switched on - paint more with a left drag)."""
        mv = self.map_view
        if not mv.v_regions.get():
            mv.v_regions.set(True)
            mv._regions_toggled()
        self.v_paint.set(name + "  (new)")
        self._region_point, self._town_auto = ("city", name), True
        self.status.set("Click the tile where the town of %s stands - the land around it becomes %s's." % (name, name))
        self.show_map()

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

    def _town_land(self, xy, name):
        """The tiles around a town placed from the legend that become its region's: the 3 x 3 around it (no other
        region may touch a town), land only, never another town or port. {tile: region it had in region_paint}."""
        cm = self._cmap
        taken = {tuple(r.get(k) or ()) for r in self.new_regions for k in ("city", "port")}
        got = {}
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                t = (xy[0] + dx, xy[1] + dy)
                if not (0 <= t[0] < cm.w and 0 <= t[1] < cm.h) or t in taken:
                    continue
                if cm.region_at(*t) is None or cm.regions_img.get(*t) in ((0, 0, 0), (255, 255, 255)):
                    continue                          # sea, towns and ports keep their region
                got[t] = self.region_paint.get(t)
                self.region_paint[t] = name
        return got

    def place_region_point(self, xy):
        what, name = self._region_point
        before = None
        if self._town_auto and what == "city":
            self.remember()
            before = self._town_land(tuple(xy), name)
        why = self.region_point_problem(xy)
        if why:
            if before is not None:                    # the land given for nothing goes back
                for t, was in before.items():
                    if was is None:
                        self.region_paint.pop(t, None)
                    else:
                        self.region_paint[t] = was
            return why
        r = self._new_region(name)
        if before is None:
            self.remember()
        r[what] = tuple(xy)
        self._region_point, self._town_auto = None, False
        self.map_view.set_tool(None)
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
        self.chosen = [r for r in self.chosen if r != name]
        self.refresh_chosen()
        self.fill_towns()
        self.v_paint.set("")
        self.show_map()

    def new_region_dialog(self, edit=None, then=None, cancelled=None):
        """New region..., or with edit = a region's name: its data again - a new one (not written
        yet) all of it, a region of the map its descr_regions lines (builder, rebels, tags,
        triumph, farming), written with the next Apply."""
        if not self.mod or not self.strat:
            return
        from .regionedit import EDITABLE, SHOWN, free_colour, shown_labels
        cur = self._new_region(edit) if edit else None
        old = self.regions.get(edit) if edit and not cur else None
        if edit is not None and not cur and not old:
            messagebox.showerror(APP, "Pick a region first: 'Paint with' on the Map (right click a region), "
                                      "or a town on the Settlements tab.")
            return
        w = tk.Toplevel(self)
        w.title("Region %s%s" % (edit, " (new)" if cur else "") if edit else "New region")
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        facs = [fb.name for fb in self.strat.factions]
        rebels = sorted({v.get("rebels") for v in self.regions.values() if v.get("rebels")})
        res = self._region_tag_names()
        me = self.v["template"].get().strip()
        fields = [("Region - name in the files", "name", "", "letters, digits, _ ; no spaces (Tribus_Novus)"),
                  ("Region - name shown in the game", "label", "", "empty = the file name without _ (best kept alike)"),
                  ("Town - name in the files", "settlement", "", "must differ from the region's (Novus_Oppidum)"),
                  ("Town - name shown in the game", "settlement_label", "", "best like its file name (the region's may match)"),
                  ("Built by (culture of its buildings)", "creator", AS_LAND,
                   "the faction whose style the town's buildings have; by default that of the region "
                   "its land is cut from"),
                  ("Rebels there", "rebels", AS_LAND,
                   "who rises up / holds it as rebels (a rebel type of this mod); by default those of "
                   "the region its land is cut from"),
                  ("Region tags (hidden resources)", "resources", "",
                   "comma list; empty = those of the land it is cut from. Not the goods drawn on the map: "
                   "tags buildings ask for ('resource' / 'hidden_resource' in export_descr_buildings), "
                   "which open buildings and local units"),
                  ("Triumph value", "triumph", "5", "how much taking it counts for a triumph; most use 5"),
                  ("Farming level", "farming", "3", "food from the land: 1 poor ... 5 rich; most use 2-4"),
                  ("Owner at the start", "owner", "(rebel village - no settlement written)",
                   "a faction gets a settlement; none = the game makes a rebel village"),
                  ("Town size at the start", "level", "village", "for an owner only")]
        rebel_text = "(rebel village - no settlement written)"
        if cur:
            given = {"name": cur["name"], "label": cur.get("label") or "", "settlement": cur["settlement"],
                     "settlement_label": cur.get("settlement_label") or "", "creator": cur.get("creator") or AS_LAND,
                     "rebels": cur.get("rebels") or AS_LAND, "resources": ", ".join(cur.get("resources") or []),
                     "triumph": str(cur.get("triumph", 5)), "farming": str(cur.get("farming", 3)),
                     "owner": cur.get("owner") or rebel_text, "level": cur.get("level") or "village"}
            fields = [(a, k, given[k], h) for a, k, _, h in fields]
        elif old:
            town = old.get("settlement", "")
            now_shown = shown_labels(self.mod, self.v_campaign.get(), [edit, town])
            shown_now = {"label": now_shown.get(edit) or edit.replace("_", " "),
                         "settlement_label": now_shown.get(town) or town.replace("_", " ")}
            was = dict(old, **shown_now)
            was.update(self.region_edits.get(edit, {}))
            given = {k: (", ".join(was[k]) if isinstance(was.get(k), list) else str(was.get(k) or ""))
                     for k in SHOWN + EDITABLE}
            fields = [(a, k, given[k], "the name players see; the file name %s stays - best keep them alike"
                       % (edit if k == "label" else town) if k in SHOWN else h.split(";")[0].replace("by default ", ""))
                      for a, k, _, h in fields if k in SHOWN + EDITABLE]
            ttk.Label(frm, text="%s - town %s. Written with the next Apply (descr_regions.txt, the names players "
                                "see in the campaign's names text); the file names and the land stay as they are. Tip: give the name "
                                "players see and the name in the files the same spelling (Latium / Latium) - a mod is "
                                "easier to read, search and fix when a place has one name everywhere."
                                % (edit, town), font=("", 9, "bold"), wraplength=620, justify="left"
                      ).grid(row=99, column=0, columnspan=3, sticky="w", pady=(6, 0))
        vs = {}
        for i, (label, key, default, hint) in enumerate(fields):
            ttk.Label(frm, text=hint, foreground="#666", wraplength=420, justify="left").grid(row=i, column=2, sticky="w")
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=1)
            v = tk.StringVar(value=default)
            vs[key] = v
            if key in ("creator", "owner"):
                vals = [AS_LAND] + facs if key == "creator" else ["(rebel village - no settlement written)"] + facs
                from .gui_util import FactionBox
                FactionBox(frm, v, vals, self.shown_names(), width=34).grid(row=i, column=1, sticky="we", padx=6)
            elif key == "rebels":
                ttk.Combobox(frm, textvariable=v, values=[AS_LAND] + rebels,
                             width=34).grid(row=i, column=1, sticky="we", padx=6)
            elif key == "level":
                ttk.Combobox(frm, textvariable=v, values=SETTLEMENT_LEVELS, state="readonly",
                             width=34).grid(row=i, column=1, sticky="we", padx=6)
            else:
                ttk.Entry(frm, textvariable=v, width=36).grid(row=i, column=1, sticky="we", padx=6)
        ttk.Label(frm, text="region tags in this mod (descr_regions line 6 and the buildings' requirements): " +
                  ", ".join(res), foreground="#666", wraplength=620,
                  justify="left").grid(row=len(fields), column=0, columnspan=3, sticky="w", pady=(4, 0))

        def ok():
            from .regionedit import _ok_name
            d = {k: v.get().strip() for k, v in vs.items()}
            if old:                                      # a region of the map: only what differs
                ch = {}
                for k in SHOWN + EDITABLE:
                    now = shown_now[k] if k in SHOWN else str(old.get(k) or "")
                    val = d[k]
                    if k in SHOWN and ("{" in val or "}" in val):
                        messagebox.showerror(APP, "a name players see cannot hold { or }", parent=w)
                        return
                    if k == "resources":
                        val = ", ".join(x.strip() for x in val.split(",") if x.strip())
                        now = ", ".join(x.strip() for x in now.split(",") if x.strip())
                    if k in ("triumph", "farming") and val and not val.isdigit():
                        messagebox.showerror(APP, "%s is a whole number" % k, parent=w)
                        return
                    if k == "creator" and val and val not in facs:
                        messagebox.showerror(APP, "%s is no faction of this mod" % val, parent=w)
                        return
                    if val and val != now:
                        ch[k] = val
                self.remember()
                if ch:
                    self.region_edits[edit] = ch
                else:
                    self.region_edits.pop(edit, None)
                w.destroy()
                self.status.set("%s: %s - Preview, then Apply." % (edit, ", ".join("%s %s" % x for x in ch.items())
                                                                     or "as it is"))
                return
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
            if cur:
                taken -= {cur["name"], cur["settlement"]}
            clash = [n for n in (d["name"], d["settlement"]) if n in taken]
            if clash:
                messagebox.showerror(APP, "%s is taken already by a region or settlement" % clash[0], parent=w)
                return
            self.remember()
            owner = d["owner"] if d["owner"] in facs else None
            if cur:                                      # the new region's data again: in place, names followed
                was = cur["name"]
                cur.update({
                    "name": d["name"], "settlement": d["settlement"], "label": d["label"] or None,
                    "settlement_label": d["settlement_label"] or None,
                    "creator": "" if d["creator"] == AS_LAND else d["creator"],
                    "rebels": "" if d["rebels"] == AS_LAND else d["rebels"],
                    "resources": [x.strip() for x in d["resources"].split(",") if x.strip()],
                    "triumph": int(d["triumph"]) if d["triumph"].isdigit() else 5,
                    "farming": int(d["farming"]) if d["farming"].isdigit() else 3,
                    "owner": owner, "level": d["level"] or "village"})
                if d["name"] != was:
                    self.region_paint = {t: (d["name"] if r == was else r) for t, r in self.region_paint.items()}
                    self.chosen = [d["name"] if r == was else r for r in self.chosen]
                    for store in (self.region_religions, self.garrisons, self.buildings_picked, self.sizes):
                        if was in store:
                            store[d["name"]] = store.pop(was)
                if owner and self.editing() and owner == me and d["name"] not in self.chosen:
                    self.chosen.append(d["name"])
                self.refresh_chosen()
                self.fill_towns()
                w.destroy()
                self.v_paint.set(d["name"] + "  (new)")
                self.status.set("%s changed - written with the next Apply." % d["name"])
                self.show_map()
                return
            colour = free_colour(self.mod, self.v_campaign.get(), self._region_colours().values())
            self.new_regions.append({
                "name": d["name"], "settlement": d["settlement"], "label": d["label"] or None,
                "settlement_label": d["settlement_label"] or None,
                # empty = as the region its land is cut from (regionedit.donor_of, on Apply)
                "creator": "" if d["creator"] == AS_LAND else d["creator"],
                "rebels": "" if d["rebels"] == AS_LAND else d["rebels"], "resources": [x.strip() for x in d["resources"].split(",") if x.strip()],
                "triumph": int(d["triumph"]) if d["triumph"].isdigit() else 5,
                "farming": int(d["farming"]) if d["farming"].isdigit() else 3,
                "colour": colour, "city": None, "port": None, "owner": owner, "level": d["level"] or "village"})
            if owner and self.editing() and owner == me and d["name"] not in self.chosen:
                # the edited faction's own new town: in its lists at once (garrison, buildings,
                # capital), written with the region by the same Apply
                self.chosen.append(d["name"])
                self.refresh_chosen()
            self.fill_towns()                  # in the towns list at once, as '(new - written with Apply)'
            w.destroy()
            self.v_paint.set(d["name"] + "  (new)")
            self.status.set("Paint %s's land (left drag), then 'Place its town' (and 'Place its port')." % d["name"])
            if then:
                then(d["name"])
                return
            self.show_map()

        def cancel():
            w.destroy()
            if cancelled:
                cancelled()
        w.protocol("WM_DELETE_WINDOW", cancel)
        bar = ttk.Frame(frm)
        bar.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(bar, text="OK" if edit else "Add", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=cancel).pack(side="left", padx=4)

    def _regions_opts(self):
        if not self.region_paint and not self.new_regions and not self.region_religions and not self.region_edits \
                and not self.culture_names and not self.new_religions:
            return None
        me = self.v["template"].get().strip()
        new = []
        for r in self.new_regions:
            r = dict(r)
            if self.editing() and r.get("owner") == me and r["name"] not in self.chosen:
                r["owner"] = None                  # taken out of the faction's towns again: a rebel village
            if not self.editing() and not self.map_only() and r["name"] in self.chosen:
                r["owner"] = None                  # the new faction starts there: it takes the rebel village
            new.append(r)
        return {"new_religions": [dict(r) for r in self.new_religions],
                "painted": dict(self.region_paint), "new": new,
                "religions": {k: dict(v) for k, v in self.region_religions.items()},
                "edits": {k: dict(v) for k, v in self.region_edits.items()},
                "culture_names": {k: dict(v) for k, v in self.culture_names.items()}}

    def culture_names_table(self):
        """Every town's names by culture in one table (sort, filter, edit in place)."""
        if not self.mod or not self.strat:
            messagebox.showerror(APP, "Load a mod first.")
            return
        from .gui_culturenames import CultureNamesTable
        CultureNamesTable(self)

    def culture_names_dialog(self, region):
        """REX: the town's name for each culture of its owner - the game renames it when it changes hands."""
        if not self.mod or not self.strat:
            return
        from . import culturenames as CN
        new = self._new_region(region) if region else None
        info = new or self.regions.get(region) if region else None
        if not info or not info.get("settlement"):
            self.culture_names_table()          # no town picked: the table of every town
            return
        town = info["settlement"]
        cults = CN.cultures(self.mod)
        now = dict(CN.read(self.mod, self.v_campaign.get()).get(town) or {})
        now.update(self.culture_names.get(town) or {})
        now.setdefault(CN.DEFAULT, (new or {}).get("settlement_label") or CN.shown_name(
            self.mod, self.v_campaign.get(), town))
        w = tk.Toplevel(self)
        w.title("Names of %s by culture" % town)
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        eng, rex = CN.engine(self.mod)
        ttk.Label(frm, justify="left", wraplength=460, foreground="#555" if rex else "#a33", text=(
            "When the town changes hands, " + eng + " renames it for the new owner's culture - at once when a general "
            "takes it, and at the start of each of its owner's turns. Empty = no name of its own for that "
            "culture: the name for 'every other culture' is used. Written into the campaign's "
            "campaign_script.txt (made when the campaign has none)." if rex else
            "Needs %s: the game folder has no %s.exe, so nothing will be written." % (eng, eng))).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        rows = [(CN.DEFAULT, "every other culture")] + [(c, c) for c in cults]
        vs = {}
        for i, (key, label) in enumerate(rows):
            ttk.Label(frm, text=label).grid(row=i + 1, column=0, sticky="w", padx=(0, 8), pady=1)
            v = tk.StringVar(value=now.get(key, ""))
            ttk.Entry(frm, textvariable=v, width=30).grid(row=i + 1, column=1, sticky="w", pady=1)
            vs[key] = v

        def ok():
            got = {k: v.get().strip() for k, v in vs.items() if v.get().strip()}
            bad = CN.problems(self.mod, {town: got})
            if bad:
                messagebox.showerror(APP, "\n".join(bad), parent=w)
                return
            self.remember()
            self.culture_names[town] = got
            self.status.set("%s: names by culture for %d culture(s) - written with the next Apply." % (
                town, len(got)))
            w.destroy()
            self.fill_towns()                  # the map and the towns list show the owner's name at once
            self.show_map()
        bar = ttk.Frame(frm)
        bar.grid(row=len(rows) + 1, column=0, columnspan=2, pady=(8, 0), sticky="w")
        ttk.Button(bar, text="OK", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)
        ttk.Button(bar, text="All towns...", command=lambda: (w.destroy(), self.culture_names_table())).pack(
            side="left", padx=(16, 0))

    def religions_from_menu(self, new):
        """Tools > New religion / Religions of a region: the same dialogs as on the Map (Edit regions), reached
        without knowing where they live - the Map is opened with Edit regions on, so the shares can be painted
        region by region afterwards."""
        if not self.mod:
            messagebox.showerror(APP, "Load a mod first.")
            return
        from . import religions as RL
        if not RL.names(self.mod):
            messagebox.showinfo(APP, "Rome has no religions (the game has no descr_religions.txt) - they are "
                                     "Medieval II's.")
            return
        if self.v_work.get() not in ("new", "edit"):
            self.v_work.set("edit")
            self.work_changed()
        tabs = [self.nb.tab(t, "text").strip() for t in self.nb.tabs()]
        if "Map" in tabs:
            self.nb.select(tabs.index("Map"))
        if not self.map_view.v_regions.get():
            self.map_view.v_regions.set(True)
            self.show_map()
        if new:
            self.new_religion_dialog()
        elif not self.v_paint.get().strip():
            self.status.set("Right click a region on the map (or pick it in 'Paint with'), then Religions... above "
                            "the map.")
        else:
            self.religions_dialog()

    def religions_dialog(self):
        """Medieval II: the religions of the region in 'Paint with' (percent, 100 in all)."""
        if not self.mod or not self.strat:
            return
        known = {k: v["religions"] for k, v in self.regions.items() if "religions" in v}
        if not known:
            messagebox.showinfo(APP, "This game's regions have no religions line (Rome has none; "
                                     "Medieval II has one per region).")
            return
        name = self.v_paint.get().replace("  (new)", "").strip()
        new = self._new_region(name)
        if not new and name not in self.regions:
            messagebox.showerror(APP, "pick a region in 'Paint with' first (or right click it on the map)")
            return
        names = list(next(iter(known.values())).keys())
        for v in known.values():
            names += [k for k in v if k not in names]
        names += [r["name"] for r in self.new_religions if r["name"] not in names]   # waiting for Apply
        now = (new or {}).get("religions") or self.region_religions.get(name) or known.get(name)
        if not now:
            # a new region: those of the region its land is cut from (what Apply writes when
            # the dialog is skipped), else the campaign's most common
            from .regionedit import donor_of, religions_for
            donor = donor_of(self.mod, self.v_campaign.get(), self.region_paint, new) if new else None
            now = religions_for(self.regions, None, donor) or {k: 0 for k in names}
        # the region as players see it and in the files, with its town - also inside the window: a narrow
        # window's title bar cuts the name
        from .regionedit import shown_labels
        town = (new or self.regions.get(name) or {}).get("settlement") or ""
        try:
            shown = shown_labels(self.mod, self.v_campaign.get(), [name, town] if town else [name])
        except Exception:
            shown = {}
        head = shown.get(name) or name
        if head != name:
            head += "  (%s)" % name
        if town:
            head += "  -  town %s" % (shown.get(town) or town)
        w = tk.Toplevel(self)
        w.title("Religions of %s" % (shown.get(name) or name))
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=head, font=("", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="percent of the region's people, 100 in all", foreground="#666").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))
        frm = ttk.Frame(frm)
        frm.grid(row=2, column=0, columnspan=2, sticky="w")
        vs = {}
        total = ttk.Label(frm, text="")
        for i, k in enumerate(names):
            ttk.Label(frm, text=k).grid(row=i, column=0, sticky="w")
            v = tk.StringVar(value=str(now.get(k, 0)))
            vs[k] = v
            e = ttk.Spinbox(frm, from_=0, to=100, increment=5, textvariable=v, width=6,
                            command=lambda: sums())
            e.grid(row=i, column=1, sticky="w", padx=6, pady=1)
            e.bind("<KeyRelease>", lambda ev: sums())
        total.grid(row=len(names), column=0, columnspan=2, sticky="w", pady=(6, 0))

        def values():
            return {k: int(v.get()) if v.get().strip().isdigit() else 0 for k, v in vs.items()}

        def sums():
            t = sum(values().values())
            total.configure(text="in all %d%%%s" % (t, "" if t == 100 else " - must be 100"),
                            foreground="" if t == 100 else "#c00000")
        sums()

        def ok():
            rel = values()
            if sum(rel.values()) != 100:
                messagebox.showerror(APP, "the religions must add up to 100", parent=w)
                return
            self.remember()
            if new:
                new["religions"] = rel
            elif rel == known.get(name):
                self.region_religions.pop(name, None)
            else:
                self.region_religions[name] = rel
            w.destroy()
            self.status.set("%s: %s - Preview, then Apply changes." % (
                name, ", ".join("%s %d%%" % (k, v) for k, v in rel.items() if v)))
        bar = ttk.Frame(frm)
        bar.grid(row=len(names) + 1, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(bar, text="OK", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    def new_religion_dialog(self):
        """Medieval II: a new religion (e.g. Judaism) written everywhere the game needs it on Apply;
        its shares per region are set with Religions... afterwards."""
        if not self.mod:
            messagebox.showerror(APP, "Load a mod first.")
            return
        from . import religions as RL
        have = RL.names(self.mod)
        if not have:
            messagebox.showinfo(APP, "Religions are Medieval II's - this game has no descr_religions.txt.")
            return
        w = tk.Toplevel(self)
        w.title("New religion")
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        v = {k: tk.StringVar() for k in ("name", "shown", "pip_from", "picture")}
        v["pip_from"].set(have[0])
        from .limits import engine_of, lifted
        count = ("%d religions in this mod (%s beside the game: no limit)" % (len(have), engine_of(self.mod)[:-4])
                 if lifted(self.mod, "religions") else
                 "%d of %d religions in this mod (the original game's limit)" % (len(have), RL.MAX_RELIGIONS))
        ttk.Label(frm, text="%s%s. A new one is written to descr_religions.txt, its "
                            "lookup, text/religions.txt, its symbol (ui/pips) and every region's religions line "
                            "(0 %% until you set its share with Religions...); map.rwm is removed." % (
                                count, ", %d waiting" % len(self.new_religions)
                                if self.new_religions else ""),
                  wraplength=520, justify="left").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(frm, text="Name in the files").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v["name"], width=24).grid(row=1, column=1, sticky="w")
        ttk.Label(frm, text="e.g. judaism", foreground="#666").grid(row=1, column=2, sticky="w")
        ttk.Label(frm, text="Name players see").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v["shown"], width=24).grid(row=2, column=1, sticky="w")
        ttk.Label(frm, text="Symbol like").grid(row=3, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=v["pip_from"], values=have, state="readonly", width=21).grid(
            row=3, column=1, sticky="w")
        ttk.Label(frm, text="its size; its picture unless you pick one", foreground="#666").grid(
            row=3, column=2, sticky="w")
        ttk.Label(frm, text="Own symbol").grid(row=4, column=0, sticky="w")
        pic = ttk.Frame(frm)
        pic.grid(row=4, column=1, columnspan=2, sticky="w")
        ttk.Entry(pic, textvariable=v["picture"], width=30).pack(side="left")
        ttk.Button(pic, text="Browse...", command=lambda: v["picture"].set(filedialog.askopenfilename(
            parent=w, title="The religion's symbol (PNG, JPG, TGA...)") or v["picture"].get())).pack(side="left", padx=4)
        ttk.Label(frm, text="Factions that follow it").grid(row=5, column=0, sticky="nw", pady=(6, 0))
        lb = tk.Listbox(frm, selectmode="multiple", height=8, exportselection=False)
        facs = [n for n, _ in self.mod.factions() if n != "slave"]
        from .build import faction_label
        for n in facs:
            lb.insert("end", faction_label(n, self.shown_names().get(n)))
        lb.grid(row=5, column=1, sticky="w", pady=(6, 0))
        ttk.Label(frm, text="optional - none keeps every faction's religion", foreground="#666").grid(
            row=5, column=2, sticky="nw", pady=(6, 0))

        def ok():
            spec = {"name": v["name"].get().strip().lower(), "shown": v["shown"].get().strip(),
                    "pip_from": v["pip_from"].get(), "picture": v["picture"].get().strip() or None,
                    "factions": [facs[i] for i in lb.curselection()]}
            why = RL.problems(self.mod, spec, self.new_religions)
            if why:
                messagebox.showerror(APP, "\n".join(why), parent=w)
                return
            self.remember()
            self.new_religions.append(spec)
            w.destroy()
            self.status.set("New religion %s waits for Apply - give it regions with Religions... (Map tab, "
                            "Regions), then Preview and Apply changes." % spec["name"])
        bar = ttk.Frame(frm)
        bar.grid(row=6, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(bar, text="OK", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    # ---- resources on the map ----
    def _resources_opts(self):
        forts = {"moved": {str(k): list(v) for k, v in self.fort_moves.items()}, "removed": list(self.fort_removed),
                 "added": [dict(a) for a in self.fort_added]} \
            if (self.fort_moves or self.fort_removed or self.fort_added) else None
        if not (self.res_moves or self.res_removed or self.res_added or self.region_tags or forts):
            return None
        return {"moved": {str(k): list(v) for k, v in self.res_moves.items()}, "removed": list(self.res_removed),
                "added": [dict(a) for a in self.res_added], "region_tags": dict(self.region_tags), "forts": forts}

    def _file_resources(self):
        """The resources of the campaign's descr_strat.txt (read once per load)."""
        from .resources import read
        key = (self.mod.data, self.v_campaign.get())
        if getattr(self, "_res_cache", None) is None or self._res_cache[0] != key:
            f = self.mod.load(self.mod.campaign_file(self.v_campaign.get(), "descr_strat.txt"))
            self._res_cache = (key, read(f))
        return self._res_cache[1]

    @staticmethod
    def _how(parent, text):
        """A bar's how-to on a line of its own under it, wrapping at the window's width (never cut off)."""
        lbl = ttk.Label(parent, text=text, foreground="#666", justify="left")
        lbl.pack(fill="x", anchor="w", pady=(2, 0))
        parent.bind("<Configure>", lambda e: lbl.configure(wraplength=max(200, e.width - 8)), add="+")

    def _resource_view(self):
        """The Map's resources, forts and watchtowers: shown with their layer, moved, added and removed here
        (ids: r<line> / n<i> resources, f<line> / g<i> forts)."""
        from . import forts as FT
        from .resources import problem, types
        mv = self.map_view
        res_on, forts_on = mv.v_res.get(), mv.v_forts.get()
        for bar, on in ((self.res_bar, res_on), (self.fort_bar, forts_on)):
            if on:
                bar.pack(fill="x", before=mv)
            else:
                bar.pack_forget()
        if not (res_on or forts_on):
            self._res_placing = None
            return {}
        kinds = list(types(self.mod))
        self.cb_res_type["values"] = kinds
        if self.v_res_type.get() not in kinds:
            self.v_res_type.set(kinds[0] if kinds else "")
        if self._res_placing and not (forts_on if self._res_placing in FT.KINDS else res_on):
            self._res_placing = None                    # its mode was switched off
        shown = []
        if res_on:
            shown += [{"id": "r%d" % r.index, "kind": r.kind, "xy": tuple(self.res_moves.get(r.index, r.xy))}
                      for r in self._file_resources() if r.index not in self.res_removed]
            shown += [{"id": "n%d" % i, "kind": a["type"], "xy": tuple(a["xy"])} for i, a in enumerate(self.res_added)]
        camp = self.v_campaign.get()
        file_forts = self.strat.forts if self.strat else []
        if forts_on:
            shown += [{"id": "f%d" % fo.line, "kind": fo.kind, "xy": tuple(self.fort_moves.get(fo.line, fo.xy))}
                      for fo in file_forts if fo.line not in self.fort_removed]
            shown += [{"id": "g%d" % i, "kind": a["kind"], "xy": tuple(a["xy"])} for i, a in enumerate(self.fort_added)]
            # a new one copies a line of its kind the campaign has: say at once which kinds cannot be placed
            have = {fo.kind for fo in file_forts if fo.line not in self.fort_removed}
            missing = [k for k in FT.KINDS if k not in have]
            self.lbl_fort_new.configure(text="" if not missing else (
                "This campaign has no %s line yet, so a new %s cannot be placed here: the line differs by game "
                "and mod and is copied from one the campaign already has (vanilla Rome and Medieval II have "
                "none). Moving and removing work for the ones on the map." % (
                    " or ".join(missing), " / ".join(missing))))

        def is_fort(rid):
            return rid[:1] in ("f", "g")

        def taken(but=None, forts=False):
            return [r["xy"] for r in shown if r["id"] != but and is_fort(r["id"]) == forts]

        def check(rid, xy):
            if is_fort(rid):
                return FT.problem(self.mod, camp, xy, taken(rid, True))
            return problem(self.mod, camp, xy, taken(rid))

        def moved(rid, xy):
            self.remember()
            if rid.startswith("g"):
                self.fort_added[int(rid[1:])]["xy"] = tuple(xy)
            elif rid.startswith("f"):
                i = int(rid[1:])
                orig = next(fo.xy for fo in file_forts if fo.line == i)
                if tuple(xy) == tuple(orig):
                    self.fort_moves.pop(i, None)
                else:
                    self.fort_moves[i] = tuple(xy)
            elif rid.startswith("n"):
                self.res_added[int(rid[1:])]["xy"] = tuple(xy)
            else:
                i = int(rid[1:])
                orig = next(r.xy for r in self._file_resources() if r.index == i)
                if tuple(xy) == tuple(orig):
                    self.res_moves.pop(i, None)
                else:
                    self.res_moves[i] = tuple(xy)
            self._res_sel = rid
            self.status.set("%s moved to %d, %d - Preview, then Apply." % (
                next((r["kind"] for r in shown if r["id"] == rid), "Resource").capitalize(), xy[0], xy[1]))
            self.show_map()

        def clicked(rid):
            self._res_sel = rid
            kind = next((r["kind"] for r in shown if r["id"] == rid), None)
            if kind:
                (self.v_fort_type if is_fort(rid) else self.v_res_type).set(kind)
            self.show_map()

        kw = {"resources": shown, "check_res": check, "on_res_move": moved, "on_res_click": clicked,
              "res_sel": self._res_sel}
        if self._res_placing:
            kind = self._res_placing

            def place(xy):
                if kind in FT.KINDS:
                    why = FT.problem(self.mod, camp, xy, taken(None, True))
                    alive = [fo for fo in file_forts if fo.line not in self.fort_removed]
                    if not why and FT.example(alive, kind, xy) is None:
                        why = FT.no_example(kind)
                        messagebox.showinfo(APP, "No new %s: %s." % (kind, why))
                        self._res_placing = None
                        return why
                else:
                    why = problem(self.mod, camp, xy, taken())
                if why:
                    return why
                self.remember()
                if kind in FT.KINDS:
                    self.fort_added.append({"kind": kind, "xy": tuple(xy)})
                    self._res_sel = "g%d" % (len(self.fort_added) - 1)
                else:
                    self.res_added.append({"type": kind, "xy": tuple(xy)})
                    self._res_sel = "n%d" % (len(self.res_added) - 1)
                self._res_placing = None
                self.map_view.set_tool(None)
                self.status.set("%s placed at %d, %d - right drag moves it; Preview, then Apply." % (kind, xy[0], xy[1]))
                self.show_map()
                return None
            kw["on_place"] = place
        return kw

    def res_place_new(self, kind):
        """Place new on the resource / fort bar: the next click on the map puts one there."""
        if not kind:
            messagebox.showerror(APP, "Pick what to place first (the list left of Place new).")
            return
        self._res_placing = kind
        self.status.set("Now click a land tile on the map where the new %s goes." % kind)
        self.show_map()

    def res_delete(self):
        rid = self._res_sel
        if not rid:
            messagebox.showerror(APP, "Click the resource or fort on the map first (it gets a frame), then Delete "
                                      "picked.")
            return
        self.remember()
        if rid.startswith("g"):
            i = int(rid[1:])
            if i < len(self.fort_added):
                del self.fort_added[i]
        elif rid.startswith("f"):
            i = int(rid[1:])
            if i not in self.fort_removed:
                self.fort_removed.append(i)
            self.fort_moves.pop(i, None)
        elif rid.startswith("n"):
            i = int(rid[1:])
            if i < len(self.res_added):
                del self.res_added[i]
        else:
            i = int(rid[1:])
            if i not in self.res_removed:
                self.res_removed.append(i)
            self.res_moves.pop(i, None)
        self._res_sel = None
        self.status.set("Removed - Preview, then Apply (Undo brings it back).")
        self.show_map()

    def region_tags_dialog(self):
        """Line 6 of a region's entry in descr_regions.txt: its resource tags (in HLR
        also the hidden resources that open local units)."""
        if not self.mod or not self.strat:
            return
        name = self.v_paint.get().replace("  (new)", "").strip()
        if name not in self.regions:
            # the region under the picked resource, else ask for Regions mode's pick
            rid = self._res_sel
            xy = None
            if rid:
                xy = next((a["xy"] for i, a in enumerate(self.res_added) if "n%d" % i == rid), None) or \
                    next((self.res_moves.get(r.index, r.xy) for r in self._file_resources() if "r%d" % r.index == rid), None)
            cm = self._cmap
            name = (cm.region_at(*xy) or next((r for r, t in cm.cities.items() if t == tuple(xy)), None)) \
                if xy and cm else None
        if not name or name not in self.regions:
            messagebox.showerror(APP, "click a resource on the map (its region is taken), or pick a region "
                                      "in Regions mode (right click)")
            return
        now = self.region_tags.get(name, self.regions[name].get("resources", ""))
        known = self._region_tag_names()
        w = tk.Toplevel(self)
        w.title("Region tags of %s" % name)
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="%s - region tags (hidden resources), comma separated: line 6 of its entry in "
                            "descr_regions.txt.\nBuildings ask for them ('resource' / 'hidden_resource' "
                            "requirements) - they open buildings and local units. The goods drawn on the map are "
                            "the resources above it, not these." % name, justify="left").pack(anchor="w")
        v = tk.StringVar(value=now)
        ttk.Entry(frm, textvariable=v, width=70).pack(fill="x", pady=4)
        ttk.Label(frm, text="in this mod: " + ", ".join(known), foreground="#666", wraplength=520,
                  justify="left").pack(anchor="w")

        def ok():
            text = ", ".join(x.strip() for x in v.get().split(",") if x.strip())
            if not text:
                messagebox.showerror(APP, "a region needs at least one tag", parent=w)
                return
            self.remember()
            if text == self.regions[name].get("resources", ""):
                self.region_tags.pop(name, None)
            else:
                self.region_tags[name] = text
            w.destroy()
            self.status.set("%s: %s - Preview, then Apply." % (name, text))
        bar = ttk.Frame(frm)
        bar.pack(anchor="e", pady=(8, 0))
        ttk.Button(bar, text="OK", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    def _region_tag_names(self):
        """The region tags this mod uses: descr_regions' line 6 and the names the
        buildings' 'resource' / 'hidden_resource' requirements ask for."""
        import re
        out = {x.strip() for v in self.regions.values() for x in (v.get("resources") or "").split(",")
               if x.strip() and x.strip() != "none"}
        edb = self.mod.file("edb") if self.mod else None
        if edb:
            rx = re.compile(r"\b(?:hidden_)?resource\s+([A-Za-z0-9_]+)")
            for line in self.mod.load(edb).texts():
                if "resource" in line:
                    out.update(rx.findall(line.split(";")[0]))
        return sorted(out)

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
            from .diplomacy import kinds
            feeling = kinds(self.strat)[0]
            for other in {fb.name for fb in self.strat.factions}:
                pick = lambda key: self.dip_set[key] if key in self.dip_set else base.get(key)
                start = pick(("faction_relationships", "me", other))     # an alliance / a war shows first
                v = start if isinstance(start, str) else pick((feeling, "me", other))
                colours[other] = tuple(int(dip_colour(v)[i:i + 2], 16) for i in (1, 3, 5))
        if not self.editing():
            template = self.v["template"].get().strip()
            colours[me] = tuple(self.colours["primary"] or colours.get(template, (255, 215, 0)))
        elif self.colours["primary"]:
            colours[me] = tuple(self.colours["primary"])
        owners = self.owners_after(me, owners)
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
        from .start import unit_name
        for fb in self.strat.factions:
            for i, c in enumerate(fb.characters):
                if not c.xy:
                    continue
                lines = self.strat.lines[c.start:c.end]
                army = any(tokens(l)[:1] == ["army"] for l in lines)
                cid = "%s:%d" % (fb.name, i)
                xy = self.char_moves.get(cid, town_moves.get(c.xy) or fleet_moves.get(c.start) or c.xy)
                ulines = [l for l in lines if tokens(l)[:1] == ["unit"]]
                chars.append({"id": cid, "faction": fb.name, "name": c.name, "kind": c.kind, "xy": xy,
                              "army": army, "units": len(ulines), "unit_names": [unit_name(l) for l in ulines],
                              "from": c.xy})
                if army:
                    armies_at.add(xy)
        from .start import KINDS
        for i, fc in enumerate(self.field):
            if fc.get("xy") and not fc.get("existing"):         # those are drawn from descr_strat
                rtw_kind, army = KINDS[fc["kind"]]
                chars.append({"id": "new:%d" % i, "faction": me, "name": fc["name"], "kind": rtw_kind,
                              "xy": tuple(fc["xy"]), "army": army, "units": len(fc["units"]),
                              "unit_names": [u if isinstance(u, str) else str(u.get("name", "")) if isinstance(u, dict)
                                             else str(u) for u in fc["units"]], "from": None})
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
            self.map_view.set_tool(None)
            self.refresh_field(keep=i)
            self.status.set("%s %s placed at %d, %d - drag it to move it.%s" % (
                fc["kind"], fc["name"], xy[0], xy[1],
                " Give it its units on the Units & armies tab (an army needs at least one)."
                if fc["kind"] in ("army", "fleet") and not fc.get("units") else ""))
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
        res_kw = self._resource_view()
        on_place = region_kw.pop("on_place", place if placing is not None else None)
        if res_kw.get("on_place"):
            on_place = res_kw.pop("on_place")
            region_kw.pop("ghost", None)
        region_kw.update(res_kw)
        if placing is not None and not region_kw.get("ghost") and placing < len(self.field):
            fc = self.field[placing]
            rtw_kind, army = KINDS[fc["kind"]]
            region_kw["ghost"] = {"kind": fc["kind"] if fc["kind"] in ("army", "fleet") else "agent",
                                  "check": lambda xy: self.mod.tile_problem(self.v_campaign.get(), xy, rtw_kind, army,
                                                                            armies_at)}
        self._map_labels = self.culture_labels(owners, me)
        self.map_view.allow_religion(self._m2())
        self.map_view.tools = self._map_tools()           # the legend's signs that are tools here
        from .resources import types as _res_types
        self.map_view.res_types = list(_res_types(self.mod))
        if self.map_view.v_rel.get():                # Religion colours: each region in its main religion's colour
            region_kw["tint"], region_kw["tint_legend"] = self.religion_tint()
        self.map_view.load(self._cmap, owners, colours, me, self.chosen, on_city=self.map_city, chars=chars,
                           labels=self._map_labels,
                           draggable=mine, on_char_move=moved, check_tile=check, symbols=symbols,
                           on_place=on_place,
                           places=self.place_moves, check_place=check_place, on_place_move=place_moved,
                           locked=self._locked_hint, forts=self.strat.forts if self.strat else [], **region_kw)

    RELIGION_COLOURS = {"catholic": (214, 170, 60), "orthodox": (70, 110, 190), "islam": (60, 150, 70),
                        "pagan": (140, 95, 50), "heretic": (140, 40, 140)}

    def religion_tint(self):
        """({region: rgb}, [(legend line, rgb)]) of the religion colours: each region in the colour of its main
        religion (its descr_regions line, or the share set in Religions... not written yet), paler the smaller that
        share is."""
        import colorsys
        from .religions import names as religion_names
        regions = self.mod.regions(self.v_campaign.get())
        known = list(religion_names(self.mod))
        def colour(rel):
            if rel in self.RELIGION_COLOURS:
                return self.RELIGION_COLOURS[rel]
            h = (sum(map(ord, rel)) * 0.137) % 1.0
            return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.6, 0.8))
        tint, count = {}, {}
        for r, v in regions.items():
            rel = dict(self.region_religions.get(r) or v.get("religions") or {})
            if not rel:
                continue
            main, share = max(rel.items(), key=lambda kv: kv[1])
            if share <= 0:
                continue
            k = 0.45 + 0.55 * min(share, 100) / 100.0             # a small majority: paler
            tint[r] = tuple(int(c * k + 200 * (1 - k)) for c in colour(main))
            count[main] = count.get(main, 0) + 1
        legend = [("%s: %d region(s)" % (rel, count[rel]), colour(rel))
                  for rel in sorted(count, key=lambda x: (known.index(x) if x in known else 99, x))]
        legend.append(("paler: a smaller majority", (200, 200, 200)))
        return tint, legend

    def _locked_hint(self, ch):
        """Why a character on the map cannot be dragged, and what to do instead."""
        if ch["faction"] == "slave":
            return "%s is a rebel - pick 'slave' in Edit faction to move the rebels" % ch["name"]
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
        if getattr(self, "_map_labels", {}).get(region, town) != town:
            town += " (now %s)" % self._map_labels[region]
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
        self.select_tab("Units & armies")
        i = self.chosen.index(region) if region in self.chosen else 0
        self.lb_units.selection_clear(0, "end")
        self.lb_units.selection_set(i)
        self.load_garrison()

    # ------------------------------------------------------------------ loading
    def browse(self):
        d = filedialog.askdirectory(title="The mod's data folder",
                                    initialdir=settings.get("game") or "")
        if d:
            self.v_path.set(d)
            self.load()

    def load_last(self):
        """At start: the mod loaded last time, if its folder is still there."""
        self.fill_mods(settings.get("game"))
        last = settings.get("mod_data")
        if last and os.path.isfile(os.path.join(last, "descr_sm_factions.txt")):
            self.v_path.set(last)
            self.load()

    def fill_mods(self, game):
        """The Mod list: what the game folder holds (the game, bi, HLR, mods made here...)."""
        self._mods = list_mods(game) if game else []
        self.cb_mods["values"] = [label for label, _ in self._mods]
        here = os.path.normcase(os.path.abspath(self.mod.data)) if self.mod else None
        self.v_modpick.set(next((label for label, d in self._mods
                                 if here and os.path.normcase(os.path.abspath(d)) == here), ""))

    def mod_picked(self):
        d = next((d for label, d in self._mods if label == self.v_modpick.get()), None)
        if d and (not self.mod or os.path.abspath(d) != os.path.abspath(self.mod.data)):
            if self.undo_stack and not messagebox.askyesno(
                    APP, "Load %s? The changes not written yet are dropped." % self.v_modpick.get()):
                self.fill_mods(settings.get("game"))
                return
            self.v_path.set(d)
            self.load()

    def campaign_picked(self):
        if self.mod:
            camps = settings.get("campaigns") or {}
            camps[self.mod.data] = self.v_campaign.get()
            settings.put("campaigns", camps)
        self.load_campaign()

    def shown_names(self):
        """{faction: the name players see} for this mod and campaign (read once per load / campaign)."""
        from .build import display_names
        key = (id(self.mod), self.v_campaign.get())
        if getattr(self, "_shown_key", None) != key:
            try:
                self._shown = display_names(self.mod, self.v_campaign.get() or None) if self.mod else {}
            except Exception:
                self._shown = {}
            self._shown_key = key
        return self._shown

    def load(self):
        try:
            self.mod = ModData(self.v_path.get())
            self._units_for = self._edb_for = None
        except Exception as e:
            from . import gamefix
            need = gamefix.unpack_needed(self.v_path.get()) if isinstance(e, FileNotFoundError) else None
            if need:
                self.offer_unpack(need)
            else:
                messagebox.showerror(APP, str(e))
            return
        self.v_path.set(self.mod.data)
        log.write("Load %s" % self.mod.data)
        self.roster_editor.forget()
        self.family_editor.forget()
        # remembered for the next start: this mod, its game folder, the campaign picked in it
        game = game_of(self.mod.data)
        settings.put("mod_data", self.mod.data)
        if is_game(game):
            settings.put("game", game)
        self.fill_mods(settings.get("game"))
        camps = self.mod.campaigns()
        self.cb_campaign["values"] = camps
        was = (settings.get("campaigns") or {}).get(self.mod.data)
        self.v_campaign.set(was if was in camps else
                            "imperial_campaign" if "imperial_campaign" in camps else (camps[0] if camps else ""))
        names = [n for n, _ in self.mod.factions() if n != "slave"]
        self.fill_faction_list()
        self._game_rows()
        self.load_campaign()
        from .limits import describe, faction_limit
        lim = faction_limit(self.mod)
        full = len(names) + 1 >= lim["max"] and lim["known"]
        self.status.set("%s, %d campaign(s).%s" % (describe(lim, len(names) + 1), len(camps),
                        (" Full: a new faction needs a higher max_factions (asked on Preview)." if lim["engine"]
                         else " Full: the original exe takes no new faction.") if full else ""))
        if not getattr(self, "_fix_queued", False):
            self._fix_queued = True
            self.after_idle(self.offer_fixes)
        # after Apply the editors read the files again; changes waiting in one whose file
        # was not written stay
        ed = self.editor()
        if ed is not None:
            self._rebind(ed)
        self._mark_work()

    def _m2(self):
        from .limits import game_kind
        return bool(self.mod) and game_kind(self.mod) == "medieval2"

    def _game_rows(self):
        """The faction form shows only what the loaded game has: Rome's short name and icon tooltip are hidden on
        Medieval II (its texts have neither)."""
        m2 = self._m2()
        for w in self.rome_rows:
            (w.grid_remove if m2 else w.grid)()
        for w in self.m2_rows:
            (w.grid if m2 else w.grid_remove)()
        if m2:
            from .religions import names
            self.cb_religion["values"] = names(self.mod) + [r["name"] for r in self.new_religions
                                                            if r["name"] not in names(self.mod)]
        else:
            self.v["religion"].set("")
        if m2:
            self.v["short_name"].set("")
            self.t_descr.delete("1.0", "end")

    def _rebind(self, ed):
        lost = ed.rebind(self.mod)
        if lost:
            messagebox.showwarning(APP, "The %s editor had %d change(s) not written; its file was written since "
                                        "(by another Apply), so they are dropped - make them again." % (ed.kind, lost))

    def offer_unpack(self, need):
        """Medieval II straight from Steam: its files are still in packs/. On a yes, the two
        DLLs the unpacker needs go next to it (from the game folder) and the game's own
        unpacker runs; then the game loads."""
        from . import gamefix
        dlls = (" First %s %s copied from the game folder next to the unpacker (it needs them)." % (
            " and ".join(need["dlls"]), "is" if len(need["dlls"]) == 1 else "are")) if need["dlls"] else ""
        if not messagebox.askyesno(APP, (
                "This Medieval II is not unpacked yet: its files are still in %d .pack file(s), so there is "
                "nothing to edit.\n\nUnpack it now with the game's own unpacker (tools\\unpacker)?%s\n\n"
                "It takes a few minutes and several GB of disk; the packs stay as they are.") % (
                need["packs"], dlls)):
            return
        result = {}

        def work():
            try:
                result["out"] = gamefix.unpack(need, log=lambda m: result.__setitem__("step", m))
            except Exception as e:
                result["error"] = str(e)
        th = threading.Thread(target=work, daemon=True)
        th.start()
        started = datetime.datetime.now()

        def wait():
            if th.is_alive():
                self.status.set("Unpacking Medieval II ... %d s (%s)" % (
                    (datetime.datetime.now() - started).seconds, result.get("step", "the unpacker runs")))
                self.after(1000, wait)
                return
            log.write("Unpack %s\n%s" % (need["game"], result.get("out") or result.get("error", "")))
            if "error" in result:
                self.status.set("")
                messagebox.showerror(APP, "Unpacking failed: %s" % result["error"])
                return
            self.v_path.set(os.path.join(need["game"], "data"))
            self.load()
            self.status.set("Medieval II unpacked and loaded.")
        wait()

    def offer_fixes(self):
        """Set-up problems that stop the game from starting (gamefix): put right on a yes,
        with a backup; a no is remembered for this mod."""
        from . import gamefix
        self._fix_queued = False
        try:
            found = gamefix.problems(ModData(self.mod.data))          # the files as they are now
        except Exception as e:
            log.write("setup check failed: %s" % e)
            return
        declined = settings.get("fixes_declined") or {}
        found = [p for p in found if p["id"] not in declined.get(self.mod.data, [])]
        if not found:
            return
        text = "\n\n".join(p["why"] for p in found)
        if not messagebox.askyesno(APP, "Found on Load - set-up problems of this game / mod:\n\n%s\n\nPut them right now? "
                                        "A backup is made first (Restore undoes it)." % text):
            declined = dict(declined)
            declined[self.mod.data] = declined.get(self.mod.data, []) + [p["id"] for p in found]
            settings.put("fixes_declined", declined)
            return
        plan = gamefix.fix_plan(ModData(self.mod.data), found)
        bdir = plan.apply()
        log.write("Set-up fixed (backup %s)\n%s" % (bdir, plan.report()))
        self.load()
        self.status.set("Set-up fixed: %s (backup made)." % ", ".join(p["id"] for p in found))

    def new_mod(self):
        """Make <game>/<name> from the loaded mod (hard links + copied text), then load it."""
        if not self.mod:
            messagebox.showerror(APP, "load the mod (or the game's data folder) to build on first")
            return
        _, base = game_root_of(self.mod.data)
        game = game_of(self.mod.data)
        m2 = is_medieval2(game)
        w = tk.Toplevel(self)
        w.title("New mod folder")
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Based on:  %s" % (base or "the game's own data"), font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="Created in:  %s" % os.path.dirname(mod_target(self.mod.data, "x"))).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(frm, text="New mod name").grid(row=2, column=0, sticky="w")
        v_name = tk.StringVar(value=(base or ("M2" if m2 else "RTW")) + "_" + (self.v["name"].get().strip().capitalize() or "New"))
        ttk.Entry(frm, textvariable=v_name, width=30).grid(row=3, column=0, sticky="we", padx=(0, 6))
        v_copy = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Copy every file (no hard links; needs the disk space)", variable=v_copy).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Label(frm, justify="left", wraplength=560, text=(
            "The base stays untouched. Text files are copied. Models, textures and sounds are 'hard links': "
            "the new folder shows every file (tens of thousands of them) at its full size in Explorer, but "
            "they are the same files on the disk as the base's - they take no extra space (only the copied "
            "text does, some tens of MB).\n"
            "Deleting the new mod folder never touches the game or the base mod. Only a program that "
            "overwrites a linked file in place (a texture editor saving over a .dds, say) changes the "
            "base's file too - the tool itself never does; tick 'Copy every file' to be fully apart.\n" +
            ("It goes into the game's mods folder with %s.cfg and Start_%s.bat (Medieval II starts a mod "
             "from its .cfg)." % ("<name>", "<name>") if m2 else
             "A start script Start_<name>.bat is written into the new folder."))).grid(
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
                    "Made %s\n\n%d file(s) linked, %d copied (%.0f MB really written)%s.\n\n%s"
                    "It is loaded now: the faction you create goes into it. Start the game with %s." % (
                        st["target"], st["linked"], st["copied"], st["bytes_copied"] / 1048576.0,
                        "" if st["hard_links"] else " - no hard links (another drive or 'copy every file')",
                        ("The linked files show full size in Explorer but take no disk space: they are the "
                         "base's own files under a second name. Deleting this folder never touches the "
                         "game.\n\n") if st["hard_links"] and st["linked"] else "",
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
        self.cb_owner.set_names(["(all)"] + owners, self.shown_names())
        self.chosen = []
        self.garrisons = {}
        self.buildings_picked = {}
        self.sizes = {}
        self.kinds = {}
        self.field, self._placing = [], None
        self.editing_now, self.char_moves = None, {}
        self.place_moves = {}
        self.dip_set.clear()
        self.region_paint, self.new_regions, self._region_point = {}, [], None
        self.region_edits = {}
        self.region_religions = {}
        self.new_religions = []
        self.culture_names = {}
        self.name_list = {}
        self.res_moves, self.res_removed, self.res_added, self.region_tags = {}, [], [], {}
        self.fort_moves, self.fort_removed, self.fort_added = {}, [], []
        self._res_placing, self._res_sel, self._res_cache = None, None, None
        self.art_replace, self.sel_map = {}, {}
        self.figures = {}
        self.roster_set = {}
        self.family_set = {}
        self._cmap_for = None                  # the map is read again: after Apply towns may stand elsewhere
        self.undo_stack, self.redo_stack = [], []
        self.refresh_field()
        self.refresh_chosen()
        self.fill_towns()
        # after Apply (which reloads) or a campaign change, the edited faction is read
        # afresh: its towns as they are now, never a stale list from before
        t = self.v["template"].get().strip()
        if t and t not in {n for n, _ in self.mod.factions()}:
            self.v["template"].set("")               # a faction of the mod loaded before (france in a Rome mod)
            t = ""
        if self.editing() and t and self.strat.faction(t):
            self.load_existing()
            self._baseline = self._faction_state()
        # an open Map (or Diplomacy) tab shows the files as they are now - after Apply,
        # Restore or a campaign change - not the picture read before
        if self.tab_name() in ("Map", "Diplomacy"):
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
        owners.update({r["name"]: r.get("owner") or "slave" for r in getattr(self, "new_regions", [])})
        return owners

    def culture_labels(self, owners, me=None):
        """{region: name} the towns show for these owners by the names-by-culture table (the campaign's
        script + what waits for Apply): the name follows the owner's culture as soon as a town changes hands."""
        from . import culturenames as CN
        if not self.mod or not self.strat:
            return {}
        table = dict(CN.read(self.mod, self.v_campaign.get()))
        table.update({k: v for k, v in self.culture_names.items() if v})
        for k in [k for k, v in self.culture_names.items() if not v]:
            table.pop(k, None)
        if not table:
            return {}
        cultures = dict(self.mod.factions())
        if me and me not in cultures:           # the new faction: the template's culture (the clone keeps it)
            cultures[me] = cultures.get(self.v["template"].get().strip())
        towns = {r: i.get("settlement") for r, i in self.regions.items() if i.get("settlement")}
        towns.update({r["name"]: r["settlement"] for r in self.new_regions if r.get("settlement")})
        return CN.labels(table, towns, owners, cultures.get)

    def owners_after(self, me=None, owners=None):
        """{region: owner} as the next Apply leaves the towns: new regions, the faction's chosen towns (me = the
        edited faction, or the new one's name), the towns it gives away."""
        if me is None:
            me = self.v["template"].get().strip() if self.editing() else \
                (self.v["name"].get().strip().lower() or "(new)")
        owners = dict(self.town_owners() if owners is None else owners)
        for r in self.new_regions:                  # a new region: its owner at the start, else the rebels
            owners[r["name"]] = r.get("owner") or "slave"
        for r in self.chosen:
            owners[r] = me
        if self.editing() and self.editing_now:
            for r in self.editing_now.get("regions", []):
                if r not in self.chosen:
                    owners[r] = self.v_give.get() or "slave"
        return owners

    def name_list_key(self):
        return self.v["template"].get().strip() if self.editing() else "(new)"

    def pool_for(self, faction):
        """The faction's name pools as the next Apply leaves them (a Name list... waiting counts)."""
        from .namelists import key_of
        key = faction if self.editing() else ("(new)" if faction == self.v["template"].get().strip() else faction)
        pools = self.name_list.get(key)
        if pools and self.editing() and faction == self.v["template"].get().strip():
            from .namelists import keep_used
            pools = keep_used(self.mod, faction, pools)[0]
        if pools:
            return {p: [key_of(n) for n in v] for p, v in pools.items() if v}
        return self.mod.name_pool(faction) or {}

    def leader_pool(self):
        return self.pool_for(self.v["template"].get().strip())

    def refresh_name_combos(self):
        pool = self.leader_pool()
        for a, b in self.cb_names:
            a["values"] = first_names(pool, "general")
            b["values"] = [""] + pool.get("surnames", [])
        own = self.name_list.get(self.name_list_key())
        if hasattr(self, "l_name_list"):
            from .namelists import counts
            self.l_name_list.configure(text=("its own list, written with Apply: " + counts(own)) if own else
                                       "its own men's names, surnames and women's names")

    def name_list_dialog(self):
        if not self.mod:
            return
        t = self.v["template"].get().strip()
        if not t:
            messagebox.showerror(APP, "pick the %s first" % ("faction" if self.editing() else "template"))
            return
        from .gui_names import NameListWizard
        key = self.name_list_key()
        label = t if self.editing() else (self.v["name"].get().strip() or "the new faction")
        start = self.name_list.get(key)
        if start is None and not self.editing():
            start = {}                         # a new faction: its own names typed in (or copied, step by step)
        NameListWizard(self, t if self.editing() else key, label, start)

    def name_list_set(self, who, pools):
        from .namelists import counts
        self.remember()
        self.name_list[self.name_list_key()] = {p: list(v) for p, v in pools.items()}
        self.refresh_name_combos()
        pool = self.leader_pool()
        for role in ("leader", "heir"):        # a name the new list lacks is emptied (the game crashes on it)
            if self.v[role + "_first"].get() and self.v[role + "_first"].get() not in pool.get("characters", []):
                self.v[role + "_first"].set("")
                self.v[role + "_last"].set("")
        self.status.set("Name list: %s - written with the next Apply." % counts(pools))

    def fill_towns(self):
        if not self.strat:
            return
        self.tv.delete(*self.tv.get_children())
        q = self.v_search.get().lower().strip()
        want = self.v_owner.get()
        villages = self.villages()
        owners = self.town_owners()
        shown = self.culture_labels(owners)
        for region, owner in sorted(owners.items(), key=lambda x: (x[1] != "slave", x[1], x[0])):
            town = self.regions.get(region, {}).get("settlement", "")
            if region in shown and shown[region] != town:
                town += "  (shown: %s)" % shown[region]
            if want not in ("", "(all)") and owner != want:
                continue
            if q and q not in region.lower() and q not in town.lower():
                continue
            new = self._new_region(region)
            if new:
                town = new["settlement"] + "  (new - written with Apply)"
            elif region in villages:
                town += " (village, not in descr_strat)"
            self.tv.insert("", "end", iid=region, text=region, values=(town, owner))

    def template_changed(self):
        t = self.v["template"].get()
        if not t or not self.mod:
            return
        if self.editing():
            was = self.editing_now.get("_faction") if self.editing_now else None
            if was and was != t and self.faction_pending():
                # the changes belong to the faction picked before: write them, drop them, or stay
                ans = messagebox.askyesnocancel(APP, "%s has changes not written yet.\n\nYes: apply them now "
                                                     "(with a backup), then open %s.\nNo: drop them.\n"
                                                     "Cancel: stay with %s." % (was, t, was))
                if ans is None:
                    self.v["template"].set(was)
                    return
                if ans:
                    self.v["template"].set(was)
                    self.create()
                    if self.faction_pending():
                        return                        # not written (refused or failed): stay
                    self.v["template"].set(t)
            self.load_existing()
        if self.tab_name() == "Faction" and self._family_open:     # the family tree open in the form's place
            self.family_editor.load()
        self.show_family_button()
        fb = self.strat.faction(t) if self.strat else None
        if fb:
            parts = fb.header.split(";")[0].split(",", 1)
            self.v["ai"].set(" ".join(parts[1].split()) if len(parts) > 1 else "")
        # the list offers every economy x military pair, plus what this campaign already uses
        # (variants like 'balanced smith random' or REX's 'opportunist')
        seen = {" ".join(x.header.split(";")[0].split(",", 1)[1].split())
                for x in (self.strat.factions if self.strat else []) if "," in x.header}
        self.cb_ai["values"] = AI_CHOICES + sorted(v for v in seen if v and v not in AI_CHOICES)
        pool = self.leader_pool()
        self.refresh_name_combos()
        if not self.editing():                 # names left from another faction are not in this one's lists
            for role in ("leader", "heir"):
                if self.v[role + "_first"].get() and self.v[role + "_first"].get() not in pool.get("characters", []):
                    self.v[role + "_first"].set("")
                    self.v[role + "_last"].set("")
        self.load_victory(t)
        disp = template_display(self.mod, t, self.v_campaign.get())
        if self.editing():
            self._baseline = self._faction_state()      # what 'not changed yet' looks like
            self._mark_work()
            return
        # empty fields start from the template: its money and colours (shown; the new
        # faction keeps them unless you pick others)
        try:
            now = read_faction(self.mod, self.v_campaign.get(), t)
        except Exception:
            now = {}
        d = self.v["denari"].get().strip()
        if now.get("denari") is not None and (not d or d == getattr(self, "_auto_denari", None)):
            self._auto_denari = str(now["denari"])             # the last template's, replaced by the next
            self.v["denari"].set(self._auto_denari)
        # the religion starts as the template's (Medieval II); one picked by hand for this faction stays
        r = self.v["religion"].get()
        if now.get("religion") and (not r or r == getattr(self, "_auto_religion", None)):
            self._auto_religion = now["religion"]
            self.v["religion"].set(now["religion"])
        for key, b in (("primary", self.b_primary), ("secondary", self.b_secondary)):
            rgb = self.colours.get(key) or now.get(key + "_colour")
            if rgb:
                b.configure(**colour_look(rgb))
        self.status.set("Template %s: %s. Its units, buildings, names, traits and art are copied." %
                        (t, disp.get("display_name", t)))

    def show_family_button(self):
        """The Faction tab's Family tree button: what a click does, and whose family it is."""
        me = self.v["template"].get().strip() if self.v_mode.get() == "edit" else ""
        if self._family_open:
            self.b_family.configure(text="\u25c2  Back to the faction")
            self.l_family.configure(text="")
        else:
            self.b_family.configure(text="\u25b8  Family tree%s" % (" of %s" % me if me else ""))
            self.l_family.configure(text="people, marriages, heirs, portraits - opens here in the form's place")

    def toggle_family(self):
        """Open the family tree in the form's place, or go back to the form."""
        self._family_open = not self._family_open
        if self._family_open:
            self._form_view.pack_forget()
            self._family_host.pack(fill="both", expand=True)
            self.family_editor.load()
        else:
            self._family_host.pack_forget()
            self._form_view.pack(fill="both", expand=True)
        self.show_family_button()

    def load_victory(self, faction):
        """The Victory block shows the faction's (a new one: its template's, which the clone copies) conditions."""
        from .wincond import read
        from .limits import game_kind
        try:
            cond = read(self.mod, self.v_campaign.get()).get(faction)
        except Exception:
            cond = None
        regions = [(r, (v.get("settlement") or "")) for r, v in sorted(self.regions.items())]
        regions += [(r["name"], r.get("settlement", "")) for r in self.new_regions]
        names = dict(self.mod.factions())
        factions = [(fb.name, names.get(fb.name, "")) for fb in (self.strat.factions if self.strat else [])]
        self.victory.load(cond, regions, factions, game_kind(self.mod) == "medieval2", faction)

    def _victory_changed(self):
        if self.victory.changed():
            self.status.set("Victory conditions changed - Preview, then %s." % (
                "Apply changes" if self.editing() else "Create faction"))
        self._mark_work()

    def pick_colour(self, which):
        c = colorchooser.askcolor(title=which + " colour")
        if c and c[0]:
            rgb = tuple(int(x) for x in c[0])
            self.colours[which] = rgb
            btn = self.b_primary if which == "primary" else self.b_secondary
            btn.configure(**colour_look(rgb))

    def _rename_painted(self):
        """Map > Edit regions > Rename...: the names players see of the region in 'Paint with' (right click one)."""
        region = self.v_paint.get().replace("  (new)", "").strip()
        if not region:
            messagebox.showerror(APP, "Right click a region on the map first (it goes into 'Paint with'), then "
                                      "Rename...")
            return
        self.new_region_dialog(edit=region)

    def _rename_painted_files(self):
        """Map > Edit regions > Rename in the files...: the names the files use for the region in 'Paint with'
        and its town, changed everywhere the mod names them (the Settlements tab's window)."""
        region = self.v_paint.get().replace("  (new)", "").strip()
        if not region:
            messagebox.showerror(APP, "Right click a region on the map first (it goes into 'Paint with'), then "
                                      "Rename in the files...")
            return
        from .gui_settlements import rename_in_files
        rename_in_files(self, region, self)

    def rename_town(self):
        """Rename... beside the town list: the region picked on the left (or a chosen town) in Edit region, whose
        first fields are the names players see of the region and its town."""
        region = (self.tv.selection() or [""])[0] or self.selected_town()
        if not region:
            messagebox.showerror(APP, "Pick a region in the list first (a click on its line), then Rename...")
            return
        self.new_region_dialog(edit=region)

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
            self.lb_build.insert("end", "%s%s%s%s" % (r, "  (-> %s)" % self.kinds[r] if r in self.kinds else "",
                                                    "  [%d buildings]" % n if r in self.buildings_picked
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
        n = len(self.chosen)
        self.lbl_towns.configure(text=("%d town(s): %s%s" % (n, ", ".join(self.chosen[:4]), " ..." if n > 4 else "")
                                       if n else "no town yet") + " - a click on a town on the Map gives or "
                                                                   "takes it")

    # ---- field armies, agents, fleets ----
    @property
    def AGENTS(self):
        """The mod's agent types (from descr_character.txt)."""
        return tuple(self.mod.agent_kinds()) if self.mod else ("spy", "assassin", "diplomat")

    def refresh_field(self, keep=None):
        self.lb_field.delete(0, "end")
        for c in self.field:
            xy = self.char_moves.get(c["cid"], c["xy"]) if c.get("existing") else c.get("xy")
            where = "%d, %d" % tuple(xy) if xy else "not placed"
            units = ("%d%s" % (len(c["units"]), " + guard" if c.get("named") else "")) \
                if c["kind"] in ("army", "fleet") else ""
            moved = c.get("existing") and c.get("cid") in self.char_moves
            tag = ("changed" if c.get("changed") or moved else "as it is") if c.get("existing") else "new"
            self.lb_field.insert("end", (c["kind"], c["name"], units, where, tag))
        if keep is not None and keep < len(self.field):
            self.lb_field.selection_set(keep)

    def field_on_map(self):
        """Double click in the list: the Map tab, centred on that army, agent or fleet."""
        i = self.selected_field()
        if i is None:
            return
        c = self.field[i]
        xy = self.char_moves.get(c["cid"], c["xy"]) if c.get("existing") else c.get("xy")
        if not xy:
            self.place_field()
            return
        self.select_tab("Map")
        self.show_map()
        self.update()
        self.map_view.centre_on(tuple(xy))

    def field_faction(self):
        return self.v["template"].get().strip()

    def add_field(self, kind, preset=None, then_place=False):
        """A small form: kind (agents), name from the faction's name list, age. preset: the agent picked;
        then_place: the next click on the Map puts the new one there (the legend's tools)."""
        if not self.mod or not self.field_faction():
            messagebox.showerror(APP, "load a mod and pick the %s first" % ("faction" if self.editing() else "template"))
            return
        pool = self.pool_for(self.field_faction())
        rebels = self.field_faction() == "slave"
        v_sub = tk.StringVar()
        if rebels:                    # a rebel has a sub_faction: its look and the list its name comes from
            from collections import Counter
            fb = self.strat.faction("slave") if self.strat else None
            seen = Counter(c.sub_faction for c in (fb.characters if fb else []) if c.sub_faction)
            v_sub.set(seen.most_common(1)[0][0] if seen else next(
                (n for n, _ in self.mod.factions() if n != "slave"), ""))
            pool = self.pool_for(v_sub.get())
        w = tk.Toplevel(self)
        w.title({"army": "New army", "fleet": "New fleet"}.get(kind, "New agent"))
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack()
        agent = kind not in ("army", "fleet")
        v_kind = tk.StringVar(value=(preset if preset in self.AGENTS else self.AGENTS[0]) if agent else kind)
        row = 0
        if rebels:
            ttk.Label(frm, text="Rebels of").grid(row=row, column=0, sticky="w")
            from .gui_util import FactionBox
            cb_sub = FactionBox(frm, v_sub, [n for n, _ in self.mod.factions() if n != "slave"], self.shown_names(),
                                state="readonly", width=24)
            cb_sub.grid(row=row, column=1, sticky="w")
            ttk.Label(frm, text="(sub_faction: their look, and the list their name comes from)",
                      foreground="#666").grid(row=row, column=2, sticky="w")
            row += 1
        if agent:
            ttk.Label(frm, text="Agent").grid(row=row, column=0, sticky="w")
            ttk.Combobox(frm, textvariable=v_kind, values=self.AGENTS, state="readonly", width=14).grid(
                row=row, column=1, sticky="w")
            row += 1
        ttk.Label(frm, text="Name" if agent else ("Admiral" if kind == "fleet" else "General")).grid(
            row=row, column=0, sticky="w")
        v_first, v_last, v_age = tk.StringVar(), tk.StringVar(), tk.StringVar(value="30")
        cb_first = ttk.Combobox(frm, textvariable=v_first, values=first_names(pool, v_kind.get()), width=16)
        cb_first.grid(row=row, column=1)

        cb_last = ttk.Combobox(frm, textvariable=v_last, values=[""] + pool.get("surnames", []), width=16)
        cb_last.grid(row=row, column=2)

        def kind_changed(*a):                 # a princess takes a woman's name, the others a man's
            nonlocal pool
            if rebels:
                pool = self.pool_for(v_sub.get())
                cb_last["values"] = [""] + pool.get("surnames", [])
            names = first_names(pool, v_kind.get())
            cb_first["values"] = names
            if v_first.get() and v_first.get() not in names:
                v_first.set("")
        v_kind.trace_add("write", kind_changed)
        v_sub.trace_add("write", kind_changed)
        row += 1
        ttk.Label(frm, text="Age").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v_age, width=5).grid(row=row, column=1, sticky="w")
        row += 1
        ttk.Label(frm, text="names come from the list of the faction picked in 'Rebels of'" if rebels else
                  "names come from the faction's name list", foreground="#666").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(4, 0))

        def ok():
            first = v_first.get().strip()
            if not first:
                messagebox.showerror(APP, "pick a first name", parent=w)
                return
            if pool and first not in first_names(pool, v_kind.get()):
                messagebox.showerror(APP, "'%s' is not in the faction's %s names - the game crashes on a name "
                                          "it has no string for" % (first, "women's" if v_kind.get() in FEMALE_KINDS
                                                                     else "men's"), parent=w)
                return
            full = (first + " " + v_last.get().strip()).strip()
            if full in self._faction_names():
                messagebox.showerror(APP, "%s already has someone called %s - the game skips a second one "
                                          "with the same name. Pick another name (or add a surname)."
                                     % (self.field_faction(), full), parent=w)
                return
            self.remember()
            self.field.append({"kind": v_kind.get(), "name": (first + " " + v_last.get().strip()).strip(),
                               "age": int(v_age.get()) if v_age.get().isdigit() else 30, "units": [], "xy": None,
                               **({"sub_faction": v_sub.get()} if rebels else {})})
            w.destroy()
            self.refresh_field(keep=len(self.field) - 1)
            self.load_field()
            if then_place:                         # the legend's tool: the next click on the map places it
                self._placing = len(self.field) - 1
                c = self.field[-1]
                self.status.set("Click the tile for %s %s (%s)." % (c["kind"], c["name"],
                                "sea" if c["kind"] == "fleet" else "land, or a town for an agent"))
                self.show_map()

        def cancel():
            w.destroy()
            if then_place:
                self.map_view.set_tool(None)
        w.protocol("WM_DELETE_WINDOW", cancel)
        bar = ttk.Frame(frm)
        bar.grid(row=row + 1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(bar, text="Add", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=cancel).pack(side="left", padx=4)

    def _faction_names(self):
        """Names the faction gives someone already or will: its characters and records in the file (Edit),
        the leader and heir typed on the Faction tab, the armies and agents placed here."""
        from .strat import faction_names
        names = set(faction_names(self.strat, self.field_faction())) if self.strat and self.editing() else set()
        for role in ("leader", "heir"):
            n = (self.v[role + "_first"].get().strip() + " " + self.v[role + "_last"].get().strip()).strip()
            if n:
                names.add(n)
        names |= {c["name"] for c in self.field}
        return names

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
        if c["kind"] not in ("army", "fleet"):
            self.garrison_editor.load(self.mod, self.field_faction(), "%s %s - an agent, no units" % (c["kind"], c["name"]),
                                      [], [], lambda t: None)
            return
        units = faction_units(self.mod, self.field_faction(), ships=c["kind"] == "fleet", mercs=True)
        own = [u for u in units if not set(u.ownership) <= {"slave"}]
        if c["kind"] == "fleet" and own and all(u.mercenary for u in own):
            self.garrison_editor.v_whose.set("own + mercenaries")     # many mods mark every ship a mercenary
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
        if self.tab_name() == "Map":
            self.show_map()                 # already there: no tab event, so refresh by hand
        else:
            self.select_tab("Map")
        self.status.set("Click the tile for %s %s (%s)." % (c["kind"], c["name"],
                        "sea" if c["kind"] == "fleet" else "land, or a town for an agent"))

    def load_garrison(self):
        """Open the selected town of the Units tab in the garrison editor."""
        sel = self.lb_units.curselection()
        if not sel or not self.mod or sel[0] >= len(self.chosen):
            return
        region = self.chosen[sel[0]]
        template = self._faction_for(region)
        if self._units_for != template:
            self._units_cache = faction_units(self.mod, template, mercs=True)
            self._units_for = template
        units = self._roster_units(self._units_cache)
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
            "religion": (v.get("religion") or None) if self._m2() else None,
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
            "art": dict(self.art_replace), "select_map": self.select_map_opts(),
            "figures": {k: list(v) for k, v in self.figures.items()},
            "regions": self._regions_opts(),
            "resources": self._resources_opts(),
            "names": self.name_list.get("(new)"),
            "kinds": {r: k for r, k in self.kinds.items() if r in self.chosen},
            "victory": self.victory.get(),
        }
        return v["template"], v["name"].lower(), opts

    def gather_edit(self):
        v = {k: x.get().strip() for k, x in self.v.items()}
        if not v["template"]:
            raise ValueError("pick the faction to edit")
        had = list((self.editing_now or {}).get("regions", []))
        if had and not self.chosen:
            raise ValueError("the faction would be left without towns - keep or give it at least one (a click on a town on the Map)")

        def person(role):
            if not v[role + "_first"]:
                return None
            return {"name": (v[role + "_first"] + " " + v[role + "_last"]).strip(),
                    "age": int(v[role + "_age"]) if v[role + "_age"].isdigit() else None}
        return v["template"], {
            "display_name": v["display_name"], "short_name": v["short_name"], "adjective": v["adjective"],
            "description": self.t_descr.get("1.0", "end").strip(),
            "long_description": self.t_long.get("1.0", "end").strip(),
            "religion": (v.get("religion") or None) if self._m2() else None,
            "primary_colour": self.colours["primary"], "secondary_colour": self.colours["secondary"],
            "ai": v["ai"], "denari": int(v["denari"]) if v["denari"].isdigit() else None,
            "playable": self.v_playable.get(),
            **{k: v[k] for k in self.extra_rows if k in (self.editing_now or {})},
            "take": [r for r in self.chosen if r not in had and not self._new_region(r)],
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
            "art": dict(self.art_replace), "select_map": self.select_map_opts(),
            "figures": {k: list(v) for k, v in self.figures.items()},
            "regions": self._regions_opts(),
            "resources": self._resources_opts(),
            "sizes": {r: dict(v) for r, v in self.sizes.items() if r in self.chosen},
            "buildings": {r: [list(x) for x in b] for r, b in self.buildings_picked.items()},
            "roster": dict(self.roster_set),
            "names": self.name_list.get(v["template"]),
            "kinds": {r: k for r, k in self.kinds.items() if r in self.chosen},
            "family": copy.deepcopy(self.family_set) if self.family_set else None,
            "victory": self.victory.get()}

    def _places(self):
        return [{"what": w, "region": r, "to": xy} for (w, r), xy in self.place_moves.items()]

    def map_only(self):
        """New faction mode with no faction named yet: the buttons write the map's changes alone."""
        return not self.editing() and not (self.v["template"].get().strip() and self.v["name"].get().strip())

    def update_actions(self):
        if getattr(self, "v_work", None) is not None and self.v_work.get() in ("units", "buildings"):
            p, a = "Preview changes", "Apply changes"
        elif self.editing():
            p, a = "Preview changes", "Apply changes"
        elif self.map_only():
            # no faction chosen yet: only the map's changes can be written - said beside the work
            # bar, the buttons keep their usual names (the user found "map changes" puzzling)
            p, a = "Preview changes", "Apply changes"
        else:
            p, a = "Preview changes", "Create faction"
        self.b_preview.configure(text=p)
        self.b_create.configure(text=a)
        if getattr(self, "lbl_work", None) is not None and getattr(self, "v_work", None) is not None:
            hint = ""                 # what each work is: in the work buttons' hover texts
            if self.v_work.get() == "new" and self.map_only():
                picked = self.v["template"].get().strip()
                hint = ("%s = template of a NEW faction. To change %s itself: Edit faction" % (picked, picked)
                        if picked else "")
            self.lbl_work.configure(text=hint)

    def make_plan(self):
        ed = self.editor()
        if ed is not None:
            return ed.make_plan()
        return self._faction_plan()

    # ---- what waits for Apply, across the faction tabs and both editors ----
    def faction_pending(self):
        """The faction tabs (New / Edit faction, the map) hold changes not written yet."""
        if not self.mod:
            return False
        if self.editing():
            base = getattr(self, "_baseline", None)
            if not self.editing_now or base is None:
                return False
            st = self._faction_state()
            # the faction just picked in the list is not a change of the one being edited
            st["fields"]["template"] = base["fields"]["template"]
            return st != base
        if self.map_only():
            return bool(self._places() or self._regions_opts() or self._resources_opts())
        return True

    def _faction_label(self):
        if self.editing():
            return "Edit faction %s" % self.v["template"].get().strip()
        if self.map_only():
            return "Map changes"
        return "New faction %s (from %s)" % (self.v["name"].get().strip(), self.v["template"].get().strip())

    def _faction_state(self):
        """What the Edit faction work has now: the kept state and every field of the Faction tab."""
        st = self.snapshot()
        st["fields"] = {k: v.get() for k, v in self.v.items()}
        st["texts"] = (self.t_descr.get("1.0", "end").strip(), self.t_long.get("1.0", "end").strip())
        st["colours"] = dict(self.colours)
        st["playable"] = self.v_playable.get()
        st["give"] = self.v_give.get()
        st["victory"] = self.victory.get()
        return st

    def pending_parts(self):
        """[(key, label)] of the work waiting for Apply, in the order it is written: the
        editors first (their changes sit on the file's lines as read), then the faction
        tabs (built from the files as the editors leave them)."""
        out = []
        for key, name in (("units", "Unit editor"), ("buildings", "Building editor"),
                          ("characters", "Character editor"), ("terrain", "Terrain editor")):
            ed = self.editors.get(key)
            if ed is not None and ed.mod is not None and ed.dirty():
                out.append((key, "%s: %d change(s)" % (name, ed.pending())))
        if self.faction_pending():
            out.append(("faction", self._faction_label()))
        return out

    def _part_plan(self, key):
        return self.editors[key].make_plan() if key in self.editors else self._faction_plan()

    def _mark_work(self):
        """A * on the work buttons that hold changes not written yet."""
        keys = {k for k, _ in self.pending_parts()} if self.mod else set()
        for val, b in getattr(self, "work_buttons", {}).items():
            base = self.WORK_TITLES[val]
            mine = val in keys or val == self.v_mode.get() and "faction" in keys
            b.configure(text=base + ("  *" if mine else ""))

    def _faction_plan(self):
        if self.map_only():
            places, regions, res = self._places(), self._regions_opts(), self._resources_opts()
            if not places and not regions and not res:
                picked = self.v["template"].get().strip()
                if picked:                  # a faction picked in New faction mode: most likely meant to be edited
                    raise ValueError(
                        "Nothing was written: you are in \"New faction\" (top left), where %s is only the "
                        "template a NEW faction is copied from.\n\n"
                        "- To change %s itself (its garrisons, towns, armies...): press \"Edit faction\" at the "
                        "top, pick %s there and make the changes again.\n"
                        "- To make a new faction from it: type the new faction's name on the Faction tab."
                        % (picked, picked, picked))
                raise ValueError("Nothing to write yet. Pick what to do at the top: \"Edit faction\" to change a "
                                 "faction, \"New faction\" to make one (template + name on the Faction tab), or "
                                 "move towns, paint regions or change resources on the Map.")
            mod = ModData(self.mod.data)
            plan = Plan(mod, "map", "map", {})
            from .mapedit import apply_places
            from .regionedit import apply_opts as apply_region_opts
            from .resources import apply as apply_resources
            if places:
                apply_places(plan, self.v_campaign.get(), places)
            if res:
                apply_resources(plan, self.v_campaign.get(), res)
            if regions:
                apply_region_opts(plan, self.v_campaign.get(), regions)
                # the campaign-select maps of the factions whose land changed follow the new borders
                if self.select_map_opts().get("on"):    # only when asked on the Art tab: the originals stay
                    from .factionart import redraw_map_changes
                    plan.opts["regions"] = regions
                    redraw_map_changes(plan, self.v_campaign.get())
            return plan
        if self.editing():
            if not self.mod:
                raise ValueError("load a mod first")
            faction, opts = self.gather_edit()
            return edit_faction(ModData(self.mod.data), self.v_campaign.get(), faction, opts)
        template, name, opts = self.gather()
        # a fresh read, so a previous preview's edits never leak in
        from .limits import LimitError
        if self._limit_raise == self.mod.data:
            opts["raise_faction_limit"] = True
        try:
            return build(ModData(self.mod.data), self.v_campaign.get(), template, name, opts)
        except LimitError as e:
            if not e.can_raise or not messagebox.askyesno(APP, "%s\n\nRaise it now? (written with the faction and "
                                                               "its backup; Restore takes it back)" % e):
                raise
            self._limit_raise = self.mod.data         # asked once per mod: Preview and Apply both use it
            opts["raise_faction_limit"] = True
            return build(ModData(self.mod.data), self.v_campaign.get(), template, name, opts)

    def events_window(self):
        """Tools > Events and later factions...: the campaign's descr_events.txt."""
        from .gui_events import open_events
        open_events(self)

    def traits_window(self):
        """Tools > Traits and retinue... (also in the Character editor): the traits and ancillaries themselves."""
        from .gui_traits import open_traits
        open_traits(self)

    def campaign_rules(self):
        """Tools > Campaign rules...: the campaign's settings files as plain values."""
        from .gui_rules import open_rules
        open_rules(self)

    def install_pack(self):
        """Tools > Check and install a pack...: a pack that says 'copy data over the game' checked file by file."""
        from .gui_modpack import open_pack
        open_pack(self)

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

    def game_manifest(self):
        """Fingerprint every file of the game (not of its mods) into rtw_manifest.json.gz."""
        start = game_of(self.mod.data) if self.mod else settings.get("game")
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
            self.status.set("Saved %s - press Check mod again." % path)
        ttk.Button(bar, text="Save", command=save).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)
        t.focus_set()

    def preview(self):
        parts = self.pending_parts()
        if len(parts) <= 1:
            try:
                plan = self._part_plan(parts[0][0]) if parts else self.make_plan()
            except Exception as e:
                messagebox.showerror(APP, str(e))
                return
            log.write("Preview\n" + plan.report())
            self.show_text("Preview - nothing written yet", plan.report())
            return
        out = []
        for key, label in parts:
            try:
                rep = self._part_plan(key).report()
            except Exception as e:
                rep = "cannot be written: %s" % e
            out.append("=" * 70 + "\n%s\n" % label + "=" * 70 + "\n" + rep)
        text = ("%d pieces of work wait for Apply; Apply writes them one after another, each with its own "
                "backup (the later ones are built on the files as the earlier leave them).\n\n" % len(parts)
                + "\n\n".join(out))
        log.write("Preview\n" + text)
        self.show_text("Preview - nothing written yet", text)

    def create(self):
        parts = self.pending_parts()
        if len(parts) <= 1:
            key = parts[0][0] if parts else None
            try:
                plan = self._part_plan(key) if key else self.make_plan()
            except Exception as e:
                messagebox.showerror(APP, str(e))
                return
            warn = "\n".join("- " + m for _, m in plan.warnings)
            msg = "Write %d file(s) and copy %d art item(s)?\nA backup is made first.%s" % (
                len(plan.changed_files()), len(plan.copies), ("\n\nWarnings:\n" + warn) if warn else "")
            if not messagebox.askyesno(APP, msg):
                return
            self._write([(key or "current", parts[0][1] if parts else "", plan)])
            return
        self._apply_dialog(parts)

    def _apply_dialog(self, parts):
        """Several pieces of work wait: tick which to write (all by default)."""
        w = tk.Toplevel(self)
        w.title("Apply changes")
        w.transient(self)
        frm = ttk.Frame(w, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Changes not written yet - Apply writes the ticked ones, one after another, each with "
                            "its own backup (Restore undoes each):", wraplength=560, justify="left").pack(anchor="w")
        picks = []
        for key, label in parts:
            v = tk.BooleanVar(value=True)
            try:
                plan = self._part_plan(key)
                note = "%d file(s)" % len(plan.changed_files()) + (
                    "; warnings: " + "; ".join(m for _, m in plan.warnings) if plan.warnings else "")
            except Exception as e:
                note = "cannot be written: %s" % e
                v.set(False)
            ttk.Checkbutton(frm, text=label, variable=v).pack(anchor="w", pady=(6, 0))
            ttk.Label(frm, text=note, foreground="#666", wraplength=540, justify="left").pack(anchor="w", padx=(24, 0))
            picks.append((key, label, v))

        def go():
            chosen = [(k, l) for k, l, v in picks if v.get()]
            w.destroy()
            if chosen:
                self._write([(k, l, None) for k, l in chosen])
        bar = ttk.Frame(frm)
        bar.pack(anchor="e", pady=(12, 0))
        ttk.Button(bar, text="Apply", command=go).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    def _write(self, parts):
        """Write [(key, label, plan or None)] in order; a plan left None is built just
        before it is written, on the files as the pieces before it left them."""
        done, failed, applied = [], None, set()
        for key, label, plan in parts:
            try:
                ed = self.editors.get(key)
                if ed is not None and ed.dirty() and ed._signature() != getattr(ed, "_sig", None):
                    raise ValueError("%s changed on the disk since the editor read it - its changes cannot be "
                                     "placed; they stay for you to redo" % os.path.basename(ed.path()))
                if plan is None:
                    plan = self._part_plan(key)
                bdir = plan.apply()
            except Exception as e:
                failed = "%s: %s" % (label or key, e)
                log.write("Writing failed: %s\n%s" % (failed, traceback.format_exc()))
                break
            applied.add(key)
            log.write("Written (backup %s)\n%s" % (bdir, plan.report()))
            done.append("%s%s\n\nBackup: %s" % (("=" * 70 + "\n%s\n" % label + "=" * 70 + "\n") if label and
                                                 len(parts) > 1 else "", plan.report(), bdir))
        for key in applied:                            # written: the editor starts clean on the new files
            if key in self.editors:
                self.editors[key].mod = None
        text = "\n\n".join(done)
        if failed:
            text = "Writing stopped - %s\n\n%s" % (failed, text or "nothing was written.")
            messagebox.showerror(APP, "Writing failed: %s" % failed)
        if done:
            text += "\n\nStart a NEW campaign to see the changes."
            self.show_text("Done" if not failed else "Written in part", text)
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
        faction = self.v["template"].get().strip()         # picked: where it is named goes into the report too

        def work():
            try:
                result["text"] = check_mod(ModData(data), campaign, deep=deep,
                                           progress=lambda m: result.__setitem__("step", m))
                if faction:
                    result["step"] = "where %s is named..." % faction
                    result["text"] += "\n\n" + "=" * 70 + "\nWHERE %s IS NAMED (every text file of the mod)\n\n" \
                        % faction + scan_mod(ModData(data), faction, campaign).report()
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
            self.show_text("Check mod" + (" (and where %s is named)" % faction if faction else ""), result["text"],
                           extra=[("Ignore list...", self.edit_ignore)] if faction else ())
        wait()

    def _log_status(self):
        """Status lines go to the log, but one of a kind in a row (painting sends many).
        The work buttons' * (changes waiting) is brought up to date soon after."""
        if not getattr(self, "_mark_queued", False):
            self._mark_queued = True

            def mark():
                self._mark_queued = False
                try:
                    self._mark_work()
                except Exception:
                    pass
            self.after(300, mark)
        text = self.status.get()
        shape = re.sub(r"\d+", "#", text)
        if text and shape != getattr(self, "_last_status_shape", None):
            log.write(text)
        self._last_status_shape = shape

    def show_log(self):
        """The tool's log - send faction_tool.log along with the game's system.log.txt."""
        self.show_text("Log - %s" % (log.path() or "no log file"), log.tail() or "(empty)",
                       extra=[("Save logs (zip)...", self.save_logs), ("Report a bug...", self.send_report)])

    def send_report(self, message="", kind="bug"):
        """A bug (with the logs, anonymised) or an idea to the author in one click (gui_report, report)."""
        from .gui_report import open_report
        return open_report(self, message, kind)

    def save_logs(self):
        """One zip for a report: the tool's log and the game's (system.log.txt, the
        newest REX crash report), found from the loaded mod's game folder."""
        game = mod_dir = None
        if self.mod:
            game = game_of(self.mod.data)                    # Medieval II: <game>/mods/<mod>/data
            mod_dir = os.path.dirname(os.path.abspath(self.mod.data))
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.basename(mod_dir) if mod_dir else "tool"
        # into the tool's own folder (RTW-M2TW-Campaign-Editor-files/logs next to the exe), not the game's
        where = log.logs_dir() or mod_dir or ""
        try:
            os.makedirs(where, exist_ok=True)
        except OSError:
            where = mod_dir or ""
        out = filedialog.asksaveasfilename(title="Save the logs", defaultextension=".zip",
                                           initialdir=where, initialfile="%s_logs_%s.zip" % (base, stamp),
                                           filetypes=[("Zip", "*.zip")])
        if not out:
            return
        try:
            names = log.pack(out, game, mod_dir)
        except OSError as e:
            messagebox.showerror(APP, "Could not write %s: %s" % (out, e))
            return
        missing = []
        if not any(n.endswith("system.log.txt") for n in names):
            missing.append("no system.log.txt (the game writes it in its folder%s)" % (
                ": %s" % game if game else "; load the mod first"))
        if not any(n.startswith("reports/") for n in names):
            missing.append("no crash report in reports (fine if the game did not crash, or runs without REX)")
        log.write("Logs saved to %s: %s" % (out, ", ".join(names)))
        messagebox.showinfo(APP, "Saved %s\n\n%s%s\n\nYour names are cut out of the logs. Send this file - or use "
                                 "Report a bug / Suggest, which sends it in one click." % (
            out, "\n".join(names) or "(nothing found)", ("\n\n" + "\n".join(missing)) if missing else ""))

    def report_callback_exception(self, exc, val, tb):
        """A crash inside the window: logged with its traceback and shown, never silent."""
        text = "".join(traceback.format_exception(exc, val, tb))
        log.write("ERROR (unexpected)\n" + text)
        if messagebox.askyesno(APP, "Something went wrong: %s\n\nThe details are in the log. Send a report to the "
                                    "author now (the logs, with your names cut out - you see it before it goes)?"
                               % val, icon="error"):
            self.send_report("The editor showed: %s\n\nWhat I did just before:\n" % val)

    def restore(self):
        if not self.mod:
            return
        bs = backups(self.mod)
        if not bs:
            messagebox.showinfo(APP, "No backups yet.")
            return
        w = tk.Toplevel(self)
        w.title("Restore a backup")
        ttk.Label(w, justify="left", text="Newest first. Pick the change to go back to: it and every change made "
                  "after it are undone in one go,\nnewest first. Pick the lowest line to get the files back as they "
                  "were before the tool's first write.").pack(anchor="w", padx=6, pady=(6, 0))
        lb = tk.Listbox(w, width=90, height=14, selectmode="browse")
        for b in bs:
            lb.insert("end", backup_label(b))
        lb.pack(fill="both", expand=True, padx=6, pady=6)
        info = ttk.Label(w, text="")
        info.pack(anchor="w", padx=6)

        def picked(_e=None):
            sel = lb.curselection()
            lb.selection_clear(0, "end")
            if sel:
                lb.selection_set(0, sel[0])             # show every change that will be undone
                n = sel[0] + 1
                info.configure(text="%d change%s will be undone." % (n, "" if n == 1 else "s"))
        lb.bind("<<ListboxSelect>>", picked)

        def go():
            sel = lb.curselection()
            if not sel:
                return
            b = bs[max(sel)]
            n = bs.index(b) + 1
            text = ("Undo %s?" % backup_label(b) if n == 1 else
                    "Undo %d changes, from the newest back to\n%s?" % (n, backup_label(b)))
            if not messagebox.askyesno(APP, text + "\nFiles are put back as they were before it."):
                return
            ms = restore_to(self.mod, b)
            back = sum(len(m["modified"]) for m in ms)
            gone = sum(len(m["created"]) for m in ms)
            log.write("Restored %d backup(s) down to %s: %d file(s) back, %d copied item(s) removed"
                      % (len(ms), b, back, gone))
            messagebox.showinfo(APP, "Undid %d change%s: %d file(s) put back, %d copied item(s) removed."
                                % (len(ms), "" if len(ms) == 1 else "s", back, gone))
            w.destroy()
            self.load()
        ttk.Button(w, text="Undo back to here", command=go).pack(pady=(0, 6))

def main():
    log.write("Start %s" % APP)
    App().mainloop()
