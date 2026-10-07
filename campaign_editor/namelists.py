"""A faction's own name lists (descr_names.txt), typed in by the user.

A name list is three pools: men's first names (`characters`, every man of the faction), surnames
(`surnames`, optional - Dacia, Numidia and the rebels have none) and women's names (`women`, wives,
daughters, princesses). Every name is a key: descr_names.txt lists the key, the string table names.txt
gives the text the game shows ({Key}Text), and descr_names_lookup.txt (both games) lists every key.
A name in descr_strat that is in no pool crashes the game (CHARACTER_DB::create / name_set), so the three
files are written together: the faction's own section (its own even when it shared one, BI), the strings
the table lacks and the keys the lookup lacks, appended."""

import re

POOLS = ("characters", "surnames", "women")
TITLES = {"characters": "Men's names", "surnames": "Surnames", "women": "Women's names"}
RE_BAD_KEY = re.compile(r"[^A-Za-z0-9_'\-]")


def parse(text):
    """Names typed by the user: one per line or separated by commas / semicolons (then a name may have
    spaces: 'Abd al-Malik'); with none of those, spaces separate the names. Duplicates dropped."""
    text = text or ""
    if re.search(r"[,;\n]", text):
        parts = re.split(r"[,;\n]+", text)
    else:
        parts = text.split()
    out, seen = [], set()
    for p in parts:
        p = " ".join(p.split())
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


class Kept(str):
    """A key the faction's characters already carry, written back exactly as it is (vanilla Medieval II has
    surname keys with a space: 'de Avena')."""


def key_of(name):
    """The key a name is written under: spaces become _ (descr_strat separates first name and surname by a
    space, and the console wants "Gaius Julius_Caesar" - so a new key never holds one)."""
    if isinstance(name, Kept):
        return str(name)
    return "_".join(name.split())


def problems(pools):
    """Plain words for what the game would not take; [] = fine."""
    out = []
    if not pools.get("characters"):
        out.append("men's names: at least one is needed (every man of the faction takes one)")
    if not pools.get("women"):
        out.append("women's names: at least one is needed (wives, daughters and princesses take one)")
    for pool in POOLS:
        for n in pools.get(pool) or []:
            k = key_of(n)
            if RE_BAD_KEY.search(k):
                out.append("%s: '%s' - only Latin letters, digits, ' and - (the game's files and its "
                           "font take no others)" % (TITLES[pool].lower(), n))
    return out


def advice(pools):
    """Warnings that do not stop the write."""
    out = []
    n = len(pools.get("characters") or [])
    if 0 < n < 20:
        out.append("only %d men's names: the game will repeat them often (vanilla factions have 25-150)" % n)
    if not pools.get("surnames"):
        out.append("no surnames: the faction's men get a first name only (as Dacia's and Numidia's do)")
    return out


def section(faction, pools, nl="\r\n"):
    """The faction's section as descr_names.txt writes it."""
    lines = ["faction: %s" % faction, ""]
    for pool in POOLS:
        names = pools.get(pool) or []
        if names:
            lines.append("\t" + pool)
            lines += ["\t\t" + key_of(n) for n in names]
            lines.append("")
    return lines + [""]


def used_names(mod, faction, plan=None):
    """{pool: [keys]} of the faction's current list that its characters and family records already carry
    in any campaign's descr_strat (first names, surnames): a new list must keep them, or the game crashes."""
    from .strat import Strat, faction_names
    old = mod.name_pool(faction) or {}
    firsts, rests = set(), set()
    for c in mod.campaigns():
        p = mod.campaign_file(c, "descr_strat.txt")
        f = plan.files[p] if plan is not None and p in plan.files else mod.load(p)
        for n in faction_names(Strat(f), faction):
            parts = n.split(None, 1)             # the first name, then the surname (which may hold a space)
            firsts.add(parts[0])
            if len(parts) > 1:
                rests.add(" ".join(parts[1].split()))
    return {pool: [k for k in old.get(pool) or [] if (k in rests if pool == "surnames" else k in firsts)]
            for pool in POOLS}


