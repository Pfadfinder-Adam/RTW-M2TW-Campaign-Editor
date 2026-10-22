"""A Plan collects every edit in memory, can report and validate it, and writes
it to disk with a backup that restore() undoes."""

import datetime
import json
import time
import os
import re
import shutil

from .textio import TextFile, WriteError, make_writable, plain, readonly, refused, remove_file, replace_file

BACKUP_DIR = "CampaignEditor_backups"
OLD_BACKUP_DIR = "faction_tool_backups"           # up to 0.28: still listed, Restore works on both
BACKUP_DIRS = (BACKUP_DIR, OLD_BACKUP_DIR)


# listeners told of every finished write: fn(backup folder, the plan) - the window's 'Undo this write' button
WRITTEN = []
# asked before every write, nothing written yet: fn(the plan) may raise WriteError to stop it (the window's 'make your
# own mod folder first?' - asked once per mod the editor did not make)
BEFORE = []

class _Owned(dict):
    """A dict of paths whose keys are the mod's own places: a file of the game's data under a mod that holds only
    its changes (ModData.under) is written as the mod's copy, so a lookup by either path finds it."""

    def __init__(self, mod):
        super().__init__()
        self._own = getattr(mod, "own", None) or (lambda p: p)

    def __getitem__(self, k):
        return super().__getitem__(self._own(k))

    def __setitem__(self, k, v):
        super().__setitem__(self._own(k), v)

    def __contains__(self, k):
        return super().__contains__(self._own(k))

    def __delitem__(self, k):
        super().__delitem__(self._own(k))

    def get(self, k, default=None):
        return super().get(self._own(k), default)

    def pop(self, k, *default):
        return super().pop(self._own(k), *default)

    def setdefault(self, k, default=None):
        return super().setdefault(self._own(k), default)


