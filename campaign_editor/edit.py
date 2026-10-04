"""Edit a faction that already exists: its names and descriptions, colours, AI,
treasury, playability, and the garrisons and buildings of its towns. The same
Plan as a new faction, so preview, backup and restore work alike."""

import re

from .build import template_display, validate
from .clone import FE_NAMES, description_key, entry_end
from .plan import Plan
from .start import MAX_UNITS, _has_army, _units, unit_name
from .strat import first_names, RE_XY, Strat, character_line, village_block
from .textio import tokens

RE_RGB = re.compile(r"red\s*(\d+)\s*,\s*green\s*(\d+)\s*,\s*blue\s*(\d+)")
RE_KEY = re.compile(r"^(\s*\{)([A-Za-z0-9_]+)(\}.*)$")


def _unescape(v):
    """A string value as text: '\\n' is a line break; the file's own line breaks
    inside a long value are only wrapping."""
    return " ".join(x.strip() for x in v.splitlines()).replace("\\n", "\n").strip()


def _value(texts, i):
    """The whole value of the entry at line i (a long text spans lines)."""
    end = entry_end(texts, i)
    first = RE_KEY.match(texts[i]).group(3)[1:]
    return "\n".join([first] + texts[i + 1:end])


# Medieval II's faction-select screen: {FRANCE_STRENGTH}, {FRANCE_WEAKNESS}, {FRANCE_UNIT}
EXTRA_TEXTS = {"_STRENGTH": "strength", "_WEAKNESS": "weakness", "_UNIT": "unit_text"}


def read_faction(mod, campaign, faction):
    """What the faction is now: {display_name, short_name, adjective, description,
    long_description, primary_colour, secondary_colour, ai, denari, playable, regions}."""
    out = dict(template_display(mod, faction, campaign))
    F = faction.upper()
    keys = {m.group(2).upper() for p in mod.campaign_text_files(campaign) for l in mod.load(p).texts()
            for m in [RE_KEY.match(l)] if m}
    long_key = description_key(faction, campaign, keys) + "_DESCR"
    for path in mod.campaign_text_files(campaign):
        texts = mod.load(path).texts()
        for i, line in enumerate(texts):
            m = RE_KEY.match(line)
            if not m or not m.group(2).upper().endswith(("DESCR", "_STRENGTH", "_WEAKNESS", "_UNIT")):
                continue
            key, val = m.group(2).upper(), _value(texts, i)
            extra = EXTRA_TEXTS.get(key[len(F):]) if key.startswith(F + "_") else None
            if extra and extra not in out:
                out[extra] = _unescape(val)         # Medieval II's faction screen: strengths, weaknesses, unit
            elif key == F + "_DESCR" and "description" not in out:
                out["description"] = _unescape(val)
            elif key == long_key and "long_description" not in out:
                out["long_description"] = _unescape(val)
    cur = None
    for l in mod.load(mod.file("sm_factions")).texts():
        t = tokens(l)
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1]
        elif cur == faction and t[:1] in (["primary_colour"], ["secondary_colour"]):
            m = RE_RGB.search(l)
            if m:
                out[t[0]] = tuple(int(x) for x in m.groups())
    s = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
    fb = s.faction(faction)
    if not fb:
        raise ValueError("%s has no faction block in this campaign's descr_strat.txt" % faction)
    out["ai"] = " ".join(tokens(fb.header)[2:])
    for i in range(fb.start, fb.end):
        t = tokens(s.lines[i])
        if t[:1] == ["denari"] and len(t) > 1:
            out["denari"] = int(t[1]) if t[1].isdigit() else t[1]
            break
    out["playable"] = bool(s.playable and faction in [n for _, n in s.playable["items"]])
    from .religions import faction_religion
    rel = faction_religion(mod, faction)
    if rel:
        out["religion"] = rel                                     # Medieval II
    out["regions"] = [st.region for st in fb.settlements]
    for c in fb.characters:
        if c.role in ("leader", "heir") and c.role not in out:
            m = re.search(r"\bage\s+(\d+)", s.lines[c.start])
            out[c.role] = {"name": c.name, "age": int(m.group(1)) if m else None}
    return out


