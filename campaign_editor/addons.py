"""Add-ons: ready-made scripts that bring the game something new, put in with their settings chosen in the tool.

An add-on is a Squirrel module (script/modules/<name>.nut - REX (Rome) and M2EX (Medieval II) both require() every
file there once the campaign is up, whatever mod runs). Besides the built-in ones, anyone's .nut can be added
(Add an add-on...): it is kept in the tool's own folder (addons/), its settings found by themselves, and Share...
packs it as a zip for others. Its settings are the 'local NAME = value' lines at the top of the file; the tool writes
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
    kind: 'bool', 'int', 'float', 'text', 'choice' (choices = [(value, label)]), 'list' (Squirrel array of strings),
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


# Sack / Raze Settlement: the people a sacked town keeps at least (the scripts' RAZE_MIN_PEOPLE; the games' own level
# minimum is 400 - a town is never emptied), and what the kept chains mean (the scripts never tear down core_*)
MIN_PEOPLE = 600
KEEP_HELP = ("the governor's chain (core) always stays, listed or not - without it the town can never be built up "
             "again; %s by default, take them out if you like. Any building of the mod is read in the game, also "
             "one added or brought from another mod")


class Addon:
    """game: 'rome', 'medieval2' or 'both'; path: the script of an add-on someone added (else a built-in one in
    assets/addons); picks {var: 'chains' | 'units' | 'factions'}: settings picked from the mod's own names."""

    def __init__(self, key, title, game, file, summary, settings, needs, picks=None, path=None):
        self.key, self.title, self.game, self.file = key, title, game, file
        self.summary, self.settings, self.needs = summary, settings, needs
        self.picks, self.path = dict(picks or {}), path

    @property
    def own(self):
        """Added by the user (kept in the tool's addons/ folder), not built in."""
        return self.path is not None

    def fits(self, game):
        return self.game in ("both", game)

    def template(self):
        with open(self.path or os.path.join(assets_dir(), self.file), "rb") as f:
            return f.read().decode("utf-8")