class Plan:
    def __init__(self, mod, template, new, opts=None):
        self.mod = mod
        self.template = template
        self.new = new
        self.opts = opts or {}
        self.files = _Owned(mod)       # path -> edited TextFile
        self.binaries = _Owned(mod)    # path -> new bytes (pictures such as map_regions.tga)
        self.deletions = []      # paths removed (map.rwm, which the game rebuilds)
        self.originals = _Owned(mod)   # path -> original bytes
        self.borrowed = set()    # the mod's new copies of the game's files (Restore removes them)
        self.copies = []         # (src, dst) files or folders to copy
        self.notes = []          # (rel path or "", message)
        self.warnings = []
        self.faction_count = None
        # Medieval II: resources left on a wasteland's land (resources.drop_on) - found ['silk at 289, 70'], and the
        # modder's answer to the one question (the user, 2026-10-10): None / True = they go, False = they stay
        self.on_wasteland = []
        self.wasteland_resources_out = None
        # characters a moved town carried along (mapedit.apply_places): {(name, old tile): new tile} - the Map's
        # later changes to them (a move out, units) still find them by the tile they were read on
        self.carried = {}

    # ---- building ----
    def edit(self, path):
        if path not in self.files:
            f = TextFile.load(path)
            mine = self.mod.own(path) if hasattr(self.mod, "own") else path
            if mine != path and not os.path.exists(mine):    # the game's file: written as the mod's own copy
                f.path = mine
                self.borrowed.add(mine)
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
        dst = self.mod.own(dst) if hasattr(self.mod, "own") else dst   # never into the game's data under a mod
        self.copies.append((src, dst))
        self.note(None, "copy %s -> %s" % (self.mod.rel(src), self.mod.rel(dst)))

    def note(self, f, msg):
        self.notes.append((self.mod.rel(f.path) if f is not None else "", msg))

    def warn(self, f, msg):
        self.warnings.append((self.mod.rel(f.path) if f is not None else "", msg))

    MAP_FILES = ("descr_regions.txt", "descr_terrain.txt")
    # the files the game builds map.rwm from (RomeTW.exe FUN_0046e313: descr_regions, descr_terrain, the heights, then
    # the layer pictures) - never a faction's select map (map_<faction>.tga), the radar map or a campaign's texts
    MAP_LAYERS = frozenset(MAP_FILES + (
        "map_regions.tga", "map_heights.tga", "map_heights.hgt", "map_ground_types.tga", "map_climates.tga",
        "map_features.tga", "map_fog.tga", "map_roughness.tga", "map_trade_routes.tga", "map_fe.tga",
        "water_surface.tga"))

    def _is_map_layer(self, name):
        name = name.lower()
        return name in self.MAP_LAYERS or name.endswith(".hgt")

    def _whole_map_folders(self):
        """A mod that holds only its changes (ModData.under, a thin New mod folder): the first time it gets its own
        copy of a map layer (map_regions.tga, the heights, descr_regions, descr_terrain... MAP_LAYERS), the other map
        layers of that folder of the game come into the mod with it - but map.rwm - as the mod's own copies (Restore
        removes them). The game then builds map.rwm from the mod's whole map - never the mod's new map with the game's
        old map.rwm. Nothing else of the folder comes: a campaign's descr_strat, events, scripts, texts and pictures
        (a redrawn map_<faction>.tga too) stay the game's, read from there, so they never shadow the modder's own."""
        under = getattr(self.mod, "under", None)
        if not under:
            return
        folders = set()
        written = {os.path.normcase(os.path.abspath(p)) for p in self.changed_files()}
        for mine in self.borrowed:
            if os.path.normcase(os.path.abspath(mine)) not in written:
                continue                            # read for the change but left as it is: still the game's
            rel = os.path.relpath(mine, self.mod.data).replace("\\", "/").lower()
            name = os.path.basename(rel)
            if rel.startswith("world/maps/") and self._is_map_layer(name):
                folders.add(os.path.dirname(mine))
        taken = written | {os.path.normcase(os.path.abspath(d)) for _, d in self.copies}
        for folder in sorted(folders):
            src = os.path.join(under, os.path.relpath(folder, self.mod.data))
            if not os.path.isdir(src):
                continue
            n = 0
            for name in sorted(os.listdir(src)):
                s, d = os.path.join(src, name), os.path.join(folder, name)
                if not os.path.isfile(s) or not self._is_map_layer(name) or os.path.exists(d) or \
                        os.path.normcase(os.path.abspath(d)) in taken:
                    continue
                self.copies.append((s, d))
                n += 1
            if n:
                self.notes.append((self.mod.rel(folder), "%d more map layer(s) of the game copied into the mod with it "
                                   "(the game builds map.rwm again from the mod's whole map; the rest stays the game's)"
                                   % n))

    def binary(self, path, data):
        """A whole new content for a (binary) file, backed up like any edit (a file of the game's data under a mod
        that holds only its changes: the mod's own copy)."""
        mine = self.mod.own(path) if hasattr(self.mod, "own") else path
        if mine != path and not os.path.exists(mine):
            self.borrowed.add(mine)
        self.binaries[path] = data

    def patch_tga(self, path, changes):
        """Pixels of a TGA changed on top of what this plan already changed in it (painted regions and a moved
        town in one write: the second must not start again from the file and lose the first)."""
        from .tga import patched
        self.binary(path, patched(path, changes, self.binaries.get(path)))

    def delete(self, path, why):
        if hasattr(self.mod, "own") and self.mod.own(path) != path:
            return                                  # the game's own file: a mod never removes it
        if os.path.exists(path) and path not in self.deletions:
            self.deletions.append(path)
            self.notes.append((self.mod.rel(path), "removed - %s" % why))

    # the texts the game compiles into data/sounds/events.dat + events.idx (descr_sounds_db.xml and the accents name the
    # factions by their place in descr_sm_factions.txt, so a new faction moves the others' voices too)
    SOUND_TEXTS = re.compile(r"^(descr_sounds.*\.(txt|xml)|export_descr_sounds.*\.txt|descr_sm_factions\.txt)$", re.I)

    def stale_sounds(self):
        """The game's compiled sounds (data/sounds/events.dat + events.idx) go (backed up) when a sound text or the
        factions' list changed - the game builds them again on its next start. Kept, they gave every faction the
        voices of another after a new faction (Discord, 2026-10-17: Denmark speaking Arabic, Turks German - fixed by
        deleting those two files, an old twcenter tip)."""
        changed = [p for p, f in self.files.items() if f.dump() != self.originals.get(p)]
        if not any(self.SOUND_TEXTS.match(os.path.basename(p)) for p in changed):
            return
        folder = self.mod.find("sounds")
        if not folder:
            return
        try:
            names = os.listdir(folder)
        except OSError:
            return
        for n in names:
            if n.lower() in ("events.dat", "events.idx"):
                self.delete(os.path.join(folder, n), "the game's compiled sounds - kept, the factions' voices would "
                                                    "be mixed up; the game builds them again on its next start")

    def stale_bins(self):
        """Medieval II reads a string table's compiled <name>.txt.strings.bin when one lies beside the .txt, so a
        changed .txt was never seen (the event, temple and hall names of a tester's run, 2026-10-05): the .bin
        beside every changed text file goes (backed up; the game builds it again from the .txt)."""
        made = [p for p in self.binaries if p.lower().endswith(".txt")]   # a .txt made from the .bin (strtables)
        for p in [p for p, f in self.files.items() if f.dump() != self.originals.get(p)] + made:
            if not p.lower().endswith(".txt"):
                continue
            folder = os.path.dirname(p)
            want = os.path.basename(p).lower() + ".strings.bin"
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for n in names:
                if n.lower() == want:
                    self.delete(os.path.join(folder, n), "the compiled copy of %s - Medieval II would read it instead "
                                                         "of the changed text; the game builds it again"
                                % os.path.basename(p))

    def changed_files(self):
        return [p for p, f in self.files.items() if f.dump() != self.originals[p]] + \
            [p for p, d in self.binaries.items() if not os.path.exists(self.source_of(p)) or _read(self.source_of(p)) != d] + \
            list(self.deletions)

    def source_of(self, path):
        """What a file is now: the mod's own, else - a thin mod's file not copied yet - the game's it would be copied
        from (a picture written with the game's very bytes is no change: never copied into the mod)."""
        if os.path.exists(path) or not getattr(self.mod, "under", None):
            return path
        rel = os.path.relpath(os.path.abspath(path), os.path.abspath(self.mod.data))
        return os.path.join(self.mod.under, rel) if not rel.startswith("..") else path

    def touched(self, path):
        """A file this plan really changes, or one the mod already holds as its own - the only files the keep-ups
        (lnt / eventimages / emergence) may put right: a game's file the plan only read stays the game's (the user,
        2026-10-20: copies of untouched game files shadow a modder's own)."""
        mine = self.mod.own(path) if hasattr(self.mod, "own") else path
        if mine not in self.borrowed:
            return True
        f = self.files.get(path)
        if f is not None:
            return f.dump() != self.originals[path]
        return path in self.binaries

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
        old = self.opts.get("template_people")
        if old and not any(o == old for o, _ in pairs):
            # the template's people ('The Scots are Victorious'): its own word, else the short name + s
            nw = self.opts.get("people") or ""
            if not nw:
                base = (self.opts.get("short_name") or (self.opts.get("display_name") or "").split(" of ")[-1]).strip()
                nw = base if not base or base.lower().endswith("s") else base + "s"
            if nw:
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
        self.stale_bins()
        self.stale_sounds()
        lines = []
        bad = self.crash_problems()
        if bad:                                     # said in Preview, not only when Apply is pressed (a report)
            lines += ["APPLY WILL REFUSE THIS - the game could not read it:"] + ["    " + m for m in bad] + [""]
        by = {}
        for rel, msg in self.notes:
            by.setdefault(rel, []).append(msg)
        for rel in sorted(by):
            lines.append(rel or "(files)")
            for msg in by[rel]:
                lines.append("    " + msg)
        warnings = list(self.warnings) + [("", m) for m in self.tile_notes()]
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
    def crash_problems(self):
        """What this write would make that the game cannot read, judged on the files as they will be written (so the
        order of the changes does not matter): an army with no unit (the game stops reading the campaign there - a
        report: most factions vanished), two armies on one tile. One the mod has already is its own and stays."""
        from .strat import Strat, empty_armies, shared_army_tiles, stray_units
        out = []
        changed = self.changed_files()
        for path, f in self.files.items():
            if os.path.basename(path).lower() != "descr_strat.txt" or path not in changed:
                continue
            old = Strat(TextFile.load(path)) if os.path.exists(path) else None
            had = set(empty_armies(old)) if old else set()
            new = [a for a in empty_armies(Strat(f)) if a not in had]
            if new:
                out.append("%s: an army needs at least one unit - the game stops reading the campaign there ('Must "
                           "add at least one unit to an army') and every faction after it is lost; give it a unit or "
                           "take it off the map" % (", ".join(new[:8]) + (" and %d more" % (len(new) - 8)
                                                                            if len(new) > 8 else "")))
            had = {w.split(" (line ")[0] for _, w in stray_units(old)} if old else set()
            for _, w in stray_units(Strat(f)):
                if w.split(" (line ")[0] not in had:
                    out.append("%s - the game stops reading the factions there and every faction after it is lost "
                               "(the rebels too); this write would leave it so" % w)
                    break
            was = shared_army_tiles(old) if old else {}
            for xy, names in sorted(shared_army_tiles(Strat(f)).items()):
                if not set(names) - set(was.get(xy, [])) or self._engine_takes(names):
                    continue
                out.append("%s: two armies on one tile (%d, %d) - the game stops reading the campaign there "
                           "('trying to attach ... to the army of' / 'Cannot attach 2 armies together'); move one of "
                           "them" % (" and ".join("%s (%s)" % n for n in names), xy[0], xy[1]))
        out += self._wall_problems(changed)
        return out

    def _wall_problems(self, changed):
        """The original exes' walls this write would cross (none with REX / M2EX): a character's skill over 10,
        Rome's age over 120, a trait with more than 10 levels - each a Script Error, the game stops."""
        from .limits import engine_of, game_kind
        from .strat import character_walls, trait_level_walls
        if engine_of(self.mod):
            return []
        out, kind = [], game_kind(self.mod)
        for path, f in self.files.items():
            if path not in changed:
                continue
            base = os.path.basename(path).lower()
            old = TextFile.load(path).texts() if os.path.exists(path) else []
            if base == "descr_strat.txt":
                had = set(character_walls(old, kind))
                for w in [w for w in character_walls(f.texts(), kind) if w not in had][:8]:
                    out.append("descr_strat.txt: the game stops ('%s'); the original exe takes no more" % w)
            elif base == "export_descr_character_traits.txt":
                had = set(trait_level_walls(old))
                for name, n in [w for w in trait_level_walls(f.texts()) if w not in had]:
                    out.append("%s: the trait %s has %d levels - the game stops ('Too many levels for trait(%s). Max "
                               "is 10.')" % (base, name, n, name))
        return out

    def _engine_takes(self, names):
        """REX / M2EX place another faction's army standalone on a taken tile (their reader, exe study 2026-10-14);
        two of ONE faction stay refused (not shown to be softened)."""
        from .limits import engine_of
        factions = [f for _, f in names]
        return bool(engine_of(self.mod)) and len(set(factions)) == len(factions)

    def tile_notes(self):
        """Armies of different factions on one tile that REX / M2EX take (placed standalone): said, not refused."""
        from .strat import Strat, shared_army_tiles
        out = []
        changed = self.changed_files()
        for path, f in self.files.items():
            if os.path.basename(path).lower() != "descr_strat.txt" or path not in changed:
                continue
            was = shared_army_tiles(Strat(TextFile.load(path))) if os.path.exists(path) else {}
            for xy, names in sorted(shared_army_tiles(Strat(f)).items()):
                if set(names) - set(was.get(xy, [])) and self._engine_takes(names):
                    out.append("%s share tile %d, %d - the engine places one of them standalone there (the original "
                               "game would stop)" % (" and ".join("%s (%s)" % n for n in names), xy[0], xy[1]))
        return out

    def _no_empty_army(self):
        """Refused before anything is written: what crash_problems names (Preview has said it already)."""
        bad = self.crash_problems()
        if bad:
            raise WriteError("\n".join(bad) + "\n\nNothing was changed.")

    def apply(self):
        from .limits import keep_up
        for fn in list(BEFORE):              # may stop the write before anything is done (WriteError)
            fn(self)
        keep_up(self)                       # REX / M2EX: max_factions follows the factions, silently (limits.py)
        from . import lnt
        lnt.keep_up(self)                   # the faction-select screen: a slot for every playable faction (lnt.py)
        from . import emergence
        emergence.keep_up(self)             # a 'comes later' faction given a town starts alive (emergence.py)
        self._no_empty_army()
        self.stale_bins()
        self.stale_sounds()
        self._whole_map_folders()
        sm = self.mod.file("sm_factions")
        if sm and sm in self.files and self.touched(sm):   # Rome: a 'faction destroyed' picture for every faction
            # (eventimages.py) - only when the faction list is really changed or the mod's own
            from . import eventimages
            eventimages.keep_up(self)
        for f in self.files.values():           # a single-byte file given letters it cannot hold: said, not a stop
            odd = f.unplain()
            if odd and f.dump() != self.originals.get(f.path):
                self.note(f, "letters this file cannot hold (%s) written as their nearest plain letter - the game "
                             "reads this file in a one-byte code page; the names players read can carry them in the "
                             "text files" % " ".join(odd))
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
                if (path not in self.originals or path in self.borrowed) and not os.path.exists(path):
                    created.append(rel.replace("\\", "/"))     # a new picture / the mod's copy of a game file: Restore
                    continue                                    # removes it
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


