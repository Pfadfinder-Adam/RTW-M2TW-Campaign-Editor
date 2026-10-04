"""A tiny synthetic mod (no game files): one faction 'alpha' with a town, the rebels with another, a 4 x 4 map -
what the editor's tests run on, and what the exe's self-check loads (selfcheck.py)."""

import codecs
import os
import struct

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



def make(root):
    """The tiny mod written under root (root/data/...); returns the data folder."""
    d = os.path.join(root, "data")
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
    return d
