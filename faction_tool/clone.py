"""Cloning a faction: every data file that keys something by faction name.

Each step reads a file through the Plan, edits the in-memory copy and records a
note. Nothing touches the disk until Plan.apply().
"""

import os
import re

from .moddata import _ci
from .textio import strip_comment, tokens


def _is_blank(text):
    return strip_comment(text).strip() == ""


def _block_end(f, start, stop_heads, stop_on_blank=True, limit=None):
    """First line after `start` that ends a simple block: a blank line, or a line
    whose first word is in stop_heads."""
    limit = len(f) if limit is None else limit
    j = start + 1
    while j < limit:
        t = f.text(j)
        if stop_on_blank and t.strip() == "":
            break
        tk = tokens(t)
        if tk and tk[0] in stop_heads:
            break
        j += 1
    return j


def _replace_word(text, old, new):
    return re.sub(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(old), new, text)


# ---------------------------------------------------------------------------
# descr_sm_factions.txt / .json
# ---------------------------------------------------------------------------
def sm_factions(plan):
    t, new = plan.template, plan.new
    f = plan.edit(plan.mod.file("sm_factions"))
    starts = [i for i in range(len(f)) if tokens(f.text(i))[:1] == ["faction"]]
    names = [tokens(f.text(i))[1] for i in starts]
    if new in names:
        raise ValueError("faction '%s' already exists in descr_sm_factions.txt" % new)
    if t not in names:
        raise ValueError("template faction '%s' not found" % t)
    k = names.index(t)
    s = starts[k]
    e = starts[k + 1] if k + 1 < len(starts) else len(f)
    block = f.raw[s:e]
    # keep the separator comments that trail the block with it
    out = []
    for raw in block:
        text = raw.rstrip("\r")
        tk = tokens(text)
        if tk[:1] == ["faction"]:
            text = text.replace(t, new, 1)
        elif tk[:1] == ["primary_colour"] and plan.opts.get("primary_colour"):
            r, g, b = plan.opts["primary_colour"]
            text = re.sub(r"red\s*\d+\s*,\s*green\s*\d+\s*,\s*blue\s*\d+", "red %d, green %d, blue %d" % (r, g, b), text)
        elif tk[:1] == ["secondary_colour"] and plan.opts.get("secondary_colour"):
            r, g, b = plan.opts["secondary_colour"]
            text = re.sub(r"red\s*\d+\s*,\s*green\s*\d+\s*,\s*blue\s*\d+", "red %d, green %d, blue %d" % (r, g, b), text)
        out.append(text + ("\r" if raw.endswith("\r") else ""))
    if out[-1].strip():
        out.append(f.make(""))
    at = starts[names.index("slave")] if "slave" in names else len(f)
    f.insert_raw(at, out)
    plan.note(f, "faction block copied from %s (before slave)" % t)
    plan.faction_count = len(names) + 1


def sm_factions_json(plan):
    path = plan.mod.file("sm_factions_json")
    if not path:
        return
    t, new = plan.template, plan.new
    f = plan.edit(path)
    lines = f.texts()
    def entry(name):
        for i, l in enumerate(lines):
            if re.match(r'\s*"%s"\s*:' % re.escape(name), l):
                depth, seen = 0, False
                for j in range(i, len(lines)):
                    depth += lines[j].count("{") - lines[j].count("}")
                    seen = seen or "{" in lines[j]
                    if seen and depth == 0:
                        return i, j + 1
        return None
    if entry(new):
        raise ValueError("faction '%s' already exists in descr_sm_factions.json" % new)
    span = entry(t)
    if not span:
        plan.warn(f, "template not found in the JSON file - left unchanged")
        return
    block = lines[span[0]:span[1]]
    T, N = t.upper(), new.upper()
    block[0] = block[0].replace('"%s"' % t, '"%s"' % new, 1)
    for n, l in enumerate(block):
        block[n] = l.replace('"%s"' % T, '"%s"' % N).replace('"%s_DESCR"' % T, '"%s_DESCR"' % N)
    for key in ("primary", "secondary"):
        rgb = plan.opts.get(key + "_colour")
        if rgb:
            for n, l in enumerate(block):
                if re.match(r'\s*"%s"\s*:\s*\[' % key, l):
                    block[n] = re.sub(r"\[[^\]]*\]", "[ %d, %d, %d ]" % tuple(rgb), l, 1)
    if not block[-1].rstrip().endswith(","):
        block[-1] = block[-1].rstrip() + ","
    target = entry("slave")
    at = target[0] if target else span[1]
    if not target:
        # appending after the template: the template needs a comma, the copy must not end with one
        if not lines[span[1] - 1].rstrip().endswith(","):
            f.set(span[1] - 1, lines[span[1] - 1].rstrip() + ",")
        block[-1] = block[-1].rstrip().rstrip(",")
    f.insert(at, block)
    plan.note(f, "faction entry copied from %s" % t)


