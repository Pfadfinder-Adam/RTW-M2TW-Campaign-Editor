"""What every value of a unit's line in export_descr_unit.txt means, both games, in plain words - from the notes
the games write at the top of that file (Rome's and Medieval II's), the few they leave out marked so. The Unit
editor's 'Every line of the block' window shows it on the '?' beside each line, for the value typed there now."""

import re

from . import unitattrs

# one weapon: stat_pri / stat_sec (/ stat_ter, Medieval II)
WEAPON = [
    ("attack", "how hard each man hits"),
    ("charge bonus", "added to the attack when it charges"),
    ("missile", "the missile it fires (descr_projectile.txt); no = not a missile weapon"),
    ("range", "how far the missile flies, in metres"),
    ("ammunition", "missiles each man carries"),
    ("weapon type", "melee, thrown, missile or siege_missile"),
    ("tech type", "Rome: simple, other, blade, archery or siege; Medieval II: melee_simple, melee_blade, "
                  "missile_mechanical, missile_gunpowder, artillery_mechanical or artillery_gunpowder"),
    ("damage type", "piercing, blunt, slashing or fire (the game's own notes: likely no longer used)"),
    ("sound", "the sound when it hits: none, knife, mace, axe, sword or spear"),
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
                ("radius?", "only Barbarian Invasion's giant berserkers have it - the game's notes do not name it; "
                            "most likely the man's collision radius, metres"),
                ("height?", "with the one before - the game's notes do not name it; most likely the man's height, "
                            "metres")],
    "formation": [("close: side", "space between men side to side in close formation, metres"),
                  ("close: front", "space front to back in close formation, metres"),
                  ("loose: side", "space side to side in loose formation, metres"),
                  ("loose: front", "space front to back in loose formation, metres"),
                  ("ranks", "the default number of ranks"),
                  ("formation", "a formation it can take: square, horde, phalanx, testudo, wedge (Medieval II also "
                                "schiltrom, shield_wall)"),
                  ("second formation", "a second one (one or two may be named)")],
    "stat_health": [("man", "hit points of a man"),
                    ("animal", "hit points of the mount or attached animal (ridden horses and camels have none of "
                               "their own)")],
    "stat_pri_armour": [("armour", "the man's armour"),
                        ("defence skill", "his skill at parrying (not used when shot at)"),
                        ("shield", "the shield (only against attacks from the front or left)"),
                        ("sound", "the sound when he is hit: flesh, leather or metal")],
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
                    ("discipline", "normal, low, disciplined or impetuous (charges without orders); how it takes "
                                   "morale shocks"),
                    ("training", "untrained, trained or highly_trained: how tidy its formation is")],
    "stat_food": [("food", "no longer used (the game's own notes)"), ("food", "no longer used")],
    "stat_cost": [("turns", "turns to recruit it"), ("cost", "the price to recruit"), ("upkeep", "upkeep a turn"),
                  ("weapon upgrade", "the price of a weapon upgrade"),
                  ("armour upgrade", "the price of an armour upgrade"),
                  ("custom battle cost", "its price in custom battles"),
                  ("custom battle: units", "Medieval II: how many of it a custom battle army takes before the "
                                           "price rises (not named in the game's notes; modders' reading)"),
                  ("custom battle: extra price", "Medieval II: what each one after those costs more (not named in "
                                                 "the game's notes; modders' reading)")],
    "unit_info": [("melee attack", "shown on the unit's info panel"), ("missile attack", "shown on the info panel"),
                  ("defence", "shown on the info panel")],
}
for _k in ("stat_pri_ex", "stat_sec_ex", "stat_ter_ex"):
    FIXED[_k] = EX

