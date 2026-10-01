"""Victory: a faction's block in the campaign's descr_win_conditions.txt - what the player must do to win the
long and the short campaign (the AI does not read it). The game crashes when a playable faction's block names a
region or a faction that does not exist (check.win_condition_problems).

    romans_julii                         macedon                        venice
    imperator                            take_rome                      hold_regions Constantinople_Province
    short_campaign outlive_factions      short_campaign outlive_factions take_regions 45
    gauls                                greek_cities thrace            short_campaign hold_regions ;Constantinople_Province
                                                                        take_regions 15
                                                                        outlive milan byzantium

The block starts at the faction's name and runs to the next blank line; the lines before 'short_campaign' are the
long campaign, that line and the ones after it the short one. Words the exes read (strings of RomeTW.exe,
RomeTW-BI.exe, medieval2.exe): hold_regions <regions>, take_regions <n>, outlive <factions> and outlive_factions
(Rome writes the factions on the next line), and in Rome only imperator (the Senate's way: become emperor) and
take_rome. Lines the tool does not know are kept as they are."""

from .textio import strip_comment, tokens

GOALS = ("imperator", "take_rome")          # Rome only
WORDS = ("hold_regions", "take_regions", "outlive", "outlive_factions") + GOALS


def _empty():
    return {"hold": [], "take": None, "outlive": [], "goals": [], "other": [], "outlive_word": None}


def file_of(mod, campaign):
    return mod.campaign_file(campaign, "descr_win_conditions.txt")


def blocks(f):
    """{faction: (start, end)} - the name line and the line after the block's last one."""
    out, i, n = {}, 0, len(f.raw)
    while i < n:
        text = strip_comment(f.text(i))
        if text.strip() and not text[:1].isspace() and len(text.split()) == 1 and text.strip() not in WORDS \
                and text.strip() != "short_campaign":
            j = i + 1
            while j < n and f.text(j).strip() != "":
                j += 1
            out.setdefault(text.strip(), (i, j))
            i = j
        else:
            i += 1
    return out


def parse(texts):
    """The lines of one block after the faction's name -> {'long': cond, 'short': cond}; cond = {'hold': [regions],
    'take': n or None, 'outlive': [factions], 'goals': ['imperator' / 'take_rome'], 'other': [lines kept],
    'outlive_word': the word the file used}."""
    out = {"long": _empty(), "short": _empty()}
    part, listing = "long", False
    for line in texts:
        t = tokens(strip_comment(line))
        if not t:
            continue
        if t[0] == "short_campaign":
            part, listing, t = "short", False, t[1:]
            if not t:
                continue
        c = out[part]
        w = t[0]
        if w == "hold_regions":
            c["hold"] += t[1:]
            listing = False
        elif w == "take_regions":
            try:
                c["take"] = int(t[1])
            except (IndexError, ValueError):
                c["other"].append(line)
            listing = False
        elif w in ("outlive", "outlive_factions"):
            c["outlive"] += t[1:]
            c["outlive_word"] = w
            listing = w == "outlive_factions" and not t[1:]     # Rome: the factions follow on the next line
        elif w in GOALS:
            c["goals"].append(w)
            listing = False
        elif listing:
            c["outlive"] += t
            listing = False
        else:
            c["other"].append(line)
            listing = False
    return out


def read(mod, campaign):
    """{faction: {'long': cond, 'short': cond}} for every block of the campaign's file ({} without one)."""
    p = file_of(mod, campaign)
    if not p:
        return {}
    f = mod.load(p)
    return {fac: parse([f.text(k) for k in range(a + 1, b)]) for fac, (a, b) in blocks(f).items()}


def same(a, b):
    keys = ("hold", "take", "outlive", "goals", "other")
    return all(a["long"][k] == b["long"][k] and a["short"][k] == b["short"][k] for k in keys)


def lines(faction, cond, medieval):
    """The block's text lines (without the closing blank line)."""
    out = [faction]
    for part in ("long", "short"):
        c = cond[part]
        body = []
        body += list(c["goals"]) if not medieval else []
        if c["hold"]:
            body.append("hold_regions " + " ".join(c["hold"]))
        if c["take"] is not None:
            body.append("take_regions %d" % c["take"])
        if c["outlive"]:
            word = c.get("outlive_word") or ("outlive" if medieval else "outlive_factions")
            if word == "outlive_factions":
                body += ["outlive_factions", " ".join(c["outlive"])]
            else:
                body.append("outlive " + " ".join(c["outlive"]))
        body += [l.strip() for l in c["other"]]
        if part == "short" and body:
            body[0] = "short_campaign " + body[0]
        out += body
    return out


def problems(cond, regions, factions, medieval):
    """Plain-word reasons the game would crash or the goal could not be met; [] when fine."""
    out = []
    for part, name in (("long", "long campaign"), ("short", "short campaign")):
        c = cond[part]
        for r in c["hold"]:
            if r not in regions:
                out.append("%s: region '%s' does not exist - the game crashes when the faction is played" % (name, r))
        for f in c["outlive"]:
            if f not in factions:
                out.append("%s: faction '%s' does not exist" % (name, f))
        if c["take"] is not None and not 0 < c["take"] <= len(regions):
            out.append("%s: take %d regions - the map has %d" % (name, c["take"], len(regions)))
        if medieval and c["goals"]:
            out.append("%s: %s is Rome's - Medieval II does not read it" % (name, " / ".join(c["goals"])))
    return out


def set_conditions(plan, campaign, faction, cond, medieval):
    """Write the faction's block (in place of its old one, else at the end of the file). Nothing changes when the
    block already says the same."""
    p = file_of(plan.mod, campaign)
    if not p:
        return
    f = plan.edit(p)
    have = blocks(f).get(faction)
    if have:
        a, b = have
        if same(parse([f.text(k) for k in range(a + 1, b)]), cond):
            return
        f.raw[a:b] = [f.make(t) for t in lines(faction, cond, medieval)]
        plan.note(f, "victory conditions of %s rewritten" % faction)
    else:
        add = lines(faction, cond, medieval)
        if f.raw and f.text(len(f.raw) - 1).strip() != "":
            add = [""] + add
        f.insert(len(f.raw), add + [""])
        plan.note(f, "victory conditions of %s added" % faction)


def apply_opts(plan, campaign, faction, cond, opts=None):
    """opts['victory'] = {'long': cond, 'short': cond}: checked against the regions (the campaign's and the run's
    new ones) and factions, then written. A region or faction that does not exist is refused - the game would
    crash."""
    from .limits import game_kind
    from .strat import Strat
    mod = plan.mod
    regions = set(mod.regions(campaign))
    regions |= {r["name"] for r in ((opts or {}).get("regions") or {}).get("new", [])}
    p = mod.campaign_file(campaign, "descr_strat.txt")
    factions = {fb.name for fb in Strat(mod.load(p)).factions} | {faction}
    medieval = game_kind(mod) == "medieval2"
    bad = [m for m in problems(cond, regions, factions, medieval) if "does not exist" in m]
    if bad:
        raise ValueError("Victory conditions of %s: %s. Nothing written." % (faction, "; ".join(bad)))
    set_conditions(plan, campaign, faction, cond, medieval)
