"""What stands on the campaign map, for Maps > 3D: towns (their level's model of the owner's culture), ports, forts,
watchtowers, resources and characters (armies, agents, fleets) - each with the game's own model and texture, both
games.

Where the models are named:
- towns, forts, ports, watchtowers: Rome descr_sm_settlements.txt (culture -> level -> 'normal') and
  descr_sm_forts_ports_watchtowers.txt ('culture x' then fort / port_land / watchtower); Medieval II descr_cultures.txt
  (both in one file, a 'culture x' line before each block);
- resources: descr_sm_resources.txt ('type x' ... 'item <model>');
- characters: descr_model_strat.txt by the faction's figure of each character type (stratmodels.figures).

The graphics card's 3D map (glmap) draws these with the game's own models in a later step; the small pictures laid on
the older view were taken out with it (the user, 2026-10-16)."""

import re

from .textio import strip_comment

# what stands on the map with no model the 3D map can draw: mapmodels draws a red question mark for it
MISSING = "ce:missing"



def _rel(path):
    """The model of a line's value: its first word (#335: Barbarian Invasion's descr_cultures names the aerial base
    after the model - 'roman_port_01_land.CAS   port_roman_level_2' - taken as one file name, the port not found)."""
    words = (path or "").split(",")[0].split()
    path = (words[0] if words else "").replace("\\", "/")
    return path[5:] if path.lower().startswith("data/") else path


def culture_models(mod):
    """{culture: {'levels': {level: model}, 'fort', 'watchtower', 'port', 'fishing_village': model}} of both
    games' files (data-relative model paths)."""
    out = {}
    for name in ("descr_sm_settlements.txt", "descr_cultures.txt", "descr_sm_forts_ports_watchtowers.txt"):
        p = mod.find_any(name)
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
            elif word == "wall" and level:                     # Rome: one per wall level (wall_1, wall_2 ...)
                c.setdefault("walls", {}).setdefault(level, []).append(_rel(t[1]))
            elif word in ("fort", "watchtower", "fishing_village") and word not in c:
                c[word] = _rel(t[1])
            elif word == "port_land" and "port" not in c:
                c["port"] = _rel(t[1])
            elif word == "port_sea" and "port_sea" not in c:       # a port is two models: the quay and its ships
                c["port_sea"] = _rel(t[1])
    return {k: v for k, v in out.items() if k}


def resource_models(mod):
    """{resource type: model} of descr_sm_resources.txt."""
    p = mod.find_any("descr_sm_resources.txt")
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
    p = mod.find_any("descr_model_strat.txt")
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


def _defence_levels(mod):
    """[level names] of the walls' building chain (export_descr_buildings.txt 'building defenses' - its 'levels'
    line, in order: Rome wooden_pallisade wooden_wall stone_wall ...)."""
    p = mod.file("edb") if hasattr(mod, "file") else None
    try:
        lines = mod.load(p).texts() if p else []
    except (OSError, ValueError):
        lines = []
    inside = False
    for line in lines:
        t = strip_comment(line).split()
        if t[:2] == ["building", "defenses"]:
            inside = True
        elif inside and t[:1] == ["levels"]:
            return t[1:]
        elif inside and t[:1] == ["building"]:
            break
    return []


def _wall_level(block, levels):
    """1-based level of the walls a settlement block has built (its 'type defenses <level>' line), else 0."""
    for line in block:
        t = strip_comment(line).split()
        if t[:2] == ["type", "defenses"] and len(t) > 2:
            return levels.index(t[2]) + 1 if t[2] in levels else 1
    return 0


CHAR_TYPES = {"named character": "named character", "general": "general", "admiral": "admiral", "spy": "spy",
              "assassin": "assassin", "diplomat": "diplomat", "merchant": "merchant", "priest": "priest",
              "princess": "princess", "heretic": "heretic", "witch": "witch", "inquisitor": "inquisitor"}


