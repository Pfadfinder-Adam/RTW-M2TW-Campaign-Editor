"""The editor checks itself: `campaign_editor.py selfcheck [report file]` (CI runs the built exe with it before an
exe is handed out). Every module of the editor imports; the files that travel inside the exe are there and read (the
game manifests, the engines' catalogue, the built-in add-ons, the window's icons); the tiny mod (minimod.py) loads,
Check mod files runs on it, a new faction is written and Restore puts every byte back. A file left out of the exe,
or a module that no longer imports, is found before a release - not by someone who downloaded it."""

import gzip
import json
import os
import sys
import tempfile
import traceback


REFERENCE = ("rtw_gold_steam_manifest.json.gz", "rex_manifest.json.gz", "m2tw_manifest.json.gz",
             "engine_catalogue.json.gz")
MIN_MODULES = 40                     # fewer found means the module list itself could not be read
WINDOW_ONLY = ("theme",)             # modules of the window not named gui*: they need tkinter
OPTIONAL = ("PIL", "tkinter", "numpy")   # a Python may lack them (pictures / the window / the quick 3D view);
                                         # the exe must have all three


def run(window=True):
    """(ok, [lines]) - window False leaves out the modules of the window (a Python without tkinter)."""
    lines, bad = [], []

    def ok(what):
        lines.append("ok    " + what)

    def fail(what, err):
        bad.append(what)
        lines.append("FAIL  %s: %s" % (what, err))

    _modules(ok, fail, window)
    _bundled(ok, fail)
    _tiny_mod(ok, fail)
    lines.append("")
    lines.append("SELF-CHECK %s (%d problem%s)" % ("PASSED" if not bad else "FAILED", len(bad),
                                                   "" if len(bad) == 1 else "s"))
    return not bad, lines


def built_list():
    """The modules the source had when the exe was built (modules.txt, written by the build next to the exe's own
    files); [] outside the exe or when the build wrote none."""
    base = getattr(sys, "_MEIPASS", None)
    try:
        with open(os.path.join(base, "modules.txt"), encoding="utf-8") as fh:
            return [n.strip() for n in fh if n.strip() and n.strip() != "__main__"]
    except (OSError, TypeError):
        return []


def _modules(ok, fail, window):
    import importlib
    import pkgutil
    import campaign_editor
    names = sorted(m.name for m in pkgutil.iter_modules(campaign_editor.__path__) if m.name != "__main__")
    if len(names) < MIN_MODULES:
        fail("the editor's modules", "only %d found" % len(names))
    for n in sorted(set(built_list()) - set(names)):       # in the source when it was built, not in the exe (the
        fail("module %s" % n, "not in the exe")             # tester, 2026-10-22: 'No module named gui_modzero')
    done, lacking = 0, []
    for n in names:
        if not window and (n.startswith("gui") or n in WINDOW_ONLY):
            continue
        try:
            importlib.import_module("campaign_editor." + n)
            done += 1
        except ModuleNotFoundError as e:
            if (e.name or "").split(".")[0] in OPTIONAL and not getattr(sys, "frozen", False):
                lacking.append(n)                           # this Python lacks Pillow / tkinter / NumPy; the exe never does
            else:
                fail("module %s" % n, "%s: %s" % (type(e).__name__, e))
        except Exception as e:                              # noqa: BLE001 - every failure is reported
            fail("module %s" % n, "%s: %s" % (type(e).__name__, e))
    ok("%d modules import" % done + (" (not tried: %s - this Python lacks Pillow / tkinter / NumPy)" % ", ".join(lacking)
                                      if lacking else ""))
    try:                                                    # the graphics card's 3D map (glmap): its OpenGL loader
        import glcontext
        import moderngl  # noqa: F401
        glcontext.default_backend()
        ok("moderngl and its OpenGL loader import (Maps > 3D on the graphics card)")
    except Exception as e:                                  # noqa: BLE001 - the exe must have it, a Python may not
        if getattr(sys, "frozen", False):
            fail("moderngl", "%s: %s" % (type(e).__name__, e))
    try:                                                    # REX / M2EX packs of version 4 (zstd) - gamepacks
        import zstandard  # noqa: F401
        ok("zstandard imports (packs of REX / M2EX, version 4)")
    except Exception as e:                                  # noqa: BLE001
        if getattr(sys, "frozen", False):
            fail("zstandard", "%s: %s" % (type(e).__name__, e))


