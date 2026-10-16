"""The campaign map drawn by the graphics card (OpenGL through moderngl) the way the games draw it - Maps > 3D, both
games. What the games do (read in the engine's source, facts only - editor-notes strat_map_render.md):

- the ground is one grid of points, map_heights.tga's own size (2 W + 1 x 2 H + 1 for W x H tiles): a tile is
  1 x 1, a point every half tile, each half-tile square split along its south-west -> north-east diagonal; a point
  stands h * 0.0005 * (1.2 Medieval II, 0.6 Rome) high, the sea level at 0;
- each point names a ground picture (its climate on map_climates.tga and ground on map_ground_types.tga, through
  descr_aerial_map_ground_types.txt); a half-tile square blends the pictures of its four corners with the game's
  painted masks (terrain/aerial_map/template_weights/weights*.tga - each corner one of them at random, mirrored to
  its corner), so the borders between grounds are soft and ragged, never a straight cross-fade;
- the pictures lie fixed on the world: a picture N pixels wide repeats every N / (64 x texture_density) tiles;
- the light (descr_strategy_lighting.txt): colour = picture x min(ambient + diffuse x (normal . sun), 1), per point;
- the sea is a flat sheet at height 0 under everything - land below 0 hides under it, so the coast is where the
  ground crosses 0: water_surface.tga stretched over the whole map, with the waves and the sky's reflection.

Everything lives on the card as pictures (the heights, the ground picture of each point): a brush stroke changes
a few of their pixels, the next frame shows it. The frame is drawn off the screen and handed to the window as a
picture (the same way on every system - no window of its own to fit into Tk). Without moderngl or a card that
gives OpenGL 3.3, available() says why and Maps > 3D draws as before (terrain3d)."""

import math

import numpy as np

from . import terrain3d as T3

SCALE = {"medieval2": 1.2, "rome": 0.6}         # the games' height scale (aerial_map.h)
SEGMENT_TEXELS = 64                             # a picture's pixels a tile covers at texture_density 1
LAYER = 512                                     # every ground picture is made this size on the card
SEA_LIGHT = (0.5, 1.0, 1.0)                     # the way to the sea's own light (the engine's (-0.5, -1, -1) reversed)

_ctx = None
_why = None


def context():
    """The one OpenGL context of the editor (made the first time), or None - available() says why."""
    global _ctx, _why
    if _ctx is not None or _why is not None:
        return _ctx
    try:
        import moderngl
    except ImportError:
        _why = "moderngl is not installed (the editor's exe has it)"
        return None
    errors = []
    for backend in (None, "egl"):                # the system's own way first; EGL where there is no display
        try:
            ctx = moderngl.create_standalone_context(**({"backend": backend} if backend else {}))
            if ctx.version_code < 330:
                errors.append("OpenGL %s - 3.3 is needed" % ctx.info.get("GL_VERSION", ctx.version_code))
                ctx.release()
                continue
            _ctx = ctx
            return ctx
        except Exception as e:                   # each way said why it could not
            errors.append(str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__)
    _why = "no OpenGL 3.3 from the graphics card (%s)" % "; ".join(errors)
    return None


def available():
    """(True, '') when the card draws the map, else (False, why in plain words)."""
    return (context() is not None, _why or "")


def lighting(mod):
    """{ambient, diffuse, direction} of descr_strategy_lighting.txt (the mod's, else the game's), the games' own
    values where a line is missing."""
    from .textio import strip_comment
    m2 = _kind(mod) == "medieval2"
    out = {"ambient": (0.5, 0.5, 0.52) if m2 else (0.3, 0.3, 0.5),
           "diffuse": (0.7, 0.7, 0.72) if m2 else (1.1, 1.1, 0.85),
           "direction": (-1.0, -1.0, 1.0)}
    p = mod.find("descr_strategy_lighting.txt")
    if p:
        for line in mod.load(p).texts():
            t = strip_comment(line).split()
            key = {"ambient_colour": "ambient", "diffuse_colour": "diffuse", "diffuse_direction": "direction"}.get(
                t[0] if t else "")
            if key and len(t) >= 4:
                try:
                    out[key] = tuple(float(v) for v in t[1:4])
                except ValueError:
                    pass
    return out


