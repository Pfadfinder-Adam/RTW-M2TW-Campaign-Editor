"""Bigger map (x3)... (the work bar): one window that leads through the five steps of upsteps - each written with a
backup and checked, the map in the editor between them to look at and fix by hand - and puts the old map back with
one button. The values (heights, smoothing...) are fields of their own; the list of changes is behind 'Show every
change...' (a tester once took the long list for a log and missed the button under it)."""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from . import log

APP = "RTW & M2TW Campaign Editor"
def _game_words(mod):
    from .limits import engine_of, game_kind
    game = "Medieval II" if game_kind(mod) == "medieval2" else "Rome"
    eng = engine_of(mod)
    if eng:
        return "%s (with %s)" % (game, eng.replace(".exe", ""))
    return "%s (the original exe - a map this big needs %s)" % (game, "M2EX" if game == "Medieval II" else "REX")


def _num(v):
    """A value as the field shows it: 3 not 3.0, 0.55 not 0.5500000001."""
    return ("%.2f" % v).rstrip("0").rstrip(".")


def open_upscale(app):
    """The window of Bigger map (x3)... (App.upscale_map)."""
    from .moddata import ModData
    from .plan import restore_to
    from .upscale import FACTOR, TUNES, look_over
    from .gui_util import hint
    if not app.mod:
        messagebox.showinfo(APP, "Load a mod first.")
        return
    camp = app.v_campaign.get()
    try:
        img = app.mod.region_map(camp)
        size = (img.width, img.height)
    except Exception:
        size = None
    w = tk.Toplevel(app)
    w.title("Make the campaign map 3 x bigger")
    w.transient(app)
    from .gui_util import window_body
    frm, bottom = window_body(w, 720, 760)            # resizable, scrolls, the buttons always in sight
    ttk.Label(frm, text="Make the campaign map 3 x bigger (alpha)", font=("", 12, "bold")).pack(anchor="w")
    resume = _unfinished(app, camp)
    ttk.Label(frm, justify="left", wraplength=620, text="Campaign %s - %s%s" % (
        camp, _game_words(app.mod), ("\nThe map now: %d x %d tiles (3 x bigger since step 1)" % size if resume else
                                     "\nThe map now: %d x %d tiles  ->  after: %d x %d tiles" % (
                                         size[0], size[1], size[0] * FACTOR, size[1] * FACTOR)) if size else "")
              ).pack(anchor="w", pady=(4, 0))
    ttk.Label(frm, justify="left", wraplength=620, text=(
        "Every tile becomes a block of 3 x 3 tiles, in five steps: the grid, smoothing, heights, rivers, objects. "
        "Each step is written with a backup and checked; between the steps the map is in the Map editor - look at "
        "it, fix what you want by hand (borders after step 2, the coast before step 3, the ground after step 3), "
        "then do the next step. Towns, ports, armies, agents, resources and forts keep their places (in the middle "
        "of their blocks), and the campaign's scripts and events move with the map. 'Put the old map back' undoes "
        "every step at once. You may close this window between the steps: opened again, it goes on where it "
        "stopped.")).pack(anchor="w", pady=(8, 0))
    ttk.Label(frm, text="Values (the shore by the water is the game's own and stays as it is)",
              font=("", 10, "bold")).pack(anchor="w", pady=(10, 0))
    grid = ttk.Frame(frm)
    grid.pack(anchor="w", pady=(2, 0))
    fields, radios = {}, []                       # radios: every input, greyed once the map is written
    for row, (key, (words, default, lo, hi, about)) in enumerate(TUNES.items()):
        ttk.Label(grid, text=words).grid(row=row, column=0, sticky="w", pady=1)
        var = tk.StringVar(value=_num(default))
        box = ttk.Spinbox(grid, textvariable=var, from_=lo, to=hi, increment=0.05 if hi <= 1 else 0.1 if hi <= 3
                          else 0.5, width=6)
        box.grid(row=row, column=1, sticky="w", padx=(8, 0))
        ttk.Label(grid, foreground="#666", text="default %s  (%s - %s)" % (_num(default), _num(lo), _num(hi))).grid(
            row=row, column=2, sticky="w", padx=(6, 0))
        hint(grid, about, width=480).grid(row=row, column=3, sticky="w")
        fields[key] = var
        radios.append(box)

    def defaults():
        for key, var in fields.items():
            var.set(_num(TUNES[key][1]))
    reset = ttk.Button(frm, text="Back to the defaults", command=defaults)
    reset.pack(anchor="w", pady=(4, 0))
    radios.append(reset)

    def values():
        """The fields as numbers, each kept within its range; None (and a message) when one is not a number."""
        out = {}
        for key, var in fields.items():
            try:
                v = float(var.get().replace(",", "."))
            except ValueError:
                messagebox.showerror(APP, "'%s' is not a number: %s" % (TUNES[key][0], var.get()), parent=w)
                return None
            out[key] = min(max(v, TUNES[key][2]), TUNES[key][3])
            var.set(_num(out[key]))
        return out
    v_state = tk.StringVar(value="")
    # the five steps (upsteps.STEPS): each written with its own backup and checked; between them the map is in the
    # editor - look, fix by hand, then the next step
    from .upsteps import STEPS, check_step, plan_step
    steps_box = ttk.Frame(frm)
    steps_box.pack(anchor="w", pady=(10, 0))
    ttk.Label(steps_box, text="Step by step - look at the map after each, fix what you want, then the next",
              font=("", 10, "bold")).pack(anchor="w")
    marks = []
    for n, (_, words) in enumerate(STEPS):
        lbl = ttk.Label(steps_box, text="", justify="left")
        lbl.pack(anchor="w")
        marks.append((lbl, words))
    st = {}
    if resume:
        st.update(resume)
    state = ttk.Label(frm, textvariable=v_state, justify="left", wraplength=620)
    state.pack(anchor="w", pady=(10, 0))
    bar = ttk.Frame(bottom)
    bar.pack(anchor="e")

    def show_marks():
        done = st.get("done", 0)
        for n, (lbl, words) in enumerate(marks):
            lbl.configure(text="%s %d. %s" % ("\u2714" if n < done else "\u25b6" if n == done else "   ", n + 1, words),
                          foreground="#2a8a2a" if n < done else "")
        for r in radios:                          # the values serve steps 2 and 3: fixed once those are done
            r.state(["disabled"] if done >= 3 else ["!disabled"])
        buttons()

    def step():
        k = st.get("done", 0)
        if k >= len(STEPS):
            return
        if app.pending_parts():
            messagebox.showwarning(APP, "There are changes not written yet in the main window (%s). Apply or undo "
                                        "them first - the next step reads the files as they are." % ", ".join(
                                            label for _, label in app.pending_parts()), parent=w)
            return
        tune = values()
        if tune is None:
            return
        w.config(cursor="watch")
        v_state.set("Working on step %d of %d: %s ... (step 2 and 3 take a minute or two)" % (
            k + 1, len(STEPS), STEPS[k][1]))
        w.update()
        try:
            plan, warn = plan_step(ModData(app.mod.data), camp, k, st, tune)
            bdir = plan.apply()
        except Exception as e:
            log.write("x3 step %d failed: %s" % (k + 1, e))
            v_state.set("Step %d could not be done: %s" % (k + 1, e))
            w.config(cursor="")
            return
        if k == 0:
            st["bdir"] = bdir
        st["done"] = k + 1
        _save_state(st, camp)
        log.write("x3 step %d (%s) written (backup %s)\n%s" % (k + 1, STEPS[k][0], bdir, plan.report()))
        app.load()
        found = check_step(ModData(app.mod.data), camp, k, st)
        w.config(cursor="")
        img = ModData(app.mod.data).region_map(camp)
        text = "Step %d done - the map is %d x %d tiles; look at it in the Map editor (Map and Terrain tabs)." % (
            k + 1, img.width, img.height)
        text += ("\nThe check after it: fine." if not found else
                 "\nThe check after it found:\n- " + "\n- ".join(found) + "\nFix it by hand, or go on.")
        if warn:
            text += "\nNote:\n- " + "\n- ".join(warn[:6])
        if k == 0:
            text += "\nFixes made now are drawn over by step 2 (it smooths from the old map): fix after step 2."
        if st["done"] == len(STEPS):
            text += "\nALL DONE. Look the map over (the message that opened says what), then start the game: on the " \
                    "first start it builds map.rwm again, which takes a while."
            messagebox.showinfo(APP, look_over(warn), parent=w)
        v_state.set(text)
        show_marks()

    def show_all():
        k = st.get("done", 0)
        if k >= len(STEPS):
            return
        tune = values()
        if tune is None:
            return
        w.config(cursor="watch")
        w.update()
        try:
            plan, _ = plan_step(ModData(app.mod.data), camp, k, st, tune)
        finally:
            w.config(cursor="")
        app.show_text("Step %d - every change, nothing written yet" % (k + 1), plan.report())

    def undo():
        bdir = st.get("bdir")
        if not bdir or not messagebox.askyesno(APP, "Put the old map back? Every file the steps changed is put "
                                                    "back as it was before step 1 (and every change made after "
                                                    "it).", parent=w):
            return
        try:
            restore_to(ModData(app.mod.data), bdir)
        except (ValueError, OSError) as e:
            messagebox.showerror(APP, "Not undone: %s" % e, parent=w)
            return
        log.write("The bigger map undone (backup %s restored)" % bdir)
        st.clear()
        app.load()
        app.status.set("The old map is back (backup %s restored)." % bdir)
        v_state.set("The old map is back - every file as it was before step 1.")
        show_marks()

    def buttons():
        for b in bar.winfo_children():
            b.destroy()
        k = st.get("done", 0)
        if k < len(STEPS):
            ttk.Button(bar, text="Do step %d: %s" % (k + 1, STEPS[k][0]), command=step).pack(side="left")
            ttk.Button(bar, text="Show every change...", command=show_all).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="right")
        if st.get("bdir"):          # undoes every step: set apart from 'Do step' (a hurried click must not land on it)
            ttk.Button(bar, text="Put the old map back", command=undo).pack(side="right", padx=(0, 24))

    if resume:
        v_state.set("This map is part-way through: %d of %d steps done. Go on with step %d, or put the old map "
                    "back." % (st["done"], len(STEPS), st["done"] + 1))
    show_marks()
    return w


STATE = "x3_steps.json"


def _save_state(st, campaign):
    """The steps done, kept in step 1's backup folder: the window goes on from there when opened again."""
    import json
    try:
        with open(os.path.join(st["bdir"], STATE), "w", encoding="utf-8") as fh:
            json.dump({"campaign": campaign, "done": st["done"], "bdir": st["bdir"],
                       "vertical": st.get("vertical"), "edges": st.get("edges")}, fh)
    except OSError:
        pass


def _unfinished(app, campaign):
    """The steps state of a bigger map begun and not finished on this campaign (the newest), else None."""
    import json
    from .plan import backups
    for b in backups(app.mod):
        p = os.path.join(b, STATE)
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as fh:
                    st = json.load(fh)
            except (OSError, ValueError):
                return None
            if st.get("campaign") == campaign and 0 < st.get("done", 0) < 5 and os.path.isdir(st.get("bdir", "")):
                return st
            return None
    return None
