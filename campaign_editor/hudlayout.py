"""The classic campaign HUD - the strategy map's bottom panel - put together as the game draws it, both games
(Wholesome Queen's campaign UI editor showed the wish; the user, 2026-10-21: 'yes, do it'). The places are the
engines' own (the M2EX / REX engine source, strat_v2_pieces.cpp / ui_buttons.cpp / pc_display.cpp - read only, the
numbers written here as facts; editor-notes hud_facts.md has every source line): everything is laid out on a fixed
1024 x 768 canvas and the whole canvas is stretched to the screen (x and y apart, no anchoring); the HUD's bottom is
at 768, its top 768 - the LEFT panel's height (587 with the game's own); the MIDDLE panel stands on the bottom.

pieces(mod) -> the pieces with their sheet, sprite and box; compose(mod, ...) -> the picture (Pillow)."""

import os

from . import symbols as SY

CANVAS = (1024, 768)

# (piece, sheet, sprite, x, y, w, h) on 1024 x 768 with the game's own panels (HUD top 587); a box of None is the
# sprite's own size; 'ring' faces are centred in their ring (Rome's round buttons)
ROME = [
    ("radar zoom in", "shared2", "RADAR_PLUS_BUTTON_IMAGE", 3, 746, 21, 21),
    ("radar zoom out", "shared2", "RADAR_MINUS_BUTTON_IMAGE", 27, 746, 21, 21),
    ("radar column", "strat3", "HUD_COLUMN_OVERLAY", 245, 602, 11, 14),
    ("build button", "strat3", "BUILD_BUTTON_IMAGE", 774, 608, 76, 76),
    ("build ring", "strat3", "BUTTON_OUTER_RING_LRG", 769, 603, 86, 86),
    ("recruit button", "strat3", "TRAIN_BUTTON_IMAGE", 774, 690, 76, 76),
    ("recruit ring", "strat3", "BUTTON_OUTER_RING_LRG", 769, 685, 86, 86),
    ("previous", "shared2", "CONTROL_DEC", 859, 627, 23, 32),
    ("next", "shared2", "CONTROL_INC", 991, 627, 23, 32),
    ("faction logo", "strat3", "FACTION_LOGO_*", 904, 712, 52, 52),
    ("faction ring", "strat3", "BUTTON_OUTER_RING_MED", 900, 709, 60, 60),
    ("end turn", "strat3", "END_TURN_BUTTON_IMAGE", 965, 712, 52, 53),
    ("end turn ring", "strat3", "BUTTON_OUTER_RING_MED", 961, 709, 60, 60),
    ("money icon", "strat3", "CONSTRUCTION_COST_ICON", 865, 662, 19, 20),
    ("season", "strat3", "SEASON_ICON_SUMMER", 980, 662, 32, 32),
]
ROME_PANELS = ("strat3", "STRAT_HUD_LEFT", "STRAT_HUD_MIDDLE", "STRAT_HUD_RIGHT")
ROME_RADAR = (0, 602, 256, 165)
ROME_CARDS = (273, 636, 478, 128)
ROME_TABS = ("strat3", "HUD_TEXT_TAB_LEFT", "HUD_TEXT_TAB_MID", "HUD_TEXT_TAB_RIGHT", 596, 25)
ROME_TEXTS = [("name", 884, 627, "Brutus"), ("money", 888, 666, "5000"), ("date", 888, 680, "270 BC")]

