"""Tests against a small fake library, built in a temp folder."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REGISTRY = {"items": {
    "dudin_scope_sdc-nikon": {
        "id": "dudin_scope_sdc-nikon", "lab": "Dudin", "room": "002",
        "aliases": ["Scope - SDC Nikon", "Spinning disk (Nikon)", "dudin-sdc"],
        "title": "Spinning-disk confocal (Nikon) - Dudin lab",
        "objectives": {"60x-120-water": {"model": "CFI Plan Apo VC 60XC WI"},
                       "10x-030-air": {"model": "Plan Fluor 10x/0.30"}},
        "paths": {"disk": "Through the CSU-W1 disk"}, "lines": [405, 488, 561, 640],
    },
    "aumeier_scope_sdc-3i": {
        "id": "aumeier_scope_sdc-3i", "lab": "Aumeier", "room": "347",
        "aliases": ["Scope - SDC 3i", "Spinning disk (3i)", "Charlotte's scope"],
        "title": "Spinning disk (3i) - Aumeier lab",
        "objectives": {"100x-146-oil": {"model": "alpha Plan-Apochromat 100x/1.46 Oil"}},
        "paths": {"disk": "Through the CSU-W1 spinning disk", "tirf": "Vector3"}, "lines": [405, 488, 561, 640],
    },
    "roux_vm_vdi": {"id": "roux_vm_vdi", "lab": "Roux", "aliases": ["VM - Roux"], "title": "VM - Roux lab"},
}}

PAGE = """A spinning disk from the Dudin lab.

<!-- list: dudin_scope_sdc-nikon -->

# Spinning-disk confocal (Nikon) - Dudin lab

## Hardware

### Objectives

An all-water set.

## Software

NIS-Elements AR 5.42. **Napari** is not installed here.

## Known quirks

The stage forgets its home.
"""

VMS = """# How the lab VMs work

## What is installed

| Software | |
| --- | --- |
| Fiji | Installed |
| Cellpose | Being set up |
"""

ASK = """# Image analysis

## Just ask

**Nicolas Chiaruttini** - room 3-308, nicolas.chiaruttini@unige.ch

## Something else

