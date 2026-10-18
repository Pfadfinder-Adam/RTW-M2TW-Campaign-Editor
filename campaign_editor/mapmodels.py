"""What stands on the campaign map - towns with their walls, ports, forts, watchtowers, resources, armies, agents
and fleets (mapobjects3d.objects says which model stands where) - laid on the 3D map as the game's own models,
for the graphics card (glmap).

- Buildings and resources are plain .cas models (stratcas reads them): each part with its own texture, found the way
  the game finds it (the model's folder's textures/, the folder itself, models_strat/textures/).
- Characters are figures with a skeleton: posed in their skeleton's standing move (the first frame of its
  stand / idle animation, as the older view did), scaled by descr_model_strat.txt's 'scale' - tile units, as the
  engine (AERIAL_MAP_TILE_SIZE 1, model_db opens the model at that scale); in their faction's texture.
- Each stands in its tile's middle on the ground (a fleet on the water); a character looks south, at the camera, as
  the game shows them (_face_camera), on his lowest point; a port is two models turned
  alike, its land part on its tile, its sea part on the dock - the sea tile beside it the engine picks (_port_dock).

Our world: x east, y up, z SOUTH from the map's top; the models' z (the game's north) is turned round."""

import numpy as np

from . import tilemodels as TM

KIND = {"town": 1, "wall": 1, "port": 1, "port_sea": 1, "fort": 1, "watchtower": 1, "resource": 2, "character": 3}


class Loader:
    """The mod's models and textures, read once each."""

    def __init__(self, mod):
        self.mod, self._models, self._pics, self.missing = mod, {}, {}, set()
        self._figures, self._moves = {}, {}           # posed figures by (model, skeleton); stand moves by skeleton

    def picture(self, rel):
        """A texture as an (h, w, 4) uint8 array, or None."""
        if rel is None:
            return None
        key = rel.lower()
        if key not in self._pics:
            from . import models as MO
            try:
                im = MO.texture_image(self.mod, rel)
            except Exception:
                im = None
            self._pics[key] = np.asarray(im, np.uint8) if im is not None else None
        return self._pics[key]

    def _texture(self, model, name):
        """The data-relative texture a static model's part names, as the game finds it - or None."""
        if not name:
            return None
        folder = model.replace("\\", "/").rsplit("/", 1)[0] if "/" in model else ""
        # a name with no ending (HLR's 'Paccos_barbarian_texture') is its .tga (texture_image finds .tga.dds too)
        for nm in [name] + ([name + ".tga"] if "." not in name.rsplit("/", 1)[-1] else []):
            for rel in (folder + "/textures/" + nm, folder + "/" + nm, "models_strat/textures/" + nm, nm):
                if self.picture(rel) is not None:
                    return rel
        self.missing.add(name)
        return None

    def parts(self, model, skeleton=None, texture=None):
        """[(texture rel or None, vertices (n, 8) x y z normal u v - triangles as vertex triples, our frame)]."""
        key = (model.lower(), skeleton, texture)
        if key in self._models:
            return self._models[key]
        out = []
        try:
            out = self._figure(model, skeleton, texture) if skeleton else self._static(model)
        except Exception:
            out = []
        if not out and skeleton is None:
            try:
                out = self._figure(model, None, texture)
            except Exception:
                out = []
        if not out:
            self.missing.add(model)
        self._models[key] = out
        return out

    def _static(self, model):
        from . import stratcas
        path = self.mod.find_any(model)
        if not path:
            return []
        with open(path, "rb") as fh:
            parts = stratcas.read(fh.read())
        out = []
        for p in parts:
            if not p.uvs or not p.texture:
                continue                                  # an untextured helper part (none drawn in the game)
            P = np.asarray(p.positions, np.float32).reshape(-1, 3)
            N = np.asarray(p.normals, np.float32).reshape(-1, 3)
            U = np.asarray(p.uvs, np.float32).reshape(-1, 2)
            F = np.asarray(p.faces, np.int64).reshape(-1, 3)
            v = np.concatenate([P, N, U], 1)[F.ravel()]
            v[:, 2] *= -1                                 # the game's z runs north, ours south
            v[:, 5] *= -1
            out.append((self._texture(model, p.texture), v))
        return out

    def _stand(self, skeleton):
        """The first frame of the skeleton's standing move (read once per skeleton), or None."""
        if skeleton not in self._moves:
            from . import animations as AN
            from . import meshview as MV
            moves = {w.lower(): f for w, f in AN.of_skeleton(self.mod, skeleton)}
            f = moves.get("stand_a_idle") or moves.get("stand") or moves.get("idle") or next(
                (v for k, v in moves.items() if "stand" in k or "idle" in k), None)
            anim = AN.find(self.mod, f) if f else None
            self._moves[skeleton] = MV.Pose.of(anim, 0) if anim is not None else None
        return self._moves[skeleton]

    def _figure(self, model, skeleton, texture):
        key = (model.lower(), skeleton)
        if key not in self._figures:
            self._figures[key] = self._posed(model, skeleton)
        v = self._figures[key]
        if v is None:
            return []
        tex = texture if self.picture(texture) is not None else None
        if texture and tex is None:
            self.missing.add(texture)
        return [(tex, v)]

    def _game(self):
        try:
            from .models import game_kind
            return game_kind(self.mod)
        except Exception:
            return None

    def _posed(self, model, skeleton):
        """The figure's triangles (n, 8) in its standing pose, our frame - or None."""
        from . import fastmesh as F
        from . import meshview as MV
        path = MV.mesh_path(self.mod, model)
        if not path:
            return None
        mesh = None
        pose = self._stand(skeleton) if skeleton else None
        if pose is not None:
            mesh = MV.read_posed(path, pose)
        if mesh is None:
            mesh = MV.read_file(path, "frame")
        tri = F._make_triangles(mesh, mesh.groups)
        if tri is None or not mesh.uvs:
            return None
        T, base, one = tri
        P = np.asarray(mesh.positions, np.float32)
        U = np.asarray(mesh.uvs, np.float32).reshape(-1, 2)[T]          # (m, 3, 2)
        half = np.where(one, 0, (U[:, :, 0].mean(1) >= 0.5).astype(np.int64))
        U[:, :, 0] = np.where(one[:, None], U[:, :, 0], U[:, :, 0] * 2 - half[:, None])
        V = P[T].copy()                                                  # (m, 3, 3)
        V[..., 2] *= -1                                  # the game's z runs north, ours south (as every model here)
        _face_camera(V, self._game())
        V[..., 1] -= min(0.0, float(V[..., 1].min()))    # his feet on the ground: a pose's lowest point, not its root
        n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        v = np.concatenate([V, np.repeat(n[:, None], 3, 1), U], 2).reshape(-1, 8).astype(np.float32)
        pic = (base + half)
        keep = np.repeat(pic == 0, 3) if (pic == 0).any() else np.ones(len(v), bool)    # the man (attachments: later)
        return v[keep]


