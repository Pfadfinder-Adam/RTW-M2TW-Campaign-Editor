"""The 3D view's heavy work on NumPy arrays (the user, 2026-10-10: 'move it to NumPy - 20-30 MB more is nothing'):
posing a Medieval II mesh on its bones and drawing a model with its textures. meshview calls these when NumPy is
there and keeps its own pure-Python ways when it is not (a Python without NumPy, the tests' second run).

pose(): every point moved by its bones' matrices at once (one gather + a matrix product per bone weight) instead of
a Python loop over 5 000 points. draw(): a small rasteriser - every front-facing triangle's pixels found from its
box, kept when inside (half a pixel's leeway at each edge, as the old outlined polygons, so no seams show), the
nearest one per pixel kept (a depth buffer: no painter's sorting mistakes), its texture point found from the
corners' u v and the pixel's place in the triangle, shaded by the triangle's light. A still picture used to lay a
Pillow affine copy of the texture per triangle (5 000 small pictures a frame): this draws the same in one go, fast
enough for the full texture while an animation plays (measured: a pure-NumPy rasteriser was slower than Pillow's
own polygon filling - Pillow fills, NumPy colours)."""

import math

import numpy as np



# ---------------------------------------------------------------------------
# Posing
# ---------------------------------------------------------------------------
def _static(mesh):
    """The mesh's points, bones and weights as arrays, made once per mesh."""
    got = getattr(mesh, "_np", None)
    if got is None or got[0] is not mesh.arr:
        skin = np.asarray(mesh.skin, dtype=np.float64)
        got = (mesh.arr, mesh.arr, skin[:, 0].astype(np.int64),
               skin[:, 1].astype(np.int64), skin[:, 2].copy(), skin[:, 3].copy())
        mesh._np = got
    return got[1:]


def pose(mesh, n, mats, held_mats):
    """The posed points [(x, y, z)]. mats {bone: 12 floats (3 x 3 row by row, then the shift)} for bones 0..n-1;
    held_mats {(weapon bone, hand): 12 floats} - a weapon with its own move in the hand. The same rules as
    meshview.pose_mesh's loop: a weapon point without a move of its own is held by the hand (its second bone, else
    the pelvis), a point with no weights is all on its first bone."""
    P, b0, b1, w0, w1 = _static(mesh)
    table = [mats[b] for b in range(n)]
    held_idx = {}
    for key, m in held_mats.items():
        held_idx[key] = len(table)
        table.append(m)
    T = np.asarray(table, dtype=np.float64)
    M, t = T[:, :9].reshape(-1, 3, 3), T[:, 9:]
    hand = np.where((b1 > 0) & (b1 < n), b1, 12 if n == 20 else 0)    # meshview.hand_of
    i0 = np.where(b0 >= n, hand, b0)
    i1 = np.where(b1 >= n, i0, b1)
    if held_idx:
        for (wb, h), k in held_idx.items():
            hit = (b0 == wb) & (hand == h)
            i0 = np.where(hit, k, i0)
            i1 = np.where(hit, k, i1)
    a0 = np.where((w0 <= 0) & (w1 <= 0), 1.0, np.maximum(w0, 0.0))
    a1 = np.where(i1 == i0, 0.0, np.maximum(w1, 0.0))
    tw = a0 + a1
    tw[tw == 0] = 1.0
    p, r = (a0 / tw)[:, None], (a1 / tw)[:, None]
    out = p * (np.einsum("nij,nj->ni", M[i0], P) + t[i0]) + r * (np.einsum("nij,nj->ni", M[i1], P) + t[i1])
    return out


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
_PICS = {}


def _pic(img):
    """A picture as an (h, w, 3) array, kept while the picture lives."""
    got = _PICS.get(id(img))
    if got is None or got[0] is not img:
        got = _PICS[id(img)] = (img, np.asarray(img.convert("RGB"), dtype=np.uint8))
        while len(_PICS) > 16:
            _PICS.pop(next(iter(_PICS)))
    return got[1]


_UVS = {}


