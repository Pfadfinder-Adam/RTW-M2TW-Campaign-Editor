# Changelog

## 0.17.0 - 2026-09-29

REX's new features, read from REX's own notes, and two things the tool got wrong on Medieval II.

### Fixed
- **Medieval II recruitment lines**: Medieval II recruits with `recruit_pool` lines (the vanilla buildings file has
  1475 of them and no `recruit` line at all), but the Roster tab, unit renames, unit packs, "Copy as new" and the
  line checks read only Rome's `recruit`. On Medieval II the Roster showed no place a unit is recruited, a renamed
  unit kept its recruit_pool lines on the old name, and unit packs carried no recruit places. One reader now knows
  `recruit`, `recruit_pool` and REX's retrain-only `retrain` / `retrain_pool`; "Add line" writes the file's own form
  (Medieval II: units at the start, new units a turn, most units waiting). Checked on vanilla Medieval II (england:
  37 of its 46 units recruited, with their buildings) and Rome.
- **Forts** (`fort x y ...` lines in descr_strat, Medieval II and REX) were not read: a fort line inside a faction's
  block was taken as part of the character before it (moved or removed with him), and armies could be placed on a
  fort's tile. Forts and watchtowers are now read on their own, drawn on the map (owner, name and "permanent" on
  hover, in the legend) and their tiles kept free; the terrain editor keeps their ground.

### Added
- **REX bracket requirements**: one requires line may carry several `factions { }` groups, each with conditions of
  its own (`( ( factions { greek, } and ... ) or ( factions { middle_eastern, } and ... ) )`). Every group is read;
  giving a unit or a level joins the first group (said in Preview), taking removes the faction from every group,
  and a group it alone forms is left for a person to rewrite, said in plain words. Unit packs name their owners in
  every group.
- **Unit editor: what REX adds to units** - a REX... button next to the attributes, stat_mental, stat_ground and
  weapon lines ticks REX's words with their effect in plain words: expendable, elitist, steadfast, intimidate,
  immune_to_psychology, relentless, disciplined_missile, inexhaustible, brace_for_charge, aggressive_push,
  disciplined_charge, ai_cannot_skirmish, ai_cannot_toggle_formation, desert_raider, forest_ambusher,
  troublemaker, police, client_kingdom_only_units, infinite_ammo, no_scale, single_entity, sp (shield piercing).
  `recruit_priority_offset` may be added although no unit of the mod has one yet.

## 0.16.1 - 2026-09-29