# ---------------------------------------------------------------------------
# Files with "faction <name>" blocks
# ---------------------------------------------------------------------------
def faction_blocks(plan, key, braced=False, heads=("faction", "type")):
    path = plan.mod.file(key)
    if not path:
        return
    t, new = plan.template, plan.new
    f = plan.edit(path)
    i = 0
    count = 0
    while i < len(f):
        tk = tokens(f.text(i))
        if tk[:1] == ["faction"] and t in tk[1:]:
            if len(tk) > 2:
                # "faction a, b, c": add the new name to the list
                f.set(i, _replace_word(f.text(i), t, "%s, %s" % (t, new)))
                count += 1
                i += 1
                continue
            if braced:
                depth, seen, j = 0, False, i
                while j < len(f):
                    s = strip_comment(f.text(j))
                    depth += s.count("{") - s.count("}")
                    seen = seen or "{" in s
                    j += 1
                    if seen and depth == 0:
                        break
            else:
                j = _block_end(f, i, heads)
            copy = list(f.raw[i:j])
            copy[0] = _replace_word(copy[0], t, new)
            lead_blank = [] if f.text(j - 1).strip() == "" else [f.make("")]
            f.insert_raw(j, lead_blank + copy)
            i = j + len(copy) + len(lead_blank)
            count += 1
            continue
        i += 1
    if count:
        plan.note(f, "%d faction block(s) copied" % count)
    else:
        plan.warn(f, "no block for %s - nothing copied" % t)


def names(plan):
    from .moddata import name_sections
    path = plan.mod.file("names")
    t, new = plan.template, plan.new
    if plan.opts.get("names"):                 # a name list of its own, typed in the window
        if any(new in o for _, o in name_sections(plan.edit(path).texts())):
            raise ValueError("faction '%s' already has names in descr_names.txt" % new)
        from .namelists import apply
        apply(plan, new, plan.opts["names"])
        return
    f = plan.edit(path)
    heads = name_sections(f.texts())
    owners = [o for _, o in heads]
    if any(new in o for o in owners):
        raise ValueError("faction '%s' already has names in descr_names.txt" % new)
    k = next((k for k, o in enumerate(owners) if t in o), None)
    if k is None:
        raise ValueError("template '%s' has no names in descr_names.txt" % t)
    s = heads[k][0]
    e = heads[k + 1][0] if k + 1 < len(heads) else len(f)
    copy = list(f.raw[s:e])
    copy[0] = f.make("faction: %s" % new)          # its own section, never the template's partners
    slave = next((i for i, o in heads if "slave" in o), None)
    f.insert_raw(slave if slave is not None else len(f), copy)
    plan.note(f, "name lists copied from %s (the same names, so every one already has a string)" % t)


# ---------------------------------------------------------------------------
# Lists of factions inside lines
# ---------------------------------------------------------------------------
def edu_ownership(plan):
    path = plan.mod.file("edu")
    t, new = plan.template, plan.new
    f = plan.edit(path)
    n = 0
    for i in range(len(f)):
        text = f.text(i)
        tk = tokens(text)
        if tk[:1] in (["ownership"], ["era"]) and t in tk[1:] and new not in tk:
            code = strip_comment(text)
            rest = text[len(code):]
            f.set(i, code.rstrip() + ", " + new + (" " + rest if rest else ""))
            n += 1
    plan.note(f, "%d unit(s) now also owned by %s" % (n, new))
    if n == 0:
        plan.warn(f, "no unit lists %s in ownership" % t)


RE_FACTIONS = re.compile(r"factions\s*\{([^}]*)\}")


