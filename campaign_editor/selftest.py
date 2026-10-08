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

from . import scriptmods as SM
from .textio import strip_comment
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
        self.shadow = _free_name("ce_test_shadow", taken | {self.new, self.later, self.split})
        # a faction of another culture than the template: its units and buildings are surely not the clone's
        cult = dict(mod.factions())
        self.foreign = next((n for n, cu in mod.factions() if n != "slave" and cu != cult.get(self.template) and
                             n not in (self.new, self.later, self.split, self.shadow)), self.other)
        # the faction the split-off one leaves: on Barbarian Invasion the new faction itself, which has a shadow too -
        # the test of whether one faction may have both (BI's own never does; plain Rome takes neither); elsewhere
        # the template
        from . import emergence as EM
        from .limits import game_kind
        self.both = game_kind(mod) == "rome" and EM.is_bi(mod)
        self.split_of = self.new if self.both else self.template
        self.logo = None
        self.colours = test_colours(mod, [self.new, self.shadow, self.later, self.split])
        self.said = {}                       # what the steps picked, for the texts: {'near': town, 'far': town}

    def mod(self):
        from .moddata import ModData
        return ModData(self.data)


# colours to pick the test factions' from: the ones farthest from every faction of the game, so each test faction is
# told apart at once on the map and in battle (and Recolour shows what it did)
CANDIDATES = [(255, 0, 255), (0, 255, 255), (255, 140, 0), (128, 255, 0), (255, 105, 180), (0, 0, 0),
              (64, 224, 208), (255, 255, 255), (139, 69, 19), (128, 128, 128), (0, 255, 128), (255, 255, 0),
              (75, 0, 130), (0, 128, 128)]


def test_colours(mod, factions):
    """{faction: (primary, secondary)}: for each test faction the candidate primary farthest from every colour the
    game's factions wear (and from those already given), with the candidate secondary that stands out most on it."""
    from .recolour import faction_colours
    worn = [c for pair in faction_colours(mod).values() for c in pair if c]

    def d2(c, w):
        return sum((a - b) ** 2 for a, b in zip(c, w))

    def far(c, used):
        # far from the game's colours; one within 200 of a test faction's own is out - they must not look alike
        if any(d2(c, u) < 200 ** 2 for u in used):
            return -1
        return min([d2(c, w) for w in worn] or [0])
    out, used = {}, []
    for f in factions:
        p = max((c for c in CANDIDATES if c not in used), key=lambda c: far(c, used))
        used.append(p)
        s = max((c for c in CANDIDATES if c not in used), key=lambda c: d2(c, p))
        out[f] = (p, s)
    return out


class _Names(dict):
    """The factions' names for a step's text, and what the steps picked ({near}, {far}); not picked yet: '...'."""

    def __init__(self, names, said):
        super().__init__(names)
        self.update(said)

    def __missing__(self, key):
        return "..."


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
    """The towns {faction} holds now; for the rebels, never the region the faction that comes later rises in (no
    other step may take it - an emergent faction must rise in a rebel region)."""
    keep = c.said.get("near") if faction == "slave" else None
    return [r for r, o in _strat(mod, c.campaign).owners().items() if o == faction and r != keep]


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
        p, s = c.colours[c.new]
        ImageDraw.Draw(im).ellipse((20, 20, 236, 236), fill=p + (255,), outline=s + (255,),
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
        "primary_colour": c.colours[c.new][0], "secondary_colour": c.colours[c.new][1], "raise_faction_limit": True,
        "start": {"regions": regions, "leader": {"name": names[0], "age": 40}, "characters": chars}})


@step("A faction that comes later: a clone of {edited}, dead at the start, woken by an event on turn 3 in a rebel "
      "region beside {new}'s capital", "{later} is not on the map at the start")
def s_later(c, mod):
    from . import emergence as EM
    if "event" not in EM.ways_for(mod):
        raise Skip(EM.NOT_ROME)
    from .build import build
    from .events import turn_date
    return build(mod, c.campaign, c.edited, c.later, {
        "display_name": "Rising Test", "short_name": "Rising", "adjective": "Rising", "raise_faction_limit": True,
        "primary_colour": c.colours[c.later][0], "secondary_colour": c.colours[c.later][1],
        "start": {"way": "event", "date": turn_date(mod, c.campaign, 3), "region": near_capital(c, mod),
                  "denari": 3000, "regions": [], "leader": None, "playable": False}})


@step("...its event moved to turn 2, in the rebel region next to {new}'s capital (it comes in at once, beside "
      "the test faction, to be seen on the first turns); with REX / M2EX it also lives without towns (can_homeless)",
      "{later} comes in on turn 2 in {near}, beside {new}'s capital, in its own colours; with REX / M2EX it stays in "
      "the game even when it has no town (can_homeless)")
def s_later_way(c, mod):
    from . import emergence as E
    if "event" not in E.ways_for(mod):
        raise Skip(E.NOT_ROME)
    from .events import turn_date
    from .limits import engine_of
    plan = Plan(mod, "later", c.later, {})
    E.apply(plan, c.campaign, c.later, "event", date=turn_date(mod, c.campaign, 2), region=near_capital(c, mod),
            homeless=True if engine_of(mod) else None)
    return plan


def near_capital(c, mod):
    """The REBEL town nearest {new}'s capital, where the faction that comes later rises (the games' own: Barbarian
    Invasion's slavs rise in a rebel region; in a faction's region Rome with REX killed it as the campaign loaded).
    Picked once and kept in c.said["near"]; towns_of(.., "slave") leaves it out, so no later step takes it."""
    if c.said.get("near"):
        return c.said["near"]
    tiles = mod.city_tiles(c.campaign)
    mine = [tiles[r] for r in towns_of(c, mod, c.new) if tiles.get(r)]
    rebels = [r for r in towns_of(c, mod, "slave") if tiles.get(r)]
    if not rebels:
        raise Skip("no rebel town left for the faction that comes later")
    cx, cy = mine[0] if mine else tiles[rebels[0]]
    c.said["near"] = min(rebels, key=lambda r: abs(tiles[r][0] - cx) + abs(tiles[r][1] - cy))
    return c.said["near"]


@step("A shadow of {new}: a clone of {template}, dead at the start, may come back",
      "{shadow} is not on the map at the start; when {new} has a revolt (a civil war), {shadow} takes the rebel "
      "towns - {new}'s far town (the Town window step's) is left without a garrison for it")
def s_shadow(c, mod):
    from . import emergence as EM
    if "shadow" not in EM.ways_for(mod):
        raise Skip(EM.NOT_ROME)
    from .build import build
    return build(mod, c.campaign, c.template, c.shadow, {
        "display_name": "Shadow Test", "short_name": "Shadow", "adjective": "Shadowy", "raise_faction_limit": True,
        "primary_colour": c.colours[c.shadow][0], "secondary_colour": c.colours[c.shadow][1],
        "start": {"way": "shadow", "of": c.new, "re_emergent": True, "denari": 2000, "regions": [], "leader": None,
                  "playable": False}})


@step("A faction that splits off {split_of} in a revolt: a clone of {template}, dead at the start",
      "{split} is not on the map at the start; when towns of {split_of} revolt they go to {split}, in its own "
      "colours (Barbarian Invasion: {new} has a shadow too - the test of whether one faction may have both: play "
      "a few turns, the game must not stop at the end of a turn)")
