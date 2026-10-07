"""Map size... (the button beside the map's size under the map): tiles added at an edge of the campaign map (deep sea)
or cut off it, every place on the map moved with it (mapresize). One window, as Bigger map (x3)...: what happens,
the four edges, a backup, and the old map back with one button."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import ShortHint
from .gui_util import ask
from . import log

APP = "RTW & M2TW Campaign Editor"
SIDES = (("left", "Left"), ("right", "Right"), ("top", "Top"), ("bottom", "Bottom"))


def open_map_size(app):
    """The window (App.map_size_window)."""
    from .mapresize import plan_resize
    from .moddata import ModData
    from .plan import Plan, restore_to
    if not app.mod:
        messagebox.showinfo(APP, "Load a mod first.")
        return None
    if app.pending_parts():
        messagebox.showwarning(APP, "There are changes not written yet (%s). Apply or undo them first - the map is "
                                    "changed from the files as they are."
                               % ", ".join(label for _, label in app.pending_parts()))
        return None
    camp = app.v_campaign.get()
    img = app.mod.region_map(camp)
    w0, h0 = img.width, img.height
    w = tk.Toplevel(app)
    w.title("Map size - add or cut tiles at the edges")
    w.transient(app)
    from .gui_util import window_body
    frm, bottom = window_body(w, 640, 520)            # resizable, scrolls, the buttons always in sight
    ttk.Label(frm, text="Add or cut tiles at the edges of the map", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frm, text="Campaign %s - the map now: %d x %d tiles." % (camp, w0, h0)).pack(anchor="w", pady=(4, 0))
    ShortHint(frm, text=(
        "Above 0 adds tiles of deep sea at that edge, below 0 cuts tiles off. A number above 0 adds that many rows or columns of tiles at "
        "that edge - deep sea, as the map's own deepest water; paint land on it with the Map editor and the Terrain "
        "tab. Below 0 cuts them off (refused when a town, port, army, resource, fort or an event's place stands "
        "there - each is named). Towns, armies, agents, resources, forts, events and the campaign's scripts move "
        "with the map. Nothing is written until you press the button; a backup is made first.")
              ).pack(anchor="w", fill="x", pady=(4, 0))
    grid = ttk.Frame(frm)
    grid.pack(anchor="w", pady=(10, 0))
    vars_ = {}
    for i, (key, words) in enumerate(SIDES):
        ttk.Label(grid, text=words).grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=(0 if i % 2 == 0 else 18, 6),
                                         pady=2)
        v = tk.StringVar(value="0")
        ttk.Spinbox(grid, textvariable=v, from_=-999, to=999, increment=1, width=6).grid(
            row=i // 2, column=(i % 2) * 2 + 1, sticky="w")
        vars_[key] = v
    v_after = tk.StringVar()
    ttk.Label(frm, textvariable=v_after, font=("", 10, "bold")).pack(anchor="w", pady=(8, 0))
    v_state = tk.StringVar()
    ttk.Label(frm, textvariable=v_state, justify="left", wraplength=560).pack(anchor="w", pady=(8, 0))
    bar = ttk.Frame(bottom)
    bar.pack(anchor="e")
    done = {}

    def numbers():
        out = {}
        for key, v in vars_.items():
            try:
                out[key] = int(v.get().strip() or 0)
            except ValueError:
                return None
        return out

    def after(*_):
        n = numbers()
        v_after.set("after: %d x %d tiles" % (w0 + n["left"] + n["right"], h0 + n["top"] + n["bottom"]) if n
                    else "only whole numbers, please")
    for v in vars_.values():
        v.trace_add("write", after)
    after()

    def make_plan():
        n = numbers()
        if n is None:
            messagebox.showerror(APP, "Only whole numbers, please.", parent=w)
            return None
        p = Plan(ModData(app.mod.data), "map", "map_size", {})
        try:
            done["warn"] = plan_resize(p, camp, **n)
        except ValueError as e:
            v_state.set("Not possible: %s" % e)
            return None
        v_state.set("Ready: %d file(s) will change. Nothing is written yet." % len(p.changed_files()))
        return p

    def show_all():
        p = make_plan()
        if p:
            app.show_text("Every change of the map's size - nothing written yet", p.report())

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
        log.write("Map size changed (backup %s)\n%s" % (bdir, p.report()))
        app.load()
        now = ModData(app.mod.data).region_map(camp)
        app.status.set("The map is %d x %d tiles now - written (backup %s)." % (now.width, now.height, bdir))
        v_state.set("DONE: the map is %d x %d tiles now. On the first start the game builds map.rwm again (a "
                    "while).%s\nNot happy with it? 'Put the old map back' undoes it (or later: Tools > Restore a "
                    "backup...)." % (now.width, now.height, "".join("\n- " + x for x in done.get("warn") or ())))
        for b in bar.winfo_children():
            b.destroy()
        ttk.Button(bar, text="Put the old map back", command=undo).pack(side="left")
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))

    def undo():
        bdir = done.get("bdir")
        if not bdir or not ask(APP, "Put the old map back? Every file the new size changed is put "
                                                    "back as it was (and every change made after it).", parent=w, yes='Put the old map back', no='Cancel'):
            return
        try:
            restore_to(ModData(app.mod.data), bdir)
        except (ValueError, OSError) as e:
            messagebox.showerror(APP, "Not undone: %s" % e, parent=w)
            return
        log.write("Map size undone (backup %s restored)" % bdir)
        app.load()
        app.status.set("The old map is back (backup %s restored)." % bdir)
        v_state.set("The old map is back - every file as it was before.")
        for b in bar.winfo_children():
            b.destroy()
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="left")

    ttk.Button(bar, text="Write it in", command=write).pack(side="left")
    ttk.Button(bar, text="Preview", command=show_all).pack(side="left", padx=(6, 0))
    ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))
    return w