def _uv(uvs):
    """The u v list as an array, kept while the list lives (the same at every frame of a play)."""
    if not uvs:
        return None
    got = _UVS.get(id(uvs))
    if got is None or got[0] is not uvs:
        got = _UVS[id(uvs)] = (uvs, np.asarray(uvs, dtype=np.float64).reshape(-1, 2))
        while len(_UVS) > 16:
            _UVS.pop(next(iter(_UVS)))
    return got[1]


_TRIS = {}


def _triangles(mesh, groups):
    """(corners (m, 3) point numbers, picture of each, one-texture flag of each) for the groups drawn - made once
    per set of parts (the same at every frame of a play)."""
    key = (tuple(id(g) for g in groups), mesh.one_texture)
    got = _TRIS.get(key)
    if got is not None and all(a is b for a, b in zip(got[0], groups)):
        return got[1]
    got = _TRIS[key] = (list(groups), _make_triangles(mesh, groups))
    while len(_TRIS) > 16:
        _TRIS.pop(next(iter(_TRIS)))
    return got[1]


def _make_triangles(mesh, groups):
    tris, pic, one = [], [], []
    for g in groups:
        t = np.asarray(g.tris, dtype=np.int64)
        k = len(t) // 3
        if not k:
            continue
        tris.append(t[:3 * k].reshape(k, 3))
        pic.append(np.full(k, getattr(g, "pic", 0), dtype=np.int64))
        one.append(np.full(k, bool(getattr(g, "one", mesh.one_texture))))
    if not tris:
        return None
    return np.concatenate(tris), np.concatenate(pic), np.concatenate(one)


