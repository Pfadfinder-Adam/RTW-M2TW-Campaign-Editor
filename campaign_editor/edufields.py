"""What every value of a unit's line in export_descr_unit.txt means, both games, in plain words - from the notes
the games write at the top of that file (Rome's and Medieval II's), the few they leave out marked so. The Unit
editor's 'Every line of the block' window shows it on the '?' beside each line, for the value typed there now."""

import re

from . import unitattrs

# one weapon: stat_pri / stat_sec (/ stat_ter, Medieval II)
WEAPON = [
    ("attack", "how hard each man hits (0 = no weapon: the rest of the line is not read)"),
    ("charge bonus", "added to the attack when it charges"),
    ("missile", "the missile it fires (descr_projectile.txt); no = not a missile weapon"),
    ("range", "how far the missile flies, in metres"),
    ("ammunition", "missiles each man carries"),
    ("weapon type", "melee, thrown, missile, siege_missile or siege_melee"),
    ("tech type", "Rome: simple, other, blade, archery or siege; Medieval II: melee_simple, melee_blade, "
                  "missile_mechanical, missile_gunpowder, artillery_mechanical, artillery_gunpowder or naval_gunpowder"),
    ("damage type", "piercing, blunt, slashing or fire (the game's own notes: likely no longer used)"),
    ("sound", "the sound when it hits: none, knife, mace, axe, sword, spear or club"),
    ("attack delay", "the least time between two attacks, in tenths of a second"),
    ("skeleton factor", "skeleton compensation factor in melee - should be 1 (Rome's notes leave it out, Medieval "
                        "II's name it)"),
]
EFFECT = ("fire effect", "Medieval II, may be left out: the effect played when the weapon fires")
EX = [("attack vs mounted", "attack bonus against mounted units"),
      ("defence vs mounted", "defence bonus against mounted units"),
      ("armour piercing", "armour penetration")]

FIXED = {
    "soldier": [("model", "the soldier's model (descr_models_battle.txt / battle_models.modeldb)"),
                ("men", "the number of ordinary soldiers (the unit-size setting scales it)"),
                ("extras", "pigs, dogs, elephants, chariots, artillery pieces... attached to the unit"),
                ("mass", "collision mass of the men, 1.0 = normal (infantry only)"),
                ("radius", "may be left out: the man's collision radius, metres (0.4 when left out; vanilla only "
                           "Barbarian Invasion's berserkers and hounds of Culann have it)"),
                ("height", "may be left out: the man's height, metres (1.7 when left out)")],
    "formation": [("close: side", "space between men side to side in close formation, metres"),
                  ("close: front", "space front to back in close formation, metres"),
                  ("loose: side", "space side to side in loose formation, metres"),
                  ("loose: front", "space front to back in loose formation, metres"),
                  ("ranks", "the default number of ranks"),
                  ("formation", "a formation it can take: square, horde, phalanx, wedge, testudo (Rome only), "
                                "schiltrom, shield_wall (Barbarian Invasion and Medieval II); every unit needs "
                                "square, horde or phalanx"),
                  ("second formation", "a second one (one or two may be named)")],
    "stat_health": [("man", "hit points of a man"),
                    ("animal", "hit points of the mount or attached animal (ridden horses and camels have none of "
                               "their own)")],
    "stat_pri_armour": [("armour", "the man's armour"),
                        ("defence skill", "his skill at parrying (not used when shot at)"),
                        ("shield", "the shield (only against attacks from the front or left)"),
                        ("sound", "the sound when he is hit: flesh, leather or metal (the engine also takes wood, "
                                  "ground, building)")],
    "stat_sec_armour": [("armour", "the animal's or vehicle's armour (ridden horses have none of their own)"),
                        ("defence skill", "its skill at defending"),
                        ("sound", "the sound when it is hit: flesh, leather or metal")],
    "stat_armour_ex": [("armour", "base armour"), ("armour, upgrade 1", "armour after the first upgrade"),
                       ("armour, upgrade 2", "after the second"), ("armour, upgrade 3", "after the third"),
                       ("defence skill", "skill at parrying (not used when shot at)"),
                       ("shield vs melee", "the shield in melee"), ("shield vs missiles", "the shield against missiles"),
                       ("sound", "the sound when hit: flesh, leather or metal")],
    "stat_ground": [("scrub", "combat bonus or penalty on scrub"), ("sand", "on sand"), ("forest", "in forest"),
                    ("snow", "on snow")],
    "stat_mental": [("morale", "the base morale"),
                    ("discipline", "normal, low, disciplined, impetuous (charges without orders) or berserker "
                                   "(goes berserk); how it takes morale shocks"),
                    ("training", "untrained, trained or highly_trained: how tidy its formation is")],
    "stat_food": [("food eaten", "no longer used (the game's own notes)"), ("food carried", "no longer used")],
    "stat_cost": [("turns", "turns to recruit it"), ("cost", "the price to recruit"), ("upkeep", "upkeep a turn"),
                  ("weapon upgrade", "the price of a weapon upgrade"),
                  ("armour upgrade", "the price of an armour upgrade"),
                  ("custom battle cost", "its price in custom battles"),
                  ("custom battle: units", "Medieval II: how many of it a custom battle army takes before the "
                                           "price rises"),
                  ("custom battle: extra price", "Medieval II: what each one after those costs more")],
    "unit_info": [("melee attack", "shown on the unit's info panel"), ("missile attack", "shown on the info panel"),
                  ("defence", "shown on the info panel")],
}
for _k in ("stat_pri_ex", "stat_sec_ex", "stat_ter_ex"):
    FIXED[_k] = EX