def edit(mod, campaign, faction, opts):
    """A Plan with the changes in opts (only the keys given are changed):
    display_name, short_name, adjective, description, long_description,
    primary_colour, secondary_colour, ai, denari, playable,
    garrisons {region: [unit types]}, buildings {region: [(chain, level)]}."""
    names = [n for n, _ in mod.factions()]
    if faction not in names:
        raise ValueError("pick an existing faction to edit")
    now = read_faction(mod, campaign, faction)
    plan = Plan(mod, faction, faction, dict(opts))
    _texts(plan, now, campaign)
    _colours(plan)
    # new regions first: a new town given to this faction is then one of its towns for the
    # garrisons, buildings and capital below (one Apply, one backup)
    if opts.get("names"):                  # before anything that picks names (captains, records)
        from .namelists import apply as apply_names
        apply_names(plan, faction, opts["names"])
    if opts.get("regions"):
        from .regionedit import apply_opts as apply_region_opts
        apply_region_opts(plan, campaign, opts["regions"])
    if opts.get("religion") and opts["religion"] != now.get("religion"):   # after a new religion is written
        from .religions import set_faction_religion
        set_faction_religion(plan, faction, opts["religion"])
    _strat(plan, campaign, now)
    if opts.get("places"):
        from .mapedit import apply_places
        apply_places(plan, campaign, opts["places"])
    if opts.get("resources"):
        from .resources import apply as apply_resources
        apply_resources(plan, campaign, opts["resources"])
    if opts.get("relations"):
        from .diplomacy import apply_opts
        apply_opts(plan, campaign, faction, opts["relations"])
    if opts.get("victory"):
        from .wincond import apply_opts as apply_victory
        apply_victory(plan, campaign, faction, opts["victory"], opts)
    if opts.get("roster"):
        from .roster import apply as apply_roster
        apply_roster(plan, faction, opts["roster"], campaign)
        taken = {k[5:] for k, v in opts["roster"].items() if k.startswith("unit:") and v is False}
        for region, units in (opts.get("garrisons") or {}).items():
            gone = sorted(set(units) & taken)
            if gone:
                plan.warn(None, "%s's new garrison has %s, taken away on the Roster" % (region, ", ".join(gone)))
    if opts.get("figures"):                   # before the art: a figure's new texture line may get a picture
        from .stratmodels import apply as apply_figures
        apply_figures(plan, faction, opts["figures"])
    from .factionart import apply_opts as apply_art
    plan.opts["_primary_changed"] = bool(opts.get("primary_colour")) and \
        tuple(opts["primary_colour"]) != tuple(now.get("primary_colour") or ())
    given = set(opts.get("give") or {})
    towns = [r for r in now["regions"] if r not in given] + [r for r in opts.get("take") or [] if r not in now["regions"]]
    apply_art(plan, campaign, faction, towns, opts.get("primary_colour") or now.get("primary_colour"),
              towns_changed=bool(opts.get("take") or given))
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    if sp in plan.files:
        from .strat import characters_after_tree
        bad = characters_after_tree(Strat(plan.files[sp]))
        if bad:
            raise ValueError("internal check failed - a character would follow the family tree of %s "
                             "(the game crashes on that); nothing written" % ", ".join(bad))
        from .strat import check_names
        from .textio import TextFile
        check_names(Strat(TextFile.load(sp)), Strat(plan.files[sp]))
        s = Strat(plan.files[sp])
        tiles = plan_tiles(plan, campaign)
        fb = s.faction(faction)
        held = {c.xy for c in fb.characters if c.xy and _has_army(s.lines[c.start:c.end])}
        empty = [st.region for st in fb.settlements if tiles.get(st.region) not in held]
        if empty and plan.changed_files():
            plan.warn(plan.files[sp], "no army in %s - the town(s) start without a garrison"
                      % ", ".join(empty))
    if plan.opts.get("garrisons") or plan.opts.get("buildings"):
        plan.edit(mod.file("edu"))            # validate() reads these through the plan
        plan.edit(mod.file("sm_factions"))
        validate(plan, campaign)
        plan.warnings = [w for w in plan.warnings if "factions (slave included)" not in w[1]]
    if not plan.changed_files():
        plan.note(None, "nothing to change")
    return plan


# ---------------------------------------------------------------------------
def _texts(plan, now, campaign):
    o, F = plan.opts, plan.new.upper()
    pairs = []
    for k in ("display_name", "short_name", "adjective"):
        old, new = now.get(k), o.get(k)
        if old and new and old != new:
            pairs += [(old, new)] + ([(old.upper(), new.upper())] if old.upper() != old else [])
    pairs.sort(key=lambda p: -len(p[0]))
    set_to = {}
    if o.get("display_name") and o["display_name"] != now.get("display_name"):
        set_to[F] = o["display_name"]
    if o.get("description") is not None and o.get("description") != now.get("description"):
        set_to[F + "_DESCR"] = o["description"]
    for suffix, k in EXTRA_TEXTS.items():
        if k in now and o.get(k) is not None and o[k] != now[k]:
            set_to[F + suffix] = o[k]
    long_new = o.get("long_description")
    if long_new is not None and long_new != now.get("long_description"):
        keys = {m.group(2).upper() for p in plan.mod.campaign_text_files(campaign)
                for l in plan.mod.load(p).texts() for m in [RE_KEY.match(l)] if m}
        set_to[description_key(plan.new, campaign, keys) + "_DESCR"] = long_new
    if not pairs and not set_to:
        return
    fe = FE_NAMES.get(plan.new)
    word = re.compile(r"(?<![A-Z0-9])(%s)(?![A-Z0-9])" % "|".join(re.escape(x) for x in (F, fe) if x))
    for path in plan.mod.campaign_text_files(campaign):
        # region labels, and the rebels' names: {Gauls} there is a rebel type, not the faction
        if "regions_and_settlement_names" in path.lower() or "rebel_faction_descr" in path.lower():
            continue
        f = None
        texts = plan.mod.load(path).texts()
        edits = []                                  # (start, end, new lines)
        i = 0
        while i < len(texts):
            m = RE_KEY.match(texts[i])
            if not m:
                i += 1
                continue
            end = entry_end(texts, i)
            if word.search(m.group(2).upper()):
                key = m.group(2).upper()
                value = m.group(3)[1:]
                gap = value[:len(value) - len(value.lstrip())]
                old = [value] + texts[i + 1:end]
                if key in set_to:
                    new = [gap + set_to[key].replace("\n", "\\n")]
                else:
                    new = list(old)
                    for a, b in pairs:
                        new = [re.sub(r"(?<![A-Za-z])%s(?![a-z])" % re.escape(a), b, x) for x in new]
                if new != old:
                    edits.append((i, end, [m.group(1) + m.group(2) + "}" + new[0]] + new[1:]))
            i = end
        if edits:
            f = plan.edit(path)
            for a, b, lines in reversed(edits):
                f.raw[a:b] = [f.make(x) for x in lines]
            plan.note(f, "%d string(s) changed" % len(edits))


