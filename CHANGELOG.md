# Changelog

## Unreleased

### Changed
- **Factions that appear later** (a tester, REX): a new faction can come into the campaign later instead of starting
  on the map - *by an event* (a date and a region: `emergent_faction` in `descr_events.txt`), *as the shadow of a
  faction* (the side that splits off it in a civil war: `shadowing` / `shadowed_by`) or *splitting off a faction in a
  revolt* (`spawned_by` / `spawns_on_revolt`) - New faction > *Comes into the campaign*. It starts dead
  (`dead_until_resurrected`, optionally `re_emergent` - may come back after it dies), with no towns or characters,
  nonplayable. **Tools > Events and later factions** now lists every such faction and changes how one comes in.
  **Check mod files** finds a shadow / split-off pair written on one side only, an emergence event for a faction
  that is not dead at the start, and a dead faction holding towns. A clone of such a faction (Ostrogoths, the
  empires' rebels) starts plain and alive. Both games (Barbarian Invasion, REX and Medieval II read these words).
- **A town straight from the Map** (a tester): a double click on a town (or the right click's *Edit this town...*)
  opens its owner in Edit faction with the town picked on the Buildings tab - level, population, city or castle,
  buildings.
- **Many towns made city / castle and of another level at once** (a tester): a third tab in *Buildings and garrisons
  for many towns* (also on the Map's Pick towns menu) - city <-> castle with the buildings converted the game's way
  (Medieval II), a new level with its governor's building and population; towns of any owner, a backup first.
- **REX / M2EX: no faction limit** (the author: they have none) - every new faction raises `max_factions` in the
  mod's own `descr_ex.txt` by itself, written with the faction (Preview says so), no question asked; the status line
  no longer says "Full" under an engine. Only the original exes still stop at 21 / 31.
- **A town on its region's edge stays its region's** (a tester's Erebor, Divide and Conquer): a town pixel that
  touches a neighbour's land more than its own went to the neighbour - the town was not drawn, and the bigger map
  painted its block in the neighbour's colour. Now every region keeps one town, the surest pixels given first (the
  same on the Map and in the bigger map; vanilla maps unchanged).
- **Rome in 3D put together right** (a tester): the parts that hang on a bone - weapons, shields, helmet crests, the
  pieces of a ballista, onager or ram - were placed by numbers that are no place in the model, so crests floated
  off helmets, spears lay on the ground and engines fell apart; now each sits on its bone. The **T pose** (arms out)
  is the default for every Rome model, **Pose** shows it as the file stands. A **chariot** unit stands on its chariot
  with its horses and crew where `descr_mount.txt` puts them; a **siege engine** unit shows its engine
  (`descr_engines.txt`) whole, with its texture (a model's texture is looked for beside it - `models_engine` too).
  Checked on all 948 vanilla Rome unit, mount and engine models (the 52 the reader does not know yet are the same as
  before: ladders, towers, some engine variants).
- **Land and sea: new land rises from the shore** (a tester: a new coast flickered in the game) - it was all set at
  the shore's height and lay flat on the water; now it climbs inland as both games' own coasts do (measured on the
  vanilla maps: 2, 8, 12, 14, then 16 grey steps from the sea), also where land is painted tile by tile.
- **The Unit and Building editors no longer lag** (a tester): a big building (Medieval II barracks, 316 lines) took
  2.3 s to show after every pick or added line - now 0.02 s: the block's lines are made only when unfolded, and the
  look's colours are worked out once instead of 50 000 times per window.
- **A faction without name lists no longer stops Apply** (found in a tester's log: "no name in empire_east's name
  list for a captain", a faction brought from Barbarian Invasion): it gets a copy of its culture's kin's name lists in
  `descr_names.txt` (said in the preview), so its captains and new characters can be named.
- **Events: the picture players see and what the event does** (a tester) - the scroll's picture (a historic event
  its own `ui/<culture>/eventpics/<event>.tga`, a plague / volcano / earthquake its kind's `disaster_<kind>.tga`),
  **Picture...** puts your own in for every culture at the game's size, and each kind says in plain words what it
  does (a plague spreads from the nearest town, a volcano or earthquake damages buildings and kills people...).
- **Campaign rules: the REX / M2EX engine settings** (a tester: on Rome the window was nearly empty) -
  `descr_ex.txt` (ages and the family, bribery, hordes, camera, max factions, battle visuals...) and `descr_caps_ex.txt`
  (feature switches: recruitment slots per town, sprite format, trade fleets...), grouped by the file's own headings,
  each value explained by the comment the engine writes above it; written into the mod's own copy.
- **One temple per town, as the games want** (both games: a chain named `temple_...`; two in one town stop the game
  with "Settlement specified with multiple temple buildings"): the Buildings tab swaps the old temple for the new
  pick, Buildings for many towns skips a town that has another temple, Check mod files names a town holding two.
- **Terrain editor: impassable land and impassable sea brushes** (a tester: the Medieval II map is full of them) -
  Medieval II always; Rome only with REX (REX knows these ground types, the original exe does not; not yet tried in
  the game on Rome). Refused under towns, ports and characters like mountains.
- **Land and sea: new land stands in shallows** (a tester): the 8 sea tiles round a tile made land turn shallow sea
  in the ground where they were deeper (ocean / deep sea).
- **Map: what you place rides under the mouse** (a tester: only a white square showed) - a resource, fort,
  watchtower, wonder or agent shows its own sign, framed green where it may go and red where not.
- **Map: unticking Pick towns unpicks every town** (a tester) - the same rule everywhere: switching Edit resources
  or Edit regions off drops what was picked or waiting for a click, hiding the legend puts its picked tool down.
- **Map: no "Edit forts, towers & wonders" switch any more** - forts, watchtowers and wonders are always moved with
  the right drag, placed from the legend (a wonder: right click, Put a wonder here) and deleted with the right click;
  their battlements keep the owner's colour.
- **Map: resource letters readable on every colour** - black on bright colours, white on dark ones.
- **Map: the map's size stands under the map, bottom left** (a tester: over the map it seemed to float).
- **Wonders on the Map (Rome)**: a double click on a wonder (or the right click's "about it") opens its window as the
  game shows it - picture, title, what it does, short and long description - with **View it in 3D** (its campaign-map
  model); the right click on free land has **Put a wonder here** (one of the game's seven - the game knows no
  others). Written on Apply like the other map changes.
- **Traits and retinue: a right click on Effects lists every bonus the game knows** (a tester: nobody knows them all
  by heart) - grouped, each in plain words, both games (the lists come from the games' own exes); a pick is added
  after a comma with the value 1.
- **Map: Delete from the map on the right-click menu** (a tester: things could be added but not taken away): a
  resource, fort, watchtower or wonder, or a character of any faction with his army - gone from descr_strat.txt with
  the next Apply, nothing left behind; the leader, the heir and members of the family tree are refused in plain
  words.
- **The old "Faction Tool" name is gone** (the author's wish): the code is the `campaign_editor` package, started
  from source with `python campaign_editor.py`; the files it makes beside a mod are `CampaignEditor_ignore.txt` and
  `CampaignEditor_mod.json`. Put over an older version, nothing breaks or is lost: its settings and log are moved in
  (also the settings an older version kept in APPDATA), its ignore list and mod mark are read and take today's names
  the next time they are written, its backups (`faction_tool_backups`) stay listed and restorable.
- **README**: the important things first - download, wiki, roadmap, changelog, what to do when something goes wrong,
  why support it - then what the editor does.
- **Recolour leaves the white banner a fleeing unit shows and the rebels' banner alone** (found in a tester's log: it
  made the faction its own recoloured copy of standard_routing / standard_slave).
- **Add-ons go where REX loads them** (a tester's HLR report): into the game's `script/modules` - a mod with a script
  plugin of its own (manifest.nut + main.nut, as HLR has) loads no modules from its own folder, so an add-on put
  there never ran. An add-on whose code is already pasted into the mod's own scripts is refused (it would run
  twice).
- **New add-on: Player Diplomacy** (Rome + REX): truces that hold, client kingdoms that never invade you, far weaker
  factions that keep away; settings for each (add-on settings may now be numbers like 3.0).
- **Victory: many regions or factions at once** (a tester: one by one is too many clicks): drag over rows, Shift-click
  a run, Tick all shown, tick every region a faction holds, or pick the towns **On the map...** (their regions yellow).
- **Map: a sign grows as the mouse comes near it**, softly, from further away when zoomed out (a tester's wish).
- **A new man tied to no family is no error**: Apply puts him on the map as a general of the faction (with a
  bodyguard, in its first town); only a new woman tied to no one stays a record (Preview says so).
- **People and family: one button, Add a person...** (testers: a person made from nothing; four buttons for one job) -
  step by step: who the new person is to whom (son, daughter, wife, husband, brother, sister, parents, uncle, aunt,
  or the head of a new family tied to no one), then the name, or someone already in the faction; Preview warns while
  a new person is on no tree. On the Faction tab the tree now stands on the right of the list and the person (it was
  on top, too cramped - a tester).
- **Character panel: a click on the pips sets the attribute** (a tester's wish): the traits are fitted to it - his own
  trait moved to the level that fits, else a trait giving that attribute alone added; both games.
- **Traits and retinue window: the labels whole** ("Points it needs (Threshold)" was cut) and the descriptions in the
  window's own font (a tester's report).
- **Building editor: the texts players read** (a tester: the description tied to a culture was missing): the level's
  name, short description and description for each culture or faction, shown under the pictures and changed there;
  written to export_buildings.txt on Apply.
- **Unit and Building editors: the list's width can be dragged** (a tester's report), the line's grip drawn in the
  text's colour so it shows on either look; the width is kept.
- **Faction emblem: fitted by hand before it is made into every picture** (found by a tester: the emblem needed an
  editor of its own to fit a picture into the round icons): move, size, turn, cut to the old emblem's own shape (or
  a circle, a square), a ground in the faction's colours, a magic wand that clears an area of like colour, a paint
  bucket (emblem_edit.py, gui_emblem.EmblemFitter).
- **Faction emblem: the new symbol on the battle banners and the campaign map's flag (Rome)** (a tester's wish: the
  symbol on every 3D flag, not only the icons): the faction's battle banners are made from the game's own blank
  white banner (standard_routing - Roman, barbarian or eastern, any of the three for any faction, whatever its culture), its cloth
  dyed in the faction's colour and the symbol painted on it with the cloth's folds; the allies' banner the same with
  the symbol faint; the flag symbol gets the bare symbol. **Banner...** picks another blank banner, a pattern of up
  to three colours (plain, tricolours upright / across / slanting, quarters, crosses, a border...), the symbol on or
  off, and moves the symbol (banners.py, gui_banners.BannerWindow). The game's blank banner itself (a fleeing unit's)
  is only read, never changed.
- **Faction emblem: a plain background goes at once** (a tester: a white square showed on the banners): a picture
  whose four corners are one solid colour has that background cleared when it opens; Start over brings it back.
- **Edit region... holds both names** (a tester: three buttons on the Map's region bar did one job): for a region of
  the map it now has the names in the files of the region and its town beside the names players see; a change of
  the file names is written at once in every file that names them, with a backup (asked first). The Map's
  **Rename...** and **Rename in the files...** buttons are gone (the Settlements tab keeps its own).

- **Every window opens in the middle of the screen**; a hover text stays inside the screen; a drop-down list is as
  wide as its longest line; a field whose text is longer than the box shows it whole when the mouse rests on it; the
  '?' marks are light blue in the Dark look (they were dark blue on dark grey) - from a tester's reports.
- **The Faction tab in two columns**: the short fields keep a fitting width, Leader and heir and Victory stand beside
  them, the tooltip and the description below across the whole width.
- **Bring from another mod and New unit / building step by step show what is picked as the game shows it**: the
  pictures (a building's in the town and when built, for a culture you pick), the name and description players read
  and what it does in plain words ("public order from happiness +15%", "trains roman hastati") - not the file's code.
- **Bring units: one line per unit for where it is trained** - the same buildings as in the other mod, any level of
  this mod, or nowhere; only the units come over, never a building.
- **New building step by step: two pictures per level** (in the town and when built), shown as they are and as
  chosen; the texts step says plainly that only names and texts are written there, with what each level does beside
  it.
- **Check mod files** finds building lines naming a hidden resource, resource or religion the mod lacks.
- **Map: armies, fleets, agents and towns for any faction, no faction to pick first** (the user's wish): a click
  with the legend's army / fleet / agent tool (or a right click: New army / agent / fleet here) asks for the name,
  the faction set to the one holding that land (a fleet: the owner of the nearest land) and changeable there; a
  right click on a town: **Give this town to** any faction. The faction being made or edited gets them as before;
  any other faction's are written with the next Apply (edit.map_changes; edit.move_towns is now the one writer of
  towns changing hands), an army or fleet starting with the first unit of that faction's nearest one.
- **Map: a port from the legend** - click a coastal land tile and the port of the region there goes to it; a region
  without a port gets one (the port belongs to the region most of the land round it is, else refused).
- **Map: Pick towns shows the picked towns' regions in yellow**; every named character is drawn as a general's flag
  (as in the game - the separate family-member sign meant nothing there); painting on the map shows the painted
  tiles solid with a thin yellow edge while the brush moves (a see-through fill was invisible on a like colour and
  shimmered on the coast).
- **The bigger map's write buttons say what they do**: "Write it - hills 3 x higher" / "Write it - heights as they
  are (flatter)".
- **Report a bug: paste a screenshot with Ctrl+V** (or the Paste button) - no file to save first.
- **Unit and Building editors: the block's lines fold away** behind **Every line of the block** (like the family
  tree), so the pictures, the battle model and the voice have the room; Add line... opens them.

### Fixed
- **Recolour keeps a bright colour of its own** (found by a tester: an emblem's gold wolf and laurel on red turned
  red): the edge growth past the colour test takes only a dull or dark rim, never a clean bright colour next to it.
- **Recolour makes its 'to' colours the faction's own too** (found by a tester: after a recolour the faction's
  primary and secondary colours were still the old ones): a box, ticked, writes them into descr_sm_factions.txt
  (and REX's .json) with the pictures - one shared writer with the Faction tab (edit.set_faction_colours).
- **Recolour's pictures fit the screen** (found by a tester: the 'after' picture ran past the window's edge).
- **Units and buildings brought from another mod no longer stop the game at start** (a tester brought Barbarian
  Invasion's british legionaries into Rome; REX: "Hidden resource condition, unrecognised hidden resource
  'britain'"): conditions naming a hidden resource or a resource this mod does not have are taken out of the
  recruit and requires lines, and a `religious_belief` line for a religion the game has not is left out - said in
  Preview.
- **New forts and watchtowers on a campaign that has none** (vanilla Rome and Medieval II): they were refused
  ("no line to copy"); now written under their region in the regions section at the end of descr_strat.txt, the form
  both games' exes read there (Barbarian Invasion's watchtowers use it; a Medieval II fort as `wooden_fort` with the
  owner's culture). A region without a town is refused, as the game does.
- **Roster: a double click right after Apply** no longer shows "'NoneType' object is not subscriptable" (the tab
  reads the changed files again first).

## 0.29.2 - 2026-10-02

### Added
- **The editor offers to put itself into the game's folder** (where it finds the game and every mod by itself):
  started from elsewhere (the Downloads folder, the desktop), the first start of each new version asks; the user
  picks the game's folder (checked: the game's exe must lie there), the exe is copied there with its settings and
  add-ons (an older copy of the editor there is replaced), a desktop shortcut is made if wanted (Windows), and it
  starts from there. 'Not now' asks with the next version, 'Don't ask again' never; Settings > Folders has the button.

### Fixed
- **The bigger map (x3) keeps the rules of the games' own maps** (five reports from Divide and Conquer, all of them
  measured on vanilla Medieval II too - 66 of 77 ports there had no water beside them): a town in a region
  descr_regions does not list stays one town pixel with its land round it (Erebor became nine); every port stands on
  a coastal land tile touching the sea and its region; map_regions and the heights share one coast (7024 tiles
  disagreed); every new tile keeps the ground type and climate of the old tile it lies in (Mirkwood's forest turned
  to wilderness - 8 of 9 new tiles took the old picture's in-between points); land bridges stay unbroken chains from
  land to land (they were left as dots on the water).
- **A file the system refuses no longer leaves a mod half written** (reports from a Medieval II mod: "[WinError 5]
  Access denied" on descr_sounds_accents.txt while making a faction): Apply is all or nothing - when one file cannot
  be written, the files written before it are put back, the copies removed, no temp file stays, and the message says
  in plain words what to close or change. A file marked read-only (Windows' Read-only box) is named in Preview and
  written (the mark is taken off); a file another program holds for a moment is tried again.
- **A new faction gets its faction-select buttons and the rest of its template's pictures** (a tester: new
  factions made from greek_cities showed no buttons on the campaign's faction-select screen): (1) a template whose
  name holds `_` (greek_cities, romans_julii, papal_states) never had its loose pictures copied - symbol24 /
  symbol48 buttons, the loading-screen symbol, the campaign-select map; (2) a mod that keeps the game's own pictures
  (its folder holds only what it changed - common for REX and Medieval II mods) now gets copies of the template's
  pictures, unit cards and banners from the game's data, written into the mod (the game's data is never touched).
- **A battle_models.modeldb with models after its count is read** (a tester: "modeldb: 1585 characters left after
  872 models" stopped a new faction): models added by hand while the count at the top stayed as it was are kept
  exactly as they are, and Preview / Check mod say which ones the game never reads and which count would read them.
- **New regions on a big map get a colour** (a tester: "no free colour left"): the colour search walked only 200
  colours over and over; it now walks millions, so a map with hundreds of regions still gets new ones.
- **Recolour window: a touch-up stroke after the colours were changed** no longer raises an error.
- **Changes waiting for Apply are never written into another mod, and never dropped without asking**: loading
  another mod (Load, F5, Browse, the Mod list) or opening another campaign now asks first when changes wait (the
  editors' and the faction tabs'); every editor then reads the new mod. Before, an editor's changes stayed bound to
  the mod they were made on, and Apply on the new mod wrote them into the old one's files.
- **A template that does not play in the open campaign** (Medieval II's saxons outside the Norman prologue) is
  said plainly, with the campaign it plays in.
- **The game's log kept on close is named `game_system.log.txt`** in the sessions folder (a tester read the game's
  own errors there as the editor's), and Tools > The game's log in plain words explains REX's "Game selection
  invalid - is the path ... ok?" (the engine started away from the game's folder, or a path it cannot read).
- **Start_<mod>.bat of a new Rome mod folder starts the engine from the game's folder** wherever it is started
  from (a shortcut, another folder) - it went `cd ..` from the folder it was started in.
- **Terrain editor / win conditions**: two buttons that raised an error before a mod was loaded.
- **Map: no more errors after switching tools while a new region's town waited for its click** (34 errors in one
  report: a fort placed in between, then every mouse move). The map forgets the old click and says so.
- **Buildings tab: the buttons above the list work before a town is picked** ('BuildingsEditor' has no
  attribute 'own').
- **A mod's engine settings come from the mod's own files only**: REX and M2EX read `descr_ex.txt` /
  `descr_caps_ex.txt` from the mod's data folder - a mod without them runs on the engine's built-in defaults (their
  own words: "Mods that don't ship this file get safe defaults"), not on the game's copy. The tool read the game's
  copy for such a mod, so it could show the wrong faction limit, ancillary / children limits and age of manhood,
  and take sprite sheets as xml (faction logos written that the game would not read). Now it reads what the engine
  reads; raising the faction limit in a mod without its own `descr_ex.txt` makes one with that line alone (every
  other setting stays as the mod ran before). Load still offers to copy the game's engine files into the mod.

## 0.29.1 - 2026-10-01

### Added
- **Raze Settlement for Medieval II** (Add-ons, M2EX): a 4th button on the capture scroll under Occupy / Sack /
  Exterminate - the game's Exterminate, then every building but the kept chains torn down, most people gone, a
  reward, the ruins to the rebels with a fresh rebel garrison (`give_settlement slave`); who may raze as in Rome's
  Sack Settlement. Lua add-ons go to `eopData/eopScripts` with one loader line in `luaPluginScript.lua`. The Add-ons
  list opens on the add-on of the loaded game.

### Fixed
- **A new Medieval II faction keeps its template's `ai_label` and `denari_kings_purse`**: they were lost, so the AI
  ran on the 'default' rule set with no income each turn (one reason new factions stood still). A note in Preview
  when the new faction starts with one army led by its leader (the computer seldom sends its leader out).

## 0.29.0 - 2026-10-01

### Changed
- **The bigger map's ground and climates get natural edges**: forests, hills and climates are no longer drawn in
  3 x 3 squares - their patches are rounded (each tile's own ground kept exactly, the coast where the heights put it).
  The x3 preview says plainly that nothing is written until 'Write it', and after writing shows the old and new size.
- **The exe goes into the game's folder** (beside RomeTW.exe / medieval2.exe): it finds the game and its mods by
  itself; the Mod list shows the mods of every game folder used (both games at once). Beside it only
  `CampaignEditor_settings.json` and `CampaignEditor_logs` (the log `CampaignEditor.log`, the zips, `sessions`).
  Backups go to `CampaignEditor_backups` (old `faction_tool_backups` still listed and restored). Old files are moved
  in by themselves.
- **Logs saved by themselves**: on every close, `CampaignEditor_logs/sessions/<time>/` gets that session's log and
  the game's newest `system.log.txt` (the last 30 sessions kept) - nothing to press.
- The Map's switches wrap onto a second row in a narrow window (Find was cut off); the mouse how-to is a '?'.
- **Long explanations fold into a '?'**: the Terrain editor's hint under each brush, and the intro texts of the
  Roster, Religions, Settlements, Traits, Events, Campaign rules, Art, pack and family tree panels show their first
  sentence; the whole text when the mouse rests on it or on its '?' - the map and the lists get the room.
- Making the map 3 x bigger says what it is working on (the coast, the heights, rivers...) - a big map takes half a
  minute.

### Added
- **Medieval II faction logos** (M2EX with `sprite_format xml`): the faction logo and small logo on the sprite sheets
  are on the Art tab, in the faction emblem and replaceable; the sprite moves to a page of the faction's own, factions
  borrowing it keep theirs as copies.
- **Shared pictures pulled apart**: a battle banner, the faction symbol's 3D texture or a town flag several factions
  name - the faction it is named after keeps the file and the others get copies of their own (their lines pointed at
  them; a symbol model's copy keeps its bytes' length), so recolouring changes one faction only. Crusade and military
  order banners stay as they are.
- **The Art tab shows every faction picture**: also the faction symbol's 3D texture, the flag on its towns in battle
  (Rome) and the battle banners (Medieval II, read from descr_banners_new.xml); a shared one says with whom. Thumbnails
  of Medieval II's .texture files are drawn.
- **Faction emblem - one picture everywhere** (Art tab), both games: the menu buttons (normal, mouse over,
  selected, greyed out), loading-screen logo, faction-screen symbol, in-game panels' symbol and the faction logos made
  from one picture, each in its own size; the button states measured from the mod's own; written with a backup.
- **Recolour a faction's pictures** (Art tab, Tools), both games: unit cards, battle textures, symbols, banners and
  captain cards moved from the colours they carry (a template's, found by itself) to the faction's own or any picked;
  only the faction-coloured parts change (compared with other factions' copies), light and shade kept; before / after
  shown; each file written in its own format, with a backup.
  The rims of the coloured parts (dull or blended edge pixels) are taken in too, and what is still missed can be
  painted by hand on the 'after' picture (new primary / secondary colour, or keep as it was).
  It also covers the units' far-away sprites, the campaign-map figures, the faction symbol's texture, the flag on
  Rome's towns in battle and Medieval II's battle banners; a shared picture a line names gets a copy of its own.
- **Engine files missing in a mod**: Load (and Check mod files) says when a mod of a game with REX / M2EX lacks
  the engine's own files the game's data has (`descr_ex.txt`, `descr_caps_ex.txt`, other `*_ex` files) - the engine
  may then run it on its built-in defaults - and with a yes copies the game's ones into the mod (backup, Restore).
- **Buildings and garrisons for many towns** (Tools, the Buildings tab's *Many towns at once...*, and the Map's new
  **Pick towns**: the ground only, a click picks a town in yellow, a right click acts on all of them): a building
  level added to (or a chain taken out of) many towns of any owner at once, picked by owner, level and city / castle;
  each town checked as the game would see it (too small, a castle's building in a city, the owner's faction list, no
  port) and left out with the reason. Garrisons drawn at random - 2 to 6 units per town or any range - from the units
  each owner may recruit (a rebel town: the nearest rebel armies' units), under an upkeep limit per town; added to
  the army in the town or replacing it. Asked for by a Stainless Steel modder.
- **Tools > The game's log in plain words**: the game's newest `system.log.txt` for this mod (found anywhere in the
  game folder) read and explained, both games: a crash first, then errors grouped (one kind once, however many units
  or factions it names), each with what it means and what to do, and for a Script Error the mod's line as it reads
  now. Known messages explained so far: a recruit line for a faction the unit's ownership does not name, a town or
  a character on a tile no one can reach or stand on, a town founded after the campaign's start year, a city /
  castle conversion into a level the faction may not build, missing files, portraits and interface pictures, a
  faction a script names that the mod lacks. "Open another log..." reads any other one.

### Fixed
- **M2EX / REX not seen** (a player with M2EX got "the original exe cannot take more"): the engine is found in
  the game folder by any spelling of its exe or .xdb, and its `descr_ex.txt` (in the mod or the game's data) counts as
  the engine being installed. Load says which engine was found and where `max_factions` comes from; a refusal says
  where it looked. Raising the faction limit writes the mod's OWN `descr_ex.txt` (a copy of the game's) - the game's
  data is not changed for one mod.
- **Report a bug / Suggest: 'SSL' error on some PCs** (an old Windows or an antivirus checking web traffic): the
  certificates inside the exe are trusted too; when it still fails, the message says why and to save the zip.
- **Reports came without the game's log**: the report window looked for `system.log.txt` only in the game folder
  and the loaded mod's folder. It now looks in every mod folder of the game (Rome: `<game>/<mod>/`, Medieval II:
  `<game>/mods/<mod>/`, also `bi/` and `alexander/`, each with its `logs/`), and with no mod loaded in the game
  folder used last - the mod's own log first, then the newest, each with how long ago it was written. When none is
  found, "How to switch the game's log on" says which lines the game's preference file needs.

## 0.28.0 - 2026-10-01

### Added
- **Terrain editor: Land and sea** - turn sea into land (draw a new island, a longer coast) or land into sea (a bay,
  a strait), both games. Each tile changes everything that says land or sea together: its `map_regions.tga` pixel
  (the region of the nearest land, or the one picked in "new land joins"; or the sea's colour), the ground round it
  (a land ground like its neighbours', or shallow sea) and the heights round it (a low shore or the sea's depth) in
  `map_heights.tga` and `map_heights.hgt`. Refused, in plain words: drowning a town, port, character, fort or
  resource, a region's last land, a river tile, or a port's last land. Undo / Redo stroke, Preview, one backup.

### Fixed
- **The bigger map (Tools > Make the campaign map 3 x bigger) - played in the game, it was flat and square:**
  - `map_heights.hgt` - the game's float copy of the heights, which it reads INSTEAD of `map_heights.tga` and never
    makes again - was left at the old size; it is now written at the new size (measured on both vanilla games:
    land = grey x max_land_height / 255, sea = min_sea_height x (255 - blue) / 255).
  - The hills and mountains became hillocks: the land got 3 x wider with the same heights. The heights and the sea
    floor are now 3 x higher (`descr_terrain.txt` max_land_height / min_sea_height), so the slopes stay as steep as
    they were; "Write it, heights as they are" keeps the old ones.
  - The coast was drawn in 3 x 3 squares: now smooth (a new pixel is land when most of the old land round it is;
    every block's middle keeps its value, so towns, armies, fleets and resources stay where they may stand; ports
    still touch their region's land). The heights' coast and the sea ground types are made smooth the same way.
  - Rivers: a diagonal step is a staircase, not an L; a river's mouth runs on to the new coast (and to the map's
    edge where it ran off it); rivers keep the land under them.

## 0.27.0 - 2026-10-01

### Added
- **Bring units and buildings from another mod** (asked by modders: moving them was hard): **Bring from another
  mod...** in the Unit editor and the Building editor - straight from the other mod's folder, no pack file to make
  first, in six steps you can go back and forth between: which mod, which units / building chains, their names here
  (taken ones get free names; a chain's levels too), who has them, where the units are recruited (pick a level of
  your mod when the other mod's is not here - before, such recruit lines were dropped and only Preview said so) or
  which of your units a building recruits, then the check and one write with a backup. Buildings come with all
  their levels, texts for every culture and level pictures; a `requires` or `convert_to` naming a building your mod
  lacks is warned about. Both games, same game only.
- Wiki: **Move units and buildings between mods**, step by step.

## 0.26.0 - 2026-10-01

### Added
- **A right-click menu on the Map**: what can be done at that spot - a town: add it or take it out, its garrison,
  its buildings; a character: open it on Units & armies; a free tile: a new army, agent or fleet placed right there
  (the nearest good tile when it may not stand there).
- **Dropped into the town**: an army or agent dragged onto a town's sign goes into the town (the sign is drawn
  bigger than its tile when zoomed out); a town that already holds an army says so.
- **Roster: building levels pull their chain along**: giving a level gives the levels below it, taking one takes
  the levels above (a chain is built level by level); the status line names them.
- The README shows the reports inbox: every bug report and idea really arrives.
- **Search on the Units & armies tab** (asked in a report): a Search box over "Your towns" (region or town name) and
  one over the armies, agents and fleets (name, tile, or a unit inside the army, e.g. "knight").

### Fixed
- A mod without `descr_names.txt` (e.g. a small Medieval II add-on mod) no longer stops the window when a template
  faction is picked ("expected str, bytes or os.PathLike object, not NoneType"); the name lists are just empty.
- The mouse wheel over an open drop-down list no longer logs an error.

## 0.25.0 - 2026-10-01

### Added
- **The bigger map is ready to play**: the relief is now SMOOTH (heights blended between the old points, land and
  sea apart so the coast stays where the regions have it; roughness blended too) instead of 3 x 3 steps; Rome's
  wonders move with the map too.
- **Wonders on the Map (Rome)**: the landmarks of descr_strat.txt (pyramids, pharos, colossus...) drawn as golden
  pyramids, dragged, removed and added (Edit forts, towers & wonders; a new one of any type of
  descr_sm_landmarks.txt). Medieval II's exe reads no landmark lines.
- **The map's real size** shown over the map, bottom left: tiles (map_regions.tga) and the heights' pixels.
- The bigger map leads the README and the ROADMAP.

## 0.24.0 - 2026-10-01

### Added
- **Settings** (bottom bar, beside Help): everything the tool keeps between starts in one window - light / dark,
  the window's language (English now; Spanish, French, German, Italian, Russian, Turkish planned), the game folder
  and the mod opened last, the map's look and legend, your contact for reports, the set-up fixes you said no to
  (Ask again), and the tool's and the mod's backup folders.

- **Make the campaign map 3 x bigger (alpha)** (Tools), both games: every tile becomes a 3 x 3 block - towns,
  armies, agents, resources, forts and event positions keep their places in the middle of their blocks, ports stay
  on the shore of their region, rivers stay 1 pixel wide (redrawn through the blocks' middles; a corner link becomes
  an L), every map picture made bigger with exact colours (regions, features, trade routes, heights, ground,
  climates, fog, roughness, disasters, radar maps), descr_terrain's size x 3, map.rwm removed. Shown before it is
  written, one backup, Restore gives every byte back. Not moved: coordinates in scripts (warned with a count).
  Without REX / M2EX it warns that the original exe stops at 510 tiles. Checked on both vanilla maps (every town,
  port and character in place); not yet in the game.

### Changed
- **Check mod** is now called **Check mod files** (Tools) - the same check (it took in Scan in 0.22.0): every file
  of the mod read, what the game would stumble on said in plain words.

## 0.23.0 - 2026-10-01

### Added
- **Alliances and wars at the start, both games**: the Diplomacy tab offers 'alliance' and 'war' as the Status at
  the start (descr_strat `faction_relationships X, allied_to / at_war_with Y`, as Sons of Mars, Barbarian Invasion
  and Medieval II write them); picking one side sets the other too. Trade rights have no start line in either
  game, so they are not offered.
- **Victory conditions on the Faction tab, both games**: regions to hold, regions to take, factions to outlive and
  Rome's goal (be emperor / take Rome), for the long and the short campaign (descr_win_conditions.txt); a region or
  faction that does not exist is refused (the game crashes on it); Undo / Redo. A new faction starts from its
  template's conditions.
- **The Diplomacy tab in plain words**: one **Status at the start** per faction (neutral / alliance / war, both
  ways) beside the AI feelings both ways; every value with its meaning (`600 (enemies)`, `0.5 (friends)`); a status
  pulls the feelings along (alliance up to the allied level, war down to the enemies', neutral out).
- **Family tree folded away**: the Faction tab's **Family tree** button opens it in the form's place; the form has
  the whole tab otherwise.
- Hover texts in place of long labels: the work buttons (New faction, Unit editor...), a '?' on the Diplomacy columns
  and the Victory block.

### Fixed
- **Medieval II diplomacy**: the tab now reads and writes `faction_standings` (-1.0 .. 1.0) - before it showed every
  Medieval II faction as neutral. A new Medieval II faction 'neutral to all' got Rome's `600 slave` lines, which
  Medieval II does not read (it was not at war with the rebels); now `faction_standings -1.0 slave` and
  `at_war_with slave` both ways, like every vanilla faction. Rome keeps the form the campaign's own factions use
  towards the rebels (600, or at_war_with in Barbarian Invasion).

## 0.22.0 - 2026-10-01

### Added
- **The Map's legend is a palette** (the user's idea): its signs are buttons - pick a town, fort, watchtower,
  resource, army, fleet or agent, then click the map to make one there. A town asks for its region's names first,
  then the click puts it and gives the land around it (3 x 3) to the new region; an army or agent asks for its
  name first. The picked button is yellow; a click on it again stops. Both games.
- **A faction's religion pulls its temples and priests along** (Medieval II): changed in the Faction form (or given
  to a new faction), the faction leaves the old faith's temples and guilds (levels and priest lines) and gets the
  new faith's where a faction of that faith - of its own culture first - has them; its priest, bishop and cardinal
  figures follow. Units and traits of the old faith are named in Preview, not changed.
- **Rome's packed textures are read** (data/packs/*.pak): a unit's or figure's texture that is not loose on disk
  is taken from the game's packs - the Battle model thumbnail and View in 3D show it instead of a grey model.
- **Events and later factions** (Tools; both games): the campaign's events - date, place, the title and text
  players see - changed, removed, new ones made; the date checked in each game's form; a name used twice (vanilla
  Rome's plague_in_italy) handled. The factions that appear later and the script lines that wake them are listed.
- **Map colour modes and a religion map**: a **Colours** choice on the map's bar (and in Layers) - Political,
  Diplomacy, Religion (Medieval II), None - one at a time instead of colour layers that hid each other. Religion
  colours each region by its main religion (changes made in Religions... not written yet count), paler where the
  majority is small; the legend lists the religions with their number of regions.
- **Traits and retinue** (Character editor, and Tools; both games): the traits and ancillaries themselves - who
  can have a trait, each level's name and description as players see them, the points it needs and its effects;
  an ancillary's name, text, picture (its own when it shared one), barred cultures and effects; a new trait or
  ancillary as a copy of one there is (levels and text keys renamed, texts copied). Preview, backup, Restore.
  Medieval II's compiled string tables are turned into a .txt when a text is written (the .bin is left: Preview
  says to remove it if the game shows the old text).
- **Character editor: the game's character panel** (both games; the user's wish): the picked person as the game
  shows him - portrait in a frame, name, who he is, age, the attributes as pips added up from his traits' and
  retinue's effects (Medieval II: Command, Chivalry / Dread, Loyalty / Authority, Piety, agents their skill;
  Rome: Command, Influence, Management), the traits by the names players see with what each gives, the retinue
  as picture cards. **Character** / **Family tree** above it switch to the whole family. The traits list on the
  left shows the level names players see too. Medieval II's compiled string tables (`.strings.bin`) are read
  when there is no .txt.
- **Figures on the campaign map** (Art tab, both games; asked by a tester): every character type of the faction
  with the strat model that shows it (descr_character.txt / descr_model_strat.txt) - pick another, see it in 3D
  with the faction's texture, Preview, Apply. A faction sharing its entry gets one of its own; a model it has no
  texture in gets a texture line. The figures' textures are listed as Art pictures ("campaign map figure: ...")
  to Replace; only the figures the faction uses are listed.
- **A new faction's figure textures are its own**: the clone copies the template's campaign-map figure textures
  under the new name (diplomat_macedon -> diplomat_epirus) where only the template used them - only the figures
  its characters show (vanilla Medieval II keeps unused Rome models with faction textures) - as it does for
  banners - replacing one no longer changes the template's (before, the new faction pointed at the template's
  files).
- **The map is a free canvas** (Map tab and Terrain editor): it can be dragged past its edges and zoomed out
  smaller than the view, with an empty field around it and a thin line along its edge (a strip of it always stays
  in sight); the wheel zooms to the point under the mouse; **Fit** puts it in the middle. A click on the field
  places, paints and drops nothing ("outside the map").
- **Rename in the files... on the Map** (Edit regions, beside Rename...): the region's and its town's names in the
  files changed everywhere the mod uses them, from the map too - not only the names players see (asked on
  Discord). The same window as on the Settlements tab.

### Changed
- **Scan mod is part of Check mod** (they looked like the same thing): with a faction picked, Check mod's report
  ends with every place that faction is named in the mod (game, REX and mod files told apart), and its window has
  **Ignore list...**; the separate Tools item is gone. The command line keeps `scan`. Its "missing files" no longer
  lists Rome textures kept as x.tga.dds or only in data/packs/*.pak.
- **Map: Edit resources and Edit forts & watchtowers are two switches** (they were one, "Edit resources & forts"),
  each with its own bar and a how-to line under it that is never cut off: pick the kind, **Place new**, then click
  a land tile; drag with the right mouse button to move; click, then **Delete picked** to remove. Where the
  campaign has no fort or watchtower line to copy (vanilla Rome and Medieval II) the bar says at once that a new
  one cannot be placed there, instead of after the click.
- **3D view: "man 1 of 8" read as eight men** - it was the most variants of one part (highlanders: 8 shields). It
  now names each part that comes in several: "Head 1 of 4, Body 1 of 2, weapon 1 of 3, shield 1 of 8".
- **3D view: the mount stands beside the rider** ("Its mount beside him"), both on one ground, as the files keep
  them - the seat drawn in 0.21.0 put a standing man (the files hold him with straight legs; the game bends them
  with its animations) through the horse's back and looked wrong.
- **Report a bug / Suggest**: the window's opening words are three short sentences - the long list of what is cut
  out (and the names of services in it) scared people off; the wiki page keeps the details.

### Fixed
- **"modeldb: a number expected at ..." on a mod's battle_models.modeldb** (a tester, Total Vanilla Beyond): a
  modeldb edited by hand - line breaks, tabs, two spaces between the values - is read as the game reads it (it was
  refused, so no new faction could be made); written back in the game's own form.
- **Wasteland regions (REX / M2EX)**: a region with `wasteland` where its town stands is read as a region without
  a town (it was read as a town called "wasteland"); Check mod no longer asks for its town pixel and names them
  (a tester's Sahara_Province); a settlement given to one is refused.
- **Rename in the files renamed people too**: a woman or a surname named like the town (vanilla Rome: Apollonia,
  "of Epirus") was renamed in descr_names.txt, its lookup and names.txt, and a character named like it in
  descr_strat. The name lists and characters' names now stay.
- **Add a relative... on Medieval II**: parents who died before the start are written too (it was refused - the
  form of such a record was thought unknown; the game's own world/template.txt has it: `age 94, dead,
  past_leader`), as on Rome.
- **Add-ons: two settings patterns could hang the editor** on a crafted script (a long line of spaces inside a
  list or set value took exponential time; found by GitHub code scanning). Now linear; values whose items touch
  with no comma or space between them (not valid in a script either) are no longer shown as settings.

## 0.21.0 - 2026-09-30

### Added
- **Volcanoes and land bridges in the Terrain editor** (Rivers, cliffs, volcanoes...): volcanoes on land (both
  games), land bridges on Medieval II - armies walk across a narrow strait (vanilla has 9: the Bosporus, the Danish
  islands, Messina, Corinth...), painted as a straight strip of 3 tiles; Preview names a lone, bent or broken one.
  Both were already drawn on the map, now they can be painted and rubbed out.
- **Forts and watchtowers on the Map** (Edit resources & forts): picked, dragged to another tile, deleted, and new
  ones placed - a new one copies the line of the nearest one the campaign already has (the line differs by game and
  mod; vanilla Rome and Medieval II have none, so there none is offered). Preview, backup, Restore.
- **Add-ons from anyone** (Add-ons > Add an add-on...): any REX (Rome) / M2EX (Medieval II) Squirrel script (`.nut`,
  or a zip with one) joins the list, kept in the editor's own folder; its settings are found by themselves (the
  UPPER_CASE `local NAME = value` lines: ticks, numbers, texts, lists, sets, the comments as help; optional
  `// @title / @game / @pick VAR chains|units|factions ...` header lines). Put in, updated and taken out with a
  backup like the built-in ones; **Share...** saves one as a zip with a README; a zip's folders never reach the
  disk.
- **Save a copy beside every Import / Replace**: unit cards and description pictures, building pictures and faction
  art (**Save a copy...** - as it is, or as a PNG to edit), a unit's battle model (**Save its files...**: its meshes
  and every faction's textures, in their data/ folders), its name call (**Save...**: the sounds, also those inside
  the game's packs) and portraits (a click on the picture). Nothing is written into the mod.

- **One path guard for every write**: whatever a pack, add-on zip or backup names, the editor writes, copies and
  removes only inside the loaded mod's or its game's folder (a `../`, another drive, a link that leads out are
  refused before anything is written, and logged); Restore refuses a backup that names files outside.

### Changed
- **The main window, reorganised** (the user's wish; every button that was there still is):
  - **Towns are picked on the Map**: the "Starting settlements" list is gone - a click on a town on the Map gives it
    to the faction or takes it back; **Capital** and **Removed towns** are in the Faction form.
  - **The family is on the Faction tab**: the tree on top, its people and the picked person below (the Family tab is
    gone). **Add a relative...** adds a son, daughter, wife, husband, brother, sister, parents, uncle or aunt;
    parents (and a brother / uncle older than the age of manhood, who may not live off the map) are written as died
    before the start - Rome's `dead` record; on Medieval II it is refused in plain words until a campaign shows the
    game's form of such a record.
  - **Settlements tab** = the towns' names only, as before, and the last tab again.
  - **A faction's religion** (Medieval II): a Religion field in the Faction form (descr_sm_factions.txt; spacing and
    comment kept, a religion the game does not know refused); a new faction takes the one picked. **Religions** is a
    work button (the end of the top row).
- **Art tab: the campaign-select map part is put away for now** - the maps stay the originals (a new faction a copy
  of its template's); drawing one from the faction's towns comes back in a later release.

### Fixed
- **A unit given to a faction was listed twice in a building's description** (a tester, Rome; Medieval II the same):
  where a level recruits a unit by two lines for different factions (vanilla: Arab Cavalry for the Moors and for
  Egypt, Turkomans, the Carthaginian peasant for Spain and for the Carthaginian culture - 36 levels in Rome, 107 in
  Medieval II), giving the unit (Roster, Unit editor) wrote the faction into each. Now it joins one line per level,
  and none where a line lets it in already. A mod given units this way before: take the unit away and give it again.
- **3D view** (testers): Medieval II's weapons and shields were grey - their textures (AttachmentSets) are named
  only in battle_models.modeldb and were lost when both model files were read (690 of 701 vanilla models have
  them). **Mounted units now show their mount**: the Battle model block has a Mount row (its model from
  descr_mount.txt, View in 3D, Save its files), and View in 3D of the soldiers has **With its mount** - the rider
  sat on it by descr_mount's rider_offset (Medieval II; on Rome over the middle of its back), legs straight as the
  files hold him. **Ships**: the Battle model and Voice blocks say plainly that a ship has neither (the game fights
  at sea by auto-resolve; its soldier and voice lines are only what the file's form asks for) instead of showing
  that placeholder land model and voice as its own - both games.
- **The Map did not open on some big maps** (a tester's "paneuroafricasia", Rome + REX): the political colours
  crashed with "IndexError: list index out of range" when the map had fewer than 256 region colours and Pillow took
  its fast path (the Windows exe). The Terrain editor was not touched by it.
- **SECURITY.md** said the editor sends nothing anywhere - true until Report a bug / Suggest; it now says when it
  sends.
- **Barbarian Invasion's 53 watchtowers** (listed after the diplomacy, under the regions) were not read: not drawn
  and their tiles not kept free for new armies.
- **The work buttons at the top** (New faction ... Add-ons) were cut off at the window's smallest width: they now
  scroll left / right (arrows at the ends, the mouse wheel over them), and the picked one is always in sight.
- **Faction form on Medieval II**: "Name (short)" and "Tooltip (faction icon)" are hidden - Medieval II's texts have
  neither (they were written for nothing); Rome keeps both.
- **Religions of a region** (Medieval II) says which region it is inside the window - the name players see, the
  name in the files and the town (a narrow window's title bar cut it); "in all 100%" is readable in the dark look.

## 0.20.1 - 2026-09-30

### Added
- **Ideas too**: the report window (now **Report a bug / Suggest**; Tools > Report a bug... / Suggest an idea...)
  takes a problem or an idea - an idea needs no logs (they are unticked, can be ticked), its words are required;
  the author sees "Bug:" or "Idea:" in front of each one.

## 0.20.0 - 2026-09-30

### Added
- **Report a problem** (bottom right; Tools > Send a report...; offered when the editor shows an error): a few words
  of what happened, screenshots if wanted, and the logs - the editor's, the game's `system.log.txt`, the newest REX
  crash report - reach the author in one click, no account needed; a report number comes back. Anonymous: the logs
  lose the Windows user name (also in paths), the computer's name, e-mail addresses, Steam IDs, SIDs, IP addresses,
  the player's name of REX's crash report and any words the user adds; **Show what is sent** shows every line, and
  nothing leaves before Send. Sent through a small relay (`worker/`, a Cloudflare Worker) that keeps the GitHub
  token - never in the exe. **Save logs (zip)** cuts the same names out now.
- **Settlements tab** (Edit / New faction): every region and its town with the names in the files, the names
  players see, the owner and names by culture; **Rename in the files...** changes a region's and its town's system
  names everywhere the mod names them - descr_regions, descr_strat, the names lookup and every language's names text
  ({keys} only), mercenaries, win conditions, campaign scripts, trait / ancillary conditions (`SettlementName ...`) -
  as whole words, spelled exactly, never in comments or descriptions, never where the line names a faction of the
  same name, not in a campaign with a map of its own; Preview, a backup, map.rwm removed. Checked on vanilla Rome
  (Latium / Rome) and Medieval II (Jerusalem_Province / Jerusalem: 37 files), Restore byte for byte. The Map's
  Edit regions bar has **Rename...** for the names players see.
- **Tools > New religion... / Religions of a region...** (Medieval II): the religion dialogs reached from the menu
  too - the Map opens with Edit regions on; on Rome the menu says Rome has no religions.
- **View in 3D for Rome**: Rome's `.cas` battle models (units, officers, mounts, animals - every one of the 807 vanilla
  files, versions 2.22 to 3.2) are drawn like Medieval II's: the man put together on his skeleton, weapons and shield
  in their places (on or off), each faction's texture, the game's detail levels. A model without a texture line
  (the women peasants) shows the texture its `.cas` names. Model files a mod folder does not have are taken from the
  game's own data folder (Medieval II too).
- **Campaign rules** (Tools > Campaign rules...), both games: every value of the campaign's settings files with a
  plain explanation, grouped as the files are, Find, the game's own value beside a changed one (Reset), Preview,
  written with a backup. Medieval II: descr_campaign_db.xml (ages, agents, revolts, crusades, bribery, ransom...),
  descr_settlement_mechanics.xml (each line of the town scrolls: growth, public order, income), descr_diplomacy.xml,
  descr_recruitment.xml; Rome under REX: descr_settlement_mechanics.xml (the people each settlement level needs);
  REX / M2EX: descr_unit_sizes.txt (the Unit size choices). Only the value's characters change - M2EX's own
  unquoted values (bool=false) included.
- **Add-ons** (a new button beside the editors): ready-made scripts put into the game with their settings picked in
  the tool, a backup on every write, Take it out. The first: **Sack Settlement** (Rome + REX) - a 4th choice on the
  capture scroll that tears the town down, pays a reward and leaves the ruins to the rebels. New: **who may sack** -
  only the player (default), everyone, only factions without a town (hordes), the player and hordes, only the
  computer, or picked factions; a computer faction allowed to sack does it whenever it exterminates. The chains
  that stay standing and the rebel units are picked from the mod's own buildings and units (Pick...), and names the
  mod does not have are refused - as is leaving out the governor's chain.

### Fixed
- **A region or its town could not be renamed** (a user asked; a double click on the town list only adds the town):
  **Rename...** beside the towns list, a right click on a town, and Edit region now show the names players see of the
  region and its town and write them to the campaign's `<campaign>_regions_and_settlement_names.txt` (the key and
  its gap kept, a missing key added; the names in the files stay) - both games.
  A double click on the town list now opens Rename (it used to move the town into Chosen); **Add >** or Enter adds.
- **Medieval II clone: "the Kingdom of Kingdom of Jerusalem"** - the game has no short faction names, so the
  template's name inside the copied texts (advice, intro subtitles, "de Sicily" surnames) was swapped for the whole
  new name; now "Kingdom of Sicily" becomes the new full name and a bare "Sicily" the short name (or the end of
  "Kingdom of Jerusalem"). Found making a Kingdom of Jerusalem with Judaism from Sicily.
- **Map: the buttons above the map were cut off** at a normal window width (New religion..., Names by culture...
  lay past the right edge - a user could not find them): the Regions and Resources toolbars now wrap onto a second
  row.
- **Buildings / Units & armies: a town opened without picking a faction first** - they show what the town's owner
  may build and recruit (the status line says so) instead of "pick the template faction first".
- **3D view: the detail levels were out of order** when a model mixed `model_flexi` and `model_flexi_m` lines
  (Rome: "0 - closest" showed the farthest model); they now follow the file.
- Campaign rules: the settings files' tag pattern could take very long on a crafted line (GitHub code scanning,
  py/redos); it now reads any line in linear time, with the same result on the games' files.
- **3D view: "Weapons and shield" off hid the legs too** on some models (vanilla peasants list their legs after the
  first weapons part): weapons and shields are now told by their names.

### Changed
- README, wiki, SECURITY: download the editor only from this repository's Releases page (or a link the author
  posted) - never a copy passed around elsewhere.
- **Unit editor: the battle model and the voice sit beside the two pictures** (they were below them, leaving half
  the panel empty - a user's screenshot); the unit's lines start higher. Fits a 1280-pixel-wide window.

## 0.19.2 - 2026-09-30

### Changed
- **Factions are listed with the name players see** when the mod shows another one: "turks - Ryazan" (Medieval II's
  faction names are fixed in the game, so mods keep "turks" and rename it in the texts - a tester on Discord). In
  every list where a faction is picked: the faction to copy or change, New region's owner and builder, where
  removed towns go, the towns' owner filter, rebels of, the Character editor, name lists, the editors' Show filter
  and New religion. The files keep the internal name.

### Fixed
- **Buildings whose list says `factions { all, }`** (a modder's way to let everyone build them) were taken as
  buildable by no one: the Buildings tab offered only the other levels, and setting them warned "not in the faction
  list" (a tester's report). 'all' in a factions list now means every faction, everywhere the tool checks it.

### Added
- **Hear a unit and give it a voice** (Unit editor, Voice in battle), both games: for each accent (Medieval II) or
  culture (Rome) of the unit's owners - its voice class, Play its own name call ("Khan's Guard!") and each of its
  orders, straight from the game's sound packs; Put in my own... makes your .wav files its name call (a unit that
  shares a line with others gets its own; a new unit gets one), shown before writing, with a backup. The game
  builds its sound list (events.dat) again on the next start.

## 0.19.1 - 2026-09-30

### Changed
- **Help (F1) rewritten for newcomers**: an "I want to..." list at the top says which button does what; every
  tab, editor and tool in plain words, the new ones of 0.19.0 included.

## 0.19.0 - 2026-09-30

### Fixed
- **A faction picked in New faction mode** (to change it, not to copy it) no longer ends in a puzzling "nothing to
  write" (a tester on Discord): the line at the top and the message on Apply now say that it is the template of
  a new faction, and to press Edit faction to change it itself.
- **Big campaign maps open ten times lighter**: a map of 4080 x 2496 tiles took 38 s and 6.6 GB of memory to open
  in the tool; now 2 s and 0.6 GB. The map is drawn in about a second instead of 19.
- **The Map tab no longer fails on a very big map zoomed far out** (Pillow refused a 1.3-billion-pixel picture): only
  the part of the map in view is drawn.
- **Painting regions on a big map**: the check before writing took 11 s and 800 MB on a 4080 x 2496 map; now a
  fraction of a second. A tile off the map is refused in plain words (it stopped the check).
- **A new faction on Medieval II now has battle banners, a voice, one-liners, movies and campaign music**: it is
  named beside its template in descr_banners_new.xml (with its own copy of the banner texture when that is on disk),
  descr_sounds_accents.txt, descr_sounds_db.xml, descr_movies_tracks.xml, the campaign's descr_faction_movies.xml
  and descr_sounds_music_types.txt - vanilla names every faction in them, and they were left out.
- **The ring round a town**: the 8 tiles round a town must be its own region or sea (vanilla Rome and Medieval II
  never break it), and on Medieval II no port may stand next to a town. Moving a town or port, painting regions
  and placing a new region's town or port are refused on Medieval II and warned about on Rome; Check mod lists
  what a map already breaks.

### Added
- **New unit / New building step by step** (Unit and Building editors; was Copy as new): a new one starts as a
  copy of one that works in the game, then steps you can go back and forth between - names and the texts
  players read, who owns the unit or may build the chain (factions or cultures), the unit's main numbers
  (men, attack, armour, cost...), pictures of your own - and last every file it will change before it is
  added. On Medieval II a renamed level gets its new name in every culture's own text too.
- Unit editor: **View in 3D...** - a Medieval II battle model (.mesh) drawn in 3D with its texture: turn it with
  the mouse, zoom with the wheel, pick the faction's texture, the level of detail and 'Another man' (the game's
  mix of heads, arms, bodies); also in the Replace model window. Reads all 3354 vanilla meshes. Rome's .cas
  models are not shown yet.
- **Check and install a pack** (Tools): a "copy data over the game" mod checked file by file before it goes in -
  new, the same, or what a replacement would lose: a file of REX's own, a picture of another size (for an interface
  icon page, the icons left outside it), another mod's whole text file. A text file that differs in a few lines can
  go in as "only its changes" (the pack's changed and added lines; lines it would drop stay). Pick per file, Preview,
  Install with a backup; Restore takes it all back. Found on a Julii unit-card pack that also brought the original
  game's battlepage_03.tga over REX's (the schiltrom / shield-wall buttons lost their pictures), an older
  descr_projectile_new.txt and a whole export_descr_unit.txt.
- **Replace a unit's battle model** (Unit editor, new **Battle model** block): the soldiers' (and each officer's)
  model with a texture of one of the unit's factions, how the model sits (on foot, on a horse or camel, an
  elephant, a chariot) against the unit's mount, and **Replace model...**: pick another model of this mod or of
  another mod folder of the same game (it comes with its meshes, textures and sprites; a taken name gets a free
  one). Every faction that owns the unit gets a texture on the new model where it has none - in
  descr_model_battle.txt and, on Medieval II, in battle_models.modeldb alike. A model made to sit otherwise is
  marked in the list and warned about (Medieval II likely crashes on it). Preview, a backup, Restore as always.
- **An icon of its own** for the exe and the window: a gear ring round a Roman "R" and a medieval "M" (drawn for the editor, no game pictures).

### Fixed
- Settlement names by culture under M2EX: checked in the game, so Preview no longer warns that it is untested there.
- **Medieval II with M2EX: a new mod folder starts the way M2EX's own mods do** - `Start_<name>.bat` runs
  `M2EX.exe --features.mod=mods/<name>` (as M2EX's Teutonic.bat / Crusades.bat), the plain game keeps
  `medieval2.exe @mods\<name>\<name>.cfg`.

## 0.18.1 - 2026-09-30

### Fixed
- **Barbarian Invasion: regions read and written right.** BI's descr_regions.txt has a `legion: ...` line after
  each region's name and a beliefs line (`pagan 90 christianity 10`) after farming. The tool took the legion
  line for the town, so a BI region showed the town as "legion: ...", the builder as the town and so on. Now
  both lines are read, kept when a region is edited, and a new region gets them from the region most of its land
  came from (checked on BI's own campaign: all 72 regions; a new region written and restored byte for byte).

## 0.18.0 - 2026-09-30

- **License**: GNU GPL v3.0 from this version on (up to 0.17.1: MIT). The editor stays free and open; programs
  built from its code must stay open under GPL-3.0 and keep the author's copyright notice.

### Fixed (from the user's tests)
- **Medieval II: a new army, agent or fleet of the rebels never showed up in the game.** In Medieval II the rebels
  are the last faction in descr_strat, and their block ends where the diplomacy starts with `faction_standings`
  (Rome starts it with `core_attitudes`). The tool knew only Rome's word, so it wrote the rebel army after the
  diplomacy lines, where the game does not read it. Now it goes into the rebels' block.
- **Smaller windows keep their buttons.** + Army / Place on map / Remove on Units & armies, Automatic / Suggest,
  the map's zoom buttons, the Unit editor's pack buttons, the Terrain editor's undo buttons and the Campaign box no
  longer drop out of a narrow or low window - a long hint is cut instead. The Faction tab's form and the Character
  editor's person form scroll when the window is lower than they are (Leader and heir, portraits, traits stay
  reachable). The smallest window is now 1024 x 640.
- **Drag the line** between the left side and the rest on the Faction, Units & armies and Buildings tabs: a wider
  towns list, or more room for the roster cards.

### Fixed (from the modders' guides, checked on the vanilla files)
- **REX / M2EX: the original game's limits no longer hold a modder back.** With REX or M2EX beside the game the
  religions limit (9) is not applied (New religion... says "no limit"), and Check mod counts regions, map size,
  units and religions as lifted for both engines (their own notes: "no faction, religion, region, unit, cultures,
  model limits"). The faction count still follows the engine's max_factions, which the tool offers to raise. On
  the original exes the limits stay as before.
- **Unit and Building editors: no cap of our own on lines.** A key the mod repeats (officers, bonuses, recruit
  lines, upgrades) takes as many lines as you like - no more "not more than the mod already has". A one-line key
  (category, class, recruit_priority_offset...) stays one line, and a key the mod never uses there is refused (most
  likely a typo). Officers stop at 3 only on the original exes (their own limit); with REX / M2EX there is no cap.
- **A son off the map may be as old as the mod's own age of manhood** (REX `age_of_manhood` in descr_ex.txt,
  Medieval II `<age_of_manhood>` in descr_campaign_db.xml), not a fixed 16; 16 when the mod does not set it.
- **Family tab**: a son or other living man written off the map (a record) older than 16 is refused -
  the game crashes on one; new sons now start at 16 or younger. One already in the file is only warned about.
- **Flag symbols (Rome)**: the banner sheets are read from descr_standards.txt (Barbarian Invasion uses
  symbols9-15, not symbols1-8). A new faction no longer puts its symbol on a rebels' sheet: it takes a free
  faction slot, or a new faction sheet is added (slave's flag keeps its picture).
- **Terrain editor**: Preview warns about a 2 x 2 block of river and a river closing into a ring.
- **Names by culture on Medieval II** need **M2EX** (not REX): the check, the window texts and Preview name the
  right engine; under M2EX the names are written the way REX documents it (to test in the game once).

### Added
- **Terrain editor: Heights** (`map_heights.tga`), a spray brush: hold the left button and the land under the
  brush rises (Raise) or sinks (Lower) the more the longer you hold; the middle does the most, the edge fades.
  **Smooth** evens out bumps, **Level to height** brings the land towards a height (right click picks a
  tile's own). Strength slider, brush up to 12 tiles. The map shows the heights as the file has them - land
  grey (black low, white high, brightened a little), the sea blue; only land is changed, the coast stays.
  Apply writes map_heights.tga, changes the same points in **map_heights.hgt** (the game's own copy of the
  heights, read instead of the picture while it is there; Medieval II needs it to load) and deletes map.rwm. Land
  never goes down to pure black (the game may take it for sea). Same file
  layout on Rome and Medieval II (checked on both vanilla maps). Tested in the game on both (video: https://youtu.be/mTdRAWympuw).
- **Find on the map** (Map tab and Terrain editor): type part of a name - a town (also the name shown for
  its owner), a port, a general, agent or fleet, a unit in an army, a fort, a resource - and pick a hit: the
  map zooms in close on it and a ring blinks round it. Names come first (typing "rom" lists Rome before the Romans' armies).
- **Check mod**: the factions against max_factions, and the original exe's limits (regions, map size, units, building chains, levels, hidden
  resources) counted against the mod, saying whether REX / M2EX is beside the game and what it is known to
  lift (REX: regions - HLR runs 750); win conditions naming a missing region or faction; Medieval II rebels
  with units the slave faction may not own; Rome regions lacking the 'slaves' the mod's other regions have.
- **A new religion for Medieval II** (Map tab, Regions: **New religion...**), e.g. Judaism: its name in
  descr_religions.txt (list + its own block), descr_religions_lookup.txt, text/religions.txt, its symbol
  (ui/pips/pip_<name>.tga - your picture as a 24-bit TGA sized like the religion copied, or a copy of its
  symbol), every region's religions line in every descr_regions.txt at 0 %, map.rwm removed; optionally the
  factions that follow it. Its shares per region are set with **Religions...** in the same Apply. Refused: a
  name taken, no shown name (the game crashes silently without its text), more than 9 religions (the engine's
  limit). Preview says how many lines of buildings, traits, ancillaries, faction standing and the AI still name
  only the religion copied. Checked on vanilla Medieval II (Judaism, 30 % in Cordoba, Restore byte-exact) and in
  the window; not yet in the game.

## 0.17.1 - 2026-09-29

Asked on Discord: where are the rebels?

### Added
- **The rebels (`slave`) in Edit faction**: their armies, fleets, agents, garrisons, towns, buildings and units
  (Roster) are edited like any faction's. Every rebel character in the game files carries `sub_faction <faction>`
  and takes its name from that faction's list (all 91 vanilla rebels, Rome and Medieval II); the tool writes the
  same: a captain for an empty rebel town takes the sub_faction of the nearest rebel (else the region's creator),
  and **+ Army / + Fleet / + Agent** ask whose rebels they are (**Rebels of**) and offer that faction's names.
  The rebels are never made playable and have no capital, leader or heir (greyed out). Checked on vanilla Rome
  and Medieval II (rebels take a town, a captain and a new army written, Restore byte-exact) and in the window.

### Fixed
- **A new faction no longer takes its template's shadow / spawn ties** (BI / Medieval II `descr_sm_factions`):
  a clone of `empire_east` was also `shadowed_by empire_east_rebels`, so two factions claimed one civil-war
  shadow; `spawns_on_revolt`, `spawned_by` and `spawned_on_event` were copied the same way. The clone starts as a
  plain faction and Preview says which tie stayed with the template.

## 0.17.0 - 2026-09-29

REX's new features, read from REX's own notes, and two things the tool got wrong on Medieval II.

### Fixed
- **Medieval II recruitment lines**: Medieval II recruits with `recruit_pool` lines (the vanilla buildings file has
  1475 of them and no `recruit` line at all), but the Roster tab, unit renames, unit packs, "Copy as new" and the
  line checks read only Rome's `recruit`. On Medieval II the Roster showed no place a unit is recruited, a renamed
  unit kept its recruit_pool lines on the old name, and unit packs carried no recruit places. One reader now knows
  `recruit`, `recruit_pool` and REX's retrain-only `retrain` / `retrain_pool`; "Add line" writes the file's own form
  (Medieval II: units at the start, new units a turn, most units waiting). Checked on vanilla Medieval II (england:
  37 of its 46 units recruited, with their buildings) and Rome.
- **Forts** (`fort x y ...` lines in descr_strat, Medieval II and REX) were not read: a fort line inside a faction's
  block was taken as part of the character before it (moved or removed with him), and armies could be placed on a
  fort's tile. Forts and watchtowers are now read on their own, drawn on the map (owner, name and "permanent" on
  hover, in the legend) and their tiles kept free; the terrain editor keeps their ground.

### Added
- **REX bracket requirements**: one requires line may carry several `factions { }` groups, each with conditions of
  its own (`( ( factions { greek, } and ... ) or ( factions { middle_eastern, } and ... ) )`). Every group is read;
  giving a unit or a level joins the first group (said in Preview), taking removes the faction from every group,
  and a group it alone forms is left for a person to rewrite, said in plain words. Unit packs name their owners in
  every group.
- **Unit editor: what REX adds to units** - a REX... button next to the attributes, stat_mental, stat_ground and
  weapon lines ticks REX's words with their effect in plain words: expendable, elitist, steadfast, intimidate,
  immune_to_psychology, relentless, disciplined_missile, inexhaustible, brace_for_charge, aggressive_push,
  disciplined_charge, ai_cannot_skirmish, ai_cannot_toggle_formation, desert_raider, forest_ambusher,
  troublemaker, police, client_kingdom_only_units, infinite_ammo, no_scale, single_entity, sp (shield piercing).
  `recruit_priority_offset` may be added although no unit of the mod has one yet.

## 0.16.1 - 2026-09-29

The user's Medieval II run (scotland: Edinburgh castle and back, Inverness taken and made a city): the game started
and ran with the changes, and its own log converts buildings the same way the tool does ("Conversion target
building not specified ... building will disappear during conversion").

### Fixed
- **City / castle with a size set by hand**: Inverness (a castle town) made a city and raised to a large town got
  its governor's building fitted to the file's old size at the write (`wooden_pallisade` in a large town - Preview
  warned "the game refuses to load that"). Buildings picked in the window keep the governor's building fitted
  there; without picks the fit follows the size set by hand. Preview now says "wooden_pallisade becomes
  wooden_wall" instead of "goes".

## 0.16.0 - 2026-09-29

### Added
- **Medieval II `battle_models.modeldb`** (asked for by the Stainless Steel author): the tool reads and writes the
  battle model database the game loads (a Boost text archive: length-prefixed strings, class info on a class's
  first appearance - the vanilla file of 701 models reads back byte for byte). **New faction**: every battle
  model with texture or attachment (shield) entries for the template gets the same for the new faction (vanilla
  england -> 121 models), so its units are not untextured in battle; a mod folder without its own modeldb gets a
  copy of the game's with the additions. **Unit packs** carry their modeldb models with the meshes, textures and
  sprites they name; on import a model with the same name and other content is added under a free name in
  modeldb and descr_model_battle.txt alike (the unit's soldier / officer lines and mounts follow), and every owner
  gets texture entries in both files (from the model's mercenary texture, else its first). Checked on vanilla
  Medieval II (clone england -> wessex, pack export / import, Restore byte-exact); not yet in the game.
- **Unit packs give every new owner a texture line** in descr_model_battle.txt (Rome too), instead of only
  warning that one was missing.

### Fixed
- **"<army> stands on x, y - move it first" when moving a town** (the user's HLR log): taking Odessus sent its
  garrison out to the next free tile, the very tile the town was then moved to, and Apply refused every time. An
  army on a moved town's new tile now steps aside to the nearest free tile of the region (said in Preview).
- **Unit packs (Medieval II)**: a model named `Feudal_Knights` in the unit and `feudal_knights` in
  descr_model_battle.txt was not found (the game reads these names without case) - now it is.
- **An early 0.12 names-by-culture module** (`<mod>/script/modules/ft_settlement_names.nut`, with guessed REX
  calls, which REX loads as a script module) is found on Load; with a yes its names move into the campaign
  script (REX's documented way) and the module goes.

## 0.15.1 - 2026-09-29

### Changed
- **City or castle: Medieval II only, twice checked.** The switch shows (and the write is allowed) only when the game
  is Medieval II (its exe, else its data) **and** its buildings mark castle levels; Rome, Barbarian Invasion and
  Alexander never show it, and a castle asked for there is refused before anything is written.
- **A castle never outgrows castles**: picking huge city for a castle on the Buildings tab is refused with the reason
  (castles end at the citadel, a large city - make it a city first), and Preview refuses such a castle too.

## 0.15.0 - 2026-09-29

### Added
- **City or castle (Medieval II)**: *Settlement is a* city / castle on the Buildings tab (New and Edit faction).
  A castle is the settlement's `settlement castle` line in descr_strat plus castle buildings; the tool switches the
  line and converts the buildings as the game does - each level becomes the level its `convert_to` names in the
  matching chain (core_building <-> core_castle_building, barracks <-> castle_barracks, a church <-> a chapel,
  roads <-> castle roads...), a level without one goes (a castle has no market or town hall), and the governor's
  building is fitted to the settlement level (a castle's equals it, a city's is one below). Afterwards only that
  kind's buildings are offered. A huge city cannot be a castle (castles end at the citadel, a large city) - the
  tool says so. Preview lists every building converted or gone. Checked on vanilla Medieval II (england: London a
  castle, Nottingham a city; Restore byte-exact); not yet in the game. Rome has no castles: not shown there.
  (Asked on Discord - the tool only made cities before.)

## 0.14.1 - 2026-09-29

### Fixed
- **Name list... on Medieval II**: vanilla M2 has surname keys with a space (`de Lyon`, `von Saxony`, `al Rashid` -
  8 factions' characters carry them). A new list kept such names as `de_Lyon`, another key, so the game would not
  have found the characters' names. Names the characters already carry are now kept exactly as written; new names
  are still written with `_` instead of a space (the game and its console want no space inside a name:
  `"Gaius Julius_Caesar"`, vanilla Rome's `of_Scaldis`), and the wizard says so.

## 0.14.0 - 2026-09-29

Name lists of one's own and every town's names by culture in one table (the user's wishes). Checked on a plain Rome
copy (the julii's own list: Preview, the names kept that its characters carry; a new faction with its own list in
the synthetic mod, Restore byte-exact) and in the window; not yet tested in the game.

### Added
- **Name list...** (Faction tab, under the leader and heir; New and Edit faction): a faction's own men's names,
  surnames and women's names in three steps - type or paste them, one per line or separated by commas (then a name
  may have spaces), or by spaces; each step can copy or add another faction's names. Written together: the faction's
  own section in `descr_names.txt` (a section it shared, as in BI, is left to the others), the shown names in
  `text/names.txt` and the keys in `descr_names_lookup.txt`. The leader, heir, captains and family records take
  names from the new list in the same Apply. Editing: names the faction's characters and records already carry
  stay in the list (Preview says which) - the game crashes on a name that is in no list. Only Latin letters,
  digits, ' and - (the game's files and font take no others).
- **All towns' names...** (Faction tab, the per-town dialog, Tools): every town's names by culture in one table -
  a column per culture, the owner, its culture and the name shown now; sort by any column, filter by culture
  (with / without a name for it), by the owner's culture, by what waits for Apply, search; double click a cell to
  type a name in place. Towns the mod's own campaign script renames show grey and are left alone.

### Noted
- Big maps: a tester's mod with a campaign map of **5456 x 2464 tiles** (map_regions.tga pixels) loaded in the tool, regions painted on it.

## 0.13.0 - 2026-09-29

Settlement names that follow the owner's culture (REX), shown live in the window. Checked in the window on a
plain Rome copy (the julii taking Mediolanium); not yet tested in the game.

### Added
- **Settlement names by the owner's culture (REX)**: **Names by culture...** (next to Edit region..., and on the Map's
  region bar) gives a town a name for each culture - Roma for the Romans, Rom for the barbarians - and a name for
  every other culture. The tool writes it into the campaign's `campaign_script.txt` (made, with its `script` line
  in descr_strat, when the campaign has none; a script of the mod's own is kept around the tool's block): REX
  renames the town with its `rename_settlement` as soon as a general takes it and at each of its owner's turns
  (`SettlementTurnStart` / `GeneralCaptureSettlement` + `SettlementName` + `FactionCultureType`, from REX's own
  documentation). Needs REX; backup and Restore as for every write. Not yet tested in the game. (Asked for on
  Discord.)
- **The name shows at once in the window**: as soon as a town changes hands in the tool (taken or given on the
  Faction tab or the Map, a new faction's start towns), the Map labels it with the name for its new owner's
  culture, the status line says it ("Mediolanium (now Mediolanum) added"), and the towns list shows the name the
  town has now ("(shown: Medhlan)"). A name set in Names by culture... shows on the map the moment OK is pressed.

### Fixed
- **New mod folder made from Barbarian Invasion or Alexander** (REX): its start file now starts that game (`-bi` /
  `-alx`, as REX's own start files do). Without it REX read the mod over the plain game's data, and the menu's
  imperial campaign was read with BI's factions (the user's log).

## 0.12.0 - 2026-09-29

Built from a tester's questions and the user's Barbarian Invasion run. Checked on Rome (plain + REX) and
Medieval II copies, in the window on Linux and with the deep Check; the flag symbols and logos not yet in the game.

### Added
- **Flag symbol and faction logos** (Rome): the Art tab now lists the symbol on the faction's campaign-map flags
  (`banners/symbolsN.tga.dds`, slot `standard_index`) and its faction logos (the faction button, `logo_index`;
  the small logo, `small_logo_index`), and **Replace...** changes them. A new faction gets its own flag slot and,
  under REX (`sprite_format xml`), logo sprites of its own with the template's pictures copied in, so the
  template keeps its own. A faction sharing a slot or sprite gets its own on Replace. (Asked for by a tester.)
- Terrain editor: **Climates** - paint each land tile's climate (`map_climates.tga`: trees and plants on the
  campaign and battle maps, winter snow, heat). The climates and their colours come from the mod's own
  `descr_climates.txt`, so Rome, Medieval II and mods with their own climates all work; the map shows the
  climates in their colours while this mode is on. Undo / Redo, backup and Restore as for the ground.
  (Asked for on Discord.) Adding a *new* climate is not in yet.

- Family / Character editor: Preview warns when a character gets more ancillaries, or a parent more children,
  than the game takes - REX's `max_num_ancillaries` / `max_num_children` in `descr_ex.txt` (the mod's, else the
  game's), else the original game's 8 and 4.

### Changed
- Terrain editor: long palettes wrap into rows, so every brush stays inside the window.
- **Restore a backup...**: pick any write in the list and **Undo back to here** undoes it and every later one in
  one go - no more restoring one by one. The list says when, what (faction, template) and how many files.
  Two writes made by one Apply are undone in the right order.

### Fixed
- Building editor: **Add line** refused a new `recruit` line once a level had as many as the busiest level of the
  mod ("no building level in this mod has more than 101 'recruit' lines"). Recruit lines only list units and the
  game takes any number of them, so they are no longer held to that rule. (Reported by a tester.)
- Buildings tab: a town showed **another culture's pictures** (BI's Eastern Empire got barbarian huts) and empty
  boxes for pictures that exist. The pictures are now looked for only in the town's own culture (and the cultures
  `descr_ui_buildings.txt` sends it to), in the mod and then in the game's own `data` - where Barbarian
  Invasion and REX mods take what they do not have. A level with no picture of its culture says so.
- A captain made for a garrison could get the name of one of the faction's **family members** (egypt's
  Heruben), which the game skips as a duplicate - captains now skip the family's names and the names of
  characters added in the same Apply. Medieval II first names of two words (egypt's `al Adil`, which the game
  reads as first name `al`) are no longer picked as first names.
- Linux: without tkinter the tool now says which packages to install instead of a Python error.
- Barbarian Invasion: the Eastern / Western Empire had no names ("no name in empire_east's name list for a
  captain"). BI's `descr_names.txt` gives one name list to several factions (`faction: empire_east,
  empire_east_rebels`); the tool now reads such lists for every faction on them, and a new faction cloned from
  one gets a list of its own.

## 0.11.0 - 2026-09-29

Tested in the game by the user on Rome + REX: a new faction (Nabataea) made in a few clicks with new regions,
its own pictures shown everywhere, the painted terrain drawn; the bugs he found are fixed here.

### Added
- **Faction limit**: the tool knows how many factions the game takes (slave included) - the original exes stop
  at 21 (Rome) / 31 (Medieval II); REX and M2EX read `max_factions` in `data/descr_ex.txt`. Load says "N of max
  factions"; a new faction over it is refused before anything is written, or - with your yes - `max_factions`
  is raised in the same write (backup, Restore). Over the limit the game closed at start ("Too many factions
  described here, maximum is(21)").
- Family: **someone already in the faction can be the wife or the child** - a new faction's heir can become its
  leader's son; before, only new people could be added, so a new faction's tree could not be built.
- Terrain: **Redo stroke**; the bottom Undo / Redo (and Ctrl+Z / Ctrl+Y) undo and redo strokes in the Terrain
  editor.

### Changed
- The tool's log `faction_tool.log` now lies in `RTW-M2TW-Campaign-Editor-files\logs`, together with the
  logs zips from **Save logs** - one folder to find what to send. The settings stay in
  `RTW-M2TW-Campaign-Editor-files`; a log an older version left there moves into `logs` by itself.

### Fixed
- **Two characters of one faction with the same name**: the game skipped the second ("duplicated character name
  in this faction, skipping") - an army named like the leader, a spy named like an automatic captain. Names now
  stay unique in a faction: the automatic captain skips taken names, the New army / agent dialog refuses one,
  and Preview refuses a write that would repeat a name.
- **Rivers**: the game follows a river side to side and stops where two river tiles touch only by a corner -
  everything past it is not drawn (the user's test). The 1-tile river brush now fills such steps itself, and
  Preview names every river piece that joins no sea, map edge, source or other river.
- Family buttons with nobody picked now say to pick a person instead of doing nothing.
- Portrait library: the portraits filled only one column when the window opened.
- Character editor: traits for `Characters all` are offered to everyone; ancillaries barred to the faction's
  culture (`ExcludeCultures`) are no longer offered.
- Rome portraits: young, old and dead of the same man are shown; the greyed Replace buttons gave way to a plain
  line and **Portrait library...** (Rome gives no portrait of one's own; Medieval II keeps Replace).
- The bottom Undo in the Terrain / Character editor did nothing and named the building editor.
- **A new faction's banners were the template's files**: `descr_banners.txt` kept the template's texture paths,
  so replacing the new faction's banner in the Art tab would have changed the template's too. A new faction now
  gets banner textures and a loading-screen logo of its own, named after it (`standard_macedonia` ->
  `standard_epirus`), and its lines point at them; the template's files stay untouched.
- The loading-screen logo (`loading_logo` in descr_sm_factions) was copied under the new name but the line
  still named the template's picture: it now names the copy.
- Replacing a `.dds` picture (Rome's `*.tga.dds` banner textures) wrote a TGA inside the .dds name; it now
  writes a real DDS in the format of the one replaced (DXT1/3/5, with its mipmaps).
- Two writes in the same second no longer fail on the backup folder's name.
- Medieval II portrait library (checked on the game's own southern_european pools): a new portrait no
  longer makes Rome-only folders (`cards`, `old` for groups that have none), and a new princess also gets
  her dead portrait (`portraits/dead/princesses`) - without it the game would show its placeholder.

### Added
- Art tab: a picture several factions share (the rebels' or routing banner) becomes the faction's own copy when
  replaced - written under its own name, and only this faction's line points at it.
- Art tab: **Back to the original** puts back a picture the tool changed (as the first backup kept it; for a
  new faction, the template's picture it was copied from). A pending change still has *Keep the current one*.
- Art tab: each picture says which file and line names it, and who shares it.

## 0.10.0 - 2026-09-29

### Added
- **Terrain editor** (its own work at the top): paint the campaign map tile by tile - the ground (fertility,
  wilderness, forests, hills, mountains, high mountains, swamp; the kinds of sea) and the marks across it
  (rivers, fords where armies cross, river sources, cliffs). Land stays land and sea stays sea; nothing the game
  refuses goes under a town, port or character; Preview warns about a broken river. Apply writes
  `map_ground_types.tga` and `map_features.tga` with a backup and deletes `map.rwm` (the game builds its map
  again). Not yet tested in the game.
- The map draws each feature in its own colour (rivers, fords, sources, cliffs, volcanoes).

### Fixed
- Medieval II's impassable land (`64 64 64` in map_ground_types) now refuses characters like mountains do.

## 0.9.4 - 2026-09-29

### Fixed
- **Barbarian Invasion (bi) would not load its campaign** ("invalid literal for int() ... 'Pictii'"): an entry
  of its `descr_regions.txt` has a line more before the colour. The file is now read by one reader for
  everyone (the colour line anchors each entry), and the tool's writers (Edit region, region tags) use it too.
- Loading a Rome mod after a Medieval II one with *Edit faction* on no longer shows "france has no faction
  block": a faction the new mod does not have is cleared.

### Changed
- Scan mod knows the **Barbarian Invasion** files (the game manifest now has `bi/`, from the user's install).

## 0.9.3 - 2026-09-29

### Added / changed
- **Portrait library** (Character editor): every portrait of a culture - young, old, dead; generals, civilians,
  rogues - as the game hands them out; **Add portraits...** puts new ones in the culture's size and depth with
  their cards under the next free number in every folder of the group (the dead one greyed unless given);
  Medieval II: **Use for <character>** makes a picked one his own.
- **Art tab: the campaign-select map is an optional part** that opens and closes (a line at the top). It is
  closed and **off by default: every `map_<faction>.tga` stays the original** - nothing is drawn over it, for a
  new faction, taken towns or painted regions alike. Ticked, the faction's map is drawn from its towns and the
  maps of the factions whose land changes follow, as before. Closed, the pictures take the whole tab.

## 0.9.2 - 2026-09-29

### Changed
- **New name: RTW & M2TW Campaign Editor** (it edits Rome: Total War and Medieval II: Total War alike). The exe
  is now `RTW-M2TW-Campaign-Editor.exe`; its folder `RTW-Campaign-Editor-files` is renamed to
  `RTW-M2TW-Campaign-Editor-files` on the first start, so the log and settings stay.

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
