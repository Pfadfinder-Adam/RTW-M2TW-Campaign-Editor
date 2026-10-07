"""Regions picked on the campaign map (a tester: lists of regions are picked faster on the map): the map in a window
of its own in 'Select' mode - only the ground, a click on a town picks its region (yellow), again unpicks it."""

import tkinter as tk
from tkinter import messagebox, ttk


def pick_regions(parent, app, chosen, title="Pick regions on the map"):
    """The regions picked (a list, in the order picked), or None (Cancel)."""
    from .gui_map import MapView
    from .mapdata import CampaignMap
    try:
        cmap = app._cmap if getattr(app, "_cmap", None) is not None and app._cmap_for == (
            app.mod.data, app.v_campaign.get()) else CampaignMap(app.mod, app.v_campaign.get())
    except Exception as e:
        messagebox.showerror(title, "Cannot draw the map: %s" % e, parent=parent)
        return None
    w = tk.Toplevel(parent)
    w.title(title)
    w.transient(parent.winfo_toplevel())
    w.geometry("1100x760")
    view = MapView(w)
    view.pack(fill="both", expand=True)
    view.legend.pack_forget()                      # only towns are picked here
    view.b_resize.pack_forget()                    # picking towns: the map's size is not changed here
    from .mapdata import faction_colours
    try:
        owners = app.owners_after()
    except Exception:
        owners = {}
    view.load(cmap, owners, faction_colours(app.mod), None, ())
    view.v_pick.set(True)
    view._pick_toggled()
    order = [r for r in chosen if r in cmap.cities]
    view.picked = set(order)
    view.on_pick_menu = None
    old = view._picked_changed

    def changed():
        for r in list(order):
            if r not in view.picked:
                order.remove(r)
        order.extend(r for r in sorted(view.picked) if r not in order)
        old()
        lbl.configure(text="%d region(s) picked" % len(view.picked))
    view._picked_changed = changed
    bar = ttk.Frame(w, padding=6)
    bar.pack(fill="x")
    lbl = ttk.Label(bar, text="click a town to pick its region (yellow), again to unpick it")
    lbl.pack(side="left")
    out = {}

    def ok():
        out["v"] = list(order)
        w.destroy()
    ttk.Button(bar, text="OK", command=ok).pack(side="right")
    ttk.Button(bar, text="Cancel", command=w.destroy).pack(side="right", padx=4)
    w.update_idletasks()
    w.after(80, view.fit)                          # the whole map in the window once it has its size
    w.grab_set()
    parent.wait_window(w)
    return out.get("v")
