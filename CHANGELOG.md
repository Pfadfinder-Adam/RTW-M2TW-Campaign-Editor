# Changelog

## Unreleased

### Added
- **The campaign-select map and the leader's face on the faction tab**: Edit faction and New faction show them
  beside the description, as the game's start screen does - each with Replace..., Save a copy... and Keep the
  current one (Preview, then Apply writes it). A faction without one says so (in Rome only a faction with a
  `leader_pic_<faction>.tga` shows a face there). The Art tab's list no longer repeats them.
- **Avoid Growth on Rome's town scroll matches Automanage closer**: the tick is stretched over its box as the game's
  own (it looked narrower), the box 1 px narrower on the left (it stood out), every place counted with one rounding,
  and its size and place follow the scroll's own governor panel - so it stays with the scroll at any screen size.
  Load offers to update the add-on in the game.
- **The top row by topic, shorter names**: **Maps** · Bigger map (x3)... | **Factions** · Recolour... |
  **Settlements** · Many towns... · Mercenaries... | **Units** | **Buildings** | **Characters** · Traits and
  retinue... | **Religions** | **Add-ons** · Module builder... · Campaign rules... · Events... - each tool beside its
  work, a thin line between the topics (once Map editor, Faction editor, Unit editor...).
- **Settlements is a work of its own, with the names by culture in it**: every region and its town - the names in
  the files, the names players see, the owner, the owner's culture, the name shown now - and one column for each
  culture (drag the table sideways to see them all); double click a culture's cell to type the town's name for it.
  Filters by culture, by what is set, by the owner's culture. The separate Culture names... window is gone.
- **Factions opens faster** when you come back to it: its kept work is put back without reading the faction's
  files again.
- **Calmer coloured buttons**: Start the game, Discord, YouTube and Ko-fi a fifth less bright and saturated - they
  glowed too much.
- **The map is the Map editor's alone**: the Faction editor has no Map tab any more. A faction's towns are picked
  with **Towns on the map...** (under Capital): the Map editor opens, a click on a town adds it (yellow ring),
  another takes it out, **Done** brings you back to the faction - nothing you typed is lost. **Capital on the
  map...** the same for the capital: one click and you are back. New armies, agents and fleets: in the Map editor
  (right click the map, for any faction - a new faction once it is created); a double click on one of the faction's
  armies in Units & armies opens the Map editor on it. The map's colour mode *Diplomacy (towards the faction)* went
  with it.
- **Settlements...** moved from the faction's tabs to the top row: every region and its town in a window of its
  own - the names in the files and the names players see, the owner, names by culture.
- **Fix: the Shore line showed on the Terrain tab** when zoomed in - it belongs to **Coast & heights** only (its tick
  there), and switching tabs now turns it on and off.
- **No scrollbars**: every list, table, page and read-only text scrolls by the mouse wheel, by **dragging** it with the left button (it follows the mouse, up / down and left / right) and by the **middle button**: press the wheel and move the mouse - the further from where you pressed, the faster it scrolls, both ways (held: it stops when you let go; a click: it goes on until the next click or Esc).
  A text you can type in keeps the left drag for selecting words. The map is as before (the right button moves it).
- **Fix: a right click on the map crashed** ('dict' object is not callable) and the context menu did not open -
  a newer field had taken the name of the map's own check of where a click lands.
- **One Faction editor**: New faction and Edit faction are one button at the top now - **Faction editor**, with
  its first two tabs **New faction** and **Edit faction** (the old Faction tab renamed; the editor opens there),
  in the same row and look as Units & armies, Buildings... - no row of their own. One button less in the top row. **Switching never drops
  work**: New faction and Edit faction each keep what you did, not written yet, while you go to the Map editor,
  the other side or any other editor, and find it again on the way back (no more 'Switch, drop them').
- **Add-on: Upkeep x 2** (both games, any mod, no engine needed) - every unit's upkeep multiplied (x 2 or any
  number), so only a big income keeps a big army; the game shows the real numbers. Take it out puts back exactly the
  old ones.
- **A faction may start with no town** (Rome with REX, Medieval II with M2EX): Edit (giving its last town away) and
  Delete region (its last town) no longer refuse - the faction gets `can_homeless yes` and lives on with its armies
  and agents (with none left on the map the game ends it). Without an engine it is still refused: the plain games
  crash on a faction with no town.
- **Fewer made-up limits**: Campaign rules' recruitment slots can be changed (its tip says what 0 did in a test);
  a new building chain can have up to 99 levels (the plain games' 9 is still warned); climates can be painted on
  the sea; the arrows of temples, trait levels, ages and trait thresholds go higher (typing any number worked
  before too).
- **Terrain editor: impassable land, always black**: a new ground brush (Rome with REX, Medieval II with M2EX - the
  engines' ground type impassable_shrouded): no army walks there and the land stays black all game, for a
  wasteland's land you want hidden. Towns, ports and characters are refused on it, as on the other impassable ground.
- **A report carries the mod's file list**: with a mod loaded, Report a bug / Suggest adds `mod_files.txt` (a tick,
  on by default) - every file of the mod's data folder and the files beside it, with its size and date and whether
  the game has it with the same size (new / other size). Never the files' contents; the hidden words are cut out
  of it too.
- **New mod folder on the plain game makes a thin mod**: nothing is copied (made at once, no disk space) - the mod
  holds only what you change, the game reads every other file from its own data. The editor puts a game file into the
  mod the first time you change it, and the whole map folder (all but map.rwm, which the game builds again there) the
  first time you change the map. A mod built on another mod (HLR) still holds all of it - the game takes one mod
  folder, never a chain.
- **Recolour into black / white looks like the game's own**: a unit's battle texture made black / white starts from
  the same model's texture of the faction whose colours are nearest (Medieval II: Sicily's grey / white, the rebels'
  grey...) - the artist's own black and white cloth, its folds and the faces kept - and only what still differs is
  recoloured; where no such texture exists the colours are made black / white with every fold kept (a flat black lost
  the folds, white bands came on the faces and black / white patches on the skin - a modder's report). The window
  says which faction's texture a picture was made from.
- **Recolour: an area of like colour in one click** (the touch-ups' new tool beside the brush): a click on the
  'after' picture takes the whole patch of the picture's own colour joined to that point - a hood, a shield's field -
  and paints it the new primary or secondary colour; 'keep as it was' + a click gives an area back; *alike* says how
  far a colour may differ and still belong.
- **The test mod's report puts what to look at first**: the steps that were already seen working in the game (per
  game) are listed as such, the new or changed ones on top - 'look at these in the game'.
- **Your own mod folder first?** Before the first write into the game's own data or a mod the editor did not make,
  the editor asks once: *Make my own mod folder* (nothing is written, New mod folder opens) or *Write here* (not asked
  again for that mod; a backup is made before every write anyway).
- **A deleted town's region can stay as a wasteland** (Rome with REX, Medieval II with M2EX): *Delete this town with
  its region* and *Delete the N selected towns* ask where its land goes - **stays as a wasteland** (the default with
  an engine) or **goes to a neighbour** (as before; the only way of the original exes). A wasteland keeps the region
  and its land but has no town, no owner, no rebels and no economy: the AI never goes for it, no victory counts it,
  no neighbour grows, armies can still walk over it. An island can go too now. The engines' own way (REX's
  `wasteland` keyword in descr_regions), in place of the old trick of a town hidden behind a river ring.
- **The way back**: right click a wasteland's land on the Map - *Give it its town here...* writes its town on that
  tile again (its name, the name players see, its owner; a village as the game makes it), with a backup.
- **Fix: a town (or port) dragged away can be dragged back onto its own tile** - the map refused it as if another
  town stood there; now the move is simply undone.
- **Map size: the minimap follows the cut** (both games): the campaign's minimap pictures (radar_map1 / radar_map2.tga,
  pictures of their own size) are cut or grown in the same proportion as the map - before, the old picture stayed
  and the game drew the real borders over the wrong land. Medieval II's winter minimap keeps its thin blue border at
  the new edge, and new parts take the deep sea's colour (a grown map showed a blue band).
- **Fix: no black band across the map after it is grown** (Medieval II): the fog picture's dark frame
  (map_fog.tga) moves to the new edge instead of staying where the old edge was.
- **Land and sea brush: a smooth coast** - new land's coast follows a smooth curve at half-tile level, the way the
  games' own maps are drawn, instead of tile-sized steps; one-tile islets stay small ovals of land and one-tile
  straits stay open. Every tile stays what it was painted (region, town, port).
- **Land and sea: the shape brush - a coast drawn where you want it, smooth in the game**: the game cuts every
  square of four heights points into two triangles and lays the water at height 0, so a coast whose heights are the
  same numbers everywhere can only run in steps of 90 and 45 degrees (a stepped bay or island in the game). The
  shape brush keeps the coast as a shape: round, not tied to the tiles, and the heights near the water set by
  their distance from its edge on one slope - the game's shore falls on the edge you drew; the exact heights go
  into map_heights.hgt. Tiles follow by their middles (new land joins a region), the ground point by point (shallow
  water along the shore), a town, port, character, fort, resource or river keeps a little land round it.
- **The map by points and the Shore line**: while a point brush is picked the Terrain map shows map_heights point
  by point, each point centred on its place; close up a light line shows the shore exactly as the game will draw
  it (Shore line, on by default).
- **Land and sea: 'Smooth the coast' and the coast pen** - 'Smooth the coast' rounds the coast under the brush as
  a shape (the longer you hold, the smoother; tiles follow, towns keep their land); the coast pen draws the coast point by point on the heights
  (land point / water point), the way modders draw it by hand - the map is shown point by point while it is picked
  (land grey, water blue), and touching a tile's middle turns the whole tile with its region. The ground of every
  point follows, so no land texture on the water and no holes in the land.
- **Land and sea: find ground on the wrong side of the coast** - a button under the Land and sea brushes finds every
  point where `map_ground_types.tga` and `map_heights.tga` disagree: a land ground on the water (the land's texture
  lies on the water in the game) or a sea ground in the land (holes of sea), rings them on the map and says how
  many of each. On a yes each point takes the ground round it on its own side - the heights lead and are not
  changed; kept until Apply, Undo stroke takes it back. The games' own maps have next to none (Rome 0, Medieval II
  18 by lakes in the hills).
- **The minimap follows painted land, sea and ground**: on Apply, the campaign's minimap pictures (radar_map1 /
  radar_map2.tga) are drawn again on every tile whose land, sea or ground you changed - from the nearest tile of the
  same ground (a forest from a forest, the sea from the sea), so its look and season fit. Needs Pillow (else a note).
- **Fix: the brush's outline follows the mouse while painting** with the button held (it stood still).
- **Map size**: a cut that takes a town off deletes its region from every file, and nothing more - the part of its
  land that stays on the map is left as it is, given to no one; the question before the cut and the result name it,
  and you paint it into the regions you want (Edit regions). The cut no longer refuses a town whose land left
  touches no other region.
- **Map size: a cut that takes a faction's last town takes the faction out of this campaign** (both games), after a
  question that names it - its people, its place in the faction lists, its diplomacy, its victory conditions and the
  events that make it rise; it stays in the mod (its units, pictures and other campaigns keep it). Script lines naming
  it are listed to change by hand. It was a refusal ('... would keep no town').

### Changed
- **Terrain editor: the Heights brush in even sizes too**: size n is now n points of the heights picture across,
  round and snapped to the points like a pixel-art pencil - 1 one point, 2 a square of 2 x 2, 3 a 3 x 3, 4 a round
  4 x 4 (before: only 1, 3, 5... points across). The outline under the mouse shows exactly the points it takes; the
  brush goes up to 24 (the old 12 was 23 points across).
- **Map editor: a Coast & heights tab beside Terrain**: the Terrain panel had grown too full - Terrain keeps Ground,
  Rivers / cliffs / volcanoes and Climates, the new Coast & heights tab has Land and sea and Heights (one editor in
  two tabs: the strokes, Undo / Redo and Apply are shared). The Map tab's own switches (Layers, Colours, Edit
  regions, Select, Merge regions, Legend, Find) are no longer shown over the terrain's map - nothing of the map's
  towns or armies is worked there.
- **The test mod's special building** (Rome with REX, Medieval II with M2EX - the engine way of putting a model on the
  map): a click on it now opens its own window (its title, picture, text, what it gives and who holds it), and the
  region's owner gets 100 every turn - a first try of special buildings of one's own; the game's log says which of
  the engines' calls worked.
- **README**: a quick start, what it works with, what is new, the features at a glance (the long list folds away), a
  short FAQ.
