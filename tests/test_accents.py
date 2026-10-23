"""Voice accents of factions (accents.py): Medieval II's descr_sounds_accents.txt and the sound banks speaking each
accent, as the engine reads them (SOUND_DB::parse_accent_type, the banks' `accent` blocks)."""

import hashlib
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from campaign_editor import accents as AC                    # noqa: E402
from campaign_editor.build import build                      # noqa: E402
from campaign_editor.edit import edit, read_faction          # noqa: E402
from campaign_editor.moddata import ModData                  # noqa: E402
from campaign_editor.plan import Plan, backups, restore      # noqa: E402
from campaign_editor.minimod import write, make as make_minimod  # noqa: E402

ACCENTS = "accent English\n    factions slave\n\naccent Arabic\n    factions alpha\n"
VOICE = ("BANK: unit_voice\n"
         "         accent English\n"
         "                  class Heavy\n"
         "                           vocal Unit_Select\n"
         "                                    event\n"
         "                                             folder data/sounds/voice\n"
         "                                                  English_Select.wav\n"
         "                                    end\n"
         "\n"
         "         accent Arabic\n"
         "                  class Heavy\n"
         "                           vocal Unit_Select\n"
         "                                    event\n"
         "                                             folder data/sounds/voice\n"
         "                                                  Arabic_Select.wav\n"
         "                                    end\n")
CONFIRM = "BANK: unit_confirm\n\taccent English, Arabic\n\t\tclass Heavy\n\t\t\tevent\n\t\t\t  a\n\t\t\tend\n"


def tree_hash(root):
    out = {}
    for d, _, fs in os.walk(root):
        for n in fs:
            p = os.path.join(d, n)
            rel = os.path.relpath(p, root)
            if rel.startswith("CampaignEditor_backups"):
                continue
            with open(p, "rb") as f:
                out[rel] = hashlib.md5(f.read()).hexdigest()
    return out


class AccentsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.d = make_minimod(self.root)
        write(os.path.join(self.d, "descr_sounds_accents.txt"), ACCENTS)
        write(os.path.join(self.d, "export_descr_sounds_units_voice.txt"), VOICE)
        write(os.path.join(self.d, "descr_sounds_units_confirm.txt"), CONFIRM)

    def tearDown(self):
        shutil.rmtree(self.root)

    def rd(self, name):
        with open(os.path.join(self.d, name), encoding="latin-1") as f:
            return f.read()

    def test_reads_accents_as_the_engine(self):
        mod = ModData(self.root)
        self.assertEqual(AC.names(mod), ["English", "Arabic"])
        self.assertEqual(AC.accent_of(mod, "ALPHA"), "Arabic")          # faction names without letter case
        self.assertEqual(AC.voiced(mod)["Arabic"], ["descr_sounds_units_confirm.txt",
                                                     "export_descr_sounds_units_voice.txt"])
        self.assertEqual(read_faction(mod, "test", "alpha")["accent"], "Arabic")
        self.assertEqual(AC.problems(mod), [])

    def test_rome_speaks_by_culture(self):
        os.remove(os.path.join(self.d, "descr_sounds_accents.txt"))
        mod = ModData(self.root)
        self.assertFalse(AC.has_accents(mod))
        self.assertEqual(AC.voice_of(mod, "alpha"), ("culture", "eastern"))
        self.assertNotIn("accent", read_faction(mod, "test", "alpha"))
        plan = Plan(mod, "accent", "x")
        with self.assertRaises(ValueError):
            AC.set_accent(plan, "alpha", "English")

    def test_edit_faction_moves_its_accent_and_restores(self):
        before = tree_hash(self.root)
        mod = ModData(self.root)
        plan = edit(mod, "test", "alpha", {"accent": "English"})
        plan.apply()
        text = self.rd("descr_sounds_accents.txt")
        self.assertIn("factions slave, alpha", text)                    # the file's commas
        self.assertNotIn("factions alpha", text)                        # its old line, left empty, went
        self.assertEqual(AC.accent_of(ModData(self.root), "alpha"), "English")
        restore(ModData(self.root), backups(ModData(self.root))[0])
        self.assertEqual(tree_hash(self.root), before)

    def test_unknown_accent_refused(self):
        plan = Plan(ModData(self.root), "accent", "x")
        with self.assertRaises(ValueError):
            AC.set_accent(plan, "alpha", "english")                     # the banks compare letter case

    def test_new_accent_copies_the_voices(self):
        mod = ModData(self.root)
        plan = Plan(mod, "accent", "Venetian")
        AC.new_accent(plan, "Venetian", "Arabic", ["alpha"])
        plan.apply()
        acc = self.rd("descr_sounds_accents.txt")
        self.assertTrue(acc.rstrip().endswith("accent Venetian\n    factions alpha"), acc)
        voice = self.rd("export_descr_sounds_units_voice.txt")
        self.assertEqual(voice.count("Arabic_Select.wav"), 2)          # the block copied, same sounds
        self.assertIn("         accent Venetian\n                  class Heavy", voice)
        self.assertIn("accent English, Arabic, Venetian", self.rd("descr_sounds_units_confirm.txt"))
        mod = ModData(self.root)
        self.assertEqual(AC.accent_of(mod, "alpha"), "Venetian")
        self.assertEqual(AC.problems(mod), [])
        # the opposite: removed, its factions to another, the banks as they were
        plan = Plan(mod, "accent", "Venetian")
        AC.remove_accent(plan, "Venetian", "English")
        plan.apply()
        self.assertEqual(self.rd("export_descr_sounds_units_voice.txt"), VOICE)
        self.assertEqual(self.rd("descr_sounds_units_confirm.txt"), CONFIRM)
        self.assertNotIn("Venetian", self.rd("descr_sounds_accents.txt"))
        self.assertEqual(AC.accent_of(ModData(self.root), "alpha"), "English")

    def test_new_accent_name_checked(self):
        plan = Plan(ModData(self.root), "accent", "x")
        for bad in ("two words", "Arabic", "arabic", "a,b", ""):
            with self.assertRaises(ValueError):
                AC.new_accent(plan, bad, "English")

    def test_new_faction_keeps_or_takes_an_accent(self):
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        self.assertEqual(AC.accent_of(ModData(self.root), "beta"), "Arabic")      # beside its template
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "gamma", {"accent": "English",
                                                     "start": {"regions": ["A_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(AC.accent_of(mod, "gamma"), "English")
        self.assertEqual(AC.accent_of(mod, "alpha"), "Arabic")                    # the template's stays

    def test_problems_as_the_engine_reports_them(self):
        write(os.path.join(self.d, "descr_sounds_accents.txt"),
              "accent English\n    factions slave, nobody\n\naccent Mute\n    factions alpha\n")
        write(os.path.join(self.d, "descr_sounds_units_confirm.txt"), CONFIRM.replace("Arabic", "arabic"))
        msgs = [m for m, fault in AC.problems(ModData(self.root)) if fault]
        self.assertTrue(any("nobody is no faction" in m for m in msgs), msgs)
        self.assertTrue(any("no sound file speaks the accent Mute" in m for m in msgs), msgs)
        self.assertTrue(any("accent arabic is not in" in m for m in msgs), msgs)
        self.assertTrue(any("accent Arabic is not in" in m for m in msgs), msgs)   # the voice file's
        write(os.path.join(self.d, "descr_sounds_accents.txt"), "accent English\n    factions slave\n")
        msgs = [m for m, fault in AC.problems(ModData(self.root)) if fault]
        self.assertTrue(any("names no accent for alpha" in m for m in msgs), msgs)

    def test_rename_takes_the_accent_along(self):
        from campaign_editor.factionrename import plan_rename
        mod = ModData(self.root)
        plan = Plan(mod, "rename", "omega")
        plan_rename(plan, "test", "alpha", "omega")
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(AC.accent_of(mod, "omega"), "Arabic")
        self.assertEqual([m for m, fault in AC.problems(mod) if fault], [])

    def test_brought_faction_speaks_its_own_accent(self):
        """Bring a faction from another mod: it speaks the accent it spoke there when this mod has one of that name,
        else the frame's stays and the plan says so."""
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other)
        make_minimod(other)
        write(os.path.join(other, "data", "descr_sounds_accents.txt"), "accent English\n    factions alpha, slave\n")
        mod = ModData(self.root)
        plan = Plan(mod, "alpha", "beta")
        AC.set_accent(plan, "beta", "Arabic")                    # the frame's line, as clone.medieval_lists leaves it
        AC.take_after(plan, ModData(other), "alpha", "beta")
        self.assertEqual(AC.accent_of(plan, "beta"), "English")
        write(os.path.join(other, "data", "descr_sounds_accents.txt"), "accent Gaulish\n    factions alpha, slave\n")
        plan = Plan(mod, "alpha", "beta")
        AC.set_accent(plan, "beta", "Arabic")
        AC.take_after(plan, ModData(other), "alpha", "beta")
        self.assertEqual(AC.accent_of(plan, "beta"), "Arabic")
        self.assertTrue(any("no such accent" in w for _, w in plan.warnings), plan.warnings)

    def test_unit_accent_line_offers_the_mods_accents(self):
        from campaign_editor import lineinfo
        info = lineinfo.about("unit", "accent  Arabic", True, (), AC.names(ModData(self.root)))
        self.assertEqual([w for w, _ in info["words"]], ["English", "Arabic"])


if __name__ == "__main__":
    unittest.main()
