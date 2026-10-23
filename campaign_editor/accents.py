"""Voice accents of factions: which voices a faction's soldiers, generals, agents and diplomats speak with.

Medieval II (with M2EX or without): descr_sounds_accents.txt (included by descr_sounds.txt) names the accents and the
factions of each:

    accent English
        factions england, normans, saxons

The engine (SOUND_DB::parse_accent_type) makes an accent of each name in file order and gives it the factions of the
`factions` lines after it; every sound bank that speaks (export_descr_sounds_units_voice, _soldier_voice,
_stratmap_voice, _prebattle, _units_battle_events, descr_sounds_units_confirm...) then holds `accent <names>`
blocks, and a faction speaks what the blocks of its accent hold. What the engine does with what it reads:
- a faction the file names that the mod does not have: 'Unknown faction' script error;
- a faction named twice: logged, the later accent wins;
- a faction named nowhere: logged ('accent_type not found for factions'), it has no voice in battle and on the map;
- a bank naming an accent the file does not define (names are compared letter case and all): 'Unrecognised
  accent', that bank is not read;
- an accent no bank speaks: its factions are silent;
- a unit's own `accent` line in export_descr_unit.txt (after voice_type) speaks that accent in battle whatever its
  owner's; on the campaign map only with descr_campaign_db's <enable_unit_accent_overrides>.
Rebel armies speak the accent of the faction they split from when the game's 'sub-faction accents' option is on.

Rome (with REX or without) has no accents file: its banks are keyed by culture (`culture roman`, `culture eastern,
carthaginian,egyptian`), so a faction speaks the voices of its culture (descr_sm_factions.txt) - the culture is its
accent there. REX adds the same sub-faction option for rebels.

The game compiles the sound texts into data/sounds/events.dat + .idx; Plan.stale_sounds removes those after a change
so the game builds them again."""

import os
import re

from .textio import strip_comment

ACCENTS_FILE = "descr_sounds_accents.txt"
# the sound texts that may hold `accent` blocks (the banks), found in the mod's data and the game's under it
RE_BANK_FILE = re.compile(r"^(export_)?descr_sounds.*\.txt$", re.I)
RE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
# lines that end an accent block of a bank (the next block, the next bank, the file's defaults)
RE_BLOCK_END = re.compile(r"^\s*(accent\b|BANK:|DEFAULT:|include\b)", re.I)


class Accent:
    """One `accent <name>` of the accents file: its line, and its `factions` lines [(line, [factions])]."""

    def __init__(self, name, line):
        self.name, self.line, self.lists = name, line, []

    @property
    def factions(self):
        return [x for _, names in self.lists for x in names]

    @property
    def end(self):
        """The line after the accent's last `factions` line."""
        return (self.lists[-1][0] if self.lists else self.line) + 1


def _words(rest):
    return [x for x in rest.replace(",", " ").split() if x]


def parse(f):
    """[Accent] of a loaded accents file, in file order (the engine's accent numbers)."""
    out = []
    for i, line in enumerate(f.texts()):
        code = strip_comment(line).strip()
        word, _, rest = code.partition(" ")
        key = word.lower()
        if key == "accent" and rest.strip():
            out.append(Accent(rest.split()[0], i))
        elif key == "factions" and out:
            out[-1].lists.append((i, _words(rest)))
    return out


def has_accents(mod):
    """True when the game reads an accents file (Medieval II); Rome speaks by culture."""
    return bool(mod.file("accents")) if mod else False


def _file(src, path):
    """The file as the plan leaves it (src a Plan), or as it is on disk (src a ModData)."""
    files = getattr(src, "files", None)
    if files is not None and path in files:
        return files[path]
    mod = getattr(src, "mod", src)
    return mod.load(path)


def _mod(src):
    return getattr(src, "mod", src)


def read(src):
    """[Accent] of the mod (src: ModData, or a Plan - then as the plan leaves the file); [] on Rome."""
    p = _mod(src).file("accents")
    return parse(_file(src, p)) if p else []


def names(src):
    """The accents' names in the game's order."""
    seen, out = set(), []
    for a in read(src):
        if a.name not in seen:
            seen.add(a.name)
            out.append(a.name)
    return out


def table(src):
    """{faction (small letters, as the engine finds it): accent} - a faction named twice gets the later one."""
    out = {}
    for a in read(src):
        for fac in a.factions:
            out[fac.lower()] = a.name
    return out


def accent_of(src, faction):
    """Medieval II: the faction's accent (None when the file does not name it); Rome: None."""
    return table(src).get((faction or "").lower())


