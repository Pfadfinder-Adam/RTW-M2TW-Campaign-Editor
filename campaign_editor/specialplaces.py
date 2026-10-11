"""Special places on the campaign map (the user, 2026-10-09 / 2026-10-11: a 3D model of one's own on any tile, its
own window like a wonder's, a bonus for whoever holds it) - Rome with REX and Medieval II with M2EX, by the engine's
script (the test mod's s_special proved it in the game: 'имба, с первого раза').

How it works in the game (one script for all the places of a mod, <game>/script/modules/ce_places_<mod>.nut):
- each place's model (any .cas of the campaign map: a watchtower, a fort, a wonder, a mine, one's own) is registered
  with game.models.add(path, number, false) and drawn on its tile with game.models.drawAt(number, x, y, scale) on
  every load (drawAt draws with no fog of war - the games' maps are open anyway);
- the mouse resting on it: its name in a tooltip; a DOUBLE click on its tile opens its window, any click closes it;
- the window stands at the screen's left like the game's wonder / settlement scrolls: the game's own scroll (Medieval
  II's painted frame, Rome's rolled scroll - the SCROLL_* pieces of the interface sheets, put together here), the
  place's picture across its whole width (never cut), its name, the bonus lines, the text, and at the foot who holds
  it now (the tile's owner). The scroll and the picture are made into one .tga here (data/ui/ce_places/<id>.tga);
  the script writes the words on it (the engine's own font, so they wrap as the game draws them);
- money a turn (optional) goes to the faction holding the tile, at the start of its turn;
- the script runs only for its own mod (game.modName()) - the script folder is the game's, shared by every mod.
The editor keeps the places in the script itself (its '// @places ' line, JSON) - one file, read back to edit."""

import json
import math
import os
import re

SCRIPT = "ce_places_%s.nut"
FOLDER = "ui/ce_places"                     # the windows' pictures (data-relative)
MARK = "// @places "
WIDTH = 440                                 # the window's width in the game, px
FIRST_ID = 9300                             # the models' numbers (game.models.add) - out of the test mod's way


class Place:
    """One special place: where (tile x, y of a campaign), its model and size, its words, its picture, its money."""
    FIELDS = ("id", "campaign", "x", "y", "model", "size", "title", "bonus", "text", "picture", "money")

    def __init__(self, **kw):
        self.id = kw.get("id") or 0
        self.campaign = kw.get("campaign") or ""
        self.x, self.y = int(kw.get("x", 0)), int(kw.get("y", 0))
        self.model = kw.get("model") or ""               # data-relative .cas ('data/models_strat/...')
        self.size = float(kw.get("size") or 1.0)
        self.title = kw.get("title") or ""
        self.bonus = kw.get("bonus") or ""              # one or two lines of what it gives
        self.text = kw.get("text") or ""
        self.picture = kw.get("picture") or ""          # data-relative .tga of its window (made here), or ""
        self.money = int(kw.get("money") or 0)

    def as_dict(self):
        return {k: getattr(self, k) for k in self.FIELDS}

    def __repr__(self):
        return "Place(%s at %d, %d)" % (self.title, self.x, self.y)


def mod_name(mod):
    """The mod's folder name as the engine's game.modName() gives it (the folder holding data/)."""
    return os.path.basename(os.path.dirname(os.path.abspath(mod.data)))


def script_file(mod):
    return SCRIPT % re.sub(r"[^A-Za-z0-9_]+", "_", mod_name(mod)).lower()


def script_path(mod):
    """Where the places' script goes: the game's script/modules (addons._script_target - what REX / M2EX load)."""
    import types
    from .addons import _script_target
    return _script_target(mod, types.SimpleNamespace(file=script_file(mod)))


def read(mod):
    """The places this mod's script holds now ([] when it has none)."""
    path = script_path(mod)
    if not path or not os.path.isfile(path):
        return []
    with open(path, "rb") as fh:
        return parse(fh.read().decode("utf-8", "replace"))


def parse(text):
    for line in text.splitlines():
        if line.startswith(MARK):
            try:
                return [Place(**d) for d in json.loads(line[len(MARK):])]
            except (ValueError, TypeError):
                return []
    return []


