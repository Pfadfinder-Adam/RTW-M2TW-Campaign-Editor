"""RTW & M2TW Campaign Editor.

How this tool is built - every change is weighed against these:

- Friendly for everyone: the modder works with factions, towns, armies and the map; the tool finds the files,
  lines and formats. Every value is shown in plain words (a number always says what it means); long explanations
  sit in hover texts ('?').
- A change pulls along everything tied to it, made in the one shared place - never a special case bolted on.
- Nothing is lost: a preview before writing, a backup of every write, a byte-exact Restore, Undo / Redo; what
  would crash the game is refused in plain words; set-up fixes only with a yes.
- Both games, always: Rome (with REX) and Medieval II (with M2EX); the original exes' limits only on vanilla.
- The layout stays: features are added where they belong; what is used rarely folds away behind a button.
- A bug from the game gets a test first; every change is checked in the window and on the real files.
"""
