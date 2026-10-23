"""The game's own log (system.log.txt) in plain words: what the game could not read or did not find, grouped, with
the mod's line it names and what to do about it. Both games, with or without REX / M2EX (their log lines share a
form: 'hh:mm:ss.ms [area] [error|warning] message', a Script Error's reason on the lines after it).

Read only - nothing is written. The texts explained were seen in real logs (players' reports, the vanilla games)."""

import os
import re

RE_LINE = re.compile(r"^\d\d:\d\d:\d\d(?:\.\d+)?\s+\[([^\]]+)\]\s+\[(fatal|error|warning|warn)\]\s*(.*)$", re.I)
RE_ANY = re.compile(r"^\d\d:\d\d:\d\d(?:\.\d+)?\s+\[")
RE_SCRIPT = re.compile(r"(Script Error|Trigger parsing warning) in (.+?), at line (\d+), column (\d+)", re.I)

# (pattern, what it means and what to do) - {0}, {1}... are the pattern's groups
KNOWN = [
    (r"year_founded",
     "A town's founding year (descr_strat.txt, 'year_founded') is later than the campaign's start year - the game "
     "stops here. Set it to the start year or earlier."),
    (r"Character '(.+?)' is placed on an invalid tile",
     "{0} stands on a tile no one may stand on (the sea, a river, mountains, dense forest, off the map) - the game "
     "leaves him out. Move him on the Map (drag him)."),
    (r"unit\((.+?)\) does not match up to the ownership for faction\((.+?)\)",
     "A building lets {1} recruit '{0}', but the unit's ownership (export_descr_unit.txt) does not name {1} - the "
     "game drops that recruit line. Give {1} the unit (Roster tab: Give) or take {1} off the line (Buildings)."),
    # the engine's own words (world.cpp finalise_campaign_setup, world_map.cpp assign_region_frontiers): a town on a
    # tile it puts no town on - the region is skipped: land with no town and no owner; Medieval II with M2EX then
    # crashed as the campaign started, in the AI's look at the neighbours (R-20261023-D68B3A)
    (r"invalid tile\((\d+), ?(\d+)\) for a settlement position in region\((\d+)\)\.?\s*PLACEMENT_(\w+)",
     "The town of region number {2} stands at {0}, {1} on a tile the game puts no town on (its reason: {3}; it "
     "takes no mountains, dense forest, river, ford, cliff or sea) - the game leaves that region with no town and no owner, and Medieval II "
     "crashes as the campaign starts. Drag the town (Map) to flat open land."),
    (r"invalid tile\((\d+), ?(\d+)\) for the settlement of ([^,.\s]+)",
     "The town {2} stands at {0}, {1} on a tile the game puts no town on (mountains, dense forest, a river, ford or "
     "cliff, the sea, off the map) - the game skips its region: no town, no owner, and Medieval II crashes as the "
     "campaign starts. Drag the town (Map) to flat open land; Check names every such town."),
    (r"land region '(.+?)' \(id (\d+)\) has no owning faction",
     "Region {0} has land but no town and no owner (its town was skipped - see the 'invalid tile' line before, or no "
     "descr_strat.txt settlement) - Medieval II crashes when the AI looks at its neighbours. Move its town to flat "
     "open land (Map)."),
    (r"we already have a port position in this region",
     "Two port pixels count for one region: the game gives a port to the first land next to it, looking up, right, "
     "down, left - one port meant for a neighbour went to this region, the neighbour has none. Check names the "
     "region; drag the port (Map)."),
    (r"Unknown settlement level : (\w+)",
     "descr_campaign_db.xml names a settlement level '{0}' the game does not know (its castle levels: "
     "moot_and_bailey - the game's own spelling -, wooden_castle, castle, fortress, citadel; the cities: village, "
     "town, large_town, city, large_city, huge_city) - that rule is not set. The mod's own file; not a crash by "
     "itself. Campaign rules fixes the word."),
    (r"Target building level not allowed: (.+?), (\w+) -> (\w+)",
     "When a {1} of {0} turns into a {2} (a city made a castle or back, Medieval II), its buildings change by their "
     "chains' convert_to lines - here into a level {0} may not build. Check the requires lines of those levels for "
     "that faction (Buildings) or the convert_to lines."),
    (r"FactionType: faction not found",
     "A file or a script names a faction this mod does not have. The vanilla games' prologue scripts do this too "
     "(harmless there); otherwise look for a removed or renamed faction in the scripts and descr_strat.txt."),
    (r"open: (.+?) is missing",
     "The game looked for {0} and did not find it. Often harmless (it falls back to something else); a missing "
     "picture shows as a blank or a default one."),
    (r"Cannot find the portrait path: (.+?),",
     "No portrait pictures in {0} - the game uses the culture's default ones."),
    (r"Unresolved sprite definition\((.+?)\)",
     "An interface picture {0} is not on its sprite page - the game draws another in its place (a faction logo "
     "missing for a new faction, often)."),
    (r"Game selection invalid - is the path '(.*?)' ok",
     "The engine could not tell which game or mod to run: the path it read ('{0}') makes no sense - letters it reads "
     "wrong (a folder with non-Latin letters on the way to the game), or the engine started away from the game's "
     "folder. Start the mod with its .bat from the mod's folder, or with the -mod: line from the game's folder; this "
     "is the engine's own log - the campaign editor does not start the game."),
    (r"skeleton\.cpp\(\d+\): adata != 0",
     "A battle skeleton names an animation the game cannot find - in no animation pack (data/animations/pack.idx) "
     "and no loose .cas file at its path - so the game stops while it loads the animations, before the menu. "
     "Units brought from another mod are the usual cause: bring them again with this editor's newest version (it "
     "carries the animation or leaves that skeleton out), or copy the missing .cas file from the other mod. "
     "(Report R-20261018-D47E51.)"),
    (r"Condition eval: (\w+) needs a (\w+)",
     "A script condition '{0}' asks about a {1}, but the event it runs on gives none (campaign_script.txt or "
     "export_descr_*: a condition on an event of another kind) - the game takes it as false and goes on; the "
     "trigger never fires. Not a crash."),
    (r"encountered an unspecified error",
     "The game crashed. The lines just before this one in the log name what it was doing."),
    (r"DATA: src.(.+?)\((\d+)\)",
     "The game's own check failed in its code ({0}, line {1}) while reading data - the lines before it in the log "
     "say what it was reading."),
    (r"does not exist|not found|unknown",
     "The game met a name it does not know."),
]


