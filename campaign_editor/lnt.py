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
# the states a button's UI object draws (the vanilla files of both games): the game's name -> plain words
STATES = {"enabled": "normal", "highlighted": "mouse over", "selected": "pressed", "checked": "ticked", "art": "picture"}

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
        self._cache = {}                     # textures / objects / pieces read from the tree, made again on a parse
        self.problems = []                   # the file's slips the game passes over (an open tag never closed ...)
        self.root = Node("", "", -1)
        stack = [self.root]
        comment = False
        for i, raw in enumerate(self.lines):
            s = raw.strip()
            # a modder's <!-- comment --> (one line or several) and <?...?> / <!...> lines are no pieces
            if comment:
                comment = "-->" not in s
                continue
            if s.startswith("<!--"):
                comment = "-->" not in s[4:]
                continue
            if not s or s.startswith(("<?", "<!")):
                continue
            m = _LEAF.match(s)
            if m:
                stack[-1].children.append(Node(m.group(1), m.group(2).strip(), i, leaf=True))
                continue
            m = _CLOSE.match(s)
            if m:
                # the game reads a mod's slips (report #349: an <identifier> never closed before </UI piece>): an
                # open tag left open is a one-line leaf, a close with nothing of its name open is passed over -
                # both said in problems (Check mod files), never a stop
                if not any(n.tag == m.group(1) for n in stack[1:]):
                    self.problems.append("line %d: </%s> closes nothing open%s - passed over" % (
                        i + 1, m.group(1), "" if len(stack) == 1 else " (open: <%s>)" % stack[-1].tag))
                    continue
                while stack[-1].tag != m.group(1):
                    self._unclosed(stack)
                stack[-1].end = i
                stack.pop()
                continue
            m = _OPEN.match(s)
            if m:
                n = Node(m.group(1), m.group(2).strip(), i)
                stack[-1].children.append(n)
                stack.append(n)
        while len(stack) > 1:
            self._unclosed(stack)
        self.root.end = len(self.lines)

    def _unclosed(self, stack):
        """The open block on top never closed: read as a one-line leaf, what was read under it goes back beside it."""
        n = stack.pop()
        self.problems.append("line %d: <%s> is never closed - read as one line" % (n.start + 1, n.tag))
        parent = stack[-1]
        at = parent.children.index(n) + 1
        parent.children[at:at] = n.children
        n.children, n.leaf, n.end = [], True, n.start

    def textures(self):
        """{page as the objects name it (textures\\FE_texture1.tga): {'path', 'regions': {name: (l, t, r, b)}}} -
        read once a parse (a piece's picture asks for it at every drawing: a drag re-read it hundreds of times)."""
        if "textures" in self._cache:
            return self._cache["textures"]
        out = self._cache["textures"] = {}
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

    def videos(self):
        """{identifier: video file} of the <fmv> blocks - the moving menu backdrop (Rome Dump0000.m1v, Medieval II
        Dump0000.bik); a piece shows it when its object_id is that identifier (fmv_backdrop)."""
        return {f.get("identifier", f.value): f.value for f in self.root.all("fmv")}

    def objects(self):
        """{object name: {'type', 'regions': {state: (page, region)}}}, read once a parse."""
        if "objects" in self._cache:
            return self._cache["objects"]
        out = self._cache["objects"] = {}
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
        if p is None:
            return []
        out = [piece_info(n) for n in p.all("UI piece")]
        for i, x in enumerate(out):
            x["index"] = i
        return out

    def piece(self, page, key):
        """A piece by its place on the page (int - the sure way: a page may hold two pieces of one name, Medieval
        II's main menu does) or by its name (the first of that name)."""
        got = self.pieces(page)
        if isinstance(key, int):
            return got[key] if 0 <= key < len(got) else None
        return next((x for x in got if x["name"] == key), None)

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
        if leaf is not None:                    # the one line changed: no line moves, so no reading again (a drag
            self._set_leaf(leaf, value)         # read the whole file twice a mouse move - it lagged)
            leaf.value = str(value).strip()
            return
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
        """A copy of a piece (name or place) under a new name, right after it (or at the end of to_page), moved by
        dx, dy -> its place on its page. The game finds many pieces by their name (CFP_symbol48_N...), so a slot = the
        next number."""
        x = self.piece(page, name)
        if x is None:
            raise LntError("no piece %s on page %s" % (name, page))
        if self.piece(to_page or page, new_name) is not None:
            raise LntError("page %s has a piece %s already" % (to_page or page, new_name))
        n = x["node"]
        block = self.lines[n.start:n.end + 1]
        head = block[0]
        block[0] = re.sub(r"(<UI piece>)\s*%s" % re.escape(x["name"]), lambda m: m.group(1) + new_name, head,
                          count=1)
        if to_page and to_page != page:
            tp = self.page_node(to_page)
            if tp is None:
                raise LntError("no page %s" % to_page)
            at, where = tp.end, len(self.pieces(to_page))
        else:
            at, where = n.end + 1, x["index"] + 1
        self.lines[at:at] = block
        self.parse()
        new = self.piece(to_page or page, where)
        if dx or dy:
            self.move(to_page or page, where,
                      x=(new["x"] or 0) + dx if dx else None, y=(new["y"] or 0) + dy if dy else None)
        return where

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
        self.lines[i] = re.sub(r"(<UI piece>)\s*%s" % re.escape(x["name"]), lambda m: m.group(1) + new_name,
                               self.lines[i], count=1)
        self.parse()

    # ---- the pictures of an object's states (normal, mouse over, pressed, ticked) ----
    def object_node(self, obj):
        return next((o for o in self.root.all("UI object") if o.value == obj), None)

    def users(self, obj):
        """[(page, piece name)] of every piece drawn with this UI object - a change of its pictures shows on all."""
        return [(p, x["name"]) for p in self.pages() for x in self.pieces(p) if x["object"] == obj]

    def set_state(self, obj, state, page, region):
        """The picture (texture page + region) the object shows in a state; a state it lacks is added as a copy of
        its last <UI region> block, after it."""
        o = self.object_node(obj)
        if o is None:
            raise LntError("no UI object %s" % obj)
        r = next((r for r in o.all("UI region") if r.value == state), None)
        if r is None:
            last = o.all("UI region")
            if not last:
                raise LntError("UI object %s has no picture to copy" % obj)
            block = self.lines[last[-1].start:last[-1].end + 1]
            block[0] = re.sub(r"(<UI region>)[^\r\n]*", lambda m: m.group(1) + state, block[0], count=1)
            self.lines[last[-1].end + 1:last[-1].end + 1] = block
            self.parse()
            o = self.object_node(obj)
            r = next(r for r in o.all("UI region") if r.value == state)
        for tag, value in (("page", page), ("region", region)):
            leaf = r.find(tag)
            if leaf is None:
                raise LntError("UI object %s, state %s has no <%s>" % (obj, state, tag))
            self._set_leaf(leaf, value)
        self.parse()

    def remove_state(self, obj, state):
        """A state's picture taken out (the game then shows the object's first picture); its only one stays."""
        o = self.object_node(obj)
        regs = o.all("UI region") if o is not None else []
        r = next((r for r in regs if r.value == state), None)
        if r is None:
            raise LntError("UI object %s has no state %s" % (obj, state))
        if len(regs) == 1:
            raise LntError("%s is the only picture of UI object %s - it stays" % (state, obj))
        del self.lines[r.start:r.end + 1]
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


    # ---- own pictures (the user, 2026-10-17: a piece's picture replaced by one's own, what it does kept) ----
    def names_taken(self):
        """Every texture region and UI object name, upper-cased - the engine finds both by name in ONE list each,
        without case (menu_resource.cpp find_art_piece; parse.cpp upper-cases every word)."""
        out = {o.value.upper() for o in self.root.all("UI object")}
        for t in self.root.all("texture"):
            out.update(r.value.upper() for r in t.all("region"))
        return out

    def free_object_name(self, stem):
        """A UI object / region stem not used yet, 32 letters at most with room for '_highlighted' (the engine keeps
        names in 32 characters)."""
        taken = self.names_taken()
        stem = re.sub(r"[^A-Za-z0-9_]", "_", stem)[:NAME_MAX - 12 - 3] or "own"
        for n in range(1, 1000):
            name = stem if n == 1 else "%s%d" % (stem, n)
            if not any(k.startswith(name.upper()) for k in taken):
                return name
        raise LntError("no free name for %s" % stem)

    def _insert_after(self, tag, block):
        """Lines put after the last block of this tag at the top of the file (else before the layout)."""
        last = self.root.all(tag)
        at = last[-1].end + 1 if last else (self.layout().start if self.layout() is not None else len(self.lines))
        self.lines[at:at] = block
        self.parse()

    def add_texture(self, rel, regions):
        """A <texture> block for a picture under data/menu/ (rel as the game names it, 'ce_ui\\x.tga') with its
        regions {name: (left, top, right, bottom)} - the edges inclusive, as the engine counts them."""
        e = self._eol()
        folder = rel.replace("/", "\\").rsplit("\\", 1)[0] if "\\" in rel.replace("/", "\\") else ""
        block = ["<texture>%s%s" % (rel, e)]
        if folder:
            block.append("  <path>%s</path>%s" % (folder, e))
        for name, box in regions.items():
            block.append("  <region>%s%s" % (name, e))
            for k, v in zip(("left", "top", "right", "bottom"), box):
                block.append("    <%s>%d</%s>%s" % (k, v, k, e))
            block.append("  </region>%s" % e)
        block.append("</texture>%s" % e)
        self._insert_after("texture", block)

    def add_object(self, name, kind, regions):
        """A <UI object> of its type with a picture per state {state: (texture page, region)}."""
        e = self._eol()
        block = ["<UI object>%s%s" % (name, e), "  <type>%s</type>%s" % (kind or "art", e)]
        for state, (page, region) in regions.items():
            block += ["  <UI region>%s%s" % (state, e), "    <page>%s</page>%s" % (page, e),
                      "    <region>%s</region>%s" % (region, e), "  </UI region>%s" % e]
        block.append("</UI object>%s" % e)
        self._insert_after("UI object", block)

    def set_object(self, page, key, obj):
        """The UI object a piece is drawn with (its <object_id>) - only its pictures change, what it does stays
        (menu_layout.cpp parse_piece: the identifier and the parameters make the behaviour)."""
        x = self.piece(page, key)
        if x is None:
            raise LntError("no piece %s on page %s" % (key, page))
        leaf = x["node"].find("object_id")
        if leaf is not None:
            self._set_leaf(leaf, obj)
        else:
            after = x["node"].find("identifier")
            at = (after.end if after is not None else x["node"].start) + 1
            ind = self._indent_of(at - 1) if after is not None else self._indent_of(x["node"].start) + "  "
            self.lines.insert(at, "%s<object_id>%s</object_id>%s" % (ind, obj, self._eol()))
        self.parse()

    def states_of(self, piece):
        """The states a piece's picture has (its UI object's, in its order; 'art' for a picture with no object)."""
        o = self.objects().get(piece.get("object") or "")
        return list(o["regions"]) if o and o["regions"] else ["art"]

    def own_stem(self, page, key):
        """The name an own copy of the piece's UI object takes (<game object>_own[n], free)."""
        x = self.piece(page, key)
        base = self.game_object(x["object"]) or x["object"] or x["name"]
        return self.free_object_name(base + OWN)

    def own_picture(self, page, key, pics, shared=False, texture=None, stem=None):
        """A piece drawn with pictures of one's own, what it does kept: pics {state: (texture page, region)} - a
        region of the game's sheets (the library) or of texture = (rel under data/menu/, {region: box}), a new
        picture file the caller writes (a TGA). The piece gets its OWN copy of its UI object (own_stem) so no other
        piece changes - or, shared, its UI object itself is pointed at them (every piece drawn with it changes). A
        piece drawn with an own picture before: that one is taken out once nothing shows it any more.
        stem: the own object's name the caller named the new regions after (own_stem). Returns (the object used, the
        picture file no longer used or None)."""
        x = self.piece(page, key)
        if x is None:
            raise LntError("no piece %s on page %s" % (key, page))
        stem = stem or self.own_stem(page, key)          # named before the new regions take its letters
        was = x["object"]
        base = self.game_object(was) or was or x["name"]
        o = self.objects().get(was or "") or self.objects().get(base)
        if texture is not None:
            self.add_texture(*texture)
        if shared and self.objects().get(base) is not None:
            for st, (pg, rg) in pics.items():
                self.set_state(base, st, pg, rg)
            if was != base:
                self.set_object(page, key, base)
            return base, self._tidy(was) if was != base else None
        self.add_object(stem, o["type"] if o else "art", pics)
        self.set_object(page, key, stem)
        return stem, self._tidy(was)

    def game_object(self, obj):
        """The UI object an own copy stands for ('x_own2' -> 'x'), or None when obj is not an own copy."""
        m = re.match(r"^(.+?)%s\d*$" % OWN, obj or "", re.I)
        return m.group(1) if m else None

    def back_to_game(self, page, key):
        """The opposite of own_picture: the piece drawn with the game's object again; the own object and its picture
        taken out once nothing else is drawn with them. Returns the picture file no longer used, or None."""
        x = self.piece(page, key)
        own = x and x["object"]
        back = self.game_object(own)
        if back is None:
            raise LntError("%s has no picture of its own" % (x["name"] if x else key))
        self.set_object(page, key, back)
        return self._tidy(own)

    def _tidy(self, own):
        """An own UI object no piece is drawn with any more taken out, then an own picture (data/menu/ce_ui/) no
        object or piece names any more - never the game's. Returns that picture's name, or None."""
        if self.game_object(own) is None or self.users(own):
            return None
        node = self.object_node(own)
        if node is not None:
            del self.lines[node.start:node.end + 1]
            self.parse()
        used = {rg.upper() for o in self.objects().values() for _, rg in o["regions"].values() if rg}
        used |= {x["object"].upper() for pg in self.pages() for x in self.pieces(pg) if x["object"]}
        for t in self.root.all("texture"):
            names = {r.value.upper() for r in t.all("region")}
            own_file = t.value.replace("/", "\\").lower().startswith(OWN_FOLDER + "\\")
            if own_file and names and not names & used:
                del self.lines[t.start:t.end + 1]
                self.parse()
                return t.value
        return None

    def missing_regions(self):
        """[(object, state, region)] of the UI objects pieces are drawn with whose picture names a region no texture
        has - the engine stops there (menu_layout.cpp: 'failed to find art piece'); names compared without case."""
        have = set()
        for t in self.root.all("texture"):
            have.update(r.value.upper() for r in t.all("region"))
        have.update(v.upper() for v in self.videos())          # the moving backdrop: a video, not a region
        used = {x["object"] for pg in self.pages() for x in self.pieces(pg) if x["object"]}
        return [(name, st, rg) for name, o in self.objects().items() if name in used and not name.startswith(SELF_DRAWN)
                for st, (_, rg) in o["regions"].items() if rg and rg.upper() not in have]

    def page_area(self, page):
        """Pixels the page's pictures take in the engine's one sheet a page (each region rounded up to 8 pixels, the
        engine's step; the backdrop page drawn under it counted too)."""
        regions = {}
        for t in self.textures().values():
            for name, box in t["regions"].items():
                regions[name.upper()] = box
        names = set()
        for pg in {page, "background"} & set(self.pages()):
            for x in self.pieces(pg):
                o = self.objects().get(x["object"] or "")
                if o:
                    names.update(rg.upper() for _, rg in o["regions"].values() if rg)
                elif x["object"]:
                    names.add(x["object"].upper())

        def up(v):
            return (v + 7) // 8 * 8
        return sum(up(b[2] - b[0] + 1) * up(b[3] - b[1] + 1) for n, b in regions.items() if n in names)