def _colours(plan):
    o = plan.opts
    set_faction_colours(plan, plan.new, o.get("primary_colour"), o.get("secondary_colour"))


def set_faction_colours(plan, faction, primary=None, secondary=None):
    """The faction's primary / secondary colour lines in descr_sm_factions.txt (and REX's .json when there is
    one) - the one writer, used by the Faction tab and by Recolour (its 'to' colours become the faction's)."""
    want = {"primary_colour": primary, "secondary_colour": secondary}
    if not (primary or secondary):
        return
    f = plan.edit(plan.mod.file("sm_factions"))
    cur, n = None, 0
    for i in range(len(f)):
        t = tokens(f.text(i))
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1].rstrip(",")
        elif cur == faction and t[:1] in (["primary_colour"], ["secondary_colour"]):
            rgb = want.get(t[0])
            if rgb:
                new = RE_RGB.sub("red %d, green %d, blue %d" % tuple(rgb), f.text(i), 1)
                if new != f.text(i):
                    f.set(i, new)
                    n += 1
    if n:
        plan.note(f, "colours of %s set" % faction)
    path = plan.mod.file("sm_factions_json")
    if not path:
        return
    j = plan.edit(path)
    inside = depth = 0
    for i in range(len(j)):
        line = j.text(i)
        if not inside and re.match(r'\s*"%s"\s*:' % re.escape(faction), line):
            inside, depth = 1, 0
        if inside:
            for key in ("primary", "secondary"):
                rgb = want.get(key + "_colour")
                if rgb and re.match(r'\s*"%s"\s*:\s*\[' % key, line):
                    j.set(i, re.sub(r"\[[^\]]*\]", "[ %d, %d, %d ]" % tuple(rgb), line, count=1))
            depth += line.count("{") - line.count("}")
            if "{" in line or depth:
                inside = 2
            if inside == 2 and depth <= 0:
                inside = 0


def _strat(plan, campaign, now):
    o, fac = plan.opts, plan.new
    path = plan.mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(path)
    s = Strat(f)
    fb = s.faction(fac)
    # the header line: faction <name>, <ai>
    if o.get("ai") and o["ai"] != now.get("ai"):
        f.set(fb.start, re.sub(r"^(\s*faction\s+%s\s*,\s*).*$" % re.escape(fac), r"\g<1>" + o["ai"], f.text(fb.start)))
        plan.note(f, "AI set to %s" % o["ai"])
    if o.get("denari") not in (None, "") and str(o["denari"]) != str(now.get("denari")):
        for i in range(fb.start, fb.end):
            if tokens(f.text(i))[:1] == ["denari"]:
                f.set(i, re.sub(r"(denari\s+)\S+", r"\g<1>%d" % int(o["denari"]), f.text(i), count=1))
                plan.note(f, "denari set to %d" % int(o["denari"]))
                break
    if o.get("playable") is not None and bool(o["playable"]) != now.get("playable"):
        if fac == "slave":
            raise ValueError("the rebels (slave) cannot be made playable")
        _move_list(plan, f, fac, bool(o["playable"]))
    if o.get("army_units") or o.get("remove"):
        _army_edits(plan, f)
    if o.get("moves"):
        _moves(plan, f, campaign)
    if o.get("take") or o.get("give"):
        _towns(plan, f, campaign)
    if o.get("family"):
        from .family import apply as apply_family
        apply_family(plan, f, fac, o["family"])
    _people(plan, f, now)
    if o.get("capital") and fac != "slave":           # rebels have no capital
        _capital(plan, f, o["capital"])
    if o.get("characters"):
        from .start import extra_characters
        s = Strat(f)
        armies = {c.xy for x in s.factions for c in x.characters if c.xy and _has_army(s.lines[c.start:c.end])}
        lines = extra_characters(plan, f, campaign, o["characters"], plan.name_pool(fac) or {}, armies)
        at = _chars_at(f, s.faction(fac))
        f.raw[at:at] = lines
    s = Strat(f)
    _garrisons(plan, f, s, campaign)
    _buildings(plan, f, Strat(f))