def parse(text):
    """[{'level', 'area', 'msg', 'why', 'file', 'line', 'col'}] of every error / warning line, a Script Error's
    reason (the lines after it without a time) in 'why'."""
    out = []
    lines = text.splitlines()
    for i, l in enumerate(lines):
        m = RE_LINE.match(l)
        if not m:
            continue
        area, level, msg = m.group(1), m.group(2).lower(), m.group(3).strip()
        e = {"level": {"fatal": "fatal", "error": "error"}.get(level, "warning"), "area": area, "msg": msg, "why": "",
             "file": None, "line": None, "col": None}
        s = RE_SCRIPT.search(msg)
        if s:
            e["file"], e["line"], e["col"] = s.group(2).replace("\\", "/"), int(s.group(3)), int(s.group(4))
            why = []
            for k in range(i + 1, min(i + 6, len(lines))):
                if RE_ANY.match(lines[k]) or not lines[k].strip():
                    break
                why.append(lines[k].strip())
            e["why"] = " ".join(why)
        out.append(e)
    return out


def explain(text, generic=False):
    """Plain words for a log message (or a Script Error's reason), or ''. generic: for a group whose lines name
    different units / factions / towns - the names become 'X', 'Y'... (the lines below name them)."""
    for pattern, words in KNOWN:
        m = re.search(pattern, text, re.I)
        if m:
            if generic and m.groups():
                return words.format(*"XYZWV"[:len(m.groups())]) + " (X, Y: as each line below names them)"
            return words.format(*m.groups())
    return ""


def _key(e):
    """Entries that say the same thing of different lines or names count as one."""
    s = re.sub(r"\([^)]*\)", "()", e["why"] or e["msg"])
    s = re.sub(r"'[^']*'", "''", s)
    s = re.sub(r"\d+", "N", s)
    return (e["level"], e["file"], s[:120])


ORDER = {"fatal": 0, "error": 1, "warning": 2}


