"""The editor's own look as the modder makes it (the user, 2026-10-17 / 2026-10-20: 'so I do not come to you for
every button: click it and change its size, its name, its place' - buttons and ticks dragged anywhere, and the
language of the editor, translated by the community and picked in Settings).

Kept apart from the windows (gui_look puts it on them):
- the look: {piece key: {'text', 'tip', 'width', 'hidden', 'to', 'where', 'xy', 'up', 'size'}} in
  CampaignEditor_look.json beside the settings ('to' + 'where': before / after another piece in a row; 'xy' + 'up':
  free, at x, y of its box or of the box 'up' boxes around it; 'size': [width, height] in pixels); a piece key names a button / tick / label by its window, the box it sits in and its own English words
  (gui_look.piece_key) - the code needs no names of its own, and a piece whose words the code changes later simply
  stops taking its change (nothing breaks);
- the languages: JSON files {'language': its own name, 'by': who translated, 'words': {English: translated}} -
  the editor's own (assets/lang) and the modder's (CampaignEditor_lang/); 'Words to translate' writes every English
  word of the windows (read from the code, words()) for a translator to fill.

Pure Python, no Tk."""

import ast
import json
import os

from . import log

LOOK_NAME = "_look.json"
LANG_FOLDER = "_lang"
BOARD_FOLDER = "_look_board"
KEYS = ("text", "tip", "width", "hidden", "to", "where", "xy", "up", "size")


def _home(name):
    h = log.home()
    return os.path.join(h, log.SHORT + name) if h else None


def look_file():
    return _home(LOOK_NAME)


def load(path=None):
    """{'pieces': {key: entry}, 'order': [key moved, in the order moved]} - empty when there is none (never raises)."""
    path = path or look_file()
    try:
        with open(path, encoding="utf-8") as fh:
            got = json.load(fh)
        pieces = {k: {a: b for a, b in v.items() if a in KEYS} for k, v in (got.get("pieces") or {}).items()
                  if isinstance(v, dict)}
        order = [k for k in got.get("order") or [] if k in pieces]
        return {"pieces": pieces, "order": order}
    except (OSError, ValueError, TypeError, AttributeError):
        return {"pieces": {}, "order": []}


def save(look, path=None):
    """The look written (pieces with nothing left are left out); False when it could not be."""
    path = path or look_file()
    if not path:
        return False
    pieces = {k: v for k, v in look["pieces"].items() if v}
    data = {"version": 1, "pieces": pieces, "order": [k for k in look["order"] if k in pieces and "to" in pieces[k]]}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
        return True
    except OSError:
        return False


def set_entry(look, key, entry):
    """A piece's change set (None or {} takes it out); a move goes to the end of the order (moves are put on in turn)."""
    entry = {a: b for a, b in (entry or {}).items() if a in KEYS and b not in (None, "", False)}
    if "to" in entry:                                   # in a row, or free: never both
        entry.pop("xy", None)
        entry.pop("up", None)
    elif "xy" not in entry:
        entry.pop("up", None)
    if entry:
        look["pieces"][key] = entry
    else:
        look["pieces"].pop(key, None)
    if key in look["order"]:
        look["order"].remove(key)
    if "to" in entry:
        look["order"].append(key)


def merged(entry, change):
    """A piece's entry with a change laid over it (None in the change takes that part out) - a new dict."""
    new = dict(entry or {})
    for k, v in (change or {}).items():
        if v is None:
            new.pop(k, None)
        else:
            new[k] = v
    return new


# ---- the layout board (gui_lookboard): every page of the editor laid out side by side ----
def board_dir():
    return _home(BOARD_FOLDER)


def load_board(folder=None):
    """The pages last gathered: [{'id', 'title', 'group', 'size', 'picture', 'pieces', 'hidden'}] ([] when none)."""
    folder = folder or board_dir()
    try:
        with open(os.path.join(folder, "pages.json"), encoding="utf-8") as fh:
            got = json.load(fh)
        return [p for p in got.get("pages") or [] if isinstance(p, dict) and p.get("id")]
    except (OSError, ValueError, TypeError, AttributeError):
        return []


def save_board(pages, folder=None):
    folder = folder or board_dir()
    if not folder:
        return False
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "pages.json"), "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "pages": pages}, fh, ensure_ascii=False)
        return True
    except OSError:
        return False


CARD_HEAD = 70


def lay_cards(groups, row_width=8200, gap=80, head=CARD_HEAD):
    """Where each page card stands on the board: groups = [[(id, width, height), ...], ...] (a group = one kind of
    page: the works, the tabs of one work, the windows); each group starts a row of its own under its heading, its
    cards side by side, wrapping at row_width; each card's title in the head above it.
    -> ({id: (x, y)}, (total width, total height), [y of each group's heading])."""
    out, tops, y, right = {}, [], 0, 0
    for group in groups:
        tops.append(y)
        y += head
        x, line = 0, 0
        for pid, w, h in group:
            if x and x + w > row_width:
                x, y = 0, y + line + gap + head
                line = 0
            out[pid] = (x, y + head)
            x += w + gap
            line = max(line, h)
            right = max(right, x - gap)
        if group:
            y += head + line + gap * 4                 # room for the next group's heading
    return out, (right, max(y - gap * 4, 0)), tops