ADDONS = [
    Addon("sack_settlement", "Sack Settlement (Rome)", "rome", "sack_settlement.nut",
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
           Setting("RAZE_PEOPLE_LEFT", "int", "People left in the ruins", "%d at least - a town cannot be wiped "
                   "off the map" % MIN_PEOPLE),
           Setting("RAZE_KEEP_CHAINS", "set", "Building chains never torn down", KEEP_HELP % "walls and roads"),
           Setting("RAZE_DEFAULT_REBEL_UNITS", "list", "Rebel units if the game raises none", "unit types of this "
                   "mod's export_descr_unit.txt; empty = none"),
           Setting("RAZE_BUTTON", "bool", "The 4th button", "off: Exterminate asks Yes / No to sack instead"),
           Setting("RAZE_BUTTON_LABEL", "text", "Button text", "the words on the button"),
           Setting("RAZE_BUTTON_TIP", "text", "Button tooltip", "shown when the mouse is over it")],
          "REX (Rome: Total War). Vanilla Rome has no scripts - the add-on then does nothing.",
          picks={"RAZE_KEEP_CHAINS": "chains", "RAZE_DEFAULT_REBEL_UNITS": "units", "RAZE_FACTIONS": "factions"}),
    Addon("raze_settlement", "Sack Settlement (Medieval II)", "medieval2", "raze_settlement.nut",
          "A 4th choice on the capture scroll, under Occupy / Sack / Exterminate - its button says Raze Settlement "
          "(the game's own second button is already called Sack Settlement; change the words below), drawn from the "
          "game's own button pieces like the three above it. The town is exterminated the game's own way, "
          "every building but the kept ones is torn down, most people are gone, you get a reward, and the ruins go "
          "to the rebels with a fresh rebel garrison M2EX raises itself - the Medieval II brother of Rome's Sack "
          "Settlement, the same script engine. The computer's factions allowed below raze when they exterminate.",
          [Setting("RAZE_ENABLED", "bool", "Razing on", "off keeps the file but does nothing"),
           Setting("RAZE_WHO", "choice", "Who may raze", "the player picks it on the capture scroll; a computer "
                   "faction allowed here razes whenever it exterminates a town", WHO),
           Setting("RAZE_FACTIONS", "list", "The factions", "for 'Only the factions I pick'",
                   when=("RAZE_WHO", ["list"])),
           Setting("RAZE_GIVE_TO_REBELS", "bool", "Ruins go to the rebels", "off: the razed town stays yours"),
           Setting("RAZE_REBEL_GARRISON", "bool", "Rebels get a garrison", "the game raises it from the region's "
                   "rebel type (descr_rebel_factions.txt)"),
           Setting("RAZE_GOLD_PER_BUILDING", "int", "Money per building torn down", "added to the extermination's"),
           Setting("RAZE_GOLD_PER_CITIZEN", "int", "Money per inhabitant", "for each person the raze removes"),
           Setting("RAZE_PEOPLE_LEFT", "int", "People left in the ruins", "%d at least - a town cannot be wiped "
                   "off the map" % MIN_PEOPLE),
           Setting("RAZE_KEEP_CHAINS", "set", "Building chains never torn down", KEEP_HELP % "roads (the walls are "
                   "levels of the core chains in Medieval II)"),
           Setting("RAZE_DEFAULT_REBEL_UNITS", "list", "Rebel units if the game raises none", "unit types of this "
                   "mod's export_descr_unit.txt; empty = none"),
           Setting("RAZE_BUTTON", "bool", "The 4th button", "off: Exterminate asks Yes / No to raze instead"),
           Setting("RAZE_BUTTON_LABEL", "text", "Button text", "the words on the button"),
           Setting("RAZE_BUTTON_TIP", "text", "Button tooltip", "shown when the mouse is over it")],
          "M2EX (Medieval II: Total War) - its own scripts (script/main.nut) load every .nut of the game's "
          "script/modules, whatever mod runs. Vanilla Medieval II runs no scripts - the add-on then does nothing.",
          picks={"RAZE_KEEP_CHAINS": "chains", "RAZE_DEFAULT_REBEL_UNITS": "units", "RAZE_FACTIONS": "factions"}),
    Addon("player_diplomacy", "Player Diplomacy", "rome", "player_diplomacy.nut",
          "The computer's factions stop attacking you when it makes no sense: after a ceasefire they keep the peace "
          "for some turns (a war they declare in that time is undone), your client kingdoms never plan to invade "
          "you, and a faction far weaker than you does not either (its allies already at war with you count on its "
          "side, so a big alliance still comes). Only how the computer treats YOU changes; its wars with each other "
          "stay as they are. The console: sq ::truce_status(), sq ::truce_set(\"egypt\", 10), sq ::power(\"egypt\").",
          [Setting("TRUCE_TURNS", "int", "Turns a ceasefire holds", "your turns; 0 = no truce rule"),
           Setting("TRUCE_STEER_AI", "bool", "The computer plans no invasion of you in a truce", "the main rule"),
           Setting("TRUCE_RESTORE_PEACE", "bool", "A war declared in a truce is undone", "peace put back at once"),
           Setting("CLIENT_NEVER_ATTACK", "bool", "Client kingdoms never attack you", "while they are your "
                   "protectorates"),
           Setting("DETER_ENABLED", "bool", "Far weaker factions do not attack you", "by strength below"),
           Setting("DETER_RATIO", "float", "You this many times stronger", "units in all armies and garrisons, "
                   "plus the settlements below; 3.0 = three times"),
           Setting("STRENGTH_PER_SETTLEMENT", "int", "A settlement counts as units", "in that strength"),
           Setting("COALITIONS_COUNT", "bool", "Allies at war with you add their strength", "so small factions "
                   "still join a big alliance against you")],
          "REX (Rome: Total War), its campaign AI hook (calculateLtgd). Vanilla Rome has no scripts - the add-on "
          "then does nothing."),
]


def by_key(key):
    return next(a for a in library() if a.key == key)


# ---------------------------------------------------------------------------
# Anyone's add-on: its settings read from the script itself
# ---------------------------------------------------------------------------
RE_LOCAL = re.compile(r"^local\s+([A-Z][A-Z0-9_]*)\s*=", re.M)
RE_TAG = re.compile(r"^//\s*@(\w+)\s*(.*?)\s*$", re.M)
NAME_KINDS = ("chains", "units", "factions")
SCRIPT_CAP = 1 << 20


