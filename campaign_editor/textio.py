"""Reading and writing the game's text files without changing their encoding.

Rome: Total War data files come in two flavours:
  * descr_*/export_* files: single-byte text (ASCII / Windows-1252), CRLF or LF;
  * data/text/*.txt string tables: UTF-16 LE with a BOM, usually CRLF;
  * REX's data/text/english/*.txt: UTF-8 without a BOM.

A TextFile splits on "\\n" only, so every line keeps its own "\\r" (some files
mix CRLF and LF). Writing joins with "\\n" again: an untouched line, and the
file as a whole when nothing changed, stays byte-identical.

Lines handed out by .text(i) have the "\\r" removed; lines added through
.make(text) get the file's usual ending.
"""

import codecs
import os
import stat
import time


class WriteError(OSError):
    """A file the system would not let the tool write, said in plain words."""


def make_writable(path):
    """Take a file's read-only mark off (Windows' Read-only box; mods unpacked from some archives or copied from a
    disc carry it, and Windows then refuses to replace or remove the file). True when it was read-only."""
    try:
        mode = os.stat(path).st_mode
    except OSError:
        return False
    if mode & stat.S_IWRITE:
        return False
    try:
        os.chmod(path, mode | stat.S_IWRITE)
    except OSError:
        return False
    return True


def readonly(path):
    """True when an existing file carries the read-only mark."""
    try:
        return not os.stat(path).st_mode & stat.S_IWRITE
    except OSError:
        return False


def refused(path, err):
    """Plain words for a file the system would not let the tool write or remove."""
    where = os.path.abspath(path)
    tips = ["close the game and any program that has the file open (a text editor, a pack tool, an antivirus "
            "scan, a cloud folder such as OneDrive syncing it)"]
    if "program files" in where.lower():
        tips.append("the game lies under Program Files, where Windows lets only an administrator write - start "
                    "the editor with 'Run as administrator' or move the game's library out of Program Files")
    return "%s could not be written - the system refused (%s). Try: %s; then Apply again." % (
        where, getattr(err, "strerror", None) or err, "; or ".join(tips))


WIN_DISK_FULL = (112, 39)               # ERROR_DISK_FULL, ERROR_HANDLE_DISK_FULL
WIN_TOO_LONG = (206,)                    # ERROR_FILENAME_EXCED_RANGE
WIN_REFUSED = (5, 32, 33)                # access denied, in use by another program, locked
WIN_MAX_PATH = 259


def plain(path, err):
    """Plain words for a file the system would not write, or None when the error is not one of those known: refused
    (read-only, held by a program, no rights), the disk full, a path longer than Windows takes."""
    import errno
    code, win = getattr(err, "errno", None), getattr(err, "winerror", None)
    where = os.path.abspath(path)
    if code == errno.ENOSPC or win in WIN_DISK_FULL:
        drive = os.path.splitdrive(where)[0] or os.path.dirname(where)
        return ("%s could not be written - the disk is full (%s). Free some room on %s, then Apply again."
                % (where, getattr(err, "strerror", None) or err, drive))
    too_long = ("%s could not be written - the path is too long for the system (%d characters; Windows takes 260). "
                "Move the game or the mod into a shorter folder (like C:\\Games), then Apply again."
                % (where, len(where)))
    if code == errno.ENAMETOOLONG or win in WIN_TOO_LONG:
        return too_long
    if isinstance(err, PermissionError) or win in WIN_REFUSED or code in (errno.EACCES, errno.EPERM):
        return refused(path, err)
    if os.name == "nt" and len(where) > WIN_MAX_PATH:  # long paths off: Windows says 'path not found' (WinError 3)
        return too_long
    return None


def _retrying(do, path):
    """Run do() (a replace or a remove of path); when the system refuses: take the read-only mark off and try again,
    and wait a little for a program that holds the file for a moment (about 2.5 s in all). Raises WriteError."""
    last = None
    for wait in (0, 0.1, 0.2, 0.4, 0.8, 1.0):
        if wait:
            time.sleep(wait)
        try:
            return do()
        except PermissionError as e:              # WinError 5 (access denied) / 32 (in use) / EACCES / EPERM
            last = e
            make_writable(path)
        except OSError as e:
            if getattr(e, "winerror", None) in (5, 32, 33):
                last = e
                continue
            raise
    raise WriteError(refused(path, last)) from last


