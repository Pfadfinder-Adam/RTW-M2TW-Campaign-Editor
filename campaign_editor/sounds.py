"""Sounds of both games: the SND.PACK packs (data/sounds/*.idx + .dat), loose sound files, and the unit voices of
export_descr_sounds_units_voice.txt - which lines a unit says, hearing them and putting in one's own.

A pack's .idx: 'SND.PACK', u32 version (Rome 4, Medieval II 5), u32 count, u32 count2, u32 data size; then per
sound six u32 (offset in the .dat, size, rate, bits, channels, kind: 1 wav, 2 IMA ADPCM wav, 13 mp3), the name
('data/sounds/...'), a zero byte and three more bytes. The .dat holds whole wav / mp3 files.

The game compiles the sound texts into data/sounds/events.dat + events.idx; after the texts change those two are
removed (with a backup) so the game builds them again. A sound of our own is a loose file under a name no pack has
(Medieval II ships 1009 loose voice files that are in no pack and the texts name them)."""

import os
import re
import struct

from .moddata import _ci, ci_path

PACKS = ("Voice1", "Voice2", "Voice3", "SFX", "Music")
VOICE_FILE = "export_descr_sounds_units_voice.txt"
ACCENTS_FILE = "descr_sounds_accents.txt"
VOICE_FOLDER = "data/sounds/Voice/Human/Localized/Battle_Map"
NAME_CALL = "Unit_Select"           # the vocal that holds each unit's own name call ("Khan's Guard!")
KINDS = {1: "wav", 2: "wav (ADPCM)", 13: "mp3"}


class Sound:
    __slots__ = ("name", "dat", "offset", "size", "rate", "bits", "channels", "kind")

    def __init__(self, name, dat, offset, size, rate, bits, channels, kind):
        self.name, self.dat, self.offset, self.size = name, dat, offset, size
        self.rate, self.bits, self.channels, self.kind = rate, bits, channels, kind

    def read(self):
        with open(self.dat, "rb") as f:
            f.seek(self.offset)
            return f.read(self.size)


_PACK_CACHE = {}


def read_pack(idx):
    """[Sound] of one .idx (cached while the file is unchanged)."""
    stamp = os.path.getmtime(idx)
    got = _PACK_CACHE.get(idx)
    if got and got[0] == stamp:
        return got[1]
    with open(idx, "rb") as f:
        b = f.read()
    if b[:8] != b"SND.PACK":
        raise ValueError("%s is not a sound pack" % os.path.basename(idx))
    _ver, n = struct.unpack_from("<2I", b, 8)
    dat = idx[:-4] + (".dat" if idx.endswith(".idx") else ".DAT")
    dat = _ci(os.path.dirname(idx), os.path.basename(dat)) or dat
    pos, out = 24, []
    for _ in range(n):
        off, size, rate, bits, ch, kind = struct.unpack_from("<6I", b, pos)
        pos += 24
        end = b.index(b"\0", pos)
        out.append(Sound(b[pos:end].decode("latin-1"), dat, off, size, rate, bits, ch, kind))
        pos = end + 4
    _PACK_CACHE[idx] = (stamp, out)
    return out


def sound_dirs(mod):
    """The folders sounds come from: the mod's data/sounds, then the game's own (a mod folder often has none)."""
    out = []
    for data in (mod.data, _game_data(mod)):
        d = _ci(data, "sounds") if data else None
        if d and os.path.isdir(d) and d not in out:
            out.append(d)
    return out


def _game_data(mod):
    try:
        from .newmod import game_of
        d = os.path.join(game_of(mod.data), "data")
        return d if os.path.isdir(d) else None
    except Exception:
        return None


def pack_index(mod):
    """{lower 'data/sounds/...' name: Sound} of every pack the mod plays (its own first)."""
    out = {}
    for d in reversed(sound_dirs(mod)):
        for p in PACKS:
            idx = _ci(d, p + ".idx")
            if idx:
                try:
                    for s in read_pack(idx):
                        out[s.name.lower().replace("\\", "/")] = s
                except (OSError, ValueError, struct.error):
                    continue
    return out


def loose_path(mod, rel):
    """A loose sound file on disk for 'data/sounds/...' (the mod's, else the game's), or None."""
    rel = rel.replace("\\", "/")
    sub = rel[5:] if rel.lower().startswith("data/") else rel
    for data in (mod.data, _game_data(mod)):
        p = ci_path(data, sub) if data else None
        if p and os.path.isfile(p):
            return p
    return None