MEDIEVAL2 = [
    ("tab: units", "strategy", "HUD_TAB_LEFT_SELECTED", 281, 587, 115, 62),
    ("tab: buildings", "strategy", "HUD_TAB_MID", 396, 587, 116, 58),
    ("tab: agents", "strategy", "HUD_TAB_MID", 512, 587, 116, 58),
    ("tab: passengers", "strategy", "HUD_TAB_RIGHT", 628, 587, 115, 58),
    ("radar zoom in", "shared", "RADAR_PLUS_BUTTON_IMAGE", 20, 600, 39, 40),
    ("radar zoom out", "shared", "RADAR_MINUS_BUTTON_IMAGE", 55, 600, 39, 40),
    ("build button", "strategy", "BUILD_BUTTON_IMAGE", 773, 684, 81, 82),
    ("build ring", "strategy", "BUTTON_OUTER_RING_LRG", 773, 684, 81, 85),
    ("recruit button", "strategy", "TRAIN_BUTTON_IMAGE", 865, 684, 81, 85),
    ("recruit ring", "strategy", "BUTTON_OUTER_RING_LRG", 865, 684, 81, 85),
    ("faction", "strategy", "FACTION_LOGO_*", 734, 588, 68, 76),
    ("end turn", "strategy", "END_TURN_BUTTON_IMAGE", 960, 588, 62, 68),
    ("missions", "strategy", "MISSION_BUTTON", 234, 588, 65, 58),
    ("finance", "strategy", "FINANCE_BUTTON_IMAGE", 948, 669, 68, 68),
    ("previous", "shared", "CONTROL_DEC", 794, 623, 25, 32),
    ("next", "shared", "CONTROL_INC", 936, 623, 25, 32),
    ("season", "strategy", "SEASON_ICON_SUMMER", 100, 600, 32, 32),
]
M2_PANELS = ("strategy", "STRAT_HUD_LEFT", "STRAT_HUD_MIDDLE", "STRAT_HUD_RIGHT")
M2_RADAR = (0, 637, 250, 125)
M2_CARDS = (270, 641, 478, 128)
M2_TEXTS = [("name", 821, 623, "Edward"), ("money", 955, 747, "10000"), ("date", 136, 609, "1080")]
GOLD = (255, 245, 139)
HUD_TOP = 587               # with the game's own LEFT panel (181 high); a taller / shorter one moves everything


def _sheets(mod):
    return {s["name"].lower(): s for s in SY.all_sheets(mod)}


def find(sheets, sheet, sprite):
    """(page, (x, y, w, h)) of a sprite in the sheet (a name ending in * takes the first that begins so), or None."""
    sh = sheets.get(sheet)
    if not sh:
        return None
    for page, boxes in sh["pages"]:
        for name, box in boxes:
            if name == sprite or (sprite.endswith("*") and name.startswith(sprite[:-1])):
                return page, box
    return None


def pieces(mod):
    """[{'piece', 'sheet', 'sprite', 'page', 'art' (its box on the page), 'box' (x, y, w, h on 1024 x 768), 'kind'
    ('sprite' / 'radar' / 'cards')}] in the order the game draws them; pieces whose sprite the mod lacks are left
    out (said by missing())."""
    from .limits import game_kind
    rome = game_kind(mod) == "rome"
    sheets = _sheets(mod)
    panels = ROME_PANELS if rome else M2_PANELS
    out = []
    got = [find(sheets, panels[0], n) for n in panels[1:]]
    left = got[0][1] if got[0] else (0, 0, 281, 181)
    top = CANVAS[1] - left[3]
    dy = top - HUD_TOP
    x = 0
    for k, (name, g) in enumerate(zip(("left panel", "middle panel", "right panel"), got)):
        if g:
            w, h = g[1][2], g[1][3]
            y = top if name != "middle panel" else top + left[3] - h
            out.append({"piece": name, "sheet": panels[0], "sprite": panels[1 + k], "page": g[0],
                        "art": g[1], "box": (x, y, w, h), "kind": "sprite"})
            x += w
    rx, ry, rw, rh = ROME_RADAR if rome else M2_RADAR
    out.append({"piece": "radar (the campaign's small map)", "sheet": None, "sprite": None, "page": None,
                "art": None, "box": (rx, ry + dy, rw, rh), "kind": "radar"})
    cx, cy, cw, ch = ROME_CARDS if rome else M2_CARDS
    out.append({"piece": "unit cards", "sheet": None, "sprite": None, "page": None, "art": None,
                "box": (cx, cy + dy, cw, ch), "kind": "cards"})
    if rome:
        out += _rome_tabs(sheets, dy)
    for piece, sheet, sprite, px, py, w, h in (ROME if rome else MEDIEVAL2):
        g = find(sheets, sheet, sprite)
        if g:
            name = sprite if not sprite.endswith("*") else next(
                n for p, b in sheets[sheet]["pages"] for n, bb in b if n.startswith(sprite[:-1]))
            out.append({"piece": piece, "sheet": sheet, "sprite": name, "page": g[0], "art": g[1],
                        "box": (px, py + dy, w, h), "kind": "sprite"})
    return out