def _chars_at(f, fb):
    """Where new characters go in a faction block: before its family tree. A
    character line after character_record / relative lines crashes the game
    (on load, or when the diplomacy scroll lists the factions)."""
    return next((i for i in range(fb.start, fb.end)
                 if f.text(i).split(None, 1)[:1] in (["character_record"], ["relative"])), fb.end)


def _towns(plan, f, campaign):
    """Take towns from other owners (opts['take'] = [region]) and give towns away
    (opts['give'] = {region: new owner}). The whole settlement block moves.
    In a town that changes hands: the old owner's named characters and agents
    go to one of its other towns (next to it if that town has an army already);
    a captain with a garrison (not named) goes with the town to its new owner,
    except rebels leaving a town, who simply go."""
    fac = plan.new
    owners = _owners_now(plan.mod, campaign, f)
    moves = [(r, owners.get(r), fac) for r in plan.opts.get("take") or []]
    moves += [(r, fac, to or "slave") for r, to in (plan.opts.get("give") or {}).items()]
    move_towns(plan, f, campaign, moves, fac, plan.opts.get("take") or [])


def _owners_now(mod, campaign, f):
    """{region: owner} of descr_strat as f holds it - a region with no settlement block is the game's rebel village."""
    s = Strat(f)
    tiles = mod.city_tiles(campaign)
    owners = s.owners()
    owners.update({r: "slave" for r in mod.regions(campaign) if r not in owners and tiles.get(r)})
    return owners


def move_towns(plan, f, campaign, moves, fac=None, taking=()):
    """Towns change hands: moves [(region, old owner, new owner)] - the whole settlement block moves; in a town
    that changes hands the old owner's named characters and agents go to one of its other towns (fac's towns
    being taken count as its own), a captain with a garrison goes with the town, rebels leaving simply go.
    Shared by Edit faction's take / give and the Map's 'give this town to' for any faction."""
    mod = plan.mod
    s = Strat(f)
    tiles = mod.city_tiles(campaign)
    for r, old, new in moves:
        if old is None:
            raise ValueError("%s has no settlement in descr_strat.txt" % r)
        if old == new:
            raise ValueError("%s already belongs to %s" % (r, new))
        if not s.faction(new):
            raise ValueError("%s has no faction block in descr_strat.txt" % new)
    moving = {r for r, _, _ in moves}
    taken = set(tiles.values()) | {c.xy for fb in s.factions for c in fb.characters if c.xy}
    armies_at = {c.xy for fb in s.factions for c in fb.characters
                 if c.xy and _has_army(s.lines[c.start:c.end])}
    sets, cuts, to_add = {}, [], {}        # line -> text; (start, end); owner -> {"towns": [], "chars": []}
    for r, old, new in moves:
        st = s.settlement_of(r)
        if st is None:                          # the game's rebel village, written out
            block = [f.make(l) for l in village_block(r, new)]
            plan.note(f, "%s: the rebel village (no settlement in descr_strat.txt) is written as a village" % r)
        else:
            cuts.append((st.start, st.end))
            block = list(f.raw[st.start:st.end])
        to_add.setdefault(new, {"towns": [], "chars": []})["towns"].append(block)
        xy = tiles.get(r)
        ob = s.faction(old)
        for c in [c for c in ob.characters if xy and c.xy == xy]:
            army = _has_army(s.lines[c.start:c.end])
            if old == "slave":                  # rebels do not move anywhere: they leave with the town
                cuts.append((c.start, c.end))
                armies_at.discard(c.xy)
                plan.note(f, "%s: the rebel %s leaves" % (r, c.name))
                continue
            if army and not c.named:
                cuts.append((c.start, c.end))
                armies_at.discard(c.xy)
                if old == "slave":
                    plan.note(f, "%s: the rebel garrison of %s leaves" % (r, c.name))
                else:
                    chunk = list(f.raw[c.start:c.end])
                    chunk[0] = re.sub(r"(character\s*,?\s*)sub_faction\s+\S+\s*,\s*", r"\1", chunk[0], count=1)
                    to_add[new]["chars"].append(chunk)
                    plan.note(f, "%s: captain %s and his garrison go over to %s" % (r, c.name, new))
                continue
            keep = [x.region for x in ob.settlements if x.region not in moving and tiles.get(x.region)]
            if old == fac:                  # the towns this faction takes are its own too
                keep += [t for t in taking if tiles.get(t)]
            if not keep:
                raise ValueError("%s: %s of %s stands in the town and %s has no other town to go to"
                                 % (r, c.name, old, old))
            dest = tiles[keep[0]]
            if army and dest in armies_at:
                from .regionedit import plan_land
                ptiles, own = plan_land(plan, campaign)
                dest = mod.free_tile(campaign, keep[0], taken, start=ptiles.get(keep[0]), own=own(keep[0]))
                if not dest:
                    raise ValueError("%s: no free tile next to %s for %s" % (r, keep[0], c.name))
            taken.add(dest)
            if army:
                armies_at.add(dest)
            sets[c.start] = RE_XY.sub("x %d, y %d" % dest, f.text(c.start), 1)
            plan.note(f, "%s: %s of %s moves to %s" % (r, c.name, old, keep[0]))
        plan.note(f, "%s: %s -> %s" % (r, old, new))
    for i, text in sets.items():
        f.set(i, text)
    for a, b in sorted(cuts, reverse=True):
        del f.raw[a:b]
    for owner, add in to_add.items():
        s = Strat(f)
        fb = s.faction(owner)
        if add["chars"]:
            at = _chars_at(f, fb)
            f.raw[at:at] = [l for ch in add["chars"] for l in ch + [f.make("")]]
        if fb.settlements:
            at = fb.settlements[-1].end
        else:
            at = next((i + 1 for i in range(fb.start, fb.end) if tokens(f.text(i))[:1] == ["denari"]), fb.start + 1)
        f.raw[at:at] = [l for t in add["towns"] for l in t]
    for who in {old for _, old, _ in moves if old and old != "slave"}:
        fb = Strat(f).faction(who)
        if fb is not None and not fb.settlements:
            plan.warn(f, "%s is left with no town - it starts as a horde or dies on turn 1" % who)


