"""Units and buildings made from nothing - not as a copy of one the modder picks.

The modder says WHAT it is (foot soldiers with swords, with spears, with bows / slings / javelins, horsemen
with lances or with bows) and the editor writes every line of the new unit itself, in the form this mod's own
units of that kind have: the lines and their order of the kind's most usual unit, every number the MIDDLE value
(median) of the mod's units of that kind - so the first numbers are what is usual for such a unit in this very mod
(vanilla, a mod with its own scales, REX or not alike) - and then each number the modder sets, in plain words, with
the mod's range beside it. The model is one of the mod's (or the modder's own files, models.own_files); the cards
are pictures of the modder's or plain ones the editor draws; it is recruited where the modder says.

A siege crew, a ship, an elephant or a chariot needs an engine, a ship or an animal of its own - those are still
made as a copy (New unit step by step, 'Start from a unit').

A building chain the same way: the modder says what it is for (soldiers, money or food, order and learning, a
temple, something else) and how many levels; each level's town size, cost and turns start at the middle of the mod's
chains of that kind, with the effects most of them have; the modder changes them, adds any effect the mod's
buildings use, the units it trains from a level on, its names, texts and pictures (plain ones drawn when none)."""

import os
import re
import statistics

from . import buildings as B
from . import editors as E
from .textio import strip_comment, tokens

# (key, what players would call it, category, classes, mounted)
KINDS = [
    ("foot_melee", "Foot soldiers who fight hand to hand (swords, axes, maces)", "infantry", ("light", "heavy"),
     False),
    ("foot_spear", "Foot soldiers with spears or pikes", "infantry", ("spearmen",), False),
    ("foot_missile", "Foot soldiers who shoot or throw (bows, slings, javelins, crossbows, guns)", "infantry",
     ("missile", "skirmish"), False),
    ("horse_melee", "Horsemen who charge and fight hand to hand (lances, swords)", "cavalry",
     ("light", "heavy", "spearmen"), True),
    ("horse_missile", "Horsemen who shoot or throw (horse archers, mounted javelins)", "cavalry",
     ("missile", "skirmish"), True),
]
KIND_WORDS = {k: w for k, w, *_ in KINDS}
RIDDEN = ("horse", "camel")                         # mounts a horseman's unit rides (elephants, chariots: no)
SKIP_WORDS = ("general_unit", "general_unit_upgrade", "mercenary_unit", "no_custom", "is_peasant", "legionary_name",
              "command")                              # what makes a unit special - not what a new one starts with
WORD_LINES = ("attributes", "stat_pri_attr", "stat_sec_attr", "stat_ter_attr")
NUMBER = re.compile(r"^-?\d+(\.\d+)?f?$")


def _values(text):
    """The comma-separated values of a line, its key cut off (spaces kept out)."""
    code = strip_comment(text).strip()
    parts = code.split(None, 1)
    return [v.strip() for v in parts[1].split(",")] if len(parts) > 1 else []


def _blocks(mod, f=None):
    f = f or mod.load(mod.file("edu"))
    for name, a, b in E.unit_blocks(f):
        yield name, [f.text(i) for i in range(a, b)]


def _first(lines, key):
    return next((_values(t) for t in lines if tokens(t)[:1] == [key]), None)


def mount_class(mod, mount):
    from .models import mount_classes
    return mount_classes(mod).get((mount or "").strip().lower(), "")


def kind_of(mod, lines):
    """The kind (KINDS key) a unit's lines are, or None (a siege crew, a ship, an elephant, a general...)."""
    cat = (_first(lines, "category") or [""])[0].lower()
    cls = (_first(lines, "class") or [""])[0].lower()
    mount = (_first(lines, "mount") or [""])[0]
    if mount and mount_class(mod, mount) not in RIDDEN:
        return None
    if any(tokens(t)[:1] in (["engine"], ["animal"], ["ship"], ["mounted_engine"]) for t in lines):
        return None
    for key, _, c, classes, mounted in KINDS:
        if cat == c and cls in classes and bool(mount) == mounted:
            return key
    return None


def _is_general(lines):
    attrs = " ".join(_first(lines, "attributes") or [])
    return "general_unit" in attrs


def units_of_kind(mod, kind):
    """[(type, lines)] of the mod's units of this kind (generals' bodyguards left out - they are not the usual)."""
    out = [(n, ls) for n, ls in _blocks(mod) if kind_of(mod, ls) == kind and not _is_general(ls)]
    return out or [(n, ls) for n, ls in _blocks(mod) if kind_of(mod, ls) == kind]


def _num(v):
    try:
        return float(v.rstrip("f"))
    except ValueError:
        return None


def _shown(x, like):
    """A median written as the file writes that value: a whole number where the value was one."""
    if "." not in like:
        return str(int(round(x)))
    return ("%.2f" % x).rstrip("0").rstrip(".") or "0"


def nice(x):
    """A number as a person reads it: 40, 3.5, 0.75."""
    return str(int(x)) if float(x).is_integer() else ("%.2f" % x).rstrip("0").rstrip(".")


