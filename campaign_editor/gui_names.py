"""The name-list wizard: a faction's own men's names, surnames and women's names in three steps."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import scroll_body
from . import namelists as NL
from . import theme

STEPS = (
    ("characters", "Step 1 of 3 - men's names",
     "Every man of the faction takes one: the leader, heirs, generals, sons, agents."),
    ("surnames", "Step 2 of 3 - surnames (may stay empty)",
     "Given to the men after the first name ('Harun al-Rashid'). Empty = first names only, as Dacia's and "
     "Numidia's in vanilla Rome."),
    ("women", "Step 3 of 3 - women's names",
     "Wives, daughters and (Medieval II) princesses take one."),
)
FORMAT = ("Type or paste the names: one per line, or separated by commas (then a name may have spaces: "
          "'Abd al-Malik', 'of Sparta'). Without commas or new lines, spaces separate the names - type a name of "
          "several words with _ then ('of_Sparta'). The game wants no space inside a name, so the tool writes "
          "it with _ (as vanilla's 'of_Scaldis'; in the console: \"Gaius Julius_Caesar\") and shows it with "
          "spaces. Latin letters, digits, ' and - only. Duplicates are dropped.")


def shown(key):
    return key.replace("_", " ")


class NameListWizard:
    """app.name_list[who] = {pool: [names as shown]} on Done (pending, written with the next Apply)."""

    def __init__(self, app, who, faction_label, start=None):
        self.app, self.who = app, who
        mod = app.mod
        self.factions = [f for f, _ in mod.factions()]
        if start is None:
            start = {p: [shown(k) for k in v] for p, v in (mod.name_pool(who) or {}).items()}
        self.texts = {p: "\n".join(start.get(p) or []) for p, _, _ in STEPS}
        self.step = 0
        w = self.w = tk.Toplevel(app)
        w.title("Name list of %s" % faction_label)
        w.transient(app)
        w.geometry("740x560")
        frm = scroll_body(w, 10)          # resizable, scrolls when the window is lower than it
        self.l_title = ttk.Label(frm, font=("", 11, "bold"))
        self.l_title.pack(anchor="w")
        self.l_what = ttk.Label(frm, wraplength=700, justify="left")
        self.l_what.pack(anchor="w", pady=(2, 4))
        ttk.Label(frm, text=FORMAT, wraplength=700, justify="left", foreground="#666").pack(anchor="w")
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=4)
        ttk.Label(bar, text="Copy this step from").pack(side="left")
        self.v_from = tk.StringVar(value=who if who in self.factions else (app.v["template"].get().strip() or ""))
        from .gui_util import FactionBox
        FactionBox(bar, self.v_from, self.factions, app.shown_names(), width=24, state="readonly").pack(
            side="left", padx=4)
        ttk.Button(bar, text="Copy", command=self.copy_from).pack(side="left")
        ttk.Button(bar, text="Add from it", command=lambda: self.copy_from(add=True)).pack(side="left", padx=4)
        ttk.Button(bar, text="Clear", command=lambda: self.set_text("")).pack(side="left")
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True)
        self.t = tk.Text(box, wrap="word", height=14, undo=True)
        sb = ttk.Scrollbar(box, command=self.t.yview)
        self.t.configure(yscrollcommand=sb.set)
        self.t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.t.bind("<<Modified>>", self._changed)
        self.l_count = ttk.Label(frm, wraplength=700, justify="left")
        self.l_count.pack(anchor="w", pady=(4, 0))
        nav = ttk.Frame(frm)
        nav.pack(fill="x", pady=(8, 0))
        self.b_back = ttk.Button(nav, text="< Back", command=lambda: self.go(-1))
        self.b_back.pack(side="left")
        self.b_next = ttk.Button(nav, text="Next >", command=lambda: self.go(1))
        self.b_next.pack(side="left", padx=4)
        ttk.Button(nav, text="Cancel", command=w.destroy).pack(side="right")
        self.show()

    # ---- steps ----
    def pool(self):
        return STEPS[self.step][0]

    def show(self):
        p, title, what = STEPS[self.step]
        self.l_title.configure(text=title)
        self.l_what.configure(text=what)
        self.set_text(self.texts[p])
        self.b_back.state(["disabled"] if self.step == 0 else ["!disabled"])
        self.b_next.configure(text="Done" if self.step == len(STEPS) - 1 else "Next >")

    def set_text(self, text):
        self.t.delete("1.0", "end")
        self.t.insert("1.0", text)
        self._count()

    def _changed(self, *a):
        self.t.edit_modified(False)
        self._count()

    def _count(self):
        names = NL.parse(self.t.get("1.0", "end"))
        bad = [n for n in names if NL.RE_BAD_KEY.search(NL.key_of(n))]
        msg = "%d name(s)" % len(names)
        if bad:
            msg += " - not taken by the game: " + ", ".join(bad[:6]) + ("..." if len(bad) > 6 else "")
        self.l_count.configure(text=msg, foreground=theme.ink("#a33") if bad else "")

    def copy_from(self, add=False):
        f = self.v_from.get()
        if not f:
            return
        got = [shown(k) for k in (self.app.mod.name_pool(f) or {}).get(self.pool()) or []]
        if add:
            now = NL.parse(self.t.get("1.0", "end"))
            got = now + [n for n in got if n.lower() not in {x.lower() for x in now}]
        self.set_text("\n".join(got))

    def go(self, d):
        self.texts[self.pool()] = "\n".join(NL.parse(self.t.get("1.0", "end")))
        if d > 0 and self.pool() != "surnames" and not self.texts[self.pool()]:
            messagebox.showerror("Name list", "At least one name is needed here.", parent=self.w)
            return
        if d > 0 and self.step == len(STEPS) - 1:
            return self.done()
        self.step = max(0, min(len(STEPS) - 1, self.step + d))
        self.show()

    def done(self):
        pools = {p: NL.parse(self.texts[p]) for p, _, _ in STEPS}
        bad = NL.problems(pools)
        if bad:
            messagebox.showerror("Name list", "\n".join(bad), parent=self.w)
            return
        tips = NL.advice(pools)
        if tips and not messagebox.askyesno("Name list", "\n".join(tips) + "\n\nKeep this list?", parent=self.w):
            return
        self.app.name_list_set(self.who, pools)
        self.w.destroy()
