"""The maps' review (2026-10-22): the Terrain editor, the land and sea, the heights, the regions' map pictures."""

import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


def _terrain_editor():
    try:
        from campaign_editor.gui_terrain import TerrainEditor
    except ImportError:                                  # CI's test job may lack tkinter here
        return None
    return TerrainEditor


class TerrainCampaignTest(unittest.TestCase):
    def _editor(self, camp):
        strokes = {"ground": {(1, 1): (0, 64, 0)}}
        me = SimpleNamespace(
            app=SimpleNamespace(v_campaign=SimpleNamespace(get=lambda: camp[0]), mod=SimpleNamespace(data="D")),
            mod=SimpleNamespace(data="D"), ground=dict(strokes["ground"]), features={}, climate={}, heights={},
            coast={}, cpx={"regions": {}, "ground": {}, "heights": {}, "hgt": {}}, _sig="same", _camp="a",
            _rtiles={"Latium": 3}, _last_river=(4, 4), _sea=(1, 2, 3), view=None, cmap="old map", shown=[],
            v_coast_region=SimpleNamespace(get=lambda: "", set=lambda v: None))
        TE = _terrain_editor()
        me.dirty = lambda: TE.dirty(me)
        me.pending = lambda: TE.pending(me)
        me._signature = lambda: "same"
        me.show = lambda: me.shown.append(camp[0])
        return me

    def test_another_campaign_drops_the_old_maps_strokes_and_counts(self):
        """The Terrain editor kept the strokes and its map of the campaign picked before: after another campaign
        Apply wrote them into the new one's pictures, and Maps > 3D painted on the old map's tiles."""
        TE = _terrain_editor()
        if TE is None:
            self.skipTest("no tkinter")
        camp = ["b"]
        me = self._editor(camp)
        with mock.patch("campaign_editor.moddata.ModData", lambda data: SimpleNamespace(data=data)), \
                mock.patch("campaign_editor.regiondelete.can_waste", lambda mod: False):
            lost = TE.rebind(me, me.app.mod)
        self.assertEqual(lost, 0)                       # asked by the App already: no 'written since' warning
        self.assertEqual((me.ground, me._rtiles, me._last_river, me._camp, me.cmap), ({}, None, None, "b", None))
        self.assertEqual(me.shown, ["b"])
        self.assertFalse(hasattr(me, "_sea"))           # the sea's colour read again from the new map
        # the same campaign again: the strokes stay
        me = self._editor(["a"])
        me.app.v_campaign = SimpleNamespace(get=lambda: "a")
        with mock.patch("campaign_editor.moddata.ModData", lambda data: SimpleNamespace(data=data)), \
                mock.patch("campaign_editor.regiondelete.can_waste", lambda mod: False):
            TE.rebind(me, me.app.mod)
        self.assertEqual(me.ground, {(1, 1): (0, 64, 0)})
        self.assertIsNone(me._rtiles)                   # counted again on the files as read now

    def test_a_stroke_after_another_campaign_binds_the_new_map(self):
        TE = _terrain_editor()
        if TE is None:
            self.skipTest("no tkinter")
        bound = []
        me = SimpleNamespace(mod=SimpleNamespace(data="D"), _camp="a", cmap="map",
                             app=SimpleNamespace(mod="M", v_campaign=SimpleNamespace(get=lambda: "b")),
                             rebind=bound.append)
        self.assertTrue(TE._bound(me))
        self.assertEqual(bound, ["M"])
        bound.clear()
        me._camp = "b"
        TE._bound(me)
        self.assertEqual(bound, [])


class ClimatesViewTest(unittest.TestCase):
    def test_the_climates_tint_by_pillow_is_the_tile_by_tile_one(self):
        """The Climates mode's tint was worked out tile by tile in Python (a second on a big map at every stroke):
        now by Pillow - the same picture, the sea left out (a town or port pixel never counts as sea)."""
        try:
            from PIL import ImageChops
            from campaign_editor.mapdata import CampaignMap
        except ImportError:
            self.skipTest("no Pillow")
        from campaign_editor.tga import Image as Tga
        w, h = 6, 4
        ground, climates = Tga(2 * w + 1, 2 * h + 1), Tga(2 * w + 1, 2 * h + 1)
        regions = Tga(w, h)
        for y in range(2 * h + 1):
            for x in range(2 * w + 1):
                ground.set(x, y, (64, 0, 0) if x < 5 else (0, 128, 128))
                climates.set(x, y, (10 * (x % 3), 20 * (y % 4), 200))
        for y in range(h):
            for x in range(w):
                regions.set(x, y, (41, 140, 233) if x < 2 else (200, 10, 10))
        regions.set(1, 1, (255, 255, 255))                     # a port pixel on a sea ground's tile
        maps = {"map_climates.tga": climates, "map_ground_types.tga": ground}
        cm = CampaignMap.__new__(CampaignMap)
        cm.mod = SimpleNamespace(_optional_map=lambda camp, name: maps.get(name))
        cm.campaign, cm.w, cm.h, cm.regions_img, cm.ground = "c", w, h, regions, ground
        cm.by_colour, cm.info = {(200, 10, 10): "Latium"}, {"Latium": {"colour": (200, 10, 10)}}
        for sea in (False, True):
            cm.show_sea_climates = sea
            im = cm._tiles()
            fast = cm._climates(im)
            cm._climates_fast = lambda s: None
            slow = cm._climates(im)
            del cm._climates_fast
            self.assertIsNone(ImageChops.difference(fast, slow).getbbox(), sea)
        self.assertIsNotNone(cm._climates_fast(False))