def find(mod, rel, index=None):
    """('file', path) | ('pack', Sound) | None - a loose file wins, as it does in the game."""
    p = loose_path(mod, rel)
    if p:
        return ("file", p)
    s = (index if index is not None else pack_index(mod)).get(rel.lower().replace("\\", "/"))
    return ("pack", s) if s else None


def sound_bytes(mod, rel, index=None):
    got = find(mod, rel, index)
    if not got:
        return None
    if got[0] == "file":
        with open(got[1], "rb") as f:
            return f.read()
    return got[1].read()


def wav_info(data):
    """(format, channels, rate, bits) of a wav, or None when it is no wav."""
    if len(data) < 36 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
        if cid == b"fmt " and size >= 16:
            fmt, ch, rate = struct.unpack_from("<HHI", data, pos + 8)
            bits = struct.unpack_from("<H", data, pos + 22)[0]
            return fmt, ch, rate, bits
        pos += 8 + size + (size & 1)
    return None


# ---------------------------------------------------------------------------
# export_descr_sounds_units_voice.txt
# ---------------------------------------------------------------------------
class VoiceEvent:
    """One 'event ... end' block: who says it (group = the accent or the cultures), the class (EDU voice_type),
    the vocal (an order: Group_Created, Unit_Select...), for Unit_Select the units / engines it names, its files."""

    def __init__(self, group, cls, vocal, target, names, head):
        self.group, self.cls, self.vocal = group, cls, vocal
        self.target, self.names = target, names    # 'unit' | 'engine' | None, [names]
        self.head = head                            # the unit/engine line, else the 'event' line
        self.event = None                           # the 'event' line
        self.end = None                             # the 'end' line
        self.files = []                             # ['data/sounds/.../x.wav']

    def says_for(self, unit):
        return self.target == "unit" and unit.lower() in (n.lower() for n in self.names)


def voice_file(mod):
    return _ci(mod.data, VOICE_FILE)


def voice_events(f):
    """[VoiceEvent] of a loaded export_descr_sounds_units_voice TextFile, in file order."""
    out = []
    group, cls, vocal, target, cur, folder = [], "", "", None, None, ""
    for i, line in enumerate(f.texts()):
        code = line.split(";", 1)[0].strip()
        if not code:
            continue
        word, _, rest = code.partition(" ")
        key = word.lower()
        rest = rest.strip()
        if cur is not None:
            if key == "end":
                cur.end = i
                out.append(cur)
                cur, target = None, None
            elif key == "folder":
                folder = rest.strip().rstrip("/\\")
            elif key == "group":
                continue
            elif code.lower().endswith((".wav", ".mp3")):
                cur.files.append((folder + "/" if folder else "") + code)
            continue
        if key in ("accent", "culture"):
            group = [x.strip() for x in rest.split(",") if x.strip()]
        elif key == "class":
            cls = rest
        elif key == "vocal":
            vocal = rest.split()[0] if rest else ""
        elif key in ("unit", "engine"):
            target = (key, [x.strip() for x in rest.split(",") if x.strip()], i)
        elif key == "event":
            if target:
                cur = VoiceEvent(group, cls, vocal, target[0], target[1], target[2])
            else:
                cur = VoiceEvent(group, cls, vocal, None, [], i)
            cur.event = i
            folder = ""
    return out


def accents(mod):
    """Medieval II: {faction: accent} from descr_sounds_accents.txt ({} on Rome / without the file)."""
    p = _ci(mod.data, ACCENTS_FILE)
    out = {}
    if not p:
        return out
    acc = None
    for line in mod.load(p).texts():
        code = line.split(";", 1)[0].strip()
        t = code.split(None, 1)
        if not t:
            continue
        if t[0].lower() == "accent" and len(t) > 1:
            acc = t[1].strip()
        elif t[0].lower() == "factions" and acc and len(t) > 1:
            for fac in t[1].replace(",", " ").split():
                out[fac] = acc
    return out


def voice_groups(mod, factions):
    """[(group key the voice file uses, [factions])] for the given owner factions: Medieval II's accent of each,
    Rome's culture. A faction the accents file does not name gets None."""
    acc = accents(mod)
    out = {}
    for fac in factions:
        if acc:
            key = acc.get(fac)
        else:
            try:
                key = mod.culture(fac)
            except Exception:
                key = None
        out.setdefault(key, []).append(fac)
    return list(out.items())


def _in_group(ev, key):
    return key is not None and key.lower() in (g.lower() for g in ev.group)


