"""The campaign's events (world/maps/campaign/<campaign>/descr_events.txt), both games:

    event   plague      plague_in_macedonia         (kind, then the name: the key of its texts)
    date    14 winter                               (Rome: years from the start and a season; Medieval II: years
    position    138, 67                              from the start, or two - a random one between them)
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
    """[{'id', 'kind', 'name', 'date', 'position': (x, y) or None, 'region', 'movie', 'span': (a, b), 'lines': {word: line}}]
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
                   "region": "", "movie": "", "span": (i, i + 1), "lines": {"event": i}}
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
        elif word == "region":                  # a region instead of a position (both games' comments)
            cur["region"] = rest.split()[0] if rest else ""
    seen = {}
    for e in out:                       # one name may be used twice (vanilla Rome: plague_in_italy): name, name#2
        seen[e["name"]] = seen.get(e["name"], 0) + 1
        e["id"] = e["name"] if seen[e["name"]] == 1 else "%s#%d" % (e["name"], seen[e["name"]])
    return out


def date_problem(date, rome):
    """None, or why the game would not read the date: Rome 'years [season]', Medieval II 'years [years]'."""
    t = (date or "").split()
    if not t or not t[0].isdigit():
        return "a date starts with a number (%s)" % ("years from the start" if rome else "the turn")
    if rome:
        if len(t) > 2 or (len(t) == 2 and t[1] not in ("summer", "winter")):
            return "Rome's date is years from the start and optionally summer or winter, like '14 winter'"
    elif len(t) > 2 or (len(t) == 2 and not t[1].isdigit()):
        return "Medieval II's date is years from the start, or two numbers (a random year between them), like '120' or '210 220'"
    return None


def date_key(date, rome):
    """A number to sort dates by (the earliest first): Rome years x 2 (+1 for winter), Medieval II the first year.
    Both games read descr_events.txt as a queue in date order - an event put after a later one never fires (the
    a tester's test mod: Rome's events written at the file's end never came)."""
    t = (date or "").split()
    if not t or not t[0].isdigit():
        return None
    return int(t[0]) * 2 + (1 if rome and len(t) > 1 and t[1] == "winter" else 0) if rome else int(t[0])


def calendar(mod, campaign):
    """(start year, start season, years per turn) of the campaign from descr_strat.txt: start_date '-270 summer' /
    '1080 summer', timescale (Medieval II; Rome's turn is half a year unless the file says otherwise)."""
    rome = _rome(mod)
    year, season, scale = (-270 if rome else 1080), "summer", (0.5 if rome else 2.0)
    try:
        f = mod.load(mod.campaign_file(campaign, "descr_strat.txt"))
    except Exception:
        return year, season, scale
    for l in f.texts():
        t = tokens(l)
        if t[:1] == ["start_date"] and len(t) > 1:
            try:
                year = int(t[1])
            except ValueError:
                pass
            season = t[2] if len(t) > 2 else season
        elif t[:1] == ["timescale"] and len(t) > 1:
            try:
                scale = float(t[1]) or scale
            except ValueError:
                pass
        elif t[:1] == ["faction"]:
            break
    return year, season, scale


def year_words(year):
    return "%d BC" % -year if year < 0 else ("%d AD" % year if year < 1000 else str(year))


