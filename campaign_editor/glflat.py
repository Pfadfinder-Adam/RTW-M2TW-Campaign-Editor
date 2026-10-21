"""Coast & heights drawn by the graphics card (the user, 2026-10-21: 'step 2 - the heights map on the card, as the 3D
map'): the map's picture lies on the card as one texture, moving and zooming only change where the card shows it;
the shore line goes as one buffer of lines; whatever the window draws over the map (the brush's outline, the grid,
marks, the selection box) is taken from the canvas as lines and shapes and drawn by the card on top. The frame is
shown in the window by glwindow (Windows); elsewhere, or when anything in it fails, the tab draws as before (a
picture on the canvas) - never a crash.

Coordinates as MapView's: a tile (tx, ty) - ty from the map's top - is on the screen at ((tx - ox) * z, (ty - oy) * z);
the picture has per_tile pixels a tile, its top row the map's top."""

import math

try:
    import numpy as np
except ImportError:
    np = None

VS_PIC = """
#version 330
uniform vec2 size;
in vec2 pos;
in vec2 uv;
out vec2 t;
void main() {
    t = uv;
    gl_Position = vec4(pos.x / size.x * 2.0 - 1.0, 1.0 - pos.y / size.y * 2.0, 0.0, 1.0);
}
"""

FS_PIC = """
#version 330
uniform sampler2D pic;
in vec2 t;
out vec4 colour;
void main() {
    colour = vec4(texture(pic, t).rgb, 1.0);
}
"""


def segments_rows(seg, width, rgba):
    """Line pieces seg (N x 4: x0, y0, x1, y1 in screen pixels) as triangles width pixels wide - rows of x, y, r, g,
    b, a, six a piece (the card draws lines one pixel wide only); worked out at once for all of them."""
    seg = np.asarray(seg, np.float32).reshape(-1, 4)
    if not len(seg):
        return np.zeros((0, 6), np.float32)
    d = seg[:, 2:4] - seg[:, 0:2]
    n = np.hypot(d[:, 0], d[:, 1])
    keep = n > 1e-6
    seg, d, n = seg[keep], d[keep], n[keep]
    u = d / n[:, None] * (width / 2.0)                  # along the piece, half the width
    v = np.stack([-u[:, 1], u[:, 0]], 1)                # across it
    p0, p1 = seg[:, 0:2] - u, seg[:, 2:4] + u           # a little past each end: the joints show no gaps
    a, b, c, e = p0 + v, p1 + v, p1 - v, p0 - v
    pts = np.stack([a, b, c, a, c, e], 1).reshape(-1, 2)
    col = np.broadcast_to(np.asarray(rgba, np.float32), (len(pts), 4))
    return np.concatenate([pts, col], 1).astype(np.float32)


def fan_rows(points, rgba):
    """A filled shape (convex: a rectangle, an oval, the canvas's polygons) as triangles from its first point."""
    rows = []
    for i in range(1, len(points) - 1):
        for p in (points[0], points[i], points[i + 1]):
            rows.append((p[0], p[1], *rgba))
    return np.asarray(rows, np.float32).reshape(-1, 6)


def _rgba(canvas, colour, stipple=""):
    if not colour:
        return None
    try:
        r, g, b = canvas.winfo_rgb(colour)
    except Exception:
        return None
    return (r / 65535.0, g / 65535.0, b / 65535.0, 0.5 if stipple else 1.0)


def _oval(x0, y0, x1, y1, n=28):
    cx, cy, rx, ry = (x0 + x1) / 2.0, (y0 + y1) / 2.0, abs(x1 - x0) / 2.0, abs(y1 - y0) / 2.0
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def canvas_rows(canvas, skip=("bg",)):
    """Everything drawn on the canvas but the map's own picture - lines, rectangles, ovals, polygons - as triangle
    rows for the card, in the canvas's stacking order (texts and pictures are left out: Coast & heights draws
    none over the map)."""
    out = []
    for item in canvas.find_all():
        tags = canvas.gettags(item)
        if any(t in tags for t in skip) or canvas.itemcget(item, "state") == "hidden":
            continue
        kind = canvas.type(item)
        xy = canvas.coords(item)
        if kind not in ("line", "rectangle", "oval", "polygon") or len(xy) < 4:
            continue
        pts = list(zip(xy[0::2], xy[1::2]))
        width = float(canvas.itemcget(item, "width") or 1)
        stipple = canvas.itemcget(item, "stipple")
        fill = _rgba(canvas, canvas.itemcget(item, "fill"), stipple)
        if kind == "line":
            if fill:
                seg = [(a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:])]
                out.append(segments_rows(seg, max(width, 1.0), fill))
            continue
        if kind == "rectangle":
            (x0, y0), (x1, y1) = pts[0], pts[1]
            pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        elif kind == "oval":
            pts = _oval(pts[0][0], pts[0][1], pts[1][0], pts[1][1])
        if fill:
            out.append(fan_rows(pts, fill))
        line = _rgba(canvas, canvas.itemcget(item, "outline"), canvas.itemcget(item, "outlinestipple"))
        if line and width > 0:
            ring = pts + pts[:1]
            out.append(segments_rows([(a[0], a[1], b[0], b[1]) for a, b in zip(ring, ring[1:])], width, line))
    return np.concatenate(out) if out else np.zeros((0, 6), np.float32)


