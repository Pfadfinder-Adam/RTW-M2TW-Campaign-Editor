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
regions deleted with it follows them), delete_many() writes them in one plan - one backup, one Undo."""

import os
import re

from .strat import Strat
from .textio import strip_comment

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _word(name):
    return re.compile(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(name))


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
    if text is None or not any(n in text for n in names):
        return []
    out = []
    rxs = [_word(n) for n in names]
    for i, line in enumerate(text.splitlines()):
        code, _ = _split(path, line)
        for rx in rxs:
            m = next((m for m in rx.finditer(code) if not FACTION_BEFORE.search(code[:m.start()])
                      and not PERSON_BEFORE.search(code[:m.start()])), None)
            if m:
                out.append((i + 1, line.strip()))
                break
    return out


def problems(mod, campaign, region, into=None, land=True):
    """([refusals], [warnings]) in plain words. land=False: the region's land goes off the map with it (a cut of the
    map's edge) - no neighbour needed for it."""
    regions = mod.regions(campaign)
    if region not in regions:
        return ["%s is no region of this campaign" % region], []
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


def refusals(mod, campaign, gone, last_town=True):
    """([refusals], [warnings]) for the regions `gone` deleted together, every file read once for all of them (a big
    mod has tens of thousands): a faction left without a town (unless last_town is False - the caller says it its own
    way), a faction rising in one by an event, a campaign script naming one (refused); other files naming one -
    trait / ancillary conditions, REX / M2EX scripts (warned: they never fire there again)."""
    regions = mod.regions(campaign)
    gone = [r for r in gone if r in regions]
    town = {r: regions[r].get("settlement") or "" for r in gone}
    names = [n for r in gone for n in (r, town[r]) if n]
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


def delete(plan, campaign, region, into=None, land=True, checked=False):
    """Write the deletion into the plan (see the module text). Returns the region the land went to. land=False (a cut
    of the map's edge takes all its land off the map): its pixels are left for the cut, given to no one (None).
    checked: the caller has asked problems / refusals already (and says their warnings) - the files are not read
    again (a big mod's thousands of them)."""
    mod = plan.mod
    errors, warns = ([], []) if checked else problems(mod, campaign, region, into, land)
    if errors:
        raise ValueError("; ".join(errors))
    regions = mod.regions(campaign)
    town = regions[region].get("settlement") or ""
    path = mod.campaign_file(campaign, "map_regions.tga")
    if land:
        into = into or neighbours(mod, campaign, region)[0][0]
        # the map: the land, the town and the port go to the neighbour
        colour = regions[into]["colour"]
        px = region_pixels(mod, campaign, region)
        plan.patch_tga(path, {xy: colour for xy in px})
        plan.notes.append((mod.rel(path), "%d tile(s) of %s, its town and port pixels with them -> %s" % (
            len(px), region, into)))
    else:
        into = None
        plan.notes.append((mod.rel(path), "%s: all its land goes off the map with the cut" % region))
    for folder in {os.path.dirname(path), os.path.join(mod.data, "world", "maps", "base")}:
        plan.delete(os.path.join(folder, "map.rwm"), "the game rebuilds it from the changed map on the next start")
    # descr_regions.txt
    dr = plan.edit(mod.campaign_file(campaign, "descr_regions.txt"))
    at = next(i for i in range(len(dr.raw)) if strip_comment(dr.text(i)).strip() == region and
              not dr.text(i)[:1].isspace())
    _drop_block(dr, at)
    plan.note(dr, "region %s (%s) out" % (region, town or "no town"))
    tile = mod.city_tiles(campaign).get(region)
    music = _ci_file(mod.base, "descr_sounds_music_types.txt")
    done = set()
    for c in sharing(mod, campaign):
        tag = "" if c == campaign else " (%s)" % c
        sp = mod.campaign_file(c, "descr_strat.txt")
        if sp and sp not in done:
            done.add(sp)
            _strat(plan, sp, region, tile, tag)
        hp = mod.campaign_file(c, "descr_harvests.txt")
        if hp and hp not in done:
            done.add(hp)
            _harvests(plan, hp, region, tag)
        for name, key in (("descr_mercenaries.txt", "regions"), ("descr_win_conditions.txt", "hold_regions")):
            p = mod.campaign_file(c, name)
            if not p or p in done:
                continue
            done.add(p)
            f = plan.edit(p)
            empty = _drop_word(plan, f, key, region, tag)
            if name == "descr_mercenaries.txt":
                for i in sorted(empty, reverse=True):        # a pool left without a region goes
                    start = next((k for k in range(i, -1, -1) if strip_comment(f.text(k)).split()[:1] == ["pool"]),
                                 None)
                    if start is not None:
                        pool = strip_comment(f.text(start)).split()[1:2]
                        _drop_block(f, start)
                        plan.note(f, "pool %s had no region left - it goes" % (pool[0] if pool else "?"))
    if music:
        f = plan.edit(music)
        for i in sorted(_drop_word(plan, f, "regions", region, ""), reverse=True):
            del f.raw[i]
    for w in warns:
        plan.warn(None, w)
    return into


def delete_many(plan, campaign, into, warns=()):
    """Many towns deleted with their regions in one plan (one backup, one Undo): into = {region: the region that
    stays and takes its land} as receivers() gives it (refusals asked already - its warnings in warns)."""
    for region in sorted(into):
        delete(plan, campaign, region, into[region], checked=True)
    for w in warns:
        plan.warn(None, w)


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


def _strat(plan, path, region, tile, tag):
    """descr_strat.txt: the settlement block out; the rebels standing on the town's tile with it."""
    f = plan.edit(path)
    s = Strat(f)
    st = s.settlement_of(region)
    gone = []
    if tile:
        for fb in s.factions:
            if fb.name != "slave":
                continue
            for ch in fb.characters:
                if ch.xy and tuple(ch.xy) == tuple(tile):
                    gone.append(ch)
    cuts = ([(st.start, st.end, "settlement of %s" % region)] if st else []) + \
        [(ch.start, ch.end, "rebel %s on its tile" % ch.name) for ch in gone]
    for a, b, what in sorted(cuts, reverse=True):
        del f.raw[a:b]
        plan.note(f, "%s out%s" % (what, tag))
    if st and st.owner != "slave":
        left = [r for r, o in Strat(f).owners().items() if o == st.owner]
        if left:
            plan.note(f, "%s keeps %d town(s); its first, %s, is its capital" % (st.owner, len(left), left[0]))
        else:                                       # only when it leaves the campaign (a cut, the modder's yes)
            plan.note(f, "%s keeps no town" % st.owner)