# the tabs' words and the word each is as wide as (strat_v2_pieces.cpp 127-143: the wider of Army / Fleet, of Town /
# City; Agents; the passengers' tab is as wide as 'Army' and shows no word until a ship's army is picked - the
# tester's game at 1600 x 900, 2026-10-22: 'Army / Town / Agents / (empty)')
ROME_TAB_WORDS = (("Army", "Fleet"), ("Town", "City"), ("Agents", "Agents"), ("", "Army"))
# Verdana small's letters, pixels on the 1024 canvas (narrow and wide ones; the rest 6) - the four tabs measured in the
# game: about 333 wide together
TAB_LETTERS = {**dict.fromkeys("iljI", 3), **dict.fromkeys("frt", 4), **dict.fromkeys("s", 5),
               **dict.fromkeys("ACDGHNOQRUw", 7), **dict.fromkeys("mMW", 10), "T": 6}


def tab_text_width(word):
    return sum(TAB_LETTERS.get(c, 6) for c in word)


def _rome_tabs(sheets, dy, words=ROME_TAB_WORDS):
    """Rome's four tabs: each LEFT + MID (as wide as its word + 20) + RIGHT, the group centred on 1024, 8 pixels
    over each other (strat_v2_pieces.cpp 1549-1609); the first one picked (drawn last, on top). words: (shown,
    the words its width comes from)."""
    sheet, l, m, r, y, h = ROME_TABS
    gl, gm, gr = (find(sheets, sheet, n) for n in (l, m, r))
    if not (gl and gm and gr):
        return []
    widths = [gl[1][2] + max(tab_text_width(x) for x in w) + 20 + gr[1][2] for w in words]
    words = [w[0] for w in words]
    total = sum(widths) - 8 * (len(widths) - 1)
    x = (CANVAS[0] - total) // 2
    tabs = []
    for word, w in zip(words, widths):
        tabs.append({"piece": "tab: %s" % (word.lower() or "passengers"), "sheet": sheet, "sprite": m, "page": gm[0], "art": gm[1],
                     "box": (x, y + dy, w, h), "kind": "tab", "parts": (gl, gm, gr), "word": word})
        x += w - 8
    return tabs[1:][::-1] + tabs[:1]


def missing(mod):
    """The HUD's sprites the mod's sheets do not have (a mod's own HUD named otherwise, or a sheet not found)."""
    from .limits import game_kind
    rome = game_kind(mod) == "rome"
    sheets = _sheets(mod)
    return [(sheet, sprite) for _, sheet, sprite, *_ in (ROME if rome else MEDIEVAL2)
            if not find(sheets, sheet, sprite)]


def radar_picture(mod, campaign):
    """The campaign's radar map picture (radar_map2.tga, else radar_map1.tga) or None."""
    try:
        folder = mod.campaign_dir(campaign)
    except Exception:
        return None
    for n in ("radar_map2.tga", "radar_map1.tga"):
        for d in (folder,) + tuple(getattr(mod, "dirs", lambda r: [])("world/maps/campaign/" + campaign)):
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


