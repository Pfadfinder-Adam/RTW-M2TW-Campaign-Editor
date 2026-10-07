"""The traits and the retinue (ancillaries) themselves, both games: export_descr_character_traits.txt and
export_descr_ancillaries.txt read as blocks, edited in place and copied into new ones, with the names and
descriptions players see (export_VnVs.txt, export_ancillaries.txt).

    Trait GoodDefender                      Ancillary apothecary
        Characters family                       Type Health
        AntiTraits BadDefender                  Transferable  1
        Level Promising_Defender                Image academic_alchemist.tga
            Description Promising_Defender_desc ExcludeCultures mesoamerican
            Threshold  1                        Description apothecary_desc
            Effect Defence  1                   Effect Fertility  1

A level's name is also the key of the name players see ({Promising_Defender} in export_VnVs), its description
keys <level>_desc / <level>_effects_desc ... An ancillary's name is the key of its name, <name>_desc its text.

Medieval II ships its string tables compiled (text/<name>.txt.strings.bin). A text written where only the .bin lies
becomes a .txt made from the .bin with the change in it, and the .bin goes (Plan.stale_bins: the game reads a .bin
beside the .txt instead of it - a tester's run showed the old texts - and builds it again).
Triggers (what gives a trait) are not touched: a new trait is given to characters in the Character editor."""

import os
import re

from .strtables import write_texts  # noqa: F401  (the texts players see)
from .textio import strip_comment, tokens

RE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
TEXTS = {"trait": "export_VnVs.txt", "ancillary": "export_ancillaries.txt"}
KEY_OF = {"trait": "Trait", "ancillary": "Ancillary"}
LEVEL_TEXT_KEYS = ("Description", "EffectsDescription", "GainMessage", "LoseMessage", "Epithet")


def file_of(mod, kind):
    return mod.file("traits" if kind == "trait" else "ancillaries")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def blocks(f, kind):
    """{name: {'span': (a, b), 'levels': [{'name', 'span', 'threshold': (line, value), 'effects': [(line, attr,
    value)], 'keys': {word: (line, key)}}], 'lines': {word: (line, text after it)}, 'effects': [...] (an
    ancillary's)}} - b is past the block's last line that is not blank or a comment."""
    head = KEY_OF[kind]
    out, cur, lvl = {}, None, None
    last = None
    for i in range(len(f)):
        code = strip_comment(f.text(i)).strip()
        if not code:
            continue
        t = code.split()
        word = t[0]
        if word in ("Trait", "Ancillary", "Trigger"):
            if cur is not None:
                cur["span"] = (cur["span"][0], last + 1)
                if lvl is not None:
                    lvl["span"] = (lvl["span"][0], last + 1)
            cur = lvl = None
            if word == head and len(t) > 1:
                cur = {"span": (i, i + 1), "levels": [], "lines": {}, "effects": []}
                out[t[1]] = cur
            last = i
            continue
        if cur is None:
            continue
        last = i
        rest = code[len(word):].strip()
        if kind == "trait" and word == "Level" and len(t) > 1:
            if lvl is not None:
                lvl["span"] = (lvl["span"][0], i)
            lvl = {"name": t[1], "span": (i, i + 1), "threshold": None, "effects": [], "keys": {}}
            cur["levels"].append(lvl)
        elif word == "Effect" and len(t) > 2:
            try:
                eff = (i, t[1], int(t[2]))
            except ValueError:
                continue
            (lvl["effects"] if lvl is not None else cur["effects"]).append(eff)
        elif lvl is not None and word == "Threshold" and len(t) > 1:
            try:
                lvl["threshold"] = (i, int(t[1]))
            except ValueError:
                pass
        elif lvl is not None and word in LEVEL_TEXT_KEYS and len(t) > 1:
            lvl["keys"][word] = (i, t[1])
        else:
            cur["lines"].setdefault(word, (i, rest))
    if cur is not None:
        cur["span"] = (cur["span"][0], last + 1)
        if lvl is not None:
            lvl["span"] = (lvl["span"][0], last + 1)
    return out


def effect_names(mod):
    """Every attribute an Effect line of the traits or the retinue names (to check a typed one)."""
    names = set()
    for kind in ("trait", "ancillary"):
        path = file_of(mod, kind)
        if path:
            for l in mod.load(path).texts():
                t = tokens(l)
                if len(t) > 2 and t[0] == "Effect":
                    names.add(t[1])
    return names


