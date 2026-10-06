"""Mercenary pools (descr_mercenaries.txt of a campaign, both games): which units are for hire in which regions.

A pool is a group of regions sharing one hire list:

    pool Gaul
        regions Belgica Armorica Central_Gaul
        unit merc barbarian infantry,   exp 0 cost 800 replenish 0.06 - 0.44 max 4 initial 1

Each unit line: experience, the price, how fast the pool fills again each turn (a range the game picks from), how
many at most, how many at the start. Medieval II adds optional words after them (start_year, end_year, religions
{ }, crusading, events { }) - kept as written ('more').

A region stands in one pool at most: given to a pool, it leaves the one it was in; a pool left without a region
goes (as regiondelete does). Lines not changed stay byte-exact; a changed pool rewrites only its regions line and
the unit lines that changed."""

import re

from .textio import strip_comment

RE_UNIT = re.compile(r"^\s*unit\s+(.+?),?\s+exp\s+(\S+)\s+cost\s+(\S+)\s+replenish\s+(\S+)\s*-\s*(\S+)\s+max\s+(\S+)"
                     r"\s+initial\s+(\S+)(.*)$", re.I)
RE_POOL_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class Unit:
    """One hire line; the numbers kept as written (strings) so an unchanged line writes back the same."""

    FIELDS = ("exp", "cost", "lo", "hi", "max", "initial")

    def __init__(self, name, exp="0", cost="500", lo="0.05", hi="0.15", max_="2", initial="1", more="", line=None):
        self.name, self.exp, self.cost, self.lo, self.hi = name, exp, cost, lo, hi
        self.max, self.initial, self.more, self.line = max_, initial, more.strip(), line

    def key(self):
        return (self.name, self.exp, self.cost, self.lo, self.hi, self.max, self.initial, self.more)

    def copy(self):
        u = Unit(self.name, self.exp, self.cost, self.lo, self.hi, self.max, self.initial, self.more, self.line)
        return u

    def text(self):
        return "\tunit %s,\t\t\texp %s cost %s replenish %s - %s max %s initial %s%s" % (
            self.name, self.exp, self.cost, self.lo, self.hi, self.max, self.initial,
            (" " + self.more) if self.more else "")

    def words(self):
        """The line in plain words."""
        try:
            lo, hi = float(self.lo), float(self.hi)
            every = ("one every %s turns" % _turns(hi, lo)) if hi > 0 else "never comes back"
        except ValueError:
            every = "?"
        return "%s at the start, at most %s; comes back %s - %s a turn (%s); costs %s; experience %s%s" % (
            self.initial, self.max, self.lo, self.hi, every, self.cost, self.exp,
            ("; " + self.more) if self.more else "")


def _turns(hi, lo):
    a = round(1 / hi)
    b = round(1 / lo) if lo > 0 else None
    if b is None:
        return "%d or more" % a
    return str(a) if a == b else "%d - %d" % (a, b)


class Pool:
    def __init__(self, name, regions=None, units=None, start=None, regions_line=None, end=None):
        self.name = name
        self.regions = list(regions or [])
        self.units = list(units or [])
        self.start, self.regions_line, self.end = start, regions_line, end     # line indexes in the file (None: new)
        self.old_name = name if start is not None else None

    def copy(self):
        p = Pool(self.name, self.regions, [u.copy() for u in self.units], self.start, self.regions_line, self.end)
        p.old_name = self.old_name
        return p

    def words(self):
        return "%s - %d region(s), %d unit(s)" % (self.name, len(self.regions), len(self.units))


def path_of(mod, campaign):
    return mod.campaign_file(campaign, "descr_mercenaries.txt")