def summary(entries):
    """[(entry, count, [(line, its reason)])] grouped: a crash first, then errors, the most frequent first."""
    groups = {}
    for e in entries:
        g = groups.setdefault(_key(e), [e, 0, []])
        g[1] += 1
        if len(g[2]) < 6 and (e["line"] is not None or e["why"]):
            g[2].append((e["line"], e["why"]))
    return sorted(groups.values(), key=lambda g: (ORDER[g[0]["level"]], -g[1]))


def mod_line(game, rel, line):
    """The text of line `line` of the file the log names (relative to the game folder), or None."""
    if not game or not rel:
        return None
    path = os.path.join(game, *rel.split("/"))
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="latin-1") as fh:
            for n, t in enumerate(fh, 1):
                if n == line:
                    return t.rstrip("\r\n")
    except OSError:
        return None
    return None


def report(path, game=None, limit=40):
    """The whole log in plain words, as the text the window shows."""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) > 40 * 1024 * 1024:
        data = data[-40 * 1024 * 1024:]                 # a very long log: its newest part
    text = data.decode("utf-8", "replace")
    entries = parse(text)
    errs = sum(1 for e in entries if e["level"] != "warning")
    v = verdict(text, game)
    out = ["THE GAME'S LOG IN PLAIN WORDS - %s" % path, ""]
    if v:                                                # the crash doctor's word first
        out += ["IN SHORT: " + v["headline"]]
        if v.get("now"):
            out += ["    %s line %s reads now: %s" % (v["file"], v["line"], v["now"].strip()[:200])]
        out += ["    serious, the game went on: " + w for w in v["serious"][:3]] + [""]
    out += [
           "%d error line(s), %d warning(s). Grouped below: errors first, the most frequent first. A Script Error "
           "names a file and a line: that line is shown as the mod has it now." % (errs, len(entries) - errs), ""]
    if not entries:
        out.append("No errors or warnings - the game read everything it was given.")
    for e, n, seen in summary(entries)[:limit]:
        head = "%s%s" % ({"fatal": "CRASH", "error": "ERROR"}.get(e["level"], "warning"), " x%d" % n if n > 1 else "")
        where = " in %s" % e["file"] if e["file"] else ""
        out.append("%s  [%s]%s" % (head, e["area"], where if e["file"] else " " + e["msg"][:200]))
        plain = explain(e["why"] or e["msg"], generic=len({w for _, w in seen}) > 1)
        if plain:
            out.append("    what it means: %s" % plain)
        for line, why in seen:
            text = mod_line(game, e["file"], line) if e["file"] and line else None
            out.append("    %s%s" % ("line %d: " % line if line else "", why[:220] if why else ""))
            if text is not None:
                out.append("        the line now reads: %s" % text.strip()[:200])
        if n > len(seen) and seen:
            out.append("    ... %d more like it" % (n - len(seen)))
        out.append("")
    more = len(summary(entries)) - limit
    if more > 0:
        out.append("... and %d more kind(s) of message." % more)
    return "\n".join(out)


RE_FATAL = re.compile(r"\[fatal\]|encountered an unspecified error", re.I)
RE_STOP = re.compile(r"ASSERT FAILED|encountered an unspecified error", re.I)
RE_CLOSED = re.compile(r"sprites_close\(\)|libs called display_close", re.I)
RE_CODE = re.compile(r"(?:ASSERT FAILED|ERROR|DATA):\s*src[\\/](\S+?)\((\d+)\)(?::\s*(.*))?", re.I)
RE_PATH = re.compile(r"((?:data/)?[\w\-./\\]+\.(?:txt|tga|dds|texture|cas|mesh|xml|lnt|db|modeldb|spr))", re.I)
# fatal lines the game goes on after but crashes from later (Medieval II with M2EX: a region skipped for its town's
# tile, then the AI's look at its neighbours - R-20261023-D68B3A, an access violation and no stop in the log)
RE_CRASH_LATER = re.compile(r"skipping region|for a settlement position in region|has no owning faction", re.I)
RE_PORT_LATER = re.compile(r"we already have a port position", re.I)
GENERIC = ("The game crashed.", "The game's own check failed", "The game met a name")


