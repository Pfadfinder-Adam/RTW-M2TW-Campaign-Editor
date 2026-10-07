"""A Plan collects every edit in memory, can report and validate it, and writes
it to disk with a backup that restore() undoes."""

import datetime
import json
import time
import os
import shutil

from .textio import TextFile, WriteError, make_writable, plain, readonly, refused, remove_file, replace_file

BACKUP_DIR = "CampaignEditor_backups"
OLD_BACKUP_DIR = "faction_tool_backups"           # up to 0.28: still listed, Restore works on both
BACKUP_DIRS = (BACKUP_DIR, OLD_BACKUP_DIR)


# listeners told of every finished write: fn(backup folder, the plan) - the window's 'Undo this write' button
WRITTEN = []

class Plan:
    def __init__(self, mod, template, new, opts=None):
        self.mod = mod
        self.template = template
        self.new = new
        self.opts = opts or {}
        self.files = {}          # path -> edited TextFile
        self.binaries = {}       # path -> new bytes (pictures such as map_regions.tga)
        self.deletions = []      # paths removed (map.rwm, which the game rebuilds)
        self.originals = {}      # path -> original bytes
        self.copies = []         # (src, dst) files or folders to copy
        self.notes = []          # (rel path or "", message)
        self.warnings = []
        self.faction_count = None

    # ---- building ----
    def edit(self, path):
        if path not in self.files:
            f = TextFile.load(path)
            self.originals[path] = f.dump()
            self.files[path] = f
        return self.files[path]

    def name_pool(self, faction):
        """The faction's name pools as this plan leaves descr_names.txt (a name list written in this
        run counts at once: the leader, captains and records get names of the faction's own list)."""
        from .moddata import pool_in
        path = self.mod.file("names")
        if path in self.files:
            return pool_in(self.files[path].texts(), faction)
        return self.mod.name_pool(faction)

    def copy(self, src, dst):
        self.copies.append((src, dst))
        self.note(None, "copy %s -> %s" % (self.mod.rel(src), self.mod.rel(dst)))

    def note(self, f, msg):
        self.notes.append((self.mod.rel(f.path) if f is not None else "", msg))

    def warn(self, f, msg):
        self.warnings.append((self.mod.rel(f.path) if f is not None else "", msg))

    def binary(self, path, data):
        """A whole new content for a (binary) file, backed up like any edit."""
        self.binaries[path] = data

    def patch_tga(self, path, changes):
        """Pixels of a TGA changed on top of what this plan already changed in it (painted regions and a moved
        town in one write: the second must not start again from the file and lose the first)."""
        from .tga import patched
        self.binary(path, patched(path, changes, self.binaries.get(path)))

    def delete(self, path, why):
        if os.path.exists(path) and path not in self.deletions:
            self.deletions.append(path)
            self.notes.append((self.mod.rel(path), "removed - %s" % why))

    def changed_files(self):
        return [p for p, f in self.files.items() if f.dump() != self.originals[p]] + \
            [p for p, d in self.binaries.items() if not os.path.exists(p) or _read(p) != d] + \
            list(self.deletions)

    # ---- display names for the string tables ----
    def display_replacements(self):
        """[(old, new)] used to rewrite copied strings, longest first, with UPPER forms."""
        pairs = []
        for key in ("display_name", "short_name", "adjective"):
            old = self.opts.get("template_" + key)
            nw = self.opts.get(key)
            if old and nw:
                if key == "display_name" and not self.opts.get("template_short_name"):
                    # a game without short names (Medieval II: {SICILY}Sicily): the texts use the name inside
                    # phrases ("the Kingdom of Sicily", "de Sicily") - there the new faction's short name (or
                    # the end of 'Kingdom of Jerusalem') fits, the full name only where the whole phrase stood
                    core = (self.opts.get("short_name") or nw.split(" of ")[-1]).strip() or nw
                    if core != nw:
                        lead = nw[:len(nw) - len(nw.split(" of ")[-1])] if " of " in nw else ""
                        if lead:
                            pairs.append((lead + old, nw))
                        nw = core
                pairs.append((old, nw))
        out = []
        for old, nw in pairs:
            out.append((old, nw))
            if old.upper() != old:
                out.append((old.upper(), nw.upper()))
        # plural forms ("Parthians") ride along with the adjective/short name prefix
        out.sort(key=lambda p: -len(p[0]))
        return out

    # ---- report ----
    def report(self):
        lines = []
        by = {}
        for rel, msg in self.notes:
            by.setdefault(rel, []).append(msg)
        for rel in sorted(by):
            lines.append(rel or "(files)")
            for msg in by[rel]:
                lines.append("    " + msg)
        warnings = list(self.warnings)
        ro = self.readonly_note()
        if ro:
            warnings.append(("", ro))
        if warnings:
            lines.append("")
            lines.append("WARNINGS")
            for rel, msg in warnings:
                lines.append("    %s%s" % (rel + ": " if rel else "", msg))
        return "\n".join(lines)

    def readonly_note(self):
        """Plain words for the files this run changes that carry the read-only mark (Apply takes it off to write
        them), or ''."""
        ro = [self.mod.rel(p) for p in self.changed_files() if readonly(p)]
        if not ro:
            return ""
        return ("%d file(s) are marked read-only (Windows' Read-only box): Apply takes the mark off to write them - "
                "%s" % (len(ro), ", ".join(ro[:8]) + (" ..." if len(ro) > 8 else "")))

    # ---- disk ----
    def apply(self):
        from .limits import keep_up
        keep_up(self)                       # REX / M2EX: max_factions follows the factions, silently (limits.py)
        sm = self.mod.file("sm_factions")
        if sm and sm in self.files:         # Rome: a 'faction destroyed' picture for every faction (eventimages.py)
            from . import eventimages
            eventimages.keep_up(self)
        # every path this run touches lies in the mod's or its game's folder (guard.py) - checked before anything
        from . import guard
        guard.check(list(self.changed_files()) + [dst for _, dst in self.copies], guard.roots_of(self.mod))
        root = os.path.dirname(self.mod.data)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(root, BACKUP_DIR, "%s_%s" % (stamp, self.new))
        k = 1
        while os.path.exists(bdir) or os.path.exists(bdir + "_restored"):   # two writes in one second
            k += 1
            bdir = os.path.join(root, BACKUP_DIR, "%s_%s_%d" % (stamp, self.new, k))
        # copied_from {created: its source}: what a copied picture was before it was replaced (Art's
        # "Back to the original"); Restore does not need it
        # made: when, to the nanosecond - two writes in one second keep their order for Restore (a file's own
        # time is too coarse on Windows to tell them apart)
        manifest = {"faction": self.new, "template": self.template, "modified": [], "created": [], "copied_from": {},
                    "made": time.time_ns()}
        created = []
        changed = self.changed_files()
        dst = bdir
        try:
            os.makedirs(bdir)
            for path in changed:
                rel = os.path.relpath(path, root)
                if path not in self.originals and not os.path.exists(path):
                    created.append(rel.replace("\\", "/"))     # a new picture: Restore removes it
                    continue
                dst = os.path.join(bdir, stored(rel))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if path in self.originals:
                    with open(dst, "wb") as out:
                        out.write(self.originals[path])
                else:                               # a picture or a removed file: back up what is on disk
                    shutil.copy2(path, dst)
                manifest["modified"].append(rel.replace("\\", "/"))
        except OSError as e:                        # the backup itself could not be made: no rights, disk full...
            shutil.rmtree(bdir, ignore_errors=True)
            if os.path.isdir(os.path.dirname(bdir)) and not os.listdir(os.path.dirname(bdir)):
                os.rmdir(os.path.dirname(bdir))
            raise WriteError("%s\n\nNothing was changed: the backup is made before any file is written, and it "
                             "could not be made." % (plain(dst, e) or "%s: %s" % (type(e).__name__, e))) from e
        made, done = [], []
        try:
            for src, dst in self.copies:
                if os.path.exists(dst):
                    continue
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                except PermissionError as e:
                    raise WriteError(refused(dst, e)) from e
                made.append(dst)
                created.append(os.path.relpath(dst, root).replace("\\", "/"))
                if not os.path.isdir(src):
                    manifest["copied_from"][created[-1]] = os.path.relpath(src, root).replace("\\", "/")
            manifest["created"] = created
            with open(os.path.join(bdir, "manifest.json"), "w", encoding="utf-8") as out:
                json.dump(manifest, out, indent=2)
            for path in changed:
                if path in self.files:
                    self.files[path].save(path)
                elif path in self.binaries:
                    replace_file(path, self.binaries[path])      # never write through a hard link
                elif path in self.deletions:
                    remove_file(path)
                done.append(path)
        except Exception as e:
            # one file refused (read-only, held by the game...): the files written before it go back, so the mod
            # is never left half changed - all of this run or none of it
            left = _roll_back(root, bdir, manifest, done, made)
            why = str(e) if isinstance(e, WriteError) else \
                (isinstance(e, OSError) and plain(getattr(e, "filename", None) or root, e)) or \
                "%s: %s" % (type(e).__name__, e)
            if left:
                raise WriteError("%s\n\n%d file(s) written before it could not be put back (%s) - use Restore on "
                                 "the backup %s." % (why, len(left), ", ".join(left[:5]), bdir)) from e
            raise WriteError("%s\n\nNothing was changed: %s" % (
                why, "the %d file(s) written before it were put back." % (len(done) + len(made))
                if done or made else "no file had been written yet.")) from e
        for fn in list(WRITTEN):                    # the window offers 'Undo this write' (gui.App._written)
            try:
                fn(bdir, self)
            except Exception:
                pass
        return bdir


