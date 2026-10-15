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
    known_ids, known_objs = set(ENGINE_PAGES), set()
    try:
        from .campaignrules import game_data
        gd = game_data(mod)
        own = os.path.join(gd, "menu", name) if gd else None
        if own and os.path.isfile(own) and os.path.normcase(os.path.abspath(own)) != \
                os.path.normcase(os.path.abspath(path)):
            ids, known_objs = _loose(Lnt.load(own))
            known_ids |= ids
    except (OSError, LntError, ValueError):
        pass
    out = []
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


__all__ = ["Lnt", "LntError", "Node", "find", "menu_texts", "piece_info", "font_db", "font_source", "free_name", "texture_file", "plan_write", "FILES", "PARAMS"]