class UnitVoice:
    """What one group (accent / culture) makes a unit say: the orders of its class, and its own name call."""

    def __init__(self, key, factions, cls):
        self.key, self.factions, self.cls = key, factions, cls
        self.classes = []           # the classes this group has (what voice_type may be)
        self.orders = []            # [VoiceEvent] of the class without a unit / engine
        self.name_call = None       # the Unit_Select event naming the unit
        self.label = ""             # the group line's own spelling ('English', 'eastern,carthaginian,egyptian')

    @property
    def known_class(self):
        return self.cls.lower() in (c.lower() for c in self.classes)


def unit_voices(mod, events, unit, voice_type, factions):
    """[UnitVoice] for a unit (EDU type) of voice_type owned by factions, one per accent / culture."""
    out = []
    for key, facs in voice_groups(mod, factions):
        uv = UnitVoice(key, facs, voice_type)
        for ev in events:
            if not _in_group(ev, key):
                continue
            uv.label = uv.label or ",".join(ev.group)
            if ev.cls not in uv.classes:
                uv.classes.append(ev.cls)
            if ev.cls.lower() != voice_type.lower():
                continue
            if ev.target is None:
                uv.orders.append(ev)
            elif ev.says_for(unit) and uv.name_call is None:
                uv.name_call = ev
        out.append(uv)
    return out


def _slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "unit"


def new_sound_name(mod, prefix, index=None):
    """A loose file name under VOICE_FOLDER that no pack and no file has yet: <prefix>_1.wav, _2..."""
    index = index if index is not None else pack_index(mod)
    k = 1
    while True:
        name = "%s_%d.wav" % (prefix, k)
        rel = VOICE_FOLDER + "/" + name
        if rel.lower() not in index and not loose_path(mod, rel):
            return name
        k += 1


def _layout(f, events, key, cls):
    """How the voice file writes a Unit_Select block for this group and class: (indents, rome_style, after line)
    - taken from an existing block, so the new one reads like the file's own."""
    same = [ev for ev in events if _in_group(ev, key) and ev.cls.lower() == cls.lower() and ev.vocal == NAME_CALL]
    tmpl = next((ev for ev in same if ev.target), None)
    if tmpl is None:
        return None
    ind = lambda i: re.match(r"[ \t]*", f.text(i)).group(0)
    lines = range(tmpl.event + 1, tmpl.end)
    folder_i = next((i for i in lines if f.text(i).strip().lower().startswith("folder")), None)
    file_i = next((i for i in lines if f.text(i).strip().lower().endswith((".wav", ".mp3"))), None)
    group_i = next((i for i in lines if f.text(i).strip().lower() == "group"), None)
    folders = sum(1 for i in lines if f.text(i).strip().lower().startswith("folder"))
    return {"head": ind(tmpl.head), "event": ind(tmpl.event), "end": ind(tmpl.end),
            "folder": ind(folder_i) if folder_i is not None else ind(tmpl.event) + "\t",
            "file": ind(file_i) if file_i is not None else ind(tmpl.event) + "\t",
            "group": ind(group_i) if group_i is not None else None,
            "folder_each": folders > 1,
            "after": max(ev.end for ev in same)}


def _block(lay, unit, names):
    out = [lay["head"] + "unit " + unit, lay["event"] + "event"]
    for n, name in enumerate(names):
        if n == 0 or lay["folder_each"]:
            out.append(lay["folder"] + "folder " + VOICE_FOLDER)
        out.append(lay["file"] + name)
    if lay["group"] is not None:
        out.append(lay["group"] + "group")
    out.append(lay["end"] + "end")
    return out


