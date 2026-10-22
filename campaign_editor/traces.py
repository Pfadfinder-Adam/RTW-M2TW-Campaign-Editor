"""Traces of another faction in one faction: what it still shares with, or copied from, another (the user,
2026-10-22: a new faction 'with nothing in common with an existing one' - colours, symbols, pictures, texts).

None of these stops the game: Check mod files lists them for the factions the editor made (their template known from
the backups), the New faction plan notes them for the faction it makes. Each trace: {'what', 'other', 'count',
'example', 'where'} - 'where' is the editor's place that changes it.
"""

import os
import re

from .textio import tokens

RE_RGB = re.compile(r"red\s*(\d+)\s*,\s*green\s*(\d+)\s*,\s*blue\s*(\d+)")
PICTURE_EXT = (".tga", ".dds", ".png", ".bmp")


def sm_blocks(mod, load=None):
    """{faction: {field: [words]}} of descr_sm_factions.txt (the first line of each field)."""
    f = (load or mod.load)(mod.file("sm_factions"))
    out, cur = {}, None
    for line in f.texts():
        tk = tokens(line)
        if len(tk) >= 2 and tk[0] == "faction":
            cur = out.setdefault(tk[1].rstrip(","), {})
        elif tk and cur is not None:
            cur.setdefault(tk[0], tk[1:])
            m = RE_RGB.search(line)
            if m and tk[0] in ("primary_colour", "secondary_colour"):
                cur[tk[0]] = tuple(int(x) for x in m.groups())
    return out