def typical(mod, kind):
    """What is usual for a unit of this kind in this mod: {'lines': the lines of the kind's most usual unit with
    every number made the kind's middle value, 'ranges': {(key, i): (low, middle, high)}, 'count': how many units
    of the kind there are, 'model', 'mount' (the usual one)}. ValueError when the mod has no unit of the kind."""
    units = units_of_kind(mod, kind)
    if not units:
        raise ValueError("this mod has no unit of that kind (%s) to learn the usual numbers from" %
                         KIND_WORDS.get(kind, kind))
    nums = {}                                         # (key, i) -> [numbers]
    for _, ls in units:
        for t in ls:
            k = tokens(t)[:1]
            if not k or k[0] in ("type", "dictionary", "ownership", "era"):
                continue
            for i, v in enumerate(_values(t)):
                x = _num(v)
                if x is not None:
                    nums.setdefault((k[0], i), []).append(x)
    mid = {k: statistics.median(v) for k, v in nums.items()}
    # word lists: the words at least half the kind's units have (a single unit's quirks - warcry, frighten_foot -
    # are not what such a unit usually is); the mental words: the commonest
    words, mental = {}, {}
    for _, ls in units:
        for key in WORD_LINES:
            for w in {x.split()[0] for x in (_first(ls, key) or []) if x and x.split()}:
                words.setdefault(key, {}).setdefault(w, 0)
                words[key][w] += 1
        for i, v in enumerate(_first(ls, "stat_mental") or []):
            if i > 0 and _num(v) is None:
                mental.setdefault(i, {}).setdefault(v, 0)
                mental[i][v] += 1
    common = {k: {w for w, n in c.items() if n * 2 >= len(units) and w != "no" and w not in SKIP_WORDS}
              for k, c in words.items()}
    span = {k: (min(v), mid[k], max(v)) for k, v in nums.items()}

    def far(ls):                                      # how far a unit is from the middle, each value by its spread
        d = 0.0
        for t in ls:
            k = tokens(t)[:1]
            for i, v in enumerate(_values(t)):
                x = _num(v)
                if k and x is not None and (k[0], i) in span:
                    lo, m, hi = span[(k[0], i)]
                    d += abs(x - m) / ((hi - lo) or 1)
        return d
    # the usual form: the commonest order of keys of the kind, then of those the unit nearest the middle
    forms = {}
    for n, ls in units:
        forms.setdefault(tuple(tokens(t)[0] for t in ls if tokens(t)), []).append((n, ls))
    best = max(forms.values(), key=len)
    _, base = min(best, key=lambda u: far(u[1]))
    lines = []
    for t in base:
        code = strip_comment(t).rstrip()
        k = tokens(code)[:1]
        if not k:
            continue
        if k[0] in ("era",):                          # Medieval II's multiplayer eras: none for a new unit
            continue
        vals = _values(code)
        head = code[:len(code) - len(code.split(None, 1)[1])] if len(code.split(None, 1)) > 1 else code + " "
        if k[0] in WORD_LINES:
            seen, keep = set(), []
            for _, ls in units:                      # the common words in the order the mod writes them
                for w in _first(ls, k[0]) or []:
                    w0 = (w.split() or [""])[0]
                    if w0 in common.get(k[0], ()) and w0 not in seen:
                        seen.add(w0)
                        keep.append(w)
            vals = keep or (["sea_faring"] if k[0] == "attributes" else ["no"])
        elif k[0] == "stat_mental":
            vals = [max(mental[i], key=mental[i].get) if i in mental else
                    (_shown(mid[(k[0], i)], v) if _num(v) is not None and (k[0], i) in mid else v)
                    for i, v in enumerate(vals)]
        elif k[0] not in ("type", "dictionary", "ownership", "soldier", "armour_ug_models", "armour_ug_levels",
                          "officer", "mount", "banner"):
            vals = [_shown(mid[(k[0], i)], v) if _num(v) is not None and (k[0], i) in mid else v
                    for i, v in enumerate(vals)]
        lines.append([k[0], head, vals])
    soldier = _first(base, "soldier") or ["", "", "", ""]
    for line in lines:                                # the men, extras and mass: the kind's middle numbers too
        if line[0] == "soldier":
            line[2] = [soldier[0]] + [_shown(mid[("soldier", i)], v) if _num(v) is not None and ("soldier", i)
                                      in mid else v for i, v in enumerate(soldier) if i > 0]
    return {"lines": lines, "ranges": span, "count": len(units), "model": soldier[0],
            "mount": (_first(base, "mount") or [""])[0] or None}


def weapons(lines):
    """('stat_pri' or 'stat_sec' of the weapon it fights hand to hand with, the one it shoots / throws with or
    None), read from the lines [key, head, values]."""
    by = {k: v for k, _, v in lines if k in ("stat_pri", "stat_sec")}

    def kind(key):
        v = by.get(key) or []
        return v[5].lower() if len(v) > 5 else ""
    missile = next((k for k in ("stat_pri", "stat_sec") if kind(k) in ("missile", "thrown", "siege_missile")), None)
    melee = next((k for k in ("stat_pri", "stat_sec") if kind(k) == "melee"), "stat_pri")
    return melee, missile


