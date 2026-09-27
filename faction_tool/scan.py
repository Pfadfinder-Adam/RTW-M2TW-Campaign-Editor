"""Scan a whole mod: an inventory of its files, every place a faction is
mentioned, whether the tool handles that place, and references to files that
do not exist. Read-only - nothing is written."""

import codecs
import os
import re
from collections import Counter

from .moddata import DATA_FILES
from .plan import BACKUP_DIR
from .textio import strip_comment, tokens

TEXT_EXT = {".txt", ".json", ".xml", ".nut", ".lua", ".ini", ".cfg", ".csv", ".yml", ".yaml", ".rsd"}
MAX_TEXT = 32 * 1024 * 1024

# folders under data/ whose files named after a faction the tool copies
HANDLED_ART = ("ui/", "menu/", "loading_screen/")
# campaign files the tool edits (in the campaign it is run on)
HANDLED_CAMPAIGN = {"descr_strat.txt", "descr_win_conditions.txt"}
# campaign files it reads only: a mention there is information, not a gap
READ_CAMPAIGN = {"descr_regions.txt", "descr_regions_and_settlement_name_lookup.txt", "descr_regions_safe.txt"}


def _read_text(path):
    with open(path, "rb") as f:
        data = f.read(MAX_TEXT + 1)
    if len(data) > MAX_TEXT:
        return None
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            return None
    if b"\0" in data[:4096]:
        return None                     # binary under a text extension
    return data.decode("latin-1")


def _word(name):
    """Whole word, any case; '_' and '#' count as separators ('symbol24_gaetulii')."""
    return re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(name), re.I)


