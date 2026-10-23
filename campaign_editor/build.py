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
    own = []                                                # the template's own strings (keys naming it)
    from .textio import parsed_once
    for path in mod.campaign_text_files(campaign):
        keys = parsed_once(_text_keys, mod.load(path))         # each table read once, then looked up
        own.extend(v for k, v in keys.items() if T in k)
        val = keys.get(T)
        if val is not None and "display_name" not in found:
            found["display_name"] = val
        val = keys.get("ST_" + T)
        if val is not None and "short_name" not in found:
            found["short_name"] = val
        val = keys.get("EMT_%s_SPY" % T)
        if val is not None and "adjective" not in found and val.endswith(" Spy"):
            found["adjective"] = val[:-4].strip()
        if "adjective" not in found:
            adj = _shared_adjective([keys.get("EMT_%s_%s" % (T, s)) for s in ADJECTIVE_LABELS])
            if adj:
                found["adjective"] = adj
    people = people_word(found)
    if people and any(re.search(r"\b%s\b" % re.escape(people), v) for v in own):     # a word its texts use
        found["people"] = people
    return found


def people_word(names):
    """The people's plural name copied texts may use beside the faction's names: 'Scots' of Scotland / Scottish -
    the stem the name and the adjective share (4 letters at least, shorter than both) with an s; None when they share
    none ('Gaul' / 'Gallic') - then no word of the template's people is looked for."""
    adj = (names.get("adjective") or "").strip()
    best = ""
    for key in ("short_name", "display_name"):
        name = (names.get(key) or "").strip().split(" of ")[-1].strip()
        n = 0
        while n < min(len(name), len(adj)) and name[n].lower() == adj[n].lower():
            n += 1
        if n > len(best) and n < len(name) and n < len(adj) and " " not in name[:n]:
            best = name[:n]
    return best + "s" if len(best) >= 4 else None


# the faction's own labels ({EMT_MAYANS_CITY} Mayan City): their first word(s) are the adjective - a mod may call the
# spy a Scout ({EMT_MAYANS_SPY} Mayan Scout, Medieval II's Americas), so 'X Spy' alone is not enough (report #192)
ADJECTIVE_LABELS = ("SPY", "ASSASSIN", "DIPLOMAT", "MERCHANT", "PRIEST", "PRINCESS", "ADMIRAL", "GENERAL",
                    "NAMED_GENERAL", "NAMED_CHARACTER", "FACTION_LEADER", "FACTION_HEIR", "CAPITAL", "CITY", "TOWN",
                    "VILLAGE", "LARGE_TOWN", "LARGE_CITY", "HUGE_CITY", "FISHING_VILLAGE", "PORT", "DOCK", "CASTLE",
                    "FORT", "FORTRESS", "WATCHTOWER")


def _shared_adjective(values):
    """The longest run of first words most of the labels share ('Mayan' of 'Mayan City', 'Mayan Scout'...) - at
    least 3 labels and more than half of them, and a word left after it in each; else None."""
    words = [v.split() for v in values if v and len(v.split()) > 1]
    best = None
    for n in range(1, 4):
        heads = {}
        for w in words:
            if len(w) > n:
                heads[tuple(w[:n])] = heads.get(tuple(w[:n]), 0) + 1
        top = max(heads.items(), key=lambda kv: kv[1], default=None)
        if not top or top[1] < 3 or top[1] * 2 <= len(words):
            break
        best = " ".join(top[0])
    return best


def _text_keys(f):
    """{KEY in capitals: its text} of a string table, the first line of each key."""
    out = {}
    rx = re.compile(r"\s*\{([A-Za-z0-9_]+)\}\s*(.*)$")
    for line in f.texts():
        m = rx.match(line)
        if m:
            out.setdefault(m.group(1).upper(), m.group(2).strip())
    return out


def display_names(mod, campaign=None):
    """{faction: the name players see} from the string tables this campaign reads ({ENGLAND} England) - a mod
    may keep the game's internal name and show another (Medieval II's names are hard-wired: 'turks' shown as
    'Ryazan'). Factions without a string are left out."""
    want = {n.upper(): n for n, _ in mod.factions()}
    found = {}
    for path in mod.campaign_text_files(campaign):
        for line in mod.load(path).texts():
            m = re.match(r"\s*\{([A-Za-z0-9_]+)\}\s*(.*)$", line)
            if m and m.group(1).upper() in want:
                name = want[m.group(1).upper()]
                if name not in found and m.group(2).strip():
                    found[name] = m.group(2).strip()
    return found