def fields(kind, typ):
    """The numbers a modder sets, in plain words: [(label, key, index, value now, (low, middle, high) or None,
    choices or None, a short help)]."""
    lines = typ["lines"]
    melee, missile = weapons(lines)
    by = {k: v for k, _, v in lines}
    out = []

    def add(label, key, i, help_, choices=None):
        vals = by.get(key) or []
        if i < len(vals):
            out.append((label, key, i, vals[i], typ["ranges"].get((key, i)), choices, help_))
    add("Men in the unit", "soldier", 1, "how many soldiers (the unit-size setting scales it)")
    add("Hit points of a man", "stat_health", 0, "1 = dies of one wound, 2 = takes two")
    add("Attack (hand to hand)", melee, 0, "how hard each man hits in melee")
    add("Charge bonus", melee, 1, "added to the attack when it charges")
    if missile:
        add("Missile attack", missile, 0, "how hard each missile hits")
        add("Range (metres)", missile, 3, "how far it shoots or throws")
        add("Missiles each man carries", missile, 4, "its ammunition")
    add("Armour", "stat_pri_armour", 0, "the man's armour")
    add("Defence skill", "stat_pri_armour", 1, "his skill at parrying in melee")
    add("Shield", "stat_pri_armour", 2, "the shield (from the front and left)")
    add("Morale", "stat_mental", 0, "how long it stands before it routs")
    add("Discipline", "stat_mental", 1, "how it takes shocks; impetuous = charges without orders",
        ["normal", "low", "disciplined", "impetuous"])
    add("Training", "stat_mental", 2, "how tidy its formation is", ["untrained", "trained", "highly_trained"])
    add("Turns to train", "stat_cost", 0, "turns in the recruitment queue")
    add("Cost", "stat_cost", 1, "the price to recruit (the custom battle price follows it)")
    add("Upkeep a turn", "stat_cost", 2, "what it costs every turn")
    return out


def _line(head, vals):
    return head + ", ".join(vals) if vals else head.rstrip()


def unit_lines(mod, kind, new_type, new_dict, owners, model=None, mount=None, values=None, name=None, typ=None):
    """The new unit's block, every line written new (typical() + the modder's numbers {(key, i): value})."""
    typ = typ or typical(mod, kind)
    model = model or typ["model"]
    out = []
    for key, head, vals in typ["lines"]:
        vals = list(vals)
        for (k, i), v in (values or {}).items():
            if k == key and i < len(vals) and str(v).strip() != "":
                vals[i] = str(v).strip()
        if key == "type":
            vals = [new_type]
        elif key == "dictionary":
            out.append(head + new_dict + ("      ; %s" % name if name else ""))
            continue
        elif key == "soldier":
            vals[0] = model
        elif key == "mount" and mount:
            vals = [mount]
        elif key == "armour_ug_levels":            # Medieval II: one look, no armour upgrades of its own models
            vals = vals[:1] or ["0"]
        elif key == "armour_ug_models":
            vals = [model]
        elif key == "ownership":
            vals = list(owners)
        elif key == "stat_cost" and values and ("stat_cost", 1) in values and len(vals) > 5:
            vals[5] = str(values[("stat_cost", 1)]).strip() or vals[5]   # the custom battle price follows the cost
        if key == "type":
            out.append(head + new_type)
        else:
            out.append(_line(head, vals))
    return out


def problems(mod, kind, new_type, new_dict, owners, model=None, mount=None, values=None):
    """Why the new unit cannot be written (plain sentences; empty = fine)."""
    from . import models as MO
    out = []
    f = mod.load(mod.file("edu"))
    blocks = E.unit_blocks(f)
    if not " ".join((new_type or "").split()):
        out.append("give it a name in the files (type)")
    elif any(b[0].lower() == " ".join(new_type.split()).lower() for b in blocks):
        out.append("a unit '%s' is in the mod already" % new_type)
    if not new_dict or not re.match(r"^[A-Za-z0-9_]+$", new_dict):
        out.append("the dictionary name is one word: letters, digits and _ only")
    elif any(tokens(f.text(i))[:2] == ["dictionary", new_dict] for _, a, b in blocks for i in range(a, b)):
        out.append("the dictionary name '%s' is taken" % new_dict)
    if not owners:
        out.append("pick who may have it (a faction, a culture or all)")
    if kind not in KIND_WORDS:
        out.append("pick what kind of unit it is")
        return out
    if model and model.lower() not in MO.catalogue(mod):
        out.append("no battle model '%s' in this mod" % model)
    if kind.startswith("horse") and mount and mount_class(mod, mount) not in RIDDEN:
        out.append("'%s' is not a horse or camel of descr_mount.txt" % mount)
    for (k, i), v in (values or {}).items():
        if k in ("stat_mental",) and i > 0:
            continue
        if _num(str(v)) is None:
            out.append("%s: '%s' is not a number" % (k, v))
    return out


