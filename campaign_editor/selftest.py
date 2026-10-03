"""The author's stress test (Tools > Test mod - every feature): a new mod folder made beside the loaded mod (or game)
with New mod folder, and every feature of the editor applied to it through the same code the buttons use - one
write (with its backup) per step. After each step Check mod files runs again, so a step that leaves the mod with a
problem is caught where it happened. The report (<mod>/CE_Test_report.txt) says per step what was written and what
to look at in the game; then the mod is started in the game and its log read, so every feature is tried in the game
in one go. Not for modders: it makes a mod nobody wants to play.

Both games: the factions it works on are picked from the mod itself (the first playable factions with towns), so it
runs on vanilla and on any mod."""

import os
import random
import time
import traceback

from .plan import Plan

NAME = "CE_Test"
LOGO_SIZE = 256


class Skip(Exception):
    """A step that cannot run on this mod (said in the report, not a failure)."""


class Ctx:
    def __init__(self, data, campaign, work):
        from .moddata import ModData
        self.data, self.campaign, self.work = data, campaign, work
        mod = ModData(data)
        self.m2 = _is_m2(mod)
        self.rng = random.Random(7)
        s = _strat(mod, campaign)
        owners = s.owners()
        play = [n for _, n in s.playable["items"]] if getattr(s, "playable", None) else []
        with_towns = [f for f in play if f != "slave" and any(o == f for o in owners.values())]
        if len(with_towns) < 3:
            with_towns += [fb.name for fb in s.factions if fb.name not in with_towns and fb.name != "slave" and
                           any(o == fb.name for o in owners.values())]
        if len(with_towns) < 3:
            raise ValueError("the test needs three factions with towns in %s" % campaign)
        self.template, self.edited, self.other = with_towns[:3]
        taken = {n.lower() for n, _ in mod.factions()}
        self.new = _free_name("ce_test", taken)
        self.later = _free_name("ce_test_later", taken | {self.new})
        self.split = _free_name("ce_test_split", taken | {self.new, self.later})
        # a faction of another culture than the template: its units and buildings are surely not the clone's
        cult = dict(mod.factions())
        self.foreign = next((n for n, cu in mod.factions() if n != "slave" and cu != cult.get(self.template) and
                             n not in (self.new, self.later, self.split)), self.other)
        self.logo = None

    def mod(self):
        from .moddata import ModData
        return ModData(self.data)


def _is_m2(mod):
    from .packs import game_kind
    return game_kind(mod) == "medieval2"


def _free_name(base, taken):
    k, name = 1, base
    while name in taken:
        k += 1
        name = "%s%d" % (base, k)
    return name


def _strat(mod, campaign):
    from .strat import Strat
    return Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt")))


# ---------------------------------------------------------------------------
# helpers on the campaign
def towns_of(c, mod, faction):
    return [r for r, o in _strat(mod, c.campaign).owners().items() if o == faction]


def near_rebels(c, mod, faction, n=2):
    tiles = mod.city_tiles(c.campaign)
    mine = [tiles[r] for r in towns_of(c, mod, faction) if tiles.get(r)]
    reb = [r for r in towns_of(c, mod, "slave") if tiles.get(r)]
    if not mine:
        return reb[:n]
    cx, cy = mine[0]
    return sorted(reb, key=lambda r: abs(tiles[r][0] - cx) + abs(tiles[r][1] - cy))[:n]


def taken_tiles(c, mod):
    s = _strat(mod, c.campaign)
    return {ch.xy for fb in s.factions for ch in fb.characters if ch.xy} | set(mod.city_tiles(c.campaign).values())


def free_land(c, mod, xy, kind="general", army=True, skip=()):
    taken = taken_tiles(c, mod) | set(skip)
    for d in range(2, 14):
        for dx in range(-d, d + 1):
            for dy in (-d, d):
                p = (xy[0] + dx, xy[1] + dy)
                if p not in taken and not mod.tile_problem(c.campaign, p, kind, army, taken):
                    return p
    return None


def unit_names(mod, faction, n=3, ships=False):
    from .units import faction_units
    return [u.type for u in faction_units(mod, faction, ships=ships, mercs=ships)][:n]


def free_names(c, mod, faction, n=3):
    from .strat import faction_names, first_names
    pool = first_names(mod.name_pool(faction), "general") or ["Testus"]
    used = set(faction_names(_strat(mod, c.campaign), faction))
    free = [x for x in pool if x not in used] or pool
    return (free * n)[:n]


def logo(c):
    """A plain picture to put in (a green disc with a yellow ring) - made once, beside the report."""
    if c.logo is None:
        from PIL import Image, ImageDraw
        im = Image.new("RGBA", (LOGO_SIZE, LOGO_SIZE), (0, 0, 0, 0))
        ImageDraw.Draw(im).ellipse((20, 20, 236, 236), fill=(40, 140, 60, 255), outline=(240, 220, 40, 255),
                                   width=12)
        c.logo = os.path.join(c.work, "ce_test_logo.png")
        im.save(c.logo)
    return c.logo


# ---------------------------------------------------------------------------
# the steps: (title, what to look at in the game, fn(c, mod) -> Plan | [Plan] | None)
STEPS = []


def step(title, see=""):
    def wrap(fn):
        STEPS.append((title, see, fn))
        return fn
    return wrap


@step("New faction: a clone of {template} with two rebel towns, a leader, an army, a spy and a fleet",
      "{new} is on the faction-select screen and plays: its two towns, its leader's army, the spy and fleet beside "
      "its capital; {template} as before")
def s_new_faction(c, mod):
    from .build import build
    regions = near_rebels(c, mod, c.template, 2)
    if not regions:
        raise Skip("no rebel town to start in")
    cap = mod.city_tiles(c.campaign)[regions[0]]
    names = free_names(c, mod, c.template, 4)
    land = free_land(c, mod, cap)
    chars = [{"kind": "spy", "name": names[2], "age": 25, "units": [], "xy": cap}]
    if land:
        chars.insert(0, {"kind": "army", "name": names[1], "age": 30, "units": unit_names(mod, c.template, 3),
                         "xy": land})
    ships = unit_names(mod, c.template, 1, ships=True)
    sea = None
    for d in range(1, 14):
        for dx in range(-d, d + 1):
            for dy in (-d, d):
                p = (cap[0] + dx, cap[1] + dy)
                if sea is None and ships and not mod.tile_problem(c.campaign, p, "admiral", True, set()):
                    sea = p
        if sea:
            break
    if sea:
        chars.append({"kind": "fleet", "name": names[3], "age": 30, "units": ships, "xy": sea})
    return build(mod, c.campaign, c.template, c.new, {
        "display_name": "Test Kingdom", "short_name": "Testland", "adjective": "Testish",
        "description": "A faction made by the editor's test mod.",
        "primary_colour": (40, 140, 60), "secondary_colour": (240, 220, 40), "raise_faction_limit": True,
        "start": {"regions": regions, "leader": {"name": names[0], "age": 40}, "characters": chars}})


@step("A faction that comes later: a clone of {edited}, dead at the start, woken by an event in {edited}'s town",
      "{later} is not on the map at the start")
def s_later(c, mod):
    from .build import build
    from .events import turn_date
    return build(mod, c.campaign, c.edited, c.later, {
        "display_name": "Rising Test", "short_name": "Rising", "adjective": "Rising", "raise_faction_limit": True,
        "start": {"way": "event", "date": turn_date(mod, c.campaign, 6), "region": towns_of(c, mod, c.edited)[0],
                  "re_emergent": True, "denari": 3000, "regions": [], "leader": None, "playable": False}})


@step("...its way changed to: the shadow of {edited}, may come back",
      "when {edited} has a revolt, {later} takes the rebel towns")
def s_later_way(c, mod):
    from . import emergence as E
    plan = Plan(mod, "later", c.later, {})
    E.apply(plan, c.campaign, c.later, "shadow", of=c.edited, re_emergent=True)
    return plan


@step("A faction that splits off {other} in a revolt: a clone of {other}, dead at the start",
      "{split} is not on the map at the start; when towns of {other} revolt they go to {split}")
def s_split(c, mod):
    from .build import build
    return build(mod, c.campaign, c.other, c.split, {
        "display_name": "Split Test", "short_name": "Split", "adjective": "Splitting", "raise_faction_limit": True,
        "start": {"way": "revolt", "of": c.other, "denari": 2000, "regions": [], "leader": None,
                  "playable": False}})


