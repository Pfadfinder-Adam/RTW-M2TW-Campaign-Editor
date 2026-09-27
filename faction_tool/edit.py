"""Edit a faction that already exists: its names and descriptions, colours, AI,
treasury, playability, and the garrisons and buildings of its towns. The same
Plan as a new faction, so preview, backup and restore work alike."""

import re

from .build import template_display, validate
from .buildings import settlement_info
from .clone import FE_NAMES, description_key
from .plan import Plan
from .start import MAX_UNITS, _has_army, _units, unit_name
from .strat import Strat
from .textio import tokens

RE_RGB = re.compile(r"red\s*(\d+)\s*,\s*green\s*(\d+)\s*,\s*blue\s*(\d+)")
RE_KEY = re.compile(r"^(\s*\{)([A-Za-z0-9_]+)(\}.*)$")


def _unescape(v):
    return v.strip().replace("\\n", "\n")


def read_faction(mod, campaign, faction):
    """What the faction is now: {display_name, short_name, adjective, description,
    long_description, primary_colour, secondary_colour, ai, denari, playable, regions}."""
    out = dict(template_display(mod, faction, campaign))
    F = faction.upper()
    keys = {m.group(2).upper() for p in mod.campaign_text_files(campaign) for l in mod.load(p).texts()
            for m in [RE_KEY.match(l)] if m}
    long_key = description_key(faction, campaign, keys) + "_DESCR"
    for path in mod.campaign_text_files(campaign):
        for line in mod.load(path).texts():
            m = RE_KEY.match(line)
            if not m:
                continue
            key, val = m.group(2).upper(), m.group(3)[1:]
            if key == F + "_DESCR" and "description" not in out:
                out["description"] = _unescape(val)
            elif key == long_key and "long_description" not in out:
                out["long_description"] = _unescape(val)
    cur = None
    for l in mod.load(mod.file("sm_factions")).texts():
        t = tokens(l)
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1]
        elif cur == faction and t[:1] in (["primary_colour"], ["secondary_colour"]):
            m = RE_RGB.search(l)
            if m:
                out[t[0]] = tuple(int(x) for x in m.groups())
    s = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
    fb = s.faction(faction)
    if not fb:
        raise ValueError("%s has no faction block in this campaign's descr_strat.txt" % faction)
    out["ai"] = " ".join(tokens(fb.header)[2:])
    for i in range(fb.start, fb.end):
        t = tokens(s.lines[i])
        if t[:1] == ["denari"] and len(t) > 1:
            out["denari"] = int(t[1]) if t[1].isdigit() else t[1]
            break
    out["playable"] = bool(s.playable and faction in [n for _, n in s.playable["items"]])
    out["regions"] = [st.region for st in fb.settlements]
    return out


def edit(mod, campaign, faction, opts):
    """A Plan with the changes in opts (only the keys given are changed):
    display_name, short_name, adjective, description, long_description,
    primary_colour, secondary_colour, ai, denari, playable,
    garrisons {region: [unit types]}, buildings {region: [(chain, level)]}."""
    names = [n for n, _ in mod.factions()]
    if faction not in names or faction == "slave":
        raise ValueError("pick an existing faction (not slave) to edit")
    now = read_faction(mod, campaign, faction)
    plan = Plan(mod, faction, faction, dict(opts))
    _texts(plan, now, campaign)
    _colours(plan)
    _strat(plan, campaign, now)
    if plan.opts.get("garrisons") or plan.opts.get("buildings"):
        plan.edit(mod.file("edu"))            # validate() reads these through the plan
        plan.edit(mod.file("sm_factions"))
        validate(plan, campaign)
        plan.warnings = [w for w in plan.warnings if "factions (slave included)" not in w[1]]
    if not plan.changed_files():
        plan.note(None, "nothing to change")
    return plan