def first_units(mod, campaign, faction, kind, xy):
    """[unit] for a new army / fleet of faction placed on the Map: the first unit of its nearest army (a fleet:
    of its nearest fleet) - the general's bodyguard -, else the first unit it may own (ships for a fleet).
    Its units can be changed afterwards in Edit faction > Units & armies."""
    from .start import unit_name
    from .units import faction_units
    s = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))
    fb = s.faction(faction)
    best = None
    for c in (fb.characters if fb else []):
        lines = s.lines[c.start:c.end]
        if not c.xy or not _has_army(lines):
            continue
        if (c.kind == "admiral") != (kind == "fleet"):
            continue
        d = (c.xy[0] - xy[0]) ** 2 + (c.xy[1] - xy[1]) ** 2
        first = next((unit_name(l) for l in lines if tokens(l)[:1] == ["unit"]), None)
        if first and (best is None or d < best[0]):
            best = (d, first)
    if best:
        return [best[1]]
    owned = faction_units(mod, faction, ships=kind == "fleet")
    return [owned[0].type] if owned else []


def map_changes(plan, campaign, changes):
    """What the Map changed for factions other than the one being made or edited (or with none picked - the Map
    editor): changes = {'owners': {region: new owner}, 'characters': {faction: [character dicts as
    start.extra_characters takes them]}, 'remove': {faction: [{'name', 'from': (x, y)}]}, 'moves': {faction:
    [{'name', 'from', 'to'}]}, 'army_units': {faction: [{'name', 'from', 'units'}]}} - written into the plan's
    descr_strat.txt like the edited faction's own changes. A removed character goes with his whole block (his army
    or fleet too); a member of the family tree is refused (the relative lines name him)."""
    if not changes or not any(changes.get(k) for k in ("owners", "characters", "remove", "moves", "army_units")):
        return
    from .start import extra_characters
    f = plan.edit(plan.mod.campaign_file(campaign, "descr_strat.txt"))
    gone = []
    for fac, items in (changes.get("remove") or {}).items():
        fb = Strat(f).faction(fac)
        if fb is None:
            raise ValueError("%s has no faction block in descr_strat.txt" % fac)
        for m in items:
            src = tuple(m["from"])
            c = next((c for c in fb.characters if c.name == m["name"] and c.xy == src), None)
            if c is None:
                raise ValueError("%s at %d, %d is not a character of %s" % (m["name"], src[0], src[1], fac))
            if c.role:
                raise ValueError("%s is %s's %s - the faction needs him; make another the %s first" % (
                    c.name, fac, c.role, c.role))
            if c.named and any(t.split()[:1] == ["relative"] and c.name in t
                               for t in f.texts()[fb.start:fb.end] if t.strip()):
                raise ValueError("%s is on %s's family tree - take him off it in the Character editor first (the "
                                 "relative lines name him)" % (c.name, fac))
            gone.append((c.start, c.end, "%s %s (%s) at %d, %d removed with everything under him" % (
                fac, c.name, c.kind, src[0], src[1])))
    for start, end, note in sorted(gone, reverse=True):
        del f.raw[start:end]
        plan.note(f, note)
    # units first (found where they stand in the file), then the moves, before towns change hands (moving a town's
    # owner moves the characters standing in it)
    for fac, items in (changes.get("army_units") or {}).items():
        if items:
            _army_edits(plan, f, fac, units=items, remove=[])
    for fac, items in (changes.get("moves") or {}).items():
        if items:
            _moves(plan, f, campaign, fac, items)
    if changes.get("owners"):
        now = _owners_now(plan.mod, campaign, f)
        moves = [(r, now.get(r), to) for r, to in changes["owners"].items() if now.get(r) != to]
        move_towns(plan, f, campaign, moves)
    for fac, chars in (changes.get("characters") or {}).items():
        if not chars:
            continue
        s = Strat(f)
        fb = s.faction(fac)
        if fb is None:
            raise ValueError("%s has no faction block in descr_strat.txt" % fac)
        armies = {c.xy for x in s.factions for c in x.characters if c.xy and _has_army(s.lines[c.start:c.end])}
        lines = extra_characters(plan, f, campaign, chars, plan.name_pool(fac) or {}, armies, owner=fac)
        at = _chars_at(f, fb)
        f.raw[at:at] = lines


