# RTW & M2TW Campaign Editor

(formerly RTW Campaign Editor / RTW Faction Tool)

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/pfadfinder)

I'm building a tool that finally lets us improve the games of our childhood ourselves - without digging through files every time, without the fear of breaking something, and without everything falling apart because we forgot one step.

[![RTW & M2TW Campaign Editor - video overview](https://img.youtube.com/vi/m1sCPg-Lzsw/hqdefault.jpg)](https://www.youtube.com/watch?v=m1sCPg-Lzsw)

**Video:** [what the editor does, in a few minutes](https://www.youtube.com/watch?v=m1sCPg-Lzsw).

**Why support?** I'm building this on my own on an old laptop. If the tool helps you, a small contribution on **[Ko-fi](https://ko-fi.com/pfadfinder)** would mean a lot - it would help me finally get a proper gaming PC, a childhood dream, and give the editor more time and faster testing (big mods and both games load slowly on the old machine).

A campaign editor for games on the **Rome: Total War engine**: Rome: Total War (with Barbarian Invasion and Alexander, plain or modded, on REX or the original exe) and, in early support, **Medieval II: Total War** (with Kingdoms, on M2EX or the original exe). It works on the game's or mod's own data files, shows every change before writing it, keeps a backup and can undo it byte for byte.

Medieval II: the tool loads and edits it (factions, towns, map, its agents such as merchants, priests and princesses, religions, character lines as Medieval II writes them), but support is new and less tested than Rome's. Medieval II keeps most data in `packs`: load the game folder and the tool offers to unpack it with the game's own unpacker (it copies the two DLLs the unpacker needs, `msvcp71.dll` and `msvcr71.dll`, from the game folder next to it). Set-up problems that stop the game from starting (M2EX's `vegetation_source text` without the raw vegetation maps) are found on Load and fixed with a yes.

- **New factions** cloned from a template: names, texts, colours, units, buildings, cards, start towns, leader and heir, garrisons, buildings, diplomacy.
- **Characters and the family tree**: traits, ancillaries, ages and names of every character, family members off the map, and the family tree drawn like the game's.
- **Name lists of its own**: a faction's men's names, surnames and women's names typed in three steps (one per line or separated by commas), written into `descr_names.txt`, `names.txt` and the lookup together; names its characters already carry are kept.
- **Medieval II battle models (`battle_models.modeldb`)**: a new faction gets its template's textures in every battle model (read and written byte-exact, 701 vanilla models); unit packs carry their modeldb models, renamed on clashes and textured for every new owner, kept in step with `descr_model_battle.txt`.
- **City or castle (Medieval II)**: turn a settlement into a castle or a city on the Buildings tab - `settlement castle` and its buildings converted the game's own way (`convert_to`), only the kind's buildings offered.
- **Edit existing factions**: names and texts, colours, AI, money, playable, towns taken or given, capital, leader and heir, garrisons, buildings, settlement size, armies, fleets and agents, diplomacy.
- **Campaign map**: the map drawn from the ground types, political and diplomacy colours, towns, ports and characters you can drag, new armies, agents and fleets placed by clicking, towns and ports moved, **new regions painted** and borders moved, **resources** placed, moved and removed, religions (Medieval II), **settlement names by the owner's culture** (REX on Rome, M2EX on Medieval II renames a town when it changes hands; the map shows the new owner's name at once; every town's names in one table, sorted and filtered by culture). Big maps load: a tester's map of 5456 x 2464 tiles (map_regions.tga pixels) opened and edits fine.
- **Unit and building editors**: every line of a unit or building chain as a field, pictures imported in the right size and format into the right place, new units and buildings copied from existing ones.
- **Unit packs (export / import)**: take units out of one mod with everything they need - their models (`descr_model_battle`), mount, engine, animal, textures, sprites, cards, names and descriptions and where they are recruited - into one `.zip`, and put them into another mod of the same game. Names that are taken get free ones, nothing of the target mod is overwritten, and it is written with a backup like every change.
- **Faction art**: every picture of a faction listed and replaceable; optionally the campaign-select map drawn from its start towns (off by default - the original stays).
- **Terrain editor**: paint the campaign map's ground (fertility, forest, hills, mountains, swamp, seas), rivers, fords, cliffs and climates.
- **Character editor**: any faction's characters - names, ages, traits, ancillaries - with the family tree and the portraits the game shows, a portrait library per culture to add new portraits to; Medieval II characters get portraits of their own (Replace...).
- **Safe**: a separate mod folder in one click, preview of every file and line, backups with Restore, Undo/Redo in the window, Check mod, and a log.

> [!IMPORTANT]
> ### ⚠️ Something went wrong? Send the logs - and a video or screenshot ⚠️
> When the game crashes, the tool shows an error, or something looks wrong, please send:
> 1. **The logs:** in the tool, **Tools -> Save logs (zip)** - one `.zip` with the tool's log and the
>    game's `system.log.txt` (it is saved in `RTW-M2TW-Campaign-Editor-files/logs` next to the exe).
> 2. **A video or a screenshot** of what you did and what went wrong.
>
> With these the cause is usually found and fixed **the same day** (the logs name the file, line and
> the game's own error); without them it is guesswork and takes much longer.

A step-by-step guide is in the [Wiki](../../wiki). Version **0.11.0** - see [ROADMAP.md](ROADMAP.md) for what it does, what is being tested and what comes next, and [CHANGELOG.md](CHANGELOG.md) for what is in it and what has been tested in the game.

Built and tested on **Barbarian Empires REX Ultimate Edition 1.0.6** (folder `HLR`) running on REX. It reads the mod's own files and doesn't assume their contents, so other RTW / BI-format mods should work too. Reports are welcome.

## Download

- **Windows:** grab `RTW-M2TW-Campaign-Editor.exe` from the [Releases](../../releases) page. No install needed.

**Installing:** make a new, empty folder for the editor wherever suits you (for example `Documents\RTW & M2TW Campaign Editor` - not the game folder, not straight into Downloads or the desktop) and put the `.exe` in it. Start it from there. Next to the exe it makes the folder `RTW-M2TW-Campaign-Editor-files` with its settings and, in its `logs` folder, its log and the logs zips you send with a bug report; an update is simply the new exe in the same folder (the settings stay).
- **Any OS with Python 3.8+:** `python rtw_faction_tool.py` (standard library; Pillow for the pictures).
  **Linux:** the window needs tkinter and Pillow's Tk part, which many distributions ship apart from Python -
  Debian / Ubuntu / Mint: `sudo apt install python3-tk python3-pil python3-pil.imagetk`, then
  `python3 rtw_faction_tool.py` (Fedora: `python3-tkinter python3-pillow-tk`; Arch: `tk python-pillow`).

**Unit packs:** in the **Unit editor**, pick a unit (or narrow the list with Show / Find) and press **Export pack...**: the unit - or every unit the list shows - goes into one `.zip` with its models, textures, sprites, mount, engine or animal, cards, texts and recruit places. **Import pack...** in another mod of the same game shows the units with their names in that mod (taken names get a free one you can change), asks which factions or cultures own them, and **Preview** / **Write it in** puts them in with a backup. A model that exists with other lines is added under a new name; a file that exists is kept, never overwritten; recruit lines go into the same building and level where the mod has them (else the preview says to add them in the Building editor).

## Using it

1. **Close the game** and press **Browse...** to pick the mod's `data` folder (for example `...\Rome Total War Gold\HLR\data`).
2. Pick the **campaign** (usually `imperial_campaign`).
3. Pick a **template**. The new faction gets its culture, units, buildings, character models, name lists, trait triggers and art.
4. Fill in:
   - **Internal name:** lower case, no spaces, for example `saba`.
   - **Name (full)**, **Name (short)** and **Adjective**, for example `Sabaean Kingdom`, `Saba`, `Sabaean`. The copied strings use them ("Sabaean Spy", "Your forces attack an army of Saba").
5. **Starting settlements:** filter by owner (for example `slave` for rebel towns), double-click to add, then pick the capital.
6. **Leader** (and optionally the heir): first name and surname **from the template's name list**. The game crashes on a name that has no string, so the tool only accepts listed names.
7. Press **Preview changes** to see every file and edit. Nothing is written yet.
8. Press **Create faction**. Then start a **new** campaign; old saves don't know the faction.

**A separate mod (recommended):** press **New mod folder...** after loading the mod you build on (for example `HLR\data`). The tool makes `<game>\HLR_Saba\` next to it and loads it; the faction goes there, and `Start_HLR_Saba.bat` (your base mod's start script with `-mod:HLR_Saba`) starts it. The base is never touched. The game reads one `-mod:` folder and falls back to the game's own `data`, so a mod built on HLR holds all of HLR: text files are copied, everything else is a hard link (the same file on disk under a second name - no extra space, same drive only). Explorer shows the linked files at full size (tens of thousands of them), but they take no disk space; deleting the new mod folder never touches the game. Don't overwrite a linked texture in place from an image editor, or tick **Copy every file**. Medieval II: the new mod goes into `<game>\mods\<name>` with `<name>.cfg` (`[features] mod = mods/<name>`) and `Start_<name>.bat`, which starts the game with that .cfg. A mod built on the plain game can be slimmed to the changed files afterwards (`slim` on the command line).

**Garrisons by hand:** the **Units & armies** tab lists your chosen towns (or select one in **Chosen** and press **Garrison...**); pick a town and fill its garrison: the template's units as the game's own cards (upkeep under each, the full line on hover), click to add, click the garrison to take one out, **Suggest** for the balanced pick, **Automatic** to leave the town to the 'Leader's army' / 'Old garrisons' rules on the same tab. The leader's or heir's bodyguard comes on top in the towns they hold; elsewhere the old garrison's captain (or a new one from the name list) leads it. Pictures need Pillow (`pip install pillow`; the exe has it).

**Buildings by hand:** the **Buildings** tab shows, for the selected town, every building chain the faction may build (from `export_descr_buildings.txt`: the level's `requires factions { }` names the template, the new faction or its culture) with the game's picture of the chosen level (`ui/<culture>/buildings/#<culture>_<level>.tga`, falling back through `descr_ui_buildings.txt`'s culture variants and the plain level name). Pick a level per chain or `-` for none; levels too big for the settlement are hidden unless you ask. Untouched towns keep their own buildings; **Keep the town's own** undoes your picks. The preview warns about a level the faction list or the settlement size does not allow.

**Edit an existing faction:** switch **Edit faction** at the top and pick the faction. The window fills with what it is now (names, tooltip and campaign-screen text, colours, AI, denari, playable, its towns). Change what you want; **Units & armies** replaces the garrison of any of its towns (a named character there keeps his bodyguard; a town nobody holds gets a captain), **Buildings** sets what stands in them. Add towns to **Chosen** to take them (their rebels leave; another owner's characters go to its other towns), take towns out to give them to the faction named in **Removed towns go to** (rebels by default; the faction's named characters move to one of its towns, a captain and his garrison go with the town). **Capital** puts that town first in the faction's block. Leader and heir can get new names (from the faction's name list) and ages. Untouched fields and towns stay as they are. **Preview changes**, then **Apply changes** - with a backup, like a new faction. Names and texts change only in the chosen campaign's string tables.

**Map:** the **Map** tab shows the campaign map like a full-window minimap drawn tile by tile from `map_ground_types.tga` (the ground type of each tile: grass, forest, hills, mountains, desert, sea), cities, ports (the white pixels of `map_regions.tga`) and, with **Political**, each region in its owner's colour, see-through, with the towns you picked already in the new or edited faction's colour. Wheel zooms, a left drag moves the map, a click on a town adds it to **Chosen** or takes it out, a right drag (or Ctrl + left drag) moves characters, towns and ports; the line under the map describes the tile under the mouse (region, owner, ground, and whether an army may stand there). **Characters** shows everyone in `descr_strat.txt`: armies as flags in the faction's colour, agents as lettered dots (S spy, D diplomat, A assassin, M merchant), admirals as boats. In **Edit** the edited faction's characters are framed in yellow and can be dragged: the target tile turns green or red (an army needs a tile it may stand on or a town no other army holds, a fleet needs sea, agents any land), and the moves are written with **Apply changes**.

**New armies, agents and fleets:** on **Units & armies**, **+ Army**, **+ Agent** (spy, assassin or diplomat) and **+ Fleet** add a new character with a name from the faction's name list. Select it: an army gets its units from the land cards, a fleet from the ships (the **own units / mercenaries / own + mercenaries** filter next to the category picks whose units show; in mods that mark every ship a mercenary it turns to own + mercenaries by itself; **Show** above the list keeps armies, fleets or agents apart and a click on a heading sorts). **Place on map** opens the **Map**; click a tile: an army needs land it may stand on or a town no other army holds, a fleet needs sea, an agent any land or a town. Placed ones can be dragged there. Works for a new faction and in **Edit**; written with **Create faction** / **Apply changes**.

**What is there already (Edit):** a town's garrison opens as it stands now (marked *unchanged* until you click a card); **Automatic** goes back to it. The faction's armies, fleets and agents already on the map are in **Armies, agents & fleets** too: pick one to change its units (a family member keeps his bodyguard), **Remove** takes an agent, captain or admiral off the map (never a family member), drag them on the **Map** to move them. **Apply changes** asks first and lists the warnings, for example a town left without an army.

**Regions:** tick **Regions** on the **Map**: every region shows in its own colour with its borders. **New region...** asks for the names (region, settlement, their labels), the creator faction, the rebels, the region tags (hidden resources: descr_regions line 6, what buildings' `resource` / `hidden_resource` requirements ask for - not the goods drawn on the map), triumph value, farming level, the owner at the start (or none - the game then makes it a rebel village) and the settlement level; the tool picks an unused colour. Paint its land with a left drag (brush 1-6 tiles; only land changes hands, never a town or port), then **Place its town** and, on the coast, **Place its port** and click the tile (a see-through marker under the mouse shows green where it may go, red with the reason where not; the same when placing a new army, agent or fleet). **Borders** hides the dark borders while painting. The same brush moves the border between two existing regions: right click a region to paint with it, right drag moves the map. Preview lists what is written: `map_regions.tga`, `descr_regions.txt` (8 lines), the campaign's `descr_regions_and_settlement_name_lookup.txt` (the names are appended, so existing ones keep their places), the labels in `<campaign>_regions_and_settlement_names.txt`, a settlement in `descr_strat.txt` for an owner, and `map.rwm` removed. It warns when a region falls into pieces. Borders are not stored anywhere - they are where the colour changes - so the view draws them again as you paint. To change only the map, stay in **New faction** mode with no faction named: **Apply changes** then writes the map alone (the line beside the work bar says so). A new region is in the towns list on the Faction tab at once (marked *new - written with Apply*): a new faction can start there and an edited one take it, all written by one Apply together with the map. **Edit region...** (on the Map's region bar for the region in *Paint with*, or under the towns list for the selected town) opens a new region's data again - names, builder, rebels, tags, triumph, farming, owner, size; a renamed one is renamed on the map, in the towns and garrisons too - and for a region of the map its `descr_regions.txt` lines (builder, rebels, region tags, triumph, farming). A new region given to the faction you edit is one of its towns at once (garrison, buildings, capital) and is written with it in one Apply; its builder, rebels and religions come from the region its land is cut from unless you pick others. Check mod, Scan mod, Restore a backup, Game manifest and Log are in the **Tools** menu.

**Settlement level and population:** the **Buildings** tab has both for the selected town. A governor's building (the `core_building` chain) that needs a bigger settlement grows it by itself - a town with a governor's palace becomes a large town - and lifts the population to that level's threshold (town 400, large town 2000, city 6000, large city 12000, huge city 24000). A level or population typed by hand wins; the preview warns if it is too small for the building.

**Moving towns and ports:** drag a town (the hall) or a port (the anchor) on the **Map** to another tile; a click still picks the town. A town goes on its own region's land (no river, ford, cliff, sea or mountain), a port on its region's coast (sea next to it). The tool repaints the two pixels of `map_regions.tga` (black = town, white = port), moves the characters standing in a moved town with it, and removes `map.rwm` - the game's compiled map, which it rebuilds on the next start (the first start takes a little longer). All of it is backed up and **Restore** puts it back. `map_regions.tga` in `world/maps/base` serves every campaign that has no own copy.

**Regions without a settlement block:** some campaigns leave regions out of `descr_strat.txt` (vanilla: Galatia with Ancyra, Dalmatia, Arabia and others); the game makes each a rebel village with no buildings. They are listed as "village, not in descr_strat" and can be taken like any rebel town: the tool writes the village into the faction's block.

**Family (Edit):** the **Family** tab lists everyone of the faction - the characters on the map (with their traits and ancillaries) and the family members off the map (`character_record`) - and draws the **family tree the way the game shows it**: husband and wife side by side, their children in the row below, the leader and heir marked. Click a card or a row to edit the person: name (from the faction's name lists - the game crashes on a name it has no string for), age, sex (off the map), traits with their level (only traits of the mod for that kind of character, never one with its opposite) and ancillaries. **Give a wife...**, **Add a child...** (someone already in the faction - a new faction's heir as its leader's son - or new family members off the map, written in the file's own form), **Take off the tree** and **Leave out** change the tree; a renamed person is renamed on every `relative` line, also when the leader or heir is renamed on the Faction tab. The tree is checked before writing: everyone on it is someone of the faction, a husband is a man and a wife a woman, nobody has two sets of parents or is their own ancestor; a parent less than 14 years older than a child is a warning. Rome and Medieval II alike.

**Character editor:** **Character editor** at the top: pick any faction (rebels too). The same list, person form and family tree as the Family tab, with the **portraits** the game shows: in Rome the game gives every character one picture of its culture's pool (`ui/<culture>/portraits/portraits/young|old/generals|civilians|rogues/NNN.tga`, picked at random when the campaign starts - the tree shows one of them, and says so), and family members off the map the family picture (`ui/<culture>/portraits/family/wife|son|daughter.tga`). In Medieval II a character on the map can have a portrait of his own: **Replace...** under *young*, *old* or *dead* takes a PNG, JPG or TGA, writes it in the size of the mod's portraits to `ui/custom_portraits/<faction>_<name>/portrait_young.tga` (the ages not given get the same picture) and adds `, portrait <folder>` to his line - the game's own way (vanilla `norman_prologue` does it for William, Rufus and Harold). The editor writes on its own **Apply** with a backup, like the unit and building editors; the Family tab writes with the faction.

**Terrain editor:** **Terrain editor** at the top paints the campaign map itself, tile by tile. *Ground*: low / medium / high fertility, wilderness, sparse and dense forest, hills, mountains, high mountains, swamp, and the three kinds of sea; *Rivers, fords, cliffs*: rivers, fords (the tiles where armies cross a river), river sources, cliffs, or nothing to rub one out; *Climates*: the mod's own climates from `descr_climates.txt` (trees, winter snow, heat), shown on the map in their colours. Left drag paints (brush 1-6), right click picks the ground of a tile, right drag moves the map, **Grid** on or off. Land stays land and sea stays sea (the coast is also the regions and the heights - a later step), and nothing the game refuses is put under a town, port or character. Preview warns about a river tile that touches no other river. **Apply** writes `map_ground_types.tga` (a tile is the 3 x 3 block around its middle), `map_features.tga` and `map_climates.tga` (the same 3 x 3 blocks), and deletes `map.rwm` so the game builds its map again on the next start. The heights are their own picture (`map_heights.tga`): painting mountains does not raise the land - a heights brush comes next.

**Portrait library:** **Portrait library...** in the Character editor shows every portrait of a culture the way the game keeps them - young, old and dead, for generals, civilians and rogues (`ui/<culture>/portraits/portraits/...` with the small cards in `.../cards/...`; the same number is the same man at every age). The game hands them out at random when a campaign starts. **Add portraits...** puts new ones in: any PNG, JPG or TGA is made the size and depth of the culture's own (vanilla 69 x 96 and a 44 x 63 card), under the next free number in every folder of the group at once (the dead one greyed unless you give one), so the game can hand them out too. In Medieval II **Use for <character>** gives the picked one to the picked character as his own portrait. Written with Apply and a backup.

**Your own pictures:** the tool does not draw art. A new faction starts with copies of its template's pictures (unit cards, icons, symbols, banners, the campaign-select map is drawn for it), and a new unit or building with the pictures of the one it was copied from. To make them its own, draw or find the pictures yourself and put them in with **Replace...** on the **Art** tab, **Import...** in the Unit and Building editors, or **Replace...** for a portrait: the tool converts them to the size and format the game wants and writes them to the right place - no copying over the existing files in `ui/` by hand. 3D models, textures and strat-map banners are not handled yet.

**Roster (Edit):** the **Roster** tab lists every unit and building level of the mod and whether the faction has it (by its own name, its culture or everyone). **Give** / **Take away** (or a double click). A unit is really the faction's only when three places agree, and **Apply changes** keeps them in step: its `ownership` in `export_descr_unit.txt`, the `recruit "<unit>" ... requires factions { }` lines in `export_descr_buildings.txt` that let the faction train it, and its cards (`ui/units/<faction>/#<dictionary>.tga`, `ui/unit_info/<faction>/<dictionary>_info.tga`, copied from an owner's). A building level is the faction's through its `requires factions { }` list. When only this faction loses what its culture (or everyone) had, the list is written out as the other factions. The preview warns about armies and towns that already hold it (they keep it) and about a unit that no building level of the faction recruits. The **Units & armies** and **Buildings** tabs offer what the faction will have.

**Unit and building editors - lines:** **Add line...** puts a line in its place: in a building level a recruit line (unit, experience, factions and more conditions; factions that do not own the unit yet get it and its cards), a capability (bonus; the keys the mod uses, with an example value), an upgrade, or another line of the level - a `capability` / `upgrades` block is made when the level has none. In a unit, any key the mod's units use. **x** removes a line, except the ones every unit or level of the mod has. **Tied to it** shows who owns and recruits a unit (or may build each level), what requires a chain, and how many armies or towns hold it at the start. A change drags along what is tied to it: a unit's new `type` reaches its recruit lines, the armies of every campaign, the mercenary pools and the rebels; a new `dictionary` copies its texts and cards; factions added to `ownership` get the cards; a chain's new name reaches the towns and the requirements. A line naming a unit or building the mod has not is refused.

**The mod is remembered:** the last mod and the campaign picked in it load at the next start; **Mod** at the top lists every mod of the game folder (the game itself, `bi`, `alexander`, HLR, the mods made with **New mod folder...**, Medieval II's `mods/...`).

**Diplomacy:** the **Diplomacy** tab lists every faction with four values: how they feel about the edited (or new) faction and how it feels about them (`core_attitudes`), and where they start with each other (`faction_relationships`). Lower is better: -10 own (the Roman houses), 90-100 friends, 310 wary, 410 dislike, 600 enemies (everyone towards the rebels); neutral = no line. Pick a value or type a number; changed cells get a blue frame. Only the lines naming the faction are rewritten. The **Diplomacy** switch on the **Map** colours every owner by how the faction feels about it (green friends, yellow wary, orange dislike, red enemies). These files have no lines for alliances or wars at the start.

**Check mod:** reads every file the tool uses and reports what it found (factions, cultures, units, buildings, regions, towns, ports, characters, diplomacy) and anything it cannot make sense of - a settlement without a region, a unit an army names but the unit file lacks, a character after a family tree. The deep check also rehearses, in memory, an edit and a new faction for every faction and checks the result the way the game reads it (minutes on a big mod). Nothing is written.

**Undo, keys, help:** **Undo** / **Redo** (Ctrl+Z, Ctrl+Y or Ctrl+Shift+Z) step back through towns picked, garrisons, buildings, settlement sizes, map moves, armies and diplomacy. Ctrl+P preview, Ctrl+S apply, F5 load again, Ctrl+1..5 the tabs, F1 or **Help** for a short guide. Far out on the map only towns are drawn; ports and characters show from zoom 4.

**Log:** the tool keeps `faction_tool.log` in `RTW-M2TW-Campaign-Editor-files\logs` next to the exe, together with the logs zips (or in `%APPDATA%\RTW Faction Tool\logs`): what was loaded, previewed and written, and every error with its details. The **Log** button shows it; send it along with the game's `system.log.txt` when something goes wrong.

**Undo:** press **Restore a backup...** Backups sit in `faction_tool_backups` next to `data`. Pick the write to go back to: it and every later one are undone in one go.

## What it changes

| File | Change |
|---|---|
| `descr_sm_factions.txt` / `.json` | Copies the template block (colours optional), inserted before `slave` |
| `descr_character.txt` | Copies the template's block under every character type |
| `descr_names.txt` | Copies the template's name lists, so every name already has a string |
| `export_descr_unit.txt` | Adds the faction to every `ownership` line that has the template |
| `export_descr_buildings.txt` | Adds the faction to every `factions { }` list that has the template |
| `descr_model_battle.txt`, `descr_model_strat.txt` | Copies the template's `texture` lines |
| `descr_banners.txt`, `descr_lbc_db.txt`, `descr_offmap_models.txt`, `descr_building_battle.txt` | Copies the template's entries |
| `export_descr_character_traits.txt`, `export_descr_ancillaries.txt` | Copies every trigger that tests `FactionType <template>` (optional) |
| `data/text/*.txt` | Copies every string whose key names the template (`{PARTHIA}`, `{EMT_PARTHIA_SPY}`, ...) and rewrites the name. The **tooltip** goes to `{<FACTION>_DESCR}` (over the faction icon), the **full description** to `{<CAMPAIGN>_<FACTION>_DESCR}` in `campaign_descriptions.txt` (the campaign screen) |
| `descr_strat.txt` | Adds the playable/nonplayable entry, a new faction block, the diplomacy lines and the leader and heir, and moves the chosen towns (details below) |
| `descr_win_conditions.txt` | Copies the template's conditions; edit them by hand afterwards |
| Art | Copies files and folders named after the template under `data/ui`, `data/menu`, `data/loading_screen` and the campaign folder (`map_parthia.tga` becomes `map_saba.tga`, `ui/units/parthia/` becomes `ui/units/saba/`); a folder left from an earlier attempt is filled in file by file (optional) |
| Unit cards | For every unit the faction owns, checks `ui/units/<faction>/#<dictionary>.tga` and `ui/unit_info/<faction>/<dictionary>_info.tga` and copies a missing one from the template (or any faction that has it) |

How the chosen towns are moved in `descr_strat.txt`:

- The whole `settlement { }` block moves, so no region ends up with two settlements.
- A settlement holds **one army** at the start. The leader holds the capital; the heir holds the second chosen town, or stands next to the capital when there is only one.
- **Leader's army** `balanced` (default): sized like the leader armies of factions with about as many towns (median size and upkeep), from the template's bodyguard and the cheapest units of its own starting armies. `template` copies the template leader's army, `bodyguard` gives the bodyguard alone.
- **Old garrisons** `replace` (default): the capital's old garrison leaves; in other towns its captain stays with the template's cheapest units. `keep` folds the old units into the new armies instead.
- A general or agent of the previous owner is moved to one of that owner's other towns, or next to it when that town already has an army.
- "Next to" is the flattest free tile of the town's region within 4 tiles: no river, ford or cliff (`map_features.tga`), no sea or mountain (`map_ground_types.tga`), a height range inside the tile of at most 25 (`map_heights.tga`).

After building, the tool checks:

- the braces balance in `descr_strat.txt`;
- every region has exactly one settlement;
- every unit in the new armies exists in `export_descr_unit.txt`;
- how many factions there are now.

## Command line

```
python rtw_faction_tool.py list    --data PATH          # factions, campaigns, backups
python rtw_faction_tool.py towns   --data PATH --owner slave
python rtw_faction_tool.py names   --data PATH parthia  # names a leader may use
python rtw_faction_tool.py example > saba.json          # a config to edit
python rtw_faction_tool.py new saba.json --data PATH    # preview
python rtw_faction_tool.py new saba.json --data PATH --apply
python rtw_faction_tool.py restore --data PATH
python rtw_faction_tool.py scan gaetulii --data PATH    # every mention of a faction in the whole mod
python rtw_faction_tool.py newmod HLR_Saba --data PATH  # a separate mod folder built on PATH's mod
python rtw_faction_tool.py slim --data NEWMOD\data        # plain-game mods: keep only the changed files
```

**Scan mod** (button or `scan`) reads every text file of the mod (not only `data`) and lists where the faction is named: places the tool does **not** handle (check these by hand), places it does, files and folders named after the faction, and files the faction's models, textures and unit cards point at that do not exist. It tells every file apart - the game's own (unchanged), changed by the mod, REX's, or the mod's own - from the game manifests that come inside the tool (a manifest made on your PC with **Game manifest...** wins). It writes nothing. Folders and files you want it to skip go in `faction_tool_ignore.txt` next to `data` (button **Ignore list...** in the scan window; one rule per line: `folder/`, `name/` for that folder name anywhere, or a mask like `*.bak`). The list only affects the scan.

The Windows `.exe` is the window only. Use Python for the command line.

## Known limits

- **Faction count.** The game stops at a set number of factions, `slave` included: plain Rome 21, Medieval II 31. REX reads it from `max_factions` in `data/descr_ex.txt` (REX ships 21; a mod can raise it in its own `descr_ex.txt`); over it the game closes at start ("Too many factions described here, maximum is(21)"). HLR ships 31 factions. Check the limit before adding one.
- **Banner and logo.** The new faction gets banner textures and a loading-screen logo of its own (copies of the template's, under its name - replace them on the **Art** tab), but still shares the template's `standard_index` (the strat-map flag symbol), sprite logos and strat symbol model. Those are future work (REX's `--ui-pack` sprite packer makes new logos possible).
- **Strings.** Copied strings keep the template's text apart from the names ("the wicked Seleucids..."). Edit them in `data/text` if you care.
- **Character names.** Names must come from the template's lists. Adding new names means editing `descr_names.txt` and the names string table by hand.
- **Other campaigns.** One campaign is edited per run. Run again for another campaign; the faction files see the faction already exists and refuse, so add those campaigns by hand for now.

## Code signing policy

Windows release builds are to be signed through the SignPath Foundation (application pending; until then the exe is unsigned):
free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

- Only builds made by this repository's GitHub Actions release workflow from its own source are signed.
- Committers and reviewers: [MasterOogwayHomebrew](https://github.com/MasterOogwayHomebrew). Approver (every signing request): [MasterOogwayHomebrew](https://github.com/MasterOogwayHomebrew).

Privacy: this program will not transfer any information to other networked systems. It reads and writes only the game or mod folder you load and its own `RTW-M2TW-Campaign-Editor-files` folder (see [SECURITY.md](SECURITY.md)).

## License

Copyright (C) 2026 Pfadfinder (Adam) - [MasterOogwayHomebrew](https://github.com/MasterOogwayHomebrew), the author of
RTW & M2TW Campaign Editor.

GNU General Public License v3.0 ([LICENSE](LICENSE)). You may use, study, change and share the editor. If you share
it or a program built from its code, that program must stay under GPL-3.0 with its source open, and must keep the
copyright notice above and say it is based on this project. Releases up to 0.17.1 were published under the MIT
license.

## Support

The editor is free and stays free. It is built with the help of AI, which costs money every month; if the tool saves you time, a coffee on [Ko-fi](https://ko-fi.com/pfadfinder) keeps new features coming. Thank you!

**Changes waiting for Apply:** a `*` on **Edit faction**, **Unit editor** or **Building editor** marks work not written yet. When more than one holds changes, **Apply changes** lists them with ticks and writes them one after another (the editors first, then the faction and the map), each with its own backup; **Preview** shows them all. Picking another faction in Edit with changes not written asks: apply them, drop them, or stay.

**Look:** **Dark / Light** at the right of the work bar (kept for the next start). The Map's **Layers** menu also draws the ground tile by tile (one square = one tile, the ground at its middle - what the tool checks), relief from `map_heights`, rivers, fords and cliffs from `map_features`, and a tile grid when zoomed in. The Unit and Building editors' lists filter (**Show**: a faction, a culture, a category or class, mercenaries apart; building chains by who may build them, their kind, recruiting or not) and sort.
