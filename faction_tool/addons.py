"""Add-ons: ready-made scripts that bring the game something new, put in with their settings chosen in the tool.

An add-on is a REX Squirrel module (script/modules/<name>.nut - REX require()s every file there once the campaign
is up, whatever mod runs). Its settings are the 'local NAME = value' lines at the top of the file; the tool writes
the chosen values into those lines and nothing else, so a later version of the add-on keeps the same shape.
Installing and removing go through a Plan like every write: a backup, and Restore undoes it."""

import os
import re
import sys

from .moddata import _ci


def assets_dir():
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets", "addons")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "addons")


class Setting:
    """One setting: the variable in the script, how it is shown and what it takes.
    kind: 'bool', 'int', 'text', 'choice' (choices = [(value, label)]), 'list' (Squirrel array of strings),
    'set' (Squirrel table of names = true, written one per line)."""

    def __init__(self, var, kind, label, help, choices=None, when=None):
        self.var, self.kind, self.label, self.help = var, kind, label, help
        self.choices = choices or []
        self.when = when            # (other var, [values]) - shown only then


WHO = [("player", "Only the player (the human)"),
       ("everyone", "Everyone - the player and every computer faction"),
       ("homeless", "Only factions without a town of their own (hordes, homeless) - player or computer"),
       ("player_and_homeless", "The player, and computer factions without a town (hordes)"),
       ("ai", "Only the computer's factions"),
       ("list", "Only the factions I pick")]


class Addon:
    def __init__(self, key, title, game, file, summary, settings, needs):
        self.key, self.title, self.game, self.file = key, title, game, file
        self.summary, self.settings, self.needs = summary, settings, needs

    def template(self):
        with open(os.path.join(assets_dir(), self.file), "rb") as f:
            return f.read().decode("utf-8")


ADDONS = [
    Addon("sack_settlement", "Sack Settlement", "rome", "sack_settlement.nut",
          "A 4th choice on the capture scroll, under Occupy / Enslave / Exterminate: Sack Settlement. The town is "
          "exterminated the game's own way, every building but the kept ones is torn down, you get a reward, and "
          "the ruins go to the rebels (with a rebel garrison the game raises itself) - land you do not want to hold "
          "is burned and left to regrow. The computer's factions allowed below sack when they exterminate.",
          [Setting("RAZE_ENABLED", "bool", "Sacking on", "off keeps the file but does nothing"),
           Setting("RAZE_WHO", "choice", "Who may sack", "the player picks it on the capture scroll; a computer "
                   "faction allowed here sacks whenever it exterminates a town", WHO),
           Setting("RAZE_FACTIONS", "list", "The factions", "for 'Only the factions I pick'",
                   when=("RAZE_WHO", ["list"])),
           Setting("RAZE_GIVE_TO_REBELS", "bool", "Ruins go to the rebels", "off: the sacked town stays yours"),
           Setting("RAZE_REBEL_GARRISON", "bool", "Rebels get a garrison", "the game raises it from the region's "
                   "rebel type (descr_rebel_factions.txt)"),
           Setting("RAZE_GOLD_PER_BUILDING", "int", "Money per building torn down", "added to the extermination's"),
           Setting("RAZE_GOLD_PER_CITIZEN", "int", "Money per inhabitant", "for each person the sack removes"),
           Setting("RAZE_KEEP_CHAINS", "set", "Building chains never torn down", "the governor's building (core) "
                   "must stay; walls and roads by default - use this mod's chain names"),
           Setting("RAZE_DEFAULT_REBEL_UNITS", "list", "Rebel units if the game raises none", "unit types of this "
                   "mod's export_descr_unit.txt; empty = none"),
           Setting("RAZE_BUTTON", "bool", "The 4th button", "off: Exterminate asks Yes / No to sack instead"),
           Setting("RAZE_BUTTON_LABEL", "text", "Button text", "the words on the button"),
           Setting("RAZE_BUTTON_TIP", "text", "Button tooltip", "shown when the mouse is over it")],
          "REX (Rome: Total War). Vanilla Rome has no scripts - the add-on then does nothing."),
]


def by_key(key):
    return next(a for a in ADDONS if a.key == key)


# ---------------------------------------------------------------------------
# The script's setting lines
# ---------------------------------------------------------------------------
def _span(text, var):
    """(start, end) of the value of 'local VAR = value' (a { } or [ ] value may run over lines), or None."""
    m = re.search(r"^local\s+%s\s*=\s*" % re.escape(var), text, re.M)
    if not m:
        return None
    start = m.end()
    if text[start] in "{[":
        close = "}" if text[start] == "{" else "]"
        end = text.index(close, start) + 1
    else:
        end = start
        quoted = False
        while end < len(text) and text[end] != "\n":
            c = text[end]
            if c == '"' and text[end - 1] != "\\":
                quoted = not quoted
            if not quoted and text[end:end + 2] == "//":
                break
            end += 1
        while end > start and text[end - 1] in " \t\r":
            end -= 1
    return start, end