@step("Edit faction {edited}: names, description, colours, money, a garrison, a rebel town taken",
      "{edited} has the new name and colours (purple / white), 12345 money, the new garrison in its capital and the "
      "rebel town next to it")
def s_edit(c, mod):
    from .edit import edit, read_faction
    now = read_faction(mod, c.campaign, c.edited)
    town = now["regions"][0]
    return edit(mod, c.campaign, c.edited, {
        "display_name": "Test Realm", "adjective": now["adjective"], "description": "Edited by the test mod.",
        "primary_colour": (150, 30, 160), "secondary_colour": (250, 250, 250), "denari": 12345,
        "garrisons": {town: unit_names(mod, c.edited, 2)}, "take": near_rebels(c, mod, c.edited, 1),
        "capital": town})


@step("Armies and agents placed by hand for {edited}",
      "a new army and a diplomat stand next to {edited}'s capital")
def s_chars(c, mod):
    from .edit import edit, read_faction
    cap = mod.city_tiles(c.campaign)[read_faction(mod, c.campaign, c.edited)["regions"][0]]
    names = free_names(c, mod, c.edited, 2)
    a = free_land(c, mod, cap)
    b = free_land(c, mod, cap, "diplomat", False, skip={a})
    chars = []
    if a:
        chars.append({"kind": "army", "name": names[0], "age": 28, "units": unit_names(mod, c.edited, 3), "xy": a})
    if b:
        chars.append({"kind": "diplomat", "name": names[1], "age": 35, "units": [], "xy": b})
    if not chars:
        raise Skip("no free land near the capital")
    return edit(mod, c.campaign, c.edited, {"characters": chars})


@step("Diplomacy: {edited} and {new} like each other, {edited} hates {other}",
      "the diplomacy screen at the start")
def s_diplomacy(c, mod):
    from .edit import edit
    return edit(mod, c.campaign, c.edited, {"relations": [
        {"kind": "core_attitudes", "from": "me", "to": c.new, "value": 100},
        {"kind": "core_attitudes", "from": c.new, "to": "me", "value": 100},
        {"kind": "faction_relationships", "from": "me", "to": c.other, "value": -600}]})


@step("Victory conditions of {edited}: hold its capital, take 20 regions", "the victory conditions screen")
def s_victory(c, mod):
    from . import wincond
    from .edit import edit, read_faction
    cond = wincond.read(mod, c.campaign).get(c.edited)
    if not cond:
        raise Skip("no victory conditions file / entry")
    cond["long"]["hold"] = read_faction(mod, c.campaign, c.edited)["regions"][:1]
    cond["long"]["take"] = 20
    return edit(mod, c.campaign, c.edited, {"victory": cond})


@step("Resources on the map: one moved, one added, one removed", "the resource signs on the campaign map")
def s_resources(c, mod):
    from . import resources as R
    from .edit import edit
    rs = R.read(mod.load(mod.campaign_file(c.campaign, "descr_strat.txt")))
    types = list(R.types(mod))
    if len(rs) < 3 or not types:
        raise Skip("too few resources")
    taken = {r.xy for r in rs}
    pick = rs[len(rs) // 2]
    to = add = None
    for d in range(1, 8):
        for dx in range(-d, d + 1):
            p = (pick.xy[0] + dx, pick.xy[1] + d)
            if to is None and p not in taken and not R.problem(mod, c.campaign, p, taken):
                to = p
    for r in rs[::7]:
        p = (r.xy[0] + 3, r.xy[1] + 2)
        if add is None and p not in taken and p != to and not R.problem(mod, c.campaign, p, taken | {to}):
            add = p
    ch = {"moved": {str(rs.index(pick)): list(to)} if to else {}, "removed": [len(rs) - 1],
          "added": [{"type": types[0], "xy": list(add)}] if add else []}
    return edit(mod, c.campaign, c.edited, {"resources": ch})


@step("Forts, watchtowers, wonders: a fort, a watchtower (and on Rome a wonder) added near {edited}'s capital, an "
      "old one moved", "the new fort, watchtower and wonder beside the capital")
def s_forts(c, mod):
    from . import forts as FT
    from .edit import edit, read_faction
    now = FT.read(mod, c.campaign)
    cap = mod.city_tiles(c.campaign)[read_faction(mod, c.campaign, c.edited)["regions"][0]]
    taken = {f.xy for f in now} | taken_tiles(c, mod)
    spots = []
    for d in range(2, 9):
        for dx in range(-d, d + 1):
            for dy in (-d, d):
                p = (cap[0] + dx, cap[1] + dy)
                if len(spots) < 3 and p not in taken and not FT.problem(mod, c.campaign, p, taken | set(spots)):
                    spots.append(p)
    if len(spots) < 3:
        raise Skip("no free land for a fort")
    ch = {"added": [{"kind": "fort", "xy": list(spots[0])}, {"kind": "watchtower", "xy": list(spots[1])}]}
    wonders = FT.landmark_types(mod)                  # Rome: a wonder put on the map too
    if wonders:
        ch["added"].append({"kind": FT.LANDMARK, "type": wonders[0], "xy": list(spots[2])})
    if now:
        f0 = now[0]
        for d in range(1, 5):
            p = (f0.xy[0] + d, f0.xy[1])
            if "moved" not in ch and p not in taken and p not in spots and \
                    not FT.problem(mod, c.campaign, p, taken | set(spots)):
                ch["moved"] = {str(f0.line): list(p)}
    return edit(mod, c.campaign, c.edited, {"resources": {"forts": ch}})


@step("Town window: a rebel town given to {new}, its population set to 2600 (the level follows the people)",
      "the town is {new}'s, big enough for 2600 people")
def s_town(c, mod):
    from . import masstown as MT
    region = towns_of(c, mod, "slave")[-1]
    plan = Plan(mod, "town", region, {})
    MT.apply(plan, c.campaign, {"population": {region: 2600}, "owners": {region: c.new}, "level_follows": True})
    return plan


@step("Buildings and garrisons for many towns: a building in {edited}'s towns, random garrisons",
      "the building in those towns; the bigger garrisons")
def s_masstown(c, mod):
    from . import masstown as MT
    towns = MT.towns(mod, c.campaign)
    known = MT.known_buildings(mod)
    mine = [t for t in towns if t["owner"] == c.edited]
    build = {}
    for chain, b in known.items():
        if MT.is_core(chain) or not b.levels:
            continue
        lv = b.levels[0].name
        fits = [t for t in mine if MT.building_fit(known, t, chain, lv)[0] in ("add", "upgrade", "set")]
        if len(fits) >= 2:
            build = {t["region"]: (chain, lv) for t in fits[:3]}
            break
    pool = MT.garrison_pool(mod, c.edited)
    gar = {}
    for t in mine[:2]:
        g = MT.random_garrison(MT.town_pool(mod, t, pool), 2, 4, 2000, c.rng)
        if g:
            gar[t["region"]] = g
    plan = Plan(mod, "towns", "towns", {})
    MT.apply(plan, c.campaign, {"build": build, "garrisons": gar, "add_units": True})
    return plan


@step("Map: an army placed for another faction ({other})", "a new army next to {other}'s town")
def s_map(c, mod):
    from .edit import first_units, map_changes
    region = towns_of(c, mod, c.other)[0]
    free = mod.free_tile(c.campaign, region, taken_tiles(c, mod))
    if not free:
        raise Skip("no free tile")
    units = first_units(mod, c.campaign, c.other, "army", free)
    plan = Plan(mod, "map", "map", {})
    map_changes(plan, c.campaign, {"characters": {c.other: [
        {"kind": "army", "name": free_names(c, mod, c.other, 1)[0], "age": 30, "units": units, "xy": free}]}})
    return plan


@step("Map: a town of {edited} moved one tile", "the town one tile from where it stood")
def s_move_town(c, mod):
    from . import mapedit as ME
    from .edit import edit, read_faction
    region = read_faction(mod, c.campaign, c.edited)["regions"][-1]
    x, y = mod.city_tiles(c.campaign)[region]
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (2, 0), (0, 2)):
        to = (x + dx, y + dy)
        if not ME.place_problem(mod, c.campaign, "city", region, to):
            return edit(mod, c.campaign, c.edited, {"places": [{"what": "city", "region": region, "to": to}]})
    raise Skip("no tile next to %s takes the town" % region)


@step("New region carved out of a rebel region: CE_Newland with the town CE_Newtown, {new}'s",
      "a new region on the map with its own town")
