"""A faction's people in descr_strat.txt and its family tree.

- on the map: `character Name, kind, [male|female,] [leader|heir,] age N, ..., x X, y Y`, then
  optional `traits T 2 , U 1` and `ancillaries a, b` lines, then its army;
- off the map (family members only): `character_record Name, male|female, [command 0, ...,] age N,
  alive, never_a_leader` (Rome writes the four skills, Medieval II does not);
- the tree: `relative Father, Wife, Child, Child, end` - one line per couple, after the records.
  Every name on a relative line is a character or a record of the same faction.

Rome and Medieval II write these the same way apart from the sex on character lines
(strat.medieval) and the skills on record lines, which are copied from the file's own lines."""

import re

from .strat import Strat, medieval
from .textio import strip_comment, tokens

RE_AGE = re.compile(r"\bage\s+(\d+)")
# A living man off the map is a boy: older ones belong on the map, and the game crashes on a living male
# character_record over the age of manhood (heavengames "The Descr_Strat Reference"; vanilla keeps to it - RTW 0
# of 74, M2TW 0 of 21 living male records are older). The age is the mod's setting (limits.manhood_age: REX
# descr_ex.txt / M2TW descr_campaign_db.xml), 16 by default.
MAX_RECORD_AGE = 16


class Person:
    def __init__(self, **kw):
        self.key = self.name = self.source = self.kind = self.sex = self.role = None
        self.age, self.status, self.line, self.xy = None, "", None, None
        self.traits, self.ancillaries = [], []
        self.portrait = None                    # Medieval II: the folder under ui/custom_portraits
        self.__dict__.update(kw)

    @property
    def on_map(self):
        return self.source == "map"

    @property
    def family(self):
        """A member of the family: a named character (or a princess), or a record."""
        return self.source == "record" or self.kind in ("named character", "princess")

    def as_dict(self):
        return {k: getattr(self, k) for k in ("key", "name", "source", "kind", "sex", "role", "age", "status",
                                               "xy", "traits", "ancillaries", "portrait")}


def _parts(line, head):
    body = strip_comment(line).strip()[len(head):]
    return [p.strip() for p in body.split(",")]


def parse_traits(line):
    """'traits GoodCommander 2 , Austere 1' -> [['GoodCommander', 2], ['Austere', 1]]."""
    out = []
    for p in _parts(line, "traits"):
        t = p.split()
        if len(t) >= 2 and t[-1].lstrip("-").isdigit():
            out.append([" ".join(t[:-1]), int(t[-1])])
        elif t:
            out.append([" ".join(t), 1])
    return out


def parse_ancillaries(line):
    return [p for p in _parts(line, "ancillaries") if p]


def traits_line(traits):
    return "traits " + " , ".join("%s %d" % (t, int(n)) for t, n in traits) + " "


def ancillaries_line(ancs):
    return "ancillaries " + ", ".join(ancs)


def _head_lines(texts, c):
    """{'traits': i, 'ancillaries': i} inside a character chunk (before its army)."""
    out = {}
    for i in range(c.start + 1, c.end):
        h = tokens(texts[i])[:1]
        if h in (["army"], ["unit"], ["character"]):
            break
        if h in (["traits"], ["ancillaries"]):
            out[h[0]] = i
    return out


def _parse_relative(line):
    parts = [p for p in _parts(line, "relative") if p]
    if parts and parts[-1] == "end":
        parts = parts[:-1]
    if not parts:
        return None
    return [parts[0], parts[1] if len(parts) > 1 else "", parts[2:]]