def _drop_backup(bdir):
    """A backup that was put back goes (the user, 2026-10-07: 'why keep all these _restored folders if I undid it');
    one that cannot go now (a file held open) is renamed *_restored and taken away by clean_restored later."""
    try:
        shutil.rmtree(bdir)
    except OSError:
        if os.path.isdir(bdir):
            shutil.move(bdir, bdir + "_restored")


def clean_restored(mod):
    """Take away the *_restored folders older versions left in the backups folders (backups already put back:
    nothing reads them). Returns how many went."""
    gone = 0
    for name in BACKUP_DIRS:
        root = os.path.join(os.path.dirname(mod.data), name)
        if not os.path.isdir(root):
            continue
        for n in os.listdir(root):
            d = os.path.join(root, n)
            if n.endswith("_restored") and os.path.isfile(os.path.join(d, "manifest.json")):
                try:
                    shutil.rmtree(d)
                    gone += 1
                except OSError:
                    pass
    return gone


def delete_backups(mod):
    """Tools > Settings > Delete this mod's backups: every backup folder of the mod goes (after a yes) - the files
    stay as they are now, only the way back is gone. Returns how many went."""
    gone = 0
    for b in backups(mod):
        try:
            shutil.rmtree(b)
            gone += 1
        except OSError:
            pass
    return gone + clean_restored(mod)


