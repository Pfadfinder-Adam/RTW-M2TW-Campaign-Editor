"""The tool's own log and its folder. The exe is meant to lie in the game's folder (beside RomeTW.exe /
medieval2.exe - it then finds the game and every mod by itself); beside it the tool keeps two things of its own:

    CampaignEditor_logs/           its log (CampaignEditor.log), the logs zips (Save logs) and sessions/: on every
                                   close the session's part of the log and the game's newest system.log.txt
    CampaignEditor_settings.json   what it keeps between starts

When run from the source the same two lie beside campaign_editor.py; where the exe's folder cannot be written
(Program Files) in %APPDATA%/RTW-M2TW-Campaign-Editor. Older versions' files (RTW-M2TW-Campaign-Editor-files/,
faction_tool.log, faction_tool_settings.json) are moved in once, nothing lost. Kept small: over 1 MB the log
moves to CampaignEditor.log.old."""

import datetime
import os
import sys
import traceback

LIMIT = 1 << 20
_path = None
_home = None
SHORT = "CampaignEditor"
LOGS = SHORT + "_logs"                           # beside the exe: the log, the logs zips, the sessions
LOG_NAME = SHORT + ".log"
SETTINGS_NAME = SHORT + "_settings.json"
SESSIONS = "sessions"
GAME_LOG = "game_system.log.txt"                 # the game's own system.log.txt as a session keeps it
KEEP_SESSIONS = 30
APPDATA_NAME = "RTW-M2TW-Campaign-Editor"

FOLDER = "RTW-M2TW-Campaign-Editor-files"      # 0.9.2 - 0.28: the tool's folder beside the exe
OLD_FOLDERS = ("RTW-Campaign-Editor-files",)     # its name before 0.9.2
OLD_LOG = "faction_tool.log"
OLD_SETTINGS = "faction_tool_settings.json"


def exe_dir():
    """The folder of the exe (from the source: of campaign_editor.py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _candidates():
    yield exe_dir()
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    yield os.path.join(base, APPDATA_NAME)
    yield os.path.join(base, "RTW Faction Tool")                    # where older versions fell back to


def _move(src, dst):
    try:
        if os.path.isfile(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.replace(src, dst)
    except OSError:
        pass


def _move_old(home):
    """Older versions' files into the new places once: the folder RTW-M2TW-Campaign-Editor-files (its settings,
    its logs/ with faction_tool.log and the zips), faction_tool.log / faction_tool_settings.json beside the exe, and
    the settings an older version kept in the user's APPDATA ('RTW Faction Tool', 'RTW-M2TW-Campaign-Editor') when
    the exe's folder was not writable - copied, so nothing set there is lost."""
    logs = os.path.join(home, LOGS)
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    for d in (os.path.join(base, "RTW Faction Tool"), os.path.join(base, APPDATA_NAME)):
        if os.path.normcase(os.path.abspath(d)) == os.path.normcase(os.path.abspath(home)):
            continue
        for old in (SETTINGS_NAME, OLD_SETTINGS, os.path.join(FOLDER, OLD_SETTINGS)):
            src, dst = os.path.join(d, old), os.path.join(home, SETTINGS_NAME)
            if os.path.isfile(src) and not os.path.exists(dst):
                try:
                    import shutil
                    shutil.copy2(src, dst)
                except OSError:
                    pass
    for folder in (FOLDER,) + OLD_FOLDERS + ("",):
        d = os.path.join(home, folder) if folder else home
        if folder and not os.path.isdir(d):
            continue
        _move(os.path.join(d, OLD_SETTINGS), os.path.join(home, SETTINGS_NAME))
        for sub in ("logs", ""):
            ld = os.path.join(d, sub) if sub else d
            for old, new in ((OLD_LOG, LOG_NAME), (OLD_LOG + ".old", LOG_NAME + ".old")):
                _move(os.path.join(ld, old), os.path.join(logs, new))
            if sub and os.path.isdir(ld) and folder:
                try:
                    for n in os.listdir(ld):                    # the logs zips made by Save logs
                        _move(os.path.join(ld, n), os.path.join(logs, n))
                except OSError:
                    pass
        if folder:
            for sub in ("logs", ""):                            # the old folder goes once it is empty
                try:
                    os.rmdir(os.path.join(d, sub) if sub else d)
                except OSError:
                    pass


