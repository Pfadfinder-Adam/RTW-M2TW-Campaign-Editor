# Installing

> ⚠️ **Only download the editor from this repository's [Releases](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/releases) page** (or a link the author posted or approved). Never take the exe - or a "fixed" / "patched" copy of it - from another site, a file-sharing link or someone in a chat, and don't pass it on that way: a copy from elsewhere can be changed to harm your PC. Share the link to the Releases page instead.

1. Download `RTW-M2TW-Campaign-Editor.exe` from
   [Releases](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/releases). No install needed.
2. Put it into the **game's folder** - beside `RomeTW.exe` / `medieval2.exe` (where REX or M2EX goes too).
3. Start it from there, or make a shortcut to it (on the desktop or anywhere).

Started from somewhere else (the Downloads folder, the desktop)? On the first start of each new version it offers
to **put itself into the game's folder**: press **Pick the game's folder...**, choose the folder where `RomeTW.exe`
or `medieval2.exe` lies (it checks that the game is there), and it copies itself there with its settings, puts a
shortcut on the desktop if you like, and starts from there. The copy you started can be deleted then. **Not now**
asks again with the next version; **Don't ask again** never asks. Tools > Settings > Folders has the same button.

It then finds the game and every mod in it by itself (Rome: `<game>\<mod>`, Medieval II: `<game>\mods\<mod>`),
and whether REX / M2EX is installed (the status line says so after Load). Have both games? Load a mod of the
other one once with **Browse...** - from then on the Mod list shows the mods of both.

Beside the exe, in a folder of its own - `CampaignEditor` (not among the game's files) - it keeps what is its own:

- `CampaignEditor_settings.json` - what it remembers between starts;
- `CampaignEditor_logs` - its log (`CampaignEditor.log`), the logs zips, and `sessions`: on every close the
  session's log and a copy of the game's newest `system.log.txt` (as `game_system.log.txt` - the game's own log, its
  errors are the game's, not the editor's) are saved there by themselves. **Report a bug** sends them.
- `CampaignEditor_addons` - add-ons you added.

**An update** is simply the new exe in the same place; the settings stay. Versions up to 0.33 kept these files right
beside the exe: there they keep working, and the editor asks once whether to move them into `CampaignEditor` (a
yes moves them, nothing lost). An older version's `RTW-M2TW-Campaign-Editor-files` folder is moved in by itself.

## Going back to an older version

Something wrong with a new version? Every version stays on the
[Releases](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/releases) page: download the one you
want and put its exe in place of the new one. Nothing else needs to change:

- **your mods** stay as they are - the exe is not part of them;
- **the settings** a newer version wrote are read where this version knows them; a value it keeps in another form
  takes this version's default;
- **backups** a newer version made are listed under Restore; one it keeps in a form this version does not read is
  refused in plain words and nothing is changed - restore it with the version that made it. The safest way:
  restore what you want undone *before* going back;
- **add-ons and Module builder modules** a newer version made stay in the game; this version shows what it can
  read of them.

Then send a report (**Report a bug**) saying what went wrong with the new one, so it can be fixed.

## The browser or Windows warns about the exe

The exe is not signed yet (a free certificate from the SignPath Foundation has been applied for), so the
browser and Windows SmartScreen may warn about it:

- the browser: **Keep**;
- SmartScreen: **More info -> Run anyway**;
- an antivirus (Avast, AVG and others have done it) may hold a new version back for a while or call it suspicious:
  a program packed into one exe the way this one is (compiled with Nuitka, unpacking itself at start) is often taken
  for one at first. Download it only
  from Releases; you can let the antivirus finish its check, or mark the exe as safe in it.

The tool sends nothing over the network unless you press **Send** in *Report a bug / Suggest*; it only asks GitHub
for the newest version's number and, once you sent a report, asks for the answers to it ([SECURITY](https://github.com/Pfadfinder-Adam/RTW-M2TW-Campaign-Editor/blob/main/SECURITY.md)).
It reads and writes only the game or mod folder you load and its own `CampaignEditor` folder beside the exe.

## Without the exe (any OS)

With Python 3.8 or newer: `python campaign_editor.py` from the repository (standard library; Pillow for the
pictures, NumPy for a quicker 3D view, moderngl for the 3D map on the graphics card, zstandard for REX / M2EX packs: `pip install pillow numpy moderngl zstandard`).

**Linux** (Mint, Ubuntu, Debian...): the window needs tkinter and Pillow's Tk part, which the distribution
ships apart from Python. Install them once, then start the tool with `python3`:

```
sudo apt install python3-tk python3-pil python3-pil.imagetk
python3 campaign_editor.py
```

Fedora: `sudo dnf install python3-tkinter python3-pillow-tk`; Arch: `sudo pacman -S tk python-pillow`.
Without tkinter the tool says what to install instead of a Python error.

**Changing the code:** `python -m unittest discover -s tests` and `ruff check` (`pip install ruff`; the rules are
in `ruff.toml`) - CI runs both before it builds the exe.