def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


def read_settings(addon, text):
    """{var: value} from a script: bool -> True/False, int -> int, text / choice -> str, list / set -> [str]."""
    out = {}
    for s in addon.settings:
        sp = _span(text, s.var)
        if not sp:
            continue
        raw = text[sp[0]:sp[1]]
        if s.kind == "bool":
            out[s.var] = raw.strip() == "true"
        elif s.kind == "int":
            try:
                out[s.var] = int(raw.strip())
            except ValueError:
                out[s.var] = 0
        elif s.kind == "list":
            out[s.var] = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
        elif s.kind == "set":
            body = re.sub(r"//[^\n]*", "", raw)
            out[s.var] = re.findall(r"([A-Za-z_][\w]*)\s*=\s*true", body)
        else:
            out[s.var] = _unquote(raw)
    return out


def _quote(v):
    return '"%s"' % str(v).replace("\\", "\\\\").replace('"', '\\"')


def _render(s, v, old):
    if s.kind == "bool":
        return "true" if v else "false"
    if s.kind == "int":
        return str(int(v))
    if s.kind == "list":
        return "[" + ", ".join(_quote(x) for x in v) + "]"
    if s.kind == "set":
        indent = re.search(r"\n([ \t]+)\S", old)
        ind = indent.group(1) if indent else "    "
        return "{\n" + "".join("%s%s = true,\n" % (ind, x) for x in v) + "}"
    return _quote(v)


def check(addon, values):
    """[problem] with the chosen values (empty = fine)."""
    out = []
    name = re.compile(r"^[A-Za-z_][\w]*$")
    for s in addon.settings:
        v = values.get(s.var)
        if v is None:
            continue
        if s.kind == "int" and (not isinstance(v, int) or v < 0):
            out.append("%s: a whole number, 0 or more" % s.label)
        if s.kind == "set" and any(not name.match(x) for x in v):
            out.append("%s: names of letters, digits and _" % s.label)
        if s.kind == "choice" and v not in [c for c, _ in s.choices]:
            out.append("%s: pick one of the list" % s.label)
    if values.get("RAZE_WHO") == "list" and not values.get("RAZE_FACTIONS"):
        out.append("Who may sack: pick at least one faction")
    return out


def render(addon, text, values):
    """The script with the chosen values written into their lines (the rest byte for byte)."""
    have = read_settings(addon, text)
    for s in sorted(addon.settings, key=lambda s: -(_span(text, s.var) or (0, 0))[0]):
        if s.var not in values or (s.var in have and have[s.var] == values[s.var]):
            continue                    # an unchanged value keeps its line as it is (comments included)
        sp = _span(text, s.var)
        if not sp:
            raise ValueError("the add-on's script has no %s line" % s.var)
        text = text[:sp[0]] + _render(s, values[s.var], text[sp[0]:sp[1]]) + text[sp[1]:]
    return text


# ---------------------------------------------------------------------------
# Where it goes
# ---------------------------------------------------------------------------
def target(mod, addon):
    """<mod folder>/script/modules/<file>: a mod with a script folder of its own gets it there (REX reads the
    running mod's scripts), else the game's own script/modules."""
    root = os.path.dirname(os.path.abspath(mod.data))
    own = _ci(root, "script")
    if not own:
        try:
            from .newmod import game_of
            game = game_of(mod.data)
            if game and _ci(game, "script"):
                root = game
        except Exception:
            pass
    return os.path.join(root, "script", "modules", addon.file)


def plan_mod(mod, addon):
    """The ModData whose folder holds the add-on's place (backups live beside it): the mod itself, or the game's own
    data when the add-on goes into the game's script folder (a mod without scripts of its own)."""
    from .moddata import ModData
    root = os.path.dirname(os.path.abspath(mod.data))
    dst = os.path.abspath(target(mod, addon))
    if dst.startswith(os.path.join(root, "")):
        return mod
    game_root = os.path.dirname(os.path.dirname(os.path.dirname(dst)))
    return ModData(os.path.join(game_root, "data"))


def installed(mod, addon):
    """{var: value} of the add-on as it is installed, or None."""
    p = target(mod, addon)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as f:
        return read_settings(addon, f.read().decode("utf-8", "replace"))


def plan_install(plan, addon, values):
    problems = check(addon, values)
    if problems:
        raise ValueError("; ".join(problems))
    text = render(addon, addon.template(), values)
    dst = target(plan.mod, addon)
    plan.binary(dst, text.encode("utf-8"))
    plan.note(None, "%s %s: %s" % ("updated" if os.path.isfile(dst) else "put in", addon.title,
                                   os.path.relpath(dst, os.path.dirname(os.path.abspath(plan.mod.data)))))
    return dst


def plan_remove(plan, addon):
    dst = target(plan.mod, addon)
    plan.delete(dst, "the %s add-on taken out" % addon.title)
    return dst