def read(f, faction):
    """{'people': [Person], 'tree': [[father, wife, [children]]], 'relative_lines': [i],
    'record_lines': [i], 'medieval': bool} for the faction's block of a loaded descr_strat."""
    s = Strat(f)
    fb = s.faction(faction)
    if fb is None:
        raise ValueError("%s has no faction block in descr_strat.txt" % faction)
    texts = s.lines
    m2 = medieval(texts)
    people, seen = [], {}

    def key(source, name):
        n = seen.get((source, name), 0)
        seen[(source, name)] = n + 1
        return "%s:%s#%d" % (source, name, n)

    for c in fb.characters:
        parts = _parts(texts[c.start], "character")
        sex = "female" if "female" in parts else ("male" if "male" in parts else
                                                  ("female" if c.kind in ("princess", "witch") else "male"))
        m = RE_AGE.search(texts[c.start])
        head = _head_lines(texts, c)
        portrait = next((x.split(None, 1)[1].strip() for x in parts if x.startswith("portrait ")), None)
        p = Person(key=key("map", c.name), name=c.name, source="map", kind=c.kind, sex=sex, role=c.role,
                   portrait=portrait,
                   age=int(m.group(1)) if m else None, line=c.start, xy=c.xy, chunk=(c.start, c.end),
                   traits=parse_traits(texts[head["traits"]]) if "traits" in head else [],
                   ancillaries=parse_ancillaries(texts[head["ancillaries"]]) if "ancillaries" in head else [])
        people.append(p)
    tree, rel_lines, rec_lines = [], [], []
    for i in range(fb.start, fb.end):
        h = tokens(texts[i])[:1]
        if h == ["character_record"]:
            parts = _parts(texts[i], "character_record")
            m = RE_AGE.search(texts[i])
            status = [p for p in parts[1:] if p and not p.startswith(("age", "command", "influence", "management",
                                                                        "subterfuge")) and p not in ("male", "female")]
            people.append(Person(key=key("record", parts[0]), name=parts[0], source="record", kind="record",
                                 sex="female" if "female" in parts else "male", age=int(m.group(1)) if m else None,
                                 status=", ".join(status), line=i))
            rec_lines.append(i)
        elif h == ["relative"]:
            r = _parse_relative(texts[i])
            if r:
                tree.append(r)
                rel_lines.append(i)
    return {"people": people, "tree": tree, "relative_lines": rel_lines, "record_lines": rec_lines,
            "medieval": m2, "block": (fb.start, fb.end)}


# ---------------------------------------------------------------- what the mod has
def trait_list(mod):
    """{trait: {'characters': [kinds], 'levels': [level names], 'anti': [traits], 'effects': [[(attribute, value)]
    per level]}} from export_descr_character_traits.txt."""
    path = mod.file("traits")
    out, cur = {}, None
    if not path:
        return out
    for l in mod.load(path).texts():
        t = tokens(l)
        if not t:
            continue
        if t[0] == "Trait" and len(t) > 1:
            cur = out.setdefault(t[1], {"characters": [], "levels": [], "anti": [], "effects": []})
        elif t[0] in ("Trigger", "Ancillary"):
            cur = None
        elif cur is not None and t[0] == "Characters":
            cur["characters"] = [x.strip() for x in strip_comment(l).strip()[len("Characters"):].split(",") if x.strip()]
        elif cur is not None and t[0] == "AntiTraits":
            cur["anti"] = [x.strip() for x in strip_comment(l).strip()[len("AntiTraits"):].split(",") if x.strip()]
        elif cur is not None and t[0] == "Level" and len(t) > 1:
            cur["levels"].append(t[1])
            cur["effects"].append([])
        elif cur is not None and t[0] == "Effect" and len(t) > 2 and cur["effects"]:
            try:
                cur["effects"][-1].append((t[1], int(t[2])))
            except ValueError:
                pass
    return out


def ancillary_list(mod):
    """{ancillary: {'exclude': [cultures], 'image': picture name, 'effects': [(attribute, value)]}} from
    export_descr_ancillaries.txt."""
    path = mod.file("ancillaries")
    out, cur = {}, None
    if not path:
        return out
    for l in mod.load(path).texts():
        t = tokens(l)
        if not t:
            continue
        if t[0] == "Ancillary" and len(t) > 1:
            cur = out.setdefault(t[1], {"exclude": [], "image": None, "effects": []})
        elif t[0] == "Trigger":
            cur = None
        elif cur is not None and t[0] == "Image" and len(t) > 1:
            cur["image"] = t[1]
        elif cur is not None and t[0] == "Effect" and len(t) > 2:
            try:
                cur["effects"].append((t[1], int(t[2])))
            except ValueError:
                pass
        elif cur is not None and t[0] == "ExcludeCultures":
            cur["exclude"] = [x.strip() for x in strip_comment(l).strip()[len("ExcludeCultures"):].split(",")
                              if x.strip()]
    return out


