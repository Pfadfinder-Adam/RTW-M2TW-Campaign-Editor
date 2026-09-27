"""The campaign map as pictures: the background (drawn from the
ground types, tile by tile), the political layer, cities and
ports. Tile (x, y) is descr_strat's tile: x to the right, y up from the bottom.
Needs Pillow."""

from PIL import Image

from .textio import tokens

PORT = (255, 255, 255)
CITY = (0, 0, 0)

# map_ground_types.tga colours, for the tile read-out
GROUND = {
    (101, 124, 0): "low fertility", (96, 160, 64): "medium fertility", (0, 128, 0): "high fertility",
    (0, 0, 0): "wilderness", (0, 64, 0): "dense forest", (0, 128, 128): "sparse forest",
    (128, 128, 64): "hills", (98, 65, 65): "mountains", (196, 128, 128): "high mountains",
    (0, 255, 128): "swamp", (255, 255, 255): "beach / impassable", (64, 0, 0): "ocean",
    (128, 0, 0): "deep sea", (196, 0, 0): "shallow sea",
}
SEA = {(64, 0, 0), (128, 0, 0), (196, 0, 0)}
# the background: a colour per ground type of map_ground_types.tga
GROUND_LOOK = {
    (101, 124, 0): (170, 160, 95), (96, 160, 64): (120, 150, 80), (0, 128, 0): (80, 130, 60),
    (0, 0, 0): (200, 180, 130), (0, 64, 0): (45, 90, 45), (0, 128, 128): (70, 115, 70),
    (128, 128, 64): (140, 125, 85), (98, 65, 65): (125, 110, 95), (196, 128, 128): (225, 225, 225),
    (0, 255, 128): (90, 110, 80), (255, 255, 255): (215, 200, 160), (64, 0, 0): (45, 75, 120),
    (128, 0, 0): (35, 60, 105), (196, 0, 0): (60, 95, 140),
}
REBELS = (130, 130, 130)


class CampaignMap:
    def __init__(self, mod, campaign):
        self.mod, self.campaign = mod, campaign
        self.regions_img = mod.region_map(campaign)
        self.w, self.h = self.regions_img.width, self.regions_img.height
        self.info = mod.regions(campaign)                    # region -> {settlement, colour, ...}
        self.by_colour = {v["colour"]: k for k, v in self.info.items()}
        self.cities = mod.city_tiles(campaign)               # region -> (x, y)
        self.ports = self._ports()                           # region -> (x, y)
        self.ground = mod._optional_map(campaign, "map_ground_types.tga")
        self.ok, self.slope = mod._standable(campaign)
        self._background = None
        self._political = {}

    # ---- tiles ----
    def region_at(self, x, y):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return None
        return self.by_colour.get(self.regions_img.get(x, y))

    def ground_at(self, x, y):
        g = self.ground
        if g is None or not (0 <= 2 * x + 1 < g.width and 0 <= 2 * y + 1 < g.height):
            return None
        return g.get(2 * x + 1, 2 * y + 1)

    def is_sea(self, x, y):
        c = self.regions_img.get(x, y) if 0 <= x < self.w and 0 <= y < self.h else None
        if c in (CITY, PORT):
            return False
        g = self.ground_at(x, y)
        return self.region_at(x, y) is None if g is None else g in SEA

    def describe(self, x, y, owners=None):
        """One line for the status bar about tile (x, y)."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return ""
        px = self.regions_img.get(x, y)
        region = self.region_at(x, y) or next((r for r, t in self.cities.items() if t == (x, y)), None) \
            or next((r for r, t in self.ports.items() if t == (x, y)), None)
        parts = ["tile %d, %d" % (x, y)]
        if region:
            town = self.info.get(region, {}).get("settlement", "")
            parts.append("%s (%s)" % (region, town))
            if owners:
                parts.append("owner " + owners.get(region, "?"))
        if px == CITY:
            parts.append("CITY")
        elif px == PORT:
            parts.append("PORT")
        g = self.ground_at(x, y)
        if g is not None:
            parts.append(GROUND.get(g, "ground %s" % (g,)))
        if region and px not in (CITY, PORT) and not self.is_sea(x, y):
            parts.append("an army may stand here" if self.ok((x, y)) else "no army here (river/ford/slope/mountain)")
        return "   ".join(parts)

    def _ports(self):
        out = {}
        img = self.regions_img
        for y in range(self.h):
            for x in range(self.w):
                if img.get(x, y) != PORT:
                    continue
                votes = {}
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                    r = self.region_at(x + dx, y + dy)
                    if r:
                        votes[r] = votes.get(r, 0) + 1
                if votes:
                    out[max(votes, key=votes.get)] = (x, y)
        return out

    # ---- pictures (top-down, as Pillow draws them) ----
    def background(self):
        """The map drawn from map_ground_types.tga - each tile's terrain type, the
        information that matters here (the game's painted radar map is left alone
        by choice). Returned at 2 px per tile."""
        if self._background is None:
            self._background = self._drawn().resize((2 * self.w, 2 * self.h), Image.BILINEAR)
        return self._background

    def _drawn(self):
        g = self.ground
        if g is None:
            im = Image.new("RGB", (self.w, self.h))
            im.putdata([(60, 95, 140) if self.region_at(x, self.h - 1 - y) is None else (170, 160, 110)
                        for y in range(self.h) for x in range(self.w)])
            return im
        im = Image.new("RGB", (g.width, g.height))
        im.putdata([GROUND_LOOK.get(g.get(x, g.height - 1 - y), (150, 150, 150))
                    for y in range(g.height) for x in range(g.width)])
        return im

    def political(self, owners, colours, highlight=None, alpha=110):
        """RGBA, 1 px per tile: each region in its owner's primary colour, see-through,
        borders darker; the highlighted faction a little stronger."""
        key = (tuple(sorted(owners.items())), highlight, alpha)
        if key in self._political:
            return self._political[key]
        img = self.regions_img
        fill = {}
        for region, owner in owners.items():
            col = self.info.get(region, {}).get("colour")
            if col is None:
                continue
            rgb = REBELS if owner == "slave" else colours.get(owner, REBELS)
            a = min(255, alpha + 60) if owner == highlight else alpha
            if owner == "slave":
                a = alpha // 4                   # rebel land barely tinted: the factions stand out
            fill[col] = rgb + (a,)
        out = []
        for y in range(self.h - 1, -1, -1):
            for x in range(self.w):
                c = img.get(x, y)
                p = fill.get(c)
                if p is None:
                    out.append((0, 0, 0, 0))
                    continue
                right = img.get(x + 1, y) if x + 1 < self.w else c
                down = img.get(x, y - 1) if y > 0 else c
                border = (right != c and right not in (CITY, PORT)) or (down != c and down not in (CITY, PORT))
                out.append((p[0] // 3, p[1] // 3, p[2] // 3, 200) if border else p)
        im = Image.new("RGBA", (self.w, self.h))
        im.putdata(out)
        self._political = {key: im}
        return im


def faction_colours(mod):
    """{faction: (r, g, b)} primary colours from descr_sm_factions.txt."""
    import re
    out, cur = {}, None
    for l in mod.load(mod.file("sm_factions")).texts():
        t = tokens(l)
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1]
        elif t[:1] == ["primary_colour"] and cur:
            m = re.search(r"red\s*(\d+)\s*,\s*green\s*(\d+)\s*,\s*blue\s*(\d+)", l)
            if m:
                out[cur] = tuple(int(v) for v in m.groups())
    return out

