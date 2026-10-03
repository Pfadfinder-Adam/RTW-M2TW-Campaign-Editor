"""Campaign rules: the settings files of both games shown as plain values with an explanation, changed in place.

Medieval II: descr_campaign_db.xml (agents, ages, revolts, crusades...), descr_settlement_mechanics.xml (how towns
grow, riot and pay), descr_diplomacy.xml (what offers cost), descr_recruitment.xml. Rome under REX:
descr_settlement_mechanics.xml (population per settlement level, the same factors). REX / M2EX:
descr_unit_sizes.txt (the Unit size choices), and the engines' own settings descr_ex.txt (ages, bribery, hordes,
camera, max_factions...) and descr_caps_ex.txt (feature switches: recruitment slots, sprite format, conversion...) -
each value explained by the comment the engine writes above it in the file.

The files are read line by line, not by an XML parser: M2EX's own descr_campaign_db.xml has values without quotes
(bool=false) that a parser refuses, and a write changes only the value's characters - the rest stays byte for byte."""

import os
import re

from .moddata import _ci
from .textio import TextFile

FILES = (
    ("descr_campaign_db.xml", "Campaign rules"),
    ("descr_settlement_mechanics.xml", "Towns: growth, order, income"),
    ("descr_diplomacy.xml", "Diplomacy offers"),
    ("descr_recruitment.xml", "Recruitment"),
    ("descr_unit_sizes.txt", "Unit sizes"),
    ("descr_ex.txt", "Engine settings (REX / M2EX)"),
    ("descr_caps_ex.txt", "Engine features (REX / M2EX)"),
)
TYPE_WORDS = ("uint", "int", "float", "bool", "string")
PLAIN_ATTRS = TYPE_WORDS + ("value", "flag", "modifier")

# the tag's inside as quoted texts or single other characters (no two ways to match the same text - linear time;
# the attributes are then read from it by RE_ATTR)
RE_TAG = re.compile(r"<(/?)([A-Za-z_][\w.-]*)((?:\"[^\"]*\"|'[^']*'|[^<>\"'])*?)(/?)>")
RE_ATTR = re.compile(r"([\w.-]+)\s*=\s*(\"([^\"]*)\"|'([^']*)'|([^\s/>]+))")


class Rule:
    """One value of a settings file: where it sits (section, key), its text, its type and its place in the line."""

    def __init__(self, path, section, key, attr, value, kind, line, start, end, note=None):
        self.path, self.section, self.key, self.attr = path, section, key, attr
        self.value, self.kind, self.line, self.start, self.end = value, kind, line, start, end
        self.note = note                # the file's own explanation (the comment above an engine setting)

    @property
    def ident(self):
        return (self.section, self.key)

    def __repr__(self):
        return "Rule(%s / %s = %s)" % (self.section, self.key, self.value)


def _kind(attr, value):
    if attr in TYPE_WORDS:
        return attr
    if attr == "flag" or value.lower() in ("true", "false"):
        return "bool"
    if re.fullmatch(r"-?\d+", value):
        return "int"
    if re.fullmatch(r"-?\d*\.\d+|-?\d+\.\d*", value):
        return "float"
    return "string"


def _blank_comments(lines):
    """The lines with every <!-- ... --> turned into spaces (offsets kept), comments running over lines too."""
    out, inside = [], False
    for text in lines:
        chars, i = list(text), 0
        while i < len(text):
            if inside:
                j = text.find("-->", i)
                end = len(text) if j < 0 else j + 3
                for k in range(i, end):
                    chars[k] = " "
                inside = j < 0
                i = end
            else:
                j = text.find("<!--", i)
                if j < 0:
                    break
                inside, i = True, j
        out.append("".join(chars))
    return out