class FlatGL:
    """The heights map on the card: set_picture() lays the map's picture on it (again only when it is another one),
    frame() draws the view - the picture where the view puts it, the shore line, the canvas's own lines - into an
    off-screen frame (self.fbo) that glwindow shows."""

    def __init__(self, ctx):
        from .glwindow import FS, VS
        self.ctx = ctx
        self.pic_prog = ctx.program(vertex_shader=VS_PIC, fragment_shader=FS_PIC)
        self.line_prog = ctx.program(vertex_shader=VS, fragment_shader=FS)
        self.tex, self._pic_of, self.fbo, self.fbo_size = None, None, None, None

    def set_picture(self, pic):
        """The map's picture (PIL, RGB) onto the card - only when it is another picture than the one there."""
        if pic is self._pic_of and self.tex is not None:
            return
        rgb = pic.convert("RGB")
        if self.tex is None or self.tex.size != rgb.size:
            if self.tex is not None:
                self.tex.release()
            self.tex = self.ctx.texture(rgb.size, 3, rgb.tobytes())
            self.tex.filter = (self.ctx.NEAREST, self.ctx.NEAREST)        # sharp tiles, as the canvas shows them
            self.tex.repeat_x = self.tex.repeat_y = False
        else:
            self.tex.write(rgb.tobytes())
        self._pic_of = pic

    def frame(self, W, H, view, field, per_tile, rows):
        """The view (ox, oy, z, map width, map height in tiles) drawn W x H into self.fbo: the field, the picture, the
        map's edge, then rows (triangle rows: the shore line, the canvas's lines) on top."""
        ctx = self.ctx
        if self.fbo is None or self.fbo_size != (W, H):
            if self.fbo is not None:
                self.fbo.release()
            self.fbo = ctx.simple_framebuffer((W, H), components=4)
            self.fbo_size = (W, H)
        self.fbo.use()
        ctx.viewport = (0, 0, W, H)
        ctx.clear(field[0] / 255.0, field[1] / 255.0, field[2] / 255.0, 1.0)
        ox, oy, z, mw, mh = view
        x0, y0, x1, y1 = -ox * z, -oy * z, (mw - ox) * z, (mh - oy) * z
        if self.tex is not None:
            # the picture's pixels as many tiles as the map has (per_tile a tile); its last pixels may run past
            u1 = mw * per_tile / float(self.tex.size[0])
            v1 = mh * per_tile / float(self.tex.size[1])
            quad = np.asarray([(x0, y0, 0, 0), (x1, y0, u1, 0), (x1, y1, u1, v1),
                               (x0, y0, 0, 0), (x1, y1, u1, v1), (x0, y1, 0, v1)], np.float32)
            self.pic_prog["size"].value = (float(W), float(H))
            self.tex.use(0)
            self.pic_prog["pic"].value = 0
            vbo = ctx.buffer(quad.tobytes())
            vao = ctx.vertex_array(self.pic_prog, [(vbo, "2f 2f", "pos", "uv")])
            ctx.enable_only(0)
            vao.render()
            vao.release()
            vbo.release()
        edge = segments_rows([(x0 - 1, y0 - 1, x1, y0 - 1), (x1, y0 - 1, x1, y1), (x1, y1, x0 - 1, y1),
                              (x0 - 1, y1, x0 - 1, y0 - 1)], 1.0, (120 / 255.0, 124 / 255.0, 132 / 255.0, 1.0))
        rows = np.concatenate([edge, rows]) if len(rows) else edge
        self.line_prog["size"].value = (float(W), float(H))
        vbo = ctx.buffer(np.ascontiguousarray(rows, np.float32).tobytes())
        vao = ctx.vertex_array(self.line_prog, [(vbo, "2f 4f", "pos", "tint")])
        ctx.enable_only(ctx.BLEND)
        ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
        vao.render(vertices=len(rows))
        ctx.disable(ctx.BLEND)
        vao.release()
        vbo.release()

    def read(self):
        """The frame back as RGB bytes, top row first (the tests; the window never reads it)."""
        W, H = self.fbo_size
        raw = self.fbo.read(components=3)
        row = 3 * W
        return b"".join(raw[(H - 1 - y) * row:(H - y) * row] for y in range(H))

    def release(self):
        for x in (self.tex, self.fbo):
            if x is not None:
                x.release()
        self.tex = self.fbo = None


__all__ = ["FlatGL", "canvas_rows", "segments_rows", "fan_rows"]
