"""What the game's character panel shows, read from the files (both games): the attributes the traits and the
retinue give (drawn as pips 0 - 10), the traits by the level names players see (export_VnVs), the retinue with its
pictures (ui/ancillaries) and names (export_ancillaries). The Character editor draws it beside the person's form.

M2TW keeps its string tables as text/<name>.txt and / or the compiled text/<name>.txt.strings.bin: u16 2, u16 2048,
u32 count, then per entry a u16-counted UTF-16 key and a u16-counted UTF-16 text. The .txt is read when both lie
there (the game builds the .bin again from a newer .txt)."""

import os
import re
import struct

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
_cache = {}


def read_strings_bin(data):
    """{key: text} of a Medieval II .strings.bin."""
    out = {}
    if len(data) < 8:
        return out
    count = struct.unpack_from("<I", data, 4)[0]
    p = 8
    for _ in range(count):
        texts = []
        for _ in range(2):
            if p + 2 > len(data):
                return out
            n = struct.unpack_from("<H", data, p)[0]
            p += 2
            texts.append(data[p:p + 2 * n].decode("utf-16-le", "replace"))
            p += 2 * n
        out[texts[0]] = texts[1]
    return out


def strings(mod, name):
    """{KEY upper: text} of a string table (name like 'export_VnVs.txt'): the .txt the game reads, else its
    .strings.bin; {} when neither is there. Cached by the files' times."""
    txt = mod.text_file(name)
    binp = None
    if not txt:
        for folder in mod.text_dirs():
            for n in os.listdir(folder):
                if n.lower() == name.lower() + ".strings.bin":
                    binp = os.path.join(folder, n)
                    break
            if binp:
                break
    path = txt or binp
    if not path:
        return {}
    key = (path, os.path.getmtime(path))
    if key in _cache:
        return _cache[key]
    out = {}
    if txt:
        # a text runs on until the next {KEY} or comment line (the tables' own way: a description often starts
        # on the line under its key)
        key, parts = None, []

        def done():
            if key is not None:
                while parts and not parts[-1].strip():
                    parts.pop()
                out.setdefault(key, "\n".join(p.strip() for p in parts).strip())
        for line in mod.load(txt).texts():
            s = line.lstrip()
            m = re.match(r"\{([^}]+)\}(.*)$", s)
            if m:
                done()
                key, parts = m.group(1).upper(), [m.group(2)]
            elif s.startswith("\u00ac"):
                done()
                key, parts = None, []
            elif key is not None:
                parts.append(line)
        done()
    else:
        with open(binp, "rb") as fh:
            out = {k.upper(): v for k, v in read_strings_bin(fh.read()).items()}
    _cache[key] = out
    return out


def shown(table, key):
    """The text players see for a key, else the key made readable (Promising_Defender -> Promising Defender)."""
    got = table.get((key or "").upper())
    return got if got else (key or "").replace("_", " ")


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
