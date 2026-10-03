"""The Module builder: a new add-on put together from blocks, no code.

A module is a recipe of three parts, each picked from lists in plain words:
  WHEN  something happens in the campaign (a faction's turn starts, a general takes a town, a building is done ...),
  IF    conditions hold (it is the player, its money is below 0, the town has over 24000 people, a 5 % chance ...),
  DO    actions (give money, add or take people, build, tear down, new units, give the town away, a trait, a message).
The editor writes the Squirrel script itself (REX for Rome and M2EX for Medieval II run the same script: their
script/main.nut loads every .nut of the game's script/modules). The script is an ordinary add-on: it is kept in the
editor's add-ons folder and shows in the Add-ons list; any number or text of the recipe may be made a setting (a
'local NAME = value' line at the top) that the player changes there later. The recipe itself rides in the script as
one comment line (// @recipe {...}), so the module can be opened in the builder again.

Every event, condition and action is one both engines have (their docudemon event lists, the dev-console commands in
both console_commands.txt, the API names in REX.exe / M2EX.exe) - checked 2026-10-04. Messages are the games' own
event scrolls: the console's display_message reads <id>, <id>_body from the mod's text/custom_messages.txt, which
putting the module in writes."""

import json
import os
import re

# what an event brings along (the payload): the faction, a town, a general, the faction a town was taken from, a unit
F, S, C, T, U = "faction", "settlement", "character", "target", "unit"
SUBJECT_WORDS = {F: "a faction", S: "a town", C: "a general", T: "a town's old owner", U: "a unit"}


class Event:
    def __init__(self, key, label, engine, subjects, help):
        self.key, self.label, self.engine, self.subjects, self.help = key, label, engine, subjects, help


EVENTS = [
    Event("faction_turn", "a faction's turn starts", "FactionTurnStart", (F,),
          "once for every faction at the start of its turn - add 'the faction is: the player' for your own turns"),
    Event("town_turn", "a town's turn starts (each town)", "SettlementTurnStart", (F, S),
          "once for every town of every faction, at the start of its faction's turn"),
    Event("town_taken", "a general takes a town", "GeneralCaptureSettlement", (F, S, C, T),
          "the faction is the one that took it, the old owner the one that lost it"),
    Event("building_done", "a building is finished in a town", "BuildingCompleted", (F, S),
          "once for every building finished"),
    Event("unit_trained", "a unit is trained in a town", "UnitTrained", (F, S, U),
          "once for every unit trained (bought mercenaries are not trained)"),
    Event("battle_over", "a battle ends (for each general in it)", "PostBattle", (F, C),
          "once for each general who fought, winner or loser"),
    Event("town_riots", "a town riots", "CityRiots", (F, S), "the town's owner is the faction"),
    Event("town_rebels", "a town rebels", "CityRebels", (F, S), "the town's owner (before it goes) is the faction"),
    Event("town_grows", "a town grows to its next level", "SettlementUpgraded", (F, S),
          "a village becomes a town, a town a large town ..."),
    Event("faction_destroyed", "a faction is destroyed", "FactionDestroyed", (F,), "the faction is the one gone"),
    Event("new_leader", "a faction gets a new leader", "BecomesFactionLeader", (F, C), "the general is the new leader"),
    Event("comes_of_age", "a son comes of age", "CharacterComesOfAge", (F, C), "the general is the young man"),
]
EVENT = {e.key: e for e in EVENTS}
ENGINE_EVENT = "ev:"                 # a recipe's WHEN 'ev:<Name>': any event of the engines' own list


def event_of(when, game="both", mod=None):
    """The Event a recipe's WHEN names: one of the plain ones above, or 'ev:<Name>' - any event of the engines' own
    list, what it brings read from its exports. None when it names nothing."""
    if when in EVENT:
        return EVENT[when]
    if not isinstance(when, str) or not when.startswith(ENGINE_EVENT) or len(when) <= len(ENGINE_EVENT):
        return None
    name = when[len(ENGINE_EVENT):]
    from . import enginedocs as ED
    e = None
    for g in (game, "medieval2", "rome"):
        e = ED.catalogue(g, mod)["events"].get(name)
        if e is not None:
            break
    if e is None:
        return Event(when, "%s (an engine event)" % name, name, (), "an event neither engine's list knows")
    brings = ", ".join(e.needs) or "nothing"
    return Event(when, "%s (an engine event)" % name, name, ED.subjects_of(e),
                 (e.desc.rstrip(".") + " - " if e.desc else "") + "one of the engines' own events (it brings: %s)"
                 % brings)

# faction picks: who a condition asks about / who an action gives to
WHO_IS = [("player", "the player"), ("computer", "a computer faction"), ("these", "one of these factions")]
TO = [("this", "the faction"), ("old", "the old owner"), ("player", "the player"), ("rebels", "the rebels"),
      ("named", "this faction:")]
OPS = [("<", "is below"), (">", "is above"), ("<=", "is at most"), (">=", "is at least"), ("==", "is")]
TURN_OPS = OPS + [("every", "is a multiple of")]
COUNT_OPS = {"<": "fewer than", ">": "more than", "<=": "at most", ">=": "at least", "==": "exactly"}
STANCES = [("war", "war"), ("neutral", "neutral"), ("allied", "allied")]


class Part:
    """One condition or action: its key, plain label, the subjects it needs and its fields.
    fields: [(name, kind, label, default)] - kind: 'int', 'signed', 'percent', 'text', 'long' (a longer text),
    'op', 'turn_op', 'who', 'to', 'stance', 'names:<what>' (a list from the mod: factions, towns, units, chains,
    levels, traits, ancillaries), 'name:<what>' (one name), 'cond' (a condition line of the engines' list) or
    'cmd:console' / 'cmd:commands' (a console / campaign-script command line of the engines' list)."""

    def __init__(self, key, label, needs, fields, help=""):
        self.key, self.label, self.needs, self.fields, self.help = key, label, needs, fields, help


CONDITIONS = [
    Part("who", "the faction is", (F,), [("v", "who", "", "player"), ("names", "names:factions", "factions", [])]),
    Part("money", "its money", (F,), [("op", "op", "", "<"), ("v", "signed", "denarii", 0)]),
    Part("towns", "its number of towns", (F,), [("op", "op", "", "<"), ("v", "int", "towns", 3)]),
    Part("turn", "the turn", (), [("op", "turn_op", "", ">="), ("v", "int", "turn", 10)],
         "the campaign's turn number, from 1"),
    Part("chance", "a chance of", (), [("v", "percent", "%", 10)], "a roll each time it happens"),
    Part("people", "the town's people", (S,), [("op", "op", "", ">"), ("v", "int", "people", 24000)]),
    Part("town_is", "the town is one of", (S,), [("names", "names:towns", "towns", [])]),
    Part("capital", "the town is the faction's capital", (S, F), []),
    Part("has_chain", "the town has a building of", (S,), [("v", "name:chains", "chain", "")],
         "a building chain of export_descr_buildings.txt"),
    Part("old_owner", "the old owner is", (T,), [("v", "who", "", "computer"),
                                                 ("names", "names:factions", "factions", [])]),
    Part("counter", "a remembered number", (), [("name", "counter", "named", "my_count"), ("op", "op", "", ">="),
                                                ("v", "signed", "", 1)],
         "a number the module keeps between turns (DO 'remember a number' / 'add to a remembered number' set it) - "
         "0 until set; the engines keep it as an event counter, so campaign_script's I_EventCounter reads it too; "
         "{faction} {town} in its name make one number per faction / town"),
    Part("game", "a game condition (any of the engine's)", (), [("line", "cond", "condition", "")],
         "any condition of the engines' own list (Pick... shows them all), checked against what just happened - "
         "like I_TurnNumber > 5, FactionType england, SettlementName London, Trait GoodCommander > 0; 'not' in "
         "front turns it round; {town} {faction} {owner} {general} {turn} {people} are filled in"),
]
CONDITION = {c.key: c for c in CONDITIONS}

