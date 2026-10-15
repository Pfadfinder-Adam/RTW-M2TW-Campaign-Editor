"""What stands on the campaign map, for Maps > 3D: towns (their level's model of the owner's culture), ports, forts,
watchtowers, resources and characters (armies, agents, fleets) - each with the game's own model and texture, both
games.

Where the models are named:
- towns, forts, ports, watchtowers: Rome descr_sm_settlements.txt (culture -> level -> 'normal') and
  descr_sm_forts_ports_watchtowers.txt ('culture x' then fort / port_land / watchtower); Medieval II descr_cultures.txt
  (both in one file, a 'culture x' line before each block);
- resources: descr_sm_resources.txt ('type x' ... 'item <model>');
- characters: descr_model_strat.txt by the faction's figure of each character type (stratmodels.figures).

Each model is drawn once per view angle into a small picture (meshview.render, its origin - where it stands - in the
middle) and laid on the 3D view by terrain3d.draw_objects ('impostors': the way far trees are drawn in games)."""

import math
import re

from .textio import strip_comment

KEY = (255, 0, 255)             # the pictures' ground colour, made see-through
SPRITE = 160                    # the pictures' side in pixels
YAWS = 16                       # angles a model is drawn from (every 22.5 degrees)


def _rel(path):
    path = (path or "").split(",")[0].strip().replace("\\", "/")
    return path[5:] if path.lower().startswith("data/") else path


def culture_models(mod):
    """{culture: {'levels': {level: model}, 'fort', 'watchtower', 'port', 'fishing_village': model}} of both
    games' files (data-relative model paths)."""
    out = {}
    for name in ("descr_sm_settlements.txt", "descr_cultures.txt", "descr_sm_forts_ports_watchtowers.txt"):
        p = mod.find(name)
        if not p:
            continue
        cur, level, depth, pending = None, None, 0, None
        for line in mod.load(p).texts():
            code = strip_comment(line).strip()
            if not code:
                continue
            t = code.split(None, 1)
            word = t[0].lower()
            if code == "{":
                depth += 1
                if depth == 1 and pending and cur is None:          # Rome: 'roman' then '{'
                    cur = pending
                elif depth == 2 or (depth == 1 and cur is not None and pending and pending != cur):
                    level = pending
                pending = None
                continue
            if code == "}":
                depth -= 1
                if depth <= 0:
                    depth, level = 0, None
                    if name == "descr_sm_settlements.txt":
                        cur = None
                elif depth == 1:
                    level = None
                continue
            if word == "culture" and len(t) > 1:
                cur, level, depth = t[1].strip(), None, 0
                continue
            if len(t) == 1:
                pending = t[0]
                continue
            c = out.setdefault(cur, {"levels": {}}) if cur else None
            if c is None:
                continue
            if word == "normal" and level:
                c["levels"].setdefault(level, _rel(t[1]))
            elif word in ("fort", "watchtower", "fishing_village") and word not in c:
                c[word] = _rel(t[1])
            elif word == "port_land" and "port" not in c:
                c["port"] = _rel(t[1])
    return {k: v for k, v in out.items() if k}


def resource_models(mod):
    """{resource type: model} of descr_sm_resources.txt."""
    p = mod.find("descr_sm_resources.txt")
    out, cur = {}, None
    for line in (mod.load(p).texts() if p else []):
        t = strip_comment(line).split(None, 1)
        if len(t) < 2:
            continue
        if t[0] == "type":
            cur = t[1].strip()
        elif t[0] == "item" and cur:
            out[cur] = _rel(t[1])
    return out


def _strat_scales(mod):
    """{figure: (scale, skeleton)} of descr_model_strat.txt (its 'scale' line - 1 when none - and 'skeleton')."""
    p = mod.find("descr_model_strat.txt")
    out, cur = {}, None
    for line in (mod.load(p).texts() if p else []):
        t = strip_comment(line).replace(",", " ").split()
        if len(t) >= 2 and t[0] == "type":
            cur = t[1]
            out[cur] = [1.0, None]
        elif len(t) >= 2 and t[0] == "scale" and cur:
            try:
                out[cur][0] = float(t[1])
            except ValueError:
                pass
        elif len(t) >= 2 and t[0] == "skeleton" and cur and out[cur][1] is None:
            out[cur][1] = t[1]
    return {k: tuple(v) for k, v in out.items()}


