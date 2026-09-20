#!/usr/bin/env python3
"""Preserve failed public CI and seal the one portable path-assertion correction."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_core import canonical_bytes, sha256_file, write_new_json
from record_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_implementation_readiness import ARTIFACTS


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-apply-orbit-correction-input-resolution-diagnostic-001"
READINESS_REF = f"records/readiness/{PREFIX}-implementation-readiness.json"
SUPERSEDED_REF = f"records/readiness/{PREFIX}-implementation-readiness-attempt-001-superseded.json"
FAILURE_REF = f"records/readiness/{PREFIX}-implementation-publication-attempt-001-failure.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
FAILED_COMMIT = "1c8a1f9f95debd47c6b58b0ae3dde8cb300a9daf"
FAILED_RUN_ID = 35477364361
FAILED_RUN_URL = "https://github.com/drwbkr1/nepal-2026-before-after-map/actions/runs/35477364361"


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


def append_evidence(value: dict[str, Any]) -> None:
    with (ROOT / "records/evidence-ledger.jsonl").open("ab", buffering=0) as stream:
        stream.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recorded-at-utc", required=True)
    args = parser.parse_args()
    if not args.recorded_at_utc.endswith("Z"):
        raise SystemExit("--recorded-at-utc must be UTC")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != FAILED_COMMIT:
        raise SystemExit("HEAD does not match the terminal failed implementation commit")
    for ref in (SUPERSEDED_REF, FAILURE_REF):
        if (ROOT / ref).exists():
            raise SystemExit(f"correction output collision: {ref}")
    prior = load(READINESS_REF)
    if prior.get("status") != "pass_read_only_diagnostic_implementation_public_ci_pending":
        raise SystemExit("attempt-001 readiness differs")
    missing = [ref for ref in ARTIFACTS if not (ROOT / ref).is_file()]
    if missing:
        raise SystemExit("missing corrected implementation artifact: " + ", ".join(missing))

    write_new_json(ROOT / SUPERSEDED_REF, prior)
    if sha256_file(ROOT / SUPERSEDED_REF) != sha256_file(ROOT / READINESS_REF):
        raise SystemExit("superseded readiness byte identity differs")
    failure = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION-PUBLICATION-ATTEMPT-001-FAILURE",
        "observed_at_utc": args.recorded_at_utc,
        "status": "terminal_public_ci_failure_no_release",
        "implementation_commit_sha": FAILED_COMMIT,
        "public_ci_run_id": FAILED_RUN_ID,
        "public_ci_url": FAILED_RUN_URL,
        "public_ci_conclusion": "failure",
        "repository_checker_status": "pass_1200_required_files",
        "public_test_result": {"tests_run": 645, "intentional_skips": 13, "errors": 0, "failures": 1},
        "failure": {
            "test": "test_m2_radar_apply_orbit_correction_input_resolution_diagnostic_001.InputResolutionDiagnostic001Tests.test_candidate_paths_are_exact_and_contained",
            "type": "AssertionError",
            "stage": "portable_public_test",
            "cause": "The test constructed its expected Windows child path with the host-native pathlib separator, producing forward slashes on the Ubuntu public runner while production path construction remained exact Windows lexical handling.",
        },
        "superseded_readiness_ref": SUPERSEDED_REF,
        "superseded_readiness_sha256": sha256_file(ROOT / SUPERSEDED_REF),
        "correction": "Keep production Windows path construction unchanged and compare the synthetic expected paths through the same explicit Windows lexical containment helper.",
        "assertions": {
            "public_gate_passed": False,
            "final_no_content_preflight_performed": False,
            "diagnostic_process_started": False,
            "arcpy_imported": False,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "new_radar_attempt_created": False,
            "historical_root_cause_established": False,
            "radar_recovery_readiness_established": False,
            "scientific_result_established": False,
        },
    }
    write_new_json(ROOT / FAILURE_REF, failure)

    corrected = json.loads(json.dumps(prior))
    corrected.update({
        "record_id": "NEPAL-M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION-READINESS-CORRECTED-001",
        "recorded_at_utc": args.recorded_at_utc,
        "status": "pass_portable_path_assertion_correction_public_ci_pending",
        "bindings": {ref: sha256_file(ROOT / ref) for ref in ARTIFACTS},
        "supersedes": {"ref": SUPERSEDED_REF, "sha256": sha256_file(ROOT / SUPERSEDED_REF)},
        "failed_publication": {"ref": FAILURE_REF, "sha256": sha256_file(ROOT / FAILURE_REF)},
        "next_action": "Publish the exact portable synthetic-test correction and require a fresh successful public default-branch CI run before gate-state publication, final preflight, ArcPy import, or external input access.",
    })
    corrected["validation"].update({
        "repository_checker_status": "pass_1203_required_files",
        "portable_windows_path_assertion_checked": True,
        "failed_public_ci_attempts_preserved": 1,
    })
    corrected["released_now"].update({"public_ci": True, "gate_state_publication": False, "final_no_content_preflight": False, "diagnostic_process": False})
    replace_json(READINESS_REF, corrected, "portable-correction-001")

    milestone = load("contracts/milestone-002.json")
    units = {item.get("id"): item for item in milestone.get("units", []) if isinstance(item, dict)}
    implementation = units["M2-RADAR-APPLY-ORBIT-CORRECTION-INPUT-RESOLUTION-DIAGNOSTIC-001-IMPLEMENTATION"]
    implementation["gates"].update({
        "public_ci": "pending",
        "failed_public_ci_attempts": 1,
        "failed_public_ci_run_id": FAILED_RUN_ID,
        "implementation_readiness_sha256": sha256_file(ROOT / READINESS_REF),
    })
    implementation["outputs"].extend([SUPERSEDED_REF, FAILURE_REF])
    implementation["exit_condition_delta"] = {
        "expected": ["successful public default-branch CI"],
        "observed": ["attempt-001 public CI failed only on one host-separator-dependent synthetic assertion; the failed run is preserved and the production path logic is unchanged"],
        "decision_value": "pending_corrected_public_ci",
        "rationale": "No final preflight, ArcPy import, or external input access is released by the failed run or correction.",
    }
    replace_json("contracts/milestone-002.json", milestone, "input-resolution-portable-correction-001")

    append_evidence({
        "record_id": "EVID-0192",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_implementation_publication_failure_001",
        "verified_at_utc": args.recorded_at_utc,
        "status": "terminal_public_ci_failure_no_release",
        "claim": "Implementation public CI attempt 001 failed only on one Ubuntu separator-dependent synthetic path assertion. The repository checker passed; no gate, preflight, ArcPy import, external input access, or diagnostic process was released.",
        "failure_ref": FAILURE_REF,
        "failure_sha256": sha256_file(ROOT / FAILURE_REF),
        "assertions": failure["assertions"],
    })
    append_evidence({
        "record_id": "EVID-0193",
        "type": "m2_radar_apply_orbit_correction_input_resolution_diagnostic_001_portability_correction_001",
        "verified_at_utc": args.recorded_at_utc,
        "status": "pass_portable_path_assertion_correction_public_ci_pending",
        "claim": "The bounded correction changes only the synthetic expected-path assertion to use explicit Windows lexical containment. Production diagnostic logic and every zero-action boundary remain unchanged; fresh public CI is required.",
        "implementation_readiness_ref": READINESS_REF,
        "implementation_readiness_sha256": sha256_file(ROOT / READINESS_REF),
        "assertions": {
            "production_path_logic_changed": False,
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
    })
    print(json.dumps({"status": corrected["status"], "failure_ref": FAILURE_REF, "readiness_ref": READINESS_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