def read_xml(path, f):
    """[Rule] of one of the XML settings files (a loaded TextFile)."""
    rules, stack = [], []
    for i, text in enumerate(_blank_comments(f.texts())):
        for m in RE_TAG.finditer(text):
            closing, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
            if closing:
                while stack and stack.pop()[0] != tag:
                    pass
                continue
            found = []
            for a in RE_ATTR.finditer(attrs):
                gi = 3 if a.group(3) is not None else 4 if a.group(4) is not None else 5
                start = m.start(3) + a.start(gi)
                found.append((a.group(1), a.group(gi), start, start + len(a.group(gi))))
            name = next((v for k, v, _, _ in found if k == "name"), None)
            where = [n for _, n in stack if n != "root"]
            for attr, value, s, e in found:
                if attr == "name":
                    continue
                if attr in TYPE_WORDS + ("value", "flag") or (attr == "modifier" and not name):
                    section, key = where + ([name] if name else []), tag
                elif name:
                    section, key = where + [name], attr
                else:
                    section, key = where, "%s %s" % (tag, attr)
                rules.append(Rule(path, " / ".join(section) or "settings", key, attr, value, _kind(attr, value), i, s, e))
            if not selfclose and tag not in ("?xml",):
                stack.append((tag, name or tag))
    # blocks without a name that repeat (descr_diplomacy's text entries): numbered, so each value is its own
    seen = {}
    for r in rules:
        n = seen[r.ident] = seen.get(r.ident, 0) + 1
        if n > 1:
            r.section = "%s %d" % (r.section, n)
    for r in rules:
        if seen.get((r.section, r.key), 0) > 1 and not r.section[-1].isdigit():
            r.section += " 1"
    return rules


def read_unit_sizes(path, f):
    """[Rule] of descr_unit_sizes.txt: 'unit_size <text key> <multiplier>' - the multiplier is the value."""
    rules = []
    for i, text in enumerate(f.texts()):
        code = text.split(";", 1)[0]
        m = re.match(r"(\s*unit_size\s+(\S+)\s+)(\S+)", code)
        if m:
            rules.append(Rule(path, "unit sizes (battle options)", m.group(2), "multiplier", m.group(3), "float", i,
                              m.start(3), m.end(3)))
    return rules


def read_ex(path, f):
    """[Rule] of an engine settings file (descr_ex.txt / descr_caps_ex.txt of REX or M2EX): 'key value' lines; the
    section is the last ';;;; / ; Heading / ;;;;' banner, the explanation the comment lines right above the key.
    Settings left commented out are not offered (the engine's default holds)."""
    rules, section, note, head = [], "switches" if "caps" in os.path.basename(path).lower() else "general", [], None    # head: None, 'open' (after a banner), 'in'
    for i, text in enumerate(f.texts()):
        s = text.strip()
        if not s:
            note = []
            continue
        if s.startswith(";"):
            body = s.lstrip(";").strip()
            if not body:
                if re.fullmatch(r";{3,}", s):     # a ';;;;' banner line: opens or closes a heading
                    head = "open" if head is None else None
                    note = []
                continue                          # a bare ';' keeps the comment going
            if head == "open":                 # the heading's first line names the section
                section, head = body.replace(" / ", " and "), "in"     # ' / ' is the tool's level mark
            elif head is None:
                note.append(body)
            continue
        head = None
        m = re.match(r"\s*([A-Za-z_][\w.]*)(\s+)([^;]*?)\s*(;.*)?$", text)
        if not m or not m.group(3):
            note = []
            continue
        value = m.group(3)
        start = m.start(3)
        kind = _kind("", value) if " " not in value and "\t" not in value else "words"
        rules.append(Rule(path, section, m.group(1), "value", value, kind, i, start, start + len(value),
                          "\n".join(note) or None))
        note = []
    return rules


