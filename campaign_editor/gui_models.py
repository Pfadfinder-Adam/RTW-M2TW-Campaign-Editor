"""The Models tab (the user, 2026-10-09: 'a separate Models button - the figures out of Art, everything sorted'):
the faction's figures on the campaign map - who is shown by which model (a strat model of descr_model_strat.txt per
character type, picked here, waiting for Apply like every change: app.figures), seen in 3D - and below them the
figures' textures as picture cards (Replace..., Save a copy..., 3D). Art keeps the other pictures.
Later phases (open.md 'CAMPAIGN MAP MODELS'): one model to many factions at once, battle models, own models."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import factionart as FA


class ModelsEditor(ttk.Frame):
    """One card per character type (and level: a priest, bishop, cardinal): which figure shows it - picked in the
    list, 3D - and that figure's texture with Replace... / Save a copy... - one place for each, nothing twice (the
    pickers and the textures were two lists, a tester: 'duplicates again')."""

    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        self.grid_ = None

    def load(self):
        from .gui_art import CardGrid
        a = self.app
        if self.grid_ is None:
            # one short line, the rest on its '?' (a tester: the top part takes room for nothing)
            from .gui_util import ShortHint
            self.head = ShortHint(self)
            self.head.pack(anchor="w", pady=(0, 2))
            self.grid_ = CardGrid(self, a.art_editor.CELL + 60)
            self.grid_.pack(fill="both", expand=True)
        g = self.grid_
        g.clear()
        self.head.configure(text="")
        if not a.mod:
            return
        src_faction, new = a.art_editor._names()
        if not src_faction:
            g.say("Pick the %s on the Faction tab first." % ("faction" if a.editing() else "template"))
            return
        from . import stratmodels as SM
        figs = SM.figures(a.mod, src_faction)
        if not figs:
            g.say("%s has no character types in descr_character.txt." % src_faction)
            return
        self.head.configure(text=(
            "%s's figures on the campaign map, one card per character type. Each type's figure is a strat model of "
            "descr_model_strat.txt - pick another in its list; Preview, then Apply writes descr_character.txt; a "
            "faction sharing its line with others gets a line of its own. 3D shows it with the faction's texture, "
            "and its texture below it to Replace... A model the faction has no texture in gets a line with the "
            "model's first texture; its picture shows here after Apply." % src_faction))
        pics = {}                                         # model -> its texture pictures of this faction
        for p in FA.faction_pictures(a.mod, a.v_campaign.get(), src_faction):
            if FA.art_group(p) == "models" and p.get("link"):
                pics.setdefault(p["link"][1].split(":", 1)[-1], []).append(p)
        names = sorted(SM.model_types(a.mod), key=str.lower)
        cells, shown = [], set()
        for fg in figs:
            want = a.figures.get(fg["type"]) or fg["models"]
            for lv, now in enumerate(fg["models"]):
                model = want[lv] if lv < len(want) else now
                cells.append(self._type_card(g.inner, fg, lv, model, now, names, pics.get(model, []),
                                             src_faction, new))
                shown.add(model)
        for model, ps in pics.items():                  # a texture no type shows now (another was picked)
            if model not in shown:
                cells += [a.art_editor.card(g.inner, p, src_faction, new) for p in ps]
        g.fill(cells)

    def _type_card(self, parent, fg, lv, model, now, names, pics, faction, new):
        a = self.app
        box = ttk.Frame(parent, padding=4, relief="groove")
        top = ttk.Frame(box)
        top.pack(fill="x")
        title = fg["type"] + (" (level %d)" % (lv + 1) if len(fg["models"]) > 1 else "")
        ttk.Label(top, text=title, font=("", 10, "bold")).pack(side="left")
        v = tk.StringVar(value=model)
        cb = ttk.Combobox(top, textvariable=v, values=names, width=22, state="readonly")
        cb.pack(side="left", padx=(8, 4))
        cb.bind("<<ComboboxSelected>>", lambda e: self.pick_figure(fg["type"], lv, v.get(), fg["models"]))
        ttk.Button(top, text="3D", command=lambda: self.view_figure(v.get(), faction)).pack(side="left")
        if model != now:
            ttk.Label(box, text="was %s (not written yet)" % now, foreground="#b05a00").pack(anchor="w")
        for p in pics:
            a.art_editor.card(box, p, faction, new, wrap=a.art_editor.CELL - 60).pack(fill="x", pady=(4, 0))
        if not pics:
            ttk.Label(box, foreground="#555", wraplength=a.art_editor.CELL, justify="left", text=(
                "no texture of %s's for this figure yet - it gets the model's first one with Apply, then shows "
                "here to Replace" % faction if model != now else "its texture is not named after %s (the model's "
                "own, shared by every faction that uses it)" % faction)).pack(anchor="w", pady=(4, 0))
        return box

    def pick_figure(self, ctype, level, model, now):
        a = self.app
        a.remember()
        want = list(a.figures.get(ctype) or now)
        want[level] = model
        if want == list(now):
            a.figures.pop(ctype, None)
        else:
            a.figures[ctype] = want
        a.status.set("%s on the campaign map: %s - Preview, then Apply." % (ctype, ", ".join(want)))
        self.load()

    def view_figure(self, model, faction):
        from . import stratmodels as SM
        from .gui_meshview import ModelViewer
        info = SM.mesh_info(self.app.mod, model)
        if info is None or not info.meshes:
            messagebox.showinfo("3D", "%s names no model file (.cas) in descr_model_strat.txt." % model)
            return
        ModelViewer(self, self.app.mod, info, (faction,), title="Campaign map figure in 3D")
