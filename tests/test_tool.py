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
from faction_tool.scan import scan                       # noqa: E402
from faction_tool.newmod import create_mod, slim         # noqa: E402
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
        write(os.path.join(d, "text", "test_regions_and_settlement_names.txt"), "{Alpha}\t\tAlpha region\n", utf16=True)
        write(os.path.join(d, "text", "expanded_bi.txt"),
              "{ALPHA}\t\tAlphan Kingdom\n{ALPHA_DESCR}\t\tAlphans ride\n{EMT_ALPHA_SPY}\t\tAlphan Spy\n"
              "{TEST_ALPHA_DESCR}\t\tThe long Alphan story\n", utf16=True)
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
        # the rebel garrison leaves, so no foreign units are left behind
        self.assertEqual(plan.warnings, [], plan.report())
        plan.apply()

        mod = ModData(self.root)
        self.assertEqual([n for n, _ in mod.factions()], ["alpha", "beta", "slave"])
        s = Strat(mod.load(mod.campaign_file("test", "descr_strat.txt")))
        self.assertEqual(s.owners(), {"A_R": "alpha", "B_R": "beta"})
        beta = s.faction("beta")
        # one army per town: the old garrison leaves, the leader holds the town
        self.assertEqual([c.name for c in beta.characters], ["Boris Alphid"])
        boris = beta.characters[0]
        self.assertEqual(boris.xy, (2, 2))
        units = [l.split("\t")[2] for l in s.lines[boris.start:boris.end] if l.startswith("unit")]
        self.assertEqual(units, ["alpha general"])
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

    def test_kept_garrison_folds_into_the_leader(self):
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {
            "start": {"regions": ["B_R"], "leader": {"name": "Boris"}, "garrison": "keep"}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        chars = s.faction("beta").characters
        self.assertEqual([c.name for c in chars], ["Boris"])
        units = [l.split("\t")[2] for l in s.lines[chars[0].start:chars[0].end] if l.startswith("unit")]
        self.assertEqual(units, ["alpha general", "rebel spear"])
        self.assertTrue(any("rebel spear" in m for _, m in plan.warnings))

    def test_scan_sorts_mentions(self):
        write(os.path.join(self.root, "script", "war.nut"), "local f = \"alpha\";\nlocal alphabet = 1;\n")
        write(os.path.join(self.root, "data", "descr_model_strat.txt"),
              "type\tgeneral\ntexture\talpha, data/models_strat/textures/alpha_general.tga\n")
        write(os.path.join(self.root, "data", "models_strat", "textures", "ALPHA_GENERAL.tga"), "x")
        write(os.path.join(self.root, "data", "descr_model_battle.txt"),
              "type\tspear\ntexture\talpha, data/models_unit/textures/gone.tga\n")
        rep = scan(ModData(self.root), "alpha", "test")
        report = rep.report()
        self.assertEqual(list(rep.hits["script/war.nut"]), [(1, 'local f = "alpha";')])  # not 'alphabet'
        self.assertIn("NOT HANDLED - mentions of 'alpha' the tool does not copy (1 file(s))", report)
        self.assertIn("script/war.nut", report.split("HANDLED - files")[0])
        # a missing texture is found, a case-different one is not reported
        self.assertEqual([m[2] for m in rep.missing], ["data/models_unit/textures/gone.tga"])

    def test_lookup_keys_and_nested_mods(self):
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "lookup_campaign_descriptions.txt"), "TEST_ALPHA_TITLE\nTEST_ALPHA_DESCR\nOTHER_KEY\n")
        # a mod folder inside the scanned one is left out; UTF-8 text reads as UTF-8
        write(os.path.join(self.root, "somemod", "data", "descr_sm_factions.txt"), "faction alpha\n")
        with open(os.path.join(self.root, "notes.txt"), "wb") as fh:
            fh.write("alpha: Déjà vu\n".encode("utf-8"))
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        self.assertEqual(plan.files[mod.file("lookup_descr")].texts()[:5],
                         ["TEST_ALPHA_TITLE", "TEST_BETA_TITLE", "TEST_ALPHA_DESCR", "TEST_BETA_DESCR", "OTHER_KEY"])
        rep = scan(mod, "alpha", "test")
        self.assertEqual(rep.other_mods, ["somemod"])
        self.assertFalse(any(r.startswith("somemod/") for r in rep.hits))
        self.assertEqual(rep.hits["notes.txt"], [(1, "alpha: Déjà vu")])

    def test_scan_ignore_list(self):
        write(os.path.join(self.root, "junk", "a.txt"), "alpha\n")
        write(os.path.join(self.root, "data", "deep", "old_stuff", "b.txt"), "alpha\n")
        write(os.path.join(self.root, "data", "c.bak.txt"), "alpha\n")
        write(os.path.join(self.root, "data", "keep.txt"), "alpha\n")
        write(os.path.join(self.root, "faction_tool_ignore.txt"), "# comment\njunk/\nold_stuff/\n*.bak.txt\n")
        rep = scan(ModData(self.root), "alpha", "test")
        self.assertIn("data/keep.txt", rep.hits)
        for gone in ("junk/a.txt", "data/deep/old_stuff/b.txt", "data/c.bak.txt"):
            self.assertNotIn(gone, rep.hits)
        self.assertEqual(sorted(rep.user_dirs), ["data/deep/old_stuff/", "junk/"])
        self.assertIn("left out by faction_tool_ignore.txt: 2 folder(s)", rep.report())

    def _game(self):
        """A game folder with REX.exe, its own data, and self.root as the mod HLR."""
        game = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, game)
        write(os.path.join(game, "REX.exe"), "exe")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "data"))
        hlr = os.path.join(game, "HLR")
        shutil.copytree(self.root, hlr)
        write(os.path.join(hlr, "Start_mod.bat"), "cd ..\\.\nstart REX.exe -nm -show_err -mod:HLR -multirun\n")
        write(os.path.join(hlr, "data", "sounds", "HLR.idx"), "sounds")
        return game, hlr

    def test_new_mod_on_a_mod_leaves_the_base_untouched(self):
        game, hlr = self._game()
        before = tree_hash(hlr)
        data, st = create_mod(os.path.join(hlr, "data"), "HLR_Beta")
        target = os.path.join(game, "HLR_Beta")
        self.assertEqual(data, os.path.join(target, "data"))
        self.assertEqual(st["base"], "HLR")
        # text is copied, the rest linked; files named after the base also get the new name
        edu = os.path.join("data", "export_descr_unit.txt")
        self.assertFalse(os.path.samefile(os.path.join(hlr, edu), os.path.join(target, edu)))
        card = os.path.join("data", "ui", "units", "alpha", "#alpha_general.tga")
        self.assertTrue(os.path.samefile(os.path.join(hlr, card), os.path.join(target, card)))
        self.assertTrue(os.path.exists(os.path.join(target, "data", "sounds", "HLR_Beta.idx")))
        with open(os.path.join(target, "Start_HLR_Beta.bat"), "rb") as f:
            self.assertIn(b"-mod:HLR_Beta -multirun", f.read())
        self.assertFalse(os.path.exists(os.path.join(target, "Start_mod.bat")))
        # a faction created in the new mod, then restored, never reaches HLR
        mod = ModData(data)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        self.assertIn("beta", [n for n, _ in ModData(data).factions()])
        self.assertEqual(before, tree_hash(hlr))
        restore(mod, backups(mod)[0])
        self.assertEqual(before, tree_hash(hlr))
        with self.assertRaises(ValueError):
            create_mod(os.path.join(hlr, "data"), "HLR_Beta")        # exists already

    def test_new_mod_on_the_game_slims_to_the_changes(self):
        game, _ = self._game()
        data, st = create_mod(os.path.join(game, "data"), "Beta")
        self.assertEqual(st["base"], "(game)")
        with open(os.path.join(game, "Beta", "Start_Beta.bat"), "rb") as f:
            self.assertIn(b"REX.exe -nm -show_err -mod:Beta", f.read())
        plan = build(ModData(data), "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        removed = slim(data)
        left = sorted(os.path.relpath(os.path.join(d, n), data).replace(os.sep, "/")
                      for d, _, fs in os.walk(data) for n in fs)
        self.assertGreater(removed, 0)
        self.assertIn("descr_sm_factions.txt", left)
        self.assertIn("ui/units/beta/#alpha_general.tga", left)
        self.assertNotIn("ui/units/alpha/#alpha_general.tga", left)     # unchanged: the game has it

    def test_garrisons_by_hand(self):
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        # a third, empty rebel town C_R (green) to the right of the map
        red, blue, green, black = (255, 0, 0), (0, 0, 255), (0, 255, 0), (0, 0, 0)
        px = [[red, red, blue, blue, green, green],
              [red, black, blue, blue, green, black],
              [red, red, black, blue, green, green],
              [red, red, blue, blue, green, green]]
        write_tga(os.path.join(camp, "map_regions.tga"), 6, 4, px)
        write(os.path.join(camp, "descr_regions.txt"),
              REGIONS + "C_R\n\tCtown\n\tslave\n\tRebels\n\t0 255 0\n\tnone\n\t5\n\t1\n")
        write(os.path.join(camp, "descr_strat.txt"), STRAT.replace(
            ";;\tBtown", "settlement\n{\n\tlevel village\n\tregion C_R\n\tpopulation 400\n}\n\n;;\tBtown"))
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {
            "regions": ["B_R", "C_R"], "leader": {"name": "Boris"},
            "garrisons": {"B_R": ["alpha general", "rebel spear"], "C_R": ["alpha general"]}}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        chars = {c.name: c for c in s.faction("beta").characters}
        self.assertEqual(sorted(chars), ["Aaron", "Boris"])     # Grog left; Aaron captains C_R
        def units(c):
            return [l.split("\t")[2] for l in s.lines[c.start:c.end] if l.startswith("unit")]
        self.assertEqual(units(chars["Boris"]), ["alpha general", "alpha general", "rebel spear"])
        self.assertEqual(chars["Aaron"].xy, (5, 1))
        self.assertEqual(chars["Aaron"].kind, "general")
        self.assertEqual(units(chars["Aaron"]), ["alpha general"])

    def test_buildings_by_hand(self):
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"), """building core_building
{
    levels hut hall
    {
        hut requires factions { alpha, }
        {
            construction 1
            cost 100
            settlement_min village
            upgrades
            {
                hall
            }
        }
        hall requires factions { roman, }
        {
            capability
            {
                recruit "alpha general" 0 requires factions { alpha, }
            }
            construction 2
            cost 900
            settlement_min city
            upgrades
            {
            }
        }
    }
    plugins
    {
    }
}
""")
        mod = ModData(self.root)
        from faction_tool.buildings import read_buildings, settlement_info
        bs = read_buildings(mod.load(mod.file("edb")))
        self.assertEqual([(l.name, l.settlement_min, l.cost) for l in bs[0].levels],
                         [("hut", "village", 100), ("hall", "city", 900)])
        plan = build(mod, "test", "alpha", "beta", {"start": {
            "regions": ["B_R"], "leader": {"name": "Boris"}, "buildings": {"B_R": [["core_building", "hall"]]}}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        st = s.faction("beta").settlements[0]
        self.assertEqual(settlement_info(s.lines[st.start:st.end]), ("town", [("core_building", "hall")]))
        warnings = " ".join(m for _, m in plan.warnings)
        self.assertIn("hall is not for alpha's faction list", warnings)
        self.assertIn("hall needs a city, the settlement is a town", warnings)
        with self.assertRaises(ValueError):
            build(ModData(self.root), "test", "alpha", "beta", {"start": {
                "regions": ["B_R"], "leader": {"name": "Boris"}, "buildings": {"B_R": [["core_building", "tower"]]}}})

    def test_edit_an_existing_faction(self):
        from faction_tool.edit import edit, read_faction
        before = tree_hash(self.root)
        mod = ModData(self.root)
        now = read_faction(mod, "test", "alpha")
        self.assertEqual((now["display_name"], now["adjective"], now["ai"], now["denari"], now["playable"],
                          now["primary_colour"], now["regions"]),
                         ("Alphan Kingdom", "Alphan", "balanced smith", 1000, True, (1, 2, 3), ["A_R"]))
        plan = edit(mod, "test", "alpha", {
            "display_name": "Alphan Empire", "adjective": "Alphic", "long_description": "Rewritten",
            "primary_colour": (9, 8, 7), "ai": "fortified mao", "denari": 4000, "playable": False,
            "garrisons": {"A_R": ["rebel spear"]}})
        plan.apply()
        mod = ModData(self.root)
        now = read_faction(mod, "test", "alpha")
        self.assertEqual((now["display_name"], now["adjective"], now["ai"], now["denari"], now["playable"],
                          now["primary_colour"], now["long_description"]),
                         ("Alphan Empire", "Alphic", "fortified mao", 4000, False, (9, 8, 7), "Rewritten"))
        s = Strat(mod.load(mod.campaign_file("test", "descr_strat.txt")))
        aaron = s.faction("alpha").characters[0]
        self.assertEqual([l.split("\t")[2] for l in s.lines[aaron.start:aaron.end] if l.startswith("unit")],
                         ["alpha general", "rebel spear"])          # the bodyguard stays
        self.assertIn("alpha", [n for _, n in s.nonplayable["items"]])
        restore(mod, backups(mod)[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith("faction_tool_backups")}
        self.assertEqual(before, after)

    def _three_towns(self):
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        red, blue, green, black = (255, 0, 0), (0, 0, 255), (0, 255, 0), (0, 0, 0)
        px = [[red, red, blue, blue, green, green],
              [red, black, blue, blue, green, black],
              [red, red, black, blue, green, green],
              [red, red, blue, blue, green, green]]
        write_tga(os.path.join(camp, "map_regions.tga"), 6, 4, px)
        write(os.path.join(camp, "descr_regions.txt"),
              REGIONS + "C_R\n\tCtown\n\tslave\n\tRebels\n\t0 255 0\n\tnone\n\t5\n\t1\n")
        write(os.path.join(camp, "descr_strat.txt"), STRAT.replace(
            ";;\tBtown", "settlement\n{\n\tlevel village\n\tregion C_R\n\tpopulation 400\n}\n\n;;\tBtown"))

    def test_edit_takes_and_gives_towns(self):
        from faction_tool.edit import edit, read_faction
        self._three_towns()
        before = tree_hash(self.root)
        mod = ModData(self.root)
        plan = edit(mod, "test", "alpha", {"take": ["B_R", "C_R"], "give": {"A_R": "slave"}, "capital": "C_R",
                                           "leader": {"name": "Boris Alphid", "age": 50}})
        plan.apply()
        mod = ModData(self.root)
        now = read_faction(mod, "test", "alpha")
        self.assertEqual(now["regions"], ["C_R", "B_R"])                 # the capital first
        self.assertEqual(now["leader"], {"name": "Boris Alphid", "age": 50})
        s = Strat(mod.load(mod.campaign_file("test", "descr_strat.txt")))
        self.assertEqual(s.owners(), {"A_R": "slave", "B_R": "alpha", "C_R": "alpha"})
        self.assertEqual([c.name for c in s.faction("slave").characters], [])     # Grog's rebels left
        boris = s.faction("alpha").characters[0]
        self.assertIn(boris.xy, [(2, 2), (5, 1)])                        # moved into one of its new towns
        restore(mod, backups(mod)[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith("faction_tool_backups")}
        self.assertEqual(before, after)
        with self.assertRaises(ValueError):                               # a name with no string
            edit(ModData(self.root), "test", "alpha", {"leader": {"name": "Zed"}})

    def test_long_texts_are_copied_whole(self):
        # a value runs over several lines until the next {KEY}; the copy must not split it
        body = ("{hut_alpha}\t\tAlphan Hut\n"
                "{hut_alpha_desc}\t\tFirst line of the Alphans.\\n\\n\n"
                "Second paragraph.\n"
                "Third paragraph.\n\n"
                "{hut_other}\t\tSomeone else\n")
        write(os.path.join(self.root, "data", "text", "export_buildings.txt"), body, utf16=True)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"display_name": "Betan League", "adjective": "Betan",
                                                    "start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        path = [p for p in mod.text_files() if p.endswith("export_buildings.txt")][0]
        text = "\n".join(plan.files[path].texts())
        self.assertIn("{hut_alpha_desc}\t\tFirst line of the Alphans.\\n\\n\nSecond paragraph.\nThird paragraph.\n"
                      "{hut_beta_desc}", text)                              # the template's text is whole
        self.assertIn("{hut_beta_desc}\t\tFirst line of the Betans.\\n\\n\nSecond paragraph.\nThird paragraph.",
                      text)
        # and editing replaces the whole value, not just its first line
        from faction_tool.edit import edit, read_faction
        plan.apply()
        mod = ModData(self.root)
        write(os.path.join(self.root, "data", "text", "campaign_descriptions.txt"),
              "{TEST_ALPHA_DESCR}\t\tOne.\\n\nTwo.\n{TEST_ALPHA_TITLE}\t\tA\n", utf16=True)
        eb = os.path.join(self.root, "data", "text", "expanded_bi.txt")
        with open(eb, "rb") as fh:
            kept = fh.read().decode("utf-16").replace("{TEST_ALPHA_DESCR}\t\tThe long Alphan story\r\n", "")
        write(eb, kept.replace("\r\n", "\n"), utf16=True)
        mod = ModData(self.root)
        self.assertEqual(read_faction(mod, "test", "alpha")["long_description"], "One.\n Two.")
        p2 = edit(mod, "test", "alpha", {"long_description": "Fresh"})
        cd = [p for p in mod.text_files() if p.endswith("campaign_descriptions.txt")][0]
        self.assertEqual(p2.files[cd].texts()[:2], ["{TEST_ALPHA_DESCR}\t\tFresh", "{TEST_ALPHA_TITLE}\t\tA"])

    def test_edit_moves_characters(self):
        from faction_tool.edit import edit
        mod = ModData(self.root)
        # Aaron (alpha's army) from his town A_R (1, 1) to the land tile (0, 0)
        self.assertIsNone(mod.tile_problem("test", (0, 0), "named character", True))
        self.assertEqual(mod.tile_problem("test", (2, 2), "named character", True, {(2, 2)}),
                         "another army stands there (a town holds one army)")
        self.assertEqual(mod.tile_problem("test", (0, 0), "admiral", True), "a fleet needs sea")
        plan = edit(mod, "test", "alpha", {"moves": [{"name": "Aaron Alphid", "from": (1, 1), "to": (0, 0)}]})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        self.assertEqual(s.faction("alpha").characters[0].xy, (0, 0))
        with self.assertRaises(ValueError):             # Grog's army holds Btown
            edit(ModData(self.root), "test", "alpha",
                 {"moves": [{"name": "Aaron Alphid", "from": (1, 1), "to": (2, 2)}]})

    def test_armies_agents_fleets_placed_by_hand(self):
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        red, blue, black, sea = (255, 0, 0), (0, 0, 255), (0, 0, 0), (41, 140, 233)
        px = [[red, red, blue, sea],
              [red, black, blue, blue],
              [red, red, black, blue],
              [red, red, blue, blue]]
        write_tga(os.path.join(camp, "map_regions.tga"), 4, 4, px)
        chars = [{"kind": "army", "name": "Aaron", "age": 33, "units": ["alpha general"], "xy": (3, 1)},
                 {"kind": "spy", "name": "Boris Alphid", "xy": (2, 2)},          # agents may stand in a town
                 {"kind": "fleet", "name": "Aaron", "units": ["alpha general"], "xy": (3, 0)}]
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {
            "regions": ["B_R"], "leader": {"name": "Boris"}, "characters": chars}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        got = [(c.name, c.kind, c.xy) for c in s.faction("beta").characters]
        self.assertIn(("Aaron", "general", (3, 1)), got)
        self.assertIn(("Boris Alphid", "spy", (2, 2)), got)
        self.assertIn(("Aaron", "admiral", (3, 0)), got)
        bad = [dict(chars[0], name="Zed"), dict(chars[2], xy=(3, 2)), dict(chars[0], xy=(2, 2))]
        for c in bad:                                   # unknown name, fleet on land, army into a held town
            with self.assertRaises(ValueError):
                build(ModData(self.root), "test", "alpha", "beta", {"start": {
                    "regions": ["B_R"], "leader": {"name": "Boris"}, "characters": [c]}})
        from faction_tool.edit import edit
        path = mod.campaign_file("test", "descr_strat.txt")
        with open(path) as fh:
            text = fh.read()
        tree = "character_record\t\tAnna, \tfemale, age 30, alive, never_a_leader\n" \
               "relative \tAaron Alphid, \tAnna, \tend\n"
        with open(path, "w") as fh:
            fh.write(text.replace("weapon_lvl 0\n;#####<", "weapon_lvl 0\n\n" + tree + ";#####<", 1))
        p2 = edit(ModData(self.root), "test", "alpha", {"characters": [chars[1]]})
        s = Strat(p2.files[path])
        self.assertIn(("Boris Alphid", "spy", (2, 2)), [(c.name, c.kind, c.xy) for c in s.faction("alpha").characters])
        # new characters go before the family tree: a character after it crashes the game
        fb = s.faction("alpha")
        lines = [l.split(None, 1)[0] for l in s.lines[fb.start:fb.end] if l.strip()]
        self.assertLess(max(i for i, w in enumerate(lines) if w == "character"), lines.index("character_record"))
        # the same for a captain made for a taken town's garrison
        p3 = edit(ModData(self.root), "test", "alpha", {"take": ["B_R"], "garrisons": {"B_R": ["alpha general"]}})
        s = Strat(p3.files[path])
        self.assertIn("captain", "\n".join(m for _, m in p3.notes))
        fb = s.faction("alpha")
        lines = [l.split(None, 1)[0] for l in s.lines[fb.start:fb.end] if l.strip()]
        self.assertLess(max(i for i, w in enumerate(lines) if w == "character"), lines.index("character_record"))

    def test_existing_armies_changed_and_removed(self):
        from faction_tool.edit import edit
        mod = ModData(self.root)
        # Aaron (named) keeps his bodyguard; units after it are replaced
        plan = edit(mod, "test", "alpha", {"army_units": [{"name": "Aaron Alphid", "from": (1, 1),
                                                            "units": ["rebel spear", "rebel spear"]}]})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        c = s.faction("alpha").characters[0]
        units = [l.split("\t")[2] for l in s.lines[c.start:c.end] if l.startswith("unit")]
        self.assertEqual(units, ["alpha general", "rebel spear", "rebel spear"])
        with self.assertRaises(ValueError):             # family members are never removed
            edit(ModData(self.root), "test", "alpha", {"remove": [{"name": "Aaron Alphid", "from": (1, 1)}]})
        # taking a town whose rebels leave warns that it starts empty
        plan = edit(ModData(self.root), "test", "alpha", {"take": ["B_R"]})
        self.assertTrue(any("no army in B_R" in m for _, m in plan.warnings))

    def test_region_without_settlement_is_a_rebel_village(self):
        # the game makes a region descr_strat leaves out a rebel village; taking it writes that village
        from faction_tool.edit import edit
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        red, blue, green, black = (255, 0, 0), (0, 0, 255), (0, 255, 0), (0, 0, 0)
        px = [[red, red, blue, blue, green, green],
              [red, black, blue, blue, green, black],
              [red, red, black, blue, green, green],
              [red, red, blue, blue, green, green]]
        write_tga(os.path.join(camp, "map_regions.tga"), 6, 4, px)
        write(os.path.join(camp, "descr_regions.txt"),
              REGIONS + "C_R\n\tCtown\n\tslave\n\tRebels\n\t0 255 0\n\tnone\n\t5\n\t1\n")
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        plan = edit(mod, "test", "alpha", {"take": ["C_R"]})
        st = Strat(plan.files[path]).settlement_of("C_R")
        self.assertEqual(st.owner, "alpha")
        self.assertIn("\tlevel village", Strat(plan.files[path]).lines[st.start:st.end])
        plan = build(ModData(self.root), "test", "alpha", "beta", {"start": {"regions": ["C_R"],
                                                                            "leader": {"name": "Boris"}}})
        self.assertEqual(Strat(plan.files[path]).settlement_of("C_R").owner, "beta")

    def test_town_moved_on_the_map(self):
        from faction_tool.edit import edit
        from faction_tool.tga import read_tga
        rwm = os.path.join(self.root, "data", "world", "maps", "base", "map.rwm")
        write(rwm, "compiled map")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        with self.assertRaises(ValueError):             # not A_R's land
            edit(mod, "test", "alpha", {"places": [{"what": "city", "region": "A_R", "to": (2, 0)}]})
        plan = edit(ModData(self.root), "test", "alpha", {"places": [{"what": "city", "region": "A_R", "to": (0, 2)}]})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        self.assertEqual(s.faction("alpha").characters[0].xy, (0, 2))       # Aaron moves with his town
        bdir = plan.apply()
        img = read_tga(mod.campaign_file("test", "map_regions.tga"))
        self.assertEqual((img.get(1, 1), img.get(0, 2)), ((255, 0, 0), (0, 0, 0)))
        self.assertFalse(os.path.exists(rwm))             # the game rebuilds it
        self.assertEqual(ModData(self.root).city_tiles("test")["A_R"], (0, 2))
        restore(ModData(self.root), bdir)
        after = {k: v for k, v in tree_hash(self.root).items() if "faction_tool_backups" not in k}
        self.assertEqual(after, before)

    def test_ships_owned_by_culture(self):
        # vanilla gives ships to cultures ("ownership roman, greek"), not factions
        with open(os.path.join(self.root, "data", "export_descr_unit.txt"), "a") as fh:
            fh.write("\ntype\t\teastern bireme\ndictionary\teastern_bireme\ncategory\tship\nownership\teastern\n")
        from faction_tool.units import faction_units
        mod = ModData(self.root)
        self.assertEqual([u.type for u in faction_units(mod, "alpha", ships=True)], ["eastern bireme"])
        self.assertNotIn("eastern bireme", [u.type for u in faction_units(mod, "alpha")])

    def test_campaign_screen_key_under_a_front_end_name(self):
        # the template's description sits under a front end name (like GAUL for gauls)
        from faction_tool import clone
        clone.FE_NAMES["alpha"] = "ALPHALAND"
        self.addCleanup(clone.FE_NAMES.pop, "alpha")
        write(os.path.join(self.root, "data", "text", "campaign_descriptions.txt"),
              "{TEST_ALPHALAND_TITLE}\t\tAlphaland\n{TEST_ALPHALAND_DESCR}\t\tOld story\n", utf16=True)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"display_name": "Betan League", "long_description": "New story",
                                                    "start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        path = [p for p in mod.text_files() if p.endswith("campaign_descriptions.txt")][0]
        text = "\n".join(plan.files[path].texts())
        self.assertIn("{TEST_BETA_TITLE}\tBetan League", text)
        self.assertIn("{TEST_BETA_DESCR}\tNew story", text)

    def test_descriptions(self):
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {
            "description": "Short one", "long_description": "Line one\nLine two",
            "start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        text = "\n".join(plan.files[mod.text_files()[0]].texts())
        self.assertIn("{BETA_DESCR}\t\tShort one", text)
        self.assertIn("{TEST_BETA_DESCR}\t\tLine one\\nLine two", text)
        self.assertIn("{TEST_ALPHA_DESCR}\t\tThe long Alphan story", text)
        # region labels named like the template are left alone
        self.assertFalse(any("regions_and_settlement_names" in p for p in plan.changed_files()))

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
