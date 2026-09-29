"""Unit attributes the engine knows (export_descr_unit.txt), with their effect in plain
words, so the Unit editor can offer them even when no unit of the mod uses one yet.

REX (the 64-bit engine for Rome: Total War, also Medieval II) added these; the list is
REX's own (docs/reference/rex_edu_attributes.md). A word goes on one line of the unit:
'attributes', 'stat_mental', 'stat_ground' or 'stat_pri_attr' / 'stat_sec_attr'."""

REX = "REX"

# (word, line, effect)
ATTRIBUTES = [
    # morale
    ("expendable", "stat_mental", "does not give other units the 'friendlies routing' morale penalty"),
    ("elitist", "stat_mental", "ignores the 'friendlies routing' penalty from units that are not elitist"),
    ("steadfast", "stat_mental", "smaller 'friendlies routing' morale penalty"),
    ("intimidate", "stat_mental", "a lesser fear effect on enemies nearby"),
    ("immune_to_psychology", "stat_mental", "no morale penalty from fear effects of enemies nearby"),
    # fatigue (hardy = -2 fatigue rate, very_hardy = -4)
    ("relentless", "attributes", "tires more slowly (fatigue rate -2, like hardy)"),
    ("disciplined_missile", "attributes", "tires more slowly while shooting (-1)"),
    ("inexhaustible", "attributes", "never gets tired"),
    # combat
    ("brace_for_charge", "attributes", "braces harder: halves the charge bonus of a charge it is ready for"),
    ("aggressive_push", "attributes", "charge bonus +1"),
    ("disciplined_charge", "attributes", "its charge bonus fades more slowly (-2 a hit instead of -3)"),
    ("ai_cannot_skirmish", "attributes", "the AI never puts it in skirmish mode"),
    ("ai_cannot_toggle_formation", "attributes", "the AI never switches it to loose formation"),
    # terrain
    ("desert_raider", "stat_ground", "+2 when fighting in desert"),
    ("forest_ambusher", "stat_ground", "+2 when fighting in forest"),
    # in a town, unit size
    ("troublemaker", "attributes", "in a garrison: public order -5 % per 80 soldiers, income - 2 per soldier"),
    ("police", "attributes", "in a garrison: public order +5 % per 80 soldiers"),
    ("client_kingdom_only_units", "attributes", "recruited only by a protectorate"),
    ("infinite_ammo", "attributes", "never runs out of ammunition"),
    ("no_scale", "attributes", "the unit-size setting does not change it: the soldier count as written"),
    ("single_entity", "attributes", "one figure that does not scale with unit size (like a general)"),
    # weapons
    ("sp", "stat_pri_attr", "shield piercing: halves the shield of the unit it hits"),
    ("sp", "stat_sec_attr", "shield piercing: halves the shield of the unit it hits"),
]

# keys a unit may get although no unit of the mod has one yet: {key: (example value, effect)}
ENGINE_KEYS = {
    "recruit_priority_offset": ("0", "the AI recruits the unit more (a higher number) or less (lower); "
                                     "Medieval II has it, REX adds it to Rome"),
}

LINES = ("attributes", "stat_mental", "stat_ground", "stat_pri_attr", "stat_sec_attr")


def for_line(key):
    """[(word, effect)] of the words the engine knows for that line of a unit."""
    return [(w, e) for w, l, e in ATTRIBUTES if l == key]


def words(value):
    """The comma-separated items of a line's value, stripped ('no' of an empty weapon list kept)."""
    return [x.strip() for x in value.split(",") if x.strip()]


def toggled(key, value, word, on):
    """The line's value with word added at the end (on) or taken out; the other items and
    their order are kept. A weapon line left empty reads 'no'."""
    items = words(value)
    if on:
        if word in items:
            return value
        if key in ("stat_pri_attr", "stat_sec_attr") and items == ["no"]:
            items = []
        items.append(word)
    else:
        if word not in items:
            return value
        items = [x for x in items if x != word]
        if not items and key in ("stat_pri_attr", "stat_sec_attr"):
            items = ["no"]
    return ", ".join(items)