# descr_strat.txt's top: the campaign's dates and switches (both games; the exes know every one of these words)
STRAT_SECTION = "campaign start"
STRAT_FLAGS = (
    ("night_battles_enabled", "battles may be fought at night"),
    ("show_date_as_turns", "the campaign shows the turn instead of the year (Medieval II)"),
    ("marian_reforms_disabled", "the Marian reforms never happen (Rome; Medieval II's file carries it too)"),
    ("marian_reforms_activated", "the Marian reforms have already happened at the start (Rome)"),
    ("rebelling_characters_active", "generals of low loyalty may rebel"),
    ("gladiator_uprising_disabled", "no gladiator uprisings (Rome)"),
)
STRAT_KEYS = {
    "start_date": "the year and season the campaign starts (a minus = BC)",
    "end_date": "the year and season the long campaign ends",
    "timescale": "years one turn takes (Medieval II and REX; Rome's own turn is half a year)",
    "brigand_spawn_value": "how seldom brigands appear on land (bigger = fewer)",
    "pirate_spawn_value": "how seldom pirates appear at sea (bigger = fewer)",
    "random_persona_weights": "odds a faction's leader is loyal / steadfast / neutral / opportunist / treacherous "
                              "(REX / M2EX)",
}
STRAT_END = re.compile(r"^\s*(resource|faction|settlement|landmark|region|core_attitudes|faction_relationships)\b")


def read_strat(path, f, medieval2=True):
    """[Rule] of descr_strat.txt's top (until the resources): 'key value' lines (start_date, end_date, timescale,
    spawn values...) and the switch lines (night_battles_enabled ...) as on / off - a missing switch is offered as
    off (line None) and written in when turned on."""
    rules, in_list, have = [], False, set()
    for i, text in enumerate(f.texts()):
        code = text.split(";", 1)[0]
        if STRAT_END.match(code):
            break
        t = code.split()
        if not t:
            continue
        if t[0] in ("playable", "unlockable", "nonplayable"):
            in_list = True
            continue
        if in_list:
            in_list = t[0] != "end"
            continue
        if t[0] == "campaign":
            continue
        if len(t) == 1:
            m = re.search(re.escape(t[0]), text)
            rules.append(Rule(path, STRAT_SECTION, t[0], "switch", "on", "flag", i, m.start(), m.end()))
            have.add(t[0])
            continue
        m = re.match(r"(\s*\S+\s+)([^;]*?)\s*(;.*)?$", text)
        value = m.group(2)
        kind = "date" if t[0] in ("start_date", "end_date") else (
            _kind("", value) if len(t) == 2 else "words")
        rules.append(Rule(path, STRAT_SECTION, t[0], "value", value, kind, i, m.start(2), m.start(2) + len(value)))
    for key, _ in STRAT_FLAGS:
        if key not in have and (medieval2 or key != "show_date_as_turns"):     # RomeTW / REX do not know it
            rules.append(Rule(path, STRAT_SECTION, key, "switch", "off", "flag", None, 0, 0))
    return rules


def _apply_strat(f, changes):
    """Switches turned off lose their line, turned on get one after the last line of the top; values in place."""
    for rule, new in changes.items():
        if rule.kind != "flag":
            text = f.text(rule.line)
            if text[rule.start:rule.end] != rule.value:
                raise ValueError("descr_strat.txt changed on disk since it was read - load again")
            f.set(rule.line, text[:rule.start] + new.strip() + text[rule.end:])
    for rule, new in sorted(changes.items(), key=lambda x: -(x[0].line or -1)):
        if rule.kind == "flag" and new == "off" and rule.line is not None:
            f.delete(rule.line, rule.line + 1)
    on = [r.key for r, new in changes.items() if r.kind == "flag" and new == "on" and r.line is None]
    if on:
        last = 0
        for i, text in enumerate(f.texts()):
            if STRAT_END.match(text.split(";", 1)[0]):
                break
            if text.split(";", 1)[0].strip():
                last = i
        f.insert(last + 1, on)


def read(path, f=None, medieval2=True):
    f = f or TextFile.load(path)
    low = os.path.basename(path).lower()
    if low == "descr_strat.txt":
        return read_strat(path, f, medieval2)
    if low in ("descr_ex.txt", "descr_caps_ex.txt"):
        return read_ex(path, f)
    return read_unit_sizes(path, f) if low.endswith(".txt") else read_xml(path, f)


def game_data(mod):
    try:
        from .newmod import game_of
        d = os.path.join(game_of(mod.data), "data")
        return d if os.path.isdir(d) and os.path.normcase(os.path.abspath(d)) != \
            os.path.normcase(os.path.abspath(mod.data)) else None
    except Exception:
        return None