ACTIONS = [
    Part("money", "give money", (), [("amount", "signed", "denarii", 1000), ("to", "to", "to", "this"),
                                     ("faction", "name:factions", "", "")],
         "below 0 takes money"),
    Part("people", "add people to the town", (S,), [("amount", "signed", "people", 1000)],
         "below 0 takes people (the town never goes under its level's minimum)"),
    Part("people_pct", "the town loses a share of its people", (S,), [("pct", "percent", "%", 10)]),
    Part("people_max", "the town keeps at most", (S,), [("max", "int", "people", 6000)],
         "people over it are gone; fewer stay as they are (a ceiling, like Avoid Growth)"),
    Part("build", "build in the town", (S,), [("level", "name:levels", "building level", "")],
         "a building level of export_descr_buildings.txt (its chain must suit the town)"),
    Part("tear_down", "tear down in the town", (S,), [("chain", "name:chains", "chain", "")],
         "the whole chain; the governor's buildings (core_...) are never torn down"),
    Part("units", "new units in the town", (S,), [("unit", "name:units", "unit", ""), ("count", "int", "units", 1)],
         "units of export_descr_unit.txt join the town's garrison"),
    Part("give_town", "give the town to", (S,), [("to", "to", "", "rebels"), ("faction", "name:factions", "", "")]),
    Part("stance", "set relations between", (), [("a", "to", "", "this"), ("faction", "name:factions", "", ""),
                                                 ("b", "to", "and", "player"),
                                                 ("faction_b", "name:factions", "", ""),
                                                 ("stance", "stance", "to", "war")]),
    Part("trait", "give the general a trait", (C,), [("trait", "name:traits", "trait", ""),
                                                     ("level", "int", "level", 1)]),
    Part("ancillary", "give the general a retinue member", (C,), [("anc", "name:ancillaries", "", "")]),
    Part("counter_set", "remember a number", (), [("v", "signed", "", 0), ("name", "counter", "named", "my_count")],
         "kept between turns and in the saved game; IF 'a remembered number' reads it"),
    Part("counter_add", "add to a remembered number", (), [("v", "signed", "", 1),
                                                          ("name", "counter", "named", "my_count")],
         "below 0 takes away; a number never set starts at 0"),
    Part("message", "show a message", (), [("title", "text", "title", ""), ("body", "long", "text", "")],
         "the game's own event scroll, to the player"),
    Part("log", "write a line in the game's log", (), [("text", "text", "", "")],
         "{town} {faction} {owner} {general} {turn} {people} are filled in"),
    Part("console", "run a console command (for experts)", (), [("text", "cmd:console", "command", "")],
         "any command of the game's console (Pick... shows them all), like add_money egypt 500 or kill_character "
         "\"{general}\" Battle - {town} {faction} {owner} {general} {turn} {people} are filled in"),
    Part("script", "run a campaign-script command (for experts)", (), [("text", "cmd:commands", "command", "")],
         "any one-line command of campaign_script.txt (Pick... shows them all), like give_trait or "
         "set_event_counter - {town} {faction} {owner} {general} {turn} {people} are filled in"),
]
ACTION = {a.key: a for a in ACTIONS}
PLACEHOLDERS = ("town", "faction", "owner", "general", "turn", "people")

BUILT_IN = ("sack_settlement", "raze_settlement", "avoid_growth", "player_diplomacy")


# ---------------------------------------------------------------------------
# A recipe: a plain dict, kept in the script as JSON
# ---------------------------------------------------------------------------
def new_recipe(title="My module"):
    return {"v": 1, "title": title, "game": "both", "when": "faction_turn", "once": False, "ifs": [], "dos": [],
            "settings": {}}


def item(kind, key, **values):
    """A condition (kind 'if') or action ('do') with its fields' defaults, overridden by values."""
    part = (CONDITION if kind == "if" else ACTION)[key]
    out = {"k": key}
    for name, _, _, default in part.fields:
        out[name] = values.get(name, list(default) if isinstance(default, list) else default)
    return out


def key_of(title):
    """The add-on's key and file name stem: the title in lower-case words joined by _."""
    k = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40] or "my_module"
    return k if k[0].isalpha() else "m_" + k


def var_of(label, taken=()):
    """A setting's variable: MB_ and the label's words in capitals, unique among taken."""
    base = "MB_" + (re.sub(r"[^A-Z0-9]+", "_", label.upper()).strip("_")[:36] or "VALUE")
    v, n = base, 2
    while v in taken:
        v, n = "%s_%d" % (base, n), n + 1
    return v


def setting_vars(recipe):
    """{path ('dos.0.amount'): (var, label)} for the values made settings, in recipe order."""
    out, taken = {}, {"MB_ON", "MB_ONCE"}
    for path, label in recipe.get("settings", {}).items():
        v = var_of(label, taken)
        taken.add(v)
        out[path] = (v, label)
    return out


def field_kind(recipe, path):
    """The field kind of a path like 'dos.0.amount', or None."""
    try:
        group, idx, name = path.split(".")
        it = recipe[group][int(idx)]
        part = (CONDITION if group == "ifs" else ACTION)[it["k"]]
        return next(k for n, k, _, _ in part.fields if n == name)
    except (ValueError, KeyError, IndexError, StopIteration):
        return None


SETTABLE = ("int", "signed", "percent", "text", "long")


def settable(recipe):
    """[(path, plain words)] - every value of the recipe that may be made a setting (numbers and texts)."""
    out = []
    for group in ("ifs", "dos"):
        for i, it in enumerate(recipe.get(group, [])):
            part = (CONDITION if group == "ifs" else ACTION).get(it.get("k"))
            if part is None:
                continue
            for name, kind, label, _ in part.fields:
                if kind in SETTABLE:
                    out.append(("%s.%d.%s" % (group, i, name), "%s - %s" % (part.label, label) if label else
                                part.label))
    return out


# ---------------------------------------------------------------------------
# Plain words
# ---------------------------------------------------------------------------
def _who(it, field="v", names="names"):
    v = it.get(field)
    if v == "these":
        return "one of " + (", ".join(it.get(names) or []) or "(no faction picked)")
    return dict(WHO_IS).get(v, v)


