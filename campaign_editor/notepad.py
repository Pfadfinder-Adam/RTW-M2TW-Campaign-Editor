"""A file opened in the modder's own text editor at a line (the user, 2026-10-21: 'and Notepad++ too'; the design of
2026-10-06): Notepad++ where it is installed (it opens at the line: -n<line>), else the program the modder picked once
(settings 'text_editor'), else Windows' Notepad (no line). Nothing is changed by opening; what the modder saves there
the editor reads at its next Load (the editors see a file changed on disk and say so)."""

import os
import subprocess
import sys

from . import settings

NPP = ("Notepad++\\notepad++.exe",)
NPP_LINK = "https://notepad-plus-plus.org/"


def notepad_pp():
    """Notepad++'s exe, or None: the usual places under Program Files, then the registry's App Paths."""
    roots = [os.environ.get(k) for k in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "LOCALAPPDATA")]
    for r in filter(None, roots):
        for rel in NPP + ("Programs\\Notepad++\\notepad++.exe",):
            p = os.path.join(r, rel)
            if os.path.isfile(p):
                return p
    if sys.platform == "win32":
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\App Paths\notepad++.exe") as k:
                        p = winreg.QueryValue(k, None)
                        if p and os.path.isfile(p):
                            return p
                except OSError:
                    continue
        except ImportError:
            pass
    return None


def program():
    """(exe, kind) of the editor to open files in: the one picked in Settings, Notepad++, or Notepad."""
    own = settings.get("text_editor")
    if own and os.path.isfile(own):
        return own, "notepad++" if os.path.basename(own).lower() == "notepad++.exe" else "own"
    npp = notepad_pp()
    if npp:
        return npp, "notepad++"
    return "notepad.exe", "notepad"


def command(path, line=None):
    """The command line that opens path at line (1-based) in the program()."""
    exe, kind = program()
    if kind == "notepad++" and line:
        return [exe, "-n%d" % int(line), path]
    if kind == "own" and line and "code" in os.path.basename(exe).lower():
        return [exe, "-g", "%s:%d" % (path, int(line))]            # VS Code: --goto file:line
    return [exe, path]


def open_at(path, line=None):
    """Open path at line; OSError when the program cannot be started (said by the caller)."""
    if sys.platform != "win32":
        raise OSError("opens on Windows - the file: %s%s" % (path, " (line %d)" % line if line else ""))
    subprocess.Popen(command(path, line))


__all__ = ["notepad_pp", "program", "command", "open_at", "NPP_LINK"]
