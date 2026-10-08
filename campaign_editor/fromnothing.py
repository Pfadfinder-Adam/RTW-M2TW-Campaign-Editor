"""Units (and later buildings) made from nothing - not as a copy of one the modder picks.

The modder says WHAT it is (foot soldiers with swords, with spears, with bows / slings / javelins, horsemen
with lances or with bows) and the editor writes every line of the new unit itself, in the form this mod's own
units of that kind have: the lines and their order of the kind's most usual unit, every number the MIDDLE value
(median) of the mod's units of that kind - so the first numbers are what is usual for such a unit in this very mod
(vanilla, a mod with its own scales, REX or not alike) - and then each number the modder sets, in plain words, with
the mod's range beside it. The model is one of the mod's (or the modder's own files, models.own_files); the cards
are pictures of the modder's or plain ones the editor draws; it is recruited where the modder says.

A siege crew, a ship, an elephant or a chariot needs an engine, a ship or an animal of its own - those are still
made as a copy (New unit step by step, 'Start from a unit')."""

import re
import statistics

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
    table = mod.text_file("export_units.txt")
    if not table:
        raise ValueError("no text/export_units.txt in this mod or the game's data - the unit's name has nowhere to go")
    E.set_text_values(plan, table, {
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


__all__ = ["KINDS", "kind_of", "units_of_kind", "typical", "fields", "unit_lines", "problems", "new_unit",
           "card_picture", "recruit_levels", "usual_levels"]
