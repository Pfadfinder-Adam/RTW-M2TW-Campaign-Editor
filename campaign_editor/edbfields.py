"""What every line of a building chain in export_descr_buildings.txt means, both games, in plain words (the
Building editor's 'Every line of the block' window shows it on the '?' beside each line, as edufields does for
units). A line's words are split into what each one is, for the value typed there now (report #316: 'in the
buildings the ? hints are missing')."""

import re

SIZES = "village, town, large_town, city, large_city or huge_city"

# key -> (what the line does, [names of the values after the key, left to right] or None)
LINES = {
    "building": ("the chain's name - the name the other files use for it", None),
    "levels": ("the chain's levels, lowest first; each gets a block of its own below", None),
    "capability": ("what a finished level gives the town - the lines inside", None),
    "faction_capability": ("what a finished level gives the WHOLE faction (Medieval II) - the lines inside", None),
    "construction": ("how long it takes to build", ["turns"]),
    "cost": ("what it costs to build", ["money"]),
    "settlement_min": ("the smallest town that may build it (%s)" % SIZES, ["size"]),
    "upgrades": ("the levels it can be upgraded to next - one per line inside", None),
    "material": ("Medieval II: what it is built of - wooden or stone (cost bonuses and repair use it)", ["material"]),
    "plugins": ("buildings of the same chain that plug into it (rarely used)", None),
    "convert_to": ("Medieval II: the level it turns into when the town is switched between city and castle",
                   ["level"]),
    "wall_level": ("the walls the town gets: 0 palisade, 1 wooden wall, 2 stone, 3 large stone, 4 epic",
                   ["level"]),
    "tower_level": ("arrow towers on the walls: 0 none, 1 arrows, 2 and up stronger (ballistae, cannon in "
                    "Medieval II)", ["level"]),
    "gate_strength": ("how strong the gates are: 0 wooden, 1 reinforced, 2 iron-bound", ["level"]),
    "gate_defences": ("what the gate shoots: 0 none, 1 arrows, 2 boiling oil", ["level"]),
    "road_level": ("the roads of the region: 0 dirt, 1 paved, 2 highways", ["level"]),
    "farming_level": ("farm improvements: more food, faster growth, more farm income", ["level"]),
    "mine_resource": ("mines: income from the region's mineable resources (gold, silver, iron...)", ["level"]),
    "trade_fleet": ("merchant fleets: sea trade routes from the port", ["fleets"]),
    "trade_base_income_bonus": ("more trade income", ["'bonus'", "amount"]),
    "trade_level_bonus": ("Medieval II: more trade (counts as trade levels)", ["'bonus'", "amount"]),
    "happiness_bonus": ("happier people: public order up (in steps of 5 %)", ["'bonus'", "amount"]),
    "law_bonus": ("more law: public order up, corruption down (in steps of 5 %)", ["'bonus'", "amount"]),
    "population_growth_bonus": ("faster growth (in steps of 0.5 %)", ["'bonus'", "amount"]),
    "population_health_bonus": ("healthier town: public order and growth up, less plague", ["'bonus'", "amount"]),
    "population_loyalty_bonus": ("more loyal people (in steps of 5 %)", ["'bonus'", "amount"]),
    "recruits_exp_bonus": ("units trained here start with more experience (chevrons)", ["'bonus'", "amount"]),
    "recruits_morale_bonus": ("units trained here have better morale", ["'bonus'", "amount"]),
    "stage_games": ("the governor may hold games here (Rome): public order, at a cost", ["level"]),
    "stage_races": ("the governor may hold chariot races here: public order, at a cost", ["level"]),
    "upgrade_bodyguard": ("generals' bodyguards here get better (Rome)", ["level"]),
    "weapon_simple": ("units here get better simple weapons (spears, clubs) - the level of the upgrade", ["level"]),
    "weapon_bladed": ("units here get better blades - the level of the upgrade", ["level"]),
    "weapon_missile": ("units here get better missile weapons - the level of the upgrade", ["level"]),
    "weapon_siege": ("siege engines here get better - the level of the upgrade", ["level"]),
    "weapon_other": ("other weapons upgraded here - the level of the upgrade", ["level"]),
    "weapon_melee_simple": ("Medieval II: better simple melee weapons - the level", ["level"]),
    "weapon_melee_blade": ("Medieval II: better blades - the level", ["level"]),
    "weapon_missile_mechanical": ("Medieval II: better bows / crossbows - the level", ["level"]),
    "weapon_missile_gunpowder": ("Medieval II: better handguns - the level", ["level"]),
    "weapon_artillery_mechanical": ("Medieval II: better catapults / trebuchets - the level", ["level"]),
    "weapon_artillery_gunpowder": ("Medieval II: better cannon - the level", ["level"]),
    "weapon_naval_gunpowder": ("Medieval II: better ship guns - the level", ["level"]),
    "weapon_projectile": ("Medieval II: better projectiles - the level", ["level"]),
    "armour": ("units here get better armour - the level of the upgrade", ["level"]),
    "recruitment_slots": ("Medieval II: units the town can train at once", ["slots"]),
    "free_upkeep": ("Medieval II: units with free_upkeep_unit stationed here cost no upkeep", ["'bunch'",
                                                                                               "units"]),
    "agent_limit": ("Medieval II: how many of this agent the faction may have more", ["agent", "more"]),
    "religion": ("spreads a religion in the region", ["religion", "strength"]),
    "religion_level": ("Medieval II: spreads the faction's religion", ["strength"]),
    "amplify_religion_level": ("Medieval II: makes the religion buildings stronger", ["amount"]),
    "pope_approval": ("Medieval II: the Pope likes the faction more", ["amount"]),
    "pope_disapproval": ("Medieval II: the Pope likes the faction less", ["amount"]),
    "construction_cost_bonus_stone": ("Medieval II: stone buildings cost less (%)", ["percent"]),
    "construction_cost_bonus_wooden": ("Medieval II: wooden buildings cost less (%)", ["percent"]),
    "construction_cost_bonus_military": ("Medieval II: military buildings cost less (%)", ["percent"]),
    "construction_cost_bonus_religious": ("Medieval II: religious buildings cost less (%)", ["percent"]),
    "construction_cost_bonus_defensive": ("Medieval II: walls and towers cost less (%)", ["percent"]),
    "construction_cost_bonus_other": ("Medieval II: other buildings cost less (%)", ["percent"]),
    "construction_time_bonus_stone": ("Medieval II: stone buildings build faster (%)", ["percent"]),
    "construction_time_bonus_wooden": ("Medieval II: wooden buildings build faster (%)", ["percent"]),
    "recruitment_cost_bonus_naval": ("Medieval II: ships cost less to train (%)", ["percent"]),
    "retrain_cost_bonus": ("Medieval II: retraining costs less (%)", ["percent"]),
    "gun_bonus": ("Medieval II: gunpowder units get more experience / bonus", ["amount"]),
    "cavalry_bonus": ("Medieval II: cavalry trained here get a bonus", ["amount"]),
    "heavy_cavalry_bonus": ("Medieval II: heavy cavalry trained here get a bonus", ["amount"]),
    "archer_bonus": ("Medieval II: archers trained here get a bonus", ["amount"]),
    "navy_bonus": ("Medieval II: ships trained here get a bonus", ["amount"]),
    "income_bonus": ("more income", ["'bonus'", "amount"]),
    "taxable_income_bonus": ("more tax income", ["'bonus'", "amount"]),
}
REQUIRES = ("the condition: the line works only when it holds - 'factions { ... }' lists the factions or "
            "cultures, 'and' / 'or' / 'not' join more conditions (event_counter, hidden_resource, building_present_"
            "min_level...)")