def compose(mod, campaign=None, page_picture=None, boxes=None, screen=None):
    """The HUD as the game draws it on 1024 x 768 (the campaign map left dark): page_picture(page) -> the page's
    picture (Pillow RGBA - the Sprite sheets tab's changed one when there is one; the files' else); boxes:
    {(sheet, sprite): (x, y, w, h)} art boxes changed there; screen (w, h): the canvas stretched as the game does."""
    from PIL import Image, ImageDraw
    from .recolour import read_picture
    cache = {}

    def page_pic(page):
        if page not in cache:
            im = page_picture(page) if page_picture else None
            if im is None:
                got = SY.page_cultures(mod, page)
                im = read_picture(got[0][1]).convert("RGBA") if got else None
            cache[page] = im
        return cache[page]
    out = Image.new("RGBA", CANVAS, (34, 52, 40, 255))
    draw = ImageDraw.Draw(out)
    for p in pieces(mod):
        x, y, w, h = p["box"]
        if p["kind"] == "radar":
            path = radar_picture(mod, campaign) if campaign else None
            if path:
                try:
                    out.paste(read_picture(path).convert("RGBA").resize((w, h)), (x, y))
                    continue
                except Exception:
                    pass
            draw.rectangle((x, y, x + w - 1, y + h - 1), fill=(60, 80, 60, 255))
            continue
        if p["kind"] == "cards":
            for k in range(10):
                cx = x + k * 48
                if cx + 46 <= x + w:
                    draw.rectangle((cx, y, cx + 45, y + 61), outline=(200, 190, 150, 255))
            continue
        if p["kind"] == "tab":
            gl, gm, gr = p["parts"]
            pic = page_pic(gm[0])
            if pic is None:
                continue
            for g, part_name, gx, gw in ((gl, ROME_TABS[1], x, gl[1][2]),
                                         (gm, ROME_TABS[2], x + gl[1][2], w - gl[1][2] - gr[1][2]),
                                         (gr, ROME_TABS[3], x + w - gr[1][2], gr[1][2])):
                ax, ay, aw, ah = (boxes or {}).get((p["sheet"], part_name), g[1])
                part = page_pic(g[0]).crop((ax, ay, ax + aw, ay + ah)).resize((max(1, gw), h))
                out.alpha_composite(part, (gx, y))
            draw.text((x + 20, y + 6), p["word"], fill=(0, 0, 0, 255))
            continue
        pic = page_pic(p["page"])
        if pic is None:
            continue
        ax, ay, aw, ah = (boxes or {}).get((p["sheet"], p["sprite"]), p["art"])
        part = pic.crop((ax, ay, ax + aw, ay + ah))
        if part.size != (w, h):
            part = part.resize((max(1, w), max(1, h)))
        out.alpha_composite(part, (x, y))
    from .limits import game_kind
    rome = game_kind(mod) == "rome"
    dy = pieces_top(mod) - HUD_TOP
    if not rome:                                        # the tabs' words: centred, 18 below the tab's top
        for p in pieces(mod):
            if p["piece"].startswith("tab: "):
                x, y, w, h = p["box"]
                word = p["piece"][5:].capitalize()
                draw.text((x + (w - 6 * len(word)) // 2, y + 18), word,
                          fill=(0, 0, 0, 255) if p["sprite"].endswith("_SELECTED") else GOLD + (255,))
    for _, tx, ty, word in (ROME_TEXTS if rome else M2_TEXTS):
        draw.text((tx, ty + dy), word, fill=(0, 0, 0, 255) if rome else GOLD + (255,))
    if screen and tuple(screen) != CANVAS:
        out = out.resize(tuple(screen))
    return out


def pieces_top(mod):
    left = next((p for p in pieces(mod) if p["piece"] == "left panel"), None)
    return left["box"][1] if left else HUD_TOP


def piece_at(mod, x, y, items=None):
    """The topmost piece under (x, y) on 1024 x 768, or None."""
    for p in reversed(items if items is not None else pieces(mod)):
        px, py, w, h = p["box"]
        if px <= x < px + w and py <= y < py + h:
            return p
    return None


def pieces_at(mod, x, y, items=None):
    """Every piece under (x, y), the topmost first (a ring lies over its button's picture: both can be picked)."""
    out = []
    for p in reversed(items if items is not None else pieces(mod)):
        px, py, w, h = p["box"]
        if px <= x < px + w and py <= y < py + h:
            out.append(p)
    return out


def sharing(p, items):
    """The other pieces that show the same sprite of the same sheet as p (Rome's medium ring is the faction button's
    and the end-turn button's both - a new picture for it changes both, the tester, 2026-10-22)."""
    if not p.get("sprite"):
        return []
    return [q for q in items if q is not p and q.get("sprite") == p["sprite"] and q.get("sheet") == p.get("sheet")]


__all__ = ["pieces", "compose", "missing", "piece_at", "pieces_at", "sharing", "find", "CANVAS"]
