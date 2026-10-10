"""Factions that appear later: emergent, shadow and split-off factions, both games (Barbarian Invasion's, REX's and
Medieval II's engines all read these words; vanilla RomeTW.exe knows them too).

How a faction comes into the campaign is written in three files:

    descr_sm_factions.txt   the header line of its block, after a comma:
        faction slavs, spawned_on_event                  appears by an event (descr_events.txt)
        faction empire_east, shadowed_by empire_east_rebels
        faction empire_east_rebels, shadowing empire_east   its shadow: the side that splits off in a civil war
        faction goths, spawns_on_revolt ostrogoths
        faction ostrogoths, spawned_by goths             split off from goths when goths' towns revolt
    descr_strat.txt         its block holds `dead_until_resurrected` (+ `re_emergent`: may come back after it dies),
                            its money and no towns, no characters (BI: ostrogoths, romano_british, slavs, the
                            empires' rebels; Medieval II: mongols, timurids)
    descr_events.txt        `event emergent_faction slavs` / `date 47 summer` / `region Locus_Barbaricum` - BI's own
                            comment: 'this faction must be marked as emergent in descr_strat.txt'; a list of regions
                            or of positions below the date (both games' comments say so). Medieval II's own
                            Mongols / Timurids are woken by the campaign script instead (shown, not changed).

WAYS: 'map' (there from the start), 'event', 'shadow' (of a faction), 'revolt' (splits off a faction)."""

import re

from .textio import strip_comment, tokens

WAYS = ("map", "event", "shadow", "revolt")
# the words on a header line: the faction's own way in, and the word its partner gets
RE_TIE = re.compile(r"\s*,\s*(shadowed_by|shadowing|spawned_by|spawns_on_revolt)\s+([A-Za-z0-9_]+)"
                    r"|\s*,\s*(spawned_on_event)\b")
PARTNER = {"shadowing": "shadowed_by", "spawned_by": "spawns_on_revolt",
           "shadowed_by": "shadowing", "spawns_on_revolt": "spawned_by"}
OWN_WORD = {"shadow": "shadowing", "revolt": "spawned_by"}       # the way -> the word on the faction's own line
DEAD_WORDS = ("dead_until_resurrected", "re_emergent")
# ONE faction with a shadow AND a faction splitting off it (in the games, checked by the in-game tester):
#   plain Rome with REX - crashes at the end of a turn (SETTLEMENT::get_revolt_type): refused;
#   Medieval II with M2EX, Barbarian Invasion with REX - no crash, but every revolting town goes to the SHADOW, so the
#   split-off faction never comes: allowed, with that said in Preview.
BOTH_TIES = ("%s already has %s as %s - plain Rome crashes at the end of a turn with both on one faction: pick "
             "another faction")
BOTH_NOTE = ("%s has both a shadow and a faction splitting off it: the game takes it (Medieval II with M2EX and "
             "Barbarian Invasion with REX, no crash), but every town of %s that revolts goes to the shadow - the "
             "split-off faction never comes while the shadow is there")
# Medieval II brings a faction that comes by an event in as a HORDE (the Mongols' and Timurids' way): the engine stops
# when its descr_sm_factions block has no horde lines - 'ASSERT FAILED: faction.cpp: can_horde()', 'horde.cpp: ...
# m_horde_unit_resource_ids.empty()' (a tester's game with M2EX: the faction never came). The Mongols' own numbers:
HORDE = (("horde_min_units", "10"), ("horde_max_units", "20"), ("horde_max_units_reduction_every_horde", "10"),
         ("horde_unit_per_settlement_population", "250"), ("horde_min_named_characters", "2"),
         ("horde_max_percent_army_stack", "80"), ("horde_disband_percent_on_settlement_capture", "0"))
HORDE_UNITS = 6


# Factions that come later are Barbarian Invasion's: plain Rome (also with REX) cannot take them. A shadow + a split-off
# faction crashed it at the end of a turn, and its descr_strat.txt reader STOPS at a faction that starts dead
# (dead_until_resurrected, the in-game tester's proof 2026-10-07: the rebels' garrisons, the diplomacy and every faction
# after it were lost, no error written). Medieval II keeps them all (its engine is BI's; tried in the game with M2EX).
BI_ONLY = ("event", "shadow", "revolt")
NOT_ROME = ("only Barbarian Invasion and Medieval II take a faction that comes later - plain Rome, also with REX, "
            "stops reading descr_strat.txt at a faction that starts dead (the rebels' garrisons, the diplomacy and "
            "every faction after it are lost) and crashes at the end of a turn with a shadow and a split-off faction")