# ---------------------------------------------------------------------------
def _texts(plan, now, campaign):
    o, F = plan.opts, plan.new.upper()
    pairs = []
    for k in ("display_name", "short_name", "adjective"):
        old, new = now.get(k), o.get(k)
        if old and new and old != new:
            pairs += [(old, new)] + ([(old.upper(), new.upper())] if old.upper() != old else [])
    pairs.sort(key=lambda p: -len(p[0]))
    set_to = {}
    if o.get("display_name"):
        set_to[F] = o["display_name"]
    if o.get("description") is not None and o.get("description") != now.get("description"):
        set_to[F + "_DESCR"] = o["description"]
    long_new = o.get("long_description")
    if long_new is not None and long_new != now.get("long_description"):
        keys = {m.group(2).upper() for p in plan.mod.campaign_text_files(campaign)
                for l in plan.mod.load(p).texts() for m in [RE_KEY.match(l)] if m}
        set_to[description_key(plan.new, campaign, keys) + "_DESCR"] = long_new
    if not pairs and not set_to:
        return
    fe = FE_NAMES.get(plan.new)
    word = re.compile(r"(?<![A-Z0-9])(%s)(?![A-Z0-9])" % "|".join(re.escape(x) for x in (F, fe) if x))
    for path in plan.mod.campaign_text_files(campaign):
        if "regions_and_settlement_names" in path.lower():
            continue
        f = None
        n = 0
        texts = plan.mod.load(path).texts()
        for i, line in enumerate(texts):
            m = RE_KEY.match(line)
            if not m or not word.search(m.group(2).upper()):
                continue
            key = m.group(2).upper()
            value = m.group(3)[1:]
            gap = value[:len(value) - len(value.lstrip())]
            if key in set_to:
                new = gap + set_to[key].replace("\n", "\\n")
            else:
                new = value
                for a, b in pairs:
                    new = re.sub(r"(?<![A-Za-z])%s(?![a-z])" % re.escape(a), b, new)
            if new != value:
                f = f or plan.edit(path)
                f.set(i, m.group(1) + m.group(2) + "}" + new)
                n += 1
        if n:
            plan.note(f, "%d string(s) changed" % n)


def _colours(plan):
    o = plan.opts
    if not (o.get("primary_colour") or o.get("secondary_colour")):
        return
    f = plan.edit(plan.mod.file("sm_factions"))
    cur, n = None, 0
    for i in range(len(f)):
        t = tokens(f.text(i))
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1]
        elif cur == plan.new and t[:1] in (["primary_colour"], ["secondary_colour"]):
            rgb = o.get(t[0])
            if rgb:
                new = RE_RGB.sub("red %d, green %d, blue %d" % tuple(rgb), f.text(i), 1)
                if new != f.text(i):
                    f.set(i, new)
                    n += 1
    if n:
        plan.note(f, "colours set")
    path = plan.mod.file("sm_factions_json")
    if not path:
        return
    j = plan.edit(path)
    inside = depth = 0
    for i in range(len(j)):
        line = j.text(i)
        if not inside and re.match(r'\s*"%s"\s*:' % re.escape(plan.new), line):
            inside, depth = 1, 0
        if inside:
            for key in ("primary", "secondary"):
                rgb = o.get(key + "_colour")
                if rgb and re.match(r'\s*"%s"\s*:\s*\[' % key, line):
                    j.set(i, re.sub(r"\[[^\]]*\]", "[ %d, %d, %d ]" % tuple(rgb), line, 1))
            depth += line.count("{") - line.count("}")
            if "{" in line or depth:
                inside = 2
            if inside == 2 and depth <= 0:
                inside = 0


def _strat(plan, campaign, now):
    o, fac = plan.opts, plan.new
    path = plan.mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(path)
    s = Strat(f)
    fb = s.faction(fac)
    # the header line: faction <name>, <ai>
    if o.get("ai") and o["ai"] != now.get("ai"):
        f.set(fb.start, re.sub(r"^(\s*faction\s+%s\s*,\s*).*$" % re.escape(fac), r"\g<1>" + o["ai"], f.text(fb.start)))
        plan.note(f, "AI set to %s" % o["ai"])
    if o.get("denari") not in (None, "") and str(o["denari"]) != str(now.get("denari")):
        for i in range(fb.start, fb.end):
            if tokens(f.text(i))[:1] == ["denari"]:
                f.set(i, re.sub(r"(denari\s+)\S+", r"\g<1>%d" % int(o["denari"]), f.text(i), 1))
                plan.note(f, "denari set to %d" % int(o["denari"]))
                break
    if o.get("playable") is not None and bool(o["playable"]) != now.get("playable"):
        _move_list(plan, f, fac, bool(o["playable"]))
    s = Strat(f)
    _garrisons(plan, f, s, campaign)
    _buildings(plan, f, Strat(f))


