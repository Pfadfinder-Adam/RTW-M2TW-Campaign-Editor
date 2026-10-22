"""A new climate made as a copy of one the mod has (Climate library > New climate from this...), and a climate's own
campaign-map pieces changed (its ground texture of a ground type, its trees).

A climate is found by NAME in every file that knows climates (climatelib), and the battle map crashes on a climate
whose name it finds no block for - so a new climate is never made empty: every block of the source climate is copied
under the new name, file by file, and the new climate goes LAST in descr_climates.txt's 'climates' list (each
name's place there is its engine slot: the old ones keep theirs). With REX / M2EX the engine has 32 slots; the
original exes know only their 12.

How each kind of place is copied (measured on both games' files, 2026-10-22):
- a block of its own ('climate x', 'sea x summer', 'x modifies default', '<climate id="x">', the roads' <climate>
  with <name>x</name>): the whole block again, right after it, under the new name;
- a list of climates ('climates x, y'): the new name added after x (the weather, sounds, day types of x go for it);
- a line led by the name ('x any tree_A_palm', descr_settlement_plan): the line again for the new name;
- one thing's own climate ('climate x' of a disaster, a custom battle place, an ambient town) and anything else:
  left as it is (that thing stays x's);
- the name players read (text/climates.txt) and the mountains' own textures (tile_textures/x/) copied too."""

import os
import re

from . import climatelib as L

NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def _word(name):
    return re.compile(r"(?<![\w])" + re.escape(name) + r"(?![\w])", re.I)


def problems(mod, source, new, colour):
    """[why] the copy cannot be made: a name the files cannot hold, one taken, a colour taken, past 32 slots."""
    from . import terrain as T
    out = []
    if not NAME.match(new or ""):
        out.append("the name must be small letters, digits and _ (no spaces), starting with a letter")
    have = T.climates(mod)
    if any(n.lower() == (new or "").lower() for n, _, _ in have):
        out.append("a climate named %s is there already" % new)
    if any(c == tuple(colour) for _, c, _ in have):
        out.append("the colour %d %d %d is another climate's - map_climates.tga tells climates apart by colour"
                   % tuple(colour))
    if not any(n == source for n, _, _ in have):
        out.append("no climate %s to copy" % source)
    path = mod.find("descr_climates.txt")
    if path and len(L.listed(mod.load(path).texts())) >= L.SLOTS:
        out.append("all %d climate slots are taken (the engine stops at %d)" % (L.SLOTS, L.SLOTS))
    return out


def _block_end(lines, i):
    """(the line after the block whose header is line i, True) - or (i + 1, False) when no block opens there."""
    t = L._strip(lines[i])
    j = i + 1
    if not t.endswith("{"):
        while j < len(lines) and not L._strip(lines[j]):
            j += 1
        if j >= len(lines) or L._strip(lines[j]).split()[:1] != ["{"]:
            return i + 1, False
        j += 1
    depth = 1
    while j < len(lines) and depth > 0:
        v = L._strip(lines[j])
        depth += v.count("{") - v.count("}")
        j += 1
    return j, True


def _xml_end(lines, i, tag):
    end = re.compile(r"</\s*" + re.escape(tag) + r"\s*>")
    j = i
    while j < len(lines) and not end.search(lines[j]):
        j += 1
    return j + 1


def _xml_parent(lines, i):
    """(start, end, tag) of the XML element line i sits in (its nearest unclosed open tag above), or None."""
    stack = 0
    for k in range(i - 1, max(-1, i - 200), -1):
        s = lines[k].strip()
        if re.match(r"</\s*\w+", s):
            stack += 1
            continue
        m = re.match(r"<\s*(\w+)\b[^>]*>$", s)
        if m and not s.endswith("/>"):
            if stack == 0:
                return k, _xml_end(lines, k, m.group(1)), m.group(1)
            stack -= 1
    return None