def set_name_call(plan, unit, key, cls, sounds):
    """Make the unit's name call for one accent / culture (key) and class the given sound files (paths of .wav on
    disk): each is copied in as a new loose file, the voice file gets the unit its own Unit_Select block (the unit
    is taken out of a line it shares with others; a unit without one gets a new block), and events.dat / .idx are
    removed so the game builds them from the texts again. Returns the new 'data/sounds/...' names."""
    mod = plan.mod
    path = voice_file(mod)
    if not path:
        raise ValueError("this mod has no %s - the game has no unit voices to change here" % VOICE_FILE)
    if not sounds:
        raise ValueError("pick at least one .wav file")
    f = plan.edit(path)
    events = voice_events(f)
    lay = _layout(f, events, key, cls)
    if lay is None:
        raise ValueError("the voice file has no '%s' names for %s class %s - pick another voice class "
                         "(the unit's voice_type line)" % (NAME_CALL, key, cls))
    index = pack_index(mod)
    prefix = "%s_%s_name_%s_custom" % (_slug(key).title(), cls, _slug(unit))
    names, taken = [], set()
    for src in sounds:
        with open(src, "rb") as fh:
            data = fh.read()
        info = wav_info(data)
        if info is None:
            raise ValueError("%s is not a .wav file - the game's voices are wav (save it as wav first)"
                             % os.path.basename(src))
        name = new_sound_name(mod, prefix, index)
        while name.lower() in taken:
            index[(VOICE_FOLDER + "/" + name).lower()] = None
            name = new_sound_name(mod, prefix, index)
        taken.add(name.lower())
        index[(VOICE_FOLDER + "/" + name).lower()] = None
        dst = os.path.join(mod.data, *VOICE_FOLDER[5:].split("/"), name)
        folder = ci_path(mod.data, VOICE_FOLDER[5:])
        if folder and os.path.isdir(folder):
            dst = os.path.join(folder, name)
        plan.binary(dst, data)
        plan.note(None, "new sound %s (from %s)" % (mod.rel(dst), os.path.basename(src)))
        fmt, ch, rate, bits = info
        if (ch, rate, bits) != (1, 22050, 16) and fmt == 1:
            plan.warn(None, "%s is %d Hz, %d-bit, %s - the game's own voices are 22050 Hz, 16-bit, mono; it may "
                            "sound off in the game" % (os.path.basename(src), rate, bits,
                                                       "mono" if ch == 1 else "%d channels" % ch))
        names.append(name)
    old = next((ev for ev in events if _in_group(ev, key) and ev.cls.lower() == cls.lower() and ev.says_for(unit)),
               None)
    new = _block(lay, unit, names)
    if old is not None and len(old.names) == 1:
        f.delete(old.head, old.end + 1)
        f.insert(old.head, new)
        plan.note(f, "%s, class %s: the name call of %s now plays %s" % (key, cls, unit, ", ".join(names)))
    else:
        at = lay["after"] + 1
        if old is not None:
            rest = [n for n in old.names if n.lower() != unit.lower()]
            head = f.text(old.head)
            word = re.match(r"([ \t]*unit)\s", head).group(1)
            sep = ", " if ", " in head else ","
            f.set(old.head, word + " " + sep.join(rest))
            at = old.end + 1
            plan.note(f, "%s, class %s: %s taken out of the line it shared with %s" % (
                key, cls, unit, ", ".join(rest[:3]) + (" ..." if len(rest) > 3 else "")))
        f.insert(at, new)
        plan.note(f, "%s, class %s: %s gets its own name call: %s" % (key, cls, unit, ", ".join(names)))
    rebuild_events(plan)
    return [VOICE_FOLDER + "/" + n for n in names]


def rebuild_events(plan):
    """Remove the mod's events.dat / events.idx (backed up) so the game builds them from the changed texts."""
    d = _ci(plan.mod.data, "sounds")
    found = False
    for n in ("events.dat", "events.idx"):
        p = _ci(d, n) if d else None
        if p:
            plan.delete(p, "the game builds it again from the sound texts on the next start")
            found = True
    if not found:
        plan.note(None, "this mod has no data/sounds/events.dat of its own; if the game still says the old "
                        "line, remove the game's data/sounds/events.dat and events.idx (keep a copy) and start again")


def play(data, name="sound.wav"):
    """Play a sound: Windows plays wav itself (mp3 goes to the default player); elsewhere a player program if one
    is there. Returns None, or a plain message why nothing plays."""
    import tempfile
    import sys
    tmp = os.path.join(tempfile.gettempdir(), "campaign_editor_sound" + os.path.splitext(name)[1].lower())
    with open(tmp, "wb") as f:
        f.write(data)
    if sys.platform.startswith("win"):
        if tmp.endswith(".wav"):
            import winsound
            winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            os.startfile(tmp)
        return None
    import shutil
    import subprocess
    for prog in ("paplay", "aplay", "afplay", "ffplay"):
        exe = shutil.which(prog)
        if exe:
            args = [exe, "-nodisp", "-autoexit", tmp] if prog == "ffplay" else [exe, tmp]
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return None
    return "no sound player here - the file is saved as %s" % tmp


def stop():
    import sys
    if sys.platform.startswith("win"):
        import winsound
        winsound.PlaySound(None, 0)