ONE = {
    "type": "the unit's inner name (not always the name on screen)",
    "dictionary": "the key of its name and descriptions in the text files",
    "category": "infantry, cavalry, siege, handler, ship or non_combatant",
    "class": "light, heavy, missile, spearmen or skirmish - with the category: its place in formations and the AI's "
             "use",
    "voice_type": "the voice it speaks with: Light, Medium, Heavy, General or Female (Rome writes them Light_1...; "
                  "both spellings work)",
    "accent": "Medieval II: the accent it speaks in battle whatever its owner's (an accent of "
              "descr_sounds_accents.txt, letter case and all - another name leaves it silent); on the campaign map "
              "only with descr_campaign_db's enable_unit_accent_overrides. Right after voice_type",
    "banner": "Medieval II: a banner it carries - two words: the kind (faction, holy or unit) and the banner's name "
              "(main_infantry, crusade, templars...); the line may repeat",
    "officer": "an officer's model (up to three officer lines)",
    "ship": "the ship it sails, if it is one",
    "engine": "its siege engine",
    "mounted_engine": "Medieval II: an engine it rides, like a war wagon",
    "animal": "the animals its handlers bring (handler units): wardogs or pigs",
    "mount": "what its men ride",
    "stat_heat": "extra fatigue in hot climates",
    "stat_charge_dist": "how far from the enemy it starts its charge",
    "stat_fire_delay": "extra delay between volleys, beyond the animation's",
    "stat_stl": "Medieval II: how many men it needs to count as alive",
    "info_pic_dir": "Medieval II: the folder of its info picture (instead of the faction's)",
    "card_pic_dir": "Medieval II: the folder of its unit card (instead of the faction's)",
}

LISTS = {
    "attributes": "its abilities - words, any number of them",
    "stat_pri_attr": "the primary weapon's abilities - words, any number of them; no = none (a word the game does "
                     "not know here stops the unit from loading)",
    "stat_sec_attr": "the secondary weapon's abilities - words; no = none (a word the game does not know here stops "
                     "the unit from loading)",
    "stat_ter_attr": "the third weapon's abilities - words; no = none (a word the game does not know here stops the "
                     "unit from loading)",
    "ownership": "the factions and cultures that may have it",
    "armour_ug_levels": "Medieval II: the armourer's level each armour upgrade needs (the first = the base)",
    "armour_ug_models": "Medieval II: the model for each armour level, in the same order",
    "mount_effect": "up to three bonuses against units riding a kind of mount: 'elephant +3', 'horse -2'",
}