DEAD_ROME = ("plain Rome (also with REX) stops reading descr_strat.txt at 'dead_until_resurrected': the rebels' "
             "garrisons, the diplomacy and every faction after it are lost, with no error in the log - only Barbarian "
             "Invasion and Medieval II read it")


def _ci_file(folder, name):
    from .moddata import _ci
    return _ci(folder, name)


def is_bi(mod):
    """Whether a Rome mod is Barbarian Invasion's: its data under a 'bi' folder, or factions already tied the BI way
    (shadowed_by / spawns_on_revolt in descr_sm_factions)."""
    import os
    parts = [x.lower() for x in os.path.normpath(mod.data).split(os.sep)]
    if "bi" in parts or _ci_file(mod.data, "descr_beliefs.txt"):     # BI's own file (beliefs)
        return True
    try:
        return any(t.get(w) for t in ties(mod).values() for w in ("shadowed_by", "spawns_on_revolt", "shadowing",
                                                                   "spawned_by"))
    except Exception:
        return False


def plain_rome(mod):
    """Rome that is not Barbarian Invasion (also with REX): no faction that comes later."""
    from .limits import game_kind
    return game_kind(mod) == "rome" and not is_bi(mod)


def ways_for(mod):
    """The ways in this mod's game takes: all on Medieval II and Barbarian Invasion, plain Rome only 'map'."""
    from .limits import game_kind
    if game_kind(mod) == "rome" and not is_bi(mod):
        return tuple(w for w in WAYS if w not in BI_ONLY)
    return WAYS


def both_ties(mod):
    """[(faction, shadow, split)] of the factions that carry both shadowed_by and spawns_on_revolt."""
    return [(fac, t["shadowed_by"], t["spawns_on_revolt"]) for fac, t in ties(mod).items()
            if t.get("shadowed_by") and t.get("spawns_on_revolt")]


def describe(way, of=None, short=False):
    """The way in plain words (short: for a table)."""
    if short:
        return {"map": "on the map from the start", "event": "by an event", "shadow": "shadow of %s (civil war)" % of,
                "revolt": "splits off %s in a revolt" % of}.get(way, way)
    return {"map": "on the map from the start",
            "event": "appears later, by an event (a date and a region in descr_events.txt)",
            "shadow": "the shadow of %s: the side that splits off %s in a civil war" % (of, of),
            "revolt": "splits off %s when towns of %s revolt" % (of, of)}.get(way, way)


HOW = ("A faction that appears later starts dead: no towns, no characters, only its money; the engine brings it in. "
       "By an event: on the date the faction rises in the region with an army of its own (Barbarian Invasion's "
       "Slavs). The shadow of a faction: the side that splits off it in a civil war (Barbarian Invasion's rebels of "
       "the two Roman empires). Splits off in a revolt: towns of the other faction that revolt go to it (Barbarian "
       "Invasion's Ostrogoths split off the Goths). 'May come back' (re_emergent): after it dies it can rise again. "
       "Barbarian Invasion's, REX's and Medieval II's engines read these words; plain Rome (also with REX) does not: "
       "a faction that starts dead stops its reading of descr_strat.txt.")


def ties(mod):
    """{faction: {word: partner or True}} - every tie word on the header lines of descr_sm_factions.txt."""
    return _ties_in(mod.load(mod.file("sm_factions")))


def _ties_in(f):
    out = {}
    for i in range(len(f)):
        t = tokens(f.text(i))
        if t[:1] != ["faction"] or len(t) < 2:
            continue
        fac, text = t[1], f.text(i)
        got = {}
        for m in RE_TIE.finditer(strip_comment(text)):
            if m.group(3):
                got["spawned_on_event"] = True
            else:
                got[m.group(1)] = m.group(2)
        out[fac] = got
    return out


def way_of(mod, faction, tie=None):
    """(way, partner or None): how the faction comes into the campaign by descr_sm_factions.txt."""
    t = (ties(mod) if tie is None else tie).get(faction) or {}
    if t.get("shadowing"):
        return "shadow", t["shadowing"]
    if t.get("spawned_by"):
        return "revolt", t["spawned_by"]
    if t.get("spawned_on_event"):
        return "event", None
    return "map", None


