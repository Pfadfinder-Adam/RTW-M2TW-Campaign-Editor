"""Bigger map (x3)... (the work bar): one window that says what happens, asks one thing (the heights), shows its
progress, writes with a backup and then offers to put the old map back. A tester pressed the button, saw the long
list of changes (it looked like a log), missed the 'Write it' buttons under it, found no bigger map in the game and
no way back - so the list is now behind 'Show every change...' and the window itself leads the way."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import log

APP = "RTW & M2TW Campaign Editor"
EDGES = (
    ("smooth", "Smooth - as water finds its level: coasts, wide rivers, borders and the edges of ground and climates "
               "run as smooth lines (no 3 x 3 steps)"),
    ("light", "Smooth, lighter - the same, 1.5 x weaker: closer to the old shapes"),
    ("winding", "Winding - bays and capes, every old tile's corner kept (small steps can stay)"),
)
HEIGHTS = (
    (3, "Hills 3 x higher - they look as they did (the land is 3 x wider, so this keeps them as steep)"),
    (1, "Heights as they are - a flatter world"),
)


def _game_words(mod):
    from .limits import engine_of, game_kind
    game = "Medieval II" if game_kind(mod) == "medieval2" else "Rome"
    eng = engine_of(mod)
    if eng:
        return "%s (with %s)" % (game, eng.replace(".exe", ""))
    return "%s (the original exe - a map this big needs %s)" % (game, "M2EX" if game == "Medieval II" else "REX")


def open_upscale(app):
    """The window of Bigger map (x3)... (App.upscale_map)."""
    from .moddata import ModData
    from .plan import Plan, restore_to
    from .upscale import FACTOR, look_over, plan_upscale
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
    ttk.Label(frm, text="The heights", font=("", 10, "bold")).pack(anchor="w", pady=(10, 0))
    v_high = tk.IntVar(value=3)
    radios = [ttk.Radiobutton(frm, text=text, variable=v_high, value=val) for val, text in HEIGHTS]
    for r in radios:
        r.pack(anchor="w")
    ttk.Label(frm, text="The lines (coast, rivers drawn as sea, borders, ground, climates)",
              font=("", 10, "bold")).pack(anchor="w", pady=(10, 0))
    v_edges = tk.StringVar(value="smooth")
    radios += [ttk.Radiobutton(frm, text=text, variable=v_edges, value=val) for val, text in EDGES]
    for r in radios[len(HEIGHTS):]:
        r.pack(anchor="w")
    v_state = tk.StringVar(value="")
    state = ttk.Label(frm, textvariable=v_state, justify="left", wraplength=620)
    state.pack(anchor="w", pady=(10, 0))
    bar = ttk.Frame(frm)
    bar.pack(anchor="e", pady=(10, 0))
    plans, warns, done = {}, {}, {}

    def make_plan():
        vertical, edges = v_high.get(), v_edges.get()
        key = (vertical, edges)
        if key in plans:
            return plans[key]
        p = Plan(ModData(app.mod.data), "map", "map_x3", {})
        w.config(cursor="watch")
        buttons(False)

        def step(text):                           # a big map takes a minute or two: say what is being done
            v_state.set("Working (a big map takes a minute or two): %s" % text)
            w.update()
        try:
            warns[key] = plan_upscale(p, camp, vertical=vertical, progress=step, edges=edges)
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
        messagebox.showinfo(APP, look_over(warns.get((v_high.get(), v_edges.get()), ())), parent=w)   # look it over yourself

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