def files(mod, campaign=None):
    """[(file name, title, the mod's path or None, the game's path or None)] of the settings files there are; with a
    campaign also its descr_strat.txt (the top: dates, turns, switches)."""
    game = game_data(mod)
    out = []
    if campaign:
        own = _ci(mod.campaign_dir(campaign), "descr_strat.txt") if os.path.isdir(mod.campaign_dir(campaign)) else None
        gdir = os.path.join(game, "world", "maps", "campaign", campaign) if game else None
        base = _ci(gdir, "descr_strat.txt") if gdir and os.path.isdir(gdir) else None
        if own or base:
            out.append(("descr_strat.txt", "The campaign %s" % campaign, own, base))
    for name, title in FILES:
        own = _ci(mod.data, name)
        base = _ci(game, name) if game else None
        if own or base:
            if not own and name.lower().endswith("_ex.txt"):    # the engines read these from the mod alone
                title += " - this mod has none, so the engine's defaults hold; a change puts a copy in the mod"
            out.append((name, title, own, base))
    return out


def check(rule, text):
    """None, or why the text cannot be this value."""
    t = text.strip()
    if not t:
        return "empty"
    if rule.kind == "uint":
        return None if re.fullmatch(r"\d+", t) else "a whole number, 0 or more"
    if rule.kind == "int":
        return None if re.fullmatch(r"-?\d+", t) else "a whole number"
    if rule.kind == "float":
        return None if re.fullmatch(r"-?\d+(\.\d*)?|-?\.\d+", t) else "a number (like 1.5)"
    if rule.kind == "bool":
        return None if t in ("true", "false") else "true or false"
    if rule.kind == "flag":
        return None if t in ("on", "off") else "on or off"
    if rule.kind == "date":
        return None if re.fullmatch(r"-?\d+( summer| winter)?", " ".join(t.split())) else \
            "a year (a minus = BC) and summer or winter, like '1080 summer'"
    if rule.kind == "words":
        return None if not re.search(r"[\"'<>;]", t) else "words or numbers, no quotes or ';'"
    return None if not re.search(r"[\"'<>\s]", t) else "one word, no quotes"


def apply(plan, name, changes, own, base):
    """Write {Rule: new text} of one file: the mod's own file edited in place; a mod without it gets the game's
    file with the changes (the game reads the mod's one first)."""
    target = own or os.path.join(plan.mod.data, name)
    if own:
        f = plan.edit(own)
    else:
        f = TextFile.load(base)
    if name.lower() == "descr_strat.txt":
        for rule, new in changes.items():
            why = check(rule, new)
            if why:
                raise ValueError("%s / %s: '%s' - must be %s" % (rule.section, rule.key, new, why))
        if not own:
            raise ValueError("the campaign's descr_strat.txt is not in the mod")
        _apply_strat(f, {r: " ".join(n.split()) for r, n in changes.items()})
        for rule, new in changes.items():
            plan.note(f, "%s / %s: %s -> %s" % (rule.section, rule.key, rule.value, new.strip()))
        return
    for rule, new in sorted(changes.items(), key=lambda x: (x[0].line, -x[0].start)):
        why = check(rule, new)
        if why:
            raise ValueError("%s / %s: '%s' - must be %s" % (rule.section, rule.key, new, why))
        text = f.text(rule.line)
        if text[rule.start:rule.end] != rule.value:
            raise ValueError("%s changed on disk since it was read - load again" % name)
        f.set(rule.line, text[:rule.start] + new.strip() + text[rule.end:])
        plan.note(f if own else None, "%s / %s: %s -> %s" % (rule.section, rule.key, rule.value, new.strip()))
    if not own:
        plan.binary(target, f.dump())
        plan.note(None, "%s: the mod had none - the game's copy with these changes is put in the mod" % name)


