"""Delete a town together with its region, everywhere the files tie them ('pull one knot, the whole web follows').

Both games (Rome with REX or without, Medieval II with M2EX or without). Audited 2026-10-04 on both games' own files
(every file that names a region or its town):

- map_regions.tga: the region's land, its town pixel and its port pixel become the land of the neighbour region it
  shares the longest border with (or the one picked); the sea stays sea. An island with no land neighbour is refused.
- descr_regions.txt: the region's block goes (the campaign's own, else world/maps/base's).
- descr_strat.txt: its settlement block goes; the owner's next town is its capital then (the capital is the first
  settlement). The rebels standing on the town's tile (its garrison) go with it; a faction's characters there stay,
  in the field.
- descr_mercenaries.txt: the region leaves every pool's regions line; a pool left without a region goes.
- descr_win_conditions.txt: the region leaves every hold_regions line (the keyword stays, as vanilla Medieval II's
  'short_campaign hold_regions' with none).
- Medieval II's descr_sounds_music_types.txt: the region leaves every regions line (a line left empty goes).
- Barbarian Invasion's descr_harvests.txt (bad harvests: 'year N' + 'region R' [+ 'faction F']): an entry naming the
  region goes whole (without its region a faction's entry would turn into an empire-wide bad harvest). Left in, BI
  with REX logged 'cannot find this region name' (a tester's run).
- map.rwm is removed (the game builds it again).
- Kept: descr_regions_and_settlement_name_lookup.txt and the names texts - an unused name harms nothing (vanilla
  Medieval II's norman_prologue lookup lists every region of the big map).
- Every campaign that shares the map (no descr_regions.txt of its own) gets the same descr_strat / mercenaries /
  win conditions treatment.

Refused, in plain words: the last town of a faction that is alive (it would die as the campaign loads and the game
crash - a tester's Rome with REX), a faction rising there by an event, a campaign script that names the town or the
region (the script would stop). Trait / ancillary conditions and REX / M2EX scripts that name it are listed as
warnings: they simply never fire there again.

Many at once (the map's Select, report R-20261008-7696AA): refusals() reads the files once for all of them (the
last towns of a faction counted together), receivers() gives each region the neighbour that stays (one ringed by
regions deleted with it follows them), delete_many() writes them in one plan - one backup, one Undo. Every file is
read and changed once for all of them (report #154: 48 towns of HLR took 14 s, descr_strat read again per town).

A WASTELAND instead (REX / M2EX - report #154, the user: 'deleting must not give its land to anyone'; REX's
modding/wasteland_regions.md): the region stays, its land nobody's - no town, owner, rebels or economy, the AI never
goes for it, no victory counts it, nobody grows. descr_regions: the settlement line says `wasteland` (the other lines
stay, read but ignored by the engines); map_regions: only the town and port pixels take the region's colour; its
settlement, the rebels on its tile, its mercenary pools and hold_regions go as above; the music lists and bad harvests
keep it (the region is still there). No neighbour is needed - an island can go too. The original exes know no
wasteland (can_waste)."""

import os
import re

from .strat import Strat
from .textio import strip_comment

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _word(name):
    return re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(name))


def _words(names):
    """One pattern for all the names (whole words): a file is searched once, not once per name (48 towns of HLR = 96
    names over 83 files took 5 s)."""
    alts = "|".join(re.escape(n) for n in sorted(set(names), key=lambda n: (-len(n), n)))
    return re.compile(r"(?<![A-Za-z0-9_])(?:%s)(?![A-Za-z0-9_])" % alts)


def _shown(mod, path):
    """A file's name in the report as it will be written: a game file under a thin mod is written as the mod's copy."""
    return mod.rel(mod.own(path) if hasattr(mod, "own") else path)


def can_waste(mod):
    """Whether the game that runs this mod reads a wasteland region: REX (Rome) and M2EX (Medieval II) do, the
    original exes do not."""
    from .limits import engine_of
    return bool(engine_of(mod))


