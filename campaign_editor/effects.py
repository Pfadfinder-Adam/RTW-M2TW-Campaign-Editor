"""What a building level does and needs, in plain words - the lines of export_descr_buildings.txt as a player would
read them in the game's building panel (both games). Used where a building is picked to copy or to bring from
another mod, so the modder sees the bonuses and not the code.

A bonus point is what the game shows as 5 % for public order (happiness, law), 0.5 % for population growth and
health; the rest is said as the file gives it. A line this module does not know is shown as it stands."""

from .textio import strip_comment

# key -> (plain words, how the number reads); %s = the number
WORDS = {
    "happiness_bonus": ("public order from happiness +%s%%", 5),
    "law_bonus": ("public order from law +%s%%", 5),
    "population_growth_bonus": ("population growth +%s%%", 0.5),
    "population_health_bonus": ("health (population growth) +%s%%", 0.5),
    "population_loyalty_bonus": ("loyalty +%s", 1),
    "trade_base_income_bonus": ("trade income +%s (base)", 1),
    "trade_level_bonus": ("trade level +%s", 1),
    "trade_fleet": ("trade fleets +%s", 1),
    "taxable_income_bonus": ("tax income +%s%%", 1),
    "farming_level": ("farming level +%s", 1),
    "farming_level_bonus": ("farming level +%s", 1),
    "mine_resource": ("mining income level %s", 1),
    "road_level": ("roads level %s (0 dirt, 1 paved, 2 highways)", 1),
    "wall_level": ("walls level %s", 1),
    "tower_level": ("towers level %s", 1),
    "gate_strength": ("gate strength %s", 1),
    "gate_defences": ("gate defences %s", 1),
    "armour": ("armour upgrade +%s for units trained here", 1),
    "weapon_simple": ("weapon upgrade +%s (spears, simple weapons)", 1),
    "weapon_bladed": ("weapon upgrade +%s (swords, bladed weapons)", 1),
    "weapon_missile": ("weapon upgrade +%s (missile units)", 1),
    "weapon_siege": ("weapon upgrade +%s (siege engines)", 1),
    "weapon_gunpowder": ("weapon upgrade +%s (gunpowder)", 1),
    "weapon_artillery_mechanical": ("weapon upgrade +%s (mechanical artillery)", 1),
    "weapon_artillery_gunpowder": ("weapon upgrade +%s (gunpowder artillery)", 1),
    "weapon_naval_gunpowder": ("weapon upgrade +%s (naval guns)", 1),
    "recruits_morale_bonus": ("morale +%s for units trained here", 1),
    "recruits_exp_bonus": ("experience +%s for units trained here", 1),
    "upgrade_bodyguard": ("better general's bodyguard", None),
    "free_upkeep": ("%s unit(s) kept without upkeep", 1),
    "stage_games": ("games (public order) level %s", 1),
    "stage_races": ("races (public order) level %s", 1),
    "construction_cost_bonus_military": ("military buildings %s%% cheaper", 1),
    "construction_cost_bonus_religious": ("temples %s%% cheaper", 1),
    "construction_cost_bonus_defensive": ("walls %s%% cheaper", 1),
    "construction_cost_bonus_other": ("other buildings %s%% cheaper", 1),
    "construction_cost_bonus_wooden": ("wooden buildings %s%% cheaper", 1),
    "construction_cost_bonus_stone": ("stone buildings %s%% cheaper", 1),
    "construction_time_bonus_military": ("military buildings %s%% faster", 1),
    "construction_time_bonus_religious": ("temples %s%% faster", 1),
    "construction_time_bonus_defensive": ("walls %s%% faster", 1),
    "construction_time_bonus_other": ("other buildings %s%% faster", 1),
    "pope_approval": ("papal standing +%s", 1),
    "religious_order": ("religious orders %s", 1),
    "amplify_religion_level": ("religion spreads stronger (+%s)", 1),
    "heretic_level": ("heresy +%s", 1),
    "retrain_cost_bonus": ("retraining %s%% cheaper", 1),
    "income_bonus": ("income +%s", 1),
    "recruitment_slots": ("%s more units trained at a time", 1),
    "recruitment_cost_bonus_naval": ("ships %s%% cheaper", 1),
    "pope_disapproval": ("papal standing -%s", 1),
    "religion_level": ("religion spreads (strength %s)", 1),
    "gun_bonus": ("gunpowder units +%s experience", 1),
    "archer_bonus": ("archers +%s experience", 1),
    "cavalry_bonus": ("cavalry +%s experience", 1),
    "heavy_cavalry_bonus": ("heavy cavalry +%s experience", 1),
    "navy_bonus": ("ships +%s experience", 1),
    "weapon_melee_blade": ("weapon upgrade +%s (bladed melee)", 1),
    "weapon_missile_gunpowder": ("weapon upgrade +%s (gunpowder missiles)", 1),
    "weapon_projectile": ("weapon upgrade +%s (projectiles)", 1),
}