def strat_state(mod, campaign):
    """{faction: {'dead', 're_emergent', 'towns', 'people'}} of descr_strat.txt's blocks."""
    from .strat import Strat
    s = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
    out = {}
    for fb in s.factions:
        head = set()
        for i in range(fb.start + 1, fb.end):
            t = tokens(s.lines[i])
            if not t:
                continue
            if t[0] in ("settlement", "character", "character_record", "relative") or t[0].startswith("{"):
                break
            head.add(t[0])
        out[fb.name] = {"dead": "dead_until_resurrected" in head, "re_emergent": "re_emergent" in head,
                        "towns": len(fb.settlements), "people": len(fb.characters)}
    return out


def emergent_events(mod, campaign):
    """{faction: event} of the campaign's `event emergent_faction <faction>` lines (events.read's dicts)."""
    from . import events as EV
    path = EV.path_of(mod, campaign)
    if not path:
        return {}
    return {e["name"]: e for e in EV.read(mod.load(path)) if e["kind"] == "emergent_faction"}


def later_rows(mod, campaign):
    """[{'faction', 'way', 'of', 'dead', 're_emergent', 'towns', 'event', 'script'}] of every faction that does not
    simply start on the map (a tie word, dead at the start, or an emergent_faction event) - for the Events window."""
    from .events import later_factions
    tie = ties(mod)
    state = strat_state(mod, campaign)
    evs = emergent_events(mod, campaign)
    script = dict(later_factions(mod, campaign))
    out = []
    for fac in state:
        if fac == "slave":
            continue
        way, of = way_of(mod, fac, tie)
        st = state[fac]
        if way == "map" and not st["dead"] and fac not in evs:
            continue
        out.append({"faction": fac, "way": way, "of": of, "dead": st["dead"], "re_emergent": st["re_emergent"],
                    "towns": st["towns"] + st["people"], "event": evs.get(fac), "script": script.get(fac) or []})
    return out


# ---------------------------------------------------------------------------- writing
def set_way(plan, faction, way, of=None, both_ok=False):
    """descr_sm_factions.txt: the faction's own way in (its header line) and its partner's word; the faction's old
    way and any partner word naming it go. Refused: a partner that is the faction itself / unknown / already has a
    shadow (or a split-off faction) of its own."""
    if way not in WAYS:
        raise ValueError("unknown way '%s'" % way)
    mod = plan.mod
    if way not in ways_for(mod):
        raise ValueError("%s cannot come in as %s: %s" % (faction, describe(way, of or "another faction"), NOT_ROME))
    f = plan.edit(mod.file("sm_factions"))
    heads = [(i, tokens(f.text(i))[1]) for i in range(len(f))
             if tokens(f.text(i))[:1] == ["faction"] and len(tokens(f.text(i))) > 1]
    names = [n for _, n in heads]
    if faction not in names:
        raise ValueError("descr_sm_factions.txt has no faction %s" % faction)
    if way in ("shadow", "revolt"):
        if not of or of not in names:
            raise ValueError("pick the faction %s %s" % (faction, "is the shadow of" if way == "shadow" else
                                                         "splits off"))
        if of in (faction, "slave"):
            raise ValueError("%s cannot be %s" % (faction, "its own shadow" if of == faction else
                                                  "the rebels' (slave) %s" % way))
        partner_word = PARTNER[OWN_WORD[way]]
        line = f.text(dict((n, i) for i, n in heads)[of])         # the plan's copy: earlier changes count
        m = re.search(r",\s*%s\s+([A-Za-z0-9_]+)" % partner_word, strip_comment(line))
        has = m.group(1) if m else None
        if has and has != faction:
            raise ValueError("%s already has %s: %s - one per faction" % (
                of, "a shadow" if way == "shadow" else "a faction splitting off it", has))
        other = PARTNER[OWN_WORD["revolt" if way == "shadow" else "shadow"]]
        m = re.search(r",\s*%s\s+([A-Za-z0-9_]+)" % other, strip_comment(line))
        if m and m.group(1) != faction:
            if plain_rome(mod) and not both_ok:
                raise ValueError(BOTH_TIES % (of, m.group(1), "a shadow" if way == "revolt" else
                                              "a faction splitting off it"))
            plan.warn(f, BOTH_NOTE % (of, of))

    if way_of(mod, faction, _ties_in(f)) == (way, of if way in ("shadow", "revolt") else None):
        return                                      # already so: nothing to change

    def cut(i, keep=lambda word, who: False):
        text = f.text(i)
        code, rest = text, ""
        k = text.find(";")
        if k >= 0:
            code, rest = text[:k], text[k:]
        out = RE_TIE.sub(lambda m: m.group(0) if keep(m.group(1) or m.group(3), m.group(2)) else "", code)
        if out != code:
            f.set(i, out.rstrip() + ((" " + rest) if rest else ""))
            return True
        return False

    for i, n in heads:                              # the faction's own way in; partners' words naming it
        if n == faction:
            if cut(i, keep=lambda word, who: word in ("shadowed_by", "spawns_on_revolt")):
                plan.note(f, "%s: its old way in removed" % faction)
        elif cut(i, keep=lambda word, who: not (word in ("shadowed_by", "spawns_on_revolt") and who == faction)):
            plan.note(f, "%s: no longer names %s" % (n, faction))

    def add(i, words):
        text = f.text(i)
        k = text.find(";")
        code, rest = (text[:k], text[k:]) if k >= 0 else (text, "")
        f.set(i, code.rstrip() + ", " + words + ((" " + rest) if rest else ""))

    at = dict((n, i) for i, n in heads)
    if way == "event":
        add(at[faction], "spawned_on_event")
    elif way in ("shadow", "revolt"):
        add(at[faction], "%s %s" % (OWN_WORD[way], of))
        add(at[of], "%s %s" % (PARTNER[OWN_WORD[way]], faction))
    plan.note(f, "%s: %s" % (faction, describe(way, of)))


