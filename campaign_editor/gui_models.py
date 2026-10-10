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
            # every figure at once like a culture's or a faction's (the user, 2026-10-10: a copy of a faction, its
            # culture changed, every figure follows; a faction - its colours too)
            bar = ttk.Frame(self)
            bar.pack(anchor="w", pady=(0, 4))
            ttk.Label(bar, text="Culture").pack(side="left")
            self.v_culture = tk.StringVar()
            self.cb_culture = ttk.Combobox(bar, textvariable=self.v_culture, width=14, state="readonly")
            self.cb_culture.pack(side="left", padx=(4, 12))
            self.cb_culture.bind("<<ComboboxSelected>>", lambda e: self.take_all("culture", self.v_culture.get()))
            ttk.Label(bar, text="Faction").pack(side="left")
            self.v_like = tk.StringVar()
            self.cb_like = ttk.Combobox(bar, textvariable=self.v_like, width=22, state="readonly")
            self.cb_like.pack(side="left", padx=(4, 12))
            self.cb_like.bind("<<ComboboxSelected>>", lambda e: self.take_all("faction", self.v_like.get()))
            ttk.Button(bar, text="As it was", command=self.as_it_was).pack(side="left")
            from .gui_util import hint
            hint(bar, "Every figure of this faction on the campaign map at once: Culture - the figures and textures "
                      "of the first faction of that culture in the list; Faction - the figures and textures (its "
                      "colours) of the faction picked. Waits for Preview / Apply; As it was takes them back.").pack(
                side="left")
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
        facs = a.mod.factions()
        self.cb_culture.configure(values=sorted({c for _, c in facs if c}))
        self.cb_like.configure(values=[n for n, _ in facs if n not in (src_faction, "slave")])
        self._figs, self._faction = figs, src_faction
        if not figs:
            g.say("%s has no character types in descr_character.txt." % src_faction)
            return
        self.head.configure(text=(
            "%s's figures on the campaign map, one card per character type - all of them changed at once with Culture "
            "or Faction above. Each figure is a strat model of descr_model_strat.txt; Preview, "
            "then Apply writes descr_character.txt (a faction sharing its line with others gets a line of its own) "
            "and its texture lines. 3D shows it with the faction's texture, its texture below it to Replace..."
            % src_faction))
        pics = {}                                         # model -> its texture pictures of this faction
        for p in FA.faction_pictures(a.mod, a.v_campaign.get(), src_faction):
            if FA.art_group(p) == "models" and p.get("link"):
                pics.setdefault(p["link"][1].split(":", 1)[-1], []).append(p)
        cells, shown = [], set()
        for fg in figs:
            want = a.figures.get(fg["type"]) or fg["models"]
            for lv, now in enumerate(fg["models"]):
                model = want[lv] if lv < len(want) else now
                cells.append(self._type_card(g.inner, fg, lv, model, now, pics.get(model, []), src_faction, new))
                shown.add(model)
        for model, ps in pics.items():                  # a texture no type shows now (another was picked)
            if model not in shown:                      # - seen in 3D too (the user: 'a texture I cannot see in 3D')
                cells += [a.art_editor.card(g.inner, p, src_faction, new, buttons=[
                    ("3D", lambda m=model: self.view_figure(m, src_faction))]) for p in ps]
        g.fill(cells)

    def _type_card(self, parent, fg, lv, model, now, pics, faction, new):
        a = self.app
        box = ttk.Frame(parent, padding=4, relief="groove")
        top = ttk.Frame(box)
        top.pack(fill="x")
        title = fg["type"] + (" (level %d)" % (lv + 1) if len(fg["models"]) > 1 else "")
        ttk.Label(top, text=title, font=("", 10, "bold")).pack(side="left")
        ttk.Label(top, text=model, foreground="#555").pack(side="left", padx=(8, 4))   # changed by the switches above
        ttk.Button(top, text="3D", command=lambda: self.view_figure(model, faction)).pack(side="left")
        if model != now:
            ttk.Label(box, text="was %s (not written yet)" % now, foreground="#b05a00").pack(anchor="w")
        for p in pics:
            a.art_editor.card(box, p, faction, new, wrap=a.art_editor.CELL - 60).pack(fill="x", pady=(4, 0))
        if not pics:
            src = (getattr(a, "figures_like", None) or {}).get(model)
            ttk.Label(box, foreground="#555", wraplength=a.art_editor.CELL, justify="left", text=(
                "no texture of %s's for this figure yet - it gets %s with Apply, then shows here to Replace" % (
                    faction, "%s's (its colours)" % src if src else "the model's first one")
                if model != now or src else "its texture is not named after %s (the model's own, shared by every "
                "faction that uses it)" % faction)).pack(anchor="w", pady=(4, 0))
        return box

    def take_all(self, how, name):
        """Every figure the faction shows taken from a culture's factions or from one faction (stratmodels), with
        their textures; kept for Apply in app.figures / app.figures_like."""
        from . import stratmodels as SM
        a = self.app
        if not name or not getattr(self, "_figs", None):
            return
        figs, like = SM.culture_figures(a.mod, name, but=self._faction) if how == "culture" else \
            SM.faction_figures(a.mod, name)
        a.remember()
        took = []
        for fg in self._figs:
            models = figs.get(fg["type"])
            if not models:
                continue
            want = list(models[:len(fg["models"])]) + list(fg["models"][len(models):])
            if want == list(fg["models"]):
                a.figures.pop(fg["type"], None)
            else:
                a.figures[fg["type"]] = want
            took.append(fg["type"])
        a.figures_like = {m: f for m, f in like.items() if f != self._faction}
        (self.v_like if how == "culture" else self.v_culture).set("")
        a.status.set("%s's figures as %s %s: %s - Preview, then Apply." % (
            self._faction, "the culture" if how == "culture" else "the faction", name,
            ", ".join(took) or "nothing of theirs fits its character types"))
        self.load()

    def as_it_was(self):
        a = self.app
        if not a.figures and not a.figures_like:
            return
        a.remember()
        a.figures, a.figures_like = {}, {}
        self.v_culture.set("")
        self.v_like.set("")
        a.status.set("The figures as they are in the files again.")
        self.load()

    def view_figure(self, model, faction):
        from . import stratmodels as SM
        from .gui_meshview import ModelViewer
        info = SM.mesh_info(self.app.mod, model)
        if info is None or not info.meshes:
            messagebox.showinfo("3D", "%s names no model file (.cas) in descr_model_strat.txt." % model)
            return
        ModelViewer(self, self.app.mod, info, (faction,), title="Campaign map figure in 3D")