NAME_MAX = 32                                         # the engine's names: char[32 + 1] (ui_menu_resource.h)
SHEETS = {"mtw2.lnt": (4096, 2048)}                   # the engine's one sheet a page: Medieval II, else Rome's


def sheet_size(path):
    """(w, h) of the sheet the engine packs a page's pictures into (menu_handler.cpp: Medieval II 4096 x 2048, Rome
    2048 x 2048)."""
    return SHEETS.get(os.path.basename(path or "").lower(), (2048, 2048))
OWN = "_own"                                          # an own copy of a UI object: <game object>_own[n]
OWN_FOLDER = "ce_ui"                                  # own pictures: data/menu/ce_ui/<object>.tga


def own_picture_file(states_pictures, size):
    """The TGA bytes of an own picture: each state's picture (a Pillow image) fitted into size, stacked top-down."""
    import io
    from PIL import Image
    w, h = size
    sheet = Image.new("RGBA", (w, h * len(states_pictures)), (0, 0, 0, 0))
    for i, im in enumerate(states_pictures):
        sheet.paste(im.convert("RGBA").resize((w, h), Image.LANCZOS), (0, i * h))
    out = io.BytesIO()
    sheet.save(out, format="TGA", rle=False, orientation=-1)     # the engine reads TGA only, bottom-up as the game's
    return out.getvalue()


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


