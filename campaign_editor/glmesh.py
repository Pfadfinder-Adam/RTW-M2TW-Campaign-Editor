"""View in 3D (units, mounts, siege engines) drawn by the graphics card - the same picture fastmesh draws with
Pillow and NumPy, filled by OpenGL instead (the user, 2026-10-17: 'the units on OpenGL too').

Where each point lands, each triangle's light and texture point come from fastmesh (screen, tex_coords,
flat_colours: one place for both drawings); the card only fills the triangles - a depth buffer for what is in
front, the texture read at each pixel, the games' alpha test (a texture point below 128 is not drawn: round
shields cut out of squares). The frame is drawn off the screen in the editor's one OpenGL context (glmap.context)
and read back as a picture. meshview.render uses it when the card gives OpenGL 3.3, else fastmesh."""

import numpy as np

from . import fastmesh as F

VS = """
#version 330
in vec3 pos;
in vec2 uv;
in vec3 tint;
out vec2 t;
out vec3 c;
void main() { t = uv; c = tint; gl_Position = vec4(pos, 1.0); }
"""

FS = """
#version 330
uniform sampler2D pic;
uniform int textured;
in vec2 t;
in vec3 c;
out vec4 colour;
void main() {
    if (textured == 1) {
        vec4 p = texture(pic, t);
        if (p.a < 0.5) discard;                 // the games' alpha test
        colour = vec4(p.rgb * c, 1.0);
    } else {
        colour = vec4(c, 1.0);
    }
}
"""

_gl = {}                                        # the program, frames by size, textures by picture


def _context():
    from .glmap import context
    ctx = context()
    if ctx is None:
        return None
    if _gl.get("ctx") is not ctx:
        _gl.clear()
        _gl["ctx"] = ctx
        _gl["prog"] = ctx.program(vertex_shader=VS, fragment_shader=FS)
        _gl["fbo"] = {}
        _gl["tex"] = {}
    return ctx


def available():
    from .glmap import available as gl_available
    return gl_available()[0]


def _texture(ctx, img):
    """The picture on the card (its alpha kept), made once while the picture lives."""
    cache = _gl["tex"]
    got = cache.get(id(img))
    if got is not None and got[0] is img:
        return got[1]
    rgba = np.ascontiguousarray(np.asarray(img.convert("RGBA"), dtype=np.uint8))
    tex = ctx.texture((rgba.shape[1], rgba.shape[0]), 4, rgba.tobytes())
    tex.build_mipmaps()
    tex.filter = (ctx.LINEAR_MIPMAP_LINEAR, ctx.LINEAR)
    tex.repeat_x, tex.repeat_y = False, True     # u held inside the picture, v wrapped (as fastmesh samples)
    cache[id(img)] = (img, tex)
    while len(cache) > 16:
        old = cache.pop(next(iter(cache)))
        old[1].release()
    return tex


def _frame(ctx, W, H):
    fbos = _gl["fbo"]
    fbo = fbos.get((W, H))
    if fbo is None:
        for old in list(fbos.values()):
            old.release()
        fbos.clear()
        fbo = fbos[(W, H)] = ctx.simple_framebuffer((W, H))
    return fbo


def draw(mesh, groups, fit, W, H, yaw, pitch, zoom, pics, textured, background, light, plain, frame=None,
         pan=(0.0, 0.0)):
    """fastmesh.draw on the graphics card: the model as an (H, W, 3) uint8 array. RuntimeError without OpenGL."""
    ctx = _context()
    if ctx is None:
        raise RuntimeError("no OpenGL 3.3")
    got = F.screen(mesh, groups, fit, W, H, yaw, pitch, zoom, light, frame, pan)
    fbo = _frame(ctx, W, H)
    fbo.use()
    ctx.viewport = (0, 0, W, H)
    bg = [v / 255.0 for v in background[:3]]
    ctx.clear(bg[0], bg[1], bg[2], 1.0, depth=1.0)
    if got is not None and len(got[7]):
        T, base, one, sx, sy, sz, shade, keep = got
        corners = T[keep]
        lo, hi = float(sz.min()), float(sz.max())
        depth = 1.0 - 2.0 * (sz - lo) / max(hi - lo, 1e-9) * 0.98 - 0.01      # nearer = smaller, inside -1..1
        pos = np.stack([sx / W * 2 - 1, 1 - sy / H * 2, depth], 1)[corners]  # (n, 3 corners, 3)
        tc = F.tex_coords(mesh, T, base, one)
        if tc is not None:
            uv = np.stack([tc[0], tc[1]], 2)[keep]
            pic = tc[2][keep]
        else:
            uv, pic = np.zeros((len(keep), 3, 2)), np.full(len(keep), -1)
        light_of = shade[keep]
        arrays = {k: (F._pic(im) if im is not None else None) for k, im in pics.items()}
        if textured and tc is not None:
            passes = [(k, pic == k) for k, im in pics.items() if im is not None]
            plain_sel = ~np.isin(pic, [k for k, im in pics.items() if im is not None])
            tint = np.repeat(light_of[:, None], 3, 1)
            colour = np.empty((len(keep), 3))
            colour[:] = np.asarray(plain, np.float64) / 255.0
            colour *= tint
        else:
            flat = F.flat_colours(arrays, tc[0], tc[1], tc[2], plain, len(T))[keep] if tc is not None else \
                np.repeat(np.asarray(plain, np.float64)[None, :], len(keep), 0)
            colour = flat / 255.0 * light_of[:, None]
            passes, plain_sel, tint = [], np.ones(len(keep), bool), None
        ctx.enable(ctx.DEPTH_TEST)
        ctx.disable(ctx.CULL_FACE)                 # the facing-away triangles are already left out (fastmesh.screen)
        prog = _gl["prog"]

        def fill(sel, rgb, tex):
            if not sel.any():
                return
            n = int(sel.sum())
            data = np.concatenate([pos[sel].reshape(-1, 3), uv[sel].reshape(-1, 2),
                                   np.repeat(rgb[sel], 3, 0)], 1).astype(np.float32)
            vbo = ctx.buffer(data.tobytes())
            vao = ctx.vertex_array(prog, [(vbo, "3f 2f 3f", "pos", "uv", "tint")])
            prog["textured"].value = 1 if tex is not None else 0
            if tex is not None:
                tex.use(0)
                prog["pic"].value = 0
            vao.render(vertices=n * 3)
            vao.release()
            vbo.release()
        fill(plain_sel, colour, None)
        for k, sel in passes:
            fill(sel, np.repeat(light_of[:, None], 3, 1), _texture(ctx, pics[k]))
        ctx.disable(ctx.DEPTH_TEST)
    raw = fbo.read(components=3)
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)[::-1].copy()


__all__ = ["draw", "available"]
