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
    raise FileNotFoundError("no descr_sm_factions.txt in %s or its data folder" % path)


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
}


# map_ground_types.tga colours a character does not start on: the three seas
# and both mountain colours (no character in HLR's descr_strat.txt stands on one)
BLOCKED_GROUND = {(64, 0, 0), (128, 0, 0), (196, 0, 0), (98, 65, 65), (196, 128, 128)}
MAX_SLOPE = 25


class ModData:
    def __init__(self, path):
        self.data = find_data_dir(path)
        self.campaign_root = os.path.join(self.data, "world", "maps", "campaign")
        self.base = os.path.join(self.data, "world", "maps", "base")
        self._cache = {}

    # ---- locations ----
    def file(self, key):
        return _ci(self.data, DATA_FILES[key])

    def campaigns(self):
        out = []
        if os.path.isdir(self.campaign_root):
            for n in sorted(os.listdir(self.campaign_root)):
                if _ci(os.path.join(self.campaign_root, n), "descr_strat.txt"):
                    out.append(n)
        return out

    def campaign_dir(self, campaign):
        return os.path.join(self.campaign_root, campaign)

    def campaign_file(self, campaign, name):
        """A campaign file, falling back to world/maps/base like the game does."""
        return _ci(self.campaign_dir(campaign), name) or _ci(self.base, name)

    def text_files(self):
        folder = os.path.join(self.data, "text")
        if not os.path.isdir(folder):
            return []
        return [os.path.join(folder, n) for n in sorted(os.listdir(folder)) if n.lower().endswith(".txt")]

    def rel(self, path):
        return os.path.relpath(path, os.path.dirname(self.data)).replace("\\", "/")

    def load(self, path):
        if path not in self._cache:
            self._cache[path] = TextFile.load(path)
        return self._cache[path]

    # ---- factions ----
    def factions(self):
        """[(name, culture)] in descr_sm_factions.txt order."""
        f = self.load(self.file("sm_factions"))
        out = []
        cur = None
        for line in f.texts():
            t = tokens(line)
            if len(t) >= 2 and t[0] == "faction":
                cur = [t[1], None]
                out.append(cur)
            elif len(t) >= 2 and t[0] == "culture" and cur is not None and cur[1] is None:
                cur[1] = t[1]
        return [tuple(x) for x in out]

    def name_pool(self, faction):
        """descr_names.txt pools: {'characters': [...], 'surnames': [...], 'women': [...]}."""
        f = self.load(self.file("names"))
        pools = {}
        cur = None
        section = None
        for line in f.texts():
            s = strip_comment(line).strip()
            if not s:
                continue
            m = re.match(r"faction\s*:\s*(\S+)", s)
            if m:
                cur = m.group(1)
                section = None
                continue
            if cur != faction:
                continue
            if s in ("characters", "surnames", "women"):
                section = s
                pools.setdefault(section, [])
            elif section:
                pools[section].append(s)
        return pools

    # ---- map ----
    def regions(self, campaign):
        """{region: {'settlement', 'creator', 'rebels', 'colour'}} from descr_regions.txt."""
        path = self.campaign_file(campaign, "descr_regions.txt")
        f = self.load(path)
        out = {}
        cur = None
        vals = []
        def flush():
            if cur and len(vals) >= 4:
                colour = tuple(int(v) for v in vals[3].split()[:3])
                out[cur] = {"settlement": vals[0], "creator": vals[1], "rebels": vals[2], "colour": colour}
        for line in f.texts():
            s = strip_comment(line)
            if not s.strip():
                continue
            if not s[0].isspace():
                flush()
                cur = s.strip()
                vals = []
            else:
                vals.append(s.strip())
        flush()
        return out

    def city_tiles(self, campaign):
        """{region: (x, y)} of each settlement, from the black pixels of map_regions.tga."""
        key = ("tiles", campaign)
        if key in self._cache:
            return self._cache[key]
        regions = self.regions(campaign)
        by_colour = {v["colour"]: k for k, v in regions.items()}
        img = self.region_map(campaign)
        tiles = {}
        for y in range(img.height):
            for x in range(img.width):
                if img.get(x, y) != (0, 0, 0):
                    continue
                votes = {}
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < img.width and 0 <= ny < img.height:
                        r = by_colour.get(img.get(nx, ny))
                        if r:
                            votes[r] = votes.get(r, 0) + 1
                if votes:
                    tiles[max(votes, key=votes.get)] = (x, y)
        self._cache[key] = tiles
        return tiles

    def region_map(self, campaign):
        key = ("map", campaign)
        if key not in self._cache:
            self._cache[key] = read_tga(self.campaign_file(campaign, "map_regions.tga"))
        return self._cache[key]

    def free_tile(self, campaign, region, taken, reach=4):
        """The best tile of `region` near its city that no one stands on, or None.

        Candidates are tiles of the region's own colour in map_regions.tga (so
        never sea, a neighbour's land or another city) within `reach` tiles of
        the city that pass _standable(); the flattest wins, then the nearest."""
        img = self.region_map(campaign)
        info = self.regions(campaign).get(region)
        start = self.city_tiles(campaign).get(region)
        if not info or not start:
            return None
        colour = info["colour"]
        ok, slope = self._standable(campaign)
        best = None
        for y in range(start[1] - reach, start[1] + reach + 1):
            for x in range(start[0] - reach, start[0] + reach + 1):
                p = (x, y)
                if p == start or p in taken or not (0 <= x < img.width and 0 <= y < img.height):
                    continue
                if img.get(x, y) != colour or not ok(p):
                    continue
                key = (slope(p), max(abs(x - start[0]), abs(y - start[1])), abs(x - start[0]) + abs(y - start[1]))
                if best is None or key < best[0]:
                    best = (key, p)
        return best[1] if best else None

    def _optional_map(self, campaign, name):
        key = ("map", campaign, name)
        if key not in self._cache:
            path = self.campaign_file(campaign, name)
            self._cache[key] = read_tga(path) if path else None
        return self._cache[key]

    def _standable(self, campaign):
        """(ok, slope) for tiles a character may start on.

        ok: no river, ford or cliff in map_features.tga; no sea, impassable land
        or mountain in the middle of the tile in map_ground_types.tga; and a
        height difference inside the tile (its nine vertices in map_heights.tga)
        of at most MAX_SLOPE - the game refuses steep tiles, and the characters
        it accepts in HLR's own descr_strat.txt almost all stand below 25.
        slope: that height difference, 0 without a heights map.
        A map that is missing or of an unexpected size is not checked."""
        regions = self.region_map(campaign)
        size = (2 * regions.width + 1, 2 * regions.height + 1)
        feat = self._optional_map(campaign, "map_features.tga")
        if feat and (feat.width, feat.height) != (regions.width, regions.height):
            feat = None
        ground = self._optional_map(campaign, "map_ground_types.tga")
        if ground and (ground.width, ground.height) != size:
            ground = None
        heights = self._optional_map(campaign, "map_heights.tga")
        if heights and (heights.width, heights.height) != size:
            heights = None

        def slope(p):
            if not heights:
                return 0
            v = [heights.get(2 * p[0] + dx, 2 * p[1] + dy)[0] for dy in range(3) for dx in range(3)]
            return max(v) - min(v)

        def ok(p):
            x, y = p
            if feat and feat.get(x, y) != (0, 0, 0):
                return False
            if ground and ground.get(2 * x + 1, 2 * y + 1) in BLOCKED_GROUND:
                return False
            return slope(p) <= MAX_SLOPE
        return ok, slope
