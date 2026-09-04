#!/usr/bin/env python3
"""Activate the exact approved one-attempt M1-SRC-004 recovery control."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent.resolve()
DATA_ROOT = PROJECT_ROOT / "nepal-2026-before-after-map-data"
BUNDLE_REF = "reviews/m2-sentinel-recovery/review-bundle.json"
BUNDLE_SHA256 = "dffa194cc91636a35b5f55af6ece32bb6eb90d77b65ea3d9865413f912d146e7"
PROPOSAL_REF = "contracts/milestone-002-sentinel-recovery-proposal.json"
PROPOSAL_SHA256 = "7b8b5e83265b37962f879ca7dad85ab5f5c04ceb28ee0f15fa774a79df7fd013"
REVIEW_CONTRACT_REF = "reviews/m2-sentinel-recovery/review-contract.json"
REVIEW_RECONCILIATION_REF = "records/source-gates/m2-sentinel-recovery-review-reconciliation.json"
ACTIVE_INTAKE_REF = "contracts/m2-intake.json"
FAILED_RECEIPT_REF = "records/acquisition/attempts/m1-src-004-20260904t043930z-ac125c11.json"
FAILED_RECEIPT_SHA256 = "8cbaf911e5a3329c5aa00a7288e237fa71987a2d4f03cea8c630c7dd28b9e7e9"
ACQUISITION_RECONCILIATION_REF = "records/acquisition/sentinel-acquisition-reconciliation-001.json"
ACQUISITION_RECONCILIATION_SHA256 = "37dea3830d7b08724f61b16634f04daf30e0f2d7633aa608c2b5655d0683fd87"
APPROVAL_REF = "records/source-gates/m2-sentinel-recovery-approval.json"
RECOVERY_CONTRACT_REF = "contracts/m2-sentinel-recovery.json"
ACTIVATION_REF = "records/acquisition/sentinel-recovery-activation.json"
CORE_REF = "scripts/m2_sentinel_recovery_core.py"
RUNNER_REF = "scripts/acquire_m2_sentinel_recovery.py"
VERIFIER_REF = "scripts/verify_m2_sentinel_recovery_container.py"
TEST_REF = "tests/test_m2_sentinel_recovery.py"
FAILED_PARTIAL_SHA256 = "299b2d07ccb58747cce43ae3b18e6d25c1c6d72a5653831b50a44ca72677ea66"
FAILED_PARTIAL_BYTES = 561_593_598


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(relative: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / relative).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {relative}")
    return value


def write_new(relative: str, payload: bytes) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def original_asset_and_partial(active_intake: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    assets = [
        asset for asset in active_intake.get("assets", [])
        if asset.get("extensions", {}).get("source_id") == "M1-SRC-004"
    ]
    if len(assets) != 1:
        raise ValueError("original M1-SRC-004 asset identity drift")
    asset = assets[0]
    attempts = asset.get("attempts", [])
    if (
        asset.get("state") != "failed"
        or asset.get("failure", {}).get("code") != "transferred_size_mismatch"
        or len(attempts) != 1
        or attempts[0].get("attempt_id") != "m1-src-004-20260904t043930z-ac125c11"
        or attempts[0].get("outcome") != "failed"
    ):
        raise ValueError("original M1-SRC-004 failed history drift")
    event_path = Path(attempts[0]["extensions"]["external_started_event"]).resolve(strict=True)
    event_path.relative_to(DATA_ROOT.resolve(strict=True))
    event = json.loads(event_path.read_text(encoding="utf-8"))
    partial = Path(event["staging_path"]).resolve(strict=True)
    partial.relative_to(DATA_ROOT.resolve(strict=True))
    if partial.stat().st_size != FAILED_PARTIAL_BYTES:
        raise ValueError("retained failed partial size drift")
    digest = hashlib.sha256()
    with partial.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != FAILED_PARTIAL_SHA256:
        raise ValueError("retained failed partial hash drift")
    return asset, partial


def build_outputs(activated_at_utc: str) -> dict[str, bytes]:
    for relative, expected in {
        BUNDLE_REF: BUNDLE_SHA256,
        PROPOSAL_REF: PROPOSAL_SHA256,
        FAILED_RECEIPT_REF: FAILED_RECEIPT_SHA256,
        ACQUISITION_RECONCILIATION_REF: ACQUISITION_RECONCILIATION_SHA256,
    }.items():
        if sha256_file(relative) != expected:
            raise ValueError(f"immutable input hash drift: {relative}")

    proposal = load(PROPOSAL_REF)
    reconciliation = load(REVIEW_RECONCILIATION_REF)
    if (
        reconciliation.get("status") != "reconciled_exact_human_response"
        or reconciliation.get("contract_sha256") != sha256_file(REVIEW_CONTRACT_REF)
        or reconciliation.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}
        or reconciliation.get("human_decisions_fabricated") is not False
    ):
        raise ValueError("review response is not one exact reconciled human approval")
    active_intake = load(ACTIVE_INTAKE_REF)
    original, partial = original_asset_and_partial(active_intake)
    destination = DATA_ROOT / "custody" / Path(*Path(original["destination_relative_path"]).parts)
    if destination.exists():
        raise ValueError("approved recovery destination already exists")
    recovery_root = DATA_ROOT / ".intake-staging" / "nepal-m2-sentinel-recovery-001"
    if recovery_root.exists():
        raise ValueError("approved recovery staging identity already exists")

    approval = {
        "schema_version": "1.0",
        "approval_id": "NEPAL-M2-SENTINEL-RECOVERY-APPROVAL-001",
        "status": "approved_exact_bounded_fresh_byte_zero_recovery",
        "approved_at_utc": activated_at_utc,
        "review_id": "m2-sentinel-recovery-review-001",
        "review_bundle_id": "m2-sentinel-recovery-review-bundle-001",
        "review_bundle_manifest_sha256": BUNDLE_SHA256,
        "recovery_proposal_ref": PROPOSAL_REF,
        "recovery_proposal_sha256": PROPOSAL_SHA256,
        "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
        "review_reconciliation_sha256": sha256_file(REVIEW_RECONCILIATION_REF),
        "locked_response_sha256": reconciliation["response_sha256"],
        "lock_receipt_sha256": reconciliation["receipt_sha256"],
        "human_decision_count": 1,
        "decision_counts": {"approve": 1, "revise": 0, "defer": 0},
        "recovery_identity": {
            "source_id": "M1-SRC-004",
            "recovery_asset_id": "m1-src-004-recovery-001",
            "mode": "fresh_full_restart_distinct_attempt",
            "restart_offset_bytes": 0,
            "retained_failed_attempt_id": "m1-src-004-20260904t043930z-ac125c11",
            "retained_partial_bytes": FAILED_PARTIAL_BYTES,
            "retained_partial_sha256": FAILED_PARTIAL_SHA256,
        },
        "authorized_next_actions": copy.deepcopy(proposal["approval_would_authorize"]),
        "does_not_authorize": copy.deepcopy(proposal["approval_would_not_authorize"]),
        "human_decisions_fabricated": False,
    }
    approval_bytes = canonical_bytes(approval)
    approval_sha256 = sha256_bytes(approval_bytes)

    recovery_asset = copy.deepcopy(original)
    recovery_asset["asset_id"] = "m1-src-004-recovery-001"
    recovery_asset["source"]["authorization_ref"] = APPROVAL_REF
    recovery_asset["staging_relative_path"] = (
        "m1-src-004-recovery-001/"
        "S1D_IW_GRDH_1SDV_20260828T122116_20260828T122141_004326_007FA4_C523.SAFE.zip.part"
    )
    recovery_asset["observed"] = {
        "staged_sha256": None,
        "staged_size_bytes": None,
        "promoted_sha256": None,
        "promoted_size_bytes": None,
    }
    recovery_asset["state"] = "authorized"
    recovery_asset["attempts"] = []
    recovery_asset["failure"] = None
    recovery_asset["superseded_by"] = None
    recovery_asset["extensions"].update({
        "recovery_of_asset_id": "m1-src-004",
        "retained_failed_attempt_id": "m1-src-004-20260904t043930z-ac125c11",
        "retained_failed_receipt_ref": FAILED_RECEIPT_REF,
        "retained_failed_receipt_sha256": FAILED_RECEIPT_SHA256,
        "retained_partial_external_path": str(partial),
        "retained_partial_size_bytes": FAILED_PARTIAL_BYTES,
        "retained_partial_sha256": FAILED_PARTIAL_SHA256,
    })
    contract = {
        "contract_version": "1.0",
        "intake_id": "nepal-m2-sentinel-recovery-001",
        "created_at": activated_at_utc,
        "collision_policy": "fail",
        "promotion_mode": "atomic-no-replace",
        "secret_policy": "references-only",
        "custody_root": "nepal-2026-before-after-map-data/custody",
        "staging_root": "nepal-2026-before-after-map-data/.intake-staging/nepal-m2-sentinel-recovery-001",
        "assets": [recovery_asset],
        "extensions": {
            "status": "active_authorized_one_fresh_attempt_publication_gate_pending",
            "recovery_approval_ref": APPROVAL_REF,
            "recovery_approval_sha256": approval_sha256,
            "review_bundle_ref": BUNDLE_REF,
            "review_bundle_sha256": BUNDLE_SHA256,
            "review_reconciliation_ref": REVIEW_RECONCILIATION_REF,
            "review_reconciliation_sha256": sha256_file(REVIEW_RECONCILIATION_REF),
            "recovery_proposal_ref": PROPOSAL_REF,
            "recovery_proposal_sha256": PROPOSAL_SHA256,
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256_at_activation": sha256_file(ACTIVE_INTAKE_REF),
            "acquisition_reconciliation_ref": ACQUISITION_RECONCILIATION_REF,
            "acquisition_reconciliation_sha256": ACQUISITION_RECONCILIATION_SHA256,
            "restart_offset_bytes": 0,
            "resume_partial": False,
            "delete_or_modify_failed_partial": False,
            "reuse_failed_staging_path": False,
            "maximum_real_transfer_attempts": 1,
        },
    }
    contract_bytes = canonical_bytes(contract)
    contract_sha256 = sha256_bytes(contract_bytes)

    activation = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-RECOVERY-ACTIVATION-001",
        "activated_at_utc": activated_at_utc,
        "status": "pass_exact_recovery_authorized_publication_gate_pending",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": approval_sha256,
            "recovery_contract_ref": RECOVERY_CONTRACT_REF,
            "recovery_contract_sha256": contract_sha256,
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256": sha256_file(ACTIVE_INTAKE_REF),
            "failed_receipt_ref": FAILED_RECEIPT_REF,
            "failed_receipt_sha256": FAILED_RECEIPT_SHA256,
            "recovery_core_ref": CORE_REF,
            "recovery_core_sha256": sha256_file(CORE_REF),
            "recovery_runner_ref": RUNNER_REF,
            "recovery_runner_sha256": sha256_file(RUNNER_REF),
            "container_verifier_ref": VERIFIER_REF,
            "container_verifier_sha256": sha256_file(VERIFIER_REF),
            "tests_ref": TEST_REF,
            "tests_sha256": sha256_file(TEST_REF),
        },
        "preflight": {
            "original_failed_attempt_preserved": True,
            "original_partial_path": str(partial),
            "original_partial_size_bytes": FAILED_PARTIAL_BYTES,
            "original_partial_sha256": FAILED_PARTIAL_SHA256,
            "destination_absent": True,
            "distinct_recovery_staging_root_absent": True,
            "credential_reference": "CDSE_ACCESS_TOKEN",
            "credential_presence_checked": False,
        },
        "assertions": {
            "network_requests_performed": False,
            "authentication_performed": False,
            "credential_values_read_or_recorded": False,
            "external_custody_mutated": False,
            "recovery_staging_created": False,
            "product_payload_requested": False,
            "product_payload_bytes_received": 0,
            "original_intake_mutated": False,
            "original_failed_attempt_reclassified": False,
            "automatic_second_recovery_authorized": False,
            "pixel_or_scientific_action_released": False,
        },
        "next_gate": "publish_exact_runner_and_tests_then_verify_successful_public_ci_before_one_real_recovery",
    }
    return {
        APPROVAL_REF: approval_bytes,
        RECOVERY_CONTRACT_REF: contract_bytes,
        ACTIVATION_REF: canonical_bytes(activation),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activated-at-utc", required=True)
    args = parser.parse_args()
    outputs = build_outputs(args.activated_at_utc)
    collisions = [relative for relative in outputs if (ROOT / relative).exists()]
    if collisions:
        raise SystemExit("refusing output collision: " + ", ".join(collisions))
    for relative, payload in outputs.items():
        write_new(relative, payload)
    print(json.dumps({"status": "activated_publication_gate_pending", "outputs": list(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
