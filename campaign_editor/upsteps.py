"""The bigger map (x3) step by step: five steps, each written to the files with its own backup, each checked after
it, the map shown in the editor between them - look, fix by hand with the Map editor and the Terrain tab, then the
next step. One step builds on what the one before wrote (and on the modder's fixes since):

  1 grid      every tile a 3 x 3 block (exact colours, no smoothing); towns, armies, resources, events and the
              campaign's scripts moved to their blocks' middles; descr_terrain's size; map.rwm removed.
  2 smoothing the coast, the borders of regions (a border along a river stays on the river), ground types and
              climates drawn smooth - from the old map (fixes made after step 1 are drawn over: fix after this one).
  3 heights   the relief from the old heights over the coast map_regions has NOW (fixes after step 2 count): every
              sea point under the water, no land point under it (no saw teeth, no holes), the old map's own shore,
              slopes no steeper than the old map's; map_heights.hgt the same; the ground's sea follows the heights,
              mountains only where the land stands high, shallow sea along the coast.
  4 rivers    the old rivers drawn over the land as it is NOW: one pixel wide, only on land, ending on the last land
              tile at the water, no square corners.
  5 objects   every town on its block's middle, every port on a coastal land tile touching the sea and its region,
              every army / agent / fleet / resource on a tile it may stand on (moved to the nearest one when not).

The old map is read from step 1's backup; 'Put the old map back' restores that backup (and every step after it).
Both games."""

import os
import re
import struct

from . import upscale as U
from .plan import Plan, _copy_of
from .textio import tokens

STEPS = (("grid", "The grid: every tile becomes a 3 x 3 block"),
         ("smoothing", "Smoothing: coast, region borders, ground and climates"),
         ("heights", "Heights: the relief, every sea point under the water and no land point under it"),
         ("rivers", "Rivers: one pixel wide, on land only, ending at the water"),
         ("objects", "Objects: towns, ports, armies, agents, fleets and resources on tiles they may stand on"))
WORK = "map_x3"


def _base(mod, campaign):
    return os.path.dirname(mod.campaign_file(campaign, "map_regions.tga"))


def old(mod, st, path):
    """The file as it was before step 1 (step 1's backup), else as it is."""
    if not st.get("bdir"):
        return path
    p = _copy_of(st["bdir"], os.path.relpath(path, os.path.dirname(mod.data)))
    return p if os.path.isfile(p) else path


def _lands(mod, campaign, regions_path, heights_path):
    colours = [v["colour"] for v in mod.regions(campaign).values()]
    return U.land_colours(regions_path, colours, heights_path if heights_path and os.path.isfile(heights_path)
                          else None)


def _land_now(regions_path, lands):
    """Mask of the land tiles of a map_regions as it is (towns and ports land)."""
    _, w, h, _, _, at = U._pixels(regions_path)
    lands = set(lands) | {U.CITY, U.PORT}
    m = U.Mask(w, h)
    for y in range(h):
        for x in range(w):
            if at(x, y) in lands:
                m.b[y * w + x] = 1
    return m