def sharing(mod, campaign):
    """The campaigns that use this campaign's map and descr_regions.txt (itself first): those without a
    descr_regions.txt of their own when it uses world/maps/base's."""
    mine = os.path.normcase(os.path.abspath(mod.campaign_file(campaign, "descr_regions.txt") or ""))
    out = [campaign]
    for c in mod.campaigns():
        if c != campaign and os.path.normcase(os.path.abspath(mod.campaign_file(c, "descr_regions.txt") or "")) == mine:
            out.append(c)
    return out


def region_pixels(mod, campaign, region):
    """[(x, y)] of the region's land on map_regions.tga, its town pixel and its port pixel among them."""
    from .mapedit import ports
    img = mod.region_map(campaign)
    colour = mod.regions(campaign)[region]["colour"]
    out = list(img.find(colour))
    town = mod.city_tiles(campaign).get(region)
    if town:
        out.append(tuple(town))
    port = ports(mod, campaign).get(region)
    if port:
        out.append(tuple(port))
    return out


def neighbours(mod, campaign, region):
    """[(neighbour region, border length in tiles)], the longest border first: the land regions that touch the
    region's land side by side."""
    img = mod.region_map(campaign)
    by_colour = mod.region_colours(campaign)
    own = set(region_pixels(mod, campaign, region))
    count = {}
    for x, y in own:
        for dx, dy in N4:
            nx, ny = x + dx, y + dy
            if (nx, ny) in own or not (0 <= nx < img.width and 0 <= ny < img.height):
                continue
            r = by_colour.get(img.get(nx, ny))
            if r and r != region:
                count[r] = count.get(r, 0) + 1
    return sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))


def _script_files(mod, campaign):
    """The campaign's own script files (campaign_script.txt, a prologue's ..._Script.txt): the game reads them as
    the campaign loads."""
    out, seen = [], set()
    for d in mod.campaign_dirs(campaign) if hasattr(mod, "campaign_dirs") else [mod.campaign_dir(campaign)]:
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            if n.lower().endswith(".txt") and "script" in n.lower() and n.lower() not in seen:
                seen.add(n.lower())              # the mod's own copy wins over the game's
                out.append(os.path.join(d, n))
    return out


def _hits(path, names):
    """[(line number, line)] of a text file whose code (comments left out) names one of names as a whole word."""
    from .regionrename import FACTION_BEFORE, PERSON_BEFORE, _split
    from .scan import _read_text
    text = _read_text(path)
    if text is None or not names or not any(n in text for n in names):
        return []
    out = []
    rx = _words(names)
    for i, line in enumerate(text.splitlines()):
        if not rx.search(line):
            continue
        code, _ = _split(path, line)
        if any(not FACTION_BEFORE.search(code[:m.start()]) and not PERSON_BEFORE.search(code[:m.start()])
               for m in rx.finditer(code)):
            out.append((i + 1, line.strip()))
    return out


def problems(mod, campaign, region, into=None, land=True, waste=False):
    """([refusals], [warnings]) in plain words. land=False: the region's land goes off the map with it (a cut of the
    map's edge) - no neighbour needed for it; waste: it stays as a wasteland - no neighbour needed either."""
    regions = mod.regions(campaign)
    if region not in regions:
        return ["%s is no region of this campaign" % region], []
    if waste:
        return refusals(mod, campaign, [region], waste=True)
    errors = []
    near = neighbours(mod, campaign, region) if land else [(into, 1)] if into else []
    if land and not near:
        errors.append("%s touches no other region's land (an island) - its land would belong to no region; give it to "
                      "a neighbour on the Map with Edit regions instead" % region)
    elif into and into not in dict(near):
        errors.append("%s does not touch %s - its land can go only to a neighbour (%s)" % (
            into, region, ", ".join(r for r, _ in near[:6])))
    more, warns = refusals(mod, campaign, [region])
    return errors + more, warns


