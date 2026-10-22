"""Authors and sources of a mod (sources.py): the list kept in the mod folder and its text file."""

import os
import shutil
import tempfile
import unittest

from campaign_editor import sources as SO


class SourcesTest(unittest.TestCase):
    def setUp(self):
        self.game = tempfile.mkdtemp()
        open(os.path.join(self.game, "RomeTW.exe"), "w").close()
        self.data = os.path.join(self.game, "MyMod", "data")
        os.makedirs(self.data)
        self.root = os.path.join(self.game, "MyMod")

    def tearDown(self):
        shutil.rmtree(self.game, ignore_errors=True)

    def test_the_list_lives_in_the_mod_folder_not_in_the_games_own(self):
        self.assertEqual(SO.folder(self.data), self.root)
        self.assertIsNone(SO.folder(os.path.join(self.game, "data")))

    def test_the_game_and_its_expansions_are_not_another_modders_work(self):
        self.assertTrue(SO.is_game_own(os.path.join(self.game, "data")))
        self.assertTrue(SO.is_game_own(os.path.join(self.game, "bi", "data")))
        self.assertFalse(SO.is_game_own(os.path.join(self.game, "EB", "data")))
        m2 = tempfile.mkdtemp()
        try:
            open(os.path.join(m2, "medieval2.exe"), "w").close()
            self.assertFalse(SO.is_game_own(os.path.join(m2, "mods", "SS", "data")))
            self.assertEqual(SO.folder(os.path.join(m2, "mods", "SS", "data")), os.path.join(m2, "mods", "SS"))
        finally:
            shutil.rmtree(m2, ignore_errors=True)

    def test_source_names(self):
        self.assertEqual(SO.source_name(os.path.join(self.game, "EB", "data")), "EB")
        self.assertEqual(SO.source_name(os.path.join(self.game, "packs", "Aquila Rubra.zip")), "Aquila Rubra")

    def test_a_source_noted_twice_keeps_one_entry_and_its_answers(self):
        items, i = SO.noted([], "EB", "units a, b")
        self.assertEqual(items[i]["asked"], "not_yet")
        items[i].update(author="EB Team", link="twcenter.net/eb", asked="yes")
        items, j = SO.noted(items, "eb", "battle model x")
        items, j = SO.noted(items, "EB", "units a, b")
        self.assertEqual((len(items), j), (1, 0))
        self.assertEqual(items[0]["what"], "units a, b; battle model x")
        self.assertEqual((items[0]["author"], items[0]["asked"]), ("EB Team", "yes"))

    def test_saved_list_reads_back_and_writes_the_text_players_see(self):
        items, _ = SO.noted([], "EB", "units a")
        items[0].update(author="EB Team", link="twcenter.net/eb", asked="yes")
        items, _ = SO.noted(items, "RS2", "battle model y")
        SO.save(self.root, items)
        self.assertEqual(SO.load(self.root), items)
        with open(os.path.join(self.root, SO.TEXT_NAME), encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("- EB - EB Team\n  twcenter.net/eb\n  Taken: units a\n  Used with the author's permission.",
                      txt.replace("\r", ""))
        self.assertIn("- RS2\n  Taken: battle model y", txt.replace("\r", ""))
        self.assertTrue(txt.startswith("Authors and sources - MyMod"))
        SO.save(self.root, [])
        self.assertFalse(os.path.exists(os.path.join(self.root, SO.TEXT_NAME)))
        self.assertEqual(SO.load(self.root), [])

    def test_a_broken_list_reads_as_none(self):
        with open(os.path.join(self.root, SO.LIST_NAME), "w") as fh:
            fh.write("{not json")
        self.assertEqual(SO.load(self.root), [])
        with open(os.path.join(self.root, SO.LIST_NAME), "w") as fh:
            fh.write('{"sources": [{"source": "X", "asked": "maybe"}]}')
        self.assertEqual(SO.load(self.root)[0]["asked"], "not_yet")


if __name__ == "__main__":
    unittest.main()