def problems(place):
    """What must be put right before writing (a name and a text are a must - the user, 2026-10-09: 'only a
    description is a must'; a model to draw)."""
    out = []
    if not place.title.strip():
        out.append("it needs a name")
    if not place.text.strip():
        out.append("it needs a text (what the place is)")
    if not place.model:
        out.append("pick a model for it")
    return out


# ---------------------------------------------------------------------------
# the window: the game's own scroll, the picture, room for the words
# ---------------------------------------------------------------------------
PIECES = ("TOP_LEFT", "TOP_CENTER", "TOP_RIGHT", "MID_LEFT", "MID", "MID_RIGHT", "BOTTOM_LEFT", "BOTTOM_CENTER",
          "BOTTOM_RIGHT")
# (left / right, top, bottom) inside the scroll's border: Medieval II's painted frame, Rome's rolls and meander
MARGINS = {"medieval2": (42, 42, 42), "rome": (52, 34, 40)}
TITLE, LINE, GAP = 34, 22, 12                # the name's line, a text line, the gap between parts (px)


def pieces(mod, culture=None):
    """{piece: RGBA picture} of the game's scroll (SCROLL_TOP_LEFT ...) from its interface sheets, or None."""
    from .cardmaker import game_sprite
    got = {k: game_sprite(mod, "SCROLL_" + k, culture) for k in PIECES}
    return got if all(got.values()) else None


def scroll(parts, w, h):
    """The scroll w x h put together from its nine pieces: corners as they are, the edges and the middle repeated
    (the last copy cut at the edge)."""
    from PIL import Image
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tl, tc, tr = parts["TOP_LEFT"], parts["TOP_CENTER"], parts["TOP_RIGHT"]
    ml, mm, mr = parts["MID_LEFT"], parts["MID"], parts["MID_RIGHT"]
    bl, bc, br = parts["BOTTOM_LEFT"], parts["BOTTOM_CENTER"], parts["BOTTOM_RIGHT"]

    def tile(img, x0, y0, x1, y1):
        for y in range(y0, y1, img.height):
            for x in range(x0, x1, img.width):
                piece = img.crop((0, 0, min(img.width, x1 - x), min(img.height, y1 - y)))
                out.alpha_composite(piece, (x, y))
    top, bottom = max(tl.height, tr.height), max(bl.height, br.height)
    tile(mm, ml.width, top, w - mr.width, h - bottom)
    tile(ml, 0, top, ml.width, h - bottom)
    tile(mr, w - mr.width, top, w, h - bottom)
    tile(tc, tl.width, 0, w - tr.width, tc.height)
    tile(bc, bl.width, h - bc.height, w - br.width, h)
    for img, at in ((tl, (0, 0)), (tr, (w - tr.width, 0)), (bl, (0, h - bl.height)), (br, (w - br.width, h - br.height))):
        out.alpha_composite(img, at)
    return out


def lines_of(text, width, size=17):
    """About how many lines the text takes at that width (the game's font: about half a size a letter) - the
    scroll's height is made from it; the script wraps the words as the game draws them."""
    per = max(8, int(width / (size * 0.5)))
    return sum(max(1, math.ceil(len(part) / per)) for part in (text or "").split("\n")) if text else 0


def layout(game, place, picture_size=None, width=WIDTH):
    """Where each part of the window goes: {'w', 'h', 'mx', 'pic': (x, y, w, h) or None, 'title', 'bonus', 'text',
    'held', 'inner'} - px from the window's top left."""
    mx, top, bottom = MARGINS["medieval2" if game == "medieval2" else "rome"]
    inner = width - 2 * mx
    y = top
    pic = None
    if picture_size:
        pw, ph = picture_size
        h = max(1, round(inner * ph / max(1, pw)))       # across the whole width, never cut
        pic = (mx, y, inner, h)
        y += h + GAP
    out = {"w": width, "mx": mx, "inner": inner, "pic": pic, "title": y}
    y += TITLE
    out["bonus"] = y
    nb = lines_of(place.bonus, inner)
    y += nb * LINE + (GAP if nb else 0)
    out["text"] = y
    y += lines_of(place.text, inner) * LINE + GAP
    out["rule"] = y                                       # a thin line, then who holds it
    out["held"] = y + GAP
    out["h"] = y + GAP + LINE + bottom
    return out


