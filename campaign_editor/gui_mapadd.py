"""Armies, fleets and agents put on the Map for ANY faction (a tester: "adding on the map should not depend on the
faction picked in another window"): the owner comes from where it is put - the faction holding that land (a fleet:
the owner of the nearest land) - and the window lets another faction be picked. The faction being made or edited
gets it in its own list (Units & armies, as before); any other faction's goes into App.map_chars, written with the
next Apply by edit.map_changes, its army or fleet starting with the first unit of that faction's nearest army
(the general's bodyguard; changed later in Edit faction)."""

import tkinter as tk
from tkinter import messagebox, ttk

APP = "RTW & M2TW Campaign Editor"


def owner_at(app, xy):
    """The faction holding the land at tile xy as the next Apply leaves it (a town given on the Map counts); on
    the sea the owner of the nearest land. None when nobody does."""
    cm = app._cmap
    if cm is None:
        return None
    owners = app.owners_after()
    region = cm.region_at(*xy) if 0 <= xy[0] < cm.w and 0 <= xy[1] < cm.h else None
    if region:
        return owners.get(region) or "slave"
    best = None
    for r, (tx, ty) in cm.cities.items():
        d = (tx - xy[0]) ** 2 + (ty - xy[1]) ** 2
        if best is None or d < best[0]:
            best = (d, r)
    return (owners.get(best[1]) or "slave") if best else None


def factions_here(app):
    """Every faction with a block in descr_strat (the rebels too)."""
    return [fb.name for fb in app.strat.factions] if app.strat else []


def taken_names(app, faction):
    from .strat import faction_names
    names = set(faction_names(app.strat, faction)) if app.strat else set()
    names |= {c["name"] for c in app.map_chars.get(faction, [])}
    if faction == app.field_faction():
        names |= set(app._faction_names())
    return names


