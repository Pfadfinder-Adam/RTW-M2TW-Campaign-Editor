"""Grow or cut the campaign map at its edges (Map size...): rows / columns of tiles added at the left, right, top or
bottom - deep sea, as the map's own deepest water - or cut off. Both games.

Tile (x, y) - counted from the map's bottom left, as descr_strat.txt and map_regions.tga (read bottom-up) count
them - becomes (x + left, y + bottom); the pictures 2W+1 / 2W wide move by twice as many points. Every place the
x3 upscale moves is moved the same way (upscale's shared movers, given this shift instead): characters,
resources, forts / watchtowers / wonders in descr_strat.txt, events' positions, the campaign's scripts (tile
commands; distances, radii and rectangle sizes stay), trait / ancillary conditions when the mod has this one
campaign. descr_terrain.txt gets the new width / height, map_heights.hgt is moved with the picture, map.rwm goes.

A cut that would leave a town, a port, a character, a resource, a fort or an event's place off the map is refused
with the file and line of each (nothing is written)."""

import os
import re
import struct
from collections import deque

from . import upscale as U
from .tga import _decode, read_tga

STEP = {"tiles": 1, "corners": 2, "double": 2}     # how many points a tile is in each kind of picture


def deepest_sea(mod, campaign):
    """(x, y): the sea tile farthest from any land in map_regions (the colour the new edges are filled with comes
    from there in every picture); ValueError when the map has no sea."""
    img = read_tga(mod.campaign_file(campaign, "map_regions.tga"))
    w, h = img.width, img.height
    lands = {v["colour"] for v in mod.regions(campaign).values()} | {U.CITY, U.PORT}
    counts = {}
    for y in range(h):
        for x in range(w):
            c = img.get(x, y)
            if c not in lands:
                counts[c] = counts.get(c, 0) + 1
    if not counts:
        raise ValueError("the map has no sea - the new edge has nothing to be filled with")
    sea = max(counts, key=counts.get)
    dist = [-1] * (w * h)
    todo = deque()
    for y in range(h):
        for x in range(w):
            if img.get(x, y) != sea:
                dist[y * w + x] = 0
                todo.append((x, y))
    if not todo:                                    # all sea: the middle
        return w // 2, h // 2
    while todo:
        x, y = todo.popleft()
        d = dist[y * w + x] + 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and dist[ny * w + nx] < 0:
                dist[ny * w + nx] = d
                todo.append((nx, ny))
    i = max(range(w * h), key=lambda k: dist[k])
    return i % w, i // w


def shifted(data, kind, left, bottom, right, top, fill_tile, path="(picture)"):
    """A picture's bytes with `left` .. `top` tiles added (or cut, when negative) at its edges; new points take the
    value of fill_tile's point (deep sea)."""
    w, h, step, top_down, _, raw = _decode(data, path)
    k = STEP[kind]
    W, H = w + (left + right) * k, h + (bottom + top) * k
    if W < 1 or H < 1:
        raise ValueError("%s would have no tiles left" % os.path.basename(path))
    fx, fy = (fill_tile[0], fill_tile[1]) if kind == "tiles" else \
        (2 * fill_tile[0] + 1, 2 * fill_tile[1] + 1) if kind == "corners" else (2 * fill_tile[0], 2 * fill_tile[1])
    fx, fy = min(fx, w - 1), min(fy, h - 1)

    def row_of(y, height):                         # storage row of bottom-up row y
        return (height - 1 - y) if top_down else y
    o = (row_of(fy, h) * w + fx) * step
    fill = bytes(raw[o:o + step])
    out = bytearray(fill * (W * H))
    dx, dy = left * k, bottom * k
    for Y in range(H):
        y = Y - dy
        if not 0 <= y < h:
            continue
        x0, x1 = max(0, -dx), min(w, W - dx)          # the old columns that land inside
        if x0 >= x1:
            continue
        src = row_of(y, h) * w
        dst = row_of(Y, H) * W
        out[(dst + x0 + dx) * step:(dst + x1 + dx) * step] = raw[(src + x0) * step:(src + x1) * step]
    return U._write(data, W, H, step, out)


FRAME_MAX = 30                  # points: a fog edge deeper than this is a hidden part of the map, not the frame


