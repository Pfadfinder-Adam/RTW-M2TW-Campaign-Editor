"""End-to-end test on a tiny synthetic mod (no game files needed)."""

import hashlib
import os
import shutil
import struct
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from campaign_editor.build import build                     # noqa: E402
from campaign_editor.moddata import ModData                 # noqa: E402
from campaign_editor.plan import Plan, backup_label, backups, restore, restore_to  # noqa: E402
from campaign_editor.scan import scan                       # noqa: E402
from campaign_editor.newmod import create_mod, slim         # noqa: E402
from campaign_editor.strat import Strat                     # noqa: E402
from campaign_editor.textio import TextFile                 # noqa: E402

from campaign_editor.minimod import (SM, NAMES, EDU, REGIONS, STRAT, write, write_tga,  # noqa: E402
                                     make as make_minimod)


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
        make_minimod(self.root)

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
        after = {k: v for k, v in after.items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_clone_names_the_new_faction_in_medieval2_lists(self):
        """Medieval II names every faction in its battle banners, voice accents, one-liners, movies and campaign
        music (the VK -> TVB port crashed without them): the clone copies the template's entries, spelled as the
        file spells names, the banner texture on disk becomes the new faction's own; Restore byte for byte."""
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_banners_new.xml"),
              '<BannerDB>\n   <FactionBanners>\n      <Banner Name="main_spear">\n         <Textures>\n'
              '            <Texture Faction="Alpha" DiffuseMap="banners\\textures\\Faction_banner_alpha.texture"/>\n'
              '            <Texture Faction="Slave" DiffuseMap="banners\\textures\\Faction_banner_slave.texture"/>\n'
              '         </Textures>\n      </Banner>\n   </FactionBanners>\n</BannerDB>\n')
        write(os.path.join(d, "banners", "textures", "Faction_banner_alpha.texture"), "A-banner")
        write(os.path.join(d, "descr_sounds_accents.txt"), "accent English\n    factions slave, normans\n\n"
                                                            "accent Alphan\n    factions alpha\n")
        write(os.path.join(d, "descr_sounds_db.xml"), "<SoundDB>\n  <OneLiners>\n    <Faction>alpha</Faction>\n"
                                                      "    <Faction>slave</Faction>\n  </OneLiners>\n</SoundDB>\n")
        write(os.path.join(d, "descr_movies_tracks.xml"), '<movies>\n  <faction name="alpha">\n    <track>a.bik</track>\n'
                                                         '  </faction>\n</movies>\n')
        camp = os.path.join(d, "world", "maps", "campaign", "test")
        write(os.path.join(camp, "descr_faction_movies.xml"), "<factions>\n\t<faction>\n\t\t<name>alpha</name>\n"
                                                             "\t\t<intro>faction/alpha.bik</intro>\n\t</faction>\n</factions>\n")
        write(os.path.join(d, "world", "maps", "base", "descr_sounds_music_types.txt"),
              "music_type northern\n\tfactions slave alpha\n")
        before = tree_hash(self.root)
        plan = build(ModData(self.root), "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        def rd(*p):
            with open(os.path.join(d, *p), encoding="latin-1") as fh:
                return fh.read()
        self.assertIn('<Texture Faction="Beta" DiffuseMap="banners\\textures\\Faction_banner_beta.texture"/>',
                      rd("descr_banners_new.xml"))
        self.assertEqual(rd("banners", "textures", "Faction_banner_beta.texture"), "A-banner")
        self.assertIn("factions alpha, beta", rd("descr_sounds_accents.txt"))       # the file's commas
        self.assertIn("<Faction>alpha</Faction>\n    <Faction>beta</Faction>", rd("descr_sounds_db.xml"))
        self.assertIn('<faction name="beta">\n    <track>a.bik</track>', rd("descr_movies_tracks.xml"))
        self.assertIn("<name>beta</name>", rd("world", "maps", "campaign", "test", "descr_faction_movies.xml"))
        self.assertIn("factions slave alpha beta", rd("world", "maps", "base", "descr_sounds_music_types.txt"))
        self.assertEqual(rd("descr_banners_new.xml").count("Faction="), 3)            # slave's not copied
        restore(ModData(self.root), backups(ModData(self.root))[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_restore_to_undoes_a_backup_and_every_newer_one(self):
        before = tree_hash(self.root)
        mod = ModData(self.root)
        build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}}).apply()
        mid = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        mod = ModData(self.root)
        p2 = Plan(mod, None, "gamma")
        p2.binary(os.path.join(mod.campaign_dir("test"), "map_beta.tga"), b"repainted")
        p2.apply()
        bs = backups(mod)
        self.assertEqual(len(bs), 2)
        self.assertTrue(bs[0].endswith("_gamma") and bs[1].endswith("_beta"), bs)
        self.assertIn("beta (from alpha)", backup_label(bs[1]))
        self.assertIn("gamma  - 1 file", backup_label(bs[0]))
        ms = restore_to(mod, bs[1])                  # the oldest: both are undone, newest first
        self.assertEqual(len(ms), 2)
        self.assertEqual(backups(mod), [])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)
        self.assertNotEqual(mid, after)

    def test_modeldb_round_trip_and_clone(self):
        # Medieval II battle_models.modeldb: read back byte for byte, the clone copies the template's texture
        # entries (and attachment sets) for the new faction, Restore undoes it
        from campaign_editor import modeldb as MDB
        def model(name, facs, first=False):
            m = MDB.from_dict({"name": name, "scale": "1.12", "lods": [["unit_models/x/%s_lod0.mesh" % name, "121"]],
                               "textures": [[f, "unit_models/x/tex %s.texture" % f, "unit_models/x/n.texture",
                                             "unit_sprites/%s_s.spr" % f] for f in facs],
                               "attach": [[facs[0], "unit_models/a/shield.texture", "unit_models/a/n.texture", ""]],
                               "mounts": [{"type": "Horse", "primary": "fs_horse", "secondary": "",
                                           "weapons": ["w1"], "weapons2": []}],
                               "torch": ["-1", "0", "0", "0", "0", "0", "0"]})
            if first:
                m.ci = {k: ["0", "0"] for k in ("lodvec", "lod", "texvec", "tex", "mountvec", "mount", "weapons",
                                                 "torch")}
            return m
        text = "22 serialization::archive 3 0 0 0 0 2 0 0 " + " ".join(
            MDB.ModelDB.dump_models([model("knights", ["alpha", "slave"], True), model("spears", ["slave"])]))
        db = MDB.ModelDB(text)
        self.assertEqual(db.dump(), text)
        self.assertEqual(db.model("KNIGHTS").factions(), ["alpha", "slave"])
        # edited by hand (a tester's Total Vanilla Beyond: "modeldb: a number expected"): line breaks, tabs, two
        # spaces between the values read as the game reads them; the file written back in the game's own form
        edited = text.replace(" 6 spears ", "\r\n6 spears  ").replace(" 3 0 0", "\t3\t0 0", 1) + "\r\n"
        self.assertEqual(MDB.ModelDB(edited).dump(), text)
        # a model added by hand after the count at the top was left as it was (a tester: "modeldb: 1585 characters
        # left after 872 models"): the game reads only the counted ones - read, said, kept byte for byte
        extra = text + " " + " ".join(MDB.ModelDB.dump_models([model("archers", ["alpha"])]))
        db = MDB.ModelDB(extra)
        self.assertEqual([m.name for m in db.extra], ["archers"])
        self.assertIn("1 more follow (archers)", db.uncounted_note())
        self.assertIn("to 3", db.uncounted_note())
        self.assertEqual(db.dump(), extra)
        db.add_faction("alpha", "gamma")
        self.assertTrue(db.dump().endswith(extra[len(text):]))               # the uncounted model untouched
        self.assertEqual(MDB.ModelDB(db.dump()).model("knights").factions(), ["alpha", "slave", "gamma"])
        junk = MDB.ModelDB(text + " 7 broken")
        self.assertIn("characters follow the 2 models", junk.uncounted_note())
        self.assertEqual(junk.dump(), text + " 7 broken")
        path = os.path.join(self.root, "data", "unit_models", "battle_models.modeldb")
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as fh:
            fh.write(text.encode("latin-1"))
        before = tree_hash(self.root)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        got = MDB.load(path)
        self.assertEqual(got.model("knights").factions(), ["alpha", "slave", "beta"])
        self.assertEqual([r[0] for r in got.model("knights").attach], ["alpha", "beta"])
        self.assertEqual(got.model("spears").factions(), ["slave"])           # the template has none there
        self.assertEqual(MDB.ModelDB(got.dump()).dump(), got.dump())
        restore(ModData(self.root), backups(ModData(self.root))[0])
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if "_backups" not in k}, before)

    def test_medieval_city_and_castle(self):
        # M2: a castle = `settlement castle` + castle levels; the game converts by each level's convert_to
        from campaign_editor.buildings import (read_buildings, convert, set_kind, settlement_kind, kind_problem,
                                            has_castles)
        from campaign_editor.textio import TextFile
        path = os.path.join(self.root, "edb_m2.txt")
        write(path, """building core_building
{
    convert_to core_castle_building
    levels wooden_pallisade wooden_wall
    {
        wooden_pallisade city requires factions { northern_european, }
        {
            convert_to 1
            settlement_min town
        }
        wooden_wall city requires factions { northern_european, }
        {
            convert_to 2
            settlement_min large_town
        }
    }
}
building core_castle_building
{
    convert_to core_building
    levels motte_and_bailey wooden_castle castle
    {
        motte_and_bailey castle requires factions { northern_european, }
        {
            settlement_min village
        }
        wooden_castle castle requires factions { northern_european, }
        {
            convert_to 0
            settlement_min town
        }
        castle castle requires factions { northern_european, }
        {
            convert_to 1
            settlement_min large_town
        }
    }
}
building market
{
    levels corn_exchange
    {
        corn_exchange city requires factions { northern_european, }
        {
            settlement_min town
        }
    }
}
building smith
{
    levels leather_tanner
    {
        leather_tanner requires factions { northern_european, }
        {
            settlement_min town
        }
    }
}
""")
        known = {b.name: b for b in read_buildings(TextFile.load(path))}
        self.assertTrue(has_castles(known))
        city = [("core_building", "wooden_wall"), ("market", "corn_exchange"), ("smith", "leather_tanner")]
        got, changes = convert(city, "castle", known, "large_town")
        self.assertEqual(got, [("core_castle_building", "castle"), ("smith", "leather_tanner")])
        self.assertIn((("market", "corn_exchange"), None), changes)                 # a castle has no market
        self.assertEqual(convert(got, "city", known, "large_town")[0][0], ("core_building", "wooden_wall"))
        self.assertEqual(convert([], "castle", known, "village")[0], [("core_castle_building", "motte_and_bailey")])
        self.assertEqual(convert([("core_castle_building", "motte_and_bailey")], "city", known, "village")[0], [])
        # picked in the window (already fitted to a level set by hand): the governor's building is left alone -
        # the user's Inverness: wooden_wall for a large_town was refitted to the file's town (0.15.x)
        self.assertEqual(convert([("core_building", "wooden_wall")], "city", known, "town", fit_core=False)[0],
                         [("core_building", "wooden_wall")])
        self.assertTrue(kind_problem(known, "castle", "city"))           # castles stop at large_town here
        self.assertIsNone(kind_problem(known, "castle", "large_town"))
        raw = ["settlement\r\n", "{\r\n", "\tlevel town\r\n", "}\r\n"]
        castle = set_kind(raw, "castle", lambda t: t + "\r\n")
        self.assertEqual(castle[0], "settlement castle\r\n")
        self.assertEqual(settlement_kind(castle), "castle")
        self.assertEqual(set_kind(castle, "city", lambda t: t + "\r\n"), raw)
        # Rome has no castle levels: nothing offered
        rome = {b.name: b for b in read_buildings(ModData(self.root).load(ModData(self.root).file("edb")))}
        self.assertFalse(has_castles(rome))
        from campaign_editor.buildings import castles_allowed, with_kind
        self.assertFalse(castles_allowed(ModData(self.root), known))    # Rome: castle levels alone are not enough
        p = Plan(ModData(self.root), None, "x")
        with self.assertRaises(ValueError):
            with_kind(p, None, "R", raw, "castle", None, known)

    def test_own_name_list_for_new_and_edited_faction(self):
        from campaign_editor import namelists as NL
        from campaign_editor.edit import edit
        self.assertEqual(NL.parse("Abd al-Malik, Harun\nYusuf"), ["Abd al-Malik", "Harun", "Yusuf"])
        self.assertEqual(NL.parse("Harun  Yusuf harun"), ["Harun", "Yusuf"])
        self.assertEqual(NL.key_of("of Sparta"), "of_Sparta")
        self.assertEqual(NL.key_of(NL.Kept("de Avena")), "de Avena")        # M2 vanilla keeps such keys
        self.assertTrue(NL.problems({"characters": ["X"], "women": []}))
        self.assertTrue(NL.problems({"characters": ["Жан"], "women": ["A"]}))
        write(os.path.join(self.root, "data", "text", "names.txt"), "{Aaron}\t\tAaron\n", utf16=True)
        before = tree_hash(self.root)
        mod = ModData(self.root)
        pools = {"characters": ["Harun", "Abd al-Malik"], "surnames": ["ibn Said"], "women": ["Aisha"]}
        plan = build(mod, "test", "alpha", "beta", {"names": pools, "start": {"regions": ["B_R"], "leader": {"name": "Harun"}}})
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(mod.name_pool("beta"), {"characters": ["Harun", "Abd_al-Malik"], "surnames": ["ibn_Said"],
                                                 "women": ["Aisha"]})
        self.assertEqual(mod.name_pool("alpha")["characters"], ["Aaron", "Boris"])      # the template's untouched
        with open(mod.campaign_file("test", "descr_strat.txt")) as fh:
            strat = fh.read()
        leader = strat[strat.index("faction\tbeta") if "faction\tbeta" in strat else strat.index("faction beta"):]
        self.assertTrue(any(n in leader.split("character", 1)[1][:60] for n in ("Harun", "Abd_al-Malik")), leader[:300])
        texts = mod.load(mod.text_file("names.txt")).texts()
        self.assertIn("{Abd_al-Malik}\t\t\tAbd al-Malik", texts)
        # editing: a list that drops a name a character carries keeps that name
        p2 = edit(mod, "test", "beta", {"names": {"characters": ["Omar"], "women": ["Layla"]}})
        self.assertTrue(any("kept in the new list" in w for _, w in p2.warnings))
        got = p2.name_pool("beta")["characters"]
        self.assertEqual(got[0], "Omar")
        self.assertEqual(len(got), 2)
        p2.apply()
        restore_to(ModData(self.root), backups(ModData(self.root))[-1])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_name_section_shared_by_factions(self):
        # BI: one section serves a faction and its rebels ('faction: empire_east, empire_east_rebels')
        path = os.path.join(self.root, "data", "descr_names.txt")
        write(path, NAMES.replace("faction: alpha\n", "faction: alpha, alpha_rebels\n", 1))
        mod = ModData(self.root)
        self.assertEqual(mod.name_pool("alpha")["characters"], ["Aaron", "Boris"])
        self.assertEqual(mod.name_pool("alpha_rebels")["surnames"], ["Alphid"])
        self.assertEqual(mod.name_pool("nobody"), {})
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(mod.name_pool("beta")["characters"], ["Aaron", "Boris"])
        self.assertEqual(mod.name_pool("alpha")["characters"], ["Aaron", "Boris"])
        text = open(path, encoding="latin-1").read()
        self.assertIn("faction: beta\n", text)
        self.assertIn("faction: alpha, alpha_rebels\n", text)

    def test_building_pictures_from_the_game_and_never_another_culture(self):
        # Barbarian Invasion: bi/data has no roman pictures; the game's data/ui has them.
        # A roman level with no roman picture must stay empty, not show a barbarian one.
        from campaign_editor.buildings import BuildingPictures
        game, _ = self._game()
        gui = os.path.join(game, "data", "ui")
        write(os.path.join(gui, "roman", "buildings", "#roman_governors_house.tga"), "r")
        write(os.path.join(gui, "barbarian", "buildings", "#barbarian_governors_house.tga"), "b")
        write(os.path.join(gui, "barbarian", "buildings", "#barbarian_stables.tga"), "b")
        write(os.path.join(gui, "greek", "buildings", "#greek_temple.tga"), "g")
        write(os.path.join(game, "data", "descr_ui_buildings.txt"), "lookup_variants\n{\n\troman greek\n}\n")
        bi = os.path.join(game, "bi", "data")
        shutil.copytree(os.path.join(self.root, "data"), bi)
        write(os.path.join(bi, "ui", "roman", "buildings", "#roman_forum.tga"), "bi")
        pics = BuildingPictures(ModData(os.path.dirname(bi)))
        self.assertTrue(pics.find("roman", "governors_house").endswith(os.path.join("roman", "buildings", "#roman_governors_house.tga")))
        self.assertTrue(pics.find("roman", "forum").startswith(bi))
        self.assertTrue(pics.find("roman", "temple").endswith("#greek_temple.tga"))   # the file's variant
        self.assertIsNone(pics.find("roman", "stables"))                              # never barbarian
        self.assertTrue(pics.find("barbarian", "stables").endswith("#barbarian_stables.tga"))

    def test_family_limits_from_descr_ex(self):
        from campaign_editor.family import limit_warnings
        from campaign_editor.limits import ex_setting
        game, hlr = self._game()
        mod = ModData(hlr)
        self.assertEqual(ex_setting(mod, "max_num_ancillaries"), 8)       # no descr_ex.txt: the game's default
        self.assertEqual(ex_setting(mod, "max_num_children"), 4)
        write(os.path.join(game, "data", "descr_ex.txt"), "max_num_ancillaries 16\nmax_num_children 6\n")
        self.assertEqual(ex_setting(mod, "max_num_ancillaries"), 8)       # a mod never takes the game's copy
        write(os.path.join(hlr, "data", "descr_ex.txt"), "; the mod's own\nmax_factions 31\n")
        self.assertEqual(ex_setting(mod, "max_num_children"), 4)          # the mod's file decides: default
        self.assertEqual(ex_setting(ModData(os.path.join(game, "data")), "max_num_ancillaries"), 16)  # the game
        tree = [["Boris", "Anna", ["A", "B", "C", "D", "E"]]]
        changes = {"k": {"ancillaries": ["a%d" % i for i in range(9)]}}
        # REX beside the game (the user, 2026-10-03): no warning - the lines are rewritten to fit instead
        self.assertEqual(limit_warnings(mod, tree, changes, {}), [])
        from campaign_editor.family import _engine_settings
        plan = Plan(mod, "x", "y", {})
        _engine_settings(plan, tree, changes)
        text = "\n".join(plan.files[os.path.join(hlr, "data", "descr_ex.txt")].texts())
        self.assertIn("max_num_ancillaries 9", text)
        self.assertIn("max_num_children 5", text)
        self.assertIn("max_factions 31", text)                           # the mod's own lines kept
        os.remove(os.path.join(game, "REX.exe"))
        os.remove(os.path.join(hlr, "data", "descr_ex.txt"))
        os.remove(os.path.join(game, "data", "descr_ex.txt"))
        mod = ModData(hlr)                                               # the original exe: warned as before
        w = limit_warnings(mod, tree, changes, {})
        self.assertEqual(len(w), 3, w)                                    # 9 ancillaries; Boris and Anna 5 kids
        self.assertEqual(limit_warnings(mod, tree, {}, {}, old_tree=tree), [])   # nothing added: no warning

    def test_recruit_lines_are_not_capped(self):
        from campaign_editor import editors as E
        edb = ("building barracks\n{\n    levels militia_barracks\n    {\n"
               "        militia_barracks requires factions { alpha, }\n        {\n"
               "            capability\n            {\n"
               "                recruit \"alpha general\" 0 requires factions { alpha, }\n"
               "                law_bonus bonus 1\n            }\n"
               "            construction 1\n            cost 100\n            settlement_min town\n"
               "            upgrades\n            {\n            }\n        }\n    }\n}\n")
        p = os.path.join(self.root, "edb_test.txt")
        write(p, edb)
        f = TextFile.load(p)
        blk = E.building_blocks(f)[0]
        limits = E.line_limits(f, "building")
        # one recruit line is the most the "mod" has, yet another one may go in
        self.assertIsNone(E.room_for(f, "building", blk, "capability", "militia_barracks", "recruit", limits))
        # other keys keep the rule
        self.assertIsNotNone(E.room_for(f, "building", blk, "capability", "militia_barracks", "law_bonus", limits))

    def test_flag_sheets_follow_descr_standards(self):
        """The banner sheets are descr_standards.txt's faction list and then its rebel list; with the
        faction sheets full a new faction gets a new faction sheet - never a rebels' slot - and slave's
        flag (vanilla RTW: 20, the first rebel slot) keeps the picture it showed."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor import symbols as SY
        from campaign_editor.factionart import image_dds
        d = os.path.join(self.root, "data")
        extra = "".join("faction\t\tfill%d\nculture\t\teastern\nstandard_index\t\t%d\n\n" % (n, n) for n in (1, 2, 3))
        sm = SM.replace("culture\t\teastern\n", "culture\t\teastern\nstandard_index\t\t0\n", 1)
        sm = sm.replace("culture\t\tbarbarian\n", "culture\t\tbarbarian\nstandard_index\t\t4\n", 1)
        write(os.path.join(d, "descr_sm_factions.txt"), extra + sm)
        write(os.path.join(d, "descr_standards.txt"), "file_scale\t0.185f\n\nfactions\nsymbols\t\t\t\tbanners/symbols1.tga\n"
              "rebels_factions\nsymbols\t\t\t\tbanners/symbols2.tga\n")
        write(os.path.join(d, "descr_cultures.txt"), "culture\t\teastern\nrebel_standard_index\t0\n")
        os.makedirs(os.path.join(d, "banners"))
        for n, colour in ((1, (0, 200, 0, 255)), (2, (250, 130, 0, 255))):
            sheet = Image.new("RGBA", (128, 128), colour)
            with open(os.path.join(d, "banners", "symbols%d.tga.dds" % n), "wb") as fh:
                fh.write(image_dds(sheet))
        before = tree_hash(self.root)
        mod = ModData(self.root)
        self.assertEqual(SY.sheet_lists(mod), (["banners/symbols1.tga"], ["banners/symbols2.tga"]))
        self.assertEqual(SY.flag_of(mod, "slave")["rel"], "banners/symbols2.tga")
        self.assertIsNone(SY.free_slot(mod))                 # 0-3 taken; 4 is slave's and the rebels'
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(SY.sheet_lists(mod), (["banners/symbols1.tga", "banners/symbols3.tga"], ["banners/symbols2.tga"]))
        self.assertEqual(SY.flag_of(mod, "beta")["index"], 5)
        self.assertEqual(SY.flag_of(mod, "slave")["index"], 4)
        self.assertGreater(SY.flag_image(mod, "slave").getpixel((32, 32))[0], 200)     # still orange
        self.assertEqual(SY.flag_image(mod, "beta").getpixel((32, 32))[:3], SY.flag_image(mod, "alpha").getpixel((32, 32))[:3])
        restore_to(mod, backups(mod)[-1])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_new_faction_gets_its_own_flag_symbol_and_logos(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor import symbols as SY
        from campaign_editor.factionart import image_dds, image_tga
        d = os.path.join(self.root, "data")
        sm = SM.replace("culture\t\teastern\n", "culture\t\teastern\nstandard_index\t\t0\n"
                        "logo_index\t\tFACTION_LOGO_A\nsmall_logo_index\t\tSMALL_FACTION_LOGO_A\n", 1)
        sm = sm.replace("culture\t\tbarbarian\n", "culture\t\tbarbarian\nstandard_index\t\t1\n", 1)
        write(os.path.join(d, "descr_sm_factions.txt"), sm)
        write(os.path.join(d, "descr_caps_ex.txt"), "sprite_format  xml\n")
        sheet = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        sheet.paste(Image.new("RGBA", (64, 64), (0, 200, 0, 255)), (0, 0))      # alpha's slot 0: green
        os.makedirs(os.path.join(d, "banners"))
        with open(os.path.join(d, "banners", "symbols1.tga.dds"), "wb") as fh:
            fh.write(image_dds(sheet))
        for xml, page, spr, size in (("strat3.sd.xml", "stratpage_02.tga", "FACTION_LOGO_A", 52),
                                     ("shared2.sd.xml", "sharedpage_01.tga", "SMALL_FACTION_LOGO_A", 32)):
            write(os.path.join(d, "ui", xml), '<sprite_definitions version="7">\n  <page file="%s" w="64" h="64">\n'
                  '    <sprite name="%s" x="0" y="0" w="%d" h="%d" alpha="1"/>\n  </page>\n</sprite_definitions>\n'
                  % (page, spr, size, size))
            os.makedirs(os.path.join(d, "ui", "roman", "interface"), exist_ok=True)
            with open(os.path.join(d, "ui", "roman", "interface", page), "wb") as fh:
                fh.write(image_tga(Image.new("RGBA", (64, 64), (0, 0, 200, 255))))
        before = tree_hash(self.root)
        mod = ModData(self.root)
        self.assertEqual([e["rel"] for e in SY.entries(mod, "alpha")], [SY.FLAG, SY.LOGO, SY.SMALL])
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(SY.flag_of(mod, "beta")["index"], 2)                   # 0 and 1 are taken
        self.assertEqual(SY.flag_of(mod, "alpha")["index"], 0)
        self.assertEqual(SY.logo_of(mod, "beta", SY.LOGO)["name"], "FACTION_LOGO_BETA")
        self.assertEqual(SY.logo_of(mod, "alpha", SY.LOGO)["name"], "FACTION_LOGO_A")
        self.assertTrue(SY.logo_of(mod, "beta", SY.SMALL)["own"])
        self.assertEqual(SY.flag_image(mod, "beta").getpixel((32, 32))[:3], SY.flag_image(mod, "alpha").getpixel((32, 32))[:3])
        self.assertEqual(SY.logo_image(mod, "beta", SY.LOGO).size, (52, 52))
        # replacing beta's symbols leaves alpha's as they are
        red = os.path.join(self.root, "red.png")
        Image.new("RGBA", (90, 90), (220, 0, 0, 255)).save(red)
        from campaign_editor.edit import edit
        p2 = edit(mod, "test", "beta", {"art": {SY.FLAG: red, SY.LOGO: red}})
        p2.apply()
        mod = ModData(self.root)
        self.assertGreater(SY.flag_image(mod, "beta").getpixel((32, 32))[0], 180)
        self.assertLess(SY.flag_image(mod, "alpha").getpixel((32, 32))[0], 60)
        self.assertGreater(SY.logo_image(mod, "beta", SY.LOGO).getpixel((26, 26))[0], 180)
        self.assertEqual(SY.logo_image(mod, "alpha", SY.LOGO).getpixel((26, 26))[:3], (0, 0, 200))
        restore_to(mod, backups(mod)[-1])
        os.remove(red)
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_settlement_names_follow_owner_culture(self):
        # the map and the towns list show the name for the owner's culture as soon as a town changes hands
        from campaign_editor import culturenames as CN
        table = {"Atown": {"*": "Atown", "barbarian": "Atburg"}, "Btown": {"roman": "Bopolis"}}
        towns = {"A": "Atown", "B": "Btown", "C": "Ctown"}
        cult = {"julii": "roman", "gauls": "barbarian", "slave": "carthaginian"}.get
        self.assertEqual(CN.labels(table, towns, {"A": "gauls", "B": "julii", "C": "gauls"}, cult),
                         {"A": "Atburg", "B": "Bopolis"})
        self.assertEqual(CN.labels(table, towns, {"A": "julii", "B": "gauls"}, cult), {"A": "Atown"})
        self.assertEqual(CN.labels(table, towns, {}, cult), {"A": "Atown"})     # no owner = the rebels

    def test_settlement_names_by_culture_campaign_script(self):
        # REX's documented way (dump_docudemon): SettlementTurnStart / GeneralCaptureSettlement +
        # SettlementName + FactionCultureType -> console_command rename_settlement
        from campaign_editor import culturenames as CN
        from campaign_editor.regionedit import apply_opts
        game, hlr = self._game()
        write(os.path.join(hlr, "data", "descr_cultures.txt"), "culture roman\n{\n}\nculture barbarian\n{\n}\n")
        before = tree_hash(hlr)
        mod = ModData(hlr)
        self.assertEqual(CN.cultures(mod), ["roman", "barbarian"])
        plan = Plan(mod, None, "map")
        apply_opts(plan, "test", {"culture_names": {"Atown": {"*": "Atown", "barbarian": "Atburg"}}})
        plan.apply()
        mod = ModData(hlr)
        self.assertEqual(CN.read(mod, "test"), {"Atown": {"*": "Atown", "barbarian": "Atburg"}})
        with open(CN.script_path(mod, "test"), encoding="latin-1") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("script"))
        self.assertIn("monitor_event SettlementTurnStart SettlementName Atown", text)
        self.assertIn("and FactionCultureType barbarian", text)
        self.assertIn('console_command rename_settlement Atown "Atburg"', text)
        self.assertIn("and not FactionCultureType barbarian", text)
        self.assertIn("wait_monitors", text)
        with open(mod.campaign_file("test", "descr_strat.txt")) as fh:
            self.assertTrue(fh.read().rstrip().endswith("script\ncampaign_script.txt"))
        # a second write replaces the block, a script of the mod's own around it stays
        path = CN.script_path(mod, "test")
        with open(path, encoding="latin-1", newline="") as fh:
            own = fh.read().replace("script\r\n", "script\r\n\tdeclare_counter mine\r\n", 1)
        with open(path, "w", encoding="latin-1", newline="") as fh:
            fh.write(own)
        p2 = Plan(ModData(hlr), None, "map")
        apply_opts(p2, "test", {"culture_names": {"Atown": {"roman": "Atopolis"}}})
        p2.apply()
        with open(path, encoding="latin-1") as fh:
            text = fh.read()
        self.assertIn("declare_counter mine", text)
        self.assertIn('rename_settlement Atown "Atopolis"', text)
        self.assertNotIn("Atburg", text)
        self.assertEqual(text.count(CN.BEGIN), 1)
        with self.assertRaises(ValueError):                            # a culture the mod has not
            apply_opts(Plan(ModData(hlr), None, "map"), "test", {"culture_names": {"Atown": {"gaulish": "X"}}})
        restore_to(mod, backups(mod)[-1])
        after = {k: v for k, v in tree_hash(hlr).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)
        self.assertEqual(CN.engine(mod), ("REX", True))
        # Medieval II: M2EX runs it (the user: "on Medieval it is M2EX, not REX"); without it nothing is written
        os.rename(os.path.join(game, "REX.exe"), os.path.join(game, "M2EX.exe"))
        write(os.path.join(hlr, "data", "descr_religions.txt"), "religions\n{\n    catholic\n}\n")
        mod = ModData(hlr)
        self.assertEqual(CN.engine(mod), ("M2EX", True))
        p3 = Plan(mod, None, "map")
        apply_opts(p3, "test", {"culture_names": {"Atown": {"barbarian": "Atburg"}}})
        self.assertIn(CN.script_path(mod, "test"), list(p3.files) + list(p3.binaries))
        # checked in the game under M2EX (the user, 2026-09-30): no "not checked" warning any more
        self.assertFalse(any("M2EX" in w for _, w in p3.warnings))
        os.remove(os.path.join(game, "M2EX.exe"))
        p4 = Plan(ModData(hlr), None, "map")
        apply_opts(p4, "test", {"culture_names": {"Atown": {"barbarian": "Atburg"}}})
        self.assertTrue(any("no M2EX.exe" in w for _, w in p4.warnings))

    def test_check_mod_limits_know_the_engine(self):
        """Check mod's LIMITS: with REX beside the game it says so, and what REX is known to lift (regions)
        is never a fault; M2EX is named for Medieval II."""
        from campaign_editor.check import engine_limits
        from campaign_editor.limits import ENGINE_LIFTS
        game, hlr = self._game()
        mod = ModData(hlr)
        img = mod.region_map("test")
        many = {"R%d" % i: {} for i in range(750)}                       # HLR's 750 regions
        got = engine_limits(mod, "test", many, [], [], img)
        self.assertIn("REX beside the game", got[0][0])
        self.assertIn("LIMITS: none", got[0][0])                         # the user's rule: no limit at all
        self.assertFalse(any(fault for _, fault in got))
        from campaign_editor.limits import lifted
        for key in ("regions", "chains", "levels", "hidden_resources", "cultures", "anything"):
            self.assertTrue(lifted(mod, key))
        os.remove(os.path.join(game, "REX.exe"))
        got = engine_limits(ModData(hlr), "test", many, [], [], img)
        self.assertTrue(any(fault and "regions" in m for m, fault in got))   # the original exe stops at 200
        self.assertIn("units", ENGINE_LIFTS["M2EX.exe"])
        for key in ("regions", "map_size", "units", "religions"):          # one engine, the same lifts
            self.assertIn(key, ENGINE_LIFTS["REX.exe"])
            self.assertIn(key, ENGINE_LIFTS["M2EX.exe"])

    def test_record_age_follows_the_mods_age_of_manhood(self):
        """A living son off the map must be younger than the mod's age of manhood - REX's descr_ex.txt setting
        (default 16), not a fixed 16. At the age itself the game refuses him (REX, age_of_manhood 15, vanilla's
        15-year-old Ahmose: 'is a live male of age > 15 and so must be created as a named character')."""
        from campaign_editor import family as FM
        from campaign_editor.limits import manhood_age
        game, hlr = self._game()
        mod = ModData(hlr)
        self.assertEqual(manhood_age(mod), 16)
        son = [{"source": "record", "sex": "male", "age": 17, "name": "Boy", "key": "record:Boy#0"}]
        self.assertTrue(FM.record_age_problems(son, None, manhood_age(mod) - 1))
        at = [dict(son[0], age=16)]
        self.assertTrue(FM.record_age_problems(at, None, manhood_age(mod) - 1))
        self.assertFalse(FM.record_age_problems([dict(son[0], age=15)], None, manhood_age(mod) - 1))
        write(os.path.join(hlr, "data", "descr_ex.txt"), "; REX\nage_of_manhood 18\n")
        mod = ModData(hlr)
        self.assertEqual(manhood_age(mod), 18)
        self.assertFalse(FM.record_age_problems(son, None, manhood_age(mod) - 1))

    def test_religion_limit_only_on_the_original_exe(self):
        """The original exe takes 9 religions; with REX / M2EX beside the game a 10th is not refused (their
        README: religions uncapped) - the tool must not hold modders on REX to vanilla's limits."""
        from campaign_editor import religions as RL
        from campaign_editor.limits import lifted
        game, hlr = self._game()
        mod = ModData(hlr)
        full = ["r%d" % i for i in range(RL.MAX_RELIGIONS)]
        spec = {"name": "judaism", "shown": "Judaism", "picture": __file__}
        real = RL.names
        try:
            RL.names = lambda m: full
            self.assertTrue(lifted(mod, "religions"))
            self.assertFalse([p for p in RL.problems(mod, spec) if "religions" in p])       # REX: no limit
            os.remove(os.path.join(game, "REX.exe"))
            mod = ModData(hlr)
            self.assertIsNone(lifted(mod, "religions"))
            self.assertTrue([p for p in RL.problems(mod, spec) if "at most" in p])        # original exe: 9
        finally:
            RL.names = real

    def test_new_mod_from_bi_starts_barbarian_invasion(self):
        # REX starts BI with -bi (its own "Barbarian Invasion.bat"); a mod made from bi must too, else REX
        # reads it over the plain game's data (the user's bi_Empire_east log)
        game, _ = self._game()
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "bi", "data"))
        create_mod(os.path.join(game, "bi", "data"), "bi_test")
        with open(os.path.join(game, "bi_test", "Start_bi_test.bat")) as fh:
            bat = fh.read()
        self.assertIn("REX.exe -bi -nm -show_err -mod:bi_test", bat)

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
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
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

    def test_new_faction_gets_the_weapons_texture_line_too(self):
        """A tester in Medieval II (with M2EX, which reads descr_model_battle.txt): the test faction's men looked like
        bare skeletons in battle - their model lines had 'texture ce_test, ...' but no 'texture_attachments ce_test,
        ...', and a figure takes half its picture from that weapons / shields texture. The clone, a model given to
        a new owner and the catalogue all carry the line now."""
        from campaign_editor import models, packs
        dmb = os.path.join(self.root, "data", "descr_model_battle.txt")
        write(dmb, "type\tspear\nskeleton\tMTW2_Spear\n"
                   "texture\talpha, unit_models/_Units/A/textures/a_alpha.texture, unit_models/_Units/A/textures/n.texture\n"
                   "texture_attachments\talpha, unit_models/AttachmentSets/Final Kite_alpha_diff.texture, "
                   "unit_models/AttachmentSets/Final Kite_alpha_norm.texture\n\n")
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        text = "\n".join(plan.files[dmb].texts())
        self.assertIn("texture_attachments\tbeta, unit_models/AttachmentSets/Final Kite_alpha_diff.texture", text)
        self.assertIn("texture\tbeta, unit_models/_Units/A/textures/a_alpha.texture", text)
        lines, added = packs._owner_textures(["type spear", "texture alpha, a.texture",
                                              "texture_attachments alpha, k.texture, kn.texture"], ["gamma"])
        self.assertEqual(added, ["gamma"])
        self.assertIn("texture_attachments gamma, k.texture, kn.texture", lines)
        self.assertEqual(models._text_models(mod)["spear"].attach,
                         {"alpha": "unit_models/AttachmentSets/Final Kite_alpha_diff.texture"})
        from campaign_editor.check import weapons_texture_problems
        self.assertEqual(weapons_texture_problems(mod), [])
        with open(dmb) as fh:
            write(dmb, fh.read() + "type\tsword\ntexture\talpha, s.texture\ntexture\tbeta, s.texture\n"
                                    "texture_attachments\talpha, k.texture, kn.texture\n")
        self.assertEqual(weapons_texture_problems(ModData(self.root)), [("sword", ["beta"])])

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

    def test_engine_max_factions_follows_on_every_write(self):
        """REX beside the game (the user, 2026-10-03: 'no limit errors at all - just rewrite the line'): a mod whose
        max_factions is lower than its factions is put right by ANY write, silently (a note, no warning); without
        REX nothing is touched."""
        game, hlr = self._game()
        ex = os.path.join(hlr, "data", "descr_ex.txt")
        write(ex, "; mine\nmax_factions 1\n")
        mod = ModData(hlr)
        plan = Plan(mod, "x", "y", {})
        p = os.path.join(hlr, "data", "export_descr_unit.txt")
        f = plan.edit(p)
        f.set(0, f.text(0) + " ")
        plan.apply()
        self.assertIn("max_factions 2", open(ex).read())                # alpha + slave
        self.assertEqual(plan.warnings, [])
        os.remove(os.path.join(game, "REX.exe"))
        write(ex, "max_factions 1\n")
        os.rename(ex, ex + ".off")                                       # no descr_ex: no engine at all
        plan = Plan(ModData(hlr), "x", "y", {})
        f = plan.edit(p)
        f.set(0, f.text(0) + " ")
        plan.apply()
        self.assertFalse(os.path.exists(ex))

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
            bat = f.read()
        self.assertIn(b"REX.exe -nm -show_err -mod:Beta", bat)
        self.assertTrue(bat.startswith(b'cd /d "%~dp0.."'))       # the game's folder wherever it is started from
        plan = build(ModData(data), "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        removed = slim(data)
        left = sorted(os.path.relpath(os.path.join(d, n), data).replace(os.sep, "/")
                      for d, _, fs in os.walk(data) for n in fs)
        self.assertGreater(removed, 0)
        self.assertIn("descr_sm_factions.txt", left)
        self.assertIn("ui/units/beta/#alpha_general.tga", left)
        self.assertNotIn("ui/units/alpha/#alpha_general.tga", left)     # unchanged: the game has it

    def test_new_mod_under_m2ex_starts_with_features_mod(self):
        # M2EX's own Teutonic.bat: start "" "%~dp0M2EX.exe" --features.mod=mods/teutonic
        game = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, game)
        write(os.path.join(game, "M2EX.exe"), "exe")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "data"))
        create_mod(os.path.join(game, "data"), "Beta")
        with open(os.path.join(game, "mods", "Beta", "Start_Beta.bat"), "rb") as f:
            self.assertIn(b"M2EX.exe --features.mod=mods/Beta", f.read())

    def test_new_mod_on_medieval2_goes_into_mods_with_a_cfg(self):
        game = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, game)
        write(os.path.join(game, "medieval2.exe"), "exe")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "data"))
        data, st = create_mod(os.path.join(game, "data"), "Beta")
        target = os.path.join(game, "mods", "Beta")
        self.assertEqual(data, os.path.join(target, "data"))
        with open(os.path.join(target, "Beta.cfg"), "rb") as f:
            self.assertIn(b"mod = mods/Beta", f.read())
        with open(os.path.join(target, "Start_Beta.bat"), "rb") as f:
            self.assertIn(b"medieval2.exe @mods\\Beta\\Beta.cfg", f.read())
        # a mod made from that one: its own folder name in the .cfg it copies
        with open(os.path.join(target, "Beta.cfg"), "ab") as f:
            f.write(b"[game]\r\nunit_size = huge\r\n")
        data2, _ = create_mod(data, "Gamma")
        with open(os.path.join(game, "mods", "Gamma", "Gamma.cfg"), "rb") as f:
            text = f.read()
        self.assertIn(b"mod = mods/Gamma", text)
        self.assertIn(b"unit_size = huge", text)
        self.assertFalse(os.path.exists(os.path.join(game, "mods", "Gamma", "Beta.cfg")))
        self.assertEqual(data2, os.path.join(game, "mods", "Gamma", "data"))

    def test_editor_lists_sort_and_filter_by_what_a_record_is(self):
        from campaign_editor import editors as E
        from campaign_editor.factionart import label_of, where_shown
        edu = ("type\t\tmerc spear\ndictionary\tmerc_spear\ncategory\tinfantry\nclass\t\tspearmen\n"
               "attributes\tsea_faring, mercenary_unit\nownership\tslave, alpha\n"
               "type\t\tbeta horse\ndictionary\tbeta_horse\ncategory\tcavalry\nclass\t\theavy\n"
               "attributes\tgeneral_unit\nownership\tbeta\n")
        edb = ("building temple_of_war\n{\n    levels shrine\n    {\n        shrine requires factions { beta, }\n"
               "        {\n            capability\n            {\n                recruit \"beta horse\"  0\n"
               "            }\n        }\n    }\n}\nbuilding market\n{\n    levels stall\n    {\n"
               "        stall requires factions { alpha, beta, }\n        {\n        }\n    }\n}\n")
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_unit.txt"), edu)
        write(os.path.join(d, "export_descr_buildings.txt"), edb)
        mod = ModData(d)
        f = mod.load(mod.file("edu"))
        a, b = E.unit_blocks(f)
        self.assertEqual(E.block_facets(f, "unit", a), {"owners": ["slave", "alpha"], "category": "infantry",
                                                        "class": "spearmen", "mercenary": True, "general": False})
        self.assertTrue(E.block_facets(f, "unit", b)["general"])
        g = mod.load(mod.file("edb"))
        temple, market = E.building_blocks(g)
        self.assertEqual(E.block_facets(g, "building", temple), {"factions": ["beta"], "recruits": True,
                                                                 "group": "temple"})
        self.assertEqual(E.block_facets(g, "building", market)["group"], "economy")
        # the Art tab names every picture and says where the game shows it
        self.assertEqual(label_of("menu/battlefield_pics/france.tga"), "battle-select picture")
        self.assertEqual(label_of("world/maps/campaign/imperial_campaign/vc_france.tga"), "victory conditions map")
        self.assertIn("faction-select screen", where_shown("menu/fe_faction_units/france.tga"))
        self.assertEqual(label_of("ui/faction_symbols/france_roll.tga"), "faction symbol (in-game panels) (mouse over)")

    def test_map_drawn_tile_by_tile(self):
        try:
            import PIL  # noqa: F401 - the map is drawn with Pillow (the exe has it)
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor.mapdata import CampaignMap, GROUND_LOOK
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        hills, sea = (128, 128, 64), (64, 0, 0)
        # map_ground_types at 2x+1: the middle of tile (1, 2) is hills, the rest sea
        px = [[hills if (x, y) == (3, 5) else sea for x in range(9)] for y in range(9)]     # bottom-up
        write_tga(os.path.join(camp, "map_ground_types.tga"), 9, 9, px)
        cm = CampaignMap(ModData(os.path.join(self.root, "data")), "test")
        im = cm.background()
        self.assertEqual(im.size, (8, 8))
        # tile (1, 2) is the 2x2 block at column 2, row (4 - 1 - 2) * 2 top-down
        self.assertEqual({im.getpixel((2 + dx, 2 + dy)) for dx in (0, 1) for dy in (0, 1)}, {GROUND_LOOK[hills]})
        self.assertEqual(im.getpixel((0, 0)), GROUND_LOOK[sea])

    def test_check_and_install_a_pack(self):
        """A 'copy data over the game' pack checked file by file: new / same / replaces; a sprite page of another
        size that leaves sprites outside is kept back; a text differing in a few lines goes in as 'only its
        changes' (lines it would drop stay); another mod's whole file is kept back; README outside data/ is not
        put in; the install is one Plan and Restore gives the mod back byte for byte."""
        import zipfile
        from campaign_editor import modpack as MP
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "ui", "test.sd.xml"), '<sprite_definitions>\n  <page file="page.tga" w="64" h="64">\n'
              '    <sprite name="TOP" x="0" y="0" w="32" h="30"/>\n    <sprite name="LOW" x="0" y="40" w="32" h="20"/>\n'
              '  </page>\n</sprite_definitions>\n')
        red = [[(200, 0, 0)] * 64 for _ in range(64)]
        os.makedirs(os.path.join(d, "ui", "roman", "interface"), exist_ok=True)
        write_tga(os.path.join(d, "ui", "roman", "interface", "page.tga"), 64, 64, red)
        common = "".join("line %d\n" % i for i in range(30))
        write(os.path.join(d, "descr_things.txt"), common + "one 1\ntwo 2\nthree 3\nrex_only 9\nfour 4\n")
        before = tree_hash(self.root)
        pack = os.path.join(tempfile.mkdtemp(), "pack.zip")
        self.addCleanup(shutil.rmtree, os.path.dirname(pack))
        small = os.path.join(os.path.dirname(pack), "small.tga")
        write_tga(small, 64, 32, [[(0, 0, 200)] * 64 for _ in range(32)])
        with zipfile.ZipFile(pack, "w") as z:
            z.writestr("README.txt", "copy data over the game")
            with open(small, "rb") as fh:
                z.writestr("data/ui/roman/interface/page.tga", fh.read())
            z.writestr("data/ui/units/alpha/#new_card.tga", b"card")
            z.writestr("data/descr_things.txt", common + "one 1\ntwo 22\nthree 3\nfour 4\nfive 5\n")
            z.writestr("data/export_descr_unit.txt", "type something else entirely\n" * 40)
            with open(os.path.join(d, "descr_sm_factions.txt"), "rb") as fh:
                z.writestr("data/descr_sm_factions.txt", fh.read())
        files, left = MP.read(pack)
        self.assertEqual(left, ["README.txt"])
        mod = ModData(self.root)
        by = {e["rel"]: e for e in MP.check(mod, files)}
        self.assertEqual((by["ui/units/alpha/#new_card.tga"]["state"], by["ui/units/alpha/#new_card.tga"]["choice"]),
                         ("new", "install"))
        self.assertEqual(by["descr_sm_factions.txt"]["state"], "same")
        page = by["ui/roman/interface/page.tga"]
        self.assertEqual(page["choice"], "keep")
        self.assertIn("LOW", page["notes"][0][1])
        self.assertEqual(by["descr_things.txt"]["choice"], "merge")
        self.assertEqual(by["descr_things.txt"]["merge"], {"changed": 1, "added": 1, "kept": 1})
        self.assertEqual(by["export_descr_unit.txt"]["choice"], "keep")
        plan = Plan(mod, "pack", "mod_pack", {})
        MP.install(plan, files, list(by.values()))
        plan.apply()
        with open(os.path.join(d, "descr_things.txt")) as fh:
            self.assertEqual(fh.read(), common + "one 1\ntwo 22\nthree 3\nrex_only 9\nfour 4\nfive 5\n")
        self.assertTrue(os.path.exists(os.path.join(d, "ui", "units", "alpha", "#new_card.tga")))
        with open(os.path.join(d, "ui", "roman", "interface", "page.tga"), "rb") as fh:
            self.assertEqual(MP.picture_size(fh.read(), "page.tga"), (64, 64))
        restore(ModData(self.root), backups(ModData(self.root))[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_town_ring_rule(self):
        """The 8 tiles round a town are its own region or sea (0 exceptions in vanilla Rome and Medieval II), and
        on Medieval II no port stands in a town's 3 x 3: a move, a painted tile or a new region that breaks it is
        refused on Medieval II and warned about on Rome; Check mod finds it on the whole map."""
        from campaign_editor.check import town_ring_problems
        from campaign_editor.mapedit import apply_places, owner_of, place_problem, ring_problems
        from campaign_editor.plan import Plan
        from campaign_editor.regionedit import region_problems
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        R, B, K, S = (255, 0, 0), (0, 0, 255), (0, 0, 0), (41, 140, 233)
        px = [[R, R, R, B, B, B, S],
              [R, K, R, B, K, B, S],
              [R, R, R, B, B, B, S],
              [R, R, R, B, B, B, S],
              [R, R, R, B, B, B, S]]
        write_tga(os.path.join(camp, "map_regions.tga"), 7, 5, px)
        mod = ModData(self.root)
        self.assertEqual(mod.city_tiles("test"), {"A_R": (1, 1), "B_R": (4, 1)})
        self.assertEqual(town_ring_problems(mod, "test"), [])
        # Rome: warned, not refused
        self.assertIsNone(place_problem(mod, "test", "city", "B_R", (3, 2)))
        plan = Plan(mod, "map", "map", {})
        apply_places(plan, "test", [{"what": "city", "region": "B_R", "to": (3, 2)}])
        self.assertTrue(any("touches A_R's land" in w for _, w in plan.warnings))
        errors, warns = region_problems(mod, "test", {(2, 1): "B_R"}, [])
        self.assertEqual(errors, [])
        self.assertTrue(any("town of A_R touches B_R" in w for w in warns))
        # a port beside a town: nothing on Rome
        towns, ports = {"B_R": (4, 1)}, {"B_R": (5, 2)}
        self.assertEqual(ring_problems(mod, "test", owner_of(mod, "test"), towns, ports), [])
        # Medieval II: refused
        write(os.path.join(self.root, "data", "descr_religions.txt"), "religions\n{\n    catholic\n}\n")
        mod = ModData(self.root)
        why = place_problem(mod, "test", "city", "B_R", (3, 2))
        self.assertIn("touches A_R's land", why)
        errors, _ = region_problems(mod, "test", {(2, 1): "B_R"}, [])
        self.assertTrue(any("Medieval II crashes" in e for e in errors))
        got = ring_problems(mod, "test", owner_of(mod, "test"), towns, ports)
        self.assertEqual([s_ for s_, _ in got], [False])          # a warning: vanilla's norman_prologue has two
        self.assertIn("port of B_R stands next to the town of B_R", got[0][1])
        # Check mod sees a town already against another region
        px[1][2], px[1][1] = K, R                  # A's town moved to 2,1 beside B's land
        write_tga(os.path.join(camp, "map_regions.tga"), 7, 5, px)
        mod = ModData(self.root)
        self.assertTrue(town_ring_problems(mod, "test")[0][0])

    def test_a_grown_village_gets_its_governors_building(self):
        """A tester in Rome with REX: the test mod's town window grew a rebel village to a town (2600 people) and the
        game stopped: 'Settlement(Lepcis Magna) ... has not been given a core building ... should have a level 0 core
        building'. A village has none, so the governor's building of the new level is added - Rome's core chain
        names neither city nor castle. Check mod files says it of a town written by hand; and the age of manhood is
        not lowered under a living son off the map ('Ahmose is a live male of age > 15 ...')."""
        from campaign_editor import masstown as MT
        from campaign_editor.campaignrules import _manhood_fits
        from campaign_editor.check import check_mod
        from campaign_editor.buildings import settlement_info
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        red, blue, green, black = (255, 0, 0), (0, 0, 255), (0, 255, 0), (0, 0, 0)
        px = [[red, red, blue, blue, green, green],
              [red, black, blue, blue, green, black],
              [red, red, black, blue, green, green],
              [red, red, blue, blue, green, green]]
        write_tga(os.path.join(camp, "map_regions.tga"), 6, 4, px)
        write(os.path.join(camp, "descr_regions.txt"),
              REGIONS + "C_R\n\tCtown\n\tslave\n\tRebels\n\t0 255 0\n\tnone\n\t5\n\t1\n")
        village = "settlement\n{\n\tlevel village\n\tregion C_R\n\tpopulation 400\n}\n\n"
        write(os.path.join(camp, "descr_strat.txt"), STRAT.replace(";;\tBtown", village + ";;\tBtown"))
        write(os.path.join(self.root, "data", "export_descr_buildings.txt"), """building core_building
{
    levels governors_house governors_villa
    {
        governors_house requires factions { alpha, }
        {
            construction 1
            cost 100
            settlement_min town
            upgrades
            {
                governors_villa
            }
        }
        governors_villa requires factions { alpha, }
        {
            construction 2
            cost 900
            settlement_min large_town
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
        path = mod.campaign_file("test", "descr_strat.txt")
        plan = Plan(mod, "towns", "towns", {})
        MT.apply(plan, "test", {"towns": {"C_R": {"level": "town"}}})
        st = next(x for fb in Strat(plan.files[path]).factions for x in fb.settlements if x.region == "C_R")
        self.assertEqual(settlement_info(Strat(plan.files[path]).lines[st.start:st.end]),
                         ("town", [("core_building", "governors_house")]))
        # written by hand without it: Check mod files names it
        write(path, STRAT.replace(";;\tBtown", village.replace("village", "town") + ";;\tBtown"))
        self.assertIn("C_R (slave): a town without its governor's building", check_mod(ModData(self.root), "test"))
        # a son of 15 off the map: the age of manhood stays above him
        write(path, STRAT.replace(";;\tBtown", village + ";;\tBtown") + "character_record\t\tAhmose, \tmale, "
              "command 0, influence 0, management 0, subterfuge 0, age 15, alive, never_a_leader\n")
        mod = ModData(self.root)
        self.assertNotIn("Ahmose", check_mod(mod, "test"))                       # 15 under 16: fine
        with self.assertRaises(ValueError):
            _manhood_fits(mod, 15)
        _manhood_fits(mod, 16)
        with open(path) as fh:
            write(path, fh.read().replace("age 15, alive", "age 16, alive"))
        self.assertIn("Ahmose: a living man off the map (character_record) of 16", check_mod(ModData(self.root),
                                                                                              "test"))

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
        from campaign_editor.buildings import read_buildings, settlement_info
        bs = read_buildings(mod.load(mod.file("edb")))
        self.assertEqual([(l.name, l.settlement_min, l.cost) for l in bs[0].levels],
                         [("hut", "village", 100), ("hall", "city", 900)])
        plan = build(mod, "test", "alpha", "beta", {"start": {
            "regions": ["B_R"], "leader": {"name": "Boris"}, "buildings": {"B_R": [["core_building", "hall"]]}}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        st = s.faction("beta").settlements[0]
        # the game wants the core level one below the settlement level: hall (the chain's
        # second level) belongs to a large town, whatever its settlement_min says
        self.assertEqual(settlement_info(s.lines[st.start:st.end]), ("large_town", [("core_building", "hall")]))
        self.assertIn("\tpopulation 2000", s.lines[st.start:st.end])
        warnings = " ".join(m for _, m in plan.warnings)
        self.assertIn("hall is not for alpha's faction list", warnings)
        self.assertNotIn("needs a city", warnings)
        # a level set by hand wins, with a warning; population by hand too
        plan = build(ModData(self.root), "test", "alpha", "beta", {"start": {
            "regions": ["B_R"], "leader": {"name": "Boris"}, "buildings": {"B_R": [["core_building", "hall"]]},
            "sizes": {"B_R": {"level": "city", "population": 7000}}}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        st = s.faction("beta").settlements[0]
        self.assertEqual(settlement_info(s.lines[st.start:st.end])[0], "city")
        self.assertIn("\tpopulation 7000", s.lines[st.start:st.end])
        self.assertIn("belongs to a large_town, the level is set to city", " ".join(m for _, m in plan.warnings))
        with self.assertRaises(ValueError):
            build(ModData(self.root), "test", "alpha", "beta", {"start": {
                "regions": ["B_R"], "leader": {"name": "Boris"}, "buildings": {"B_R": [["core_building", "tower"]]}}})

    def test_edit_an_existing_faction(self):
        from campaign_editor.edit import edit, read_faction
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
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
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
        from campaign_editor.edit import edit, read_faction
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
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)
        with self.assertRaises(ValueError):                               # a name with no string
            edit(ModData(self.root), "test", "alpha", {"leader": {"name": "Zed"}})

    def test_effects_menu_and_insert(self):
        """The Effects field's right-click menu: the game's bonuses by group with plain words, the Combat_V_ ones
        for this mod; a pick is added after a comma with the value 1."""
        from campaign_editor import traitsedit as TE
        self.assertEqual(TE.add_effect("Command -1, TroopMorale 2", "Law"), "Command -1, TroopMorale 2, Law 1")
        self.assertEqual(TE.add_effect("", "Law"), "Law 1")
        self.assertEqual(TE.add_effect("Command 1, ", "Law"), "Command 1, Law 1")
        groups = dict(TE.effect_menu(ModData(self.root), {"Combat_V_Slave", "OddOne"}))
        self.assertIn("Command", [n for n, _ in groups["Generals and battle"]])
        self.assertIn("Combat_V_Slave", [n for n, _ in groups["Against a faction, culture or religion"]])
        self.assertEqual([n for n, _ in groups["Others this mod's files use"]], ["OddOne"])
        self.assertEqual(TE.parse_effects(TE.add_effect("Command 2", "Law")), [("Command", 2), ("Law", 1)])

    def test_pips_click_fits_the_traits(self):
        """A click on the character panel's pips: a trait he has moved to the level that gives the value, else a
        trait giving that attribute alone added; Dread = Chivalry below 0; nothing reaches it -> None."""
        from campaign_editor import charpanel as CP
        defs = {"GoodCommander": {"levels": ["a", "b", "c"], "effects": [[("Command", 1)], [("Command", 2)],
                                                                          [("Command", 3)]], "anti": ["BadCommander"],
                                  "characters": ["family"]},
                "Mixed": {"levels": ["m"], "effects": [[("Command", 1), ("Influence", 2)]], "anti": [],
                          "characters": ["family"]},
                "Spyish": {"levels": ["s"], "effects": [[("Influence", 5)]], "anti": [], "characters": ["spy"]},
                "Brute": {"levels": ["x", "y"], "effects": [[("Chivalry", -1)], [("Chivalry", -3)]], "anti": [],
                          "characters": ["family"]}}
        got, what = CP.traits_for("named character", [("GoodCommander", 1)], defs, [], {}, "Command", 3)
        self.assertEqual(dict(got)["GoodCommander"], 3)                     # his own trait moved up
        got, what = CP.traits_for("named character", [("Mixed", 1)], defs, [], {}, "Command", 4)
        self.assertEqual(sum(CP.attributes("rome", "named character", "", got, defs, [], {})[0][1:]), 4)
        got, _ = CP.traits_for("named character", [("GoodCommander", 2)], defs, [], {}, "Command", 0)
        self.assertNotIn("GoodCommander", dict(got))                        # taken off
        self.assertIsNone(CP.traits_for("named character", [], defs, [], {}, "Influence", 5))  # a spy's trait only
        got, _ = CP.traits_for("named character", [], defs, [], {}, "Dread", 3)
        self.assertEqual(dict(got)["Brute"], 2)

    def test_building_level_texts_per_culture(self):
        """The Building editor's texts: the suffixes a level has texts for (both games' {level_culture} keys, with
        _desc and _desc_short), and a changed name / description written into export_buildings.txt."""
        from campaign_editor import editors as E
        from campaign_editor.plan import Plan
        body = ("{farms}\tfarms\n{farms_desc}\tDO NOT TRANSLATE\n{farms_desc_short}\tDO NOT TRANSLATE\n"
                "{farms_eastern_european}\tLand Clearance\n{farms_eastern_european_desc}\tCleared land.\n"
                "{farms_carthage_desc}\tPunic fields.\n{farms+1_greek}\tCommunal\n")
        write(os.path.join(self.root, "data", "text", "export_buildings.txt"), body, utf16=True)
        mod = ModData(self.root)
        self.assertEqual(E.level_text_suffixes(mod, "farms"), ["", "carthage", "eastern_european"])
        plan = Plan(mod, "buildings", "buildings", {})
        path = mod.text_file("export_buildings.txt")
        E.set_text_values(plan, path, {"farms_eastern_european": "Woods Cut", "farms_greek_desc": "Olive groves.\nAnd more."})
        text = "\n".join(plan.files[path].texts())
        self.assertIn("{farms_eastern_european}\tWoods Cut", text)
        self.assertIn("{farms_eastern_european_desc}\tCleared land.", text)    # the rest untouched
        self.assertIn("{farms_greek_desc}\tOlive groves.\nAnd more.", text)       # a new key added

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
        from campaign_editor.edit import edit, read_faction
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
        from campaign_editor.edit import edit
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
                 {"kind": "fleet", "name": "Aaron Alphid", "units": ["alpha general"], "xy": (3, 0)}]
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {
            "regions": ["B_R"], "leader": {"name": "Boris"}, "characters": chars}})
        s = Strat(plan.files[mod.campaign_file("test", "descr_strat.txt")])
        got = [(c.name, c.kind, c.xy) for c in s.faction("beta").characters]
        self.assertIn(("Aaron", "general", (3, 1)), got)
        self.assertIn(("Boris Alphid", "spy", (2, 2)), got)
        self.assertIn(("Aaron Alphid", "admiral", (3, 0)), got)
        # a name the faction already gives someone: the game skips the second one ("duplicated character
        # name in this faction" - the user's nabataea army named like its leader)
        with self.assertRaises(ValueError) as e:
            build(ModData(self.root), "test", "alpha", "beta", {"start": {
                "regions": ["B_R"], "leader": {"name": "Boris"}, "characters": [dict(chars[0], name="Boris")]}})
        self.assertIn("duplicated character name", str(e.exception))
        bad = [dict(chars[0], name="Zed"), dict(chars[2], xy=(3, 2)), dict(chars[0], xy=(2, 2))]
        for c in bad:                                   # unknown name, fleet on land, army into a held town
            with self.assertRaises(ValueError):
                build(ModData(self.root), "test", "alpha", "beta", {"start": {
                    "regions": ["B_R"], "leader": {"name": "Boris"}, "characters": [c]}})
        from campaign_editor.edit import edit
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

    def test_captain_names_skip_family_records_and_two_word_names(self):
        # egypt's Heruben is a family record: a captain Heruben was skipped by the game as a duplicate;
        # Medieval II's 'al Adil' cannot start a character line (the game reads 'al' as the first name)
        from campaign_editor.edit import edit
        from campaign_editor.strat import first_names
        self.assertEqual(first_names({"characters": ["al Adil", "Omar"]}, "general"), ["Omar"])
        write(os.path.join(self.root, "data", "descr_names.txt"),
              NAMES.replace("\t\tAaron\n", "\t\tal Adil\n\t\tAaron\n", 1).replace("\t\tBoris\n", "\t\tBoris\n\t\tCyrus\n", 1))
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        with open(path) as fh:
            text = fh.read()
        with open(path, "w") as fh:
            fh.write(text.replace("weapon_lvl 0\n;#####<", "weapon_lvl 0\n\ncharacter_record\t\tBoris, \tmale, "
                                  "age 9, alive, never_a_leader\n;#####<", 1))
        p = edit(ModData(self.root), "test", "alpha", {"take": ["B_R"], "garrisons": {"B_R": ["alpha general"]}})
        said = "\n".join(m for _, m in p.notes)
        self.assertIn("captain Cyrus", said)

    def test_children_are_written_oldest_first(self):
        """A tester in Medieval II (with M2EX): 'Children of King Philip: Adenin (age 3) is supposed to be younger
        than Henry (age 1)' - a new son was put after a younger child. Both games want each couple's children oldest
        first (vanilla: every couple); the editor writes them so and Check mod files names a wrong order."""
        from campaign_editor import family
        from campaign_editor.check import check_mod
        from campaign_editor.edit import edit
        self.assertEqual(family.oldest_first([["F", "W", ["Henry", "X", "Adenin"]]], {"Henry": "1", "Adenin": "3"}),
                         [["F", "W", ["Adenin", "X", "Henry"]]])
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        with open(path) as fh:
            text = fh.read()
        text = text.replace("weapon_lvl 0\n;#####<", "weapon_lvl 0\n\ncharacter_record\t\tAnna, \tfemale, command 0, "
                            "influence 0, management 0, subterfuge 0, age 30, alive, never_a_leader\n"
                            "relative \tAaron Alphid, \tAnna,\t\tend\n;#####<", 1)
        with open(path, "w") as fh:
            fh.write(text)
        plan = edit(ModData(self.root), "test", "alpha", {"family": {
            "new": [{"name": "Boris", "sex": "male", "age": 1}, {"name": "Aaron", "sex": "male", "age": 3}],
            "tree": [["Aaron Alphid", "Anna", ["Boris", "Aaron"]]]}})          # the mini mod's names
        rel = next(l for l in plan.files[path].texts() if l.startswith("relative"))
        self.assertLess(rel.index("Aaron,\t"), rel.index("Boris,\t"))
        plan.apply()
        self.assertNotIn("is written before the older", check_mod(ModData(self.root), "test"))
        with open(path) as fh:
            text = fh.read()
        with open(path, "w") as fh:
            fh.write(text.replace("Aaron,\tBoris", "Boris,\tAaron"))
        self.assertIn("Boris is written before the older Aaron", check_mod(ModData(self.root), "test"))

    def test_family_edit_and_restore(self):
        """Family tab: traits, ages, a renamed leader followed on the tree, a new wife and child
        (records in the file's own form, the tree after them), then Restore byte for byte."""
        from campaign_editor import family
        from campaign_editor.edit import edit
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        with open(path) as fh:
            text = fh.read()
        text = text.replace("age 40, , x 1, y 1\n", "age 40, , x 1, y 1\ntraits Brave 1 \n", 1)
        text = text.replace("weapon_lvl 0\n;#####<", "weapon_lvl 0\n\ncharacter_record\t\tAnna, \tfemale, command 0, "
                            "influence 0, management 0, subterfuge 0, age 30, alive, never_a_leader\n"
                            "relative \tAaron Alphid, \tAnna,\t\tend\n;#####<", 1)
        with open(path, "w") as fh:
            fh.write(text)
        write(os.path.join(self.root, "data", "export_descr_character_traits.txt"),
              "Trait Brave\n    Characters family\n    AntiTraits Coward\n\n    Level Bold\n    Level Fearless\n\n"
              "Trait Coward\n    Characters family\n\n    Level Timid\n")
        write(os.path.join(self.root, "data", "export_descr_ancillaries.txt"), "Ancillary scribe\n    Image x.tga\n")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        fam = family.read(mod.load(path), "alpha")
        self.assertEqual(fam["tree"], [["Aaron Alphid", "Anna", []]])
        lead = fam["people"][0]
        self.assertEqual((lead.name, lead.role, lead.traits), ("Aaron Alphid", "leader", [["Brave", 1]]))
        anna = next(p for p in fam["people"] if p.name == "Anna")
        opts = {"people": {lead.key: {"name": "Boris Alphid", "traits": [["Brave", 2]], "ancillaries": ["scribe"]},
                           anna.key: {"age": 33}},
                "new": [{"name": "Aaron Alphid", "sex": "male", "age": 5}]}
        opts["tree"] = [["Boris Alphid", "Anna", ["Aaron Alphid"]]]
        for bad in ({"people": {lead.key: {"traits": [["Brave", 3]]}}},          # Brave has 2 levels
                    {"people": {lead.key: {"traits": [["Nosuch", 1]]}}},
                    {"people": {lead.key: {"name": "Zed"}}},                      # no such name: the game crashes
                    {"tree": [["Aaron Alphid", "Anna", ["Aaron Alphid"]]]},     # his own child
                    # a living man off the map over 16 crashes the game (heavengames descr_strat reference)
                    {"new": [{"name": "Aaron", "sex": "male", "age": 25}],
                     "tree": [["Aaron Alphid", "Anna", ["Aaron"]]]}):
            with self.assertRaises(ValueError):
                edit(ModData(self.root), "test", "alpha", {"family": bad})
        # no age given: a son is written at 15 (one under the age of manhood - the game refuses 16), a daughter at 20
        p1 = edit(ModData(self.root), "test", "alpha", {"family": {"new": [{"name": "Aaron", "sex": "male"}],
                                                                   "tree": [["Aaron Alphid", "Anna", ["Aaron"]]]}})
        self.assertTrue(any("Aaron, " in l and "age 15," in l for l in Strat(p1.files[path]).lines))
        # a new man tied to no one is no error: he goes on the map as a general (with an army) in the first town
        pg = edit(ModData(self.root), "test", "alpha", {"family": {"new": [{"name": "Aaron", "sex": "male",
                                                                            "age": 25}]}})
        gl = Strat(pg.files[path]).lines
        at = next(i for i, l in enumerate(gl) if l.lstrip().startswith("character") and "Aaron, " in l)
        self.assertIn("general", gl[at])
        self.assertTrue(any(l.strip() == "army" for l in gl[at:at + 3]))
        # the leader renamed on the Faction tab: the tree follows (a stale name there is nobody)
        p0 = edit(ModData(self.root), "test", "alpha", {"leader": {"name": "Boris Alphid", "age": 40}})
        self.assertIn("relative \tBoris Alphid, \tAnna,\t\tend", Strat(p0.files[path]).lines)
        plan = edit(mod, "test", "alpha", {"family": opts})
        plan.apply()
        with open(path) as fh:
            lines = fh.read().splitlines()
        self.assertIn("character\tBoris Alphid, named character, leader, age 40, , x 1, y 1", lines)
        self.assertIn("traits Brave 2 ", lines)
        self.assertIn("ancillaries scribe", lines)
        self.assertIn("character_record\t\tAnna, \tfemale, command 0, influence 0, management 0, subterfuge 0, "
                      "age 33, alive, never_a_leader", lines)
        self.assertIn("character_record\t\tAaron Alphid, \tmale, command 0, influence 0, management 0, "
                      "subterfuge 0, age 5, alive, never_a_leader", lines)
        rel = [i for i, l in enumerate(lines) if l.startswith("relative")]
        self.assertEqual([lines[i] for i in rel], ["relative \tBoris Alphid, \tAnna,\t\tAaron Alphid,\tend"])
        self.assertLess(max(i for i, l in enumerate(lines) if l.startswith("character_record")), rel[0])
        fam = family.read(ModData(self.root).load(path), "alpha")
        self.assertEqual(fam["tree"], [["Boris Alphid", "Anna", ["Aaron Alphid"]]])
        mod = ModData(self.root)
        restore(mod, backups(mod)[0])
        after = tree_hash(self.root)
        self.assertEqual({k: v for k, v in after.items() if "_backups" not in k}, before)

    def test_family_m2_portrait(self):
        """Medieval II: a character's own portrait = ui/custom_portraits/<folder>/portrait_young|old|dead.tga
        + ', portrait <folder>' on his line; Rome refuses; Restore removes the pictures and the folder."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import family
        from campaign_editor.edit import edit
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        with self.assertRaises(ValueError):                  # Rome: the game rolls portraits itself
            key = family.read(mod.load(path), "alpha")["people"][0].key
            edit(mod, "test", "alpha", {"family": {"portraits": {key: {"young": "x.png"}}}})
        with open(path) as fh:
            text = fh.read()
        with open(path, "w") as fh:
            fh.write(text.replace("Aaron Alphid, named character, leader, age 40, , x 1, y 1",
                                  "Aaron Alphid, named character, male, leader, age 40, x 1, y 1"))
        src = os.path.join(self.root, "face.png")
        Image.new("RGB", (120, 160), (200, 10, 10)).save(src)
        before = tree_hash(self.root)
        mod = ModData(self.root)
        key = family.read(mod.load(path), "alpha")["people"][0].key
        edit(mod, "test", "alpha", {"family": {"portraits": {key: {"young": src}}}}).apply()
        with open(path) as fh:
            self.assertIn("male, leader, age 40, x 1, y 1, portrait alpha_aaron_alphid", fh.read())
        folder = os.path.join(self.root, "data", "ui", "custom_portraits", "alpha_aaron_alphid")
        for a in ("young", "old", "dead"):
            with Image.open(os.path.join(folder, "portrait_%s.tga" % a)) as im:
                self.assertEqual(im.size, (69, 96))
        mod = ModData(self.root)
        restore(mod, backups(mod)[0])
        self.assertFalse(os.path.exists(os.path.join(self.root, "data", "ui", "custom_portraits")))
        after = tree_hash(self.root)
        self.assertEqual({k: v for k, v in after.items() if "_backups" not in k}, before)

    def test_portrait_library_add(self):
        """A new portrait goes under the next free number into every folder of its group (young, old,
        dead, the cards), in the culture's own sizes and folder case; Restore takes it all away."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import portraits as PL
        from campaign_editor.plan import Plan
        base = os.path.join(self.root, "data", "ui", "eastern", "portraits")
        for folder, size in ((("portraits", "Young", "generals"), (69, 96)), (("portraits", "old", "generals"), (69, 96)),
                             (("portraits", "dead"), (69, 96)), (("cards", "Young", "generals"), (44, 63)),
                             (("cards", "old", "generals"), (44, 63)), (("cards", "dead"), (44, 63)),
                             (("portraits", "Young", "civilians"), (69, 96))):
            d = os.path.join(base, *folder)
            os.makedirs(d)
            for n in (0, 1):
                Image.new("RGBA", size, (9, 9, 9, 255)).save(os.path.join(d, "%03d.tga" % n))
        src = os.path.join(self.root, "face.png")
        Image.new("RGB", (200, 300), (250, 0, 0)).save(src)
        before = tree_hash(self.root)
        mod = ModData(self.root)
        self.assertEqual(PL.cultures(mod)[:1], ["eastern"])
        lib = PL.library(mod, "eastern")
        self.assertEqual((lib["generals"]["count"], len(lib["generals"]["dead"])), (2, 2))
        plan = Plan(mod, "characters", "characters")
        self.assertEqual(PL.add(plan, "eastern", "generals", [{"young": src}]), [2])
        plan.apply()
        for folder, size in ((("portraits", "Young", "generals"), (69, 96)), (("portraits", "dead"), (69, 96)),
                             (("cards", "old", "generals"), (44, 63)), (("cards", "dead"), (44, 63))):
            with Image.open(os.path.join(base, *(folder + ("002.tga",)))) as im:
                self.assertEqual(im.size, size)
        with Image.open(os.path.join(base, "portraits", "dead", "002.tga")) as im:
            r, g, b = im.convert("RGB").getpixel((30, 40))
            self.assertEqual(r, g)                               # the dead one greyed
        mod = ModData(self.root)
        restore(mod, backups(mod)[0])
        after = tree_hash(self.root)
        self.assertEqual({k: v for k, v in after.items() if "_backups" not in k}, before)

    def test_volcanoes_and_land_bridges(self):
        from campaign_editor import terrain as T
        # land bridges are Medieval II's (vanilla Rome's map has none); volcanoes both games
        self.assertIn(T.LAND_BRIDGE, T.feature_brushes("medieval2"))
        self.assertNotIn(T.LAND_BRIDGE, T.feature_brushes("rome"))
        self.assertIn(T.VOLCANO, T.feature_brushes("rome"))
        # a straight strip is fine, a lone tile, a bent group or a broken strip is named
        B = T.LAND_BRIDGE
        self.assertEqual(T.bridge_warnings({(4, 2): B, (5, 2): B, (6, 2): B, (9, 9): (0, 0, 255)}), [])
        self.assertEqual(T.bridge_warnings({(4, 2): B, (4, 3): B, (4, 4): B}), [])
        self.assertEqual(len(T.bridge_warnings({(1, 1): B})), 1)
        self.assertIn("straight", T.bridge_warnings({(1, 1): B, (2, 2): B})[0][3])

        class Map:
            w = h = 10

            def is_sea(self, x, y):
                return x == 5
        # a bridge may cross the sea, a volcano may not; neither under a town (the bridge's land end may)
        self.assertIsNone(T.paint_problem(Map(), "features", (5, 2), B, set()))
        self.assertIn("on land", T.paint_problem(Map(), "features", (5, 2), T.VOLCANO, set()))
        self.assertIn("town", T.paint_problem(Map(), "features", (3, 2), T.VOLCANO, {(3, 2)}))

    def test_river_pieces(self):
        """The game follows a river side to side from the sea, the map's edge, a source or another river,
        and stops at a corner-only step (the user's river west of the Nile): such a piece is named."""
        from campaign_editor import terrain as T
        R = (0, 0, 255)
        joined = {(0, 3): R, (1, 3): R, (2, 3): R, (2, 2): R}               # from the map's edge
        corner = {(3, 1): R, (4, 1): R}                                     # only a corner touches (2, 2)
        self.assertEqual(T.river_warnings({**joined, **corner}, 8, 8), [(3, 1, 2)])
        self.assertEqual(T.river_warnings(joined, 8, 8), [])
        inland = {(4, 4): R, (5, 4): R}
        self.assertEqual(T.river_warnings(inland, 8, 8), [(4, 4, 2)])
        self.assertEqual(T.river_warnings(inland, 8, 8, is_sea=lambda x, y: (x, y) == (6, 4)), [])
        self.assertEqual(T.river_warnings({**inland, (3, 4): (255, 255, 255)}, 8, 8), [])  # a source
        # 2 x 2 blocks and rings (heavengames: a river is one tile wide and never rejoins itself)
        block = {(1, 1): R, (2, 1): R, (1, 2): R, (2, 2): R}
        self.assertEqual(T.river_shapes(block), [("square", 1, 1)])
        ring = {(x, y): R for x in range(1, 5) for y in range(1, 5) if x in (1, 4) or y in (1, 4)}
        self.assertEqual(T.river_shapes(ring), [("loop", 1, 1, 12)])
        self.assertEqual(T.river_shapes(ring, painted={(7, 7)}), [])                   # not this edit's
        self.assertEqual(T.river_shapes(joined), [])
        self.assertEqual(T.river_shapes({(x, y): R for x in range(3) for y in range(3)}),   # a solid 3 x 3: blocks only
                         [("square", 0, 0), ("square", 1, 0), ("square", 0, 1), ("square", 1, 1)])
        # the brush's staircase: a diagonal step gets the corner tile before it, a jump every tile between
        self.assertEqual(T.river_path((2, 2), (3, 1)), [(3, 2), (3, 1)])
        path = T.river_path((0, 0), (3, 2))
        self.assertEqual(path[-1], (3, 2))
        for a, b in zip([(0, 0)] + path, path):
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)

    def test_faction_limit(self):
        """REX / M2EX read max_factions from data/descr_ex.txt: over it the game closes at start ("Too many
        factions described here, maximum is(21)" - the user's nabataea). They have no limit of their own: a new
        faction raises max_factions in the same plan, unasked (backup, Restore); the original exe cannot be raised."""
        from campaign_editor.limits import faction_limit
        start = {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}}
        mod = ModData(self.root)
        self.assertFalse(faction_limit(mod)["known"])            # no exe beside the data: warned only
        build(mod, "test", "alpha", "beta", start)
        d = os.path.join(self.root, "data")
        write(os.path.join(self.root, "RomeTW.exe"), "exe")
        write(os.path.join(d, "descr_ex.txt"), "max_factions 2\n")
        # descr_ex.txt comes only with an engine: REX is taken as installed though its exe was not seen
        lim = faction_limit(ModData(self.root))
        self.assertEqual((lim["max"], lim["engine"], lim["known"]), (2, "REX.exe", True))
        os.rename(os.path.join(d, "descr_ex.txt"), os.path.join(self.root, "ex.bak"))
        lim = faction_limit(ModData(self.root))                   # the original exe alone: 21
        self.assertEqual((lim["max"], lim["engine"], lim["known"]), (21, None, True))
        os.rename(os.path.join(self.root, "ex.bak"), os.path.join(d, "descr_ex.txt"))
        os.remove(os.path.join(self.root, "RomeTW.exe"))
        write(os.path.join(self.root, "REX.exe"), "exe")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        self.assertEqual(faction_limit(mod)["max"], 2)
        plan = build(mod, "test", "alpha", "beta", start)          # raised by itself, no question (the user)
        self.assertTrue(any("max_factions 2 -> 3" in n for _, n in plan.notes))
        plan.apply()
        with open(os.path.join(d, "descr_ex.txt")) as fh:
            self.assertIn("max_factions 3", fh.read())
        restore(ModData(self.root), backups(ModData(self.root))[0])
        after = tree_hash(self.root)
        self.assertEqual({k: v for k, v in after.items() if "_backups" not in k}, before)
        # no descr_ex.txt at all: REX's default (21 for Rome) - far from 3 factions here
        os.remove(os.path.join(d, "descr_ex.txt"))
        self.assertEqual(faction_limit(ModData(self.root))["max"], 21)

    def test_editor_put_into_the_game_folder(self):
        """An exe started outside every game folder offers once per version to go into the game's folder: the folder
        the user picks is checked (a game exe must lie there), the exe goes there with the settings (when that place
        has none yet), an older copy of the editor there is replaced; a folder without the game is refused."""
        import sys
        from unittest import mock
        from campaign_editor import log, relocate, settings
        downloads = os.path.join(self.root, "Downloads")
        game = os.path.join(self.root, "Rome Total War")
        exe = os.path.join(downloads, "RTW-M2TW-Campaign-Editor.exe")
        write(exe, "new editor")
        write(os.path.join(downloads, "CampaignEditor_settings.json"), '{"theme": "dark"}')
        write(os.path.join(game, "RomeTW.exe"), "the game")
        write(os.path.join(game, "RTW-M2TW-Campaign-Editor.exe"), "old editor")
        saved = (log._candidates, log._home, log._path, settings._data)
        try:
            log._candidates, log._home, log._path, settings._data = (lambda: iter([downloads])), None, None, None
            with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(sys, "executable", exe):
                self.assertTrue(relocate.should_offer("9.9"))
                relocate.asked("9.9")
                self.assertFalse(relocate.should_offer("9.9"))             # once per version
                self.assertTrue(relocate.should_offer("9.10"))             # a new version asks again
                relocate.asked("9.10", never=True)
                self.assertFalse(relocate.should_offer("9.11"))            # 'Don't ask again'
                self.assertIn("none of the games' exes", relocate.target_problem(downloads))
                self.assertIsNone(relocate.target_problem(game))
                new = relocate.move_to(game)
                self.assertEqual(new, os.path.join(game, "RTW-M2TW-Campaign-Editor.exe"))
                with open(new) as fh:
                    self.assertEqual(fh.read(), "new editor")             # the older copy replaced
                with open(os.path.join(game, "CampaignEditor_settings.json")) as fh:
                    self.assertIn("dark", fh.read())                       # the settings came along
                self.assertTrue(os.path.isfile(exe))                       # the started copy stays where it was
                with mock.patch.object(sys, "executable", new):
                    self.assertFalse(relocate.should_offer("10.0"))         # in the game folder: never asks
        finally:
            log._candidates, log._home, log._path, settings._data = saved

    def test_log_in_logs_folder(self):
        """Beside the exe (in the game's folder): CampaignEditor_logs/ (the log, the zips, sessions/) and
        CampaignEditor_settings.json. An older version's RTW-M2TW-Campaign-Editor-files (settings, logs/ with
        faction_tool.log and a zip) is moved in once and goes; on close a session folder gets this session's part
        of the log and the game's system.log.txt."""
        from campaign_editor import log, settings
        home = os.path.join(self.root, "game")
        old = os.path.join(home, "RTW-M2TW-Campaign-Editor-files")
        os.makedirs(os.path.join(old, "logs"))
        write(os.path.join(home, "RomeTW.exe"), "exe")
        write(os.path.join(home, "system.log.txt"), "game log\n")
        with open(os.path.join(old, "logs", "faction_tool.log"), "w") as fh:
            fh.write("old entry\n")
        write(os.path.join(old, "logs", "logs_1.zip"), "zip")
        write(os.path.join(old, "faction_tool_settings.json"), '{"theme": "dark"}')
        saved = (log._candidates, log._home, log._path, settings._data, log._session_start)
        try:
            log._candidates, log._home, log._path, settings._data = (lambda: iter([home])), None, None, None
            logs = os.path.join(home, "CampaignEditor_logs")
            self.assertEqual(log.path(), os.path.join(logs, "CampaignEditor.log"))
            self.assertEqual(log.logs_dir(), logs)
            self.assertFalse(os.path.exists(old))                         # moved in and gone
            self.assertTrue(os.path.isfile(os.path.join(logs, "logs_1.zip")))
            self.assertEqual(settings._path(), os.path.join(home, "CampaignEditor_settings.json"))
            self.assertEqual(settings.get("theme"), "dark")
            log.session_start()
            log.write("new entry")
            with open(log.path()) as fh:
                self.assertEqual([l.split("  ", 1)[-1] for l in fh.read().splitlines()], ["old entry", "new entry"])
            out = log.save_session(home)
            with open(os.path.join(out, "CampaignEditor.log")) as fh:
                self.assertEqual([l.split("  ", 1)[-1] for l in fh.read().splitlines()], ["new entry"])
            with open(os.path.join(out, "game_system.log.txt")) as fh:
                self.assertEqual(fh.read(), "game log\n")
            # the next session keeps no second copy of an unchanged game log (a tester: logs grew to 61 MB),
            # and a big one is kept as a report sends it (its start, errors, end), not whole
            log._session_start = (0, "2099-01-01_00-00-00")
            out2 = log.save_session(home)
            self.assertFalse(os.path.exists(os.path.join(out2, "game_system.log.txt")))
            game_log = os.path.join(home, "system.log.txt")
            with open(game_log, "w") as fh:
                fh.write("start\n" + "x" * 80 + "\n" * 1 + ("10:00 [ai] [info] thinking\n" * 120000) + "end\n")
            log._session_start = (0, "2099-01-02_00-00-00")
            out3 = log.save_session(home)
            kept = os.path.getsize(os.path.join(out3, "game_system.log.txt"))
            self.assertLess(kept, os.path.getsize(game_log) // 2)
        finally:
            log._candidates, log._home, log._path, settings._data, log._session_start = saved

    def test_files_from_a_newer_version_do_not_break_this_one(self):
        """Going back to this version after a newer one: whatever the newer one wrote is read without an error -
        settings of other kinds (or a file that is no settings dict) read as not there, a backup whose record has
        another form is listed and refused in plain words with nothing changed, a mod folder's mark of another form
        is no mark, a Module builder module made with blocks this version does not know is listed and says what
        it cannot read, reports' 'seen' marks of another form count as unseen."""
        import json
        from unittest import mock
        from campaign_editor import log, settings, newmod, report, modbuilder as MB, addons as AD
        from campaign_editor.plan import backups, backup_label, restore
        home = tempfile.mkdtemp()
        sp = os.path.join(home, log.SETTINGS_NAME)
        with mock.patch.object(log, "home", return_value=home):
            for text in ("[1, 2, 3]", "not json", '"a string"'):
                with open(sp, "w") as fh:
                    fh.write(text)
                settings._data = None
                self.assertEqual(settings.get("games", []), [])
                self.assertIsNone(settings.get("game"))
            with open(sp, "w") as fh:
                json.dump({"game": {"path": "C:/x"}, "games": "C:/x", "campaigns": ["a"], "map_look": "tiles",
                           "editor_list_width_unit": "wide", "reports_check": "yes", "map_legend": 0,
                           "future_key": {"anything": 1}, "theme": "dark"}, fh)
            settings._data = None
            self.assertIsNone(settings.get("game"))
            self.assertEqual(settings.get("games") or [], [])
            self.assertEqual(settings.get("campaigns") or {}, {})
            self.assertEqual(settings.get("map_look") or {}, {})
            self.assertIsNone(settings.get("editor_list_width_unit"))
            self.assertTrue(settings.get("reports_check", True))
            self.assertEqual(settings.get("map_legend", True), 0)                # a bool kept as 0 / 1 is fine
            self.assertEqual(settings.get("theme"), "dark")
            self.assertEqual(settings.get("future_key"), {"anything": 1})      # unknown to this version: as it is
            self.assertEqual(settings.get("future_key", []), [])              # ... unless asked for another kind
        settings._data = None
        # a backup with another record
        mod = ModData(self.root)
        root = os.path.dirname(mod.data)
        bdir = os.path.join(root, "CampaignEditor_backups", "20991231_235959_future")
        os.makedirs(bdir)
        with open(os.path.join(bdir, "manifest.json"), "w") as fh:
            json.dump({"files": [{"path": "data/descr_strat.txt", "was": "x"}], "editor": "9.9"}, fh)
        self.assertIn(bdir, backups(mod))
        self.assertTrue(backup_label(bdir).startswith("2099-12-31 23:59:59"))
        def snap():
            out = {}
            for dp, _, fs in os.walk(mod.data):
                for n in fs:
                    with open(os.path.join(dp, n), "rb") as fh:
                        out[os.path.join(dp, n)] = fh.read()
            return out
        before = snap()
        with self.assertRaises(ValueError) as ctx:
            restore(mod, bdir)
        self.assertIn("another version", str(ctx.exception))
        self.assertTrue(os.path.isdir(bdir))
        self.assertEqual(before, snap())
        from campaign_editor.plan import restore_to
        with self.assertRaises(ValueError):           # undo back to an older one: refused before anything changes
            restore_to(mod, backups(mod)[-1])
        self.assertEqual(before, snap())
        with open(os.path.join(bdir, "manifest.json"), "w") as fh:
            json.dump([1, 2], fh)
        self.assertTrue(backup_label(bdir).startswith("2099-12-31"))
        # the mod folder's mark
        with open(os.path.join(root, newmod.MARKER), "w") as fh:
            json.dump(["base", "(game)"], fh)
        self.assertIsNone(newmod.marker(root))
        self.assertEqual(newmod.slim(mod.data), 0)
        # a Module builder module from a newer version
        future = MB.new_recipe("From the future")
        future.update(v=99, when="ev:SomethingNew", ifs=[{"k": "future_cond", "x": 1}],
                      dos=[{"k": "future_act", "y": [1, 2]}], settings={"dos.0.y": "Y"})
        text = "// @title From the future\n// @recipe %s\nlocal MB_ON = true\n" % json.dumps(future)
        lib = os.path.join(self.root, "lib")
        os.makedirs(lib)
        with open(os.path.join(lib, "from_the_future.nut"), "w") as fh:
            fh.write(text)
        with mock.patch.object(AD, "library_dir", return_value=lib):
            mine = MB.my_modules()
        self.assertEqual([r["title"] for _, r in mine], ["From the future"])
        bad = MB.problems(mine[0][1])
        self.assertTrue(any("unknown (future_cond)" in x for x in bad) and any("unknown (future_act)" in x for x in bad))
        self.assertIn("future_act", MB.plain_words(mine[0][1]))
        with self.assertRaises(ValueError):
            MB.script(mine[0][1])
        # reports seen in another form
        answers = {"R-1": {"state": "open", "messages": [{"from": "author", "text": "hi"}]}}
        self.assertEqual(report.news(answers, {"R-1": 3}), ["R-1"])
        self.assertEqual(report.news(answers, {"R-1": {"n": "two"}}), ["R-1"])

    def test_every_value_of_a_unit_line_is_explained(self):
        """A modder: 'we can edit every line but do not know what those numbers with commas mean'. edufields names
        each value of a unit's line (both games, the games' own notes), for what is typed there now."""
        from campaign_editor import edufields as EF
        rome = EF.explain("stat_pri", "13, 3, pilum, 35, 2, thrown, blade, piercing, spear, 25 ,1")
        self.assertIn("2. charge bonus = 3", rome)
        self.assertIn("3. missile = pilum", rome)
        self.assertIn("10. attack delay = 25", rome)
        m2 = EF.explain("stat_pri", "9, 3, arrow, 120, 30, missile, missile_mechanical, piercing, none, "
                                    "musket_shot_set, 25, 1", True)
        self.assertIn("10. fire effect = musket_shot_set", m2)                 # Medieval II's optional effect
        self.assertIn("11. attack delay = 25", m2)
        self.assertEqual(EF.explain("stat_sec", "no"), "stat_sec: no weapon.")
        cost = EF.explain("stat_cost", "1, 520, 150, 100, 120, 0, 4, 130", True)
        self.assertIn("7. custom battle: units = 4", cost)
        words = EF.explain("stat_pri_attr", "prec, thrown ap")                 # Rome's own file: a space too
        self.assertIn("- ap: armour piercing", words)
        mental = EF.explain("stat_mental", "8, normal, trained, lock_morale, expendable", True)
        self.assertIn("- lock_morale: never routs", mental)
        self.assertIn("- expendable:", mental)                                  # REX / M2EX's own word
        engine = EF.explain("attributes", "sea_faring, stun_immune, unstoppable, is_knockdown_immune, hardy_40")
        self.assertIn("- stun_immune: is never knocked back", engine)            # words REX.exe / M2EX.exe read
        self.assertIn("- hardy_40: tires more slowly: 40 fatigue points", engine)
        self.assertIn("- hp_damage_3: each hit takes 3 hit points", EF.explain("stat_pri_attr", "ap, hp_damage_3"))
        self.assertIsNone(EF.explain("no_such_line", "1"))
        # every line of every unit in a mod: a meaning for each value, none left unnamed
        mod = ModData(self.root)
        from campaign_editor import editors as E
        f = mod.load(mod.file("edu"))
        for name, a, b in E.unit_blocks(f):
            for fd in E.fields(f, a, b):
                text = EF.explain(fd.key, fd.value)
                self.assertIsNotNone(text, fd.key)
                self.assertNotIn("do not name", text, (fd.key, fd.value))

    def test_signs_letters_stand_out_on_any_colour(self):
        """A letter or picture on a coloured sign (a town's hall, an agent's sign, a resource's letters, a colour
        button): black on a bright colour, white on a dark one - Egypt's white disc hid its agents' white signs."""
        try:
            from campaign_editor import theme
        except ImportError as e:
            self.skipTest("no tkinter: %s" % e)
        for fill, want in (("#ffffff", "black"), ((255, 255, 128), "black"), ("#f2c200", "black"),
                           ("#5a5f66", "white"), ((30, 30, 30), "white"), ((200, 40, 40), "white")):
            self.assertEqual(theme.on_colour(fill), want, fill)
            ink = (0, 0, 0) if want == "black" else (255, 255, 255)
            rgb = fill if isinstance(fill, tuple) else tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
            self.assertGreaterEqual(theme.contrast(rgb, ink), 4.5)

    def test_text_is_readable_on_its_ground_in_either_look(self):
        """The dark look showed light text on the Module builder's light IF block, dark red / dark blue on its dark
        grey: theme.readable makes any text colour readable (4.5:1) on the ground it stands on, keeping its hue."""
        try:
            from campaign_editor import theme
        except ImportError as e:                      # a Python without tkinter: the window's look is not here
            self.skipTest("no tkinter: %s" % e)
        rgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        dark_grey, cream = rgb(theme.DARK["bg"]), rgb("#f7efd6")
        for text, ground in (("#bb0000", dark_grey), ("#1d3b6a", dark_grey), ("#e3e3e3", cream),
                             ("#a9adb3", cream), ("#000000", rgb("#233c69")), ("#999999", (255, 255, 255))):
            fixed = theme.readable(rgb(text), ground)
            self.assertIsNotNone(fixed, text)
            self.assertGreaterEqual(theme.contrast(rgb(fixed), ground), theme.READABLE, (text, fixed))
        red = rgb(theme.readable(rgb("#bb0000"), dark_grey))
        self.assertTrue(red[0] > red[1] and red[0] > red[2])            # still red, only lighter
        self.assertIsNone(theme.readable(rgb(theme.DARK["fg"]), dark_grey))     # what reads stays as it is
        self.assertIsNone(theme.readable(rgb(theme.LIGHT["fg"]), cream))
        self.assertEqual(theme.ink("#b00"), "#b00")                     # no window yet: the colour as given

    def test_the_editor_checks_itself(self):
        """`campaign_editor.py selfcheck` (CI runs it on the built exe): modules, bundled files, the tiny mod."""
        from campaign_editor import selfcheck
        good, lines = selfcheck.run(window=False)
        self.assertTrue(good, "\n".join(lines))
        self.assertTrue(lines[-1].startswith("SELF-CHECK PASSED"))
        self.assertTrue(any("the engines' catalogue" in l for l in lines))
        self.assertTrue(any("Restore puts every byte back" in l for l in lines))
        out = os.path.join(self.root, "selfcheck.txt")
        from io import StringIO
        old, sys.stdout = sys.stdout, StringIO()
        try:
            code = selfcheck.main(out)                      # tkinter as this Python has it (CI: yes, Pillow: no)
        finally:
            sys.stdout = old
        with open(out, encoding="utf-8") as fh:
            report_text = fh.read()
        self.assertEqual(code, 0, report_text)
        self.assertIn("SELF-CHECK PASSED", report_text)
        self.assertIn("icons", report_text)

    def test_a_mod_with_only_its_changed_files_is_explained(self):
        """REX -mod: and Medieval II mods/<name> may hold only the files they change (the game reads the rest from
        its own data): Load says so in plain words and what to do, instead of 'no descr_sm_factions.txt'."""
        from campaign_editor.moddata import find_data_dir
        for thin in (os.path.join(self.root, "Thin", "data"), os.path.join(self.root, "mods", "thin", "data")):
            os.makedirs(os.path.join(thin, "text"))
            with self.assertRaises(FileNotFoundError) as e:
                ModData(os.path.dirname(thin))
            self.assertIn("holds only the files this mod changes", str(e.exception))
            self.assertIn(os.path.join(self.root, "data"), str(e.exception))
        empty = os.path.join(self.root, "Empty")
        os.makedirs(empty)
        with self.assertRaises(FileNotFoundError) as e:
            find_data_dir(empty)
        self.assertIn("no descr_sm_factions.txt", str(e.exception))

    def test_older_versions_files_beside_a_mod_still_work(self):
        """A new version put over an old one: the older names beside a mod are still read - the ignore list, the
        mod folder's mark, the backups - and take today's names when they are written again."""
        from campaign_editor import scan as SC
        from campaign_editor import newmod as NM
        root = tempfile.mkdtemp()
        write(os.path.join(root, "faction_tool_ignore.txt"), "junk/\n")
        self.assertTrue(SC.ignore_path(root).endswith("faction_tool_ignore.txt"))
        self.assertIn("junk", repr(SC.load_ignore(root)))
        SC.save_ignore(root, "junk/\nold_stuff/")
        self.assertEqual(sorted(os.listdir(root)), ["CampaignEditor_ignore.txt"])
        self.assertIn("old_stuff", repr(SC.load_ignore(root)))
        with open(os.path.join(root, "faction_tool_mod.json"), "w") as fh:
            fh.write('{"base": "HLR"}')
        self.assertEqual(NM.marker(root), {"base": "HLR"})
        self.assertEqual(sorted(os.listdir(root)), ["CampaignEditor_ignore.txt", "CampaignEditor_mod.json"])
        self.assertEqual(NM.marker(root), {"base": "HLR"})

    def test_portrait_library_add_m2_layout(self):
        """Medieval II's pools (vanilla southern_european): no cards, old only for generals, the dead
        princesses in portraits/dead/princesses - a new princess gets young + dead there, nothing more."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import portraits as PL
        from campaign_editor.plan import Plan
        base = os.path.join(self.root, "data", "ui", "eastern", "portraits", "portraits")
        for folder in (("young", "generals"), ("old", "generals"), ("dead",), ("young", "princesses"),
                       ("dead", "princesses")):
            d = os.path.join(base, *folder)
            os.makedirs(d)
            for n in (0, 1, 2):
                Image.new("RGBA", (69, 96), (9, 9, 9, 255)).save(os.path.join(d, "%03d.tga" % n))
        src = os.path.join(self.root, "face.png")
        Image.new("RGB", (200, 300), (250, 0, 0)).save(src)
        mod = ModData(self.root)
        lib = PL.library(mod, "eastern")
        self.assertEqual(len(lib["princesses"]["dead"]), 3)
        self.assertEqual((lib["generals"]["cards"], len(lib["generals"]["dead"])), ({}, 3))
        plan = Plan(mod, "characters", "characters")
        self.assertEqual(PL.add(plan, "eastern", "princesses", [{"young": src}]), [3])
        self.assertEqual(sorted(os.path.relpath(p, base).replace("\\", "/") for p in plan.binaries),
                         ["dead/princesses/003.tga", "young/princesses/003.tga"])

    def test_descr_regions_with_an_odd_entry(self):
        """BI's descr_regions.txt has an entry with a line more before the colour ('Pictii' where the
        colour was read - every map read failed). The colour line anchors the entry; writers use the same."""
        from campaign_editor.moddata import region_entries
        from campaign_editor.plan import Plan
        from campaign_editor.regionedit import edit_regions
        path = os.path.join(self.root, "data", "world", "maps", "campaign", "test", "descr_regions.txt")
        with open(path) as fh:
            text = fh.read()
        with open(path, "w") as fh:
            fh.write(text.replace("B_R\n\tBtown\n\tslave\n\tRebels\n", "B_R\n\tBtown\n\tslave\n\tPictii\n\tRebels\n", 1))
        mod = ModData(self.root)
        r = mod.regions("test")["B_R"]
        self.assertEqual((r["colour"], r["rebels"], r["creator"], r["triumph"]), ((0, 0, 255), "Rebels", "slave", "5"))
        plan = Plan(mod, "x", "x")
        edit_regions(plan, "test", {"B_R": {"farming": "4", "rebels": "Picts"}})
        lines = plan.files[path].texts()
        e = region_entries(plan.files[path])["B_R"]
        self.assertEqual((lines[e["farming"][0]], lines[e["rebels"][0]]), ("\t4", "\tPicts"))
        self.assertIn("\tPictii", lines)

    def test_rename_region_and_town_shown_names(self):
        """Edit region renames what players see: the region's and its town's {key} lines of the campaign's names
        text get the new text (the key and the gap stay), a missing key is added; the file names stay; Restore
        gives the file back byte for byte; a name with { } is refused."""
        from campaign_editor.plan import Plan, restore
        from campaign_editor.regionedit import edit_regions, shown_labels
        mod = ModData(self.root)
        path = mod.region_labels_file("test")
        with open(path, "rb") as fh:
            before = fh.read()
        self.assertEqual(shown_labels(mod, "test", ["alpha", "Atown"]), {"alpha": "Alpha region"})
        plan = Plan(mod, "x", "x")
        edit_regions(plan, "test", {"A_R": {"label": "Latium Novum", "settlement_label": "Roma Nova"}})
        texts = plan.files[path].texts()
        self.assertIn("{Alpha}\t\tAlpha region", texts)                 # another key untouched
        self.assertIn("{A_R}\t\t\tLatium Novum", texts)                  # added: the file had no {A_R}
        self.assertIn("{Atown}\t\t\tRoma Nova", texts)
        self.assertNotIn(mod.campaign_file("test", "descr_regions.txt"), plan.files)   # nothing else asked
        bdir = plan.apply()
        mod2 = ModData(self.root)
        self.assertEqual(shown_labels(mod2, "test", ["A_R", "Atown"]), {"A_R": "Latium Novum", "Atown": "Roma Nova"})
        plan = Plan(mod2, "x", "x")
        edit_regions(plan, "test", {"A_R": {"label": "Latium"}})          # an existing key: its text replaced
        self.assertIn("{A_R}\t\t\tLatium", plan.files[path].texts())
        with self.assertRaises(ValueError):
            edit_regions(Plan(mod2, "x", "x"), "test", {"A_R": {"label": "bad {name}"}})
        restore(mod2, bdir)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), before)

    def test_rename_region_in_the_files(self):
        """Settlements > Rename in the files: the region and its town renamed as whole words in every text file of
        the mod (descr_regions, descr_strat, win conditions, scripts), the {keys} of the names texts; comments,
        a word inside a longer name, a line naming a faction and a campaign with its own map keep theirs; taken
        or bad names refused; Restore byte for byte."""
        from campaign_editor.plan import Plan, restore
        from campaign_editor.regionrename import problems, rename
        d = os.path.join(self.root, "data")
        camp = os.path.join(d, "world", "maps", "campaign", "test")
        write(os.path.join(camp, "campaign_script.txt"),
              "script\n; A_R is Alpha's heart\nmonitor_event SettlementTurnStart SettlementName Atown\n"
              "\tand FactionType Atown\n\tconsole_command reveal_tile A_R_2\nend_monitor\nend_script\n")
        other = os.path.join(d, "world", "maps", "campaign", "prologue")
        write(os.path.join(other, "descr_regions.txt"), REGIONS)
        write(os.path.join(other, "descr_strat.txt"), STRAT)
        write(os.path.join(d, "text", "test_regions_and_settlement_names.txt"),
              "{A_R}\t\tAlpha land\n{Atown}\t\tAlpha town\n", utf16=True)
        # people named like the place (vanilla Rome: the woman Apollonia, surnames 'of Epirus') keep their names
        write(os.path.join(d, "descr_names.txt"), "faction: alpha\n\tcharacters\n\t\tAtown\n\tsurnames\n\t\tof Atown\n")
        write(os.path.join(d, "descr_names_lookup.txt"), "Atown\n")
        write(os.path.join(d, "text", "names.txt"), "{Atown}\tAtown\n", utf16=True)
        write(os.path.join(camp, "descr_strat.txt"), STRAT + "\ncharacter\tAtown of Atown, named character, male, "
              "age 30, x 1, y 1\ncharacter_record\t\tAtown, \tfemale, age 20, alive, never_a_leader\n")
        before = tree_hash(d)
        mod = ModData(self.root)
        self.assertTrue(problems(mod, "test", "A_R", "B_R", "Newtown"))            # taken by another region
        self.assertTrue(problems(mod, "test", "A_R", "New R", "Newtown"))          # a space
        self.assertTrue(problems(mod, "test", "A_R", "Same", "Same"))
        plan = Plan(mod, "rename", "New_R")
        counts = rename(plan, "test", "A_R", "New_R", "Newtown")
        self.assertEqual(set(counts), {"A_R", "Atown"})
        script = plan.files[os.path.join(camp, "campaign_script.txt")].texts()
        self.assertIn("; A_R is Alpha's heart", script)                            # a comment keeps its words
        self.assertIn("monitor_event SettlementTurnStart SettlementName Newtown", script)
        self.assertIn("\tand FactionType Atown", script)                           # a faction's name stays
        self.assertIn("\tconsole_command reveal_tile A_R_2", script)               # part of a longer name
        strat = plan.files[os.path.join(camp, "descr_strat.txt")].texts()
        self.assertIn("\tregion New_R", strat)
        self.assertIn("character\tAtown of Atown, named character, male, age 30, x 1, y 1", strat)
        self.assertIn("character_record\t\tAtown, \tfemale, age 20, alive, never_a_leader", strat)
        for n in ("descr_names.txt", "descr_names_lookup.txt", os.path.join("text", "names.txt")):
            self.assertNotIn(os.path.join(d, n), plan.files, n)
        self.assertIn("hold_regions New_R", plan.files[os.path.join(camp, "descr_win_conditions.txt")].texts())
        regions = plan.files[os.path.join(camp, "descr_regions.txt")].texts()
        self.assertEqual(regions[:2], ["New_R", "\tNewtown"])
        names = plan.files[os.path.join(d, "text", "test_regions_and_settlement_names.txt")].texts()
        self.assertEqual(names[:2], ["{New_R}\t\tAlpha land", "{Newtown}\t\tAlpha town"])   # keys only
        self.assertFalse(any(p.startswith(other) for p in plan.files))              # a map of its own: untouched
        bdir = plan.apply()
        self.assertIn("New_R", ModData(self.root).regions("test"))
        restore(ModData(self.root), bdir)
        self.assertEqual(tree_hash(d), before)

    def test_terrain_paint_and_restore(self):
        """Terrain editor: a tile's ground is the 3 x 3 block around (2x + 1, 2y + 1) of map_ground_types.tga,
        features one pixel per tile; land stays land, nothing refused under a town; map.rwm goes; Restore."""
        from campaign_editor import terrain as T
        from campaign_editor.plan import Plan
        from campaign_editor.tga import read_tga
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        wild, sea = (0, 0, 0), (64, 0, 0)
        write_tga(os.path.join(camp, "map_ground_types.tga"), 9, 9,
                  [[sea if x >= 7 else wild for x in range(9)] for y in range(9)])
        write_tga(os.path.join(camp, "map_features.tga"), 4, 4, [[wild] * 4 for _ in range(4)])
        write_tga(os.path.join(camp, "map_climates.tga"), 9, 9, [[(236, 0, 140)] * 9 for _ in range(9)])
        write(os.path.join(self.root, "data", "descr_climates.txt"),
              "climates\n{\n\ttest_climate\n\tsandy_desert\n}\n\nclimate test_climate\n{\n\tcolour 236 0 140\n"
              "\theat 1\n}\n\n;climate old_one\n;{\n;\tcolour 1 2 3\n;}\nclimate sandy_desert\n{\n\tcolour 102 45 145\n"
              "\theat 4\n}\n")
        write(os.path.join(camp, "map.rwm"), "x")
        before = tree_hash(self.root)
        mod = ModData(self.root)

        class Map:                                        # what paint_problem asks of the map
            w = h = 4

            def is_sea(self, x, y):
                return x == 3
        self.assertIsNone(T.paint_problem(Map(), "ground", (0, 0), (128, 128, 64), set()))
        self.assertTrue(T.paint_problem(Map(), "ground", (3, 0), (128, 128, 64), set()))        # sea stays sea
        self.assertTrue(T.paint_problem(Map(), "ground", (1, 1), (98, 65, 65), {(1, 1)}))       # no mountains under a town
        self.assertTrue(T.paint_problem(Map(), "features", (1, 1), (0, 0, 255), {(1, 1)}))
        self.assertEqual(T.river_warnings({(0, 0): (0, 0, 255), (0, 1): (0, 255, 255), (2, 2): (0, 0, 255)}, 4, 4),
                         [(2, 2, 1)])
        plan = Plan(mod, "terrain", "terrain")
        self.assertEqual(T.climates(mod), [("test_climate", (236, 0, 140), 1), ("sandy_desert", (102, 45, 145), 4)])
        self.assertTrue(T.paint_problem(Map(), "climate", (3, 0), (102, 45, 145), set()))    # the sea keeps its own
        self.assertIsNone(T.paint_problem(Map(), "climate", (1, 1), (102, 45, 145), {(1, 1)}))
        T.apply(plan, "test", {(1, 2): (128, 128, 64)}, {(0, 0): (0, 0, 255)}, {(2, 1): (102, 45, 145)})
        self.assertTrue(any("1 sandy_desert" in n for _, n in plan.notes))
        plan.apply()
        c = read_tga(os.path.join(camp, "map_climates.tga"))
        self.assertEqual({c.get(x, y) for x in (4, 5, 6) for y in (2, 3, 4)}, {(102, 45, 145)})
        self.assertEqual(c.get(3, 3), (236, 0, 140))
        g = read_tga(os.path.join(camp, "map_ground_types.tga"))
        self.assertEqual({g.get(x, y) for x in (2, 3, 4) for y in (4, 5, 6)}, {(128, 128, 64)})
        self.assertEqual(g.get(1, 5), wild)
        self.assertEqual(read_tga(os.path.join(camp, "map_features.tga")).get(0, 0), (0, 0, 255))
        self.assertFalse(os.path.exists(os.path.join(camp, "map.rwm")))
        mod = ModData(self.root)
        restore(mod, backups(mod)[0])
        after = tree_hash(self.root)
        self.assertEqual({k: v for k, v in after.items() if "_backups" not in k}, before)

    def test_coast_brush_land_and_sea(self):
        """The land / sea brush: a sea tile made land joins the nearest region and gets a land ground and a low
        shore in the heights (and in map_heights.hgt); a land tile made sea gets the sea's colour, shallow sea and a
        depth; a town, a region's last land and a river are refused; Restore gives every file back."""
        try:
            import PIL  # noqa: F401 - the campaign map module draws with Pillow (the exe has it)
        except ImportError:
            self.skipTest("Pillow is not installed")
        import struct
        from campaign_editor import terrain as T
        from campaign_editor.mapdata import CampaignMap
        from campaign_editor.plan import Plan
        from campaign_editor.tga import read_tga
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        red, blue, black, sea = (255, 0, 0), (0, 0, 255), (0, 0, 0), (41, 140, 233)
        write_tga(os.path.join(camp, "map_regions.tga"), 4, 4, [[red, red, blue, sea], [red, black, blue, sea],
                                                                 [red, red, black, sea], [red, red, blue, sea]])
        green, shallow, ocean = (96, 160, 64), (196, 0, 0), (64, 0, 0)
        write_tga(os.path.join(camp, "map_ground_types.tga"), 9, 9,
                  [[(ocean if y >= 3 else shallow) if x >= 6 else green for x in range(9)] for y in range(9)])
        write_tga(os.path.join(camp, "map_heights.tga"), 9, 9,
                  [[(0, 0, 250) if x >= 6 else (20, 20, 20) for x in range(9)] for y in range(9)])
        with open(os.path.join(camp, "map_heights.hgt"), "wb") as fh:
            fh.write(struct.pack("<II", 9, 9) + struct.pack("<81f", *[(-30.0 if x >= 6 else 589.0)
                                                                     for y in range(9) for x in range(9)]))
        write_tga(os.path.join(camp, "map_features.tga"), 4, 4, [[black, black, black, black],
                                                                  [black, black, black, black],
                                                                  [black, black, black, black],
                                                                  [(0, 0, 255), black, black, black]])
        before = tree_hash(self.root)
        mod = ModData(self.root)
        cmap = CampaignMap(mod, "test")
        standing = set(cmap.cities.values()) | {(1, 1)}
        counts = {"A_R": 8, "B_R": 3}
        self.assertIsNone(T.coast_problem(cmap, (3, 0), True, standing, {}, counts, {}))
        self.assertIn("stands there", T.coast_problem(cmap, (1, 1), False, standing, {}, counts, {}))
        self.assertIn("last land", T.coast_problem(cmap, (2, 0), False, standing, {}, {"B_R": 1}, {}))
        self.assertIn("rub it out", T.coast_problem(cmap, (0, 3), False, standing, {(0, 3): (0, 0, 255)}, counts, {}))
        self.assertEqual(T.nearest_region(cmap, (3, 0)), "B_R")
        class Pic:                                # an open sea with a 5 x 5 pixel island at shore height
            width = height = 11

            def get(self, x, y):
                return (2, 2, 2) if 3 <= x <= 7 and 3 <= y <= 7 else (0, 0, 253)
        rise = T.shore_rise(Pic(), [(x, y) for x in range(3, 8) for y in range(3, 8)])
        self.assertNotIn((3, 5), rise)                                  # the shore stays low
        self.assertEqual(rise[(4, 5)], (8, 8, 8))                       # one in: like vanilla's coasts
        self.assertEqual(rise[(5, 5)], (12, 12, 12))                    # the middle higher - no flat island
        imp = (64, 64, 64)                       # impassable land: Medieval II, Rome only with REX
        self.assertIn(imp, T.ground_brushes("medieval2")[0])
        self.assertIn(imp, T.ground_brushes("rome", "REX.exe")[0])
        self.assertNotIn(imp, T.ground_brushes("rome")[0])
        reg = mod.region_map("test")
        self.assertEqual(T.sea_colour(reg, [red, blue]), sea)
        heights = mod._optional_map("test", "map_heights.tga")
        land = T.coast_pixels(cmap, (3, 0), True, blue, heights, sea)
        water = T.coast_pixels(cmap, (0, 0), False, None, heights, sea)
        self.assertEqual(land["regions"], {(3, 0): blue})
        self.assertEqual(land["ground"][(7, 1)], green)                      # like its land neighbours
        self.assertEqual((land["ground"][(7, 3)], land["ground"][(7, 4)]), (shallow, shallow))  # shallows round it
        self.assertNotIn((7, 5), land["ground"])                                # the next tile down stays ocean
        self.assertNotIn((4, 3), land["ground"])                                # land round it untouched
        self.assertTrue(all(c[0] == c[1] == c[2] and c[0] >= 1 for c in land["heights"].values()))
        self.assertEqual(water["ground"][(1, 1)], shallow)
        self.assertTrue(all(c[0] == 0 and c[2] > 0 for c in water["heights"].values()))
        coast = {"tiles": {(3, 0): "land", (0, 0): "sea"}, "regions": {}, "ground": {}, "heights": {}}
        for px in (land, water):
            for k in ("regions", "ground", "heights"):
                coast[k].update(px[k])
        plan = Plan(ModData(self.root), "terrain", "terrain")
        T.apply(plan, "test", coast=coast)
        plan.apply()
        m2 = ModData(self.root)
        r = read_tga(os.path.join(camp, "map_regions.tga"))
        self.assertEqual((r.get(3, 0), r.get(0, 0)), (blue, sea))
        g = read_tga(os.path.join(camp, "map_ground_types.tga"))
        self.assertEqual((g.get(7, 1), g.get(1, 1)), (green, shallow))
        self.assertTrue(CampaignMap(m2, "test").is_sea(0, 0))
        self.assertFalse(CampaignMap(m2, "test").is_sea(3, 0))
        with open(os.path.join(camp, "map_heights.hgt"), "rb") as fh:
            floats = struct.unpack("<81f", fh.read()[8:])
        h = read_tga(os.path.join(camp, "map_heights.tga"))
        self.assertAlmostEqual(floats[1 * 9 + 7], h.get(7, 1)[0] * 7511.272 / 255, 2)   # new land: grey x step
        self.assertLess(floats[1 * 9 + 1], 0)                                          # new sea: below 0
        mod = ModData(self.root)
        restore(mod, backups(mod)[0])
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if "_backups" not in k}, before)

    def test_heights_spray_and_restore(self):
        """Heights brush: a spray on land raises the middle most, never touches the sea (blue), puffs add up;
        written into map_heights.tga, map_heights.hgt (the game's copy that wins over the picture) and map.rwm
        deleted; Restore gives every file back."""
        from campaign_editor import terrain as T
        from campaign_editor.plan import Plan
        from campaign_editor.tga import read_tga
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        land, sea = (10, 10, 10), (0, 0, 253)
        write_tga(os.path.join(camp, "map_heights.tga"), 9, 9,
                  [[sea if x >= 7 else land for x in range(9)] for y in range(9)])
        import struct
        hgt_path = os.path.join(camp, "map_heights.hgt")
        with open(hgt_path, "wb") as fh:                   # the game's copy: w, h, then floats bottom-up
            fh.write(struct.pack("<II", 9, 9) + struct.pack("<81f", *([300.0] * 81)))
        write(os.path.join(camp, "map.rwm"), "x")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        img = mod._optional_map("test", "map_heights.tga")
        vals = {}
        first = T.height_spray(img, (5.0, 4.0), 3, "raise", 10, vals)
        self.assertTrue(first)
        self.assertTrue(all(x < 7 for x, _ in first))                        # the sea is left alone
        self.assertEqual(max(first, key=first.get), (5, 4))                  # the middle gets the most
        for p, v in first.items():
            img.pixels[p[1] * img.width + p[0]] = (v, v, v)
        second = T.height_spray(img, (5.0, 4.0), 3, "raise", 10, vals)
        self.assertGreater(second[(5, 4)], first[(5, 4)])                    # held longer, higher
        weak = T.height_spray(img, (1.0, 1.0), 3, "lower", 1, {})
        self.assertTrue(all(v <= 10 for v in weak.values()))
        low = {}
        for _ in range(40):                                                  # held long: never down to black
            T.height_spray(img, (1.0, 1.0), 3, "lower", 10, low)
        self.assertEqual(min(low.values()), 1.0)
        heights = dict(first)
        heights.update(second)
        with self.assertRaises(ValueError):                                  # never the sea
            T.apply(Plan(ModData(self.root), "terrain", "terrain"), "test", heights={(8, 8): 50})
        mod = ModData(self.root)
        plan = Plan(mod, "terrain", "terrain")
        T.apply(plan, "test", heights=heights)
        self.assertTrue(any("raised" in n for _, n in plan.notes))
        plan.apply()
        h = read_tga(os.path.join(camp, "map_heights.tga"))
        self.assertEqual(h.get(5, 4)[0], second[(5, 4)])
        self.assertEqual(h.get(8, 4), sea)
        with open(hgt_path, "rb") as fh:                   # kept, the same pixels moved by the grey step
            floats = struct.unpack("<81f", fh.read()[8:])
        self.assertAlmostEqual(floats[4 * 9 + 5], 300.0 + (second[(5, 4)] - 10) * 7511.272 / 255, places=2)
        self.assertEqual(floats[0], 300.0)
        self.assertFalse(os.path.exists(os.path.join(camp, "map.rwm")))
        mod = ModData(self.root)
        restore(mod, backups(mod)[0])
        after = tree_hash(self.root)
        self.assertEqual({k: v for k, v in after.items() if "_backups" not in k}, before)

    def test_family_tree_checks(self):
        from campaign_editor.family import ordered, tree_problems
        people = [{"name": n, "sex": s} for n, s in (("A", "male"), ("B", "female"), ("C", "male"), ("D", "female"),
                                                     ("E", "male"))]
        self.assertEqual(tree_problems([["A", "B", ["C"]], ["C", "D", ["E"]]], people), [])
        self.assertTrue(tree_problems([["B", "A", []]], people))                     # a woman heads a couple
        self.assertTrue(tree_problems([["A", "B", ["C"]], ["E", "D", ["C"]]], people))  # two sets of parents
        self.assertTrue(tree_problems([["A", "B", ["X"]]], people))                  # nobody of the faction
        self.assertEqual(ordered([["C", "D", ["E"]], ["A", "B", ["C"]]])[0][0], "A")  # parents first

    def test_existing_armies_changed_and_removed(self):
        from campaign_editor.edit import edit
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
        from campaign_editor.edit import edit
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
        from campaign_editor.edit import edit
        from campaign_editor.tga import read_tga
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
        after = {k: v for k, v in tree_hash(self.root).items() if "_backups" not in k}
        self.assertEqual(after, before)

    def test_old_culture_names_module_moves_into_the_script(self):
        # an early 0.12 build wrote script/modules/ft_settlement_names.nut (the user's HLR, 2026-09-29)
        from campaign_editor import gamefix, culturenames as CN
        game, hlr = self._game()
        write(os.path.join(hlr, "data", "descr_cultures.txt"), "culture roman\n{\n}\nculture barbarian\n{\n}\n")
        old = os.path.join(hlr, "script", "modules", "ft_settlement_names.nut")
        write(old, '// generated\n// DATA {"Atown": {"barbarian": "Atburg"}}\nlocal x = 1;\n')
        before = tree_hash(hlr)
        mod = ModData(hlr)
        found = [p for p in gamefix.problems(mod) if p["id"] == "old_culture_names"]
        self.assertEqual(found[0]["table"], {"Atown": {"barbarian": "Atburg"}})
        gamefix.fix_plan(mod, found).apply()
        self.assertFalse(os.path.exists(old))
        self.assertEqual(CN.read(ModData(hlr), "test"), {"Atown": {"barbarian": "Atburg"}})
        restore_to(ModData(hlr), backups(ModData(hlr))[-1])
        self.assertEqual({k: v for k, v in tree_hash(hlr).items() if "_backups" not in k}, before)

    def test_army_on_the_new_town_tile_steps_aside(self):
        # the user's HLR run: taking Odessus sent its garrison out onto the tile he then moved the town to -
        # "Philokles's army stands on 257, 254 - move it first" blocked the Apply
        from campaign_editor.edit import edit
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        with open(path) as fh:
            text = fh.read()
        with open(path, "w") as fh:
            fh.write(text.replace("Grog, general, age 30, , x 2, y 2", "Grog, general, age 30, , x 0, y 2"))
        plan = edit(ModData(self.root), "test", "alpha", {"places": [{"what": "city", "region": "A_R", "to": (0, 2)}]})
        s = Strat(plan.files[path])
        grog = next(c for c in s.faction("slave").characters if "Grog" in c.line)
        self.assertNotEqual(grog.xy, (0, 2))
        self.assertEqual(s.faction("alpha").characters[0].xy, (0, 2))
        self.assertTrue(any("steps aside" in n for _, n in plan.notes))

    def test_diplomacy_both_ways(self):
        from campaign_editor.edit import edit
        from campaign_editor.diplomacy import read
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        with open(path, "a") as fh:
            fh.write("core_attitudes\talpha,\t600\t\tslave\ncore_attitudes\tslave,\t600\t\talpha\n"
                     "faction_relationships\talpha,\t600\t\tslave\n")
        plan = edit(ModData(self.root), "test", "alpha", {"relations": [
            {"kind": "core_attitudes", "from": "me", "to": "slave", "value": 90},
            {"kind": "core_attitudes", "from": "slave", "to": "me", "value": None},
            {"kind": "faction_relationships", "from": "slave", "to": "me", "value": 310}]})
        rel = read(Strat(plan.files[path]))
        self.assertEqual(rel["core_attitudes"], {("alpha", "slave"): 90})
        self.assertEqual(rel["faction_relationships"], {("alpha", "slave"): 600, ("slave", "alpha"): 310})

    def test_diplomacy_alliances_wars_and_standings(self):
        """Both games: allied_to / at_war_with at the start (both ways), Medieval II's faction_standings floats,
        and a new faction neutral to all gets the rebels' lines the way the file's own factions have them."""
        from campaign_editor.diplomacy import kinds, read, rebels, set_relations
        from campaign_editor.textio import TextFile
        from campaign_editor.diplomacy import parse

        class P:
            def note(self, f, t):
                pass
        rome = ("; >>>> start of diplomacy section <<<<\r\n"
                "core_attitudes\talpha,\t600\t\tslave\r\n"
                "faction_relationships \talpha, at_war_with \tslave\r\n"
                "faction_relationships \tslave, at_war_with \talpha\r\n")
        m2 = ("character\tBob, named character, male, age 30, x 1, y 2\r\n"
              "; >>>> start of diplomacy section <<<<\r\n"
              "faction_standings\talpha,\t\t-0.45\tbeta\r\n"
              "faction_standings\talpha,\t\t-1.0\tslave\r\n"
              "faction_relationships \talpha, at_war_with \tslave\r\n"
              "faction_relationships \tslave, at_war_with \talpha\r\n")
        for text, feeling in ((rome, "core_attitudes"), (m2, "faction_standings")):
            path = os.path.join(self.root, "s.txt")
            with open(path, "wb") as fh:
                fh.write(text.encode())
            f = TextFile.load(path)
            s = Strat(f)
            self.assertEqual(kinds(s), (feeling, "faction_relationships"))
            set_relations(P(), f, "gamma", rebels(s, "gamma"))
            set_relations(P(), f, "gamma", {"faction_relationships": {("me", "alpha"): "allied_to",
                                                                      ("alpha", "me"): "allied_to"}})
            rel = read(Strat(f))
            self.assertEqual(rel["faction_relationships"][("gamma", "slave")], "at_war_with")
            self.assertEqual(rel["faction_relationships"][("slave", "gamma")], "at_war_with")
            self.assertEqual(rel["faction_relationships"][("gamma", "alpha")], "allied_to")
            self.assertEqual(rel["faction_relationships"][("alpha", "gamma")], "allied_to")
            body = "\n".join(f.text(i) for i in range(len(f.raw)))
            self.assertIn("faction_relationships\tgamma, allied_to\talpha", body)
            self.assertIn("slave, at_war_with\talpha, gamma", body)      # onto the rebels' own line
            if feeling == "faction_standings":
                self.assertEqual(rel["faction_standings"][("gamma", "slave")], -1.0)
                self.assertEqual(rel["faction_standings"][("alpha", "beta")], -0.45)
                self.assertIn("faction_standings\tgamma,\t-1.0\t\tslave", body)
                self.assertNotIn("600", body)
            else:
                self.assertEqual(rel["core_attitudes"][("gamma", "slave")], 600)
            self.assertTrue(f.raw[0].endswith(b"\r\n") if isinstance(f.raw[0], bytes) else True)
        self.assertEqual(parse("alliance", "faction_relationships"), "allied_to")
        self.assertEqual(parse("-0.45 dislike", "faction_standings"), -0.45)
        self.assertEqual(parse("310 wary"), 310)
        with self.assertRaises(ValueError):
            parse("war", "faction_standings")
        with self.assertRaises(ValueError):
            parse("2.0", "faction_standings")
        # the status pulls the AI feeling along (lower is better in Rome, higher in Medieval II)
        from campaign_editor.diplomacy import feeling_for
        self.assertEqual(feeling_for("core_attitudes", "allied_to", 310), 0)
        self.assertEqual(feeling_for("core_attitudes", "allied_to", -10), -10)
        self.assertEqual(feeling_for("core_attitudes", "at_war_with", 100), 600)
        self.assertEqual(feeling_for("faction_standings", "at_war_with", 0.2), -1.0)
        self.assertEqual(feeling_for("faction_standings", "allied_to", 0.8), 0.8)
        self.assertIsNone(feeling_for("faction_standings", None, -1.0))

    def test_victory_conditions(self):
        """descr_win_conditions.txt: a faction's block read and rewritten (Rome's outlive_factions on the next
        line kept), other blocks byte-exact, a missing region refused (the game crashes on it)."""
        from campaign_editor.edit import edit
        from campaign_editor import wincond
        mod = ModData(self.root)
        camp = os.path.dirname(mod.campaign_file("test", "descr_strat.txt"))
        path = os.path.join(camp, "descr_win_conditions.txt")
        text = ("alpha\r\ntake_rome \r\nshort_campaign outlive_factions\r\nslave\r\n\r\n"
                "beta\r\nhold_regions A_R\r\ntake_regions 2\r\n\r\n")
        with open(path, "wb") as fh:
            fh.write(text.encode())
        mod = ModData(self.root)
        got = wincond.read(mod, "test")
        self.assertEqual(got["alpha"]["long"]["goals"], ["take_rome"])
        self.assertEqual(got["alpha"]["short"]["outlive"], ["slave"])
        self.assertEqual(got["beta"]["long"]["hold"], ["A_R"])
        self.assertEqual(got["beta"]["long"]["take"], 2)
        cond = got["alpha"]
        cond["long"]["hold"] = ["A_R"]
        cond["short"]["take"] = 1
        plan = edit(mod, "test", "alpha", {"victory": cond})
        body = plan.files[path].raw
        out = "\n".join(body)
        self.assertIn("alpha\r\nhold_regions A_R\r\ntake_rome\r\nshort_campaign take_regions 1\r\n"
                      "outlive_factions\r\nslave\r\n\r\nbeta\r\nhold_regions A_R\r\ntake_regions 2\r\n", out)
        cond["long"]["hold"] = ["Nowhere"]
        with self.assertRaises(ValueError):
            edit(ModData(self.root), "test", "alpha", {"victory": cond})
        # unchanged conditions: the file is not touched
        plan = edit(ModData(self.root), "test", "alpha", {"victory": wincond.read(ModData(self.root), "test")["alpha"]})
        self.assertNotIn(path, list(plan.changed_files()))
        # a new faction: the template's block is copied, then the picks are written over the copy
        cond = wincond.read(ModData(self.root), "test")["alpha"]
        cond["long"]["goals"] = ["imperator"]
        plan = build(ModData(self.root), "test", "alpha", "beta", {
            "display_name": "Beta", "start": {"regions": ["B_R"], "leader": {"name": "Boris Alphid", "age": 35}},
            "victory": cond})
        f = plan.files[path]
        from campaign_editor.wincond import blocks, parse
        a, b = blocks(f)["beta"]
        got = parse([f.text(k) for k in range(a + 1, b)])
        self.assertEqual(got["long"]["goals"], ["imperator"])
        self.assertEqual(got["short"]["outlive"], ["slave"])
        a, b = blocks(f)["alpha"]
        self.assertEqual(f.text(a + 1).strip(), "take_rome")             # the template's own block untouched

    def test_check_mod_reads_the_mini_mod(self):
        from campaign_editor.check import check_mod
        text = check_mod(ModData(self.root), "test")
        self.assertIn("FACTIONS: 2 in descr_sm_factions.txt, 2 blocks", text)
        self.assertIn("No problems found", text)
        self.assertIn("LIMITS (the original Rome exe: no REX", text)
        self.assertIn("building chains", text)

    def test_check_mod_crash_rules_from_modders(self):
        """Win conditions naming a missing region or faction, a region without the 'slaves' the mod's
        others have (Rome), Medieval II rebels with units slave may not own - all crash the game."""
        from campaign_editor.check import check_mod, rebel_problems
        from campaign_editor.units import read_units
        mod = ModData(self.root)
        camp = os.path.dirname(mod.campaign_file("test", "descr_strat.txt"))
        write(os.path.join(camp, "descr_win_conditions.txt"), "alpha\nhold_regions A_R Nowhere\noutlive ghost\n")
        regions = mod.campaign_file("test", "descr_regions.txt")
        with open(regions) as fh:
            text = fh.read()
        with open(regions, "w") as fh:
            fh.write(text.replace("255 0 0\n\tnone", "255 0 0\n\tslaves, none", 1))
        text = check_mod(ModData(self.root), "test")
        self.assertIn("region 'Nowhere' does not exist", text)
        self.assertIn("faction 'ghost' does not exist", text)
        self.assertIn("lack the 'slaves' resource", text)
        self.assertNotIn("region 'A_R'", text)
        # Medieval II (descr_religions.txt): the rebels' units must be the slave faction's
        write(os.path.join(self.root, "data", "descr_religions.txt"), "religions\n{\n    catholic\n}\n")
        write(os.path.join(self.root, "data", "descr_rebel_factions.txt"),
              "rebel_type\tRebels\ncategory\tpeasant_revolt\nunit\trebel spear\nunit\talpha general\n")
        mod = ModData(self.root)
        got = rebel_problems(mod, read_units(mod.load(mod.file("edu"))))
        self.assertEqual(len(got), 1)
        self.assertIn("'alpha general' has no 'slave'", got[0])

    def test_bigger_map_names_only_scripts_that_place_things_by_tile(self):
        """x3 warns about Lua / Squirrel scripts it does not change - only those that put something on the map by
        tile number: not the engines' own interface (script/core, script/ui: screen places), not a colour, a comment
        or the add-ons that come with the editor."""
        from campaign_editor.upscale import code_names_tiles, code_with_tiles
        game = os.path.join(self.root, "game")
        write(os.path.join(game, "script", "ui", "campaign", "hud.nut"), "pane.setPosition(10, 20)\n"
              'runScriptCommand("move", "x 1, 2")\n')
        write(os.path.join(game, "script", "main.nut"), "character.teleport(1, 2)\n")
        write(os.path.join(game, "script", "modules", "colours.nut"),
              "local c = [255, 0, 0]\nlocal X = 0  // move the tick right, the game's 1024 x 768 screen\n")
        write(os.path.join(game, "script", "modules", "forts.nut"),
              'game.runConsoleCommand("create_fort", "120 85 romans_julii roman 0 1")\n')
        write(os.path.join(game, "script", "modules", "jump.nut"), "character.teleport(120, 85)\n")
        write(os.path.join(game, "eopData", "eopScripts", "a.lua"), "M2TWEOP.callConsole('move_character', 'G 1 2')\n")
        self.assertEqual(code_with_tiles(game), [("eopData/eopScripts", ["a.lua"]), ("script", ["forts.nut",
                                                                                               "jump.nut"])])
        self.assertTrue(code_names_tiles("local t = stratMap.getTile(120, 85)"))
        self.assertFalse(code_names_tiles("if (hostile(3, 4)) {}"))
        for name in os.listdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets",
                                            "addons")):
            shutil.copy(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "addons",
                                     name), os.path.join(game, "script", "modules", name))
        self.assertEqual(code_with_tiles(game)[1], ("script", ["forts.nut", "jump.nut"]))

    def test_bigger_map_rivers_stop_at_the_new_coast(self):
        """A river whose last tiles the smoother coast puts in the sea stops at the coast: none of it on the sea, its
        end touching the sea (a tester's DaC x3: land kept under such rivers stood off every mouth as a sandbar)."""
        from campaign_editor import upscale
        from campaign_editor.tga import read_tga
        river, black = (0, 0, 255), (0, 0, 0)
        px = [[black] * 4 for _ in range(4)]
        for x in range(4):
            px[1][x] = river                                  # a river along y 1, west to east
        path = os.path.join(self.root, "feat.tga")
        write_tga(path, 4, 4, px)
        land = upscale.Mask(12, 12)
        for X in range(12):
            for Y in range(12):
                land[(X, Y)] = X < 8                          # the new coast cuts the last tile and a bit
        data, drawn = upscale.features_scaled(path, land)
        with open(path, "wb") as fh:
            fh.write(data)
        f = read_tga(path)
        on = {(x, y) for x in range(12) for y in range(12) if f.get(x, y) != black}
        self.assertTrue(on and all(land[p] for p in on))                 # nothing on the sea
        self.assertEqual(on, drawn)
        self.assertEqual(max(x for x, y in on), 7)                      # the end on the last land, the sea beside it

    def test_bigger_map_natural_rivers(self):
        """x3 rivers drawn the natural way: a bend's point moves into the bend, a straight run swings a pixel to
        either side by the golden-ratio meander - and still one unbroken river (side by side only), as many ends as
        before, every pixel inside its old tiles' 3 x 3 blocks (a corner link: the one beside), a ford on the river, never two pixels wide (no 2 x 2
        square anywhere); the same map, the same river."""
        from campaign_editor import upscale
        river, ford, black = (0, 0, 255), (0, 255, 255), (0, 0, 0)
        n = 14
        px = [[black] * n for _ in range(n)]
        for x in range(1, 12):
            px[2][x] = river                                  # a long straight run west to east...
        for y in range(3, 9):
            px[y][11] = river                                 # ...a bend, south...
        for i in range(1, 5):
            px[8 + i][11 - i] = river                         # ...then a diagonal of corner links
        px[2][6] = ford
        path = os.path.join(self.root, "feat.tga")
        write_tga(path, n, n, px)
        old = {(x, y) for y in range(n) for x in range(n) if px[y][x] != black}
        _, plain = upscale.features_scaled(path)
        _, nat = upscale.features_scaled(path, natural=True)
        self.assertEqual(upscale.features_scaled(path, natural=True)[1], nat)            # the same each time
        self.assertNotEqual(nat, plain)
        for q in nat:                         # in its old tiles' blocks (a corner link: the block beside it too)
            bx, by = q[0] // 3, q[1] // 3
            self.assertTrue((bx, by) in old or any((bx + a, by) in old and (bx, by + b) in old
                                                   for a in (-1, 1) for b in (-1, 1)), q)
        seen, todo = {next(iter(nat))}, [next(iter(nat))]
        while todo:
            x, y = todo.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in nat and q not in seen:
                    seen.add(q)
                    todo.append(q)
        self.assertEqual(seen, nat)                                                     # one unbroken river

        def ends(px):
            return sum(1 for p in px if sum((p[0] + a, p[1] + b) in px for a, b in ((1, 0), (-1, 0), (0, 1),
                                                                                        (0, -1))) == 1)
        self.assertEqual(ends(nat), ends(plain))
        self.assertFalse([q for q in nat if (q[0] + 1, q[1]) in nat and (q[0], q[1] + 1) in nat and
                          (q[0] + 1, q[1] + 1) in nat])                               # never wider than one pixel
        bend = (11 * 3 + 1, 2 * 3 + 1)                                                  # the corner tile's middle
        self.assertNotIn(bend, nat)                                                     # cut, not a right angle

    def test_bigger_map_no_islands_in_a_navigable_river(self):
        """A tester's DaC x3 (Medieval II with M2EX): small islands inside a navigable river - a river map_regions
        calls the province's land and the heights call water, with a sea tile here and there. The smooth coast gave
        the 8 pixels round such a sea tile the province (land), and the heights followed map_regions there because
        the old tile agreed (sea in both): a ring of land rose in the water. Inside water all round the heights keep
        their own coast: no land there."""
        from campaign_editor import upscale
        P, S, LAND, WATER = (200, 40, 40), (41, 140, 233), (60, 60, 60), (0, 0, 120)
        regions = [[S if (x, y) == (2, 2) else P for x in range(5)] for y in range(5)]
        rpath = os.path.join(self.root, "regions.tga")
        write_tga(rpath, 5, 5, regions)
        heights = [[WATER if 3 <= x <= 7 else LAND for x in range(11)] for y in range(11)]   # tiles 1-3 water
        hpath = os.path.join(self.root, "heights.tga")
        write_tga(hpath, 11, 11, heights)
        info = {}
        upscale.regions_scaled(rpath, {P}, None, (), info)
        agree = upscale._agreement(rpath, hpath, {P})
        wet = upscale.heights_from_tiles(info["land"], agree, upscale.heights_mask(hpath))
        ring = [(2 * X + 1, 2 * Y + 1) for X in range(6, 9) for Y in range(6, 9)]     # the old sea tile's new 3 x 3
        self.assertTrue(all(wet[p] for p in ring), [p for p in ring if not wet[p]])
        self.assertFalse(wet[(1, 1)])                                   # the bank (heights land) stays land

    def test_bigger_map_winding_coast_and_borders(self):
        """x3 the natural way: the coast and the borders between regions wind (not along the 3 x 3 blocks), while
        every old tile's middle keeps its region or sea, each region stays in as many pieces as before and the
        ground's edges wind too - the same map gives the same picture."""
        from campaign_editor import upscale
        from campaign_editor.tga import read_tga
        A, B, S = (200, 40, 40), (40, 200, 40), (41, 140, 233)
        n = 14
        old = [[S if x + y < 6 else (A if x < 7 else B) for x in range(n)] for y in range(n)]
        rpath = os.path.join(self.root, "regions.tga")
        write_tga(rpath, n, n, old)
        flat = upscale.coast_mask(rpath, {A, B})
        bent = upscale.coast_mask(rpath, {A, B}, natural=True)
        self.assertNotEqual(bytes(flat.b), bytes(bent.b))
        self.assertEqual(bytes(bent.b), bytes(upscale.coast_mask(rpath, {A, B}, natural=True).b))
        out = os.path.join(self.root, "regions3.tga")
        with open(out, "wb") as fh:
            fh.write(upscale.regions_scaled(rpath, {A, B}, bent, (), {}, natural=True))
        g, first = read_tga(out), read_tga(rpath)
        W = n * 3
        for x in range(n):
            for y in range(n):
                self.assertEqual(g.get(3 * x + 1, 3 * y + 1), first.get(x, y))
        cols = lambda c: [(X, Y) for X in range(W) for Y in range(W) if g.get(X, Y) == c]
        for c in (A, B):
            px = set(cols(c))
            seen, st = {next(iter(px))}, [next(iter(px))]
            while st:
                a, b = st.pop()
                for q in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if q in px and q not in seen:
                        seen.add(q)
                        st.append(q)
            self.assertEqual(seen, px)                                  # one piece, as before
        border = {X for X in range(W) for Y in range(W) if g.get(X, Y) == A and X + 1 < W and g.get(X + 1, Y) == B}
        self.assertGreater(len(border), 1)                              # the border bends: not one straight column

    def test_bigger_map_natural_heights(self):
        """x3 heights the natural way: the sea and land as the mask says, no slope (times the heights' growth)
        steeper than the old map's steepest, a river's valley lower than the land beside it, the land round a town
        smooth, and the .hgt the game reads made the same way; the same map, the same heights."""
        from campaign_editor import upscale
        import random
        rnd = random.Random(5)
        n = 21                                                       # heights points (10 x 10 tiles)
        SEA = (0, 0, 120)
        grey = [[(v, v, v) for v in (rnd.randrange(20, 240) for _ in range(n))] for _ in range(n)]
        for y in range(n):
            grey[y][0] = SEA                                         # a sea column on the left
        hpath = os.path.join(self.root, "heights.tga")
        write_tga(hpath, n, n, grey)
        mask = upscale.Mask(61, 61)
        for Y in range(61):
            for X in range(3):
                mask[(X, Y)] = True
        rivers = [(15, Y) for Y in range(5, 25)]
        towns = [(22, 22)]
        flat = upscale.smooth_scaled(hpath, "corners", sea=True, mask=mask)
        nat = upscale.smooth_scaled(hpath, "corners", sea=True, mask=mask, natural=True, rivers=rivers, towns=towns,
                                    vertical=3.0)
        self.assertEqual(nat, upscale.smooth_scaled(hpath, "corners", sea=True, mask=mask, natural=True,
                                                    rivers=rivers, towns=towns, vertical=3.0))
        self.assertNotEqual(flat, nat)
        out = os.path.join(self.root, "heights3.tga")
        with open(out, "wb") as fh:
            fh.write(nat)
        from campaign_editor.tga import read_tga
        g, old = read_tga(out), read_tga(hpath)
        steep = max(abs(old.get(x + 1, y)[0] - old.get(x, y)[0]) for x in range(1, n - 1) for y in range(n))
        for X in range(61):
            for Y in range(61):
                c = g.get(X, Y)
                self.assertEqual(c[0] == 0 and c[1] == 0, mask[(X, Y)], (X, Y))
                if X >= 4 and X + 1 < 61:
                    self.assertLessEqual(3 * abs(g.get(X + 1, Y)[0] - c[0]), steep + 3, (X, Y))
        valley = [g.get(31, Y)[0] for Y in range(15, 45)]           # the river's tiles' middles (2X + 1)
        with open(out, "wb") as fh:
            fh.write(flat)
        f = read_tga(out)
        self.assertLess(sum(valley), sum(f.get(31, Y)[0] for Y in range(15, 45)))   # carved
        hgt = os.path.join(self.root, "heights.hgt")
        with open(hgt, "wb") as fh:
            fh.write(struct.pack("<II", n, n) + struct.pack("<%df" % (n * n), *[
                (-5.0 if grey[n - 1 - y][x] == SEA else float(grey[n - 1 - y][x][0])) for y in range(n) for x in range(n)]))
        data = upscale.hgt_scaled(hgt, hpath, mask, 3.0, natural=True, rivers=rivers, towns=towns)
        W, H = struct.unpack_from("<II", data)
        vals = struct.unpack_from("<%df" % (W * H), data, 8)
        self.assertEqual((W, H), (61, 61))
        self.assertTrue(all((v <= 0) == mask[(i % W, i // W)] or v == 0 for i, v in enumerate(vals)))

    def test_bigger_map_no_islets_no_spikes(self):
        """x3 heights' coast: a land point the old heights held inside a navigable river (map_regions calls the
        river land) came out as a small square island; corners of an older coast stuck out as thin wedges lying on
        the water's level (they flicker in the game, z-fighting). Afterwards: no land in the river, no point with
        the other kind on 3 or 4 sides except the tiles' middles map_regions decided."""
        from campaign_editor import upscale
        P, S, LAND, WATER = (200, 40, 40), (41, 140, 233), (60, 60, 60), (0, 0, 120)
        n = 8
        regions = [[S if x + y < 4 else P for x in range(n)] for y in range(n)]       # a sea corner, land
        rpath = os.path.join(self.root, "regions.tga")
        write_tga(rpath, n, n, regions)
        hn = 2 * n + 1
        heights = [[WATER if (x + y < 8 or 9 <= x <= 11) and (x, y) != (10, 10) else LAND for x in range(hn)]
                   for y in range(hn)]                                                # a river, a land point in it
        hpath = os.path.join(self.root, "heights.tga")
        write_tga(hpath, hn, hn, heights)
        info = {}
        coast = upscale.coast_mask(rpath, {P}, natural=True)
        upscale.regions_scaled(rpath, {P}, coast, (), info, natural=True)
        agree = upscale._agreement(rpath, hpath, {P})
        wet = upscale.heights_from_tiles(info["land"], agree, upscale.heights_mask(hpath, True))
        W = wet.W
        river = [(X, Y) for X in range(29, 32) for Y in range(27, 34)]                # round the old point 10, 10
        self.assertTrue(all(wet[p] for p in river), [p for p in river if not wet[p]])
        for X in range(1, W - 1):
            for Y in range(1, W - 1):
                if X % 2 and Y % 2:
                    continue
                other = sum(1 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)) if wet[(X + a, Y + b)] != wet[(X, Y)])
                self.assertLess(other, 3, (X, Y))

    def test_bigger_map_beach_one_tile_wide(self):
        """The beach stays one tile wide along the new coast, as in both games' own maps (a tester's DaC x3: grown
        3 x it was a wide band of sand)."""
        from campaign_editor import upscale
        from campaign_editor.tga import read_tga
        sea, beach, farm = (196, 0, 0), (255, 255, 255), (0, 128, 0)
        kind = lambda x: sea if x < 2 else (beach if x < 4 else farm)      # points: tile 0 sea, 1 beach, 2-3 farm
        path = os.path.join(self.root, "ground.tga")
        write_tga(path, 9, 9, [[kind(x) for x in range(9)] for y in range(9)])
        wet = upscale.Mask(25, 25)                       # the heights' sea mask: True = sea
        for X in range(25):
            for Y in range(25):
                wet[(X, Y)] = X < 6                      # new tiles 0-2 sea, 3 on is land
        data = upscale.ground_scaled(path, wet, {sea})
        with open(path, "wb") as fh:
            fh.write(data)
        g = read_tga(path)
        tiles = [g.get(2 * t + 1, 13) for t in range(12)]
        self.assertEqual(tiles[:3], [sea] * 3)
        self.assertEqual(tiles[3], beach)                                    # the tile on the sea
        self.assertNotIn(beach, tiles[4:])                                   # none further in
        self.assertFalse([X for X in range(9, 25) if g.get(X, 13) == beach])  # nor the points between

    def test_map_made_three_times_bigger(self):
        """Every tile a 3 x 3 block: towns and characters in their blocks' middles, rivers 1 pixel wide (a corner
        link a staircase), descr_terrain's size x 3 and its heights x 3, map_heights.hgt at the new size (3 x higher),
        map.rwm removed; Restore gives every byte back."""
        from campaign_editor.plan import Plan
        from campaign_editor import upscale
        from campaign_editor.tga import read_tga
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        river, black = (0, 0, 255), (0, 0, 0)
        px = [[black] * 4 for _ in range(4)]
        px[0][0] = px[0][1] = px[1][2] = river              # (0,0)-(1,0) straight, (1,0)-(2,1) a corner
        write_tga(os.path.join(camp, "map_features.tga"), 4, 4, px)
        write(os.path.join(camp, "descr_terrain.txt"), "dimensions\n{\n\twidth  4\n\theight  4\n}\n"
              "heights\n{\n\tmin_sea_height  -3122.256\n\tmax_land_height  7511.272\n}\n")
        import struct
        hp = [[(0, 0, 253) if x < 3 else (51, 51, 51) for x in range(9)] for y in range(9)]   # sea west, land east
        write_tga(os.path.join(camp, "map_heights.tga"), 9, 9, hp)
        with open(os.path.join(camp, "map_heights.hgt"), "wb") as fh:          # the game's own copy, read instead
            fh.write(struct.pack("<II", 9, 9) + struct.pack("<81f", *[(-24.5 if x < 3 else 1502.3)
                                                                     for y in range(9) for x in range(9)]))
        write(os.path.join(camp, "map.rwm"), "cache")
        # the campaign's script: campaign-map places move with the map (a tester's DaC: scripted armies stood in the
        # clouds at their old places), battle positions in the same script stay
        write(os.path.join(camp, "campaign_script.txt"),
              "script\n\tspawn_army\n\t\tfaction romans_julii\n"
              "\t\tcharacter\tGaius, named character, age 30, x 1, y 2, family\n"
              "\t\tunit\t\troman generals guard cavalry early\texp 1 armour 0 weapon_lvl 0\n\tend\n"
              "\tsnap_strat_camera 2, 1\t\t\t; the camera 2, 1\n"
              "\treposition_character Gaius Julius, 0, 3\n"
              "\tif I_CharacterTypeNearTile romans_julii named_character, 0 1, 1 and I_TurnNumber > 2\n"
              "\t\treveal_area 0, 0, 1, 2\n\tend_if\n"
              "\tunit_order_move cohort1 100 60 run\n"
              "\tset_camera_bookmark 1, 100, 0, 100, 100, 0, 0\n"
              "\tset_counter ghost 3, 4\n"
              "end_script\n")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        tiles = mod.city_tiles("test")
        plan = Plan(mod, "map", "map_x3", {})
        warn = upscale.plan_upscale(plan, "test")
        bdir = plan.apply()
        script = open(os.path.join(camp, "campaign_script.txt")).read().splitlines()
        self.assertIn("x 4, y 7, family", script[3])                                    # spawned: (1, 2)
        self.assertEqual(script[6], "\tsnap_strat_camera 7, 4\t\t\t; the camera 2, 1")    # comment as it was
        self.assertEqual(script[7], "\treposition_character Gaius Julius, 1, 10")
        self.assertEqual(script[8], "\tif I_CharacterTypeNearTile romans_julii named_character, 1 4, 4 "
                                    "and I_TurnNumber > 2")                            # distance 0 = its block
        self.assertEqual(script[9], "\t\treveal_area 0, 0, 5, 8")                         # whole blocks
        self.assertEqual(script[11:13], ["\tunit_order_move cohort1 100 60 run",          # battle places stay
                                         "\tset_camera_bookmark 1, 100, 0, 100, 100, 0, 0"])
        self.assertTrue(any("campaign_script.txt: line(s) 14 " in w for w in warn))      # not known: by hand
        mod = ModData(self.root)
        self.assertEqual({r: xy for r, xy in mod.city_tiles("test").items()},
                         {r: upscale.new_xy(*xy) for r, xy in tiles.items()})
        s = Strat(mod.load(mod.campaign_file("test", "descr_strat.txt")))
        self.assertIn((4, 4), [c.xy for fb in s.factions for c in fb.characters])        # was (1, 1)
        f = read_tga(os.path.join(camp, "map_features.tga"))
        self.assertEqual((f.width, f.height), (12, 12))
        rivers = {(x, y) for x in range(12) for y in range(12) if f.get(x, y) == river}
        self.assertTrue({(1, 1), (7, 4)} <= rivers)                    # its two ends in their blocks' middles
        self.assertTrue(all((x // 3, y // 3) in {(0, 0), (1, 0), (2, 1), (2, 0), (1, 1)} for x, y in rivers))
        seen, todo = {(1, 1)}, [(1, 1)]                                # (natural rivers: the bend's point moved)
        while todo:
            x, y = todo.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in rivers and q not in seen:
                    seen.add(q)
                    todo.append(q)
        self.assertEqual(seen, rivers)                                 # one unbroken river, side by side only
        self.assertFalse(any({(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)} <= rivers
                             for x in range(11) for y in range(11)))                     # never 2 x 2
        self.assertIn("width  12", open(os.path.join(camp, "descr_terrain.txt")).read())
        self.assertIn("max_land_height  22533.816", open(os.path.join(camp, "descr_terrain.txt")).read())  # x 3
        with open(os.path.join(camp, "map_heights.hgt"), "rb") as fh:
            raw = fh.read()
        hw, hh = struct.unpack_from("<II", raw)
        self.assertEqual((hw, hh), (25, 25))                                   # the picture's new size: 6W+1
        vals = struct.unpack_from("<625f", raw, 8)
        self.assertAlmostEqual(vals[24], 1502.3 * 3, 1)                        # land, 3 x higher
        self.assertAlmostEqual(vals[0], -24.5 * 3, 1)                          # sea, 3 x deeper
        hi = read_tga(os.path.join(camp, "map_heights.tga"))
        self.assertEqual((hi.width, hi.height), (25, 25))
        self.assertFalse(os.path.exists(os.path.join(camp, "map.rwm")))
        from campaign_editor.plan import restore
        restore(ModData(self.root), bdir)
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))},
                         before)

    def test_bigger_map_with_an_empty_hgt(self):
        """A tester's Rome mod carried an empty map_heights.hgt (0 bytes): x3 stopped with 'unpack_from requires a
        buffer of at least 8 bytes'. It is made again from the new map_heights.tga instead (as the game converts it),
        said in the warnings; Restore gives the empty file back."""
        from campaign_editor.plan import Plan, restore
        from campaign_editor import upscale
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        write(os.path.join(camp, "descr_terrain.txt"), "dimensions\n{\n\twidth  4\n\theight  4\n}\n"
              "heights\n{\n\tmin_sea_height  -3122.256\n\tmax_land_height  7511.272\n}\n")
        hp = [[(0, 0, 253) if x < 3 else (51, 51, 51) for x in range(9)] for y in range(9)]
        write_tga(os.path.join(camp, "map_heights.tga"), 9, 9, hp)
        open(os.path.join(camp, "map_heights.hgt"), "wb").close()
        before = tree_hash(self.root)
        mod = ModData(self.root)
        plan = Plan(mod, "map", "map_x3", {})
        warn = upscale.plan_upscale(plan, "test")
        self.assertTrue(any("map_heights.hgt was empty" in w for w in warn), warn)
        bdir = plan.apply()
        with open(os.path.join(camp, "map_heights.hgt"), "rb") as fh:
            raw = fh.read()
        self.assertEqual(struct.unpack_from("<II", raw), (25, 25))
        vals = struct.unpack_from("<625f", raw, 8)
        self.assertLess(vals[0], 0)                                           # the sea in the west
        self.assertAlmostEqual(vals[24], 51 * 7511.272 * 3 / 255, 0)          # land: grey x the new top / 255
        restore(ModData(self.root), bdir)
        self.assertEqual({k: v for k, v in tree_hash(self.root).items()
                          if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}, before)

    def test_bigger_map_keeps_towns_ports_bridges_and_ground(self):
        """x3 on a map like a tester's DaC: a town in a region descr_regions does not list (Erebor became 9 town
        pixels), a port (ports were left off the water), a land bridge over a strait (left as dots), forests painted
        as dense-forest tile middles with wilderness between (Mirkwood turned to wilderness). Afterwards: one town
        pixel each with its own region round it, the port on land touching the sea and its region, map_regions and
        the heights agree on every tile, every land tile still dense forest, the bridge one unbroken chain."""
        from campaign_editor.plan import Plan
        from campaign_editor import upscale
        from campaign_editor.upscale import _pixels, _heights_sea
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        S, R, B, U, T, P = (40, 140, 230), (255, 0, 0), (0, 0, 255), (10, 200, 10), (0, 0, 0), (255, 255, 255)
        rows = ["SSSSSSSSSS", "SBTBBSSSSS", "SBBBBSSSSS", "SRRRPSUUUS", "SRTRRSUTUS", "SRRRRSUUUS", "SSSSSSSSSS"]
        key = {"S": S, "R": R, "B": B, "U": U, "T": T, "P": P}
        px = [[key[c] for c in row] for row in rows]                   # rows[y], y = 0 at the bottom
        write_tga(os.path.join(camp, "map_regions.tga"), 10, 7, px)
        land = lambda x, y: 0 <= x < 10 and 0 <= y < 7 and px[y][x] != S
        hp, gp = [], []
        for j in range(15):
            hrow, grow = [], []
            for i in range(21):
                tiles = [(a, b) for a in ((i - 1) // 2,) if i % 2 for b in ((j - 1) // 2,) if j % 2] or \
                    [(a, b) for a in {(i - 1) // 2, i // 2} for b in {(j - 1) // 2, j // 2}
                     if 0 <= a < 10 and 0 <= b < 7]
                on = any(land(a, b) for a, b in tiles)
                hrow.append((60, 60, 60) if on else (0, 0, 253))
                grow.append(((0, 64, 0) if i % 2 and j % 2 else (0, 0, 0)) if on else (196, 0, 0))
            hp.append(hrow)
            gp.append(grow)
        write_tga(os.path.join(camp, "map_heights.tga"), 21, 15, hp)
        write_tga(os.path.join(camp, "map_ground_types.tga"), 21, 15, gp)
        fp = [[(0, 0, 0)] * 10 for _ in range(7)]
        for x in (4, 5, 6):
            fp[4][x] = (0, 255, 0)                                     # red land - the strait - the unlisted land
        write_tga(os.path.join(camp, "map_features.tga"), 10, 7, fp)
        mod = ModData(self.root)
        plan = Plan(mod, "map", "map_x3", {})
        upscale.plan_upscale(plan, "test")
        plan.apply()
        _, W, H, _, _, at = _pixels(os.path.join(camp, "map_regions.tga"))
        _, _, _, _, _, hat = _pixels(os.path.join(camp, "map_heights.tga"))
        _, _, _, _, _, gat = _pixels(os.path.join(camp, "map_ground_types.tga"))
        _, _, _, _, _, fat = _pixels(os.path.join(camp, "map_features.tga"))
        sea = _heights_sea(hat)
        self.assertEqual((W, H), (30, 21))
        towns = [(x, y) for y in range(H) for x in range(W) if at(x, y) == T]
        self.assertEqual(sorted(towns), sorted(upscale.new_xy(*t) for t in ((2, 1), (2, 4), (7, 4))))
        for x, y in towns:                                             # its own region (or sea) all round it
            ring = {at(x + a, y + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b}
            self.assertEqual(len(ring - {S}), 1, (x, y, ring))
        self.assertEqual({at(x + 1, y) for x, y in towns if (x, y) == upscale.new_xy(7, 4)}, {U})
        ports = [(x, y) for y in range(H) for x in range(W) if at(x, y) == P]
        self.assertEqual(len(ports), 1)
        (x, y), = ports
        sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
        self.assertFalse(sea(2 * x + 1, 2 * y + 1))                    # a port stands on land
        self.assertTrue(any(sea(2 * (x + a) + 1, 2 * (y + b) + 1) for a, b in sides))
        self.assertTrue(any(at(x + a, y + b) == R for a, b in sides))
        for Y in range(H):
            for X in range(W):
                self.assertEqual(at(X, Y) != S, not sea(2 * X + 1, 2 * Y + 1), (X, Y))   # one coast
                if at(X, Y) != S:
                    self.assertEqual(gat(2 * X + 1, 2 * Y + 1), (0, 64, 0), (X, Y))      # the forest stays
        bridge = {(X, Y) for X in range(W) for Y in range(H) if fat(X, Y) == (0, 255, 0)}
        seen, todo = set(), [next(iter(bridge))]
        while todo:
            q = todo.pop()
            seen.add(q)
            todo += [(q[0] + a, q[1] + b) for a, b in sides if (q[0] + a, q[1] + b) in bridge - seen]
        self.assertEqual(seen, bridge)                                 # one unbroken chain ...
        self.assertTrue({at(*q) for q in bridge} >= {R, U, S})         # ... from land over the water to land

    def test_new_region_colour_on_a_full_map(self):
        """A map whose regions already use the 200 colours the old walk could make (a tester's big map: 'no free
        colour left') still gets a new colour, one no pixel has."""
        from campaign_editor.regionedit import free_colour
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        old = sorted({((i * 97) % 200 + 30, (i * 57) % 200 + 30, (i * 37) % 200 + 30) for i in range(1, 5000)})
        self.assertEqual(len(old), 200)
        px = [old[y * 20:(y + 1) * 20] for y in range(10)]
        write_tga(os.path.join(camp, "map_regions.tga"), 20, 10, px)
        mod = ModData(self.root)
        c = free_colour(mod, "test", [(1, 2, 3)])
        self.assertNotIn(c, set(old))
        self.assertNotEqual(c, (1, 2, 3))
        many = []
        for _ in range(300):                                  # and hundreds more after it
            many.append(free_colour(mod, "test", many))
        self.assertEqual(len(set(many)), 300)
        self.assertFalse(set(many) & set(old))

    def test_new_region_carved_out(self):
        from campaign_editor.edit import edit
        from campaign_editor.tga import read_tga
        mod = ModData(self.root)
        new = {"name": "N_R", "settlement": "Ntown", "creator": "alpha", "rebels": "Rebels", "resources": [],
               "city": (0, 3), "owner": "alpha", "level": "village"}
        painted = {(0, 3): "N_R", (1, 3): "N_R", (0, 2): "N_R"}
        for bad in ({(1, 1): "N_R"}, {(0, 3): "Nowhere"}):          # a town pixel; an unknown region
            with self.assertRaises(ValueError):
                edit(ModData(self.root), "test", "alpha", {"regions": {"painted": bad, "new": [new]}})
        plan = edit(mod, "test", "alpha", {"regions": {"painted": painted, "new": [new]}})
        bdir = plan.apply()
        m2 = ModData(self.root)
        self.assertEqual(m2.regions("test")["N_R"]["settlement"], "Ntown")
        self.assertEqual(m2.city_tiles("test")["N_R"], (0, 3))
        img = read_tga(m2.campaign_file("test", "map_regions.tga"))
        self.assertEqual(img.get(1, 3), m2.regions("test")["N_R"]["colour"])
        self.assertEqual(Strat(m2.load(m2.campaign_file("test", "descr_strat.txt"))).owners()["N_R"], "alpha")
        labels = open(m2.region_labels_file("test"), "rb").read().decode("utf-16")
        self.assertIn("{N_R}", labels)
        self.assertIn("{Ntown}", labels)
        restore(m2, bdir)
        self.assertNotIn("N_R", ModData(self.root).regions("test"))

    def test_new_region_gets_its_slaves_resource_in_rome(self):
        """Rome: every region carries a 'resource slaves' (the enslaved people go there); a new region without one
        stops the game ("could not find slave resource in CE Newland(97), every region must have one" - the
        a tester's test mod). A game whose regions do not all carry one is left alone."""
        from campaign_editor import resources as R
        from campaign_editor.edit import edit
        mod = ModData(self.root)
        img = mod.region_map("test")
        seed = Plan(mod, "res", "", {})
        added = []
        for name, info in mod.regions("test").items():
            cells = [tuple(p) for p in img.find(tuple(info["colour"])) if tuple(p) not in ((0, 3), (1, 3), (0, 2))]
            added.append({"type": "slaves", "xy": cells[0]})
        R.apply(seed, "test", {"added": added})
        seed.apply()
        mod = ModData(self.root)
        new = {"name": "N_R", "settlement": "Ntown", "creator": "alpha", "rebels": "Rebels", "resources": [],
               "city": (0, 3), "owner": "alpha", "level": "village"}
        painted = {(0, 3): "N_R", (1, 3): "N_R", (0, 2): "N_R"}
        plan = edit(mod, "test", "alpha", {"regions": {"painted": painted, "new": [new]}})
        sf = plan.edit(mod.campaign_file("test", "descr_strat.txt"))
        slaves = [r for r in R.read(sf) if r.kind == "slaves"]
        self.assertEqual(len(slaves), len(added) + 1)
        self.assertTrue(any(tuple(r.xy) in painted and tuple(r.xy) != (0, 3) for r in slaves))
        restore(mod, backups(mod)[0])

    def test_slaves_on_the_town_tile_count_for_its_region(self):
        """HLR keeps every region's slaves resource on the town's own tile (a black pixel of map_regions): those
        regions have theirs - none is added - and the check reads descr_regions once, not for every tile (on HLR's
        750 regions Preview of a new faction froze for many minutes)."""
        from unittest import mock
        from campaign_editor import regionedit, resources as R
        mod = ModData(self.root)
        towns = mod.city_tiles("test")
        seed = Plan(mod, "res", "", {})
        R.apply(seed, "test", {"added": [{"type": "slaves", "xy": xy} for xy in towns.values()]})
        seed.apply()
        mod = ModData(self.root)
        plan = Plan(mod, "probe", "", {})
        colours = {k: v["colour"] for k, v in mod.regions("test").items()}
        with mock.patch.object(ModData, "regions", autospec=True, side_effect=ModData.regions) as reads:
            regionedit._slave_resources(plan, "test", {}, colours, [])
        self.assertLessEqual(reads.call_count, 3)
        sf = plan.files[mod.campaign_file("test", "descr_strat.txt")]
        self.assertEqual(len([r for r in R.read(sf) if r.kind == "slaves"]), len(towns))
        restore(mod, backups(mod)[0])

    def test_new_faction_starts_in_a_new_region_one_apply(self):
        """A region made on the Map and picked as the new faction's start town: map, region and
        faction written by one Apply (the region first, as a rebel village the faction takes);
        an existing region's descr_regions lines changed by the same run."""
        new = {"name": "N_R", "settlement": "Ntown", "creator": "alpha", "rebels": "Rebels", "resources": [],
               "city": (0, 3), "owner": None, "level": "village"}
        painted = {(0, 3): "N_R", (1, 3): "N_R", (0, 2): "N_R"}
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {
            "start": {"regions": ["N_R"], "leader": {"name": "Boris Alphid", "age": 35}},
            "regions": {"painted": painted, "new": [new], "edits": {"A_R": {"triumph": "9", "farming": "4"}}}})
        plan.apply()
        m2 = ModData(self.root)
        self.assertEqual(Strat(m2.load(m2.campaign_file("test", "descr_strat.txt"))).owners()["N_R"], "beta")
        self.assertEqual(m2.city_tiles("test")["N_R"], (0, 3))
        with open(m2.campaign_file("test", "descr_regions.txt")) as fh:
            lines = [l.strip() for l in fh.read().splitlines()]
        a = lines.index("A_R")
        self.assertEqual(lines[a + 6:a + 8], ["9", "4"])
        with self.assertRaises(ValueError):
            build(ModData(self.root), "test", "alpha", "gamma", {
                "start": {"regions": ["B_R"], "leader": {"name": "Boris Alphid"}},
                "regions": {"edits": {"A_R": {"creator": "nobody"}}}})

    def test_setup_fix_vegetation(self):
        from campaign_editor import gamefix
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_caps_ex.txt"), "; caps\nsprite_format  xml\nvegetation_source  text\n")
        mod = ModData(self.root)
        found = gamefix.problems(mod)
        self.assertEqual([p["id"] for p in found], ["vegetation_source"])
        bdir = gamefix.fix_plan(mod, found).apply()
        self.assertIn("vegetation_source  binary", open(os.path.join(d, "descr_caps_ex.txt")).read())
        self.assertEqual(gamefix.problems(ModData(self.root)), [])
        restore(ModData(self.root), bdir)
        self.assertIn("vegetation_source  text", open(os.path.join(d, "descr_caps_ex.txt")).read())

    def test_medieval_unpack(self):
        # a Medieval II straight from Steam: packs only; the unpacker needs two DLLs next to it
        import stat, sys, tempfile
        from campaign_editor import gamefix
        game = tempfile.mkdtemp()
        os.makedirs(os.path.join(game, "packs"))
        os.makedirs(os.path.join(game, "data"))
        open(os.path.join(game, "packs", "data_0.pack"), "wb").close()
        self.assertIsNone(gamefix.unpack_needed(game))              # no unpacker: nothing to offer
        tools = os.path.join(game, "tools", "unpacker")
        os.makedirs(tools)
        exe = os.path.join(tools, "unpacker.exe")
        with open(exe, "w") as fh:                                  # a stand-in that 'unpacks'
            fh.write("#!%s\nimport os\nopen(os.path.join('..', '..', 'data', 'descr_sm_factions.txt'), 'w')"
                     ".write('faction x')\n" % sys.executable)
        os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
        for d in gamefix.UNPACK_DLLS:
            open(os.path.join(game, d), "wb").write(b"dll")
        need = gamefix.unpack_needed(os.path.join(game, "data"))
        self.assertEqual(need["dlls"], list(gamefix.UNPACK_DLLS))
        if os.name != "nt":
            gamefix.unpack(need)
            self.assertTrue(all(os.path.exists(os.path.join(tools, d)) for d in gamefix.UNPACK_DLLS))
            self.assertIsNone(gamefix.unpack_needed(game))          # unpacked now

    def test_english_text_wins(self):
        # the game reads data/text/english first (Medieval II keeps its tables only there):
        # the tool reads and writes that copy, and a new town gets the core level of its size
        from campaign_editor.edit import edit
        d = os.path.join(self.root, "data", "text")
        write(os.path.join(d, "english", "test_regions_and_settlement_names.txt"), "{Alpha}\t\tA\n", utf16=True)
        write(os.path.join(d, "english", "extra.txt"), "{X}\t\tx\n", utf16=True)
        mod = ModData(self.root)
        self.assertIn(os.path.join("english", "test_regions"), mod.region_labels_file("test"))
        names = [os.path.relpath(p, d) for p in mod.text_files()]
        self.assertIn(os.path.join("english", "extra.txt"), names)
        self.assertNotIn("test_regions_and_settlement_names.txt", names)     # hidden by the english copy
        write(os.path.join(self.root, "data", "export_descr_buildings.txt"),
              "building core_building\n{\n    levels hut hall\n    {\n        hut requires factions { alpha, }\n"
              "        {\n            settlement_min village\n        }\n        hall requires factions { alpha, }\n"
              "        {\n            settlement_min town\n        }\n    }\n}\n")
        new = {"name": "N_R", "settlement": "Ntown", "creator": "alpha", "rebels": "Rebels", "resources": [],
               "city": (0, 3), "owner": "alpha", "level": "town"}
        plan = edit(ModData(self.root), "test", "alpha", {"regions": {"painted": {(0, 3): "N_R"}, "new": [new]}})
        plan.apply()
        m2 = ModData(self.root)
        self.assertIn("{N_R}", open(m2.region_labels_file("test"), "rb").read().decode("utf-16"))
        s = Strat(m2.load(m2.campaign_file("test", "descr_strat.txt")))
        st = next(x for x in s.faction("alpha").settlements if x.region == "N_R")
        from campaign_editor.buildings import settlement_info
        self.assertEqual(settlement_info(s.lines[st.start:st.end]), ("town", [("core_building", "hut")]))

    def test_new_region_takes_after_its_land(self):
        # 'built by' and the rebels left empty: those of the region its land is cut from; the
        # owner's new town takes a garrison in the same Apply (one backup, not two)
        from campaign_editor.edit import edit
        new = {"name": "N_R", "settlement": "Ntown", "creator": "", "rebels": "", "resources": [],
               "city": (0, 3), "owner": "alpha", "level": "village"}
        plan = edit(ModData(self.root), "test", "alpha", {
            "regions": {"painted": {(0, 3): "N_R", (1, 3): "N_R"}, "new": [new]},
            "garrisons": {"N_R": ["alpha general"]}})
        plan.apply()
        m2 = ModData(self.root)
        info = m2.regions("test")["N_R"]
        donor = m2.regions("test")["A_R"]
        self.assertEqual((info["creator"], info["rebels"]), (donor["creator"], donor["rebels"]))
        s = Strat(m2.load(m2.campaign_file("test", "descr_strat.txt")))
        self.assertIn("N_R", [st.region for st in s.faction("alpha").settlements])
        self.assertTrue(any(c.xy == (0, 3) for c in s.faction("alpha").characters))     # its garrison

    def test_new_region_religions_never_broken(self):
        from campaign_editor.regionedit import religions_for
        regions = {"A": {"religions": {"catholic": 90, "pagan": 10}}, "B": {"religions": {"catholic": 90, "pagan": 10}},
                   "C": {"religions": {"islam": 100}}}
        self.assertEqual(religions_for(regions, {"catholic": 0, "pagan": 0}, "C"), {"islam": 100})   # zeros: the donor's
        self.assertEqual(religions_for(regions, None, None), {"catholic": 90, "pagan": 10})         # most common
        self.assertEqual(religions_for(regions, {"pagan": 100}, "C"), {"pagan": 100})             # given, sums to 100

    def test_unit_pack_round_trip(self):
        # a unit taken out with its model, mount, texture, card, texts and recruit place, put into
        # another mod where its names and its model's name are taken: all renamed, nothing overwritten
        from campaign_editor import packs
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_unit.txt"), EDU.replace(
            "ownership\talpha", "soldier\t\talpha_model, 20, 0, 1\nmount\t\tlight horse\nownership\talpha"))
        write(os.path.join(d, "descr_model_battle.txt"),
              "type\t\talpha_model\ntexture\t\talpha, data/models_unit/textures/a.tga\n"
              "model_flexi\t\tdata/models_unit/a.cas, max\n\n"
              "type\t\thorse_model\ntexture\t\talpha, data/models_unit/textures/h.tga\n")
        write(os.path.join(d, "descr_mount.txt"), "type\t\tlight horse\nclass\t\thorse\nmodel\t\thorse_model\n")
        write(os.path.join(d, "models_unit", "textures", "a.tga.dds"), "A-texture")      # Rome keeps .tga.dds
        write(os.path.join(d, "models_unit", "a.cas"), "A-model")
        write(os.path.join(d, "models_unit", "textures", "h.tga.dds"), "H-texture")
        write(os.path.join(d, "export_descr_buildings.txt"),
              "building barracks\n{\n    levels hall\n    {\n        hall requires factions { alpha, }\n"
              "        {\n            capability\n            {\n                recruit \"alpha general\"  0  "
              "requires factions { alpha, }\n            }\n        }\n    }\n}\n")
        write(os.path.join(d, "text", "export_units.txt"),
              "{alpha_general}Alpha Guard\n{alpha_general_descr}Good\nmen\n{alpha_general_descr_short}Good\n",
              utf16=True)
        pack = os.path.join(self.root, "alpha.zip")
        man = packs.export_pack(ModData(self.root), ["alpha general"], pack)
        self.assertEqual(sorted(man["blocks"]["model"]), ["alpha_model", "horse_model"])
        self.assertIn("models_unit/textures/a.tga.dds", man["files"])
        self.assertEqual(man["recruit"][0]["chain"], "barracks")
        # the target: a copy whose alpha_model is another model
        target = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, target)
        shutil.copytree(self.root, os.path.join(target, "mod"))
        troot = os.path.join(target, "mod")
        write(os.path.join(troot, "data", "descr_model_battle.txt"),
              "type\t\talpha_model\nmodel_flexi\t\tdata/models_unit/other.cas, max\n\n"
              "type\t\thorse_model\ntexture\t\talpha, data/models_unit/textures/h.tga\n")
        before = tree_hash(troot)
        manifest, files = packs.read_pack(pack)
        tmod = ModData(troot)
        plan = Plan(tmod, "pack", "pack", {})
        packs.import_pack(plan, manifest, files, ["alpha"])
        bdir = plan.apply()
        m2 = ModData(troot)
        edu = m2.load(m2.file("edu"))
        blocks = packs.type_blocks(edu)
        self.assertIn("alpha general 2", blocks)
        unit = "\n".join(edu.text(i) for i in range(*blocks["alpha general 2"]))
        self.assertIn("alpha_model_2", unit)                       # its model, renamed with it
        self.assertIn("alpha_general_2", unit)
        models = packs.type_blocks(m2.load(os.path.join(troot, "data", "descr_model_battle.txt")))
        self.assertEqual(sorted(models), ["alpha_model", "alpha_model_2", "horse_model"])   # horse shared
        self.assertTrue(os.path.exists(os.path.join(troot, "data", "ui", "units", "alpha", "#alpha_general_2.tga")))
        txt = open(m2.text_file("export_units.txt"), "rb").read().decode("utf-16")
        self.assertIn("{alpha_general_2_descr}Good", txt)
        self.assertIn('recruit "alpha general 2"', open(m2.file("edb")).read())
        restore(ModData(troot), bdir)
        after = {k: v for k, v in tree_hash(troot).items() if "_backups" not in k}
        self.assertEqual(after, before)                              # Restore: byte for byte

    def test_engine_found_in_the_game_folder_and_the_limit_raised_in_the_mod(self):
        # M2EX copied over the game's root (any case), the mod in mods/<mod>/data: the engine is seen, the
        # game's descr_ex.txt is NOT read for the mod (engines read a mod's own _ex files only - "Mods that don't
        # ship this file get safe defaults"), and a raise makes the mod's own file - the game's file untouched
        from campaign_editor import limits
        game = os.path.join(self.root, "game")
        os.makedirs(os.path.join(game, "mods"))
        write(os.path.join(game, "medieval2.exe"), "x")
        write(os.path.join(game, "data", "descr_ex.txt"), "; Extended settings\nmax_factions 50\nrolloff 1\n")
        write(os.path.join(game, "data", "descr_sm_factions.txt"), SM)
        write(os.path.join(game, "data", "descr_religions.txt"), "religions\n{\n}\n")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "mods", "m", "data"))
        mod = ModData(os.path.join(game, "mods", "m", "data"))
        self.assertEqual(limits.engine_of(mod), "M2EX.exe")         # its descr_ex.txt is there
        self.assertIn("taken as installed", limits.engine_report(mod))
        os.rename(os.path.join(game, "data", "descr_ex.txt"), os.path.join(game, "ex.bak"))
        self.assertIsNone(limits.engine_of(mod))
        self.assertIn("not found", limits.engine_report(mod))
        os.rename(os.path.join(game, "ex.bak"), os.path.join(game, "data", "descr_ex.txt"))
        write(os.path.join(game, "m2ex.EXE"), "x")
        self.assertEqual(limits.engine_of(mod), "M2EX.exe")
        lim = limits.faction_limit(mod)
        self.assertEqual((lim["max"], lim["own"], lim["written"]), (31, False, False))   # M2EX's default, not 50
        self.assertIn("built-in defaults", limits.engine_report(mod))
        self.assertEqual(limits.faction_limit(ModData(os.path.join(game, "data")))["max"], 50)  # the game itself
        plan = Plan(mod, "a", "b", {})
        limits.raise_limit(plan, lim, 40)
        plan.apply()
        own = os.path.join(game, "mods", "m", "data", "descr_ex.txt")
        with open(own, "rb") as fh:
            text = fh.read()
        self.assertIn(b"max_factions 40", text)
        self.assertNotIn(b"rolloff", text)                          # only the line meant: the rest stays default
        with open(os.path.join(game, "data", "descr_ex.txt"), "rb") as fh:
            self.assertIn(b"max_factions 50", fh.read())
        lim = limits.faction_limit(ModData(mod.data))
        self.assertEqual((lim["max"], lim["own"]), (40, True))
        restore(ModData(mod.data), backups(ModData(mod.data))[0])
        self.assertFalse(os.path.exists(own))

    def test_engine_files_missing_in_a_mod(self):
        """A mod of a game with M2EX / REX that lacks the engine's own files (*_ex.txt) is told so on Load, and
        with a yes gets the game's copies (backup, Restore removes them)."""
        from campaign_editor import gamefix
        game = os.path.join(self.root, "game")
        write(os.path.join(game, "medieval2.exe"), "x")
        write(os.path.join(game, "M2EX.exe"), "x")
        write(os.path.join(game, "data", "descr_ex.txt"), "max_factions 31\n")
        write(os.path.join(game, "data", "descr_caps_ex.txt"), "sprite_format xml\n")
        write(os.path.join(game, "data", "descr_religions.txt"), "x\n")
        write(os.path.join(game, "data", "descr_sm_factions.txt"), SM)
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "mods", "m", "data"))
        write(os.path.join(game, "mods", "m", "data", "descr_caps_ex.txt"), "sprite_format xml\n")
        mod = ModData(os.path.join(game, "mods", "m", "data"))
        found = [p for p in gamefix.problems(mod) if p["id"] == "engine_files"]
        self.assertEqual(found[0]["names"], ["descr_ex.txt"])
        self.assertEqual(gamefix.missing_engine_files(ModData(os.path.join(game, "data"))), [])   # the game itself
        gamefix.fix_plan(mod, found).apply()
        self.assertTrue(os.path.isfile(os.path.join(mod.data, "descr_ex.txt")))
        self.assertEqual(gamefix.missing_engine_files(ModData(mod.data)), [])
        restore(ModData(mod.data), backups(ModData(mod.data))[0])
        self.assertFalse(os.path.exists(os.path.join(mod.data, "descr_ex.txt")))

    def test_engine_settings_come_from_the_mods_own_files_only(self):
        """REX / M2EX read a mod's descr_ex.txt / descr_caps_ex.txt from the mod alone ("Mods that don't ship this
        file get safe defaults"): the game's data copy says nothing about a mod's sprites or battle models."""
        from campaign_editor import gamefix, limits, modeldb, symbols
        game = os.path.join(self.root, "game")
        write(os.path.join(game, "medieval2.exe"), "x")
        write(os.path.join(game, "M2EX.exe"), "x")
        write(os.path.join(game, "data", "descr_religions.txt"), "x\n")
        write(os.path.join(game, "data", "descr_caps_ex.txt"),
              "sprite_format  xml\nmodel_battle_source  text\nvegetation_source  text\n")
        write(os.path.join(game, "data", "descr_sm_factions.txt"), SM)
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "mods", "m", "data"))
        mod = ModData(os.path.join(game, "mods", "m", "data"))
        self.assertIsNone(limits.ex_file(mod, "descr_caps_ex.txt"))
        self.assertEqual(symbols.sprite_mode(mod), "sd")               # the engine's default for mods
        self.assertFalse(modeldb.text_source(mod))
        self.assertNotIn("vegetation_source", [p["id"] for p in gamefix.problems(mod)])
        self.assertIn("descr_caps_ex.txt", [n for p in gamefix.problems(mod) if p["id"] == "engine_files"
                                            for n in p["names"]])
        gd = ModData(os.path.join(game, "data"))
        self.assertEqual(symbols.sprite_mode(gd), "xml")                # the game's own campaign reads it
        self.assertTrue(modeldb.text_source(gd))
        write(os.path.join(mod.data, "descr_caps_ex.txt"), "sprite_format  xml\n")
        self.assertEqual(symbols.sprite_mode(mod), "xml")
        self.assertFalse(modeldb.text_source(mod))                      # not in the mod's file: default modeldb

    def test_a_refused_write_changes_nothing(self):
        """A file the system refuses half way through Apply (WinError 5: read-only, or held by another program - a
        report from a Medieval II mod): the files written before it go back, the copies go, no temp file and no
        backup stay, and the error says it in plain words. A read-only file is said in Preview and written."""
        import stat
        from unittest import mock
        from campaign_editor import textio
        before = tree_hash(self.root)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {
            "display_name": "Betan League", "short_name": "Beta", "adjective": "Betan",
            "start": {"regions": ["B_R"], "leader": {"name": "Boris Alphid", "age": 35}, "denari": 500}})
        changed = plan.changed_files()
        self.assertGreater(len(changed), 3)
        victim = changed[2]
        real = textio.os.replace

        def refuse(src, dst):
            if os.path.normcase(dst) == os.path.normcase(victim):
                raise PermissionError(13, "Access is denied", dst)
            return real(src, dst)
        with mock.patch.object(textio.os, "replace", side_effect=refuse), \
                mock.patch.object(textio.time, "sleep"):
            with self.assertRaises(textio.WriteError) as got:
                plan.apply()
        self.assertIn("could not be written", str(got.exception))
        self.assertIn("Nothing was changed", str(got.exception))
        self.assertEqual(tree_hash(self.root), before)                   # byte for byte, no backup, no temp file
        # a read-only file: Preview says so, Apply takes the mark off and writes it
        os.chmod(victim, stat.S_IREAD)
        try:
            mod = ModData(self.root)
            plan = build(mod, "test", "alpha", "beta", {
                "display_name": "Betan League", "short_name": "Beta", "adjective": "Betan",
                "start": {"regions": ["B_R"], "leader": {"name": "Boris Alphid", "age": 35}, "denari": 500}})
            self.assertIn("marked read-only", plan.report())
            plan.apply()
            self.assertTrue(os.stat(victim).st_mode & stat.S_IWRITE)
            restore(ModData(self.root), backups(ModData(self.root))[0])
        finally:
            os.chmod(victim, stat.S_IREAD | stat.S_IWRITE)

    def test_no_rights_disk_full_and_restore_half_way_in_plain_words(self):
        """Windows' corner cases: the mod's folder takes no writes (the backup cannot be made), the disk fills half
        way, a path longer than Windows takes, a file held by the game while Restore runs - each said in plain
        words with what to do, nothing changed or lost, and Restore can be run again."""
        import errno
        from unittest import mock
        from campaign_editor import plan as plan_mod, textio
        before = tree_hash(self.root)
        opts = {"display_name": "Betan League", "short_name": "Beta", "adjective": "Betan",
                "start": {"regions": ["B_R"], "leader": {"name": "Boris Alphid", "age": 35}, "denari": 500}}
        # no rights: the backup folder cannot be made
        real_makedirs = plan_mod.os.makedirs

        def no_rights(p, *a, **k):
            if plan_mod.BACKUP_DIR in p:
                raise PermissionError(13, "Access is denied", p)
            return real_makedirs(p, *a, **k)
        with mock.patch.object(plan_mod.os, "makedirs", side_effect=no_rights):
            with self.assertRaises(textio.WriteError) as got:
                build(ModData(self.root), "test", "alpha", "beta", opts).apply()
        self.assertIn("the system refused", str(got.exception))
        self.assertIn("the backup is made before any file is written", str(got.exception))
        self.assertEqual(tree_hash(self.root), before)
        # the disk fills half way: what was written goes back
        plan = build(ModData(self.root), "test", "alpha", "beta", opts)
        victim, real = plan.changed_files()[2], textio.os.replace

        def full(src, dst):
            if os.path.normcase(dst) == os.path.normcase(victim):
                raise OSError(errno.ENOSPC, "No space left on device", dst)
            return real(src, dst)
        with mock.patch.object(textio.os, "replace", side_effect=full):
            with self.assertRaises(textio.WriteError) as got:
                plan.apply()
        self.assertIn("the disk is full", str(got.exception))
        self.assertIn("Nothing was changed", str(got.exception))
        self.assertEqual(tree_hash(self.root), before)
        self.assertIn("too long", textio.plain("x.txt", OSError(errno.ENAMETOOLONG, "File name too long")))
        self.assertIsNone(textio.plain("x.txt", OSError(errno.EIO, "I/O error")))   # not one we can explain
        # Restore meets a file held by the game: it stops, keeps the backup whole, and runs again later
        bdir = build(ModData(self.root), "test", "alpha", "beta", opts).apply()
        real_copy = plan_mod.shutil.copy2
        held = {"n": 0}

        def busy(src, dst, *a, **k):
            held["n"] += 1
            if held["n"] == 2:
                raise PermissionError(13, "The process cannot access the file", dst)
            return real_copy(src, dst, *a, **k)
        with mock.patch.object(plan_mod.shutil, "copy2", side_effect=busy):
            with self.assertRaises(textio.WriteError) as got:
                restore(ModData(self.root), bdir)
        self.assertIn("Restore stopped half way", str(got.exception))
        self.assertIn("then Restore again", str(got.exception))
        self.assertTrue(os.path.isdir(bdir))                              # still there, not marked restored
        restore(ModData(self.root), bdir)
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if not k.startswith(plan_mod.BACKUP_DIR)},
                         before)                                         # the mod's files as before, byte for byte

    def test_clone_takes_the_templates_pictures_from_the_games_data(self):
        """A mod that keeps the game's own pictures (its folder holds what it changed): the template's faction
        buttons, unit cards and banner lie in the game's data. The new faction gets copies in the MOD (a tester's
        REX mod: new factions had no buttons on the faction-select screen); the game's data stays untouched."""
        game, hlr = self._game()
        gdata = os.path.join(game, "data")
        write(os.path.join(gdata, "menu", "symbols", "FE_buttons_48", "symbol48_alpha.tga"), "button")
        write(os.path.join(gdata, "ui", "units", "alpha", "#alpha_general.tga"), "card")
        write(os.path.join(gdata, "loading_screen", "symbols", "symbol128_alpha.tga"), "logo")
        shutil.rmtree(os.path.join(hlr, "data", "ui"))                  # the mod keeps none of its own
        before = tree_hash(gdata)
        mod = ModData(os.path.join(hlr, "data"))
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        d = os.path.join(hlr, "data")
        self.assertTrue(os.path.isfile(os.path.join(d, "menu", "symbols", "FE_buttons_48", "symbol48_beta.tga")))
        self.assertTrue(os.path.isfile(os.path.join(d, "loading_screen", "symbols", "symbol128_beta.tga")))
        self.assertTrue(os.path.isfile(os.path.join(d, "ui", "units", "beta", "#alpha_general.tga")))
        self.assertEqual(tree_hash(gdata), before)                      # nothing written into the game's data
        restore(ModData(d), backups(ModData(d))[0])
        self.assertFalse(os.path.exists(os.path.join(d, "menu")))
        # a template with _ in its name (greek_cities): its buttons were never renamed, so never copied
        from campaign_editor.clone import renamed
        self.assertEqual(renamed("symbol48_greek_cities_grey.tga", "greek_cities", "athens"),
                         "symbol48_athens_grey.tga")
        self.assertEqual(renamed("romans_julii_logo.tga", "romans_julii", "saba"), "saba_logo.tga")
        self.assertEqual(renamed("gaulsx.tga", "gauls", "new"), "gaulsx.tga")
        # the mod's own copy of a template picture wins over the game's
        write(os.path.join(d, "menu", "symbols", "FE_buttons_48", "symbol48_alpha.tga"), "mod's button")
        plan = build(ModData(d), "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        src = [s_ for s_, d_ in plan.copies if d_.endswith("symbol48_beta.tga")]
        self.assertEqual(src, [os.path.join(d, "menu", "symbols", "FE_buttons_48", "symbol48_alpha.tga")])

    def test_recolour_black_coat_dull_cloak_and_faces(self):
        """A faction in black (the Holy Roman Empire) gets its black coat recoloured where the other factions' copies
        of the card wear other colours; a face stays; a cloak painted duller and darker than the faction's colour
        is taken whole, not in patches; on a symbol (other factions' symbols are other drawings) black is left."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor import recolour as R

        def card(coat, cloak):
            im = Image.new("RGB", (60, 60), (90, 90, 90))       # the coat and cloak a third of it
            d = ImageDraw.Draw(im)
            d.rectangle([4, 4, 18, 30], fill=coat)          # the coat in the faction's first colour
            d.rectangle([22, 4, 36, 30], fill=cloak)        # a cloak in its second colour
            d.rectangle([12, 32, 28, 38], fill=(205, 150, 120))   # a face
            return im
        hre = ((0, 0, 0), (40, 110, 30))                      # black and a green the cloak is painted duller in
        mine = card((15, 15, 15), (70, 100, 55))
        mine.paste((25, 40, 20), (22, 18, 37, 31))           # the cloak's shaded half: dark
        others = [(card((30, 60, 160), (150, 40, 40)), ((30, 60, 160), (150, 40, 40))),
                  (card((200, 170, 20), (40, 40, 150)), ((200, 170, 20), (40, 40, 150))),
                  (card((160, 20, 20), (220, 220, 220)), ((160, 20, 20), (220, 220, 220)))]
        new, share = R.recolour(mine, hre, ((200, 0, 0), (0, 0, 200)), others)
        coat, face = new.getpixel((10, 15)), new.getpixel((20, 35))
        self.assertTrue(coat[0] > 2 * coat[1] and coat[0] > 2 * coat[2] and coat[0] > 8, coat)
        self.assertEqual(face, (205, 150, 120))
        for xy in ((28, 8), (28, 25)):                        # the light and the shaded half of the cloak
            px = new.getpixel(xy)
            self.assertTrue(px[2] > px[1] and px[2] > px[0], (xy, px))
        same, _ = R.recolour(mine, hre, ((200, 0, 0), (0, 0, 200)), others, plain=False)
        self.assertEqual(same.getpixel((10, 15)), (15, 15, 15))

    def test_recolour_gives_the_faction_its_own_far_away_sprites(self):
        """A tester: the recoloured test faction's men were green up close but kept the template's colours far away
        - its model lines named the template's sprite. Recolour gives it its own .spr (copied: it holds no names)
        and pages under its name, recoloured, and points its line at them (Rome's model_sprite here; Medieval II's
        texture line's fourth value the same way)."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import recolour as R
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_model_battle.txt"),
              "type\tspear\nskeleton\tfs_spearman\n"
              "texture\talpha, data/models_unit/textures/spear_alpha.tga\n"
              "texture\tbeta, data/models_unit/textures/spear_alpha.tga\n"
              "model_sprite\talpha, 60.0, data/sprites/alpha_spear_sprite.spr\n"
              "model_sprite\tbeta, 60.0, data/sprites/alpha_spear_sprite.spr\n\n")
        os.makedirs(os.path.join(d, "sprites"), exist_ok=True)
        with open(os.path.join(d, "sprites", "alpha_spear_sprite.spr"), "wb") as fh:
            fh.write(b"\xad\xad\xbf\xde spr")
        im = Image.new("RGBA", (16, 8), (200, 10, 10, 255))
        im.save(os.path.join(d, "sprites", "alpha_spear_sprite_000.tga"))
        os.makedirs(os.path.join(d, "models_unit", "textures"), exist_ok=True)
        im.save(os.path.join(d, "models_unit", "textures", "spear_alpha.tga"))
        cols = {"alpha": ((215, 0, 0), (255, 210, 0)), "beta": ((215, 0, 0), (255, 210, 0))}
        old = R.faction_colours
        R.faction_colours = lambda m: cols
        try:
            mod = ModData(self.root)
            items = [it for it in R.targets(mod, "test", "beta") if it.get("own_sprite")]
            self.assertEqual([os.path.basename(it["own_sprite"]["page"]) for it in items],
                             ["beta_spear_sprite_000.tga"])
            plan = Plan(mod, "recolour", "beta", {})
            R.plan_recolour(plan, items, ((215, 0, 0), (255, 210, 0)), ((0, 160, 60), (240, 240, 0)))
        finally:
            R.faction_colours = old
        sprites = os.path.join(d, "sprites")
        self.assertEqual(plan.binaries[os.path.join(sprites, "beta_spear_sprite.spr")], b"\xad\xad\xbf\xde spr")
        self.assertIn(os.path.join(sprites, "beta_spear_sprite_000.tga"), plan.binaries)
        text = "\n".join(plan.files[os.path.join(d, "descr_model_battle.txt")].texts())
        self.assertIn("model_sprite\tbeta, 60.0, data/sprites/beta_spear_sprite.spr", text)
        self.assertIn("model_sprite\talpha, 60.0, data/sprites/alpha_spear_sprite.spr", text)  # the template's stays

    def test_recolour_faction_pictures(self):
        """A unit card in the faction's red / yellow next to another faction's blue / white copy: the red and yellow
        parts take the new colours, the brown horse (near red, but the same in both copies and duller) stays;
        written as a TGA of the same depth with a backup, Restore gives the bytes back."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import recolour as R
        d = os.path.join(self.root, "data")
        cols = {"alpha": ((215, 0, 0), (255, 210, 0)), "slave": ((0, 60, 180), (240, 240, 240))}

        def card(c1, c2):
            im = Image.new("RGBA", (40, 30), (0, 0, 0, 0))
            for x in range(40):
                for y in range(30):
                    im.putpixel((x, y), (c1 if x < 8 else c2 if x < 16 else (120, 80, 50)) + (255,))
            return im
        for f, (a, b) in (("alpha", ((200, 10, 10), (250, 200, 20))), ("slave", ((10, 60, 170), (235, 235, 235)))):
            os.makedirs(os.path.join(d, "ui", "units", f), exist_ok=True)
            card(a, b).save(os.path.join(d, "ui", "units", f, "#spear.tga"))
        mod = ModData(self.root)
        R.faction_colours = lambda m: cols                     # the mini mod's factions have no colour lines
        try:
            # Medieval II's siege engine of its own (the carroccio), not its normal map nor another faction's
            sd = os.path.join(d, "siege_engines", "textures")
            os.makedirs(sd)
            for n in ("great_bell_tower_alpha.texture", "great_bell_tower_alpha_normal.texture",
                      "great_bell_tower_slave.texture"):
                open(os.path.join(sd, n), "wb").close()
            engines = [os.path.basename(it["path"]) for it in R.targets(mod, "test", "alpha")
                       if it["label"].startswith("siege engine")]
            self.assertEqual(engines, ["great_bell_tower_alpha.texture"])
            items = [it for it in R.targets(mod, "test", "alpha") if it["path"].endswith("#spear.tga")]
            self.assertEqual(len(items), 1)
            self.assertEqual(len(items[0]["others"]), 1)
            path = items[0]["path"]
            with open(path, "rb") as fh:
                before = fh.read()
            plan = Plan(mod, "recolour", "recolour_alpha", {})
            R.plan_recolour(plan, items, cols["alpha"], ((20, 120, 40), (240, 240, 240)))
            plan.apply()
            im = Image.open(path).convert("RGB")
            r, g, b = im.getpixel((5, 5))
            self.assertTrue(g > r and g > b)                       # red -> green
            r, g, b = im.getpixel((12, 5))
            self.assertTrue(min(r, g, b) > 200)                    # yellow -> white-ish
            self.assertEqual(im.getpixel((30, 5)), (120, 80, 50))  # the horse stays
            restore(ModData(self.root), backups(ModData(self.root))[0])
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), before)
        finally:
            import importlib
            importlib.reload(R)

    def test_recolour_keeps_what_all_factions_share(self):
        """A banner nearly all in the faction's red, with a bronze (orange-red) star that every faction's banner has:
        the field changes, the star stays - even though most of the picture differs between the factions."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import recolour as R

        def banner(field):
            im = Image.new("RGBA", (40, 40), field + (255,))
            for x in range(30, 38):
                for y in range(30, 38):
                    im.putpixel((x, y), (190, 90, 40, 255))          # bronze: near red in hue
            return im
        mine = banner((200, 20, 20))
        others = [(banner((20, 140, 30)), ((20, 140, 30), (240, 240, 240))),
                  (banner((30, 50, 170)), ((30, 50, 170), (240, 240, 240))),
                  (banner((230, 230, 230)), ((230, 230, 230), (0, 0, 0)))]
        new, share = R.recolour(mine, ((200, 20, 20), (0, 0, 0)), ((30, 60, 180), (240, 240, 240)), others)
        r, g, b, a = new.getpixel((5, 5))
        self.assertTrue(b > r)                                        # the field: blue now
        self.assertEqual(new.getpixel((33, 33)), (190, 90, 40, 255))  # the star: as it was

    def test_medieval2_faction_logo_moves_to_its_own_page(self):
        """M2EX (sprite_format xml): FACTION_LOGO_ALPHA already carries alpha's name and slave borrows it. Replacing
        alpha's logo moves that sprite to a page of alpha's own; slave first gets FACTION_LOGO_SLAVE with the old
        picture - one definition of each name, slave's picture unchanged; Restore gives every file back."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        from unittest import mock
        from campaign_editor import symbols as SY
        from campaign_editor.factionart import image_tga
        d = os.path.join(self.root, "data")
        sm = SM.replace("culture\t\teastern\n", "culture\t\teastern\nlogo_index\t\tFACTION_LOGO_ALPHA\n", 1)
        sm = sm.replace("culture\t\tbarbarian\n", "culture\t\tbarbarian\nlogo_index\t\tFACTION_LOGO_ALPHA\n", 1)
        write(os.path.join(d, "descr_sm_factions.txt"), sm)
        write(os.path.join(d, "descr_caps_ex.txt"), "sprite_format  xml\n")
        write(os.path.join(d, "ui", "strategy.sd.xml"), '<sprite_definitions version="7">\n'
              '  <page file="stratpage_02.tga" w="128" h="128">\n'
              '    <sprite name="FACTION_LOGO_ALPHA" x="0" y="0" w="68" h="76" alpha="1"/>\n'
              '    <sprite name="OTHER" x="68" y="0" w="10" h="10" alpha="1"/>\n  </page>\n</sprite_definitions>\n')
        os.makedirs(os.path.join(d, "ui", "southern_european", "interface"))
        with open(os.path.join(d, "ui", "southern_european", "interface", "stratpage_02.tga"), "wb") as fh:
            fh.write(image_tga(Image.new("RGBA", (128, 128), (0, 0, 200, 255))))
        before = tree_hash(self.root)
        with mock.patch.object(SY, "rome", lambda m: False):
            mod = ModData(self.root)
            self.assertEqual([e["rel"] for e in SY.entries(mod, "alpha")], [SY.LOGO])
            plan = Plan(mod, "t", "t", {})
            self.assertEqual(SY.own_logo(plan, "alpha", SY.LOGO, Image.new("RGBA", (40, 40), (220, 0, 0, 255))),
                             "FACTION_LOGO_ALPHA")
            plan.apply()
            mod = ModData(self.root)
            xml = open(os.path.join(d, "ui", "strategy.sd.xml")).read()
            self.assertEqual(xml.count('name="FACTION_LOGO_ALPHA"'), 1)
            self.assertEqual(xml.count('name="FACTION_LOGO_SLAVE"'), 1)
            self.assertIn('name="OTHER"', xml)
            self.assertTrue(SY.logo_of(mod, "alpha", SY.LOGO)["own"])
            self.assertEqual(SY.logo_of(mod, "slave", SY.LOGO)["name"], "FACTION_LOGO_SLAVE")
            self.assertGreater(SY.logo_image(mod, "alpha", SY.LOGO).getpixel((30, 30))[0], 180)
            self.assertEqual(SY.logo_image(mod, "slave", SY.LOGO).getpixel((30, 30))[:3], (0, 0, 200))
            self.assertEqual(SY.logo_image(mod, "alpha", SY.LOGO).size, (68, 76))
            restore(mod, backups(mod)[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith("CampaignEditor_backups")}
        self.assertEqual(after, before)

    def test_same_length_texture_name_for_a_cas_copy(self):
        """A texture name baked into a .cas model is rewritten in place: the copy's name keeps the length."""
        from campaign_editor.factionart import _same_length_name
        self.assertEqual(_same_length_name("#banner_symbol_england", "england", "normans"), "#banner_symbol_normans")
        self.assertEqual(len(_same_length_name("#banner_symbol_england", "england", "pisa")), 22)
        self.assertEqual(len(_same_length_name("#banner_symbol_milan", "milan", "papal_states")), 20)

    def test_factions_that_appear_later_emergent_shadow_split(self):
        """A new faction that appears later starts dead (no towns, no characters, only money), nonplayable; the
        header words of descr_sm_factions go in pairs; an event brings an emergent one in; a template's own dead
        words / ties never come along to a faction that starts on the map; Check finds broken pairs; Restore byte
        for byte."""
        from campaign_editor import emergence as E
        before = tree_hash(self.root)
        d = os.path.join(self.root, "data")
        camp = os.path.join(d, "world", "maps", "campaign", "test")
        write(os.path.join(camp, "descr_events.txt"), "; events\n\nevent\thistoric\tfirst\ndate\t2\n")
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "slavs", {"start": {
            "way": "event", "date": "5 summer", "region": "B_R", "re_emergent": True, "denari": 2000,
            "regions": [], "leader": None, "playable": True}})
        sp = mod.campaign_file("test", "descr_strat.txt")
        s = Strat(plan.files[sp])
        fb = s.faction("slavs")
        self.assertEqual((fb.settlements, fb.characters), ([], []))
        head = [l.strip() for l in s.lines[fb.start:fb.end] if l.strip() and not l.startswith(";")]
        self.assertEqual(head[:4], ["faction\tslavs, balanced smith", "dead_until_resurrected", "re_emergent",
                                    "denari\t2000"])
        self.assertIn("slavs", [n for _, n in s.nonplayable["items"]])
        self.assertNotIn("slavs", [n for _, n in s.playable["items"]])
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(E.way_of(mod, "slavs"), ("event", None))
        ev = E.emergent_events(mod, "test")["slavs"]
        self.assertEqual((ev["date"], ev["region"]), ("5 summer", "B_R"))
        faults, notes = E.problems(mod, "test")
        self.assertEqual(faults, [])
        # the games' own factions that come by an event are not re_emergent (BI's slavs, romano_british)
        self.assertEqual(len(notes), 1)
        self.assertIn("marked re_emergent", notes[0])
        # rising in a faction's town: Rome with REX killed it as the campaign loaded and crashed (a tester)
        evp = os.path.join(camp, "descr_events.txt")
        with open(evp) as fh:
            text = fh.read()
        write(evp, text.replace("region\tB_R", "region\tA_R"))
        faults, _ = E.problems(ModData(self.root), "test")
        self.assertTrue(any("rises in A_R, a town of alpha" in f for f in faults), faults)
        write(evp, text)
        # the editor offers only the rebels' regions and refuses a faction's own
        self.assertEqual(E.rising_regions(mod, "test"), ["B_R"])
        with self.assertRaises(ValueError) as cm:
            E.apply(Plan(mod, "later", "slavs", {}), "test", "slavs", "event", date="6 summer", region="A_R")
        self.assertIn("A_R is held by alpha", str(cm.exception))
        # plain Rome takes no shadow / split-off faction (a test mod crashed at the end of a turn) - only BI does
        self.assertEqual(E.ways_for(mod), ("map", "event"))
        with self.assertRaises(ValueError) as cm:
            E.apply(Plan(mod, "later", "alpha", {}), "test", "slavs", "shadow", of="alpha")
        self.assertIn("only Barbarian Invasion", str(cm.exception))
        self.addCleanup(setattr, E, "ways_for", E.ways_for)
        E.ways_for = lambda m: E.WAYS                          # the rest as on Barbarian Invasion
        # the shadow of alpha: both header lines; a clone of the dead faction starts plain and alive
        plan = Plan(mod, "later", "alpha", {})
        E.apply(plan, "test", "slavs", "shadow", of="alpha", re_emergent=True)
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(E.way_of(mod, "slavs"), ("shadow", "alpha"))
        self.assertEqual(E.ties(mod)["alpha"], {"shadowed_by": "slavs"})
        self.assertNotIn("slavs", E.emergent_events(mod, "test"))
        self.assertEqual(E.problems(mod, "test"), ([], []))
        with self.assertRaises(ValueError):           # one shadow per faction
            E.set_way(Plan(mod, "x", "y", {}), "slave", "shadow", "alpha")
        plan = build(mod, "test", "slavs", "venedi", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        s = Strat(plan.files[sp])
        txt = "\n".join(s.lines[s.faction("venedi").start:s.faction("venedi").end])
        self.assertNotIn("dead_until_resurrected", txt)
        sm = "\n".join(plan.files[mod.file("sm_factions")].texts())
        self.assertIn("faction\t\tvenedi\n", sm + "\n")
        # broken pair: Check says so; making it a faction on the map again takes every word away
        smf = mod.file("sm_factions")
        with open(smf, encoding="latin-1", newline="") as fh:
            write(smf, fh.read().replace("\r\n", "\n").replace(", shadowed_by slavs", ""))
        mod = ModData(self.root)
        self.assertTrue(any("go in pairs" in x for x in E.problems(mod, "test")[0]))
        plan = Plan(mod, "later", "slavs", {})
        E.apply(plan, "test", "slavs", "map")
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(E.later_rows(mod, "test"), [])
        for b in backups(mod):
            restore(mod, b)
        write(smf, SM)
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith("CampaignEditor_backups")}
        before["data/world/maps/campaign/test/descr_events.txt"] = after.get(
            "data/world/maps/campaign/test/descr_events.txt")
        self.assertEqual(before, after)

    def test_one_town_population_and_owner(self):
        """The town window's writes (masstown.apply): the population line, the town handed to another faction (the
        whole block moves, edit.map_changes); towns() reads the population and the garrison's units; Restore exact."""
        from campaign_editor import masstown as MT
        before = tree_hash(self.root)
        mod = ModData(self.root)
        t = next(x for x in MT.towns(mod, "test") if x["region"] == "B_R")
        self.assertEqual((t["population"], t["owner"], t["unit_names"]), (800, "slave", ["rebel spear"]))
        plan = Plan(mod, "town", "B_R", {})
        MT.apply(plan, "test", {"population": {"B_R": 1500}, "owners": {"B_R": "alpha"}})
        with self.assertRaises(ValueError):
            MT.apply(Plan(mod, "town", "B_R", {}), "test", {"population": {"B_R": 0}})
        # more people than the level holds: the game stops reading descr_strat there (a tester's test mod lost the
        # rebels' garrisons and the diplomacy) - cut to the level's range with a warning, or the level follows
        from campaign_editor.buildings import pop_range, level_for_population
        level = t.get("level") or "town"
        hi = pop_range(level)[1]
        cut = Plan(mod, "town", "B_R", {})
        MT.apply(cut, "test", {"population": {"B_R": hi + 1000}})
        self.assertTrue(any("too high for a" in w[1] for w in cut.warnings), cut.warnings)
        self.assertIn("population %d" % hi, "\n".join(cut.edit(mod.campaign_file("test", "descr_strat.txt")).texts()))
        grow = Plan(mod, "town", "B_R", {})
        MT.apply(grow, "test", {"population": {"B_R": hi + 1000}, "level_follows": True})
        text = "\n".join(grow.edit(mod.campaign_file("test", "descr_strat.txt")).texts())
        self.assertIn("level %s" % level_for_population(hi + 1000), text)
        self.assertIn("population %d" % (hi + 1000), text)
        self.assertFalse(any("too high" in w[1] for w in grow.warnings))
        plan.apply()
        mod = ModData(self.root)
        t = next(x for x in MT.towns(mod, "test") if x["region"] == "B_R")
        self.assertEqual((t["population"], t["owner"]), (1500, "alpha"))
        restore(mod, backups(mod)[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith("CampaignEditor_backups")}
        self.assertEqual(before, after)

    def test_garrison_only_what_the_town_recruits(self):
        """A drawn garrison holds only what the town's own buildings recruit for its owner (the user: no catapult in
        a village without a siege workshop); a town recruiting none of the pool gets the cheapest units."""
        from campaign_editor import masstown as MT
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"),
              "building barracks\n{\n    levels militia_barracks\n    {\n"
              "        militia_barracks requires factions { alpha, }\n        {\n            capability\n            {\n"
              "                recruit \"alpha spear\" 0 requires factions { alpha, }\n"
              "                recruit \"beta spear\" 0 requires factions { beta, }\n"
              "            }\n            construction 1\n            cost 100\n            settlement_min town\n"
              "            upgrades\n            {\n            }\n        }\n    }\n}\n")
        mod = ModData(self.root)
        pool = [("alpha spear", 100), ("catapult", 300), ("peasants", 50), ("levy", 60), ("knights", 200)]
        town = {"owner": "alpha", "culture": "eastern", "buildings": [("barracks", "militia_barracks")]}
        self.assertEqual(MT.recruitable_here(mod, town), {"alpha spear"})
        self.assertEqual(MT.town_pool(mod, town, pool), [("alpha spear", 100)])
        bare = dict(town, buildings=[])
        self.assertEqual(MT.town_pool(mod, bare, pool), [("peasants", 50), ("levy", 60)])
        self.assertEqual(MT.town_pool(mod, bare, []), [])

    def test_rebel_towns_draw_from_their_rebel_type(self):
        """A rebel town's garrison pool is its region's rebel type (descr_rebel_factions - what the game raises there),
        the nearest rebel armies only without one; units per town by level as the mod's own towns have them."""
        from campaign_editor import masstown as MT
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_rebel_factions.txt"),
              "rebel_type\t\tRebels\ncategory\t\tpeasant_revolt\nchance\t\t\t10\nunit\t\t\trebel spear\n"
              "unit\t\t\tno such unit\n")
        mod = ModData(self.root)
        self.assertEqual(MT.rebel_types(mod), {"Rebels": ["rebel spear", "no such unit"]})
        self.assertEqual([t for t, _ in MT.rebel_pool(mod, "test", "B_R")], ["rebel spear"])
        sizes = MT.level_sizes(mod, "test")
        self.assertEqual(sizes["town"], 1)                               # B_R: a town held by 1 rebel unit
        self.assertEqual(sizes["city"], MT.VANILLA_SIZES["rome"]["city"])    # no rebel city: vanilla's median

    def test_new_faction_keeps_the_templates_ai_label_and_purse(self):
        """Medieval II: the template's block header (ai_label - the campaign AI's rule set, denari_kings_purse - its
        money every turn) comes along to the new faction; the treasury is the one picked."""
        d = os.path.join(self.root, "data")
        sp = os.path.join(d, "world", "maps", "campaign", "test", "descr_strat.txt")
        text = open(sp).read().replace("faction\talpha, balanced smith\ndenari\t1000\n",
                                       "faction\talpha, balanced smith\nai_label\t\tcatholic\ndenari\t1000\n"
                                       "denari_kings_purse\t1500\n", 1)
        self.assertIn("ai_label", text)
        write(sp, text)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"},
                                                              "denari": 3000}})
        lines = [l.strip() for l in plan.files[sp].texts()]
        i = lines.index("faction\tbeta, balanced smith")
        head = lines[i:i + 5]
        self.assertIn("denari\t3000", head)
        self.assertIn("ai_label\t\tcatholic", head)
        self.assertIn("denari_kings_purse\t1500", head)
        self.assertEqual(sum(1 for l in head if l.startswith("denari\t")), 1)
        self.assertTrue(any("seldom sends its leader" in n for _, n in plan.notes))

    def test_raze_settlement_native_addon_for_medieval2(self):
        """The Medieval II add-on is a Squirrel module like Rome's Sack (M2EX runs the same squi scripts): settings
        written as Squirrel ([] lists), the file in script/modules; an older version's Lua copy in the mod's
        eopData/eopScripts and its loader line are taken out (the mod's own lines kept, byte for byte), so the
        capture scroll never shows two buttons; Restore gives everything back."""
        from campaign_editor import addons as A
        a = A.by_key("raze_settlement")
        self.assertEqual(a.file, "raze_settlement.nut")
        self.assertTrue(a.fits("medieval2"))
        self.assertFalse(a.fits("rome"))
        self.assertFalse(any(x.file.lower().endswith(".lua") for x in A.library()))
        text = a.template()
        got = A.read_settings(a, text)
        self.assertEqual(got["RAZE_WHO"], "player")
        self.assertEqual(got["RAZE_KEEP_CHAINS"],
                         ["core_building", "core_castle_building", "hinterland_roads", "hinterland_castle_roads"])
        self.assertEqual(A.render(a, text, got), text)
        # the script is the Sack's engine code with Medieval II's names: Sack is the scroll's middle button there
        self.assertIn('"loot_settlement_sack_button"', text)
        self.assertNotIn("loot_settlement_enslave_button", text)
        self.assertIn('local PREFIX = "[RAZE] "', text)
        mod = ModData(self.root)
        edb = os.path.join(self.root, "data", "export_descr_buildings.txt")
        write(edb, "building core_building\n{\n}\nbuilding core_castle_building\n{\n}\n"
                   "building hinterland_roads\n{\n}\nbuilding hinterland_castle_roads\n{\n}\n")
        self.assertFalse(A.check(a, got, mod))
        # a town is never emptied: 600 people at least (the script's floor is the editor's)
        self.assertEqual(got["RAZE_PEOPLE_LEFT"], A.MIN_PEOPLE)
        self.assertIn("local RAZE_MIN_PEOPLE = %d" % A.MIN_PEOPLE, text)
        self.assertTrue(any("600 at least" in x for x in A.check(a, dict(got, RAZE_PEOPLE_LEFT=100), mod)))
        # the governor's chains stay whatever the list says: the script itself never tears down core_*
        self.assertFalse(A.check(a, dict(got, RAZE_KEEP_CHAINS=["hinterland_roads"]), mod))
        self.assertIn('chain.indexof("core") != 0', text)
        folder = os.path.join(self.root, "eopData", "eopScripts")
        entry = os.path.join(folder, "luaPluginScript.lua")
        own = b"-- the mod's own\r\nfunction onPluginLoad() end\r\n"
        entry_before = own + b'do dofile("x/raze_settlement.lua") end  -- added by RTW & M2TW Campaign Editor: ' \
            b'raze_settlement.lua\n'
        os.makedirs(folder, exist_ok=True)
        with open(entry, "wb") as f:
            f.write(entry_before)
        old = os.path.join(folder, "raze_settlement.lua")
        write(old, "-- Raze Settlement, the older Lua\n")
        vals = dict(got, RAZE_WHO="list", RAZE_FACTIONS=["alpha"], RAZE_GOLD_PER_BUILDING=500, RAZE_PEOPLE_LEFT=900)
        plan = Plan(mod, "addon", "raze", {})
        dst = A.plan_install(plan, a, vals, mod)
        self.assertEqual(dst, os.path.join(self.root, "script", "modules", "raze_settlement.nut"))
        bdir = plan.apply()
        new = open(dst).read()
        self.assertIn('local RAZE_FACTIONS = ["alpha"]', new)
        self.assertIn("local RAZE_GOLD_PER_BUILDING = 500", new)
        self.assertEqual(A.installed(mod, a)["RAZE_PEOPLE_LEFT"], 900)
        self.assertFalse(os.path.exists(old))
        with open(entry, "rb") as f:
            self.assertEqual(f.read(), own)
        restore(mod, bdir)
        self.assertTrue(os.path.exists(old))
        with open(entry, "rb") as f:
            self.assertEqual(f.read(), entry_before)
        self.assertIsNone(A.installed(mod, a))
        # taking it out takes the older Lua out too
        p2 = Plan(mod, "addon", "raze_off", {})
        A.plan_remove(p2, a, mod)
        p2.apply()
        self.assertFalse(os.path.exists(old))
        with open(entry, "rb") as f:
            self.assertEqual(f.read(), own)

    def test_avoid_growth_addon_for_both_games(self):
        """Avoid Growth: one script for REX and M2EX (the same engine scripts); the game's own tick pieces, the
        ceilings kept in the saved game (persistent), held on every settlement turn; its settings written and read
        back, a move left (below 0) allowed for the tick's place; put into the game's script/modules and taken out."""
        from campaign_editor import addons as A
        a = A.by_key("avoid_growth")
        self.assertTrue(a.fits("rome") and a.fits("medieval2"))
        text = a.template()
        for part in ('"PLAIN_CHECKBOX_BG"', '"PLAIN_CHECKBOX_TICK"', '"CHECKBOX_BG"', '"TICK_GADGET"',
                     '"verdana_sml"', '"BEVEL_TL"', "AG_M2_ROW", "root.persistent", '"SettlementTurnStart"',
                     "settlementScroll", "rawdelete"):
            self.assertIn(part, text)
        # the game's small tick pieces first (the scroll's own Auto-manage / Construction / Recruitment ticks)
        self.assertLess(text.index('"PLAIN_CHECKBOX_BG"'), text.index('["CHECKBOX_BG"'))
        self.assertNotIn("delete ", text.replace("rawdelete", ""))         # the engines forbid 'delete'
        got = A.read_settings(a, text)
        self.assertEqual(A.render(a, text, got), text)
        self.assertFalse(got["AG_SHOW_CAP"])                               # the ceiling goes in the tooltip
        self.assertIn("{cap}", got["AG_TIP_ON"])
        new = dict(got, AG_OFFSET_X=-12, AG_LABEL="Stay small", AG_SHOW_CAP=True, AG_TIP_ON="Max {cap}")
        self.assertEqual(A.read_settings(a, A.render(a, text, new)), new)
        self.assertFalse(A.check(a, new))
        self.assertTrue(A.check(a, dict(got, AG_OFFSET_Y="up")))
        mod = ModData(self.root)
        plan = Plan(mod, "addon", "growth", {})
        dst = A.plan_install(plan, a, new, mod)
        self.assertEqual(dst, os.path.join(self.root, "script", "modules", "avoid_growth.nut"))
        bdir = plan.apply()
        self.assertEqual(A.installed(mod, a)["AG_OFFSET_X"], -12)
        restore(mod, bdir)
        self.assertIsNone(A.installed(mod, a))

    def test_module_builder(self):
        """The Module builder: a recipe of WHEN / IF / DO blocks -> a REX / M2EX script that is an ordinary add-on
        (its settings and their words found by from_script, money below 0 allowed, the recipe read back out of it, no
        names left in the engine's root table); its problems in plain words (a block the event brings nothing for, a
        name the mod lacks, a built-in add-on's name, a number that is none); kept in the add-ons list, never over an
        add-on the builder did not make; put in, its message goes into the mod's text/custom_messages.txt (the
        games' encoding) and Restore takes both back; the examples fit any mod."""
        import codecs
        import re as _re
        from unittest import mock
        from campaign_editor import addons as AD, modbuilder as MB
        mod = ModData(self.root)
        r = MB.example("Help when broke")
        self.assertTrue(MB.plain_words(r).startswith(
            "When a faction's turn starts, if the faction is the player and its money is below 0: the faction gets "
            "3000 denarii"))
        text = MB.script(r)
        self.assertEqual(MB.recipe_of(text), r)
        for part in ('"FactionTurnStart"', "mb_add_money", "display_message", "help_when_broke_msg1",
                     'local PREFIX = "[HELP_WHEN_BROKE] "'):
            self.assertIn(part, text)
        self.assertNotIn("delete ", text.replace("rawdelete", ""))         # the engines forbid 'delete'
        self.assertFalse(_re.search(r"^\s*function\s", text, _re.M))      # local functions only
        self.assertFalse(_re.search(r"^\s*::\w+\s*<-", text, _re.M))
        lib = os.path.join(self.root, "addons")
        with mock.patch.object(AD, "library_dir", return_value=lib):
            a = MB.save(r)
            self.assertEqual((a.key, a.title, a.game, a.own), ("help_when_broke", "Help when broke", "both", True))
            kinds = {s.var: (s.kind, s.label, s.signed) for s in a.settings}
            self.assertEqual(kinds, {"MB_ON": ("bool", "Module on", False),
                                     "MB_ONCE": ("bool", "Only once in a campaign", False),
                                     "MB_AMOUNT_OF_THE_LOAN": ("int", "Amount of the loan", True)})
            values = AD.read_settings(a, a.template())
            self.assertEqual(values["MB_AMOUNT_OF_THE_LOAN"], 3000)
            self.assertEqual(AD.check(a, dict(values, MB_AMOUNT_OF_THE_LOAN=-500)), [])   # a debt is allowed
            self.assertEqual([x[1]["title"] for x in MB.my_modules()], ["Help when broke"])
            with open(os.path.join(lib, "border_tolls.nut"), "w") as fh:
                fh.write("local TOLL = 1\n")
            with self.assertRaises(ValueError):                         # someone's own add-on is never overwritten
                MB.save(dict(r, title="Border Tolls"))
            plan = Plan(mod, "addon", a.key, {})
            AD.plan_install(plan, a, dict(values, MB_AMOUNT_OF_THE_LOAN=2500), mod)
            bdir = plan.apply()
        dst = os.path.join(self.root, "script", "modules", "help_when_broke.nut")
        with open(dst, encoding="utf-8") as fh:
            self.assertIn("local MB_AMOUNT_OF_THE_LOAN = 2500", fh.read())
        msgs = os.path.join(self.root, "data", "text", "custom_messages.txt")
        with open(msgs, "rb") as fh:
            raw = fh.read()
        self.assertTrue(raw.startswith(codecs.BOM_UTF16_LE))                # like the mod's other string tables
        words = raw[2:].decode("utf-16-le")
        self.assertIn("{help_when_broke_msg1}\tA loan", words)
        self.assertIn("{help_when_broke_msg1_body}\tThe treasury was empty", words)
        restore(mod, bdir)
        self.assertFalse(os.path.exists(dst) or os.path.exists(msgs))
        # problems in plain words
        bad = dict(r, dos=[MB.item("do", "people", amount=500)])
        self.assertTrue(any("brings no town" in p for p in MB.problems(bad)))
        self.assertTrue(any("built-in" in p for p in MB.problems(dict(r, title="Sack Settlement"))))
        odd = dict(r, ifs=[MB.item("if", "money", op="<", v="lots")])
        self.assertTrue(any("whole number" in p for p in MB.problems(odd)))
        unit = MB.new_recipe("Free spears")
        unit.update(when="town_turn", dos=[MB.item("do", "units", unit="no such unit", count=1)])
        self.assertEqual(MB.problems(unit), [])                             # no mod: names not checked
        self.assertEqual(MB.problems(unit, mod), ["DO 1 (new units in the town): no such unit is not in this mod"])
        with self.assertRaises(ValueError):
            MB.script(bad)
        # the examples, made for this mod: all but the two whose names it lacks (a building chain, a trait) are ready
        ready = [x["title"] for x in MB.EXAMPLES if not MB.problems(MB.fit_to_mod(x, mod), mod)]
        self.assertEqual(len(ready), len(MB.EXAMPLES) - 2)
        for title in ready:
            MB.script(MB.fit_to_mod(MB.example(title), mod))

    def test_module_builder_takes_every_line_of_the_engines(self):
        """The engines' own lists (dump_docudemon) read: console usages split at the first ':' outside <> / [],
        docudemon blocks with their fields; the catalogue the editor carries has both engines (a module for both games
        offers what both have); a game's documentation folder adds the descriptions. A module line is checked by the
        list: an unknown name, the wrong letter case, a block of campaign_script.txt, a console command of battles, a
        condition needing what the event does not bring - in plain words; good lines become the engines' calls."""
        from campaign_editor import enginedocs as ED, modbuilder as MB
        con = ED.parse("console", "## listing ##\r\n\r\ngive_trait\r\n  Availability: campaign\r\n  Usage: give_trait "
                                  "<charactername> <trait name> <opt:level>: gives a trait\r\n\r\nfire\r\n  "
                                  "Availability: battle\r\n  Usage: fire : shoots\r\n")
        self.assertEqual([(e.name, e.params, e.desc, e.runnable()) for e in con],
                         [("give_trait", "<charactername> <trait name> <opt:level>", "gives a trait", True),
                          ("fire", "", "shoots", False)])
        cond = ED.parse("conditions", "intro\n---------------------------------------------------\nIdentifier:"
                                      "              SettlementName\nTrigger requirements:    settlement\nParameters:"
                                      "              settlement name\nSample use:              SettlementName Rome\n"
                                      "Description:             For scripting\nBattle or Strat:         Either\n"
                                      "Implemented:             Yes\n---------------------------------------------------\n")
        self.assertEqual((cond[0].name, cond[0].needs, cond[0].sample, cond[0].where), (
            "SettlementName", ["settlement"], "SettlementName Rome", "Either"))
        b = ED.builtin()
        for engine in ED.ENGINES:
            self.assertGreater(len(b[engine]["console"]), 100)
            self.assertGreater(len(b[engine]["conditions"]), 250)
        both = ED.catalogue("both")
        self.assertTrue(all(n in b["rex"]["console"] and n in b["m2ex"]["console"] for n in both["console"]))
        self.assertIn("kill_character", both["console"])
        # what an event brings, by the engines' own lists: REX's town taken has no old owner, REX has no
        # SettlementUpgraded at all
        town_taken, grows = MB.EVENT["town_taken"], MB.EVENT["town_grows"]
        self.assertEqual(MB.event_subjects(town_taken, "both"), ("faction", "settlement", "character"))
        self.assertEqual(MB.event_subjects(town_taken, "medieval2"), ("faction", "settlement", "character", "target"))
        self.assertIsNone(MB.event_subjects(grows, "both"))
        self.assertEqual(MB.event_subjects(grows, "medieval2"), ("faction", "settlement"))
        g = MB.new_recipe("Grow")
        g.update(when="town_grows", dos=[MB.item("do", "money", amount=10)])
        self.assertIn("make the module for Medieval II only", MB.problems(g)[0])
        self.assertEqual(MB.problems(dict(g, game="medieval2")), [])
        old = dict(g, when="town_taken", dos=[MB.item("do", "money", amount=10, to="old")])
        self.assertTrue(any("has no old owner" in x for x in MB.problems(old)))
        self.assertEqual(MB.problems(dict(old, game="medieval2")), [])
        # the game's own documentation: its descriptions
        doc = os.path.join(self.root, "documentation")
        write(os.path.join(doc, "console_commands.txt"), "kill_character\n  Availability: campaign\n  Usage: "
                                                         "kill_character <character_name> : kills a character\n")
        mod = ModData(self.root)
        self.assertEqual(ED.doc_dir(mod), doc)
        self.assertEqual(ED.catalogue("both", mod)["console"]["kill_character"].desc, "kills a character")
        r = MB.new_recipe("Lines")
        r.update(when="faction_turn", ifs=[MB.item("if", "game", line="not I_TurnNumber < 3")],
                 dos=[MB.item("do", "console", text='kill_character "{general}" Battle'),
                      MB.item("do", "script", text="set_event_counter mb_seen 1")])
        self.assertEqual(MB.problems(r), [])
        text = MB.script(r)
        self.assertIn('mb_condition(mb_fill("not I_TurnNumber < 3", c))', text)
        self.assertIn('mb_script_line(mb_fill("set_event_counter mb_seen 1", c))', text)
        self.assertIn("::game.evaluateCondition(line)", text)
        self.assertIn("::game.runScriptCommand(verb, rest)", text)

        def why(kind, line, when="faction_turn"):
            return MB.line_problems(kind, line, dict(r, when=when), MB.EVENT[when])
        self.assertIn("not one of the console commands", why("cmd:console", "no_such_thing 1")[0])
        self.assertIn("write it add_money", why("cmd:console", "Add_money 5")[0])
        self.assertIn("flow of campaign_script.txt", why("cmd:commands", "if I_TurnNumber > 3")[0])
        self.assertIn("only in battle", why("cmd:console", "force_battle_victory")[0])
        self.assertIn("needs settlement", why("cond", "SettlementName London")[0])
        self.assertEqual(why("cond", "SettlementName London", "town_taken"), [])
        self.assertEqual(why("cond", "not FactionType england"), [])
        # the parameters as fields, and the line put back together
        kinds = lambda kind, name: [(p.kind, p.optional) for p in ED.params_of(both[kind][name])]
        self.assertEqual(kinds("console", "kill_character"), [("characters", False), ("text", True)])
        self.assertEqual(kinds("console", "diplomatic_stance"), [("factions", False), ("factions", False),
                                                                 ("choice", False)])
        m2_stance = ED.params_of(b["m2ex"]["console"]["diplomatic_stance"])[2]     # M2EX of 2026-10-04
        self.assertEqual((m2_stance.kind, m2_stance.choices[-2:]), ("choice", ["protectorate_of", "client_of"]))
        self.assertEqual(ED.params_of(b["m2ex"]["console"]["test_message"])[0].kind, "text")   # a name | all
        self.assertEqual(kinds("console", "create_unit")[:2], [("towns|characters", False), ("units", False)])
        self.assertEqual(kinds("conditions", "Trait"), [("traits", False), ("logic", False), ("number", False)])
        self.assertEqual(kinds("commands", "give_settlement"), [("factions", False), ("towns", False)])
        self.assertEqual(ED.compose(both["console"]["kill_character"], ["{general}", "Battle"]),
                         'kill_character "{general}" Battle')
        self.assertEqual(ED.compose(both["conditions"]["Trait"], ["GoodCommander", ">=", "2"], True),
                         "not Trait GoodCommander >= 2")
        self.assertEqual(ED.compose(both["console"]["add_money"], ["", "500"]), "add_money 500")
        self.assertEqual(ED.split_line('kill_character "Gaius Julius" Battle'), ["kill_character", "Gaius Julius",
                                                                                  "Battle"])
        # any event of the engines as WHEN; numbers kept between turns
        ev = MB.event_of("ev:SettlementTurnEnd")
        self.assertEqual((ev.engine, ev.subjects), ("SettlementTurnEnd", ("faction", "settlement")))
        self.assertIsNone(MB.event_of("ev:"))
        self.assertIsNone(MB.event_of("no such thing"))
        only_m2 = next(n for n in ED.builtin()["m2ex"]["events"] if n not in ED.builtin()["rex"]["events"])
        n = MB.new_recipe("Count")
        n.update(when="ev:SettlementTurnEnd", ifs=[MB.item("if", "counter", name="seen_{town}", op="<", v=3)],
                 dos=[MB.item("do", "counter_add", v=1, name="seen_{town}"),
                      MB.item("do", "counter_set", v=0, name="reset")])
        self.assertEqual(MB.problems(n), [])
        self.assertIn("the number 'seen_{town}' is below 3", MB.plain_words(n))
        text = MB.script(n)
        self.assertIn('mb_listen("SettlementTurnEnd", mb_run)', text)
        self.assertIn('mb_set_counter(mb_fill("seen_{town}", c), mb_counter(mb_fill("seen_{town}", c)) + 1)', text)
        self.assertIn("::game.setEventCounter(name, v)", text)
        self.assertTrue(any("name the number" in x for x in MB.problems(dict(
            n, dos=[MB.item("do", "counter_set", v=1, name="two words")]))))
        self.assertTrue(any("make the module for Medieval II only" in x for x in MB.problems(dict(
            n, when="ev:" + only_m2, ifs=[], dos=[MB.item("do", "counter_set", v=1, name="x")]))))

    def test_faction_emblem_one_picture_everywhere(self):
        """One emblem picture -> every emblem picture in its own size; mouse over brighter, greyed out grey, selected
        with a glow round the new shape - by the amounts the old pictures show."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import emblem as E
        d = tempfile.mkdtemp()

        def disc(size, colour, glow=None):
            im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            if glow:
                dr.ellipse((0, 0, size - 1, size - 1), fill=glow + (160,))
            dr.ellipse((4, 4, size - 5, size - 5), fill=colour + (255,))
            return im
        olds = {"": disc(40, (100, 20, 20)), "_roll": disc(40, (140, 28, 28)),
                "_select": disc(40, (140, 28, 28), (230, 190, 40)), "_grey": disc(40, (40, 40, 40))}
        pics = []
        for v, im in olds.items():
            path = os.path.join(d, "symbol48_alpha%s.tga" % v)
            im.save(path)
            label = "big campaign-menu button" + {"": "", "_roll": " (mouse over)", "_select": " (selected)",
                                                  "_grey": " (greyed out)"}[v]
            pics.append({"path": path, "rel": "menu/symbols/fe_buttons_48/symbol48_alpha%s.tga" % v,
                         "label": label, "size": (40, 40, 32)})
        logo = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        ImageDraw.Draw(logo).rectangle((10, 10, 117, 117), fill=(20, 60, 160, 255))
        pics.append({"path": os.path.join(d, "symbol128_alpha.tga"), "rel": "loading_screen/symbols/symbol128_alpha.tga",
                     "label": "loading-screen logo", "size": (128, 128, 32)})
        logo.save(pics[-1]["path"])
        self.assertEqual(len(E.emblem_pictures(pics)), 5)
        src = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(src).rectangle((0, 0, 63, 63), fill=(20, 120, 40, 255))
        made = E.build(src, pics)
        self.assertEqual(made[pics[4]["rel"]].size, (128, 128))
        n, roll, sel, grey = (made[p["rel"]] for p in pics[:4])
        self.assertEqual(n.size, (40, 40))
        self.assertGreater(roll.getpixel((20, 20))[1], n.getpixel((20, 20))[1])       # brighter
        r, g, b, a = grey.getpixel((20, 20))
        self.assertTrue(r == g == b)                                                    # grey
        self.assertEqual(n.getpixel((1, 1))[3], 0)                                      # the margin stays clear
        self.assertGreater(sel.getpixel((2, 20))[3], 0)                                 # the glow round it
        self.assertGreater(sel.getpixel((2, 20))[0], sel.getpixel((2, 20))[2])          # gold, as the old one

    def test_new_faction_header_lines_in_the_games_order(self):
        """A clone's first lines follow the template's in the games' order (every vanilla descr_strat: superfaction /
        ai_label, dead_until_resurrected, re_emergent, denari, denari_kings_purse) - 0.29.1 put denari first and the
        games then started the new faction without its towns ('Faction Destroyed' on turn 1, the test mod in both
        games). A faction made dead later goes after ai_label too; a mod already written so is found by Check mod
        files and put right by Load's set-up fix (only those lines move)."""
        from campaign_editor import gamefix
        from campaign_editor.check import check_mod
        from campaign_editor.strat import headers_out_of_order
        d = os.path.join(self.root, "data")
        sp = os.path.join(d, "world", "maps", "campaign", "test", "descr_strat.txt")
        with open(sp) as fh:
            text = fh.read()
        self.assertIn("faction\talpha, balanced smith\n", text)
        text = text.replace("faction\talpha, balanced smith\n",
                            "faction\talpha, balanced smith\nsuperfaction slave\nai_label\tcatholic\n", 1)
        with open(sp, "w") as fh:
            fh.write(text)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"},
                                                              "denari": 777}})
        s = Strat(plan.files[sp])
        fb = s.faction("beta")
        head = [l.strip() for l in s.lines[fb.start + 1:fb.end] if l.strip() and not l.startswith(";")][:3]
        self.assertEqual([h.split()[0] for h in head], ["superfaction", "ai_label", "denari"])
        self.assertEqual(headers_out_of_order(plan.files[sp]), [])
        later = build(ModData(self.root), "test", "alpha", "gamma", {"start": {
            "way": "event", "date": "5 summer", "region": "B_R", "re_emergent": True, "regions": [], "leader": None}})
        s = Strat(later.files[sp])
        fb = s.faction("gamma")
        head = [l.strip().split()[0] for l in s.lines[fb.start + 1:fb.end] if l.strip() and not l.startswith(";")]
        self.assertEqual(head[:5], ["superfaction", "ai_label", "dead_until_resurrected", "re_emergent", "denari"])
        plan.apply()
        # a mod written by 0.29.1 / 0.29.2: denari first - found and put right
        with open(sp) as fh:
            text = fh.read()
        broken = text.replace("faction\tbeta, balanced smith\nsuperfaction slave\nai_label\tcatholic\ndenari\t777",
                              "faction\tbeta, balanced smith\ndenari\t777\nsuperfaction slave\nai_label\tcatholic", 1)
        self.assertNotEqual(broken, text)
        with open(sp, "w") as fh:
            fh.write(broken)
        mod = ModData(self.root)
        self.assertIn("beta: its first lines", check_mod(mod, "test"))
        found = [p for p in gamefix.problems(mod) if p["id"] == "faction_header"]
        self.assertEqual([n for n, _ in found[0]["blocks"]], ["beta"])
        gamefix.fix_plan(mod, found).apply()
        with open(sp) as fh:
            self.assertEqual(fh.read(), text)

    def test_medieval2_victory_parts_start_with_hold_regions(self):
        """Medieval II reads a victory block's parts in a fixed order starting with hold_regions (all 20 vanilla
        blocks: 'short_campaign hold_regions ;Jerusalem_Province'): written with an empty list it stays
        'short_campaign hold_regions' with take_regions below - 0.29.2 wrote 'short_campaign take_regions 20', the
        game stopped reading there and the player's faction had no victory conditions (the test mod). Check mod
        files finds such a line on Medieval II, Load puts it right."""
        from campaign_editor import gamefix, wincond
        cond = {"long": dict(wincond._empty(), hold=["A_R"], take=45),
                "short": dict(wincond._empty(), take=20, outlive=["slave"])}
        got = wincond.lines("alpha", cond, True)
        self.assertEqual(got, ["alpha", "hold_regions A_R", "take_regions 45", "short_campaign hold_regions",
                               "take_regions 20", "outlive slave"])
        self.assertEqual(wincond.lines("alpha", cond, False)[3], "short_campaign take_regions 20")   # Rome as before
        d = os.path.join(self.root, "data")
        os.makedirs(os.path.join(d, "unit_models"))                     # a Medieval II mod
        wp = os.path.join(d, "world", "maps", "campaign", "test", "descr_win_conditions.txt")
        with open(wp, "w") as fh:
            fh.write("alpha\nhold_regions A_R\ntake_regions 45\nshort_campaign take_regions 20\noutlive slave\n\n"
                     "slave\nhold_regions A_R\ntake_regions 5\nshort_campaign take_regions 2\noutlive alpha\n")
        mod = ModData(self.root)
        found = [p for p in gamefix.problems(mod) if p["id"] == "short_campaign"]
        self.assertEqual([p["line"] for p in found], [3, 9])
        gamefix.fix_plan(mod, found).apply()
        with open(wp) as fh:
            self.assertEqual(fh.read(), "alpha\nhold_regions A_R\ntake_regions 45\nshort_campaign hold_regions\n"
                                        "take_regions 20\noutlive slave\n\nslave\nhold_regions A_R\ntake_regions 5\n"
                                        "short_campaign hold_regions\ntake_regions 2\noutlive alpha\n")
        self.assertEqual([p for p in gamefix.problems(ModData(self.root)) if p["id"] == "short_campaign"], [])

    def test_author_test_mod_steps_and_report(self):
        """Tools > Test mod (selftest.py): every step names what it does and what to look at in the game, both
        written with the factions it picked; the report says each step's status, its files, notes and new problems.
        (The whole run is tried on both games' real files by check-scripts/testmod.py.)"""
        from campaign_editor import selftest as ST
        names = {"template": "alpha", "edited": "beta", "other": "gamma", "new": "ce_test", "later": "ce_test_later",
                 "split": "ce_test_split", "shadow": "ce_test_shadow", "foreign": "delta",
                 "addon": "Sack Settlement (Rome, REX)"}
        self.assertGreaterEqual(len(ST.STEPS), 30)
        for title, see, fn in ST.STEPS:
            self.assertTrue(title.format(**names) and callable(fn))
            see.format_map(ST._Names(names, {"near": "Town A", "far": "Town B"}))    # towns the steps pick
        with self.assertRaises(ValueError):                 # the mini-mod has two factions, the test needs three
            ST.Ctx(os.path.join(self.root, "data"), "test", self.root)
        text = ST.report("/x/CE_Test/data", "test", names, [
            {"step": "One", "see": "look", "status": "OK", "files": ["a.txt"], "warnings": ["a note"],
             "new_problems": []},
            {"step": "Two", "see": "", "status": "FAILED", "files": [], "warnings": [], "new_problems": ["broken"],
             "error": "ValueError: no"}])
        self.assertIn("1 of 2 steps fine", text)
        self.assertIn(" 1. [OK] One", text)
        self.assertIn("NEW PROBLEM in Check mod files: broken", text)
        self.assertIn("ValueError: no", text)

    def test_medieval2_banner_symbol_stays_on_the_cloth(self):
        """A pennant whose cloth is no rectangle (Medieval II's L-shaped mini_infantry): the symbol's place is a
        square of cloth, not the middle of the box round it (it ran past the cloth's edge)."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import banners_m2 as M
        cloth = Image.new("L", (128, 96), 0)
        cloth.paste(255, (0, 0, 128, 30))                  # the long top streamer
        cloth.paste(255, (0, 0, 50, 96))                   # the part down the pole
        blank = Image.new("RGBA", cloth.size, (210, 210, 210, 255))
        sheet = M.Sheet(blank, cloth, cloth, [(0, 0, 128, 96)], 1)
        (x0, y0, x1, y1), = M.symbol_boxes(sheet)
        self.assertTrue(x1 - x0 >= 20 and x1 - x0 == y1 - y0)
        self.assertTrue(all(cloth.getpixel((x, y)) == 255 for x in range(x0, x1) for y in range(y0, y1)))
        full = M.Sheet(blank, cloth, Image.new("L", cloth.size, 255), [(0, 0, 128, 96)], 1)
        self.assertEqual(M.symbol_boxes(full), [(40, 16, 88, 64)])       # a whole rectangle: as before

    def test_medieval2_pennants_every_look_and_no_seam(self):
        """Medieval II's small pennants have four looks on the sheet (the mesh shows the first; the others a quarter
        across and half down - the game shows them on other units): every look gets the made design, found where the
        sheets' see-through shape repeats the first's; a banner's long thin slit (the cavalry banner's, no mesh shows
        it) is cloth, dyed with the rest - it went through the symbol as a dark seam; an edge's short notches stay."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import banners_m2 as M
        W, H = 128, 64
        alpha = Image.new("L", (W, H), 0)
        for x0, y0 in ((64, 0), (96, 0), (64, 32), (96, 32)):     # one pennant shape, four times
            alpha.paste(255, (x0 + 2, y0 + 2, x0 + 24, y0 + 20))
        alpha.paste(255, (0, 0, 60, 64))                          # a big banner on the left
        cloth = Image.new("L", (W, H), 0)
        cloth.paste(255, (66, 2, 88, 20))                         # the mesh shows the first look only
        cloth.paste(255, (4, 4, 56, 60))
        cloth.paste(0, (20, 30, 56, 33))                          # the slit: 36 long, 3 high, open at the edge
        for y in range(6, 58, 8):
            cloth.paste(0, (4, y, 7, y + 4))                      # the hoist's ties: short notches
        panels = [(4, 4, 56, 60), (66, 2, 88, 20)]
        mini = Image.new("L", (W, H), 0)
        mini.paste(255, (66, 2, 88, 20))
        copies = M.variant_copies(panels, cloth, alpha, [mini])
        self.assertEqual(sorted(copies), [(1, 0, 32), (1, 32, 0), (1, 32, 32)])
        self.assertEqual(M.variant_copies(panels, cloth, alpha, []), [])     # not a pennant: no copies
        filled = M.fill_slits(cloth, panels)
        self.assertEqual(filled.getpixel((40, 31)), 255)                     # the slit is cloth
        self.assertEqual(filled.getpixel((5, 8)), 0)                         # a tie stays out
        blank = Image.merge("RGBA", (Image.new("L", (W, H), 210),) * 3 + (alpha,))
        for i, dx, dy in copies:
            x0, y0, x1, y1 = panels[i]
            filled.paste(filled.crop((x0, y0, x1, y1)), (x0 + dx, y0 + dy))
        sheet = M.Sheet(blank, Image.new("L", (W, H), 210), filled, panels, 3, copies)
        made = M.paint(sheet, [(200, 0, 0), (0, 0, 200)], None, None, "two stripes, upright")
        for dx, dy in ((0, 0), (32, 0), (0, 32), (32, 32)):
            self.assertEqual(made.getpixel((68 + dx, 10 + dy))[:3], made.getpixel((68, 10))[:3])
            self.assertEqual(made.getpixel((86 + dx, 10 + dy))[:3], made.getpixel((86, 10))[:3])
        self.assertGreater(made.getpixel((68, 10))[0], 150)                  # red half ...
        self.assertGreater(made.getpixel((86, 10))[2], 150)                  # ... blue half, in every look
        self.assertGreater(made.getpixel((50, 31))[2], 150)                  # the slit dyed like the cloth round it
        self.assertEqual(M.template_picture(sheet).getpixel((98, 2)), (140, 140, 140, 255))   # looks outlined

    def test_medieval2_white_banner_from_the_faction_sheets(self):
        """Medieval II has no white banner: the template is the per-pixel median of the mod's faction banner
        sheets (each faction's heraldry elsewhere, so it vanishes; the folds every sheet shares stay; what is
        alike in them all - the pole - kept in its colour); then dyed in a pattern per panel, the symbol on it, or
        the player's drawing in its place. The pole every banner mesh shows is no cloth."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow")
        import math
        from campaign_editor import banners as B
        from campaign_editor import banners_m2 as M
        W, H = 192, 96
        heraldry = [(200, 30, 30), (30, 60, 200), (40, 160, 40), (220, 200, 40), (120, 40, 140)]
        sheets = []
        for k, col in enumerate(heraldry):
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            px = im.load()
            for y in range(H):
                for x in range(W):
                    if y >= 84:
                        px[x, y] = (120, 80, 40, 255)                         # the pole: alike in every sheet
                    elif (8 <= x < 88 and 4 <= y < 80) or (104 <= x < 184 and 4 <= y < 60):
                        fold = 0.8 + 0.2 * math.sin(x / 5.0)                   # the folds every sheet shares
                        c = col if not (20 + 12 * k <= x < 30 + 12 * k) else (250, 250, 250)   # a stripe of its own
                        px[x, y] = tuple(int(v * fold) for v in c) + (255,)
            sheets.append(im)
        sheet = M.make_sheet(sheets)
        self.assertEqual(sheet.count, 5)
        self.assertEqual(sorted(sheet.panels), [(8, 0, 88, 80), (104, 0, 184, 64)])
        r, g, b, a = sheet.blank.getpixel((50, 40))
        self.assertTrue(r == g == b and r > 120)                               # white, the heraldry gone
        self.assertEqual(sheet.blank.getpixel((50, 90)), (120, 80, 40, 255))  # the pole kept as it is
        self.assertLess(sheet.shade.getpixel((47, 40)), sheet.shade.getpixel((39, 40)))   # the folds kept
        self.assertEqual(sheet.blank.getpixel((96, 30))[3], 0)                 # the gap stays clear
        made = M.paint(sheet, [(200, 0, 0), (0, 0, 200)], None, None, "two stripes, upright")
        self.assertGreater(made.getpixel((20, 40))[0], 120)                    # left half of a panel red
        self.assertGreater(made.getpixel((80, 40))[2], 120)                    # right half blue
        self.assertGreater(made.getpixel((110, 30))[0], 120)                   # each panel on its own
        self.assertEqual(made.getpixel((50, 90)), (120, 80, 40, 255))
        sym = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        ImageDraw.Draw(sym).rectangle((0, 0, 19, 19), fill=(20, 200, 40, 255))
        kit = M.Kit(sheet)
        own = kit.make({"colours": [(200, 0, 0)], "pattern": "plain"}, sym)
        # see-through only where the template is (the faction's own sheet, once replaced by another picture, gave
        # its alpha to the new banner and the poles went see-through in the game - a tester's test mod)
        self.assertEqual(own.getchannel("A").tobytes(), sheet.blank.getchannel("A").tobytes())
        self.assertEqual(own.getpixel((50, 90))[3], 255)                       # the pole stays solid
        bx = M.symbol_boxes(sheet)[0]
        r, g, b, a = own.getpixel(((bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2))
        self.assertGreater(g, r)                                               # the symbol on the cloth
        self.assertEqual(kit.make({"colours": [(200, 0, 0)], "no_symbol": True}, sym).getpixel(
            ((bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2))[1], 0)
        self.assertEqual(kit.template({}).getpixel((8, 0)), (220, 30, 30, 255))    # panels outlined to draw on
        d = tempfile.mkdtemp()
        drawn = os.path.join(d, "mine.png")
        Image.new("RGBA", (W // 2, H // 2), (10, 20, 230, 255)).save(drawn)
        mine = kit.make({"drawing": drawn, "no_symbol": True})
        self.assertEqual(mine.size, (W, H))
        self.assertEqual(mine.getpixel((50, 40))[:3], (10, 20, 230))
        self.assertEqual(mine.getpixel((96, 30))[3], 0)                        # the sheet's outline kept
        # the meshes: what one mesh alone shows is cloth; the pole both hang on is not
        a_mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(a_mask).rectangle((8, 4, 87, 95), fill=255)
        b_mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(b_mask).rectangle((104, 4, 183, 59), fill=255)
        ImageDraw.Draw(b_mask).rectangle((8, 84, 183, 95), fill=255)
        cloth, panels = M.own_cloth([a_mask, b_mask], Image.new("L", (W, H), 0), (W, H))
        self.assertEqual(cloth.getpixel((50, 90)), 0)
        self.assertEqual(cloth.getpixel((50, 40)), 255)
        self.assertEqual(len(panels), 2)
        self.assertEqual(B.banner_at(panels, 50, 40), panels.index(next(p for p in panels if p[0] < 50)))
        self.assertIsNone(B.banner_at(panels, 95, 2))
        # Rome's banners take the drawing the same way, and make() without one is the dyed banner as before
        blank = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(blank).rectangle((4, 4, 59, 40), fill=(220, 220, 220, 255))
        s = {"colours": [(30, 60, 200)], "pattern": "plain", "no_symbol": True}
        self.assertEqual(B.make(blank, s).tobytes(), B.paint(blank, [(30, 60, 200)], None).tobytes())
        r = B.make(blank, dict(s, drawing=drawn))
        self.assertEqual(r.getpixel((20, 20))[:3], (10, 20, 230))
        self.assertEqual(r.getpixel((20, 50))[3], 0)

    def test_medieval2_banner_sheet_written_as_its_own_texture(self):
        """A Medieval II banner sheet shared by two factions, replaced for one (the Banner... window, Replace (its
        own copy)): the faction gets a .texture of its own - the 48-byte head kept, the DDS inside of the old size -
        and its descr_banners_new.xml line pointed at it; the other faction's untouched; Restore byte for byte."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        import io
        from campaign_editor import factionart as FA
        from campaign_editor.edit import edit
        from campaign_editor.recolour import read_picture
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_banners_new.xml"),
              '<BannerDB>\n   <FactionBanners>\n      <Banner Name="main_spear" MainMesh="data\\banners\\x.mesh">\n'
              '         <Textures>\n'
              '            <Texture Faction="Alpha" DiffuseMap="banners\\textures\\Faction_banner_alpha.texture"/>\n'
              '            <Texture Faction="Slave" DiffuseMap="banners\\textures\\Faction_banner_alpha.texture"/>\n'
              '         </Textures>\n      </Banner>\n   </FactionBanners>\n</BannerDB>\n')
        buf = io.BytesIO()
        Image.new("RGBA", (64, 32), (200, 30, 30, 255)).save(buf, format="DDS")
        tex = os.path.join(d, "banners", "textures", "Faction_banner_alpha.texture")
        os.makedirs(os.path.dirname(tex))
        head = bytes(range(48))
        with open(tex, "wb") as fh:
            fh.write(head + buf.getvalue())
        self.assertEqual(FA.picture_info(tex)[:2], (64, 32))
        mod = ModData(self.root)
        x = next(e for e in FA.extra_pictures(mod, "slave") if e["kind"] == "banner")
        png = os.path.join(self.root, "new.png")
        Image.new("RGBA", (32, 16), (20, 40, 220, 255)).save(png)
        before = tree_hash(self.root)
        plan = edit(mod, "test", "slave", {"art": {"banners/textures/Faction_banner_alpha.texture": {
            "src": png, "extra": [x["kind"], x["ref"]]}}})
        plan.apply()
        own = os.path.join(d, "banners", "textures", "Faction_banner_slave.texture")
        with open(own, "rb") as fh:
            raw = fh.read()
        self.assertEqual(raw[:48], head)
        self.assertEqual(raw[48:52], b"DDS ")
        im = read_picture(own)
        self.assertEqual(im.size, (64, 32))
        self.assertGreater(im.getpixel((10, 10))[2], 150)
        self.assertGreater(read_picture(tex).getpixel((10, 10))[0], 150)      # Alpha's own untouched
        with open(os.path.join(d, "descr_banners_new.xml"), encoding="latin-1") as fh:
            xml = fh.read()
        self.assertIn('Faction="Slave" DiffuseMap="banners\\textures\\Faction_banner_slave.texture"', xml)
        self.assertIn('Faction="Alpha" DiffuseMap="banners\\textures\\Faction_banner_alpha.texture"', xml)
        restore(ModData(self.root), backups(ModData(self.root))[0])
        after = {k: v for k, v in tree_hash(self.root).items()
                 if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_a_factions_pictures_are_not_a_longer_named_factions(self):
        """A faction whose name another faction's name holds (empire_east / empire_east_rebels, the test mod's
        ce_test / ce_test_later): the other's pictures are not its own - its emblem wrote over ce_test_later's
        symbol128 / symbol24 pictures, a clone of empire_east copied empire_east_rebels' as its own."""
        from campaign_editor.clone import _token_hit, longer_names
        names = ["empire_east", "empire_east_rebels", "ce_test", "ce_test_later", "romans_julii"]
        self.assertEqual(longer_names(names, "empire_east"), ["empire_east_rebels"])
        self.assertEqual(longer_names(names, "romans_julii"), [])
        east = longer_names(names, "empire_east")
        self.assertTrue(_token_hit("symbol24_empire_east_grey.tga", "empire_east", east))
        self.assertFalse(_token_hit("symbol24_empire_east_rebels_grey.tga", "empire_east", east))
        self.assertTrue(_token_hit("symbol24_empire_east_rebels_grey.tga", "empire_east_rebels",
                                   longer_names(names, "empire_east_rebels")))
        self.assertFalse(_token_hit("symbol128_ce_test_later.tga", "ce_test", longer_names(names, "ce_test")))
        self.assertTrue(_token_hit("symbol128_ce_test.tga", "ce_test", longer_names(names, "ce_test")))
        # ... and the Art tab's list (Faction emblem and Recolour read it) on a mod with both factions
        try:
            from PIL import Image
        except ImportError:
            return
        from campaign_editor import factionart as FA
        data = os.path.join(tempfile.mkdtemp(), "data")
        os.makedirs(os.path.join(data, "menu", "symbols", "FE_buttons_24"))
        os.makedirs(os.path.join(data, "world", "maps", "campaign", "imperial_campaign"))
        with open(os.path.join(data, "descr_sm_factions.txt"), "w") as fh:
            # the later faction's header carries more words: its loading logo line is still its own
            fh.write("faction ce_test\nculture roman\nloading_logo loading_screen/symbols/symbol128_ce_test.tga\n"
                     "faction ce_test_later, shadowing ce_test\nculture roman\n"
                     "loading_logo loading_screen/symbols/symbol128_ce_test_later.tga\n")
        for n in ("symbol24_ce_test.tga", "symbol24_ce_test_later.tga"):
            Image.new("RGBA", (24, 24)).save(os.path.join(data, "menu", "symbols", "FE_buttons_24", n))
        os.makedirs(os.path.join(data, "loading_screen", "symbols"))
        for n in ("symbol128_ce_test.tga", "symbol128_ce_test_later.tga"):
            Image.new("RGBA", (128, 128)).save(os.path.join(data, "loading_screen", "symbols", n))
        got = sorted(e["rel"] for e in FA.faction_pictures(ModData(data), "imperial_campaign", "ce_test"))
        self.assertEqual(got, ["loading_screen/symbols/symbol128_ce_test.tga",
                               "menu/symbols/FE_buttons_24/symbol24_ce_test.tga"])
        shutil.rmtree(os.path.dirname(data))

    def test_recolour_gives_a_shared_battle_texture_a_copy_of_its_own(self):
        """A clone wears its template's battle textures (and a mod in mods/ the game's): Recolour skipped them, so a
        new faction's men stayed in the template's colours in battle (a tester's test mod, both games). The
        faction now gets its own copy in the mod and its model line points at it; the template's stays."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import recolour as RC, models as M
        d = os.path.join(self.root, "data")
        tex = os.path.join(d, "models_unit", "textures")
        os.makedirs(tex, exist_ok=True)
        im = Image.new("RGB", (32, 32), (200, 20, 20))
        for x in range(32):
            im.putpixel((x, 0), (90, 90, 90))
        im.save(os.path.join(tex, "spearman_alpha.tga"))
        write(os.path.join(d, "descr_model_battle.txt"),
              "type\t\tspearman\nskeleton\tfs_spearman\nindiv_range\t40\n"
              "texture\t\talpha, data/models_unit/textures/spearman_alpha.tga\n"
              "texture\t\tbeta, data/models_unit/textures/spearman_alpha.tga\n"
              "model_flexi\tdata/models_unit/spearman.cas, max\n\n")
        mod = ModData(self.root)
        items = [t for t in RC.targets(mod, "test", "beta") if t["group"] == "unit textures"]
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["own_tex"] and not items[0]["skip"])
        with open(os.path.join(tex, "spearman_alpha.tga"), "rb") as fh:
            before = fh.read()
        plan = Plan(mod, "recolour", "beta", {})
        RC.plan_recolour(plan, items, ((200, 20, 20), None), ((20, 160, 40), None), "alpha")
        plan.apply()
        mod = ModData(self.root)
        info = M.catalogue(mod)["spearman"]
        self.assertEqual(info.textures["beta"], "data/models_unit/textures/spearman_beta.tga")
        self.assertEqual(info.textures["alpha"], "data/models_unit/textures/spearman_alpha.tga")
        with open(os.path.join(tex, "spearman_alpha.tga"), "rb") as fh:
            self.assertEqual(fh.read(), before)
        own = Image.open(os.path.join(tex, "spearman_beta.tga")).convert("RGB")
        self.assertGreater(own.getpixel((5, 5))[1], own.getpixel((5, 5))[0])       # green now
        self.assertEqual(own.getpixel((5, 0)), (90, 90, 90))                       # the grey kept
        restore(mod, backups(mod)[0])
        self.assertFalse(os.path.exists(os.path.join(tex, "spearman_beta.tga")))

    def test_recolour_copies_of_two_textures_never_share_a_name(self):
        """Two battle textures that differ only in the wearer's word (EN_Peasant_Padded_england / _france) both became
        ..._<faction>: the one written last dressed every model of the other (a tester: the peasants of a new
        faction wore France's blue in battle). Each copy keeps a name of its own."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import recolour as RC, models as M
        d = os.path.join(self.root, "data")
        tex = os.path.join(d, "models_unit", "textures")
        os.makedirs(tex, exist_ok=True)
        Image.new("RGB", (32, 32), (200, 20, 20)).save(os.path.join(tex, "peasant_alpha.tga"))
        im = Image.new("RGB", (32, 32), (200, 20, 20))
        for x in range(16, 32):
            for y in range(32):
                im.putpixel((x, y), (20, 40, 210))
        im.save(os.path.join(tex, "peasant_gamma.tga"))
        write(os.path.join(d, "descr_model_battle.txt"),
              "type\t\tspearman\nskeleton\tfs_spearman\nindiv_range\t40\n"
              "texture\t\talpha, data/models_unit/textures/peasant_alpha.tga\n"
              "texture\t\tbeta, data/models_unit/textures/peasant_alpha.tga\n"
              "model_flexi\tdata/models_unit/spearman.cas, max\n\n"
              "type\t\tarcher\nskeleton\tfs_archer\nindiv_range\t40\n"
              "texture\t\tgamma, data/models_unit/textures/peasant_gamma.tga\n"
              "texture\t\tbeta, data/models_unit/textures/peasant_gamma.tga\n"
              "model_flexi\tdata/models_unit/archer.cas, max\n\n")
        mod = ModData(self.root)
        items = [t for t in RC.targets(mod, "test", "beta") if t["group"] == "unit textures"]
        refs = sorted(t["own_tex"]["ref"] for t in items)        # the first keeps the plain name, the other its source's
        self.assertEqual(refs, ["data/models_unit/textures/peasant_alpha_beta.tga",
                                "data/models_unit/textures/peasant_beta.tga"])
        # each is painted in the colours of the faction it is named after: gamma's picture is recoloured from
        # gamma's colours, whatever the window's 'from' (alpha) says; colours picked by hand ('*') count for all
        self.assertEqual(sorted(t["painted_by"] for t in items), ["alpha", "gamma"])
        g_item = next(t for t in items if t["painted_by"] == "gamma")
        self.assertEqual(RC.item_source(dict(g_item, painted=((20, 40, 210), None)), "red", "alpha"),
                         ((20, 40, 210), None))
        self.assertEqual(RC.item_source(dict(g_item, painted=((20, 40, 210), None)), "red", "*"), "red")
        self.assertEqual(RC.item_source(dict(g_item, painted=((20, 40, 210), None)), "red", "gamma"), "red")
        plan = Plan(mod, "recolour", "beta", {})
        RC.plan_recolour(plan, items, ((200, 20, 20), None), ((20, 160, 40), None), "alpha")
        plan.apply()
        info = M.catalogue(ModData(self.root))
        self.assertEqual(info["spearman"].textures["beta"], "data/models_unit/textures/peasant_alpha_beta.tga")
        self.assertEqual(info["archer"].textures["beta"], "data/models_unit/textures/peasant_beta.tga")
        a = Image.open(os.path.join(tex, "peasant_alpha_beta.tga")).convert("RGB").getpixel((24, 5))
        g = Image.open(os.path.join(tex, "peasant_beta.tga")).convert("RGB").getpixel((24, 5))
        self.assertGreater(a[1], a[2])                    # the spearman's copy is alpha's, recoloured green
        self.assertGreater(g[2], g[1])                    # the archer's keeps gamma's blue half
        restore(mod, backups(mod)[0])

    def test_recolour_reads_a_game_picture_in_the_games_own_colours(self):
        """A unit given to the faction wears an owner's texture from the game's own data: it is painted in that
        owner's colours of the game's descr_sm_factions, not in what the mod made of them since (a tester's test mod
        gave France purple, so France's blue peasants were not found to recolour)."""
        from campaign_editor import recolour as RC
        game = os.path.join(self.root, "game")
        os.makedirs(os.path.join(game, "mods"))
        write(os.path.join(game, "medieval2.exe"), "x")
        write(os.path.join(game, "data", "descr_sm_factions.txt"), SM)
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "mods", "m", "data"))
        mine = os.path.join(game, "mods", "m", "data", "descr_sm_factions.txt")
        with open(mine) as fh:
            text = fh.read()
        game_cols = RC.faction_colours(ModData(os.path.join(game, "data")))
        alpha = game_cols["alpha"][0]
        write(mine, text.replace("red %d, green %d, blue %d" % alpha, "red 150, green 30, blue 160", 1))
        mod = ModData(os.path.join(game, "mods", "m", "data"))
        self.assertEqual(RC.faction_colours(mod)["alpha"][0], (150, 30, 160))
        self.assertEqual(RC._game_colours(mod)["alpha"][0], alpha)
        self.assertEqual(RC._game_colours(ModData(os.path.join(game, "data"))), {})     # the game itself: none

    def test_delete_a_town_with_its_region(self):
        """Map editor: a town deleted with its region in every file that ties them - its land, town and port
        pixels to the neighbour, its descr_regions block, its settlement and the rebels on its tile, its mercenary
        pools and win conditions; the last town of a living faction, a campaign script naming it and a faction
        rising there are refused; a trait condition naming it is warned about; Restore byte for byte."""
        from campaign_editor import regiondelete as RD
        before = tree_hash(self.root)
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        write(os.path.join(camp, "descr_mercenaries.txt"),
              "pool Both\n\tregions A_R B_R ; both\n\tunit rebel spear exp 0 cost 100 replenish 0.1 - 0.2 max 2 "
              "initial 1\n\npool Only_B\n\tregions B_R\n\tunit rebel spear exp 0 cost 100 replenish 0.1 - 0.2 "
              "max 2 initial 1\n")
        write(os.path.join(camp, "descr_win_conditions.txt"), "alpha\nhold_regions A_R B_R\ntake_regions 10\n")
        write(os.path.join(camp, "campaign_script.txt"), "script\n\tsettlement_flash_start Btown\nend_script\n")
        write(os.path.join(self.root, "data", "export_descr_ancillaries.txt"),
              "Trigger t1\n    WhenToTest CharacterTurnEnd\n    Condition SettlementName Btown\n")
        mod = ModData(self.root)
        self.assertEqual(RD.neighbours(mod, "test", "B_R")[0][0], "A_R")
        errors, _ = RD.problems(mod, "test", "A_R")
        self.assertTrue(any("last town of alpha" in e for e in errors), errors)
        errors, _ = RD.problems(mod, "test", "B_R")
        self.assertTrue(any("campaign_script.txt names B_R / Btown on line 2" in e for e in errors), errors)
        os.remove(os.path.join(camp, "campaign_script.txt"))
        mod = ModData(self.root)
        errors, warns = RD.problems(mod, "test", "B_R")
        self.assertEqual(errors, [])
        self.assertTrue(any("export_descr_ancillaries.txt names" in w for w in warns), warns)
        plan = Plan(mod, "delete", "B_R", {})
        self.assertEqual(RD.delete(plan, "test", "B_R"), "A_R")
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(sorted(mod.regions("test")), ["A_R"])
        img = mod.region_map("test")
        self.assertEqual(sorted(img.colours()), [(0, 0, 0), (255, 0, 0)])        # all A_R's, its town
        self.assertEqual(mod.city_tiles("test"), {"A_R": (1, 1)})
        s = Strat(mod.load(mod.campaign_file("test", "descr_strat.txt")))
        self.assertEqual(s.owners(), {"A_R": "alpha"})
        self.assertFalse(any(ch.name == "Grog" for fb in s.factions for ch in fb.characters))   # the garrison went
        with open(os.path.join(camp, "descr_mercenaries.txt")) as fh:
            merc = fh.read()
        self.assertIn("\tregions A_R ; both", merc)
        self.assertNotIn("Only_B", merc)
        with open(os.path.join(camp, "descr_win_conditions.txt")) as fh:
            self.assertIn("hold_regions A_R\n", fh.read())
        restore(mod, backups(mod)[0])
        os.remove(os.path.join(camp, "descr_mercenaries.txt"))
        os.remove(os.path.join(self.root, "data", "export_descr_ancillaries.txt"))
        write(os.path.join(camp, "descr_win_conditions.txt"), "alpha\nhold_regions A_R\ntake_regions 10\n")
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith("CampaignEditor_backups")}
        self.assertEqual(after, before)

    def test_scripts_in_the_game_listed_switched_set_deleted(self):
        """Add-ons > Scripts in the game: every script in the game's script/modules (the engine requires each .nut
        there) - turned off as x.nut.off and on again, its settings written in its own lines, deleted - each with
        a backup, Restore byte for byte."""
        from campaign_editor import scriptmods as SCR
        game = os.path.join(self.root, "game")
        write(os.path.join(game, "medieval2.exe"), "x")
        write(os.path.join(game, "data", "descr_sm_factions.txt"), SM)
        write(os.path.join(game, "script", "main.nut"), "foreach (n in ::scripting.listModules(\"modules\")) {}\n")
        mods = os.path.join(game, "script", "modules")
        write(os.path.join(mods, "tolls.nut"), "// Border Tolls - a toll at every border\n"
              "local TOLL_ON = true\nlocal TOLL_GOLD = 100   // money per crossing\nfunction go() {}\n")
        write(os.path.join(mods, "old.nut.off"), "// Old thing - kept, not run\nlocal OLD_X = 1\n")
        write(os.path.join(mods, "eop.lua"), "-- an older Lua file\n")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "mods", "m", "data"))
        before = tree_hash(game)
        mod = ModData(os.path.join(game, "mods", "m", "data"))
        self.assertEqual(os.path.normcase(SCR.folders(mod)[0][0]), os.path.normcase(mods))
        got = {s.file: s for s in SCR.scripts(mod)}
        self.assertEqual(sorted(got), ["eop.lua", "old.nut", "tolls.nut"])
        t = got["tolls.nut"]
        self.assertTrue(t.on and not got["old.nut"].on and got["eop.lua"].lua)
        self.assertEqual(t.title, "Border Tolls")
        self.assertEqual(t.values, {"TOLL_ON": True, "TOLL_GOLD": 100})
        plan = Plan(t.plan_mod(), "scripts", "tolls", {})
        SCR.plan_switch(plan, t, False)                                   # off: the same bytes as tolls.nut.off
        plan.apply()
        self.assertFalse(os.path.exists(os.path.join(mods, "tolls.nut")))
        self.assertTrue(os.path.exists(os.path.join(mods, "tolls.nut.off")))
        t = {s.file: s for s in SCR.scripts(mod)}["tolls.nut"]
        plan = Plan(t.plan_mod(), "scripts", "tolls", {})
        SCR.plan_switch(plan, t, True)
        plan.apply()
        t = {s.file: s for s in SCR.scripts(mod)}["tolls.nut"]
        plan = Plan(t.plan_mod(), "scripts", "tolls", {})
        self.assertTrue(SCR.plan_settings(plan, t, {"TOLL_ON": True, "TOLL_GOLD": 250}))
        plan.apply()
        with open(os.path.join(mods, "tolls.nut")) as fh:
            self.assertIn("local TOLL_GOLD = 250   // money per crossing", fh.read())
        with self.assertRaises(ValueError):                             # a whole number, 0 or more
            SCR.plan_settings(Plan(t.plan_mod(), "scripts", "tolls", {}), t, {"TOLL_GOLD": -5})
        old = {s.file: s for s in SCR.scripts(mod)}["old.nut"]
        plan = Plan(old.plan_mod(), "scripts", "old", {})
        SCR.plan_delete(plan, old)
        plan.apply()
        self.assertFalse(os.path.exists(os.path.join(mods, "old.nut.off")))
        gm = ModData(os.path.join(game, "data"))
        restore_to(gm, backups(gm)[-1])
        after = {k: v for k, v in tree_hash(game).items() if "CampaignEditor_backups" not in k}
        self.assertEqual(after, before)

    def test_rome_faction_destroyed_picture_for_every_faction(self):
        """Rome: descr_event_images.txt's 'faction_defeated' switch has one case per faction (21 in vanilla); a
        faction past the last case crashed the game when it was destroyed (message_builder_objects.cpp(763), a
        tester's Rome + REX test mod). A new faction adds its case; Check says it; Load fixes an older mod."""
        from campaign_editor import check as CK, eventimages as EI, gamefix as GF
        images = os.path.join(self.root, "data", "descr_event_images.txt")
        case = "\t\t\tcase %d\n\t\t\t{\n\t\t\t\tmovie\t\t center 320 240\tdata/fmv/lose/f%d_eliminated.wmv\n\t\t\t}\n"
        write(images, "faction_defeated\n\ticon\tdiplomacy\n\tformat\n\t{\n\t\ttitle center verdana black\n"
              "\t\tswitch\n\t\t{\n" + "".join(case % (i, i) for i in range(2)) + "\t\t}\n\t}\n\n"
              "faction_defeated_by_player\n\ticon\tdiplomacy\n\tformat use faction_defeated\n")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        self.assertEqual((EI.cases(mod), EI.faction_count(mod)), (2, 2))
        self.assertIsNone(EI.problem(mod))
        plan = build(mod, "test", "alpha", "beta", {
            "display_name": "Betan League", "short_name": "Beta", "adjective": "Betan",
            "start": {"regions": ["B_R"], "leader": {"name": "Boris Alphid", "age": 35}, "denari": 500}})
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual((EI.cases(mod), EI.faction_count(mod)), (3, 3))
        with open(images) as fh:
            text = fh.read()
        self.assertIn("case 2\n\t\t\t{\n\t\t\t\tmovie\t\t center 320 240\tdata/fmv/lose/f1_eliminated.wmv", text)
        self.assertTrue(text.endswith("format use faction_defeated\n"))
        restore_to(mod, backups(mod)[-1])
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if "CampaignEditor_backups" not in k}, before)
        # an older mod with more factions than cases: Check says it, Load offers the fix
        with open(images) as fh:
            write(images, fh.read().replace(case % (1, 1), ""))
        mod = ModData(self.root)
        self.assertIn("crashes when faction 2", EI.problem(mod))
        self.assertIn("faction destroyed", CK.check_mod(mod, "test"))
        found = [p for p in GF.problems(mod) if p["id"] == "faction_defeated"]
        self.assertEqual(len(found), 1)
        GF.fix_plan(mod, found).apply()
        self.assertEqual(EI.cases(ModData(self.root)), 2)

    def test_backup_of_a_game_folder_file_stays_in_the_backup(self):
        """A mod's write that changes a file of the game's folder beside it (an add-on updated in the game's
        script/modules): its backup copy is kept inside the backup's folder ('..' -> '_up'), and Restore takes it
        from there - it was copied outside and Restore refused it (the test mod's 'Scripts in the game' step)."""
        from campaign_editor.plan import stored
        game = os.path.join(self.root, "game")
        write(os.path.join(game, "medieval2.exe"), "x")
        nut = os.path.join(game, "script", "modules", "x.nut")
        write(nut, "local X_ON = true\n")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "mods", "m", "data"))
        mod = ModData(os.path.join(game, "mods", "m", "data"))
        plan = Plan(mod, "scripts", "x", {})
        plan.binary(nut, b"local X_ON = false\n")
        bdir = plan.apply()
        self.assertTrue(os.path.isfile(os.path.join(bdir, stored("../../script/modules/x.nut"))))
        self.assertTrue(os.path.realpath(os.path.join(bdir, stored("../../script/modules/x.nut"))).startswith(
            os.path.realpath(bdir) + os.sep))
        restore_to(mod, bdir)
        with open(nut) as fh:
            self.assertEqual(fh.read(), "local X_ON = true\n")

    def test_scripts_the_test_mod_put_in_are_found_and_taken_out(self):
        """The test mod puts its add-ons into the GAME's script/modules: thrown away with its folder, they stayed
        there. Each carries scriptmods.TEST_MARK at its end (older ones: a ce_test_ name); Scripts in the game finds
        them and takes them all out in one write - anyone else's script stays, Restore gives them back."""
        from campaign_editor import addons as AD, scriptmods as SCR
        game = os.path.join(self.root, "game")
        write(os.path.join(game, "medieval2.exe"), "x")
        write(os.path.join(game, "data", "descr_sm_factions.txt"), SM)
        write(os.path.join(game, "script", "main.nut"), "foreach (n in ::scripting.listModules(\"modules\")) {}\n")
        mods = os.path.join(game, "script", "modules")
        write(os.path.join(mods, "tolls.nut"), "// Border Tolls - a toll at every border\nlocal TOLL_GOLD = 100\n")
        write(os.path.join(mods, "ce_test_engine_lines.nut.off"), "// CE Test engine lines\nfunction go() {}\n")
        shutil.copytree(os.path.join(self.root, "data"), os.path.join(game, "mods", "m", "data"))
        mod = ModData(os.path.join(game, "mods", "m", "data"))
        src = os.path.join(self.root, "growth_like.nut")
        write(src, "// @title Growth like\nlocal GL_ON = true\nfunction go() {}\n")
        with open(src) as fh:
            text = fh.read()
        a = AD.from_script(text, "growth_like.nut", src)
        before = tree_hash(game)
        plan = Plan(mod, "addon", "growth_like", {})
        dst = AD.plan_install(plan, a, AD.read_settings(a, text), mod, mark=SCR.TEST_MARK)
        plan.apply()
        with open(dst) as fh:
            got = fh.read()
        self.assertTrue(got.startswith(text) and got.endswith(SCR.TEST_MARK + "\n"))
        s = {x.file: x for x in SCR.scripts(mod)}["growth_like.nut"]
        self.assertEqual(s.values, {"GL_ON": True})                        # the mark changes no setting
        self.assertEqual(sorted(x.file for x in SCR.test_scripts(mod)), ["ce_test_engine_lines.nut",
                                                                          "growth_like.nut"])
        self.assertEqual(s.kind, "put in by the test mod")
        items = SCR.test_scripts(mod)
        plan = Plan(items[0].plan_mod(), "scripts", "test_mod_scripts", {})
        self.assertEqual(SCR.plan_take_out_test(plan, items), 2)
        plan.apply()
        self.assertEqual([x.file for x in SCR.scripts(mod)], ["tolls.nut"])
        gm = ModData(os.path.join(game, "data"))
        restore_to(gm, backups(gm)[-1])
        self.assertEqual(sorted(x.file for x in SCR.test_scripts(mod)), ["ce_test_engine_lines.nut",
                                                                          "growth_like.nut"])
        self.assertTrue(set(before) <= set(tree_hash(game)))

    def test_medieval2_children_limit_raised_with_the_family(self):
        """Medieval II: descr_campaign_db.xml <max_number_of_children> (4 in vanilla) - a fifth child made the game
        stop reading descr_strat.txt at the family's relative line (a tester's test mod: France's Philip). A tree
        that needs more raises it in the same write; one within it leaves the file alone."""
        from campaign_editor import family as FM
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_campaign_db.xml"), "<campaign_db>\n  <family_tree>\n"
              "    <max_number_of_children uint=\"4\"/>\n  </family_tree>\n</campaign_db>\n")
        mod = ModData(self.root)
        plan = Plan(mod, "family", "alpha", {})
        FM._campaign_db_children(plan, [["Philip", "Bertrada", ["A", "B", "C", "D"]]])
        self.assertEqual(plan.changed_files(), [])
        FM._campaign_db_children(plan, [["Philip", "Bertrada", ["A", "B", "C", "D", "E"]]])
        f = plan.edit(os.path.join(d, "descr_campaign_db.xml"))
        self.assertIn('<max_number_of_children uint="5"/>', "\n".join(f.texts()))

    def test_mod_at_a_glance_for_the_log(self):
        """Every Load writes a short picture of the mod into the log (the author's idea: every report then shows
        what the mod is - its factions, towns, files - without any game file)."""
        from campaign_editor.check import mod_summary
        text = mod_summary(ModData(self.root), "test")
        self.assertIn("Mod at a glance", text)
        for word in ("factions", "regions", "units", "buildings", "own files", "alpha"):
            self.assertIn(word, text)
        self.assertNotIn("not read", text.split("own files")[0].split("map")[0])

    def test_report_leaves_out_logs_it_sent_already(self):
        """The author: a log the program has sent is not sent again - a finished log (the game's) sent unchanged is
        left out (unticked, 'already sent with R-...'), the editor's own log goes only from where the last report
        left off."""
        from campaign_editor import report, settings, log
        saved = (settings._data, settings._path, log._path)
        tmp = tempfile.mkdtemp()
        settings._data, settings._path = {}, (lambda: os.path.join(tmp, "s.json"))
        try:
            ed = os.path.join(tmp, "CampaignEditor.log")
            game = os.path.join(tmp, "system.log.txt")
            write(ed, "old line\n")
            write(game, "game log\n")
            log._path = ed
            files = [(ed, "CampaignEditor.log", "the editor's log"), (game, "system.log.txt", "the game's log")]
            self.assertIsNone(report.already_sent(game))
            report.remember_sent_logs(files, "R-20261003-AAAAAA")
            self.assertEqual(report.already_sent(game), "R-20261003-AAAAAA")
            with open(ed, "a") as fh:
                fh.write("new line\n")
            text = dict(report.contents(files[:1], []))["CampaignEditor.log"]
            self.assertIn("new line", text)
            self.assertNotIn("old line", text)
            self.assertIn("R-20261003-AAAAAA", text)
            with open(game, "a") as fh:                       # the game wrote more: it goes again
                fh.write("more\n")
            os.utime(game, (time.time() + 5, time.time() + 5))
            self.assertIsNone(report.already_sent(game))
        finally:
            settings._data, settings._path, log._path = saved
            shutil.rmtree(tmp, ignore_errors=True)

    def test_banner_symbol_dragged_snapped_and_sized(self):
        """The Banner window moves the symbol with the mouse: its middle snaps to the banner's own grid (quarters,
        eighths, sixteenths) or goes freely, it stays on its banner, the wheel sizes it round its middle."""
        from campaign_editor import banners as B
        ban = (0, 0, 100, 200)
        box = (10, 10, 40, 40)
        self.assertEqual(B.place_box(box, 51, 77, ban, 4), (35, 85, 65, 115))    # middle on (50, 100)
        self.assertEqual(B.place_box(box, 51, 77, ban, 0), (36, 62, 66, 92))     # freely
        self.assertEqual(B.place_box(box, 99, 199, ban), (70, 170, 100, 200))    # kept on the banner
        self.assertEqual(B.scale_box(box, 2, ban)[2:], (60, 60))                 # bigger, still on it
        small = B.scale_box(box, 0.01, ban)
        self.assertEqual(small[2] - small[0], B.MIN_SYMBOL)
        self.assertEqual(B.scale_box((0, 0, 90, 90), 5, ban)[2], 100)            # never wider than the banner
        self.assertEqual(B.banner_at([ban, (20, 20, 40, 40)], 30, 30), 1)        # the smallest under the point
        self.assertIsNone(B.banner_at([ban], 150, 10))
        self.assertEqual(B.grid_lines(ban, 4), ([25.0, 50.0, 75.0], [50.0, 100.0, 150.0]))
        self.assertEqual(B.grid_lines(ban, 0), ([], []))
        self.assertEqual(list(B.GRIDS.values()), [0, 4, 8, 16])

    def test_symbol_painted_on_the_battle_banners(self):
        """The battle banners made from the game's blank white banner: the cloth dyed in the faction's colour, the
        symbol on it (faint on the allies' banner), the trim, stars and pole as they were; the flag symbol on the
        campaign map gets the bare symbol."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow")
        from campaign_editor import banners as B
        from campaign_editor import emblem as E
        d = tempfile.mkdtemp()
        blank = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        dr = ImageDraw.Draw(blank)
        for x0, x1 in ((4, 104), (112, 252)):                          # two white banners
            dr.rectangle((x0, 4, x1, 180), fill=(220, 220, 220, 255))
        dr.rectangle((112, 170, 252, 180), fill=(200, 160, 30, 255))    # a gold fringe
        dr.rectangle((20, 200, 200, 230), fill=(200, 180, 40, 255))     # stars and pole below
        self.assertEqual(len(B.banner_boxes(blank)), 2)
        old = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        ImageDraw.Draw(old).rectangle((4, 4, 104, 180), fill=(170, 30, 30, 255))
        ImageDraw.Draw(old).rectangle((112, 4, 252, 180), fill=(170, 30, 30, 255))
        other = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        ImageDraw.Draw(other).ellipse((0, 0, 255, 120), fill=(9, 9, 9, 255))
        self.assertEqual(B.best_template({"Roman": blank, "eastern": other}, old), "Roman")
        flag = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(flag).ellipse((8, 8, 56, 56), fill=(0, 0, 0, 255))
        pics = []
        for name, field in (("standard_alpha", "standard_texture"), ("standard_alpha_ally", "ally_texture")):
            path = os.path.join(d, name + ".tga")
            old.save(path)
            pics.append({"path": path, "rel": "models/textures/%s.tga" % name, "label": "banner / standard texture",
                         "link": ["banners", field], "size": (256, 256, 32)})
        flag.save(os.path.join(d, "flag.tga"))
        pics.append({"path": os.path.join(d, "flag.tga"), "rel": "symbol:flag",
                     "label": "flag symbol on the campaign map", "size": (64, 64, 32)})
        self.assertEqual(len(E.emblem_pictures(pics)), 3)
        sym = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        ImageDraw.Draw(sym).polygon(((20, 0), (40, 40), (0, 40)), fill=(20, 160, 40, 255))
        self.assertNotIn(pics[0]["rel"], E.build(sym, pics, sym))       # no blank banner: left as it is
        made = E.build(sym, pics, sym, {"blank": blank, "colour": (30, 60, 200), "boxes": None})
        own, ally = made[pics[0]["rel"]], made[pics[1]["rel"]]
        box = B.symbol_boxes(blank)[1]
        mid = ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2 + 8)
        r, g, b, a = own.getpixel(mid)
        self.assertGreater(g, r + 40)                                   # the symbol
        self.assertGreater(g, b)
        r, g, b, a = ally.getpixel(mid)
        self.assertGreater(b, g)                                        # faint on the allies' cloth
        self.assertGreater(g, 60)
        r, g, b, a = own.getpixel((120, 10))                            # the cloth dyed
        self.assertGreater(b, 150)
        self.assertLess(r, 60)
        self.assertEqual(own.getpixel((180, 175)), (200, 160, 30, 255))  # the gold fringe kept
        self.assertEqual(own.getpixel((100, 215)), (200, 180, 40, 255))  # the stars' row as it was
        self.assertEqual(own.getpixel((108, 50))[3], 0)                 # the gap stays clear
        f = made["symbol:flag"]
        self.assertEqual(f.size, (64, 64))
        self.assertEqual(f.getpixel((2, 2))[3], 0)
        self.assertGreater(f.getpixel((32, 40))[1], 100)                # the bare symbol, no disc or ground
        # a tricolour upright on each banner, no symbol: three colours across each banner's own width
        tri = E.build(sym, pics, sym, {"blank": blank, "colours": [(200, 0, 0), (0, 200, 0), (0, 0, 200)],
                                       "pattern": "three stripes, upright (tricolour)", "no_symbol": True})
        own = tri[pics[0]["rel"]]
        for x, want in ((120, 0), (182, 1), (245, 2)):
            px = own.getpixel((x, 60))
            self.assertEqual(max(range(3), key=lambda i: px[i]), want)
        self.assertEqual(max(range(3), key=lambda i: own.getpixel((8, 60))[i]), 0)   # the other banner too
        # a symbol picture on a white square: the square cleared from its corners, the symbol kept
        from campaign_editor import emblem_edit as EE
        sq = Image.new("RGBA", (50, 50), (255, 255, 255, 255))
        ImageDraw.Draw(sq).ellipse((10, 10, 40, 40), fill=(200, 0, 0, 255))
        self.assertGreater(EE.clear_background(sq), 500)
        self.assertEqual(sq.getpixel((1, 1))[3], 0)
        self.assertEqual(sq.getpixel((25, 25)), (200, 0, 0, 255))
        self.assertEqual(EE.clear_background(sq), 0)                    # already clear: nothing more

    def test_a_town_on_its_regions_edge_stays_its_own(self):
        """A town pixel touching a neighbour's land more than its own (a tester's Erebor) stays its region's town:
        each region has one town, the surest pixels are given first."""
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        red, blue, black = (255, 0, 0), (0, 0, 255), (0, 0, 0)
        # A's town in A's middle; B's town at B's edge, five of its eight neighbours red
        px = [[red, red, red, red, red],
              [red, black, red, red, red],
              [red, red, red, black, red],
              [blue, blue, blue, blue, blue]]
        write_tga(os.path.join(camp, "map_regions.tga"), 5, 4, px)
        self.assertEqual(ModData(self.root).city_tiles("test"), {"A_R": (1, 1), "B_R": (3, 2)})

    def test_faction_without_names_borrows_a_kins(self):
        """A faction with no name lists (brought from another game - a report: 'no name in empire_east's name list
        for a captain') gets a copy of its culture's kin's section, so captains and new characters can be named."""
        from campaign_editor.clone import give_names
        from campaign_editor.plan import Plan
        write(os.path.join(self.root, "data", "descr_sm_factions.txt"),
              SM + "\nfaction\t\tbeta\nculture\t\teastern\n")
        plan = Plan(ModData(self.root), "e", "e", {})
        self.assertEqual(plan.name_pool("beta"), {})
        self.assertEqual(give_names(plan, "beta"), "alpha")
        self.assertIn("Aaron", plan.name_pool("beta")["characters"])
        self.assertIsNone(give_names(plan, "beta"))                         # has them now
        self.assertIn("Rebel", plan.name_pool("slave")["characters"])      # the others untouched

    def test_many_towns_city_castle_and_level(self):
        """Many towns at once made city / castle (Medieval II) and of another level (a tester): what each would do,
        and the refusals in plain words."""
        from campaign_editor import masstown as M
        town = {"region": "A_R", "level": "town", "kind": "city", "buildings": []}
        self.assertEqual(M.town_fit({}, town, "city", None)[0], "skip")              # is that already
        what, why = M.town_fit({}, town, "castle", "large_town")
        self.assertEqual(what, "set")
        self.assertIn("city -> castle", why)
        self.assertIn("town -> large town", why)
        rome = {"region": "A_R", "level": "town", "kind": None, "buildings": []}
        self.assertEqual(M.town_fit({}, rome, "castle", None)[0], "skip")            # Rome: no castles

    def test_one_temple_per_town(self):
        """The games take one temple per town (a chain named temple_...: 'Settlement specified with multiple temple
        buildings'); the many-towns window skips a second, the Check names a town holding two."""
        from campaign_editor import buildings as B, masstown as MT
        self.assertTrue(B.is_temple("temple_of_battle") and B.is_temple("Temple_catholic"))
        self.assertFalse(B.is_temple("church") or B.is_temple("temples_market"))
        town = {"buildings": [("temple_of_battle", "shrine")], "kind": None, "level": "town", "owner": "x"}
        what, why = MT.building_fit({}, town, "temple_of_law", "shrine")
        self.assertEqual(what, "skip")
        self.assertIn("one temple", why)
        self.assertEqual(MT.building_fit({}, town, "temple_of_battle", "temple")[0], "upgrade")
        self.assertEqual(MT.building_fit({}, town, "barracks", "x")[0], "add")
        self.assertEqual(B.other_temple(["temple_of_battle", "barracks"], "temple_of_law"), "temple_of_battle")
        self.assertIsNone(B.other_temple(["temple_of_battle"], "barracks"))

    def test_buildings_and_garrisons_for_many_towns(self):
        import random
        from campaign_editor import masstown as M
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_unit.txt"), EDU.replace(
            "ownership\talpha", "category\tcavalry\nattributes\tgeneral_unit\nstat_cost\t1, 400, 200, 0, 0, 400\n"
            "ownership\talpha").replace(
            "ownership\tslave", "category\tinfantry\nstat_cost\t1, 100, 100, 0, 0, 100\nownership\tslave"))
        write(os.path.join(d, "export_descr_buildings.txt"), """building market
{
    levels stall shop
    {
        stall requires factions { alpha, }
        {
            settlement_min village
        }
        shop requires factions { alpha, }
        {
            settlement_min city
        }
    }
}
""")
        mod = ModData(self.root)
        strat = mod.campaign_file("test", "descr_strat.txt")
        before = open(strat, "rb").read()
        towns = {t["region"]: t for t in M.towns(mod, "test")}
        self.assertEqual((towns["A_R"]["owner"], towns["A_R"]["level"], towns["A_R"]["units"]), ("alpha", "town", 1))
        self.assertEqual(towns["B_R"]["name"], "Btown")
        known = M.known_buildings(mod)
        self.assertEqual(M.building_fit(known, towns["A_R"], "market", "stall")[0], "add")
        self.assertIn("needs a city", M.building_fit(known, towns["A_R"], "market", "shop")[1])
        self.assertIn("may not build", M.building_fit(known, towns["B_R"], "market", "stall")[1])
        self.assertEqual(M.building_fit(known, towns["B_R"], "market", "stall", any_owner=True)[0], "add")
        # garrisons: only the units the owner may have, generals left out; 2..6 under the cap
        self.assertEqual(M.garrison_pool(mod, "slave"), [("rebel spear", 100)])
        self.assertEqual(M.garrison_pool(mod, "alpha"), [])
        rng = random.Random(3)
        for _ in range(30):
            g = M.random_garrison([("a", 100), ("b", 300)], 2, 6, 500, rng)
            self.assertTrue(2 <= len(g) <= 5 and sum({"a": 100, "b": 300}[u] for u in g) <= 500)
        plan = Plan(mod, "towns", "towns", {})
        M.apply(plan, "test", {"build": {"A_R": ("market", "stall"), "B_R": ("market", "stall")},
                               "garrisons": {"B_R": ["rebel spear", "rebel spear"]}, "add_units": True})
        plan.apply()
        mod = ModData(self.root)
        towns = {t["region"]: t for t in M.towns(mod, "test")}
        self.assertEqual(towns["A_R"]["buildings"], [("market", "stall")])
        self.assertEqual(towns["B_R"]["units"], 3)                   # Grog's spear + the two added
        self.assertEqual(M.building_fit(M.known_buildings(mod), towns["A_R"], "market", "stall")[1], "has it already")
        plan = Plan(mod, "towns", "towns", {})
        M.apply(plan, "test", {"remove": {"A_R": "market"}})
        plan.apply()
        self.assertEqual([t["buildings"] for t in M.towns(ModData(self.root), "test")][0], [])
        for b in backups(ModData(self.root)):
            restore(ModData(self.root), b)
        self.assertEqual(open(strat, "rb").read(), before)

    def test_bring_units_and_buildings_from_another_mod(self):
        # straight from another mod's folder (no .zip): a unit whose recruit place is moved to a building the
        # user picks, and a building chain whose names are taken here - renamed with its levels, texts and
        # pictures, its recruit line pointing at the unit brought along, its factions the ones picked
        from campaign_editor import packs
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"),
              "building barracks\n{\n    levels hall\n    {\n        hall requires factions { alpha, }\n"
              "        {\n            capability\n            {\n                recruit \"alpha general\"  0  "
              "requires factions { alpha, }\n            }\n        }\n    }\n}\n"
              "building temple\n{\n    levels shrine big_shrine\n    {\n        shrine requires factions { alpha, }\n"
              "        {\n            capability\n            {\n                recruit \"alpha general\"  0  "
              "requires factions { alpha, }\n            }\n            upgrades\n            {\n"
              "                big_shrine\n            }\n        }\n"
              "        big_shrine requires factions { alpha, }\n        {\n        }\n    }\n}\n")
        write(os.path.join(d, "text", "export_buildings.txt"), "{shrine}Shrine\n{shrine_desc}Holy\n{big_shrine}Big\n",
              utf16=True)
        write(os.path.join(d, "ui", "greek", "buildings", "#greek_shrine.tga"), "PIC")
        target = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, target)
        shutil.copytree(self.root, os.path.join(target, "mod"))
        troot = os.path.join(target, "mod")
        before = tree_hash(troot)
        src, tmod = ModData(self.root), ModData(troot)
        man, files = packs.collect(src, ["alpha general"])
        names = packs.plan_names(tmod, man)
        rmap = packs.default_recruit_map(tmod, man)
        self.assertEqual(rmap, {("barracks", "hall"): ("barracks", "hall"), ("temple", "shrine"): ("temple", "shrine")})
        rmap[("barracks", "hall")] = ("temple", "big_shrine")           # the user's pick
        rmap[("alpha general", "temple", "shrine")] = None               # this unit alone: not at the shrine
        plan = Plan(tmod, "pack", "pack", {})
        packs.import_pack(plan, man, files, ["alpha"], names, rmap)
        bman, bfiles = packs.collect_buildings(src, ["temple"])
        self.assertEqual(bman["buildings"][0]["units"], ["alpha general"])
        cn, ln = packs.building_names(tmod, bman)
        self.assertEqual((cn, ln), ({"temple": "temple_2"}, {"shrine": "shrine_2", "big_shrine": "big_shrine_2"}))
        packs.import_buildings(plan, bman, bfiles, ["alpha"], cn, ln, {"alpha general": names["alpha general"][0]})
        bdir = plan.apply()
        m2 = ModData(troot)
        edb = open(m2.file("edb")).read()
        block = edb[edb.index("building temple_2"):]
        self.assertIn("levels shrine_2 big_shrine_2", block)
        self.assertIn('recruit "alpha general 2"', block)                # pointed at the unit brought along
        self.assertIn("big_shrine_2\n", block)                            # the upgrades list renamed
        hall = edb[edb.index("building barracks"):edb.index("building temple\n")]
        self.assertNotIn("alpha general 2", hall)                          # sent elsewhere by the user
        big = edb[edb.index("building temple\n"):edb.index("building temple_2")]
        self.assertIn('recruit "alpha general 2"', big)                    # into the picked level of this mod
        self.assertEqual(big.count('recruit "alpha general 2"'), 1)        # and not at the shrine (unit's own pick)
        txt = open(m2.text_file("export_buildings.txt"), "rb").read().decode("utf-16")
        self.assertIn("{shrine_2_desc}Holy", txt)
        self.assertTrue(os.path.exists(os.path.join(troot, "data", "ui", "greek", "buildings", "#greek_shrine_2.tga")))
        restore(ModData(troot), bdir)
        after = {k: v for k, v in tree_hash(troot).items() if "_backups" not in k}
        self.assertEqual(after, before)                              # Restore: byte for byte

    def test_brought_building_recruits_only_units_its_faction_may_own(self):
        """Bring from another mod: a brought barracks recruited the units of every culture, each line written for the
        new faction - the game warned 'unit(...) does not match up to the ownership for faction(...)' 159 times on
        every start (a test mod in Rome). A recruit line now names only the factions export_descr_unit lets own the
        unit; a line no picked faction may own is left out, said."""
        from campaign_editor import packs
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"),
              "building barracks\n{\n    levels hall\n    {\n        hall requires factions { alpha, slave, }\n"
              "        {\n            capability\n            {\n"
              "                recruit \"alpha general\"  0  requires factions { alpha, }\n"
              "                recruit \"rebel spear\"  0  requires factions { slave, }\n"
              "            }\n        }\n    }\n}\n")
        target = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, target)
        shutil.copytree(self.root, os.path.join(target, "mod"))
        tmod = ModData(os.path.join(target, "mod"))
        bman, bfiles = packs.collect_buildings(ModData(self.root), ["barracks"])
        plan = Plan(tmod, "pack", "pack", {})
        cn, ln = packs.building_names(tmod, bman)
        packs.import_buildings(plan, bman, bfiles, ["alpha"], cn, ln)
        text = "\n".join(plan.files[tmod.file("edb")].texts())
        block = text[text.index("building " + cn["barracks"]):]
        self.assertIn('recruit "alpha general"  0  requires factions { alpha, }', block)
        self.assertNotIn("rebel spear", block)                       # alpha may not own it
        self.assertIn("may not own the unit", plan.report())
        self.assertNotIn(tmod.file("edu"), plan.files)               # export_descr_unit only read

    def test_brought_lines_lose_conditions_this_mod_lacks(self):
        # a tester brought BI's british legionaries into plain Rome: their recruit line kept 'hidden_resource
        # britain', which Rome does not have, and REX stopped at start ('unrecognised hidden resource')
        from campaign_editor import packs
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        edb = ("building barracks\n{\n    levels hall\n    {\n        hall requires factions { alpha, }\n"
               "        {\n            capability\n            {\n                recruit \"alpha general\"  0  "
               "requires factions { alpha, } and hidden_resource britain\n                religious_belief "
               "christianity 2\n            }\n        }\n    }\n}\n")
        write(os.path.join(d, "export_descr_buildings.txt"), "hidden_resources britain\n" + edb)
        target = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, target)
        shutil.copytree(self.root, os.path.join(target, "mod"))
        troot = os.path.join(target, "mod")
        write(os.path.join(troot, "data", "export_descr_buildings.txt"), "hidden_resources rome\n" + edb.replace(
            " and hidden_resource britain", "").replace("                religious_belief christianity 2\n", ""))
        before = tree_hash(troot)
        src, tmod = ModData(self.root), ModData(troot)
        man, files = packs.collect(src, ["alpha general"])
        bman, bfiles = packs.collect_buildings(src, ["barracks"])
        plan = Plan(tmod, "pack", "pack", {})
        names = packs.plan_names(tmod, man)
        packs.import_pack(plan, man, files, ["alpha"], names)
        cn, ln = packs.building_names(tmod, bman)
        packs.import_buildings(plan, bman, bfiles, ["alpha"], cn, ln, {"alpha general": names["alpha general"][0]})
        self.assertIn("hidden_resource britain", plan.report())     # said in Preview
        bdir = plan.apply()
        with open(ModData(troot).file("edb")) as fh:
            text = fh.read()
        self.assertNotIn("britain", text)
        self.assertNotIn("religious_belief", text)                  # Rome has no beliefs
        self.assertIn('recruit "alpha general 2"', text)
        from campaign_editor.check import building_condition_problems
        self.assertEqual(building_condition_problems(ModData(troot)), [])
        with open(ModData(troot).file("edb"), "a") as fh:            # as the tester's file was: Check mod says it
            fh.write("building x\n{\n    levels y\n    {\n        y requires factions { alpha, } and "
                     "hidden_resource britain\n    }\n}\n")
        self.assertIn("britain", " ".join(building_condition_problems(ModData(troot))))
        restore(ModData(troot), bdir)
        after = {k: v for k, v in tree_hash(troot).items() if "_backups" not in k}
        self.assertEqual(after, before)

    def test_a_region_without_a_port_gets_one(self):
        # a tester: the Map's legend offered towns but no port - a region by the sea without a port gets one
        from campaign_editor import mapedit as ME
        from campaign_editor.plan import Plan
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        red, blue, black, sea = (255, 0, 0), (0, 0, 255), (0, 0, 0), (41, 140, 233)
        write_tga(os.path.join(camp, "map_regions.tga"), 5, 4, [[red, red, blue, blue, sea],
                                                                 [red, black, blue, blue, sea],
                                                                 [red, red, blue, black, sea],
                                                                 [red, red, blue, blue, sea]])
        write_tga(os.path.join(camp, "map_heights.tga"), 11, 9,
                  [[(0, 0, 250) if x >= 8 else (20, 20, 20) for x in range(11)] for y in range(9)])
        mod = ModData(self.root)
        self.assertEqual(ME.ports(mod, "test"), {})
        region = mod.regions("test") and next(r for r, v in mod.regions("test").items() if v["colour"] == blue)
        spot = next((x, y) for y in range(4) for x in range(5)
                    if mod.region_map("test").get(x, y) == blue and not ME.place_problem(mod, "test", "port", region,
                                                                                         (x, y)))
        before = tree_hash(self.root)
        plan = Plan(mod, "map", "port", {})
        ME.apply_places(plan, "test", [{"what": "port", "region": region, "to": spot}])
        self.assertIn("a new port for %s" % region, plan.report())
        bdir = plan.apply()
        self.assertEqual(tuple(ME.ports(ModData(self.root), "test").get(region)), spot)
        restore(ModData(self.root), bdir)
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if "_backups" not in k}, before)

    def test_map_deletes_a_character_of_any_faction(self):
        """The Map's right-click Delete: a character of any faction goes with his whole block (army too); the leader,
        the heir and one on the family tree are refused."""
        from campaign_editor.edit import map_changes
        mod = ModData(self.root)
        strat = mod.campaign_file("test", "descr_strat.txt")
        s = Strat(mod.load(strat))
        fb = next(fb for fb in s.factions if any(c.xy and not c.role and c.kind != "named character"
                                                 for c in fb.characters))
        c = next(c for c in fb.characters if c.xy and not c.role and c.kind != "named character")
        plan = Plan(mod, "map", "map", {})
        map_changes(plan, "test", {"remove": {fb.name: [{"name": c.name, "from": list(c.xy)}]}})
        after = Strat(plan.files[strat])
        self.assertFalse(any(x.name == c.name and x.xy == c.xy for x in after.faction(fb.name).characters))
        self.assertEqual(len(plan.files[strat].raw), len(mod.load(strat).raw) - (c.end - c.start))
        lead = next((x for f in s.factions for x in f.characters if x.role == "leader" and x.xy), None)
        if lead:
            with self.assertRaises(ValueError):
                map_changes(Plan(mod, "map", "map", {}), "test",
                            {"remove": {lead.owner: [{"name": lead.name, "from": list(lead.xy)}]}})

    def test_map_editor_moves_and_arms_any_faction(self):
        """The Map editor (no faction picked): any faction's character dragged elsewhere and any army's units
        changed, written together - units found where the army stands, then the move; a named general keeps his
        bodyguard; Restore puts every byte back."""
        from campaign_editor.edit import map_changes
        from campaign_editor.textio import tokens
        mod = ModData(self.root)
        before = tree_hash(self.root)
        strat = mod.campaign_file("test", "descr_strat.txt")
        taken = set(mod.city_tiles("test").values()) | {(1, 1), (2, 2)}
        to = mod.free_tile("test", "A_R", taken)
        self.assertIsNotNone(to)
        plan = Plan(mod, "map", "map", {})
        map_changes(plan, "test", {
            "army_units": {"slave": [{"name": "Grog", "from": (2, 2), "units": ["rebel spear", "rebel spear"]}],
                           "alpha": [{"name": "Aaron Alphid", "from": (1, 1), "units": ["alpha general"]}]},
            "moves": {"slave": [{"name": "Grog", "from": (2, 2), "to": to}]}})
        s = Strat(plan.files[strat])
        grog = next(c for c in s.faction("slave").characters if c.name == "Grog")
        self.assertEqual(tuple(grog.xy), tuple(to))
        self.assertEqual([tokens(l)[1:3] for l in s.lines[grog.start:grog.end] if tokens(l)[:1] == ["unit"]],
                         [["rebel", "spear"]] * 2)
        aaron = next(c for c in s.faction("alpha").characters if c.name == "Aaron Alphid")
        units = [l for l in s.lines[aaron.start:aaron.end] if tokens(l)[:1] == ["unit"]]
        self.assertEqual(len(units), 2)                              # his bodyguard + the one given
        with self.assertRaises(ValueError):                         # an army without units is refused
            map_changes(Plan(mod, "map", "map", {}), "test",
                        {"army_units": {"slave": [{"name": "Grog", "from": (2, 2), "units": []}]}})
        with self.assertRaises(ValueError):                         # a tile he cannot stand on
            map_changes(Plan(mod, "map", "map", {}), "test",
                        {"moves": {"slave": [{"name": "Grog", "from": (2, 2), "to": (1, 1)}]}})
        restore(ModData(self.root), plan.apply())
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if "_backups" not in k}, before)

    def test_map_changes_for_any_faction(self):
        # a tester: what is put on the Map should not depend on the faction picked elsewhere - a town given to any
        # faction, an army or agent placed for any faction, written with the next Apply
        from campaign_editor.edit import first_units, map_changes
        from campaign_editor.plan import Plan
        mod = ModData(self.root)
        before = tree_hash(self.root)
        free = mod.free_tile("test", "A_R", set(mod.city_tiles("test").values()) | {(1, 1), (2, 2)})
        self.assertIsNotNone(free)
        units = first_units(mod, "test", "alpha", "army", free)
        self.assertEqual(units, ["alpha general"])                   # its nearest army's first unit
        plan = Plan(mod, "map", "map", {})
        map_changes(plan, "test", {"owners": {"B_R": "alpha"},
                                   "characters": {"alpha": [{"kind": "army", "name": "Boris", "age": 30,
                                                             "units": units, "xy": free}]}})
        self.assertIn("B_R: slave -> alpha", plan.report())
        bdir = plan.apply()
        st = Strat(ModData(self.root).load(ModData(self.root).campaign_file("test", "descr_strat.txt")))
        alpha = st.faction("alpha")
        self.assertIn("B_R", [x.region for x in alpha.settlements])
        self.assertIn("Boris", [c.name for c in alpha.characters])
        restore(ModData(self.root), bdir)
        self.assertEqual({k: v for k, v in tree_hash(self.root).items() if "_backups" not in k}, before)

    def test_recolour_keeps_a_bright_colour_of_its_own(self):
        # a tester's emblem: a gold wolf and laurel on red turned red - the rim growth took bright gold for red
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor.recolour import recolour
        im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((2, 2, 61, 61), fill=(180, 10, 10, 255))
        for k in range(6):
            d.line((10 + 7 * k, 12, 14 + 7 * k, 50), fill=(225, 175, 30, 255), width=2)
        d.rectangle((24, 26, 40, 38), fill=(205, 160, 40, 255))
        out, share = recolour(im, ((165, 20, 20), (0, 0, 0)), ((20, 40, 170), (255, 255, 255)))
        gold = [(x, y) for x in range(64) for y in range(64)
                if im.getpixel((x, y))[:3] in ((225, 175, 30), (205, 160, 40))]
        self.assertTrue(all(out.getpixel(p)[:3] == im.getpixel(p)[:3] for p in gold))
        red = [(x, y) for x in range(64) for y in range(64) if im.getpixel((x, y))[:3] == (180, 10, 10)]
        self.assertTrue(all(out.getpixel(p)[2] > 100 for p in red))

    def test_emblem_fitted_by_hand(self):
        # a tester: the emblem needs an editor of its own - cut to the old emblem's disc, a white background
        # cleared with the magic wand, a click on the turned picture finds the right pixel
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor import emblem_edit as EE
        from campaign_editor.emblem import footprint
        src = Image.new("RGBA", (200, 100), (255, 255, 255, 255))
        ImageDraw.Draw(src).rectangle((150, 10, 190, 50), fill=(200, 0, 0, 255))
        for ang in (0, 30, -45):
            st = {"scale": 1.0, "dx": 10, "dy": -5, "angle": ang, "shape": None, "frame": None, "ground": None}
            m = EE.compose(src, st)
            st["_box"] = footprint(src)
            hits = [(x, y) for x in range(0, 256, 5) for y in range(0, 256, 5)
                    if m.getpixel((x, y)) == (200, 0, 0, 255)]
            self.assertTrue(hits)
            self.assertTrue(all(src.getpixel(EE.to_source(st, src.size, h))[:3] == (200, 0, 0) for h in hits))
        n = EE.flood(src, (5, 5), 20)                                  # the magic wand on the white
        self.assertEqual(n, 200 * 100 - 41 * 41)
        self.assertEqual(src.getpixel((5, 5))[3], 0)
        disc = EE.compose(src, {"scale": None, "dx": 0, "dy": 0, "angle": 0, "shape": "circle", "frame": None,
                                "ground": (0, 0, 255)})
        self.assertEqual(disc.getpixel((3, 3))[3], 0)                  # outside the circle: clear
        self.assertEqual(disc.getpixel((128, 10))[:3], (0, 0, 255))   # inside, beside the picture: the ground
        frame = Image.new("L", (64, 64), 0)
        ImageDraw.Draw(frame).ellipse((0, 0, 63, 63), fill=255)
        old = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        old.putalpha(frame)
        got = EE.frame_mask([{"rel": "a", "label": "loading-screen logo"}], {"a": old})
        self.assertEqual((got.size, got.getpixel((128, 128)), got.getpixel((2, 2))), ((256, 256), 255, 0))

    def test_read_and_draw_a_medieval2_mesh(self):
        """A .mesh laid out as the vanilla ones: parts with triangles, then the vertex streams (texture u v,
        bone weights, positions). Read back, the man shown, drawn both ways."""
        import struct
        from campaign_editor import meshview as MV

        def text(t):
            return struct.pack("<I", len(t)) + t.encode()
        cube = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
                 (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
        n = len(cube)
        tri = lambda fs: struct.pack("<I", len(fs)) + b"".join(struct.pack("<3H", *f) for f in fs)
        data = (b"\x16\x00\x00\x00serialization::archive\x03\x04\x04\x04\x08\x01" +
                bytes.fromhex("0000000000000001000000000004000103000000000000070001000100000000000200000000000b00"
                              "0103020000 00".replace(" ", "")) +
                text("Head") + text("head_01") + b"\x00\x00" + tri(faces[:8]) +
                bytes.fromhex("000000000000000000 0a00010003000000 0b00020000000b0004000000".replace(" ", "")) +
                text("Attachments3") + text("teeth") + tri(faces[8:]) +
                bytes.fromhex("0000000000 0a00050000000b00040000000b0006000000".replace(" ", "")) +
                bytes.fromhex("0600010044000000070001000000") + struct.pack("<I", n) +
                bytes.fromhex("000002000000000012000100450000000400000000 00".replace(" ", "")) +
                struct.pack("<I", n) + b"".join(struct.pack("<2f", 0.1 + 0.05 * i, 0.2) for i in range(n)) +
                bytes.fromhex("000000001b004600000012004700000001000000") + struct.pack("<I", n) +
                b"".join(struct.pack("<2f", 1.0, 0.0) for i in range(n)) +
                bytes.fromhex("000000001b004800000017000100490000000000000000 00".replace(" ", "")) +
                struct.pack("<I", n) + b"".join(struct.pack("<3f", *v) for v in cube) + b"\x00" * 40)
        m = MV.read(data)
        self.assertEqual([(g.name, g.material, len(g.tris) // 3) for g in m.groups],
                         [("Head", "head_01", 8), ("Attachments3", "teeth", 4)])
        self.assertEqual(m.count, 8)
        self.assertEqual(m.positions[7], (1.0, 1.0, 1.0))
        self.assertAlmostEqual(m.uvs[2][0], 0.2, places=5)
        self.assertEqual([g.name for g in m.shown()], ["Head", "Attachments3"])
        with self.assertRaises(MV.MeshError):
            MV.read(b"\x16\x00\x00\x00not a mesh at all.........")
        # a battle banner (data/banners/*.mesh): one part 'GenMesh' with no material and 1 byte of class info
        head = data[:data.index(text("Head"))]
        streams = data[data.index(bytes.fromhex("0600010044000000")):]
        banner = MV.read(head + text("GenMesh") + b"\x00\x00\x00\x00" + b"\x00" + tri(faces) + streams)
        self.assertEqual([(g.name, g.material, len(g.tris) // 3) for g in banner.groups], [("GenMesh", "", 12)])
        self.assertEqual(banner.positions[7], (1.0, 1.0, 1.0))
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed - the drawing is not checked")
        tex = Image.new("RGB", (8, 8), (200, 30, 30))
        for textured in (True, False):
            im = MV.render(m, (60, 80), texture=tex, textured=textured)
            self.assertEqual(im.size, (60, 80))
            reds = [p for p in im.getdata() if p[0] > 60 and p[0] > 2 * p[1]]
            self.assertTrue(len(reds) > 200, textured)       # the cube in the man's (red) texture

    def test_clone_names_inside_texts(self):
        """Medieval II has no short names ({SICILY}Sicily): a clone named 'Kingdom of Jerusalem' must not become
        'the Kingdom of Kingdom of Jerusalem' or 'de Kingdom of Jerusalem' in the copied texts."""
        from campaign_editor.plan import Plan

        def swap(opts, text):
            p = Plan.__new__(Plan)
            p.opts = opts
            for old, new in p.display_replacements():
                text = text.replace(old, new)
            return text
        m2 = dict(template_display_name="Sicily", display_name="Kingdom of Jerusalem", template_adjective="Sicilian",
                  adjective="Jerusalemite")
        self.assertEqual(swap(m2, "The Kingdom of Sicily awaits. de Sicily. Sicilian knights."),
                         "The Kingdom of Jerusalem awaits. de Jerusalem. Jerusalemite knights.")
        self.assertEqual(swap(dict(m2, short_name="Outremer"), "de Sicily"), "de Outremer")
        rome = dict(template_display_name="Macedon", template_short_name="Macedon", display_name="Epirus",
                    short_name="Epirus")
        self.assertEqual(swap(rome, "the Kingdom of Macedon"), "the Kingdom of Epirus")

    def test_read_and_draw_a_rome_cas(self):
        """A Rome .cas laid out as the vanilla ones (3.05): header with the bone count and parents, frame times, bone
        records, rest places, a shield hanging on a bone and a body whose points hang on a bone. Read back, put
        together in the T pose (the skeleton at rest), the texture the file names, drawn in one texture."""
        import math
        import struct
        from campaign_editor import meshview as MV

        def text(t):
            return struct.pack("<I", len(t) + 1) + t.encode() + b"\x00"
        cube = [(x, y, z) for x in (-0.1, 0.1) for y in (-0.1, 0.1) for z in (-0.1, 0.1)]
        faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
                 (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]

        def vertices(skinned):
            n = len(cube)
            out = struct.pack("<2H2B", n, len(faces), 1, 1 if skinned else 0)
            if skinned:
                out += struct.pack("<%dI" % n, *([1] * n))
            out += b"".join(struct.pack("<3f", *v) for v in cube)
            out += b"".join(struct.pack("<3f", *[c / math.sqrt(0.03) for c in v]) for v in cube)
            out += b"".join(struct.pack("<3H", *f) for f in faces) + b"\x00" * 4
            return out + b"".join(struct.pack("<2f", 0.1 * i, 0.9 - 0.1 * i) for i in range(n)) + b"\x00"
        head = struct.pack("<f", 3.05) + b"\x00" * 46 + struct.pack("<H", 2) + struct.pack("<2I", 0, 0)
        head += struct.pack("<If", 1, 0.5)                                   # one frame
        bones = text("Scene Root") + struct.pack("<5I", 0, 0, 0, 0, 0)
        bones += text("bone_pelvis") + struct.pack("<5I", 1, 0, 0, 16, 0)
        anim = struct.pack("<4f", 0, 0, 0, 1) + struct.pack("<3f", 0, 0, 0) + struct.pack("<3f", 0, 1, 0)
        shield = text("shield") + text("")[:-1] + b"\x00" + text("")[:-1] + b"\x00" + struct.pack(
            "<I7f", 1, 0, 0, 0, 1, 2, 0, 0) + vertices(False)
        body = text("Body_400") + b"\x01\x00\x00\x00\x00" + struct.pack("<I6f", 0, *([0] * 6)) + vertices(True)
        data = head + bones + anim + struct.pack("<2I", 1, 1) + shield + body + text("textures\\unit_x.tga") + \
            b"\x00" * 40
        m = MV.read_cas(data)
        self.assertEqual([(g.name, g.attachment, len(g.tris) // 3) for g in m.groups],
                         [("shield", True, 12), ("Body_400", False, 12)])
        self.assertTrue(m.one_texture)
        self.assertEqual(m.texture_ref, "data/models_unit/textures/unit_x.tga")
        for got, want in zip(m.positions[7], (0.1, 1.1, 0.1)):              # the shield from the bone it hangs on
            self.assertAlmostEqual(got, want, places=5)                     # (its 7 floats are no place: a report)
        for got, want in zip(m.positions[15], (0.1, 1.1, 0.1)):             # the body on the pelvis, 1 up
            self.assertAlmostEqual(got, want, places=5)
        self.assertEqual(len(m.shown(weapons=False)), 1)                     # the shield hidden
        with self.assertRaises(MV.MeshError):
            MV.read_cas(b"\x00" * 80)
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed - the drawing is not checked")
        im = MV.render(m, (200, 240), texture=Image.new("RGB", (8, 8), (200, 30, 30)))
        self.assertTrue(len([p for p in im.getdata() if p[0] > 60 and p[0] > 2 * p[1]]) > 200)

    def test_engine_settings_in_campaign_rules(self):
        """descr_ex.txt / descr_caps_ex.txt (REX, M2EX): each 'key value' line a value, its section the banner heading,
        its explanation the comment above; a write changes the value's characters only."""
        from campaign_editor import campaignrules as CR
        from campaign_editor.plan import Plan
        text = (";;;;;;;;\r\n; Extended settings\r\n;;;;;;;;\r\n\r\n; Maximum number of factions\r\n; Increase for mods\r\n"
                "max_factions 21\r\n\r\n;;;;;;;;\r\n; Family / ageing\r\n; All in years\r\n;;;;;;;;\r\n\r\n"
                "; Age of manhood (default 16)\r\nage_of_manhood 16\r\n;unit_group_mode vanilla\r\n"
                "; colour r g b\r\nrange_indicator_colour 60 200 255\r\n")
        path = os.path.join(self.root, "data", "descr_ex.txt")
        with open(path, "w", newline="") as fh:
            fh.write(text)
        rules = {r.key: r for r in CR.read(path)}
        self.assertEqual(sorted(rules), ["age_of_manhood", "max_factions", "range_indicator_colour"])
        self.assertEqual(rules["max_factions"].section, "Extended settings")
        self.assertEqual(CR.explain(rules["max_factions"]), "Maximum number of factions\nIncrease for mods")
        self.assertEqual(rules["age_of_manhood"].section, "Family and ageing")
        self.assertEqual(rules["range_indicator_colour"].kind, "words")
        self.assertIsNone(CR.check(rules["range_indicator_colour"], "10 20 30"))
        self.assertIsNotNone(CR.check(rules["age_of_manhood"], "x"))
        plan = Plan(ModData(self.root), "rules", "rules")
        CR.apply(plan, "descr_ex.txt", {rules["age_of_manhood"]: "14", rules["range_indicator_colour"]: "1 2 3"}, path, None)
        plan.apply()
        with open(path, newline="") as fh:
            self.assertEqual(fh.read(), text.replace("age_of_manhood 16", "age_of_manhood 14").replace(
                "60 200 255", "1 2 3"))

    def test_test_mod_covers_every_feature(self):
        """The test mod covers the whole editor: every work button, tab and Tools entry of the window names a feature
        of selftest.COVERAGE, every feature names steps that exist (or says why none - the run does it, or it only
        shows), every step serves a feature. A new button or Tools entry without its step fails here."""
        import re as _re
        import campaign_editor
        from campaign_editor import selftest as ST
        self.assertEqual(ST.coverage_problems(), [])
        with open(os.path.join(os.path.dirname(campaign_editor.__file__), "gui.py"), encoding="utf-8") as fh:
            src = fh.read()                                   # read as text: the test job has no tkinter
        tools = src[src.index('tools = ttk.Menubutton'):src.index('tools["menu"] = menu')]
        labels = _re.findall(r'add_command\(label="([^"]+)"', tools)
        labels += _re.findall(r'^TEST_MOD_LABEL = "([^"]+)"', src, _re.M)
        works = src[src.index("WORK_TITLES = {"):]
        labels += _re.findall(r'"\w+": "([^"]+)"', works[:works.index("}")])
        buttons = src[src.index("WINDOW_BUTTONS = ["):]                  # the work bar's window buttons
        labels += _re.findall(r'\("\w+", "([^"]+)"', buttons[:buttons.index("\n    ]")])
        labels += [t.strip() for t in _re.findall(r'self\.nb\.add\(\w+, text="([^"]+)"\)', src)]
        self.assertGreater(len(labels), 30)
        self.assertEqual([t for t in labels if ST.ui_entry(t) is None], [])

    def test_dds_written_with_the_games_own_header(self):
        """A compressed DDS (Rome .tga.dds, the DDS inside a Medieval II .texture) keeps the top level's byte size
        in its header (DDSD_LINEARSIZE): Pillow wrote a row pitch there (4108 for 1024 x 1024 DXT5) and Medieval II
        read the data by it - recoloured units turned to grey stripes in battle. A picture replacing a file of the same
        size, format and mipmaps takes that file's header byte for byte."""
        try:
            from PIL import Image
        except ImportError:
            return
        from campaign_editor.factionart import image_dds
        im = Image.new("RGBA", (64, 32), (10, 200, 30, 255))
        data = image_dds(im)
        self.assertEqual(data[:4], b"DDS ")
        old = os.path.join(self.root, "old.dds")
        im.save(old, format="DDS", pixel_format="DXT5")
        new = image_dds(Image.new("RGBA", (64, 32), (200, 10, 30, 255)), old)
        self.assertEqual(int.from_bytes(new[20:24], "little"), 16 * 8 * 16)        # 16 x 8 blocks of 16 bytes
        self.assertTrue(int.from_bytes(new[8:12], "little") & 0x80000)
        with open(old, "rb") as fh:
            head = bytearray(fh.read(128))
        head[20:24] = (16 * 8 * 16).to_bytes(4, "little")
        with open(old, "r+b") as fh:
            fh.write(bytes(head))
        self.assertEqual(image_dds(im, old)[:128], bytes(head))                     # its own header kept

    def test_campaign_start_in_campaign_rules(self):
        """Campaign rules: the top of the campaign's descr_strat.txt - start / end date, timescale, spawn values as
        values, switch lines (night_battles_enabled ...) as on / off; a switch turned off loses its line, one turned
        on gets a line in its place in the engines' order (before the spawn values - after them Rome's campaign did
        not load: 'Script Error in descr_strat.txt'); a bad date refused; the rest of the file byte for byte; Restore exact."""
        from campaign_editor import campaignrules as CR
        from campaign_editor.plan import Plan
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        old = b"resource\tiron, 1, 1\n\nfaction\talpha, balanced smith\ndenari 100\n"
        top = ("campaign\ttest\nplayable\n\talpha\nend\nnonplayable\n\tslave\nend\n\nstart_date\t-270 summer\n"
               "end_date\t14 summer ; the end\nnight_battles_enabled\nbrigand_spawn_value 10\n\n")
        with open(path, "wb") as fh:
            fh.write(top.encode() + old)
        before = tree_hash(os.path.join(self.root, "data"))
        self.assertIn(("descr_strat.txt", "The campaign test", path, None), CR.files(mod, "test"))
        rules = {r.key: r for r in CR.read(path, medieval2=False)}
        self.assertEqual(rules["start_date"].value, "-270 summer")
        self.assertEqual(rules["night_battles_enabled"].value, "on")
        self.assertEqual(rules["gladiator_uprising_disabled"].value, "off")
        self.assertNotIn("show_date_as_turns", rules)                       # RomeTW / REX do not know it
        self.assertNotIn("alpha", rules)                                    # the faction lists are not values
        self.assertIsNotNone(CR.check(rules["start_date"], "soon"))
        self.assertIsNone(CR.check(rules["start_date"], "-200 winter"))
        self.assertIsNotNone(CR.check(rules["night_battles_enabled"], "yes"))
        plan = Plan(mod, "rules", "rules", {})
        CR.apply(plan, "descr_strat.txt", {rules["start_date"]: "-200 winter", rules["end_date"]: "20 winter",
                                           rules["night_battles_enabled"]: "off",
                                           rules["gladiator_uprising_disabled"]: "on"}, path, None)
        bdir = plan.apply()
        with open(path, "rb") as fh:
            got = fh.read().decode()
        self.assertEqual(got, (top.replace("-270 summer", "-200 winter").replace("14 summer ;", "20 winter ;")
                               .replace("night_battles_enabled\n", "")
                               .replace("brigand_spawn_value 10\n", "gladiator_uprising_disabled\n"
                                        "brigand_spawn_value 10\n")) + old.decode())
        restore(ModData(self.root), bdir)
        self.assertEqual(tree_hash(os.path.join(self.root, "data")), before)

    def test_campaign_rules_and_addons(self):
        """Campaign rules: values of the settings files read with their section (M2EX's unquoted bool=false too),
        a change writes only the value's characters, a bad value is refused, a mod without the file gets the game's
        copy; Restore byte for byte. Add-ons: the script's settings read and written back, the rest untouched."""
        from campaign_editor import campaignrules as CR
        from campaign_editor import addons as AD
        import time
        t0 = time.time()                    # a tag the old pattern took exponential time on (CodeQL py/redos)
        self.assertEqual(list(CR.RE_TAG.finditer("<A -=" + '"" -=' * 3000)), [])
        self.assertLess(time.time() - t0, 1.0)
        d = os.path.join(self.root, "data")
        db = ('<?xml version="1.0"?>\n<root>\n   <family_tree>\n      <age_of_manhood uint="16"/>\n'
              '   </family_tree>\n   <display>\n      <keep_original_heretic_portraits bool=false/>\n'
              '      <!-- <max_age uint="1"/> -->\n   </display>\n   <factor_modifiers>\n'
              '      <factor name="SOF_HEALTH">\n         <pip_modifier value="1.0"/>\n      </factor>\n'
              '   </factor_modifiers>\n</root>\n')
        write(os.path.join(d, "descr_campaign_db.xml"), db)
        write(os.path.join(d, "descr_unit_sizes.txt"), "; sizes\nunit_size UI_VIDEO_UNIT_SCALE_SMALL   0.5\n")
        mod = ModData(self.root)
        names = [f[0] for f in CR.files(mod)]
        self.assertEqual(names, ["descr_campaign_db.xml", "descr_unit_sizes.txt"])
        rules = CR.read(os.path.join(d, "descr_campaign_db.xml"))
        self.assertEqual([(r.section, r.key, r.value, r.kind) for r in rules],
                         [("family_tree", "age_of_manhood", "16", "uint"),
                          ("display", "keep_original_heretic_portraits", "false", "bool"),
                          ("factor_modifiers / SOF_HEALTH", "pip_modifier", "1.0", "float")])
        self.assertIn("public order", CR.explain(rules[2]))
        self.assertEqual(CR.check(rules[0], "-3"), "a whole number, 0 or more")
        self.assertEqual(CR.check(rules[1], "yes"), "true or false")
        before = tree_hash(d)
        plan = Plan(mod, "rules", "rules", {})
        CR.apply(plan, "descr_campaign_db.xml", {rules[0]: "14", rules[1]: "true"},
                 os.path.join(d, "descr_campaign_db.xml"), None)
        sizes = CR.read(os.path.join(d, "descr_unit_sizes.txt"))
        CR.apply(plan, "descr_unit_sizes.txt", {sizes[0]: "3.0"}, os.path.join(d, "descr_unit_sizes.txt"), None)
        with self.assertRaises(ValueError):
            CR.apply(Plan(mod, "r", "r", {}), "descr_campaign_db.xml", {rules[0]: "x"},
                     os.path.join(d, "descr_campaign_db.xml"), None)
        bdir = plan.apply()
        with open(os.path.join(d, "descr_campaign_db.xml")) as f:
            self.assertEqual(f.read(), db.replace('uint="16"', 'uint="14"').replace("bool=false", "bool=true"))
        with open(os.path.join(d, "descr_unit_sizes.txt")) as f:
            self.assertEqual(f.read(), "; sizes\nunit_size UI_VIDEO_UNIT_SCALE_SMALL   3.0\n")
        restore(mod, bdir)
        self.assertEqual(tree_hash(d), before)
        # the Sack Settlement add-on: settings read, changed, written; unchanged ones keep their lines
        a = AD.by_key("sack_settlement")
        text = a.template()
        got = AD.read_settings(a, text)
        self.assertEqual(got["RAZE_WHO"], "player")
        self.assertEqual(got["RAZE_KEEP_CHAINS"], ["core_building", "defenses", "hinterland_roads"])
        self.assertEqual(got["RAZE_PEOPLE_LEFT"], AD.MIN_PEOPLE)
        self.assertIn('chain.indexof("core") != 0', text)
        self.assertEqual(AD.render(a, text, got), text)
        new = dict(got, RAZE_WHO="homeless", RAZE_GOLD_PER_BUILDING=500, RAZE_KEEP_CHAINS=["core_building"])
        self.assertEqual(AD.read_settings(a, AD.render(a, text, new)), new)
        self.assertTrue(AD.check(a, dict(got, RAZE_WHO="list", RAZE_FACTIONS=[])))
        # tied to the mod's files: a rebel unit the mod does not have is refused
        self.assertTrue(any("nobody" in p for p in AD.check(a, dict(got, RAZE_DEFAULT_REBEL_UNITS=["nobody"]), mod)))
        self.assertFalse(AD.check(a, dict(got, RAZE_DEFAULT_REBEL_UNITS=["alpha general"]), mod))
        plan = Plan(mod, "addon", "sack", {})
        dst = AD.plan_install(plan, a, new)
        self.assertEqual(dst, os.path.join(self.root, "script", "modules", "sack_settlement.nut"))
        bdir = plan.apply()
        self.assertEqual(AD.installed(mod, a)["RAZE_WHO"], "homeless")
        restore(mod, bdir)
        self.assertIsNone(AD.installed(mod, a))

    def test_faction_names_players_see(self):
        """A mod may keep an internal name and show another ('turks' shown as 'Ryazan'): the lists say both; a name
        that only differs by case or 'The' stays plain (a tester's wish on Discord)."""
        from campaign_editor.build import display_names, faction_label
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "text", "expanded_bi.txt"), "{ALPHA}\t\tRyazan\n{SLAVE}\tRebels\n", utf16=True)
        mod = ModData(self.root)
        self.assertEqual(display_names(mod), {"alpha": "Ryazan", "slave": "Rebels"})
        self.assertEqual(faction_label("alpha", "Ryazan"), "alpha - Ryazan")
        self.assertEqual(faction_label("turks", "The Turks"), "turks")
        self.assertEqual(faction_label("papal_states", "The Papal States"), "papal_states")
        self.assertEqual(faction_label("england", None), "england")

    def test_factions_all_lets_everyone_build(self):
        """'requires factions { all, }' (a modder's way to say everyone): every faction may build the level - the
        town's buildings, the Buildings tab and the Building editor say so, and setting it warns about nothing
        (a tester's report on 0.18.1: only the temples were offered)."""
        from campaign_editor.buildings import Level, available
        from campaign_editor import editors as E
        for req in ("factions { all, }", "factions { all }", "factions { all, } and resource gold",
                    "factions { roman, all, }"):
            self.assertTrue(available(Level("stone_wall", req), "athens", "greek"), req)
        self.assertFalse(available(Level("stone_wall", "factions { roman, }"), "athens", "greek"))
        self.assertTrue(available(Level("stone_wall", ""), "athens", "greek"))
        edb = TextFile.from_bytes("x.txt", (
            "building defenses\n{\n    levels stone_wall\n    {\n        stone_wall city requires factions { all, }\n"
            "        {\n            capability\n            {\n            }\n            construction 3\n"
            "            cost 800\n            settlement_min town\n            upgrades\n            {\n"
            "            }\n        }\n    }\n}\n").encode())
        self.assertIsNone(E.block_facets(edb, "building", ("defenses", 0, len(edb)))["factions"])

    def test_unit_voices_hear_and_put_in_own(self):
        """Sound packs read (a loose file wins over the pack), a unit's voice found by the owners' culture (Rome) or
        accent (Medieval II) and its voice_type, its name call replaced by the user's wav: a shared line split,
        a unit without one given a block in the file's own layout, events.dat / .idx removed; Restore byte for byte."""
        from campaign_editor import sounds as SN
        d = os.path.join(self.root, "data")
        wav = b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 22050, 44100, 2, 16) \
            + b"data" + struct.pack("<I", 0)
        folder = "data/sounds/Voice/Human/Localized/Battle_Map"
        names = [folder + "/Eastern_Heavy_1_name_x_1.wav", folder + "/Eastern_Heavy_1_Group_Created_1.wav"]
        idx, dat = bytearray(b"SND.PACK" + struct.pack("<4I", 4, len(names), len(names), len(wav) * 2)), b""
        for n in names:
            idx += struct.pack("<6I", 24 + len(dat), len(wav), 22050, 16, 1, 1) + n.encode() + b"\0abc"
            dat += wav
        os.makedirs(os.path.join(d, "sounds"))
        with open(os.path.join(d, "sounds", "Voice1.idx"), "wb") as f:
            f.write(bytes(idx))
        with open(os.path.join(d, "sounds", "Voice1.dat"), "wb") as f:
            f.write(b"PACKHEAD" * 3 + dat)
        for n in ("events.dat", "events.idx"):
            write(os.path.join(d, "sounds", n), "compiled")
        write(os.path.join(d, SN.VOICE_FILE),
              "BANK: unit_voice\n\tculture eastern,carthaginian\n\t\tclass Heavy_1\n\t\t\tvocal Group_Created\n"
              "\t\t\t\tevent\n\t\t\t\t\tfolder %s\n\t\t\t\t\tEastern_Heavy_1_Group_Created_1.wav\n\t\t\t\tend\n"
              "\t\t\tvocal Unit_Select\n\t\t\t\tunit alpha general,other unit\n\t\t\t\tevent\n"
              "\t\t\t\t\tfolder %s\n\t\t\t\t\tEastern_Heavy_1_name_x_1.wav\n\t\t\t\t\tgroup\n\t\t\t\tend\n" % (folder, folder))
        mod = ModData(self.root)
        index = SN.pack_index(mod)
        self.assertEqual(SN.find(mod, names[0], index)[0], "pack")
        self.assertEqual(SN.sound_bytes(mod, names[0].upper(), index), wav)
        events = SN.voice_events(mod.load(SN.voice_file(mod)))
        self.assertEqual([(e.vocal, e.target, e.names) for e in events],
                         [("Group_Created", None, []), ("Unit_Select", "unit", ["alpha general", "other unit"])])
        uv = SN.unit_voices(mod, events, "Alpha General", "Heavy_1", ["alpha"])
        self.assertEqual([(u.key, u.factions, u.known_class) for u in uv], [("eastern", ["alpha"], True)])
        self.assertEqual(uv[0].name_call.files, [names[0]])
        self.assertEqual([e.vocal for e in uv[0].orders], ["Group_Created"])
        self.assertFalse(SN.unit_voices(mod, events, "alpha general", "Light_1", ["alpha"])[0].known_class)
        # a loose file of that name wins
        write(os.path.join(d, "sounds", "voice", "human", "localized", "battle_map", "eastern_heavy_1_name_x_1.wav"),
              "LOOSE")
        self.assertEqual(SN.sound_bytes(mod, names[0], index), b"LOOSE")
        before = tree_hash(d)
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other)
        mine = os.path.join(other, "mine.wav")
        with open(mine, "wb") as f:
            f.write(wav)
        plan = Plan(mod, "voice", "unit_voice", {})
        got = SN.set_name_call(plan, "alpha general", "eastern", "Heavy_1", [mine])
        self.assertEqual(got, [folder + "/Eastern_Heavy_1_name_alpha_general_custom_1.wav"])
        text = plan.files[SN.voice_file(mod)].texts()
        self.assertIn("\t\t\t\tunit other unit", text)
        k = text.index("\t\t\t\tunit alpha general")
        self.assertEqual(text[k:k + 6], ["\t\t\t\tunit alpha general", "\t\t\t\tevent", "\t\t\t\t\tfolder " + folder,
                                         "\t\t\t\t\tEastern_Heavy_1_name_alpha_general_custom_1.wav",
                                         "\t\t\t\t\tgroup", "\t\t\t\tend"])
        with self.assertRaises(ValueError):
            SN.set_name_call(Plan(mod, "v", "v", {}), "alpha general", "eastern", "Heavy_1", [os.path.join(d, SN.VOICE_FILE)])
        bdir = plan.apply()
        self.assertFalse(os.path.exists(os.path.join(d, "sounds", "events.dat")))
        new = SN.voice_events(TextFile.load(SN.voice_file(mod)))
        again = SN.unit_voices(mod, new, "alpha general", "Heavy_1", ["alpha"])[0].name_call
        self.assertEqual(again.names, ["alpha general"])
        self.assertEqual(SN.sound_bytes(mod, again.files[0]), wav)
        # the same unit again: its own block is rewritten, the name not taken twice
        plan = Plan(mod, "voice", "unit_voice", {})
        self.assertEqual(SN.set_name_call(plan, "alpha general", "eastern", "Heavy_1", [mine]),
                         [folder + "/Eastern_Heavy_1_name_alpha_general_custom_2.wav"])
        b2 = plan.apply()
        restore(mod, b2)
        restore(mod, bdir)
        self.assertEqual(tree_hash(d), before)

    def test_replace_battle_model(self):
        """A unit's soldier model swapped for another of this mod or of another mod (brought with its files, renamed
        when the name is taken), the unit's factions given textures on it, a seat mismatch warned about, another
        game refused, Restore byte for byte."""
        from campaign_editor import models as MO
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_unit.txt"), EDU.replace(
            "ownership\talpha", "soldier\t\talpha_model, 20, 0, 1 ; the riders\nmount\t\tlight horse\nownership\talpha"))
        write(os.path.join(d, "descr_model_battle.txt"),
              "type\t\talpha_model\nskeleton\t\tfs_hc_swordsman\ntexture\t\talpha, data/models_unit/textures/a.tga\n"
              "model_flexi\t\tdata/models_unit/a.cas, max\n\n"
              "type\t\tfoot_model\nskeleton\t\tfs_spearman\ntexture\t\tslave, data/models_unit/textures/f.tga\n"
              "model_flexi\t\tdata/models_unit/f.cas, max\n\n"
              "type\t\thorse_model\nskeleton\t\tfs_medium_horse\n")
        write(os.path.join(d, "descr_mount.txt"), "type\t\tlight horse\nclass\t\thorse\nmodel\t\thorse_model\n")
        # another mod of the same game with a rider model of its own, whose name this mod has too
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other)
        shutil.copytree(self.root, os.path.join(other, "mod"))
        od = os.path.join(other, "mod", "data")
        write(os.path.join(od, "descr_model_battle.txt"),
              "type\t\tfoot_model\nskeleton\t\tfs_hc_spearman\ntexture\t\tmerc, data/models_unit/textures/o.tga\n"
              "model_flexi\t\tdata/models_unit/o.cas, max\n")
        write(os.path.join(od, "models_unit", "textures", "o.tga.dds"), "O-texture")
        write(os.path.join(od, "models_unit", "o.cas"), "O-model")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        cat = MO.catalogue(mod)
        self.assertEqual(cat["alpha_model"].seats, {"horse", "camel"})
        self.assertEqual(cat["foot_model"].seats, {"none"})
        lines = MO.unit_lines(mod, "alpha general")
        self.assertEqual(MO.unit_slots(lines), [("soldier", 0, "alpha_model")])
        self.assertEqual(MO.unit_seat(mod, lines), "horse")
        # this mod's foot model: the line swapped (the rest kept), alpha gets a texture, the seat warned about
        plan = Plan(mod, "model", "model", {})
        self.assertEqual(MO.replace(plan, "alpha general", "soldier", 0, "FOOT_MODEL"), "foot_model")
        edu = Strat(plan.files[mod.file("edu")]).lines
        self.assertIn("soldier\t\tfoot_model, 20, 0, 1 ; the riders", edu)
        dmb = "\n".join(plan.files[os.path.join(d, "descr_model_battle.txt")].texts())
        self.assertIn("texture\t\talpha, data/models_unit/textures/f.tga", dmb)
        self.assertTrue(any("on a horse" in w and "on foot" in w for _, w in plan.warnings))
        # from the other mod: brought in with its files as foot_model_2 (foot_model is taken here), no warning
        plan = Plan(ModData(self.root), "model", "model", {})
        got = MO.replace(plan, "alpha general", "soldier", 0, "foot_model", src_mod=ModData(os.path.join(other, "mod")))
        self.assertEqual(got, "foot_model_2")
        self.assertFalse(plan.warnings)
        bdir = plan.apply()
        m2 = ModData(self.root)
        self.assertEqual(MO.unit_slots(MO.unit_lines(m2, "alpha general")), [("soldier", 0, "foot_model_2")])
        self.assertIn("alpha", MO.catalogue(m2)["foot_model_2"].textures)
        self.assertTrue(os.path.exists(os.path.join(d, "models_unit", "o.cas")))
        restore(ModData(self.root), bdir)
        after = {k: v for k, v in tree_hash(self.root).items() if "_backups" not in k}
        self.assertEqual(after, before)
        # another game: refused
        os.makedirs(os.path.join(od, "unit_models"))
        with self.assertRaises(ValueError):
            MO.replace(Plan(ModData(self.root), "model", "model", {}), "alpha general", "soldier", 0, "foot_model",
                       src_mod=ModData(os.path.join(other, "mod")))

    def test_medieval_religions(self):
        # Medieval II: a ninth line per region, the religions
        from campaign_editor.edit import edit
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        text = REGIONS.replace("\t1\nB_R", "\t1\n\treligions { catholic 90 pagan 10 }\nB_R")
        write(os.path.join(camp, "descr_regions.txt"), text + "\treligions { catholic 20 pagan 80 }\n")
        mod = ModData(self.root)
        self.assertEqual(mod.regions("test")["A_R"]["religions"], {"catholic": 90, "pagan": 10})
        with self.assertRaises(ValueError):                             # not 100 in all
            edit(ModData(self.root), "test", "alpha", {"regions": {"religions": {"A_R": {"catholic": 50}}}})
        new = {"name": "N_R", "settlement": "Ntown", "creator": "alpha", "rebels": "Rebels", "resources": [],
               "city": (0, 3), "owner": None}
        plan = edit(mod, "test", "alpha", {"regions": {
            "painted": {(0, 3): "N_R", (1, 3): "N_R"}, "new": [new],
            "religions": {"A_R": {"catholic": 60, "pagan": 40}}}})
        plan.apply()
        regs = ModData(self.root).regions("test")
        self.assertEqual(regs["A_R"]["religions"], {"catholic": 60, "pagan": 40})
        self.assertEqual(regs["B_R"]["religions"], {"catholic": 20, "pagan": 80})
        self.assertEqual(regs["N_R"]["religions"], {"catholic": 90, "pagan": 10})     # A_R, where its land was

    def test_princess_takes_a_womans_name(self):
        from campaign_editor.strat import first_names
        pool = {"characters": ["Adam"], "women": ["Constance"]}
        self.assertEqual(first_names(pool, "princess"), ["Constance"])
        self.assertEqual(first_names(pool, "spy"), ["Adam"])

    def test_medieval_character_lines(self):
        from campaign_editor.strat import character_line
        m2 = ["character\tPhilip, named character, male, leader, age 40, x 113, y 131"]
        self.assertEqual(character_line(m2, "Adam", "general", 30, (1, 2)),
                         "character\tAdam, general, male, age 30, x 1, y 2")
        self.assertEqual(character_line(m2, "Constance", "princess", 19, (1, 2)),
                         "character\tConstance, princess, female, age 19, x 1, y 2")
        rome = ["character\tFlavius, named character, leader, age 47, , x 87, y 80"]
        self.assertEqual(character_line(rome, "Louis", "named character", 21, (1, 2), role="heir"),
                         "character\tLouis, named character, heir, age 21, , x 1, y 2")

    def test_resources(self):
        from campaign_editor import resources as R
        from campaign_editor.edit import edit
        path = os.path.join(self.root, "data", "world", "maps", "campaign", "test", "descr_strat.txt")
        with open(path) as fh:
            text = fh.read()
        with open(path, "w") as fh:
            fh.write(text.replace(";#####>", "resource\tiron,\t0,\t0\n\tresource\tgold, 1, 7, 3;\tAtown\n\n;#####>", 1))
        write(os.path.join(self.root, "data", "descr_sm_resources.txt"), "type\tiron\n\ntype\tgold\n\ntype\twine\n")
        mod = ModData(self.root)
        rs = R.read(mod.load(path))
        self.assertEqual([(r.kind, r.xy, r.quantity) for r in rs], [("iron", (0, 0), None), ("gold", (7, 3), 1)])
        self.assertEqual(list(R.types(mod)), ["iron", "gold", "wine"])
        with self.assertRaises(ValueError):                      # two on one tile
            edit(ModData(self.root), "test", "alpha", {"resources": {"moved": {"0": [3, 3]}, "added": [{"type": "wine", "xy": [3, 3]}]}})
        with self.assertRaises(ValueError):                      # an unknown type
            edit(ModData(self.root), "test", "alpha", {"resources": {"added": [{"type": "spice", "xy": [3, 3]}]}})
        plan = edit(mod, "test", "alpha", {"resources": {
            "moved": {"1": [2, 3]}, "removed": [0], "added": [{"type": "wine", "xy": [0, 3]}],
            "region_tags": {"A_R": "wine, iron"}}})
        bdir = plan.apply()
        m2 = ModData(self.root)
        with open(path) as fh:
            new = fh.read()
        self.assertIn("\tresource\tgold, 1, 2, 3;\tAtown\n", new)            # layout, quantity, comment kept
        self.assertIn("\nresource\twine,\t0,\t3\n", new)                    # the layout of a line without quantity
        self.assertNotIn("iron,", new)
        self.assertEqual(m2.regions("test")["A_R"]["resources"], "wine, iron")
        restore(m2, bdir)
        with open(path) as fh:
            self.assertIn("resource\tiron,\t0,\t0", fh.read())

    def test_rider_beside_mount(self):
        """3D view with its mount: rider and mount standing side by side on one ground, as the files keep them (a
        seat drawn over the horse looked wrong - the files hold the rider standing); the mount's parts take
        pictures 2 / 3."""
        from campaign_editor import meshview as MV
        rider = MV.Mesh([MV.Group("body", "m", [0, 1, 2], False)], [(0, -1.0, 0), (0, 0.9, 0), (0.2, 0, 0)],
                        [(0.1, 0.1)] * 3)
        horse = MV.Mesh([MV.Group("horse", "m", [0, 1, 2], False)], [(0, -1.9, 0), (0, 0.7, 2), (0.3, 0, 1)],
                        [(0.2, 0.2)] * 3)
        both = MV.combine(rider, rider.groups, horse, horse.groups, mount_one=True)
        self.assertEqual(both.count, 6)
        self.assertAlmostEqual(both.positions[0][1], -1.9)                       # feet on the horse's ground
        self.assertGreater(min(p[0] for p in both.positions[:3]), 0.3)           # beside it, not over it
        self.assertAlmostEqual(both.positions[0][2], 1.0)                        # at its middle
        self.assertEqual([getattr(g, "pic", 0) for g in both.groups], [0, 2])
        self.assertEqual(both.groups[1].tris, [3, 4, 5])
        self.assertTrue(both.groups[1].one)

    def test_mesh_variants_by_part(self):
        """3D view: the variants shown are counted per part (a tester read 'man 1 of 8' as eight men - it was the
        eight shields of highlanders, which have 4 heads, 2 bodies, 3 axes)."""
        from campaign_editor import meshview as MV
        g = lambda name, mat: MV.Group(name, mat, [0, 1, 2], False)
        mesh = MV.Mesh([g("Head", "h1"), g("Head", "h2"), g("Head", "h3"), g("Head", "h4"), g("Body", "b"),
                        g("primaryactive1", "a1"), g("primaryactive1", "a2"), g("primaryactive1", "a3")] +
                       [g("shield0", "s%d" % i) for i in range(8)], [(0, 0, 0)] * 3, [(0, 0)] * 3)
        self.assertEqual(mesh.variants(0), [("Head", 1, 4), ("weapon", 1, 3), ("shield", 1, 8)])
        self.assertEqual(mesh.variants(5, weapons=False), [("Head", 2, 4)])

    def test_label_table_few_colours(self):
        """The political map's palette table on a map with fewer than 256 colours (a tester's map would not open:
        IndexError in _labels)."""
        try:
            import PIL  # noqa: F401  (the map module needs Pillow; the CI test job has none)
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor.mapdata import label_table
        src = [(0, 0, 0), (10, 20, 30), (40, 50, 60)]
        where = {(10, 20, 30): (0, 1), (40, 50, 60): (1, 7)}
        t0, t1 = label_table(src, where, 0), label_table(src, where, 1)
        self.assertEqual(len(t0), 256)
        self.assertEqual(t0[:3], [0, 1, 0])
        self.assertEqual(t1[:3], [0, 0, 7])
        self.assertEqual(set(t0[3:]) | set(t1[3:]), {0})

    def test_faction_religion(self):
        """Medieval II: a faction's religion (descr_sm_factions.txt) read, changed in Edit, given to a new faction -
        the template keeps its own; a religion the game does not know is refused; Rome has none."""
        from campaign_editor.edit import edit, read_faction
        from campaign_editor.religions import faction_religion
        sm = os.path.join(self.root, "data", "descr_sm_factions.txt")
        self.assertIsNone(faction_religion(ModData(self.root), "alpha"))            # Rome: no religion line
        with open(sm) as fh:
            text = fh.read()
        write(sm, text.replace("culture\t\teastern\n", "culture\t\teastern\nreligion\t\tcatholic ; theirs\n", 1))
        write(os.path.join(self.root, "data", "descr_religions.txt"), "religions\n{\n    catholic\n    orthodox\n}\n")
        mod = ModData(self.root)
        self.assertEqual(read_faction(mod, "test", "alpha")["religion"], "catholic")
        with self.assertRaises(ValueError):
            edit(mod, "test", "alpha", {"religion": "jedi"})
        plan = edit(mod, "test", "alpha", {"religion": "orthodox"})
        bdir = plan.apply()
        with open(sm) as fh:
            self.assertIn("religion\t\torthodox ; theirs\n", fh.read())             # spacing and comment kept
        restore(ModData(self.root), bdir)
        plan = build(ModData(self.root), "test", "alpha", "beta", {"religion": "orthodox", "start": {
            "regions": ["B_R"], "leader": {"name": "Boris"}}})
        text = plan.files[sm].dump().decode().replace("\r\n", "\n")
        self.assertIn("faction\t\tbeta\nculture\t\teastern\nreligion\t\torthodox", text)
        self.assertIn("faction\t\talpha\nculture\t\teastern\nreligion\t\tcatholic", text)

    def test_dead_parents_record(self):
        """Parents added on the tree died before the start: Rome writes 'dead' (a dead man off the map may be
        any age), Medieval II the same (the game's world/template.txt: 'age 94, dead, past_leader'); a living man
        off the map older than the age of manhood is still refused."""
        from campaign_editor import family as FM
        texts = ["character_record\t\tMarcus, \tmale, command 0, influence 0, management 0, subterfuge 0, age 12, "
                 "alive, never_a_leader"]
        line = FM.record_line(texts, "Gaius", "male", 70, False, dead=True)
        self.assertIn("age 70, dead, never_a_leader", line)
        self.assertIn("alive,", FM.record_line(texts, "Gaius", "male", 10, False))
        m2 = ["character_record\t\tMatilda, \tfemale, age 49, alive, never_a_leader"]   # Medieval II's form
        self.assertEqual(FM.record_line(m2, "Odo", "male", 60, True, dead=True),
                         "character_record\t\tOdo, \tmale, age 60, dead, never_a_leader")
        after = [{"name": "Gaius", "sex": "male", "age": 70, "source": "record", "status": "dead"},
                 {"name": "Titus", "sex": "male", "age": 40, "source": "record", "status": "alive"}]
        self.assertEqual([n for n, _, _ in FM.record_age_problems(after, [], 16)], ["Titus"])

    def test_addon_setting_kinds_match_fast(self):
        """An add-on's list / set values are told in linear time (CodeQL py/redos: a long line of spaces between
        items backtracked exponentially), with commas or white space between items, a comma after the last."""
        import time
        from campaign_editor.addons import _kind
        for v in ('[]', '["a", "b",]', '[ "a" "b" ]', '{A=true, B = true,}', '{ A=true\n B=true // x\n}'):
            self.assertIn(_kind(v), ("list", "set"), v)
        for v in ('[,]', '["a",,"b"]', '{A=false}', '{A=true,,B=true}'):
            self.assertIsNone(_kind(v), v)
        t = time.time()
        _kind('["' + '"' + ' ""' * 20000 + ' x')
        _kind('{A=true' + ' A=true' * 20000 + ' x')
        self.assertLess(time.time() - t, 2)

    def test_campaign_map_figures(self):
        """Art tab, Figures on the campaign map: a faction's strat models read per character type; a figure changed
        in a faction line shared with others gets a line of its own (the others keep theirs); a model without the
        faction's texture gets one; the textures are Art pictures (picture_links); Restore byte for byte."""
        from campaign_editor import stratmodels as SM
        from campaign_editor.clone import picture_links
        from campaign_editor.edit import edit
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_character.txt"),
              "type\t\tnamed character\nactions\t\tmoving_normal\n\nfaction\t\talpha, slave ; both\n"
              "dictionary\t2\nstrat_model\tgeneral\nbattle_model\tg\n\ntype\t\tspy\n"
              "faction\t\talpha\ndictionary\t3\nstrat_model\tspy_a\n")
        write(os.path.join(d, "descr_model_strat.txt"),
              "type\t\tgeneral\nscale\t0.7\ntexture\t\talpha, data/models_strat/textures/gen_alpha.tga\n"
              "model_flexi\tdata/models_strat/gen.cas, max\n\ntype\t\tgeneral_b\n"
              "texture\t\tslave, data/models_strat/textures/gb_slave.tga\nmodel_flexi\tdata/models_strat/gb.cas, max\n"
              "\ntype\t\tspy_a\ntexture\t\talpha, data/models_strat/textures/spy_alpha.tga\n")
        mod = ModData(self.root)
        self.assertEqual([(f["type"], f["models"], f["shared"]) for f in SM.figures(mod, "alpha")],
                         [("named character", ["general"], ["slave"]), ("spy", ["spy_a"], [])])
        links = [l for l in picture_links(mod) if l["key"] == "model_strat"]
        self.assertEqual([(l["faction"], l["field"]) for l in links],
                         [("alpha", "texture:general"), ("slave", "texture:general_b"), ("alpha", "texture:spy_a")])
        before = tree_hash(d)
        plan = edit(mod, "test", "alpha", {"figures": {"named character": ["general_b"]}})
        ch = plan.files[mod.file("character")].texts()
        self.assertIn("faction\t\tslave ; both", ch)                   # the other keeps the shared entry
        i = ch.index("faction\t\talpha")
        self.assertEqual(ch[i + 1:i + 4], ["dictionary\t2", "strat_model\tgeneral_b", "battle_model\tg"])
        self.assertEqual(ch[ch.index("faction\t\tslave ; both") + 2], "strat_model\tgeneral")
        ms = plan.files[mod.file("model_strat")].texts()
        self.assertIn("texture\t\talpha, data/models_strat/textures/gb_slave.tga", ms)   # a texture to show it
        with self.assertRaises(ValueError):
            edit(mod, "test", "alpha", {"figures": {"spy": ["no_such_model"]}})
        bdir = plan.apply()
        self.assertEqual(SM.figures(ModData(self.root), "alpha")[0]["models"], ["general_b"])
        self.assertEqual(SM.figures(ModData(self.root), "slave")[0]["models"], ["general"])
        restore(ModData(self.root), bdir)
        self.assertEqual(tree_hash(d), before)

    def test_character_panel(self):
        """Character editor's panel: the attributes the traits and the retinue give (Medieval II: Authority for the
        leader, Dread when the chivalry is below 0), the traits by the level names players see (a .txt or the
        compiled .strings.bin), the retinue's names and pictures."""
        import struct
        from campaign_editor import charpanel as CP
        from campaign_editor import family as FM
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_character_traits.txt"),
              "Trait GoodCommander\n    Characters family\n\n    Level Good_Commander\n        Threshold  1\n"
              "        Effect Command  2\n        Effect Chivalry  -3\n\n    Level Great_Commander\n"
              "        Threshold  2\n        Effect Command  4\n")
        write(os.path.join(d, "export_descr_ancillaries.txt"),
              "Ancillary shieldbearer\n    Image shield_bearer.tga\n    Effect Command  1\n")
        # the compiled string table: u16 2, u16 2048, u32 count, then u16-counted UTF-16 key and text
        def entry(t):
            return struct.pack("<H", len(t)) + t.encode("utf-16-le")
        blob = struct.pack("<HHI", 2, 2048, 1) + entry("Good_Commander") + entry("A Good Commander")
        self.assertEqual(CP.read_strings_bin(blob), {"Good_Commander": "A Good Commander"})
        os.makedirs(os.path.join(d, "text"), exist_ok=True)
        with open(os.path.join(d, "text", "export_VnVs.txt.strings.bin"), "wb") as fh:
            fh.write(blob)
        mod = ModData(self.root)
        td, ad = FM.trait_list(mod), FM.ancillary_list(mod)
        self.assertEqual(td["GoodCommander"]["effects"], [[("Command", 2), ("Chivalry", -3)], [("Command", 4)]])
        self.assertEqual(ad["shieldbearer"]["image"], "shield_bearer.tga")
        attrs = CP.attributes("medieval2", "named character", "leader", [("GoodCommander", 1)], td,
                              ["shieldbearer"], ad)
        self.assertEqual(attrs, [("Command", 3), ("Dread", 3), ("Authority", 0), ("Piety", 0)])
        self.assertEqual(CP.attributes("rome", "spy", "", [], td, [], ad), [("Subterfuge", 0)])
        got = CP.panel(mod, {"name": "Aaron", "age": 40, "kind": "named character", "role": "leader", "source": "map",
                             "traits": [("GoodCommander", 1)], "ancillaries": ["shieldbearer"]}, td, ad)
        self.assertEqual(got["traits"], [("A Good Commander", "GoodCommander", 1, "+2 Command, -3 Chivalry")])
        self.assertEqual(got["retinue"][0][:2], ("shieldbearer", "shieldbearer"))        # no string: the key

    def test_traits_and_retinue_editor(self):
        """Tools > Traits and retinue: a level's threshold and effects changed in place, a trait copied under a new
        name (its levels and text keys renamed, the texts copied), an ancillary's effects and cultures; a text of a
        table Medieval II keeps only compiled (.strings.bin) goes into a .txt made from it; Restore byte for byte."""
        import struct
        from campaign_editor import traitsedit as TE
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_character_traits.txt"),
              ";------\nTrait GoodCommander\n    Characters family\n\n    Level Good_Commander\n"
              "        Description Good_Commander_desc\n        Threshold  1 \n\n        Effect Command  1 \n\n"
              "    Level Great_Commander\n        Description Great_Commander_desc\n        Threshold  3 \n\n"
              "        Effect Command  2 \n        Effect Loyalty  1 \n\n;------\nTrigger t1\n    WhenToTest X\n")
        write(os.path.join(d, "export_descr_ancillaries.txt"),
              "Ancillary healer\n    Image healer.tga\n    Description healer_desc\n    Effect HitPoints  2 \n")
        write(os.path.join(d, "text", "export_VnVs.txt"),
              "\u00ac texts\n{Good_Commander}\tGood Commander\n{Good_Commander_desc}\nKnows his men.\n\n"
              "{Great_Commander}\tGreat Commander\n", utf16=True)
        def entry(t):
            return struct.pack("<H", len(t)) + t.encode("utf-16-le")
        with open(os.path.join(d, "text", "export_ancillaries.txt.strings.bin"), "wb") as fh:
            fh.write(struct.pack("<HHI", 2, 2048, 2) + entry("healer") + entry("Healer") + entry("healer_desc") +
                     entry("Mends wounds."))
        before = tree_hash(d)
        mod = ModData(self.root)
        b = TE.blocks(mod.load(TE.file_of(mod, "trait")), "trait")
        self.assertEqual([(l["name"], l["threshold"][1], [(a, v) for _, a, v in l["effects"]])
                          for l in b["GoodCommander"]["levels"]],
                         [("Good_Commander", 1, [("Command", 1)]), ("Great_Commander", 3, [("Command", 2), ("Loyalty", 1)])])
        self.assertEqual(TE.parse_effects("Command 1, Loyalty -2"), [("Command", 1), ("Loyalty", -2)])
        with self.assertRaises(ValueError):
            TE.parse_effects("Command")
        plan = Plan(mod, "t", "t", {})
        TE.apply(plan, "trait", {"new": [["GoodCommander", "IronCommander"]],
                                 "edit": {"GoodCommander": {"levels": {"Great_Commander": {
                                     "threshold": 4, "effects": [["Command", 3]]}}}},
                                 "texts": {"Good_Commander": "A Fine Commander"}})
        TE.apply(plan, "ancillary", {"edit": {"healer": {"effects": [["HitPoints", 3], ["Piety", 1]],
                                                          "exclude": "roman"}},
                                     "texts": {"healer": "Physician"}})
        tr = plan.files[TE.file_of(mod, "trait")].texts()
        self.assertIn("        Threshold  4 ", tr)
        i = tr.index("    Level Great_Commander")
        self.assertIn("        Effect Command  3 ", tr[i:i + 6])
        self.assertNotIn("        Effect Loyalty  1 ", tr[i:i + 8])
        self.assertIn("Trait IronCommander", tr)
        self.assertIn("    Level Good_Commander_IronCommander", tr)
        self.assertIn("        Description Good_Commander_IronCommander_desc", tr)
        self.assertLess(tr.index("Trait IronCommander"), tr.index("Trigger t1"))          # among the traits
        vnv = plan.files[mod.text_file("export_VnVs.txt")].texts()
        self.assertIn("{Good_Commander}\tA Fine Commander", vnv)
        self.assertIn("{Good_Commander_IronCommander}\tGood Commander", vnv)           # the texts copied
        self.assertTrue(any(w for _, w in plan.warnings if "no trigger gives IronCommander" in w))
        an = plan.files[TE.file_of(mod, "ancillary")].texts()
        self.assertEqual([l.strip() for l in an if l.strip().startswith(("Effect", "ExcludeCultures"))],
                         ["ExcludeCultures roman", "Effect HitPoints  3", "Effect Piety  1"])
        made = os.path.join(d, "text", "export_ancillaries.txt")
        text = plan.binaries[made].decode("utf-16")
        self.assertIn("{healer}\tPhysician", text)
        self.assertIn("{healer_desc}\tMends wounds.", text)
        self.assertTrue(any("strings.bin" in w for _, w in plan.warnings))
        bdir = plan.apply()
        restore(ModData(self.root), bdir)
        self.assertEqual(tree_hash(d), before)

    def test_campaign_events(self):
        """Tools > Events: descr_events.txt read (a name used twice is name / name#2, as vanilla Rome's
        plague_in_italy), a date and place changed (the comment kept), one removed, a new one with its title in
        historic_events.txt; a date the game would not read refused; later factions with the script lines that
        wake them; Restore byte for byte."""
        from campaign_editor import events as EV
        from campaign_editor.plan import Plan
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        write(os.path.join(camp, "descr_events.txt"),
              "; events\nevent\tplague\tplague_in_x\ndate\t9 winter ; early\nposition\t1, 2\n\n"
              "event\thistoric\tnews\ndate\t14\n\nevent\tplague\tplague_in_x\ndate\t20 summer\n")
        write(os.path.join(self.root, "data", "text", "historic_events.txt"),
              "{NEWS_TITLE}\tNews\n{NEWS_BODY}\tSomething.\n", utf16=True)
        write(os.path.join(camp, "campaign_script.txt"), "script\n\tevent\temergent_faction\tslave\nend_script\n")
        before = tree_hash(os.path.join(self.root, "data"))
        mod = ModData(self.root)
        evs = EV.read(mod.load(EV.path_of(mod, "test")))
        self.assertEqual([(e["id"], e["date"], e["position"]) for e in evs],
                         [("plague_in_x", "9 winter", (1, 2)), ("news", "14", None), ("plague_in_x#2", "20 summer", None)])
        self.assertIsNone(EV.date_problem("14 winter", True))
        self.assertTrue(EV.date_problem("winter 14", True))
        self.assertTrue(EV.date_problem("14 winter", False))
        self.assertIsNone(EV.date_problem("210 220", False))
        plan = Plan(mod, "e", "e", {})
        EV.apply(plan, "test", {"edit": {"plague_in_x": {"date": "10 summer", "position": [3, 4]}},
                                "remove": ["plague_in_x#2"],
                                "new": [{"kind": "volcano", "name": "boom", "date": "30", "position": [5, 6],
                                         "title": "Boom!"}]})
        t = plan.files[EV.path_of(mod, "test")].texts()
        self.assertIn("date\t10 summer ; early", t)
        self.assertIn("position\t3, 4", t)
        self.assertEqual(sum(1 for l in t if l.startswith("event")), 3)              # one gone, one new
        self.assertIn("event\tvolcano\tboom", t)
        self.assertIn("{BOOM_TITLE}\tBoom!", plan.files[mod.text_file("historic_events.txt")].texts())
        # a historic event always gets its body - the game stops without one (event_manager: description_string)
        quiet = Plan(mod, "e", "e", {})
        EV.apply(quiet, "test", {"new": [{"kind": "historic", "name": "hush", "date": "31", "title": "Hush"}]})
        self.assertIn("{HUSH_BODY}\tHush", quiet.files[mod.text_file("historic_events.txt")].texts())
        # a disaster too: Medieval II opens a scroll for it with its own title and text (the test mod's
        # 'ce_test_plague' showed its bare name as both)
        sick = Plan(mod, "e", "e", {})
        EV.apply(sick, "test", {"new": [{"kind": "plague", "name": "ce_test_plague", "date": "32"}]})
        texts = sick.files[mod.text_file("historic_events.txt")].texts()
        self.assertIn("{CE_TEST_PLAGUE_TITLE}\tPlague", texts)
        self.assertTrue(any(l.startswith("{CE_TEST_PLAGUE_BODY}\tA plague has broken out") for l in texts))
        self.assertIn("{BOOM_BODY}\tThe volcano has erupted: buildings nearby are damaged and people have died.",
                      plan.files[mod.text_file("historic_events.txt")].texts())
        # a new event goes in date order - the games read the events as a queue (the author's Rome test mod: events
        # written at the end, after later ones, never came); the turn and year a date means
        early = Plan(mod, "e", "e", {})
        EV.apply(early, "test", {"new": [{"kind": "historic", "name": "first", "date": "0 winter", "title": "F"},
                                         {"kind": "earthquake", "name": "shake", "date": "15 summer"}]})
        names = [e["name"] for e in EV.read(early.files[EV.path_of(mod, "test")])]
        self.assertEqual(names, ["first", "plague_in_x", "news", "shake", "plague_in_x"])
        self.assertEqual(EV.date_key("1 winter", True), 3)
        self.assertEqual(EV.date_key("210 220", False), 210)
        with self.assertRaises(ValueError):
            EV.apply(Plan(mod, "e", "e", {}), "test", {"edit": {"news": {"date": "soon"}}})
        self.assertIn("plague", EV.what_it_does("plague").lower())
        self.assertEqual(EV.picture_name("news", "historic"), "news")                    # its own picture
        self.assertEqual(EV.picture_name("plague_in_x", "plague"), "disaster_plague")    # shared by its kind
        bdir = plan.apply()
        restore(ModData(self.root), bdir)
        self.assertEqual(tree_hash(os.path.join(self.root, "data")), before)
        try:
            from PIL import Image
        except ImportError:
            return
        for c in ("roman", "greek"):
            os.makedirs(os.path.join(self.root, "data", "ui", c, "eventpics"), exist_ok=True)
        src = os.path.join(self.root, "pic.png")
        Image.new("RGB", (50, 20), (9, 9, 9)).save(src)
        mod = ModData(self.root)
        self.assertEqual(EV.picture_files(mod, "news", "historic"), {"greek": None, "roman": None})
        plan = Plan(mod, "e", "e", {})
        EV.apply(plan, "test", {"pictures": {"news": src}})
        plan.apply()
        got = EV.picture_files(ModData(self.root), "news", "historic")
        self.assertTrue(all(got.values()))
        self.assertEqual(Image.open(got["roman"]).size, (360, 160))                      # Rome's own size

    def test_rome_pak_read(self):
        """Rome's data/packs/*.pak: the name table, the end offsets, the files one after another - a file not loose
        on disk is read from the pack (x.tga found as x.tga.dds too)."""
        import struct
        from campaign_editor import rompak as RP
        names = ["DATA\\MODELS_UNIT\\TEXTURES\\A.TGA.DDS", "DATA\\UI\\B.TGA"]
        table = "".join(n + "\0" for n in names)
        files = [b"first-file", b"second"]
        start = 12 + len(table) * 2 + 4 * len(names)
        ends, at = [], start
        for f in files:
            at += len(f)
            ends.append(at)
        blob = b"PAK0" + struct.pack("<II", len(table), len(names)) + table.encode("utf-16-le") + \
            struct.pack("<%dI" % len(ends), *ends) + b"".join(files)
        os.makedirs(os.path.join(self.root, "data", "packs"), exist_ok=True)
        with open(os.path.join(self.root, "data", "packs", "x.pak"), "wb") as fh:
            fh.write(blob)
        mod = ModData(self.root)
        self.assertEqual(sorted(RP.read_index(os.path.join(self.root, "data", "packs", "x.pak"))),
                         ["data/models_unit/textures/a.tga.dds", "data/ui/b.tga"])
        self.assertEqual(RP.find(mod, "data/models_unit/textures/a.tga"), b"first-file")
        self.assertEqual(RP.find(mod, "ui/B.tga"), b"second")
        self.assertIsNone(RP.find(mod, "ui/c.tga"))

    def test_religion_web(self):
        """A faction's religion changed (Medieval II): it leaves the old faith's buildings (levels and the priest
        lines in them) and gets the new faith's where a faction of that faith (of its own culture first) has them;
        its priest figure follows; the faction of the old faith keeps its own; Restore byte for byte."""
        from campaign_editor.edit import edit
        d = os.path.join(self.root, "data")
        sm = os.path.join(d, "descr_sm_factions.txt")
        with open(sm) as fh:
            text = fh.read()
        text = text.replace("culture\t\teastern\n", "culture\t\teastern\nreligion\t\torthodox\n", 1)
        beta = text[text.index("faction\t\talpha"):text.index("faction\t\tslave")].replace("alpha", "beta")
        beta = beta.replace("religion\t\torthodox", "religion\t\tcatholic")
        write(sm, text.replace("faction\t\tslave", beta + "faction\t\tslave", 1))
        write(os.path.join(d, "descr_religions.txt"), "religions\n{\n    catholic\n    orthodox\n}\n")
        def temple(rel, level, who):
            return ("building temple_%s\n{\n    religion %s\n    levels %s\n    {\n"
                    "        %s city requires factions { %s, }\n        {\n            capability\n            {\n"
                    "                agent priest  0  requires factions { %s, }\n            }\n        }\n    }\n}\n"
                    % (rel, rel, level, level, who, who))
        write(os.path.join(d, "export_descr_buildings.txt"), temple("orthodox", "church", "alpha") +
              temple("catholic", "chapel", "beta"))
        write(os.path.join(d, "descr_character.txt"),
              "type\t\tpriest\nfaction\t\talpha\ndictionary\t1\nstrat_model\torthodox_priest\n\n"
              "faction\t\tbeta\ndictionary\t1\nstrat_model\tcatholic_priest\n")
        write(os.path.join(d, "descr_model_strat.txt"),
              "type\t\torthodox_priest\ntexture\t\talpha, data/x.tga\n\ntype\t\tcatholic_priest\n"
              "texture\t\tbeta, data/y.tga\n")
        before = tree_hash(d)
        mod = ModData(self.root)
        plan = edit(mod, "test", "alpha", {"religion": "catholic"})
        edb = plan.files[mod.file("edb")].texts()
        self.assertIn("        church city requires factions { }", edb)                # left the old faith's
        self.assertIn("                agent priest  0  requires factions { }", edb)
        self.assertIn("        chapel city requires factions { beta, alpha, }", edb)   # got the new faith's
        self.assertIn("                agent priest  0  requires factions { beta, alpha, }", edb)
        ch = plan.files[mod.file("character")].texts()
        self.assertEqual(ch[3], "strat_model\tcatholic_priest")                         # its priest figure
        self.assertIn("texture\t\talpha, data/y.tga", plan.files[mod.file("model_strat")].texts())
        self.assertTrue(any("not changed" in w for _, w in plan.warnings))
        bdir = plan.apply()
        restore(ModData(self.root), bdir)
        self.assertEqual(tree_hash(d), before)

    def test_wasteland_region(self):
        """REX / M2EX wasteland regions ('wasteland' where the town stands; the 3-line form too): no settlement, no
        rebels read from it; Check mod does not ask for its town pixel (a tester's Sahara_Province)."""
        from campaign_editor.check import check_mod
        from campaign_editor.moddata import region_entries
        from campaign_editor.textio import TextFile
        f = TextFile.from_bytes("x", (REGIONS + "Sahara\n\twasteland\n\t9 9 9\nGobi\n\twasteland\n\tslave\n"
                                      "\tRebels\n\t8 8 8\n\tnone\n\t5\n\t1\n").encode())
        e = region_entries(f)
        self.assertNotIn("settlement", e["Sahara"])
        self.assertNotIn("rebels", e["Sahara"])
        self.assertIn("wasteland", e["Sahara"])
        self.assertIn("wasteland", e["Gobi"])
        self.assertEqual(e["Gobi"]["rebels"][1], "Rebels")
        camp = os.path.join(self.root, "data", "world", "maps", "base", "descr_regions.txt")
        if not os.path.exists(camp):
            camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test", "descr_regions.txt")
        write(camp, REGIONS + "Sahara\n\twasteland\n\t9 9 9\n")
        mod = ModData(self.root)
        self.assertTrue(mod.regions("test")["Sahara"]["wasteland"])
        rep = check_mod(mod, "test")
        self.assertNotIn("without a town pixel", rep)
        self.assertIn("wasteland regions", rep)

    def test_path_guard(self):
        """Every write of a Plan and every Restore stays inside the mod's / game's folder: '../', a link that leads
        out and a crafted backup manifest are refused before anything is written."""
        import json
        from campaign_editor import guard
        from campaign_editor.plan import Plan
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside, True)
        mod = ModData(self.root)
        victim = os.path.join(outside, "victim.txt")
        write(victim, "keep me")
        # a binary / copy whose path climbs out of the mod
        for make in (lambda p: p.binary(os.path.join(self.root, "..", os.path.basename(outside), "victim.txt"), b"x"),
                     lambda p: p.copy(os.path.join(self.root, "data", "descr_sm_factions.txt"),
                                      os.path.join(outside, "copied.txt"))):
            plan = Plan(mod, "t", "t")
            make(plan)
            with self.assertRaises(guard.OutsideError):
                plan.apply()
        self.assertEqual(open(victim).read(), "keep me")
        self.assertFalse(os.path.exists(os.path.join(outside, "copied.txt")))
        # a link inside the mod that leads out
        if hasattr(os, "symlink"):
            link = os.path.join(self.root, "data", "out_link")
            try:
                os.symlink(outside, link)
            except OSError:
                link = None
            if link:
                plan = Plan(mod, "t", "t")
                plan.binary(os.path.join(link, "victim.txt"), b"x")
                with self.assertRaises(guard.OutsideError):
                    plan.apply()
                self.assertEqual(open(victim).read(), "keep me")
                os.remove(link)
        # a normal write passes, and its backup restores
        plan = Plan(mod, "t", "t")
        plan.binary(os.path.join(self.root, "data", "new.bin"), b"ok")
        bdir = plan.apply()
        self.assertTrue(guard.inside(os.path.join(self.root, "data", "new.bin"), self.root))
        # a crafted manifest that names a file outside is refused - the victim stays
        with open(os.path.join(bdir, "manifest.json"), "w") as fh:
            json.dump({"faction": "t", "template": "t", "modified": [], "created": [
                "../" + os.path.basename(outside) + "/victim.txt"]}, fh)
        with self.assertRaises(guard.OutsideError):
            restore(mod, bdir)
        self.assertEqual(open(victim).read(), "keep me")

    def test_addon_goes_where_rex_loads_it(self):
        """REX's own script/main.nut (squi) requires every .nut of the game's script/modules; a mod with a script
        plugin of its own (HLR: manifest.nut + main.nut, no module loading) would never run one put beside it - so
        the add-on goes to the game's script/modules. Its code already pasted into the mod's scripts is refused."""
        from campaign_editor import addons as AD
        game = tempfile.mkdtemp()
        open(os.path.join(game, "REX.exe"), "wb").close()
        write(os.path.join(game, "script", "main.nut"),
              'foreach (name in ::scripting.listModules("modules")) { require(name) }\n')
        data = os.path.join(game, "HLR", "data")
        write(os.path.join(data, "descr_sm_factions.txt"), "")
        write(os.path.join(game, "HLR", "script", "manifest.nut"), 'return { name = "HLR" entry = "main" }\n')
        write(os.path.join(game, "HLR", "script", "main.nut"), 'let events = require("game.events")\n')
        mod = ModData(data)
        sack = AD.by_key("sack_settlement")
        self.assertEqual(os.path.normcase(AD.target(mod, sack)),
                         os.path.normcase(os.path.join(game, "script", "modules", "sack_settlement.nut")))
        self.assertEqual(AD.marker(sack), "[SACK]")
        self.assertFalse(AD.already_in_scripts(mod, sack))
        write(os.path.join(game, "HLR", "script", "main.nut"),
              'let events = require("game.events")\nlocal PREFIX = "[SACK] "\n')
        self.assertTrue(any("main.nut" in p for p in AD.already_in_scripts(mod, sack)))
        self.assertTrue(any("run twice" in x for x in AD.check(sack, {}, mod)))

    def test_addons_from_anyone(self):
        import zipfile
        from unittest import mock
        from campaign_editor import addons as AD
        script = (
            "// Border Tolls - a toll at every border crossing\n"
            "// @game both\n"
            "// @pick TOLL_FACTIONS factions\n"
            "// @label TOLL_GOLD Money per crossing\n"
            "\n"
            "// switch it off without taking it out\n"
            "local TOLL_ON = true\n"
            "local TOLL_GOLD = 25 // paid by the one who crosses\n"
            "local TOLL_TEXT = \"Toll paid\"\n"
            "local TOLL_FACTIONS = [\"romans_julii\"]\n"
            "local TOLL_SKIP = { slave = true, // the rebels never pay\n}\n"
            "local TOLL_RATE = 0.5\n"
            "local helper = 3\n"
            "function toll() {}\n")
        a = AD.from_script(script, "border_tolls.nut")
        self.assertEqual((a.title, a.game), ("Border Tolls", "both"))
        self.assertTrue(a.fits("rome") and a.fits("medieval2"))
        kinds = {s.var: s.kind for s in a.settings}
        self.assertEqual(kinds, {"TOLL_ON": "bool", "TOLL_GOLD": "int", "TOLL_TEXT": "text",
                                 "TOLL_FACTIONS": "list", "TOLL_SKIP": "set"})       # 0.5 and lower case left out
        help_ = {s.var: s.help for s in a.settings}
        self.assertEqual(help_["TOLL_ON"], "switch it off without taking it out")
        self.assertEqual(help_["TOLL_GOLD"], "paid by the one who crosses")
        self.assertEqual(next(s.label for s in a.settings if s.var == "TOLL_GOLD"), "Money per crossing")
        self.assertEqual(a.picks, {"TOLL_FACTIONS": "factions"})
        self.assertEqual(AD.read_settings(a, script)["TOLL_SKIP"], ["slave"])
        lib = os.path.join(self.root, "addons")
        src = os.path.join(self.root, "share.zip")
        with mock.patch.object(AD, "library_dir", return_value=lib):
            with open(os.path.join(self.root, "border_tolls.nut"), "w") as fh:
                fh.write(script)
            got = AD.add_to_library(os.path.join(self.root, "border_tolls.nut"))
            self.assertEqual([x.key for x in got], ["border_tolls"])
            self.assertIn("border_tolls", [x.key for x in AD.library()])
            own = AD.by_key("border_tolls")
            self.assertTrue(own.own)
            # Share: the script with the picked settings and a README; a zip's folders never reach the disk
            AD.share(own, src, {"TOLL_GOLD": 40})
            with zipfile.ZipFile(src) as z:
                self.assertIn("local TOLL_GOLD = 40", z.read("border_tolls.nut").decode())
                self.assertIn("script/modules", z.read("README.txt").decode())
            evil = os.path.join(self.root, "evil.zip")
            with zipfile.ZipFile(evil, "w") as z:
                z.writestr("../../outside/evil_mod.nut", "local X = 1\n")
            AD.add_to_library(evil)
            self.assertTrue(os.path.isfile(os.path.join(lib, "evil_mod.nut")))
            self.assertFalse(os.path.exists(os.path.join(self.root, "outside")))
            with self.assertRaises(ValueError):
                AD.add_to_library(os.path.join(self.root, "notes.txt"))              # not a script
            with self.assertRaises(ValueError):                       # the built-in one is not added twice
                with open(os.path.join(self.root, "sack_settlement.nut"), "w") as fh:
                    fh.write("local A = 1\n")
                AD.add_to_library(os.path.join(self.root, "sack_settlement.nut"))
            AD.remove_from_library(own)
            self.assertNotIn("border_tolls", [x.key for x in AD.library()])

    def test_forts_moved_removed_added(self):
        from campaign_editor import forts as FT
        from campaign_editor.edit import edit
        path = os.path.join(self.root, "data", "world", "maps", "campaign", "test", "descr_strat.txt")
        with open(path, "rb") as fh:
            before = fh.read()
        # Barbarian Invasion keeps its watchtowers after the diplomacy, under the regions
        with open(path, "wb") as fh:
            fh.write(before + b"\nregion A_R\nwatchtower \t2 3\n\nwatchtower \t0 3 ; west\n")
        mod = ModData(self.root)
        now = FT.read(mod, "test")
        self.assertEqual([(f.kind, f.xy) for f in now], [("watchtower", (2, 3)), ("watchtower", (0, 3))])
        self.assertIn("fort", FT.no_example("fort"))
        # no fort line to copy: written under its region in the regions section (the form both exes read there)
        p2 = edit(ModData(self.root), "test", "alpha", {"resources": {"forts": {"added": [{"kind": "fort", "xy": [3, 3]}]}}})
        b2 = p2.apply()
        with open(path) as fh:
            self.assertIn("\nregion B_R\nroad_level 0\nfarming_level 0\nfamine_threat 0\nfort\t3 3", fh.read())
        restore(ModData(self.root), b2)
        with self.assertRaises(ValueError):                  # two on one tile
            edit(ModData(self.root), "test", "alpha", {"resources": {"forts": {"moved": {str(now[0].line): [0, 3]}}}})
        plan = edit(mod, "test", "alpha", {"resources": {"forts": {
            "moved": {str(now[0].line): [3, 3]}, "removed": [now[1].line],
            "added": [{"kind": "watchtower", "xy": [2, 3]}]}}})
        bdir = plan.apply()
        with open(path) as fh:
            new = fh.read()
        self.assertIn("region A_R\nwatchtower \t3 3\nwatchtower \t2 3\n", new)     # layout kept, new after it
        self.assertNotIn("0 3 ; west", new)
        restore(ModData(self.root), bdir)
        with open(path, "rb") as fh:
            self.assertEqual(fh.read(), before + b"\nregion A_R\nwatchtower \t2 3\n\nwatchtower \t0 3 ; west\n")

    def test_garrison_emptied_by_hand(self):
        from campaign_editor.edit import edit
        mod = ModData(self.root)
        path = mod.campaign_file("test", "descr_strat.txt")
        with open(path) as fh:
            text = fh.read()
        with open(path, "w") as fh:                       # Aaron has a unit besides his bodyguard
            fh.write(text.replace("weapon_lvl 0\n;#####<", "weapon_lvl 0\nunit\t\trebel spear\t\texp 0 armour 0 weapon_lvl 0\n;#####<", 1))
        plan = edit(ModData(self.root), "test", "alpha", {"garrisons": {"A_R": []}})
        s = Strat(plan.files[path])
        c = s.faction("alpha").characters[0]
        units = [l.split("\t")[2] for l in s.lines[c.start:c.end] if l.startswith("unit")]
        self.assertEqual(units, ["alpha general"])        # the named man keeps only his bodyguard

    def test_ships_owned_by_culture(self):
        # vanilla gives ships to cultures ("ownership roman, greek"), not factions
        with open(os.path.join(self.root, "data", "export_descr_unit.txt"), "a") as fh:
            fh.write("\ntype\t\teastern bireme\ndictionary\teastern_bireme\ncategory\tship\nownership\teastern\n")
        from campaign_editor.units import faction_units
        mod = ModData(self.root)
        self.assertEqual([u.type for u in faction_units(mod, "alpha", ships=True)], ["eastern bireme"])
        self.assertNotIn("eastern bireme", [u.type for u in faction_units(mod, "alpha")])

    def test_campaign_screen_key_under_a_front_end_name(self):
        # the template's description sits under a front end name (like GAUL for gauls)
        from campaign_editor import clone
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


    def test_every_module_compiles(self):
        # the window is not imported by the other tests: a syntax error there (a stray
        # backslash in a text) once built an exe with none of the tool in it
        import glob
        import py_compile
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for p in glob.glob(os.path.join(here, "campaign_editor", "*.py")) + [os.path.join(here, "campaign_editor.py")]:
            py_compile.compile(p, cfile=os.path.join(self.root, "x.pyc"), doraise=True)

    def test_unit_and_building_editors(self):
        from campaign_editor import editors as E
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        with open(os.path.join(d, "export_descr_unit.txt"), "a") as fh:
            fh.write("\ntype\t\tbeta spear\ndictionary\tbeta_spear\t; the card name\n"
                     "stat_cost\t1, 400, 170, 60, 70, 400\nownership\talpha\n")
        write(os.path.join(d, "export_descr_buildings.txt"),
              "building core_building\n{\n    levels hut house\n    {\n        hut requires factions { alpha, }\n"
              "        {\n            settlement_min village\n            construction  2\n        }\n    }\n}\n")
        mod = ModData(self.root)
        edu_path = mod.file("edu")
        f = mod.load(edu_path)
        blocks = E.unit_blocks(f)
        self.assertEqual([b[0] for b in blocks], ["alpha general", "rebel spear", "beta spear"])
        fs = E.fields(f, blocks[2][1], blocks[2][2])
        cost = next(x for x in fs if x.key == "stat_cost")
        self.assertEqual(cost.value, "1, 400, 170, 60, 70, 400")
        dic = next(x for x in fs if x.key == "dictionary")
        self.assertEqual(dic.value, "beta_spear")
        edb = mod.load(mod.file("edb"))
        (chain, a, b), = E.building_blocks(edb)
        self.assertEqual(chain, "core_building")
        turns = next(x for x in E.fields(edb, a, b) if x.key == "construction")
        self.assertEqual((turns.value, turns.depth), ("2", 3))
        # a picture for the card, from a PNG (Pillow: in the exe; the CI test run may lack it)
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        png = os.path.join(self.root, "card.png")
        Image.new("RGB", (100, 80), (0, 128, 0)).save(png)
        plan = Plan(mod, "units", "units", {})
        E.apply_fields(plan, edu_path, {cost.line: "1, 500, 170, 60, 70, 500", dic.line: "beta_spear"}, "unit beta spear")
        E.apply_fields(plan, mod.file("edb"), {turns.line: "3"}, "core_building hut")
        targets = E.unit_picture_targets(mod, "beta_spear", ["alpha"])
        E.import_picture(plan, png, targets, (48, 64))
        bdir = plan.apply()
        with open(edu_path) as fh:
            text = fh.read()
        self.assertIn("stat_cost\t1, 500, 170, 60, 70, 500\n", text)
        self.assertIn("dictionary\tbeta_spear\t; the card name\n", text)      # the comment kept
        with open(mod.file("edb")) as fh:
            self.assertIn("            construction  3\n", fh.read())
        self.assertEqual(E.tga_info(targets[0]), (48, 64, 32))
        restore(ModData(self.root), bdir)
        self.assertFalse(os.path.exists(targets[0]))                     # Restore removes the new card
        with open(edu_path) as fh:
            self.assertIn("stat_cost\t1, 400, 170", fh.read())

    def test_faction_art_and_select_map(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor import factionart as FA
        camp = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        os.remove(os.path.join(camp, "map_alpha.tga"))
        with open(os.path.join(self.root, "data", "descr_sm_factions.txt"), "a") as fh:
            fh.write("\nfaction\t\tgamma\nculture\t\teastern\n;;;;;;;;\n")
        for n in ("alpha", "gamma", "slave", "heights"):      # three maps of one background; map_heights is no faction's
            Image.new("RGB", (8, 8), (100, 100, 100)).save(os.path.join(camp, "map_%s.tga" % n))
        menu = os.path.join(self.root, "data", "menu", "symbols", "FE_buttons_24")
        os.makedirs(menu)
        for n in ("symbol24_alpha.tga", "symbol24_alpha_roll.tga"):
            Image.new("RGBA", (30, 30), (1, 2, 3, 255)).save(os.path.join(menu, n))
        mod = ModData(self.root)
        labels = {p["label"] for p in FA.faction_pictures(mod, "test", "alpha")}
        self.assertIn("small campaign-menu button (mouse over)", labels)
        self.assertIn("campaign-select map (its land lit)", labels)
        png = os.path.join(self.root, "button.png")
        Image.new("RGB", (64, 64), (200, 0, 0)).save(png)
        plan = build(mod, "test", "alpha", "beta", {
            "start": {"regions": ["B_R"], "leader": {"name": "Boris"}},
            "art": {"menu/symbols/FE_buttons_24/symbol24_beta_roll.tga": png},
            "select_map": {"on": True, "colour": [0, 200, 0]}})
        plan.apply()
        roll = os.path.join(menu, "symbol24_beta_roll.tga")
        self.assertEqual(FA.tga_info(roll), (30, 30, 32))                # the template's size and depth
        self.assertEqual(Image.open(roll).convert("RGB").getpixel((5, 5)), (200, 0, 0))
        sel = Image.open(os.path.join(camp, "map_beta.tga")).convert("RGB")
        self.assertEqual(sel.size, (8, 8))
        # B_R (blue) is the right half of the 4 x 4 region map: lit green there, grey on the left
        self.assertGreater(sel.getpixel((7, 4))[1], 150)
        self.assertEqual(sel.getpixel((0, 4)), (100, 100, 100))
        # a new region carved out of the rebels' B_R for alpha: alpha's map lights it at once
        from campaign_editor.edit import edit
        new = {"name": "N_R", "settlement": "Ntown", "creator": "alpha", "rebels": "Rebels", "resources": [],
               "city": (3, 0), "owner": "alpha", "level": "village"}
        mod = ModData(self.root)
        painted = {(3, 0): "N_R", (2, 0): "N_R", (2, 1): "N_R", (3, 1): "N_R"}
        # not asked for: every select map stays the original
        plan = edit(mod, "test", "alpha", {"regions": {"painted": painted, "new": [new]}})
        self.assertFalse([p for p in plan.binaries if os.path.basename(p).startswith("map_")
                          and "regions" not in p])
        plan = edit(mod, "test", "alpha", {"regions": {"painted": painted, "new": [new]}, "select_map": {"on": True}})
        plan.apply()
        am = Image.open(os.path.join(camp, "map_alpha.tga")).convert("RGB")
        self.assertNotEqual(am.getpixel((7, 7)), (100, 100, 100))            # (3, 0) is the bottom right corner

    def test_faction_picture_links(self):
        """Banners / loading logo are named by path: a clone gets files of its own (the template's
        stay untouched), a shared picture replaced becomes the faction's own copy, a DDS stays a
        DDS, and Back to the original finds what the tool changed."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is not installed")
        from campaign_editor import factionart as FA
        d = os.path.join(self.root, "data")
        with open(os.path.join(d, "descr_sm_factions.txt"), "rb") as fh:
            sm = fh.read().decode("latin-1").replace(
                "culture\t\teastern\r\n", "culture\t\teastern\r\nloading_logo\t\tloading_screen/symbols/symbol128_alpha.tga\r\n")
        write(os.path.join(d, "descr_sm_factions.txt"), sm.replace("\r\n", "\n"))
        write(os.path.join(d, "descr_banners.txt"),
              "faction\t\talpha\nstandard_texture\tmodels/textures/standard_alphan.tga\n"
              "rebels_texture\t\tmodels/textures/standard_rebels.tga\n"
              "ally_texture\t\tmodels/textures/standard_alphan_ally.tga\n\n"
              "faction\t\tslave\nstandard_texture\tmodels/textures/standard_slave.tga\n"
              "rebels_texture\t\tmodels/textures/standard_rebels.tga\n")
        tex = os.path.join(d, "models", "textures")
        os.makedirs(tex)

        def dds(path, colour, levels=3):                  # a DXT5 texture with mipmaps, as Rome keeps them
            import io
            parts = []
            for k in range(levels):
                buf = io.BytesIO()
                Image.new("RGBA", (16 >> k, 16 >> k), colour).save(buf, format="DDS", pixel_format="DXT5")
                parts.append(buf.getvalue())
            head = bytearray(parts[0][:128])
            head[28:32] = levels.to_bytes(4, "little")
            with open(path, "wb") as fh:
                fh.write(bytes(head) + b"".join(p[128:] for p in parts))
        for n in ("standard_alphan", "standard_alphan_ally", "standard_rebels", "standard_slave"):
            dds(os.path.join(tex, n + ".tga.dds"), (10, 20, 30, 255))
        logo = os.path.join(d, "loading_screen", "symbols")
        os.makedirs(logo)
        Image.new("RGBA", (128, 128), (1, 2, 3, 255)).save(os.path.join(logo, "symbol128_alpha.tga"))
        self.assertEqual(FA.own_picture_ref("models/textures/standard_macedonia_ally.tga", "macedon", "epirus"),
                         "models/textures/standard_epirus_ally.tga")
        self.assertEqual(FA.own_picture_ref("models/textures/standard_julii.tga", "romans_julii", "epirus"),
                         "models/textures/standard_epirus.tga")
        self.assertEqual(FA.own_picture_ref("models/textures/standard_greek_rebels.tga", "macedon", "epirus"),
                         "models/textures/standard_greek_rebels_epirus.tga")
        # a clone still naming its template's logo (packed in the game, so not copied): its own copy is named
        # after it, not '<template>_<new>' (the author's M2TW test mod made symbol128_england_ce_test)
        packed = {"link": ["sm_factions", "loading_logo"], "ref": "loading_screen/symbols/symbol128_england.tga",
                  "rel": "loading_screen/symbols/symbol128_england.tga", "shared": ["england"]}
        self.assertEqual(FA.picture_target(packed, "ce_test", "ce_test"), "loading_screen/symbols/symbol128_ce_test.tga")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
        plan.apply()
        with open(os.path.join(d, "descr_banners.txt")) as fh:
            banners = fh.read()
        beta = banners[banners.index("faction\t\tbeta"):]
        self.assertIn("models/textures/standard_beta.tga", beta)
        self.assertIn("models/textures/standard_beta_ally.tga", beta)
        self.assertIn("models/textures/standard_rebels.tga", beta)          # shared: stays shared
        self.assertIn("standard_texture\tmodels/textures/standard_alphan.tga", banners)
        self.assertTrue(os.path.isfile(os.path.join(tex, "standard_beta.tga.dds")))
        with open(os.path.join(d, "descr_sm_factions.txt")) as fh:
            self.assertIn("loading_screen/symbols/symbol128_beta.tga", fh.read())
        self.assertTrue(os.path.isfile(os.path.join(logo, "symbol128_beta.tga")))
        # the Art list: beta's own banner; the rebels' banner shared with alpha and slave
        mod = ModData(self.root)
        pics = {p["rel"]: p for p in FA.faction_pictures(mod, "test", "beta")}
        own = pics["models/textures/standard_beta.tga.dds"]
        self.assertEqual((own["link"], own["shared"], own["size"]), (["banners", "standard_texture"], [], (16, 16, "DXT5")))
        reb = pics["models/textures/standard_rebels.tga.dds"]
        self.assertEqual(reb["shared"], ["alpha", "slave"])
        target = FA.picture_target(reb, "beta", "beta")
        self.assertEqual(target, "models/textures/standard_rebels_beta.tga.dds")
        png = os.path.join(self.root, "flag.png")
        Image.new("RGB", (40, 40), (200, 0, 0)).save(png)
        from campaign_editor.edit import edit
        plan = edit(mod, "test", "beta", {"art": {target: {"src": png, "link": reb["link"]},
                                                  own["rel"]: png}})
        plan.apply()
        with open(os.path.join(d, "descr_banners.txt")) as fh:
            banners = fh.read()
        self.assertIn("rebels_texture\t\tmodels/textures/standard_rebels_beta.tga", banners)
        self.assertEqual(banners.count("models/textures/standard_rebels.tga"), 2)   # alpha's and slave's lines
        got = FA.dds_info(os.path.join(tex, "standard_rebels_beta.tga.dds"))
        self.assertEqual(got, (16, 16, "DXT5", 3))                          # the shared one's size, format, mipmaps
        im = Image.open(os.path.join(tex, "standard_rebels_beta.tga.dds")).convert("RGB")
        self.assertEqual(im.size, (16, 16))
        self.assertGreater(im.getpixel((8, 8))[0], 180)
        with Image.open(os.path.join(tex, "standard_rebels.tga.dds")) as a, \
                Image.open(os.path.join(tex, "standard_alphan.tga.dds")) as b:
            self.assertEqual(a.convert("RGB").getpixel((8, 8)), b.convert("RGB").getpixel((8, 8)))   # untouched
        # Back to the original: beta's banner as the clone made it (alpha's picture)
        mod = ModData(self.root)
        orig = FA.original_picture(mod, own["rel"])
        self.assertEqual(os.path.normcase(orig), os.path.normcase(os.path.join(tex, "standard_alphan.tga.dds")))
        self.assertIsNone(FA.original_picture(mod, "models/textures/standard_slave.tga.dds"))
        plan = edit(mod, "test", "beta", {"art": {own["rel"]: {"src": orig, "exact": True}}})
        plan.apply()
        with open(orig, "rb") as a, open(os.path.join(tex, "standard_beta.tga.dds"), "rb") as b:
            self.assertEqual(a.read(), b.read())
        for b in backups(ModData(self.root)):                  # newest first
            restore(ModData(self.root), b)
        after = tree_hash(self.root)
        self.assertEqual({k: v for k, v in after.items() if "_backups" not in k and k != "flag.png"},
                         before)

    def test_copy_unit_and_building(self):
        from campaign_editor import editors as E
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"),
              "building barracks\n{\n    levels hut house\n    {\n        hut requires factions { alpha, }\n"
              "        {\n            capability\n            {\n                recruit \"alpha general\"  0\n"
              "            }\n            upgrades\n            {\n                house\n            }\n        }\n"
              "        house requires factions { alpha, }\n        {\n        }\n    }\n}\n")
        write(os.path.join(d, "text", "export_units.txt"), "{alpha_general}\tAlpha General\n"
              "{alpha_general_descr}\nA long\ntext\n{alpha_general_descr_short}\tShort\n", utf16=True)
        write(os.path.join(d, "text", "export_buildings.txt"), "{hut}\tHut\n{hut_desc}\tA hut\n{house}\tHouse\n",
              utf16=True)
        mod = ModData(self.root)
        plan = Plan(mod, "u", "u", {})
        E.copy_unit(plan, "alpha general", "alpha guard", "alpha_guard")
        with self.assertRaises(ValueError):
            E.copy_unit(plan, "alpha general", "rebel spear", "x")               # the type is taken
        E.copy_building(plan, "barracks", "camp", {"hut": "tent", "house": "hall"})
        plan.apply()
        m2 = ModData(self.root)
        from campaign_editor.units import read_units
        u = {x.type: x for x in read_units(m2.load(m2.file("edu")))}
        self.assertEqual(u["alpha guard"].dictionary, "alpha_guard")
        self.assertEqual(u["alpha guard"].ownership, ["alpha"])
        edb = open(m2.file("edb")).read()
        self.assertIn('recruit "alpha guard"  0', edb)
        self.assertIn("building camp", edb)
        self.assertIn("levels tent hall", edb)
        self.assertIn("tent requires factions { alpha, }", edb)
        self.assertIn("                hall\n", edb)                       # upgrades follow the new names
        units_text = open(os.path.join(d, "text", "export_units.txt"), "rb").read().decode("utf-16").replace("\r", "")
        self.assertIn("{alpha_guard_descr}\nA long\ntext\n", units_text)
        self.assertIn("{alpha_guard}\tAlpha General", units_text)
        bt = open(os.path.join(d, "text", "export_buildings.txt"), "rb").read().decode("utf-16").replace("\r", "")
        self.assertIn("{tent_desc}\tA hut", bt)
        self.assertIn("{hall}\tHouse", bt)

    def test_new_unit_and_building_step_by_step(self):
        """What the step-by-step windows give copy_unit / copy_building: texts players read, owners, values,
        a picture of one's own; factions and texts per level; Restore gives every file back."""
        from campaign_editor import editors as E
        from campaign_editor.plan import Plan, restore
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"),
              "building barracks\n{\n    levels hut\n    {\n        hut requires factions { alpha, }\n"
              "        {\n            capability\n            {\n                recruit \"alpha general\"  0\n"
              "            }\n        }\n    }\n}\n")
        write(os.path.join(d, "text", "export_units.txt"), "{alpha_general}\tAlpha General\n", utf16=True)
        write(os.path.join(d, "text", "export_buildings.txt"), "{hut}\tHut\n", utf16=True)
        mod = ModData(self.root)
        before = {p: open(p, "rb").read() for p in (mod.file("edu"), mod.file("edb"),
                  mod.text_file("export_units.txt"), mod.text_file("export_buildings.txt"))}
        plan = Plan(mod, "u", "u", {})
        E.copy_unit(plan, "alpha general", "alpha guard", "alpha_guard", True,
                    texts={"name": "Alpha Guard", "descr": "Two\nlines", "descr_short": "Short one"},
                    owners=["alpha", "beta"], values={"stat_cost": "1, 999, 99, 10, 20, 999"})
        E.copy_building(plan, "barracks", "camp", {"hut": "tent"},
                        texts={"tent": {"name": "Tent", "desc": "A tent"}}, factions=["beta"])
        bdir = plan.apply()
        m2 = ModData(self.root)
        from campaign_editor.units import read_units
        u = {x.type: x for x in read_units(m2.load(m2.file("edu")))}
        self.assertEqual(u["alpha guard"].ownership, ["alpha", "beta"])
        self.assertTrue(any("no 'stat_cost' line" in w for _, w in plan.warnings))   # the mini-mod's units have none
        ut = open(m2.text_file("export_units.txt"), "rb").read().decode("utf-16").replace("\r", "")
        self.assertIn("{alpha_guard}\tAlpha Guard", ut)
        self.assertIn("{alpha_guard_descr}\tTwo\nlines\n", ut)           # over two lines, as the tables do
        self.assertIn("{alpha_guard_descr_short}\tShort one", ut)
        self.assertIn("{alpha_general}\tAlpha General", ut)                 # the source keeps its own
        edb = open(m2.file("edb")).read()
        self.assertIn("tent requires factions { beta, }", edb)
        self.assertIn("hut requires factions { alpha, }", edb)
        bt = open(m2.text_file("export_buildings.txt"), "rb").read().decode("utf-16").replace("\r", "")
        self.assertIn("{tent}\tTent", bt)
        self.assertIn("{tent_desc}\tA tent", bt)
        restore(m2, bdir)
        for p, data in before.items():
            self.assertEqual(open(p, "rb").read(), data)

    def test_logs_zip(self):
        import zipfile
        from campaign_editor import log
        game = os.path.join(self.root, "game")
        os.makedirs(os.path.join(game, "reports"))
        with open(os.path.join(game, "system.log.txt"), "w") as fh:
            fh.write("log")
        for n, t in (("report-Some Nick-7-26_09_27.txt", 2000000000), ("report-x-1-26_09_01.txt", 1000000000)):
            with open(os.path.join(game, "reports", n), "w") as fh:
                fh.write("r")
            os.utime(os.path.join(game, "reports", n), (t, t))
        out = os.path.join(self.root, "logs.zip")
        log.pack(out, game)
        names = zipfile.ZipFile(out).namelist()
        self.assertIn("system.log.txt", names)
        self.assertIn("reports/report-7-26_09_27.txt", names)        # the newest, without the nick
        self.assertEqual(len([n for n in names if n.startswith("reports/")]), 1)

    def test_game_log_in_plain_words(self):
        """The game's system.log.txt read: a Script Error's reason (the lines after it), errors of one kind grouped
        whatever unit / faction they name, a crash first, the mod's line shown, plain words for known messages."""
        from campaign_editor import gamelog
        game = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, game)
        write(os.path.join(game, "data", "export_descr_buildings.txt"),
              "".join("line %d\n" % i for i in range(1, 30)))
        log_text = ("10:00:00.001 [script.err] [error] Script Error in data/export_descr_buildings.txt, at line 12, "
                    "column 4\nunit(cog) does not match up to the ownership for faction(normans)\n"
                    "10:00:00.002 [script.err] [error] Script Error in data/export_descr_buildings.txt, at line 13, "
                    "column 4\nunit(dhow) does not match up to the ownership for faction(aztecs)\n"
                    "10:00:01.000 [system.io] [warning] open: models_strat/navy_cog.rum is missing\n"
                    "10:00:02.000 [core.assert] [fatal] ASSERT FAILED: src\\game_rtw\\culture_db.cpp(882): "
                    "year_founded_signed <= world.calender.year_get()\n")
        path = os.path.join(game, "system.log.txt")
        write(path, log_text)
        entries = gamelog.parse(log_text)
        self.assertEqual(entries[0]["file"], "data/export_descr_buildings.txt")
        self.assertEqual(entries[0]["line"], 12)
        self.assertIn("unit(cog)", entries[0]["why"])
        groups = gamelog.summary(entries)
        self.assertEqual(groups[0][0]["level"], "fatal")                       # the crash first
        self.assertEqual(groups[1][1], 2)                                       # the two recruit errors as one
        text = gamelog.report(path, game)
        self.assertIn("CRASH", text)
        self.assertIn("year_founded", text)
        self.assertIn("the line now reads: line 12", text)
        self.assertIn("ownership", gamelog.explain("unit(cog) does not match up to the ownership for faction(x)"))
        # REX's own complaint about its start (a tester saw it in the log copy and blamed the editor)
        self.assertIn("does not start the game", gamelog.explain(
            "ERROR: src\\game\\romans_game.cpp(1764) Game selection invalid - is the path '\uad4c\ub2f7' ok?"))

    def test_report_finds_the_game_logs(self):
        """The game writes system.log.txt where the mod was started from: the report finds the mod's own first, then
        the newest elsewhere in the game folder (a Rome mod folder, Medieval II's mods/<mod>/logs), at most 3."""
        from campaign_editor import report
        game = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, game)
        old = os.path.join(game, "logs", "system.log.txt")
        hlr = os.path.join(game, "HLR", "logs", "system.log.txt")
        mine = os.path.join(game, "mods", "mine", "logs", "system.log.txt")
        for i, p in enumerate((old, hlr, mine)):
            write(p, "log %d" % i)
            os.utime(p, (1000 + i, 1000 + i))
        os.utime(hlr, (5000, 5000))                                    # the newest of the others
        got = report.game_logs(game, os.path.join(game, "mods", "mine"))
        self.assertEqual(got, [mine, hlr, old])
        self.assertEqual(report.game_logs(game), [hlr, mine, old])                # no mod: newest first
        self.assertIn("[log]", report.LOG_HOWTO)

    def test_report_is_anonymous_and_sent(self):
        import base64
        import http.server
        import io
        import json
        import threading
        import zipfile
        from campaign_editor import report, settings
        # the person's names go: user folders in paths, e-mails, Steam IDs, SIDs, IPs, the given words
        text = ("C:\\Users\\Adam Smith\\Desktop\\x.txt /home/adam/rtw D:/Documents and Settings/adam/y "
                "mail adam@example.com id 76561198012345678 S-1-5-21-1-2-3-1001 at 192.168.1.20 v0.19.2 "
                "Pfadfinder said hi; pfadfinder2 stays; user stays")
        out = report.scrub(text, ["Pfadfinder", "user", "ab"])
        for gone in ("Adam", "adam", "example.com", "7656119801", "S-1-5-21", "192.168", "Pfadfinder said"):
            self.assertNotIn(gone, out)
        for kept in ("Desktop\\x.txt", "/rtw", "v0.19.2", "pfadfinder2 stays", "user stays"):
            self.assertIn(kept, out)
        # the logs found: the newest REX crash report without the player's name - inside it as well
        game = os.path.join(self.root, "game")
        os.makedirs(os.path.join(game, "reports"))
        with open(os.path.join(game, "system.log.txt"), "w") as fh:
            fh.write("start\nC:\\Users\\Bob\\game\n" + "x" * 50 + "\n")
        with open(os.path.join(game, "reports", "report-Some Nick-7-26_09_27.txt"), "w") as fh:
            fh.write("crash of Some Nick")
        files = report.found(game)
        names = [n for _, n, _ in files]
        self.assertIn("system.log.txt", names)
        self.assertIn("reports/report-7-26_09_27.txt", names)
        texts = dict(report.contents(files, report.hidden_words(files)))
        self.assertNotIn("Some Nick", texts["reports/report-7-26_09_27.txt"])
        self.assertNotIn("Bob", texts["system.log.txt"])
        # a big log: only its newest part
        self.assertIn("left out", report._read_tail(os.path.join(game, "system.log.txt"), cap=20))
        # ... and its start (the game reading the mod's files: load errors are there) and the errors of the middle,
        # each once with how many times - a test mod's report came with only the last turns' AI chatter
        big = os.path.join(game, "big.log")
        with open(big, "w") as fh:
            fh.write("10:00:00.000 [data.invalid] [error] descr_strat.txt line 3031: unknown faction\n")
            for k in range(3000):
                fh.write("10:00:01.%03d [ai.agents] [info] thinking %d\n" % (k % 1000, k))
                if k % 500 == 0:
                    fh.write("10:00:02.%03d [core.assert] [fatal] ERROR: settlement.cpp(4326)\n" % (k % 1000))
                if k == 1700:          # the game's words come on the next line - kept with the error
                    fh.write("10:00:03.000 [script.err] [error] Script Error in descr_strat.txt, at line 3071\n"
                             "Population of 2600 is too high for a village - max is 1500\n")
            fh.write("10:00:09.000 [game] [info] the newest line\n")
        got = report._read_tail(big, cap=30000)
        self.assertIn("unknown faction", got)                          # the start
        self.assertRegex(got, r"settlement\.cpp\(4326\)  \(x5\)")       # the middle's errors, once, counted
        self.assertIn("at line 3071  |  Population of 2600 is too high for a village", got)
        self.assertIn("the newest line", got)                          # the end
        self.assertLess(len(got), 40000)
        data = report.build_zip(list(texts.items()), "it crashed at C:\\Users\\Bob\\x", "disc#1",
                                {"editor": "0.19.2"}, words=["Bob"])
        z = zipfile.ZipFile(io.BytesIO(data))
        head = z.read("report.txt").decode()
        self.assertIn("it crashed", head)
        self.assertNotIn("Bob", head)
        self.assertIn("disc#1", head)
        # sent to a relay: its answer is the report's number; a refusal comes back in plain words
        got = {}

        class Relay(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                got.update(body, agent=self.headers["User-Agent"])
                ok = body["zip"].startswith("UEsDB")
                self.send_response(200 if ok else 400)
                self.end_headers()
                self.wfile.write(json.dumps({"id": "R-1"} if ok else {"error": "broken"}).encode())

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), Relay)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            settings.put("report_url", "http://127.0.0.1:%d/" % srv.server_port)
            self.assertEqual(report.send(data, "it crashed", "disc#1", {"editor": "0.19.2"}), "R-1")
            self.assertEqual(base64.b64decode(got["zip"]), data)
            self.assertTrue(got["agent"].startswith("RTW-M2TW-Campaign-Editor/"))
            with self.assertRaises(RuntimeError) as e:
                report.send(b"not a zip")
            self.assertIn("broken", str(e.exception))
            with self.assertRaises(RuntimeError):
                report.send(b"x" * (report.ZIP_CAP + 1))
            settings.put("report_url", "")
            if not report.REPORT_URL:
                with self.assertRaises(RuntimeError) as e:
                    report.send(data)
                self.assertIn("not set up", str(e.exception))
        finally:
            settings.put("report_url", "")
            srv.shutdown()
            srv.server_close()

    def test_a_deleted_tcl_command_name_never_comes_back(self):
        """A call the window scheduled ('after') on a part that is closed before it runs must not run another
        function that got the same Tcl name (Python reuses addresses): "<lambda>() missing 1 required positional
        argument: 'e'" in the click test. With a running number in every name, buttons, bindings, scheduled calls and
        clean-up work as before and a stale call finds nothing."""
        try:
            import tkinter as tk
            root = tk.Tk()
        except Exception as e:                        # no tkinter / no display (CI): the window is not tested here
            self.skipTest("no window: %s" % e)
        from campaign_editor.gui_util import unique_tcl_names
        unique_tcl_names()
        try:
            hits, names = [], set()
            for _ in range(200):                      # many short-lived parts, each with a callback
                w = tk.Label(root)
                w.bind("<Configure>", lambda e: hits.append("wrong"))
                w.after(10, lambda: hits.append("stale"))
                names.update(w._tclCommands or [])
                w.destroy()
            self.assertEqual(len(names), 400)         # no name given twice
            b = tk.Button(root, command=lambda: hits.append("button"))
            b.invoke()
            root.after(60, root.quit)
            root.mainloop()
            self.assertEqual(hits, ["button"])        # the stale calls ran nothing, nothing ran in their place
            self.assertFalse(set(root.tk.call("info", "commands", "ce*")) & names)
        finally:
            root.destroy()

    def test_no_internet_or_a_silent_service_never_hangs(self):
        """No internet, or a report service that takes the call and never answers: the editor gives up after its
        time and says it in plain words (the window runs these in a thread, so it never freezes)."""
        import socket
        from campaign_editor import report, settings
        saved = (settings._data, settings._path)
        tmp = tempfile.mkdtemp()
        settings._data, settings._path = {}, (lambda: os.path.join(tmp, "s.json"))
        silent = socket.socket()
        silent.bind(("127.0.0.1", 0))
        silent.listen(5)                                      # takes the call, never answers
        closed = socket.socket()
        closed.bind(("127.0.0.1", 0))
        port_closed = closed.getsockname()[1]
        closed.close()                                        # nobody there: like no internet
        try:
            settings.put("report_url", "http://127.0.0.1:%d/" % silent.getsockname()[1])
            t = time.time()
            with self.assertRaises(RuntimeError) as e:
                report.answers([{"id": "R-1", "issue": 1}], timeout=1)
            self.assertLess(time.time() - t, 10)
            self.assertIn("could not reach the report service", str(e.exception))
            settings.put("report_url", "http://127.0.0.1:%d/" % port_closed)
            with self.assertRaises(RuntimeError) as e:
                report.send_reply("R-1", 1, "hello", timeout=1)
            self.assertIn("is the internet on?", str(e.exception))
        finally:
            silent.close()
            settings._data, settings._path = saved

    def test_answers_to_my_reports(self):
        """The reporter cannot see the private reports repo: the editor keeps the numbers it sent (and finds older
        ones in its log), asks the relay for the author's answers, marks what is new until read, and sends the
        reporter's answer (with a zip of new pictures) to the same report."""
        import base64
        import http.server
        import json
        import threading
        from campaign_editor import report, settings
        saved = (settings._data, settings._path)
        tmp = tempfile.mkdtemp()
        settings._data, settings._path = {}, (lambda: os.path.join(tmp, "s.json"))
        calls = []

        class Relay(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                calls.append((self.path, body))
                if self.path == "/answers":
                    out = {"answers": {"R-20261003-ABCDEF": {"issue": 7, "state": "open", "reason": "",
                                                             "messages": [{"from": "author", "text": "Which picture?",
                                                                           "at": "2026-10-03T10:00:00Z"}]}}}
                elif self.path == "/reply":
                    out = {"ok": True}
                else:
                    out = {"id": "R-20261003-ABCDEF", "issue": 7}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(out).encode())

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), Relay)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            settings.put("report_url", "http://127.0.0.1:%d/" % srv.server_port)
            zipdata = report.build_zip([], "x")
            rid, issue = report.send(zipdata, "Bug: x", "", {"editor": "t"}, full=True)
            self.assertEqual((rid, issue), ("R-20261003-ABCDEF", 7))
            report.remember_sent(rid, issue, "bug", "Bug: x")
            # an older report only in the log is found too; the same number is not doubled
            rows = report.sent_reports(["12:00 Report sent: R-20261001-0A1B2C (40 KB)",
                                        "Report sent: R-20261003-ABCDEF (1 KB)"])
            self.assertEqual([r["id"] for r in rows], ["R-20261003-ABCDEF", "R-20261001-0A1B2C"])
            self.assertEqual(rows[0]["issue"], 7)
            got = report.answers(rows, "t")
            self.assertEqual(calls[-1][0], "/answers")
            self.assertEqual(calls[-1][1]["reports"][0], {"id": rid, "issue": 7})
            self.assertEqual(got[rid]["messages"][0]["text"], "Which picture?")
            # new until it was shown; a later answer or a closing is new again
            self.assertEqual(report.news(got, settings.get("reports_seen")), [rid])
            report.mark_seen(got, [rid])
            self.assertEqual(report.news(got, settings.get("reports_seen")), [])
            got[rid]["state"], got[rid]["reason"] = "closed", "completed"
            self.assertEqual(report.news(got, settings.get("reports_seen")), [rid])
            self.assertEqual(report.state_words(got[rid]), "closed - fixed / done")
            self.assertEqual(report.state_words(None), "no answer yet")
            # the reporter's answer goes to the same report, with its files
            report.send_reply(rid, 7, "the unit cards of England", zipdata, "t")
            path, body = calls[-1]
            self.assertEqual((path, body["id"], body["issue"]), ("/reply", rid, 7))
            self.assertEqual(base64.b64decode(body["zip"]), zipdata)
        finally:
            srv.shutdown()
            srv.server_close()
            settings._data, settings._path = saved
            shutil.rmtree(tmp, ignore_errors=True)

    # ---- 0.5.0: roster, lines added / removed, renames, mod list, file origins ----
    RICH_EDB = """building barracks
{
    levels muster big_barracks
    {
        muster requires factions { barbarian, }
        {
            capability
            {
                recruit "rebel spear"  0  requires factions { slave, }
            }
            construction  1
            cost  100
            settlement_min town
            upgrades
            {
                big_barracks
            }
        }
        big_barracks requires factions { barbarian, }
        {
            capability
            {
                recruit "rebel spear"  1  requires factions { slave, }
            }
            construction  2
            cost  200
            settlement_min town
        }
    }
}
building shrine
{
    levels altar
    {
        altar requires factions { alpha, } and building_present_min_level barracks muster
        {
            capability
            {
                happiness_bonus bonus 1
            }
            construction  1
            cost  50
            settlement_min town
        }
    }
}
"""

    def _rich(self):
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"), self.RICH_EDB)
        write(os.path.join(d, "ui", "units", "slave", "#rebel_spear.tga"), "spear card")
        write(os.path.join(d, "ui", "unit_info", "slave", "rebel_spear_info.tga"), "spear info")
        return ModData(self.root)

    def test_roster_give_and_take_keep_every_place_in_step(self):
        from campaign_editor import roster as R
        from campaign_editor.edit import edit
        mod = self._rich()
        before = tree_hash(self.root)
        r = R.roster(mod, "alpha")
        self.assertEqual({u["type"]: u["has"] for u in r["units"]}, {"alpha general": "own", "rebel spear": None})
        self.assertEqual({(b["chain"], b["level"]): b["has"] for b in r["buildings"]},
                         {("barracks", "muster"): None, ("barracks", "big_barracks"): None, ("shrine", "altar"): "own"})
        plan = edit(mod, "test", "alpha", {"roster": {"unit:rebel spear": True, "building:barracks:muster": True,
                                                      "unit:alpha general": False}})
        edu = plan.files[mod.file("edu")].dump().decode("latin-1")
        edb = plan.files[mod.file("edb")].dump().decode("latin-1")
        self.assertIn("ownership\tslave, alpha", edu)                     # given: owned...
        self.assertEqual(edb.count('recruit "rebel spear"  0  requires factions { slave, alpha, }'), 1)  # ...recruited
        self.assertIn("muster requires factions { barbarian, alpha, }", edb)    # ...and the level it needs
        self.assertIn("big_barracks requires factions { barbarian, }", edb)
        self.assertIn("ownership\tslave", edu.split("type\t\trebel spear")[0])  # taken: never an empty line
        self.assertTrue(any("start with alpha general" in m for _, m in plan.warnings), plan.report())
        self.assertTrue(any("big_barracks" not in m for _, m in plan.notes))
        plan.apply()
        ui = os.path.join(mod.data, "ui")
        self.assertEqual(open(os.path.join(ui, "units", "alpha", "#rebel_spear.tga")).read().strip(), "spear card")
        self.assertTrue(os.path.exists(os.path.join(ui, "unit_info", "alpha", "rebel_spear_info.tga")))
        restore(mod, backups(mod)[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    POOL_EDB = """building barracks
{
    levels muster
    {
        muster city requires factions { barbarian, alpha, }
        {
            capability
            {
                recruit_pool "rebel spear"  1   0.5   4  0  requires factions { slave, }
                retrain_pool "alpha general"  0   0.2   1  0  requires factions { alpha, }
            }
            construction  1
            cost  100
            settlement_min town
        }
    }
}
"""

    def test_medieval2_recruit_pool_and_rex_retrain_lines(self):
        # Medieval II recruits with recruit_pool lines (vanilla has no 'recruit' at all); REX adds retrain-only lines
        from campaign_editor import editors as E
        from campaign_editor import roster as R
        from campaign_editor import packs
        from campaign_editor.edit import edit
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"), self.POOL_EDB)
        mod = ModData(self.root)
        f = mod.load(mod.file("edb"))
        self.assertEqual(R.recruit_dialect(f), "pool")
        self.assertEqual([(u, c, l) for _, u, c, l in R.recruit_lines(f)], [("rebel spear", "barracks", "muster")])
        self.assertEqual(len(R.recruit_lines(f, R.RECRUIT_KEYS)), 2)          # retrain_pool too, when asked
        units = {u["type"]: u for u in R.roster(mod, "slave")["units"]}
        self.assertEqual(units["rebel spear"]["recruit"], [("barracks", "muster")])
        # giving writes the faction into the recruit_pool line
        plan = edit(mod, "test", "alpha", {"roster": {"unit:rebel spear": True}})
        edb = plan.files[mod.file("edb")].dump().decode("latin-1")
        self.assertIn('recruit_pool "rebel spear"  1   0.5   4  0  requires factions { slave, alpha, }', edb)
        # a rename follows recruit_pool and retrain_pool lines
        plan = Plan(mod, None, "rename")
        E.rename_unit(plan, "alpha general", "alpha lord")
        edb = plan.files[mod.file("edb")].dump().decode("latin-1")
        self.assertIn('retrain_pool "alpha lord"', edb)
        self.assertNotIn('"alpha general"', edb)
        # a unit pack carries its recruit_pool place
        self.assertEqual([r["line"].split()[0] for r in packs._recruit_places(mod, ["rebel spear"])], ["recruit_pool"])
        # the line checks know every form; the Add line text is written in the file's own form
        self.assertEqual([m for e, m in E.check_text(mod, "building", E.recruit_text(
            "pool", "rebel spear", "0", factions=["slave"])) if e], [])
        self.assertTrue(E.recruit_text("pool", "rebel spear", "1", retrain=True).startswith('retrain_pool "rebel spear"'))
        self.assertTrue(E.recruit_text("plain", "rebel spear", "1").startswith('recruit "rebel spear"  1'))
        self.assertTrue(any(e for e, _ in E.check_text(mod, "building", 'recruit_pool "rebel spear"  0')))
        self.assertTrue(any(e for e, _ in E.check_text(mod, "building", 'recruit "rebel spear"  x')))

    BRACKET_EDB = """building sea_trade
{
    levels merchants_wharf
    {
        merchants_wharf city requires ( ( factions { alpha, barbarian, } and building_present_min_level port port ) or ( factions { eastern, } and building_present_min_level market corn_exchange ) )
        {
            capability
            {
                trade_fleet 2
                recruit_pool "rebel spear"  1   0.5   4  0  requires ( ( factions { slave, } and building_present_min_level port port ) or ( factions { alpha, } ) )
            }
            construction  3
            cost  1600
            settlement_min city
        }
    }
}
"""

    def test_rex_bracket_requirements_read_every_faction_group(self):
        # REX: one line, several 'factions { }' groups, each with conditions of its own
        from campaign_editor import roster as R
        from campaign_editor.buildings import read_buildings
        from campaign_editor.edit import edit
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"), self.BRACKET_EDB)
        mod = ModData(self.root)
        f = mod.load(mod.file("edb"))
        head = next(l for l in f.texts() if "merchants_wharf city" in l)
        self.assertEqual(R.factions_groups(head), [["alpha", "barbarian"], ["eastern"]])
        self.assertEqual(R.factions_in(head), ["alpha", "barbarian", "eastern"])
        lv = read_buildings(f)[0].levels[0]
        self.assertEqual(lv.factions(), ["alpha", "barbarian", "eastern"])      # alpha's culture 'eastern' counts
        units = {u["type"]: u for u in R.roster(mod, "alpha")["units"]}
        self.assertEqual(units["rebel spear"]["recruit"], [("sea_trade", "merchants_wharf")])  # the 2nd group
        # taking the unit from alpha leaves slave's group and its conditions alone
        plan = Plan(mod, None, "roster")
        R.take_unit(plan, "slave", "rebel spear")
        edb = plan.files[mod.file("edb")].dump().decode("latin-1")
        self.assertIn('factions { slave, } and building_present_min_level port port', edb)  # slave's group alone...
        self.assertTrue(any("rewrite that line" in m for _, m in plan.warnings), plan.report())  # ...left to a person
        plan = edit(mod, "test", "alpha", {"roster": {"unit:rebel spear": False}})
        edb = plan.files[mod.file("edb")].dump().decode("latin-1")
        self.assertIn("( factions { alpha, } )", edb)                  # alpha's own group: left, said so
        self.assertTrue(any("rewrite that line" in m for _, m in plan.warnings), plan.report())
        # a faction named in two groups goes out of both; one alone in a group is left for a person
        line = "requires ( ( factions { a, b, } and x ) or ( factions { b, c, } and y ) )"
        self.assertEqual(R.drop_faction(line, "b"),
                         "requires ( ( factions { a, } and x ) or ( factions { c, } and y ) )")
        self.assertIsNone(R.drop_faction(line.replace("{ b, c, }", "{ b, }"), "b"))
        self.assertEqual(R.add_faction(line, "d"),
                         "requires ( ( factions { a, b, d, } and x ) or ( factions { b, c, } and y ) )")

    def test_editor_lines_no_cap_of_our_own(self):
        """A key the mod repeats takes any number of lines (no "not more than the mod has"); a one-line key stays
        one line; an unknown key is refused; officers stop at 3 only on the original exe (REX / M2EX lift it)."""
        from campaign_editor import editors as E
        game, hlr = self._game()
        mod = ModData(hlr)
        f = mod.load(mod.file("edu"))
        blk = E.unit_blocks(f)[0]
        limits = {None: {"officer": 2, "category": 1}}
        self.assertIsNone(E.room_for(f, "unit", blk, None, None, "officer", limits, 2, mod=mod))    # a 3rd: fine
        self.assertIsNone(E.room_for(f, "unit", blk, None, None, "officer", limits, 3, mod=mod))    # REX: a 4th too
        os.remove(os.path.join(game, "REX.exe"))
        mod = ModData(hlr)
        self.assertIn("at most 3", E.room_for(f, "unit", blk, None, None, "officer", limits, 3, mod=mod))
        self.assertIn("one line only", E.room_for(f, "unit", blk, None, None, "category", {None: {"category": 1}},
                                                  1, mod=mod))
        self.assertIn("not a key", E.room_for(f, "unit", blk, None, None, "no_such_key", limits, mod=mod))

    def test_engine_known_unit_keys_and_rex_attributes(self):
        # a key the engine knows may be added although no unit of the mod has one; REX words toggle on their line
        from campaign_editor import editors as E
        from campaign_editor import unitattrs as A
        mod = ModData(self.root)
        f = mod.load(mod.file("edu"))
        blk = E.unit_blocks(f)[0]
        limits = E.line_limits(f, "unit")
        self.assertIn("recruit_priority_offset", E.keys_seen(f, "unit"))
        self.assertIsNone(E.room_for(f, "unit", blk, None, None, "recruit_priority_offset", limits))
        self.assertTrue(E.room_for(f, "unit", blk, None, None, "recruit_priority_offset", limits, 1))  # one only
        self.assertEqual(A.toggled("attributes", "sea_faring, hardy", "ai_cannot_skirmish", True),
                         "sea_faring, hardy, ai_cannot_skirmish")
        self.assertEqual(A.toggled("stat_pri_attr", "no", "sp", True), "sp")
        self.assertEqual(A.toggled("stat_pri_attr", "sp", "sp", False), "no")
        self.assertEqual(A.toggled("stat_mental", "5, normal, untrained, steadfast", "steadfast", False),
                         "5, normal, untrained")
        self.assertIn("immune_to_psychology", [w for w, _ in A.for_line("stat_mental")])

    def test_forts_are_read_and_nobody_starts_on_them(self):
        # REX / M2TW fort lines: kept out of the character before them, their tiles taken
        from campaign_editor.strat import Strat
        d = os.path.join(self.root, "data", "world", "maps", "campaign", "test")
        p = os.path.join(d, "descr_strat.txt")
        text = open(p, encoding="latin-1").read().replace(
            "unit\t\talpha general\t\texp 1 armour 0 weapon_lvl 0\n",
            "unit\t\talpha general\t\texp 1 armour 0 weapon_lvl 0\n"
            "fort 3 1 cerin_fort culture eastern permanent name Cerin Amroth\n", 1)
        write(p, text)
        mod = ModData(self.root)
        s = Strat(mod.load(p))
        self.assertEqual([(f.xy, f.owner, f.permanent, f.name) for f in s.forts],
                         [((3, 1), "alpha", True, "Cerin Amroth")])
        aaron = s.faction("alpha").characters[0]
        self.assertFalse(any(l.startswith("fort") for l in s.lines[aaron.start:aaron.end]))  # not the leader's line
        self.assertIn((3, 1), s.taken_tiles())
        self.assertIn("fort stands there", mod.tile_problem("test", (3, 1), "named character", True) or "")

    def test_rebels_are_edited_like_a_faction(self):
        # the rebels (slave) in Edit faction: a new rebel army and a captain for an empty rebel town
        # carry a sub_faction, and their names come from that faction's list (as every vanilla rebel)
        from campaign_editor.edit import edit
        from campaign_editor.strat import Strat
        mod = ModData(self.root)
        p = mod.campaign_file("test", "descr_strat.txt")
        s0 = Strat(mod.load(p))
        self.assertEqual(s0.faction("slave").characters[0].sub_faction, "alpha")
        plan = edit(mod, "test", "slave", {
            "characters": [{"kind": "army", "name": "Boris", "age": 30, "units": ["rebel spear"], "xy": (2, 3)}]})
        text = plan.files[p].dump().decode("latin-1")
        self.assertIn("character\tsub_faction alpha, Boris, general, age 30, , x 2, y 3", text)
        with self.assertRaises(ValueError):              # a name outside alpha's list is refused
            edit(mod, "test", "slave", {"characters": [{"kind": "army", "name": "Rebel", "units": ["rebel spear"],
                                                        "xy": (2, 3)}]})
        with self.assertRaises(ValueError):              # the rebels are never playable
            edit(mod, "test", "slave", {"playable": True})

    def test_clone_leaves_the_templates_shadow_and_spawn_ties(self):
        # BI: 'faction empire_east, shadowed_by empire_east_rebels' - a clone must not claim the same shadow
        sm = os.path.join(self.root, "data", "descr_sm_factions.txt")
        write(sm, SM.replace("faction\t\talpha\n", "faction\t\talpha, shadowed_by slave\n", 1))
        mod = ModData(self.root)
        plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"],
                                                              "leader": {"name": "Boris Alphid", "age": 35}}})
        text = plan.files[sm].dump().decode("latin-1").replace("\r", "")
        self.assertIn("faction\t\tbeta\n", text)
        self.assertIn("faction\t\talpha, shadowed_by slave\n", text)
        self.assertTrue(any("shadowed_by slave" in m for _, m in plan.notes), plan.report())

    def test_medieval2_new_religion_everywhere(self):
        # a new religion (Medieval II): list + block, lookup, text, symbol, every region's line, map.rwm
        from campaign_editor import religions as RL
        from campaign_editor.regionedit import apply_opts
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "descr_religions.txt"), "religions\n{\n\tcatholic\n\tislam\n}\n\n"
              "religion catholic\n{\n\tpip_path\tui/pips/pip_catholic.tga\n}\n\n"
              "religion islam\n{\n\tpip_path\tui/pips/pip_islam.tga\n}\n")
        write(os.path.join(d, "descr_religions_lookup.txt"), "catholic\nislam\n")
        write(os.path.join(d, "text", "religions.txt"), "\u00ac\n{catholic}Catholic\n{islam}Islam\n", utf16=True)
        write(os.path.join(d, "ui", "pips", "pip_islam.tga"), "pip picture")
        rp = os.path.join(d, "world", "maps", "campaign", "test", "descr_regions.txt")
        write(rp, REGIONS.replace("\t1\nB_R", "\t1\n\treligions { catholic 100 islam 0 }\nB_R").rstrip("\n")
              + "\n\treligions { catholic 0 islam 100 }\n")
        before = tree_hash(self.root)
        mod = ModData(self.root)
        self.assertEqual(RL.names(mod), ["catholic", "islam"])
        spec = {"name": "judaism", "shown": "Judaism", "pip_from": "islam", "picture": None, "factions": ["alpha"]}
        self.assertEqual(RL.problems(mod, spec), [])
        self.assertTrue(RL.problems(mod, dict(spec, name="catholic")))          # taken
        self.assertTrue(RL.problems(mod, dict(spec, shown="")))                 # no text = silent crash
        plan = Plan(mod, None, "religion")
        apply_opts(plan, "test", {"new_religions": [spec],
                                  "religions": {"B_R": {"catholic": 0, "islam": 70, "judaism": 30}}})
        plan.apply()
        mod = ModData(self.root)
        self.assertEqual(RL.names(mod), ["catholic", "islam", "judaism"])
        self.assertEqual(RL.pip_of(mod, "judaism"), "ui/pips/pip_judaism.tga")
        self.assertEqual(open(os.path.join(d, "ui", "pips", "pip_judaism.tga")).read(), "pip picture")
        self.assertIn("judaism", open(os.path.join(d, "descr_religions_lookup.txt")).read())
        self.assertIn("{judaism}Judaism", open(os.path.join(d, "text", "religions.txt"), "rb").read().decode("utf-16"))
        regs = mod.regions("test")
        self.assertEqual(regs["A_R"]["religions"], {"catholic": 100, "islam": 0, "judaism": 0})
        self.assertEqual(regs["B_R"]["religions"], {"catholic": 0, "islam": 70, "judaism": 30})
        restore(mod, backups(mod)[0])
        after = {k: v for k, v in tree_hash(self.root).items() if not k.startswith(("faction_tool_backups", "CampaignEditor_backups"))}
        self.assertEqual(before, after)

    def test_give_unit_joins_one_recruit_line_per_level(self):
        """A level that recruits a unit by two lines for different factions (vanilla: Arab Cavalry for moors and
        for egypt, carthaginian peasant for spain and the carthaginian culture): giving the unit writes the
        faction into ONE of them - in both it was listed twice in the building's description (a tester)."""
        from campaign_editor import roster as R
        from campaign_editor.plan import Plan
        d = os.path.join(self.root, "data")
        write(os.path.join(d, "export_descr_buildings.txt"), self.POOL_EDB.replace(
            'recruit_pool "rebel spear"  1   0.5   4  0  requires factions { slave, }\n',
            'recruit_pool "rebel spear"  1   0.5   4  0  requires factions { slave, }\n'
            '                recruit_pool "rebel spear"  1   0.5   4  0  requires factions { beta, }\n'))
        mod = ModData(self.root)
        plan = Plan(mod, "x", "x")
        R.give_unit(plan, "alpha", "rebel spear")
        edb = plan.files[mod.file("edb")].dump().decode("latin-1")
        self.assertEqual(sum("rebel spear" in l and "alpha" in l for l in edb.splitlines()), 1, edb)
        self.assertIn('requires factions { slave, alpha, }', edb)
        self.assertIn('requires factions { beta, }', edb)
        # a faction one line already lets in is written nowhere
        plan = Plan(mod, "x", "x")
        R.give_unit(plan, "beta", "rebel spear")
        edb = plan.files[mod.file("edb")].dump().decode("latin-1")
        self.assertNotIn("slave, beta", edb)

    def test_roster_take_a_culture_writes_the_others_out(self):
        from campaign_editor import roster as R
        from campaign_editor.plan import Plan
        mod = self._rich()
        plan = Plan(mod, "x", "x")
        R.set_level(plan, "slave", "barracks", "muster", give=False)      # slave is barbarian: the culture goes
        R.set_level(plan, "alpha", "shrine", "altar", give=False)
        edb = plan.files[mod.file("edb")].texts()
        self.assertIn("        muster requires factions { }", edb)             # no other barbarian faction
        self.assertIn("        altar requires factions { } and building_present_min_level barracks muster", edb)
        self.assertTrue(plan.warnings)

    def test_lines_added_and_removed_in_their_place(self):
        from campaign_editor import editors as E
        from campaign_editor.plan import Plan
        mod = self._rich()
        plan = Plan(mod, "b", "b")
        edb = mod.file("edb")
        f = mod.load(edb)
        rm = next(i for i, l in enumerate(f.texts()) if "recruit" in l and " 1 " in l)
        E.restructure(plan, edb, "building", [
            {"block": "barracks", "place": "capability", "level": "muster", "text": 'recruit "alpha general"  0'},
            {"block": "barracks", "place": "upgrades", "level": "big_barracks", "text": "muster"},
            {"block": "shrine", "place": "level", "level": "altar", "text": "fake 1"}], [rm])
        g = plan.files[edb]
        t = g.texts()
        i = t.index('                recruit "alpha general"  0')
        self.assertEqual(t[i - 1].strip(), 'recruit "rebel spear"  0  requires factions { slave, }')
        self.assertFalse(any('"rebel spear"  1' in l for l in t))               # removed
        self.assertIn("            upgrades", t)
        self.assertEqual(t.count("            upgrades"), 2)                    # a block made for the new one
        blocks = E.building_blocks(g)
        tree = E.chain_tree(g, *next(b for b in blocks if b[0] == "barracks")[1:])
        self.assertEqual([lv["name"] for lv in tree["levels"]], ["muster", "big_barracks"])
        self.assertIsNotNone(tree["levels"][1]["upgrades"])
        self.assertEqual(t[t.index("            fake 1") + 1].strip(), "}")        # inside the level
        # checks: a recruit line naming no unit, an unknown level
        self.assertTrue(any(e for e, _ in E.check_text(mod, "building", 'recruit "no such unit"  0')))
        self.assertTrue(any(e for e, _ in E.check_text(mod, "building",
                                                        "x requires building_present_min_level barracks nope")))
        self.assertFalse(E.check_text(mod, "building", 'recruit "rebel spear"  0  requires factions { alpha, }'))
        self.assertEqual(E.required_keys(g, "building") >= {"construction", "cost", "settlement_min"}, True)

    def test_renamed_unit_and_chain_are_followed(self):
        from campaign_editor import editors as E
        from campaign_editor.plan import Plan
        mod = self._rich()
        plan = Plan(mod, "u", "u")
        E.rename_unit(plan, "rebel spear", "rebel pike")
        strat = plan.files[mod.campaign_file("test", "descr_strat.txt")].texts()
        self.assertIn("unit\t\trebel pike\t\texp 0 armour 0 weapon_lvl 0", strat)
        edb = "\n".join(plan.files[mod.file("edb")].texts())
        self.assertEqual(edb.count('"rebel pike"'), 2)
        self.assertNotIn('"rebel spear"', edb)
        plan = Plan(mod, "c", "c")
        E.rename_chain(plan, "barracks", "camp")
        self.assertIn("building_present_min_level camp muster", "\n".join(plan.files[mod.file("edb")].texts()))
        with self.assertRaises(ValueError):
            E.rename_unit(Plan(mod, "u", "u"), "rebel spear", "alpha general")

    def test_mod_list_of_a_game_folder(self):
        from campaign_editor.newmod import game_of, list_mods
        game = os.path.join(self.root, "game")
        for rel in ("data", "HLR/data", "bi/data", "mods/m2mod/data"):
            write(os.path.join(game, rel, "descr_sm_factions.txt"), "faction a\n")
        write(os.path.join(game, "RomeTW.exe"), "x")
        write(os.path.join(game, "notamod", "readme.txt"), "x")
        self.assertEqual([l for l, _ in list_mods(game)], ["(the game's own data)", "bi", "HLR", "mods/m2mod"])
        self.assertEqual(game_of(os.path.join(game, "HLR", "data")), game)
        self.assertEqual(game_of(os.path.join(game, "mods", "m2mod", "data")), game)

    def test_file_origins_from_manifests(self):
        from campaign_editor.scan import Origins
        p = os.path.join(self.root, "data", "x.txt")
        write(p, "same")
        md5 = hashlib.md5(open(p, "rb").read()).hexdigest()
        size = os.path.getsize(p)
        o = Origins({"data/x.txt": [size, md5], "data/y.txt": [5, "0"]}, {"data/z.txt": [size, md5]}, ["t"])
        self.assertEqual(o.classify("data/X.txt", p, size), "game")        # the game's paths ignore case
        self.assertEqual(o.classify("data/y.txt", p, size), "changed")
        self.assertEqual(o.classify("data/z.txt", p, size), "rex")
        self.assertEqual(o.classify("data/new.txt", p, size), "own")


class CoreLevelTest(unittest.TestCase):
    def test_castle_core_equals_settlement_level(self):
        """M2: 'The castle core building level should be EQUAL the settlement level!' - a castle
        village has motte_and_bailey; a town's core stays one below (the user's crash, 0.7.4)."""
        from campaign_editor.buildings import Building, Level, core_level_for, core_settlement
        castle, town = Building("core_castle_building"), Building("core_building")
        castle.levels = [Level(n, "") for n in ("motte_and_bailey", "wooden_castle", "castle", "fortress", "citadel")]
        town.levels = [Level(n, "") for n in ("wooden_pallisade", "wooden_wall", "stone_wall")]
        self.assertEqual(core_settlement(castle, "motte_and_bailey"), "village")
        self.assertEqual(core_settlement(castle, "castle"), "large_town")
        self.assertEqual(core_level_for(castle, "village").name, "motte_and_bailey")
        self.assertEqual(core_level_for(castle, "town").name, "wooden_castle")
        self.assertEqual(core_settlement(town, "wooden_pallisade"), "town")
        self.assertIsNone(core_level_for(town, "village"))
        self.assertEqual(core_level_for(town, "large_town").name, "wooden_wall")



class M2DiplomacyEndTest(unittest.TestCase):
    def test_last_faction_block_stops_before_faction_standings(self):
        """Medieval II's diplomacy starts with faction_standings (Rome's with core_attitudes): the slave block, the
        last one, must end before it - a rebel army written after it was never read (the user's M2TW, 2026-09-30)."""
        from campaign_editor.strat import Strat
        from campaign_editor.textio import TextFile
        text = ("campaign\timperial_campaign\r\n"
                "faction\tslave, comfortable caliph\r\n"
                "denari\t5000\r\n"
                "character\tsub_faction turks, Abi, general, male, age 30, x 1, y 2\r\n"
                "army\r\n"
                "unit\t\tSpear Militia\t\t\t\texp 0 armour 0 weapon_lvl 0\r\n"
                "\r\n"
                ";;;;;;;;\r\n"
                "; >>>> start of diplomacy section <<<<\r\n"
                "\r\n"
                "faction_standings\tengland,\t\t-1.0\tslave\r\n"
                "faction_relationships\tslave, at_war_with\tengland\r\n")
        s = Strat(TextFile.from_bytes("descr_strat.txt", text.encode("latin-1")))
        lines = s.lines
        self.assertEqual(lines[s.diplomacy_start].split()[0], "faction_standings")
        slave = s.factions[-1]
        self.assertEqual(slave.name, "slave")
        self.assertTrue(all(not lines[k].startswith("faction_standings") for k in range(slave.start, slave.end)))
        self.assertEqual(lines[slave.end - 1].split()[0], "unit")


class BIRegionsTest(unittest.TestCase):
    def test_bi_regions_legion_and_beliefs(self):
        """Barbarian Invasion's descr_regions has a 'legion: X' line after the name and a beliefs line after
        farming (9 value lines, all 72 regions of BI's own file): the reader took the legion for the town."""
        from campaign_editor.moddata import region_entries
        text = ["Caledonia", "\tlegion: Caledonica", "\tDal_Raida", "\tcelts", "\tPictii", "\t111 111 0",
                "\tslaves", "\t5", "\t5", "\tpagan 90 christianity 10",
                "Tribus_Saxones", "\tlegion: Barbaricorum", "\tVicus_Saxones", "\tsaxons", "\tAngles",
                "\t232 41 55", "\ttimber, slaves, amber", "\t5", "\t3", "\tpagan 100"]
        e = {k: {f: v for f, (_, v) in d.items()} for k, d in region_entries(text).items()}
        c = e["Caledonia"]
        self.assertEqual((c["settlement"], c["creator"], c["rebels"]), ("Dal_Raida", "celts", "Pictii"))
        self.assertEqual((c["legion"], c["farming"], c["beliefs"]), ("legion: Caledonica", "5", "pagan 90 christianity 10"))
        self.assertEqual(e["Tribus_Saxones"]["resources"], "timber, slaves, amber")

if __name__ == "__main__":
    unittest.main()
