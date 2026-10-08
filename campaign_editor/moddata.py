"""Finding a mod's files and reading what the tool needs from them."""

import os
import re

from .textio import TextFile, strip_comment, tokens
from .tga import read_tga


def find_data_dir(path):
    """Accept the mod folder, its data folder or the game folder; return the data folder."""
    path = os.path.abspath(path)
    for cand in (path, os.path.join(path, "data"), os.path.join(path, "Data")):
        if os.path.isfile(os.path.join(cand, "descr_sm_factions.txt")):
            return cand
    game = _game_above(path)
    if game:
        raise FileNotFoundError(
            "%s holds only the files this mod changes - the game takes the rest (descr_sm_factions.txt and the "
            "others) from %s. The editor needs one data folder with every file: load the game's own data folder, "
            "or make the mod whole - New mod folder... on the game, then copy this mod's files into the new folder."
            % (path, os.path.join(game, "data")))
    raise FileNotFoundError("no descr_sm_factions.txt in %s or its data folder" % path)


def _game_above(path):
    """The game folder a mod folder sits in when that mod holds only what it changes (REX -mod:, Medieval II
    mods/<name> - the game reads the rest from its own data folder), or None."""
    data = next((c for c in (os.path.join(path, "data"), os.path.join(path, "Data"), path)
                 if os.path.isdir(os.path.join(c, "text")) or os.path.isdir(os.path.join(c, "world"))), None)
    if not data:
        return None
    up = os.path.dirname(data)
    for _ in range(3):                                   # <game>/<mod>/data, <game>/mods/<mod>/data
        up = os.path.dirname(up)
        if os.path.isfile(os.path.join(up, "data", "descr_sm_factions.txt")):
            return up
    return None


def _ci(folder, name):
    """Case-insensitive file lookup inside one folder (Windows mods mix cases)."""
    if not os.path.isdir(folder):
        return None
    p = os.path.join(folder, name)
    if os.path.exists(p):
        return p
    low = name.lower()
    for n in os.listdir(folder):
        if n.lower() == low:
            return os.path.join(folder, n)
    return None


def ci_path(root, rel):
    """root/rel found without case in every folder on the way (the game's files name 'unit_models/_Units/EN_x/..'
    while the disk may say '_units/en_x'), or None."""
    cur = root
    for part in [x for x in rel.replace("\\", "/").split("/") if x]:
        cur = _ci(cur, part)
        if cur is None:
            return None
    return cur


DATA_FILES = {
    # key: file name in the data root
    "sm_factions": "descr_sm_factions.txt",
    "sm_factions_json": "descr_sm_factions.json",
    "character": "descr_character.txt",
    "names": "descr_names.txt",
    "edu": "export_descr_unit.txt",
    "edb": "export_descr_buildings.txt",
    "model_battle": "descr_model_battle.txt",
    "model_strat": "descr_model_strat.txt",
    "banners": "descr_banners.txt",
    "lbc_db": "descr_lbc_db.txt",
    "offmap": "descr_offmap_models.txt",
    "building_battle": "descr_building_battle.txt",
    "traits": "export_descr_character_traits.txt",
    "ancillaries": "export_descr_ancillaries.txt",
    "lookup_descr": "lookup_campaign_descriptions.txt",
    "resources": "descr_sm_resources.txt",
    # Medieval II: battle banners, voice accents, one-liners, faction movies (every faction is named in them)
    "banners_xml": "descr_banners_new.xml",
    "accents": "descr_sounds_accents.txt",
    "sounds_db": "descr_sounds_db.xml",
    "movies_tracks": "descr_movies_tracks.xml",
}


# map_ground_types.tga colours no land character (army or agent) may start on: the
# three seas, both mountain colours and dense forest. The user checked in the game:
# on land only these refuse a character - hills, woodland, swamp and steep tiles are
# fine. Rivers, fords and cliffs (map_features.tga) refuse one too ("invalid tile").
BLOCKED_GROUND = {(64, 0, 0): "sea", (128, 0, 0): "sea", (196, 0, 0): "sea",
                  (98, 65, 65): "mountains", (196, 128, 128): "high mountains", (0, 64, 0): "dense forest",
                  (64, 64, 64): "impassable land", (128, 128, 128): "impassable sea"}     # Medieval II's


