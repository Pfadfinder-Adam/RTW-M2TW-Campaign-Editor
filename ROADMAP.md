# Roadmap

Where RTW & M2TW Campaign Editor stands, what comes next and what each step needs.
📦 built and released (delivered) · ✅ built, released and confirmed in the game · 🧪 released, being tested in the game now ·
🔜 next · 💡 later. Updated with every release
(see [CHANGELOG.md](CHANGELOG.md) for the details).

Found a bug or a crash? Press **Report a bug / Suggest** - the logs (your names cut out) and a screenshot reach the
author in one click ([video](https://youtu.be/7MbYR9ywNsI)). That is the fastest way to a fix.

## 🗺️ Rescale the whole campaign map 3 x

**Bigger map (x3)...** (top row) (beta), Rome (REX) and Medieval II (M2EX). Each tile of
`map_regions.tga` becomes a 3 x 3 block; everything tied to the map is converted with it:

- **Positions** (`descr_strat.txt`, `descr_events.txt`, ...): towns, characters, fleets, resources, forts,
  watchtowers, wonders and event places go to the middle of their new block.
- **Coast and borders**: natural - the coastline winds with bays and capes and the borders between regions wind
  too, instead of 3 x 3 squares and straight 45-degree cuts (the old map's own relief bends
  them - a cape where a ridge comes down to the sea, a bay where a valley does, a river on the lower side of its
  valley - with a fractal coast's small detail, rougher where the land is steep; the same map always comes out
  alike); every block's middle keeps its old
  value, so nothing changes under a town, army or resource, and every region stays in as many pieces as before. Ports stay on the shore pixel of their own region.
- **Heights**: `map_heights` the natural way - bent with the ground, crags on the mountains, rivers in their
  valleys, no slope steeper than the old map's steepest - along the new coast, and
  **`map_heights.hgt`** - the game's float copy, which it reads instead of the picture and never rebuilds - written
  at the new size too. The hills, mountains and sea floor are made **3 x higher** (`max_land_height`,
  `min_sea_height` in `descr_terrain.txt`): the land is 3 x wider, so the slopes stay as steep as they were
  (or keep the old heights - a choice in the window). The sea ground types follow the heights' new coast.
- **Rivers**: 1 pixel wide (the game crashes on a 2-pixel river), drawn the way rivers run - bends rounded, gentle
  meanders on straight runs; a river mouth runs on to the new coast and stops there (none on the sea).
- **No beach and no cliffs** are written on the bigger map (both looked wrong in the game) - paint them with the
  Terrain editor where wanted.
- **Ground and climates by tile**: every new tile the ground type and climate of the old tile it lies in, the edges
  between kinds winding, no 3 x 3 steps.
- **Pictures**: `map_trade_routes`, fog, roughness, disasters and radar maps scaled with exact colours.
- `descr_terrain.txt` gets the new size; `map.rwm` is deleted so the game rebuilds it.
- Preview of every file, one backup, Restore byte-exact.

Scripts follow too: every campaign-map place in the campaign's scripts (spawned armies and characters, `reposition_character`, `move`, the camera, `reveal_tile`, forts and resources made by `console_command`, 'near a tile' and 'in a rectangle' conditions) goes to its block; battle positions in the same scripts stay. Lua / Squirrel scripts that place things by tile move too; lines the editor cannot read for sure are listed to check by hand.
Without REX / M2EX the original exes stop at
510 tiles - the tool warns. Checked on both vanilla campaigns (103 / 112 towns, 177 / 216 characters, 75 / 77 ports
in place, no river on the sea, every river end at the sea, a river or the map's edge as in the original). The first
alpha (0.24-0.27) left the old `map_heights.hgt` in place and kept the heights - flat, square-coasted maps; make the
map again from a backup with this version. Video of the first alpha: [rescaling the whole map](https://youtu.be/kkfI-WulRmU).

## Where it started

Version 0.1: a small script for one mod (Barbarian Empires REX on Rome: Total War) that cloned a faction
from a template - texts, units, buildings, start towns, leader. Rome only, command line first.

## The road so far

The first nine days (0.1.0 → 0.30.0): from a one-mod faction cloner to a campaign editor for two games.

**Day 1 - Rome and REX**

| Version | What came |
|---|---|
| 0.1 | New faction from a template · Separate mod folder |
| 0.2 | Resources on the map · Tile rules for armies |
| 0.3 | Unit and building editors |
| 0.4 | Faction art · Map legend · Campaign-select map |
| 0.5 | Roster · Renames followed everywhere |
| 0.6 | Map by tiles · Medieval II unpacked by the tool · Dark theme |
| 0.7 | Unit packs (export / import) |

**Day 2 - characters, terrain, Medieval II**

| Version | What came |
|---|---|
| 0.8 - 0.9 | Family tree · Character editor · Portraits |
| 0.10 | Terrain editor |
| 0.11 | Faction limit known (REX / M2EX) |
| 0.12 | Flags and logos · Climates · Restore to any backup |
| 0.13 - 0.14 | Town names by culture · Own name lists |
| 0.15 | Medieval II city / castle |
| 0.16 | battle_models.modeldb |
| 0.17 | recruit_pool · REX brackets · Forts · Rebels editable |

**Day 3 - community knowledge, models, packs**

| Version | What came |
|---|---|
| 0.18 | New religion (Medieval II) · Heights brush · Find on the map · GPL-3.0 |
| 0.19 | Replace a battle model · 3D view of unit models · Unit voices · Pack check before install · Big maps 10x lighter |
| 0.20 | Report a bug in one click · Settlements tab · 3D view of Rome models too · Campaign rules · Add-ons |
| 0.21 | Volcanoes and land bridges · Forts and watchtowers on the map · Main window reorganised |

**Day 4 - a living campaign map, both games**

| Version | What came |
|---|---|
| 0.22 | Character panel as in the game · Traits and retinue · Events and later factions · Religion map |
| 0.23 | Alliances and wars at the start · Victory conditions · Diplomacy in plain words |
| 0.24 | Campaign map 3x bigger (alpha) · Settings window |
| 0.25 | Smooth relief on the bigger map · Wonders on the map |
| 0.26 | Right-click menu on the map · Search in Units and armies · Building chains kept whole |
| 0.27 | Units and buildings brought from another mod, step by step |
| 0.28 | The bigger map smooth - coast, relief 3x higher, its heights file · Land and sea brush - a new island |
| 0.29 | Recolour every faction picture · Faction emblem from one picture · Buildings and garrisons for many towns · Natural edges on the bigger map · Raze Settlement for Medieval II (0.29.1) · Fixes from reports - bigger map rules, all-or-nothing writes, new factions' buttons, the editor into the game folder (0.29.2) |

**Days 5 - 9 - the Map editor, step by step**

| Version | What came |
|---|---|
| 0.30 | Map editor - select, give, delete, a town window · Bigger map step by step (beta) · Map size + / - · Mercenaries · Module builder and Avoid Growth · Start the game · Check mod files by when it breaks · Undo this write · Credits · One write for the session, fixes for packed Medieval II games (0.30.1) |

**Day 10 - one language, fixes from the testers**

| Version | What came |
|---|---|
| 0.31 | Every window one write · Mods holding only their changes · Rename a faction · Cards on hover, tables sorted · Enter / Esc and answers in words · Fixes from the in-game test runs |
| 0.32 | Module builder like Scratch - blocks dragged into each other · ELSE, any / none / not, FOR EACH town, army, faction |

**Day 11 - from nothing, the map's shape by hand**

| Version | What came |
|---|---|
| 0.33 | Units, buildings and religions from nothing · Your own files for a battle model · Map size by dragging its edges · Merge regions · Many towns deleted at once · A town's own garrison · Recolour never over the original · Cards and pictures as the game shows them |

**Days 12 - 13 - the models move, the map's free land**

| Version | What came |
|---|---|
| 0.34 | Animations in View in 3D - riders on their horses, siege engines · Cards made from the 3D view · Wastelands - a deleted town's region, one common wasteland · Pull and Push the coast · Thin mods · Faster on big mods · Every picture big on a click |

**Days 14 - 22 - a faction brought whole, the map in 3D**

| Version | What came |
|---|---|
| 0.35 | A whole faction brought from another mod · The campaign map in 3D, everything on it carried with the mouse · One emblem for every flag and banner · Locked factions opened · Your own pictures in the menus · Every script's places on the map |
| 0.35.1 | Fixes from the testers' reports · The crash doctor: why the game stopped, in one line |
| 0.35.2 | Fixes from the testers' and players' reports · Thin mods stay thin · Check mod files: the quick-battle crash |

| Area | Confirmed in game | Released | Being tested | Next |
|---|---|---|---|---|
| Factions | new faction, faction limit, edit, garrisons, mod folder | settlement size, rebels, diplomacy, roster | alliances and wars at the start, victory conditions, building chains kept whole | the new factions' AI |
| Campaign map | tiles, moving towns, new regions, terrain, heights, find, town names, map 3x bigger (beta) | resources, climates, forts, big maps | wastelands, pull and push the coast, the bigger map smooth (coast, heights, natural edges), many towns at once, land and sea brush, wonders, events, right-click menu, drop into a town, map size by dragging its edges, merge regions, many towns deleted at once | flat plains and sharp peaks, borders drawn by the tool, a map from the real world |
| Characters | - | name lists | character panel, traits and retinue, family tree, portraits | - |
| Units, buildings, art | faction art | editors, unit packs, modeldb, REX abilities | recolour of every faction picture, faction emblem, battle banners from a white banner (both games), units and buildings brought from another mod, replace a model, your own model files, 3D view of Rome and Medieval II models with their animations, riders and siege engines, cards from the 3D view, new unit / building step by step or from nothing, unit voices | M2EX monster units |
| Both games | Rome / BI / Alexander, city ↔ castle | Medieval II and Kingdoms | religions, campaign rules, add-ons, module builder | vassals (`client_of`), window in other languages |
| Safety | - | preview, backup, byte-exact restore, Check mod files, report a bug in one click, settings | pack check | signed exe |

## What it does now (0.35.2)

### Factions
- ✅ New faction from a template: names, texts, colours, units, buildings, cards, name lists, traits, art *(in-game ✓)*
- ✅ Faction limit known and raised (REX / M2EX `max_factions`) *(in-game ✓ on Rome + REX)*
- ✅ Edit an existing faction: names, texts, colours, AI, money, playable, towns taken or given, capital, leader and heir *(in-game ✓)*
- ✅ Garrisons and buildings per town, with the game's own cards and pictures *(in-game ✓)*
- 🧪 The campaign-select map and the leader's face on the faction tab, beside the description (Replace... there) (0.35.0)
- 🧪 Add-on: Upkeep x 2 - every unit's upkeep multiplied, put in and taken out (any mod, both games) (0.35.0)
- 🧪 A faction with no town at the start (REX / M2EX: can_homeless); fewer made-up limits (recruitment slots, 99 levels, climate on sea, spin box caps) (0.35.0)
- ✅ Settlement level and population (the governor's building follows the size) (0.35.0) *(in-game ✓ from a report)*
- 🧪 The rebels edited like any faction: armies, fleets, garrisons, towns, units (each rebel with its `sub_faction`) (0.35.0)
- 🧪 Diplomacy: attitudes and starting relations with every other faction (0.35.0)
- ✅ Roster: give or take units and building levels (ownership, recruit lines and cards kept in step) *(in-game ✓ Rome + REX: a barbarian archer given to the Julii is recruited in their town)*
- ✅ A separate mod folder in one click (the base mod stays untouched) *(in-game ✓)*

### Campaign map
- ✅ The map drawn tile by tile from the game's own map files; political, diplomacy and region colours *(in-game ✓)*
- ✅ Characters on the map: drag to move, new armies, agents and fleets placed by clicking
- ✅ Move towns and ports (roads and sea routes follow) *(in-game ✓)*
- ✅ Paint new regions and move borders *(in-game ✓ on HLR)*
- 🧪 Edit a region's data (builder, rebels, tags, triumph, farming), new or existing (0.35.0)
- ✅ Map changes, new regions and faction changes written together by one Apply
- ✅ Resources placed, moved and removed; religions per region (Medieval II)
- ✅ Terrain editor: paint ground types, rivers, fords, river sources and cliffs tile by tile *(in-game ✓ on Rome and Medieval II; [video](https://youtu.be/z0T723riXaU))*
- ✅ Terrain editor: heights brush like a spray can - raise, lower, smooth, level (`map_heights.hgt` kept in step) *(in-game ✓ on Rome and Medieval II; [video](https://youtu.be/mTdRAWympuw))*
- ✅ Find on the map: towns, ports, armies, agents, fleets, units, forts, resources *(in-game ✓ on Rome and Medieval II; [video](https://youtu.be/6WAdnGovGzA))*
- 🧪 Terrain editor: paint climates (`map_climates.tga`, the mod's own climates) (0.35.0)
- 🧪 Rivers kept joined side to side (the game stops a river at a corner-only step); Preview names a river the game will not draw (0.35.0)
- ✅ Settlement names by the owner's culture (REX / M2EX rename a town when it changes hands); the map shows the new owner's name at once; every town's names in one table *(in-game ✓ on Medieval II with M2EX; [video](https://youtu.be/umwRyWkHoDE))*
- 🧪 Big maps load (a tester's map of 5456 x 2464 tiles) (0.35.0)
- 🧪 Forts and watchtowers shown on the map; no one is placed on them (0.35.0)
- ✅ Make the campaign map 3 x bigger (beta): everything on the map moved with it, rivers 1 pixel, the relief smooth *(in-game ✓ alpha; [video](https://youtu.be/kkfI-WulRmU); Rome with REX, the newest rules: in-game ✓ from a report)*

### Characters
- ✅ Character editor for any faction: names, ages, traits with levels, ancillaries (0.35.0) *(in-game ✓ from a report)*
- 🧪 A faction's own name list (men, surnames, women) typed in three steps (0.35.0)
- 🧪 Family tree drawn like the game's (couples, children, leader and heir); give a wife, add a child, rename (followed on the tree) (0.35.0)
- 🧪 Portraits on the tree as the game shows them; Medieval II characters get portraits of their own (0.35.0)
- 🧪 Portrait library: every portrait of a culture, add new ones (sized and numbered for the game) (0.35.0)

### Units, buildings, art
- 🧪 Unit and building editors: every line as a field, add / remove lines, copy as new, renames followed everywhere (0.35.0)
- 🧪 Pictures imported into the right place in the right size and format (cards, building pictures, faction art) (0.35.0)
- 🧪 Medieval II recruitment (`recruit_pool`) and REX's retrain-only lines read and written everywhere (0.35.0)
- 🧪 REX's bracket requirements: several faction groups on one line, each with its own conditions (0.35.0)
- 🧪 Unit editor: REX's unit abilities ticked with their effect in plain words (morale, fatigue, charge, terrain, garrison, shield piercing...) (0.35.0)
- 🧪 Unit packs: export units with models, textures, mounts, cards and texts into a .zip and import them into another mod (0.35.0)
- 🧪 Medieval II `battle_models.modeldb`: a new faction gets its template's textures in every battle model; unit packs carry their modeldb models (renamed on clashes, textured for every new owner) (0.35.0)
- ✅ Faction art: every picture of a faction listed with where the game shows it, Replace... *(in-game ✓)*; a new faction's banners and logo are its own files; Back to the original
- ✅ Rome: the flag symbol on the campaign map and the faction logos, each faction its own, Replace... in the Art tab (0.35.0) *(in-game ✓ from a report)*

### Both games
- ✅ Rome: Total War, Barbarian Invasion, Alexander - plain or on REX *(in-game ✓)*
- 🧪 Medieval II and Kingdoms - plain or on M2EX: unpacking offered, set-up fixes, castles, `mods/<name>` with its .cfg (0.35.0)
- ✅ Medieval II: turn a settlement into a castle or a city (buildings converted the game's own way) *(in-game ✓ loads)*

### Safety
- 🧪 Preview of every file and line before writing; only the lines meant change, the rest stays byte for byte (0.35.0)
- 🧪 A backup of every write; Restore gives the original back byte for byte (any write and every later one in one go); Undo / Redo in the window (0.35.0)
- 🧪 Check mod files (consistency report; with a faction picked, every place it is named - game, REX and mod files told apart) (0.35.0)
- 🧪 Log, Save logs (zip) for bug reports; Light / Dark look; smaller windows keep every button, side panels can be dragged wider (0.35.0)

## 📦 Built, comes with the next release

- 📦 Buildings by faction: a faction's chains as pictures, a chain's levels side by side, the units each level recruits as cards, the unit on the right (both games)
- 🧪 New / Edit faction: Culture - one line written, the game follows (towns, portraits, buildings, units); what changes said first (0.35.0)
- 🧪 Faction emblem (Rome): town flags in battle, the 3D campaign-map symbol, captains' cards and portraits from white templates; routing / rebel flags untouched (0.35.0)
- 🧪 Faction emblem (Medieval II): the battle banner sheet from the white template of the mod's sheets, the symbol on every banner shape (0.35.0)
- 🧪 The minimap drawn from the map (textures, relief, rivers, a painted sea); the faction-select map from the same picture, land at 75 % with a smooth outline; 3D map textures blended (0.35.0)
- 🧪 An army's units: its general shown as his portrait card, as in the game (0.35.0)
- 🧪 New faction > From another mod: a whole faction of another mod brought - units, names, family by the capital, figures on the map and in battle, flags, icons, pictures; garrisons of its own units (0.35.0)
- ✅ Maps > 3D: the campaign map in 3D in the game's own ground textures and models (towns, ports, forts, resources, armies, agents), the brushes' work seen at once (0.35.0) *(✓ in the window, from the tester)*
- 🧪 Maps > 3D on the graphics card: drawn the way the games draw it - the game's ground blend, light and sea sheet, the beach and surf along the coast, the game's mountains, hills, volcanoes, rivers, cliffs and trees, the towns, ports, resources and armies as the game's models, roads and region borders, armies and agents carried to another tile with the mouse (next: painting in 3D) (0.35.0)
- 🧪 Bring units: everything the target lacks - the voices of its class, its fire arrows and their effects, its skeletons' lines (0.35.0)
- ✅ Interface... (both games): the game's menu screens drawn as the game lays them out - pieces moved, sized, copied, renamed, removed; their words, tooltips and the page they open (the menu layout file written byte-exact) *(in-game ✓ on Rome + REX: a piece moved, its picture and click area moved with it)*
- 🧪 Interface: buttons' states (both games) - mouse over shown under the mouse, all pressed / ticked on a switch, each state's picture set, added, taken out (0.35.0)
- 🧪 Interface: own pictures (both games) - Replace picture... with a file or the Picture library (the game's pieces + your own), what the piece does kept; Back to the game's picture; checks for a missing region and a page too big for the game's sheet (next: the menus drawn by the graphics card) (0.35.0)
- 🧪 Check mod files (both games): a texture named inside a campaign-map model (.cas) that is not there - the game stops as the campaign loads (0.35.0)
- 🧪 Check mod files (Medieval II): battle_models.modeldb names whose count is not their length, two models of one name (0.35.0)
- 🧪 Check mod files (both games): files named in the banners / standards / projectile files not there or on a drive letter; events without their words (0.35.0)
- 🧪 Check mod files (both games): rivers the game leaves out (joined by a corner only), 2 x 2 river blocks and loops as notes (0.35.0)
- 🧪 Interface > Sprite sheets (both games): every sprite of the sheets the game reads (binary or .sd.xml), page and culture, Find, saved as PNG (0.35.0)
- 🧪 Rebels... (both games): rebel types - their units, kind, chance, the name players read - new, copied, renamed, deleted; which regions have which type, many at once, a faction filter (from a report) (0.35.0)
- 🧪 The map shows what Apply will write before it (regions yellow as a selection): a new faction's towns, garrisons, towns given in other windows; every capital a star in its square (from reports) (0.35.0)
- 🧪 Unit cards and description pictures for each faction on its own; New unit step by step: the pictures shown, View in 3D with Make a card; Recolour while a new faction is being made (from reports) (0.35.0)
- 🧪 Draw from the map: the faction-select map from the campaign map - relief, rivers, the faction's land one solid patch (0.35.0)
- 🧪 Bring units (both games): its name call in battle with its sounds; the unit's own skeletons and animations come along into your mod's animation set (0.35.0)
- 🧪 Add-on Recruitment Order (both games): the recruitment panel in order - infantry, missiles, cavalry, missile cavalry, chariots, elephants, war dogs and pigs, siege, ships, the dearest first (0.35.0)
- 🧪 Bigger map (x3): the minimap keeps its size; maps saved as colour-mapped TGAs open; Map > Layers: towns on / off, rebel land coloured (0.35.0)
- 🧪 Bigger map (x3): no sea ground on the land (light blue teeth along the coast, ports seeming in the water), every river reaching the sea by one pixel (from reports) (0.35.0)
- 🧪 Terrain editor: land and sea painted tile by tile with the ground brush; rivers always shown while painting them; Layers close on a second press; Report a bug packs its logs without freezing (from reports) (0.35.0)
- ✅ Bring units from another mod: a Faction pick; a file of the same name with other content brought under its own name (chariots no longer the Britons'; a chariot's body wears its own mod's look for each new owner; a model whose skeleton the mod lacks takes the mod's nearest, no crash at start); buildings show another culture's picture when theirs has none (from reports) (0.35.0) *(in-game ✓ from a report and the tester)*
- 🧪 Bigger map (x3): lines and rivers bent by the old map's own relief (capes on ridges, bays in valleys, rivers on the lower side), no golden-ratio waves (from a report) (0.35.0)
- 🧪 Bring units from another mod: a building this mod lacks comes along with its unit; New unit: your own texture / model file in the window itself (from reports) (0.35.0)
- 🧪 Bring buildings from another mod (Rome / BI / REX): the building keeps its look in towns on the battle map - town-plan places, battle building, items and models come along (from a report) (0.35.0)
- 🧪 Bring units from another mod: the list sorts (name, kind, owner, cost), the unit under the mouse shows without ticking it, the first step in a window as small as it needs (from reports) (0.35.0)
- 🧪 View in 3D: Medieval II's armour upgrades picked in the window; a shield worn two ways drawn once (on the back with the first weapon) (0.35.0)
- 🧪 Scripts on the map: a layer with a scroll on every tile the campaign's scripts and the Lua / Squirrel scripts name - dragged to move the place, double clicked to edit the lines round it; Undo, Preview and Apply as the Map's other changes (0.35.0)
- ✅ Special places: any campaign-map model on any tile with its own window on the game's scroll (picture, name, bonus, text, holder) and money a turn, its diamond dragged to move it - REX / M2EX
- 🧪 Leader's and heir's titles on the faction tab (New and Edit, both games) (0.35.0)
- 🧪 Make a card: beside the 3D view and following it; its framing kept for the next unit (0.35.0)
- 🧪 View in 3D: Medieval II's siege engines play standing, moving, loading and shooting with their crew at their places, each man in his own moves (0.35.0)
- 🧪 The 2D map quicker: moving, zooming and the heights brush (0.35.0)
- 🧪 Interface drawn by the graphics card; dragging a piece no longer lags (0.35.0)
- 🧪 View in 3D: Rome's siege engines with their crew at the engine's own places; elephants (both games) with their whole crew on them (0.35.0)
- 🧪 Unit editor: the card, the description picture, the battle model and the voice in one row of alike frames (a second row on a narrow window); the explanations on a '?', problems in sight; Tied to it behind a button (0.35.0)
- 🧪 Recolour... on a texture: one battle-model texture (Unit editor) or figure texture (Models tab) in the faction's colours (0.35.0)
- 🧪 Models tab slimmer: each texture card its title and where it shows, the rest on '?'; the Culture / Faction switches taken out again (0.35.0)

## 🧪 Being tested in the game now (newest first)

- 🧪 Map cut / delete a town: a campaign script naming it is no refusal any more - its lists and one-line commands are commented out, its conditions named (Medieval II's right edge with Baghdad and Mosul can be cut) (0.34.0)
- 🧪 Medieval II: resources left on a wasteland's land - one question, delete them or keep them; a renamed faction followed in the campaign script; music for new regions; a later faction's message in the game's own form (0.34.0)
- 🧪 Every picture opens big on a click (Unit and Building editors too); View in 3D opens once a model, keeps its frame while it plays, the right button moves the view; a siege crew's dagger without a second weapon (0.34.0)
- 🧪 The map shows a resource's name under the mouse; a ship unit's fleet in 3D; Show's faction gives the unit its colours (0.34.0)
- 🧪 Reports carry screenshots made smaller (a few fit the 4 MB) and say what of a big game log goes (0.34.0)
- 🧪 View in 3D: the rider sits on his horse in any animation and the horse plays the same move (Medieval II; Rome's riders sit, the horse plays the same name or stands); Medieval II's siege engines in 3D; a knight's second weapon set with his second skeleton; the rider turns with a turning horse; a horse moves on its own bones; the weapons' own moves in the hand (a javelin thrown point first); animations play smoothly at the game's speed, in the whole texture (the 3D view on NumPy, about 5 x quicker); the wheel turns a drop-down again where nothing scrolls (0.34.0)
- 🧪 Battle models: a battle_models.modeldb with two numbers written without a space ('0-1') read as the game reads it; Check mod files names a faction's AI label the campaign AI file lacks, a governor's building that does not fit its town's size and a port with no sea beside it (Medieval II) (0.34.0)
- 🧪 The map names the man under the mouse beside it (a general's name, 'Captain <name>' for an army without one), as the game does (0.34.0)
- 🧪 The editor's own files (settings, logs, add-ons) in a folder of their own, CampaignEditor, beside the exe - an older version's moved in after one question (0.34.0)
- ✅ Religions of a town and of many selected regions at once from the Map's right click (Medieval II; Barbarian Invasion's beliefs per region too); Edit regions' bar shorter (0.34.0) *(in-game ✓ from a report)*
- ✅ New land that joins nobody: ONE common wasteland region for all the free land (Rome with REX, Medieval II with M2EX) - the Land / shape brushes' default, and the land a map cut leaves of a town it takes (it crashed Medieval II with M2EX) *(in-game ✓ a map cut with the wasteland on both games' own campaigns)* (0.34.0)
- 🧪 Terrain: Pull and Push the coast (pull drags the coast with the mouse like a painter's liquify; push grows the land into the water or the water into the land) (0.34.0)
- 🧪  unit's card and description picture made from its 3D model (View in 3D > Make a card... / Make a picture...): the frame you pick, the game's framing, your own ground or the game's card ground, Medieval II's picture frame *(in-game ✓ a card and a picture replaced, Medieval II)* (0.34.0)
- 🧪 The Module builder opens in the main window (a work like Maps), its unsaved module kept across works; View in 3D: scrub the animation frame by frame; Models lists only the type's own figures; mounts in their whole texture (0.34.0)
- 🧪 View in 3D plays the model's animations from the game's packs (Rome, Barbarian Invasion, Medieval II): any move of its skeleton, Play / Pause, frame by frame - step 1 of the 'cards from the 3D model' road (0.34.0)
- 🧪 Set-up fix: the engine's settings files go into a mod with every setting switched off (the mod runs as before - the game's copy made Medieval II with M2EX miss the mod's battle models); a mod with the game's `model_battle_source text` is put right on Load; Campaign rules shows switched-off settings (0.34.0)
- ✅ Start Rome for a mod in `mods\<name>` (`-mod:mods/<name>`); the report window's text box grows (0.34.0)
- 🧪 No scrollbars: lists, tables and pages scroll by a left drag (both ways) and the middle button's autoscroll (0.34.0)
- ✅ New mod folder on the plain game makes a thin mod (only what you change; the whole map folder at the first map change); the editor asks once before writing into a mod it did not make (0.34.0) *(in-game ✓ from the tester)*
- 🧪 Recolour: an area of like colour painted with one click (a quick select beside the brush) (0.34.0)
- 🧪 Recolour into black / white looks like the game's own: a battle texture starts from the nearest-coloured faction's texture of the model (the artist's black / white, folds and faces kept) (0.34.0)
- 🧪 The test mod's report lists the steps to look at in the game first, the ones already seen working below (0.34.0)
- 🧪 Terrain: Land and sea makes a smooth coast like the games' own (half-tile curve, islets and straits kept); the brush outline follows while painting (0.34.0)
- ✅ Add-ons: an older version in the game is found on Load and put right with one yes (settings kept); no more 'font autoscale' in the script console *(in-game ✓ from a report, Medieval II with M2EX)* (0.34.0)
- ✅ Terrain: the shape brush - a coast drawn where you want it, smooth in the game (heights by distance from the edge, exact in map_heights.hgt); 'Smooth the coast' rounds a coast as a shape; the map by points + the Shore line as the game draws it; the coast pen *(in-game ✓ from a report, Medieval II with M2EX)* (0.34.0)
- 🧪 Terrain: find ground on the wrong side of the coast (land texture on the water, holes of sea in the land) and put it right under the heights; the Ground brush stays on its side of the waterline; the beach painted on land, as in both games (0.34.0)
- 🧪 Terrain: the minimap follows painted land, sea and ground (drawn from the nearest tile of the same ground) (0.34.0)
- 🧪 Map size: no black band after a grow (the fog's frame moves to the new edge); the minimap's border and sea follow (0.34.0)
- 🧪 Terrain: impassable land, always black (REX / M2EX's impassable_shrouded) - for a wasteland's land hidden for good (0.34.0)
- ✅ bug report carries the list of the mod's files (names, sizes, dates, new / other size than the game's - no contents) (0.34.0) *(in-game ✓ in every report)*
- ✅  deleted town's region can stay as a wasteland (Rome with REX, Medieval II with M2EX): nobody's land, no neighbour grows; right click its land to give it its town again; the land a map cut leaves goes to the one common wasteland (0.34.0)
- 🧪 Faster on a big mod: many towns deleted at once (21 s -> under 2 s on HLR), the town window about 5 times faster and smaller (it remembers its size) (0.34.0)
- 🧪 Map size: a cut that takes a faction's last town takes the faction out of this campaign (it stays in the mod); the cut waits for Apply, so a town given meanwhile keeps the faction (0.34.0)
- 🧪  new version of the editor is seen on every start (and every 6 hours while it is open): the GitHub button turns green with its number (0.34.0)
- ✅ A region with no town of its own (the game's rebel village): its town window writes the town for an owner picked (the rebels too); Edit region shows and changes the owner (0.33.0) *(in-game ✓ from a report)*
- 🧪 Sack Settlement (Medieval II): the Raze button's words in the game's own Verdana, no hover text, the capture scroll one button taller (the button stays under Exterminate if the game keeps the size); Avoid Growth's words in Verdana too (0.33.0)
- ✅ Merge regions on the map (both games): click the region that stays, then its neighbour that goes - its land joins the first, everything tied to it follows (0.33.0)
- 🧪 Many towns deleted with their regions at once (the map's Select, both games): each region's land to a neighbour that stays, shown on the map (red goes, yellow takes land, green could) - a click picks another neighbour; one write, one Undo (0.33.0)
- ✅ Map size by dragging the map's edges (both games) *(in-game ✓ a cut on Rome with REX, Medieval II with M2EX and a big Medieval II map)*: out adds deep sea, in cuts tiles off (shown dark); what stands on the part cut off is ringed red on the map and goes with the cut after a question (family members move to their faction's nearest town) (0.33.0)
- 🧪 A new religion from nothing (Medieval II, Barbarian Invasion): its symbol drawn by the editor, temples of its own made from nothing (0.33.0)
- ✅ A new building from nothing (both games): say what it is for and how many levels, every line written with the mod's usual numbers for such buildings; levels side by side, any effect the mod uses, the units it trains, plain pictures drawn (0.33.0)
- 🧪 A new unit from nothing (both games): say what kind it is, the editor writes every line with the mod's usual numbers for such a unit; you set each one, its model, owners, where it is trained; plain cards drawn when you have none (0.33.0)
- 🧪 Your own files for a unit's battle model (both games): your texture (every faction or one), Medieval II's weapons texture and your own .cas / .mesh put in, converted, named and written; a model of its own when other units share it (0.33.0)
- 🧪 Module builder: WHEN 'the player's turn starts (once a turn)' - the default for new modules; 'every faction's turn starts' says plainly that it comes for each faction (0.33.0)
- 🧪 Fix: Recolour never writes over an original battle texture - it copies it, recolours the copy and points the faction's line at it; a faction with a texture but no weapons texture gets that line (Medieval II men like bare skeletons in battle), Load offers it for the whole mod (0.33.0)
- 🧪 A town's own garrison with no captain (`garrisoned_army` in the town's block - some mods use it for every town): read, shown in the town window and the garrison editor, changed in place, checked (0.33.0)
- 🧪 Fix: closing the editor never ends in a Windows error box (0.33.0)
- 🧪 Unit cards and building pictures as the game shows them, in every window (one lookup for all; checked over every unit and building of Rome, BI and Medieval II) (0.33.0)
- ✅ Start the game names the mod it starts (amber without one); the test mod is offered to be started at once; its modules act only in the test mod (0.33.0)
- ✅ Avoid Growth: only on the Construction tab, in Rome looking like Automanage; forts and watchtowers keep a tile from towns and from each other (0.33.0) *(in-game ✓ on Rome + REX: the tick in Rome's look, a town held at its ceiling; REX's scroll does not say which tab is open, so there the tick shows on every tab)*
- ✅ Fix: plain Rome is never given a faction that starts dead (the game stopped reading descr_strat there: empty rebel towns, no diplomacy) (0.33.0)
- 🧪 Fixes: painting on the Terrain tab right after Apply; ports for regions without one; an add-on's old copy outside script\modules is shown, moved or taken out (0.33.0)
- ✅ Module builder: ELSE, all / any / none of the conditions and NOT, FOR EACH town / army / faction - the control blocks of Scratch (0.32.0)
- ✅ Module builder looks like Scratch: coloured blocks dragged into each other (the old lists one click away) (0.32.0) *(✓ in the window, from the tester)*
- 🧪 Edit faction > Rename...: a faction's code name changed in every file at once (0.31.0)
- 🧪 Hover a unit or a building in any list: its card; a click on a column heading sorts any table (0.31.0)
- 🧪 One language in every window (Preview / Write it in / Keep for Apply, Enter and Esc, answers in words); the right mouse button takes things out of lists (0.31.0)
- 🧪 Backups: one put back is deleted (no more `_restored` folders); Settings can delete all of a mod's backups (0.31.0)
- 🧪 Every window keeps its changes for one Apply (Mercenaries, Events, Campaign rules, Traits, Many towns, Recolour) (0.31.0)
- ✅ Mods that hold only the files they change load (the rest read from the game's data, as the game does); changes go into the mod as its own copies (0.31.0) *(in-game ✓ from the tester)*
- 🧪 Fixes from the in-game test runs: Medieval II diplomacy written in its own form (and old lines put right on Load), new texts seen in Medieval II (the old compiled `.strings.bin` taken away), Module builder message pictures, BI bad harvests and watchtowers follow their regions, Sack Settlement ignores revolts, storms only at sea (0.31.0)
- 🧪 One write for the session: the town and character windows keep their changes for Apply; one Apply writes everything waiting; Undo takes back the last part or the whole write (0.30.1)
- 🧪 Fixes: Module builder / Add-ons on a Medieval II game with packed data; a long set-up list on Load scrolls and closes (0.30.1)
- ✅ Religions in Barbarian Invasion: a new belief (`descr_beliefs.txt`, its pips and texts); the test mod gives it temples of its own (0.30.0) *(in-game ✓ from a tester)*
- 🧪 Bigger map (x3): the values in fields of their own (heights, smoothing of the lines, narrow rivers, crags, valleys, volcanoes) with their defaults, what was tried, and a reset; the shore by the water the games' own (no teeth on diagonal coasts) (0.30.0)
- 🧪 Map > New army: Make him a general (his bodyguard leads the army) (0.30.0)
- 🧪 Discord, YouTube and GitHub buttons; GitHub shows the number of a newer release when one is out (`GitHub (new 0.30)`); Settings and Help now in Tools; the bottom buttons wrap on a narrow window (0.30.0)
- 🧪 Credits - a page and a window that thank everyone who made the editor with us: testers, ideas, supporters ([CREDITS.md](CREDITS.md)) (0.30.0)
- ✅ Start the game with the loaded mod from the editor - one green button beside Tools (the mod's start script, or the engine's own line) (0.30.0)
- 🧪 Add-ons > Scripts in the game: every script in the game's script/modules - settings, off / on, delete; the test mod's scripts taken out with one press (0.30.0)
- ✅ Map editor: delete a town with its region - its land goes to a neighbour, every file that ties them follows (descr_regions, descr_strat, mercenaries, win conditions, music); what would break the game is refused in plain words (0.30.0)
- 🧪 Map: Select - a box round many things at once, as in a strategy game: give the towns, add a building or garrisons, take characters, resources and forts off the map (0.30.0)
- 🧪 The town window has the Buildings and Garrison editors of the main window, for any town (0.30.0)
- ✅ Module builder (both games): your own add-on made of WHEN / IF / DO blocks picked in plain words, no code - the mod's own names, nine examples, settings for the player, Put it in / Share (0.30.0) *(in-game ✓ on Rome + REX, Barbarian Invasion + REX and Medieval II + M2EX: money and messages given, loot for a town taken - from the in-game tester)*
- ✅ Module builder: every event, condition, console and campaign-script command of REX / M2EX (from the engines' own lists, with a search and the parameters as fields) and numbers kept between turns (0.30.0)
- ✅ Add-on Avoid Growth (both games): a tick on your town's scroll in the game's own look - the town keeps at most the people it has, may shrink and grows back to that (0.30.0) *(in-game ✓ on Barbarian Invasion + REX: a town ticked and held at its ceiling - from the in-game tester)*
- ✅ Test mod: every campaign rule changed in one step (Medieval II 548 values, Rome 162), the game must read them all (0.30.0) *(in-game ✓: Medieval II + M2EX read all 546 values and played 11 turns, Rome + REX played 10 - from the in-game tester)*
- 🧪 Sack Settlement (both games): the governor's building always stays, 600 people at least in the ruins (0.30.0)
- 🧪 Sack Settlement for Medieval II (M2EX) as a button of the game's own kind: the same script as Rome's, drawn from the scroll's own button pieces in the game's font; the older Lua copy taken out (0.30.0) *(in-game ✓: the button on the capture scroll - from the in-game tester)*
- 🧪 Answers to my reports: the author's reply comes back into the editor (report window tab, "(1 new)" on the Report button), and you can answer back with words or a screenshot (from Discord) (0.30.0)
- 🧪 The bigger map (x3) moves the campaign's scripts too: spawned armies, moved characters, camera, revealed tiles, 'near a tile' conditions (from a tester's game: scripted armies stood off the map) (0.30.0)
- 🧪 Drawn garrisons fit the town: only what its own buildings recruit, else the cheapest units (0.30.0)
- ✅ Factions that appear later: by an event, as a faction's shadow (civil war) or splitting off in a revolt - New faction and Events... (from Discord) (0.30.0) *(in-game ✓: the shadow way on Medieval II + M2EX and Barbarian Invasion + REX; the split-off way and the event way on Medieval II + M2EX - from the in-game tester)*
- 🧪 A double click on a town opens its own window (owner, city / castle, level, population, buildings); many towns made city / castle and of another level at once (from Discord) (0.30.0)
- ✅ REX / M2EX: no faction limit - max_factions raised by itself with every new faction (0.30.0)
- 🧪 A town on its region's edge stays its region's - on the Map and in the bigger map (from a report) (0.30.0)
- 🧪 Rome 3D: weapons, shields, crests and engine parts on their bones; T pose by default; chariots with horses and crew; siege engines (from a report) (0.30.0)
- 🧪 Unit and Building editors without the lag on picking and adding (from a report) (0.30.0)
- 🧪 Events: the scroll's picture shown and replaced (every culture), what each kind does in plain words (from a report) (0.30.0)
- ✅ Campaign rules: the REX / M2EX engine settings (descr_ex.txt, descr_caps_ex.txt), each explained by the engine's own comment (from a report) (0.30.0)
- 🧪 One temple per town, as the games want: kept in the Buildings tab, the many-towns window and Check mod files (0.30.0)
- 🧪 Terrain: impassable land / sea brushes (Medieval II; Rome with REX); new land stands in shallows (from reports) (0.30.0)
- 🧪 Map: the sign being placed rides under the mouse; switching a mode off unpicks what it picked; no separate forts mode (all in the legend and the right click); readable resource letters; the map's size under the map (from reports) (0.30.0)
- ✅ Edit region holds both names of a region and its town: the names players see and the names in the files (the Map's extra Rename buttons gone) (0.30.0)
- 🧪 Units and buildings brought from another mod lose conditions this mod does not have (a hidden resource, a religion) - the game no longer stops at start (from a report) (0.30.0)
- 🧪 New forts and watchtowers on campaigns that have none (vanilla Rome and Medieval II), written in the regions section (0.30.0)
- 🧪 Roster: no error on a double click right after Apply (from a report) (0.30.0)
- 🧪 Windows open in the middle of the screen; hover texts stay on screen; wide drop-down lists; long field texts shown on hover; '?' visible in the Dark look (from reports) (0.30.0)
- 🧪 Faction tab in two columns; the editors' block lines fold away behind a button (from reports) (0.30.0)
- 🧪 Bring from another mod / New unit and building: the picked one shown as the game shows it (pictures, texts, effects in plain words); units: one line each for where they are trained; two pictures per building level (from reports) (0.30.0)
- 🧪 Faction emblem fitted by hand: move, size, turn, the old emblem's disc or a circle / square, a ground colour, magic wand, paint bucket (from a report) (0.30.0)
- 🧪 Wonders (Rome): their window as in the game, 3D view, Put a wonder here (from a tester) (0.30.0)
- 🧪 Traits and retinue: every bonus the game knows on a right click, in plain words (from a report) (0.30.0)
- 🧪 Map: Delete from the map (right click) - resources, forts, towers, wonders, characters of any faction (from a report) (0.30.0)
- ✅ Add-ons put where REX loads them (the game's script/modules); new add-on Player Diplomacy (from a report) (0.30.0) *(in-game ✓ from the tester)*
- 🧪 Victory regions picked many at once or on the map; map signs grow as the mouse comes near (from a report) (0.30.0)
- 🧪 People and family: one Add a person... step by step, the tree on the right on the Faction tab too (from a report) (0.30.0)
- 🧪 Character panel: click the pips to set Command / Influence / ... - the traits fitted to it (from a report) (0.30.0)
- 🧪 Building editor: names and descriptions per culture / faction; the editors' list width dragged (from a report) (0.30.0)
- 🧪 The new symbol on Rome's 3D battle banners and the campaign map's flag: the game's blank white banner dyed in the faction's colour or a pattern (tricolours, quarters, crosses...), the symbol painted on (from a report) (0.30.0)
- 🧪 Recolour: a bright colour of its own kept (gold next to red), the faction's colours set with the pictures, pictures fit the screen (from reports) (0.30.0)
- ✅ Map: armies, fleets, agents and towns for any faction - the land clicked says whose, changeable in the window; Give this town to any faction (right click) (0.30.0)
- ✅ Map: a port from the legend (a region without one gets one); picked towns' regions in yellow; generals' flags for every named character; painted tiles always visible while painting (from reports) (0.30.0)
- 🧪 Check mod files: building lines naming a hidden resource, resource or religion the mod lacks; a screenshot pasted into a report with Ctrl+V (from reports) (0.30.0)
- 🧪 Banner... on the Art tab, both games: the battle banners from a white banner - a pattern of your colours, a symbol where you draw it, or your own drawing on the saved template; Medieval II's white template made from the mod's own banner sheets, seen in 3D (0.30.0)
- 🧪 The bigger map (x3): rivers stop at the new coast (no sandbar off a river mouth), the beach one tile wide (from a report) (0.30.0)
- 🧪 The bigger map (x3) drawn the way nature draws: rivers bend and meander (one pixel wide), the coast, the borders of regions, ground types and climates wind instead of following 3 x 3 squares; the relief gets crags on the mountains and river valleys (0.30.0)
- 🧪 The bigger map (x3): no flickering wedges on the coasts, no islets in navigable rivers, volcanoes keep their cones, mountains never flat, lakes with gentle banks (from reports) (0.30.0)
- 🧪 The bigger map (x3): a border that ran along a river stays on the new river, no lone pixel sticks out of a border, and a message says what to look over by hand once the map is written (from a report) (0.30.0)
- ✅ One faction with both a shadow and a faction splitting off it: refused only in plain Rome (it crashed at the end of a turn); Medieval II + M2EX and Barbarian Invasion + REX take it, and Preview says that the revolting towns go to the shadow, so the split-off faction does not come while the shadow is there *(in-game ✓ on both - from the in-game tester)*; a shadow gets no victory conditions (the game stopped reading them) (from the test mod) (0.30.0)
- 🧪 Medieval II: a faction that comes by an event arrives as a horde - the editor writes its horde lines and its event's text (from the test mod) (0.30.0)
- 🧪 The Terrain editor is a tab of the Map editor; the top row moves with the wheel or a drag, no arrows; buttons no wider than their words (from reports) (0.30.0)
- ✅ Shadow and split-off factions offered only in Barbarian Invasion and Medieval II (plain Rome cannot take them) (0.30.0)
- 🧪 Terrain editor: Land and sea no longer lags while painting (0.30.0)
- ✅ Test mod: every feature and every option (59 steps), with a table of which step tried each feature (0.30.0)
- ✅ Campaign rules: the campaign's start - dates, years a turn, brigands and pirates, the switches on / off (the top of `descr_strat.txt`), written in the order the game reads them (0.30.0)
- 🧪 Unit editor: the attributes of the newest REX / M2EX builds (immune to arrows / fire, resistance to missiles, enduring fortitude, life steal, hardy, strong against / ignoring armour) (0.30.0)
- 🧪 Unit and Building editors: Every line of the block opens in a window of its own (0.30.0)
- ✅ Events: new ones put in date order (the games read them as a queue - a new Rome event never came), 'turn N, year X' beside each date; a historic event always gets its text (0.30.0)
- 🧪 Fixed from the test mod in both games: new factions keep their towns (lost on turn 1 since 0.29.1 - Load offers the fix for older mods); Rome's campaign loads after a campaign switch is changed; Rome's victory conditions read in full; Medieval II units no longer grey stripes after Recolour; units given by Roster / a new unit / Bring wear the faction's colours in battle; a fifth child in Medieval II; town populations the game takes at the start; Rome's slaves resource for new regions (0.30.0)
- 🧪 Recolour more exact (black / white faction colours, shading, Medieval II shields and the carroccio) (0.30.0)
- 🧪 Rebel towns' garrisons drawn as the game makes them (the region's own rebels) (0.30.0)
- 🧪 The mod at a glance in the log; reports keep each middle error's message and never send a log twice; the logs folder kept small (0.30.0)
- 🧪 Map editor: the map alone, no faction to pick - drag and give anything of any faction, any army's units (0.30.0)
- 🧪 Stability for 0.30: one mouse-wheel handler for the whole window; going back to an older version never breaks on what a newer one wrote; the exe checks itself before it is handed out; a full disk, a too-long path, no rights or a file held by the game said in plain words with nothing lost (Restore runs again); no internet never hangs anything; a mod with only its changed files explained on Load; a step left over from a closed window can no longer call a new one; the code checked with Ruff before every build, files read in passing closed at once (0.30.0)
- 🧪 Medieval II banners: every look of the small pennants dyed, no seam on the cavalry banner (0.30.0)
- 🧪 Module builder: the engines' builds of 2026-10-04 - a faction made another's protectorate or client (0.30.0)
- ✅ A faction that lives without towns (REX / M2EX's `can_homeless`), a tick in How a faction comes into the campaign - written right before `can_sap`, after the horde's last unit (0.30.0) *(in-game ✓: the line read by Rome, Barbarian Invasion and Medieval II - from the in-game tester)*
- 🧪 Campaign rules and the Module builder marked experimental (a red line: try it, send a report) (0.30.0)
- 🧪 Delete a mod's folder from Tools (asked twice; never the game's own data) (0.30.0)
- 🧪 Forts and watchtowers drawn as a stone castle and a wooden lookout (0.30.0)
- 🧪 Barbarian Invasion: a new faction's campaign-map figures recoloured; Rome: a faction that comes by an event comes as a horde (0.30.0)
- ✅ Bigger map (x3) step by step: grid, smoothing, heights, rivers, objects - each checked, the map fixed by hand between them (0.30.0)
- 🧪 Where a building can be built / where a unit is recruited (windows of their own in the editors); taking a region tag off lists what stops working; town names never cover each other (0.30.0)
- 🧪 Save the campaign map as a picture; Find matches the names players read (0.30.0)
- 🧪 Check mod files checks the building tree's shape (chains twice, missing levels, upgrades / convert_to / requirements naming nothing) (0.30.0)
- 🧪 Is this faction complete? (Check mod files with a faction picked): every file that names every other faction but not this one (0.30.0)
- ✅ Map size: grow the map at any edge by whole tiles (deep sea) or cut it; towns, armies, resources, events and scripts move with it (0.30.0)
- 🧪 Mercenaries: a region's hire list made the garrison way (cards), pools of regions picked on the map the Select way, their units' numbers in plain words, new pools, units added / taken out (0.30.0)
- 🧪 Check mod files lists the problems worst first, by when the game would meet them, each with a button to the place that fixes it (0.30.0)
- 🧪 Start the game checks first: a missing exe refused, a Medieval II .cfg not naming the mod asked about (0.30.0)
- 🧪 Bigger map (x3): no water wedges or foam-ringed squares on the coast, no land bridges over navigable rivers, river mouths ending on the land at the water (never on it), small islands and lakes round, shallow sea along every coast, no cliffs or beach (painted by hand where wanted), mountains only where the heights stand high (0.30.0)
- 🧪 Started outside the game's folder, the editor offers (once per version) to put itself there - you pick the game's folder, it copies itself over with its settings and a desktop shortcut (0.29.2)
- ✅ The bigger map keeps the rules of the games' own maps: one coast for regions and heights, every town with its own region round it, every port on a coastal land tile, ground types and climates by tile (forests stay forests), land bridges unbroken (from five reports on Divide and Conquer) (0.29.2) *(in-game ✓ Rome + REX, vanilla campaign played)*
- 🧪 A new faction gets its faction-select buttons and the template's other pictures - also when the template's name holds `_` (greek_cities) or its pictures lie only in the game's data (from a report) (0.29.2)
- 🧪 Apply is all or nothing: a file the system refuses (read-only, held by another program) leaves the mod as it was, said in plain words (from two reports) (0.29.2)
- 🧪 A mod's engine settings (`descr_ex.txt`, `descr_caps_ex.txt`) read from the mod alone, as REX / M2EX read them (0.29.2)
- 🧪 New regions on a big map get a colour (the search tried only 200); a modeldb with models after its count is read; changes waiting for Apply never go into another mod and are never dropped without asking (0.29.2)
- ✅ Raze Settlement for Medieval II (M2EX): a 4th button on the capture scroll, the ruins to the rebels (0.29.1; replaced by the button of the game's own kind - see above)
- 🧪 Fixed: a new Medieval II faction keeps its template's AI rule set (`ai_label`) and money every turn (`denari_kings_purse`) (0.29.1)
- 🧪 Medieval II faction logos (M2EX xml sprite sheets) on the Art tab and in the emblem; shared banners and 3D symbol textures pulled apart so a recolour changes one faction only (0.29.0)
- 🧪 The bigger map: ground and climates with natural edges (no 3 x 3 squares); the preview says plainly nothing is written until 'Write it' and shows the new size after (0.29.0)
- 🧪 Faction emblem: one picture made into every place the game shows it (menu buttons in all states, loading screen, logos), each in its own size (0.29.0)
- ✅ Recolour a faction's pictures: unit cards, battle textures, symbols, banners - from the template's colours to the faction's own, light and shade kept (0.29.0) *(in-game ✓ from a report)*
- 🧪 The exe in the game folder, logs saved on every close, M2EX / REX found by any name, missing engine files offered (0.29.0)
- 🧪 Buildings and garrisons for many towns: pick towns on the Map (yellow) or by owner / level / city / castle; a building in all of them, or random garrisons under an upkeep limit (0.29.0)
- 🧪 The game's log in plain words (Tools): a crash first, errors grouped with what they mean and the mod's line (0.29.0)
- ✅ Reports find the game's log in every mod folder, and say how to switch it on (0.29.0) *(in-game ✓ in the reports)*
- 🧪 Terrain editor: Land and sea - a new island, a bay, a strait (regions, ground, heights and map_heights.hgt changed together) (0.28.0)
- 🧪 The bigger map, second alpha: smooth coast, heights 3 x higher in proportion (or as they were), map_heights.hgt rebuilt at the new size, rivers as staircases running on to the new coast (0.28.0)
- ✅ Bring units and buildings from another mod, step by step (Unit and Building editors), with a wiki guide (0.27.0) *(in-game ✓ on Rome + REX: 12 units brought from Barbarian Invasion, fought in battle)*
- 🧪 Map: a right-click menu (a town's garrison and buildings, open a character, a new army / agent / fleet on that tile); a character dropped on a town's sign goes into the town (0.26.0)
- 🧪 Roster: a building level pulls its chain along (lower levels given with it, higher ones taken with it) (0.26.0)
- 🧪 Search on the Units & armies tab: towns by name, armies by name or by a unit inside them (asked in a report) (0.26.0)
- 🧪 Fixed: a mod without `descr_names.txt` no longer stops the window when a template is picked (from a report) (0.26.0)
- 🧪 The Map's legend as a palette: pick a town, fort, watchtower, resource, army or agent, click the map to make one (0.22.0)
- 🧪 Alliances and wars at the start (both games): one status per faction that pulls the AI feelings along, every value in words; Medieval II's diplomacy read as the game writes it (`faction_standings`), a new Medieval II faction at war with the rebels (0.23.0)
- 🧪 Victory conditions on the Faction tab: regions to hold and take, factions to outlive, Rome's goal - long and short campaign (0.23.0)
- ✅ Wonders on the Map (Rome): shown, dragged, added, removed; the map's real size shown (0.25.0)
- 📦 The layout board: every page of the editor side by side on one canvas - buttons dragged into their rows or anywhere (Alt), sized by their corners, renamed, hidden; shown in the editor at once
- 📦 The editor's own look: Tools > Edit the editor's look - any button, tick or label dragged anywhere, renamed, given a hover text or width, hidden, taken back; the window's language from a language file (Settings), Words to translate for the community
- 🧪 A Settings window (look, language, game folder, the map's look, report contact, set-up questions, folders); Check mod renamed Check mod files (0.24.0)
- 🧪 The family tree folded behind a Family tree button on the Faction tab; hover texts on the work buttons (0.23.0)
- 🧪 A faction's religion pulls its temples, guilds, priests and their figures along (Medieval II) (0.22.0)
- 🧪 Rome's packed textures (data/packs/*.pak) read for the model thumbnails and 3D (0.22.0)
- ✅ Events and later factions: the campaign's plagues, volcanoes, earthquakes and historic messages - date, place, texts, new ones (0.22.0) *(in-game ✓: earthquakes, plague, floods and messages on Medieval II + M2EX and Rome + REX - from the in-game tester)*
- 🧪 Map colour modes (political / diplomacy / religion / none) and a religion map (Medieval II) (0.22.0)
- 🧪 The map is a free canvas (Map tab and Terrain editor): dragged past its edges, zoomed out smaller than the view (0.22.0)
- ✅ Map: Edit resources and Edit forts & watchtowers apart, each with its how-to; Rename in the files on the Map (0.22.0)
- 🧪 3D view: the mount stands beside the rider; variants counted per part (0.22.0)
- 🧪 Character editor as the game's character panel: portrait, attribute pips, traits by their shown names, the retinue as picture cards; the family tree a click away (0.22.0)
- 🧪 Traits and retinue: what each trait level and ancillary gives, their names and texts, pictures, new ones as copies (0.22.0)
- 🧪 Figures on the campaign map (Art tab): each character type's strat model picked, seen in 3D, its texture replaced; a new faction's figure textures its own (0.22.0)
- 🧪 The main window reorganised: towns picked on the Map, the family on the Faction tab, Add a relative..., a faction's religion (Medieval II), Religions as a work button (0.21.0)
- 🧪 A unit given to a faction is listed once in a building's description; the Map opens on huge maps (0.21.0)
- 🧪 Forts and watchtowers placed, moved and removed on the map (a new one copies the campaign's own line); Barbarian Invasion's watchtowers read (0.21.0)
- 🧪 Volcanoes and (Medieval II) land bridges painted in the Terrain editor (0.21.0)
- 🧪 Save a copy beside every Import / Replace: pictures, a battle model's files, name calls, portraits (0.21.0)
- 🧪 Add-ons from anyone: any REX / M2EX script added, its settings found by themselves, shared as a zip (0.21.0)
- 🧪 One path guard for every write and Restore (only the mod's or game's folder) (0.21.0)
- 🧪 The work buttons scroll instead of being cut; Rome-only fields hidden on Medieval II; the Religions window names its region (0.21.0)
- ✅ **Report a bug / Suggest** (one click, anonymous): ideas too (0.20.1); the logs, a few words and screenshots go to the author through a small relay - no account, no key inside the exe; names cut out first, everything shown before it goes (0.20.0) *(in-game ✓ in the reports)*
- ✅ Settlements tab: every region and town, the names players see, owners, names by culture; rename a region and its town in the files everywhere the mod names them (0.20.0) *(in-game ✓: renamed towns on Medieval II + M2EX and Barbarian Invasion + REX - from the in-game tester)*
- ✅ Campaign rules (Tools): every value of the campaign's settings files with a plain explanation - Medieval II's campaign_db, town growth / order / income, diplomacy, recruitment; Rome + REX the people each town level needs; the Unit size choices (0.20.0) *(in-game ✓: read and played on Medieval II + M2EX and Rome + REX - from the in-game tester)*
- ✅ Add-ons: Sack Settlement for Rome + REX with who may sack (only the player, everyone, hordes, picked factions); the kept buildings and rebel units picked from the mod's own (0.20.0) *(in-game ✓ on Rome + REX: a town sacked - its buildings torn down, the reward paid, the ruins and a rebel garrison to the rebels)*
- 🧪 View in 3D for Rome's .cas models (every vanilla unit, mount and animal), both games take missing model files from the game's data; weapons off no longer hides the legs, detail levels in order (0.20.0)
- ✅ Tools: New religion / Religions of a region (Medieval II); a Medieval II clone's texts say "the Kingdom of Jerusalem" right (0.20.0)
- 🧪 Hear a unit and give it a voice (Unit editor, Voice in battle): its name call and orders played from the game's packs, your own .wav as its name call (0.19.2)
- 🧪 Faction lists with the name players see ("turks - Ryazan"); `factions { all, }` buildings for everyone (0.19.2)
- 🧪 Replace a unit's battle model (Unit editor, Battle model: Replace model...) - from this mod or another mod of the same game, with its files; the unit's factions get textures; a model made to sit otherwise (foot / horse / camel / elephant / chariot) is warned about; View in 3D (0.19.0)
- 🧪 New unit / New building step by step (Unit and Building editors): Back / Next between the steps, every file shown before it is added (0.19.0)
- 🧪 Check and install a pack (Tools): every file of a "copy data over the game" mod checked - REX's own files, pictures of another size, whole text files - and put in as picked, with a backup (0.19.0)
- 🧪 Medieval II new faction named in battle banners, accents, one-liners, movies and music; the ring round a town (no other region, no port next to a town on Medieval II) checked when moving towns / ports, painting regions and in Check mod (0.19.0)
- 🧪 Big maps: a 4080 x 2496 map opens in 2 s and 0.6 GB (was 38 s and 6.6 GB); region painting checked in a moment (0.19.0)
- ✅ A new religion for Medieval II (0.18.0): New religion... on the Map tab; Medieval II rebels' new armies, agents and fleets (0.18.0 fix)
- 🧪 From the modders' guides (0.18.0): off-map sons kept at 16 or younger; flag symbols from descr_standards.txt (BI's sheets, never a rebels' slot); river blocks and rings warned; Check mod counts the engine's limits and finds win conditions / rebels / slaves faults
- 🧪 The rebels in Edit faction (0.17.1)
- 🧪 Medieval II recruit_pool lines; REX bracket requirements and unit abilities; forts on the map (0.17.0)
- 🧪 Medieval II battle_models.modeldb: clone and unit packs (0.16.0)
- 🧪 Medieval II city / castle switch (0.15.0)
- 🧪 Own name lists, the names-by-culture table (0.14.0)
- ✅ Settlement names by culture on Rome with REX (0.13.0); a New mod folder from BI / Alexander started with -bi / -alx
- 🧪 Terrain climates; Rome flag symbols and faction logos; BI's shared name lists and building pictures (0.12.0)
- 🧪 Family tab and Character editor, own portraits (Medieval II), portrait library (0.8 - 0.9)
- 🧪 Barbarian Invasion campaign loading (0.9.4 fix)
- ✅ Edit region; a new faction starting in a new region in one Apply
- 🧪 Medieval II castle fix (0.7.5), unit packs, new armies / agents / fleets on the map

## 🔜 Next

| Step | What it needs |
|---|---|
| Signed exe (no browser / SmartScreen warnings) | SignPath Foundation's answer (applied) |
| Missions editor (Medieval II / M2EX): the council's and the Pope's missions made and edited - every field, condition and reward | Time; in-game tests |
| The whole Rome campaign moved onto the Barbarian Invasion engine in one click (religions, hordes, night battles for Rome) | Time; in-game tests |
| Diplomacy: a faction that starts as another's vassal (`client_of`, REX + M2EX; the engine setting switched on by itself) | Time; in-game tests |
| M2EX monster units (`descr_monsters.txt`) and campaign voice lines per unit | The format from the engine's authors |
| Terrain: mountains and hills kept in step with the heights (a mountain tile raises the land) | Time; an in-game test |
| Terrain: a tilted 3D view from the heights and ground (asked on Discord) | Time |
| Terrain: a new climate of one's own | Time; in-game tests |
| A new campaign map from scratch (one region, one faction, loads in the game), then grown in the editor | Time; in-game tests |
| The bigger map, after the alpha: plains really flat and mountains with sharp peaks (heights follow the ground type), clean coasts; grow or cut the map's edges | Time; in-game tests |
| Faction packs (like unit packs); building chains as a .zip to share | Time; then an in-game test |
| Mods made on the plain game (slimmed folders) loaded with the game's data behind them | Time |
| Check mod files: the crash rules modders documented (undeclared ai_label, religions not summing to 100, a region with no town not last, event texts, antitraits, dead ancillaries, absolute paths, a town touching another region) | Time |
| Limits shown up front on the original exes (REX / M2EX lift most): units (500), building chains (64 Rome / 128 Medieval II), levels (9), religions (9) | Time |
| A religion of one's own, step by step in its own window: name, symbol, text, its temple chain (levels, pictures, effects like the Building editor), which factions follow it - Medieval II and Barbarian Invasion (BI's `descr_beliefs.txt`, `religious_belief` in the buildings); greyed on plain Rome, which has no religions | Time; BI's campaign files for the test |
| A faction brought over from Rome into Barbarian Invasion (or between any two Rome mods): a faction pack - its units already go over as unit packs | Time; then an in-game test |
| Saved games edited (money, characters, towns of a running campaign), if the save files can be read safely - to be researched first | Research: the save format of both games |
| The window in other languages - the language files themselves (the editor reads them since the look editor: Settings > Language of the window, Words to translate...) | Translators from the community |
| More of REX's settings in plain words (sprites, arrow visibility, fort upkeep, trade fleets...) - the engine files `descr_ex.txt` / `descr_caps_ex.txt` are in Campaign rules already | Time |
| The AI's war plans (`invade_*` in descr_campaign_ai_db.xml) explained in plain words on the Faction tab | Time |
| 3D for everything: buildings, strat-map models, wonders, ships, agents - viewed, replaced and saved (both games); custom models placed on the map, a mode for wonders | Time |

## 💡 Later

| Step | What it needs |
|---|---|
| A culture of its own (buildings, settlements, sounds, and optionally its own interface look - the panels' pictures in `ui/<culture>/interface`), made like a faction clone from a template culture | Whether REX / M2EX limit the number of cultures (HLR runs 11 under REX); the custom-battle culture list is fixed in the game |
| A new campaign-select map drawn from the faction's towns (built in 0.4, put away for now - the original map stays) | Its look checked in both games' start screens |
| Roads and trade routes: see where the game lays them after a new town or port, warn where no path can run | How the engines lay them; in-game tests |
| A **clean faction template**: a new faction without the template's own rules and triggers (the Senate, the Pope, crusades, hordes, scripts), its flags and symbols made white to paint | A list of each game's faction-only rules, agreed first |
| Rome characters with portraits of their own | Whether REX reads a `portrait` line |
| **Borders drawn by the tool**: natural region borders that follow mountains, hills and rivers; new regions generated in an area | How map tools of other games do it; in-game tests |
| **A smaller map** (the reverse of 3 x bigger): the land and heights first, then towns, ports and resources placed back by priority (big towns and capitals stay), regions merged, factions left to the modder | The tool-drawn borders first |
| **A campaign map from the real world**: pick an area on a world map (e.g. Italy or Sicily), get land, sea, real heights, rivers and climate in the game's format; optional real town names and borders filtered by the map's scale; every step generated or drawn by hand, any step skipped | Open map data (OpenStreetMap, GeoNames, SRTM / Copernicus heights, climate maps); the tool-drawn borders first |
| **Rome Remastered: to be looked into** - whether the editor can work with it too. Nothing promised: first we find out if it is possible | Its files checked against the classic Rome's (most text files kept their old form; mods, packed models and pictures are new); the game to test on |