def copy_places(lines, source, new, aliases=()):
    """[(insert at, [new lines])] for one file's lines: every place of source copied for new (module text); the
    inserts in the order of the file (apply them from the last)."""
    names = [source] + [a for a in aliases if a]
    pats = [_word(n) for n in names]
    out, i, n = [], 0, len(lines)
    xml_done = set()

    def rename(text):
        for p in pats:
            text = p.sub(new, text, count=1)
        return text
    while i < n:
        raw = lines[i]
        s = raw.strip()
        text = s if s.startswith("<") else L._strip(raw)
        if not text or not any(p.search(text) for p in pats):
            i += 1
            continue
        if s.startswith("<"):
            m = re.match(r"<\s*(\w+)\b[^>]*\bid\s*=\s*\"([^\"]*)\"", s)
            if m and not s.endswith("/>") and m.group(2).lower() in [x.lower() for x in names]:
                j = _xml_end(lines, i, m.group(1))
                out.append((j, [rename(lines[i])] + lines[i + 1:j]))
                i = j
                continue
            m = re.match(r"<\s*name\s*>\s*([^<]*?)\s*<\s*/\s*name\s*>", s)
            if m and m.group(1).lower() in [x.lower() for x in names]:
                par = _xml_parent(lines, i)
                if par and par[0] not in xml_done:
                    xml_done.add(par[0])
                    out.append((par[1], [rename(x) if k == i else x for k, x in enumerate(lines[par[0]:par[1]],
                                                                                          par[0])]))
                    i = par[1]
                    continue
            i += 1
            continue
        words = text.replace(",", " ").split()
        if any(L._own_header(text, x) for x in names):
            j, block = _block_end(lines, i)
            if block:
                out.append((j, [rename(lines[i])] + lines[i + 1:j]))
                i = j
                continue
        if words and words[0].lower() == "climates":
            hit = next(p for p in pats if p.search(raw))
            m = hit.search(raw)
            after = raw[m.end():]
            sep = ", " if "," in text else (re.match(r"\s*", after).group(0) or " ")
            body = raw.rstrip("\r\n")
            out.append((i, None, body[:m.end()] + (sep if sep.strip() else " ") + new + body[m.end():]))
        elif words and words[0].lower() in [x.lower() for x in names] and len(words) > 1:
            out.append((i + 1, [rename(raw)]))
        i += 1
    return out


def _apply_places(f, places):
    """The places of copy_places laid into TextFile f (a list line changed in place, the rest inserted)."""
    for place in sorted(places, key=lambda p: p[0], reverse=True):
        if len(place) == 3:
            f.set(place[0], place[2])
        else:
            f.insert(place[0], [x[:-1] if x.endswith("\r") else x for x in place[1]])


def write_copy(plan, source, new, colour, title=None, game=None):
    """The new climate new (colour (r, g, b); title: the name players read) made in plan as a copy of source, in
    every file of climatelib.FILES that names source. -> [(file, how many places)]."""
    mod = plan.mod
    if game is None:
        from .limits import game_kind
        game = game_kind(mod)
    why = problems(mod, source, new, colour)
    if why:
        raise ValueError("; ".join(why))
    path = mod.find("descr_climates.txt")
    order = L.listed(mod.load(path).texts())
    aliases = []
    if source in order:
        other = L.slot_name(order.index(source), game)
        if other and other not in (source, "default"):
            aliases.append(other)
    done = []
    for _section, rel in L.FILES:
        if rel in ("descr_climates_lookup.txt",):
            continue
        p = mod.find(rel)
        if not p:
            continue
        if rel == "text/climates.txt":
            continue                                    # _text: the .txt or Medieval II's .strings.bin
        f = plan.edit(p)
        lines = f.texts()
        if rel == "descr_climates.txt":
            _climates_file(plan, f, lines, source, new, colour)
            done.append((rel, 2))
            continue
        places = copy_places(lines, source, new, aliases)
        if places:
            _apply_places(f, places)
            plan.note(f, "climate %s copied from %s (%d place(s))" % (new, source, len(places)))
            done.append((rel, len(places)))
    _text(plan, source, new, title)
    for name in [source] + aliases:
        for season in ("summer", "winter"):
            rel = "terrain/aerial_map/tile_textures/%s/%s" % (name, season)
            for d in mod.dirs(rel)[:1]:
                plan.copy(d, os.path.join(mod.data, "terrain", "aerial_map", "tile_textures", new, season))
                done.append((rel, 1))
    from .limits import engine_of
    if not engine_of(mod) and len(order) + 1 > 12:
        plan.warn(None, "without %s the game knows its own 12 climates only: a battle fought in %s may crash - "
                        "play the mod with %s" % ("M2EX" if game == "medieval2" else "REX", new,
                                                  "M2EX" if game == "medieval2" else "REX"))
    return done


