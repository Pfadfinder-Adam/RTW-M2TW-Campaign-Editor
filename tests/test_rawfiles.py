"""Any game file, as it is written (rawfiles.py): every text file the game reads listed the way the engine finds it,
written through a Plan with only the typed lines changed, the game's own file becoming the mod's copy."""

import hashlib
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from campaign_editor import rawfiles as RF                  # noqa: E402
from campaign_editor.minimod import make as make_minimod, write  # noqa: E402
from campaign_editor.moddata import ModData                  # noqa: E402
from campaign_editor.newmod import create_mod                # noqa: E402
from campaign_editor.plan import Plan, restore               # noqa: E402


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


class RawFilesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        make_minimod(self.root)

    def test_every_text_file_is_listed_and_binaries_are_not(self):
        data = os.path.join(self.root, "data")
        write(os.path.join(data, "descr_geography_new.db"), "binary")
        write(os.path.join(data, "descr_campaign_db.xml"), "<root/>\n")
        rels = [f["rel"] for f in RF.listing(ModData(self.root))]
        self.assertIn("descr_sm_factions.txt", rels)
        self.assertIn("descr_campaign_db.xml", rels)
        self.assertNotIn("descr_geography_new.db", rels)
        self.assertEqual(rels, sorted(rels, key=str.lower))

    def test_only_the_typed_lines_change_and_restore_brings_the_file_back(self):
        mod = ModData(self.root)
        path = mod.file("sm_factions")
        before = digest(path)
        with open(path, "rb") as fh:
            raw = fh.read()
        lines = mod.load(path).texts()
        i = next(k for k, t in enumerate(lines) if t.strip())
        new = list(lines)
        new[i] = new[i] + " ; mine"
        new.insert(i + 1, "; a line of my own")
        plan = Plan(mod, "raw_files", "raw_files", {})
        self.assertEqual(RF.plan_lines(plan, path, new), 2)
        bdir = plan.apply()
        with open(path, "rb") as fh:
            after = fh.read()
        self.assertIn(b" ; mine\r\n; a line of my own\r\n", after)    # the file's own line ending kept
        self.assertEqual(after.replace(b" ; mine", b"").replace(b"; a line of my own\r\n", b""), raw)
        restore(ModData(self.root), bdir)
        self.assertEqual(digest(path), before)

    def test_nothing_typed_is_no_change(self):
        mod = ModData(self.root)
        path = mod.file("sm_factions")
        plan = Plan(mod, "raw_files", "raw_files", {})
        self.assertEqual(RF.plan_lines(plan, path, mod.load(path).texts()), 0)
        self.assertEqual(plan.changed_files(), [])

    def test_a_game_file_under_a_thin_mod_is_written_as_the_mods_copy(self):
        game = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, game, ignore_errors=True)
        write(os.path.join(game, "REX.exe"), "exe")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "data"))
        gd = os.path.join(game, "data")
        data, _ = create_mod(gd, "Beta")
        mod = ModData(data)
        files = {f["rel"]: f for f in RF.listing(mod)}
        f = files["export_descr_unit.txt"]
        if not f["game"]:                               # New mod folder copied it: make it the game's only
            os.remove(f["path"])
            mod = ModData(data)
            f = {x["rel"]: x for x in RF.listing(mod)}["export_descr_unit.txt"]
        self.assertTrue(f["game"])
        before = digest(f["path"])
        lines = mod.load(f["path"]).texts() + ["; added by hand"]
        plan = Plan(mod, "raw_files", "raw_files", {})
        RF.plan_lines(plan, f["path"], lines)
        plan.apply()
        self.assertEqual(digest(f["path"]), before)     # the game's own data never written
        mine = os.path.join(mod.data, "export_descr_unit.txt")
        with open(mine, "rb") as fh:
            self.assertTrue(fh.read().rstrip().endswith(b"; added by hand"))

    def test_what_the_game_would_stumble_on_is_underlined(self):
        self.assertEqual(RF.check("a.txt", ["block", "{", "    x 1 ; } in a comment", "}"]), {})
        self.assertIn(2, RF.check("a.txt", ["block", "{", "    x 1"]))
        self.assertIn(1, RF.check("a.txt", ["}", "x"]))
        self.assertEqual(RF.check("data/text/names.txt", ["{KEY}text {", "x"]), {})     # {KEY} of a text table
        self.assertEqual(RF.check("descr_campaign_db.xml", ["<a>", "  <b v='1'/>", "</a>"]), {})
        self.assertEqual(list(RF.check("descr_campaign_db.xml", ["<a>", "  <b>", "</a>"])), [3])

    def test_plain_words_for_every_file(self):
        self.assertEqual(RF.about("export_descr_unit.txt")[1], "Unit editor")
        self.assertEqual(RF.about("export_descr_unit_enums.txt")[1], "Unit editor")
        self.assertIn("campaign", RF.about("world/maps/campaign/imperial_campaign/descr_strat.txt")[0])
        self.assertEqual(RF.about("world/maps/campaign/x/descr_harvests.txt"), ("a campaign's file", None))
        self.assertEqual(RF.about("whatever.cfg"), ("a file the game reads", None))
        self.assertEqual(RF.work_of("Unit editor > Voice"), "units")
        self.assertEqual(RF.work_of("Map, Faction editor"), "map")
        self.assertEqual(RF.work_of("Traits (Characters)"), "traits")
        self.assertIsNone(RF.work_of(None))
        for words, window in RF.ABOUT.values():         # every window named leads to a work of the main window
            self.assertTrue(window is None or RF.work_of(window), window)
        import re
        with open(os.path.join(os.path.dirname(RF.__file__), "gui.py"), encoding="utf-8") as fh:
            src = fh.read()                             # read as text: the test job has no tkinter
        titles = src[src.index("WORK_TITLES = {"):]
        keys = set(re.findall(r'"(\w+)":', titles[:titles.index("}")]))
        self.assertEqual(set(RF.WORKS.values()) - keys, set())
        self.assertIsNone(RF.comment_mark("a.xml"))
        self.assertEqual(RF.comment_mark("script/main.nut"), "//")


if __name__ == "__main__":
    unittest.main()
