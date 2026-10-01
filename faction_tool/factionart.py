"""A faction's pictures: every picture file named after it (buttons, symbols,
logos, banners, the leader's picture, the campaign-select map...), what each
needs (size, depth), replacing any of them, and the campaign-select map
map_<faction>.tga drawn from the faction's start regions.

The campaign-select maps of a campaign (map_<faction>.tga in its folder, vanilla
384 x 237, 24-bit) share one background; each lights its faction's land in a
colour of its own, the ground's texture showing through. The background is what
most of them have at each pixel; the land is map_regions.tga scaled to the
picture; the light is the colour times the ground's brightness (to the power 0.3), a crisp
edge softened by half a pixel - denser than vanilla's, by the user's choice."""

import colorsys
import os
import re

from .clone import (ART_ROOTS, _token_hit, disk_tail, link_users, own_picture_ref, picture_file, picture_links,
                    set_picture_ref)
from .editors import tga_info
from .moddata import _ci

PICTURE_EXT = (".tga", ".dds", ".png", ".bmp")


# ---------------------------------------------------------------------------
# Every picture of a faction
# ---------------------------------------------------------------------------
# (test on the path, what it is, where the game shows it) - the first that fits wins
PICTURE_KINDS = (
    (lambda low, name: "fe_buttons_24" in low, "small campaign-menu button",
     "the small faction button of the campaign menus"),
    (lambda low, name: "fe_buttons_48" in low, "big campaign-menu button",
     "the big faction button of the campaign-select screen"),
    (lambda low, name: "battlefield_pics" in low, "battle-select picture",
     "the custom / historical battle screen, behind the faction's name"),
    (lambda low, name: "fe_faction_units" in low, "units picture on the faction screen",
     "the faction-select screen, the soldiers standing under the faction's name"),
    (lambda low, name: "fe_symbols_80" in low, "symbol on the faction screen",
     "the faction-select screen, the faction's symbol (80 px)"),
    (lambda low, name: "faction_symbols" in low, "faction symbol (in-game panels)",
     "the campaign's panels: settlement, character and diplomacy scrolls"),
    (lambda low, name: "/fe_flags" in low or "flag" in name, "flag",
     "the front-end menus, next to the faction's name"),
    (lambda low, name: low.startswith("loading_screen"), "loading-screen logo",
     "the loading screen while the campaign loads"),
    (lambda low, name: name.startswith("map_"), "campaign-select map (its land lit)",
     "the campaign-select screen: the map with the faction's land lit"),
    (lambda low, name: name.startswith("vcs_"), "victory conditions map (short campaign)",
     "the campaign-select screen, the regions to take in the short campaign"),
    (lambda low, name: name.startswith("vc_"), "victory conditions map",
     "the campaign-select screen, the regions to take to win"),
    (lambda low, name: name.startswith("leader_pic"), "leader picture (campaign select)",
     "the campaign-select screen, the faction leader's face"),
    (lambda low, name: "faction_icons" in low, "faction icon",
     "the campaign map's top bar and the faction lists"),
    (lambda low, name: "captain" in name and "portrait" in name, "captain's portrait",
     "the army panel of an army led by a captain (no named general)"),
    (lambda low, name: "captain" in name, "captain's card",
     "the unit card of a captain's bodyguard in the army panel"),
    (lambda low, name: "standard" in name or "banner" in low, "banner / standard texture",
     "the banners carried over the faction's units in battle"),
    (lambda low, name: "/units/" in low or "/unit_info/" in low, "unit picture",
     "the unit cards and the unit information scroll"),
    (lambda low, name: "symbol" in name, "symbol",
     "the faction's symbol in the menus"),
)


def _picture_kind(rel):
    low = rel.replace("\\", "/").lower()
    name = os.path.basename(low)
    for test, kind, where in PICTURE_KINDS:
        if test(low, name):
            return low, name, kind, where
    folder = os.path.dirname(low)
    return low, name, "picture in %s" % (folder or "data"), None


def label_of(rel):
    """A plain name for what a picture is, from where it lies."""
    low, name, kind, _ = _picture_kind(rel)
    for part, word in (("_roll", " (mouse over)"), ("_select", " (selected)"), ("_grey", " (greyed out)"),
                       ("_rebel", " (rebel)")):
        if part in name:
            kind += word
            break
    if "/dead/" in low:
        kind += " (dead)"
    return kind


def where_shown(rel):
    """Where the game shows the picture, or None when the tool does not know."""
    return _picture_kind(rel)[3]


