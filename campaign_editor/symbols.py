"""A faction's symbols that live on shared sheets, not in files of their own:

- the **flag symbol** on the campaign map (armies, towns, fleets; Rome and Medieval II alike - the engine's
  standard_display reads descr_standards.txt the same way in both): descr_sm_factions.txt
  `standard_index k` picks slot k of the banner sheets - data/banners/symbols<k//4 + 1>.tga.dds,
  128 x 128 DXT5, four 64 x 64 symbols: k%4 = top left, top right, bottom left, bottom right
  (vanilla RTW: julii 0 = the laurel, brutii 1 = the dagger, scipii 2 = the wolf, senate 3 = the eagle).
  Barbarian Invasion adds symbols9..15; a faction and its shadow may share a slot;
- the **faction logo** on the faction button and in the panels: `logo_index` (52 x 52) and
  `small_logo_index` (32 x 32) name sprites of ui/strat3.sd.xml and ui/shared2.sd.xml. With REX's
  `sprite_format xml` (descr_caps_ex.txt: "v7 .sd.xml with runtime atlas packing, allows you to freely
  add new sprites") a faction gets a page of its own: <page file="faction_logo_<f>.tga"> with one
  sprite, the picture in ui/roman/interface (REX looks in ui/<culture>/interface, then ui/roman/interface).
  The binary .rsd of the original exe cannot take new sprites: there the logo stays shared.

A new faction gets its own slot and logos (the template's pictures copied in), so replacing
them never changes the template's."""

import io
import os
import re
import struct

from .moddata import _ci
from .textio import TextFile, strip_comment, tokens

FLAG, LOGO, SMALL = "symbol:flag", "symbol:logo", "symbol:small_logo"
SHEETS = {LOGO: ("strat3.sd.xml", "logo_index", "FACTION_LOGO_%s", "faction_logo_%s.tga", 52),
          SMALL: ("shared2.sd.xml", "small_logo_index", "SMALL_FACTION_LOGO_%s", "faction_logo_small_%s.tga", 32)}
# Medieval II: the same lines and sprite names on ui/strategy.sd.xml (68 x 76) and ui/shared.sd.xml (32 x 32); M2EX
# reads the xml sheets with 'sprite_format xml' in the mod's own descr_caps_ex.txt ("v7 .sd.xml with runtime atlas
# packing"), vanilla medieval2.exe only the binary ui/*.sd (strings of both exes, 2026-10-01)
SHEETS_M2 = {LOGO: ("strategy.sd.xml", "logo_index", "FACTION_LOGO_%s", "faction_logo_%s.tga", (68, 76)),
             SMALL: ("shared.sd.xml", "small_logo_index", "SMALL_FACTION_LOGO_%s", "faction_logo_small_%s.tga", 32)}


def sheets(mod):
    return SHEETS if rome(mod) else SHEETS_M2


def _box(size):
    return tuple(size) if isinstance(size, (tuple, list)) else (size, size)
LABELS = {FLAG: ("flag symbol on the campaign map",
                 "the flags over the faction's armies, fleets and towns on the campaign map"),
          LOGO: ("faction logo (faction button)",
                 "the faction button at the bottom right of the campaign map, diplomacy and the faction lists"),
          SMALL: ("small faction logo",
                  "the small logo in lists and scrolls (diplomacy, the faction list)")}


# ---------------------------------------------------------------------------
# descr_sm_factions.txt lines
# ---------------------------------------------------------------------------
def _sm(plan_or_mod):
    mod = getattr(plan_or_mod, "mod", plan_or_mod)
    path = mod.file("sm_factions")
    if hasattr(plan_or_mod, "files") and path in plan_or_mod.files:
        return path, plan_or_mod.files[path]
    return path, mod.load(path)


def sm_values(f, key):
    """{faction: (line index, value)} of one key of every faction block."""
    out, cur = {}, None
    for i in range(len(f)):
        t = tokens(strip_comment(f.text(i)))
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1].rstrip(",")
        elif t[:1] == [key] and len(t) > 1 and cur and cur not in out:
            out[cur] = (i, t[1])
    return out


def _set_value(f, i, value):
    text = f.text(i)
    f.set(i, re.sub(r"^(\s*\S+\s+)(\S+)", lambda m: m.group(1) + str(value), text, count=1))


def rome(mod):
    from .limits import game_kind
    return game_kind(mod) == "rome"


def _game_data(mod):
    from .buildings import _game_data as gd
    return gd(mod.data)


def _find(mod, *parts):
    """A file of the mod, else of the game's data (what REX and BI read in its place)."""
    for data in (mod.data, _game_data(mod)):
        if not data:
            continue
        d = data
        for p in parts[:-1]:
            d = _ci(d, p) if d else None
        p = _ci(d, parts[-1]) if d else None
        if p:
            return p
    return None


def _read_image(plan, path):
    from PIL import Image
    data = (plan.binaries.get(path) if plan is not None else None)
    if data is not None:
        return Image.open(io.BytesIO(data)).convert("RGBA")
    return Image.open(path).convert("RGBA")


