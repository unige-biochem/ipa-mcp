"""Where the site's library is on this machine, and the user's settings.

The server reads a *synced copy* of the SharePoint library (OneDrive's "Sync"
on the library's web view), never SharePoint itself: no credentials, no token,
and the user sees exactly what their own account can read. Nothing under
``private/`` is ever read.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

SITE_URL = "https://unigech.sharepoint.com/teams/ipa"
PAGES_URL = f"{SITE_URL}/SitePages"
LISTS_URL = f"{SITE_URL}/Lists"
LIBRARY_URL = f"{SITE_URL}/Documents%20partages"
LIBRARY_FOLDER = "biochem-ipa - Documents"  # OneDrive's name for the synced library
NEVER_READ = ("private",)  # restricted folders: never part of the corpus

HOME = Path(os.environ.get("IPA_MCP_HOME") or (Path.home() / ".ipa-mcp"))
CONFIG = HOME / "config.json"


# ---------------------------------------------------------------- config ---

def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(update: dict) -> dict:
    cfg = load_config()
    cfg.update({k: v for k, v in update.items() if v is not None})
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg


# --------------------------------------------------------------- library ---

def is_library(p: Path | None) -> bool:
    return bool(p) and (p / "site" / "registry.json").is_file()


def _registry_mount_points() -> list[Path]:
    """Windows: every OneDrive sync root whose URL is this site."""
    if sys.platform != "win32":
        return []
    try:
        import winreg
    except ImportError:
        return []
    found: list[Path] = []
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\SyncEngines\Providers\OneDrive")
    except OSError:
        return []
    with root:
        i = 0
        while True:
            try:
                name = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                with winreg.OpenKey(root, name) as k:
                    url = winreg.QueryValueEx(k, "UrlNamespace")[0]
                    mount = winreg.QueryValueEx(k, "MountPoint")[0]
            except OSError:
                continue
            if "/teams/ipa" in str(url).lower():
                found.append(Path(mount))
    return found


def _guesses() -> list[Path]:
    home = Path.home()
    out: list[Path] = []
    # macOS: ~/Library/CloudStorage/OneDrive-SharedLibraries-<tenant>/<library>
    out += list((home / "Library" / "CloudStorage").glob(f"OneDrive-*/{LIBRARY_FOLDER}"))
    # A OneDrive folder under the home, one level down
    out += list(home.glob(f"*/{LIBRARY_FOLDER}"))
    if sys.platform == "win32":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            out += list(Path(f"{letter}:/").glob(f"*/{LIBRARY_FOLDER}"))
    return out


def find_library() -> Path | None:
    """The synced library, from (in order) ``IPA_LIBRARY``, the saved config,
    OneDrive's registry entries, then the usual places. None if not found."""
    env = os.environ.get("IPA_LIBRARY")
    if env and is_library(Path(env)):
        return Path(env)
    cfg = load_config().get("library")
    if cfg and is_library(Path(cfg)):
        return Path(cfg)
    for p in _registry_mount_points() + _guesses():
        if is_library(p):
            return p
    return None


SETUP_HELP = f"""The synced library was not found on this machine.

Set it up once (any UNIGE account that can read the site):
1. Open the library in a browser: {LIBRARY_URL}
2. Click "Sync" in the toolbar. OneDrive creates a folder named "{LIBRARY_FOLDER}"
   (under "Universite de Geneve" on Windows, under ~/Library/CloudStorage on macOS).
3. Wait for the first sync: the folder must contain site/registry.json.
4. If the server still cannot find it, give it the path with ipa_set_user(library=...),
   or set the environment variable IPA_LIBRARY.

Files stay OneDrive placeholders until read; the first read of a large raw
file downloads it. This server never writes to the library."""


def library_url(rel: str) -> str:
    """The SharePoint URL of a library path such as ``data/psf/psf.csv``."""
    return f"{LIBRARY_URL}/{quote(rel.replace(os.sep, '/'))}"


def page_url(name: str) -> str:
    return f"{PAGES_URL}/{name}.aspx"


def is_placeholder(p: Path) -> bool | None:
    """True if OneDrive has not downloaded the file (Windows only; None elsewhere)."""
    if sys.platform != "win32":
        return None
    try:
        attrs = os.stat(p).st_file_attributes  # type: ignore[attr-defined]
    except OSError:
        return None
    recall = 0x400000 | 0x1000  # RECALL_ON_DATA_ACCESS | OFFLINE
    return bool(attrs & recall)


def allowed(lib: Path, p: Path) -> bool:
    """A path inside the library and outside its restricted folders."""
    try:
        rel = p.resolve().relative_to(lib.resolve())
    except ValueError:
        return False
    return not rel.parts or rel.parts[0].lower() not in NEVER_READ