def _army_edits(plan, f, faction=None, units=None, remove=None):
    """Characters already on the map: opts['army_units'] = [{'name', 'from', 'units'}]
    replaces an army's or fleet's units (a named character keeps his bodyguard);
    opts['remove'] = [{'name', 'from'}] takes out agents, captains and admirals
    (never a family member - the family tree names them). faction / units / remove: another faction's (the Map
    editor), in place of the edited faction's opts."""
    faction = faction or plan.new
    if units is None and remove is None:
        units, remove = plan.opts.get("army_units"), plan.opts.get("remove")
    s = Strat(f)
    fb = s.faction(faction)
    if fb is None:
        raise ValueError("%s has no faction block in descr_strat.txt" % faction)
    jobs = []
    for m in units or []:
        jobs.append(("units", m))
    for m in remove or []:
        jobs.append(("remove", m))
    found = []
    for what, m in jobs:
        src = tuple(m["from"])
        c = next((c for c in fb.characters if c.name == m["name"] and c.xy == src), None)
        if c is None:
            raise ValueError("%s at %d, %d is not a character of %s" % (m["name"], src[0], src[1], faction))
        if what == "remove" and c.named:
            raise ValueError("%s is a member of the family - the tool does not remove those" % c.name)
        found.append((c, what, m))
    for c, what, m in sorted(found, key=lambda x: -x[0].start):
        chunk = f.texts()[c.start:c.end]
        if what == "remove":
            del f.raw[c.start:c.end]
            plan.note(f, "%s (%s) at %d, %d removed" % (c.name, c.kind, c.xy[0], c.xy[1]))
            continue
        units = [i for i, l in enumerate(chunk) if tokens(l)[:1] == ["unit"]]
        if not units:
            raise ValueError("%s has no army to change" % c.name)
        if not m.get("units"):
            raise ValueError("%s: an army or fleet needs at least one unit (remove it instead)" % c.name)
        keep = units[:1] if c.named else []
        room = MAX_UNITS - len(keep)
        lines = ["unit\t\t%s\t\t\t\texp 0 armour 0 weapon_lvl 0" % t for t in m["units"]][:room]
        new = [l for i, l in enumerate(chunk) if i not in units or i in keep]
        at = units[0] + len(keep)
        new[at:at] = lines
        f.raw[c.start:c.end] = [f.make(l) for l in new]
        plan.note(f, "%s (%s): %d unit(s)%s" % (c.name, c.kind, len(lines), " + his bodyguard" if keep else ""))


def _moves(plan, f, campaign, faction=None, moves=None):
    """opts['moves'] = [{'name', 'from': (x, y), 'to': (x, y)}]: characters of
    the faction moved on the map, checked like the window checks them (faction / moves: another faction's, the
    Map editor)."""
    faction = faction or plan.new
    s = Strat(f)
    fb = s.faction(faction)
    if fb is None:
        raise ValueError("%s has no faction block in descr_strat.txt" % faction)
    armies_at = {c.xy for x in s.factions for c in x.characters if c.xy and _has_army(s.lines[c.start:c.end])}
    for m in plan.opts["moves"] if moves is None else moves:
        src, dst = tuple(m["from"]), tuple(m["to"])
        c = next((c for c in fb.characters if c.name == m["name"] and c.xy == src), None)
        if c is None:
            raise ValueError("%s at %d, %d is not a character of %s" % (m["name"], src[0], src[1], faction))
        army = _has_army(s.lines[c.start:c.end])
        why = plan.mod.tile_problem(campaign, dst, c.kind, army, armies_at - {src})
        if why:
            raise ValueError("%s cannot go to %d, %d: %s" % (c.name, dst[0], dst[1], why))
        if army:
            armies_at.discard(src)
            armies_at.add(dst)
        f.set(c.start, RE_XY.sub("x %d, y %d" % dst, f.text(c.start), 1))
        plan.note(f, "%s moved from %d, %d to %d, %d" % (c.name, src[0], src[1], dst[0], dst[1]))