def _kind(mod):
    from .limits import game_kind
    return game_kind(mod)


def _image(mod, rels, size=None, mode="RGB"):
    """A picture of the mod (else the game) as an array (h, w, channels), resized to size when given; None
    without one. rels: the paths under data/ to try, each also with '.dds' after it."""
    from PIL import Image
    for rel in rels:
        for name in (rel, rel + ".dds"):
            p = mod.find(name)
            if not p:
                continue
            try:
                with Image.open(p) as im:
                    im = im.convert(mode)
                    if size:
                        im = im.resize((size, size), Image.BILINEAR)
                    return np.asarray(im, dtype=np.uint8)
            except Exception:
                continue
    return None


def _image_size(mod, rel):
    from PIL import Image
    for name in (rel, rel + ".dds"):
        p = mod.find(name)
        if p:
            try:
                with Image.open(p) as im:
                    return im.size[0]
            except Exception:
                return None
    return None


class MapData:
    """What the card needs of a campaign map, as arrays (the slow part, no OpenGL - made once, also in a thread):
    heights (metres, top row first), the ground picture of each point (an index into pictures), the pictures, the
    masks, the sea's pictures, the light."""

    def __init__(self, mod, campaign, winter=False):
        h = T3.heights_metres(mod, campaign)
        if h is None:
            raise ValueError("this campaign has no map_heights.tga - nothing to raise in 3D")
        self.heights = h.astype(np.float32)
        self.rows, self.cols = h.shape
        self.kind = _kind(mod)
        self.scale = SCALE.get(self.kind, 0.6)
        self.notes = []
        self.layers, self.pictures, self.repeat = self._ground(mod, campaign, winter)
        self.masks = self._masks(mod)
        self.water = _image(mod, ["world/maps/campaign/%s/water_surface.tga" % campaign,
                                  "world/maps/base/water_surface.tga"])
        self.waves = _image(mod, ["terrain/aerial_map/sea/waves.tga"], mode="RGBA")
        self.sky = _image(mod, ["terrain/aerial_map/sea/sky_environment_summer.tga"])
        self.light = lighting(mod)

    def _ground(self, mod, campaign, winter):
        """(layer of each point (rows, cols) uint16, [pictures (LAYER, LAYER, 3)], [repeats a tile per layer])."""
        sets, density = T3.aerial_sets(mod)
        names = list(sets) or ["default"]
        keys = sorted(set(T3.GROUND_KEYS.values()) | {"beach"})
        ground = T3._picture(mod, campaign, "map_ground_types.tga")
        climate = T3._picture(mod, campaign, "map_climates.tga")
        shape = (self.rows, self.cols)
        gi = T3._ground_index(ground, keys) if ground is not None and ground.shape[:2] == shape else \
            np.full(shape, keys.index("fertility_low"), np.int32)
        ci = T3._climate_index(mod, climate, names) if climate is not None and climate.shape[:2] == shape else \
            np.zeros(shape, np.int32)
        sea = self.heights <= 0
        # the games' own fix at loading: a land point with a sea colour is low fertility, a sea point is beach
        gi = np.where(gi < 0, keys.index("fertility_low"), gi)
        gi = np.where(sea, keys.index("beach"), gi)
        files, pictures, repeat, missing = {}, [], [], set()
        table = np.zeros((len(names), len(keys)), np.int32)
        for c, cname in enumerate(names):
            for g, key in enumerate(keys):
                entry = sets.get(cname, {}).get(key) or sets.get("default", {}).get(key)
                if entry is None and T3.FALLBACK.get(key):
                    entry = sets.get(cname, {}).get(T3.FALLBACK[key]) or sets.get("default", {}).get(T3.FALLBACK[key])
                fname = (entry[1] if winter and entry[1] else entry[0]) if entry else None
                tag = fname.lower() if fname else "plain:" + key
                if tag not in files:
                    arr, n = None, None
                    if fname:
                        rel = "terrain/aerial_map/ground_types/" + fname
                        arr = _image(mod, [rel], LAYER)
                        n = _image_size(mod, rel)
                        if arr is None:
                            missing.add(fname)
                    if arr is None:              # the ground's plain colour where the picture is missing
                        arr = np.empty((LAYER, LAYER, 3), np.uint8)
                        arr[:] = T3.PLAIN.get(key, (120, 120, 90))
                    files[tag] = len(pictures)
                    pictures.append(arr)
                    repeat.append(SEGMENT_TEXELS * density / float(n or LAYER))
                table[c, g] = files[tag]
        if missing:
            self.notes.append("%d ground picture(s) not found - their ground's plain colour shown: %s" % (
                len(missing), ", ".join(sorted(missing)[:4]) + (" ..." if len(missing) > 4 else "")))
        if not sets:
            self.notes.append("no descr_aerial_map_ground_types.txt - the grounds' plain colours shown")
        return table[ci, gi].astype(np.uint16), pictures, repeat

    def _masks(self, mod):
        """The game's blend masks (template_weights/weights*.tga, their red), all made one size; a plain fade from
        the corner when the mod has none."""
        from PIL import Image
        out = []
        for i in range(1, 33):
            a = _image(mod, ["terrain/aerial_map/template_weights/weights%d.tga" % i])
            if a is None:
                break
            out.append(np.asarray(Image.fromarray(a[..., 0]).resize((32, 32), Image.BILINEAR), np.uint8))
        if not out:
            y, x = np.mgrid[0:32, 0:32] / 31.0
            out.append((np.clip(1 - (x + y) / 2.0, 0, 1) * 255).astype(np.uint8))
            self.notes.append("no template_weights - the grounds blend in a plain fade")
        return out

    def tiles(self):
        """The map's size in tiles (across, up)."""
        return (self.cols - 1) / 2.0, (self.rows - 1) / 2.0

    def ground_height(self, x, z):
        """The ground's height (world units) at tile point (x east, z south - from the map's top), 0 on the sea."""
        c = int(round(min(max(x * 2, 0), self.cols - 1)))
        r = int(round(min(max(z * 2, 0), self.rows - 1)))
        return max(0.0, float(self.heights[r, c])) * 0.0005 * self.scale


