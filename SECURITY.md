# Security Policy

## Supported Versions

Only the latest release gets fixes. Please update to it before reporting a problem:
[Releases](https://github.com/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor/releases).

| Version | Supported          |
| ------- | ------------------ |
| 0.32.x (latest) | :white_check_mark: |
| < 0.32   | :x:                |

## Where to get it

**Only download the editor from this repository's [Releases](https://github.com/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor/releases) page** (or a link the author posted or approved). Never take the exe - or a "fixed" / "patched" copy of it - from another site, a file-sharing link or someone in a chat, and don't pass it on that way: a copy from elsewhere can be changed to harm your PC. Share the link to the Releases page instead.

The same goes for unit packs, add-ons and mods: take them from their authors' own pages, and let the
editor's Preview show what a pack would write before you apply it.

## What the tool does on your PC

RTW & M2TW Campaign Editor only reads and writes the game or mod folder you load, plus its own files
next to the exe (`CampaignEditor_settings.json`, `CampaignEditor_logs` with the log and the saved sessions,
`CampaignEditor_addons` with add-ons you added) and files you pick in a save
dialog. Started outside the game's folder, it offers (with a question) to copy itself into the game folder you pick,
with its settings, and to make a desktop shortcut (Windows) - nothing of that without a yes. The code enforces it: every write to the game goes through one guard that refuses a path outside the mod's
or the game's folder (a `../`, another drive, a link that leads out - whatever a pack, add-on zip or backup names),
before anything is written, and logs it. Every write is shown first and backed up (`CampaignEditor_backups`), and
Restore undoes it (a backup that names files outside is refused too). It needs no internet connection; it sends
something only when you press **Send** in **Report a bug / Suggest** (below), and - once it has sent a report -
asks the same relay for the author's answers to those reports (below), and it asks GitHub for the number of the newest release (below). The Windows exe is built from this repository's source by GitHub Actions
(`.github/workflows/release.yml`); anyone can check the build log of every release.

The exe is not code-signed yet, so browsers and Windows SmartScreen may warn about it
("Keep" / "More info -> Run anyway"). If you prefer, run it from source: `python campaign_editor.py`.

## Reporting a Vulnerability

Please do **not** open a public issue for a security problem (for example a crafted mod file or
pack that makes the tool write outside the mod folder, or a download that does not match the
release build).

- Report it privately: **Security** tab of this repository -> **Report a vulnerability**.
- You will get an answer within **7 days**.
- If it is confirmed, a fixed release follows as soon as possible (usually within a few days) and the
  report is credited in the CHANGELOG, unless you ask not to be named.
- If it is declined, you get the reason.

For ordinary bugs and crashes, press **Report a bug / Suggest** in the tool, or open an issue and attach the logs
(**Tools -> Save logs (zip)**) and a video or screenshot.

## What a report sends

**Report a bug / Suggest** sends only what its window lists, and only after you press Send: the words you wrote, the
contact you gave (optional), the editor's version, Windows' version, the game, the engine and the mod folder's name,
the logs you left ticked and the pictures you picked. Before that the logs lose your Windows user name (also in
folder paths), the computer's name, e-mail addresses, Steam IDs, Windows SIDs, IP addresses, the player's name of
REX's crash report and the words you add; **Show what is sent** shows every line. The report goes over HTTPS to a
relay (`worker/report-relay.js`, a Cloudflare Worker) that files it in the author's **private** reports repo; the
GitHub token lives only in the relay's settings - never in the exe or this repo - and can touch nothing but that
repo. The relay keeps no IP addresses.

**Answers to my reports**: an editor that has sent reports asks the relay, when it starts (at most every 3 hours) and
on **Check now**, for the answers to them - it sends only the reports' numbers (random, known only to the sender), and
gets back only the author's comments on those reports and whether they are closed. **Send the answer** adds your words
(and, if you pick them, screenshots and the logs, names cut out as above) to the same report. Switch the start-up look
off in Tools > Settings > Reports.

**New versions**: when it starts (at most every 6 hours) the editor asks GitHub's public page of its own
repository for the number of the newest release (`api.github.com/repos/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor/releases/latest`).
Nothing is sent with it but the request itself; a newer number shows on the GitHub button. Switch it off in
Tools > Settings > New versions.