def faction_label(name, shown):
    """'turks - Ryazan' when the name players see is not the internal one ('england' / 'England',
    'turks' / 'The Turks' stay plain)."""
    if not shown:
        return name
    norm = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"^the\s+", "", s.strip().lower()))
    return name if norm(shown) == norm(name) else "%s - %s" % (name, shown)


def build(mod, campaign, template, new, opts):
    if not RE_NAME.match(new):
        raise ValueError("internal name must be lower case letters, digits and _ (like 'saba')")
    names = [n for n, _ in mod.factions()]
    # a faction of the mod (descr_sm_factions.txt) that is not in this campaign: brought INTO it - only the
    # campaign's part written (its block in descr_strat.txt: towns, family; victory, description, diplomacy), its
    # files kept as the mod has them (a tester, #341: it was refused as 'already exists' and could not be edited)
    into = new in names and not _in_campaign(mod, campaign, new)
    if new in names and not into:
        raise ValueError("a faction called '%s' already exists" % new)
    if template not in names or template == "slave":
        raise ValueError("pick an existing faction (not slave) as the template")
    opts = dict(opts)
    for k, v in template_display(mod, template, campaign).items():
        opts.setdefault("template_" + k, v)
    plan = Plan(mod, template, new, opts)
    plan.campaign = campaign
    if into:
        return _into_campaign(plan, campaign, opts)
    clone.sm_factions(plan)
    clone.sm_factions_json(plan)
    clone.faction_blocks(plan, "character", heads=("faction", "type"))
    clone.names(plan)
    if not opts.get("bring"):                    # brought from another mod: it owns its own units (factionbring)
        clone.edu_ownership(plan)
    clone.edb_factions(plan)
    if opts.get("from_zero") and opts.get("common_units", True) and not opts.get("bring"):
        # New faction > From zero: only the units its culture shares, not the template's own (Roster gives its own)
        from .fromzero import take_template_units
        take_template_units(plan, campaign, opts.get("culture") or mod.culture(template))
    clone.texture_lines(plan, "model_battle")
    clone.texture_lines(plan, "model_strat")
    from .modeldb import plan_add_faction
    plan_add_faction(plan, template, new)        # Medieval II: battle_models.modeldb (none in Rome)
    clone.faction_blocks(plan, "banners", heads=("faction",))
    clone.faction_blocks(plan, "lbc_db", heads=("faction",))
    clone.faction_blocks(plan, "offmap", braced=True)
    clone.medieval_lists(plan, campaign)          # Medieval II: banners, accents, one-liners, movies, music
    clone.building_battle(plan)
    if opts.get("copy_triggers", False):         # a clone is clean: none of the template's triggers (the user,
        # 2026-10-21: 'a clone is its colour, units, buildings, models, cards - no events, no triggers, nothing')
        clone.triggers(plan, "traits")
        clone.triggers(plan, "ancillaries")
    clone.win_conditions(plan, campaign)
    clone.text_strings(plan)
    clone.campaign_description(plan, campaign)
    clone.lookup_keys(plan)
    if opts.get("copy_art", True):
        clone.art_files(plan, campaign)
        clone.own_pictures(plan)
        clone.own_symbol(plan)
        from .symbols import give_own
        give_own(plan, new)              # its own flag symbol and faction logos (Rome)
    if opts.get("bring"):                        # a faction of another mod: its own units, names, figures, pictures
        from . import factionbring
        factionbring.overlay(plan, campaign, opts["bring"])
    clone.unit_cards(plan)
    # new regions first: a new region picked as a start town is then a region of the map
    # (a rebel village the new faction takes) - one Apply writes the map and the faction
    if opts.get("regions"):
        from .regionedit import apply_opts as apply_region_opts
        apply_region_opts(plan, campaign, opts["regions"])
    if opts.get("religion"):             # Medieval II: the clone's own religion (the template's is kept otherwise)
        from .religions import set_faction_religion
        set_faction_religion(plan, new, opts["religion"])
    if opts.get("accent"):               # Medieval II: the voice accent it speaks (the template's otherwise; a
        from .accents import accent_of, set_accent        # brought faction's own when this mod has it)
        if opts["accent"] not in (accent_of(mod, template), accent_of(plan, new)):
            set_accent(plan, new, opts["accent"])
    if opts.get("culture") and opts["culture"] != mod.culture(template):    # its own culture (the template's else)
        from .culture import set_faction_culture
        set_faction_culture(plan, new, opts["culture"])
    build_start(plan, campaign, opts["start"])
    if opts.get("places"):
        from .mapedit import apply_places
        apply_places(plan, campaign, opts["places"], (opts.get("regions") or {}).get("painted"))
    if opts.get("resources"):
        from .resources import apply as apply_resources
        apply_resources(plan, campaign, opts["resources"])
    if opts.get("relations"):
        from .diplomacy import apply_opts
        apply_opts(plan, campaign, new, opts["relations"])
    if opts.get("victory"):
        from .wincond import apply_opts as apply_victory
        apply_victory(plan, campaign, new, opts["victory"], opts)
    if opts.get("figures") or opts.get("figures_like"):   # before the art: a new texture line may get a picture
        from .stratmodels import apply as apply_figures
        apply_figures(plan, new, opts["figures"], opts.get("figures_like"))
    from .factionart import apply_opts as apply_art
    try:
        primary = opts.get("primary_colour") or tuple(
            __import__("campaign_editor.edit", fromlist=["x"]).read_faction(mod, campaign, template).get("primary_colour") or ())
    except Exception:
        primary = None
    apply_art(plan, campaign, new, list(opts["start"].get("regions") or []), primary,
              towns_changed=opts.get("copy_art", True), own_map=opts.get("copy_art", True))
    from .traces import plan_note
    plan_note(plan)
    validate(plan, campaign)
    return plan


