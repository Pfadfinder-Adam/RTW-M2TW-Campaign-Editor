"""Campaign rules... (top row): the campaign's settings files as plain values with an explanation, the game's own value
beside a changed one, Preview, Write it in (backup, Restore undoes it)."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import one_window, ShortHint, tip
from . import campaignrules as CR
from .gui_util import ScrollFrame
from .plan import Plan

CHANGED = "#fff3b0"
BAD = "#f4b6b6"


@one_window
class RulesWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.mod = app, app.mod
        self.title("Campaign rules - %s" % self.mod.data)
        self.geometry("1100x720")
        self.transient(app)
        self.changes = {}                       # Rule -> new text
        self.groups = []                        # [(label, file name, section head, [Rule])]
        self.files = {}                         # file name -> (own, base, {ident: game's value})
        self._read()
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        from .gui_util import experimental
        experimental(frm).pack(fill="x", anchor="w", pady=(0, 4))
        ShortHint(frm, wraplength=1060, justify="left", text=(
            "The rules of the whole campaign, from this mod's settings files and the top of the campaign's "
            "descr_strat.txt (start and end date, years a turn, switches). Pick a group on the left (or Find), "
            "change a value, then Preview and Write it in - a backup is made first and Restore undoes it. A value "
            "that differs from the game's own shows the game's beside it, with Reset.")).pack(anchor="w")
        if any(CR.blocked(r) for g in self.groups for r in g[3]):
            ttk.Label(frm, foreground="#777", wraplength=1060, justify="left", text=(
                "Greyed-out values: changing them broke the game in a test, so they are kept as they are for now - "
                "hover one to see what happened.")).pack(anchor="w", pady=(4, 0))
        bar = ttk.Frame(frm)
        bar.pack(fill="x", pady=(6, 4))
        ttk.Label(bar, text="Find").pack(side="left")
        self.v_find = tk.StringVar()
        ttk.Entry(bar, textvariable=self.v_find, width=30).pack(side="left", padx=4)
        self.v_find.trace_add("write", lambda *a: self.show())
        self.v_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="only values that differ from the game's", variable=self.v_only,
                        command=self.show).pack(side="left", padx=10)
        body = ttk.Panedwindow(frm, orient="horizontal")
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        body.add(left, weight=0)
        self.lb = tk.Listbox(left, width=42, exportselection=False)
        self.lb.pack(fill="both", expand=True)
        for label, *_ in self.groups:
            self.lb.insert("end", label)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.show())
        self.sf = ScrollFrame(body)
        body.add(self.sf, weight=1)
        foot = ttk.Frame(frm)
        foot.pack(fill="x", pady=(6, 0))
        self.lbl = ttk.Label(foot, foreground="#555")
        self.lbl.pack(side="left")
        from .gui_util import close_guard               # never closes over unwritten changes silently
        close = close_guard(self, "Campaign rules", lambda: ("%d value(s)" % len(self.changes)) if self.changes
                            else "", self.write)
        ttk.Button(foot, text="Close", command=close).pack(side="right")
        ttk.Button(foot, text="Write it in", command=self.write).pack(side="right", padx=6)
        ttk.Button(foot, text="Preview", command=self.preview).pack(side="right")
        if self.groups:
            self.lb.selection_set(0)
        self.show()

    def _read(self):
        from .limits import game_kind
        m2 = game_kind(self.mod) == "medieval2"
        campaign = self.app.v_campaign.get() if hasattr(self.app, "v_campaign") else None
        for name, title, own, base in CR.files(self.mod, campaign):
            rules = CR.read(own or base, medieval2=m2)
            game = {}
            if own and base:
                try:
                    game = {r.ident: r.value for r in CR.read(base, medieval2=m2)}
                except Exception:
                    game = {}
            self.files[name] = (own, base, game)
            heads = []
            for r in rules:
                head = r.section.split(" / ")[0]
                if head not in heads:
                    heads.append(head)
            for head in heads:
                rs = [r for r in rules if r.section.split(" / ")[0] == head]
                label = "%s: %s%s" % (title, head.replace("_", " "), "" if own else "  (the game's file)")
                self.groups.append((label, name, head, rs))

    def _game(self, rule):
        name = next(n for n, (own, base, _) in self.files.items() if rule.path in (own, base))
        own, base, game = self.files[name]
        return game.get(rule.ident) if own else None

    def show(self):
        for w in self.sf.inner.winfo_children():
            w.destroy()
        q = self.v_find.get().strip().lower()
        if q:
            rows = [(g, r) for g in self.groups for r in g[3]
                    if q in r.key.lower() or q in r.section.lower() or q in CR.explain(r).lower()]
        else:
            sel = self.lb.curselection()
            rows = [(self.groups[sel[0]], r) for r in self.groups[sel[0]][3]] if sel else []
        if self.v_only.get():
            rows = [(g, r) for g, r in rows if self._game(r) is not None and self._game(r) != r.value]
        inner = self.sf.inner
        if not self.groups:
            ttk.Label(inner, text="This mod and its game have none of the settings files (%s)." % ", ".join(
                n for n, _ in CR.FILES), wraplength=600).grid(sticky="w")
            return
        if rows and not q:
            g = rows[0][0]
            ttk.Label(inner, text=g[0], font=("", 11, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
            ttk.Label(inner, text="%s   (%s)" % (CR.section_words(g[2]), g[1]), foreground="#555",
                      wraplength=640, justify="left").grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 6))
        r0, last = 2, None
        for g, rule in rows[:400]:
            if rule.section != last and rule.section.split(" / ")[1:]:
                ttk.Label(inner, text=" / ".join(rule.section.split(" / ")[1:]).replace("_", " "),
                          font=("", 9, "bold")).grid(row=r0, column=0, columnspan=4, sticky="w", pady=(6, 0))
                r0 += 1
            last = rule.section
            self._row(inner, r0, rule, q)
            r0 += 1
        if len(rows) > 400:
            ttk.Label(inner, text="... %d more - Find narrows the list" % (len(rows) - 400)).grid(row=r0, column=0)
        inner.columnconfigure(2, weight=1)
        self._status()

    def _row(self, inner, r, rule, q):
        ttk.Label(inner, text=("%s: %s" % (rule.section.split(" / ")[0], rule.key) if q else rule.key)).grid(
            row=r, column=0, sticky="w", padx=(12, 6))
        v = tk.StringVar(value=self.changes.get(rule, rule.value))
        if rule.kind == "flag":                         # a switch line of descr_strat.txt: on / off
            e = tk.Spinbox(inner, textvariable=v, values=("off", "on"), width=12, state="readonly",
                           readonlybackground="white")
            v.set(self.changes.get(rule, rule.value))
        else:
            e = tk.Entry(inner, textvariable=v, width=14)
        e.grid(row=r, column=1, sticky="w")
        why_not = CR.blocked(rule)
        if why_not:                                     # broke the game in a test: shown, not changed
            v.set(rule.value)
            e.configure(state="disabled")
            tip(e, why_not)
        hint = CR.explain(rule)
        game = self._game(rule)
        hl = ttk.Label(inner, text=hint, foreground="#555", wraplength=360, justify="left")
        hl.grid(row=r, column=2, sticky="we", padx=6)
        hl.bind("<Configure>", lambda e: hl.configure(wraplength=max(120, e.width - 4)), add="+")   # never cut
        cell = ttk.Frame(inner)
        cell.grid(row=r, column=3, sticky="w")

        def paint(*_):
            now = v.get().strip()
            why = CR.check(rule, now)
            if now == rule.value:
                self.changes.pop(rule, None)
            else:
                self.changes[rule] = now
            colour = BAD if why else CHANGED if now != rule.value else "white"
            e.configure(**({"readonlybackground": colour} if rule.kind == "flag" else {"background": colour}))
            self._status(why and "%s: %s must be %s" % (rule.key, now or "(empty)", why))
        v.trace_add("write", paint)
        if game is not None and game != rule.value and not why_not:
            ttk.Label(cell, text="game: %s" % game, foreground="#b60").pack(side="left")
            ttk.Button(cell, text="Reset", command=lambda: v.set(game)).pack(side="left", padx=4)
        paint()

    def _status(self, problem=None):
        n = len(self.changes)
        self.lbl.configure(text=problem or ("%d value(s) changed - Preview, then Write it in." % n if n else
                                            "Nothing changed yet - change a value, then Preview and Write it in."),
                           foreground="#a33" if problem else "#555")

    def _plan(self):
        bad = [(r, t) for r, t in self.changes.items() if CR.check(r, t)]
        if bad:
            r, t = bad[0]
            raise ValueError("%s / %s: '%s' must be %s" % (r.section, r.key, t, CR.check(r, t)))
        plan = Plan(self.mod, "rules", "campaign_rules", {})
        for name, (own, base, _) in self.files.items():
            mine = {r: t for r, t in self.changes.items() if r.path in (own, base)}
            if mine:
                CR.apply(plan, name, mine, own, base)
        return plan

    def preview(self):
        if not self.changes:
            messagebox.showinfo("Campaign rules", "Nothing changed yet - change a value first.", parent=self)
            return
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror("Campaign rules", str(e), parent=self)
            return
        self.app.show_text("Campaign rules - preview (nothing written)", plan.report())

    def write(self):
        if not self.changes:
            messagebox.showinfo("Campaign rules", "Nothing changed yet - change a value first.", parent=self)
            return
        try:
            plan = self._plan()
        except Exception as e:
            messagebox.showerror("Campaign rules", str(e), parent=self)
            return
        if not messagebox.askyesno("Campaign rules", "Write %d value(s) into %d file(s)? A backup is made first "
                                                     "(Restore undoes it). The game reads them on the next start."
                                   % (len(self.changes), len(plan.changed_files())), parent=self):
            return
        bdir = plan.apply()
        from . import log
        log.write("Campaign rules changed (backup %s)\n%s" % (bdir, plan.report()))
        self.app.status.set("Campaign rules: %d value(s) written (backup %s) - start the game to try them."
                            % (len(self.changes), bdir))
        self.destroy()


def open_rules(app):
    if not app.mod:
        messagebox.showinfo("Campaign rules", "Load a mod first (Mod or Browse..., then Load).", parent=app)
        return
    RulesWindow(app)