def card_picture(size, title, colour=(92, 74, 52)):
    """A plain card the editor draws when the modder has no picture: the unit's initials on a dark ground, its
    name under them on a big picture - a Pillow image, or None without Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    w, h = size
    im = Image.new("RGBA", (w, h), colour + (255,))
    d = ImageDraw.Draw(im)
    for y in range(h):                              # a soft light from the top
        k = 1.0 - 0.45 * y / max(1, h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c * k + 30 * (1 - k)) for c in colour) + (255,))
    d.rectangle([0, 0, w - 1, h - 1], outline=(214, 190, 140, 255))
    initials = "".join(p[0] for p in re.findall(r"[A-Za-z0-9]+", title)[:2]).upper() or "?"

    def font(px):
        for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(name, px)
            except OSError:
                continue
        try:
            return ImageFont.load_default(size=px)
        except TypeError:
            return ImageFont.load_default()
    big = font(max(10, min(w, h) // 2))
    bb = d.textbbox((0, 0), initials, font=big)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], (h * (0.42 if h > 120 else 0.5)) - (bb[3] - bb[1]) / 2 - bb[1]),
           initials, font=big, fill=(236, 220, 180, 255))
    if h > 120:                                     # an info picture: the name too
        small = font(max(9, w // 12))
        words, row, rows = title.split(), "", []
        for wd in words:
            if d.textlength((row + " " + wd).strip(), font=small) > w - 10 and row:
                rows.append(row)
                row = wd
            else:
                row = (row + " " + wd).strip()
        rows.append(row)
        y = h * 0.72
        for r in rows[:3]:
            tw = d.textlength(r, font=small)
            d.text(((w - tw) / 2, y), r, font=small, fill=(236, 220, 180, 255))
            y += small.size + 2 if hasattr(small, "size") else 12
    return im


def _card_bytes(mod, title, info):
    from .factionart import image_tga
    need = E.unit_picture_need(mod, info) or ((160, 210, 32) if info else (48, 64, 32))
    im = card_picture(need[:2], title)
    return image_tga(im) if im is not None else None


def new_unit(plan, kind, new_type, new_dict, owners, model=None, mount=None, values=None, texts=None,
             pictures=None, recruit=(), exp="0", typ=None):
    """Write a unit made from nothing: its block at the end of export_descr_unit.txt, its names and descriptions
    (export_units.txt), its cards (pictures {'card' | 'info': a file}, else plain ones drawn), the model's textures
    for its factions, and a recruit line in every building level of recruit [(chain, level)] (in the file's own
    form, its factions list = the owners). Returns the block's lines."""
    from . import models as MO
    from .roster import recruit_dialect
    mod = plan.mod
    new_type = " ".join(new_type.split())
    why = problems(mod, kind, new_type, new_dict, owners, model, mount, values)
    if why:
        raise ValueError("; ".join(why))
    typ = typ or typical(mod, kind)
    texts = texts or {}
    name = (texts.get("name") or "").strip() or new_type
    lines = unit_lines(mod, kind, new_type, new_dict, owners, model, mount, values, name, typ)
    f = plan.edit(mod.file("edu"))
    while f.raw and not f.text(len(f.raw) - 1).strip():
        del f.raw[-1]
    f.insert(len(f.raw), ["", ""] + lines + [""])
    plan.note(f, "unit %s made from nothing: %s (the usual numbers of the mod's %d such units, then yours)" % (
        new_type, KIND_WORDS[kind].split(" (")[0].lower(), typ["count"]))
    # texts players read
    from . import strtables
    strtables.write_texts(plan, "export_units.txt", {
        new_dict: name, new_dict + "_descr": (texts.get("descr") or "").strip() or name,
        new_dict + "_descr_short": (texts.get("descr_short") or "").strip() or name})
    # the model wears a texture for each of its factions
    facs = [n for n, c in mod.factions() if n in owners or c in owners or "all" in owners]
    info = MO.catalogue(mod).get((model or typ["model"]).lower())
    if info is not None:
        MO._give_textures(plan, info, facs)
    # cards: the modder's pictures, else plain ones drawn
    for which in ("card", "info"):
        targets = E.unit_picture_targets(mod, new_dict, facs, which == "info")
        if not targets:
            continue
        pic = (pictures or {}).get(which)
        if pic:
            E.import_picture(plan, pic, targets, E.unit_picture_need(mod, which == "info"))
            continue
        data = _card_bytes(mod, name, which == "info")
        if data is None:
            plan.warn(None, "no %s for %s: Pillow is missing to draw a plain one - put a picture in with the Unit "
                            "editor" % ("card" if which == "card" else "info picture", new_type))
            continue
        for t in targets:
            plan.binary(t, data)
        plan.notes.append((mod.rel(targets[0]), "a plain %s drawn for %s (%d faction folder(s)) - put your own "
                                                "picture in any time" % (which, new_type, len(targets))))
    # where it is recruited
    if recruit and mod.file("edb"):
        e = plan.edit(mod.file("edb"))
        dialect = recruit_dialect(e)
        blocks = {b[0]: b for b in E.building_blocks(e)}
        done = []
        for chain, level in recruit:
            blk = blocks.get(chain)
            if blk is None:
                raise ValueError("no building chain %s" % chain)
            at, make = E.line_place(e, "building", blk, "capability", level)
            e.insert(at, make(E.recruit_text(dialect, new_type, exp, factions=owners)))
            blocks = {b[0]: b for b in E.building_blocks(e)}
            done.append("%s/%s" % (chain, level))
        plan.note(e, "%s recruited in %s" % (new_type, ", ".join(done)))
    else:
        plan.warn(None, "%s is recruited nowhere yet - pick a building level (or give it with Roster later)" %
                  new_type)
    return lines


def recruit_levels(mod):
    """[(chain, level, how many units it trains now)] of every building level that recruits (where a new unit
    can go)."""
    from .roster import recruit_lines
    if not mod.file("edb"):
        return []
    e = mod.load(mod.file("edb"))
    count = {}
    for _, _, chain, level in recruit_lines(e):
        count[(chain, level)] = count.get((chain, level), 0) + 1
    return [(c, lv, n) for (c, lv), n in count.items()]