# the words the games' own notes explain (REX / M2EX words: unitattrs)
WORDS = {
    "sea_faring": "can board ships", "can_swim": "can swim across rivers (Barbarian Invasion, Medieval II)",
    "hide_forest": "can hide in forest", "hide_improved_forest": "can hide in forest, better",
    "hide_long_grass": "can hide in long grass", "hide_anywhere": "can hide anywhere",
    "can_sap": "can dig tunnels under walls", "frighten_foot": "frightens infantry nearby",
    "frighten_mounted": "frightens cavalry nearby",
    "can_run_amok": "may run out of control when the riders lose control of the animals",
    "general_unit": "can be a named character's bodyguard", "cantabrian_circle": "has the Cantabrian circle ability",
    "no_custom": "cannot be picked in custom battles", "command": "carries an eagle: a bonus to units nearby",
    "mercenary_unit": "a mercenary, open to every faction", "is_peasant": "a peasant unit (the game's notes: unknown)",
    "druid": "can chant to raise morale", "power_charge": "its charge bonus fades more slowly",
    "free_upkeep_unit": "can be kept free in a town", "warcry": "can shout a war cry",
    "screeching_women": "can screech to frighten the enemy", "legionary_name": "takes a legion's name",
    "ap": "armour piercing: counts only half the target's armour",
    "bp": "body piercing: the missile passes through men and hits those behind",
    "spear": "long spears: better against cavalry, worse against infantry",
    "light_spear": "spears: braced, a defence against cavalry charging from the front",
    "long_pike": "very long pikes (phalanx units)", "short_pike": "shorter spears",
    "prec": "throws / fires just before charging", "thrown": "the missile is thrown, not fired",
    "launching": "may throw the men it hits into the air", "area": "hits an area, not one man",
    "fire": "a fire attack", "no": "none", "lock_morale": "never routs",
    # words both vanilla files use that their notes do not list
    "slightly_hardy": "tires a little more slowly (fatigue -1)", "hardy": "tires slowly (fatigue -2)",
    "very_hardy": "tires very slowly (fatigue -4)", "can_withdraw": "can withdraw from a battle",
    "can_formed_charge": "charges in formation", "can_horde": "can become a horde",
    "start_not_skirmishing": "starts a battle with skirmish mode off", "warcry_": "",
    "knight": "Medieval II: counts as knights", "peasant": "Medieval II: counts as peasants",
    "gunpowder_unit": "Medieval II: a gunpowder unit", "gunmen": "Medieval II: handgunners",
    "guncavalry": "Medieval II: mounted gunmen", "crossbow": "Medieval II: crossbowmen",
    "artillery": "Medieval II: an artillery crew", "cannon": "Medieval II: a cannon", "mortar": "Medieval II: a mortar",
    "rocket": "Medieval II: rockets", "explode": "Medieval II: its guns may explode",
    "fire_by_rank": "Medieval II: fires rank by rank", "stakes": "Medieval II: can plant stakes",
    "pike": "Medieval II: pikemen", "berserker": "goes berserk - a discipline word of stat_mental, not of attributes",
    "standard": "Medieval II: carries a standard", "wagon_fort": "Medieval II: can form a wagon fort",
    "incendiary": "Medieval II: sets things on fire",
    "general_unit_upgrade": "becomes the generals' bodyguard after the reforms (Rome: the Marian reforms; Medieval II: "
                            "the late bodyguards); with REX / M2EX a quoted event name after it picks the event",
}
WORDS.pop("warcry_")
# Medieval II words the battle reader gives no effect of its own: tags scripts and traits test
TAGS = ("knight", "peasant", "gunmen", "guncavalry", "crossbow", "artillery", "cannon", "mortar", "rocket", "explode",
        "pike", "standard", "incendiary")
for _w in TAGS:
    WORDS[_w] += " - a tag scripts and traits can test (PercentageUnitAttribute...); no battle effect of its own"

