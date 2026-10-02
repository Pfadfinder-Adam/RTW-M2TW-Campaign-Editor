"""The string tables the game reads (the texts players see), both games: one place to read and write them.

A table is data/text[/english]/<name>.txt ({KEY} text; a text runs on over lines until the next {KEY} or a comment
line), or Medieval II's compiled data/text/<name>.txt.strings.bin: u16 2, u16 2048, u32 count, then per entry a
u16-counted UTF-16 key and a u16-counted UTF-16 text. The .txt is read when both lie there.
A text written where only the .bin lies goes into a .txt made from the .bin; the .bin is never removed on our own
(that the game builds it again from the .txt is not checked in the game) - Preview says to remove it if the game
shows the old text."""

import os
import re
import struct

_cache = {}


def read_strings_bin(data):
    """{key: text} of a Medieval II .strings.bin."""
    out = {}
    if len(data) < 8:
        return out
    count = struct.unpack_from("<I", data, 4)[0]
    p = 8
    for _ in range(count):
        texts = []
        for _ in range(2):
            if p + 2 > len(data):
                return out
            n = struct.unpack_from("<H", data, p)[0]
            p += 2
            texts.append(data[p:p + 2 * n].decode("utf-16-le", "replace"))
            p += 2 * n
        out[texts[0]] = texts[1]
    return out


def strings(mod, name):
    """{KEY upper: text} of a string table (name like 'export_VnVs.txt'): the .txt the game reads, else its
    .strings.bin; {} when neither is there. Cached by the files' times."""
    txt = mod.text_file(name)
    binp = None
    if not txt:
        for folder in mod.text_dirs():
            for n in os.listdir(folder):
                if n.lower() == name.lower() + ".strings.bin":
                    binp = os.path.join(folder, n)
                    break
            if binp:
                break
    path = txt or binp
    if not path:
        return {}
    key = (path, os.path.getmtime(path))
    if key in _cache:
        return _cache[key]
    out = {}
    if txt:
        # a text runs on until the next {KEY} or comment line (the tables' own way: a description often starts
        # on the line under its key)
        key, parts = None, []

        def done():
            if key is not None:
                while parts and not parts[-1].strip():
                    parts.pop()
                out.setdefault(key, "\n".join(p.strip() for p in parts).strip())
        for line in mod.load(txt).texts():
            s = line.lstrip()
            m = re.match(r"\{([^}]+)\}(.*)$", s)
            if m:
                done()
                key, parts = m.group(1).upper(), [m.group(2)]
            elif s.startswith("\u00ac"):
                done()
                key, parts = None, []
            elif key is not None:
                parts.append(line)
        done()
    else:
        with open(binp, "rb") as fh:
            out = {k.upper(): v for k, v in read_strings_bin(fh.read()).items()}
    _cache[key] = out
    return out


def shown(table, key):
    """The text players see for a key, else the key made readable (Promising_Defender -> Promising Defender)."""
    got = table.get((key or "").upper())
    return got if got else (key or "").replace("_", " ")


def write_texts(plan, name, values):
    """{KEY: text} into the string table `name` (export_VnVs.txt ...): the .txt when there is one, else a .txt made
    from Medieval II's compiled .strings.bin; a .strings.bin beside it is removed (the game builds it again)."""
    from .editors import set_text_values
    values = {k: v for k, v in (values or {}).items() if v is not None}
    if not values:
        return
    mod = plan.mod
    txt = mod.text_file(name)
    binp = None
    for folder in mod.text_dirs():
        for n in os.listdir(folder):
            if n.lower() == name.lower() + ".strings.bin":
                binp = binp or os.path.join(folder, n)
    if txt:
        set_text_values(plan, txt, values)
    elif binp:
        with open(binp, "rb") as fh:
            entries = read_strings_bin(fh.read())
        low = {k.lower(): k for k in entries}
        for k, v in values.items():
            entries[low.get(k.lower(), k)] = v
        lines = ["¬ made from %s by the editor (the game builds the .strings.bin again from this file)"
                 % os.path.basename(binp)]
        lines += ["{%s}\t%s" % (k, v.replace("\r\n", "\n").replace("\n", "\r\n")) for k, v in entries.items()]
        path = binp[:-len(".strings.bin")]
        plan.binary(path, b"\xff\xfe" + "\r\n".join(lines + [""]).encode("utf-16-le"))
        plan.notes.append((mod.rel(path), "made from the compiled %s with %d text(s) changed or added" % (
            os.path.basename(binp), len(values))))
    else:
        plan.warn(None, "no %s in data/text - the new texts are not written (the game shows the keys)" % name)
        return
    if binp:        # not removed on our own: that the game builds it again is not checked in the game yet
        plan.warn(None, "Medieval II keeps %s also compiled (%s): if the game shows the old text or a key, remove "
                        "that .strings.bin so it is built again from the .txt" % (name, mod.rel(binp)))
