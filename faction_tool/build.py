"""Putting a new faction together from a template, and checking the result."""

import re

from . import clone
from .plan import Plan
from .start import build_start
from .strat import Strat
from .textio import TextFile, strip_comment, tokens

RE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def template_display(mod, template, campaign=None):
    """Guess the template's display strings from data/text: full name, short name,
    adjective - from the tables this campaign reads (not another campaign's)."""
    T = template.upper()
    found = {}
    for path in mod.campaign_text_files(campaign):
        f = mod.load(path)
        for line in f.texts():
            m = re.match(r"\s*\{([A-Za-z0-9_]+)\}\s*(.*)$", line)
            if not m:
                continue
            key, val = m.group(1).upper(), m.group(2).strip()
            if key == T and "display_name" not in found:
                found["display_name"] = val
            elif key == "ST_" + T and "short_name" not in found:
                found["short_name"] = val
            elif key == "EMT_%s_SPY" % T and "adjective" not in found and val.endswith(" Spy"):
                found["adjective"] = val[:-4].strip()
    return found


def build(mod, campaign, template, new, opts):
    if not RE_NAME.match(new):
        raise ValueError("internal name must be lower case letters, digits and _ (like 'saba')")
    names = [n for n, _ in mod.factions()]
    if new in names:
        raise ValueError("a faction called '%s' already exists" % new)
    if template not in names or template == "slave":
        raise ValueError("pick an existing faction (not slave) as the template")
    opts = dict(opts)
    for k, v in template_display(mod, template, campaign).items():
        opts.setdefault("template_" + k, v)
    plan = Plan(mod, template, new, opts)
    plan.campaign = campaign
    clone.sm_factions(plan)
    clone.sm_factions_json(plan)
    clone.faction_blocks(plan, "character", heads=("faction", "type"))
    clone.names(plan)
    clone.edu_ownership(plan)
    clone.edb_factions(plan)
    clone.texture_lines(plan, "model_battle")
    clone.texture_lines(plan, "model_strat")
    clone.faction_blocks(plan, "banners", heads=("faction",))
    clone.faction_blocks(plan, "lbc_db", heads=("faction",))
    clone.faction_blocks(plan, "offmap", braced=True)
    clone.building_battle(plan)
    if opts.get("copy_triggers", True):
        clone.triggers(plan, "traits")
        clone.triggers(plan, "ancillaries")
    clone.win_conditions(plan, campaign)
    clone.text_strings(plan)
    clone.campaign_description(plan, campaign)
    clone.lookup_keys(plan)
    if opts.get("copy_art", True):
        clone.art_files(plan, campaign)
        clone.own_pictures(plan)
    clone.unit_cards(plan)
    # new regions first: a new region picked as a start town is then a region of the map
    # (a rebel village the new faction takes) - one Apply writes the map and the faction
    if opts.get("regions"):
        from .regionedit import apply_opts as apply_region_opts
        apply_region_opts(plan, campaign, opts["regions"])
    build_start(plan, campaign, opts["start"])
    if opts.get("places"):
        from .mapedit import apply_places
        apply_places(plan, campaign, opts["places"])
    if opts.get("resources"):
        from .resources import apply as apply_resources
        apply_resources(plan, campaign, opts["resources"])
    if opts.get("relations"):
        from .diplomacy import apply_opts
        apply_opts(plan, campaign, new, opts["relations"])
    from .factionart import apply_opts as apply_art
    try:
        primary = opts.get("primary_colour") or tuple(
            __import__("faction_tool.edit", fromlist=["x"]).read_faction(mod, campaign, template).get("primary_colour") or ())
    except Exception:
        primary = None
    apply_art(plan, campaign, new, list(opts["start"].get("regions") or []), primary,
              towns_changed=opts.get("copy_art", True))
    validate(plan, campaign)
    return plan


def validate(plan, campaign):
    """Checks that catch the crashes we have met: duplicate settlements, broken
    braces, unknown units, faction counts that disagree between files."""
    mod, new = plan.mod, plan.new
    strat_path = mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.files[strat_path]
    depth = 0
    for l in f.texts():
        s = strip_comment(l)
        depth += s.count("{") - s.count("}")
    if depth != 0:
        plan.warn(f, "braces do not balance (%+d)" % depth)
    s = Strat(f)
    from .strat import characters_after_tree
    for name in characters_after_tree(s):
        raise ValueError("internal check failed - a character would follow the family tree of %s "
                         "(the game crashes on that); nothing written" % name)
    from .strat import check_names
    check_names(Strat(TextFile.load(strat_path)), s)
    seen = {}
    for fb in s.factions:
        for st in fb.settlements:
            if st.region in seen:
                plan.warn(f, "%s has two settlement blocks (%s and %s)" % (st.region, seen[st.region], fb.name))
            seen[st.region] = fb.name
    # units in the new block exist in export_descr_unit
    edu = plan.files.get(mod.file("edu"))
    known, mercs = set(), set()        # mercenaries are hired, never recruited: no warning
    owners = {}
    cur = None
    for l in edu.texts():
        t = tokens(l)
        if t[:1] == ["type"]:
            cur = " ".join(strip_comment(l).split()[1:])
            known.add(cur)
        elif t[:1] == ["ownership"] and cur:
            owners[cur] = set(t[1:])
        elif t[:1] == ["attributes"] and cur and "mercenary_unit" in l:
            mercs.add(cur)
    fb = s.faction(new)
    bad, foreign = [], []
    for c in fb.characters:
        for l in s.lines[c.start:c.end]:
            if tokens(l)[:1] == ["unit"]:
                from .start import unit_name
                u = unit_name(l)
                if u not in known:
                    bad.append(u)
                elif u not in mercs and not owners.get(u, set()) & {new, "all", mod.culture(new)}:
                    foreign.append(u)
    if bad:
        plan.warn(f, "unknown unit type(s) in %s's armies: %s" % (new, ", ".join(sorted(set(bad)))))
    if foreign:
        plan.warn(f, "%s does not own these garrison units (they stay, but it cannot recruit them): %s"
                  % (new, ", ".join(sorted(set(foreign)))))
    # every file that lists factions by block agrees on the count
    sm = plan.files[mod.file("sm_factions")]
    count = sum(1 for l in sm.texts() if tokens(l)[:1] == ["faction"])
    ch = plan.files.get(mod.file("character"))
    if ch is not None:
        per_type = {}
        cur = None
        for l in ch.texts():
            t = tokens(l)
            if t[:1] == ["type"]:
                cur = " ".join(t[1:])
            elif t[:1] == ["faction"] and cur:
                per_type.setdefault(cur, 0)
                per_type[cur] += len(t) - 1
        for k, v in per_type.items():
            if v > count:
                plan.warn(ch, "character type '%s' lists %d factions, more than the %d factions" % (k, v, count))
    plan.faction_count = count
    if count > 31:
        plan.warn(sm, "%d factions (slave included). Classic RTW stops at 31; REX lifts the faction limit "
                      "(its README) - fine under REX, test a new campaign" % count)
