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


HEAD_CAP = 512 * 1024           # a long log's start: the game reading the mod's files (where load errors are)
MIDDLE_CAP = 256 * 1024         # ... its errors and warnings from the part left out
IMPORTANT = re.compile(rb"\[(?:error|fatal|warning|critical)\]|\bERROR\b|\bWARNING\b|ASSERT|[Ee]xception|crash")


def _read_tail(path, cap=TEXT_CAP):
    """A log as text, at most about cap bytes: all of it when small; else its start (HEAD_CAP - the game reading the
    mod's files at the start of the campaign is where a mod's mistakes show), the error and warning lines of the
    middle left out (MIDDLE_CAP, each kind once with how many times) and its newest part. What was cut is said."""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size <= cap:
            return fh.read().decode("utf-8", errors="replace")
        head_cap, middle_cap = min(HEAD_CAP, cap // 3), min(MIDDLE_CAP, cap // 6)
        head = fh.read(head_cap)
        head = head[:head.rfind(b"\n") + 1] or head
        tail_size = max(cap - head_cap - middle_cap, cap // 4)
        tail_at = max(len(head), size - tail_size)
        fh.seek(len(head))
        seen, order, kept = {}, [], 0
        left = tail_at - len(head)
        pending = None
        while left > 0 or pending is not None:
            if pending is not None:
                line, pending = pending, None
            else:
                line = fh.readline(min(left, 1 << 20))
                if not line:
                    break
                left -= len(line)
            if IMPORTANT.search(line):
                key = re.sub(rb"^[\d:.]+\s*", b"", line.strip())[:300]   # the same message at another time once
                # the game writes what went wrong on the next line ("Script Error in ... line 702" / "Population of
                # 2600 is too high for a village") - kept with it, else the middle's errors said nothing
                if left > 0:
                    nxt = fh.readline(min(left, 1 << 20))
                    left -= len(nxt)
                    if nxt.strip() and not re.match(rb"^\d\d:\d\d:\d\d", nxt) and not nxt.lstrip().startswith(b"at "):
                        key = key + b"  |  " + nxt.strip()[:300]
                    elif nxt:
                        pending = nxt
                if key in seen:
                    seen[key] += 1
                elif kept < middle_cap:
                    seen[key] = 1
                    order.append(key)
                    kept += len(key) + 1
        fh.seek(tail_at)
        tail = fh.read()
    tail = tail.split(b"\n", 1)[-1] if tail_at > len(head) else tail
    middle = b"\n".join(k + (b"  (x%d)" % seen[k] if seen[k] > 1 else b"") for k in order)
    cut = (tail_at - len(head)) // 1024
    text = head.decode("utf-8", errors="replace")
    text += "\n[... %d KB in the middle left out - its %d error / warning line(s) kept below, each once ...]\n" % (
        cut, len(order))
    text += middle.decode("utf-8", errors="replace")
    text += "\n[... the newest part ...]\n" + tail.decode("utf-8", errors="replace")
    return text


def game_logs(game, mod_dir=None, keep=3):
    """The game's system.log.txt files worth sending, newest first: the mod's own (its folder and its logs/), the
    game folder's and its logs/, and those of every other mod in the game folder (Rome: <game>/<mod>/, Medieval II:
    <game>/mods/<mod>/; also bi/ and alexander/) - the game writes the log where the mod was started from, so it is
    looked for everywhere one level down; at most `keep`, the mod's own always first."""
    seen, mine, others = set(), [], []

    def add(folder, own=False):
        for f in (os.path.join(folder, "system.log.txt"), os.path.join(folder, "logs", "system.log.txt")):
            k = os.path.normcase(os.path.abspath(f))
            if k in seen or not os.path.isfile(f):
                continue
            seen.add(k)
            (mine if own else others).append(f)
    if mod_dir:
        add(mod_dir, own=True)
    add(game)
    for parent in (game, os.path.join(game, "mods")):
        try:
            names = sorted(os.listdir(parent))
        except OSError:
            continue
        for n in names:
            d = os.path.join(parent, n)
            if os.path.isdir(d) and n.lower() not in ("data", "faction_tool_backups", "campaigneditor_backups"):
                add(d)
    newest = lambda fs: sorted(fs, key=lambda f: -os.path.getmtime(f))
    return (newest(mine) + newest(others))[:keep]


def _age(path):
    """'5 minutes ago', '3 hours ago', '2 days ago'."""
    import time
    s = max(0, time.time() - os.path.getmtime(path))
    for size, word in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if s >= size:
            n = int(s // size)
            return "%d %s%s ago" % (n, word, "s" if n != 1 else "")
    return "just now"


LOG_HOWTO = ("The game writes system.log.txt only while its log is on. REX and M2EX keep it on. The original games "
             "need two lines in the preference file they start with (Rome: RomeTW.preference.cfg - or the mod's "
             ".cfg; Medieval II: medieval2.preference.cfg - or the mod's .cfg), under [log]:\n"
             "    [log]\n    to = logs/system.log.txt\n    level = * error\n"
             "Start the game again, do what went wrong, then send the report: the log is in the game's (or the "
             "mod's) logs folder.")


def found(game=None, mod_dir=None):
    """[(path, name in the zip, what it is)] of the logs a report can carry: the tool's log (+ .old), the game's
    system.log.txt (game folder, mod folder, their logs/), the newest crash report of <game>/reports (REX) - its
    name without the player's name."""
    out = []
    if not game:
        try:
            from . import settings
            game = log.exe_game() or settings.get("game") or None   # no mod loaded: the exe's game, the one used last
        except Exception:
            game = None
    p = log.path()
    for f, what in ((p, "the editor's log"), ((p or "") + ".old", "the editor's older log")):
        if p and os.path.isfile(f):
            out.append((f, os.path.basename(f), what))
    if game:
        for f in game_logs(game, mod_dir):
            rel = os.path.relpath(f, game).replace("\\", "/")
            out.append((f, rel if not rel.startswith("..") else "mod_system.log.txt",
                        "the game's log, written %s" % _age(f)))
        reports = os.path.join(game, "reports")
        if os.path.isdir(reports):
            txts = [os.path.join(reports, n) for n in os.listdir(reports) if n.lower().endswith(".txt")]
            txts = [f for f in txts if os.path.isfile(f)]
            if txts:
                latest = max(txts, key=os.path.getmtime)
                m = _NICK.match(os.path.basename(latest))
                name = "report-%s-%s.txt" % (m.group(2), m.group(3)) if m else os.path.basename(latest)
                out.append((latest, "reports/" + name, "the newest crash report (REX)"))
    if not any(n.endswith("system.log.txt") for _, n, _ in out):
        # the game's log not found where it lies now: the copy the last closed session kept
        sess = os.path.join(log.logs_dir() or "", log.SESSIONS)
        try:
            for n in sorted(os.listdir(sess), reverse=True):
                f = next((p for p in (os.path.join(sess, n, log.GAME_LOG), os.path.join(sess, n, "system.log.txt"))
                          if os.path.isfile(p)), None)     # (sessions before 0.30 kept it as system.log.txt)
                if f:
                    out.append((f, "sessions/%s/system.log.txt" % n, "the game's log kept when the editor closed "
                                "(%s)" % _age(f)))
                    break
        except OSError:
            pass
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


def ssl_context():
    """The certificates to trust when sending: Windows' own store AND the certifi bundle inside the exe - an old
    Windows or an antivirus that checks web traffic may lack the root the report service's certificate comes from
    ('SSL: CERTIFICATE_VERIFY_FAILED' - a player's report did not go)."""
    import ssl
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:
        pass
    return ctx


def _post(path, payload, version="", timeout=60, what="the report service"):
    """One JSON POST to the relay (path '' = a new report, 'answers', 'reply'); its JSON answer. RuntimeError in
    plain words when it did not go."""
    import urllib.error
    import urllib.request
    where = url()
    if not where:
        raise RuntimeError("the report service is not set up in this version yet - save the zip instead and send "
                           "it on Discord or GitHub")
    if path:
        where = where.rstrip("/") + "/" + path
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(where, data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "RTW-M2TW-Campaign-Editor/%s" % version})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            why = json.loads(e.read().decode("utf-8")).get("error") or e.reason
        except Exception:
            why = e.reason
        raise RuntimeError("%s said no (%s): %s" % (what, e.code, why))
    except (urllib.error.URLError, OSError, ValueError) as e:
        why = getattr(e, "reason", e)
        if "SSL" in str(why) or "CERTIFICATE" in str(why).upper():
            raise RuntimeError("the connection to the report service was refused by a security check on this PC "
                               "(%s) - often an antivirus that checks web traffic. Save the zip instead and send "
                               "it on Discord or GitHub." % why)
        raise RuntimeError("could not reach the report service (%s) - is the internet on?" % why)


def send(data, message="", contact="", info=None, timeout=60, full=False):
    """The zip to the relay; the report's number it answers (like R-20260930-7F3A), with full=True (number, issue)
    - the issue lets the editor ask for answers later. Raises RuntimeError in plain words when it did not go."""
    if len(data) > ZIP_CAP:
        raise RuntimeError("the report is %d KB, over the %d KB the service takes - leave a picture or a log out"
                           % (len(data) // 1024, ZIP_CAP // 1024))
    answer = _post("", {"message": message[:4000], "contact": contact[:200], "info": info or {},
                        "zip": base64.b64encode(data).decode("ascii")}, (info or {}).get("editor", ""), timeout)
    if not answer.get("id"):
        raise RuntimeError("the report service gave no report number: %s" % answer.get("error", answer))
    if full:
        return answer["id"], int(answer.get("issue") or 0)
    return answer["id"]


# --- answers to my reports: the editor keeps the numbers it sent; the relay gives back the author's comments on them
# (the reporter cannot see the private reports repo). The number is random and known only to the sender.
RE_SENT = re.compile(r"Report sent: (R-\d{8}-[0-9A-F]{6})")
RE_ID = re.compile(r"^R-\d{8}-[0-9A-F]{6}$")
CHECK_EVERY = 3 * 3600          # seconds between the checks on start
KEEP_SENT = 30                  # the relay answers 30 numbers at a time


def remember_sent(rid, issue=0, kind="bug", title=""):
    """A sent report into the settings list (newest first) - Answers to my reports asks for these."""
    import time
    from . import settings
    rows = [r for r in (settings.get("reports_sent") or []) if isinstance(r, dict) and r.get("id") != rid]
    rows.insert(0, {"id": rid, "issue": int(issue or 0), "kind": kind, "title": (title or "")[:120],
                    "at": time.strftime("%Y-%m-%d %H:%M")})
    settings.put("reports_sent", rows[:KEEP_SENT])


def sent_reports(log_texts=None):
    """Every report this editor sent: the settings list, plus numbers in the log ('Report sent: R-...') from versions
    before the list was kept. [{id, issue, kind, title, at}], newest first."""
    from . import settings
    rows = [dict(r) for r in (settings.get("reports_sent") or []) if isinstance(r, dict) and RE_ID.match(
        str(r.get("id", "")))]
    have = {r["id"] for r in rows}
    if log_texts is None:
        log_texts = []
        d = log.logs_dir()
        for name in (log.LOG_NAME, log.LOG_NAME + ".old"):
            try:
                with open(os.path.join(d, name), encoding="utf-8", errors="replace") as fh:
                    log_texts.append(fh.read())
            except (OSError, TypeError):
                pass
    for text in log_texts:
        for m in RE_SENT.finditer(text):
            if m.group(1) not in have:
                have.add(m.group(1))
                rows.append({"id": m.group(1), "issue": 0, "kind": "", "title": "", "at": m.group(1)[2:10]})
    return rows[:KEEP_SENT]


def answers(rows, version="", timeout=30):
    """The relay's answers for the reports: {id: {issue, state ('open' / 'closed'), reason ('completed' /
    'not_planned' / ''), messages [{from 'author' | 'you', text, at}]}}. Raises RuntimeError like send."""
    got = _post("answers", {"reports": [{"id": r["id"], "issue": int(r.get("issue") or 0)} for r in rows]},
                version, timeout)
    out = got.get("answers") or {}
    return out if isinstance(out, dict) else {}


def send_reply(rid, issue, message, data=None, version="", timeout=60):
    """The reporter's answer to the author, a comment on the same report (data: a zip of new pictures / logs)."""
    payload = {"id": rid, "issue": int(issue or 0), "message": message[:4000]}
    if data:
        if len(data) > ZIP_CAP:
            raise RuntimeError("the files are %d KB, over the %d KB the service takes" % (len(data) // 1024,
                                                                                       ZIP_CAP // 1024))
        payload["zip"] = base64.b64encode(data).decode("ascii")
    got = _post("reply", payload, version, timeout)
    if not got.get("ok"):
        raise RuntimeError("the report service did not take the reply: %s" % got.get("error", got))


def state_words(a):
    """A report's state in plain words."""
    if not a:
        return "no answer yet"
    if a.get("state") == "closed":
        return "closed - not planned" if a.get("reason") == "not_planned" else "closed - fixed / done"
    return "open"


def news(all_answers, seen):
    """The reports with something new since they were last looked at: more author messages than seen, or the state
    changed. seen = {id: {'n': author messages, 'state': 'open|closed reason'}} (settings 'reports_seen')."""
    out = []
    for rid, a in (all_answers or {}).items():
        n = sum(1 for m in a.get("messages", []) if m.get("from") == "author")
        st = "%s %s" % (a.get("state", ""), a.get("reason", ""))
        old = (seen or {}).get(rid) or {}
        if n > old.get("n", 0) or (old and st != old.get("state")) or (not old and a.get("state") == "closed"):
            out.append(rid)
    return out


def mark_seen(all_answers, ids=None):
    """Remember what was shown, so it is no longer 'new'."""
    from . import settings
    seen = dict(settings.get("reports_seen") or {})
    for rid, a in (all_answers or {}).items():
        if ids is None or rid in ids:
            seen[rid] = {"n": sum(1 for m in a.get("messages", []) if m.get("from") == "author"),
                         "state": "%s %s" % (a.get("state", ""), a.get("reason", ""))}
    settings.put("reports_seen", seen)