def objects(mod, campaign, strat, moved=None):
    """[{'kind', 'model' (data-relative), 'texture' (data-relative or None), 'xy' (tile), 'scale', 'faction'}] of
    what stands on the map now (descr_strat as read); moved: {('city' | 'port', region): tile} - towns and ports the
    Map moved and not written yet (map_regions.tga changes only at Apply)."""
    moved = moved or {}
    from . import stratmodels as SM
    cultures = culture_models(mod)
    first = next(iter(cultures.values()), {"levels": {}})
    out = []
    tiles = dict(mod.city_tiles(campaign))
    tiles.update({r: tuple(xy) for (w, r), xy in moved.items() if w == "city"})

    def culture_of(faction):
        try:
            return cultures.get(mod.culture(faction)) or first
        except Exception:
            return first
    towns, ports = set(), None
    wall_levels = _defence_levels(mod)
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
            walls = (cm.get("walls") or {}).get(level) or []
            n = _wall_level(strat.lines[st.start:st.end], wall_levels)
            if walls and n:                                    # its walls: the defences built there
                out.append({"kind": "wall", "model": walls[min(n, len(walls)) - 1], "texture": None,
                            "xy": tuple(xy), "scale": 1.0, "faction": fb.name})
        if ports is None:
            try:
                from .mapedit import ports as _ports     # the one reader of port pixels
                ports = dict(_ports(mod, campaign))
                ports.update({r: tuple(xy) for (w, r), xy in moved.items() if w == "port"})
            except Exception:
                ports = {}
        for st in fb.settlements:                         # its port, on the coast beside the town
            pxy = ports.get(st.region)
            if pxy and cm.get("port"):
                for part in ("port", "port_sea"):
                    if cm.get(part):
                        out.append({"kind": part, "model": cm[part], "texture": None, "xy": tuple(pxy),
                                    "scale": 1.0, "faction": fb.name})
        for fo in [f for f in strat.forts if getattr(f, "owner", None) == fb.name]:
            kind = "watchtower" if fo.kind == "watchtower" else "fort"
            model = cm.get(kind)
            if model and fo.kind != "landmark":
                out.append({"kind": kind, "model": model, "texture": None, "xy": tuple(fo.xy), "scale": 1.0,
                            "faction": fb.name})
    # a region with no settlement in descr_strat: the game's rebel village stands there (the user: 'some villages are
    # not shown') - in the culture of the faction that built it (descr_regions' creator), else the rebels'
    try:
        regions = mod.regions(campaign)
    except Exception:
        regions = {}
    for region, xy in tiles.items():
        if tuple(xy) in towns or region not in regions:
            continue
        creator = (regions.get(region) or {}).get("creator") or "slave"
        cm = culture_of(creator)
        model = cm["levels"].get("village") or next(iter(cm["levels"].values()), None)
        if model:
            out.append({"kind": "town", "model": model, "texture": None, "xy": tuple(xy), "scale": 1.0,
                        "faction": "slave"})
            towns.add(tuple(xy))
    # Rome's wonders ('landmark <type> x, y' in descr_strat): their own models of descr_sm_landmarks.txt
    try:
        from . import wonders as W
        kinds = W.types(mod)
    except Exception:
        kinds = {}
    for fo in strat.forts:
        if fo.kind != "landmark":
            continue
        item = (kinds.get(fo.type) or {}).get("item") or MISSING        # no model of its own: the red '?'
        rel = item[5:] if item.lower().startswith("data/") else item
        out.append({"kind": "landmark", "model": rel, "texture": None, "xy": tuple(fo.xy), "scale": 1.0,
                    "faction": None})
    # resources (their lines in descr_strat: 'resource gold, 83, 128')
    res = resource_models(mod)
    for line in strat.lines:
        m = re.match(r"\s*resource\s+([\w\-]+)\s*,\s*(\d+)\s*,\s*(\d+)", strip_comment(line))
        if m:                                             # no model of its type: the red '?'
            out.append({"kind": "resource", "model": res.get(m.group(1)) or MISSING, "texture": None,
                        "xy": (int(m.group(2)), int(m.group(3))), "scale": 1.0, "faction": None})
    # characters: the faction's figure of their type, in its texture
    scales = _strat_scales(mod)
    stood = set()                                         # one figure a tile: an army in a town stands on its roofs
    for fb in strat.factions:
        try:
            figs = {f["type"]: f["models"] for f in SM.figures(mod, fb.name)}
        except Exception:
            figs = {}
        for c in fb.characters:
            if not c.xy or tuple(c.xy) in stood:
                continue
            lines = strat.lines[c.start:c.end]
            kind = "named character" if c.kind == "named character" else (c.kind or "general")
            if any(strip_comment(x).split()[:1] == ["unit"] for x in lines) and kind not in figs:
                kind = "general"
            names = figs.get(CHAR_TYPES.get(kind, kind)) or figs.get("general") or []
            info = SM.mesh_info(mod, names[0]) if names else None
            if info is None or not info.meshes:              # no figure to draw: the red '?' where he stands
                stood.add(tuple(c.xy))
                out.append({"kind": "character", "model": MISSING, "texture": None, "xy": tuple(c.xy), "scale": 1.0,
                            "skeleton": None, "faction": fb.name, "in_town": tuple(c.xy) in towns})
                continue
            tex = info.textures.get(fb.name) or info.textures.get("") or next(iter(info.textures.values()), None)
            sc, skel = scales.get(names[0], (1.0, None))
            stood.add(tuple(c.xy))
            out.append({"kind": "character", "model": info.meshes[0], "texture": tex, "xy": tuple(c.xy),
                        "scale": sc, "skeleton": skel, "faction": fb.name, "faces": True,
                        "in_town": tuple(c.xy) in towns})
    return out


__all__ = ["objects", "culture_models", "resource_models"]