def refusals(mod, campaign, gone, last_town=True, waste=False):
    """([refusals], [warnings]) for the regions `gone` deleted together, every file read once for all of them (a big
    mod has tens of thousands): a faction left without a town (unless last_town is False - the caller says it its own
    way), a faction rising in one by an event, a campaign script naming one (refused); other files naming one -
    trait / ancillary conditions, REX / M2EX scripts (warned: they never fire there again). waste: the regions stay
    (as wastelands) - only their towns' names are gone, so only those are looked for."""
    regions = mod.regions(campaign)
    gone = [r for r in gone if r in regions]
    town = {r: regions[r].get("settlement") or "" for r in gone}
    names = [n for r in gone for n in ((town[r],) if waste else (r, town[r])) if n]
    errors, warns = [], []

    def named(got):
        """The names a file's lines name (all of one region's when only one goes - the old words)."""
        if len(gone) == 1:
            return names
        return [n for n in names if any(_word(n).search(line) for _, line in got)] or names
    from .emergence import emergent_events
    for c in sharing(mod, campaign):
        p = mod.campaign_file(c, "descr_strat.txt")
        owners = Strat(mod.load(p)).owners() if p else {}
        for fac in sorted({owners.get(r) for r in gone} - {None, "slave"}) if last_town else ():
            if [r for r, o in owners.items() if o == fac and r not in gone]:
                continue
            mine = [town[r] or r for r in gone if owners.get(r) == fac]
            errors.append("%s %s the last town%s of %s%s - a faction without a town dies as the campaign loads and "
                          "the game crashes; give %s another town first" % (
                              ", ".join(mine), "is" if len(mine) == 1 else "are", "" if len(mine) == 1 else "s",
                              fac, "" if c == campaign else " in %s" % c, fac))
        for fac, e in emergent_events(mod, c).items():
            if e.get("region") in gone:
                errors.append("%s rises in %s by an event (descr_events.txt%s) - pick another region for it first "
                              "(Events and later factions)" % (fac, e["region"], "" if c == campaign else " of %s" % c))
        for path in _script_files(mod, c):
            got = _hits(path, names)
            if got:
                errors.append("%s names %s on line%s %s (%s) - the script would stop; change those lines first" % (
                    mod.rel(path), " / ".join(named(got)), "s" if len(got) > 1 else "",
                    ", ".join(str(n) for n, _ in got[:8]) + (" ..." if len(got) > 8 else ""), got[0][1][:60]))
    for path, got in _other_mentions(mod, campaign, names):
        warns.append("%s names %s on line%s %s - it never fires there again" % (
            mod.rel(path), " / ".join(named(got)), "s" if len(got) > 1 else "",
            ", ".join(str(n) for n, _ in got[:6]) + (" ..." if len(got) > 6 else "")))
    return errors, warns


def receivers(near, gone, chosen=None):
    """Where the land of each region in `gone` goes when they are deleted together -> ({region: the region that
    stays and takes its land}, [regions with nowhere to go]). near = {region: neighbours(...)} of every region in
    gone. A region keeps the neighbour picked for it (chosen) when that one stays and touches it; else it goes to the
    neighbour that stays it shares the longest border with. A neighbour deleted with it counts with the region its
    own land goes to, so a region ringed only by regions deleted with it follows them (step by step, outside in)."""
    gone, chosen = list(gone), chosen or {}
    into, left = {}, sorted(gone)
    while left:
        known = dict(into)                    # each round reads the rounds before it only: the order never matters
        for r in list(left):
            pick = chosen.get(r)
            if pick and pick not in gone and pick in dict(near.get(r, ())):
                into[r] = pick
            else:
                count = {}
                for n, k in near.get(r, ()):
                    t = known.get(n) if n in gone else n
                    if t:
                        count[t] = count.get(t, 0) + k
                if not count:
                    continue
                into[r] = min(count, key=lambda t: (-count[t], t))
            left.remove(r)
        if len(into) == len(known):
            break
    return into, left