ONE = {
    "type": "the unit's inner name (not always the name on screen)",
    "dictionary": "the key of its name and descriptions in the text files",
    "category": "infantry, cavalry, siege, handler, ship or non_combatant",
    "class": "light, heavy, missile or spearmen - with the category: its place in formations and the AI's use",
    "voice_type": "the kind of voice the unit speaks with",
    "accent": "Medieval II: the accent of its voice",
    "banner": "Medieval II: a banner it carries (faction, holy...)",
    "officer": "an officer's model (up to three officer lines)",
    "ship": "the ship it sails, if it is one",
    "engine": "its siege engine",
    "mounted_engine": "Medieval II: an engine it rides, like a war wagon",
    "animal": "animals it brings that are not ridden",
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
    "stat_pri_attr": "the primary weapon's abilities - words, any number of them; no = none",
    "stat_sec_attr": "the secondary weapon's abilities - words; no = none",
    "stat_ter_attr": "the third weapon's abilities - words; no = none",
    "ownership": "the factions and cultures that may have it",
    "armour_ug_levels": "Medieval II: the armourer's level each armour upgrade needs (the first = the base)",
    "armour_ug_models": "Medieval II: the model for each armour level, in the same order",
    "mount_effect": "up to three bonuses against units riding a kind of mount: 'elephant +3', 'horse -2'",
}

# the words the games' own notes explain (REX / M2EX words: unitattrs)
WORDS = {
    "sea_faring": "can board ships", "can_swim": "can swim across rivers (Medieval II)",
    "hide_forest": "can hide in forest", "hide_improved_forest": "can hide in forest, better",
    "hide_long_grass": "can hide in long grass", "hide_anywhere": "can hide anywhere",
    "can_sap": "can dig tunnels under walls", "frighten_foot": "frightens infantry nearby",
    "frighten_mounted": "frightens cavalry nearby",
    "can_run_amok": "may run out of control when the riders lose control of the animals",
    "general_unit": "can be a named character's bodyguard", "cantabrian_circle": "has the Cantabrian circle ability",
    "no_custom": "cannot be picked in custom battles", "command": "carries an eagle: a bonus to units nearby",
    "mercenary_unit": "a mercenary, open to every faction", "is_peasant": "a peasant unit (the game's notes: unknown)",
    "druid": "can chant to raise morale", "power_charge": "a stronger charge (the game's notes: unknown)",
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
    "hardy": "tires slowly", "very_hardy": "tires very slowly", "can_withdraw": "can withdraw from a battle",
    "can_formed_charge": "charges in formation", "can_horde": "can become a horde",
    "start_not_skirmishing": "starts a battle with skirmish mode off", "warcry_": "",
    "knight": "Medieval II: counts as knights", "peasant": "Medieval II: counts as peasants",
    "gunpowder_unit": "Medieval II: a gunpowder unit", "gunmen": "Medieval II: handgunners",
    "guncavalry": "Medieval II: mounted gunmen", "crossbow": "Medieval II: crossbowmen",
    "artillery": "Medieval II: an artillery crew", "cannon": "Medieval II: a cannon", "mortar": "Medieval II: a mortar",
    "rocket": "Medieval II: rockets", "explode": "Medieval II: its guns may explode",
    "fire_by_rank": "Medieval II: fires rank by rank", "stakes": "Medieval II: can plant stakes",
    "pike": "Medieval II: pikemen", "berserker": "Medieval II: can go berserk",
    "standard": "Medieval II: carries a standard", "wagon_fort": "Medieval II: can form a wagon fort",
    "incendiary": "Medieval II: sets things on fire",
    "general_unit_upgrade": "Medieval II: the bodyguard to use after the event named next to it",
}
WORDS.pop("warcry_")


def _word(w, key):
    w = (w.split() or [""])[0]                 # general_unit_upgrade "event": the word, then what it names
    if w.startswith("spear_bonus_"):
        return "attack bonus against cavalry: +%s" % w[len("spear_bonus_"):]
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
    if key in FIXED:
        names = FIXED[key]
        out.append("%s, from left to right:" % key)
        for i, v in enumerate(vals):
            if key == "stat_mental" and i >= len(names):          # then words: lock_morale, REX / M2EX's own
                out.append("- %s: %s" % (v, _word(v, key) or "a word the game's notes do not explain"))
                continue
            n, m = names[i] if i < len(names) else ("?", "a value the game's notes do not name")
            out.append("%d. %s = %s - %s" % (i + 1, n, v, m))
        if key == "stat_cost" and not medieval2 and len(vals) <= 6:
            out.append("(Medieval II adds two more: custom battle units, the extra price)")
        return "\n".join(out)
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