def window_picture(mod, place, game, culture=None, picture=None):
    """(the window's picture - the game's scroll with the place's picture across it and a thin line above 'Held by'
    - and its layout). picture: an RGBA picture of the place, or None."""
    from PIL import Image, ImageDraw
    lay = layout(game, place, picture.size if picture is not None else None)
    parts = pieces(mod, culture)
    if parts is not None:
        img = scroll(parts, lay["w"], lay["h"])
    else:                                                 # no interface sheets found: a plain parchment
        img = Image.new("RGBA", (lay["w"], lay["h"]), (226, 208, 164, 250))
        ImageDraw.Draw(img).rectangle((0, 0, lay["w"] - 1, lay["h"] - 1), outline=(70, 45, 20, 255), width=3)
    if picture is not None and lay["pic"]:
        x, y, w, h = lay["pic"]
        img.alpha_composite(picture.convert("RGBA").resize((w, h), Image.LANCZOS), (x, y))
    d = ImageDraw.Draw(img)
    d.line((lay["mx"] + 20, lay["rule"], lay["w"] - lay["mx"] - 20, lay["rule"]), fill=(110, 75, 35, 200), width=2)
    return img, lay


# ---------------------------------------------------------------------------
# the script
# ---------------------------------------------------------------------------
def _sq(text):
    """A Squirrel string literal."""
    return '"%s"' % str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "\\n")


def script(mod, places, layouts):
    """The engine script of all the places (layouts {place id: layout} of their windows)."""
    models, rows = {}, []
    for p in places:
        mid = models.setdefault(p.model, FIRST_ID + len(models))
        lay = layouts[p.id]
        rows.append("    { id = %d, model = %d, x = %d, y = %d, size = %s, title = %s, bonus = %s, text = %s, "
                    "money = %d, bg = %s, w = %d, h = %d, mx = %d, inner = %d, title_y = %d, bonus_y = %d, "
                    "text_y = %d, held_y = %d }" % (
                        p.id, mid, p.x, p.y, repr(float(p.size)), _sq(p.title), _sq(p.bonus), _sq(p.text), p.money,
                        _sq("data/" + FOLDER + "/%d.tga" % p.id), lay["w"], lay["h"], lay["mx"], lay["inner"],
                        lay["title"], lay["bonus"], lay["text"], lay["held"]))
    model_rows = ["    [%d] = %s" % (mid, _sq(path)) for path, mid in models.items()]
    data = json.dumps([p.as_dict() for p in places], ensure_ascii=False)
    return NUT % {"mark": MARK + data, "mod": _sq(mod_name(mod)), "models": ",\n".join(model_rows),
                  "places": ",\n".join(rows)}