def home():
    """The tool's own place (the first one we may write to): the settings and the logs folder lie there."""
    global _home
    if _home is None:
        for d in _candidates():
            try:
                os.makedirs(os.path.join(d, LOGS), exist_ok=True)
                _move_old(d)                             # before the probe below makes an empty log
                probe = os.path.join(d, LOGS, LOG_NAME)
                with open(probe, "a", encoding="utf-8"):
                    pass
                _home = d
                break
            except OSError:
                continue
    return _home


def logs_dir():
    """Where the log, the logs zips and the sessions go: <the tool's place>/CampaignEditor_logs."""
    h = home()
    return os.path.join(h, LOGS) if h else None


def path():
    """The log file's path."""
    global _path
    if _path is None and home():
        _path = os.path.join(_home, LOGS, LOG_NAME)
    return _path


def exe_game():
    """The game folder the exe lies in (beside RomeTW.exe / medieval2.exe / REX.exe / M2EX.exe), or None."""
    from .newmod import is_game
    d = exe_dir()
    return d if is_game(d) else None


_session_start = None


def session_start():
    """Mark where this session's part of the log begins (called at start)."""
    global _session_start
    p = path()
    try:
        _session_start = (os.path.getsize(p) if p and os.path.exists(p) else 0,
                          datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    except OSError:
        _session_start = (0, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))


def save_session(game=None, mod_dir=None):
    """On close: CampaignEditor_logs/sessions/<start time>/ gets this session's part of the log and copies of the
    game's newest system.log.txt (the mod's own first) - no button needed; the oldest sessions beyond
    KEEP_SESSIONS go. Returns the folder, or None. Never raises."""
    try:
        import shutil
        from . import report
        logs = logs_dir()
        if not logs or _session_start is None:
            return None
        offset, stamp = _session_start
        out = os.path.join(logs, SESSIONS, stamp)
        os.makedirs(out, exist_ok=True)
        p = path()
        if p and os.path.exists(p):
            with open(p, "rb") as fh:
                size = os.path.getsize(p)
                fh.seek(offset if offset <= size else 0)            # the log moved to .old meanwhile: all of it
                with open(os.path.join(out, LOG_NAME), "wb") as o:
                    o.write(fh.read())
        for i, f in enumerate(report.game_logs(game, mod_dir, keep=2) if game else []):
            # named as the GAME's: a tester read its errors in the session folder as the editor's own
            shutil.copyfile(f, os.path.join(out, GAME_LOG if i == 0 else "game_system.log.%d.txt" % i))
        root = os.path.join(logs, SESSIONS)
        olds = sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n)))
        for n in olds[:-KEEP_SESSIONS]:
            shutil.rmtree(os.path.join(root, n), ignore_errors=True)
        return out
    except Exception:
        return None


def write(text):
    """Append a time-stamped entry; never raises (a log must not break the tool)."""
    try:
        p = path()
        if not p:
            return
        if os.path.exists(p) and os.path.getsize(p) > LIMIT:
            os.replace(p, p + ".old")
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (stamp, str(text).rstrip().replace("\n", "\n    ")))
    except Exception:
        pass


def error(text, exc=True):
    """An error, with the traceback being handled if there is one."""
    tb = traceback.format_exc() if exc else ""
    write("ERROR " + str(text) + ("\n" + tb if tb and not tb.startswith("NoneType: None") else ""))


def tail(limit=200000):
    """The end of the log for showing in the window."""
    p = path()
    if not p or not os.path.exists(p):
        return ""
    with open(p, encoding="utf-8", errors="replace") as fh:
        data = fh.read()
    return data[-limit:]


# ---------------------------------------------------------------------------
# The game's logs, packed with ours for a report
# ---------------------------------------------------------------------------
def pack(zip_path, game, mod_dir=None, extra_words=()):
    """Write zip_path with faction_tool.log (+ .old) and the game's logs, the person's names cut out as in a sent
    report (report.scrub). Returns [names put in]."""
    import zipfile
    from . import report
    files = report.found(game, mod_dir)
    texts = report.contents(files, report.hidden_words(files, extra_words))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in texts:
            z.writestr(name, text)
    return [name for name, _ in texts]