class Scan:
    def __init__(self, mod, faction, campaign=None):
        self.mod = mod
        self.faction = faction.lower()
        self.campaign = campaign
        self.root = os.path.dirname(mod.data)
        self.files = []                  # (rel path, size)
        self.hits = {}                   # rel path -> [(line no, line)]
        self.named = []                  # rel paths of files / folders named after the faction
        self.missing = []                # (from rel, what, missing rel)
        self.skipped = []                # text files too big or unreadable

    def rel(self, path):
        return os.path.relpath(path, self.root).replace("\\", "/")

    # ---- the walk ----
    def run(self, progress=None):
        word = _word(self.faction)
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d != BACKUP_DIR)
            for d in dirnames:
                if word.search(d):
                    self.named.append(self.rel(os.path.join(dirpath, d)) + "/")
            for n in sorted(filenames):
                p = os.path.join(dirpath, n)
                try:
                    size = os.path.getsize(p)
                except OSError:
                    continue
                rel = self.rel(p)
                self.files.append((rel, size))
                if word.search(os.path.splitext(n)[0]):
                    self.named.append(rel)
                if os.path.splitext(n)[1].lower() not in TEXT_EXT:
                    continue
                text = _read_text(p)
                if text is None:
                    self.skipped.append(rel)
                    continue
                if progress and len(self.files) % 500 == 0:
                    progress(len(self.files))
                if not word.search(text):
                    continue
                lines = [(i + 1, l.rstrip("\r")) for i, l in enumerate(text.split("\n")) if word.search(l)]
                self.hits[rel] = lines
        self.check_references()
        return self

    # ---- which places the tool handles ----
    def handled(self, rel):
        data = self.rel(self.mod.data) + "/"
        if not rel.startswith(data):
            return False
        sub = rel[len(data):]
        low = sub.lower()
        if low in {v.lower() for v in DATA_FILES.values()}:
            return True
        if low.startswith("text/"):
            return True
        if low.startswith(HANDLED_ART):
            return True
        if low.startswith("world/maps/campaign/") or low.startswith("world/maps/base/"):
            parts = low.split("/")
            name = parts[-1]
            if self.campaign and len(parts) >= 4 and parts[3] != self.campaign.lower() and parts[2] == "campaign":
                return False                     # another campaign: the tool runs on one at a time
            return name in HANDLED_CAMPAIGN or name.startswith("map_")
        return False

    def read_only(self, rel):
        return rel.lower().rsplit("/", 1)[-1] in READ_CAMPAIGN

    # ---- references that point at nothing ----
    def check_references(self):
        """Texture/model paths of the faction in descr_model_battle / _strat, and
        its units' cards, must exist on disk."""
        for key in ("model_battle", "model_strat"):
            path = self.mod.file(key)
            if not path:
                continue
            f = self.mod.load(path)
            for i, l in enumerate(f.texts()):
                tk = tokens(l)
                if len(tk) >= 3 and tk[0] in ("texture", "model_flexi", "model_flexi_m") and tk[1] == self.faction:
                    ref = strip_comment(l).split(",", 1)[1].strip()
                    if tk[0].startswith("model_flexi"):
                        ref = ref.split(",")[0].strip()
                    if not self._exists(ref):
                        self.missing.append((self.mod.rel(path) + ":%d" % (i + 1), tk[0], ref))
        edu = self.mod.file("edu")
        if edu:
            cur = None
            for l in self.mod.load(edu).texts():
                tk = tokens(l)
                if tk[:1] == ["dictionary"] and len(tk) > 1:
                    cur = tk[1]
                elif tk[:1] == ["ownership"] and cur and self.faction in tk[1:]:
                    for sub, pattern in (("units", "#%s.tga"), ("unit_info", "%s_info.tga")):
                        ref = "data/ui/%s/%s/%s" % (sub, self.faction, pattern % cur)
                        if not self._exists(ref):
                            self.missing.append(("export_descr_unit.txt (%s)" % cur, "unit card", ref))
                    cur = None

    def _exists(self, ref):
        ref = ref.replace("\\", "/").strip().strip('"')
        if not ref.lower().startswith("data/"):
            ref = "data/" + ref
        p = os.path.join(os.path.dirname(self.mod.data), *ref.split("/"))
        if os.path.exists(p):
            return True
        # the game's paths ignore case; so does this check
        folder, name = os.path.split(p)
        if not os.path.isdir(folder):
            return self._exists_ci(p)
        low = name.lower()
        return any(n.lower() == low for n in os.listdir(folder))

    def _exists_ci(self, p):
        parts = os.path.normpath(p).split(os.sep)
        cur = parts[0] + os.sep if parts[0] else os.sep
        for part in parts[1:]:
            if not os.path.isdir(cur):
                return False
            m = next((n for n in os.listdir(cur) if n.lower() == part.lower()), None)
            if m is None:
                return False
            cur = os.path.join(cur, m)
        return True

    # ---- the report ----
    def report(self, samples=3):
        out = []
        total = sum(s for _, s in self.files)
        out.append("SCAN of %s for '%s'%s" % (self.root, self.faction,
                                              " (campaign %s)" % self.campaign if self.campaign else ""))
        out.append("")
        out.append("INVENTORY: %d files, %.1f MB" % (len(self.files), total / 1048576.0))
        by_ext = Counter(os.path.splitext(r)[1].lower() or "(none)" for r, _ in self.files)
        out.append("    by type: " + ", ".join("%s %d" % (e, n) for e, n in by_ext.most_common(15)))
        top = Counter()
        for r, s in self.files:
            parts = r.split("/")
            top["/".join(parts[:2]) if parts[0].lower() == "data" and len(parts) > 2 else parts[0]] += 1
        out.append("    by folder: " + ", ".join("%s %d" % (d, n) for d, n in top.most_common(20)))
        if self.skipped:
            out.append("    not read (binary or over 32 MB): %d text-type file(s)" % len(self.skipped))

        groups = {"handled": [], "read": [], "other": []}
        for rel in sorted(self.hits, key=str.lower):
            g = "handled" if self.handled(rel) else "read" if self.read_only(rel) else "other"
            groups[g].append(rel)

        out.append("")
        out.append("NOT HANDLED - mentions of '%s' the tool does not copy (%d file(s))" % (self.faction, len(groups["other"])))
        out.append("    check these by hand: a new faction may need an entry here too")
        for rel in groups["other"]:
            lines = self.hits[rel]
            out.append("  %s  (%d line(s))" % (rel, len(lines)))
            for no, l in lines[:samples]:
                out.append("      %6d: %s" % (no, l.strip()[:140]))
            if len(lines) > samples:
                out.append("         ... %d more" % (len(lines) - samples))

        out.append("")
        out.append("HANDLED - files the tool edits or copies from (%d)" % len(groups["handled"]))
        for rel in groups["handled"]:
            out.append("  %s  (%d line(s))" % (rel, len(self.hits[rel])))
        if groups["read"]:
            out.append("")
            out.append("READ ONLY - information the tool reads, nothing to copy (%d)" % len(groups["read"]))
            for rel in groups["read"]:
                out.append("  %s  (%d line(s))" % (rel, len(self.hits[rel])))

        named_other = [r for r in self.named if not self.handled(r.rstrip("/"))]
        out.append("")
        out.append("FILES AND FOLDERS NAMED AFTER '%s': %d, of which %d outside the copied folders"
                   % (self.faction, len(self.named), len(named_other)))
        for r in named_other[:60]:
            out.append("  " + r)
        if len(named_other) > 60:
            out.append("  ... %d more" % (len(named_other) - 60))

        out.append("")
        out.append("MISSING FILES - referenced for '%s' but not on disk (%d)" % (self.faction, len(self.missing)))
        for src, what, ref in self.missing[:200]:
            out.append("  %s  %s -> %s" % (src, what, ref))
        if len(self.missing) > 200:
            out.append("  ... %d more" % (len(self.missing) - 200))
        return "\n".join(out)


def scan(mod, faction, campaign=None, progress=None):
    return Scan(mod, faction, campaign).run(progress)
