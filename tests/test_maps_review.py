"""The maps' review (2026-10-22): the Terrain editor, the land and sea, the heights, the regions' map pictures."""

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


if __name__ == "__main__":
    unittest.main()