def parse_religions(text):
    """'religions { catholic 90 orthodox 0 pagan 10 }' -> {'catholic': 90, ...} in order."""
    inside = text[text.find("{") + 1:text.rfind("}")] if "{" in text else ""
    t = inside.split()
    out = {}
    for i in range(0, len(t) - 1, 2):
        try:
            out[t[i]] = int(t[i + 1])
        except ValueError:
            pass
    return out


def religions_line(rel):
    return "religions { %s }" % " ".join("%s %d" % (k, v) for k, v in rel.items())


RE_COLOUR = re.compile(r"^\s*\d+\s+\d+\s+\d+\s*$")


def region_entries(f):
    """{region: {field: (line index, value)}} of a loaded descr_regions.txt. A region is its name at the
    start of a line, then indented value lines: settlement, creator, rebels, 'r g b', resources, triumph,
    farming (and Medieval II's religions). Barbarian Invasion adds a 'legion: X' line right after the name
    and a beliefs line after farming ('pagan 90 christianity 10'). The colour line (three numbers) anchors the rest, so a
    region with a line more or less before it (seen in BI's file: 'Pictii' where the colour was
    expected) still reads right: settlement and creator are the first two, rebels the line before
    the colour, resources / triumph / farming the lines after it. The one place that knows the
    layout - readers and writers all use it."""
    out, cur, vals = {}, None, []

    def flush():
        if not cur:
            return
        e = {}
        ci = next((k for k, (_, v) in enumerate(vals) if RE_COLOUR.match(v)), None)
        rel = next((k for k, (_, v) in enumerate(vals) if v.startswith("religions")), None)
        leg = next((k for k, (_, v) in enumerate(vals) if v.lower().startswith("legion:")), None)
        plain = [k for k in range(len(vals)) if k not in (rel, leg)]
        if plain:
            e["settlement"] = vals[plain[0]]
        if len(plain) > 1 and (ci is None or plain[1] < ci - 1):
            e["creator"] = vals[plain[1]]
        if ci is not None:
            e["colour"] = vals[ci]
            if ci - 1 > 0:
                e["rebels"] = vals[ci - 1]
            after = [k for k in plain if k > ci]
            for name, k in zip(("resources", "triumph", "farming", "beliefs"), after):
                e[name] = vals[k]
        if leg is not None:
            e["legion"] = vals[leg]
        if rel is not None:
            e["religions"] = vals[rel]
        # REX / M2EX wasteland: 'wasteland' where the settlement stands (Name / wasteland / r g b, or the long form) -
        # a region without a town, owner or rebels (no town pixel needed)
        for k in ("settlement", "rebels", "creator"):
            if k in e and e[k][1].lower() == "wasteland":
                e["wasteland"] = e.pop(k)
        out[cur] = e

    texts = f.texts() if hasattr(f, "texts") else f
    for i, line in enumerate(texts):
        code = strip_comment(line)
        if not code.strip():
            continue
        if not code[0].isspace():
            flush()
            cur, vals = code.strip(), []
        else:
            vals.append((i, code.strip()))
    flush()
    return out


def thin_mod(path):
    """(the mod's data folder, the game's data folder under it) for a mod inside a game's folder (Medieval II
    mods/<name>, REX -mod:<name>, a New mod folder...): the game reads every file the mod lacks from its own data
    folder, and so does the editor - a mod that holds only the files it changes loads too. None for the game's own
    data or a folder in no game. FileNotFoundError when such a mod sits on a game whose data is still packed."""
    path = os.path.abspath(path)
    data = next((c for c in (os.path.join(path, "data"), os.path.join(path, "Data"), path)
                 if os.path.isfile(os.path.join(c, "descr_sm_factions.txt")) or os.path.isdir(os.path.join(c, "text"))
                 or os.path.isdir(os.path.join(c, "world"))), None)
    if not data:
        return None
    from .newmod import game_of, is_game
    game = game_of(data)
    if not game or not is_game(game):
        return None
    under = os.path.join(game, "data")
    if os.path.normcase(os.path.abspath(under)) == os.path.normcase(os.path.abspath(data)):
        return None
    if not os.path.isfile(os.path.join(under, "descr_sm_factions.txt")):
        if os.path.isfile(os.path.join(data, "descr_sm_factions.txt")):
            return None                                  # a whole mod on a packed game: it stands on its own
        raise FileNotFoundError(
            "%s holds only the files this mod changes, and the game's own data (%s) is still packed - the editor reads "
            "the rest from there, as the game does. Load the game's own data folder once: the editor offers to unpack "
            "it; then load this mod again." % (path, under))
    return data, under