# every effect the game's exe knows (its own table, read from RomeTW.exe / medieval2.exe), with what it does in plain
# words, by group - for the Effects field's right-click menu (a tester: nobody knows every bonus by heart)
EFFECT_GROUPS = (
    ("Generals and battle", (
        ("Command", "generals' skill in battle (the stars)"), ("Attack", "melee attack of his men"),
        ("Defence", "defence of his men"), ("TroopMorale", "morale of his army"),
        ("MovementPoints", "how far his army moves on the map"), ("Ambush", "chance to ambush / not be ambushed"),
        ("NightBattle", "can fight at night"), ("SiegeAttack", "attacking towns"), ("SiegeDefence", "defending towns"),
        ("SiegeEngineering", "building siege equipment faster"), ("NavalCommand", "admirals' skill at sea"),
        ("CavalryCommand", "command of cavalry"), ("InfantryCommand", "command of infantry"),
        ("ArtilleryCommand", "command of artillery (Medieval II)"),
        ("GunpowderCommand", "command of gunpowder units (Medieval II)"),
        ("BodyguardSize", "men in his bodyguard (Medieval II)"), ("BodyguardValour", "experience of his bodyguard"),
        ("HitPoints", "his own hit points in battle"), ("BattleSurgery", "wounded men saved after a battle"),
        ("LineOfSight", "how far he sees on the map"), ("Looting", "money from sacking towns"))),
    ("Governing towns", (
        ("Management", "the governor's skill"), ("Influence", "influence (Rome: the stars; diplomats)"),
        ("Law", "law in his town"), ("Unrest", "unrest in his town"), ("Squalor", "squalor in his town"),
        ("Health", "health in his town"), ("TaxCollection", "taxes collected"), ("Trading", "trade income"),
        ("Farming", "farming income"), ("Mining", "mining income"), ("Construction", "cheaper buildings"),
        ("TrainingUnits", "cheaper units"), ("TrainingAgents", "cheaper agents"),
        ("TrainingAnimalUnits", "cheaper animal units"), ("Fertility", "children he has"),
        ("LocalPopularity", "popularity in his town"), ("GrainTrading", "grain trade (Rome)"),
        ("SlaveTrading", "slave trade (Rome)"), ("PublicSecurity", "security of his town"))),
    ("Character", (
        ("Loyalty", "loyalty to the faction"), ("Chivalry", "chivalry (Medieval II; below 0 = Dread)"),
        ("Piety", "piety (Medieval II; priests too)"), ("Authority", "the leader's authority (Medieval II)"),
        ("Electability", "chance to be elected (Rome Senate, Medieval II pope)"),
        ("SenateStanding", "standing with the Senate (Rome)"), ("PopularStanding", "standing with the people (Rome)"),
        ("PersonalSecurity", "safety from assassins"), ("Generosity", "generosity (Medieval II)"),
        ("Boldness", "boldness (Medieval II)"), ("Disposition", "disposition (Medieval II)"),
        ("Violence", "violence (Medieval II)"), ("Purity", "purity (Medieval II)"),
        ("Eligibility", "worth as a husband / bride (Medieval II)"), ("HeresyImmunity", "safe from heresy"),
        ("Unorthodoxy", "leaning to heresy (Medieval II)"))),
    ("Agents", (
        ("Subterfuge", "spies' and assassins' skill"), ("Bribery", "bribing others"),
        ("BribeResistance", "resisting bribes"), ("FootInTheDoor", "diplomats' first contact"),
        ("Negotiation", "diplomats' bargaining"), ("Sabotage", "saboteurs' skill (Medieval II)"),
        ("Assassination", "assassins' skill (Medieval II)"), ("Charm", "princesses' charm (Medieval II)"),
        ("Finance", "merchants' skill (Medieval II)"))),
)
COMBAT_V = ("Combat_V_", "fighting better against one faction, culture or religion: Combat_V_<name> (Rome: "
            "Combat_V_<culture or faction>, Medieval II: Combat_V_Faction_<faction>, Combat_V_Religion_<religion>)")


