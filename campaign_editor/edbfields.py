"""What every line of a building chain in export_descr_buildings.txt means, both games, in plain words (the
Building editor's 'Every line of the block' window shows it on the '?' beside each line, as edufields does for
units). A line's words are split into what each one is, for the value typed there now (report #316: 'in the
buildings the ? hints are missing')."""

import re

SIZES = "village, town, large_town, city, large_city or huge_city"
CASTLES = "moot_and_bailey, wooden_castle, castle, fortress or citadel"
RELIGIONS_M2 = "catholic, orthodox, islam, pagan or heretic"
RELIGIONS_BI = "pagan, christianity or zoroastrian"

# key -> (what the line does, [names of the values after the key, left to right] or None)
LINES = {
    "building": ("the chain's name - the name the other files use for it", None),
    "levels": ("the chain's levels, lowest first; each gets a block of its own below", None),
    "capability": ("what a finished level gives the town - the lines inside", None),
    "faction_capability": ("what a finished level gives the WHOLE faction (Medieval II) - the lines inside", None),
    "construction": ("how long it takes to build", ["turns"]),
    "cost": ("what it costs to build", ["money"]),
    "settlement_min": ("the smallest town that may build it (%s; Medieval II castles: %s)" % (SIZES, CASTLES),
                       ["size"]),
    "upgrades": ("the levels it can be upgraded to next - one per line inside", None),
    "material": ("Medieval II: what it is built of - wooden or stone (cost bonuses and repair use it)", ["material"]),
    "plugins": ("buildings of the same chain that plug into it (rarely used)", None),
    "convert_to": ("Medieval II: on the chain (before 'levels') - the chain of the other kind of town it becomes "
                   "when the town is switched between city and castle; inside a level - the number of the matching "
                   "level in that chain (0 = the first)", ["chain or level number"]),
    "hidden_resources": ("the hidden resources the conditions may test ('requires hidden_resource X') - names with "
                         "spaces between, at the top of the file; regions get them in descr_regions.txt", None),
    "wall_level": ("the walls the town gets: 0 palisade, 1 wooden wall, 2 stone, 3 large stone, 4 epic",
                   ["level"]),
    "tower_level": ("arrow towers on the walls: 0 none, 1 arrows, 2 and up stronger (ballistae, cannon in "
                    "Medieval II)", ["level"]),
    "gate_strength": ("how strong the gates are: 0 wooden, 1 reinforced, 2 iron-bound", ["level"]),
    "gate_defences": ("what the gate shoots: 0 none, 1 arrows, 2 boiling oil", ["level"]),
    "road_level": ("the roads of the region: 0 dirt, 1 paved, 2 highways", ["level"]),
    "farming_level": ("farm improvements: more food, faster growth, more farm income", ["level"]),
    "fire_risk": ("the risk of fire in the town", ["level"]),
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
    "weapon_simple": ("Rome: the weapon level for units whose weapon's tech is simple (spears, clubs) - a unit is "
                      "trained only where the level of its weapon's tech is set (0 and up)", ["level"]),
    "weapon_bladed": ("Rome: the weapon level for units whose weapon's tech is blade - a unit is trained only where "
                      "the level of its weapon's tech is set", ["level"]),
    "weapon_missile": ("Rome: the weapon level for units whose weapon's tech is archery - a unit is trained only "
                       "where the level of its weapon's tech is set", ["level"]),
    "weapon_siege": ("Rome: the weapon level for siege engines (tech siege)", ["level"]),
    "weapon_other": ("Rome: the weapon level for units whose weapon's tech is other", ["level"]),
    "weapon_melee_simple": ("Medieval II: better simple melee weapons - the level", ["level"]),
    "weapon_melee_blade": ("Medieval II: better blades - the level", ["level"]),
    "weapon_missile_mechanical": ("Medieval II: better bows / crossbows - the level", ["level"]),
    "weapon_missile_gunpowder": ("Medieval II: better handguns - the level", ["level"]),
    "weapon_artillery_mechanical": ("Medieval II: better catapults / trebuchets - the level", ["level"]),
    "weapon_artillery_gunpowder": ("Medieval II: better cannon - the level", ["level"]),
    "weapon_naval_gunpowder": ("Medieval II: better ship guns - the level", ["level"]),
    "weapon_projectile": ("Medieval II: better projectiles - the level", ["level"]),
    "armour": ("units here get better armour - the level of the upgrade (Medieval II: the levels a unit names in "
               "armour_ug_levels)", ["level"]),
    "recruitment_slots": ("Medieval II: units the town can train at once", ["slots"]),
    "free_upkeep": ("Medieval II: how many units with the free_upkeep_unit attribute this town keeps for free",
                    ["units"]),
    "agent_limit": ("Medieval II: how many of this agent the faction may have more", ["agent", "more"]),
    "religion": ("Medieval II, on the chain: the religion this temple chain belongs to (%s)" % RELIGIONS_M2,
                 ["religion"]),
    "religious_belief": ("Barbarian Invasion: spreads a religion in the region - %s, then the strength"
                         % RELIGIONS_BI, ["religion", "strength"]),
    "religion_level": ("Medieval II: converts the region to the faction's religion - the strength", ["strength"]),
    "amplify_religion_level": ("Medieval II: multiplies the town's religion spread (1.5 = half as much again)",
                               ["multiplier"]),
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
    "construction_time_bonus_military": ("Medieval II: military buildings build faster (%)", ["percent"]),
    "construction_time_bonus_religious": ("Medieval II: religious buildings build faster (%)", ["percent"]),
    "construction_time_bonus_defensive": ("Medieval II: walls and towers build faster (%)", ["percent"]),
    "construction_time_bonus_other": ("Medieval II: other buildings build faster (%)", ["percent"]),
    "recruitment_cost_bonus_naval": ("Medieval II: ships cost less to train (vanilla 1 or 2)", ["amount"]),
    "retrain_cost_bonus": ("Medieval II: retraining costs less (vanilla 1 or 2)", ["amount"]),
    "gun_bonus": ("Medieval II: gunpowder units get more experience / bonus", ["amount"]),
    "cavalry_bonus": ("Medieval II: cavalry trained here get a bonus", ["amount"]),
    "heavy_cavalry_bonus": ("Medieval II: heavy cavalry trained here get a bonus", ["amount"]),
    "archer_bonus": ("Medieval II: archers trained here get a bonus", ["amount"]),
    "navy_bonus": ("Medieval II: ships trained here get a bonus", ["amount"]),
    "income_bonus": ("more income", ["'bonus'", "amount"]),
    "taxable_income_bonus": ("more tax income", ["'bonus'", "amount"]),
}
# the lines of a chain / a level that are not capabilities (every capability may be 'N' or 'bonus N' - the engine
# reads both on every one: N alone a level, the highest among the town's buildings counts; 'bonus N' added on top of
# the others, may be negative - the 2026-10-21 audit, the engine source's building reader)
NOT_CAPS = {"building", "levels", "capability", "faction_capability", "construction", "cost", "settlement_min",
            "upgrades", "material", "plugins", "convert_to", "hidden_resources", "religion", "religious_belief",
            "agent_limit"}
