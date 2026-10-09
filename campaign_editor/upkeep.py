"""Upkeep x N - an add-on of its own (the user, 2026-10-09: 'no huge armies - like Imperium Surrectum: double the
upkeep; on ANY mod, put in and taken out'). Every unit's upkeep in export_descr_unit.txt (stat_cost's third number)
multiplied; the game reads the numbers from that file, so it shows the real, higher upkeep everywhere. What each
unit had is kept in CampaignEditor_upkeep.json beside the file, so Take it out puts back exactly the old numbers
(a unit the modder changed since is left as it is and named). Both games, no engine needed; a backup first, as every
write."""

import json
import os
import re

MARK = "CampaignEditor_upkeep.json"
RE_COST = re.compile(r"^(\s*stat_cost\b\s*)([^;\r\n]*)(.*)$", re.S)
RE_TYPE = re.compile(r"^\s*type\s+(.+?)\s*(;.*)?$")


def _edu(mod):
    p = mod.file("edu")
    if not p or not os.path.isfile(p):
        raise ValueError("this mod has no export_descr_unit.txt")
    return p


def mark_path(mod):
    return os.path.join(os.path.dirname(os.path.abspath(_edu(mod))), MARK)


def installed(mod):
    """{'FACTOR': factor} when the add-on is in this mod, else None."""
    try:
        p = mark_path(mod)
    except ValueError:
        return None
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return {"FACTOR": float(json.load(fh).get("factor", 2))}
    except (OSError, ValueError):
        return None


def _record(mod):
    p = mark_path(mod)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh).get("units", {})


def _units(f):
    """[(line index, unit type, the numbers' text, [numbers' raw parts])] of every stat_cost line."""
    out, unit = [], None
    for i in range(len(f)):
        t = f.text(i)
        m = RE_TYPE.match(t)
        if m:
            unit = m.group(1).strip()
            continue
        m = RE_COST.match(t)
        if m and unit:
            out.append((i, unit, m))
    return out


def _with_upkeep(m, value):
    parts = m.group(2).split(",")
    if len(parts) < 3:
        return None
    old = parts[2]
    lead = old[:len(old) - len(old.lstrip())]
    tail = old[len(old.rstrip()):]
    parts[2] = lead + str(value) + tail
    return m.group(1) + ",".join(parts) + m.group(3)


def _upkeep(m):
    parts = m.group(2).split(",")
    try:
        return int(float(parts[2]))
    except (IndexError, ValueError):
        return None


def plan_install(plan, factor):
    """Every unit's upkeep x factor (from what it had before the add-on, when it is in already)."""
    factor = float(factor)
    if factor <= 0:
        raise ValueError("the upkeep is multiplied by a number above 0")
    mod = plan.mod
    rec = _record(mod)
    f = plan.edit(_edu(mod))
    units, changed = {}, 0
    for i, unit, m in _units(f):
        now = _upkeep(m)
        if now is None:
            continue
        was = rec.get(unit)
        base = was[0] if was and was[1] == now else now      # the modder changed it since: his number is the base
        new = int(round(base * factor))
        units[unit] = [base, new]
        if new != now:
            f.set(i, _with_upkeep(m, new))
            changed += 1
    if not units:
        raise ValueError("no stat_cost line found in export_descr_unit.txt")
    plan.binary(mark_path(mod), (json.dumps({"factor": factor, "units": units}, indent=1, sort_keys=True)
                                 + "\n").encode("utf-8"))
    plan.note(f, "upkeep x %g: %d unit(s) changed (the old numbers kept in %s - Take it out puts them back)"
              % (factor, changed, MARK))


def plan_remove(plan):
    """Every unit's upkeep back to what it had before the add-on; one the modder changed since is left and named."""
    mod = plan.mod
    rec = _record(mod)
    if not rec:
        raise ValueError("Upkeep x N is not in this mod")
    f = plan.edit(_edu(mod))
    left = []
    for i, unit, m in _units(f):
        was = rec.get(unit)
        now = _upkeep(m)
        if not was or now is None:
            continue
        if now == was[1]:
            if was[0] != now:
                f.set(i, _with_upkeep(m, was[0]))
        else:
            left.append(unit)
    plan.delete(mark_path(mod), "Upkeep x N taken out")
    plan.note(f, "upkeep back to the old numbers")
    if left:
        plan.warn(f, "upkeep left as it is now (changed after the add-on was put in): %s" % ", ".join(left[:20]))