MAP_SOURCES = ("descr_regions.txt", "descr_terrain.txt", "water_surface.tga")


def _drop_built_maps(mod, root, manifest):
    """The map.rwm the game built from a write's map pictures goes when the write is undone - else the game reads the
    undone map from it (a tester, 2026-10-22: Undo of Map from zero left the island's map.rwm). One the backup put
    back stays."""
    back = {os.path.normcase(os.path.join(root, rel)) for rel in manifest.get("modified", [])}
    folders = set()
    for rel in manifest.get("modified", []) + manifest.get("created", []):
        n = os.path.basename(rel).lower()
        if n.startswith("map_") or n in MAP_SOURCES:
            folders.add(os.path.dirname(os.path.join(root, rel)))
    if folders:
        folders.add(os.path.join(mod.data, "world", "maps", "base"))
    for d in folders:
        rwm = os.path.join(d, "map.rwm")
        if os.path.isfile(rwm) and os.path.normcase(rwm) not in back:
            remove_file(rwm)


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
        _drop_built_maps(mod, root, manifest)
        p = bdir
        _drop_backup(bdir)               # undone: its copies are the files as they are now - nothing left to keep
    except OSError as e:                        # a file held by the game, the disk full...: the backup stays whole
        words = str(e) if isinstance(e, WriteError) else plain(getattr(e, "filename", None) or p, e) or \
            "%s: %s" % (type(e).__name__, e)
        raise WriteError("%s\n\nRestore stopped half way; the backup %s is kept whole - Restore it again once the "
                         "file is free (the files already put back are put back again, nothing is lost)."
                         % (words.replace("then Apply again", "then Restore again"), os.path.basename(bdir))) from e
    return manifest


