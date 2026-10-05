"""Religions: a new one written everywhere the game needs it - Medieval II's religions and Barbarian Invasion's
beliefs (Rome's official expansion; plain Rome has neither).

Barbarian Invasion (bi/data, and a mod made from it): descr_beliefs.txt holds 7 lines a belief - its tag, the paths
of its order / unrest / level pips, and the labels of its name, unrest and order texts (text/expanded_bi.txt).
A town's beliefs come from its buildings (`religious_belief <tag> <n>` in export_descr_buildings.txt) and its
characters' traits - there are no region shares; a new belief is written with its pips and texts, and matters once
a temple carries it (the test mod copies the Christian church chain).

Medieval II:

A religion lives in several places that must agree:
  * descr_religions.txt       its name in the `religions { }` list (the set the engine reads) and its own
                              `religion <name> { pip_path ui/pips/pip_<name>.tga }` block;
  * descr_religions_lookup.txt its name;
  * text/english/religions.txt `{name}Shown name` - a religion with no text crashes the game silently;
  * ui/pips/pip_<name>.tga     its symbol, a 24-bit TGA (16 / 32 bit reported not to work);
  * descr_regions.txt          every region's `religions { ... }` line names it (0 % until set; each line
                              must add up to 100) - in the base map and every campaign's own copy;
  * map.rwm                    removed, so the game rebuilds it.
Optional: factions that follow it (descr_sm_factions `religion`). The engine takes at most 9 religions
(5 in vanilla). Temples, priests, traits and religion-gated mercenaries of the template religion are not
copied; Preview says how many lines name it, so one knows what else could follow."""

import io
import os
import re

from .moddata import _ci, parse_religions, religions_line
from .textio import strip_comment, tokens

from .limits import MAX_RELIGIONS                              # noqa: E402  (the original exe's; REX / M2EX lift it)
RE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def _block(f, key):
    """(start, open, close) line indexes of the first `key` line and its braces, or None."""
    n = len(f.raw)
    for i in range(n):
        t = tokens(f.text(i))
        if t[:1] == [key] and len(t) == 1 or (key != "religions" and t[:2] == key.split()):
            op = next((j for j in range(i, n) if "{" in strip_comment(f.text(j))), None)
            if op is None:
                return None
            cl = next((j for j in range(op, n) if "}" in strip_comment(f.text(j))), None)
            return (i, op, cl) if cl is not None else None
    return None


def beliefs_path(mod):
    """descr_beliefs.txt of a Barbarian Invasion mod (None elsewhere)."""
    return None if _ci(mod.data, "descr_religions.txt") else _ci(mod.data, "descr_beliefs.txt")


def _beliefs(mod):
    """[(tag, [order pip, unrest pip, level pip], [label, unrest, order])] of descr_beliefs.txt."""
    p = beliefs_path(mod)
    if not p:
        return []
    lines = [strip_comment(t).strip() for t in mod.load(p).texts()]
    lines = [t for t in lines if t and not t.startswith(";")]
    return [(c[0], c[1:4], c[4:7]) for c in (lines[i:i + 7] for i in range(0, len(lines) - 6, 7))]


def names(mod):
    """The religions the engine reads: the names in descr_religions.txt's `religions { }` list (Medieval II), or
    descr_beliefs.txt's tags (Barbarian Invasion)."""
    p = _ci(mod.data, "descr_religions.txt")
    if not p:
        return [b[0] for b in _beliefs(mod)]
    f = mod.load(p)
    b = _block(f, "religions")
    if not b:
        return []
    out = []
    for i in range(b[1], b[2] + 1):
        out += [w for w in strip_comment(f.text(i)).replace("{", " ").replace("}", " ").split() if w]
    return out


def _faction_religion_line(f, faction):
    """(line index, religion) of `religion X` in faction's block of descr_sm_factions.txt, or (None, None)."""
    cur = None
    for i in range(len(f.raw)):
        t = tokens(f.text(i))
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1].rstrip(",")
        elif cur == faction and t[:1] == ["religion"] and len(t) > 1:
            return i, t[1]
    return None, None


def faction_religion(mod, faction):
    """The faction's religion (Medieval II: descr_sm_factions.txt `religion catholic`), or None (Rome has none)."""
    path = mod.file("sm_factions")
    return _faction_religion_line(mod.load(path), faction)[1] if path else None


