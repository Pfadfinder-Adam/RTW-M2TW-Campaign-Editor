"""Who leads a Medieval II faction after its leader (succession.py): descr_sm_factions.txt's has_family_tree
yes / teutonic / no and can_have_princess, as the engine reads them (faction_db.cpp, faction.cpp promote_new_leader)."""

import hashlib
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from campaign_editor import succession as SU                   # noqa: E402
from campaign_editor.build import build                        # noqa: E402
from campaign_editor.edit import edit, read_faction            # noqa: E402
from campaign_editor.minimod import SM, make as make_minimod, write  # noqa: E402
from campaign_editor.moddata import ModData                    # noqa: E402
from campaign_editor.plan import Plan, backups, restore        # noqa: E402

# Medieval II's last two words of a block, as vanilla writes them (the game's own spacing and a comment kept)
M2_SM = SM.replace("secondary_colour\t\tred 4, green 5, blue 6\n",
                   "secondary_colour\t\tred 4, green 5, blue 6\n"
                   "can_have_princess\t\t\tyes\n"
                   "has_family_tree\t\t\t\t\tyes  ; the king's line\n", 1)


def tree_hash(root):
    out = {}
    for d, _, fs in os.walk(root):
        for n in fs:
            p = os.path.join(d, n)
            rel = os.path.relpath(p, root)
            if not rel.startswith("CampaignEditor_backups"):
                with open(p, "rb") as f:
                    out[rel] = hashlib.md5(f.read()).hexdigest()
    return out


class SuccessionTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.d = make_minimod(self.root)
        write(os.path.join(self.d, "descr_sm_factions.txt"), M2_SM)

    def tearDown(self):
        shutil.rmtree(self.root)

    def sm(self):
        with open(os.path.join(self.d, "descr_sm_factions.txt"), encoding="latin-1") as f:
            return f.read()

    def test_read_as_the_file_says(self):
        now = read_faction(ModData(self.root), "test", "alpha")
        self.assertEqual((now["succession"], now["princesses"]), ("yes", True))

    def test_election_takes_the_princesses_away_and_restores(self):
        before = tree_hash(self.root)
        plan = edit(ModData(self.root), "test", "alpha", {"succession": "teutonic"})
        self.assertTrue(any("princesses taken away" in w for _, w in plan.warnings), plan.warnings)
        plan.apply()
        text = self.sm()
        self.assertIn("has_family_tree\t\t\t\t\tteutonic  ; the king's line\n", text)   # spacing and comment kept
        self.assertIn("can_have_princess\t\t\tno\n", text)
        now = read_faction(ModData(self.root), "test", "alpha")
        self.assertEqual((now["succession"], now["princesses"]), ("teutonic", False))
        restore(ModData(self.root), backups(ModData(self.root))[0])
        self.assertEqual(tree_hash(self.root), before)

    def test_no_family_tree_warns_the_faction_never_dies(self):
        plan = edit(ModData(self.root), "test", "alpha", {"succession": "no", "princesses": True})
        self.assertTrue(any("never dies" in w for _, w in plan.warnings), plan.warnings)
        plan.apply()
        self.assertIn("has_family_tree\t\t\t\t\tno", self.sm())
        self.assertIn("can_have_princess\t\t\tyes", self.sm())                    # asked for, kept

    def test_princesses_alone_and_back(self):
        edit(ModData(self.root), "test", "alpha", {"princesses": False}).apply()
        self.assertIn("can_have_princess\t\t\tno", self.sm())
        edit(ModData(self.root), "test", "alpha", {"princesses": True}).apply()
        self.assertEqual(self.sm(), M2_SM)

    def test_unchanged_writes_nothing(self):
        plan = edit(ModData(self.root), "test", "alpha", {"succession": "yes", "princesses": True})
        self.assertNotIn(ModData(self.root).file("sm_factions"), plan.changed_files())

    def test_rome_has_no_such_setting(self):
        write(os.path.join(self.d, "descr_sm_factions.txt"), SM)
        mod = ModData(self.root)
        self.assertNotIn("succession", read_faction(mod, "test", "alpha"))
        with self.assertRaises(ValueError):
            SU.apply(Plan(mod, "alpha", "alpha"), "alpha", "teutonic")

    def test_new_faction_elects_while_its_template_stays(self):
        mod = ModData(self.root)
        build(mod, "test", "alpha", "beta", {"succession": "teutonic",
                                             "start": {"regions": ["B_R"], "leader": {"name": "Boris"}}}).apply()
        mod = ModData(self.root)
        self.assertEqual(SU.read(mod, "beta"), {"succession": "teutonic", "princesses": False})
        self.assertEqual(SU.read(mod, "alpha"), {"succession": "yes", "princesses": True})


if __name__ == "__main__":
    unittest.main()
