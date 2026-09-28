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


# map_ground_types.tga colours no land character (army or agent) may start on: the
# three seas, both mountain colours and dense forest. The user checked in the game:
# on land only these refuse a character - hills, woodland, swamp and steep tiles are
# fine. Rivers, fords and cliffs (map_features.tga) refuse one too ("invalid tile").
BLOCKED_GROUND = {(64, 0, 0): "sea", (128, 0, 0): "sea", (196, 0, 0): "sea",
                  (98, 65, 65): "mountains", (196, 128, 128): "high mountains", (0, 64, 0): "dense forest"}


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
        return _ci(os.path.join(self.data, "text"), "%s_regions_and_settlement_names.txt" % campaign)

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

    def culture(self, faction):
        """The faction's culture from descr_sm_factions.txt, or None."""
        cur = None
        for l in self.load(self.file("sm_factions")).texts():
            t = tokens(l)
            if t[:1] == ["faction"] and len(t) > 1:
                cur = t[1]
            elif t[:1] == ["culture"] and len(t) > 1 and cur == faction:
                return t[1]
        return None

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
        """{region: {'settlement', 'creator', 'rebels', 'colour', 'resources'}} from descr_regions.txt."""
        path = self.campaign_file(campaign, "descr_regions.txt")
        f = self.load(path)
        out = {}
        cur = None
        vals = []
        def flush():
            if cur and len(vals) >= 4:
                colour = tuple(int(v) for v in vals[3].split()[:3])
                out[cur] = {"settlement": vals[0], "creator": vals[1], "rebels": vals[2], "colour": colour,
                            "resources": vals[4] if len(vals) > 4 else ""}
                rel = next((v for v in vals[5:] if v.startswith("religions")), None)
                if rel:                                      # Medieval II: religions { catholic 90 pagan 10 }
                    out[cur]["religions"] = parse_religions(rel)
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

    def is_sea(self, campaign, xy):
        """Sea: a map_regions pixel that is no region, city or port."""
        img = self.region_map(campaign)
        x, y = xy
        if not (0 <= x < img.width and 0 <= y < img.height):
            return False
        px = img.get(x, y)
        if px in ((0, 0, 0), (255, 255, 255)):
            return False
        return px not in {v["colour"] for v in self.regions(campaign).values()}

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
        if army and xy in armies_at:
            return "another army stands there" + (" (a town holds one army)" if town else "")
        if not town:
            why = self.land_problem(campaign, xy)
            if why:
                return "no one can stand here: " + why
        return None
