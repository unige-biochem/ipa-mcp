"""The site's pages: ``site/<name>.md`` in the library, as ``publish`` wrote
them (the text of the SharePoint page, without its header)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .library import page_url

HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
MARKER = re.compile(r"<!--\s*(\w+):\s*([^>]*?)\s*-->")


@dataclass
class Section:
    level: int
    title: str
    text: str

    @property
    def anchor(self) -> str:
        a = re.sub(r"[^\w\s-]", "", self.title.lower().replace("—", "-"))
        return re.sub(r"\s+", "-", a.strip())


def list_pages(lib: Path) -> list[str]:
    return sorted(p.stem for p in (lib / "site").glob("*.md"))


def page_path(lib: Path, name: str) -> Path | None:
    name = name.strip().split("/")[-1]
    for suffix in (".aspx", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    p = lib / "site" / f"{name}.md"
    return p if p.is_file() else None


def read(lib: Path, name: str) -> str | None:
    p = page_path(lib, name)
    return p.read_text(encoding="utf-8") if p else None


def sections(text: str) -> list[Section]:
    """Split a page at its headings. The text before the first heading is a
    section titled ``(top)``: the summary line, the picture, the contents."""
    out: list[Section] = []
    level, title, buf = 0, "(top)", []
    in_code = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        m = None if in_code else HEADING.match(line)
        if m:
            out.append(Section(level, title, "\n".join(buf).strip()))
            level, title, buf = len(m.group(1)), m.group(2), []
        else:
            buf.append(line)
    out.append(Section(level, title, "\n".join(buf).strip()))
    return [s for s in out if s.text or s.level]


def find_section(secs: list[Section], wanted: str) -> list[Section]:
    """A section by title (case-insensitive substring) or anchor, with its
    subsections."""
    w = wanted.lower().strip("# ")
    for i, s in enumerate(secs):
        if w in s.title.lower() or w == s.anchor:
            block = [s]
            for t in secs[i + 1:]:
                if t.level <= s.level:
                    break
                block.append(t)
            return block
    return []


def outline(secs: list[Section]) -> list[str]:
    return [f"{'#' * s.level} {s.title}" if s.level else s.title for s in secs]


def markers(text: str) -> dict[str, str]:
    """``<!-- list: slug -->`` and the other machine markers on a page."""
    return {m.group(1): m.group(2) for m in MARKER.finditer(text)}


def summary(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith(("!", "<!--", "-", "#", "|")):
            return line
    return ""


def search(lib: Path, pattern: str, max_hits: int = 40, extra: list[Path] = ()) -> list[dict]:
    """Regex search, case-insensitive, over every page and the given extra
    files (the data READMEs); each hit with its page, nearest heading and line."""
    rx = re.compile(pattern, re.IGNORECASE)
    files = sorted((lib / "site").glob("*.md")) + list(extra)
    hits: list[dict] = []
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        is_page = f.parent.name == "site"
        heading = ""
        for n, line in enumerate(lines, 1):
            m = HEADING.match(line)
            if m:
                heading = m.group(2)
            if rx.search(line):
                hits.append({
                    "page": f.stem if is_page else f.relative_to(lib).as_posix(),
                    "heading": heading, "line": n, "text": line.strip()[:300],
                    "url": page_url(f.stem) if is_page else None,
                })
                if len(hits) >= max_hits:
                    return hits
    return hits
