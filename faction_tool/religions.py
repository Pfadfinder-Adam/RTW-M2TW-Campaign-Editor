"""Medieval II religions: a new one written everywhere the game needs it.

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

MAX_RELIGIONS = 9
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


def names(mod):
    """The religions the engine reads: the names in descr_religions.txt's `religions { }` list."""
    p = _ci(mod.data, "descr_religions.txt")
    if not p:
        return []
    f = mod.load(p)
    b = _block(f, "religions")
    if not b:
        return []
    out = []
    for i in range(b[1], b[2] + 1):
        out += [w for w in strip_comment(f.text(i)).replace("{", " ").replace("}", " ").split() if w]
    return out


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
        return ["this game has no descr_religions.txt - religions are Medieval II's (Rome has none)"]
    name = (spec.get("name") or "").strip()
    if not RE_NAME.match(name):
        out.append("the name is written in the files: small letters, digits and _ only, a letter first "
                   "(e.g. judaism)")
    if name in have or name in [p["name"] for p in pending]:
        out.append("there is a religion called %s already" % name)
    if len(have) + len(pending) + 1 > MAX_RELIGIONS:
        out.append("the game takes at most %d religions; this mod has %d%s" % (
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


def _pip_bytes(mod, spec):
    """The new symbol as a 24-bit TGA: the picture given, sized like the template's pip, or the
    template's pip copied as it is."""
    src = _find_data_file(mod, pip_of(mod, spec.get("pip_from") or "") or "")
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
            f.set(i, re.sub(r"(religion\s+)\S+", r"\g<1>%s" % religion, f.text(i), 1))
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


__all__ = ["MAX_RELIGIONS", "names", "pip_of", "problems", "apply", "region_files"]
