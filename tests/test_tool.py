"""End-to-end test on a tiny synthetic mod (no game files needed)."""

import codecs
import hashlib
import os
import shutil
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from faction_tool.build import build                     # noqa: E402
from faction_tool.moddata import ModData                 # noqa: E402
from faction_tool.plan import backups, restore           # noqa: E402
from faction_tool.strat import Strat                     # noqa: E402
from faction_tool.textio import TextFile                 # noqa: E402

SM = """faction\t\talpha
culture\t\teastern
primary_colour\t\tred 1, green 2, blue 3
secondary_colour\t\tred 4, green 5, blue 6
;;;;;;;;

faction\t\tslave
culture\t\tbarbarian
;;;;;;;;
"""

CHARACTER = """type\t\tnamed character
faction\t\talpha
dictionary\t2
strat_model\tgeneral

faction\t\tslave
dictionary\t2
strat_model\tgeneral
"""

NAMES = """faction: alpha
\tcharacters
\t\tAaron
\t\tBoris
\tsurnames
\t\tAlphid
\twomen
\t\tAnna

faction: slave
\tcharacters
\t\tRebel
\tsurnames
\t\tNobody
"""

EDU = """type\t\talpha general
dictionary\talpha_general
ownership\talpha

type\t\trebel spear
dictionary\trebel_spear
ownership\tslave
"""

EDB = "\t\trecruit \"alpha general\" 0 requires factions { alpha, }\n"

REGIONS = """A_R
\tAtown
\talpha
\tRebels
\t255 0 0
\tnone
\t5
\t1
B_R
\tBtown
\tslave
\tRebels
\t0 0 255
\tnone
\t5
\t1
"""

STRAT = """campaign\ttest
playable
\talpha
end
unlockable
end
nonplayable
\tslave
end

;#####>
faction\talpha, balanced smith
denari\t1000

settlement
{
\tlevel town
\tregion A_R
\tpopulation 1000
}

character\tAaron Alphid, named character, leader, age 40, , x 1, y 1
army
unit\t\talpha general\t\texp 1 armour 0 weapon_lvl 0
;#####<

;#####>
faction\tslave, balanced smith
denari\t1000

settlement
{
\tlevel town
\tregion B_R
\tpopulation 800
}

;;\tBtown
character,\tsub_faction alpha, Grog, general, age 30, , x 2, y 2
army
unit\t\trebel spear\t\texp 0 armour 0 weapon_lvl 0
;#####<

core_attitudes\talpha,\t600\t\tslave
core_attitudes\tslave,\t600\t\talpha
faction_relationships\talpha,\t600\t\tslave
"""


def write(path, text, utf16=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        if utf16:
            f.write(codecs.BOM_UTF16_LE + text.replace("\n", "\r\n").encode("utf-16-le"))
        else:
            f.write(text.replace("\n", "\r\n").encode("latin-1"))


def write_tga(path, w, h, pixels):
    """Uncompressed 24-bit, bottom-up; pixels[y][x] = (r, g, b)."""
    head = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 24, 0)
    body = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[y][x]
            body += bytes((b, g, r))
    with open(path, "wb") as f:
        f.write(head + body)