def _face_camera(V, game):
    """A figure turned to look south, at the camera, as the game shows them - both games alike (report #330: Rome's
    stood with their backs to it; #331: Medieval II's too, they were left unturned)."""
    V[..., 0] *= -1
    V[..., 2] *= -1


def _port_dock(x, y, sea):
    """(degrees clockwise from the north, dock tile) of the port at (x, y), as the engine works them out
    (PORT_BUILDING::setup_orientation): of the sea tiles north, east, south, west of it, the one with the most sea
    around it - its count not started again when it loses, as the engine's - the port's sea side (the models' south,
    -z: Rome's port_sea and Medieval II's port_land are a U of walls open there, report #329) turned toward it.
    port_land stands on the port's own tile (land), port_sea on the dock, both turned alike - so the houses stand
    inside the walls and the columns in the water."""
    H, W = sea.shape
    steps = ((0, 1), (1, 0), (0, -1), (-1, 0))

    def wet(px, py):
        return 0 <= px < W and 0 <= py < H and bool(sea[py, px])
    deg, best, count, most = 180, None, 0, 0
    for i, (dx, dy) in enumerate(steps):
        nx, ny = x + dx, y + dy
        if not wet(nx, ny):
            continue
        if most == 0:
            best = (nx, ny)
        count += sum(wet(nx + ex, ny + ey) for ex, ey in steps)
        if count > most:
            best, most, count, deg = (nx, ny), count, 0, (180 + 90 * i) % 360
    return deg, best or (x, y)


def build(objs, loader, heights, yscale):
    """{texture rel or None: (n, 9) float32 x y z normal u v kind} of every object laid on the map (triangles as
    vertex triples); kind KIND (1 towns and ports, 2 resources, 3 characters)."""
    rows, cols = heights.shape
    H, W = (rows - 1) // 2, (cols - 1) // 2
    sea = heights[::-1][1::2, 1::2][:H, :W] <= 0
    out = {}
    for o in objs:
        x, y = o["xy"]
        if not (0 <= x < W and 0 <= y < H):
            continue
        parts = loader.parts(o["model"], o.get("skeleton") if o["kind"] == "character" else None, o.get("texture"))
        if not parts:
            continue
        deg = 0
        if o["kind"] in ("port", "port_sea"):
            deg, dock = _port_dock(x, y, sea)
            if o["kind"] == "port_sea":                  # the dock: the sea tile beside the port
                x, y = dock
        top = H - 1 - y
        gy = max(float(TM._ground_h(heights, np.array([2.0 * top + 1]), np.array([2.0 * x + 1]))[0]) * yscale, 0.0)
        s = float(o.get("scale") or 1.0)
        for tex, v in parts:
            w = v.copy()
            w[:, :3] *= s
            if deg:                                      # turned clockwise seen from above (our z runs south)
                gx, gz = TM.turn(w[:, 0], -w[:, 2], deg)
                nx, nz = TM.turn(w[:, 3], -w[:, 5], deg)
                w[:, 0], w[:, 2], w[:, 3], w[:, 5] = gx, -gz, nx, -nz
            w[:, 0] += x + 0.5
            w[:, 1] += gy
            w[:, 2] += top + 0.5
            out.setdefault(tex, []).append(np.c_[w, np.full(len(w), KIND.get(o["kind"], 1), np.float32)])
    return {k: np.concatenate(v).astype(np.float32) for k, v in out.items()}


__all__ = ["Loader", "build", "KIND"]