def trait_kind(kind):
    """The 'Characters' word a trait names for a character of this kind."""
    return "family" if kind in ("named character", "general", "record") else kind


# ---------------------------------------------------------------- checks
def tree_problems(tree, people):
    """Why a family tree cannot be written ([] when it can): names that are nobody of the
    faction, a child with two sets of parents, a person their own ancestor, a father who is
    a woman or a wife who is a man."""
    by = {p["name"]: p for p in people}
    out, parent_of = [], {}
    for father, wife, kids in tree:
        for n in [father, wife] + list(kids):
            if n and n not in by:
                out.append("%s is on the family tree but is no character of the faction" % n)
        if father in by and by[father]["sex"] == "female":
            out.append("%s heads a couple but is a woman" % father)
        if wife and wife in by and by[wife]["sex"] == "male":
            out.append("%s is %s's wife but is a man" % (wife, father))
        for k in kids:
            if k in parent_of:
                out.append("%s has two sets of parents (%s and %s)" % (k, parent_of[k], father))
            parent_of[k] = father
    kids_of = {}
    for father, wife, kids in tree:
        for p in (father, wife):
            if p:
                kids_of.setdefault(p, set()).update(kids)
    for start in kids_of:
        stack, seen = list(kids_of[start]), set()
        while stack:
            n = stack.pop()
            if n == start:
                out.append("%s is their own ancestor" % start)
                break
            if n not in seen:
                seen.add(n)
                stack.extend(kids_of.get(n, ()))
    return sorted(set(out))


def age_warnings(tree, people):
    by = {p["name"]: p for p in people}
    out = []
    for father, wife, kids in tree:
        for parent in (father, wife):
            pa = (by.get(parent) or {}).get("age")
            for k in kids:
                ka = (by.get(k) or {}).get("age")
                if pa is not None and ka is not None and pa - ka < 14:
                    out.append("%s (%d) is only %d years older than the child %s (%d)" % (parent, pa, pa - ka, k, ka))
    return out


def ordered(tree):
    """The couples with every parent's couple before their children's couples (the order
    vanilla writes them); otherwise the order given."""
    out, left = [], list(tree)
    while left:
        kids = {k for _, _, ks in left for k in ks}
        nxt = next((c for c in left if c[0] not in kids and c[1] not in kids), left[0])
        out.append(nxt)
        left.remove(nxt)
    return out


def relative_line(father, wife, kids):
    return "relative \t%s, \t%s,\t\t%s" % (father, wife, "".join("%s,\t" % k for k in kids) + "end")


def record_line(texts, name, sex, age, m2, dead=False):
    """A character_record line in the file's own form (another record as the pattern); dead: the person died
    before the start (a parent on the tree): 'dead' where a living one has 'alive' - both games (Rome: HLR's
    records; Medieval II: the game's own world/template.txt and battle.txt, 'age 94, dead, past_leader')."""
    status = "dead" if dead else "alive"
    for l in texts:
        if tokens(l)[:1] == ["character_record"]:
            parts = _parts(l, "character_record")
            head = re.match(r"\s*character_record\s*", l).group(0)
            rest = []
            for p in parts[1:]:
                if p in ("male", "female"):
                    p = sex
                elif p.startswith("age"):
                    p = "age %d" % int(age)
                elif p.split()[:1] in (["alive"], ["dead"]):
                    p = status
                rest.append(p)
            return "%s%s, \t%s" % (head, name, ", ".join(rest))
    skills = "" if m2 else "command 0, influence 0, management 0, subterfuge 0, "
    return "character_record\t\t%s, \t%s, %sage %d, %s, never_a_leader" % (name, sex, skills, int(age), status)


