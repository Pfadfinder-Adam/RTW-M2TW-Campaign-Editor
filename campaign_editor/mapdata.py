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


def recolour(im, table, default):
    """im (RGB) with each colour c drawn as table.get(c, default). Pillow does it through a palette (a map of
    millions of tiles in a moment); the result is checked against the source and done pixel by pixel instead
    when a palette cannot hold it exactly (more than 256 colours, or colours too close for Pillow's lookup)."""
    cols = im.getcolors(256)
    if cols:
        src = [c for _, c in cols]
        pad = 256 - len(src)
        pal = Image.new("P", (1, 1))
        pal.putpalette([v for c in src + [src[0]] * pad for v in c])
        q = im.quantize(palette=pal, dither=Image.Dither.NONE)
        back = q.convert("RGB")
        if ImageChops.difference(back, im).getbbox() is None:           # every pixel found its own colour
            q.putpalette([v for c in src + [src[0]] * pad for v in table.get(c, default)])
            return q.convert("RGB")
    out = Image.new("RGB", im.size)
    b = im.tobytes()                             # not getdata(): Pillow 14 drops it
    out.putdata([table.get(p, default) for p in zip(b[0::3], b[1::3], b[2::3])])
    return out


def label_table(src, where, group):
    """The 256-entry table that turns a palette index into the region's number within `group` (0 = none): src the
    palette's colours (fewer than 256 - the rest of the table is 0), where {colour: (group, number)}. A map with
    fewer than 256 region colours crashed here (IndexError, a tester's 'paneuroafricasia' map, 0.20.x)."""
    out = []
    for j in range(256):
        g, n = where.get(src[j], (-1, 0)) if j < len(src) else (-1, 0)
        out.append(n if g == group else 0)
    return out


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
        # the heights: the map view adds the point under the mouse exactly (height_point) - a tile has 2 x 2 points
        if region and px not in (CITY, PORT) and not self.is_sea(x, y):
            why = self.mod.land_problem(self.campaign, (x, y))
            parts.append("armies and agents may stand here" if not why else "no one can stand here: " + why)
        return "   ".join(parts)

    def _ports(self):
        from .mapedit import ports                    # the one reader of port pixels
        return dict(ports(self.mod, self.campaign))

    # ---- pictures (top-down, as Pillow draws them) ----
    def background(self, relief=False, rivers=False):
        """The map drawn from map_ground_types.tga - each tile's terrain type, the
        information that matters here (the game's painted radar map is left alone
        by choice). Returned at 2 px per tile, every tile one square in the colour
        of the ground at its middle (what the tool checks and every brush paints);
        relief: shaded from map_heights.tga; rivers: map_features.tga's rivers,
        fords and cliffs."""
        if getattr(self, "show_heights", False):
            return self.heights_view()                  # the Terrain editor's Heights mode: map_heights itself
        climates = bool(getattr(self, "show_climates", False))
        key = (bool(relief), bool(rivers), climates)
        cache = self.__dict__.setdefault("_backgrounds", {})
        if key not in cache:
            # everything worked out per tile, then blown up: each square one colour, nothing
            # bleeds into the next tile (the grid and the picture agree)
            im = self._tiles()
            if climates:
                im = self._climates(im)
            if relief:
                im = self._relief(im)
            if rivers:
                im = self._rivers(im)
            cache[key] = im.resize((2 * self.w, 2 * self.h), Image.NEAREST)
        return cache[key]

    def _tiles(self):
        """One pixel per tile, top-down, in its ground's colour (the tile's middle)."""
        g = self.ground
        if g is not None and (g.width, g.height) == (2 * self.w + 1, 2 * self.h + 1):
            full = Image.frombytes("RGB", (g.width, g.height), g.rgb_top_down())
            middles = full.resize((self.w, self.h), Image.NEAREST, box=(0, 0, 2 * self.w, 2 * self.h))
            return recolour(middles, GROUND_LOOK, (150, 150, 150))
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

    @staticmethod
    def height_look(c):
        """How a map_heights.tga pixel is drawn: land in grey (brightened, so the low land - most of
        vanilla's, 10-20 of 255 - is not all black), the sea blue, darker where deeper."""
        if c[0] == c[1] == c[2]:
            g = int(round(255 * (c[0] / 255.0) ** 0.5))
            return g, g, g
        d = max(0, min(255, c[2]))
        return 20, 40 + (d - 145) // 3 if d > 145 else 30, 60 + (d - 100) // 2 if d > 100 else 50

    def heights_view(self):
        """map_heights.tga as drawn (height_look), at 2 px per tile like background(); kept and changed
        pixel by pixel (set_height) while the heights brush sprays."""
        if getattr(self, "_hpil", None) is None:
            t = self.mod._optional_map(self.campaign, "map_heights.tga")
            if t is None:
                return self._tiles().resize((2 * self.w, 2 * self.h), Image.NEAREST)
            self._hpil = self._height_picture(t)
        im = self._hpil
        view = im.crop((0, 1, 2 * self.w, 2 * self.h + 1)) if im.size == (2 * self.w + 1, 2 * self.h + 1) else \
            im.resize((2 * self.w, 2 * self.h), Image.BILINEAR)
        return view

    def _height_picture(self, t):
        """height_look() of every pixel of map_heights.tga t, top-down - done by Pillow per channel (grey land
        and the blue sea told apart by a mask), not pixel by pixel in Python."""
        im = Image.frombytes("RGB", (t.width, t.height), t.rgb_top_down())
        r, g, b = im.split()
        grey = r.point([self.height_look((v, v, v))[0] for v in range(256)])
        land = Image.merge("RGB", (grey, grey, grey))
        sea = Image.merge("RGB", [b.point([self.height_look((0, 0, v))[k] for v in range(256)]) for k in range(3)])
        other = ImageChops.lighter(ImageChops.difference(r, g), ImageChops.difference(g, b)).point(
            lambda v: 255 if v else 0)
        return Image.composite(sea, land, other)

    def set_height(self, px, py, value):
        """The drawn heights picture follows one changed pixel (px, py bottom-up, grey value)."""
        im = getattr(self, "_hpil", None)
        if im is not None and 0 <= px < im.width and 0 <= py < im.height:
            im.putpixel((px, im.height - 1 - py), self.height_look((value, value, value)))

    def height_point(self, px, py):
        """map_heights pixel (px, py) (bottom-up, 2 per tile, 2W+1 x 2H+1) in plain words: land grey and metres, or
        water and its depth; with map_heights.hgt (the game reads it instead of the picture) its own value too."""
        from .terrain import max_land_height, min_sea_height
        t = self.mod._optional_map(self.campaign, "map_heights.tga")
        if t is None or not (0 <= px < t.width and 0 <= py < t.height):
            return ""
        c = t.get(px, py)                                    # the brush paints into this picture: shown as painted
        top, low = max_land_height(self.mod, self.campaign), min_sea_height(self.mod, self.campaign)
        if c[0] == c[1] == c[2]:
            text = "point %d, %d: land, grey %d of 255 (about %d m%s)" % (
                px, py, c[0], round(c[0] * top / 255), "; 0 = the lowest land, still above the water" if c[0] == 0
                else "")
        else:
            text = "point %d, %d: water, blue %d (sea floor about %d m; the water's surface is 0)" % (
                px, py, c[2], round(low * (255 - c[2]) / 255))
        hv = self._hgt_at(px, py)
        if hv is not None:
            text += "   (map_heights.hgt in the file: %.1f)" % hv
        return text

    def _hgt_at(self, px, py):
        if "_hgt" not in self.__dict__:
            import struct
            from array import array
            path = self.mod.campaign_file(self.campaign, "map_heights.hgt")
            self._hgt = None
            if path:
                with open(path, "rb") as fh:
                    raw = fh.read()
                w, h = struct.unpack("<II", raw[:8])
                vals = array("f")
                vals.frombytes(raw[8:8 + 4 * w * h])
                if len(vals) == w * h:
                    self._hgt = (w, h, vals)
        if self._hgt is None:
            return None
        w, h, vals = self._hgt
        return vals[py * w + px] if 0 <= px < w and 0 <= py < h else None

    def height_at(self, x, y):
        """The grey of tile (x, y)'s middle in map_heights.tga (land), or None (the sea, no file)."""
        t = self.mod._optional_map(self.campaign, "map_heights.tga")
        if t is None or not (0 <= 2 * x + 1 < t.width and 0 <= 2 * y + 1 < t.height):
            return None
        c = t.get(2 * x + 1, 2 * y + 1)
        return c[0] if c[0] == c[1] == c[2] else None

    def _pil(self, name):
        """A campaign map file as a top-down Pillow picture, or None."""
        t = self.mod._optional_map(self.campaign, name)
        if t is None:
            return None
        return Image.frombytes("RGB", (t.width, t.height), t.rgb_top_down())

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

    def _rivers(self, im):
        """map_features.tga's non-black tiles drawn over the ground, each kind in its colour."""
        f = self._pil("map_features.tga")
        if f is None or f.size != (self.w, self.h):
            return im
        over = recolour(f, self.FEATURE_LOOK, (50, 105, 200))
        mask = f.convert("L").point(lambda v: 255 if v else 0)
        over, mask = over.resize(im.size, Image.NEAREST), mask.resize(im.size, Image.NEAREST)
        return Image.composite(over, im, mask)

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
        rgb = Image.frombytes("RGB", (w, h), img.rgb_top_down())
        for (x, y), gi in spot.items():                # towns and ports drawn as their region
            if 0 <= x < w and 0 <= y < h:
                rgb.putpixel((x, h - 1 - y), tuple(self.info[groups[gi[0]][gi[1] - 1]]["colour"]))
        planes = None
        cols = rgb.getcolors(256)
        if cols:                                       # few colours: Pillow maps them through a palette
            src = [c for _, c in cols]
            pal = Image.new("P", (1, 1))
            pal.putpalette([v for c in src + [src[0]] * (256 - len(src)) for v in c])
            q = rgb.quantize(palette=pal, dither=Image.Dither.NONE)
            if ImageChops.difference(q.convert("RGB"), rgb).getbbox() is None:
                index = Image.frombytes("L", (w, h), q.tobytes())
                planes = [index.point(label_table(src, where, g)).tobytes() for g in range(len(groups))]
        if planes is None:                             # many colours (HLR's hundreds of regions): row by row
            planes = [bytearray(w * h) for _ in groups]
            raw = rgb.tobytes()
            code = {bytes(c): gi for c, gi in where.items()}
            for o in range(0, w * h):
                gi = code.get(raw[3 * o:3 * o + 3])
                if gi:
                    planes[gi[0]][o] = gi[1]
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

