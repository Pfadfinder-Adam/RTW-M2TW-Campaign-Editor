"""Units from export_descr_unit.txt, with the pictures the game shows for them."""

import os

from .moddata import _ci
from .textio import strip_comment, tokens


class Unit:
    def __init__(self, type_):
        self.type = type_
        self.dictionary = ""
        self.category = ""
        self.cls = ""
        self.soldiers = 0
        self.attributes = []
        self.cost = []              # turns, cost, upkeep, weapon up, armour up, custom battle cost
        self.ownership = []

    @property
    def price(self):
        return self.cost[1] if len(self.cost) > 1 else 0

    @property
    def upkeep(self):
        return self.cost[2] if len(self.cost) > 2 else 0

    @property
    def mercenary(self):
        return "mercenary_unit" in self.attributes

    @property
    def general(self):
        return "general_unit" in self.attributes or "general_unit_upgrade" in " ".join(self.attributes)

    def summary(self):
        return "%s - %s %s, %d men, cost %d, upkeep %d%s" % (
            self.type, self.category, self.cls, self.soldiers, self.price, self.upkeep,
            ", mercenary" if self.mercenary else "")


def _ints(text):
    out = []
    for p in text.replace(",", " ").split():
        try:
            out.append(int(float(p)))
        except ValueError:
            pass
    return out


def read_units(edu):
    """[Unit] from a loaded export_descr_unit TextFile, in file order (read once while its text stays the same)."""
    from .textio import parsed_once
    return parsed_once(_read_units, edu)


def _read_units(edu):
    units, cur = [], None
    for l in edu.texts():
        code = strip_comment(l)
        t = tokens(l)
        if not t:
            continue
        key = t[0]
        rest = code.split(None, 1)[1] if len(code.split(None, 1)) > 1 else ""
        if key == "type":
            cur = Unit(" ".join(code.split()[1:]))
            units.append(cur)
        elif cur is None:
            continue
        elif key == "dictionary" and len(t) > 1:
            cur.dictionary = t[1]
        elif key == "category" and len(t) > 1:
            cur.category = t[1]
        elif key == "class" and len(t) > 1:
            cur.cls = t[1]
        elif key == "soldier" and len(t) > 2:
            n = _ints(" ".join(t[2:3]))
            cur.soldiers = n[0] if n else 0
        elif key == "attributes":
            cur.attributes = [a.strip() for a in rest.split(",") if a.strip()]
        elif key == "stat_cost":
            cur.cost = _ints(rest)
        elif key == "ownership":
            cur.ownership = [a.strip() for a in rest.replace(",", " ").split() if a.strip()]
    return units


# the lines every unit must have (RomeTW.exe / medieval2.exe: each missing one is a Script Error; every vanilla unit of
# Rome, BI, Alexander and Medieval II has them all)
EDU_NEEDS = ("dictionary", "category", "class", "soldier", "attributes", "formation", "stat_health", "stat_pri",
             "stat_pri_attr", "stat_sec", "stat_sec_attr", "stat_pri_armour", "stat_sec_armour", "stat_heat",
             "stat_ground", "stat_mental", "stat_charge_dist", "stat_fire_delay", "stat_food", "stat_cost")
# Rome's own attribute words (RomeTW.exe; anything else: 'Unrecognised attribute')
ROME_ATTRIBUTES = set("""can_sap can_withdraw can_formed_charge can_feign_rout can_run_amok can_swim can_horde hide_forest
    hide_improved_forest hide_long_grass hide_anywhere sea_faring command heavy hardy very_hardy power_charge slave
    frighten_foot frighten_mounted mercenary_unit no_custom is_peasant cantabrian_circle druid screeching_women warcry
    general_unit general_unit_upgrade legionary_name""".split())
# men a unit may have before the scale (the code's own numbers): combatant / non_combatant; extras at most 300
SOLDIERS = {"rome": (6, 60), "medieval2": (4, 100)}


