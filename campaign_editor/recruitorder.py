"""The recruitment panel in a sensible order (the user, 2026-10-14: 'the strongest units come first - the top left
corner of the panel takes the strongest, or simply the dearest; by kind: infantry first, then missiles - skirmishers,
archers -, then cavalry, then siege, and only then ships').

The game lists a town's units in the order of the recruit lines of export_descr_buildings.txt (the Medieval 2 GUI
Toolkit's notes: 'the order the game's recruitment panel lists units in'). So the lines are sorted once in the file
and every town, every unit added later and old saves follow it - no script runs in the game. Inside each building
level's capability block only the recruit lines change places, among the slots they held; every other line (agents,
bonuses, retrain lines, comments of their own) stays where it is, and each recruit line moves with its own comment.
How the game joins the lists of SEVERAL buildings of one town (barracks, stables, a range) is not known for sure -
the order inside each building is what this sets."""

from .editors import building_blocks, chain_tree
from .roster import RECRUITING, recruit_of

# the kinds in the order the panel shows them (missile infantry is infantry of class missile or skirmish)
KIND_ORDER = ("infantry", "missiles", "handlers", "cavalry", "siege", "ships", "non-combatants", "other")
KIND_WORDS = {"infantry": "infantry", "missiles": "missiles (archers, slingers, skirmishers)",
              "handlers": "animal handlers", "cavalry": "cavalry", "siege": "siege", "ships": "ships",
              "non-combatants": "non-combatants", "other": "units the unit file lacks"}


def unit_facts(edu):
    """{unit type (lower case): (kind, cost)} of an export_descr_unit.txt (TextFile)."""
    from .packs import _block_lines, _values, type_blocks
    out = {}
    for name, span in type_blocks(edu).items():
        lines = _block_lines(edu, span)

        def first(key):
            got = _values(lines, key)
            return [x.lower() for x in got[0]] if got else []
        cat = (first("category") or [""])[0]
        cls = (first("class") or [""])[0]
        if cat == "infantry":
            kind = "missiles" if cls in ("missile", "skirmish") else "infantry"
        elif cat == "handler":
            kind = "handlers"
        elif cat == "cavalry":
            kind = "cavalry"
        elif cat == "siege":
            kind = "siege"
        elif cat == "ship":
            kind = "ships"
        elif cat == "non_combatant":
            kind = "non-combatants"
        else:
            kind = "other"
        cost = first("stat_cost")
        try:
            price = int(float(cost[1]))
        except (IndexError, ValueError):
            price = 0
        out[name.lower()] = (kind, price)
    return out


def sort_key(facts, unit):
    """The panel's order: the kind (KIND_ORDER), then the dearest first, then the name."""
    kind, price = facts.get(unit.lower(), ("other", 0))
    return (KIND_ORDER.index(kind), -price, unit.lower())


def sorted_edb(edb, edu):
    """Put the recruit lines of every level of edb (TextFile, changed in place) in the panel's order.
    -> [(chain, level, [units in the new order])] of the levels whose order changed."""
    facts = unit_facts(edu)
    changed = []
    for chain, start, end in building_blocks(edb):
        for lv in chain_tree(edb, start, end)["levels"]:
            cap = lv["capability"]
            if not cap:
                continue
            slots = [i for i in range(cap[0] + 1, cap[1]) if recruit_of(edb.text(i), RECRUITING)]
            if len(slots) < 2:
                continue
            lines = [(recruit_of(edb.text(i), RECRUITING)[1], edb.raw[i]) for i in slots]
            want = sorted(lines, key=lambda u: sort_key(facts, u[0]))
            if [u for u, _ in want] == [u for u, _ in lines]:
                continue
            for i, (_, raw) in zip(slots, want):
                edb.raw[i] = raw
            changed.append((chain, lv["name"], [u for u, _ in want]))
    return changed


def plan_sort(plan):
    """The sort in a plan (Preview, Keep for Apply, one backup, Restore byte-exact). -> the changed levels."""
    mod = plan.mod
    if not mod.file("edb") or not mod.file("edu"):
        raise ValueError("this mod has no export_descr_buildings.txt or export_descr_unit.txt")
    edb = plan.edit(mod.file("edb"))
    changed = sorted_edb(edb, mod.load(mod.file("edu")))
    for chain, level, units in changed:
        plan.note(edb, "%s / %s: the recruitment panel in order - %s" % (chain, level, ", ".join(units)))
    if changed:
        plan.note(None, "Recruit lines sorted in %d building level(s): %s, the dearest first in each kind - the "
                        "panel's top left takes the strongest" % (
                            len(changed), " -> ".join(KIND_WORDS[k] for k in KIND_ORDER[:6])))
    return changed

