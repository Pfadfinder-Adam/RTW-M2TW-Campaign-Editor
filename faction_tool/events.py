"""The campaign's events (world/maps/campaign/<campaign>/descr_events.txt), both games:

    event   plague      plague_in_macedonia         (kind, then the name: the key of its texts)
    date    14 winter                               (Rome: years from the start and a season; Medieval II: a
    position    138, 67                              turn, or two turns - a random one between them)
    movie   event/gunpowder_invented.bik            (optional)

Kinds seen in the games' files: historic (a message only), plague, volcano, earthquake; the engines know more
(flood, storm, horde, dustbowl, locusts...). The texts players see are {NAME_TITLE} and {NAME_BODY} in
text/historic_events.txt. Factions that appear later: `dead_until_resurrected` under a faction of descr_strat.txt,
woken by the campaign script (`event emergent_faction mongols` ...) - read here to show them, not changed."""

import os
import re

from .textio import strip_comment, tokens

KINDS = ("historic", "plague", "volcano", "earthquake", "flood", "storm", "horde", "dustbowl", "locusts")
RE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def path_of(mod, campaign):
    from .moddata import _ci
    d = mod.campaign_dir(campaign)
    return _ci(d, "descr_events.txt") if d and os.path.isdir(d) else None


def read(f):
    """[{'id', 'kind', 'name', 'date', 'position': (x, y) or None, 'movie', 'span': (a, b), 'lines': {word: line}}]
    in the file's order (b is past the event's last line that is not blank or a comment); id = the name, or name#2
    for its second use."""
    out, cur = [], None
    for i in range(len(f)):
        code = strip_comment(f.text(i)).strip()
        if not code:
            continue
        word = code.split()[0]
        rest = code[len(word):].strip()
        if word == "event":
            t = rest.split()
            cur = {"kind": t[0] if t else "", "name": t[1] if len(t) > 1 else "", "date": "", "position": None,
                   "movie": "", "span": (i, i + 1), "lines": {"event": i}}
            out.append(cur)
            continue
        if cur is None:
            continue
        cur["span"] = (cur["span"][0], i + 1)
        cur["lines"][word] = i
        if word == "date":
            cur["date"] = rest
        elif word == "position":
            nums = re.findall(r"-?\d+", rest)
            cur["position"] = (int(nums[0]), int(nums[1])) if len(nums) >= 2 else None
        elif word == "movie":
            cur["movie"] = rest
    seen = {}
    for e in out:                       # one name may be used twice (vanilla Rome: plague_in_italy): name, name#2
        seen[e["name"]] = seen.get(e["name"], 0) + 1
        e["id"] = e["name"] if seen[e["name"]] == 1 else "%s#%d" % (e["name"], seen[e["name"]])
    return out


def date_problem(date, rome):
    """None, or why the game would not read the date: Rome 'years [season]', Medieval II 'turn [turn]'."""
    t = (date or "").split()
    if not t or not t[0].isdigit():
        return "a date starts with a number (%s)" % ("years from the start" if rome else "the turn")
    if rome:
        if len(t) > 2 or (len(t) == 2 and t[1] not in ("summer", "winter")):
            return "Rome's date is years from the start and optionally summer or winter, like '14 winter'"
    elif len(t) > 2 or (len(t) == 2 and not t[1].isdigit()):
        return "Medieval II's date is a turn, or two turns (a random one between them), like '120' or '210 220'"
    return None


def later_factions(mod, campaign):
    """[(faction, [lines of the campaign script that wake it])] of the factions descr_strat keeps dead until the
    script brings them in (dead_until_resurrected)."""
    from .moddata import _ci
    f = mod.load(mod.campaign_file(campaign, "descr_strat.txt"))
    out, cur = [], None
    for l in f.texts():
        t = tokens(l)
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1]
        elif t[:1] == ["dead_until_resurrected"] and cur:
            out.append(cur)
    script = _ci(mod.campaign_dir(campaign), "campaign_script.txt") if mod.campaign_dir(campaign) else None
    lines = mod.load(script).texts() if script else []
    return [(fac, [" ".join(strip_comment(l).split()) for l in lines if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(fac),
                                                         strip_comment(l)) and "emergent_faction" in l])
            for fac in out]