def set_faction_religion(plan, faction, religion):
    """Its `religion` line changed (as the plan leaves descr_sm_factions.txt: a new faction's block is there
    already); the rest of the line - spacing, comment - kept."""
    f = plan.edit(plan.mod.file("sm_factions"))
    i, now = _faction_religion_line(f, faction)
    if i is None:
        raise ValueError("%s has no religion line in descr_sm_factions.txt (Rome's factions have no religion)"
                         % faction)
    known = names(plan.mod) + [s["name"] for s in (plan.opts.get("regions") or {}).get("new_religions") or []]
    if known and religion not in known:
        raise ValueError("'%s' is no religion of this game (%s)" % (religion, ", ".join(known)))
    if now != religion:
        line = f.text(i)
        f.set(i, re.sub(r"(\breligion\s+)%s\b" % re.escape(now), lambda m: m.group(1) + religion, line, count=1))
        plan.note(f, "%s: religion %s (was %s)" % (faction, religion, now))
        follow_religion(plan, faction, now, religion)


def follow_religion(plan, faction, old, new):
    """What hangs on a faction's religion follows it (the web): it leaves the old religion's buildings (temples,
    the guilds of that faith - `religion X` chains of export_descr_buildings.txt: their levels and the priest lines
    in them) and gets the new religion's ones wherever a faction of that religion (of its own culture when there is
    one) has them; its priest figure on the campaign map becomes that faction's (descr_character.txt). A culture or
    'all' that let it in on an old religion's line is written out as the other factions it stood for."""
    from .editors import building_blocks
    from .roster import _spelled_out, add_faction, covers, drop_faction, factions_in, with_factions
    mod = plan.mod
    sm = plan.edit(mod.file("sm_factions"))
    cultures = mod.factions()
    culture = dict(cultures).get(faction)
    peers = [x for x, c in cultures if x not in (faction, "slave") and _faction_religion_line(sm, x)[1] == new]
    if not peers:
        plan.warn(None, "%s: no other faction has the religion %s - its temples, priests and figures were not changed "
                        "(give it the buildings on the Roster tab)" % (faction, new))
        return
    model = next((x for x in peers if dict(cultures).get(x) == culture), peers[0])
    model_culture = dict(cultures).get(model)
    path = mod.file("edb")
    if path:
        e = plan.edit(path)
        left, joined = set(), set()
        for chain, a, b in building_blocks(e):
            rel = next((tokens(e.text(i))[1] for i in range(a, b) if tokens(e.text(i))[:1] == ["religion"]
                        and len(tokens(e.text(i))) > 1), None)
            if rel not in (old, new):
                continue
            for i in range(a, b):
                text = e.text(i)
                names = factions_in(text)
                if names is None:
                    continue
                if rel == old:
                    how = covers(names, faction, culture)
                    if how == "own":
                        out = drop_faction(text, faction)
                    elif how in ("culture", "all"):
                        out = with_factions(text, _spelled_out(names, faction, cultures))
                    else:
                        continue
                    if out is None:
                        plan.warn(e, "%s: a line of several faction groups names only %s - left for you to rewrite"
                                  % (chain, faction))
                        continue
                    e.set(i, out)
                    left.add(chain)
                elif covers(names, model, model_culture) and not covers(names, faction, culture):
                    e.set(i, add_faction(text, faction))
                    joined.add(chain)
        if left:
            plan.note(e, "%s leaves the %s buildings: %s" % (faction, old, ", ".join(sorted(left))))
        if joined:
            plan.note(e, "%s gets the %s buildings %s has: %s" % (faction, new, model, ", ".join(sorted(joined))))
    from .stratmodels import figures, set_figure
    mine = next((x for x in figures(mod, faction, plan.edit) if x["type"] == "priest"), None)
    theirs = next((x for x in figures(mod, model, plan.edit) if x["type"] == "priest"), None)
    if mine and theirs and mine["models"] != theirs["models"][:len(mine["models"])]:
        set_figure(plan, faction, "priest", theirs["models"][:len(mine["models"])])
    plan.warn(None, "%s now %s: units and traits of the old faith (crusaders, jihad, the Pope's favour...) are not "
                    "changed - check the Roster tab" % (faction, new))