def _seq(item, open_, close):
    """A bracketed list of items apart by a comma or by white space, a comma after the last allowed - written so
    that a text can be matched in one way only (the older '\\s*,?\\s*' between items backtracked exponentially
    on a long line of spaces: CodeQL py/redos)."""
    return r"%s\s*(?:%s(?:(?:\s*,\s*|\s+)%s)*(?:\s*,)?\s*)?%s" % (open_, item, item, close)


def _kind(raw):
    """The setting kind a literal value asks for, or None (not a setting the tool can show)."""
    v = raw.strip()
    if v in ("true", "false"):
        return "bool"
    if re.fullmatch(r"-?\d+", v):
        return "int"
    if re.fullmatch(r'"(?:[^"\\]|\\.)*"', v):
        return "text"
    if v.startswith("[") and re.fullmatch(_seq(r'"(?:[^"\\]|\\.)*"', r"\[", r"\]"), v, re.S):
        return "list"
    if v.startswith("{") and re.fullmatch(_seq(r"[A-Za-z_]\w*\s*=\s*true", r"\{", r"\}"),
                                          re.sub(r"//[^\n]*", "", v), re.S):
        return "set"
    return None


def _help(text, start, end):
    """A setting's help: the // comment after its value on the same line, else the // lines right above it."""
    line_end = text.find("\n", end)
    tail = text[end:line_end if line_end >= 0 else len(text)]
    m = re.match(r"\s*,?\s*//\s*(.*)", tail)
    if m and m.group(1).strip():
        return m.group(1).strip()
    above = text[:text.rfind("\n", 0, start) + 1].rstrip("\n").split("\n")
    out = []
    for line in reversed(above):
        s = line.strip()
        if not s.startswith("//") or s.startswith("// @") or s.startswith("//@") or set(s) <= set("/=- "):
            break
        out.append(s[2:].strip())
    return " ".join(reversed(out))


def from_script(text, file, path=None):
    """An Addon made from anyone's script: the title, game, summary, needs and name pickers from optional header
    lines (// @title ..., // @game rome|medieval2|both, // @summary ..., // @needs ..., // @settings A, B,
    // @pick VAR chains|units|factions, // @label VAR words), its settings from the UPPER_CASE `local NAME = value`
    lines at the top level (true / false, a whole number, "text", ["a", "b"], { a = true }) - or only those
    @settings names."""
    tags = {}
    picks, labels = {}, {}
    for m in RE_TAG.finditer(text):
        key, val = m.group(1).lower(), m.group(2)
        if key == "pick" and len(val.split()) == 2 and val.split()[1] in NAME_KINDS:
            picks[val.split()[0]] = val.split()[1]
        elif key == "label" and len(val.split(None, 1)) == 2:
            labels[val.split(None, 1)[0]] = val.split(None, 1)[1]
        else:
            tags.setdefault(key, val)
    only = [x.strip() for x in tags.get("settings", "").split(",") if x.strip()]
    settings = []
    for m in RE_LOCAL.finditer(text):
        var = m.group(1)
        if (only and var not in only) or any(s.var == var for s in settings):
            continue
        sp = _span(text, var)
        if not sp:
            continue
        kind = _kind(text[sp[0]:sp[1]])
        if kind is None:
            continue
        label = labels.get(var) or var.replace("_", " ").strip().capitalize()
        settings.append(Setting(var, kind, label, _help(text, m.start(), sp[1])))
    stem = os.path.splitext(os.path.basename(file))[0]
    first = next((l.strip("/ \t=-") for l in text.splitlines()[:12]
                  if l.strip().startswith("//") and l.strip("/ \t=-") and "@" not in l[:4]), "")
    game = tags.get("game", "both").lower()
    if game not in ("rome", "medieval2", "both"):
        game = "both"
    # no @title: the words before ' - ' on the first comment line ("// Border Tolls - a toll at ..."), else the file
    title = tags.get("title") or (first.split(" - ")[0].strip() if " - " in first else "") or \
        stem.replace("_", " ").title()
    return Addon(stem, title, game, os.path.basename(file),
                 tags.get("summary") or first or "An add-on script (%s)." % os.path.basename(file), settings,
                 tags.get("needs") or "REX (Rome) or M2EX (Medieval II): the script goes into script/modules, which "
                                      "they load by themselves. The original exes run no scripts.",
                 picks=picks, path=path)


