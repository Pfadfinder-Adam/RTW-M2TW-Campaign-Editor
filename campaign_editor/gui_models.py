"""The Models tab (the user, 2026-10-09: 'a separate Models button - the figures out of Art, everything sorted'):
the faction's figures on the campaign map - who is shown by which model (a strat model of descr_model_strat.txt per
character type, picked here, waiting for Apply like every change: app.figures), seen in 3D - and below them the
figures' textures as picture cards (Replace..., Save a copy..., 3D). Art keeps the other pictures.
Later phases (open.md 'CAMPAIGN MAP MODELS'): one model to many factions at once, battle models, own models."""

import tkinter as tk
from tkinter import messagebox, ttk

from . import factionart as FA
from .gui_util import ShortHint


class ModelsEditor(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=4)
        self.app = app
        from .gui_util import ScrollFrame
        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True)
        body = sf.inner
        self.fig_box = ttk.LabelFrame(body, text="Figures on the campaign map - who is shown by which model", padding=6)
        self.fig_box.pack(fill="x")
        self.tex_box = ttk.LabelFrame(body, text="Their textures (the figure's colours) - 3D shows the figure with it",
                                      padding=6)
        self.tex_box.pack(fill="both", expand=True, pady=(8, 0))
        self.cells, self._cols = [], 0
        self.tex_box.bind("<Configure>", lambda e: self._reflow(), add="+")

    def _reflow(self, force=False):
        art = self.app.art_editor
        cols = max(1, (self.tex_box.winfo_width() - 20) // art.CELL)
        if cols == self._cols and not force:
            return
        self._cols = cols
        for c in range(8):
            self.tex_box.columnconfigure(c, weight=0, minsize=0)
        for c in range(cols):
            self.tex_box.columnconfigure(c, weight=1, minsize=art.CELL - 8)
        for i, w in enumerate(self.cells):
            w.grid(row=i // cols, column=i % cols, sticky="nwe", padx=3, pady=3)

    def load(self):
        a = self.app
        for box in (self.fig_box, self.tex_box):
            for w in box.winfo_children():
                w.destroy()
        self.cells, self._cols = [], 0
        if not a.mod:
            return
        art = a.art_editor
        src_faction, new = art._names()
        if not src_faction:
            ttk.Label(self.fig_box, text="Pick the %s on the Faction tab first." % (
                "faction" if a.editing() else "template"), foreground="#555").grid(row=0, column=0, sticky="w")
            return
        self.fill_figures(src_faction, new)
        pics = [p for p in FA.faction_pictures(a.mod, a.v_campaign.get(), src_faction) if FA.art_group(p) == "models"]
        if not pics:
            ttk.Label(self.tex_box, text="No figure textures named after %s were found." % src_faction,
                      foreground="#555").grid(row=0, column=0, sticky="w")
            return
        for p in pics:
            model = (p.get("link") or ["", ""])[1].split(":", 1)[-1] if p.get("link") else None
            extra = [("3D", lambda m=model: self.view_figure(m, src_faction))] if model else None
            self.cells.append(art.card(self.tex_box, p, src_faction, new, buttons=extra))
        self._reflow(force=True)

    def fill_figures(self, faction, new):
        """A row per character type of the faction: its figure (a strat model of descr_model_strat.txt, one per
        level) to pick, and View in 3D. The pick waits for Apply like every change (app.figures)."""
        from . import stratmodels as SM
        a = self.app
        box = self.fig_box
        for w in box.winfo_children():
            w.destroy()
        figs = SM.figures(a.mod, faction) if faction else []
        if not figs:
            ttk.Label(box, text="%s has no character types in descr_character.txt." % faction if faction else
                      "Pick the faction first.", foreground="#555").grid(row=0, column=0, sticky="w")
            return
        names = sorted(SM.model_types(a.mod), key=str.lower)
        wide = max(self.winfo_width(), self.winfo_toplevel().winfo_width() - 40)
        cols = max(1, min(3, wide // 470))              # as many as the width takes (the third was cut)
        r = c = 0
        for fg in figs:
            wide = len(fg["models"]) > 1                # levels (a priest, bishop, cardinal): a row of its own
            if wide and c:
                r, c = r + 1, 0
            cell = ttk.Frame(box, padding=(0, 2, 12, 2))
            cell.grid(row=r, column=c, columnspan=cols if wide else 1, sticky="w")
            want = a.figures.get(fg["type"]) or fg["models"]
            ttk.Label(cell, text=fg["type"], width=16, font=("", 9, "bold")).grid(row=0, column=0, sticky="w")
            for lv, now in enumerate(fg["models"]):
                v = tk.StringVar(value=want[lv] if lv < len(want) else now)
                cb = ttk.Combobox(cell, textvariable=v, values=names, width=20, state="readonly")
                cb.grid(row=0, column=1 + 2 * lv, padx=(0, 2))
                cb.bind("<<ComboboxSelected>>", lambda e, t=fg["type"], lv=lv, v=v, fg=fg: self.pick_figure(
                    t, lv, v.get(), fg["models"]))
                ttk.Button(cell, text="3D", command=lambda v=v: self.view_figure(v.get(), faction)).grid(
                    row=0, column=2 + 2 * lv, padx=(0, 6))
            if fg["type"] in a.figures:
                ttk.Label(cell, text="was %s (not written yet)" % ", ".join(fg["models"]),
                          foreground="#b05a00").grid(row=1, column=1, columnspan=2 * len(fg["models"]), sticky="w")
            if wide:
                r, c = r + 1, 0
            else:
                r, c = (r + 1, 0) if c + 1 >= cols else (r, c + 1)
        r += 1 if c else 0
        ShortHint(box, foreground="#555", justify="left", wraplength=900, text=(
            "Pick another model for a character type (the list holds every figure of descr_model_strat.txt); "
            "Preview, then Apply writes descr_character.txt (a faction sharing its line with others gets a line "
            "of its own). A model the faction has no texture in gets a line with the model's first texture; "
            "its picture then shows below after Apply, to Replace. 3D shows the figure with the faction's texture.")
        ).grid(row=r, column=0, columnspan=cols, sticky="w", pady=(4, 0))

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