# ---- kept plans: a window's changes kept for the session's one write (App.session_add) ----
def merge_lines(base, ours, theirs):
    """ours and theirs both grew from base (lists of lines): theirs with ours' changes laid over it, the way two
    people's edits of one file come together. Changes to different lines both stay; the same lines changed both
    ways (differently) -> ValueError naming the line. ours unchanged -> theirs; theirs unchanged -> ours."""
    import difflib
    if ours == base:
        return list(theirs)
    if theirs == base:
        return list(ours)

    def changes(new):
        return [(i1, i2, new[j1:j2]) for tag, i1, i2, j1, j2 in
                difflib.SequenceMatcher(None, base, new, autojunk=False).get_opcodes() if tag != "equal"]
    mine, other = changes(ours), changes(theirs)
    for a1, a2, a_new in mine:
        for b1, b2, b_new in other:
            touch = max(a1, b1) < min(a2, b2) or (a1 == b1 and (a1 == a2 or b1 == b2)) or \
                (a1 == a2 and b1 < a1 < b2) or (b1 == b2 and a1 < b1 < a2)
            both_insert = a1 == a2 == b1 == b2               # two additions at one place (the end of a file):
            if touch and not both_insert and (a1, a2, a_new) != (b1, b2, b_new):   # theirs, then ours
                raise ValueError("line %d was changed twice in this session, two different ways" % (min(a1, b1) + 1))
    # walk base once, taking each line from theirs' side and laying ours' changes over it
    other_at = {b1: (b2, b_new) for b1, b2, b_new in other}
    mine_at = {a1: (a2, a_new) for a1, a2, a_new in mine}
    out, i = [], 0
    while i <= len(base):
        if i in mine_at:
            a2, a_new = mine_at.pop(i)
            if i in other_at and other_at[i] == (a2, a_new):
                other_at.pop(i)                       # the same change made twice: once
            elif i in other_at and other_at[i][0] == i:   # theirs inserts here too
                b_new = other_at.pop(i)[1]
                # the one that goes on with the lines above it (a unit after an army's units) first, else theirs:
                # a town's new garrison and a new agent written at the end of one faction block left the units
                # under the agent - the game stopped reading the factions there (Keapon_Laffin, 2026-10-22)
                if a2 == i and _goes_on(base[i - 1] if i else None, a_new) and \
                        not _goes_on(base[i - 1] if i else None, b_new):
                    out += a_new
                    a_new = b_new
                else:
                    out += b_new
            out += a_new
            if a2 > i:
                i = a2
                continue
        if i in other_at:
            b2, b_new = other_at.pop(i)
            out += b_new
            if b2 > i:
                i = b2
                continue
        if i < len(base):
            out.append(base[i])
        i += 1
    return out