def when(mod, campaign, date):
    """'turn 4, 269 BC winter' - the turn and the year a date of descr_events.txt means ('' when not a date)."""
    rome = _rome(mod)
    if date_problem(date, rome):
        return ""
    start, season, scale = calendar(mod, campaign)
    out = []
    for part in ([date] if rome else date.split()[:2]):
        t = part.split()
        years = int(t[0])
        if rome:
            half = years * 2 + (1 if len(t) > 1 and t[1] == "winter" else 0) + (1 if season == "winter" else 0)
            turn = int(round(half * 0.5 / scale)) + 1
            out.append("turn %d, %s %s" % (turn, year_words(start + half // 2), "winter" if half % 2 else "summer"))
        else:
            turn = int(years / scale) + 1
            out.append("turn %d, year %s" % (turn, year_words(start + years)))
    return " to ".join(out)


def turn_date(mod, campaign, turn):
    """The date text of descr_events.txt for a turn (1 = the first): Rome 'years season', Medieval II 'years'."""
    start, season, scale = calendar(mod, campaign)
    if _rome(mod):
        half = int(round((turn - 1) * scale * 2)) + (1 if season == "winter" else 0)
        return "%d %s" % (half // 2, "winter" if half % 2 else "summer")
    return str(int(round((turn - 1) * scale)))


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
    {KEY: text}; 'pictures' {event name: picture file} - its scroll picture for every culture."""
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
        # in date order: the games read the events as a queue (date_key)
        key = date_key(ev["date"], rome)
        later = [e for e in read(f) if date_key(e["date"], rome) is not None and date_key(e["date"], rome) > key]
        if later:
            at = later[0]["span"][0]
            while at > 0 and f.text(at - 1).lstrip().startswith(";"):
                at -= 1                                 # the comment lines right above the later event stay on it
            f.insert(at, lines[1:] + [""])
        else:
            f.insert(len(f.raw) - (1 if f.raw and not f.text(len(f.raw) - 1).strip() else 0), lines)
        have.add(name.lower())
        if (ev.get("kind") or "historic") == "historic":
            # the game shows a historic event's title and body on its scroll and stops on a missing one
            # ("ASSERT FAILED: event_manager.cpp: description_string" - a tester's test mod, both games)
            ev = dict(ev, body=ev.get("body") or ev.get("text") or ev.get("title") or name.replace("_", " "),
                      title=ev.get("title") or name.replace("_", " "))
        for part in ("title", "body"):
            if ev.get(part):
                texts["%s_%s" % (name.upper(), part.upper())] = ev[part]
        plan.note(f, "new event %s (%s, %s)" % (name, ev.get("kind") or "historic", ev["date"].strip()))
    write_texts(plan, "historic_events.txt", texts)
    for name, src in sorted((changes.get("pictures") or {}).items()):
        set_picture(plan, name, src)


# what each kind does in the game (both games' engines; the strength of the random disasters in descr_disasters.txt)
WHAT = {
    "historic": "A message only: the scroll opens on that date with its title, picture and text; nothing else "
                "happens in the game (a campaign script may react to it by its name).",
    "plague": "A plague breaks out in the town nearest the place: its people fall ill and die over the turns, its "
              "growth and order drop, and armies, agents and traders carry it on to other towns. Without a place "
              "it strikes a town of the engine's choosing.",
    "volcano": "The volcano at the place erupts: buildings in the region nearest it are damaged or destroyed and "
               "people die (the map shows the eruption).",
    "earthquake": "An earthquake around the place: buildings of the town nearest it are damaged or destroyed and "
                  "people die.",
    "flood": "A flood around the place: buildings and farmland of the nearest town are damaged, people die.",
    "storm": "A storm at sea around the place: fleets there lose ships and men.",
    "horde": "A horde rises (Medieval II: the Mongols / Timurids) - with the faction's own script.",
    "dustbowl": "A dust storm (Medieval II): the farms around the place yield less.",
    "locusts": "Locusts (Medieval II): the farms around the place yield less.",
}


def what_it_does(kind):
    return WHAT.get(kind, "The engine's own %s event (what it does is the game's - not described here)." % kind)


def picture_name(name, kind):
    """The eventpics picture the game shows on the scroll: a historic event its own (ui/<culture>/eventpics/<name>.tga
    - each culture's folder; none: no picture), a disaster the shared disaster_<kind>.tga."""
    return name if kind == "historic" else "disaster_%s" % kind


def event_cultures(mod):
    """[culture folder] of ui/ that hold eventpics (the mod's own, else the game's)."""
    from .campaignrules import game_data
    out = []
    for data in (mod.data, game_data(mod)):
        ui = os.path.join(data, "ui") if data else None
        if ui and os.path.isdir(ui):
            for c in sorted(os.listdir(ui)):
                if os.path.isdir(os.path.join(ui, c, "eventpics")) and c not in out:
                    out.append(c)
    return out


def picture_files(mod, name, kind):
    """{culture: picture file on disk or None} of an event (the mod's own, else the game's copy)."""
    from .campaignrules import game_data
    from .clone import picture_file
    pic = picture_name(name, kind)
    out = {}
    for c in event_cultures(mod):
        rel = "ui/%s/eventpics/%s.tga" % (c, pic)
        got = None
        for data in (mod.data, game_data(mod)):
            if data and not got:
                got = picture_file(data, rel)
        out[c] = got[1] if got else None
    return out


def set_picture(plan, name, src, size=None):
    """The picture players see on a historic event's scroll: src (any picture) as ui/<culture>/eventpics/<name>.tga
    in every culture folder of the mod (the game picks the player's culture), sized like the game's own (Rome
    360 x 160, Medieval II 367 x 148) unless size is given."""
    from .editors import tga_bytes
    mod = plan.mod
    if size is None:
        size = (360, 160) if _rome(mod) else (367, 148)
    data = tga_bytes(src, size)
    cultures = event_cultures(mod)
    if not cultures:
        raise ValueError("no ui/<culture>/eventpics folders in this mod or its game")
    for c in cultures:
        plan.binary(os.path.join(mod.data, "ui", c, "eventpics", "%s.tga" % name), data)
    plan.notes.append(("ui/<culture>/eventpics/%s.tga" % name, "the event's picture for %d culture(s): %s" % (
        len(cultures), ", ".join(cultures))))


def _comment(text):
    """The comment at the end of a line, with the space before it ('' when none)."""
    code = strip_comment(text).rstrip()
    return text[len(code):] if text[len(code):].strip() else ""


def _rome(mod):
    from .limits import game_kind
    return game_kind(mod) != "medieval2"