def keep_used(mod, faction, pools, plan=None):
    """pools with the names the faction's characters already carry added back: (pools, [names added])."""
    out = {p: list(pools.get(p) or []) for p in POOLS}
    added = []
    for pool, keys in used_names(mod, faction, plan).items():
        have = {key_of(n).lower() for n in out[pool]}
        for k in keys:
            if k.lower() not in have:
                out[pool].append(Kept(k))
                added.append(k)
    return out, added


def apply(plan, faction, pools):
    """Write the faction's own name list: its section in descr_names.txt (replacing the one it had alone;
    taken out of a shared header), the names.txt strings and the lookup keys that are missing. Names the
    faction's characters already carry stay in the list (said in Preview)."""
    from .moddata import name_sections
    bad = problems(pools)
    if bad:
        raise ValueError("name list of %s: %s" % (faction, "; ".join(bad)))
    mod = plan.mod
    if mod.name_pool(faction):
        pools, kept = keep_used(mod, faction, pools, plan)
        if kept:
            plan.warn(None, "%s's characters already carry %d name(s) of its old list (%s%s): kept in the new "
                            "list, or the game would crash on them" % (
                                faction, len(kept), ", ".join(kept[:8]), "..." if len(kept) > 8 else ""))
    f = plan.edit(mod.file("names"))
    heads = name_sections(f.texts())
    new = section(faction, pools)
    own = [k for k, (_, o) in enumerate(heads) if o == [faction]]
    shared = [k for k, (_, o) in enumerate(heads) if faction in o and o != [faction]]
    for k in shared:                                   # BI: 'faction: empire_east, empire_east_rebels'
        at, owners = heads[k]
        f.set(at, "faction: " + ", ".join(o for o in owners if o != faction))
    if own:
        k = own[0]
        s = heads[k][0]
        e = heads[k + 1][0] if k + 1 < len(heads) else len(f)
        texts = f.texts()
        while e > s + 1 and texts[e - 1].strip().startswith(";") and not texts[e - 1].strip().startswith(";;;"):
            e -= 1                                     # a comment heading the next section stays with it
        f.raw[s:e] = [f.make(t) for t in new]
        plan.note(f, "%s's name list replaced (%s)" % (faction, counts(pools)))
    else:
        slave = next((i for i, o in heads if "slave" in o), None)
        f.insert(slave if slave is not None else len(f), new)
        plan.note(f, "%s's own name list (%s)" % (faction, counts(pools)))
    if shared:
        plan.note(f, "%s no longer shares the name list of %s" % (
            faction, ", ".join(o for k in shared for o in heads[k][1] if o != faction)))
    keys = [(key_of(n), str(n).replace("_", " ")) for pool in POOLS for n in pools.get(pool) or []]
    tp = mod.text_file("names.txt")
    if tp:
        t = plan.edit(tp)
        have = {m.group(1).lower() for m in (re.match(r"\s*\{([^}]*)\}", x) for x in t.texts()) if m}
        add = [(k, n) for k, n in keys if k.lower() not in have]
        if add:
            t.insert(_end(t.texts()), ["{%s}\t\t\t%s" % (k, n) for k, n in add])
            plan.note(t, "%d name(s) the game shows added" % len(add))
    else:
        plan.warn(None, "no text/names.txt found: the game would show the names' keys")
    lp = mod.find("descr_names_lookup.txt")
    if lp:
        lk = plan.edit(lp)
        have = {x.strip().lower() for x in lk.texts()}
        add = [k for k, _ in keys if k.lower() not in have]
        if add:
            lk.insert(_end(lk.texts()), add)
            plan.note(lk, "%d name key(s) added to the lookup" % len(add))


def _end(texts):
    end = len(texts)
    while end and not texts[end - 1].strip():
        end -= 1
    return end


def counts(pools):
    return ", ".join("%d %s" % (len(pools.get(p) or []), TITLES[p].lower()) for p in POOLS)