def tree_hash(root):
    out = {}
    for d, _, fs in os.walk(root):
        for n in fs:
            p = os.path.join(d, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = hashlib.md5(f.read()).hexdigest()
    return out


class ToolTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_sm_factions.txt"), SM)
        write(os.path.join(d, "descr_character.txt"), CHARACTER)
        write(os.path.join(d, "descr_names.txt"), NAMES)
        write(os.path.join(d, "export_descr_unit.txt"), EDU)
        write(os.path.join(d, "export_descr_buildings.txt"), EDB)
        write(os.path.join(d, "text", "expanded_bi.txt"),
              "{ALPHA}\t\tAlphan Kingdom\n{ALPHA_DESCR}\t\tAlphans ride\n{EMT_ALPHA_SPY}\t\tAlphan Spy\n", utf16=True)
        camp = os.path.join(d, "world", "maps", "campaign", "test")
        write(os.path.join(camp, "descr_strat.txt"), STRAT)
        write(os.path.join(camp, "descr_regions.txt"), REGIONS)
        write(os.path.join(camp, "descr_win_conditions.txt"), "alpha\nhold_regions A_R\ntake_regions 10\n")
        red, blue, black = (255, 0, 0), (0, 0, 255), (0, 0, 0)
        px = [[red, red, blue, blue],
              [red, black, blue, blue],
              [red, red, black, blue],
              [red, red, blue, blue]]
        write_tga(os.path.join(camp, "map_regions.tga"), 4, 4, px)
        write(os.path.join(camp, "map_alpha.tga"), "x")
        ui = os.path.join(d, "ui")
        write(os.path.join(ui, "units", "alpha", "#alpha_general.tga"), "card")
        write(os.path.join(ui, "unit_info", "alpha", "alpha_general_info.tga"), "info")
        write(os.path.join(ui, "unit_info", "alpha", "spy_info.tga"), "spy")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_round_trip_is_byte_exact(self):
        mod = ModData(self.root)
        for p in [mod.file("sm_factions"), mod.text_files()[0]]:
            with open(p, "rb") as f:
                self.assertEqual(f.read(), TextFile.load(p).dump())

    def test_clone_and_restore(self):
        before = tree_hash(self.root)
        mod = ModData(self.root)
        self.assertEqual(mod.city_tiles("test"), {"A_R": (1, 1), "B_R": (2, 2)})
        plan = build(mod, "test", "alpha", "beta", {
            "display_name": "Betan League", "short_name": "Beta", "adjective": "Betan",
            "start": {"regions": ["B_R"], "leader": {"name": "Boris Alphid", "age": 35}, "denari": 500}})
        # the only warning: the rebel garrison's units are not beta's own
        self.assertEqual(len(plan.warnings), 1, plan.report())
        self.assertIn("rebel spear", plan.warnings[0][1])
        plan.apply()

        mod = ModData(self.root)
        self.assertEqual([n for n, _ in mod.factions()], ["alpha", "beta", "slave"])
        s = Strat(mod.load(mod.campaign_file("test", "descr_strat.txt")))
        self.assertEqual(s.owners(), {"A_R": "alpha", "B_R": "beta"})
        beta = s.faction("beta")
        # one army per town: the rebel garrison folds into the leader's army
        self.assertEqual([c.name for c in beta.characters], ["Boris Alphid"])
        boris = beta.characters[0]
        self.assertEqual(boris.xy, (2, 2))
        units = [l.split("\t")[2] for l in s.lines[boris.start:boris.end] if l.startswith("unit")]
        self.assertEqual(units, ["alpha general", "rebel spear"])
        self.assertTrue(all("sub_faction" not in s.lines[c.start] for c in beta.characters))
        self.assertIn("beta", [n for _, n in s.playable["items"]])
        edu = open(mod.file("edu"), encoding="latin-1").read()
        self.assertIn("ownership\talpha, beta", edu)
        edb = open(mod.file("edb"), encoding="latin-1").read()
        self.assertIn("factions { alpha, beta, }", edb)
        self.assertEqual(mod.name_pool("beta")["characters"], ["Aaron", "Boris"])
        text = open(mod.text_files()[0], "rb").read().decode("utf-16")
        self.assertIn("{BETA}\t\tBetan League", text)
        self.assertIn("{EMT_BETA_SPY}\t\tBetan Spy", text)
        self.assertTrue(os.path.exists(os.path.join(mod.campaign_dir("test"), "map_beta.tga")))

        restore(mod, backups(mod)[0])
        after = tree_hash(self.root)
        after = {k: v for k, v in after.items() if not k.startswith("faction_tool_backups")}
        self.assertEqual(before, after)

    def test_unit_cards_fill_a_folder_left_from_an_earlier_attempt(self):
        # ui/units/beta exists already (an old manual attempt) but lacks alpha's cards
        write(os.path.join(self.root, "data", "ui", "units", "beta", "#old_unit.tga"), "old")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        ui = os.path.join(mod.data, "ui")
        for rel in (("units", "beta", "#alpha_general.tga"), ("unit_info", "beta", "alpha_general_info.tga"),
                    ("unit_info", "beta", "spy_info.tga"), ("units", "beta", "#old_unit.tga")):
            self.assertTrue(os.path.exists(os.path.join(ui, *rel)), rel)
        self.assertEqual(sum("#alpha_general.tga" in m for _, m in plan.notes), 1, plan.report())
        restore(mod, backups(mod)[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith("faction_tool_backups")}
        self.assertEqual(before, after)

    def test_heir_with_one_town_stands_next_to_it(self):
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {
            "start": {"regions": ["B_R"], "leader": {"name": "Boris"}, "heir": {"name": "Aaron", "age": 20}}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        chars = {c.name: c for c in s.faction("beta").characters}
        self.assertEqual(sorted(chars), ["Aaron", "Boris"])
        self.assertEqual(chars["Boris"].xy, (2, 2))
        # a free tile of B_R's own colour, not the city and not A_R's land
        x, y = chars["Aaron"].xy
        self.assertNotEqual((x, y), (2, 2))
        self.assertLessEqual(max(abs(x - 2), abs(y - 2)), 1)
        self.assertEqual(mod.region_map("test").get(x, y), (0, 0, 255))
        armies = [c.xy for fb in s.factions for c in fb.characters if "army" in s.lines[c.start:c.end]]
        self.assertEqual(len(armies), len(set(armies)))

    def test_heir_avoids_rivers(self):
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        black, river = (0, 0, 0), (0, 0, 255)
        feat = [[black] * 4 for _ in range(4)]
        feat[2][3] = river                      # (3, 2): the first free tile of B_R
        write_tga(os.path.join(camp, "map_features.tga"), 4, 4, feat)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {
            "start": {"regions": ["B_R"], "leader": {"name": "Boris"}, "heir": {"name": "Aaron"}}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        aaron = next(c for c in s.faction("beta").characters if c.name == "Aaron")
        self.assertNotEqual(aaron.xy, (3, 2))
        self.assertEqual(mod.region_map("test").get(*aaron.xy), (0, 0, 255))

    def test_bad_leader_name_is_refused(self):
        mod = ModData(self.root)
        with self.assertRaises(ValueError):
            build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Zed"}}})


if __name__ == "__main__":
    unittest.main()