def edb_factions(plan):
    path = plan.mod.file("edb")
    t, new = plan.template, plan.new
    f = plan.edit(path)
    n = 0
    for i in range(len(f)):
        text = f.text(i)
        if "factions" not in text or t not in text:
            continue
        def fix(m):
            inner = m.group(1)
            items = [x.strip() for x in inner.split(",")]
            if t not in items or new in items:
                return m.group(0)
            body = inner.rstrip()
            if body.endswith(","):
                return "factions {" + body + " " + new + ", }"
            return "factions {" + body + ", " + new + " }"
        out = RE_FACTIONS.sub(fix, text)
        if out != text:
            f.set(i, out)
            n += 1
    plan.note(f, "%d requirement(s) extended to %s" % (n, new))


def texture_lines(plan, key):
    """descr_model_battle / descr_model_strat: 'texture <faction>, path' lines."""
    path = plan.mod.file(key)
    if not path:
        return
    t, new = plan.template, plan.new
    f = plan.edit(path)
    n = 0
    i = 0
    while i < len(f):
        tk = tokens(f.text(i))
        if len(tk) >= 3 and tk[0] in ("texture", "model_flexi_m", "model_flexi") and tk[1] == t:
            f.insert_raw(i + 1, [_replace_word(f.raw[i], t, new)])
            n += 1
            i += 2
            continue
        i += 1
    if n:
        plan.note(f, "%d texture line(s) copied" % n)


def building_battle(plan):
    path = plan.mod.file("building_battle")
    if not path:
        return
    t, new = plan.template, plan.new
    f = plan.edit(path)
    n = 0
    i = 0
    while i < len(f):
        tk = tokens(f.text(i))
        if len(tk) >= 2 and tk[0] == t and "##" in f.text(i):
            f.insert_raw(i + 1, [_replace_word(f.raw[i], t, new)])
            n += 1
            i += 2
            continue
        i += 1
    if n:
        plan.note(f, "%d standard line(s) copied" % n)


def triggers(plan, key):
    """Copy every Trigger that tests 'FactionType <template>' (ethnic traits etc.)."""
    path = plan.mod.file(key)
    if not path:
        return
    t, new = plan.template, plan.new
    f = plan.edit(path)
    starts = [i for i in range(len(f)) if tokens(f.text(i))[:1] == ["Trigger"]]
    pat = re.compile(r"\bFactionType\s+%s\b" % re.escape(t))
    n = 0
    for k in reversed(range(len(starts))):
        s = starts[k]
        e = starts[k + 1] if k + 1 < len(starts) else len(f)
        while e > s + 1 and (f.text(e - 1).strip() == "" or f.text(e - 1).lstrip().startswith(";")):
            e -= 1
        if not any(pat.search(strip_comment(f.text(j))) for j in range(s, e)):
            continue
        copy = []
        for raw in f.raw[s:e]:
            text = raw.rstrip("\r")
            cr = "\r" if raw.endswith("\r") else ""
            if tokens(text)[:1] == ["Trigger"]:
                text = re.sub(r"(Trigger\s+)(\S+)", lambda m: m.group(1) + m.group(2) + "_" + new, text, 1)
            else:
                text = re.sub(r"(\bFactionType\s+)%s\b" % re.escape(t), r"\g<1>" + new, text)
            copy.append(text + cr)
        f.insert_raw(e, [f.make("")] + copy)
        n += 1
    if n:
        plan.note(f, "%d trigger(s) copied for %s" % (n, new))


def win_conditions(plan, campaign):
    path = plan.mod.campaign_file(campaign, "descr_win_conditions.txt")
    if not path:
        return
    t, new = plan.template, plan.new
    f = plan.edit(path)
    for i in range(len(f)):
        text = strip_comment(f.text(i))
        if text.strip() == t and not text[:1].isspace():
            j = i + 1
            while j < len(f) and f.text(j).strip() != "":
                j += 1
            copy = list(f.raw[i:j])
            copy[0] = _replace_word(copy[0], t, new)
            f.insert_raw(j, [f.make("")] + copy)
            plan.note(f, "win conditions copied from %s" % t)
            return
    plan.warn(f, "no win conditions for %s - add them by hand" % t)


# ---------------------------------------------------------------------------
# data/text string tables
# ---------------------------------------------------------------------------
RE_KEY = re.compile(r"^(\s*\{)([A-Za-z0-9_]+)(\}.*)$")


