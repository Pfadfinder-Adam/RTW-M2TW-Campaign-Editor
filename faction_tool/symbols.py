"""A Rome faction's symbols that live on shared sheets, not in files of their own:

- the **flag symbol** on the campaign map (armies, towns, fleets): descr_sm_factions.txt
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

from .moddata import _ci
from .textio import TextFile, strip_comment, tokens

FLAG, LOGO, SMALL = "symbol:flag", "symbol:logo", "symbol:small_logo"
SHEETS = {LOGO: ("strat3.sd.xml", "logo_index", "FACTION_LOGO_%s", "faction_logo_%s.tga", 52),
          SMALL: ("shared2.sd.xml", "small_logo_index", "SMALL_FACTION_LOGO_%s", "faction_logo_small_%s.tga", 32)}
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
    f.set(i, re.sub(r"^(\s*\S+\s+)(\S+)", lambda m: m.group(1) + str(value), text, 1))


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
def slot_box(k, size=128):
    """(sheet number, (x, y, w, h)) of standard_index k."""
    h = size // 2
    return k // 4 + 1, ((k % 2) * h, ((k // 2) % 2) * h, h, h)


def sheet_path(mod, n, plan=None):
    """The sheet symbols<n>: the plan's new one, the mod's, else the game's (None when none)."""
    mine = os.path.join(mod.data, "banners", "symbols%d.tga.dds" % n)
    if plan is not None and mine in plan.binaries:
        return mine
    return _find(mod, "banners", "symbols%d.tga.dds" % n)


def flag_of(plan_or_mod, faction):
    """{'index', 'sheet' (path or None), 'box', 'shared': [factions]} or None."""
    mod = getattr(plan_or_mod, "mod", plan_or_mod)
    _, f = _sm(plan_or_mod)
    vals = sm_values(f, "standard_index")
    if faction not in vals or not vals[faction][1].isdigit():
        return None
    k = int(vals[faction][1])
    n, box = slot_box(k)
    shared = sorted(x for x, (_, v) in vals.items() if v == str(k) and x != faction)
    return {"index": k, "sheet": sheet_path(mod, n, plan_or_mod if hasattr(plan_or_mod, "files") else None),
            "box": box, "shared": shared}


def free_slot(plan_or_mod):
    """The lowest standard_index no faction uses."""
    _, f = _sm(plan_or_mod)
    used = {int(v) for _, v in sm_values(f, "standard_index").values() if v.isdigit()}
    k = 0
    while k in used:
        k += 1
    return k


def _paste_flag(plan, k, im, why):
    """Picture im into slot k of its sheet (written to the mod's banners folder, in the sheet's
    own format and mipmaps; a sheet the game does not have yet is made like symbols1)."""
    from PIL import Image
    from .factionart import image_dds
    mod = plan.mod
    n, (x, y, w, h) = slot_box(k)
    src = sheet_path(mod, n, plan)
    # the format and mipmaps to write in: the sheet on disk, else symbols1's
    like = _find(mod, "banners", "symbols%d.tga.dds" % n) or _find(mod, "banners", "symbols1.tga.dds")
    sheet = _read_image(plan, src) if src else Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    if sheet.size != (w * 2, h * 2):
        _, (x, y, w, h) = slot_box(k, sheet.size[0])
    im = im.convert("RGBA").resize((w, h), Image.LANCZOS)
    sheet.paste(im, (x, y))
    target = os.path.join(mod.data, "banners", "symbols%d.tga.dds" % n)
    plan.binary(target, image_dds(sheet, like))
    plan.notes.append((mod.rel(target), "flag symbol %d (%s) %s" % (k, ("top left", "top right", "bottom left",
                                                                         "bottom right")[k % 4], why)))