def _roll_back(root, bdir, manifest, done, made):
    """Undo a write that stopped half way: the files written so far back from the backup, the copies removed, the
    backup itself dropped when all went back. -> [what could not be put back]."""
    left = []
    modified = set(manifest.get("modified", []))
    for path in reversed(done):
        rel = os.path.relpath(path, root).replace("\\", "/")
        try:
            if rel in modified:
                if os.path.exists(path):
                    remove_file(path)
                shutil.copy2(os.path.join(bdir, stored(rel)), path)
            elif os.path.exists(path):
                remove_file(path)
        except Exception:
            left.append(rel)
    for dst in reversed(made):
        try:
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            elif os.path.exists(dst):
                remove_file(dst)
        except Exception:
            left.append(os.path.relpath(dst, root).replace("\\", "/"))
    if not left:
        try:                                     # a backup of a read-only file is read-only too
            shutil.rmtree(bdir, onerror=lambda fn, p, exc: (make_writable(p), fn(p)) if os.path.exists(p) else None)
        except OSError:
            pass                                 # an empty-handed backup left behind: harmless
    return left


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def backups(mod):
    """Every backup of the mod, newest first - in CampaignEditor_backups and in older versions' faction_tool_backups."""
    out = []
    for name in BACKUP_DIRS:
        root = os.path.join(os.path.dirname(mod.data), name)
        if not os.path.isdir(root):
            continue
        for n in os.listdir(root):
            m = os.path.join(root, n, "manifest.json")
            if os.path.isfile(m) and not n.endswith("_restored"):
                try:
                    with open(m, encoding="utf-8") as fh:
                        made = json.load(fh).get("made")
                except (OSError, ValueError):
                    made = None
                out.append((n[:15], made or int(os.path.getmtime(m) * 1e9), os.path.join(root, n)))
    # newest first; two runs in one second (terrain + faction by one Apply) by when they were made (older
    # backups without it: the time their manifest was written), not by name
    return [p for _, _, p in sorted(out, reverse=True)]


