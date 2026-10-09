"""The window: pick the mod, fill in the faction, preview, create, restore."""

import copy
import datetime
import os
import re
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from .gui_util import right_click
from .gui_util import ask, ask_choice
from .gui_util import scroll_body
from . import emergence as EM, log, settings, theme
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

VERSION = "0.33.0"
KOFI = "https://ko-fi.com/pfadfinder"
DISCORD = "https://discord.gg/uqA9MEn4Z"
YOUTUBE = "https://www.youtube.com/channel/UC8j5rv6mTmtvRR8u7NmaCvQ"
APP = "RTW & M2TW Campaign Editor"
# Tools > the author's stress test (selftest.py) - said plainly that modders do not need it
TEST_MOD_LABEL = "Test mod - every feature (for the author, a stress test)..."
TEST_MOD_HINT = ("For the author: a script that does everything the editor can do, to stress-test the editor and "
                 "then try it all in the game. You do not need it.")

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
                                  and the Map editor's Terrain tab (ground, rivers, climates, heights)
  a building / garrisons in many  Many towns... (top row), or the Map:
    towns at once ............... Select, drag a box (left button), right click
  join two regions into one ..... Map: Merge regions - the one that stays, then the one that goes
  grow or cut the map ........... Map: Change size... under the map - drag its edges out (sea)
                                  or in (cut); Bigger map (x3)... for 3 x the tiles
  change a unit or a building ... Unit editor / Building editor
  make a new unit or building ... Unit / Building editor: New unit (New building) step by step...
  change a unit's look .......... Unit editor: Battle model - View in 3D..., Replace model...
  hear a unit, give it a voice .. Unit editor: Voice in battle - Play, Put in my own...
  edit characters and families .. Character editor (or the Faction tab in Edit faction)
  put in a mod made by others ... Tools > Check and install a pack...
  change the campaign's rules ... Campaign rules... (top row): ages, agents, towns, diplomacy, unit sizes
  add a religion ................ Religions > New religion... (Medieval II; Rome has no religions)
  add Sack Settlement ........... Add-ons (Rome + REX): who may sack, reward, what stays standing
  make your own script, no code . Module builder... (top row; REX / M2EX): WHEN something happens, IF ...,
                                  DO ... - picked from lists; nine examples to start from
  rename a region or its town ... Edit region... (Map, or Rename... beside the towns list): the names
                                  players see and the names in the files (changed everywhere)
  make a copy of the mod to work on  New mod folder... (the base mod stays untouched)