def usual_levels(mod, kind, owners):
    """The building levels where this mod's units of the kind are recruited most for these owners (the first
    guess of where a new one goes): up to two (chain, level)."""
    from .roster import recruit_lines
    if not mod.file("edb"):
        return []
    e = mod.load(mod.file("edb"))
    mine = {n for n, _ in units_of_kind(mod, kind)}
    count = {}
    for _, unit, chain, level in recruit_lines(e):
        if unit in mine:
            count[(chain, level)] = count.get((chain, level), 0) + 1
    return [k for k, _ in sorted(count.items(), key=lambda kv: -kv[1])[:2]]


# ---------------------------------------------------------------------------------------------------------------
# Buildings made from nothing
# ---------------------------------------------------------------------------------------------------------------
# (key = editors.chain_group, what players would call it): the mod's chains of each kind give the usual numbers
BUILDING_KINDS = [
    ("military", "Trains soldiers (barracks, stables, ranges, ports)"),
    ("economy", "Brings money or food (markets, farms, mines, roads, smiths)"),
    ("culture and law", "Keeps order or brings learning (law, games, schools, halls)"),
    ("temple", "A temple (a town holds one temple: its name in the files starts with temple_)"),
    ("other", "Something else"),
]
BUILDING_KIND_WORDS = dict(BUILDING_KINDS)
SETTLEMENT_LEVELS = B.SETTLEMENT_LEVELS
MAX_LEVELS = 99                                 # the spin box's top; the original exes take 9 (building_problems warns)
NOT_EFFECTS = ("recruit", "recruit_pool", "retrain", "retrain_pool")    # units are picked on their own
SPECIAL_CHAINS = ("core_", "convert_to_", "guild_")                     # never what a new chain learns from
LEVEL_KEYS = ("settlement_min", "cost", "construction", "material")


def _game(mod):
    from .limits import game_kind
    return game_kind(mod)


def _effect(code):
    """(head, number) of a capability line - the words before its first number ('happiness_bonus bonus',
    'agent spy', 'road_level') and that number - or None (a recruit line, braces, a line with no number)."""
    w = code.split(" requires ")[0].split()
    if not w or w[0] in ("{", "}") or w[0] in NOT_EFFECTS:
        return None
    head = []
    for x in w:
        if NUMBER.match(x):
            return (" ".join(head), x) if head else None
        head.append(x)
    return None


def chain_levels(mod, f=None):
    """[(chain, group, [{'name', 'cost', 'construction', 'settlement_min', 'material', 'effects': [(head, n)]}])]
    of every building chain of the mod."""
    f = f or mod.load(mod.file("edb"))
    out = []
    for name, a, b in E.building_blocks(f):
        levels = []
        for lv in E.chain_tree(f, a, b)["levels"]:
            info = {"name": lv["name"], "effects": []}
            for i in range(lv["open"] + 1, lv["close"]):
                w = strip_comment(f.text(i)).split()
                if len(w) > 1 and w[0] in LEVEL_KEYS:
                    info[w[0]] = w[1]
            if lv["capability"]:
                for i in range(lv["capability"][0] + 1, lv["capability"][1]):
                    e = _effect(strip_comment(f.text(i)))
                    if e:
                        info["effects"].append(e)
            levels.append(info)
        out.append((name, E.chain_group(name), levels))
    return out


def chains_of_kind(mod, kind, f=None):
    """[(chain, levels)] of the mod's own chains of a kind (core, convert_to and guild chains left out)."""
    return [(n, ls) for n, g, ls in chain_levels(mod, f) if g == kind and not n.startswith(SPECIAL_CHAINS)]


def effect_catalogue(mod, f=None):
    """{head: {'count', 'low', 'middle', 'high'}} of every effect the mod's buildings have - what a new building may
    do (both games; the REX / M2EX words a mod uses come with it)."""
    vals = {}
    for _, _, levels in chain_levels(mod, f):
        for lv in levels:
            for head, n in lv["effects"]:
                x = _num(n)
                if x is not None:
                    vals.setdefault(head, []).append(x)
    return {h: {"count": len(v), "low": min(v), "middle": statistics.median_low(v), "high": max(v)}
            for h, v in vals.items()}         # median_low: a value the mod really uses (a whole number stays whole)


def effect_label(head):
    """What an effect row means, without its number ('public order from happiness (+5% a point)')."""
    from .effects import WORDS
    w = head.split()
    if w[0] == "agent" and len(w) > 1:
        return "trains agents: %s (the number: their experience)" % w[1]
    if w[0] == "agent_limit" and len(w) > 1:
        return "more %s agents allowed" % w[1]
    if w[0] == "religious_belief" and len(w) > 1:
        return "spreads %s (the number: its strength)" % w[1]
    if w[0] in WORDS:
        words, per = WORDS[w[0]]
        if per is None:
            return words
        base = re.sub(r"\s*[+-]?%s(%%)?", "", words).replace("%%", "%").strip()
        return base + (" (%s%g%% a point)" % ("+" if "+%s" in words else "", per) if "%%" in words and per != 1
                       else "")
    return head.replace("_", " ")


def _usual(values):
    """The commonest word (the first seen wins a tie), or None."""
    count = {}
    for v in values:
        if v:
            count[v] = count.get(v, 0) + 1
    return max(count, key=lambda k: (count[k], -values.index(k))) if count else None


