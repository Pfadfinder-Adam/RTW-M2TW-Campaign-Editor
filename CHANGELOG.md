# Changelog

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