def fog_framed(old, new, left, bottom, right, top, path="map_fog.tga"):
    """map_fog.tga after a resize (Medieval II): its dark ragged frame stays at the map's edge, like a picture's frame
    moves with the canvas. The game's own fog is clear in the middle with a frame 1 - 14 points deep on the sides (a
    report: grown 17 tiles at the top, the old frame stayed inside as a black band across the map). On every changed
    side each line's frame (the points from the edge up to the first clear one, soft grey ones with it) goes to the
    new edge and its old place turns clear; a line dark deeper than FRAME_MAX (vanilla's hidden west, 35 tiles) is a
    hidden part of the map - it stays and the new points of that line take its dark. new: shifted()'s bytes."""
    w, h, step, td, _, raw = _decode(old, path)
    W, H, _, ntd, _, nraw = _decode(new, path)
    dx, dy = 2 * left, 2 * bottom

    def at(buf, width, height, down, x, y):           # bottom-up x, y
        o = (((height - 1 - y) if down else y) * width + x) * step
        return bytes(buf[o:o + step])
    clear = max((bytes(raw[o:o + step]) for o in range(0, w * h * step, step)), key=sum)    # the clearest point
    out = bytearray(nraw)

    def put(x, y, v):
        o = (((H - 1 - y) if ntd else y) * W + x) * step
        out[o:o + step] = v

    def frame(line):                                  # the points from the edge up to the first clear one
        got = []
        for v in line:
            if v == clear:
                break
            got.append(v)
        return got

    def side(n_lines, length, new_len, shift, old_line, new_xy, grow_at):
        for i in range(n_lines):
            seq = frame(old_line(i))
            if not seq:
                continue
            if len(seq) > FRAME_MAX:                  # a hidden part: its dark goes on over the new points
                for j in grow_at:
                    put(*new_xy(i, j), seq[0])
                continue
            for j in grow_at:                         # the new points clear (whatever the deep sea's fog was)
                put(*new_xy(i, j), clear)
            for k in range(len(seq)):                 # its old place turns clear ...
                j = k + shift
                if 0 <= j < new_len:
                    put(*new_xy(i, j), clear)
            for k, v in enumerate(seq):               # ... and the frame goes to the new edge
                put(*new_xy(i, k), v)

    def col(X):
        return min(max(X - dx, 0), w - 1)

    def row(Y):
        return min(max(Y - dy, 0), h - 1)
    if top:
        side(W, h, H, H - h - dy, lambda X: [at(raw, w, h, td, col(X), h - 1 - k) for k in range(h)],
             lambda X, j: (X, H - 1 - j), range(max(0, H - h - dy)))
    if bottom:
        side(W, h, H, dy, lambda X: [at(raw, w, h, td, col(X), k) for k in range(h)],
             lambda X, j: (X, j), range(max(0, dy)))
    if left:
        side(H, w, W, dx, lambda Y: [at(raw, w, h, td, k, row(Y)) for k in range(w)],
             lambda Y, j: (j, Y), range(max(0, dx)))
    if right:
        side(H, w, W, W - w - dx, lambda Y: [at(raw, w, h, td, w - 1 - k, row(Y)) for k in range(w)],
             lambda Y, j: (W - 1 - j, Y), range(max(0, W - w - dx)))
    return U._write(new, W, H, step, out)


def hgt_shifted(raw, left, bottom, right, top, fill_tile):
    """map_heights.hgt (uint32 w, h, then w * h float32 bottom-up) moved as the 2W+1 picture."""
    w, h = struct.unpack_from("<II", raw)
    vals = struct.unpack_from("<%df" % (w * h), raw, 8)
    fx, fy = min(2 * fill_tile[0] + 1, w - 1), min(2 * fill_tile[1] + 1, h - 1)
    fill = vals[fy * w + fx]
    W, H = w + 2 * (left + right), h + 2 * (bottom + top)
    out = [fill] * (W * H)
    dx, dy = 2 * left, 2 * bottom
    for Y in range(H):
        y = Y - dy
        if 0 <= y < h:
            for X in range(max(0, dx), min(W, w + dx)):
                out[Y * W + X] = vals[y * w + X - dx]
    return struct.pack("<II", W, H) + struct.pack("<%df" % (W * H), *out)


def _mover(left, bottom):
    """(xy(x, y), values(kind, nums)) moving tiles by the shift: distances, radii and sizes stay."""
    def xy(x, y):
        return x + left, y + bottom

    def values(kind, nums):
        if kind == "xy":
            return list(xy(nums[0], nums[1]))
        if kind == "xyr":
            return list(xy(nums[0], nums[1])) + [nums[2]]
        if kind == "dxy":
            return [nums[0]] + list(xy(nums[1], nums[2]))
        if kind == "area":
            return list(xy(nums[0], nums[1])) + list(xy(nums[2], nums[3]))
        return list(xy(nums[0], nums[1])) + list(nums[2:4])          # rect: a corner, then width / height
    return xy, values


def _texts(path):
    with open(path, encoding="latin-1") as fh:
        return fh.read().splitlines()