# the words a line may hold, for the right click (both engines' word tables, the vanilla files - the 2026-10-21 audit)
CHOICES = {
    "category": ["infantry", "cavalry", "siege", "handler", "ship", "non_combatant"],
    "class": ["light", "heavy", "missile", "spearmen", "skirmish"],
    "voice_type": ["Light", "Medium", "Heavy", "General", "Female", "Light_1", "Medium_1", "Heavy_1", "General_1",
                   "Female_1"],
    "accent": ["East_European", "Arabic", "Mediterranean", "Mongolian", "German", "Scottish", "English", "French"],
    "animal": ["wardogs", "pigs"],
}
# the line's form for the right click: its values in order, with their separators
FORMS = {
    "type": "the unit's name   (words with spaces allowed)", "dictionary": "a text key   (one word)",
    "category": " | ".join(CHOICES["category"]), "class": " | ".join(CHOICES["class"]),
    "voice_type": "Light | Medium | Heavy | General | Female   (Rome: Light_1 ...)",
    "accent": "an accent name   (Medieval II)",
    "banner": "faction|holy|unit  name   (Medieval II; a space between; the line may repeat)",
    "soldier": "model, men, extras, mass[, radius, height]   (commas between)",
    "officer": "model   (0-3 lines)", "ship": "ship type   (ship units only)",
    "engine": "engine type   (siege units only)", "mounted_engine": "engine type   (Medieval II cavalry, before mount)",
    "animal": "wardogs | pigs   (handler units only)", "mount": "mount type   (cavalry only)",
    "mount_effect": "class-or-mount +N, class-or-mount -N   (commas between; up to three)",
    "formation": "close side, close front, loose side, loose front, ranks, formation[, formation]   (commas)",
    "stat_health": "man, animal   (commas between)",
    "stat_pri_armour": "armour, defence skill, shield, sound   (commas between)",
    "stat_sec_armour": "armour, defence skill, sound   (commas between)",
    "stat_heat": "one number", "stat_ground": "scrub, sand, forest, snow   (commas between)",
    "stat_mental": "morale, discipline, training[, lock_morale]   (commas between)",
    "stat_charge_dist": "metres   (one number)", "stat_fire_delay": "one number",
    "stat_food": "food eaten, food carried   (commas; no longer used)",
    "stat_cost": "turns, cost, upkeep, weapon upgrade, armour upgrade, custom battle cost[, custom units, extra price]"
                 "   (commas; the last two Medieval II)",
    "stat_stl": "men   (Medieval II; one number)",
    "armour_ug_levels": "level, level, ...   (commas; Medieval II)",
    "armour_ug_models": "model, model, ...   (commas, as many as the levels; Medieval II)",
    "info_pic_dir": "folder   (Medieval II)", "card_pic_dir": "folder   (Medieval II)",
    "stat_pri_ex": "attack vs mounted, defence vs mounted, armour piercing   (only a note - not read)",
    "stat_armour_ex": "armour, upg1, upg2, upg3, defence, shield melee, shield missile, sound   (only a note - not "
                      "read)",
    "unit_info": "melee attack, missile attack, defence   (only a note - not read)",
}
FORMS["stat_sec_ex"] = FORMS["stat_ter_ex"] = FORMS["stat_pri_ex"]

# lines only written as notes (comment lines) in Medieval II's own file: the game reads none of them
NOTE_ONLY = ("stat_pri_ex", "stat_sec_ex", "stat_ter_ex", "stat_armour_ex", "unit_info")
NOTE = ("Medieval II: only a note in the game's own file (a comment line, ';%s ...'); the game does not read this "
        "line - written into a unit it breaks the block")


def _word(w, key):
    w = (w.split() or [""])[0]                 # general_unit_upgrade "event": the word, then what it names
    if w.startswith("spear_bonus_"):
        return "attack bonus against cavalry: +%s" % w[len("spear_bonus_"):]
    if w.startswith("hp_damage_"):
        return "each hit takes %s hit points (REX / M2EX)" % w[len("hp_damage_"):]
    if w.startswith("hardy_") and w[len("hardy_"):].isdigit():
        return "tires more slowly: %s fatigue points taken off per update (REX / M2EX)" % w[len("hardy_"):]
    if w in WORDS:
        return WORDS[w]
    for word, line, effect in unitattrs.ATTRIBUTES:
        if word == w and (line == key or key == "attributes"):
            return effect
    for word, _line, effect in unitattrs.ATTRIBUTES:
        if word == w:
            return effect
    return None