def colour_gap(a, b):
    """How far two colours look apart (0..~765): the 'redmean' weighting of the RGB distance."""
    rm = (a[0] + b[0]) / 2.0
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return ((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db) ** 0.5


NEAR = 60          # two colours this close look alike on the map (a step of ~20 in each of red, green and blue)


def colour_traces(blocks, faction):
    mine = blocks.get(faction) or {}
    p, s = mine.get("primary_colour"), mine.get("secondary_colour")
    out = []
    if not isinstance(p, tuple):
        return out
    for other, b in blocks.items():
        if other in (faction, "slave") or not isinstance(b.get("primary_colour"), tuple):
            continue
        near_p = colour_gap(p, b["primary_colour"]) < NEAR
        q = b.get("secondary_colour")
        near_s = isinstance(s, tuple) and isinstance(q, tuple) and colour_gap(s, q) < NEAR
        if near_p and (near_s or not isinstance(s, tuple)):
            out.append({"what": "colours almost the same as another faction's", "other": other, "count": 1,
                        "example": "primary %d %d %d / %d %d %d" % (p + b["primary_colour"]), "where": "colours"})
    return out


def line_traces(blocks, faction):
    """The same 3D symbol file, or a movie only one other faction shows, as another faction."""
    mine = blocks.get(faction) or {}
    out = []
    for field in sorted(mine):
        if field != "symbol" and not field.endswith("_movie"):
            continue
        val = (mine[field] or [""])[0].replace("\\", "/").lower()
        if not val:
            continue
        who = sorted(o for o, b in blocks.items() if o != faction and
                     (b.get(field) or [""])[0].replace("\\", "/").lower() == val)
        if who and (field == "symbol" or len(who) == 1):
            out.append({"what": "%s the same file as another faction's" % (
                            "3D symbol" if field == "symbol" else field.replace("_", " ")),
                        "other": ", ".join(who), "count": 1, "example": val,
                        "where": "art" if field == "symbol" else "files"})
    return out


def texture_traces(mod, faction, load=None):
    """descr_model_battle / descr_model_strat: the faction's texture lines naming a picture another faction's line
    names too - its men and agents dressed as the other's."""
    out = []
    for key, what in (("model_battle", "battle textures of its units"), ("model_strat", "campaign-map figure textures")):
        path = mod.file(key)
        if not path:
            continue
        users = {}
        for line in (load or mod.load)(path).texts():
            tk = [t.rstrip(",") for t in tokens(line)]
            if len(tk) >= 3 and tk[0] in ("texture", "texture_attachments", "model_sprite", "model_flexi",
                                          "model_flexi_m"):
                ref = tk[-1].replace("\\", "/").lower()
                users.setdefault(ref, set()).add(tk[1])
        shared = {}
        for ref, who in users.items():
            if faction in who:
                for o in who - {faction}:
                    shared.setdefault(o, []).append(ref)
        for o, refs in sorted(shared.items(), key=lambda kv: -len(kv[1])):
            out.append({"what": what + " shared with another faction", "other": o, "count": len(refs),
                        "example": os.path.basename(refs[0]), "where": "recolour"})
    return out


def _same_bytes(a, b):
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def card_traces(mod, faction, names):
    """Unit cards and info pictures pixel for pixel another faction's (ui/units/<faction>/ beside ui/units/<x>/)."""
    from .moddata import _ci
    out = {}
    for folder in ("units", "unit_info"):
        for root in [os.path.join(d, "ui", folder) for d in mod.roots()]:
            mine = _ci(root, faction) if os.path.isdir(root) else None
            if not mine or not os.path.isdir(mine):
                continue
            others = [o for o in os.listdir(root) if o.lower() != faction.lower() and o.lower() in names and
                      os.path.isdir(os.path.join(root, o))]
            for n in os.listdir(mine):
                for o in others:
                    p = _ci(os.path.join(root, o), n)
                    if p and _same_bytes(os.path.join(mine, n), p):
                        out.setdefault(o.lower(), []).append(n)
                        break
            break                                       # the mod's own folder counts first
    return [{"what": "unit cards pixel for pixel another faction's", "other": o, "count": len(ns), "example": ns[0],
             "where": "recolour"} for o, ns in sorted(out.items(), key=lambda kv: -len(kv[1]))]


def picture_traces(mod, campaign, faction, names):
    """The faction's own pictures (buttons, logos, banners, captain cards...) pixel for pixel a picture of another
    faction (a file named after it beside it), and pictures its lines share with another faction."""
    from .clone import _token_hit
    from .factionart import faction_pictures
    out = {}
    for e in faction_pictures(mod, campaign, faction):
        p = e.get("path")
        if not p or not os.path.isfile(p):
            continue
        for o in e.get("shared") or []:
            out.setdefault(o, []).append(e.get("label") or os.path.basename(p))
        folder, mine = os.path.dirname(p), os.path.basename(p).lower()
        try:
            beside = os.listdir(folder)
        except OSError:
            continue
        for n in beside:
            if n.lower() == mine or not n.lower().endswith(PICTURE_EXT):
                continue
            o = next((x for x in names if x != faction and _token_hit(n, x)), None)
            if o and _same_bytes(p, os.path.join(folder, n)):
                out.setdefault(o, []).append(e.get("label") or os.path.basename(p))
                break
    return [{"what": "pictures pixel for pixel (or the same file as) another faction's", "other": o, "count": len(ls), "example": ls[0], "where": "art"}
            for o, ls in sorted(out.items(), key=lambda kv: -len(kv[1]))]


def text_traces(mod, campaign, faction, words):
    """The faction's own texts (keys naming it) that still name another faction ('The Gauls are victorious' in a
    clone of the Gauls): words = {faction: [its full / short name, adjective, people]}."""
    F = faction.upper()
    own = " ".join(words.get(faction) or [])
    # a word of its own name ('CE Gaul Clone' holds Gaul) is its own, not a trace
    words = {o: [w for w in ws if not re.search(r"\b%s\b" % re.escape(w), own)] for o, ws in words.items()}
    rx = {o: re.compile(r"\b(%s)\b" % "|".join(re.escape(w) for w in ws)) for o, ws in words.items()
          if o != faction and ws}
    mine = re.compile(r"(^|_)%s(_|$)" % re.escape(F))
    out = {}
    key_rx = re.compile(r"^\s*\{([A-Za-z0-9_]+)\}(.*)$")
    for path in mod.campaign_text_files(campaign):
        for line in mod.load(path).texts():
            m = key_rx.match(line)
            if not m or not mine.search(m.group(1).upper()):
                continue
            for o, r in rx.items():
                hit = r.search(m.group(2))
                if hit:
                    out.setdefault(o, []).append("{%s} '%s'" % (m.group(1), hit.group(1)))
    return [{"what": "of its texts naming another faction", "other": o, "count": len(ls), "example": ls[0], "where": "texts"}
            for o, ls in sorted(out.items(), key=lambda kv: -len(kv[1]))]


def name_traces(mod, faction):
    """Its name list is (nearly) another faction's: 80 % of its first names theirs too."""
    from .moddata import name_sections
    f = mod.load(mod.file("names"))
    texts = f.texts()
    heads = name_sections(texts)
    lists = {}
    for k, (i, owners) in enumerate(heads):
        e = heads[k + 1][0] if k + 1 < len(heads) else len(texts)
        names, part = set(), None
        for line in texts[i + 1:e]:
            w = line.split(";")[0].strip()
            if w in ("characters", "surnames", "women"):
                part = w
            elif w and part == "characters":
                names.add(w.lower())
        for o in owners:
            lists.setdefault(o, set()).update(names)
    mine = lists.get(faction) or set()
    out = []
    if len(mine) < 5:
        return out
    for o, ns in lists.items():
        if o in (faction, "slave") or not ns:
            continue
        if len(mine & ns) >= 0.8 * len(mine):
            out.append({"what": "first names from another faction's list", "other": o, "count": len(mine & ns),
                        "example": sorted(mine & ns)[0], "where": "names"})
    return out


def faction_words(mod, campaign, factions):
    """{faction: [full name, short name, adjective, people]} as its texts give them (build.template_display)."""
    from .build import template_display
    out = {}
    for fac in factions:
        d = template_display(mod, fac, campaign)
        ws = {d.get(k) for k in ("display_name", "short_name", "adjective", "people") if d.get(k)}
        out[fac] = sorted((w for w in ws if len(w) >= 3), key=len, reverse=True)
    return out


def traces(mod, campaign, faction):
    """Every trace of another faction in `faction`, most first."""
    blocks = sm_blocks(mod)
    names = [n.lower() for n, _ in mod.factions()]
    out = colour_traces(blocks, faction) + line_traces(blocks, faction)
    out += picture_traces(mod, campaign, faction, names)
    out += card_traces(mod, faction, set(names))
    out += texture_traces(mod, faction)
    out += name_traces(mod, faction)
    out += text_traces(mod, campaign, faction, faction_words(mod, campaign, [n for n in names if n != "slave"]))
    return out


def made_factions(mod):
    """{faction: its template} of the factions the editor made in this mod that it still has (the backups'
    manifests: 'faction' made from 'template')."""
    import json
    from .plan import backups
    have = {n for n, _ in mod.factions()}
    out = {}
    for bdir in backups(mod):
        try:
            with open(os.path.join(bdir, "manifest.json"), encoding="utf-8") as fh:
                m = json.load(fh)
        except (OSError, ValueError):
            continue
        f, t = m.get("faction"), m.get("template")
        if f in have and t in have and f != t:
            out.setdefault(f, t)
    return out


def summary(found):
    """The traces as lines a person reads, one per kind, the factions most shared with first: '34 battle textures
    of its units shared with another faction: gauls (34), britons - e.g. ...'."""
    kinds = {}
    for t in found:
        kinds.setdefault(t["what"], []).append(t)
    out = []
    for what, ts in kinds.items():
        ts = sorted(ts, key=lambda t: -t["count"])
        top = ts[0]
        who = ", ".join("%s (%d)" % (t["other"], t["count"]) if t["count"] > 1 else t["other"] for t in ts[:6])
        more = " and %d more" % (len(ts) - 6) if len(ts) > 6 else ""
        out.append("%s%s: %s%s - e.g. %s" % ("%d " % top["count"] if top["count"] > 1 else "", what, who, more,
                                             top["example"]))
    return out


def describe(t):
    """One line a person reads: '36 battle textures of its units shared with another faction: gauls (e.g. x.tga)'."""
    return "%s%s: %s (e.g. %s)" % ("%d " % t["count"] if t["count"] > 1 else "", t["what"], t["other"], t["example"])


def plan_note(plan):
    """What a new faction still has of its template when its plan is made - said in the plan (the files are not
    written yet, so traces() cannot read them): its pictures copied, its men's textures, its names, its units."""
    t, new = plan.template, plan.new
    pics = [d for _, d in plan.copies if not re.search(r"[\\/]ui[\\/]unit(s|_info)[\\/]", d)]
    cards = [d for _, d in plan.copies if re.search(r"[\\/]ui[\\/]unit(s|_info)[\\/]", d)]
    parts = []
    zero = plan.opts.get("from_zero")
    if zero and (pics or cards):
        # New faction > From zero: its emblem drawn on the signs, the rest recoloured by the part after this one
        parts.append("%d picture(s) and its men's textures copied from it - recoloured in its own colours right "
                     "after it is written (the same Apply)%s" % (len(pics) + len(cards), "" if plan.opts.get("art")
                                                                   else "; no emblem picked: its signs are %s's" % t))
    elif pics:
        parts.append("%d picture(s) copied from it (buttons, logos, banners, captain cards, figures) - Art > "
                     "Faction emblem draws them all from one symbol of its own" % len(pics))
    if cards and not zero:
        parts.append("its unit cards - Art > Recolour all its pictures...")
    tex = [] if zero else [x for x in texture_traces(plan.mod, new, plan.edit) if x["other"] == t]
    if tex:
        parts.append("%d battle / campaign-map texture(s) its men share with it - Recolour gives them copies in its "
                     "own colours" % sum(x["count"] for x in tex))
    if not plan.opts.get("names"):
        parts.append("its name list - Name list... on the New faction tab gives it one of its own")
    if not plan.opts.get("bring"):
        parts.append("its units and buildings - Roster takes out what it should not have")
    if parts:
        plan.note(None, "%s still has of %s: %s. Check mod files lists what is left later (TRACES OF ANOTHER "
                        "FACTION)." % (new, t, "; ".join(parts)))
