"""What the game's character panel shows, read from the files (both games): the attributes the traits and the
retinue give (drawn as pips 0 - 10), the traits by the level names players see (export_VnVs), the retinue with its
pictures (ui/ancillaries) and names (export_ancillaries). The Character editor draws it beside the person's form.

M2TW keeps its string tables as text/<name>.txt and / or the compiled text/<name>.txt.strings.bin: u16 2, u16 2048,
u32 count, then per entry a u16-counted UTF-16 key and a u16-counted UTF-16 text. The .txt is read when both lie
there (the game builds the .bin again from a newer .txt)."""

import os

from .strtables import read_strings_bin, shown, strings  # noqa: F401  (the panel's texts)

# the attributes the game's panel shows, per game and kind of character (named characters / generals: 'family')
PANEL = {
    "medieval2": {"family": ("Command", "Chivalry", "Loyalty", "Piety"),
                  "spy": ("Subterfuge",), "assassin": ("Subterfuge",), "diplomat": ("Influence",),
                  "princess": ("Charm",), "merchant": ("Finance",), "priest": ("Piety",), "heretic": ("Piety",),
                  "witch": ("Piety",), "inquisitor": ("Piety",), "admiral": ("Command",)},
    "rome": {"family": ("Command", "Influence", "Management"),
             "spy": ("Subterfuge",), "assassin": ("Subterfuge",), "diplomat": ("Influence",),
             "admiral": ("Command",)},
}


def panel_kind(kind):
    return "family" if kind in ("named character", "general", "record") else kind


def attributes(game, kind, role, traits, trait_defs, ancs, anc_defs):
    """[(attribute, value)] the panel shows: every effect of the character's traits (at their levels) and
    retinue added up, for the attributes of his kind (Medieval II: Authority for the leader and the heir in place
    of Loyalty, Dread when the chivalry is below 0)."""
    total = {}
    for t, n in traits:
        eff = (trait_defs.get(t) or {}).get("effects") or []
        if 0 < n <= len(eff):
            for a, v in eff[n - 1]:
                total[a] = total.get(a, 0) + v
    for a in ancs:
        for at, v in (anc_defs.get(a) or {}).get("effects") or []:
            total[at] = total.get(at, 0) + v
    names = list(PANEL.get(game, PANEL["rome"]).get(panel_kind(kind), ()))
    out = []
    for name in names:
        if game == "medieval2" and name == "Loyalty" and role in ("leader", "heir"):
            name = "Authority"
        value = total.get(name, 0)
        if name == "Chivalry" and value < 0:
            name, value = "Dread", -value
        out.append((name, value))
    return out


def effects_text(effects):
    """'+1 Defence, -2 Loyalty'."""
    return ", ".join("%+d %s" % (v, a) for a, v in effects)


def ancillary_picture(mod, image, culture=None):
    """The retinue card's picture on disk (ui/ancillaries[/<culture>]/<image>, .dds too), or None."""
    from .clone import picture_file
    if not image:
        return None
    for rel in (["ui/ancillaries/%s/%s" % (culture, image)] if culture else []) + ["ui/ancillaries/%s" % image]:
        got = picture_file(mod.data, rel)
        if got:
            return got[1]
    from .campaignrules import game_data
    base = game_data(mod)
    if base and os.path.normcase(base) != os.path.normcase(mod.data):
        for rel in (["ui/ancillaries/%s/%s" % (culture, image)] if culture else []) + ["ui/ancillaries/%s" % image]:
            got = picture_file(base, rel)
            if got:
                return got[1]
    return None


def panel(mod, person, trait_defs, anc_defs, culture=None):
    """What the panel shows for a person of the Character editor: {'name', 'line' (kind, role), 'age',
    'attributes': [(name, value)], 'traits': [(level name shown, trait, level, effects text)], 'retinue':
    [(name shown, ancillary, picture or None, effects text)]}."""
    from .limits import game_kind
    game = game_kind(mod)
    vnv = strings(mod, "export_VnVs.txt")
    anct = strings(mod, "export_ancillaries.txt")
    traits = list(person.get("traits") or [])
    ancs = list(person.get("ancillaries") or [])
    role = person.get("role") or ""
    kind = person.get("kind") or ("family member" if person.get("source") != "map" else "")
    out = {"name": person.get("name", ""), "age": person.get("age"),
           "line": ", ".join(x for x in (kind, role) if x),
           "attributes": attributes(game, person.get("kind") or "record", role, traits, trait_defs, ancs, anc_defs)
           if person.get("source") == "map" else [],
           "traits": [], "retinue": []}
    for t, n in traits:
        d = trait_defs.get(t) or {}
        levels, eff = d.get("levels") or [], d.get("effects") or []
        lname = levels[n - 1] if 0 < n <= len(levels) else t
        out["traits"].append((shown(vnv, lname), t, n, effects_text(eff[n - 1]) if 0 < n <= len(eff) else ""))
    for a in ancs:
        d = anc_defs.get(a) or {}
        out["retinue"].append((shown(anct, a), a, ancillary_picture(mod, d.get("image"), culture),
                               effects_text(d.get("effects") or [])))
    return out
