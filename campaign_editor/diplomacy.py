"""Diplomacy at the start: the lines at the end of descr_strat.txt.

Rome (and BI, REX):
    core_attitudes         carthage,   310   romans_julii, romans_scipii
    faction_relationships  romans_julii, 100 romans_brutii
    faction_relationships  romans_julii, allied_to  romans_scipii, romans_senate
    faction_relationships  gauls, at_war_with  romans_julii
A number: lower is better (BI names them: 0 allied, 100 suspicious, 200 neutral, 400 hostile, 600 at war;
the Roman houses -10 among themselves, everyone 600 towards the rebels). allied_to / at_war_with (Sons of
Mars, BI) put two factions in an alliance or at war from the first turn.

Medieval II (and M2EX) - no core_attitudes:
    faction_standings      venice,  -0.45  milan, hre        (-1.0 hate .. 1.0 love; how the AI feels)
    faction_relationships  england, at_war_with  slave       (allied_to / at_war_with only)

A pair with no line is neutral. Trade rights have no start line in either game (the exes read none).
Only the lines that name the edited faction change; the others keep their bytes."""

KINDS = ("core_attitudes", "faction_standings", "faction_relationships")
STANCES = ("allied_to", "at_war_with")

# the numbers the window offers (value, word); None = no line (neutral)
LEVELS = [(-10, "own house"), (0, "allied"), (90, "friends"), (100, "friendly"), (200, "neutral"), (310, "wary"),
          (410, "dislike"), (600, "enemies")]
STANDINGS = [(1.0, "love"), (0.5, "friends"), (0.2, "friendly"), (0.0, "neutral"), (-0.2, "wary"),
             (-0.45, "dislike"), (-0.8, "hate"), (-1.0, "enemies")]
STANCE_WORDS = {"allied_to": "alliance", "at_war_with": "war"}
NEUTRAL = "neutral"


# The status (alliance / war at the start) pulls the AI's feeling along, so the two never contradict each other:
# an alliance lifts a worse feeling to the allied level, a war drops a better one to the enemies' level, neutral
# takes the line out (neutral). Rome: lower is better (BI's own levels: 0 allied, 600 at war); Medieval II: higher.
STATUS_LEVELS = {"core_attitudes": {"allied_to": 0, "at_war_with": 600},
                 "faction_standings": {"allied_to": 0.5, "at_war_with": -1.0}}


def feeling_for(kind, status, current):
    """The AI feeling (`kind` core_attitudes / faction_standings) a pair should have once `status` (None neutral,
    'allied_to', 'at_war_with') is picked; `current` kept when it already fits."""
    if status is None:
        return None
    level = STATUS_LEVELS[kind][status]
    if not isinstance(current, (int, float)) or isinstance(current, bool):
        return level
    lower_better = kind == "core_attitudes"
    worse = (current > level) if lower_better else (current < level)
    if status == "allied_to":
        return level if worse else current
    better = (current < level) if lower_better else (current > level)
    return level if better else current


def is_medieval(strat):
    """Whether the descr_strat is Medieval II's (faction_standings lines, or characters with a sex)."""
    from .strat import medieval
    return any(k == "faction_standings" for _, k, _, _, _ in strat.diplomacy_lines()) or bool(medieval(strat.lines))


def kinds(strat):
    """The two kinds of lines the game of this descr_strat reads: (how the AI feels, where they start)."""
    return ("faction_standings" if is_medieval(strat) else "core_attitudes", "faction_relationships")


def value_of(kind, text):
    """The value of a line's word: 'allied_to' / 'at_war_with', a float for faction_standings, else an int;
    None when it is none of these."""
    t = text.strip().rstrip(",")
    if t in STANCES:
        return t
    try:
        return float(t) if kind == "faction_standings" else int(t)
    except ValueError:
        return None


def text_of(value):
    """How a value is written: allied_to, -1.0, 0.45, 600."""
    if isinstance(value, float):
        return repr(round(value, 4))
    return str(value)


def word(value):
    """A word for a value: the stance, else the nearest level."""
    if value is None:
        return "neutral"
    if isinstance(value, str):
        return STANCE_WORDS.get(value, value)
    levels = STANDINGS if isinstance(value, float) else LEVELS
    return min(levels, key=lambda lv: abs(lv[0] - value))[1]


