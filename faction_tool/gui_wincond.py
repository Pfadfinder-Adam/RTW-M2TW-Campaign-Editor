"""The Faction tab's Victory block: what the player must do to win the long and the short campaign
(descr_win_conditions.txt, see wincond.py) - regions to hold, how many to take, factions to outlive, and in Rome
the Senate's goals (become emperor / take Rome)."""

import copy
import tkinter as tk
from tkinter import ttk

from .gui_util import hint
from .wincond import _empty, problems, same

GOAL_WORDS = {"": "(none)", "imperator": "be emperor", "take_rome": "take Rome"}
HELP = ("What the PLAYER must do to win (descr_win_conditions.txt; the AI does not read it). Long and short "
        "campaign each: Hold - regions to own at the end; Take - how many regions in all; Outlive - factions that "
        "must be gone. Rome also has the Senate's goals: become emperor, or take Rome. A region or a faction that "
        "does not exist makes the game crash when this faction is played - the tool refuses it.")


def pick_many(parent, title, items, chosen, groups=None, on_map=None):
    """A list to tick names from: items [(name, label)]; returns the picked names in order, or None (Cancel).
    Many at once (a tester: one by one is too many clicks): a drag over rows ticks them all, Shift-click ticks a
    run, 'Tick all shown' takes what Find shows; groups {label: [names]} ticks a whole group (a faction's regions);
    on_map(picked) -> picked or None opens the map to click them there."""
    w = tk.Toplevel(parent)
    w.title(title)
    w.transient(parent.winfo_toplevel())
    w.geometry("420x520")
    top = ttk.Frame(w, padding=6)
    top.pack(fill="x")
    ttk.Label(top, text="Find").pack(side="left")
    v_find = tk.StringVar()
    ent = ttk.Entry(top, textvariable=v_find)
    ent.pack(side="left", fill="x", expand=True, padx=4)
    btns = ttk.Frame(w, padding=6)
    btns.pack(side="bottom", fill="x")
    lb = tk.Listbox(w, selectmode="multiple", exportselection=False)
    sb = ttk.Scrollbar(w, orient="vertical", command=lb.yview)
    lb.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    lb.pack(fill="both", expand=True, padx=(6, 0))
    picked = list(chosen)
    shown = []

    def fill(*_, fresh=False):
        q = v_find.get().strip().lower()
        if not fresh:                       # (fresh: picked was set from outside - the rows' ticks are old)
            sync()
        lb.delete(0, "end")
        shown[:] = [(n, l) for n, l in items if not q or q in n.lower() or q in l.lower()]
        for k, (n, l) in enumerate(shown):
            lb.insert("end", n if not l or l == n else "%s - %s" % (n, l))
            if n in picked:
                lb.selection_set(k)

    def sync():
        sel = {shown[k][0] for k in lb.curselection()} if shown else None
        if sel is None:
            return
        for n, _ in shown:
            if n in sel and n not in picked:
                picked.append(n)
            elif n not in sel and n in picked:
                picked.remove(n)

    result = []

    def ok():
        sync()
        result.append(list(picked))
        w.destroy()
    ttk.Button(btns, text="OK", command=ok).pack(side="right")
    ttk.Button(btns, text="Cancel", command=w.destroy).pack(side="right", padx=4)
    ttk.Button(btns, text="Clear", command=lambda: (picked.clear(), lb.selection_clear(0, "end"))).pack(side="left")
    more = ttk.Frame(w, padding=(6, 0))
    more.pack(side="bottom", fill="x")
    ttk.Button(more, text="Tick all shown", command=lambda: (lb.selection_set(0, "end"), sync())).pack(side="left")
    ttk.Button(more, text="Untick shown", command=lambda: (lb.selection_clear(0, "end"), sync())).pack(
        side="left", padx=4)
    if groups:
        v_grp = tk.StringVar(value="tick a whole group...")
        cg = ttk.Combobox(more, textvariable=v_grp, values=sorted(groups), state="readonly", width=20)
        cg.pack(side="left", padx=4)

        def group(_e=None):
            sync()
            for n in groups.get(v_grp.get(), []):
                if n not in picked and any(n == x for x, _ in items):
                    picked.append(n)
            v_grp.set("tick a whole group...")
            fill(fresh=True)
        cg.bind("<<ComboboxSelected>>", group)
    if on_map:
        def by_map():
            sync()
            got = on_map(list(picked))
            if got is not None:
                picked[:] = got
                fill(fresh=True)
        ttk.Button(more, text="On the map...", command=by_map).pack(side="right")

    # a drag over the rows ticks (or unticks, from a ticked row) every row it passes; Shift-click a run
    drag = {}

    def press(e):
        k = lb.nearest(e.y)
        drag.update(start=k, on=not lb.selection_includes(k), last=k)
        if e.state & 1 and "anchor" in drag:                     # Shift: the run from the last click
            a, b = sorted((drag["anchor"], k))
            lb.selection_set(a, b)
            sync()
            return "break"
        drag["anchor"] = k

    def motion(e):
        if "start" not in drag:
            return
        k = lb.nearest(e.y)
        if k == drag.get("last"):
            return
        drag["last"] = k
        a, b = sorted((drag["start"], k))
        (lb.selection_set if drag["on"] else lb.selection_clear)(a, b)
        sync()
        return "break"
    lb.bind("<ButtonPress-1>", press, add="+")
    lb.bind("<B1-Motion>", motion)
    lb.bind("<ButtonRelease-1>", lambda e: (drag.pop("start", None), sync()), add="+")
    v_find.trace_add("write", fill)
    fill()
    ent.focus_set()
    w.grab_set()
    parent.wait_window(w)
    return result[0] if result else None


