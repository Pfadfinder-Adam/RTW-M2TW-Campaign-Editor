"""The Module builder window (Tools > Module builder..., Add-ons > New module (no code)...): a new add-on put together
from blocks - WHEN something happens, IF conditions hold, DO actions - each picked from lists in plain words, with the
mod's own names to pick from. The sentence below says what it will do; any number or text may be made a setting the
player changes later on the Add-ons page. Show the script / Check it / Save to my add-ons / Put it in the game (a
backup first) / Share... The examples on the left start it; modules made before open again from the same list."""

import copy
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import addons as AD
from . import modbuilder as MB
from .gui_util import ScrollFrame, hint, one_window
from .plan import Plan

TITLE = "Module builder"
COLOURS = {"when": "#dfe9f7", "ifs": "#f7efd6", "dos": "#e2f2df"}
HEADS = {"when": "WHEN  (what happens in the game)", "ifs": "IF  (only when all of this is true)",
         "dos": "DO  (what the module does, in this order)"}
ADD = {"ifs": "+ another condition...", "dos": "+ another action..."}
GAMES = [("both", "both games (REX and M2EX)"), ("rome", "Rome: Total War (REX)"),
         ("medieval2", "Medieval II (M2EX)")]
CHOICES = {"op": MB.OPS, "turn_op": MB.TURN_OPS, "who": MB.WHO_IS, "to": MB.TO, "stance": MB.STANCES}
NUMBERS = ("int", "signed", "percent")
WIDE = ("text", "long")
EMPTY = "Empty - make your own"
MINE = "--- my modules ---"
HOW = ("A module is a small script the engine runs during the campaign: WHEN something happens, IF the conditions "
       "hold, it DOES the actions. REX (Rome) and M2EX (Medieval II) run it from the game's script/modules folder; "
       "the original exes run no scripts.\n\nStart from an example on the left or from an empty one: the list under "
       "WHEN says what happens, '+ another condition...' / '+ another action...' add a line, x takes it out. The "
       "sentence 'In plain words' says what it will do.\n\nTick a value under 'What the player may change later' and "
       "it becomes a setting on the Add-ons page. Save to my add-ons keeps it in the Add-ons list; Put it in the game "
       "writes it into the game (a backup first, Tools > Restore undoes it); Share... makes a zip for others. "
       "Each time it acts, the game's log (system.log.txt) gets a line starting with its name.")


