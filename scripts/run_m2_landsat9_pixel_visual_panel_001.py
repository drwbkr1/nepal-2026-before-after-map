#!/usr/bin/env python3
"""One gated, append-only local Landsat-9 header/pixel QA and visual route.

No network, credentials, provider request, retry, or change calculation.
Run only after the exact packet and implementation public-CI gates pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import numpy as np

from landsat9_pixel_visual_core_001 import (
    CELL, OFFSET, SCALE, PixelMethodError, aoi_cell_weights, classify_pixels,
    nearest_rank_stretch, validate_headers, weighted_metrics,
)
from landsat_l2_grouped_mtl_integrity_002 import _verify_grouped_metadata
from m2_transfer_core import is_reparse_point, sha256_file
from landsat9_visual_panel_arcgis_001 import build as build_panel, fresh_reopen

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
INTAKE = DATA / ".intake-staging/nepal-m2-landsat9-grouped-mtl-recovery-002/attempt-events"
ATTEMPT = DATA / "processing/landsat9-pixel-visual-panel-001/real-001"
APPROVAL = ROOT / "records/source-gates/m2-landsat9-pixel-visual-panel-001-approval.json"
APPROVAL_SHA = "5f0ee6a201c77784e103f1e2b2cf316f87f01af1983676e54cc96c3a52563cbc"
PROPOSAL = ROOT / "contracts/milestone-002-landsat9-pixel-visual-panel-001-proposal.json"
PROPOSAL_SHA = "e40d6f84aed7e41e52f8b084511213d4fe4c6d1a31fe54484172f1d1893d793e"
BUNDLE = ROOT / "reviews/m2-landsat9-pixel-visual-panel-001/review-bundle.json"
BUNDLE_SHA = "9df5137caa4d83577b5350178b5c61055cd366f935653d8aa5e13d2eed0a0f28"
POST_CI = ROOT / "records/readiness/m2-landsat9-grouped-mtl-recovery-002-post-ci-reconciliation.json"
POST_CI_SHA = "e3ab69e49a8799afbc12551b7424f9f0082e9e07b7247d4bcb6085b410eb79b6"
AOI = ROOT / "config/aoi/approved-study-areas-epsg32645.json"
AOI_SHA = "3d6c9bb39fa9b3ffeddfb0048ddabf30ee4472c0006b78c5c7d58193693ac615"
QA_CONTRACT = ROOT / "config/qa/pixel-readiness-contract.json"
QA_CONTRACT_SHA = "5a66ae11288813868f362c342027ce0e4850d435dfbb2cfec3f5098b17d123e2"
QA_DECODER = ROOT / "scripts/landsat_c2_qa_flags.py"
QA_DECODER_SHA = "9023715cb57a7651fc679acbe412e363d8e26d399f2f13493dba2693d54f2e03"
PRODUCTS = {
    "before": ("LC09_L2SP_141040_20260810_20260811_02_T1", "LC91410402026222LGN00",
               1126565376, "9f9a5a63e7abd78f889c9f5229a80f62008b6c31e88b212bf8af01950ca9b255",
               "landsat9-before-20260810-grouped-mtl-recovery-002"),
    "after": ("LC09_L2SP_141040_20260826_20260827_02_T1", "LC91410402026238LGN00",
              1123888128, "f2b7a99f75d1324f0c7a984af5172740ca20862b774e2a17714df0cd7c454b38",
              "landsat9-after-20260826-grouped-mtl-intake-002"),
}
SUFFIXES = ("_MTL.txt", "_MTL.xml", "_QA_PIXEL.TIF", "_QA_RADSAT.TIF",
            "_SR_QA_AEROSOL.TIF", "_SR_B3.TIF", "_SR_B4.TIF", "_SR_B5.TIF",
            "_SR_B6.TIF", "_SR_B7.TIF")
ROLES = ("QA_PIXEL", "QA_RADSAT", "SR_QA_AEROSOL", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7")


class RouteStop(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_new(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, sort_keys=True, indent=2, allow_nan=False)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())


def read_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or is_reparse_point(path):
        raise RouteStop("required_control_missing_or_unsafe")
    return json.loads(path.read_text(encoding="utf-8"))


def _check_controls() -> None:
    for path, expected in ((APPROVAL, APPROVAL_SHA), (PROPOSAL, PROPOSAL_SHA),
                           (BUNDLE, BUNDLE_SHA), (POST_CI, POST_CI_SHA),
                           (AOI, AOI_SHA), (QA_CONTRACT, QA_CONTRACT_SHA),
                           (QA_DECODER, QA_DECODER_SHA)):
        if sha256_file(path) != expected:
            raise RouteStop("frozen_control_hash_drift")
    approval = read_json(APPROVAL)
    if (approval.get("decision") != "approved_one_conditional_envelope"
            or approval.get("review_bundle_sha256") != BUNDLE_SHA
            or approval.get("proposal_sha256") != PROPOSAL_SHA):
        raise RouteStop("owner_approval_invalid")
    if read_json(POST_CI).get("status") != "terminal_container_only_publication_verified_envelope_closed":
        raise RouteStop("closed_container_intake_invalid")


def _receipt(role: str) -> dict:
    product, scene, size, digest, prior_attempt = PRODUCTS[role]
    terminal = ROOT / "records/readiness/m2-landsat9-grouped-mtl-recovery-002-terminal-reconciliation.json"
    t = read_json(terminal)
    r = t[role]
    receipt_path = INTAKE / prior_attempt / "verification.json"
    if sha256_file(receipt_path) != r["external_receipt_sha256"]["verification.json"]:
        raise RouteStop("prior_verification_receipt_drift")
    receipt = read_json(receipt_path)
    if ((receipt.get("product_id"), receipt.get("scene_id"), receipt.get("archive_size_bytes"),
         receipt.get("archive_sha256")) != (product, scene, size, digest)
            or receipt.get("status") != "pass_container_and_grouped_mtl_identity_only"):
        raise RouteStop("prior_verification_identity_invalid")
    return receipt


def preflight(public_ci_commit: str, public_ci_run: str) -> dict:
    """No TAR internals or TIFFs: freeze controls, exact archives, receipts and paths."""
    _check_controls()
    if not re.fullmatch(r"[0-9a-f]{40}", public_ci_commit) or not re.fullmatch(r"[0-9]{8,20}", public_ci_run):
        raise RouteStop("public_ci_reference_invalid")
    if not DATA.is_dir() or DATA.is_symlink() or is_reparse_point(DATA):
        raise RouteStop("controlled_data_root_unsafe")
    if ATTEMPT.exists() or ATTEMPT.is_symlink() or is_reparse_point(ATTEMPT):
        raise RouteStop("real_attempt_already_consumed")
    runtime = Path(r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe")
    if not runtime.is_file():
        raise RouteStop("installed_arcgis_runtime_missing")
    if shutil.disk_usage(DATA).free < 5 * 1024**3:
        raise RouteStop("insufficient_non_git_space")
    evidence = {}
    for role in ("before", "after"):
        product, _, size, expected, _ = PRODUCTS[role]
        archive = DATA / "custody/landsat9-c2l2" / f"{product}.tar"
        if (not archive.is_file() or archive.is_symlink() or is_reparse_point(archive)
                or archive.stat().st_size != size or sha256_file(archive) != expected):
            raise RouteStop("promoted_archive_identity_drift")
        receipt = _receipt(role)
        evidence[role] = {"product_id": product, "archive_size_bytes": size,
                          "archive_sha256": expected, "verified_member_count": len(receipt["members"])}
    return {"schema_version": "1.0", "status": "pass_final_no_content_preflight",
            "checked_at_utc": now(), "approval_sha256": APPROVAL_SHA,
            "proposal_sha256": PROPOSAL_SHA, "review_bundle_sha256": BUNDLE_SHA,
            "implementation_public_ci_commit": public_ci_commit,
            "implementation_public_ci_run_id": public_ci_run,
            "archive_checks": evidence, "real_tiff_header_or_pixel_read": False,
            "network_or_provider_request": False}


def extract_exact(role: str, root: Path) -> dict[str, Path]:
    product, _, expected_size, expected_sha, _ = PRODUCTS[role]
    receipt = _receipt(role)
    expected = {PurePosixPath(item["name"]).name: item for item in receipt["members"]}
    target = root / "members"
    target.mkdir(exist_ok=False)
    archive = DATA / "custody/landsat9-c2l2" / f"{product}.tar"
    if (not archive.is_file() or archive.is_symlink() or is_reparse_point(archive)
            or archive.stat().st_size != expected_size or sha256_file(archive) != expected_sha):
        raise RouteStop("promoted_archive_identity_drift")
    paths = {}
    with tarfile.open(archive, "r:") as tar:
        names = {PurePosixPath(m.name).name: m for m in tar.getmembers() if m.isfile()}
        for suffix in SUFFIXES:
            name = product + suffix
            member = names.get(name)
            item = expected.get(name)
            if (member is None or item is None or member.size != item["size_bytes"]
                    or PurePosixPath(member.name).name != name):
                raise RouteStop("exact_member_missing_or_size_drift")
            stream = tar.extractfile(member)
            if stream is None:
                raise RouteStop("exact_member_unreadable")
            destination = target / name
            digest = hashlib.sha256()
            count = 0
            with stream, destination.open("xb") as output:
                for block in iter(lambda: stream.read(8 * 1024**2), b""):
                    count += len(block)
                    digest.update(block)
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
            if count != item["size_bytes"] or digest.hexdigest() != item["sha256"]:
                raise RouteStop("materialized_member_hash_drift")
            paths[suffix] = destination
    if archive.stat().st_size != expected_size or sha256_file(archive) != expected_sha:
        raise RouteStop("promoted_archive_changed_during_materialization")
    return paths


def mtl_fields(paths: dict[str, Path], role: str) -> dict:
    product, scene, _, _, _ = PRODUCTS[role]
    text = paths["_MTL.txt"].read_bytes()
    xml = paths["_MTL.xml"].read_bytes()
    _verify_grouped_metadata(text, xml, product, scene)
    values = {}
    for line in text.decode("utf-8-sig").splitlines():
        match = re.fullmatch(r"\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*", line)
        if match:
            key, val = match.groups()
            if key in values and values[key] != val:
                raise RouteStop("mtl_field_duplicate_disagreement")
            values[key] = val.strip('"')
    if values.get("DATE_ACQUIRED", "").replace("-", "") != product.split("_")[3]:
        raise RouteStop("mtl_acquisition_date_mismatch")
    if not re.fullmatch(r"[0-9:.]+Z", values.get("SCENE_CENTER_TIME", "")):
        raise RouteStop("mtl_scene_center_time_invalid")
    for band in range(3, 8):
        try:
            mult = float(values[f"REFLECTANCE_MULT_BAND_{band}"])
            add = float(values[f"REFLECTANCE_ADD_BAND_{band}"])
        except (KeyError, ValueError):
            raise RouteStop("mtl_reflectance_scale_missing") from None
        if not (math.isclose(mult, SCALE, rel_tol=0, abs_tol=1e-12)
                and math.isclose(add, OFFSET, rel_tol=0, abs_tol=1e-12)):
            raise RouteStop("mtl_reflectance_scale_mismatch")
    return {"date_acquired": values["DATE_ACQUIRED"],
            "scene_center_time": values["SCENE_CENTER_TIME"],
            "reflectance_mult": SCALE, "reflectance_add": OFFSET}


def tiff_georeference(path: Path) -> dict:
    """Read first-IFD GeoTIFF transform tags only; never decode image blocks."""
    with path.open("rb") as file:
        order = file.read(2)
        if order not in (b"II", b"MM"):
            raise RouteStop("tiff_byte_order_invalid")
        endian = "<" if order == b"II" else ">"
        magic = struct.unpack(endian + "H", file.read(2))[0]
        if magic == 42:
            offset = struct.unpack(endian + "I", file.read(4))[0]
            count_format, entry_size, value_size = "H", 12, 4
            offset_format, count_width = "I", 2
        elif magic == 43:
            size, reserved = struct.unpack(endian + "HH", file.read(4))
            if size != 8 or reserved != 0:
                raise RouteStop("bigtiff_header_invalid")
            offset = struct.unpack(endian + "Q", file.read(8))[0]
            count_format, entry_size, value_size = "Q", 20, 8
            offset_format, count_width = "Q", 8
        else:
            raise RouteStop("tiff_magic_invalid")
        if offset <= 0 or offset >= path.stat().st_size:
            raise RouteStop("tiff_ifd_offset_invalid")
        file.seek(offset)
        count = struct.unpack(endian + count_format, file.read(count_width))[0]
        if count > 256:
            raise RouteStop("tiff_ifd_tag_count_invalid")
        tags = {}
        for _ in range(count):
            raw = file.read(entry_size)
            if len(raw) != entry_size:
                raise RouteStop("tiff_ifd_truncated")
            tag, kind = struct.unpack(endian + "HH", raw[:4])
            n = struct.unpack(endian + ("I" if magic == 42 else "Q"), raw[4:(8 if magic == 42 else 12)])[0]
            if tag not in (33550, 33922, 34264):
                continue
            if kind != 12 or n > 32:
                raise RouteStop("tiff_georeference_tag_invalid")
            val = raw[-value_size:]
            byte_count = n * 8
            if byte_count > value_size:
                pointer = struct.unpack(endian + offset_format, val)[0]
                if pointer <= 0 or pointer + byte_count > path.stat().st_size:
                    raise RouteStop("tiff_georeference_tag_offset_invalid")
                here = file.tell()
                file.seek(pointer)
                val = file.read(byte_count)
                file.seek(here)
            tags[tag] = struct.unpack(endian + str(n) + "d", val[:byte_count])
    if 34264 in tags:
        transform = tags[34264]
        if len(transform) != 16:
            raise RouteStop("tiff_transform_shape_invalid")
        rotation_x, rotation_y = transform[1], transform[4]
        cell_x, cell_y = abs(transform[0]), abs(transform[5])
    elif 33550 in tags and 33922 in tags:
        scales = tags[33550]
        if len(scales) != 3 or len(tags[33922]) < 6:
            raise RouteStop("tiff_scale_or_tiepoint_invalid")
        rotation_x = rotation_y = 0.
        cell_x, cell_y = scales[0], scales[1]
    else:
        raise RouteStop("tiff_georeference_tags_missing")
    if not all(math.isfinite(value) for value in (rotation_x, rotation_y, cell_x, cell_y)):
        raise RouteStop("tiff_georeference_nonfinite")
    return {"rotation_x": rotation_x, "rotation_y": rotation_y,
            "tag_cell_x": cell_x, "tag_cell_y": cell_y}


def raster_headers(paths: dict[str, Path], arcpy) -> dict[str, dict]:
    headers = {}
    for role in ROLES:
        suffix = "_" + role + ".TIF"
        geotiff = tiff_georeference(paths[suffix])
        raster = arcpy.Raster(str(paths[suffix]))
        extent = raster.extent
        try:
            nodata = raster.noDataValue
            nodata = None if nodata is None else float(nodata)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            nodata = None
        headers[role] = {
            "wkid": raster.spatialReference.factoryCode, "bands": raster.bandCount,
            "rows": raster.height, "columns": raster.width,
            "cell_x": raster.meanCellWidth, "cell_y": raster.meanCellHeight,
            "xmin": extent.XMin, "ymin": extent.YMin,
            "xmax": extent.XMax, "ymax": extent.YMax,
            "nodata": nodata, "pixel_type": raster.pixelType,
            **geotiff,
        }
        if abs(geotiff["tag_cell_x"] - raster.meanCellWidth) > 1e-6 or abs(geotiff["tag_cell_y"] - raster.meanCellHeight) > 1e-6:
            raise RouteStop("tiff_arcgis_georeference_disagreement")
    return headers


def aoi_window(ring: list, grid: dict) -> tuple[float, float, int, int]:
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    c0 = math.floor((min(xs) - grid["xmin"]) / CELL)
    c1 = math.ceil((max(xs) - grid["xmin"]) / CELL)
    r0 = math.floor((grid["ymax"] - max(ys)) / CELL)
    r1 = math.ceil((grid["ymax"] - min(ys)) / CELL)
    if c1 <= c0 or r1 <= r0:
        raise RouteStop("aoi_window_empty")
    return grid["xmin"] + c0 * CELL, grid["ymax"] - r0 * CELL, c1 - c0, r1 - r0


def read_window(path: Path, header: dict, xmin: float, ymax: float,
                columns: int, rows: int, fill: int, arcpy) -> tuple[np.ndarray, np.ndarray]:
    output = np.full((rows, columns), fill, dtype=np.uint16)
    footprint = np.zeros((rows, columns), dtype=bool)
    dc = (xmin - header["xmin"]) / CELL
    dr = (header["ymax"] - ymax) / CELL
    if abs(dc - round(dc)) > 1e-6 or abs(dr - round(dr)) > 1e-6:
        raise RouteStop("pixel_window_lattice_mismatch")
    dc, dr = round(dc), round(dr)
    sc0, sc1 = max(0, dc), min(header["columns"], dc + columns)
    sr0, sr1 = max(0, dr), min(header["rows"], dr + rows)
    if sc1 <= sc0 or sr1 <= sr0:
        return output, footprint
    lower_left = arcpy.Point(header["xmin"] + sc0 * CELL,
                             header["ymax"] - sr1 * CELL)
    array = np.asarray(arcpy.RasterToNumPyArray(str(path), lower_left,
                                               sc1 - sc0, sr1 - sr0,
                                               nodata_to_value=fill))
    if array.shape != (sr1 - sr0, sc1 - sc0) or array.dtype.kind not in "iu":
        raise RouteStop("pixel_window_shape_or_type_invalid")
    tr0, tc0 = sr0 - dr, sc0 - dc
    output[tr0:tr0 + array.shape[0], tc0:tc0 + array.shape[1]] = array
    footprint[tr0:tr0 + array.shape[0], tc0:tc0 + array.shape[1]] = True
    return output, footprint


def read_aoi_date(paths: dict[str, Path], headers: dict, window: tuple,
                  arcpy) -> tuple[dict, np.ndarray]:
    xmin, ymax, columns, rows = window
    arrays, footprints, nodata = {}, [], []
    for role in ROLES:
        suffix = "_" + role + ".TIF"
        fill = 255 if role == "SR_QA_AEROSOL" else 65535
        array, footprint = read_window(paths[suffix], headers[role], xmin, ymax,
                                       columns, rows, fill, arcpy)
        arrays[role] = array
        footprints.append(footprint)
        nodata.append(fill if headers[role]["nodata"] is None else headers[role]["nodata"])
    if not all(np.array_equal(footprints[0], other) for other in footprints[1:]):
        raise RouteStop("within_scene_pixel_footprint_mismatch")
    bands = np.stack([arrays[f"SR_B{i}"] for i in range(3, 8)])
    result = classify_pixels(arrays["QA_PIXEL"], arrays["QA_RADSAT"],
                             arrays["SR_QA_AEROSOL"], bands, footprints[0], nodata)
    return result, footprints[0]


def _safe_code(exc: BaseException) -> str:
    code = str(exc)
    return code if isinstance(exc, (RouteStop, PixelMethodError)) and re.fullmatch(r"[a-z0-9_]+", code) else "local_io_or_unexpected_failure"


def run_once(gate: dict, arcpy) -> dict:
    if gate.get("status") != "pass_final_no_content_preflight" or gate.get("approval_sha256") != APPROVAL_SHA:
        raise RouteStop("final_preflight_gate_invalid")
    _check_controls()
    if ATTEMPT.exists() or ATTEMPT.is_symlink():
        raise RouteStop("real_attempt_already_consumed")
    ATTEMPT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT.mkdir(exist_ok=False)
    try:
        write_new(ATTEMPT / "started.json", {"status": "reserved_before_real_content_read",
                                           "started_at_utc": now(),
                                           "approval_sha256": APPROVAL_SHA,
                                           "implementation_public_ci_commit": gate["implementation_public_ci_commit"],
                                           "implementation_public_ci_run_id": gate["implementation_public_ci_run_id"]})
    except BaseException:
        write_new(ATTEMPT / "terminal-fallback.json", {
            "status": "block_reservation_receipt_persistence_failure",
            "terminal_at_utc": now(), "real_content_read": False})
        return {"status": "block_reservation_receipt_persistence_failure",
                "stage": "reservation", "reason": "reservation_receipt_persistence_failed"}
    result = {"status": "stopped", "stage": "before", "reason": None}
    try:
        paths, headers, mtls = {}, {}, {}
        for role in ("before", "after"):
            result["stage"] = role + "_header"
            role_root = ATTEMPT / role
            role_root.mkdir(exist_ok=False)
            write_new(role_root / "started.json", {"status": "reserved_exact_source_header_attempt", "at_utc": now(), "role": role})
            paths[role] = extract_exact(role, role_root)
            mtls[role] = mtl_fields(paths[role], role)
            headers[role] = raster_headers(paths[role], arcpy)
            validate_headers({"before": headers[role], "after": headers[role]})
            write_new(role_root / "header.json", {"status": "pass_single_scene_header_only",
                                                   "role": role, "mtl": mtls[role],
                                                   "tiff_headers": headers[role],
                                                   "pixel_read": False})
        result["stage"] = "cross_scene_header"
        grid = validate_headers(headers)
        write_new(ATTEMPT / "pair-header.json", {"status": "pass_shared_30m_epsg32645_lattice_only", "grid": grid})
        aoi = read_json(AOI)
        rings = {f["attributes"]["AOI_ID"]: f["geometry"]["rings"][0]
                 for f in aoi["features"] if f["attributes"]["AOI_ID"] in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR")}
        if set(rings) != {"AOI-SOURCE", "AOI-UPPER-CORRIDOR"}:
            raise RouteStop("approved_aoi_ids_missing")
        all_metrics, panel_data = {}, {}
        for aoi_id in ("AOI-SOURCE", "AOI-UPPER-CORRIDOR"):
            result["stage"] = "pixel_qa_" + aoi_id.lower().replace("-", "_")
            window = aoi_window(rings[aoi_id], grid["before"])
            xmin, ymax, cols, rows = window
            weights = aoi_cell_weights(rings[aoi_id], xmin, ymax, cols, rows)
            before, before_fp = read_aoi_date(paths["before"], headers["before"], window, arcpy)
            after, after_fp = read_aoi_date(paths["after"], headers["after"], window, arcpy)
            metrics = weighted_metrics(weights, before, after, before_fp, after_fp)
            all_metrics[aoi_id] = metrics
            # Local NPZ is retained for the one conditional panel; never Git-published.
            np.savez_compressed(ATTEMPT / (aoi_id.lower() + "-panel-data.npz"),
                                weights=weights, before_reason=before["reason"],
                                after_reason=after["reason"],
                                before_bands=before["calibrated"][[4, 3, 1]],
                                after_bands=after["calibrated"][[4, 3, 1]],
                                xmin=xmin, ymax=ymax)
            panel_data[aoi_id] = {"window": window,
                                  "npz": aoi_id.lower() + "-panel-data.npz"}
        write_new(ATTEMPT / "pixel-qa.json", {"status": "measured_visual_only_qa",
                                              "evaluated_at_utc": now(),
                                              "aoi_metrics": all_metrics,
                                              "registration_residual_measured": False,
                                              "change_analysis_performed": False})
        qualifying = [key for key, value in all_metrics.items()
                      if value["visual_status"] != "no_visual_panel_for_aoi"]
        result = {"status": "pass_pixel_qa_visual_only_no_panel_qualified" if not qualifying
                  else "pass_pixel_qa_panel_qualified_pending_arcgis",
                  "stage": "pixel_qa_complete", "qualifying_aois": qualifying,
                  "aoi_metrics": all_metrics,
                  "registration_residual_measured": False,
                  "change_analysis_or_attribution": False,
                  "public_derived_pixel_publication": False}
        if qualifying:
            result["stage"] = "arcgis_visual_panel"
            output = ATTEMPT / "panel"
            built = build_panel(ATTEMPT, all_metrics, panel_data, mtls, output, arcpy)
            write_new(ATTEMPT / "panel-build.json", built)
            reopened = fresh_reopen(output)
            write_new(ATTEMPT / "panel-reopen.json", reopened)
            result["status"] = "pass_local_arcgis_visual_panel_only"
            result["stage"] = "panel_fresh_reopen_complete"
            result["panel_artifacts"] = {
                "aprx_sha256": built["aprx_sha256"], "png_sha256": built["png_sha256"],
                "pdf_sha256": built["pdf_sha256"],
                "reopen_png_sha256": reopened["reopen_png_sha256"],
                "wkid": 32645}
    except BaseException as exc:
        result = {"status": "blocked_terminal_no_retry", "stage": result["stage"],
                  "reason": _safe_code(exc), "change_analysis_or_attribution": False,
                  "public_derived_pixel_publication": False}
    try:
        write_new(ATTEMPT / "terminal.json", {**result, "terminal_at_utc": now()})
    except BaseException:
        result = {"status": "block_terminal_receipt_persistence_failure",
                  "stage": result.get("stage", "unknown"),
                  "reason": "terminal_receipt_persistence_failed",
                  "change_analysis_or_attribution": False,
                  "public_derived_pixel_publication": False}
        write_new(ATTEMPT / "terminal-fallback.json", {**result, "terminal_at_utc": now()})
    try:
        write_new(ATTEMPT / "cleanup.json", {
            "status": "local_attempt_outputs_retained_for_audit",
            "recorded_at_utc": now(), "source_archives_overwritten_or_removed": False,
            "provider_request_or_retry": False})
    except BaseException:
        write_new(ATTEMPT / "cleanup-fallback.json", {
            "status": "cleanup_receipt_persistence_failed_outputs_retained",
            "recorded_at_utc": now(), "source_archives_overwritten_or_removed": False})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    parser.add_argument("--public-ci-commit")
    parser.add_argument("--public-ci-run")
    parser.add_argument("--gate")
    args = parser.parse_args()
    try:
        if args.mode == "preflight":
            result = preflight(args.public_ci_commit or "", args.public_ci_run or "")
            print(json.dumps(result, sort_keys=True))
            return 0
        import arcpy  # type: ignore[import-not-found]
        gate = read_json(Path(args.gate or ""))
        result = run_once(gate, arcpy)
        print(json.dumps({k: v for k, v in result.items() if k not in ("aoi_metrics", "panel_data")}, sort_keys=True))
        return 0 if result["status"].startswith("pass_") else 20
    except BaseException as exc:
        print(json.dumps({"status": "stopped_before_real_attempt", "code": _safe_code(exc)}, sort_keys=True))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
