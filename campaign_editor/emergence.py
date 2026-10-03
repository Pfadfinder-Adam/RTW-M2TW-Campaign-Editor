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
       "Barbarian Invasion's, REX's and Medieval II's engines read these words; on vanilla Rome try it in the game.")


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
def set_way(plan, faction, way, of=None):
    """descr_sm_factions.txt: the faction's own way in (its header line) and its partner's word; the faction's old
    way and any partner word naming it go. Refused: a partner that is the faction itself / unknown / already has a
    shadow (or a split-off faction) of its own."""
    if way not in WAYS:
        raise ValueError("unknown way '%s'" % way)
    mod = plan.mod
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
    lines = ["", "event\temergent_faction\t%s" % faction, "date\t%s" % (date or "").strip()]
    if region:
        lines.append("region\t%s" % region)
    if not path:                    # the campaign has no events file: a new one holding this event
        path = os.path.join(mod.campaign_dir(campaign), "descr_events.txt")
        plan.binary(path, ("; historical events and when they occur\r\n" + "\r\n".join(lines) + "\r\n")
                    .encode("latin-1"))
        plan.notes.append((mod.rel(path), "new file: %s rises %s" % (faction, date.strip())))
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


def apply(plan, campaign, faction, way, of=None, re_emergent=False, date=None, region=None):
    """One faction's way in, in every file: descr_sm_factions (words), descr_strat (dead at the start or alive),
    descr_events (the emergence event for 'event', taken out otherwise)."""
    set_way(plan, faction, way, of)
    set_dead(plan, campaign, faction, way != "map", re_emergent and way != "map")
    if way == "event":
        set_event(plan, campaign, faction, date, region)
    else:
        set_event(plan, campaign, faction, remove=True)


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
    from .events import later_factions
    script = dict(later_factions(mod, campaign))
    for fac, st in state.items():
        way, of = way_of(mod, fac, tie)
        if st["dead"] and (st["towns"] or st["people"]):
            faults.append("descr_strat.txt: %s starts dead (dead_until_resurrected) but holds %d town(s) and %d "
                          "character(s) - the games' own later factions hold none" % (fac, st["towns"], st["people"]))
        if way != "map" and not st["dead"] and fac in state:
            faults.append("%s %s, but its descr_strat.txt block lacks dead_until_resurrected" % (
                fac, describe(way, of)))
        if way == "event" and fac not in evs and not script.get(fac):
            notes.append("%s appears by an event, but no emergent_faction event of descr_events.txt (nor the "
                         "campaign script) names it - only the engine's own events can bring it in" % fac)
    for fac, e in evs.items():
        if fac not in state:
            faults.append("descr_events.txt: event emergent_faction %s - descr_strat.txt has no such faction" % fac)
        elif not state[fac]["dead"]:
            faults.append("descr_events.txt: event emergent_faction %s - the faction must start dead "
                          "(dead_until_resurrected in descr_strat.txt), the file's own comment says" % fac)
    return faults, notes
