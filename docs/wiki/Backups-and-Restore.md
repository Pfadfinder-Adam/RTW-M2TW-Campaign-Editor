# Backups and Restore

Every **Apply** first saves the files it changes in `CampaignEditor_backups` next to `data` (older versions' backups are listed too), one folder per
write. **Tools -> Restore a backup...** puts them back **byte for byte** and removes what that write created.
The list shows each write by date, faction and number of files, newest first. Pick the one to go back to and
**Undo back to here** undoes it and every write after it in one go (newest first, as they must be); pick the
lowest line to get the files back as they were before the tool's first write. A backup that was put back
(Restore or **Undo this write**) is deleted - it holds nothing the files do not have now; the `*_restored` folders
older versions left are taken away when the mod is loaded. **Tools > Settings > Folders > Delete this mod's
backups...** deletes every backup of the loaded mod after a question: the files stay as they are, only the way back
goes.

- **Preview changes** shows every file and line before anything is written.
- **Undo** / **Redo** (Ctrl+Z, Ctrl+Y) step back through what you did in the window before Apply.
- **Check mod files** reads every file the tool uses and reports what it cannot make sense of; the deep check
  rehearses an edit and a new faction for every faction in memory. Nothing is written. The problems come worst first,
  grouped by when the game would meet them (it closes before its menu, the campaign does not load, something is lost,
  in battle, while playing), each with a button to the place that puts it right. Medieval II: a
  faction's `ai_label` (in `descr_strat.txt`) that `descr_campaign_ai_db.xml` lacks is named - the game stops at the
  campaign's start with "Could not link faction ... to AI label"; so are a governor's building that does not fit
  its town's size (a castle's must be its level, a city's one below) and a port with no sea on any of its four sides.
  Both games: what the games' own readers refuse, in their words - a faction block missing from the playable /
  unlockable / nonplayable lists, `event` lines in `descr_strat.txt`, a family member off the map the game leaves
  out (a woman with no husband or father, a child with no father), a building factions list without its last comma,
  a recruit line for a unit the unit file lacks and a faction that may build a level but not the one below it (these
  two not with REX). Every unit is checked as the games read it: its lines, its owners, and without REX / M2EX
  its men (Rome 6-60, Medieval II 4-100, others 1-300), extras (300), officers (3) and Rome's attributes. A unit
  without an ownership line is only a note: the games give it to every faction.
  Also from the games' readers: pikes without phalanx, a unit with none of square / horde / phalanx, a projectile
  that does not exist, a unit line its kind does not take (a mount on foot soldiers, two of mount / engine / animal,
  a handler with no animal), a mount descr_mount.txt lacks, a missile with under 2 arrows (Rome: or under 20 m of
  range; with REX only 0), a building upgrade pointing down, a wrong settlement_min, a port building with no port on the
  map; notes for a misspelt word in a faction's first lines, a resource on sea, units without their own card.
  A texture named inside a campaign-map model (`.cas` of a resource, a settlement, a faction symbol, or a model in
  `descr_model_strat.txt` with no texture line of its own) that is not there is named too - both games stop as the
  campaign loads with "Failed to find texture". Medieval II's `battle_models.modeldb`: a name whose number before
  it is not its length (a space too many or too few by hand - the game reads the file by those numbers) is a fault,
  two models of one name a note. A file the banners, standards or projectile files name that is not there, or is
  written as a whole path on one PC (`C:\...`), is named; an event without its words in `historic_events.txt` is a
  note (the game shows its scroll empty). The rivers of the campaign map: a river piece joined to no sea, map edge,
  source or other river by a side is left out by the game; 2 x 2 river blocks and rivers rejoining themselves are
  notes.
- **Check mod files** with a faction picked also says whether it is **complete**: first what the game itself stops
  on for it (it is listed at the top of descr_strat.txt with no block, or has a block in no list; descr_character.txt
  gives it no general), then every file where every other
  faction is named and this one is not (the game or its screens would miss it), with a faction of its culture to
  copy the lines from; files most (not all) factions are named in are only noted - real factions go without them.
- **Check mod files** with a faction picked also lists everywhere that faction is named in the whole mod, and which files are the game's own,
  changed by the mod, REX's or the mod's.
- A [separate mod folder](First-steps#a-separate-mod-folder-recommended) keeps your base mod untouched.
- **A file Windows will not write** (held by the game or another program, read-only, no rights in the folder,
  the disk full, a path over 260 characters): Apply says which file and what to do, and puts back what it had
  written already - the mod is never left half changed. Restore that meets such a file stops, keeps the backup
  whole, and simply runs again once the file is free.
- **Backups of a newer version** stay listed after going back to an older one; a backup it cannot read is refused
  in plain words, nothing changed - restore it with the version that made it.

## Check and install a pack

Many mods come as "copy the data folder over the game". **Tools -> Check and install a pack...** opens such a
pack (a `.zip` or its folder) and lists every file of its `data` folder against the loaded mod before anything is
written: **new**, **the same** as the mod's, or **replaces** the mod's - and what a replacement would lose:

- a file of **REX's own** (REX's version would be gone);
- a **picture of another size** than the one it replaces - for a page of interface icons, the icons that would
  fall outside it;
- a **text file**: how many lines differ. One that differs in a few lines goes in as **only its changes** - the
  pack's changed and added lines are taken, lines it would drop (REX's, the mod's own) stay. One that differs in
  most lines is another mod's whole file and is kept back.

Lines that lose something are red and set to keep the mod's file; double click a line (or pick lines and use the
buttons) to choose **put in**, **only its changes** or **keep this mod's**. **Preview**, then **Install** writes
it with a backup - **Restore** takes the whole install back. Files outside `data` (readmes) are only listed.

## Deleting a whole mod

**Tools > Delete this mod's folder...** (red) deletes the loaded mod's folder with everything in it - its files,
its backups, its start script. It asks twice; the second time you type the mod's name. Restore cannot bring it back.
Only a mod folder (`<game>/<mod>` for Rome, `<game>/mods/<mod>` for Medieval II) can be deleted - never the game's
own data or Barbarian Invasion's / Alexander's.

