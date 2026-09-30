"""Send a report: the logs (the tool's, the game's system.log.txt, the newest REX crash report), a few words of what
happened and the pictures the user picked go to the editor's author in one click - no account needed.

Anonymous: before anything is packed, every text loses what names the person - the Windows user name (in paths and
as a word), the computer's name, e-mail addresses, Steam IDs, Windows SIDs, IP addresses, the player's name of REX's
crash report (its file name carries it) and whatever words the user asks to hide. The user sees exactly what goes
(Show what is sent) and nothing leaves without the Send button.

The report goes to a small relay (a Cloudflare Worker, worker/report-relay.js in the repo): it keeps the GitHub
token on its side (never in the exe), checks the size and the rate, and files the zip into the author's private
reports repo. The tool only knows the relay's address."""

import base64
import io
import json
import os
import platform
import re
import zipfile

from . import log

# the relay's address (worker/README.md); a settings value 'report_url' overrides it (a test relay)
REPORT_URL = "https://rtw-m2tw-campaign-editor-reports.aldam-dubaev.workers.dev/"
TEXT_CAP = 1536 * 1024          # a log's newest 1.5 MB (the game's system.log.txt can grow to hundreds of MB)
PICTURE_CAP = 3 * 1024 * 1024   # a picked picture
PICTURES = 3
ZIP_CAP = 4 * 1024 * 1024       # the relay refuses more
PICTURE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")

