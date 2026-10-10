"""Small window settings kept between starts (the legend shown or hidden...), in
CampaignEditor_settings.json in the editor's own folder beside the exe (log.home(); older versions' faction_tool_settings.json is moved
in once). Never raises: a missing or broken
file means the defaults. A value of another kind than this version keeps there (written by a newer or an older
version) reads as not there - going back to an older editor never fails on a newer one's settings."""

import json
import os

from . import log

_data = None

# what each key holds (a key ending in '_' is a prefix: editor_list_width_unit ...)
KINDS = {"game": str, "games": list, "campaigns": dict, "mod_data": str, "fixes_declined": dict,
         "reports_seen": dict, "reports_sent": list, "reports_sent_logs": dict, "reports_log_sent_upto": dict,
         "reports_checked_at": (int, float), "report_hide": str, "report_contact": str, "report_url": str,
         "theme": str, "map_look": dict, "banner_grid": str, "map_legend": (bool, int), "art_map_open": (bool, int),
         "level_follows_population": (bool, int), "reports_check": (bool, int), "report_contact_keep": (bool, int),
         "release_check": (bool, int), "release_checked_at": (int, float), "release_latest": dict,
         "editor_list_width_": int, "suggest_units_lo": int, "suggest_units_hi": int, "suggest_upkeep": int}


def _kind(key, default):
    k = KINDS.get(key) or next((v for p, v in KINDS.items() if p.endswith("_") and key.startswith(p)), None)
    if k is None and default is not None:
        if isinstance(default, (list, tuple)):
            k = (list, tuple)
        elif isinstance(default, (bool, int, float)):
            k = (bool, int, float)
        else:
            k = type(default)
    return k


def _path():
    h = log.home()
    return os.path.join(h, log.SETTINGS_NAME) if h else None


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
        if not isinstance(_data, dict):           # not settings this version can read
            _data = {}
    return _data


def get(key, default=None):
    v = _load().get(key, default)
    k = _kind(key, default)
    if v is not None and k is not None and not isinstance(v, k):
        return default
    return v


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
