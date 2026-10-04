"""The Diplomacy tab: how the faction and every other one stand towards each other at the start.

Per faction, in plain words:
- Status at the start (faction_relationships, both games): neutral, alliance or war - one pick sets both ways;
- the AI's feeling, both ways (Rome core_attitudes, a number, lower is better; Medieval II faction_standings,
  -1.0 .. 1.0) - every value shown with what it means, e.g. "600 (enemies)".
Picking a status pulls the feelings along (diplomacy.feeling_for): an alliance lifts them to the allied level, a war
drops them to the enemies', neutral takes them out; they can still be set by hand afterwards."""

import tkinter as tk
from tkinter import ttk

from .diplomacy import LEVELS, NEUTRAL, STANDINGS, STANCE_WORDS, feeling_for, parse, text_of, word
from .gui_util import hint, tip

ALLIANCE, WAR = STANCE_WORDS["allied_to"], STANCE_WORDS["at_war_with"]
STATUS_HELP = ("Status at the start (faction_relationships): what holds on the first turn - neutral (no line), "
               "alliance or war. One pick sets it both ways, as the game keeps it. The AI feelings move along: an "
               "alliance lifts them to the allied level, a war drops them to the enemies' level, neutral takes them "
               "out - set them by hand afterwards if you like.")
FEEL_HELP = {
    "core_attitudes": "AI feeling (core_attitudes): how a faction's AI likes the other. Lower is better: -10 own "
                      "house (the Roman houses), 0 allied, 100 friendly, 200 neutral, 310 wary, 410 dislike, "
                      "600 enemies (everyone towards the rebels). Pick one or type a number.",
    "faction_standings": "AI feeling (faction_standings): how a faction's AI likes the other, from -1.0 (hate - "
                         "everyone towards the rebels) to 1.0 (love). Pick one or type a number.",
}
TOP_TEXT = {
    "core_attitudes": "Status = alliance / war on the first turn.  AI feeling: lower is better (0 allied ... 600 "
                      "enemies).",
    "faction_standings": "Status = alliance / war on the first turn.  AI feeling: -1.0 hate ... 1.0 love.",
}
# kept for the map and older callers
COLUMNS = (("core_attitudes", "me", "AI feeling: they to it"), ("core_attitudes", "them", "AI feeling: it to them"),
           ("faction_relationships", "me", "Start: they to it"), ("faction_relationships", "them", "Start: it to them"))


def shown(value):
    """A value in plain words: 'neutral', 'alliance', 'war', '600 (enemies)', '-0.45 (dislike)'."""
    if value is None:
        return NEUTRAL
    if isinstance(value, str):
        return STANCE_WORDS.get(value, value)
    return "%s (%s)" % (text_of(value), word(value))