def faction_pictures(mod, campaign, faction):
    """[{'path', 'rel', 'label', 'size': (w, h, bpp) or None}] of every picture file
    named after the faction under data/ui, data/menu, data/loading_screen, the
    campaign folder, and its banner textures in descr_banners.txt - not the
    unit cards (the unit editor has those)."""
    out, seen = [], {}

    def add(p):
        n = os.path.normcase(os.path.abspath(p))
        if n in seen or not os.path.isfile(p):
            return seen.get(n)
        rel = os.path.relpath(p, mod.data).replace("\\", "/")
        e = {"path": p, "rel": rel, "label": label_of(rel), "where": where_shown(rel), "size": picture_info(p)}
        seen[n] = e
        out.append(e)
        return e
    roots = [os.path.join(mod.data, r) for r in ART_ROOTS] + [mod.campaign_dir(campaign)]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            low = dirpath.replace("\\", "/").lower()
            if "/ui/units" in low or "/ui/unit_info" in low:
                dirnames[:] = []
                continue
            for d in dirnames:
                if d.lower() == faction:                      # a folder of its own: all of it
                    for sp, _, fs in os.walk(os.path.join(dirpath, d)):
                        for n in fs:
                            if n.lower().endswith(PICTURE_EXT):
                                add(os.path.join(sp, n))
            dirnames[:] = [d for d in dirnames if d.lower() != faction]
            for n in filenames:
                if n.lower().endswith(PICTURE_EXT) and _token_hit(n, faction):
                    add(os.path.join(dirpath, n))
    # pictures the faction's lines name by path (banners, loading logo): 'link' = [file key, field],
    # 'ref' = the path as written, 'shared' = the other factions naming the same file
    links = picture_links(mod)
    users = link_users(links)
    from .stratmodels import figures
    who = {}                                            # strat model: the faction's characters it shows
    for fg in figures(mod, faction):
        for m in fg["models"]:
            who.setdefault(m, []).append(fg["type"])
    for l in links:
        if l["faction"] != faction:
            continue
        if l["key"] == "model_strat" and l["field"].split(":", 1)[1] not in who:
            continue                                    # a figure none of its characters uses: not its picture
        got = picture_file(mod.data, l["ref"])
        e = add(got[1]) if got else None
        if e is not None:
            e.update(link=[l["key"], l["field"]], ref=l["ref"],
                     shared=sorted(users.get(l["ref"].replace("\\", "/").lower(), set()) - {faction}))
            if l["key"] == "model_strat":               # a campaign-map figure: which one, who is shown by it
                kind, model = l["field"].split(":", 1)
                e["label"] = "campaign map figure: %s%s" % (model, " (standing still)" if kind != "texture" else "")
                e["where"] = "the campaign map: the faction's %s" % ", ".join(who[model])
    for x in extra_pictures(mod, faction):
        e = add(x["path"])
        if e is not None:
            e.update(label=x["label"], where=x["where"], extra=x)
            others = sorted(u for u in x["users"] if u.lower() != faction.lower())
            if others:
                e.update(locked=True, note="shared with %s%s" % (", ".join(others[:4]), (
                    " - Recolour gives them copies of their own first" if (x.get("owner") or "").lower() ==
                    faction.lower() else " - Recolour gives %s a copy of its own" % faction)))
    out.sort(key=lambda e: (e["label"], e["rel"]))
    from .symbols import entries
    return entries(mod, faction) + out          # the flag symbol and logos on shared sheets first


def extra_pictures(mod, faction):
    """The faction's pictures named in other files than the Art lines: the faction symbol's texture (the 3D symbol
    model of descr_sm_factions.txt names it inside), the flag on its towns in battle (Rome's descr_building_battle
    '<faction> ##standard_x.tga'), the battle banners (Medieval II's descr_banners_new.xml Faction= DiffuseMap=).
    [{'path', 'label', 'where', 'users': factions naming the same file}]."""
    from .packs import _on_disk
    out = []

    def texture(rel):
        rel = rel.replace("\\", "/")
        for r in (rel, rel + ".dds", rel[:-4] + ".texture" if rel.lower().endswith(".tga") else None):
            got = _on_disk(mod, r) if r else None
            if got:
                return got[1]
        return None
    sm = _ci(mod.data, "descr_sm_factions.txt")
    symbols, cur = {}, None
    if sm:
        for line in open(sm, encoding="latin-1"):
            t = line.split(";")[0].split()
            if len(t) >= 2 and t[0] == "faction":
                cur = t[1].strip(",")
            elif len(t) >= 2 and t[0] == "symbol" and cur:
                symbols.setdefault(t[1].lower(), [t[1], set()])[1].add(cur)
    for ref, users in symbols.values():
        if faction not in users:
            continue
        got = _on_disk(mod, ref.replace("\\", "/"))
        if not got:
            continue
        with open(got[1], "rb") as fh:
            raw = fh.read()
        base = os.path.dirname(os.path.relpath(got[1], mod.data)).replace("\\", "/")
        for m in re.finditer(rb"textures[\\/]([^\x00\\/]{1,80}?\.tga)", raw, re.I):
            p = texture(base + "/textures/" + m.group(1).decode("latin-1"))
            if p:
                out.append({"path": p, "label": "faction symbol (3D) texture", "users": set(users),
                            "kind": "symbol", "ref": ref, "cas": got[1], "tex": m.group(1).decode("latin-1"),
                            "where": "the faction's 3D symbol (%s): the faction-select screen and the campaign "
                                     "map's faction panels" % os.path.basename(ref)})
    bb = _ci(mod.data, "descr_building_battle.txt")
    if bb:
        whose = {}
        for line in open(bb, encoding="latin-1"):
            t = line.split(";")[0].split()
            if len(t) == 2 and t[1].lower().endswith(".tga") and t[1].startswith("#"):
                whose.setdefault(t[1].lower(), set()).add(t[0])
        for tex, fs in sorted(whose.items()):
            if faction in fs:
                p = texture("models_building/textures/" + tex)
                if p:
                    out.append({"path": p, "label": "flag on its towns in battle", "users": fs, "kind": "town_flag",
                                "ref": tex, "file": bb,
                                "where": "the flags on the faction's towns and forts in a siege battle"})
    xml = _ci(mod.data, "descr_banners_new.xml")
    if xml:
        whose, refs = {}, {}
        for m in re.finditer(r'Faction="([^"]+)"[^>]*?DiffuseMap="([^"]+)"', open(xml, encoding="latin-1").read()):
            k = m.group(2).replace("\\", "/").lower()
            whose.setdefault(k, set()).add(m.group(1).lower())
            refs.setdefault(k, m.group(2))
        for tex, fs in sorted(whose.items()):
            if faction.lower() in fs and "test_" not in tex:
                p = texture(tex)
                if p:
                    out.append({"path": p, "label": "battle banner %s" % os.path.basename(tex), "users": fs,
                                "kind": "banner", "ref": refs[tex], "file": xml,
                                "where": "the banners over the faction's units in battle"})
    for x in out:
        base = os.path.basename(x["path"]).lower()
        x["owner"] = next((u for u in sorted(x["users"], key=len, reverse=True)
                           if _token_hit(base, u.lower()) or _token_hit(base, _short_name(u))), None)
    return out


