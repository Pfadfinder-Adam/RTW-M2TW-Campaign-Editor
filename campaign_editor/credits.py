"""The credits: CREDITS.md - the page on GitHub (beside the CHANGELOG and the ROADMAP) and, inside the exe, the
Tools > Credits... window. One file for both: whoever is thanked on the page is thanked in the editor."""

import os
import re
import sys

PAGE = "https://github.com/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor/blob/main/CREDITS.md"
RE_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
RE_MARK = re.compile(r"\*\*|__|(?<![\w*])[*_](?=\S)|(?<=\S)[*_](?![\w*])|`")


def path():
    """CREDITS.md: inside the exe (PyInstaller unpacks it beside the program's files), else the repo's root."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "CREDITS.md")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CREDITS.md")


def read():
    with open(path(), encoding="utf-8") as fh:
        return fh.read()


def plain(text):
    """A line of the page without its Markdown marks (bold, italics, code, links keep their words)."""
    return RE_MARK.sub("", RE_LINK.sub(r"\1", text))


def blocks(text):
    """The page as [(kind, words)]: 'title' (#), 'heading' (##), 'item' (- ...), 'quote' (> ...), 'text' - a
    paragraph or an item running over several lines is one block."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append(("gap", ""))
            continue
        if s.startswith("## "):
            out.append(("heading", plain(s[3:])))
        elif s.startswith("# "):
            out.append(("title", plain(s[2:])))
        elif s.startswith(("- ", "* ")):
            out.append(("item", plain(s[2:])))
        elif s.startswith(">"):
            if out and out[-1][0] == "quote":
                out[-1] = ("quote", out[-1][1] + " " + plain(s[1:].strip()))
            else:
                out.append(("quote", plain(s[1:].strip())))
        elif out and out[-1][0] in ("item", "text", "quote") and line[:1] in (" ", "\t") or \
                out and out[-1][0] == "text":
            out[-1] = (out[-1][0], out[-1][1] + " " + plain(s))
        else:
            out.append(("text", plain(s)))
    return [b for b in out if b[0] != "gap"]
