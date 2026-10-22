"""The board's maths: an endless sheet seen through a window, as on Obsidian Canvas (the user, 2026-10-22: 'like in
Canvas - move it, look around, zoom in; a screenshot laid on it lands on the grid'). World points are the sheet's own
(a HUD on it is one world unit per screen pixel); the window shows them at a zoom from an offset. No tkinter here, so
the tests run anywhere; gui_board.Board is the canvas that uses it (the Campaign HUD and the editor's layout board).

View: to_screen / to_world, zoom_at (the point under the mouse stays put), pan, fit (a world box into the window).
snap / snap_box: a box's corner onto the grid and its edges onto other boxes' edges within a few screen pixels."""

import math

ZOOMS = (0.1, 0.125, 0.167, 0.25, 0.333, 0.5, 0.667, 0.75, 1, 1.25, 1.5, 2, 3, 4, 6, 8)
GRID = 16                   # world units between two grid dots (a 1024 x 768 HUD is 64 x 48 of them)
SNAP_PX = 8                 # how near (screen pixels) an edge comes before it sticks - tldraw's own 8


class View:
    def __init__(self, zoom=1.0, ox=0.0, oy=0.0):
        self.zoom, self.ox, self.oy = zoom, ox, oy           # screen = world * zoom + offset

    def to_screen(self, x, y):
        return x * self.zoom + self.ox, y * self.zoom + self.oy

    def to_world(self, sx, sy):
        return (sx - self.ox) / self.zoom, (sy - self.oy) / self.zoom

    def pan(self, dx, dy):
        self.ox += dx
        self.oy += dy

    def set_zoom(self, z, at=(0, 0)):
        """z (kept within ZOOMS' ends), the world point under at (screen x, y) staying where it is."""
        z = max(ZOOMS[0], min(ZOOMS[-1], z))
        wx, wy = self.to_world(*at)
        self.zoom = z
        self.ox, self.oy = at[0] - wx * z, at[1] - wy * z

    def zoom_at(self, up, at, fine=False):
        """One step in or out at the mouse: the next of ZOOMS, or 5 % with fine (Shift)."""
        if fine:
            z = self.zoom * (1.05 if up else 1 / 1.05)
        elif up:
            z = next((s for s in ZOOMS if s > self.zoom + 1e-9), ZOOMS[-1])
        else:
            z = next((s for s in reversed(ZOOMS) if s < self.zoom - 1e-9), ZOOMS[0])
        self.set_zoom(z, at)

    def fit(self, box, width, height, margin=24, most=None):
        """The world box (x0, y0, x1, y1) as big as the window (width x height) takes, in its middle; most caps the
        zoom (1 = never bigger than 100 %)."""
        x0, y0, x1, y1 = box
        bw, bh = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        z = min((width - 2 * margin) / bw, (height - 2 * margin) / bh)
        z = max(ZOOMS[0], min(ZOOMS[-1] if most is None else most, z))
        self.zoom = z
        self.ox = width / 2 - (x0 + bw / 2) * z
        self.oy = height / 2 - (y0 + bh / 2) * z

    def visible(self, width, height):
        """The world box the window shows."""
        x0, y0 = self.to_world(0, 0)
        x1, y1 = self.to_world(width, height)
        return x0, y0, x1, y1

    def grid_step(self, step=GRID, least_px=10):
        """The grid step drawn at this zoom: step, times 4 until the dots are at least least_px apart on the screen
        (zoomed far out a dot every 16 world units would be a grey fog)."""
        while step * self.zoom < least_px:
            step *= 4
        return step

    def grid_points(self, width, height, step=GRID, least_px=10):
        """The grid's dots inside the window: (world step, [(screen x, screen y)])."""
        s = self.grid_step(step, least_px)
        x0, y0, x1, y1 = self.visible(width, height)
        xs = [i * s for i in range(math.floor(x0 / s), math.ceil(x1 / s) + 1)]
        ys = [j * s for j in range(math.floor(y0 / s), math.ceil(y1 / s) + 1)]
        return s, [self.to_screen(x, y) for y in ys for x in xs]


def snap(v, step=GRID):
    """v onto the nearest grid line."""
    return round(v / step) * step


def snap_box(box, others=(), grid=GRID, zoom=1.0, px=SNAP_PX, to_grid=True):
    """Where a box being dragged lands: (x, y) of its top-left. Its edges (left / right, top / bottom) and middle
    stick to another box's edges or middle when within px screen pixels - laid exactly over a HUD the same size, its
    corner lands on the HUD's - otherwise its corner goes onto the grid (to_grid). box = (x, y, w, h), others the same;
    returns (x, y, stuck) with stuck the boxes it stuck to (for drawing the guide lines)."""
    x, y, w, h = box
    reach = px / max(zoom, 1e-6)

    def best(pos, size, lines):
        found = None
        for mine in (0, size / 2, size):                    # its left, middle, right (or top, middle, bottom)
            for line, who in lines:
                d = line - (pos + mine)
                if abs(d) <= reach and (found is None or abs(d) < abs(found[0])):
                    found = (d, who)
        return found

    xs = [(o[0] + k, o) for o in others for k in (0, o[2] / 2, o[2])]
    ys = [(o[1] + k, o) for o in others for k in (0, o[3] / 2, o[3])]
    stuck = []
    bx, by = best(x, w, xs), best(y, h, ys)
    if bx:
        x += bx[0]
        stuck.append(bx[1])
    elif to_grid:
        x = snap(x, grid)
    if by:
        y += by[0]
        stuck.append(by[1])
    elif to_grid:
        y = snap(y, grid)
    return x, y, stuck