def _short_name(f):
    f = f.lower()
    return f.split("_", 1)[1] if f.startswith("romans_") else f


def _same_length_name(old, owner, who):
    """A file name as long as `old` with `who` in place of `owner` (a texture name baked into a .cas model is
    rewritten in place - the same length keeps the model's bytes where they were)."""
    new = re.sub(re.escape(owner), who, old, flags=re.I) if owner and owner.lower() in old.lower() else old + "_" + who
    if len(new) > len(old):
        new = new[:len(old)]
    return new + "_" * (len(old) - len(new))


def share_out(plan, x, faction):
    """An extra picture (extra_pictures) several factions name, made the faction's own - the web pulled along: when
    the file carries the faction's name, every other faction naming it first gets a copy of its own (its line
    pointed at it) and the file stays where it is; otherwise the faction gets the copy. Returns the path the
    faction's picture is now written to."""
    others = sorted(set(x["users"]) - {faction, faction.lower()})
    if x.get("owner") and x["owner"].lower() == faction.lower():
        for o in others:
            _copy_for(plan, x, o, keep=True)
        return x["path"]
    return _copy_for(plan, x, faction, keep=False)


def _copy_for(plan, x, who, keep):
    """A copy of x's picture for faction `who`, its lines pointed at it. keep: the copy holds the picture as it is
    (a borrower keeps its look); else the caller writes the new picture there. Returns the copy's path."""
    mod = plan.mod
    owner = x.get("owner") or ""
    folder, name = os.path.split(x["path"])
    stem, ext = name.split(".", 1)
    if x["kind"] == "symbol":
        tex_stem = x["tex"].rsplit(".", 1)[0]
        new_stem = _same_length_name(tex_stem, owner, who)
        k = 0
        while os.path.exists(os.path.join(folder, new_stem + "." + ext)) and k < 9:
            k += 1
            new_stem = new_stem[:-1] + str(k)
        dst = os.path.join(folder, new_stem + "." + ext)
        with open(x["cas"], "rb") as fh:
            raw = fh.read()
        raw = raw.replace(tex_stem.encode("latin-1"), new_stem.encode("latin-1"), 1)
        cas_dir, cas_name = os.path.split(x["cas"])
        cas_ext = cas_name.rsplit(".", 1)[1]
        new_cas = os.path.join(cas_dir, "symbol_%s.%s" % (who, cas_ext))
        if os.path.exists(new_cas):
            new_cas = os.path.join(cas_dir, "symbol_%s_own.%s" % (who, cas_ext))
        plan.binary(new_cas, raw)
        sm = _ci(mod.data, "descr_sm_factions.txt")
        f = plan.edit(sm)
        cur = None
        for i, t in enumerate(f.texts()):
            tok = t.split(";")[0].split()
            if len(tok) >= 2 and tok[0] == "faction":
                cur = tok[1].strip(",")
            elif len(tok) >= 2 and tok[0] == "symbol" and cur == who and tok[1] == x["ref"]:
                ref = x["ref"].rsplit("/", 1)[0] + "/" + os.path.basename(new_cas)
                set_picture_ref(f, i, x["ref"], ref)
                plan.note(f, "%s's symbol now %s (was %s, shared)" % (who, ref, x["ref"]))
    else:
        new_stem = re.sub(re.escape(owner), who, stem, flags=re.I) if owner and owner.lower() in stem.lower() \
            else stem + "_" + who
        dst = os.path.join(folder, new_stem + "." + ext)
        f = plan.edit(x["file"])
        new_ref = x["ref"].replace(stem, new_stem) if stem in x["ref"] else \
            re.sub(re.escape(stem), new_stem, x["ref"], flags=re.I)
        for i, t in enumerate(f.texts()):
            if x["kind"] == "banner":
                m = re.search(r'Faction="([^"]+)"', t)
                hit = m and m.group(1).lower() == who.lower() and ('DiffuseMap="%s"' % x["ref"]) in t
            else:
                tok = t.split(";")[0].split()
                hit = len(tok) == 2 and tok[0] == who and tok[1].lower() == x["ref"].lower()
            if hit:
                set_picture_ref(f, i, x["ref"] if x["kind"] == "banner" else tok[1], new_ref)
        plan.note(f, "%s's %s now %s (was %s, shared)" % (who, x["label"], new_ref, x["ref"]))
    if keep:
        with open(x["path"], "rb") as fh:
            plan.binary(dst, fh.read())
    return dst


def picture_info(path):
    """(width, height, depth) of a picture: bits per pixel for a TGA, the DDS format
    ('DXT5', 'DXT1', 'RGBA'...) for a DDS; None when unknown."""
    low = path.lower()
    if low.endswith(".tga"):
        return tga_info(path)
    if low.endswith(".dds"):
        got = dds_info(path)
        return got[:3] if got else None
    return None


def dds_info(path):
    """(width, height, format, mipmap levels) from a DDS header, or None."""
    try:
        with open(path, "rb") as fh:
            h = fh.read(128)
    except OSError:
        return None
    if len(h) < 128 or h[:4] != b"DDS ":
        return None
    le = lambda k: int.from_bytes(h[k:k + 4], "little")
    four = h[84:88]
    fmt = four.decode("latin-1") if le(80) & 0x4 else ("RGBA" if le(80) & 0x1 else "RGB")
    return le(16), le(12), fmt, max(1, le(28))


