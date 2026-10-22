# First steps

1. **Close the game.**
2. **Browse...** and pick the mod's `data` folder, for example
   `...\Rome Total War Gold\HLR\data`, or the game's own `data`. Next time the tool opens the last mod by
   itself; **Mod** at the top lists every mod of the game folder.
3. Pick the **campaign** (usually `imperial_campaign`).
4. Choose the work at the top: **Maps** (its **Terrain** tab paints the ground, rivers and climates, its
   **Coast & heights** tab the coast and the heights), **Factions** (its tabs **Edit faction** and **New faction**), **Units**, **Buildings** or **Characters**.

Every change waits until you press **Preview changes** (shows every file and line) and **Apply changes**
(writes it, with a backup). **Undo** / **Redo** step back through what you did in the window.

**Scrolling**: every list, table, page and text shows a scrollbar while there is more to see; every list, table, page and read-only text also scrolls by the mouse wheel, by **dragging** it with the left button (it follows the mouse, up / down and left / right) and by the **middle button**: press the wheel and move the mouse - the further from where you pressed, the faster it scrolls, both ways (held: it stops when you let go; a click: it goes on until the next click or Esc). A text you can type in keeps the left drag for selecting words. The map is as before (the right button moves it).

## Your own look and language

**Tools > Edit the editor's look...** turns the windows into a layout you can change: a click picks a button, tick or
label (a yellow frame); drag it with the left button before or after any other piece, in any bar of any window (in a
bar of another part of the window a copy of it stands there - it does the same and greys out with it); its right
click renames it, gives it a hover text, a width or its own colours, font and emoji, hides it or takes it back. The small bar beside it holds **Undo**,
**Hidden pieces...** (show one again), **Back to how it was**, **Save my look...** and **Load a look...** (to share
one). The look is kept for every start in `CampaignEditor_look.json`; a piece whose words a new version of the editor
changes simply goes back to its place.

**Tools > Layout board...** does the same on one big canvas, with every page already laid out: each work of the
main window, the tabs of Maps and Factions and the Tools windows side by side (the editor opens each one in turn the
first time and keeps their pictures; **Refresh all pages** takes them again, after you load a mod for example). The
wheel zooms, the middle button moves the board. Drag a button, tick or label with the left button: it stays exactly
where you drop it. On the way its edges and middle stick to the lines the other pieces (and the window's edges)
stand on - a pink line shows which - and, with **Grid** ticked, to a grid (4, 8, 16 or 32 px; **Stick to lines**
turns the lines off). Hold **Alt** (or tick **In a row**) to put it into the row beside the piece nearest to where
you drop it instead. Drag a corner of the picked piece to size it (it sticks the same way); the arrows move it a
pixel (Shift: ten). Right click a piece: Rename, Hover text, Size in pixels, Width in letters, **Colours, font and
emoji...** (its background and words' colour, a font, size and bold / italic, an emoji before its words - a preview
shows it; **All the editor's own** takes them off), **Copy its look** / **Paste the look** (the same colours, font and
emoji on another piece), Hide, Back into its row, Back to how it was, Show it in the editor; right click a page: refresh it, show it in the editor, its pieces
back to how they were. Your changes are a draft drawn on the board (the piece where it goes, its old place greyed):
**Accept** puts them all on the editor and keeps them in the same `CampaignEditor_look.json`, **Discard** drops
them, **Undo** / **Redo** step through them; after Accept, **Undo** and **Back to how it was...** take it back.
**Appearance** on the board's bar opens a panel at its side for the whole editor at once (as Obsidian's Appearance):
Light or Dark, a font and size for every window, and a swatch for each colour - background, words, fields and lists,
buttons, tabs, the picked line, links... - and, folded under them, for each button with a colour of its own (Play,
Report a bug...). Click a swatch to pick a new colour: every window takes it at once and keeps it for every start;
its arrow gives the look's own colour back, **All back to the look as it comes** all of them. The questions and file pickers Windows draws itself are not on the board.

**Settings > Language of the window** puts a language on every window, the hover texts and the menus; **Add a
language file...** puts one in. **Words to translate...** writes every word of the windows into a file - fill in the
translations, add the language's name and yours, and send it: it comes with the editor. Words a file has none for
stay English.

## Medieval II

Medieval II keeps most data in `packs`. Load the game folder (or a Kingdoms campaign's folder, such as `mods/british_isles`) and the tool offers to
unpack it with the game's own unpacker (the campaign's own `unpack_britannia.bat` and the like for a campaign; it copies the two DLLs the unpacker needs, `msvcp71.dll` and `msvcr71.dll`, next to it). Set-up
problems that stop the game from starting (M2EX's `vegetation_source text` without the raw vegetation maps; in both games a
character's name that no list of `descr_names.txt` has any more) are found on Load and fixed with a yes.

## A separate mod folder (recommended)

**New mod folder...** after loading the mod you build on makes a copy of it next to it (for example
`HLR_Saba`) with its own start file. Your base mod is never touched. On the **plain game** it makes a **thin** mod
instead: nothing is copied (made at once, no disk space) - the mod holds only what you change and the game reads every
other file from its own `data`; the editor puts a game file into it the first time you change it (the map's own files -
pictures, heights, `descr_regions`, `descr_terrain`, not `map.rwm` - the first time you change the map; the game then
builds its map again there; a campaign's `descr_strat`, events and scripts only when you change them). Copies of
the game's files a thin mod still holds unchanged (an older version made them) are named by Check mod files, with
*Take them out* (backed up). Before the first
write into the game's own data or a mod it did not make, the editor asks once: *Make my own mod folder* or *Write
here*.

- **Rome / REX:** `<game>\<name>\`, started by `Start_<name>.bat` (`-mod:<name>`).
- **Medieval II:** `<game>\mods\<name>\` with `<name>.cfg`, started by `Start_<name>.bat` (under M2EX: `M2EX.exe --features.mod=mods/<name>`).

**Start the game** (the green button at the bottom right, beside Tools) says what it starts - *Start Rome - CE_Test*,
or in amber *Start Rome - no mod* when the game's own data is loaded - and starts the game with the mod that is
loaded: its own start script, else the line the engine's own start scripts use (`REX.exe -mod:<name>` - or
`-mod:mods/<name>` for a mod in the game's `mods` folder -, `-bi` /
`-alx` for the expansions, `M2EX.exe --features.mod=mods/<name>`). Apply your changes first - the game reads the
files on disk; the button names any change not written yet. Before it starts the game it checks: a start script
that starts an exe the game folder lacks is refused in plain words, a Medieval II `.cfg` that does not name the
mod's folder is asked about, and a 32-bit game exe that can use only 2 GB of memory is noted in the status line.

A mod built on another mod (HLR) holds all of it - the game reads one mod folder, never a chain. Every file is
copied, so the new mod stands on its own - to share, to zip, to change in any program. For a mod
you keep to yourself, tick **Hard links instead of copies**: text files are still copied, everything else becomes
a **hard link** (the same file on disk under a second name) - no extra disk space, Explorer still shows full
sizes, and deleting the new mod folder never touches the game. Do not overwrite a linked texture in place from
an image editor.
