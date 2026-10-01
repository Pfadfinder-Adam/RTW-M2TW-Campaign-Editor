"""Scan a whole mod: an inventory of its files, every place a faction is
mentioned, whether the tool handles that place, and references to files that
do not exist. Read-only - nothing is written."""

import codecs
import fnmatch
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


# mentions that are normal for any faction and need nothing from a new one
IGNORABLE = (
    (re.compile(r"(^|/)world/maps/(battle|custom)/|(^|/)descr_battle\.txt$", re.I), "battle maps and historical battles"),
    (re.compile(r"(^|/)editor_log\.txt$", re.I), "battle editor logs"),
    (re.compile(r"(^|/)[^/]*\.log(\.txt)?$|(^|/)system\.log", re.I), "game logs"),
    (re.compile(r"(^|/)export_descr_advice\.txt$", re.I), "advisor triggers (optional)"),
    (re.compile(r"(^|/)export_descr_sounds_prebattle\.txt$", re.I), "pre-battle speech lines (optional)"),
    (re.compile(r"(^|/)(campaign_script|be_script[^/]*|four_turns)\.txt$", re.I),
     "campaign scripts: events written for that faction - read them, copy by hand if wanted"),
    (re.compile(r"(^|/)data/text/(?!english/)[^/]+/", re.I),
     "translations in data/text/<language>/ (the tool writes English only)"),
    (re.compile(r"(^|/)(![^/]*|[^/]*kopie[^/]*|[^/]*backup[^/]*|[^/]* - copy[^/]*)(/|$)", re.I), "copies and backups"),
)


IGNORE_FILE = "faction_tool_ignore.txt"
IGNORE_HELP = """# Folders and files the scan leaves out - one rule per line, paths from the
# mod folder, '/' as separator, case does not matter. Only the scan reads this.
#
#   data/world/maps/campaign/custom/     a folder (ends with /)
#   old_stuff/                           any folder with this name, anywhere
#   *.bak                                files matching a mask, anywhere
#   data/text/test_*.txt                 files matching a mask in one folder
"""


def ignore_path(root):
    return os.path.join(root, IGNORE_FILE)