def replace_file(path, data):
    """Write data as the file path: into a temp file beside it, then renamed over the old file - a new file, never
    written into the old one (in a mod made of hard links the old file may be shared with the base mod). A file
    marked read-only is made writable; a file held by another program for a moment is tried again. Raises
    WriteError in plain words when the system still refuses; the temp file never stays behind."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".CampaignEditor_tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        _retrying(lambda: os.replace(tmp, path), path)
    except WriteError:
        raise
    except OSError as e:                          # the temp file itself refused (no rights, disk full, path too long)
        words = plain(path, e)
        if words is None:
            raise
        raise WriteError(words) from e
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def remove_file(path):
    """Remove a file (a read-only one too); WriteError in plain words when the system refuses."""
    _retrying(lambda: os.remove(path), path)


def _utf8(data):
    """UTF-8 with no BOM: non-ASCII bytes that decode as UTF-8 (a Windows-1252 file
    almost never does - an accented letter alone is not a valid UTF-8 sequence)."""
    if max(data, default=0) < 0x80:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


class TextFile:
    def __init__(self, path, raw_lines, encoding, bom):
        self.path = path
        self.raw = raw_lines            # lines including a trailing "\r" where the file had one
        self.encoding = encoding
        self.bom = bom
        crlf = sum(1 for l in raw_lines if l.endswith("\r"))
        self.cr = "\r" if crlf * 2 >= len(raw_lines) and crlf > 0 else ""

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            return cls.from_bytes(path, f.read())

    @classmethod
    def from_bytes(cls, path, data):
        """A file's bytes (as on disk, or a plan's new content) read the way load() reads them."""
        bom = b""
        if data.startswith(codecs.BOM_UTF16_LE):
            encoding, bom, data = "utf-16-le", codecs.BOM_UTF16_LE, data[2:]
        elif data.startswith(codecs.BOM_UTF16_BE):
            encoding, bom, data = "utf-16-be", codecs.BOM_UTF16_BE, data[2:]
        elif data.startswith(codecs.BOM_UTF8):
            encoding, bom, data = "utf-8", codecs.BOM_UTF8, data[3:]
        elif len(data) > 1 and data[1:2] == b"\x00" and data[0:1] != b"\x00":
            encoding = "utf-16-le"
        elif _utf8(data):
            encoding = "utf-8"          # REX's data/text/english tables: UTF-8 without a BOM
        else:
            encoding = "latin-1"        # single-byte: a byte-exact round trip for any file
        return cls(path, data.decode(encoding).split("\n"), encoding, bom)

    # ---- access ----
    def __len__(self):
        return len(self.raw)

    def text(self, i):
        l = self.raw[i]
        return l[:-1] if l.endswith("\r") else l

    def texts(self):
        return [self.text(i) for i in range(len(self.raw))]

    def make(self, text):
        """A new raw line with the file's usual ending."""
        return text + self.cr

    def set(self, i, text):
        """Replace line i's text, keeping its own ending."""
        cr = "\r" if self.raw[i].endswith("\r") else ""
        self.raw[i] = text + cr

    def insert(self, i, texts):
        self.raw[i:i] = [self.make(t) for t in texts]

    def insert_raw(self, i, raw_lines):
        self.raw[i:i] = list(raw_lines)

    def delete(self, start, end):
        del self.raw[start:end]

    # ---- output ----
    def dump(self):
        return self.bom + "\n".join(self.raw).encode(self.encoding)

    def save(self, path=None):
        # a new file replaces the old one, never written into it: in a mod made
        # of hard links the old file may be shared with the base mod
        replace_file(path or self.path, self.dump())


def strip_comment(line):
    """The line without a ';' comment (the game's comment marker)."""
    i = line.find(";")
    return line if i < 0 else line[:i]


def tokens(line):
    """Whitespace/comma separated words of a line, comment removed."""
    return strip_comment(line).replace(",", " ").split()