def picture_target(e, owner, new):
    """Where a picture of the list is written for faction `new` (`owner` = the faction the
    list was read for: the template of a new faction, else the same). A picture found by its
    name gets the name swapped (as the clone copies it); a picture a line names gets the name
    the clone gives it, or, shared with other factions, a copy of the faction's own."""
    rel = e["rel"]
    if e.get("symbol"):
        return rel                                        # symbols.FLAG / LOGO / SMALL: written by symbols.write
    if e.get("link"):
        if not e.get("shared") and owner == new:
            return rel                                    # already its own
        ref = own_picture_ref(e["ref"], owner, new)
        ref = ref[5:] if ref.lower().startswith("data/") else ref
        return ref + disk_tail(e["ref"], rel)
    if not new or new == owner:
        return rel
    return re.sub(r"(?i)(^|[^a-z0-9])%s(?=$|[^a-z0-9])" % re.escape(owner), lambda m: m.group(1) + new, rel)


def original_picture(mod, rel):
    """The picture under data/rel as it was before this tool first changed it: the copy the
    oldest backup kept (what Restore brings back), or for a picture the tool made, the file it
    was copied from; None when the tool never changed it (it is the original)."""
    import json
    from .plan import backups
    root = os.path.dirname(mod.data)
    want = os.path.normcase(os.path.relpath(os.path.join(mod.data, *rel.split("/")), root))
    for b in reversed(backups(mod)):                    # the oldest first
        try:
            with open(os.path.join(b, "manifest.json"), encoding="utf-8") as fh:
                m = json.load(fh)
        except (OSError, ValueError):
            continue
        for r in m.get("modified", []):
            if os.path.normcase(r) == want and os.path.isfile(os.path.join(b, r)):
                return os.path.join(b, r)
        for r in m.get("created", []):
            if os.path.normcase(r) == want:
                src = (m.get("copied_from") or {}).get(r)
                p = os.path.join(root, src) if src else None
                return p if p and os.path.isfile(p) else None
    return None


# ---------------------------------------------------------------------------
# The campaign-select map
# ---------------------------------------------------------------------------
def map_name(campaign_dir, faction):
    """The campaign-select map of a faction in the campaign folder (existing case), or the
    name a new one gets."""
    return _ci(campaign_dir, "map_%s.tga" % faction) or os.path.join(campaign_dir, "map_%s.tga" % faction)


def _pixels(im):
    """The pixels of a Pillow image as a list (get_flattened_data where Pillow has it)."""
    return list(getattr(im, "get_flattened_data", im.getdata)())


def default_map_colour(primary):
    """The light a faction's land gets on the campaign-select map: its primary colour's
    hue, lighter and softer (vanilla picks each by hand; this lands near them)."""
    if not primary:
        return (200, 200, 200)
    h, s, v = colorsys.rgb_to_hsv(*[c / 255.0 for c in primary])
    if s < 0.08:                                            # black, grey, white: a light grey
        return (215, 215, 212)
    r, g, b = colorsys.hsv_to_rgb(h, min(max(s, 0.35), 0.6), 0.82)
    return int(r * 255), int(g * 255), int(b * 255)


def select_background(mod, campaign):
    """(Pillow RGB image, the file it copies the layout of) - what most of the
    campaign's map_*.tga have at each pixel; None with fewer than three maps."""
    key = ("select_bg", campaign)
    if key in mod._cache:
        return mod._cache[key]
    try:
        from PIL import Image
    except ImportError:                     # without Pillow (python + the standard library only): no drawing
        return None
    folder = mod.campaign_dir(campaign)
    maps = []
    # only map_<faction>.tga of real factions (their front-end names too): the campaign folder
    # may also hold map_regions, map_heights, map_ground_types... (HLR keeps them there)
    from .clone import FE_NAMES
    names = set()
    for n, _ in mod.factions():
        names.add(n.lower())
        if FE_NAMES.get(n):
            names.add(FE_NAMES[n].lower())
    names |= {n.split("_", 1)[-1] for n in names if n.startswith("romans_")}      # map_julii
    if os.path.isdir(folder):
        for n in sorted(os.listdir(folder)):
            m = re.match(r"map_(.+)\.tga$", n, re.I)
            if m and m.group(1).lower() in names:
                try:
                    im = Image.open(os.path.join(folder, n)).convert("RGB")
                except Exception:
                    continue
                maps.append((n, im))
    sizes = {}
    for n, im in maps:
        sizes.setdefault(im.size, []).append((n, im))
    group = max(sizes.values(), key=len) if sizes else []
    if len(group) < 3:
        mod._cache[key] = None
        return None
    w, h = group[0][1].size
    datas = [_pixels(im) for _, im in group]
    half = len(datas) // 2
    out = []
    for i in range(w * h):
        vals = sorted(d[i] for d in datas)                  # the middle value: what most have
        out.append(vals[half])
    bg = Image.new("RGB", (w, h))
    bg.putdata(out)
    mod._cache[key] = (bg, os.path.join(folder, group[0][0]))
    return mod._cache[key]


def _map_mask(mod, campaign, keep):
    """An L image the size of map_regions.tga, top row first: 255 where keep(rgb)."""
    from PIL import Image
    from .mapdata import recolour
    img = mod.region_map(campaign)
    w, h = img.width, img.height
    rgb = Image.frombytes("RGB", (w, h), img.rgb_top_down())
    table = {c: (255, 255, 255) for c in img.colours() if keep(c)}
    return recolour(rgb, table, (0, 0, 0)).convert("L")


def _place(mask, frame, size):
    """The map-sized mask scaled and set where the map lies in the picture.
    frame = (sx, sy, dx, dy) (or the older (s, dx, dy))."""
    from PIL import Image
    sx, sy, dx, dy = frame if len(frame) == 4 else (frame[0], frame[0], frame[1], frame[2])
    big = mask.resize((max(1, round(mask.width * sx)), max(1, round(mask.height * sy))), Image.NEAREST)
    out = Image.new("L", size)
    out.paste(big, (dx, dy))
    return out