# ---------------------------------------------------------------------------
# Plain words
# ---------------------------------------------------------------------------
SECTIONS = {
    STRAT_SECTION: "the top of the campaign's descr_strat.txt: when it starts and ends, how long a turn is, switches",
    "settings": "the file's settings",
    "demeanours": "how a faction's mood (its attitude) moves its answers to offers",
    "recruitment":"how many units a town trains at once and how recruit pools refill and drain",
    "religion": "witches, heretics, inquisitors and priests: how many, how fast they convert",
    "bribery": "the chance to bribe an army or a town",
    "family_tree": "ages: coming of age, marriage, children, old age, death",
    "diplomacy": "diplomats: how many items one offer may hold",
    "ransom": "captives after a battle: release or ransom chances",
    "autoresolve": "battles fought by the computer: captives, lopsided battles, sea battles",
    "settlement": "sacking, exterminating, unrest from religion, which towns need siege gear",
    "revolt": "when generals and towns rise up",
    "hordes": "where a horde (a faction without towns) goes",
    "merchants": "merchants' income",
    "agents": "chances of assassins, inquisitors, priests and merchants' takeovers",
    "crusades": "crusades and jihads: when, how far, when they disband",
    "display": "what the campaign map shows",
    "missions": "the council's missions",
    "characters": "characters on the map",
    "population_levels": "the people a settlement needs to grow to the next level (Rome under REX)",
    "factor_modifiers": "each line of the town's scrolls (growth, public order, income): x its weight, min, max",
    "diplomacy_text_fields": "where the diplomacy screen switches words (how friendly, how rich...): each word up to "
                             "its threshold",
    "item_modifiers": "each offer a diplomat can make: its price and how it moves standing",
    "unit sizes (battle options)": "the Unit size choices in the options: soldiers of a unit x this number",
}