def _people(plan, f, now):
    """New names (from the faction's own name list) and ages for leader and heir."""
    pool = plan.name_pool(plan.new) or {}
    fb = Strat(f).faction(plan.new)
    for role in ("leader", "heir"):
        want, have = plan.opts.get(role), now.get(role)
        if not want or not have:
            continue
        c = next((c for c in fb.characters if c.role == role), None)
        if c is None:
            continue
        name = (want.get("name") or have["name"]).strip()
        age = want.get("age") or have["age"]
        if name == have["name"] and age == have["age"]:
            continue
        first = name.split(" ")[0]
        if pool and first not in pool.get("characters", []):
            raise ValueError("%s: '%s' is not in %s's name list - the game crashes on names it has no string for"
                             % (role, first, plan.new))
        rest = name[len(first):].strip()
        if rest and pool and rest not in pool.get("surnames", []):
            raise ValueError("%s: surname '%s' is not in %s's surname list" % (role, rest, plan.new))
        line = f.text(c.start)
        if name != have["name"]:
            from .family import rename_in_tree
            rename_in_tree(f, plan.new, have["name"], name)     # the tree names him too
        line = line.replace(have["name"], name, 1)
        if age:
            line = re.sub(r"\bage\s+\d+", "age %d" % int(age), line, count=1)
        f.set(c.start, line)
        plan.note(f, "%s: %s, age %s" % (role, name, age))


def _capital(plan, f, capital):
    """The capital is the faction's first settlement block: move it to the front."""
    fb = Strat(f).faction(plan.new)
    sts = fb.settlements
    st = next((x for x in sts if x.region == capital), None)
    if st is None:
        raise ValueError("%s is not a town of %s" % (capital, plan.new))
    if st is sts[0]:
        return
    block = f.raw[st.start:st.end]
    del f.raw[st.start:st.end]
    f.raw[sts[0].start:sts[0].start] = block
    plan.note(f, "capital: %s (now the first settlement of %s)" % (capital, plan.new))


def _move_list(plan, f, fac, playable):
    s = Strat(f)
    src, dst = (s.nonplayable, s.playable) if playable else (s.playable, s.nonplayable)
    if dst is None:
        raise ValueError("descr_strat.txt has no %s list" % ("playable" if playable else "nonplayable"))
    if src:
        for i, n in src["items"]:
            if n == fac:
                del f.raw[i]
                break
    s = Strat(f)
    dst = s.playable if playable else s.nonplayable
    items = dst["items"]
    at = next((j for j, n in items if n == "slave"), None)
    at = at if at is not None else (items[-1][0] + 1 if items else dst["start"] + 1)
    indent = re.match(r"\s*", f.text(items[0][0])).group(0) if items else "\t"
    f.insert(at, [indent + fac])
    plan.note(f, "%s moved to the %s list" % (fac, "playable" if playable else "nonplayable"))


def plan_tiles(plan, campaign):
    """{region: town tile} as the plan leaves the map: towns moved (opts places) and the towns
    of new regions (opts regions/new) on top of map_regions.tga as it is."""
    tiles = dict(plan.mod.city_tiles(campaign))
    tiles.update({p["region"]: tuple(p["to"]) for p in plan.opts.get("places") or [] if p["what"] == "city"})
    tiles.update({r["name"]: tuple(r["city"]) for r in (plan.opts.get("regions") or {}).get("new") or []
                  if r.get("city")})
    return tiles


