"""Who leads a Medieval II faction after its leader dies: descr_sm_factions.txt's `has_family_tree` and
`can_have_princess` lines (Medieval II and M2EX; Rome's factions have neither - its leaders follow the family tree).

What the engine does with each value (Pannoniae's engine source, read only: faction_db.cpp reads the word,
faction.cpp promote_new_leader / promote_new_heir / choose_teutonic_leader, character.cpp and faction.cpp
FACTION_FAMILY::strat_start_round for births and marriages, world.cpp determine_faction_status; medieval2.exe and
M2EX.exe both hold the word 'teutonic' beside 'has_family_tree'):

    yes        by birth: the heir takes over, then the leader's eldest son, the husband of his eldest daughter, then
               the family member with the most authority (his own house first); children are born, marriages offered
    teutonic   by election: the leader and the heir are the family's grown men with the most authority + command
               (born in the faction, not the leader or heir already); a family tree is shown, but no child is born
               and no marriage is offered - new members come by adoption only; the engine says 'Factions with a
               teutonic family tree should not allow princesses!' - can_have_princess must be no
    no         no family tree: no tree on the scrolls, no births, no marriages; the leader's place goes to the heir,
               else to the family member with the most authority; and the faction never dies - with no town and no
               leader it stays in the game, as the Pope and the rebels do (determine_faction_status)

Both lines stand in every Medieval II block (the engine stops at a block without them: 'Expecting
can_have_princess'), so only their words are changed, never a line added or moved."""

import re

from .textio import strip_comment, tokens

TREE, PRINCESS = "has_family_tree", "can_have_princess"
WAYS = ("yes", "teutonic", "no")
LABELS = {"yes": "By birth (family tree)", "teutonic": "By election (teutonic)", "no": "No family tree"}
SAID = {"yes": "by birth (has_family_tree yes): the heir, then the leader's sons take over; children are born and "
               "marriages offered",
        "teutonic": "by election (has_family_tree teutonic): the family's grown man with the most authority + command "
                    "becomes leader, the next one heir, as the Teutonic Order; no children are born and no marriages "
                    "offered - new members come by adoption only",
        "no": "no family tree (has_family_tree no): no tree, births or marriages; the heir or the family member with "
              "the most authority takes over"}


def _block(f, faction):
    from .emergence import _block as block
    return block(f, faction)


def _line(f, faction, word):
    """(line index, its word) of `word` in the faction's block, or (None, None)."""
    start, end = _block(f, faction)
    if start is None:
        return None, None
    for i in range(start + 1, end):
        t = tokens(strip_comment(f.text(i)))
        if t[:1] == [word] and len(t) > 1:
            return i, t[1].lower()
    return None, None


def read(mod, faction, f=None):
    """{'succession': 'yes' | 'teutonic' | 'no', 'princesses': True / False} as descr_sm_factions.txt says now (f:
    the file as a plan leaves it); {} where the block has no family tree line (Rome)."""
    f = f if f is not None else mod.load(mod.file("sm_factions"))
    _, tree = _line(f, faction, TREE)
    if tree not in WAYS:
        return {}
    _, princess = _line(f, faction, PRINCESS)
    return {"succession": tree, "princesses": princess == "yes"}


def _set(plan, f, i, word, value):
    line = f.text(i)
    f.set(i, re.sub(r"(\b%s\s+)\S+" % word, lambda m: m.group(1) + value, line, count=1))


def apply(plan, faction, succession=None, princesses=None, campaign=None):
    """has_family_tree / can_have_princess of the faction set (None: left as it is). An election (teutonic) takes
    the princesses away - the engine refuses them together - and says so; princesses already on the campaign's
    map are named (they stay; the game makes no new ones)."""
    f = plan.edit(plan.mod.file("sm_factions"))
    ti, tree = _line(f, faction, TREE)
    pi, princess = _line(f, faction, PRINCESS)
    if ti is None or pi is None:
        raise ValueError("%s has no has_family_tree / can_have_princess line in descr_sm_factions.txt - how a leader "
                         "follows another is Medieval II's setting (Rome's leaders always follow the family tree)"
                         % faction)
    if succession is not None and succession not in WAYS:
        raise ValueError("succession must be one of %s" % ", ".join(WAYS))
    want_tree = succession or tree
    want_princess = princess if princesses is None else ("yes" if princesses else "no")
    if want_tree == "teutonic" and want_princess == "yes":
        want_princess = "no"
        plan.warn(f, "%s: princesses taken away (can_have_princess no) - the game refuses princesses in a faction "
                     "that elects its leader ('Factions with a teutonic family tree should not allow princesses!')"
                  % faction)
    if want_tree != tree:
        _set(plan, f, ti, TREE, want_tree)
        plan.note(f, "%s: leader %s (was %s)" % (faction, SAID[want_tree], tree))
        if want_tree == "no":
            plan.warn(f, "%s: without a family tree the faction never dies - with no town and no leader left it "
                         "stays in the game, as the Pope and the rebels do" % faction)
    if want_princess != princess:
        _set(plan, f, pi, PRINCESS, want_princess)
        plan.note(f, "%s: princesses %s (can_have_princess %s)" % (
            faction, "on" if want_princess == "yes" else "off", want_princess))
        if want_princess == "no" and campaign:
            _princesses_left(plan, faction, campaign)


def _princesses_left(plan, faction, campaign):
    from .strat import Strat
    sp = plan.mod.campaign_file(campaign, "descr_strat.txt")
    s = Strat(plan.files[sp] if sp in plan.files else plan.mod.load(sp))
    fb = s.faction(faction)
    left = [c.name for c in (fb.characters if fb else ()) if c.kind == "princess"]
    if left:
        one = len(left) == 1
        plan.warn(None, "%s: %s %s %s on the map at the start; the game makes no new ones - take %s off on Maps if "
                        "not wanted" % (faction, "the princess" if one else "the princesses", ", ".join(left),
                                        "stays" if one else "stay", "her" if one else "them"))
