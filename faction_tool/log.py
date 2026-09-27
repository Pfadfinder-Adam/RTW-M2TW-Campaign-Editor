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
