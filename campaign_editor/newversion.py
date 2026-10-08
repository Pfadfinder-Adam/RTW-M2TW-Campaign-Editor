"""Is a newer release of the editor out? One GET of GitHub's public 'latest release' page of the editor's repository
(nothing is sent, nothing else is asked), in a thread, on every start and again every CHECK_EVERY seconds while the
editor stays open (it looked at most once in 6 hours, on start only: a release made after the morning's start was not
seen that day). A newer one turns the GitHub button green with its number ('GitHub (new 0.30)') and the button opens its
release page. The last answer is
kept in the settings, so the mark shows at once on the next start; it goes away by itself once that version (or a
later one) runs. Settings > 'Look for a new version' turns it off. Only releases count - the builds of every push
(GitHub Actions) do not."""
import json
import re
import threading
import time
import urllib.request

from . import log, settings

REPO = "MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor"
PAGE = "https://github.com/" + REPO
API = "https://api.github.com/repos/%s/releases/latest" % REPO
CHECK_EVERY = 6 * 3600          # seconds between the looks while the editor stays open


def _number(text):
    """The version number in a text: the first with a dot ('M2TW' in a name is no version), else a lone number."""
    m = re.search(r"\d+(?:\.\d+)+", text or "") or re.search(r"\d+", text or "")
    return m.group(0) if m else None


def parse(version):
    """(0, 30, 0) from 'v0.30.0', '0.30', 'RTW & M2TW Campaign Editor 0.30'; None when it holds no number."""
    n = _number(version)
    return tuple(int(p) for p in n.split(".")) if n else None


def newer(tag, current):
    """Whether release tag is a later version than current ('0.30' after '0.29.2'; '0.29.2' = '0.29.2.0')."""
    a, b = parse(tag), parse(current)
    if a is None or b is None:
        return False
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def shown(tag):
    """The number as the button shows it: 'v0.30.0' -> '0.30', 'v0.29.2' -> '0.29.2'."""
    n = _number(tag)
    return re.sub(r"^(\d+\.\d+)\.0$", r"\1", n) if n else (tag or "")


def latest(version="", timeout=15):
    """(tag, release page) of the newest release on GitHub; raises on no connection or an odd answer."""
    from .report import ssl_context
    req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "RTW-M2TW-Campaign-Editor/%s" % version})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
        data = json.loads(r.read().decode("utf-8"))
    tag = data.get("tag_name") or ""
    if not parse(tag) or data.get("draft") or data.get("prerelease"):
        raise ValueError("no release number in GitHub's answer")
    return tag, data.get("html_url") or PAGE + "/releases"


def known(current):
    """(number shown, release page) of a newer release seen by an earlier check, or None."""
    rel = settings.get("release_latest") or {}
    tag = rel.get("tag") if isinstance(rel, dict) else None
    if tag and newer(tag, current):
        return shown(tag), rel.get("url") or PAGE + "/releases"
    return None


def check(app, current, done):
    """Unless turned off: ask GitHub in a thread; done(number, page) runs in the window's thread when a newer release
    is out. Offline or an error: one line in the log, nothing shown."""
    if settings.get("release_check", True) is False:
        return
    result = {}

    def work():
        try:
            result["r"] = latest(current)
        except Exception as e:
            result["e"] = str(e)
    th = threading.Thread(target=work, daemon=True)
    th.start()

    def wait():
        if th.is_alive():
            app.after(500, wait)
            return
        if "e" in result:
            log.write("New version not looked for: %s" % result["e"])
            return
        tag, url = result["r"]
        settings.put("release_checked_at", time.time())
        settings.put("release_latest", {"tag": tag, "url": url})
        if newer(tag, current):
            log.write("A newer release is out: %s (%s)" % (tag, url))
            done(shown(tag), url)
    wait()
