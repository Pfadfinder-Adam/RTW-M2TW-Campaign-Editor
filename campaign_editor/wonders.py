"""Rome's wonders (landmarks) as the game shows them: descr_sm_landmarks.txt gives each type its campaign-map model
(item, a .cas in models_strat), its picture (image, ui/wonders) and its movie; text/landmarks.txt (the keys listed in
descr_landmarks_lookup.txt) its title, short and long description and what it does; descr_strat.txt places it
(`landmark <type> x, y`). The types are the game's own seven - the exe (and REX) refuses any other ("dont
recognise this wonder type"), so a new wonder is one of them put on the map, with its model, picture and texts
changed if one likes. Medieval II has no wonders."""

import os

KEYS = ("item", "image", "movie")


def types(mod):
    """{type: {'item', 'image', 'movie', 'rtm': {..}}} from descr_sm_landmarks.txt (paths as written)."""
    p = os.path.join(mod.data, "descr_sm_landmarks.txt")
    if not os.path.isfile(p):
        return {}
    out, cur = {}, None
    for line in mod.load(p).texts():
        t = line.split(";")[0].split()
        if len(t) < 2:
            continue
        if t[0] == "type":
            cur = out.setdefault(t[1], {"rtm": {}})
        elif cur is not None:
            if t[0] in KEYS:
                cur[t[0]] = t[1]
            elif t[0].endswith("_rtm"):
                cur["rtm"][t[0][:-4]] = t[1]
    return out


def _file(mod, rel):
    """A data-relative or 'data/...' path on disk (case as it lies; .dds beside a .tga too), or None."""
    from .clone import picture_file
    if not rel:
        return None
    rel = rel.replace("\\", "/")
    if rel.lower().startswith("data/"):
        rel = rel[5:]
    got = picture_file(mod.data, rel)
    if got:
        return got[1]
    p = os.path.join(mod.data, *rel.split("/"))
    return p if os.path.isfile(p) else None


def info(mod, kind):
    """What the game shows of a wonder: {'type', 'title', 'short', 'long', 'effects', 'image' (file or None),
    'item' (data-relative .cas or None), 'item_file', 'texture' (data-relative or None)}."""
    from .charpanel import strings
    d = types(mod).get(kind) or {}
    texts = strings(mod, "landmarks.txt")

    def text(key):
        return (texts.get(key.upper()) or texts.get(key) or "").replace("\\n", "\n").strip()
    item = d.get("item")
    rel = item[5:] if item and item.lower().startswith("data/") else item
    item_file = _file(mod, item)
    texture = None
    if item_file:
        try:
            from . import meshview as MV
            m = MV.read_file(item_file)
            ref = getattr(m, "texture_ref", None)          # 'data/models_unit/textures/x.tga' as read_cas makes it
            if ref:
                name = ref.replace("\\", "/").split("/")[-1]
                for folder in (os.path.dirname(rel) + "/textures", "models_strat/textures", "models_unit/textures"):
                    cand = "%s/%s" % (folder, name)
                    if _file(mod, cand):
                        texture = cand
                        break
        except Exception:
            pass
    return {"type": kind, "title": text(kind + "_title") or kind, "short": text(kind + "_short_descr"),
            "long": text(kind + "_long_descr"), "effects": text(kind + "_effects"),
            "image": _file(mod, d.get("image")), "item": rel, "item_file": item_file, "texture": texture}


def model_info(mod, kind):
    """A models.ModelInfo of the wonder's map model for the 3D view, or None."""
    from .models import ModelInfo
    w = info(mod, kind)
    if not w["item"]:
        return None
    mi = ModelInfo(w["title"])
    mi.meshes = [w["item"]]
    if w["texture"]:
        mi.textures = {"": w["texture"]}
    return mi
