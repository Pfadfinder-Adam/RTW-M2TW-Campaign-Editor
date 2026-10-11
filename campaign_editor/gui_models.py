"""The Models tab (the user, 2026-10-09: 'a separate Models button - the figures out of Art, everything sorted'):
the faction's figures on the campaign map - which model shows each character type (a strat model of
descr_model_strat.txt), seen in 3D - and below each the figure's texture as a slim picture card (Replace..., Save a
copy..., Recolour...; the rest on its '?'). The Culture / Faction switches went out (the user, 2026-10-10 night:
'pointless'); app.figures / figures_like stay the way a figure change is written (stratmodels.apply). Art keeps the
other pictures.
Later phases (open.md 'CAMPAIGN MAP MODELS'): one model to many factions at once, battle models, own models."""

from tkinter import messagebox, ttk

from . import factionart as FA


class ModelsEditor(ttk.Frame):
    """One card per character type (and level: a priest, bishop, cardinal): which figure shows it, 3D - and that
    figure's texture with Replace... / Save a copy... / Recolour... - one place for each, nothing twice (a tester:
    'duplicates again')."""

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
        self._figs, self._faction = figs, src_faction
        if not figs:
            g.say("%s has no character types in descr_character.txt." % src_faction)
            return
        self.head.configure(text=(
            "%s's figures on the campaign map, one card per character type. Each figure is a strat model of "
            "descr_model_strat.txt, named per faction in descr_character.txt. 3D shows it with the faction's "
            "texture; its texture below it to Replace..., Save a copy... or Recolour... (the ? beside a texture's "
            "name: its file, the size it needs and where it is named)." % src_faction))
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
                cells += [a.art_editor.card(g.inner, p, src_faction, new, slim=True, buttons=[
                    ("3D", lambda m=model: self.view_figure(m, src_faction))] + (
                    [("Recolour...", lambda q=p["path"]: self.recolour(src_faction, q))]
                    if not new or new == src_faction else [])) for p in ps]
        g.fill(cells)

    def _type_card(self, parent, fg, lv, model, now, pics, faction, new):
        a = self.app
        box = ttk.Frame(parent, padding=4, relief="groove")
        top = ttk.Frame(box)
        top.pack(fill="x")
        title = fg["type"] + (" (level %d)" % (lv + 1) if len(fg["models"]) > 1 else "")
        ttk.Label(top, text=title, font=("", 10, "bold")).pack(side="left")
        ttk.Label(top, text=model, foreground="#555").pack(side="left", padx=(8, 4))
        ttk.Button(top, text="3D", command=lambda: self.view_figure(model, faction)).pack(side="left")
        if model != now:
            ttk.Label(box, text="was %s (not written yet)" % now, foreground="#b05a00").pack(anchor="w")
        # Recolour... for a faction that exists (a new one is made first - Create faction - then recoloured)
        own = not new or new == faction
        for p in pics:
            a.art_editor.card(box, p, faction, new, wrap=a.art_editor.CELL - 60, slim=True, buttons=[
                ("Recolour...", lambda q=p["path"]: self.recolour(faction, q))] if own else None).pack(
                fill="x", pady=(4, 0))
        if not pics:
            from .gui_util import hint
            src = (getattr(a, "figures_like", None) or {}).get(model)
            hint(top, "No texture of %s's for this figure yet - it gets %s with Apply, then shows here to Replace." % (
                faction, "%s's (its colours)" % src if src else "the model's first one")
                if model != now or src else "Its texture is not named after %s: the model's own, shared by every "
                "faction that uses it." % faction, width=420).pack(side="left", padx=(4, 0))
        return box

    def recolour(self, faction, path):
        """This one texture in the faction's colours (gui_recolour.open_one)."""
        from .gui_recolour import open_one
        try:
            return open_one(self.app, faction, path, parent=self)
        except Exception as e:
            messagebox.showerror("Recolour", "Could not read the pictures: %s" % e, parent=self)
            return None

    def view_figure(self, model, faction):
        from . import stratmodels as SM
        from .gui_meshview import ModelViewer
        info = SM.mesh_info(self.app.mod, model)
        if info is None or not info.meshes:
            messagebox.showinfo("3D", "%s names no model file (.cas) in descr_model_strat.txt." % model)
            return
        ModelViewer(self, self.app.mod, info, (faction,), title="Campaign map figure in 3D")
