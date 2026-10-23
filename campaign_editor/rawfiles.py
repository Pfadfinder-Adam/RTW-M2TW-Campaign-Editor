"""Any file of the game as it is written (the user, 2026-10-22, the rule COMPLETENESS: 'everything both games can do,
and better' - its floor: nothing the game reads is out of the editor's reach, even before it has a window of its
own). Every text file of the mod's data folder and of the game's data under it, found the way the engine finds it
(the mod's own first, the game's under it; names without case), opened in the editor's notepad and written through a
Plan like every other change: Preview, a backup, byte-exact Restore, Undo. A file read from the game's data is
written as the mod's own copy (Plan.edit), the game's folder is never touched.

Only the lines typed change - every other byte, the line endings and the file's encoding stay (textio). Before the
game is started the notepad underlines what the game would stumble on: an xml file that does not parse, a brace never
closed or closed twice."""

import difflib
import os
import xml.etree.ElementTree as ET

# the files the games read as text (Medieval II's descr_*.db, the .strings.bin and the packs are binary: not here)
TEXT_EXT = (".txt", ".xml", ".lnt", ".nut", ".lua", ".cfg", ".ini", ".json")

# what a file is, in plain words, and where the editor has a window of its own for it (the start of the name; the
# longest match wins) - the rest of the files are shown with their folder's words below
ABOUT = {
    "export_descr_unit": ("every unit: soldiers, stats, costs, owners", "Unit editor"),
    "export_descr_buildings": ("every building: levels, what each gives and recruits", "Building editor"),
    "export_descr_character_traits": ("character traits and what gives them", "Traits (Characters)"),
    "export_descr_ancillaries": ("retinue members and what gives them", "Traits (Characters)"),
    "export_descr_guilds": ("guilds (Medieval II): which building, their points", None),
    "export_descr_sounds_units_voice": ("what units say, by culture / accent", "Unit editor > Voice"),
    "export_descr_sounds": ("sounds and voices of the game", None),
    "export_descr_advice": ("the advisor's lines", None),
    "descr_strat": ("the campaign's start: factions, towns, armies, characters, diplomacy", "Map, Faction editor"),
    "descr_regions": ("regions: names, rebels, colour, resources, farming", "Map, Settlements"),
    "descr_sm_factions": ("factions: culture, colours, symbols, AI", "Faction editor"),
    "descr_character": ("agents and generals: their models and moves", "Faction editor"),
    "descr_names": ("the names of each faction's people", "Faction editor > Names"),
    "descr_cultures": ("cultures: their towns' and agents' looks", "Faction editor > Culture"),
    "descr_rebel_factions": ("rebels: their units and chances", "Rebels"),
    "descr_mercenaries": ("mercenaries for hire, by region pool", "Mercenaries"),
    "descr_events": ("events by date: plagues, factions that come later", "Events"),
    "descr_disasters": ("earthquakes, floods, fires, storms", None),
    "descr_win_conditions": ("what each faction must hold to win", "Victory conditions"),
    "campaign_script": ("the campaign's own script", "Events > Campaign script"),
    "descr_model_battle": ("battle models of the units", "Unit editor > Models"),
    "descr_model_strat": ("campaign-map figures", "Models"),
    "descr_mount": ("horses, camels, elephants the units ride", None),
    "descr_animals": ("animals that go with units (dogs, pigs)", None),
    "descr_engines": ("siege engines", None),
    "descr_ship": ("ships in battle", None),
    "descr_projectile": ("arrows, stones, javelins: damage, range", None),
    "descr_unit_sizes": ("the Unit size choices (REX / M2EX)", "Campaign rules"),
    "descr_campaign_db": ("the campaign's rules (Medieval II): ages, agents, revolts", "Campaign rules"),
    "descr_settlement_mechanics": ("how towns grow, riot and pay", "Campaign rules"),
    "descr_diplomacy": ("what diplomatic offers cost (Medieval II)", "Campaign rules"),
    "descr_recruitment": ("recruitment slots and pools (Medieval II)", "Campaign rules"),
    "descr_ex": ("the engine's own settings (REX / M2EX)", "Campaign rules"),
    "descr_caps_ex": ("the engine's limits (REX / M2EX)", "Campaign rules"),
    "descr_missions": ("council, pope and guild missions (Medieval II)", None),
    "descr_senate": ("the Senate's missions (Rome)", None),
    "descr_difficulty": ("what each difficulty changes", None),
    "descr_triumphs": ("triumphs (Rome)", None),
    "descr_formations": ("battle formations", None),
    "descr_religions": ("religions (Medieval II)", "Religions"),
    "descr_beliefs": ("beliefs (Barbarian Invasion, Medieval II)", "Religions"),
    "descr_sm_resources": ("resources on the campaign map", "Map > Resources"),
    "descr_sm_landmarks": ("Rome's wonders", "Wonders"),
    "descr_climates": ("climates: trees, ground, weather", "Terrain > Climates"),
    "descr_terrain": ("the campaign map's ground", "Terrain editor"),
    "descr_event_images": ("the pictures of event messages", "Events"),
    "descr_banners": ("banners and their colours", "Art"),
    "descr_standards": ("standards and symbols", "Art"),
    "descr_ui_buildings": ("the buildings' pictures in the panel", "Building editor"),
    "descr_sounds": ("sound effects and music", None),
    "descr_effects": ("effects in battle (fire, smoke, dust)", None),
    "descr_particle": ("particles in battle", None),
}

