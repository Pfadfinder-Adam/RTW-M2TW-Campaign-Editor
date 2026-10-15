"""The text of a release page (release.yml): this version's part of CHANGELOG.md, laid out so nobody scrolls to the
bottom to download - GitHub always puts the Assets list there:
  1. a download link to the exe of this release;
  2. the version's '### In short' part (a few lines: the big things added, fixed, changed);
  3. everything else of the version in a fold, closed at first.
Run: python .github/release_notes.py <version> <owner/repo>  ->  release_notes.md"""

import re
import sys

EXE = "RTW-M2TW-Campaign-Editor.exe"
SHORT = "### In short"


def part(changelog, version):
    """The lines under '## <version>' up to the next '## ' heading."""
    head = re.compile(r"## \[?v?%s\]?(\s|$)" % re.escape(version))
    out, inside = [], False
    for line in changelog.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = bool(head.match(line))
            continue
        if inside:
            out.append(line)
    return out


def notes(changelog, version, repo):
    version = version.strip().lstrip("v")
    lines = part(changelog, version)
    if not "\n".join(lines).strip():
        raise ValueError("CHANGELOG.md has no '## %s' part with text - write it first" % version)
    short, rest, in_short = [], [], False
    for line in lines:
        if line.startswith("### "):
            in_short = line.strip() == SHORT
            if in_short:
                continue
        (short if in_short else rest).append(line)
    url = "https://github.com/%s/releases/download/v%s/%s" % (repo, version, EXE)
    out = ["### [⬇ Download %s](%s)" % (EXE, url), ""]
    if "\n".join(short).strip():
        out += ["\n".join(short).strip(), ""]
    out += ["<details>", "<summary><b>Everything in this release</b> (click to open)</summary>", "",
            "\n".join(rest).strip(), "", "</details>"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    with open("CHANGELOG.md", encoding="utf-8") as fh:
        text = notes(fh.read(), sys.argv[1], sys.argv[2])
    with open("release_notes.md", "w", encoding="utf-8") as fh:
        fh.write(text)
    # the Windows runner's console is cp1252: a character it lacks (a ✕) stopped the release here (0.33.0)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