HANDLED = re.compile(r"(^|/)(descr_regions|descr_strat|descr_mercenaries|descr_win_conditions|descr_sounds_music_types|"
                     r"descr_regions_and_settlement_name_lookup|descr_events|descr_harvests)\.txt$|(^|/)text/", re.I)


def _other_mentions(mod, campaign, names):
    """[(path, [(line, text)])] of the files that name the place outside what delete() follows and the campaign
    scripts (problems refuses those): trait / ancillary conditions, REX / M2EX scripts, ..."""
    from .regionrename import _files
    scripts = {os.path.normcase(os.path.abspath(p)) for c in sharing(mod, campaign) for p in _script_files(mod, c)}
    out = []
    for path in _files(mod, campaign):
        rel = os.path.relpath(path, mod.data).replace("\\", "/")
        if HANDLED.search(rel) or os.path.normcase(os.path.abspath(path)) in scripts:
            continue
        got = _hits(path, names)
        if got:
            out.append((path, got))
    return out


def _drop_word(plan, f, key, region, why):
    """The region taken out of every '<key> A B C' line of f (its indent, the gap after the key and a comment
    kept). -> [line indexes left with no name]."""
    empty = []
    for i in range(len(f.raw)):
        line = f.text(i)
        code = strip_comment(line)
        words = code.split()
        if not words or words[0] != key or region not in words[1:]:
            continue
        cut = line.find(";") if ";" in line else len(line)
        body, tail = line[:cut].rstrip(), line[len(line[:cut].rstrip()):]       # tail: the gap and the comment
        m = re.match(r"(\s*%s)(\s*)(.*)$" % re.escape(key), body)
        left = [w for w in m.group(3).split() if w != region]
        f.set(i, m.group(1) + ((m.group(2) or " ") + " ".join(left) if left else "") + tail)
        if not left:
            empty.append(i)
        plan.note(f, "%s out of a %s line%s" % (region, key, why))
    return empty


def _drop_block(f, start):
    """Lines start .. before the next line that starts at column 0 with code (a descr_regions block, a pool)."""
    end = start + 1
    while end < len(f.raw):
        code = strip_comment(f.text(end))
        if code.strip() and not code[0].isspace():
            break
        end += 1
    while end > start + 1 and not f.text(end - 1).strip():       # the blank lines before the next block stay
        end -= 1
    del f.raw[start:end]


def delete(plan, campaign, region, into=None, land=True, checked=False, waste=False):
    """Write the deletion into the plan (see the module text). Returns the region the land went to. land=False (a cut
    of the map's edge takes all its land off the map): its pixels are left for the cut, given to no one (None).
    waste: the region stays as a wasteland, its land nobody's (None). checked: the caller has asked problems /
    refusals already (and says their warnings) - the files are not read again (a big mod's thousands of them)."""
    mod = plan.mod
    errors, warns = ([], []) if checked else problems(mod, campaign, region, into, land, waste)
    if errors:
        raise ValueError("; ".join(errors))
    if waste:
        into = None
    elif land:
        into = into or neighbours(mod, campaign, region)[0][0]
    else:
        into = None
    _delete(plan, campaign, {region: (into, land)}, {region} if waste else ())
    for w in warns:
        plan.warn(None, w)
    return into


def delete_many(plan, campaign, into, warns=(), waste=False):
    """Many towns deleted with their regions in one plan (one backup, one Undo): into = {region: the region that
    stays and takes its land} as receivers() gives it - or, waste, the regions that stay as wastelands (a list, or a
    dict whose values are not read). Refusals asked already - their warnings in warns."""
    gone = sorted(into)
    _delete(plan, campaign, {r: (None if waste else into[r], True) for r in gone}, gone if waste else ())
    for w in warns:
        plan.warn(None, w)


