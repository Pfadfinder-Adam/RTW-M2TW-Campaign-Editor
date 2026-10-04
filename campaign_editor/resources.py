"""Resources on the campaign map: the 'resource <type>, x, y' lines near the top
of descr_strat.txt, and the types descr_sm_resources.txt knows (with the picture
the game shows for each).

    resource	iron,	83,	128                     vanilla
    	resource	marble, 92, 210;	Palma           HLR: indented, the town in a comment
    resource	iron, 1, 83, 128                    REX: a quantity before x, y

The line's own layout is kept when a resource moves; a new one copies the layout
of a resource line already in the file. Where a resource stands decides which
region has it (the game counts the resources on a region's land)."""

import os
import re

from .textio import strip_comment

RE_RES = re.compile(r"^(\s*resource\s+)([A-Za-z0-9_]+)(\s*,\s*)(-?\d+)(\s*,\s*)(-?\d+)(?:(\s*,\s*)(-?\d+))?(.*)$")


class Resource:
    def __init__(self, index, line_no, kind, xy, quantity=None):
        self.index = index            # its place among the file's resource lines (the key the window uses)
        self.line = line_no           # its line in the file
        self.kind = kind
        self.xy = xy
        self.quantity = quantity

    @property
    def key(self):
        return self.index


def _parse(text):
    """(type, (x, y), quantity or None) of a resource line, or None."""
    code = strip_comment(text)
    m = RE_RES.match(code.rstrip())
    if not m:
        return None
    if m.group(8) is not None:                                   # type, quantity, x, y
        return m.group(2), (int(m.group(6)), int(m.group(8))), int(m.group(4))
    return m.group(2), (int(m.group(4)), int(m.group(6))), None


def read(f):
    """[Resource] of a loaded descr_strat.txt TextFile, in file order."""
    out = []
    for i in range(len(f.raw)):
        p = _parse(f.text(i))
        if p:
            out.append(Resource(len(out), i, p[0], p[1], p[2]))
    return out


def types(mod):
    """{type: icon path or None} from descr_sm_resources.txt, in the file's order."""
    key = ("resource_types",)
    if key in mod._cache:
        return mod._cache[key]
    out = {}
    p = mod.file("resources")
    if p:
        cur = None
        for l in mod.load(p).texts():
            t = strip_comment(l).split()
            if len(t) >= 2 and t[0] == "type":
                cur = t[1]
                out[cur] = None
            elif len(t) >= 2 and t[0] == "icon" and cur:
                icon = os.path.join(mod.data, *t[1].replace("\\", "/").split("/")[1:]) \
                    if t[1].lower().startswith("data/") else os.path.join(mod.data, t[1])
                out[cur] = icon if os.path.isfile(icon) else None
    mod._cache[key] = out
    return out


def problem(mod, campaign, xy, taken=()):
    """Why a resource may not lie on tile xy, or None: it needs land (a town's tile
    is fine - HLR keeps its slaves there) and a tile of its own (no file has two)."""
    img = mod.region_map(campaign)
    x, y = xy
    if not (0 <= x < img.width and 0 <= y < img.height):
        return "off the map"
    if mod.is_sea(campaign, xy):
        return "that is sea"
    if tuple(xy) in set(tuple(t) for t in taken):
        return "another resource lies there"
    return None


def _moved_line(text, xy):
    """text with x, y set (layout, quantity and comment kept)."""
    body, sep, comment = text.partition(";")
    m = RE_RES.match(body.rstrip())
    tail = body[len(body.rstrip()):]
    if m.group(8) is not None:
        new = "%s%s%s%s%s%d%s%d" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), xy[0], m.group(7), xy[1])
    else:
        new = "%s%s%s%d%s%d" % (m.group(1), m.group(2), m.group(3), xy[0], m.group(5), xy[1])
    return new + (m.group(9) or "") + tail + sep + comment


def _new_line(template, kind, xy, town=None):
    """A line for a new resource in the layout of an existing one (without a
    quantity; with the town as a comment where the file names towns)."""
    body, sep, _ = template.partition(";")
    m = RE_RES.match(body.rstrip())
    if not m:
        return "resource\t%s,\t%d,\t%d" % (kind, xy[0], xy[1])
    sep2 = m.group(7) if m.group(8) is not None else m.group(5)
    line = "%s%s%s%d%s%d" % (m.group(1), kind, m.group(3), xy[0], sep2, xy[1])
    if sep and town:
        line += ";\t" + town
    return line