def check_name(pool, name, sex, faction):
    """None, or why the game would crash on this name (every name needs its string)."""
    if not pool:
        return None
    first = name.split(" ")[0]
    firsts = pool.get("women" if sex == "female" else "characters", [])
    if first not in firsts:
        return "'%s' is not in %s's %s name list - the game crashes on a name it has no string for" % (
            first, faction, "women's" if sex == "female" else "men's")
    rest = name[len(first):].strip()
    if rest and rest not in pool.get("surnames", []):
        return "surname '%s' is not in %s's surname list" % (rest, faction)
    return None


# ---------------------------------------------------------------- writing
def rename_in_tree(f, faction, old, new):
    """Every relative line of the faction naming 'old' names 'new' instead."""
    fam = read(f, faction)
    for i in fam["relative_lines"]:
        r = _parse_relative(f.text(i))
        if r and old in [r[0], r[1]] + r[2]:
            names = [new if n == old else n for n in [r[0], r[1]] + r[2]]
            f.set(i, relative_line(names[0], names[1], names[2:]))


def record_age_problems(after, before=None, most=MAX_RECORD_AGE):
    """Living men off the map (records) older than `most` (the mod's age of manhood): [(name, age, new)] - new
    is False for one the file already had at that age (the edit did not make it so)."""
    old = {d.get("key"): d.get("age") for d in before or [] if d.get("key")}
    out = []
    for d in after:
        if d.get("source") != "record" or d.get("sex") != "male" or d.get("age") in (None, ""):
            continue
        if "dead" in (d.get("status") or "") or int(d["age"]) <= most:
            continue
        was = old.get(d.get("key"))
        out.append((d["name"], int(d["age"]), was in (None, "") or int(was) != int(d["age"])))
    return out


def default_record_age(sex, most=MAX_RECORD_AGE):
    return most if sex == "male" else 20


def limit_warnings(mod, tree, changes, people, renames=None, old_tree=None):
    """Ancillaries and children over what the game takes (limits.ex_setting: REX's descr_ex.txt
    max_num_ancillaries / max_num_children, else the original game's 8 / 4)."""
    from .limits import ex_setting
    out = []
    most = ex_setting(mod, "max_num_ancillaries")
    for key, ch in (changes or {}).items():
        ancs = ch.get("ancillaries")
        if most and ancs is not None and len(ancs) > most:
            p = people.get(key)
            out.append("%s: %d ancillaries - the game keeps at most %d (max_num_ancillaries in descr_ex.txt)"
                       % ((renames or {}).get(p.name, p.name) if p else key, len(ancs), most))
    most = ex_setting(mod, "max_num_children")

    def kids_of(t):
        kids = {}
        for father, wife, ks in t or []:
            for parent in (father, wife):
                if parent:
                    kids.setdefault(parent, set()).update(ks)
        return kids
    before = kids_of(old_tree)
    for parent, ks in sorted(kids_of(tree).items()):
        if most and len(ks) > most and len(ks) > len(before.get(parent, ())):   # only what this edit adds
            out.append("%s: %d children - the game takes at most %d (max_num_children in descr_ex.txt)"
                       % (parent, len(ks), most))
    return out