# ---------------------------------------------------------------------------
# The flag symbol
# ---------------------------------------------------------------------------
DEFAULT_SHEETS = (["banners/symbols%d.tga" % n for n in range(1, 6)],
                  ["banners/symbols%d.tga" % n for n in range(6, 9)])


def _standards(plan_or_mod):
    """(path it was read from or None, TextFile or None, path the plan writes) of descr_standards.txt:
    the plan's copy, the mod's, else the game's (a copy in the mod is written when it changes)."""
    mod = getattr(plan_or_mod, "mod", plan_or_mod)
    plan = plan_or_mod if hasattr(plan_or_mod, "files") else None
    mine = os.path.join(mod.data, "descr_standards.txt")
    if plan is not None:
        for p in (mine, mod.find("descr_standards.txt")):
            if p and p in plan.binaries:
                return p, TextFile.from_bytes(p, plan.binaries[p]), p
    src = _find(mod, "descr_standards.txt")
    if not src:
        return None, None, mine
    return src, TextFile.load(src), (src if os.path.dirname(src) == os.path.normpath(mod.data) else mine)


def _sheet_rel(path):
    """'../amazon/data/banners/symbols1.tga' -> 'banners/symbols1.tga' (the mod:switch form)."""
    path = path.replace("\\", "/")
    low = path.lower()
    at = low.rfind("data/")
    return path[at + 5:] if at >= 0 else path.lstrip("./")


def sheet_lists(plan_or_mod):
    """([faction sheets], [rebel sheets]) as data-relative paths, in descr_standards.txt's order - the
    game takes standard_index k from the (k // 4)th sheet of the faction list followed by the rebel
    list (vanilla RTW: symbols1-5 + 6-8, slave 20 = the first rebel sheet; BI: symbols9-13 + 14-15).
    No file: vanilla RTW's lists."""
    _, f, _ = _standards(plan_or_mod)
    if f is None:
        return list(DEFAULT_SHEETS[0]), list(DEFAULT_SHEETS[1])
    fac, reb, cur = [], [], None
    for line in f.texts():
        t = tokens(strip_comment(line))
        if t[:1] == ["factions"]:
            cur = fac
        elif t[:1] == ["rebels_factions"]:
            cur = reb
        elif t[:1] == ["symbols"] and len(t) > 1 and cur is not None:
            cur.append(_sheet_rel(t[1]))
    if not fac and not reb:
        return list(DEFAULT_SHEETS[0]), list(DEFAULT_SHEETS[1])
    return fac, reb