def apply(plan, campaign, changes):
    """changes = {'moved': {index: (x, y)}, 'removed': [index], 'added': [{'type', 'xy'}],
    'region_tags': {region: 'tag, tag'}} - JSON keys may be strings. Writes descr_strat.txt
    (and descr_regions.txt for region tags)."""
    if not changes:
        return
    if changes.get("forts"):                     # below the resources: their lines keep their places
        from .forts import apply as apply_forts
        apply_forts(plan, campaign, changes["forts"])
    mod = plan.mod
    moved = {int(k): tuple(v) for k, v in (changes.get("moved") or {}).items()}
    removed = {int(k) for k in changes.get("removed") or []}
    added = list(changes.get("added") or [])
    known = types(mod)
    if moved or removed or added:
        f = plan.edit(mod.campaign_file(campaign, "descr_strat.txt"))
        now = read(f)
        by_index = {r.index: r for r in now}
        for k in list(moved) + list(removed):
            if k not in by_index:
                raise ValueError("resource %d is not in descr_strat.txt (the file changed?)" % k)
        # where every resource will lie, to refuse two on one tile
        final = [moved.get(r.index, r.xy) for r in now if r.index not in removed] + \
            [tuple(a["xy"]) for a in added]
        by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}
        img = mod.region_map(campaign)

        def town_of(xy):
            if not (0 <= xy[0] < img.width and 0 <= xy[1] < img.height):
                return None
            r = by_colour.get(img.get(*xy))
            return (mod.regions(campaign).get(r) or {}).get("settlement") if r else None

        for i, r in enumerate(now):
            if r.index in moved:
                xy = moved[r.index]
                others = final[:]
                others.remove(xy)
                why = problem(mod, campaign, xy, others)
                if why:
                    raise ValueError("%s at %d, %d cannot go to %d, %d: %s" % (r.kind, r.xy[0], r.xy[1], xy[0], xy[1], why))
                line = _moved_line(f.text(r.line), xy)
                was, now_town = town_of(r.xy), town_of(xy)
                body, sep, comment = line.partition(";")
                if sep and was and now_town and comment.strip() == was and was != now_town:
                    line = body + sep + comment.replace(was, now_town)        # HLR notes the town
                f.set(r.line, line)
                plan.note(f, "%s moved from %d, %d to %d, %d" % (r.kind, r.xy[0], r.xy[1], xy[0], xy[1]))
        for a in added:
            if known and a["type"] not in known:
                raise ValueError("no resource type '%s' in descr_sm_resources.txt" % a["type"])
            xy = tuple(a["xy"])
            others = final[:]
            others.remove(xy)
            why = problem(mod, campaign, xy, others)
            if why:
                raise ValueError("new %s at %d, %d: %s" % (a["type"], xy[0], xy[1], why))
        # new lines after the last resource line, in its layout (one without a quantity if there is one)
        if added:
            plain = [r for r in now if r.quantity is None] or now
            template = f.text(plain[-1].line) if plain else "resource\tx,\t0,\t0"
            at = now[-1].line + 1 if now else _resources_start(f)
            lines = []
            for a in added:
                xy = tuple(a["xy"])
                lines.append(_new_line(template, a["type"], xy, town_of(xy)))
                plan.note(f, "new %s at %d, %d%s" % (a["type"], xy[0], xy[1],
                                                     " (%s)" % town_of(xy) if town_of(xy) else ""))
            f.raw[at:at] = [f.make(l) for l in lines]
        for r in sorted((by_index[k] for k in removed), key=lambda r: -r.line):
            del f.raw[r.line]
            plan.note(f, "%s at %d, %d removed" % (r.kind, r.xy[0], r.xy[1]))
    tags = changes.get("region_tags") or {}
    if tags:
        set_region_tags(plan, campaign, tags)


def _resources_start(f):
    """Where resource lines go in a file that has none: before the first faction block."""
    for i in range(len(f.raw)):
        if strip_comment(f.text(i)).split()[:1] == ["faction"]:
            return i
    return len(f.raw)


def set_region_tags(plan, campaign, tags):
    """tags = {region: 'a, b, c'}: the resources line of the regions' entries in descr_regions.txt
    (the region's resource tags; in HLR also the hidden resources that open units)."""
    from .regionedit import set_region_lines
    changes = {}
    for r, t in tags.items():
        want = ", ".join(x.strip() for x in t.split(",") if x.strip())
        if not want:
            raise ValueError("%s: a region needs at least one resource tag" % r)
        changes[r] = {"resources": want}
    set_region_lines(plan, plan.edit(plan.mod.campaign_file(campaign, "descr_regions.txt")), changes)
