"""The campaign map as pictures: the background (drawn from the
ground types, tile by tile), the political layer, cities and
ports. Tile (x, y) is descr_strat's tile: x to the right, y up from the bottom.
Needs Pillow."""

from PIL import Image, ImageChops

from .textio import tokens

PORT = (255, 255, 255)
CITY = (0, 0, 0)

from .terrain import GROUND, SEA                                   # noqa: E402  (one place for the colours)
# the background: a colour per ground type of map_ground_types.tga
GROUND_LOOK = {
    (101, 124, 0): (170, 160, 95), (96, 160, 64): (120, 150, 80), (0, 128, 0): (80, 130, 60),
    (0, 0, 0): (200, 180, 130), (0, 64, 0): (45, 90, 45), (0, 128, 128): (70, 115, 70),
    (128, 128, 64): (140, 125, 85), (98, 65, 65): (125, 110, 95), (196, 128, 128): (225, 225, 225),
    (0, 255, 128): (90, 110, 80), (255, 255, 255): (215, 200, 160), (64, 0, 0): (45, 75, 120),
    (128, 0, 0): (35, 60, 105), (196, 0, 0): (60, 95, 140), (64, 64, 64): (95, 90, 85),
    (128, 128, 128): (30, 45, 70),
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

    def climate_at(self, x, y):
        """The tile's colour in map_climates.tga (its middle, like the ground), or None."""
        c = self.mod._optional_map(self.campaign, "map_climates.tga")
        if c is None or not (0 <= 2 * x + 1 < c.width and 0 <= 2 * y + 1 < c.height):
            return None
        return c.get(2 * x + 1, 2 * y + 1)

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
            rel = self.info.get(region, {}).get("religions")
            if rel:
                parts.append(" ".join("%s %d%%" % (k, v) for k, v in rel.items() if v))
        if px == CITY:
            parts.append("CITY")
        elif px == PORT:
            parts.append("PORT")
        g = self.ground_at(x, y)
        if g is not None:
            parts.append(GROUND.get(g, "ground %s" % (g,)))
        if region and px not in (CITY, PORT) and not self.is_sea(x, y):
            why = self.mod.land_problem(self.campaign, (x, y))
            parts.append("armies and agents may stand here" if not why else "no one can stand here: " + why)
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
    def background(self, tiles=False, relief=False, rivers=False):
        """The map drawn from map_ground_types.tga - each tile's terrain type, the
        information that matters here (the game's painted radar map is left alone
        by choice). Returned at 2 px per tile. tiles: every tile one square in the
        colour of the ground at its middle (what the tool checks); relief: shaded
        from map_heights.tga; rivers: map_features.tga's rivers, fords and cliffs."""
        climates = bool(getattr(self, "show_climates", False))
        key = (bool(tiles), bool(relief), bool(rivers), climates)
        cache = self.__dict__.setdefault("_backgrounds", {})
        if key not in cache:
            size = (2 * self.w, 2 * self.h)
            if tiles:
                # everything worked out per tile, then blown up: each square one colour, nothing
                # bleeds into the next tile (the grid and the picture agree)
                im = self._tiles()
                if climates:
                    im = self._climates(im)
                if relief:
                    im = self._relief(im)
                if rivers:
                    im = self._rivers(im, True)
                im = im.resize(size, Image.NEAREST)
            else:
                im = self._drawn().resize(size, Image.BILINEAR)
                if climates:
                    im = self._climates(im)
                if relief:
                    im = self._relief(im)
                if rivers:
                    im = self._rivers(im, False)
            cache[key] = im
        return cache[key]

    def _tiles(self):
        """One pixel per tile, top-down, in its ground's colour (the tile's middle)."""
        im = Image.new("RGB", (self.w, self.h))
        data = []
        for y in range(self.h - 1, -1, -1):
            for x in range(self.w):
                g = self.ground_at(x, y)
                if g is None:
                    data.append((60, 95, 140) if self.region_at(x, y) is None else (170, 160, 110))
                else:
                    data.append(GROUND_LOOK.get(g, (150, 150, 150)))
        im.putdata(data)
        return im

    def _climates(self, im):
        """Each land tile tinted in its map_climates.tga colour (the Terrain editor's Climates mode)."""
        over = Image.new("RGB", (self.w, self.h))
        mask = Image.new("L", (self.w, self.h))
        cols, keep = [], []
        for y in range(self.h - 1, -1, -1):
            for x in range(self.w):
                c = None if self.is_sea(x, y) else self.climate_at(x, y)
                cols.append(c or (0, 0, 0))
                keep.append(170 if c else 0)
        over.putdata(cols)
        mask.putdata(keep)
        return Image.composite(over.resize(im.size, Image.NEAREST), im, mask.resize(im.size, Image.NEAREST))

    def _pil(self, name):
        """A campaign map file as a top-down Pillow picture, or None."""
        t = self.mod._optional_map(self.campaign, name)
        if t is None:
            return None
        im = Image.new("RGB", (t.width, t.height))
        im.putdata(t.pixels)
        return im.transpose(Image.FLIP_TOP_BOTTOM)

    def _relief(self, im):
        """Hills lit from the north-west, the valleys in shade (map_heights.tga)."""
        from PIL import ImageFilter
        h = self._pil("map_heights.tga")
        if h is None:
            return im
        h = h.convert("L").resize(im.size, Image.BILINEAR)
        shade = h.filter(ImageFilter.EMBOSS).convert("RGB")      # 128 = flat
        lit = ImageChops.overlay(im, shade) if hasattr(ImageChops, "overlay") else ImageChops.multiply(im, shade)
        return Image.blend(im, lit, 0.55)

    # how map_features.tga's marks are drawn: rivers blue, fords (crossings) light, sources white,
    # cliffs brown-yellow, volcanoes red, Medieval II's land bridges green
    FEATURE_LOOK = {(0, 0, 255): (50, 105, 200), (0, 255, 255): (140, 210, 235), (255, 255, 255): (235, 240, 255),
                    (255, 255, 0): (190, 160, 60), (255, 0, 0): (200, 40, 30), (0, 255, 0): (60, 170, 60)}

    def _rivers(self, im, tiles):
        """map_features.tga's non-black tiles drawn over the ground, each kind in its colour."""
        f = self._pil("map_features.tga")
        if f is None or f.size != (self.w, self.h):
            return im
        over = Image.new("RGB", f.size)
        over.putdata([self.FEATURE_LOOK.get(p, (50, 105, 200)) for p in f.getdata()])
        mask = f.convert("L").point(lambda v: 255 if v else 0)
        over, mask = over.resize(im.size, Image.NEAREST), mask.resize(im.size, Image.NEAREST)
        if not tiles:
            mask = mask.point(lambda v: 190 if v else 0)          # the terrain shows a little through
        return Image.composite(over, im, mask)

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

    def _labels(self):
        """([(label image, [region per label])], border mask), made once: each
        pixel holds its region's number within a group of 254 regions (0 = not
        in the group: sea, unknown or another group), top-down; towns and ports
        count as their region. A political layer is then a palette on these
        images - Pillow's work, not a Python loop over every pixel."""
        if hasattr(self, "_label_cache"):
            return self._label_cache
        names = sorted(self.info)
        groups = [names[i:i + 254] for i in range(0, len(names), 254)] or [[]]
        where = {}
        for g, chunk in enumerate(groups):
            for i, r in enumerate(chunk):
                where[self.info[r]["colour"]] = (g, i + 1)
        spot = {}
        for r, xy in list(self.cities.items()) + list(self.ports.items()):
            if r in self.info:
                spot[xy] = where[self.info[r]["colour"]]
        img, w, h = self.regions_img, self.w, self.h
        planes = [bytearray(w * h) for _ in groups]
        flat = bytearray(w * h * 3)                   # the map with towns/ports as their region, for borders
        for y in range(h):
            row = (h - 1 - y) * w
            for x in range(w):
                px = img.get(x, y)
                gi = spot.get((x, y)) or where.get(px)
                if gi:
                    planes[gi[0]][row + x] = gi[1]
                    if (x, y) in spot:
                        px = self.info[groups[gi[0]][gi[1] - 1]]["colour"]
                o = (row + x) * 3
                flat[o:o + 3] = bytes(px)
        rgb = Image.frombytes("RGB", (w, h), bytes(flat))
        self._flat_rgb = rgb
        edge = ImageChops.add(ImageChops.difference(rgb, ImageChops.offset(rgb, -1, 0)),
                              ImageChops.difference(rgb, ImageChops.offset(rgb, 0, -1))).convert("L")
        mask = edge.point(lambda v: 255 if v else 0)
        mask.paste(0, (w - 1, 0, w, h))              # offset() wraps round: no border on the far edges
        mask.paste(0, (0, h - 1, w, h))
        self._label_cache = ([(Image.frombytes("P", (w, h), bytes(p)),
                               Image.frombytes("L", (w, h), bytes(p)).point(lambda v: 255 if v else 0), g)
                              for p, g in zip(planes, groups)], mask)
        return self._label_cache

    def regions_layer(self, painted=None, colours=None, alpha=150, borders=True):
        """RGBA, 1 px per tile: every region in its own map_regions colour, borders
        dark - the Regions view, where the borders are what matters. painted
        {(x, y): region} with colours {region: rgb} shows tiles given to another
        region, borders drawn again around them (borders are not stored anywhere:
        they are where the colour changes)."""
        key = (frozenset((painted or {}).items()), borders)
        cache = getattr(self, "_regions_layers", None)
        if cache and cache[0] == key:
            return cache[1]
        layers, _ = self._labels()
        rgb = self._flat_rgb.copy()
        land = None
        for _, here, _ in layers:
            land = here if land is None else ImageChops.lighter(land, here)
        if painted:
            land = land.copy()
            for (x, y), r in painted.items():
                if r in (colours or {}) and 0 <= x < self.w and 0 <= y < self.h:
                    rgb.putpixel((x, self.h - 1 - y), tuple(colours[r]))
                    land.putpixel((x, self.h - 1 - y), 255)
        edge = ImageChops.add(ImageChops.difference(rgb, ImageChops.offset(rgb, -1, 0)),
                              ImageChops.difference(rgb, ImageChops.offset(rgb, 0, -1))).convert("L")
        mask = edge.point(lambda v: 255 if v else 0)
        mask.paste(0, (self.w - 1, 0, self.w, self.h))
        mask.paste(0, (0, self.h - 1, self.w, self.h))
        im = rgb.copy()
        im.putalpha(land.point(lambda v: alpha if v else 0))
        if borders:
            dark = Image.new("RGBA", im.size, (20, 20, 20, 150))
            im = Image.composite(dark, im, ImageChops.multiply(mask, land))
        self._regions_layers = (key, im)
        return im

    def political(self, owners, colours, highlight=None, alpha=205, borders=True, painted=None):
        """RGBA, 1 px per tile: each region in its owner's primary colour, see-through,
        borders darker (unless borders is False); the highlighted faction a little
        stronger. painted {(x, y): region}: tiles given to another region, in its
        owner's colour (the map as it will be)."""
        key = (tuple(sorted(owners.items())), tuple(sorted(colours.items())), highlight, alpha, borders,
               tuple(sorted((painted or {}).items())))
        if key in self._political:
            return self._political[key]
        layers, mask = self._labels()
        fill = dark = None
        for pimg, here, names in layers:
            flat, shade = [0, 0, 0, 0], [0, 0, 0, 0]
            for r in names:
                owner = owners.get(r)
                if owner is None:
                    flat += [0, 0, 0, 0]
                    shade += [0, 0, 0, 0]
                    continue
                rgb = REBELS if owner == "slave" else colours.get(owner, REBELS)
                a = min(255, alpha + 40) if owner == highlight else alpha
                if owner == "slave":
                    a = alpha // 4                   # rebel land barely tinted: the factions stand out
                flat += list(rgb) + [a]
                shade += [rgb[0] // 3, rgb[1] // 3, rgb[2] // 3, 200]
            pad = [0, 0, 0, 0] * (256 - len(names) - 1)
            a_img, b_img = pimg.copy(), pimg.copy()
            a_img.putpalette(flat + pad, "RGBA")
            b_img.putpalette(shade + pad, "RGBA")
            a_img, b_img = a_img.convert("RGBA"), b_img.convert("RGBA")
            # this group's pixels only: its label image is 0 elsewhere
            fill = a_img if fill is None else Image.composite(a_img, fill, here)
            dark = b_img if dark is None else Image.composite(b_img, dark, here)
        im = Image.composite(dark, fill, mask) if borders else fill
        if painted:
            im = im.copy()
            px = im.load()
            for (x, y), r in painted.items():
                if 0 <= x < self.w and 0 <= y < self.h:
                    owner = owners.get(r)
                    if owner is None:
                        px[x, self.h - 1 - y] = (0, 0, 0, 0)
                        continue
                    rgb = REBELS if owner == "slave" else colours.get(owner, REBELS)
                    a = min(255, alpha + 40) if owner == highlight else (alpha // 4 if owner == "slave" else alpha)
                    px[x, self.h - 1 - y] = tuple(rgb) + (a,)
        self._political = {key: im}
        return im

    def _political_slow(self, owners, colours, highlight=None, alpha=205):
        """The same, pixel by pixel (kept as the reference the fast one is tested against)."""
        key = (tuple(sorted(owners.items())), tuple(sorted(colours.items())), highlight, alpha)
        img = self.regions_img
        fill = {}
        for region, owner in owners.items():
            col = self.info.get(region, {}).get("colour")
            if col is None:
                continue
            rgb = REBELS if owner == "slave" else colours.get(owner, REBELS)
            a = min(255, alpha + 40) if owner == highlight else alpha
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

