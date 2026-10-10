"""Check mod files' answer: the problems worst first, grouped by when the game would meet them (it would not start,
the campaign loads with something lost, in battle, while playing), each with a button to the place that puts it
right; the whole report one button away."""

import os
import tkinter as tk
from tkinter import ttk

from . import theme
from .check import fix_of, grouped


def go(app, place):
    """Open the place a problem is put right in (check.FIXES' places)."""
    if place == "load":
        app.load()
    elif place == "engine_files":
        app.copy_engine_files()
    elif place == "rules":
        app.campaign_rules()
    elif place == "events":
        app.events_window()
    else:
        app.v_work.set(place)
        app.work_changed()
    app.lift()


def open_problems(app, problems, report, title="Check mod files", extra=(), complete=None):
    """The problems window (App.check). problems: the problem lines; report: the whole text (Full report);
    complete: (faction, rows, fine) of factioncheck.complete when a faction is picked."""
    w = tk.Toplevel(app)
    w.title(title)
    w.geometry("900x600")
    bar = ttk.Frame(w, padding=6)
    bar.pack(side="bottom", fill="x")
    ttk.Button(bar, text="Full report...", command=lambda: app.show_text(title, report)).pack(side="left")
    for label, cmd in extra:
        ttk.Button(bar, text=label, command=cmd).pack(side="left", padx=(theme.BUTTON_GAP, 0))
    ttk.Button(bar, text="Close", command=w.destroy).pack(side="right")
    p = theme.palette()
    t = tk.Text(w, wrap="word", relief="flat", padx=14, pady=10, cursor="arrow", font=("", 10),
                background=p["bg"], foreground=p["fg"], highlightthickness=0, spacing1=2, spacing3=2)
    sb = ttk.Scrollbar(w, orient="vertical", command=t.yview)
    t.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    t.pack(fill="both", expand=True)
    t.tag_configure("title", font=("", 12, "bold"), spacing3=6)
    t.tag_configure("heading", font=("", 10, "bold"), spacing1=12, spacing3=4)
    t.tag_configure("item", lmargin1=12, lmargin2=12)
    if not problems:
        t.insert("end", "No problems found.\n", "title")
        t.insert("end", "Full report... below says what was read.\n", "item")
    else:
        t.insert("end", "%d problem(s), worst first - by when the game would meet them\n" % len(problems), "title")
        for n, (heading, these) in enumerate(grouped(problems)):
            t.insert("end", "%d. %s\n" % (n + 1, heading[:1].upper() + heading[1:]), "heading")
            for msg in these:
                t.insert("end", "•  " + msg, "item")
                fix = fix_of(msg)
                if fix:
                    t.insert("end", "  ", "item")
                    t.window_create("end", window=ttk.Button(t, text=fix[0], cursor="hand2",
                                                             command=lambda pl=fix[1]: go(app, pl)))
                t.insert("end", "\n", "item")
    if complete:
        faction, rows, fine = complete
        gaps = [r for r in rows if r[1] == "gap"]
        notes = [r for r in rows if r[1] != "gap"]
        t.insert("end", "\nIs %s complete?\n" % faction, "title")
        t.insert("end", "%d file(s) name it as the other factions do. %s\n" % (fine, (
            "Missing where EVERY other faction is named - the game or its screens will miss it:" if gaps else
            "Nothing missing that every other faction has.")), "item")
        for rel, _, _, like in gaps:
            t.insert("end", "\u2022  %s%s\n" % (rel, " - copy %s's lines there and rename them" % like if like
                                                  else ""), "item")
        if notes:
            t.insert("end", "Not named where most (not all) factions are - real, working factions go without "
                            "these too: %s\n" % ", ".join(os.path.basename(r[0]) for r in notes), "item")
    t.configure(state="disabled")
    return w