def apply(plan, f, faction, opts):
    """opts = {'people': {key: {'name', 'age', 'sex', 'traits', 'ancillaries'}},
               'new': [{'name', 'sex', 'age'}], 'remove': [key], 'tree': [[father, wife, [kids]]] | None}
    Only what is given changes; a renamed person is renamed on the tree too."""
    fam = read(f, faction)
    m2 = fam["medieval"]
    people = {p.key: p for p in fam["people"]}
    changes = opts.get("people") or {}
    remove = set(opts.get("remove") or [])
    pool = plan.name_pool(faction) or {}
    known_traits = trait_list(plan.mod)
    known_ancs = ancillary_list(plan.mod)
    renames = {}
    for key, ch in changes.items():
        p = people.get(key)
        if p is None:
            raise ValueError("%s: no such character of %s any more" % (key.split(":", 1)[-1], faction))
        name = (ch.get("name") or p.name).strip()
        if name != p.name:
            why = check_name(pool, name, ch.get("sex") or p.sex, faction)
            if why:
                raise ValueError("%s: %s" % (p.name, why))
            renames[p.name] = name
        for t, n in ch.get("traits") or []:
            info = known_traits.get(t)
            if known_traits and info is None:
                raise ValueError("%s: trait %s is not in export_descr_character_traits.txt" % (p.name, t))
            if info and info["levels"] and not 1 <= int(n) <= len(info["levels"]):
                raise ValueError("%s: %s has levels 1-%d, not %s" % (p.name, t, len(info["levels"]), n))
        for a in ch.get("ancillaries") or []:
            if known_ancs and a not in known_ancs:
                raise ValueError("%s: ancillary %s is not in export_descr_ancillaries.txt" % (p.name, a))
        if not p.on_map and (ch.get("traits") or ch.get("ancillaries")):
            raise ValueError("%s is off the map (a record): the game keeps no traits or ancillaries for records"
                             % p.name)
    for key in remove:
        p = people.get(key)
        if p is None:
            continue
        if p.on_map:
            raise ValueError("%s is on the map - remove characters on the map in Units & armies" % p.name)
    for n in opts.get("new") or []:
        why = check_name(pool, n["name"], n.get("sex", "male"), faction)
        if why:
            raise ValueError("new %s: %s" % (n["name"], why))

    # the people as they will be, for the tree checks
    after = []
    for p in fam["people"]:
        if p.key in remove:
            continue
        d = p.as_dict()
        d.update({k: v for k, v in (changes.get(p.key) or {}).items() if k in ("name", "age", "sex") and v})
        after.append(d)
    after += [{"name": n["name"], "sex": n.get("sex", "male"), "age": n.get("age"), "source": "record",
               "status": "dead" if n.get("dead") else "alive"}
              for n in opts.get("new") or []]
    names = [d["name"] for d in after]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        plan.warn(f, "%s: more than one person named %s - the family tree cannot tell them apart"
                  % (faction, ", ".join(dup)))
    gone = {people[k].name for k in remove if k in people}
    tree = opts.get("tree")
    if tree is None:
        tree = [[renames.get(a, a), renames.get(b, b), [renames.get(k, k) for k in ks if k not in gone]]
                for a, b, ks in fam["tree"]]
        for a, b, _ in tree:
            if a in gone or b in gone:
                raise ValueError("%s heads a couple on the family tree - take them off the tree first"
                                 % (a if a in gone else b))
    tree = [[a, b, list(ks)] for a, b, ks in tree]
    from .limits import manhood_age
    most = manhood_age(plan.mod)
    for name, age, new in record_age_problems(after, [p.as_dict() for p in fam["people"]], most):
        msg = ("%s (%d) is a living man off the map (a record) - the game crashes on one older than %d (the mod's "
               "age of manhood): make him %d or younger, or put him on the map" % (name, age, most, most))
        if new:
            raise ValueError(msg)
        plan.warn(f, msg + " (already so in the file)")
    bad = tree_problems(tree, after)
    if bad:
        raise ValueError("family tree of %s: %s" % (faction, "; ".join(bad)))
    for w in age_warnings(tree, after):
        plan.warn(f, w)
    tied = {x for a, b, ks in tree for x in [a, b] + list(ks)}
    for n in opts.get("new") or []:
        if n["name"] not in tied:
            plan.warn(f, "%s: %s is new and on no family tree - written as a record no one is related to; tie them "
                         "on (Add a person... > son, daughter or wife of someone, then pick them) or leave them out" % (faction, n["name"]))
    for w in limit_warnings(plan.mod, tree, changes, people, renames, fam["tree"]):
        plan.warn(f, w)

    # the lines, from the bottom up so earlier indices stay right
    texts = f.texts()
    jobs = []                               # (line, kind, payload)
    for key, ch in changes.items():
        p = people[key]
        if key in remove:
            continue
        jobs.append((p.line, "person", (p, ch)))
    for key in remove:
        if key in people:
            jobs.append((people[key].line, "remove", people[key]))
    for line, what, x in sorted(jobs, key=lambda j: -j[0]):
        if what == "remove":
            del f.raw[line]
            plan.note(f, "%s: %s left out (off-map family member)" % (faction, x.name))
            continue
        p, ch = x
        _person(plan, f, texts, p, ch, faction)

    # own portraits (Medieval II): on the lines as they are now
    if opts.get("portraits"):
        now = {p.key: p for p in read(f, faction)["people"]}
        for key, pics in opts["portraits"].items():
            p = now.get(key)
            if p is None and key in people and key in changes and changes[key].get("name"):
                p = next((x for x in now.values() if x.name == changes[key]["name"] and x.source == "map"), None)
            if p is None:
                raise ValueError("%s: no such character of %s any more" % (key.split(":", 1)[-1], faction))
            set_portraits(plan, f, faction, p, pics, m2)

    # new records and the tree: after the characters, where the records / relatives stand
    fam2 = read(f, faction)
    recs, rels = fam2["record_lines"], fam2["relative_lines"]
    def age_of(n):
        return n.get("age") or default_record_age(n.get("sex", "male"), manhood_age(plan.mod))
    new_lines = [record_line(f.texts(), n["name"], n.get("sex", "male"), age_of(n), m2, n.get("dead"))
                 for n in opts.get("new") or []]
    for n in opts.get("new") or []:
        plan.note(f, "%s: %s (%s, age %s%s) added off the map" % (
            faction, n["name"], n.get("sex", "male"), age_of(n), ", died before the start" if n.get("dead") else ""))
    old_tree = [_parse_relative(f.text(i)) for i in rels]
    want = ordered(tree)
    if want == old_tree and not new_lines:
        return
    keep_raw = {}
    for i in rels:
        r = _parse_relative(f.text(i))
        keep_raw[repr(r)] = f.raw[i]
    first_rel = rels[0] if rels else None
    for i in sorted(rels, reverse=True):
        del f.raw[i]
    if rels:
        at = first_rel - sum(1 for i in rels if i < first_rel)
    else:
        at = None
    if recs:
        rec_at = recs[-1] + 1
    elif at is not None:
        rec_at = at
    else:
        rec_at = read(f, faction)["block"][1]
    f.raw[rec_at:rec_at] = [f.make(l) for l in new_lines]
    if at is None:
        at = rec_at + len(new_lines)
        if want:
            f.raw[at:at] = [f.make("")]
            at += 1
    elif at >= rec_at:
        at += len(new_lines)
    f.raw[at:at] = [keep_raw.get(repr(c)) or f.make(relative_line(*c)) for c in want]
    if want != old_tree:
        plan.note(f, "%s: family tree - %d couple(s)" % (faction, len(want)))