def s_split(c, mod):
    from . import emergence as EM
    if "shadow" not in EM.ways_for(mod):
        raise Skip(EM.NOT_ROME)
    from .build import build
    return build(mod, c.campaign, c.template, c.split, {
        "display_name": "Split Test", "short_name": "Split", "adjective": "Splitting", "raise_faction_limit": True,
        "primary_colour": c.colours[c.split][0], "secondary_colour": c.colours[c.split][1],
        "start": {"way": "revolt", "of": c.split_of, "both_ok": c.both, "denari": 2000, "regions": [], "leader": None,
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
        {"kind": "core_attitudes", "from": "me", "to": c.other, "value": 600}]})     # Rome: lower is better


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
                kind = ("fort", "watchtower", None)[len(spots)] if len(spots) < 3 else None
                if len(spots) < 3 and p not in taken and not FT.problem(mod, c.campaign, p, taken | set(spots), kind):
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
                    not FT.problem(mod, c.campaign, p, taken | set(spots), f0.kind):
                ch["moved"] = {str(f0.line): list(p)}
    return edit(mod, c.campaign, c.edited, {"resources": {"forts": ch}})


@step("Town window: a rebel town given to {new}, its population set to 2600 (the level follows the people)",
      "{far} is {new}'s, big enough for 2600 people - with NO garrison on purpose, far from {new}'s capital: when it "
      "revolts, {shadow} ({new}'s shadow, a civil war - Barbarian Invasion and Medieval II) takes it, else the rebels")
def s_town(c, mod):
    from . import masstown as MT
    region = towns_of(c, mod, "slave")[-1]
    c.said["far"] = region
    plan = Plan(mod, "town", region, {})
    MT.apply(plan, c.campaign, {"population": {region: 2600}, "owners": {region: c.new}, "level_follows": True})
    return plan


@step("...a rebel town given to {split_of} with no garrison, far from its capital - to revolt for {split}",
      "{split_far} is {split_of}'s, big enough for 2600 people, with NO garrison on purpose: when it revolts it goes "
      "to {split} (a faction with a shadow sends its revolting towns to the shadow instead - Medieval II with M2EX: "
      "so the split-off faction leaves another faction than the shadow's)")
def s_split_town(c, mod):
    from . import emergence as EM
    from . import masstown as MT
    if "revolt" not in EM.ways_for(mod):
        raise Skip(EM.NOT_ROME)
    if c.split_of == c.new:
        raise Skip("the split-off faction leaves the test faction here, whose far town (the Town window step) "
                   "revolts already")
    tiles = mod.city_tiles(c.campaign)
    capital = next((tiles[r] for r in towns_of(c, mod, c.split_of) if tiles.get(r)), (0, 0))
    keep = {c.said.get("near"), c.said.get("far")}
    cands = [r for r in towns_of(c, mod, "slave") if r not in keep and tiles.get(r)]
    if not cands:
        raise Skip("no rebel town left to give %s" % c.split_of)
    region = max(cands, key=lambda r: abs(tiles[r][0] - capital[0]) + abs(tiles[r][1] - capital[1]))
    c.said["split_far"] = region
    plan = Plan(mod, "town", region, {})
    MT.apply(plan, c.campaign, {"population": {region: 2600}, "owners": {region: c.split_of},
                                "level_follows": True})
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


@step("Map: an army placed for another faction ({other}), its leader made a general ('Make him a general')",
      "a new army next to {other}'s town, led by a general with his own name and the faction's bodyguard")
def s_map(c, mod):
    from .edit import bodyguard_unit, first_units, map_changes
    region = towns_of(c, mod, c.other)[0]
    free = mod.free_tile(c.campaign, region, taken_tiles(c, mod))
    if not free:
        raise Skip("no free tile")
    units = first_units(mod, c.campaign, c.other, "army", free)
    guard = bodyguard_unit(mod, c.campaign, c.other)
    if guard:
        units = [guard] + [u for u in units if u != guard]
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


@step("...the new town CE_Newtown gets a garrison of {new}'s own units (it stood empty)",
      "CE_Newtown holds an army of {new}")
def s_region_garrison(c, mod):
    from . import masstown as MT
    town = next((t for t in MT.towns(mod, c.campaign) if t["region"] == "CE_Newland"), None)
    if town is None:
        raise Skip("no CE_Newland (the step before was skipped)")
    units = MT.random_garrison(MT.town_pool(mod, town, MT.garrison_pool(mod, c.new)), 2, 3, None, c.rng)
    if not units:
        raise Skip("no unit %s may have there" % c.new)
    plan = Plan(mod, "towns", "CE_Newland", {})
    MT.apply(plan, c.campaign, {"garrisons": {"CE_Newland": units}})
    return plan


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


FAITH_LEVELS = ("shrine", "temple", "abbey", "cathedral", "great_cathedral")


