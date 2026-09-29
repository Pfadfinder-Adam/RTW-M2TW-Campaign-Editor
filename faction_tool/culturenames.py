"""Settlement names that follow the owner's culture (REX).

The game gives a town one name; REX can rename it while the campaign runs (console command
`rename_settlement <settlement> <name>`, a "quoted" name is literal text) and runs Squirrel
scripts: every .nut in script/modules is loaded (REX's squi entry, script/main.nut:
`::scripting.listModules("modules")`), with the mod's scope over the game's. So the tool
writes one module, <mod>/script/modules/ft_settlement_names.nut, holding a table
{settlement: {culture: name, "*": name for every other culture}} and a handler that, when a
turn begins and whenever the campaign map opens (also after a battle), renames every listed
town whose owner's culture wants another name.

Engine calls the module uses (from REX's own scripts and REX.exe's API text; to be confirmed
with REX's `dump_docudemon` and in the game): ::events.on(name, fn), ::game.factionCount(),
::game.faction(i), faction.cultureId, faction.settlementCount, faction.settlement(i),
settlement.name / settlement.displayName, ::game.cultureName(id), ::game.runConsoleCommand(line).
The table is also kept as JSON on one comment line, which is what the tool reads back."""

import json
import os
import re

from .textio import strip_comment, tokens

MODULE = ("script", "modules", "ft_settlement_names.nut")
DEFAULT = "*"                                  # the name for a culture the table does not list
RE_DATA = re.compile(r"^// DATA (.*)$", re.M)


def module_path(mod):
    """Where the module goes: the mod's folder (REX's mod scope), next to its data."""
    return os.path.join(os.path.dirname(os.path.abspath(mod.data)), *MODULE)


def cultures(mod):
    """The cultures of descr_cultures.txt in their order (the order is the game's culture id)."""
    from .symbols import _find
    p = _find(mod, "descr_cultures.txt")
    out = []
    if not p:
        return out
    for line in mod.load(p).texts():
        t = tokens(strip_comment(line))
        if t[:1] == ["culture"] and len(t) > 1 and t[1] not in out:
            out.append(t[1])
    return out


def shown_name(mod, campaign, town):
    """The town's name as the game shows it now ({town} in the campaign's region labels), or the file name."""
    import re as _re
    p = mod.region_labels_file(campaign)
    if p:
        for line in mod.load(p).texts():
            m = _re.match(r"\s*\{([^}]+)\}\s*(.*)$", line)
            if m and m.group(1).lower() == town.lower() and m.group(2).strip():
                return m.group(2).strip()
    return town.replace("_", " ")


def read(mod, plan=None):
    """{settlement: {culture or '*': name}} as the module holds it (the plan's new one first)."""
    p = module_path(mod)
    if plan is not None and p in plan.binaries:
        text = plan.binaries[p].decode("utf-8")
    elif os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
    else:
        return {}
    m = RE_DATA.search(text)
    try:
        return json.loads(m.group(1)) if m else {}
    except ValueError:
        return {}


def _sq(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(table, culture_list):
    """The Squirrel module for a table."""
    rows = []
    for town in sorted(table):
        names = table[town]
        inner = ", ".join("[%s] = %s" % (_sq(c), _sq(n)) for c, n in sorted(names.items()))
        rows.append("    [%s] = { %s }" % (_sq(town), inner))
    return """// Written by RTW & M2TW Campaign Editor - settlement names by the owner's culture (REX).
// Edit it in the tool (Edit region... -> Names by culture); a hand edit below the DATA line is overwritten.
// DATA %s
local CULTURES = [%s]
local NAMES = {
%s
}
local warned = false

local function cultureOf(faction) {
    local id = faction.cultureId
    if (id == null || id < 0) return null
    if (::game.rawin("cultureName")) {
        try { return ::game.cultureName(id) } catch (e) {}
    }
    return id < CULTURES.len() ? CULTURES[id] : null
}

local function apply() {
    try {
        local count = ::game.factionCount()
        for (local fi = 0; fi < count; fi += 1) {
            local faction = ::game.faction(fi)
            if (faction == null) continue
            local culture = cultureOf(faction)
            for (local si = 0; si < faction.settlementCount; si += 1) {
                local town = faction.settlement(si)
                if (town == null || !(town.name in NAMES)) continue
                local names = NAMES[town.name]
                local want = (culture != null && culture in names) ? names[culture] : ("*" in names ? names["*"] : null)
                if (want == null || town.displayName == want) continue
                ::game.runConsoleCommand("rename_settlement " + town.name + " \\"" + want + "\\"")
            }
        }
    }
    catch (e) {
        if (!warned) println("ft_settlement_names: " + e)
        warned = true
    }
}

::events.on("turnChanged", function (...) { apply() })
::events.on("campaignMapLoaded", function (...) { apply() })
""" % (json.dumps(table, ensure_ascii=False, sort_keys=True), ", ".join(_sq(c) for c in culture_list),
       ",\n".join(rows))


def problems(mod, table):
    """Plain words for what the game would not take."""
    out = []
    known = set(cultures(mod)) | {DEFAULT}
    for town, names in table.items():
        for c, n in names.items():
            if c not in known:
                out.append("%s: no culture called %s in descr_cultures.txt" % (town, c))
            if '"' in n or "\n" in n or not n.strip():
                out.append("%s: the name for %s must be one line of text without \"" % (town, c))
    return out


def apply(plan, campaign, changes):
    """changes = {settlement: {culture: name, '*': name} or {} to drop the town}: merged into the
    module the mod has, written with the plan (a backup, Restore). Not REX: a warning, nothing written."""
    if not changes:
        return
    from .limits import faction_limit
    mod = plan.mod
    table = read(mod, plan)
    for town, names in changes.items():
        names = {c: n.strip() for c, n in (names or {}).items() if n and n.strip()}
        if names:
            table[town] = names
        else:
            table.pop(town, None)
    bad = problems(mod, table)
    if bad:
        raise ValueError("names by culture: " + "; ".join(bad))
    if faction_limit(mod).get("engine") != "REX.exe":
        plan.warn(None, "names by culture need REX (it renames towns while the campaign runs); the game "
                        "folder has no REX.exe - nothing written")
        return
    path = module_path(mod)
    plan.binary(path, script(table, cultures(mod)).encode("utf-8"))
    plan.notes.append((mod.rel(path), "names by the owner's culture for %d town(s): %s" % (
        len(table), ", ".join(sorted(table)[:8]) + (" ..." if len(table) > 8 else ""))))
