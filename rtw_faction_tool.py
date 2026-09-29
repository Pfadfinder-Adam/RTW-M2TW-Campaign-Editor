"""Entry point: no arguments opens the window, arguments run the command line.

    python rtw_faction_tool.py                      (window)
    python rtw_faction_tool.py list --data PATH     (command line, see README)
"""
import sys

from faction_tool.cli import main as cli_main

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(cli_main())
    try:
        import tkinter  # noqa: F401 - the window; some Linux Pythons come without it
    except ImportError:
        sys.exit("The window needs tkinter, which this Python lacks.\n"
                 "  Debian / Ubuntu / Mint:  sudo apt install python3-tk python3-pil python3-pil.imagetk\n"
                 "  Fedora:                  sudo dnf install python3-tkinter python3-pillow-tk\n"
                 "  Arch:                    sudo pacman -S tk python-pillow\n"
                 "then run it again with: python3 rtw_faction_tool.py")
    from faction_tool.gui import main as gui_main
    gui_main()