def _bundled(ok, fail):
    from .scan import reference_dir
    for name in REFERENCE:
        p = os.path.join(reference_dir(), name)
        try:
            with gzip.open(p, "rb") as fh:
                data = json.loads(fh.read().decode("utf-8"))
            if not data:
                raise ValueError("empty")
            ok(name)
        except Exception as e:                              # noqa: BLE001
            fail(name, e)
    try:
        from . import enginedocs as ED
        ED._BUILTIN.clear()
        b = ED.builtin()
        counts = {e: sum(len(v) for v in b[e].values()) for e in ED.ENGINES}
        if not all(counts.values()):
            raise ValueError("empty: %s" % counts)
        ok("the engines' catalogue (%s)" % ", ".join("%s %d" % kv for kv in counts.items()))
    except Exception as e:                                  # noqa: BLE001
        fail("the engines' catalogue", e)
    from . import addons as AD
    try:
        for a in AD.ADDONS:
            if AD.is_files(a):
                a.code()                        # its module is in the exe (a test-mod run: 'No module named upkeep')
                continue
            text = a.template()
            if not text.strip() or AD.from_script(text, a.file) is None:
                raise ValueError("%s is empty" % a.file)
        ok("%d built-in add-ons" % len(AD.ADDONS))
    except Exception as e:                                  # noqa: BLE001
        fail("the built-in add-ons", e)
    try:
        from . import credits as CR
        found = [k for k, _ in CR.blocks(CR.read()) if k == "heading"]
        if len(found) < 3:
            raise ValueError("CREDITS.md has %d section(s)" % len(found))
        ok("the credits (%d sections)" % len(found))
    except Exception as e:                                  # noqa: BLE001
        fail("the credits (CREDITS.md)", e)
    try:
        from . import themes as TH
        own = [t for t in TH.available() if not t["own"]]
        if len(own) < 2:
            raise ValueError("%d in %s" % (len(own), TH.builtin_dir()))
        ok("%d built-in themes" % len(own))
    except Exception as e:                                  # noqa: BLE001
        fail("the built-in themes", e)
    try:
        folder = os.path.dirname(AD.assets_dir())          # assets/ (the add-ons are assets/addons)
        icons = [n for n in os.listdir(folder) if n.lower().startswith("icon") and n.endswith(".png")]
        if not icons:
            raise ValueError("no icon_*.png in %s" % folder)
        ok("%d icons" % len(icons))
    except Exception as e:                                  # noqa: BLE001
        fail("the window's icons", e)


def _tiny_mod(ok, fail):
    from . import minimod
    from .build import build
    from .check import check_mod
    from .moddata import ModData
    from .plan import backups, restore
    with tempfile.TemporaryDirectory() as root:
        try:
            data = minimod.make(root)
            mod = ModData(data)
            if [n for n, _ in mod.factions()] != ["alpha", "slave"] or mod.campaigns() != ["test"]:
                raise ValueError("read %s / %s" % (mod.factions(), mod.campaigns()))
            ok("the tiny mod loads")
            check_mod(mod, "test")
            ok("Check mod files runs")
            before = _snapshot(data)
            plan = build(mod, "test", "alpha", "beta", {"start": {"regions": ["B_R"], "leader": {"name": "Boris"}}})
            bdir = plan.apply()
            if _snapshot(data) == before or "beta" not in [n for n, _ in ModData(data).factions()]:
                raise ValueError("the new faction was not written")
            restore(mod, bdir)
            if _snapshot(data) != before or backups(mod):
                raise ValueError("Restore did not put every byte back")
            ok("a new faction written and Restore puts every byte back")
        except Exception as e:                              # noqa: BLE001
            fail("the tiny mod", "%s\n%s" % (e, traceback.format_exc(limit=3)))


def _snapshot(folder):
    out = {}
    for dp, _, fs in os.walk(folder):
        for n in fs:
            with open(os.path.join(dp, n), "rb") as fh:
                out[os.path.relpath(os.path.join(dp, n), folder)] = fh.read()
    return out


def main(out=None):
    """Runs it; the report goes to out (a file) and to the console when there is one. Returns 0 / 1."""
    import importlib.util
    good, lines = run(importlib.util.find_spec("tkinter") is not None)
    text = "\n".join(lines) + "\n"
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    if sys.stdout is not None:                    # the exe has no console: the file is the report
        try:
            sys.stdout.write(text)
        except (OSError, ValueError):
            pass
    return 0 if good else 1
