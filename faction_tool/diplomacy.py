"""Diplomacy at the start: the core_attitudes and faction_relationships lines
at the end of descr_strat.txt.

    core_attitudes         carthage,   310   romans_julii, romans_scipii
    faction_relationships  romans_julii, 100 romans_brutii

A line says how its first faction stands towards the ones after the number;
lower is better (the files use -10 for the Roman houses among themselves,
90-100 friends, 300-310 wary, 400-410 dislike, 600 enemies - everyone towards
the rebels). A pair with no line is neutral. There are no lines for alliances
or wars in these files.

Only the lines that name the edited faction change; the others keep their bytes."""

KINDS = ("core_attitudes", "faction_relationships")

# the choices the window offers (value, word); None = no line (neutral)
LEVELS = [(-10, "own"), (90, "friends"), (100, "friendly"), (310, "wary"), (410, "dislike"), (600, "enemies")]


def word(value):
    """A word for a value: the nearest of LEVELS."""
    if value is None:
        return "neutral"
    return min(LEVELS, key=lambda lv: abs(lv[0] - value))[1]


def read(strat):
    """{kind: {(a, b): value}} for every pair in the file."""
    out = {k: {} for k in KINDS}
    for _, kind, a, value, targets in strat.diplomacy_lines():
        try:
            v = int(value)
        except ValueError:
            continue
        for b in targets:
            out[kind][(a.rstrip(","), b.rstrip(","))] = v
    return out


def _line(kind, a, value, targets):
    return "%s\t%s,\t%d\t\t%s" % (kind, a, value, ", ".join(targets))


def set_relations(plan, f, faction, wanted):
    """wanted = {kind: {('me', other): value or None, (other, 'me'): value or None}}
    with 'me' standing for `faction`. Rewrites only the lines that name it."""
    from .strat import Strat
    s = Strat(f)
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
                pairs[k] = int(v)
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
        new_out = [_line(kind, faction, v, sorted(tg)) for v, tg in sorted(out.items())]
        # 2. others' lines naming it: keep where the value still holds, else take it out
        need_in = {a: v for (a, b), v in pairs.items() if b == faction}
        for idx, _, a, value, targets in mine:
            if a == faction or faction not in targets:
                continue
            try:
                v = int(value)
            except ValueError:
                continue
            if need_in.get(a) == v:
                need_in.pop(a)
                continue
            rest = [t for t in targets if t != faction]
            lines[idx] = ("new", _line(kind, a, v, rest)) if rest else ("gone", None)
        # 3. what is still needed from others: onto a line of theirs with that value, else a line of its own
        extra = []
        for a, v in sorted(need_in.items()):
            host = next((d for d in mine if d[2] == a and d[3].lstrip("-").isdigit() and int(d[3]) == v
                         and lines[d[0]][0] != "gone"), None)
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
                plan.note(f, "%s: %s towards %s %s -> %s" % (kind, a, b, "neutral" if old is None else old,
                                                            "neutral" if v is None else v))
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
