"""A unit's card and description picture made from its 3D model (View in 3D > Make a card... / Make a picture...):
the model as the 3D view shows it (turned, zoomed, in an animation's frame) cut out of its background, framed the way
the games' own cards are, laid on a background and sized to the mod's own pictures.

The games' own cards (48 x 64, both games) are the figure alone on a see-through ground - the game draws the card's
frame and ground behind it - the man from his head to his thighs, a horseman with the front of his horse, cut at the
bottom; the description pictures (Rome 160 x 210, Medieval II 256 x 384) the whole man.

The cut: the same view drawn twice, on black and on white - where the two differ the picture is see-through (the
smoothed edges keep their part-see-through), so no colour of the model is ever taken for the ground."""

# how much of the figure, from the top, each framing keeps
PARTS = (("whole", "the whole man", 1.0), ("knees", "to the knees", 0.78), ("thighs", "to the thighs", 0.64),
         ("waist", "to the waist", 0.5))
PART_SHARE = {k: v for k, _, v in PARTS}
CARD_PART, PICTURE_PART = "thighs", "whole"
CARD_SIZE = (48, 64)
PICTURE_SIZE = {"rome": (160, 210), "medieval2": (256, 384)}
TOP_ROOM = 0.04                 # room over the head, of the picture's height (the cards' heads touch the top)


def cut_out(on_black, on_white):
    """The figure as an RGBA picture from two drawings of the same view, on black and on white."""
    from PIL import ImageChops
    b, w = on_black.convert("RGB"), on_white.convert("RGB")
    alpha = ImageChops.invert(ImageChops.subtract(w, b).convert("L"))     # 0 where the ground shows through
    out = b.copy()
    out.putalpha(alpha)
    # a point on the edge, part see-through: drawn on black it is its colour x alpha - its own colour back
    px = out.load()
    W = out.width
    for i, a in enumerate(alpha.getdata()):
        if a < 255:
            x, y = i % W, i // W
            if a == 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                c = px[x, y]
                px[x, y] = (min(255, c[0] * 255 // a), min(255, c[1] * 255 // a), min(255, c[2] * 255 // a), a)
    return out


def frame(figure, size, part="whole", scale=1.0, shift=0.0, side=0.0, top=None, box=None):
    """The figure (RGBA) cut and sized to size (w, h): `part` of it from the top (PARTS), its head near the top for a
    part, in the middle for the whole man; scale > 1 brings it nearer, shift moves the figure up (+) or down (-) by
    that share of the picture's height, side right (+) or left (-) by that share of its width. top: room over the
    head (TOP_ROOM for a part). box: the (x0, y0, x1, y1) to frame by (the body without its weapons - a spear held
    high is cut at the top as on the games' cards); else the whole figure's."""
    from PIL import Image
    W, H = size
    box = box or figure.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not box:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    x0, y0, x1, y1 = box
    keep = PART_SHARE.get(part, 1.0)
    bw, bh = x1 - x0, (y1 - y0) * keep
    aspect = W / H
    cx = (x0 + x1) / 2
    if keep < 1.0:                    # a part: the head near the top, cut below - as the games' cards
        room = TOP_ROOM if top is None else top
        rh = max(bh * (1 + room), bw / aspect)
        rh = rh / max(0.1, scale)
        ry = y0 - rh * room
    else:                             # the whole man, a little room all round, in the middle
        room = 0.05 if top is None else top
        rh = max((y1 - y0) * (1 + 2 * room), bw * (1 + 2 * room) / aspect)
        rh = rh / max(0.1, scale)
        ry = (y0 + y1) / 2 - rh / 2
    rw = rh * aspect
    ry += shift * rh
    rx = cx - rw / 2 - side * rw
    # crop with see-through round it where the region runs past the drawing
    left, upper = int(round(rx)), int(round(ry))
    right, lower = int(round(rx + rw)), int(round(ry + rh))
    canvas = Image.new("RGBA", (max(1, right - left), max(1, lower - upper)), (0, 0, 0, 0))
    canvas.paste(figure.crop((max(0, left), max(0, upper), min(figure.width, right), min(figure.height, lower))),
                 (max(0, -left), max(0, -upper)))
    return canvas.resize((W, H), Image.LANCZOS)


def on_ground(picture, ground=None):
    """The framed figure laid on its ground: None = see-through (as the games' own cards), an (r, g, b) colour, or a
    picture (Image) - scaled to cover the whole picture and cut to it."""
    from PIL import Image
    if ground is None:
        return picture
    W, H = picture.size
    if isinstance(ground, tuple):
        base = Image.new("RGBA", (W, H), tuple(ground[:3]) + (255,))
    else:
        g = ground.convert("RGBA")
        k = max(W / g.width, H / g.height)
        g = g.resize((max(W, int(round(g.width * k))), max(H, int(round(g.height * k)))), Image.LANCZOS)
        left, upper = (g.width - W) // 2, (g.height - H) // 2
        base = g.crop((left, upper, left + W, upper + H))
    base.alpha_composite(picture)
    return base


def model_figure(mod, info, faction=None, size=(640, 800), yaw=35.0, pitch=8.0, stand=("stand", "stand_a_idle")):
    """A battle model (models.ModelInfo) standing in its skeleton's stand animation, drawn as the 3D view draws it
    and cut out: (RGBA figure, the box of its body without weapons) - the test mod's card, without a window."""
    from . import animations as AN
    from . import meshview as MV
    from . import models as MO
    path = MV.mesh_path(mod, info.meshes[0]) if info.meshes else None
    if not path:
        raise ValueError("%s: its model file is not here" % info.name)
    mesh = MV.read_file(path)
    man = mesh
    for sk in info.skeletons:
        moves = AN.of_skeleton(mod, sk)
        f = next((f for want in stand for what, f in moves if what.lower() == want), None)
        anim = AN.find(mod, f) if f else None
        if anim is None:
            continue
        pose = MV.Pose.of(anim, 0)
        if path.lower().endswith(".cas"):
            man = MV.read_posed(path, pose)
        else:
            base = AN.base_pose(mod, sk)
            man = (MV.pose_mesh(mesh, pose, base) if base else None) or mesh
        break
    pick = lambda table: table.get(faction) or table.get("") or next(iter(table.values()), None)
    tex = MO.texture_image(mod, pick(info.textures)) if info.textures else None
    if tex is None and man.texture_ref:
        tex = MO.texture_image(mod, man.texture_ref)
    att = MO.texture_image(mod, pick(info.attach)) if info.attach else None
    groups, body = man.shown(), man.shown(0, False)
    if not info.attach and MV.whole_picture(man):
        groups, body = MV.one_picture(groups), MV.one_picture(body)
    shots = [MV.render(man, size, yaw, pitch, 1.0, tex, att, groups, quality=2, background=bg)
             for bg in ((0, 0, 0), (255, 255, 255))]
    alone = cut_out(*[MV.render(man, size, yaw, pitch, 1.0, None, None, body, quality=1, background=bg,
                                textured=False, fit=groups) for bg in ((0, 0, 0), (255, 255, 255))])
    return cut_out(*shots), alone.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()


def picture_size(kind, need, info):
    """(w, h) the picture is made in: the mod's own size (need from editors.unit_picture_need), else the game's."""
    if need:
        return tuple(need[:2])
    return PICTURE_SIZE.get(kind, PICTURE_SIZE["rome"]) if info else CARD_SIZE


__all__ = ["PARTS", "CARD_PART", "PICTURE_PART", "cut_out", "frame", "on_ground", "model_figure", "picture_size"]
