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
OPTIONAL = ("PIL", "tkinter")        # a Python may lack them (pictures / the window); the exe must have both


def run(window=True):
    """(ok, [lines]) - window False leaves out the modules of the window (a Python without tkinter)."""
    lines, bad = [], []

    def ok(what):
        lines.append("ok    " + what)

    def fail(what, err):
        bad.append(what)
        lines.append("FAIL  %s: %s" % (what, err))

    _modules(ok, fail, window)
    _bundled(ok, fail, window)
    _tiny_mod(ok, fail)
    lines.append("")
    lines.append("SELF-CHECK %s (%d problem%s)" % ("PASSED" if not bad else "FAILED", len(bad),
                                                   "" if len(bad) == 1 else "s"))
    return not bad, lines


def _modules(ok, fail, window):
    import importlib
    import pkgutil
    import campaign_editor
    names = sorted(m.name for m in pkgutil.iter_modules(campaign_editor.__path__) if m.name != "__main__")
    if len(names) < MIN_MODULES:
        fail("the editor's modules", "only %d found" % len(names))
    done, lacking = 0, []
    for n in names:
        if not window and (n.startswith("gui") or n in WINDOW_ONLY):
            continue
        try:
            importlib.import_module("campaign_editor." + n)
            done += 1
        except ModuleNotFoundError as e:
            if (e.name or "").split(".")[0] in OPTIONAL and not getattr(sys, "frozen", False):
                lacking.append(n)                           # this Python lacks Pillow / tkinter; the exe never does
            else:
                fail("module %s" % n, "%s: %s" % (type(e).__name__, e))
        except Exception as e:                              # noqa: BLE001 - every failure is reported
            fail("module %s" % n, "%s: %s" % (type(e).__name__, e))
    ok("%d modules import" % done + (" (not tried: %s - this Python lacks Pillow / tkinter)" % ", ".join(lacking)
                                      if lacking else ""))


def _bundled(ok, fail, window):
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
    try:
        from . import addons as AD
        for a in AD.ADDONS:
            text = a.template()
            if not text.strip() or AD.from_script(text, a.file) is None:
                raise ValueError("%s is empty" % a.file)
        ok("%d built-in add-ons" % len(AD.ADDONS))
    except Exception as e:                                  # noqa: BLE001
        fail("the built-in add-ons", e)
    if window:
        try:
            from .gui import assets_dir
            icons = [n for n in os.listdir(assets_dir()) if n.lower().startswith("icon") and n.endswith(".png")]
            if not icons:
                raise ValueError("no icon_*.png in %s" % assets_dir())
            ok("%d icons" % len(icons))
        except Exception as e:                              # noqa: BLE001
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