def _to(it, field="to", name="faction"):
    v = it.get(field)
    if v == "named":
        return it.get(name) or "(no faction picked)"
    return dict(TO).get(v, v)


def condition_words(it):
    k = it["k"]
    if k == "who":
        return "the faction is " + _who(it)
    if k == "old_owner":
        return "the town's old owner is " + _who(it)
    if k == "money":
        return "its money %s %s" % (dict(OPS)[it["op"]], it["v"])
    if k in ("towns", "people"):
        return "%s %s %s %s" % ("the faction has" if k == "towns" else "the town has", COUNT_OPS[it["op"]], it["v"],
                                "town(s)" if k == "towns" else "people")
    if k == "turn":
        return ("the turn is a multiple of %s" % it["v"]) if it["op"] == "every" else \
            "the turn %s %s" % (dict(OPS)[it["op"]], it["v"])
    if k == "chance":
        return "a %s %% chance comes up" % it["v"]
    if k == "town_is":
        return "the town is " + (" or ".join(it.get("names") or []) or "(no town picked)")
    if k == "capital":
        return "the town is the faction's capital"
    if k == "has_chain":
        return "the town has a %s building" % (it.get("v") or "(no chain picked)")
    if k == "game":
        return "the game's condition '%s' holds" % (it.get("line") or "(none written)")
    if k == "counter":
        return "the number '%s' %s %s" % (it.get("name") or "?", dict(OPS).get(it.get("op"), it.get("op")), it.get("v"))
    return k


def action_words(it):
    k = it["k"]
    if k == "money":
        n = it["amount"]
        return ("%s gets %s denarii" if int(n or 0) >= 0 else "%s pays %s denarii") % (
            _to(it), abs(int(n or 0)))
    if k == "people":
        n = int(it["amount"] or 0)
        return "the town %s %d people" % ("gains" if n >= 0 else "loses", abs(n))
    if k == "people_pct":
        return "the town loses %s %% of its people" % it["pct"]
    if k == "people_max":
        return "the town keeps at most %s people" % it["max"]
    if k == "build":
        return "the town gets the building %s" % (it["level"] or "(none picked)")
    if k == "tear_down":
        return "the town's %s buildings are torn down" % (it["chain"] or "(none picked)")
    if k == "units":
        return "%s new unit(s) of %s join the town" % (it["count"], it["unit"] or "(none picked)")
    if k == "give_town":
        return "the town goes to " + _to(it)
    if k == "stance":
        return "%s and %s are at %s" % (_to(it, "a", "faction"), _to(it, "b", "faction_b"), it["stance"]) \
            if it["stance"] == "war" else "%s and %s are %s" % (_to(it, "a", "faction"), _to(it, "b", "faction_b"),
                                                               it["stance"])
    if k == "trait":
        return "the general gets the trait %s (level %s)" % (it["trait"] or "(none picked)", it["level"])
    if k == "ancillary":
        return "the general gets %s in his retinue" % (it["anc"] or "(none picked)")
    if k == "message":
        return "the player sees the message '%s'" % (it["title"] or "(no title)")
    if k == "log":
        return "the game's log gets the line '%s'" % it["text"]
    if k == "console":
        return "the console runs '%s'" % it["text"]
    if k == "script":
        return "the campaign script runs '%s'" % it["text"]
    if k == "counter_set":
        return "the number '%s' becomes %s" % (it.get("name") or "?", it.get("v"))
    if k == "counter_add":
        n = it.get("v")
        neg = isinstance(n, int) and n < 0
        return "the number '%s' %s by %s" % (it.get("name") or "?", "goes down" if neg else "goes up",
                                             abs(n) if isinstance(n, int) else n)
    return k


def plain_words(recipe):
    """The whole module in one sentence or two."""
    ev = event_of(recipe.get("when"), recipe.get("game", "both"))
    head = "When %s" % (ev.label if ev else "(nothing picked)")
    ifs = [condition_words(i) for i in recipe.get("ifs", [])]
    dos = [action_words(a) for a in recipe.get("dos", [])]
    text = head + (", if " + " and ".join(ifs) if ifs else "") + ": " + ("; ".join(dos) if dos else "nothing yet") + "."
    if recipe.get("once"):
        text += " Only once in a campaign."
    return text[0].upper() + text[1:]


# ---------------------------------------------------------------------------
# Problems
# ---------------------------------------------------------------------------
def mod_names(mod, what):
    """The names of the mod a field picks from: factions, towns (settlement names), regions, units, chains, levels,
    traits, ancillaries, characters (the named ones of the campaign's start). [] when the file is not there."""
    from . import addons as AD
    try:
        if what in ("factions", "units", "chains"):
            return AD.mod_names(mod, what)
        if what == "levels":
            from .buildings import read_buildings
            return [lv.name for b in read_buildings(mod.load(mod.file("edb"))) for lv in b.levels]
        if what in ("towns", "regions"):
            from .masstown import towns
            camp = next(iter(mod.campaigns()), None)
            return [t["name" if what == "towns" else "region"] for t in towns(mod, camp)] if camp else []
        if what == "characters":                     # the named characters of the campaign's start
            from .strat import Strat
            camp = next(iter(mod.campaigns()), None)
            s = Strat(mod.load(mod.campaign_file(camp, "descr_strat.txt"))) if camp else None
            return [ch.name for fb in (s.factions if s else []) for ch in fb.characters if ch.named and ch.name]
        if what in ("traits", "ancillaries"):
            from . import traitsedit as TE
            kind = "trait" if what == "traits" else "ancillary"
            p = TE.file_of(mod, kind)
            return list(TE.blocks(mod.load(p), kind)) if p else []
    except Exception:
        return []
    return []