def effect_menu(mod, used=()):
    """[(group, [(name, words)])] for the Effects field's menu: the groups of the game's effects (only those of this
    game where marked), the Combat_V_ ones this mod uses or its factions give, and any other the mod's files use."""
    m2 = False
    try:
        from .limits import game_kind
        m2 = game_kind(mod) == "medieval2"
    except Exception:
        pass
    other = "Rome" if m2 else "Medieval II"
    out, known = [], set()
    for group, items in EFFECT_GROUPS:
        keep = [(n, w) for n, w in items if "(%s)" % other not in w and "(%s;" % other not in w]
        known |= {n for n, _ in keep}
        out.append((group, keep))
    combat = sorted(n for n in used if n.startswith("Combat_V_"))
    try:
        facs = mod.factions()
    except Exception:
        facs = []
    if m2:                           # Medieval II: by faction (and religion, as the mod's files use them)
        combat += ["Combat_V_Faction_%s" % f for f, _ in facs]
    else:                            # Rome: by culture, as vanilla's own (Combat_V_Barbarian)
        combat += ["Combat_V_%s" % c.capitalize() for _, c in facs if c]
    out.append(("Against a faction, culture or religion", [(n, "fights better against %s" % n.split("_", 2)[-1])
                                                           for n in sorted(set(combat))]))
    rest = sorted(n for n in used if n not in known and not n.startswith("Combat_V_"))
    if rest:
        out.append(("Others this mod's files use", [(n, "") for n in rest]))
    return out


def add_effect(text, name, value=1):
    """The Effects text with 'name value' added after a comma (or alone when empty) - the right-click menu's insert."""
    t = (text or "").rstrip().rstrip(",").rstrip()
    return ("%s, %s %d" % (t, name, value)) if t else "%s %d" % (name, value)


def parse_effects(text):
    """'Command 1, Chivalry -2' -> [('Command', 1), ('Chivalry', -2)]; ValueError in plain words."""
    out = []
    for part in [p.strip() for p in (text or "").replace(";", ",").split(",") if p.strip()]:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+([+-]?\d+)$", part)
        if not m:
            raise ValueError("'%s': an effect is a name and a whole number, like 'Command 1' or 'Loyalty -2'" % part)
        out.append((m.group(1), int(m.group(2))))
    return out


def effects_words(effects):
    return ", ".join("%s %d" % (a, v) for a, v in effects)


# ---------------------------------------------------------------------------
# The texts players see
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def _indent_of(text):
    return text[:len(text) - len(text.lstrip())]


def _set_effects(f, span, effects, old, after):
    """The Effect lines of a level / ancillary (old: [(line, attr, value)]) replaced by `effects`, written where the
    first old one was (else after line `after`), in the old ones' indentation."""
    if old:
        indent, at = _indent_of(f.text(old[0][0])), old[0][0]
    else:
        base = f.text(after)
        indent, at = _indent_of(base) + ("    " if base.lstrip().startswith(("Level", "Ancillary")) else ""), after + 1
    for line, _, _ in sorted(old, reverse=True):
        f.delete(line, line + 1)
        if line < at:
            at -= 1
    f.insert(at, ["%sEffect %s  %d " % (indent, a, v) for a, v in effects])


def _set_word(f, line, word, value):
    text = f.text(line)
    m = re.match(r"^(\s*%s\s+)(\S+)" % re.escape(word), text)
    if m:
        f.set(line, m.group(1) + str(value) + text[m.end():])


def copy_block(plan, kind, src, new):
    """A new trait / ancillary: a copy of `src` under the name `new`, right after it; a trait's levels and every
    text key renamed after the new name (their texts copied). Returns {old key: new key} of the texts."""
    if not RE_NAME.match(new or ""):
        raise ValueError("'%s': a name is letters, digits and _ only, starting with a letter" % new)
    path = file_of(plan.mod, kind)
    f = plan.edit(path)
    have = blocks(f, kind)
    if new in have or new.lower() in {k.lower() for k in have}:
        raise ValueError("there is already a %s called '%s'" % (kind, new))
    b = have.get(src)
    if b is None:
        raise ValueError("no %s called '%s'" % (kind, src))
    a, e = b["span"]
    lines = [f.text(i) for i in range(a, e)]
    keys = {src: new}
    if kind == "trait":
        taken = {l["name"].lower() for x in have.values() for l in x["levels"]}
        for lv in b["levels"]:
            n = re.sub(re.escape(src), new, lv["name"], flags=re.I) if src.lower() in lv["name"].lower() else \
                "%s_%s" % (lv["name"], new)
            while n.lower() in taken:
                n += "_2"
            taken.add(n.lower())
            keys[lv["name"]] = n
            for _, k in lv["keys"].values():
                keys[k] = k.replace(lv["name"], n) if lv["name"] in k else "%s_%s" % (k, new)
    else:
        for word in ("Description", "EffectsDescription"):
            got = b["lines"].get(word)
            if got:
                k = got[1].split()[0]
                keys[k] = k.replace(src, new) if src in k else "%s_%s" % (k, new)
    out = []
    for text in lines:
        code = strip_comment(text)
        words = code.split()
        if words and words[0] in (KEY_OF[kind], "Level") + LEVEL_TEXT_KEYS and len(words) > 1 and words[1] in keys:
            text = re.sub(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(words[1]), keys[words[1]], text, count=1)
        out.append(text)
    nl_blank = ""
    f.insert(e, [nl_blank, ";------------------------------------------"] + out)
    plan.note(f, "%s %s: a copy of %s" % (kind, new, src))
    if kind == "trait":
        plan.warn(f, "no trigger gives %s yet: give it to characters in the Character editor (their traits), or "
                     "copy a trigger of %s in the file" % (new, src))
    return keys


