"""Maps > 3D drawn by the graphics card straight into the window (the user, 2026-10-17: step 2 - the frame was read
back from the card, made a picture and handed to Tk every time; that pipe, not the card, made the map lag).

The editor keeps its one OpenGL context (glmap.context); the map is still drawn into its frame off the screen (the
mouse reads the ground from that frame's depth), then the card itself copies the frame into the window, draws the
brush's ring / the tile frame over it and shows it - nothing comes back to the CPU. On Windows the window is a Tk
frame given the context's own pixel format, so the one context draws into it (wglMakeCurrent with the frame's DC)
and every texture already on the card stays usable. Elsewhere, or when anything in it fails, Maps > 3D draws as
before (a picture on the canvas) - never a crash."""

import ctypes
import math
import sys

try:
    import numpy as np
except ImportError:
    np = None

VS = """
#version 330
uniform vec2 size;
in vec2 pos;
in vec4 tint;
out vec4 c;
void main() {
    c = tint;
    gl_Position = vec4(pos.x / size.x * 2.0 - 1.0, 1.0 - pos.y / size.y * 2.0, 0.0, 1.0);
}
"""

FS = """
#version 330
in vec4 c;
out vec4 colour;
void main() {
    colour = c;
}
"""


def thick_line(points, width, rgba):
    """A line through points (screen pixels) as triangles width pixels wide: rows of x, y, r, g, b, a (the card
    draws lines one pixel wide only)."""
    rows, h = [], width / 2.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        if n < 1e-6:
            continue
        nx, ny = -dy / n * h, dx / n * h
        ex, ey = dx / n * h, dy / n * h                   # a little past each end: the joints show no gaps
        a = (x0 - ex + nx, y0 - ey + ny)
        b = (x1 + ex + nx, y1 + ey + ny)
        c = (x1 + ex - nx, y1 + ey - ny)
        d = (x0 - ex - nx, y0 - ey - ny)
        rows += [(*p, *rgba) for p in (a, b, c, a, c, d)]
    return rows


class Overlay:
    """The lines drawn over the map on the card (the brush's ring, the carried figure's tile frame)."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=VS, fragment_shader=FS)

    def draw(self, W, H, lines):
        """lines: [(points, width, rgba)] in screen pixels, drawn in order into the framebuffer in use."""
        rows = [r for pts, width, rgba in lines for r in thick_line(pts, width, rgba)]
        if not rows:
            return
        ctx = self.ctx
        self.prog["size"].value = (float(W), float(H))
        vbo = ctx.buffer(np.asarray(rows, np.float32).tobytes())
        vao = ctx.vertex_array(self.prog, [(vbo, "2f 4f", "pos", "tint")])
        ctx.enable_only(ctx.BLEND)
        ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
        vao.render(vertices=len(rows))
        ctx.disable(ctx.BLEND)
        vao.release()
        vbo.release()


def show(ctx, frame, screen, W, H, lines, overlay):
    """The map's frame copied into screen (the window's own framebuffer) by the card, the lines over it."""
    ctx.copy_framebuffer(screen, frame)
    screen.use()
    ctx.viewport = (0, 0, W, H)
    overlay.draw(W, H, lines)


class _PFD(ctypes.Structure):
    _fields_ = [("nSize", ctypes.c_ushort), ("nVersion", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong)] + \
        [(n, ctypes.c_ubyte) for n in ("iPixelType", "cColorBits", "cRedBits", "cRedShift", "cGreenBits",
                                        "cGreenShift", "cBlueBits", "cBlueShift", "cAlphaBits", "cAlphaShift",
                                        "cAccumBits", "cAccumRedBits", "cAccumGreenBits", "cAccumBlueBits",
                                        "cAccumAlphaBits", "cDepthBits", "cStencilBits", "cAuxBuffers",
                                        "iLayerType", "bReserved")] + \
        [("dwLayerMask", ctypes.c_ulong), ("dwVisibleMask", ctypes.c_ulong), ("dwDamageMask", ctypes.c_ulong)]


class WindowGL:
    """The editor's one OpenGL context drawing into a Tk frame (Windows). attach() says True when it can; present()
    copies a frame there and shows it. Any failure: False / an exception - the caller draws as before."""

    def __init__(self, ctx):
        self.ctx, self.dc, self.hwnd, self.overlay = ctx, None, None, None
        self.why = ""

    def attach(self, hwnd):
        if sys.platform != "win32":
            self.why = "drawn straight into the window on Windows only"
            return False
        try:
            u, g, w = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.opengl32
            vp = ctypes.c_void_p
            u.GetDC.restype, u.GetDC.argtypes = vp, [vp]
            for f in (w.wglGetCurrentDC, w.wglGetCurrentContext):
                f.restype, f.argtypes = vp, []
            w.wglMakeCurrent.restype, w.wglMakeCurrent.argtypes = ctypes.c_int, [vp, vp]
            g.GetPixelFormat.restype, g.GetPixelFormat.argtypes = ctypes.c_int, [vp]
            g.DescribePixelFormat.restype = ctypes.c_int
            g.DescribePixelFormat.argtypes = [vp, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(_PFD)]
            g.SetPixelFormat.restype, g.SetPixelFormat.argtypes = ctypes.c_int, [vp, ctypes.c_int, ctypes.POINTER(_PFD)]
            g.SwapBuffers.restype, g.SwapBuffers.argtypes = ctypes.c_int, [vp]
            self._u, self._g, self._w = u, g, w
            with self.ctx:                                    # the context's own window: its DC and pixel format
                own_dc, rc = w.wglGetCurrentDC(), w.wglGetCurrentContext()
            if not own_dc or not rc:
                self.why = "no OpenGL context to share"
                return False
            fmt = g.GetPixelFormat(own_dc)
            pfd = _PFD()
            pfd.nSize = ctypes.sizeof(_PFD)
            if not fmt or not g.DescribePixelFormat(own_dc, fmt, ctypes.sizeof(_PFD), ctypes.byref(pfd)):
                self.why = "the context's pixel format not readable"
                return False
            dc = u.GetDC(hwnd)
            have = g.GetPixelFormat(dc)
            if have != fmt and (have or not g.SetPixelFormat(dc, fmt, ctypes.byref(pfd))):
                self.why = "the window took no OpenGL pixel format"
                return False
            self.own_dc, self.rc, self.dc, self.hwnd = own_dc, rc, dc, hwnd
            self.overlay = Overlay(self.ctx)
            return True
        except Exception as e:                                # never a crash: drawn as before
            self.why = str(e)
            return False

    def present(self, frame, W, H, lines=()):
        """The frame (the map drawn off the screen, W x H) shown in the window with the lines over it."""
        w = self._w
        if not w.wglMakeCurrent(self.dc, self.rc):
            raise RuntimeError("the window's OpenGL could not be made current")
        try:
            ctx = self.ctx
            ctx.viewport = (0, 0, W, H)
            screen = ctx.detect_framebuffer(0)
            show(ctx, frame, screen, W, H, lines, self.overlay)
            ctx.finish()
            self._g.SwapBuffers(self.dc)
        finally:
            w.wglMakeCurrent(self.own_dc, self.rc)            # the context's own window again: everything else as before


__all__ = ["WindowGL", "Overlay", "show", "thick_line"]