# pieces the game draws itself (no picture of their own) - never a problem
SELF_DRAWN = ("empty_", "fmv_backdrop")
# pages the games make in their code, not in the file (their own buttons lead there): Rome / BI / Alexander,
# Medieval II
ENGINE_PAGES = {"CB_custom_army", "Historical_battle_details", "PC_choose_faction"}


def _loose(lnt):
    """(menu_ids that name no page, objects with no picture) of a layout - what the game's own file already has
    (Rome's CB_custom_army, Medieval II's PC_choose_faction...) is no problem in a mod's copy."""
    pages = set(lnt.pages())
    ids, objs = set(), set()
    for page in lnt.pages():
        for x in lnt.pieces(page):
            if x["menu_id"] and x["menu_id"] not in pages:
                ids.add(x["menu_id"])
            if x["object"] and not x["object"].startswith(SELF_DRAWN) and lnt.art(x) is None:
                objs.add(x["object"])
    return ids, objs


def problems(mod):
    """[plain words] wrong in the mod's menu layout file (Check mod files): a button leading to a page the file does
    not have, a piece whose picture names no region, (Rome) a picture file the game cannot find. What the game's own
    file has the same way is left out."""
    path = find(mod)
    if not path:
        return []
    name = os.path.basename(path)
    try:
        lnt = Lnt.load(path)
    except (OSError, LntError) as e:
        return ["menu %s cannot be read: %s - the game's menus may not open" % (name, e)]
    known_ids, known_objs, known_missing = set(ENGINE_PAGES), set(), set()
    try:
        from .campaignrules import game_data
        gd = game_data(mod)
        own = os.path.join(gd, "menu", name) if gd else None
        if own and os.path.isfile(own) and os.path.normcase(os.path.abspath(own)) != \
                os.path.normcase(os.path.abspath(path)):
            game = Lnt.load(own)
            ids, known_objs = _loose(game)
            known_ids |= ids
            known_missing = set(game.missing_regions())
    except (OSError, LntError, ValueError):
        pass
    out = ["menu %s, %s (the game reads past it; the editor too)" % (name, slip) for slip in lnt.problems[:10]]
    pages = set(lnt.pages())
    said = set()
    for page in lnt.pages():
        for x in lnt.pieces(page):
            mid = x["menu_id"]
            if mid and mid not in pages and mid not in known_ids and (page, mid) not in said:
                said.add((page, mid))
                out.append("menu %s, page %s: the button %s leads to the page '%s', which neither the file nor the "
                           "game's own menus have - pressing it may go nowhere (try it in the game)"
                           % (name, page, x["name"], mid))
            obj = x["object"]
            if obj and not obj.startswith(SELF_DRAWN) and obj not in known_objs and lnt.art(x) is None \
                    and obj not in said:
                said.add(obj)
                out.append("menu %s, page %s: the piece %s shows '%s', a picture no texture region of the file "
                           "has - it shows nothing" % (name, page, x["name"], obj))
    for obj, state, region in [m for m in lnt.missing_regions() if m not in known_missing]:
        out.append("menu %s: the picture '%s' (%s) is drawn from the region '%s', which no texture of the file has - "
                   "the game stops when it opens that menu" % (name, obj, STATES.get(state, state), region))
    sw, sh = sheet_size(path)
    for page in lnt.pages():
        if lnt.page_area(page) > sw * sh:
            out.append("menu %s, page %s: its pictures take more than the %d x %d sheet the game packs a page into - "
                       "some of them will not show (smaller pictures help)" % (name, page, sw, sh))
    if name.lower() == "rome.lnt":                 # Medieval II's menu pictures lie in its packs: not looked for
        for page_name in lnt.textures():
            if not texture_file(mod, path, page_name):
                out.append("menu %s: its picture file %s is not found in the mod or the game - the menus that use "
                           "it show nothing there" % (name, page_name))
    return out


