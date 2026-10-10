"""Where a building level can be built, and where a unit is recruited - read-only answers for the editors' windows.

A level's `requires` clause mixes terms tied to the land (`resource X` - goods on the region's land or its tags;
`hidden_resource X` - the region's tags, descr_regions.txt) with terms that are not (`factions { }`,
`building_present ...`, events, counters...). Only the land terms decide WHERE: the others are taken as met, so the
answer is "the regions where the land allows it". A clause the reader cannot follow (brackets) says so instead of
guessing."""

import re

from .textio import strip_comment, tokens

RE_LAND = re.compile(r"^(not\s+)?(hidden_resource|resource)\s+([A-Za-z0-9_]+)$", re.I)


def region_goods(mod, campaign):
    """{region: set of every resource name on its land (descr_strat's resource lines) and its tags}."""
    from .resources import read as read_res
    out = {r: {x.strip().lower() for x in (i.get("resources") or "").split(",") if x.strip()}
           for r, i in mod.regions(campaign).items()}
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    if sp:
        img = mod.region_map(campaign)
        by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}
        for res in read_res(mod.load(sp)):
            x, y = res.xy
            if 0 <= x < img.width and 0 <= y < img.height:
                r = by_colour.get(img.get(x, y))
                if r in out:
                    out[r].add(res.kind.lower())
    return out


def land_terms(requires):
    """The clause as [[(negated, kind, name)]] - OR of ANDs of the land terms - or None when it names no land term;
    'unreadable' when it has brackets."""
    text = strip_comment(requires or "")
    if "(" in text:
        return "unreadable" if re.search(r"\bresource\b", text) else None
    text = re.sub(r"factions\s*\{[^}]*\}", " ", text)
    groups, found = [], False
    for part in re.split(r"\bor\b", text):
        terms = []
        for term in re.split(r"\band\b", part):
            m = RE_LAND.match(" ".join(term.split()))
            if m:
                terms.append((bool(m.group(1)), m.group(2).lower(), m.group(3).lower()))
                found = True
        groups.append(terms)
    return groups if found else None


def regions_for(mod, campaign, requires, goods=None):
    """(regions where the land allows the clause, sorted) - or None when no land term decides it (any region), or
    'unreadable'."""
    terms = land_terms(requires)
    if terms is None or terms == "unreadable":
        return terms
    goods = goods if goods is not None else region_goods(mod, campaign)
    out = []
    for region, have in goods.items():
        if any(all((name in have) != neg for neg, _, name in group) for group in terms):
            out.append(region)
    return sorted(out)


def where_built(mod, campaign, chain):
    """[(level, requires text, regions | None | 'unreadable', [(unit, regions)] of its recruit lines whose own clause
    names the land)] for every level of a building chain."""
    from .buildings import read_buildings
    b = next((x for x in read_buildings(mod.load(mod.file("edb"))) if x.name == chain), None)
    if b is None:
        return []
    goods = region_goods(mod, campaign)
    units = {}
    for c, lv, line, _ in recruit_lines(mod):
        if c == chain and land_terms(line.split("requires", 1)[1] if "requires" in line else ""):
            units.setdefault(lv, []).append((line.split('"')[1], regions_for(mod, campaign, line.split(
                "requires", 1)[1], goods)))
    return [(lv.name, lv.requires, regions_for(mod, campaign, lv.requires, goods), units.get(lv.name, []))
            for lv in b.levels]


def recruited_by(mod, unit):
    """[(chain, level, the pool line as written, line number)] of every building level that recruits this unit
    (recruit_pool "<unit>" in Medieval II, recruit "<unit>" in Rome)."""
    return [r for r in recruit_lines(mod) if r[2].split('"')[1].strip().lower() == unit.lower()]


def pool_words(line):
    """A recruit line's numbers in plain words: Medieval II's pool (at the start, comes back each turn, at most,
    experience), Rome's experience."""
    t = line.split('"')[2].split("requires")[0].split() if line.count('"') >= 2 else []
    if line.lstrip().startswith("recruit_pool") and len(t) >= 4:
        return "%s at the start, +%s a turn, at most %s, experience %s" % tuple(t[:4])
    if t:
        return "experience %s" % t[0]
    return ""