def flag_image(plan_or_mod, faction):
    """The faction's flag symbol as a picture, or None."""
    got = flag_of(plan_or_mod, faction)
    if not got or not got["sheet"]:
        return None
    sheet = _read_image(plan_or_mod if hasattr(plan_or_mod, "files") else None, got["sheet"])
    n, (x, y, w, h) = slot_box(got["index"], sheet.size[0])
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
    if got["shared"]:
        k = free_slot(plan)
        f = plan.edit(path)
        i = sm_values(f, "standard_index")[faction][0]
        _set_value(f, i, k)
        plan.note(f, "%s's flag symbol: slot %d of its own (was %d, shared with %s)" % (
            faction, k, got["index"], ", ".join(got["shared"])))
    if pic is not None:
        _paste_flag(plan, k, pic, "for %s" % faction if im is None else "replaced for %s" % faction)
    return k


# ---------------------------------------------------------------------------
# The faction logos (REX sprite sheets)
# ---------------------------------------------------------------------------
def sprite_mode(mod):
    """'xml' when REX packs the .sd.xml sheets (sprites can be added), else 'sd' (binary .rsd)."""
    p = _ci(mod.data, "descr_caps_ex.txt") or (_ci(_game_data(mod), "descr_caps_ex.txt") if _game_data(mod) else None)
    if not p:
        return "sd"
    for line in TextFile.load(p).texts():
        t = tokens(strip_comment(line))
        if t[:1] == ["sprite_format"] and len(t) > 1:
            return t[1].lower()
    return "sd"


RE_PAGE = re.compile(r'<page\s+file="([^"]+)"[^>]*>(.*?)</page>', re.S)
RE_SPRITE = re.compile(r'<sprite\s+name="([^"]+)"\s+x="(\d+)"\s+y="(\d+)"\s+w="(\d+)"\s+h="(\d+)"')


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


def page_path(mod, page, plan=None):
    mine = os.path.join(mod.data, "ui", "roman", "interface", page)
    if plan is not None and mine in plan.binaries:
        return mine
    return _find(mod, "ui", "roman", "interface", page)


def find_sprite(mod, sheet, name, plan=None):
    """{'xml', 'page', 'page_path', 'box'} of a sprite, or None."""
    xp = xml_path(mod, sheet, plan)
    if not xp:
        return None
    text = _xml_text(plan, xp)
    for m in RE_PAGE.finditer(text):
        for s in RE_SPRITE.finditer(m.group(2)):
            if s.group(1) == name:
                x, y, w, h = (int(v) for v in s.groups()[1:])
                return {"xml": xp, "page": m.group(1), "page_path": page_path(mod, m.group(1), plan),
                        "box": (x, y, w, h)}
    return None


def logo_of(plan_or_mod, faction, which):
    """{'name', 'sprite' (find_sprite or None), 'own' (a page of its own), 'shared': [factions]}."""
    mod = getattr(plan_or_mod, "mod", plan_or_mod)
    plan = plan_or_mod if hasattr(plan_or_mod, "files") else None
    sheet, key, _, own_page, _ = SHEETS[which]
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


def own_logo(plan, faction, which, im=None):
    """The faction's logo on a page of its own (made when it has none: a sprite named after it in
    the sheet, the picture in ui/roman/interface, its logo line pointed at it); im or the logo it
    shows now drawn there. Returns the sprite name, or None when the mod cannot take new sprites."""
    from PIL import Image
    from .factionart import image_tga
    mod = plan.mod
    sheet, key, sprite_name, own_page, size = SHEETS[which]
    got = logo_of(plan, faction, which)
    if got is None or sprite_mode(mod) != "xml":
        return None
    pic = im if im is not None else logo_image(plan, faction, which)
    if pic is None:
        return None
    page = own_page % faction
    target = os.path.join(mod.data, "ui", "roman", "interface", page)
    name = got["name"]
    if not got["own"]:
        name = sprite_name % faction.upper()
        xp = xml_path(mod, sheet, plan)
        text = _xml_text(plan, xp)
        if not find_sprite(mod, sheet, name, plan):
            nl = "\r\n" if "\r\n" in text else "\n"
            block = ('  <page file="%s" w="%d" h="%d">%s    <sprite name="%s" x="0" y="0" w="%d" h="%d" alpha="1"/>'
                     '%s  </page>%s') % (page, size, size, nl, name, size, size, nl, nl)
            at = text.rfind("</sprite_definitions>")
            text = text[:at] + block + text[at:]
            mine = os.path.join(mod.data, "ui", sheet)
            plan.binary(mine, text.encode("latin-1"))
            plan.notes.append((mod.rel(mine), "sprite %s: a page of its own for %s (%s)" % (name, faction, page)))
        path, f = _sm(plan)
        f = plan.edit(path)
        _set_value(f, sm_values(f, key)[faction][0], name)
        plan.note(f, "%s's %s now %s (was %s%s)" % (faction, key, name, got["name"],
                                                     ", shared with " + ", ".join(got["shared"]) if got["shared"] else ""))
    size_now = got["sprite"]["box"][2:] if got["own"] and got["sprite"] else (size, size)
    pic = pic.convert("RGBA").resize(tuple(size_now), Image.LANCZOS)
    plan.binary(target, image_tga(pic))
    plan.notes.append((mod.rel(target), "%s of %s%s" % (LABELS[which][0], faction, " replaced" if im is not None else "")))
    return name


