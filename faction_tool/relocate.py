"""Putting the editor into the game's folder: the place it is meant to lie (beside RomeTW.exe / medieval2.exe), where
it finds the game and every mod by itself and keeps its settings and logs in one place.

Offered once per version to whoever starts the exe somewhere else (the Downloads folder, the desktop, a mod's
folder): the user picks the game's folder - nothing is guessed -, the folder is checked (the game's exe must lie
there), the exe is copied there with what it keeps (its settings and add-ons, when that place has none of its own
yet), a desktop shortcut is made if asked (Windows), and the copy starts from there. The exe started from elsewhere
stays where it is (a running program cannot remove itself); the user may delete it."""

import os
import subprocess
import sys

from . import log, settings
from .newmod import GAME_EXES, is_game

ASKED = "move_offer"                      # settings: the version that asked last, or "never"
SHORTCUT = "RTW-M2TW Campaign Editor.lnk"


def running_exe():
    """The exe this editor runs from, or None when it runs from the source (nothing to move)."""
    return os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else None


def should_offer(version):
    """True when the editor runs as an exe that lies outside every game folder, and this version has not asked yet
    (each new version asks once; 'Don't ask again' stops it for good)."""
    if not running_exe() or log.exe_game():
        return False
    return settings.get(ASKED) not in (version, "never")


def asked(version, never=False):
    settings.put(ASKED, "never" if never else version)


def target_problem(folder, exe=None):
    """None when the editor may go into folder, else why not - in plain words."""
    if not folder or not os.path.isdir(folder):
        return "that folder is not there"
    if not is_game(folder):
        return ("%s holds none of the games' exes (%s) - pick the folder the game starts from, the one with "
                "RomeTW.exe or medieval2.exe in it" % (folder, ", ".join(GAME_EXES)))
    exe = exe or running_exe()
    if exe and os.path.normcase(os.path.abspath(os.path.dirname(exe))) == os.path.normcase(os.path.abspath(folder)):
        return "the editor lies in that folder already"
    probe = os.path.join(folder, ".CampaignEditor_probe")
    try:
        with open(probe, "w") as fh:
            fh.write("x")
        os.remove(probe)
    except OSError:
        return ("the system does not let the editor write into %s (a game under Program Files: start the editor "
                "with 'Run as administrator' once, or move the game's library out of Program Files)" % folder)
    return None


def move_to(folder, exe=None, home=None):
    """The exe copied into folder (an older copy of the editor there replaced), and with it the settings and the
    add-ons folder when folder has none of its own yet - the logs stay where they are. -> the new exe's path.
    Raises ValueError (target_problem) or textio.WriteError (the system refused) in plain words."""
    from .textio import replace_file
    exe = exe or running_exe()
    if not exe:
        raise ValueError("the editor runs from its source files here - there is no exe to move")
    why = target_problem(folder, exe)
    if why:
        raise ValueError(why)
    target = os.path.join(folder, os.path.basename(exe))
    with open(exe, "rb") as fh:
        replace_file(target, fh.read())
    home = home or log.home()
    if home:
        src = os.path.join(home, log.SETTINGS_NAME)
        dst = os.path.join(folder, log.SETTINGS_NAME)
        if os.path.isfile(src) and not os.path.exists(dst):
            with open(src, "rb") as fh:
                replace_file(dst, fh.read())
        addons = os.path.join(home, "CampaignEditor_addons")
        if os.path.isdir(addons) and not os.path.exists(os.path.join(folder, "CampaignEditor_addons")):
            import shutil
            shutil.copytree(addons, os.path.join(folder, "CampaignEditor_addons"))
    log.write("The editor copied into the game's folder: %s (from %s)" % (target, exe))
    return target


def desktop_shortcut(target):
    """A shortcut to target on the desktop (Windows, through PowerShell - no extra program needed). -> None, or why
    it could not be made."""
    if not sys.platform.startswith("win"):
        return "shortcuts are made on Windows only"
    q = lambda s: s.replace("'", "''")
    script = ("$d=[Environment]::GetFolderPath('Desktop'); "
              "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d '%s')); "
              "$s.TargetPath='%s'; $s.WorkingDirectory='%s'; $s.Save()"
              % (q(SHORTCUT), q(target), q(os.path.dirname(target))))
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return str(e)
    return None if r.returncode == 0 else (r.stderr or b"").decode("utf-8", "replace").strip()[:300] or "it failed"


def start(target):
    """Start the editor from its new place."""
    subprocess.Popen([target], cwd=os.path.dirname(target))