def _delete(plan, campaign, gone, waste=()):
    """The deletion of every region in gone = {region: (the region that takes its land or None, land)} written into
    the plan, each file read and changed once for all of them; the regions in waste stay as wastelands."""
    from .mapedit import ports
    from .moddata import region_entries
    mod = plan.mod
    waste = set(waste)
    regions = mod.regions(campaign)
    tiles = mod.city_tiles(campaign)
    harbour = ports(mod, campaign)
    path = mod.campaign_file(campaign, "map_regions.tga")
    paint = {}
    for region in sorted(gone):
        into, land = gone[region]
        if region in waste:
            # the town and port pixels take the region's own colour: no town, its land stays its own
            px = [tuple(p) for p in (tiles.get(region), harbour.get(region)) if p]
            paint.update({xy: regions[region]["colour"] for xy in px})
            plan.notes.append((_shown(mod, path), "%s stays as a wasteland - its town%s pixel%s painted with its own "
                               "colour, its %d tile(s) of land nobody's" % (
                                   region, " and port" if region in harbour else "", "s" if region in harbour else "",
                                   sum(1 for _ in mod.region_map(campaign).find(regions[region]["colour"])))))
        elif land:
            # the map: the land, the town and the port go to the neighbour
            px = region_pixels(mod, campaign, region)
            paint.update({xy: regions[into]["colour"] for xy in px})
            plan.notes.append((_shown(mod, path), "%d tile(s) of %s, its town and port pixels with them -> %s" % (
                len(px), region, into)))
        else:
            plan.notes.append((_shown(mod, path), "%s: all its land goes off the map with the cut" % region))
    if paint:
        plan.patch_tga(path, paint)
    for folder in {os.path.dirname(path), os.path.join(mod.data, "world", "maps", "base")}:
        plan.delete(os.path.join(folder, "map.rwm"), "the game rebuilds it from the changed map on the next start")
    # descr_regions.txt: a wasteland's settlement line says so (no line moves); then the other blocks go, bottom up
    dr = plan.edit(mod.campaign_file(campaign, "descr_regions.txt"))
    entries = region_entries(dr)
    for region in sorted(waste):
        if "settlement" not in entries.get(region, {}):
            continue                                # a wasteland already: nothing to change in its block
        at, town = entries[region]["settlement"]
        line = dr.text(at)
        dr.set(at, line[:len(line) - len(line.lstrip())] + "wasteland" + line[line.index(town) + len(town):])
        plan.note(dr, "region %s: wasteland (its town %s gone; no owner, no rebels, no economy - REX / M2EX)" % (
            region, town))
    starts = {}
    for i in range(len(dr.raw)):
        if not dr.text(i)[:1].isspace():
            name = strip_comment(dr.text(i)).strip()
            if name in gone and name not in waste and name not in starts:
                starts[name] = i
    for region, at in sorted(starts.items(), key=lambda kv: -kv[1]):
        _drop_block(dr, at)
        plan.note(dr, "region %s (%s) out" % (region, regions[region].get("settlement") or "no town"))
    music = _ci_file(mod.base, "descr_sounds_music_types.txt")
    out = [r for r in sorted(gone) if r not in waste]           # regions that leave every file
    done = set()
    for c in sharing(mod, campaign):
        tag = "" if c == campaign else " (%s)" % c
        sp = mod.campaign_file(c, "descr_strat.txt")
        if sp and sp not in done:
            done.add(sp)
            _strat(plan, sp, sorted(gone), tiles, tag, {r: (None if r in waste else gone[r][0]) for r in gone})
        hp = mod.campaign_file(c, "descr_harvests.txt")
        if hp and hp not in done and out:
            done.add(hp)
            for region in out:
                _harvests(plan, hp, region, tag)
        for name, key in (("descr_mercenaries.txt", "regions"), ("descr_win_conditions.txt", "hold_regions")):
            p = mod.campaign_file(c, name)
            if not p or p in done:
                continue
            done.add(p)
            f = plan.edit(p)
            for region in sorted(gone):
                empty = _drop_word(plan, f, key, region, tag)
                if name == "descr_mercenaries.txt":
                    for i in sorted(empty, reverse=True):        # a pool left without a region goes
                        start = next((k for k in range(i, -1, -1)
                                      if strip_comment(f.text(k)).split()[:1] == ["pool"]), None)
                        if start is not None:
                            pool = strip_comment(f.text(start)).split()[1:2]
                            _drop_block(f, start)
                            plan.note(f, "pool %s had no region left - it goes" % (pool[0] if pool else "?"))
    if music and out:
        f = plan.edit(music)
        for region in out:
            for i in sorted(_drop_word(plan, f, "regions", region, ""), reverse=True):
                del f.raw[i]


