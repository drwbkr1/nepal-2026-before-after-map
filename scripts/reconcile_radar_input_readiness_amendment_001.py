#!/usr/bin/env python3
"""Reconcile the single amended real-002 result and reverify external custody."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
CONTRACT_REF = "config/qa/radar-input-readiness-contract-amendment-001.json"
CONTRACT_SHA256 = "d02a4344c755ac7b69e2b1bd2b66403fa2a68d204116a32220a03a6e4166e6bd"
REAL_REF = "records/readiness/radar-input/m2-s1-input-readiness-real-002.json"
APPROVAL_REF = "records/source-gates/m2-radar-input-readiness-amendment-approval.json"
OUTPUT_REF = "records/surface-receipts/radar-input-readiness-amendment-real-002-reconciliation.json"
PUBLISHED_COMMIT = "c05e1e26c8ee8dd8755573524da90c2080de4bd7"
PUBLISHED_CI_RUN = 33910395201
PUBLISHED_CI_URL = "https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/33910395201"
ORIGINAL_HASHES = {
    "config/qa/radar-input-readiness-contract.json": "ad478b8abd4e4a47c8d16012fffc2b67770681538bddc23b500ce5b32b17428a",
    "records/readiness/radar-input/m2-s1-input-readiness-real-001.json": "feab3645709df16306c81dae959a8693925a7c6f919f2a1e414cf3765c3a5b0c",
    "records/surface-receipts/radar-input-readiness-real-reconciliation.json": "5e4f703b938f9adaf10a6f37ec5195d1e1fc426197ffa1fa6a712ba0cb4de0a6",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest(relative: str) -> str:
    return sha256_file(ROOT.joinpath(*PurePosixPath(relative).parts))


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def require_external(path_value: str) -> Path:
    path = Path(path_value).resolve(strict=True)
    path.relative_to(DATA_ROOT.resolve(strict=True))
    return path


def inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: str(item).casefold())
    ]


def reverify_external(contract: dict[str, Any]) -> dict[str, Any]:
    attempt_file_count = 0
    safe_file_count = 0
    safe_total_bytes = 0
    added_sidecar_count = 0
    per_source: dict[str, Any] = {}
    for source in contract["sources"]:
        receipt_ref = source["materialization_receipt_ref"]
        receipt = load(ROOT.joinpath(*PurePosixPath(receipt_ref).parts))
        manifest_path = require_external(receipt["bindings"]["external_manifest_path"])
        safe_root = require_external(receipt["external_safe_root"])
        manifest = load(manifest_path)
        expected = {
            item["relative_path"]: {"size_bytes": item["size_bytes"], "sha256": item["sha256"]}
            for item in manifest["files"]
        }
        actual = inventory(safe_root)
        actual_by_path = {
            item["relative_path"]: {"size_bytes": item["size_bytes"], "sha256": item["sha256"]}
            for item in actual
        }
        if actual_by_path != expected:
            raise ValueError(f"SAFE inventory or bytes changed for {source['source_id']}")
        attempt_root = safe_root.parent
        attempt_inventory = inventory(attempt_root)
        extras = sorted(set(actual_by_path) - set(expected))
        attempt_file_count += len(attempt_inventory)
        safe_file_count += len(actual)
        safe_total_bytes += sum(item["size_bytes"] for item in actual)
        added_sidecar_count += len(extras)
        per_source[source["source_id"]] = {
            "attempt_file_count": len(attempt_inventory),
            "safe_file_count": len(actual),
            "safe_total_bytes": sum(item["size_bytes"] for item in actual),
            "external_manifest_sha256": sha256_file(manifest_path),
            "manifest_match": True,
            "added_sidecar_count": len(extras),
        }
    return {
        "status": "pass_exact_attempt_inventories_and_all_safe_hashes_unchanged",
        "attempt_count": len(contract["sources"]),
        "attempt_file_count": attempt_file_count,
        "safe_file_count": safe_file_count,
        "safe_total_bytes": safe_total_bytes,
        "added_sidecar_count": added_sidecar_count,
        "per_source": per_source,
    }


def validate_real(receipt: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    if receipt.get("receipt_id") != "NEPAL-S1-MATERIALIZED-INPUT-READINESS-REAL-002":
        raise ValueError("real-002 identity differs")
    if receipt.get("status") != "pass_partial_pre_event_header_readiness_only":
        raise ValueError("real-002 is not the bounded passing result")
    if receipt.get("bindings", {}).get("contract_sha256") != CONTRACT_SHA256:
        raise ValueError("real-002 contract binding differs")
    if receipt.get("runtime") != {"product": "ArcGISPro", "version": "3.7.1", "license_level": "Advanced"}:
        raise ValueError("real-002 ArcGIS runtime differs")
    activity = receipt.get("activity", {})
    if (
        activity.get("external_materialization_inventory_unchanged") is not True
        or activity.get("selected_materialized_files_rehashed") is not True
        or activity.get("all_real_annotation_metadata_parsed") is not True
        or activity.get("all_real_measurement_raster_headers_opened_with_arcgis") is not True
        or any(activity.get(key) is not False for key in (
            "network_requests_performed", "authentication_performed", "credential_values_read_or_recorded",
            "real_product_pixel_values_examined", "derived_raster_written",
        ))
    ):
        raise ValueError("real-002 activity boundary differs")
    products = receipt.get("products", {})
    if set(products) != {item["source_id"] for item in contract["sources"]}:
        raise ValueError("real-002 source set differs")
    per_source: dict[str, Any] = {}
    for source_id, product in products.items():
        annotations = product.get("annotations", {})
        headers = product.get("raster_headers", {})
        if (
            product.get("inventory", {}).get("status") != "pass_inventory_only"
            or product.get("decision", {}).get("status") != "pass_header_readability_only"
            or product.get("decision", {}).get("errors") != []
            or set(annotations) != {"vv", "vh"}
            or set(headers) != {"vv", "vh"}
        ):
            raise ValueError(f"real-002 source decision differs: {source_id}")
        for polarization in ("vv", "vh"):
            annotation = annotations[polarization]
            header = headers[polarization]
            if (
                annotation.get("pixel_value") != "Detected"
                or annotation.get("errors") != []
                or annotation.get("orbit_times_strictly_increasing") is not True
                or annotation.get("orbit_vectors_finite") is not True
                or header.get("format") != "TIFF"
                or header.get("band_count") != 1
                or header.get("pixel_type") != "U16"
                or header.get("width") != annotation.get("number_of_samples")
                or header.get("height") != annotation.get("number_of_lines")
            ):
                raise ValueError(f"real-002 annotation or header differs: {source_id} {polarization}")
        per_source[source_id] = {
            "inventory_status": product["inventory"]["status"],
            "annotation_pixel_values": {key: value["pixel_value"] for key, value in annotations.items()},
            "annotation_orbit_vector_counts": {key: value["orbit_vector_count_observed"] for key, value in annotations.items()},
            "raster_dimensions": {key: [value["width"], value["height"]] for key, value in headers.items()},
            "raster_pixel_types": {key: value["pixel_type"] for key, value in headers.items()},
            "decision_status": product["decision"]["status"],
        }
    return per_source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    output_path = ROOT / OUTPUT_REF
    if output_path.exists():
        raise SystemExit("refusing reconciliation output collision")
    if digest(CONTRACT_REF) != CONTRACT_SHA256:
        raise SystemExit("amended contract hash drift")
    for relative, expected in ORIGINAL_HASHES.items():
        if digest(relative) != expected:
            raise SystemExit(f"original evidence hash drift: {relative}")
    contract = load(ROOT / CONTRACT_REF)
    receipt = load(ROOT / REAL_REF)
    per_source = validate_real(receipt, contract)
    external = reverify_external(contract)
    if (
        external["attempt_count"] != 3
        or external["attempt_file_count"] != 87
        or external["safe_file_count"] != 78
        or external["safe_total_bytes"] != 5_183_550_209
        or external["added_sidecar_count"] != 0
    ):
        raise SystemExit("external custody aggregate differs")
    output = {
        "record_version": "1.0",
        "record_id": "NEPAL-S1-MATERIALIZED-INPUT-READINESS-AMENDMENT-REAL-002-RECONCILIATION-001",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_partial_pre_event_header_readiness_only_post_observation_no_downstream_release",
        "bindings": {
            "amended_contract_ref": CONTRACT_REF,
            "amended_contract_sha256": CONTRACT_SHA256,
            "real_receipt_ref": REAL_REF,
            "real_receipt_sha256": digest(REAL_REF),
            "approval_ref": APPROVAL_REF,
            "approval_sha256": digest(APPROVAL_REF),
            "original_real_001_receipt_sha256": ORIGINAL_HASHES["records/readiness/radar-input/m2-s1-input-readiness-real-001.json"],
        },
        "publication_gate": {
            "commit_sha": PUBLISHED_COMMIT,
            "remote_ref": "refs/heads/main",
            "remote_commit_verified": True,
            "github_actions_run_id": PUBLISHED_CI_RUN,
            "github_actions_workflow": "Validate project controls",
            "github_actions_conclusion": "success",
            "github_actions_url": PUBLISHED_CI_URL,
        },
        "observed_result": {
            "source_count": 3,
            "required_member_inventory_pass_count": 3,
            "annotation_parse_count": 6,
            "annotation_pixel_value_observed_set": ["Detected"],
            "measurement_header_open_count": 6,
            "all_measurement_headers_opened": True,
            "all_measurement_headers_one_band_u16": True,
            "all_header_dimensions_match_annotations": True,
            "all_embedded_orbit_structures_passed": True,
            "source_pass_count": 3,
            "source_block_count": 0,
            "blocking_errors": [],
            "per_source": per_source,
        },
        "external_custody_reverification": {**external, "verified_at_utc": args.reconciled_at_utc},
        "disposition": {
            "amended_gate_result": "pass_partial_pre_event_header_readiness_only",
            "post_observation_correction": True,
            "blind_or_independent_validation": False,
            "real_001_remains_block": True,
            "real_002_maximum_invocations_consumed": 1,
            "automatic_retry_authorized": False,
            "baseline_processing_released": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_materialization_inventory_unchanged": True,
            "real_product_pixel_values_examined": False,
            "derived_raster_written": False,
            "pixel_usability_established": False,
            "complete_pair_established": False,
            "baseline_processing_released": False,
            "change_established": False,
            "scientific_admission_authorized": False,
            "sentinel_recovery_authority_created": False,
            "orbit_recovery_authority_created": False,
        },
        "limitations": [
            "The Detected correction followed observation of that label in real-001; real-002 is confirmatory and is not blind or independent.",
            "The pass covers selected-member identity, annotation structure, embedded vectors, and ArcGIS header readability for only three pre-event sources.",
            "No measurement pixels were decoded, and no usable-pixel, AOI-coverage, updated-orbit, terrain-correction, registration, baseline, change, or scientific result is established.",
            "No before-after radar pair is complete because M1-SRC-004 through M1-SRC-006 are not in promoted verified custody.",
        ],
        "next_action": "Return to the independent Sentinel recovery, orbit recovery, DEM vertical-datum, terrain-result, and later pixel-readiness gates; do not run real-002 again.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(output, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": output["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
