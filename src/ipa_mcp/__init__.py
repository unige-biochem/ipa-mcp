"""ipa-mcp: the UNIGE Biochemistry imaging site (biochem-ipa) for AI assistants.

A stdio MCP server that reads the user's *synced copy* of the site's library:
the pages (``site/``), the measurements (``data/psf``, ``data/laser-power``)
and the builds (``builds/``). No credentials, no network: what the assistant
sees is what the user's own account can already read. Nothing is written to
the library, and ``private/`` is never read.
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from importlib.metadata import PackageNotFoundError, version as _version
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import pages, records
from .library import (CONFIG, SETUP_HELP, SITE_URL, allowed, find_library, is_library,
                      load_config, page_url, save_config)

try:
    __version__ = _version("ipa-mcp")
except PackageNotFoundError:  # running from a checkout without install
    __version__ = "0.0.0"

DATA = Path(__file__).with_name("data")
PROTOCOLS = {"laser": "protocol-laser-power", "psf": "protocol-psf"}
DEFAULT_CONTACT = ("Nicolas Chiaruttini, the facility's image-analysis and microscopy support: "
                   f"see {page_url('image-analysis')}#just-ask")


# --------------------------------------------------------------- helpers ---

def _lib() -> Path:
    lib = find_library()
    if lib is None:
        raise RuntimeError(SETUP_HELP)
    return lib


def _contact(lib: Path | None) -> str:
    """The *Just ask* block of the image-analysis page, or a fallback."""
    if lib is None:
        return DEFAULT_CONTACT
    text = pages.read(lib, "image-analysis")
    if not text:
        return DEFAULT_CONTACT
    block = pages.find_section(pages.sections(text), "Just ask")
    return "\n".join(s.text for s in block).strip() or DEFAULT_CONTACT


def _not_measured(what: str, protocol: str, lib: Path, readme: str) -> dict:
    return {
        "found": [],
        "not_measured": True,
        "message": (f"No {what} measurement is on record for that. It can be measured: the protocol is on "
                    f"the site, and the maintainer can do it with you or for you."),
        "protocol_page": page_url(protocol),
        "protocol_file": str(lib / readme),
        "ask": _contact(lib),
    }


def _item(items: dict, id_or_name: str, lab: str | None) -> tuple[str | None, list[dict]]:
    """Resolve an id or a free-text name to one item id, or give candidates."""
    if id_or_name in items:
        return id_or_name, []
    cands = records.find_items(items, id_or_name, lab)
    if len(cands) == 1 or (len(cands) > 1 and cands[0]["score"] > cands[1]["score"]):
        return cands[0]["id"], cands
    return None, cands


def instructions() -> str:
    lib = find_library()
    cfg = load_config()
    tpl = (DATA / "instructions.md").read_text(encoding="utf-8")
    return (tpl.replace("{version}", __version__)
               .replace("{library}", str(lib) if lib else "NOT FOUND - call ipa_status for setup steps")
               .replace("{user}", cfg.get("name") or "unknown - ask once, then ipa_set_user")
               .replace("{lab}", cfg.get("lab") or "unknown")
               .replace("{contact}", _contact(lib))
               .replace("{site}", SITE_URL))


mcp = FastMCP("ipa", instructions=instructions())


# ----------------------------------------------------------------- tools ---

@mcp.tool()
def ipa_status() -> dict:
    """Is the synced library here, how fresh is it, and who is the user? Call
    first when anything fails; it gives the setup steps when the library is missing."""
    lib = find_library()
    cfg = load_config()
    out = {"version": __version__, "site": SITE_URL, "library": str(lib) if lib else None,
           "user": cfg.get("name"), "lab": cfg.get("lab"), "config_file": str(CONFIG)}
    if lib is None:
        out["setup"] = SETUP_HELP
        return out
    reg = lib / "site" / "registry.json"
    newest = max((p.stat().st_mtime for p in (lib / "site").glob("*.md")), default=reg.stat().st_mtime)
    import datetime as dt
    out.update({
        "pages": len(pages.list_pages(lib)),
        "equipment": len(records.registry(lib)),
        "psf_sessions": len({r["session"] for r in records.psf_rows(lib)}),
        "laser_measurements": len(records.laser_rows(lib)),
        "builds": len(records.builds(lib)),
        "pages_last_published": dt.datetime.fromtimestamp(newest).isoformat(timespec="minutes"),
        "note": "The copy is as fresh as OneDrive's last sync; the site itself is the reference.",
    })
    return out


@mcp.tool()
def ipa_set_user(name: str | None = None, lab: str | None = None, library: str | None = None) -> dict:
    """Remember who the user is (name, lab - Aumeier, Dudin, Kaksonen, Kruse, Roux or other)
    and, if auto-detection failed, where their synced library is. Ask the user once, then call this."""
    if library is not None and not is_library(Path(library)):
        raise ValueError(f"{library} is not the synced library: it has no site/registry.json")
    cfg = save_config({"name": name, "lab": lab, "library": library})
    return {"saved": cfg}


@mcp.tool()
def ipa_equipment(lab: str | None = None, kind: str | None = None) -> list[dict]:
    """Every item on the site - microscopes (kind 'scope'), hoods, VM desktops -
    with id, lab, aliases, room, page, objectives, light paths and laser lines.
    Filter by lab and/or kind."""
    lib = _lib()
    out = []
    for slug, it in records.registry(lib).items():
        s = records.item_summary(slug, it)
        if lab and (s["lab"] or "").lower() != lab.lower():
            continue
        if kind and s["kind"] != kind.lower():
            continue
        out.append(s)
    return out


@mcp.tool()
def ipa_find(query: str) -> dict:
    """Which item does the user mean? 'the spinning disc', 'the Nikon scope', 'Dobby'...
    Ranked candidates; the user's lab (from ipa_status) breaks ties. If several labs have
    a match, ask the user which lab rather than guessing."""
    lib = _lib()
    cands = records.find_items(records.registry(lib), query, load_config().get("lab"))
    return {"query": query, "candidates": cands,
            "hint": None if cands else "No match: try ipa_equipment() to list everything."}


@mcp.tool()
def ipa_item(id_or_name: str) -> dict:
    """Everything the site knows about one item, structured: identity, objectives (with
    immersion and NA parsed from the tag), light paths, laser lines, the page's outline,
    where to book it, and which measurements exist (PSF per objective, laser power per line).
    Read a page section with ipa_page for the prose."""
    lib = _lib()
    items = records.registry(lib)
    slug, cands = _item(items, id_or_name, load_config().get("lab"))
    if slug is None:
        return {"ambiguous": True, "candidates": cands}
    s = records.item_summary(slug, items[slug])
    text = pages.read(lib, slug) or ""
    mk = pages.markers(text)
    lists = [v.strip() for v in mk.get("list", "").split(",") if v.strip()] if "list" in mk else None
    psf = records.psf_sessions(lib, records.psf_rows(lib), scope=slug)
    laser = records.laser_series(records.laser_rows(lib), scope=slug)
    s.update({
        "summary": pages.summary(text),
        "outline": pages.outline(pages.sections(text)),
        "subpages": [p for p in pages.list_pages(lib) if p.startswith(slug + "_")],
        "booking": records.booking(slug, lists) if lists or s["kind"] in ("scope", "hood", "vm") else None,
        "psf_measured": sorted({(p["objective"], p["path"], p["date"]) for p in psf}),
        "laser_measured": [(l["line_nm"], l["path"], l["latest"]) for l in laser],
    })
    return s


@mcp.tool()
def ipa_page(name: str, section: str | None = None, max_chars: int = 12000) -> dict:
    """Read a page of the site (Markdown): by id ('dudin_scope_sdc-nikon', 'lab-vms',
    'protocol-psf', 'image-analysis') and optionally one section by title ('Software',
    'Known quirks', 'What is installed'). A long page without a section gives its outline
    and the first part; ask for sections to read the rest. Cite the page's URL in answers."""
    lib = _lib()
    text = pages.read(lib, name)
    if text is None:
        return {"error": f"No page named {name!r}", "pages": pages.list_pages(lib)}
    stem = pages.page_path(lib, name).stem
    secs = pages.sections(text)
    if section:
        block = pages.find_section(secs, section)
        if not block:
            return {"page": stem, "url": page_url(stem), "error": f"No section {section!r}",
                    "outline": pages.outline(secs)}
        body = "\n\n".join(f"{'#' * s.level} {s.title}\n{s.text}" for s in block)
        anchor = block[0].anchor
        return {"page": stem, "url": f"{page_url(stem)}#{anchor}", "section": block[0].title, "text": body}
    out = {"page": stem, "url": page_url(stem), "outline": pages.outline(secs), "text": text[:max_chars]}
    if len(text) > max_chars:
        out["truncated"] = f"{len(text)} characters; read sections for the rest"
    return out