NUT = r"""// @title Special places of the mod
// @summary Made by RTW & M2TW Campaign Editor (Map editor > right click > Special place here...): each place's 3D
// @summary model drawn on its tile, its window (a double click on it) and its money a turn for the faction holding it.
// @summary Runs only for its own mod. Change it in the editor - it is written again from its places.
%(mark)s
local PREFIX = "[CE_PLACES] "
local MOD = %(mod)s
local MODELS = {
%(models)s
}
local PLACES = [
%(places)s
]
local state = { drawn = false, open = null, img = {}, armed = false }
local said = {}

local function log(message) {
    println(PREFIX + message)
}

local function once(key, message) {
    if (!(key in said)) {
        said[key] <- true
        log(message)
    }
}

local function get(o, field) {
    if (o == null) {
        return null
    }
    try {
        return o[field]
    } catch (err) {
    }
    return null
}

local function ours() {                                // the game's script folder is every mod's: ours only
    try {
        return ::game.modName().tolower() == MOD.tolower()
    } catch (err) {
        once("modname", "game.modName() could not be read (" + err + ") - drawn anyway")
    }
    return true
}

local function draw_models(...) {
    if (!ours()) {
        return
    }
    local models = get(::game, "models")
    if (models == null) {
        once("nomodels", "no game.models in this engine - the places cannot be drawn")
        return
    }
    foreach (id, path in MODELS) {
        try {
            models.add(path, id, false)
        } catch (err) {
            log("models.add " + path + " failed: " + err)
        }
    }
    foreach (p in PLACES) {
        try {
            if (!models.drawAt(p.model, p.x, p.y, p.size)) {
                log(p.title + ": drawAt answered false (tile " + p.x + "," + p.y + ")")
            }
        } catch (err) {
            log(p.title + ": drawAt failed: " + err)
        }
    }
    state.drawn = true
    log(PLACES.len() + " place(s) drawn")
}

local function owner(p) {
    try {
        local id = get(::stratMap.tile(p.x, p.y), "factionId")
        if (id != null && id >= 0) {
            return ::game.faction(id)
        }
    } catch (err) {
        once("owner", "a tile's owner could not be read: " + err)
    }
    return null
}

local function money_of(f) {
    local m = get(f, "money")
    return m != null ? m : get(f, "treasury")
}

local function on_turn(e) {
    if (!ours()) {
        return
    }
    local f = get(e, "faction")
    if (f == null) {
        return
    }
    foreach (p in PLACES) {
        if (p.money == 0) {
            continue
        }
        local o = owner(p)
        if (o == null || get(o, "id") != get(f, "id")) {
            continue
        }
        local before = money_of(f)
        try {
            f.money = before + p.money
        } catch (err) {
        }
        if (money_of(f) == before) {
            try {
                ::game.runConsoleCommand("add_money", get(f, "name") + " " + p.money)
            } catch (err) {
                log("add_money failed: " + err)
            }
        }
        log(p.title + ": " + get(f, "name") + " holds it - money " + before + " -> " + money_of(f))
    }
}

// ---- the words on the window ----
local function ex_font() {
    try {
        local root = getroottable()
        if ("EX" in root && "fonts" in root.EX && "body" in root.EX.fonts) {
            return root.EX.fonts.body
        }
    } catch (err) {
    }
    return null
}

local function text_at(ui, x, y, words, size, r, g, b) {
    local face = ex_font()
    if (face != null) {
        ui.drawText(x, y, words, face, r, g, b, 255, size)
    } else {
        ui.drawText(x, y, words, "tnr_med", r, g, b, 255, 0)
    }
}

local function text_width(words, size) {
    local face = ex_font()
    try {
        return ::UI.textSize(words, face != null ? face : "tnr_med", size)[0]
    } catch (err) {
    }
    return (words.len() * size * 0.55).tointeger()
}

local function words_of(text) {
    local out = []
    local rest = text
    local i = rest.indexof(" ")
    while (i != null) {
        if (i > 0) {
            out.append(rest.slice(0, i))
        }
        rest = rest.slice(i + 1)
        i = rest.indexof(" ")
    }
    if (rest.len() > 0) {
        out.append(rest)
    }
    return out
}

local function paragraphs(text) {                       // the text's lines (no string library needed)
    local out = []
    local rest = text
    local i = rest.indexof("\n")
    while (i != null) {
        out.append(rest.slice(0, i))
        rest = rest.slice(i + 1)
        i = rest.indexof("\n")
    }
    out.append(rest)
    return out
}

local function wrapped(text, width, size) {             // each paragraph cut into lines no wider than width
    local out = []
    foreach (para in paragraphs(text)) {
        local line = ""
        foreach (word in words_of(para)) {
            local more = line.len() > 0 ? line + " " + word : word
            if (line.len() > 0 && text_width(more, size) > width) {
                out.append(line)
                line = word
            } else {
                line = more
            }
        }
        out.append(line)
    }
    return out
}

local function near(a, b) {
    return a - b <= 1 && b - a <= 1
}

local function place_under_mouse() {
    try {
        if (::UI.cursorOverGameUi()) {
            return null
        }
        local t = ::stratMap.hoveredTile()
        if (t == null) {
            return null
        }
        foreach (p in PLACES) {
            if (near(get(t, "x"), p.x) && near(get(t, "y"), p.y)) {
                return p
            }
        }
    } catch (err) {
        once("hover", "the tile under the mouse could not be read: " + err)
    }
    return null
}

local function draw_tip() {
    local p = place_under_mouse()
    if (p == null) {
        return
    }
    try {
        local m = ::UI.mouse.pos()
        ::UI.tooltipAt(m[0] - 8, m[1] - 8, 16, 16)
        ::UI.tooltip(0, p.title + " (double click: more)")
    } catch (err) {
        once("tip", "tooltip failed: " + err)
    }
}

local function picture(p) {
    if (!(p.id in state.img)) {
        state.img[p.id] <- null
        try {
            local t = ::UI.loadTexture(p.bg)
            if (t != null && get(t, "img") != 0) {
                state.img[p.id] = t.img
            }
        } catch (err) {
            log(p.title + ": its window's picture " + p.bg + " could not be loaded: " + err)
        }
    }
    return state.img[p.id]
}

local function draw_window() {
    if (state.open == null) {
        draw_tip()
        return
    }
    local ui = ::UI
    local p = state.open
    local sh = 1080
    try {
        sh = ui.screenSize()[1]
    } catch (err) {
    }
    local x = 8
    local y = (sh * 0.11).tointeger()                  // under the game's top bar, at the left like its scrolls
    local img = picture(p)
    if (img != null) {
        ui.image(img, p.w, p.h, x, y)
    } else {
        ui.drawRoundedRect(x, y, p.w, p.h, 8, 226, 208, 164, 250)
    }
    local left = x + p.mx
    local tw = text_width(p.title, 24)
    text_at(ui, x + (p.w - tw) / 2, y + p.title_y, p.title, 24, 70, 30, 10)
    local line = y + p.bonus_y
    if (p.bonus.len() > 0) {
        foreach (part in wrapped(p.bonus, p.inner, 17)) {
            text_at(ui, left, line, part, 17, 25, 85, 20)
            line += 22
        }
    }
    line = y + p.text_y
    foreach (part in wrapped(p.text, p.inner, 17)) {
        text_at(ui, left, line, part, 17, 40, 25, 10)
        line += 22
    }
    local o = owner(p)
    local held = "Held by: " + (o != null ? get(o, "name") : "nobody")
    text_at(ui, x + (p.w - text_width(held, 17)) / 2, y + p.held_y, held, 17, 60, 30, 10)
}

local function on_frame() {
    local ui = ::UI
    if (state.open != null) {
        if (ui.mouse.clicked(ui.mouse.left) || ui.mouse.clicked(ui.mouse.right)) {
            state.open = null
        }
        return
    }
    local dbl = false
    try {
        dbl = ui.mouse.doubleClicked(ui.mouse.left)
    } catch (err) {
        once("dbl", "mouse.doubleClicked failed: " + err)
    }
    if (dbl) {
        local p = place_under_mouse()
        if (p != null) {
            state.open = p
            log(p.title + ": its window is open")
        }
    }
}

local function arm(...) {
    if (state.armed || !ours()) {
        return
    }
    state.armed = true
    local ui = ::UI
    try {
        ui.onFrame(function() {
            try {
                on_frame()
            } catch (err) {
                once("frame", "the click check failed: " + err)
            }
        })
        local canvas = ui.canvas("##ce_places_canvas", 0, 0, 4, 4)
        foreach (cap in ["autoScaleCanvas", "autoScale", "autoScaleFonts"]) {
            try {
                ui.setWidgetStyle(canvas, ui.Cap[cap], 0)
            } catch (err) {
            }
        }
        ui.onDraw(canvas, function() {
            try {
                draw_window()
            } catch (err) {
                once("draw", "the window could not be drawn: " + err)
            }
        })
        log("armed")
    } catch (err) {
        log("the window could not be armed: " + err)
    }
}

local function listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        log("events.on(" + name + ") failed: " + err)
    }
}

listen("FactionTurnStart", function(e) { if (!state.drawn) { draw_models() } arm(); on_turn(e) })
listen("GameReloaded", function(...) { state.drawn = false; draw_models(); arm() })
log("module loaded")
"""


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------
def model_choices(mod):
    """The campaign map's models a place can take: every .cas under models_strat (the mod's and the game's) -
    [data-relative path], resources, residences, wonders, mines ... sorted."""
    out = set()
    for folder in mod.dirs("models_strat"):
        for root, _, files in os.walk(folder):
            for n in files:
                if n.lower().endswith(".cas"):
                    rel = os.path.relpath(os.path.join(root, n), os.path.dirname(folder)).replace("\\", "/")
                    out.add("data/" + rel)
    return sorted(out, key=str.lower)