CHAR_TYPES = {"named character": "named character", "general": "general", "admiral": "admiral", "spy": "spy",
              "assassin": "assassin", "diplomat": "diplomat", "merchant": "merchant", "priest": "priest",
              "princess": "princess", "heretic": "heretic", "witch": "witch", "inquisitor": "inquisitor"}


def objects(mod, campaign, strat):
    """[{'kind', 'model' (data-relative), 'texture' (data-relative or None), 'xy' (tile), 'scale', 'faction'}] of
    what stands on the map now (descr_strat as read)."""
    from . import stratmodels as SM
    cultures = culture_models(mod)
    first = next(iter(cultures.values()), {"levels": {}})
    out = []
    tiles = mod.city_tiles(campaign)

    def culture_of(faction):
        try:
            return cultures.get(mod.culture(faction)) or first
        except Exception:
            return first
    towns, ports = set(), None
    for fb in strat.factions:
        cm = culture_of(fb.name)
        for st in fb.settlements:
            xy = tiles.get(st.region)
            if xy is None:
                continue
            level = next((strip_comment(strat.lines[i]).split()[1] for i in range(st.start, st.end)
                          if strip_comment(strat.lines[i]).split()[:1] == ["level"]
                          and len(strip_comment(strat.lines[i]).split()) > 1), "town")
            model = cm["levels"].get(level) or next(iter(cm["levels"].values()), None)
            if model:
                out.append({"kind": "town", "model": model, "texture": None, "xy": tuple(xy), "scale": 1.0,
                            "faction": fb.name})
                towns.add(tuple(xy))
        if ports is None:
            try:
                from .mapedit import ports as _ports     # the one reader of port pixels
                ports = dict(_ports(mod, campaign))
            except Exception:
                ports = {}
        for st in fb.settlements:                         # its port, on the coast beside the town
            pxy = ports.get(st.region)
            if pxy and cm.get("port"):
                out.append({"kind": "port", "model": cm["port"], "texture": None, "xy": tuple(pxy), "scale": 1.0,
                            "faction": fb.name})
        for fo in [f for f in strat.forts if getattr(f, "owner", None) == fb.name]:
            kind = "watchtower" if fo.kind == "watchtower" else "fort"
            model = cm.get(kind)
            if model and fo.kind != "landmark":
                out.append({"kind": kind, "model": model, "texture": None, "xy": tuple(fo.xy), "scale": 1.0,
                            "faction": fb.name})
    # resources (their lines in descr_strat: 'resource gold, 83, 128')
    res = resource_models(mod)
    for line in strat.lines:
        m = re.match(r"\s*resource\s+([\w\-]+)\s*,\s*(\d+)\s*,\s*(\d+)", strip_comment(line))
        if m and res.get(m.group(1)):
            out.append({"kind": "resource", "model": res[m.group(1)], "texture": None,
                        "xy": (int(m.group(2)), int(m.group(3))), "scale": 1.0, "faction": None})
    # characters: the faction's figure of their type, in its texture
    scales = _strat_scales(mod)
    for fb in strat.factions:
        try:
            figs = {f["type"]: f["models"] for f in SM.figures(mod, fb.name)}
        except Exception:
            figs = {}
        for c in fb.characters:
            if not c.xy or tuple(c.xy) in towns:
                continue
            lines = strat.lines[c.start:c.end]
            kind = "named character" if c.kind == "named character" else (c.kind or "general")
            if any(strip_comment(x).split()[:1] == ["unit"] for x in lines) and kind not in figs:
                kind = "general"
            names = figs.get(CHAR_TYPES.get(kind, kind)) or figs.get("general") or []
            info = SM.mesh_info(mod, names[0]) if names else None
            if info is None or not info.meshes:
                continue
            tex = info.textures.get(fb.name) or info.textures.get("") or next(iter(info.textures.values()), None)
            sc, skel = scales.get(names[0], (1.0, None))
            out.append({"kind": "character", "model": info.meshes[0], "texture": tex, "xy": tuple(c.xy),
                        "scale": sc, "skeleton": skel, "faction": fb.name})
    return out


