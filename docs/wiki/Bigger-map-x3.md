# Bigger map (x3)

The whole campaign map made 3 x bigger, with everything tied to it.

**Bigger map (x3)...** (Maps, beside the zoom) (beta), Rome (REX) and Medieval II (M2EX). Each tile of
`map_regions.tga` becomes a 3 x 3 block; everything tied to the map is converted with it:

- **Positions** (`descr_strat.txt`, `descr_events.txt`, ...): towns, characters, fleets, resources, forts,
  watchtowers, wonders and event places go to the middle of their new block.
- **Coast and borders**: natural - the coastline winds with bays and capes and the borders between regions wind
  too, instead of 3 x 3 squares and straight 45-degree cuts (the old map's own relief bends
  them - a cape where a ridge comes down to the sea, a bay where a valley does, a river on the lower side of its
  valley - with a fractal coast's small detail, rougher where the land is steep; the same map always comes out
  alike); every block's middle keeps its old
  value, so nothing changes under a town, army or resource, and every region stays in as many pieces as before. The rules the games' own maps keep are kept: every town has its own region (or sea) all round it,
  every port stands on a coastal land tile touching the sea and its region, and a region `descr_regions.txt` does
  not list still counts as land.
- **Heights**: `map_heights` the natural way - bent with the ground, crags on the mountains (plains stay flat),
  volcanoes keep their cones, lakes get gentle banks, land touching water stands clearly above it (no flickering
  wedges on the coasts, no islets in navigable rivers),
  every river in its valley, no slope steeper than the old map's steepest -, with **the same coast as `map_regions`** (every
  tile's middle point is sea exactly when the tile is - as in both games' own maps), and
  **`map_heights.hgt`** - the game's float copy, which it reads instead of the picture and never rebuilds - written
  at the new size too. The hills, mountains and sea floor are made **3 x higher** (`max_land_height`,
  `min_sea_height` in `descr_terrain.txt`): the land is 3 x wider, so the slopes stay as steep as they were
  (or keep the old heights - a choice in the window). The sea ground types follow the heights' new coast.
- **Rivers**: 1 pixel wide (the game crashes on a 2-pixel river), drawn the way rivers run - bends rounded, gentle
  meanders on straight runs (never twice the same, the same map always alike), side by side pixels only; a river mouth runs on to the new coast and ends on the land touching the water - never a pixel on the water (no land is left under it). Medieval II's land bridges stay unbroken lines too. No cliffs and no beach are drawn (paint them where wanted). Small islands and lakes keep their size and come out round (no crosses or clovers), capes one tile wide stay whole strips; the sea along the coast is shallow, the line to the deep water smooth.
- **Ground and climates by tile**: every new tile gets the ground type and climate of the old tile it lies in (a
  forest stays a forest), the edges where two kinds meet winding as the coast does - no 3 x 3 steps.
- **Pictures**: `map_trade_routes`, fog, roughness and disasters scaled with exact colours. The minimap (radar maps)
  is kept as it is: it shows the same land, and a 3 x bigger one can crash plain Rome.
- `descr_terrain.txt` gets the new size; `map.rwm` is deleted so the game rebuilds it.
- Preview of every file, one backup, Restore byte-exact.

<img src="https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/bigger_map_coast.png" width="700" alt="The coast of Italy made 3 x bigger: before (squares), after (smooth)">

<img src="https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/bigger_map_natural.png" width="700" alt="Regions of Italy and Greece 3 x bigger: in squares (left), the natural way (right)">

Scripts follow too: every campaign-map place in the campaign's scripts (spawned armies and characters, `reposition_character`, `move`, the camera, `reveal_tile`, forts and resources made by `console_command`, 'near a tile' and 'in a rectangle' conditions) goes to its block; battle positions in the same scripts stay. Lua / Squirrel scripts that place things by tile (not the engines' own interface scripts) move too; lines the editor cannot read for sure are listed to check by hand. The Map's **Scripts** layer shows every tile the scripts name as a scroll: drag it to move the place, double click it to edit the lines round it.
Without REX / M2EX the original exes stop at
510 tiles - the tool warns. Checked on both vanilla campaigns (103 / 112 towns, 177 / 216 characters, 75 / 77 ports
in place, no river on the sea, every river end at the sea, a river or the map's edge as in the original). The first
alpha (0.24-0.27) left the old `map_heights.hgt` in place and kept the heights - flat, square-coasted maps; make the
map again from a backup with this version. Video of the first alpha: [rescaling the whole map](https://youtu.be/kkfI-WulRmU).
