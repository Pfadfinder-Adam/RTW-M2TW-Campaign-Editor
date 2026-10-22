# New faction

A new faction is **cloned from a template** - a faction that already works in the game. The clone starts in
the game at once, so you can test every change after that straight away. The template is never changed.

## From zero

**New faction > From zero...** makes a faction with nothing of an existing one, step by step:

1. **Culture** - its towns on the map, portraits, agents, the buildings and units open to it. A faction of that
   culture lends the new one its lines in the game's lists, inside the files only; it is never shown as a template.
2. **Names** - full, short, adjective, people (plural); the internal name is made from them.
3. **Colours** - pick them, or click one of the free pairs (none near any faction's). Colours like another
   faction's are said.
4. **Emblem** - your symbol (a square PNG with a clear background is best), fitted once and made into every sign:
   menu buttons, loading screen, logos, the flag on the map, its 3D symbol, banners, captains' cards. A must - a
   symbol that looks like another faction's is said.
5. **Name list** - mixed from every faction of the culture, so it is no one faction's list (Name list... to type
   your own).

**Fill the form** puts it all on the New faction tab: pick its towns, capital and leader there, then **Create
faction**. One Apply writes it with its emblem and recolours every picture it got (cards, battle textures,
sprites) in its own colours. Check mod files lists anything it still shares (TRACES OF ANOTHER FACTION).
**Forget it** makes it a plain copy of the template again.

## Steps

1. **Factions** at the top, its **New faction** tab; load the mod, pick the campaign.
2. **Template**: the faction to copy. The new one gets its culture, units, buildings, character models, name
   lists and pictures - a clean clone: none of the template's trait or ancillary triggers.
   **From another mod...** (under it): take a faction of another mod of the same game instead - pick the mod
   (it is only read) and the faction. The window fills with its names, colours and descriptions. It is made
   **from zero**: the Template row and the template's options are put away - a faction of your mod of the same
   culture only gives it its lines in the game's lists, inside, nothing of it is seen (its relations start neutral,
   its own pictures come along), and its select map is a stand-in - your map with no land
   lit - until you give it towns and press Art's **Draw from the map**.
   Apply brings what is the faction's own: its
   units (with their models, cards and recruit lines; a unit your mod has just the same is shared), its name
   lists, its figures on the campaign map and in battle, its banners, flags, icons and pictures. Its leader and
   heir fill the window; on Apply its whole family (generals with their bodyguards, wives, children, the family
   tree) stands by the capital you pick, and its towns' garrisons are 3-6 of its own units, drawn as for an empty
   town. Its armies, towns, scripts and events do not come - pick its towns on your map.
   **Forget it** makes it a plain copy of the template again.
3. **Internal name**: lower case, no spaces, for example `epirus`.
   **Comes into the campaign**: *on the map from the start* (the usual), or later - *by an event* (a date and a
   region the rebels hold - in another faction's region the game kills it as the campaign loads), *as the shadow of a faction* (its civil war) or *splitting off a faction in a revolt* - all three only in Barbarian Invasion and Medieval II: plain Rome, also with REX, stops reading descr_strat.txt at a faction that starts dead (the rebels' garrisons and the diplomacy are lost), so there only *on the map* is offered. A faction that
   comes later starts dead: no towns, no leader, only its money, nonplayable (the towns and leader below are not
   used); Events... (top row) changes it afterwards.
4. **Name (full)**, **Name (short)**, **Adjective**: for example `Kingdom of Epirus`, `Epirus`, `Epirote`.
   The copied texts use them ("Epirote Spy", "Your forces attack an army of Epirus").
   **Colours**: the faction's primary and secondary colour (empty at first; left empty, the template's stay). **Emblem everywhere...** beside them takes one
   picture - the faction's symbol - and makes every sign of the faction from it in those colours: the menu
   buttons, loading screen, logos, the flag on the campaign map and its 3D symbol, the battle banners, the
   flag on its towns, the captains' cards (the same window as the Art tab's **Faction emblem**).
5. **Starting settlements**: **Towns on the map...** (under Capital) opens Maps - click the towns, **Done**
   brings you back (nothing lost); **Capital on the map...** picks the capital with one click. A double click (or **Rename...**) changes the names players see of a region and its town. A new region painted on the [[Campaign map]] can be a starting town too.