class ModData:
    under = None                 # the game's data under a mod (set in __init__; a ModData made otherwise has none)

    def __init__(self, path):
        thin = thin_mod(path)
        # under: the game's own data folder a mod that holds only its changes sits on - read where the mod has no
        # file of its own; every write goes into the mod (Plan: a copy of the game's file, Restore takes it away)
        self.data, self.under = thin if thin else (find_data_dir(path), None)
        self.campaign_root = os.path.join(self.data, "world", "maps", "campaign")
        self.base = os.path.join(self.data, "world", "maps", "base")
        self._cache = {}

    # ---- locations ----
    def roots(self):
        """The data folders read, the mod's first."""
        return [self.data] + ([self.under] if self.under else [])

    def find(self, rel):
        """data/<rel> found without case - the mod's own first, then the game's under it (the game reads it so), or
        None."""
        for root in self.roots():
            p = ci_path(root, rel)
            if p:
                return p
        return None

    def own(self, path):
        """Where a write of this file goes: the mod's own copy of a file read from the game's data (the same place
        under the mod's data folder); any other path as it is."""
        if not self.under or not path:
            return path
        a = os.path.abspath(path)
        u = os.path.abspath(self.under)
        if os.path.normcase(a).startswith(os.path.normcase(u) + os.sep):
            return os.path.join(self.data, os.path.relpath(a, u))
        return path

    def file(self, key):
        return next((p for p in (_ci(r, DATA_FILES[key]) for r in self.roots()) if p), None)

    def campaigns(self):
        """The mod's own campaigns; a mod without one plays the game's (as the game does)."""
        for root in self.roots():
            croot = os.path.join(root, "world", "maps", "campaign")
            out = [n for n in sorted(os.listdir(croot)) if _ci(os.path.join(croot, n), "descr_strat.txt")] \
                if os.path.isdir(croot) else []
            if out:
                return out
        return []

    def campaign_dir(self, campaign):
        mine = os.path.join(self.campaign_root, campaign)
        if self.under and not os.path.isdir(mine):
            game = os.path.join(self.under, "world", "maps", "campaign", campaign)
            if os.path.isdir(game):
                return game
        return mine

    def in_campaign(self, campaign, name):
        """The campaign folder's own file (no base fallback) - the mod's, then the game's under it - or None."""
        for root in self.roots():
            p = _ci(os.path.join(root, "world", "maps", "campaign", campaign), name)
            if p:
                return p
        return None

    def campaign_dirs(self, campaign):
        """The campaign's folders read, the mod's first (a mod that holds only its changes: the game's too)."""
        return [d for d in (os.path.join(r, "world", "maps", "campaign", campaign) for r in self.roots())
                if os.path.isdir(d)]

    def campaign_file(self, campaign, name):
        """A campaign file, falling back to world/maps/base like the game does (the mod's own first, then the
        game's, for a mod that holds only its changes)."""
        for sub in (("campaign", campaign), ("base",)):
            for root in self.roots():
                p = _ci(os.path.join(root, "world", "maps", *sub), name)
                if p:
                    return p
        return None

    def text_dirs(self):
        """The string-table folders in the order the game reads them: data/text/english
        first (Medieval II keeps its tables only there; RTW Gold reads a table there before
        data/text when both have it), then data/text - the mod's, then the game's under it."""
        out = []
        for root in self.roots():
            text = _ci(root, "text")
            if not text or not os.path.isdir(text):
                continue
            eng = _ci(text, "english")
            out += [d for d in (eng, text) if d and os.path.isdir(d)]
        return out

    def text_files(self):
        """Every string table the game reads, one per name: the copy in text/english wins
        over the one in data/text (the game never sees the other)."""
        seen, out = set(), []
        for folder in self.text_dirs():
            for n in sorted(os.listdir(folder)):
                if n.lower().endswith(".txt") and n.lower() not in seen:
                    seen.add(n.lower())
                    out.append(os.path.join(folder, n))
        return out

    def text_file(self, name):
        """The copy of this string table the game reads, or None."""
        for folder in self.text_dirs():
            p = _ci(folder, name)
            if p:
                return p
        return None

    def campaign_text_files(self, campaign=None):
        """The string tables that speak for this campaign, the one the game reads
        first leading: <campaign>_expanded_bi.txt, expanded_bi.txt, expanded.txt,
        then the rest. Another campaign's own tables (<other>_expanded*.txt)
        are left out."""
        camp = (campaign or "").lower()
        mine, main, rest = [], [], []
        for p in self.text_files():
            n = os.path.basename(p).lower()
            m = re.match(r"^(.+)_expanded(_bi)?\.txt$", n)
            if m:
                (mine if m.group(1) == camp else []).append(p)
            elif n in ("expanded_bi.txt", "expanded.txt"):
                main.append(p)
            else:
                rest.append(p)
        main.sort(key=lambda p: os.path.basename(p).lower() != "expanded_bi.txt")
        return mine + main + rest

    def region_labels_file(self, campaign):
        """data/text/<campaign>_regions_and_settlement_names.txt, or None."""
        return self.text_file("%s_regions_and_settlement_names.txt" % campaign)

    def rel(self, path):
        if self.under and path:
            a, u = os.path.abspath(path), os.path.abspath(self.under)
            if os.path.normcase(a).startswith(os.path.normcase(u) + os.sep):      # read from the game's own data
                return "(the game's) data/" + os.path.relpath(a, u).replace("\\", "/")
        return os.path.relpath(path, os.path.dirname(self.data)).replace("\\", "/")

    def load(self, path):
        if path not in self._cache:
            self._cache[path] = TextFile.load(path)
        return self._cache[path]

    # ---- factions ----
    def factions(self):
        """[(name, culture)] in descr_sm_factions.txt order."""
        return list(self._factions_table())

    def _factions_table(self):
        """descr_sm_factions.txt read once while it stays the same (the town window asked a culture 113 times, each
        reading the whole file again - half its opening time): kept with the file's text, read again when it
        differs."""
        f = self.load(self.file("sm_factions"))
        sig = hash("\n".join(f.raw))
        got = self._cache.get(("factions_table", id(f)))
        if got and got[0] == sig:
            return got[1]
        out = []
        cur = None
        for line in f.texts():
            t = tokens(line)
            if len(t) >= 2 and t[0] == "faction":
                cur = [t[1], None]
                out.append(cur)
            elif len(t) >= 2 and t[0] == "culture" and cur is not None and cur[1] is None:
                cur[1] = t[1]
        table = tuple(tuple(x) for x in out)
        self._cache[("factions_table", id(f))] = (sig, table, {n: c for n, c in reversed(table)})
        return table

    def culture(self, faction):
        """The faction's culture from descr_sm_factions.txt, or None."""
        self._factions_table()
        f = self.load(self.file("sm_factions"))
        return self._cache[("factions_table", id(f))][2].get(faction)

    def name_pool(self, faction):
        """descr_names.txt pools: {'characters': [...], 'surnames': [...], 'women': [...]}.
        A section may serve several factions (BI: 'faction: empire_east, empire_east_rebels');
        when a faction has more than one section (BI's alemanni), the first one counts."""
        path = self.file("names")
        return pool_in(self.load(path).texts() if path else [], faction)

    # ---- map ----
    def regions(self, campaign):
        """{region: {'settlement', 'creator', 'rebels', 'colour', 'resources', 'triumph', 'farming', 'wasteland'
        (, 'religions')}} from descr_regions.txt (see region_entries); a wasteland region (REX / M2EX) has no
        settlement ('').
        Read once while the file stays the same (report #154: deleting 48 towns of HLR read its 749 regions 150
        times); each call gets its own copy to change."""
        f = self.load(self.campaign_file(campaign, "descr_regions.txt"))
        sig = hash("\n".join(f.raw))
        got = self._cache.get(("regions", id(f)))
        if not got or got[0] != sig:
            got = (sig, self._read_regions(f))
            self._cache[("regions", id(f))] = got
        return {k: dict(v) for k, v in got[1].items()}

    @staticmethod
    def _read_regions(f):
        out = {}
        for name, e in region_entries(f).items():
            v = {k: val for k, (_, val) in e.items()}
            if "colour" not in v:
                continue
            v["colour"] = tuple(int(x) for x in v["colour"].split()[:3])
            if "religions" in v:                         # Medieval II: religions { catholic 90 pagan 10 }
                v["religions"] = parse_religions(v["religions"])
            if "beliefs" in v:                           # Barbarian Invasion: pagan 90 christianity 10
                v["beliefs"] = parse_religions("{%s}" % v["beliefs"])
            v["wasteland"] = "wasteland" in v               # REX / M2EX: no town, no owner
            for k in ("settlement", "creator", "rebels", "resources", "triumph", "farming"):
                v.setdefault(k, "")
            out[name] = v
        return out

    def city_tiles(self, campaign):
        """{region: (x, y)} of each settlement, from the black pixels of map_regions.tga."""
        key = ("tiles", campaign)
        if key in self._cache:
            return self._cache[key]
        regions = self.regions(campaign)
        by_colour = {v["colour"]: k for k, v in regions.items()}
        img = self.region_map(campaign)
        owners = town_colours(img.get, img.width, img.height, img.find((0, 0, 0)), set(by_colour))
        tiles = {by_colour[c]: xy for xy, c in owners.items()}
        self._cache[key] = tiles
        return tiles

    def region_map(self, campaign):
        key = ("map", campaign)
        if key not in self._cache:
            self._cache[key] = read_tga(self.campaign_file(campaign, "map_regions.tga"))
        return self._cache[key]

    def forts(self, campaign):
        """[strat.Fort] of the campaign's descr_strat.txt (forts and watchtowers)."""
        key = ("forts", campaign)
        if key not in self._cache:
            from .strat import Strat
            p = self.campaign_file(campaign, "descr_strat.txt")
            self._cache[key] = Strat(self.load(p)).forts if p else []
        return self._cache[key]

    def free_tile(self, campaign, region, taken, reach=4, start=None, own=None):
        """The best tile of `region` near its city that no one stands on, or None.

        Candidates are tiles of the region's own colour in map_regions.tga (so
        never sea, a neighbour's land or another city) within `reach` tiles of
        the city that pass _standable(); the flattest wins, then the nearest.
        A plan that changes the map (new regions, painted borders) gives its own
        town tile (start) and own(tile) -> bool for 'this region's land'."""
        img = self.region_map(campaign)
        info = self.regions(campaign).get(region)
        start = start or self.city_tiles(campaign).get(region)
        if (not info and own is None) or not start:
            return None
        colour = info["colour"] if info else None
        ok, slope = self._standable(campaign)
        taken = set(taken) | {x.xy for x in self.forts(campaign)}
        best = None
        for y in range(start[1] - reach, start[1] + reach + 1):
            for x in range(start[0] - reach, start[0] + reach + 1):
                p = (x, y)
                if p == start or p in taken or not (0 <= x < img.width and 0 <= y < img.height):
                    continue
                mine = own(p) if own is not None else img.get(x, y) == colour
                if not mine or not ok(p):
                    continue
                key = (slope(p), max(abs(x - start[0]), abs(y - start[1])), abs(x - start[0]) + abs(y - start[1]))
                if best is None or key < best[0]:
                    best = (key, p)
        return best[1] if best else None

    def agent_kinds(self):
        """The agent types of descr_character.txt (every 'type' but general, named
        character and admiral), in the file's order; spy, assassin, diplomat without it."""
        key = ("agents",)
        if key not in self._cache:
            found = []
            p = self.file("character")
            if p:
                for l in self.load(p).texts():
                    t = strip_comment(l).split(None, 1)
                    if len(t) == 2 and t[0] == "type":
                        k = t[1].strip()
                        if k not in ("general", "named character", "admiral") and k not in found:
                            found.append(k)
            self._cache[key] = found or ["spy", "assassin", "diplomat"]
        return self._cache[key]

    def _optional_map(self, campaign, name):
        key = ("map", campaign, name)
        if key not in self._cache:
            path = self.campaign_file(campaign, name)
            self._cache[key] = read_tga(path) if path else None
        return self._cache[key]

    def _standable(self, campaign):
        """(ok, slope) for tiles a character may start on: ok(p) is land_problem() == None;
        slope(p) is the height difference inside the tile (0 without a heights map), used
        only to prefer flat tiles when the tool picks one."""
        regions = self.region_map(campaign)
        size = (2 * regions.width + 1, 2 * regions.height + 1)
        heights = self._optional_map(campaign, "map_heights.tga")
        if heights and (heights.width, heights.height) != size:
            heights = None

        def slope(p):
            if not heights:
                return 0
            v = [heights.get(2 * p[0] + dx, 2 * p[1] + dy)[0] for dy in range(3) for dx in range(3)]
            return max(v) - min(v)

        def ok(p):
            return self.land_problem(campaign, p) is None
        return ok, slope

    def land_problem(self, campaign, xy):
        """Why no character may stand on land tile xy, or None: a river, ford or cliff
        in map_features.tga, or sea, mountains or dense forest in the middle of the tile
        in map_ground_types.tga. A map missing or of an unexpected size is not checked."""
        regions = self.region_map(campaign)
        x, y = xy
        feat = self._optional_map(campaign, "map_features.tga")
        if feat and (feat.width, feat.height) == (regions.width, regions.height) and feat.get(x, y) != (0, 0, 0):
            return "a river, ford or cliff runs there"
        ground = self._optional_map(campaign, "map_ground_types.tga")
        if ground and (ground.width, ground.height) == (2 * regions.width + 1, 2 * regions.height + 1):
            what = BLOCKED_GROUND.get(ground.get(2 * x + 1, 2 * y + 1))
            if what:
                return what
        return None

    def region_colours(self, campaign):
        """{colour: region} of descr_regions.txt as loaded (read once - is_sea asks it for every tile)."""
        key = ("colours", campaign)
        if key not in self._cache:
            self._cache[key] = {v["colour"]: k for k, v in self.regions(campaign).items()}
        return self._cache[key]

    def is_sea(self, campaign, xy):
        """Sea: a map_regions pixel that is no region, city or port."""
        img = self.region_map(campaign)
        x, y = xy
        if not (0 <= x < img.width and 0 <= y < img.height):
            return False
        px = img.get(x, y)
        if px in ((0, 0, 0), (255, 255, 255)):
            return False
        return px not in self.region_colours(campaign)

    def tile_problem(self, campaign, xy, kind, army, armies_at=()):
        """Why a character of this kind may not start on tile xy, or None.
        Admirals need sea; everyone else land without river, mountains or dense
        forest (or a town); an army also a tile no other army holds."""
        img = self.region_map(campaign)
        x, y = xy
        if not (0 <= x < img.width and 0 <= y < img.height):
            return "off the map"
        sea = self.is_sea(campaign, xy)
        if kind == "admiral":
            return None if sea else "a fleet needs sea"
        if sea:
            return "that is sea"
        town = xy in set(self.city_tiles(campaign).values())
        fort = next((x for x in self.forts(campaign) if x.xy == xy), None)
        if fort:
            return "a %s stands there%s" % (fort.kind, " (%s)" % fort.name if fort.name else "")
        if army and xy in armies_at:
            return "another army stands there" + (" (a town holds one army)" if town else "")
        if not town:
            why = self.land_problem(campaign, xy)
            if why:
                return "no one can stand here: " + why
        return None