def load_ignore(root):
    try:
        with open(ignore_path(root), encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    return [l.strip().replace("\\", "/").lower() for l in lines if l.strip() and not l.strip().startswith("#")]


def _ignored(rel, is_dir, rules):
    rel = rel.lower()
    name = rel.rsplit("/", 1)[-1]
    for r in rules:
        if r.endswith("/"):
            if not is_dir:
                continue
            r = r[:-1]
            if "/" in r:
                if fnmatch.fnmatch(rel, r):
                    return True
            elif fnmatch.fnmatch(name, r):
                return True
        elif not is_dir:
            if fnmatch.fnmatch(rel, r) if "/" in r else fnmatch.fnmatch(name, r):
                return True
    return False


def _ignorable(rel):
    for rx, why in IGNORABLE:
        if rx.search(rel):
            return why
    return None


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
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
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
        self.other_mods = []             # mod folders inside the scanned folder, left out
        self.rules = load_ignore(self.root)
        self.origins = Origins.for_mod(mod)     # game / REX manifests: where each file comes from
        self.origin = {}                 # rel path -> 'game' | 'changed' | 'rex' | 'own'
        self.origin_bytes = Counter()
        self.user_dirs, self.user_files = [], 0     # left out by the ignore list

    def rel(self, path):
        return os.path.relpath(path, self.root).replace("\\", "/")

    def rel_game(self, path):
        """The path as the game's own install would have it: data/... from the mod's
        data folder (a mod folder mirrors the game's layout)."""
        return "data/" + os.path.relpath(path, self.mod.data).replace("\\", "/")

    # ---- the walk ----
    def run(self, progress=None):
        word = _word(self.faction)
        data_abs = os.path.normcase(os.path.abspath(self.mod.data))
        for dirpath, dirnames, filenames in os.walk(self.root):
            keep = []
            for d in sorted(dirnames):
                full = os.path.join(dirpath, d)
                if d == BACKUP_DIR:
                    continue
                if self.rules and _ignored(self.rel(full), True, self.rules):
                    self.user_dirs.append(self.rel(full) + "/")
                    continue
                if os.path.normcase(os.path.abspath(full)) != data_abs and \
                        os.path.isfile(os.path.join(full, "data", "descr_sm_factions.txt")):
                    self.other_mods.append(self.rel(full))     # a mod inside the game folder
                    continue
                keep.append(d)
            dirnames[:] = keep
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
                if self.rules and _ignored(rel, False, self.rules):
                    self.user_files += 1
                    continue
                self.files.append((rel, size))
                if self.origins:
                    o = self.origins.classify(self.rel_game(p), p, size)
                    self.origin[rel] = o
                    self.origin_bytes[o] += size
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
            mine = {self.rel(p).lower() for p in self.mod.text_files()}
            return rel.lower() in mine
        if low.startswith(HANDLED_ART):
            return True
        if low.startswith("world/maps/campaign/") or low.startswith("world/maps/base/"):
            parts = low.split("/")
            name = parts[-1]
            if self.campaign and len(parts) >= 4 and parts[3] != self.campaign.lower() and parts[2] == "campaign":
                return False                     # another campaign: the tool runs on one at a time
            return name in HANDLED_CAMPAIGN or name.startswith("map_")
        return False

    def _other_campaign(self, rel):
        m = re.search(r"world/maps/campaign/(.+)/[^/]+$", rel, re.I)
        if m and self.campaign and m.group(1).lower().rstrip("/").split("/")[-1] != self.campaign.lower():
            return "other campaigns: the tool adds the faction to one campaign per run"
        return None

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
        # Rome keeps x.tga as x.tga.dds, and many pictures only in data/packs/*.pak: both count as there
        if ref.lower().endswith(".tga") and self._exists(ref + ".dds"):
            return True
        if self._in_packs(ref):
            return True
        p = os.path.join(os.path.dirname(self.mod.data), *ref.split("/"))
        if os.path.exists(p):
            return True
        # the game's paths ignore case; so does this check
        folder, name = os.path.split(p)
        if not os.path.isdir(folder):
            return self._exists_ci(p)
        low = name.lower()
        return any(n.lower() == low for n in os.listdir(folder))

    def _in_packs(self, ref):
        from .rompak import has
        try:
            return has(self.mod, ref)
        except Exception:
            return False

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
        if self.origins:
            out.append("    where they come from (by %s):" % self.origins.label())
            n = Counter(self.origin.values())
            for o in ("game", "rex", "changed", "own"):
                if n[o]:
                    out.append("        %-44s %6d  (%.1f MB)" % (ORIGIN_TEXT[o], n[o], self.origin_bytes[o] / 1048576.0))
            for o in ("changed", "own"):
                folders = Counter()
                for r, x in self.origin.items():
                    if x == o and not r.lower().startswith("data/"):
                        folders[r.split("/")[0]] += 1
                    elif x == o:
                        parts = r.split("/")
                        folders["/".join(parts[:2]) if len(parts) > 2 else parts[0]] += 1
                if folders:
                    out.append("        %s by folder: %s" % (ORIGIN_TEXT[o].split(" (")[0], ", ".join(
                        "%s %d" % kv for kv in folders.most_common(10))))
        else:
            out.append("    (no game manifest found: files are not told apart as the game's, REX's or the mod's own)")

        if self.other_mods:
            out.append("    other mods inside this folder, not scanned: " + ", ".join(self.other_mods))
        if self.rules:
            out.append("    left out by %s: %d folder(s)%s, %d file(s) by mask"
                       % (IGNORE_FILE, len(self.user_dirs),
                          (" (" + ", ".join(self.user_dirs[:5]) + (" ..." if len(self.user_dirs) > 5 else "") + ")")
                          if self.user_dirs else "", self.user_files))
        groups = {"handled": [], "read": [], "other": [], "ignore": []}
        why = {}
        for rel in sorted(self.hits, key=str.lower):
            if self.handled(rel):
                g = "handled"
            elif self.read_only(rel):
                g = "read"
            else:
                why[rel] = _ignorable(rel) or self._other_campaign(rel)
                g = "ignore" if why[rel] else "other"
            groups[g].append(rel)

        out.append("")
        out.append("NOT HANDLED - mentions of '%s' the tool does not copy (%d file(s))" % (self.faction, len(groups["other"])))
        out.append("    check these by hand: a new faction may need an entry here too")
        for rel in groups["other"]:
            lines = self.hits[rel]
            tag = ORIGIN_TAG.get(self.origin.get(rel), "")
            out.append("  %s  (%d line(s))%s" % (rel, len(lines), tag))
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

        if groups["ignore"]:
            out.append("")
            out.append("USUALLY SAFE TO IGNORE (%d)" % len(groups["ignore"]))
            reasons = Counter(why[r] for r in groups["ignore"])
            for reason, n in reasons.most_common():
                files = [r for r in groups["ignore"] if why[r] == reason]
                out.append("  %s: %d file(s), e.g. %s" % (reason, n, ", ".join(files[:3])))

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


# ---------------------------------------------------------------------------
# Where a mod's file comes from: the game's manifests (a clean install and REX)
# ---------------------------------------------------------------------------
ORIGIN_TEXT = {"game": "game files, unchanged", "rex": "REX's files (the 64-bit engine's own)",
               "changed": "game files changed by the mod", "own": "the mod's own files (not in the game)"}
ORIGIN_TAG = {"game": "  [the game's own file, unchanged]", "rex": "  [REX's file]",
              "changed": "  [game file changed by the mod]", "own": "  [the mod's own file]"}


def reference_dir():
    """The folder with the manifests that come with the tool (docs/reference in the
    source, 'reference' inside the exe)."""
    import sys
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "reference")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "reference")


