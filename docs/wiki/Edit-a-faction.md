# Edit a faction

**Factions** at the top, its **Edit faction** tab (the first), then pick the faction. The window fills with what it is now; change what you
want. Untouched fields and towns stay exactly as they are.

**The rebels** (`slave`) are in the list too: their armies, fleets, agents, garrisons, towns, buildings and
units are edited like any faction's. A rebel has a `sub_faction` - the faction whose look and name list it
uses: a new rebel army (Maps, right click) asks for it, a captain for an empty rebel town takes the nearest rebel's.
The rebels are never playable and have no capital, leader or heir.

## Edit faction tab (the faction itself)

- Names, tooltip and campaign-screen text, colours, AI, money (denari), playable, religion (Medieval II).
- **Voice accent** (Medieval II): the voices the faction speaks with - its soldiers in battle, its general's speech
  before battle, its agents and diplomats on the map (`descr_sounds_accents.txt`). **Accents...** beside it shows
  every accent, its factions and the sound files speaking it; **New accent...** makes one that speaks like another
  until you give it sounds of its own (every sound file's block of that accent is copied, so nothing is silent);
  **Remove accent...** gives its factions another. A faction no accent names has no voice - Check mod files says so.
  Rome has no accents: a faction speaks the voices of its culture, so change the culture to change its voices.
- **Culture**: the faction's culture (`descr_sm_factions.txt`). The game takes from it the look of its towns, forts and ports on the map, its portraits and agents' pictures, the buildings and units open to that culture and the event pictures (Rome: the voices too). Preview says which units it gains or loses and which buildings in its towns the new culture cannot build (they stay). A new faction keeps its template's culture unless another is picked.
- **Rename...** beside the internal name changes the faction's code name (`egypt` -> `kemet`) in every file of the
  mod at once: the campaign, units, buildings, names, banners, models, texts' keys; its pictures are copied under
  the new name. The campaign scripts (`campaign_script.txt`: `I_LocalFaction venice`...) follow too; Lua / Squirrel scripts that name it are listed, not changed (code is changed by hand). One write, one backup -
  **Undo this write** puts it all back.
- **Towns**: **Towns on the map...** opens Maps - a click on a town adds it (their rebels leave; another
  owner's characters go to its other towns), another click takes it out to give it to the faction in **Removed
  towns go to** (rebels by default); **Done** brings you back, nothing lost. **Capital on the map...**: one click.
- **Capital** puts that town first in the faction's block.
- **Leader** and **heir**: new names (from the faction's name list) and ages.
- **Leader's title** / **heir's**: what the game calls them - King, Duke, Emperor, Grand Prince... Medieval II:
  only the word of 'King %S' / 'Prince %S' (`text/expanded.txt`, %S is his name) and the former leader's title
  change; Rome: the whole leader's / heir's label (`expanded_bi.txt`). A mod whose texts are only in a
  `.strings.bin` is told so in Preview.
- **Name list...**: the faction's men's names, surnames and women's names, typed in three steps (see
  [[New faction]]). Names its characters and family already carry stay in the list (Preview says which) - the
  game crashes on a name that is in no list.

## Units & armies

- A town's garrison opens as it stands now (marked *unchanged* until you click a card).
- The faction's armies, fleets and agents already on the map: change units, remove (right click its row) an agent, captain or
  admiral (never a family member).
- New armies, agents and fleets: Maps (right click the map); a double click on a row opens the Map
  editor on it.

## Buildings

Every building chain the faction may build, with the game's picture of each level. The settlement level and
population follow a governor's building (a town with a governor's palace becomes a large town).

**City or castle (Medieval II).** *Settlement is a* (top right of the Buildings tab) turns the town into a castle or
a city. In Medieval II that is the settlement's own line in `descr_strat.txt` (`settlement castle`) together with
its buildings, which are either a city's or a castle's (each level says which in `export_descr_buildings.txt`). The
tool converts the buildings the game's own way: a level becomes the level its `convert_to` names in the matching
chain (a city's `wooden_wall` becomes a castle's `castle`, `town_guard` becomes `drill_square`, a church a chapel),
a level with no such line goes (a castle has no market or town hall), and the governor's building is fitted to the
settlement (a castle's level equals the settlement's, a city's is one below; a village castle has a motte and
bailey, a village city none). Only the kind's own buildings are offered afterwards. Castles go up to a large city
(a citadel); a huge city stays a city. Rome has no castles, so the choice is not shown there.

## Other tabs

- **Map**: drag the faction's characters, see [[Campaign map]].
- **Diplomacy**: per faction the **Status at the start** (neutral, **alliance** or **war** on the first turn, both
  games) and the AI feeling both ways (Rome: a number, lower is better, `600 (enemies)`; Medieval II: -1.0 to 1.0).
  A status pulls the feelings along; hover a column's **?**.
- **Family tree**: the button at the top of the Edit / New faction tab opens it in the form's place.
- **Victory** (on the Edit / New faction tab, under the leader): regions to hold, how many to take, factions to outlive, Rome's
  goal (be emperor / take Rome) - for the long and the short campaign. Only the player needs them, but a playable
  faction without them, or naming a region that does not exist, can crash the game. The list of regions or
  factions takes many at once: drag over the rows, Shift-click a run, **Tick all shown** (with Find), **tick a whole
  group** (every region a faction holds), or **On the map...** - click towns there, their regions turn yellow.
- **Art**: see [[Faction art]].
- **Models**: who is shown by which figure on the campaign map, their textures, 3D - see [[Faction art]].
- **Roster**: give or take units and building levels; **By buildings**: a building's levels and their units -
  click a unit to add it to a level and every level above - see [[Units and buildings]].
- **Family**: characters, traits, the family tree - see [[Characters and portraits]].

**Preview changes**, then **Apply changes**. One Apply writes every tab at once, with a backup. Picking
another faction with changes not written asks: apply them, drop them, or stay. **New faction** and **Edit faction**
are the first two tabs (Edit faction is the old Faction tab); going to Maps, the other one or any other editor drops nothing - each keeps
its work not written yet until you come back.