def places(mod, campaign):
    """Every place on the map a cut must not leave off it unasked: [(label, (x, y), kind, what)] - label 'file line N:
    what (x, y)'; kind town / port (what = the region), character (what = 'family' for a named character, else its
    kind: general, admiral, spy ...), resource, fort (what = fort / watchtower / landmark), event (what = its kind),
    script (what = the file). Read once; blocking() then checks any cut against it at once (the Map size window, as
    the edges are dragged)."""
    out = []
    for region, t in sorted(mod.city_tiles(campaign).items()):
        out.append(("map_regions.tga: the town of %s (%d, %d)" % (region, t[0], t[1]), tuple(t), "town", region))
    from .mapedit import ports
    for region, t in sorted(ports(mod, campaign).items()):
        out.append(("map_regions.tga: the port of %s (%d, %d)" % (region, t[0], t[1]), tuple(t), "port", region))
    camp = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt"))
    strat = mod.campaign_file(campaign, "descr_strat.txt")
    for i, text in enumerate(_texts(strat)):
        code = text.split(";")[0]
        for rx, kind in ((U.RE_CHAR_XY, "character"), (U.RE_RESOURCE, "resource"), (U.RE_FORT, "fort")):
            m = rx.search(code)
            if not m:
                continue
            p = (int(m.group(2)), int(m.group(4)))
            if kind == "character":
                parts = [x.strip() for x in code.split(",")]
                what = next((k for k in parts if k in CHARACTER_KINDS), "character")
                what = "family" if what == "named character" else what
            elif kind == "fort":
                what = code.split()[0]
            else:
                what = ""
            out.append(("descr_strat.txt line %d: %s (%d, %d)" % (i + 1, code.strip()[:60], p[0], p[1]), p, kind, what))
            break
    ev = os.path.join(camp, "descr_events.txt")
    if os.path.isfile(ev):
        what = ""
        for i, text in enumerate(_texts(ev)):
            code = text.split(";")[0]
            t = code.split()
            if t[:1] == ["event"]:
                what = t[1] if len(t) > 1 else ""
            m = U.RE_POSITION.search(code)
            if m:
                p = (int(m.group(2)), int(m.group(4)))
                out.append(("descr_events.txt line %d: %s (%d, %d)" % (i + 1, code.strip()[:60], p[0], p[1]), p,
                            "event", what))
    _, same = _mover(0, 0)
    for path in U.script_files(mod, campaign):
        for i, text in enumerate(_texts(path)):
            code = text.split(";")[0]
            for p in _tiles_in(text, same) + [(int(m.group(2)), int(m.group(4))) for m in U.RE_CHAR_XY.finditer(code)]:
                out.append(("%s line %d: %s (%d, %d)" % (os.path.basename(path), i + 1, code.strip()[:60], p[0], p[1]),
                            p, "script", os.path.basename(path)))
    return out


def off(p, W, H, left=0, bottom=0, right=0, top=0, town=False):
    """Whether place p (as now) is off the W x H map the edges make. town: a town or port is off on the edge a cut
    makes too - the game cannot place one there and stops while it builds map.rwm (report #158: Girga and Quseir
    left on the bottom row)."""
    x, y = p[0] + left, p[1] + bottom
    if not (0 <= x < W and 0 <= y < H):
        return True
    return town and ((left < 0 and x == 0) or (bottom < 0 and y == 0) or (right < 0 and x == W - 1) or
                     (top < 0 and y == H - 1))


def blocking(found, width, height, left=0, bottom=0, right=0, top=0):
    """Of places() those a cut would leave off a width x height map, as places() gives them ((x, y) as now)."""
    W, H = width + left + right, height + bottom + top
    return [x for x in found if off(x[1], W, H, left, bottom, right, top, x[2] in ("town", "port"))]


def off_map(mod, campaign, left, bottom, right, top):
    """What a cut would leave off the map: ['file line N: what (x, y)']. Towns and ports from map_regions."""
    img = read_tga(mod.campaign_file(campaign, "map_regions.tga"))
    return [x[0] for x in blocking(places(mod, campaign), img.width, img.height, left, bottom, right, top)]


