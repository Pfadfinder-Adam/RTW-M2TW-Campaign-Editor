"""Small window settings kept between starts (the legend shown or hidden...), in
faction_tool_settings.json in the tool's folder (log.home()). Never raises: a missing or broken
file means the defaults."""

import json
import os

from . import log

_data = None


def _path():
    h = log.home()
    return os.path.join(h, "faction_tool_settings.json") if h else None


def _load():
    global _data
    if _data is None:
        _data = {}
        p = _path()
        try:
            if p and os.path.exists(p):
                with open(p, encoding="utf-8") as fh:
                    _data = json.load(fh) or {}
        except (OSError, ValueError):
            _data = {}
    return _data


def get(key, default=None):
    return _load().get(key, default)


def put(key, value):
    d = _load()
    d[key] = value
    p = _path()
    if not p:
        return
    try:
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1)
    except OSError:
        pass