def problems(recipe, mod=None, names=None):
    """[plain words] - what keeps the recipe from being a working module (empty = fine). With the mod, the names it
    picks are checked against the mod's files (names: a function what -> [names] that answers instead, the window's
    cache)."""
    out = []
    title = (recipe.get("title") or "").strip()
    if not title:
        out.append("give the module a name")
    elif key_of(title) in BUILT_IN:
        out.append("'%s' is the name of a built-in add-on - pick another" % title)
    ev = event_of(recipe.get("when"), recipe.get("game", "both"), mod)
    if ev is None:
        out.append("WHEN: pick what happens")
        return out
    if not recipe.get("dos"):
        out.append("DO: add at least one action")
    game = recipe.get("game", "both")
    brings = event_subjects(ev, game, mod)
    if brings is None:
        only = [g for g in ("rome", "medieval2") if event_subjects(ev, g, mod) is not None]
        out.append("WHEN: '%s' is not an event of %s%s" % (
            ev.label, GAME_ENGINES.get(game, game), " - make the module for %s only, or pick another" % (
                "Rome" if only == ["rome"] else "Medieval II") if len(only) == 1 else ""))
        brings = ev.subjects
    have = set(brings)
    names_cache = {}

    def known(what):
        if what not in names_cache:
            got = names(what) if names is not None else mod_names(mod, what) if mod is not None else []
            names_cache[what] = {n.lower() for n in got}
        return names_cache[what]

    for group, table, word in (("ifs", CONDITION, "IF"), ("dos", ACTION, "DO")):
        for n, it in enumerate(recipe.get(group, []), 1):
            part = table.get(it.get("k"))
            if part is None:
                out.append("%s %d: unknown (%s)" % (word, n, it.get("k")))
                continue
            for need in part.needs:
                if need not in have:
                    out.append("%s %d (%s): '%s' brings no %s - pick another WHEN or take this out"
                               % (word, n, part.label, ev.label, SUBJECT_WORDS[need].split(" ", 1)[1]))
            for name, kind, label, _ in part.fields:
                v = it.get(name)
                what = label or name
                if kind in ("int", "percent", "signed"):
                    if not isinstance(v, int) or isinstance(v, bool):
                        out.append("%s %d (%s): %s must be a whole number" % (word, n, part.label, what))
                    elif kind == "int" and v < 0:
                        out.append("%s %d (%s): %s is 0 or more" % (word, n, part.label, what))
                    elif kind == "percent" and not 1 <= v <= 100:
                        out.append("%s %d (%s): a share from 1 to 100" % (word, n, part.label))
                if kind in ("text", "long") and part.key in ("message", "log") and \
                        not str(v or "").strip() and (part.key != "message" or name == "title"):
                    out.append("%s %d (%s): write the %s" % (word, n, part.label, label or "text"))
                if kind == "counter" and not RE_COUNTER.match(str(v or "")):
                    out.append("%s %d (%s): name the number with letters, digits and _ (and {faction}, {town} ...)"
                               % (word, n, part.label))
                if kind == "cond" or kind.startswith("cmd:"):
                    if not str(v or "").strip():
                        out.append("%s %d (%s): write the %s - or Pick... one" % (word, n, part.label,
                                                                                   label or "line"))
                    else:
                        out += ["%s %d (%s): %s" % (word, n, part.label, x)
                                for x in line_problems(kind, str(v), recipe, ev, mod)]
                if kind == "to" and v == "old" and T not in have:
                    out.append("%s %d (%s): '%s' has no old owner" % (word, n, part.label, ev.label))
                if kind.startswith("name:"):
                    pick = kind.split(":")[1]
                    needed = not (pick == "factions" and _faction_field_unused(part, it, name))
                    if needed and not str(v or "").strip():
                        out.append("%s %d (%s): pick the %s" % (word, n, part.label, label or pick[:-1]))
                    elif needed and known(pick) and str(v).lower() not in known(pick):
                        out.append("%s %d (%s): %s is not in this mod" % (word, n, part.label, v))
                if kind.startswith("names:") and it.get("v") == "these" and not v:
                    out.append("%s %d (%s): pick at least one" % (word, n, part.label))
                if kind == "names:towns" and not v:
                    out.append("%s %d (%s): pick at least one town" % (word, n, part.label))
                if kind.startswith("names:") and v:
                    pick = kind.split(":")[1]
                    wrong = [x for x in v if known(pick) and x.lower() not in known(pick)]
                    if wrong:
                        out.append("%s %d (%s): %s not in this mod" % (word, n, part.label, ", ".join(wrong)))
    for path in recipe.get("settings", {}):
        if field_kind(recipe, path) not in SETTABLE:
            out.append("a setting points at nothing (%s) - tick it again" % path)
    return out


LINE_KIND = {"cond": "conditions", "cmd:console": "console", "cmd:commands": "commands"}
RE_COUNTER = re.compile(r"^(?:[A-Za-z0-9_]|\{(?:%s)\})+$" % "|".join(PLACEHOLDERS))


def event_subjects(ev, game="both", mod=None):
    """What the event brings along for a module of game ('both': what BOTH engines' payloads carry - REX's town
    taken has no old owner, its unit trained no unit), by the engines' own event list; None when the engine(s) have no
    such event (REX has no SettlementUpgraded). Without the editor's list: the event's own subjects."""
    from . import enginedocs as ED
    events = ED.catalogue(game, mod)["events"]
    if not events:
        return ev.subjects
    e = events.get(ev.engine)
    if e is None:
        return None
    got = set(ED.subjects_of(e))
    return tuple(x for x in ev.subjects if x in got)
GAME_ENGINES = {"both": "REX and M2EX (both must have it)", "rome": "REX", "medieval2": "M2EX"}


def line_problems(kind, line, recipe, ev=None, mod=None):
    """[plain words] wrong with a condition / command line by the engines' own list: a name neither engine has (for a
    module of both games: one engine lacks), one the engine marks not implemented, a console command of battles only,
    a block command (if ... end_if), a condition of battles only or one needing what the event does not bring. Its
    parameters are not checked here (the engine says in the game's log when it cannot read them)."""
    from . import enginedocs as ED
    what = LINE_KIND[kind]
    game = recipe.get("game", "both")
    cat = ED.catalogue(game, mod)
    have = cat[what]
    if not have:                                      # the editor's list is missing: nothing to check against
        return []
    name = ED.first_word(line)
    e = have.get(name)
    if e is None:
        low = {k.lower(): k for k in have}
        if name.lower() in low:
            return ["write it %s (the engines tell the letters apart)" % low[name.lower()]]
        return ["%s is not one of the %s of %s" % (name, ED.KIND_WORDS[what], GAME_ENGINES.get(game, game))]
    if not e.works:
        return ["the engine marks %s as not implemented - it would do nothing" % name]
    if not e.runnable():
        if what == "console":
            return ["%s works only in %s, not on the campaign map" % (name, e.where or "battles")]
        if what == "commands":
            return ["%s belongs to the flow of campaign_script.txt (a block, a jump or a wait) - a module does "
                    "that itself: its IF lines, and each event that fires" % name]
        return ["%s is checked only in battle" % name]
    if what == "conditions" and ev is not None:
        miss = ED.missing(e, cat["events"].get(ev.engine))
        if miss:
            return ["%s needs %s, which '%s' does not bring" % (name, " and ".join(miss), ev.label)]
    return []


def _faction_field_unused(part, it, name):
    """A faction name field matters only when its 'to' field says 'this faction:' (named)."""
    pairs = {"faction": "to", "faction_b": "b"}
    if part.key == "stance":
        pairs = {"faction": "a", "faction_b": "b"}
    other = pairs.get(name)
    return other is not None and it.get(other) != "named"


# ---------------------------------------------------------------------------
# The script
# ---------------------------------------------------------------------------
def _sq(v):
    """A Squirrel literal."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_sq(x) for x in v) + "]"
    return '"%s"' % str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def message_id(key, n):
    """The custom_messages.txt id of the module's n-th message (n from 1)."""
    return "%s_msg%d" % (key, n)