def pip_of(mod, religion):
    """The data-relative pip_path of a religion's block, or None."""
    p = _ci(mod.data, "descr_religions.txt")
    if not p:
        return None
    f = mod.load(p)
    b = _block(f, "religion %s" % religion)
    if not b:
        return None
    for i in range(b[1], b[2] + 1):
        t = tokens(f.text(i))
        if t[:1] == ["pip_path"] and len(t) > 1:
            return t[1]
    return None


def _find_data_file(mod, rel):
    """rel under the mod's data, else under the game's own data folder (a mod may lack ui/)."""
    from .buildings import _game_data
    for root in (mod.data, _game_data(mod.data)):
        if not root:
            continue
        p = root
        for part in rel.replace("\\", "/").split("/"):
            p = _ci(p, part) if p and os.path.isdir(p) else None
        if p and os.path.isfile(p):
            return p
    return None


def problems(mod, spec, pending=()):
    """Why this new religion cannot be written (a list of plain sentences; empty = fine).
    spec = {'name', 'shown', 'pip_from', 'picture'}; pending = new religions already waiting."""
    out = []
    have = names(mod)
    if not have:
        return ["this game has no religions - Medieval II's descr_religions.txt or Barbarian Invasion's "
                "descr_beliefs.txt (plain Rome has neither)"]
    if beliefs_path(mod):
        return _belief_problems(mod, spec, pending, have)
    name = (spec.get("name") or "").strip()
    if not RE_NAME.match(name):
        out.append("the name is written in the files: small letters, digits and _ only, a letter first "
                   "(e.g. judaism)")
    if name in have or name in [p["name"] for p in pending]:
        out.append("there is a religion called %s already" % name)
    from .limits import lifted
    if len(have) + len(pending) + 1 > MAX_RELIGIONS and not lifted(mod, "religions"):
        out.append("the original game takes at most %d religions; this mod has %d%s (REX / M2EX lift the limit - "
                   "none of them was found beside the game)" % (
                       MAX_RELIGIONS, len(have), " and %d more waiting" % len(pending) if pending else ""))
    if not (spec.get("shown") or "").strip():
        out.append("give it the name players see (e.g. Judaism) - without a text the game crashes")
    picture = spec.get("picture")
    if picture and not os.path.isfile(picture):
        out.append("the picture %s is not there" % picture)
    if not picture:
        src = pip_of(mod, spec.get("pip_from") or "")
        if not src or not _find_data_file(mod, src):
            out.append("pick a picture for its symbol: %s's (%s) is not in this mod or the game's data" % (
                spec.get("pip_from") or "the religion copied", src or "no pip_path"))
    for f in spec.get("factions") or []:
        if f not in [n for n, _ in mod.factions()]:
            out.append("no faction %s" % f)
    return out


def _belief_file(mod, path):
    """A belief's pip path as descr_beliefs.txt writes it (data/ui/pips/..., bi/data/...) found in the mod or the
    game's data, or None."""
    rel = path.replace("\\", "/")
    for head in ("bi/data/", "data/"):
        if rel.lower().startswith(head):
            rel = rel[len(head):]
            break
    return _find_data_file(mod, rel)


def _belief_problems(mod, spec, pending, have):
    out = []
    name = (spec.get("name") or "").strip()
    if not RE_NAME.match(name):
        out.append("the name is written in the files: small letters, digits and _ only, a letter first "
                   "(e.g. mithraism)")
    if name in have or name in [p["name"] for p in pending]:
        out.append("there is a belief called %s already" % name)
    if not (spec.get("shown") or "").strip():
        out.append("give it the name players see (e.g. Mithraism)")
    picture = spec.get("picture")
    if picture and not os.path.isfile(picture):
        out.append("the picture %s is not there" % picture)
    tpl = next((b for b in _beliefs(mod) if b[0] == spec.get("pip_from")), None)
    if tpl is None:
        out.append("pick the belief whose pips are copied (%s is not one)" % (spec.get("pip_from") or "none"))
    else:
        for pip in tpl[1][:2] + ([] if picture else tpl[1][2:]):
            if not _belief_file(mod, pip):
                out.append("%s's pip %s is not in this mod or the game's data" % (tpl[0], pip))
    return out


