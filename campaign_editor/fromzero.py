"""New faction from zero (the user, 2026-10-22: a new faction 'with nothing in common with an existing one' - its
colours, its symbol, its names): what the window 'New faction from zero' picks for the modder.

The game still needs a faction whose lines the new one's are made from (the clone's template): here it is picked
behind the culture - a faction of that culture - and everything the modder sees is the new faction's own: its
colours away from every faction's, its emblem on every sign, its pictures recoloured, a name list mixed from the
whole culture, not one faction's.
"""

import re

from .namelists import Kept
from .textio import tokens

ALIKE = 60          # traces.NEAR: two colours this close look alike on the map
FAR = 110           # a suggested colour is at least this far from every faction's


def internal_of(text):
    """'Zorgan Realm' -> 'zorgan_realm': lower case letters, digits and _, a letter first."""
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s if s[:1].isalpha() else ("f_" + s if s else "")


def culture_factions(mod, culture):
    """The factions of the culture (descr_sm_factions.txt order), the rebels left out."""
    return [f for f, c in mod.factions() if c == culture and f != "slave"]


def _owned(mod):
    """{faction or culture: how many units name it in their ownership line} (export_descr_unit.txt)."""
    out = {}
    path = mod.file("edu")
    if not path:
        return out
    for line in mod.load(path).texts():
        t = tokens(line.split(";")[0])
        if t[:1] == ["ownership"]:
            for w in t[1:]:
                w = w.strip(",")
                out[w] = out.get(w, 0) + 1
    return out


def frame_faction(mod, campaign, culture):
    """The faction of the culture the new one's lines are made from: one in the campaign before one that is not,
    then the one sharing the most units with its culture (the new faction starts with those - take_template_units),
    then the one with the most units, then by name. None: the culture has no faction."""
    from .build import _in_campaign
    owned = _owned(mod)
    got = culture_factions(mod, culture)
    if not got:
        return None
    return sorted(got, key=lambda f: (not _in_campaign(mod, campaign, f), -len(template_units(mod, f, culture)[1]),
                                      -owned.get(f, 0), f))[0]


def _share(mine, theirs):
    m = {n.lower() for n in mine}
    return len(m & {n.lower() for n in theirs}) / float(len(m)) if m else 0.0


def culture_name_list(mod, culture, most=0.75):
    """(pools, factions the names come from): men's names, surnames and women's names mixed from every faction of
    the culture in turn (each name once), so no one faction's list is most of it - a faction holding more than
    `most` of the first names gives up the names only it has until it does not (traces: 80 % is another faction's
    list). One faction in the culture: its list (the window says so - Name list... makes one of its own)."""
    owners = [f for f in culture_factions(mod, culture) if mod.name_pool(f).get("characters")]
    pools_of = {f: mod.name_pool(f) for f in owners}
    out = {}
    for pool in ("characters", "surnames", "women"):
        lists = [list(pools_of[f].get(pool) or []) for f in owners]
        got, seen = [], set()
        for i in range(max([len(x) for x in lists] or [0])):
            for x in lists:
                if i < len(x) and x[i].lower() not in seen:
                    seen.add(x[i].lower())
                    got.append(Kept(x[i]))      # the game's own keys, as written (Rome's 'Skílas', 'of Itius Portis')
        out[pool] = got
    if len(owners) > 1:
        men = out["characters"]
        for _ in range(len(owners)):
            heavy = [f for f in owners if _share(men, pools_of[f]["characters"]) > most]
            if not heavy:
                break
            for f in heavy:
                others = set().union(*({n.lower() for n in pools_of[o].get("characters") or []}
                                       for o in owners if o != f))
                mine = {n.lower() for n in pools_of[f]["characters"]}
                only = [n for n in men if n.lower() in mine and n.lower() not in others]
                # as few as it takes: the last ones taken go first
                while only and _share(men, pools_of[f]["characters"]) > most:
                    men.remove(only.pop())
        out["characters"] = men
    return out, owners


def colours_alike(mod, primary, secondary=None, skip=()):
    """[(faction, 'both' / 'primary')]: the factions whose colours look like these on the map - the primary alone
    is what the campaign map and the flags show most."""
    from .recolour import faction_colours
    from .traces import colour_gap
    out = []
    if not primary:
        return out
    for f, (p, s) in sorted(faction_colours(mod).items()):
        if f in skip or f == "slave" or not p:
            continue
        if colour_gap(primary, p) < ALIKE:
            both = secondary is None or s is None or colour_gap(secondary, s) < ALIKE
            out.append((f, "both" if both else "primary"))
    return out


