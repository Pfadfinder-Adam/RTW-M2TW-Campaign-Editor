"""Map size... (the button beside the map's size under the map): tiles added at an edge of the campaign map (deep sea)
or cut off it, every place on the map moved with it (mapresize). The edges are dragged on the map itself (an orange
frame with a grip on each side: out = new sea, drawn blue; in = cut off, drawn dark) or typed as numbers - both stay
in step. What stands on the part cut off is ringed red on the map and named in the window before anything is
written. One window, as Bigger map (x3)...: what happens, the four edges, a backup, and the old map back with one
button."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import ShortHint
from .gui_util import ask
from . import log

APP = "RTW & M2TW Campaign Editor"
SIDES = (("left", "Left"), ("right", "Right"), ("top", "Top"), ("bottom", "Bottom"))
SHOWN = 6                                     # places on the cut part named in the window (all of them on the map)


def open_map_size(app, view=None):
    """The window (App.map_size_window); view = the map whose edges are dragged (the main window's by default)."""
    from .mapresize import blocking, places, plan_resize
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
    view = view or getattr(app, "map_view", None)
    if view is not None and not getattr(view, "cmap", None):
        view = None
    camp = app.v_campaign.get()
    img = app.mod.region_map(camp)
    w0, h0 = img.width, img.height
    try:
        found = places(app.mod, camp)               # every place on the map, read once: the window checks a cut live
    except (OSError, ValueError):
        found = None
    w = tk.Toplevel(app)
    w.title("Map size - add or cut tiles at the edges")
    w.transient(app)
    from .gui_util import window_body
    frm, bottom = window_body(w, 520, 520)            # resizable, scrolls, the buttons always in sight
    if view is not None:                              # at the main window's right (over the legend), not in the
        try:                                          # middle over the map whose edges are dragged
            w._centred = True
            w.geometry("+%d+%d" % (max(0, app.winfo_rootx() + app.winfo_width() - 540), app.winfo_rooty() + 110))
            w.attributes("-alpha", 1.0)
        except tk.TclError:
            pass
    ttk.Label(frm, text="Add or cut tiles at the edges of the map", font=("", 12, "bold")).pack(anchor="w")
    ttk.Label(frm, text="Campaign %s - the map now: %d x %d tiles." % (camp, w0, h0)).pack(anchor="w", pady=(4, 0))
    ttk.Label(frm, text=("Drag an edge of the map (the orange frame on the map) or type the numbers: out / above 0 "
                         "adds deep sea (blue), in / below 0 cuts the tiles off (dark)." if view else
                         "Type the numbers: above 0 adds deep sea, below 0 cuts the tiles off."),
              justify="left", wraplength=480).pack(anchor="w", fill="x", pady=(6, 0))
    ShortHint(frm, text=(
        "A number above 0 adds that many rows or columns of tiles at that edge - deep sea, as the map's own deepest "
        "water; paint land on it with the Map editor and the Terrain tab. Below 0 cuts them off - not while a town, "
        "port, army, agent, resource, fort or an event's place stands there (each is ringed red on the map and named "
        "here; move or delete it first). Towns, armies, agents, resources, forts, events and the campaign's scripts "
        "move with the map. Nothing is written until you press the button; a backup is made first.")
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
    lbl_block = ttk.Label(frm, text="", justify="left", wraplength=480, foreground="#c0392b")
    lbl_block.pack(anchor="w", fill="x", pady=(6, 0))
    v_state = tk.StringVar()
    ttk.Label(frm, textvariable=v_state, justify="left", wraplength=480).pack(anchor="w", pady=(8, 0))
    bar = ttk.Frame(bottom)
    bar.pack(anchor="e")
    done = {"syncing": False}

    def numbers():
        out = {}
        for key, v in vars_.items():
            try:
                out[key] = int(v.get().strip() or 0)
            except ValueError:
                return None
        return out

    def in_the_way(n):
        """What stands on the part a cut takes off: ['what (x, y)'], their tiles for the map."""
        if found is None or not n:
            return [], []
        hit = blocking(found, w0, h0, **n)
        return [label for label, _ in hit], [xy for _, xy in hit]

    def after(*_):
        n = numbers()
        if n is None:
            v_after.set("only whole numbers, please")
            return
        W, H = w0 + n["left"] + n["right"], h0 + n["top"] + n["bottom"]
        if not done.get("bdir"):
            v_state.set("")                          # an older 'Not possible' / 'Ready' no longer holds
        v_after.set("after: %d x %d tiles" % (W, H) + ("" if any(n.values()) else " (as it is)"))
        names, tiles = in_the_way(n)
        if W < 1 or H < 1:
            lbl_block.configure(text="The map would have no tiles left.")
        elif names:
            lbl_block.configure(text="%d place(s) stand on the part cut off (ringed red on the map) - move or delete "
                                     "them first, or cut less:\n%s" % (
                                         len(names), "\n".join("- " + x for x in names[:SHOWN])
                                         + ("\n... and %d more" % (len(names) - SHOWN) if len(names) > SHOWN else "")))
        else:
            lbl_block.configure(text="")
        if view is not None and not done["syncing"] and getattr(view, "edge_mode", False):
            view.set_edges(n, blocked=tiles)

    def from_the_map(edges):
        """An edge dragged on the map: its numbers into the boxes (and the check above)."""
        done["syncing"] = True
        try:
            for key, v in vars_.items():
                if str(edges.get(key, 0)) != v.get().strip():
                    v.set(str(edges.get(key, 0)))
        finally:
            done["syncing"] = False
        after()

    for v in vars_.values():
        v.trace_add("write", after)
    if view is not None:
        view.show_edges(dict.fromkeys(vars_, 0), from_the_map)
        try:                                         # the whole map in sight left of this window, room round it
            cv = view.canvas
            covered = cv.winfo_rootx() + cv.winfo_width() - (app.winfo_rootx() + app.winfo_width() - 540) + 10
            view.fit_beside(free=max(0, covered))
        except tk.TclError:
            view.fit()
    after()

    def leave_the_map():
        if view is not None and getattr(view, "edge_mode", False):
            try:
                view.hide_edges()
            except tk.TclError:
                pass

    def closed(e):
        if e.widget is w:
            leave_the_map()
    w.bind("<Destroy>", closed, add="+")

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
            log.write("Map size: not written - %s" % e)
            messagebox.showwarning(APP, "The map's size cannot be changed like this:\n\n%s" % e, parent=w)
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
            log.write("Map size: not written - %s" % e)
            messagebox.showerror(APP, "Not written: %s" % e, parent=w)
            return
        done["bdir"] = bdir
        log.write("Map size changed (backup %s)\n%s" % (bdir, p.report()))
        leave_the_map()
        app.load()
        now = ModData(app.mod.data).region_map(camp)
        if view is not None:
            try:
                view.fit()
            except tk.TclError:
                pass
        app.status.set("The map is %d x %d tiles now - written (backup %s)." % (now.width, now.height, bdir))
        v_state.set("DONE: the map is %d x %d tiles now. On the first start the game builds map.rwm again (a "
                    "while).%s\nNot happy with it? 'Put the old map back' undoes it (or later: Tools > Restore a "
                    "backup...)." % (now.width, now.height, "".join("\n- " + x for x in done.get("warn") or ())))
        lbl_block.configure(text="")
        for b in bar.winfo_children():
            b.destroy()
        ttk.Button(bar, text="Put the old map back", command=undo).pack(side="left")
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))

    def undo():
        bdir = done.get("bdir")
        if not bdir or not ask(APP, "Put the old map back? Every file the new size changed is put "
                                    "back as it was (and every change made after it).", parent=w,
                               yes='Put the old map back', no='Cancel'):
            return
        try:
            restore_to(ModData(app.mod.data), bdir)
        except (ValueError, OSError) as e:
            messagebox.showerror(APP, "Not undone: %s" % e, parent=w)
            return
        log.write("Map size undone (backup %s restored)" % bdir)
        app.load()
        if view is not None:
            try:
                view.fit()
            except tk.TclError:
                pass
        app.status.set("The old map is back (backup %s restored)." % bdir)
        v_state.set("The old map is back - every file as it was before.")
        for b in bar.winfo_children():
            b.destroy()
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="left")

    ttk.Button(bar, text="Write it in", command=write).pack(side="left")
    ttk.Button(bar, text="Preview", command=show_all).pack(side="left", padx=(6, 0))
    ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))
    return w