class Sprites:
    """The models drawn into small see-through pictures, kept: one per (model, texture, angle)."""

    def __init__(self, mod):
        self.mod = mod
        self.meshes, self.textures, self.pics = {}, {}, {}

    def _mesh(self, rel, skeleton=None):
        """The model, a figure standing as in the game: its skeleton's standing move from the game's animation
        packs (the file itself holds the arms-out pose); a building as the file has it."""
        key = (rel, skeleton)
        if key not in self.meshes:
            from . import meshview as MV
            path = MV.mesh_path(self.mod, rel)
            mesh = None
            if path and skeleton and path.lower().endswith(".cas"):
                try:
                    from . import animations as AN
                    moves = {w.lower(): f for w, f in AN.of_skeleton(self.mod, skeleton)}
                    f = moves.get("stand_a_idle") or moves.get("stand") or moves.get("idle") or next(
                        (v for k, v in moves.items() if "stand" in k or "idle" in k), None)
                    anim = AN.find(self.mod, f) if f else None
                    if anim is not None:
                        mesh = MV.read_posed(path, MV.Pose.of(anim, 0))
                except Exception:
                    mesh = None
            if mesh is None and path:
                try:
                    mesh = MV.read_file(path, "frame")
                except Exception:
                    mesh = None
            self.meshes[key] = mesh
        return self.meshes[key]

    def _texture(self, rel):
        if rel not in self.textures:
            from . import models as MO
            try:
                self.textures[rel] = MO.texture_image(self.mod, rel) if rel else None
            except Exception:
                self.textures[rel] = None
        return self.textures[rel]

    def _own_texture(self, model, mesh):
        """The texture a .cas names itself: as written, else beside the model (its folder's textures/ - a
        residence names 'textures\\set_rome_village.tga' meaning models_strat/residences/textures)."""
        ref = getattr(mesh, "texture_ref", None) or ""
        name = ref.replace("\\", "/").rsplit("/", 1)[-1]
        if not name:
            return None
        folder = model.replace("\\", "/").rsplit("/", 1)[0] if "/" in model else ""
        for rel in (ref, folder + "/textures/" + name, folder + "/" + name):
            got = self._texture(rel)
            if got is not None:
                return got
        return None

    def get(self, model, texture, yaw_deg, pitch_deg, skeleton=None, cached_only=False):
        """(RGBA array (S, S, 4), radius in model units) - the model from that side and height, its standing point
        in the middle; None when the model cannot be read."""
        yb = int(round(yaw_deg / (360.0 / YAWS))) % YAWS
        pb = int(max(10, min(80, round(pitch_deg / 10.0) * 10)))
        key = (model, texture, yb, pb, skeleton)
        if key in self.pics:
            return self.pics[key]
        if cached_only:                          # while the mouse moves: a near angle already drawn, else nothing
            near = [v for (m, t, _, _, sk), v in self.pics.items() if (m, t, sk) == (model, texture, skeleton) and v]
            return near[0] if near else None
        import numpy as np
        from . import meshview as MV
        mesh = self._mesh(model, skeleton)
        got = None
        if mesh is not None and len(mesh.positions):
            P = np.asarray(mesh.positions, dtype=np.float64)
            radius = float(np.sqrt((P ** 2).sum(axis=1)).max()) or 1.0
            tex = self._texture(texture) or self._own_texture(model, mesh)
            try:
                img = MV.render(mesh, size=(SPRITE, SPRITE), yaw=yb * 360.0 / YAWS, pitch=pb, texture=tex,
                                quality=1, background=KEY, frame=((0.0, 0.0, 0.0), radius))
                a = np.asarray(img.convert("RGB"), dtype=np.uint8)
                alpha = np.where(np.all(a == np.array(KEY, np.uint8), axis=2), 0, 255).astype(np.uint8)
                got = (np.dstack([a, alpha]), radius)
            except Exception:
                got = None
        self.pics[key] = got
        return got


