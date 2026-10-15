"""One Recruitment Grid - a Medieval II add-on that changes the mod's own file (the user, 2026-10-15: on the Add-ons
page, not in Campaign rules): descr_campaign_db.xml <recruitment_sort_simple> set to true, so a town's recruitment
panel is one grid read row by row, as in Rome, instead of the game's blocks by kind (infantry, missiles, cavalry...).
Any Medieval II, no engine needed. What the line said before is kept in CampaignEditor_onegrid.json beside the file,
so Take it out puts it back; a mod that had no file of its own gets the game's copy (the other settings switched
off, as Campaign rules does) and loses it again on Take it out. The game itself puts agents first, then ships, in
that grid (the engine source: its recruit list is sorted by kind before price) - only an engine change moves them."""

import json
import os

NAME = "descr_campaign_db.xml"
KEY = "recruitment_sort_simple"
MARK = "CampaignEditor_onegrid.json"


def _rule(mod):
    """(the rule, the mod's own file or None, the game's file or None)."""
    from . import campaignrules as CR
    for name, _title, own, base in CR.files(mod):
        if name.lower() == NAME:
            src = own or base
            rule = next((r for r in CR.read(src) if r.key == KEY), None)
            if rule is None:
                raise ValueError("%s has no <%s> line" % (NAME, KEY))
            return rule, own, base
    raise ValueError("this mod and its game have no %s (Medieval II only)" % NAME)


def mark_path(mod):
    return os.path.join(mod.data, MARK)


def installed(mod):
    """{} when the add-on is in this mod, else None."""
    return {} if os.path.isfile(mark_path(mod)) else None


def plan_install(plan):
    from . import campaignrules as CR
    mod = plan.mod
    if installed(mod) is not None:
        raise ValueError("One Recruitment Grid is in this mod already")
    rule, own, base = _rule(mod)
    plan.binary(mark_path(mod), (json.dumps({"was": rule.value, "own_file": bool(own)}, indent=1) + "\n")
                .encode("utf-8"))
    if rule.value.strip().lower() == "true":
        plan.note(None, "%s: %s is true already - the panel is one grid; kept as it is" % (NAME, KEY))
        return
    CR.apply(plan, NAME, {rule: "true"}, own, base)


def plan_remove(plan):
    from . import campaignrules as CR
    mod = plan.mod
    try:
        with open(mark_path(mod), encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        raise ValueError("One Recruitment Grid is not in this mod")
    rule, own, base = _rule(mod)
    plan.delete(mark_path(mod), "the One Recruitment Grid note")
    if own and not rec.get("own_file", True):
        plan.delete(own, "%s: the copy One Recruitment Grid put in - the game's own settings hold again" % NAME)
        return
    was = str(rec.get("was", "false"))
    if rule.value.strip().lower() != was.strip().lower():
        CR.apply(plan, NAME, {rule: was}, own, base)
