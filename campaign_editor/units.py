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


def card_path(mod, faction, dictionary, info=False):
    """ui/units/<faction>/#<dict>.tga (or ui/unit_info/<faction>/<dict>_info.tga),
    else the same picture in any other faction's folder, else None."""
    folder = os.path.join(mod.data, "ui", "unit_info" if info else "units")
    name = ("%s_info.tga" if info else "#%s.tga") % dictionary
    own = _ci(folder, faction)
    if own:
        p = _ci(own, name)
        if p:
            return p
    if not os.path.isdir(folder):
        return None
    for d in sorted(os.listdir(folder)):
        sub = os.path.join(folder, d)
        if os.path.isdir(sub):
            p = _ci(sub, name)
            if p:
                return p
    return None