class ResourceOnWastelandTest(unittest.TestCase):
    def setUp(self):
        from campaign_editor.minimod import make
        self.root = tempfile.mkdtemp()
        make(self.root)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_a_resource_put_on_a_wasteland_is_warned_in_medieval2(self):
        """Medieval II refuses a resource in a region without a town (report #186): one moved or added there on the
        map went in silently - only Check mod files named it after the write. Now the write says so (kept: freedom)."""
        from campaign_editor import regiondelete as RD, resources as RS
        from campaign_editor.minimod import write
        from campaign_editor.moddata import ModData
        from campaign_editor.plan import Plan
        write(os.path.join(self.root, "data", "descr_ex.txt"), "max_factions 31\n")
        write(os.path.join(self.root, "data", "descr_religions.txt"), "religions\n{\n\tcatholic\n}\n")
        mod = ModData(self.root)
        land = sorted(set(RD.region_pixels(mod, "test", "B_R")) - {mod.city_tiles("test")["B_R"]})
        plan = Plan(mod, "delete", "B_R", {})
        RD.delete(plan, "test", "B_R", waste=True)
        plan.apply()
        mod = ModData(self.root)
        kind = next(iter(RS.types(mod)), "silk")
        plan = Plan(mod, "resources", "test", {})
        RS.apply(plan, "test", {"added": [{"type": kind, "xy": land[0]}]})
        self.assertTrue(any("B_R, a wasteland" in w for _, w in plan.warnings), plan.warnings)
        self.assertIn(kind, [r.kind for r in RS.read(plan.files[mod.campaign_file("test", "descr_strat.txt")])])
        os.remove(os.path.join(self.root, "data", "descr_religions.txt"))             # Rome: nothing said
        mod = ModData(self.root)
        plan = Plan(mod, "resources", "test", {})
        RS.apply(plan, "test", {"added": [{"type": kind, "xy": land[0]}]})
        self.assertFalse(any("wasteland" in w for _, w in plan.warnings))


    def test_a_wastelands_town_never_touches_another_region_at_a_corner_in_medieval2(self):
        """A wasteland given its town again (Place its town) checked only the tile's four sides: a tile touching
        another region at a corner went through - Medieval II stops on it (the rule every other town placing keeps).
        Rome: allowed (its vanilla never does it, HLR's REX plays with a few)."""
        from campaign_editor import regiondelete as RD
        from campaign_editor.minimod import write
        from campaign_editor.moddata import ModData
        from campaign_editor.plan import Plan
        write(os.path.join(self.root, "data", "descr_ex.txt"), "max_factions 31\n")
        write(os.path.join(self.root, "data", "descr_religions.txt"), "religions\n{\n\tcatholic\n}\n")
        from campaign_editor.minimod import write_tga
        mod = ModData(self.root)
        a, b = (mod.regions("test")[r]["colour"] for r in ("A_R", "B_R"))
        px = [[a if x < 4 else b for x in range(9)] for y in range(9)]   # a map big enough for an inner tile
        px[4][1], px[4][6] = (0, 0, 0), (0, 0, 0)
        write_tga(mod.campaign_file("test", "map_regions.tga"), 9, 9, px)
        for name in ("map_ground_types.tga", "map_features.tga", "map_heights.tga"):
            if mod.campaign_file("test", name):                 # (their old size no longer fits: not read)
                os.remove(mod.campaign_file("test", name))
        mod = ModData(self.root)
        plan = Plan(mod, "delete", "B_R", {})
        RD.delete(plan, "test", "B_R", waste=True)
        plan.apply()
        mod = ModData(self.root)
        img, col = mod.region_map("test"), mod.regions("test")["B_R"]["colour"]
        other = next(v["colour"] for r, v in mod.regions("test").items() if r != "B_R")
        inside = [(x, y) for x in range(2, img.width - 2) for y in range(2, img.height - 2)
                  if all(img.get(x + a, y + b) == col for a in (-1, 0, 1) for b in (-1, 0, 1))
                  and not mod.land_problem("test", (x, y))]
        self.assertTrue(inside, "the fixture's B_R has an inner tile")
        x, y = inside[0]

        def corner(mod):                                # another region's land at the tile's corner (in memory)
            mod.region_map("test").set(x + 1, y + 1, other)
            return mod
        self.assertIsNone(RD.town_problem(mod, "test", "B_R", (x, y)))
        why = RD.town_problem(corner(ModData(self.root)), "test", "B_R", (x, y))
        self.assertIn("8 tiles round a town", why or "")
        os.remove(os.path.join(self.root, "data", "descr_religions.txt"))
        self.assertIsNone(RD.town_problem(corner(ModData(self.root)), "test", "B_R", (x, y)))


if __name__ == "__main__":
    unittest.main()
