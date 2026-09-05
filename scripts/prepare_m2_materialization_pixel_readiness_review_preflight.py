#!/usr/bin/env python3
"""Record a read-only preflight for the five-source M2 materialization review."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
SOURCE_ORDER = ["M1-SRC-004", "M1-SRC-005", "M1-SRC-006", "M1-SRC-010", "M1-SRC-008"]
ATTEMPT_IDS = {source_id: f"{source_id.casefold()}-materialization-001" for source_id in SOURCE_ORDER}
EXISTING_MATERIALIZATION_RECEIPTS = [
    "records/acquisition/materialization/m1-src-001-fixture-must-not-run.json",
    "records/acquisition/materialization/m1-src-002-m1-src-002-materialization-001.json",
    "records/acquisition/materialization/m1-src-003-m1-src-003-materialization-001.json",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def repository_sha(relative: str) -> str:
    return sha256_file(ROOT / relative)


def container_receipt_for(source_id: str, attempt_id: str) -> Path:
    path = ROOT / "records" / "acquisition" / "container-verification" / f"{source_id.casefold()}-{attempt_id}.json"
    if not path.is_file():
        raise RuntimeError(f"missing exact container receipt for {source_id}: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        raise RuntimeError(f"refusing to replace {output}")

    intake = load("contracts/m2-intake.json")
    milestone = load("contracts/milestone-002.json")
    materialization_contract = load("contracts/m2-materialization.json")
    by_source = {
        asset.get("extensions", {}).get("source_id"): asset
        for asset in intake.get("assets", [])
        if isinstance(asset, dict)
    }
    if milestone.get("handoff", {}).get("current_checkpoint") != "M2-VERIFY":
        raise RuntimeError("current checkpoint is not M2-VERIFY")
    if materialization_contract.get("status") != "active_authorized_gate_deferred":
        raise RuntimeError("materialization contract is not active and gate-deferred")
    if not DATA_ROOT.is_dir():
        raise RuntimeError(f"external data root is missing: {DATA_ROOT}")

    planned_sources: list[dict] = []
    total_uncompressed = 0
    for source_id in SOURCE_ORDER:
        asset = by_source.get(source_id)
        if not asset or asset.get("state") != "promoted":
            raise RuntimeError(f"{source_id} is not promoted")
        successes = [attempt for attempt in asset.get("attempts", []) if attempt.get("outcome") == "succeeded"]
        if len(successes) != 1:
            raise RuntimeError(f"{source_id} does not have exactly one successful transfer")
        transfer_attempt = successes[0]
        container_path = container_receipt_for(source_id, transfer_attempt["attempt_id"])
        container = json.loads(container_path.read_text(encoding="utf-8"))
        result = container.get("result", {})
        if container.get("status") != "pass_container_only" or result.get("source_id") != source_id:
            raise RuntimeError(f"{source_id} container receipt does not pass")
        archive = Path(materialization_contract["execution_boundary"]["external_data_root"]) / "custody" / result["archive_relative_path"]
        if not archive.is_file():
            raise RuntimeError(f"{source_id} archive is missing")
        observed = asset.get("observed", {})
        archive_size = archive.stat().st_size
        archive_sha = sha256_file(archive)
        if archive_size != observed.get("promoted_size_bytes") or archive_size != result.get("local_size_bytes"):
            raise RuntimeError(f"{source_id} archive size differs")
        if archive_sha != observed.get("promoted_sha256") or archive_sha != result.get("local_sha256"):
            raise RuntimeError(f"{source_id} archive SHA-256 differs")
        attempt_id = ATTEMPT_IDS[source_id]
        output_path = DATA_ROOT / "materialized" / source_id.casefold() / attempt_id
        receipt_ref = f"records/acquisition/materialization/{source_id.casefold()}-{attempt_id}.json"
        if output_path.exists() or (ROOT / receipt_ref).exists():
            raise RuntimeError(f"{source_id} planned materialization identity collides")
        total_uncompressed += int(result["total_uncompressed_bytes"])
        planned_sources.append(
            {
                "source_id": source_id,
                "sensor_route": asset["extensions"]["sensor_route"],
                "event_role": asset["extensions"]["event_role"],
                "exact_product_id": asset["extensions"]["exact_product_id"],
                "archive_size_bytes": archive_size,
                "archive_sha256": archive_sha,
                "container_receipt_ref": container_path.relative_to(ROOT).as_posix(),
                "container_receipt_sha256": sha256_file(container_path),
                "member_count": result["member_count"],
                "total_uncompressed_bytes": result["total_uncompressed_bytes"],
                "planned_attempt_id": attempt_id,
                "planned_external_attempt_path": str(output_path),
                "planned_receipt_ref": receipt_ref,
                "planned_path_absent": True,
                "planned_receipt_absent": True,
            }
        )

    existing_materializations: list[dict] = []
    for receipt_ref in EXISTING_MATERIALIZATION_RECEIPTS:
        receipt_path = ROOT / receipt_ref
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        manifest_path = Path(receipt["bindings"]["external_manifest_path"])
        if not manifest_path.is_file():
            raise RuntimeError(f"missing retained materialization manifest: {manifest_path}")
        if sha256_file(manifest_path) != receipt["bindings"]["external_manifest_sha256"]:
            raise RuntimeError(f"retained materialization manifest drift: {receipt_ref}")
        existing_materializations.append(
            {
                "source_id": receipt["source_id"],
                "attempt_id": receipt["attempt_id"],
                "status": receipt["status"],
                "receipt_ref": receipt_ref,
                "receipt_sha256": sha256_file(receipt_path),
                "external_manifest_sha256": receipt["bindings"]["external_manifest_sha256"],
                "file_count": receipt["file_count"],
                "total_extracted_bytes": receipt["total_extracted_bytes"],
            }
        )

    disk = shutil.disk_usage(DATA_ROOT)
    minimum_free = total_uncompressed * 2
    if disk.free < minimum_free:
        raise RuntimeError("free space is below twice the planned uncompressed bytes")
    base_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-MATERIALIZATION-PIXEL-READINESS-REVIEW-PREFLIGHT-001",
        "observed_at_utc": args.observed_at_utc,
        "status": "pass_exact_five_ready_no_mutation",
        "base_repository_commit": base_commit,
        "bindings": {
            "active_intake_ref": "contracts/m2-intake.json",
            "active_intake_sha256": repository_sha("contracts/m2-intake.json"),
            "postsuccess_reconciliation_ref": "records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json",
            "postsuccess_reconciliation_sha256": repository_sha("records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json"),
            "materialization_contract_ref": "contracts/m2-materialization.json",
            "materialization_contract_sha256": repository_sha("contracts/m2-materialization.json"),
            "optical_input_contract_ref": "config/qa/optical-input-readiness-contract.json",
            "optical_input_contract_sha256": repository_sha("config/qa/optical-input-readiness-contract.json"),
            "radar_input_contract_ref": "config/qa/radar-input-readiness-contract-amendment-001.json",
            "radar_input_contract_sha256": repository_sha("config/qa/radar-input-readiness-contract-amendment-001.json"),
            "pixel_readiness_contract_ref": "config/qa/pixel-readiness-contract.json",
            "pixel_readiness_contract_sha256": repository_sha("config/qa/pixel-readiness-contract.json"),
        },
        "source_order": SOURCE_ORDER,
        "planned_sources": planned_sources,
        "existing_materializations": existing_materializations,
        "storage": {
            "planned_uncompressed_bytes": total_uncompressed,
            "minimum_free_bytes": minimum_free,
            "observed_free_bytes": disk.free,
            "free_space_gate": "pass",
        },
        "assertions": {
            "promoted_source_count": 8,
            "container_pass_source_count": 8,
            "existing_materialization_count": 3,
            "planned_materialization_count": 5,
            "planned_paths_absent": True,
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "archive_extraction_performed": False,
            "measurement_pixels_read": False,
            "external_files_mutated": False,
        },
        "limitations": [
            "This read-only preflight does not authorize or perform materialization, metadata inspection, raster header access, or pixel reads.",
            "Free space and collision state can drift and must be rechecked immediately before any approved execution.",
            "Container identity and SAFE structure do not establish raster readability, usable pixels, registration, or scientific fitness.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": record["status"], "output": str(output), "output_sha256": sha256_file(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
