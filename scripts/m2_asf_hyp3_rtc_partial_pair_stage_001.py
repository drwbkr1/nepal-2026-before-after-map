#!/usr/bin/env python3
"""Gated one-attempt preparation of the exact ASF visual-only RTC pair.

No provider pixels are read until exact before/after custody, metadata rights,
headers, individual pixel QA, public CI and no-content gates all pass. A
passing pair remains a local partial visual, never scientific change evidence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from m2_asf_hyp3_rtc_acquire_after_partial_001 import DATA_ROOT, SUBMISSION_REF
from m2_asf_hyp3_rtc_after_descriptor_core_001 import (
    SOURCE_ID as AFTER_SOURCE, submission_view,
)
from m2_asf_hyp3_rtc_after_header_001 import (
    ACQUISITION_REF as AFTER_ACQUISITION_REF,
    APPROVAL_REF, APPROVAL_SHA, METADATA_REVIEW_REF as AFTER_REVIEW_REF,
    SOURCE_GATE_REF, SOURCE_GATE_SHA,
    _json, _now, _safe_dir, _safe_file, _sha, _write_json,
)
from m2_asf_hyp3_rtc_composite_provenance_core_001 import (
    ARCHIVE_SHA256 as BEFORE_ARCHIVE_SHA,
    ARCHIVE_SIZE as BEFORE_ARCHIVE_SIZE,
    JOB_ID as BEFORE_JOB, PRODUCT_FILENAME as BEFORE_FILENAME,
    SOURCE_ID as BEFORE_SOURCE,
)
from m2_asf_hyp3_rtc_core_001 import ROOT, RouteStop
from m2_asf_hyp3_rtc_product_pixel_001 import (
    AOI_REF, AOI_SHA256, CONTRACT_REF, CONTRACT_SHA256, _load_aois,
)


BEFORE_ARCHIVE_REF = "m2-asf-hyp3-rtc-products-001/" + BEFORE_FILENAME
BEFORE_ACQUISITION_REF = "m2-asf-hyp3-rtc-acquire-first-001/attempt-001/terminal.json"
BEFORE_REVIEW_REF = "records/readiness/m2-asf-hyp3-rtc-product-metadata-001-local-review.json"
BEFORE_HEADER_REF = "m2-asf-hyp3-rtc-product-header-001/attempt-001/terminal.json"
BEFORE_PIXEL_REF = "m2-asf-hyp3-rtc-product-pixel-001/attempt-001/terminal.json"
AFTER_HEADER_REF = "m2-asf-hyp3-rtc-after-header-001/attempt-001/terminal.json"
AFTER_PIXEL_REF = "m2-asf-hyp3-rtc-after-pixel-001/attempt-001/terminal.json"
RIGHTS_REF = "records/readiness/m2-asf-hyp3-rtc-partial-pair-rights-review-001.json"
GATE_REF = "records/readiness/m2-asf-hyp3-rtc-partial-pair-stage-001-implementation-gate.json"
PREFLIGHT_REF = "records/readiness/m2-asf-hyp3-rtc-partial-pair-stage-001-preflight.json"
ATTEMPT_ROOT = DATA_ROOT / "m2-asf-hyp3-rtc-partial-pair-stage-001" / "attempt-001"
IMPLEMENTATION_FILES = (
    "scripts/m2_asf_hyp3_rtc_partial_pair_stage_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_pair_stage_io_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_pair_stage_core_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_pair_grid_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_pair_core_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_pair_map_001.py",
    "scripts/m2_asf_hyp3_rtc_partial_panel_audit_001.py",
    "scripts/validate_m2_asf_hyp3_rtc_partial_pair_stage_arcgis_synthetic_001.py",
    "scripts/validate_m2_asf_hyp3_rtc_partial_pair_stage_route_arcgis_synthetic_001.py",
    "tests/test_m2_asf_hyp3_rtc_partial_pair_stage_001.py",
    "tests/test_m2_asf_hyp3_rtc_partial_pair_stage_core_001.py",
)


def _source_pixel_ready(before: dict, after: dict) -> bool:
    if (before.get("source_id") != BEFORE_SOURCE
            or before.get("job_id") != BEFORE_JOB
            or before.get("status") != "stop_source_event_aoi_pixel_qa_no_next_date"
            or before.get("archive_sha256_verified_current") is not True
            or before.get("VV_VH_layover_shadow_AOI_pixels_read") is not True
            or after.get("source_id") != AFTER_SOURCE
            or after.get("archive_sha256_verified_current") is not True
            or after.get("VV_VH_layover_shadow_AOI_pixels_read") is not True
            or after.get("disposition", {}).get(
                "partial_pair_candidate_pending_same_cell_overlap") is not True):
        return False
    for record in (before, after):
        rows = record.get("aoi_results")
        if (not isinstance(rows, list) or len(rows) != 2
                or [row.get("aoi_id") for row in rows if isinstance(row, dict)]
                != ["AOI-SOURCE", "AOI-UPPER-CORRIDOR"]):
            return False
        for row in rows:
            if (row.get("unknown_provider_mask_value_present") is not False
                    or row.get("status") not in {"pass_qa_only", "defer"}
                    or type(row.get("valid_area_m2")) not in (int, float)
                    or type(row.get("aoi_area_m2")) not in (int, float)
                    or row["aoi_area_m2"] <= 0
                    or row["valid_area_m2"] / row["aoi_area_m2"] < .2):
                return False
    return True


def require_release(root: Path = ROOT, data_root: Path = DATA_ROOT,
                    attempt_root: Path = ATTEMPT_ROOT) -> tuple[dict, Path, Path, dict, dict]:
    """Prove an exact released attempt without opening either provider ZIP."""
    paths = {
        "approval": root / APPROVAL_REF,
        "source_gate": root / SOURCE_GATE_REF,
        "rights": root / RIGHTS_REF,
        "gate": root / GATE_REF,
        "preflight": root / PREFLIGHT_REF,
        "aoi": root / AOI_REF,
        "contract": root / CONTRACT_REF,
        "submission": data_root / SUBMISSION_REF,
        "before_acquisition": data_root / BEFORE_ACQUISITION_REF,
        "before_review": root / BEFORE_REVIEW_REF,
        "before_header": data_root / BEFORE_HEADER_REF,
        "before_pixel": data_root / BEFORE_PIXEL_REF,
        "after_acquisition": data_root / AFTER_ACQUISITION_REF,
        "after_review": root / AFTER_REVIEW_REF,
        "after_header": data_root / AFTER_HEADER_REF,
        "after_pixel": data_root / AFTER_PIXEL_REF,
    }
    if any(not _safe_file(path) for path in paths.values()):
        raise RouteStop("partial_pair_stage_required_path_invalid")
    records = {name: _json(path) for name, path in paths.items()
               if name not in {"aoi", "contract"}}
    before_archive = data_root / BEFORE_ARCHIVE_REF
    after_name = records["after_acquisition"].get("product_filename")
    if (not isinstance(after_name, str) or after_name != Path(after_name).name
            or not after_name.endswith(".zip")):
        raise RouteStop("partial_pair_stage_after_name_invalid")
    after_archive = data_root / "m2-asf-hyp3-rtc-products-after-partial-001" / after_name
    if (not _safe_dir(data_root) or not _safe_file(before_archive)
            or not _safe_file(after_archive)
            or attempt_root.parent.parent.resolve() != data_root.resolve()
            or attempt_root.parent.is_symlink()
            or (attempt_root.parent.exists() and not _safe_dir(attempt_root.parent))
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("partial_pair_stage_path_or_attempt_invalid")
    approval, rights, gate, preflight = (
        records[key] for key in ("approval", "rights", "gate", "preflight")
    )
    before_acq, after_acq = (records[key] for key in
                             ("before_acquisition", "after_acquisition"))
    before_header, after_header = (records[key] for key in
                                    ("before_header", "after_header"))
    before_pixel, after_pixel = (records[key] for key in
                                  ("before_pixel", "after_pixel"))
    files = gate.get("bindings", {}).get("implementation_file_sha256")
    try:
        job = submission_view(records["submission"])["job_id"]
        valid = (
            _sha(paths["approval"]) == APPROVAL_SHA
            and approval.get("decision") == "approve"
            and approval.get("authority", {}).get(
                "conditional_local_EPSG_32645_partial_pair_panel_and_fresh_process_export") is True
            and _sha(paths["source_gate"]) == SOURCE_GATE_SHA
            and records["source_gate"].get("decision", {}).get("status") == "ready"
            and _sha(paths["aoi"]) == AOI_SHA256
            and _sha(paths["contract"]) == CONTRACT_SHA256
            and before_acq.get("status") == "pass_local_zip_promoted_no_replace"
            and before_acq.get("source_id") == BEFORE_SOURCE
            and before_acq.get("job_id") == BEFORE_JOB
            and before_acq.get("archive_sha256") == BEFORE_ARCHIVE_SHA
            and before_acq.get("archive_size_bytes") == BEFORE_ARCHIVE_SIZE
            and before_archive.stat().st_size == BEFORE_ARCHIVE_SIZE
            and after_acq.get("status") == "pass_local_zip_promoted_no_replace"
            and after_acq.get("source_id") == AFTER_SOURCE
            and after_acq.get("job_id") == job
            and after_acq.get("archive_integrity_verified") is True
            and after_archive.stat().st_size == after_acq.get("archive_size_bytes")
            and records["before_review"].get("status")
                == "pass_product_metadata_for_separate_local_header_and_pixel_qa_only"
            and records["before_review"].get("bindings", {}).get("archive_sha256")
                == BEFORE_ARCHIVE_SHA
            and records["before_review"].get("source_id") == BEFORE_SOURCE
            and records["before_review"].get("job_id") == BEFORE_JOB
            and records["after_review"].get("status")
                == "pass_after_metadata_for_header_and_pixel_qa_only"
            and records["after_review"].get("bindings", {}).get("archive_sha256")
                == after_acq.get("archive_sha256")
            and records["after_review"].get("source_id") == AFTER_SOURCE
            and records["after_review"].get("job_id") == job
            and before_header.get("status") == "pass_actual_headers_for_local_pixel_qa_only"
            and before_header.get("source_id") == BEFORE_SOURCE
            and before_header.get("job_id") == BEFORE_JOB
            and before_header.get("archive_sha256_verified_current") is True
            and after_header.get("status") == "pass_after_headers_for_local_pixel_qa_only"
            and after_header.get("source_id") == AFTER_SOURCE
            and after_header.get("job_id") == job
            and after_header.get("archive_sha256_verified_current") is True
            and _source_pixel_ready(before_pixel, after_pixel)
            and after_pixel.get("job_id") == job
            and rights.get("status") == "pass_local_rtc_vv_visual_display_only"
            and rights.get("bindings", {}).get("before_review_sha256")
                == _sha(paths["before_review"])
            and rights.get("bindings", {}).get("after_review_sha256")
                == _sha(paths["after_review"])
            and rights.get("local_VV_display") is True
            and rights.get("DEM_display_or_export") is False
            and rights.get("public_derived_pixels") is False
            and gate.get("status") == "pass_partial_pair_stage_implementation_public_ci_only"
            and gate.get("public_ci", {}).get("conclusion") == "success"
            and gate.get("bindings", {}).get("approval_sha256") == APPROVAL_SHA
            and gate.get("bindings", {}).get("rights_review_sha256") == _sha(paths["rights"])
            and gate.get("bindings", {}).get("submission_sha256")
                == _sha(paths["submission"])
            and gate.get("bindings", {}).get("before_review_sha256")
                == _sha(paths["before_review"])
            and gate.get("bindings", {}).get("after_review_sha256")
                == _sha(paths["after_review"])
            and all(gate.get("bindings", {}).get(key + "_sha256") == _sha(paths[key])
                    for key in ("before_acquisition", "before_header", "before_pixel",
                                "after_acquisition", "after_header", "after_pixel"))
            and gate.get("bindings", {}).get("aoi_sha256") == AOI_SHA256
            and gate.get("bindings", {}).get("contract_sha256") == CONTRACT_SHA256
            and isinstance(files, dict) and set(files) == set(IMPLEMENTATION_FILES)
            and all(_sha(root / ref) == files[ref] for ref in IMPLEMENTATION_FILES)
            and preflight.get("status") == "pass_partial_pair_stage_no_content"
            and preflight.get("bindings", {}).get("implementation_gate_sha256")
                == _sha(paths["gate"])
            and preflight.get("bindings", {}).get("before_acquisition_sha256")
                == _sha(paths["before_acquisition"])
            and preflight.get("bindings", {}).get("after_acquisition_sha256")
                == _sha(paths["after_acquisition"])
            and preflight.get("assertions", {}).get("attempt_absent") is True
            and preflight.get("assertions", {}).get("no_pair_pixel_read") is True
        )
    except (OSError, TypeError, ValueError, KeyError):
        raise RouteStop("partial_pair_stage_release_unavailable") from None
    if not valid:
        raise RouteStop("partial_pair_stage_not_released")
    return after_acq, before_archive, after_archive, before_header, after_header


def stage_real_pair(before_archive: Path, after_archive: Path,
                    before_header: dict, after_header: dict,
                    output: Path, root: Path = ROOT) -> dict:
    """Open only VV, VH and layover/shadow after the release gate passes."""
    from osgeo import gdal

    from m2_asf_hyp3_rtc_partial_pair_stage_io_001 import stage_from_open_datasets
    from m2_asf_hyp3_rtc_product_header_001 import describe_vsi
    from pixel_qa_core import load_contract

    datasets = {}
    try:
        for label, archive, frozen in (("before", before_archive, before_header),
                                       ("after", after_archive, after_header)):
            for role, suffix in (("vv", "VV"), ("vh", "VH"), ("mask", "ls_map")):
                base = archive.stem
                member = f"{base}/{base}_{suffix}.tif"
                actual = describe_vsi(archive, member)
                if actual != frozen.get("headers", {}).get("ls_map" if role == "mask" else role):
                    raise RouteStop("partial_pair_stage_header_drift")
                dataset = gdal.OpenEx("/vsizip/" + archive.as_posix() + "/" + member,
                                      gdal.OF_RASTER)
                if dataset is None:
                    raise RouteStop("partial_pair_stage_vsi_open_failed")
                datasets[f"{label}_{role}"] = dataset
        aois = _load_aois(root)
        return stage_from_open_datasets(
            datasets=datasets, rings=dict(aois),
            contract=load_contract(root / CONTRACT_REF), output=output,
        )
    finally:
        datasets.clear()


def process_once(after_acq: dict, before_archive: Path, after_archive: Path,
                 before_header: dict, after_header: dict,
                 attempt_root: Path = ATTEMPT_ROOT, *,
                 controlled_root: Path = DATA_ROOT, stage=stage_real_pair,
                 root: Path = ROOT) -> dict:
    """Reserve once, rehash both ZIPs and preserve either result or failure."""
    if (not _safe_dir(controlled_root)
            or attempt_root.parent.parent.resolve() != controlled_root.resolve()
            or attempt_root.parent.is_symlink()
            or attempt_root.exists() or attempt_root.is_symlink()):
        raise RouteStop("partial_pair_stage_attempt_collision")
    try:
        attempt_root.parent.mkdir(parents=True, exist_ok=True)
        if not _safe_dir(attempt_root.parent):
            raise RouteStop("partial_pair_stage_attempt_parent_invalid")
        attempt_root.mkdir(exist_ok=False)
    except RouteStop:
        raise
    except OSError:
        raise RouteStop("partial_pair_stage_attempt_reservation_failed") from None
    _write_json(attempt_root / "started.json", {
        "status": "partial_pair_stage_reserved", "started_at_utc": _now(),
        "source_ids": [BEFORE_SOURCE, AFTER_SOURCE],
        "provider_zip_mutated": False, "scientific_admission": False,
    })
    try:
        if (not _safe_file(before_archive) or not _safe_file(after_archive)
                or before_archive.stat().st_size != BEFORE_ARCHIVE_SIZE
                or _sha(before_archive) != BEFORE_ARCHIVE_SHA
                or after_archive.name != after_acq.get("product_filename")
                or after_archive.stat().st_size != after_acq.get("archive_size_bytes")
                or _sha(after_archive) != after_acq.get("archive_sha256")):
            raise RouteStop("partial_pair_stage_archive_identity_mismatch")
        before_stat, after_stat = before_archive.stat(), after_archive.stat()
        result = stage(before_archive, after_archive, before_header, after_header,
                       attempt_root / "display", root)
        if any((prior.st_size, prior.st_mtime_ns, prior.st_ino)
               != (current.st_size, current.st_mtime_ns, current.st_ino)
               for prior, current in ((before_stat, before_archive.stat()),
                                      (after_stat, after_archive.stat()))):
            raise RouteStop("partial_pair_stage_archive_changed_during_read")
        terminal = {
            "status": result["status"], "finished_at_utc": _now(),
            "source_ids": [BEFORE_SOURCE, AFTER_SOURCE],
            "after_job_id": after_acq.get("job_id"),
            "pair_stage_result": result, "provider_zip_mutated": False,
            "registration_measured": False, "scientific_admission": False,
            "change_analysis_or_attribution": False,
            "map_or_export_created": False,
        }
    except RouteStop as exc:
        terminal = {"status": "stopped_partial_pair_stage_no_automatic_retry",
                    "code": exc.code, "finished_at_utc": _now(),
                    "source_ids": [BEFORE_SOURCE, AFTER_SOURCE],
                    "pair_pixel_status": "indeterminate_on_failure",
                    "provider_zip_mutated": False, "map_or_export_created": False}
    except BaseException:
        terminal = {"status": "stopped_partial_pair_stage_no_automatic_retry",
                    "code": "partial_pair_stage_unexpected_failure",
                    "finished_at_utc": _now(),
                    "source_ids": [BEFORE_SOURCE, AFTER_SOURCE],
                    "pair_pixel_status": "indeterminate_on_failure",
                    "provider_zip_mutated": False, "map_or_export_created": False}
    _write_json(attempt_root / "terminal.json", terminal)
    return terminal


def main() -> int:
    try:
        after_acq, before_archive, after_archive, before_header, after_header = require_release()
        if sys.argv[1:] == ["--check-release"]:
            print(json.dumps({"status": "pass_partial_pair_stage_release_no_product_read"}))
            return 0
        if sys.argv[1:]:
            raise RouteStop("partial_pair_stage_arguments_invalid")
        terminal = process_once(after_acq, before_archive, after_archive,
                                before_header, after_header)
        print(json.dumps({"status": terminal["status"],
                          "code": terminal.get("code"),
                          "map_or_export_created": False}, sort_keys=True))
        return 12 if terminal["status"].startswith("stopped_") else 0
    except RouteStop as exc:
        print(json.dumps({"status": "stopped", "code": exc.code,
                          "map_or_export_created": False}, sort_keys=True))
        return 12
    except BaseException:
        print(json.dumps({"status": "stopped",
                          "code": "partial_pair_stage_unexpected_failure",
                          "map_or_export_created": False}, sort_keys=True))
        return 20


if __name__ == "__main__":
    raise SystemExit(main())