def set_dead(plan, campaign, faction, dead, re_emergent=False):
    """descr_strat.txt: the faction's block starts dead (dead_until_resurrected [+ re_emergent]) or alive. A dead
    faction must hold no towns and no characters - refused otherwise."""
    from .strat import Strat
    f = plan.edit(plan.mod.campaign_file(campaign, "descr_strat.txt"))
    s = Strat(f)
    fb = s.faction(faction)
    if not fb:
        raise ValueError("descr_strat.txt has no block for %s" % faction)
    if dead and plain_rome(plan.mod):
        raise ValueError("%s cannot start dead: %s" % (faction, DEAD_ROME))
    if dead and (fb.settlements or fb.characters):
        raise ValueError("%s holds %d town(s) and %d character(s) - a faction that appears later starts with none; "
                         "give them to others first" % (faction, len(fb.settlements), len(fb.characters)))
    gone = [i for i in range(fb.start + 1, fb.end) if tokens(f.text(i))[:1] and tokens(f.text(i))[0] in DEAD_WORDS]
    for i in reversed(gone):
        f.delete(i, i + 1)
    if dead:
        # after superfaction / ai_label, before denari - the games' own order (strat.HEADER_RANK)
        from .strat import header_rank
        at = fb.start + 1
        while at < fb.end and tokens(strip_comment(f.text(at)))[:1] and header_rank(f.text(at)) < 1 and \
                tokens(strip_comment(f.text(at)))[0] in ("superfaction", "ai_label"):
            at += 1
        f.insert(at, ["dead_until_resurrected"] + (["re_emergent"] if re_emergent else []))
    plan.note(f, "%s: %s" % (faction, ("starts dead%s" % (", may come back after it dies" if re_emergent else ""))
                             if dead else "starts alive"))