def apply(plan, campaign, changes):
    """changes = {'edit': {id: {'date': text, 'position': [x, y] or None}}, 'remove': [ids],
    'new': [{'kind', 'name', 'date', 'position', 'title', 'body'}]}; texts of new / changed events: 'texts'
    {KEY: text}."""
    from .strtables import write_texts
    mod = plan.mod
    path = path_of(mod, campaign)
    if not path:
        raise ValueError("the campaign has no descr_events.txt")
    rome = _rome(mod)
    f = plan.edit(path)
    texts = dict(changes.get("texts") or {})
    for name, ch in sorted((changes.get("edit") or {}).items()):
        ev = next((e for e in read(f) if e["id"] == name), None)
        if ev is None:
            raise ValueError("no event called %s" % name)
        if ch.get("date") is not None:
            why = date_problem(ch["date"], rome)
            if why:
                raise ValueError("%s: %s" % (name, why))
            i = ev["lines"].get("date")
            if i is not None:
                text = f.text(i)
                m = re.match(r"^(\s*date\s+)", text)
                f.set(i, m.group(1) + ch["date"].strip() + _comment(text))
            else:
                f.insert(ev["lines"]["event"] + 1, ["date\t%s" % ch["date"].strip()])
            plan.note(f, "%s: date %s" % (name, ch["date"].strip()))
        if "position" in ch:
            ev = next(e for e in read(f) if e["id"] == name)
            i = ev["lines"].get("position")
            pos = ch["position"]
            if pos is None and i is not None:
                f.delete(i, i + 1)
                plan.note(f, "%s: no position (anywhere)" % name)
            elif pos is not None:
                line = "position\t%d, %d" % tuple(pos)
                if i is not None:
                    m = re.match(r"^(\s*position\s+)", f.text(i))
                    f.set(i, m.group(1) + "%d, %d" % tuple(pos) + _comment(f.text(i)))
                else:
                    f.insert(ev["lines"].get("date", ev["lines"]["event"]) + 1, [line])
                plan.note(f, "%s: position %d, %d" % (name, pos[0], pos[1]))
    gone = [e for e in read(f) if e["id"] in set(changes.get("remove") or [])]
    for ev in sorted(gone, key=lambda e: -e["span"][0]):        # from the end: the earlier lines keep their place
        name = ev["id"]
        a, b = ev["span"]
        while b < len(f) and not f.text(b).strip():
            b += 1                                      # the blank lines after it go with it
        f.delete(a, b)
        plan.note(f, "%s removed" % name)
    have = {e["name"].lower() for e in read(f)}
    for ev in changes.get("new") or []:
        name = (ev.get("name") or "").strip()
        if not RE_NAME.match(name):
            raise ValueError("'%s': an event's name is letters, digits and _ only, starting with a letter" % name)
        if name.lower() in have:
            raise ValueError("there is already an event called %s" % name)
        why = date_problem(ev.get("date"), rome)
        if why:
            raise ValueError("%s: %s" % (name, why))
        lines = ["", "event\t%s\t%s" % (ev.get("kind") or "historic", name), "date\t%s" % ev["date"].strip()]
        if ev.get("position"):
            lines.append("position\t%d, %d" % tuple(ev["position"]))
        f.insert(len(f.raw) - (1 if f.raw and not f.text(len(f.raw) - 1).strip() else 0), lines)
        have.add(name.lower())
        for part in ("title", "body"):
            if ev.get(part):
                texts["%s_%s" % (name.upper(), part.upper())] = ev[part]
        plan.note(f, "new event %s (%s, %s)" % (name, ev.get("kind") or "historic", ev["date"].strip()))
    write_texts(plan, "historic_events.txt", texts)


def _comment(text):
    """The comment at the end of a line, with the space before it ('' when none)."""
    code = strip_comment(text).rstrip()
    return text[len(code):] if text[len(code):].strip() else ""


def _rome(mod):
    from .limits import game_kind
    return game_kind(mod) != "medieval2"