@mcp.tool()
def ipa_search(pattern: str, max_hits: int = 40) -> list[dict]:
    """Search every page and the measurement READMEs (regular expression, case-insensitive).
    Each hit: page, nearest heading, line. Good for 'is napari installed', 'TeamViewer',
    'correction collar', a filter name, a software version."""
    lib = _lib()
    extra = [p for p in (lib / "data").glob("*/README.md")]
    return pages.search(lib, pattern, max_hits, extra)


@mcp.tool()
def ipa_laser_power(scope: str | None = None, line_nm: int | None = None, path: str | None = None) -> dict:
    """Laser power at the sample, per scope, laser line and light path: every measurement
    by date with the change since the first and since the previous one (per cent). Scope is
    an id from ipa_find. With nothing measured for the scope, says so and gives the protocol
    and whom to ask. The protocol compares runs within one light path only."""
    lib = _lib()
    series = records.laser_series(records.laser_rows(lib), scope, line_nm, path)
    if not series:
        return _not_measured("laser-power", PROTOCOLS["laser"], lib, "data/laser-power/README.md")
    return {"found": series, "protocol_page": page_url(PROTOCOLS["laser"]),
            "viewer": next((b["url"] for b in records.builds(lib) if b.get("id") == "laser-power"), None),
            "unit": "mW at the sample, through the scope's 10x dry objective, laser at 100 %"}


