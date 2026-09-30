"""The one guard every write of a Plan (and every Restore) goes through: a file may be written, copied, created or
removed only inside the loaded mod's folder or its game's folder - never elsewhere, whatever a crafted pack, add-on
zip or backup manifest names ('../', another drive, a link that leads out). A path outside is refused before
anything is written, and logged. The tool's own folder (settings, log, add-ons) and files the user picks in a save
dialog are written by their own code, not through here."""

import os


class OutsideError(ValueError):
    pass


def _real(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def inside(path, root):
    """True when path (links followed) is root or lies under it."""
    try:
        p, r = _real(path), _real(root)
        return os.path.commonpath([p, r]) == r
    except ValueError:                      # another drive on Windows
        return False


def roots_of(mod):
    """Where a Plan on mod may write: the mod's folder (the parent of data/) and its game's folder - only a real
    game folder (its exe there), never whatever folder happens to hold the mod."""
    roots = [os.path.dirname(os.path.abspath(mod.data))]
    try:
        from .newmod import game_of, is_game
        game = game_of(mod.data)
        if game and is_game(game):
            roots.append(game)
    except Exception:
        pass
    return roots


def check(paths, roots, what="write"):
    """Raise OutsideError naming every path of paths that lies outside all roots (nothing is written then)."""
    bad = [p for p in paths if not any(inside(p, r) for r in roots)]
    if bad:
        from . import log
        log.write("REFUSED %s outside the mod / game folder: %s" % (what, ", ".join(bad)))
        raise OutsideError("refused - these lie outside the mod and game folders, so nothing was written: %s"
                           % ", ".join(bad[:5]) + (" ..." if len(bad) > 5 else ""))