def script(recipe):
    """The add-on script (.nut) for a recipe. Raises ValueError when the recipe has problems (no mod check here)."""
    bad = problems(recipe)
    if bad:
        raise ValueError("; ".join(bad))
    title = recipe["title"].strip()
    key = key_of(title)
    ev = event_of(recipe["when"], recipe.get("game", "both"))
    sv = setting_vars(recipe)
    words = plain_words(recipe)

    def val(group, i, name, value):
        path = "%s.%d.%s" % (group, i, name)
        return sv[path][0] if path in sv else _sq(value)

    lines = [
        "// " + "=" * 76,
        "// %s - made with the Module builder of RTW & M2TW Campaign Editor" % title,
        "// " + words,
        "// For REX (Rome: Total War) and M2EX (Medieval II: Total War): put this file in",
        "// <the game's folder>\\script\\modules\\ - the engine loads it when the campaign starts.",
        "// Log lines start with \"[%s]\"." % key.upper(),
        "// " + "=" * 76,
        "// @title " + title,
        "// @game " + recipe.get("game", "both"),
        "// @summary " + words,
        "// @needs REX (Rome) or M2EX (Medieval II): the script goes into the game's script/modules, which they load by "
        "themselves. The original exes run no scripts.",
        "// @settings " + ", ".join(["MB_ON", "MB_ONCE"] + [v for v, _ in sv.values()]),
        "// @label MB_ON Module on",
        "// @label MB_ONCE Only once in a campaign",
    ]
    lines += ["// @label %s %s" % (v, label) for v, label in sv.values()]
    signed = [v for path, (v, _) in sv.items() if field_kind(recipe, path) == "signed"]
    if signed:
        lines.append("// @signed " + ", ".join(signed))
    lines.append("// @recipe " + json.dumps(recipe, ensure_ascii=True, separators=(",", ":")))
    lines += ["", 'local PREFIX = "[%s] "' % key.upper(),
              "local MB_ON = true                   // off keeps the file but does nothing",
              "local MB_ONCE = %s                  // it acts once in a campaign, then never again" % _sq(
                  bool(recipe.get("once")))]
    for path, (v, label) in sv.items():
        group, i, name = path.split(".")
        lines.append("local %s = %s        // %s" % (v, _sq(recipe[group][int(i)][name]), label))
    lines += ["local mb_key = %s" % _sq(key), ""]
    lines += LIBRARY.splitlines()
    lines += ["", "local function mb_run(e) {", "    if (!MB_ON) {", "        return", "    }",
              "    local c = mb_context(e)"]
    for i, it in enumerate(recipe.get("ifs", [])):
        lines += ["    if (!(%s)) {" % _cond_code(it, i, val), "        return", "    }   // " + condition_words(it)]
    lines += ["    if (MB_ONCE && mb_done()) {", "        return", "    }",
              '    mb_log("acts: " + mb_where(c))']
    msg = 0
    for i, it in enumerate(recipe.get("dos", [])):
        if it["k"] == "message":
            msg += 1
        lines.append("    try {")
        lines += ["        " + l for l in _act_code(it, i, val, key, msg)]
        lines += ["    } catch (err) {", '        mb_log("%s failed: " + err)' % action_words(it).replace('"', "'"),
                  "    }"]
    lines += ["    if (MB_ONCE) {", "        mb_mark_done()", "    }", "}", "",
              'mb_listen("%s", mb_run)' % ev.engine,
              'mb_listen("GameReloaded", function(...) { mb_faction_cache = {} })',
              'mb_log("%s module loaded")' % title.replace('"', "'"), ""]
    return "\n".join(lines)


def _faction_expr(it, field, name_field):
    v = it.get(field)
    if v == "this":
        return "c.faction"
    if v == "old":
        return "c.target"
    if v == "player":
        return "mb_player()"
    if v == "rebels":
        return 'mb_faction("slave")'
    return "mb_faction(%s)" % _sq(it.get(name_field) or "")


def _cond_code(it, i, val):
    k = it["k"]
    v = lambda name: val("ifs", i, name, it[name])
    if k in ("who", "old_owner"):
        subj = "c.faction" if k == "who" else "c.target"
        if it["v"] == "player":
            return "mb_is_player(%s)" % subj
        if it["v"] == "computer":
            return "%s != null && !mb_is_player(%s)" % (subj, subj)
        return "mb_in(mb_name(%s), %s)" % (subj, _sq(it.get("names") or []))
    if k == "money":
        return "mb_cmp(mb_money(c.faction), %s, %s)" % (_sq(it["op"]), v("v"))
    if k == "towns":
        return "mb_cmp(mb_towns(c.faction), %s, %s)" % (_sq(it["op"]), v("v"))
    if k == "people":
        return "mb_cmp(mb_people(c.settlement), %s, %s)" % (_sq(it["op"]), v("v"))
    if k == "turn":
        return "mb_cmp(mb_turn(), %s, %s)" % (_sq(it["op"]), v("v"))
    if k == "chance":
        return "mb_chance(%s)" % v("v")
    if k == "town_is":
        return "mb_in(mb_name(c.settlement), %s)" % _sq(it.get("names") or [])
    if k == "capital":
        return "mb_is_capital(c.settlement, c.faction)"
    if k == "has_chain":
        return "mb_has_chain(c.settlement, %s)" % _sq(it["v"])
    if k == "game":
        return "mb_condition(mb_fill(%s, c))" % _sq(it["line"].strip())
    if k == "counter":
        return "mb_cmp(mb_counter(mb_fill(%s, c)), %s, %s)" % (_sq(it["name"]), _sq(it["op"]), v("v"))
    raise ValueError("unknown condition %s" % k)


def _act_code(it, i, val, key, msg):
    k = it["k"]
    v = lambda name: val("dos", i, name, it[name])
    if k == "money":
        return ["mb_add_money(%s, %s)" % (_faction_expr(it, "to", "faction"), v("amount"))]
    if k == "people":
        return ["mb_add_people(c.settlement, %s)" % v("amount")]
    if k == "people_pct":
        return ["mb_lose_share(c.settlement, %s)" % v("pct")]
    if k == "people_max":
        return ["mb_cap_people(c.settlement, %s)" % v("max")]
    if k == "build":
        return ['mb_console("create_building", mb_name(c.settlement) + " " + %s)' % _sq(it["level"])]
    if k == "tear_down":
        return ["mb_tear_down(c.settlement, %s)" % _sq(it["chain"])]
    if k == "units":
        return ['mb_console("create_unit", mb_name(c.settlement) + " " + mb_quoted(%s) + " " + %s)'
                % (_sq(it["unit"]), v("count"))]
    if k == "give_town":
        return ["mb_give_town(c.settlement, %s)" % _faction_expr(it, "to", "faction")]
    if k == "stance":
        return ['mb_console("diplomatic_stance", mb_name(%s) + " " + mb_name(%s) + " " + %s)'
                % (_faction_expr(it, "a", "faction"), _faction_expr(it, "b", "faction_b"), _sq(it["stance"]))]
    if k == "trait":
        return ['mb_console("give_trait", mb_quoted(mb_general_name(c.character)) + " " + %s + " " + %s)'
                % (_sq(it["trait"]), v("level"))]
    if k == "ancillary":
        return ['mb_console("give_ancillary", mb_quoted(mb_general_name(c.character)) + " " + %s)' % _sq(it["anc"])]
    if k == "message":
        return ["mb_message(%s, %s)" % (_sq(message_id(key, msg)), v("title"))]
    if k == "log":
        return ["mb_log(mb_fill(%s, c))" % v("text")]
    if k == "console":
        return ["mb_console_line(mb_fill(%s, c))" % v("text")]
    if k == "script":
        return ["mb_script_line(mb_fill(%s, c))" % v("text")]
    if k == "counter_set":
        return ["mb_set_counter(mb_fill(%s, c), %s)" % (_sq(it["name"]), v("v"))]
    if k == "counter_add":
        return ["mb_set_counter(mb_fill(%s, c), mb_counter(mb_fill(%s, c)) + %s)" % (_sq(it["name"]), _sq(it["name"]),
                                                                                      v("v"))]
    raise ValueError("unknown action %s" % k)