def apply(plan, kind, changes):
    """changes = {'new': [[src, new]], 'edit': {name: {'characters': text, 'exclude': text, 'image': name,
    'levels': {level: {'threshold': n, 'effects': [[attr, value]]}}, 'effects': [[attr, value]]}},
    'texts': {KEY: text}, 'pictures': {image name: picture file}} for kind 'trait' or 'ancillary'."""
    mod = plan.mod
    path = file_of(mod, kind)
    if not path:
        raise ValueError("this mod has no %s file" % ("traits" if kind == "trait" else "ancillaries"))
    texts = dict(changes.get("texts") or {})
    shown = None
    for src, new in changes.get("new") or []:
        keys = copy_block(plan, kind, src, new)
        if shown is None:
            from .charpanel import strings
            shown = strings(mod, TEXTS[kind])
        for old, k in keys.items():
            if old.upper() in shown and k not in texts:
                texts[k] = shown[old.upper()]
    f = plan.edit(path)
    for name, ch in sorted((changes.get("edit") or {}).items()):
        b = blocks(f, kind).get(name)
        if b is None:
            raise ValueError("no %s called '%s'" % (kind, name))
        for word, key in (("Characters", "characters"), ("ExcludeCultures", "exclude"), ("Image", "image")):
            if ch.get(key) is None:
                continue
            got = b["lines"].get(word)
            value = str(ch[key]).strip()
            if got:
                text = f.text(got[0])
                code = strip_comment(text)
                f.set(got[0], "%s%s %s%s" % (_indent_of(text), word, value, text[len(code.rstrip()):]))
            elif value:
                at = b["span"][0]
                f.insert(at + 1, ["%s%s %s" % (_indent_of(f.text(at + 1)) or "    ", word, value)])
            plan.note(f, "%s %s: %s %s" % (kind, name, word, value))
            b = blocks(f, kind)[name]
        for lname, lch in sorted((ch.get("levels") or {}).items()):
            lv = next((l for l in blocks(f, kind)[name]["levels"] if l["name"] == lname), None)
            if lv is None:
                raise ValueError("%s has no level %s" % (name, lname))
            if lch.get("threshold") is not None and lv["threshold"]:
                _set_word(f, lv["threshold"][0], "Threshold", int(lch["threshold"]))
                plan.note(f, "%s / %s: threshold %d" % (name, lname, int(lch["threshold"])))
            if lch.get("effects") is not None:
                lv = next(l for l in blocks(f, kind)[name]["levels"] if l["name"] == lname)
                after = lv["threshold"][0] if lv["threshold"] else lv["span"][0]
                _set_effects(f, lv["span"], [tuple(x) for x in lch["effects"]], lv["effects"], after)
                plan.note(f, "%s / %s: %s" % (name, lname, effects_words(lch["effects"]) or "no effects"))
        if ch.get("effects") is not None and kind == "ancillary":
            b = blocks(f, kind)[name]
            after = max((l for l, _ in b["lines"].values()), default=b["span"][0])
            _set_effects(f, b["span"], [tuple(x) for x in ch["effects"]], b["effects"], after)
            plan.note(f, "%s %s: %s" % (kind, name, effects_words(ch["effects"]) or "no effects"))
    for image, src in sorted((changes.get("pictures") or {}).items()):
        from .factionart import replace_picture
        from .clone import picture_file
        like = picture_file(mod.data, "ui/ancillaries/%s" % image)
        target = like[1] if like else os.path.join(mod.data, "ui", "ancillaries", image)
        if not like:                                    # a new picture: the size of the others
            folder = os.path.join(mod.data, "ui", "ancillaries")
            others = sorted(n for n in os.listdir(folder) if n.lower().endswith(".tga")) if os.path.isdir(folder) \
                else []
            like = (None, os.path.join(folder, others[0])) if others else None
        replace_picture(plan, src, target, like[1] if like else None)
    write_texts(plan, TEXTS[kind], texts)
