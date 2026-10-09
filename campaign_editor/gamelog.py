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
    (r"invalid tile\((\d+), (\d+)\) for the settlement of (.+?)\.",
     "The town {2} sits on tile {0}, {1}, which nothing can reach (water, a blocked tile or off the map) - the game "
     "ignores it there for now, but armies cannot get to it. Move it on the Map (drag it) or check the map's size."),
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
    entries = parse(data.decode("latin-1", "replace"))
    errs = sum(1 for e in entries if e["level"] != "warning")
    out = ["THE GAME'S LOG IN PLAIN WORDS - %s" % path, "",
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


__all__ = ["parse", "explain", "summary", "mod_line", "report"]