def _harvests(plan, path, region, tag):
    """descr_harvests.txt: every entry ('year N' and the lines after it up to the next 'year') naming the region
    goes whole."""
    f = plan.edit(path)
    starts = [i for i in range(len(f.raw)) if strip_comment(f.text(i)).split()[:1] == ["year"]]
    gone = 0
    for k in reversed(range(len(starts))):
        a = starts[k]
        b = starts[k + 1] if k + 1 < len(starts) else len(f.raw)
        if any(strip_comment(f.text(i)).split()[:2] == ["region", region] for i in range(a, b)):
            del f.raw[a:b]
            gone += 1
    if gone:
        plan.note(f, "%d bad-harvest entr%s of %s out%s" % (gone, "y" if gone == 1 else "ies", region, tag))


def _ci_file(folder, name):
    from .moddata import _ci
    return _ci(folder, name) if os.path.isdir(folder) else None


BLOCK_WORDS = ("road_level", "farming_level", "famine_threat", "fort", "watchtower")


def _region_blocks(f, start):
    """{region: (its `region R` line, the end)} of descr_strat's regions section (after the diplomacy): an unindented
    `region R` and its road / farming / famine lines, forts and watchtowers (Barbarian Invasion's 16 blocks, a mod's
    forts); the comments and blank lines before the next block are not its."""
    out, cur = {}, None
    if start is None:
        return out

    def close(end):
        while end > cur[1] + 1 and not strip_comment(f.text(end - 1)).strip():
            end -= 1
        out.setdefault(cur[0], (cur[1], end))
    for i in range(start, len(f.raw)):
        code = strip_comment(f.text(i))
        t = code.split()
        if not t:
            continue
        if t[0] == "region" and len(t) > 1 and code[:1] not in (" ", "\t"):
            if cur:
                close(i)
            cur = (t[1], i)
        elif cur and t[0] not in BLOCK_WORDS and code[:1] not in (" ", "\t"):
            close(i)
            cur = None
    if cur:
        close(len(f.raw))
    return out