The user's Medieval II run (scotland: Edinburgh castle and back, Inverness taken and made a city): the game started
and ran with the changes, and its own log converts buildings the same way the tool does ("Conversion target
building not specified ... building will disappear during conversion").

### Fixed
- **City / castle with a size set by hand**: Inverness (a castle town) made a city and raised to a large town got
  its governor's building fitted to the file's old size at the write (`wooden_pallisade` in a large town - Preview
  warned "the game refuses to load that"). Buildings picked in the window keep the governor's building fitted
  there; without picks the fit follows the size set by hand. Preview now says "wooden_pallisade becomes
  wooden_wall" instead of "goes".

## 0.16.0 - 2026-09-29

### Added
- **Medieval II `battle_models.modeldb`** (asked for by the Stainless Steel author): the tool reads and writes the
  battle model database the game loads (a Boost text archive: length-prefixed strings, class info on a class's
  first appearance - the vanilla file of 701 models reads back byte for byte). **New faction**: every battle
  model with texture or attachment (shield) entries for the template gets the same for the new faction (vanilla
  england -> 121 models), so its units are not untextured in battle; a mod folder without its own modeldb gets a
  copy of the game's with the additions. **Unit packs** carry their modeldb models with the meshes, textures and
  sprites they name; on import a model with the same name and other content is added under a free name in
  modeldb and descr_model_battle.txt alike (the unit's soldier / officer lines and mounts follow), and every owner
  gets texture entries in both files (from the model's mercenary texture, else its first). Checked on vanilla
  Medieval II (clone england -> wessex, pack export / import, Restore byte-exact); not yet in the game.
- **Unit packs give every new owner a texture line** in descr_model_battle.txt (Rome too), instead of only
  warning that one was missing.

### Fixed
- **"<army> stands on x, y - move it first" when moving a town** (the user's HLR log): taking Odessus sent its
  garrison out to the next free tile, the very tile the town was then moved to, and Apply refused every time. An
  army on a moved town's new tile now steps aside to the nearest free tile of the region (said in Preview).
- **Unit packs (Medieval II)**: a model named `Feudal_Knights` in the unit and `feudal_knights` in
  descr_model_battle.txt was not found (the game reads these names without case) - now it is.
- **An early 0.12 names-by-culture module** (`<mod>/script/modules/ft_settlement_names.nut`, with guessed REX
  calls, which REX loads as a script module) is found on Load; with a yes its names move into the campaign
  script (REX's documented way) and the module goes.

## 0.15.1 - 2026-09-29

### Changed
- **City or castle: Medieval II only, twice checked.** The switch shows (and the write is allowed) only when the game
  is Medieval II (its exe, else its data) **and** its buildings mark castle levels; Rome, Barbarian Invasion and
  Alexander never show it, and a castle asked for there is refused before anything is written.
- **A castle never outgrows castles**: picking huge city for a castle on the Buildings tab is refused with the reason
  (castles end at the citadel, a large city - make it a city first), and Preview refuses such a castle too.

## 0.15.0 - 2026-09-29

### Added
- **City or castle (Medieval II)**: *Settlement is a* city / castle on the Buildings tab (New and Edit faction).
  A castle is the settlement's `settlement castle` line in descr_strat plus castle buildings; the tool switches the
  line and converts the buildings as the game does - each level becomes the level its `convert_to` names in the
  matching chain (core_building <-> core_castle_building, barracks <-> castle_barracks, a church <-> a chapel,
  roads <-> castle roads...), a level without one goes (a castle has no market or town hall), and the governor's
  building is fitted to the settlement level (a castle's equals it, a city's is one below). Afterwards only that
  kind's buildings are offered. A huge city cannot be a castle (castles end at the citadel, a large city) - the
  tool says so. Preview lists every building converted or gone. Checked on vanilla Medieval II (england: London a
  castle, Nottingham a city; Restore byte-exact); not yet in the game. Rome has no castles: not shown there.
  (Asked on Discord - the tool only made cities before.)

## 0.14.1 - 2026-09-29

### Fixed
- **Name list... on Medieval II**: vanilla M2 has surname keys with a space (`de Lyon`, `von Saxony`, `al Rashid` -
  8 factions' characters carry them). A new list kept such names as `de_Lyon`, another key, so the game would not
  have found the characters' names. Names the characters already carry are now kept exactly as written; new names
  are still written with `_` instead of a space (the game and its console want no space inside a name:
  `"Gaius Julius_Caesar"`, vanilla Rome's `of_Scaldis`), and the wizard says so.

## 0.14.0 - 2026-09-29

Name lists of one's own and every town's names by culture in one table (the user's wishes). Checked on a plain Rome
copy (the julii's own list: Preview, the names kept that its characters carry; a new faction with its own list in
the synthetic mod, Restore byte-exact) and in the window; not yet tested in the game.

### Added
- **Name list...** (Faction tab, under the leader and heir; New and Edit faction): a faction's own men's names,
  surnames and women's names in three steps - type or paste them, one per line or separated by commas (then a name
  may have spaces), or by spaces; each step can copy or add another faction's names. Written together: the faction's
  own section in `descr_names.txt` (a section it shared, as in BI, is left to the others), the shown names in
  `text/names.txt` and the keys in `descr_names_lookup.txt`. The leader, heir, captains and family records take
  names from the new list in the same Apply. Editing: names the faction's characters and records already carry
  stay in the list (Preview says which) - the game crashes on a name that is in no list. Only Latin letters,
  digits, ' and - (the game's files and font take no others).
- **All towns' names...** (Faction tab, the per-town dialog, Tools): every town's names by culture in one table -
  a column per culture, the owner, its culture and the name shown now; sort by any column, filter by culture
  (with / without a name for it), by the owner's culture, by what waits for Apply, search; double click a cell to
  type a name in place. Towns the mod's own campaign script renames show grey and are left alone.

### Noted
- Big maps: a tester's mod with a campaign map of **5456 x 2464 tiles** (map_regions.tga pixels) loaded in the tool, regions painted on it.

## 0.13.0 - 2026-09-29

Settlement names that follow the owner's culture (REX), shown live in the window. Checked in the window on a
plain Rome copy (the julii taking Mediolanium); not yet tested in the game.

### Added
- **Settlement names by the owner's culture (REX)**: **Names by culture...** (next to Edit region..., and on the Map's
  region bar) gives a town a name for each culture - Roma for the Romans, Rom for the barbarians - and a name for
  every other culture. The tool writes it into the campaign's `campaign_script.txt` (made, with its `script` line
  in descr_strat, when the campaign has none; a script of the mod's own is kept around the tool's block): REX
  renames the town with its `rename_settlement` as soon as a general takes it and at each of its owner's turns
  (`SettlementTurnStart` / `GeneralCaptureSettlement` + `SettlementName` + `FactionCultureType`, from REX's own
  documentation). Needs REX; backup and Restore as for every write. Not yet tested in the game. (Asked for on
  Discord.)
- **The name shows at once in the window**: as soon as a town changes hands in the tool (taken or given on the
  Faction tab or the Map, a new faction's start towns), the Map labels it with the name for its new owner's
  culture, the status line says it ("Mediolanium (now Mediolanum) added"), and the towns list shows the name the
  town has now ("(shown: Medhlan)"). A name set in Names by culture... shows on the map the moment OK is pressed.

### Fixed
- **New mod folder made from Barbarian Invasion or Alexander** (REX): its start file now starts that game (`-bi` /
  `-alx`, as REX's own start files do). Without it REX read the mod over the plain game's data, and the menu's
  imperial campaign was read with BI's factions (the user's log).

## 0.12.0 - 2026-09-29

Built from a tester's questions and the user's Barbarian Invasion run. Checked on Rome (plain + REX) and
Medieval II copies, in the window on Linux and with the deep Check; the flag symbols and logos not yet in the game.

### Added
- **Flag symbol and faction logos** (Rome): the Art tab now lists the symbol on the faction's campaign-map flags
  (`banners/symbolsN.tga.dds`, slot `standard_index`) and its faction logos (the faction button, `logo_index`;
  the small logo, `small_logo_index`), and **Replace...** changes them. A new faction gets its own flag slot and,
  under REX (`sprite_format xml`), logo sprites of its own with the template's pictures copied in, so the
  template keeps its own. A faction sharing a slot or sprite gets its own on Replace. (Asked for by a tester.)
- Terrain editor: **Climates** - paint each land tile's climate (`map_climates.tga`: trees and plants on the
  campaign and battle maps, winter snow, heat). The climates and their colours come from the mod's own
  `descr_climates.txt`, so Rome, Medieval II and mods with their own climates all work; the map shows the
  climates in their colours while this mode is on. Undo / Redo, backup and Restore as for the ground.
  (Asked for on Discord.) Adding a *new* climate is not in yet.

- Family / Character editor: Preview warns when a character gets more ancillaries, or a parent more children,
  than the game takes - REX's `max_num_ancillaries` / `max_num_children` in `descr_ex.txt` (the mod's, else the
  game's), else the original game's 8 and 4.

### Changed
- Terrain editor: long palettes wrap into rows, so every brush stays inside the window.
- **Restore a backup...**: pick any write in the list and **Undo back to here** undoes it and every later one in
  one go - no more restoring one by one. The list says when, what (faction, template) and how many files.
  Two writes made by one Apply are undone in the right order.

### Fixed
- Building editor: **Add line** refused a new `recruit` line once a level had as many as the busiest level of the
  mod ("no building level in this mod has more than 101 'recruit' lines"). Recruit lines only list units and the
  game takes any number of them, so they are no longer held to that rule. (Reported by a tester.)
- Buildings tab: a town showed **another culture's pictures** (BI's Eastern Empire got barbarian huts) and empty
  boxes for pictures that exist. The pictures are now looked for only in the town's own culture (and the cultures
  `descr_ui_buildings.txt` sends it to), in the mod and then in the game's own `data` - where Barbarian
  Invasion and REX mods take what they do not have. A level with no picture of its culture says so.
- A captain made for a garrison could get the name of one of the faction's **family members** (egypt's
  Heruben), which the game skips as a duplicate - captains now skip the family's names and the names of
  characters added in the same Apply. Medieval II first names of two words (egypt's `al Adil`, which the game
  reads as first name `al`) are no longer picked as first names.
- Linux: without tkinter the tool now says which packages to install instead of a Python error.
- Barbarian Invasion: the Eastern / Western Empire had no names ("no name in empire_east's name list for a
  captain"). BI's `descr_names.txt` gives one name list to several factions (`faction: empire_east,
  empire_east_rebels`); the tool now reads such lists for every faction on them, and a new faction cloned from
  one gets a list of its own.

## 0.11.0 - 2026-09-29

Tested in the game by the user on Rome + REX: a new faction (Nabataea) made in a few clicks with new regions,
its own pictures shown everywhere, the painted terrain drawn; the bugs he found are fixed here.

### Added
- **Faction limit**: the tool knows how many factions the game takes (slave included) - the original exes stop
  at 21 (Rome) / 31 (Medieval II); REX and M2EX read `max_factions` in `data/descr_ex.txt`. Load says "N of max
  factions"; a new faction over it is refused before anything is written, or - with your yes - `max_factions`
  is raised in the same write (backup, Restore). Over the limit the game closed at start ("Too many factions
  described here, maximum is(21)").
- Family: **someone already in the faction can be the wife or the child** - a new faction's heir can become its
  leader's son; before, only new people could be added, so a new faction's tree could not be built.
- Terrain: **Redo stroke**; the bottom Undo / Redo (and Ctrl+Z / Ctrl+Y) undo and redo strokes in the Terrain
  editor.

### Changed
- The tool's log `faction_tool.log` now lies in `RTW-M2TW-Campaign-Editor-files\logs`, together with the
  logs zips from **Save logs** - one folder to find what to send. The settings stay in
  `RTW-M2TW-Campaign-Editor-files`; a log an older version left there moves into `logs` by itself.

### Fixed
- **Two characters of one faction with the same name**: the game skipped the second ("duplicated character name
  in this faction, skipping") - an army named like the leader, a spy named like an automatic captain. Names now
  stay unique in a faction: the automatic captain skips taken names, the New army / agent dialog refuses one,
  and Preview refuses a write that would repeat a name.
- **Rivers**: the game follows a river side to side and stops where two river tiles touch only by a corner -
  everything past it is not drawn (the user's test). The 1-tile river brush now fills such steps itself, and
  Preview names every river piece that joins no sea, map edge, source or other river.
- Family buttons with nobody picked now say to pick a person instead of doing nothing.
- Portrait library: the portraits filled only one column when the window opened.
- Character editor: traits for `Characters all` are offered to everyone; ancillaries barred to the faction's
  culture (`ExcludeCultures`) are no longer offered.
- Rome portraits: young, old and dead of the same man are shown; the greyed Replace buttons gave way to a plain
  line and **Portrait library...** (Rome gives no portrait of one's own; Medieval II keeps Replace).
- The bottom Undo in the Terrain / Character editor did nothing and named the building editor.
- **A new faction's banners were the template's files**: `descr_banners.txt` kept the template's texture paths,
  so replacing the new faction's banner in the Art tab would have changed the template's too. A new faction now
  gets banner textures and a loading-screen logo of its own, named after it (`standard_macedonia` ->
  `standard_epirus`), and its lines point at them; the template's files stay untouched.
- The loading-screen logo (`loading_logo` in descr_sm_factions) was copied under the new name but the line
  still named the template's picture: it now names the copy.
- Replacing a `.dds` picture (Rome's `*.tga.dds` banner textures) wrote a TGA inside the .dds name; it now
  writes a real DDS in the format of the one replaced (DXT1/3/5, with its mipmaps).
- Two writes in the same second no longer fail on the backup folder's name.
- Medieval II portrait library (checked on the game's own southern_european pools): a new portrait no
  longer makes Rome-only folders (`cards`, `old` for groups that have none), and a new princess also gets
  her dead portrait (`portraits/dead/princesses`) - without it the game would show its placeholder.

### Added
- Art tab: a picture several factions share (the rebels' or routing banner) becomes the faction's own copy when
  replaced - written under its own name, and only this faction's line points at it.
- Art tab: **Back to the original** puts back a picture the tool changed (as the first backup kept it; for a
  new faction, the template's picture it was copied from). A pending change still has *Keep the current one*.
- Art tab: each picture says which file and line names it, and who shares it.

## 0.10.0 - 2026-09-29

### Added
- **Terrain editor** (its own work at the top): paint the campaign map tile by tile - the ground (fertility,
  wilderness, forests, hills, mountains, high mountains, swamp; the kinds of sea) and the marks across it
  (rivers, fords where armies cross, river sources, cliffs). Land stays land and sea stays sea; nothing the game
  refuses goes under a town, port or character; Preview warns about a broken river. Apply writes
  `map_ground_types.tga` and `map_features.tga` with a backup and deletes `map.rwm` (the game builds its map
  again). Not yet tested in the game.
- The map draws each feature in its own colour (rivers, fords, sources, cliffs, volcanoes).

### Fixed
- Medieval II's impassable land (`64 64 64` in map_ground_types) now refuses characters like mountains do.

## 0.9.4 - 2026-09-29

### Fixed
- **Barbarian Invasion (bi) would not load its campaign** ("invalid literal for int() ... 'Pictii'"): an entry
  of its `descr_regions.txt` has a line more before the colour. The file is now read by one reader for
  everyone (the colour line anchors each entry), and the tool's writers (Edit region, region tags) use it too.
- Loading a Rome mod after a Medieval II one with *Edit faction* on no longer shows "france has no faction
  block": a faction the new mod does not have is cleared.

### Changed
- Scan mod knows the **Barbarian Invasion** files (the game manifest now has `bi/`, from the user's install).

## 0.9.3 - 2026-09-29

### Added / changed
- **Portrait library** (Character editor): every portrait of a culture - young, old, dead; generals, civilians,
  rogues - as the game hands them out; **Add portraits...** puts new ones in the culture's size and depth with
  their cards under the next free number in every folder of the group (the dead one greyed unless given);
  Medieval II: **Use for <character>** makes a picked one his own.
- **Art tab: the campaign-select map is an optional part** that opens and closes (a line at the top). It is
  closed and **off by default: every `map_<faction>.tga` stays the original** - nothing is drawn over it, for a
  new faction, taken towns or painted regions alike. Ticked, the faction's map is drawn from its towns and the
  maps of the factions whose land changes follow, as before. Closed, the pictures take the whole tab.

## 0.9.2 - 2026-09-29

### Changed
- **New name: RTW & M2TW Campaign Editor** (it edits Rome: Total War and Medieval II: Total War alike). The exe
  is now `RTW-M2TW-Campaign-Editor.exe`; its folder `RTW-Campaign-Editor-files` is renamed to
  `RTW-M2TW-Campaign-Editor-files` on the first start, so the log and settings stay.

## 0.9.1 - 2026-09-29

### Added
- **Edit region...** (Map region bar and under the towns list): a new region's data again (names, builder,
  rebels, tags, triumph, farming, owner, size; a rename follows on the map, the towns and garrisons), and the
  `descr_regions.txt` lines of a region of the map (builder, rebels, region tags, triumph, farming).

### Fixed
- A new region shows in the towns list on the Faction tab at once (it only came after Apply).
- A **new faction** can start in a region made in the same session: the map, the region and the faction are
  written by one Apply (the region first; the faction takes it as a rebel village). Characters placed next to
  a new town stand on the new region's land as painted.

## 0.9.0 - 2026-09-29

### Added
- **Character editor** (its own work at the top, like the unit and building editors): any faction's
  characters and family tree, written on its own Apply with a backup.
- **Portraits** on the family tree and in the person form, as the game shows them: Rome's culture pool
  (the game picks one at random - the tree shows one of them and says so) and the family pictures of
  members off the map; Medieval II's own portraits (`ui/custom_portraits/<folder>/portrait_young|old|dead.tga`
  + `, portrait <folder>` on the character's line). **Replace...** writes a Medieval II character's own
  portrait from a PNG / JPG / TGA in the size of the mod's portraits.
- README: how to install (the exe in a folder of its own) and what the tool does with your own pictures.

### Fixed
- Restore removes the folders a run made for its new files when they are left empty.

## 0.8.0 - 2026-09-29

### Added
- **Family tab (Edit faction)**: every character of the faction and the family tree, drawn the way the
  game shows it (couples side by side, children below, leader and heir marked). Edit a person's name
  (from the faction's name lists), age, sex (off the map), traits with levels and ancillaries; give a
  wife, add a child, take someone off the tree, leave a family member out. The tree is checked before
  writing (everyone on it is of the faction, husband a man, wife a woman, one set of parents, nobody
  their own ancestor). New family members are written as `character_record` lines in the file's own
  form (Rome with the four skills, Medieval II without), the tree as `relative` lines after them.
  Checked on the vanilla files of both games (julii, england): preview, write, Restore byte for byte.

### Fixed
- Renaming the leader or heir on the Faction tab now renames him on the family tree (`relative`
  lines) too; before, the tree kept the old name.

## 0.7.5 - 2026-09-29

### Fixed
- **Medieval II: crash on load after taking a castle** ("The castle core building level should be
  EQUAL the settlement level!"): a castle's governor's building (`core_castle_building`) stands at
  the settlement's own level (motte_and_bailey = village, wooden_castle = town, castle = large
  town...), not one below as in towns and cities. The tool raised a village castle to a town; now it
  keeps castles at the right level. Towns and cities (and Rome) are unchanged.

### Changed
- README: how to report a problem (Save logs zip + a video or screenshot).

## 0.7.4 - 2026-09-28

### Fixed
- **Art tab: the picture list was squeezed to a strip** by the campaign-select map blown up to 2x;
  the map now takes at most about 40 % of the tab's height (and half its width), smaller on small
  windows, so the pictures below keep their room.

## 0.7.3 - 2026-09-28

### Changed
- **Tools > Save logs (zip)** offers RTW-Campaign-Editor-files\logs next to the exe (not the game's
  folder), so everything the tool writes for itself stays in one place.

## 0.7.2 - 2026-09-28

### Changed
- The tool's own files (faction_tool.log, faction_tool_settings.json) go into the folder
  **RTW-Campaign-Editor-files** next to the exe instead of lying loose beside it (in Downloads they
  mixed with everything else); files an older version left beside the exe are moved in once.

## 0.7.1 - 2026-09-28

### Fixed
- **Preview / Apply changes, Undo, Tools... disappeared** when a tab was taller than the window
  (a smaller screen, a window made smaller): the buttons and the status line are now held at the
  bottom first and the tab shrinks instead (checked on a 1000 x 640 window on every tab).

## 0.7.0 - 2026-09-28

The first release since 0.1.2: it holds 0.2.0 - 0.6.0 below (those were test builds) and this.

### New
- **Unit packs (export / import)**: Unit editor -> Export pack... takes the picked unit (or every
  unit the list shows) with its models, mount, engine, animal, textures, sprites, cards, names,
  descriptions and recruit places into one .zip; Import pack... puts it into another mod of the same
  game: taken names get free ones, the owners are picked, a model with other lines under the same
  name is added under a new one, files that exist are never overwritten; Preview, backup, Restore.
- **A new region given to the faction you edit** is one of its towns at once (garrison, buildings,
  capital) and is written with it in one Apply (one backup).
- **New region: builder, rebels and religions** come from the region its land is cut from unless
  picked; religions are written only when they add up to 100 (else the donor's), so a skipped or
  zeroed dialog cannot break the game.

### Fixed
- **Campaign-select map (Medieval II) lit in the wrong place in the game** (shifted right): the
  place of the map inside the picture is now learnt from where the game lights each vanilla faction
  on its own map (a scale per axis); the land is filled solid (the see-through fill looked poor),
  the picture's border lines kept.
- New faction with no faction named: the buttons say Preview / Apply changes (not "map changes"),
  the work bar says only the map is written.
- The Art tab's "Finding where the map lies..." line no longer stays in the status bar.

## 0.6.0 - 2026-09-28 (test build)

### New
- **Map by tiles**: the ground is drawn one colour per tile (mountain, land, water - the type the
  tool checks), relief and rivers per tile too, so the picture and the tile grid agree; the detailed
  picture is still in Layers.
- **Medieval II straight from Steam gets unpacked by the tool**: Load on a game whose files are
  still in packs/ offers (with a yes) to copy msvcp71.dll and msvcr71.dll from the game folder next
  to tools/unpacker and run the game's own unpacker; then it loads the unpacked data.
- **Set-up problems fixed on Load with a yes**: M2EX's `vegetation_source text` without the raw
  vegetation maps (the game closed at start) is set to `binary`, with a backup.
- **One Apply for all the work waiting**: a `*` on the work buttons marks changes not written
  yet (Edit faction, Unit editor, Building editor). When several hold changes, Apply lists them
  with ticks and writes them one after another - the editors first, then the faction and the
  map - each with its own backup; Preview shows them all. Changes in an editor now survive an
  Apply elsewhere (they are dropped, with a message, only when their own file was written).
  Picking another faction in Edit with changes not written asks: apply, drop, or stay.
- **Dark theme** (Dark / Light at the right of the work bar, kept for the next start).
- **Tabs stand out**: bigger, bold, the open one coloured like the work bar's button.
- **Map**: the ground tile by tile (one square = one tile), relief from map_heights, rivers,
  fords and cliffs from map_features, a tile grid when zoomed in (Layers menu, kept); denser
  political colours; a new region's land, town and port show on the normal map until Apply.
- **Unit / Building editor lists**: Show (a faction, a culture, a category, a class,
  mercenaries only / none, general's units; building chains by who may build them, their kind,
  recruiting or not) and Sort (name, owner, category, class; who may build, kind).
- **Units & armies**: own units / mercenaries / own + mercenaries next to the category;
  the armies, agents & fleets list filters by kind and sorts by a click on a heading.
- **Art tab**: the campaign-select map shown up to twice as big, the pictures in as many
  columns as fit; every picture named (battle-select picture, units picture on the faction
  screen, symbol on the faction screen, faction symbol, victory conditions map...) with where
  the game shows it.
- **Medieval II mods**: New mod folder makes `<game>/mods/<name>` with `<name>.cfg`
  (`[features] mod = mods/<name>`, the base mod's own .cfg when it has one) and a
  `Start_<name>.bat` that starts the game with it.

### Changed
- New region: "Resources" is now **Region tags (hidden resources)**, explained (descr_regions
  line 6: what buildings' `resource` / `hidden_resource` requirements ask for, not the goods
  on the map), with the tags the mod uses listed.
- New mod folder says plainly what the linked files are: full size in Explorer, no disk space,
  deleting the folder never touches the game.
- Undo no longer reaches back into the faction edited before.

## 0.5.0 - 2026-09-28

### New
- **Roster tab** (Edit faction): every unit and building level of the mod and whether
  the faction has it (by its own name, its culture or everyone); **Give / Take away**.
  Apply keeps every place tied to it in step: a unit's `ownership` (export_descr_unit),
  the `recruit` lines that let the faction train it (export_descr_buildings) and its
  cards (ui/units, ui/unit_info, copied from an owner's); a building level's
  `requires factions` list. When only this faction loses what its culture (or everyone)
  had, the list is written out as the other factions. The preview warns about armies
  and towns that already hold it, and about a unit no building level of the faction
  recruits. The Units & armies and Buildings tabs offer what the faction will have.
- **Add and remove lines** in the Unit and Building editors: **Add line...** puts a recruit
  line, a capability (bonus), an upgrade or another level line in its place in a
  building level (a capability / upgrades block is made when the level has none), or
  any key the mod's units use in a unit. Factions named on a new recruit line that do
  not own the unit get it and its cards. **x** removes a line - never one that every
  unit (building level) of the mod has.
- **Changes drag along what is tied to them**: a unit's new `type` reaches its recruit
  lines, the armies of every campaign, the mercenary pools and the rebels; a new
  `dictionary` copies its texts and cards; factions added to `ownership` get the cards;
  a building chain's new name reaches the towns of every campaign and the requirements
  naming it. A line naming a unit, a building chain or level the mod has not is refused;
  a `levels` line must name the chain's level blocks.
- A line is added only while its place has fewer lines of that key than the most any
  unit (building level) of the mod has - the tool keeps to what the mod already does.
- **Building names per culture and faction**: the Building editor shows a level's names
  (`{<level>_<culture>}` / `{<level>_<faction>}` - Shrine to Ares for the Greeks, to
  Taranis for the Gauls...); a level given to a faction whose culture has no picture
  for it is warned about.
- **Tied to it**: above the lines, who owns and recruits the unit (or may build each
  level), what requires the chain, and how many armies / towns hold it at the start.
- **The mod is remembered**: the last mod and each mod's campaign load at the next
  start; **Mod** at the top lists every mod of the game folder (the game, bi, alexander,
  HLR, the mods made with New mod folder, Medieval II's mods/...).
- **Scan mod tells files apart**: the game's own (unchanged), changed by the mod, REX's,
  or the mod's own - from the game manifests, which now come inside the exe (a manifest
  made on your PC with Game manifest... wins). Each unhandled mention shows which it is.

## 0.4.2 - 2026-09-28

- **New regions and painted borders reach everything tied to them**: the
  campaign-select maps of every faction whose land changed are drawn on the map as
  it will be (a new region lights up on its owner's map, a cut region shrinks on
  its owner's), also when only the map is written; a new region joins the
  mercenary pool of the region its land came from (descr_mercenaries.txt).
- A faction whose own select map shows no light gets one from its colours.

## 0.4.1 - 2026-09-28

Fixes from a run through every part of the tool as a user (vanilla and HLR).

- **Edit no longer renames the rebels**: it wrote the faction's name into every
  string keyed like it even when the name was not changed - also a rebel type of
  the same name ({Belgae} "Belgae Rebels" became "Belgae Confederacy").
- **Campaign-select maps**: the factions that lose or get towns are drawn again
  too, in the colour their own map has; the colour is read inside the land; a new
  faction starts with its template's map colour. Only real map_<faction>.tga files
  make the background (HLR's map_heights etc. gave a garbled picture; HLR has no
  campaign-select maps to draw from, and the tool says so).
- **Much faster on big mods**: a new faction on HLR 65 s -> 1.5 s; Check mod
  (deep) on vanilla 4 min -> 26 s, on HLR about 2 minutes.
- Neutral agent signs: priest an open book, inquisitor scales, heretic a torn book,
  witch a pointed hat.
- Undo / Redo in the unit and building editors no longer undo the faction tabs
  unseen; switching New / Edit faction asks before dropping unwritten changes.
- Without Pillow a new faction no longer fails on the campaign-select map.

## 0.4.0 - 2026-09-28

### New
- **Map legend** on the right of the Map tab: every sign and what it means; hide it
  or show it, the choice is kept between starts.
- **Art tab**: every picture of the faction (campaign-menu buttons with their
  mouse-over/selected/grey states, captain cards and portraits, leader picture,
  the campaign-select map, banner textures...) with what each needs and
  **Replace...** - a PNG/JPG/TGA made the size and depth of the game's own.
- **Campaign-select map drawn**: map_<faction>.tga lights the faction's start land
  in a colour you pick, on the campaign's own background with the ground's texture
  showing through (within a point or two of the vanilla maps). Drawn for a new
  faction and again when an edited one takes or gives towns.
- **Copy as new unit / building**: a new unit from one there is (its block, names
  and descriptions, cards, recruit lines) or a new building chain (levels renamed,
  texts, pictures).

### Fixed
- A new faction now also gets the template's mouse-over, selected and grey
  campaign buttons (file names with the faction name in the middle were missed).

## 0.3.0 - 2026-09-28

### New
- **Unit editor** and **Building editor** (first steps): every line of a unit's block
  in export_descr_unit.txt or a building chain in export_descr_buildings.txt as a
  field; **picture import** - a PNG/JPG/TGA converted to the mod's own size and
  format and put where the game reads it (unit cards and description pictures for
  every owning faction, building pictures per culture and level), requirements
  shown next to each picture. Preview / Apply with a backup like everything else.
- The work is picked at the top: **New faction**, **Edit faction**, **Unit editor**,
  **Building editor** (instead of the two switches top right).
- Map: the layers in one **Layers** menu; **Edit regions** switches the political
  colours and borders off and back; painted land shows in its new owner's colour.
- A template fills the new faction's empty fields (money, colours).

### Fixed
- A princess (witch) takes a woman's name from descr_names.
- A lower settlement level or a smaller governor's building pulls every other
  building down to what fits.
- Restore removes pictures a run created.

## 0.2.0 - 2026-09-28

The big patch: resources, Medieval II, tiles as the game has them.

### Map
- **Resources**: a Resources layer with a simple sign per type; click to pick,
  right drag to move, Place new, Delete picked; a region's resource tags
  (descr_regions.txt). Lines keep their layout (vanilla, HLR, REX quantities).
- **Tiles**: armies and agents are refused only by sea, mountains, dense forest
  and rivers/fords/cliffs - checked in the game; hills, woodland and steep tiles
  are fine now. The reason shows on hover and drag, and a character dropped or
  placed on a bad tile goes to the nearest good one.
- Trying to drag a character that cannot move here says why and what to do.
- Every agent kind has its own sign.
- An open Map or Diplomacy tab is drawn again after Apply, Restore or reload.

### Towns
- Buildings follow the settlement level both ways: a level picked by hand sets
  the governor's building and the population range, a bigger governor's building
  raises the level, and every chain offers the levels of the settlement as it
  will be (no more ticking 'show levels too big').

### Armies, agents & fleets
- A table (kind, name, units, tile) under a split you can drag; double click shows
  it on the map.

### Medieval II (early)
- Character lines with the sex, as Medieval II writes them (the tool wrote Rome's
  form before - the likely cause of a crash after taking rebel towns).
- Agents from the mod's descr_character.txt: merchant, priest, princess, inquisitor...
- Religions: read, shown on the map, edited per region (Regions mode), written
  for new regions.

### Logs
- Tools > Save logs (zip): the tool's log with the game's system.log.txt and the
  newest crash report (the player's nick taken out of its name).

## 0.1.2 - 2026-09-28

- Edit: taking every unit out of a town's garrison now leaves it empty (a family
  member keeps only his bodyguard, a captain leaves). Before, the town's own
  garrison came back; that is what **Automatic** is for.

## 0.1.1 - 2026-09-28

- Renamed to **RTW Campaign Editor** (the exe is RTW-Campaign-Editor.exe): it edits
  far more than factions now. Backups and the log keep their old names.
- New faction mode no longer keeps a leader/heir name from another faction's list.

## 0.1.0 - 2026-09-28

The first release: a campaign editor for Rome: Total War mods, built on
Barbarian Empires REX Ultimate Edition (HLR, under REX) and the plain game.

### New factions
- Cloned from a template: descr_sm_factions, descr_names, the unit and building
  ownership lists, models, banners, triggers, text strings (whole multi-line
  entries), campaign-screen texts, unit cards and art.
- Start towns (also rebel villages the campaign leaves out), capital, leader and
  heir, a balanced army or garrisons by hand, buildings by hand, diplomacy.
- A separate mod folder in one click (hard links, own start script and sound pack).

### Editing existing factions
- Names, tooltip and campaign-screen texts, colours, AI, denari, playable.
- Towns taken and given away, capital, leader and heir.
- Garrisons (shown as they stand), buildings, settlement level and population
  (a bigger governor's building grows the settlement).
- Armies, fleets and agents: new ones placed on the map, existing ones get new
  units, moved or removed.
- Diplomacy: core_attitudes both ways and faction_relationships.

### Campaign map
- Drawn from map_ground_types; political and diplomacy colours; towns, ports,
  characters; zoom up to 64 px per tile.
- Drag characters, towns and ports; fleets follow a moved port; the compiled map
  (map.rwm) is removed so the game rebuilds it.
- Regions: paint new regions and move borders; descr_regions, the name lookup,
  labels and map_regions are written together.

### Safety
- Preview of every file and line, backups with byte-exact Restore, Undo/Redo
  (Ctrl+Z / Ctrl+Y), map-only writes, Check mod (quick and deep), a log file,
  Help (F1).

### Tested in the game
New factions, the separate mod folder, garrisons and buildings, editing towns,
leaders and texts, moving characters, towns and ports (roads and sea routes
follow), new regions.

### Not yet tested in the game
Diplomacy changes, settlement level/population changes, changing or removing
existing armies, fleets and agents. They are checked against the game files the
way the tool checks everything, but have not been played yet.

### Known limits
- Banners and logos: a new faction shares its template's.
- Names come from the existing name lists.
- One campaign per run.
- Tested mods: vanilla and HLR. Check mod reports what the tool understands in
  any other mod.