# a folder's words for the files ABOUT does not name
FOLDERS = (
    ("world/maps/campaign/", "a campaign's file"),
    ("world/maps/base/", "the map's base file"),
    ("world/maps/battle/", "a battle map"),
    ("text/", "texts players read"),
    ("menu/", "the menu's layout"),
    ("ui/", "the interface"),
    ("settlement_plans/", "a town's plan in battle"),
    ("globallighting/", "light and shadows"),
    ("sounds/", "sounds"),
    ("scripts/", "scripts"),
)


def is_text(name):
    return name.lower().endswith(TEXT_EXT)


def listing(mod):
    """Every text file of the data folders the game reads: [{'rel', 'path', 'game': True when it is the game's own
    file under the mod}], the mod's own winning over the game's of the same name (any case), sorted by rel."""
    got = {}
    for i, root in enumerate(mod.roots()):
        for dp, dn, fn in os.walk(root):
            dn.sort()
            for n in fn:
                if not is_text(n):
                    continue
                p = os.path.join(dp, n)
                rel = os.path.relpath(p, root).replace("\\", "/")
                got.setdefault(rel.lower(), {"rel": rel, "path": p, "game": i > 0})
    return [got[k] for k in sorted(got)]


def about(rel):
    """(what the file is, the editor's window for it or None) - plain words for any file."""
    low = rel.lower().replace("\\", "/")
    name = low.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]
    hits = [k for k in ABOUT if stem.startswith(k)]
    if hits:
        return ABOUT[max(hits, key=len)]
    for pre, words in FOLDERS:
        if low.startswith(pre) or ("/" + pre) in ("/" + low):
            return words, None
    return "a file the game reads", None


def comment_mark(rel):
    """The line comment of the file's kind: ';' (the games' txt), '--' (lua), '//' (Squirrel), None (xml, json)."""
    low = rel.lower()
    if low.endswith((".xml", ".json")):
        return None
    if low.endswith(".lua"):
        return "--"
    if low.endswith(".nut"):
        return "//"
    return ";"


def _code(line, mark):
    if not mark:
        return line
    c = line.find(mark)
    return line if c < 0 else line[:c]


def check(rel, lines):
    """{row (1-based): why} - what the game would stumble on, found before it starts: an xml that does not parse (its
    first fault), a '}' with no '{' before it, a '{' never closed (the last one open)."""
    low = rel.lower()
    if low.endswith(".xml"):
        try:
            ET.fromstring("\n".join(lines).lstrip("﻿").encode("utf-8"))
        except ET.ParseError as e:
            row = max(1, e.position[0]) if getattr(e, "position", None) else 1
            return {row: "the xml does not read here: %s" % str(e).split(":")[0]}
        except ValueError:
            return {}
        return {}
    if low.endswith(".json") or "/text/" in "/" + low.replace("\\", "/"):
        return {}                                       # a text table's {KEY} are not blocks
    mark = comment_mark(rel)
    errors, open_rows = {}, []
    for i, line in enumerate(lines):
        for ch in _code(line, mark):
            if ch == "{":
                open_rows.append(i + 1)
            elif ch == "}":
                if open_rows:
                    open_rows.pop()
                else:
                    errors.setdefault(i + 1, "'}' closes nothing - no '{' is open above it")
    if open_rows:
        errors.setdefault(open_rows[-1], "this '{' is never closed - the game reads the rest of the file into it")
    return errors


def plan_lines(plan, path, lines):
    """The file written with these lines: only the lines that differ change (each untouched line keeps its bytes and
    its own ending). Returns how many lines changed (0: nothing)."""
    f = plan.edit(path)
    old = f.texts()
    if old == list(lines):
        return 0
    ops = difflib.SequenceMatcher(None, old, lines, autojunk=False).get_opcodes()
    n = 0
    for tag, a, b, c, d in reversed(ops):               # from the end: the earlier lines keep their place
        if tag == "equal":
            continue
        if tag == "replace" and b - a == d - c:
            for k in range(b - a):
                f.set(a + k, lines[c + k])
        else:
            f.delete(a, b)
            f.insert(a, lines[c:d])
        n += max(b - a, d - c)
    plan.note(f, "written by hand in the editor's notepad: %d line(s) changed" % n)
    for row, why in sorted(check(path, lines).items())[:5]:
        plan.warn(f, "line %d: %s" % (row, why))
    return n


__all__ = ["TEXT_EXT", "listing", "about", "comment_mark", "check", "plan_lines"]