def cut_words(hit, waste=False):
    """What a cut takes off, in a few plain lines (the question before it): blocking()'s list grouped. waste: REX /
    M2EX beside the game - the land that stays of a town cut off goes to the common wasteland (clear_cut), else to
    the neighbour region."""
    by = {}
    for label, xy, kind, what in hit:
        by.setdefault(kind, []).append((label, xy, what))
    lines = []
    if by.get("town"):
        towns = sorted({w for _, _, w in by["town"]})
        lines.append("%d town(s) with their regions: %s%s - %s" % (
            len(towns), ", ".join(towns[:8]), " ..." if len(towns) > 8 else "",
            "the land of theirs that stays goes to the common wasteland (nobody's land)" if waste else
            "the land of theirs that stays goes to the neighbour region"))
    if by.get("port"):
        ports_ = sorted({w for _, _, w in by["port"]} - {w for _, _, w in by.get("town", [])})
        if ports_:
            lines.append("%d port(s) of regions that stay: %s (their harbour buildings with them)" % (
                len(ports_), ", ".join(ports_[:8]) + (" ..." if len(ports_) > 8 else "")))
    chars = by.get("character", [])
    family = [x for x in chars if x[2] == "family"]
    rest = [x for x in chars if x[2] != "family"]
    if rest:
        kinds = {}
        for _, _, w in rest:
            kinds[w or "character"] = kinds.get(w or "character", 0) + 1
        lines.append("%d army / fleet / agent (%s) - with their soldiers and ships" % (
            len(rest), ", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))))
    if family:
        lines.append("%d family member(s) (never deleted) move to the nearest town their faction keeps" % len(family))
    if by.get("resource"):
        lines.append("%d resource(s)" % len(by["resource"]))
    if by.get("fort"):
        kinds = {}
        for _, _, w in by["fort"]:
            kinds[w] = kinds.get(w, 0) + 1
        lines.append(", ".join("%d %s(s)" % (n, k) for k, n in sorted(kinds.items())))
    if by.get("event"):
        lines.append("%d event(s) placed there (%s)" % (len(by["event"]), ", ".join(sorted({w for _, _, w in
                                                                                         by["event"]}))))
    if by.get("script"):
        lines.append("%d line(s) of the campaign's scripts name tiles there - left as they are: change them by hand "
                     "(the game may stop at them)" % len(by["script"]))
    return lines


def lost_factions(mod, campaign, left=0, bottom=0, right=0, top=0, owners=None):
    """{faction: [its towns on the part cut off]} of the factions (rebels aside) the cut would leave without a town.
    owners: {region: owner} as they will be (the changes not written yet), else descr_strat's."""
    from .strat import Strat
    img = mod.region_map(campaign)
    W, H = img.width + left + right, img.height + bottom + top
    if owners is None:
        owners = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).owners()
    tiles = mod.city_tiles(campaign)
    cut = {r for r, t in tiles.items() if off(t, W, H, left, bottom, right, top, town=True)}
    out = {}
    for fac in sorted({owners.get(r) for r in cut} - {None, "slave"}):
        if not [r for r, o in owners.items() if o == fac and r not in cut]:
            out[fac] = sorted(r for r in cut if owners.get(r) == fac)
    return out


def clear_cut(plan, campaign, left=0, bottom=0, right=0, top=0, factions_out=()):
    """Everything standing on the part a cut takes off, taken off first, in the plan (the modder said yes to it):
    - a town: its region goes from every file (regiondelete), with or without an engine (the user, 2026-10-08: 'just
      delete the region, the modder fills the gap himself'); the part of its land that stays never stays without a
      region (report #178: 'Region has no descr_regions.txt entry', then a crash): with REX / M2EX it goes to the ONE
      common wasteland (regiondelete.common_wasteland - the user, 2026-10-10: 'variant B'), without an engine to the
      neighbour that stays (refused when it touches none);
    - the port of a region that stays: taken off with the harbour buildings (mapedit._remove_ports);
    - a member of a faction's family (a named character: the leader, the heir, the family tree) moves into the
      nearest town his faction keeps; every other character - armies, agents, fleets, rebels - goes with his army;
    - resources, forts, watchtowers, wonders: their lines go;
    - an event placed there goes;
    - lines of the campaign's scripts naming tiles there are left as they are (returned as warnings);
    - a faction left without a town, when it is in factions_out (the modder said yes): taken out of the campaign
      with all its people (factionout.take_out - it stays in the mod).
    Refused before anything is written (ValueError, every reason in plain words): a faction left without a town, a
    region a campaign script or a faction's rising names (regiondelete.refusals), a family member whose faction keeps
    no town to go to, a faction's rising placed on the cut part, without an engine land left of a cut town that
    touches no region that stays. Returns the warnings."""
    from . import regiondelete as RD
    from .edit import _has_army, map_changes
    from .events import apply as events_apply, path_of, read as events_read
    from .mapedit import _remove_ports, ports
    from .resources import apply as res_apply, read as res_read
    from .strat import Strat
    mod = plan.mod
    img = mod.region_map(campaign)
    W, H = img.width + left + right, img.height + bottom + top

    def gone(p):
        return off(p, W, H, left, bottom, right, top)

    def town_gone(p):                               # a town / port on the edge the cut makes goes too
        return off(p, W, H, left, bottom, right, top, town=True)
    strat_path = mod.campaign_file(campaign, "descr_strat.txt")
    s0 = Strat(mod.load(strat_path))
    owners = s0.owners()
    tiles = mod.city_tiles(campaign)
    cut = sorted(r for r, t in tiles.items() if town_gone(t))
    errors, warn, out = [], [], []
    for fac in sorted({owners.get(r) for r in cut} - {None, "slave"}):
        if not [r for r, o in owners.items() if o == fac and r not in cut]:
            if fac in factions_out:
                out.append(fac)
                continue
            errors.append("%s would keep no town (%s on the part cut off) - a faction without a town dies as the "
                          "campaign loads and the game crashes; give it a town that stays first" % (
                              fac, ", ".join(r for r in cut if owners.get(r) == fac)))
    # a town cut = its region goes from the files (the user, 2026-10-08: 'just delete the region'); the land of it
    # that stays never keeps a colour with no region - the game stops at it (report #178): with REX / M2EX it goes to
    # the ONE common wasteland (the user, 2026-10-10: 'variant B - all the free land into ONE common wasteland
    # region'), without an engine to the neighbour that stays (a region ringed by other cut towns' land follows them)
    into, waste, leftover = {}, set(), {}
    for r in cut:
        stays = [p for p in RD.region_pixels(mod, campaign, r) if not gone(p)]
        into[r] = (None, False)
        if stays:
            leftover[r] = stays
    wl = RD.common_wasteland(mod, campaign) if leftover else None
    given = {}
    if leftover and wl is None:
        given, alone = RD.receivers(_leftover_near(img, mod.region_colours(campaign), leftover, gone), list(leftover))
        for r in alone:
            errors.append("%d tile(s) of %s stay on the map and touch no region that stays - the original game cannot "
                          "have land without a region (with REX / M2EX it would be a wasteland); give that land to a "
                          "region first (Map > Edit regions) or cut so that it goes too" % (len(leftover[r]), r))
    errs, said = RD.refusals(mod, campaign, cut, last_town=False)     # the files read once for every town cut
    errors += errs
    ev_path = path_of(mod, campaign)
    events = [e for e in (events_read(mod.load(ev_path)) if ev_path else []) if e.get("position") and
              gone(e["position"]) and not (e["kind"] == "emergent_faction" and e["name"] in out)]
    for e in events:
        if e["kind"] == "emergent_faction":
            errors.append("%s rises at %d, %d by an event - on the part cut off; place it elsewhere first (Events and "
                          "later factions)" % (e["name"], e["position"][0], e["position"][1]))
    # where each family member on the cut part goes: the nearest town his faction keeps that may take him
    armies = {c.xy for fb in s0.factions for c in fb.characters if c.xy and _has_army(s0.lines[c.start:c.end])}
    armies -= {c.xy for fb in s0.factions for c in fb.characters if c.xy and gone(c.xy)}
    remove, moves = {}, {}
    town_tiles = {tuple(t) for t in tiles.values()}
    for fb in s0.factions:
        if fb.name in out:                          # it leaves the campaign with all its people
            continue
        mine = [tiles[r] for r, o in owners.items() if o == fb.name and r not in cut and r in tiles]
        for c in fb.characters:
            if not c.xy or not gone(c.xy):
                continue
            if not c.named or fb.name == "slave":      # the rebels' generals go too: they have no town to keep
                remove.setdefault(fb.name, []).append({"name": c.name, "from": list(c.xy)})
                continue
            army = _has_army(s0.lines[c.start:c.end])
            to = next((t for t in _spots(mine, c.xy, town_tiles, gone)
                       if not mod.tile_problem(campaign, t, c.kind, army, armies)), None)
            if to is None:
                errors.append("%s (%s's family) stands on the part cut off and %s keeps no town he could go to - move "
                              "him first" % (c.name, fb.name, fb.name))
                continue
            if army:
                armies.add(tuple(to))
            moves.setdefault(fb.name, []).append({"name": c.name, "from": list(c.xy), "to": list(to)})
    if errors:
        raise ValueError("the cut cannot take these off the map:\n- " + "\n- ".join(dict.fromkeys(errors)))
    RD._delete(plan, campaign, into, waste)          # every file read once for all the towns cut
    if leftover:                                     # its town and port pixels with it: plain land
        regs = mod.regions(campaign)
        path = mod.campaign_file(campaign, "map_regions.tga")
        paint = {tuple(p): wl[1] if wl else regs[given[r]]["colour"] for r, px in leftover.items() for p in px}
        plan.patch_tga(path, paint)
        if wl and wl[2]:
            RD.make_wasteland(plan, campaign, wl[0], wl[1], paint)
        for r, px in sorted(leftover.items()):
            plan.notes.append((RD._shown(mod, path), "%d tile(s) of %s left by the cut -> %s" % (
                len(px), r, "%s, the common wasteland - nobody's land (REX / M2EX)" % wl[0] if wl else given[r])))
    for w in said:
        plan.warn(None, w)
    lost_ports = [r for r, t in ports(mod, campaign).items() if r not in cut and town_gone(t)]
    if lost_ports:
        _remove_ports(plan, campaign, sorted(lost_ports))
    from .factionout import take_out
    for fac in out:
        warn += take_out(plan, campaign, fac)
    f = plan.edit(strat_path)
    s = Strat(f)
    # a fleet the port took out to the sea beside may stand on the cut part too
    for fb in s.factions:
        for c in fb.characters:
            if c.xy and gone(c.xy) and not c.named and {"name": c.name, "from": list(c.xy)} not in \
                    remove.get(fb.name, []):
                remove.setdefault(fb.name, []).append({"name": c.name, "from": list(c.xy)})
    # only those still there: a town's deletion took the rebels standing in it (its garrison) with it
    def still(items):
        return {fac: [m for m in ms if any(c.name == m["name"] and list(c.xy or ()) == m["from"]
                                           for c in (s.faction(fac).characters if s.faction(fac) else []))]
                for fac, ms in items.items()}
    left_out, moves = still(remove), still(moves)
    map_changes(plan, campaign, {"remove": {k: v for k, v in left_out.items() if v},
                                 "moves": {k: v for k, v in moves.items() if v}})
    f = plan.edit(strat_path)
    res = [r.index for r in res_read(f) if gone(r.xy)]
    forts = [fo.line for fo in Strat(f).forts if fo.xy and gone(fo.xy)]
    if res or forts:
        res_apply(plan, campaign, {"removed": res, "forts": {"removed": forts}})
    if events:
        events_apply(plan, campaign, {"remove": [e["id"] for e in events]})
    hit = [x for x in places(mod, campaign) if x[2] == "script" and gone(x[1])]
    if hit:
        warn.append("%d line(s) of the campaign's scripts name tiles the cut takes off - left as they are, change "
                    "them by hand (the game may stop at them): %s%s" % (
                        len(hit), "; ".join(x[0] for x in hit[:6]), " ..." if len(hit) > 6 else ""))
    return warn


def _leftover_near(img, by_colour, leftover, gone):
    """{cut region: [(region, border length)]} - the regions the land a cut town leaves touches side by side (other
    cut towns' land left among them), the longest border first (regiondelete.receivers reads it)."""
    from .regiondelete import N4
    out = {}
    for r, px in leftover.items():
        own, count = {tuple(p) for p in px}, {}
        for x, y in own:
            for dx, dy in N4:
                p = (x + dx, y + dy)
                if p in own or gone(p) or not (0 <= p[0] < img.width and 0 <= p[1] < img.height):
                    continue
                n = by_colour.get(img.get(*p))
                if n and n != r:
                    count[n] = count.get(n, 0) + 1
        out[r] = sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))
    return out