def menu_texts(mod):
    """{KEY (upper): text} the pieces show - menu_english.txt as the game reads it (strtables.strings, the one
    reader of string tables; Medieval II's .strings.bin when its .txt holds no {KEY} lines)."""
    from .strtables import read_strings_bin, strings
    out = strings(mod, "menu_english.txt")
    if out or not hasattr(mod, "text_dirs"):
        return out
    from .moddata import _ci
    for folder in mod.text_dirs():
        p = _ci(folder, "menu_english.txt.strings.bin")
        if p:
            with open(p, "rb") as fh:
                return {k.upper(): v for k, v in read_strings_bin(fh.read()).items()}
    return {}


def _data_file(mod, rel):
    from .moddata import ci_path
    for root in (mod.roots() if hasattr(mod, "roots") else [mod.data]):
        p = ci_path(root, rel.replace("\\", "/"))
        if p and os.path.isfile(p):
            return p
    return None


def font_db(mod):
    """{name: (font file, size)} of data/descr_font_db.txt - the engines' (REX / M2EX) TrueType fonts for the menus'
    font names (tnr, verdana_sml...): 'font <name> <file> <size> [kerned]'."""
    p = _data_file(mod, "descr_font_db.txt")
    out = {}
    if not p:
        return out
    with open(p, "rb") as fh:
        for line in fh.read().decode("latin-1").splitlines():
            t = line.split(";")[0].split()
            if len(t) >= 4 and t[0] == "font":
                try:
                    out[t[1]] = (t[2], int(float(t[3])))
                except ValueError:
                    continue
    return out


