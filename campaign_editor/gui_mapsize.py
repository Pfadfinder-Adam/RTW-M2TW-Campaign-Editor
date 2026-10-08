"""Map size... (the button beside the map's size under the map): tiles added at an edge of the campaign map (deep sea)
or cut off it, every place on the map moved with it (mapresize). The edges are dragged on the map itself (an orange
frame with a grip on each side: out = new sea, drawn blue; in = cut off, drawn dark) or typed as numbers - both stay
in step. What stands on the part cut off is ringed red on the map and named in the window; it goes with the cut
after a question (mapresize.clear_cut), so the modder may move it first; a faction left without a town leaves this
campaign with it (factionout - it stays in the mod). The cut is KEPT FOR APPLY, not written at once: it is made at the
write, after every other change waiting (App.session_add build=), so a town given on the Map meanwhile counts - the
faction that gets one stays and its family moves there. Undo this write / Restore give the old map back."""

import tkinter as tk
from tkinter import messagebox, ttk

from .gui_util import ShortHint
from .gui_util import ask
from . import log

APP = "RTW & M2TW Campaign Editor"
SIDES = (("left", "Left"), ("right", "Right"), ("top", "Top"), ("bottom", "Bottom"))


def open_map_size(app, view=None):
    """The window (App.map_size_window); view = the map whose edges are dragged (the main window's by default)."""
    from .mapresize import blocking, cut_words, lost_factions, places, plan_resize
    from .moddata import ModData
    from .plan import Plan
    if not app.mod:
        messagebox.showinfo(APP, "Load a mod first.")
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
        "water; paint land on it with the Map editor and the Terrain tab. Below 0 cuts them off. What stands on the "
        "part cut off is ringed red on the map and named here: it goes with the cut - towns with their regions (the "
        "land of theirs that stays is left with no region: paint it into one yourself, Edit regions), armies, agents, "
        "fleets, resources, forts, events - after a "
        "question, so you can move what you want to keep first; family members are never deleted, they move to "
        "their faction's nearest town. A faction left without any town leaves this campaign with all its people (it "
        "stays in the mod: its units, pictures, other campaigns). Everything that stays moves with the map. The cut "
        "waits for Apply changes (bottom left): until then give such a faction a town that stays (Map: right click "
        "a town > Give this town to) and it stays, its family moving into that town. A backup is made first; Undo "
        "this write or Tools > Restore a backup gives every file back.")
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
        """What stands on the part a cut takes off, as mapresize.places gives it."""
        if found is None or not n:
            return []
        return blocking(found, w0, h0, **n)

    def lost(n):
        """{faction: its towns cut off} of the factions the cut leaves without a town - the towns given on the Map
        and not written yet counted."""
        if not n or not any(v < 0 for v in n.values()):
            return {}
        try:
            return lost_factions(app.mod, camp, owners=app.owners_after(), **n)
        except (OSError, ValueError):
            return {}

    def after(*_):
        n = numbers()
        if n is None:
            v_after.set("only whole numbers, please")
            return
        W, H = w0 + n["left"] + n["right"], h0 + n["top"] + n["bottom"]
        if not done.get("bdir"):
            v_state.set("")                          # an older 'Not possible' / 'Ready' no longer holds
        v_after.set("after: %d x %d tiles" % (W, H) + ("" if any(n.values()) else " (as it is)"))
        hit = in_the_way(n)
        if W < 1 or H < 1:
            lbl_block.configure(text="The map would have no tiles left.")
        elif hit:
            gone = lost(n)
            lbl_block.configure(text="On the part cut off (ringed red on the map) - it goes with the cut, you are "
                                     "asked first (or move it away before):\n%s%s" % (
                                         "\n".join("- " + x for x in cut_words(hit)),
                                         "".join("\n- %s keeps no town - it leaves this campaign with the cut (give "
                                                 "it a town that stays to keep it)" % f for f in gone)))
        else:
            lbl_block.configure(text="")
        if view is not None and not done["syncing"] and getattr(view, "edge_mode", False):
            view.set_edges(n, blocked=[x[1] for x in hit])

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

    def build(n, out):
        """The cut's plan on the files as they are at this moment (at the write: as every other part left them)."""
        p = Plan(ModData(app.mod.data), "map", "map_size", {})
        done["warn"] = plan_resize(p, camp, clear=any(v < 0 for v in n.values()), factions_out=out, **n)
        return p

    def make_plan(keep=False):
        n = numbers()
        if n is None:
            messagebox.showerror(APP, "Only whole numbers, please.", parent=w)
            return None
        hit = in_the_way(n)
        gone = lost(n)
        try:                                         # checked now on the files as they are (a refusal said at once)
            p = build(n, tuple(gone) + tuple(lost_factions(app.mod, camp, **n)) if hit else ())
        except ValueError as e:
            v_state.set("Not possible: %s" % e)
            log.write("Map size: not kept - %s" % e)
            messagebox.showwarning(APP, "The map's size cannot be changed like this:\n\n%s" % e, parent=w)
            return None
        # asked only once the cut is known to be possible (a refusal is said first, without a question)
        if hit and keep and not ask(
                APP, "The cut takes these off the map with it:\n\n- %s%s\n\nNothing is written now: the cut waits for "
                     "Apply changes (a backup first; Undo this write gives every one back). Until then you can move "
                     "what you want to keep off the part cut off on the map%s." % (
                         "\n- ".join(cut_words(hit)),
                         "".join("\n- %s keeps no town (%s) - it leaves this campaign with all its people; the "
                                 "faction stays in the mod" % (f, ", ".join(t[:4]) + (" ..." if len(t) > 4 else ""))
                                 for f, t in gone.items()),
                         ", or give a faction that keeps no town a town that stays (right click a town > Give this "
                         "town to) - then it stays and its family moves there" if gone else ""),
                parent=w, yes="Keep the cut for Apply", no="Not now"):
            v_state.set("Not kept - nothing changed.")
            return None
        v_state.set("Ready: %d file(s) will change%s. Nothing is written yet." % (
            len(p.changed_files()), ", %d thing(s) on the part cut off go with it" % len(hit) if hit else ""))
        return p, n, tuple(gone)

    def show_all():
        got = make_plan()
        if got:
            app.show_text("Every change of the map's size - nothing written yet", got[0].report())

    def keep():
        got = make_plan(keep=True)
        if not got:
            return
        p, n, gone = got
        W, H = w0 + n["left"] + n["right"], h0 + n["top"] + n["bottom"]
        label = "Map size: %d x %d -> %d x %d tiles%s" % (w0, h0, W, H, "; leave the campaign: %s" % ", ".join(gone)
                                                           if gone else "")

        def written(bdir):
            log.write("Map size changed (backup %s)%s" % (bdir, "".join("\n- " + x for x in done.get("warn") or ())))
        app.session_add("map_size", label, None, after=written, build=lambda: build(n, gone))
        v_state.set("KEPT for Apply: %s. Apply changes (bottom left) writes it after every other change waiting - "
                    "a town given on the Map meanwhile counts. On the first start the game builds map.rwm again (a "
                    "while)." % label)
        for b in bar.winfo_children():
            b.destroy()
        ttk.Button(bar, text="Keep for Apply", command=keep).pack(side="left")
        ttk.Button(bar, text="Preview", command=show_all).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Throw the cut away", command=throw).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))

    def throw():
        app.session_drop("map_size")
        v_state.set("The kept change of the map's size is thrown away - nothing will be written for it.")

    if app.session_kept("map_size"):
        v_state.set("A change of the map's size is kept for Apply already - Keep for Apply replaces it.")
    ttk.Button(bar, text="Keep for Apply", command=keep).pack(side="left")
    ttk.Button(bar, text="Preview", command=show_all).pack(side="left", padx=(6, 0))
    ttk.Button(bar, text="Close", command=w.destroy).pack(side="left", padx=(6, 0))
    return w
