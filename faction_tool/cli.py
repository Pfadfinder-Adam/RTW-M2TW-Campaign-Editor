"""Command line: describe the faction in a JSON file, preview, apply, restore.

    python -m faction_tool new  saba.json --data "C:/Games/RTW/HLR/data" [--apply]
    python -m faction_tool list --data ...            factions, campaigns, backups
    python -m faction_tool towns --data ... [--campaign imperial_campaign] [--owner slave]
    python -m faction_tool names --data ... parthia   the name lists a leader can use
    python -m faction_tool restore --data ... [backup folder]
"""

import argparse
import json
import sys

from .build import build
from .moddata import ModData
from .plan import backups, restore
from .strat import Strat

EXAMPLE = {
    "campaign": "imperial_campaign",
    "template": "parthia",
    "name": "saba",
    "display_name": "Sabaean Kingdom",
    "short_name": "Saba",
    "adjective": "Sabaean",
    "description": "",
    "long_description": "",
    "primary_colour": [150, 90, 23],
    "secondary_colour": [220, 194, 166],
    "copy_triggers": True,
    "copy_art": True,
    "start": {
        "regions": ["Mariba_R", "Sanaa_R", "Sapphar_R"],
        "capital": "Mariba_R",
        "leader": {"name": "Pacorus Arsacid", "age": 45},
        "heir": {"name": "Oxynta Arsacid", "age": 22},
        "denari": 6000,
        "playable": True,
        "diplomacy": "neutral",
        "army_mode": "balanced",
        "garrison": "replace"
    }
}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="faction_tool", description="Add a new faction to a Rome: Total War mod.")
    ap.add_argument("command", choices=["new", "list", "towns", "names", "restore", "example"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--data", help="the mod's data folder (or the mod folder)")
    ap.add_argument("--campaign", default="imperial_campaign")
    ap.add_argument("--owner", help="towns: only this owner")
    ap.add_argument("--apply", action="store_true", help="new: write the changes (default: preview only)")
    a = ap.parse_intermixed_args(argv)

    if a.command == "example":
        print(json.dumps(EXAMPLE, indent=2))
        return 0
    if not a.data:
        ap.error("--data is required")
    mod = ModData(a.data)

    if a.command == "list":
        print("data folder:", mod.data)
        print("campaigns:  ", ", ".join(mod.campaigns()))
        print("factions:   ", ", ".join(n for n, _ in mod.factions()))
        for b in backups(mod):
            print("backup:     ", b)
        return 0
    if a.command == "towns":
        strat = Strat(mod.load(mod.campaign_file(a.campaign, "descr_strat.txt")))
        regions = mod.regions(a.campaign)
        for region, owner in sorted(strat.owners().items(), key=lambda x: (x[1], x[0])):
            if a.owner and owner != a.owner:
                continue
            print("%-24s %-24s %s" % (region, regions.get(region, {}).get("settlement", "?"), owner))
        return 0
    if a.command == "names":
        pool = mod.name_pool(a.arg)
        for k in ("characters", "surnames"):
            print("%s (%d):" % (k, len(pool.get(k, []))))
            print("   " + ", ".join(pool.get(k, [])))
        return 0
    if a.command == "restore":
        target = a.arg or (backups(mod) or [None])[0]
        if not target:
            print("no backup to restore")
            return 1
        m = restore(mod, target)
        print("restored %d file(s), removed %d created, from %s" % (len(m["modified"]), len(m["created"]), target))
        return 0

    with open(a.arg, encoding="utf-8") as f:
        cfg = json.load(f)
    opts = {k: v for k, v in cfg.items() if k not in ("campaign", "template", "name")}
    plan = build(mod, cfg.get("campaign", a.campaign), cfg["template"], cfg["name"], opts)
    print(plan.report())
    if a.apply:
        print("\nbackup written to", plan.apply())
    else:
        print("\n(preview only - add --apply to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