def voice_of(mod, faction):
    """What the faction speaks with, in words: ('accent', name) on Medieval II, ('culture', name) on Rome."""
    if has_accents(mod):
        return "accent", accent_of(mod, faction)
    try:
        return "culture", mod.culture(faction)
    except Exception:
        return "culture", None


# ---------------------------------------------------------------------------
# the banks: which accents the sound texts speak
# ---------------------------------------------------------------------------
def bank_files(mod):
    """The sound texts the game reads that may hold accent blocks (not the accents file): the mod's own copy of a name
    first, else the game's - [path] in name order."""
    seen, out = set(), []
    for root in mod.roots():
        try:
            listed = sorted(os.listdir(root))
        except OSError:
            continue
        for n in listed:
            low = n.lower()
            if low in seen or low == ACCENTS_FILE or not RE_BANK_FILE.match(n):
                continue
            p = os.path.join(root, n)
            if os.path.isfile(p):
                seen.add(low)
                out.append(p)
    return sorted(out, key=lambda p: os.path.basename(p).lower())


def bank_lines(f):
    """[(line, [accent names])] of a loaded bank file's `accent` lines."""
    out = []
    for i, line in enumerate(f.texts()):
        code = strip_comment(line).strip()
        word, _, rest = code.partition(" ")
        if word.lower() == "accent" and rest.strip():
            out.append((i, [x.strip() for x in rest.split(",") if x.strip()]))
    return out


def voiced(src):
    """{accent name: [bank file names that speak it]} (names as the banks spell them - the engine compares them
    letter case and all)."""
    mod = _mod(src)
    out = {}
    for p in bank_files(mod):
        for _, accs in bank_lines(_file(src, p)):
            for a in accs:
                lst = out.setdefault(a, [])
                if os.path.basename(p) not in lst:
                    lst.append(os.path.basename(p))
    return out


# ---------------------------------------------------------------------------
# changes (in a Plan)
# ---------------------------------------------------------------------------
def _indent(f, accents_):
    """The `factions` lines' indent and separator the file uses (commas, as Medieval II's own file, when no line
    shows one: lists of one name each)."""
    ind, sep = "    ", ", "
    lines = [(f.text(i), lst) for a in accents_ for i, lst in a.lists]
    if lines:
        t = lines[0][0]
        ind = t[:len(t) - len(t.lstrip())]
        if not any("," in strip_comment(t) for t, _ in lines) and any(len(lst) > 1 for _, lst in lines):
            sep = " "
    return ind, sep


def _drop(f, accents_, faction):
    """The faction out of every `factions` line; a line left empty goes. Returns [accent names it left]."""
    left, gone = [], []
    low = faction.lower()
    for a in accents_:
        for i, lst in a.lists:
            if low not in (x.lower() for x in lst):
                continue
            left.append(a.name)
            rest = [x for x in lst if x.lower() != low]
            if not rest:
                gone.append(i)
                continue
            t = f.text(i)
            ind = t[:len(t) - len(t.lstrip())]
            sep = ", " if "," in strip_comment(t) else " "
            comment = t[len(strip_comment(t)):]
            f.set(i, "%sfactions %s%s" % (ind, sep.join(rest), (" " + comment.strip()) if comment.strip() else ""))
    for i in sorted(gone, reverse=True):
        f.delete(i, i + 1)
    return left


def _find(accents_, name):
    return next((a for a in accents_ if a.name == name), None)


def set_accent(plan, faction, accent):
    """The faction speaks accent: it leaves every `factions` line naming it and joins the accent's (a `factions`
    line of its own when the accent has none). The accent must be one the file defines (letter case and all)."""
    path = plan.mod.file("accents")
    if not path:
        raise ValueError("this game has no voice accents (Rome speaks by culture: change the faction's culture)")
    f = plan.edit(path)
    acc = parse(f)
    target = _find(acc, accent)
    if target is None:
        raise ValueError("'%s' is no accent of %s (%s)" % (accent, ACCENTS_FILE, ", ".join(a.name for a in acc)))
    if faction.lower() in (x.lower() for x in target.factions) and \
            sum(faction.lower() in (x.lower() for x in a.factions) for a in acc) == 1:
        return
    was = _drop(f, acc, faction)
    acc = parse(f)
    target = _find(acc, accent)
    ind, sep = _indent(f, acc)
    if target.lists:
        i, lst = target.lists[-1]
        t = f.text(i)
        code = strip_comment(t).rstrip()
        own = ", " if "," in code else (" " if len(lst) > 1 else sep)
        f.set(i, code + own + faction + t[len(code):])
    else:
        f.insert(target.line + 1, ["%sfactions %s" % (ind, faction)])
    plan.note(f, "%s speaks the %s accent%s" % (faction, accent, " (was %s)" % ", ".join(was) if was else ""))
    _warn_silent(plan, accent)