def font_source(mod, lnt, font_id):
    """Where the letters of a font name come from, as the game takes them: ('ttf', path, size) from
    descr_font_db.txt (the engines draw the menus with TrueType), else ('cuf', path) - the layout file's own <font>
    (Medieval II: fonts\\font_18.cuf...), else the .cuf of the nearest size (Rome's layout names a fonts\\arial.CAF
    that is not there). None without any font file."""
    try:
        from .limits import engine_of
        engine = engine_of(mod)
    except Exception:
        engine = None
    db = font_db(mod) if engine else {}              # the original exes draw the menus from the .cuf fonts
    if font_id in db:
        p = _data_file(mod, "fonts/" + db[font_id][0])
        if p:
            return "ttf", p, db[font_id][1]
    fonts = lnt.fonts() if lnt is not None else {}
    f = fonts.get(font_id) or {}
    if f.get("file", "").lower().endswith(".cuf"):
        p = _data_file(mod, f["file"])
        if p:
            return "cuf", p
    try:
        want = int(f.get("height") or 14)
    except ValueError:
        want = 14
    best = None
    for n in (10, 14, 18):
        p = _data_file(mod, "fonts/font_%d.cuf" % n)
        if p and (best is None or abs(n - want) < abs(best[0] - want)):
            best = (n, p)
    return ("cuf", best[1]) if best else None