LEVEL = "a level: the highest among the town's buildings counts"
BONUS = ("this word itself: the number after it is ADDED on top of the other buildings' (it may be negative; "
         "without the word the number is a level, the highest counts)")

REQUIRES = ("the condition: the line works only when it holds - 'factions { ... }' lists the factions or "
            "cultures, 'and' / 'or' / 'not' join more conditions (event_counter, hidden_resource, building_present_"
            "min_level...)")


def _cut(value):
    """(the value before 'requires', the condition or '')."""
    m = re.search(r"\brequires\b", value)
    return (value[:m.start()].strip(), value[m.start():].strip()) if m else (value.strip(), "")


def _numbers(out, parts, names, at):
    """The numbers of a capability: 'N' (a level) or 'bonus N' (added) - the engine takes both on every one."""
    i = 0
    for v in parts:
        if v == "bonus":
            out.append("%d. bonus - %s" % (at, BONUS))
        else:
            n = names[min(i, len(names) - 1)] if names else "?"
            i += 1
            out.append("%d. %s = %s%s" % (at, n, v, (" (" + LEVEL + ")") if len(parts) == 1 and n in (
                "level", "amount", "percent", "strength", "units", "slots", "fleets", "money") else ""))
        at += 1


# the words a line's first value may be, for the right click
WORDS = {"settlement_min": SIZES.replace(" or ", ", ").split(", ") + CASTLES.replace(" or ", ", ").split(", "),
         "material": ["wooden", "stone"],
         "agent": ["spy", "assassin", "diplomat", "merchant", "priest"],
         "agent_limit": ["spy", "assassin", "diplomat", "merchant", "priest"],
         "religion": RELIGIONS_M2.replace(" or ", ", ").split(", "),
         "religious_belief": RELIGIONS_BI.replace(" or ", ", ").split(", ")}