def library_dir():
    """The tool's own addons/ folder (next to the exe): add-ons someone added."""
    from . import log
    home = log.home()
    if not home:
        return None
    new = os.path.join(home, log.SHORT + "_addons")              # beside the exe, apart from the game's own folders
    old = os.path.join(home, log.FOLDER, "addons")                # up to 0.28: in RTW-M2TW-Campaign-Editor-files
    if os.path.isdir(old) and not os.path.exists(new):
        try:
            os.replace(old, new)
        except OSError:
            return old
    return new


def library():
    """Every add-on the tool knows: the built-in ones, then the added ones (by title)."""
    out = list(ADDONS)
    d = library_dir()
    if d and os.path.isdir(d):
        own = []
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if n.lower().endswith(".nut") and os.path.isfile(p) and os.path.getsize(p) <= SCRIPT_CAP:
                try:
                    with open(p, "rb") as f:
                        a = from_script(f.read().decode("utf-8", "replace"), n, p)
                except OSError:
                    continue
                if all(a.key != b.key for b in out):
                    own.append(a)
        out += sorted(own, key=lambda a: a.title.lower())
    return out


def add_to_library(src):
    """Add-ons from a .nut or a .zip (every .nut in it, by file name only - nothing outside addons/ is written).
    Returns [Addon]; raises ValueError in plain words."""
    import zipfile
    d = library_dir()
    if not d:
        raise ValueError("the tool has no folder of its own to keep add-ons in")
    got = []                                           # (file name, bytes)
    low = src.lower()
    if low.endswith(".nut"):
        if os.path.getsize(src) > SCRIPT_CAP:
            raise ValueError("%s is over 1 MB - not a script" % os.path.basename(src))
        with open(src, "rb") as f:
            got.append((os.path.basename(src), f.read()))
    elif low.endswith(".zip"):
        with zipfile.ZipFile(src) as z:
            for info in z.infolist():
                name = os.path.basename(info.filename.replace("\\", "/"))
                if name.lower().endswith(".nut") and not info.is_dir() and info.file_size <= SCRIPT_CAP:
                    got.append((name, z.read(info)))
    else:
        raise ValueError("an add-on is a Squirrel script (.nut) or a zip with one - REX and M2EX load those")
    if not got:
        raise ValueError("no .nut script in %s" % os.path.basename(src))
    built = {a.file.lower() for a in ADDONS}
    os.makedirs(d, exist_ok=True)
    out = []
    for name, data in got:
        if not re.fullmatch(r"[\w.-]+\.nut", name, re.I):
            raise ValueError("%s: a script's name is letters, digits, _ - and . only" % name)
        if name.lower() in built:
            raise ValueError("%s is built in already (it is in the list)" % name)
        dst = os.path.join(d, name)
        with open(dst, "wb") as f:
            f.write(data)
        out.append(from_script(data.decode("utf-8", "replace"), name, dst))
    return out


def remove_from_library(addon):
    """An added add-on off the list (its script in addons/ deleted; one put into a game stays there)."""
    if not addon.own:
        raise ValueError("%s is built in" % addon.title)
    os.remove(addon.path)


def share(addon, out, values=None):
    """A zip to give others: the script (with the settings picked here, if given) and a README.txt saying what it
    is and where it goes."""
    import zipfile
    text = render(addon, addon.template(), values) if values else addon.template()
    readme = "\n".join([
        addon.title, "", addon.summary, "", "Needs: " + addon.needs, "",
        "Put it in with RTW & M2TW Campaign Editor: Add-ons > Add an add-on... > this zip, pick the settings, "
        "Put it in. By hand: copy %s into <game folder>/script/modules/." % addon.file, ""])
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(addon.file, text)
        z.writestr("README.txt", readme)
    return out


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
            if not quoted and text[end:end + 2] in ("//", "--"):
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
        elif s.kind == "float":
            try:
                out[s.var] = float(raw.strip())
            except ValueError:
                out[s.var] = 0.0
        elif s.kind == "list":
            out[s.var] = re.findall(r'"((?:[^"\\]|\\.)*)"', raw)
        elif s.kind == "set":
            body = re.sub(r"(//|--)[^\n]*", "", raw)
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
    if s.kind == "float":
        return repr(float(v))                      # 3.0, never 3 (Squirrel would make it a whole number)
    if s.kind == "list":
        return "[" + ", ".join(_quote(x) for x in v) + "]"
    if s.kind == "set":
        indent = re.search(r"\n([ \t]+)\S", old)
        ind = indent.group(1) if indent else "    "
        return "{\n" + "".join("%s%s = true,\n" % (ind, x) for x in v) + "}"
    return _quote(v)