def select_frame(mod, campaign, size=None):
    """(sx, sy, dx, dy): where the map lies in the campaign's select pictures - a map pixel
    x, y (top row first) is picture pixel x * sx + dx, y * sy + dy. Rome's pictures are the
    whole map stretched (the same shape as map_regions). Medieval II's are the map scaled
    about 1.39 and shifted inside a decorated frame, the Americas cut off: learnt from the
    pictures themselves - first land against sea, then (the fit that counts) where the game
    lights each faction's own start regions on its own map_<faction>.tga."""
    key = ("select_frame", campaign)
    if key in mod._cache:
        return mod._cache[key]
    got = select_background(mod, campaign)
    img = mod.region_map(campaign)
    if not got:
        return None
    bg, _ = got
    pw, ph = size or bg.size
    W, H = img.width, img.height
    stretch = (pw / W, ph / H, 0, 0)
    if abs((pw / W) / (ph / H) - 1) < 0.03:
        mod._cache[key] = stretch                  # the same shape as the map: the whole map stretched (Rome)
        return stretch
    # the fit takes seconds: kept in the settings, per mod, campaign and sizes
    from . import settings
    skey = "%s|%s|%dx%d|%dx%d" % (os.path.normcase(os.path.abspath(mod.data)), campaign, pw, ph, W, H)
    known = settings.get("select_frames2", {}) or {}
    if isinstance(known.get(skey), list) and len(known[skey]) == 4:
        frame = tuple(known[skey])
    else:
        info = mod.regions(campaign)
        cols = {r["colour"] for r in info.values()} | {(0, 0, 0), (255, 255, 255)}
        land = _map_mask(mod, campaign, lambda c: c in cols)
        s, dx, dy = _fit(bg.convert("L"), land, (pw / W, 0, 0))
        frame = _fit_lit(mod, campaign, bg, (s, s, dx, dy))
        known = dict(known)
        known[skey] = list(frame)
        settings.put("select_frames2", known)
    mod._cache[key] = frame
    return frame


def _fit_lit(mod, campaign, bg, frame):
    """The frame moved to where the vanilla pictures really light each faction: for up to
    six factions with a map_<faction>.tga, the pixels that differ from the background
    against the faction's start regions laid on the picture; the best mean overlap wins."""
    from PIL import Image, ImageChops, ImageStat
    from .strat import Strat
    try:
        owners = Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).owners()
    except Exception:
        return frame
    regions = {}
    for r, f in owners.items():
        regions.setdefault(f, []).append(r)
    info = mod.regions(campaign)
    folder = mod.campaign_dir(campaign)
    pairs = []
    for f, regs in regions.items():
        path = _ci(folder, "map_%s.tga" % f)
        if not path or f == "slave":
            continue
        try:
            im = Image.open(path).convert("RGB")
        except Exception:
            continue
        if im.size != bg.size:
            continue
        lit = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 20 else 0)
        area = ImageStat.Stat(lit).sum[0] / 255
        cols = {info[r]["colour"] for r in regs if r in info}
        if area > 40 and cols:
            pairs.append((area, lit, _map_mask(mod, campaign, lambda c, cols=cols: c in cols)))
    pairs = [(lit, mask) for _, lit, mask in sorted(pairs, key=lambda p: -p[0])[:6]]
    if len(pairs) < 3:
        return frame

    def score(fr):
        t = 0.0
        for lit, mask in pairs:
            a = _place(mask, fr, bg.size)
            both = ImageStat.Stat(ImageChops.darker(a, lit)).sum[0]
            either = ImageStat.Stat(ImageChops.lighter(a, lit)).sum[0]
            t += both / either if either else 0.0
        return t / len(pairs)
    sx, sy, dx, dy = frame
    best = (score(frame), frame)
    for i in range(-6, 7):                                   # the scale within 6 %, the place within 12 px
        s = sx * (1 + 0.01 * i)
        for ddx in range(-12, 13, 3):
            for ddy in range(-12, 13, 3):
                fr = (s, s, dx + ddx, dy + ddy)
                v = score(fr)
                if v > best[0]:
                    best = (v, fr)
    sx0, _, dx0, dy0 = best[1]
    for i in range(-2, 3):                                   # then each axis on its own, pixel by pixel
        for j in range(-2, 3):
            for ddx in range(-2, 3):
                for ddy in range(-2, 3):
                    fr = (sx0 * (1 + 0.005 * i), sx0 * (1 + 0.005 * j), dx0 + ddx, dy0 + ddy)
                    v = score(fr)
                    if v > best[0]:
                        best = (v, fr)
    return best[1]


