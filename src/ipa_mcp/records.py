"""The structured records in the library: the equipment registry
(``site/registry.json``), PSF sessions (``data/psf``), laser power
(``data/laser-power``) and the builds (``builds/*/*/build.yaml``).

The conventions are the site's (its docs/measurements.md): a scope is a slug
``<lab>_<kind>_<name>``; an objective is ``<mag>x-<NA*100>-<immersion>``;
a measurement is keyed by scope, objective and light path.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import yaml

from .library import LISTS_URL, is_placeholder, library_url, page_url

OBJECTIVE = re.compile(r"^(?P<mag>\d+(?:\.\d+)?)x-(?P<na>\d{3})-(?P<imm>[a-z]+)(?:-(?P<dup>b))?$")

# Words people use, mapped to what the slugs and aliases say.
SYNONYMS = {
    "disc": "disk", "spinning": "sdc", "spinningdisk": "sdc",
    "widefield": "wf", "epifluorescence": "wf", "epi": "wf",
    "virtual": "vm", "desktop": "vm", "desktops": "vm", "vdi": "vm", "vms": "vm",
    "hoods": "hood", "cabinet": "hood",
    "microscope": "scope", "microscopes": "scope", "scopes": "scope",
    "olympus": "ix",
}

NUMERIC_SUFFIXES = ("_nm", "_x", "_y", "_z")


def kind_of(slug: str) -> str:
    parts = slug.split("_")
    return parts[1] if len(parts) >= 3 else "item"


def parse_objective(tag: str) -> dict:
    m = OBJECTIVE.match(tag)
    if not m:
        return {"tag": tag}
    return {"tag": tag, "magnification": float(m["mag"]), "na": int(m["na"]) / 100,
            "immersion": m["imm"]}


# -------------------------------------------------------------- registry ---

def registry(lib: Path) -> dict[str, dict]:
    with open(lib / "site" / "registry.json", encoding="utf-8") as f:
        return json.load(f)["items"]


def item_summary(slug: str, it: dict) -> dict:
    objectives = {}
    for tag, o in (it.get("objectives") or {}).items():
        d = parse_objective(tag)
        d["model"] = o.get("model")
        if "collar" in o:
            d["collar"] = o["collar"]
        objectives[tag] = d
    return {
        "id": slug, "kind": kind_of(slug), "lab": it.get("lab"), "title": it.get("title"),
        "aliases": it.get("aliases", []), "room": it.get("room"),
        "page": it.get("page") or page_url(slug),
        "objectives": objectives, "paths": it.get("paths") or {}, "lines": it.get("lines") or [],
    }


def _tokens(s: str) -> set[str]:
    out = set()
    for w in re.split(r"[^a-z0-9]+", s.lower()):
        if w:
            out.add(SYNONYMS.get(w, w))
    return out


def find_items(items: dict[str, dict], query: str, lab: str | None = None) -> list[dict]:
    """Rank items by how many words of the query appear in their slug, aliases,
    title, lab or objective models. The user's ``lab`` breaks ties."""
    q = _tokens(query)
    if not q:
        return []
    ranked = []
    for slug, it in items.items():
        hay = _tokens(slug) | _tokens(it.get("title", "")) | _tokens(it.get("lab", ""))
        for a in it.get("aliases", []):
            hay |= _tokens(a)
        for o in (it.get("objectives") or {}).values():
            hay |= _tokens(o.get("model", ""))
        score = len(q & hay)
        if score == 0:
            continue
        if lab and it.get("lab", "").lower() == lab.lower():
            score += 0.5
        ranked.append((score, slug))
    ranked.sort(key=lambda t: (-t[0], t[1]))
    return [{"id": s, "lab": items[s].get("lab"), "title": items[s].get("title"), "score": sc}
            for sc, s in ranked[:8]]


def booking(slug: str, lists: list[str] | None = None) -> dict:
    """Where the item's booking calendar is: embedded on the item's page, and
    the list itself at ``/Lists/<slug without hyphens>/``. VM desktops have one
    list per desktop (``<slug>_1``, ``<slug>_2``)."""
    names = lists or [slug]
    return {"page": page_url(slug), "lists": [f"{LISTS_URL}/{n.replace('-', '')}/" for n in names]}


# ------------------------------------------------------------ laser power --

