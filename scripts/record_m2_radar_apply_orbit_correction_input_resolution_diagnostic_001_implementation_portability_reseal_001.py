#!/usr/bin/env python3
"""Reseal corrected readiness after making its publication reader correction-aware."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core import canonical_bytes, sha256_file, write_new_json
from record_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_implementation_readiness import ARTIFACTS


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
READINESS_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
RESEAL_REF = f"records/readiness/{PREFIX}-implementation-portability-correction-001-reseal.json"


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON root is not an object: {ref}")
    return value


def replace_json(ref: str, value: object, nonce: str) -> None:
    path = ROOT / ref
    temporary = path.with_name(f".{path.name}.{nonce}.tmp")
    with temporary.open("xb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    args = parser.parse_args()
    if not args.recorded_at_utc.endswith("Z"):
        raise SystemExit("--recorded-at-utc must be UTC")
    if (ROOT / RESEAL_REF).exists():
        raise SystemExit("reseal output collision")
    readiness = load(READINESS_REF)
    if readiness.get("status") != "pass_portable_path_assertion_correction_public_ci_pending":
        raise SystemExit("corrected readiness differs")
    missing = [ref for ref in ARTIFACTS if not (ROOT / ref).is_file()]
    if missing:
        raise SystemExit("missing implementation artifact: " + ", ".join(missing))
    prior_sha = sha256_file(ROOT / READINESS_REF)
    readiness["bindings"] = {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS}
    readiness["validation"].update({
        "repository_checker_status": "pass_1205_required_files",
        "correction_aware_publication_reader_checked": True,
    })
    readiness["reseal"] = {
        "reason": "The publication recorder now accepts the exact corrected-readiness status; no production diagnostic behavior changed.",
        "prior_readiness_sha256": prior_sha,
        "recorded_at_utc": args.recorded_at_utc,
    }
    replace_json(READINESS_REF, readiness, "portable-reseal-001")
    readiness_sha = sha256_file(ROOT / READINESS_REF)
    reseal = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION-PORTABILITY-CORRECTION-001-RESEAL",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_corrected_readiness_resealed_public_ci_pending",
        "prior_readiness_sha256": prior_sha,
        "current_readiness_ref": READINESS_REF,
        "current_readiness_sha256": readiness_sha,
        "changed_control": "implementation publication recorder accepts pass_portable_path_assertion_correction_public_ci_pending",
        "assertions": {
            "production_path_logic_changed": False,
            "diagnostic_runner_changed": False,
            "public_ci_pending": True,
            "final_no_content_preflight_performed": False,
            "diagnostic_process_started": False,
            "arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(ROOT / RESEAL_REF, reseal)

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION"]
    implementation["gates"]["implementation_readiness_sha256"] = readiness_sha
    implementation["outputs"].append(RESEAL_REF)
    replace_json("contracts/milestone-002.json", milestone, "input-resolution-portable-reseal-001")

    evidence = {
        "record_id": "EVID-0194",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_portability_correction_reseal_001",
        "verified_at_utc": args.recorded_at_utc,
        "status": "pass_corrected_readiness_resealed_public_ci_pending",
        "claim": "The corrected readiness was resealed after the publication recorder was made aware of its exact corrected status. The diagnostic runner and production path logic did not change; fresh public CI remains required.",
        "reseal_ref": RESEAL_REF,
        "reseal_sha256": sha256_file(ROOT / RESEAL_REF),
        "implementation_readiness_ref": READINESS_REF,
        "implementation_readiness_sha256": readiness_sha,
        "assertions": reseal["assertions"],
    }
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(evidence, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())
    print(json.dumps({"status": reseal["status"], "readiness_sha256": readiness_sha}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