def set_horde(plan, faction):
    """Both games: the horde lines a faction that comes by an event needs (HORDE) - Medieval II's Mongols and
    Barbarian Invasion's Slavs come so; without them the faction has no one to come with ('has no faction leader
    ... this faction will be toast' in Rome with REX, the test mod's later faction never came; Medieval II asserted
    on can_horde): the Mongols' numbers and up to HORDE_UNITS of its own units (no general's, no ships) as
    horde_unit, after custom_battle_availability. RomeTW.exe, RomeTW-BI.exe and REX.exe all know the words. A block
    that has horde lines already (a clone of the Mongols / Slavs) keeps its own."""
    from .units import read_units
    mod = plan.mod
    f = plan.edit(mod.file("sm_factions"))
    heads = [i for i in range(len(f)) if tokens(f.text(i))[:1] == ["faction"]]
    start = next((i for i in heads if len(tokens(f.text(i))) > 1 and tokens(f.text(i))[1] == faction), None)
    if start is None:
        return
    end = next((i for i in heads if i > start), len(f))
    block = [tokens(strip_comment(f.text(i))) for i in range(start, end)]
    if any(t[:1] and t[0].startswith("horde_") for t in block):
        return
    culture = next((t[1] for t in block if len(t) > 1 and t[0] == "culture"), None)
    edu = mod.file("edu")
    units = [u for u in read_units(plan.edit(edu))] if edu else []
    mine = [u for u in units if faction in u.ownership] or [u for u in units if culture and culture in u.ownership]
    # foot and horse alike, the cheapest of each first (the Mongols' horde: foot archers to heavy lancers)
    by_kind = [sorted((u for u in mine if u.category == kind and not u.general and not u.mercenary),
                      key=lambda u: u.price or 0) for kind in ("infantry", "cavalry")]
    pick = []
    for k in range(HORDE_UNITS):
        for kind in by_kind:
            if k < len(kind) and len(pick) < HORDE_UNITS:
                pick.append(kind[k].type)
    if not pick:
        plan.warn(f, "%s comes by an event: the game brings it as a horde, but it owns no unit to make one of - "
                     "give it units (Units) or it will not come" % faction)
        return
    at = next((start + k + 1 for k, t in enumerate(block) if t[:1] == ["custom_battle_availability"]), None)
    if at is None:
        at = end
        while at > start + 1 and (not f.text(at - 1).strip() or f.text(at - 1).lstrip().startswith(";")):
            at -= 1
    f.insert(at, ["%s\t\t\t\t%s" % kv for kv in HORDE] + ["horde_unit\t\t\t\t\t%s" % n for n in pick])
    if any(t[:1] == [HOMELESS] for t in block):          # can_homeless stays where the engines read it
        try:
            set_homeless(plan, faction, True)
        except ValueError:
            pass
    plan.note(f, "%s: horde lines (a faction that comes by an event comes as a horde, as the Mongols / Slavs): "
                 "%s" % (faction, ", ".join(pick)))


HOMELESS = "can_homeless"


def homeless(mod, faction):
    """Whether the faction's block in descr_sm_factions.txt says 'can_homeless yes'."""
    f = mod.load(mod.file("sm_factions"))
    start, end = _block(f, faction)
    return start is not None and any(tokens(strip_comment(f.text(i)))[:2] == [HOMELESS, "yes"]
                                     for i in range(start, end))


def _block(f, faction):
    """(first line, line after) of the faction's block in descr_sm_factions.txt, or (None, None)."""
    heads = [i for i in range(len(f)) if tokens(f.text(i))[:1] == ["faction"]]
    start = next((i for i in heads if len(tokens(f.text(i))) > 1 and tokens(f.text(i))[1] == faction), None)
    if start is None:
        return None, None
    return start, next((i for i in heads if i > start), len(f))


# the block's words in the order the engines read them (M2EX.exe's / REX's faction_db: a word out of its place
# stops the reading - every faction after it is lost: 'no faction named slave in descr_sm_factions.txt', units owned
# by them 'Invalid ownership type'). PROVEN in all three games by the in-game tester (2026-10-05, runs 1803 / 1811 /
# 1838): can_homeless right before can_sap, AFTER the last horde_unit; between the horde numbers and horde_unit
# the games stop ('Expecting can_sap').
HOMELESS_AFTER = ("custom_battle_availability", "periods_unavailable_in_custom_battle", "horde_min_units",
                  "horde_max_units", "horde_max_units_reduction_every_horde", "horde_unit_per_settlement_population",
                  "horde_min_named_characters", "horde_max_percent_army_stack",
                  "horde_disband_percent_on_settlement_capture", "horde_unit")
HOMELESS_BEFORE = ("can_sap", "prefers_naval_invasions", "can_have_princess", "has_family_tree")


def homeless_place(f, start, end):
    """The line can_homeless goes in front of: after the horde numbers and the last horde_unit (after
    custom_battle_availability when there are none), right before can_sap - where M2EX / REX read it."""
    words = [(i, (tokens(strip_comment(f.text(i)))[:1] or [None])[0]) for i in range(start + 1, end)]
    after = [i for i, w in words if w in HOMELESS_AFTER]
    if after:
        return after[-1] + 1
    before = [i for i, w in words if w in HOMELESS_BEFORE]
    if before:
        return before[0]
    at = end
    while at > start + 1 and (not f.text(at - 1).strip() or f.text(at - 1).lstrip().startswith(";")):
        at -= 1
    return at