def _garrisons(plan, f, s, campaign, faction=None, picked=None, add=False):
    """Each picked garrison replaces the units of the army that holds the town
    (a named character keeps his bodyguard); a town nobody holds gets a captain.
    faction / picked: another owner's towns (Buildings and garrisons for many towns); add: the units join
    the army that holds the town (up to its 20) instead of replacing it."""
    faction = faction or plan.new
    picked = plan.opts.get("garrisons") if picked is None else picked
    if not picked:
        return
    fb = s.faction(faction)
    tiles = plan_tiles(plan, campaign)
    rebels = faction == "slave"                # a rebel captain: a sub_faction and a name from its list
    pool = plan.name_pool(faction) or {}
    if not rebels and not first_names(pool, "general"):
        from .clone import give_names            # a faction brought without name lists: a kin's copy (a report)
        if give_names(plan, faction):
            pool = plan.name_pool(faction) or {}
    used = {c.name.split()[0] for x in s.factions for c in x.characters if c.name}
    # the faction's family records too (egypt's Heruben is a character_record: a captain Heruben is skipped
    # by the game as a duplicate), and the names of characters this edit adds (a new army named Heruben: no captain Heruben too)
    from .strat import faction_names
    used |= {n.split()[0] for n in faction_names(s, faction) if n}
    used |= {(c.get("name") or "").split()[0] for c in plan.opts.get("characters") or [] if c.get("name")}
    men = first_names(pool, "general")
    captains = [n for n in men if n not in used] or men
    jobs = []
    for region, types in picked.items():
        if region not in [st.region for st in fb.settlements]:
            raise ValueError("%s is not a town of %s" % (region, faction))
        xy = tiles.get(region)
        holder = next((c for c in fb.characters if c.xy == xy and _has_army(s.lines[c.start:c.end])), None)
        if add and holder is not None:
            room = MAX_UNITS - len(_units(s.lines[holder.start:holder.end]))
        else:
            room = MAX_UNITS - (1 if holder is not None and holder.named else 0)
        if len(types) > room:
            plan.warn(f, "%s: only %d of the %d unit(s) fit - an army holds %d at most" % (
                region, max(room, 0), len(types), MAX_UNITS))
        lines = ["unit\t\t%s\t\t\t\texp 0 armour 0 weapon_lvl 0" % t for t in types][:room]
        jobs.append((region, holder, lines, xy))
    for region, holder, lines, xy in sorted(jobs, key=lambda j: -(j[1].start if j[1] else fb.end)):
        if not lines:                                   # emptied by hand
            if holder is None or add:
                continue
            if not holder.named:                        # a captain with nothing to lead goes
                del f.raw[holder.start:holder.end]
                plan.note(f, "%s: captain %s and his garrison leave - the town is empty" % (region, holder.name))
                continue
        if holder is not None:
            chunk = f.texts()[holder.start:holder.end]
            units = [i for i, l in enumerate(chunk) if tokens(l)[:1] == ["unit"]]
            keep = units if add else units[:1] if holder.named else []
            first = units[0] if units else next(i for i, l in enumerate(chunk) if tokens(l)[:1] == ["army"]) + 1
            new = [l for i, l in enumerate(chunk) if i not in units or i in keep]
            at = first + len(keep)
            new[at:at] = lines
            f.raw[holder.start:holder.end] = [f.make(l) for l in new]
            if add:
                plan.note(f, "%s: %d unit(s) join %s's army (%d now)" % (region, len(lines), holder.name,
                                                                         len(keep) + len(lines)))
            else:
                plan.note(f, "%s: %s holds the town with %d unit(s)%s" % (
                    region, holder.name, len(lines), " + his bodyguard" if keep else ""))
        else:
            sub = None
            if rebels:
                from .strat import rebel_look
                sub = rebel_look(s, xy, plan.mod, campaign)
                men = first_names(plan.name_pool(sub) or {}, "general")
                picks = [n for n in men if n not in used]
                if not picks:
                    raise ValueError("%s: no free name in %s's name list for a rebel captain" % (region, sub))
                name = picks[0]
                used.add(name)
            else:
                if not captains:
                    raise ValueError("%s: no name in %s's name list for a captain" % (region, faction))
                name = captains.pop(0)
            block = [character_line(f, name, "general", 30, xy, sub_faction=sub), "army"] + lines + [""]
            f.insert(_chars_at(f, fb), block)
            plan.note(f, "%s: captain %s holds the town with %d unit(s)" % (region, name, len(lines)))


def _buildings(plan, f, s):
    from .buildings import available, castle_fits, ranks_ok, read_buildings, set_buildings, sized, with_kind
    picked = dict(plan.opts.get("buildings") or {})
    sizes = plan.opts.get("sizes") or {}
    kinds = plan.opts.get("kinds") or {}
    if not picked and not sizes and not kinds:
        return
    fb = s.faction(plan.new)
    known = {b.name: b for b in read_buildings(plan.mod.load(plan.mod.file("edb")))} if plan.mod.file("edb") else {}
    culture = plan.mod.culture(plan.new)
    by_region = {st.region: st for st in fb.settlements}
    for region in sorted(set(picked) | set(sizes) | set(kinds), key=lambda r: -by_region[r].start if r in by_region
                         else 0):
        st = by_region.get(region)
        if st is None:
            raise ValueError("%s is not a town of %s" % (region, plan.new))
        if region in kinds:                   # Medieval II: a city or a castle (the header, buildings converted)
            given = [tuple(x) for x in picked[region]] if region in picked else None
            raw, got = with_kind(plan, f, region, f.raw[st.start:st.end], kinds[region], given, known,
                                 sizes.get(region))
            f.raw[st.start:st.end] = raw
            if got is not given:
                picked[region] = got
        items = [tuple(x) for x in picked.get(region, [])]
        raw, level = sized(plan, f, region, f.raw[st.start:st.end], items, sizes.get(region), known)
        f.raw[st.start:st.end] = raw
        castle_fits(plan, region, raw, level, known)
        if region not in picked:
            continue
        for chain, lv_name in items:
            b = known.get(chain)
            lv = b.level(lv_name) if b else None
            if known and not lv:
                raise ValueError("%s: %s %s is not in export_descr_buildings.txt" % (region, chain, lv_name))
            given = (plan.opts.get("roster") or {}).get("building:%s:%s" % (chain, lv_name))
            if lv and not (given if given is not None else available(lv, plan.new, culture)):
                plan.warn(f, "%s: %s is not in %s's faction list (%s)" % (region, lv_name, plan.new, lv.requires))
            if lv and not chain.lower().startswith("core") and not ranks_ok(lv, level):
                plan.warn(f, "%s: %s needs a %s, the settlement is a %s" % (region, lv_name, lv.settlement_min, level))
        f.raw[st.start:st.end] = set_buildings(f.raw[st.start:st.end], items, f.make)
        plan.note(f, "%s: %d building(s) set" % (region, len(items)))


__all__ = ["read_faction", "edit", "unit_name"]
