"""Builds the editor's one-file exe with Nuitka: the Python code is compiled to C and then to machine code, so the exe
holds no .py or .pyc files to unpack and decompile (PyInstaller, used before, packed the bytecode as it is). Docstrings
are left out too (--python-flag=no_docstrings; the editor never reads them). The files the editor reads lie at the
same places as in the PyInstaller exe (campaign_editor/bundle.py: files_dir).

    python .github/build_exe.py          -> dist/RTW-M2TW-Campaign-Editor.exe (on Linux: dist/RTW-M2TW-Campaign-Editor)

Run from the repo's root (CI: build.yml and release.yml)."""

import glob
import os
import pkgutil
import subprocess
import sys

NAME = "RTW-M2TW-Campaign-Editor"
WINDOWS = sys.platform.startswith("win")


def main():
    import campaign_editor
    # the source's module list goes inside the exe: the self-check names every module the exe lacks
    with open("modules.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(m.name for m in pkgutil.iter_modules(campaign_editor.__path__))))
    data = [("modules.txt", "modules.txt"), ("CREDITS.md", "CREDITS.md")]
    data += [(p, "reference/" + os.path.basename(p)) for p in sorted(glob.glob("docs/reference/*.json.gz"))]
    data += [(p, "assets/" + os.path.basename(p)) for p in sorted(glob.glob("assets/*.png"))]
    for sub in ("addons", "lang", "themes"):
        data += [(p, "assets/%s/%s" % (sub, os.path.basename(p))) for p in sorted(glob.glob("assets/%s/*" % sub))
                 if os.path.isfile(p)]
    cmd = [sys.executable, "-m", "nuitka", "--onefile", "--assume-yes-for-downloads",
           "--output-dir=dist", "--output-filename=" + NAME + (".exe" if WINDOWS else ""),
           "--enable-plugin=tk-inter",
           "--include-package=campaign_editor",           # importlib-loaded modules too (the self-check imports all)
           "--include-package=glcontext",                 # moderngl picks its OpenGL loader at run time
           "--include-module=moderngl", "--include-module=zstandard",
           "--python-flag=no_docstrings",
           "--report=dist/nuitka-report.xml"]
    cmd += ["--include-data-files=%s=%s" % (src, dst) for src, dst in data]
    if WINDOWS:
        cmd += ["--windows-console-mode=disable", "--windows-icon-from-ico=assets/icon.ico",
                "--company-name=Pfadfinder", "--product-name=RTW & M2TW Campaign Editor",
                "--file-description=RTW & M2TW Campaign Editor", "--product-version=%s" % version(),
                "--copyright=Copyright (C) 2026 Pfadfinder (Adam), GPL-3.0"]
    cmd.append("campaign_editor.py")
    print(" ".join(cmd), flush=True)
    return subprocess.call(cmd)


def version():
    """The version for the exe's file properties: digits and dots only (Windows wants 1-4 numbers)."""
    import re
    with open("campaign_editor/gui.py", encoding="utf-8") as fh:
        m = re.search(r'^VERSION = "([^"]+)"', fh.read(), re.M)
    nums = [n for n in (m.group(1) if m else "0").split(".") if n.isdigit()][:4]
    return ".".join(nums or ["0"])


if __name__ == "__main__":
    sys.path.insert(0, os.getcwd())
    sys.exit(main())