def _spots(towns, xy, town_tiles, gone, reach=3):
    """Where a family member from the cut part may go: his faction's towns that stay, the nearest first, each
    followed by the land beside it (a town holds one army - its own general may be in it), never another town's tile
    nor the part cut off."""
    for t in sorted(towns, key=lambda t: abs(t[0] - xy[0]) + abs(t[1] - xy[1])):
        t = tuple(t)
        yield t
        ring = [(t[0] + dx, t[1] + dy) for dx in range(-reach, reach + 1) for dy in range(-reach, reach + 1)
                if (dx, dy) != (0, 0)]
        for p in sorted(ring, key=lambda p: (max(abs(p[0] - t[0]), abs(p[1] - t[1])),
                                             abs(p[0] - t[0]) + abs(p[1] - t[1]))):
            if p not in town_tiles and not gone(p):
                yield p


CHARACTER_KINDS = ("named character", "general", "admiral", "spy", "assassin", "diplomat", "merchant", "priest",
                   "princess", "heretic", "witch", "inquisitor", "captain")


def _tiles_in(text, values):
    """The new tiles of a script line's tile commands (the shifted x, y pairs the commands take)."""
    out = []
    code = text.partition(";")[0]
    cmds = list(U.RE_SCRIPT_CMD.finditer(code))
    for k, m in enumerate(cmds):
        kind = U.SCRIPT_TILES[next(c for c in U.SCRIPT_TILES if c.lower() == m.group(1).lower())]
        end = cmds[k + 1].start() if k + 1 < len(cmds) else len(code)
        stop = U.RE_SCRIPT_STOP.search(code, m.end(), end)
        if stop:
            end = stop.start()
        ints = [int(i.group()) for i in list(U.RE_INT.finditer(code, m.end(), end))[:U.NEEDS[kind]]]
        if len(ints) < U.NEEDS[kind]:
            continue
        new = values(kind, ints)
        pairs = {"xy": [(0, 1)], "xyr": [(0, 1)], "dxy": [(1, 2)], "area": [(0, 1), (2, 3)], "rect": [(0, 1)]}[kind]
        out += [(new[a], new[b]) for a, b in pairs]
    return out


