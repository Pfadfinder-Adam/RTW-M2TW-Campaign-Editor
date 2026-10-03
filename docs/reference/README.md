# Reference data

- `rtw_gold_steam_manifest.json.gz` - every file of a clean *Rome: Total War Gold*
  (Steam, English) install: `{"files": {path: [size, md5]}}`, made with the
  tool's **Game manifest...** (`python campaign_editor.py manifest <game folder>`).
  30,341 files, 3.2 GB, plus the `bi` expansion (`bi/...`, 11,915 files; the one
  file there identical to REX's `bi` overlay is left out, so it counts as REX's).
- `rex_manifest.json.gz` - the same for the unpacked REX download (REX.zip,
  2026-09): 626 files. Against the vanilla manifest: 571 new
  (REX.exe and dlls, `script/`, `miles/`, `tools/`, a `bi/` and `alexander/` data
  overlay, extra `data/`), 50 replacing a vanilla file (descr_sm_factions.txt,
  descr_engines, effects, fonts, `menu/Rome.lnt`, aerial map ground textures...),
  5 byte-identical to vanilla. A file in the game folder that matches this
  manifest is REX's; vanilla's original of a replaced one is in the game manifest.

- `engine_catalogue.json.gz` - what REX and M2EX offer a script, from the documentation the engines write
  themselves (console command `dump_docudemon`, builds of 2026-10-03): every console command, campaign-script
  command, condition and event of each engine with its parameters, a sample line, where it works, what a condition
  needs from the event and what an event brings (`{"rex"|"m2ex": {kind: [[name, params, sample, where, needs,
  implemented]]}}`). No descriptions: the Module builder reads those from the game's own `documentation` folder.
  Made with `campaign_editor.enginedocs.write_catalogue(rex_docs, m2ex_docs, path)`.

No game files are kept here: the repository is public.