def _move_list(plan, f, fac, playable):
    s = Strat(f)
    src, dst = (s.nonplayable, s.playable) if playable else (s.playable, s.nonplayable)
    if dst is None:
        raise ValueError("descr_strat.txt has no %s list" % ("playable" if playable else "nonplayable"))
    if src:
        for i, n in src["items"]:
            if n == fac:
                del f.raw[i]
                break
    s = Strat(f)
    dst = s.playable if playable else s.nonplayable
    items = dst["items"]
    at = next((j for j, n in items if n == "slave"), None)
    at = at if at is not None else (items[-1][0] + 1 if items else dst["start"] + 1)
    indent = re.match(r"\s*", f.text(items[0][0])).group(0) if items else "\t"
    f.insert(at, [indent + fac])
    plan.note(f, "%s moved to the %s list" % (fac, "playable" if playable else "nonplayable"))


def _garrisons(plan, f, s, campaign):
    """Each picked garrison replaces the units of the army that holds the town
    (a named character keeps his bodyguard); a town nobody holds gets a captain."""
    picked = plan.opts.get("garrisons") or {}
    if not picked:
        return
    fb = s.faction(plan.new)
    tiles = plan.mod.city_tiles(campaign)
    pool = plan.mod.name_pool(plan.new) or {}
    used = {c.name.split()[0] for x in s.factions for c in x.characters if c.name}
    captains = [n for n in pool.get("characters", []) if n not in used] or pool.get("characters", [])
    jobs = []
    for region, types in picked.items():
        if region not in [st.region for st in fb.settlements]:
            raise ValueError("%s is not a town of %s" % (region, plan.new))
        xy = tiles.get(region)
        holder = next((c for c in fb.characters if c.xy == xy and _has_army(s.lines[c.start:c.end])), None)
        room = MAX_UNITS - (1 if holder is not None and holder.named else 0)
        lines = ["unit\t\t%s\t\t\t\texp 0 armour 0 weapon_lvl 0" % t for t in types][:room]
        jobs.append((region, holder, lines, xy))
    for region, holder, lines, xy in sorted(jobs, key=lambda j: -(j[1].start if j[1] else fb.end)):
        if holder is not None:
            chunk = f.texts()[holder.start:holder.end]
            units = [i for i, l in enumerate(chunk) if tokens(l)[:1] == ["unit"]]
            keep = units[:1] if holder.named else []
            first = units[0] if units else next(i for i, l in enumerate(chunk) if tokens(l)[:1] == ["army"]) + 1
            new = [l for i, l in enumerate(chunk) if i not in units or i in keep]
            at = first + len(keep)
            new[at:at] = lines
            f.raw[holder.start:holder.end] = [f.make(l) for l in new]
            plan.note(f, "%s: %s holds the town with %d unit(s)%s" % (
                region, holder.name, len(lines), " + his bodyguard" if keep else ""))
        else:
            if not captains:
                raise ValueError("%s: no name in %s's name list for a captain" % (region, plan.new))
            name = captains.pop(0)
            block = ["character\t%s, general, age 30, , x %d, y %d" % (name, xy[0], xy[1]), "army"] + lines + [""]
            f.insert(fb.end, block)
            plan.note(f, "%s: captain %s holds the town with %d unit(s)" % (region, name, len(lines)))


def _buildings(plan, f, s):
    from .buildings import available, ranks_ok, read_buildings, set_buildings
    picked = plan.opts.get("buildings") or {}
    if not picked:
        return
    fb = s.faction(plan.new)
    known = {b.name: b for b in read_buildings(plan.mod.load(plan.mod.file("edb")))} if plan.mod.file("edb") else {}
    culture = plan.mod.culture(plan.new)
    by_region = {st.region: st for st in fb.settlements}
    for region in sorted(picked, key=lambda r: -by_region[r].start if r in by_region else 0):
        st = by_region.get(region)
        if st is None:
            raise ValueError("%s is not a town of %s" % (region, plan.new))
        items = [tuple(x) for x in picked[region]]
        level, _ = settlement_info(f.texts()[st.start:st.end])
        for chain, lv_name in items:
            b = known.get(chain)
            lv = b.level(lv_name) if b else None
            if known and not lv:
                raise ValueError("%s: %s %s is not in export_descr_buildings.txt" % (region, chain, lv_name))
            if lv and not available(lv, plan.new, culture):
                plan.warn(f, "%s: %s is not in %s's faction list (%s)" % (region, lv_name, plan.new, lv.requires))
            if lv and not ranks_ok(lv, level):
                plan.warn(f, "%s: %s needs a %s, the settlement is a %s" % (region, lv_name, lv.settlement_min, level))
        f.raw[st.start:st.end] = set_buildings(f.raw[st.start:st.end], items, f.make)
        plan.note(f, "%s: %d building(s) set" % (region, len(items)))


__all__ = ["read_faction", "edit", "unit_name"]