def draw(mesh, groups, fit, W, H, yaw, pitch, zoom, pics, textured, background, light, plain, frame=None,
         pan=(0.0, 0.0)):
    """The model drawn as an (H, W, 3) uint8 array; pics {picture number: PIL picture or None} (0 / 1 the man's
    texture and attachment, 2 / 3 a mount's ...). textured False: one colour per triangle (its texture's colour at
    the middle and the corners, as the quick look always was).

    Pillow fills the front-facing triangles far to near with their numbers (a 'which triangle is seen here' map,
    each outlined so no seams show - as the old drawing); then every seen pixel at once: its place inside its
    triangle, the texture's colour there, the triangle's light."""
    from PIL import Image, ImageDraw
    tri = _triangles(mesh, groups)
    out = np.empty((H, W, 3), dtype=np.uint8)
    out[:] = background
    if tri is None:
        return out
    T, base, one = tri
    P = mesh.arr
    used = np.unique(T)
    ft = _triangles(mesh, fit) if fit else None
    sized = np.unique(ft[0]) if ft is not None else used
    if not len(sized):
        sized = used
    if frame is not None:                       # kept by the window while an animation plays (meshview.frame_of)
        c, radius = np.asarray(frame[0], dtype=np.float64), float(frame[1])
    else:
        S = P[sized]
        c = (S.min(axis=0) + S.max(axis=0)) / 2
        radius = float(np.sqrt(((S - c) ** 2).sum(axis=1)).max()) or 1.0
    scale = zoom * 0.95 * min(W, H) / (2 * radius)
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    x, y, z = c[0] - P[:, 0], P[:, 1] - c[1], P[:, 2] - c[2]        # x mirrored: left-handed to right-handed
    x, z = x * cy + z * sy, -x * sy + z * cy
    y, z = y * cp - z * sp, y * sp + z * cp
    sx, sy_, sz = W / 2 + pan[0] + x * scale, H / 2 + pan[1] - y * scale, z
    A, B, C = T[:, 0], T[:, 1], T[:, 2]
    ux, uy, uz = sx[B] - sx[A], sy_[A] - sy_[B], sz[B] - sz[A]
    vx, vy, vz = sx[C] - sx[A], sy_[A] - sy_[C], sz[C] - sz[A]
    nx, ny, nz = -(uy * vz - uz * vy), -(uz * vx - ux * vz), -(ux * vy - uy * vx)
    nl = np.sqrt(nx * nx + ny * ny + nz * nz)
    nl[nl == 0] = 1.0
    L = np.asarray(light, dtype=np.float64)
    L = L / np.sqrt((L * L).sum())
    shade = 0.32 + 0.68 * np.maximum(0.0, (nx * L[0] + ny * L[1] + nz * L[2]) / nl)
    keep = np.nonzero(nz > 0)[0]                         # facing away: not drawn (the game does not either)
    if not len(keep):
        return out
    keep = keep[np.argsort(sz[A[keep]] + sz[B[keep]] + sz[C[keep]], kind="stable")]     # far first
    X = np.stack([sx[A], sx[B], sx[C]], axis=1)
    Y = np.stack([sy_[A], sy_[B], sy_[C]], axis=1)
    seen = Image.new("I", (W, H), 0)
    dr = ImageDraw.Draw(seen)
    corners = np.stack([X[keep], Y[keep]], axis=2).tolist()
    for t, pts in zip((keep + 1).tolist(), corners):
        dr.polygon([tuple(p) for p in pts], fill=t, outline=t)
    ids = np.asarray(seen, dtype=np.int64)
    py, px = np.nonzero(ids)
    if not len(px):
        return out
    t = ids[py, px] - 1
    # which picture and u v: two textures side by side unless the group has one
    uvs = _uv(mesh.uvs)
    arrays = {k: (_pic(im) if im is not None else None) for k, im in pics.items()}
    col = np.empty((len(t), 3), dtype=np.float64)
    col[:] = plain
    if uvs is not None:
        U = uvs[T][:, :, 0]
        V = uvs[T][:, :, 1]
        half = np.where(one, 0, (U.mean(axis=1) >= 0.5).astype(np.int64))
        U = np.where(one[:, None], U, U * 2 - half[:, None])
        pic = base + half
        if textured:
            # the pixel's place inside its triangle (its three weights), held inside it at the outlined edges
            cx, cy_ = px + 0.5, py + 0.5
            ax, ay, bx, by_, qx, qy = X[t, 0], Y[t, 0], X[t, 1], Y[t, 1], X[t, 2], Y[t, 2]
            area = (bx - ax) * (qy - ay) - (qx - ax) * (by_ - ay)
            area = np.where(np.abs(area) < 1e-9, 1e-9, area)
            wa = ((bx - cx) * (qy - cy_) - (qx - cx) * (by_ - cy_)) / area
            wb = ((qx - cx) * (ay - cy_) - (ax - cx) * (qy - cy_)) / area
            wa, wb = np.clip(wa, 0, 1), np.clip(wb, 0, 1)
            both = wa + wb
            over = both > 1
            both = np.where(over, both, 1.0)
            wa, wb = wa / both, wb / both
            wc = 1.0 - wa - wb
            u = wa * U[t, 0] + wb * U[t, 1] + wc * U[t, 2]
            v = wa * V[t, 0] + wb * V[t, 1] + wc * V[t, 2]
            pw = pic[t]
            for k, arr in arrays.items():
                s_ = pw == k
                if arr is not None and s_.any():
                    col[s_] = _sample(arr, u[s_], v[s_])
        else:                                            # one colour per triangle
            colour = np.empty((len(T), 3), dtype=np.float64)
            colour[:] = plain
            for k, arr in arrays.items():
                sel = np.nonzero(pic == k)[0]
                if arr is None or not len(sel):
                    continue
                mu, mv = U[sel].mean(axis=1), V[sel].mean(axis=1)
                acc = _sample(arr, mu, mv).astype(np.float64)
                for j in range(3):
                    acc += _sample(arr, (mu * 2 + U[sel, j]) / 3, (mv * 2 + V[sel, j]) / 3)
                colour[sel] = acc / 4
            col = colour[t]
    out[py, px] = np.clip(col * shade[t][:, None], 0, 255).astype(np.uint8)
    return out


def _sample(arr, u, v):
    """Texture colours at u v (u held inside the picture, v wrapped - as meshview's sampler)."""
    h, w = arr.shape[:2]
    px = np.clip((u * (w - 1)).astype(np.int64), 0, w - 1)
    py = np.clip(((v % 1.0) * (h - 1)).astype(np.int64), 0, h - 1)
    return arr[py, px]
