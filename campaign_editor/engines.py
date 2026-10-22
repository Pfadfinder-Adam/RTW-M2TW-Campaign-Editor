"""Medieval II's siege engines with their crew, as the game sets them (the user, 2026-10-10: 'the crew's man, the
engine itself and its animations together with the crew').

What the game reads (worked out on the vanilla catapult, trebuchet, ballista and the guns):
- descr_engines.txt, a 'type <engine>' block: engine_model_group normal / dying / dead, then per group its
  engine_skeleton, engine_bone_map, engine_mesh lines (closest first); reference_points (a .modelReferencePoints file);
  crew_animations: '<engine state> <crew place>, <crew move>, <crew move> ...' - the crew man at that place plays
  those moves one after another while the engine plays that state (crank: loading, fire: shooting).
- descr_engine_skeleton.txt: 'type <engine skeleton>', 'anim <state> <file>' lines (default, idle, moving, crank,
  attack_commence ...) - the files are LOOSE .cas animations in data/animations/engine (Rome's form: a skeleton of
  the engine's own bones - bone_body, wheels, arm, rock, winch - and their keys; meshview.CasAnim).
- the engine's .mesh is skinned on those bones: its own list of bone names gives each point's bone (the bone map
  xml lists them in another order on the catapult - the mesh's own list is the one that moves it right).
- the .modelReferencePoints file (a boost archive): a count, then per point its kind ('Engine StationPoint' - where
  a crew man stands to work it, 'Engine PushPoint' - where he pushes it), a 4 x 4 matrix (row by row, the place in its
  last column: x, up, forward) and its name (Crew_Right, Crew_Left, Crew_Rear ...).
- the crew's moves (crew_right_load_1 ...) are in the crew man's own skeleton (the unit's soldier model: e.g.
  MTW2_Catapult) in the animation packs."""

import re
import struct

from . import meshview as MV


class Engine:
    """A siege engine's block: meshes / skeleton / bone_map of its 'normal' group, reference points file, and
    crew {state (lower): [(place, [crew moves])]}; Rome's crew places: stations [(role, x, forward)] (its
    engine_station lines) and pushes [(x, forward)] (engine_push_point)."""

    def __init__(self, name):
        self.name = name
        self.meshes, self.skeleton, self.bone_map, self.points = [], None, None, None
        self.crew = {}
        self.stations, self.pushes = [], []


def read_engine(mod, kind):
    """The Engine of this type from descr_engines.txt (any case), or None."""
    path = mod.find("descr_engines.txt")
    if not path or not kind:
        return None
    eng, cur, group, in_crew = None, None, None, False
    for line in mod.load(path).texts():
        raw = line.split(";")[0].strip()
        t = raw.replace(",", " ").split()
        if not t:
            continue
        if t[0] == "type":
            if eng is not None:
                break
            cur, group, in_crew = (t[1] if len(t) > 1 else None), None, False
            if cur and cur.lower() == kind.lower():
                eng = Engine(cur)
            continue
        if eng is None:
            continue
        if t[0] == "end":
            break
        if t[0] == "engine_model_group":
            group, in_crew = (t[1].lower() if len(t) > 1 else None), False
        elif t[0] == "crew_animations":
            in_crew = True
        elif in_crew and len(t) >= 3 and "," in raw:
            state, rest = raw.split(None, 1)
            parts = [x.strip() for x in rest.split(",") if x.strip()]
            eng.crew.setdefault(state.lower(), []).append((parts[0], parts[1:]))
        elif t[0] == "reference_points" and len(t) > 1:
            eng.points = t[1]
        elif t[0] == "engine_station" and len(t) >= 4 and _num(t[2]) is not None and _num(t[3]) is not None:
            eng.stations.append((t[1], _num(t[2]), _num(t[3])))
        elif t[0] == "engine_push_point" and len(t) >= 3 and _num(t[1]) is not None and _num(t[2]) is not None:
            eng.pushes.append((_num(t[1]), _num(t[2])))
        elif group in (None, "normal"):
            if t[0] in ("engine_mesh", "engine_model") and len(t) > 1:
                eng.meshes.append(t[1])
            elif t[0] == "engine_skeleton" and len(t) > 1:
                eng.skeleton = t[1]
            elif t[0] == "engine_bone_map" and len(t) > 1:
                eng.bone_map = t[1]
    return eng


def _num(t):
    try:
        return float(t)
    except ValueError:
        return None


def station_points(eng):
    """Rome's crew places as reference points {(kind, name): (x, up, forward)}: the engine_station lines standing
    (Engine StationPoint, 'crank 1', 'captain 1' ...) and the engine_push_point lines moving (Engine PushPoint) -
    on the ground, the game's own numbers from descr_engines.txt."""
    out, seen = {}, {}
    for role, x, z in eng.stations:
        seen[role] = seen.get(role, 0) + 1
        out[("Engine StationPoint", "%s %d" % (role, seen[role]))] = (x, 0.0, z)
    for k, (x, z) in enumerate(eng.pushes, 1):
        out[("Engine PushPoint", "push %d" % k)] = (x, 0.0, z)
    return out


