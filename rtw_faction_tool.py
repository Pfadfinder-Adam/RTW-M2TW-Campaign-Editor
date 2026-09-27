"""Entry point: no arguments opens the window, arguments run the command line.

    python rtw_faction_tool.py                      (window)
    python rtw_faction_tool.py list --data PATH     (command line, see README)
"""
import sys

from faction_tool.cli import main as cli_main

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(cli_main())
    from faction_tool.gui import main as gui_main
    gui_main()