def _in_campaign(mod, campaign, faction):
    path = mod.campaign_file(campaign, "descr_strat.txt")
    return bool(path) and Strat(mod.load(path)).faction(faction) is not None


def _into_campaign(plan, campaign, opts):
    """build() for a faction the mod has already: the campaign's files only - the template lends its start (the
    family and armies are made for the faction, build_start), its victory and description lines."""
    new = plan.new
    wc = plan.mod.campaign_file(campaign, "descr_win_conditions.txt")
    if not wc or not any(strip_comment(l).strip() == new and not l[:1].isspace() for l in plan.mod.load(wc).texts()):
        clone.win_conditions(plan, campaign)         # (a mod may hold its victory already)
    clone.campaign_description(plan, campaign)
    if opts.get("regions"):
        from .regionedit import apply_opts as apply_region_opts
        apply_region_opts(plan, campaign, opts["regions"])
    build_start(plan, campaign, opts["start"])
    if opts.get("places"):
        from .mapedit import apply_places
        apply_places(plan, campaign, opts["places"], (opts.get("regions") or {}).get("painted"))
    if opts.get("resources"):
        from .resources import apply as apply_resources
        apply_resources(plan, campaign, opts["resources"])
    if opts.get("relations"):
        from .diplomacy import apply_opts
        apply_opts(plan, campaign, new, opts["relations"])
    if opts.get("victory"):
        from .wincond import apply_opts as apply_victory
        apply_victory(plan, campaign, new, opts["victory"], opts)
    plan.note(plan.edit(plan.mod.campaign_file(campaign, "descr_strat.txt")),
              "%s is a faction of the mod already: brought into the campaign %s - its own files (descr_sm_factions, "
              "units, names, pictures) stay as they are" % (new, campaign))
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
    from .strat import fix_names
    fix_names(plan, strat_path, Strat(TextFile.load(strat_path)))
    s = Strat(f)
    seen = {}
    for fb in s.factions:
        for st in fb.settlements:
            if st.region in seen:
                plan.warn(f, "%s has two settlement blocks (%s and %s)" % (st.region, seen[st.region], fb.name))
            seen[st.region] = fb.name
    # units in the new block exist in export_descr_unit
    edu = plan.files.get(mod.file("edu")) or mod.load(mod.file("edu"))      # (not edited: a faction brought in)
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
    sm = plan.files.get(mod.file("sm_factions")) or mod.load(mod.file("sm_factions"))
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
    from .limits import check as check_limit
    check_limit(plan, count)                       # REX / M2EX: max_factions raised in the same plan
