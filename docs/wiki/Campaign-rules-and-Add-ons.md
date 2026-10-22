# Campaign rules and Add-ons

## Campaign rules (the Campaign rules... button, top row)

![Campaign rules](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/campaign_rules.png)

> **Experimental** (a red line at the top of the window): try it at your own risk - a backup is made first and Restore
> undoes it. If you tried it, please send a report (Report a bug / Suggest).

Every value of the campaign's settings files, by group, each with a plain explanation:

- **Both games** - the top of the loaded campaign's `descr_strat.txt` (group "The campaign ..."): the start and end
  date (year and season, a minus = BC), `timescale` (years a turn - Medieval II and REX), how seldom brigands and
  pirates appear, REX / M2EX's `random_persona_weights`, and the switches as on / off: night battles, the date shown
  as turns (Medieval II), Marian reforms off or already done, rebelling generals, gladiator uprisings. A switch
  turned off loses its line, one turned on gets a line; the faction lists and everything below stay as they are.
- **Medieval II** - `descr_campaign_db.xml`: recruitment, religion (witches, heretics, inquisitors), bribery, ages and
  the family tree (coming of age, marriage, children, old age), ransom, autoresolve, sacking and siege gear, revolts,
  hordes, merchants, agents' chances, crusades and jihads. `descr_settlement_mechanics.xml`: each line of the town
  scrolls - population growth, public order, income - with its weight, min and max (cities and castles apart).
  `descr_diplomacy.xml`: what each offer costs and how it moves standing. `descr_recruitment.xml`.
- **Rome under REX** - `descr_settlement_mechanics.xml`: the people each settlement level starts with, needs to grow,
  and holds at most; the weights of the town scroll lines.
