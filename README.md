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
| `data/text/*.txt` | Copies every string whose key names the template (`{PARTHIA}`, `{EMT_PARTHIA_SPY}`, ...) and rewrites the name |
| `descr_strat.txt` | Adds the playable/nonplayable entry, a new faction block, the diplomacy lines and the leader and heir, and moves the chosen towns (details below) |
| `descr_win_conditions.txt` | Copies the template's conditions; edit them by hand afterwards |
| Art | Copies files and folders named after the template under `data/ui`, `data/menu`, `data/loading_screen` and the campaign folder (`map_parthia.tga` becomes `map_saba.tga`, `ui/units/parthia/` becomes `ui/units/saba/`) (optional) |

How the chosen towns are moved in `descr_strat.txt`:

- The whole `settlement { }` block moves, so no region ends up with two settlements.
- A rebel garrison standing in the town joins the new faction, and its `sub_faction` is removed.
- A general or agent of the previous owner is moved to one of that owner's other towns (towns are located through `map_regions.tga`).

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
```

The Windows `.exe` is the window only. Use Python for the command line.

## Known limits

- **Faction count.** HLR ships 31 factions including `slave`. With the tool's new one that makes 32, which ran fine under REX in our tests. Check before adding more.
- **Banner and logo.** The new faction shares the template's `standard_index`, logos and strat symbol. A unique banner is future work (REX's `--ui-pack` sprite packer makes new logos possible).
- **Strings.** Copied strings keep the template's text apart from the names ("the wicked Seleucids..."). Edit them in `data/text` if you care.
- **Character names.** Names must come from the template's lists. Adding new names means editing `descr_names.txt` and the names string table by hand.
- **Other campaigns.** One campaign is edited per run. Run again for another campaign; the faction files see the faction already exists and refuse, so add those campaigns by hand for now.

## License

MIT