def entry_end(texts, i):
    """A string's value runs from its {KEY} line up to the next {KEY} or '¬'
    comment line: a long text spans several lines of the file. Trailing blank
    lines belong to the gap, not the value."""
    j = i + 1
    while j < len(texts) and not texts[j].lstrip().startswith(("{", "\u00ac")):
        j += 1
    while j > i + 1 and not texts[j - 1].strip():
        j -= 1
    return j


def entry_end_in(f, i):
    """entry_end for a TextFile, reading only the lines it needs (texts() copies the
    whole file: once per entry that made HLR's big tables take minutes)."""
    n = len(f.raw)
    j = i + 1
    while j < n and not f.text(j).lstrip().startswith(("{", "\u00ac")):
        j += 1
    while j > i + 1 and not f.text(j - 1).strip():
        j -= 1
    return j


def text_strings(plan):
    t, new = plan.template.upper(), plan.new.upper()
    tparts = t.split("_")
    repl = plan.display_replacements()
    long_keys = []
    for path in plan.mod.text_files():
        if "regions_and_settlement_names" in os.path.basename(path).lower():
            continue        # region and town labels ({Baktria} the region), not the faction's strings
        f = plan.edit(path)
        keys = set()
        for i in range(len(f)):
            m = RE_KEY.match(f.text(i))
            if m:
                keys.add(m.group(2).upper())
        n = 0
        i = 0
        while i < len(f):
            m = RE_KEY.match(f.text(i))
            if not m:
                i += 1
                continue
            key = m.group(2)
            end = entry_end_in(f, i)
            parts = key.upper().split("_")
            hit = None
            for p in range(len(parts) - len(tparts) + 1):
                if parts[p:p + len(tparts)] == tparts:
                    hit = p
                    break
            if hit is None:
                i = end
                continue
            nparts = key.split("_")
            was = "_".join(nparts[hit:hit + len(tparts)])
            part = new.lower() if was.islower() else new          # keep the key's own case
            new_key = "_".join(nparts[:hit] + [part] + nparts[hit + len(tparts):])
            if new_key.upper() in keys:
                i = end
                continue
            value = m.group(3)[1:]
            gap = value[:len(value) - len(value.lstrip())]
            more = [f.text(k) for k in range(i + 1, end)]           # the rest of a long text
            if key.upper() == t and plan.opts.get("display_name"):
                value, more = gap + plan.opts["display_name"], []
            elif key.upper() == t + "_DESCR" and plan.opts.get("description"):
                value, more = gap + plan.opts["description"].replace("\n", "\\n"), []
            elif key.upper().endswith("_" + t + "_DESCR") and plan.opts.get("long_description"):
                # the campaign screen's long text, e.g. {IMPERIAL_CAMPAIGN_<FACTION>_DESCR}
                value, more = gap + plan.opts["long_description"].replace("\n", "\\n"), []
                long_keys.append(new_key)
            else:
                for old, nw in repl:
                    value = value.replace(old, nw)
                    more = [l.replace(old, nw) for l in more]
            # the copy goes after the template's whole entry, never inside it
            f.insert(end, [m.group(1) + new_key + "}" + value] + more)
            keys.add(new_key.upper())
            n += 1
            i = end + 1 + len(more)
        if n:
            plan.note(f, "%d string(s) added" % n)
    if long_keys:
        plan.note(None, "full description written to %s" % ", ".join(sorted(set(long_keys))))


# ---------------------------------------------------------------------------
# Art files the game finds by faction name
# ---------------------------------------------------------------------------
ART_ROOTS = ("ui", "menu", "loading_screen")


def _token_hit(name, t):
    """Whether a file name names the faction t as a whole word: map_gauls, symbol24_gauls_roll,
    romans_julii_logo (names with _ inside match as a whole: symbol24_romans_julii_grey)."""
    stem = os.path.splitext(name)[0].lower()
    return t in re.split(r"[^a-z0-9]+", stem) or stem == t or stem.endswith("_" + t) or \
        stem.startswith(t + "_") or ("_" + t + "_") in stem