# The helpers every module carries: local functions only (no names left in the game's root table, so two modules
# never step on each other); every engine call in a try - a field one engine lacks reads as nothing.
LIBRARY = r'''
local function mb_log(message) {
    println(PREFIX + message)
}

local function mb_get(o, field) {
    if (o == null) {
        return null
    }
    try {
        return o[field]
    } catch (err) {
    }
    return null
}

local function mb_name(o) {
    local n = mb_get(o, "name")
    return n == null ? "" : n
}

local function mb_is_player(f) {
    local v = mb_get(f, "isPlayerControlled")
    return v == true || v == 1
}

local function mb_in(name, list) {
    foreach (x in list) {
        if (x == name) {
            return true
        }
    }
    return false
}

local function mb_cmp(a, op, b) {
    if (a == null) {
        return false
    }
    if (op == "<") {
        return a < b
    }
    if (op == ">") {
        return a > b
    }
    if (op == "<=") {
        return a <= b
    }
    if (op == ">=") {
        return a >= b
    }
    if (op == "every") {
        return b > 0 && a % b == 0
    }
    return a == b
}

local mb_faction_cache = {}
local function mb_faction(name) {
    if (name in mb_faction_cache) {
        return mb_faction_cache[name]
    }
    local n = 0
    try {
        n = ::game.factionCount()
    } catch (err) {
    }
    for (local i = 0; i < n; i++) {
        local f = null
        try {
            f = ::game.faction(i)
        } catch (err) {
        }
        if (f != null && mb_name(f) == name) {
            mb_faction_cache[name] <- f
            return f
        }
    }
    return null
}

local function mb_player() {
    try {
        return ::game.localFaction()
    } catch (err) {
    }
    return null
}

local function mb_money(f) {
    local m = mb_get(f, "money")
    return m != null ? m : mb_get(f, "treasury")
}

local function mb_towns(f) {
    return mb_get(f, "settlementCount")
}

local function mb_people(s) {
    return mb_get(s, "population")
}

local function mb_turn() {
    try {
        local c = ::game.campaign()
        local t = mb_get(c, "turnNumber")
        if (t != null) {
            return t + 1                     // the engine counts from 0, the player from 1
        }
    } catch (err) {
    }
    return null
}

local mb_seed = 0
local function mb_chance(pct) {
    if (mb_seed == 0) {
        mb_seed = 12345
        try {
            mb_seed = (::game.campaign().millisecondCount % 2147483647) + 1
        } catch (err) {
        }
    }
    mb_seed = (mb_seed * 1103515245 + 12345) & 0x7fffffff
    return (mb_seed / 65536) % 100 < pct
}

local function mb_is_capital(s, f) {
    local cap = mb_get(f, "capital")
    if (cap == null || s == null) {
        return false
    }
    return cap == s || mb_name(cap) == mb_name(s)
}

local function mb_has_chain(s, chain) {
    if (s == null) {
        return false
    }
    local n = 0
    try {
        n = s.buildingCount
    } catch (err) {
    }
    for (local i = 0; i < n; i++) {
        try {
            if (s.building(i).chainName == chain) {
                return true
            }
        } catch (err) {
        }
    }
    return false
}

local function mb_general_name(ch) {
    foreach (o in [ch, mb_get(ch, "characterRecord")]) {
        foreach (f in ["fullName", "name"]) {
            local n = mb_get(o, f)
            if (n != null && n != "") {
                return n
            }
        }
    }
    return ""
}

local function mb_quoted(text) {
    foreach (i, ch in text) {
        if (ch == ' ') {
            return "\"" + text + "\""
        }
    }
    return text
}

// One dev-console verb; the console's reply goes to the log.
local function mb_console(verb, rest) {
    try {
        local reply = ::game.runConsoleCommand(verb, rest)
        mb_log(verb + " " + rest + (reply != null && reply != "" ? " -> " + reply : ""))
        return true
    } catch (err) {
    }
    try {
        ::game.runScriptCommand("console_command", verb + " " + rest)
        mb_log("console_command " + verb + " " + rest)
        return true
    } catch (err) {
        mb_log(verb + " " + rest + " failed: " + err)
    }
    return false
}

local function mb_console_line(line) {
    local verb = line
    local rest = ""
    foreach (i, ch in line) {
        if (ch == ' ') {
            verb = line.slice(0, i)
            rest = line.slice(i + 1)
            break
        }
    }
    return mb_console(verb, rest)
}

// One condition line of the engines' own list (campaign_script's), checked against the event that fired.
local function mb_condition(line) {
    try {
        return ::game.evaluateCondition(line) == true
    } catch (err) {
        mb_log("condition '" + line + "' could not be checked: " + err)
    }
    return false
}

// One campaign-script command (one line) through the engine's own parser; what it did goes to the log.
local function mb_script_line(line) {
    local verb = line
    local rest = ""
    foreach (i, ch in line) {
        if (ch == ' ') {
            verb = line.slice(0, i)
            rest = line.slice(i + 1)
            break
        }
    }
    local ran = false
    try {
        ran = ::game.runScriptCommand(verb, rest)
    } catch (err) {
        mb_log(line + " failed: " + err)
        return false
    }
    mb_log(line + (ran == false ? " - the engine did not run it (check the line)" : ""))
    return ran != false
}

local function mb_add_money(f, n) {
    if (f == null) {
        mb_log("money: no such faction")
        return
    }
    local before = mb_money(f)
    try {
        f.money = before + n
    } catch (err) {
    }
    if (n != 0 && mb_money(f) == before) {
        mb_console("add_money", mb_name(f) + " " + n)
    }
    mb_log("money of " + mb_name(f) + ": " + before + " -> " + mb_money(f))
}

local function mb_set_people(s, n) {
    if (s == null) {
        return
    }
    local before = mb_people(s)
    try {
        s.population = n < 0 ? 0 : n           // the engine keeps the level's minimum
    } catch (err) {
    }
    if (mb_people(s) == before && n != before) {
        mb_console("set_population", mb_name(s) + " " + n)
    }
    mb_log(mb_name(s) + ": people " + before + " -> " + mb_people(s))
}

local function mb_add_people(s, n) {
    local now = mb_people(s)
    if (now != null) {
        mb_set_people(s, now + n)
    }
}

local function mb_lose_share(s, pct) {
    local now = mb_people(s)
    if (now != null) {
        mb_set_people(s, now - now * pct / 100)
    }
}

local function mb_cap_people(s, most) {
    local now = mb_people(s)
    if (now != null && now > most) {
        mb_set_people(s, most)
    }
}

local function mb_tear_down(s, chain) {
    if (s == null || chain.len() >= 4 && chain.slice(0, 4) == "core") {
        return                                   // the governor's buildings stay: the town needs them
    }
    try {
        s.destroyBuilding(chain, false)
        mb_log(mb_name(s) + ": " + chain + " torn down")
    } catch (err) {
        mb_log(mb_name(s) + ": " + chain + " not torn down: " + err)
    }
}

local function mb_give_town(s, f) {
    if (s == null || f == null) {
        mb_log("give the town: no town or no faction")
        return
    }
    local fname = mb_name(f)
    try {
        s.owner = f
    } catch (err) {
    }
    if (mb_name(mb_get(s, "owner")) != fname) {
        foreach (rest in [fname + ", " + mb_name(s), fname + " " + mb_name(s)]) {
            try {
                ::game.runScriptCommand("give_settlement", rest)
            } catch (err) {
            }
            if (mb_name(mb_get(s, "owner")) == fname) {
                break
            }
        }
    }
    mb_log(mb_name(s) + " now belongs to " + mb_name(mb_get(s, "owner")))
}

// The game's own event scroll with the module's text (the mod's text/custom_messages.txt), to the player.
local function mb_message(id, title) {
    mb_log("message: " + title)
    mb_console("display_message", id)
}

// {town} {faction} {owner} {general} {turn} {people} in a text filled in.
local function mb_fill(text, c) {
    local words = { town = mb_name(c.settlement), faction = mb_name(c.faction), owner = mb_name(c.target),
                    general = mb_general_name(c.character), turn = mb_turn(), people = mb_people(c.settlement) }
    local out = ""
    local i = 0
    local n = text.len()
    while (i < n) {
        local done = false
        if (text[i] == '{') {
            foreach (k, v in words) {
                local tag = "{" + k + "}"
                if (i + tag.len() <= n && text.slice(i, i + tag.len()) == tag) {
                    out += v == null ? "" : v.tostring()
                    i += tag.len()
                    done = true
                    break
                }
            }
        }
        if (!done) {
            out += text.slice(i, i + 1)
            i++
        }
    }
    return out
}

// What the event brought: the faction, the town, the general, the town's old owner, the unit.
local function mb_context(e) {
    local c = { faction = mb_get(e, "faction"), settlement = mb_get(e, "settlement"),
                character = mb_get(e, "character"), target = mb_get(e, "targetFaction"), unit = mb_get(e, "unit") }
    if (c.settlement == null) {
        c.settlement = mb_get(e, "targetSettlement")
    }
    if (c.character == null) {
        c.character = mb_get(e, "characterRecord")
    }
    local region = mb_get(e, "regionId")
    if (c.settlement == null && region != null) {
        try {
            c.settlement = ::stratMap.region(region).settlementAt(0)
        } catch (err) {
        }
    }
    if (c.faction == null && c.settlement != null) {
        c.faction = mb_get(c.settlement, "owner")
    }
    return c
}

local function mb_where(c) {
    local parts = []
    foreach (k in ["faction", "settlement", "target"]) {
        local n = mb_name(c[k])
        if (n != "") {
            parts.append(k == "settlement" ? "town " + n : k == "target" ? "old owner " + n : n)
        }
    }
    local out = ""
    foreach (i, p in parts) {
        out += (i > 0 ? ", " : "") + p
    }
    return out
}

// The saved game remembers a once-only module that has acted (persistent.<its key>).
local function mb_store() {
    local root = getroottable()
    if (!("persistent" in root) || typeof(root.persistent) != "table") {
        root.persistent <- {}
    }
    if (!(mb_key in root.persistent) || typeof(root.persistent[mb_key]) != "table") {
        root.persistent[mb_key] <- {}
    }
    return root.persistent[mb_key]
}

local function mb_done() {
    return "done" in mb_store()
}

local function mb_mark_done() {
    mb_store().done <- true
}

// A number kept between turns: the engines' own event counters (campaign_script's I_EventCounter reads them), and
// a copy in the module's table of the saved game for an engine that has none.
local function mb_counter(name) {
    try {
        local v = ::game.eventCounter(name)
        if (v != null) {
            return v
        }
    } catch (err) {
    }
    local t = mb_store()
    return ("n_" + name) in t ? t["n_" + name] : 0
}

local function mb_set_counter(name, v) {
    try {
        ::game.setEventCounter(name, v)
    } catch (err) {
        mb_log("setEventCounter(" + name + ") failed: " + err)
    }
    mb_store()["n_" + name] <- v
    mb_log("the number " + name + " is now " + v)
}

local function mb_listen(name, handler) {
    try {
        ::events.on(name, handler)
    } catch (err) {
        mb_log("events.on(" + name + ") failed: " + err)
    }
}
'''.strip("\n")