def faith_symbol(path):
    """The test religion's own symbol, made here so it is told apart at once in the game: a bright magenta disc
    with a yellow star (False without Pillow - the template's symbol is copied then)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    import math
    im = Image.new("RGB", (64, 64), (40, 0, 40))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 61, 61), fill=(230, 0, 200), outline=(255, 255, 255), width=4)
    pts = [(32 + (26 if k % 2 == 0 else 11) * math.sin(math.pi * k / 5),
            32 - (26 if k % 2 == 0 else 11) * math.cos(math.pi * k / 5)) for k in range(10)]
    d.polygon(pts, fill=(255, 230, 0))
    im.save(path)
    return True


@step("Religions (Medieval II, Barbarian Invasion): a new religion 'Test Faith' in every file, with its own symbol "
      "(a magenta disc, a yellow star) and its own temples (Christianity's church chain copied: ce_faith_shrine ...); "
      "Medieval II: {new} follows it, a region's shares changed; Barbarian Invasion: a new belief (its pips and texts)",
      "'Test Faith' with the magenta star in the region's religion bar (Medieval II) / a town's beliefs once its "
      "Test Faith shrine stands (Barbarian Invasion); {new}'s towns can build the Test Faith shrine")
def s_religion(c, mod):
    import tempfile
    from . import religions as RL
    from .regionedit import apply_opts
    names = RL.names(mod)
    if not names:
        raise Skip("plain Rome has no religions (Barbarian Invasion's beliefs and Medieval II's religions do)")
    plan = Plan(mod, None, "religion")
    if RL.beliefs_path(mod):                     # Barbarian Invasion: a belief, its pips and texts, its temples
        with tempfile.TemporaryDirectory() as d:
            pic = os.path.join(d, "ce_faith.png")
            spec = {"name": "ce_faith", "shown": "Test Faith", "picture": pic if faith_symbol(pic) else None,
                    "pip_from": "christianity" if "christianity" in names else names[0]}
            apply_opts(plan, c.campaign, {"new_religions": [spec]})
        faith_temples(plan, c.new)
        return plan
    with tempfile.TemporaryDirectory() as d:
        pic = os.path.join(d, "ce_faith.png")
        spec = {"name": "ce_faith", "shown": "Test Faith", "pip_from": names[0],
                "picture": pic if faith_symbol(pic) else None, "factions": [c.new]}
        region = (towns_of(c, mod, c.new) or towns_of(c, mod, c.edited))[0]
        apply_opts(plan, c.campaign, {"new_religions": [spec], "religions": {
            region: dict({n: 0 for n in names}, **{names[0]: 60, "ce_faith": 40})}})
    faith_temples(plan, c.new)
    return plan


def faith_temples(plan, faction):
    """The test religion's temples: a copy of the template religion's town temple chain (temple_catholic in
    Medieval II) under temple_ce_faith, its levels ce_faith_*, its 'religion' line naming ce_faith, no conversion to
    the castle chain, built by `faction` only, named 'Test Faith ...'."""
    from .editors import building_blocks, copy_building, fields
    from .textio import strip_comment
    f = plan.edit(plan.mod.file("edb"))
    chain, faith = ("temple_catholic", "catholic")       # Medieval II; Barbarian Invasion: the Christian churches
    if not any(b[0] == chain for b in building_blocks(f)):
        chain, faith = ("temple_church_christianity", "christianity")
    src = next((b for b in building_blocks(f) if b[0] == chain), None)
    if src is None:
        plan.warn(f, "no temple_catholic / temple_church_christianity chain - the test religion gets no temples of "
                     "its own")
        return
    levels = next((fd.value.split() for fd in fields(f, src[1], src[2]) if fd.key == "levels"), [])
    names = {old: "ce_faith_" + FAITH_LEVELS[min(i, len(FAITH_LEVELS) - 1)] + ("" if i < len(FAITH_LEVELS) else
                                                                                   "_%d" % i)
             for i, old in enumerate(levels)}
    texts = {new: {"name": "Test Faith " + new[9:].replace("_", " "),
                   "desc": "A temple of the editor's test religion - built here, the religion works.",
                   "desc_short": "Test Faith temple"} for new in names.values()}
    copy_building(plan, chain, "temple_ce_faith", names, texts=texts, factions=[faction])
    b = next(b for b in building_blocks(f) if b[0] == "temple_ce_faith")
    for i in range(b[2] - 1, b[1] - 1, -1):
        t = strip_comment(f.text(i)).split()
        if t[:2] in (["religion", faith], ["religious_belief", faith]):
            f.set(i, f.text(i).replace(faith, "ce_faith", 1))
        elif t[:1] == ["convert_to"] and len(t) == 2:
            f.delete(i, i + 1)        # no conversion into the Christian castle chain (nor its levels' 'convert_to N')
    plan.note(f, "temple_ce_faith: the Test Faith's temples (a copy of %s)" % chain)


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
    AD.plan_install(plan, a, AD.read_settings(a, a.template()), mod, mark=SM.TEST_MARK)
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
    s = {"colours": [c.colours[c.new][0], c.colours[c.new][1], (240, 240, 240)],
         "pattern": "three stripes, upright (tricolour)"}
    if c.m2:
        from . import banners_m2 as BM
        ps = [p for p in pics if (p.get("extra") or {}).get("kind") == "banner" and BM.faction_sheet(p["path"])]
        sheet = BM.sheet_blank(mod)
        if not ps or sheet is None:
            raise Skip("no banner sheet")
        kit = BM.Kit(sheet, BM.meshes(mod))
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
    src, src_of = R.guess_source(mod, c.new, items, R.faction_colours(mod))
    plan = Plan(mod, "recolour", c.new, {})
    R.plan_recolour(plan, items, src, c.colours[c.new], src_of)
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


@step("Map editor (no faction picked): an army of {other} moved and its units changed",
      "{other}'s army on its new tile with a unit more")
def s_map_any(c, mod):
    from .edit import map_changes
    from .start import unit_name
    from .textio import tokens
    s = _strat(mod, c.campaign)
    towns = set(mod.city_tiles(c.campaign).values())
    army = next((ch for ch in s.faction(c.other).characters if ch.xy and tuple(ch.xy) not in towns and
                 any(tokens(l)[:1] == ["unit"] for l in s.lines[ch.start:ch.end])), None)
    if army is None:
        raise Skip("%s has no army outside its towns" % c.other)
    to = free_land(c, mod, army.xy, army.kind, True)
    if not to:
        raise Skip("no free tile next to %s's army" % c.other)
    now = [unit_name(l) for l in s.lines[army.start:army.end] if tokens(l)[:1] == ["unit"]]
    units = (now[1:] if army.named else now) + now[-1:]
    plan = Plan(mod, "map", "map", {})
    map_changes(plan, c.campaign, {"army_units": {c.other: [{"name": army.name, "from": army.xy, "units": units}]},
                                   "moves": {c.other: [{"name": army.name, "from": army.xy, "to": to}]}})
    return plan


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
    AD.plan_install(plan, a, AD.read_settings(a, a.template()), mod, mark=SM.TEST_MARK)
    return plan


@step("Add-on: Avoid Growth installed (REX / M2EX)",
      "the settlement scroll of your town has the game's own tick 'Avoid Growth': tick it, end a few turns - the town "
      "never grows past the people it had; recruit there - it shrinks, then grows back up to that ceiling")
def s_addon_growth(c, mod):
    from . import addons as AD
    a = next((x for x in AD.library() if x.key == "avoid_growth"), None)
    if a is None:
        raise Skip("the add-on is not in the library")
    plan = Plan(mod, "addon", "avoid_growth", {})
    AD.plan_install(plan, a, AD.read_settings(a, a.template()), mod, mark=SM.TEST_MARK)
    return plan


COND_SCRIPT = "ce_test_conditions.nut"
# the forms of one game condition tried once (the engines' parser refused 'I_TurnNumber >= 1' thousands of times in
# the tester's runs, also with a line end): the docs' own sample form first - the log shows which form it takes
COND_FORMS = ["I_TurnNumber > 0", "I_TurnNumber >= 1", "I_TurnNumber > 0\\n", "I_TurnNumber > 0 ",
              "Condition I_TurnNumber > 0", "not I_TurnNumber < 1", "I_TurnNumber > 0 and I_TurnNumber < 100000",
              "FactionIsLocal", "IsFactionAIControlled"]
COND_NUT = r"""// @title CE Test game conditions
// @summary The editor's test mod: at the player's first turn tries one game condition in several forms through
// @summary game.evaluateCondition, each written to the game's log as [CE_CONDITIONS] before and after - a form
// @summary the engine cannot read shows its 'Condition parser' line between them. Does nothing outside the test mod.
local PREFIX = "[CE_CONDITIONS] "
local FACTION = "%(faction)s"
local FORMS = [%(forms)s]
local done = false

local function log(message) {
    println(PREFIX + message)
}

local function test_mod() {
    local n = 0
    try {
        n = ::game.factionCount()
    } catch (err) {
        return false
    }
    for (local i = 0; i < n; i++) {
        try {
            if (::game.faction(i).name == FACTION) {
                return true
            }
        } catch (err) {
        }
    }
    return false
}

local function player(f) {
    try {
        return f != null && f.isPlayerControlled
    } catch (err) {
    }
    return false
}

local function probe(e) {
    if (done) {
        return
    }
    local f = null
    try {
        f = e.faction
    } catch (err) {
    }
    if (!player(f)) {
        return
    }
    done = true
    if (!test_mod()) {
        log("not the test mod (no faction " + FACTION + ") - nothing done")
        return
    }
    foreach (i, line in FORMS) {
        log("form " + (i + 1) + " tried: '" + line + "'")
        local r = null
        try {
            r = ::game.evaluateCondition(line)
        } catch (err) {
            log("form " + (i + 1) + " refused: " + err)
            continue
        }
        log("form " + (i + 1) + " gave: " + r + " (" + typeof(r) + ")")
    }
}