def read_points(data):
    """{(kind, name): (x, up, forward)} of a .modelReferencePoints file's bytes: each point's kind text, its 4 x 4
    matrix (the place in the last column) and its name text."""
    out = {}
    texts = []
    for m in re.finditer(rb"([\x02-\x40])\x00\x00\x00", data):
        n, p = m.group(1)[0], m.start()
        s = data[p + 4:p + 4 + n]
        if len(s) == n and all(32 <= c < 127 for c in s) and s[:1].isalpha():
            texts.append((p, p + 4 + n, s.decode("latin-1")))
    for (p0, e0, kind), (p1, _, name) in zip(texts, texts[1:]):
        if not kind.startswith(("Engine", "Artillery")) or p1 - 64 < e0:
            continue
        mat = struct.unpack_from("<16f", data, p1 - 64)
        if abs(mat[15] - 1.0) > 1e-3:
            continue
        out[(kind, name)] = (mat[3], mat[7], mat[11])
    return out


def points_of(mod, eng):
    """The engine's reference points (read_points), {} when its file is not found."""
    path = mod.find(eng.points) if eng is not None and eng.points else None
    if not path:
        return {}
    with open(path, "rb") as fh:
        return read_points(fh.read())


def moves(mod, skeleton):
    """{state (lower): animation file} of an engine skeleton from descr_engine_skeleton.txt, in the file's order."""
    from .animations import skeleton_anims
    return {w.lower(): f for w, f in skeleton_anims(mod, skeleton, "descr_engine_skeleton.txt")}


_ANIMS = {}


def anim(mod, rel):
    """The loose .cas animation (meshview.CasAnim) at rel ('data/animations/engine/x.CAS'), or None."""
    rel = (rel or "").replace("\\", "/")
    rel = rel[5:] if rel.lower().startswith("data/") else rel
    path = mod.find(rel) if rel else None
    if not path:
        return None
    if path not in _ANIMS:
        try:
            with open(path, "rb") as fh:
                _ANIMS[path] = MV.CasAnim(fh.read(), rel)
        except (OSError, ValueError):
            _ANIMS[path] = None
    return _ANIMS[path]


def rigged(mesh, an):
    """The engine's mesh with its points' bones put in the animation's order (by the bones' names: the mesh's own
    list) and the animation's bone tree - ready for meshview.pose_mesh; None when they do not meet."""
    if not getattr(mesh, "skin", None) or not mesh.bone_names or an is None:
        return None
    idx = {n.lower(): i for i, n in enumerate(an.names)}
    to = {k: idx.get(n.lower()) for k, n in mesh.bone_names.items()}
    if not any(v is not None for v in to.values()):
        return None
    body = idx.get("bone_body", 1 if an.bones > 1 else 0)
    m = MV.Mesh(mesh.groups, mesh.positions, mesh.uvs)
    m.skin = [(to.get(a) if to.get(a) is not None else body, to.get(b) if to.get(b) is not None else body, w0, w1)
              for a, b, w0, w1 in mesh.skin]
    m.parents = an.parents
    m.one_texture, m.texture_ref, m.bone_names = mesh.one_texture, mesh.texture_ref, {}
    return m


def pose(mesh, an, base, frame):
    """The engine's mesh in frame `frame` of its animation (base: its 'default' animation - the pose the mesh is made
    in); the mesh as it is when it cannot be posed."""
    m = rigged(mesh, an)
    if m is None or base is None:
        return mesh
    from .animations import Skeleton
    sk = Skeleton("", an.parents, base.offsets(0), getattr(an, "names", None))
    sk.binds = Skeleton.from_anim("", sk, base).binds
    got = MV.pose_mesh(m, MV.Pose.of(an, frame), sk)
    return got or mesh


# the engine's states as the 3D view offers them: (words, engine state, crew state, where the crew stands)
STATES = (("standing", "idle", None, "Engine StationPoint"),
          ("moving (pushed)", "moving", None, "Engine PushPoint"),
          ("loading", "crank", "crank", "Engine StationPoint"),
          ("shooting", "attack_commence", "fire", "Engine StationPoint"))


def crew_places(eng, points, where):
    """[(place name, (x, up, forward))] of the crew for `where` (StationPoint / PushPoint) - the places
    crew_animations names, else every point of that kind."""
    names = []
    for lst in eng.crew.values():
        for place, _ in lst:
            if place not in names:
                names.append(place)
    got = [(n, points[(where, n)]) for n in names if (where, n) in points]
    if not got:
        got = [(n, p) for (k, n), p in points.items() if k == where]
    return got


def crew_moves(eng, state, place, known):
    """The crew man's moves at `place` in this engine state: crew_animations' list for it (those his skeleton has),
    else his place's idle ('crew_right' for Crew_Right), else his standing move."""
    lst = next((ms for p, ms in eng.crew.get(state or "", []) if p.lower() == place.lower()), None)
    got = [m for m in (lst or []) if m.lower() in known]
    if got:
        return got
    idle = place.lower()
    if idle in known:
        return [idle]
    return [m for m in ("crew_stand", "stand_a_idle", "stand") if m in known][:1]


def scene(engine_mesh, engine_groups, men):
    """One Mesh of the engine (picture 2, its own texture) and its crew: men [(posed mesh, groups, (x, y, z))], each
    man's points moved to his place (picture 0, the crew's texture)."""
    pieces = [(engine_mesh, engine_groups, (0.0, 0.0, 0.0), 2, True)]
    for mesh, groups, at in men:
        pieces.append((mesh, groups, at, 0, mesh.one_texture))
    return MV.assemble(pieces)


__all__ = ["Engine", "read_engine", "read_points", "station_points", "points_of", "moves", "anim", "rigged", "pose", "STATES",
           "crew_places", "crew_moves", "scene"]
