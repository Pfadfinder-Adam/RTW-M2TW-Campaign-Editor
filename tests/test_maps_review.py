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


if __name__ == "__main__":
    unittest.main()
