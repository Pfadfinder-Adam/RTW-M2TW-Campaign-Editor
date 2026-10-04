"""Rome's message 'a faction is destroyed' (descr_event_images.txt, faction_defeated): its picture is a 'switch' with
one 'case' per faction - case N for the Nth faction of descr_sm_factions.txt (21 in Rome: case 0 the Julii's film ...
case 20 the rebels'). A faction past the last case crashes the game the moment it is destroyed:

    ASSERT FAILED: src\\game_rtw\\UI\\message_builder_objects.cpp(763): condition < int32(m_alt_condition_chains.count())
    Trying to initialise a switch message object with a value higher than it's number of conditions
      ... MESSAGE_EVENT_HANDLER::faction_defeated

(a tester's Rome + REX test mod: ce_test_later, the 23rd faction, died on turn 1). So the switch gets a case for
every faction: a new case shows the film of the last one there was. Medieval II has no such switch (nothing to do);
Rome's other switches (civil war, the Senate) count the three Roman houses only."""

import os
import re

from .moddata import _ci
from .textio import strip_comment, tokens

NAME = "descr_event_images.txt"
EVENT = "faction_defeated"


def path_of(mod):
    """(path, own): the mod's descr_event_images.txt, else the game's (own False), else (None, False)."""
    own = _ci(mod.data, NAME)
    if own:
        return own, True
    try:
        from .newmod import game_of
        game = game_of(mod.data)
        gdata = _ci(game, "data") if game else None
        if gdata and os.path.normcase(os.path.abspath(gdata)) != os.path.normcase(os.path.abspath(mod.data)):
            p = _ci(gdata, NAME)
            if p:
                return p, False
    except Exception:
        pass
    return None, False


def _block(lines):
    """(first, last, [(case number, first line, last line)]) of the faction_defeated switch, or None: last = the
    line of the switch's closing brace."""
    start = next((i for i, x in enumerate(lines) if tokens(strip_comment(x)) == [EVENT]), None)
    if start is None:
        return None
    sw = None
    for i in range(start + 1, len(lines)):
        t = tokens(strip_comment(lines[i]))
        if t and re.match(r"^[a-z_]+$", t[0]) and not lines[i][:1].isspace() and len(t) == 1:
            return None                                     # the next message: no switch here
        if t[:1] == ["switch"]:
            sw = i
            break
    if sw is None:
        return None
    depth, cases, case = 0, [], None
    for i in range(sw + 1, len(lines)):
        code = strip_comment(lines[i])
        t = tokens(code)
        if depth == 1 and t[:1] == ["case"] and len(t) > 1 and t[1].isdigit():
            case = [int(t[1]), i, None]
        depth += code.count("{") - code.count("}")
        if case and depth == 1 and "}" in code:
            case[2] = i
            cases.append(tuple(case))
            case = None
        if depth == 0 and "}" in code:
            return sw, i, cases
    return None


def cases(mod):
    """The number of cases of the switch (None when the file or the switch is not there - Medieval II)."""
    path, _ = path_of(mod)
    if not path:
        return None
    b = _block(mod.load(path).texts())
    return len(b[2]) if b else None


def faction_count(mod, plan=None):
    sm = mod.file("sm_factions")
    if not sm:
        return 0
    f = plan.files.get(sm) if plan else None
    f = f or mod.load(sm)
    return sum(1 for x in f.texts() if tokens(strip_comment(x))[:1] == ["faction"])


def problem(mod, count=None):
    """Plain words when the switch has fewer cases than there are factions, else None."""
    have = cases(mod)
    count = faction_count(mod) if count is None else count
    if have is None or count <= have:
        return None
    return ("descr_event_images.txt: the message 'faction destroyed' has %d pictures (one per faction) for %d "
            "factions - the game crashes when faction %d or a later one is destroyed (message_builder_objects.cpp: "
            "'a switch message object with a value higher than its number of conditions')" % (have, count, have + 1))


def keep_up(plan, count=None):
    """The switch given a case for every faction the plan leaves - in the mod's own copy, or the game's copy put
    into the mod. Called by Plan.apply when descr_sm_factions.txt is written; never stops a write."""
    try:
        mod = plan.mod
        count = faction_count(mod, plan) if count is None else count
        path, own = path_of(mod)
        if not path:
            return False
        target = path if own else os.path.join(mod.data, NAME)
        if own:
            f = plan.edit(path)
        else:                                               # the game's copy, as this plan leaves it
            from .textio import TextFile
            data = plan.binaries.get(target)
            if data is None:
                with open(path, "rb") as fh:
                    data = fh.read()
            f = TextFile.from_bytes(target, data)
        lines = f.texts()
        b = _block(lines)
        if not b or count <= len(b[2]):
            return False
        _, end, cs = b
        num, first, last = cs[-1]
        body = lines[first + 1:last + 1]                    # '{' ... '}' of the last case
        head = lines[first]
        new = []
        for n in range(len(cs), count):
            new.append(re.sub(r"case\s+\d+", "case %d" % n, head, count=1))
            new.extend(body)
        f.insert(end, new)
        if own:
            plan.note(f, "the message 'faction destroyed' has a picture for each of the %d factions (cases %d-%d "
                         "added; the game crashed when a faction past the last case was destroyed)"
                      % (count, len(cs), count - 1))
        else:
            plan.binary(target, f.dump())
            plan.note(None, "%s: the game's copy put in the mod with a 'faction destroyed' picture for each of the "
                            "%d factions (the game crashed when a faction past the last case was destroyed)"
                      % (NAME, count))
        return True
    except Exception:
        return False