def edu_problems(lines, factions, kind="rome", engine=None):
    """What the games' own export_descr_unit readers refuse, per unit and in their words (each a Script Error - the
    game stops): a missing line, an ownership naming no faction / culture / all. Without an engine also: soldiers
    out of range (Rome 6-60, Medieval II 4-100, non-combatants 1-300), more than 300 extras, more than 3 officers,
    and in Rome an attribute it does not know. With REX / M2EX numbers are no limit (limits.md THE RULE; REX's
    `soldiers { }` block stands for the soldier line). factions: [(faction, culture)]."""
    owners = {f for f, _ in factions} | {c for _, c in factions if c} | {"all"}
    blocks, cur = [], None
    for n, l in enumerate(lines, 1):
        code = strip_comment(l)
        t = tokens(code)
        if not t:
            continue
        if t[0] == "type":
            cur = {"type": " ".join(code.split()[1:]), "line": n, "keys": {}, "officers": 0}
            blocks.append(cur)
        elif cur is not None:
            rest = code.split(None, 1)[1] if len(code.split(None, 1)) > 1 else ""
            cur["keys"].setdefault(t[0], rest)
            cur["officers"] += t[0] == "officer"
    out = []

    def say(b, what, quoted=True):
        out.append("export_descr_unit.txt, %s (line %d): the game stops at the start - %s" % (
            b["type"], b["line"], "'%s'" % what if quoted else what))

    for b in blocks:
        keys, name = b["keys"], b["type"]
        if "soldiers" in keys:
            keys.setdefault("soldier", "")
        if "dictionary" not in keys:
            say(b, "Must declare a dictionary entry for the name of unit type '%s'." % name)
        lack = [k for k in EDU_NEEDS[1:] if k not in keys]
        if lack:
            say(b, "it has no %s line%s" % (", ".join(lack), "s" if len(lack) > 1 else ""), quoted=False)
        for o in keys.get("ownership", "").replace(",", " ").split():
            if o not in owners:
                say(b, "Invalid ownership type '%s' found in unit '%s'." % (o, name))
        if engine:
            continue
        nums = [x.strip() for x in keys.get("soldier", "").split(",")]
        if len(nums) > 2 and nums[1].isdigit() and nums[2].isdigit():
            men, extras = int(nums[1]), int(nums[2])
            low, high = (1, 300) if keys.get("category") == "non_combatant" else SOLDIERS.get(kind, SOLDIERS["rome"])
            if not low <= men <= high:
                say(b, "Invalid number of soldiers %d for %s unit type '%s'." % (
                    men, "non-combatant" if keys.get("category") == "non_combatant" else "combatant", name))
            if extras > 300:
                say(b, "Invalid number of extras %d for unit type '%s'." % (extras, name))
        if b["officers"] > 3:
            say(b, "Too many officers added to unit type '%s'." % name)
        if kind == "rome":
            for a in keys.get("attributes", "").split(","):
                a = a.split()[0] if a.split() else ""
                if a and a not in ROME_ATTRIBUTES:
                    say(b, "Unrecognised attribute '%s' in unit type '%s'." % (a, name))
    return out


def owner_factions(mod, ownership):
    """The factions an ownership list names: factions by name, every faction of a culture it names, all of them
    for 'all' (in the order of descr_sm_factions.txt). A list naming nothing the mod knows is given back as it is."""
    own = [x.strip() for x in ownership if x and x.strip()]
    out = [n for n, c in mod.factions() if n in own or c in own or "all" in own]
    return out or own


def faction_units(mod, faction, ships=False, mercs=False):
    """Units the faction may own (its name, its culture or 'all' in ownership - vanilla
    gives ships by culture): land units, or with ships=True only its ships;
    never the non_combatant townsfolk."""
    edu = mod.file("edu")
    if not edu:
        return []
    owners = {faction, "all"}
    try:
        owners.add(mod.culture(faction))
    except Exception:
        pass
    # mercs=True adds every mercenary (vanilla gives them to the rebels, 'slave', and
    # hires them out by region through descr_mercenaries.txt)
    return [u for u in read_units(mod.load(edu))
            if (owners & set(u.ownership) or (mercs and u.mercenary)) and (u.category == "ship") == ships
            and u.category != "non_combatant"]            # townsfolk for battles in towns, not troops


# Folders of ui/units (ui/unit_info) that are not a faction's: the recruitment queue's small pictures
# (ui/units/construction, 42 x 56 - a whole figure) - a card looked up there showed a figure where the game shows
# the card (a tester: 'full-height pictures instead of the cards').
NOT_FACTIONS = ("construction",)
MERC_FOLDERS = ("mercs", "merc", "mercenaries")        # the games' own: Rome ui/units/mercs + ui/unit_info/merc


def card_path(mod, faction, dictionary, info=False, owners=None, mercenary=False):
    """The card the game shows for a unit (ui/units/<faction>/#<dict>.tga; info: the picture of its description,
    ui/unit_info/<faction>/<dict>_info.tga) - the one resolver every window uses. Looked up the game's way: the
    faction's own folder, then each owner's (owners: the factions the unit's ownership gives it - unit_owners), then
    the mercenaries' folder for a mercenary; never a folder that is no faction's (construction). owners None (a
    caller that does not know the unit): any faction's folder. None when there is no such card - a window says so,
    never another picture in its place. The mod's own data first, then the game's (as the game reads them)."""
    from .clone import data_roots
    name = ("%s_info.tga" if info else "#%s.tga") % dictionary
    folders = [os.path.join(d, "ui", "unit_info" if info else "units") for d in data_roots(mod)]
    folders = [f for f in folders if os.path.isdir(f)]
    order = [faction] if faction else []
    if owners is not None:
        order += [o for o in owners if o and o not in order]
        if mercenary:
            order += [m for m in MERC_FOLDERS if m not in order]
    for who in order:
        for folder in folders:
            own = _ci(folder, who)
            p = _ci(own, name) if own else None
            if p:
                return p
    if owners is not None:
        return None
    for folder in folders:                              # a caller without the unit: any faction's card
        for d in sorted(os.listdir(folder)):
            sub = os.path.join(folder, d)
            if d.lower() not in NOT_FACTIONS and os.path.isdir(sub):
                p = _ci(sub, name)
                if p:
                    return p
    return None


def unit_owners(mod, unit):
    """The factions whose cards a unit has, in the order the card is looked up: its ownership's factions (a culture
    named: every faction of it; 'all': every faction), descr_sm_factions.txt's order."""
    return owner_factions(mod, getattr(unit, "ownership", None) or [])


def unit_card(mod, unit, faction=None, info=False):
    """card_path for a Unit (units.read_units): its own owners and, for a mercenary, the mercenaries' folder."""
    if not getattr(unit, "dictionary", ""):
        return None
    return card_path(mod, faction, unit.dictionary, info, owners=unit_owners(mod, unit),
                     mercenary=bool(getattr(unit, "mercenary", False)))