def recruit_lines(mod):
    """[(chain, level, the recruit line as written, line number)] of every recruit / recruit_pool line."""
    out, chain, level, depth = [], None, None, 0
    names = []
    for n, line in enumerate(mod.load(mod.file("edb")).texts(), 1):
        code = strip_comment(line)
        t = tokens(code)
        if t[:1] == ["building"] and depth == 0 and len(t) > 1:
            chain, names = t[1], []
        elif t[:1] == ["levels"] and depth == 1:
            names = t[1:]
        elif depth == 2 and t and t[0] in names:
            level = t[0]
        elif t[:1] in (["recruit"], ["recruit_pool"]) and code.count('"') >= 2:
            out.append((chain, level, code.strip(), n))
        depth += code.count("{") - code.count("}")
        depth = max(depth, 0)
    return out


def open_where(editor, name):
    """The building editor's 'Where it can be built...' / the unit editor's 'Where it is recruited...' window."""
    import tkinter as tk
    from tkinter import ttk
    app, mod = editor.app, editor.mod
    camp = app.v_campaign.get()
    w = tk.Toplevel(editor)
    w.transient(app)
    w.geometry("860x560")
    from . import theme
    pal = theme.palette()
    t = tk.Text(w, wrap="word", relief="flat", padx=12, pady=8, font=("", 10), cursor="arrow", background=pal["bg"],
                foreground=pal["fg"], highlightthickness=0)
    sb = ttk.Scrollbar(w, orient="vertical", command=t.yview)
    t.configure(yscrollcommand=sb.set)
    bar = ttk.Frame(w, padding=6)
    bar.pack(side="bottom", fill="x")
    ttk.Button(bar, text="Close", command=w.destroy).pack(side="right")
    sb.pack(side="right", fill="y")
    t.pack(fill="both", expand=True)
    t.tag_configure("h", font=("", 11, "bold"), spacing1=8, spacing3=2)
    t.tag_configure("i", lmargin1=14, lmargin2=14)
    t.tag_configure("bad", foreground=theme.ink("#c00000"), lmargin1=14, lmargin2=14)
    t.tag_configure("dim", foreground=pal["muted"], lmargin1=28, lmargin2=28, font=("", 9))

    def regions_line(regions, what):
        if regions is None:
            t.insert("end", "%s: any region (no land requirement)\n" % what, "i")
        elif regions == "unreadable":
            t.insert("end", "%s: its requirement has brackets - not counted\n" % what, "i")
        elif not regions:
            t.insert("end", "%s: NOWHERE - no region has what it asks for\n" % what, "bad")
        else:
            t.insert("end", "%s: %d region(s)\n" % (what, len(regions)), "i")
            t.insert("end", ", ".join(regions) + "\n", "dim")
    if editor.kind == "building":
        w.title("Where %s can be built" % name)
        t.insert("end", "Where %s can be built\n" % name, "h")
        t.insert("end", "Counted from the land only (goods on a region's land and its tags); factions, other buildings "
                        "and events are taken as met.\n", "i")
        for level, req, regions, units in where_built(mod, camp, name):
            t.insert("end", "%s\n" % level, "h")
            regions_line(regions, "built in")
            for unit, ur in units:
                regions_line(ur, "recruits %s in" % unit)
    else:
        w.title("Where %s is recruited" % name)
        t.insert("end", "Where %s is recruited\n" % name, "h")
        rows = recruited_by(mod, name)
        if not rows:
            t.insert("end", "No building recruits it (export_descr_buildings.txt) - add it to one in the Building "
                            "editor.\n", "bad")
        goods = region_goods(mod, camp) if rows else {}
        for chain, level, line, n in rows:
            t.insert("end", "%s - %s   " % (chain, level), "h")

            def go(chain=chain):
                app.v_work.set("buildings")
                app.work_changed()
                ed = app.editor()
                ed.v_find.set(chain)
                ed.fill_list()
                names = [b[0] for b in ed.shown]
                if chain in names:
                    ed.lb.selection_clear(0, "end")
                    ed.lb.selection_set(names.index(chain))
                    ed.lb.see(names.index(chain))
                    ed.show()
            t.window_create("end", window=ttk.Button(t, text="Open in Buildings", command=go))
            t.insert("end", "\n")
            words = pool_words(line)
            if words:
                t.insert("end", words + "\n", "i")
            req = line.split("requires", 1)[1].strip() if "requires" in line else ""
            if req:
                t.insert("end", "requires %s\n" % req, "dim")
            regions_line(regions_for(mod, camp, req, goods), "in")
            t.insert("end", "(export_descr_buildings.txt line %d)\n" % n, "dim")
    t.configure(state="disabled")
    return w