def _strat(plan, path, gone, tiles, tag, into=None):
    """descr_strat.txt: the settlement blocks of the regions in gone out, the rebels standing on their towns' tiles
    with them - the file read once for all of them. Their blocks of the regions section (roads, forts, watchtowers):
    into = {region: the region that takes its land, or None}: its forts / watchtowers move to that region's block (its
    own block renamed when that one has none); with no region taking its land (a wasteland, a cut) the block goes -
    the game takes forts and watchtowers only in a region with a town ('You are trying to place a fort or watchtower
    in this region, but it doesn't have a settlement')."""
    f = plan.edit(path)
    s = Strat(f)
    into = into or {}
    cuts, losers = [], []
    at = {tuple(tiles[r]): r for r in gone if tiles.get(r)}
    for region in gone:
        st = s.settlement_of(region)
        if st:
            cuts.append((st.start, st.end, "settlement of %s" % region))
            if st.owner != "slave" and st.owner not in losers:
                losers.append(st.owner)
    for fb in s.factions:
        if fb.name != "slave":
            continue
        for ch in fb.characters:
            if ch.xy and tuple(ch.xy) in at:
                cuts.append((ch.start, ch.end, "rebel %s on its tile" % ch.name))
    blocks = _region_blocks(f, s.diplomacy_start)
    adds = []
    for region in gone:
        if region not in blocks:
            continue
        a, b = blocks[region]
        to = into.get(region)
        lines = [f.text(i) for i in range(a + 1, b) if strip_comment(f.text(i)).split()[:1] in (["fort"], ["watchtower"])]
        if to and lines and to in blocks and to not in gone:
            adds.append((blocks[to][1], lines, to))
            cuts.append((a, b, "its block of the regions section (%d fort / watchtower line(s) to %s's)" % (
                len(lines), to)))
        elif to and lines:
            line = f.text(a)
            f.set(a, line.replace(region, to, 1))
            plan.note(f, "the regions section's block of %s is %s's now (its forts / watchtowers go with the land)%s"
                      % (region, to, tag))
        else:
            cuts.append((a, b, "the regions section's block of %s%s" % (
                region, " with its %d fort / watchtower line(s) - the game takes them only in a region with a town"
                % len(lines) if lines else "")))
    ops = [(a, 1, (b, what)) for a, b, what in cuts] + [(i, 0, (lines, to)) for i, lines, to in adds]
    for i, kind, x in sorted(ops, key=lambda o: (-o[0], -o[1])):
        if kind:
            del f.raw[i:x[0]]
            plan.note(f, "%s out%s" % (x[1], tag))
        else:
            f.raw[i:i] = [f.make(t) for t in x[0]]
            plan.note(f, "%d fort / watchtower line(s) into %s's block of the regions section%s" % (len(x[0]), x[1], tag))
    if losers:
        owners = Strat(f).owners()
        for fac in losers:
            left = [r for r, o in owners.items() if o == fac]
            if left:
                plan.note(f, "%s keeps %d town(s); its first, %s, is its capital" % (fac, len(left), left[0]))
            else:                                   # only when it leaves the campaign (a cut, the modder's yes)
                plan.note(f, "%s keeps no town" % fac)


def town_problem(mod, campaign, region, xy, name=None):
    """None, or why a wasteland region may not get its town on tile xy (named name)."""
    from .mapedit import CITY, PORT
    regions = mod.regions(campaign)
    info = regions.get(region)
    if not info:
        return "%s is not a region of this map" % region
    if not info.get("wasteland"):
        return "%s is no wasteland - it has its town" % region
    img = mod.region_map(campaign)
    x, y = xy
    if not (1 <= x < img.width - 1 and 1 <= y < img.height - 1):
        return "too near the map's edge"
    if img.get(x, y) in (CITY, PORT):
        return "another town or port stands there"
    if any(img.get(x + dx, y + dy) != info["colour"] for dx, dy in N4 + ((0, 0),)):
        return "pick a tile inside %s's land (its land all round it)" % region
    why = mod.land_problem(campaign, (x, y))
    if why:
        return why
    if name is not None:
        if not re.match(r"^[A-Za-z0-9_\-]+$", name or ""):
            return "the town's name in the files may use letters, digits, _ and - (no spaces)"
        if name == region:
            return "the town needs a name other than its region's"
        taken = {v.get("settlement") for v in regions.values()} | set(regions)
        if name in taken:
            return "%s is a region or town of this map already" % name
    return None


