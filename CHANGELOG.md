# Changelog

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
