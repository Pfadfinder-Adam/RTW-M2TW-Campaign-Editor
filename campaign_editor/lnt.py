"""The games' menu layout files (.lnt): Rome data/menu/Rome.lnt (Barbarian Invasion bi/data/menu/Rome.lnt,
Alexander alexander/data/menu/rome.lnt), Medieval II data/menu/mtw2.lnt - read and written byte-exact, only the
lines meant change (rules.md 'MENU LAYOUT FILES (.lnt) - THE FORMAT'; the idea and the first map of the format from
Wholesome Queen's RTW Sprite & HUD Studio, given to make this editor better).

Not XML: a block is '<tag>value' with its value on the same line, its children below, then '</tag>'; a leaf is
'<tag>value</tag>' on one line. The pieces of the menus live in <layout> -> <lpage>PAGE -> <UI piece>NAME, each
with <identifier> (its behaviour), <Parameters> (x, y, width, height on the 1024 x 768 layout, menu_id = the page a
button opens, <UI text>KEY with its font and align, tool_tip_id) and <object_id> - the picture chain is
piece -> <UI object> -> <UI region>STATE -> <page> (a picture under data/menu/<path>/) + <region> (a box on it).
"""

import os
import re

FILES = ("Rome.lnt", "rome.lnt", "mtw2.lnt")
PARAMS = ("x", "y", "width", "height")

_LEAF = re.compile(r"^<([^/<>][^<>]*)>(.*)</\1>$")
_OPEN = re.compile(r"^<([^/<>][^<>]*)>(.*)$")
_CLOSE = re.compile(r"^</([^<>]+)>$")


class Node:
    """A block or a leaf: tag, value (the text after the open tag), first line, last line (its close; = first for a
    leaf), children."""
    __slots__ = ("tag", "value", "start", "end", "children", "leaf")

    def __init__(self, tag, value, start, leaf=False):
        self.tag, self.value, self.start, self.end, self.children, self.leaf = tag, value, start, start, [], leaf

    def find(self, tag):
        return next((c for c in self.children if c.tag == tag), None)

    def all(self, tag):
        return [c for c in self.children if c.tag == tag]

    def get(self, tag, default=None):
        c = self.find(tag)
        return c.value if c is not None else default

    def __repr__(self):
        return "<Node %s %r %d-%d>" % (self.tag, self.value, self.start, self.end)


class LntError(ValueError):
    pass


def _split(text):
    """The lines with their own endings (CRLF kept)."""
    return text.splitlines(keepends=True)


