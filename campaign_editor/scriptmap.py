"""The scripts on the map (the user, 2026-10-18: 'every script seen on the map at once, carried like anything else,
a double click opens it as a town opens'): every campaign-map tile the campaign's scripts name (campaign_script.txt
and the file descr_strat names, upscale.script_files: spawned characters' 'x, y', the tile commands of SCRIPT_TILES)
and the Lua / Squirrel scripts beside the mod (upscale.move_code_line's places) - read with the same readers that move
them when the map changes size, so what is shown is what moves.

A spot is one place on one row: its file, line (0-based, the file's own numbering), sub (the row of an edited
line), k (its place among the row's places), xy. The edits not written yet: {path: {line: new text}} - the text may
hold more lines ('\n'), None takes the line out; the file's own numbering stays until Apply writes them."""

import os

from . import upscale as U
from .textio import TextFile


def _values_on(xy):
    """values(kind, nums) moving every tile through xy, distances / radii / sizes as they are (mapresize._mover)."""
    def values(kind, nums):
        if kind == "xy":
            return list(xy(nums[0], nums[1]))
        if kind == "xyr":
            return list(xy(nums[0], nums[1])) + [nums[2]]
        if kind == "dxy":
            return [nums[0]] + list(xy(nums[1], nums[2]))
        if kind == "area":
            return list(xy(nums[0], nums[1])) + list(xy(nums[2], nums[3]))
        return list(xy(nums[0], nums[1])) + list(nums[2:4])
    return values


def _move(text, xy, code):
    if code:
        return U.move_code_line(text, _values_on(xy), xy)[0]
    return U.move_script_line(text, _values_on(xy), xy)[0]


def places_in(text, code=False):
    """[(x, y)] of a line's places, in the order the movers meet them."""
    seen = []

    def rec(x, y):
        seen.append((x, y))
        return x, y
    _move(text, rec, code)
    return seen


def moved(text, k, to, code=False):
    """The line with its k-th place put on tile `to` (the rest as they are)."""
    n = [0]

    def one(x, y):
        i = n[0]
        n[0] += 1
        return tuple(to) if i == k else (x, y)
    return _move(text, one, code)


def files(mod, campaign):
    """[(path, code?)]: the campaign's script files, then the Lua / Squirrel scripts naming tiles."""
    out = [(p, False) for p in U.script_files(mod, campaign)]
    root = os.path.dirname(os.path.abspath(mod.data))
    try:
        out += [(p, True) for p in U.code_files_with_tiles(root)]
    except OSError:
        pass
    return out


def element(path, i, edits=None, lines=None):
    """Line i of the file as it will be written: its edit (text, more lines joined by '\n', None = taken out) or
    the file's own."""
    mine = (edits or {}).get(path) or {}
    if i in mine:
        return mine[i]
    if lines is None:
        lines = TextFile.load(path).texts()
    return lines[i] if 0 <= i < len(lines) else None


def rows(path, edits=None):
    """[(line, sub, text)] - the file as it will be written, each row with the file's line it stands for and its
    place among that line's rows (an edit may turn one line into several)."""
    lines = TextFile.load(path).texts()
    out = []
    for i in range(len(lines)):
        t = element(path, i, edits, lines)
        if t is not None:
            out += [(i, j, r) for j, r in enumerate(t.split("\n"))]
    return out


def spots(mod, campaign, edits=None):
    """Every place the scripts name, as spots {'id', 'path', 'line', 'sub', 'k', 'xy', 'text', 'code'}; edits:
    {path: {line: text}} not written yet."""
    out = []
    for path, code in files(mod, campaign):
        try:
            rs = rows(path, edits)
        except OSError:
            continue
        for i, j, text in rs:
            if code and not U.code_names_tiles(text):
                continue
            for k, xy in enumerate(places_in(text, code)):
                out.append({"id": "%s|%d|%d|%d" % (path, i, j, k), "path": path, "line": i, "sub": j, "k": k,
                            "xy": tuple(xy), "text": text, "code": code})
    return out


def move_spot(edits, spot, to):
    """The edits with the spot's place put on tile `to` (a new dict; the spot from spots() with the same edits)."""
    out = {p: dict(v) for p, v in (edits or {}).items()}
    parts = element(spot["path"], spot["line"], edits).split("\n")
    parts[spot["sub"]] = moved(parts[spot["sub"]], spot["k"], to, spot["code"])
    out.setdefault(spot["path"], {})[spot["line"]] = "\n".join(parts)
    return _clean(out)


def block(rs, n, code=False):
    """(start, end) rows of the block row n stands in - the command it belongs to (spawn_army ... end, a monitor ...
    end_monitor) as far as the blank rows round it, at most 31 rows; a Lua / Squirrel line with two rows round it.
    Widened to whole file lines (an edit's rows stay together)."""
    if code:
        a, b = max(0, n - 2), min(len(rs), n + 3)
    else:
        a = n
        while a > 0 and rs[a - 1][2].strip():
            a -= 1
        b = n + 1
        while b < len(rs) and rs[b][2].strip():
            b += 1
        if b - a > 31:                                   # a long run with no blank line: the rows round it
            a, b = max(0, n - 15), min(len(rs), n + 16)
    while a > 0 and rs[a][1]:
        a -= 1
    while b < len(rs) and rs[b][1]:
        b += 1
    return a, b


def set_block(edits, path, rs, a, b, text):
    """The edits with rows a..b of the file (rows()) replaced by text (its lines): line for line where the count of
    rows stays, else all into the block's first file line and the others taken out."""
    out = {p: dict(v) for p, v in (edits or {}).items()}
    mine = out.setdefault(path, {})
    new = text.split("\n")
    old = rs[a:b]
    groups = []                                          # [(file line, [rows])] in order
    for i, j, t in old:
        if not groups or groups[-1][0] != i:
            groups.append((i, []))
        groups[-1][1].append(t)
    if len(new) == len(old):
        n = 0
        for i, ts in groups:
            mine[i] = "\n".join(new[n:n + len(ts)])
            n += len(ts)
    elif groups:
        mine[groups[0][0]] = "\n".join(new)
        for i, _ in groups[1:]:
            mine[i] = None
    else:                                                # an empty block (an empty file): its first line
        mine[0] = "\n".join(new)
    return _clean(out)


def _clean(edits):
    """Edits that change nothing dropped (a line put back as it was)."""
    out = {}
    for path, changes in edits.items():
        try:
            lines = TextFile.load(path).texts()
        except OSError:
            continue
        keep = {i: t for i, t in changes.items() if not (0 <= i < len(lines) and t == lines[i])}
        if keep:
            out[path] = keep
    return out


def apply(plan, edits):
    """The edits written: each file's lines replaced in place (each keeps its ending; one line may become several or
    go)."""
    for path, changes in (edits or {}).items():
        if not changes:
            continue
        f = plan.edit(path)
        n = 0
        for i, text in sorted(changes.items(), reverse=True):
            if not 0 <= i < len(f.raw):
                continue
            if text is None:
                del f.raw[i]
            else:
                cr = "\r" if f.raw[i].endswith("\r") else ""
                f.raw[i:i + 1] = [t + cr for t in text.split("\n")]
            n += 1
        if n:
            plan.note(f, "%d line(s) of the script changed on the map" % n)


__all__ = ["spots", "places_in", "moved", "files", "rows", "element", "move_spot", "block", "set_block", "apply"]