def backup_label(bdir):
    """A backup as a person reads it: '2026-09-29 14:03:12  epirus (from macedon)  - 12 files'."""
    n = os.path.basename(bdir)
    when = n[:15]
    try:
        when = datetime.datetime.strptime(n[:15], "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    try:
        with open(os.path.join(bdir, "manifest.json"), encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return "%s  %s" % (when, n[16:])
    if not isinstance(m, dict):                   # another version's record
        return "%s  %s" % (when, n[16:])
    what = m.get("faction") or n[16:]
    if m.get("template") and m.get("template") != what:
        what += " (from %s)" % m["template"]
    k = sum(len(m.get(x)) for x in ("modified", "created") if isinstance(m.get(x), list))
    return "%s  %s  - %d file%s" % (when, what, k, "" if k == 1 else "s")


def stored(rel):
    """Where a backup keeps its copy of a file, inside the backup's folder: the file's path from the mod's folder,
    each '..' (a file of the game's folder beside the mod - an add-on in the game's script/modules) kept as '_up'.
    Before, '../script/modules/x.nut' was copied OUT of the backup's folder and Restore refused it."""
    return os.path.join(*["_up" if x == ".." else x for x in rel.replace("\\", "/").split("/")])


def _copy_of(bdir, rel):
    """The backup's copy of rel: stored(rel); a backup of an older version kept a '..' file outside its folder,
    within the backups folder (CampaignEditor_backups/script/modules/x.nut) - read from there."""
    p = os.path.join(bdir, stored(rel))
    if os.path.exists(p) or ".." not in rel.replace("\\", "/").split("/"):
        return p
    return os.path.normpath(os.path.join(bdir, rel))


def restore_to(mod, bdir):
    """Undo bdir and every newer backup, newest first (backups undo each other in
    order), so the files are as they were before bdir's run. Returns the manifests."""
    order = backups(mod)
    norm = [os.path.normcase(os.path.abspath(b)) for b in order]
    key = os.path.normcase(os.path.abspath(bdir))
    if key not in norm:
        raise ValueError("no such backup: %s" % bdir)
    todo = order[:norm.index(key) + 1]
    for b in todo:                       # every record read first: one this version cannot read stops it all
        read_manifest(b)
    return [restore(mod, b) for b in todo]


def read_manifest(bdir):
    """A backup's record ({'modified': [...], 'created': [...], ...}); ValueError in plain words when it is not one
    this version reads (made by another version of the editor)."""
    with open(os.path.join(bdir, "manifest.json"), encoding="utf-8") as f:
        try:
            manifest = json.load(f)
        except ValueError:
            manifest = None
    if not (isinstance(manifest, dict) and all(isinstance(manifest.get(k), list) and all(
            isinstance(x, str) for x in manifest[k]) for k in ("modified", "created"))):
        raise ValueError("%s was made by another version of the editor and keeps its list of files in a form this "
                         "version does not read - restore it with that version. Nothing was changed."
                         % os.path.basename(bdir))
    return manifest


def restore(mod, bdir):
    """Put every file of a backup back and remove what that run created."""
    root = os.path.dirname(mod.data)
    manifest = read_manifest(bdir)
    # a backup names its files relative to the mod's folder; one that points outside it (a crafted manifest,
    # '../') is refused before anything is put back or removed
    from . import guard
    guard.check([os.path.join(root, rel) for rel in manifest.get("modified", []) + manifest.get("created", [])],
                guard.roots_of(mod), "restore")
    guard.check([_copy_of(bdir, rel) for rel in manifest.get("modified", [])], [os.path.dirname(bdir)], "restore")
    p = root
    try:
        for rel in manifest["modified"]:
            p = os.path.join(root, rel)
            if os.path.exists(p):
                remove_file(p)                  # never write through a hard link (a read-only one too)
            shutil.copy2(_copy_of(bdir, rel), p)
        for rel in manifest["created"]:
            p = os.path.join(root, rel)
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                remove_file(p)
            # folders the run made for its new files (ui/custom_portraits/<name>/) go when left empty
            d = os.path.dirname(p)
            while os.path.abspath(d).startswith(os.path.abspath(mod.data) + os.sep) and os.path.isdir(d) \
                    and not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
        p = bdir
        shutil.move(bdir, bdir + "_restored")
    except OSError as e:                        # a file held by the game, the disk full...: the backup stays whole
        words = str(e) if isinstance(e, WriteError) else plain(getattr(e, "filename", None) or p, e) or \
            "%s: %s" % (type(e).__name__, e)
        raise WriteError("%s\n\nRestore stopped half way; the backup %s is kept whole - Restore it again once the "
                         "file is free (the files already put back are put back again, nothing is lost)."
                         % (words.replace("then Apply again", "then Restore again"), os.path.basename(bdir))) from e
    return manifest