RE_NAME_HEAD = re.compile(r"\s*faction\s*:\s*(.+)")


def town_colours(get, w, h, points, lands):
    """{(x, y): land colour} for the town pixels `points` of a map_regions picture: each to the colour most of its
    8 neighbours have - but one town per region: a town on its region's edge, touching a neighbour more than its
    own land, went to the neighbour and took its town away (a tester's Erebor was never drawn, and the bigger map
    painted it over). The surest pixels are given first, each to its best colour still without a town."""
    seen = []
    for x, y in points:
        votes = {}
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                c = get(nx, ny)
                if c in lands:
                    votes[c] = votes.get(c, 0) + 1
        if votes:
            seen.append(((x, y), sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))))
    seen.sort(key=lambda t: (-(t[1][0][1] - (t[1][1][1] if len(t[1]) > 1 else 0)), t[0][1], t[0][0]))
    out, taken = {}, set()
    for xy, ranked in seen:
        c = next((c for c, _ in ranked if c not in taken), None)
        if c is not None:
            out[xy] = c
            taken.add(c)
    return out


def pool_in(texts, faction):
    """The faction's pools in descr_names.txt lines (see ModData.name_pool)."""
    heads = name_sections(texts)
    for k, (start, owners) in enumerate(heads):
        if faction not in owners:
            continue
        end = heads[k + 1][0] if k + 1 < len(heads) else len(texts)
        pools, section = {}, None
        for line in texts[start + 1:end]:
            s = strip_comment(line).strip()
            if not s:
                continue
            if s in ("characters", "surnames", "women"):
                section = s
                pools.setdefault(section, [])
            elif section:
                pools[section].append(s)
        return pools
    return {}


def name_sections(texts):
    """descr_names.txt sections: [(line index, [factions])]. The header lists every faction
    the section serves: 'faction: romans_julii' or BI's 'faction: empire_east, empire_east_rebels'."""
    out = []
    for i, line in enumerate(texts):
        m = RE_NAME_HEAD.match(strip_comment(line))
        if m:
            out.append((i, [x for x in re.split(r"[\s,]+", m.group(1)) if x]))
    return out
