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
        self.lbl_plain = ttk.Label(pl, wraplength=1150, justify="left", foreground="#1d3b6a", font=("", 10))
        self.lbl_plain.pack(anchor="w")
        self.lbl_bad = ttk.Label(low, wraplength=1180, justify="left")
        self.lbl_bad.pack(anchor="w", pady=(4, 0))
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
        self.recipe["title"] = self.v_title.get()
        self.recipe["game"] = next((k for k, l in GAMES if l == self.v_game.get()), "both")
        self.recipe["once"] = bool(self.v_once.get())
        self.changed = True
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
            tk.Label(f, text=ev.help[0].upper() + ev.help[1:] + ".", bg=c, fg="#444", wraplength=820,
                     justify="left").pack(anchor="w", padx=18)
            tk.Label(f, bg=c, fg="#444", text="It brings along: " + ", ".join(
                MB.SUBJECT_WORDS[s] for s in ev.subjects) + " - the conditions and actions below work on them.").pack(
                anchor="w", padx=18, pady=(0, 6))

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
                               width=max(len(p.label) for p in parts) - 10)
            pcb.pack(side="left")
            pcb.bind("<<ComboboxSelected>>", lambda e, g=group, n=i, v=pv: self.change_part(g, n, v.get()))
            for name, kind, label, _ in (part.fields if part else []):
                self._field(row, c, group, i, it, part, name, kind, label)
            tk.Button(row, text="x", relief="flat", bg=c, fg="#a00", activebackground=c, cursor="hand2",
                      command=lambda g=group, n=i: self.remove(g, n)).pack(side="left", padx=6)
            if part and part.help:
                hint(row, part.help).pack(side="left")
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
        if kind in NUMBERS or kind in ("text", "long"):
            v = tk.StringVar(value="" if it.get(name) is None else str(it.get(name)))
            ttk.Entry(row, textvariable=v, width={"text": 24, "long": 36}.get(kind, 8)).pack(side="left", padx=2)
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
        elif kind.startswith("names:"):
            what = kind.split(":")[1]
            v = tk.StringVar(value=", ".join(it.get(name) or []))
            ttk.Entry(row, textvariable=v, width=34).pack(side="left", padx=2)
            v.trace_add("write", lambda *a: self.set_value(group, i, name, kind, v.get()))
            ttk.Button(row, text="Pick...", command=lambda: self.pick_many(what, v)).pack(side="left", padx=2)
        if label and not before:
            tk.Label(row, text=label, bg=c, fg="#1e1e1e").pack(side="left", padx=(2, 6))

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
            e = ttk.Entry(r, textvariable=lab, width=34)
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
        have = set(ev.subjects) if ev else set()
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