def read_lines(texts):
    """[Pool] from the file's lines."""
    pools, cur = [], None
    for i, line in enumerate(texts):
        code = strip_comment(line)
        words = code.split()
        if not words:
            continue
        if words[0] == "pool":
            cur = Pool(words[1] if len(words) > 1 else "", start=i, end=i + 1)
            pools.append(cur)
        elif cur is None:
            continue
        elif words[0] == "regions":
            cur.regions = [w.rstrip(",") for w in words[1:] if w.rstrip(",")]
            cur.regions_line, cur.end = i, i + 1
        elif words[0] == "unit":
            m = RE_UNIT.match(code)
            if m:
                cur.units.append(Unit(m.group(1).strip().rstrip(",").strip(), *m.group(2, 3, 4, 5, 6, 7),
                                      more=m.group(8), line=i))
                cur.end = i + 1
    return pools


def read(mod, campaign):
    """(path or None, [Pool])."""
    p = path_of(mod, campaign)
    if not p:
        return None, []
    return p, read_lines(mod.load(p).texts())


def pool_of(pools, region):
    return next((p for p in pools if region in p.regions), None)


def mercenary_units(mod):
    """Every unit of export_descr_unit.txt that may be hired (mercenary_unit), sorted by name."""
    from .units import read_units
    edu = mod.file("edu")
    if not edu:
        return []
    return sorted((u for u in read_units(mod.load(edu)) if u.mercenary), key=lambda u: u.type.lower())


def _number(v, kind):
    try:
        x = float(v) if kind == "float" else int(v)
    except ValueError:
        return None
    return x if x >= 0 else None


def problems(mod, campaign, pools):
    """[plain words] of what the game would not take."""
    out = []
    regions = {r.lower() for r in mod.regions(campaign)}
    from .units import read_units
    edu = mod.file("edu")
    known = {u.type.lower(): u for u in read_units(mod.load(edu))} if edu else {}
    seen = {}
    for p in pools:
        if not RE_POOL_NAME.match(p.name or ""):
            out.append("pool '%s': a pool's name is one word - letters, digits and _" % p.name)
        if p.name.lower() in seen:
            out.append("two pools are called %s" % p.name)
        seen[p.name.lower()] = p
        for r in p.regions:
            if r.lower() not in regions:
                out.append("pool %s: no region %s in descr_regions.txt" % (p.name, r))
        for u in p.units:
            where = "pool %s, %s" % (p.name, u.name)
            k = known.get(u.name.lower())
            if known and k is None:
                out.append("%s: no such unit in export_descr_unit.txt" % where)
            elif k is not None and not k.mercenary:
                out.append("%s: the unit is not a mercenary (no mercenary_unit in export_descr_unit.txt)" % where)
            nums = {f: _number(getattr(u, f), "float" if f in ("lo", "hi") else "int") for f in Unit.FIELDS}
            bad = [f for f, x in nums.items() if x is None]
            if bad:
                out.append("%s: %s must be a number of 0 or more" % (where, ", ".join(_LABEL[f] for f in bad)))
                continue
            if nums["lo"] > nums["hi"]:
                out.append("%s: 'comes back' from %s is more than up to %s" % (where, u.lo, u.hi))
            if nums["initial"] > nums["max"]:
                out.append("%s: %s at the start is more than at most %s" % (where, u.initial, u.max))
    return out


_LABEL = {"exp": "experience", "cost": "cost", "lo": "comes back from", "hi": "comes back up to", "max": "at most",
          "initial": "at the start"}


def give_regions(pools, pool, regions):
    """The regions now belong to pool (and to no other) - [(region, the pool it left)]."""
    left = []
    want = list(dict.fromkeys(regions))
    for p in pools:
        if p is pool:
            continue
        for r in want:
            if r in p.regions:
                p.regions.remove(r)
                left.append((r, p.name))
    pool.regions = want
    return left


