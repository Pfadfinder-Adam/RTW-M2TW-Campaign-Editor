"""Forts and watchtowers of a campaign's descr_strat.txt: moved, removed and added on the Map (Edit forts &
watchtowers), both games.

A fort / watchtower is one line: `watchtower 53 152` (Barbarian Invasion, in its region section after the
diplomacy), `fort 263 330 cerin_amroth_fort culture middle_eastern permanent name Cerin Amroth` (Medieval II
mods, in a faction's block). Their exact form differs by game and mod, and neither vanilla Rome nor vanilla Medieval
II has one, so a new one copies a line of the same kind the campaign already has - the nearest one, only its tile
changed, put right after it (same section, same owner). Without such a line a new one is refused in plain words.
A moved one keeps its line, only the tile changes; a removed one loses its line."""

import re

from .strat import RE_FORT, Strat

KINDS = ("fort", "watchtower")
RE_XY_PART = re.compile(r"^(\s*(?:fort|watchtower)\s+)(-?\d+)(\s*,?\s*)(-?\d+)")


def read(mod, campaign):
    """[strat.Fort] of the campaign (every line of the file, the diplomacy part too)."""
    return Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).forts


def problem(mod, campaign, xy, taken=()):
    """None, or why a fort / watchtower may not stand on tile xy: on land, not on a town, port or another one."""
    x, y = xy
    img = mod.region_map(campaign)
    if not (0 <= x < img.width and 0 <= y < img.height):
        return "off the map"
    if mod.is_sea(campaign, (x, y)):
        return "not on the sea"
    if tuple(xy) in {tuple(t) for t in mod.city_tiles(campaign).values()}:
        return "a town stands there"
    if img.get(x, y) in ((0, 0, 0), (255, 255, 255)):
        return "a town or port stands there"
    if tuple(xy) in {tuple(t) for t in taken}:
        return "another fort or watchtower stands there"
    return mod.land_problem(campaign, (x, y))


def example(forts, kind, xy):
    """The line a new `kind` at xy copies: the nearest one of that kind, or None."""
    same = [f for f in forts if f.kind == kind]
    if not same:
        return None
    return min(same, key=lambda f: (f.xy[0] - xy[0]) ** 2 + (f.xy[1] - xy[1]) ** 2)


def moved_line(text, xy):
    """The fort line with its tile changed, the rest (spacing, comma, type, culture, name, comment) kept."""
    return RE_XY_PART.sub(lambda m: "%s%d%s%d" % (m.group(1), xy[0], m.group(3), xy[1]), text, count=1)


def apply(plan, campaign, changes):
    """changes = {'moved': {line: (x, y)}, 'removed': [line], 'added': [{'kind', 'xy'}]} (JSON keys may be
    strings; line = the line's index in descr_strat.txt as read). Run before the resources (whose lines lie
    above the forts)."""
    if not changes:
        return
    moved = {int(k): tuple(v) for k, v in (changes.get("moved") or {}).items()}
    removed = {int(k) for k in changes.get("removed") or []}
    added = list(changes.get("added") or [])
    if not (moved or removed or added):
        return
    mod = plan.mod
    f = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
    now = Strat(f).forts
    by_line = {fo.line: fo for fo in now}
    for k in list(moved) + list(removed):
        if k not in by_line:
            raise ValueError("no fort or watchtower on line %d of descr_strat.txt (the file changed?)" % (k + 1))
    final = [moved.get(fo.line, fo.xy) for fo in now if fo.line not in removed] + [tuple(a["xy"]) for a in added]

    def others(xy):
        rest = list(final)
        rest.remove(tuple(xy))
        return rest

    for line, xy in moved.items():
        fo = by_line[line]
        why = problem(mod, campaign, xy, others(xy))
        if why:
            raise ValueError("the %s at %d, %d cannot go to %d, %d: %s" % (fo.kind, fo.xy[0], fo.xy[1], xy[0], xy[1],
                                                                           why))
        f.set(line, moved_line(f.text(line), xy))
        plan.note(f, "%s moved from %d, %d to %d, %d" % (fo.kind, fo.xy[0], fo.xy[1], xy[0], xy[1]))
    inserts = []                                   # (after line, text)
    for a in added:
        kind, xy = a["kind"], tuple(a["xy"])
        if kind not in KINDS:
            raise ValueError("'%s' is neither a fort nor a watchtower" % kind)
        why = problem(mod, campaign, xy, others(xy))
        if why:
            raise ValueError("a new %s at %d, %d: %s" % (kind, xy[0], xy[1], why))
        ex = example([fo for fo in now if fo.line not in removed], kind, xy)
        if ex is None:
            raise ValueError(no_example(kind))
        inserts.append((ex.line, moved_line(f.text(ex.line), xy)))
        plan.note(f, "new %s at %d, %d (its line copied from the one at %d, %d%s)" % (
            kind, xy[0], xy[1], ex.xy[0], ex.xy[1], ", %s's" % ex.owner if ex.owner else ""))
    # bottom up, so the lines above keep their places
    ops = [(line, "del", None) for line in removed] + [(line, "add", text) for line, text in inserts]
    for line, op, text in sorted(ops, key=lambda o: (-o[0], o[1] == "del")):
        if op == "del":
            fo = by_line[line]
            del f.raw[line]
            plan.note(f, "%s at %d, %d removed" % (fo.kind, fo.xy[0], fo.xy[1]))
        else:
            f.raw[line + 1:line + 1] = [f.make(text)]


def no_example(kind):
    return ("this campaign has no %s line to copy: the line the game wants differs by game and mod (vanilla Rome and "
            "Medieval II have none), so a new one is made only from one the campaign already has" % kind)


__all__ = ["KINDS", "read", "problem", "example", "moved_line", "apply", "no_example", "RE_FORT"]
