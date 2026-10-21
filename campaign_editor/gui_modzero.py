"""Tools > A mod from zero, step by step (the user, 2026-10-21: 'make a mod from zero easier - a map, then a faction,
then more'): the steps in their order in one small window - your own mod folder, the map, the factions, their units
and buildings, Check mod files, the game - each with what it is, how far it is now and the button that does it. The
window does nothing itself: each button opens the editor's own work for that step."""

import os
import tkinter as tk
from tkinter import ttk

from . import theme

TITLE = "A mod from zero"


def state(app):
    """[(step key, done?, words)] for the mod loaded now."""
    from .newmod import marker
    mod = getattr(app, "mod", None)
    if mod is None:
        return [("folder", False, "load the game (Mod / Browse..., then Load) - then make your own mod folder")]
    out = []
    own = marker(os.path.dirname(os.path.abspath(mod.data))) is not None
    out.append(("folder", own, ("your own mod folder: %s" % os.path.basename(os.path.dirname(os.path.abspath(
        mod.data)))) if own else "the game itself (or a mod not made here) is loaded - make your own folder first"))
    try:
        regions = len(mod.regions(app.v_campaign.get()))
    except Exception:
        regions = 0
    out.append(("map", regions > 0, "the campaign's map has %d region(s)" % regions))
    strat = getattr(app, "strat", None)
    facs = [fb.name for fb in (strat.factions if strat else []) if fb.name != "slave"]
    out.append(("factions", len(facs) > 0, "%d faction(s) in the campaign%s" % (
        len(facs), (": " + ", ".join(facs[:6]) + (" ..." if len(facs) > 6 else "")) if facs else "")))
    out.append(("units", None, "your factions' units and buildings - as many as you like"))
    out.append(("check", None, "what the game would stumble on, said in plain words"))
    out.append(("game", None, "start a NEW campaign with the mod"))
    return out


STEPS = [
    ("folder", "1. Your own mod folder", "a copy of the game to work on - the game itself stays clean",
     [("New mod folder...", "new_mod")]),
    ("map", "2. The map", "keep the campaign's map, or start a new small one: an island, its regions, towns, a port",
     [("Map from zero...", "map_zero"), ("Open the map", "map")]),
    ("factions", "3. Factions", "a new faction is a clean copy of one you pick (its colours, units, buildings, "
                                "models, cards - no triggers, no events); or one taken from another mod",
     [("New faction", "new"), ("Change a faction", "edit")]),
    ("units", "4. Units and buildings", "new units and buildings from nothing or from others, their cards and "
                                         "pictures", [("Units", "units"), ("Buildings", "buildings")]),
    ("check", "5. Check mod files", "before the game: every file read, mistakes said where to fix them",
     [("Check mod files", "check")]),
    ("game", "6. Start the game", "a NEW campaign - a saved game keeps the old map and factions",
     [("Start the game", "start")]),
]


def go(app, what):
    """A step's button: the editor's own work or window for it."""
    if what == "new_mod":
        app.new_mod()
    elif what == "map_zero":
        _work(app, "map")
        app.map_from_zero()
    elif what == "check":
        app.check()
    elif what == "start":
        app.start_game()
    else:
        _work(app, what)


def _work(app, key):
    try:
        app.v_work.set(key)
        app.work_changed()
    except Exception:
        pass


def open_window(app):
    w = tk.Toplevel(app)
    w.title(TITLE)
    w.transient(app)
    f = ttk.Frame(w, padding=12)
    f.pack(fill="both", expand=True)
    ttk.Label(f, text="The steps of a mod made from zero, in their order. Each button opens the editor's own place "
                      "for it; come back here for the next step (this window stays open).",
              wraplength=560, justify="left").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
    status = {}
    for r, (key, title, what, buttons) in enumerate(STEPS, start=1):
        ttk.Label(f, text=title, font=("", 10, "bold")).grid(row=2 * r - 1, column=0, sticky="w", pady=(6, 0))
        bf = ttk.Frame(f)
        bf.grid(row=2 * r - 1, column=2, sticky="e", pady=(6, 0))
        for text, act in buttons:
            ttk.Button(bf, text=text, command=lambda a=act: go(app, a)).pack(side="left", padx=(theme.BUTTON_GAP, 0))
        ttk.Label(f, text=what, foreground="#555", wraplength=380, justify="left").grid(row=2 * r, column=0,
                                                                                      columnspan=2, sticky="w")
        status[key] = ttk.Label(f, text="", foreground="#1c6b1c", wraplength=200, justify="left")
        status[key].grid(row=2 * r, column=2, sticky="e")

    def refresh(e=None):
        for key, done, words in state(app):
            if key in status:
                status[key].configure(text=("✓ " if done else "") + words,
                                      foreground="#1c6b1c" if done else ("#555" if done is None else "#a05a00"))
    refresh()
    w.bind("<FocusIn>", refresh)
    ttk.Button(f, text="Close", command=w.destroy).grid(row=2 * len(STEPS) + 1, column=2, sticky="e", pady=(12, 0))
    return w


__all__ = ["open_window", "state", "STEPS", "go"]
