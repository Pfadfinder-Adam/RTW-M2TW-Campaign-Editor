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

    def changed_files(self):
        return [p for p, f in self.files.items() if f.dump() != self.originals[p]]

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
        os.makedirs(bdir)
        manifest = {"faction": self.new, "template": self.template, "modified": [], "created": []}
        for path in self.changed_files():
            rel = os.path.relpath(path, root)
            dst = os.path.join(bdir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as out:
                out.write(self.originals[path])
            manifest["modified"].append(rel.replace("\\", "/"))
        created = []
        for src, dst in self.copies:
            if os.path.exists(dst):
                continue
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            created.append(os.path.relpath(dst, root).replace("\\", "/"))
        manifest["created"] = created
        with open(os.path.join(bdir, "manifest.json"), "w", encoding="utf-8") as out:
            json.dump(manifest, out, indent=2)
        for path in self.changed_files():
            self.files[path].save(path)
        return bdir


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
        shutil.copy2(os.path.join(bdir, rel), os.path.join(root, rel))
    for rel in manifest["created"]:
        p = os.path.join(root, rel)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)
    shutil.move(bdir, bdir + "_restored")
    return manifest