def _fit(pic, land, stretch):
    from PIL import Image, ImageChops, ImageOps, ImageStat
    sea = ImageOps.invert(land)

    def score(p, lm, sm, frame):
        # how much lighter the picture is on the map's land than on its sea, summed over the
        # map's place and set against its size (a cross-correlation of the land mask)
        a, b = _place(lm, frame, p.size), _place(sm, frame, p.size)
        na, nb = ImageStat.Stat(a).sum[0] / 255, ImageStat.Stat(b).sum[0] / 255
        if na < 50 or nb < 50:
            return -1e18
        la = ImageStat.Stat(ImageChops.multiply(p, a)).sum[0]
        lb = ImageStat.Stat(ImageChops.multiply(p, b)).sum[0]
        n = na + nb
        if n < 0.6 * p.width * p.height:
            return -1e18                                   # the map covers most of the picture
        q = squares[p.size]
        sq = (ImageStat.Stat(ImageChops.multiply(q, a)).sum[0] + ImageStat.Stat(ImageChops.multiply(q, b)).sum[0])
        m = (la + lb) / n
        var = sq * 255.0 / n - m * m
        if var <= 0:
            return -1e18
        # Pearson's r of the picture's brightness and the land mask over the part the map covers
        return abs(la / na - lb / nb) * (na * nb) ** 0.5 / n / var ** 0.5
    # coarse: a quarter of the size, every scale and place
    k = 4
    small = pic.resize((max(1, pic.width // k), max(1, pic.height // k)), Image.BILINEAR)
    squares = {p.size: ImageChops.multiply(p, p) for p in (pic, small)}
    W, H = land.size
    base = min(pic.width / W, pic.height / H)
    best = (score(pic, land, sea, stretch), stretch)
    scales = [base * (0.9 + 0.03 * i) for i in range(24)]
    coarse = (-1, None)
    for sc in scales:
        w, h = W * sc / k, H * sc / k
        xs = range(int(min(0, small.width - w)) - 3, int(max(0, small.width - w)) + 4)
        ys = range(int(min(0, small.height - h)) - 3, int(max(0, small.height - h)) + 4)
        for dx in xs:
            for dy in ys:
                v = score(small, land, sea, (sc / k, dx, dy))
                if v > coarse[0]:
                    coarse = (v, (sc, dx * k, dy * k))
    if coarse[1]:
        sc0, dx0, dy0 = coarse[1]
        for i in range(-4, 5):
            sc = sc0 * (1 + 0.005 * i)
            for dx in range(dx0 - 5, dx0 + 6):
                for dy in range(dy0 - 5, dy0 + 6):
                    v = score(pic, land, sea, (sc, dx, dy))
                    if v > best[0] * 1.02:                  # the plain stretch unless clearly worse
                        best = (v, (sc, dx, dy))
    return best[1]


def _region_mask(mod, campaign, regions, size):
    """An L image of `size`: 255 on these regions' land, map_regions.tga laid where the
    map lies in the select pictures (select_frame)."""
    img = mod.region_map(campaign)
    info = mod.regions(campaign)
    cols = {info[r]["colour"] for r in regions if r in info}
    mask = _map_mask(mod, campaign, lambda c: c in cols)
    px = mask.load()
    # the town (black) and port (white) pixels are the region's land too - else a hole at each town
    from .mapedit import ports
    towns, harbours = mod.city_tiles(campaign), ports(mod, campaign)
    for r in regions:
        for xy in (towns.get(r), harbours.get(r)):
            if xy:
                px[xy[0], img.height - 1 - xy[1]] = 255
    frame = select_frame(mod, campaign, size) or (size[0] / img.width, size[1] / img.height, 0, 0)
    return _place(mask, frame, size)


def draw_select_map(mod, campaign, regions, colour):
    """Pillow RGB image: the background with the land of these regions filled with the colour -
    a solid fill (the user: see-through looked poor), the dark border lines between regions kept
    and a thin dark outline round the land; None when the campaign has no background to start
    from (or Pillow is missing)."""
    got = select_background(mod, campaign)
    if not got:
        return None
    from PIL import Image, ImageChops, ImageFilter
    bg, _ = got
    mask = _region_mask(mod, campaign, regions, bg.size)
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(3)), mask)      # just outside the land
    soft = mask.filter(ImageFilter.GaussianBlur(0.4))                             # no jagged steps
    m, e, lum = _pixels(soft), _pixels(edge), _pixels(bg.convert("L"))
    out = _pixels(bg)
    fill = tuple(max(0, min(255, int(c))) for c in colour)
    dark = tuple(int(c * 0.35) for c in fill)
    for i in range(len(out)):
        a = m[i]
        if a:
            want = dark if lum[i] < 70 else fill          # the picture's own border lines stay
            k = a / 255.0
            o = out[i]
            out[i] = tuple(int(round(o[j] * (1 - k) + want[j] * k)) for j in range(3))
        elif e[i]:
            o = out[i]
            out[i] = tuple(int(round(o[j] * 0.45 + dark[j] * 0.55)) for j in range(3))
    res = Image.new("RGB", bg.size)
    res.putdata(out)
    return res


def image_tga(im, like=None):
    """A Pillow image as TGA bytes in the depth of `like` (a TGA file: 24 or 32 bit),
    uncompressed, rows bottom-up as the game's own."""
    import io
    info = tga_info(like) if like else None
    mode = "RGB" if info and info[2] == 24 else "RGBA"
    buf = io.BytesIO()
    im.convert(mode).save(buf, format="TGA", rle=False, orientation=-1)
    return buf.getvalue()


def future(plan, campaign):
    """The mod as it will be once the plan is written, for drawing: map_regions.tga and
    descr_regions.txt as the plan leaves them (new regions, painted borders); the
    background learnt from the files on disk."""
    from .moddata import ModData
    from .tga import read_tga_bytes
    mod = plan.mod
    fut = ModData(mod.data)
    rp = mod.campaign_file(campaign, "map_regions.tga")
    if rp in plan.binaries:
        fut._cache[("map", campaign)] = read_tga_bytes(plan.binaries[rp], rp)
    dr = mod.campaign_file(campaign, "descr_regions.txt")
    if dr in plan.files:
        fut._cache[dr] = plan.files[dr]
    fut._cache[("select_bg", campaign)] = select_background(mod, campaign)
    fut._cache[("select_frame", campaign)] = select_frame(mod, campaign)     # where the map lies: from disk too
    return fut


def write_select_map(plan, campaign, faction, regions, colour):
    """map_<faction>.tga drawn from its regions (a note says so), on the map as the plan
    leaves it; False when the campaign has no maps to learn the background from."""
    mod = plan.mod
    im = draw_select_map(future(plan, campaign), campaign, regions, tuple(colour))
    if im is None:
        return False
    target = map_name(mod.campaign_dir(campaign), faction)
    _, like = select_background(mod, campaign)
    plan.binary(target, image_tga(im, like))
    plan.notes.append((mod.rel(target), "campaign-select map drawn: %d region(s) lit in %d %d %d" % (
        (len(regions),) + tuple(colour))))
    return True


# ---------------------------------------------------------------------------
# Writing: pictures replaced by hand, the campaign-select map drawn
# ---------------------------------------------------------------------------
def replace_picture(plan, src, target, like=None):
    """src (PNG, JPG, TGA...) written over target in the size and depth of `like`
    (the file it replaces, or the template's picture it is copied from)."""
    from PIL import Image
    info = picture_info(like) if like else None
    im = Image.open(src)
    size = info[:2] if info else None
    if size and im.size != tuple(size):
        im = im.resize(tuple(size), Image.LANCZOS)
    dds = target.lower().endswith(".dds")
    plan.binary(target, image_dds(im, like) if dds else image_tga(im, like))
    what = ""
    if info:
        what = " (%d x %d, %s)" % (info[0], info[1], ("DDS " + info[2]) if dds else "%d-bit" % info[2])
    plan.notes.append((plan.mod.rel(target), "picture replaced by %s%s" % (os.path.basename(src), what)))


def image_dds(im, like=None):
    """A Pillow image as DDS bytes in the format of `like` (a DDS file: DXT1/3/5 or
    uncompressed) with as many mipmap levels as it has - Rome's .tga.dds textures are DXT5
    with a full chain; a DDS written as TGA inside is a picture the game cannot read."""
    import io
    from PIL import Image
    info = dds_info(like) if like and like.lower().endswith(".dds") else None
    fmt = info[2] if info and info[2] in ("DXT1", "DXT3", "DXT5") else None
    im = im.convert("RGBA")
    want = info[3] if info else 1
    levels, (w, h) = [], im.size
    for k in range(want):
        lw, lh = max(1, w >> k), max(1, h >> k)
        lv = im if k == 0 else im.resize((lw, lh), Image.LANCZOS)
        buf = io.BytesIO()
        if fmt:
            lv.save(buf, format="DDS", pixel_format=fmt)
        else:
            lv.save(buf, format="DDS")
        levels.append(buf.getvalue())
        if lw == 1 and lh == 1:
            break
    head = bytearray(levels[0][:128])
    if len(levels) > 1:
        put = lambda k, v: head.__setitem__(slice(k, k + 4), v.to_bytes(4, "little"))
        get = lambda k: int.from_bytes(head[k:k + 4], "little")
        put(8, get(8) | 0x20000)                       # DDSD_MIPMAPCOUNT
        put(28, len(levels))
        put(108, get(108) | 0x400008)                  # DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
    return bytes(head) + b"".join(lv[128:] for lv in levels)


def colour_on_map(mod, campaign, faction, regions):
    """The colour a faction's land has on its own campaign-select map now (the mean
    of the lit pixels), or None."""
    got = select_background(mod, campaign)
    path = _ci(mod.campaign_dir(campaign), "map_%s.tga" % faction)
    if not got or not path:
        return None
    from PIL import Image
    bg, _ = got
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    if im.size != bg.size:
        return None
    a, b = _pixels(im), _pixels(bg)
    mask = _pixels(_region_mask(mod, campaign, regions, bg.size)) if regions else None
    if mask:                                 # inside its land (the edges and texture average out as drawn)
        pairs = [(p, q) for p, q, k in zip(a, b, mask) if k > 128]
        # land that is not lit at all (the map shows no light there): no colour to learn
        if pairs and sum(abs(p[i] - q[i]) for p, q in pairs for i in range(3)) / len(pairs) < 30:
            return None
        lit = [p for p, _ in pairs]
    else:
        lit = [p for p, q in zip(a, b) if abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) > 60]
    if not lit:
        return None
    n = len(lit)
    return tuple(int(sum(p[i] for p in lit) / n) for i in range(3))


