"""Checking a mod pack (a .zip or a folder that says "copy data over the game") before it goes in, then putting in
only what the user picks - with a Plan: Preview, a backup, Restore.

For every file of the pack's data folder:
  new        not in the mod: goes in
  same       the mod has it byte for byte: nothing to do
  replaces   the mod has another one - then, what would be lost:
    - a file of REX's own (the REX manifest; REX's copy is what the mod has now);
    - a picture of another size than the one it replaces; for a sprite page (a page of a ui/*.sd.xml), the sprites
      that would lie outside it (the Aquila Rubra card pack brought the original game's battlepage_03.tga, 141 x 36,
      over REX's 141 x 106 - the schiltrom / shield wall buttons below row 36 lost their pictures);
    - a text file: how many lines differ; one that differs in a few lines can go in as "only its changes" (the
      pack's changed and added lines taken, lines it would drop kept - REX's distance_visibility lines stay); one
      that differs in most lines is another mod's whole file (the pack's export_descr_unit.txt over HLR's).
Choices: 'install', 'keep' (the mod's own stays), 'merge' (text only: only its changes)."""

import difflib
import os
import struct
import zipfile

from .moddata import _ci
from .textio import TextFile

TEXT_EXT = (".txt", ".xml", ".json", ".cfg", ".nut", ".lua", ".csv", ".ini")
PICTURE_EXT = (".tga", ".dds", ".texture", ".png", ".bmp", ".jpg")
MERGE_SHARE = 0.2            # a text differing in at most this share of lines is offered as "only its changes"


# ---------------------------------------------------------------------------
# Reading a pack
# ---------------------------------------------------------------------------
def _data_prefix(names):
    """The folder inside the pack that stands for data/ ('data/', 'MyMod/data/'), '' when the pack's files are
    data's own folders (ui/, text/...), None when nothing looks like game data."""
    best = None
    for n in names:
        low = n.lower()
        at = low.find("data/")
        if at >= 0 and (at == 0 or low[at - 1] == "/"):
            p = n[:at + 5]
            if best is None or len(p) < len(best):
                best = p
    if best is not None:
        return best
    tops = {n.split("/")[0].lower() for n in names if "/" in n}
    if tops & {"ui", "text", "world", "models", "models_unit", "unit_models", "banners", "sounds", "loading_screen"}:
        return ""
    return None


def read(path):
    """(files {data-relative path: bytes}, left_out [paths outside data/ - readmes]) of a .zip or a folder."""
    raw = {}
    if os.path.isdir(path):
        for root, _, fs in os.walk(path):
            for f in fs:
                p = os.path.join(root, f)
                with open(p, "rb") as fh:
                    raw[os.path.relpath(p, path).replace("\\", "/")] = fh.read()
    else:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                raw[info.filename.replace("\\", "/")] = z.read(info)
    prefix = _data_prefix(list(raw))
    if prefix is None:
        raise ValueError("no data folder in this pack (and nothing that looks like one: ui/, text/, world/...)")
    files, left = {}, []
    for n, data in raw.items():
        if n.startswith(prefix) and len(n) > len(prefix):
            files[n[len(prefix):]] = data
        else:
            left.append(n)
    return files, sorted(left)


# ---------------------------------------------------------------------------
# What each file would do
# ---------------------------------------------------------------------------
def picture_size(data, name=""):
    """(width, height) of a TGA / DDS / Medieval II .texture / PNG / BMP picture, or None."""
    try:
        if name.lower().endswith(".texture") and data[48:52] == b"DDS ":
            data = data[48:]
        if data[:4] == b"DDS ":
            h, w = struct.unpack("<II", data[12:20])
            return w, h
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", data[16:24])
        if data[:2] == b"BM":
            w, h = struct.unpack("<ii", data[18:26])
            return w, abs(h)
        if name.lower().endswith(".tga") and len(data) >= 18:
            return struct.unpack("<HH", data[12:16])
    except struct.error:
        return None
    return None


def _game_root(mod):
    try:
        from .newmod import game_of
        return game_of(mod.data)
    except Exception:
        return None