def plan_pools(plan, campaign, pools):
    """Write the pools as edited (pools = the whole list, read with read() and changed). A pool with no region left
    goes; lines not changed stay as they are."""
    mod = plan.mod
    path = path_of(mod, campaign)
    if not path:
        raise ValueError("this campaign has no descr_mercenaries.txt")
    f = plan.edit(path)
    old = {p.start: p for p in read_lines(f.texts())}
    check = []                      # only what this edit changes: a mistake the mod already had is not ours to refuse
    for p in pools:
        op = old.get(p.start)
        if not p.regions:
            continue
        was = {u.line: u.key() for u in op.units} if op else {}
        units = [u for u in p.units if u.line not in was or was[u.line] != u.key()]
        q = Pool(p.name, p.regions if op is None or p.regions != op.regions else [], units)
        if op is None or p.name != op.name or units or q.regions:
            check.append(q)
    why = problems(mod, campaign, check)
    if why:
        raise ValueError("; ".join(why))
    keep = {p.start for p in pools if p.start is not None and p.regions}
    edits = []                      # (start, end, [new texts] | None for 'set lines', note)
    for start, op in old.items():
        if start not in keep:
            end = op.end
            if end < len(f.raw) and not f.text(end).strip():
                end += 1                                       # its blank line goes with it
            edits.append((start, end, [], "pool %s goes%s" % (
                op.name, " (no region left)" if any(p.start == start for p in pools) else "")))
    for p in pools:
        if p.start is None or not p.regions:
            continue
        op = old.get(p.start)
        if op is None:
            raise ValueError("descr_mercenaries.txt changed since it was read - open the window again")
        if p.name != op.name:
            words = f.text(p.start)
            edits.append((p.start, p.start + 1, [re.sub(r"(pool\s+)%s" % re.escape(op.name), lambda m: m.group(1) +
                                                        p.name, words, count=1)], "pool %s renamed %s" % (op.name, p.name)))
        if p.regions != op.regions:
            if op.regions_line is not None:
                text = f.text(op.regions_line)
                lead = re.match(r"\s*", text).group(0) or "\t"
                _, sep, comment = text.partition(";")          # its comment stays
                edits.append((op.regions_line, op.regions_line + 1, [lead + "regions " + " ".join(p.regions) +
                                                                     ((" ;" + comment) if sep else "")],
                              "pool %s: regions %s" % (p.name, " ".join(p.regions))))
            else:
                edits.append((p.start + 1, p.start + 1, ["\tregions " + " ".join(p.regions)],
                              "pool %s: regions %s" % (p.name, " ".join(p.regions))))
        old_units = {u.line: u for u in op.units}
        kept = {u.line for u in p.units if u.line is not None}
        for line, u in old_units.items():
            if line not in kept:
                edits.append((line, line + 1, [], "pool %s: %s no longer for hire" % (p.name, u.name)))
        for u in p.units:
            if u.line is not None and u.line in old_units and u.key() != old_units[u.line].key():
                edits.append((u.line, u.line + 1, [u.text()], "pool %s: %s - %s" % (p.name, u.name, u.words())))
        new = [u for u in p.units if u.line is None]
        if new:
            at = op.end
            edits.append((at, at, [u.text() for u in new], "pool %s: %s for hire" % (
                p.name, ", ".join(u.name for u in new))))
    # bottom-up so the indexes stay true; an insert at the same place as a replacement goes after it
    for start, end, texts, note in sorted(edits, key=lambda e: (e[0], e[1] - e[0]), reverse=True):
        if end > start and len(texts) == end - start:
            for k, t in enumerate(texts):
                f.set(start + k, t)
        else:
            f.delete(start, end)
            f.insert(start, texts)
        plan.note(f, note)
    added = [p for p in pools if p.start is None and p.regions]
    if added:
        at = len(f.raw)
        while at > 0 and not f.text(at - 1).strip():
            at -= 1
        lines = []
        for p in added:
            lines += ["", "pool %s" % p.name, "\tregions " + " ".join(p.regions)] + [u.text() for u in p.units]
            plan.note(f, "new pool %s: %s - %d unit(s)" % (p.name, " ".join(p.regions), len(p.units)))
        f.insert(at, lines)
    return plan