@one_window
class ModuleBuilder(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.mod = app, getattr(app, "mod", None)
        self.title("%s - a new add-on without code" % TITLE)
        self.geometry("1240x800")
        self.transient(app)
        self.names = {}                  # {what: [the mod's names]} - read once per window
        self.recipe = MB.new_recipe()
        self.changed = False
        self._quiet = False              # True while the window itself sets its fields
        top = ttk.Frame(self, padding=(10, 8, 10, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Module name", font=("", 10, "bold")).pack(side="left")
        self.v_title = tk.StringVar()
        ttk.Entry(top, textvariable=self.v_title, width=34).pack(side="left", padx=6)
        ttk.Label(top, text="for").pack(side="left")
        self.v_game = tk.StringVar()
        cb = ttk.Combobox(top, textvariable=self.v_game, values=[l for _, l in GAMES], state="readonly", width=27)
        cb.pack(side="left", padx=6)
        self.v_once = tk.BooleanVar()
        ttk.Checkbutton(top, text="only once in a campaign", variable=self.v_once).pack(side="left", padx=10)
        hint(top, HOW, width=520).pack(side="left")
        self.v_title.trace_add("write", lambda *a: self._top_changed())
        self.v_game.trace_add("write", lambda *a: self._top_changed())
        self.v_once.trace_add("write", lambda *a: self._top_changed())

        body = ttk.Frame(self, padding=(10, 0))
        body.pack(fill="both", expand=True)
        left = ttk.LabelFrame(body, text=" Start from an example ", padding=4)
        left.pack(side="left", fill="y", padx=(0, 8))
        self.lb = tk.Listbox(left, width=36, height=22, exportselection=False)
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.pick_entry())
        ttk.Label(left, foreground="#666", wraplength=250, justify="left", text=(
            "An example is made for the loaded mod: its names (a unit, a building, a town) are the mod's own - "
            "change any of them.")).pack(anchor="w", pady=(4, 0))
        self.sf = ScrollFrame(body)
        self.sf.pack(side="left", fill="both", expand=True)

        low = ttk.Frame(self, padding=(10, 4, 10, 8))
        low.pack(fill="x")
        pl = ttk.LabelFrame(low, text=" In plain words ", padding=6)
        pl.pack(fill="x")
        self.lbl_plain = wrapping(ttk.Label(pl, justify="left", foreground="#1d3b6a", font=("", 10)))
        self.lbl_bad = wrapping(ttk.Label(low, justify="left"), pady=(4, 0))
        bar = ttk.Frame(low)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Show the script", command=self.show_script).pack(side="left")
        ttk.Button(bar, text="Check it", command=self.check).pack(side="left", padx=4)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Share...", command=self.share).pack(side="right", padx=4)
        ttk.Button(bar, text="Put it in the game...", command=self.put_in).pack(side="right")
        ttk.Button(bar, text="Save to my add-ons", command=self.save).pack(side="right", padx=4)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.fill_list()
        self.load(self.recipe, fresh=True)

    # ---- the list of examples and own modules ----
    def fill_list(self):
        self.entries = []
        self.lb.delete(0, "end")
        titles = [r["title"] for r in MB.EXAMPLES] + [r.get("title") or a.title for a, r in MB.my_modules()]
        self.lb.configure(width=max([36] + [len(t) + 2 for t in titles]))
        for r in MB.EXAMPLES:
            self.entries.append(("ex", r))
            self.lb.insert("end", r["title"])
        self.entries.append(("empty", None))
        self.lb.insert("end", EMPTY)
        mine = MB.my_modules()
        if mine:
            self.entries.append(("sep", None))
            self.lb.insert("end", MINE)
            self.lb.itemconfigure("end", foreground="#888")
            for a, r in mine:
                self.entries.append(("mine", r))
                self.lb.insert("end", r.get("title") or a.title)

    def pick_entry(self):
        sel = self.lb.curselection()
        if not sel:
            return
        kind, r = self.entries[sel[0]]
        if kind == "sep":
            return
        name = r["title"] if r else EMPTY
        if self.changed and not messagebox.askyesno(TITLE, "Start from '%s'?\n\nWhat is in the builder now is replaced "
                                                           "(it is not saved)." % name, parent=self):
            return
        if kind == "ex":
            r = MB.fit_to_mod(r, self.mod) if self.mod is not None else copy.deepcopy(r)
        elif kind == "empty":
            r = MB.new_recipe()
        self.load(r, fresh=True)

    def load(self, recipe, fresh=False, ask=False):
        """The recipe into the window (a copy); ask: say first that the one there now is replaced."""
        if ask and self.changed and not messagebox.askyesno(
                TITLE, "Open '%s'?\n\nWhat is in the builder now is replaced (it is not saved)." % recipe.get("title"),
                parent=self):
            return
        self.recipe = copy.deepcopy(recipe)
        self.recipe.setdefault("settings", {})
        self._quiet = True
        self.v_title.set(self.recipe.get("title", ""))
        self.v_game.set(dict(GAMES).get(self.recipe.get("game"), GAMES[0][1]))
        self.v_once.set(bool(self.recipe.get("once")))
        self._quiet = False
        self.changed = not fresh
        self.rebuild()

    def _top_changed(self):
        if self._quiet:
            return
        game = next((k for k, l in GAMES if l == self.v_game.get()), "both")
        other_game = game != self.recipe.get("game")
        self.recipe["title"] = self.v_title.get()
        self.recipe["game"] = game
        self.recipe["once"] = bool(self.v_once.get())
        self.changed = True
        if other_game:
            self.rebuild()                       # what the event brings and the engines' lists follow the game
        else:
            self.refresh()

    # ---- the blocks ----
    def names_of(self, what):
        if what not in self.names:
            self.names[what] = MB.mod_names(self.mod, what) if self.mod is not None else []
        return self.names[what]

    def rebuild(self):
        inner = self.sf.inner
        for w in inner.winfo_children():
            w.destroy()
        self._when(inner)
        for group in ("ifs", "dos"):
            self._block(inner, group)
        self._settings(inner)
        inner.update_idletasks()
        self.refresh()

    def _frame(self, inner, key):
        c = COLOURS[key]
        f = tk.Frame(inner, bg=c, bd=1, relief="solid")
        f.pack(fill="x", pady=4, padx=2)
        tk.Label(f, text=HEADS[key], bg=c, fg="#1e1e1e", font=("", 11, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
        return f, c

    def _when(self, inner):
        f, c = self._frame(inner, "when")
        row = tk.Frame(f, bg=c)
        row.pack(anchor="w", padx=18, pady=(0, 2))
        ev = MB.EVENT.get(self.recipe.get("when"))
        v = tk.StringVar(value=ev.label if ev else "")
        cb = ttk.Combobox(row, textvariable=v, values=[e.label for e in MB.EVENTS], state="readonly", width=40)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_when(v.get()))
        if ev:
            wrapping(tk.Label(f, text=ev.help[0].upper() + ev.help[1:] + ".", bg=c, fg="#444", justify="left",
                              anchor="w"), padx=18)
            brings = MB.event_subjects(ev, self.recipe.get("game", "both"), self.mod)
            if brings is None:
                wrapping(tk.Label(f, bg=c, fg="#b00", justify="left", anchor="w", text=(
                    "%s has no such event - see the line at the bottom." % MB.GAME_ENGINES.get(
                        self.recipe.get("game", "both")))), padx=18, pady=(0, 6))
            else:
                wrapping(tk.Label(f, bg=c, fg="#444", justify="left", anchor="w", text="It brings along: " + (
                    ", ".join(MB.SUBJECT_WORDS[s] for s in brings) or "nothing") +
                    " - the conditions and actions below work on them."), padx=18, pady=(0, 6))

    def _block(self, inner, group):
        f, c = self._frame(inner, group)
        table = MB.CONDITION if group == "ifs" else MB.ACTION
        parts = MB.CONDITIONS if group == "ifs" else MB.ACTIONS
        items = self.recipe.get(group, [])
        if not items:
            tk.Label(f, bg=c, fg="#555", text="(nothing yet - %s)" % (
                "the actions run every time" if group == "ifs" else "add what it does")).pack(anchor="w", padx=18)
        for i, it in enumerate(items):
            part = table.get(it.get("k"))
            row = tk.Frame(f, bg=c)
            row.pack(anchor="w", padx=18, pady=2, fill="x")
            pv = tk.StringVar(value=part.label if part else it.get("k"))
            pcb = ttk.Combobox(row, textvariable=pv, values=[p.label for p in parts], state="readonly",
                               width=max(len(p.label) for p in parts) + 1)
            pcb.pack(side="left")
            pcb.bind("<<ComboboxSelected>>", lambda e, g=group, n=i, v=pv: self.change_part(g, n, v.get()))
            wide = []
            for name, kind, label, _ in (part.fields if part else []):
                if kind in WIDE or kind.startswith(("names:", "cmd:")) or kind == "cond":
                    wide.append((name, kind, label))      # on a line of its own below: no text cut at the edge
                else:
                    self._field(row, c, group, i, it, part, name, kind, label)
            tk.Button(row, text="x", relief="flat", bg=c, fg="#a00", activebackground=c, cursor="hand2",
                      command=lambda g=group, n=i: self.remove(g, n)).pack(side="left", padx=6)
            if part and part.help:
                hint(row, part.help).pack(side="left")
            for name, kind, label in wide:
                if self._shown(part, it, name, kind):
                    self._wide_field(f, c, group, i, it, name, kind, label)
        add = tk.Button(f, text=ADD[group], relief="groove", bg=c, activebackground=c, cursor="hand2")
        add.configure(command=lambda b=add, g=group: self.add_menu(b, g))
        add.pack(anchor="w", padx=18, pady=(4, 6))

    def _shown(self, part, it, name, kind):
        """A faction list shows only for 'one of these factions', a faction name only for 'this faction:'."""
        if kind == "names:factions" and part.key in ("who", "old_owner"):
            return it.get("v") == "these"
        if kind == "name:factions":
            return not MB._faction_field_unused(part, it, name)
        return True

    def _field(self, row, c, group, i, it, part, name, kind, label):
        if not self._shown(part, it, name, kind):
            return
        before = bool(label) and kind not in NUMBERS
        if before:
            tk.Label(row, text=label, bg=c, fg="#1e1e1e").pack(side="left", padx=(6, 2))
        if kind in NUMBERS:
            v = tk.StringVar(value="" if it.get(name) is None else str(it.get(name)))
            ttk.Entry(row, textvariable=v, width=8).pack(side="left", padx=2)
            v.trace_add("write", lambda *a: self.set_value(group, i, name, kind, v.get()))
        elif kind in CHOICES:
            pairs = CHOICES[kind]
            v = tk.StringVar(value=dict(pairs).get(it.get(name), pairs[0][1]))
            cb = ttk.Combobox(row, textvariable=v, values=[l for _, l in pairs], state="readonly",
                              width=max(len(l) for _, l in pairs) + 1)
            cb.pack(side="left", padx=2)
            cb.bind("<<ComboboxSelected>>", lambda e: self.set_choice(group, i, name, kind, v.get()))
        elif kind.startswith("name:"):
            what = kind.split(":")[1]
            v = tk.StringVar(value=it.get(name) or "")
            ttk.Combobox(row, textvariable=v, values=self.names_of(what), width=28).pack(side="left", padx=2)
            v.trace_add("write", lambda *a: self.set_value(group, i, name, kind, v.get()))
        if label and not before:
            tk.Label(row, text=label, bg=c, fg="#1e1e1e").pack(side="left", padx=(2, 6))

    def _wide_field(self, f, c, group, i, it, name, kind, label):
        """A text or a list of names on a line of its own under its row, in a box as wide as the block that grows
        with what is typed (one line of words: Enter adds none)."""
        sub = tk.Frame(f, bg=c)
        sub.pack(anchor="w", fill="x", padx=(46, 18), pady=(0, 3))
        tk.Label(sub, text=label, bg=c, fg="#1e1e1e", width=8, anchor="e").pack(side="left", padx=(0, 4))
        names = kind.startswith("names:")
        line = kind == "cond" or kind.startswith("cmd:")
        now = ", ".join(it.get(name) or []) if names else str(it.get(name) or "")
        about = None
        if line:                                      # what the engines say of the command / condition typed
            about = tk.Label(f, bg=c, fg="#444", justify="left", anchor="w")
            wrapping(about, padx=(46 + 8 * 8, 18), pady=(0, 3))

        def changed(text):
            self.set_value(group, i, name, kind, text)
            if about is not None:
                about.configure(text=self.about_line(kind, text))
        box = GrowingText(sub, now, changed, least=2 if kind == "long" else 1)
        if names:
            ttk.Button(sub, text="Pick...", command=lambda: self.pick_many(kind.split(":")[1], box)).pack(
                side="right", padx=(4, 0))
        if line:
            ttk.Button(sub, text="Pick...", command=lambda: EnginePicker(
                self, MB.LINE_KIND[kind], box.set, current=box.get())).pack(side="right", padx=(4, 0))
            about.configure(text=self.about_line(kind, now))
            about.pack_forget()
            about.pack(fill="x", anchor="w", padx=(46 + 8 * 8, 18), pady=(0, 3), after=sub)
        box.pack(side="left", fill="x", expand=True)

    def catalogue(self):
        from . import enginedocs as ED
        return ED.catalogue(self.recipe.get("game", "both"), self.mod)

    def about_line(self, kind, text):
        """One line under a command / condition box: its form and the engine's words, or what is wrong with it."""
        from . import enginedocs as ED
        name = ED.first_word(text)
        if not name:
            return "Pick... lists every one the engines have (%s)." % MB.GAME_ENGINES.get(
                self.recipe.get("game", "both"), "")
        e = self.catalogue()[MB.LINE_KIND[kind]].get(name)
        if e is None:
            return "%s is not in the engines' list - Pick... shows every one" % name
        words = "%s %s" % (e.name, e.params) if e.params else e.name
        return words + (" - " + e.desc if e.desc else "")

    def _settings(self, inner):
        f = ttk.LabelFrame(inner, text=" What the player may change later (on the Add-ons page) ", padding=6)
        f.pack(fill="x", pady=(6, 2), padx=2)
        ttk.Label(f, foreground="#555", wraplength=860, justify="left", text=(
            "Tick a value to make it a setting: the player changes it on the Add-ons page, no script touched. The words "
            "beside it are what the page shows. 'Module on' and 'Only once in a campaign' are always there.")).pack(
            anchor="w")
        have = self.recipe.setdefault("settings", {})
        rows = MB.settable(self.recipe)
        if not rows:
            ttk.Label(f, text="(no numbers or texts yet)", foreground="#777").pack(anchor="w", pady=2)
        for path, words in rows:
            r = ttk.Frame(f)
            r.pack(anchor="w", fill="x", pady=1)
            on = tk.BooleanVar(value=path in have)
            lab = tk.StringVar(value=have.get(path) or words[0].upper() + words[1:])
            ttk.Checkbutton(r, variable=on, text=words, width=58).pack(side="left")
            e = ttk.Entry(r, textvariable=lab, width=max(34, min(60, len(lab.get()) + 4)))
            e.pack(side="left", padx=8)

            def toggled(p=path, on=on, lab=lab, e=e):
                if on.get():
                    self.recipe["settings"][p] = lab.get().strip() or p
                else:
                    self.recipe["settings"].pop(p, None)
                e.configure(state="normal" if on.get() else "disabled")
                self.changed = True
                self.refresh()

            def relabel(*a, p=path, on=on, lab=lab):
                if on.get():
                    self.recipe["settings"][p] = lab.get().strip() or p
                    self.changed = True
                    self.refresh()
            on.trace_add("write", lambda *a, t=toggled: t())
            lab.trace_add("write", relabel)
            e.configure(state="normal" if on.get() else "disabled")

    # ---- changes ----
    def set_when(self, label):
        self.recipe["when"] = next(e.key for e in MB.EVENTS if e.label == label)
        self.changed = True
        self.rebuild()

    def set_value(self, group, i, name, kind, raw):
        it = self.recipe[group][i]
        if kind in NUMBERS:
            try:
                it[name] = int(str(raw).strip())
            except ValueError:
                it[name] = str(raw)                 # not a number: the problems line says so
        elif kind.startswith("names:"):
            it[name] = [x.strip() for x in str(raw).split(",") if x.strip()]
        elif kind.startswith("name:"):
            it[name] = str(raw).strip()
        else:
            it[name] = raw
        self.changed = True
        self.refresh()

    def set_choice(self, group, i, name, kind, label):
        self.recipe[group][i][name] = next(k for k, l in CHOICES[kind] if l == label)
        self.changed = True
        if kind in ("who", "to"):
            self.rebuild()                          # a faction list / name shows or goes
        else:
            self.refresh()

    def _settings_without(self, group, i, shift):
        """The settings of line i of group dropped; with shift the later lines' paths move up one."""
        out = {}
        for path, label in self.recipe.get("settings", {}).items():
            g, n, name = path.split(".")
            n = int(n)
            if g == group and n == i:
                continue
            if shift and g == group and n > i:
                n -= 1
            out["%s.%d.%s" % (g, n, name)] = label
        self.recipe["settings"] = out

    def remove(self, group, i):
        del self.recipe[group][i]
        self._settings_without(group, i, True)
        self.changed = True
        self.rebuild()

    def change_part(self, group, i, label):
        parts = MB.CONDITIONS if group == "ifs" else MB.ACTIONS
        key = next(p.key for p in parts if p.label == label)
        if self.recipe[group][i].get("k") == key:
            return
        self.recipe[group][i] = self._new_item(group, key)
        self._settings_without(group, i, False)
        self.changed = True
        self.rebuild()

    def _new_item(self, group, key):
        it = MB.item("if" if group == "ifs" else "do", key)
        if self.mod is not None:                    # its names filled from the mod, like an example's
            r = MB.fit_to_mod({"ifs": [it] if group == "ifs" else [], "dos": [it] if group == "dos" else []}, self.mod)
            it = r[group][0]
        return it

    def add_menu(self, button, group):
        ev = MB.EVENT.get(self.recipe.get("when"))
        have = set(MB.event_subjects(ev, self.recipe.get("game", "both"), self.mod) or ev.subjects) if ev else set()
        m = tk.Menu(self, tearoff=False)
        for p in (MB.CONDITIONS if group == "ifs" else MB.ACTIONS):
            lack = [MB.SUBJECT_WORDS[n] for n in p.needs if n not in have]
            if lack:
                m.add_command(label="%s   (needs %s - pick another WHEN)" % (p.label, " and ".join(lack)),
                              state="disabled")
            else:
                m.add_command(label=p.label, command=lambda k=p.key: self.add(group, k))
        try:
            m.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())
        finally:
            m.grab_release()

    def add(self, group, key):
        self.recipe.setdefault(group, []).append(self._new_item(group, key))
        self.changed = True
        self.rebuild()

    def pick_many(self, what, var):
        names = self.names_of(what)
        if not names:
            messagebox.showinfo(TITLE, "Load a mod first - the names are picked from its files. (Or type them, "
                                       "parted by commas.)" if self.mod is None else
                                "This mod has no %s to pick from - type the names." % what, parent=self)
            return
        now = {x.strip().lower() for x in var.get().split(",") if x.strip()}
        w = tk.Toplevel(self)
        w.title("Pick %s" % what)
        w.transient(self)
        frm = ttk.Frame(w, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="The %s of this mod - click to tick or untick." % what).pack(anchor="w")
        v_find = tk.StringVar()
        ttk.Entry(frm, textvariable=v_find, width=30).pack(anchor="w", pady=4)
        box = ttk.Frame(frm)
        box.pack(fill="both", expand=True)
        lb = tk.Listbox(box, selectmode="multiple", height=18, width=44, exportselection=False)
        sb = ttk.Scrollbar(box, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        picked = set(n for n in names if n.lower() in now)
        shown = []

        def show(*a):
            for i, n in enumerate(shown):                # keep the ticks of what is shown before the list changes
                (picked.add if lb.selection_includes(i) else picked.discard)(n)
            f = v_find.get().strip().lower()
            shown[:] = [n for n in names if f in n.lower()]
            lb.delete(0, "end")
            for i, n in enumerate(shown):
                lb.insert("end", n)
                if n in picked:
                    lb.selection_set(i)
        v_find.trace_add("write", show)
        show()

        def ok():
            show()
            var.set(", ".join(n for n in names if n in picked))
            w.destroy()
        bar = ttk.Frame(frm)
        bar.pack(anchor="e", pady=(6, 0))
        ttk.Button(bar, text="OK", command=ok).pack(side="left")
        ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="left", padx=4)

    # ---- what it says ----
    def problems(self, with_mod=True):
        bad = MB.problems(self.recipe, self.mod if with_mod else None, names=self.names_of if with_mod else None)
        if self.mod is not None:
            from .limits import game_kind
            game = game_kind(self.mod)
            if self.recipe.get("game") not in ("both", game):
                bad.append("it is made for %s - the loaded mod is %s (change 'for' at the top)" % (
                    dict(GAMES)[self.recipe["game"]], "Medieval II" if game == "medieval2" else "Rome: Total War"))
        return bad

    def refresh(self):
        self.lbl_plain.configure(text=MB.plain_words(self.recipe))
        bad = self.problems()
        if bad:
            self.lbl_bad.configure(foreground="#b00", text="Not ready yet: " + "; ".join(bad[:4]) + (
                " ... (%d more - Check it lists them)" % (len(bad) - 4) if len(bad) > 4 else ""))
        else:
            self.lbl_bad.configure(foreground="#2a7a1f", text="Ready: nothing missing. Check it, then Save to my "
                                                              "add-ons or Put it in the game.")

    def show_script(self):
        try:
            text = MB.script(self.recipe)
        except ValueError:
            messagebox.showinfo(TITLE, "Not ready yet:\n\n- " + "\n- ".join(self.problems(False)), parent=self)
            return
        self.app.show_text("%s - %s (the script, nothing written)" % (TITLE, self.recipe["title"].strip()), text)

    def check(self):
        bad = self.problems()
        if bad:
            messagebox.showwarning(TITLE, "Not ready yet:\n\n- " + "\n- ".join(bad), parent=self)
            return
        notes = []
        if self.mod is None:
            notes.append("No mod is loaded: the names were not checked against a mod's files.")
        else:
            from .limits import engine_of
            if not engine_of(self.mod):
                notes.append("No REX / M2EX was found beside this game: the original exes run no scripts, so the "
                             "module would do nothing there.")
        messagebox.showinfo(TITLE, "Nothing missing.\n\nIt does: %s\n\n%sWhat it does in the game is seen only there: "
                                   "put it in, start the campaign - the game's log (system.log.txt) gets a line "
                                   "starting with [%s] each time it acts." % (
                                       MB.plain_words(self.recipe), "".join(n + "\n\n" for n in notes),
                                       MB.key_of(self.recipe["title"]).upper()), parent=self)

    def _saved(self, quiet=False):
        """The module written into the editor's add-ons folder -> its Addon, or None (the user was told why)."""
        bad = self.problems()
        if bad:
            messagebox.showwarning(TITLE, "Not ready yet - nothing saved:\n\n- " + "\n- ".join(bad), parent=self)
            return None
        try:
            a = MB.save(self.recipe)
        except (ValueError, OSError) as e:
            messagebox.showerror(TITLE, "%s\n\nNothing saved." % e, parent=self)
            return None
        from . import log
        log.write("Module builder: %s saved (%s) - %s" % (a.title, a.path, MB.plain_words(self.recipe)))
        self.changed = False
        self.fill_list()
        panel = getattr(self.app, "editors", {}).get("addons")
        if panel is not None:
            try:
                panel.fill(a.key)
                panel.show()
            except tk.TclError:
                pass
        if not quiet:
            messagebox.showinfo(TITLE, "Saved: %s is in the Add-ons list now (the Add-ons page) - put it in there or "
                                       "with Put it in the game here." % a.title, parent=self)
        return a

    def save(self):
        self._saved()

    def put_in(self):
        if self.mod is None:
            messagebox.showinfo(TITLE, "Load a mod first (Mod or Browse..., then Load).", parent=self)
            return
        a = self._saved(quiet=True)
        if a is None:
            return
        try:
            plan = Plan(AD.plan_mod(self.mod, a), "addon", a.key, {})
            AD.plan_install(plan, a, AD.read_settings(a, a.template()), self.mod)
        except Exception as e:
            messagebox.showerror(TITLE, "%s\n\nNothing was written." % e, parent=self)
            return
        if not plan.changed_files():
            messagebox.showinfo(TITLE, "It is in the game already, exactly like this - nothing to write.", parent=self)
            return
        from .limits import engine_of
        warn = "" if engine_of(self.mod) else ("\n\nNo REX / M2EX was found beside this game: the original exes run "
                                              "no scripts - the module does nothing without one.")
        if not messagebox.askyesno(TITLE, "%s%s\n\nWrite it? A backup is made first (Restore undoes it)." % (
                plan.report(), warn), parent=self):
            return
        bdir = plan.apply()
        from . import log
        log.write("Add-on %s put in from the Module builder (backup %s)\n%s" % (a.title, bdir, plan.report()))
        self.app.status.set("%s put in (backup %s) - start the campaign: the game's log shows its [%s] lines."
                            % (a.title, bdir, a.key.upper()))
        panel = getattr(self.app, "editors", {}).get("addons")
        if panel is not None:
            try:
                panel.show()
            except tk.TclError:
                pass
        messagebox.showinfo(TITLE, "%s is in the game. Start the campaign; the game's log (system.log.txt) gets a "
                                   "line starting with [%s] each time it acts. Its settings are on the Add-ons page."
                            % (a.title, a.key.upper()), parent=self)

    def share(self):
        a = self._saved(quiet=True)
        if a is None:
            return
        out = filedialog.asksaveasfilename(parent=self, title="Share %s" % a.title, defaultextension=".zip",
                                           initialfile="%s.zip" % a.key, filetypes=[("Zip", "*.zip")])
        if not out:
            return
        try:
            AD.share(a, out)
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self)
            return
        messagebox.showinfo(TITLE, "Saved %s - give it to others: Add-ons > Add an add-on... takes it, and the "
                                   "Module builder opens it again." % out, parent=self)

    def close(self):
        if self.changed and not messagebox.askyesno(TITLE, "Close the builder? The module is not saved.", parent=self):
            return
        self.destroy()


def open_builder(app, recipe=None):
    """The builder (one window); recipe: a module to open in it (a builder-made add-on)."""
    w = ModuleBuilder(app)
    if recipe is not None:
        w.load(recipe, ask=True)
    return w


def wrapping(label, **pack):
    """A label packed across its parent whose words wrap at its own width - never cut at the window's edge."""
    label.pack(fill="x", anchor="w", **pack)
    label.bind("<Configure>", lambda e: label.configure(wraplength=max(60, e.width - 8)), add="+")
    return label


class GrowingText(tk.Text):
    """A box for one line of words that wraps them and grows (up to 5 lines) instead of hiding what does not fit;
    on_change(text) on every change. get() / set() like a StringVar (pick_many fills it)."""

    def __init__(self, master, text, on_change, least=1):
        super().__init__(master, height=least, width=40, wrap="word", font="TkDefaultFont", relief="solid", bd=1,
                         undo=True, highlightthickness=0)
        self.least, self.on_change = least, on_change
        self.insert("1.0", text)
        self.edit_modified(False)
        self.bind("<<Modified>>", self._changed)
        self.bind("<Return>", lambda e: "break")
        self.bind("<KP_Enter>", lambda e: "break")
        self.bind("<Configure>", lambda e: self._fit())

    def get(self, *a):
        if a:
            return super().get(*a)
        return super().get("1.0", "end-1c").replace("\n", " ")

    def set(self, text):
        self.delete("1.0", "end")
        self.insert("1.0", text)

    def _changed(self, e=None):
        if not self.edit_modified():
            return
        self.edit_modified(False)
        self.on_change(self.get())
        self._fit()

    def _fit(self):
        try:
            n = self.count("1.0", "end", "displaylines")
            n = n[0] if isinstance(n, tuple) else n
        except (tk.TclError, TypeError, IndexError):
            return
        self.configure(height=max(self.least, min(5, n or 1)))


class EnginePicker(tk.Toplevel):
    """Every console command / campaign-script command / condition / event the module's engines have, with a search:
    the form, a sample, where it works, what it needs or brings, the engine's own words when the game has its
    documentation folder - and its parameters as fields (factions, towns, units, traits ... of the mod, the event's own
    {faction} / {town} / {general} first), the line put together below them. on_pick(line) on Use it (or a double
    click); current: the line there now - its command picked and its words put in the fields."""

    # what a parameter field offers before the mod's names: the event's own, filled in when the module acts
    PLACEHOLDERS = {"factions": ["{faction}", "{owner}"], "towns": ["{town}"], "regions": [],
                    "characters": ["{general}"]}

    def __init__(self, builder, what, on_pick, current=""):
        from . import enginedocs as ED
        super().__init__(builder)
        self.builder, self.what, self.on_pick, self.ED = builder, what, on_pick, ED
        game = builder.recipe.get("game", "both")
        cat = ED.catalogue(game, builder.mod)
        self.entries = list(cat[what].values())
        self.event = cat["events"].get(getattr(MB.EVENT.get(builder.recipe.get("when")), "engine", None))
        self.title("Pick one of the %s - %s" % (ED.KIND_WORDS[what], MB.GAME_ENGINES.get(game, game)))
        self.geometry("1060x720")
        self.transient(builder)
        words = ED.split_line(current)
        self.v_not = tk.BooleanVar(value=bool(words) and words[0] == "not")
        if words and words[0] == "not":
            words = words[1:]
        self.start = (words[0], words[1:]) if words else (None, [])
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Find").pack(side="left")
        self.v_find = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.v_find, width=30)
        e.pack(side="left", padx=6)
        e.focus_set()
        ticks = ttk.Frame(self, padding=(8, 0, 8, 6))           # a line of their own: nothing cut at the edge
        ticks.pack(fill="x")
        self.v_usable = tk.BooleanVar(value=True)
        ttk.Checkbutton(ticks, variable=self.v_usable, text="only what a module can use on the campaign map").pack(
            anchor="w")
        self.v_fits = tk.BooleanVar(value=what == "conditions" and self.event is not None)
        if what == "conditions" and self.event is not None:
            ttk.Checkbutton(ticks, variable=self.v_fits, text="only what fits '%s'" % MB.EVENT[
                builder.recipe["when"]].label).pack(anchor="w")
        body = ttk.Frame(self, padding=(8, 0))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        self.lb = tk.Listbox(left, width=max(30, min(48, max([len(x.name) for x in self.entries] + [10]) + 2)),
                             exportselection=False)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="y", expand=True)
        sb.pack(side="left", fill="y")
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.info = tk.Text(right, wrap="word", font="TkDefaultFont", relief="flat", padx=10, pady=6, height=9)
        self.info.pack(fill="both", expand=True)
        self.info.tag_configure("head", font=("", 12, "bold"))
        self.info.tag_configure("bad", foreground="#b00")
        self.info.tag_configure("dim", foreground="#666")
        self.form = ttk.LabelFrame(right, text=" Its parameters ", padding=6)
        self.form.pack(fill="x", pady=(6, 0))
        self.lbl_line = wrapping(ttk.Label(right, foreground="#1d3b6a", font=("", 10), justify="left"), pady=(6, 0))
        low = ttk.Frame(self, padding=8)
        low.pack(fill="x")
        self.lbl = ttk.Label(low, foreground="#555")
        self.lbl.pack(side="left")
        ttk.Button(low, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(low, text="Use it", command=self.use).pack(side="right", padx=6)
        self.fields = []
        self.lb.bind("<<ListboxSelect>>", lambda ev: self.show())
        self.lb.bind("<Double-1>", lambda ev: self.use())
        for v in (self.v_find, self.v_usable, self.v_fits):
            v.trace_add("write", lambda *a: self.fill())
        self.v_not.trace_add("write", lambda *a: self.put_line())
        self.fill()

    def fill(self):
        ED = self.ED
        got = ED.search(self.entries, self.v_find.get())
        if self.v_usable.get():
            got = [e for e in got if e.runnable()]
        if self.v_fits.get():
            got = [e for e in got if not ED.missing(e, self.event)]
        self.shown = got
        self.lb.delete(0, "end")
        for e in got:
            self.lb.insert("end", e.name)
        self.lbl.configure(text="%d of %d %s" % (len(got), len(self.entries), ED.KIND_WORDS[self.what]))
        names = [e.name for e in got]
        at = names.index(self.start[0]) if self.start[0] in names else 0
        if got:
            self.lb.selection_set(at)
            self.lb.see(at)
        self.show()

    def picked(self):
        sel = self.lb.curselection()
        return self.shown[sel[0]] if sel and sel[0] < len(self.shown) else None

    def show(self):
        ED = self.ED
        e = self.picked()
        t = self.info
        t.configure(state="normal")
        t.delete("1.0", "end")
        self._form(e)
        if e is None:
            t.insert("end", "Nothing found - change the words in Find, or untick the boxes above.", "dim")
            t.configure(state="disabled")
            return
        t.insert("end", e.name + "\n", "head")
        if e.params:
            t.insert("end", "Parameters: %s\n" % e.params)
        if e.sample and e.sample != e.name:
            t.insert("end", "Written like: %s\n" % e.sample)
        if e.where:
            t.insert("end", "Works in: %s\n" % e.where)
        if self.what == "conditions":
            t.insert("end", "Needs from what happened: %s\n" % (", ".join(e.needs) or "nothing - it fits every event"))
            miss = ED.missing(e, self.event)
            if miss:
                t.insert("end", "'%s' does not bring %s\n" % (MB.EVENT[self.builder.recipe["when"]].label,
                                                              " and ".join(miss)), "bad")
        if self.what == "events":
            t.insert("end", "Brings along: %s\n" % (", ".join(e.needs) or "nothing"))
        t.insert("end", "Engines: %s\n" % " and ".join(ED.ENGINE_WORDS[x] for x in e.engines))
        if not e.works:
            t.insert("end", "The engine marks it not implemented: it does nothing.\n", "bad")
        elif not e.runnable():
            t.insert("end", "A module cannot use it on the campaign map (a battle or editor command, or the flow of "
                            "campaign_script.txt: blocks, jumps, waits).\n", "bad")
        t.insert("end", "\n")
        if e.desc:
            t.insert("end", e.desc + "\n")
        else:
            t.insert("end", "No description here: " + ED.DUMP_HOW + "\n", "dim")
        t.configure(state="disabled")

    def _offer(self, p):
        """What a parameter's field lists: the event's own words first, then the mod's names (or its choices)."""
        if p.kind == "logic":
            return list(self.ED.LOGIC)
        if p.kind == "choice":
            return list(p.choices)
        out = []
        for k in p.kind.split("|"):
            out += self.PLACEHOLDERS.get(k, [])
        for k in p.kind.split("|"):
            if k in ("factions", "towns", "regions", "characters", "units", "traits", "ancillaries", "levels",
                     "chains"):
                out += self.builder.names_of(k)
        return out

    def _form(self, e):
        for w in self.form.winfo_children():
            w.destroy()
        self.fields = []
        if e is None:
            self.lbl_line.configure(text="")
            return
        params = self.ED.params_of(e)
        given = self.start[1] if e.name == self.start[0] else []
        # a command picked anew: its sample's comparison, choices and numbers go in; the names are the mod's to pick
        sample = self.ED.split_line(e.sample)[1:] if not given and e.sample else []
        if not params:
            ttk.Label(self.form, foreground="#666", text="none - the line is its name%s" % (
                " (the rest, if the engine wants more, may be typed in the box after Use it)" if e.params else "")).grid(
                row=0, column=0, sticky="w")
        for n, p in enumerate(params):
            ttk.Label(self.form, text=p.label + (" (may be left empty)" if p.optional else "")).grid(
                row=n, column=0, sticky="w", padx=(0, 8), pady=1)
            v = tk.StringVar(value=given[n] if n < len(given) else "")
            if not given and n < len(sample) and p.kind in ("logic", "choice", "number") and \
                    (p.kind != "number" or sample[n].lstrip("-").replace(".", "", 1).isdigit()) and \
                    (p.kind != "logic" or sample[n] in self.ED.LOGIC) and (p.kind != "choice" or sample[n] in p.choices):
                v.set(sample[n])
            if n == len(params) - 1 and len(given) > len(params):    # extra words (a name with spaces) go last
                v.set(" ".join(given[n:]))
            offer = self._offer(p)
            if offer:
                w = ttk.Combobox(self.form, textvariable=v, values=offer, width=40,
                                 state="readonly" if p.kind in ("logic", "choice") else "normal")
                if p.kind in ("logic", "choice") and not v.get() and not p.optional:
                    v.set(offer[0])
            else:
                w = ttk.Entry(self.form, textvariable=v, width=42)
            w.grid(row=n, column=1, sticky="w", pady=1)
            v.trace_add("write", lambda *a: self.put_line())
            self.fields.append(v)
        if self.what == "conditions":
            ttk.Checkbutton(self.form, variable=self.v_not, text="not - it holds when this is NOT true").grid(
                row=len(params) + 1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.form.columnconfigure(1, weight=1)
        self.put_line()

    def line(self):
        e = self.picked()
        if e is None:
            return ""
        return self.ED.compose(e, [v.get() for v in self.fields], self.v_not.get())

    def put_line(self):
        self.lbl_line.configure(text="The line: " + self.line() if self.picked() else "")

    def use(self):
        e = self.picked()
        if e is None:
            return
        empty = [p.label for p, v in zip(self.ED.params_of(e), self.fields) if not p.optional and not v.get().strip()]
        if empty:
            messagebox.showinfo(TITLE, "Fill in first: %s." % ", ".join(empty), parent=self)
            return
        self.on_pick(self.line())
        self.destroy()
