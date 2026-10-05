"""Bigger map (x3)... (the work bar): one window that says what happens, asks one thing (the heights), shows its
progress, writes with a backup and then offers to put the old map back. A tester pressed the button, saw the long
list of changes (it looked like a log), missed the 'Write it' buttons under it, found no bigger map in the game and
no way back - so the list is now behind 'Show every change...' and the window itself leads the way."""

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
    from .plan import Plan, restore_to
    from .upscale import FACTOR, TUNES, look_over, plan_upscale
    from .gui_util import hint
    if not app.mod:
        messagebox.showinfo(APP, "Load a mod first.")
        return
    if app.pending_parts():
        messagebox.showwarning(APP, "There are changes not written yet (%s). Apply or undo them first - the bigger "
                                    "map is built from the files as they are."
                               % ", ".join(label for _, label in app.pending_parts()))
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
    frm = ttk.Frame(w, padding=12)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="Make the campaign map 3 x bigger (alpha)", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frm, justify="left", wraplength=620, text="Campaign %s - %s%s" % (
        camp, _game_words(app.mod), "\nThe map now: %d x %d tiles  ->  after: %d x %d tiles" % (
            size[0], size[1], size[0] * FACTOR, size[1] * FACTOR) if size else "")).pack(anchor="w", pady=(4, 0))
    ttk.Label(frm, justify="left", wraplength=620, text=(
        "Every tile becomes a block of 3 x 3 tiles. Towns, ports, armies, agents, resources and forts keep their "
        "places (in the middle of their blocks); the coast is drawn smooth, rivers run on to the new coast, the "
        "relief stays smooth, and the campaign's scripts and events move with the map. Nothing is written until "
        "you press the button below; a backup is made first, and this window then offers to put the old map "
        "back.")).pack(anchor="w", pady=(8, 0))
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
    state = ttk.Label(frm, textvariable=v_state, justify="left", wraplength=620)
    state.pack(anchor="w", pady=(10, 0))
    bar = ttk.Frame(frm)
    bar.pack(anchor="e", pady=(10, 0))
    plans, warns, done = {}, {}, {}

    def make_plan():
        tune = values()
        if tune is None:
            return None
        key = tuple(sorted(tune.items()))
        if key in plans:
            return plans[key]
        p = Plan(ModData(app.mod.data), "map", "map_x3", {})
        w.config(cursor="watch")
        buttons(False)

        def step(text):                           # a big map takes a minute or two: say what is being done
            v_state.set("Working (a big map takes a minute or two): %s" % text)
            w.update()
        try:
            warns[key] = plan_upscale(p, camp, progress=step, tune=tune)
        except Exception as e:
            log.write("upscale failed: %s" % e)
            v_state.set("The map could not be made bigger: %s" % e)
            return None
        finally:
            if w.winfo_exists():
                w.config(cursor="")
                buttons(True)
        plans[key] = p
        v_state.set("Ready: %d file(s) will change. Nothing is written yet." % len(p.changed_files()))
        return p

    def show_all():
        p = make_plan()
        if p:
            app.show_text("Every change of the bigger map - nothing written yet", p.report())

    def write():
        p = make_plan()
        if not p:
            return
        try:
            bdir = p.apply()
        except Exception as e:
            messagebox.showerror(APP, "Not written: %s" % e, parent=w)
            return
        done["bdir"] = bdir
        done["key"] = next((k for k, v in plans.items() if v is p), None)
        log.write("Map made 3 x bigger (backup %s)\n%s" % (bdir, p.report()))
        app.load()
        try:
            img = ModData(app.mod.data).region_map(camp)
            now = " (%d x %d tiles)" % (img.width, img.height)
        except Exception:
            now = ""
        app.status.set("The map is 3 x bigger now%s - written (backup %s)." % (now, bdir))
        v_state.set("DONE: the map is 3 x bigger now%s.\nLook it over (what to look at: the message that opened), "
                    "then start the game - on the first start the game builds map.rwm again, which takes a while.\n"
                    "Not happy with it? 'Put the old map back' undoes it (or later: Tools > Restore a backup...)."
                    % now)
        for b in bar.winfo_children():
            b.destroy()
        for r in radios:                          # written: the choice is made
            r.state(["disabled"])
        ttk.Button(bar, text="Put the old map back", command=undo).pack(side="left")
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))
        messagebox.showinfo(APP, look_over(warns.get(done.get("key"), ())), parent=w)   # look it over yourself

    def undo():
        bdir = done.get("bdir")
        if not bdir or not messagebox.askyesno(APP, "Put the old map back? Every file the bigger map changed is "
                                                    "put back as it was (and every change made after it).", parent=w):
            return
        try:
            restore_to(ModData(app.mod.data), bdir)
        except (ValueError, OSError) as e:
            messagebox.showerror(APP, "Not undone: %s" % e, parent=w)
            return
        log.write("The bigger map undone (backup %s restored)" % bdir)
        app.load()
        app.status.set("The old map is back (backup %s restored)." % bdir)
        v_state.set("The old map is back - every file as it was before.")
        for b in bar.winfo_children():
            b.destroy()
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="left")

    def buttons(on):
        for b in bar.winfo_children():
            try:
                b.state(["!disabled"] if on else ["disabled"])
            except tk.TclError:
                pass

    ttk.Button(bar, text="Make the map 3 x bigger", command=write).pack(side="left")
    ttk.Button(bar, text="Show every change...", command=show_all).pack(side="left", padx=(6, 0))
    ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))
    return w