def parse(text, kind="core_attitudes"):
    """'310 wary' / '310' / 'neutral' / 'alliance' / '-0.45 dislike' -> 310 / None / 'allied_to' / -0.45;
    ValueError for anything else (or a stance where the kind takes none)."""
    t = text.strip()
    if not t or t == NEUTRAL:
        return None
    w = t.split()[0]
    for stance in STANCES:
        if w in (stance, STANCE_WORDS[stance]):
            if kind == "faction_standings":
                raise ValueError(t)
            return stance
    if kind == "faction_standings":
        v = float(w)
        if not -1.0 <= v <= 1.0:
            raise ValueError(t)
        return v
    return int(w)


def read(strat):
    """{kind: {(a, b): value}} for every pair in the file."""
    out = {k: {} for k in KINDS}
    for _, kind, a, value, targets in strat.diplomacy_lines():
        v = value_of(kind, value)
        if v is None:
            continue
        for b in targets:
            out[kind][(a.rstrip(","), b.rstrip(","))] = v
    return out


def _line(kind, a, value, targets):
    if isinstance(value, str):
        return "%s\t%s, %s\t%s" % (kind, a, value, ", ".join(targets))
    return "%s\t%s,\t%s\t\t%s" % (kind, a, text_of(value), ", ".join(targets))


def _order(v):
    """Stances first (alliances, then wars), numbers after, low to high."""
    return (0, STANCES.index(v), 0) if isinstance(v, str) else (1, 0, v)


def rebels(strat, faction):
    """{kind: {(a, b): value}} a faction new to the start needs towards the rebels: written the way the file's
    own factions stand to them (the commonest value each way), else as the game's vanilla files have it -
    Rome 600 both ways, Medieval II faction_standings -1.0 and at_war_with both ways."""
    from collections import Counter
    rel = read(strat)
    present = {k for _, k, _, _, _ in strat.diplomacy_lines()}
    if is_medieval(strat):
        defaults = {"faction_standings": (-1.0, None), "faction_relationships": ("at_war_with", "at_war_with")}
    else:
        defaults = {k: (600, 600) for k in ("core_attitudes", "faction_relationships") if k in present}
    out = {}
    for kind, (to, back) in defaults.items():
        pairs = rel[kind]
        seen_to = Counter(v for (a, b), v in pairs.items() if b == "slave" and a != faction)
        seen_back = Counter(v for (a, b), v in pairs.items() if a == "slave" and b != faction)
        to = seen_to.most_common(1)[0][0] if seen_to else to
        back = seen_back.most_common(1)[0][0] if seen_back else (to if isinstance(to, str) else back)
        out[kind] = {(faction, "slave"): to}
        if back is not None:
            out[kind][("slave", faction)] = back
    return out


def standing_of(number):
    """Rome's feeling number (0 allied .. 200 neutral .. 600 at war) as a Medieval II standing (0.5 .. 0 .. -1.0)."""
    return round(max(-1.0, min(1.0, (200 - number) / 400.0)), 2)


def number_of(standing):
    """A Medieval II standing as Rome's feeling number (the other way of standing_of)."""
    return int(round(200 - 400 * standing))


def in_game_forms(wanted, feeling):
    """`wanted` with every line in the form the game of this descr_strat reads (`feeling` = its feeling kind):
    Medieval II reads no core_attitudes and only allied_to / at_war_with on faction_relationships (a Rome form there
    made M2EX drop the whole diplomacy); Rome reads no faction_standings."""
    out = {}
    for kind, pairs in (wanted or {}).items():
        for pair, v in pairs.items():
            to = kind
            if v is not None and not isinstance(v, str):
                if feeling == "faction_standings" and kind in ("core_attitudes", "faction_relationships"):
                    to, v = "faction_standings", standing_of(v)
                elif feeling == "core_attitudes" and kind == "faction_standings":
                    to, v = "core_attitudes", number_of(v)
            elif v is None and kind == "core_attitudes" and feeling == "faction_standings":
                to = "faction_standings"
            elif v is None and kind == "faction_standings" and feeling == "core_attitudes":
                to = "core_attitudes"
            out.setdefault(to, {})[pair] = v
    return out


def foreign_lines(strat):
    """[(index, the line in this game's own form)] for diplomacy lines the game of this descr_strat does not read:
    on Medieval II core_attitudes and numeric faction_relationships (as faction_standings), on Rome
    faction_standings (as core_attitudes)."""
    feeling = kinds(strat)[0]
    out = []
    for i, kind, a, value, targets in strat.diplomacy_lines():
        v = value_of(kind, value)
        if v is None or isinstance(v, str):
            continue
        new = in_game_forms({kind: {(a, None): v}}, feeling)
        (to, pairs), = new.items()
        if to != kind:
            out.append((i, _line(to, a.rstrip(","), pairs[(a, None)], [t.rstrip(",") for t in targets if t != ","])))
    return out