def _climates_file(plan, f, lines, source, new, colour):
    """descr_climates.txt: new LAST in the 'climates' list (the old ones keep their slots), the source's block copied
    after it with the new colour."""
    end = last = None
    state = 0
    for i, raw in enumerate(lines):
        t = L._strip(raw).split()
        if not t:
            continue
        if state == 0 and t[0] == "climates":
            state = 1 if t[-1] != "{" else 2
        elif state == 1 and t[0] == "{":
            state = 2
        elif state == 2:
            if t[0] == "}":
                end = i
                break
            last = i
    b = L.climates_block(lines, source)
    start = b["line"]
    stop, _ = _block_end(lines, start)
    block = [lines[start].replace(source, new, 1)] + lines[start + 1:stop]
    block = [re.sub(r"^(\s*colour\s+)\d+\s+\d+\s+\d+", lambda m: m.group(1) + "%d %d %d" % tuple(colour), x)
             for x in block]
    f.insert(stop, [""] + block)
    if end is not None:
        at = last if last is not None else end - 1
        indent = re.match(r"\s*", lines[last]).group(0) if last is not None else "\t"
        f.insert(at + 1, [indent + new])
    plan.note(f, "climate %s made from %s (slot %d)" % (new, source, len(L.listed(lines)) + 1))


def _text(plan, source, new, title):
    """The name players read: climates.txt's {new} (the given title, else the source's words) - the .txt, or one
    made from Medieval II's compiled .strings.bin (strtables.write_texts)."""
    from . import strtables
    words = strtables.strings(plan.mod, "climates.txt").get(source.upper())
    strtables.write_texts(plan, "climates.txt", {new: title or (words + " 2" if words else new)})


def set_ground(plan, climate, slot, summer, winter=None):
    """descr_aerial_map_ground_types.txt: climate's slot (GROUND_SLOTS) takes the picture summer (winter: its winter
    picture; None keeps the line's own). A climate with no block of its own gets one, a copy of 'default' (so only
    the slot asked changes how it looks)."""
    p = plan.mod.find("descr_aerial_map_ground_types.txt")
    if not p:
        raise ValueError("this mod has no descr_aerial_map_ground_types.txt")
    f = plan.edit(p)
    lines = f.texts()
    head = _header_at(lines, "climate", climate)
    if head is None:
        d = _header_at(lines, "climate", "default")
        if d is None:
            raise ValueError("descr_aerial_map_ground_types.txt has no 'default' block to start from")
        stop, _ = _block_end(lines, d)
        f.insert(len(lines), [""] + [lines[d].replace("default", climate, 1)] + lines[d + 1:stop])
        lines = f.texts()
        head = _header_at(lines, "climate", climate)
    stop, _ = _block_end(lines, head)
    for i in range(head + 1, stop):
        t = L._strip(lines[i]).split()
        if t[:1] == [slot]:
            old_winter = t[2] if len(t) > 2 else None
            lead = re.match(r"\s*", lines[i]).group(0)
            w = winter if winter is not None else old_winter
            f.set(i, "%s%s\t\t%s%s" % (lead, slot, summer, ("\t" + w) if w else ""))
            break
    else:
        close = stop - 1
        lead = "\t"
        w = winter or ""
        f.insert(close, ["%s%s\t\t%s%s" % (lead, slot, summer, ("\t" + w) if w else "")])
    plan.note(f, "%s: %s -> %s" % (climate, slot, summer))


def set_tree(plan, climate, line_no, model, cell=None):
    """descr_climates.txt: the 'strategy' line line_no (1 = the first line) of climate's block names model (a .cas in
    terrain/aerial_map/tree_models/) - its season and kind kept; cell: its sprite cell, None keeps it."""
    p = plan.mod.find("descr_climates.txt")
    f = plan.edit(p)
    i = line_no - 1
    t = L._strip(f.text(i)).split()
    if t[:1] != ["strategy"] or len(t) < 4:
        raise ValueError("line %d of descr_climates.txt is not a tree line" % line_no)
    lead = re.match(r"\s*", f.text(i)).group(0)
    f.set(i, "%sstrategy\t%s\t%s\t%s\t%s" % (lead, t[1], t[2], model, cell if cell is not None else
                                                (t[4] if len(t) > 4 else "0")))
    plan.note(f, "%s: %s %s tree -> %s" % (climate, t[1], t[2], model))


def _header_at(lines, kind, name):
    for i, raw in enumerate(lines):
        if L._strip(raw).split()[:2] == [kind, name]:
            return i
    return None


def pool(mod, folder, ends=(".tga", ".dds", ".texture")):
    """[file name] in data/<folder> of the mod and the game under it (loose files), sorted - the pictures or models a
    climate's slot may take."""
    seen = {}
    for d in mod.dirs(folder):
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            if n.lower().endswith(ends) and os.path.isfile(os.path.join(d, n)):
                base = n[:-4] if n.lower().endswith(".tga.dds") else n
                seen.setdefault(base.lower(), base)
    return sorted(seen.values(), key=str.lower)


__all__ = ["problems", "copy_places", "write_copy", "set_ground", "set_tree", "pool"]