def _cut(value):
    """(the value before 'requires', the condition or '')."""
    m = re.search(r"\brequires\b", value)
    return (value[:m.start()].strip(), value[m.start():].strip()) if m else (value.strip(), "")


def explain(key, value, medieval2=False):
    """What a line of a building chain does and what each of its values is: a text for the '?' (None when the line
    is not known)."""
    key = key.strip()
    value = value.split(";")[0].strip()
    head, cond = _cut(value)
    if key == "recruit" or key == "recruit_pool":
        m = re.match(r'"([^"]+)"\s*(.*)$', head)
        unit, rest = (m.group(1), m.group(2).split()) if m else (head, [])
        out = ["%s: a unit this level lets the town train." % key, "1. unit = %s - its type in "
               "export_descr_unit.txt" % unit]
        names = (["units at the start (the pool)", "units added a turn", "most units the pool holds",
                  "experience the units start with"] if key == "recruit_pool" else ["experience it starts with"])
        for i, v in enumerate(rest):
            out.append("%d. %s = %s" % (i + 2, names[i] if i < len(names) else "?", v))
        if cond:
            out.append("then: %s - %s" % (cond, REQUIRES))
        return "\n".join(out)
    if key == "agent":
        parts = head.split()
        out = ["agent: an agent this level lets the town train."]
        names = ["agent (spy, assassin, diplomat, merchant, priest...)", "experience it starts with"]
        for i, v in enumerate(parts):
            out.append("%d. %s = %s" % (i + 1, names[i] if i < len(names) else "?", v))
        if cond:
            out.append("then: %s - %s" % (cond, REQUIRES))
        return "\n".join(out)
    if key not in LINES:
        if value.startswith("requires"):             # a level's own line: its name, then who may build it
            return "%s: a level of the chain. %s" % (key, REQUIRES.capitalize())
        return None
    what, names = LINES[key]
    out = ["%s: %s." % (key, what)]
    if names:
        for i, v in enumerate(head.split()):
            n = names[i] if i < len(names) else "?"
            if n.startswith("'"):                      # a fixed word the game wants there ('bonus', 'bunch')
                out.append("%d. %s - this word itself" % (i + 1, v))
            else:
                out.append("%d. %s = %s" % (i + 1, n, v))
    elif head:
        out.append("value: %s" % head)
    if cond:
        out.append("then: %s - %s" % (cond, REQUIRES))
    return "\n".join(out)
