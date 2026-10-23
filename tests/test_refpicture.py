"""The reference picture over the campaign map (refpicture): where it lies on the tiles, how see-through it is,
the PureRef keys, kept between starts."""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from PIL import Image
except ImportError:                                     # CI's test job has no Pillow (the exe has it)
    Image = None

CTRL, SHIFT = 0x4, 0x1


def key(keysym, keycode=0):
    return SimpleNamespace(keysym=keysym, keycode=keycode)


@unittest.skipIf(Image is None, "Pillow")
class RefPictureTest(unittest.TestCase):
    def setUp(self):
        from campaign_editor import refpicture
        self.rp = refpicture
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "real map.png")
        im = Image.new("RGBA", (40, 20), (255, 0, 0, 255))
        im.putpixel((0, 0), (0, 0, 255, 255))           # its top left corner blue
        im.save(self.path)

    def test_opened_on_the_whole_map(self):
        r = self.rp.RefPicture()
        r.open(self.path, 100, 50)
        self.assertEqual((r.x, r.y, r.w, r.h), (0, 0, 100, 50))
        self.assertTrue(r.visible() and r.locked)

    def test_view_lies_on_the_tiles(self):
        r = self.rp.RefPicture()
        r.open(self.path, 40, 20)
        r.set_opacity(1.0)
        v = r.view(0, 0, 2, (80, 40))                  # 2 px a tile: the picture fills the view
        self.assertEqual(v.size, (80, 40))
        self.assertEqual(v.getpixel((79, 39))[:3], (255, 0, 0))
        r.smooth = False
        v = r.view(0, 0, 2, (80, 40))
        self.assertEqual(v.getpixel((0, 0)), (0, 0, 255, 255))
        v = r.view(-10, 0, 2, (80, 40))                # the view 10 tiles left of the map: the picture starts at 20 px
        self.assertEqual(v.getpixel((19, 5))[3], 0)
        self.assertEqual(v.getpixel((20, 0)), (0, 0, 255, 255))
        self.assertIsNone(r.view(100, 0, 2, (80, 40)))  # out of sight
        r.shown = False
        self.assertIsNone(r.view(0, 0, 2, (80, 40)))

    def test_far_zoom_costs_the_view_only(self):
        r = self.rp.RefPicture()
        r.open(self.path, 40, 20)
        v = r.view(5, 5, 64, (300, 200))
        self.assertEqual(v.size, (300, 200))

    def test_opacity_and_flips(self):
        r = self.rp.RefPicture()
        r.open(self.path, 40, 20)
        r.smooth = False
        r.set_opacity(0.5)
        self.assertAlmostEqual(r.view(0, 0, 1, (40, 20)).getpixel((5, 5))[3], 128, delta=1)
        r.nudge_opacity(1)
        self.assertAlmostEqual(r.opacity, 0.6)
        r.opacity = 0.45
        r.nudge_opacity(1)
        self.assertAlmostEqual(r.opacity, 0.5)          # onto the next whole tenth, as the keys go
        for _ in range(20):
            r.nudge_opacity(-1)
        self.assertAlmostEqual(r.opacity, self.rp.LEAST_OPACITY)    # never quite gone
        r.flip_h = r.flip_v = True
        r.set_opacity(1)
        self.assertEqual(r.view(0, 0, 1, (40, 20)).getpixel((39, 19)), (0, 0, 255, 255))
        r.grey = True
        px = r.view(0, 0, 1, (40, 20)).getpixel((5, 5))
        self.assertEqual(px[0], px[1])

    def test_onto_the_map_picture(self):
        r = self.rp.RefPicture()
        r.open(self.path, 40, 20)
        r.set_opacity(0.5)
        pic = Image.new("RGB", (40, 20), (0, 0, 0))
        out = r.onto(pic, 0, 0, 1)
        self.assertEqual(out.mode, "RGB")
        self.assertAlmostEqual(out.getpixel((5, 5))[0], 128, delta=2)

    def test_scale_keeps_the_point_under_the_mouse(self):
        r = self.rp.RefPicture()
        r.open(self.path, 40, 20)
        r.scale(2, (10, 5))
        self.assertEqual((r.x, r.y, r.w, r.h), (-10, -5, 80, 40))
        r.w, r.h = 80, 80                               # stretched
        r.own_shape()
        self.assertEqual((r.w, r.h), (80, 40))

    def test_kept_and_restored(self):
        r = self.rp.RefPicture()
        r.open(self.path, 40, 20)
        r.move(3, -2)
        r.set_opacity(0.3)
        r.front, r.flip_h, r.locked = True, True, False
        s = r.state()
        q = self.rp.RefPicture()
        self.assertTrue(q.restore(s))
        self.assertEqual((q.x, q.y, q.opacity, q.front, q.flip_h), (3, -2, 0.3, True, True))
        self.assertTrue(q.locked)                       # never opens grabbing the left button
        self.assertFalse(self.rp.RefPicture().restore(dict(s, path=os.path.join(self.tmp, "gone.png"))))
        cmap = SimpleNamespace(mod=SimpleNamespace(data=self.tmp), campaign="imperial_campaign")
        store = {}
        with mock.patch("campaign_editor.settings.get", lambda k, d=None: store.get(k, d)), \
                mock.patch("campaign_editor.settings.put", lambda k, v: store.__setitem__(k, v)):
            self.rp.keep(cmap, r)
            self.assertEqual(self.rp.kept(cmap)["path"], r.path)
            other = SimpleNamespace(mod=cmap.mod, campaign="other")
            self.assertIsNone(self.rp.kept(other))      # each campaign its own
            r.clear()
            self.rp.keep(cmap, r)
            self.assertIsNone(self.rp.kept(cmap))