def set_relations(plan, f, faction, wanted):
    """wanted = {kind: {('me', other): value or None, (other, 'me'): value or None}}
    with 'me' standing for `faction`. Rewrites only the lines that name it."""
    from .strat import Strat
    s = Strat(f)
    wanted = in_game_forms(wanted, kinds(s)[0])
    now = read(s)
    start = s.diplomacy_start
    lines = [("raw", r) for r in f.raw[start:]]           # the diplomacy section and what follows
    dip = [(i - start, kind, a.rstrip(","), value, [t.rstrip(",") for t in targets])
           for i, kind, a, value, targets in s.diplomacy_lines()]
    changed = 0
    for kind in KINDS:
        want = {}
        for (a, b), v in (wanted.get(kind) or {}).items():
            a, b = (faction if a == "me" else a), (faction if b == "me" else b)
            if a == b:
                continue
            want[(a, b)] = v
        if not want:
            continue
        pairs = dict(now[kind])
        for k, v in want.items():
            if v is None:
                pairs.pop(k, None)
            else:
                pairs[k] = v if isinstance(v, str) else (float(v) if kind == "faction_standings" else int(v))
        if pairs == now[kind]:
            continue
        mine = [d for d in dip if d[1] == kind]
        last_of_kind = max((d[0] for d in mine), default=None)
        # 1. lines whose first faction is the edited one: dropped, written again grouped by value
        first_at = None
        for idx, _, a, _, _ in mine:
            if a == faction:
                first_at = idx if first_at is None else min(first_at, idx)
                lines[idx] = ("gone", None)
        out = {}
        for (a, b), v in sorted(pairs.items()):
            if a == faction:
                out.setdefault(v, []).append(b)
        new_out = [_line(kind, faction, v, sorted(tg)) for v, tg in sorted(out.items(), key=lambda x: _order(x[0]))]
        # 2. others' lines naming it: keep where the value still holds, else take it out
        need_in = {a: v for (a, b), v in pairs.items() if b == faction}
        for idx, _, a, value, targets in mine:
            if a == faction or faction not in targets:
                continue
            v = value_of(kind, value)
            if v is None:
                continue
            if need_in.get(a) == v and type(need_in.get(a)) is type(v):
                need_in.pop(a)
                continue
            rest = [t for t in targets if t != faction]
            lines[idx] = ("new", _line(kind, a, v, rest)) if rest else ("gone", None)
        # 3. what is still needed from others: onto a line of theirs with that value, else a line of its own
        extra = []
        for a, v in sorted(need_in.items()):
            host = next((d for d in mine if d[2] == a and value_of(kind, d[3]) == v
                         and type(value_of(kind, d[3])) is type(v) and lines[d[0]][0] != "gone"), None)
            if host:
                idx = host[0]
                cur = lines[idx]
                targets = host[4] if cur[0] == "raw" else [t.strip() for t in cur[1].split("\t")[-1].split(",")]
                lines[idx] = ("new", _line(kind, a, v, [t for t in targets if t] + [faction]))
            else:
                extra.append(_line(kind, a, v, [faction]))
        at = first_at if first_at is not None else ((last_of_kind + 1) if last_of_kind is not None else 0)
        lines[at:at] = [("new", t) for t in new_out + extra]
        # indices after `at` moved: shift the parsed lines for the next kind
        shift = len(new_out) + len(extra)
        dip = [(i + shift if i >= at else i, k, a, v, t) for i, k, a, v, t in dip]
        changed += 1
        for (a, b), v in sorted(want.items()):
            old = now[kind].get((a, b))
            if old != v:
                plan.note(f, "%s: %s towards %s %s -> %s" % (kind, a, b, "neutral" if old is None else text_of(old),
                                                            "neutral" if v is None else text_of(v)))
    if changed:
        f.raw[start:] = [x[1] if x[0] == "raw" else f.make(x[1]) for x in lines if x[0] != "gone"]


def apply_opts(plan, campaign, faction, relations):
    """opts['relations'] = [{'kind', 'from', 'to', 'value' (None = neutral)}], 'me' for the faction."""
    if not relations:
        return
    wanted = {}
    for r in relations:
        wanted.setdefault(r["kind"], {})[(r["from"], r["to"])] = r["value"]
    f = plan.edit(plan.mod.campaign_file(campaign, "descr_strat.txt"))
    set_relations(plan, f, faction, wanted)
