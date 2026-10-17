"""Interface: a menu page drawn by the graphics card (the user, 2026-10-17: dragging a piece lagged) - the way glmap
and glmesh draw: off the screen in the editor's one OpenGL context (glmap.context), read back as one picture.

Each picture sheet the page uses goes onto the card once; every piece is then a square cut out of its sheet and laid
where the piece stands, scaled by the card (before, each piece was cut and resized by Pillow again at every zoom
step and kept as a picture of its own). The words and the pieces the game draws itself go on the card the same way,
made once at the layout's own size. Drawn in the page's order, each over the one before (the pictures' alpha
blended as the game blends them)."""

try:
    import numpy as np
except ImportError:                             # the drawing on the canvas, as before
    np = None

VS = """
#version 330
uniform vec2 size;
in vec2 pos;
in vec2 uv;
in vec4 tint;
out vec2 t;
out vec4 c;
void main() {
    t = uv; c = tint;
    gl_Position = vec4(pos.x / size.x * 2.0 - 1.0, 1.0 - pos.y / size.y * 2.0, 0.0, 1.0);
}
"""

FS = """
#version 330
uniform sampler2D pic;
uniform int textured;
in vec2 t;
in vec4 c;
out vec4 colour;
void main() {
    colour = textured == 1 ? texture(pic, t) * c : c;
}
"""

_gl = {}                                        # the program, frames by size, textures by picture
KEEP = 256                                      # pictures kept on the card (sheets, words, drawn pieces)


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
    """True when the graphics card gives OpenGL 3.3 (and NumPy is there)."""
    if np is None:
        return False
    from .glmap import available as gl_available
    return gl_available()[0]


def _texture(ctx, img):
    """The picture on the card (its alpha kept), made once while the picture lives."""
    cache = _gl["tex"]
    got = cache.get(id(img))
    if got is not None and got[0] is img:
        cache[id(img)] = cache.pop(id(img))         # the newest used last: the oldest unused goes first
        return got[1]
    rgba = np.ascontiguousarray(np.asarray(img.convert("RGBA"), dtype=np.uint8))
    tex = ctx.texture((rgba.shape[1], rgba.shape[0]), 4, rgba.tobytes())
    tex.build_mipmaps()
    tex.filter = (ctx.LINEAR_MIPMAP_LINEAR, ctx.LINEAR)
    tex.repeat_x = tex.repeat_y = False
    cache[id(img)] = (img, tex)
    while len(cache) > KEEP:
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


def quad(x0, y0, x1, y1, u0=0.0, v0=0.0, u1=1.0, v1=1.0, rgba=(1.0, 1.0, 1.0, 1.0)):
    """The two triangles of a square on the screen (pixels) with its part of the picture (0..1): 6 rows of
    x, y, u, v, r, g, b, a."""
    r, g, b, a = rgba
    return [(x0, y0, u0, v0, r, g, b, a), (x1, y0, u1, v0, r, g, b, a), (x1, y1, u1, v1, r, g, b, a),
            (x0, y0, u0, v0, r, g, b, a), (x1, y1, u1, v1, r, g, b, a), (x0, y1, u0, v1, r, g, b, a)]


def picture_quad(img, box, rect):
    """A piece cut out of its sheet: box (x0, y0, x1, y1) in the sheet's pixels, rect where it goes on the screen."""
    W, H = img.size
    return quad(rect[0], rect[1], rect[2], rect[3], box[0] / W, box[1] / H, box[2] / W, box[3] / H)


def draw(W, H, background, ops):
    """The page as an (H, W, 3) uint8 array. ops in drawing order: (picture or None, [rows from quad()]) - None
    fills its squares with their colour. RuntimeError without OpenGL."""
    ctx = _context()
    if ctx is None:
        raise RuntimeError("no OpenGL 3.3")
    W, H = max(1, int(W)), max(1, int(H))
    fbo = _frame(ctx, W, H)
    fbo.use()
    ctx.viewport = (0, 0, W, H)
    bg = [v / 255.0 for v in background[:3]]
    ctx.clear(bg[0], bg[1], bg[2], 1.0)
    ctx.enable(ctx.BLEND)
    ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
    prog = _gl["prog"]
    prog["size"].value = (float(W), float(H))
    batch, cur = [], None

    def flush():
        if not batch:
            return
        data = np.asarray(batch, np.float32)
        vbo = ctx.buffer(data.tobytes())
        vao = ctx.vertex_array(prog, [(vbo, "2f 2f 4f", "pos", "uv", "tint")])
        prog["textured"].value = 1 if cur is not None else 0
        if cur is not None:
            _texture(ctx, cur).use(0)
            prog["pic"].value = 0
        vao.render(vertices=len(batch))
        vao.release()
        vbo.release()
        batch.clear()
    for img, rows in ops:
        if not rows:
            continue
        if img is not cur:                      # one call for each run of squares on the same picture
            flush()
            cur = img
        batch.extend(rows)
    flush()
    ctx.disable(ctx.BLEND)
    raw = fbo.read(components=3)
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3)[::-1].copy()


__all__ = ["available", "draw", "quad", "picture_quad"]