def _person(plan, f, texts, p, ch, faction):
    name = (ch.get("name") or p.name).strip()
    age = ch.get("age") if ch.get("age") not in (None, "") else p.age
    said = []
    if p.on_map:
        start, end = p.chunk
        line = f.text(start)
        if name != p.name:
            line = line.replace(p.name, name, 1)
            said.append("renamed %s" % name)
        if age is not None and age != p.age:
            line = RE_AGE.sub("age %d" % int(age), line, 1)
            said.append("age %d" % int(age))
        from .strat import Character
        head = _head_lines(texts, Character(start, end, texts[start], faction))
        stop = max([start] + list(head.values())) + 1
        new = [f.make(line) if line != f.text(start) else f.raw[start]]
        traits = ch.get("traits") if ch.get("traits") is not None else p.traits
        ancs = ch.get("ancillaries") if ch.get("ancillaries") is not None else p.ancillaries
        if traits:
            same = "traits" in head and [list(x) for x in traits] == p.traits
            new.append(f.raw[head["traits"]] if same else f.make(traits_line(traits)))
        if ancs:
            same = "ancillaries" in head and list(ancs) == p.ancillaries
            new.append(f.raw[head["ancillaries"]] if same else f.make(ancillaries_line(ancs)))
        # lines between the character line and its traits/ancillaries (blank or comments) stay
        others = [f.raw[i] for i in range(start + 1, stop) if i not in head.values()]
        if [list(x) for x in traits] != p.traits:
            said.append("traits: %s" % (", ".join("%s %d" % (t, n) for t, n in traits) or "none"))
        if list(ancs) != p.ancillaries:
            said.append("ancillaries: %s" % (", ".join(ancs) or "none"))
        f.raw[start:stop] = new + others
    else:
        line = f.text(p.line)
        if name != p.name:
            line = re.sub(r"(character_record\s*)" + re.escape(p.name), lambda m: m.group(1) + name, line, 1)
            said.append("renamed %s" % name)
        if age is not None and age != p.age:
            line = RE_AGE.sub("age %d" % int(age), line, 1)
            said.append("age %d" % int(age))
        sex = ch.get("sex")
        if sex and sex != p.sex:
            line = re.sub(r"\b%s\b" % p.sex, sex, line, 1)
            said.append(sex)
        if line != f.text(p.line):
            f.set(p.line, line)
    if said:
        plan.note(f, "%s: %s - %s" % (faction, p.name, "; ".join(said)))