def _apply_belief(plan, spec):
    """Barbarian Invasion: the new belief's 7 lines at the end of descr_beliefs.txt, its three pips (the order and
    unrest pips copied from the template belief, the level pip the picture picked - sized like the template's - or
    a copy) and its three texts in text/expanded_bi.txt."""
    mod = plan.mod
    name, shown = spec["name"].strip(), spec["shown"].strip()
    tpl = next(b for b in _beliefs(mod) if b[0] == spec["pip_from"])
    key = name.upper()
    pips = ["data/ui/pips/pip_religion_%s_positive.tga" % name, "data/ui/pips/pip_religion_%s_negative.tga" % name,
            "data/ui/pips/pip_religion_%s.tga" % name]
    f = plan.edit(beliefs_path(mod))
    at = max((i for i in range(len(f.raw)) if f.text(i).strip()), default=-1) + 1
    f.insert(at, [""] + [name] + pips + ["%s_LABEL" % key, "%s_UNREST" % key, "%s_ORDER" % key])
    plan.note(f, "belief %s added (its pips and texts below)" % name)
    for k, (dst, src) in enumerate(zip(pips, tpl[1])):
        srcp = _belief_file(mod, src)
        if k == 2 and spec.get("picture"):
            data = _pip_bytes(mod, dict(spec, pip_from=None), size_of=srcp)
        else:
            with open(srcp, "rb") as fh:
                data = fh.read()
        plan.binary(os.path.join(mod.data, *dst[len("data/"):].split("/")), data)
        plan.notes.append((dst, "%s's %s pip (%s)" % (name, ("order", "unrest", "level")[k], "the picture picked"
                                                          if k == 2 and spec.get("picture") else
                                                          "a copy of %s's" % tpl[0])))
    text = mod.text_file("expanded_bi.txt")
    lines = ["{%s_LABEL}\t\t\t%s" % (key, shown),
             "{%s_ORDER}\t\t\t%s is improving public order in this settlement" % (key, shown),
             "{%s_UNREST}\t\t\t%s is causing unrest in this settlement" % (key, shown)]
    if text:
        tf = plan.edit(text)
        at = max((i for i in range(len(tf.raw)) if tf.text(i).strip()), default=-1) + 1
        tf.insert(at, lines)
        plan.note(tf, "{%s_LABEL} %s and its order / unrest texts" % (key, shown))
    else:
        plan.warn(None, "no text/expanded_bi.txt found - add %s there" % "; ".join(lines))
    if spec.get("factions"):
        plan.warn(None, "Barbarian Invasion's factions have no religion line - %s spreads by the buildings that "
                        "carry it (religious_belief %s) and by traits" % (name, name))
    _mentions(plan, spec.get("pip_from"), name)


def _pip_bytes(mod, spec, size_of=None):
    """The new symbol as a 24-bit TGA: the picture given, sized like the template's pip, or the
    template's pip copied as it is."""
    src = size_of or _find_data_file(mod, pip_of(mod, spec.get("pip_from") or "") or "")
    picture = spec.get("picture")
    if not picture:
        with open(src, "rb") as fh:
            return fh.read()
    from PIL import Image
    im = Image.open(picture).convert("RGB")
    if src:
        size = Image.open(src).size
        if im.size != size:
            im = im.resize(size, Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="TGA", rle=False)
    return out.getvalue()


def region_files(mod):
    """Every descr_regions.txt the campaigns read (the base map's and each campaign's own copy)."""
    seen = []
    for camp in mod.campaigns() or [None]:
        p = mod.campaign_file(camp, "descr_regions.txt") if camp else _ci(mod.base, "descr_regions.txt")
        if p and p not in seen:
            seen.append(p)
    base = _ci(mod.base, "descr_regions.txt")
    if base and base not in seen:
        seen.append(base)
    return seen