def _warn_silent(plan, accent):
    if plan.mod and accent not in voiced(plan):
        plan.warn(None, "no sound file speaks the %s accent - its factions are silent in battle and on the map "
                        "(New accent... copies another's voices for it)" % accent)


def _block_end(texts, i):
    """The line after the bank block that starts on line i (its `accent` line): up to the next accent / bank / defaults
    line, the blank and comment lines before that one left to it."""
    j = i + 1
    while j < len(texts) and not RE_BLOCK_END.match(texts[j]):
        j += 1
    while j > i + 1 and not strip_comment(texts[j - 1]).strip():
        j -= 1
    return j


def new_accent(plan, name, like, factions=()):
    """A new accent name that speaks like the accent like: defined in the accents file (after the last accent), every
    bank block of like copied under the new name (a block several accents share gets the new name in its list) - so
    nothing is silent; then each of factions moves to it. The copies point at the same sound files: put the new
    accent's own sounds in the Unit editor's Voice block or by hand."""
    path = plan.mod.file("accents")
    if not path:
        raise ValueError("this game has no voice accents (Rome speaks by culture)")
    if not RE_NAME.match(name or ""):
        raise ValueError("an accent's name is one word of letters, digits and _ (the game reads one word)")
    f = plan.edit(path)
    acc = parse(f)
    if any(a.name.lower() == name.lower() for a in acc):
        raise ValueError("there is an accent %s already" % next(a.name for a in acc if a.name.lower() == name.lower()))
    if like and _find(acc, like) is None:
        raise ValueError("'%s' is no accent of %s" % (like, ACCENTS_FILE))
    at = max((a.end for a in acc), default=len(f))
    ind, _ = _indent(f, acc)
    f.insert(at, ["", "accent %s" % name] if at and strip_comment(f.text(at - 1)).strip() else ["accent %s" % name])
    plan.note(f, "new accent %s%s" % (name, " - it speaks like %s" % like if like else ""))
    if like:
        copied = 0
        for p in bank_files(plan.mod):
            if not any(like in accs for _, accs in bank_lines(_file(plan, p))):
                continue
            b = plan.edit(p)
            n = _copy_blocks(b, like, name)
            if n:
                copied += n
                plan.note(b, "%d block(s) of the %s accent given to %s too" % (n, like, name))
        if not copied:
            plan.warn(None, "no sound file speaks %s - %s has no voices to copy" % (like, name))
    for fac in factions:
        set_accent(plan, fac, name)
    if not factions:
        plan.warn(None, "no faction speaks %s yet - pick it as a faction's Voice accent" % name)


def _accent_lines(texts):
    """[(line, [accent names])] of a bank's `accent` lines, from the last up (a change below never moves those
    above)."""
    out = []
    for i, t in enumerate(texts):
        code = strip_comment(t).strip()
        word, _, rest = code.partition(" ")
        if word.lower() == "accent":
            out.append((i, [x.strip() for x in rest.split(",") if x.strip()]))
    return out[::-1]


def _copy_blocks(f, like, name):
    """Each `accent` block of like in a loaded bank file copied for name right after it (a shared list gets the name
    added). Returns how many blocks were copied or joined."""
    texts = f.texts()
    n = 0
    for i, accs in _accent_lines(texts):
        if like not in accs or name in accs:
            continue
        t = texts[i]
        n += 1
        if len(accs) > 1:
            body = strip_comment(t).rstrip()
            f.set(i, body + ", " + name + t[len(body):])
            continue
        end = _block_end(texts, i)
        block = [re.sub(r"(\baccent\s+)%s\b" % re.escape(like), lambda m: m.group(1) + name, t, count=1)]
        f.insert(end, block + texts[i + 1:end])
    return n


def remove_accent(plan, name, to):
    """The accent out of the game: its factions speak to (an accent of the file), its definition and every bank block
    of its own go, a list it shares loses its name (the opposite of new_accent)."""
    path = plan.mod.file("accents")
    if not path:
        raise ValueError("this game has no voice accents")
    f = plan.edit(path)
    acc = parse(f)
    me = _find(acc, name)
    if me is None:
        raise ValueError("'%s' is no accent of %s" % (name, ACCENTS_FILE))
    if to == name or _find(acc, to) is None:
        raise ValueError("pick another accent for its factions")
    moving = list(me.factions)
    for fac in moving:
        set_accent(plan, fac, to)
    acc = parse(f)
    me = _find(acc, name)
    start, end = me.line, me.end
    while start > 0 and not strip_comment(f.text(start - 1)).strip() and not f.text(start - 1).strip():
        start -= 1
    f.delete(start, end)
    plan.note(f, "accent %s removed%s" % (name, " - %s speak %s" % (", ".join(moving), to) if moving else ""))
    for p in bank_files(plan.mod):
        if not any(name in accs for _, accs in bank_lines(_file(plan, p))):
            continue
        b = plan.edit(p)
        n = _drop_blocks(b, name)
        if n:
            plan.note(b, "%d block(s) of the %s accent removed" % (n, name))


