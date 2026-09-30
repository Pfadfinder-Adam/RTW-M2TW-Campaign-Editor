# Changelog

## Unreleased

### Added
- **Tools > New religion... / Religions of a region...** (Medieval II): the religion dialogs reached from the menu
  too - the Map opens with Edit regions on; on Rome the menu says Rome has no religions.
- **View in 3D for Rome**: Rome's `.cas` battle models (units, officers, mounts, animals - every one of the 807 vanilla
  files, versions 2.22 to 3.2) are drawn like Medieval II's: the man put together on his skeleton, weapons and shield
  in their places (on or off), each faction's texture, the game's detail levels. A model without a texture line
  (the women peasants) shows the texture its `.cas` names. Model files a mod folder does not have are taken from the
  game's own data folder (Medieval II too).
- **Campaign rules** (Tools > Campaign rules...), both games: every value of the campaign's settings files with a
  plain explanation, grouped as the files are, Find, the game's own value beside a changed one (Reset), Preview,
  written with a backup. Medieval II: descr_campaign_db.xml (ages, agents, revolts, crusades, bribery, ransom...),
  descr_settlement_mechanics.xml (each line of the town scrolls: growth, public order, income), descr_diplomacy.xml,
  descr_recruitment.xml; Rome under REX: descr_settlement_mechanics.xml (the people each settlement level needs);
  REX / M2EX: descr_unit_sizes.txt (the Unit size choices). Only the value's characters change - M2EX's own
  unquoted values (bool=false) included.
- **Add-ons** (a new button beside the editors): ready-made scripts put into the game with their settings picked in
  the tool, a backup on every write, Take it out. The first: **Sack Settlement** (Rome + REX) - a 4th choice on the
  capture scroll that tears the town down, pays a reward and leaves the ruins to the rebels. New: **who may sack** -
  only the player (default), everyone, only factions without a town (hordes), the player and hordes, only the
  computer, or picked factions; a computer faction allowed to sack does it whenever it exterminates. The chains
  that stay standing and the rebel units are picked from the mod's own buildings and units (Pick...), and names the
  mod does not have are refused - as is leaving out the governor's chain.

### Fixed
- **Medieval II clone: "the Kingdom of Kingdom of Jerusalem"** - the game has no short faction names, so the
  template's name inside the copied texts (advice, intro subtitles, "de Sicily" surnames) was swapped for the whole
  new name; now "Kingdom of Sicily" becomes the new full name and a bare "Sicily" the short name (or the end of
  "Kingdom of Jerusalem"). Found making a Kingdom of Jerusalem with Judaism from Sicily.
- **Map: the buttons above the map were cut off** at a normal window width (New religion..., Names by culture...
  lay past the right edge - a user could not find them): the Regions and Resources toolbars now wrap onto a second
  row.
- **Buildings / Units & armies: a town opened without picking a faction first** - they show what the town's owner
  may build and recruit (the status line says so) instead of "pick the template faction first".
- **3D view: the detail levels were out of order** when a model mixed `model_flexi` and `model_flexi_m` lines
  (Rome: "0 - closest" showed the farthest model); they now follow the file.
- Campaign rules: the settings files' tag pattern could take very long on a crafted line (GitHub code scanning,
  py/redos); it now reads any line in linear time, with the same result on the games' files.
- **3D view: "Weapons and shield" off hid the legs too** on some models (vanilla peasants list their legs after the
  first weapons part): weapons and shields are now told by their names.

### Changed
- README, wiki, SECURITY: download the editor only from this repository's Releases page (or a link the author
  posted) - never a copy passed around elsewhere.