@mcp.tool()
def ipa_psf(scope: str | None = None, objective: str | None = None, path: str | None = None) -> dict:
    """PSF measurements: per session (scope, objective tag such as '100x-146-oil', light path,
    date), the FWHM in x, y, z per channel against the expected value, the chromatic shift,
    and the local path of each channel's PSF image (psf_<channel>.tif, for deconvolution).
    Newest first. With nothing measured, says so and gives the protocol and whom to ask."""
    lib = _lib()
    sessions = records.psf_sessions(lib, records.psf_rows(lib), scope, objective, path)
    if not sessions:
        out = _not_measured("PSF", PROTOCOLS["psf"], lib, "data/psf/README.md")
        if scope:
            items = records.registry(lib)
            if scope in items:
                out["objectives_on_this_scope"] = list((items[scope].get("objectives") or {}).keys())
        return out
    return {"found": sessions, "protocol_page": page_url(PROTOCOLS["psf"]),
            "viewer": next((b["url"] for b in records.builds(lib) if b.get("id") == "psf"), None),
            "note": "psf_file is a local path in the synced library; OneDrive downloads it on first read."}


@mcp.tool()
def ipa_builds(kind: str | None = None) -> list[dict]:
    """The courses, presentations and viewers on the site (interactive HTML in the library),
    with title, summary, URL and source repository. kind: course | presentation | viewer."""
    lib = _lib()
    return [b for b in records.builds(lib) if not kind or b.get("kind") == kind]


@mcp.tool()
def ipa_booking(id_or_name: str) -> dict:
    """Where to book an item: its page (the calendar is embedded there), the SharePoint list
    behind it, and the booking directory of the whole site. Booking is per lab: confirm the
    user's lab (ipa_status) before opening another lab's scope."""
    lib = _lib()
    items = records.registry(lib)
    slug, cands = _item(items, id_or_name, load_config().get("lab"))
    if slug is None:
        return {"ambiguous": True, "candidates": cands}
    mk = pages.markers(pages.read(lib, slug) or "")
    lists = [v.strip() for v in mk.get("list", "").split(",") if v.strip()] if "list" in mk else None
    out = records.booking(slug, lists)
    out["item"] = {"id": slug, "lab": items[slug].get("lab"), "title": items[slug].get("title")}
    out["directory"] = next((b["url"] for b in records.builds(lib) if b.get("id") == "booking"), None)
    out["user_lab"] = load_config().get("lab")
    return out


@mcp.tool()
def ipa_open(url: str) -> dict:
    """Open a page of the site, a booking list or a library file in the user's browser.
    Only URLs of the site are accepted."""
    if not url.startswith(SITE_URL):
        raise ValueError(f"Only URLs under {SITE_URL} can be opened")
    return {"opened": url, "ok": webbrowser.open(url)}


@mcp.tool()
def ipa_files(folder: str, max_files: int = 200) -> list[dict]:
    """List the files of a library folder - 'data/equipment/<id>', 'data/psf/<session>/raw',
    'data/laser-power' - with size, URL and whether OneDrive has downloaded each one.
    Raw acquisitions are large: list before reading, and read only what is needed."""
    lib = _lib()
    p = (lib / folder).resolve()
    if not allowed(lib, p):
        raise ValueError("That folder is outside the readable library")
    if not p.is_dir():
        raise ValueError(f"No folder {folder!r} in the library")
    return records.list_files(lib, p, max_files)


# ------------------------------------------------------------------ main ---

def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="ipa-mcp", description=__doc__.splitlines()[0])
    ap.add_argument("--version", action="version", version=f"ipa-mcp {__version__}")
    ap.add_argument("--print-instructions", action="store_true", help="show the MCP instructions and exit")
    ap.add_argument("--status", action="store_true", help="where the library is, and exit")
    args = ap.parse_args(argv)
    if args.print_instructions:
        print(instructions())
        return
    if args.status:
        import json
        print(json.dumps(ipa_status(), indent=2, ensure_ascii=False))
        return
    mcp.run()


if __name__ == "__main__":
    main()