def recipe_of(text):
    """The recipe a builder-made script carries (its // @recipe line), or None."""
    m = re.search(r"^//\s*@recipe\s+(\{.*\})\s*$", text, re.M)
    if not m:
        return None
    try:
        r = json.loads(m.group(1))
    except ValueError:
        return None
    return r if isinstance(r, dict) and "when" in r else None


def messages(recipe, values=None):
    """[(id, title, body)] of the recipe's messages, with the settings' values when given ({var: value})."""
    values = values or {}
    sv = setting_vars(recipe)
    key = key_of(recipe.get("title") or "")
    out, n = [], 0
    for i, it in enumerate(recipe.get("dos", [])):
        if it.get("k") != "message":
            continue
        n += 1
        got = []
        for name in ("title", "body"):
            path = "dos.%d.%s" % (i, name)
            var = sv.get(path, (None,))[0]
            got.append(values.get(var, it.get(name, "")) if var else it.get(name, ""))
        out.append((message_id(key, n), got[0], got[1]))
    return out


MESSAGES_FILE = "custom_messages.txt"


def plan_messages(plan, mod, recipe, values=None):
    """The module's messages written into the mod's text/custom_messages.txt (<id> the title, <id>_body the text) -
    the file made in the encoding of the mod's other string tables when it is not there yet."""
    from .moddata import _ci
    msgs = messages(recipe, values)
    if not msgs:
        return None
    text = _ci(mod.data, "text") or os.path.join(mod.data, "text")
    path = _ci(text, MESSAGES_FILE) if os.path.isdir(text) else None
    entries = {}
    for mid, title, body in msgs:
        entries[mid] = title
        entries[mid + "_body"] = body or title
    if path:
        from .editors import set_text_values
        set_text_values(plan, path, entries)
        return path
    path = os.path.join(text, MESSAGES_FILE)
    # a mod in mods/<name> reads the game's own file when it has none: its copy starts from that one
    base = _game_messages(mod)
    lines = base.splitlines() if base else [
        "\u00ac Messages of the add-ons made with the Module builder (display_message <id>)", ""]
    low = {k.lower() for k in entries}
    lines = [l for l in lines if not (l.lstrip().startswith("{") and "}" in l and
                                      l.lstrip()[1:l.lstrip().index("}")].lower() in low)]
    lines += ["{%s}\t%s" % (k, v.replace("\n", "\\n")) for k, v in entries.items()]
    plan.binary(path, _table_bytes(text, "\r\n".join(lines) + "\r\n"))
    plan.note(None, "%s made%s: the module's messages" % (os.path.relpath(path, mod.data),
                                                          " (a copy of the game's own)" if base else ""))
    return path