def keep_townless(plan, faction):
    """A faction left with no town at the start (the user, 2026-10-09: 'factions without towns at the start - try
    it'): with REX / M2EX it lives on - 'can_homeless yes' written (its armies and agents stay on the map; with none
    left the game ends it). The plain games end such a faction as the campaign loads and crash - refused there, in
    plain words."""
    from .limits import engine_of
    if not engine_of(plan.mod):
        raise ValueError("%s would keep no town - the game without REX / M2EX ends such a faction as the campaign "
                         "loads and crashes; give it a town, or put REX / M2EX beside the game (with them it lives "
                         "on without towns)" % faction)
    set_homeless(plan, faction, True)
    plan.warn(None, "%s starts with no town (can_homeless yes): its armies and agents on the map keep it alive - "
                    "with none left the game ends it" % faction)


def set_homeless(plan, faction, on):
    """descr_sm_factions.txt: 'can_homeless yes' in the faction's block (on) or out of it. REX's and M2EX's own word
    (their exes: 'the faction may exist with zero settlements without becoming a horde'); the original exes do not
    know it - refused without an engine beside the game."""
    from .limits import engine_of
    mod = plan.mod
    f = plan.edit(mod.file("sm_factions"))
    start, end = _block(f, faction)
    if start is None:
        raise ValueError("descr_sm_factions.txt has no faction %s" % faction)
    have = [i for i in range(start, end) if tokens(strip_comment(f.text(i)))[:1] == [HOMELESS]]
    if on and not engine_of(mod):
        raise ValueError("'lives without towns' (can_homeless) is REX's and M2EX's own setting - the game without "
                         "them does not know it; put REX / M2EX beside the game first")
    if on:
        was = [f.text(i) for i in range(start, end)]
        for i in reversed(have):                          # (an older one at the block's end goes to its place)
            f.delete(i, i + 1)
        end -= len(have)
        f.insert(homeless_place(f, start, end), ["%s				yes" % HOMELESS])
        if [f.text(i) for i in range(start, end + 1)] == was:
            return
        plan.note(f, "%s: can_homeless yes - it stays in the game without a single town (REX / M2EX)" % faction)
    elif have:
        for i in reversed(have):
            f.delete(i, i + 1)
        plan.note(f, "%s: can_homeless taken out - without towns it is out of the game, as the games have it" % faction)


def set_event_texts(plan, faction):
    """The emergence event's title and text in historic_events.txt ({FACTION_TITLE}, {FACTION_BODY}): Medieval II
    with M2EX asked for them ('Couldn't find title string for historic event ...'); one the mod has stays."""
    from .build import display_names
    from .strtables import strings, write_texts
    have = strings(plan.mod, "historic_events.txt")
    shown = display_names(plan.mod).get(faction) or faction.replace("_", " ").title()
    want = {"%s_TITLE" % faction.upper(): "%s rises" % shown,
            "%s_BODY" % faction.upper(): "A new power has risen: %s." % shown}
    want = {k: v for k, v in want.items() if not have.get(k)}
    if want:
        write_texts(plan, "historic_events.txt", want)


def set_event(plan, campaign, faction, date=None, region=None, remove=False):
    """descr_events.txt: the `event emergent_faction <faction>` with its date and region (written, changed or, with
    remove, taken out). The file is made when the campaign has none."""
    import os
    from . import events as EV
    mod = plan.mod
    path = EV.path_of(mod, campaign)
    if not path and remove:
        return
    why = None if remove else EV.date_problem(date, EV._rome(mod))
    if why:
        raise ValueError("%s: %s" % (faction, why))
    if region and region not in mod.regions(campaign):
        raise ValueError("%s is not a region of this campaign" % region)
    if region:
        from .strat import Strat
        held = Strat(plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))).owners().get(region)
        if held not in (None, "slave"):
            raise ValueError("%s is held by %s at the start - a faction that comes by an event must rise in a region "
                             "the rebels hold (as Barbarian Invasion's slavs); in a faction's region the game kills it "
                             "as the campaign loads and crashes. Pick a rebel region (or give %s to the rebels "
                             "first)." % (region, held, region))
    lines = ["", "event\temergent_faction\t%s" % faction, "date\t%s" % (date or "").strip()]
    if region:
        lines.append("region\t%s" % region)
    if not path:                    # the campaign has no events file: a new one holding this event
        path = os.path.join(mod.campaign_dir(campaign), "descr_events.txt")
        plan.binary(path, ("; historical events and when they occur\r\n" + "\r\n".join(lines) + "\r\n")
                    .encode("latin-1"))
        plan.notes.append((mod.rel(path), "new file: %s rises %s" % (faction, date.strip())))
        set_event_texts(plan, faction)
        set_horde(plan, faction)
        return
    f = plan.edit(path)
    have = [e for e in EV.read(f) if e["kind"] == "emergent_faction" and e["name"] == faction]
    for e in sorted(have, key=lambda e: -e["span"][0]):
        a, b = e["span"]
        while b < len(f) and not f.text(b).strip():
            b += 1
        f.delete(a, b)
    if remove:
        if have:
            plan.note(f, "%s: its emergence event removed" % faction)
        return
    end = len(f.raw) - (1 if f.raw and not f.text(len(f.raw) - 1).strip() else 0)
    f.insert(end, lines)
    plan.note(f, "%s rises %s%s" % (faction, date.strip(), " in %s" % region if region else ""))
    set_event_texts(plan, faction)
    set_horde(plan, faction)


