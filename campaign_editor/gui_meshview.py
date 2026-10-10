"""Units' 3D view of a battle model (meshview.py draws it) - Medieval II's .mesh and Rome's .cas: turn it
with the mouse, zoom with the wheel, see it in each faction's texture, one man after another (Medieval II mixes the
model's heads, arms, legs ...), and in any of its skeleton's animations from the game's packs (animations.py):
Play / Pause, a frame at a time."""

import tkinter as tk
from tkinter import ttk

from . import animations as AN
from . import meshview as MV
from . import models as MO

SIZE = (420, 520)
POSE_WORDS = ("T pose (arms out)", "standing (the file's first frame)")
NO_ANIM = "(none)"


class ModelViewer(tk.Toplevel):
    def __init__(self, parent, mod, info, factions=(), mount=None, title="Battle model in 3D"):
        """mount: (its ModelInfo, mount type[, chariot]) - the unit's horse, camel ...: shown standing beside the
        rider; a Rome chariot (models.chariot_of, with 'horse_info'): the car, its horses and the crew put together
        as the game sets them."""
        super().__init__(parent)
        self.mod, self.info, self.mount = mod, info, mount
        self.mount_mesh = self.horse_mesh = None
        self.chariot = mount[2] if mount and len(mount) > 2 else None
        self.title("%s - %s" % (title, info.name))
        self.yaw, self.pitch, self.zoom, self.look = 35.0, 8.0, 1.0, 0
        self._drag, self._tex, self._photo, self.mesh = None, {}, None, None
        self.path, self.anim, self.frame, self._play, self._base = None, None, 0, None, {}
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
        self.v_pose = tk.StringVar(value=POSE_WORDS[0])
        if any(m.lower().endswith(".cas") for m in self.lods):        # Rome: the T pose, or as the file stands
            ttk.Label(side, text="Pose").pack(anchor="w", pady=(8, 0))
            cp = ttk.Combobox(side, textvariable=self.v_pose, values=POSE_WORDS, state="readonly", width=22)
            cp.pack(anchor="w")
            cp.bind("<<ComboboxSelected>>", lambda e: self.load())
        self._anim_box(side)
        self.v_weapons = tk.BooleanVar(value=True)
        ttk.Checkbutton(side, text="Weapons and shield", variable=self.v_weapons,
                        command=self.draw).pack(anchor="w", pady=(8, 0))
        self.v_mount = tk.BooleanVar(value=bool(mount))
        if mount:
            ttk.Checkbutton(side, text=("On its chariot (%s)" if self.chariot else "Its mount beside him (%s)")
                            % mount[1], variable=self.v_mount,
                            command=self.draw).pack(anchor="w")
        self.b_look = ttk.Button(side, text="Another man", command=self.next_look)
        self.b_look.pack(anchor="w", pady=(8, 0))
        ttk.Button(side, text="Front", command=lambda: self.turn_to(0)).pack(anchor="w", pady=(8, 0))
        ttk.Button(side, text="Back", command=lambda: self.turn_to(180)).pack(anchor="w")
        # short lines, the long words on their '?' (the user, 2026-10-10: the grey text stretched the window), and
        # only this game's words (a Medieval II model's window spoke of Rome)
        from .gui_util import ShortHint
        self.info_lbl = ShortHint(side)
        self.info_lbl.pack(anchor="w", pady=(10, 0))
        m2 = MO.game_kind(mod) == "medieval2"
        ShortHint(side, text="Drag to turn it, the wheel zooms. " + (
            "The model as it stands in the files (arms out). The game gives each man one of the model's heads, "
            "arms, bodies ... - 'Another man' shows the next mix; the weapons and shield take the attachment "
            "texture." if m2 else
            "Pose: the T pose (arms out), or as the file stands - a chariot with its horses and crew, a siege engine "
            "whole. One texture for the man and his weapons.") + (
            " Animation: any of its skeleton's moves from the game's animation packs - Play / Pause, then the "
            "frame line (drag it, or the < > buttons / the arrow keys) to go a frame back or on, like a video; "
            "the mount stays still." if self.anims else "")).pack(anchor="w", pady=(6, 0))
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.draw())
        self.canvas.bind("<MouseWheel>", lambda e: self._wheel(1 if e.delta > 0 else -1))
        self.canvas.bind("<Button-4>", lambda e: self._wheel(1))
        self.canvas.bind("<Button-5>", lambda e: self._wheel(-1))
        self.bind("<Destroy>", lambda e: self._stop() if e.widget is self else None)
        self.load()

    # -- animations ---------------------------------------------------------------------------------------------
    def _anim_box(self, side):
        """Skeleton + Animation pickers, Play / Pause and the frame - only when the packs hold the model's skeleton's
        animations."""
        self.anims = {}                             # skeleton -> [(what, file)]
        for sk in self.info.skeletons:
            try:
                got = AN.of_skeleton(self.mod, sk)
            except (OSError, ValueError):
                got = []
            if got and sk not in self.anims:
                self.anims[sk] = got
        self.v_skel = tk.StringVar(value=next(iter(self.anims), ""))
        self.v_anim = tk.StringVar(value=NO_ANIM)
        self.v_frame = tk.IntVar(value=0)
        if not self.anims:
            return
        ttk.Label(side, text="Animation").pack(anchor="w", pady=(8, 0))
        if len(self.anims) > 1:                     # Rome's spearmen: the spear's skeleton and the sword's
            cs = ttk.Combobox(side, textvariable=self.v_skel, values=list(self.anims), state="readonly", width=22)
            cs.pack(anchor="w")
            cs.bind("<<ComboboxSelected>>", lambda e: self._skel_changed())
        self.cb_anim = ttk.Combobox(side, textvariable=self.v_anim, state="readonly", width=22, height=24)
        self.cb_anim.pack(anchor="w")
        self.cb_anim.bind("<<ComboboxSelected>>", lambda e: self._anim_changed())
        self.lbl_file = ttk.Label(side, foreground="#555")
        self.lbl_file.pack(anchor="w")
        row = ttk.Frame(side)
        row.pack(anchor="w", pady=(4, 0), fill="x")
        self.b_play = ttk.Button(row, text="Play", command=self._toggle, state="disabled")
        self.b_play.pack(side="left")
        self.lbl_frame = ttk.Label(row, foreground="#555")
        self.lbl_frame.pack(side="left", padx=6)
        # the frame line: drag it back and on like a video's (it pauses the play), < > a frame at a time
        line = ttk.Frame(side)
        line.pack(anchor="w")
        self.b_back = ttk.Button(line, text="<", width=2, command=lambda: self._step(-1))
        self.b_back.pack(side="left")
        self.sc_frame = ttk.Scale(line, from_=0, to=1, orient="horizontal", length=190,
                                  command=lambda v: self._seek(int(round(float(v)))))
        self.sc_frame.pack(side="left", padx=2)
        self.b_on = ttk.Button(line, text=">", width=2, command=lambda: self._step(1))
        self.b_on.pack(side="left")
        for w in (self.sc_frame, self.b_back, self.b_on):
            w.state(["disabled"])
        self.bind("<Left>", lambda e: self._step(-1))
        self.bind("<Right>", lambda e: self._step(1))
        self.bind("<space>", lambda e: self._toggle())
        self._skel_changed()

    def _labels(self):
        return [NO_ANIM] + [what for what, _ in self.anims.get(self.v_skel.get(), [])]

    def _skel_changed(self):
        self.cb_anim.configure(values=self._labels())
        self.v_anim.set(NO_ANIM)
        self._anim_changed()

    def _anim_changed(self):
        self._stop()
        labels = self._labels()
        i = labels.index(self.v_anim.get()) if self.v_anim.get() in labels else 0
        self.anim, self.frame = None, 0
        self.lbl_file.configure(text="")
        if i:
            what, f = self.anims[self.v_skel.get()][i - 1]
            try:
                self.anim = AN.find(self.mod, f)
            except (OSError, ValueError):
                self.anim = None
            self.lbl_file.configure(text=f.replace("\\", "/").rsplit("/", 1)[-1])
        on = self.anim is not None and self.anim.frames > 1
        self.b_play.state(["!disabled"] if on else ["disabled"])
        for w in (self.sc_frame, self.b_back, self.b_on):
            w.state(["!disabled"] if on else ["disabled"])
        self.sc_frame.configure(to=max(1, (self.anim.frames - 1) if self.anim else 1))
        self.sc_frame.set(0)
        self._frame_words()
        self.draw()

    def _frame_words(self):
        self.lbl_frame.configure(text="frame %d of %d (%d a second)" % (self.frame + 1, self.anim.frames, AN.FPS)
                                 if self.anim else "")

    def _seek(self, k):
        if self.anim is None or k == self.frame:
            return
        if self._play is not None:                 # the line dragged while it plays: it stops on that frame
            self._stop()
        self.frame = max(0, min(self.anim.frames - 1, k))
        self._frame_words()
        self.draw()

    def _step(self, d):
        """A frame back or on (the < > buttons, the arrow keys) - paused there."""
        if self.anim is None or self.anim.frames < 2:
            return
        self._stop()
        self.frame = (self.frame + d) % self.anim.frames
        self.sc_frame.set(self.frame)
        self._frame_words()
        self.draw()

    def _toggle(self):
        if self._play is not None:
            self._stop()
            self.draw()
        elif self.anim is not None:
            self.b_play.configure(text="Pause")
            import time
            self._clock = (time.monotonic(), self.frame)
            self._tick()

    def _tick(self):
        """The next frame by the clock (a slow drawing skips frames, the move keeps its speed)."""
        if self.anim is None or not self.winfo_exists():
            self._play = None
            return
        import time
        t0, f0 = self._clock
        self.frame = (f0 + 1 + int((time.monotonic() - t0) * AN.FPS)) % self.anim.frames
        self.sc_frame.set(self.frame)
        self._frame_words()
        self.draw(quick="play")                     # textured, at half the smoothing
        self._play = self.after(int(1000 / AN.FPS), self._tick)

    def _stop(self):
        if self._play is not None:
            try:
                self.after_cancel(self._play)
            except tk.TclError:
                pass
            self._play = None
        if getattr(self, "b_play", None) is not None and self.b_play.winfo_exists():
            self.b_play.configure(text="Play")

    def _posed(self):
        """The man in the animation's frame (None: as loaded); a reason when the animation does not fit."""
        if self.anim is None or self.mesh is None:
            return None, None
        pose = MV.Pose.of(self.anim, self.frame)
        if self.path and self.path.lower().endswith(".cas"):
            try:
                return MV.read_posed(self.path, pose), None
            except Exception as e:
                return None, "the animation could not be put on the model: %s" % e
        sk = self.v_skel.get()
        if sk not in self._base:
            self._base[sk] = AN.base_pose(self.mod, sk)
        base = self._base[sk]
        if base is None:
            return None, "no base pose (the skeleton's 'default' animation) - the model stays as it is"
        got = MV.pose_mesh(self.mesh, pose, base)
        return (got, None) if got is not None else (None, "the animation does not fit the model's bones")

    def _lod_name(self, i):
        return "%d - %s" % (i, "closest" if i == 0 else "farther") if i < len(self.info.meshes) else "-"

    def load(self):
        i = int((self.v_lod.get() or "0").split()[0]) if self.lods else 0
        rel = self.lods[i] if i < len(self.lods) else None
        self.mesh = None
        path = MV.mesh_path(self.mod, rel) if rel else None
        self.path = path
        if not rel:
            msg = "the model names no mesh"
        elif not rel.lower().endswith((".mesh", ".cas")):
            msg = "this kind of model file cannot be shown: %s" % rel
        elif not path:
            msg = "the mesh file is not in this mod or the game: %s" % rel
        else:
            try:
                self.mesh = MV.read_file(path, self._pose())
                msg = None
            except Exception as e:
                msg = "cannot read %s: %s" % (rel, e)
        if self.mesh is not None:
            self.b_look.state(["!disabled"] if self.mesh.looks() > 1 else ["disabled"])
        self.mount_mesh = None
        if self.mount:                                  # the mount's mesh at the same detail (or its closest)
            ms = self.mount[0].meshes
            mp = MV.mesh_path(self.mod, ms[min(i, len(ms) - 1)]) if ms else None
            try:
                self.mount_mesh = MV.read_file(mp, self._pose()) if mp else None
            except Exception:
                self.mount_mesh = None
            self.horse_mesh = None
            hi = (self.chariot or {}).get("horse_info")
            if hi is not None and hi.meshes:
                hp = MV.mesh_path(self.mod, hi.meshes[min(i, len(hi.meshes) - 1)])
                try:
                    self.horse_mesh = MV.read_file(hp, self._pose()) if hp else None
                except Exception:
                    self.horse_mesh = None
        if msg:
            self.canvas.delete("all")
            self.canvas.create_text(SIZE[0] // 2, SIZE[1] // 2, text=msg, fill="#ddd", width=SIZE[0] - 40)
            self.info_lbl.configure(text="")
            return
        self.draw()

    def _pose(self):
        return MV.POSES[POSE_WORDS.index(self.v_pose.get())] if self.v_pose.get() in POSE_WORDS else "t"

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
        if tex is None and self.mesh.texture_ref:       # Rome: no texture line - the one the .cas names
            tex = self._texture({"": self.mesh.texture_ref})
        man, why = self._posed()
        man = man or self.mesh
        mesh, more = man, None
        riding = self.mount and self.v_mount.get() and self.mount_mesh is not None
        if riding and self.chariot:                     # Rome: the car, its horses and the crew in their places
            ch = self.chariot
            mesh = MV.chariot(man, groups, self.mount_mesh, self.horse_mesh, ch["horses"], ch["riders"])
            groups = mesh.groups
            hi = ch.get("horse_info")
            more = {2: self._texture({"": self.mount_mesh.texture_ref}) if self.mount_mesh.texture_ref else None,
                    4: (self._texture(hi.textures) if hi is not None and hi.textures else
                        self._texture({"": self.horse_mesh.texture_ref})
                        if self.horse_mesh is not None and self.horse_mesh.texture_ref else None)}
        elif riding:
            mi = self.mount[0]
            mesh = MV.combine(man, groups, self.mount_mesh, self.mount_mesh.shown(0, True),
                              mount_one=True if not mi.attach else None)
            groups = mesh.groups
            more = {2: self._texture(mi.textures) if mi.textures else None,
                    3: self._texture(mi.attach) if mi.attach else None}
            if more[2] is None and self.mount_mesh.texture_ref:
                more[2] = self._texture({"": self.mount_mesh.texture_ref})
        whole = not riding and not self.info.attach and MV.whole_picture(man)
        if whole:
            groups = MV.one_picture(groups)          # a mount alone: its whole texture (half was drawn white)
        img = MV.render(mesh, SIZE, self.yaw, self.pitch, self.zoom, tex, att, groups,
                        quality=1 if quick else 2, textured=not quick or quick == "play", more=more)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        if not quick:
            n = sum(len(g.tris) // 3 for g in groups)
            if self.mount and self.v_mount.get() and self.mount_mesh is None:
                self.info_lbl.configure(text="the mount's mesh file is not in this mod or the game")
                return
            parts = self.mesh.variants(self.look, self.v_weapons.get())
            said = [w for w in (why, None if tex is not None else "no texture file found for the man",
                                None if att is not None or not self.v_weapons.get() or self.mesh.one_texture or
                                whole else "no attachment texture found: weapons in grey") if w]
            # what needs seeing first (a problem, else the size), the variants on the '?'
            size = "%d triangles, %d points." % (n, self.mesh.count)
            self.info_lbl.configure(text=(", ".join(said) + ". " + size if said else size) + (
                (" Variants shown: " + ", ".join("%s %d of %d" % p for p in parts) + ".") if parts else ""))

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