def piece_at(pieces, x, y):
    """The smallest piece whose box holds x, y (pieces = [{'key', 'box': [x, y, w, h]}]), or None."""
    best = None
    for p in pieces:
        bx, by, bw, bh = p["box"]
        if bx <= x < bx + bw and by <= y < by + bh and (best is None or bw * bh < best["box"][2] * best["box"][3]):
            best = p
    return best


def drop_beside(pieces, moved, x, y):
    """Where a piece dropped at x, y stands in a row: (the nearest other piece, 'before' / 'after' by which half of
    it the mouse is on) - pieces holding the moved one or held by it are skipped; (None, None) when there is none."""
    mb = moved["box"]
    best, dist = None, None
    for p in pieces:
        if p["key"] == moved["key"]:
            continue
        bx, by, bw, bh = p["box"]
        if _holds(p["box"], mb) or _holds(mb, p["box"]):
            continue
        dx = max(bx - x, 0, x - (bx + bw))
        dy = max(by - y, 0, y - (by + bh))
        d = dx * dx + dy * dy
        if dist is None or d < dist:
            best, dist = p, d
    if best is None:
        return None, None
    return best, ("before" if x < best["box"][0] + best["box"][2] / 2 else "after")


def _holds(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[0] + a[2] >= b[0] + b[2] and a[1] + a[3] >= b[1] + b[3]


def free_spot(boxes, x, y, w, h):
    """A piece put free with its top left at x, y (w x h): (how many boxes up from its own it goes - the first box
    of boxes = [own box, the one around it, ...] that holds it whole, else the last - , x and y in that box)."""
    for up, (bx, by, bw, bh) in enumerate(boxes):
        if bx <= x and by <= y and x + w <= bx + bw and y + h <= by + bh:
            return up, int(x - bx), int(y - by)
    up = max(len(boxes) - 1, 0)
    bx, by = (boxes[up][0], boxes[up][1]) if boxes else (0, 0)
    return up, int(x - bx), int(y - by)


# ---- languages ----
def lang_dirs():
    """(the editor's own languages, the modder's own) folders."""
    from .addons import assets_dir
    own = os.path.join(os.path.dirname(assets_dir()), "lang")
    return own, _home(LANG_FOLDER)


def languages():
    """{language name: file} of every language file found (the modder's own win over the editor's of one name)."""
    out = {}
    for d in lang_dirs():
        if not d or not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if n.lower().endswith(".json"):
                p = os.path.join(d, n)
                got = read_language(p)
                if got is not None:
                    out[got["language"]] = p
    return out


def read_language(path):
    """{'language', 'by', 'words'} of a language file, or None when it is not one."""
    try:
        with open(path, encoding="utf-8-sig") as fh:
            got = json.load(fh)
        words = {str(k): str(v) for k, v in (got.get("words") or {}).items() if isinstance(v, str) and v.strip()}
        name = str(got.get("language") or os.path.splitext(os.path.basename(path))[0])
        return {"language": name, "by": str(got.get("by") or ""), "words": words}
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def add_language(src):
    """A language file copied into the modder's own folder; returns its name there, or raises ValueError / OSError."""
    got = read_language(src)
    if got is None:
        raise ValueError("%s is not a language file of the editor (JSON with 'words')" % os.path.basename(src))
    d = lang_dirs()[1]
    if not d:
        raise OSError("the editor has no folder of its own here")
    os.makedirs(d, exist_ok=True)
    import shutil
    shutil.copyfile(src, os.path.join(d, os.path.basename(src)))
    return got["language"]


# the calls whose words a window shows: keyword text= / label= (buttons, ticks, menus, tabs, headings), the first
# argument of these, the second of tip(widget, words)
_WORD_KEYWORDS = ("text", "label")
_FIRST_ARG = ("title", "add_command", "add_checkbutton", "add_radiobutton", "add_cascade")
_SECOND_ARG = ("tip", "Tip", "hint")


def words(folder=None):
    """[English words] every window of the editor shows, read from its code (the gui_*.py files): text= / label=
    words, window titles, hover texts - whole strings only (words built at run time are not here; a translator sees
    them in the editor and can add them)."""
    folder = folder or os.path.dirname(os.path.abspath(__file__))
    found = {}
    for n in sorted(os.listdir(folder)):
        if not (n.startswith("gui") and n.endswith(".py")):
            continue
        try:
            with open(os.path.join(folder, n), encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            cands = [kw.value for kw in node.keywords if kw.arg in _WORD_KEYWORDS]
            if name in _FIRST_ARG and node.args:
                cands.append(node.args[0])
            if name in _SECOND_ARG and len(node.args) > 1:
                cands.append(node.args[1])
            for c in cands:
                s = _const(c)
                if s and s.strip() and any(ch.isalpha() for ch in s):
                    found.setdefault(s, None)
    return list(found)


def _const(node):
    """The string a node always is: a literal, or literals joined with + / implicit joining; else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _const(node.left), _const(node.right)
        return a + b if a is not None and b is not None else None
    return None


def template(have=None, seen=()):
    """A language file to fill: every word of the windows (and the words seen in them while the editor ran), each
    with its translation so far ('' when none)."""
    have = have or {}
    out = {}
    for w in list(words()) + [s for s in seen if s]:
        out.setdefault(w, have.get(w, ""))
    return {"language": "", "by": "", "words": out}


__all__ = ["load", "save", "set_entry", "merged", "look_file", "board_dir", "load_board", "save_board", "lay_cards",
           "piece_at", "drop_beside", "free_spot", "languages", "read_language", "add_language", "words",
           "template", "KEYS"]
