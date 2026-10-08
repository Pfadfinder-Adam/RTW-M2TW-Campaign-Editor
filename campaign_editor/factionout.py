"""Take a faction out of ONE campaign (the opposite of placing it there): the faction stays in the mod - descr_sm_factions,
its units, pictures, names, other campaigns -, only this campaign no longer has it, as both games' own prologues
leave most of the mod's factions out (Rome's sons_of_mars places 7 of 21, Medieval II's norman_prologue 5).

Both games (Rome with REX or without, Medieval II with M2EX or without). What goes, in the campaign's files:
- descr_strat.txt: its block (towns, armies, agents, fleets, family), its line in the playable / unlockable /
  nonplayable lists, every diplomacy line it starts and its name in the others' (a line left naming no one goes);
- descr_win_conditions.txt: its block, and its name in the others' outlive lists;
- descr_events.txt: the events that make it rise (emergent_faction);
- lines of the campaign's scripts naming it are left as they are and listed (returned as warnings).
Its towns are taken by the caller first (a cut deletes them with their regions; the land is never left without
a region)."""
import re

from .textio import strip_comment, tokens


def words_of(faction):
    """A regex finding the faction's name as a whole word."""
    return re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(faction))


def take_out(plan, campaign, faction):
    """The faction out of the campaign, in the plan. Returns the warnings (script lines naming it)."""
    from .diplomacy import _line, value_of
    from .strat import Strat
    if faction == "slave":
        raise ValueError("the rebels cannot be taken out of a campaign")
    mod = plan.mod
    path = mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(path)
    s = Strat(f)
    fb = s.faction(faction)
    if fb is None:
        raise ValueError("%s is not in this campaign" % faction)
    if [b for b in s.factions if b.name != "slave" and b.name != faction] == []:
        raise ValueError("%s is the campaign's last faction" % faction)
    gone, new = set(), {}
    # its block (with the banner comments before the next one, which belong to that one, left as they are)
    gone.update(range(fb.start, fb.end))
    for lst in (s.playable, s.unlockable, s.nonplayable):
        for i, name in (lst or {}).get("items", []):
            if name == faction:
                gone.add(i)
    for i, kind, a, value, targets in s.diplomacy_lines():
        a = a.rstrip(",")
        names = [t.rstrip(",") for t in targets if t.rstrip(",")]
        if a == faction:
            gone.add(i)
            continue
        if faction not in names:
            continue
        rest = [t for t in names if t != faction]
        v = value_of(kind, value)
        if not rest or v is None:
            gone.add(i)
        else:
            new[i] = _line(kind, a, v, rest)
    f.raw[:] = [f.make(new[i]) if i in new else r for i, r in enumerate(f.raw) if i not in gone]
    plan.note(f, "%s taken out of the campaign: its block (%d line(s)), its place in the faction lists and its "
                 "diplomacy - the faction stays in the mod (descr_sm_factions)" % (faction, fb.end - fb.start))
    _win_conditions(plan, campaign, faction)
    _events(plan, campaign, faction)
    return _scripts(plan, campaign, faction)


def _win_conditions(plan, campaign, faction):
    from .wincond import blocks, drop, file_of
    p = file_of(plan.mod, campaign)
    if not p:
        return
    drop(plan, campaign, faction)
    f = plan.edit(p)
    word = words_of(faction)
    changed = 0
    for name, (a, b) in blocks(f).items():
        for i in range(a, b):
            t = f.text(i)
            head = tokens(strip_comment(t))[:1]
            # the outlive list: 'outlive x y' (Medieval II) or the line after 'outlive_factions' (Rome)
            after_word = i > a and tokens(strip_comment(f.text(i - 1)))[:1] == ["outlive_factions"]
            if (head == ["outlive"] or after_word) and word.search(strip_comment(t)):
                code, sep, note = t.partition(";")
                rest = " ".join(x for x in code.split() if x != faction)
                f.set(i, rest + ((" " + sep + note) if sep else ""))
                changed += 1
    if changed:
        plan.note(f, "%s taken out of %d outlive line(s)" % (faction, changed))


def _events(plan, campaign, faction):
    from .events import apply as events_apply, path_of, read as events_read
    p = path_of(plan.mod, campaign)
    if not p:
        return
    ids = [e["id"] for e in events_read(plan.edit(p)) if e["kind"] == "emergent_faction" and e["name"] == faction]
    if ids:
        events_apply(plan, campaign, {"remove": ids})


def _scripts(plan, campaign, faction):
    import os
    word = words_of(faction)
    out = []
    folder = os.path.dirname(plan.mod.campaign_file(campaign, "descr_strat.txt") or "")
    for name in ("campaign_script.txt",):
        p = os.path.join(folder, name)
        if not os.path.isfile(p):
            continue
        hits = [k + 1 for k, t in enumerate(plan.edit(p).texts()) if word.search(strip_comment(t))]
        if hits:
            out.append("%s: %d line(s) of %s still name %s (lines %s%s) - left as they are; the game may stop at them, "
                       "change them by hand" % (faction, len(hits), name, faction, ", ".join(map(str, hits[:8])),
                                                " ..." if len(hits) > 8 else ""))
    for w in out:
        plan.warn(None, w)
    return out