try {
    ::events.on("FactionTurnStart", probe)
} catch (err) {
    log("events.on(FactionTurnStart) failed: " + err)
}
log("module loaded")
"""


@step("Module builder: five modules made of blocks put in (REX / M2EX) - money and a message on turn 2, loot for "
      "every town taken, one of the engines' own lines (an engine event, a remembered number, a console and a "
      "campaign-script command), the control blocks (FOR EACH town, NOT, ELSE) and a game condition; plus a script "
      "trying the game condition in several forms",
      "on turn 2 (the first turn after, if it was missed) your treasury gets 1000 denarii and the game's message "
      "scroll 'The Module builder works' shows; take a town: 1500 denarii of loot; at the end of your first turn each "
      "of your towns gives 10 denarii once; on turn 2 each of your towns but the capital gets 100 people ONCE and the "
      "capital a [CE_TEST_CONTROL_BLOCKS] 'ELSE' log line; the game's log has [CE_TEST_MODULE], "
      "[LOOT_FOR_TAKING_A_TOWN], [CE_TEST_ENGINE_LINES] ('the number ce_seen_<town> is now 1', 'add_money ...', "
      "'set_event_counter ...'), [CE_TEST_GAME_CONDITION] and [CE_CONDITIONS] lines (which form of a game condition "
      "the engine reads: a 'Condition parser' line right after a 'tried' line = that form is refused)")
def s_module(c, mod):
    import tempfile
    import types as _types
    from . import addons as AD, modbuilder as MB
    test = MB.new_recipe("CE Test module")
    test.update({"when": "player_turn", "once": True,
                 "ifs": [MB.item("if", "turn", op=">=", v=2)],
                 "dos": [MB.item("do", "money", amount=1000, to="this"),
                         MB.item("do", "message", title="The Module builder works",
                                 body="CE_Test: a module made of blocks (no code) gave you 1000 denarii."),
                         MB.item("do", "log", text="{faction}: the test module acted on turn {turn}")],
                 "settings": {"dos.0.amount": "Money given"}})
    lines = MB.new_recipe("CE Test engine lines")
    lines.update({"when": "ev:SettlementTurnEnd",
                  "ifs": [MB.item("if", "counter", name="ce_seen_{town}", op="<", v=1)],
                  "dos": [MB.item("do", "counter_add", v=1, name="ce_seen_{town}"),
                          MB.item("do", "console", text="add_money {faction} 10"),
                          MB.item("do", "script", text="set_event_counter ce_test_engine_lines 1"),
                          MB.item("do", "log", text="{town}: counted once, 10 denarii")]})
    ctl = MB.new_recipe("CE Test control blocks")
    cap = MB.item("if", "capital")
    cap["not"] = True
    # the player's turn only, turn 2 only: on 'every faction's turn starts' and 'turn >= 2' the towns got +100 about
    # 20 times a turn and every turn after (the tester's vanilla Rome run of 0.32.0)
    ctl.update({"when": "player_turn", "each": "town", "each_of": "player", "match": "all",
                "ifs": [MB.item("if", "turn", op="==", v=2), cap],
                "dos": [MB.item("do", "people", amount=100),
                        MB.item("do", "log", text="{town}: FOR EACH town, not the capital - 100 people")],
                "else": [MB.item("do", "log", text="{town}: ELSE (the capital, or not turn 2)")]})
    # the game condition by itself, once a turn until it holds (it was on every town's turn end: thousands of
    # 'Condition parser' lines when the engine refused it)
    cond = MB.new_recipe("CE Test game condition")
    cond.update({"when": "player_turn", "once": True,
                 "ifs": [MB.item("if", "game", line=COND_FORMS[0])],
                 "dos": [MB.item("do", "log", text="the game condition '%s' held on turn {turn}" % COND_FORMS[0])]})
    plan = Plan(mod, "addon", "ce_test_module", {})
    with tempfile.TemporaryDirectory() as d:          # the editor's own add-ons list is left as it is
        for r in (test, MB.fit_to_mod(MB.example("Loot for taking a town"), mod), lines, ctl, cond):
            # they lie in the GAME's script/modules: in any other campaign of that game they do nothing (a tester's
            # plain campaign got the test's +100 people in every town)
            r["only_with"] = c.new
            bad = MB.problems(r, mod)
            if bad:
                raise ValueError("; ".join(bad))
            text = MB.script(r)
            p = os.path.join(d, MB.key_of(r["title"]) + ".nut")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
            a = AD.from_script(text, os.path.basename(p), p)
            AD.plan_install(plan, a, AD.read_settings(a, text), mod, mark=SM.TEST_MARK)
    forms = ", ".join('"%s"' % f for f in COND_FORMS)
    text = COND_NUT % {"faction": c.new, "forms": forms} + SM.TEST_MARK + "\n"
    plan.binary(AD.target(mod, _types.SimpleNamespace(file=COND_SCRIPT)), text.encode("utf-8"))
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
    # a storm strikes only at sea: the sea tile nearest the town (the tester's storm on the town's land never came)
    sea = next((p for d in range(1, 80) for p in ((x + dx, y + dy) for dx in range(-d, d + 1) for dy in range(-d, d + 1))
                if mod.is_sea(c.campaign, p)), (x, y))
    ch = {"new": [{"kind": k, "name": "ce_test_" + k, "date": EV.turn_date(mod, c.campaign, t),
                   "position": list(sea) if k == "storm" else [x, y]}
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


# every campaign rule changed (s_rules_all): what is left as it is, and why
BYTE_TOPS = (127, 255, 32767, 65535)            # the most a byte / a short holds: a limit there is not raised
UNIT_SIZES_LEFT = "the game's options keep their unit size choice only with these numbers as they are"
RULES_LEFT = {
    "start_date": "the events and the campaign script count from it",
    # a tester in Medieval II: the years jumped +2 / +3 a turn (2.00 -> 1.90) and the turn counter showed the year
    "timescale": "the test's events are put on turns by it (turn 2, 4...), and a part of a year makes the years jump "
                 "unevenly",
    "show_date_as_turns": "the turn counter keeps showing turns, as the game has it",
    "disable_console": "the console stays on - add-ons are looked at through it",
    "faction_unlock": "'earned' would hide the test's new factions from the faction list",
    "portrait_pool": "'isolated' takes the game's portraits away from a mod with none of its own",
    "sprite_format": "names the files the engine loads - another value needs other files",
    "marian_reforms_disabled": "kept with its pair marian_reforms_activated",
}


def rule_changed(rule, now=None):
    """(the new text of a campaign rule, None) - a value of its own kind the game takes, every number moved a step
    the same way so their order holds (a level's minimum stays under its maximum) - or (None, why it is left)."""
    import re
    v, key = rule.value.strip(), rule.key
    if key in RULES_LEFT:
        return None, RULES_LEFT[key]
    if os.path.basename(rule.path or "").lower() == "descr_unit_sizes.txt":
        # the user's test mod in Rome with REX: with 0.475 / 0.95 / 1.9 / 3.8 the game's options lost the
        # unit size choice
        return None, UNIT_SIZES_LEFT
    if key.endswith("_source"):
        return None, "names the files the engine loads - another value needs other files"
    # a range only widens: a maximum or limit goes up, a minimum (and any other number) down - so the towns, families
    # and armies the campaign already has still fit (a village's max 1500 -> 1499 lost a town of 1500 people; the
    # children's max 5 -> 4 a family of five)
    words = set(re.split(r"[_\s.]+", key.lower()))
    # the age of manhood too: lower, the campaign's 15-year-old sons off the map are men the game refuses (a tester in
    # Rome with REX: 'Ahmose is a live male of age > 15 and so must be created as a named character')
    up = bool(words & {"max", "maximum", "limit", "cap", "manhood"})
    if rule.kind in ("int", "uint"):
        n = int(v)
        if up and n not in BYTE_TOPS:
            return str(n + 1), None
        return str(n - 1 if n > 0 else n + 1 if n < 0 else 1), None
    if rule.kind == "float":
        x = float(v)
        # a share (0 - 1) or a percent (0 - 100) already at its top goes down instead: M2EX clamps it ('attribute
        # float (1.05) of tag max_heretics_conversion_modifier outside specified range (0, 1)', 'float (105) of tag
        # max_bribe_chance outside specified range (0, 100)' - a tester's test mod)
        if up and x in (1.0, 100.0):
            up = False
        y = (x * 1.05 if up else x * 0.95) if x else 0.05
        text = ("%.10f" % y).rstrip("0")             # plain decimals, as the files write them (0.000095, 95.0)
        return text + "0" if text.endswith(".") else text, None
    if rule.kind == "bool":
        return ({"true": "false", "false": "true"}.get(v), None) if v in ("true", "false") else \
            (None, "not true / false")
    if rule.kind == "flag":
        if key == "marian_reforms_activated" and (now or {}).get("marian_reforms_disabled") == "on":
            return None, "the Marian reforms are switched off in this campaign"
        return ("off" if v == "on" else "on"), None
    if rule.kind == "date":
        m = re.fullmatch(r"(-?\d+)(.*)", v)
        return (str(int(m.group(1)) + 2) + m.group(2), None) if m else (None, "not a date")
    if rule.kind == "words":
        nums = v.split()
        if not all(re.fullmatch(r"-?\d+", x) for x in nums):
            return None, "words the engine reads as they are"
        n = [int(x) for x in nums]
        if key == "random_persona_weights":            # odds that make 100 together: one moved from the biggest
            big = n.index(max(n))
            low = n.index(min(n))
            if big != low:
                n[big] -= 1
                n[low] += 1
        else:                                          # a colour (0 - 255 each) or other numbers
            n = [x - 1 if x > 0 else x + 1 for x in n]
        return " ".join(str(x) for x in n), None
    if rule.kind == "string" and rule.note:            # an engine switch: another of the values its comment names
        names = re.findall(r"^\s*([a-z_]+)\s*[=:]\s", rule.note, re.M)
        other = next((x for x in names if x != v), None)
        if other is None and v in ("enabled", "disabled"):
            other = "disabled" if v == "enabled" else "enabled"
        if other:
            return other, None
    return None, "a name (a settlement level, a file) the game must know - left as it is"


@step("Campaign rules - every one: each value of every settings file changed (numbers a step, switches turned, "
      "the engines' options) - the game must read them all",
      "the campaign starts and plays; Campaign rules shows the new values")
def s_rules_all(c, mod):
    from . import campaignrules as CR
    plan = Plan(mod, "rules", "rules_all", {})
    changed, files, left = 0, 0, {}
    for name, title, own, base in CR.files(mod, c.campaign):
        rules = CR.read(own or base, medieval2=c.m2)
        now = {r.key: r.value for r in rules}
        ch = {}
        for r in rules:
            if CR.blocked(r):
                left.setdefault("greyed out in Campaign rules - a change broke the game in a test", []).append(r.key)
                continue
            new, why = rule_changed(r, now)
            if new is not None and new != r.value and CR.check(r, new) is None:
                ch[r] = new
            else:
                left.setdefault(why or "no other value", []).append(r.key)
        if ch:
            CR.apply(plan, name, ch, own, base)
            changed += len(ch)
            files += 1
    if not changed:
        raise Skip("no campaign settings file")
    plan.warn(None, "%d rules changed in %d files" % (changed, files))
    for why, keys in sorted(left.items(), key=lambda x: -len(x[1])):
        plan.warn(None, "left as they are (%s): %s" % (why, ", ".join(sorted(set(keys))[:8]) +
                                                       (" ..." if len(set(keys)) > 8 else "")))
    return plan


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


@step("Art: every picture of {later} replaced (each one the Art tab offers, but the 3D figures' textures)",
      "{later}'s pictures (buttons, loading screen, banners, cards...) are the test picture once it comes in; its "
      "figures on the campaign map look as the template's, in its colours")
def s_art_all(c, mod):
    from . import factionart as FA
    from .edit import edit
    # not the 3D models' textures (the campaign map figures, the 3D symbol): the test picture laid over a model's
    # unfolded skin made solid green figures on the map in the game - the recolour steps test those
    if c.later not in {n for n, _ in mod.factions()}:
        raise Skip("%s was not made (the step that makes it was skipped)" % c.later)
    pics = [p for p in FA.faction_pictures(mod, c.campaign, c.later) if not p.get("locked") and p.get("size")
            and not p.get("rel", "").startswith("models_strat/")]
    if not pics:
        raise Skip("no pictures of its own")
    return edit(mod, c.campaign, c.later, {"art": {FA.picture_target(p, c.later, c.later): logo(c) for p in pics}})


@step("Map editor: a rebel town deleted with its region (its land to a neighbour, every file that ties them)",
      "{gone} is not on the map any more: its land is {gone_into}'s, its rebels and mercenary pool entries gone")
def s_delete_region(c, mod):
    from . import regiondelete as RD
    keep = {c.said.get("near"), c.said.get("far"), c.said.get("split_far")}
    tiles = mod.city_tiles(c.campaign)
    capital = next((tiles[r] for r in towns_of(c, mod, c.new) if tiles.get(r)), (0, 0))
    cands = [r for r in towns_of(c, mod, "slave") if r not in keep and tiles.get(r)]
    # the farthest from the test faction's capital, so nothing of the test faction stands near it
    for r in sorted(cands, key=lambda r: -(abs(tiles[r][0] - capital[0]) + abs(tiles[r][1] - capital[1]))):
        if not RD.problems(mod, c.campaign, r)[0]:
            plan = Plan(mod, "delete", r, {})
            c.said["gone"] = r
            c.said["gone_into"] = RD.delete(plan, c.campaign, r)
            return plan
    raise Skip("no rebel town that can go (each is named by a campaign script, an event or is an island)")



@step("Scripts in the game: the tooltip of Avoid Growth's tick changed in the script the test mod put in "
      "(REX / M2EX)",
      "the settlement scroll's tick (still 'Avoid Growth') shows '{label}' under the mouse; afterwards Add-ons > Scripts in the game... lists every script the "
      "test mod put into the game's script/modules and takes them all out with one press")
def s_scripts(c, mod):
    s = next((x for x in SM.scripts(mod) if x.test and x.file.lower() == "avoid_growth.nut"), None)
    if s is None:
        raise Skip("Avoid Growth is not in the game's script/modules (its step did not write)")
    c.said["label"] = "Keep the town at the size it has now (changed by the test mod)"
    values = dict(s.values, AG_TIP=c.said["label"])
    plan = Plan(mod, "scripts", "avoid_growth", {})
    if not SM.plan_settings(plan, s, values):
        raise Skip("the words were already set")
    return plan


ABOARD_SCRIPT = "ce_test_aboard.nut"
ABOARD_NUT = r"""// @title CE Test army aboard
// @summary The editor's test mod: at the campaign start puts %(army)s (an army of %(faction)s on the shore beside its
// @summary fleet) aboard the fleet of %(fleet)s - the engine way (REX / M2EX); descr_strat.txt has no form for an
// @summary army aboard. Each way tried is written to the game's log as [CE_ABOARD]. Does nothing elsewhere.
local PREFIX = "[CE_ABOARD] "
local FACTION = "%(faction)s"
local ARMY = "%(army)s"
local FLEET = "%(fleet)s"
local done = false

local function log(message) {
    println(PREFIX + message)
}

local function get(o, field) {
    if (o == null) {
        return null
    }
    try {
        return o[field]
    } catch (err) {
    }
    return null
}

local function named(ch, name) {
    foreach (o in [ch, get(ch, "record"), get(ch, "characterRecord")]) {
        foreach (f in ["name", "fullName", "shortName"]) {
            local n = get(o, f)
            if (n != null && typeof(n) == "string" && n.indexof(name) != null) {
                return true
            }
        }
    }
    return false
}

local function board(...) {
    if (done) {
        return
    }
    local fac = null
    local n = 0
    try {
        n = ::game.factionCount()
    } catch (err) {
        return
    }
    for (local i = 0; i < n; i++) {
        local f = null
        try {
            f = ::game.faction(i)
        } catch (err) {
        }
        if (get(f, "name") == FACTION) {
            fac = f
        }
    }
    if (fac == null) {
        return
    }
    done = true
    local army = null
    local navy = null
    local cn = get(fac, "characterCount") || 0
    for (local i = 0; i < cn; i++) {
        local ch = null
        try {
            ch = fac.character(i)
        } catch (err) {
        }
        if (army == null && named(ch, ARMY)) {
            army = get(ch, "army")
        } else if (navy == null && named(ch, FLEET)) {
            navy = get(ch, "army")
        }
    }
    if (army == null || navy == null) {
        log("the army (" + ARMY + ") or the fleet (" + FLEET + ") not found - nothing tried")
        return
    }
    local ways = [
        ["army.transportingNavy = fleet", function() { army.transportingNavy = navy }],
        ["fleet.transportedArmy = army", function() { navy.transportedArmy = army }]]
    foreach (w in ways) {
        try {
            w[1]()
        } catch (err) {
            log(w[0] + " refused: " + err)
            continue
        }
        local on = get(army, "transportingNavy") != null || get(navy, "transportedArmy") != null
        log(w[0] + (on ? " - the army is aboard" : " - taken, but the army is not aboard"))
        if (on) {
            return
        }
    }
}

local function listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        log("events.on(" + name + ") failed: " + err)
    }
}

listen("FactionTurnStart", board)
log("module loaded")
"""


@step("Experiment: a copy of {new}'s army on the shore beside its fleet, put aboard at the start by an engine "
      "script (REX / M2EX) - descr_strat.txt has no form for an army aboard (an army on the fleet's sea tile stops "
      "the file there)",
      "{aboard} is aboard the fleet once the campaign starts (the log's [CE_ABOARD] lines say which way worked); "
      "else he stands on the shore beside it")
def s_aboard(c, mod):
    import types as _types
    from . import addons as AD
    from .limits import engine_of
    from .scriptmods import TEST_MARK
    from .start import _set_xy
    from .textio import strip_comment
    from .strat import Strat
    if not engine_of(mod):
        raise Skip("only an engine script (REX / M2EX) can put an army aboard - the original exes cannot")
    path = mod.campaign_file(c.campaign, "descr_strat.txt")
    plan = Plan(mod, "aboard", c.new, {})
    f = plan.edit(path)
    s = Strat(f)
    fb = s.faction(c.new)
    if fb is None:
        raise Skip("%s is not in descr_strat.txt" % c.new)
    fleet = next((ch for ch in fb.characters if ch.kind == "admiral" and ch.xy), None)
    army = next((ch for ch in reversed(fb.characters) if ch.kind in ("general", "named character") and ch.xy
                 and any(strip_comment(t).split()[:1] == ["unit"] for t in f.texts()[ch.start + 1:ch.end])), None)
    if fleet is None or army is None:
        raise Skip("%s has no fleet or no army to copy" % c.new)
    taken = taken_tiles(c, mod)
    fx, fy = fleet.xy
    shore = next((p for d in (1, 2) for p in ((fx + dx, fy + dy) for dx in range(-d, d + 1) for dy in range(-d, d + 1))
                  if p not in taken and not mod.tile_problem(c.campaign, p, "general", True, taken)), None)
    if shore is None:
        raise Skip("no free land beside %s's fleet" % c.new)
    name = free_names(c, mod, c.new, 6)[-1]
    lines = f.texts()[army.start:army.end]
    lines[0] = _set_xy(lines[0].replace(army.name, name, 1), shore)
    f.insert(fleet.end, lines)
    c.said["aboard"] = name
    plan.note(f, "%s (a copy of %s's army) put on the shore at %d, %d beside the fleet of %s" % (
        name, army.name, shore[0], shore[1], fleet.name))
    text = ABOARD_NUT % {"faction": c.new, "army": name, "fleet": fleet.name} + TEST_MARK + "\n"
    plan.binary(AD.target(mod, _types.SimpleNamespace(file=ABOARD_SCRIPT)), text.encode("utf-8"))
    return plan


# the three ways a modder's own building can stand on the campaign map (rules.md 'Own buildings / models'), each
# with a model of the game's own copied under a new name so the three look different: (game, route) -> model
SPECIAL_MODELS = {("rome", "resource"): "resource_lion.cas", ("rome", "engine"): "wonder_pyramids.cas",
                  ("medieval2", "resource"): "resource_elephants.cas", ("medieval2", "engine"): "volcano_rock.cas"}
SPECIAL_TYPE = "ce_test_special"
SPECIAL_ENGINE = "ce_test_special_engine.cas"
SPECIAL_SCRIPT = "ce_test_special_models.nut"


def _special_model(mod, route):
    from .packs import game_kind
    name = SPECIAL_MODELS[("rome" if game_kind(mod) != "medieval2" else "medieval2", route)]
    return mod.find("models_strat/" + name)


@step("Own buildings on the map 1/2: a new resource type '%s' with its own model (a copy of one of the game's) - "
      "new resource types take REX / M2EX" % SPECIAL_TYPE,
      "nothing to see yet - the next step puts it on the map")
def s_special_type(c, mod):
    from .editors import set_text_values
    from .moddata import _ci
    from .resources import types
    from .limits import engine_of
    if not engine_of(mod):                  # RomeTW.exe / medieval2.exe: 'dont recognise this resource type'
        raise Skip("a new resource type needs REX or M2EX - the original exe refuses unknown types")
    if SPECIAL_TYPE in types(mod):
        raise Skip("there already")
    src = _special_model(mod, "resource")
    res = mod.file("resources")
    if not src or not res:
        raise Skip("no model to copy or no descr_sm_resources.txt")
    plan = Plan(mod, "special", SPECIAL_TYPE, {})
    f = plan.edit(res)
    cur, block = False, []
    for t in f.texts():                                 # the elephants' block as the pattern (both games have it)
        w = strip_comment(t).split()
        if w[:1] == ["type"]:
            if cur:
                break
            cur = w[1:2] == ["elephants"]
        if cur and w:
            block.append(t)
    if not block:
        raise Skip("no elephants resource to copy")
    rel = "data/models_strat/%s.cas" % SPECIAL_TYPE
    out = []
    for t in block:
        w = strip_comment(t).split()
        if w[:1] == ["type"]:
            t = t.replace("elephants", SPECIAL_TYPE, 1)
        elif w[:1] == ["item"] and len(w) > 1:
            t = t.replace(w[1], rel, 1)
        elif w[:1] == ["has_mine"]:
            continue
        out.append(t)
    at = len(f.raw) - 1 if f.raw and f.raw[-1] in ("", "\r") else len(f.raw)   # before the file's last line end
    f.insert(at, [""] + [x for x in out if x.strip()])
    plan.copy(src, os.path.join(mod.data, "models_strat", SPECIAL_TYPE + ".cas"))
    strat = _ci(os.path.join(mod.data, "text"), "strat.txt") or mod.text_file("strat.txt")
    if strat and strat.lower().endswith(".txt"):         # Rome names resources SMT_RESOURCE_<TYPE> in strat.txt
        set_text_values(plan, strat, {"SMT_RESOURCE_" + SPECIAL_TYPE.upper(): "Test Special Building"})
    plan.note(f, "%s: a new resource type (a copy of elephants with the model %s)" % (SPECIAL_TYPE,
                                                                                    os.path.basename(src)))
    return plan


SPECIAL_NUT = r"""// @title CE Test special models
// @summary The editor's test mod: draws a model of the game's own (copied as %(model)s) beside ce_test's capital
// @summary at %(x)d, %(y)d - the engine way (REX / M2EX) of putting a building's model on the map. Does nothing in
// @summary a campaign without the faction ce_test.
local PREFIX = "[CE_SPECIAL] "
local MODEL = "data/models_strat/%(model)s"
local MODEL_ID = 9177
local AT_X = %(x)d
local AT_Y = %(y)d
local done = false

local function log(message) {
    println(PREFIX + message)
}

local function get(o, field) {
    if (o == null) {
        return null
    }
    try {
        return o[field]
    } catch (err) {
    }
    return null
}

local function has_test_faction() {
    local n = 0
    try {
        n = ::game.factionCount()
    } catch (err) {
        return false
    }
    for (local i = 0; i < n; i++) {
        local f = null
        try {
            f = ::game.faction(i)
        } catch (err) {
        }
        if (get(f, "name") == "ce_test") {
            return true
        }
    }
    return false
}

// the argument order of models.add / drawAt is not in the engines' strings: each way is tried, the one that works
// is written to the game's log
local function try_calls(label, calls) {
    foreach (i, call in calls) {
        try {
            local r = call()
            log(label + ": way " + i + " worked (answer " + (r == null ? "null" : r.tostring()) + ")")
            return true
        } catch (err) {
            log(label + ": way " + i + " refused: " + err)
        }
    }
    return false
}

local function draw(...) {
    if (!has_test_faction()) {
        return
    }
    local models = get(::game, "models")
    if (models == null) {
        log("no game.models in this engine - the engine way cannot draw")
        return
    }
    if (!try_calls("models.add", [
            function() { return models.add(MODEL, MODEL_ID) },
            function() { return models.add(MODEL_ID, MODEL) },
            function() { return models.add(MODEL, MODEL_ID, false) }])) {
        return
    }
    try_calls("models.drawAt", [
        function() { return models.drawAt(MODEL_ID, AT_X, AT_Y) },
        function() { return models.drawAt(AT_X, AT_Y, MODEL_ID) }])
    done = true
}

local function listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        log("events.on(" + name + ") failed: " + err)
    }
}

listen("FactionTurnStart", function(...) { if (!done) { draw() } })
listen("GameReloaded", function(...) { done = false; draw() })
log("module loaded")
"""


@step("Own buildings on the map 2/2: three ways side by side beside {new}'s capital - a wonder of the game's own "
      "(Rome), the new resource type with its own model, and a model drawn by an engine script (REX / M2EX)",
      "near {new}'s capital: {special_wonder}a lion / elephants model = the resource way (hover: its name only), "
      "{special_engine} = the engine way (the log's [CE_SPECIAL] lines say which call worked); the new resource's hover "
      "text is the copied type's name (Medieval II keeps resource names in its compiled strat.txt.strings.bin)")
def s_special(c, mod):
    import types as _types
    from . import addons as AD, forts as FT, resources as RS
    from .scriptmods import TEST_MARK
    from .strat import Strat
    tiles = mod.city_tiles(c.campaign)
    cap = next((tiles[r] for r in towns_of(c, mod, c.new) if tiles.get(r)), None)
    if cap is None:
        raise Skip("%s has no town" % c.new)
    path = mod.campaign_file(c.campaign, "descr_strat.txt")
    f = mod.load(path)
    used = {r.xy for r in RS.read(f)} | {fo.xy for fo in Strat(f).forts}
    picked = []
    for _ in range(3):
        t = free_land(c, mod, cap, skip=used | set(picked))
        if t is None:
            raise Skip("no free land beside %s's capital" % c.new)
        picked.append(t)
    plan = Plan(mod, "special", "map", {})
    wonder = FT.landmark_types(mod)
    ch = {"added": []}
    if SPECIAL_TYPE in RS.types(mod):
        ch["added"].append({"type": SPECIAL_TYPE, "xy": picked[1]})
    if wonder:
        t = "statue" if "statue" in wonder else wonder[0]
        ch["forts"] = {"added": [{"kind": FT.LANDMARK, "type": t, "xy": picked[0]}]}
        c.said["special_wonder"] = "the %s wonder = the wonder way (double click: the game's window), " % t
    else:
        c.said["special_wonder"] = ""
    RS.apply(plan, c.campaign, ch)
    src = _special_model(mod, "engine")
    if src:
        plan.copy(src, os.path.join(mod.data, "models_strat", SPECIAL_ENGINE))
        text = SPECIAL_NUT % {"model": SPECIAL_ENGINE, "x": picked[2][0], "y": picked[2][1]} + TEST_MARK + "\n"
        plan.binary(AD.target(mod, _types.SimpleNamespace(file=SPECIAL_SCRIPT)), text.encode("utf-8"))
        c.said["special_engine"] = "the %s model at %d, %d" % (os.path.basename(src).rsplit(".", 1)[0], *picked[2])
    else:
        c.said["special_engine"] = "(no model to copy)"
    return plan

@step("Mercenaries: a new pool of one region with one mercenary unit; another pool's first unit costs 1 more",
      "{merc}")
def s_mercs(c, mod):
    from . import mercenaries as ME
    path, pools = ME.read(mod, c.campaign)
    units = ME.mercenary_units(mod)
    if not path or len(pools) < 2 or not units:
        raise Skip("no descr_mercenaries.txt with two pools, or no mercenary unit")
    region = pools[0].regions[0]
    new = ME.Pool("ce_test_pool")
    pools.append(new)
    ME.give_regions(pools, new, [region])
    new.units = [ME.Unit(units[0].type, cost="100", max_="3", initial="3")]
    u = pools[1].units[0] if pools[1].units else None
    if u is not None:
        u.cost = str(int(u.cost) + 1)
    plan = Plan(mod, "mercenaries", c.campaign, {})
    ME.plan_pools(plan, c.campaign, pools)
    c.said["merc"] = ("in %s: %s for hire (3 at the start, cost 100) - its own pool ce_test_pool%s" % (
        region, units[0].type, "; in %s %s costs %s" % (pools[1].regions[0] if pools[1].regions else pools[1].name,
                                                        u.name, u.cost) if u is not None else ""))
    return plan


@step("Rename a faction everywhere: a faction no other step uses gets the code name <name>_ce",
      "the renamed faction plays as before - its towns, units, pictures and names on screen")
def s_rename_faction(c, mod):
    from . import factionrename as FR
    used = {c.template, c.edited, c.other, c.foreign, c.new, c.later, c.split, c.shadow, "slave"}
    old = next((n for n, _ in mod.factions() if n not in used), None)
    if old is None:
        raise Skip("no faction left that no other step uses")
    taken = {n.lower() for n, _ in mod.factions()}
    new = _free_name(old + "_ce", taken)
    if FR.problems(mod, old, new):
        raise Skip(FR.problems(mod, old, new))
    plan = Plan(mod, "rename", new)
    FR.plan_rename(plan, c.campaign, old, new)
    return plan


@step("Your own files for a battle model: a unit of {edited} gets its model's texture (colours turned over, as "
      "a picture made in another program) and its model file put in as files of its own - a model of its own",
      "the unit in battle: its colours turned over (a negative); the other units of that model unchanged")
def s_own_model(c, mod):
    try:
        from PIL import ImageOps
    except ImportError:
        raise Skip("needs Pillow")
    from . import models as MO
    from .meshview import on_disk
    cat = MO.catalogue(mod)
    for u in unit_names(mod, c.edited, 80):
        lines = MO.unit_lines(mod, u)
        slots = [x for x in (MO.unit_slots(lines) if lines else []) if x[0] == "soldier"]
        info = cat.get(slots[0][2].lower()) if slots else None
        if info is None or not info.meshes or not on_disk(mod, info.meshes[0]):
            continue
        wear = c.edited if c.edited in info.textures else next((f for f in info.textures if f), None)
        im = MO.texture_image(mod, info.textures.get(wear, "")) if wear else None
        if im is None:
            continue
        pic = os.path.join(c.work, "ce_test_own_texture.png")
        ImageOps.invert(im.convert("RGB")).save(pic)
        mesh = os.path.join(c.work, "ce_test_own_model" + MO.mesh_kind(mod)[0])
        with open(on_disk(mod, info.meshes[0])[1], "rb") as fh, open(mesh, "wb") as out:
            out.write(fh.read())
        plan = Plan(mod, "own", "own", {})
        MO.own_files(plan, u, "soldier", 0, textures={wear: pic}, meshes=[mesh], name="ce_test_own_model")
        c.said["own_model"] = u
        return plan
    raise Skip("no unit of %s whose model's files are on disk" % c.edited)


@step("A unit made from nothing: 'CE Nothing Guard', horsemen who charge, for {new} - every line written new with "
      "the mod's usual numbers, its cost and men set, plain cards drawn, recruited where such units usually are",
      "the unit in the recruitment list of {new}'s stables / barracks, its plain 'CN' card; in battle it looks like "
      "the usual horsemen's model")
def s_unit_nothing(c, mod):
    from . import fromnothing as FN
    kind = "horse_melee" if FN.units_of_kind(mod, "horse_melee") else "foot_melee"
    plan = Plan(mod, "nothing", "nothing", {})
    FN.new_unit(plan, kind, "ce nothing guard", "ce_nothing_guard", [c.new],
                values={("stat_cost", 1): "999", ("soldier", 1): "30"},
                texts={"name": "CE Nothing Guard", "descr": "A unit the editor made from nothing (test mod)."},
                recruit=FN.usual_levels(mod, kind, [c.new]))
    return plan


@step("Map size: the map grown by 2 tiles of deep sea at the right and at the top (the last step - grown at the "
      "left or the bottom every place would move, and the test mod's engine scripts name tiles by number)",
      "the campaign map is 2 tiles wider and higher: open water at its right and top edges; every town, army and "
      "resource where it was; the game builds map.rwm again on the first start")
def s_map_size(c, mod):
    from .mapresize import plan_resize
    plan = Plan(mod, "map", "map_size", {})
    plan_resize(plan, c.campaign, right=2, top=2)
    return plan


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
    "Factions that come later: by an event": ["s_later", "s_later_way"],
    "Factions that come later: a shadow (civil war)": ["s_shadow"],
    "Factions that come later: splitting off in a revolt": ["s_split", "s_split_town"],
    "Resources on the map": ["s_resources"],
    "Forts, watchtowers, wonders (Rome)": ["s_forts"],
    "Town window: owner and population": ["s_town"],
    "Many towns: a building, random garrisons": ["s_masstown"],
    "Many towns: city / castle and level": ["s_city_castle"],
    "Many towns: garrisons the game's way (rebels, the town's own buildings)": ["s_garrison_kinds"],
    "Map: a town moved": ["s_move_town"],
    "Map: a port moved": ["s_port"],
    "Map: a character moved, one deleted": ["s_move_delete"],
    "Map editor: any faction's army moved, its units": ["s_map_any"],
    "Map editor: a town deleted with its region": ["s_delete_region"],
    "Map size: tiles added or cut at the edges": ["s_map_size"],
    "Mercenaries: pools of regions and their units": ["s_mercs"],
    "New region": ["s_region", "s_region_garrison"],
    "Rename a region and its town everywhere": ["s_rename"],
    "Rename a faction everywhere (Edit faction > Rename...)": ["s_rename_faction"],
    "Edit region: rebels, resources, farming, names players see": ["s_region_props"],
    "Settlement names by culture": ["s_culture_names"],
    "Terrain editor: ground and heights": ["s_terrain"],
    "Terrain editor: features and climates": ["s_features"],
    "Land and sea": ["s_coast"],
    "Family: a son": ["s_family"],
    "Family: a daughter, a man tied to no one": ["s_family_more"],
    "Character editor: traits and retinue of a character": ["s_character"],
    "Traits and retinue: a new trait": ["s_traits"],
    "Religions (Medieval II, Barbarian Invasion)": ["s_religion"],
    "Roster: give": ["s_roster", "s_roster_other"],
    "Roster: take away": ["s_roster_take"],
    "Campaign-map figures": ["s_figures"],
    "Unit editor: lines": ["s_unit_fields"],
    "Unit editor: new unit step by step": ["s_units"],
    "Unit editor: replace the battle model": ["s_model"],
    "Unit editor: your own files for a battle model (texture, model file)": ["s_own_model"],
    "Unit editor: a new unit made from nothing": ["s_unit_nothing"],
    "Unit editor: voice": ["s_voice"],
    "Building editor: lines": ["s_building_fields"],
    "Building editor: new building step by step": ["s_buildings"],
    "Bring from another mod": ["s_bring"],
    "Unit packs export / import": ["s_unit_pack"],
    "Check and install a pack": ["s_modpack"],
    "Events": ["s_events", "s_events_more"],
    "Campaign rules": ["s_rules", "s_rules_all"],
    "Campaign start (descr_strat.txt)": ["s_campaign_start"],
    "Engine settings (REX / M2EX)": ["s_engine_rules"],
    "Add-ons": ["s_addon", "s_addon_diplomacy", "s_addon_growth"],
    "Module builder": ["s_module"],
    "Experiment: an army starting aboard its fleet": ["s_aboard"],
    "Own buildings on the map: a wonder, a new resource type, an engine model": ["s_special_type", "s_special"],
    "Scripts in the game (script/modules: settings, off / on, delete, the test mod's taken out)": ["s_scripts"],
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
    "Start the game (the bottom bar)": "starts the game - tried by hand: start CE_Test with it",
    "Credits": LOOK,
    "Delete this mod's folder": "deletes for good - tried by hand on a copy (the unit test checks what it refuses)",
    "Test mod": "this run",
}