# ---------------------------------------------------------------- portraits
# Medieval II: `, portrait <folder>` at the end of a character line takes the pictures from
# data/ui/custom_portraits/<folder>/portrait_young.tga, portrait_old.tga, portrait_dead.tga
# (the game's own strings; vanilla uses it in norman_prologue). Without it - and always in
# Rome - the game gives each character one of its culture's pool at random:
# ui/<portrait_mapping>/portraits/portraits/young|old|dead/<generals|civilians|rogues>/NNN.tga,
# family members off the map ui/<portrait_mapping>/portraits/family/<wife|son|daughter>.tga.
AGES = ("young", "old", "dead")


def data_roots(mod):
    """The mod's data, then the game's own data (a mod falls back to it)."""
    import os
    from .newmod import game_of
    out = [mod.data]
    try:
        game = os.path.join(game_of(mod.data), "data")
    except Exception:
        game = None
    if game and os.path.isdir(game) and os.path.abspath(game) != os.path.abspath(mod.data):
        out.append(game)
    return out


def _find(mod, *parts):
    import os
    from .moddata import _ci
    for root in data_roots(mod):
        cur = root
        for p in parts:
            cur = _ci(cur, p) if cur else None
        if cur and os.path.exists(cur):
            return cur
    return None


def portrait_culture(mod, faction):
    """The portrait_mapping of the faction's culture (descr_cultures.txt)."""
    culture = dict(mod.factions()).get(faction)
    path = _find(mod, "descr_cultures.txt")
    if not path or not culture:
        return culture
    cur = None
    for l in mod.load(path).texts():
        t = tokens(l)
        if t[:1] == ["culture"] and len(t) > 1:
            cur = t[1]
        elif t[:1] == ["portrait_mapping"] and len(t) > 1 and cur == culture:
            return t[1]
    return culture


POOL_OF = {"named character": "generals", "general": "generals", "admiral": "generals", "spy": "rogues",
           "assassin": "rogues", "witch": "rogues", "heretic": "rogues"}


def portraits(mod, faction, person, m2):
    """What the game shows for a person: {'custom': folder or None, 'files': {age: path of the
    custom picture}, 'sample': a picture of the pool (or the family picture), 'pool': how many the
    game picks from, 'how': plain words}."""
    import os
    out = {"custom": person.get("portrait"), "files": {}, "sample": None, "pool": 0, "how": ""}
    if out["custom"]:
        for a in AGES:
            out["files"][a] = _find(mod, "ui", "custom_portraits", out["custom"], "portrait_%s.tga" % a)
        out["how"] = "its own portrait: ui/custom_portraits/%s/" % out["custom"]
        return out
    c = portrait_culture(mod, faction)
    if not c:
        return out
    if person.get("source") == "record":
        pic = "son" if person.get("sex") != "female" else ("wife" if person.get("wife") else "daughter")
        out["sample"] = _find(mod, "ui", c, "portraits", "family", pic + ".tga")
        if out["sample"]:
            out["how"] = "off the map the game shows the family picture ui/%s/portraits/family/%s.tga" % (c, pic)
            return out
        kind = "record"
    else:
        kind = person.get("kind") or ""
    age = "old" if (person.get("age") or 0) >= 45 else "young"
    pool = POOL_OF.get(kind, "civilians")
    if kind == "princess":
        pool = "princesses" if m2 else "civilians"
    folder = _find(mod, "ui", c, "portraits", "portraits", age, pool)
    out["samples"] = {}
    if folder:
        pics = sorted(n for n in os.listdir(folder) if n.lower().endswith(".tga"))
        if pics:
            # the game rolls one at random at the start: show the same one each time for a name - and the
            # same number young, old and dead (one man at every age)
            i = sum(ord(ch) for ch in person.get("name") or "") % len(pics)
            out["sample"], out["pool"] = os.path.join(folder, pics[i]), len(pics)
            for a, parts in (("young", ("young", pool)), ("old", ("old", pool)),
                             ("dead", ("dead",) if pool == "generals" else ("dead", pool))):
                d = _find(mod, "ui", c, "portraits", "portraits", *parts)
                from .moddata import _ci
                p = _ci(d, pics[i]) if d else None
                if p:
                    out["samples"][a] = p
    out["how"] = ("the game picks one of %d pictures of ui/%s/portraits/portraits/%s/%s at random - shown: one of "
                  "them" % (out["pool"], c, age, pool)) if out["pool"] else "no portrait pool found for %s" % c
    return out