class KeysTest(unittest.TestCase):
    """The keys are PureRef's, in any keyboard layout; none takes one the editor already uses."""

    def act(self, e, state=0, alt=False):
        from campaign_editor.refpicture import action_of
        return action_of(e, bool(state & CTRL), bool(state & SHIFT), alt)

    def test_pureref_keys(self):
        self.assertEqual(self.act(key("plus"), CTRL | SHIFT), "more")
        self.assertEqual(self.act(key("equal"), CTRL | SHIFT), "more")
        self.assertEqual(self.act(key("underscore"), CTRL | SHIFT), "less")
        self.assertEqual(self.act(key("i"), CTRL), "open")
        self.assertEqual(self.act(key("Y"), CTRL | SHIFT), "show")
        self.assertEqual(self.act(key("T"), CTRL | SHIFT), "fit")
        self.assertEqual(self.act(key("Down"), CTRL, alt=True), "own_shape")
        self.assertEqual(self.act(key("l"), alt=True), "lock")
        self.assertEqual(self.act(key("g"), alt=True), "grey")
        self.assertEqual(self.act(key("t"), alt=True), "smooth")
        self.assertEqual(self.act(key("H"), SHIFT, alt=True), "flip_h")
        self.assertEqual(self.act(key("V"), SHIFT, alt=True), "flip_v")
        self.assertEqual(self.act(key("Up")), "front")
        self.assertEqual(self.act(key("Down")), "back")

    def test_any_layout(self):
        # a Russian layout: Tk names the key by its own letter, the key's code still says which one
        self.assertEqual(self.act(key("Cyrillic_de", 76), alt=True), "lock")
        self.assertEqual(self.act(key("Cyrillic_sha", 73), CTRL), "open")
        self.assertEqual(self.act(key("Cyrillic_EN", 89), CTRL | SHIFT), "show")

    def test_editor_keys_left_alone(self):
        for e, state in ((key("z"), CTRL), (key("Z"), CTRL | SHIFT), (key("y"), CTRL), (key("s"), CTRL),
                         (key("p"), CTRL), (key("Cyrillic_ya", 90), CTRL), (key("Left"), 0), (key("a"), 0)):
            self.assertIsNone(self.act(e, state), e)

    def test_every_shortcut_listed_is_answered(self):
        from campaign_editor import refpicture
        actions = {"open", "show", "more", "less", "lock", "fit", "own_shape", "flip_h", "flip_v", "grey", "smooth",
                   "front", "back"}
        said = " ".join(k for k, _w, _p in refpicture.SHORTCUTS)
        for k in ("Ctrl+I", "Ctrl+Shift+Y", "Ctrl+Shift+=", "Alt+L", "Ctrl+Shift+T", "Ctrl+Alt+Down", "Alt+Shift+H",
                  "Alt+Shift+V", "Alt+G", "Alt+T", "Up", "Down", "Ctrl+Alt+Shift", "Ctrl+Alt + left drag"):
            self.assertIn(k, said)
        self.assertEqual(len(actions), 13)


class OnTheMapTest(unittest.TestCase):
    """The map view: the left button is the picture's only while it is unlocked (Alt+L); Ctrl+Alt+Shift drags its
    opacity any time it shows; the window follows the keys."""

    def test_drag_keys_window(self):
        try:
            import tkinter as tk
            from campaign_editor.gui_map import MapView
            root = tk.Tk()
        except Exception as e:                        # no tkinter / display / Pillow (CI): not tested here
            self.skipTest("no window: %s" % e)
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "ref.png")
        Image.new("RGB", (50, 50), (0, 128, 0)).save(path)
        try:
            v = MapView(root)
            v.pack()
            root.update()
            v.render = lambda: None
            v._ref_kept = lambda: None                 # no settings written by a test
            v.cmap = SimpleNamespace(w=50, h=50, cities={}, ports={})
            v.z, v.ox, v.oy = 10, 0.0, 0.0
            v.ref.open(path, 50, 50)
            ev = lambda x, y, state=0: SimpleNamespace(x=x, y=y, num=1, state=state)      # noqa: E731
            self.assertFalse(v._ref_press(ev(20, 20)))          # locked: the map's own
            v._ref_key(SimpleNamespace(keysym="l", keycode=76, state=v_alt()))
            self.assertFalse(v.ref.locked)
            v._press(ev(20, 20))
            v._move(ev(70, 120))
            v._release(ev(70, 120))
            self.assertEqual((v.ref.x, v.ref.y), (5, 10))      # 50 / 100 px at 10 px a tile
            v._press(ev(0, 0, CTRL | SHIFT | v_alt()))
            v._move(ev(-300, 0, CTRL | SHIFT | v_alt()))
            v._release(ev(-300, 0))
            from campaign_editor.refpicture import LEAST_OPACITY
            self.assertAlmostEqual(v.ref.opacity, LEAST_OPACITY)
            w = v.ref_window()
            root.update()
            v._ref_key(SimpleNamespace(keysym="plus", keycode=187, state=CTRL | SHIFT))
            self.assertEqual(w.lbl_op.cget("text"), "10 %")              # 5 % -> the next whole tenth
            v._ref_key(SimpleNamespace(keysym="Up", keycode=38, state=0))
            self.assertTrue(w.v_front.get())
            v._ref_front(200, 200)                               # over the signs: a picture on the canvas
            self.assertTrue(v.canvas.find_withtag("refpic"))
        finally:
            root.destroy()


def v_alt():
    return 0x20000 if sys.platform == "win32" else 0x0010 if sys.platform == "darwin" else 0x0008


if __name__ == "__main__":
    unittest.main()
