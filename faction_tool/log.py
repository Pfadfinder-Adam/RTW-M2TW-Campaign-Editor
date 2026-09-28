"""The tool's own log, faction_tool.log: what was loaded, previewed and written,
every error with its traceback. Next to the exe (or rtw_faction_tool.py), else in
the user's profile. Kept small: over 1 MB it moves to faction_tool.log.old."""

import datetime
import os
import sys
import traceback

LIMIT = 1 << 20
_path = None


def _candidates():
    if getattr(sys, "frozen", False):
        yield os.path.dirname(os.path.abspath(sys.executable))
    else:
        yield os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    yield os.path.join(base, "RTW Faction Tool")


def path():
    """The log file's path (the first folder we may write to)."""
    global _path
    if _path is None:
        for d in _candidates():
            try:
                os.makedirs(d, exist_ok=True)
                p = os.path.join(d, "faction_tool.log")
                with open(p, "a", encoding="utf-8"):
                    pass
                _path = p
                break
            except OSError:
                continue
    return _path


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
import re as _re

_NICK = _re.compile(r"^report-(.+)-(\d+)-(\d{2}_\d{2}_\d{2}(?:-\d+)?)\.txt$")


def game_logs(game, mod_dir=None):
    """[(file, name in the zip)] of the game's logs: system.log.txt in the game's
    working folder (the start script cd's there) or a logs folder, and the newest
    crash report in <game>/reports (REX). The report's name loses the player's
    nick, as HLR's Collect_logs.bat does."""
    out = []
    for folder in [game, os.path.join(game, "logs")] + ([mod_dir, os.path.join(mod_dir, "logs")] if mod_dir else []):
        p = os.path.join(folder, "system.log.txt")
        if os.path.isfile(p) and all(os.path.normcase(p) != os.path.normcase(q) for q, _ in out):
            rel = os.path.relpath(p, game).replace("\\", "/")
            out.append((p, rel if not rel.startswith("..") else "mod_" + os.path.basename(p)))
    reports = os.path.join(game, "reports")
    if os.path.isdir(reports):
        txts = [os.path.join(reports, n) for n in os.listdir(reports) if n.lower().endswith(".txt")]
        txts = [p for p in txts if os.path.isfile(p)]
        if txts:
            latest = max(txts, key=os.path.getmtime)
            name = os.path.basename(latest)
            m = _NICK.match(name)
            out.append((latest, "reports/" + ("report-%s-%s.txt" % (m.group(2), m.group(3)) if m else name)))
    return out


def pack(zip_path, game, mod_dir=None):
    """Write zip_path with faction_tool.log (+ .old) and the game's logs.
    Returns [names put in]."""
    import zipfile
    names = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        p = path()
        for f in ([p, p + ".old"] if p else []):
            if os.path.isfile(f):
                z.write(f, os.path.basename(f))
                names.append(os.path.basename(f))
        for f, name in game_logs(game, mod_dir) if game else []:
            z.write(f, name)
            names.append(name)
    return names