def apply(plan, specs):
    """Write the new religions (specs = [{'name', 'shown', 'pip_from', 'picture', 'factions'}])."""
    if not specs:
        return
    mod = plan.mod
    done = []
    for spec in specs:
        why = problems(mod, spec, done)
        if why:
            raise ValueError("new religion %s: %s" % (spec.get("name"), "; ".join(why)))
        done.append(spec)
    if beliefs_path(mod):
        for spec in specs:
            _apply_belief(plan, spec)
        return
    path = _ci(mod.data, "descr_religions.txt")
    f = plan.edit(path)
    for spec in specs:
        name = spec["name"].strip()
        b = _block(f, "religions")
        ind = next((f.text(i)[:len(f.text(i)) - len(f.text(i).lstrip())] for i in range(b[1] + 1, b[2])
                    if f.text(i).strip()), "\t")
        f.insert(b[2], [ind + name])
        pip = "ui/pips/pip_%s.tga" % name
        # its own block after the last religion block, in the file's own layout
        last = max(i for i in range(len(f.raw)) if tokens(f.text(i))[:1] == ["religion"])
        tpl = _block(f, "religion %s" % tokens(f.text(last))[1])
        f.insert(tpl[2] + 1, ["", "religion %s" % name, "{", "\tpip_path\t%s" % pip, "}"])
        plan.note(f, "religion %s added (symbol %s)" % (name, pip))
        lookup = _ci(mod.data, "descr_religions_lookup.txt")
        if lookup:
            lf = plan.edit(lookup)
            at = max((i for i in range(len(lf.raw)) if lf.text(i).strip()), default=-1) + 1
            lf.insert(at, [name])
            plan.note(lf, "%s listed" % name)
        text = mod.text_file("religions.txt")
        if text:
            tf = plan.edit(text)
            at = max((i for i in range(len(tf.raw)) if tf.text(i).strip()), default=-1) + 1
            tf.insert(at, ["{%s}%s" % (name, spec["shown"].strip())])
            plan.note(tf, "{%s} %s" % (name, spec["shown"].strip()))
        else:
            plan.warn(None, "no text/english/religions.txt found - add {%s}%s there, or the game crashes"
                      % (name, spec["shown"].strip()))
        plan.binary(os.path.join(mod.data, *pip.split("/")), _pip_bytes(mod, spec))
        plan.notes.append((pip, "the symbol of %s (%s)" % (name, "the picture picked, 24-bit" if spec.get("picture")
                                                           else "a copy of %s's" % spec.get("pip_from"))))
        for rp in region_files(mod):
            rf = plan.edit(rp)
            n = 0
            for i in range(len(rf.raw)):
                line = rf.text(i)
                code = strip_comment(line)
                if code.strip().startswith("religions"):
                    rel = parse_religions(code)
                    if name not in rel:
                        rel[name] = 0
                        indent = line[:len(line) - len(line.lstrip())]
                        rf.set(i, indent + religions_line(rel))
                        n += 1
            if n:
                plan.note(rf, "%d region(s) name %s at 0 %% (set its share with Religions...)" % (n, name))
            plan.delete(os.path.join(os.path.dirname(rp), "map.rwm"), "the game rebuilds it on the next start")
        _factions(plan, name, spec.get("factions") or [])
        _mentions(plan, spec.get("pip_from"), name)


def _factions(plan, religion, factions):
    """descr_sm_factions.txt: these factions follow the new religion."""
    if not factions:
        return
    f = plan.edit(plan.mod.file("sm_factions"))
    cur = None
    for i in range(len(f.raw)):
        t = tokens(f.text(i))
        if t[:1] == ["faction"] and len(t) > 1:
            cur = t[1].rstrip(",")
        elif t[:1] == ["religion"] and cur in factions:
            f.set(i, re.sub(r"(religion\s+)\S+", r"\g<1>%s" % religion, f.text(i), count=1))
            plan.note(f, "%s now follows %s" % (cur, religion))


def _mentions(plan, template, name):
    """Say how many lines of the files that give a religion its weight name the template religion."""
    if not template:
        return
    mod = plan.mod
    counts = []
    for rel, label in (("export_descr_buildings.txt", "buildings (temples, conversion)"),
                       ("export_descr_character_traits.txt", "traits"),
                       ("export_descr_ancillaries.txt", "ancillaries"),
                       ("descr_faction_standing.txt", "faction standing"),
                       ("descr_campaign_ai_db.xml", "campaign AI")):
        p = _ci(mod.data, rel)
        if not p:
            continue
        n = sum(1 for l in mod.load(p).texts() if re.search(r"\b%s\b" % re.escape(template), strip_comment(l)))
        if n:
            counts.append("%s %d" % (label, n))
    if counts:
        plan.warn(None, "%s has no temples, traits or AI rules of its own yet - %s is named in: %s. "
                        "The religion works (regions, factions, the symbol); what makes it matter is still "
                        "%s's" % (name, template, ", ".join(counts), template))


__all__ = ["MAX_RELIGIONS", "names", "pip_of", "problems", "apply", "region_files", "beliefs_path"]
