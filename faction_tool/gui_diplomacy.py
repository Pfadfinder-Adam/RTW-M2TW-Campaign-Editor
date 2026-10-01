"""The Diplomacy tab: how the faction and every other one stand towards each
other at the start - both ways, in the two kinds of lines the game reads:
Rome core_attitudes (numbers) + faction_relationships (numbers, alliance, war);
Medieval II faction_standings (-1.0 .. 1.0) + faction_relationships (alliance, war)."""

import tkinter as tk
from tkinter import ttk

from .diplomacy import LEVELS, NEUTRAL, STANDINGS, STANCE_WORDS, parse, text_of, word
from .gui_util import hint

ALLIANCE, WAR = STANCE_WORDS["allied_to"], STANCE_WORDS["at_war_with"]
HEADS = {"core_attitudes": ("AI feeling: they to it", "AI feeling: it to them"),
         "faction_standings": ("AI feeling: they to it", "AI feeling: it to them"),
         "faction_relationships": ("Start: they to it", "Start: it to them")}
COLUMNS = (("core_attitudes", "me", HEADS["core_attitudes"][0]), ("core_attitudes", "them", HEADS["core_attitudes"][1]),
           ("faction_relationships", "me", HEADS["faction_relationships"][0]),
           ("faction_relationships", "them", HEADS["faction_relationships"][1]))
HELP = {
    "core_attitudes": "AI feeling (core_attitudes): how a faction's AI feels about the other. A number, lower is "
                      "better: -10 own (the Roman houses), 0 allied, 100 friendly, 200 neutral, 310 wary, 410 dislike, "
                      "600 enemies (everyone towards the rebels). Pick one or type a number.",
    "faction_standings": "AI feeling (faction_standings): how a faction's AI feels about the other, from -1.0 (hate - "
                         "everyone towards the rebels) to 1.0 (love). Pick one or type a number.",
    "faction_relationships": "Start (faction_relationships): 'alliance' - allied from the first turn, 'war' - at war "
                             "from the first turn (both ways: picking one side sets the other too). Rome also takes a "
                             "number here, like the AI feeling. Neutral = no line.",
}


def choices(kind, medieval):
    if kind == "faction_standings":
        return [NEUTRAL] + ["%s %s" % (text_of(v), w) for v, w in STANDINGS]
    stances = [ALLIANCE, WAR]
    if kind == "faction_relationships" and medieval:
        return [NEUTRAL] + stances
    return [NEUTRAL] + stances + ["%d %s" % (v, w) for v, w in LEVELS]


def colour(value):
    """Green (friends) to red (enemies), grey for neutral - numbers (lower is better), standings (higher is
    better) and alliance / war alike."""
    if value is None:
        return "#d8d8d8"
    if isinstance(value, str):
        return "#6fc46f" if value == "allied_to" else "#e06060"
    if isinstance(value, float):
        value = 600 - (value + 1) * 300          # 1.0 -> 0, 0 -> 300, -1.0 -> 600
    if value <= 100:
        return "#8fd18f"
    if value <= 320:
        return "#e8e08a"
    if value <= 450:
        return "#f0b070"
    return "#e88080"


def shown(value):
    if value is None:
        return NEUTRAL
    if isinstance(value, str):
        return STANCE_WORDS.get(value, value)
    return "%s %s" % (text_of(value), word(value))


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
        self.kinds, self.medieval = ("core_attitudes", "faction_relationships"), False

    def load(self, me, others, base, changes, names, on_change, kinds=None, medieval=False):
        """base: {(kind, from, to): value} as the file (or the template) has it, with
        the faction as 'me'; changes: the dict of picks, kept by the caller; kinds: the game's two kinds of
        lines (diplomacy.kinds)."""
        self.me, self.others, self.base, self.set = me, list(others), base, changes
        self.names, self.on_change = names, on_change
        self.kinds, self.medieval = tuple(kinds or ("core_attitudes", "faction_relationships")), medieval
        self.title.configure(text="Diplomacy of %s" % me)
        self.redraw()

    def value(self, key):
        return self.set[key] if key in self.set else self.base.get(key)

    def redraw(self):
        for w in self.inner.winfo_children():
            w.destroy()
        if not self.me:
            return
        columns = [(k, side, HEADS[k][0 if side == "me" else 1]) for k in self.kinds for side in ("me", "them")]
        for j, h in enumerate(["Faction", ""]):
            ttk.Label(self.inner, text=h, font=("", 9, "bold")).grid(row=0, column=j, sticky="w", padx=4, pady=2)
        for j, (kind, _, h) in enumerate(columns):
            cell = ttk.Frame(self.inner)
            cell.grid(row=0, column=2 + j, sticky="w", padx=4, pady=2)
            ttk.Label(cell, text=h, font=("", 9, "bold")).pack(side="left")
            hint(cell, HELP[kind]).pack(side="left")
        q = self.v_find.get().strip().lower()
        row = 1
        for other in self.others:
            label = self.names.get(other, "")
            if q and q not in other.lower() and q not in label.lower():
                continue
            ttk.Label(self.inner, text=other).grid(row=row, column=0, sticky="w", padx=4)
            ttk.Label(self.inner, text=label, foreground="#555").grid(row=row, column=1, sticky="w", padx=4)
            for j, (kind, side, _) in enumerate(columns):
                key = (kind, other, "me") if side == "me" else (kind, "me", other)
                v = self.value(key)
                var = tk.StringVar(value=shown(v))
                changed = key in self.set                 # a changed cell has a blue frame
                cell = tk.Frame(self.inner, bg=colour(v), padx=3, pady=2, highlightthickness=2 if changed else 0,
                                highlightbackground="#2050ff", highlightcolor="#2050ff")
                cell.grid(row=row, column=2 + j, sticky="w", padx=3, pady=1)
                cb = ttk.Combobox(cell, textvariable=var, values=choices(kind, self.medieval), width=13)
                cb.pack()
                cb.bind("<<ComboboxSelected>>", lambda ev, k=key, var=var: self.picked(k, var.get()))
                cb.bind("<Return>", lambda ev, k=key, var=var: self.picked(k, var.get()))
                cb.bind("<FocusOut>", lambda ev, k=key, var=var: self.picked(k, var.get(), quiet=True))
            row += 1

    def picked(self, key, text, quiet=False):
        kind = key[0]
        try:
            v = parse(text, kind)
            if self.medieval and kind == "faction_relationships" and not (v is None or isinstance(v, str)):
                raise ValueError(text)               # Medieval II: alliance / war only
        except ValueError:
            if not quiet:
                self.bell()
            return
        old = self.value(key)
        if v == old and type(v) is type(old):
            return
        if getattr(self, "before", None):
            self.before()                           # the window remembers the state for Undo
        keys = [key]
        # an alliance or a war holds both ways: the other side follows (and leaves with it)
        if kind == "faction_relationships" and (isinstance(v, str) or isinstance(old, str)):
            back = (kind, key[2], key[1])
            if isinstance(v, str) or self.value(back) == old:
                keys.append(back)
        for k in keys:
            if v == self.base.get(k) and type(v) is type(self.base.get(k)):
                self.set.pop(k, None)
            else:
                self.set[k] = v
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
