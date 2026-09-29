"""A Plan collects every edit in memory, can report and validate it, and writes
it to disk with a backup that restore() undoes."""

import datetime
import json
import os
import re
import shutil

from .textio import TextFile

BACKUP_DIR = "faction_tool_backups"


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
        if self.warnings:
            lines.append("")
            lines.append("WARNINGS")
            for rel, msg in self.warnings:
                lines.append("    %s%s" % (rel + ": " if rel else "", msg))
        return "\n".join(lines)

    # ---- disk ----
    def apply(self):
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
        for path in self.changed_files():
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
        for src, dst in self.copies:
            if os.path.exists(dst):
                continue
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            created.append(os.path.relpath(dst, root).replace("\\", "/"))
            if not os.path.isdir(src):
                manifest["copied_from"][created[-1]] = os.path.relpath(src, root).replace("\\", "/")
        manifest["created"] = created
        with open(os.path.join(bdir, "manifest.json"), "w", encoding="utf-8") as out:
            json.dump(manifest, out, indent=2)
        for path in self.changed_files():
            if path in self.files:
                self.files[path].save(path)
            elif path in self.binaries:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tmp = path + ".faction_tool_tmp"
                with open(tmp, "wb") as out:
                    out.write(self.binaries[path])
                os.replace(tmp, path)            # never write through a hard link
            elif path in self.deletions:
                os.remove(path)
        return bdir


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def backups(mod):
    root = os.path.join(os.path.dirname(mod.data), BACKUP_DIR)
    if not os.path.isdir(root):
        return []
    out = []
    for n in sorted(os.listdir(root), reverse=True):
        m = os.path.join(root, n, "manifest.json")
        if os.path.isfile(m) and not n.endswith("_restored"):
            out.append(os.path.join(root, n))
    return out


def restore(mod, bdir):
    """Put every file of a backup back and remove what that run created."""
    root = os.path.dirname(mod.data)
    with open(os.path.join(bdir, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    for rel in manifest["modified"]:
        dst = os.path.join(root, rel)
        if os.path.exists(dst):
            os.remove(dst)                  # never write through a hard link
        shutil.copy2(os.path.join(bdir, rel), dst)
    for rel in manifest["created"]:
        p = os.path.join(root, rel)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)
        # folders the run made for its new files (ui/custom_portraits/<name>/) go when left empty
        d = os.path.dirname(p)
        while os.path.abspath(d).startswith(os.path.abspath(mod.data) + os.sep) and os.path.isdir(d) \
                and not os.listdir(d):
            os.rmdir(d)
            d = os.path.dirname(d)
    shutil.move(bdir, bdir + "_restored")
    return manifest