def art_files(plan, campaign):
    t, new = plan.template, plan.new
    found = []
    roots = [os.path.join(plan.mod.data, r) for r in ART_ROOTS] + [plan.mod.campaign_dir(campaign)]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for d in list(dirnames):
                if d.lower() == t:
                    src = os.path.join(dirpath, d)
                    dst = _ci(dirpath, new) or os.path.join(dirpath, new)
                    if not os.path.exists(dst):
                        found.append((src, dst))
                    else:
                        # a folder left from an earlier attempt: fill in what it lacks
                        for sp, _, fs in os.walk(src):
                            for n in fs:
                                sf = os.path.join(sp, n)
                                df = os.path.join(dst, os.path.relpath(sf, src))
                                if not os.path.exists(df):
                                    found.append((sf, df))
                    dirnames.remove(d)
            for n in filenames:
                if not n.lower().endswith((".tga", ".dds", ".png", ".bmp")) or not _token_hit(n, t):
                    continue
                stem, ext = os.path.splitext(n)
                parts = re.split(r"([^A-Za-z0-9]+)", stem)
                parts = [new if p.lower() == t else p for p in parts]
                dst = os.path.join(dirpath, "".join(parts) + ext)
                if dst != os.path.join(dirpath, n) and not os.path.exists(dst):
                    found.append((os.path.join(dirpath, n), dst))
    for src, dst in found:
        plan.copy(src, dst)
    if not found:
        plan.warn(None, "no art found under data/ui, data/menu, data/loading_screen or the campaign folder "
                        "named after %s (unit cards may be packed) - check them by hand" % t)


# ---------------------------------------------------------------------------
# Pictures a faction's lines name by path: banner textures, the loading-screen logo
# ---------------------------------------------------------------------------
# (file key, fields in a `faction X` block that name a picture under data)
PICTURE_LINKS = (("banners", ("standard_texture", "rebels_texture", "routing_texture", "ally_texture")),
                 ("sm_factions", ("loading_logo",)))


def picture_file(data, ref):
    """(path under data as it lies on disk, absolute path) of a picture a line names, or
    None. Rome writes models/textures/x.tga and keeps x.tga.dds."""
    from .moddata import _ci
    rel = ref.replace("\\", "/")
    rel = rel[5:] if rel.lower().startswith("data/") else rel
    for cand in (rel, rel + ".dds"):
        folder, name = os.path.split(os.path.join(data, *cand.split("/")))
        p = _ci(folder, name) if os.path.isdir(folder) else None
        if p:
            return os.path.relpath(p, data).replace("\\", "/"), p
    return None


def picture_links(mod, load=None):
    """[{'faction', 'key', 'path', 'line', 'field', 'ref'}] of every picture path in the
    factions' blocks of descr_banners / descr_sm_factions; load = plan.edit to see the
    files as a plan leaves them (default: as on disk)."""
    out = []
    for key, fields in PICTURE_LINKS:
        path = mod.file(key)
        if not path:
            continue
        f = (load or mod.load)(path)
        cur = None
        for i in range(len(f)):
            t = tokens(f.text(i))
            if len(t) == 2 and t[0] == "faction":
                cur = t[1]
            elif cur and len(t) >= 2 and t[0] in fields:
                out.append({"faction": cur, "key": key, "path": path, "line": i, "field": t[0], "ref": t[1]})
    return out


def link_users(links, but=None):
    """{ref lower: set of factions naming it} - who shares a picture."""
    users = {}
    for l in links:
        if l["faction"] != but:
            users.setdefault(l["ref"].replace("\\", "/").lower(), set()).add(l["faction"])
    return users


def own_picture_ref(ref, owner, new):
    """The name a picture gets as `new`'s own: the owner's name in it swapped for the new one
    (standard_julii -> standard_saba for romans_julii, standard_macedonia_ally -> standard_saba_ally
    for macedon: a word of the owner's name, or a word that starts like it), else _<new> added
    (standard_greek_rebels -> standard_greek_rebels_saba). The folder and extension stay."""
    ref = ref.replace("\\", "/")
    folder, name = (ref.rsplit("/", 1) if "/" in ref else ("", ref))
    stem, dot, ext = name.partition(".")
    whole = re.sub(r"(?i)(^|[^a-z0-9])%s(?=$|[^a-z0-9])" % re.escape(owner), lambda m: m.group(1) + new,
                   stem, count=1) if owner else stem
    if whole == stem and owner:
        words = [w for w in owner.lower().split("_") if len(w) >= 4]
        parts = re.split(r"([^A-Za-z0-9]+)", stem)
        for k, p in enumerate(parts):
            low = p.lower()
            if len(low) >= 4 and any(low == w or low.startswith(w) or w.startswith(low) for w in words):
                parts[k] = new
                whole = "".join(parts)
                break
    if whole == stem:
        whole = "%s_%s" % (stem, new)
    return (folder + "/" if folder else "") + whole + dot + ext


