"""The Map's Scripts layer (scriptmap.py): the places a script names, dragged and edited."""

import os
import tempfile
import unittest

from campaign_editor import scriptmap as SM
from campaign_editor.textio import TextFile

SCRIPT = ("script\r\n"
          "monitor_event FactionTurnStart FactionType romans_julii\r\n"
          "    spawn_army\r\n"
          "        faction romans_julii\r\n"
          "        character Flavius, named character, age 30, x 12, y 34\r\n"
          "        unit roman generals guard cavalry exp 0\r\n"
          "    end\r\n"
          "    move_strat_camera 5 6 ; and the camera\r\n"
          "    reveal_area 1 2 3 4\r\n"
          "end_monitor\r\n"
          "\r\n"
          "wait 1\r\n")


class FakePlan:
    def __init__(self):
        self.files, self.notes = {}, []

    def edit(self, path):
        if path not in self.files:
            self.files[path] = TextFile.load(path)
        return self.files[path]

    def note(self, f, msg):
        self.notes.append(msg)


class ScriptMapTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "campaign_script.txt")
        with open(self.path, "wb") as fh:
            fh.write(SCRIPT.encode("latin-1"))

    def test_places_of_a_line(self):
        self.assertEqual(SM.places_in("character Flavius, age 30, x 12, y 34"), [(12, 34)])
        self.assertEqual(SM.places_in("reveal_area 1 2 3 4"), [(1, 2), (3, 4)])
        self.assertEqual(SM.places_in("move_strat_camera 5 6 ; 7 8"), [(5, 6)])
        self.assertEqual(SM.places_in("unit roman generals guard cavalry exp 0"), [])

    def test_one_place_moved_the_rest_kept(self):
        self.assertEqual(SM.moved("reveal_area 1 2 3 4", 1, (30, 40)), "reveal_area 1 2 30 40")
        self.assertEqual(SM.moved("x 12, y 34", 0, (7, 8)), "x 7, y 8")

    def test_drag_writes_the_line_with_its_ending(self):
        rs = SM.rows(self.path)
        spot = {"path": self.path, "line": 4, "sub": 0, "k": 0, "code": False}
        self.assertIn("x 12, y 34", rs[4][2])
        edits = SM.move_spot({}, spot, (50, 60))
        self.assertEqual(list(edits[self.path]), [4])
        self.assertIn("x 50, y 60", edits[self.path][4])
        back = SM.move_spot(edits, spot, (12, 34))            # put back where it was: no edit left
        self.assertEqual(back, {})
        plan = FakePlan()
        SM.apply(plan, edits)
        out = plan.files[self.path].dump().decode("latin-1")
        self.assertEqual(out, SCRIPT.replace("x 12, y 34", "x 50, y 60"))

    def test_block_and_its_edit(self):
        rs = SM.rows(self.path)
        a, b = SM.block(rs, 4)
        self.assertEqual((a, b), (0, 10))                      # the monitor as far as the blank line
        text = "\n".join(r[2] for r in rs[a:b])
        edits = SM.set_block({}, self.path, rs, a, b, text.replace("5 6", "9 9"))
        self.assertEqual(edits, {self.path: {7: "    move_strat_camera 9 9 ; and the camera"}})
        # more lines than before: all into the first line, the others taken out; written byte for byte
        new = text + "\n    reveal_tile 2 2"
        edits = SM.set_block({}, self.path, rs, a, b, new)
        self.assertEqual(sorted(k for k, v in edits[self.path].items() if v is None), list(range(1, 10)))
        rs2 = SM.rows(self.path, edits)
        self.assertEqual([r[2] for r in rs2][:11], new.split("\n"))
        plan = FakePlan()
        SM.apply(plan, edits)
        self.assertEqual(plan.files[self.path].dump().decode("latin-1"),
                         SCRIPT.replace("end_monitor\r\n", "end_monitor\r\n    reveal_tile 2 2\r\n"))

    def test_spots_follow_the_edits(self):
        class Mod:
            data = self.dir
        import campaign_editor.upscale as U
        old = U.script_files
        U.script_files = lambda mod, campaign: [self.path]
        try:
            got = [(s["line"], s["k"], s["xy"]) for s in SM.spots(Mod(), "imperial_campaign")]
            self.assertEqual(got, [(4, 0, (12, 34)), (7, 0, (5, 6)), (8, 0, (1, 2)), (8, 1, (3, 4))])
            sp = SM.spots(Mod(), "imperial_campaign")[3]
            edits = SM.move_spot({}, sp, (20, 21))
            got = [s["xy"] for s in SM.spots(Mod(), "imperial_campaign", edits)]
            self.assertEqual(got[3], (20, 21))
        finally:
            U.script_files = old


if __name__ == "__main__":
    unittest.main()