def slot_box(k, size=128):
    """(x, y, w, h) of slot k inside its sheet: k % 4 = top left, top right, bottom left, bottom right."""
    h = size // 2
    return ((k % 2) * h, ((k // 2) % 2) * h, h, h)


def slot_sheet(plan_or_mod, k, lists=None):
    """The data-relative sheet slot k lies on, or None past the last sheet."""
    fac, reb = lists or sheet_lists(plan_or_mod)
    both = fac + reb
    return both[k // 4] if 0 <= k // 4 < len(both) else None


def sheet_path(mod, rel, plan=None):
    """The sheet's file: the plan's new one, the mod's, else the game's (None when none). rel is the
    descr_standards path ('banners/symbols1.tga'); the picture on disk is its .dds."""
    if not rel:
        return None
    names = [rel + ".dds", rel] if not rel.lower().endswith(".dds") else [rel]
    for name in names:
        mine = os.path.join(mod.data, *name.split("/"))
        if plan is not None and mine in plan.binaries:
            return mine
    for name in names:
        got = _find(mod, *name.split("/"))
        if got:
            return got
    return None


def _target(mod, rel):
    rel = rel if rel.lower().endswith(".dds") else rel + ".dds"
    return os.path.join(mod.data, *rel.split("/"))


def rebel_slots(plan_or_mod, lists=None):
    """Slots the rebels' flags take: descr_cultures.txt rebel_standard_index r = slot r of the rebel sheets."""
    mod = getattr(plan_or_mod, "mod", plan_or_mod)
    fac, _ = lists or sheet_lists(plan_or_mod)
    p = _find(mod, "descr_cultures.txt")
    out = set()
    if p:
        for line in mod.load(p).texts():
            t = tokens(strip_comment(line))
            if t[:1] == ["rebel_standard_index"] and len(t) > 1 and t[1].isdigit():
                out.add(4 * len(fac) + int(t[1]))
    return out


def flag_of(plan_or_mod, faction):
    """{'index', 'rel' (the sheet in descr_standards), 'sheet' (its file or None), 'box', 'shared': [factions]}
    or None."""
    mod = getattr(plan_or_mod, "mod", plan_or_mod)
    _, f = _sm(plan_or_mod)
    vals = sm_values(f, "standard_index")
    if faction not in vals or not vals[faction][1].isdigit():
        return None
    k = int(vals[faction][1])
    rel = slot_sheet(plan_or_mod, k)
    shared = sorted(x for x, (_, v) in vals.items() if v == str(k) and x != faction)
    return {"index": k, "rel": rel,
            "sheet": sheet_path(mod, rel, plan_or_mod if hasattr(plan_or_mod, "files") else None),
            "box": slot_box(k), "shared": shared}


def used_slots(plan_or_mod, lists=None):
    _, f = _sm(plan_or_mod)
    return {int(v) for _, v in sm_values(f, "standard_index").values() if v.isdigit()} | \
        rebel_slots(plan_or_mod, lists)


def free_slot(plan_or_mod):
    """The lowest slot of the faction sheets that no faction and no rebels' flag uses, or None (full:
    vanilla RTW has its 20 faction slots taken)."""
    lists = sheet_lists(plan_or_mod)
    used = used_slots(plan_or_mod, lists)
    return next((k for k in range(4 * len(lists[0])) if k not in used), None)


def _sheet_like(plan, rel):
    """The sheet as a picture and the file whose format / mipmaps to write in."""
    from PIL import Image
    mod = plan.mod
    src = sheet_path(mod, rel, plan)
    fac, reb = sheet_lists(plan)
    like = src or next((sheet_path(mod, r) for r in fac + reb if sheet_path(mod, r)), None)
    sheet = _read_image(plan, src) if src else Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    return sheet, like


def _new_faction_sheet(plan, why):
    """A faction sheet appended to descr_standards.txt's faction list (a new file banners/symbols<N>.tga.dds).
    The slots it now holds that some faction already points at (slave's 20 on vanilla RTW, read from the
    first rebel sheet until now) get the picture they showed, so nothing already there changes.
    Returns the new sheet's first slot."""
    from PIL import Image
    from .factionart import image_dds
    mod = plan.mod
    fac, reb = old = sheet_lists(plan)
    src, f, target = _standards(plan)
    nums = [int(m.group(1)) for r in fac + reb for m in [re.search(r"symbols(\d+)", r, re.I)] if m]
    rel = "banners/symbols%d.tga" % (max(nums) + 1 if nums else 1)
    first = 4 * len(fac)
    sheet = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    _, fsm = _sm(plan)
    shown = {int(v) for _, v in sm_values(fsm, "standard_index").values() if v.isdigit()}
    like = None
    for k in range(first, first + 4):
        if k in shown and slot_sheet(plan, k, old):
            p = sheet_path(mod, slot_sheet(plan, k, old), plan)
            if p:
                old_im = _read_image(plan, p)
                box = slot_box(k, old_im.size[0])
                piece = old_im.crop((box[0], box[1], box[0] + box[2], box[1] + box[3])).resize((64, 64))
                sheet.paste(piece, slot_box(k)[:2])
                like = like or p
    like = like or next((sheet_path(mod, r) for r in fac + reb if sheet_path(mod, r)), None)
    plan.binary(_target(mod, rel), image_dds(sheet, like))
    plan.notes.append((mod.rel(_target(mod, rel)), "a new banner sheet (slots %d-%d) %s" % (first, first + 3, why)))
    # descr_standards.txt: the new sheet after the last faction sheet
    if f is None:
        lines = ["factions"] + ["symbols\t\t\t\t%s" % r for r in fac + [rel]] + \
                ["rebels_factions"] + ["symbols\t\t\t\t%s" % r for r in reb]
        data = ("\r\n".join(lines) + "\r\n").encode("latin-1")
    else:
        texts, at, in_fac = f.texts(), None, False
        for i, line in enumerate(texts):
            t = tokens(strip_comment(line))
            if t[:1] == ["factions"]:
                in_fac, at = True, i
            elif t[:1] == ["rebels_factions"]:
                in_fac = False
            elif in_fac and t[:1] == ["symbols"]:
                at = i
        pattern = texts[at] if at is not None and tokens(strip_comment(texts[at]))[:1] == ["symbols"] else None
        new_line = re.sub(r"(symbols\s+)\S+", lambda m: m.group(1) + rel, pattern, count=1) if pattern \
            else "symbols\t\t\t\t" + rel
        f.raw[at + 1:at + 1] = [f.make(new_line)]
        data = f.dump()
    plan.binary(target, data)
    plan.notes.append((mod.rel(target), "banner sheet %s added to the faction sheets" % rel))
    plan.warn(None, "%s: every banner slot was taken, so a new banner sheet (%s, slots %d-%d) was added to "
                    "descr_standards.txt - check in the game that the flag shows (REX reads it; the original "
                    "game's own sheet count is not known)" % (why.replace("for ", ""), rel, first, first + 3))
    return first


def _paste_flag(plan, k, im, why):
    """Picture im into slot k of its sheet (written to the mod's banners folder, in the sheet's
    own format and mipmaps)."""
    from PIL import Image
    from .factionart import image_dds
    mod = plan.mod
    rel = slot_sheet(plan, k)
    if rel is None:
        raise ValueError("flag slot %d lies past the banner sheets descr_standards.txt lists" % k)
    sheet, like = _sheet_like(plan, rel)
    x, y, w, h = slot_box(k, sheet.size[0])
    im = im.convert("RGBA").resize((w, h), Image.LANCZOS)
    sheet.paste(im, (x, y))
    target = _target(mod, rel)
    plan.binary(target, image_dds(sheet, like))
    plan.notes.append((mod.rel(target), "flag symbol %d (%s) %s" % (k, ("top left", "top right", "bottom left",
                                                                         "bottom right")[k % 4], why)))


def flag_image(plan_or_mod, faction):
    """The faction's flag symbol as a picture, or None."""
    got = flag_of(plan_or_mod, faction)
    if not got or not got["sheet"]:
        return None
    sheet = _read_image(plan_or_mod if hasattr(plan_or_mod, "files") else None, got["sheet"])
    x, y, w, h = slot_box(got["index"], sheet.size[0])
    return sheet.crop((x, y, x + w, y + h))


def own_flag(plan, faction, im=None):
    """Give the faction a slot of its own (when it shares one) and put im there (default: the
    picture it shows now). Returns the slot."""
    got = flag_of(plan, faction)
    if got is None:
        return None
    pic = im if im is not None else flag_image(plan, faction)
    k = got["index"]
    path, f = _sm(plan)
    lists = sheet_lists(plan)
    on_rebels = k in rebel_slots(plan, lists) or k >= 4 * len(lists[0])
    if got["shared"] or on_rebels:
        k = free_slot(plan)
        if k is None:
            k = _new_faction_sheet(plan, "for %s" % faction)
            k = next(x for x in range(k, k + 4) if x not in used_slots(plan))
        f = plan.edit(path)
        i = sm_values(f, "standard_index")[faction][0]
        _set_value(f, i, k)
        plan.note(f, "%s's flag symbol: slot %d of its own (was %d, %s)" % (
            faction, k, got["index"], ("shared with " + ", ".join(got["shared"])) if got["shared"]
            else "on the rebels' banner sheet"))
    if pic is not None:
        _paste_flag(plan, k, pic, "for %s" % faction if im is None else "replaced for %s" % faction)
    return k


# ---------------------------------------------------------------------------
# The faction logos (REX sprite sheets)
# ---------------------------------------------------------------------------
def sprite_mode(mod):
    """'xml' when REX packs the .sd.xml sheets (sprites can be added), else 'sd' (binary .rsd) - from the mod's own
    descr_caps_ex.txt; a mod without one runs on the engine's default, sd (limits.ex_file)."""
    from .limits import ex_file
    p = ex_file(mod, "descr_caps_ex.txt")
    if not p:
        return "sd"
    for line in TextFile.load(p).texts():
        t = tokens(strip_comment(line))
        if t[:1] == ["sprite_format"] and len(t) > 1:
            return t[1].lower()
    return "sd"


RE_PAGE = re.compile(r'<page\s+file="([^"]+)"[^>]*>(.*?)</page>', re.S)
RE_SPRITE = re.compile(r'<sprite\b([^>]*?)/?>')
RE_ATTR = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def sprite_list(body):
    """[{'name', 'box': (x, y, art w, art h), 'shown': (w, h), 'file' (a loose sprite's picture) or None, 'cursor'}]
    of the <sprite .../> tags in body, read as the engines' .sd.xml reader does (the M2EX engine source,
    sd_xml_parser.cpp; Wholesome Queen's campaign UI editor showed the gap): attributes in any order; w / h the size
    shown, tw / th the picture's box on the page when set (0 or none = w / h; M2EX's own --ui-pack writes them for
    hi-res sprites); cursor and hotspot_x / _y kept."""
    out = []
    for m in RE_SPRITE.finditer(body):
        at = dict(RE_ATTR.findall(m.group(1)))
        if not at.get("name"):
            continue
        w, h = _int(at.get("w")), _int(at.get("h"))
        tw, th = _int(at.get("tw")) or w, _int(at.get("th")) or h
        out.append({"name": at["name"], "box": (_int(at.get("x")), _int(at.get("y")), tw, th), "shown": (w, h),
                    "file": at.get("file"), "cursor": _int(at.get("cursor")) != 0,
                    "hotspot": (_int(at.get("hotspot_x")), _int(at.get("hotspot_y")))})
    return out


def loose_sprites(text):
    """The sheet's loose sprites - <sprite name file w h/> outside every <page>: one picture, a page of its own
    (the engine makes it a virtual page the whole picture covers)."""
    return [sp for sp in sprite_list(RE_PAGE.sub("", text)) if sp["file"]]


def _xml_text(plan, path):
    if plan is not None and path in plan.binaries:
        return plan.binaries[path].decode("latin-1")
    with open(path, "rb") as fh:
        return fh.read().decode("latin-1")


def xml_path(mod, sheet, plan=None):
    mine = os.path.join(mod.data, "ui", sheet)
    if plan is not None and mine in plan.binaries:
        return mine
    return _find(mod, "ui", sheet)


def skins(mod):
    """The folders ui/<culture>/interface the pages are looked up in, the fallback (base) first: Rome 'roman';
    Medieval II the culture with the most pages (M2EX: 'default is whichever has the most'), then the others."""
    if rome(mod):
        return ["roman"]
    count = {}
    for base in [mod.data] + ([_game_data(mod)] if _game_data(mod) else []):
        ui = _ci(base, "ui")
        if not ui:
            continue
        for c in os.listdir(ui):
            d = _ci(os.path.join(ui, c), "interface")
            if d and os.path.isdir(d):
                n = sum(1 for f in os.listdir(d) if f.lower().endswith(".tga"))
                count[c.lower()] = max(count.get(c.lower(), 0), n)
    return sorted(count, key=lambda c: -count[c]) or ["southern_european"]


def page_path(mod, page, plan=None):
    for skin in skins(mod):
        mine = os.path.join(mod.data, "ui", skin, "interface", page)
        if plan is not None and mine in plan.binaries:
            return mine
        got = _find(mod, "ui", skin, "interface", page)
        if got:
            return got
    return None


def find_sprite(mod, sheet, name, plan=None):
    """{'xml', 'page', 'page_path', 'box'} of a sprite, or None - from the sheet the game reads: the binary one
    (spritesheet: the plain games, an engine on 'sd') or the .sd.xml text one."""
    sh = binary_sheet(mod, sheet, plan)
    if sh is not None:
        got = sh[1].find(name)
        return got and dict(got, xml=None, page_path=page_path(mod, got["page"], plan))
    xp = xml_path(mod, sheet, plan)
    if not xp:
        return None
    text = _xml_text(plan, xp)
    for m in RE_PAGE.finditer(text):
        for sp in sprite_list(m.group(2)):
            if sp["name"] == name:
                return {"xml": xp, "page": m.group(1), "page_path": page_path(mod, m.group(1), plan),
                        "box": sp["box"], "shown": sp["shown"]}
    for sp in loose_sprites(text):
        if sp["name"] == name:
            return {"xml": xp, "page": sp["file"], "page_path": _find(mod, *sp["file"].replace("\\", "/").split("/"))
                    or page_path(mod, sp["file"], plan), "box": sp["box"], "shown": sp["shown"], "loose": True}
    return None


# the binary sheet the game reads in place of each .sd.xml (RomeTW.exe 'ui/strat3.rsd', medieval2.exe 'ui/strategy.sd')
BINARY = {"strat3.sd.xml": "strat3.rsd", "shared2.sd.xml": "shared2.rsd", "strategy.sd.xml": "strategy.sd",
          "shared.sd.xml": "shared.sd"}


def binary_sheet(mod, sheet, plan=None):
    """(path, spritesheet.Sheet) of the binary sheet the game reads for a .sd.xml one (the mod's, else the game's) -
    None when the game reads the xml ('sprite_format xml') or there is none."""
    from . import spritesheet as SS
    if sprite_mode(mod) == "xml" or sheet not in BINARY:
        return None
    mine = os.path.join(mod.data, "ui", BINARY[sheet])
    if plan is not None and mine in plan.binaries:
        return mine, SS.read(plan.binaries[mine])
    path = _find(mod, "ui", BINARY[sheet])
    if not path:
        return None
    try:
        with open(path, "rb") as fh:
            return path, SS.read(fh.read())
    except (OSError, ValueError, struct.error):
        return None                                  # a sheet we cannot read: left as it is


def logo_of(plan_or_mod, faction, which):
    """{'name', 'sprite' (find_sprite or None), 'own' (a page of its own), 'shared': [factions]}."""
    mod = getattr(plan_or_mod, "mod", plan_or_mod)
    plan = plan_or_mod if hasattr(plan_or_mod, "files") else None
    sheet, key, _, own_page, _ = sheets(mod)[which]
    _, f = _sm(plan_or_mod)
    vals = sm_values(f, key)
    if faction not in vals:
        return None
    name = vals[faction][1]
    sp = find_sprite(mod, sheet, name, plan)
    return {"name": name, "sprite": sp, "own": bool(sp and sp["page"].lower() == own_page % faction),
            "shared": sorted(x for x, (_, v) in vals.items() if v == name and x != faction)}


def logo_image(plan_or_mod, faction, which):
    got = logo_of(plan_or_mod, faction, which)
    sp = got and got["sprite"]
    if not sp or not sp["page_path"]:
        return None
    x, y, w, h = sp["box"]
    return _read_image(plan_or_mod if hasattr(plan_or_mod, "files") else None, sp["page_path"]).crop(
        (x, y, x + w, y + h))


def can_own_logo(mod, which, plan=None):
    """Whether a faction can have a logo of its own: the .sd.xml sheet the engine reads, or the binary sheet the plain
    game reads (a page and a sprite added to it - spritesheet)."""
    sheet = sheets(mod)[which][0]
    if sprite_mode(mod) == "xml":
        return bool(xml_path(mod, sheet, plan))
    return binary_sheet(mod, sheet, plan) is not None


def _page_folders(mod, page):
    """The culture folders (ui/<culture>/interface) a page is read from: every one that has it (the mod's or the
    game's - each culture's interface has its own copy), else the first skin."""
    out = {}
    if page:
        for base in [mod.data] + ([_game_data(mod)] if _game_data(mod) else []):
            ui = _ci(base, "ui")
            if not ui or not os.path.isdir(ui):
                continue
            for c in sorted(os.listdir(ui)):
                d = _ci(os.path.join(ui, c), "interface")
                if d and os.path.isdir(d) and _ci(d, page):
                    out.setdefault(c.lower(), c)
    return list(out.values()) or [skins(mod)[0]]


def own_logo(plan, faction, which, im=None):
    """The faction's logo on a page of its own (made when it has none: a sprite named after it in
    the sheet, the picture in ui/<culture>/interface, its logo line pointed at it); im or the logo it
    shows now drawn there. The engine's .sd.xml sheet, or the plain game's binary one (a page and a sprite added -
    a modder on Discord: 'cannot be replaced' for Barbarian Invasion's Huns). Returns the sprite name, or None when
    the mod cannot take new sprites."""
    from PIL import Image
    from .factionart import image_tga
    from . import spritesheet as SS
    mod = plan.mod
    sheet, key, sprite_name, own_page, size = sheets(mod)[which]
    size = _box(size)
    got = logo_of(plan, faction, which)
    if got is None or not can_own_logo(mod, which, plan):
        return None
    pic = im if im is not None else logo_image(plan, faction, which)
    if pic is None:
        return None
    page = own_page % faction
    binary = binary_sheet(mod, sheet, plan)
    # the binary sheets: the page goes to every culture folder its old page was in (each culture reads its own);
    # the xml ones: the engine falls back to the first skin
    folders = _page_folders(mod, got["sprite"] and got["sprite"]["page"]) if binary else [skins(mod)[0]]
    name = got["name"]
    if not got["own"]:
        name = sprite_name % faction.upper()
        if got["name"] == name:
            # the sprite already carries its name (Medieval II: FACTION_LOGO_ENGLAND; Rome: FACTION_LOGO_HUNS) - it
            # moves to the faction's own page; the factions that borrow it (Normans) first get a page of their own
            # with the old picture
            for other in got["shared"]:
                own_logo(plan, other, which)
            if not binary:
                xp = xml_path(mod, sheet, plan)
                text = re.sub(r'[ \t]*<sprite\b[^>]*\bname="%s"[^>]*/>\r?\n?' % re.escape(name), "", _xml_text(plan, xp),
                              count=1)
                mine = os.path.join(mod.data, "ui", sheet)
                plan.binary(mine, text.encode("latin-1"))
        if not binary:
            xp = xml_path(mod, sheet, plan)
            text = _xml_text(plan, xp)
            if not find_sprite(mod, sheet, name, plan):
                nl = "\r\n" if "\r\n" in text else "\n"
                block = ('  <page file="%s" w="%d" h="%d">%s    <sprite name="%s" x="0" y="0" w="%d" h="%d" alpha="1"/>'
                         '%s  </page>%s') % (page, size[0], size[1], nl, name, size[0], size[1], nl, nl)
                at = text.rfind("</sprite_definitions>")
                text = text[:at] + block + text[at:]
                mine = os.path.join(mod.data, "ui", sheet)
                plan.binary(mine, text.encode("latin-1"))
                plan.notes.append((mod.rel(mine), "sprite %s: a page of its own for %s (%s)" % (name, faction, page)))
        path, f = _sm(plan)
        f = plan.edit(path)
        if got["name"] != name:
            _set_value(f, sm_values(f, key)[faction][0], name)
            plan.note(f, "%s's %s now %s (was %s%s)" % (faction, key, name, got["name"], ", shared with " +
                                                         ", ".join(got["shared"]) if got["shared"] else ""))
    size_now = got["sprite"]["box"][2:] if got["own"] and got["sprite"] else size
    pic = pic.convert("RGBA").resize(tuple(size_now), Image.LANCZOS)
    if binary:
        # the page (its size and click mask) and the sprite on it, in the mod's own copy of the binary sheet
        binary = binary_sheet(mod, sheet, plan)      # read again: the borrowers' own pages may be in it now
        sh = binary[1]
        SS.set_sprite(sh, name, SS.set_page(sh, page, pic), 0, 0, pic.size[0], pic.size[1])
        mine = os.path.join(mod.data, "ui", BINARY[sheet])
        plan.binary(mine, SS.write(sh))
        plan.notes.append((mod.rel(mine), "sprite %s: a page of its own for %s (%s)" % (name, faction, page)))
    for culture in folders:
        target = os.path.join(mod.data, "ui", culture, "interface", page)
        plan.binary(target, image_tga(pic))
        plan.notes.append((mod.rel(target), "%s of %s%s" % (LABELS[which][0], faction,
                                                            " replaced" if im is not None else "")))
    return name


# ---------------------------------------------------------------------------
# For the clone, the Art tab and its writes
# ---------------------------------------------------------------------------
ENGINE = {True: "REX", False: "M2EX"}


CAPS = "descr_caps_ex.txt"
XML_LINE = "sprite_format  xml"


def can_use_xml(mod):
    """Whether the mod's sheets could be switched to xml here: an engine runs it, it reads the binary sheets now and
    a .sd.xml sheet of the logos is there (the mod's own or the game's)."""
    from .limits import engine_of
    return bool(engine_of(mod)) and sprite_mode(mod) != "xml" and \
        any(xml_path(mod, sheets(mod)[w][0]) for w in (LOGO, SMALL))


def use_xml(plan):
    """'sprite_format xml' in the mod's own descr_caps_ex.txt: the engine reads the .sd.xml sheets then, and a faction
    can have logos of its own (a tester: SSHIP's new factions kept other factions' shields - the mod had no
    descr_caps_ex.txt, so M2EX read the binary sheets). A line of its own changed or switched on (a ';' taken off);
    a mod without the file gets the game's copy with every other setting off (gamefix.settings_off - the engine's
    defaults for mods stay), else a short file of that one line."""
    from .gamefix import settings_off
    from .limits import ex_file
    from .newmod import game_of
    from .moddata import _ci as ci
    mod = plan.mod
    have = ex_file(mod, CAPS)
    path = have or os.path.join(mod.data, CAPS)
    if have:
        with open(have, "rb") as fh:
            text = fh.read().decode("latin-1")
    else:
        game = game_of(mod.data)
        gdata = ci(game, "data") if game else None
        src = ci(gdata, CAPS) if gdata and os.path.normcase(os.path.abspath(gdata)) != \
            os.path.normcase(os.path.abspath(mod.data)) else None
        if src:
            with open(src, "rb") as fh:
                text = settings_off(fh.read()).decode("latin-1")
        else:
            text = "; %s - engine options (%s); the ones not named here keep their defaults for mods\r\n" % (
                CAPS, ENGINE[rome(mod)])
    nl = "\r\n" if "\r\n" in text else "\n"
    new, n = re.subn(r"(?m)^([ \t]*sprite_format[ \t]+)\S+", lambda m: m.group(1) + "xml", text, count=1)
    if not n:                                        # switched off with a ';' (the game's copy): on again
        new, n = re.subn(r"(?m)^;[ \t]*(sprite_format[ \t]+)\S+", lambda m: m.group(1) + "xml", text, count=1)
    if not n:
        new = text + ("" if text.endswith(("\n", "\r")) or not text else nl) + XML_LINE + nl
    plan.binary(path, new.encode("latin-1"))
    plan.notes.append((mod.rel(path), "sprite_format xml: %s reads the .sd.xml sprite sheets - each faction can have "
                                      "logos of its own (look the game's panels over once)" % ENGINE[rome(mod)]))
    return path


def give_own(plan, faction):
    """A new faction: its own flag slot and its own logos (the engine's xml sheets or the plain game's binary
    ones), the template's pictures in them."""
    own_flag(plan, faction)
    if not can_own_logo(plan.mod, LOGO, plan):
        if not logo_of(plan, faction, LOGO):
            return                                   # no logo line at all: nothing shared to say
        plan.warn(None, "%s: its faction logos stay %s's - no sprite sheet the editor can add to (with %s, "
                        "'sprite_format xml' in the mod's own descr_caps_ex.txt lets a faction have logos of its own)"
                  % (faction, plan.template, ENGINE[rome(plan.mod)]))
        return
    for which in (LOGO, SMALL):
        own_logo(plan, faction, which)


def entries(mod, faction):
    """The Art tab's cards for these symbols: {'path', 'rel' (the pick key), 'label', 'where', 'size',
    'crop', 'note'}."""
    out = []
    got = flag_of(mod, faction)
    if got and got["sheet"]:
        box = got["box"]
        out.append({"path": got["sheet"], "rel": FLAG, "label": LABELS[FLAG][0], "where": LABELS[FLAG][1],
                    "size": (box[2], box[3], "DXT5"), "crop": box, "symbol": True,
                    "note": "slot %d of %s.dds%s" % (
                        got["index"], got["rel"], (" - shared with %s: Replace gives it a slot of its own"
                                                   % ", ".join(got["shared"])) if got["shared"] else "")})
    for which in (LOGO, SMALL):
        lg = logo_of(mod, faction, which)
        if lg is None:
            continue                                 # no logo line in descr_sm_factions: nothing the game reads
        sp = lg["sprite"]
        found = bool(sp and sp["page_path"])
        sheet = sheets(mod)[which][0]
        own = can_own_logo(mod, which)
        # the engine's switch only where no sheet can take a sprite now (the binary sheets can - spritesheet)
        switch = not own and can_use_xml(mod)
        if found:
            note = "sprite %s on %s" % (lg["name"], sp["page"])
        else:
            # a name the sheets lack: the game shows the sheet's first picture (M2EX: 'Unresolved sprite
            # definition ... defaulting to index 0') - said here, never a card left out (a tester's SSHIP factions)
            note = "sprite %s is on no sheet (%s) - the game shows another picture in its place" % (lg["name"], sheet)
        if not own:
            note += " - cannot be replaced: no sprite sheet the editor can add to" + (
                ": 'Own logos for this mod...' lets it" if switch else
                " (%s with 'sprite_format xml' in the mod's own descr_caps_ex.txt needed)" % ENGINE[rome(mod)])
        elif not found:
            note += " - Replace gives %s a picture of its own" % faction
        elif not lg["own"]:
            note += " - %sReplace gives %s a page of its own" % (
                "shared with %s: " % ", ".join(lg["shared"]) if lg["shared"] else "", faction)
        box = sp["box"] if found else (0, 0) + _box(sheets(mod)[which][4])
        out.append({"path": sp["page_path"] if found else None, "rel": which, "label": LABELS[which][0],
                    "where": LABELS[which][1], "size": (box[2], box[3], 32), "crop": sp["box"] if found else None,
                    "symbol": True, "note": note, "locked": not own, "switch": switch,
                    "missing": not found})
    return out


def write(plan, faction, which, src):
    """An Art pick for one of these symbols: the picture src put in the faction's own place."""
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    if which == FLAG:
        own_flag(plan, faction, im)
    elif own_logo(plan, faction, which, im) is None:
        raise ValueError("%s: the %s cannot be replaced here - no sprite sheet the editor can add to; "
                         "%s with 'sprite_format xml' in the mod's own descr_caps_ex.txt can take it"
                         % (faction, LABELS[which][0], ENGINE[rome(plan.mod)]))


# ---------------------------------------------------------------------------
# Every sprite sheet of a mod, as the game reads it (Interface > Sprite sheets)
# ---------------------------------------------------------------------------
SHEET_ENDS = (".sd.xml", ".rsd", ".sd")


def _sheet_files(mod):
    """{stem: {'binary': path, 'xml': path}} of every sheet in the mod's ui folder, else the game's (the mod's wins)."""
    out = {}
    for data in (_game_data(mod), mod.data):          # the game's first: the mod's own copy replaces it
        ui = _ci(data, "ui") if data else None
        if not ui or not os.path.isdir(ui):
            continue
        for f in os.listdir(ui):
            low = f.lower()
            end = next((e for e in SHEET_ENDS if low.endswith(e)), None)
            if end and os.path.isfile(os.path.join(ui, f)):
                out.setdefault(low[:-len(end)], {})["xml" if end == ".sd.xml" else "binary"] = os.path.join(ui, f)
    return out


def xml_boxes(text):
    """[(page file, [(sprite name, (x, y, w, h))])] of a .sd.xml text - the box the picture takes on its page (tw / th
    when the sheet sets them); a loose sprite is a page of its own, its file."""
    out = [(m.group(1), [(sp["name"], sp["box"]) for sp in sprite_list(m.group(2))]) for m in RE_PAGE.finditer(text)]
    return out + [(sp["file"], [(sp["name"], sp["box"])]) for sp in loose_sprites(text)]


def all_sheets(mod):
    """Every sprite sheet of the mod as the game reads it: [{'name' (the sheet's stem), 'path' (the file read),
    'kind' ('binary' / 'text'), 'other' (its twin the game does not read, or None), 'pages': [(page, [(sprite,
    (x, y, w, h))])], 'error' (words, when it cannot be read)}], by name. The plain games and an engine on 'sd' read
    the binary .rsd / .sd; an engine on 'sprite_format xml' the .sd.xml; a sheet with only one of the two: that one."""
    from . import spritesheet as SS
    xml_mode = sprite_mode(mod) == "xml"
    out = []
    for stem, files in sorted(_sheet_files(mod).items()):
        use = "xml" if (xml_mode and "xml" in files) or "binary" not in files else "binary"
        path = files[use]
        other = files.get("binary" if use == "xml" else "xml")
        sheet = {"name": stem, "path": path, "kind": "text" if use == "xml" else "binary", "other": other,
                 "pages": [], "error": None}
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            sheet["pages"] = xml_boxes(data.decode("latin-1")) if use == "xml" else SS.read(data).boxes()
        except (OSError, ValueError, struct.error) as e:
            sheet["error"] = "%s cannot be read: %s" % (os.path.basename(path), e)
        out.append(sheet)
    return out


def page_cultures(mod, page):
    """[(culture folder, path)] of every ui/<culture>/interface that has the page (the mod's or the game's), the base
    skin first; a page lying in ui itself (Medieval II's radarpage_01.tga): [('', path)]."""
    out = []
    folders = _page_folders(mod, page)
    order = skins(mod)
    folders.sort(key=lambda c: order.index(c.lower()) if c.lower() in order else len(order))
    for c in folders:
        p = _find(mod, "ui", c, "interface", page)
        if p:
            out.append((c, p))
    if not out:
        p = _find(mod, "ui", page)
        if p:
            out.append(("", p))
    return out