# the window's work buttons, tabs and Tools entries (the start of their text) -> the feature above
UI = {
    "New faction": "New faction", "Edit faction": "Edit faction (names, colours, money, towns, garrisons)",
    "Unit editor": "Unit editor: lines", "Building editor": "Building editor: lines",
    "Character editor": "Character editor: traits and retinue of a character",
    "Terrain editor": "Terrain editor: ground and heights", "Add-ons": "Add-ons",
    "Religions": "Religions (Medieval II, Barbarian Invasion)",
    "Faction": "Edit faction (names, colours, money, towns, garrisons)",
    "Map": "Map: a town moved", "Map editor": "Map editor: any faction's army moved, its units", "Diplomacy": "Diplomacy: feelings", "Art": "Art: replace a picture",
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
    "Module builder": "Module builder", "Credits": "Credits", "Delete this mod's folder": "Delete this mod's folder",
    # the work bar's window buttons (once Tools entries)
    "Events": "Events", "Recolour": "Recolour a faction's pictures",
    "Culture names": "Settlement names by culture", "Many towns": "Many towns: a building, random garrisons",
    "Bigger map": "Make the campaign map 3 x bigger",
    "Change size": "Map size: tiles added or cut at the edges",
    "Mercenaries": "Mercenaries: pools of regions and their units",
    "New religion": "Religions (Medieval II, Barbarian Invasion)", "Religions of a region": "Religions (Medieval II, Barbarian Invasion)",
    "Restore a backup": "Restore a backup", "Game manifest": "Settings, Help, the log, Save logs, Game manifest",
    "Log": "Settings, Help, the log, Save logs, Game manifest",
    "Save logs": "Settings, Help, the log, Save logs, Game manifest",
    "Report a bug": "Report a bug / Suggest, Answers to my reports",
    "Test mod": "Test mod",
    "Settings": "Settings, Help, the log, Save logs, Game manifest",
    "Help": "Settings, Help, the log, Save logs, Game manifest",
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
            if not line.strip().startswith("-- "):            # a 'when it bites' heading
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
             "split": c.split, "split_of": c.split_of, "shadow": c.shadow, "foreign": c.foreign,
             "addon": "Sack Settlement (Medieval II, M2EX)" if c.m2 else "Sack Settlement (Rome, REX)"}
    before = problems(ModData(data), campaign)
    results = []
    for n, (title, see_raw, fn) in enumerate(STEPS, 1):
        title, see = title.format(**names), see_raw.format_map(_Names(names, c.said))
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
        rec["see"] = see_raw.format_map(_Names(names, c.said))     # a town a step picked, named after it ran
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
           "shadow of %(new)s %(shadow)s, "
           "units moved from %(foreign)s, other %(other)s" % names,
           "%d of %d steps fine (written, no new problem in Check mod files)" % (ok, len(results)), "",
           "Start the mod in the game (its Start .bat), play a few turns and a battle, look at what each step says, "
           "then send Report a bug with the game's log ticked.",
           "Its add-ons and modules go into the GAME's script/modules (the engine runs them from there), not into "
           "CE_Test: when you throw the test mod away, Add-ons > Scripts in the game... takes them out with one "
           "press.", ""]
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
