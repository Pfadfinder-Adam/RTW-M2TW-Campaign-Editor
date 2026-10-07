"""Every script the engine runs from script/modules - REX for Rome, M2EX for Medieval II: their own script/main.nut
requires every .nut there ('scripting.listModules("modules")'). Ours (the add-ons, the Module builder's modules) and
anyone's are listed with what each is; one can be turned off and on again (x.nut <-> x.nut.off: only .nut files are
required, nothing is lost), deleted, or its settings changed in place (the UPPER_CASE 'local' lines at its top,
found as the Add-ons panel finds them). Every write goes through a Plan: Preview, a backup, Restore."""

import os
import types

from . import addons as AD
from .moddata import ModData

OFF = ".off"
EXTS = (".nut", ".lua")
# the line the test mod (selftest) writes at the end of every script it puts into the game's script/modules: the
# test mod's folder can be thrown away, its scripts stay in the game's folder - this finds them again
TEST_MARK = "// @put_in_by CE_Test - the editor's test mod (Add-ons > Scripts in the game takes it out)"
TEST_NAMES = ("ce_test_",)          # the test mod's own modules before the mark existed (CE Test module ...)


def folders(mod):
    """[(folder, runs)]: the script/modules folder the engine runs for this mod first (as an add-on is put in),
    then the mod's own and the game's when they are other folders and exist (runs: the folder's main.nut requires
    its modules)."""
    out = []

    def add(folder, runs):
        if folder and os.path.isdir(folder) and \
                os.path.normcase(os.path.abspath(folder)) not in [os.path.normcase(os.path.abspath(f)) for f, _ in out]:
            out.append((folder, runs))
    main = os.path.dirname(AD.target(mod, types.SimpleNamespace(file="x.nut")))
    if os.path.isdir(main):
        out.append((main, True))
    root = os.path.dirname(os.path.abspath(mod.data))
    add(os.path.join(root, "script", "modules"), AD.loads_modules(root))
    try:
        from .newmod import game_of
        game = game_of(mod.data)
    except Exception:
        game = None
    if game:
        add(os.path.join(game, "script", "modules"), AD.loads_modules(game))
    return out


class Script:
    """One script file in a modules folder."""

    def __init__(self, path, runs):
        self.path, self.runs = path, runs
        name = os.path.basename(path)
        self.on = not name.lower().endswith(OFF)
        self.file = name[:-len(OFF)] if not self.on else name           # its name when it runs
        self.folder = os.path.dirname(path)
        st = os.stat(path)
        self.size, self.mtime = st.st_size, st.st_mtime
        with open(path, "rb") as fh:
            self.text = fh.read().decode("utf-8", "replace")
        self.lua = self.file.lower().endswith(".lua")
        known = next((a for a in AD.library() if a.file.lower() == self.file.lower()), None)
        self.addon = known or AD.from_script(self.text, self.file, path)
        self.ours = known is not None and not known.own                  # one the editor brings
        self.added = known is not None and known.own                     # one added to the Add-ons list
        self.built = "// @recipe" in self.text                           # made in the Module builder
        self.test = TEST_MARK.split(" - ")[0] in self.text or self.file.lower().startswith(TEST_NAMES)
        try:
            self.values = AD.read_settings(self.addon, self.text)
        except Exception:
            self.values = {}

    @property
    def title(self):
        return self.addon.title

    @property
    def kind(self):
        if self.lua:
            return "an older Lua script (the engines run .nut modules)"
        if self.test:
            return "put in by the test mod"
        if self.ours:
            return "an add-on of the editor"
        if self.built:
            return "made in the Module builder"
        if self.added:
            return "an add-on you added"
        return "someone's script"

    def plan_mod(self, mod=None):
        """The ModData whose folder holds this script (the backups go beside it): <root>/script/modules ->
        <root>/data; the loaded mod when that data folder cannot be read alone (Medieval II's game data: the rest is
        in packs - the mod's backup holds the game-folder file too)."""
        try:
            return ModData(os.path.join(os.path.dirname(os.path.dirname(self.folder)), "data"))
        except (FileNotFoundError, OSError):
            if mod is None:
                raise
            return mod


def scripts(mod):
    """[Script] of every .nut / .lua (and turned-off .off copy) in folders(mod), the running folder first, by name."""
    out = []
    for folder, runs in folders(mod):
        for n in sorted(os.listdir(folder), key=str.lower):
            low = n.lower()
            base = low[:-len(OFF)] if low.endswith(OFF) else low
            p = os.path.join(folder, n)
            if base.endswith(EXTS) and os.path.isfile(p):
                try:
                    out.append(Script(p, runs))
                except OSError:
                    continue
    return out


def _bytes(s):
    with open(s.path, "rb") as fh:
        return fh.read()


def plan_switch(plan, s, on):
    """The script turned on (x.nut.off -> x.nut) or off (x.nut -> x.nut.off): the same bytes under the other name."""
    if s.on == on:
        return None
    new = os.path.join(s.folder, s.file + ("" if on else OFF))
    if os.path.exists(new):
        raise ValueError("%s is there already - delete one of the two first" % os.path.basename(new))
    plan.binary(new, _bytes(s))
    plan.delete(s.path, "turned %s: %s" % ("on" if on else "off", os.path.basename(new)))
    plan.notes.append((os.path.basename(new), "%s turned %s (the engine runs only .nut files)" % (
        s.title, "on" if on else "off")))
    return new


def plan_delete(plan, s):
    plan.delete(s.path, "the script %s deleted (Restore puts it back)" % s.title)


def test_scripts(mod):
    """[Script] the test mod put in (its mark at the end, or a ce_test_ name), turned off ones too."""
    return [s for s in scripts(mod) if s.test]


def plan_take_out_test(plan, items):
    """Every script of the test mod deleted (Restore puts them back)."""
    for s in items:
        plan.delete(s.path, "put in by the test mod: %s (Restore puts it back)" % s.title)
    return len(items)


def plan_settings(plan, s, values):
    """Its settings written into its own lines (the rest byte for byte). Raises ValueError in plain words."""
    problems = AD.check(s.addon, values)
    if problems:
        raise ValueError("; ".join(problems))
    text = AD.render(s.addon, s.text, values)
    if text == s.text:
        return False
    plan.binary(s.path, text.encode("utf-8"))
    changed = [x.label for x in s.addon.settings if x.var in values and s.values.get(x.var) != values[x.var]]
    plan.notes.append((os.path.basename(s.path), "%s: %s" % (s.title, ", ".join(changed) or "settings")))
    return True