def laser_rows(lib: Path) -> list[dict]:
    f = lib / "data" / "laser-power" / "laser-power.csv"
    if not f.is_file():
        return []
    with open(f, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ("mean_mW", "std_mW", "min_mW", "max_mW", "cv_pct", "drift_pct"):
            try:
                r[k] = float(r[k])
            except (KeyError, ValueError, TypeError):
                pass
    return rows


def laser_series(rows: list[dict], scope: str | None = None, line: int | None = None,
                 path: str | None = None) -> list[dict]:
    """One entry per (scope, line, path): every measurement by date, and the
    change of the latest against the first and against the previous one."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        if scope and r["microscope"] != scope:
            continue
        if line and str(r["laser_nm"]) != str(line):
            continue
        if path and r["path"] != path:
            continue
        groups.setdefault((r["microscope"], int(r["laser_nm"]), r["path"]), []).append(r)
    out = []
    for (sc, nm, pa), rs in sorted(groups.items()):
        rs.sort(key=lambda r: (r["date"], r.get("time", "")))
        pts = [{"date": r["date"], "mean_mW": r["mean_mW"], "cv_pct": r.get("cv_pct"),
                "drift_pct": r.get("drift_pct"), "operator": r.get("operator"), "file": r.get("file")}
               for r in rs]
        first, last = pts[0]["mean_mW"], pts[-1]["mean_mW"]
        prev = pts[-2]["mean_mW"] if len(pts) > 1 else None
        out.append({
            "scope": sc, "line_nm": nm, "path": pa, "n": len(pts),
            "first": pts[0]["date"], "latest": pts[-1]["date"], "latest_mW": last,
            "change_since_first_pct": round(100 * (last - first) / first, 1) if first else None,
            "change_since_previous_pct": round(100 * (last - prev) / prev, 1) if prev else None,
            "measurements": pts,
        })
    return out


# -------------------------------------------------------------------- PSF --

def psf_rows(lib: Path) -> list[dict]:
    f = lib / "data" / "psf" / "psf.csv"
    if not f.is_file():
        return []
    with open(f, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in list(r.items()):
            if k.endswith(NUMERIC_SUFFIXES) and v not in ("", None):
                try:
                    r[k] = float(v)
                except ValueError:
                    pass
    return rows


def _channel_key(r: dict) -> float:
    try:
        return float(r["channel"])
    except (ValueError, TypeError):
        return 0.0


def psf_sessions(lib: Path, rows: list[dict], scope: str | None = None,
                 objective: str | None = None, path: str | None = None) -> list[dict]:
    """One entry per session (scope, objective, path, date), newest first, with
    every channel's FWHM and chromatic shift, and the files in its folder."""
    sessions: dict[str, list[dict]] = {}
    for r in rows:
        if scope and r["scope"] != scope:
            continue
        if objective and r["objective"] != objective:
            continue
        if path and r["path"] != path:
            continue
        sessions.setdefault(r["session"], []).append(r)
    out = []
    for sid, rs in sorted(sessions.items(), reverse=True):
        r0 = rs[0]
        folder = lib / "data" / "psf" / sid
        meta = {}
        try:
            meta = yaml.safe_load((folder / "session.yaml").read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            pass
        channels = []
        for r in sorted(rs, key=_channel_key):
            tif = folder / f"psf_{r['channel']}.tif"
            channels.append({
                "channel": r["channel"], "excitation_nm": r.get("excitation_nm"),
                "emission": r.get("emission"),
                "fwhm_nm": {"x": r.get("fwhm_x_nm"), "y": r.get("fwhm_y_nm"), "z": r.get("fwhm_z_nm")},
                "expected_fwhm_nm": {"x": r.get("expected_fwhm_x_nm"), "y": r.get("expected_fwhm_y_nm"),
                                     "z": r.get("expected_fwhm_z_nm")},
                "shift_vs_reference_nm": {"x": r.get("shift_x_nm"), "y": r.get("shift_y_nm"),
                                          "z": r.get("shift_z_nm")},
                "r2": {"x": r.get("r2_x"), "y": r.get("r2_y"), "z": r.get("r2_z")},
                "psf_file": str(tif) if tif.is_file() else None,
                "psf_url": library_url(f"data/psf/{sid}/psf_{r['channel']}.tif") if tif.is_file() else None,
            })
        out.append({
            "session": sid, "date": r0["date"], "scope": r0["scope"], "objective": r0["objective"],
            "path": r0["path"], "collar": r0.get("collar"), "reference_channel": r0.get("reference_channel"),
            "voxel_nm": {"x": r0.get("voxel_x_nm"), "y": r0.get("voxel_y_nm"), "z": r0.get("voxel_z_nm")},
            "beads": r0.get("beads"), "bead_nm": r0.get("bead_nm"), "mounting": meta.get("mounting"),
            "operator": meta.get("operator"), "notes": meta.get("notes"), "method": r0.get("method"),
            "folder": str(folder), "folder_url": library_url(f"data/psf/{sid}"),
            "pictures": [str(folder / n) for n in ("beads.png", "cross-sections.png") if (folder / n).is_file()],
            "channels": channels,
        })
    return out


# ------------------------------------------------------------------ builds --

def builds(lib: Path) -> list[dict]:
    out = []
    for m in sorted((lib / "builds").glob("*/*/build.yaml")):
        try:
            b = yaml.safe_load(m.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        rel = m.parent.relative_to(lib).as_posix()
        b["url"] = library_url(f"{rel}/{b.get('file', '')}")
        b["folder"] = str(m.parent)
        out.append(b)
    return out


# --------------------------------------------------------------- raw data --

def list_files(lib: Path, folder: Path, max_files: int = 200) -> list[dict]:
    out = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            size = None
        ph = is_placeholder(p)
        out.append({"path": str(p), "relative": p.relative_to(folder).as_posix(), "bytes": size,
                    "downloaded": None if ph is None else not ph,
                    "url": library_url(p.relative_to(lib).as_posix())})
        if len(out) >= max_files:
            break
    return out