def building_typical(mod, kind, levels):
    """What is usual for a building of this kind in this mod, level by level: {'levels': [{'settlement_min',
    'cost', 'construction', 'material'}], 'effects': {head: [number per level]} (the effects at least half the
    kind's chains have, each level their middle value there), 'count': the kind's chains, 'catalogue':
    effect_catalogue}. A level deeper than the mod's chains go grows from the one before (cost x 2, a turn more).
    ValueError when the mod has no chain of the kind."""
    f = mod.load(mod.file("edb"))
    chains = chains_of_kind(mod, kind, f)
    if not chains:
        raise ValueError("this mod has no building of that kind (%s) to learn the usual numbers from" %
                         BUILDING_KIND_WORDS.get(kind, kind))
    cat = effect_catalogue(mod, f)
    out = []
    for i in range(levels):
        deep = [ls[i] for _, ls in chains if len(ls) > i]
        prev = out[-1] if out else None
        if not deep:                                 # past every chain of the kind: grows from the level before
            lv = dict(prev)
            lv["cost"] = nice(float(prev["cost"]) * 2)
            lv["construction"] = nice(float(prev["construction"]) + 1)
            at = SETTLEMENT_LEVELS.index(prev["settlement_min"]) if prev["settlement_min"] in SETTLEMENT_LEVELS \
                else 1
            lv["settlement_min"] = SETTLEMENT_LEVELS[min(at + 1, len(SETTLEMENT_LEVELS) - 1)]
            out.append(lv)
            continue
        smin = _usual([x.get("settlement_min") for x in deep]) or "town"
        if prev and smin in SETTLEMENT_LEVELS and prev["settlement_min"] in SETTLEMENT_LEVELS and \
                SETTLEMENT_LEVELS.index(smin) < SETTLEMENT_LEVELS.index(prev["settlement_min"]):
            smin = prev["settlement_min"]            # a higher level never needs a smaller town
        lv = {"settlement_min": smin}
        for key, start in (("cost", 600), ("construction", 2)):
            nums = [_num(x.get(key) or "") for x in deep]
            nums = [x for x in nums if x is not None]
            mid = statistics.median(nums) if nums else start
            if prev and mid < float(prev[key]):
                mid = float(prev[key])               # never cheaper or quicker than the level below
            lv[key] = nice(round(mid))
        lv["material"] = _usual([x.get("material") for x in deep])
        out.append(lv)
    have = {}
    for _, ls in chains:
        for h in {h for x in ls for h, _ in x["effects"]}:
            have[h] = have.get(h, 0) + 1
    effects = {}
    for h, n in sorted(have.items(), key=lambda kv: -kv[1]):
        if n * 2 < len(chains):
            continue
        row = []
        for i in range(levels):
            nums = [_num(v) for _, ls in chains if len(ls) > i for hh, v in ls[i]["effects"] if hh == h]
            nums = [x for x in nums if x is not None]
            row.append(nice(statistics.median_low(nums)) if nums else (row[-1] if row else nice(cat[h]["middle"])))
        effects[h] = row
    return {"levels": out, "effects": effects, "count": len(chains), "catalogue": cat}


def _ownership(mod, unit):
    f = mod.load(mod.file("edu"))
    for n, a, b in E.unit_blocks(f):
        if n.lower() == unit.lower():
            return [x for x in (_first([f.text(i) for i in range(a, b)], "ownership") or []) if x]
    return None


def recruiters(mod, unit, builders):
    """The names a recruit line of the unit in this chain lets in: of the builders those who may own it (its
    ownership line) - a builder the ownership names itself as it is, a culture or 'all' only as far as its factions
    may own it (the game stops on a line letting in a faction the unit's ownership leaves out)."""
    from .units import owner_factions
    own = _ownership(mod, unit)
    if not own:
        return []
    may = set(owner_factions(mod, own))
    facs = [(n, c) for n, c in mod.factions() if n != "slave" or "slave" in builders]   # the rebels only by name
    out = []
    for b in builders:
        names = [n for n, _ in facs] if b == "all" else [b] if b in dict(facs) else [n for n, c in facs if c == b]
        hits = [n for n in names if n in may]
        if b in own or (hits and len(hits) == len(names) and b != "all"):
            got = [b]
        else:
            got = hits
        out += [x for x in got if x not in out]
    return out


def trainable_units(mod, builders):
    """The units at least one of the builders may own (what a new chain can train), the mod's order; never the
    townsfolk (category non_combatant) nor ships (a new chain is no port: ships come from the game's port
    buildings)."""
    f = mod.load(mod.file("edu"))
    out = []
    for n, a, b in E.unit_blocks(f):
        lines = [f.text(i) for i in range(a, b)]
        if (_first(lines, "category") or [""])[0].lower() in ("non_combatant", "ship"):
            continue
        if recruiters(mod, n, builders):
            out.append(n)
    return out


