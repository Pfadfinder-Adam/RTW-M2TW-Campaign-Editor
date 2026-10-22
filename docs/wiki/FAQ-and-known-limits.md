# FAQ and known limits

## FAQ

- **Does it work with my mod?** Very likely: it reads the mod's own files and assumes nothing about them (tested on
  the plain games and on testers' mods such as HLR and Kirsi's Bigger Map). Load it, press **Check mod files** - if
  something is off, **Report a bug / Suggest** sends the logs.
- **Do I need REX / M2EX?** No, but they are best: without them the original exes' limits apply (21 factions in Rome,
  200 regions...) and some things need them (wastelands, add-ons, your own modules). With them the editor knows no
  limits at all.
- **Should I make my own mod folder?** Yes - **New mod folder...** first: the game or the mod you build on stays
  clean. The editor asks once before it writes into a mod it did not make.
- **Windows warns about the exe.** It is not signed yet (see [Code signing policy](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor#code-signing-policy)). Download it only from
  [Releases](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/releases); Windows SmartScreen may ask once - *More info > Run anyway*. An antivirus (Avast...)
  may hold a new version back for a while: one-exe Python programs are often flagged at first - let it finish or mark
  the exe safe.
- **How do I go back?** **Undo this write** right after a write, or **Tools > Restore a backup** - every byte back.
- **Is it tested?** Tested on the plain games - Rome: Total War (with REX), Barbarian Invasion, Medieval II: Total War (with M2EX) - and on testers' mods (Barbarian Empires REX Ultimate Edition / HLR, Kirsi's Bigger Map and others). It reads a mod's own files and assumes nothing about their contents, so other mods of these games should work too. Reports are welcome.

## Which games and exes

| Game | With the original exe | With the engine beside it |
|---|---|---|
| **Rome: Total War** (Gold / Steam) | `RomeTW.exe` - the game's own limits apply (21 factions, 200 regions...) | **REX** - no limits at all, wastelands, add-ons and your own modules |
| **Barbarian Invasion**, **Alexander** | `RomeTW-BI.exe`, `RomeTW-ALX.exe` | REX (`-bi`, `-alx`) |
| **Medieval II: Total War** (and its Kingdoms campaigns) | `medieval2.exe` / `kingdoms.exe` | **M2EX** - no limits, wastelands, add-ons and your own modules |

Any mod of these games loads - a whole one (HLR) or one that holds only the files it changes (the game reads the rest
from its own `data`, and so does the editor). Medieval II keeps its data packed: the editor offers to unpack it once,
with the game's own unpacker.

## Known limits

- **Faction count.** The game stops at a set number of factions, `slave` included: plain Rome 21, Medieval II 31. REX and M2EX read it from `max_factions` in `descr_ex.txt` (REX ships 21, M2EX 31). A mod reads only its **own** `data/descr_ex.txt` (and `descr_caps_ex.txt`) - without one the engine's built-in defaults hold, not the game's copy - so the tool raises `max_factions` in the mod's own file by itself with every new faction and with any write that finds it too low (REX and M2EX have no faction limit of their own) and offers on Load to copy the game's engine files into a mod that lacks them. Only the original exes stop at 21 / 31; over it the game closes at start ("Too many factions described here, maximum is(21)").
- **Art.** A new faction starts with copies of its template's pictures under its own name (banners, logos, symbols, cards) - replace them on the **Art** tab; the tool does not draw art.
- **Strings.** Copied strings keep the template's text apart from the names ("the wicked Seleucids..."). Edit them in `data/text` if you care.
- **Character names.** A leader, heir or family member takes names from the faction's name list (the game crashes on a name without a string); a faction's own names go in with **Name list...**.
- **In the game.** Not every feature has been confirmed in the game yet - reports welcome.
- **A mod that holds only the files it changes** (REX `-mod:` and Medieval II `mods/<name>` leave the rest to the game's `data`) loads as the game reads it: every file the mod lacks comes from the game's `data`. A change to such a file goes into the mod as its own copy - the game's files are never written - and Restore takes the copy away. Medieval II: the game's own `data` must be unpacked first (load it once - the editor offers to unpack it). The engines' own `descr_ex.txt` / `descr_caps_ex.txt` are read from the mod alone, as REX / M2EX read them.
- **Medieval II: Kingdoms campaigns** (Americas, Britannia, Crusades, Teutonic) are checked only on made-up copies so far - reports from them welcome.
- **The bigger map (x3)** is new ground for the game's AI (pathfinding, slower turns) - try it in the game before a long campaign.
- **Other campaigns.** One campaign is edited per run. Run again for another campaign; the faction files see the faction already exists and refuse, so add those campaigns by hand for now.
