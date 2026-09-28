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
            data = f.read()
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
        path = path or self.path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # a new file replaces the old one, never written into it: in a mod made
        # of hard links the old file may be shared with the base mod
        tmp = path + ".faction_tool_tmp"
        with open(tmp, "wb") as f:
            f.write(self.dump())
        os.replace(tmp, path)


def strip_comment(line):
    """The line without a ';' comment (the game's comment marker)."""
    i = line.find(";")
    return line if i < 0 else line[:i]


def tokens(line):
    """Whitespace/comma separated words of a line, comment removed."""
    return strip_comment(line).replace(",", " ").split()