def free_colours(mod, count=6, skip=()):
    """[(primary, secondary)]: colour pairs whose primary is far from every faction's primary (and from each
    other's), its secondary light on a dark primary, dark on a light one."""
    import colorsys
    from .recolour import faction_colours
    from .traces import colour_gap
    taken = [p for f, (p, _) in faction_colours(mod).items() if p and f not in skip]
    out = []
    for v in (0.85, 0.55, 0.35):
        for s in (0.85, 0.5):
            for k in range(24):
                h = (k * 7 % 24) / 24.0                 # round the wheel in big steps: neighbours differ
                p = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
                if all(colour_gap(p, t) >= FAR for t in taken + [q for q, _ in out]):
                    light = v * (1 - s / 2) > 0.5
                    out.append((p, (30, 30, 30) if light else (235, 230, 215)))
                    if len(out) >= count:
                        return out
    return out


def _grey(im, size=32):
    """The picture as size x size greys over a mid grey (its see-through parts the grey), centred on its mean."""
    from PIL import Image
    im = im.convert("RGBA").resize((size, size))
    bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
    bg.alpha_composite(im)
    px = list(getattr(bg.convert("L"), "get_flattened_data", bg.convert("L").getdata)())
    m = sum(px) / float(len(px))
    return [v - m for v in px]


def shape_likeness(a, b):
    """-1..1: how alike two symbols look (the correlation of their greys, 1 = the same drawing, its colours
    aside - a symbol only recoloured is still the same symbol)."""
    x, y = _grey(a), _grey(b)
    nx, ny = sum(v * v for v in x) ** 0.5, sum(v * v for v in y) ** 0.5
    if not nx or not ny:
        return 1.0 if nx == ny else 0.0
    return sum(p * q for p, q in zip(x, y)) / (nx * ny)


def faction_logos(mod, campaign, skip=()):
    """{faction: its loading-screen logo (Pillow image)} - the emblem by itself, every faction has one."""
    from . import emblem as E
    from . import factionart as FA
    out = {}
    for f, _ in mod.factions():
        if f in skip or f == "slave":
            continue
        try:
            pics = FA.faction_pictures(mod, campaign, f)
        except Exception:
            continue
        p = next((p for p in pics if p["label"].startswith("loading-screen logo")), None)
        if p is not None:
            try:
                out[f] = E._old(p)
            except Exception:
                pass
    return out


def symbols_alike(picture, logos, most=0.95):
    """[(faction, likeness)] of the logos whose shape is nearly the picture's, the closest first."""
    got = []
    for f, im in logos.items():
        if im is None:
            continue
        k = shape_likeness(picture, im)
        if k >= most:
            got.append((f, k))
    return sorted(got, key=lambda fk: -fk[1])


MIN_COMMON = 6      # fewer units shared by the culture than this: the template's own stay (a faction needs an army)


def template_units(mod, template, culture):
    """(own, common): the template's units only it has - its ownership names it, but no other faction of the
    culture, nor the culture, nor 'all' - and those it shares with its culture (non-combatants left out)."""
    from . import roster as R
    path = mod.file("edu")
    if not path:
        return [], []
    f = mod.load(path)
    others = set(culture_factions(mod, culture)) - {template}
    own, common = [], []
    for blk in R._edu_blocks(f):
        cat_i = R.unit_line(f, blk, "category")
        if cat_i is not None and tokens(f.text(cat_i))[1:2] == ["non_combatant"]:
            continue
        names = set(R.ownership(f, blk))
        if template in names and not (names & others) and culture not in names and "all" not in names:
            own.append(blk[0])
        elif template in names or culture in names or "all" in names:
            common.append(blk[0])
    return own, common


def take_template_units(plan, campaign, culture):
    """New faction > From zero: the units only its frame has are not the new faction's (its ownership, recruit
    lines) - it starts with what the whole culture shares; Roster > By buildings gives it units of its own. A
    culture that shares fewer than MIN_COMMON units: the frame's own stay (said)."""
    from . import roster as R
    own, common = template_units(plan.mod, plan.template, culture)
    if not own:
        return []
    if len(common) < MIN_COMMON:
        plan.note(None, "%s keeps %s's own units (%d): its culture shares only %d - Roster takes out what it should "
                        "not have" % (plan.new, plan.template, len(own), len(common)))
        return []
    for unit in own:
        R.take_unit(plan, plan.new, unit, campaign, culture)
    start = plan.opts.get("start") or {}
    used = {u for c in start.get("characters") or [] for u in c.get("units") or []}
    used |= {u for g in (start.get("garrisons") or {}).values() for u in (g or [])
             if isinstance(u, str)}
    kept = sorted(used & set(own))
    plan.note(None, "%s has the %d unit(s) its culture shares, not %s's own %d (%s) - Roster > By buildings gives "
                    "it units of its own%s" % (plan.new, len(common), plan.template, len(own), ", ".join(own[:6]) +
                                                (" ..." if len(own) > 6 else ""),
                                                "; its starting armies keep %s" % ", ".join(kept) if kept else ""))
    return own