def portrait_size(mod, faction, m2):
    """(w, h) a portrait of this mod has: another custom portrait, else the culture's pool."""
    import os
    from PIL import Image
    for root in data_roots(mod):
        d = os.path.join(root, "ui", "custom_portraits")
        if os.path.isdir(d):
            for sub in sorted(os.listdir(d)):
                for a in AGES:
                    p = os.path.join(d, sub, "portrait_%s.tga" % a)
                    if os.path.isfile(p):
                        with Image.open(p) as im:
                            return im.size
    c = portrait_culture(mod, faction)
    folder = _find(mod, "ui", c or "", "portraits", "portraits", "young", "generals")
    if folder:
        pics = sorted(n for n in os.listdir(folder) if n.lower().endswith(".tga"))
        if pics:
            with Image.open(os.path.join(folder, pics[0])) as im:
                return im.size
    return (69, 96)


def portrait_folder(faction, name):
    return re.sub(r"[^a-z0-9_]+", "_", ("%s_%s" % (faction, name)).lower()).strip("_")


def set_portraits(plan, f, faction, person, pics, m2):
    """Medieval II: person's own portrait from pictures {age: source picture}; the line gets
    `, portrait <folder>` (kept when it has one). Pictures for the ages not given are the
    'young' one."""
    import os
    from .editors import tga_bytes
    if not m2:
        raise ValueError("%s: Rome gives portraits from its culture's pool at random - a portrait of one's own "
                         "is Medieval II's `portrait` line" % person.name)
    if not person.on_map:
        raise ValueError("%s is off the map: the game shows the family picture for such a person" % person.name)
    folder = person.portrait or portrait_folder(faction, person.name)
    size = portrait_size(plan.mod, faction, m2)
    base = os.path.join(plan.mod.data, "ui", "custom_portraits", folder)
    first = pics.get("young") or next(iter(pics.values()))
    for a in AGES:
        src = pics.get(a)
        have = _find(plan.mod, "ui", "custom_portraits", folder, "portrait_%s.tga" % a)
        if not src and have:
            continue                            # the ones not replaced stay
        plan.binary(os.path.join(base, "portrait_%s.tga" % a), tga_bytes(src or first, size))
    plan.notes.append((plan.mod.rel(base), "%s: portrait (%s) from %s (%d x %d)" % (
        person.name, ", ".join(sorted(pics)), ", ".join(os.path.basename(p) for p in pics.values()), size[0], size[1])))
    if not person.portrait:
        i = person.line
        line = f.text(i).rstrip()
        f.set(i, line + ", portrait %s" % folder)
        plan.note(f, "%s: portrait %s" % (person.name, folder))


__all__ = ["read", "apply", "trait_list", "ancillary_list", "tree_problems", "rename_in_tree", "check_name",
           "ordered", "relative_line", "trait_kind", "portraits",
           "set_portraits", "portrait_culture"]