def s_region(c, mod):
    from . import regionedit as RE
    from .edit import edit
    info = mod.regions(c.campaign)
    img = mod.region_map(c.campaign)
    tiles = mod.city_tiles(c.campaign)
    for donor in [r for r in towns_of(c, mod, "slave") if r in info][::-1]:
        col = info[donor]["colour"]
        tx, ty = tiles[donor]
        for cx in range(3, img.width - 3, 2):
            for cy in range(3, img.height - 3, 2):
                if abs(cx - tx) + abs(cy - ty) < 6:
                    continue
                if not all(img.get(px, py) == col for px in range(cx - 2, cx + 3) for py in range(cy - 2, cy + 3)):
                    continue
                painted = {(cx + dx, cy + dy): "CE_Newland" for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
                new = {"name": "CE_Newland", "settlement": "CE_Newtown", "creator": c.new,
                       "rebels": info[donor]["rebels"], "resources": [], "city": (cx, cy), "owner": c.new,
                       "level": "village"}
                faults, _ = RE.region_problems(mod, c.campaign, painted, [new])
                if faults:
                    continue
                return edit(mod, c.campaign, c.new, {"regions": {"painted": painted, "new": [new]}})
    raise Skip("no 5 x 5 block of one rebel region far from its town")


@step("Rename a rebel region and its town everywhere", "the new names on the map and in the lists")
def s_rename(c, mod):
    from . import regionrename as RR
    region = towns_of(c, mod, "slave")[0]
    town = mod.regions(c.campaign)[region]["settlement"]
    plan = Plan(mod, "rename", region)
    RR.rename(plan, c.campaign, region, region + "_CE", town + "_CE")
    return plan


@step("Settlement names by culture (REX / M2EX script): a town of {edited} named otherwise under another culture",
      "the town's name changes when a faction of the other culture takes it")
def s_culture_names(c, mod):
    from . import culturenames as CN
    from .regionedit import apply_opts
    town = mod.regions(c.campaign)[towns_of(c, mod, c.edited)[0]]["settlement"]
    cults = CN.cultures(mod)
    if len(cults) < 2:
        raise Skip("fewer than two cultures")
    plan = Plan(mod, None, "map")
    apply_opts(plan, c.campaign, {"culture_names": {town: {"*": town, cults[-1]: town + "_CE"}}})
    return plan


@step("Terrain editor: ground painted and hills sprayed near {edited}'s capital",
      "the painted ground and the hills near the capital")
def s_terrain(c, mod):
    from . import terrain as T
    from .edit import read_faction
    from .tga import read_tga
    cap = mod.city_tiles(c.campaign)[read_faction(mod, c.campaign, c.edited)["regions"][0]]
    brushes = T.ground_brushes("m2tw" if c.m2 else "rome")
    colour = list(brushes.values())[0] if isinstance(brushes, dict) else brushes[0][1]
    ground = {}
    towns = set(mod.city_tiles(c.campaign).values())
    for d in range(2, 10):                      # nine land tiles near the capital
        for dx in range(-d, d + 1):
            for dy in (-d, d):
                p = (cap[0] + dx, cap[1] + dy)
                if len(ground) < 9 and p not in towns and not mod.is_sea(c.campaign, p):
                    ground[p] = tuple(colour)
    heights = {}
    hp = mod.campaign_file(c.campaign, "map_heights.tga")
    if hp and ground:
        img = read_tga(hp)
        x, y = sorted(ground)[len(ground) // 2]
        heights = T.height_spray(img, (2 * x + 1, 2 * y + 1), 3.5, "raise", 8, {})
    if not ground and not heights:
        raise Skip("sea all round the capital")
    plan = Plan(mod, "terrain", "terrain")
    T.apply(plan, c.campaign, ground=ground, heights=heights)
    return plan


@step("Land and sea: a sea tile on the coast made land", "a new bit of coast")
def s_coast(c, mod):
    from collections import Counter
    from . import terrain as T
    from . import resources as RS
    from .mapdata import CampaignMap
    from .tga import read_tga
    cmap = CampaignMap(mod, c.campaign)
    s = _strat(mod, c.campaign)
    standing = set(cmap.cities.values()) | set(cmap.ports.values()) | s.taken_tiles() | \
        {r.xy for r in RS.read(mod.load(mod.campaign_file(c.campaign, "descr_strat.txt")))}
    counts = Counter(r for y in range(cmap.h) for x in range(cmap.w) for r in [cmap.region_at(x, y)] if r)
    hp = mod.campaign_file(c.campaign, "map_heights.tga")
    heights = read_tga(hp) if hp else None
    sea = T.sea_colour(mod.region_map(c.campaign), [v["colour"] for v in cmap.info.values()])
    for y in range(2, cmap.h - 2, 3):
        for x in range(2, cmap.w - 2, 3):
            if not cmap.is_sea(x, y) or \
                    sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if not cmap.is_sea(x + dx, y + dy)) < 2:
                continue
            if T.coast_problem(cmap, (x, y), True, standing, {}, counts, cmap.ports):
                continue
            region = T.nearest_region(cmap, (x, y))
            if not region:
                continue
            px = T.coast_pixels(cmap, (x, y), True, cmap.info[region]["colour"], heights, sea)
            plan = Plan(mod, "terrain", "terrain")
            T.apply(plan, c.campaign, coast={"tiles": {(x, y): "land"}, "regions": px["regions"],
                                            "ground": px["ground"], "heights": px["heights"]})
            return plan
    raise Skip("no sea tile to fill")


@step("Family: a new son for {edited}'s leader", "the family tree shows the boy")
def s_family(c, mod):
    from . import family as FM
    from .edit import edit
    fam = FM.read(mod.load(mod.campaign_file(c.campaign, "descr_strat.txt")), c.edited)
    tree = [list(x) for x in fam["tree"]]
    if not tree:
        raise Skip("%s has no family tree" % c.edited)
    head = tree[0]
    surname = head[0].split(" ", 1)[1] if " " in head[0] else ""
    from .strat import first_names
    people = {p.name for p in fam["people"]} | {n for t in tree for n in [t[0], t[1]] + list(t[2])}
    son = next(((f + " " + surname).strip() for f in first_names(mod.name_pool(c.edited), "general") or []
                if (f + " " + surname).strip() not in people), None)
    if son is None:
        raise Skip("no free name for a son")
    head[2] = list(head[2]) + [son]
    return edit(mod, c.campaign, c.edited, {"family": {"new": [{"name": son, "sex": "male", "age": 3}],
                                                        "tree": tree}})


@step("Traits and retinue: a new trait copied from an old one", "a general can get CETestTrait")
def s_traits(c, mod):
    from . import traitsedit as TE
    path = TE.file_of(mod, "trait")
    if not path:
        raise Skip("no traits file")
    src = next(iter(TE.blocks(mod.load(path), "trait")))
    plan = Plan(mod, "t", "t", {})
    TE.apply(plan, "trait", {"new": [[src, "CETestTrait"]]})
    return plan


@step("Religions (Medieval II): a new religion in every file, a region's shares changed",
      "'Test Faith' in the region's religion bar")
def s_religion(c, mod):
    from . import religions as RL
    from .regionedit import apply_opts
    names = RL.names(mod)
    if not names:
        raise Skip("Rome has no religions (BI's beliefs are not written here)")
    spec = {"name": "ce_faith", "shown": "Test Faith", "pip_from": names[0], "picture": None, "factions": [c.new]}
    region = (towns_of(c, mod, c.new) or towns_of(c, mod, c.edited))[0]
    plan = Plan(mod, None, "religion")
    apply_opts(plan, c.campaign, {"new_religions": [spec],
                                  "religions": {region: dict({n: 0 for n in names}, **{names[0]: 60, "ce_faith": 40})}})
    return plan


@step("Roster: {edited} gets a unit and a building level it lacked", "the unit in its recruitment list")
def s_roster(c, mod):
    from . import roster as R
    from .edit import edit
    r = R.roster(mod, c.edited)
    ch = {}
    u = next((x["type"] for x in r["units"] if not x["has"]), None)
    b = next(("building:%s:%s" % (x["chain"], x["level"]) for x in r["buildings"] if not x["has"]), None)
    if u:
        ch["unit:" + u] = True
    if b:
        ch[b] = True
    if not ch:
        raise Skip("%s has everything already" % c.edited)
    return edit(mod, c.campaign, c.edited, {"roster": ch})


@step("Units and buildings of another faction moved over: {new} gets units and building levels of {foreign}",
      "{new} recruits {foreign}'s units in its towns (with cards of its own) and builds {foreign}'s buildings")
def s_roster_other(c, mod):
    from . import roster as R
    from .edit import edit
    theirs, mine = R.roster(mod, c.foreign), R.roster(mod, c.new)
    has = {u["type"] for u in mine["units"] if u["has"]}
    units = [u["type"] for u in sorted(theirs["units"], key=lambda u: u["category"] not in ("infantry", "cavalry"))
             if u["has"] and u["type"] not in has and u["recruit_any"]][:3]
    has_b = {(b["chain"], b["level"]) for b in mine["buildings"] if b["has"]}
    blds = [(b["chain"], b["level"]) for b in theirs["buildings"] if b["has"] and (b["chain"], b["level"]) not in has_b]
    ch = {"unit:" + u: True for u in units}
    ch.update({"building:%s:%s" % b: True for b in blds[:2]})
    if not ch:
        raise Skip("%s has every unit and building of %s already" % (c.new, c.foreign))
    return edit(mod, c.campaign, c.new, {"roster": ch})


@step("Campaign-map figures: {edited}'s agent shown by another model", "its agent's figure on the campaign map")
def s_figures(c, mod):
    from . import stratmodels as SM
    from .edit import edit
    figs = SM.figures(mod, c.edited)
    types = sorted(SM.model_types(mod))
    fg = next((f for f in figs if f["type"] in ("spy", "diplomat", "merchant")), figs[0] if figs else None)
    if not fg:
        raise Skip("no character types")
    other = next(m for m in types if m not in fg["models"])
    return edit(mod, c.campaign, c.edited, {"figures": {fg["type"]: [other] * len(fg["models"])}})


@step("New unit step by step: 'CE Test Guard' copied with its texts, owned by {edited} and {new}",
      "CE Test Guard in the unit list (custom battle)")
def s_units(c, mod):
    from . import editors as E
    src = unit_names(mod, c.edited, 1)[0]
    plan = Plan(mod, "u", "u", {})
    E.copy_unit(plan, src, "ce test guard", "ce_test_guard", True,
                texts={"name": "CE Test Guard", "descr": "Made by the test mod", "descr_short": "Test unit"},
                owners=[c.edited, c.new])
    return plan


@step("New building step by step: a chain copied as ce_test_hall", "the new building in the construction list")
def s_buildings(c, mod):
    from . import editors as E
    edb = mod.load(mod.file("edb"))
    chain = next(x for x in E.building_blocks(edb) if not x[0].startswith(("core_", "defenses", "port")))
    plan = Plan(mod, "b", "b", {})
    E.copy_building(plan, chain[0], "ce_test_hall", {}, factions=[c.edited])
    return plan


@step("Replace a unit's battle model by another foot model of the mod", "the unit looks like the other in battle")
def s_model(c, mod):
    from . import models as MO
    cat = MO.catalogue(mod)
    foot = []                                   # (unit, its soldier slot) of men on foot
    for u in unit_names(mod, c.edited, 60):
        lines = MO.unit_lines(mod, u)
        slots = [x for x in (MO.unit_slots(lines) if lines else []) if x[0] == "soldier"]
        if slots and MO.unit_seat(mod, lines) == "none" and slots[0][2].lower() in cat:
            foot.append((u, slots[0]))
    pair = next(((a, b) for a in foot for b in foot if a[1][2].lower() != b[1][2].lower()), None)
    if pair is None:
        raise Skip("no two foot units with different models")
    (unit, (key, idx, _)), (_, (_, _, other)) = pair
    plan = Plan(mod, "model", "model", {})
    MO.replace(plan, unit, key, idx, cat[other.lower()].name)
    return plan


@step("Unit voice: a unit of {edited} gets its own name call (a short beep)", "select the unit in battle: the beep")
def s_voice(c, mod):
    import wave
    from . import sounds as SN
    from .models import unit_lines
    from .packs import _values
    vf = SN.voice_file(mod)
    if not vf:
        raise Skip("no voice file")
    events = SN.voice_events(mod.load(vf))
    unit = unit_names(mod, c.edited, 1)[0]
    vt = (_values(unit_lines(mod, unit) or [], "voice_type") or [["General_1"]])[0][0]
    uv = next((v for v in SN.unit_voices(mod, events, unit, vt, [c.edited]) if v.key), None)
    if uv is None:
        raise Skip("no accent / culture group for %s" % c.edited)
    wav = os.path.join(c.work, "ce_test_beep.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        import math
        w.writeframes(b"".join(int(8000 * math.sin(i / 8.0)).to_bytes(2, "little", signed=True)
                               for i in range(22050 // 3)))
    plan = Plan(mod, "voice", "unit_voice", {})
    SN.set_name_call(plan, unit, uv.key, uv.cls, [wav])
    return plan


@step("Events: a historic message and an earthquake near {edited}'s capital",
      "the message scrolls on turn 2, the earthquake on turn 4")
def s_events(c, mod):
    from . import events as EV
    if not EV.path_of(mod, c.campaign):
        raise Skip("no descr_events.txt")
    x, y = mod.city_tiles(c.campaign)[towns_of(c, mod, c.edited)[0]]
    plan = Plan(mod, "e", "e", {})
    EV.apply(plan, c.campaign, {"new": [
        {"kind": "historic", "name": "ce_test_news", "date": EV.turn_date(mod, c.campaign, 2), "position": [x, y],
         "title": "Test news", "body": "The test mod's event."},
        {"kind": "earthquake", "name": "ce_test_quake", "date": EV.turn_date(mod, c.campaign, 4),
         "position": [x, y]}]})
    return plan


@step("Campaign rules: a number in the campaign settings changed", "")
def s_rules(c, mod):
    from . import campaignrules as CR
    for name, title, own, base in CR.files(mod):
        rules = CR.read(own or base)
        num = next((r for r in rules if CR.check(r, "7") is None), None)
        if num:
            plan = Plan(mod, "rules", "rules", {})
            CR.apply(plan, name, {num: "7"}, own, base)
            return plan
    raise Skip("no settings file")


@step("Campaign start (descr_strat.txt's top): brigands and pirates rarer, rebelling generals switched",
      "fewer brigands and pirates; generals of low loyalty may rebel (or no longer, if they could)")
def s_campaign_start(c, mod):
    from . import campaignrules as CR
    got = [x for x in CR.files(mod, c.campaign) if x[0] == "descr_strat.txt"]
    if not got or not got[0][2]:
        raise Skip("the campaign's descr_strat.txt is not in the mod")
    name, _, own, base = got[0]
    rules = {r.key: r for r in CR.read(own, medieval2=c.m2)}
    ch = {}
    for key, value in (("brigand_spawn_value", "40"), ("pirate_spawn_value", "40")):
        if key in rules:
            ch[rules[key]] = value
    flag = rules.get("rebelling_characters_active")
    if flag is not None:
        ch[flag] = "off" if flag.value == "on" else "on"
    if not ch:
        raise Skip("no values at the top of descr_strat.txt")
    plan = Plan(mod, "rules", "campaign_start", {})
    CR.apply(plan, name, ch, own, base)
    return plan


@step("Add-on: {addon} installed", "after taking a town the capture scroll offers the extra choice")
def s_addon(c, mod):
    from . import addons as AD
    key = "raze_settlement" if c.m2 else "sack_settlement"
    a = next((x for x in AD.library() if x.key == key or x.file.startswith(key)), None)
    if a is None:
        raise Skip("the add-on is not in the library")
    plan = Plan(mod, "addon", key, {})
    AD.plan_install(plan, a, AD.read_settings(a, a.template()), mod)
    return plan


@step("Art: {new}'s first picture replaced (Replace...)", "the new picture where the game shows it")
def s_art(c, mod):
    from . import factionart as FA
    from .edit import edit
    pics = FA.faction_pictures(mod, c.campaign, c.new)
    p = next((x for x in pics if not x.get("locked") and not x.get("symbol") and x.get("size")), None)
    if p is None:
        raise Skip("no picture of its own")
    return edit(mod, c.campaign, c.new, {"art": {FA.picture_target(p, c.new, c.new): logo(c)}})


@step("Faction emblem - one picture everywhere for {new}", "the emblem on the menu buttons, the loading screen, logos")
def s_emblem(c, mod):
    import tempfile
    from PIL import Image
    from . import emblem as E
    from . import factionart as FA
    from .edit import edit
    pics = E.emblem_pictures(FA.faction_pictures(mod, c.campaign, c.new))
    if not pics:
        raise Skip("no emblem pictures")
    made = E.build(Image.open(logo(c)).convert("RGBA"), pics)
    paths = E.save_all(made, tempfile.mkdtemp(prefix="ce_emblem_"))
    return edit(mod, c.campaign, c.new, {"art": {FA.picture_target(p, c.new, c.new): paths[p["rel"]]
                                                 for p in pics if p["rel"] in paths}})


@step("Banner...: {new}'s battle banners from the white banner, a tricolour and the symbol",
      "the green / yellow / white banners over {new}'s units in battle")
def s_banner(c, mod):
    import tempfile
    from PIL import Image
    from . import banners as B
    from . import emblem as E
    from . import factionart as FA
    from .edit import edit
    pics = FA.faction_pictures(mod, c.campaign, c.new)
    sym = Image.open(logo(c)).convert("RGBA")
    s = {"colours": [(40, 140, 60), (240, 220, 40), (240, 240, 240)], "pattern": "three stripes, upright (tricolour)"}
    if c.m2:
        from . import banners_m2 as BM
        from .recolour import read_picture
        ps = [p for p in pics if (p.get("extra") or {}).get("kind") == "banner" and BM.faction_sheet(p["path"])]
        sheet = BM.sheet_blank(mod)
        if not ps or sheet is None:
            raise Skip("no banner sheet")
        kit = BM.Kit(sheet, BM.meshes(mod), read_picture(ps[0]["path"]).getchannel("A"))
        made = {p["rel"]: kit.make(s, sym) for p in ps}
    else:
        ps = [p for p in pics if E.is_banner(p) and not p.get("locked")]
        blanks = B.templates(mod)
        if not ps or not blanks:
            raise Skip("no banner / blank banner")
        made = {p["rel"]: B.make(blanks[next(iter(blanks))], s, sym,
                                 B.ALLY_STRENGTH if p["link"][1] == "ally_texture" else 1.0) for p in ps}
    paths = E.save_all(made, tempfile.mkdtemp(prefix="ce_banner_"))
    art = {}
    for p in ps:
        x = p.get("extra")
        art[FA.picture_target(p, c.new, c.new)] = {"src": paths[p["rel"]], "extra": [x["kind"], x["ref"]]} \
            if p.get("locked") and x else paths[p["rel"]]
    return edit(mod, c.campaign, c.new, {"art": art})


@step("Recolour all its pictures (every one Recolour finds): {new} from {template}'s colours to its own",
      "cards, unit and battle textures, shields, banners, figures, symbols in green / yellow")
def s_recolour(c, mod):
    from . import recolour as R
    items = [it for it in R.targets(mod, c.campaign, c.new) if not isinstance(it, str) and not it.get("skip")]
    if not items:
        raise Skip("nothing to recolour")
    src = R.guess_source(mod, c.new, items, R.faction_colours(mod))[0]
    plan = Plan(mod, "recolour", c.new, {})
    R.plan_recolour(plan, items, src, ((40, 140, 60), (240, 220, 40)))
    return plan



# ---------------------------------------------------------------------------
# the variants: every option of a feature its own step (a tester: 'test every function of the program')
def _game_data(mod):
    from .campaignrules import game_data
    return game_data(mod)


@step("Diplomacy at the start: {edited} allied to {new} and at war with {foreign}",
      "the diplomacy screen: {new} an ally of {edited}, {foreign} at war with it from the first turn")
def s_alliance(c, mod):
    from .diplomacy import kinds
    from .edit import edit
    stance = kinds(_strat(mod, c.campaign))[1]
    return edit(mod, c.campaign, c.edited, {"relations": [
        {"kind": stance, "from": "me", "to": c.new, "value": "allied_to"},
        {"kind": stance, "from": "me", "to": c.foreign, "value": "at_war_with"}]})


@step("Many towns at once: a rebel town made one level bigger and (Medieval II) a city made a castle",
      "the bigger rebel town; the castle where a city stood, its buildings turned into castle ones")
def s_city_castle(c, mod):
    from . import masstown as MT
    from .buildings import SETTLEMENT_LEVELS
    known = MT.known_buildings(mod)
    towns = MT.towns(mod, c.campaign)
    ch = {}
    for t in [t for t in towns if t["owner"] == "slave"]:
        i = SETTLEMENT_LEVELS.index(t["level"]) if t["level"] in SETTLEMENT_LEVELS else -1
        if 0 <= i < len(SETTLEMENT_LEVELS) - 2 and MT.town_fit(known, t, None, SETTLEMENT_LEVELS[i + 1])[0] == "set":
            ch[t["region"]] = {"level": SETTLEMENT_LEVELS[i + 1]}
            break
    if c.m2:
        for t in [t for t in towns if t["owner"] == c.other and t.get("kind") == "city"]:
            if MT.town_fit(known, t, "castle", None)[0] == "set":
                ch[t["region"]] = {"kind": "castle"}
                break
    if not ch:
        raise Skip("no town that takes another level or kind")
    plan = Plan(mod, "towns", "towns", {})
    MT.apply(plan, c.campaign, {"towns": ch})
    return plan


@step("Garrisons the game's way: a rebel town's garrison from its region's rebels, sized as the game sizes them; "
      "{other}'s town only what its buildings recruit",
      "the rebel town's local troops; {other}'s garrison of units its own buildings train")
def s_garrison_kinds(c, mod):
    from . import masstown as MT
    towns = MT.towns(mod, c.campaign)
    sizes = MT.level_sizes(mod, c.campaign)
    gar = {}
    reb = next((t for t in towns if t["owner"] == "slave"), None)
    if reb:
        n = max(1, min(6, int(sizes.get(reb["level"], 2))))
        g = MT.random_garrison(MT.rebel_pool(mod, c.campaign, reb["region"]), n, n, None, c.rng)
        if g:
            gar[reb["region"]] = g
    mine = next((t for t in towns if t["owner"] == c.other), None)
    if mine:
        g = MT.random_garrison(MT.town_pool(mod, mine, MT.garrison_pool(mod, c.other)), 2, 3, None, c.rng)
        if g:
            gar[mine["region"]] = g
    if not gar:
        raise Skip("no units to draw")
    plan = Plan(mod, "towns", "towns", {})
    MT.apply(plan, c.campaign, {"garrisons": gar, "add_units": True})
    return plan


@step("Unit editor: a line of a unit changed (its cost) - every line of a block is a field",
      "the unit of {edited} costs 10 more in the recruitment list")
def s_unit_fields(c, mod):
    from . import editors as E
    path = mod.file("edu")
    f = mod.load(path)
    blocks = {b[0]: b for b in E.unit_blocks(f)}
    for u in unit_names(mod, c.edited, 10):
        b = blocks.get(u)
        if not b:
            continue
        for fd in E.fields(f, b[1], b[2]):
            t = [x.strip() for x in fd.value.split(",")]
            if fd.key == "stat_cost" and len(t) > 1 and t[1].isdigit():
                t[1] = str(int(t[1]) + 10)
                plan = Plan(mod, "unit", u, {})
                E.apply_fields(plan, path, {fd.line: ", ".join(t)}, "unit %s" % u)
                return plan
    raise Skip("no stat_cost line")


@step("Building editor: a line of a building level changed (its cost)",
      "that building costs 10 more to build")
def s_building_fields(c, mod):
    from . import editors as E
    path = mod.file("edb")
    f = mod.load(path)
    for b in E.building_blocks(f):
        if b[0].startswith(("core_", "defenses")):
            continue
        for fd in E.fields(f, b[1], b[2]):
            if fd.key == "cost" and fd.value.split()[:1] and fd.value.split()[0].isdigit():
                plan = Plan(mod, "building", b[0], {})
                E.apply_fields(plan, path, {fd.line: str(int(fd.value.split()[0]) + 10)}, "building %s" % b[0])
                return plan
    raise Skip("no cost line")


@step("Character editor: {edited}'s leader gets a trait and a retinue member",
      "the leader's panel: the new trait and the new retinue member")
def s_character(c, mod):
    from . import family as FM
    from .edit import edit
    fam = FM.read(mod.load(mod.campaign_file(c.campaign, "descr_strat.txt")), c.edited)
    leader = next((p for p in fam["people"] if p.on_map and p.role == "leader"), None) or \
        next((p for p in fam["people"] if p.on_map and p.kind == "named character"), None)
    if leader is None:
        raise Skip("%s has no leader on the map" % c.edited)
    traits = FM.trait_list(mod)
    ancs = FM.ancillary_list(mod)
    have = {t for t, _ in (leader.traits or [])}
    t = next((n for n, i in traits.items() if n not in have and "family" in " ".join(i["characters"]).lower()
              and i["levels"]), None) or next((n for n in traits if n not in have), None)
    a = next((n for n, i in ancs.items() if n not in (leader.ancillaries or [])
              and mod.culture(c.edited) not in (i.get("exclude") or [])), None)
    ch = {}
    if t:
        ch["traits"] = list(leader.traits or []) + [[t, 1]]
    if a:
        ch["ancillaries"] = list(leader.ancillaries or []) + [a]
    if not ch:
        raise Skip("no trait or retinue member to give")
    return edit(mod, c.campaign, c.edited, {"family": {"people": {leader.key: ch}}})


@step("Family: a daughter for {other}'s leader, and a new man tied to no family (he goes on the map as a general)",
      "{other}'s family tree shows the girl; a new general with an army in {other}'s first town")
def s_family_more(c, mod):
    from . import family as FM
    from .edit import edit
    from .strat import first_names
    fam = FM.read(mod.load(mod.campaign_file(c.campaign, "descr_strat.txt")), c.other)
    tree = [list(x) for x in fam["tree"]]
    people = {p.name for p in fam["people"]} | {n for t in tree for n in [t[0], t[1]] + list(t[2])}
    pool = mod.name_pool(c.other)
    new = []
    if tree:
        head = tree[0]
        surname = head[0].split(" ", 1)[1] if " " in head[0] else ""
        girl = next(((f + " " + surname).strip() for f in first_names(pool, "princess") or
                     first_names(pool, "female") or [] if (f + " " + surname).strip() not in people), None)
        if girl:
            head[2] = list(head[2]) + [girl]
            new.append({"name": girl, "sex": "female", "age": 12})
            people.add(girl)
    man = next((f for f in first_names(pool, "general") or [] if f not in people), None)
    if man:
        new.append({"name": man, "sex": "male", "age": 30})
    if not new:
        raise Skip("no free names")
    return edit(mod, c.campaign, c.other, {"family": {"new": new, "tree": tree if tree else None}})


@step("Map: a port moved one tile along its coast", "the port beside its old place")
def s_port(c, mod):
    from . import mapedit as ME
    from .edit import edit
    ports = ME.ports(mod, c.campaign)
    for region in towns_of(c, mod, c.edited) + towns_of(c, mod, c.other):
        xy = ports.get(region)
        if not xy:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            to = (xy[0] + dx, xy[1] + dy)
            if not ME.place_problem(mod, c.campaign, "port", region, to):
                return edit(mod, c.campaign, c.edited, {"places": [{"what": "port", "region": region, "to": to}]})
    raise Skip("no port that can move")


@step("Edit region: a rebel region's rebels, resources, farming and the names players see changed",
      "the region and its town under their new shown names; its farming level")
def s_region_props(c, mod):
    from .regionedit import apply_opts
    info = mod.regions(c.campaign)
    region = next((r for r in towns_of(c, mod, "slave")[1:] if r in info), None)
    if region is None:
        raise Skip("no rebel region")
    other = next((v["rebels"] for v in info.values() if v.get("rebels") and v["rebels"] != info[region].get("rebels")),
                 info[region].get("rebels"))
    plan = Plan(mod, None, "map")
    apply_opts(plan, c.campaign, {"edits": {region: {"rebels": other, "farming": "3",
                                                     "label": "CE Shown Land", "settlement_label": "CE Shown Town"}}})
    return plan


@step("Map: a character of {edited} moved, an agent of {other} deleted from the map",
      "{edited}'s character on his new tile; {other}'s agent gone")
def s_move_delete(c, mod):
    from .edit import edit, map_changes
    s = _strat(mod, c.campaign)
    plans = []
    mine = next((ch for ch in s.faction(c.edited).characters if ch.xy and not ch.role), None)
    if mine:
        to = free_land(c, mod, mine.xy, mine.kind, True)
        if to:
            plans.append(edit(mod, c.campaign, c.edited, {"moves": [{"name": mine.name, "from": mine.xy, "to": to}]}))
    agent = next((ch for fb in s.factions if fb.name not in ("slave", c.edited) for ch in fb.characters
                  if ch.xy and not ch.role and not ch.named), None)
    if agent:
        plan = Plan(mod, "map", "map", {})
        fac = next(fb.name for fb in s.factions if agent in fb.characters)
        map_changes(plan, c.campaign, {"remove": {fac: [{"name": agent.name, "from": agent.xy}]}})
        plans.append(plan)
    if not plans:
        raise Skip("no character to move or agent to delete")
    return plans


@step("Terrain editor: a cliff and a volcano painted, a climate changed near {edited}'s capital",
      "the cliff and the volcano near the capital; the other climate's look")
def s_features(c, mod):
    from . import terrain as T
    from .edit import read_faction
    from .mapdata import CampaignMap
    cmap = CampaignMap(mod, c.campaign)
    standing = set(cmap.cities.values()) | set(cmap.ports.values()) | taken_tiles(c, mod)
    cap = mod.city_tiles(c.campaign)[read_faction(mod, c.campaign, c.edited)["regions"][0]]
    want = [(255, 255, 0), T.VOLCANO]
    features, climate = {}, {}
    clim = T.climates(mod)
    for d in range(3, 12):
        for dx in range(-d, d + 1):
            for dy in (-d, d):
                p = (cap[0] + dx, cap[1] + dy)
                if want and not T.paint_problem(cmap, "features", p, want[0], standing):
                    features[p] = want.pop(0)
                elif clim and not climate and p not in features and \
                        not T.paint_problem(cmap, "climate", p, clim[-1][1], standing):
                    climate[p] = tuple(clim[-1][1])
    if not features and not climate:
        raise Skip("no land to paint")
    plan = Plan(mod, "terrain", "terrain")
    T.apply(plan, c.campaign, features=features, climate=climate)
    return plan


@step("Bring from another mod: a unit and a building chain brought from the game's own data (renamed, as both "
      "are here already)", "the brought unit and building under their new names, owned by {new}")
def s_bring(c, mod):
    from . import packs as P
    from . import editors as E
    from .moddata import ModData
    src_data = _game_data(mod)
    if not src_data:
        raise Skip("this mod is the game's own data - no other mod to bring from")
    src = ModData(src_data)
    unit = unit_names(src, c.foreign, 1)
    edb = src.load(src.file("edb"))
    chain = next((b[0] for b in E.building_blocks(edb) if not b[0].startswith(("core_", "defenses", "port"))), None)
    plan = Plan(mod, "bring", "bring", {})
    if unit:
        manifest, files = P.collect(src, unit)
        P.import_pack(plan, manifest, files, [c.new], P.plan_names(mod, manifest))
    if chain:
        manifest, files = P.collect_buildings(src, [chain])
        chains, levels = P.building_names(mod, manifest)
        P.import_buildings(plan, manifest, files, [c.new], chains, levels)
    return plan


@step("Unit packs: a unit of {foreign} exported as a pack (.zip) and put back in as a copy for {new}",
      "the copied unit in {new}'s recruitment list")
def s_unit_pack(c, mod):
    from . import packs as P
    unit = unit_names(mod, c.foreign, 2)[-1:]
    if not unit:
        raise Skip("no unit")
    path = os.path.join(c.work, "ce_test_pack.zip")
    P.export_pack(mod, unit, path)
    manifest, files = P.read_pack(path)
    plan = Plan(mod, "pack", "pack", {})
    P.import_pack(plan, manifest, files, [c.new], P.plan_names(mod, manifest))
    return plan


@step("Check and install a pack: a small pack (a unit card for {new}) checked and installed",
      "the card in {new}'s unit list")
def s_modpack(c, mod):
    import shutil
    from . import modpack as MP
    folder = os.path.join(c.work, "ce_test_modpack")
    shutil.rmtree(folder, ignore_errors=True)
    cards = os.path.join(mod.data, "ui", "units", c.new)
    card = next((os.path.join(cards, n) for n in sorted(os.listdir(cards)) if n.lower().endswith(".tga")), None) \
        if os.path.isdir(cards) else None
    if card is None:
        raise Skip("%s has no unit cards" % c.new)
    dst = os.path.join(folder, "data", "ui", "units", c.new, "#ce_pack_card.tga")
    os.makedirs(os.path.dirname(dst))
    shutil.copyfile(card, dst)
    files, _ = MP.read(folder)
    entries = MP.check(mod, files)
    plan = Plan(mod, "pack", "pack", {})
    MP.install(plan, files, entries)
    return plan


@step("Add-on: Player Diplomacy (REX) installed", "the diplomacy offers the add-on adds")
def s_addon_diplomacy(c, mod):
    from . import addons as AD
    if c.m2:
        raise Skip("Player Diplomacy is a REX add-on (Rome)")
    a = next((x for x in AD.library() if x.key == "player_diplomacy" or x.file.startswith("player_diplomacy")), None)
    if a is None:
        raise Skip("the add-on is not in the library")
    plan = Plan(mod, "addon", "player_diplomacy", {})
    AD.plan_install(plan, a, AD.read_settings(a, a.template()), mod)
    return plan


@step("Events: a plague, a flood and a storm on turns 6-8; one of the game's events moved a turn later, another "
      "taken out", "the plague on turn 6, the flood on turn 7, the storm on turn 8")
def s_events_more(c, mod):
    from . import events as EV
    path = EV.path_of(mod, c.campaign)
    if not path:
        raise Skip("no descr_events.txt")
    x, y = mod.city_tiles(c.campaign)[towns_of(c, mod, c.other)[0]]
    old = [e for e in EV.read(mod.load(path)) if not e["name"].startswith("ce_test")]
    ch = {"new": [{"kind": k, "name": "ce_test_" + k, "date": EV.turn_date(mod, c.campaign, t), "position": [x, y]}
                  for k, t in (("plague", 6), ("flood", 7), ("storm", 8))]}
    if len(old) >= 2:
        d = old[-2]["date"].split()
        ch["edit"] = {old[-2]["id"]: {"date": " ".join([str(int(d[0]) + 1)] + d[1:])}}
        ch["remove"] = [old[-1]["id"]]
    plan = Plan(mod, "e", "e", {})
    EV.apply(plan, c.campaign, ch)
    return plan


@step("Engine settings (REX / M2EX): a number of descr_ex.txt raised by one (retinue places or faction slots)",
      "")
def s_engine_rules(c, mod):
    from . import campaignrules as CR
    for name, title, own, base in CR.files(mod):
        if name.lower() != "descr_ex.txt":
            continue
        rules = [r for r in CR.read(own or base) if r.kind == "int" and CR.check(r, r.value) is None]
        # a harmless number first: one more retinue place or faction slot
        num = next((r for k in ("max_num_ancillaries", "max_factions") for r in rules if r.key == k),
                   rules[0] if rules else None)
        if num:
            plan = Plan(mod, "rules", "engine", {})
            CR.apply(plan, name, {num: str(int(num.value) + 1)}, own, base)
            return plan
    raise Skip("no descr_ex.txt (no REX / M2EX)")


@step("Roster: a unit taken away from {edited}", "the unit no longer in {edited}'s recruitment list")
def s_roster_take(c, mod):
    from . import roster as R
    from .edit import edit
    r = R.roster(mod, c.edited)
    u = next((x["type"] for x in r["units"][::-1] if x["has"] == "own" and
              not R._units_in_armies(mod, c.campaign, c.edited, x["type"])), None)
    if u is None:
        raise Skip("no unit of %s alone to take away" % c.edited)
    return edit(mod, c.campaign, c.edited, {"roster": {"unit:" + u: False}})


@step("Art: every picture of {later} replaced (each one the Art tab offers)",
      "{later}'s pictures (buttons, loading screen, banners, cards...) are the test picture once it comes in")
def s_art_all(c, mod):
    from . import factionart as FA
    from .edit import edit
    pics = [p for p in FA.faction_pictures(mod, c.campaign, c.later) if not p.get("locked") and p.get("size")]
    if not pics:
        raise Skip("no pictures of its own")
    return edit(mod, c.campaign, c.later, {"art": {FA.picture_target(p, c.later, c.later): logo(c) for p in pics}})


# ---------------------------------------------------------------------------
# coverage: every feature of the editor and the steps that try it - a feature tried by the run itself or one that
# only shows (writes nothing) says so. tests.test_tool checks that every work button, tab and Tools entry of the
# window is in UI below, and that every step named here exists: a new feature without a step fails the tests.
RUN = "tried by the run itself"
LOOK = "only shows, writes nothing - tried in the window by check-scripts/smoke.py"
COVERAGE = {
    "New faction": ["s_new_faction"],
    "New mod folder": RUN + " (CE_Test is made with it)",
    "Edit faction (names, colours, money, towns, garrisons)": ["s_edit"],
    "Victory conditions": ["s_victory"],
    "Armies, agents and fleets placed by hand": ["s_chars", "s_map"],
    "Diplomacy: feelings": ["s_diplomacy"],
    "Diplomacy: alliances and wars at the start": ["s_alliance"],
    "Factions that come later: by an event": ["s_later"],
    "Factions that come later: a shadow (civil war)": ["s_later_way"],
    "Factions that come later: splitting off in a revolt": ["s_split"],
    "Resources on the map": ["s_resources"],
    "Forts, watchtowers, wonders (Rome)": ["s_forts"],
    "Town window: owner and population": ["s_town"],
    "Many towns: a building, random garrisons": ["s_masstown"],
    "Many towns: city / castle and level": ["s_city_castle"],
    "Many towns: garrisons the game's way (rebels, the town's own buildings)": ["s_garrison_kinds"],
    "Map: a town moved": ["s_move_town"],
    "Map: a port moved": ["s_port"],
    "Map: a character moved, one deleted": ["s_move_delete"],
    "New region": ["s_region"],
    "Rename a region and its town everywhere": ["s_rename"],
    "Edit region: rebels, resources, farming, names players see": ["s_region_props"],
    "Settlement names by culture": ["s_culture_names"],
    "Terrain editor: ground and heights": ["s_terrain"],
    "Terrain editor: features and climates": ["s_features"],
    "Land and sea": ["s_coast"],
    "Family: a son": ["s_family"],
    "Family: a daughter, a man tied to no one": ["s_family_more"],
    "Character editor: traits and retinue of a character": ["s_character"],
    "Traits and retinue: a new trait": ["s_traits"],
    "Religions (Medieval II)": ["s_religion"],
    "Roster: give": ["s_roster", "s_roster_other"],
    "Roster: take away": ["s_roster_take"],
    "Campaign-map figures": ["s_figures"],
    "Unit editor: lines": ["s_unit_fields"],
    "Unit editor: new unit step by step": ["s_units"],
    "Unit editor: replace the battle model": ["s_model"],
    "Unit editor: voice": ["s_voice"],
    "Building editor: lines": ["s_building_fields"],
    "Building editor: new building step by step": ["s_buildings"],
    "Bring from another mod": ["s_bring"],
    "Unit packs export / import": ["s_unit_pack"],
    "Check and install a pack": ["s_modpack"],
    "Events": ["s_events", "s_events_more"],
    "Campaign rules": ["s_rules"],
    "Campaign start (descr_strat.txt)": ["s_campaign_start"],
    "Engine settings (REX / M2EX)": ["s_engine_rules"],
    "Add-ons": ["s_addon", "s_addon_diplomacy"],
    "Art: replace a picture": ["s_art", "s_art_all"],
    "Faction emblem": ["s_emblem"],
    "Banner...": ["s_banner"],
    "Recolour a faction's pictures": ["s_recolour"],
    "Make the campaign map 3 x bigger": RUN + " (the x3 copy, when asked)",
    "Check mod files": RUN + " (after every step)",
    "Restore a backup": RUN + " (check-scripts/testmod.py restores every step byte for byte)",
    "The game's log in plain words": LOOK,
    "View in 3D, play a sound": LOOK,
    "Settings, Help, the log, Save logs, Game manifest": LOOK,
    "Report a bug / Suggest, Answers to my reports": "sends to the internet - tried by hand",
    "Test mod": "this run",
}

# the window's work buttons, tabs and Tools entries (the start of their text) -> the feature above
UI = {
    "New faction": "New faction", "Edit faction": "Edit faction (names, colours, money, towns, garrisons)",
    "Unit editor": "Unit editor: lines", "Building editor": "Building editor: lines",
    "Character editor": "Character editor: traits and retinue of a character",
    "Terrain editor": "Terrain editor: ground and heights", "Add-ons": "Add-ons",
    "Religions": "Religions (Medieval II)",
    "Faction": "Edit faction (names, colours, money, towns, garrisons)",
    "Map": "Map: a town moved", "Diplomacy": "Diplomacy: feelings", "Art": "Art: replace a picture",
    "Roster": "Roster: give", "Settlements": "Edit region: rebels, resources, farming, names players see",
    "Units & armies": "Armies, agents and fleets placed by hand",
    "Buildings": "Many towns: a building, random garrisons",
    "Check mod files": "Check mod files", "The game's log": "The game's log in plain words",
    "Settlement names by culture": "Settlement names by culture",
    "Buildings and garrisons for many towns": "Many towns: a building, random garrisons",
    "Recolour a faction's pictures": "Recolour a faction's pictures",
    "Make the campaign map 3 x bigger": "Make the campaign map 3 x bigger",
    "Check and install a pack": "Check and install a pack", "Campaign rules": "Campaign rules",
    "Traits and retinue": "Traits and retinue: a new trait", "Events and later factions": "Events",
    "New religion": "Religions (Medieval II)", "Religions of a region": "Religions (Medieval II)",
    "Restore a backup": "Restore a backup", "Game manifest": "Settings, Help, the log, Save logs, Game manifest",
    "Log": "Settings, Help, the log, Save logs, Game manifest",
    "Save logs": "Settings, Help, the log, Save logs, Game manifest",
    "Report a bug": "Report a bug / Suggest, Answers to my reports",
    "Suggest an idea": "Report a bug / Suggest, Answers to my reports", "Test mod": "Test mod",
}


def coverage_problems():
    """[why] a feature or a UI entry is not covered: a step named in COVERAGE that does not exist, a UI entry
    pointing at no feature."""
    names = {fn.__name__ for _, _, fn in STEPS}
    out = ["%s: no step %s" % (k, s) for k, v in COVERAGE.items() if isinstance(v, list) for s in v if s not in names]
    out += ["%s: names no feature (%s)" % (k, v) for k, v in UI.items() if v not in COVERAGE]
    used = {s for v in COVERAGE.values() if isinstance(v, list) for s in v}
    out += ["step %s is in no feature of COVERAGE" % n for n in sorted(names - used)]
    return out


def ui_entry(text):
    """The UI key a window text starts with (the longest match), or None."""
    t = text.strip()
    hits = [k for k in UI if t.startswith(k)]
    return max(hits, key=len) if hits else None

# ---------------------------------------------------------------------------
def problems(mod, campaign):
    """The PROBLEMS lines of Check mod files."""
    from .check import check_mod
    out, on = [], False
    for line in check_mod(mod, campaign).splitlines():
        if line.startswith("PROBLEMS"):
            on = True
            continue
        if on and line.startswith("    "):
            out.append(line.strip())
        elif on:
            on = False
    return out


def make_mod(data, name=NAME):
    """A new mod folder (New mod folder) from the loaded mod or game: (its data folder, the name used)."""
    from . import newmod
    base, k = name, 1
    while os.path.exists(newmod.mod_target(data, name)):
        k += 1
        name = "%s_%d" % (base, k)
    return newmod.create_mod(data, name)[0], name


def run(data, campaign, progress=None, make=True):
    """Make the test mod from data (the loaded mod or game; make=False works on data itself) and run every step.
    Returns (the mod's data folder, [result {'step', 'see', 'status' OK | FAILED | SKIPPED | NOTHING WRITTEN,
    'files', 'warnings', 'new_problems', 'error', 'seconds'}], the report text)."""
    say = progress or (lambda text: None)
    from .moddata import ModData
    if make:
        say("making the mod folder (New mod folder)...")
        data, _ = make_mod(data)
    work = os.path.join(os.path.dirname(data), "CampaignEditor_test")
    os.makedirs(work, exist_ok=True)
    c = Ctx(data, campaign, work)
    names = {"template": c.template, "edited": c.edited, "other": c.other, "new": c.new, "later": c.later,
             "split": c.split, "foreign": c.foreign,
             "addon": "Sack Settlement (Medieval II, M2EX)" if c.m2 else "Sack Settlement (Rome, REX)"}
    before = problems(ModData(data), campaign)
    results = []
    for n, (title, see, fn) in enumerate(STEPS, 1):
        title, see = title.format(**names), see.format(**names)
        say("test mod: step %d of %d - %s" % (n, len(STEPS), title))
        rec = {"step": title, "see": see, "files": [], "warnings": [], "fn": fn.__name__}
        t = time.time()
        try:
            got = fn(c, c.mod())
            for plan in (got if isinstance(got, list) else [got]):
                if plan is None:
                    continue
                rec["warnings"] += [w[1] if isinstance(w, tuple) else str(w) for w in plan.warnings]
                rec["files"] += [os.path.relpath(p, data).replace("\\", "/") for p in plan.changed_files()]
                rec["files"] += [os.path.relpath(d, data).replace("\\", "/") for _, d in plan.copies]
                plan.apply()
            rec["files"] = sorted(set(rec["files"]))
            rec["status"] = "OK" if rec["files"] else "NOTHING WRITTEN"
        except Skip as e:
            rec["status"], rec["error"] = "SKIPPED", str(e)
        except Exception as e:
            rec["status"], rec["error"] = "FAILED", "%s: %s" % (type(e).__name__, e)
            rec["trace"] = traceback.format_exc()[-2000:]
        try:
            now = problems(ModData(data), campaign)
        except Exception as e:
            now = ["Check mod files itself failed: %s" % e]
        rec["new_problems"] = [p for p in now if p not in before]
        before = now
        rec["seconds"] = round(time.time() - t, 1)
        results.append(rec)
    text = report(data, campaign, names, results)
    with open(os.path.join(os.path.dirname(data), "CE_Test_report.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return data, results, text


def run_x3(data, campaign, progress=None):
    """A second mod made from the test mod (New mod folder on it) with the campaign map made 3 x bigger - the bigger
    map tried on a map every other feature has changed. Returns (its data folder, the warnings)."""
    from .moddata import ModData
    from .upscale import plan_upscale
    say = progress or (lambda text: None)
    say("making the second mod for the 3 x bigger map...")
    data, name = make_mod(data, NAME + "_x3")
    plan = Plan(ModData(data), "map", "map_x3", {})
    warn = plan_upscale(plan, campaign, vertical=3, progress=lambda t: say("3 x bigger map: " + t))
    plan.apply()
    return data, warn


def report(data, campaign, names, results):
    ok = sum(1 for r in results if r["status"] == "OK" and not r["new_problems"])
    out = ["The editor's test mod - every feature, one step each", "",
           "Mod: %s" % os.path.dirname(data), "Campaign: %s" % campaign,
           "Factions: clone %(template)s -> %(new)s, edited %(edited)s, later %(later)s, split %(split)s, "
           "units moved from %(foreign)s, other %(other)s" % names,
           "%d of %d steps fine (written, no new problem in Check mod files)" % (ok, len(results)), "",
           "Start the mod in the game (its Start .bat), play a few turns and a battle, look at what each step says, "
           "then send Report a bug with the game's log ticked.", ""]
    for n, r in enumerate(results, 1):
        out.append("%2d. [%s] %s" % (n, r["status"], r["step"]))
        if r.get("error"):
            out.append("      %s" % r["error"])
        if r["see"]:
            out.append("      in the game: %s" % r["see"])
        if r["files"]:
            out.append("      wrote %d file(s): %s%s" % (len(r["files"]), ", ".join(r["files"][:6]),
                                                    " ..." if len(r["files"]) > 6 else ""))
        for w in r["warnings"][:5]:
            out.append("      note: %s" % w)
        for p in r["new_problems"]:
            out.append("      NEW PROBLEM in Check mod files: %s" % p)
        if r.get("trace"):
            out.append("      " + r["trace"].strip().replace("\n", "\n      "))
    out += ["", "Every feature of the editor and how this run tried it:"]
    by_fn = {r.get("fn"): (n, r["status"]) for n, r in enumerate(results, 1)}
    for feature, how in COVERAGE.items():
        if isinstance(how, list):
            got = [by_fn[s] for s in how if s in by_fn]
            out.append("  %-62s %s" % (feature, ", ".join("step %d %s" % g for g in got) or "not run"))
        else:
            out.append("  %-62s %s" % (feature, how))
    return "\n".join(out) + "\n"


__all__ = ["STEPS", "COVERAGE", "UI", "coverage_problems", "ui_entry", "run", "run_x3", "report", "make_mod", "problems", "NAME"]