def place(cmap, tile, campaign_h):
    """The colour map's pixel (x, y) of a tile's middle (tiles count from the bottom, the map from the top)."""
    k = cmap.k
    return (2 * tile[0] + 1) * k + k / 2.0, (campaign_h - 1 - (2 * tile[1] + 1)) * k + k / 2.0


def draw_objects(img, depth, cmap, cam, objs, sprites, W, H, heights_rows=None, cached_only=False):
    """Each object's picture laid on the view img (H, W, 3) where nothing nearer covers it (depth: the view's
    depth per pixel, terrain3d.render with_depth), far ones first - in the same tilted view as the ground
    (terrain3d.project). -> how many were drawn."""
    import numpy as np
    from PIL import Image
    from . import terrain3d as T3
    s, c = math.sin(cam.yaw), math.cos(cam.yaw)
    bh, bw = cmap.height.shape
    hrows = heights_rows or (bh // cmap.k)
    hscale = (cmap.k * 6.0) / max(1.0, cmap.top) * cam.exaggerate
    here = cmap.height[int(np.clip(cam.y, 0, bh - 1)), int(np.clip(cam.x, 0, bw - 1))] * hscale
    eye = here + cam.alt
    fl = T3.focal(W)
    unit = 2.0 * cmap.k                           # a model unit = a tile = two heights points
    todo = []
    for o in objs:
        x, y = place(cmap, o["xy"], hrows)
        dx, dy = x - cam.x, y - cam.y
        f = dx * s - dy * c                      # along the view
        r = dx * c + dy * s                      # to the right
        if f < 1 or f > cam.far:
            continue
        gh = cmap.height[int(np.clip(y, 0, bh - 1)), int(np.clip(x, 0, bw - 1))] * hscale
        d, sy = T3.project(f, gh - eye, cam, W, H)
        if d < 1:
            continue
        sx = W / 2.0 + r / d * fl
        todo.append((d, sx, float(sy), o, math.degrees(math.atan2(eye - gh, f))))
    drawn = 0
    yaw = (math.degrees(cam.yaw) + 180.0) % 360.0
    for d, sx, sy, o, pitch in sorted(todo, key=lambda t: -t[0]):
        got = sprites.get(o["model"], o.get("texture"), yaw, pitch, o.get("skeleton"), cached_only=cached_only)
        if got is None:
            continue
        pic, radius = got
        n = int(2.0 * radius * o.get("scale", 1.0) * unit * fl / d / 0.95)
        if n < 3 or n > 2400:
            continue
        x0, y0 = int(sx - n / 2.0), int(sy - n / 2.0)
        if x0 >= W or y0 >= H or x0 + n <= 0 or y0 + n <= 0:
            continue
        p = np.asarray(Image.fromarray(pic).resize((n, n), Image.BILINEAR if n < pic.shape[0] else Image.NEAREST))
        a0, b0 = max(0, -y0), max(0, -x0)
        a1, b1 = min(n, H - y0), min(n, W - x0)
        part = p[a0:a1, b0:b1]
        zone = depth[y0 + a0:y0 + a1, x0 + b0:x0 + b1]
        show = (part[..., 3] > 128) & (zone > d - 1.5 * cmap.k)
        tgt = img[y0 + a0:y0 + a1, x0 + b0:x0 + b1]
        tgt[show] = part[..., :3][show]
        drawn += 1
    return drawn


__all__ = ["objects", "Sprites", "draw_objects", "culture_models", "resource_models"]