def form(key):
    """The line's form for the right click: its values with their separators (spaces), or ''."""
    if key in ("recruit", "recruit_pool", "agent"):
        return {"recruit": '"unit type"  experience   (or bonus N)   [requires ...]',
                "recruit_pool": '"unit type"  at-start  a-turn  most  experience   (spaces; experience or bonus N)'
                                '   [requires ...]',
                "agent": "spy|assassin|diplomat|merchant|priest  level   (or bonus N)   [requires ...]"}[key]
    got = LINES.get(key)
    if not got:
        return ""
    what, names = got
    if key == "hidden_resources":
        return "name name name ...   (spaces between)"
    if not names:
        return ""
    if key in NOT_CAPS:
        return " ".join(names) + "   (spaces between)"
    label = [n for n in names if not n.startswith("'")][-1]
    return "%s   or   bonus %s   (%s alone = a level, the highest counts; bonus = added on top)   [requires ...]" % (
        label, label, label)


def explain(key, value, medieval2=False):
    """What a line of a building chain does and what each of its values is: a text for the '?' (None when the line
    is not known)."""
    key = key.strip()
    value = value.split(";")[0].strip()
    head, cond = _cut(value)
    first = head.split()[0] if head.split() else ""
    if key not in LINES and key not in ("recruit", "recruit_pool", "agent") and (
            first in ("city", "castle") or value.startswith("requires")):
        # a level's own line: its name, Medieval II the kind of town, then who may build it
        out = ["%s: a level of the chain." % key]
        if first in ("city", "castle"):
            out.append("1. town kind = %s - Medieval II: built in a %s" % (first, first))
        if cond:
            out.append("then: %s - %s" % (cond, REQUIRES))
        return "\n".join(out)
    if key == "recruit" or key == "recruit_pool":
        m = re.match(r'"([^"]+)"\s*(.*)$', head)
        unit, rest = (m.group(1), m.group(2).split()) if m else (head, [])
        out = ["%s: a unit this level lets the town train." % key, "1. unit = %s - its type in "
               "export_descr_unit.txt" % unit]
        names = (["units at the start (the pool)", "units added a turn", "most units the pool holds",
                  "experience the units start with"] if key == "recruit_pool" else ["experience it starts with"])
        _numbers(out, rest, names, 2)
        if cond:
            out.append("then: %s - %s" % (cond, REQUIRES))
        return "\n".join(out)
    if key == "agent":
        parts = head.split()
        out = ["agent: an agent this level lets the town train."]
        names = ["the agent's kind (spy, assassin, diplomat; Medieval II also merchant, priest)",
                 "the level it starts at"]
        if parts:
            out.append("1. agent = %s - %s" % (parts[0], names[0]))
        _numbers(out, parts[1:], names[1:], 2)
        if cond:
            out.append("then: %s - %s" % (cond, REQUIRES))
        return "\n".join(out)
    if key not in LINES:
        return None
    what, names = LINES[key]
    out = ["%s: %s." % (key, what)]
    if names and key not in NOT_CAPS:
        label = [n for n in names if not n.startswith("'")][-1]
        _numbers(out, head.split(), [label], 1)
    elif names:
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
