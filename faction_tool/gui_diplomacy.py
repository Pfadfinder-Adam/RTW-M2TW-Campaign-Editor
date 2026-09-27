"""The Diplomacy tab: how the faction and every other one stand towards each
other at the start - core_attitudes both ways and faction_relationships."""

import tkinter as tk
from tkinter import ttk

from .diplomacy import LEVELS, word

NEUTRAL = "neutral"
CHOICES = [NEUTRAL] + ["%d %s" % (v, w) for v, w in LEVELS]
COLUMNS = (("core_attitudes", "me", "They are to it"), ("core_attitudes", "them", "It is to them"),
           ("faction_relationships", "me", "Start: they to it"), ("faction_relationships", "them", "Start: it to them"))


def colour(value):
    """Green (friends) to red (enemies), grey for neutral."""
    if value is None:
        return "#d8d8d8"
    if value <= 100:
        return "#8fd18f"
    if value <= 320:
        return "#e8e08a"
    if value <= 450:
        return "#f0b070"
    return "#e88080"


def parse(text):
    """'310 wary' / '310' / 'neutral' -> 310 / None; ValueError for anything else."""
    t = text.strip()
    if not t or t == NEUTRAL:
        return None
    return int(t.split()[0])


class DiplomacyEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        top = ttk.Frame(self, padding=(0, 0, 0, 4))
        top.pack(fill="x")
        self.title = ttk.Label(top, text="Pick the faction (Faction tab)", font=("", 10, "bold"))
        self.title.pack(side="left")
        ttk.Label(top, text="   Find").pack(side="left")
        self.v_find = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.v_find, width=16)
        e.pack(side="left", padx=4)
        e.bind("<KeyRelease>", lambda ev: self.redraw())
        ttk.Button(top, text="Undo all changes", command=self.reset).pack(side="right")
        ttk.Label(self, foreground="#555", justify="left", text=(
            "Lower is better: -10 own (the Roman houses), 90-100 friends, 310 wary, 410 dislike, 600 enemies "
            "(everyone towards the rebels). Neutral = no line. Pick a value or type a number. "
            "core_attitudes: how a faction's AI feels; faction_relationships: where they start.")).pack(fill="x")
        canvas = tk.Canvas(self, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind("<Configure>", lambda ev: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Enter>", lambda ev: canvas.bind_all("<MouseWheel>",
                    lambda x: canvas.yview_scroll(int(-x.delta / 120), "units")))
        canvas.bind("<Leave>", lambda ev: canvas.unbind_all("<MouseWheel>"))
        self.canvas = canvas
        self.me, self.others, self.base, self.set = None, [], {}, {}
        self.names = {}
        self.on_change = None

    def load(self, me, others, base, changes, names, on_change):
        """base: {(kind, from, to): value} as the file (or the template) has it, with
        the faction as 'me'; changes: the dict of picks, kept by the caller."""
        self.me, self.others, self.base, self.set = me, list(others), base, changes
        self.names, self.on_change = names, on_change
        self.title.configure(text="Diplomacy of %s" % me)
        self.redraw()

    def value(self, key):
        return self.set[key] if key in self.set else self.base.get(key)

    def redraw(self):
        for w in self.inner.winfo_children():
            w.destroy()
        if not self.me:
            return
        head = ["Faction", ""] + [c[2] for c in COLUMNS]
        for j, h in enumerate(head):
            ttk.Label(self.inner, text=h, font=("", 9, "bold")).grid(row=0, column=j, sticky="w", padx=4, pady=2)
        q = self.v_find.get().strip().lower()
        row = 1
        for other in self.others:
            label = self.names.get(other, "")
            if q and q not in other.lower() and q not in label.lower():
                continue
            ttk.Label(self.inner, text=other).grid(row=row, column=0, sticky="w", padx=4)
            ttk.Label(self.inner, text=label, foreground="#555").grid(row=row, column=1, sticky="w", padx=4)
            for j, (kind, side, _) in enumerate(COLUMNS):
                key = (kind, other, "me") if side == "me" else (kind, "me", other)
                v = self.value(key)
                var = tk.StringVar(value=NEUTRAL if v is None else "%d %s" % (v, word(v)))
                changed = key in self.set                 # a changed cell has a blue frame
                cell = tk.Frame(self.inner, bg=colour(v), padx=3, pady=2, highlightthickness=2 if changed else 0,
                                highlightbackground="#2050ff", highlightcolor="#2050ff")
                cell.grid(row=row, column=2 + j, sticky="w", padx=3, pady=1)
                cb = ttk.Combobox(cell, textvariable=var, values=CHOICES, width=13)
                cb.pack()
                cb.bind("<<ComboboxSelected>>", lambda ev, k=key, var=var: self.picked(k, var.get()))
                cb.bind("<Return>", lambda ev, k=key, var=var: self.picked(k, var.get()))
                cb.bind("<FocusOut>", lambda ev, k=key, var=var: self.picked(k, var.get(), quiet=True))
            row += 1

    def picked(self, key, text, quiet=False):
        try:
            v = parse(text)
        except ValueError:
            if not quiet:
                self.bell()
            return
        if v == self.value(key) and key not in self.set:
            return
        if getattr(self, "before", None):
            self.before()                           # the window remembers the state for Undo
        if v == self.base.get(key):
            self.set.pop(key, None)
        else:
            self.set[key] = v
        if self.on_change:
            self.on_change()
        self.after_idle(self.redraw)

    def reset(self):
        if getattr(self, "before", None):
            self.before()
        self.set.clear()
        if self.on_change:
            self.on_change()
        self.redraw()
