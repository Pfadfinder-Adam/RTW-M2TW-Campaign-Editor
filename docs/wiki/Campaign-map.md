# Campaign map

The **Map** tab draws the campaign map tile by tile from the game's own map files: one square = one tile.
Big maps load too - a tester's mod with a map of 5456 x 2464 tiles (map_regions.tga pixels; vanilla Rome is 255 x 156) opened fine.

## Looking around

- **Special places** (both games, with REX / M2EX): a right click on land > **Special place here...** - a model of
  the campaign map (a tower, fort, keep, wonder, mine... any `.cas` under `models_strat`, or your own) drawn on that
  tile by the engine, and a window of its own like a wonder's: its name on a hover, a double click opens it at the
  screen's left on the game's own scroll (Medieval II's painted frame, Rome's rolled scroll) - its picture across
  the whole width, its name, what it gives (one or two lines), its text, and at the foot who holds it now. A name
  and a text are a must; the picture, what it gives and money a turn for its holder are yours to add. The window
  shows the game's window as it will look. Its gold diamond on the map: a double click or a right click edits or
  deletes it; drag it with the left button to move it to another tile. Every change waits for Apply, which writes it (one backup): the windows' pictures in `data/ui/ce_places`,
  the model into the mod, and one script in the game's `script/modules` (`ce_places_<mod>.nut`) that runs only for
  this mod.
- **Delete from the map** (right click): a resource, a fort, a watchtower or a wonder goes with its line; a
  character of any faction goes with everything under him (his army or fleet); one placed but not written yet is
  simply taken out. A man on the family tree stays on it as one who died before the start, so his wife and
  children keep their place. Refused, in plain words: a faction's leader or heir (make another one first). A town is not deleted alone - every region of the map needs its
  town; give it to another faction instead (**Give this town to**).
- A town or character sign grows as the mouse comes near it - softly, the nearer the bigger, and from further away
  when the map is zoomed far out (the signs are small then), so the mouse need not hit the sign itself.