TERRAIN_VS = """
#version 330
uniform sampler2D heights;
uniform mat4 mvp;
uniform float yscale;
uniform ivec2 size;
uniform vec3 to_light;
uniform vec3 ambient;
uniform vec3 diffuse;
in vec2 grid;
out vec2 g;
out vec3 light;
float h(ivec2 p) { return texelFetch(heights, clamp(p, ivec2(0), size - 1), 0).r * yscale; }
void main() {
    ivec2 p = ivec2(grid);
    float y = h(p);
    vec3 n = normalize(vec3(-(h(p + ivec2(1, 0)) - h(p - ivec2(1, 0))) * 0.5, 0.5,
                            -(h(p + ivec2(0, 1)) - h(p - ivec2(0, 1))) * 0.5));
    light = min(ambient + diffuse * max(dot(n, to_light), 0.0), vec3(1.0));
    g = grid;
    gl_Position = mvp * vec4(grid.x * 0.5, y, grid.y * 0.5, 1.0);
}
"""

TERRAIN_FS = """
#version 330
uniform usampler2D layers;
uniform sampler2DArray ground;
uniform sampler2DArray masks;
uniform int nmasks;
uniform ivec2 size;
uniform float rep[64];
in vec2 g;
in vec3 light;
out vec4 colour;
uint mix3(uint a, uint b, uint c) {
    uint x = a * 73856093u ^ b * 19349663u ^ c * 83492791u;
    x ^= x >> 13; x *= 0x5bd1e995u; x ^= x >> 15;
    return x;
}
vec3 pic(uint l, vec2 t) { return texture(ground, vec3(t * rep[l], float(l))).rgb; }
void main() {
    ivec2 c = clamp(ivec2(floor(g)), ivec2(0), size - 2);
    vec2 f = clamp(g - vec2(c), 0.0, 1.0);
    uint l0 = texelFetch(layers, c, 0).r;
    uint l1 = texelFetch(layers, c + ivec2(1, 0), 0).r;
    uint l2 = texelFetch(layers, c + ivec2(0, 1), 0).r;
    uint l3 = texelFetch(layers, c + ivec2(1, 1), 0).r;
    vec2 t = g * 0.5;
    vec3 col;
    if (l0 == l1 && l0 == l2 && l0 == l3) {
        col = pic(l0, t);
    } else {
        uint v = mix3(uint(c.x), uint(c.y), 7u) % 8u;
        float k = 31.0 / 32.0, o = 0.5 / 32.0;
        float w0 = texture(masks, vec3(f * k + o, float(mix3(uint(c.x), uint(c.y), v * 4u) % uint(nmasks)))).r;
        float w1 = texture(masks, vec3(vec2(1.0 - f.x, f.y) * k + o,
                                       float(mix3(uint(c.x), uint(c.y), v * 4u + 1u) % uint(nmasks)))).r;
        float w2 = texture(masks, vec3(vec2(f.x, 1.0 - f.y) * k + o,
                                       float(mix3(uint(c.x), uint(c.y), v * 4u + 2u) % uint(nmasks)))).r;
        float w3 = texture(masks, vec3((1.0 - f) * k + o,
                                       float(mix3(uint(c.x), uint(c.y), v * 4u + 3u) % uint(nmasks)))).r;
        float sum = max(w0 + w1 + w2 + w3, 1e-4);
        col = (pic(l0, t) * w0 + pic(l1, t) * w1 + pic(l2, t) * w2 + pic(l3, t) * w3) / sum;
    }
    colour = vec4(col * light, 1.0);
}
"""