def _game_messages(mod):
    """The text of the game's own data/text/custom_messages.txt when the mod is not the game's data, else None."""
    from .moddata import _ci
    try:
        from .newmod import game_of
        game = game_of(mod.data)
    except Exception:
        return None
    data = _ci(game, "data") if game else None
    if not data or os.path.abspath(data) == os.path.abspath(mod.data):
        return None
    t = _ci(data, "text")
    p = _ci(t, MESSAGES_FILE) if t else None
    if not p:
        return None
    with open(p, "rb") as fh:
        raw = fh.read()
    import codecs
    if raw.startswith(codecs.BOM_UTF16_LE):
        return raw[2:].decode("utf-16-le", "replace")
    return raw.decode("utf-8-sig", "replace")


def _table_bytes(folder, text):
    """A string table's bytes the way the folder's other tables are kept: UTF-16 LE with a BOM (the games' own),
    else UTF-8."""
    import codecs
    if os.path.isdir(folder):
        for n in sorted(os.listdir(folder)):
            if n.lower().endswith(".txt"):
                try:
                    with open(os.path.join(folder, n), "rb") as fh:
                        head = fh.read(2)
                except OSError:
                    continue
                if head == codecs.BOM_UTF16_LE:
                    break
                return text.encode("utf-8")
    return codecs.BOM_UTF16_LE + text.encode("utf-16-le")


# ---------------------------------------------------------------------------
# Kept in the editor's add-ons folder
# ---------------------------------------------------------------------------
def save(recipe):
    """The module's script written into the editor's add-ons folder (as <key>.nut); returns the Addon. A file of the
    same name that the builder did not make is never overwritten."""
    from . import addons as AD
    text = script(recipe)
    d = AD.library_dir()
    if not d:
        raise ValueError("the editor has no folder of its own to keep add-ons in")
    os.makedirs(d, exist_ok=True)
    name = key_of(recipe["title"]) + ".nut"
    path = os.path.join(d, name)
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            if recipe_of(fh.read().decode("utf-8", "replace")) is None:
                raise ValueError("%s is an add-on not made with the builder - give the module another name" % name)
    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))
    return AD.from_script(text, name, path)


def my_modules():
    """[(Addon, recipe)] of the builder-made add-ons in the editor's folder."""
    from . import addons as AD
    out = []
    for a in AD.library():
        if not a.own:
            continue
        try:
            r = recipe_of(a.template())
        except OSError:
            continue
        if r is not None:
            out.append((a, r))
    return out


# ---------------------------------------------------------------------------
# Examples to start from
# ---------------------------------------------------------------------------
def _ex(title, when, ifs, dos, settings=None, once=False, game="both"):
    r = new_recipe(title)
    r.update({"when": when, "ifs": ifs, "dos": dos, "settings": settings or {}, "once": once, "game": game})
    return r


EXAMPLES = [
    _ex("Help when broke", "faction_turn",
        [item("if", "who", v="player"), item("if", "money", op="<", v=0)],
        [item("do", "money", amount=3000, to="this"),
         item("do", "message", title="A loan", body="The treasury was empty: the money lenders give you 3000.")],
        {"dos.0.amount": "Amount of the loan"}),
    _ex("Loot for taking a town", "town_taken", [],
        [item("do", "money", amount=1500, to="this"), item("do", "log", text="{faction} took {town} and its loot")],
        {"dos.0.amount": "Loot for a town"}),
    _ex("Plague in big cities", "town_turn",
        [item("if", "people", op=">", v=24000), item("if", "chance", v=5)],
        [item("do", "people_pct", pct=10), item("do", "log", text="Plague in {town}: {people} people left")],
        {"ifs.0.v": "Cities bigger than", "ifs.1.v": "Chance each turn (%)", "dos.0.pct": "People lost (%)"}),
    _ex("A free unit when a barracks is built", "building_done",
        [item("if", "who", v="player"), item("if", "has_chain", v="")],
        [item("do", "units", unit="", count=1), item("do", "log", text="A new unit in {town}")],
        {"dos.0.count": "Free units"}),
    _ex("Gold for holding the capital", "town_turn",
        [item("if", "capital"), item("if", "who", v="player")],
        [item("do", "money", amount=300, to="this")], {"dos.0.amount": "Gold each turn"}),
    _ex("A message on turn 10", "faction_turn",
        [item("if", "who", v="player"), item("if", "turn", op="==", v=10)],
        [item("do", "message", title="Ten years of rule",
              body="Your people celebrate ten years of your rule.")],
        {"ifs.1.v": "On turn"}, once=True),
    _ex("Rebellion punished", "town_rebels", [],
        [item("do", "people_pct", pct=25), item("do", "log", text="{town} rebelled and was punished")],
        {"dos.0.pct": "People lost (%)"}),
    _ex("A trait for the conqueror", "town_taken",
        [item("if", "who", v="player")],
        [item("do", "trait", trait="", level=1), item("do", "log", text="{general} took {town}")]),
    _ex("Avoid Growth for chosen towns", "town_turn",
        [item("if", "town_is", names=[])],
        [item("do", "people_max", max=6000)], {"dos.0.max": "Most people"}),
]

# what fit_to_mod puts into an example's empty names: the first of these the mod has, else the mod's first name
PREFERRED = {"chains": ["barracks", "castle_barracks", "city_barracks"],
             "traits": ["GoodCommander", "GoodAttacker", "BattleScarred"]}


def _foot_unit(mod):
    """The mod's first plain foot soldiers (infantry, no general, mercenary or rebel-only unit), or None."""
    try:
        from .units import read_units
        for u in read_units(mod.load(mod.file("edu"))):
            own = [o for o in u.ownership if o not in ("slave",)]
            if u.category == "infantry" and own and not re.search(r"general|bodyguard|merc", u.type, re.I):
                return u.type
    except Exception:
        pass
    return None


def fit_to_mod(recipe, mod):
    """The recipe with its empty names filled from the mod (a barracks chain, a unit the town can hold, a trait, the
    player's first town) - an example made for any mod. Names already given stay."""
    import copy
    r = copy.deepcopy(recipe)
    for group, table in (("ifs", CONDITION), ("dos", ACTION)):
        for it in r.get(group, []):
            part = table.get(it.get("k"))
            for name, kind, _, _ in (part.fields if part else []):
                if kind.startswith("name:") and kind != "name:factions" and not it.get(name):
                    what = kind.split(":")[1]
                    have = mod_names(mod, what)
                    pick = next((x for x in PREFERRED.get(what, []) if x in have), None)
                    if what == "units":
                        pick = _foot_unit(mod)
                    it[name] = pick or (have[0] if have else "")
                if kind == "names:towns" and not it.get(name):
                    have = mod_names(mod, "towns")
                    it[name] = have[:1]
    return r


def example(title):
    return json.loads(json.dumps(next(r for r in EXAMPLES if r["title"] == title)))