def _rex_entry(mod, target):
    """REX manifest entry [size, md5] for the file the target stands for, or None."""
    from .scan import _load_manifest, reference_dir
    rex = _load_manifest(os.path.join(reference_dir(), "rex_manifest.json.gz")) or {}
    game = _game_root(mod)
    keys = []
    if game:
        keys.append(os.path.relpath(target, game).replace("\\", "/").lower())
    keys.append(("data/" + os.path.relpath(target, mod.data).replace("\\", "/")).lower())
    return next((rex[k] for k in keys if k in rex), None)


def _sprite_sheets(mod):
    """[(sheet name, text)] of the ui/*.sd.xml sprite sheets the mod reads (its own, else the game's)."""
    out, seen = [], set()
    game = _game_root(mod)
    for data in (mod.data, os.path.join(game, "data") if game else None):
        ui = _ci(data, "ui") if data and os.path.isdir(data) else None
        if not ui:
            continue
        for n in sorted(os.listdir(ui)):
            if n.lower().endswith(".sd.xml") and n.lower() not in seen:
                seen.add(n.lower())
                with open(os.path.join(ui, n), "rb") as fh:
                    out.append((n, fh.read().decode("latin-1")))
    return out


def sprites_outside(mod, rel, size):
    """[(sheet, sprite)] of sprite pages named like rel's file whose sprites would not fit a picture of size."""
    from .symbols import RE_PAGE, RE_SPRITE
    base = rel.split("/")[-1].lower()
    out = []
    for sheet, text in _sprite_sheets(mod):
        for m in RE_PAGE.finditer(text):
            if m.group(1).lower() != base:
                continue
            for s in RE_SPRITE.finditer(m.group(2)):
                x, y, w, h = (int(v) for v in s.groups()[1:])
                if x + w > size[0] or y + h > size[1]:
                    out.append((sheet, s.group(1)))
    return out


def _lines(data):
    return TextFile.from_bytes("", data).texts()


def merge_lines(mine, theirs):
    """The mod's lines with the pack's changes taken - changed and added lines - and lines the pack would drop kept.
    (merged, {'changed', 'added', 'kept'}) - counts of lines."""
    sm = difflib.SequenceMatcher(None, mine, theirs, autojunk=False)
    out, stats = [], {"changed": 0, "added": 0, "kept": 0}
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            out += mine[a1:a2]
        elif op == "insert":
            out += theirs[b1:b2]
            stats["added"] += b2 - b1
        elif op == "delete":
            out += mine[a1:a2]
            stats["kept"] += a2 - a1
        else:                                    # replace: the pack's lines, the mod's extra ones kept
            out += theirs[b1:b2]
            stats["changed"] += min(a2 - a1, b2 - b1)
            if a2 - a1 > b2 - b1:
                out += mine[a1 + (b2 - b1):a2]
                stats["kept"] += (a2 - a1) - (b2 - b1)
            else:
                stats["added"] += (b2 - b1) - (a2 - a1)
    return out, stats