def disk_tail(ref, disk):
    """What the file on disk adds to the name a line writes: '.dds' for x.tga kept as x.tga.dds."""
    a, b = ref.replace("\\", "/").split("/")[-1], os.path.basename(disk)
    return b[len(a):] if b.lower().startswith(a.lower()) else ""


def set_picture_ref(f, line, old, new):
    """Point line `line` of f at another picture (only the path changes)."""
    f.set(line, f.text(line).replace(old, new, 1))


def own_pictures(plan):
    """The new faction's banner textures and loading-screen logo become files of its own: a
    picture only the template names is copied under the new name (standard_macedonia ->
    standard_saba) and the new block points at the copy - else a picture replaced for the new
    faction would change the template's too. Pictures several factions share (rebels,
    routing) stay shared; the Art tab's Replace makes the faction a copy of its own then."""
    t, new, mod = plan.template, plan.new, plan.mod
    links = picture_links(mod, plan.edit)
    users = link_users(links, but=new)
    planned = {os.path.normcase(os.path.abspath(d)) for _, d in plan.copies}
    count = 0
    for l in links:
        if l["faction"] != new or users.get(l["ref"].replace("\\", "/").lower()) != {t}:
            continue
        got = picture_file(mod.data, l["ref"])
        if not got:
            continue
        ref = own_picture_ref(l["ref"], t, new)
        dst = os.path.join(os.path.dirname(got[1]), ref.split("/")[-1] + disk_tail(l["ref"], got[1]))
        if os.path.normcase(os.path.abspath(dst)) not in planned and not os.path.exists(dst):
            plan.copy(got[1], dst)
        set_picture_ref(plan.edit(l["path"]), l["line"], l["ref"], ref)
        count += 1
    if count:
        plan.note(None, "%d picture(s) of %s's banners / loading logo copied as %s's own" % (count, t, new))


# ---------------------------------------------------------------------------
# Unit cards: followed from export_descr_unit, not guessed from folder names
# ---------------------------------------------------------------------------
CARD_KINDS = (("units", "#%s.tga", "unit card"), ("unit_info", "%s_info.tga", "unit info picture"))


def unit_cards(plan):
    """Every unit the new faction owns needs ui/units/<faction>/#<dictionary>.tga
    and ui/unit_info/<faction>/<dictionary>_info.tga, or the game shows a
    placeholder. Copy each missing one from the template's folder (or, failing
    that, from any other faction's folder that has it)."""
    t, new = plan.template, plan.new
    edu = plan.files.get(plan.mod.file("edu"))
    if edu is None:
        return
    dicts = []
    cur = None
    for l in edu.texts():
        tk = tokens(l)
        if tk[:1] == ["dictionary"] and len(tk) > 1:
            cur = tk[1]
        elif tk[:1] == ["ownership"] and cur and new in tk[1:]:
            dicts.append(cur)
            cur = None
    planned = {os.path.normcase(d) for _, d in plan.copies}
    missing = []
    for folder, pattern, label in CARD_KINDS:
        root = os.path.join(plan.mod.data, "ui", folder)
        if not os.path.isdir(root):
            continue
        others = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))
                        and d.lower() not in (t, new))
        dst_dir = _ci(root, new) or os.path.join(root, new)
        for d in dicts:
            name = pattern % d
            dst = _ci(dst_dir, name) or os.path.join(dst_dir, name)
            nd = os.path.normcase(dst)
            if os.path.exists(dst) or any(nd == p or nd.startswith(p + os.sep) for p in planned):
                continue
            src = _ci(os.path.join(root, t), name) if _ci(root, t) else None
            if not src:
                src = next((p for p in (_ci(os.path.join(root, o), name) for o in others) if p), None)
            if src:
                plan.copy(src, dst)
                planned.add(os.path.normcase(dst))
            else:
                missing.append("%s/%s" % (folder, name))
    if missing:
        plan.warn(None, "no picture found anywhere under data/ui for %d unit file(s) - the game shows a "
                        "placeholder: %s" % (len(missing), ", ".join(missing[:12]) + (" ..." if len(missing) > 12 else "")))


