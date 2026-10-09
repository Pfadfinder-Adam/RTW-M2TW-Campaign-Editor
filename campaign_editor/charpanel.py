"""What the game's character panel shows, read from the files (both games): the attributes the traits and the
retinue give (drawn as pips 0 - 10), the traits by the level names players see (export_VnVs), the retinue with its
pictures (ui/ancillaries) and names (export_ancillaries). Characters draws it beside the person's form.

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


def _total(traits, trait_defs, ancs, anc_defs, key):
    t = 0
    for name, n in traits:
        eff = (trait_defs.get(name) or {}).get("effects") or []
        if 0 < n <= len(eff):
            t += sum(v for a, v in eff[n - 1] if a == key)
    for a in ancs:
        t += sum(v for at, v in (anc_defs.get(a) or {}).get("effects") or [] if at == key)
    return t


def traits_for(kind, traits, trait_defs, ancs, anc_defs, attribute, want):
    """The person's traits changed so that the panel's attribute reaches want (a click on its pips): a trait he has
    that gives it moved to another level (or taken off), else a trait of his kind that gives that attribute alone
    added at the level that fits - up to three such steps. -> (new traits [(trait, level)], [what changed]) or
    None when nothing of this mod reaches it. Dread is Chivalry below 0; the retinue's part stays as it is."""
    sign, key = (-1, "Chivalry") if attribute == "Dread" else (1, attribute)
    pk = panel_kind(kind)
    traits = [tuple(x) for x in traits]
    have = {t for t, _ in traits}
    anti = set()
    for t in have:
        anti |= set((trait_defs.get(t) or {}).get("anti") or ())

    def gives(t):
        return [sum(v for a, v in lv if a == key) for lv in (trait_defs.get(t) or {}).get("effects") or []]

    def allowed(t):
        who = (trait_defs.get(t) or {}).get("characters") or []
        return not who or "all" in who or pk in who or (pk == "family" and "family" in who)

    shown_attrs = {a for kinds in PANEL.values() for names in kinds.values() for a in names} | {"Authority"}

    def pure(t):      # no other attribute of the panel moves with it (Electability, Law... may)
        return all(a == key or a not in shown_attrs for lv in (trait_defs.get(t) or {}).get("effects") or []
                   for a, _ in lv)
    done, changed = set(), []
    for _ in range(3):
        now = sign * _total(traits, trait_defs, ancs, anc_defs, key)
        if now == want:
            break
        cands = [t for t, _ in traits if t not in done and any(gives(t))] + sorted(
            (t for t in trait_defs if t not in have and t not in done and t not in anti and allowed(t)
             and any(gives(t)) and pure(t)), key=lambda t: -len(gives(t)))
        best = None
        for t in cands:
            cur = dict(traits).get(t, 0)
            g = gives(t)
            base = now - sign * (g[cur - 1] if cur else 0)
            for lvl in range(0, len(g) + 1):
                got = base + sign * (g[lvl - 1] if lvl else 0)
                score = (abs(want - got), 0 if t in have else 1, lvl)
                if best is None or score < best[0]:
                    best = (score, t, lvl, cur)
        if best is None or best[0][0] >= abs(want - now):
            break
        _, t, lvl, cur = best
        done.add(t)
        traits = [x for x in traits if x[0] != t] + ([(t, lvl)] if lvl else [])
        changed.append("%s %s" % (t, ("level %d" % lvl) if lvl else "taken off") if cur or lvl else t)
        have = {x for x, _ in traits}
    if not changed:
        return None
    return traits, changed


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
    """What the panel shows for a person of Characters: {'name', 'line' (kind, role), 'age',
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