def check(mod, files):
    """[{'rel', 'target', 'state': new|same|replaces, 'kind': text|picture|file, 'notes': [(serious, text)],
    'choice': install|keep|merge|skip, 'merge': stats or None}] - one per file of the pack, sorted by path."""
    out = []
    for rel in sorted(files, key=str.lower):
        data = files[rel]
        target = mod.find(rel) or os.path.join(mod.data, *rel.split("/"))
        low = rel.lower()
        kind = "text" if low.endswith(TEXT_EXT) else ("picture" if low.endswith(PICTURE_EXT) else "file")
        e = {"rel": rel, "target": target, "kind": kind, "notes": [], "merge": None}
        if not os.path.isfile(target):
            e.update(state="new", choice="install")
            out.append(e)
            continue
        with open(target, "rb") as fh:
            now = fh.read()
        if now == data:
            e.update(state="same", choice="skip")
            out.append(e)
            continue
        e.update(state="replaces", choice="install")
        rex = _rex_entry(mod, target)
        if rex:
            import hashlib
            if rex[0] == len(now) and hashlib.md5(now).hexdigest() == rex[1]:
                e["notes"].append((True, "REX's own file - the pack's copy is not REX's, REX's changes would be lost"))
            else:
                e["notes"].append((False, "REX has its own version of this file"))
        if kind == "picture":
            a, b = picture_size(now, rel), picture_size(data, rel)
            if a and b and a != b:
                out_sprites = sprites_outside(mod, rel, b)
                if out_sprites:
                    names = sorted({s for _, s in out_sprites})
                    e["notes"].append((True, "a sprite page: %d x %d over %d x %d leaves %d sprite(s) of %s outside "
                                             "it (%s%s)" % (b[0], b[1], a[0], a[1], len(names),
                                                            out_sprites[0][0], ", ".join(names[:3]),
                                                            " ..." if len(names) > 3 else "")))
                else:
                    e["notes"].append((True, "%d x %d over a %d x %d picture - another size than the game uses here"
                                       % (b[0], b[1], a[0], a[1])))
        elif kind == "text":
            mine, theirs = _lines(now), _lines(data)
            merged, stats = merge_lines(mine, theirs)
            differ = stats["changed"] + stats["added"] + stats["kept"]
            share = differ / float(max(len(mine), 1))
            e["merge"] = stats
            if share <= MERGE_SHARE:
                e["notes"].append((False, "differs in %d line(s): %d changed, %d added%s" % (
                    differ, stats["changed"], stats["added"],
                    ", %d of this mod's line(s) it would drop (kept with 'only its changes')" % stats["kept"]
                    if stats["kept"] else "")))
            else:
                e["notes"].append((True, "another file: %d of %d lines differ - it would replace this mod's own "
                                         "content" % (differ, len(mine))))
        serious = any(s for s, _ in e["notes"])
        if kind == "text" and e["merge"] is not None:
            share_ok = not any(s and t.startswith("another file") for s, t in e["notes"])
            e["choice"] = "merge" if share_ok else "keep"
        elif serious:
            e["choice"] = "keep"
        out.append(e)
    return out


# ---------------------------------------------------------------------------
# Putting it in
# ---------------------------------------------------------------------------
def install(plan, files, entries):
    """The entries' choices written through plan (every write backed up; new files removed by Restore)."""
    mod = plan.mod
    n = {"install": 0, "merge": 0}
    for e in entries:
        c = e.get("choice")
        if c == "install":
            if e["state"] == "same":
                continue
            plan.binary(e["target"], files[e["rel"]])
            plan.notes.append((mod.rel(e["target"]), "from the pack (%s)" % ("new" if e["state"] == "new" else
                                                                               "replaces this mod's")))
            n["install"] += 1
        elif c == "merge" and e["kind"] == "text" and e["state"] == "replaces":
            f = plan.edit(e["target"])
            mine = f.texts()
            theirs = _lines(files[e["rel"]])
            sm = difflib.SequenceMatcher(None, mine, theirs, autojunk=False)
            raw = []
            for op, a1, a2, b1, b2 in sm.get_opcodes():   # the mod's own lines stay byte for byte
                if op in ("equal", "delete"):
                    raw += f.raw[a1:a2]
                elif op == "insert":
                    raw += [f.make(x) for x in theirs[b1:b2]]
                else:
                    raw += [f.make(x) for x in theirs[b1:b2]]
                    if a2 - a1 > b2 - b1:
                        raw += f.raw[a1 + (b2 - b1):a2]
            tail = f.raw[len(mine):]                       # the file's last (empty) piece after its final newline
            f.raw = raw + tail
            st = e.get("merge") or {}
            plan.note(f, "only the pack's changes: %d line(s) changed, %d added, %d kept that it would drop" % (
                st.get("changed", 0), st.get("added", 0), st.get("kept", 0)))
            n["merge"] += 1
    if not n["install"] and not n["merge"]:
        plan.warn(None, "nothing picked to go in")
    for e in entries:
        for serious, text in e["notes"]:
            if serious and e.get("choice") == "install":
                plan.warn(None, "%s: %s" % (e["rel"], text))
    return n


__all__ = ["read", "check", "install", "merge_lines", "picture_size", "sprites_outside"]
