# Reference data

- `rtw_gold_steam_manifest.json.gz` - every file of a clean *Rome: Total War Gold*
  (Steam, English) install: `{"files": {path: [size, md5]}}`, made with the
  tool's **Game manifest...** (`python rtw_faction_tool.py manifest <game folder>`).
  30,341 files, 3.2 GB. The `bi` expansion was left out of this first run
  (it has its own `data` folder and was taken for a mod); rerun to include it.
- `rex_manifest.json.gz` - the same for the unpacked REX download (REX.zip as the
  user installed it, 2026-09): 626 files. Against the vanilla manifest: 571 new
  (REX.exe and dlls, `script/`, `miles/`, `tools/`, a `bi/` and `alexander/` data
  overlay, extra `data/`), 50 replacing a vanilla file (descr_sm_factions.txt,
  descr_engines, effects, fonts, `menu/Rome.lnt`, aerial map ground textures...),
  5 byte-identical to vanilla. A file in the game folder that matches this
  manifest is REX's; vanilla's original of a replaced one is in the game manifest.

No game files are kept here: the repository is public.
