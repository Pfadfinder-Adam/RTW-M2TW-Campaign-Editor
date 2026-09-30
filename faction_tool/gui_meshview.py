"""The Unit editor's 3D view of a battle model (meshview.py draws it): turn it with the mouse, zoom with the wheel,
see it in each faction's texture, one man after another (the game mixes the model's heads, arms, legs ...)."""

import tkinter as tk
from tkinter import ttk

from . import meshview as MV
from . import models as MO

SIZE = (420, 520)


class ModelViewer(tk.Toplevel):
    def __init__(self, parent, mod, info, factions=()):
        super().__init__(parent)
        self.mod, self.info = mod, info
        self.title("Battle model in 3D - %s" % info.name)
        self.yaw, self.pitch, self.zoom, self.look = 35.0, 8.0, 1.0, 0
        self._drag, self._tex, self._photo, self.mesh = None, {}, None, None
        facs = [f for f in info.textures if f] or [""]
        first = next((f for f in factions if f in info.textures), facs[0])
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(frm, width=SIZE[0], height=SIZE[1], highlightthickness=0,
                                background="#2e3036")
        self.canvas.grid(row=0, column=0, rowspan=8, sticky="nw")
        side = ttk.Frame(frm, padding=(10, 0))
        side.grid(row=0, column=1, sticky="nw")
        ttk.Label(side, text=info.name, font=("", 10, "bold")).pack(anchor="w")
        ttk.Label(side, text="Texture of").pack(anchor="w", pady=(8, 0))
        self.v_fac = tk.StringVar(value=first)
        cb = ttk.Combobox(side, textvariable=self.v_fac, values=facs, state="readonly", width=22)
        cb.pack(anchor="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self.draw())
        ttk.Label(side, text="Detail (the game's distances)").pack(anchor="w", pady=(8, 0))
        self.lods = list(info.meshes)
        self.v_lod = tk.StringVar(value=self._lod_name(0))
        cl = ttk.Combobox(side, textvariable=self.v_lod, state="readonly", width=22,
                          values=[self._lod_name(i) for i in range(len(self.lods))])
        cl.pack(anchor="w")
        cl.bind("<<ComboboxSelected>>", lambda e: self.load())
        self.v_weapons = tk.BooleanVar(value=True)
        ttk.Checkbutton(side, text="Weapons and shield", variable=self.v_weapons,
                        command=self.draw).pack(anchor="w", pady=(8, 0))
        ttk.Button(side, text="Another man", command=self.next_look).pack(anchor="w", pady=(8, 0))
        ttk.Button(side, text="Front", command=lambda: self.turn_to(0)).pack(anchor="w", pady=(8, 0))
        ttk.Button(side, text="Back", command=lambda: self.turn_to(180)).pack(anchor="w")
        self.info_lbl = ttk.Label(side, foreground="#555", justify="left", wraplength=230)
        self.info_lbl.pack(anchor="w", pady=(10, 0))
        ttk.Label(side, foreground="#555", justify="left", wraplength=230, text=(
            "Drag to turn it, mouse wheel to zoom. The game gives each man one of the model's heads, arms, "
            "bodies ... - 'Another man' shows the next mix. Shown as it stands in the files (arms out); "
            "the weapons and shield take the attachment texture.")).pack(anchor="w", pady=(10, 0))
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.draw())
        self.canvas.bind("<MouseWheel>", lambda e: self._wheel(1 if e.delta > 0 else -1))
        self.canvas.bind("<Button-4>", lambda e: self._wheel(1))
        self.canvas.bind("<Button-5>", lambda e: self._wheel(-1))
        self.load()

    def _lod_name(self, i):
        return "%d - %s" % (i, "closest" if i == 0 else "farther") if i < len(self.info.meshes) else "-"

    def load(self):
        i = int((self.v_lod.get() or "0").split()[0]) if self.lods else 0
        rel = self.lods[i] if i < len(self.lods) else None
        self.mesh = None
        path = MV.mesh_path(self.mod, rel) if rel else None
        if not rel:
            msg = "the model names no mesh"
        elif not rel.lower().endswith(".mesh"):
            msg = "Rome's .cas models cannot be shown yet (only Medieval II's .mesh)"
        elif not path:
            msg = "the mesh file is not in this mod or the game: %s" % rel
        else:
            try:
                self.mesh = MV.read_file(path)
                msg = None
            except Exception as e:
                msg = "cannot read %s: %s" % (rel, e)
        if msg:
            self.canvas.delete("all")
            self.canvas.create_text(SIZE[0] // 2, SIZE[1] // 2, text=msg, fill="#ddd", width=SIZE[0] - 40)
            self.info_lbl.configure(text="")
            return
        self.draw()

    def _texture(self, table):
        rel = table.get(self.v_fac.get()) or table.get("") or next(iter(table.values()), None)
        if rel not in self._tex:
            self._tex[rel] = MO.texture_image(self.mod, rel) if rel else None
        return self._tex[rel]

    def draw(self, quick=False):
        if self.mesh is None:
            return
        from PIL import ImageTk
        groups = self.mesh.shown(self.look, self.v_weapons.get())
        tex, att = self._texture(self.info.textures), self._texture(self.info.attach)
        img = MV.render(self.mesh, SIZE, self.yaw, self.pitch, self.zoom, tex, att, groups,
                        quality=1 if quick else 2, textured=not quick)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        if not quick:
            n = sum(len(g.tris) // 3 for g in groups)
            self.info_lbl.configure(text="man %d of %d; %d triangles, %d points%s%s" % (
                self.look % self.mesh.looks() + 1, self.mesh.looks(), n, self.mesh.count,
                "" if tex is not None else "\nno texture file found for the man",
                "" if att is not None or not self.v_weapons.get() else
                "\nno attachment texture found - weapons in grey"))

    def next_look(self):
        self.look += 1
        self.draw()

    def turn_to(self, yaw):
        self.yaw, self.pitch = float(yaw), 8.0
        self.draw()

    def _press(self, e):
        self._drag = (e.x, e.y)

    def _move(self, e):
        if not self._drag:
            return
        self.yaw += (e.x - self._drag[0]) * 0.6
        self.pitch = max(-80.0, min(80.0, self.pitch + (e.y - self._drag[1]) * 0.4))
        self._drag = (e.x, e.y)
        self.draw(quick=True)

    def _wheel(self, step):
        self.zoom = max(0.4, min(6.0, self.zoom * (1.15 if step > 0 else 1 / 1.15)))
        self.draw()