- **Unit editor: the battle model and the voice sit beside the two pictures** (they were below them, leaving half
  the panel empty - a user's screenshot); the unit's lines start higher. Fits a 1280-pixel-wide window.

## 0.19.2 - 2026-09-30

### Changed
- **Factions are listed with the name players see** when the mod shows another one: "turks - Ryazan" (Medieval II's
  faction names are fixed in the game, so mods keep "turks" and rename it in the texts - a tester on Discord). In
  every list where a faction is picked: the faction to copy or change, New region's owner and builder, where
  removed towns go, the towns' owner filter, rebels of, the Character editor, name lists, the editors' Show filter
  and New religion. The files keep the internal name.

### Fixed
- **Buildings whose list says `factions { all, }`** (a modder's way to let everyone build them) were taken as
  buildable by no one: the Buildings tab offered only the other levels, and setting them warned "not in the faction
  list" (a tester's report). 'all' in a factions list now means every faction, everywhere the tool checks it.

### Added
- **Hear a unit and give it a voice** (Unit editor, Voice in battle), both games: for each accent (Medieval II) or
  culture (Rome) of the unit's owners - its voice class, Play its own name call ("Khan's Guard!") and each of its
  orders, straight from the game's sound packs; Put in my own... makes your .wav files its name call (a unit that
  shares a line with others gets its own; a new unit gets one), shown before writing, with a backup. The game
  builds its sound list (events.dat) again on the next start.

## 0.19.1 - 2026-09-30

### Changed
- **Help (F1) rewritten for newcomers**: an "I want to..." list at the top says which button does what; every
  tab, editor and tool in plain words, the new ones of 0.19.0 included.

## 0.19.0 - 2026-09-30

### Fixed
- **A faction picked in New faction mode** (to change it, not to copy it) no longer ends in a puzzling "nothing to
  write" (a tester on Discord): the line at the top and the message on Apply now say that it is the template of
  a new faction, and to press Edit faction to change it itself.
- **Big campaign maps open ten times lighter**: a map of 4080 x 2496 tiles took 38 s and 6.6 GB of memory to open
  in the tool; now 2 s and 0.6 GB. The map is drawn in about a second instead of 19.
- **The Map tab no longer fails on a very big map zoomed far out** (Pillow refused a 1.3-billion-pixel picture): only
  the part of the map in view is drawn.
- **Painting regions on a big map**: the check before writing took 11 s and 800 MB on a 4080 x 2496 map; now a
  fraction of a second. A tile off the map is refused in plain words (it stopped the check).
- **A new faction on Medieval II now has battle banners, a voice, one-liners, movies and campaign music**: it is
  named beside its template in descr_banners_new.xml (with its own copy of the banner texture when that is on disk),
  descr_sounds_accents.txt, descr_sounds_db.xml, descr_movies_tracks.xml, the campaign's descr_faction_movies.xml
  and descr_sounds_music_types.txt - vanilla names every faction in them, and they were left out.
- **The ring round a town**: the 8 tiles round a town must be its own region or sea (vanilla Rome and Medieval II
  never break it), and on Medieval II no port may stand next to a town. Moving a town or port, painting regions
  and placing a new region's town or port are refused on Medieval II and warned about on Rome; Check mod lists
  what a map already breaks.

### Added
- **New unit / New building step by step** (Unit and Building editors; was Copy as new): a new one starts as a
  copy of one that works in the game, then steps you can go back and forth between - names and the texts
  players read, who owns the unit or may build the chain (factions or cultures), the unit's main numbers
  (men, attack, armour, cost...), pictures of your own - and last every file it will change before it is
  added. On Medieval II a renamed level gets its new name in every culture's own text too.
- Unit editor: **View in 3D...** - a Medieval II battle model (.mesh) drawn in 3D with its texture: turn it with
  the mouse, zoom with the wheel, pick the faction's texture, the level of detail and 'Another man' (the game's
  mix of heads, arms, bodies); also in the Replace model window. Reads all 3354 vanilla meshes. Rome's .cas
  models are not shown yet.
