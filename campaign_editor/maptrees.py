"""The campaign map's trees as the engines place them (facts from the engine source's aerial_map_trees add_trees
and aerial_map fillChunkTrees, editor-notes strat_map_render.md section 5; no code copied).

- Only forest tiles get trees: a tile whose centre point on map_ground_types.tga is sparse forest (level 1) or dense
  forest (level 3), never a sea tile.
- descr_climates.txt names, per climate and season, the models: 'strategy summer|winter sparse_tree|dense_tree|canopy
  <file.cas> <sprite cell>'; files in data/terrain/aerial_map/tree_models/ (only their first part is used), their
  textures in tree_models/textures/. Winter uses the winter list of a kind when the climate has one, else summer's.
- Sparse forest: 3 trees at random spots of the tile.
- Dense forest: up to 8 trees on a fixed 4 x 4 lattice (which spots by the dense neighbours to the left, right and
  below), each moved up to 0.1 each way; then the canopy - the centre, the joins toward a dense neighbour above /
  to the right (and the corner between them), 4 inner spots pulled in on the sides with no dense neighbour - each
  moved up to 0.05 each way and up to 0.05 up or down.
- Every tree stands at the ground's height there, not turned, not scaled; it leans with the wind: x += y x sheer,
  the sheer one of 20 slots, slot i = 0.1 cos((time x 0.25 + i / 19) pi).

The game's own dice (its RAND seeded by each tile's seed in map.rwm) cannot be read back, so the same tiles get the
same kinds and numbers of trees, but their spots and models come from a stable dice of our own (tilemodels._hash)."""

import numpy as np

from . import tilemodels as TM

KINDS = ("sparse_tree", "dense_tree", "canopy")
SHEERS = 20
FOREST_SPARSE, FOREST_DENSE = (0, 128, 0), (0, 64, 0)       # map_ground_types.tga (terrain3d.GROUND_KEYS)

# the dense forest's lattice spots, by (left dense, right dense, below dense) - letters into SPOTS
LATTICE = ("EFKLIH", "EFGAHIJD", "EFKCD", "EFGA", "ABLIH", "HIJD", "ABCD", "")
_E, _Q = 0.125, (0.0, 0.25, 0.5, 0.75)
SPOTS = {"A": (_Q[0] + _E, _Q[0] + _E), "B": (_Q[1] + _E, _Q[0] + _E), "C": (_Q[2] + _E, _Q[0] + _E),
         "D": (_Q[3] + _E, _Q[0] + _E), "E": (_Q[0] + _E, _Q[3] + _E), "F": (_Q[0] + _E, _Q[2] + _E),
         "G": (_Q[0] + _E, _Q[1] + _E), "H": (_Q[3] + _E, _Q[3] + _E), "I": (_Q[3] + _E, _Q[2] + _E),
         "J": (_Q[3] + _E, _Q[1] + _E), "K": (_Q[1], _Q[1]), "L": (_Q[3], _Q[1])}


def read_climates(text):
    """[(climate name, {'summer'|'winter': {kind: [(file, sprite cell)]}})] of descr_climates.txt, in its order."""
    from .textio import strip_comment
    out = []
    for line in text.splitlines():
        t = strip_comment(line).split()
        if len(t) == 2 and t[0] == "climate":
            out.append((t[1], {"summer": {k: [] for k in KINDS}, "winter": {k: [] for k in KINDS}}))
        elif out and len(t) >= 4 and t[0] == "strategy" and t[1] in ("summer", "winter") and t[2] in KINDS:
            cell = int(t[4]) if len(t) >= 5 and t[4].lstrip("-").isdigit() else 0
            out[-1][1][t[1]][t[2]].append((t[3], cell))
    return out


def forest_levels(heights, ground_rgb):
    """(H, W) uint8 forest level of each tile (0 none, 1 sparse, 3 dense), rows bottom first (z up)."""
    rows, cols = heights.shape
    H, W = (rows - 1) // 2, (cols - 1) // 2
    out = np.zeros((H, W), np.uint8)
    if ground_rgb is None or ground_rgb.shape[:2] != heights.shape:
        return out
    c = ground_rgb[1::2, 1::2][:H, :W][::-1].astype(np.int32)
    code = (c[..., 0] << 16) | (c[..., 1] << 8) | c[..., 2]
    out[code == (FOREST_SPARSE[0] << 16 | FOREST_SPARSE[1] << 8 | FOREST_SPARSE[2])] = 1
    out[code == (FOREST_DENSE[0] << 16 | FOREST_DENSE[1] << 8 | FOREST_DENSE[2])] = 3
    out[heights[::-1][1::2, 1::2][:H, :W] <= 0] = 0           # the sea has none
    return out


class _Dice:
    """The tile's draws one after another (in place of the game's RAND for that tile)."""

    def __init__(self, x, z):
        self.x, self.z, self.k = x, z, 0

    def unary(self):
        self.k += 1
        return TM._hash(self.x, self.z, 7919 + self.k) / 4294967296.0

    def ranged(self, lo, hi):
        self.k += 1
        return lo + TM._hash(self.x, self.z, 7919 + self.k) % (hi - lo + 1)