def mod_names(mod, what):
    """The names a setting picks from, read from the mod: 'chains' (export_descr_buildings.txt), 'units'
    (export_descr_unit.txt). [] when the file is not there."""
    try:
        if what == "chains":
            from .buildings import read_buildings
            return [b.name for b in read_buildings(mod.load(mod.file("edb")))]
        if what == "units":
            from .units import read_units
            return [u.type for u in read_units(mod.load(mod.file("edu")))]
        if what == "factions":
            return [n for n, _ in mod.factions() if n != "slave"]
    except Exception:
        return []
    return []


def check(addon, values, mod=None):
    """[problem] with the chosen values (empty = fine). With the mod, names are checked against its files: a kept
    chain or a rebel unit the mod does not have would do nothing (the governor's chain would then be torn down);
    and the add-on's own code already pasted into the mod's scripts is refused (it would run twice)."""
    out = []
    if mod is not None:
        dup = already_in_scripts(mod, addon)
        if dup:
            out.append("this mod's own %s already holds the %s code - it would run twice (two buttons); take it out "
                       "of that file first, or leave the add-on out" % (
                           ", ".join(os.path.relpath(p, os.path.dirname(os.path.abspath(mod.data))) for p in dup),
                           addon.title))
    if mod is not None:
        for var, what in addon.picks.items():
            if what not in ("chains", "units"):
                continue
            have = mod_names(mod, what)
            if have and values.get(var):
                low = {x.lower() for x in have}
                wrong = [x for x in values[var] if x.lower() not in low]
                if wrong:
                    out.append("%s: %s not in this mod's %s" % (
                        next(s.label for s in addon.settings if s.var == var), ", ".join(wrong),
                        "export_descr_buildings.txt" if what == "chains" else "export_descr_unit.txt"))
    name = re.compile(r"^[A-Za-z_][\w]*$")
    for s in addon.settings:
        v = values.get(s.var)
        if v is None:
            continue
        if s.kind == "int" and (not isinstance(v, int) or v < 0):
            out.append("%s: a whole number, 0 or more" % s.label)
        if s.kind == "float" and (not isinstance(v, (int, float)) or v < 0):
            out.append("%s: a number, 0 or more (like 3.0)" % s.label)
        if s.kind == "set" and any(not name.match(x) for x in v):
            out.append("%s: names of letters, digits and _" % s.label)
        if s.kind == "choice" and v not in [c for c, _ in s.choices]:
            out.append("%s: pick one of the list" % s.label)
    if isinstance(values.get("RAZE_PEOPLE_LEFT"), int) and values["RAZE_PEOPLE_LEFT"] < MIN_PEOPLE:
        out.append("People left in the ruins: %d at least - a town cannot be wiped off the map" % MIN_PEOPLE)
    if values.get("RAZE_WHO") == "list" and not values.get("RAZE_FACTIONS"):
        out.append("%s: pick at least one faction" % next(
            (s.label for s in addon.settings if s.var == "RAZE_WHO"), "Who may"))
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
# Up to 0.29.2 the Medieval II Raze Settlement was an EOP-style Lua script in the mod's eopData/eopScripts, loaded by a
# line in luaPluginScript.lua; the native .nut replaces it, and putting it in (or taking it out) takes the Lua copy and
# its line out too - both would draw a button.
OLD_LUA = {"raze_settlement": "raze_settlement.lua"}
OLD_LUA_DIR = ("eopData", "eopScripts")
OLD_LUA_ENTRY = "luaPluginScript.lua"
OLD_LUA_MARK = b"added by RTW & M2TW Campaign Editor: "


def loads_modules(folder):
    """True when <folder>/script/main.nut requires every .nut of its script/modules (REX's own squi plugin does:
    scripting.listModules("modules")). A mod's own script plugin (a manifest.nut and main.nut of its own, like HLR's)
    does not - a module put beside it is never run."""
    sd = _ci(folder, "script") if folder else None
    main = _ci(sd, "main.nut") if sd else None
    if not main:
        return False
    try:
        with open(main, "rb") as fh:
            return b"listModules" in fh.read()
    except OSError:
        return False


