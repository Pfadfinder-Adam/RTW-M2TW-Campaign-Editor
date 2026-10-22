"""The editor's themes as files, as Obsidian's (the user, 2026-10-22: 'save it all, load it all - Obsidian has a
whole browser of themes, install any one'). A theme is the whole look in one file: Light or Dark under it, its own
colours (theme.NAMES / theme.COLOURED keys -> '#rrggbb') and a font for every window - theme.json

    {"name": "Roman parchment", "by": "...", "base": "light", "colours": {...}, "font": ["", 0]}

in a folder of its own with a picture of the editor in it (preview.png). The editor's own themes are assets/themes
(a .json each, no picture: the gallery draws their colours); the modder's are CampaignEditor_themes/<name>/. One
.zip (theme.json + preview.png) is what is sent to a friend or to Discord and what Import takes (a bare .json too).

Pure Python, no Tk."""

import json
import os
import re
import zipfile

from . import log

FOLDER = "_themes"
FILE = "theme.json"
PICTURE = "preview.png"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def own_dir():
    h = log.home()
    return os.path.join(h, log.SHORT + FOLDER) if h else None


def builtin_dir():
    from .addons import assets_dir
    return os.path.join(os.path.dirname(assets_dir()), "themes")


def clean(data, name=None):
    """A theme read from anywhere made safe: only its name, author, base, '#rrggbb' colours and a font; None when it
    is not a theme."""
    if not isinstance(data, dict):
        return None
    colours = data.get("colours")
    if not isinstance(colours, dict):
        return None
    font = data.get("font")
    if isinstance(font, (list, tuple)) and len(font) >= 2:
        try:
            font = [str(font[0] or "")[:64], max(0, min(48, int(font[1] or 0)))]
        except (TypeError, ValueError):
            font = None
    else:
        font = None
    return {"name": str(data.get("name") or name or "Theme")[:60].strip() or "Theme",
            "by": str(data.get("by") or "")[:60],
            "base": "dark" if data.get("base") == "dark" else "light",
            "colours": {str(k)[:40]: v for k, v in colours.items() if isinstance(v, str) and _HEX.match(v)},
            "font": font if font and any(font) else None}


def folder_name(name):
    """A folder name for a theme's name (letters, digits, spaces, - and _ kept)."""
    keep = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
    return keep or "Theme"


def read(path):
    """A theme from its theme.json, a folder holding one, or a bare .json (None when it is none)."""
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    try:
        with open(path, encoding="utf-8") as fh:
            got = clean(json.load(fh), os.path.splitext(os.path.basename(path))[0])
    except (OSError, ValueError):
        return None
    if got is not None:
        got["path"] = path
        pic = os.path.join(os.path.dirname(path), PICTURE)
        got["picture"] = pic if os.path.basename(path) == FILE and os.path.isfile(pic) else None
        got["own"] = False
    return got


def available():
    """Every theme: the editor's own first, then the modder's (a modder's one of the same name wins) -
    [{'name', 'by', 'base', 'colours', 'font', 'path', 'picture', 'own'}]."""
    out = {}
    folder = builtin_dir()
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        names = []
    for n in names:
        if n.endswith(".json"):
            t = read(os.path.join(folder, n))
            if t:
                out[t["name"].lower()] = t
    folder = own_dir()
    try:
        names = sorted(os.listdir(folder)) if folder else []
    except OSError:
        names = []
    for n in names:
        t = read(os.path.join(folder, n))
        if t:
            t["own"] = True
            out[t["name"].lower()] = t
    return list(out.values())


def save(name, by, base, colours, font, picture=None, folder=None):
    """The look now kept as the modder's theme (picture: a PIL picture of the editor, or None) -> its folder, or
    None when it could not be written."""
    folder = folder or own_dir()
    if not folder:
        return None
    data = clean({"name": name, "by": by, "base": base, "colours": colours, "font": font})
    where = os.path.join(folder, folder_name(data["name"]))
    try:
        os.makedirs(where, exist_ok=True)
        with open(os.path.join(where, FILE), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
        if picture is not None:
            picture.save(os.path.join(where, PICTURE))
    except Exception:                                        # noqa: BLE001 - a full disk, a picture that fails
        return None
    return where


def export(theme, path):
    """One theme into a .zip (theme.json + its picture) to send; False when it could not be written."""
    data = {k: theme[k] for k in ("name", "by", "base", "colours", "font")}
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(FILE, json.dumps(data, indent=1, ensure_ascii=False))
            if theme.get("picture") and os.path.isfile(theme["picture"]):
                z.write(theme["picture"], PICTURE)
        return True
    except OSError:
        return False


def import_file(path, folder=None):
    """A theme sent by someone (.zip or .json) put among the modder's -> (its name, None) or (None, why not)."""
    folder = folder or own_dir()
    if not folder:
        return None, "the editor has no folder of its own to keep it in"
    picture = None
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                inner = next((n for n in names if os.path.basename(n) == FILE), None) or \
                    next((n for n in names if n.endswith(".json")), None)
                if inner is None:
                    return None, "there is no theme.json in it"
                data = json.loads(z.read(inner).decode("utf-8"))
                pic = next((n for n in names if os.path.basename(n) == PICTURE), None)
                if pic is not None and z.getinfo(pic).file_size < 8 * 1024 * 1024:
                    picture = z.read(pic)
        else:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as e:
        return None, "it could not be read (%s)" % e
    theme = clean(data, os.path.splitext(os.path.basename(path))[0])
    if theme is None:
        return None, "it is not a theme of the editor (no colours in it)"
    where = save(theme["name"], theme["by"], theme["base"], theme["colours"], theme["font"], folder=folder)
    if where is None:
        return None, "it could not be written into %s" % folder
    if picture is not None and picture[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            with open(os.path.join(where, PICTURE), "wb") as fh:
                fh.write(picture)
        except OSError:
            pass
    return theme["name"], None


def delete(theme):
    """One of the modder's themes taken away (the editor's own stay)."""
    if not theme.get("own"):
        return False
    where = os.path.dirname(theme["path"])
    try:
        for n in os.listdir(where):
            os.remove(os.path.join(where, n))
        os.rmdir(where)
        return True
    except OSError:
        return False


__all__ = ["available", "read", "save", "export", "import_file", "delete", "clean", "own_dir", "builtin_dir"]