def lookup_keys(plan):
    """lookup_campaign_descriptions.txt (vanilla RTW): one campaign-description
    key per line. The new faction's keys go right after the template's."""
    path = plan.mod.file("lookup_descr")
    if not path:
        return
    t, new = plan.template.upper(), plan.new.upper()
    f = plan.edit(path)
    have = {tokens(l)[0].upper() for l in f.texts() if tokens(l)}
    word = re.compile(r"(?<![A-Z0-9])%s(?![A-Z0-9])" % re.escape(t))
    n, i = 0, 0
    while i < len(f):
        tk = tokens(f.text(i))
        if len(tk) == 1 and word.search(tk[0].upper()):
            key = word.sub(new, tk[0].upper())
            if key not in have:
                f.insert_raw(i + 1, [f.raw[i].replace(tk[0], key, 1)])
                have.add(key)
                n += 1
                i += 1
        i += 1
    # the chosen campaign's keys, when the template's are under a front end name
    camp = getattr(plan, "campaign", None)
    if camp:
        src = description_key(plan.template, camp, have)
        for suffix in ("_TITLE", "_DESCR"):
            key = "%s_%s%s" % (camp.upper(), new, suffix)
            if key in have:
                continue
            at = next((i + 1 for i in range(len(f)) if tokens(f.text(i))[:1] == [src + suffix]), len(f))
            f.insert(at, [key])
            have.add(key)
            n += 1
    if n:
        plan.note(f, "%d campaign description key(s) listed for %s" % (n, plan.new))


# The front end names some vanilla factions its own way in the campaign
# description keys ({IMPERIAL_CAMPAIGN_GAUL_DESCR} for gauls).
FE_NAMES = {"romans_julii": "JULII", "romans_brutii": "BRUTII", "romans_scipii": "SCIPII",
            "romans_senate": "SENATE", "gauls": "GAUL", "britons": "BRITANNIA", "germans": "GERMANIA"}


def description_key(faction, campaign, keys=()):
    """The campaign-screen key the game reads for a faction: <CAMPAIGN>_<NAME>,
    with the front end's own name for the vanilla factions that have one."""
    camp = campaign.upper()
    own = "%s_%s" % (camp, faction.upper())
    fe = FE_NAMES.get(faction)
    if fe and own + "_DESCR" not in keys and "%s_%s_DESCR" % (camp, fe) in keys:
        return "%s_%s" % (camp, fe)
    return own


def campaign_description(plan, campaign):
    """Make sure campaign_descriptions.txt has the new faction's title and full
    description for this campaign, even when the template's are under a front
    end name that text_strings() could not match."""
    path = next((p for p in plan.mod.text_files()
                 if os.path.basename(p).lower() == "campaign_descriptions.txt"), None)
    if not path:
        return
    f = plan.edit(path)
    keys = {}
    for i, l in enumerate(f.texts()):
        m = RE_KEY.match(l)
        if m:
            keys[m.group(2).upper()] = i
    new_key = "%s_%s" % (campaign.upper(), plan.new.upper())
    src = description_key(plan.template, campaign, keys)
    added = []
    for suffix in ("_TITLE", "_DESCR"):
        if new_key + suffix in keys:
            continue
        if suffix == "_TITLE":
            value = plan.opts.get("display_name") or ""
        else:
            value = (plan.opts.get("long_description") or "").replace("\n", "\\n")
        more = []
        if not value and src + suffix in keys:
            k = keys[src + suffix]
            value = RE_KEY.match(f.text(k)).group(3)[1:].strip()
            more = [f.text(x) for x in range(k + 1, entry_end(f.texts(), k))]
        if not value:
            continue
        at = entry_end(f.texts(), keys[src + suffix]) if src + suffix in keys else len(f)
        lines = ["{%s%s}\t%s" % (new_key, suffix, value)] + more
        f.insert(at, lines)
        keys = {k: (v + len(lines) if v >= at else v) for k, v in keys.items()}
        keys[new_key + suffix] = at
        added.append(new_key + suffix)
    if added:
        plan.note(f, "campaign screen strings for %s: %s" % (campaign, ", ".join(added)))
