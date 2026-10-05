"""Tools > Credits...: the people the editor owes its shape to - the author, who helped a lot, the testers, the
supporters (CREDITS.md, the same page as on GitHub)."""

import tkinter as tk
import webbrowser
from tkinter import ttk

from . import credits as CR, theme

APP = "RTW & M2TW Campaign Editor"


def open_credits(app):
    """The Credits window (App.credits_window)."""
    try:
        parts = CR.blocks(CR.read())
    except OSError as e:
        parts = [("title", "Credits"), ("text", "The credits page could not be read: %s" % e)]
    w = tk.Toplevel(app)
    w.title("Credits")
    w.transient(app)
    w.geometry("640x560")
    bar = ttk.Frame(w, padding=8)
    bar.pack(side="bottom", fill="x")
    ttk.Button(bar, text="The page on GitHub", command=lambda: webbrowser.open(CR.PAGE)).pack(side="left")
    ttk.Button(bar, text="Close", command=w.destroy).pack(side="right")
    p = theme.palette()
    t = tk.Text(w, wrap="word", relief="flat", padx=18, pady=14, cursor="arrow", font=("", 10),
                background=p["bg"], foreground=p["fg"], highlightthickness=0, spacing2=2)
    sb = ttk.Scrollbar(w, orient="vertical", command=t.yview)
    t.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    t.pack(fill="both", expand=True)
    t.tag_configure("title", font=("", 16, "bold"), spacing3=8)
    t.tag_configure("heading", font=("", 11, "bold"), spacing1=12, spacing3=4)
    t.tag_configure("text", spacing3=4)
    t.tag_configure("item", lmargin1=12, lmargin2=26, spacing3=4)
    t.tag_configure("quote", lmargin1=18, lmargin2=18, font=("", 10, "italic"), foreground=p["muted"], spacing3=4)
    for kind, words in parts:
        t.insert("end", ("•  " if kind == "item" else "") + words + "\n", kind)
    t.configure(state="disabled")
    return w