def building_problems(mod, kind, chain, levels, builders, numbers=None, units=()):
    """Why the new chain cannot be written (plain sentences; empty = fine). levels: [(code name, ...)]; numbers:
    [{'settlement_min', 'cost', 'construction', 'effects': {head: number}}] per level; units: [(type, from level
    index)]."""
    from . import limits
    out = []
    f = mod.load(mod.file("edb"))
    blocks = E.building_blocks(f)
    if not chain or not re.match(r"^[A-Za-z0-9_]+$", chain):
        out.append("the chain's name in the files is one word: letters, digits and _ only")
    elif any(b[0].lower() == chain.lower() for b in blocks):
        out.append("a building chain '%s' is in the mod already" % chain)
    taken = set()
    for _, a, b in blocks:
        for fd in E.fields(f, a, b):
            if fd.key == "levels":
                taken.update(x.lower() for x in fd.value.split())
    names = [lv[0] for lv in levels]
    if not names:
        out.append("give it at least one level")
    for n in names:
        if not re.match(r"^[A-Za-z0-9_]+$", n or ""):
            out.append("level '%s': its name in the files is one word (letters, digits and _)" % n)
        elif n.lower() in taken:
            out.append("a level '%s' is in the mod already" % n)
        elif chain and n.lower() == chain.lower():
            out.append("level '%s' has the chain's own name - give it another" % n)
    if len({(n or "").lower() for n in names}) < len(names):
        out.append("two levels have the same name")
    if not builders:
        out.append("pick who may build it (factions, cultures or all)")
    if kind not in BUILDING_KIND_WORDS:
        out.append("pick what kind of building it is")
    game = _game(mod)
    if not limits.lifted(mod, "chains"):
        cap = limits.HARD_LIMITS.get(game, {}).get("chains")
        if cap and len(blocks) + 1 > cap:
            out.append("the game takes %d building chains without REX / M2EX - this mod has %d" % (cap, len(blocks)))
    if not limits.lifted(mod, "levels"):
        cap = limits.HARD_LIMITS.get(game, {}).get("levels")
        if cap and len(names) > cap:
            out.append("the game takes %d levels in one chain without REX / M2EX" % cap)
    for i, lv in enumerate(numbers or []):
        for key, words in (("cost", "cost"), ("construction", "turns to build")):
            if _num(str(lv.get(key, ""))) is None:
                out.append("level %d: %s '%s' is not a number" % (i + 1, words, lv.get(key, "")))
        if lv.get("settlement_min") not in SETTLEMENT_LEVELS:
            out.append("level %d: the town it needs is one of %s" % (i + 1, ", ".join(SETTLEMENT_LEVELS)))
        for head, v in (lv.get("effects") or {}).items():
            if _num(str(v)) is None:
                out.append("level %d: %s - '%s' is not a number" % (i + 1, effect_label(head), v))
    for unit, start in units or ():
        own = _ownership(mod, unit)
        if own is None:
            out.append("no unit '%s' in the mod" % unit)
        elif not recruiters(mod, unit, builders):
            out.append("%s: no one who builds it may own it (its ownership: %s)" % (unit, ", ".join(own) or "none"))
        if not 0 <= start < max(1, len(names)):
            out.append("%s: trained from a level the chain does not have" % unit)
    return out


def building_lines(mod, chain, levels, builders, numbers, castle=False, units=(), indent="    ", f=None,
                   religion=None):
    """The new chain's block, every line written new in both games' form: levels [(code name, ...)], numbers per
    level {'settlement_min', 'cost', 'construction', 'material', 'effects': {head: number}}, units [(type, from
    level index)] - recruit lines from that level on (Medieval II: recruit_pool); religion: Medieval II's
    'religion <name>' line of a temple chain (the religion its religion_level spreads)."""
    from .roster import recruit_dialect
    f = f or mod.load(mod.file("edb"))
    m2 = _game(mod) == "medieval2"
    dialect = recruit_dialect(f)
    names = [lv[0] for lv in levels]
    i1, i2, i3, i4 = (indent * k for k in (1, 2, 3, 4))
    who = "requires factions { %s}" % "".join("%s, " % b for b in builders)
    out = ["building %s" % chain, "{"] + (["%sreligion %s" % (i1, religion)] if religion and m2 else []) + \
        ["%slevels %s " % (i1, " ".join(names)), "%s{" % i1]
    for k, name in enumerate(names):
        lv = numbers[k]
        out.append("%s%s%s %s " % (i2, name, (" castle" if castle else " city") if m2 else "", who))
        out += ["%s{" % i2, "%scapability" % i3, "%s{" % i3]
        for head, v in (lv.get("effects") or {}).items():
            if head.split()[0] == "agent":
                out.append("%s%s  %s  %s " % (i4, head, v, who))
            else:
                out.append("%s%s %s" % (i4, head, v))
        for unit, start in units or ():
            if k >= start:
                out.append(i4 + E.recruit_text(dialect, unit, "0", factions=recruiters(mod, unit, builders)))
        out.append("%s}" % i3)
        if m2:
            out.append("%smaterial %s" % (i3, lv.get("material") or "wooden"))
        out += ["%sconstruction  %s " % (i3, lv["construction"]), "%scost  %s " % (i3, lv["cost"]),
                "%ssettlement_min %s" % (i3, lv["settlement_min"]), "%supgrades" % i3, "%s{" % i3]
        if k + 1 < len(names):
            out.append("%s%s" % (i4, names[k + 1]))
        out += ["%s}" % i3, "%s}" % i2]
    out += ["%s}" % i1, "%splugins " % i1, "%s{" % i1, "%s}" % i1, "}"]
    return out


def picture_folders(mod, builders):
    """[culture folder] whose building pictures the cultures that build it read: each one's own buildings folder,
    else the first descr_ui_buildings.txt sends it to (the game falls back the same way), in the mod or the game's
    data; a culture with neither gets its own (the folder is made). And the BuildingPictures used."""
    bp = B.BuildingPictures(mod)
    out = []
    for c in B.cultures_of(mod, builders):
        to = next((x for x in bp.cultures(c) if bp.index.get(x.lower())), c)
        if to not in out:
            out.append(to)
    return out, bp


