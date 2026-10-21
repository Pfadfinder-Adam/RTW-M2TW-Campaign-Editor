"""The game stopped - offered as a report (the user, 2026-10-21: people wait instead of pressing Report a bug; 'and
if they close the editor?'). After Start the game the editor looks at the game's files now and then; at its own
start it looks once. A crash of the game (a crash report in <game>/reports, or a stop the crash doctor reads in
system.log.txt) the editor has not asked about yet is offered ONCE: 'The game stopped: <why>. Send a report?'.
Nothing is sent without the press - the report window shows everything first. Settings: crash_offer (on), crash_seen
(the crash asked about last). No program is left running when the editor closes."""

import os
import time

from . import report, settings


def _key(f):
    """Which file, as it is now: a new run writes the file again (another time or size)."""
    st = os.stat(f)
    return "%s|%d|%d" % (os.path.normcase(f), st.st_mtime_ns, st.st_size)


def last_crash(game, mod_dir=None):
    """The game's last crash: {'key', 'when', 'why'} or None - the newest crash report of the last run (report.found
    keeps only that one), else the crash doctor's 'The game stopped: ...' over the newest system.log.txt."""
    if not game or not os.path.isdir(game):
        return None
    files = report.found(game, mod_dir)
    dumps = [f for f, n, _ in files if n.startswith("reports/")]
    logs = [f for f, n, _ in files if n.endswith("system.log.txt") and not n.startswith("sessions/")]
    head = report.doctor([(f, os.path.basename(f), "") for f in logs]) if logs else ""
    stopped = head.startswith("The game stopped")
    if dumps:
        f = dumps[0]
        why = head[len("The game stopped: "):] if stopped else "a crash report was written (%s)" % os.path.basename(f)
        return {"key": _key(f), "when": os.path.getmtime(f), "why": why}
    if stopped:
        f = max(logs, key=os.path.getmtime)
        return {"key": _key(f), "when": os.path.getmtime(f), "why": head[len("The game stopped: "):]}
    return None


def unseen(game, mod_dir=None, since=0.0):
    """last_crash when it is one the editor has not asked about yet (and newer than since), else None; never when
    the modder switched the offer off."""
    if not settings.get("crash_offer", True):
        return None
    try:
        c = last_crash(game, mod_dir)
    except Exception:
        return None
    if not c or c["key"] == settings.get("crash_seen") or c["when"] < since:
        return None
    return c


def mark_seen(c):
    settings.put("crash_seen", c["key"])


def question(c):
    """The words of the offer."""
    return ("The game stopped: %s\n\nSend a report? The game's log and its crash report go with it - you see "
            "everything before it is sent. (Settings: this question can be switched off.)" % c["why"])


QUIET = 20          # seconds the game's log stays unchanged before it is read (the game closed or waits in a menu)
WATCH_FOR = 8 * 3600


class Watch:
    """After Start the game: step() every few seconds says a crash to offer (once), or None. Reads the game's log
    only when it has changed and then stayed still QUIET seconds; a new crash report is seen at once."""

    def __init__(self, game, mod_dir=None, now=None):
        self.game, self.mod_dir = game, mod_dir
        self.start = time.time() if now is None else now
        self.read_at = None                             # the log's time when it was last read
        self.done = False

    def _log_time(self):
        logs = report.game_logs(self.game, self.mod_dir)
        return max((os.path.getmtime(f) for f in logs), default=0.0)

    def _new_dump(self):
        d = os.path.join(self.game, "reports")
        try:
            return any(n.lower().endswith(".txt") and os.path.getmtime(os.path.join(d, n)) > self.start
                       for n in os.listdir(d))
        except OSError:
            return False

    def step(self, now=None):
        now = time.time() if now is None else now
        if self.done or now - self.start > WATCH_FOR:
            self.done = True
            return None
        t = self._log_time()
        quiet = t > self.start and now - t >= QUIET and t != self.read_at
        if not (self._new_dump() or quiet):
            return None
        self.read_at = t
        c = unseen(self.game, self.mod_dir, since=self.start)
        if c:
            self.done = True
        return c


__all__ = ["last_crash", "unseen", "mark_seen", "question", "Watch"]