def plan(mod, places, culture_of=None, pictures=None, own_models=None, into=None, mark=""):
    """A Plan writing the places: their windows' pictures (data/ui/ce_places/<id>.tga), each model into the mod at
    its own path (the engine reads models from the mod folder - a game's file gets an identical copy there; one's
    own .cas from own_models {data-relative path: file}), and the script with every place (none left: the script
    goes, the pictures too). culture_of(place): the culture whose scroll it wears; pictures {id: RGBA picture or a
    file path}. into: a plan to add them to (the test mod's step); mark: a last line for the script (the test
    mod's own mark - Scripts in the game knows it)."""
    from .packs import game_kind
    from .plan import Plan
    pl = into if into is not None else Plan(mod, "places", "special places", {})
    game = "medieval2" if game_kind(mod) == "medieval2" else "rome"
    pictures, own_models = pictures or {}, own_models or {}
    target = script_path(mod)
    layouts = {}
    used = set()
    given = {id(p): pictures.get(p.id) for p in places}       # by the id it came with (a new place's is 0)
    for p in places:
        p.id = p.id or (max([q.id for q in places] + [0]) + 1)
        used.add(p.id)
    import io
    from PIL import Image
    for p in places:
        img = None
        pic = given.get(id(p))
        if pic is not None:                        # a new picture: kept in the mod (the window is made from it)
            img = Image.open(pic).convert("RGBA") if isinstance(pic, str) else pic.convert("RGBA")
            p.picture = "data/%s/%d_picture.tga" % (FOLDER, p.id)
            out = io.BytesIO()
            img.save(out, format="TGA", rle=False, orientation=-1)
            pl.binary(os.path.join(mod.data, *FOLDER.split("/"), "%d_picture.tga" % p.id), out.getvalue())
        elif p.picture:
            got = mod.find(p.picture[5:] if p.picture.lower().startswith("data/") else p.picture)
            try:
                img = Image.open(got).convert("RGBA") if got else None
            except OSError:
                img = None
        win, lay = window_picture(mod, p, game, culture_of(p) if culture_of else None, img)
        layouts[p.id] = lay
        out = io.BytesIO()
        win.save(out, format="TGA", rle=False, orientation=-1)
        pl.binary(os.path.join(mod.data, *FOLDER.split("/"), "%d.tga" % p.id), out.getvalue())
        src = own_models.get(p.model)
        rel = p.model[5:] if p.model.lower().startswith("data/") else p.model
        mine = os.path.join(mod.data, *rel.split("/"))
        if src:
            pl.copy(src, mine)
        elif not os.path.isfile(mine):
            got = mod.find(rel)
            if got:
                pl.copy(got, mine)                 # the engine reads models from the mod folder
            else:
                pl.warn(None, "%s: its model %s is in neither the mod nor the game" % (p.title, p.model))
    # the windows of places taken out
    folder = os.path.join(mod.data, *FOLDER.split("/"))
    if os.path.isdir(folder):
        for n in os.listdir(folder):
            m = re.match(r"^(\d+)(?:_picture)?\.tga$", n, re.I)
            if m and int(m.group(1)) not in used:
                pl.delete(os.path.join(folder, n), "its special place was taken out")
    if places:
        pl.binary(target, (script(mod, places, layouts) + (mark + "\n" if mark else "")).encode("utf-8"))
        pl.note(None, "%d special place(s) in %s - drawn by the engine (REX / M2EX) on every load" % (
            len(places), os.path.basename(target)))
    elif os.path.isfile(target):
        pl.deletions.append(target)
        pl.note(None, "%s removed - no special place left" % os.path.basename(target))
    return pl


__all__ = ["Place", "read", "parse", "problems", "plan", "script", "layout", "window_picture", "scroll", "pieces",
           "model_choices", "script_path", "script_file", "mod_name"]
