# Security Policy

## Supported Versions

Only the latest release gets fixes. Please update to it before reporting a problem:
[Releases](https://github.com/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor/releases).

| Version | Supported          |
| ------- | ------------------ |
| 0.19.x (latest) | :white_check_mark: |
| < 0.19   | :x:                |

## Where to get it

**Only download the editor from this repository's [Releases](https://github.com/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor/releases) page** (or a link the author posted or approved). Never take the exe - or a "fixed" / "patched" copy of it - from another site, a file-sharing link or someone in a chat, and don't pass it on that way: a copy from elsewhere can be changed to harm your PC. Share the link to the Releases page instead.

The same goes for unit packs, add-ons and mods: take them from their authors' own pages, and let the
editor's Preview show what a pack would write before you apply it.

## What the tool does on your PC

RTW & M2TW Campaign Editor only reads and writes the game or mod folder you load, plus its own folder
`RTW-M2TW-Campaign-Editor-files` next to the exe (log and settings). Every write is shown first and
backed up (`faction_tool_backups`), and Restore undoes it. It needs no internet connection and sends
nothing anywhere. The Windows exe is built from this repository's source by GitHub Actions
(`.github/workflows/release.yml`); anyone can check the build log of every release.

The exe is not code-signed yet, so browsers and Windows SmartScreen may warn about it
("Keep" / "More info -> Run anyway"). If you prefer, run it from source: `python rtw_faction_tool.py`.

## Reporting a Vulnerability

Please do **not** open a public issue for a security problem (for example a crafted mod file or
pack that makes the tool write outside the mod folder, or a download that does not match the
release build).

- Report it privately: **Security** tab of this repository -> **Report a vulnerability**.
- You will get an answer within **7 days**.
- If it is confirmed, a fixed release follows as soon as possible (usually within a few days) and the
  report is credited in the CHANGELOG, unless you ask not to be named.
- If it is declined, you get the reason.

For ordinary bugs and crashes, open an issue and attach the logs (**Tools -> Save logs (zip)**)
and a video or screenshot.
