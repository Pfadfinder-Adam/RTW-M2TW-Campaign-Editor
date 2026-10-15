"""The games' binary sprite sheets: Rome's ui/*.rsd (version 5) and Medieval II's ui/*.sd (version 6) - the lists
that say where each interface picture (a faction's logo, a button) lies on its page (ui/<culture>/interface/*.tga).
The plain exes read only these; REX / M2EX can read the .sd.xml text mirrors instead (symbols.sprite_mode).

Decoded 2026-10-15 from the vanilla files of both games (modding_knowledge.md 'BINARY SPRITE SHEETS'), all
little-endian, a string = u32 length + its bytes:
  header   u32 version (5 / 6), u32 pages, u32 sprites; version 5: the title string
  page     version 5: a guide picture's path; the page file; u8 0; u32 w, u32 h; u32 mask length (w * h // 8 + 1);
           the mask: a bit a pixel, row by row, the lowest bit first, set where the page's alpha is over 127
  sprite   its name; u16 page, u16 x0, u16 x1, u16 y0, u16 y1 (the last pixel, inside), u16 flag, u32 (kept as read)
read() and write() give back the same bytes; a new page and sprite are added at the end (a faction's own logo)."""

import struct


class Sheet:
    def __init__(self, version, title, pages, sprites):
        self.version, self.title, self.pages, self.sprites = version, title, pages, sprites

    def page_index(self, page):
        low = page.lower()
        return next((i for i, p in enumerate(self.pages) if p["file"].lower() == low), None)

    def find(self, name):
        """{'page' (its file), 'box' (x, y, w, h)} of a sprite, or None."""
        for s in self.sprites:
            if s["name"] == name:
                return {"page": self.pages[s["page"]]["file"], "box": box(s)}
        return None

    def boxes(self):
        """[(page file, [(sprite name, (x, y, w, h))])] in the sheet's order (the shape symbols reads the xml in)."""
        out = [(p["file"], []) for p in self.pages]
        for s in self.sprites:
            if s["page"] < len(out):
                out[s["page"]][1].append((s["name"], box(s)))
        return out


def box(s):
    return (s["x0"], s["y0"], s["x1"] - s["x0"] + 1, s["y1"] - s["y0"] + 1)


def read(data):
    o = [0]

    def u32():
        v = struct.unpack_from("<I", data, o[0])[0]
        o[0] += 4
        return v

    def text():
        n = u32()
        v = data[o[0]:o[0] + n].decode("latin-1")
        o[0] += n
        return v

    version, npages, nsprites = u32(), u32(), u32()
    if version not in (5, 6):
        raise ValueError("not a sprite sheet of the games (version %d)" % version)
    title = text() if version == 5 else None
    pages = []
    for _ in range(npages):
        guide = text() if version == 5 else None
        name = text()
        flag = data[o[0]]
        o[0] += 1
        w, h, n = u32(), u32(), u32()
        pages.append({"guide": guide, "file": name, "flag": flag, "w": w, "h": h, "mask": data[o[0]:o[0] + n]})
        o[0] += n
    sprites = []
    for _ in range(nsprites):
        name = text()
        page, x0, x1, y0, y1, flag, tail = struct.unpack_from("<HHHHHHI", data, o[0])
        o[0] += 16
        sprites.append({"name": name, "page": page, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "flag": flag,
                        "tail": tail})
    if o[0] != len(data):
        raise ValueError("the sprite sheet has %d bytes after its last sprite" % (len(data) - o[0]))
    return Sheet(version, title, pages, sprites)


def _text(s):
    b = s.encode("latin-1")
    return struct.pack("<I", len(b)) + b


def write(sheet):
    out = [struct.pack("<III", sheet.version, len(sheet.pages), len(sheet.sprites))]
    if sheet.version == 5:
        out.append(_text(sheet.title))
    for p in sheet.pages:
        if sheet.version == 5:
            out.append(_text(p["guide"]))
        out.append(_text(p["file"]) + bytes([p["flag"]]) + struct.pack("<III", p["w"], p["h"], len(p["mask"])))
        out.append(bytes(p["mask"]))
    for s in sheet.sprites:
        out.append(_text(s["name"]) + struct.pack("<HHHHHHI", s["page"], s["x0"], s["x1"], s["y0"], s["y1"],
                                                  s["flag"], s["tail"]))
    return b"".join(out)


def mask(im):
    """The page's click mask: a bit a pixel, row by row, lowest bit first, set where alpha > 127."""
    w, h = im.size
    alpha = im.convert("RGBA").getchannel("A").tobytes()
    out = bytearray(w * h // 8 + 1)
    for k, a in enumerate(alpha):
        if a > 127:
            out[k >> 3] |= 1 << (k & 7)
    return bytes(out)


def set_page(sheet, page, im):
    """The page `page` with the picture im (its size and mask) - added at the end when the sheet has none. Returns
    its index."""
    i = sheet.page_index(page)
    w, h = im.size
    if i is None:
        guide = None
        if sheet.version == 5:
            # the guide path of the sheet's first page, with this page's name (the game does not open it)
            first = sheet.pages[0]["guide"] if sheet.pages else "\\romans\\data\\ui\\roman\\interface\\guides\\"
            head = first[:first.rfind("\\") + 1]
            guide = head + page.rsplit(".", 1)[0] + "_guides.tga"
        sheet.pages.append({"guide": guide, "file": page, "flag": 0, "w": w, "h": h, "mask": mask(im)})
        return len(sheet.pages) - 1
    sheet.pages[i].update(w=w, h=h, mask=mask(im))
    return i


def set_sprite(sheet, name, page, x, y, w, h):
    """The sprite `name` on page index `page` at (x, y, w, h) - moved there, or added at the end."""
    s = next((s for s in sheet.sprites if s["name"] == name), None)
    if s is None:
        s = {"name": name, "flag": 1, "tail": 0}
        sheet.sprites.append(s)
    s.update(page=page, x0=x, x1=x + w - 1, y0=y, y1=y + h - 1)