def _load_manifest(path):
    import gzip
    import json
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            d = json.load(f)
        return {k.lower(): v for k, v in d.get("files", {}).items()}
    except (OSError, ValueError):
        return None


class Origins:
    """Tells a file apart: the game's own (as in a clean install), REX's, a game file
    the mod changed, or the mod's own. Sizes first; a file is read (md5) only when
    its size matches."""
    _cache = {}

    def __init__(self, game, rex, names):
        self.game, self.rex, self.names = game or {}, rex or {}, names

    def label(self):
        return " + ".join(self.names)

    @classmethod
    def for_mod(cls, mod):
        """The manifests for the game the mod belongs to: the one made on the user's own
        PC (<game>/rtw_manifest.json.gz, Tools > Game manifest) first, else the one that
        comes with the tool (Rome: Total War Gold, Steam; Medieval II), and REX's."""
        from .newmod import game_of
        game_dir = game_of(mod.data)
        medieval = any(os.path.isfile(os.path.join(game_dir, e)) for e in ("medieval2.exe", "kingdoms.exe", "M2EX.exe"))
        ref = reference_dir()
        own = os.path.join(game_dir, MANIFEST_NAME)
        picks = [(own, "this PC's game manifest")] if os.path.isfile(own) else []
        picks.append((os.path.join(ref, "m2tw_manifest.json.gz" if medieval else "rtw_gold_steam_manifest.json.gz"),
                      "Medieval II manifest" if medieval else "Rome: Total War Gold manifest"))
        game = names = None
        for path, name in picks:
            key = (path, os.path.getmtime(path) if os.path.isfile(path) else 0)
            if key not in cls._cache:
                cls._cache[key] = _load_manifest(path)
            if cls._cache[key]:
                game, names = cls._cache[key], [name]
                break
        rex = None
        if not medieval:
            p = os.path.join(ref, "rex_manifest.json.gz")
            if p not in cls._cache:
                cls._cache[p] = _load_manifest(p)
            rex = cls._cache[p]
            if rex:
                names = (names or []) + ["REX manifest"]
        if not game and not rex:
            return None
        return cls(game, rex, names)

    def classify(self, rel, path, size):
        low = rel.lower()
        g, r = self.game.get(low), self.rex.get(low)
        digest = None
        for entry, kind in ((r, "rex"), (g, "game")):
            if entry and entry[0] == size:
                if digest is None:
                    digest = _md5(path)
                if digest == entry[1]:
                    return kind
        return "changed" if g or r else "own"


_md5_cache = {}                     # (path, size, mtime) -> md5: a second scan reads nothing again


def _md5(path):
    try:
        key = (path, os.path.getsize(path), os.path.getmtime(path))
    except OSError:
        return None
    if key not in _md5_cache:
        _md5_cache[key] = _md5_read(path)
    return _md5_cache[key]


def _md5_read(path):
    import hashlib
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


# ---------------------------------------------------------------------------
# The game's own files: a manifest of a clean install, to tell game files
# (untouched or changed) from files a mod or the user added
# ---------------------------------------------------------------------------
MANIFEST_NAME = "rtw_manifest.json.gz"
# the official expansions keep their own data folders but are part of the game
EXPANSIONS = {"bi", "alexander"}


def make_manifest(game_root, out_path=None, progress=None):
    """Walk the game folder - not the mod folders in it (a folder holding
    data/descr_sm_factions.txt of its own) and not our backups - and write
    {path: [size, md5]} gzipped. Returns (out_path, file count, mods skipped)."""
    import gzip
    import hashlib
    import json
    game_root = os.path.abspath(game_root)
    files, skipped = {}, []
    for dirpath, dirnames, filenames in os.walk(game_root):
        keep = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            if d == BACKUP_DIR:
                continue
            if dirpath == game_root and d.lower() not in EXPANSIONS and \
                    os.path.isfile(os.path.join(full, "data", "descr_sm_factions.txt")):
                skipped.append(d)
                continue
            keep.append(d)
        dirnames[:] = keep
        for n in sorted(filenames):
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, game_root).replace("\\", "/")
            if rel == MANIFEST_NAME:
                continue
            h = hashlib.md5()
            try:
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                files[rel] = [os.path.getsize(p), h.hexdigest()]
            except OSError:
                continue
            if progress and len(files) % 200 == 0:
                progress(len(files))
    out_path = out_path or os.path.join(game_root, MANIFEST_NAME)
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        json.dump({"format": 1, "root": os.path.basename(game_root), "mods_skipped": skipped,
                   "files": files}, f)
    return out_path, len(files), skipped