def target(mod, addon):
    """Where the add-on goes: <game>/script/modules/<file> - REX's own scripts (script/main.nut, the squi plugin)
    require every .nut there for whatever mod runs (a tester's HLR has a script plugin of its own whose main.nut
    loads no modules: an add-on in the mod's script/modules never ran). The mod's own script/modules only when the
    mod's main.nut loads them, or the game folder is not known. M2EX's script/main.nut does the same for Medieval II."""
    root = os.path.dirname(os.path.abspath(mod.data))
    game = None
    try:
        from .newmod import game_of
        game = game_of(mod.data)
    except Exception:
        pass
    if loads_modules(root):
        return os.path.join(root, "script", "modules", addon.file)
    if game and (loads_modules(game) or _ci(game, "script")):
        return os.path.join(game, "script", "modules", addon.file)
    return os.path.join(root, "script", "modules", addon.file)


def marker(addon):
    """A line only this add-on's code has (its log prefix, 'local PREFIX = "[SACK] "'), or None."""
    m = re.search(r'^\s*local\s+PREFIX\s*=\s*"([^"]+)"', addon.template(), re.M)
    return m.group(1).strip() if m else None


def already_in_scripts(mod, addon):
    """[the mod's own script files (not its modules folder) that already hold this add-on's code] - pasted into a
    mod's main.nut, a second copy as an add-on would run it twice (two buttons on the capture scroll)."""
    mk = marker(addon)
    # its settings' own lines too ('local RAZE_BUTTON_LABEL = ...'): code pasted into a mod's main.nut keeps them
    # while it logs under the mod's prefix
    decl = [re.compile(r"^\s*local\s+%s\s*=" % re.escape(x.var), re.M) for x in addon.settings]
    root = os.path.dirname(os.path.abspath(mod.data))
    sd = _ci(root, "script")
    if not (mk or decl) or not sd:
        return []
    out = []
    for dirpath, dirs, files in os.walk(sd):
        dirs[:] = [d for d in dirs if d.lower() != "modules"]
        for f in files:
            if not f.lower().endswith(".nut"):
                continue
            p = os.path.join(dirpath, f)
            try:
                with open(p, "rb") as fh:
                    text = fh.read().decode("utf-8", "replace")
            except OSError:
                continue
            if (mk and mk in text) or sum(1 for r in decl if r.search(text)) >= min(2, len(decl)):
                out.append(p)
    return out


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


def plan_install(plan, addon, values, mod=None):
    problems = check(addon, values, mod)
    if problems:
        raise ValueError("; ".join(problems))
    text = render(addon, addon.template(), values)
    dst = target(plan.mod, addon)
    plan.binary(dst, text.encode("utf-8"))
    _old_lua(plan, mod or plan.mod, addon)
    plan.note(None, "%s %s: %s" % ("updated" if os.path.isfile(dst) else "put in", addon.title,
                                   os.path.relpath(dst, os.path.dirname(os.path.abspath(plan.mod.data)))))
    return dst


def plan_remove(plan, addon, mod=None):
    dst = target(plan.mod, addon)
    plan.delete(dst, "the %s add-on taken out" % addon.title)
    _old_lua(plan, mod or plan.mod, addon)
    return dst


def _old_lua(plan, mod, addon):
    """An older version's Lua copy of the add-on in the mod (OLD_LUA) deleted, and its loader line taken out of
    luaPluginScript.lua - every other byte of that file kept."""
    old = OLD_LUA.get(addon.key)
    if not old:
        return
    folder = os.path.join(os.path.dirname(os.path.abspath(mod.data)), *OLD_LUA_DIR)
    lua = _ci(folder, old) if os.path.isdir(folder) else None
    if lua:
        plan.delete(lua, "the older Lua %s - the native script replaces it" % addon.title)
    entry = _ci(folder, OLD_LUA_ENTRY) if os.path.isdir(folder) else None
    if not entry:
        return
    with open(entry, "rb") as fh:
        data = fh.read()
    lines = data.split(b"\n")
    keep = [l for l in lines if (OLD_LUA_MARK + old.encode()) not in l]
    if len(keep) != len(lines):
        plan.binary(entry, b"\n".join(keep))
        plan.note(None, "%s: no longer loads the older Lua %s" % (OLD_LUA_ENTRY, old))
