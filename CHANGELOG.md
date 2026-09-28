# Changelog

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