- **REX / M2EX** - `descr_unit_sizes.txt`: the Unit size choices in the options (soldiers x this number; with REX the choice is on the options' **Controls** page, not Video).
- **REX / M2EX engine settings** - `descr_ex.txt` (sound, camera, max factions, bribery, hordes, ages and the family,
  the battle range disc and colours...) and `descr_caps_ex.txt` (feature switches: recruitment slots per town, sprite
  format, trade fleets, portrait pools, building downgrade / conversion of culture...), grouped by the file's own
  headings, each value explained by the comment the engine writes above it. The engines read these two from the mod
  alone: a mod without them runs on the engine's defaults, and a change puts a copy in the mod - with only the
  changed line on and every other setting switched off (a `;` before it), so the mod keeps running as before. A
  switched-off setting (`;key value`) is shown as such: the engine's default holds until you change it.

**Find** looks through every file. A value that differs from the game's own shows the game's beside it, with
**Reset**. Change values - every change waits for **Apply changes** by itself (written by **Apply changes** in the main window with everything else waiting): only the value itself changes in the file (the rest
stays byte for byte), with a backup - Tools > Restore a backup undoes it. A mod without its own copy of a file gets
the game's copy with your changes. The game reads the rules on the next start.

## Add-ons

![Add-ons](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/addons_sack_settlement.png)

The **Add-ons** button beside the editors lists ready-made scripts that add something new to the game. Pick the
settings, **Preview**, **Put it in** - a backup is made first. **Update it** changes the settings later, **Take it
out** removes it. An add-on in the game that an earlier version of the editor put in is marked **(old)** in the
list, and **Load** offers to put every such one in again in this version with the settings it has (one yes, a
backup first) - an older Avoid Growth or Sack Settlement could draw the game's script console in its own font.

### Anyone's add-on (Add an add-on...)

**Add an add-on...** takes a Squirrel script (`.nut`) or a zip with one - REX (Rome) and M2EX (Medieval II) both
load every `.nut` in `script/modules` by themselves. The script is kept in the editor's own folder
(`CampaignEditor\CampaignEditor_addons` beside the exe) and shown in the list; its settings are found by themselves: the
UPPER_CASE `local NAME = value` lines at the top (true / false = a tick, a whole number, a number like 3.0, "text", a list
`["a", "b"]`, a set `{ a = true }`), with the `//` comment beside or above each as its help. Put it in, Update, Take
it out work as for the built-in ones (a backup each time). **Share...** saves it as a zip (with your settings or as
it came) plus a README - give it to others. **Delete from the editor...** deletes an added one (or a module made in the Module builder) from the editor's list
- and, when it is put into the loaded game, asks whether to take it out of the game too. Only add scripts from
people you trust: a script runs inside the game.

For authors, optional header lines make it nicer: `// @title Border Tolls`, `// @game rome|medieval2|both`,
`// @summary ...`, `// @needs ...`, `// @settings A, B` (only these), `// @label VAR Words shown`,
`// @pick VAR chains|units|factions` (a picker filled from the loaded mod's own buildings, units or factions).

### Scripts in the game (every script in script/modules)

**Scripts in the game...** (in the Add-ons side bar) lists every script REX (Rome) or M2EX (Medieval II) runs from
the game's `script/modules` - the editor's add-ons, Module builder modules, ones you added and anyone else's - with
what each is and whether it runs. Pick one: change its settings (written into its own lines, the rest byte for
byte), **Turn it off** (renamed `.nut.off`: kept, not run - **Turn it on** brings it back), **Delete it**, **Show the
code**, **Open the folder**. Every change lists what it does, asks first and makes a backup (Tools > Restore a backup).
Ctrl / Shift + click picks several scripts - **Delete the N picked...** deletes them; **Delete them all...** under
the list takes every one out (one write, one backup).

The test mod (Tools > Test mod) puts its add-ons and modules into the game's `script/modules` too - they stay there
when you throw the test mod's folder away. Each carries a mark at its end; **Take out every script the test mod put
in** removes them all with one press.

### Module builder (your own add-on, no code)

![Module builder](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/module_builder.png)

> **Experimental** (a red line at the top of the window): try it at your own risk - a backup is made first and Restore
> undoes it. If you tried it, please send a report (Report a bug / Suggest).

**Look: Blocks (like Scratch)** (the first look) shows the module as blocks that fit into each other: on the left the
kinds of blocks in coloured groups - events (yellow, WHEN), control (orange: FOR EACH, IF ... ELSE), conditions
(green), actions (blue); drag one into its place in the module (a red line shows where it goes) or click it to put it
in at the end. A block of the module is dragged by its dots to another place, or back onto the blocks on the left (or
right clicked) to take it out. **Look: Lists** shows the same module as one block under another.

![Module builder - blocks](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/module_builder_blocks.png)

**Module builder** (top row - it opens in the main window, a module not saved yet stays while you look at other works) or **Add-ons > New module (no code)...** puts an add-on together from blocks. REX (Rome)
and M2EX (Medieval II) run the same script, so one module works in both games; the original exes run no scripts.

- **WHEN** - what happens in the game: **the player's turn starts** (once a turn - new modules start with it),
  **every faction's turn starts** (once for each faction in turn, about twenty times a round - with 'the faction is
  the player' it is the same as the first), a town's turn starts (each town), a general takes a town, a building is finished, a unit is trained, a battle ends (for each general in it), a town riots, rebels or
  grows to its next level, a faction is destroyed, a faction gets a new leader, a son comes of age. Under it the
  window says what the event brings along (a faction, a town, a general, the town's old owner, a unit).
- **FOR EACH** (under WHEN, like Scratch's *repeat*): **once** (what happened), or **for each town of** / **for each
  army of** the faction it happened to, the player or a faction you name, or **for each faction** (not the rebels).
  Everything below is then done once for each of them in turn, and *the town*, *the general*, *the faction* of the
  lines below is that one - "every turn, each of my towns but the capital gets 100 people".
- **IF** - **only when** *all of these are true* (and), *any one of these is true* (or) or *none of these is true*;
  **not** in front of a line turns that line round. The lines: the faction is the player / a computer faction / one of the factions you pick;
  its money; its number of towns; the turn (or every N turns); a chance in percent; the town's people; the town is
  one of those you pick; the town is the faction's capital; the town has a building of a chain; the town's old owner.
- **DO** - in this order: give money (below 0 takes it) to the faction, the old owner, the player, the rebels or a
  faction you name; add people to the town, take a share of them, or keep at most a number (a ceiling); build a
  building level; tear down a chain (the governor's `core_` buildings never); new units in the town; give the town to
  someone; set war, peace or alliance between two factions; give the general a trait or a retinue member; show the
  game's own message scroll (title and text); write a line in the game's log; run a console command (for experts).
  In the log line and the console command `{town}`, `{faction}`, `{owner}`, `{general}`, `{turn}` and `{people}` are
  filled in.
- **ELSE** - the actions done when the IF does **not** hold (the same list as DO): "if the town has a barracks, a
  free unit; else 500 denarii towards one".

**The engines' own lists** - for those who know them: **a game condition (any of the engine's)** takes any line of
the engines' condition list (`FactionType england`, `Trait GoodCommander > 0`, `not I_TurnNumber < 3`...), checked
against what just happened; **run a console command** and **run a campaign-script command** take any line of those
lists (`kill_character "{general}" Battle`, `set_event_counter my_counter 1`...). **Pick...** beside the line lists
every one with a search - its form, a sample, where it works, what a condition needs from the event - and **its
parameters as fields**: factions, towns, regions, units, characters, traits, retinue members and buildings picked
from the mod (the event's own `{faction}`, `{town}`, `{general}` first - filled in when the module acts), comparisons
and choices from a list, with the line put together under them (a line already there is read back into the fields).
Under the line the builder shows the form of the one typed. A module for both games offers what both engines have (299 conditions,
142 console and 198 campaign-script commands); for one game, that engine's whole list. The engine's own description
shows when the game has its `documentation` folder: start the game with REX / M2EX, open the console and type
`dump_docudemon` once. What an event brings comes from the engines' lists too (REX's 'a general takes a town' has no
old owner; REX has no 'a town grows' event - make such a module for Medieval II only).

**Any event and numbers kept between turns**: **More events...** beside WHEN picks any event of the engines' own
list (`SettlementTurnEnd`, `CharacterTurnEnd`, `AddedToBuildingQueue` on Medieval II ...), with what it brings. IF
**a remembered number** and DO **remember a number** / **add to a remembered number** keep numbers between turns and
in the saved game (the engines' own event counters - campaign_script's `I_EventCounter` reads them too); a name like
`seen_{town}` keeps one number per town.

`+ another condition...` / `+ another action...` add a line (one that needs what the event does not bring is greyed
out, with the reason), `x` takes it out. Names come from the loaded mod: its factions, towns, units, building chains
and levels, traits and retinue members. **In plain words** below says what the module will do, and the line under it
what is still missing.

**What the player may change later**: tick any number or text and it becomes a setting on the Add-ons page (the words
beside it are what the page shows); **Module on** and **Only once in a campaign** are always there.

Nine examples start it, made for the loaded mod: Help when broke, Loot for taking a town, Plague in big cities,
A free unit when a barracks is built, Gold for holding the capital, A message on turn 10, Rebellion punished,
A trait for the conqueror, Avoid Growth for chosen towns. **Show the script** shows what it writes; **Check it** checks
the names against the mod; **Save to my add-ons** keeps it in the Add-ons list; **Put it in the game** writes it into
the game's `script/modules` and its messages into the mod's `text/custom_messages.txt` (a backup first - Restore
undoes it); **Share...** saves it as a zip. A saved module opens in the builder again: **Add-ons > Change it in the
Module builder...**; a right click on one of your modules in the builder's list deletes it. Each time it acts, the game's log (`system.log.txt`) gets a line starting with its name, like
`[HELP_WHEN_BROKE]`.

### Upkeep x 2 (both games, no engine needed)

No more huge armies in every town: every unit's upkeep in `export_descr_unit.txt` is multiplied (x 2 by default -
1.5, 3, any number). The game reads the upkeep from that file, so the recruitment scroll and the army cards show
the real, higher numbers - only a big income keeps a big army. It works on any mod of both games and needs no
script. **Take it out** puts back exactly the old numbers (they are kept in `CampaignEditor_upkeep.json` beside the
file); a unit you changed since stays as you made it and is named. Putting it in again with another number starts
from the old numbers, not from the doubled ones.

### Sack Settlement (Rome + REX)

A 4th choice on the capture scroll, under Occupy / Enslave / Exterminate. The town is exterminated the game's own
way, every building except the chains you keep is torn down, you get a reward per building and per inhabitant, and
the ruins go to the rebels with a garrison the game raises itself (from the region's rebel type). Land you do not
want to hold is burned and left to regrow.

- **Who may sack:** only the player (default), everyone, only factions without a town of their own (hordes), the
  player and hordes, only the computer, or the factions you pick. A computer faction allowed to sack does it
  whenever it exterminates a town.
- **Building chains never torn down:** walls and roads by default (take them out if you like) - **Pick...** lists
  the mod's own chains. The governor's building (the core chain) always stays, listed or not: without it the town
  could never be built up again. Every building standing in the town is read in the game, so one added in the
  editor or brought from another mod (Barbarian Invasion, say) is torn down like the rest.
- **People left in the ruins:** 600 by default and at least - a town cannot be wiped off the map (the games' own
  floor is 400 a level).
- **Rebel units if the game raises none:** **Pick...** lists the mod's own units.
- **The 4th button** off: Exterminate asks Yes / No to sack instead. Button text and tooltip are yours to change.

It is a REX module: it goes into the **game's** `script/modules` (`Rome Total War Gold\script\modules`) - REX's
own `script/main.nut` loads every `.nut` there when the campaign starts, whatever mod runs. A mod with a script
plugin of its own (its own `script/manifest.nut` and `main.nut`, like HLR's) does not load modules from its own
folder, so the editor never puts add-ons there. If the add-on's code is already pasted into the mod's own scripts,
**Put it in** refuses (it would run twice - two buttons). The game's log (`system.log.txt`) then says `[SACK] Sack
Settlement module loaded`. Plain Rome has no scripts - the add-on does nothing there.

### Avoid Growth (Rome with REX, Medieval II with M2EX)

A tick box **Avoid Growth** on the settlement scroll of each of your towns, drawn with the game's own small box and
tick in the small font of its own ticks - in Medieval II in the row of its own Auto-manage tick, past the Construction
and Recruitment ticks the game adds there once Auto-manage is on; in Rome and Barbarian Invasion on the free line
under Automanage; at any screen size. Tick it and the people the town has right
now become its **ceiling**: it never grows past it, it still loses people the usual way (recruiting, battles,
plague, hunger) and then grows back - but only up to the ceiling again. A border town stays the village, town or
city it is: put it on auto-manage and forget it. Untick it to let the town grow freely again.

- The ceiling is kept in the saved game; a town taken by another faction drops its tick.
- The tooltip is short: unticked "Keep the town at the size it has now", ticked "At most 5000 people - it grows
  back up to that". **Words beside the tick**, both **Tooltips** ({cap} = the ceiling) and
  **Show the ceiling beside the words too** are yours to change;
  **Move the tick right / down** shifts it on the scroll (in the game's 1024 x 768 units, below 0 = left / up).
- One script for both games (REX and M2EX run the same scripts), in the game's `script/modules`. Its `[GROWTH]`
  lines show in the script console (Medieval II with M2EX writes a script's printed lines into system.log.txt only
  while the game starts up); in the console `sq ::avoid_growth_list()` lists the ticked towns and
  `sq ::avoid_growth_probe()` what the settlement scroll reports.

### Recruitment Order (Rome with REX, Medieval II with M2EX)

A town's recruitment panel in a fixed order: infantry, then missiles (archers, slingers, skirmishers), cavalry,
missile cavalry (horse archers, skirmisher horse), chariots (those that charge, then those with bows or javelins),
elephants (the same way), animals (war dogs, pigs), siege, ships - chariots and elephants are told by their
mount's class in `descr_mount.txt` - in each kind **the dearest first** (the strongest top left) or **the cheapest
first** (**In each kind**).

- Why a script: the game sorts the panel itself by each unit's custom-battle price (the 6th number of
  `stat_cost`), the smallest first - the order of the recruit lines in `export_descr_buildings.txt` does not count.
  During your turn the add-on gives every unit that number in the order above (1, 2, 3...); before every battle,
  at the end of your turn and when the campaign closes it puts the real numbers back, so battles, autoresolve,
  custom battles and the computer's turns use the real ones. Nothing is written into the mod's files or the saved
  game - take the add-on out and everything is as before.
- Ships always stand after the land units and agents last: the game keeps those groups apart.
- Medieval II splits the panel into its own kind blocks (infantry, missile infantry, cavalry, missile cavalry,
  handlers, siege, ships); **Medieval II: one panel for every kind** (on by default) switches the game's
  `recruitment_sort_simple` on while it runs (M2EX; `descr_campaign_db.xml` stays as it is), so the whole panel
  follows the order.
- One script for both games, in the game's `script/modules`. Its `[ORDER]` lines show in the script console; in the
  console `sq ::recruit_order_list()` lists the order and `sq ::recruit_order_off()` puts the real numbers back
  until your next turn.

### Player Diplomacy (Rome + REX)

The computer's factions stop attacking you when it makes no sense - only how they treat **you** changes, their wars
with each other stay as they are:

- **Truce:** after a ceasefire (whoever asked) a faction plans no invasion of you for the turns you set; a war it
  declares on you in that time is undone at once.
- **Client kingdoms** never plan to invade you while they are your protectorates.
- **Deterrence:** a faction far weaker than you (you **this many times stronger**, 3.0 by default: units in all
  armies and garrisons plus a number per settlement) does not plan one either; its allies already at war with you
  count on its side, so a big alliance still comes.

It works through REX's campaign AI hook (calculateLtgd). In the game's console: `sq ::truce_status()`,
`sq ::truce_set("egypt", 10)`, `sq ::power("egypt")`; its log lines start with `[DIPLO]`.

### Sack Settlement (Medieval II + M2EX)

The Medieval II brother of Rome's Sack Settlement - the same script, as M2EX runs the same scripts as REX.
Medieval II already has Occupy / Sack / Exterminate on the capture scroll, so its 4th button under them says
**Raze Settlement** (the words are a setting). It is drawn from the scroll's own text-button pieces, as wide and as
far apart as the game's three, in the game's font. It presses the game's own Exterminate, then tears down every
building except the chains you keep (the roads of cities and castles by default; the core chains - walls are their
levels in Medieval II - always stay), leaves as many people as you pick (600 at least), pays
a reward per building and per inhabitant, and gives the ruins to the rebels with a fresh rebel garrison
(`give_settlement slave`: M2EX turns the town rebel and raises the garrison itself).

- **Who may raze:** only the player (default), everyone, only factions without a town of their own (hordes), the
  player and hordes, only the computer, or the factions you pick. A computer faction allowed to raze does it
  whenever it exterminates a town.
- **The 4th button** off: Exterminate asks Yes / No to raze instead.

It goes into the game's `script/modules`, where M2EX's own scripts load it for every mod. The game's log says
`[RAZE] Raze Settlement module loaded`; in the console `sq ::raze_loot_probe()` lists what the capture scroll
reports and `sq ::raze_ui_fonts()` the game's fonts. An older version's Lua copy
(`eopData/eopScripts/raze_settlement.lua` and its line in `luaPluginScript.lua`) is taken out when this one is put
in. Vanilla Medieval II runs no scripts - the add-on does nothing there.


## Interface - the game's menu screens

**Interface** (top row, beside Events - shown in the main window, like the Module builder) shows every page of the game's menus - Rome, Barbarian Invasion and
Alexander's `data/menu/Rome.lnt`, Medieval II's `data/menu/mtw2.lnt` - on the 1024 x 768 layout the game uses, with
the pictures from `data/menu/textures` and the words from `menu_english.txt`. Pieces the game draws itself (buttons
with no picture of their own) show as frames with their words.
The page is drawn by the graphics card where it gives OpenGL 3.3 (else as before), so dragging, zooming and moving it stay smooth.

- The wheel zooms round the mouse, the held wheel (middle button) moves the screen, **Fit** shows it whole again.
- Click a piece to pick it; drag it to move it; drag the yellow corner to size it; the arrow keys nudge it (Shift: 10
  pixels).
- A right click on a piece: **Place and size...**, the page it opens, its words (text key) and tooltip, Copy, Rename,
  Remove, Open the page. The line under the screen says what the picked piece is.
- Tick boxes, drop-downs, text boxes, lists and sliders - the pieces the game draws itself - are drawn the way
  the game draws them, from its own parts in `data/menu` (`buttons_composite2`, `slider_composite2`, the gold
  frames). **Frames of every piece** shows each piece's box.
- The words are drawn in the game's own letters: its `.cuf` fonts, or under REX / M2EX the TrueType fonts
  `descr_font_db.txt` names.
- **Copy** (right click) makes the next numbered piece - the game finds many pieces by their numbers, so more faction buttons on the
  faction-select screen start with a copy of the last one. **Rename...** and **Remove** beside it.
- A double click on a button (or **Open its page**) goes to the page it opens, as in the game.
- A button under the mouse shows its **mouse over** picture and white words, as in the game; **Buttons shown** draws
  every button in one state (normal, mouse over, pressed, ticked). A right click > **Pictures of its states...** sets
  the picture (texture and region) of each state, adds a state or takes one out - every piece drawn with the same UI
  object changes with it.
- **Replace picture...** (right click) gives a piece a picture of your own and keeps what it does - the page it opens,
  its words, its tooltip (the game keeps a piece's behaviour apart from its picture). Each of its states (normal,
  mouse over, pressed...) takes a picture file of any kind or a picture of the **Picture library**; the files are
  fitted into the piece's size and written as one TGA under `data/menu/ce_ui/` (the game reads TGA only). Only this
  piece changes - it gets its own copy of the picture's description - or, if you choose, every piece drawn with the
  same picture. **Back to the game's picture** undoes it; an own picture no piece shows any more is taken out at
  Apply. The **Picture library** shows every picture of the game's menu sheets and your own pictures (kept in the
  editor's own folder for every mod - **Add pictures...**, a right click takes one out); a click gives it to the
  piece. Check mod files says when a picture names a region no sheet has (the game stops there) and when one page's
  pictures are too many for the sheet the game packs them into (Rome 2048 x 2048, Medieval II 4096 x 2048).
- The main window's **Undo** / **Redo** (and Ctrl+Z / Ctrl+Y) step its changes, **Preview changes** lists them,
  **Apply changes** writes them with a backup - the same buttons as for every work, none of its own. Only the lines
  changed are written; Restore takes it back. The **?** beside Fit holds this help.
- The menu backdrop: Rome, Alexander and Medieval II play a video there (`Dump0000.m1v` / `Dump0000.bik`, named in the
  layout file), so the screen shows a dark area with the video's name instead of the still picture under it;
  Barbarian Invasion shows its picture.

Medieval II keeps its menu pictures in its packs: unpacked they show, else the pieces show as frames.
### Sprite sheets

The second tab of **Interface** shows every sprite sheet in the mod's `ui` folder (Rome `strat3`, `shared2`, `battle3`...,
Medieval II `strategy`, `shared`, `battle`...) as the game reads it: the binary `.rsd` / `.sd` on the plain games, the
`.sd.xml` under REX / M2EX with `sprite_format xml`. Pick a sheet, a page and a culture: the page's picture shows with
the box of every sprite on it; the mouse over a box names it. **Find** looks through every sheet. A double click opens a
sprite big; its right click saves it, or the whole page, as a PNG. Nothing here writes the mod.

The idea and the first map of the file's format come from Wholesome Queen's *RTW Sprite & HUD Studio*.

### Campaign HUD

The third tab of **Interface** draws the campaign map's bottom panel as the game does (both games, the engines' own
places), from the mod's own pictures. It lies on a board, as on Obsidian Canvas:

- **the wheel** zooms in and out at the mouse (Shift: in small steps); the **middle** or **right** button, or **Space**
  held with the left one, moves the board; the arrow keys move it too;
- **Fit** (Shift+1) shows everything, **1:1** (Shift+0) one screen pixel per HUD pixel, Shift+2 zooms to the piece you
  picked; **+** and **-** sit beside them in the board's corner;
- **Screenshot over it...** lays your game screenshot exactly over the HUD (the HUD is stretched to its size, as the game
  stretches it). Drag the screenshot aside to see both side by side; it lands on the grid's dots and sticks to the HUD's
  edges and middle, so dragged back it sits exactly on it again. **Snap to grid** off or **Alt** held: it stays where you
  let go. Over the HUD it is see-through (the slider, [ and ]); beside it, whole. O shows or hides it.
