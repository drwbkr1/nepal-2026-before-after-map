#!/usr/bin/env python3
"""One bounded metadata-only diagnostic for the preserved recovery-005 GTC inputs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import inspect
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-gtc-input-compatibility-diagnostic-001"
PROPOSAL_REF = "contracts/milestone-002-radar-gtc-input-compatibility-diagnostic-001-proposal.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
GATE_REF = f"records/readiness/{PREFIX}-implementation-publication-gate.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-final-preflight.json"
ATTEMPT_ID = "radar-gtc-input-compatibility-diagnostic-001-real-001"
PROPOSAL_SHA = "9506b91f3809b08340b44e8965311088ad7537ff5626ef78a9f5bdad9d841910"
BUNDLE_SHA = "16221f886565c9fb445b32d7c27f2fe666591b46ddc1fde0ecf72feb95500241"
RECOVERY_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\a1")
DIAGNOSTIC_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data\r5\d1")
CANDIDATES = (
    "s/1/gamma0_linear_slant.crf",
    "s/1/gamma0_linear_despeckled.crf",
    "s/1/scattering_area.crf",
    "s/1/geometric_distortion.crf",
    "s/1/geometric_distortion_mask_slant.crf",
    "dem/ellipsoidal_dem_mosaic.tif",
)


class DiagnosticError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DiagnosticError("json_root_invalid")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def verify_public_bindings() -> tuple[dict[str, Any], dict[str, Any]]:
    if sha256(ROOT / PROPOSAL_REF) != PROPOSAL_SHA or sha256(ROOT / BUNDLE_REF) != BUNDLE_SHA:
        raise DiagnosticError("review_identity_mismatch")
    approval = load_json(ROOT / APPROVAL_REF)
    if (
        approval.get("status") != "approved_single_bounded_diagnostic_envelope"
        or approval.get("attestation") is not True
        or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA
        or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA
        or approval.get("limits", {}).get("maximum_diagnostic_processes") != 1
        or approval.get("limits", {}).get("maximum_geoprocessing_calls") != 0
    ):
        raise DiagnosticError("approval_identity_or_scope_mismatch")
    proposal = load_json(ROOT / PROPOSAL_REF)
    envelope = proposal.get("proposed_single_authority_envelope", {})
    if (
        envelope.get("diagnostic_id") != ATTEMPT_ID
        or envelope.get("diagnostic_root") != str(DIAGNOSTIC_ROOT)
        or envelope.get("exact_preserved_root") != str(RECOVERY_ROOT)
        or envelope.get("exact_candidates") != list(CANDIDATES)
        or envelope.get("maximum_geoprocessing_calls") != 0
        or envelope.get("maximum_raster_function_calls") != 0
        or envelope.get("maximum_pixel_reads") != 0
        or envelope.get("automatic_retry") is not False
    ):
        raise DiagnosticError("proposal_boundary_mismatch")
    for item in proposal.get("protected_public_evidence", []):
        ref = item.get("path")
        expected = item.get("sha256")
        if not isinstance(ref, str) or not isinstance(expected, str) or sha256(ROOT / ref) != expected:
            raise DiagnosticError("protected_public_evidence_drift")
    return approval, proposal


def verify_gate() -> dict[str, Any]:
    gate = load_json(ROOT / GATE_REF)
    expected = {
        "approval_sha256": sha256(ROOT / APPROVAL_REF),
        "proposal_sha256": PROPOSAL_SHA,
        "review_bundle_sha256": BUNDLE_SHA,
        "runner_sha256": sha256(Path(__file__)),
        "portable_tests_sha256": sha256(ROOT / "tests/test_m2_radar_gtc_input_compatibility_diagnostic_001.py"),
        "arcgis_synthetic_validator_sha256": sha256(ROOT / "scripts/validate_m2_radar_gtc_input_compatibility_diagnostic_001_arcgis.py"),
    }
    if (
        gate.get("status") != "pass_public_default_branch_ci_implementation_ready"
        or gate.get("public_ci_conclusion") != "success"
        or gate.get("bindings") != expected
    ):
        raise DiagnosticError("implementation_publication_gate_invalid")
    return gate


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def run_preflight() -> dict[str, Any]:
    if (ROOT / PREFLIGHT_REF).exists():
        raise DiagnosticError("final_preflight_already_consumed")
    verify_public_bindings()
    gate = verify_gate()
    if git_head() != subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True).strip():
        raise DiagnosticError("public_default_branch_not_current")
    if subprocess.run(["git", "merge-base", "--is-ancestor", gate["implementation_commit_sha"], "HEAD"], cwd=ROOT).returncode != 0:
        raise DiagnosticError("implementation_commit_not_in_public_history")
    if DIAGNOSTIC_ROOT.exists():
        raise DiagnosticError("diagnostic_attempt_root_collision")
    if not RECOVERY_ROOT.is_dir() or RECOVERY_ROOT.is_symlink():
        raise DiagnosticError("preserved_attempt_root_missing_or_reparse")
    if len(set(CANDIDATES)) != 6 or any(".." in Path(ref).parts for ref in CANDIDATES):
        raise DiagnosticError("candidate_list_invalid")
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-FINAL-PREFLIGHT",
        "checked_at_utc": now_utc(),
        "status": "pass_no_content_single_attempt_ready",
        "bindings": {"approval_sha256": sha256(ROOT / APPROVAL_REF), "implementation_gate_sha256": sha256(ROOT / GATE_REF), "public_gate_state_commit_sha": git_head()},
        "checks": {"exact_preserved_root_exists": True, "diagnostic_root_absent": True, "protected_public_evidence_exact": True, "candidate_list_exact": True},
        "assertions": {"candidate_content_read": False, "arcpy_imported": False, "diagnostic_process_started": False, "geoprocessing_invoked": False, "pixel_data_read": False},
    }
    write_new_json(ROOT / PREFLIGHT_REF, receipt)
    return receipt


def metadata_value(obj: Any, field: str) -> Any:
    try:
        return getattr(obj, field)
    except (AttributeError, RuntimeError, ValueError):
        return None


def number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if abs(value) < 1e12 else None


def describe_metadata(arcpy: Any, path: Path) -> dict[str, Any]:
    desc = arcpy.Describe(str(path))
    spatial = metadata_value(desc, "spatialReference")
    extent = metadata_value(desc, "extent")
    xmin = number(metadata_value(extent, "XMin")) if extent is not None else None
    xmax = number(metadata_value(extent, "XMax")) if extent is not None else None
    ymin = number(metadata_value(extent, "YMin")) if extent is not None else None
    ymax = number(metadata_value(extent, "YMax")) if extent is not None else None
    output: dict[str, Any] = {}
    for key in ("dataType", "datasetType", "format", "pixelType"):
        value = metadata_value(desc, key)
        output[key] = value if isinstance(value, str) and len(value) <= 80 and "\\" not in value and "/" not in value else None
    for key in ("bandCount", "meanCellWidth", "meanCellHeight"):
        output[key] = number(metadata_value(desc, key))
    output["spatial_reference_factory_code"] = number(metadata_value(spatial, "factoryCode")) if spatial is not None else None
    output["extent_width"] = xmax - xmin if xmin is not None and xmax is not None else None
    output["extent_height"] = ymax - ymin if ymin is not None and ymax is not None else None
    multidimensional = metadata_value(desc, "isMultidimensional")
    output["is_multidimensional"] = multidimensional if isinstance(multidimensional, bool) else None
    return output


def inspect_candidates(arcpy: Any, paths: tuple[Path, ...], observations: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if observations is None:
        observations = []
    for index, path in enumerate(paths):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise DiagnosticError(f"candidate_{index}_unsafe_filesystem_type")
        filesystem = {"type": "directory" if stat.S_ISDIR(info.st_mode) else "file", "size_bytes": info.st_size if stat.S_ISREG(info.st_mode) else None}
        exists = bool(arcpy.Exists(str(path)))
        if not exists:
            raise DiagnosticError(f"candidate_{index}_not_recognized_by_arcgis")
        observations.append({"candidate_index": index, "candidate_ref": CANDIDATES[index], "filesystem": filesystem, "arcgis_exists": True, "describe": describe_metadata(arcpy, path)})
    by_ref = {item["candidate_ref"]: item["describe"] for item in observations}
    slant = by_ref[CANDIDATES[0]]
    despeckled = by_ref[CANDIDATES[1]]
    dem = by_ref[CANDIDATES[5]]
    comparisons = {
        "slant_vs_despeckled_band_count_equal": slant["bandCount"] == despeckled["bandCount"] if slant["bandCount"] is not None and despeckled["bandCount"] is not None else None,
        "slant_vs_despeckled_spatial_reference_equal": slant["spatial_reference_factory_code"] == despeckled["spatial_reference_factory_code"] if slant["spatial_reference_factory_code"] is not None and despeckled["spatial_reference_factory_code"] is not None else None,
        "dem_single_band_observed": dem["bandCount"] == 1 if dem["bandCount"] is not None else None,
        "support_band_counts": [by_ref[ref]["bandCount"] for ref in CANDIDATES[2:5]],
    }
    return observations, comparisons


def run_diagnostic(import_arcpy: Callable[[], Any] | None = None) -> dict[str, Any]:
    verify_public_bindings()
    verify_gate()
    preflight = load_json(ROOT / PREFLIGHT_REF)
    if preflight.get("status") != "pass_no_content_single_attempt_ready":
        raise DiagnosticError("final_preflight_invalid")
    if DIAGNOSTIC_ROOT.exists():
        raise DiagnosticError("diagnostic_attempt_root_collision")
    DIAGNOSTIC_ROOT.mkdir(parents=False, exist_ok=False)
    reserve = {"schema_version": "1.0", "attempt_id": ATTEMPT_ID, "reserved_at_utc": now_utc(), "status": "reserved_before_content_access"}
    write_new_json(DIAGNOSTIC_ROOT / "terminal-reservation.json", reserve)
    write_new_json(DIAGNOSTIC_ROOT / "cleanup-reservation.json", reserve)
    write_new_json(DIAGNOSTIC_ROOT / "started.json", {**reserve, "status": "started_one_process_no_retry", "preflight_sha256": sha256(ROOT / PREFLIGHT_REF)})

    status = "block_unknown_failure"
    failure_code: str | None = None
    observations: list[dict[str, Any]] = []
    comparisons: dict[str, Any] = {}
    runtime: dict[str, Any] = {}
    try:
        paths = tuple(RECOVERY_ROOT / ref for ref in CANDIDATES)
        for path in paths:
            if not path.exists():
                raise DiagnosticError(f"exact_candidate_{paths.index(path)}_missing")
            if path.is_symlink():
                raise DiagnosticError(f"exact_candidate_{paths.index(path)}_reparse")
        arcpy = import_arcpy() if import_arcpy is not None else importlib.import_module("arcpy")
        runtime = {
            "product_info": str(arcpy.ProductInfo())[:80],
            "image_analyst_extension": str(arcpy.CheckExtension("ImageAnalyst"))[:80],
            "spatial_extension": str(arcpy.CheckExtension("Spatial"))[:80],
            "gtc_parameters": tuple(inspect.signature(arcpy.ia.ApplyGeometricTerrainCorrection).parameters),
        }
        observations, comparisons = inspect_candidates(arcpy, paths, observations)
        status = "pass_current_structural_metadata_observed_only"
    except DiagnosticError as exc:
        status = "block_exact_candidate_or_catalog"
        failure_code = exc.code
    except BaseException as exc:
        status = "block_unexpected_runtime_failure"
        failure_code = type(exc).__name__
    finally:
        terminal = {
            "schema_version": "1.0", "receipt_id": "NEPAL-M2-RADAR-GTC-INPUT-COMPATIBILITY-DIAGNOSTIC-001-TERMINAL",
            "attempt_id": ATTEMPT_ID, "recorded_at_utc": now_utc(), "status": status,
            "failure_code": failure_code, "runtime": runtime, "candidate_observations": observations,
            "structural_comparisons": comparisons,
            "assertions": {"one_process_consumed": True, "geoprocessing_called": False, "raster_function_called": False, "pixel_data_read": False, "network_or_credentials_used": False, "preserved_inputs_mutated": False, "historical_root_cause_established": False, "radar_recovery_readiness_established": False, "scientific_result_established": False},
        }
        try:
            write_new_json(DIAGNOSTIC_ROOT / "terminal.json", terminal)
        finally:
            write_new_json(DIAGNOSTIC_ROOT / "cleanup.json", {"schema_version": "1.0", "attempt_id": ATTEMPT_ID, "recorded_at_utc": now_utc(), "status": "metadata_process_exited_no_payload_cleanup_required"})
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "execute"))
    args = parser.parse_args()
    if args.command == "preflight":
        result = run_preflight()
        print(json.dumps({"status": result["status"], "receipt": PREFLIGHT_REF}))
        return 0
    result = run_diagnostic()
    print(json.dumps({"status": result["status"], "attempt_id": ATTEMPT_ID, "failure_code": result["failure_code"]}))
    return 0 if result["status"].startswith("pass_") else 12


if __name__ == "__main__":
    raise SystemExit(main())
