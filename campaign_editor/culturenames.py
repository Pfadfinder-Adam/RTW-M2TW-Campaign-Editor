"""Settlement names that follow the owner's culture (REX).

The game gives a town one name; REX renames it while the campaign runs with its console command
`rename_settlement <settlement> <name>` ("quoted" = literal text, a bare word = a key of
expanded.txt). REX's own documentation (`dump_docudemon`: docudemon_events / _conditions /
_commands, console_commands) gives the rest, all plain campaign script:

    monitor_event SettlementTurnStart SettlementName Roma      ; each town, at its owner's turn start
        and FactionCultureType barbarian                       ; the owner's culture
        console_command rename_settlement Roma "Rom"
    end_monitor

and the same on GeneralCaptureSettlement (the capturer's faction) so a taken town is renamed at
once. The monitors go in one block of the campaign's campaign_script.txt between the tool's
markers, before its `wait_monitors`; a campaign without a script gets one (script ... wait_monitors
end_script) and the `script` / `campaign_script.txt` lines at the end of descr_strat.txt, as
Medieval II's own campaigns have them. The table {settlement: {culture | '*': name}} is kept on
one comment line of the block, which is what the tool reads back."""

import json
import os
import re

from .textio import strip_comment, tokens

DEFAULT = "*"                                  # the name for every culture the table does not list
BEGIN = "; >>> RTW & M2TW Campaign Editor: settlement names by culture (REX) - edit in the tool <<<"
END = "; >>> end of settlement names by culture <<<"
RE_DATA = re.compile(r"^\s*;\s*DATA (.*)$")
EVENTS = ("SettlementTurnStart", "GeneralCaptureSettlement")


def cultures(mod):
    """The cultures of descr_cultures.txt in their order."""
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
    p = mod.region_labels_file(campaign)
    if p:
        for line in mod.load(p).texts():
            m = re.match(r"\s*\{([^}]+)\}\s*(.*)$", line)
            if m and m.group(1).lower() == town.lower() and m.group(2).strip():
                return m.group(2).strip()
    return town.replace("_", " ")


def name_for(names, culture):
    """The name a town of this table row shows under an owner of that culture, or None (the game's own)."""
    names = names or {}
    return names.get(culture) or names.get(DEFAULT) or None


def labels(table, towns, owners, culture_of):
    """{region: name the town shows} for towns whose table row gives a name for its owner's culture.
    towns {region: settlement}, owners {region: faction}, culture_of(faction) -> culture or None."""
    out = {}
    for region, town in towns.items():
        names = table.get(town)
        if names:
            n = name_for(names, culture_of(owners.get(region) or "slave"))
            if n:
                out[region] = n
    return out


def script_path(mod, campaign):
    return os.path.join(mod.campaign_dir(campaign), "campaign_script.txt")


def _texts(mod, campaign, plan=None):
    """The lines of the campaign's campaign_script.txt (the plan's edited or new copy first), or None."""
    p = mod.in_campaign(campaign, "campaign_script.txt")
    if plan is not None:
        if p and p in plan.files:
            return plan.files[p].texts()
        new = script_path(mod, campaign)
        if new in plan.binaries:
            return plan.binaries[new].decode("latin-1").splitlines()
    return mod.load(p).texts() if p else None


def _block(texts):
    """(begin, end) line indices of the tool's block, or None."""
    b = next((i for i, t in enumerate(texts) if t.strip() == BEGIN), None)
    if b is None:
        return None
    e = next((i for i in range(b + 1, len(texts)) if texts[i].strip() == END), None)
    return (b, e) if e is not None else None


def read(mod, campaign, plan=None):
    """{settlement: {culture or '*': name}} the campaign's script holds."""
    texts = _texts(mod, campaign, plan)
    got = _block(texts) if texts else None
    if not got:
        return {}
    for t in texts[got[0]:got[1]]:
        m = RE_DATA.match(t)
        if m:
            try:
                return json.loads(m.group(1))
            except ValueError:
                return {}
    return {}


RE_RENAME = re.compile(r"^\s*console_command\s+rename_settlement\s+(\S+)", re.I)


def foreign(mod, campaign):
    """{settlement: count} renamed by the campaign script outside the tool's block (the mod's own script):
    shown, not edited here - both would rename the town and the last one run would win."""
    texts = _texts(mod, campaign)
    if not texts:
        return {}
    got = _block(texts)
    out = {}
    for i, t in enumerate(texts):
        if got and got[0] <= i <= got[1]:
            continue
        m = RE_RENAME.match(strip_comment(t))
        if m:
            out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


