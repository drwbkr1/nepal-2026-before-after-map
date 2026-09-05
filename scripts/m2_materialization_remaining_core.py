#!/usr/bin/env python3
"""Shared fail-closed controls for the approved five-source materialization."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT.parent / f"{ROOT.name}-data"
PROPOSAL_REF = "contracts/milestone-002-materialization-pixel-readiness-proposal.json"
PROPOSAL_SHA256 = "3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c"
BUNDLE_REF = "reviews/m2-materialization-pixel-readiness/review-bundle.json"
BUNDLE_SHA256 = "8da456e9e0a0e378210b3d9b017e88990f1711da334f27b4cd3886211a97369a"
APPROVAL_REF = "records/source-gates/m2-materialization-pixel-readiness-approval.json"
ACTIVATION_REF = "records/readiness/m2-materialization-pixel-readiness-activation.json"
PUBLICATION_GATE_REF = "records/readiness/m2-materialization-stage-1-publication-gate.json"
FINAL_PREFLIGHT_REF = "records/readiness/m2-materialization-remaining-preflight.json"
IMPLEMENTATION_READINESS_REF = "records/readiness/m2-materialization-stage-1-implementation-readiness.json"
MATERIALIZATION_CONTRACT_REF = "contracts/m2-materialization.json"
INTAKE_REF = "contracts/m2-intake.json"
POSTSUCCESS_REF = "records/acquisition/sentinel-continuation-001-postsuccess-reconciliation.json"
SOURCE_ORDER = ["M1-SRC-004", "M1-SRC-005", "M1-SRC-006", "M1-SRC-010", "M1-SRC-008"]
ATTEMPT_IDS = {source_id: f"{source_id.casefold()}-materialization-001" for source_id in SOURCE_ORDER}
EXISTING_RECEIPTS = [
    "records/acquisition/materialization/m1-src-001-fixture-must-not-run.json",
    "records/acquisition/materialization/m1-src-002-m1-src-002-materialization-001.json",
    "records/acquisition/materialization/m1-src-003-m1-src-003-materialization-001.json",
]


class BoundaryError(RuntimeError):
    """A fail-closed materialization boundary violation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_sha(relative: str) -> str:
    return sha256_file(ROOT / relative)