def rising_regions(mod, campaign):
    """The regions a faction that comes by an event may rise in: the ones the rebels hold at the start."""
    from .strat import Strat
    owners = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).owners()
    return sorted(r for r, o in owners.items() if o == "slave")


def apply(plan, campaign, faction, way, of=None, re_emergent=False, date=None, region=None, homeless=None):
    """One faction's way in, in every file: descr_sm_factions (words), descr_strat (dead at the start or alive),
    descr_events (the emergence event for 'event', taken out otherwise); homeless True / False: can_homeless (REX /
    M2EX) written / taken out, None: left as it is."""
    set_way(plan, faction, way, of)
    if way == "shadow":
        from .wincond import drop
        drop(plan, campaign, faction)
    set_dead(plan, campaign, faction, way != "map", re_emergent and way != "map")
    if way == "event":
        set_event(plan, campaign, faction, date, region)
    else:
        set_event(plan, campaign, faction, remove=True)
    if homeless is not None:
        set_homeless(plan, faction, bool(homeless))


# ---------------------------------------------------------------------------- checking
def problems(mod, campaign):
    """([faults], [notes]) about later factions: ties that do not match their partner, unknown partners, an emergence
    event for a faction that is not dead at the start, a dead faction holding towns."""
    faults, notes = [], []
    tie = ties(mod)
    state = strat_state(mod, campaign)
    evs = emergent_events(mod, campaign)
    for fac, t in tie.items():
        for word, who in t.items():
            if word == "spawned_on_event":
                continue
            if who not in tie:
                faults.append("descr_sm_factions.txt: %s is '%s %s' - there is no faction %s" % (fac, word, who, who))
            elif (tie[who] or {}).get(PARTNER[word]) != fac:
                faults.append("descr_sm_factions.txt: %s is '%s %s' but %s's line lacks '%s %s' - the two lines "
                              "go in pairs" % (fac, word, who, who, PARTNER[word], fac))
    if ways_for(mod) != WAYS:
        for fac, t in tie.items():
            for word in ("shadowing", "spawned_by", "spawned_on_event"):
                if t.get(word):
                    faults.append("descr_sm_factions.txt: %s is '%s%s' - %s" % (
                        fac, word, "" if t[word] is True else " " + t[word], NOT_ROME))
    from .limits import game_kind
    m2 = game_kind(mod) == "medieval2"
    from .limits import engine_of
    f = mod.load(mod.file("sm_factions"))
    heads = [i for i in range(len(f)) if tokens(f.text(i))[:1] == ["faction"]] + [len(f)]
    for a, b in zip(heads, heads[1:]):                    # can_homeless where the engines read it, or nothing after
        words = [(i, (tokens(strip_comment(f.text(i)))[:1] or [None])[0]) for i in range(a + 1, b)]
        hl = [i for i, w in words if w == HOMELESS]
        late = [i for i, w in words if w in HOMELESS_BEFORE]
        early = [i for i, w in words if w in HOMELESS_AFTER]
        wrong = (late[0] if late and hl and late[0] < hl[0] else None) or \
            (early[-1] if early and hl and early[-1] > hl[0] else None)
        if wrong is not None:
            faults.append("descr_sm_factions.txt line %d: can_homeless comes %s %s - the game stops reading the "
                          "file there and loses every faction after it (the rebels too); it goes after the horde "
                          "numbers and the last horde_unit, right before can_sap (Events > How a faction comes in "
                          "puts it right)" % (hl[0] + 1, "after" if wrong < hl[0] else "before",
                                              tokens(f.text(wrong))[0]))
    if not engine_of(mod):
        for i in range(len(f)):
            if tokens(strip_comment(f.text(i)))[:1] == [HOMELESS]:
                faults.append("descr_sm_factions.txt line %d: can_homeless is REX's and M2EX's own word - the game "
                              "without them does not know it" % (i + 1))
                break
    for fac, shadow, split in ([] if m2 or is_bi(mod) else both_ties(mod)):     # plain Rome only: it crashes
        faults.append("descr_sm_factions.txt: %s has a shadow (%s) and a faction splitting off it (%s) - plain Rome "
                      "crashes at the end of a turn with both on one faction; keep one" % (fac, shadow, split))
    if True:                                # both games bring a faction that comes by an event as a horde
        blocks_ = {}
        cur = None
        for line in mod.load(mod.file("sm_factions")).texts():
            t = tokens(strip_comment(line))
            if t[:1] == ["faction"] and len(t) > 1:
                cur = t[1].rstrip(",")
                blocks_[cur] = False
            elif cur and t[:1] and t[0].startswith("horde_unit"):
                blocks_[cur] = True
        for fac in emergent_events(mod, campaign):
            if fac in blocks_ and not blocks_[fac]:
                faults.append("descr_sm_factions.txt: %s comes by an event, but its block has no horde lines - "
                              "the game brings such a faction in as a horde (the Mongols' / Slavs' way) and without "
                              "them it never comes (New faction / Events and later factions write them)" % fac)
    from .wincond import blocks, file_of
    wp = file_of(mod, campaign)
    if wp:
        listed = blocks(mod.load(wp))
        for fac, t in tie.items():
            if t.get("shadowing") and fac in listed:
                faults.append("descr_win_conditions.txt: %s is a shadow faction - the game does not know it when it "
                              "reads the file and stops there; Barbarian Invasion lists no shadow (take its block "
                              "out)" % fac)
    from .events import later_factions
    script = dict(later_factions(mod, campaign))
    rome = plain_rome(mod)
    for fac, st in state.items():
        way, of = way_of(mod, fac, tie)
        if rome:
            if st["dead"]:
                faults.append("descr_strat.txt: %s starts dead - %s (Load offers to take the line out)" % (
                    fac, DEAD_ROME))
            continue
        if st["dead"] and (st["towns"] or st["people"]):
            faults.append("descr_strat.txt: %s starts dead (dead_until_resurrected) but holds %d town(s) and %d "
                          "character(s) - the games' own later factions hold none" % (fac, st["towns"], st["people"]))
        if way != "map" and not st["dead"] and fac in state:
            faults.append("%s %s, but its descr_strat.txt block lacks dead_until_resurrected" % (
                fac, describe(way, of)))
        if way == "event" and fac not in evs and not script.get(fac):
            notes.append("%s appears by an event, but no emergent_faction event of descr_events.txt (nor the "
                         "campaign script) names it - only the engine's own events can bring it in" % fac)
    from .strat import Strat
    owners = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).owners()
    for fac, e in evs.items():
        reg = e.get("region")
        if reg and owners.get(reg) not in (None, "slave"):
            # BI's own: slavs rise in Locus_Barbaricum, a rebel region. Rome with REX, a faction's region: the faction
            # was killed as the campaign loaded ('has no capital and cannot convert to a horde') and the game crashed
            faults.append("descr_events.txt: %s rises in %s, a town of %s - a faction comes in where the rebels hold "
                          "the land (the games' own: Barbarian Invasion's slavs in a rebel region); in a faction's "
                          "region it is killed as the campaign loads and the game crashes" % (fac, reg, owners[reg]))
        if fac in state and state[fac]["re_emergent"]:
            notes.append("%s comes by an event and is marked re_emergent - the games' own factions that come by an "
                         "event (slavs, romano_british) are not; only the shadow and split-off ones are" % fac)
        if fac not in state:
            faults.append("descr_events.txt: event emergent_faction %s - descr_strat.txt has no such faction" % fac)
        elif rome:
            faults.append("descr_events.txt: event emergent_faction %s - %s" % (fac, NOT_ROME))
        elif not state[fac]["dead"]:
            faults.append("descr_events.txt: event emergent_faction %s - the faction must start dead "
                          "(dead_until_resurrected in descr_strat.txt), the file's own comment says" % fac)
    return faults, notes