def radar_resized(data, w, h, left, bottom, right, top, fill_tile=None):
    """A minimap picture (radar_map1 / radar_map2 / map_radar2.tga, its own size) cut or grown in the proportion of
    the map's W x H tiles: (TGA bytes, (new w, new h)), or None without Pillow. New parts take the picture's colour at
    fill_tile (the map's deep sea; else its top-left corner). A one-colour border line of the picture (Medieval II's
    radar_map2: a blue line along the top and the right) goes to the new edge, not left inside (a report: grown at
    the top, the minimap got a blue band)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    import io
    pic = Image.open(io.BytesIO(data))
    pic.load()
    t, b, lft, r, edge = radar_frame(pic)
    inner = pic.crop((lft, t, pic.width - r, pic.height - b)) if (t, b, lft, r) != (0, 0, 0, 0) else pic
    sx, sy = inner.width / float(w), inner.height / float(h)
    if fill_tile is not None:
        fx = min(inner.width - 1, max(0, int((fill_tile[0] + 0.5) * sx)))
        fy = min(inner.height - 1, max(0, int((h - 1 - fill_tile[1] + 0.5) * sy)))     # the picture is top row first
        fill = inner.getpixel((fx, fy))
    else:
        fill = inner.getpixel((0, 0))
    iw = max(1, int(round((w + left + right) * sx)))
    ih = max(1, int(round((h + bottom + top) * sy)))
    body = Image.new(pic.mode, (iw, ih), fill)
    body.paste(inner, (int(round(left * sx)), int(round(top * sy))))
    nw, nh = iw + lft + r, ih + t + b
    out = Image.new(pic.mode, (nw, nh), fill)
    out.paste(body, (lft, t))
    for i, c in enumerate(edge["top"] if t else []):
        out.paste(c, (0, i, nw, i + 1))
    for i, c in enumerate(edge["bottom"] if b else []):
        out.paste(c, (0, nh - 1 - i, nw, nh - i))
    for i, c in enumerate(edge["left"] if lft else []):
        out.paste(c, (i, 0, i + 1, nh))
    for i, c in enumerate(edge["right"] if r else []):
        out.paste(c, (nw - 1 - i, 0, nw - i, nh))
    buf = io.BytesIO()
    out.save(buf, format="TGA")
    return buf.getvalue(), (nw, nh)


def radar_frame(pic):
    """(top, bottom, left, right, {side: [colour of each border line]}) of a minimap picture (a Pillow image): its
    one-colour border lines (Medieval II's radar_map2: a blue line along the top and the right), not the map."""
    px = pic.load()

    def border(line):                               # (nearly) one colour all along - a texture never is
        first = line[0]
        if not isinstance(first, tuple):
            first = (first,)

        def near(v):
            v = v if isinstance(v, tuple) else (v,)
            return all(abs(a - b) <= 8 for a, b in zip(v, first))
        return line[0] if sum(1 for v in line if near(v)) >= 0.75 * len(line) else None
    edge = {}                                       # side -> [colour of each border line, outermost first]
    lines = {"top": lambda i: [px[x, i] for x in range(pic.width)],
             "bottom": lambda i: [px[x, pic.height - 1 - i] for x in range(pic.width)],
             "left": lambda i: [px[i, y] for y in range(pic.height)],
             "right": lambda i: [px[pic.width - 1 - i, y] for y in range(pic.height)]}
    for side, line in lines.items():
        got = []
        while len(got) < 3:
            c = border(line(len(got)))
            if c is None:
                break
            got.append(c)
        if got and (len(got) == 3 or border(line(len(got))) is not None):
            got = []                                # one colour on and on: the picture's own (flat sea), no border
        edge[side] = got
    t, b, lft, r = (len(edge[k]) for k in ("top", "bottom", "left", "right"))
    if pic.width <= lft + r or pic.height <= t + b:
        return 0, 0, 0, 0, {k: [] for k in edge}
    return t, b, lft, r, edge


def plan_resize(plan, campaign, left=0, bottom=0, right=0, top=0, clear=False, factions_out=()):
    """Every file of the map grown (positive) or cut (negative) by that many tiles at each edge, in the plan.
    Returns the warnings; ValueError (with every place named) when a cut would leave something off the map -
    unless clear: then what stands on the part cut off is taken off first (clear_cut - the modder was asked)."""
    mod = plan.mod
    if not any((left, bottom, right, top)):
        raise ValueError("no tiles to add or cut")
    first = []
    if clear:
        first = clear_cut(plan, campaign, left, bottom, right, top, factions_out=factions_out)
    else:
        gone = off_map(mod, campaign, left, bottom, right, top)
        if gone:
            raise ValueError("the cut would leave %d place(s) off the map - move them first:\n%s" % (
                len(gone), "\n".join(gone[:30]) + ("\n... and %d more" % (len(gone) - 30) if len(gone) > 30
                                                    else "")))
    regions_path = mod.campaign_file(campaign, "map_regions.tga")
    img = read_tga(regions_path)
    W, H = img.width + left + right, img.height + bottom + top
    fill = deepest_sea(mod, campaign) if max(left, bottom, right, top) > 0 else (0, 0)   # a cut adds no point
    xy, values = _mover(left, bottom)
    words = _words(left, bottom, right, top)
    base = os.path.dirname(regions_path)
    camp = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt"))
    warn = list(first)
    for folder, pictures in ((base, U.BASE_PICTURES), (camp, U.CAMPAIGN_PICTURES)):
        for name, kind in pictures.items():
            p = os.path.join(folder, name)
            if not os.path.isfile(p):
                continue
            data = plan.binaries.get(p)             # map_regions.tga as the cut's clearing left it
            if data is None:
                with open(p, "rb") as fh:
                    data = fh.read()
            pw, ph = struct.unpack_from("<HH", data, 12)
            want = {"tiles": (img.width, img.height), "corners": (2 * img.width + 1, 2 * img.height + 1),
                    "double": (2 * img.width, 2 * img.height)}[kind]
            if (pw, ph) != want:                    # a picture of its own size (Medieval II's radar maps, a
                if name.startswith(("radar_map", "map_radar")):
                    # the campaign map's minimap: a picture of its own size, but of THE map - the game lays the
                    # real borders over it, so it is cut / grown in the same proportion (report: Rome HLR's minimap
                    # kept its old picture after a cut, the borders drawn over the wrong land)
                    got = radar_resized(data, img.width, img.height, left, bottom, right, top, fill)
                    if got:
                        plan.binary(p, got[0])
                        plan.note(None, "%s %s in proportion (%d x %d -> %d x %d)" % (name, words, pw, ph, *got[1]))
                    else:
                        warn.append("%s could not be cut with the map (no Pillow) - paint it again by hand" % name)
                    continue
                plan.note(None, "%s left as it is (%d x %d - not tied to the map's tiles)" % (name, pw, ph))
                continue                            # disasters.tga left from Rome) is not the map's: left alone
            got = shifted(data, kind, left, bottom, right, top, fill, p)
            if name.lower() == "map_fog.tga":       # its dark frame goes to the new edge (no band across the map)
                plan.binary(p, fog_framed(data, got, left, bottom, right, top, p))
                plan.note(None, "%s %s (its dark frame moved to the new edge)" % (name, words))
                continue
            plan.binary(p, got)
            plan.note(None, "%s %s (new tiles: the map's deep sea)" % (name, words))
    hgt = os.path.join(base, "map_heights.hgt")
    hpath = os.path.join(base, "map_heights.tga")
    if os.path.isfile(hgt) and os.path.isfile(hpath) and U.hgt_usable(hgt, hpath):
        with open(hgt, "rb") as fh:
            plan.binary(hgt, hgt_shifted(fh.read(), left, bottom, right, top, fill))
        plan.note(None, "map_heights.hgt %s" % words)
    elif os.path.isfile(hgt):
        warn.append("map_heights.hgt was empty or did not fit map_heights.tga - left as it is")
    t = os.path.join(base, "descr_terrain.txt")
    if os.path.isfile(t):
        f = plan.edit(t)
        n = 0
        for i in range(len(f.raw)):
            m = re.match(r"^(\s*)(width|height)(\s+)(\d+)(.*)$", f.text(i))
            if m:
                f.raw[i] = f.make(m.group(1) + m.group(2) + m.group(3) + str(W if m.group(2) == "width" else H)
                                  + m.group(5))
                n += 1
        if n:
            plan.note(f, "the map's size: %d x %d tiles" % (W, H))
        else:
            warn.append("descr_terrain.txt: no width / height line found - check its dimensions by hand")
    shift = (left, bottom) != (0, 0)
    if shift:
        f = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
        n = U.move_coordinates(f, (U.RE_CHAR_XY, U.RE_RESOURCE, U.RE_FORT), xy)
        plan.note(f, "%d character / resource / fort / wonder place(s) moved by %d, %d" % (n, left, bottom))
        ev = os.path.join(camp, "descr_events.txt")
        if os.path.isfile(ev):
            f = plan.edit(ev)
            n = U.move_coordinates(f, (U.RE_POSITION,), xy)
            if n:
                plan.note(f, "%d event position(s) moved" % n)
        for p in U.script_files(mod, campaign):
            f = plan.edit(p)
            n, check = U.move_script(f, values, xy)
            if n:
                plan.note(f, "%d place(s) on the campaign map moved by %d, %d (distances and sizes stay)"
                          % (n, left, bottom))
            if check:
                warn.append("%s: line(s) %s hold numbers that may be map tiles the editor does not know - check them "
                            "by hand (a tile x, y becomes x%+d, y%+d)" % (os.path.basename(p), ", ".join(
                                str(k) for k in check[:12]) + (" ..." if len(check) > 12 else ""), left, bottom))
        one = mod.campaigns() == [campaign]
        for key in ("traits", "ancillaries"):
            p = mod.file(key)
            if not p:
                continue
            hits = sum(1 for line in _texts(p) if U.RE_SCRIPT_CMD.search(line.split(";")[0]))
            if not hits:
                continue
            if one:
                f = plan.edit(p)
                n, _ = U.move_script(f, values, xy)
                plan.note(f, "%d 'near a tile' / 'in a rectangle' condition(s) moved" % n)
            else:
                warn.append("%s: %d condition(s) name map tiles - not moved, the file serves the mod's other "
                            "campaigns too (a tile x, y becomes x%+d, y%+d on this campaign's map)"
                            % (os.path.basename(p), hits, left, bottom))
        for sub, hits in U.code_with_tiles(os.path.dirname(os.path.abspath(mod.data))):
            warn.append("%s: %s - Lua / Squirrel scripts are not changed; if they place things on the map by x, y, "
                        "move those by %d, %d by hand" % (sub, ", ".join(hits[:8]), left, bottom))
    p = os.path.join(base, "map.rwm")
    if os.path.isfile(p):
        plan.delete(p, "the game builds it again from the new pictures")
    from .limits import HARD_LIMITS, game_kind, lifted
    most = HARD_LIMITS[game_kind(mod)]["map_size"]
    if max(W, H) > most and not lifted(mod, "map_size"):
        warn.append("The map is %d tiles wide now - the original exe stops at %d: run it with %s"
                    % (max(W, H), most, "REX" if game_kind(mod) == "rome" else "M2EX"))
    for w_ in warn:
        plan.warn(None, w_)
    return warn


def _words(left, bottom, right, top):
    parts = []
    for n, side in ((left, "left"), (right, "right"), (top, "top"), (bottom, "bottom")):
        if n:
            parts.append("%s %d at the %s" % ("grown by" if n > 0 else "cut by", abs(n), side))
    return ", ".join(parts)