class VictoryBox(ttk.LabelFrame):
    def __init__(self, master, on_change=None, before=None):
        super().__init__(master, text="Victory (what the player must do to win)")
        self.on_change, self.before = on_change, before          # before: the window remembers it for Undo
        self.base = self.cond = self.faction = None
        self.regions, self.factions, self.medieval = [], [], False
        self.rows = {}
        head = ttk.Frame(self)
        head.grid(row=0, column=0, columnspan=8, sticky="w", padx=4)
        self.l_head = ttk.Label(head, text="", foreground="#555")
        self.l_head.pack(side="left")
        hint(head, HELP).pack(side="left")
        ttk.Label(head, text="the player's goals - hover the ?", foreground="#777").pack(side="left")
        for r, (part, label) in enumerate((("long", "Long"), ("short", "Short")), start=1):
            ttk.Label(self, text=label, font=("", 9, "bold")).grid(row=r * 2 - 1, column=0, sticky="w", padx=4)
            v_goal = tk.StringVar()
            cb_goal = ttk.Combobox(self, textvariable=v_goal, state="readonly", width=12,
                                   values=list(GOAL_WORDS.values()))
            cb_goal.bind("<<ComboboxSelected>>", lambda ev, p=part: self._goal(p))
            b_hold = ttk.Button(self, command=lambda p=part: self._pick(p, "hold"))
            v_take = tk.StringVar()
            sp = ttk.Spinbox(self, from_=0, to=999, width=4, textvariable=v_take,
                             command=lambda p=part: self._take(p))
            sp.bind("<KeyRelease>", lambda ev, p=part: self._take(p))
            b_out = ttk.Button(self, command=lambda p=part: self._pick(p, "outlive"))
            a, b = r * 2 - 1, r * 2
            ttk.Label(self, text="Hold").grid(row=a, column=1, sticky="e", padx=(6, 2))
            b_hold.grid(row=a, column=2, sticky="we", pady=1)
            ttk.Label(self, text="Take").grid(row=a, column=3, sticky="e", padx=(6, 2))
            sp.grid(row=a, column=4, sticky="w")
            ttk.Label(self, text="Outlive").grid(row=b, column=1, sticky="e", padx=(6, 2))
            b_out.grid(row=b, column=2, sticky="we", pady=(1, 4))
            l_goal = ttk.Label(self, text="Goal")
            l_goal.grid(row=b, column=3, sticky="e", padx=(6, 2))
            cb_goal.grid(row=b, column=4, sticky="w", pady=(1, 4))
            self.rows[part] = {"goal": v_goal, "cb_goal": cb_goal, "l_goal": l_goal, "hold": b_hold,
                               "take": v_take, "outlive": b_out}
        self.l_problems = ttk.Label(self, text="", foreground="#c03030", wraplength=420, justify="left")
        self.l_problems.grid(row=5, column=0, columnspan=8, sticky="w", padx=4)
        self.columnconfigure(2, weight=1)

    # ------------------------------------------------------------------
    def load(self, cond, regions, factions, medieval, faction=None):
        """cond: {'long', 'short'} as the file has it (None: the faction has no block yet); regions / factions:
        [(name, label)] to pick from."""
        self.base = copy.deepcopy(cond) if cond else {"long": _empty(), "short": _empty()}
        self.cond = copy.deepcopy(self.base)
        self.regions, self.factions, self.medieval, self.faction = regions, factions, medieval, faction
        self.l_head.configure(text=("" if cond else "%s has no victory block yet - set one, or the game may "
                                    "crash when it is played. " % (faction or "The faction")))
        self.show()

    def changed(self):
        return self.cond is not None and not same(self.cond, self.base)

    def get(self):
        """The conditions to write, or None when nothing changed."""
        return copy.deepcopy(self.cond) if self.changed() else None

    def show(self):
        if self.cond is None:
            return
        names = dict(self.regions)
        for part, w in self.rows.items():
            c = self.cond[part]
            w["hold"].configure(text=self._short(c["hold"], names) or "(none) ...")
            w["outlive"].configure(text=self._short(c["outlive"], dict(self.factions)) or "(none) ...")
            w["take"].set("" if c["take"] is None else str(c["take"]))
            goal = c["goals"][0] if c["goals"] else ""
            w["goal"].set(GOAL_WORDS.get(goal, goal))
            for k in ("cb_goal", "l_goal"):
                (w[k].grid_remove if self.medieval else w[k].grid)()
        regions = {n for n, _ in self.regions}
        factions = {n for n, _ in self.factions}
        self.l_problems.configure(text="\n".join(problems(self.cond, regions, factions, self.medieval)))

    @staticmethod
    def _short(names, labels):
        if not names:
            return ""
        first = ", ".join(names[:2])
        return first + (" +%d" % (len(names) - 2) if len(names) > 2 else "") + " ..."

    def _before(self):
        if self.before:
            self.before()

    def _changed(self):
        self.show()
        if self.on_change:
            self.on_change()

    def _pick(self, part, what):
        if self.cond is None:
            return
        items = self.regions if what == "hold" else self.factions
        groups, map_pick = None, None
        app = getattr(self, "app", None)
        if what == "hold" and app is not None:
            try:                                 # 'tick a whole group': the regions each faction holds now
                groups = {}
                for r, f in app.owners_after().items():
                    groups.setdefault("held by %s" % f, []).append(r)
            except Exception:
                groups = None

            def on_the_map(now):
                from .gui_mappick import pick_regions
                return pick_regions(self, app, now, "Hold these regions - click towns on the map")
            map_pick = on_the_map
        got = pick_many(self, "Hold these regions" if what == "hold" else "Outlive these factions", items,
                        self.cond[part][what], groups=groups, on_map=map_pick)
        if got is not None and got != self.cond[part][what]:
            self._before()
            self.cond[part][what] = got
            self._changed()

    def _take(self, part):
        if self.cond is None:
            return
        t = self.rows[part]["take"].get().strip()
        v = int(t) if t.isdigit() and int(t) > 0 else None
        if v != self.cond[part]["take"]:
            self._before()
            self.cond[part]["take"] = v
            self._changed()

    def _goal(self, part):
        if self.cond is None:                     # no faction read yet (no mod loaded)
            return
        back = {v: k for k, v in GOAL_WORDS.items()}
        g = back.get(self.rows[part]["goal"].get(), "")
        goals = [g] if g else []
        if goals != self.cond[part]["goals"]:
            self._before()
            self.cond[part]["goals"] = goals
            self._changed()