- Wheel zooms (to the point under the mouse), right drag moves the map (everywhere; a right click without moving opens the menu) - past its edges too: the map is a free canvas with an empty field around it, and zooms out smaller than the window; **Fit** puts it back in the middle.
- **Find**: type part of a name - a town or region by its file name or the name players read in the game (also
  the name shown for its owner), a port, a general, agent or
  fleet, a unit in an army (e.g. "hastati"), a fort, a resource. Pick a hit (click, or Down then Enter) and
  the map zooms in close on it and a ring blinks round it for a few seconds ([video](https://youtu.be/6WAdnGovGzA)).
- **The tab row and the side column**: the map's zoom and switches (Layers, Edit regions, Select...) stand in the tabs' own row, right of the tabs (the Terrain, Coast & heights and 3D tabs put their brushes there too); the legend (or the brush colours) stands in a column on the right, gone when hidden - the map has the whole height of the window.
- **The legend is a palette**: the signs on a button (+) are tools - click one (it turns yellow), then click
  the map to make one there: a **town** (first its region's names; then the click puts the town and the land
  around it becomes the new region's - paint more with a left drag), a **port** (click a coastal land tile: the
  port of the region there moves to it, a region without a port gets one), a **fort** or **watchtower**, any
  **resource**, an **army**, **fleet** or **agent** for **any faction**: click the tile and a window asks for the
  name - the faction is the one holding that land (a fleet: the owner of the nearest land), and another can be
  picked there. No faction has to be picked first. The faction you make or edit gets it in its list on Units &
  armies (give it its units there); any other faction's army or fleet starts with the first unit of its nearest
  army or fleet (its general's bodyguard) and is written with the next Apply.
  While a sign is picked it rides under the mouse (framed green where it may go, red where not - the reason beside
  it). Click the button again to stop; hiding the legend puts the picked sign down too. The legend is open on the
  first start (**Signs and tools** on the bar hides it; it scrolls by the wheel or a drag).
  Every named character shows as a general's flag, as in the game (family members too); an army in a town stands as a flag on the town's roof (no army, no flag). Towns, ports and characters grow under the mouse.
- **An army in a town** is one flag on the town's roof - part of the town's sign (a square cloth with a triangle cut
  into its right edge, at the sign's upper right corner); it is not dragged: right click the town > **Take the army
  out** or **Take an agent out** (each agent there by name and what he is), then click a free tile (Esc or a right
  click stops).
- **A double click on an army or a fleet** opens its units (any faction's in a window of its own; in Edit faction your
  own opens in Units & armies) - **Suggest** there draws an army at random from the units the faction trains (a
  fleet: its ships) by the numbers beside it: how many units, their upkeep together at most (0: no limit; kept for
  next time); **on a fort**, the army that holds it (a fort has no buildings - an empty one says how
  to man it: drag an army onto it).
- **A double click on a town** (or the right click's **This town...**) opens the town's own window, both games, any
  owner (Maps too). A region with no town in descr_strat.txt (the rebel village the game makes by itself)
  shows a short note instead, with an owner to pick and **Write its town** (the rebels too) - after the next Apply it
  opens like any town. Otherwise the window holds: its **owner** (hand it to another faction), **city or castle** (Medieval II), **level**,
  **population**, and two tabs that switch the same window: **Buildings** - the Buildings tab's own editor (the
  game's pictures, a level picked per chain, checked the way the game checks it: too small a town, a castle-only
  building in a city, one temple per town) - and **Garrison** - the Units & armies tab's card picker (click a card to
  add it, a garrison card to take it out; **Suggest** picks units the owner trains there - how many and the upkeep limit beside it; a named character keeps
  his bodyguard; a town nobody holds gets a captain; a town whose garrison is written in its own block -
  `garrisoned_army`, no captain, as some mods do for every town - shows that garrison and keeps it there; a town
  with nobody on its tile says who stands next to it, outside the walls). every change waits for **Apply changes** by itself: the changes go into the
  session's list and **Apply changes** in the main window writes them with everything else waiting, in one go (one
  backup set, one **Undo this write**). Another town opens in the same window. The right click's *Edit this town in Edit faction* still opens its owner in Edit faction.
- **Right click on the map**: on a town - **Give this town to** any faction (written with the next Apply; its
  characters go to the old owner's other towns, a captain's garrison goes with it; a town left empty - the rebels'
  garrison leaves with them - gets 3 to 6 of its new owner's units drawn at random, their upkeep together at most
  750, so you need not fill it by hand); on a free tile - **New army /
  agent / fleet here** with the land's owner already picked (a new army's **Make him a general** gives him the
  faction's general's bodyguard as his first unit and writes him as a named character outside the family tree - a
  general with his own name and a star on the map, not a captain; Rome's rebels keep a captain); on a new character
  not written yet - **Take it out**.
- **Layers** (a panel under its button - it stays open while you tick, a second press or a click aside closes it):
  **Colours**, one mode at a time - **Political** (the owners), **Religion** (Medieval II: each region in its main religion's colour, paler where the majority is small; the legend counts the regions), **None** (the ground only);
  **Shown**: borders, towns and ports (their squares and anchors - off for a clean look at the land), town
  names, the rebels' land coloured (it is barely tinted otherwise, so the factions stand out), characters,
  resources, the tiles the scripts name (see *Scripts on the map* below), relief, rivers, a tile grid when zoomed in. The mouse over a man shows his name beside it, over a resource its name as players see it.
- The line under the map describes the tile under the mouse: region, owner, ground, and whether an army may
  stand there.

## Maps

**Maps** (the first button of the top row) shows the map alone - no faction to pick, every faction alike:
drag any faction's towns, ports, armies, agents and fleets with the left button; right click a town to give it to
any faction, an army or a fleet for **Its units...** (the card picker in a window of its own - a general keeps his
bodyguard), a character to delete him, an empty tile for a new army, agent or fleet of any faction. Resources, forts,
wonders and regions work as on the Map tab. **Preview**, then **Apply changes** (a backup first; Restore puts every
byte back). New faction / Edit faction show all the tabs again; the map's changes stay until written.

**Delete a town with its region**: right click the town > **Delete this town with its region...**. The window asks
where its land goes:

- **stays as a wasteland** (Rome with REX, Medieval II with M2EX - the default there): the region and its land stay,
  nobody's - no town, no owner, no rebels, no economy; the AI never goes for it, no victory counts it, no neighbour
  grows, armies can still walk over it. Its line in `descr_regions.txt` says `wasteland` where the town's name stood
  (the engines' own way), its town pixel takes the region's colour. Medieval II takes no resource in a region
  without a town (its log says the tile is invalid): when resources lie on that land, one question asks whether to
  delete them or keep them (Check mod files names the ones kept). An island can go too. The map shows it grey while
  the window is open. **The way back**: right click its land > **Give it its town here...** - its name, the name
  players see and its owner; a village is written on that tile as the game makes it.
- **goes to a neighbour** (the only way of the original exes): its land (and its port) becomes the neighbour's it
  shares the longest border with - or pick another neighbour, in the window or on the map (while the window is open
  the map shows the town's region red, the one taking its land yellow and the other neighbours green; click a green
  one).

Either way every file that ties them follows: its block of `descr_regions.txt`, its settlement in `descr_strat.txt` (the owner's next
town becomes its capital; the rebels in the town go with it, a faction's characters there stay in the field), the
mercenary pools, the win conditions and Medieval II's music lists, in every campaign that uses the same map;
its block of the regions section at the end of `descr_strat.txt` (roads, forts, watchtowers: handed to the
neighbour's block, or gone with a wasteland - the game takes forts only in a region with a town); `map.rwm` is
removed. Written at once after **Preview**, with a backup. Refused in plain words: a faction's last
town (it would die as the campaign loads), a region a faction rises in by an event, an island with no land
neighbour. A campaign script that names the town or region is no reason to refuse: its lines that only list the
place (an invasion's `region` list) or flash it (`settlement_flash_start` / `stop`, `console_command`) are commented
out with `;` in the same write - as the game's own authors took Tbilisi out of the Mongols' list - and a condition
naming it (`if I_SettlementOwner ...`) is named in a warning to change by hand; an invasion left with no region is
named too. The names lookup and the names texts keep the old names (an unused name harms nothing).

**Many towns at once**: switch **Select** on, select the towns (a box, or clicks), right click > **Delete the N
selected town(s) with their regions...**. The same choice: their regions stay as wastelands (with an engine), or the
window lists each town with the region its land goes to - the
neighbour that stays it shares the longest border with; a region surrounded only by regions deleted with it follows
them. On the map: red = goes, yellow = takes land; pick a row (or click a red region) and it turns orange, its
neighbours that could take its land green - click one to give it the land. The same refusals as above (a faction's
last towns counted together). One write, one backup: **Undo this write** puts all of them back.

**Merge regions** (the switch on the map's bar - for a map with more regions than you want): only the regions'
borders and the town names are drawn meanwhile. Click the region that **stays** (yellow), then its neighbour that
**goes** (red) - a click on a third region makes that one the red, a click on a picked one drops it, **Clear** starts
again - and **Merge them** under the map: the red region's town and region go from every file as above and all its
land (and port) becomes the yellow one's; the yellow region stays as it is. Written at once with a backup (Undo this
write, Tools > Restore); the switch stays on for the next pair, and off again everything shows as before. The same
refusals as deleting a town (the two must touch; a faction's last town, an event region); script lines naming B are
commented out as when deleting a town.

## Towns and characters

- Picking a faction's towns (**Towns on the map...** in Factions): a click on a town adds it or takes it
  out, **Done** goes back.
- **Every faction's capital** (its first town in `descr_strat.txt`) shows a star inside its square in place of the
  town hall - light on a dark colour, dark on a light one.
- **What Apply will write is on the map before it**: the towns picked for a new (or edited) faction stand in its
  colour, their regions yellow as a selection is, its capital with the star, its garrisons as a flag on the roof -
  and so do a town given or a garrison changed in a town window or Many towns, kept for Apply.
- A left drag moves characters, towns and ports. The target turns green or red: an
  army needs land it may stand on (no sea, mountains, dense forest, river, ford or cliff) or a town no other
  army holds; a fleet needs sea; an agent any land.
- **Moving a town or port** repaints its pixel in `map_regions.tga`, moves the characters in it, and deletes
  `map.rwm` - the game builds it again on the next start (the first start takes a little longer).

## Select: a box round many things at once

Tick **Select** on the Map's bar and choose in **what...** the kinds it takes: towns, armies, agents, fleets (ticked at
first), resources, forts. Then, as in a strategy game, **drag a box with the left button**: everything of those
kinds inside it is added to what is selected (hold **Shift** to take it away instead). A click adds one thing
(**Shift** + click takes it away); a click on nothing clears the selection. The
political colours and borders go meanwhile; selected towns and their regions turn **yellow**, selected characters,
resources and forts get a yellow frame; the **right button drags the map**. A **right click** offers:

- **Give the N selected town(s) to** any faction (written with the next Apply);
- **Delete the N selected character(s) from the map** (their armies too) - a faction's leader, heir or a man on its
  family tree stays (the line under the map names them); **Delete the N selected resource(s) / fort(s)**;
- **Add a building to the N picked town(s)...**, **Garrisons for the N picked town(s)...** and **City / castle and
  level for the N picked town(s)...** - all open the window *Buildings and garrisons for many towns* with the picked
  towns already chosen (the third tab makes them city or castle - Medieval II - and / or of another level: the
  buildings converted the game's way, the governor's building and the population follow);
- **Pick every town of <owner>** (on a town), **Unselect all**. One Undo takes a whole job back.

Untick **Select** and nothing stays selected (the same everywhere: switching **Layers > Resources** or **Edit regions** off drops what was picked or waiting for a click, hiding the legend puts its picked tool down).

The same window is on Edit faction's Buildings tab (**Many towns at once...**). All towns of the campaign on the
left - filter them by owner, level, city / castle (Medieval II) or name, **Add all shown** - the chosen ones on the
right, with **What happens** in each:

![Garrisons for many towns](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/many_towns.png)

- **A building**: pick the chain and level. A town that has the chain gets it raised (never lowered, unless you pick
  *set it to this level*). Left out, with the reason: a town too small for the level (`settlement_min`), a castle's
  building in a city or a city's in a castle (Medieval II), a level the owner's `requires factions { }` does not
  allow (tick the box to put it in anyway - the game loads such a building, the owner just cannot build it again),
  a port building where the town has no port on the map. **Take a building out** removes a chain. The governor's
  building (walls / castle) follows the town's level and is not offered.
- **Garrisons**: units per town *from 3 to 6* (any range up to 20 - 40 with REX / M2EX) and the upkeep they may cost together per town
  (750 at first; 1000... - empty for no limit). **Draw the garrisons** picks them at random from the units each owner may
  recruit (its `ownership` and a recruit line of some building; generals' bodyguards and - unless ticked - siege
  engines left out); a rebel town draws from its region's rebel type (`descr_rebel_factions.txt` - the units the game
  itself raises there in a revolt; without one, from the rebel armies nearest to it), so a Gallic town gets Gallic
  rebels. **As many units as the game gives such a town** sets the number by the town's level, the way the mod's own
  towns of that owner have them at the start (vanilla's rebel towns: Medieval II village 5, town 4, large town 7,
  city 6; Rome 3, 3, 4, 4).
  With **only units the town's own buildings recruit** (on by default) a town gets only what its own buildings
  recruit for its owner - no catapult in a village without a siege workshop, no heavy infantry without barracks; a
  town that recruits none of them gets the two cheapest unit types (peasants, levy spearmen).
  Draw again for others. They join the army that holds the town, or replace its units (a general keeps his
  bodyguard); a town nobody holds gets a captain.

Every change waits in the session's list by itself; **Apply changes** in the main window
writes `descr_strat.txt` with everything else waiting, with a backup - Undo this write / Restore gives it back.

## Forts

Forts and watchtowers of `descr_strat.txt` (Medieval II, REX: `fort x y ... permanent name ...`) are drawn as small
towers, the top in the owner's colour; the mouse over one shows its name and whether it is permanent. No army or
agent is placed on a fort's tile. Barbarian Invasion's watchtowers (listed after the diplomacy) are drawn too.

Forts, watchtowers and wonders need no mode of their own - everything is in the legend and on the right click.
**New**: click *a fort* or *a watchtower* in the legend, then a land tile on the map. **Move**: drag one to another
tile (land, no town, port or other fort there). **Remove**: right click it -
**Delete from the map**. A new one copies the line of the nearest one the campaign already has (only the tile
changes); a campaign with none (vanilla Rome and Medieval II) gets it written in the regions section. In that
section (Barbarian Invasion's watchtowers) a new or moved one always goes under the block of the region its tile
lies in - the game skips one written under another region. Written with
Preview / Apply, backed up like every change.

## New regions

Tick **Regions**: every region in its own colour.

1. **New region...**: names, builder, rebels, region tags (hidden resources - picked from the mod's own under the arrow beside the box, a click adds or takes one out, or typed), triumph, farming, owner,
   settlement level. The tool picks an unused colour.
2. Paint its land with a left drag (brush 1-6 tiles). Right click a region to paint with that one - the same
   brush moves the border between two existing regions. **(sea)** at the end of *Paint with* paints the region
   map's sea (a border cut into a sailable river); land that belongs to no region can be painted to a region.
3. **Place its town** (and **Place its port** on the coast).
   For a region of the map picked in *Paint with* the same buttons move its town or port to the tile
   clicked; a wasteland gets its town there (then its port).
4. **Preview** lists everything written: `map_regions.tga`, `descr_regions.txt`, the name lookup, the region
   labels, the settlement, `map.rwm` removed.

A new region is in the towns list at once: a new faction can start there, and an edited one can take it, all
in one Apply. **Edit region...** opens a region's data again. For a region of the map it holds its **Owner** at the start (who holds the town in descr_strat.txt - a change is written with the next Apply, as *Give this town to*; a region with no town in descr_strat.txt, the rebel village the game makes by itself, gets its town written for the owner picked, the rebels too) and both names of the region and its town: the names players see (written to the campaign's `<campaign>_regions_and_settlement_names.txt` with the next Apply) and the names in the files (changed at once in every file that names them, with a backup - asked first). **Rename...** beside the towns list on the Edit / New faction tab (or a right click on a town there) opens the same window.

**Settlements tab:** every region and its town, both names. **Rename in the files...** (also on the Map: Edit regions, right click the region, then **Edit region...**) changes the system names (`Latium`, `Rome`) everywhere the mod uses them - descr_regions, descr_strat, the names lookup and texts of every language, mercenaries, win conditions, campaign scripts, trait and ancillary conditions - as whole words; comments, descriptions, lines naming a faction of the same name and people's names (descr_names, names.txt, a character named like the town) stay. Preview first, a backup, `map.rwm` removed. Tip: keep the name players see and the name in the files alike.

## Events and factions that appear later

**Events** (top row) (both games): the campaign's `descr_events.txt` - historic messages, and
plagues, volcanoes, earthquakes at a place. Each event's date (Rome: years from the start and optionally summer or
winter, `14 winter`; Medieval II: years from the start, or two the game picks one between, `210 220` - a date
the game would not read is refused; beside it the turn and the year it means, from the campaign's `start_date` and
`timescale`; a new event goes in date order - the games read the events as a queue, one put after a later event
never fires), its place (x, y; empty = a message only; **Show on the map**), the title and text
players see (`historic_events.txt`), the **picture players see** on the scroll (a historic event its own
`ui/<culture>/eventpics/<event>.tga` - **Picture...** puts yours in for every culture, sized like the game's; a
plague, volcano... shows its kind's `disaster_<kind>.tga` - **Picture...** replaces it for every event of that kind) and **what it does in the game** in plain words.
**New event...**, a right click on an event removes it (Ctrl / Shift + click picks many; **Remove all...** takes every one out), every change waits for **Apply changes** by itself (written with the rest, a backup first). Below the
list: **the factions that appear later** - they start dead (`dead_until_resurrected` in descr_strat.txt, no towns,
no characters) and come in *by an event* (`emergent_faction` with a date and a region the rebels hold, as Barbarian Invasion's
slavs - only those are offered), *as the shadow of a faction*
(the side that splits off it in a civil war, Barbarian Invasion's rebels of the empires) or *splitting off a faction
in a revolt* (Barbarian Invasion's Ostrogoths) - all of them only in Barbarian Invasion and Medieval II (plain Rome,
also with REX, stops reading descr_strat.txt at a faction that starts dead and crashes with a shadow and a split-off
one on a faction; Load offers to take such a line out of a plain Rome mod); the campaign script lines that wake one are shown too (Medieval II:
the Mongols and Timurids). **Change...** (or a double click) changes how a faction comes in - its date and region,
its partner, *may come back after it dies* (`re_emergent`), *lives without towns* (REX / M2EX's `can_homeless`: it stays in the game with no town instead of dying or becoming a horde); **Another faction...** makes a faction without towns
and characters appear later. Written with Apply changes, every file in step (descr_sm_factions, descr_strat,
descr_events).

**Campaign script...** (the Events window's bottom bar, both games): the campaign's own `campaign_script.txt` piece
by piece - each monitor (`monitor_event` / `monitor_conditions` ... `end_monitor`), loop, counter or command with the
comment right above it, its code beside the list. Take any out: a right click (the picked ones), **Remove all...**
for a mod made bare (an M2EX / REX mod that keeps only the map, factions and units). `script` / `end_script` stay, so
the game still finds the file. Every change waits for Apply changes - a backup first.

## Resources

Trade goods on the map can be placed, moved and removed; one per tile. Show them with **Layers > Resources**: a bar
opens under the map's buttons. **New**: click the resource in the legend on the right (or pick it in the bar and
press **Place new**), then click a land tile on the map - a right click or Esc puts it back. **Move**: drag one.
**Remove**: right click it > **Delete**, or click it (it gets a yellow frame), then **Delete picked**. A region's
resources are the ones on its land; **Region tags (hidden resources)...** edits the region's tag line.

## Medieval II

Religions per region (a town's right click on the Map: **Religions of <town>...**; with **Select**, the same shares for every selected region at once: **Religions of the N selected regions...**; or the Religions work, several lines picked); castles; agents such as merchants, priests and princesses.

**A faction's religion** (the Religion field of the Faction form) pulls what hangs on it along: the faction leaves
the old faith's buildings (temples and that faith's guilds - the `religion X` chains of export_descr_buildings.txt,
their levels and the priest lines in them) and gets the new faith's wherever a faction of that faith has them (one
of its own culture first, as a model), and its priest, bishop and cardinal on the campaign map take that
faction's figures. Preview lists every line; units and traits of the old faith (crusaders, jihad, the Pope's
favour) stay as they are - Preview says so.

**New religion...** (a town's right click on the Map, or the Religions work) adds a religion of your own - e.g. Judaism - everywhere the game needs
it: descr_religions.txt (its name and symbol), descr_religions_lookup.txt, text/religions.txt (without its
text the game crashes silently), its symbol in ui/pips, and every region's religions line at 0 %. It needs no
other religion: its symbol is **drawn by the editor** (its first letter on a disc of the colour you pick, in the
size of the game's own symbols) unless you take a copy of another religion's or a picture of yours. **Temples of
its own** (levels, 0 = none) makes a temple chain for it from nothing - `temple_<name>`, its `religion` line naming
the new faith, each level with the usual numbers of the mod's temples (another religion's own lines such as the
Pope's favour left out), built by the factions you pick, plain pictures drawn. Then give it its share per region
with **Religions of...** (each region adds up to 100) and, if you like, the factions that follow it. The game takes
at most 9 religions (vanilla has 5; REX / M2EX: no limit). Priests and traits of its own are not made - Preview
says which files still name only the old religions.

**Barbarian Invasion** (Rome's official expansion, and every mod made from it) has religions too - its beliefs
(Christianity, Paganism, Zoroastrianism). **New religion...** there writes a new belief into `descr_beliefs.txt` (its
tag, its three pips - drawn by the editor as the game draws its own: the symbol, and the same full-size symbol with the
game's own green arrow up (order) or red arrow down (unrest) laid on it at the bottom right; or the order and unrest pips copied from the belief picked and the level pip
your picture - and its name, order and unrest texts in `text/expanded_bi.txt`). Each region starts with its
shares of the beliefs - the last line of its block in `descr_regions.txt` (`pagan 90 christianity 10`, 100 in all) -
set the same way as Medieval II's (**Religions of...**, one region or many); during the game the buildings that carry
a belief (`religious_belief <tag> <n>`) and the characters' traits move them. Barbarian Invasion has no faction
religion line. **Temples of its own** makes a temple chain for the new belief from nothing, each level carrying it at
the strength the mod's temples give. Plain Rome has no religions.

## Settlement names by culture (REX / M2EX)

**Names by culture...** (next to *Edit region...* on the Edit / New faction tab, and a town's right click on the Map: **Names of <town> by culture...**) gives a town a
name for each culture of its owner, plus a name for every other culture. The engine (REX on Rome, M2EX on
Medieval II) renames the town when it changes
hands - as soon as a general takes it, and at each of its owner's turns. The tool writes it into the campaign's
`campaign_script.txt` (it makes one when the campaign has none; a script of the mod's own stays as it is around the
tool's block), with a backup like every write. Needs REX (Rome) or M2EX (Medieval II). Checked in the game on Medieval II with M2EX
([video](https://youtu.be/umwRyWkHoDE)).

The window shows it at once: take a town for a faction (on the Edit / New faction tab or by clicking it on the Map) and its
label on the map changes to the name for that faction's culture; the towns list shows the name a town has now.

**All towns' names...** (on the Edit / New faction tab, and **All towns...** in the per-town dialog) shows every town in one
table: one column per culture plus *every other*, the owner, its culture and the name shown now. Sort by any
column, filter by a culture (towns with or without a name for it), by the owner's culture, by the owner
(one faction's towns only), by what waits for Apply,
or search. Double click a culture's cell to type a name in place (Enter keeps it, Esc drops it, an empty cell
removes it). Towns the mod's own campaign script renames are shown grey and are not edited here.

## Make the map 3 x bigger

**Bigger map (x3)...** (on the map's bar, beside the zoom) turns every tile into a 3 x 3 block (both games), in five
steps you look over one by one; towns, armies, resources, the coast, heights, rivers, the map's pictures and the
campaign's scripts follow. The window, its steps and values, and what each file becomes: [[Bigger map x3]].

**Map from zero...** beside it puts a small new map in the campaign's place - an island, a region with its town,
a port and a resource, a faction and the rebels, or as many regions and factions as you ask - to grow yourself
(a backup first; Restore puts the old map back). More in [[Reference]].

The map's real size is shown under the map, bottom left.

**Save picture...** under the map saves the whole map as it is drawn now - the layers, colours and borders that
are on, 8 pixels a tile, not the signs - as a PNG or TGA picture (for a forum post or a plan).

## Mercenaries by region

**Mercenaries:** **Mercenaries** (top row), or a right click on the map > **Mercenaries for hire in <region>...**, shows who is for hire where (`descr_mercenaries.txt`), in two tabs. **For hire in a region** (the right click opens it on that region) makes the region's list the way a garrison is made: the mercenaries' cards on the left - a click adds one - and the units for hire there on the right - a click picks one for its numbers, a right click takes it out. A region shares its list with the other regions of its pool; the tab says which, and **A list of its own** takes the region out of the pool with a copy of the list (a region in no pool gets its own list with the first card). **Pools** - a pool is a group of regions that share one hire list. Pick a pool: its regions are selected on the map (Select switches on, they show yellow), so they are changed the map's own way - a box adds, Shift + box takes away - and **Take the map's selection** gives the pool exactly that (**Add the map's selection** only adds). **New pool from the map's selection** (also the map's right click with Select: **New mercenary pool from the selected regions...**) makes a pool of them; a region stands in one pool only, so it leaves its old one (a pool left without a region goes). Each unit for hire shows its numbers in plain words - how many at the start, at most, how fast they come back (one every N turns), the price, the experience, and in Medieval II the years, religions, crusading and events it needs; pick one to change them, **Add** another mercenary of the mod (units with `mercenary_unit`), take one out, rename or delete a pool. A mistake the game would stumble on is said in red; every change waits for **Apply changes** by itself (the changes go into the session's list; **Apply changes** in the main window writes them with everything else waiting - one backup set, **Undo this write** puts them back); lines not changed stay as they were.

## Rebels

**Rebels** (top row, beside Mercenaries), or a right click on the map > **Rebels in <region>...** (with Select on:
**Rebel type for the N selected region(s)...**), shows who rises when a region revolts. Each region names a **rebel
type** (`descr_regions.txt`); a type lists the units the game raises for it (`descr_rebel_factions.txt`) and the name
players read (`text/rebel_faction_descr.txt`); brigands and pirates are types too. Two tabs:

- **Rebel types**: the types on the left (a search box above), the picked one on the right - the name players read,
  its kind (`peasant_revolt`, `brigands`, `pirates`, `gladiator_revolt`), the chance, the text key and its units
  (**Add** one from the list - the rebels' own units first; a right click takes one out; the same unit twice is raised
  more often). **New type...**, **Copy this type...**, **Rename...** (its regions follow) and, set apart, **Delete
  this type...** (its regions get the type you pick in its place). **Show its regions on the map** selects them.
- **Regions**: every region with its town, owner and rebel type, a filter by faction; pick rows (Ctrl / Shift + click,
  or **Pick the map's selection**) and **Give it** a type.

A mistake the game would stumble on (a unit the mod lacks, a type with no unit, a name of two words) is said in red;
every change waits for **Apply changes** by itself, which writes it with a backup; types not changed keep their
lines byte for byte. Without REX / M2EX a type takes up to 20 unit types (said); with them, no limit.

## Grow or cut the map at its edges

**Change size...** beside the map's size under the map adds rows or columns of tiles at any edge - left, right,
top, bottom - as deep sea (the map's own deepest water, in every picture: regions, heights and `map_heights.hgt`,
ground, climates, features, fog, roughness, the campaign's `disasters.tga` and radar maps when they are the map's
size), or cuts them off with a number below 0. **Drag the edges on the map itself**: while the window is open the
map's edges are an orange frame with a grip on each side - drag one out and the new sea shows blue, drag it in and
the part cut off shows dark; the window's numbers follow the mouse (typed numbers move the frame too). Paint land on
the new water with Coast & heights' *Land and sea*.
Towns, ports, armies, agents, resources, forts, events and the campaign's scripts move with the map (grown at the
left or the bottom, every place moves by as many tiles); distances and rectangle sizes in scripts stay.
`descr_terrain.txt` gets the new size and `map.rwm` goes. What stands on the part cut off - a town, a port, an army,
an agent, a fleet, a resource, a fort, an event's place or a script's tile - is ringed red on the map and named in the
window as soon as the edge moves. **Set this size** then asks first: *Keep the cut for Apply* takes them off with
the cut - a town goes with its region from every file (the part of its land that stays goes to the common
wasteland - nobody's land - with REX / M2EX, or to the neighbour region with the original game; land with no region
would stop the game), armies, agents, fleets, resources, forts, watchtowers, events placed there and the rebels standing there are
deleted, and family members (the leader, the heir, the family tree) are never deleted: they move to the nearest town
their faction keeps. **A faction left without any town leaves this campaign** with all its people - its place in the
faction lists, its diplomacy, its victory conditions and the events that make it rise go too - but it stays in the
mod (its units, pictures and other campaigns keep it), as both games' own prologue campaigns leave most factions out.
**Nothing is written until Apply changes** (bottom left): the cut is made at the write, after every other change
waiting, so you can still move what you want to keep off the cut part, or give such a faction a town that stays (right
click a town > *Give this town to*) - then it stays in the campaign and its family moves into that town. *Not now*
keeps nothing. What cannot go is said before any question: a region a faction rises in by an event, a family member
whose faction keeps a town but no room near it. Lines of the campaign's scripts that name a town or region cut are
commented out as when deleting a town (Medieval II's right edge with Baghdad and Mosul can be cut); lines that name
tiles, a condition naming a town cut, or the faction leaving are listed to change by hand. One backup; **Undo this write** (beside the status line)
or Tools > Restore a backup gives it all back. Places in the scripts (Lua / Squirrel too) that would fall on the cut part
move in to the new edge, except lines with a condition naming a town that is cut (listed).

## Scripts on the map

**Layers > Scripts (the tiles they name)** puts a small parchment scroll on every campaign-map tile the scripts name:
the campaign's scripts (`campaign_script.txt` and the script `descr_strat.txt` names - spawned armies and characters'
`x, y`, `move`, `reposition_character`, the camera, `reveal_tile`, 'near a tile' and 'in a rectangle' conditions) and
the Lua / Squirrel scripts beside the mod. The scroll sits at the tile's upper right corner, so the town or army on the
tile stays seen; several on one tile stand side by side. The mouse on one shows its file, line and text.

- **Drag** a scroll to another tile: that one number pair of the line changes (a distance or a size stays as it was).
- **Double click** a scroll: a window over the map shows the lines round it (its command, as far as the blank lines) -
  edit them as text, **Keep** holds them, **Put back as in the file** gives the file's own lines back.
- **Right click a town > Scripts of ...**: every script line naming its tile, the town or its region by name - one
  click opens it in the same window.
- A changed scroll has a blue edge, one off the map a red edge. Nothing is written until **Apply changes**; Undo / Redo
  and Preview work as for the Map's other changes.

## Wonders (Rome)

The wonders (`landmark` lines of `descr_strat.txt`) show as golden pyramids - drag one;
a double click (or the right click's *about it*) opens its window as the game shows it (picture, title, what it does,
descriptions), with **View it in 3D**; the right click on free land has **Put a wonder here** - one of the game's
seven: Rome's exe and REX know no other types ("dont recognise this wonder type"), so a new wonder is one of them,
its model, picture and texts changed if you like -, on a wonder **Delete from the map**.