def free_name(lnt, page, name):
    """name with its number one up (CFP_symbol48_7 -> CFP_symbol48_8, a name without one -> name_2), free on the
    page - the game finds numbered pieces by their names, so a copy takes the next number."""
    taken = {x["name"] for x in lnt.pieces(page)}
    m = re.match(r"^(.*?)(\d+)$", name)
    stem, n = (m.group(1), int(m.group(2)) + 1) if m else (name + "_", 2)
    while "%s%d" % (stem, n) in taken:
        n += 1
    return "%s%d" % (stem, n)


RE_SLOT = re.compile(r"^(.*symbol48_)(\d+)$", re.I)


def slot_rows(lnt):
    """{(page, stem): [piece, ...] in number order} - the numbered faction slots of each page (CFP_symbol48_N on the
    campaign's faction select, symbol48_N on custom battle's, customize_symbol48_N...)."""
    out = {}
    for page in lnt.pages():
        for x in lnt.pieces(page):
            m = RE_SLOT.match(x["name"] or "")
            if m:
                out.setdefault((page, m.group(1)), []).append((int(m.group(2)), x))
    return {k: [x for _, x in sorted(v, key=lambda t: t[0])] for k, v in out.items()}


def _grid(slots):
    """(x0, y0, dx, dy, per row) of a slot grid from the slots there are (rows by their y, a few pixels apart)."""
    xs = [(x["x"] or 0, x["y"] or 0) for x in slots]
    first_row = [p for p in xs if abs(p[1] - xs[0][1]) <= 8]
    per = max(1, len(first_row))
    steps = [b[0] - a[0] for a, b in zip(first_row, first_row[1:])]
    dx = sorted(steps)[len(steps) // 2] if steps else (slots[0]["width"] or 53)
    if len(xs) > per:
        dy = xs[per][1] - xs[0][1]
    else:
        dy = (slots[0]["height"] or slots[0]["width"] or 53)
    return xs[0][0], xs[0][1], dx, dy, per


# the campaign's faction-select pages (Rome / BI / Alexander and Medieval II)
CAMPAIGN_PICK = ("ImpCam_choose_faction", "PC_choose_faction", "PC_choose_faction_M2")


def slots_short(lnt, pickable):
    """[(page, slots)] of the campaign's faction-select pages with fewer CFP_symbol48_N slots than pickable factions."""
    out = []
    for (page, stem), rows in slot_rows(lnt).items():
        if page in CAMPAIGN_PICK and stem.lower() == "cfp_symbol48_" and len(rows) < pickable:
            out.append((page, len(rows)))
    return out


def add_slots(lnt, page, stem, total):
    """The slots of stem on page made up to total, each a copy of the last one under the next number, placed on its
    grid continued (the same step, as many a row) - more factions to pick on the faction-select screen (the game
    asks for the piece by its name). The number of slots added."""
    rows = slot_rows(lnt).get((page, stem))
    if not rows:
        raise LntError("page %s has no %sN pieces" % (page, stem))
    x0, y0, dx, dy, per = _grid(rows)
    have = len(rows)
    cols = [x["x"] or 0 for x in rows[:per]]                 # the first row's own columns
    last_row = (have - 1) // per
    row_y = rows[last_row * per]["y"] or 0                    # rows go on from the last one there is
    for k in range(have, total):
        last = slot_rows(lnt)[(page, stem)][-1]
        col = k % per
        want_x = cols[col] if col < len(cols) else x0 + col * dx
        want_y = row_y + (k // per - last_row) * dy
        lnt.copy_piece(page, last["index"], "%s%d" % (stem, k + 1),
                       dx=want_x - (last["x"] or 0), dy=want_y - (last["y"] or 0))
    return max(0, total - have)


def keep_up(plan):
    """Every write that changes a campaign's descr_strat: the faction-select screen gets a slot for every playable
    (and unlockable) faction - the game shows a faction only in a CFP_symbol48_N piece the menu layout has (21 in
    REX's Rome.lnt), so slots are added on the grid continued (add_slots) in the layout the game reads, written with
    the plan (backed up, Restore) - as max_factions follows the factions (limits.keep_up). Never stops a write."""
    try:
        from .strat import Strat
        want = 0
        for path, f in plan.files.items():
            if os.path.basename(path).lower() == "descr_strat.txt" and plan.touched(path):
                st = Strat(f)
                want = max(want, sum(len(x["items"]) for x in (st.playable, st.unlockable) if x))
        if not want:
            return 0
        path = find(plan.mod)
        if not path:
            return 0
        data = plan.binaries.get(path)
        if data is None:
            with open(path, "rb") as fh:
                data = fh.read()
        lnt = Lnt(data, path)
        added = 0
        for (page, stem), rows in slot_rows(lnt).items():
            if page in CAMPAIGN_PICK and stem.lower() == "cfp_symbol48_" and len(rows) < want:
                added += add_slots(lnt, page, stem, want)
        if added:
            plan.binary(path, lnt.dump())
            plan.note(None, "%s: %d faction-select slot(s) added - %d playable faction(s), each needs its own slot "
                            "on the faction-select screen" % (os.path.basename(path), added, want))
        return added
    except Exception:
        return 0                                    # never stops a write


def texture_file(mod, lnt_path, page, folder=""):
    """The picture file of a texture page under data/menu/ - Rome names it with its folder ('textures\\FE_texture1.tga'),
    Medieval II alone ('M2_Border.tga') with the folder in the texture's <path> - the mod's own first, then the game's;
    a .dds / .tga.dds beside a missing .tga too. None when not there (Medieval II keeps them in its packs until
    unpacked)."""
    from .moddata import ci_path
    page = page.replace("\\", "/")
    rel = "menu/" + (page if "/" in page or not folder else folder.replace("\\", "/").strip("/") + "/" + page)
    roots = list(mod.roots()) if hasattr(mod, "roots") else [mod.data]
    if lnt_path:
        here = os.path.dirname(os.path.dirname(os.path.abspath(lnt_path)))      # the data folder of the .lnt
        if here not in roots:
            roots.insert(0, here)
    for root in roots:
        for cand in (rel, rel + ".dds", os.path.splitext(rel)[0] + ".dds", "menu/" + page.split("/")[-1]):
            p = ci_path(root, cand)
            if p and os.path.isfile(p):
                return p
    return None


def plan_write(plan, path, lnt):
    """The changed layout into a Plan (the mod's own copy of a game file), with a note of what changed."""
    with open(path, "rb") as fh:
        old = fh.read()
    new = lnt.dump()
    if new == old:
        return False
    plan.binary(path, new)
    plan.note(None, "%s: the menus' layout changed (%d line(s) differ)" % (
        os.path.basename(path), _diff_count(old.decode("latin-1"), new.decode("latin-1"))))
    return True


def _diff_count(a, b):
    import difflib
    return sum(1 for op in difflib.ndiff(a.splitlines(), b.splitlines()) if op[:1] in "+-")


__all__ = ["Lnt", "LntError", "Node", "find", "own_picture_file", "OWN", "OWN_FOLDER", "NAME_MAX", "menu_texts", "piece_info", "font_db", "font_source", "free_name", "texture_file", "plan_write", "FILES", "PARAMS"]