def _parts(value):
    return [x.strip() for x in value.split(",")]


def _words(value):
    """A word list's words: by commas or spaces (Rome's own file has 'prec, thrown ap'); a quoted name stays with
    the word before it (general_unit_upgrade "event")."""
    out = []
    for t in re.findall(r'"[^"]*"|[^\s,]+', value):
        if t.startswith('"') and out:
            out[-1] += " " + t
        else:
            out.append(t)
    return out


def explain(key, value, medieval2=False):
    """The line's values one by one, each with what it means: a text for the '?' (None when we know nothing of
    the line)."""
    key = key.strip()
    value = value.split(";")[0].strip()
    vals = _parts(value) if value else []
    out = []
    if key in ("stat_pri", "stat_sec", "stat_ter"):
        if [v.lower() for v in vals] == ["no"] or not vals:
            return "%s: no weapon." % key
        names = list(WEAPON)
        if len(vals) == len(WEAPON) + 1:              # Medieval II: the fire effect before the attack delay
            names.insert(9, EFFECT)
        head = {"stat_pri": "The primary weapon (a missile weapon is always the primary)",
                "stat_sec": "The secondary weapon: the melee arm of a missile unit, a side arm, or the attack of "
                            "its animals / vehicle",
                "stat_ter": "Medieval II: a third weapon"}[key]
        out.append(head + ", from left to right:")
        for i, v in enumerate(vals):
            n, m = names[i] if i < len(names) else ("?", "a value the game's notes do not name")
            out.append("%d. %s = %s - %s" % (i + 1, n, v, m))
        return "\n".join(out)
    if key in NOTE_ONLY:
        out.append(NOTE % key)
        names = FIXED[key]
        for i, v in enumerate(vals):
            n, m = names[i] if i < len(names) else ("?", "")
            out.append("%d. %s = %s - %s" % (i + 1, n, v, m))
        return "\n".join(out)
    if key in FIXED:
        names = FIXED[key]
        out.append("%s, from left to right:" % key)
        for i, v in enumerate(vals):
            if v in unitattrs.NOT_ON.get(key, ()) and i >= len(names):   # REX's header's place: wrong (tested)
                out.append("- %s: does NOTHING on this line - the engine reads it only on 'attributes' (move it "
                           "there): %s" % (v, _word(v, "attributes")))
                continue
            if key == "stat_mental" and i >= len(names):          # then words: lock_morale, REX / M2EX's own
                out.append("- %s: %s" % (v, _word(v, key) or "a word the game's notes do not explain"))
                continue
            n, m = names[i] if i < len(names) else ("?", "a value the game's notes do not name")
            out.append("%d. %s = %s - %s" % (i + 1, n, v, m))
        if key == "stat_cost" and not medieval2 and len(vals) <= 6:
            out.append("(Medieval II adds two more: custom battle units, the extra price)")
        return "\n".join(out)
    if key.startswith("era"):
        m = re.match(r"(\d+)\s+(.*)$", value)
        num, facs = (m.group(1), m.group(2)) if m else (key[3:].strip() or "?", value)
        return "%s: Medieval II - the factions that use it in multiplayer era %s (0, 1 or 2; the number, a space, " \
               "then the factions with commas):\n%s" % (key, num, ", ".join(_parts(facs)))
    if key in LISTS or key.startswith("era"):
        out.append("%s: %s." % (key, LISTS.get(key, "Medieval II: the factions that use it in this multiplayer "
                                                  "era")))
        if key in ("attributes", "stat_pri_attr", "stat_sec_attr", "stat_ter_attr"):
            for v in _words(value):
                if not v:
                    continue
                m = _word(v, key)
                out.append("- %s: %s" % (v, m or "a word the game's notes do not explain"))
        return "\n".join(out)
    if key in ONE:
        return "%s = %s - %s" % (key, value or "(empty)", ONE[key])
    if key in unitattrs.ENGINE_KEYS:
        return "%s = %s - %s" % (key, value, unitattrs.ENGINE_KEYS[key][1])
    return None