class Lnt:
    """One .lnt file: its lines (each with its ending, latin-1) and the tree read from them."""

    def __init__(self, data, path=None):
        if isinstance(data, bytes):
            data = data.decode("latin-1")
        self.path = path
        self.lines = _split(data)
        self.parse()

    @classmethod
    def load(cls, path):
        with open(path, "rb") as fh:
            return cls(fh.read(), path)

    def dump(self):
        return "".join(self.lines).encode("latin-1")

    # ---- reading ----
    def parse(self):
        self.root = Node("", "", -1)
        stack = [self.root]
        for i, raw in enumerate(self.lines):
            s = raw.strip()
            if not s:
                continue
            m = _LEAF.match(s)
            if m:
                stack[-1].children.append(Node(m.group(1), m.group(2).strip(), i, leaf=True))
                continue
            m = _CLOSE.match(s)
            if m:
                if len(stack) == 1 or stack[-1].tag != m.group(1):
                    raise LntError("line %d: </%s> closes nothing open%s" % (
                        i + 1, m.group(1), "" if len(stack) == 1 else " (open: <%s>)" % stack[-1].tag))
                stack[-1].end = i
                stack.pop()
                continue
            m = _OPEN.match(s)
            if m:
                n = Node(m.group(1), m.group(2).strip(), i)
                stack[-1].children.append(n)
                stack.append(n)
        if len(stack) > 1:
            raise LntError("<%s> (line %d) is never closed" % (stack[-1].tag, stack[-1].start + 1))
        self.root.end = len(self.lines)

    def textures(self):
        """{page as the objects name it (textures\\FE_texture1.tga): {'path', 'regions': {name: (l, t, r, b)}}}."""
        out = {}
        for t in self.root.all("texture"):
            regions = {}
            for r in t.all("region"):
                try:
                    regions[r.value] = tuple(int(r.get(k)) for k in ("left", "top", "right", "bottom"))
                except (TypeError, ValueError):
                    continue
            out[t.value] = {"path": t.get("path", ""), "regions": regions}
        return out

    def fonts(self):
        """{identifier: {'file', 'height'}}."""
        return {f.get("identifier", f.value): {"file": f.value, "height": f.get("lf_height")}
                for f in self.root.all("font")}

    def objects(self):
        """{object name: {'type', 'regions': {state: (page, region)}}}."""
        out = {}
        for o in self.root.all("UI object"):
            out[o.value] = {"type": o.get("type", ""),
                            "regions": {r.value: (r.get("page", ""), r.get("region", "")) for r in o.all("UI region")}}
        return out

    def layout(self):
        return self.root.find("layout")

    def size(self):
        lay = self.layout()
        try:
            return int(lay.get("layout_width")), int(lay.get("layout_height"))
        except (AttributeError, TypeError, ValueError):
            return 1024, 768

    def pages(self):
        """[page name] in the file's order."""
        lay = self.layout()
        return [p.value for p in lay.all("lpage")] if lay is not None else []

    def page_node(self, page):
        lay = self.layout()
        return next((p for p in lay.all("lpage") if p.value == page), None) if lay is not None else None

    def pieces(self, page):
        """[piece dict] of a page: name, identifier, x, y, width, height (int or None), menu_id, text, font,
        align, tooltip, object, node."""
        p = self.page_node(page)
        return [piece_info(n) for n in p.all("UI piece")] if p is not None else []

    def piece(self, page, name):
        return next((x for x in self.pieces(page) if x["name"] == name), None)

    def opened_by(self):
        """{page: [(page, piece)]}: which buttons open each page (their menu_id) - the way to a page."""
        out = {}
        for page in self.pages():
            for x in self.pieces(page):
                if x["menu_id"]:
                    out.setdefault(x["menu_id"], []).append((page, x["name"]))
        return out

    def art(self, piece, state=None):
        """(texture page, (l, t, r, b), texture path folder) of a piece's picture, or None: its object's region for
        the state (art / enabled first), else a texture region of the object's own name."""
        obj = piece.get("object") if isinstance(piece, dict) else piece
        if not obj:
            return None
        objects, textures = self.objects(), self.textures()
        o = objects.get(obj)
        cands = []
        if o:
            regs = o["regions"]
            for st in ([state] if state else []) + ["art", "enabled", "unchecked", "normal"] + list(regs):
                if st in regs and regs[st] not in cands:
                    cands.append(regs[st])
        for page, region in cands:
            t = textures.get(page)
            if t and region in t["regions"]:
                return page, t["regions"][region], t["path"]
        for page, t in textures.items():                     # an object named as its region, with no UI object
            if obj in t["regions"]:
                return page, t["regions"][obj], t["path"]
        return None

    # ---- writing (the lines meant only) ----
    def _set_leaf(self, node, value):
        raw = self.lines[node.start]
        body = raw.rstrip("\r\n")
        end = raw[len(body):]
        m = re.match(r"^(\s*<%s>)(.*?)(</%s>\s*)$" % (re.escape(node.tag), re.escape(node.tag)), body)
        if not m:
            raise LntError("line %d is not a <%s> line" % (node.start + 1, node.tag))
        self.lines[node.start] = m.group(1) + str(value) + m.group(3) + end

    def _indent_of(self, i):
        raw = self.lines[i]
        return raw[:len(raw) - len(raw.lstrip())]

    def _eol(self):
        return "\r\n" if self.lines and self.lines[0].endswith("\r\n") else "\n"

    def set_param(self, page, name, key, value):
        """A piece's parameter (x, y, width, height, menu_id, tool_tip_id...) set; a missing one is added at the end
        of its <Parameters>, indented as the line before it."""
        x = self.piece(page, name)
        if x is None:
            raise LntError("no piece %s on page %s" % (name, page))
        params = x["node"].find("Parameters")
        if params is None:
            raise LntError("piece %s has no <Parameters>" % name)
        leaf = params.find(key)
        if leaf is not None:
            self._set_leaf(leaf, value)
        else:
            ind = self._indent_of(params.end - 1) if params.end - 1 > params.start else \
                self._indent_of(params.start) + "  "
            at = params.end
            if key in PARAMS:                                    # x, y, width, height together, in that order
                after = [params.find(k) for k in PARAMS[:PARAMS.index(key)] if params.find(k) is not None]
                if after:
                    at = max(n.end for n in after) + 1
                    ind = self._indent_of(at - 1)
            self.lines.insert(at, "%s<%s>%s</%s>%s" % (ind, key, value, key, self._eol()))
        self.parse()

    def move(self, page, name, x=None, y=None, width=None, height=None):
        for key, v in zip(PARAMS, (x, y, width, height)):
            if v is not None:
                self.set_param(page, name, key, int(round(v)))

    def copy_piece(self, page, name, new_name, dx=0, dy=0, to_page=None):
        """A copy of a piece under a new name, right after it (or at the end of to_page), moved by dx, dy -> its
        name. The game finds many pieces by their name (CFP_symbol48_N...), so a slot = the next number."""
        x = self.piece(page, name)
        if x is None:
            raise LntError("no piece %s on page %s" % (name, page))
        if self.piece(to_page or page, new_name) is not None:
            raise LntError("page %s has a piece %s already" % (to_page or page, new_name))
        n = x["node"]
        block = self.lines[n.start:n.end + 1]
        head = block[0]
        block[0] = re.sub(r"(<UI piece>)\s*%s" % re.escape(name), lambda m: m.group(1) + new_name, head, count=1)
        if to_page and to_page != page:
            tp = self.page_node(to_page)
            if tp is None:
                raise LntError("no page %s" % to_page)
            at = tp.end
        else:
            at = n.end + 1
        self.lines[at:at] = block
        self.parse()
        new = self.piece(to_page or page, new_name)
        if dx or dy:
            self.move(to_page or page, new_name,
                      x=(new["x"] or 0) + dx if dx else None, y=(new["y"] or 0) + dy if dy else None)
        return new_name

    def remove_piece(self, page, name):
        x = self.piece(page, name)
        if x is None:
            raise LntError("no piece %s on page %s" % (name, page))
        n = x["node"]
        del self.lines[n.start:n.end + 1]
        self.parse()

    def rename_piece(self, page, name, new_name):
        x = self.piece(page, name)
        if x is None:
            raise LntError("no piece %s on page %s" % (name, page))
        i = x["node"].start
        self.lines[i] = re.sub(r"(<UI piece>)\s*%s" % re.escape(name), lambda m: m.group(1) + new_name,
                               self.lines[i], count=1)
        self.parse()

    def set_text(self, page, name, key):
        """The text key a piece shows (its <UI text> line)."""
        x = self.piece(page, name)
        t = x["node"].find("Parameters").find("UI text") if x else None
        if t is None:
            raise LntError("piece %s has no text" % name)
        raw = self.lines[t.start]
        self.lines[t.start] = re.sub(r"(<UI text>)[^\r\n]*", lambda m: m.group(1) + key, raw, count=1)
        self.parse()


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def piece_info(n):
    params = n.find("Parameters") or Node("Parameters", "", n.start)
    text = params.find("UI text")
    return {"name": n.value, "identifier": n.get("identifier", ""),
            "x": _int(params.get("x")), "y": _int(params.get("y")),
            "width": _int(params.get("width")), "height": _int(params.get("height")),
            "menu_id": params.get("menu_id"), "text": text.value if text is not None else None,
            "font": text.get("font_id") if text is not None else None,
            "align": text.get("align") if text is not None else None,
            "tooltip": params.get("tool_tip_id"), "locked": params.get("locked"),
            "object": n.get("object_id"), "node": n}


def find(mod):
    """The menu layout file the game reads for this mod (its own data/menu first, then the game's), or None."""
    for root in (mod.roots() if hasattr(mod, "roots") else [mod.data]):
        folder = os.path.join(root, "menu")
        if not os.path.isdir(folder):
            continue
        names = {n.lower(): n for n in os.listdir(folder)}
        for want in FILES:
            if want.lower() in names:
                return os.path.join(folder, names[want.lower()])
    return None


def menu_texts(mod):
    """{KEY: text} of data/text/menu_english.txt (the words the pieces show)."""
    path = mod.text_file("menu_english.txt") if hasattr(mod, "text_file") else None
    if not path or not os.path.isfile(path):
        return {}
    with open(path, "rb") as fh:
        data = fh.read()
    for enc in ("utf-16", "utf-8-sig", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*\{([^}]+)\}\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


__all__ = ["Lnt", "LntError", "Node", "find", "menu_texts", "piece_info", "FILES", "PARAMS"]