HIDDEN = "<hidden>"
_PATH_USER = re.compile(r"(?i)((?:[A-Z]:)?[\\/]+(?:Users|Documents and Settings|home)[\\/]+)([^\\/\r\n\"'<>|:*?]+)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_STEAM = re.compile(r"\b7656119\d{10}\b")
_SID = re.compile(r"\bS-1-5-21(?:-\d+){3,4}\b")
_IP = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")
_NICK = re.compile(r"^report-(.+)-(\d+)-(\d{2}_\d{2}_\d{2}(?:-\d+)?)\.txt$")
_COMMON = {"user", "admin", "administrator", "owner", "public", "default", "guest", "pc", "desktop", "home"}


def own_words():
    """This computer's names that may stand in a log: the user and computer names Windows (or Linux) gives."""
    out = []
    for k in ("USERNAME", "USER", "LOGNAME", "COMPUTERNAME", "USERDOMAIN"):
        v = (os.environ.get(k) or "").strip()
        if v and v not in out:
            out.append(v)
    try:
        n = platform.node()
        if n and n not in out:
            out.append(n)
    except Exception:
        pass
    return out


def scrub(text, words=()):
    """text without what names the person: paths' user folders, e-mails, Steam IDs, SIDs, IP addresses and each
    of words (as a whole word, any case; words of fewer than 3 letters and everyday ones like 'user' only inside
    paths, or the whole log would be cut up)."""
    text = _PATH_USER.sub(lambda m: m.group(1) + HIDDEN, text)
    text = _EMAIL.sub("<e-mail>", text)
    text = _STEAM.sub("<steam id>", text)
    text = _SID.sub("<sid>", text)
    text = _IP.sub("<ip>", text)
    for w in sorted({w.strip() for w in words if w and w.strip()}, key=len, reverse=True):
        if len(w) < 3 or w.lower() in _COMMON:
            continue
        text = re.sub(r"(?i)(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(w), HIDDEN, text)
    return text


def _read_tail(path, cap=TEXT_CAP):
    """A text file's newest cap bytes as text (a cut start is said so)."""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size > cap:
            fh.seek(size - cap)
        data = fh.read()
    text = data.decode("utf-8", errors="replace")
    if size > cap:
        text = "[... the first %d KB left out - only the newest part is sent ...]\n" % ((size - cap) // 1024) + \
            text.split("\n", 1)[-1]
    return text


def found(game=None, mod_dir=None):
    """[(path, name in the zip, what it is)] of the logs a report can carry: the tool's log (+ .old), the game's
    system.log.txt (game folder, mod folder, their logs/), the newest crash report of <game>/reports (REX) - its
    name without the player's name."""
    out = []
    p = log.path()
    for f, what in ((p, "the editor's log"), ((p or "") + ".old", "the editor's older log")):
        if p and os.path.isfile(f):
            out.append((f, os.path.basename(f), what))
    if game:
        folders = [game, os.path.join(game, "logs")] + ([mod_dir, os.path.join(mod_dir, "logs")] if mod_dir else [])
        for folder in folders:
            f = os.path.join(folder, "system.log.txt")
            if os.path.isfile(f) and all(os.path.normcase(f) != os.path.normcase(q) for q, _, _ in out):
                rel = os.path.relpath(f, game).replace("\\", "/")
                out.append((f, rel if not rel.startswith("..") else "mod_system.log.txt", "the game's log"))
        reports = os.path.join(game, "reports")
        if os.path.isdir(reports):
            txts = [os.path.join(reports, n) for n in os.listdir(reports) if n.lower().endswith(".txt")]
            txts = [f for f in txts if os.path.isfile(f)]
            if txts:
                latest = max(txts, key=os.path.getmtime)
                m = _NICK.match(os.path.basename(latest))
                name = "report-%s-%s.txt" % (m.group(2), m.group(3)) if m else os.path.basename(latest)
                out.append((latest, "reports/" + name, "the newest crash report (REX)"))
    return out


def hidden_words(files, extra=()):
    """The words to hide: this computer's names, the players' names REX crash reports carry, the user's own."""
    words = own_words() + [w for w in extra if w]
    for f, _, _ in files:
        m = _NICK.match(os.path.basename(f))
        if m:
            words.append(m.group(1))
    return words


def contents(files, words):
    """[(name in the zip, scrubbed text)] of the picked logs."""
    out = []
    for f, name, _ in files:
        try:
            out.append((name, scrub(_read_tail(f), words)))
        except OSError as e:
            out.append((name + ".error.txt", "could not read it: %s" % scrub(str(e), words)))
    return out


def about(mod=None, version=""):
    """What the report says of the set-up (no names): the editor's version, Windows, the game, the engine, the
    mod's folder name."""
    info = {"editor": version, "system": platform.platform(terse=True)}
    if mod is not None:
        try:
            from .limits import engine_of, game_kind
            info["game"] = "Medieval II" if game_kind(mod) == "medieval2" else "Rome"
            info["engine"] = engine_of(mod) or "none"
            info["mod"] = os.path.basename(os.path.dirname(os.path.abspath(mod.data)))
        except Exception:
            pass
    return info


def build_zip(texts, message="", contact="", info=None, pictures=(), words=()):
    """The report's zip as bytes: report.txt (what happened, the contact, the set-up), the scrubbed logs, the
    pictures (as they are - the user picked them)."""
    info = dict(info or {})
    head = ["What happened:", scrub(message.strip(), words) or "(not said)", "",
            "Contact (given by the sender): %s" % (contact.strip() or "none"), ""]
    head += ["%s: %s" % (k, scrub(str(v), words)) for k, v in info.items()]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("report.txt", "\n".join(head) + "\n")
        for name, text in texts:
            z.writestr(name, text)
        for p in list(pictures)[:PICTURES]:
            z.write(p, "pictures/" + scrub(os.path.basename(p), words))
    return buf.getvalue()


def picture_problem(path):
    """Why a picked picture cannot go, or None."""
    if not path.lower().endswith(PICTURE_EXT):
        return "%s is not a picture (png, jpg, bmp, gif, webp)" % os.path.basename(path)
    if os.path.getsize(path) > PICTURE_CAP:
        return "%s is over %d MB" % (os.path.basename(path), PICTURE_CAP // (1024 * 1024))
    return None


def url():
    from . import settings
    return (settings.get("report_url") or REPORT_URL).strip()


def send(data, message="", contact="", info=None, timeout=60):
    """The zip to the relay; the report's number it answers (like R-20260930-7F3A). Raises RuntimeError in plain
    words when it did not go."""
    import urllib.error
    import urllib.request
    where = url()
    if not where:
        raise RuntimeError("the report service is not set up in this version yet - save the zip instead and send "
                           "it on Discord or GitHub")
    if len(data) > ZIP_CAP:
        raise RuntimeError("the report is %d KB, over the %d KB the service takes - leave a picture or a log out"
                           % (len(data) // 1024, ZIP_CAP // 1024))
    body = json.dumps({"message": message[:4000], "contact": contact[:200], "info": info or {},
                       "zip": base64.b64encode(data).decode("ascii")}).encode("utf-8")
    req = urllib.request.Request(where, data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "RTW-M2TW-Campaign-Editor/%s" % (info or {}).get(
            "editor", "")})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            answer = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            why = json.loads(e.read().decode("utf-8")).get("error") or e.reason
        except Exception:
            why = e.reason
        raise RuntimeError("the report service said no (%s): %s" % (e.code, why))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError("could not reach the report service (%s) - is the internet on?" % getattr(e, "reason", e))
    if not answer.get("id"):
        raise RuntimeError("the report service gave no report number: %s" % answer.get("error", answer))
    return answer["id"]