def region_factions(plan, campaign):
    """The factions (owners after the plan) of every region whose land the plan changes:
    painted tiles (the region they go to and the one they come from) and new regions."""
    from .strat import Strat
    regions = plan.opts.get("regions") or {}
    painted = {tuple(k) if not isinstance(k, str) else tuple(int(v) for v in k.split(",")): r
               for k, r in (regions.get("painted") or {}).items()}
    new = regions.get("new") or []
    if not painted and not new:
        return set()
    mod = plan.mod
    img = mod.region_map(campaign)
    by_colour = {v["colour"]: k for k, v in mod.regions(campaign).items()}
    touched = set(painted.values()) | {r["name"] for r in new}
    for xy in painted:
        was = by_colour.get(img.get(*xy)) if 0 <= xy[0] < img.width and 0 <= xy[1] < img.height else None
        if was:
            touched.add(was)
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    owners = Strat(plan.files[sp] if sp in plan.files else mod.load(sp)).owners()
    return {owners[r] for r in touched if owners.get(r) and owners[r] != "slave"}


def redraw_map_changes(plan, campaign):
    """For a run that only changes the map: the select maps of the factions whose land
    changed, in their own colours."""
    if select_background(plan.mod, campaign):
        redraw_others(plan, campaign, region_factions(plan, campaign), force=True)


