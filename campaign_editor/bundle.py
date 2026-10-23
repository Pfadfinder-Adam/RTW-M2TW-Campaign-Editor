"""Where the editor runs from: the source files, or the one-file exe - built by Nuitka (the editor compiled to machine
code) or, before that, by PyInstaller. One place answers for both builds: is it an exe, which exe file it
is (to copy it into the game's folder, to keep the settings beside it), and the folder the exe unpacks its own files to
(the game manifests, the pictures, the add-ons, CREDITS.md, modules.txt) - None from the source."""

import os
import sys

# Nuitka puts __compiled__ into every module it compiled (sys.frozen is PyInstaller's); never there in the source
NUITKA = globals().get("__compiled__")


def frozen():
    """True when the editor runs as the built exe."""
    return bool(getattr(sys, "frozen", False) or NUITKA)


def exe():
    """The exe file the user started, or None from the source. Nuitka's one-file exe runs its Python from the folder
    it unpacks to (sys.executable lies there, gone when it closes); the file the user started is its argv[0]."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    if not NUITKA:
        return None
    argv0 = getattr(NUITKA, "original_argv0", None) or sys.argv[0]
    path = os.path.join(NUITKA.containing_dir, os.path.basename(argv0))
    if sys.platform.startswith("win") and not path.lower().endswith(".exe") and os.path.isfile(path + ".exe"):
        path += ".exe"                       # started as 'RTW-M2TW-Campaign-Editor' from a command line
    return os.path.abspath(path)


def files_dir():
    """The folder the exe unpacked its own files to, or None from the source."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return base
    if NUITKA:                               # the package lies right in that folder: <it>/campaign_editor/bundle.py
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return None