- **Faster on a big mod** (a tester's HLR, 749 regions): deleting 48 towns at once took about 21 seconds before the
  window could write - every file is now read once for all of them (1.6 s); the town window opens about 5 times
  faster (its garrison cards are made when the Garrison tab is first shown, one town is read instead of all of them)
  and its first look never lays 500 unit cards out in one column.
- **The town window is smaller** (960 x 680 at first instead of the screen's height) and opens at the size it was
  last left at.
- **Map size waits for Apply**: *Keep for Apply* puts the cut in the list of changes waiting; Apply changes writes it
  after every other change, so a town given on the Map meanwhile counts - a faction that gets a town that stays keeps
  its place, its family moves into that town. The window opens with other changes waiting too (it refused before).
  Undo this write / Restore give the old map back.
- **A new version of the editor is seen at once**: the editor looks on GitHub on every start, and again every 6 hours
  while it stays open (it looked at most once in 6 hours, only on start - a release made after the day's first start
  was not seen that day). The GitHub button turns **green** with the new number (`GitHub (new 0.34)`) and opens that
  release's page.

### Fixed
- **The test mod's own building on the map: its window's text ran past the window's edge** - the lines are now cut
  to the window's width as the engine measures them.
- **The test mod's Upkeep x 2 step failed in the exe** ("No module named upkeep"): the exe now surely carries it,
  and its own self-check tries every add-on's code.
- **Add-ons: a click on Upkeep x 2 crashed the page** ("can only concatenate str"): it now shows like the others -
  it needs nothing, no engine (it changes the mod's own files).
- **Map editor: towns whose garrison has no captain showed no army** (a big Medieval II map writes every garrison so,
  the rebels' too - `garrisoned_army` with its units inside the town's own block): such a town now shows the army
  flag on its roof like any garrisoned town, and the line under the map says how many units its own garrison has.
  The town window already showed them.
- **Terrain editor: the coast's brushes at size 1 showed a square on the points' grid**: the shape brush, Smooth the
  coast and the coast pen at size 1 now show their circle round the mouse, as at every other size - what they take
  is centred where the mouse is, not on the nearest point. And after the shape brush or the pen, picking Heights
  without the map being drawn again kept the coast's brush on the mouse - now the Heights brush is on at once.
- **Add-ons: 'font autoscale: game font ...' in the script console** (Medieval II with M2EX; Rome with REX the same):
  the add-ons' button, tick and box now draw a game font at the size the game baked (font scaling off on their own
  canvas, as the engines ask), so the warning is not written and no text of theirs is scaled.
- **Add-ons put in by an earlier version stayed old**: Update it brought one add-on up to date at a time and nothing
  said which ones were old (an older Avoid Growth could draw the script console in its own font). Now Load finds every
  add-on in the game that is not what this version writes with the same settings, names it, and offers to put them
  in again (one yes, their settings kept, a backup first); the Add-ons list marks them **(old)**.
- **Terrain: the map by points sat half a point off** (each heights point drawn beside its place, the brushes
  aimed to match): every point is drawn centred where it lies - a tile's middle point on the tile's middle.
- **Terrain: the Ground brush laid its ground over the coast**: a tile's ground is the 3 x 3 block of points round
  its middle, and on the coast that block reaches over the waterline (the heights' coast runs between the tiles) -
  a land ground painted on a coastal tile lay on the water, a sea ground made holes in the land. The brush now paints
  only the points on its own side of the waterline. Undo of a ground or climate stroke gives every point its own
  colour back (it gave the whole block the tile's middle colour).
- **Terrain: the beach is land**: both games lay the beach on the land tiles along the coast (every one of them in
  both vanilla maps); the editor had it as a sea brush, painted on sea tiles - sand on the water. The beach is now
  among the land brushes and goes on land, inland too.
- **Map size: a cut that left a town on the map's new edge** made the game stop while loading (it builds the map
  again and cannot place a town on the edge row - it needs land all round). A town or port that would stand on an
  edge the cut makes now counts as cut off: it is named in the question before the cut and goes with it (its land
  that stays is left for you to paint into a region), or move it one tile in first.
- **Place its town / Place its port for a region of the map** (Edit regions): they worked only for a new region and
  said 'pick a new region first'. Now, for the region in *Paint with*: a **wasteland** gets its town on the tile
  clicked (the same window as its right-click *Give it its town here*; its port after that), a region's town or port
  **moves** there (kept for Apply, as a drag on the map would).
- **Deleting a region left its block in descr_strat's regions section** (roads, forts, watchtowers - Barbarian
  Invasion has 16): a region given to a neighbour now hands its forts and watchtowers over to the neighbour's block;
  a wasteland's block goes (the game takes forts and watchtowers only in a region with a town).
- **Check mod files**: no false alarms on building levels with a '+' in their names (`grain+1`) or on upgrades with
  conditions (`fleet_arsenal requires factions { roman, } ...`) - a tester's HLR showed 72 of them, now none. A
  wasteland region without REX / M2EX beside the game is said.
- **Map size**: a cut over the rebels stopped with '... is not a character of slave' when a rebel general stood in a
  rebel town on the part cut off (the town went with its garrison, then the general was looked for again). The
  rebels' characters on the part cut off now simply go with the cut, generals too (they have no town to keep).

## 0.33.0 - 2026-10-08

### Added
- **Merge regions** (a switch on the map's bar, both games): only the regions and town names drawn; click the region
  that stays (yellow) and its neighbour that goes (red), then **Merge them** - the second region and its town go from
  every file, all its land joins the first, which stays as it is. One write with a backup per pair; the switch stays
  on for the next pair. For maps with more regions than wanted.
- **Delete many towns with their regions at once** (both games): with Select on, select the towns on the map, right
  click > **Delete the N selected town(s) with their regions...** - one window lists each town and the region its
  land goes to (the neighbour that stays it shares the longest border with; a region ringed only by regions deleted
  with it follows them). The map shows them: red = goes, yellow = takes land; pick a row (or click a red region) and
  its neighbours that could take its land turn green - click one to give it the land. One write, one backup, one Undo.
- **Delete this town with its region** shows the choice on the map: red = the town's region, yellow = the region that
  takes its land, green = the other neighbours - a click on a green one gives it the land (the list in the window
  follows). The window stands beside the map, the whole map in sight; the mod's files are read once (they were read
  three times - slow on a big mod).
- **Map size: drag the map's edges** (Change size... under the map, both games): the map's four edges become an
  orange frame with a grip on each side - drag one out to add rows or columns of deep sea (shown blue), in to cut them
  off (shown dark); the window's numbers follow the mouse, and typed numbers move the frame. What stands on the part
  cut off - a town, port, army, agent, resource, fort, an event's place or a script's tile - is ringed red on the map
  and named in the window. **It goes with the cut, after a question** (*Delete them and cut* / *Not now*, to move
  things first): a town with its region in every file (the part of its land that stays joins the neighbour region
  that stays), armies, agents and fleets, resources, forts and watchtowers, events placed there; family members are
  never deleted - they move to the nearest town their faction keeps. What cannot go is said before any question and
  nothing is written: a faction's last town, a town or region the campaign's script names, a family member with
  nowhere to go. Script lines that name tiles there are listed to change by hand. The window stands beside the map,
  the whole map in sight.
- **A religion from nothing** (Medieval II, Barbarian Invasion): New religion needs no other religion any more - its
  symbol drawn by the editor (its first letter on a disc of the colour picked, in the game's own size; Barbarian
  Invasion's order / unrest pips: the same full-size symbol with the game's own green / red arrow laid on it) - and **Temples of its own** makes a temple chain
  for it from nothing: the mod's usual temple numbers, Medieval II's `religion` line / Barbarian Invasion's
  `religious_belief` naming the new faith, built by the factions picked, plain pictures drawn.
- **A building from nothing** (both games): New building step by step > Start from: *Nothing*. Say what it is for
  (soldiers, money or food, order and learning, a temple, something else) and how many levels; each level's town
  size, cost and turns start at what is usual for such buildings in this mod, with the effects most of them have.
  All levels side by side: change any number, add any effect this mod's buildings use (in plain words), take one
  out with the right button; the units it trains from a level on (only those its builders may own); names and
  texts; pictures of your own or plain ones drawn for every culture that builds it (Medieval II: the small
  construction-queue picture too).
- **A unit from nothing** (both games): New unit step by step > Start from: *Nothing*. Say what it is (foot soldiers
  who fight hand to hand, with spears, or who shoot; horsemen who charge or who shoot) and the editor writes every
  line itself in the form this mod's units of that kind have, each number starting at what is usual for such a
  unit in this mod (the middle of them, the mod's lowest and highest shown beside it). Then its model and mount,
  owners, the building levels that train it (first guess: where such units are trained most), and its pictures -
  plain cards with its initials are drawn when you have none.
- **Your own files for a battle model** (Unit editor > Battle model > **Your own files...**, both games): a texture
  you made elsewhere for every faction or one faction (PNG, TGA, DDS, JPG - made the game's form: Rome `.tga.dds`,
  Medieval II `.texture`), Medieval II's weapons and shields texture, and the model file itself (Rome `.cas`,
  Medieval II `.mesh`; several files = its detail levels). The editor names and places every file and writes the
  lines; when other units share the model, the unit gets a model of its own (a copy) so they keep their look.
  Preview first, a backup, Undo this write / Restore takes it all out. Nothing is drawn by the editor.

### Changed
- **A region with no town of its own** (the game makes a rebel village there by itself): its town window is a short
  note as big as its words (it was a window the size of the screen) with an owner to pick and **Write its town** -
  the rebels too (the village as the game makes it, in the look of the faction descr_regions names as its builder)
  or any faction; after Apply it opens like any town (buildings, garrison). Written with the next Apply, as the
  Map's *Give this town to*.
- **Edit region... shows the owner** (who holds the town at the start, descr_strat.txt) beside the region's own
  lines; a change is written with the next Apply, as the Map's *Give this town to*; a region with no town gets its
  town written there (the rebels too).
- **Sack Settlement (Medieval II)**: the Raze Settlement button's words in the game's own Verdana (they were in a
  Times face), no words under the mouse (the game's three buttons have none), and the capture scroll is made one
  button taller so the 4th button stands inside it, not on its bottom edge; if the game keeps the scroll's size, the
  button stays under Exterminate. **Avoid Growth (Medieval II)**: its words in the game's Verdana too. Put them in
  the game again (Add-ons > Update it) to have the new look.
- **Start the game** names what it starts: *Start Rome - CE_Test*, or in amber *Start Rome - no mod* when the
  game's own data is loaded (the game started the plain campaign right after a test mod was made, and it looked
  like the test mod). **Tools > Test mod** offers to load the new test mod and start the game with it.
- **Module builder (Blocks look)**: every block has a small **✕** that takes it out, and a line under the module
  says the three ways (✕, drag it back to the left, right click its dots) - taking a block out was found only by
  guessing.
- **Load** says when a mod lies in another folder than its own start script / `.cfg` look for (a mod unpacked into
  'New folder' while its files say `mods\kirsi_biggermap_medieval2`): the game would not find it - rename the
  folder. Start the game refuses it in the same words.
- **Delete this mod's folder** asks once more about a mod that was never started in the game (no saved game, no
  game log naming it).
- The test mod's Module builder modules act only in a campaign that has the test faction - they lie in the game's
  `script\modules` and gave a plain campaign's towns the test's people. A module can be made so ('only in a
  campaign that has the faction ...').
- **Module builder: WHEN 'the player's turn starts (once a turn)'**, and new modules start with it. The old 'a
  faction's turn starts' is now called **every faction's turn starts**: it comes once for EACH faction, about twenty
  times a round - a module on it without 'the faction is the player' acted for every faction. The examples 'Help
  when broke' and 'A message on turn 10' use the new one.
- **Test mod**: its Module builder modules act on the player's turn; the control blocks module gives the towns
  100 people once, on turn 2 (it gave them every turn, for every faction); the game condition has a module of its
  own, and a short script tries it in several forms once and writes each to the game's log ([CE_CONDITIONS]) -
  the engines refused 'I_TurnNumber >= 1' and wrote that thousands of times; the script does nothing outside the
  test mod.

### Fixed
- **Add-ons (Sack Settlement, both games; Avoid Growth): the game's script console and other script texts turned
  into another font** after the add-on had drawn - a font it opened could stay open when its drawing failed, and
  everything drawn after it took that font. Every font the add-ons use is now closed by the game itself, whatever
  happens. Put them in the game again (Add-ons > Update it).
- The town window of a region with no town of its own (a rebel village the game makes by itself) failed when it was
  closed ('TownWindow' object has no attribute 'town'). It closes now.
- **A town's own garrison, with no captain** (both games): a garrison written inside the town's own block -
  `garrisoned_army` with its `unit` lines, a form both games' engines read and some mods use for every town - was
  not seen: the town window, Units & armies and Many towns showed no garrison. It is read now, shown as the town's
  own garrison and changed in place (no captain is added; an emptied one goes whole, as the game refuses one with no
  unit); a new faction taking such a town gives it its own units there; Check mod files names unknown units in it and
  an empty `garrisoned_army`.
- A town with no army at all showed simply no garrison. Its Garrison view now says the town starts empty and names
  who stands beside it, outside the walls (drag him onto the town on the Map to make him its garrison).
- A rebel garrison for a new town on a map with hundreds of rebel towns was refused when every first name of the
  rebels' name list was taken ('no free name for a rebel captain'). The captain now takes a first name with a
  surname of the same list.
- **Map size** said a refused cut only in a line at the bottom of its window, and nothing on the map: a cut over a
  town or an army looked as if it was written and did nothing. It is said in a message now, written in the editor's
  log, and what is in the way is ringed red on the map.
- **Recolour never writes over the original battle texture**: the original is copied, the copy recoloured and put
  in the mod, and the faction's model line points at it - also for a texture only that faction wears, when it is a
  file of the game's install (it was recoloured where it lay). A copy made for the faction before is recoloured where
  it is.
- **Men like bare skeletons in battle (Medieval II)**: a faction that had a unit's texture but no weapons / shields
  texture (`texture_attachments`) got none when it was recoloured or given the unit again - only a faction with no
  line at all did. It gets the missing line now, and Load offers to give it to every such faction of the mod at once
  (Check mod files names them, the battle_models.modeldb too).
- A picture of your own given in New unit / New building step by step stopped the write (its size came with the
  colour depth); it is put in at the size wanted now.
- A copied building chain now has the chain's own name text (`{<chain>_name}` - Medieval II logged 'localised string
  ... does not exist') and, in Medieval II, its small picture in the construction queue.
- **Unit cards and building pictures are the ones the game shows**, in every window (the Unit editor's boxes, the
  hover cards, the garrison cards, the previews, Mercenaries): a unit's card comes from a faction that owns it (or
  the mercenaries' folder), never from `ui/units/construction` - the recruitment queue's small whole figures were
  shown as cards - and none found is said plainly. The Building editor opens a level on a culture that builds it
  (despotic_law opened on barbarian: no picture, the game's 'WARNING!' stand-in texts); a culture that never builds
  it is marked so in the list and says why; the hover card names whose picture it shows.
- **Plain Rome (also with REX): no faction that comes later.** A faction that starts dead
  (`dead_until_resurrected`) made the game stop reading `descr_strat.txt` at that line, with no error in the log:
  every rebel town stood empty, the diplomacy was lost and the faction was killed as the campaign loaded. Only
  Barbarian Invasion and Medieval II read it, so on plain Rome New faction / Events offer only *on the map*; Check
  mod files names such a line and Load offers to take it out.
- **Avoid Growth**: its tick shows only on the **Construction** tab of the settlement scroll (it stood on
  Recruitment, Repair and Retrain too); in Rome its words and box look like Automanage's (the same grey, the box as
  wide and in the same column), a little lower so the two never touch.
- **Forts and watchtowers** are not put right beside a town or another fort / watchtower: the game skipped a
  watchtower placed next to a fort ('positioned on an invalid tile'). A wonder may still stand beside a town.
- **Terrain tab**: painting again right after Apply showed "'NoneType' object has no attribute '_optional_map'"
  (the tab kept no files after the write). The tab reads the new files at once now.
- **Map**: putting ports on the map for regions that had none could show "'NoneType' object is not iterable"
  under the mouse; also when such a port and a moved town were written together.
- **Add-ons**: an add-on's own file lying in the game's `script` folder outside `script\modules` (an older copy
  put there by hand) made Put it in refuse ('it would run twice') and the page said 'Not put in yet', with no
  way to take it out. The page now says where the old copy is; Update it moves it to `script\modules`, Take it
  out takes it away (with a backup). Code pasted into another script file (a mod's main.nut) is still refused.
- A refusal in plain words is written into the editor's log as one line ('Refused: ...'), not as an error with
  a long trace.
- A garrison for a faction with no men's names in descr_names.txt says what to do (add names there, or leave
  the town without a garrison).
- Closing the editor could end with a Windows error box ('Unhandled exception in script ... application has been
  destroyed'). Closing never fails now, and a fault while the editor closes goes only into its log.

## 0.32.0 - 2026-10-07

### Added
- **Module builder: control blocks** as in Scratch - **ELSE** (what the module does when the IF does not hold), the IF lines counted as **all / any one / none** of them and **not** before a line, and **FOR EACH** town or army of a faction, or each faction (everything below done for each one in turn). Older modules open and work as before.
- **Module builder looks like Scratch** (Look: Blocks): the kinds of blocks in coloured groups on the left (events, control, conditions, actions), the module on the right as blocks that fit into each other - the WHEN block on top, FOR EACH and IF / ELSE holding their actions. Drag a block into its place (a line shows where) or click it to add it at the end; drag a block of the module to move it, or back to the left (or right click it) to take it out. **Look: Lists** keeps the old view of the same module.

## 0.31.0 - 2026-10-07

### Added
- **Edit faction > Rename...**: the faction's code name changed in every file of the mod in one write (pictures copied under the new name, scripts that name it listed); Undo this write puts it back.
- Hover a unit or a building in any list or table: its card shows - the picture the game shows and what it is (men, cost, upkeep; a building's level, cost and turns).
- A click on a table's column heading sorts the rows by it, a second click the other way.
- **Tools > Settings > Folders > Delete this mod's backups...** (after a question).
- Load says what it is loading, with the moving bar.

### Changed
- **One write for the session - every window**: Mercenaries, Events, Campaign rules, Traits and retinue, Many towns and Recolour keep their changes for Apply too (**Keep for Apply**), as the town and character windows do; one **Apply changes** writes them all, **Undo this write** takes back the last part or the whole write. (Traits' *New...* still writes at once: a new trait must exist before it is edited.)
- **Mods that hold only the files they change load** (Medieval II `mods/<name>`, REX `-mod:<name>`): every file the mod lacks is read from the game's own data, as the game reads it; the Mod list shows them too. A change to such a file goes into the mod as its own copy - the game's files are never written - and Restore takes the copy away again. The engines' `descr_ex.txt` / `descr_caps_ex.txt` are still read from the mod alone. Medieval II with its data still packed: Load says to unpack the game first.
- One language in every window: **Preview** shows what will be written, **Write it in** writes at once, **Keep for Apply** keeps a window's changes for **Apply changes**. Enter presses the window's main button and Esc closes it (Cancel / Close), in every window; the main window is never closed by Esc, and a tool waiting for its click on the map is stopped by Esc first.
- Questions are answered in words, not Yes / No ("Drop them" / "Stay", "Unpack it" / "Not now"...); a button that loses something stands apart on the left and is never the one Enter presses.
- Fewer questions: a write that can be undone (**Undo this write**) is no longer asked about unless it has a warning; removing an army or agent from the faction's list is undone with Ctrl+Z.
- The right mouse button takes things out of a list: a mercenary's card or line (Mercenaries), an army / agent / fleet (the faction's list), an event (Events), a trait or a member of the retinue (the character) - the separate Remove buttons are gone.
- Long explanations at the top of Mercenaries, Map size and the 3 x bigger map are one line now; the rest shows on the '?'.

### Fixed
- Backups that were put back (Restore, Undo this write) stayed in `CampaignEditor_backups` as `*_restored` folders, one per undo. They are deleted now, and the ones older versions left are taken away when the mod is loaded.
- **Change size...** under the map did nothing on the Terrain tab; it opens the Map size window from every map now.
- The family member's diamond on a flag was always white; it takes the colour that reads on the flag (dark on a light flag, light on a dark one), like every other mark.
- Sending a report shows the seconds while it goes (with pictures it takes up to a minute - it looked stuck) and gives up after 90 s with the offer to save the zip.
- The Mod box and the data folder box at the top are the same width.
- Medieval II: diplomacy at the start reset for every faction (all neutral) after an edit of a faction's feelings - Rome's form of the lines (`core_attitudes`, a number on `faction_relationships`) was written, which Medieval II does not read. Each game now gets its own form (`faction_standings` -1.0 .. 1.0 in Medieval II, and the other way in Rome). Lines older versions wrote so are named by Check mod files, and Load offers to rewrite them.
- Medieval II: new texts (an event's title, a new building's or temple's name) were not shown in the game - it reads the compiled `<name>.txt.strings.bin` beside a text file instead of the file. A write that changes a text file now takes that `.strings.bin` away (backed up; the game builds it again from the text).
- Module builder messages showed the game's 'picture not found' placeholder: the picture line of a message (`<id>_image`) is now written too (the messenger picture every culture has).
- Barbarian Invasion: a deleted region stayed in the campaign's bad-harvest list (`descr_harvests.txt`, 'cannot find this region name'); its entries now go with it.
- Barbarian Invasion: a new watchtower was written beside the nearest one even when that one belongs to another region, and the game skipped it ('does not match up to region name'). A new or moved one now goes under the block of the region its tile lies in.
- Sack Settlement (both games): a town of the player's that revolted to another faction was taken as the player's own capture. Only a capture by the player counts now.
- New / Edit faction map: a single click on a town did nothing (the town only began a drag); only a double click picked it, and that also opened the town's window. A click picks it now; a double click picks it once and opens the window.
- A storm placed on land never comes - storms strike only fleets at sea. The Events window and Check mod files now say so.

## 0.30.1 - 2026-10-07

### Fixed
- Edit faction on a faction the mod has but the campaign does not (no block in its `descr_strat.txt`): said in plain words what to do (another campaign, or bring it in as a new / later faction).
- Module builder and Add-ons on Medieval II: putting a script into the game refused with 'D:\Medieval II Total War\data holds only the files this mod changes' when the game keeps its data in packs (the usual install). The loaded mod now carries the write and its backup; Scripts in the game the same.
- The set-up problems found on Load: a long list ran off the screen and the window could not be closed. The same problem on many lines of a file is now said once with its lines, a long text scrolls, and the buttons are always in sight (*Put them right* / *Not now*).

### Changed
- **One write for the session**: the town window and the character window no longer write by themselves. **Keep for Apply** puts their changes into the session's list; **Apply changes** in the main window writes everything waiting in one go (the button shows `(+N kept)`), each part laid over the files as the parts before it left them. **Undo this write** then asks: *Undo the last part only* (one step back) or *Undo the whole write*. Closing a window with changes asks *Keep for Apply / Keep editing / Throw the changes away*.

## 0.30.0 - 2026-10-07

### Fixed
- Windows: two writes in the same second could be put back by Restore in the wrong order (the files' own times are too coarse there); every backup now keeps the exact moment it was made. The game's log kept with the editor's logs got every line ending doubled.
- The map: painting land to a region and moving a town or port in the same write kept only one of them (the second change of the regions picture started again from the file); a town or port moved onto land just painted to its region was refused as 'not its land' until written. Both now go in one write.
- Unit cards: a mod folder that keeps the game's own cards showed them as wide name buttons; the cards are now found in the game's data too, a unit without any picture gets a grey card of the same size with its name, and cards of another size sit in the middle of the usual box, so the rows stay even.
- A new region's port: with the map's port sign, a click on the coast of a region painted over another one moved the old region's port there instead of giving the new region its own - it had to be written first. Now the port goes to the region the land is painted to, in the same go.
- **Recolour...** with no faction picked asked for the faction's name to be typed in. Now the window opens on a faction and a list at its top changes it (names players read first); brush changes not written yet are asked about before switching.
- Mercenaries: after a write the window showed the pools as they were before it.
- The editor could stop responding (Windows: 'not responding') a while after start: every window, hover tips included, was made resizable each time it showed, and on Windows that showed it again and again. Now only real windows, once each; hover tips are left alone.

### Added
- **Long work shows it is working**: checking the mod, the test mod and every step of the bigger map run beside the window with a moving bar and the seconds at the bottom - the window never freezes (the x3 heights step took up to two minutes with the window not answering).
- **Nothing is lost by closing a window**: a window with changes not written yet (Mercenaries, a town, a character, Events, Campaign rules, Traits and retinue, the Module builder) asks before it closes - *Write it in*, *Keep editing* or *Throw the changes away* (that one set apart on the left; Enter writes, Esc keeps editing).
- **Undo this write**: right after anything is written, a button beside the message at the bottom puts every file of that write back as it was (the same as Restore on the newest backup).
- **The outline under the mouse shows the brush**: a painting brush outlines its whole square of tiles, the heights brush the one point it changes at size 1 and its circle above that (Terrain editor, region borders); the brush size follows a typed number too, not only the arrows.
- **Heights brush, point by point**: brush size 1 is one point of the heights picture (2 x 2 points a tile), the brush's middle exactly under the mouse (it sat half a point off), a right click picks the height of the point under the mouse (an eyedropper), and the line under the map gives that point exactly - land grey and metres, or water and the sea floor's depth - with what `map_heights.hgt` holds there.
- **Mercenaries...** (top row; right click on the map > *Mercenaries for hire in <region>...*): *For hire in a region* makes a region's list the way a garrison is made (the mercenaries' cards, a click adds one; *A list of its own* takes the region out of its shared pool); *Pools*: the campaign's mercenary pools - a pool's regions selected on the map and changed with the map's Select box, new pools from the selected regions (a region leaves its old pool; an empty pool goes), every unit's numbers in plain words and changeable, mercenaries added or taken out, pools renamed or deleted; Preview and a backup, unchanged lines kept as they were.
- **Where it can be built...** (Building editor) and **Where it is recruited...** (Unit editor): windows of their own - the regions whose land lets a level be built (counted from the goods and tags its requirement asks for; NOWHERE in red), and every building level that recruits a unit with its pool in plain words, its requirement, the regions it applies in and a button to that building.
- **Region tags**: taking a tag (hidden resource) off a region first lists what stops working there - the buildings and recruitment that ask for it, with their lines.
- **Character window** from the map: right click a general, a family member, the heir, the leader or an agent > *Edit this character...* (a double click on an agent too) opens the Character editor on him in a window of its own, with Preview / Write it in, as the town's window does.
- **Save picture...** under the map: the whole campaign map as it is drawn now (layers, colours, borders; 8 pixels a tile) saved as a PNG or TGA picture.
- **Find** on the map matches the names players read in the game (the campaign's region and town labels) besides the file names; a town comes before its own port.
- **Check mod files** checks the shape of the building tree: a chain named twice, a level the `levels` line names without a block of its own, an `upgrades` to no level of its chain, a `convert_to` to no chain or past its levels, a `building_present(_min_level)` that names no building or level (it can never be met) - each with its line.
- **Check mod files** with a faction picked: *Is it complete?* - every file that names every other faction but not this one, with a faction of the same culture to copy from (measured on the mod itself; files most factions go without are only noted).
- **Map size** (Change size... under the map): rows or columns of tiles added at any edge as deep sea, or cut off; every picture of the map, `map_heights.hgt`, `descr_terrain.txt`, characters, resources, forts, events and the campaign's scripts move with it; a cut that would leave something off the map is refused with each place named.
- **Start the game** checks first: a start script whose exe the game folder lacks is refused in plain words; a Medieval II `.cfg` that does not name the mod's folder is asked about; a 32-bit exe limited to 2 GB of memory is noted.
- **Check mod files**: problems worst first, grouped by when the game would meet them (would not start, campaign loads with something lost, battle, play); each one with a button that opens the place to put it right; the whole report behind **Full report...**.
- **Top row**: the data folder box three times wider, the Mod box takes what is left.
- **Credits**: a special thank you, Ko-fi supporters listed.
- **Map signs**: an army's flag and a ship fit inside their tile; the ship no longer shifts in the legend when the map zooms; the heir's crown is a narrow outlined coronet (the king's a full filled crown); the legend explains the flag marks; on the flag: the leader a crown, the heir a coronet, a family member a white diamond, a general not of the family a star, a captain (an army with no general) a chevron; the wheel zooms 50 % a notch by default (Ctrl 10 %).
- **Bigger map (x3)**: no river, ford or source on a water tile - by the heights and the sea ground too, not only map_regions; a river stands on land and touches the water by a side at its mouth.
- **Avoid Growth**: the words first and the box right of them, as the scroll's own 'Automanage [ ]'; the game's log says which tick pieces it took.
- **Bigger map (x3)**: no cliffs and no beach on the bigger map - the game drew the beach as a zigzag band over the land and the cliffs never sat right on the new coast; the shore looks right without them. Paint them where wanted with the Terrain editor's brushes.
- **The top row**: the Mod box takes the free width (a mod's full name shows), the data folder box is shorter (its whole path on hover).
- **Unpacking Medieval II**: the unpacker's question 'Do you agree to these terms and conditions? (Y/N)' is answered Y (the offer says so) - it waited and nothing was unpacked; a Kingdoms campaign unpacks into its own folder (mods/<campaign>/data).
- **Map**: a port is deleted from the right-click menu (its fleet goes to the sea beside, the town's harbour buildings go; Undo brings it back).
- **Town lists** (Many towns, the Buildings and town lists): each town's row in a muted shade of its owner's colour.
- **Building pictures**: a building level given to a faction whose culture has no picture of it gets the picture of a culture that has one (there was only a note to import one); a copied building chain takes another culture's picture where a culture lacks its own.
- **Map signs**: the dagger's guard thinner; a merchant is a coin with the euro sign, a heretic a lightning bolt.
- **Credits**: the reporters thanked by the names they signed with; no quotes.
- **Map signs**: the assassin's dagger upright, its point down; every agent's sign symmetric; a plain army led by a captain carries a rank chevron; the leader marks show on smaller flags too (a town's flag bigger).
- **Map editor**: a right click or Esc puts back every tool still waiting for its click (armies, fleets, agents, resources, forts, watchtowers, ports, a new region's town); a fort, watchtower or wonder is deleted from the right-click menu too; the legend lists the resources while Layers > Resources is on.
- **Bigger map (x3)**: a one-tile islet or lake loses one or two corners - no plain 3 x 3 squares -; a cross left at the tip of a one-tile cape is rounded off.
- **Bigger map (x3)**: a river never has a pixel on the water - it ends on the land touching it; a cliff near the water stands on the coast; small islands and lakes (up to 12 tiles) keep their size and come out round, like a drop of water - no crosses or clovers -, and capes one tile wide stay whole strips; the sea along the coast is always shallow (never deep at once), the beach one pixel wide, specks of deep water in the shallows gone and the line to the deep water smooth.
- **Test mod**: the army aboard a fleet is tried the safe way - on the shore beside its fleet, put aboard by an engine script at the start (an army on the fleet's sea tile made the game stop reading descr_strat.txt there).
- **Avoid Growth (Rome, Barbarian Invasion)**: the tick uses the thin box of the scroll's own Automanage tick, and it stays under Automanage when Settlement Details is open beside the scroll (it jumped onto the details page).
- **Campaign rules**: a rule whose change broke the game in a test is greyed out and kept as it is for now, with what happened on hover (first: the recruitment slots - lowered to 0, no town could recruit). The test mod leaves such rules alone.
- **Module builder**: a game condition line is passed to the engine ended, as in a script file - a bare line gave 'Condition parser doesn't recognise this token' in both games.
- **Texts**: a new text goes into every copy of its table the mod has (data/text and data/text/english) - an emergent faction's title written to one copy was 'not found' in Barbarian Invasion.
- **Map**: a right click (or Esc) puts back what was picked on the right panel and not placed yet; the wheel zooms in round steps (10 %, Ctrl 5 %, Shift slowly and smoothly; + / - by 50 %); armies, agents, fleets and ports show from 300 % zoom (towns always) - all three in Tools > Settings > Campaign map; a fort's battlements are all stone and alike, its gate in the owner's colour; a click outside a text field takes the typing cursor out of it; the GitHub button is dark. Armies carry the same flag as a town's roof, with who leads them on it (the king a crown, his heir a small crown, a family member a star; a town's or fort's flag shows the highest one inside); a princess is a heart; a ship has a white sail and stands at the foot of its tile. Layers keeps its menu open while ticking; the 'Edit resources' tick is gone - Layers > Resources shows them, the legend on the right places new ones. Terrain editor: the beach is named so (it said 'impassable') and is painted with the sea's brushes, on a sea tile beside the land only (one tile wide, as both games draw it).
- **Load a packed Medieval II without its unpacker**: when the game or a Kingdoms campaign is still in .pack files and tools\unpacker\unpacker.exe is missing, Load now says so and how to get it back (Steam's Verify integrity of game files), instead of a bare 'file not found'.
- **Religions in Barbarian Invasion** (Rome's expansion and the mods made from it): New religion... writes a new
  belief - its lines in `descr_beliefs.txt`, its three pips and its texts in `expanded_bi.txt`; a town follows it
  through the buildings that carry it. The test mod's religion step now runs there too (a belief of its own and a
  temple chain copied from the Christian churches). Plain Rome has no religions.
- **Map > New army: Make him a general** (a tick, both games): his army starts with the faction's general's
  bodyguard (the unit marked general_unit, the one its own generals lead), so the game shows him as a general with his
  own name instead of a captain.
- **Discord, YouTube and GitHub buttons** at the bottom, each in its site's colour. **GitHub** shows the
  number of a newer release when one is out (`GitHub (new 0.30)`) and then opens its page: the editor asks GitHub for
  the newest release number when it starts (every few hours; nothing is sent; off in Tools > Settings > New
  versions). Only releases count, not the builds of every change.
- **Map: a double click on an agent** opens the Character editor on him (traits, retinue, age, the game's panel).
- **Delete this mod's folder** (Tools, red): the loaded mod's folder with everything in it, after two questions
  (the second wants the mod's name typed); never the game's own data or an expansion's.
- **Lives without towns** (Events > How a faction comes into the campaign, a tick; with REX / M2EX): writes the
  engines' own `can_homeless yes` in the faction's block of descr_sm_factions.txt - the faction stays in the game
  with no town instead of dying or turning into a horde. Greyed out without an engine (the plain games do not know
  the word); Check mod files names the line if it is there without one. The test mod's later faction gets it.
- **Campaign rules and the Module builder say they are experimental**: a red line at the top of both windows (try it
  at your own risk, a backup is made first, please send a report).
- **Credits** (Tools > Credits (who made it with us)..., and the [CREDITS.md](CREDITS.md) page beside this one): the
  author, who helped a lot, the testers who sent reports and ideas, the supporters on Ko-fi and what people said -
  one page, the same in the editor and on GitHub.
- **Start the game** (the green button beside Tools, both games): starts the game with the mod that is loaded - its
  own start script (New mod folder writes `Start_<name>.bat`; the engines' own scripts in the game folder, such as
  REX's *Barbarian Invasion.bat* or M2EX's *Teutonic.bat*, are found too), else the line those scripts use
  (`REX.exe -nm -show_err -mod:<name>`, `-bi` / `-alx` for the expansions, `M2EX.exe --features.mod=mods/<name>`,
  `medieval2.exe @mods\<name>\<name>.cfg`); the plain game with its own exe. Changes not written yet are named first
  (the game reads the files on disk). A window too narrow for the bottom row puts its right-hand buttons on a row
  of their own instead of cutting them off.
- **Add-ons > Scripts in the game...** (Rome with REX, Medieval II with M2EX): every script the engine runs from the
  game's `script/modules` - the editor's add-ons, Module builder modules, ones you added, anyone's - with what each
  is and whether it runs. Pick one to change its settings in its own lines, turn it off (renamed `.nut.off`, kept,
  not run) and on again, delete it, see its code or open its folder; every change asks first and makes a backup. The
  test mod's scripts now carry a mark at their end: they stay in the game's folder when the test mod is thrown away,
  and **Take out every script the test mod put in** removes them with one press (older ones are found by their
  `ce_test_` names). The test mod tries it (the words beside Avoid Growth's tick).
- **Map editor: delete a town with its region** (both games): right click a town > **Delete this town with its
  region...**. Its land, town and port pixels go to the neighbour it shares the longest border with (or the one you
  pick), its block of descr_regions.txt and its settlement in descr_strat.txt go (the owner's next town is its
  capital; the rebels in the town go with it, a faction's characters there stay in the field), and it leaves the
  mercenary pools, the win conditions and Medieval II's music lists, in every campaign that shares the map. map.rwm
  is removed. Refused in plain words: a faction's last town, a region a faction rises in by an event, a town a
  campaign script names (the lines are listed), an island with no land neighbour. Trait and ancillary conditions
  that name it are listed (they never fire there again). Preview, a backup, Restore byte for byte.
- **Select on the Map: a box round many things at once, as in a strategy game** (both games; replaces Pick towns):
  tick **Select**, choose in **what...** the kinds (towns, armies, agents, fleets, resources, forts), drag a box with
  the left button (Shift adds) or click things; a right click gives the towns to another faction, adds a building
  or garrisons to them all, or takes the characters, resources and forts off the map (a leader, heir or family man
  stays, named). One Undo takes the job back; the right button drags the map meanwhile.
- **The town window has the Buildings and Garrison editors of the main window** (both games, any owner, the Map
  editor too): a double click on a town opens its owner, level and population with the Buildings tab's editor (the
  game's pictures, a level per chain); **Garrison** switches the same window to the Units & armies card picker
  (**Suggest**, a named character keeps his bodyguard). Written with Preview and a backup - nothing jumps to the
  main window any more.
- **More of the engines' unit words explained** (Unit editor, the ? beside a unit's line): stun_immune, unstoppable,
  is_knockdown_immune (Rome with REX, Medieval II with M2EX), fearless (Rome with REX), unique_unit (Medieval II
  with M2EX), hp_damage_N (damage per hit) and hardy_N with its number - the words the engines' unit readers take.
- **Map editor** (the first button of the top row, both games): the campaign map alone, no faction to pick - every
  faction's things alike. Drag any faction's towns, ports, armies, agents and fleets (right button); right click: give
  a town to any faction, **Its units...** for any army or fleet (the card picker in a window of its own; a general
  keeps his bodyguard), delete a character, a new army / agent / fleet for any faction; resources, forts, wonders and
  regions as on the Map tab. Preview, then Apply changes writes them (a backup first). Box selection and deleting a
  town with its region come next.
- **Test mod: the later factions are seen at once.** The test factions wear colours no faction of the game wears
  (each told apart from the others); the faction that comes by an event rises on turn 2 next to the test faction's
  capital; a faction splits off the test faction when its far town - left without a garrison on purpose - revolts;
  the new region's town gets a garrison. The step texts name the towns.
- **Test mod**: a shadow of the test faction (ce_test_shadow) of its own; the faction that comes by an event now
  comes in on turn 2 (was 6), so it can be tried at once; the Map editor's step.
- **What every number of a unit's line means** (Unit editor > Every line of the block, both games): the **?** beside
  each line names its values one by one for what is typed there now - stat_pri's "13, 3, pilum, 35, 2, thrown, ..."
  reads attack 13, charge bonus 3, the missile pilum, range 35 m, 2 per man...; the words of attributes and of the
  weapons explained too (the game's own, and REX's / M2EX's). Taken from the notes the games write at the top of
  export_descr_unit.txt; the few values they leave out are marked so.
- **Module builder: your own add-on made of blocks, no code** (Rome + REX, Medieval II + M2EX - one script for both):
  Tools > Module builder... or Add-ons > New module (no code).... **WHEN** something happens (a faction's or a town's
  turn starts, a general takes a town, a building is finished, a unit is trained, a battle ends, a town riots, rebels
  or grows, a faction is destroyed or gets a new leader, a son comes of age), **IF** conditions hold (who the faction
  is, its money or number of towns, the turn, a chance, the town's people, which town, the capital, a building it
  has, who lost the town), **DO** actions (money given or taken, people added, taken or capped, a building built or a
  chain torn down - never the governor's -, new units, the town given away, war, peace or an alliance, a trait or a
  retinue member for the general, the game's own message scroll, a line in the game's log, any console command). The
  names are picked from the mod's own files; a sentence says in plain words what the module will do, and what is
  missing (an action that needs a town on an event that brings none, a name the mod lacks) is said before anything
  is written. Any number or text can be made a setting the player changes later on the Add-ons page. Nine examples
  to start from: help when broke, loot for taking a town, plague in big cities, a free unit when a barracks is
  built, gold for holding the capital, a message on turn 10, rebellion punished, a trait for the conqueror, Avoid
  Growth for chosen towns. **Save to my add-ons**, **Put it in the game** (a backup first; its messages go into the
  mod's `text/custom_messages.txt`), **Share...** as a zip; a saved module opens in the builder again (Add-ons >
  Change it in the Module builder...). The test mod puts two in (money and a message on turn 2, loot for every town
  taken).
- **Module builder: every command and condition of the engines.** Besides the plain blocks, an IF line can be **any
  condition** of the engines' own list (299 both engines have - `FactionType`, `Trait`, `I_TurnNumber`...; checked
  against what just happened) and a DO line **any console command** (142 both have - `kill_character`, `add_money`,
  `create_unit`...) or **any campaign-script command** (198 - `set_event_counter`, `give_settlement`...). **Pick...**
  lists them with a search: the form of the line, a sample, where it works, what a condition needs from the event; the
  engine's own description when the game has its `documentation` folder (the engines write it with the console
  command `dump_docudemon`) - and its parameters as fields: factions, towns, regions, units, characters, traits,
  retinue members, buildings picked from the mod (the event's own `{faction}`, `{town}`, `{general}` first), the
  comparison and the choices from a list, the line put together below; a line already there is read back into them. A module for one game gets that engine's whole list (REX 154 / M2EX 259 console
  commands). A line is checked before anything is written: a name the engines lack, the wrong letter case, a block of
  campaign_script.txt, a battle-only command, a condition needing what the event does not bring. What an event
  brings comes from the engines' own lists too: REX's town taken has no old owner and REX has no 'town grows' event -
  the builder says so for a module of both games.
- **Module builder: any event, and numbers kept between turns.** WHEN can be **any event** of the engines' own list
  (**More events...**: 139 both engines have, REX 167 / M2EX 221 for a module of one game), with what it brings
  read from the engine. New blocks: IF **a remembered number** (is below / above / ... a value), DO **remember a
  number** and **add to a remembered number** - kept between turns and in the saved game, as the engines' own event
  counters (campaign_script's `I_EventCounter` reads them too); `{faction}` or `{town}` in its name keeps one number
  per faction or town.
- **Add-on: Avoid Growth** (Rome + REX, Medieval II + M2EX - one script for both): a tick box on the settlement
  scroll of each of your towns, drawn with the game's own box and tick, under the population figures. Ticked, the
  people the town has become its ceiling: it never grows past it, still loses people the usual way (recruiting,
  battles, plague) and grows back up to the ceiling. Border towns stay the village, town or city they are - put
  them on auto-manage and forget them. The ceilings are kept in the saved game; a town lost to another faction
  drops its tick. The words, the tooltip and the tick's place are settings. The test mod puts it in too.
- **Unit editor: the REX / M2EX attributes of their newest builds** - immune_arrows, immune_fire,
  resistance_projectiles, enduring_fortitude, life_steal, hardy_N, strong_against_armour, ignores_armour - offered
  with their effect like the older ones.
- **Unit and Building editors: Every line of the block opens in a window of its own** (like the family tree), so the
  pictures, model and voice keep the editor's whole height.
- **Campaign rules: the campaign's start** (both games): the top of the loaded campaign's `descr_strat.txt` - start
  and end date, `timescale` (years a turn), how seldom brigands and pirates appear, REX / M2EX's leader persona odds,
  and the switches as on / off (night battles, date as turns, Marian reforms, rebelling generals, gladiator
  uprisings). The test mod changes them too.
- **Test mod: every campaign rule changed** (one step): each value of every settings file - the campaign's
  start, descr_campaign_db, the towns' growth / order / income, diplomacy offers, recruitment, unit sizes and the
  REX / M2EX engine settings and switches (548 values in Medieval II, 162 in Rome) - changed to one the game takes:
  numbers a step (a maximum or limit up, a minimum and anything else down, so the campaign's towns and families
  still fit), switches turned, an engine option to another it names. Left as they are, with the reason in the
  report: the start date, the switches that name files the engine loads, the console switch and the faction unlock.
- **Test mod: every feature and every option** (59 steps): besides one step per feature it now tries their
  variants too - a faction that splits off another in a revolt (all five engines read it), alliances and wars at
  the start, city / castle and level for many towns, garrisons the game's way, a line of a unit and of a building
  changed, a character's traits and retinue, a daughter and a man tied to no family, a port moved, a region's
  rebels / farming / shown names, a character moved and one deleted, cliffs / volcanoes / climates, Bring from
  another mod, unit packs, Check and install a pack, both add-ons, plagues / floods / storms and a game event moved
  and taken out, the engine settings, a unit taken away, every picture of a faction. The report ends with every
  feature of the editor and the step that tried it; the editor's own tests fail when a work button, tab or Tools
  entry has no step. The events fall on turns 2 and 4.
- **The mod at a glance in the log**: every Load writes a short picture of the mod into the editor's log - the game
  and engine, its campaigns, factions and cultures, regions and who holds the towns, the map's size, how many units
  and building chains, and which of its files are its own. A report then shows what the mod is, without any of its
  files. (Check mod files' result already goes into the log.)
- **Answers to my reports**: the author's answer to a report now comes
  back to the editor - the report window's new tab **Answers to my reports** lists the reports sent from this
  editor with their state (open / fixed / not planned) and the talk so far, and **Send the answer** replies (with a
  screenshot or the newest logs if you like) to the same report. The editor looks for answers when it starts (every
  few hours, by the reports' numbers only - off in Settings > Reports) and the Report button says "(1 new)" when one
  came. Reports sent with older versions are found in the editor's log.
- **Tools > Test mod - every feature (for the author)**: a stress test of the editor itself, not something a modder
  needs - it makes a new mod folder `CE_Test` beside the loaded mod (the loaded one is not changed) and applies every
  feature to it, one write each (a new faction and one that comes later, faction edits, armies, diplomacy, victory,
  resources, forts and wonders, towns, the map, a new region, renames, terrain, land and sea, family, traits,
  religions, roster, figures, a new unit and building, a battle model, a unit voice, events, campaign rules, an
  add-on, every kind of picture), with Check mod files after each step and a report of what to look at in the game;
  optionally a second copy `CE_Test_x3` with the map 3 x bigger. Then the mod is started in the game and its log
  sent with Report a bug. Both games.
- **Banner... on the Art tab, both games**: the faction's
  battle banners made new from a white banner - no emblem needed first. The cloth dyed in a pattern of up to three
  colours (plain, a tricolour upright, across or slanting, quarters, a cross, a border...), a symbol on it if you
  like (**Symbol picture...**, its plain background cleared), dragged into place with the left mouse button
  (**Snap**: a grid of three cell sizes on each banner, or freely; the wheel makes it bigger or smaller). **Save the
  template...** gives the white banner as a PNG of the game's size with each banner outlined, to paint in any
  program; **Put in my own drawing...** takes it back. *Rome*: the game's blank white banners (Roman, barbarian,
  eastern), the own and the allies' banner. *Medieval II*: the game has no white banner, so a white template is
  taken from the mod's own banner pictures (`banners/textures/faction_banner_*.texture` - every faction's holds the
  same banners in the same places, so what they share stays and each one's heraldry goes); every banner and
  pennant of the sheet is dyed on its own, and the window shows the banner in 3D on its model (infantry, spear,
  cavalry, missile, general). A sheet shared with another faction becomes the faction's own copy.
- **The exe checks itself before it is handed out**: `RTW-M2TW-Campaign-Editor.exe selfcheck [report.txt]` imports
  every part of the editor, reads every file that travels inside the exe (the game manifests, the engines'
  catalogue, the built-in add-ons, the icons), loads a tiny made-up mod, runs Check mod files on it, writes a new
  faction and restores every byte. The download page builds run it: an exe with a part or a file missing is never
  handed out. Every part of the editor now goes into the exe, also those opened only from a button.
- **Module builder: the engines' builds of 2026-10-04** - the console command `diplomatic_stance` (REX and M2EX)
  now also makes one faction the protectorate (`protectorate_of`) or client (`client_of`) of another; the
  builder offers all five stances in its list.

### Changed
- The **Tools** menu is grouped by what one comes for, each group under a grey heading: *Find what is wrong* (Check mod files, the game's log, the test mod), *Files and backups* (Restore, packs, game manifest), *About the editor* (log, Credits); Delete this mod's folder stays last, in red.
- **Bigger map (x3)** is now a beta (was alpha): step by step, checked after each step, tried in the game on both games.
- An unexpected fault of the editor is told in plain words - your files are safe, you can go on, *Send a report...* - with the technical line kept short for the report; the same fault again is not shown again (it goes to the log and the message line).
- Fields of one game only are shown greyed with the game named (*Name (short) (Rome only)*, *Religion (Medieval II only)*) instead of vanishing.
- Buttons that undo or delete (Put the old map back, Delete this pool, Delete a script) stand apart from the buttons beside them, so a hurried click does not land on them.
- **Rivers may run onto the sea again** in the Terrain editor (river, ford, source - the games' own maps end some rivers in the water); cliffs and volcanoes stay on land.
- **Bigger map (x3)**: river mouths as the games' own maps have them - the last pixel may step onto the half-flooded shore tile (rivers stopped one tile short of the sea), and a river touching the sea only by a corner gets one pixel more so it touches it by a side; the coast's corners as the games' own maps - a corner between three land tiles is always land (no more triangles of water cut into the land), between three sea tiles always water.
- **Bigger map (x3) step by step**: five steps, one press each - 1 grid, 2 smoothing (coast, borders, ground, climates), 3 heights (every sea point under the water, no land point under it), 4 rivers (one pixel, on land only), 5 objects (towns, ports, armies, resources on tiles they may stand on); each written with a backup and checked, the map shown between them to fix by hand; steps 3-5 build on the map as it is then (the modder's fixes count); the window goes on where it stopped; one button puts the old map back.
- **Every window can be resized**, and scrolls when what it holds does not fit (a small screen, a long text); a window never opens bigger than the screen. The buttons of *Make the campaign map 3 x bigger* and *Map size* stay in sight at the bottom whatever the window's size.
- **Map**: town names never cover each other - the faction's own towns first, a name that would sit on another is left out until you zoom in.
- **Ctrl+Z / Ctrl+Y** in a window of its own (banner, emblem) undo and redo that window's steps, never the main window's work unseen.
- **Character panel**: a trait's long effects no longer run into the next trait, a retinue card's two-line name no longer covers its effects.
- **New mod folder** copies every file by default (the mod stands on its own, to share); hard links are a tick for a mod kept to oneself.
- **One faction with both a shadow and a split-off faction** is refused only in plain Rome (it crashes at the end of a turn). Medieval II with M2EX and Barbarian Invasion with REX take it without a crash; Preview says that the revolting towns then go to the shadow, so the split-off faction does not come while the shadow is there.
- **Bigger map (x3): values you turn yourself** - the window has a field for each: hills and mountains (times
  higher), smoothing of the lines (the coast, rivers drawn as sea, the borders, the edges of ground and climates: 1 =
  smooth, as water finds its level - no 3 x 3 steps, no beads or breaks in a narrow river; 0.67 = lighter; 0 =
  winding, as before), narrow rivers kept open, crags on mountains, river valleys and volcano cones. Each shows its
  default and range, a ? says what was tried in the game, and *Back to the defaults* resets them. The shore by the
  water is the games' own and is not among them. Towns, ports, armies and resources keep their tiles at any value.
- **Bigger map (x3): no teeth along the shore.** The land by the water now takes the old map's heights by its real
  distance from the water (a corner step counts as 1.4) and capes stand as low as the old map's capes; one height per
  ring had made a small tooth at every step of a diagonal coast.
- **Lives without towns (can_homeless)** is written after the horde's last unit, right before `can_sap` - the place
  all three games read it (between the horde numbers and the horde's units they stopped with *Expecting can_sap*).
  Check mod files names it when it stands anywhere else.
- **Bigger map (x3): the coast as the old map had it.** The first three points on each side of the water's edge take
  the old map's own shore heights (land never higher, the sea at the old depth by the shore, not three times
  deeper), and the next four blend into the bigger map's heights, so the shore lies as in the games' own maps -
  against the corners flickering at the water's edge. Small pools of water no sea tile holds become land.
- **Map: an army in a fort or a watchtower** shows the same flag as an army in a town, on the sign's corner; the
  right click on the fort offers *Take the army out*.
- **Avoid Growth**: the tick is drawn with the box of the scroll's own Auto-manage tick, under the words "Avoid Growth" (the test mod now changes its tooltip, not its words). Medieval II: in the Auto-manage row, past the Construction and Recruitment ticks the game adds there once Auto-manage is on; Rome and Barbarian Invasion: on the free line under Automanage. At any screen size, also when the game gives its scroll in 1024 x 768 layout units; the editor tells the script which game it is put in (it took Barbarian Invasion for Medieval II).
- **A Kingdoms campaign still in its packs** (Medieval II from Steam: `mods/british_isles`, `americas`, `crusades`,
  `teutonic`): Load offers to unpack it with the game's own script for it (`unpack_britannia.bat`...) instead of
  saying descr_sm_factions.txt is missing; the question for a packed game now says the game plays from its packs
  and only the editor needs them unpacked.
- **Test mod**: the step that replaces every picture of the later faction leaves its 3D figures' textures alone (the
  test picture on a model's skin made solid green figures on the campaign map).
- **Ctrl shortcuts in any keyboard layout** (Undo / Redo / Preview / Write it, copy / paste / cut / select all, a
  screenshot pasted into a report): a Russian or another non-Latin layout no longer stops them.

- The Ko-fi button reads **Support me on Ko-fi** (Ko-fi's own words).
- **Settings** and **Help** moved into **Tools** (top of the list); Tools no longer repeats Report a bug / Suggest an
  idea - the **Report a bug / Suggest** button does both.
- **The bottom buttons wrap** when the window is narrow: button by button onto the next rows, the right-hand ones
  kept to the right edge - none hidden past the edge, none over another (also the other button rows that wrap).
- **Map: the right button drags the map everywhere**; the left button does the rest (picks, drags signs, draws the
  Select box, paints); a right click without moving still opens the menu, a double click stays on the left button.
- **Map: Select adds** - a box or a click adds to what is selected, Shift takes away; a click on nothing clears it.
- **Map: the zoom in per cent** beside - / + / Fit (100% = the whole map in the window).
- **Forts and watchtowers stay inside their tile**; a fort has no roofs any more (its towers' battlements carry the
  owner's colour).
- **Forts and watchtowers on the map** drawn anew: a fort is a small stone castle (two towers, a wall, a gate), a
  watchtower a wooden lookout on legs - both with roofs in the owner's colour (the two looked alike).
- **Every button looks alike and takes less room**: about 1.5 x lower than before (21 px instead of 29 - 33), the
  same frame, padding and gap everywhere - the top row's works and windows, Tools and the other menu buttons, Start
  the game and Ko-fi (their own colours, the same frame), the colour buttons and the Terrain tab's palette (the
  picked one framed); a focused button shows a coloured frame.
- **The Terrain editor is a tab of the Map editor** (Map | Terrain), no longer a work of its own on the top row.
- **The top row has no arrows any more** when the window is narrower than its buttons: the mouse wheel over it and
  dragging it sideways move it, and it takes no extra line.
- **Shadow and split-off factions only where the game takes them** - Barbarian Invasion and Medieval II; plain
  Rome (also with REX) is offered 'on the map' and 'by an event' only, and Check mod files names such a tie in it.
- **Avoid Growth (Rome): the tick sits on the free line under Automanage** (it lay over 'Settlement Details').
- **Campaign rules: Unit sizes say to change them with care** - with other multipliers than the game's own the
  game's options lost the unit size choice (Rome with REX).
- **Buttons no wider than their words** - about two spaces from the words to the edge, everywhere (no minimum width
  any more: '+', '-' and 'Fit' were as wide as 'Browse...'); the works and the window buttons on the top row too.
- **Map: a new town from the legend can stand on another region's land** - it takes its own tile and the 8 round it
  at once (they were refused with 'not ...'s land - paint it first' before the click), and the brush is then in
  your hand with the new region to paint the rest of its land.
- **Bigger map (x3): rivers drawn the way rivers run** - a bend is rounded instead of a right angle, a long straight
  run swings gently (a meander about every four old tiles, never twice the same, the same map always alike); still one
  pixel wide everywhere, as many rivers, sources and mouths as before, none on the sea, fords kept on the river.
- **Bigger map (x3): the coast, the borders of regions, ground types and climates wind the way nature draws them**
  instead of following the 3 x 3 blocks and straight 45-degree cuts: bays and capes, borders that bend, forests and
  marshes with ragged edges. Two waves whose sizes stand in the golden ratio bend them, so the pattern never repeats
  and the same map always comes out alike. Every old tile's middle keeps its region, land or sea, ground and climate
  (nothing changes under a town, army or resource), every region stays in as many pieces as before, rivers stay on
  the land, the beach one tile wide.
- **Bigger map (x3): a border that ran along a river stays on the river** - the new borders wound across the new
  rivers; now the land on each bank belongs to that bank's region, the river itself to its own. Lone pixels sticking
  out of a border (one side of their own region, two of another) go to the region round them, on every border.
- **Bigger map (x3): it says what to look over** - once the map is written, a message lists what to check by hand in
  the Map editor and in the game (coasts and river mouths, navigable rivers and straits, borders along rivers, ports,
  passes), which brushes fix small things, and what the editor could not do itself: no rule draws every map 100 %
  right.
- **Bigger map (x3): the relief the natural way** - the heights bend with the ground (hills and their ground types
  stay together), mountains get crags in three sizes as real ones have (plains stay flat; half as strong when the
  heights grow 3 x, which grows the crags too), and every river carves its valley (deep in the mountains, hardly at
  all on a plain). No slope comes out steeper than the steepest slope of the old map (where it would, the relief
  falls back to the plain stretch there); the land round a town stays smooth; land and sea stay where the coast
  puts them. `map_heights.tga` and `map_heights.hgt` (the copy the game reads) are made the same way. The heights
  take longer to make (about half a minute on a vanilla map).
- **The tools with a window of their own are buttons on the top row**, beside the works: Campaign rules, Events,
  Traits and retinue, Module builder, Recolour, Culture names, Many towns, Bigger map (x3) - one press away instead
  of in Tools (New religion and the region's shares are the Religions work's own buttons). Tools keeps the checks,
  the logs, packs, Restore and reports. The row scrolls when the window is narrower: drag it sideways with the left
  button (a click is still a click), the wheel or the arrows.
- **Map: an army in a town shows as a flag on the town's roof** (several side by side); a town with no army has no
  flag. Agents and ships still stand beside the town. The port's anchor now grows under the mouse like the towns and
  the characters.
- **The campaign map is always drawn tile by tile**: one square = one tile, as the game and every brush work with
  it. The switch for the old blurred "detailed picture" (Layers and Settings) is gone - it hid where a tile ends.
- **Module builder**: picking an example after changing the module asks in plain words whether to drop your
  unsaved changes (No keeps working on yours); an example looked at and left as it is still goes without a question.
  In the dark look the WHEN / IF / DO blocks keep their colours as dark tints.
- **The code is checked before every build**: CI runs Ruff (`ruff.toml`: a name never defined or never used, a file
  left open, the likely bugs flake8-bugbear knows) before the tests. A first full check with Ruff and Pylint found
  no crash; unused imports and dead code went out, and the wonder's 3D view has one handler for its window and the
  map's menu.
- **Sack Settlement (both games): the governor's building always stays, 600 people at least**: the core chain is
  never torn down, listed among the kept chains or not (without it the town could never be built up again); walls
  and roads stay by default and can be taken out. The ruins keep 600 people by default and never fewer (Rome's
  add-on gets the setting too). Any building standing in the town is torn down the same way, also one added in
  the editor or brought from another mod.
- **Sack Settlement for Medieval II (M2EX) is a button of the game's own kind**: the Medieval II add-on is now the
  same kind of script as Rome's Sack Settlement - M2EX runs the same scripts as REX (squi) - so its 4th button on
  the capture scroll is made of the scroll's own text-button pieces, as wide and as far apart as Occupy / Sack /
  Exterminate, in the game's font. It goes into the game's `script/modules`, where M2EX loads it for every mod.
  With it come the Rome add-on's options: who may raze includes hordes, rebel units if the game raises none, and
  with the 4th button off Exterminate asks Yes / No; the castles' roads are kept by default and you pick how many
  people stay in the ruins. The older Lua copy (`eopData/eopScripts/raze_settlement.lua` and its line in
  `luaPluginScript.lua`) is taken out when the new one is put in or taken out, so the scroll never shows two
  buttons. In the Add-ons list the two are **Sack Settlement (Rome)** and **Sack Settlement (Medieval II)**; in
  Medieval II the button itself says Raze Settlement, since the game's own second button is already Sack
  Settlement (the words are a setting).
- **Recolour more exact**: 64 pictures of
  five Medieval II factions recoloured and looked at one by one - before 49 good / 12 small faults / 3 bad, now 59 /
  5 / 0. Black and white faction colours (the Holy Roman Empire, Saxons, Timurids, the white of France, Denmark,
  Milan, Scotland, Poland, the Papacy...) now change on unit cards and battle textures (they never changed before);
  a cloak painted duller than the faction's colour or in deep shade is no longer recoloured in patches; faces, hands
  and hair are no longer taken for a red or yellow coat.
- **Medieval II shields recoloured**: *Recolour a faction's pictures* now
  also takes the weapons-and-shields texture of the faction's battle models (`unit_models/AttachmentSets/Final
  Kite_<faction>_diff.texture` and the like - the kite shields carry the faction's arms); one worn by other factions
  too is left alone with the reason, as the unit textures are. The battle banners' 3D models (`data/banners/*.mesh`,
  a part with no material) are now read. The carroccio of Milan and Venice (`siege_engines/textures/great_bell_tower_<faction>.texture`) is recoloured too.
- **Your contact remembered for every report**: the report window says it plainly - with *remember it*
  ticked (the default) the contact you give fills in every next report by itself (also in Settings > Reports);
  unticked, it is forgotten.
- **Rebel garrisons as the game makes them**: a rebel town's drawn garrison comes from its region's rebel
  type in `descr_rebel_factions.txt` (what the game raises there in a revolt) instead of the nearest rebel armies; a
  new box draws as many units as the game gives a town of that level (the mod's own towns measured; vanilla's rebel
  towns: Medieval II village 5 / town 4 / large town 7 / city 6, Rome 3 / 3 / 4 / 4). Rome's `//` comments in that
  file are read right.
- **Garrisons fit the town**: drawn garrisons in *Buildings and garrisons for many towns* hold only the
  units the town's own buildings recruit for its owner - no catapult in a village without a siege workshop, no heavy
  infantry where there are no barracks; a town that recruits none of them gets the cheapest units (peasants, levy
  spearmen). A box turns it off (then anything the owner recruits somewhere). Both games.
- **A town's own window**: a double click on a town on the
  Map (or the right click's *This town...*) opens it - owner (hand it to another faction), city or castle (Medieval II),
  level, population and buildings (add, raise, take out, checked as the game checks them), the garrison shown;
  Preview and Write it in with a backup. Both games. The old jump to Edit faction stays as a button and a menu item.
- **REX / M2EX: no limits at all**: with REX or
  M2EX beside the game the editor never refuses or warns for a number - factions, regions, religions, cultures,
  units, buildings, children, retinue. Check mod files says "LIMITS: none"; every write raises `max_factions` in
  the mod's own `descr_ex.txt` when the mod has more factions than it (a mod ran 32 factions under 31 and
  crashed in the faction panel), and the family editor raises `max_num_children` / `max_num_ancillaries` instead of
  warning. A new faction raises `max_factions` with it, no question asked, and the status line no longer says "Full"
  under an engine. Without an engine the original exes' limits stay as before (21 / 31 factions).
- **Testers' reports of 2026-10-03**: a window opens once - Settings, Help, Report, every Tools window and the
  Events / rules / traits / pack / bring / portrait windows come to the front when opened again instead of a new
  copy each press; a new window no longer shows at the top left for a moment before it jumps to the middle; the
  yellow hover texts keep dark text in the dark look (they were white on yellow); resource, fort, watchtower and
  wonder signs grow with the tile when zoomed in (they stopped at a small size); a battle banner or other picture
  shared with other factions now has **Replace (its own copy)...** and **Save a copy...** on the Art tab (Edit
  faction: the faction gets a copy of its own and its line points at it, the others keep theirs); the Recolour
  window opens much faster on Medieval II (it compared 40 unit cards with every faction's copy to guess where the
  colours came from); New army / agent for the rebels showed its 'Rebels of' row twice.
- **Factions that appear later**: a new faction can come into the campaign later instead of starting
  on the map - *by an event* (a date and a region: `emergent_faction` in `descr_events.txt`), *as the shadow of a
  faction* (the side that splits off it in a civil war: `shadowing` / `shadowed_by`) or *splitting off a faction in a
  revolt* (`spawned_by` / `spawns_on_revolt`) - New faction > *Comes into the campaign*. It starts dead
  (`dead_until_resurrected`, optionally `re_emergent` - may come back after it dies), with no towns or characters,
  nonplayable. **Tools > Events and later factions** now lists every such faction and changes how one comes in.
  **Check mod files** finds a shadow / split-off pair written on one side only, an emergence event for a faction
  that is not dead at the start, and a dead faction holding towns. A clone of such a faction (Ostrogoths, the
  empires' rebels) starts plain and alive. Both games (Barbarian Invasion, REX and Medieval II read these words).
- **A town straight from the Map**: the right click's *Edit this town...* (and a button in the town's own window)
  opens its owner in Edit faction with the town picked on the Buildings tab - level, population, city or castle,
  buildings. (A double click opens the town's own window, above.)
- **Many towns made city / castle and of another level at once**: a third tab in *Buildings and garrisons
  for many towns* (also on the Map's Pick towns menu) - city <-> castle with the buildings converted the game's way
  (Medieval II), a new level with its governor's building and population; towns of any owner, a backup first.
- **A town on its region's edge stays its region's** (a tester's Erebor, Divide and Conquer): a town pixel that
  touches a neighbour's land more than its own went to the neighbour - the town was not drawn, and the bigger map
  painted its block in the neighbour's colour. Now every region keeps one town, the surest pixels given first (the
  same on the Map and in the bigger map; vanilla maps unchanged).
- **Rome in 3D put together right**: the parts that hang on a bone - weapons, shields, helmet crests, the
  pieces of a ballista, onager or ram - were placed by numbers that are no place in the model, so crests floated
  off helmets, spears lay on the ground and engines fell apart; now each sits on its bone. The **T pose** (arms out)
  is the default for every Rome model, **Pose** shows it as the file stands. A **chariot** unit stands on its chariot
  with its horses and crew where `descr_mount.txt` puts them; a **siege engine** unit shows its engine
  (`descr_engines.txt`) whole, with its texture (a model's texture is looked for beside it - `models_engine` too).
  Checked on all 948 vanilla Rome unit, mount and engine models (the 52 the reader does not know yet are the same as
  before: ladders, towers, some engine variants).
- **Land and sea: new land rises from the shore** - it was all set at
  the shore's height and lay flat on the water; now it climbs inland as both games' own coasts do (measured on the
  vanilla maps: 2, 8, 12, 14, then 16 grey steps from the sea), also where land is painted tile by tile.
- **The Unit and Building editors no longer lag**: a big building (Medieval II barracks, 316 lines) took
  2.3 s to show after every pick or added line - now 0.02 s: the block's lines are made only when unfolded, and the
  look's colours are worked out once instead of 50 000 times per window.
- **A faction without name lists no longer stops Apply** (found in a tester's log: "no name in empire_east's name
  list for a captain", a faction brought from Barbarian Invasion): it gets a copy of its culture's kin's name lists in
  `descr_names.txt` (said in the preview), so its captains and new characters can be named.
- **Events: the picture players see and what the event does** - the scroll's picture (a historic event
  its own `ui/<culture>/eventpics/<event>.tga`, a plague / volcano / earthquake its kind's `disaster_<kind>.tga`),
  **Picture...** puts your own in for every culture at the game's size, and each kind says in plain words what it
  does (a plague spreads from the nearest town, a volcano or earthquake damages buildings and kills people...).
- **Campaign rules: the REX / M2EX engine settings** -
  `descr_ex.txt` (ages and the family, bribery, hordes, camera, max factions, battle visuals...) and `descr_caps_ex.txt`
  (feature switches: recruitment slots per town, sprite format, trade fleets...), grouped by the file's own headings,
  each value explained by the comment the engine writes above it; written into the mod's own copy.
- **One temple per town, as the games want** (both games: a chain named `temple_...`; two in one town stop the game
  with "Settlement specified with multiple temple buildings"): the Buildings tab swaps the old temple for the new
  pick, Buildings for many towns skips a town that has another temple, Check mod files names a town holding two.
- **Terrain editor: impassable land and impassable sea brushes** -
  Medieval II always; Rome only with REX (REX knows these ground types, the original exe does not; not yet tried in
  the game on Rome). Refused under towns, ports and characters like mountains.
- **Land and sea: new land stands in shallows**: the 8 sea tiles round a tile made land turn shallow sea
  in the ground where they were deeper (ocean / deep sea).
- **Map: what you place rides under the mouse** - a resource, fort,
  watchtower, wonder or agent shows its own sign, framed green where it may go and red where not.
- **Map: unticking Pick towns unpicks every town** - the same rule everywhere: switching Edit resources
  or Edit regions off drops what was picked or waiting for a click, hiding the legend puts its picked tool down.
- **Map: no "Edit forts, towers & wonders" switch any more** - forts, watchtowers and wonders are always moved with
  the right drag, placed from the legend (a wonder: right click, Put a wonder here) and deleted with the right click;
  their battlements keep the owner's colour.
- **Map: resource letters readable on every colour** - black on bright colours, white on dark ones.
- **Map: the map's size stands under the map, bottom left**.
- **Wonders on the Map (Rome)**: a double click on a wonder (or the right click's "about it") opens its window as the
  game shows it - picture, title, what it does, short and long description - with **View it in 3D** (its campaign-map
  model); the right click on free land has **Put a wonder here** (one of the game's seven - the game knows no
  others). Written on Apply like the other map changes.
- **Traits and retinue: a right click on Effects lists every bonus the game knows** - grouped, each in plain words, both games (the lists come from the games' own exes); a pick is added
  after a comma with the value 1.
- **Map: Delete from the map on the right-click menu**: a
  resource, fort, watchtower or wonder, or a character of any faction with his army - gone from descr_strat.txt with
  the next Apply, nothing left behind; the leader, the heir and members of the family tree are refused in plain
  words.
- **The old "Faction Tool" name is gone**: the code is the `campaign_editor` package, started
  from source with `python campaign_editor.py`; the files it makes beside a mod are `CampaignEditor_ignore.txt` and
  `CampaignEditor_mod.json`. Put over an older version, nothing breaks or is lost: its settings and log are moved in
  (also the settings an older version kept in APPDATA), its ignore list and mod mark are read and take today's names
  the next time they are written, its backups (`faction_tool_backups`) stay listed and restorable.
- **README**: the important things first - download, wiki, roadmap, changelog, what to do when something goes wrong,
  why support it - then what the editor does.
- **Recolour leaves the white banner a fleeing unit shows and the rebels' banner alone** (found in a tester's log: it
  made the faction its own recoloured copy of standard_routing / standard_slave).
- **Add-ons go where REX loads them**: into the game's `script/modules` - a mod with a script
  plugin of its own (manifest.nut + main.nut, as HLR has) loads no modules from its own folder, so an add-on put
  there never ran. An add-on whose code is already pasted into the mod's own scripts is refused (it would run
  twice).
- **New add-on: Player Diplomacy** (Rome + REX): truces that hold, client kingdoms that never invade you, far weaker
  factions that keep away; settings for each (add-on settings may now be numbers like 3.0).
- **Victory: many regions or factions at once**: drag over rows, Shift-click
  a run, Tick all shown, tick every region a faction holds, or pick the towns **On the map...** (their regions yellow).
- **Map: a sign grows as the mouse comes near it**, softly, from further away when zoomed out.
- **A new man tied to no family is no error**: Apply puts him on the map as a general of the faction (with a
  bodyguard, in its first town); only a new woman tied to no one stays a record (Preview says so).
- **People and family: one button, Add a person...** (testers: a person made from nothing; four buttons for one job) -
  step by step: who the new person is to whom (son, daughter, wife, husband, brother, sister, parents, uncle, aunt,
  or the head of a new family tied to no one), then the name, or someone already in the faction; Preview warns while
  a new person is on no tree. On the Faction tab the tree now stands on the right of the list and the person (it was
  on top, too cramped).
- **Character panel: a click on the pips sets the attribute**: the traits are fitted to it - his own
  trait moved to the level that fits, else a trait giving that attribute alone added; both games.
- **Traits and retinue window: the labels whole** ("Points it needs (Threshold)" was cut) and the descriptions in the
  window's own font.
- **Building editor: the texts players read**: the level's
  name, short description and description for each culture or faction, shown under the pictures and changed there;
  written to export_buildings.txt on Apply.
- **Unit and Building editors: the list's width can be dragged**, the line's grip drawn in the
  text's colour so it shows on either look; the width is kept.
- **Faction emblem: fitted by hand before it is made into every picture** (the emblem needed an editor of its own to fit
  a picture into the round icons): move, size, turn, cut to the old emblem's own shape (or
  a circle, a square), a ground in the faction's colours, a magic wand that clears an area of like colour, a paint
  bucket (emblem_edit.py, gui_emblem.EmblemFitter).
- **Faction emblem: the new symbol on the battle banners and the campaign map's flag (Rome)**: the faction's battle banners are made from the game's own blank
  white banner (standard_routing - Roman, barbarian or eastern, any of the three for any faction, whatever its culture), its cloth
  dyed in the faction's colour and the symbol painted on it with the cloth's folds; the allies' banner the same with
  the symbol faint; the flag symbol gets the bare symbol. **Banner...** picks another blank banner, a pattern of up
  to three colours (plain, tricolours upright / across / slanting, quarters, crosses, a border...), the symbol on or
  off, and moves the symbol (banners.py, gui_banners.BannerWindow). The game's blank banner itself (a fleeing unit's)
  is only read, never changed.
- **Faction emblem: a plain background goes at once**: a picture
  whose four corners are one solid colour has that background cleared when it opens; Start over brings it back.
- **Edit region... holds both names**: for a region of
  the map it now has the names in the files of the region and its town beside the names players see; a change of
  the file names is written at once in every file that names them, with a backup (asked first). The Map's
  **Rename...** and **Rename in the files...** buttons are gone (the Settlements tab keeps its own).

- **Every window opens in the middle of the screen**; a hover text stays inside the screen; a drop-down list is as
  wide as its longest line; a field whose text is longer than the box shows it whole when the mouse rests on it; the
  '?' marks are light blue in the Dark look (they were dark blue on dark grey).
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
- **Map: armies, fleets, agents and towns for any faction, no faction to pick first**: a click
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
- **Terrain tab**: the map showed tiny or not at all when the tab opened - it was fitted before the tab had its size; it is fitted again once it has one.
- Recolour window: the 'wheel: zoom, right drag: move' line has a row of its own (it was cut at the window's edge).
- **Bigger map (x3): the coast comes down to the water** - the land by the water kept the old shore's full height,
  a wall made 3 x taller with the heights (each tile corner on a diagonal coast a cliff tooth); it now slopes down to
  the water over one old tile and falls the way the games' own coasts do (the first land point by the water about as
  high as on the original maps: Medieval II 80 against the original's 70, Rome 72 against 63).
- **Medieval II: the game could not start with a faction that lives without towns** - `can_homeless` was written at
  the end of the faction's block, where M2EX stops reading descr_sm_factions.txt (every faction after it was lost,
  the rebels too: 'no faction named slave'); it now goes after the horde numbers, before horde_unit and can_sap, an
  old one is moved there, and Check mod files names one out of place.
- **Recolour: the list says what it does** - ☑ recolour / ☐ keep as it is / — left alone, a box on each group for the
  whole group, Space ticks the picked row.
- **Raze Settlement (Medieval II) and Sack Settlement (Rome): the button in its place on every screen** - some
  builds give the capture scroll's buttons in the game's 1024 x 768 layout units, so at 1920 x 1080 the button stood
  left of the scroll; now such units are turned into screen pixels (Avoid Growth's tick follows the same). Put the
  add-on in again (Add-ons) to get the new copy.
- **Map: a double click on a fort or watchtower** works again on the Map editor (forts are drawn there as movable
  signs and were not found): its army's units open; an empty one offers a new army for it.
- **Bigger map (x3): cliffs stay on the land** - a cliff the winding new coast put in the water moves onto the land
  beside it (cliffs showed in the shallow sea).
- **Report a bug / Suggest** takes up to 10 pictures (it was 3, and more were dropped without a word); pictures over
  the limit are named.
- **Rome: a faction that comes by an event** now comes as a horde, as Barbarian Invasion's Slavs do: it gets the
  horde lines and its own units (without them the game left it without a leader and it never came); Check mod
  files names an event faction without them in both games.
- **Barbarian Invasion: campaign-map figures recoloured** - the expansion names its pictures from the game's folder
  (`bi/data/models_strat/...`); they were never found, so a new faction kept its template's figures. Now each gets
  its own copy in the mod (`data/...`) and Recolour paints it.
- **Start the game** with M2EX / REX in the game folder starts the extender: a mod's own start script is used only
  when it starts the extender too (one for the plain exe did not start a mod that worked with M2EX's own line).
- **Bigger map (x3) mountains**: mountain ground only where the new heights stand high - a range's low edge becomes
  hills, or the ground beside it when it is lower still (it crept onto flat land round every range).
- **Map**: agents' signs grow and shrink with the zoom like armies and towns.
- **Events window**: a disaster's picture can be replaced too (the game shows one picture for every disaster of a
  kind - said beside it); the date says "years from the start"; Change... is greyed out until a faction is picked.
- **Tabs** are as low as the buttons.
- **Bigger map (x3) coasts**: no sharp triangle of water cut into the coast and no small foam-ringed squares where a
  sea tile touched the sea only by its corner - such a tile is now a square bay or joins the water through its
  corner; no land bridges across navigable rivers; small islands and thin strips of land that no tile holds are
  taken out of the water; a river ends one pixel into the water, as the games' own river mouths do.
- **Medieval II: a faction that comes by an event never came** - the game brings such a faction in as a horde (the
  Mongols' way) and stopped without horde lines ('ASSERT FAILED: faction.cpp: can_horde()'). New faction and Events
  and later factions now give it the Mongols' horde lines with three foot and three horse units of its own (the
  cheapest first) and its event's title and text ('Couldn't find title string for historic event'); Check mod files
  finds one without horde lines.
- **One faction with a shadow and a faction splitting off it**: in Medieval II (with M2EX) its revolting town went
  to the shadow and the split-off faction never came (Rome with REX crashed) - refused with the game's own reason.
  The test mod's split-off faction now leaves another faction, with a town of its own left to revolt.
- **Test mod: every campaign rule** keeps a share (0 - 1) or a percent (0 - 100) already at its top in its range
  (M2EX clamped `max_heretics_conversion_modifier` 1.05 and `max_bribe_chance` 105).
- **Rome: the game crashed at the end of a turn when one faction had both a shadow and a faction splitting off
  it** (`SETTLEMENT::get_revolt_type`). The editor now refuses the second tie on such a faction in plain words
  (Barbarian Invasion never gives one faction both), and Check mod files finds one already in a mod.
- **Rome: a shadow faction's victory conditions stopped the game reading `descr_win_conditions.txt`**
  ('stopped parsing before EOF (unrecognised faction or malformed entry)') - the factions after it had none. A
  shadow gets no victory conditions now (Barbarian Invasion lists none); Check mod files finds an old one.
- **Bigger map (x3): no wedges and no flicker on the coasts** - a corner point between land and sea tiles followed
  an older coast and stuck out as a thin wedge of sand into the sea or of water onto the land, lying on the
  water's level (it flickered in the game, z-fighting); small square islands stood in navigable rivers. Corners
  now follow the same winding coast, no point has the other kind on three sides, islets no tile of
  `map_regions.tga` holds go, and land touching water always stands clearly above it.
- **Bigger map (x3): volcanoes stood in wide flat fields** - their rise of one tile had grown to three while the
  game's volcano model stays its size. Each volcano keeps a cone of its own; mountain ground is never a flat
  field (its crags at least a mountain's usual slope); lakes that are water only in the heights wind with the
  coast and their banks come down to the water gently, with no wall.
- **Character editor: a trait written in other letter case was refused** (Barbarian Invasion's leaders carry
  `FactionLeader`, its traits file says `Factionleader`) - names of traits and retinue are now matched in any case,
  as the games read them. A long message in the status line wraps instead of running off the window.
- **Bring from another mod: a brought building's recruit lines named its faction for every unit**, also units
  of other cultures it may not own - the game warned 'unit(...) does not match up to the ownership for
  faction(...)' at every start (159 times in a test). A recruit line now names only the factions
  `export_descr_unit.txt` lets own the unit; a line none of them may own is left out, said in Preview.
- **Make the map 3 x bigger stopped on a mod with an empty `map_heights.hgt`** ('unpack_from requires a buffer of
  at least 8 bytes'). An empty or cut `.hgt`, or one that does not fit `map_heights.tga`, is now made again from the
  new heights picture, the way the game converts it, and the window says so.
- **Signs read on any colour** (both games): a town's hall, an agent's sign and a resource's letters are black on a
  bright colour and white on a dark one, on the map and in its legend (Egypt's white discs hid their agents' white
  signs); town names have a black edge all round, so they read on light land too; the colour buttons follow the
  same rule.
- **Faster windows with town and unit cards**: the faction list, the buildings and the units files are read once
  while they stay the same (the town window read them again and again), and the faction's names come from a table
  read once - the town window, the Buildings and Units & armies tabs open up to twice as fast.
- **Test mod: own buildings on the campaign map, three ways side by side** beside the test faction's capital, each
  with a different model of the game's own copied under a new name: a wonder of the game's own (Rome - its window on
  a double click), a new resource type with its own model (with REX / M2EX - the original games refuse unknown
  types), and a model drawn by an engine script (REX / M2EX; the game's log says which call worked).
- **Test mod: an experiment** - a copy of the test faction's army stands on its fleet's own sea tile: in the game
  it either starts aboard (as an army on a town's or a fort's tile is inside it) or the log says the tile is invalid.
- **Test mod: the test religion is told apart at once** (Medieval II): its own symbol (a magenta disc with a yellow
  star) and its own temples - Christianity's church chain copied as the Test Faith's (shrine to great cathedral),
  built by the test faction.
- **The town window gives the room to the buildings** (both games): the town's name once at the top, the
  explanations behind a **?**, Buildings and Garrison as clear tabs, the bottom bar only as tall as its buttons, the
  window no taller than the screen, and the building chains fill the window's width in as many columns as fit (also
  on the Buildings tab). When the main window holds changes not applied, Write it in says which ones instead of a
  bare refusal; after an Apply there the town is read again before anything is written.
- **Map editor: nothing looks selected any more** - every faction's towns and characters were drawn with the yellow
  edge of 'yours' (yellow only marks what is selected now); the map is drawn sharp, tile by tile, at rest as while
  it is dragged; 'landmark' (Rome's wonders, which have their own sign) is gone from the resources list.
- **The army flag on a town's roof is part of the town's sign** (both games): one flag says an army is in the town -
  a square cloth in the army's colour with a triangle cut into its right edge, its lower left corner on the sign's
  upper right corner, no yellow lines; it grows with the town under the mouse and is never dragged by mistake.
  **Take the army out** and **Take an agent out** (right click on the town; the agents listed by name and what each
  is - diplomat, spy, princess...) hang it under the mouse until a free tile is clicked (green where it may stand, red with why where not; Esc or a
  right click stops).
- **A double click on an army or a fleet opens its units; on a fort, the army in it** (both games, the Map editor
  and Edit faction); an empty fort or an agent says what can be done.
- **Rome: a new faction no longer crashes the game when it is destroyed.** Rome's message 'faction destroyed'
  (descr_event_images.txt) has one picture per faction - 21 in the game; a faction past the last one crashed the game
  the moment it was destroyed (message_builder_objects.cpp(763), 'a switch message object with a value higher than
  its number of conditions'). Every write that adds a faction now gives the message a picture for each (the game's
  copy put into the mod when it has none); Check mod files says it, and Load offers to put an older mod right.
- **Restore of a change to a file in the game's folder** (an add-on updated in the game's `script/modules`): its
  backup copy was kept outside the backup and Restore refused it; it is kept inside now, and older backups still
  restore.
- **Bring from another mod: the list of 'The units they recruit' scrolls** (step 5 for buildings; it was cut off
  with no way down), and the mouse wheel over a list box scrolls the page instead of changing the box - in every
  window.
- **Bigger map (x3)... has a window that leads the way**: the map's size now and after, the heights as one choice,
  a **Make the map 3 x bigger** button, the work's progress in the window, and when it is done **Put the old map
  back** (one press undoes it). The long list of changes (it looked like a log, and the buttons that wrote the map
  sat under it) is behind **Show every change...**.
- **Recolour: two battle textures never share one copy's name** (both games). Two textures that differ only in the
  wearer's word (`EN_Peasant_Padded_england` and `EN_Peasant_Padded_france`) both became
  `EN_Peasant_Padded_<faction>`, and the copy written last dressed the other's models too: a new faction's
  peasants wore France's blue and white in battle. Each copy now keeps a name of its own (the second one keeps its
  source's word, `EN_Peasant_Padded_france_<faction>`); the far-away sprites likewise. A battle texture named after
  another faction than the one in **From the colours of** is recoloured from that faction's colours: the game's own
  colours when the picture is the game's, even if the mod changed that faction's colours since (France's blue
  peasants were missed). Colours picked by hand count for every picture. A unit given to the faction gets its own
  far-away sprite too.
- **A faction that comes in by an event rises in a rebel region** (both games). Rome (with REX) crashed as the
  campaign loaded when such a faction's region belonged to another faction: "Faction(...) is about to be killed off
  because it has no capital and cannot convert to a horde", then the defeat message failed. The games' own example
  (Barbarian Invasion's slavs) rises where the rebels hold the land. New faction and Events and later factions now
  offer only the rebels' regions and refuse another faction's, and **Check mod files** names such an event. It also
  notes a faction that comes by an event marked "may come back" (re_emergent): the games' own are not.
- **The Unit and Building editors' right side scrolls** when the window is lower than its contents (the voices were
  cut at the bottom with no scroll bar). In a wide window the unit's voice stands in a third column beside the
  pictures and the battle model.
- **Bigger map x3: no islands in a navigable river.** A river that map_regions gives to a province while the heights
  hold it under water (a mod's navigable river), with a sea tile here and there, came out with small islands round
  those tiles. Inside water all round, the new heights now keep their own coast. The games' own maps come out the
  same as before.
- **A family's children are written oldest first** (both games, as every vanilla family is): a new son put after a
  younger child made Medieval II complain "... is supposed to be younger than ...". **Check mod files** names a
  wrong order.
- **Avoid Growth looks like the game's own ticks**: the small box and tick of the settlement scroll
  (PLAIN_CHECKBOX_BG / _TICK, as Auto-manage, Construction and Recruitment), their small grey-brown font, and in
  Medieval II it stands in their row, right of Recruitment (it sat over the income lines). Just the words "Avoid
  Growth" beside it; the tooltip is short and says the ceiling while ticked.
- **Recolour now reaches the far-away sprites of a new faction** (both games): a new faction's models named its
  template's sprites, so its men kept the template's colours at a distance. The faction gets its own sprite (the
  .spr and its pages under its own name, recoloured) and its model lines point at it (Medieval II: the texture
  line's sprite; Rome: its `model_sprite` line, which a new faction now gets too).
- **Medieval II (with M2EX): a new faction's men looked like bare skeletons in battle.** M2EX reads the models from
  descr_model_battle.txt, where the new faction got its `texture` line but not its `texture_attachments` line (the
  weapons and shields picture a figure takes half its look from). A new faction, a model given to a new owner and
  Recolour now write that line too, and **Check mod files** names a model where a faction lacks it.
- **A village grown to a town gets its governor's building** (Rome with REX; the town window, Many towns): the game
  stopped on the town - "has not been given a core building". **Check mod files** now names such a town too.
- **A son off the map is written one year under the age of manhood** (15 with the usual 16): the game refuses a
  living man off the map (a character record) AT that age, not only above it. **Check mod files** names such a
  record, and **Campaign rules** will not lower the age of manhood under a son the campaign already has. The test
  mod's 'every campaign rule' step now raises that age instead of lowering it (Rome with REX stopped on a
  15-year-old son of Egypt).
- **A new disaster event (plague, flood, storm, earthquake...) has its title and text**: Medieval II shows a scroll
  for disasters too and showed the event's bare name there.
- **Test mod: the 'every campaign rule' step leaves the timescale and the turn display as they are** - it changed
  them, so the years jumped two or three a turn and the turn counter showed the year.
- **Text that could not be read in the dark look**: light text on the Module builder's light IF block, dark red and
  dark blue lines (Not ready yet, In plain words) on the dark grey, light names on light ground swatches in the
  Terrain editor. Every text colour is now fitted to the ground it stands on (at least 4.5 : 1, the colour kept) - in
  both looks, also for lines coloured later (status lines, lists, the Preview).
- **A few files read in passing were left open until Python tidied up** (the factions' symbols and the banners for
  the Art tab, the town flags in battle, the heights of the map, Medieval II's age of manhood); on Windows an open
  file can stop the next write to it. They are closed at once now.
- **A rare "missing 1 required positional argument" error after closing a window**: a delayed step of a window
  closed before it ran could, much later, call a new handler that happened to get the same inner name. Every such
  name is now used only once, so a step left over from a closed window does nothing.
- **Rome: Preview froze on a big mod and could add a slaves resource to every region** - a mod that keeps
  each region's slaves on the town's own tile (like Barbarian Empires / HLR) was read as having none, and the
  check read every region again for every tile (minutes on 750 regions). A slaves resource on the town's tile
  now counts for its region, and the check takes a moment.
- **A file the system will not write is said in plain words everywhere, with what to do**: a mod folder
  that takes no writes (the backup cannot be made - nothing is changed), a full disk, a path longer than
  Windows takes (260 characters), a file held by the game or another program. Before, outside the main
  window such a refusal showed as "Something went wrong" with an offer to send a bug report. Restore that
  meets a file held by the game stops, keeps the backup whole and can simply be run again.
- **The bigger map (x3) no longer warns about the engines' own scripts**: REX's and M2EX's interface
  scripts (`script/core`, `script/ui`) and the add-ons that come with the editor were listed as "place things
  on the map by x, y - make those 3x+1 by hand" because they hold screen places and colours. Only a script that
  puts something on the map by tile (a tile command with its numbers, a teleport / spawn / tile call) is named.
- **Load on a mod that holds only the files it changes** (REX `-mod:`, Medieval II `mods/<name>`: the game
  reads the rest from its own `data`) said only "no descr_sm_factions.txt"; it now says what such a mod is, where
  the game takes the other files from and what to do (load the game's data, or make the mod whole with New mod
  folder...).
- **The mouse wheel**: a window closed while the mouse was over its list left the wheel pointing at it, and the next
  turn of the wheel anywhere could raise an error; on a touchpad or a precise mouse the lists of pictures, buildings,
  diplomacy, editors, the family tree and the garrisons did not scroll at all (a small turn counted as none). One
  handler now serves the whole window: the area under the mouse scrolls, one step per turn, a list that scrolls
  itself keeps the wheel, the map keeps its zoom.
- **Going back to an older version**: settings, backups, a mod folder's mark, Module builder modules and report marks
  written by a newer version no longer stop this one - a setting of another kind reads as not set, a backup whose
  record this version cannot read is listed and refused in plain words before anything is put back (Undo back to an
  older backup checks every one first), a module made with blocks this version does not know says what it cannot
  read.
- **Medieval II small pennants yellow / white in the game after Banner...**: each small pennant (infantry, spear,
  cavalry, missile) has four looks on the banner picture - the game shows the other three on other units - and only
  the first was dyed; the rest kept the template's grey mix. All four now get the banner's design (found where the
  picture's see-through shape repeats the first; the saved template outlines them in grey, and your own drawing's
  first pennant is copied there too). **The cavalry banner's dark seam** through the symbol is gone too: its slit (a
  line no part of the model shows, dark on every faction's picture) is dyed with the cloth round it, as the game's
  own pictures have it.
- **Check mod files / moving a port (Medieval II): a port beside a town is a warning, not a fault** - vanilla
  Medieval II's own norman_prologue has two (Marseille, Venice) and plays.
- **Buildings and garrisons for many towns / Settlement names by culture: an error when the window was closed** while
  a filter was being changed ("invalid command name ...treeview") - the lists are no longer filled once the window
  is gone.
- **Banner... (Medieval II): the symbol stays on the cloth**: on a pennant whose cloth is not a rectangle (the
  L-shaped small infantry pennant), across the slit of the cavalry banner and on the triangle, the symbol ran past the
  cloth's edge - it now goes on the biggest square of cloth nearest its usual place (still dragged anywhere by hand).
- **No text cut at a window's edge** (every window checked on both games): the Events window's Change... / Another
  faction... buttons, the Campaign rules' explanations, the Units & armies town name and unit count, the Unit and
  Building editors' buttons (they wrap to a second row now), the Buildings tab's population line and its 'show levels
  too big' tick (on a line of its own), the Add-ons explanations, the Art tab's note, the Character editor's Set name /
  age and Remove buttons, the one-line hints with a '?' and the New faction warning beside the work buttons (on a line
  of its own) - they wrap now.
- **Medieval II battle banners from Banner... had no poles and were cut** in the game (the test mod in the game):
  the new sheet took its see-through parts from the faction's current sheet - once that sheet had been replaced by
  another picture, its alpha went with it, and the poles and much of the cloth turned see-through. The banner now
  takes them from the white template, which every faction sheet of the mod shares.
- **Make the campaign map 3 x bigger: a strip of beach off every river mouth.** Where the smoother new coast put a
  river's last tiles in the sea, the land was kept under the river, so a sandbar stood out into the sea at each mouth
  (`map_ground_types.tga`, `map_regions.tga` and the heights). The river now stops at the new coast, its end touching
  the sea; no river is left on the sea.
- **Terrain editor > Land and sea lagged while painting**: each move of the mouse read the whole of
  `map_features.tga` again and re-checked every tile of the stroke so far - about 7 x faster now (35 ms -> 5 ms a move on
  the Medieval II map), and no slower as a stroke goes on.
- **Make the campaign map 3 x bigger: the beach was a band 3 tiles wide.** The beach ground type now stays one
  tile wide along the new coast, as in both games' own maps (a beach tile away from the sea takes the land round it;
  a coastal tile where the old coast had a beach becomes beach).
- **Add-ons: an empty header line** (`// @signed` with nothing after it) took the next line as its value - a setting
  then showed its variable's name instead of its words.
- **Rome's campaign did not load after Campaign rules > The campaign switched a line on** (back to the menu: "Script
  Error in descr_strat.txt, at line 47"): a switch (rebelling generals, night battles...) was written at the end of the
  file's top, after the brigand / pirate values - both engines read those lines in a fixed order. A switch now goes
  in its place, and Check mod files names a top line out of order.
- **Rome's victory conditions**: the regions to hold and to take are written before the faction's goal (imperator /
  take_rome), as Barbarian Invasion writes them ("descr_win_conditions.txt: stopped parsing before EOF").
- **Medieval II units turned to grey stripes in battle after Recolour** (and any picture written into a compressed
  texture): the DDS header held a wrong size of the top level and the game read the texture by it. A texture now
  keeps the original's header; the size is the one the format means.
- **Units given to a faction (Roster, a new unit, Bring) stayed in another faction's colours in battle**: their
  battle model had no texture of the faction, so the game dressed them in another's. Recolour now gives the faction
  its own copy, made from an owner's texture and recoloured from that owner's colours; a card copied from another
  faction is recoloured from that faction's colours.
- **New events never came in the game (Rome)**: a new event was written at the end of `descr_events.txt`, after
  events of later years - the games read the events as a queue in date order, so it never fired. New events now go
  in date order (both games). The Events window shows beside each date the turn and the year it means (from the
  campaign's start date and timescale), and Medieval II's date is said right: years from the start, not a turn.
- **A historic event without its text stopped the game** ("event_manager: description_string", both games): a historic event now always gets its scroll's title and text (its name when none is given).
- **Medieval II: a fifth child broke the campaign's start**:
  `descr_campaign_db.xml` allows `max_number_of_children` (4 in vanilla) and the game stops reading
  `descr_strat.txt` at a family with more. Adding a child now raises the number in the same write (the game's copy
  goes into the mod), and Check mod files names a family over it.
- **Reports: the middle of a long game log kept each error's first line only** - the game writes what went wrong on
  the next line ("Script Error ... at line 3071" / "Population of 2600 is too high for a village"); both are kept.
- **A report no longer sends again what it sent**: a log sent before and not changed since (the game's
  `system.log.txt`, a crash report, the editor's older log) is left out - unticked, "already sent with R-..." - and
  the editor's own log goes only from where the last report left off.
- **The logs folder grew to tens of MB**: on every close the session folder took a whole copy
  of the game's `system.log.txt` (which can grow to 60 MB). It now keeps what a report would send (the log's start,
  the middle's errors once each, its end), no second copy of a game log that has not changed since, and the oldest
  sessions go when the folder is over 40 MB.
- **Recolour left a new faction's men in its template's colours in battle**:
  a battle texture the faction wears with others (a clone wears its template's) or that only the game's data holds
  (a mod in `mods/`) was skipped. The faction now gets its own copy in the mod, recoloured, and the model's line
  for it points at the copy (`descr_model_battle.txt` and the modeldb; Medieval II's weapons and shields too); the
  template's and the game's files stay as they are.
- **A town's population the game cannot take at the start**: each settlement level holds a range of people at the start (a village
  400 - 1500, a town up to 3500, a large town 9000, a city 18000...; Medieval II castles their own; read from
  `descr_settlement_mechanics.xml` when the mod or the game has it), and outside it the game stops reading
  `descr_strat.txt` - every town, army and diplomacy line after it is lost. The town window and the Settlements
  tab now have **the level follows the population** (ticked: the town grows or shrinks to the level that holds the
  people, its governor's building with it; unticked: the population is cut to the level's range, with a warning),
  a level change keeps the population inside the new level's range, and **Check mod files** names a town outside
  its range in the game's own words.
- **Rome: a new region gets its slaves resource** (the enslaved people of a town go there): the game stops at a
  region without one ("could not find slave resource in ..., every region must have one"); a region left without
  one after the map is painted gets one on a free tile of its own. Medieval II is left as it is.
- **Sack Settlement (REX) under the REX build of October 3**: it used Squirrel's `delete`, which that REX forbids
  ("Usage of 'delete' operator is forbidden") - it uses `rawdelete` now. Install the add-on again to update it.
- **A faction's pictures were taken for another's when one name holds the other** (`empire_east` /
  `empire_east_rebels`; the test mod's `ce_test` / `ce_test_later`): Faction emblem, Recolour and the Art tab wrote
  over the other faction's `symbol24_...` / `symbol128_...` pictures, and a new faction made from `empire_east`
  copied `empire_east_rebels`' pictures as its own. A file naming the longer faction is that faction's now.
- **A Medieval II faction's loading-screen logo after its emblem**: a new faction made
  from a template whose logo it shares (England and the Normans share one in vanilla) got its emblem copy named
  `symbol128_england_<new>`; it is named after the new faction now (`symbol128_<new>`). Making such a faction also
  says that it shows the shared logo until it gets its own (Art tab, Faction emblem...).
- **The bigger map (x3) moves the places in the campaign's scripts too** (a tester's game on Divide and Conquer:
  the armies the script spawns stood out in the clouds, at their old places). Every campaign-map place in
  `campaign_script.txt` (and the script `descr_strat.txt` names) goes to the middle of its 3 x 3 block, as in
  `descr_strat.txt`: spawned armies and characters (`x N, y M`), `reposition_character`, `move`,
  `move_strat_camera` / `snap_strat_camera`, `point_at_strat_position`, `reveal_tile` / `reveal_area` /
  `reveal_radius`, `console_command move_character` / `create_fort` / `create_resource`..., and the conditions
  `I_CharacterTypeNearTile`, `I_CharacterNameNearTile`, `I_FactionNearTile` (the distance grows with the map) and
  `IsPositionInRect`. Battle positions in the same scripts (prologue battles, camera bookmarks, unit orders) stay
  as they are. The trait / ancillary triggers follow when the mod has this one campaign. Lines it cannot read
  for sure, and Lua / Squirrel scripts, are listed to check by hand. Vanilla Medieval II's Mongol and Timurid
  invasions (224 places) and both prologues are moved whole.
- **A new faction lost its towns on the first turn** (the editor's own test mod, both games: "Faction Destroyed"
  at once). Since 0.29.1 a clone's first lines in `descr_strat.txt` had `denari` before the template's
  `superfaction` (Rome) / `ai_label` (Medieval II) - the games read those lines in a fixed order and then start the
  faction without its towns. They are now written in the games' own order (superfaction / ai_label,
  dead_until_resurrected, re_emergent, denari, denari_kings_purse), also for a faction that appears later and one
  made dead later. A mod already written so is found by Check mod files, and Load offers to put it right.
- **Medieval II victory conditions**: a part with no regions to hold was written `short_campaign take_regions 20`;
  Medieval II wants `hold_regions` right after `short_campaign` (even an empty list - all its own files have it) and
  stopped reading the file there, so every faction after it had no victory conditions ("No win condition has been
  set"). Written right now; Check mod files finds an old one, Load puts it right.
- **New unit step by step**: the recruit lines copied from the old unit kept the old unit's factions, so towns of
  factions the new unit does not belong to offered it ("...but the faction is spain and the unit ownership does not
  allow this"). They now name only the unit's owners.
- **Bug reports send the start of a long game log too**: a big `system.log.txt` came with only its last 1.5 MB (the
  last turns' AI notes), while the game's complaints about a mod's files come when it starts the campaign. A report
  now holds the log's start, every error and warning line of the middle (each once, with how many times) and its end.
- **Medieval II `.texture` pictures written right by Replace**: a picture replaced on the Art tab (a shared battle
  banner's own copy above all) was written as a TGA inside the `.texture` file; it now keeps the file's 48-byte head
  and the DDS inside it, in its size and compression, as Recolour already did.
- **Recolour keeps a bright colour of its own** (found by a tester: an emblem's gold wolf and laurel on red turned
  red): the edge growth past the colour test takes only a dull or dark rim, never a clean bright colour next to it.
- **Recolour makes its 'to' colours the faction's own too** (found by a tester: after a recolour the faction's
  primary and secondary colours were still the old ones): a box, ticked, writes them into descr_sm_factions.txt
  (and REX's .json) with the pictures - one shared writer with the Faction tab (edit.set_faction_colours).
- **Recolour's pictures fit the screen** (found by a tester: the 'after' picture ran past the window's edge).
- **Units and buildings brought from another mod no longer stop the game at start** (Barbarian Invasion's british
  legionaries brought into Rome; REX: "Hidden resource condition, unrecognised hidden resource 'britain'"): conditions naming a hidden resource or a resource this mod does not have are taken out of the
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
- **A new faction gets its faction-select buttons and the rest of its template's pictures**: (1) a template whose
  name holds `_` (greek_cities, romans_julii, papal_states) never had its loose pictures copied - symbol24 /
  symbol48 buttons, the loading-screen symbol, the campaign-select map; (2) a mod that keeps the game's own pictures
  (its folder holds only what it changed - common for REX and Medieval II mods) now gets copies of the template's
  pictures, unit cards and banners from the game's data, written into the mod (the game's data is never touched).
- **A battle_models.modeldb with models after its count is read** ("modeldb: 1585 characters left after 872
  models" stopped a new faction): models added by hand while the count at the top stayed as it was are kept
  exactly as they are, and Preview / Check mod say which ones the game never reads and which count would read them.
- **New regions on a big map get a colour** ("no free colour left"): the colour search walked only 200
  colours over and over; it now walks millions, so a map with hundreds of regions still gets new ones.
- **Recolour window: a touch-up stroke after the colours were changed** no longer raises an error.
- **Changes waiting for Apply are never written into another mod, and never dropped without asking**: loading
  another mod (Load, F5, Browse, the Mod list) or opening another campaign now asks first when changes wait (the
  editors' and the faction tabs'); every editor then reads the new mod. Before, an editor's changes stayed bound to
  the mod they were made on, and Apply on the new mod wrote them into the old one's files.
- **A template that does not play in the open campaign** (Medieval II's saxons outside the Norman prologue) is
  said plainly, with the campaign it plays in.
- **The game's log kept on close is named `game_system.log.txt`** in the sessions folder, and Tools > The game's log in plain words explains REX's "Game selection
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
- **The Map's legend is a palette**: its signs are buttons - pick a town, fort, watchtower,
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
- **"modeldb: a number expected at ..." on a mod's battle_models.modeldb**: a
  modeldb edited by hand - line breaks, tabs, two spaces between the values - is read as the game reads it (it was
  refused, so no new faction could be made); written back in the game's own form.
- **Wasteland regions (REX / M2EX)**: a region with `wasteland` where its town stands is read as a region without
  a town (it was read as a town called "wasteland"); Check mod no longer asks for its town pixel and names them
 ; a settlement given to one is refused.
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
- **The main window, reorganised**:
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
- **A unit given to a faction was listed twice in a building's description**:
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
- **The Map did not open on some big maps**: the political colours
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
  list". 'all' in a factions list now means every faction, everywhere the tool checks it.

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
  write": the line at the top and the message on Apply now say that it is the template of
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
- **"<army> stands on x, y - move it first" when moving a town**: taking Odessus sent its
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

Name lists of one's own and every town's names by culture in one table. Checked on a plain Rome
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
  imperial campaign was read with BI's factions.

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
  everything past it is not drawn. The 1-tile river brush now fills such steps itself, and
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
