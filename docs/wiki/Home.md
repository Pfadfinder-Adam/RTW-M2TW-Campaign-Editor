# RTW & M2TW Campaign Editor

A campaign editor for **Rome: Total War** (with Barbarian Invasion and Alexander, plain or modded, on REX or
the original exe) and **Medieval II: Total War** (with Kingdoms, on M2EX or the original exe). It edits the
game's or a mod's own data files, shows every change before writing it, keeps a backup and can undo it byte
for byte.

**Download:** the latest `RTW-M2TW-Campaign-Editor.exe` from
[Releases](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/releases) (only from there - see [[Installing]]) ·
**▶ Video:** [what the editor does, in a few minutes](https://www.youtube.com/watch?v=m1sCPg-Lzsw) ·
**💬 Discord:** [questions, ideas, news](https://discord.gg/uqA9MEn4Z)


## 🎬 More videos

All on my YouTube channel **[Pfadfinder](https://www.youtube.com/channel/UC8j5rv6mTmtvRR8u7NmaCvQ)** - each one checked in the game:

<table>
<tr>
<td align="center" width="25%"><a href="https://youtu.be/z0T723riXaU"><img src="https://img.youtube.com/vi/z0T723riXaU/mqdefault.jpg" width="200" alt="Editing rivers, fords, cliffs"><br><b>▶ Editing rivers, fords, cliffs</b></a></td>
<td align="center" width="25%"><a href="https://youtu.be/mTdRAWympuw"><img src="https://img.youtube.com/vi/mTdRAWympuw/mqdefault.jpg" width="200" alt="Editing a height map"><br><b>▶ Editing a height map</b></a></td>
<td align="center" width="25%"><a href="https://youtu.be/6WAdnGovGzA"><img src="https://img.youtube.com/vi/6WAdnGovGzA/mqdefault.jpg" width="200" alt="Searching the map for settlements and units"><br><b>▶ Searching the map for settlements and units</b></a></td>
<td align="center" width="25%"><a href="https://youtu.be/umwRyWkHoDE"><img src="https://img.youtube.com/vi/umwRyWkHoDE/mqdefault.jpg" width="200" alt="Settlement names by culture"><br><b>▶ Settlement names by culture</b></a></td>
</tr>
</table>

## A look inside

| | |
|---|---|
| ![Edit a faction](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/edit_faction.png) | ![The campaign map](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/map.png) |
| **Edit a faction** | **The campaign map** |
| ![Terrain editor](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/terrain_editor.png) | ![Units](https://raw.githubusercontent.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/main/docs/images/unit_editor.png) |
| **Terrain editor** | **Units: model and voice** |

## What this tool is for

One goal: **a bridge between the modder and the game's files.** The editor gives you access to every corner of the
game's data - factions, campaign map, towns, armies, characters, units, buildings, diplomacy, texts and pictures - for
Rome: Total War (with REX support) and Medieval II (with M2EX support), and takes over the slow part: finding the
right files and lines, keeping the tied ones in step, checking for what the game would crash on.

It is for anyone who mods:

- **Mod teams** - work that took hours of file digging done in minutes.
- **Beginners** - a place to start making something of your own without learning every file format first.
- **Players** - something of your own in your favourite mod, just for yourself: a faction you always wanted to
  see, different starting positions, a changed map. Nothing has to be published.

What it is not: a 3D modelling program. Models can be viewed and swapped between units, but making or editing
models is left to the tools built for that. The one exception: recolouring the faction colour painted on a unit's
texture (vanilla-style uniforms), so a new faction's troops wear its own colour (Art tab > Recolour).

Medieval II keeps its data packed: the editor offers to unpack it once, with the game's own unpacker. The engines
REX / M2EX beside the game lift every limit: with them the editor knows no limits at all (no refusal, no warning -
their setting lines are rewritten to fit); the original exes' limits apply only without them. Features marked 🧪 in
the [Roadmap](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/blob/main/ROADMAP.md) are out but not yet confirmed in the game - reports welcome.

## Made to be easy

The aim of this tool is to make modding friendly for everyone, not only for people who know every file of
the game by heart. You work with factions, towns, armies and the map - the tool finds the files, the lines
and the formats for you:

- **No digging in files.** Pictures are made the right size and format and put in the right place; names,
  texts, units, cards and buildings that belong together are kept in step for you.
- **See it before it happens.** Preview shows every file and line before anything is written.
- **Nothing is lost.** Every write has a backup, and Restore gives the files back exactly as they were;
  Undo / Redo work in the window.
- **Mistakes are caught early.** Things the game would crash on (a name it has no text for, an army on a
  tile it refuses, a town with two settlements...) are refused or warned about, with the reason in plain
  words.
- **Set-up problems fixed with a yes.** Things that stop the game from starting are found when you load it
  and fixed only when you agree.

Something confusing or hard to find? That counts as a bug too - tell us ([[Reporting a bug]]).

**Made a mod with it?** Please say so where you share the mod and link to the editor - one line is enough:
`Made with the RTW & M2TW Campaign Editor: https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor`
(a request, not a condition - thank you!).

## Start here

1. [[Installing]] - where to put the exe, what it makes next to it.
2. [[First steps]] - load a mod, pick a campaign, a separate mod folder.
3. [[New faction]] - a new faction cloned from a template.
4. [[Edit a faction]] - change a faction that is already in the game.

## Guides

- [[Campaign map]] - the map, towns and ports, characters, new armies, new regions.
- [[Terrain editor]] - ground, rivers, fords and cliffs.
- [[Faction art]] - every picture of a faction, banners, the campaign-select map.
- [[Characters and portraits]] - family tree, traits, portraits and the portrait library.
- [[Units and buildings]] - the unit and building editors, battle models in 3D, unit voices, the roster, unit packs.
- [[Campaign rules and Add-ons]] - every campaign setting in plain words; Sack Settlement and other add-ons; the Module builder for your own.
- [[Backups and Restore]] - how nothing gets lost.
- [[Reporting a bug]] - what to send when something goes wrong.

## Why a clone?

A new faction starts as a **copy of a faction that already works**. It starts in the game at once, so every
change after that can be checked in the game straight away, instead of building a faction from nothing
before the first test. The clone **adds** a faction and never touches the template: files the new faction
needs are copied under its own name (Epirus cloned from Macedon gets `standard_epirus`, `symbol128_epirus`,
`map_epirus`...), and its lines point at them.

## What is where

- [ROADMAP](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/blob/main/ROADMAP.md) - what it
  does, what is being tested, what comes next.
- [CHANGELOG](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/blob/main/CHANGELOG.md) - what
  changed in each version and what was tested in the game.
- [[Every feature]] - everything the editor does, area by area.
- [[Reference]] - how each window and button works, in full.
- [[What it changes]] - the game files a new faction writes, and the command line.
- [[FAQ and known limits]] - common questions and what does not work yet.

The editor is free. If it saves you time, a coffee on [Ko-fi](https://ko-fi.com/pfadfinder) or [GitHub Sponsors](https://github.com/sponsors/Pfadfinder-Adam)
keeps new features coming.