# ---------------------------------------------------------------------------
# For the clone, the Art tab and its writes
# ---------------------------------------------------------------------------
def give_own(plan, faction):
    """A new faction: its own flag slot and (REX xml sheets) its own logos, the template's pictures in them."""
    if not rome(plan.mod):
        return
    own_flag(plan, faction)
    if sprite_mode(plan.mod) != "xml":
        if not logo_of(plan, faction, LOGO):
            return                                   # no logo line at all: nothing shared to say
        plan.warn(None, "%s: its faction logos stay %s's - the game reads the binary sprite sheets (.rsd); "
                        "with REX, 'sprite_format xml' in descr_caps_ex.txt lets a faction have logos of its own"
                  % (faction, plan.template))
        return
    for which in (LOGO, SMALL):
        own_logo(plan, faction, which)


def entries(mod, faction):
    """The Art tab's cards for these symbols: {'path', 'rel' (the pick key), 'label', 'where', 'size',
    'crop', 'note'}."""
    if not rome(mod):
        return []
    out = []
    got = flag_of(mod, faction)
    if got and got["sheet"]:
        n, box = slot_box(got["index"])
        out.append({"path": got["sheet"], "rel": FLAG, "label": LABELS[FLAG][0], "where": LABELS[FLAG][1],
                    "size": (box[2], box[3], "DXT5"), "crop": box, "symbol": True,
                    "note": "slot %d of banners/symbols%d.tga.dds%s" % (
                        got["index"], n, (" - shared with %s: Replace gives it a slot of its own"
                                          % ", ".join(got["shared"])) if got["shared"] else "")})
    xml = sprite_mode(mod) == "xml"
    for which in (LOGO, SMALL):
        lg = logo_of(mod, faction, which)
        sp = lg and lg["sprite"]
        if not sp or not sp["page_path"]:
            continue
        note = "sprite %s on %s" % (lg["name"], sp["page"])
        if not xml:
            note += " - cannot be replaced: the game reads the binary .rsd sheets (REX 'sprite_format xml' needed)"
        elif not lg["own"]:
            note += " - shared sheet: Replace gives %s a page of its own" % faction
        out.append({"path": sp["page_path"], "rel": which, "label": LABELS[which][0], "where": LABELS[which][1],
                    "size": (sp["box"][2], sp["box"][3], 32), "crop": sp["box"], "symbol": True, "note": note,
                    "locked": not xml})
    return out


def write(plan, faction, which, src):
    """An Art pick for one of these symbols: the picture src put in the faction's own place."""
    from PIL import Image
    im = Image.open(src).convert("RGBA")
    if which == FLAG:
        own_flag(plan, faction, im)
    elif own_logo(plan, faction, which, im) is None:
        raise ValueError("%s: the %s cannot be replaced here - the game reads the binary sprite sheets; "
                         "REX with 'sprite_format xml' in descr_caps_ex.txt can take it" % (faction, LABELS[which][0]))