def _block_mask(regions_path, lands):
    """Mask of the new tiles: land exactly where the old tile was (3 x 3 blocks)."""
    _, w, h, _, _, at = U._pixels(regions_path)
    lands = set(lands) | {U.CITY, U.PORT}
    W, H = w * U.FACTOR, h * U.FACTOR
    m = U.Mask(W, H)
    for Y in range(H):
        for X in range(W):
            if at(X // U.FACTOR, Y // U.FACTOR) in lands:
                m.b[Y * W + X] = 1
    return m


def _hgt_blocks(raw):
    """map_heights.hgt (uint32 w, h, then w * h float32) at the 2W+1 corners of the 3 x bigger map, each new point
    the old point it lies on (no blending - step 3 draws the relief)."""
    w, h = struct.unpack_from("<II", raw)
    vals = struct.unpack_from("<%df" % (w * h), raw, 8)
    xs, ys = U._index("corners", w), U._index("corners", h)
    W, H = len(xs), len(ys)
    out = [vals[y * w + x] for y in ys for x in xs]
    return struct.pack("<II", W, H) + struct.pack("<%df" % (W * H), *out)


# ---------------------------------------------------------------- 1 grid
def step_grid(plan, campaign, st):
    mod = plan.mod
    warn = []
    base = _base(mod, campaign)
    regions_path = mod.campaign_file(campaign, "map_regions.tga")
    camp = os.path.dirname(mod.campaign_file(campaign, "descr_strat.txt"))
    hpath = os.path.join(base, "map_heights.tga")
    lands = _lands(mod, campaign, regions_path, hpath)
    info = {}
    plan.binary(regions_path, U.regions_scaled(regions_path, lands, _block_mask(regions_path, lands), info=info))
    plan.note(None, "map_regions.tga made 3 x bigger in blocks (each town on its block's middle, each port on a "
                    "coastal pixel of its block)")
    for (x, y), spot, why in info.get("moved_ports", []):
        warn.append("the port at %d, %d: %s (now at %d, %d)" % (x, y, why, spot[0], spot[1]))
    feats = os.path.join(base, "map_features.tga")
    if os.path.isfile(feats):
        data, _ = U.features_scaled(feats, info.get("land"), natural=False)
        plan.binary(feats, data)
        plan.note(None, "map_features.tga: rivers as 1-pixel lines through the blocks' middles (step 4 draws them "
                        "for good)")
    for name, kind in U.BASE_PICTURES.items():
        p = os.path.join(base, name)
        if os.path.isfile(p) and name not in ("map_regions.tga", "map_features.tga"):
            plan.binary(p, U.scaled(p, kind)[0])
            plan.note(None, "%s made 3 x bigger in blocks" % name)
    hgt = os.path.join(base, "map_heights.hgt")
    if os.path.isfile(hgt) and os.path.isfile(hpath) and U.hgt_usable(hgt, hpath):
        with open(hgt, "rb") as fh:
            plan.binary(hgt, _hgt_blocks(fh.read()))
        plan.note(None, "map_heights.hgt made 3 x bigger in blocks")
    for name, kind in U.CAMPAIGN_PICTURES.items():
        p = os.path.join(camp, name)
        if os.path.isfile(p):
            plan.binary(p, U.scaled(p, kind)[0])
    t = os.path.join(base, "descr_terrain.txt")
    if os.path.isfile(t):
        if U._dimensions(plan.edit(t), 1.0) == 0:
            warn.append("descr_terrain.txt: no width / height line found - check its dimensions by hand")
    f = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
    n = U.move_coordinates(f, (U.RE_CHAR_XY, U.RE_RESOURCE, U.RE_FORT))
    plan.note(f, "%d character / resource / fort / wonder place(s) moved to the middle of their 3 x 3 block" % n)
    ev = os.path.join(camp, "descr_events.txt")
    if os.path.isfile(ev):
        U.move_coordinates(plan.edit(ev), (U.RE_POSITION,))
    p = os.path.join(base, "map.rwm")
    if os.path.isfile(p):
        plan.delete(p, "the game builds it again from the bigger pictures")
    for p in U.script_files(mod, campaign):
        n, check = U.move_script(plan.edit(p))
        if check:
            warn.append("%s: line(s) %s hold numbers that may be map tiles the editor does not know - check them by "
                        "hand (a tile x, y becomes 3x+1, 3y+1)" % (os.path.basename(p), ", ".join(
                            str(k) for k in check[:12])))
    if mod.campaigns() == [campaign]:
        for key in ("traits", "ancillaries"):
            p = mod.file(key)
            if p:
                with open(p, encoding="latin-1") as fh:
                    if any(U.RE_SCRIPT_CMD.search(line.split(";")[0]) for line in fh):
                        U.move_script(plan.edit(p))
    for sub, hits in U.code_with_tiles(os.path.dirname(os.path.abspath(mod.data))):
        warn.append("%s: %s - Lua / Squirrel scripts are not changed; if they place things on the map by x, y, make "
                    "those 3x+1, 3y+1 by hand" % (sub, ", ".join(hits[:8])))
    return warn


def check_grid(mod, campaign, st):
    """Every town on a block's middle."""
    off = [r for r, (x, y) in mod.city_tiles(campaign).items() if x % 3 != 1 or y % 3 != 1]
    return ["%d town(s) not on a block's middle: %s" % (len(off), ", ".join(off[:6]))] if off else []


# ---------------------------------------------------------------- 2 smoothing
def step_smooth(plan, campaign, st):
    mod = plan.mod
    base = _base(mod, campaign)
    regions_now = mod.campaign_file(campaign, "map_regions.tga")
    o_regions = old(mod, st, regions_now)
    o_heights = old(mod, st, os.path.join(base, "map_heights.tga"))
    o_feats = old(mod, st, os.path.join(base, "map_features.tga"))
    edges = st.get("edges", U.EDGE_DEFAULT)
    lands = _lands(mod, campaign, o_regions, o_heights)
    coast = U.coast_mask(o_regions, lands, natural=True, edges=edges)
    on_rivers = None
    if os.path.isfile(o_feats):
        _, rivers = U.features_scaled(o_feats, coast, natural=True)
        on_rivers = (U.river_tiles(o_feats), rivers) if rivers else None
    info = {}
    plan.binary(regions_now, U.regions_scaled(o_regions, lands, coast, (), info, natural=True, rivers=on_rivers,
                                              edges=edges))
    plan.note(None, "map_regions.tga: the coast and the borders between regions %s, a border along a river still "
                    "on the river, every region in as many pieces as before" % U.edge_words(edges))
    warn = ["the port at %d, %d: %s (now at %d, %d)" % (x, y, why, spot[0], spot[1])
            for (x, y), spot, why in info.get("moved_ports", [])]
    hmask = None
    if os.path.isfile(o_heights):
        hmask = U.heights_from_tiles(info["land"], U._agreement(o_regions, o_heights, lands),
                                     U.heights_mask(o_heights, True))
    from .terrain import SEA
    g = os.path.join(base, "map_ground_types.tga")
    if os.path.isfile(g) and hmask is not None:
        plan.binary(g, U.ground_scaled(old(mod, st, g), hmask, SEA, natural=True, edges=edges))
        plan.note(None, "map_ground_types.tga: every tile the ground of the old tile it lies in, %s edges, the sea "
                        "ground under the new coast" % U.edge_words(edges))
    c = os.path.join(base, "map_climates.tga")
    if os.path.isfile(c):
        plan.binary(c, U.climates_scaled(old(mod, st, c), natural=True, edges=edges))
        plan.note(None, "map_climates.tga: %s edges" % U.edge_words(edges))
    return warn


def check_smooth(mod, campaign, st):
    """Every town with its own region all round it."""
    img = mod.region_map(campaign)
    by = {v["colour"]: k for k, v in mod.regions(campaign).items()}
    bad = []
    for r, (x, y) in mod.city_tiles(campaign).items():
        round_ = [img.get(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and
                  0 <= x + dx < img.width and 0 <= y + dy < img.height]
        if any(c in by and by[c] != r for c in round_):
            bad.append(r)
    return ["%d town(s) touch another region's land: %s" % (len(bad), ", ".join(bad[:6]))] if bad else []


# ---------------------------------------------------------------- 3 heights
def _towns_now(mod, campaign):
    return {(x, y) for x, y in mod.city_tiles(campaign).values()}


def step_heights(plan, campaign, st):
    mod = plan.mod
    base = _base(mod, campaign)
    vertical = st.get("vertical", U.FACTOR)
    regions_now = mod.campaign_file(campaign, "map_regions.tga")
    hpath = os.path.join(base, "map_heights.tga")
    o_regions, o_heights = old(mod, st, regions_now), old(mod, st, hpath)
    if not os.path.isfile(o_heights):
        return ["no map_heights.tga - nothing to do in this step"]
    lands = _lands(mod, campaign, o_regions, o_heights)
    land = _land_now(regions_now, lands)          # the coast as map_regions has it now (fixes since step 2 count)
    hmask = U.heights_from_tiles(land, U._agreement(o_regions, o_heights, lands), U.heights_mask(o_heights, True))
    o_feats = old(mod, st, os.path.join(base, "map_features.tga"))
    rivers = U.features_scaled(o_feats, land, natural=True)[1] if os.path.isfile(o_feats) else ()
    volcanoes = []
    if os.path.isfile(o_feats):
        _, fw, fh, _, _, fat = U._pixels(o_feats)
        volcanoes = [U.new_xy(x, y) for y in range(fh) for x in range(fw) if fat(x, y) == (255, 0, 0)]
    o_ground = old(mod, st, os.path.join(base, "map_ground_types.tga"))
    towns = _towns_now(mod, campaign)
    data = U.smooth_scaled(o_heights, "corners", sea=True, mask=hmask, natural=True, rivers=rivers, towns=towns,
                           vertical=vertical, ground=o_ground, volcanoes=volcanoes)
    plan.binary(hpath, data)
    plan.note(None, "map_heights.tga: the relief the natural way over the coast map_regions has now - every sea "
                    "point under the water, no land point under it, the old map's own shore, no slope steeper than "
                    "the old map's steepest")
    hgt = os.path.join(base, "map_heights.hgt")
    o_hgt = old(mod, st, hgt)
    if os.path.isfile(o_hgt) and U.hgt_usable(o_hgt, o_heights):
        plan.binary(hgt, U.hgt_scaled(o_hgt, o_heights, hmask, vertical, natural=True, rivers=rivers, towns=towns,
                                      ground=o_ground, volcanoes=volcanoes))
        plan.note(None, "map_heights.hgt: the same relief (the game reads it instead of the picture)")
    elif os.path.isfile(hgt):
        from .terrain import max_land_height, min_sea_height
        top, low = max_land_height(mod, campaign) * vertical, min_sea_height(mod, campaign) * vertical
        plan.binary(hgt, U.hgt_from_picture(data, top, low))
    from .terrain import SEA
    g = os.path.join(base, "map_ground_types.tga")
    if os.path.isfile(g):
        ground = U.ground_scaled(o_ground, hmask, SEA, natural=True, edges=st.get("edges", U.EDGE_DEFAULT))
        ground = U.mountains_by_height(ground, data, o_ground, o_heights)
        plan.binary(g, U.shallow_coast(ground))
        plan.note(None, "map_ground_types.tga: the sea ground under the heights' sea, mountains only where the land "
                        "stands high, shallow sea along the coast")
    t = os.path.join(base, "descr_terrain.txt")
    if os.path.isfile(t) and vertical != 1:
        f = plan.edit(t)
        for i in range(len(f.raw)):
            m = re.match(r"^(\s*(?:max_land_height|min_sea_height)\s+)(-?[\d.]+)(.*)$", f.text(i))
            if m:
                v = float(m.group(2)) * vertical
                dec = len(m.group(2).partition(".")[2])
                f.raw[i] = f.make(m.group(1) + ("%.*f" % (dec, v) if dec else str(int(round(v)))) + m.group(3))
        plan.note(f, "the hills, mountains and sea floor x %g: the land is 3 x wider, the slopes stay as they were"
                  % vertical)
    return []


def check_heights(mod, campaign, st):
    """Every tile's middle point: under the water on a sea tile, above it on a land tile."""
    base = _base(mod, campaign)
    hpath = os.path.join(base, "map_heights.tga")
    if not os.path.isfile(hpath):
        return []
    _, hw, hh, _, _, hat = U._pixels(hpath)
    sea = U._heights_sea(hat)
    regions = mod.campaign_file(campaign, "map_regions.tga")
    lands = _lands(mod, campaign, regions, hpath)
    land = _land_now(regions, lands)
    dry = wet = 0
    for y in range(land.H):
        for x in range(land.W):
            if 2 * x + 1 < hw and 2 * y + 1 < hh:
                s = sea(2 * x + 1, 2 * y + 1)
                if land.b[y * land.W + x] and s:
                    wet += 1
                elif not land.b[y * land.W + x] and not s:
                    dry += 1
    out = []
    if wet:
        out.append("%d land tile(s) whose middle point is under the water (a hole in the land)" % wet)
    if dry:
        out.append("%d sea tile(s) whose middle point stands above the water (a saw tooth on the coast)" % dry)
    return out


# ---------------------------------------------------------------- 4 rivers
def step_rivers(plan, campaign, st):
    mod = plan.mod
    base = _base(mod, campaign)
    feats = os.path.join(base, "map_features.tga")
    o_feats = old(mod, st, feats)
    if not os.path.isfile(o_feats):
        return ["no map_features.tga - no rivers to draw"]
    regions_now = mod.campaign_file(campaign, "map_regions.tga")
    hpath = os.path.join(base, "map_heights.tga")
    lands = _lands(mod, campaign, old(mod, st, regions_now), old(mod, st, hpath))
    land = _land_now(regions_now, lands)
    data, _ = U.features_scaled(o_feats, land, natural=True)
    g = os.path.join(base, "map_ground_types.tga")
    if os.path.isfile(hpath) and os.path.isfile(g):
        with open(hpath, "rb") as fh:
            hdata = fh.read()
        with open(g, "rb") as fh:
            gdata = fh.read()
        data = U.rivers_off_the_water(data, hdata, gdata)
    plan.binary(feats, data)
    plan.note(None, "map_features.tga: rivers drawn naturally over the land as it is now - one pixel wide, bends "
                    "rounded, none on the water, each ending on the last land tile at the water; no cliffs (paint "
                    "them with the Terrain tab)")
    return []


def check_rivers(mod, campaign, st):
    """No river pixel on water; no 2 x 2 block of river (2 pixels wide)."""
    base = _base(mod, campaign)
    feats = os.path.join(base, "map_features.tga")
    if not os.path.isfile(feats):
        return []
    _, w, h, _, _, at = U._pixels(feats)
    regions = mod.campaign_file(campaign, "map_regions.tga")
    land = _land_now(regions, _lands(mod, campaign, regions, os.path.join(base, "map_heights.tga")))
    river = {(x, y) for y in range(h) for x in range(w) if at(x, y) in U.RIVERY}
    wet = [p for p in river if not land.get(p, True)]
    wide = [p for p in river if (p[0] + 1, p[1]) in river and (p[0], p[1] + 1) in river and
            (p[0] + 1, p[1] + 1) in river]
    out = []
    if wet:
        out.append("%d river pixel(s) on the water, e.g. %d, %d" % (len(wet), wet[0][0], wet[0][1]))
    if wide:
        out.append("%d place(s) where a river is 2 pixels wide (the game crashes), e.g. %d, %d" % (
            len(wide), wide[0][0], wide[0][1]))
    return out


# ---------------------------------------------------------------- 5 objects
def _nearest(fits, xy, reach=6):
    x, y = xy
    for d in range(1, reach + 1):
        ring = sorted(((dx, dy) for dx in range(-d, d + 1) for dy in range(-d, d + 1) if max(abs(dx), abs(dy)) == d),
                      key=lambda t: abs(t[0]) + abs(t[1]))
        for dx, dy in ring:
            if fits((x + dx, y + dy)):
                return x + dx, y + dy
    return None


def step_objects(plan, campaign, st):
    """Armies, agents, fleets and resources on a tile they may not stand on moved to the nearest one that fits."""
    mod = plan.mod
    from .strat import Strat
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    f = plan.edit(sp)
    s = Strat(mod.load(sp))
    warn, moved = [], 0
    armies = set()
    for fb in s.factions:
        for c in fb.characters:
            lines = s.lines[c.start:c.end]
            army = any(tokens(l)[:1] == ["army"] for l in lines)
            if army and c.xy:
                armies.add(tuple(c.xy))
    for fb in s.factions:
        for c in fb.characters:
            if not c.xy:
                continue
            lines = s.lines[c.start:c.end]
            army = any(tokens(l)[:1] == ["army"] for l in lines)
            kind = "admiral" if c.kind == "admiral" else c.kind
            if not mod.tile_problem(campaign, tuple(c.xy), kind, army, armies - {tuple(c.xy)}):
                continue
            to = _nearest(lambda p: not mod.tile_problem(campaign, p, kind, army, armies), tuple(c.xy))
            if to is None:
                warn.append("%s (%s) at %d, %d stands where he may not and no tile near fits - move him by hand" %
                            (c.name, fb.name, c.xy[0], c.xy[1]))
                continue
            line = f.text(c.start)
            new = U.RE_CHAR_XY.sub(lambda m: "%s%d%s%d" % (m.group(1), to[0], m.group(3), to[1]), line, count=1)
            if new != line:
                f.set(c.start, new)
                armies.discard(tuple(c.xy))
                if army:
                    armies.add(to)
                moved += 1
    if moved:
        plan.note(f, "%d army / agent / fleet place(s) moved to the nearest tile they may stand on" % moved)
    from . import resources as R
    k = 0
    for res in R.read(mod.load(sp)):
        if R.problem(mod, campaign, res.xy):
            to = _nearest(lambda p: not R.problem(mod, campaign, p), res.xy)
            if to:
                line = f.text(res.line)
                new = U._move_line(line, (U.RE_RESOURCE,), lambda x, y, t=to: t)[0]
                if new != line:
                    f.set(res.line, new)
                    k += 1
    if k:
        plan.note(f, "%d resource(s) moved to the nearest tile they may stand on" % k)
    return warn


def check_objects(mod, campaign, st):
    from .check import town_ring_problems
    return [m for serious, m in town_ring_problems(mod, campaign) if serious][:8]


RUN = {"grid": (step_grid, check_grid), "smoothing": (step_smooth, check_smooth),
       "heights": (step_heights, check_heights), "rivers": (step_rivers, check_rivers),
       "objects": (step_objects, check_objects)}


def plan_step(mod, campaign, k, st, tune=None):
    """The plan of step k (0..4) - nothing written. tune: the x3 window's values (upscale.TUNES)."""
    saved = dict(U.TUNE)
    try:
        for key, v in (tune or {}).items():
            if key in U.TUNES:
                lo, hi = U.TUNES[key][2], U.TUNES[key][3]
                U.TUNE[key] = min(max(float(v), lo), hi)
        st["vertical"] = U.TUNE["vertical"]
        st["edges"] = U.TUNE["edges"]
        plan = Plan(mod, "map", "%s_step%d" % (WORK, k + 1), {})
        warn = RUN[STEPS[k][0]][0](plan, campaign, st)
        return plan, warn
    finally:
        U.TUNE.clear()
        U.TUNE.update(saved)


def check_step(mod, campaign, k, st):
    """What the check after step k found (empty: fine)."""
    return RUN[STEPS[k][0]][1](mod, campaign, st)
