# Reference data

- `rtw_gold_steam_manifest.json.gz` - every file of a clean *Rome: Total War Gold*
  (Steam, English) install: `{"files": {path: [size, md5]}}`, made with the
  tool's **Game manifest...** (`python rtw_faction_tool.py manifest <game folder>`).
  30,341 files, 3.2 GB. The `bi` expansion was left out of this first run
  (it has its own `data` folder and was taken for a mod); rerun to include it.

No game files are kept here: the repository is public.