def place(levels, climate, trees, winter=False):
    """[(kind, model file, x, z (tiles, z up), dy, sheer slot)] of every tree: levels (H, W) from forest_levels,
    climate (H, W) the index into trees (read_climates) of each tile."""
    H, W = levels.shape
    out = []

    def season(ci, kind):
        if not 0 <= ci < len(trees):
            return []
        s = trees[ci][1]
        return s["winter"][kind] if winter and s["winter"][kind] else s["summer"][kind]
    for z, x in zip(*np.nonzero(levels)):
        x, z = int(x), int(z)
        lev = int(levels[z, x])
        ci = int(climate[z, x])
        d = _Dice(x, z)
        if lev == 1:
            models = season(ci, "sparse_tree")
            for _ in range(3 if models else 0):
                tx, tz = x + d.unary(), z + d.unary()
                sheer = d.ranged(0, SHEERS - 1)
                out.append(("sparse_tree", models[d.ranged(0, len(models) - 1)][0], tx, tz, 0.0, sheer))
            continue

        def dense(dx, dz):
            return 1 if 0 <= x + dx < W and 0 <= z + dz < H and levels[z + dz, x + dx] == 3 else 0
        t, b, le, r = dense(0, 1), dense(0, -1), dense(-1, 0), dense(1, 0)
        models = season(ci, "dense_tree")
        if models:
            for letter in LATTICE[b + (r << 1) + (le << 2)]:
                ox, oz = SPOTS[letter]
                tx, tz = x + ox + 0.2 * d.unary() - 0.1, z + oz + 0.2 * d.unary() - 0.1
                sheer = d.ranged(0, SHEERS - 1)
                out.append(("dense_tree", models[d.ranged(0, len(models) - 1)][0], tx, tz, 0.0, sheer))
        models = season(ci, "canopy")
        if models:
            spots = [(0.5, 0.5)]
            if t:
                spots.append((0.5, 1.0))
                if r:
                    spots.append((1.0, 1.0))
            if r:
                spots.append((1.0, 0.5))
                if b:
                    spots.append((1.0, 0.0))
            tl, tr, bl, br = [_Q[1], _Q[3]], [_Q[3], _Q[3]], [_Q[1], _Q[1]], [_Q[3], _Q[1]]
            if not t:
                tl[1] -= _E
                tr[1] -= _E
                if not le:
                    tl[0] += _E
                if not r:
                    tr[0] -= _E
            if not b:
                bl[1] += _E
                br[1] += _E
                if not le:
                    bl[0] += _E
                if not r:
                    br[0] -= _E
            if not le:                                # the engine's own (tl and bl pulled twice on an open left)
                tl[0] += _E
                bl[0] += _E
            if not r:                                 # and pushed back on an open right
                tl[0] -= _E
                bl[0] -= _E
            spots += [tuple(tl), tuple(tr), tuple(bl), tuple(br)]
            for ox, oz in spots:
                tx, tz = x + ox + 0.1 * d.unary() - 0.05, z + oz + 0.1 * d.unary() - 0.05
                dy = 0.1 * d.unary() - 0.05
                sheer = d.ranged(0, SHEERS - 1)
                out.append(("canopy", models[d.ranged(0, len(models) - 1)][0], tx, tz, dy, sheer))
    return out


def sheers(time):
    """The 20 lean values at a moment (seconds)."""
    i = np.arange(SHEERS, dtype=np.float64)
    return 0.1 * np.cos((time * 0.25 + i / (SHEERS - 1)) * np.pi)


def instances(placed, heights, yscale):
    """{model file (lower case): (n, 4) float32 x y z sheer-slot in our world (x east, y up, z SOUTH from the top,
    tiles)} - each tree at the ground's height under it."""
    H = (heights.shape[0] - 1) // 2
    by = {}
    for kind, f, tx, tz, dy, sheer in placed:
        by.setdefault(f.lower(), []).append((tx, tz, dy, sheer))
    out = {}
    for f, rows in by.items():
        a = np.asarray(rows, np.float64)
        prow, pcol = 2 * (H - a[:, 1]), 2 * a[:, 0]
        y = TM._ground_h(heights, prow, pcol) * yscale + a[:, 2]
        out[f] = np.stack([a[:, 0], y, H - a[:, 1], a[:, 3]], 1).astype(np.float32)
    return out


class Models:
    """The tree models of a mod, read once each: model(file) -> (vertices (n, 8) x y z normal u v in our world,
    indices (k,) uint32, texture file under data/) or None."""

    def __init__(self, mod):
        self.mod, self._got, self.missing = mod, {}, set()

    def model(self, name):
        key = name.lower()
        if key in self._got:
            return self._got[key]
        from . import stratcas
        out = None
        path = self.mod.find_any("terrain/aerial_map/tree_models/" + name)
        if not path:
            self.missing.add(name)
        else:
            try:
                with open(path, "rb") as fh:
                    part = stratcas.read(fh.read())[0]
                P = np.asarray(part.positions, np.float32).reshape(-1, 3)
                N = np.asarray(part.normals, np.float32).reshape(-1, 3)
                U = np.asarray(part.uvs if part.uvs else [0.0] * (2 * len(P)), np.float32).reshape(-1, 2)
                P[:, 2] *= -1                         # the game's z runs north, ours south
                N[:, 2] *= -1
                v = np.concatenate([P, N, U], 1).astype(np.float32)
                tex = "terrain/aerial_map/tree_models/textures/" + part.texture if part.texture else None
                out = (v, np.asarray(part.faces, np.uint32), tex)
            except (OSError, ValueError, IndexError):
                self.missing.add(name)
        self._got[key] = out
        return out


__all__ = ["read_climates", "forest_levels", "place", "instances", "sheers", "Models", "KINDS", "SHEERS"]