def redraw_others(plan, campaign, changed_factions, force=False):
    """The campaign-select maps of the other factions whose towns changed (taken
    from them, given to them), in the colour their own map has."""
    from .strat import Strat
    mod = plan.mod
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    if not select_background(mod, campaign):
        return
    before = Strat(mod.load(sp)).owners()
    after = Strat(plan.files[sp]).owners() if sp in plan.files else before
    for fac in sorted(changed_factions):
        if fac == "slave" or not _ci(mod.campaign_dir(campaign), "map_%s.tga" % fac):
            continue
        old = [r for r, o in before.items() if o == fac]
        new = [r for r, o in after.items() if o == fac]
        if sorted(old) == sorted(new) and not force:
            continue
        colour = colour_on_map(mod, campaign, fac, old)
        if not colour:                              # its map shows no light: one from its colours
            from .edit import read_faction
            try:
                colour = default_map_colour(read_faction(mod, campaign, fac).get("primary_colour"))
            except Exception:
                colour = default_map_colour(None)
        write_select_map(plan, campaign, fac, new, colour)


def art_source(pick):
    """The file an Art pick takes its picture from (a pick is a path, or {'src', 'exact', 'link'})."""
    return pick.get("src") if isinstance(pick, dict) else pick


def write_art(plan, faction, rel, pick):
    """One Art pick written to data/rel: the picture made the size and format of the one it
    replaces, or with 'exact' (back to the original) the file's bytes as they are. With
    'link' = [file key, field] the faction's line is pointed at rel (a picture of its own in
    place of one it shared) - the line of this faction only."""
    mod = plan.mod
    target = os.path.join(mod.data, *rel.replace("\\", "/").split("/"))
    src = art_source(pick)
    link = pick.get("link") if isinstance(pick, dict) else None
    line = None
    if link:
        line = next((l for l in picture_links(mod, plan.edit)
                     if l["faction"] == faction and l["key"] == link[0] and l["field"] == link[1]), None)
    like = target if os.path.exists(target) else next(
        (s for s, d in plan.copies if os.path.normcase(d) == os.path.normcase(target)), None)
    if like is None and line is not None:
        got = picture_file(mod.data, line["ref"])        # the picture it shared until now
        like = got[1] if got else None
    if isinstance(pick, dict) and pick.get("exact"):
        with open(src, "rb") as fh:
            plan.binary(target, fh.read())
        plan.notes.append((mod.rel(target), "picture put back as it was (%s)" % mod.rel(src)))
    else:
        replace_picture(plan, src, target, like)
    if line is not None:
        # the path written as the line writes it: x.tga for x.tga.dds, data/ when it had it
        ref = rel
        if rel.lower().endswith(".tga.dds") and not line["ref"].lower().endswith(".dds"):
            ref = rel[:-4]
        if line["ref"].replace("\\", "/").lower().startswith("data/"):
            ref = "data/" + ref
        if ref.lower() != line["ref"].replace("\\", "/").lower():     # (a new faction's own: the clone did it)
            set_picture_ref(plan.edit(line["path"]), line["line"], line["ref"], ref)
            plan.note(plan.files[line["path"]], "%s's %s now %s (was %s)" % (faction, line["field"], ref, line["ref"]))


def apply_opts(plan, campaign, faction, regions, primary, towns_changed):
    """opts['art'] = {path under data: picture to put there}; opts['select_map'] =
    {'on': True, 'colour': [r, g, b]}: only when asked (the Art tab's optional part), the
    campaign-select map is drawn from the faction's towns, and the maps of the factions whose
    land changed follow. Without it every map_<faction>.tga stays as it is (0.9.3: the user wants
    the originals kept unless he asks; a new faction keeps the template's copy)."""
    mod = plan.mod
    for rel, pick in sorted((plan.opts.get("art") or {}).items()):
        if rel.startswith("symbol:"):
            from .symbols import write
            write(plan, faction, rel, art_source(pick))
        else:
            write_art(plan, faction, rel, pick)
    sel = plan.opts.get("select_map") or {}
    if not sel.get("on"):
        return
    from .strat import Strat
    sp = mod.campaign_file(campaign, "descr_strat.txt")
    if sp in plan.files:                            # its land as the plan leaves it (new regions too)
        regions = [r for r, o in Strat(plan.files[sp]).owners().items() if o == faction] or regions
    shaped = region_factions(plan, campaign)        # owners of land that changed hands on the map
    if faction in shaped:
        towns_changed = True
    if shaped - {faction}:
        redraw_others(plan, campaign, shaped - {faction}, force=True)
    if towns_changed:
        # the factions that lost (or got) towns: their maps too, in their own colour
        from .strat import Strat
        sp = mod.campaign_file(campaign, "descr_strat.txt")
        if sp in plan.files:
            before = Strat(mod.load(sp)).owners()
            after = Strat(plan.files[sp]).owners()
            others = {o for r, o in before.items() if after.get(r) != o} | \
                {o for r, o in after.items() if before.get(r) != o}
            redraw_others(plan, campaign, others - {faction})
    target = map_name(mod.campaign_dir(campaign), faction)
    rel = os.path.relpath(target, mod.data).replace("\\", "/")
    if rel in (plan.opts.get("art") or {}):
        return                                              # a picture of its own was given
    colour = sel.get("colour")
    if not colour and not plan.opts.get("_primary_changed", bool(plan.opts.get("primary_colour"))):
        # no colour of its own picked: the light the template's (or its own) map already has
        from .strat import Strat
        src = plan.template
        owned = [st.region for st in (Strat(mod.load(mod.campaign_file(campaign, "descr_strat.txt"))).faction(src)
                                      or type("x", (), {"settlements": []})).settlements]
        colour = colour_on_map(mod, campaign, src, owned)
    colour = tuple(colour or default_map_colour(primary))
    if not write_select_map(plan, campaign, faction, regions, colour) and sel.get("colour"):
        plan.warn(None, "fewer than three campaign-select maps (map_<faction>.tga) in the campaign folder: "
                        "%s's cannot be drawn - replace it by hand" % faction)