def _drop_blocks(f, name):
    texts = f.texts()
    n = 0
    for i, accs in _accent_lines(texts):
        if name not in accs:
            continue
        n += 1
        if len(accs) > 1:
            t = texts[i]
            ind = t[:len(t) - len(t.lstrip())]
            comment = t[len(strip_comment(t)):]
            f.set(i, "%saccent %s%s" % (ind, ", ".join(a for a in accs if a != name), comment))
            continue
        f.delete(i, _block_end(texts, i))
    return n


def take_after(plan, src, faction, new):
    """Bring a faction: the new faction speaks the brought one's accent when this mod has an accent of that name (the
    frame's stays otherwise - said)."""
    if not has_accents(plan.mod):
        return
    theirs = accent_of(src, faction)
    if not theirs or theirs == accent_of(plan, new):
        return
    if theirs in names(plan):
        set_accent(plan, new, theirs)
    else:
        plan.warn(None, "%s spoke the %s accent in its mod - this mod has no such accent, %s speaks %s (New accent... "
                        "on the Faction tab makes one)" % (faction, theirs, new, accent_of(plan, new) or "none"))


# ---------------------------------------------------------------------------
# Check mod files
# ---------------------------------------------------------------------------
def problems(mod):
    """[(message, fault)] of the accents as the engine reads them: fault True where the game errs or a faction is
    silent, False for a note."""
    p = mod.file("accents")
    if not p:
        return []
    out = []
    rel = os.path.basename(p)
    acc = read(mod)
    have = {n.lower() for n, _ in mod.factions()}
    seen, defined = {}, set()
    for a in acc:
        if a.name in defined:
            out.append(("%s line %d: the accent %s is defined twice (the game logs it, the factions join the first)"
                        % (rel, a.line + 1, a.name), False))
        defined.add(a.name)
        for i, lst in a.lists:
            for fac in lst:
                low = fac.lower()
                if low not in have:
                    out.append(("%s line %d: %s is no faction of descr_sm_factions.txt - the game stops on an "
                                "'Unknown faction' script error" % (rel, i + 1, fac), True))
                elif low in seen and seen[low] != a.name:
                    out.append(("%s line %d: %s speaks %s and %s - the game takes the later one (%s)"
                                % (rel, i + 1, fac, seen[low], a.name, a.name), False))
                seen[low] = a.name
    missing = [n for n, _ in mod.factions() if n.lower() not in seen]
    if missing:
        out.append(("%s names no accent for %s - the game logs 'accent_type not found for factions' and they have no "
                    "voice of their own in battle and on the map (pick their Voice accent on the Faction tab)"
                    % (rel, ", ".join(missing)), True))
    spoken = voiced(mod)
    for a in acc:
        if a.name not in spoken and a.factions:
            out.append(("no sound file speaks the accent %s - %s %s silent (New accent... copies another's voices)"
                        % (a.name, ", ".join(a.factions), "is" if len(a.factions) == 1 else "are"), True))
    for b in bank_files(mod):
        for i, accs in bank_lines(mod.load(b)):
            for x in accs:
                if x not in defined:
                    close = next((d for d in defined if d.lower() == x.lower()), None)
                    out.append(("%s line %d: the accent %s is not in %s%s - the game does not read that sound bank "
                                "('Unrecognised accent')" % (os.path.basename(b), i + 1, x, rel,
                                                             " (it has %s: the letter case counts)" % close if close
                                                             else ""), True))
    edu = mod.file("edu")
    if edu:
        cur = None
        for i, line in enumerate(mod.load(edu).texts()):
            code = strip_comment(line).strip()
            word, _, rest = code.partition(" ")
            if word == "type":
                cur = rest.strip()
            elif word == "accent" and cur:
                x = rest.strip()
                if x not in defined:
                    out.append(("export_descr_unit.txt line %d: %s's accent %s is not in %s - the unit is silent in "
                                "battle" % (i + 1, cur, x, rel), True))
    return out
