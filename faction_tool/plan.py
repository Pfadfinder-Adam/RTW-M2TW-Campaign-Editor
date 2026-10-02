"""A Plan collects every edit in memory, can report and validate it, and writes
it to disk with a backup that restore() undoes."""

import datetime
import json
import os
import shutil

from .textio import TextFile, WriteError, make_writable, readonly, refused, remove_file, replace_file

BACKUP_DIR = "CampaignEditor_backups"
OLD_BACKUP_DIR = "faction_tool_backups"           # up to 0.28: still listed, Restore works on both
BACKUP_DIRS = (BACKUP_DIR, OLD_BACKUP_DIR)


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
        os.makedirs(bdir)
        # copied_from {created: its source}: what a copied picture was before it was replaced (Art's
        # "Back to the original"); Restore does not need it
        manifest = {"faction": self.new, "template": self.template, "modified": [], "created": [], "copied_from": {}}
        created = []
        changed = self.changed_files()
        for path in changed:
            rel = os.path.relpath(path, root)
            if path not in self.originals and not os.path.exists(path):
                created.append(rel.replace("\\", "/"))     # a new picture: Restore removes it
                continue
            dst = os.path.join(bdir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if path in self.originals:
                with open(dst, "wb") as out:
                    out.write(self.originals[path])
            else:                               # a picture or a removed file: back up what is on disk
                shutil.copy2(path, dst)
            manifest["modified"].append(rel.replace("\\", "/"))
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
            why = str(e) if isinstance(e, WriteError) else "%s: %s" % (type(e).__name__, e)
            if left:
                raise WriteError("%s\n\n%d file(s) written before it could not be put back (%s) - use Restore on "
                                 "the backup %s." % (why, len(left), ", ".join(left[:5]), bdir)) from e
            raise WriteError("%s\n\nNothing was changed: %s" % (
                why, "the %d file(s) written before it were put back." % (len(done) + len(made))
                if done or made else "no file had been written yet.")) from e
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
                shutil.copy2(os.path.join(bdir, rel), path)
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
                out.append((n[:15], os.path.getmtime(m), os.path.join(root, n)))
    # newest first; two runs in one second (terrain + faction by one Apply) by the time
    # their manifest was written, not by name
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
    what = m.get("faction") or n[16:]
    if m.get("template") and m.get("template") != what:
        what += " (from %s)" % m["template"]
    k = len(m.get("modified", [])) + len(m.get("created", []))
    return "%s  %s  - %d file%s" % (when, what, k, "" if k == 1 else "s")


def restore_to(mod, bdir):
    """Undo bdir and every newer backup, newest first (backups undo each other in
    order), so the files are as they were before bdir's run. Returns the manifests."""
    order = backups(mod)
    norm = [os.path.normcase(os.path.abspath(b)) for b in order]
    key = os.path.normcase(os.path.abspath(bdir))
    if key not in norm:
        raise ValueError("no such backup: %s" % bdir)
    return [restore(mod, b) for b in order[:norm.index(key) + 1]]


def restore(mod, bdir):
    """Put every file of a backup back and remove what that run created."""
    root = os.path.dirname(mod.data)
    with open(os.path.join(bdir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    # a backup names its files relative to the mod's folder; one that points outside it (a crafted manifest,
    # '../') is refused before anything is put back or removed
    from . import guard
    guard.check([os.path.join(root, rel) for rel in manifest.get("modified", []) + manifest.get("created", [])],
                guard.roots_of(mod), "restore")
    guard.check([os.path.join(bdir, rel) for rel in manifest.get("modified", [])], [bdir], "restore")
    for rel in manifest["modified"]:
        dst = os.path.join(root, rel)
        if os.path.exists(dst):
            remove_file(dst)                # never write through a hard link (a read-only one too)
        shutil.copy2(os.path.join(bdir, rel), dst)
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
    shutil.move(bdir, bdir + "_restored")
    return manifest