def block(table, indent="\t"):
    """The script lines of the tool's block for a table."""
    out = [BEGIN, "; DATA " + json.dumps(table, ensure_ascii=True, sort_keys=True)]
    for town in sorted(table):
        names = table[town]
        listed = sorted(c for c in names if c != DEFAULT)
        for event in EVENTS:
            for c in listed:
                out += [indent + "monitor_event %s SettlementName %s" % (event, town),
                        indent * 2 + "and FactionCultureType %s" % c,
                        indent * 2 + 'console_command rename_settlement %s "%s"' % (town, names[c]),
                        indent + "end_monitor"]
            if DEFAULT in names:
                out.append(indent + "monitor_event %s SettlementName %s" % (event, town))
                out += [indent * 2 + "and not FactionCultureType %s" % c for c in listed]
                out += [indent * 2 + 'console_command rename_settlement %s "%s"' % (town, names[DEFAULT]),
                        indent + "end_monitor"]
    out.append(END)
    return out


def problems(mod, table):
    """Plain words for what the game would not take."""
    out = []
    known = set(cultures(mod)) | {DEFAULT}
    for town, names in table.items():
        if not re.match(r"^\S+$", town):
            out.append("%s: a settlement's file name has no spaces" % town)
        for c, n in names.items():
            if c not in known:
                out.append("%s: no culture called %s in descr_cultures.txt" % (town, c))
            if '"' in n or "\n" in n or not n.strip():
                out.append("%s: the name for %s must be one line of text without \"" % (town, c))
            else:
                try:
                    n.encode("latin-1")
                except UnicodeEncodeError:
                    out.append("%s: the name for %s has letters the game's script files cannot hold" % (town, c))
    return out


def engine(mod):
    """(name, present): the engine that runs these renames for this game - REX for Rome, M2EX for
    Medieval II (REX's own build of it) - and whether its exe is in the game folder."""
    from .limits import faction_limit, game_kind
    name = "M2EX" if game_kind(mod) == "medieval2" else "REX"
    return name, faction_limit(mod).get("engine") == name + ".exe"


def apply(plan, campaign, changes):
    """changes = {settlement: {culture: name, '*': name} or {} to drop the town}: merged into what the
    campaign's script holds and written with the plan (a backup, Restore). Not REX: a warning only."""
    if not changes:
        return
    mod = plan.mod
    table = read(mod, campaign, plan)
    for town, names in changes.items():
        names = {c: n.strip() for c, n in (names or {}).items() if n and n.strip()}
        if names:
            table[town] = names
        else:
            table.pop(town, None)
    bad = problems(mod, table)
    if bad:
        raise ValueError("names by culture: " + "; ".join(bad))
    name, present = engine(mod)
    if not present:
        plan.warn(None, "names by culture need %s (its rename_settlement renames towns while the campaign runs); "
                        "the game folder has no %s.exe - nothing written" % (name, name))
        return
    lines = block(table) if table else []
    existing = mod.in_campaign(campaign, "campaign_script.txt")
    if existing:
        f = plan.edit(existing)
        texts = f.texts()
        got = _block(texts)
        if got:
            f.raw[got[0]:got[1] + 1] = [f.make(t) for t in lines]
        elif lines:
            at = next((i for i in range(len(texts) - 1, -1, -1)
                       if tokens(strip_comment(texts[i]))[:1] == ["wait_monitors"]), None)
            if at is None:                      # without it the script ends at once and its monitors with it
                at = next((i for i in range(len(texts) - 1, -1, -1)
                           if tokens(strip_comment(texts[i]))[:1] == ["end_script"]), len(texts))
                lines = lines + ["\twait_monitors"]
            f.insert(at, lines)
        plan.note(f, "names by the owner's culture for %d town(s)" % len(table))
        return
    if not table:
        return
    path = script_path(mod, campaign)
    body = ["script"] + lines + ["\twait_monitors", "end_script", ""]
    plan.binary(path, "\r\n".join(body).encode("latin-1"))
    plan.notes.append((mod.rel(path), "campaign script made: names by the owner's culture for %d town(s)"
                       % len(table)))
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    s = plan.edit(sp)
    texts = s.texts()
    if not any(tokens(strip_comment(t))[:1] == ["script"] for t in texts):
        end = len(texts)
        while end and not texts[end - 1].strip():
            end -= 1
        s.insert(end, ["", "script", "campaign_script.txt"])
        plan.note(s, "the campaign runs campaign_script.txt (names by culture)")