SEA_VS = """
#version 330
uniform mat4 mvp;
in vec2 pos;
out vec2 w;
void main() { w = pos; gl_Position = mvp * vec4(pos.x, 0.0, pos.y, 1.0); }
"""

SEA_FS = """
#version 330
uniform sampler2D water;
uniform sampler2D waves;
uniform sampler2D sky;
uniform vec2 tiles;
uniform vec3 sea_light;
uniform vec3 eye;
uniform float waves_mean;
out vec4 colour;
in vec2 w;
void main() {
    vec2 uv = w / tiles;
    vec3 c = texture(water, uv).rgb * sea_light;
    c *= texture(waves, w * 0.25).r / max(waves_mean, 0.05);      // the waves around their own mean
    vec2 r = (w + (eye.xz - w) * 0.15) / 32.0;
    c = mix(c, texture(sky, r).rgb, 0.5);
    colour = vec4(c, 1.0);
}
"""


def look_at(eye, target, up=(0.0, 1.0, 0.0)):
    eye, target, up = (np.asarray(v, np.float64) for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= max(np.linalg.norm(s), 1e-9)
    u = np.cross(s, f)
    m = np.identity(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1.0
    return m


class Camera:
    """The game's camera: it looks at a point of the map (x east, z south - tiles from the map's top-left corner)
    from dist tiles away, turned yaw (0 = looking north) and tilted down pitch (radians; the game's default 53
    degrees), 45 degrees of view. (x east, y up, z south: OpenGL's right-handed world.)"""
    FOV = 45.0

    def __init__(self, data):
        cols, rows = data.tiles()
        self.x, self.z = cols / 2.0, rows / 2.0
        self.yaw = 0.0
        self.pitch = math.radians(53.13)
        self.far_limit = max(cols, rows) * 1.6
        self.dist = self.far_limit * 0.6

    def eye(self, ground=0.0):
        cp = math.cos(self.pitch)
        return (self.x - math.sin(self.yaw) * cp * self.dist, ground + math.sin(self.pitch) * self.dist,
                self.z + math.cos(self.yaw) * cp * self.dist)

    def moved(self, forward, right):
        """forward: tiles the way the camera looks (along the ground), right: to its right."""
        s, c = math.sin(self.yaw), math.cos(self.yaw)
        self.x += forward * s + right * c
        self.z += -forward * c + right * s

    def zoom(self, factor):
        self.dist = min(self.far_limit, max(1.5, self.dist * factor))

    def matrix(self, w, h, ground=0.0):
        eye = self.eye(ground)
        view = look_at(eye, (self.x, ground, self.z))
        proj = perspective(self.FOV, w / float(max(h, 1)), max(0.05, self.dist * 0.01), self.dist * 4 + 50)
        return (proj @ view).astype(np.float32), eye


class GLMap:
    """The map on the card: made from MapData, then render(camera, w, h) -> (h, w, 3) uint8 picture as many times
    as the view moves. set_heights / set_layers change part of what the card holds (the brushes, live)."""

    def __init__(self, data):
        ctx = context()
        if ctx is None:
            raise RuntimeError(_why or "no OpenGL")
        self.ctx, self.data = ctx, data
        self._gone = []
        rows, cols = data.rows, data.cols
        self.heights = self._keep(ctx.texture((cols, rows), 1, data.heights.tobytes(), dtype="f4"))
        self.heights.filter = (ctx.NEAREST, ctx.NEAREST)
        self.layers = self._keep(ctx.texture((cols, rows), 1, data.layers.tobytes(), dtype="u2"))
        self.layers.filter = (ctx.NEAREST, ctx.NEAREST)          # whole numbers: never blended
        n = len(data.pictures)
        self.ground = self._keep(ctx.texture_array((LAYER, LAYER, n), 3, np.stack(data.pictures).tobytes()))
        self.ground.build_mipmaps()
        self.ground.filter = (ctx.LINEAR_MIPMAP_LINEAR, ctx.LINEAR)
        self.ground.repeat_x = self.ground.repeat_y = True
        try:
            self.ground.anisotropy = 8.0
        except Exception:
            pass
        self.masks = self._keep(ctx.texture_array((32, 32, len(data.masks)), 1, np.stack(data.masks).tobytes()))
        self.masks.repeat_x = self.masks.repeat_y = False
        self.water = self._picture(data.water, 3, (40, 70, 110))
        self.waves = self._picture(data.waves, 4, (128, 128, 128, 255), repeat=True)
        self.sky = self._picture(data.sky, 3, (150, 170, 190), repeat=True)
        self.terrain = self._keep(ctx.program(vertex_shader=TERRAIN_VS, fragment_shader=TERRAIN_FS))
        self.sea = self._keep(ctx.program(vertex_shader=SEA_VS, fragment_shader=SEA_FS))
        # the grid: one point per heights pixel, two triangles a half-tile square along its SW -> NE diagonal
        gy, gx = np.mgrid[0:rows, 0:cols].astype(np.float32)
        pts = np.stack([gx.ravel(), gy.ravel()], 1)
        i = np.arange(rows * cols, dtype=np.uint32).reshape(rows, cols)
        tl, tr, bl, br = i[:-1, :-1], i[:-1, 1:], i[1:, :-1], i[1:, 1:]
        tri = np.stack([tl, bl, tr, tr, bl, br], -1).ravel().astype(np.uint32)
        vbo = self._keep(ctx.buffer(pts.tobytes()))
        ibo = self._keep(ctx.buffer(tri.tobytes()))
        self.vao = self._keep(ctx.vertex_array(self.terrain, [(vbo, "2f", "grid")], ibo, index_element_size=4))
        tc, tr_ = data.tiles()
        quad = np.array([[0, 0], [tc, 0], [0, tr_], [tc, tr_]], np.float32)
        qbo = self._keep(ctx.buffer(quad.tobytes()))
        self.sea_vao = self._keep(ctx.vertex_array(self.sea, [(qbo, "2f", "pos")]))
        self.fbo, self.fbo_size = None, None
        L = data.light
        d = np.asarray(L["direction"], np.float64) * (1.0, 1.0, -1.0)    # the game's z runs north, ours south
        to_light = -d / max(np.linalg.norm(d), 1e-9)
        s = np.asarray(SEA_LIGHT, np.float64)
        s /= np.linalg.norm(s)
        sea_l = np.minimum(np.asarray(L["ambient"]) + np.asarray(L["diffuse"]) * max(float(s[1]), 0.0), 1.0)
        for name, value in (("to_light", tuple(to_light)), ("ambient", L["ambient"]), ("diffuse", L["diffuse"]),
                            ("size", (cols, rows))):
            self.terrain[name].value = value
        self.terrain["rep"].value = tuple(data.repeat[:64]) + (1.0,) * (64 - min(64, len(data.repeat)))
        self.terrain["nmasks"].value = len(data.masks)
        for name, unit in (("heights", 0), ("layers", 1), ("ground", 2), ("masks", 3)):
            if name in self.terrain:
                self.terrain[name].value = unit
        self.sea["tiles"].value = (tc, tr_)
        self.sea["sea_light"].value = tuple(float(v) for v in sea_l)
        self.sea["waves_mean"].value = float(data.waves[..., 0].mean()) / 255.0 if data.waves is not None else 0.5
        for name, unit in (("water", 4), ("waves", 5), ("sky", 6)):
            self.sea[name].value = unit

    def _keep(self, obj):
        self._gone.append(obj)
        return obj

    def _picture(self, arr, comps, plain, repeat=False):
        if arr is None:
            arr = np.empty((4, 4, comps), np.uint8)
            arr[:] = plain
        t = self._keep(self.ctx.texture((arr.shape[1], arr.shape[0]), comps, np.ascontiguousarray(arr).tobytes()))
        t.build_mipmaps()
        t.filter = (self.ctx.LINEAR_MIPMAP_LINEAR, self.ctx.LINEAR)
        t.repeat_x = t.repeat_y = repeat
        return t

    def set_heights(self, row, col, block):
        """Heights (metres) of a block of points from (row, col) - top row first - changed on the card."""
        block = np.asarray(block, np.float32)
        self.data.heights[row:row + block.shape[0], col:col + block.shape[1]] = block
        self.heights.write(np.ascontiguousarray(block).tobytes(),
                           viewport=(col, row, block.shape[1], block.shape[0]))

    def set_layers(self, row, col, block):
        """The ground picture (layer) of a block of points from (row, col) changed on the card."""
        block = np.asarray(block, np.uint16)
        self.data.layers[row:row + block.shape[0], col:col + block.shape[1]] = block
        self.layers.write(np.ascontiguousarray(block).tobytes(),
                          viewport=(col, row, block.shape[1], block.shape[0]))

    def render(self, cam, w, h):
        """The map seen from cam as a (h, w, 3) uint8 picture, top row first."""
        ctx = self.ctx
        w, h = max(16, int(w)), max(16, int(h))
        if self.fbo_size != (w, h):
            if self.fbo is not None:
                self.fbo.release()
            self.fbo = ctx.simple_framebuffer((w, h))
            self.fbo_size = (w, h)
        self.fbo.use()
        ctx.viewport = (0, 0, w, h)
        ctx.clear(0.0, 0.0, 0.0, 1.0, depth=1.0)
        ctx.enable(ctx.DEPTH_TEST)
        ground = self.data.ground_height(cam.x, cam.z)
        mvp, eye = cam.matrix(w, h, ground)
        mvp_bytes = np.ascontiguousarray(mvp.T).tobytes()        # column-major, as OpenGL reads it
        self.water.use(4)
        self.waves.use(5)
        self.sky.use(6)
        self.sea["mvp"].write(mvp_bytes)
        if "eye" in self.sea:
            self.sea["eye"].value = tuple(float(v) for v in eye)
        self.sea_vao.render(ctx.TRIANGLE_STRIP)
        self.heights.use(0)
        self.layers.use(1)
        self.ground.use(2)
        self.masks.use(3)
        self.terrain["mvp"].write(mvp_bytes)
        self.terrain["yscale"].value = 0.0005 * self.data.scale
        self.vao.render()
        raw = self.fbo.read(components=3)
        return np.frombuffer(raw, np.uint8).reshape(h, w, 3)[::-1]

    def release(self):
        for obj in reversed(self._gone + ([self.fbo] if self.fbo is not None else [])):
            try:
                obj.release()
            except Exception:
                pass
        self._gone, self.fbo = [], None


__all__ = ["available", "context", "MapData", "GLMap", "Camera", "lighting"]