text
"""

LASER = """date,time,operator,microscope,laser_nm,path,mean_mW,std_mW,min_mW,max_mW,cv_pct,drift_pct,n,duration_s,dips,trimmed,sensor,note,file
2025-10-20,14:06:16,nc,aumeier_scope_sdc-3i,488,disk,8.0,0.01,7.9,8.1,0.4,-0.5,478,60.1,56,0,S170C,,a.csv
2026-10-28,14:08:12,nc,aumeier_scope_sdc-3i,488,disk,6.5,0.04,6.3,6.6,0.6,0.2,484,60.1,64,0,S170C,,b.csv
2026-10-28,14:20:31,nc,aumeier_scope_sdc-3i,561,disk,6.8,0.03,6.7,6.9,0.4,-0.1,483,60.1,64,0,S170C,,c.csv
"""

PSF_HEAD = ("session,date,scope,objective,path,channel,collar,reference_channel,excitation_nm,emission,beads,bead_nm,"
            "voxel_x_nm,voxel_y_nm,voxel_z_nm,raw_voxel_x_nm,raw_voxel_y_nm,raw_voxel_z_nm,fwhm_x_nm,fwhm_y_nm,fwhm_z_nm,"
            "r2_x,r2_y,r2_z,theory_fwhm_x_nm,theory_fwhm_y_nm,theory_fwhm_z_nm,expected_fwhm_x_nm,expected_fwhm_y_nm,"
            "expected_fwhm_z_nm,centre_x_nm,centre_y_nm,centre_z_nm,shift_x_nm,shift_y_nm,shift_z_nm,method,version\n")
PSF_ROW = ("2026-07-24_aumeier_scope_sdc-3i_100x-146-oil_disk,2026-07-24,aumeier_scope_sdc-3i,100x-146-oil,disk,488,0.17,488,"
           "488,Chroma ET525/50m,TetraSpeck,200,65,65,200,65,65,200,250,255,700,0.99,0.99,0.98,200,200,600,230,230,650,"
           "0,0,0,0,0,0,median,psfdistill 0.1.0\n")


@pytest.fixture
def lib(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "biochem-ipa - Documents"
    (root / "site").mkdir(parents=True)
    (root / "site" / "registry.json").write_text(json.dumps(REGISTRY), encoding="utf-8")
    (root / "site" / "dudin_scope_sdc-nikon.md").write_text(PAGE, encoding="utf-8")
    (root / "site" / "lab-vms.md").write_text(VMS, encoding="utf-8")
    (root / "site" / "image-analysis.md").write_text(ASK, encoding="utf-8")
    (root / "data" / "laser-power").mkdir(parents=True)
    (root / "data" / "laser-power" / "laser-power.csv").write_text(LASER, encoding="utf-8")
    (root / "data" / "laser-power" / "README.md").write_text("# Laser power\n\nThorlabs PM100USB.\n", encoding="utf-8")
    sess = root / "data" / "psf" / "2026-07-24_aumeier_scope_sdc-3i_100x-146-oil_disk"
    sess.mkdir(parents=True)
    (root / "data" / "psf" / "psf.csv").write_text(PSF_HEAD + PSF_ROW, encoding="utf-8")
    (sess / "session.yaml").write_text("operator: nc\nmounting: ProLong Glass\n", encoding="utf-8")
    (sess / "psf_488.tif").write_bytes(b"")
    (root / "builds" / "viewers" / "psf").mkdir(parents=True)
    (root / "builds" / "viewers" / "psf" / "build.yaml").write_text(
        "id: psf\nkind: viewer\ntitle: PSF explorer\nfile: psf.html\n", encoding="utf-8")
    (root / "private").mkdir()
    (root / "private" / "secret.pdf").write_bytes(b"x")
    monkeypatch.setenv("IPA_LIBRARY", str(root))
    monkeypatch.setenv("IPA_MCP_HOME", str(tmp_path / "home"))
    return root


def test_find_items(lib):
    import ipa_mcp
    r = ipa_mcp.ipa_find("the spinning disc")
    ids = [c["id"] for c in r["candidates"]]
    assert set(ids) == {"dudin_scope_sdc-nikon", "aumeier_scope_sdc-3i"}
    r = ipa_mcp.ipa_find("nikon scope")
    assert r["candidates"][0]["id"] == "dudin_scope_sdc-nikon"


def test_lab_breaks_ties(lib):
    import ipa_mcp
    ipa_mcp.ipa_set_user(name="Someone", lab="Aumeier")
    r = ipa_mcp.ipa_find("spinning disk")
    assert r["candidates"][0]["id"] == "aumeier_scope_sdc-3i"


def test_item_objectives_and_booking(lib):
    import ipa_mcp
    it = ipa_mcp.ipa_item("dudin_scope_sdc-nikon")
    imm = {t: o["immersion"] for t, o in it["objectives"].items()}
    assert imm == {"60x-120-water": "water", "10x-030-air": "air"}
    assert it["objectives"]["60x-120-water"]["na"] == 1.2
    assert it["booking"]["lists"] == ["https://unigech.sharepoint.com/teams/ipa/Lists/dudin_scope_sdcnikon/"]
    assert "## Software" in it["outline"]
    assert it["psf_measured"] == []


def test_page_section_and_search(lib):
    import ipa_mcp
    r = ipa_mcp.ipa_page("dudin_scope_sdc-nikon", "Software")
    assert "NIS-Elements" in r["text"] and r["url"].endswith("#software")
    hits = ipa_mcp.ipa_search(r"napari")
    assert hits and hits[0]["page"] == "dudin_scope_sdc-nikon" and hits[0]["heading"] == "Software"
    hits = ipa_mcp.ipa_search(r"PM100")
    assert hits[0]["page"] == "data/laser-power/README.md"


def test_laser_trend(lib):
    import ipa_mcp
    r = ipa_mcp.ipa_laser_power(scope="aumeier_scope_sdc-3i", line_nm=488)
    s = r["found"][0]
    assert s["n"] == 2 and s["change_since_first_pct"] == -18.8
    r = ipa_mcp.ipa_laser_power(scope="dudin_scope_sdc-nikon")
    assert r["not_measured"] and r["protocol_page"].endswith("protocol-laser-power.aspx")
    assert "Chiaruttini" in r["ask"]


def test_psf(lib):
    import ipa_mcp
    r = ipa_mcp.ipa_psf(scope="aumeier_scope_sdc-3i", objective="100x-146-oil")
    s = r["found"][0]
    assert s["mounting"] == "ProLong Glass"
    assert s["channels"][0]["psf_file"].endswith("psf_488.tif")
    assert s["channels"][0]["fwhm_nm"]["z"] == 700.0
    r = ipa_mcp.ipa_psf(scope="dudin_scope_sdc-nikon", objective="60x-120-water")
    assert r["not_measured"] and r["objectives_on_this_scope"] == ["60x-120-water", "10x-030-air"]


def test_private_is_never_listed(lib):
    import ipa_mcp
    with pytest.raises(ValueError):
        ipa_mcp.ipa_files("private")
    with pytest.raises(ValueError):
        ipa_mcp.ipa_files("../")
    assert {f["relative"] for f in ipa_mcp.ipa_files("data/laser-power")} == {"README.md", "laser-power.csv"}


def test_open_refuses_foreign_urls(lib):
    import ipa_mcp
    with pytest.raises(ValueError):
        ipa_mcp.ipa_open("https://example.com")


def test_status_and_instructions(lib):
    import ipa_mcp
    st = ipa_mcp.ipa_status()
    assert st["equipment"] == 3 and st["psf_sessions"] == 1
    text = ipa_mcp.instructions()
    assert "Chiaruttini" in text and str(lib) in text
