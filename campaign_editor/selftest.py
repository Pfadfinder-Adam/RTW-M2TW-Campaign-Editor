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
    return build(mod, c.campaign, c.edited, c.later, {
        "display_name": "Rising Test", "short_name": "Rising", "adjective": "Rising", "raise_faction_limit": True,
        "start": {"way": "event", "date": "20" if c.m2 else "20 summer", "region": towns_of(c, mod, c.edited)[0],
                  "re_emergent": True, "denari": 3000, "regions": [], "leader": None, "playable": False}})


@step("...its way changed to: the shadow of {edited}, may come back",
      "when {edited} has a revolt, {later} takes the rebel towns")
def s_later_way(c, mod):
    from . import emergence as E
    plan = Plan(mod, "later", c.later, {})
    E.apply(plan, c.campaign, c.later, "shadow", of=c.edited, re_emergent=True)
    return plan


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


@step("Events: a historic message and an earthquake near {edited}'s capital", "the event scrolls on turn 2 and 4")
def s_events(c, mod):
    from . import events as EV
    if not EV.path_of(mod, c.campaign):
        raise Skip("no descr_events.txt")
    x, y = mod.city_tiles(c.campaign)[towns_of(c, mod, c.edited)[0]]
    plan = Plan(mod, "e", "e", {})
    EV.apply(plan, c.campaign, {"new": [
        {"kind": "historic", "name": "ce_test_news", "date": "2" if c.m2 else "2 summer", "position": [x, y],
         "title": "Test news", "body": "The test mod's event."},
        {"kind": "earthquake", "name": "ce_test_quake", "date": "4" if c.m2 else "4 winter", "position": [x, y]}]})
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
             "addon": "Raze Settlement (M2EX)" if c.m2 else "Sack Settlement (REX)"}
    before = problems(ModData(data), campaign)
    results = []
    for n, (title, see, fn) in enumerate(STEPS, 1):
        title, see = title.format(**names), see.format(**names)
        say("test mod: step %d of %d - %s" % (n, len(STEPS), title))
        rec = {"step": title, "see": see, "files": [], "warnings": []}
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
           "Factions: clone %(template)s -> %(new)s, edited %(edited)s, later %(later)s, other %(other)s" % names,
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
    return "\n".join(out) + "\n"


__all__ = ["STEPS", "run", "run_x3", "report", "make_mod", "problems", "NAME"]