def wasteland_town(plan, campaign, region, xy, name, owner="slave", label=None):
    """The opposite of a wasteland (delete(..., waste=True)): the region gets its town again on tile xy - its
    descr_regions settlement line names the town (a short 3-line wasteland entry gets the whole block, its creator,
    rebels, resources and farming as the neighbour it shares the longest border with), the town pixel on the map, a
    village of owner in descr_strat (400 people, no buildings, as the game makes it), the town's name in the names
    text and the lookup when they lack it. map.rwm is removed (the game builds it again)."""
    from .mapedit import CITY
    from .moddata import region_entries, religions_line
    from .regionedit import religions_for
    from .strat import village_block
    mod = plan.mod
    why = town_problem(mod, campaign, region, xy, name)
    if why:
        raise ValueError("%s cannot get its town at %d, %d: %s" % (region, xy[0], xy[1], why))
    regions = mod.regions(campaign)
    donor = next((r for r, _ in neighbours(mod, campaign, region) if not regions[r].get("wasteland")), None)
    d = regions.get(donor) or {}
    dr = plan.edit(mod.campaign_file(campaign, "descr_regions.txt"))
    e = region_entries(dr)[region]
    at, _ = e["wasteland"]
    creator = owner if owner != "slave" else (d.get("creator") or owner)
    if e.get("colour") and e["colour"][0] - at > 1:                 # the long form: only the town's line changes
        line = dr.text(at)
        dr.set(at, line.replace("wasteland", name, 1))
        plan.note(dr, "region %s: its town %s again (no wasteland)" % (region, name))
    else:                                                           # the short form: the whole block
        lines = ["\t" + name, "\t" + creator, "\t" + (d.get("rebels") or "Rebels")]
        after = ["\t" + (d.get("resources") or "none"), "\t" + (d.get("triumph") or "5"),
                 "\t" + (d.get("farming") or "3")]
        if d.get("legion"):
            lines.insert(0, "\t" + d["legion"])
        if d.get("beliefs"):
            after.append("\t" + " ".join("%s %d" % (k, n) for k, n in d["beliefs"].items()))
        if any(v.get("religions") for v in regions.values()):
            after.append("\t" + religions_line(religions_for(regions, None, donor)))
        colour_at = e["colour"][0] if e.get("colour") else at + 1
        dr.raw[colour_at + 1:colour_at + 1] = [dr.make(t) for t in after]
        dr.raw[at:at + 1] = [dr.make(t) for t in lines]
        plan.note(dr, "region %s: its town %s again, the rest as %s (built by %s, rebels %s)" % (
            region, name, donor or "the usual", creator, d.get("rebels") or "Rebels"))
    path = mod.campaign_file(campaign, "map_regions.tga")
    plan.patch_tga(path, {tuple(xy): CITY})
    plan.notes.append((_shown(mod, path), "the town pixel of %s at %d, %d" % (region, xy[0], xy[1])))
    for folder in {os.path.dirname(path), os.path.join(mod.data, "world", "maps", "base")}:
        plan.delete(os.path.join(folder, "map.rwm"), "the game rebuilds it from the changed map on the next start")
    sf = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
    fb = Strat(sf).faction(owner)
    if fb is None:
        raise ValueError("descr_strat.txt has no block for %s" % owner)
    block = village_block(region, creator)
    at = fb.settlements[-1].end if fb.settlements else \
        next((i + 1 for i in range(fb.start, fb.end) if sf.text(i).split()[:1] == ["denari"]), fb.start + 1)
    sf.raw[at:at] = [sf.make(t) for t in block]
    plan.note(sf, "%s: a village of %s" % (region, owner))
    lk = mod.campaign_file(campaign, "descr_regions_and_settlement_name_lookup.txt")
    if lk:
        f = plan.edit(lk)
        if name not in {strip_comment(f.text(i)).strip() for i in range(len(f.raw))}:
            while f.raw and not f.text(len(f.raw) - 1).strip():
                del f.raw[-1]
            f.raw.extend([f.make(name), f.make("")])
            plan.note(f, "%s added" % name)
    labels = mod.region_labels_file(campaign)
    if labels:
        f = plan.edit(labels)
        if not any(f.text(i).lstrip().startswith("{%s}" % name) for i in range(len(f.raw))):
            while f.raw and not f.text(len(f.raw) - 1).strip():
                del f.raw[-1]
            f.raw.extend([f.make("{%s}\t\t\t%s" % (name, label or name.replace("_", " "))), f.make("")])
            plan.note(f, "the name players see for %s: %s" % (name, label or name.replace("_", " ")))
    else:
        plan.warn(None, "no %s_regions_and_settlement_names.txt found - the town's name shows as its key" % campaign)