- **Check and install a pack** (Tools): a "copy data over the game" mod checked file by file before it goes in -
  new, the same, or what a replacement would lose: a file of REX's own, a picture of another size (for an interface
  icon page, the icons left outside it), another mod's whole text file. A text file that differs in a few lines can
  go in as "only its changes" (the pack's changed and added lines; lines it would drop stay). Pick per file, Preview,
  Install with a backup; Restore takes it all back. Found on a Julii unit-card pack that also brought the original
  game's battlepage_03.tga over REX's (the schiltrom / shield-wall buttons lost their pictures), an older
  descr_projectile_new.txt and a whole export_descr_unit.txt.
- **Replace a unit's battle model** (Unit editor, new **Battle model** block): the soldiers' (and each officer's)
  model with a texture of one of the unit's factions, how the model sits (on foot, on a horse or camel, an
  elephant, a chariot) against the unit's mount, and **Replace model...**: pick another model of this mod or of
  another mod folder of the same game (it comes with its meshes, textures and sprites; a taken name gets a free
  one). Every faction that owns the unit gets a texture on the new model where it has none - in
  descr_model_battle.txt and, on Medieval II, in battle_models.modeldb alike. A model made to sit otherwise is
  marked in the list and warned about (Medieval II likely crashes on it). Preview, a backup, Restore as always.
- **An icon of its own** for the exe and the window: a gear ring round a Roman "R" and a medieval "M" (drawn for the editor, no game pictures).

### Fixed
- Settlement names by culture under M2EX: checked in the game, so Preview no longer warns that it is untested there.
- **Medieval II with M2EX: a new mod folder starts the way M2EX's own mods do** - `Start_<name>.bat` runs
  `M2EX.exe --features.mod=mods/<name>` (as M2EX's Teutonic.bat / Crusades.bat), the plain game keeps
  `medieval2.exe @mods\<name>\<name>.cfg`.

## 0.18.1 - 2026-09-30

### Fixed
- **Barbarian Invasion: regions read and written right.** BI's descr_regions.txt has a `legion: ...` line after
  each region's name and a beliefs line (`pagan 90 christianity 10`) after farming. The tool took the legion
  line for the town, so a BI region showed the town as "legion: ...", the builder as the town and so on. Now
  both lines are read, kept when a region is edited, and a new region gets them from the region most of its land
  came from (checked on BI's own campaign: all 72 regions; a new region written and restored byte for byte).

## 0.18.0 - 2026-09-30

- **License**: GNU GPL v3.0 from this version on (up to 0.17.1: MIT). The editor stays free and open; programs
  built from its code must stay open under GPL-3.0 and keep the author's copyright notice.

### Fixed (from the user's tests)
- **Medieval II: a new army, agent or fleet of the rebels never showed up in the game.** In Medieval II the rebels
  are the last faction in descr_strat, and their block ends where the diplomacy starts with `faction_standings`
  (Rome starts it with `core_attitudes`). The tool knew only Rome's word, so it wrote the rebel army after the
  diplomacy lines, where the game does not read it. Now it goes into the rebels' block.
- **Smaller windows keep their buttons.** + Army / Place on map / Remove on Units & armies, Automatic / Suggest,
  the map's zoom buttons, the Unit editor's pack buttons, the Terrain editor's undo buttons and the Campaign box no
  longer drop out of a narrow or low window - a long hint is cut instead. The Faction tab's form and the Character
  editor's person form scroll when the window is lower than they are (Leader and heir, portraits, traits stay
  reachable). The smallest window is now 1024 x 640.
- **Drag the line** between the left side and the rest on the Faction, Units & armies and Buildings tabs: a wider
  towns list, or more room for the roster cards.

### Fixed (from the modders' guides, checked on the vanilla files)
- **REX / M2EX: the original game's limits no longer hold a modder back.** With REX or M2EX beside the game the
  religions limit (9) is not applied (New religion... says "no limit"), and Check mod counts regions, map size,
  units and religions as lifted for both engines (their own notes: "no faction, religion, region, unit, cultures,
  model limits"). The faction count still follows the engine's max_factions, which the tool offers to raise. On
  the original exes the limits stay as before.
- **Unit and Building editors: no cap of our own on lines.** A key the mod repeats (officers, bonuses, recruit
  lines, upgrades) takes as many lines as you like - no more "not more than the mod already has". A one-line key
  (category, class, recruit_priority_offset...) stays one line, and a key the mod never uses there is refused (most
  likely a typo). Officers stop at 3 only on the original exes (their own limit); with REX / M2EX there is no cap.
- **A son off the map may be as old as the mod's own age of manhood** (REX `age_of_manhood` in descr_ex.txt,
  Medieval II `<age_of_manhood>` in descr_campaign_db.xml), not a fixed 16; 16 when the mod does not set it.
- **Family tab**: a son or other living man written off the map (a record) older than 16 is refused -
  the game crashes on one; new sons now start at 16 or younger. One already in the file is only warned about.
- **Flag symbols (Rome)**: the banner sheets are read from descr_standards.txt (Barbarian Invasion uses
  symbols9-15, not symbols1-8). A new faction no longer puts its symbol on a rebels' sheet: it takes a free
  faction slot, or a new faction sheet is added (slave's flag keeps its picture).
- **Terrain editor**: Preview warns about a 2 x 2 block of river and a river closing into a ring.
- **Names by culture on Medieval II** need **M2EX** (not REX): the check, the window texts and Preview name the
  right engine; under M2EX the names are written the way REX documents it (to test in the game once).

### Added
- **Terrain editor: Heights** (`map_heights.tga`), a spray brush: hold the left button and the land under the
  brush rises (Raise) or sinks (Lower) the more the longer you hold; the middle does the most, the edge fades.
  **Smooth** evens out bumps, **Level to height** brings the land towards a height (right click picks a
  tile's own). Strength slider, brush up to 12 tiles. The map shows the heights as the file has them - land
  grey (black low, white high, brightened a little), the sea blue; only land is changed, the coast stays.
  Apply writes map_heights.tga, changes the same points in **map_heights.hgt** (the game's own copy of the
  heights, read instead of the picture while it is there; Medieval II needs it to load) and deletes map.rwm. Land
  never goes down to pure black (the game may take it for sea). Same file
  layout on Rome and Medieval II (checked on both vanilla maps). Tested in the game on both (video: https://youtu.be/mTdRAWympuw).
- **Find on the map** (Map tab and Terrain editor): type part of a name - a town (also the name shown for
  its owner), a port, a general, agent or fleet, a unit in an army, a fort, a resource - and pick a hit: the
  map zooms in close on it and a ring blinks round it. Names come first (typing "rom" lists Rome before the Romans' armies).
- **Check mod**: the factions against max_factions, and the original exe's limits (regions, map size, units, building chains, levels, hidden
  resources) counted against the mod, saying whether REX / M2EX is beside the game and what it is known to
  lift (REX: regions - HLR runs 750); win conditions naming a missing region or faction; Medieval II rebels
  with units the slave faction may not own; Rome regions lacking the 'slaves' the mod's other regions have.
- **A new religion for Medieval II** (Map tab, Regions: **New religion...**), e.g. Judaism: its name in
  descr_religions.txt (list + its own block), descr_religions_lookup.txt, text/religions.txt, its symbol
  (ui/pips/pip_<name>.tga - your picture as a 24-bit TGA sized like the religion copied, or a copy of its
  symbol), every region's religions line in every descr_regions.txt at 0 %, map.rwm removed; optionally the
  factions that follow it. Its shares per region are set with **Religions...** in the same Apply. Refused: a
  name taken, no shown name (the game crashes silently without its text), more than 9 religions (the engine's
  limit). Preview says how many lines of buildings, traits, ancillaries, faction standing and the AI still name
  only the religion copied. Checked on vanilla Medieval II (Judaism, 30 % in Cordoba, Restore byte-exact) and in
  the window; not yet in the game.

## 0.17.1 - 2026-09-29

Asked on Discord: where are the rebels?

### Added
- **The rebels (`slave`) in Edit faction**: their armies, fleets, agents, garrisons, towns, buildings and units
  (Roster) are edited like any faction's. Every rebel character in the game files carries `sub_faction <faction>`
  and takes its name from that faction's list (all 91 vanilla rebels, Rome and Medieval II); the tool writes the
  same: a captain for an empty rebel town takes the sub_faction of the nearest rebel (else the region's creator),
  and **+ Army / + Fleet / + Agent** ask whose rebels they are (**Rebels of**) and offer that faction's names.
  The rebels are never made playable and have no capital, leader or heir (greyed out). Checked on vanilla Rome
  and Medieval II (rebels take a town, a captain and a new army written, Restore byte-exact) and in the window.

### Fixed
- **A new faction no longer takes its template's shadow / spawn ties** (BI / Medieval II `descr_sm_factions`):
  a clone of `empire_east` was also `shadowed_by empire_east_rebels`, so two factions claimed one civil-war
  shadow; `spawns_on_revolt`, `spawned_by` and `spawned_on_event` were copied the same way. The clone starts as a
  plain faction and Preview says which tie stayed with the template.

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
