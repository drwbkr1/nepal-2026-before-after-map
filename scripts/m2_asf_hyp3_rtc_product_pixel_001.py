#!/usr/bin/env python3
"""Gated two-AOI pixel QA for the exact first ASF HyP3 RTC product.

Reads only VV, VH and layover/shadow windows within the approved event AOIs.
It never extracts or publishes pixel arrays, reads the DEM raster, submits a
job, evaluates registration, or admits a scientific baseline/change result.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

from m2_asf_hyp3_rtc_acquire_first_001 import DATA_ROOT
from m2_asf_hyp3_rtc_composite_provenance_core_001 import (
    ARCHIVE_SHA256, ARCHIVE_SIZE, JOB_ID, PRODUCT_FILENAME, SOURCE_ID,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_header_core_001 import inspect_raster_headers
from m2_asf_hyp3_rtc_pixel_core_001 import evaluate_window
from m2_asf_hyp3_rtc_product_header_001 import describe_vsi
from m2_asf_hyp3_rtc_product_metadata_001 import (
    APPROVAL_REF, SOURCE_GATE_REF, _json, _now, _safe_dir, _safe_file, _sha,
    _write_json,
)
from pixel_qa_core import load_contract


AOI_REF = "config/aoi/approved-study-areas-epsg32645.json"
AOI_SHA256 = "3d6c9bb39fa9b3ffeddfb0048ddabf30ee4472c0006b78c5c7d58193693ac615"
CONTRACT_REF = "config/qa/pixel-readiness-contract.json"
CONTRACT_SHA256 = "5a66ae11288813868f362c342027ce0e4850d435dfbb2cfec3f5098b17d123e2"
HEADER_RECON_REF = "records/readiness/m2-asf-hyp3-rtc-product-header-001-terminal-reconciliation.json"
HEADER_TERMINAL_REF = "m2-asf-hyp3-rtc-product-header-001/attempt-001/terminal.json"
ACQUISITION_REF = "m2-asf-hyp3-rtc-acquire-first-001/attempt-001/terminal.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-product-pixel-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-product-pixel-001-execution-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-product-pixel-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_pixel_core_001.py",
    "scripts/m2_asf_hyp3_rtc_product_pixel_001.py",
    "scripts/validate_m2_asf_hyp3_rtc_vsi_pixel_synthetic_001.py",
    "tests/test_m2_asf_hyp3_rtc_pixel_core_001.py",
    "tests/test_m2_asf_hyp3_rtc_product_pixel_001.py",
)
EVENT_AOIS = ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")


def _load_aois(root: Path = ROOT) -> list[tuple[str, list[list[float]]]]:
    path = root / AOI_REF
    if _sha(path) != AOI_SHA256:
        raise RouteStop("rtc_pixel_aoi_hash_mismatch")
    value = _json(path)
    if value.get("geometryType") != "esriGeometryPolygon" or value.get("spatialReference", {}).get("wkid") != 32645:
        raise RouteStop("rtc_pixel_aoi_crs_invalid")
    selected = {}
    for feature in value.get("features", []):
        aoi_id = feature.get("attributes", {}).get("AOI_ID")
        if aoi_id not in EVENT_AOIS:
            continue
        rings = feature.get("geometry", {}).get("rings")
        if aoi_id in selected or not isinstance(rings, list) or len(rings) != 1:
            raise RouteStop("rtc_pixel_aoi_shape_invalid")
        ring = rings[0]
        if (
            not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]
            or any(not isinstance(point, list) or len(point) != 2 or
                   any(type(item) not in (int, float) or not math.isfinite(item)
                       for item in point) for point in ring)
        ):
            raise RouteStop("rtc_pixel_aoi_shape_invalid")
        selected[aoi_id] = ring
    if set(selected) != set(EVENT_AOIS):
        raise RouteStop("rtc_pixel_aoi_set_invalid")
    return [(aoi_id, selected[aoi_id]) for aoi_id in EVENT_AOIS]


def scan_one_aoi(
    aoi_id: str, points: list[list[float]], vv_ds, vh_ds, ls_ds,
    contract: dict,
) -> dict:
    """Rasterize a projected AOI and decode only its three input windows."""
    import numpy as np
    from osgeo import gdal, ogr, osr

    gt = vv_ds.GetGeoTransform()
    if gt[1] <= 0 or gt[5] >= 0 or gt[2] != 0 or gt[4] != 0:
        raise RouteStop("rtc_pixel_grid_not_north_up")
    ring = ogr.Geometry(ogr.wkbLinearRing)
    for x, y in points:
        ring.AddPoint_2D(float(x), float(y))
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)
    if not polygon.IsValid() or polygon.IsEmpty():
        raise RouteStop("rtc_pixel_aoi_geometry_invalid")
    xmin, xmax, ymin, ymax = polygon.GetEnvelope()
    x0 = max(0, math.floor((xmin - gt[0]) / gt[1]))
    x1 = min(vv_ds.RasterXSize, math.ceil((xmax - gt[0]) / gt[1]))
    y0 = max(0, math.floor((gt[3] - ymax) / abs(gt[5])))
    y1 = min(vv_ds.RasterYSize, math.ceil((gt[3] - ymin) / abs(gt[5])))
    if x1 <= x0 or y1 <= y0:
        return evaluate_window(
            aoi_id=aoi_id, aoi_area_m2=polygon.GetArea(),
            pixel_area_m2=gt[1] * abs(gt[5]),
            footprint=np.zeros((1, 1), dtype=np.uint8),
            vv=np.ones((1, 1), dtype=np.float32),
            vh=np.ones((1, 1), dtype=np.float32),
            ls=np.ones((1, 1), dtype=np.uint8),
            vv_nodata=None, vh_nodata=None, contract=contract,
        )
    width, height = x1 - x0, y1 - y0
    mask = gdal.GetDriverByName("MEM").Create("", width, height, 1, gdal.GDT_Byte)
    mask.SetGeoTransform((gt[0] + x0 * gt[1], gt[1], 0,
                          gt[3] + y0 * gt[5], 0, gt[5]))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32645)
    mask.SetSpatialRef(spatial)
    mask.GetRasterBand(1).Fill(0)
    vector = ogr.GetDriverByName("Memory").CreateDataSource("")
    layer = vector.CreateLayer("aoi", spatial, ogr.wkbPolygon)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(polygon)
    layer.CreateFeature(feature)
    feature = None
    if gdal.RasterizeLayer(mask, [1], layer, burn_values=[1]) != 0:
        raise RouteStop("rtc_pixel_aoi_rasterization_failed")
    footprint = mask.GetRasterBand(1).ReadAsArray()
    vv_band, vh_band = vv_ds.GetRasterBand(1), vh_ds.GetRasterBand(1)
    vv = vv_band.ReadAsArray(x0, y0, width, height)
    vh = vh_band.ReadAsArray(x0, y0, width, height)
    ls = ls_ds.GetRasterBand(1).ReadAsArray(x0, y0, width, height)
    if any(item is None for item in (footprint, vv, vh, ls)):
        raise RouteStop("rtc_pixel_window_read_failed")
    return evaluate_window(
        aoi_id=aoi_id, aoi_area_m2=polygon.GetArea(),
        pixel_area_m2=gt[1] * abs(gt[5]),
        footprint=footprint, vv=vv, vh=vh, ls=ls,
        vv_nodata=vv_band.GetNoDataValue(),
        vh_nodata=vh_band.GetNoDataValue(), contract=contract,
    )


def scan_product(archive: Path, header_terminal: dict, aois: list, contract: dict) -> list[dict]:
    """Bind actual headers, then read only VV/VH/layover-shadow AOI windows."""
    from osgeo import gdal

    gdal.UseExceptions()
    base = archive.stem
    members = {role: f"{base}/{base}_{role}.tif" for role in ("VV", "VH")}
    members["ls_map"] = f"{base}/{base}_ls_map.tif"
    actual = {role.lower(): describe_vsi(archive, member)
              for role, member in members.items()}
    frozen = header_terminal.get("headers")
    if not isinstance(frozen, dict) or any(actual[role] != frozen.get(role)
                                            for role in ("vv", "vh", "ls_map")):
        raise RouteStop("rtc_pixel_header_drift")
    if inspect_raster_headers(SOURCE_ID, frozen)["status"] != "pass_header_descriptor_rules_only":
        raise RouteStop("rtc_pixel_frozen_header_invalid")
    datasets = {}
    try:
        for role, member in members.items():
            vsi = "/vsizip/" + archive.as_posix() + "/" + member
            dataset = gdal.OpenEx(vsi, gdal.OF_RASTER)
            if dataset is None:
                raise RouteStop("rtc_pixel_vsi_open_failed")
            datasets[role] = dataset
        return [scan_one_aoi(aoi_id, ring, datasets["VV"], datasets["VH"],
                             datasets["ls_map"], contract)
                for aoi_id, ring in aois]
    finally:
        datasets.clear()


def require_release(
    root: Path = ROOT, data_root: Path = DATA_ROOT,
    attempt_root: Path = ATTEMPT_ROOT,
) -> tuple[dict, dict, Path]:
    """Require exact published code and no-content gates before pixels."""
    paths = {
        "approval": root / APPROVAL_REF,
        "source_gate": root / SOURCE_GATE_REF,
        "header_recon": root / HEADER_RECON_REF,
        "gate": root / GATE_REF,
        "preflight": root / PREFLIGHT_REF,
        "header": data_root / HEADER_TERMINAL_REF,
        "acquisition": data_root / ACQUISITION_REF,
    }
    archive = data_root / "m2-asf-hyp3-rtc-products-001" / PRODUCT_FILENAME
    if any(not _safe_file(path) for path in (*paths.values(), archive)):
        raise RouteStop("rtc_pixel_required_path_invalid")
    if (
        not _safe_dir(data_root) or not _safe_dir(archive.parent)
        or not _safe_dir(paths["header"].parent)
        or attempt_root.parent.parent.resolve() != data_root.resolve()
        or attempt_root.parent.is_symlink()
        or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("rtc_pixel_path_or_attempt_invalid")
    records = {key: _json(path) for key, path in paths.items()}
    approval, source_gate, recon, gate, preflight, header, acquisition = (
        records[key] for key in ("approval", "source_gate", "header_recon",
                                 "gate", "preflight", "header", "acquisition")
    )
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    try:
        valid = (
            approval.get("decision") == "approve"
            and approval.get("authority", {}).get("conditional_product_metadata_and_pixel_QA_under_original_route") is True
            and source_gate.get("decision", {}).get("status") == "ready"
            and recon.get("status") == "pass_actual_headers_for_local_pixel_qa_only"
            and recon.get("bindings", {}).get("non_git_terminal_sha256") == _sha(paths["header"])
            and header.get("status") == "pass_actual_headers_for_local_pixel_qa_only"
            and header.get("pixels_read") is False
            and gate.get("status") == "pass_product_pixel_implementation_public_ci_only"
            and gate.get("public_ci", {}).get("conclusion") == "success"
            and gate.get("bindings", {}).get("approval_sha256") == _sha(paths["approval"])
            and gate.get("bindings", {}).get("source_gate_sha256") == _sha(paths["source_gate"])
            and gate.get("bindings", {}).get("header_reconciliation_sha256") == _sha(paths["header_recon"])
            and gate.get("bindings", {}).get("aoi_sha256") == _sha(root / AOI_REF) == AOI_SHA256
            and gate.get("bindings", {}).get("pixel_contract_sha256") == _sha(root / CONTRACT_REF) == CONTRACT_SHA256
            and isinstance(files, dict) and set(files) == set(IMPLEMENTATION_FILES)
            and all(_sha(root / ref) == sha for ref, sha in files.items())
            and preflight.get("status") == "pass_product_pixel_no_content_preflight"
            and preflight.get("bindings", {}).get("implementation_gate_sha256") == _sha(paths["gate"])
            and preflight.get("bindings", {}).get("header_terminal_sha256") == _sha(paths["header"])
            and preflight.get("bindings", {}).get("acquisition_terminal_sha256") == _sha(paths["acquisition"])
            and preflight.get("assertions", {}).get("attempt_absent") is True
            and preflight.get("assertions", {}).get("no_product_pixels_read") is True
            and acquisition.get("status") == "pass_local_zip_promoted_no_replace"
            and acquisition.get("source_id") == SOURCE_ID
            and acquisition.get("job_id") == JOB_ID
            and acquisition.get("product_filename") == PRODUCT_FILENAME
            and acquisition.get("archive_sha256") == ARCHIVE_SHA256
            and acquisition.get("archive_size_bytes") == ARCHIVE_SIZE
            and archive.stat().st_size == ARCHIVE_SIZE
        )
    except (OSError, TypeError, ValueError):
        raise RouteStop("rtc_pixel_release_unavailable") from None
    if not valid:
        raise RouteStop("rtc_pixel_not_released")
    return acquisition, header, archive


def inspect_once(
    acquisition: dict, header: dict, archive: Path,
    attempt_root: Path = ATTEMPT_ROOT, *, controlled_root: Path = DATA_ROOT,
    scan=scan_product, root: Path = ROOT,
) -> dict:
    """Reserve once, verify ZIP, evaluate two event AOIs, retain disposition."""
    if (
        not _safe_dir(controlled_root)
        or attempt_root.parent.parent.resolve() != controlled_root.resolve()
        or attempt_root.parent.is_symlink()
        or attempt_root.exists() or attempt_root.is_symlink()
    ):
        raise RouteStop("rtc_pixel_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("rtc_pixel_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("rtc_pixel_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "two_aoi_pixel_qa_reserved", "source_id": SOURCE_ID,
        "job_id": JOB_ID, "started_at_utc": _now(),
        "registration_measured": False, "archive_mutated": False,
    })
    try:
        if (
            not _safe_file(archive) or archive.name != PRODUCT_FILENAME
            or archive.stat().st_size != acquisition["archive_size_bytes"]
            or acquisition["archive_sha256"] != ARCHIVE_SHA256
            or _sha(archive) != ARCHIVE_SHA256
        ):
            raise RouteStop("rtc_pixel_archive_identity_mismatch")
        before = archive.stat()
        aois = _load_aois(root)
        if _sha(root / CONTRACT_REF) != CONTRACT_SHA256:
            raise RouteStop("rtc_pixel_contract_hash_mismatch")
        contract = load_contract(root / CONTRACT_REF)
        results = scan(archive, header, aois, contract)
        if not isinstance(results, list) or [item.get("aoi_id") for item in results] != list(EVENT_AOIS):
            raise RouteStop("rtc_pixel_result_shape_invalid")
        after = archive.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino
        ):
            raise RouteStop("rtc_pixel_archive_changed_during_read")
        passed = all(item.get("status") == "pass_qa_only" for item in results)
        terminal = {
            "status": "pass_source_event_aoi_pixel_qa_only" if passed else "stop_source_event_aoi_pixel_qa_no_next_date",
            "source_id": SOURCE_ID, "job_id": JOB_ID,
            "finished_at_utc": _now(), "aoi_results": results,
            "archive_sha256_verified_current": True,
            "VV_VH_layover_shadow_AOI_pixels_read": True,
            "DEM_pixels_read": False, "registration_measured": False,
            "next_job_released": passed, "archive_mutated": False,
            "baseline_admission_authorized": False,
            "change_analysis_authorized": False,
            "arcgis_map_ready": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_pixel_qa_no_automatic_retry",
                    "code": exc.code, "source_id": SOURCE_ID,
                    "job_id": JOB_ID, "finished_at_utc": _now(),
                    "pixel_read_status": "indeterminate_on_failure",
                    "next_job_released": False, "archive_mutated": False,
                    "arcgis_map_ready": False}
    except BaseException:
        terminal = {"status": "stopped_pixel_qa_no_automatic_retry",
                    "code": "rtc_pixel_unexpected_failure", "source_id": SOURCE_ID,
                    "job_id": JOB_ID, "finished_at_utc": _now(),
                    "pixel_read_status": "indeterminate_on_failure",
                    "next_job_released": False, "archive_mutated": False,
                    "arcgis_map_ready": False}
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        acquisition, header, archive = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_pixel_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("rtc_pixel_arguments_invalid")
        result = inspect_once(acquisition, header, archive)
        print(json.dumps({"status": result["status"], "code": result.get("code"),
                          "source_id": SOURCE_ID, "next_job_released": result.get("next_job_released", False)},
                         sort_keys=True))
        return 0 if result["status"] in {
            "pass_source_event_aoi_pixel_qa_only",
            "stop_source_event_aoi_pixel_qa_no_next_date",
        } else 12
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "next_job_released": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped", "code": "rtc_pixel_unexpected_failure",
                          "next_job_released": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