6. **Leader** (and the heir if you like): a first name and surname **from the faction's name list** - the
   game crashes on a name that has no text, so the tool only accepts listed names. The new faction copies the
   template's list, or has one of its own: **Name list...** (below).
   **Leader's title** / **heir's** (under the names): what the game calls them - empty at first, and left empty
   the template's (King, Prince) stay; write others if you like (Duke, Grand Prince...).
7. **Victory** (under the leader): what the player must do to win - starts as the template's.
   The other tabs if you want: garrisons, buildings, diplomacy (alliances and wars at the start), [[Faction art]].
8. **Preview changes**, then **Create faction**.
9. Start a **new** campaign - old saves do not know the faction.

## What the clone writes

- `descr_sm_factions.txt` (+ REX's `.json`): the template's block, before `slave`.
- `descr_character.txt`, `descr_names.txt`, `export_descr_unit.txt` (ownership),
  `export_descr_buildings.txt` (faction lists), `descr_model_battle.txt` / `descr_model_strat.txt` (texture
  lines), Medieval II's `unit_models/battle_models.modeldb` (the template's texture and attachment entries in
  every battle model, copied for the new faction - a mod folder without its own modeldb gets a copy of the
  game's), `descr_banners.txt`, `descr_lbc_db.txt`, `descr_offmap_models.txt`, `descr_building_battle.txt`,
  win conditions (no trait or ancillary triggers: the clone is clean).
- Texts: every string that names the template, with the new names.
- `descr_strat.txt`: the faction's block, towns, leader, heir, armies, diplomacy.
- **Pictures of its own**: every picture named after the template is copied under the new name
  (`map_macedon.tga` -> `map_epirus.tga`, `ui/units/macedon/` -> `ui/units/epirus/`). Banner textures and
  the loading-screen logo, which the files name by path, are copied too (`standard_macedonia.tga` ->
  `standard_epirus.tga`) and the new faction's lines point at the copies. Pictures several factions share
  (the rebels' and the routing banner) stay shared until you replace one in [[Faction art]].

## How the towns are handed over

- A town moves as a whole `settlement { }` block, so no region gets two.
- **One army per town** at the start: the leader holds the capital, the heir the second town (or stands
  next to the capital).
- The previous owner's generals and agents move to one of its other towns.
- The leader's army is sized like the armies of factions with about as many towns (**balanced**), or copied
  from the template, or just the bodyguard.

## Limits

- One campaign per run.
- Copied texts keep the template's wording apart from the names ("the wicked Seleucids..."): edit them in
  the text files if you care.
- **Faction count**: the game takes a set number of factions, `slave` included - plain Rome 21, Medieval II 31.
  REX and M2EX read it from `max_factions` in the mod's own `data/descr_ex.txt` (a mod without one runs on the
  engine's defaults - the game's copy is not read for it). After Load the status line says how many
  there are. REX and M2EX have no faction limit of their own: every new faction raises `max_factions` in the
  mod's own `descr_ex.txt` by itself, written with the faction (Preview says so; Restore takes it back) - and any
  other write puts a line that is too low right too. Only the original exes stop at 21 / 31 - over that the game
  closes at start ("Too many factions described here").
- **With REX or M2EX there are no limits at all**: factions, regions, religions, cultures, units, buildings, the
  family's children and retinue - the editor never refuses or warns for a number; the engine's setting lines
  (`max_factions`, `max_num_children`, `max_num_ancillaries`) are rewritten to fit by themselves.
- **Names**: every character of a faction needs a name of its own - the game skips a second one with the same
  name. The tool picks free names and refuses a taken one.

## A name list of its own

**Name list...** (under the leader and heir) gives the faction a name list of its own, in three steps: men's
names, surnames (may stay empty) and women's names. Type or paste them - one per line, or separated by commas
(then a name may have spaces: *Abd al-Malik*); without commas or new lines, spaces separate the names. Each step can
copy or add the names of any faction. The tool writes the faction's own section in `descr_names.txt`, the names the
game shows in `text/names.txt` and the keys in `descr_names_lookup.txt`; only Latin letters, digits, ' and - are
taken (the game's files and font take no others). The leader, heir and captains then take names from it.
