# RTW Faction Tool

Add a new faction to a **Rome: Total War** mod in a few clicks: pick an existing faction as the template, name the new one, choose its starting towns and leader. The tool edits every data file that needs it, makes a backup first, and can undo the whole change.

Built and tested on **Barbarian Empires REX Ultimate Edition 1.0.6** (folder `HLR`) running on REX. It reads the mod's own files and doesn't assume their contents, so other RTW / BI-format mods should work too. Reports are welcome.

## Download

- **Windows:** grab `RTW-Faction-Tool.exe` from the [Releases](../../releases) page. No install needed.
- **Any OS with Python 3.8+:** `python rtw_faction_tool.py` (standard library only).

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

**A separate mod (recommended):** press **New mod folder...** after loading the mod you build on (for example `HLR\data`). The tool makes `<game>\HLR_Saba\` next to it and loads it; the faction goes there, and `Start_HLR_Saba.bat` (your base mod's start script with `-mod:HLR_Saba`) starts it. The base is never touched. The game reads one `-mod:` folder and falls back to the game's own `data`, so a mod built on HLR holds all of HLR: text files are copied, everything else is a hard link (the same file on disk under a second name - no extra space, same drive only). Don't overwrite a linked texture in place from an image editor, or tick **Copy every file**. A mod built on the plain game can be slimmed to the changed files afterwards (`slim` on the command line).

**Garrisons by hand:** the **Units & armies** tab lists your chosen towns (or select one in **Chosen** and press **Garrison...**); pick a town and fill its garrison: the template's units as the game's own cards (upkeep under each, the full line on hover), click to add, click the garrison to take one out, **Suggest** for the balanced pick, **Automatic** to leave the town to the 'Leader's army' / 'Old garrisons' rules on the same tab. The leader's or heir's bodyguard comes on top in the towns they hold; elsewhere the old garrison's captain (or a new one from the name list) leads it. Pictures need Pillow (`pip install pillow`; the exe has it).

**Buildings by hand:** the **Buildings** tab shows, for the selected town, every building chain the faction may build (from `export_descr_buildings.txt`: the level's `requires factions { }` names the template, the new faction or its culture) with the game's picture of the chosen level (`ui/<culture>/buildings/#<culture>_<level>.tga`, falling back through `descr_ui_buildings.txt`'s culture variants and the plain level name). Pick a level per chain or `-` for none; levels too big for the settlement are hidden unless you ask. Untouched towns keep their own buildings; **Keep the town's own** undoes your picks. The preview warns about a level the faction list or the settlement size does not allow.

**Edit an existing faction:** switch **Edit faction** at the top and pick the faction. The window fills with what it is now (names, tooltip and campaign-screen text, colours, AI, denari, playable, its towns). Change what you want; **Units & armies** replaces the garrison of any of its towns (a named character there keeps his bodyguard; a town nobody holds gets a captain), **Buildings** sets what stands in them. Add towns to **Chosen** to take them (their rebels leave; another owner's characters go to its other towns), take towns out to give them to the faction named in **Removed towns go to** (rebels by default; the faction's named characters move to one of its towns, a captain and his garrison go with the town). **Capital** puts that town first in the faction's block. Leader and heir can get new names (from the faction's name list) and ages. Untouched fields and towns stay as they are. **Preview changes**, then **Apply changes** - with a backup, like a new faction. Names and texts change only in the chosen campaign's string tables.

**Map:** the **Map** tab shows the campaign map like a full-window minimap drawn tile by tile from `map_ground_types.tga` (the ground type of each tile: grass, forest, hills, mountains, desert, sea), cities, ports (the white pixels of `map_regions.tga`) and, with **Political**, each region in its owner's colour, see-through, with the towns you picked already in the new or edited faction's colour. Wheel zooms, dragging moves, a click on a town adds it to **Chosen** or takes it out; the line under the map describes the tile under the mouse (region, owner, ground, and whether an army may stand there). **Characters** shows everyone in `descr_strat.txt`: armies as flags in the faction's colour, agents as lettered dots (S spy, D diplomat, A assassin, M merchant), admirals as boats. In **Edit** the edited faction's characters are framed in yellow and can be dragged: the target tile turns green or red (an army needs a tile it may stand on or a town no other army holds, a fleet needs sea, agents any land), and the moves are written with **Apply changes**.

**New armies, agents and fleets:** on **Units & armies**, **+ Army**, **+ Agent** (spy, assassin or diplomat) and **+ Fleet** add a new character with a name from the faction's name list. Select it: an army gets its units from the land cards, a fleet from the ships (in mods that mark every ship a mercenary the mercenaries filter turns on by itself). **Place on map** opens the **Map**; click a tile: an army needs land it may stand on or a town no other army holds, a fleet needs sea, an agent any land or a town. Placed ones can be dragged there. Works for a new faction and in **Edit**; written with **Create faction** / **Apply changes**.

**Log:** the tool keeps `faction_tool.log` next to the exe (or in `%APPDATA%\RTW Faction Tool`): what was loaded, previewed and written, and every error with its details. The **Log** button shows it; send it along with the game's `system.log.txt` when something goes wrong.

**Undo:** press **Restore a backup...** Backups sit in `faction_tool_backups` next to `data`. Restore the newest one first.

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

**Scan mod** (button or `scan`) reads every text file of the mod (not only `data`) and lists where the faction is named: places the tool does **not** handle (check these by hand), places it does, files and folders named after the faction, and files the faction's models, textures and unit cards point at that do not exist. It writes nothing. Folders and files you want it to skip go in `faction_tool_ignore.txt` next to `data` (button **Ignore list...** in the scan window; one rule per line: `folder/`, `name/` for that folder name anywhere, or a mask like `*.bak`). The list only affects the scan.

The Windows `.exe` is the window only. Use Python for the command line.

## Known limits

- **Faction count.** HLR ships 31 factions including `slave`. With the tool's new one that makes 32, which ran fine under REX in our tests. Check before adding more.
- **Banner and logo.** The new faction shares the template's `standard_index`, logos and strat symbol. A unique banner is future work (REX's `--ui-pack` sprite packer makes new logos possible).
- **Strings.** Copied strings keep the template's text apart from the names ("the wicked Seleucids..."). Edit them in `data/text` if you care.
- **Character names.** Names must come from the template's lists. Adding new names means editing `descr_names.txt` and the names string table by hand.
- **Other campaigns.** One campaign is edited per run. Run again for another campaign; the faction files see the faction already exists and refuse, so add those campaigns by hand for now.

## License

MIT