START
  0. Best: the exe in the game's folder (beside RomeTW.exe / medieval2.exe) - then the Mod list shows every mod
     of the game at once. Started elsewhere, it offers to put itself there (you pick the game's folder).
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
               left drag moves characters, towns and ports, right drag moves the map;
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
  portraits the game shows: names, ages, traits, ancillaries; Add a person (step by step: who to whom).
  Portrait library...: every portrait of a culture; Add portraits... puts new ones in.

TERRAIN EDITOR
  Paint the campaign map tile by tile: Ground (fertile land, forest, hills, mountains, swamp,
  seas), Rivers, fords, cliffs, Climates, and Heights (a brush like a spray can: raise, lower,
  smooth, level). Left drag paints, right click picks a tile's own, right drag moves the map.
  Nothing the game refuses is put under a town, port or army. The game rebuilds its map on
  the next start.

TOOLS
  Tools > Check mod files (was Check mod): reads every file of the mod and says in plain words what the game
  would stumble on (missing pictures, broken lines, crash rules). With a faction picked it also lists every place the faction is named (game, REX and mod files told apart).
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
    words and screenshots go to the author in one click, no account needed. The author's answer comes back
    to its tab Answers to my reports ("(1 new)" on the button) - reply there with Send the answer.
    Log / Save logs (zip): the same zip to send yourself.
  Start the game (green, beside Tools): the game with the loaded mod - its own start script, else the
    engine's line (REX -mod:<name>, M2EX --features.mod=mods/<name>). Apply your changes first.

KEYS
  Ctrl+Z undo, Ctrl+Y redo    Ctrl+P preview    Ctrl+S apply    F5 load again    F1 this help
  Ctrl+1 .. Ctrl+5 the tabs    Map: wheel zooms, right drag moves the map, left drag moves a marker

THE GAMES
  Rome: Total War, Barbarian Invasion, Alexander - plain or with REX.
  Medieval II and Kingdoms - plain or with M2EX (a plain game from Steam is unpacked by the
  tool on Load, with your yes). Limits of the original games apply only without REX / M2EX.

SUPPORT
  The tool is free. If it helps you, a coffee keeps new features coming:
  https://ko-fi.com/pfadfinder  (the Support me on Ko-fi button)
"""

_showerror = messagebox.showerror


def _logged_error(title=None, message=None, **kw):
    """Every error box also goes to the log (CampaignEditor.log). A refusal in plain words (the editor's own
    ValueError: 'it would run twice', 'no men's names') is one line, not an ERROR with a traceback - those read as a
    crash in a report (a tester's note on 0.32.0)."""
    exc = sys.exc_info()
    if isinstance(exc[1], ValueError):
        last = traceback.extract_tb(exc[2])[-1] if exc[2] else None
        log.write("Refused: %s%s" % (message, "  (%s line %d)" % (os.path.basename(last.filename), last.lineno)
                                     if last else ""))
    else:
        log.error(message)
    return _showerror(title, message, **kw)


messagebox.showerror = _logged_error

# descr_strat.txt: "faction <name>, <economy> <military>" - the words the game knows
AI_ECONOMY = ("balanced", "bureaucrat", "comfortable", "craftsman", "fortified", "religious", "sailor", "trader")
AI_MILITARY = ("caesar", "genghis", "henry", "mao", "napoleon", "smith", "stalin")
AI_CHOICES = ["%s %s" % (e, m) for e in AI_ECONOMY for m in AI_MILITARY]
# New faction: how it comes into the campaign (emergence.WAYS in this order)
WAY_LABELS = ("on the map from the start", "later, by an event (a date and a region)",
              "later, as the shadow of a faction (its civil war)", "later, splitting off a faction in a revolt")
WAY_KEYS = ("map", "event", "shadow", "revolt")


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
        ttk.Label(bar, text="Search").pack(side="left", padx=(8, 0))
        self.v_find = tk.StringVar()
        self.v_find.trace_add("write", lambda *a: self._draw())
        ttk.Entry(bar, textvariable=self.v_find, width=14).pack(side="left", padx=4)
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
        self.tv.tag_configure("new", foreground=theme.ink("#0050c0", "field"))
        self.tv.tag_configure("changed", foreground=theme.ink("#a05000", "field"))
        self.rows, self.sort = [], None          # [values], (column, reverse)
        self.finds = {}                          # id(row) -> more text the Search matches (unit names)

    def _shown(self, values):
        want = self.v_show.get()
        kind = values[0]
        find = self.v_find.get().strip().lower()
        if find and not any(find in str(v).lower() for v in values[:-1]) \
                and find not in self.finds.get(id(values), ""):
            return False
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
        self.rows, self.finds = [], {}
        self.tv.delete(*self.tv.get_children())

    def insert(self, _where, values, find=""):
        self.rows.append(values)
        self.finds[id(values)] = find.lower()
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
FIELD_W = 44                     # characters: the Faction tab's short fields (names, AI, capital...)


def assets_dir():
    """The tool's own pictures (assets/ in the source, 'assets' inside the exe)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


class App(tk.Tk):
    def __init__(self):
        from .gui_util import unique_tcl_names
        unique_tcl_names()                        # before the first callback is registered
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
        self.removed_existing = []      # Edit: [{name, from}] characters taken off the map
        self.place_moves = {}           # {('city' | 'port', region): (x, y)} towns and ports moved on the map
        self.ports_gone = []            # regions whose port is taken off the map (right click > Delete the port)
        # the Map's changes for any faction (not only the one made or edited): towns given {region: new owner},
        # armies / agents / fleets placed {faction: [character dicts]} - written with the next Apply
        self.map_owners, self.map_chars, self.map_removed = {}, {}, {}
        self.map_moves, self.map_units = {}, {}          # the Map editor: any faction's characters moved, units
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
        from .gui_hovercard import install as hover_cards
        hover_cards(self, lambda: getattr(self, "mod", None), self.pictures, culture=self._picked_culture)   # a unit / building in any list shows its card
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

    def _picked_culture(self):
        """The culture of the faction picked in the window now (None when none is)."""
        try:
            t = self.v["template"].get().strip()
            return self.mod.culture(t) if t and self.mod else None
        except Exception:
            return None

    def _build(self):
        theme.apply(self)                          # light or dark, as last chosen
        from .gui_util import install_window_helpers
        install_window_helpers(self)               # windows centred, wide drop-downs, long field texts on hover
        pad = {"padx": 6, "pady": 3}
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Mod").pack(side="left")
        # the mods of the game folder last used; picking one loads it
        self.v_modpick = tk.StringVar()
        self.cb_mods = ttk.Combobox(top, textvariable=self.v_modpick, state="readonly", width=20)
        self.cb_mods.pack(side="left", padx=(4, 8), fill="x", expand=True)   # Mod and data folder: the same width,
        #                                                   sharing the free room half and half (the user, 2026-10-07)
        self.cb_mods.bind("<<ComboboxSelected>>", lambda e: self.mod_picked())
        self._mods = []
        ttk.Label(top, text="data folder").pack(side="left")
        self.v_path = tk.StringVar()
        e_path = ttk.Entry(top, textvariable=self.v_path, width=20)    # the whole path shows on hover
        e_path.pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(top, text="Browse...", command=self.browse).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(top, text="Load", command=self.load_clicked).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(top, text="New mod folder...", command=self.new_mod).pack(side="left", padx=(0, theme.BUTTON_GAP))
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
        self.b_theme.pack(side="right", padx=(theme.BUTTON_GAP, 0))
        self.work_row = HScroll(work)
        self.work_row.pack(side="left", fill="x", expand=True)
        self.v_work = tk.StringVar(value="new")
        self.work_buttons = {}
        for val, text in self.WORK_TITLES.items():
            if val == "terrain":
                continue                                 # a tab of the Map editor now, not a work of its own
            b = ttk.Radiobutton(self.work_row.inner, text=text, value=val, variable=self.v_work, style="Toolbutton",
                                command=self.work_changed, cursor="hand2")   # a button like every other one
            b.pack(side="left", padx=(0, theme.BUTTON_GAP))
            self.work_row.grab(b)
            self.work_buttons[val] = b
            tip(b, self.WORK_HINTS.get(val, ""))         # what each work is: shown on hover, takes no room
        # the tools with a window of their own, beside the works (they were in Tools: a tester wanted them in
        # sight, one press away); the row scrolls when the window is narrower - drag it with the left button
        ttk.Separator(self.work_row.inner, orient="vertical").pack(side="left", fill="y", padx=(0, theme.BUTTON_GAP),
                                                                    pady=2)
        for key, text, method, hint_text in self.WINDOW_BUTTONS:
            b = ttk.Button(self.work_row.inner, text=text, cursor="hand2",
                           command=self.once(method, lambda m=method: getattr(self, m)()))
            b.pack(side="left", padx=(0, theme.BUTTON_GAP))
            self.work_row.grab(b)
            tip(b, hint_text)
        tip(self.b_theme, "light or dark window")
        self.work_row.pack_configure(expand=False)
        # under them only a warning that needs to be seen (New faction with a faction picked), on a line of its own
        # that wraps - beside the work buttons it was cut to a few letters in a narrow window
        self._work_frame = work
        self.lbl_work = ttk.Label(self, text="", foreground="#555", justify="left")
        self.lbl_work.bind("<Configure>", lambda e: self.lbl_work.configure(wraplength=max(120, e.width - 4)),
                           add="+")
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
        # two columns (a tester: fields of a few words took a whole line): the faction's short fields on the left,
        # leader / heir and victory beside them, the long texts below across the whole width
        upper = ttk.Frame(left)
        upper.pack(fill="x")
        lf = self.lf = ttk.LabelFrame(upper, text="New faction")
        lf.grid(row=0, column=0, sticky="nw")
        side = ttk.Frame(upper)
        side.grid(row=0, column=1, sticky="nwe", padx=(8, 0))
        upper.columnconfigure(1, weight=1)
        texts = ttk.Frame(left)
        texts.pack(fill="x", pady=(6, 0))
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
            widget.grid(row=row, column=1, sticky="w", padx=4, pady=2)
            if isinstance(widget, ttk.Entry):
                widget.configure(width=FIELD_W)
            elif isinstance(widget, ttk.Combobox) and int(str(widget.cget("width") or 0)) < FIELD_W - 2:
                widget.configure(width=FIELD_W - 2)
            row += 1
        from .gui_util import FactionBox
        self.cb_template = FactionBox(lf, self.v["template"], state="readonly", width=28)
        self.cb_template.bind("<<ComboboxSelected>>", lambda e: self.template_changed())
        field("Template (copied)", self.cb_template)
        self.lbl_template = lf.grid_slaves(row=row - 1, column=0)[0]
        self.e_name = ttk.Entry(lf, textvariable=self.v["name"])
        field("Internal name", self.e_name)
        self.b_rename = ttk.Button(lf, text="Rename...", command=self.rename_faction)   # Edit faction only
        self.b_rename.grid(row=row - 1, column=2, sticky="w")
        self.b_rename.grid_remove()
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
        self.b_primary = ttk.Button(cf, text="primary", width=10, command=lambda: self.pick_colour("primary"))
        self.b_primary.pack(side="left", padx=(0, theme.BUTTON_GAP))
        self.b_secondary = ttk.Button(cf, text="secondary", width=10, command=lambda: self.pick_colour("secondary"))
        self.b_secondary.pack(side="left", padx=(0, theme.BUTTON_GAP))
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
        # how it comes into the campaign: on the map from the start, or later (emergent / shadow / split-off -
        # emergence.py); later = no towns, no leader, dead at the start
        from .emergence import HOW
        self.v_way = tk.StringVar(value=WAY_LABELS[0])
        self.v_way_of, self.v_way_date, self.v_way_region = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.v_way_back = tk.BooleanVar(value=True)
        wf = ttk.Frame(lf)
        self.cb_way = ttk.Combobox(wf, textvariable=self.v_way, state="readonly", values=WAY_LABELS, width=FIELD_W - 6)
        self.cb_way.pack(side="left")
        self.cb_way.bind("<<ComboboxSelected>>", lambda e: self.way_changed())
        from .gui_util import hint
        hint(wf, HOW, width=560).pack(side="left")
        field("Comes into the campaign", wf)
        self.way_row = [wf, lf.grid_slaves(row=row - 1, column=0)[0]]
        self.way_more = ttk.Frame(lf)
        self.way_more.grid(row=row, column=1, sticky="w", padx=4)
        row += 1
        self.way_parts = {}
        p = ttk.Frame(self.way_more)
        ttk.Label(p, text="date").pack(side="left")
        ttk.Entry(p, textvariable=self.v_way_date, width=10).pack(side="left", padx=(2, 6))
        ttk.Label(p, text="in the rebel region").pack(side="left")
        self.cb_way_region = ttk.Combobox(p, textvariable=self.v_way_region, state="readonly", width=22)
        self.cb_way_region.pack(side="left", padx=2)
        self.way_parts["event"] = p
        p = ttk.Frame(self.way_more)
        self.l_way_of = ttk.Label(p, text="of")
        self.l_way_of.pack(side="left")
        self.cb_way_of = FactionBox(p, self.v_way_of, state="readonly", width=24)
        self.cb_way_of.pack(side="left", padx=2)
        self.way_parts["of"] = p
        self.chk_way_back = ttk.Checkbutton(self.way_more, text="may come back after it dies (re_emergent)",
                                            variable=self.v_way_back)
        self.l_way_note = ttk.Label(self.way_more, foreground="#666", wraplength=330, justify="left", text=(
            "It starts dead: no towns, no leader, only its money (towns, armies and the leader above are not "
            "used); nonplayable."))
        self.way_changed()
        ttk.Label(texts, text="Tooltip\n(faction icon)").grid(row=0, column=0, sticky="nw", padx=4)
        self.t_descr = tk.Text(texts, width=34, height=2, wrap="word")
        self.t_descr.grid(row=0, column=1, sticky="we", padx=4, pady=2)
        self.rome_rows += [texts.grid_slaves(row=0, column=c)[0] for c in (0, 1)]
        ttk.Label(texts, text="Full description\n(campaign screen)").grid(row=1, column=0, sticky="nw", padx=4)
        self.t_long = tk.Text(texts, width=34, height=7, wrap="word")
        self.t_long.grid(row=1, column=1, sticky="we", padx=4, pady=2)
        texts.columnconfigure(1, weight=1)

        # --- leaders
        lf2 = self.lf2 = ttk.LabelFrame(side, text="Leader and heir (names come from the faction's name list)")
        lf2.pack(fill="x")
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
        self.victory = VictoryBox(side, on_change=self._victory_changed, before=self.remember)
        self.victory.app = self                 # its region lists can be picked on the map
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
        self.v_brush.trace_add("write", lambda *_: self._brush_changed())     # typed too, not only the arrows
        ttk.Spinbox(rb, from_=1, to=6, width=3, textvariable=self.v_brush,
                    command=lambda: setattr(self.map_view, "brush", self.v_brush.get())).pack(side="left")
        ttk.Button(rb, text="New region...", command=self.new_region_dialog).pack(side="left", padx=(12, theme.BUTTON_GAP))
        ttk.Button(rb, text="Edit region...", command=lambda: self.new_region_dialog(
            edit=self.v_paint.get().replace("  (new)", "").strip())).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(rb, text="Place its town", command=lambda: self.region_point("city")).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(rb, text="Place its port", command=lambda: self.region_point("port")).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(rb, text="Delete this new region", command=self.drop_region).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(rb, text="Religions...", command=self.religions_dialog).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(rb, text="New religion...", command=self.new_religion_dialog).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(rb, text="Names by culture...", command=lambda: self.culture_names_dialog(
            self.v_paint.get().replace("  (new)", "").strip())).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Label(rb, text="left drag paints, right click picks a region, right drag moves the map",
                  foreground="#666").pack(side="left", padx=10)
        flow(rb)
        # Edit resources: a bar (type, Place new, Delete picked) with its how-to under it
        self.res_bar = ttk.Frame(tab, padding=(0, 0, 0, 4))
        xb = ttk.Frame(self.res_bar)
        xb.pack(fill="x")
        ttk.Label(xb, text="Resource", font=("", 9, "bold")).pack(side="left")
        self.v_res_type = tk.StringVar()
        self.cb_res_type = ttk.Combobox(xb, textvariable=self.v_res_type, width=16, state="readonly")
        self.cb_res_type.pack(side="left", padx=4)
        ttk.Button(xb, text="Place new", command=lambda: self.res_place_new(self.v_res_type.get())).pack(
            side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(xb, text="Delete picked", command=self.res_delete).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(xb, text="Region tags (hidden resources)...", command=self.region_tags_dialog).pack(
            side="left", padx=(0, theme.BUTTON_GAP))
        flow(xb)
        self._how(self.res_bar, "New: pick the resource above, press Place new, then click a land tile on the map.  "
                                "Move: drag a resource.  Remove: click it, then Delete "
                                "picked.  A region's resources are the ones on its land.")
        from .forts import KINDS as FORT_KINDS
        self.v_fort_type = tk.StringVar(value=FORT_KINDS[0])   # forts: no bar - the legend and the right click
        self.map_view = MapView(tab, on_layers=lambda: self.show_map())
        self.map_view.on_menu = self.map_menu
        self.map_view.on_town = self.town_window          # a double click: the town's own window
        self.map_view.on_char_double = self.char_window   # ... an army or fleet: its units
        self.map_view.on_fort_double = self.fort_window   # ... a fort: the army in it
        self.map_view.on_wonder = lambda t: __import__("campaign_editor.gui_wonders", fromlist=["show"]).show(self, self.mod, t)
        self.map_view.on_pick_menu = self.pick_menu
        self.map_view.on_tool = self.map_tool
        self.map_view.on_resize = self.map_size_window    # Change size... beside the map's size
        self.v_borders = self.map_view.v_borders
        self.map_view.pack(fill="both", expand=True)
        self.map_view.on_stroke = self.remember
        self._cmap, self._cmap_for = None, None
        # the Terrain editor: a tab of the Map editor beside its Map (once a work of its own on the top row - the
        # author: no sense keeping it up there), made the first time it is opened
        self.terrain_tab = ttk.Frame(self.nb, padding=0)
        self.nb.add(self.terrain_tab, text="  Terrain  ")
        self.nb.hide(self.terrain_tab)                  # shown with the Map editor (_map_tab_only)
        # everything of map_heights - Land and sea (the coast) and Heights - in a tab of its own (the user, 2026-10-09:
        # the Terrain panel had grown too fat); the same Terrain editor shows its other half there: one Undo, one Apply
        self.heights_tab = ttk.Frame(self.nb, padding=0)
        self.nb.add(self.heights_tab, text="  %s  " % self.HEIGHTS_TAB)
        self.nb.hide(self.heights_tab)
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
        srow = ttk.Frame(self)
        srow.pack(side="bottom", fill="x", padx=6, pady=(0, 6), before=self.nb)
        # right after a write: 'Undo this write' beside the message (NN/g: an easy way back, like 'Undo Send')
        self.b_undo_write = ttk.Button(srow, text="Undo this write", command=self.undo_write)
        self._undo_bdir = None
        from . import plan as _plan
        _plan.WRITTEN.append(lambda bdir, p: self.after_idle(lambda: self._written(bdir, p)))
        _plan.BEFORE.append(self._own_folder_first)
        self._own_folder_asked = set()
        self.status_line = ttk.Label(srow, anchor="w", justify="left")
        self.status_line.pack(side="left", fill="x", expand=True)
        # long work (over a second or two): a moving bar and the seconds beside the message (NN/g: feedback while
        # waiting - without it the window looks broken; Windows even calls it 'not responding')
        self.busy_bar = ttk.Progressbar(srow, mode="indeterminate", length=120)
        # a long message wraps onto a second line instead of running off the window's edge
        self.status_line.bind("<Configure>", lambda e: self.status_line.configure(wraplength=max(e.width - 4, 200)))
        self.bottom_bar = ttk.Frame(self)
        self.bottom_bar.pack(side="bottom", fill="x", before=self.nb, **pad)
        # the writing buttons on the left, the rest on the right; a window too narrow for one row wraps them button by
        # button onto the next rows (gui_util.flow) - never one over another, never one hidden past the edge
        bar = self.bottom_bar
        self.b_preview = ttk.Button(bar, text="Preview changes", command=self.preview)
        self.b_preview.pack(side="left", padx=(0, theme.BUTTON_GAP))
        self.b_create = ttk.Button(bar, text="Create faction", command=self.create)
        self.b_create.pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(bar, text="Undo", command=self.undo).pack(side="left", padx=(0, theme.BUTTON_GAP))
        ttk.Button(bar, text="Redo", command=self.redo).pack(side="left", padx=(0, theme.BUTTON_GAP))
        # the right side, packed from the right edge: Ko-fi last on the screen; each link in its own colour (Ko-fi's
        # coral, Discord's blue, YouTube's red, GitHub's grey - white words in either look), a button like the others
        links = []
        for text, style, url, say in (
                ("\u2615 Support me on Ko-fi", "Kofi.TButton", KOFI, "Donations keep the work on the editor going."),
                ("YouTube", "YouTube.TButton", YOUTUBE, "The editor's videos: what it does and how."),
                ("Discord", "Discord.TButton", DISCORD, "Our Discord server: questions, help, ideas and news."),
                ("GitHub", "GitHub.TButton", None, "The editor's page: downloads, the changes of every version, "
                                                   "the wiki. When a newer version is out, it turns green with its number.")):
            b = ttk.Button(bar, text=text, style=style, cursor="hand2",
                           command=self.support if url == KOFI else (lambda u=url: self.open_link(u)) if url
                           else self.open_github)
            b.pack(side="right", padx=(theme.BUTTON_GAP, 0))
            links.append((b, say))
        self.b_github = links[-1][0]
        self.b_report = ttk.Button(bar, text="Report a bug / Suggest", command=self.once("report", self.send_report))
        self.b_report.pack(side="right", padx=(theme.BUTTON_GAP, 0))
        tools = ttk.Menubutton(bar, text="Tools")
        menu = tk.Menu(tools, tearoff=False)
        # grouped by what one comes for, each group under a grey heading (not a junk drawer of everything)
        def head(text):
            menu.add_separator()
            menu.add_command(label=text, state="disabled")
        menu.add_command(label="Settings...", command=self.once("settings_window", self.settings_window))
        menu.add_command(label="Help", command=self.once("show_help", self.show_help))
        head("Find what is wrong")
        menu.add_command(label="Check mod files (what the game would stumble on)", command=self.once("check", self.check))
        menu.add_command(label="The game's log in plain words (what went wrong in the game)...",
                         command=self.once("game_log_window", self.game_log_window))
        menu.add_command(label=TEST_MOD_LABEL, command=self.once("test_mod", self.test_mod))
        head("Files and backups")
        menu.add_command(label="Restore a backup...", command=self.restore)
        menu.add_command(label="Check and install a pack...", command=self.once("install_pack", self.install_pack))
        menu.add_command(label="Game manifest...", command=self.once("game_manifest", self.game_manifest))
        head("About the editor")
        menu.add_command(label="Log", command=self.once("show_log", self.show_log))
        menu.add_command(label="Save logs (zip)...", command=self.once("save_logs", self.save_logs))
        menu.add_command(label="Credits (who made it with us)...", command=self.once("credits", self.credits_window))
        menu.add_separator()
        menu.add_command(label="Delete this mod's folder...", command=self.delete_mod,
                         foreground=theme.ink("#c00000"))       # red: it deletes for good (asked twice)
        # a menu entry has no hover box: the status line says what it is while the mouse is on it
        menu.bind("<<MenuSelect>>", lambda e, m=menu: self._menu_hint(m))
        tools["menu"] = menu
        tools.pack(side="right", padx=(theme.BUTTON_GAP, 0))
        # the game with the loaded mod, one press away - in sight beside Tools, green, a button like the others
        play = ttk.Button(bar, text="\u25b6 Start the game", command=self.start_game, style="Play.TButton",
                          cursor="hand2")
        play.pack(side="right", padx=(theme.BUTTON_GAP, 0))
        self.play_button = play
        flow(bar)
        from .gui_util import tip
        for b, say in links:
            tip(b, say + " Opens in your browser.")
        tip(play, "Starts the game with the mod that is loaded - the button names it (amber when no mod is loaded: "
                  "the game's own campaign starts): its own start script (New mod folder writes "
                  "Start_<name>.bat), else the line the engine's own start scripts use (REX.exe -mod:<name>, "
                  "M2EX.exe --features.mod=mods/<name>). Apply your changes first - the game reads the files on disk.")
        self.status = tk.StringVar(value="Pick the Mod, or Browse... to its data folder (for example ...\\HLR\\data) "
                                         "and press Load.")
        self.status_line.configure(textvariable=self.status)
        self.status.trace_add("write", lambda *a: self._log_status())
        for k in ("name", "template"):
            self.v[k].trace_add("write", lambda *a: self.update_actions())
        self.update_actions()
        self.after(50, self.load_last)
        self.after(700, self.offer_move)
        self.after(4000, self.check_report_answers)
        self.after(6000, self.check_new_version)

    def check_new_version(self):
        """A newer release of the editor on GitHub: its number on the GitHub button (newversion) - the one an earlier
        check saw at once, a fresh look in a thread on every start and every few hours while the editor is open."""
        from . import newversion
        try:
            seen = newversion.known(VERSION)
            if seen and not getattr(self, "_release", None):
                self.show_new_version(*seen, fresh=False)
            newversion.check(self, VERSION, self.show_new_version)
        except Exception as e:
            log.write("New version not looked for: %s" % e)
        self.after(newversion.CHECK_EVERY * 1000, self.check_new_version)

    def show_new_version(self, number, url, fresh=True):
        """'GitHub (new 0.30)' on the button, green, which then opens that release's page; a fresh find says so
        below (once per number)."""
        if getattr(self, "_release", None) == (number, url):
            return
        self._release = (number, url)
        try:
            self.b_github.configure(text="GitHub (new %s)" % number, style="GitHubNew.TButton")
        except tk.TclError:
            return
        if fresh:
            self.status.set("A new version of the editor is out: %s - 'GitHub (new %s)' opens its page." % (
                number, number))

    def open_github(self):
        """The editor's page on GitHub - or, when a newer version is out, that release's page."""
        from . import newversion
        self.open_link((getattr(self, "_release", None) or ("", newversion.PAGE))[1])

    def open_link(self, url):
        """A page in the browser (Discord, YouTube, GitHub)."""
        import webbrowser
        webbrowser.open(url)
        self.status.set("%s opened in your browser." % url)
        log.write("Opened %s" % url)

    def check_report_answers(self):
        """The author's answers to the reports this editor sent (gui_answers) - quietly, every few hours."""
        from .gui_answers import check_on_start
        try:
            check_on_start(self)
        except Exception as e:
            log.write("Answers to my reports not checked: %s" % e)

    def offer_move(self, force=False):
        """Once per version, when the exe lies outside every game folder (the Downloads folder, the desktop): offer to
        put it into the game's folder - the user picks the folder (relocate.py); Settings > Folders has the same."""
        from . import relocate
        if not force and not relocate.should_offer(VERSION):
            return
        exe = relocate.running_exe()
        if not exe:
            messagebox.showinfo(APP, "The editor runs from its source files here - there is no exe to move.")
            return
        relocate.asked(VERSION)
        w = tk.Toplevel(self)
        w.title("Put the editor into the game's folder?")
        w.transient(self)
        ttk.Label(w, justify="left", wraplength=580, text=(
            "The editor works best from the game's folder - beside RomeTW.exe or medieval2.exe (and REX.exe / "
            "M2EX.exe): from there it finds the game and every mod by itself, and keeps its settings and logs in "
            "one place.\n\nIt now lies in:\n%s\n\nPick the game's folder: the editor copies itself there (its "
            "settings and add-ons go with it; an older copy of the editor there is replaced) and starts from "
            "there. The copy here can be deleted afterwards. Nothing else is changed." % os.path.dirname(exe))
                  ).pack(padx=14, pady=(12, 6), anchor="w")
        v_short = tk.BooleanVar(value=sys.platform.startswith("win"))
        ttk.Checkbutton(w, text="and put a shortcut to it on the desktop", variable=v_short).pack(anchor="w", padx=14)
        bar = ttk.Frame(w)
        bar.pack(fill="x", padx=14, pady=(10, 12))

        def pick():
            d = filedialog.askdirectory(parent=w, title="The game's folder (where RomeTW.exe / medieval2.exe is)",
                                        initialdir=settings.get("game") or "")
            if not d:
                return
            why = relocate.target_problem(d)
            if why:
                messagebox.showerror(APP, "Not there: %s." % why, parent=w)
                return
            try:
                new = relocate.move_to(d)
            except Exception as e:
                messagebox.showerror(APP, str(e), parent=w)
                return
            note = ""
            if v_short.get():
                bad = relocate.desktop_shortcut(new)
                note = ("\n\nA shortcut to it is on the desktop." if not bad else
                        "\n\nThe desktop shortcut could not be made (%s) - right click the exe there > Send to > "
                        "Desktop makes one." % bad)
            settings.put("game", d)
            messagebox.showinfo(APP, "The editor now lies in %s and starts from there.%s\n\nThe copy in %s can be "
                                     "deleted." % (d, note, os.path.dirname(exe)), parent=w)
            w.destroy()
            try:
                relocate.start(new)
            except Exception as e:
                messagebox.showerror(APP, "Start it from %s (%s)." % (new, e))
                return
            self.save_session()
            self.destroy()

        def never():
            relocate.asked(VERSION, never=True)
            w.destroy()
        ttk.Button(bar, text="Pick the game's folder...", command=pick).pack(side="left")
        ttk.Button(bar, text="Not now", command=w.destroy).pack(side="left", padx=6)
        ttk.Button(bar, text="Don't ask again", command=never).pack(side="left")

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
        usb = ttk.Frame(top)
        usb.pack(fill="x", pady=(0, 2))
        ttk.Label(usb, text="Search").pack(side="left")
        self.v_units_search = tk.StringVar()
        self.v_units_search.trace_add("write", lambda *a: self.refresh_chosen(keep_units_selection=True))
        ttk.Entry(usb, textvariable=self.v_units_search, width=20).pack(side="left", padx=4)
        self.units_rows = []         # the towns the list shows, in its order (the Search may hide some)
        # the hints and buttons are packed before the lists: a lower window shrinks the lists, never them
        ttk.Label(top, text="give it towns on the Map (a click on a town)", foreground="#666").pack(side="bottom", anchor="w")
        self.lb_units = tk.Listbox(top, width=30, height=8, exportselection=False)
        self.lb_units.pack(fill="both", expand=True)
        self.lb_units.bind("<<ListboxSelect>>", lambda e: (self.lb_field.selection_clear(0, "end"),
                                                           self.load_garrison()))
        # field armies, agents and fleets, placed on the Map
        ff = ttk.LabelFrame(split, text="Armies, agents & fleets  (drag the line above to resize)", padding=4)
        split.add(ff, weight=2)
        ttk.Label(ff, text="double click: show it on the map; right click: remove it", foreground="#666").pack(side="bottom", anchor="w")
        fb = ttk.Frame(ff)
        fb.pack(side="bottom", fill="x", pady=(4, 0))
        self.lb_field = FieldTable(ff)
        self.lb_field.pack(fill="both", expand=True)
        self.lb_field.bind("<<ListboxSelect>>", lambda e: self.lb_field.curselection() and (
            self.lb_units.selection_clear(0, "end"), self.load_field()))
        self.lb_field.bind("<Double-1>", lambda e: self.field_on_map())
        for text, kind in (("+ Army", "army"), ("+ Agent", "agent"), ("+ Fleet", "fleet")):
            ttk.Button(fb, text=text, command=lambda k=kind: self.add_field(k)).pack(side="left", padx=1)
        ttk.Button(fb, text="Place on map", command=self.place_field).pack(side="left", padx=(8, 1))
        right_click(self.lb_field.tv, self.remove_field)
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
        from .gui_util import tip
        tip(ttk.Button(side, text="Many towns at once...", command=lambda: self.mass_towns()),
            "Add a building to many towns of any owner at once (or take one out), or give them garrisons - "
            "towns picked by owner, level, city / castle. Also on the Map: 'Select', a box, then a right click.").pack(
            side="bottom", anchor="w", pady=(4, 2))
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
        from .gui_util import hint
        self.v_follow_pop = tk.BooleanVar(value=settings.get("level_follows_population", True) is not False)
        hint(ttk.Checkbutton(bar, text="level follows", variable=self.v_follow_pop,
                             command=lambda: (settings.put("level_follows_population", bool(self.v_follow_pop.get())),
                                              self.size_changed())),
             "Ticked: a population the level cannot hold makes the town grow (or shrink) to the level that holds it, "
             "its governor's building with it. Unticked: the population is cut to the level's range. Each level "
             "holds a range of people at the start (a village 400 - 1500, a town up to 3500, a large town 9000, a "
             "city 18000...) - outside it the game stops reading the campaign file.").pack(side="left", padx=(0, 12))
        self.lbl_size = ttk.Label(bar, text="", foreground="#666", justify="left")
        self.lbl_size.pack(side="left", fill="x", expand=True)
        self.lbl_size.bind("<Configure>", lambda e: self.lbl_size.configure(wraplength=max(120, e.width - 4)),
                           add="+")
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
                    self.sizes[region].pop("level_follows", None)
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
            if self.v_follow_pop.get():
                size["level_follows"] = True
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
        if self.map_work() and name not in self.MAP_TABS:
            return                                  # the Map editor shows its own tabs alone (a hidden tab would come back)
        self.nb.select([self.nb.tab(t, "text").strip() for t in self.nb.tabs()].index(name))

    MAP_EDITOR_HINT = ("Map editor: drag any faction's towns, ports, armies, agents and fleets (left button; the right one drags the map); right "
                       "click for more - give a town, an army's units, delete, new ones. Preview, then Apply changes "
                       "(a backup first).")

    def map_work(self):
        """The Map editor: the map alone, no faction picked - every faction's things alike."""
        return getattr(self, "v_mode", None) is not None and self.v_mode.get() == "map"

    HEIGHTS_TAB = "Coast & heights"
    TERRAIN_TABS = ("Terrain", HEIGHTS_TAB)         # both show the one Terrain editor, each its own brushes
    MAP_TABS = ("Map",) + TERRAIN_TABS              # the Map editor's own tabs

    def _map_tab_only(self, on):
        """The Map editor shows its Map and Terrain tabs alone; New / Edit faction all the others again (Terrain is
        the Map editor's)."""
        for t in self.nb.tabs():
            name = self.nb.tab(t, "text").strip()
            if name == "Map":
                continue
            if on != (name in self.MAP_TABS):
                self.nb.hide(t)
            elif self.nb.tab(t, "state") == "hidden":
                self.nb.add(t)

    def tab_opened(self):
        """A town tab with nothing selected opens the capital."""
        tab = self.tab_name()
        if tab == "Map":
            self.show_map()
            return
        if tab in self.TERRAIN_TABS:
            self.open_terrain()
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
        if tab == "Units & armies" and self.chosen and not self.lb_units.curselection() \
                and not self.lb_field.curselection():
            self.select_units_town(self.v["capital"].get() or self.chosen[0])
            self.load_garrison()
        elif tab == "Buildings" and self.chosen and not self.lb_build.curselection():
            capital = self.v["capital"].get() or self.chosen[0]
            self.lb_build.selection_set(self.chosen.index(capital) if capital in self.chosen else 0)
            self.load_buildings()

    # the tools that open a window of their own, on the work bar after the works: (key, button, App method, hover)
    WINDOW_BUTTONS = [
        ("rules", "Campaign rules...", "campaign_rules", "ages, agents, towns, diplomacy, unit sizes - every rule of "
                                                         "the campaign"),
        ("events", "Events...", "events_window", "events and later factions: plagues, volcanoes, historic messages"),
        ("traits", "Traits and retinue...", "traits_window", "what they give, their names, new ones"),
        ("builder", "Module builder...", "module_builder", "a new add-on made of blocks, no code (REX / M2EX)"),
        ("recolour", "Recolour...", "recolour_window", "a faction's pictures in its colours: cards, textures, "
                                                       "symbols"),
        ("culture", "Culture names...", "culture_names_table", "settlement names by culture, every town"),
        ("towns", "Many towns...", "mass_towns", "buildings and garrisons for many towns at once"),
        ("bigger", "Bigger map (x3)...", "upscale_map", "make the campaign map 3 x bigger (beta)"),
        ("mercs", "Mercenaries...", "mercenaries_window", "who is for hire in which regions: pools of regions and "
                                                          "their units"),
    ]
    WORK_TITLES = {"map": "Map editor", "new": "New faction", "edit": "Edit faction", "units": "Unit editor",
                   "buildings": "Building editor", "characters": "Character editor",
                   "terrain": "Terrain editor", "addons": "Add-ons", "religions": "Religions"}
    WORK_HINTS = {"map": "the campaign map alone, no faction to pick: drag any faction's towns, ports, armies, agents and "
                         "fleets, give towns to anyone, change any army's units, resources, forts, regions",
                  "religions": "the game's religions and each region's shares (Medieval II)", "addons": "ready-made scripts that add something new to the game (Sack Settlement...)","new": "make a new faction from a template", "edit": "change a faction that is in the game",
                  "units": "every line of a unit in export_descr_unit.txt, its card and picture",
                  "buildings": "every line of a building chain in export_descr_buildings.txt, its pictures",
                  "characters": "any faction's characters: names, ages, traits, ancillaries, portraits, family tree",
                  "terrain": "paint the campaign map's ground, rivers, fords and cliffs"}

    def work_changed(self):
        """New / Edit faction share the campaign tabs; the unit and building editors
        take the window's middle instead."""
        w = self.v_work.get()
        if w == "terrain":                              # a tab of the Map editor now
            self.v_work.set("map")
            self.work_changed()
            self.select_tab("Terrain")
            return
        if w in self.work_buttons:
            self.work_row.show(self.work_buttons[w])
        if w in ("map", "new", "edit"):
            for ed in self.editors.values():
                ed.pack_forget()
            if self.v_mode.get() != w and self.undo_stack and self.v_mode.get() != "map" and not ask(
                    APP, "Switch to %s? The faction's changes not written yet (its towns, garrisons, diplomacy...) "
                         "are dropped; the map's changes stay." % self.WORK_TITLES[w], yes='Switch, drop them', no='Stay', danger=True):
                self.v_work.set(self.v_mode.get())         # stay where the work is
                return
            self._map_tab_only(w == "map")
            self.nb.pack(fill="both", expand=True, padx=6, pady=3, after=self.bottom_bar)
            if self.v_mode.get() != w:
                self.v_mode.set(w)
                self.mode_changed()
            if w == "map":
                self.select_tab("Map")
                self.show_map()
                self.status.set(self.MAP_EDITOR_HINT)       # reading the map clears the status line
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

    def open_terrain(self):
        """The Terrain editor in the tab on show - Terrain (ground, rivers, climates) or Coast & heights (land and
        sea, heights): one editor (its strokes, Undo, Apply shared) moved into that tab, its brushes those of the
        tab; made the first time, on the mod loaded now."""
        ed = self.editors.get("terrain")
        if ed is None:
            from .gui_terrain import TerrainEditor
            ed = self.editors["terrain"] = TerrainEditor(self.nb, self)     # the notebook's child: packed into a tab
        here = self.heights_tab if self.tab_name() == self.HEIGHTS_TAB else self.terrain_tab
        ed.pack(in_=here, fill="both", expand=True)
        ed.lift(here)
        ed.set_group("heights" if here is self.heights_tab else "terrain")
        if self.mod and ed.mod is not self.mod:
            self._rebind(ed)
        self.update_actions()
        self._mark_work()

    def editor(self):
        """The unit, building or character editor on show, made the first time; None for the faction work."""
        w = self.v_work.get()
        if w not in ("units", "buildings", "characters", "addons", "religions"):
            return None                                 # (the Terrain editor is a tab of the Map editor now)
        if w not in self.editors:
            if w == "religions":
                from .gui_religions import ReligionsPanel
                self.editors[w] = ReligionsPanel(self, self)
            elif w == "addons":
                from .gui_addons import AddonsPanel
                self.editors[w] = AddonsPanel(self, self)
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
        (self.b_rename.grid if edit else self.b_rename.grid_remove)()
        for ws in self.extra_rows.values():             # shown again by load_existing when the faction has them
            for w in ws:
                w.grid_remove()
        # cloning-only options are hidden in Edit (diplomacy gets its own editor later)
        for w in [self.chk_triggers, self.chk_art] + self.dip_row + self.way_row:
            if edit:
                w.grid_remove()
            else:
                w.grid()
        if edit:
            self.v_way.set(WAY_LABELS[0])          # Edit: the way in is changed in Events... (top row)
        self.way_changed()
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
        self.status.set(self.MAP_EDITOR_HINT if self.map_work() else
                        "Edit: pick the faction to change; untouched fields stay as they are." if edit else
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
                theme.paint(b, rgb)
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
    UNDO_KEYS = ("chosen", "garrisons", "buildings_picked", "sizes", "kinds", "place_moves", "ports_gone", "char_moves", "field",
                 "removed_existing", "dip_set", "region_paint", "new_regions", "region_religions", "new_religions", "region_edits",
                 "culture_names", "name_list", "res_moves", "res_removed", "res_added", "region_tags", "fort_moves", "fort_removed", "fort_added", "art_replace", "sel_map", "figures", "roster_set",
                 "family_set", "map_owners", "map_chars", "map_removed", "map_moves", "map_units")

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

    def _in_window(self, redo=False):
        """Ctrl+Z / Ctrl+Y in a window of its own (the banner, the emblem...): its own Undo / Redo button's step;
        a window without one is never undone from the main window unseen."""
        w = self.focus_get()
        top = w.winfo_toplevel() if w is not None else None
        if top is None or top is self:
            return False
        step = getattr(top, "_redo" if redo else "_undo", None)
        if step:
            step()
        else:
            self.status.set("This window has no Undo of its own - Close it without writing to drop its changes.")
        return True

    def undo(self, e=None):
        if self._typing():
            return None
        if self._in_window():
            return "break"
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
        if self._in_window(redo=True):
            return "break"
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
        from .gui_util import keep_on_screen          # every window: resizable, never bigger than the screen
        self.bind_class("Toplevel", "<Map>", lambda e: keep_on_screen(e.widget), add="+")
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-Z>", self.redo)                  # Ctrl+Shift+Z
        self.bind_all("<Control-y>", self.redo)
        self.bind_all("<Control-p>", lambda e: self.preview())
        self.bind_all("<Control-s>", lambda e: self.create())
        self.bind_all("<F1>", lambda e: self.show_help())
        self.bind_all("<F5>", lambda e: self.load_clicked())
        for i in range(5):
            self.bind_all("<Control-Key-%d>" % (i + 1), lambda e, i=i: None if self.map_work() else self.nb.select(i))
        self.bind_all("<Control-KeyPress>", self._layout_keys)

    # Windows key codes of the letters the shortcuts use: with a non-Latin keyboard layout (Russian, Greek...) Tk
    # names the key by its own letter ('Cyrillic_ya' for Z), so <Control-z> never fires - the key's code still says Z.
    LAYOUT_KEYS = {90: "z", 89: "y", 80: "p", 83: "s", 67: "c", 86: "v", 88: "x", 65: "a"}

    def _layout_keys(self, e):
        """Ctrl + a letter in any keyboard layout: Undo / Redo / Preview / Write it, and copy / paste / cut / select
        all in the box that has the keys (a Latin layout's letters are bound above and never reach here)."""
        letter = self.LAYOUT_KEYS.get(e.keycode)
        if letter is None or (len(e.keysym) == 1 and e.keysym.isascii()):
            return None
        w = self.focus_get()
        if letter in "cvx":
            if w is not None:
                w.event_generate({"c": "<<Copy>>", "v": "<<Paste>>", "x": "<<Cut>>"}[letter])
            return "break"
        if letter == "a":
            if w is not None and w.winfo_class() in ("Text",):
                w.tag_add("sel", "1.0", "end-1c")
            elif w is not None and w.winfo_class() in ("Entry", "TEntry", "TCombobox"):
                w.selection_range(0, "end")
            return "break"
        shift = bool(e.state & 0x1)
        if letter == "z":
            (self.redo if shift else self.undo)(e)
        elif letter == "y":
            self.redo(e)
        elif letter == "p":
            self.preview()
        elif letter == "s":
            self.create()
        return "break"

    def _folder_named(self):
        """Said on Load: the mod's own start script / .cfg look for it under another folder name (a tester's mod
        lay in 'Neuer Ordner' - the game could not find it)."""
        from . import launch
        try:
            want = launch.named_folder(self.mod.data) if self.mod else None
        except Exception:
            want = None
        if want:
            here = os.path.basename(os.path.dirname(os.path.abspath(self.mod.data)))
            log.write("Load: the mod lies in %s, its start script / .cfg look for %s" % (here, want))
            messagebox.showwarning(APP, "This mod lies in the folder '%s', but its own start script / .cfg look for "
                                        "it in mods\\%s - the game will not find it so. Close the editor and rename "
                                        "the folder to %s." % (here, want, want))

    def play_label(self):
        """The Start button says what it starts: 'Start Rome - CE_Test'; amber 'Start Rome - no mod' when the game's
        own data is loaded (a tester played the plain game believing it was the test mod he had just made)."""
        b = getattr(self, "play_button", None)
        if b is None:
            return
        from . import launch
        try:
            game, mod = launch.what(self.mod.data) if self.mod else (None, None)
        except Exception:
            game, mod = None, None
        if not game:
            text, style = "\u25b6 Start the game", "Play.TButton"
        else:
            text = "\u25b6 Start %s - %s" % (game, mod or "no mod")
            style = "Play.TButton" if mod else "PlayNoMod.TButton"
        try:
            b.configure(text=text, style=style)
        except tk.TclError:
            pass

    def start_game(self):
        """The bottom bar's Start the game: the game with the loaded mod (launch.start_line - its own start script,
        else the engine's line)."""
        from . import launch
        if not self.mod:
            messagebox.showinfo(APP, "Load a mod first - the game starts with the mod that is loaded.")
            return
        if self.pending_parts() and not ask(
                APP, "There are changes not written yet (%s). The game reads the files as they are on disk - "
                     "start it without these changes?" % ", ".join(label for _, label in self.pending_parts()), yes='Start without them', no='Not now'):
            return
        try:
            how = launch.start_line(self.mod.data)
            found = launch.problems(how, self.mod.data)       # what would keep it from starting, said first
            stops = [w for s_, w in found if s_]
            if stops:
                raise ValueError("\n\n".join(stops))
            maybe = [w for s_, w in found if s_ is False]
            if maybe and not ask(
                    APP, "The game may not start as it should:\n\n%s\n\nStart it anyway?" % "\n\n".join(maybe), yes='Start it anyway', no='Not now'):
                return
            launch.start(how)
        except (ValueError, OSError) as e:
            log.write("Start the game: not started - %s" % e)
            messagebox.showerror(APP, "The game did not start: %s" % e)
            return
        log.write("Start the game: %s" % how["words"])
        notes = [w for s_, w in found if s_ is None]
        for w in notes:
            log.write("Start the game: note - %s" % w)
        self.status.set("The game is starting: %s. %sSomething went wrong in it? Report a bug / Suggest sends the "
                        "game's log with it." % (how["words"], "".join("Note: %s. " % w for w in notes)))

    def support(self):
        """The Ko-fi page in the browser: donations keep the work on the tool going."""
        import webbrowser
        webbrowser.open(KOFI)
        self.status.set("Thank you! %s opened in your browser." % KOFI)

    def credits_window(self):
        """Tools > Credits...: the author, who helped, the testers, the supporters (CREDITS.md - gui_credits)."""
        from .gui_credits import open_credits
        return open_credits(self)

    def _brush_changed(self):
        try:
            self.map_view.brush = max(1, int(self.v_brush.get()))
        except (tk.TclError, ValueError, AttributeError):
            pass

    def busy(self, on):
        """The moving bar beside the message: on while long work runs (counted - two at once keep it on)."""
        n = getattr(self, "_busy_n", 0) + (1 if on else -1)
        self._busy_n = max(0, n)
        if self._busy_n and on and n == 1:
            self.busy_bar.pack(side="right", padx=(6, 0), before=self.status_line)
            self.busy_bar.start(12)
        elif not self._busy_n:
            self.busy_bar.stop()
            self.busy_bar.pack_forget()

    def run_long(self, title, work, done, window=None):
        """work(report) runs in a thread (no Tk in it - report(text) says the step it is on); meanwhile the status
        line says title, the step and the seconds, with a moving bar; then done(result, error) runs here. window: a
        window to give the busy cursor too."""
        import time as _time
        state = {"step": "", "t0": _time.time()}

        def report(text):
            state["step"] = text

        def body():
            try:
                state["result"] = work(report)
            except Exception as e:
                state["error"] = e
                state["trace"] = traceback.format_exc()
        th = threading.Thread(target=body, daemon=True)
        self.busy(True)
        for x in (self, window):
            try:
                x and x.config(cursor="watch")
            except tk.TclError:
                pass
        th.start()

        def wait():
            secs = int(_time.time() - state["t0"])
            if th.is_alive():
                self.status.set("%s%s - %d s" % (title, (": " + state["step"]) if state["step"] else "", secs))
                self.after(300, wait)
                return
            self.busy(False)
            for x in (self, window):
                try:
                    x and x.config(cursor="")
                except tk.TclError:
                    pass
            if state.get("error") is not None:
                log.write("%s stopped: %s\n%s" % (title, state["error"], state.get("trace", "")))
            done(state.get("result"), state.get("error"))
        wait()

    def _written(self, bdir, p, group=None):
        """A write finished: offer to undo it, if it is this mod's (the test mod writes into another folder).
        group: every backup of one Apply that wrote several parts - undone together (from its first one)."""
        try:
            mine = self.mod and os.path.normcase(os.path.abspath(bdir)).startswith(
                os.path.normcase(os.path.abspath(os.path.dirname(self.mod.data))) + os.sep)
        except Exception:
            mine = False
        if not mine:
            return
        self._undo_bdir = bdir
        self._undo_group = list(group or [(bdir, "")])           # [(backup, what it wrote)], oldest first
        from .gui_util import tip
        tip(self.b_undo_write, "Puts back every file this last write changed, as it was before it (%s). The same as "
                               "Tools > Restore a backup on its newest line." % backup_label(bdir))
        self.b_undo_write.pack(side="right", padx=(6, 0), before=self.status_line)   # never squeezed by a long message

    def _undo_gone(self):
        self._undo_bdir = None
        self.b_undo_write.pack_forget()

    def undo_write(self):
        bdir = self._undo_bdir
        if not bdir or not self.mod or not os.path.isdir(bdir):
            self._undo_gone()
            return
        norm = lambda b: os.path.normcase(os.path.abspath(b))     # noqa: E731
        bs = [norm(b) for b in backups(self.mod)]
        parts = list(getattr(self, "_undo_group", None) or [(bdir, "")])
        group = {norm(b) for b, _ in parts}
        me = norm(bdir)
        newer = bs[:bs.index(me)] if me in bs else None
        if newer is None or any(b not in group for b in newer):
            self._undo_gone()                      # a newer write came since (or it was restored): Restore does it
            return
        waiting = self.pending_parts()
        if waiting:
            messagebox.showerror(APP, "Not undone yet. Changes wait for the write:\n\n%s\n\nApply them or "
                                      "Undo them first (the mod is read again after the files are put back)."
                                 % "\n".join("- " + label for _, label in waiting))
            return
        from .gui_util import ask_choice
        if len(parts) > 1:                         # one Apply wrote several parts: a step back, or all of it
            k = ask_choice(self, APP, "The last write put in %d parts:\n\n%s\n\nUndo only the last part (one step "
                                      "back), or the whole write? Every file is put back as it was before it; what "
                                      "it added is taken away." % (len(parts), "\n".join(
                                          "%d. %s" % (i + 1, lab or backup_label(b)) for i, (b, lab) in
                                          enumerate(parts))),
                           ["Undo the last part only", "Undo the whole write", "Keep it"], default=2, cancel=2)
            if k == 2 or k is None:
                return
            target = parts[-1][0] if k == 0 else parts[0][0]
        else:
            if ask_choice(self, APP, "Undo the last write?\n\n%s\n\nEvery file it changed is put back as it was "
                                     "before it; what it added is taken away." % backup_label(bdir),
                          ["Undo it", "Keep it"], default=1, cancel=1) != 0:
                return
            k, target = 1, bdir
        try:
            ms = restore_to(self.mod, target)
        except (ValueError, OSError) as e:
            log.write("Undo this write stopped: %s" % e)
            messagebox.showerror(APP, "%s" % e)
            return
        log.write("Undo this write: %s restored (%d file(s) back)" % (target, sum(len(m["modified"]) for m in ms)))
        self.load()
        if k == 0 and len(parts) > 2:              # one step back: the parts before it can still be undone
            self._written(parts[0][0], None, group=parts[:-1])
            self.status.set("The last part (%s) is undone; the parts before it are still written - Undo this write "
                            "again takes them back too." % (parts[-1][1] or "the newest"))
        elif k == 0:
            self._written(parts[0][0], None)
            self.status.set("The last part (%s) is undone; the part before it is still written." % (
                parts[-1][1] or "the newest"))
        else:
            self._undo_gone()
            self.status.set("The last write is undone - the files are as they were before it.")

    def mercenaries_window(self, region=None, new_from=None):
        from .gui_mercenaries import open_mercenaries
        return open_mercenaries(self, region=region, new_from=new_from)

    def merge_regions(self, keep, gone):
        """Merge regions (the map's switch): `gone` goes with its town from every file and all its land becomes
        `keep`'s (regiondelete, as Delete this town with its region... with the land going to `keep`)."""
        from .gui_settlements import merge_regions
        return merge_regions(self, keep, gone)

    def map_size_window(self, view=None):
        """Change size... under the map: tiles added at an edge (deep sea) or cut off, everything on the map moved
        with it (gui_mapsize, mapresize); the edges are dragged on that map (view; the main window's by default)."""
        from .gui_mapsize import open_map_size
        return open_map_size(self, view=view)

    def upscale_map(self):
        """Bigger map (x3)... (top row): one window - what happens, the heights, its progress, a backup, and the old
        map back with one button (gui_upscale)."""
        from .gui_upscale import open_upscale
        return open_upscale(self)

    def game_log_window(self, path=None):
        """Tools > The game's log in plain words: the newest system.log.txt of this mod (else of the game folder)
        read and explained - errors grouped, the mod's line each one names, what to do (gamelog.py)."""
        from . import gamelog, report
        from .newmod import game_of
        game = game_of(self.mod.data) if self.mod else settings.get("game")
        mod_dir = os.path.dirname(os.path.abspath(self.mod.data)) if self.mod else None
        if path is None:
            logs = report.game_logs(game, mod_dir) if game else []
            if not logs:
                if ask(APP, "No system.log.txt of the game found%s.\n\n%s\n\nPick a log file by "
                                            "hand?" % (" in %s or its mods" % game if game else "", report.LOG_HOWTO), yes='Pick a log file...', no='Not now'):
                    path = filedialog.askopenfilename(title="The game's system.log.txt",
                                                      filetypes=[("Game log", "*.txt"), ("Any file", "*.*")])
                if not path:
                    return
            else:
                path = logs[0]
        try:
            text = gamelog.report(path, game)
        except OSError as e:
            messagebox.showerror(APP, "Cannot read %s: %s" % (path, e))
            return
        log.write("Game log read: %s" % path)

        def other():
            p = filedialog.askopenfilename(title="The game's system.log.txt",
                                           filetypes=[("Game log", "*.txt"), ("Any file", "*.*")])
            if p:
                self.game_log_window(p)
        self.show_text("The game's log in plain words", "Written %s.\n\n" % report._age(path) + text,
                       extra=[("Open another log...", other)], wrap="word")

    def once(self, key, fn):
        """A button / menu command whose window opens once: pressed again while that window is open, it comes to
        the front instead of a second copy (a tester: Settings opened again and again). Any window the command
        makes is found by itself (the new windows after it ran) - one place for every such button."""
        def run(*a, **kw):
            open_ = [w for w in self._once.get(key, []) if w.winfo_exists() and w.winfo_ismapped()]
            if open_:
                for w in open_:
                    w.deiconify()
                    w.lift()
                w = open_[-1]
                w.focus_force()
                return None
            before = {str(w) for w in self.winfo_children()}
            out = fn(*a, **kw)
            self._once[key] = [w for w in self.winfo_children() if str(w) not in before and
                               isinstance(w, tk.Toplevel) and not w.wm_overrideredirect()]
            return out
        if not hasattr(self, "_once"):
            self._once = {}
        return run

    def settings_window(self):
        """Everything the tool keeps between starts, in one window."""
        from .gui_settings import SettingsWindow
        SettingsWindow(self)

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
            if self._region_point:                      # Edit regions off: a town / port waiting for a click is
                self._region_point, self._town_auto = None, False      # dropped too (the Pick towns rule)
                self.map_view.set_tool(None)
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
        tools = {"town": True, "port": True, "fort": True, "watchtower": True}
        tools.update({"res:" + t: True for t in types(self.mod)})
        # armies, fleets and agents for any faction: the land clicked says whose (the window lets another be picked)
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
        self._port_tool = key == "port"
        self._map_add = (key, None) if key in ("army", "fleet") else ("agent", key) if key in self.AGENTS else None
        if self._map_add:
            self.status.set("Click the %s for the new %s - it goes to the faction holding it (the window lets you pick "
                            "another). Click the sign again to stop." % (
                                "sea" if key == "fleet" else "tile", key))
            self.show_map()
            return
        if key == "port":
            self.status.set("Click a coastal land tile: the port of the region there goes to it (a region without a "
                            "port gets one). Click the sign again to stop.")
            self.show_map()
            return
        if key is None:
            self._placing = None
            self.status.set("")
            self.show_map()
            return
        if key in FT.KINDS:
            mv.v_forts.set(True)
            self.v_fort_type.set(key)
            self.res_place_new(key)
        elif key.startswith("res:"):
            mv.v_res.set(True)
            self.v_res_type.set(key[4:])
            self.res_place_new(key[4:])
        elif key == "town":
            self.new_region_dialog(then=self._start_town, cancelled=lambda: mv.set_tool(None))


    def _start_town(self, name):
        """After New region... from the legend: the next click puts its town; the land around it becomes the new
        region's (painted in Edit regions, which is switched on - paint more with a left drag)."""
        mv = self.map_view
        if not mv.v_regions.get():
            mv.v_regions.set(True)
            mv._regions_toggled()
        self.v_paint.set(name + "  (new)")
        self._region_point, self._town_auto = ("city", name), True
        self.status.set("Click the tile where the town of %s stands - also on another region: the town's tile and the 8 "
                        "round it become %s's, then the brush is in your hand to paint more." % (name, name))
        self.show_map()

    def _old_region(self, name):
        """The region of the map (not a new one) named in 'Paint with', its info, or None."""
        return None if self._new_region(name) or not self._cmap else self._cmap.info.get(name)

    def region_point(self, what):
        """The next click on the map puts the town (or port) of the region picked in 'Paint with': a new region's;
        a region of the map's moves there (Keep for Apply, as a drag on the Map would); a wasteland's town is given
        there (its own window - a wasteland has no port before its town, report #157)."""
        name = self.v_paint.get().replace("  (new)", "").strip()
        old = self._old_region(name)
        if not self._new_region(name) and old is None:
            messagebox.showerror(APP, "pick a region in 'Paint with' first - right click its land, or New region... "
                                      "makes one")
            return
        if old and old.get("wasteland") and what == "port":
            messagebox.showerror(APP, "%s is a wasteland - no town, so no port. 'Place its town' first, then its "
                                      "port." % name)
            return
        self._region_point = (what, name)
        self.status.set("Click the tile for the %s of %s (on its own land%s)%s." % (
            "town" if what == "city" else "port", name, ", by the sea" if what == "port" else "",
            " - a wasteland gets its town there" if old and old.get("wasteland") else
            " - it moves there" if old else ""))
        self.show_map()

    def place_moved(self, what, region, xy):
        """A town / port of a region of the map moved to xy (dragged, the legend's port, Place its town / port),
        kept for Apply; back on its own tile = no move."""
        self.remember()
        if tuple(xy) == tuple(place_orig(self.mod, self.v_campaign.get(), what, region) or ()):
            self.place_moves.pop((what, region), None)
        else:
            self.place_moves[(what, region)] = xy
        self.status.set("%s of %s to %d, %d - %d town(s)/port(s) moved; Preview, then %s." % (
            "Town" if what == "city" else "Port", region, xy[0], xy[1], len(self.place_moves),
            "Apply changes" if self.editing() or self.map_only() else "Create faction"))
        self.show_map()

    def _region_point_gone(self):
        """Why the town / port waiting for a click can no longer be placed (another tool was picked, or the new
        region was dropped meanwhile), or None. A map drawn before that still carries the old click handler."""
        if not self._region_point:
            return "no town or port is waiting to be placed - pick 'Place its town' again"
        if not self._new_region(self._region_point[1]) and self._old_region(self._region_point[1]) is None:
            return "the new region %s is gone (dropped) - nothing to place" % self._region_point[1]
        return None

    def region_point_problem(self, xy):
        gone = self._region_point_gone()
        if gone:
            return gone
        what, name = self._region_point
        old = self._old_region(name)
        if old is not None:                             # a region of the map: the same checks as a drag / the menu
            if old.get("wasteland"):
                from .regiondelete import town_problem
                return town_problem(self.mod, self.v_campaign.get(), name, tuple(xy))
            return place_problem(self.mod, self.v_campaign.get(), what, name, tuple(xy),
                                 {k: v for k, v in self.place_moves.items() if k != (what, name)}, self.region_paint)
        cm = self._cmap
        if not (0 <= xy[0] < cm.w and 0 <= xy[1] < cm.h):
            return "off the map"
        if cm.regions_img.get(*xy) in ((0, 0, 0), (255, 255, 255)):
            return "another town or port stands there"
        own = self.region_paint.get(tuple(xy)) or cm.region_at(*xy)
        if what == "city" and self._town_auto:          # from the legend: it takes its tile and the 8 round it
            if own is None:
                return "the sea - a town stands on land"
        elif own != name:
            return "not %s's land - paint it first" % name
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
        gone = self._region_point_gone()
        if gone:
            self._region_point, self._town_auto = None, False
            self.map_view.set_tool(None)
            self.status.set(gone[0].upper() + gone[1:] + ".")
            self.show_map()                             # the map forgets the old click handler
            return None
        what, name = self._region_point
        old = self._old_region(name)
        if old is not None:
            why = self.region_point_problem(xy)
            if why:
                return why
            self._region_point, self._town_auto = None, False
            self.map_view.set_tool(None)
            if old.get("wasteland"):
                from .gui_settlements import wasteland_town
                self.show_map()
                wasteland_town(self, name, tuple(xy), self)
            else:
                self.place_moved(what, name, tuple(xy))
            return None
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
        auto = self._town_auto
        self._region_point, self._town_auto = None, False
        self.map_view.set_tool(None)
        if auto and what == "city":                    # the brush in hand: paint the rest of its land at once
            self.v_paint.set(name + "  (new)")
            self.status.set("Town of %s at %d, %d with the 8 tiles round it - now paint more of %s's land with a "
                            "left drag (the brush holds %s); 'Place its port' when it reaches the sea."
                            % (name, xy[0], xy[1], name, name))
        else:
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
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
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
            fields = [(a, k, given[k], "the name players see - best keep it like the name in the files"
                       if k in SHOWN else h.split(";")[0].replace("by default ", ""))
                      for a, k, _, h in fields if k in SHOWN + EDITABLE]
            files_hint = ("letters, digits, _ ; a change is written at once in every file that names it, "
                          "with a backup (asked first)")
            fields = [("Region - name in the files", "file_region", edit, files_hint),
                      fields[0],
                      ("Town - name in the files", "file_town", town, files_hint)] + fields[1:]
            # who holds it (descr_strat.txt, not descr_regions - a tester: 'why is the owner not here?'); a change
            # goes the way of the Map's 'Give this town to' (with the next Apply)
            village = edit not in self.strat.owners() and edit not in self.map_owners
            owner_now = rebel_text if village else (self.owners_after().get(edit) or rebel_text)
            fields.append(("Owner", "owner", owner_now,
                           "no town in descr_strat.txt yet: the game makes a rebel village there - pick an owner "
                           "(the rebels, slave, too) to write its town" if village else
                           "who holds the town at the start (descr_strat.txt); a change is written with the next "
                           "Apply"))
            ttk.Label(frm, text="%s - town %s. The names in the files are changed at once in every file (with a "
                                "backup); the rest is written with the next Apply (descr_regions.txt, the owner in "
                                "descr_strat.txt, the names players see in the campaign's names text). Tip: give the name players see and the "
                                "name in the files the same spelling (Latium / Latium) - a mod is easier to read, "
                                "search and fix when a place has one name everywhere."
                                % (edit, town), font=("", 9, "bold"), wraplength=620, justify="left"
                      ).grid(row=99, column=0, columnspan=3, sticky="w", pady=(6, 0))
        vs = {}
        for i, (label, key, default, hint) in enumerate(fields):
            ttk.Label(frm, text=hint, foreground="#666", wraplength=420, justify="left").grid(row=i, column=2, sticky="w")
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=1)
            v = tk.StringVar(value=default)
            vs[key] = v
            if key in ("creator", "owner"):
                vals = [AS_LAND] + facs if key == "creator" else \
                    ([rebel_text] if not old or default == rebel_text else []) + facs
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
                region = edit
                new_files = (d.get("file_region") or edit, d.get("file_town") or old.get("settlement", ""))
                if new_files != (edit, old.get("settlement", "")):
                    from .gui_settlements import rename_now
                    if not rename_now(self, self.v_campaign.get(), edit, new_files[0], new_files[1], w):
                        return
                    region = new_files[0]
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
                owner = d.get("owner", owner_now)
                if owner != owner_now and owner not in facs:
                    messagebox.showerror(APP, "%s is no faction of this mod" % owner, parent=w)
                    return
                self.remember()
                if ch:
                    self.region_edits[region] = ch
                else:
                    self.region_edits.pop(region, None)
                if owner != owner_now:                   # the Map's 'Give this town to' - one Undo step with the rest
                    from .gui_mapadd import give_town
                    keep, self.remember = self.remember, lambda: None
                    try:
                        give_town(self, region, owner)
                    finally:
                        self.remember = keep
                said = dict(ch, **({"owner": owner} if owner != owner_now else {}))
                if w.winfo_exists():
                    w.destroy()
                if said:
                    self.status.set("%s: %s - Preview, then Apply." % (region, ", ".join("%s %s" % x
                                                                                      for x in said.items())))
                elif region == edit:
                    self.status.set("%s: as it is." % region)
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
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
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
        """New religion / Religions of a region (once Tools entries, now the Religions work's own buttons): the same dialogs as on the Map (Edit regions), reached
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
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
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
            messagebox.showinfo(APP, "This game has no religions - Medieval II's and Barbarian Invasion's have them "
                                     "(plain Rome has none).")
            return
        bi = bool(RL.beliefs_path(self.mod))          # Barbarian Invasion: beliefs, no region shares
        w = tk.Toplevel(self)
        w.title("New religion")
        w.transient(self)
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
        v = {k: tk.StringVar() for k in ("name", "shown", "pip_from", "picture", "symbol", "temples")}
        v["pip_from"].set(have[0])
        v["symbol"].set("draw")                    # from nothing: the editor draws it (no other religion's look)
        v["temples"].set("3")
        golden = (len(have) + len(self.new_religions)) * 137.508 % 360       # each new one its own colour
        import colorsys
        colour = [tuple(int(c * 255) for c in colorsys.hsv_to_rgb(golden / 360, 0.75, 0.8))]
        from .limits import engine_of, lifted
        count = ("%d religions in this mod (%s beside the game: no limit)" % (len(have), engine_of(self.mod)[:-4])
                 if lifted(self.mod, "religions") else
                 "%d of %d religions in this mod (the original game's limit)" % (len(have), RL.MAX_RELIGIONS))
        about = ("Barbarian Invasion: %d beliefs in this mod%s. A new one is written to descr_beliefs.txt, its three "
                 "pips (ui/pips: the order and unrest pips copied, the level pip your picture) and its texts "
                 "(expanded_bi.txt). A town follows it through the buildings that carry it (religious_belief) - "
                 "Temples of its own below makes them." % (
                     len(have), ", %d waiting" % len(self.new_religions) if self.new_religions else "")) if bi else (
            "%s%s. A new one is written to descr_religions.txt, its lookup, text/religions.txt, its symbol (ui/pips) "
            "and every region's religions line (0 %% until you set its share with Religions...); map.rwm is "
            "removed." % (count, ", %d waiting" % len(self.new_religions) if self.new_religions else ""))
        ttk.Label(frm, text=about,
                  wraplength=520, justify="left").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(frm, text="Name in the files").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v["name"], width=24).grid(row=1, column=1, sticky="w")
        ttk.Label(frm, text="e.g. judaism", foreground="#666").grid(row=1, column=2, sticky="w")
        ttk.Label(frm, text="Name players see").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v["shown"], width=24).grid(row=2, column=1, sticky="w")
        ttk.Label(frm, text="Its symbol").grid(row=3, column=0, sticky="nw")
        sym = ttk.Frame(frm)
        sym.grid(row=3, column=1, columnspan=2, sticky="w")
        drawn = ttk.Frame(sym)
        drawn.pack(anchor="w")
        ttk.Radiobutton(drawn, text="drawn: its first letter on a disc of",
                        variable=v["symbol"], value="draw").pack(side="left")
        swatch = ttk.Button(drawn, text="colour")
        swatch.pack(side="left", padx=4)

        def pick_colour():
            from tkinter import colorchooser
            got = colorchooser.askcolor(color="#%02x%02x%02x" % colour[0], parent=w)
            if got and got[0]:
                colour[0] = tuple(int(c) for c in got[0])
                theme.paint(swatch, colour[0])
                v["symbol"].set("draw")
        swatch.configure(command=pick_colour)
        theme.paint(swatch, colour[0])
        like = ttk.Frame(sym)
        like.pack(anchor="w")
        ttk.Radiobutton(like, text="a copy of the symbol of", variable=v["symbol"], value="copy").pack(side="left")
        ttk.Combobox(like, textvariable=v["pip_from"], values=have, state="readonly", width=21).pack(
            side="left", padx=4)
        pic = ttk.Frame(sym)
        pic.pack(anchor="w")
        ttk.Radiobutton(pic, text="a picture of mine", variable=v["symbol"], value="picture").pack(side="left")
        ttk.Entry(pic, textvariable=v["picture"], width=20).pack(side="left", padx=4)
        ttk.Button(pic, text="Browse...", command=lambda: (v["picture"].set(filedialog.askopenfilename(
            parent=w, title="The religion's symbol (PNG, JPG, TGA...)") or v["picture"].get()),
            v["symbol"].set("picture" if v["picture"].get() else v["symbol"].get()))).pack(side="left")
        ttk.Label(frm, text="Temples of its own").grid(row=4, column=0, sticky="w", pady=(6, 0))
        tem = ttk.Frame(frm)
        tem.grid(row=4, column=1, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Spinbox(tem, from_=0, to=99, textvariable=v["temples"], width=4).pack(side="left", anchor="n")
        ttk.Label(tem, foreground="#666", wraplength=420, justify="left", text="levels, made from nothing with the "
                  "usual numbers of this mod's temples (0 = none); built by the factions picked below, all if "
                  "none").pack(side="left", padx=4)
        ttk.Label(frm, text="Factions that follow it").grid(row=5, column=0, sticky="nw", pady=(6, 0))
        lb = tk.Listbox(frm, selectmode="multiple", height=8, exportselection=False)
        facs = [n for n, _ in self.mod.factions() if n != "slave"]
        from .build import faction_label
        for n in facs:
            lb.insert("end", faction_label(n, self.shown_names().get(n)))
        lb.grid(row=5, column=1, sticky="w", pady=(6, 0))
        if bi:                                       # there the list says who builds its temples
            lb.configure(state="normal")
        ttk.Label(frm, text="Barbarian Invasion: a faction follows a belief by its buildings - the ones picked build "
                  "its temples" if bi else "optional - none keeps every faction's religion; they build its temples",
                  foreground="#666", wraplength=220, justify="left").grid(row=5, column=2, sticky="nw", pady=(6, 0))

        def ok():
            how = v["symbol"].get()
            picked = [facs[i] for i in lb.curselection()]
            try:
                temples = max(0, int(v["temples"].get() or 0))
            except ValueError:
                temples = 0
            spec = {"name": v["name"].get().strip().lower(), "shown": v["shown"].get().strip(),
                    "pip_from": v["pip_from"].get(),
                    "picture": (v["picture"].get().strip() or None) if how == "picture" else None,
                    "draw": colour[0] if how == "draw" else None,
                    "factions": [] if bi else picked, "temples": temples, "builders": picked or ["all"]}
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
        if res_on:
            self.res_bar.pack(fill="x", before=mv)
        else:
            self.res_bar.pack_forget()
        if not res_on and self._res_sel and self._res_sel[:1] in ("r", "n"):
            self._res_sel = None                        # Edit resources off: no resource stays picked (a tester)
        if not (res_on or forts_on):
            self._res_placing = self._res_sel = None
            return {}
        kinds = list(types(self.mod))
        self.cb_res_type["values"] = kinds
        if self.v_res_type.get() not in kinds:
            self.v_res_type.set(kinds[0] if kinds else "")
        if self._res_placing and not (forts_on if (self._res_placing in FT.KINDS or
                                                   self._res_placing.startswith(FT.LANDMARK)) else res_on):
            self._res_placing = None                    # its mode was switched off
        shown = []
        if res_on:
            shown += [{"id": "r%d" % r.index, "kind": r.kind, "xy": tuple(self.res_moves.get(r.index, r.xy))}
                      for r in self._file_resources() if r.index not in self.res_removed]
            shown += [{"id": "n%d" % i, "kind": a["type"], "xy": tuple(a["xy"])} for i, a in enumerate(self.res_added)]
        camp = self.v_campaign.get()
        file_forts = self.strat.forts if self.strat else []
        if forts_on:
            shown += [{"id": "f%d" % fo.line, "kind": fo.kind, "type": fo.type, "owner": fo.owner,
                       "xy": tuple(self.fort_moves.get(fo.line, fo.xy))}
                      for fo in file_forts if fo.line not in self.fort_removed]
            shown += [{"id": "g%d" % i, "kind": a["kind"], "type": a.get("type", ""), "xy": tuple(a["xy"])}
                      for i, a in enumerate(self.fort_added)]

        def is_fort(rid):
            return rid[:1] in ("f", "g")

        def taken(but=None, forts=False):
            return [r["xy"] for r in shown if r["id"] != but and is_fort(r["id"]) == forts]

        def check(rid, xy):
            if is_fort(rid):
                kind = next((r.get("kind") for r in shown if r["id"] == rid), None)
                return FT.problem(self.mod, camp, xy, taken(rid, True), kind)
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
                if kind.startswith(FT.LANDMARK + ":"):
                    why = FT.problem(self.mod, camp, xy, taken(None, True))
                    if why:
                        return why
                    self.remember()
                    self.fort_added.append({"kind": FT.LANDMARK, "type": kind.split(":", 1)[1], "xy": tuple(xy)})
                    self._res_sel = "g%d" % (len(self.fort_added) - 1)
                    self._res_placing = None
                    self.map_view.set_tool(None)
                    self.status.set("Wonder %s placed at %d, %d - drag it to move it; Preview, then Apply."
                                    % (kind.split(":", 1)[1], xy[0], xy[1]))
                    self.show_map()
                    return None
                if kind in FT.KINDS:
                    why = FT.problem(self.mod, camp, xy, taken(None, True), kind)
                    alive = [fo for fo in file_forts if fo.line not in self.fort_removed]
                    if not why and FT.example(alive, kind, xy) is None:
                        why = FT.town_problem(self.mod, camp, xy, self.strat)
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
                self.status.set("%s placed at %d, %d - drag it to move it; Preview, then Apply." % (kind, xy[0], xy[1]))
                self.show_map()
                return None
            kw["on_place"] = place

            def placing_why(xy):                        # the same checks as place(), nothing written
                if kind.startswith(FT.LANDMARK + ":") or kind in FT.KINDS:
                    why = FT.problem(self.mod, camp, xy, taken(None, True), kind if kind in FT.KINDS else None)
                    if not why and kind in FT.KINDS:
                        alive = [fo for fo in file_forts if fo.line not in self.fort_removed]
                        if FT.example(alive, kind, xy) is None:
                            why = FT.town_problem(self.mod, camp, xy, self.strat)
                    return why
                return problem(self.mod, camp, xy, taken())
            # held in the hand under the mouse: the sign itself, not a bare tile frame (a tester)
            if kind.startswith(FT.LANDMARK + ":"):
                kw["ghost"] = {"kind": "landmark", "type": kind.split(":", 1)[1], "check": placing_why}
            elif kind in FT.KINDS:
                kw["ghost"] = {"kind": kind, "check": placing_why}
            else:
                kw["ghost"] = {"kind": "resource", "type": kind, "check": placing_why}
        return kw

    @staticmethod
    def _fort_kind(text):
        """The fort bar's pick as a placing kind: 'fort' / 'watchtower' / 'landmark:<type>' (a wonder)."""
        return "landmark:" + text.split(":", 1)[1].strip() if text.startswith("wonder:") else text

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
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
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
            gone = [x.strip() for x in now.split(",") if x.strip() and x.strip() not in
                    {y.strip() for y in text.split(",")}]
            uses = self._tag_uses(gone)                 # taken off: say first what stops working in this region
            if uses and not ask(APP, "Taking %s off %s: in this region these stop working:\n\n%s\n\n"
                                                     "Take it off anyway?" % (", ".join(gone), name, "\n".join(
                                                         uses[:20]) + ("\n... and %d more" % (len(uses) - 20)
                                                                        if len(uses) > 20 else "")), parent=w, yes='Take it off', no='Keep it'):
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

    def _tag_uses(self, tags):
        """['building chain level (line N)' / 'unit: recruited by ...'] of export_descr_buildings.txt asking for any of
        these region tags - what a region without them can no longer build or recruit."""
        import re
        edb = self.mod.file("edb") if self.mod and tags else None
        if not edb:
            return []
        rx = re.compile(r"\b(?:hidden_)?resource\s+(%s)\b" % "|".join(re.escape(t) for t in tags))
        out, chain = [], None
        for n, line in enumerate(self.mod.load(edb).texts(), 1):
            code = line.split(";")[0]
            t = code.split()
            if t[:1] == ["building"] and len(t) > 1:
                chain = t[1]
            m = rx.search(code)
            if m:
                if t[:1] in (["recruit_pool"], ["recruit"]):
                    what = "recruiting %s" % (code.split('"')[1] if '"' in code else t[1] if len(t) > 1 else "?")
                else:
                    what = "%s %s" % (chain or "?", t[0]) if t else chain or "?"
                out.append("%s - asks for %s (export_descr_buildings.txt line %d)" % (what, m.group(1), n))
        return out

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
        if self.map_work():                  # no faction of its own: every faction alike
            me = ""
        else:
            me = self.v["template"].get().strip() if self.editing() else (self.v["name"].get().strip().lower() or "(new)")
        dip_view = self.map_view.v_dip.get() and self.v["template"].get().strip() and not self.map_work()
        if dip_view:                         # every owner in the colour of how the faction stands towards it
            _, base = self.diplomacy_base()
            from .diplomacy import kinds
            feeling = kinds(self.strat)[0]
            for other in {fb.name for fb in self.strat.factions}:
                pick = lambda key: self.dip_set[key] if key in self.dip_set else base.get(key)
                start = pick(("faction_relationships", "me", other))     # an alliance / a war shows first
                v = start if isinstance(start, str) else pick((feeling, "me", other))
                colours[other] = tuple(int(dip_colour(v)[i:i + 2], 16) for i in (1, 3, 5))
        if self.map_work():
            pass
        elif not self.editing():
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
        removed = {(f, x["name"], tuple(x["from"])) for f, xs in self.map_removed.items() for x in xs}
        from .family import _parse_relative
        for fb in self.strat.factions:
            family = set()                            # every name on the faction's relative lines: the family
            for line in self.strat.lines[fb.start:fb.end]:
                if tokens(line)[:1] == ["relative"]:
                    r = _parse_relative(line)
                    if r:
                        family.update([r[0], r[1]] + list(r[2]))
            for i, c in enumerate(fb.characters):
                if not c.xy or (fb.name, c.name, tuple(c.xy)) in removed:
                    continue
                lines = self.strat.lines[c.start:c.end]
                army = any(tokens(l)[:1] == ["army"] for l in lines)
                cid = "%s:%d" % (fb.name, i)
                xy = self.map_moves.get(cid) or self.char_moves.get(
                    cid, town_moves.get(c.xy) or fleet_moves.get(c.start) or c.xy)
                ulines = [l for l in lines if tokens(l)[:1] == ["unit"]]
                chars.append({"id": cid, "faction": fb.name, "name": c.name, "kind": c.kind, "xy": xy,
                              "army": army, "units": len(ulines), "unit_names": [unit_name(l) for l in ulines],
                              "from": c.xy, "named": bool(c.named), "role": c.role,
                              "family": c.name in family or bool(c.role)})
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
        for fac, cs in self.map_chars.items():           # placed on the Map for other factions, written on Apply
            for i, fc in enumerate(cs):
                rtw_kind, army = KINDS[fc["kind"]]
                chars.append({"id": "map:%s:%d" % (fac, i), "faction": fac, "name": fc["name"], "kind": rtw_kind,
                              "xy": tuple(fc["xy"]), "army": army, "units": len(fc["units"]),
                              "unit_names": list(fc["units"]), "from": None})
                if army:
                    armies_at.add(tuple(fc["xy"]))
        if self.map_work():                  # the Map editor moves every faction's characters
            mine = [ch["id"] for ch in chars]
        else:
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
            if cid.startswith("map:"):                 # placed on the map, not written yet
                fac, i = cid[4:].rsplit(":", 1)
                self.map_chars[fac][int(i)]["xy"] = tuple(xy)
                self.status.set("%s moved to %d, %d - Preview, then Apply changes." % (ch["name"], xy[0], xy[1]))
                self.show_map()
                return
            if self.map_work():                        # another faction's character: the Map editor's own list
                if tuple(xy) == tuple(ch["from"]):
                    self.map_moves.pop(cid, None)
                else:
                    self.map_moves[cid] = tuple(xy)
                self.status.set("%s (%s) to %d, %d - %d character(s) moved; Preview, then Apply changes." % (
                    ch["name"], ch["faction"], xy[0], xy[1], len(self.map_moves)))
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
        def check_place(what, region, xy):              # land painted and not written yet counts (one go)
            return place_problem(self.mod, self.v_campaign.get(), what, region, xy,
                                 {k: v for k, v in self.place_moves.items() if k != (what, region)},
                                 self.region_paint)

        place_moved = self.place_moved
        region_kw = self._region_view(place)
        out = getattr(self, "_taking_out", None)
        if out is not None and out not in self._map_chars:
            out = self._taking_out = None
        if out is not None:                              # an army taken out of its town: placed by a click

            def out_why(xy, cid=out):
                if tuple(xy) == tuple(self._map_chars[cid]["xy"]):
                    return "it stands here now - pick another tile"
                return check(cid, xy)

            def out_click(xy, cid=out):
                why = out_why(xy)
                if why:
                    return why
                self._taking_out = None
                moved(cid, tuple(xy))
                return None

            def out_stop():
                self._taking_out = None
                self.status.set("It stays in its town.")
                self.show_map()
            region_kw["on_place"] = out_click
            region_kw["ghost"] = {"kind": "army" if self._map_chars[out].get("army") else "agent", "check": out_why}
            self.map_view.on_place_stop = out_stop
        else:
            self.map_view.on_place_stop = None
        if getattr(self, "_map_add", None) and self._cmap:
            kind, preset = self._map_add
            from .start import KINDS as _K

            def add_why(xy):
                rtw, army = _K[kind if kind != "agent" else preset]
                return self.mod.tile_problem(self.v_campaign.get(), xy, rtw, army, ())

            def add_click(xy):
                why = add_why(xy)
                if why:
                    return why
                self._map_add = None
                from .gui_mapadd import add_at
                add_at(self, kind, tuple(xy), preset)
                return None
            region_kw["on_place"] = add_click
            region_kw["ghost"] = {"kind": kind if kind != "agent" else "agent", "check": add_why,
                                  "char": preset if kind == "agent" else None}
        if getattr(self, "_port_tool", False) and self._cmap:
            def port_region(xy):                        # the land as painted now: a new region painted over an
                return self.region_paint.get(tuple(xy)) or self._cmap.region_at(*xy)   # old one gets its own port

            def port_why(xy):
                region = port_region(xy)
                if not region:
                    return "not a region's land"
                if self._new_region(region):                # not written yet: its port is part of the new region
                    self._region_point = ("port", region)
                    why = self.region_point_problem(xy)
                    self._region_point = None
                    return why
                return check_place("port", region, xy)

            def port_click(xy):
                why = port_why(xy)
                if why:
                    return why
                self._port_tool = False
                self.map_view.set_tool(None)
                region = port_region(xy)
                if self._new_region(region):
                    self._region_point = ("port", region)
                    return self.place_region_point(xy)
                place_moved("port", region, xy)
                return None
            region_kw["on_place"] = port_click
            region_kw["ghost"] = {"kind": "port", "check": port_why}
        res_kw = self._resource_view()
        on_place = region_kw.pop("on_place", place if placing is not None else None)
        if res_kw.get("on_place"):
            on_place = res_kw.pop("on_place")
            region_kw.pop("ghost", None)
        region_kw.update(res_kw)
        waiting = bool(getattr(self, "_map_add", None) or getattr(self, "_res_placing", None) or
                       getattr(self, "_port_tool", False) or getattr(self, "_region_point", None))
        self.map_view.waiting = waiting
        if waiting and self.map_view.on_place_stop is None:

            def stop_placing():                         # a right click / Esc: what hangs under the mouse is put back
                self._map_add = None                    # (only what is not on the map yet - nothing is deleted):
                self._res_placing = None                # an army, fleet, agent, resource, fort, watchtower, port, a
                self._port_tool = False                 # new region's town or port
                self._region_point, self._town_auto = None, False
                self.map_view.set_tool(None)
                self.status.set("Nothing placed.")
                self.show_map()
            self.map_view.on_place_stop = stop_placing
        if placing is not None and not region_kw.get("ghost") and placing < len(self.field):
            fc = self.field[placing]
            rtw_kind, army = KINDS[fc["kind"]]
            region_kw["ghost"] = {"kind": fc["kind"] if fc["kind"] in ("army", "fleet") else "agent",
                                  "check": lambda xy: self.mod.tile_problem(self.v_campaign.get(), xy, rtw_kind, army,
                                                                            armies_at)}
        self._map_labels = self.culture_labels(owners, me)
        self.map_view.allow_religion(self._m2())
        self.map_view.tools = self._map_tools()           # the legend's signs that are tools here
        self.map_view.ports_gone = set(self.ports_gone)
        try:                                              # Find matches the names players read too
            from .regionedit import shown_labels
            keys = list(self.regions) + [i.get("settlement") for i in self.regions.values() if i.get("settlement")]
            self.map_view.shown_names = shown_labels(self.mod, self.v_campaign.get(), keys)
        except Exception:
            self.map_view.shown_names = {}
        from .resources import types as _res_types
        self.map_view.res_types = list(_res_types(self.mod))
        if self.map_view.v_rel.get():                # Religion colours: each region in its main religion's colour
            region_kw["tint"], region_kw["tint_legend"] = self.religion_tint()
        # a town's own garrison with no captain ('garrisoned_army' in its block - a big map writes every garrison so,
        # the rebels' too: report #167) shows the same flag on the roof as an army in it
        self.map_view.inside = {st.region: len(st.garrison) for fb in self.strat.factions for st in fb.settlements
                                if st.garrison}
        self.map_view.load(self._cmap, owners, colours, me, self.chosen,
                           on_city=None if self.map_work() else self.map_city, chars=chars,
                           labels=self._map_labels,
                           draggable=mine, on_char_move=moved, check_tile=check, symbols=symbols,
                           on_place=on_place,
                           places=self.place_moves, check_place=check_place, on_place_move=place_moved,
                           locked=self._locked_hint, forts=[fo for fo in self.strat.forts if fo.line not in self.fort_removed] if self.strat
                           else [],
                           everyone=self.map_work(), **region_kw)

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
        self.select_units_town(region if region in self.chosen else self.chosen[0])
        self.load_garrison()

    def select_units_town(self, region):
        """Select a town in the Units & armies list; a Search that hides it is cleared."""
        if region not in self.units_rows:
            self.v_units_search.set("")
        self.lb_units.selection_clear(0, "end")
        if region in self.units_rows:
            i = self.units_rows.index(region)
            self.lb_units.selection_set(i)
            self.lb_units.see(i)

    # ------------------------------------------------------------------ loading
    def browse(self):
        d = filedialog.askdirectory(title="The mod's data folder",
                                    initialdir=log.exe_game() or settings.get("game") or "")
        if d:
            was = self.v_path.get()
            self.v_path.set(d)
            if not self.load_clicked():
                self.v_path.set(was)

    def unwritten(self, editors=True):
        """Plain lines for the changes not written yet on the mod loaded now: each editor's (unless editors is
        False - the same mod loaded again keeps them), and the faction tabs' (any step Undo could take back)."""
        if not self.mod:
            return []
        out = [label for key, label in self.pending_parts() if key != "faction"] if editors else []
        if self.undo_stack:
            out.append("%s: %d step(s)" % ("Edit faction" if self.editing() else "New faction / the map",
                                           len(self.undo_stack)))
        return out

    def may_drop(self, what, editors=True):
        """True when nothing waits for Apply, or the user lets the waiting changes go before `what` (loading
        another mod, another campaign) - they were made on the files loaded now and cannot follow."""
        waiting = self.unwritten(editors)
        if not waiting:
            return True
        return ask(APP, "%s?\n\nThese changes are not written yet and would be dropped:\n%s\n\n"
                                        "(Stay, then Apply writes them first.)"
                                   % (what, "\n".join("- " + w for w in waiting)), yes='Drop them', no='Stay', danger=True)

    def load_clicked(self):
        """Load (the button, F5, Browse...): the mod in the data folder box - after asking when changes made on the
        files loaded now would be dropped (the same mod again keeps the editors' changes: only the faction tabs'
        go). True when it was loaded."""
        if self.mod:
            from .moddata import find_data_dir
            try:
                target = find_data_dir(self.v_path.get().strip())
            except Exception:
                target = None
            same = bool(target) and os.path.normcase(os.path.abspath(target)) == \
                os.path.normcase(os.path.abspath(self.mod.data))
            what = "Load %s again" % self.mod.data if same else "Load %s" % (self.v_path.get().strip() or "the mod")
            if not self.may_drop(what, editors=not same):
                self.v_path.set(self.mod.data)
                return False
        self.load()
        return True

    def load_last(self):
        """At start: the mod loaded last time, if its folder is still there."""
        self.fill_mods(settings.get("game"))
        last = settings.get("mod_data")
        if last and os.path.isfile(os.path.join(last, "descr_sm_factions.txt")):
            self.v_path.set(last)
            self.load()

    def save_session(self):
        """On close: this session's log and the game's newest system.log.txt into CampaignEditor_logs/sessions
        (once per run)."""
        if getattr(self, "_session_saved", False):
            return
        self._session_saved = True
        try:
            game = (game_of(self.mod.data) if self.mod else None) or log.exe_game() or settings.get("game")
            mod_dir = os.path.dirname(self.mod.data) if self.mod else None
            log.write("Close")
            log.save_session(game, mod_dir)
        except Exception:
            pass

    def games(self, game=None):
        """The game folders the Mod list shows: the one the exe lies in, the one given, the ones used before (a
        modder with both games sees both - the exe in one game's folder reaches the other's mods too)."""
        out = []
        for g in [log.exe_game(), game, settings.get("game")] + list(settings.get("games") or []):
            if g and is_game(g) and os.path.normcase(os.path.abspath(g)) not in \
                    [os.path.normcase(os.path.abspath(x)) for x in out]:
                out.append(g)
        return out

    def fill_mods(self, game):
        """The Mod list: what the game folders hold (the game, bi, HLR, mods made here...) - the exe's own game
        first; with two games each line starts with its game's folder name."""
        games = self.games(game)
        self._mods = []
        for g in games:
            for label, d in list_mods(g):
                self._mods.append(("%s: %s" % (os.path.basename(g), label) if len(games) > 1 else label, d))
        self.cb_mods["values"] = [label for label, _ in self._mods]
        here = os.path.normcase(os.path.abspath(self.mod.data)) if self.mod else None
        self.v_modpick.set(next((label for label, d in self._mods
                                 if here and os.path.normcase(os.path.abspath(d)) == here), ""))

    def mod_picked(self):
        d = next((d for label, d in self._mods if label == self.v_modpick.get()), None)
        if d and (not self.mod or os.path.abspath(d) != os.path.abspath(self.mod.data)):
            if not self.may_drop("Load %s" % self.v_modpick.get()):
                self.fill_mods(settings.get("game"))
                return
            self.v_path.set(d)
            self.load()

    def campaign_picked(self):
        was = getattr(self, "_campaign_now", None)
        if was and was != self.v_campaign.get() and not self.may_drop("Open the campaign %s" % self.v_campaign.get()):
            self.v_campaign.set(was)
            return
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
        """Load the mod in the data folder box: the status line says so and the bar moves while it reads (a big
        mod on a slow disk takes seconds - the window looked frozen)."""
        self.status.set("Loading %s ..." % (self.v_path.get().strip() or "the mod"))
        self.busy(True)
        try:
            self.config(cursor="watch")
            self.update_idletasks()
        except tk.TclError:
            pass
        try:
            return self._load()
        finally:
            self.busy(False)
            self.play_label()
            self._folder_named()
            try:
                self.config(cursor="")
            except tk.TclError:
                pass

    def _load(self):
        before = self.mod.data if self.mod else None
        try:
            self.mod = ModData(self.v_path.get())
            self._units_for = self._edb_for = None
        except Exception as e:
            from . import gamefix
            need = gamefix.unpack_needed(self.v_path.get()) if isinstance(e, FileNotFoundError) else None
            missing = gamefix.unpacker_missing(self.v_path.get()) if isinstance(e, FileNotFoundError) else ""
            if need:
                self.offer_unpack(need)
            elif missing:
                messagebox.showinfo(APP, missing)
            else:
                messagebox.showerror(APP, str(e))
            return
        self.v_path.set(self.mod.data)
        log.write("Load %s" % self.mod.data)
        try:
            from .plan import clean_restored
            n = clean_restored(self.mod)
            if n:
                log.write("Backups already put back taken away: %d *_restored folder(s)" % n)
        except Exception:
            pass
        self.roster_editor.forget()
        self.family_editor.forget()
        # remembered for the next start: this mod, its game folder, the campaign picked in it
        game = game_of(self.mod.data)
        settings.put("mod_data", self.mod.data)
        if is_game(game):
            settings.put("game", game)
            used = [g for g in settings.get("games") or [] if os.path.normcase(g) != os.path.normcase(game)]
            settings.put("games", ([game] + used)[:4])
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
        from .limits import describe, engine_report, faction_limit
        lim = faction_limit(self.mod)
        try:
            log.write("Engine: " + engine_report(self.mod))
        except Exception as e:
            log.write("Engine: not checked (%s)" % e)
        def glance(mod=self.mod, campaign=self.v_campaign.get() or None):
            # the mod's picture for the log - every report then shows what it is (in the background: a big mod's
            # folder walk must not hold the window)
            try:
                from .check import mod_summary
                log.write(mod_summary(mod, campaign))
            except Exception as e:
                log.write("Mod at a glance: not read (%s)" % e)
        threading.Thread(target=glance, daemon=True).start()
        full = len(names) + 1 >= lim["max"] and lim["known"] and not lim["engine"]
        self.status.set("%s%s, %d campaign(s).%s" % (
            "%s found - " % lim["engine"][:-4] if lim["engine"] else "", describe(lim, len(names) + 1), len(camps),
                        " Full: the original exe takes no new faction (REX / M2EX take any number)." if full else ""))
        if not getattr(self, "_fix_queued", False):
            self._fix_queued = True
            self.after_idle(self.offer_fixes)
        # after Apply the editors read the files again; changes waiting in one whose file
        # was not written stay. Another mod: every editor reads the new one (what waited was made on the old
        # mod's files - left bound to them, Apply wrote it into the old mod)
        if before and os.path.normcase(os.path.abspath(before)) != os.path.normcase(os.path.abspath(self.mod.data)):
            for ed in self.editors.values():
                if ed.mod is not None:
                    ed.rebind(self.mod)
        ed = self.editor()
        if ed is not None:
            self._rebind(ed)
        if self.editors.get("terrain") is not None and self.tab_name() in self.TERRAIN_TABS:
            self.open_terrain()                 # written and loaded again: the tab on show reads the new files (a
            #                                     brush stroke after an Apply painted on nothing - report #141)
        self._mark_work()

    def _m2(self):
        from .limits import game_kind
        return bool(self.mod) and game_kind(self.mod) == "medieval2"

    def way(self):
        """'map' | 'event' | 'shadow' | 'revolt' - how the new faction comes into the campaign."""
        v = self.v_way.get()
        return WAY_KEYS[WAY_LABELS.index(v)] if v in WAY_LABELS else "map"

    def way_changed(self):
        """Show the parts the picked way needs (date + region / the faction / may come back)."""
        way = self.way()
        for w in self.way_more.winfo_children():
            w.pack_forget()
        if way == "map" or self.editing():
            return
        if way == "event":
            self.way_parts["event"].pack(anchor="w")
            if self.mod and not self.cb_way_region["values"]:
                try:
                    self.cb_way_region["values"] = EM.rising_regions(self.mod, self.v_campaign.get())
                except Exception:
                    pass
            if not self.v_way_date.get().strip():
                self.v_way_date.set("10 summer" if not self._m2() else "20")
        else:
            self.l_way_of.configure(text="the shadow of" if way == "shadow" else "splits off")
            self.way_parts["of"].pack(anchor="w")
            if self.mod:
                self.cb_way_of["values"] = [n for n, _ in self.mod.factions() if n != "slave"]
        self.chk_way_back.pack(anchor="w")
        self.l_way_note.pack(anchor="w")

    def _game_rows(self):
        """The faction form greys what the loaded game has not: Rome's short name and icon tooltip on Medieval II
        (its texts have neither), Medieval II's religion on Rome - each label says which game it is for."""
        m2 = self._m2()
        if m2:                                         # cleared before the fields are greyed (a greyed Text ignores it)
            self.v["short_name"].set("")
            self.t_descr.configure(state="normal")
            self.t_descr.delete("1.0", "end")
        # shown greyed with the game it belongs to, not hidden (NN/g: features vanishing unexplained confuse)
        for rows, mine, words in ((self.rome_rows, not m2, " (Rome only)"), (self.m2_rows, m2, " (Medieval II only)")):
            for w in rows:
                w.grid()
                if w.winfo_class() in ("TLabel", "Label"):
                    base = getattr(w, "_plain_text", None)
                    if base is None:
                        base = w._plain_text = str(w.cget("text"))
                    w.configure(text=base if mine else base + words)
                    continue
                try:
                    if w.winfo_class() == "TCombobox":
                        w.configure(state="readonly" if mine else "disabled")
                    else:
                        w.configure(state="normal" if mine else "disabled")
                except tk.TclError:
                    pass
        if m2:
            from .religions import names
            self.cb_religion["values"] = names(self.mod) + [r["name"] for r in self.new_religions
                                                            if r["name"] not in names(self.mod)]
        else:
            self.v["religion"].set("")

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
        if not ask(APP, (
                "%s is not unpacked yet: its files are still in %d .pack file(s) (Steam's Medieval II comes "
                "that way - the game reads the packs, so it plays), and there is nothing to edit yet.\n\nUnpack "
                "it now with the game's own unpacker (tools\\unpacker%s)?%s\n\n"
                "It takes a few minutes and several GB of disk; the packs stay as they are. The unpacker asks you to "
                "agree to SEGA's terms for it - 'Unpack it' answers Y to that for you.") % (
                ("This Medieval II campaign (%s)" % need["campaign"]) if need.get("campaign") else "This Medieval II",
                need["packs"], ("\\" + os.path.basename(need["bat"])) if need.get("bat") else "", dlls), yes='Unpack it', no='Not now'):
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
            self.v_path.set(need.get("data") or os.path.join(need["game"], "data"))
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
        if not isinstance(declined.get(self.mod.data, []), list):      # another version's form
            declined = dict(declined, **{self.mod.data: []})
        found = [p for p in found if p["id"] not in declined.get(self.mod.data, [])]
        if not found:
            return
        text = "\n\n".join(gamefix.grouped_words(found))
        from .gui_util import ask_choice
        if ask_choice(self, APP, "Found on Load - set-up problems of this game / mod:\n\n%s\n\nPut them right now? "
                                 "A backup is made first (Restore undoes it)." % text,
                      ["Put them right", "Not now"], default=0, cancel=1) != 0:
            declined = dict(declined)
            declined[self.mod.data] = declined.get(self.mod.data, []) + [p["id"] for p in found]
            settings.put("fixes_declined", declined)
            return
        plan = gamefix.fix_plan(ModData(self.mod.data), found)
        bdir = plan.apply()
        log.write("Set-up fixed (backup %s)\n%s" % (bdir, plan.report()))
        self.load()
        self.status.set("Set-up fixed: %s (backup made)." % ", ".join(p["id"] for p in found))

    def _own_folder_first(self, plan):
        """Before the first write into a mod the editor did not make (the game's own data, a downloaded mod - no
        CampaignEditor_mod.json): asked once, 'Make your own mod folder first?' (recommended: the game / that mod stays
        clean, its update never takes your work, deleting your folder takes everything back). 'Write here' is
        remembered for that mod (settings own_folder_ok); 'Make my own mod folder' stops this write and opens New mod
        folder."""
        from . import gui_util, settings as _settings
        from .newmod import game_root_of, marker
        from .textio import NotWritten
        import threading
        if self.mod is None or plan.mod is not self.mod or threading.current_thread() is not threading.main_thread():
            return                                   # another mod's plan (the test mod makes its own), or no window
        root = os.path.dirname(os.path.abspath(self.mod.data))
        key = os.path.normcase(root)
        said = list(_settings.get("own_folder_ok", []) or [])
        if marker(root) or key in said or key in self._own_folder_asked:
            return
        _, base = game_root_of(self.mod.data)
        what = ("the game's own data folder - your changes would go into the game itself" if not base else
                "%s, a mod the editor did not make - your changes would go into it" % base)
        pick = gui_util.ask_choice(self, APP, (
            "This is %s.\n\nBetter: a mod folder of your own (New mod folder...) - the game%s stays clean, an update "
            "of %s never takes your work, and deleting your folder takes everything back. On the plain game it holds "
            "only what you change.\n\nMake your own mod folder first? (Write here: not asked again for this mod - "
            "a backup is made before every write anyway.)" % (what, " and %s" % base if base else "",
                                                               base or "the game")),
            ["Make my own mod folder", "Write here"], default=0, cancel=1)
        if pick == 0:
            self.after_idle(self.new_mod)
            raise NotWritten("Nothing was written: make your own mod folder first - the New mod folder window is "
                             "open; it is loaded when made, then do the change again there.")
        if pick == 1:
            _settings.put("own_folder_ok", said + [key])
        else:                                        # the question closed: not asked again in this session
            self._own_folder_asked.add(key)

    def new_mod(self):
        """Make <game>/<name> from the loaded mod (every file copied; hard links on a tick) - on the plain game a
        THIN mod (nothing copied: only what changes goes into it), then load it."""
        if not self.mod:
            messagebox.showerror(APP, "load the mod (or the game's data folder) to build on first")
            return
        _, base = game_root_of(self.mod.data)
        game = game_of(self.mod.data)
        m2 = is_medieval2(game)
        w = tk.Toplevel(self)
        w.title("New mod folder")
        w.transient(self)
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
        ttk.Label(frm, text="Based on:  %s" % (base or "the game's own data"), font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frm, text="Created in:  %s" % os.path.dirname(mod_target(self.mod.data, "x"))).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(frm, text="New mod name").grid(row=2, column=0, sticky="w")
        v_name = tk.StringVar(value=(base or ("M2" if m2 else "RTW")) + "_" + (self.v["name"].get().strip().capitalize() or "New"))
        ttk.Entry(frm, textvariable=v_name, width=30).grid(row=3, column=0, sticky="we", padx=(0, 6))
        v_links = tk.BooleanVar(value=False)            # copies by default: a mod one shares stands on its own
        if base:                                        # the plain game: a thin mod, nothing to copy or link
            ttk.Checkbutton(frm, text="Hard links instead of copies (no extra disk space - for a mod you keep to "
                                      "yourself)", variable=v_links).grid(row=4, column=0, columnspan=2, sticky="w",
                                                                         pady=4)
        thin_words = (
            "The game stays untouched. The new mod holds only what you change (a 'thin' mod): nothing is copied now "
            "- made at once, no disk space; the game reads every other file from its own data, and the editor puts "
            "a game file into the mod the first time you change it (the whole map folder at the first change of the "
            "map, so the game builds its map again there). The mod stays small - easy to share and to zip. "
            "Deleting the new mod folder never touches the game.\n")
        full_words = (
            "The base stays untouched. Every file is copied: the new mod stands on its own - to share, to zip, "
            "to change in any program (it takes the disk space of the base's files).\n"
            "Hard links (the tick above) are for a mod you keep to yourself: text files are still copied, models, "
            "textures and sounds become the same files on the disk as the base's under a second name - no extra "
            "space, Explorer still shows their full size. Only a program that overwrites such a file in place (a "
            "texture editor saving over a .dds, say) changes the base's file too - the tool itself never does. "
            "Deleting the new mod folder never touches the game or the base mod.\n")
        start_words = ("It goes into the game's mods folder with %s.cfg and Start_%s.bat (Medieval II starts a mod "
                       "from its .cfg)." % ("<name>", "<name>") if m2 else
                       "A start script Start_<name>.bat is written into the new folder.")
        ttk.Label(frm, justify="left", wraplength=560, text=(full_words if base else thin_words) + start_words).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 8))

        def go():
            name = v_name.get().strip()
            w.destroy()
            self.status.set("Building %s ..." % name)
            result = {}

            def work():
                try:
                    result["data"], result["stats"] = create_mod(
                        self.mod.data, name, not v_links.get(),
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
                    "Made %s\n\n%s.\n\n%s"
                    "It is loaded now: what you change goes into it. Start the game with %s." % (
                        st["target"], "A thin mod: nothing copied - the game reads every file you do not change from "
                        "its own data" if st.get("thin") else "%d file(s) linked, %d copied (%.0f MB really written)%s"
                        % (st["linked"], st["copied"], st["bytes_copied"] / 1048576.0,
                           "" if st["hard_links"] else " - every file copied"),
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
        self._campaign_now = c
        if not self.mod or not c:
            return
        try:
            self.strat = Strat(self.mod.load(self.mod.campaign_file(c, "descr_strat.txt")))
            self.regions = self.mod.regions(c)
            self.mod.city_tiles(c)
            self.cb_way_region["values"] = EM.rising_regions(self.mod, c)
            self.cb_way["values"] = [WAY_LABELS[WAY_KEYS.index(k)] for k in EM.ways_for(self.mod)]
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
        self.ports_gone = []
        self.map_owners, self.map_chars, self.map_removed = {}, {}, {}
        self.map_moves, self.map_units = {}, {}          # the Map editor: any faction's characters moved, units
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
        owners.update(getattr(self, "map_owners", {}))   # towns given to any faction on the Map
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
                k = ask_choice(self, APP, "%s has changes not written yet. Apply writes them (with a backup) before "
                                          "%s opens." % (was, t), ["Apply, then open %s" % t, "Drop them",
                                                               "Stay with %s" % was], cancel=2, danger=1)
                ans = None if k == 2 else k == 0
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
                theme.paint(b, rgb)
        self.status.set("Template %s: %s. Its units, buildings, names, traits and art are copied." %
                        (t, disp.get("display_name", t)))

    def rename_faction(self):
        """Edit faction > Rename...: the faction's code name changed in every file of the mod (factionrename) -
        one write, one backup; Preview first, scripts naming it listed (not changed)."""
        from tkinter import simpledialog
        from . import factionrename as FR
        from .plan import Plan
        from .gui_util import ask
        old = self.v["template"].get().strip()
        if not self.mod or not old:
            return
        if self.unwritten():
            messagebox.showinfo(APP, "Other changes wait for Apply. Apply (or undo) them first - they were made with "
                                     "the old name.", parent=self)
            return
        new = simpledialog.askstring(APP, "The new code name of %s (small letters, digits and _ - the name the "
                                          "files use; the names players read are on this tab):" % old, parent=self)
        new = (new or "").strip()
        if not new or new == old:
            return
        why = FR.problems(self.mod, old, new)
        if why:
            messagebox.showerror(APP, "Not renamed: %s." % why, parent=self)
            return
        plan = Plan(self.mod, "rename", new)
        try:
            FR.plan_rename(plan, self.v_campaign.get(), old, new)
        except (ValueError, OSError) as e:
            messagebox.showerror(APP, "Not renamed: %s." % e, parent=self)
            return
        if not ask(APP, "%s\n\nRename %s to %s in %d file(s)? A backup is made first (Undo this write puts it "
                        "back)." % (plan.report()[:3000], old, new, len(plan.changed_files())),
                   yes="Rename it", no="Cancel", parent=self):
            return
        try:
            bdir = plan.apply()
        except Exception as e:
            messagebox.showerror(APP, "Not renamed: %s" % e, parent=self)
            return
        log.write("Faction %s renamed %s (backup %s)\n%s" % (old, new, bdir, plan.report()))
        self.load()
        if new in [n for n, _ in self.mod.factions()]:
            self.v["template"].set(new)
            self.template_changed()
        self.status.set("%s is %s now in every file; Undo this write puts it back." % (old, new))

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
                "Apply changes" if self.editing() or self.map_only() else "Create faction"))
        self._mark_work()

    def pick_colour(self, which):
        c = colorchooser.askcolor(title=which + " colour")
        if c and c[0]:
            rgb = tuple(int(x) for x in c[0])
            self.colours[which] = rgb
            btn = self.b_primary if which == "primary" else self.b_secondary
            theme.paint(btn, rgb)

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
        was = self.units_rows[sel[0]] if sel and sel[0] < len(self.units_rows) else None
        self.lb_units.delete(0, "end")
        want = self.v_units_search.get().strip().lower()
        self.units_rows = [r for r in self.chosen
                           if not want or want in r.lower()
                           or want in self.regions.get(r, {}).get("settlement", "").lower()]
        for r in self.units_rows:
            n = len(self.garrisons.get(r, []))
            self.lb_units.insert("end", "%s%s%s" % (r, "  (capital)" if r == (self.v["capital"].get() or
                                 (self.chosen[0] if self.chosen else "")) else "",
                                 "  [%d units]" % n if r in self.garrisons else
                                 ("  [unchanged]" if self.editing() else "  [automatic]")))
        if keep_units_selection and was in self.units_rows:
            self.lb_units.selection_set(self.units_rows.index(was))
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
        owners_now = self.town_owners() if self.strat else {}
        for i, r in enumerate(self.chosen):
            self._tint_row(self.lb_build, i, owners_now.get(r))
        if keep_units_selection and bsel and bsel[0] < len(self.chosen):
            self.lb_build.selection_set(bsel[0])
        self.lb.delete(0, "end")
        for r in self.chosen:
            owner = self.town_owners().get(r, "?") if self.strat else "?"
            mark = "  [%d units]" % len(self.garrisons[r]) if r in self.garrisons else ""
            self.lb.insert("end", "%s  (%s)%s" % (r, owner, mark))
            self._tint_row(self.lb, "end", owner)
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
            self.lb_field.insert("end", (c["kind"], c["name"], units, where, tag),
                                 find=" ".join(u if isinstance(u, str) else str(u.get("name", "")) if isinstance(u, dict)
                                               else str(u) for u in c.get("units", [])))
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
        return "" if self.map_work() else self.v["template"].get().strip()

    def add_field(self, kind, preset=None, then_place=False, at=None):
        """A small form: kind (agents), name from the faction's name list, age. preset: the agent picked;
        then_place: the next click on the Map puts the new one there (the legend's tools); at: put it on
        this tile at once (the map's right-click menu; the nearest good tile when it may not stand there)."""
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
            if at is not None:                     # the map's menu: placed on that tile at once
                self._placing = len(self.field) - 1
                self.show_map()
                if not self.map_view.place_at(at):
                    self.status.set("%s could not stand there - pick its tile: click the map." % self.field[-1]["name"])
                return
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

    def mass_towns(self, picked=(), tab="building"):
        """The window 'Buildings and garrisons for many towns' (the towns picked on the Map already chosen)."""
        if not self.mod:
            messagebox.showinfo(APP, "Load a mod first.")
            return
        from .gui_masstown import MassTownWindow
        try:
            MassTownWindow(self, picked, tab)
        except Exception as e:
            log.write("Many towns: %s" % e)
            messagebox.showerror(APP, "Could not read the towns: %s" % e)

    def recolour_window(self, faction=None):
        """Recolour the faction's pictures (the faction picked in the window, else the first; the window's list changes it)."""
        if not self.mod:
            messagebox.showinfo(APP, "Load a mod first.")
            return
        names = [n for n, _ in self.mod.factions()]
        faction = faction or self.field_faction()
        if faction not in names:                    # no faction picked yet: the window opens on the first, a list
            faction = next(iter(sorted(names)), None)   # at its top changes it
            if not faction:
                messagebox.showinfo(APP, "This mod has no faction to recolour.")
                return
        if self.editor() is None and self.undo_stack and self.v_mode.get() == "new":
            messagebox.showinfo(APP, "Recolour works on the files as they are: create the new faction first "
                                     "(Create faction), then recolour its pictures.")
        from .gui_recolour import RecolourWindow
        try:
            RecolourWindow(self, faction)
        except Exception as e:
            log.error("Recolour: %s" % e)
            messagebox.showerror(APP, "Could not read the pictures: %s" % e)

    def pick_menu(self, picked, region):
        """The Map's right-click menu while 'Select' is on: for the selected towns, characters, resources and forts."""
        mv = self.map_view
        n = len(picked)
        items = []
        nc, nr = len(mv.sel_chars), len(mv.sel_res)
        if n:
            from .gui_mapadd import factions_here
            names = self.shown_names()
            items.append(("Give the %d selected town(s) to" % n,
                          [(("%s - %s" % (f, names[f]) if names.get(f) else f), lambda f=f: self.give_towns(picked, f))
                           for f in factions_here(self)]))
        if nc:
            items.append(("Delete the %d selected character(s) from the map (armies too)" % nc,
                          lambda: self.delete_selected_chars(set(mv.sel_chars))))
        if nr:
            items.append(("Delete the %d selected resource(s) / fort(s) from the map" % nr,
                          lambda: self.delete_selected_res(set(mv.sel_res))))
        if n:
            from .gui_settlements import delete_towns       # many at once (report R-20261008-7696AA)
            items.append(("Delete the %d selected town(s) with their regions..." % n,
                          self.once("delete_towns", lambda: delete_towns(self, sorted(picked), self))))
        if n or nc or nr:
            items.append((None, None))
        if region:
            town = self._cmap.info.get(region, {}).get("settlement", region) if self._cmap else region
            owner = mv.owners.get(region)
            items.append(("%s (%s)" % (town, owner or "no owner"), None))
            items.append(("Unpick it" if region in picked else "Pick it", lambda: mv.toggle_pick(region)))
            if owner:
                items.append(("Pick every town of %s" % owner,
                              lambda: mv.pick_many([r for r, o in mv.owners.items() if o == owner])))
            items.append((None, None))
        items.append(("Add a building to the %d picked town(s)..." % n,
                      (lambda: self.mass_towns(sorted(picked), "building")) if n else None))
        items.append(("Garrisons for the %d picked town(s)..." % n,
                      (lambda: self.mass_towns(sorted(picked), "garrison")) if n else None))
        items.append(("City / castle and level for the %d picked town(s)..." % n,
                      (lambda: self.mass_towns(sorted(picked), "town")) if n else None))
        items.append(("New mercenary pool from the %d selected region(s)..." % n,
                      (lambda: self.mercenaries_window(new_from=sorted(picked))) if n else None))
        items.append(("Unselect all", (lambda: mv.pick_many(None)) if n or nc or nr else None))
        return items

    def give_towns(self, regions, faction):
        """The selected towns go to faction with the next Apply (one Undo step)."""
        from .gui_mapadd import give_town
        self.remember()
        keep, self.remember = self.remember, lambda: None          # one Undo step for all of them
        try:
            for r in sorted(regions):
                give_town(self, r, faction)
        finally:
            self.remember = keep
        self.status.set("%d town(s) go to %s with the next Apply - Preview first; Undo brings them back."
                        % (len(regions), faction))

    def delete_selected_chars(self, cids):
        """The selected characters off the map with the next Apply: another faction's (or any in the Map editor)
        as one line each, the ones placed here and not written yet simply dropped. The edited faction's own are
        left (Units & armies takes them off)."""
        self.remember()
        chars = getattr(self, "_map_chars", None) or {}
        gone, kept = 0, 0
        for cid in sorted((c for c in cids if str(c).startswith("map:")), key=lambda c: -int(str(c).split(":")[2])):
            _, fac, k = str(cid).split(":")
            if int(k) < len(self.map_chars.get(fac, [])):
                self.map_chars[fac].pop(int(k))
                gone += 1
        me = self.field_faction() if not self.map_only() else None
        needed = []                                  # a leader / heir, a man on the family tree: Apply refuses them

        def on_tree(ch):
            fb = self.strat.faction(ch["faction"]) if self.strat and ch.get("named") else None
            return bool(fb) and any(tokens(t)[:1] == ["relative"] and ch["name"] in t
                                    for t in self.strat.lines[fb.start:fb.end])
        for cid in cids:
            if str(cid).startswith(("map:", "new:")):
                kept += str(cid).startswith("new:")
                continue
            ch = chars.get(cid)
            if not ch or (me and ch["faction"] == me):
                kept += 1
                continue
            if ch.get("role") or on_tree(ch):
                needed.append("%s (%s's %s)" % (ch["name"], ch["faction"], ch.get("role") or "family"))
                continue
            self.map_moves.pop(cid, None)
            self.map_units.pop(cid, None)
            self.map_removed.setdefault(ch["faction"], []).append({"name": ch["name"], "from": list(ch["from"])})
            gone += 1
        self.map_view.sel_chars = set()
        self.status.set("%d character(s) go with the next Apply%s%s - Preview first; Undo brings them back." % (
            gone, " (%d of the faction you edit left: take them off on Units & armies)" % kept if kept else "",
            "; left on the map, the faction needs them: %s%s" % (", ".join(needed[:4]), " ..." if len(needed) > 4
                                                                 else "") if needed else ""))
        self._mark_work()
        self.show_map()

    def delete_selected_res(self, rids):
        """The selected resources, forts, watchtowers and wonders off the map (the added ones last first, their
        numbers do not shift)."""
        self.remember()
        keep, self.remember = self.remember, lambda: None
        try:
            for rid in sorted(rids, key=lambda r: (r[:1] not in ("g", "n"), -int(r[1:]))):
                self._res_sel = rid
                self.res_delete()
        finally:
            self.remember = keep
        self.map_view.sel_res = set()
        self.status.set("%d resource(s) / fort(s) go with the next Apply - Preview first; Undo brings them back."
                        % len(rids))

    def town_window(self, region):
        """The town's own window (gui_town): owner, city / castle, level, population, buildings."""
        from .gui_town import open_town_window
        open_town_window(self, region)

    def open_town(self, region):
        """A town straight from the Map (a double click, or the right click's 'Edit this town'): its owner opened in
        Edit faction and the town picked on the Buildings tab - its level, population, city or castle, buildings;
        its garrison is on Units & armies."""
        owner = self.owners_after().get(region)
        if not owner or not self.mod:
            self.status.set("%s has no town yet (a rebel village) - give it to a faction first." % region)
            return
        if not self.editing():
            self.v_work.set("edit")
            self.work_changed()
        if self.v["template"].get() != owner:
            self.v["template"].set(owner)
            self.template_changed()
            if self.v["template"].get() != owner:
                return                                  # stayed with the faction before (its changes)
        if region not in self.chosen:
            self.status.set("%s is %s's town at the start, but not in its list here." % (region, owner))
            return
        self.select_tab("Buildings")
        self.lb_build.selection_clear(0, "end")
        self.lb_build.selection_set(self.chosen.index(region))
        self.lb_build.see(self.chosen.index(region))
        self.load_buildings()
        town = self._cmap.info.get(region, {}).get("settlement", region) if self._cmap else region
        self.status.set("%s (%s, %s): level, population, city or castle and buildings here; its garrison on Units "
                        "& armies. Preview, then Apply changes." % (town, region, owner))

    def map_menu(self, xy, region, cid):
        """The Map's right-click menu: [(label, command)] for what can be done at that spot."""
        if not self.mod:
            return []
        items = []
        if region:
            town = self._cmap.info.get(region, {}).get("settlement", region) if self._cmap else region
            mine = region in self.chosen
            items.append(("%s (%s)" % (town, region), None))
            items.append(("This town...  (double click)", lambda: self.town_window(region)))
            txy = tuple(self.place_moves.get(("city", region)) or self._cmap.cities.get(region) or ()) \
                if self._cmap else ()
            agents = []
            for acid, ach in (getattr(self, "_map_chars", None) or {}).items():
                if tuple(ach.get("xy") or ()) != txy or acid not in getattr(self.map_view, "draggable", ()):
                    continue
                if ach.get("army"):
                    items.append(("Take the army out: %s (%s) - then click a free tile" % (ach["name"], ach["faction"]),
                                  lambda acid=acid: self.take_out(acid)))
                else:                                   # agents in the town: a list, each by name (what he is)
                    agents.append(("%s (%s)" % (ach["name"], ach["kind"]), lambda acid=acid: self.take_out(acid)))
            if agents:
                items.append(("Take an agent out - then click a free tile", sorted(agents, key=lambda a: a[0])))
            items.append(("Edit this town in Edit faction (garrison, characters)", lambda: self.open_town(region)))
            if self.field_faction() and not self.map_only():
                items.append(("Take out of my towns" if mine else "Add to my towns", lambda: self.map_city(region)))
            from .gui_mapadd import factions_here, give_town
            owner = self.owners_after().get(region)
            names = self.shown_names()
            items.append(("Give this town to", [(("%s - %s" % (f, names[f]) if names.get(f) else f),
                                                 lambda f=f: give_town(self, region, f))
                                                for f in factions_here(self) if f != owner]))
            from .gui_settlements import delete_town
            items.append(("Delete this town with its region...", self.once(
                "delete_town:%s" % region, lambda: delete_town(self, region, self))))
            if mine:
                items.append(("Its garrison...  (Units & armies)", lambda: self.show_units(region)))

                def buildings():
                    self.select_tab("Buildings")
                    self.lb_build.selection_clear(0, "end")
                    self.lb_build.selection_set(self.chosen.index(region))
                    self.load_buildings()
                items.append(("Its buildings...  (Buildings)", buildings))
        elif self._cmap and cid is None:
            # a wasteland's land (REX / M2EX: no town, nobody's): the way back - its town on this tile
            land = self._cmap.region_at(*xy)
            if land and self._cmap.info.get(land, {}).get("wasteland"):
                from .gui_settlements import wasteland_town
                items.append(("%s - a wasteland (no town, nobody's)" % land, None))
                items.append(("Give %s its town here..." % land, self.once(
                    "wasteland_town:%s" % land, lambda: wasteland_town(self, land, tuple(xy), self))))
        port = getattr(self.map_view, "menu_port", None)
        if port and port not in self.ports_gone:
            def delete_port(port=port):
                self.remember()
                self.ports_gone.append(port)
                self.place_moves.pop(("port", port), None)
                self.status.set("The port of %s goes with the next Apply (its fleet moves to the sea beside, its "
                                "harbour buildings go) - Preview first; Undo brings it back." % port)
                self._mark_work()
                self.show_map()
            if items:
                items.append((None, None))
            items.append(("Delete the port of %s" % port, delete_port))
        rid = getattr(self.map_view, "menu_res", None)
        what = None
        if rid:                                        # a resource, fort, watchtower or wonder: gone with its line
            mark = getattr(self.map_view, "resources", None) or []
            what = next((m for m in mark if m.get("id") == rid), None)
            name = (what or {}).get("kind", "this")
            if name == "landmark" and (what or {}).get("type") and not getattr(self.map_view, "menu_fort", None):
                from .gui_wonders import show as show_wonder, view_3d
                wt = what["type"]
                name = "wonder %s" % wt
                if items:
                    items.append((None, None))
                items.append(("About this wonder...  (as the game shows it)",
                              lambda wt=wt: show_wonder(self, self.mod, wt)))
                items.append(("View it in 3D", lambda wt=wt: view_3d(self, self.mod, wt)))

            def delete_mark(rid=rid):
                self._res_sel = rid
                self.res_delete()
            if items:
                items.append((None, None))
            items.append(("Delete the %s from the map" % name, delete_mark))
        fl = getattr(self.map_view, "menu_fort", None)
        fo = next((x for x in (self.strat.forts if self.strat else []) if x.line == fl), None) if fl is not None else None
        fxy = None                                       # a fort / watchtower: the army in it can be taken out
        if rid and (what or {}).get("kind") in ("fort", "watchtower"):
            fxy = tuple(what.get("xy") or ())
        elif fo is not None and fo.kind != "landmark":
            fxy = tuple(fo.xy)
        for acid, ach in ((getattr(self, "_map_chars", None) or {}).items() if fxy else ()):
            if tuple(ach.get("xy") or ()) == fxy and ach.get("army") and \
                    acid in getattr(self.map_view, "draggable", ()):
                items.append(("Take the army out: %s (%s) - then click a free tile" % (ach["name"], ach["faction"]),
                              lambda acid=acid: self.take_out(acid)))
        if fo is not None and not rid:                   # a fort / watchtower / wonder drawn as the file has it:
            def delete_fort(line=fo.line):              # deleted the same way as a picked one
                self._res_sel = "f%d" % line
                self.res_delete()
            if items:
                items.append((None, None))
            items.append(("Delete the %s from the map" % ("wonder %s" % fo.type if fo.kind == "landmark" else fo.kind),
                          delete_fort))
        if fo is not None and fo.kind == "landmark":     # a wonder (drawn on every map): its window and its model
            from .gui_wonders import show as show_wonder, view_3d
            if items:
                items.append((None, None))
            items.append(("Wonder %s: about it...  (as the game shows it)" % fo.type,
                          lambda t=fo.type: show_wonder(self, self.mod, t)))
            items.append(("View it in 3D", lambda t=fo.type: view_3d(self, self.mod, t)))
        if cid is not None and ":" in str(cid) and not str(cid).startswith(("map:", "new:")):
            ch = (getattr(self, "_map_chars", None) or {}).get(cid)
            mine = self.field_faction() and not self.map_only() and ch and ch["faction"] == self.field_faction()
            if ch and ch.get("from"):                    # anyone in descr_strat: his own window (as a town's)
                if items:
                    items.append((None, None))
                items.append(("Edit this character...  (%s %s of %s: name, age, traits, retinue)"
                              % (ch["kind"], ch["name"], ch["faction"]), lambda ch=ch: self.person_window(ch)))
            if ch and not mine and ch.get("army"):
                items.append(("Its units...  (%s %s of %s)" % (ch["kind"], ch["name"], ch["faction"]),
                              lambda cid=cid: self.army_units_window(cid)))
            if ch and not mine:
                def delete_char(ch=ch, cid=cid):
                    self.remember()
                    self.map_moves.pop(cid, None)           # nothing else of him is written
                    self.map_units.pop(cid, None)
                    self.map_removed.setdefault(ch["faction"], []).append({"name": ch["name"],
                                                                            "from": list(ch["from"])})
                    self.status.set("%s %s of %s goes with the next Apply%s - Preview first; Undo brings him back."
                                    % (ch["kind"], ch["name"], ch["faction"], " (his army too)" if ch.get("army")
                                       else ""))
                    self._mark_work()
                    self.show_map()
                if items:
                    items.append((None, None))
                items.append(("Delete %s (%s of %s) from the map%s" % (
                    ch["name"], ch["kind"], ch["faction"], ", with his army" if ch.get("army") else ""), delete_char))
        if cid is not None and str(cid).startswith("map:"):
            _, fac, k = str(cid).split(":")
            k = int(k)

            def drop(fac=fac, k=k):
                self.remember()
                if k < len(self.map_chars.get(fac, [])):
                    gone = self.map_chars[fac].pop(k)
                    self.status.set("%s %s of %s taken out (it was not written yet)." % (gone["kind"], gone["name"], fac))
                self._mark_work()
                self.show_map()
            c = (self.map_chars.get(fac) or [None] * (k + 1))[k]
            if c:
                items.append(("%s %s of %s (written with the next Apply)" % (c["kind"], c["name"], fac), None))
                if c["kind"] in ("army", "fleet"):
                    items.append(("Its units...", lambda cid=cid: self.army_units_window(cid)))
                items.append(("Take it out", drop))
        if cid is not None:
            i = next((k for k, c in enumerate(self.field)
                      if cid == "new:%d" % k or (c.get("existing") and c.get("cid") == cid)), None)
            if i is not None:
                c = self.field[i]

                def open_it(i=i):
                    self.select_tab("Units & armies")
                    self.lb_field.v_find.set("")
                    self.lb_units.selection_clear(0, "end")
                    self.lb_field.selection_set(i)
                    self.load_field()
                if items:
                    items.append((None, None))
                items.append(("%s %s: open it  (Units & armies)" % (c["kind"], c["name"]), open_it))

                def delete_own(i=i):
                    self.lb_field.selection_clear(0, "end")
                    self.lb_field.selection_set(i)
                    self.remove_field()
                    self.show_map()
                items.append(("Delete %s from the map" % c["name"], delete_own))
        land = region or (self._cmap.region_at(*xy) if self._cmap else None)
        if cid is None and land and not (self._cmap and self._cmap.info.get(land, {}).get("wasteland")):  # it hires none
            if items:
                items.append((None, None))
            items.append(("Mercenaries for hire in %s..." % land, lambda: self.mercenaries_window(region=land)))
        if cid is None and self.strat:
            # for any faction: the land's owner by default, another picked in the window
            from .gui_mapadd import add_at, owner_at
            if items:
                items.append((None, None))
            sea = self.mod.is_sea(self.v_campaign.get(), xy)
            whose = owner_at(self, xy)
            kinds = (("fleet", "New fleet here..."),) if sea else (("army", "New army here..."),
                                                                     ("agent", "New agent here..."))
            for kind, label in kinds:
                items.append(("%s  (%s)" % (label, whose) if whose else label,
                              lambda kind=kind: add_at(self, kind, tuple(xy))))
            from . import forts as FT
            wtypes = FT.landmark_types(self.mod) if not sea else []
            if wtypes:                                 # Rome: one of the game's wonders put here (written on Apply)
                placed = {fo.type for fo in (self.strat.forts if self.strat else [])
                          if fo.kind == FT.LANDMARK and fo.line not in self.fort_removed}
                placed |= {a.get("type") for a in self.fort_added if a.get("kind") == FT.LANDMARK}

                def put_wonder(t, xy=tuple(xy)):
                    why = FT.problem(self.mod, self.v_campaign.get(), xy, ())
                    if why:
                        messagebox.showerror(APP, "A wonder cannot stand at %d, %d: %s" % (xy[0], xy[1], why))
                        return
                    self.remember()
                    self.fort_added.append({"kind": FT.LANDMARK, "type": t, "xy": xy})
                    self.status.set("Wonder %s at %d, %d - Preview, then Apply (Undo takes it back)." % (t, xy[0], xy[1]))
                    self._mark_work()
                    self.show_map()
                items.append(("Put a wonder here", [("%s%s" % (t, "  (on the map already - a second one)" if t in placed
                                                               else ""), lambda t=t: put_wonder(t)) for t in wtypes]))
        return items

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
        if not sel or not self.mod or sel[0] >= len(self.units_rows):
            return
        region = self.units_rows[sel[0]]
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
            else:                                      # the town's own garrison (garrisoned_army, no captain)
                st = self.strat.settlement_of(region) if self.strat else None
                now = list(st.garrison) if st is not None else []
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

    def char_window(self, cid):
        """A double click on a character on the Map: an army or fleet opens its units (any faction's in a window of
        its own; the faction's own in Edit faction opens Units & armies); an agent says what to do."""
        i = next((k for k, c in enumerate(self.field)
                  if cid == "new:%d" % k or (c.get("existing") and c.get("cid") == cid)), None)
        if i is not None and not self.map_only():
            self.select_tab("Units & armies")
            self.lb_field.v_find.set("")
            self.lb_units.selection_clear(0, "end")
            self.lb_field.selection_set(i)
            self.load_field()
            return
        ch = (getattr(self, "_map_chars", None) or {}).get(cid)
        if str(cid).startswith("map:"):
            _, fac, k = str(cid).split(":")
            c = (self.map_chars.get(fac) or [None] * (int(k) + 1))[int(k)]
            if c and c["kind"] in ("army", "fleet"):
                self.army_units_window(cid)
            return
        if ch and ch.get("army"):
            self.army_units_window(cid)
        elif ch and not self.person_window(ch):
            self.status.set("%s %s of %s: an agent has no units - right click for what can be done with him."
                            % (ch["kind"], ch["name"], ch["faction"]))

    def person_window(self, ch):
        """The character's own window (gui_person): the Character editor on him, Write it in with a backup."""
        from .gui_person import open_person_window
        return open_person_window(self, ch)

    def open_person(self, ch):
        """A double click on an agent on the Map (report #104): the Character editor opens on him - his traits,
        retinue, age and the game's panel. False when he is not in descr_strat yet (placed, not written)."""
        if not ch.get("from"):
            return False
        self.v_work.set("characters")
        self.work_changed()
        ed = self.editor()
        if ed is None or not hasattr(ed, "v_fac"):
            return False
        ed.v_fac.set(ch["faction"])
        ed.load()
        people = ed.people()
        p = next((q for q in people if q["name"] == ch["name"] and q.get("xy") and tuple(q["xy"]) == tuple(ch["from"])),
                 None) or next((q for q in people if q["name"] == ch["name"]), None)
        if p is None:
            return False
        ed.pick(p["key"])
        self.status.set("%s %s of %s in the Character editor." % (ch["kind"], ch["name"], ch["faction"]))
        return True

    def take_out(self, cid):
        """An army or an agent leaves its town (the roof flag is part of the town's sign and is not dragged - report
        #104): it hangs under the mouse until a free tile is clicked (green where it may stand, red with why where
        not); Esc or a right click stops."""
        ch = (getattr(self, "_map_chars", None) or {}).get(cid)
        if not ch:
            return
        self._taking_out = cid
        self.status.set("%s (%s, %s): click a free tile for %s - Esc or a right click stops." % (
            ch["name"], ch["kind"], ch["faction"], "the army" if ch.get("army") else "him"))
        self.show_map()

    def fort_window(self, fo):
        """A double click on a fort: the army standing in it (its garrison) opens; an empty fort says how to man it -
        a fort has no buildings (report #102)."""
        chars = getattr(self, "_map_chars", None) or {}
        at = [cid for cid, ch in chars.items() if ch.get("army") and tuple(ch.get("xy") or ()) == tuple(fo.xy)]
        if at:
            self.char_window(at[0])
            return
        # an empty one: a new army for it at once - its units are the garrison (a fort has no buildings)
        if self.strat and ask(APP, "This %s at %d, %d is empty. Put a new army in it? Its units are "
                                                   "the garrison (a fort has no buildings)." % (fo.kind, fo.xy[0],
                                                                                              fo.xy[1]), parent=self, yes='Put a new army in', no='Not now'):
            from .gui_mapadd import add_at
            add_at(self, "army", tuple(fo.xy))
        else:
            self.status.set("This %s at %d, %d is empty: drag an army onto it - its units are the garrison."
                            % (fo.kind, fo.xy[0], fo.xy[1]))

    def army_units_window(self, cid):
        """Any faction's army or fleet on the map (the Map editor, or another faction's from Edit faction): its units
        in the card picker, in a window of its own; written with the next Apply (a named general keeps his
        bodyguard)."""
        ch = (getattr(self, "_map_chars", None) or {}).get(cid)
        if not ch or not self.mod:
            return
        fac, fleet = ch["faction"], ch["kind"] == "admiral" or ch["kind"] == "fleet"
        entry = None
        if str(cid).startswith("map:"):
            _, f, k = str(cid).split(":")
            entry = self.map_chars[f][int(k)]
            current, named = list(entry["units"]), False
        else:
            named = bool(ch.get("named"))
            start = ch["unit_names"][1:] if named else ch["unit_names"]
            current = list(self.map_units.get(cid, start))
        units = self._with_types(faction_units(self.mod, fac, ships=fleet, mercs=True), current)
        top = tk.Toplevel(self)
        top.title("%s %s of %s - units" % (ch["kind"], ch["name"], fac))
        top.geometry("940x640")
        top.transient(self)
        ed = GarrisonEditor(top, pictures=self.pictures)
        ed.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        if fleet:
            ed.v_whose.set("own + mercenaries")            # many mods mark every ship a mercenary

        def changed(types):
            self.remember()
            if entry is not None:
                entry["units"] = list(types)
            elif list(types) == list(start):
                self.map_units.pop(cid, None)
            else:
                self.map_units[cid] = list(types)
            self.status.set("%s %s of %s: %d unit(s)%s - Preview, then Apply changes." % (
                ch["kind"], ch["name"], fac, len(types), " + his bodyguard" if named else ""))
            self._mark_work()
            self.show_map()
        ed.load(self.mod, fac, "%s %s of %s" % (ch["kind"], ch["name"], fac), units, current, changed,
                held=named, unchanged=entry is None and cid not in self.map_units)
        ttk.Button(top, text="Close", command=top.destroy).pack(anchor="e", padx=6, pady=6)
        return top

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
        way = self.way()
        if not leader and way == "map":
            raise ValueError("the faction needs a leader - pick a first name")
        if way == "event" and not self.v_way_region.get():
            raise ValueError("pick the region where it rises (Comes into the campaign)")
        if way in ("shadow", "revolt") and not self.v_way_of.get():
            raise ValueError("pick the faction it %s (Comes into the campaign)" % (
                "is the shadow of" if way == "shadow" else "splits off"))
        opts = {
            "display_name": v["display_name"], "short_name": v["short_name"], "adjective": v["adjective"],
            "description": self.t_descr.get("1.0", "end").strip(),
            "long_description": self.t_long.get("1.0", "end").strip(),
            "religion": (v.get("religion") or None) if self._m2() else None,
            "primary_colour": self.colours["primary"], "secondary_colour": self.colours["secondary"],
            "copy_triggers": self.v_triggers.get(), "copy_art": self.v_art.get(),
            "start": {"regions": list(self.chosen) if way == "map" else [], "capital": v["capital"], "leader": leader,
                      "way": way, "of": self.v_way_of.get() or None, "re_emergent": self.v_way_back.get(),
                      "date": self.v_way_date.get().strip(), "region": self.v_way_region.get() or None,
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
        # no town kept: REX / M2EX let it live on (can_homeless, edit.edit); the plain games refuse it there

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

    def _tint_row(self, lb, index, owner):
        """A town's row in the muted colour of its owner (gui_util.owner_tint)."""
        from .gui_util import owner_tint
        from .mapdata import faction_colours
        if getattr(self, "_fc_for", None) is not self.mod:
            try:
                self._fc, self._fc_for = faction_colours(self.mod), self.mod
            except Exception:
                self._fc, self._fc_for = {}, self.mod
        bg = owner_tint(self._fc.get(owner)) if owner else None
        if bg:
            try:
                lb.itemconfigure(index, background=bg)
            except tk.TclError:
                pass

    def _places(self):
        return [{"what": w, "region": r, "to": xy} for (w, r), xy in self.place_moves.items()
                if not (w == "port" and r in self.ports_gone)] + \
            [{"what": "port", "region": r, "to": None} for r in self.ports_gone]

    def map_only(self):
        """The Map editor, or New faction mode with no faction named yet: the buttons write the map's changes
        alone."""
        if self.map_work():
            return True
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
        kept = len(self.session_parts()) if getattr(self, "mod", None) else 0
        if kept:                                       # the windows' changes kept for this one write
            a += "  (+%d kept)" % kept
        self.b_preview.configure(text=p)
        self.b_create.configure(text=a)
        if getattr(self, "lbl_work", None) is not None and getattr(self, "v_work", None) is not None:
            hint = ""                 # what each work is: in the work buttons' hover texts
            if self.v_work.get() == "new" and self.map_only():
                picked = self.v["template"].get().strip()
                hint = ("%s = template of a NEW faction. To change %s itself: Edit faction" % (picked, picked)
                        if picked else "")
            self.lbl_work.configure(text=hint)
            if hint and not self.lbl_work.winfo_manager():
                self.lbl_work.pack(fill="x", padx=16, after=self._work_frame)
            elif not hint and self.lbl_work.winfo_manager():
                self.lbl_work.pack_forget()

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
            return bool(self._places() or self._regions_opts() or self._resources_opts() or self._map_changes())
        return True

    def _map_changes(self):
        """The Map's changes for other factions, as edit.map_changes takes them (empty parts left out)."""
        out = {}
        if self.map_owners:
            out["owners"] = dict(self.map_owners)
        chars = {f: list(cs) for f, cs in self.map_chars.items() if cs}
        if chars:
            out["characters"] = chars
        gone = {f: list(cs) for f, cs in self.map_removed.items() if cs}
        if gone:
            out["remove"] = gone
        # the Map editor: any faction's characters moved, any army's units (found by name and where it stands)
        for key, store in (("moves", self.map_moves), ("army_units", self.map_units)):
            per = {}
            for cid, val in store.items():
                fac, i = cid.rsplit(":", 1)
                fb = self.strat.faction(fac) if self.strat else None
                if fb is None or int(i) >= len(fb.characters):
                    continue
                c = fb.characters[int(i)]
                item = {"name": c.name, "from": tuple(c.xy)}
                item.update({"to": tuple(val)} if key == "moves" else {"units": list(val)})
                per.setdefault(fac, []).append(item)
            if per:
                out[key] = per
        return out

    def _faction_label(self):
        if self.editing():
            return "Edit faction %s" % self.v["template"].get().strip()
        if self.map_only():
            return "Map editor" if self.map_work() else "Map changes"
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
        here = os.path.normcase(os.path.abspath(self.mod.data)) if self.mod else None
        for key, name in (("units", "Unit editor"), ("buildings", "Building editor"),
                          ("characters", "Character editor"), ("terrain", "Terrain editor")):
            ed = self.editors.get(key)
            # only an editor on the mod loaded now: one left on another mod's files never writes into them
            if ed is not None and ed.mod is not None and ed.dirty() and \
                    os.path.normcase(os.path.abspath(ed.mod.data)) == here:
                out.append((key, "%s: %d change(s)" % (name, ed.pending())))
        if self.faction_pending():
            out.append(("faction", self._faction_label()))
        # the own windows' changes, kept for the one write; a part built at the write (a map cut) last of all: it is
        # made on the files as every other part leaves them (towns given meanwhile count)
        for key, part in sorted(self.session_parts().items(), key=lambda kv: bool(kv[1].get("build"))):
            out.append((key, part["label"]))
        return out

    # ---- the session's list: every window hands its changes here, one Apply writes them all ----
    def session_parts(self):
        """{key: {'label', 'plan', 'after', 'mod'}} - the changes of the own windows (a town, a character,
        Mercenaries, Events, Campaign rules, ...) kept for the one write; only those made on the mod loaded now."""
        here = os.path.normcase(os.path.abspath(self.mod.data)) if self.mod else None
        parts = getattr(self, "_session", None)
        if parts is None:
            parts = self._session = {}
        return {k: v for k, v in parts.items() if v["mod"] == here}

    def session_add(self, key, label, plan, after=None, build=None):
        """A window's changes (its plan, made on the files as they are now) go into the session's list; kept again
        they replace the first. At the write each is laid over the files as the parts before it left them
        (plan.rebased: line by line; the same lines changed twice are refused in words). after(bdir) once written.
        build (plan None): a part made only at the write, on the files as every other part left them - written
        last (Map size: a cut counts the towns given on the Map meanwhile)."""
        from .plan import keep
        self.session_parts()
        self._session[key] = {"label": label, "plan": keep(plan) if plan is not None else None, "after": after,
                              "build": build, "mod": os.path.normcase(os.path.abspath(self.mod.data))}
        self._mark_work()
        self.update_actions()
        n = len(self.pending_parts())
        self.status.set("%s - kept. %d change(s) wait for the write: Apply changes (bottom left) writes them all, "
                        "Preview changes shows them." % (label, n))

    def session_kept(self, key):
        return key in self.session_parts()

    def session_drop(self, key):
        if getattr(self, "_session", None) and self._session.pop(key, None) is not None:
            self._mark_work()
            self.update_actions()

    def _part_plan(self, key):
        part = (getattr(self, "_session", None) or {}).get(key)
        if part is not None and part.get("build"):
            return part["build"]()
        if part is not None:
            from .plan import rebased
            return rebased(part["plan"])
        return self.editors[key].make_plan() if key in self.editors else self._faction_plan()

    def _mark_work(self):
        """A * on the work buttons that hold changes not written yet."""
        keys = {k for k, _ in self.pending_parts()} if self.mod else set()
        for val, b in getattr(self, "work_buttons", {}).items():
            base = self.WORK_TITLES[val]
            mine = val in keys or val == self.v_mode.get() and "faction" in keys or val == "map" and "terrain" in keys
            b.configure(text=base + ("  *" if mine else ""))

    def _faction_plan(self):
        plan = self._faction_plan_own()
        extra = self._map_changes()
        if extra:
            from .edit import map_changes
            map_changes(plan, self.v_campaign.get(), extra)
        return plan

    def _faction_plan_own(self):
        if self.map_only():
            places, regions, res = self._places(), self._regions_opts(), self._resources_opts()
            if not places and not regions and not res and self._map_changes():
                return Plan(ModData(self.mod.data), "map", "map", {})
            if not places and not regions and not res:
                if self.map_work():
                    raise ValueError("Nothing to write yet: drag a town, an army, an agent or a fleet, give a town to "
                                     "another faction, change an army's units, paint regions or move resources on "
                                     "the map first.")
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
            if regions:                         # the painted land first: a town or port may be moved onto it
                apply_region_opts(plan, self.v_campaign.get(), regions)
            if places:
                apply_places(plan, self.v_campaign.get(), places, (regions or {}).get("painted"))
            if res:
                apply_resources(plan, self.v_campaign.get(), res)
            if regions:
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
        # REX / M2EX: max_factions follows the factions by itself (written in the same plan, said in Preview)
        return build(ModData(self.mod.data), self.v_campaign.get(), template, name, opts)

    def events_window(self):
        """Events... (top row): the campaign's descr_events.txt."""
        from .gui_events import open_events
        open_events(self)

    def traits_window(self):
        """Traits and retinue... (top row; also in the Character editor): the traits and ancillaries themselves."""
        from .gui_traits import open_traits
        open_traits(self)

    def module_builder(self):
        """Module builder... (top row): a new REX / M2EX add-on made of WHEN / IF / DO blocks (Add-ons has it too)."""
        from .gui_modbuilder import open_builder
        open_builder(self)

    def campaign_rules(self):
        """Campaign rules... (top row): the campaign's settings files as plain values."""
        from .gui_rules import open_rules
        open_rules(self)

    def install_pack(self):
        """Tools > Check and install a pack...: a pack that says 'copy data over the game' checked file by file."""
        from .gui_modpack import open_pack
        open_pack(self)

    def show_text(self, title, text, extra=(), wrap="none"):
        w = tk.Toplevel(self)
        w.title(title)
        w.geometry("900x600")

        def copy_all():
            w.clipboard_clear()
            w.clipboard_append(text)
            status.configure(text="Copied to the clipboard")

        def save_as():
            path = filedialog.asksaveasfilename(parent=w, defaultextension=".txt",
                                                initialfile="CampaignEditor_report.txt",
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

        t = tk.Text(w, wrap=wrap, font=("Consolas", 10))
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
        if not ask(APP, "Fingerprint every game file under\n%s\n\nMod folders in it are left out. "
                                        "For a clean list, let Steam 'Verify integrity of game files' first.\n"
                                        "This reads every file once and can take a minute or two." % root, yes='Fingerprint them', no='Cancel'):
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
        """A small editor for the mod's CampaignEditor_ignore.txt (or an older version's ignore list)."""
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
            # saved under today's name; an older version's list is moved over (its rules kept, nothing lost)
            from .scan import save_ignore
            new = save_ignore(os.path.dirname(path), t.get("1.0", "end-1c"))
            w.destroy()
            self.status.set("Saved %s - press Check mod files again." % new)
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
            if plan.warnings and not ask(APP, msg, yes='Write it in', no='Cancel'):   # else: Undo this write
                return
            self._write([(key or "current", parts[0][1] if parts else "", plan)])
            return
        self._apply_dialog(parts)

    def _apply_dialog(self, parts):
        """Several pieces of work wait: tick which to write (all by default)."""
        w = tk.Toplevel(self)
        w.title("Apply changes")
        w.transient(self)
        frm = scroll_body(w, 12)          # resizable, scrolls when the window is lower than it
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
        done, failed, applied, bdirs = [], None, set(), []
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
            bdirs.append((bdir, label or key))
            part = (getattr(self, "_session", None) or {}).pop(key, None)
            if part is not None and part.get("after"):
                try:
                    part["after"](bdir)
                except Exception as e:                  # the window was closed meanwhile: nothing to show
                    log.write("after write of %s: %s" % (label, e))
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
        if len(bdirs) > 1:                              # Undo this write: the last part, or the whole write
            self.after_idle(lambda: self._written(bdirs[0][0], None, group=list(bdirs)))
        self._mark_work()

    def _menu_hint(self, menu):
        try:
            label = menu.entrycget("active", "label")
        except tk.TclError:
            return
        if label == TEST_MOD_LABEL:
            self.status.set(TEST_MOD_HINT)
        elif label == "Settings...":
            self.status.set("The look (light / dark), the game folder, the map, reports, new versions, set-up "
                            "questions, where the editor keeps its files.")
        elif label == "Help":
            self.status.set("A short guide to the editor (also F1).")

    def delete_mod(self):
        """Tools > Delete this mod's folder...: the loaded mod's folder with everything in it, after two questions
        (the second wants the mod's name typed); never the game's own data or an expansion's. Not undone by
        Restore - its backups lie in that folder too."""
        import shutil
        from tkinter import simpledialog
        from .newmod import deletable_mod_folder
        if not self.mod:
            messagebox.showinfo(APP, "Load the mod to delete first (Mod or Browse..., then Load).", parent=self)
            return
        try:
            folder = deletable_mod_folder(self.mod.data)
        except ValueError as e:
            messagebox.showinfo(APP, "Not deleted: %s." % e, parent=self)
            return
        name = os.path.basename(folder)
        if not ask(APP, "Delete the mod folder\n\n%s\n\nwith everything in it - its files, its "
                                        "backups, its start script? This cannot be undone: Restore cannot bring it "
                                        "back. The game itself is not touched." % folder, icon="warning", parent=self, yes='Delete the folder', no='Keep it', danger=True):
            return
        from .newmod import ever_started
        if not ever_started(folder, game_of(self.mod.data)) and not ask(
                APP, "%s was never started in the game: it has no saved game, and no game log names it. Delete it "
                     "anyway? (Start the game with the mod loaded first, if you meant to try it.)" % name,
                icon="warning", parent=self, yes="Delete it anyway", no="Keep it", danger=True):
            return
        typed = simpledialog.askstring(APP, "To delete it, type the mod's name: %s" % name, parent=self)
        if (typed or "").strip() != name:
            messagebox.showinfo(APP, "Not deleted - the name did not match.", parent=self)
            return
        game = game_of(self.mod.data)
        try:
            shutil.rmtree(folder)
        except OSError as e:
            log.write("Delete the mod %s: not done - %s" % (folder, e))
            messagebox.showerror(APP, "Not all of it could be deleted (is the game running, or a file open in "
                                      "another program?) - %s" % e, parent=self)
            return
        log.write("Deleted the mod folder %s" % folder)
        self.v_path.set(os.path.join(game, "data"))
        self.load()
        self.status.set("The mod %s was deleted; the game's own data is loaded." % name)

    def test_mod(self):
        """The author's stress test (selftest.py): a new mod folder beside the loaded mod with every feature of the
        editor applied, one write each, and its report; optionally a second one with the map 3 x bigger."""
        if not self.mod:
            messagebox.showinfo(APP, "Load a mod (or the plain game) first - the test mod is made from it.")
            return
        from . import selftest
        from .newmod import mod_target
        where = os.path.dirname(mod_target(self.mod.data, selftest.NAME))
        go = _three(self, ["Both", "Only %s" % selftest.NAME, "Cancel"], TEST_MOD_HINT + "\n\n"
                                       "It makes a NEW mod folder %s (or %s_2...) in\n%s\nfrom the loaded mod, and "
                                       "applies every feature of the editor to it, step by step (a minute or two). "
                                       "The loaded mod is not changed.\n\n"
                                       "Also make a second copy, %s_x3, with the campaign map 3 x bigger?"
                                       % (selftest.NAME, selftest.NAME, where, selftest.NAME))
        if go is None:
            return
        result, data, campaign = {}, self.mod.data, self.v_campaign.get()

        def work():
            try:
                result["data"], result["results"], result["text"] = selftest.run(
                    data, campaign, progress=lambda m: result.__setitem__("step", m))
                if go:
                    xdata, warn = selftest.run_x3(result["data"], campaign,
                                                  progress=lambda m: result.__setitem__("step", m))
                    result["text"] += "\nThe 3 x bigger map: %s\n%s" % (
                        os.path.dirname(xdata), "\n".join("    note: " + w for w in warn[:10]))
            except Exception as e:
                result["text"] = "The test mod stopped: %s\n\n%s" % (e, traceback.format_exc())
        th = threading.Thread(target=work, daemon=True)
        th.start()
        self.busy(True)
        t0 = time.time()

        def wait():
            if th.is_alive():
                self.status.set("Making the test mod... %s - %d s" % (result.get("step", ""), time.time() - t0))
                self.after(300, wait)
                return
            self.busy(False)
            log.write("Test mod\n" + result["text"])
            folder = os.path.dirname(result["data"]) if result.get("data") else None
            fine = sum(1 for r in result.get("results", []) if r["status"] in ("OK", "SKIPPED") and not r["new_problems"])
            self.status.set("Test mod: %d of %d steps fine - %s" % (fine, len(result.get("results", [])),
                                                                     folder or "stopped"))
            from .gui_settings import open_folder
            self.show_text("Test mod - every feature (for the author)", result["text"], wrap="word",
                           extra=[("Open the mod's folder", lambda: open_folder(folder))] if folder else ())
            # the game started with what was loaded before: a tester played the plain game, took it for the test
            # mod and threw the test mod away - so the test mod is offered to be loaded and started at once
            if folder and ask(APP, "The test mod %s is ready. Load it now and start the game with it?"
                              % os.path.basename(folder), yes="Load it and start", no="Later"):
                self.v_path.set(result["data"])
                self.load()
                if self.mod and os.path.normcase(os.path.abspath(self.mod.data)) == \
                        os.path.normcase(os.path.abspath(result["data"])):
                    self.start_game()
        wait()

    def check(self):
        """Read every file the tool uses and report; the deep check also rehearses the
        tool's work for every faction in memory (minutes on a big mod). Nothing is written."""
        if not self.mod:
            messagebox.showerror(APP, "load a mod first")
            return
        deep = _three(self, ["Deep check (minutes)", "Quick check (seconds)", "Cancel"],
                      "Check the mod (nothing is written). The deep check also rehearses an edit and a new faction "
                      "for every faction - a few minutes, longer on a big mod.")
        if deep is None:
            return
        from .check import check_mod
        result, data, campaign = {"found": []}, self.mod.data, self.v_campaign.get()
        faction = self.v["template"].get().strip()         # picked: where it is named goes into the report too

        def work():
            try:
                result["text"] = check_mod(ModData(data), campaign, deep=deep,
                                           progress=lambda m: result.__setitem__("step", m), found=result["found"])
                if faction:
                    from .factioncheck import complete, words
                    result["step"] = "is %s complete..." % faction
                    rows, fine = complete(ModData(data), faction, campaign)
                    result["complete"] = (faction, rows, fine)
                    result["text"] += "\n\n" + "\n".join(words(rows, fine, faction))
                    result["step"] = "where %s is named..." % faction
                    result["text"] += "\n\n" + "=" * 70 + "\nWHERE %s IS NAMED (every text file of the mod)\n\n" \
                        % faction + scan_mod(ModData(data), faction, campaign).report()
            except Exception as e:
                result["text"] = "The check stopped: %s\n\n%s" % (e, traceback.format_exc())
        th = threading.Thread(target=work, daemon=True)
        th.start()
        self.busy(True)
        t0 = time.time()

        def wait():
            if th.is_alive():
                self.status.set("Checking the mod... %s - %d s" % (result.get("step", ""), time.time() - t0))
                self.after(300, wait)
                return
            self.busy(False)
            self.status.set("Check finished.")
            log.write("Check mod files\n" + result["text"])
            title = "Check mod files" + (" (and where %s is named)" % faction if faction else "")
            extra = [("Ignore list...", self.edit_ignore)] if faction else []
            if result["text"].startswith("The check stopped"):
                self.show_text(title, result["text"], extra=extra)
                return
            from .gui_check import open_problems         # worst first, each with the place that puts it right
            open_problems(self, result["found"], result["text"], title, extra, result.get("complete"))
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
        """The tool's log - send CampaignEditor.log along with the game's system.log.txt."""
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
        # into the tool's own CampaignEditor_logs next to the exe
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
        from .textio import NotWritten, WriteError
        if isinstance(val, NotWritten):           # the modder's own choice (own mod folder first): said, no error box
            log.write("Not written: %s" % val)
            self.status.set(str(val))
            return
        if isinstance(val, WriteError):           # the system refused a file (held, read-only, disk full): no bug
            log.write("Writing refused\n" + text)
            messagebox.showerror(APP, str(val))
            return
        log.write("ERROR (unexpected)\n" + text)
        if getattr(self, "_closing", False) or not self._alive():
            return                                # the editor is closing: a window now would fail (tester, 0.32.0)
        # plain words, what it means, what to do, a button for it (NN/g error-message guidelines); the same fault
        # again (a mouse-move handler fires many times a second) is logged, not shown again
        last = traceback.extract_tb(tb)[-1] if tb else None
        where = "%s line %d" % (os.path.basename(last.filename), last.lineno) if last else ""
        sig = (exc.__name__, where)
        seen = self.__dict__.setdefault("_errors_seen", set())
        if sig in seen:
            self.status.set("The same fault of the editor again (%s) - in the log; Report a bug sends it." % where)
            return
        seen.add(sig)
        from .gui_util import ask_choice
        try:
            k = ask_choice(self, APP, "Something went wrong inside the editor - a fault of the editor itself, not of "
                                      "your mod.\n\nYour files are safe: a write either finishes with its backup or is "
                                      "put back whole. You can go on working; if the same thing happens again, please "
                                      "send a report so it gets fixed (the logs go with it, your names cut out - you see "
                                      "everything before it is sent).\n\nFor the report: %s: %s (%s)"
                           % (exc.__name__, str(val)[:300], where),
                           ["Send a report...", "Go on working"], default=1, cancel=1)
        except tk.TclError as e:                  # the window went while it was being shown
            log.write("The fault could not be shown: %s" % e)
            return
        if k == 0:
            self.send_report("The editor showed: %s: %s (%s)\n\nWhat I did just before:\n" % (exc.__name__, val,
                                                                                               where))

    def _alive(self):
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

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
            if not ask(APP, text + "\nFiles are put back as they were before it.", yes='Undo', no='Cancel'):
                return
            try:
                ms = restore_to(self.mod, b)
            except (ValueError, OSError) as e:
                log.write("Restore stopped: %s" % e)
                messagebox.showerror(APP, "%s" % e, parent=w)
                return
            back = sum(len(m["modified"]) for m in ms)
            gone = sum(len(m["created"]) for m in ms)
            log.write("Restored %d backup(s) down to %s: %d file(s) back, %d copied item(s) removed"
                      % (len(ms), b, back, gone))
            messagebox.showinfo(APP, "Undid %d change%s: %d file(s) put back, %d copied item(s) removed."
                                % (len(ms), "" if len(ms) == 1 else "s", back, gone))
            w.destroy()
            self.load()
        ttk.Button(w, text="Undo back to here", command=go).pack(pady=(0, 6))

def _three(parent, words, text):
    """A question with two answers and Cancel, in words: True / False / None (Cancel)."""
    from .gui_util import _patched
    if _patched("askyesnocancel"):              # a check script answers for the user
        return messagebox.askyesnocancel(APP, text)
    k = ask_choice(parent, APP, text, words, cancel=2)
    return None if k == 2 else k == 0


def main():
    log.session_start()
    log.write("Start %s %s (in %s)" % (APP, VERSION, log.exe_dir()))
    app = App()

    def close():
        app._closing = True                       # from here a fault is only logged, no window opens
        app.save_session()
        try:
            app.destroy()
        except tk.TclError as e:                  # the editor goes anyway; say it in the log, never in a box
            log.write("Closing: %s" % e)
    app.protocol("WM_DELETE_WINDOW", close)
    import atexit
    atexit.register(app.save_session)             # also when the window goes another way
    app.mainloop()