def add_at(app, kind, xy, preset=None, faction=None):
    """The window for a new army / fleet / agent put at tile xy: faction (by the land there, changeable), the
    agent's kind, name and age."""
    from .strat import FEMALE_KINDS, first_names
    from .gui_util import FactionBox
    camp = app.v_campaign.get()
    sea = app.mod.is_sea(camp, xy)
    if kind == "fleet" and not sea:
        messagebox.showerror(APP, "A fleet goes on the sea - click a sea tile.")
        return
    facs = factions_here(app)
    if not facs:
        return
    v_fac = tk.StringVar(value=faction or owner_at(app, xy) or facs[0])
    if v_fac.get() not in facs:
        v_fac.set(facs[0])
    agent = kind not in ("army", "fleet")
    v_kind = tk.StringVar(value=(preset if preset in app.AGENTS else app.AGENTS[0]) if agent else kind)
    v_sub = tk.StringVar()
    w = tk.Toplevel(app)
    w.title({"army": "New army", "fleet": "New fleet"}.get(kind, "New agent") + " at %d, %d" % xy)
    w.transient(app)
    frm = ttk.Frame(w, padding=10)
    frm.pack()
    ttk.Label(frm, text="Faction").grid(row=0, column=0, sticky="w")
    FactionBox(frm, v_fac, facs, app.shown_names(), state="readonly", width=28).grid(row=0, column=1, columnspan=2,
                                                                                     sticky="w")
    ttk.Label(frm, foreground="#666", text="the owner of the %s here - pick another if you like" % (
        "nearest land" if sea else "land")).grid(row=1, column=1, columnspan=2, sticky="w")
    row = 2
    sub_row = ttk.Frame(frm)
    sub_row.grid(row=row, column=0, columnspan=3, sticky="w")
    row += 1
    if agent:
        ttk.Label(frm, text="Agent").grid(row=row, column=0, sticky="w")
        ttk.Combobox(frm, textvariable=v_kind, values=app.AGENTS, state="readonly", width=14).grid(
            row=row, column=1, sticky="w")
        row += 1
    ttk.Label(frm, text="Name" if agent else ("Admiral" if kind == "fleet" else "General")).grid(
        row=row, column=0, sticky="w")
    v_first, v_last, v_age = tk.StringVar(), tk.StringVar(), tk.StringVar(value="30")
    cb_first = ttk.Combobox(frm, textvariable=v_first, width=16)
    cb_first.grid(row=row, column=1)
    cb_last = ttk.Combobox(frm, textvariable=v_last, width=16)
    cb_last.grid(row=row, column=2)
    row += 1
    ttk.Label(frm, text="Age").grid(row=row, column=0, sticky="w")
    ttk.Entry(frm, textvariable=v_age, width=5).grid(row=row, column=1, sticky="w")
    row += 1
    note = ttk.Label(frm, foreground="#666", wraplength=420, justify="left")
    note.grid(row=row, column=0, columnspan=3, sticky="w", pady=(4, 0))
    state = {"pool": {}}

    def refresh(*_):
        fac = v_fac.get()
        first_sub = next((n for n in facs if n != "slave"), "")
        if fac == "slave" and not v_sub.get() and first_sub:   # setting it calls refresh again (the row was made twice)
            v_sub.set(first_sub)
            return
        for x in sub_row.winfo_children():
            x.destroy()
        if fac == "slave":                       # a rebel: whose look, and the list his name comes from
            ttk.Label(sub_row, text="Rebels of").pack(side="left")
            FactionBox(sub_row, v_sub, [n for n in facs if n != "slave"], app.shown_names(), state="readonly",
                       width=24).pack(side="left", padx=6)
        pool = app.pool_for(v_sub.get() if fac == "slave" else fac)
        state["pool"] = pool
        names = first_names(pool, v_kind.get())
        cb_first["values"] = names
        cb_last["values"] = [""] + pool.get("surnames", [])
        if v_first.get() not in names:
            v_first.set(names[0] if names else "")
        mine = fac == app.field_faction() and not app.map_only()
        note.configure(text=(
            "Goes to %s's list on Units & armies (give it its units there)." % fac if mine else
            "Written with the next Apply%s." % (
                "; it starts with the first unit of %s's nearest %s (change it in Edit faction)" % (
                    fac, "fleet" if kind == "fleet" else "army") if not agent else "")))
    for v in (v_fac, v_kind, v_sub):
        v.trace_add("write", refresh)
    refresh()

    def ok():
        fac, first = v_fac.get(), v_first.get().strip()
        pool = state["pool"]
        if not first:
            messagebox.showerror(APP, "pick a first name", parent=w)
            return
        if pool and first not in first_names(pool, v_kind.get()):
            messagebox.showerror(APP, "'%s' is not in the %s names of that list - the game crashes on a name it has "
                                      "no string for" % (first, "women's" if v_kind.get() in FEMALE_KINDS else "men's"),
                                 parent=w)
            return
        full = (first + " " + v_last.get().strip()).strip()
        if full in taken_names(app, fac):
            messagebox.showerror(APP, "%s already has someone called %s - the game skips a second one with the same "
                                      "name. Pick another name (or add a surname)." % (fac, full), parent=w)
            return
        rtw = {"army": "general", "fleet": "admiral"}.get(kind, v_kind.get())
        armies = {c.xy for fb in app.strat.factions for c in fb.characters if c.xy and c.kind in
                  ("named character", "general", "admiral")}
        armies |= {tuple(x["xy"]) for cs in app.map_chars.values() for x in cs if x["kind"] in ("army", "fleet")}
        armies |= {tuple(x["xy"]) for x in app.field if x.get("xy") and x["kind"] in ("army", "fleet")}
        why = app.mod.tile_problem(camp, xy, rtw, kind in ("army", "fleet"), armies)
        if why:
            messagebox.showerror(APP, "It cannot stand at %d, %d: %s" % (xy[0], xy[1], why), parent=w)
            return
        app.remember()
        c = {"kind": v_kind.get() if agent else kind, "name": full,
             "age": int(v_age.get()) if v_age.get().isdigit() else 30, "units": [], "xy": tuple(xy),
             **({"sub_faction": v_sub.get()} if fac == "slave" else {})}
        if fac == app.field_faction() and not app.map_only():
            app.field.append(c)
            app.refresh_field(keep=len(app.field) - 1)
            app.load_field()
        else:
            if not agent:
                from .edit import first_units
                c["units"] = first_units(app.mod, camp, fac, kind, xy)
                if not c["units"]:
                    messagebox.showerror(APP, "%s has no unit to start the %s with" % (fac, kind), parent=w)
                    return
            app.map_chars.setdefault(fac, []).append(c)
        w.destroy()
        app.map_view.set_tool(None)
        app.status.set("%s %s of %s at %d, %d - Preview, then %s." % (
            c["kind"], full, fac, xy[0], xy[1], "Apply changes" if app.editing() or app.map_only() else
            "Create faction"))
        app._mark_work()
        app.show_map()
    bar = ttk.Frame(frm)
    bar.grid(row=row + 1, column=0, columnspan=3, sticky="w", pady=(8, 0))
    ttk.Button(bar, text="Add", command=ok).pack(side="left")
    ttk.Button(bar, text="Cancel", command=lambda: (w.destroy(), app.map_view.set_tool(None))).pack(side="left", padx=4)


def give_town(app, region, faction):
    """The Map's 'Give this town to': the town of region goes to faction with the next Apply. The faction being
    edited keeps using its own towns list (Add to / Take out of my towns)."""
    app.remember()
    me = app.field_faction() if not app.map_only() else None
    if me and faction == me:
        if region not in app.chosen:
            app.chosen.append(region)
        app.map_owners.pop(region, None)
    else:
        if me and region in app.chosen:
            app.chosen.remove(region)
        app.map_owners[region] = faction
    app.refresh_chosen()
    app.status.set("%s goes to %s with the next Apply - Preview first." % (region, faction))
    app._mark_work()
    app.show_map()