KEYS = {
    "recruitment_slots": "units a town trains at the same time",
    "retraining_slots": "units a town retrains at the same time",
    "max_agents_per_turn": "agents a town may recruit a turn",
    "percentage_pool_reduction_lost": "recruit pool lost (%) when the town is lost",
    "percentage_pool_reduction_occupy": "recruit pool lost (%) when the town is occupied",
    "percentage_pool_reduction_sack": "recruit pool lost (%) when the town is sacked",
    "percentage_pool_reduction_exterminate": "recruit pool lost (%) when the town is exterminated",
    "max_age": "oldest age a character normally reaches",
    "max_age_before_death": "no one lives past this",
    "max_age_for_marriage_for_male": "a man marries up to this age",
    "max_age_for_marriage_for_female": "a woman marries up to this age",
    "max_age_of_child": "a child is shown as a child up to this age",
    "old_age": "a character counts as old from this age",
    "age_of_manhood": "a son comes of age (joins the family on the map) at this age",
    "age_of_manhood_close": "a son is shown as about to come of age from this age",
    "daughters_age_of_consent": "a daughter can marry from this age",
    "daughters_retirement_age": "a daughter stops being offered in marriage at this age",
    "age_difference_min": "a wife at most this many years older (negative = older)",
    "age_difference_max": "a wife at most this many years younger",
    "parent_to_child_min_age_diff": "a parent is at least this much older than the child",
    "min_adoption_age": "adopted sons are at least this old",
    "max_adoption_age": "adopted sons are at most this old",
    "max_age_for_conception": "a couple has children up to this age",
    "max_number_of_children": "children a couple may have",
    "max_diplomacy_items": "items one diplomatic offer may hold",
    "enemies_reject_gifts": "factions at war refuse gifts",
    "sack_money_modifier": "money from sacking a town (x)",
    "exterminate_money_modifier": "money from exterminating a town (x)",
    "siege_gear_required_for_city_level": "cities of this level and above need siege gear to attack",
    "siege_gear_required_for_castle_level": "castles of this level and above need siege gear to attack",
    "no_towers_only_for_city_level": "cities up to this level have no shooting towers",
    "no_towers_only_for_castle_level": "castles up to this level have no shooting towers",
    "min_turn_keep_rebel_garrison": "rebel towns keep their garrison until this turn",
    "heresy_unrest_modifier": "unrest from heresy",
    "religion_unrest_modifier": "unrest from another religion",
    "max_revolt_chance": "the highest chance (%) a general revolts",
    "min_revolt_chance": "the lowest chance (%) a general revolts",
    "crusade_called_start_turn": "the first turn a crusade can be called",
    "jihad_called_start_turn": "the first turn a jihad can be called",
    "required_jihad_piety": "an imam needs this piety to call a jihad",
    "movement_points_modifier": "crusading armies move this much farther (x)",
    "assassinate_base_chance": "an assassin's base chance (%)",
    "assassinate_chance_min": "an assassination is at least this likely (%)",
    "assassinate_chance_max": "an assassination is at most this likely (%)",
    "denounce_chance_min": "a denouncement is at least this likely (%)",
    "denounce_chance_max": "a denouncement is at most this likely (%)",
    "acquisition_base_chance": "a merchant's base chance to take over another (%)",
    "base_character_chance": "base chance to bribe an army (0..1)",
    "base_settlement_chance": "base chance to bribe a town (0..1)",
    "max_witches": "witches on the whole map at most",
    "max_heretics": "heretics on the whole map at most",
    "max_inquisitors": "inquisitors on the whole map at most",
    "inquisitor_turn_start": "the first turn inquisitors appear",
    "min_capture_percent": "at least this share (%) of the losers is captured",
    "max_capture_percent": "at most this share (%) of the losers is captured",
    "base_income_modifier": "merchants' income (x)",
    "agents_can_hide": "agents can hide like armies",
    "revolt_additional_armies": "a revolt raises extra armies",
    "base": "people a town starts with on reaching this level",
    "upgrade": "people needed to grow to the next level",
    "min": "fewest people the level holds",
    "max": "most people the level holds (overcrowding past this)",
    "modifier": "weight of this line (1.0 = as the game has it)",
    "upper_threshold": "the word is used up to this value",
    "pip_modifier": "weight of this line (1.0 = as the game has it)",
    "city_modifier": "weight in cities",
    "castle_modifier": "weight in castles",
    "pip_min": "the line gives at least this",
    "pip_max": "the line gives at most this",
    "cost": "price of the offer (x)",
    "faction_standing": "how much the offer moves the other faction's opinion",
    "global_standing": "how much the offer moves everyone's opinion",
    "deplenish_multiplier": "how fast recruit pools drain (x)",
    "deplenish_offset": "recruit pools drain by this each time",
    "recruitment slots_required": "units a town trains at the same time",
    "retraining slots_required": "units a town retrains at the same time",
    "agent slots_required": "agents a town trains at the same time",
    "lost percentage_pool_reduction": "recruit pool lost (%) when the town is lost",
    "occupy percentage_pool_reduction": "recruit pool lost (%) when the town is occupied",
    "sack percentage_pool_reduction": "recruit pool lost (%) when the town is sacked",
    "exterminate percentage_pool_reduction": "recruit pool lost (%) when the town is exterminated",
    "UI_VIDEO_UNIT_SCALE_SMALL": "Small: soldiers x this",
    "UI_VIDEO_UNIT_SCALE_NORMAL": "Normal: soldiers x this",
    "UI_VIDEO_UNIT_SCALE_LARGE": "Large: soldiers x this",
    "UI_VIDEO_UNIT_SCALE_HUGE": "Huge: soldiers x this",
}

FACTOR_KINDS = {"SPF": "population growth", "SOF": "public order", "SIF": "income"}


def explain(rule):
    """A plain sentence for a value (the key's own words where known; an engine setting: the file's own comment)."""
    if getattr(rule, "note", None):
        return rule.note
    if rule.section == STRAT_SECTION:
        return STRAT_KEYS.get(rule.key) or dict(STRAT_FLAGS).get(rule.key) or rule.key.replace("_", " ")
    words = KEYS.get(rule.key)
    last = rule.section.split(" / ")[-1]
    m = re.match(r"(SPF|SOF|SIF)_(.+)", last)
    if m:
        what = "%s: %s" % (FACTOR_KINDS[m.group(1)], m.group(2).lower().replace("_", " ").replace("squalour", "squalor"))
        return "%s - %s" % (what, words) if words else what
    if words:
        return words
    return rule.key.replace("_", " ")


def section_words(section):
    first = section.split(" / ")[0]
    return SECTIONS.get(section) or SECTIONS.get(first) or ""
