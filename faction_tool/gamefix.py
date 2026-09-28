"""Known set-up problems of a game or mod that stop it from starting, found on Load and
fixed with the user's yes (a Plan: previewed, backed up, undone by Restore like any
other change)."""

import os
import re

from .moddata import _ci
from .plan import Plan
from .textio import strip_comment


def _vegetation_maps(mod):
    """Whether the raw vegetation maps M2EX's text source needs are there."""
    game = os.path.dirname(mod.data)
    for root in (mod.data, game):
        if os.path.isdir(os.path.join(root, "export", "new_vegetation", "raw_distribution_maps")):
            return True
    return False


def problems(mod):
    """[{'id', 'why', 'file', 'line', 'new'}] - what would stop the game and can be put right."""
    out = []
    caps = _ci(mod.data, "descr_caps_ex.txt")
    if caps:
        f = mod.load(caps)
        for i in range(len(f)):
            code = strip_comment(f.text(i))
            m = re.match(r"^(\s*vegetation_source\s+)text\s*$", code)
            if m and not _vegetation_maps(mod):
                out.append({
                    "id": "vegetation_source",
                    "why": "descr_caps_ex.txt reads the vegetation from text (vegetation_source text), which "
                           "needs export/new_vegetation/raw_distribution_maps - not here, so M2EX closes "
                           "at start ('Failed to load text vegetation database'). The fix: vegetation_source "
                           "binary (the game's own vegetation.db, M2EX's default for mods).",
                    "file": caps, "line": i, "new": f.text(i).replace(m.group(0), m.group(1) + "binary", 1)})
    return out


def fix_plan(mod, found):
    """A Plan that puts the problems found right."""
    plan = Plan(mod, "setup", "setup_fix")
    for p in found:
        f = plan.edit(p["file"])
        f.set(p["line"], p["new"])
        plan.note(f, "%s: text -> binary (the game started without it closing)" % p["id"])
    return plan


__all__ = ["problems", "fix_plan"]