def choices(kind, medieval):
    if kind == "faction_standings":
        return [NEUTRAL] + [shown(v) for v, _ in STANDINGS]
    if kind == "faction_relationships":
        return [NEUTRAL, ALLIANCE, WAR] + ([] if medieval else [shown(v) for v, _ in LEVELS])
    return [NEUTRAL] + [shown(v) for v, _ in LEVELS]


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
        self.l_top = ttk.Label(self, text="", foreground="#666")
        self.l_top.pack(fill="x")
        canvas = tk.Canvas(self, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind("<Configure>", lambda ev: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        from .gui_util import scroll_y, wheel
        wheel(canvas, scroll_y(canvas))
        self.canvas = canvas
        self.me, self.others, self.base, self.set = None, [], {}, {}
        self.names = {}
        self.on_change = None
        self.kinds, self.medieval = ("core_attitudes", "faction_relationships"), False

    def load(self, me, others, base, changes, names, on_change, kinds=None, medieval=False):
        """base: {(kind, from, to): value} as the file (or the template) has it, with
        the faction as 'me'; changes: the dict of picks, kept by the caller; kinds: the game's two kinds of
        lines (diplomacy.kinds: the AI feeling, then faction_relationships)."""
        self.me, self.others, self.base, self.set = me, list(others), base, changes
        self.names, self.on_change = names, on_change
        self.kinds, self.medieval = tuple(kinds or ("core_attitudes", "faction_relationships")), medieval
        self.title.configure(text="Diplomacy of %s" % me)
        self.l_top.configure(text=TOP_TEXT.get(self.kinds[0], ""))
        self.redraw()

    def value(self, key):
        return self.set[key] if key in self.set else self.base.get(key)

    def _head(self, column, text, help_text):
        cell = ttk.Frame(self.inner)
        cell.grid(row=0, column=column, sticky="w", padx=4, pady=2)
        ttk.Label(cell, text=text, font=("", 9, "bold")).pack(side="left")
        hint(cell, help_text).pack(side="left")

    def _cell(self, row, column, key, kind, value, note=""):
        changed = key in self.set or (kind == "faction_relationships" and (kind, key[2], key[1]) in self.set)
        cell = tk.Frame(self.inner, bg=colour(value), padx=3, pady=2, highlightthickness=2 if changed else 0,
                        highlightbackground="#2050ff", highlightcolor="#2050ff")   # a changed cell: blue frame
        cell.grid(row=row, column=column, sticky="w", padx=3, pady=1)
        var = tk.StringVar(value=shown(value))
        cb = ttk.Combobox(cell, textvariable=var, values=choices(kind, self.medieval),
                          width=14 if kind == "faction_relationships" else 16)
        cb.pack(side="left")
        if note:
            ttk.Label(cell, text=note, foreground="#333", background=colour(value)).pack(side="left", padx=(3, 0))
        handler = self.status_picked if kind == "faction_relationships" else self.picked
        cb.bind("<<ComboboxSelected>>", lambda ev, k=key, var=var: handler(k, var.get()))
        cb.bind("<Return>", lambda ev, k=key, var=var: handler(k, var.get()))
        cb.bind("<FocusOut>", lambda ev, k=key, var=var: handler(k, var.get(), quiet=True))
        return cb

    def redraw(self):
        for w in self.inner.winfo_children():
            w.destroy()
        if not self.me:
            return
        feel = self.kinds[0]
        ttk.Label(self.inner, text="Faction", font=("", 9, "bold")).grid(row=0, column=0, sticky="w", padx=4)
        self._head(2, "Status at the start", STATUS_HELP)
        self._head(3, "AI feeling: they to it", FEEL_HELP.get(feel, ""))
        self._head(4, "AI feeling: it to them", FEEL_HELP.get(feel, ""))
        q = self.v_find.get().strip().lower()
        row = 1
        for other in self.others:
            label = self.names.get(other, "")
            if q and q not in other.lower() and q not in label.lower():
                continue
            ttk.Label(self.inner, text=other).grid(row=row, column=0, sticky="w", padx=4)
            ttk.Label(self.inner, text=label, foreground="#555").grid(row=row, column=1, sticky="w", padx=4)
            mine, back = (("faction_relationships", "me", other), ("faction_relationships", other, "me"))
            v, vb = self.value(mine), self.value(back)
            note = "" if vb == v else "they: %s" % shown(vb)          # the file says it one way only
            cb = self._cell(row, 2, mine, "faction_relationships", v, note)
            if note:
                tip(cb, "The file has it one way only: %s to %s %s, %s to %s %s. A pick sets both ways."
                    % (self.me, other, shown(v), other, self.me, shown(vb)))
            self._cell(row, 3, (feel, other, "me"), feel, self.value((feel, other, "me")))
            self._cell(row, 4, (feel, "me", other), feel, self.value((feel, "me", other)))
            row += 1

    # ------------------------------------------------------------------
    def _put(self, key, v):
        base = self.base.get(key)
        if v == base and type(v) is type(base):
            self.set.pop(key, None)
        else:
            self.set[key] = v

    def _done(self):
        if self.on_change:
            self.on_change()
        self.after_idle(self.redraw)

    def picked(self, key, text, quiet=False):
        """An AI feeling picked or typed."""
        try:
            v = parse(text, key[0])
        except ValueError:
            if not quiet:
                self.bell()
            return
        old = self.value(key)
        if v == old and type(v) is type(old):
            return
        if getattr(self, "before", None):
            self.before()                           # the window remembers the state for Undo
        self._put(key, v)
        self._done()

    def status_picked(self, key, text, quiet=False):
        """The status at the start: set both ways, and the AI feelings pulled along."""
        kind, a, b = key
        try:
            v = parse(text, kind)
            if self.medieval and not (v is None or isinstance(v, str)):
                raise ValueError(text)               # Medieval II: alliance / war only
        except ValueError:
            if not quiet:
                self.bell()
            return
        back = (kind, b, a)
        if v == self.value(key) and v == self.value(back) and type(v) is type(self.value(key)):
            return
        if getattr(self, "before", None):
            self.before()
        self._put(key, v)
        self._put(back, v)
        if v is None or isinstance(v, str):
            feel = self.kinds[0]
            for k in ((feel, a, b), (feel, b, a)):
                self._put(k, feeling_for(feel, v, self.value(k)))
        self._done()

    def reset(self):
        if getattr(self, "before", None):
            self.before()
        self.set.clear()
        if self.on_change:
            self.on_change()
        self.redraw()