def _goes_on(above, lines):
    """lines begin with the same first word as the line above them - they go on with it (more units of one army)."""
    from .textio import tokens
    first = next((x for x in lines if x.strip()), None)
    if above is None or first is None:
        return False
    a, b = tokens(above)[:1], tokens(first)[:1]
    return bool(a) and a == b


def rebased(plan):
    """The kept plan laid over the files as they are NOW (parts of the same write before it may have changed
    some): every edited text file merged line by line (merge_lines), its backup what the disk holds now. A picture
    changed on the disk since the plan was made cannot be laid over - ValueError. The plan itself is changed."""
    for path, f in list(plan.files.items()):
        base = plan.originals[path]
        now = _read(path) if os.path.exists(path) else base
        if now == base:
            continue
        mine = f.dump()
        theirs = TextFile.from_bytes(path, now)
        try:
            lines = merge_lines(TextFile.from_bytes(path, base).raw, TextFile.from_bytes(path, mine).raw, theirs.raw)
        except ValueError as e:
            raise ValueError("%s: %s - keep this window's changes again (it reads the file as it is now)"
                             % (plan.mod.rel(path), e))
        plan.files[path] = TextFile(path, lines, theirs.encoding, theirs.bom)
        plan.originals[path] = now
    for path in plan.binaries:
        was = getattr(plan, "disk_before", {}).get(path, "?")
        now = _read(path) if os.path.exists(path) else None
        if was != "?" and now != was and was is not None and now is not None and \
                path.lower().endswith(".modeldb"):         # a modeldb is text: laid over model by model (#294)
            from .modeldb import ModelDBError, merged
            try:
                plan.binaries[path] = merged(was.decode("latin-1"), plan.binaries[path].decode("latin-1"),
                                             now.decode("latin-1")).encode("latin-1")
            except (ValueError, ModelDBError) as e:
                raise ValueError("%s: %s - keep this window's changes again (it reads the file as it is now)"
                                 % (plan.mod.rel(path), e))
            plan.disk_before[path] = now
            continue
        if was != "?" and now != was:
            raise ValueError("%s was changed by another part of this write - keep this window's changes again"
                             % plan.mod.rel(path))
    return plan


def kept_texts(plans):
    """{path: TextFile} - the text files as the kept plans (in their order) will leave them, read in memory: each
    laid over the ones before it the way the write does it (merge_lines); nothing written. A part that clashes with
    the ones before it is left out here (the write says it in words). The windows read the mod so (App.kept_view):
    what was kept for Apply is seen in them before the write."""
    out = {}
    for plan in plans:
        for path, f in plan.files.items():
            cur = out.get(path)
            if cur is None:
                now = _read(path) if os.path.exists(path) else plan.originals[path]
                cur = TextFile.from_bytes(path, now)
            base = TextFile.from_bytes(path, plan.originals[path]).raw
            try:
                lines = merge_lines(base, TextFile.from_bytes(path, f.dump()).raw, cur.raw)
            except ValueError:
                continue
            out[path] = TextFile(path, lines, cur.encoding, cur.bom)
    return out


def keep(plan):
    """Mark a plan as kept for a later write: what its pictures are on the disk now (rebased checks it)."""
    plan.disk_before = {p: (_read(p) if os.path.exists(p) else None) for p in plan.binaries}
    return plan