def picture_need(bp, culture, which, game):
    """(w, h) of a culture's own building pictures of one kind ('pic' in the town, 'constructed' when built,
    'small' in Medieval II's construction queue), from its files; else the games' usual sizes."""
    seen = {}
    for name, path in bp.index.get(culture.lower(), {}).items():
        if not name.startswith("#") or not name.endswith(".tga") or \
                (which == "constructed") != name.endswith("_constructed.tga"):
            continue
        if which == "small":
            path = os.path.join(os.path.dirname(path), "construction", os.path.basename(path))
            if not os.path.isfile(path):
                continue
        info = E.tga_info(path)
        if info:
            seen[info[:2]] = seen.get(info[:2], 0) + 1
        if sum(seen.values()) >= 30:
            break
    if seen:
        return max(seen, key=seen.get)
    return {"pic": (78, 62), "constructed": (300, 245) if game == "medieval2" else (361, 163),
            "small": (64, 51)}[which]


def has_small(bp, culture):
    """Whether a culture keeps construction-queue pictures (Medieval II: buildings/construction/)."""
    return any(os.path.isdir(os.path.join(os.path.dirname(p), "construction"))
               for p in list(bp.index.get(culture.lower(), {}).values())[:1])


def building_pictures(plan, chain, levels, builders, pictures=None):
    """Each level's pictures for every culture folder its builders read: in the town, when built and (Medieval II)
    the small one of the construction queue - the modder's (pictures {code name: {'pic', 'constructed'}}; the
    small one made from 'pic'), else plain ones drawn with the level's initials. How many were drawn."""
    from .factionart import image_tga
    mod = plan.mod
    game = _game(mod)
    folders, bp = picture_folders(mod, builders)
    drawn = 0
    for name, shown, *_ in levels:
        given = (pictures or {}).get(name) or {}
        for folder in folders:
            kinds = [("pic", "pic"), ("constructed", "constructed")]
            if game == "medieval2" and has_small(bp, folder):
                kinds.append(("small", "pic"))
            for which, src_key in kinds:
                size = picture_need(bp, folder, which, game)
                path = E.building_picture_target(mod, folder, name, which == "constructed")
                if which == "small":
                    path = os.path.join(os.path.dirname(path), "construction", os.path.basename(path))
                src = given.get(src_key)
                if src:
                    plan.binary(path, E.tga_bytes(src, size))
                    continue
                im = card_picture(size, shown or name)
                if im is not None:
                    plan.binary(path, image_tga(im))
                    drawn += 1
    return drawn


def new_building(plan, kind, chain, levels, builders, numbers, castle=False, units=(), chain_name="",
                 pictures=None, religion=None):
    """Write a building chain made from nothing: its block after the mod's last chain in export_descr_buildings.txt,
    the texts players read (export_buildings.txt: {chain}_name, each level's name, description and short
    description - every copy of the table the game may read), each level's pictures (building_pictures). levels
    [(code name, name players see, short description, description)]. Returns the block's lines."""
    from . import strtables
    mod = plan.mod
    why = building_problems(mod, kind, chain, levels, builders, numbers, units)
    if why:
        raise ValueError("; ".join(why))
    f = plan.edit(mod.file("edb"))
    blocks = E.building_blocks(f)
    indent = "    "
    if blocks:
        t = f.text(blocks[-1][1] + 2)                 # the 'levels' line of the last chain
        indent = t[:len(t) - len(t.lstrip())] or indent
    lines = building_lines(mod, chain, levels, builders, numbers, castle, units, indent, f, religion)
    at = blocks[-1][2] if blocks else len(f.raw)
    f.insert(at, [""] + lines)
    plan.note(f, "building %s made from nothing: %s, %d level(s) %s (the usual numbers of the mod's %s buildings, "
                 "then yours)" % (chain, BUILDING_KIND_WORDS[kind].split(" (")[0].lower(), len(levels),
                                  ", ".join(lv[0] for lv in levels), kind))
    values = {"%s_name" % chain: chain_name or levels[0][1] or chain.replace("_", " ")}
    for name, shown, short, desc in levels:
        values[name] = shown or name.replace("_", " ")
        values[name + "_desc"] = desc or short or values[name]
        values[name + "_desc_short"] = short or values[name]
    strtables.write_texts(plan, "export_buildings.txt", values)
    drawn = building_pictures(plan, chain, levels, builders, pictures)
    if drawn:
        plan.note(None, "%d plain picture(s) drawn for %s (the levels' initials) - put your own in any time with "
                        "the Building editor" % (drawn, chain))
    elif not any((pictures or {}).values()):
        plan.warn(None, "no pictures for %s: Pillow is missing to draw plain ones - put pictures in with the "
                        "Building editor" % chain)
    return lines


def typical_numbers(typ):
    """The per-level numbers a chain starts with: [{'settlement_min', 'cost', 'construction', 'material', 'effects':
    {head: number}}] from building_typical."""
    return [dict(lv, effects={h: row[i] for h, row in typ["effects"].items()})
            for i, lv in enumerate(typ["levels"])]


__all__ = ["KINDS", "kind_of", "units_of_kind", "typical", "fields", "unit_lines", "problems", "new_unit",
           "card_picture", "recruit_levels", "usual_levels", "BUILDING_KINDS", "chains_of_kind", "effect_catalogue",
           "effect_label", "building_typical", "typical_numbers", "recruiters", "trainable_units",
           "building_problems", "building_lines", "building_pictures", "new_building"]