def _number(rest):
    """The number of 'bonus 3' / '3' / 'bonus 3 requires ...'."""
    for w in rest.replace(",", " ").split():
        try:
            return float(w)
        except ValueError:
            continue
    return None


def _requires(rest):
    i = rest.find("requires")
    return rest[i + len("requires"):].strip() if i >= 0 else ""


def line_words(text):
    """One capability line in plain words, or None for a structure line ({, }, capability...)."""
    body = strip_comment(text).strip()
    if not body or body in ("{", "}") or body.split()[0] in ("capability", "upgrades", "construction", "cost",
                                                              "settlement_min", "faction_capability"):
        return None
    t = body.split()
    key, rest = t[0], body[len(t[0]):].strip()
    need = _requires(rest)
    tail = ("  (for %s)" % requires_words("x requires " + need)) if need else ""
    if key in ("recruit", "recruit_pool", "retrain", "retrain_pool") and '"' in rest:
        unit = rest.split('"')[1]
        nums = rest.split('"')[2].split("requires")[0].split()
        if key == "recruit_pool" and len(nums) >= 3:
            how = "pool: %s at start, +%s a turn, up to %s" % tuple(nums[:3])
        else:
            how = "experience %s" % nums[0] if nums else ""
        verb = "trains" if key.startswith("recruit") else "retrains only"
        return "%s %s%s%s" % (verb, unit, " (%s)" % how if how else "", tail)
    if key == "agent" and len(t) > 1:
        return "trains agent: %s%s" % (t[1].rstrip(","), tail)
    if key == "agent_limit" and len(t) > 2:
        return "up to %s more %s agent(s)%s" % (t[2], t[1].rstrip(","), tail)
    if key == "religious_belief" and len(t) > 2:
        return "spreads %s (strength %s)%s" % (t[1], t[2], tail)
    if key in WORDS:
        words, per = WORDS[key]
        if per is None:
            return words + tail
        n = _number(rest.split("requires")[0])
        if n is None:
            return "%s: %s" % (key, rest)
        v = n * per
        return (words % (("%g" % v))) + tail
    return "%s %s" % (key, rest)


def level_words(lines):
    """[str]: what a level does, from the lines of its capability block."""
    out = []
    for l in lines:
        w = line_words(l)
        if w:
            out.append(w)
    return out


def requires_words(head):
    """'who may build it, and what it needs' from a level's head line ('<level> requires factions {...} and ...')."""
    body = strip_comment(head).strip()
    i = body.find("requires")
    if i < 0:
        return "anyone"
    rest = body[i + len("requires"):].strip()
    import re
    m = re.search(r"factions\s*\{([^}]*)\}", rest)
    who = ", ".join(x.strip() for x in m.group(1).split(",") if x.strip()) if m else "anyone"
    more = re.sub(r"factions\s*\{[^}]*\}", "", rest).strip()
    more = re.sub(r"^\s*and\s+", "", more)
    return who + ("; needs " + more if more else "")
