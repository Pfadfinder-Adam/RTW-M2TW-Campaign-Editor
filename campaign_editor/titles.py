"""A faction's leader's and heir's titles (a modder's wish, report #188: 'rename the titles of the faction's leader
and heir - Duke, King, Emperor, Grand Prince'), from the faction's own strings in the string tables:

- Medieval II (text/expanded.txt): {EMT_<F>_FACTION_LEADER_NAME} 'King %S' - the leader's name as the game shows it
  (%S his name), {EMT_<F>_FORMER_FACTION_LEADER_TITLE} 'King' - a former leader's, {EMT_<F>_FACTION_HEIR_NAME}
  'Prince %S' - the heir's. (The _FACTION_LEADER / _FACTION_HEIR / _TITLE ones say 'English Faction Leader',
  'Faction Leader' - labels, left as they are.)
- Rome (text/expanded_bi.txt, expanded.txt): {EMT_<F>_FACTION_LEADER} 'Macedonian Faction Leader',
  {EMT_<F>_FACTION_HEIR} 'Macedonian Faction Heir' - the whole text is the title.

One place for both the Edit faction tab (edit.py) and a new faction's copied strings (clone.py)."""

LEADER_NAME, HEIR_NAME, FORMER = "_FACTION_LEADER_NAME", "_FACTION_HEIR_NAME", "_FORMER_FACTION_LEADER_TITLE"
LEADER, HEIR = "_FACTION_LEADER", "_FACTION_HEIR"
SUFFIXES = (LEADER_NAME, HEIR_NAME, FORMER, LEADER, HEIR)


def word_of(pattern):
    """'King %S' -> 'King'."""
    return " ".join(pattern.replace("%S", " ").replace("%s", " ").split())


def with_word(pattern, word):
    """The pattern with its title word changed ('King %S', 'Duke' -> 'Duke %S'); a pattern with no word or no %S
    becomes 'word %S'."""
    old = word_of(pattern)
    if old and old in pattern and "%" in pattern:
        return pattern.replace(old, word, 1)
    return word + " %S"


def read(values, faction):
    """{'leader_title', 'heir_title'} from the faction's strings ({KEY upper: text}); a title the tables lack is
    left out."""
    F = "EMT_" + faction.upper()
    out = {}
    m2 = F + LEADER_NAME in values or F + HEIR_NAME in values
    for k, name, plain in (("leader_title", LEADER_NAME, LEADER), ("heir_title", HEIR_NAME, HEIR)):
        if m2:
            if F + name in values:
                out[k] = word_of(values[F + name])
        elif F + plain in values:
            out[k] = values[F + plain].strip()
    return out


def changes(values, faction, leader=None, heir=None):
    """{KEY: new text} for the titles asked (None or unchanged: nothing) - the strings in `values` ({KEY upper:
    text}, the faction's as they are)."""
    F = "EMT_" + faction.upper()
    now = read(values, faction)
    out = {}
    m2 = F + LEADER_NAME in values or F + HEIR_NAME in values
    for k, want, name, plain in (("leader_title", leader, LEADER_NAME, LEADER), ("heir_title", heir, HEIR_NAME, HEIR)):
        want = " ".join((want or "").split())
        if not want or want == now.get(k):
            continue
        if m2:
            if F + name in values:
                out[F + name] = with_word(values[F + name].strip(), want)
            if k == "leader_title" and F + FORMER in values:
                out[F + FORMER] = want
        elif F + plain in values:
            out[F + plain] = want
    return out


def copied(key, value, faction, leader, heir, m2):
    """A new faction's copied string (key already its own, value as copied): the title asked put in, or None to
    keep the copy. m2: the tables have the _NAME strings (Medieval II's form)."""
    F = "EMT_" + faction.upper()
    k = key.upper()
    leader, heir = " ".join((leader or "").split()), " ".join((heir or "").split())
    gap = value[:len(value) - len(value.lstrip())]
    body = value.strip()
    if m2:
        if leader and k == F + LEADER_NAME:
            return gap + with_word(body, leader)
        if leader and k == F + FORMER:
            return gap + leader
        if heir and k == F + HEIR_NAME:
            return gap + with_word(body, heir)
    else:
        if leader and k == F + LEADER:
            return gap + leader
        if heir and k == F + HEIR:
            return gap + heir
    return None


__all__ = ["read", "changes", "copied", "word_of", "with_word", "SUFFIXES"]