def fatal_events(lines):
    """[(index, the fatal line, its detail)] - the engine (REX, M2EX) writes what went wrong on the lines after a
    fatal line, before its '  at ...' call stack ('failed to find art piece ...', 'Unable to load ....texture')."""
    out = []
    for i, l in enumerate(lines):
        if not RE_FATAL.search(l):
            continue
        detail = []
        for t in lines[i + 1:i + 6]:
            if not t.strip():
                continue
            if t.lstrip().startswith("at ") or RE_ANY.match(t):
                break
            detail.append(t.strip())
        out.append((i, l.strip(), " ".join(detail)))
    return out


def _words(line, detail):
    """Plain words for a fatal line and its detail: a known one's, else the engine's own detail, else its code."""
    for text in (detail, line):
        plain = explain(text) if text else ""
        if plain and not plain.startswith(GENERIC):
            return plain
    if detail:
        return "the game says: %s" % detail[:220]
    m = RE_CODE.search(line)
    if m:
        return "the game's check %s line %s%s failed (no words of its own)" % (
            m.group(1).replace("\\", "/"), m.group(2), ": " + m.group(3) if m.group(3) else "")
    return ""


WENT_ON = 150       # log lines after an ASSERT (call stack left out) that say the game ran on


def _went_on(lines, at):
    """The game wrote on after line `at`: more than WENT_ON lines that are not its call stack."""
    n = 0
    for t in lines[at + 1:]:
        s = t.strip()
        if s and not s.startswith("at "):
            n += 1
            if n > WENT_ON:
                return True
    return False


def verdict(text, game=None):
    """The crash doctor's word on the game's last run (its system.log.txt as text): {'headline': one line in plain
    words, 'lines': [the log lines it rests on], 'serious': [plain words of fatal errors the game went on after],
    'file', 'line', 'now' (that line of the mod as it reads now)} - or None for a log with nothing to say. A stop
    is an ASSERT FAILED or 'unspecified error'; a '[fatal] ERROR' the game goes on after (a fallback taken) is
    serious, not the stop. Its cause: the engine's detail line, else the nearest Script Error before it."""
    lines = text.splitlines()
    events = fatal_events(lines)
    closed = any(RE_CLOSED.search(t) for t in lines[-60:])
    # an ASSERT the game went on after is no stop (HLR writes ~28 at every load - a tester, 2026-10-22: 'The game
    # stopped' offered for a game that ran on): a stop ends the log - a call stack, a few lines, the game closing
    stops = [e for e in events if RE_STOP.search(e[1]) and not _went_on(lines, e[0])]
    serious, later, ports_ = [], [], []
    for i, line, detail in events:
        if stops and i == stops[-1][0]:
            continue
        w = _words(line, detail)
        if w and w not in serious:
            serious.append(w)
            if RE_CRASH_LATER.search(line + " " + detail):
                later.append(w)
            elif RE_PORT_LATER.search(line + " " + detail):
                ports_.append(w)
    later += ports_                                                # what crashes the game later goes first
    serious = later + [w for w in serious if w not in later]
    if not stops:
        if not events and not closed:
            return None
        head = "No crash in the game's log%s." % (": the game was closed in the usual way" if closed else "")
        if serious:
            head += " %d serious error(s) it went on after - the %s: %s" % (
                len(serious), "one that crashes it later" if later else "first", serious[0])
        return {"headline": head, "lines": [], "serious": serious[:5], "file": None, "line": None, "now": None}
    at, first, detail = stops[-1]
    why = _words(first, detail)
    rel = line_no = None
    paths = RE_PATH.findall(detail or "")
    if paths:
        rel = paths[0].replace("\\", "/")
    before = [t for t in lines[max(0, at - 30):at] if t.strip()]
    for e in reversed(parse("\n".join(before))):          # a Script Error just before: its file and line
        if e["file"]:
            if rel is None:
                rel, line_no = e["file"], e["line"]
            if not why or why.startswith("the game's check"):
                why = "%s line %s: %s" % (e["file"], e["line"], (e["why"] or e["msg"])[:200])
            break
    head = "The game stopped: %s" % (why or "the log names no cause - the lines before the stop go with the report")
    return {"headline": head, "lines": before[-8:] + [first] + ([detail] if detail else []), "serious": serious[:5],
            "file": rel, "line": line_no,
            "now": mod_line(game, rel, line_no) if rel and line_no else None}


__all__ = ["parse", "explain", "summary", "mod_line", "report", "verdict"]