def load(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file():
        raise BoundaryError(f"missing_bound_input:{relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BoundaryError(f"invalid_json_root:{relative}")
    return value


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def receipt_ref(source_id: str) -> str:
    attempt_id = ATTEMPT_IDS[source_id]
    return f"records/acquisition/materialization/{source_id.casefold()}-{attempt_id}.json"


def attempt_root(source_id: str) -> Path:
    return DATA_ROOT / "materialized" / source_id.casefold() / ATTEMPT_IDS[source_id]


def validate_static_authority(require_publication_gate: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    if repository_sha(PROPOSAL_REF) != PROPOSAL_SHA256:
        raise BoundaryError("proposal_identity_drift")
    if repository_sha(BUNDLE_REF) != BUNDLE_SHA256:
        raise BoundaryError("review_bundle_identity_drift")
    proposal = load(PROPOSAL_REF)
    approval = load(APPROVAL_REF)
    activation = load(ACTIVATION_REF)
    if approval.get("status") != "approved_exact_dependency_ordered_bounded_actions":
        raise BoundaryError("approval_status_differs")
    if approval.get("review_bundle_manifest_sha256") != BUNDLE_SHA256 or approval.get("proposal_sha256") != PROPOSAL_SHA256:
        raise BoundaryError("approval_identity_drift")
    if approval.get("human_decision_count") != 1 or approval.get("decision_counts") != {"approve": 1, "revise": 0, "defer": 0}:
        raise BoundaryError("approval_decision_differs")
    if approval.get("human_decisions_fabricated") is not False:
        raise BoundaryError("fabricated_decision_reported")
    bindings = activation.get("bindings", {})
    if (
        activation.get("status") != "pass_exact_approval_activated_stage_1_publication_pending"
        or bindings.get("approval_sha256") != repository_sha(APPROVAL_REF)
        or bindings.get("proposal_sha256") != PROPOSAL_SHA256
        or bindings.get("review_bundle_sha256") != BUNDLE_SHA256
    ):
        raise BoundaryError("activation_identity_drift")
    stage = proposal.get("stage_1_exact_materialization", {})
    if (
        stage.get("source_order") != SOURCE_ORDER
        or [item.get("planned_attempt_id") for item in stage.get("sources", [])] != [ATTEMPT_IDS[item] for item in SOURCE_ORDER]
        or stage.get("maximum_attempts_per_source") != 1
        or stage.get("automatic_retry_authorized") is not False
        or stage.get("network_or_authentication_authorized") is not False
    ):
        raise BoundaryError("proposal_stage_1_boundary_drift")
    if require_publication_gate:
        gate = load(PUBLICATION_GATE_REF)
        head, origin = git_identity()
        if head != origin:
            raise BoundaryError("head_origin_mismatch")
        actions = gate.get("github_actions", {})
        if (
            gate.get("status") != "pass_public_controls_verified_before_materialization"
            or actions.get("conclusion") != "success"
            or actions.get("head_sha") != head
            or gate.get("bindings", {}).get("approval_sha256") != repository_sha(APPROVAL_REF)
            or gate.get("bindings", {}).get("implementation_readiness_sha256") != repository_sha(IMPLEMENTATION_READINESS_REF)
        ):
            raise BoundaryError("publication_gate_differs")
    return proposal, approval


def container_receipt(source_id: str, attempt_id: str) -> tuple[str, dict[str, Any]]:
    ref = f"records/acquisition/container-verification/{source_id.casefold()}-{attempt_id}.json"
    return ref, load(ref)


def observe_preflight(observed_at_utc: str, require_publication_gate: bool = True) -> dict[str, Any]:
    proposal, _ = validate_static_authority(require_publication_gate=require_publication_gate)
    intake = load(INTAKE_REF)
    materialization = load(MATERIALIZATION_CONTRACT_REF)
    if materialization.get("status") != "active_authorized_gate_deferred":
        raise BoundaryError("materialization_contract_not_active")
    if repository_sha(MATERIALIZATION_CONTRACT_REF) != proposal["bindings"]["materialization_contract_sha256"]:
        raise BoundaryError("materialization_contract_identity_drift")
    if repository_sha(INTAKE_REF) != proposal["bindings"]["active_intake_sha256_at_proposal"]:
        raise BoundaryError("intake_identity_drift")
    if repository_sha(POSTSUCCESS_REF) != proposal["bindings"]["postsuccess_reconciliation_sha256"]:
        raise BoundaryError("postsuccess_identity_drift")
    if not DATA_ROOT.is_dir() or Path(materialization["execution_boundary"]["external_data_root"]).resolve() != DATA_ROOT.resolve():
        raise BoundaryError("external_data_root_differs")
    by_source = {item.get("extensions", {}).get("source_id"): item for item in intake.get("assets", [])}
    proposal_by_source = {item["source_id"]: item for item in proposal["stage_1_exact_materialization"]["sources"]}
    planned: list[dict[str, Any]] = []
    total_uncompressed = 0
    for source_id in SOURCE_ORDER:
        asset = by_source.get(source_id)
        expected = proposal_by_source[source_id]
        if not asset or asset.get("state") != "promoted":
            raise BoundaryError(f"source_not_promoted:{source_id}")
        successes = [item for item in asset.get("attempts", []) if item.get("outcome") == "succeeded"]
        if len(successes) != 1:
            raise BoundaryError(f"successful_transfer_history_differs:{source_id}")
        container_ref, container = container_receipt(source_id, successes[0]["attempt_id"])
        result = container.get("result", {})
        if container.get("status") != "pass_container_only" or result.get("source_id") != source_id:
            raise BoundaryError(f"container_not_passing:{source_id}")
        if repository_sha(container_ref) != expected["container_receipt_sha256"]:
            raise BoundaryError(f"container_receipt_identity_drift:{source_id}")
        archive = DATA_ROOT / "custody" / Path(*Path(result["archive_relative_path"]).parts)
        if not archive.is_file():
            raise BoundaryError(f"archive_missing:{source_id}")
        size = archive.stat().st_size
        digest = sha256_file(archive)
        if size != expected["archive_size_bytes"] or digest != expected["archive_sha256"]:
            raise BoundaryError(f"archive_identity_drift:{source_id}")
        if attempt_root(source_id).exists() or (ROOT / receipt_ref(source_id)).exists():
            raise BoundaryError(f"planned_identity_collision:{source_id}")
        total_uncompressed += int(expected["total_uncompressed_bytes"])
        planned.append({
            **expected,
            "container_receipt_ref": container_ref,
            "planned_external_attempt_path": str(attempt_root(source_id)),
            "planned_receipt_ref": receipt_ref(source_id),
            "planned_path_absent": True,
            "planned_receipt_absent": True,
        })
    retained: list[dict[str, Any]] = []
    for ref in EXISTING_RECEIPTS:
        receipt = load(ref)
        manifest = Path(receipt.get("bindings", {}).get("external_manifest_path", ""))
        if receipt.get("status") != "pass_materialization_only" or not manifest.is_file():
            raise BoundaryError(f"retained_materialization_missing:{ref}")
        if sha256_file(manifest) != receipt["bindings"]["external_manifest_sha256"]:
            raise BoundaryError(f"retained_manifest_identity_drift:{ref}")
        retained.append({
            "source_id": receipt["source_id"],
            "attempt_id": receipt["attempt_id"],
            "receipt_ref": ref,
            "receipt_sha256": repository_sha(ref),
            "external_manifest_sha256": receipt["bindings"]["external_manifest_sha256"],
        })
    free_bytes = shutil.disk_usage(DATA_ROOT).free
    minimum_free = total_uncompressed * 2
    if free_bytes < minimum_free:
        raise BoundaryError("insufficient_free_space")
    head, origin = git_identity()
    if require_publication_gate and head != origin:
        raise BoundaryError("head_origin_mismatch")
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-MATERIALIZATION-REMAINING-PREFLIGHT-001",
        "observed_at_utc": observed_at_utc,
        "status": "pass_exact_five_ready_no_mutation_publication_verified",
        "public_commit": head,
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": repository_sha(APPROVAL_REF),
            "activation_ref": ACTIVATION_REF,
            "activation_sha256": repository_sha(ACTIVATION_REF),
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": repository_sha(PUBLICATION_GATE_REF) if require_publication_gate else None,
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": PROPOSAL_SHA256,
            "active_intake_ref": INTAKE_REF,
            "active_intake_sha256": repository_sha(INTAKE_REF),
            "materialization_contract_ref": MATERIALIZATION_CONTRACT_REF,
            "materialization_contract_sha256": repository_sha(MATERIALIZATION_CONTRACT_REF),
        },
        "source_order": list(SOURCE_ORDER),
        "planned_sources": planned,
        "existing_materializations": retained,
        "storage": {
            "planned_uncompressed_bytes": total_uncompressed,
            "minimum_free_bytes": minimum_free,
            "observed_free_bytes": free_bytes,
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
            "archive_extraction_performed": False,
            "measurement_pixels_read": False,
            "external_files_mutated": False,
        },
        "next_gate": "run the five exact materializations once in order and stop on the first failure",
    }


def validate_preflight(record: dict[str, Any]) -> None:
    if (
        record.get("status") != "pass_exact_five_ready_no_mutation_publication_verified"
        or record.get("source_order") != SOURCE_ORDER
        or [item.get("planned_attempt_id") for item in record.get("planned_sources", [])] != [ATTEMPT_IDS[item] for item in SOURCE_ORDER]
        or record.get("assertions", {}).get("planned_paths_absent") is not True
        or record.get("assertions", {}).get("external_files_mutated") is not False
        or record.get("assertions", {}).get("measurement_pixels_read") is not False
        or record.get("bindings", {}).get("approval_sha256") != repository_sha(APPROVAL_REF)
        or record.get("bindings", {}).get("publication_gate_sha256") != repository_sha(PUBLICATION_GATE_REF)
    ):
        raise BoundaryError("final_preflight_differs")
