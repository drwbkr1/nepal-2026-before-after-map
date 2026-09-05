#!/usr/bin/env python3
"""Run the final authenticated-free, no-payload preflight for continuation-001."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess

from acquire_m2_product_pipe import live_page_consistency_check, public_catalog_check
from m2_sentinel_continuation_001_core import (
    ACTIVATION_REF,
    ACTIVE_INTAKE_REF,
    APPROVAL_REF,
    CONTRACT_REF,
    FINAL_PREFLIGHT_REF,
    IMPLEMENTATION_READINESS_REF,
    PROPOSAL_REF,
    PUBLICATION_GATE_REF,
    ROOT,
    SOURCE_ORDER,
    load_object,
    require_exact_contract,
    sha256_file,
    validate_approval_files,
    validate_initial_asset_state,
    validate_initial_paths_absent,
    validate_publication_gate,
    validate_retained_and_recovered_bytes,
    write_new_json,
)
from record_m2_sentinel_continuation_001_publication_gate import FILES as PUBLICATION_FILES


PREFLIGHT_REFRESH_PATH = ROOT / "records/acquisition/preflight-refresh.json"
PLAN_PATH = ROOT / "records/acquisition-plan.json"
MINIMUM_FREE_GIB = 60.0


def git_identity() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    origin = subprocess.run(["git", "rev-parse", "origin/main"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return head, origin


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-at-utc", required=True)
    args = parser.parse_args()
    output = ROOT / FINAL_PREFLIGHT_REF
    if output.exists():
        raise SystemExit("refusing final-preflight output collision")
    validate_approval_files()
    contract_path = ROOT / CONTRACT_REF
    contract = load_object(contract_path)
    require_exact_contract(contract)
    gate_path = ROOT / PUBLICATION_GATE_REF
    gate = load_object(gate_path)
    validate_publication_gate(gate)
    head, origin = git_identity()
    if head != origin or gate.get("github_actions", {}).get("head_sha") != head:
        raise SystemExit("public commit is not current HEAD and origin/main")
    if gate.get("bindings") != {key: sha256_file(path) for key, path in PUBLICATION_FILES.items()}:
        raise SystemExit("publication gate implementation bindings drift")

    activation_path = ROOT / ACTIVATION_REF
    activation = load_object(activation_path)
    if (
        activation.get("status") != "pass_exact_continuation_001_activated_final_no_payload_preflight_pending"
        or activation.get("bindings", {}).get("continuation_contract_sha256") != sha256_file(contract_path)
        or activation.get("bindings", {}).get("active_intake_sha256") != sha256_file(ROOT / ACTIVE_INTAKE_REF)
        or activation.get("bindings", {}).get("public_commit") != head
    ):
        raise SystemExit("continuation activation binding drift")

    intake = load_object(ROOT / ACTIVE_INTAKE_REF)
    snapshots = validate_initial_asset_state(intake)
    if contract.get("assets") != snapshots:
        raise SystemExit("continuation contract asset snapshot drift")
    paths = validate_initial_paths_absent(intake)
    retained = validate_retained_and_recovered_bytes(intake)
    free_gib = shutil.disk_usage(ROOT.parent).free / (1024 ** 3)
    if free_gib < MINIMUM_FREE_GIB:
        raise SystemExit("free space below approved minimum")

    refresh = load_object(PREFLIGHT_REFRESH_PATH)
    page_observations = live_page_consistency_check(refresh)
    plan = load_object(PLAN_PATH)
    plan_by_source = {item.get("source_id"): item for item in plan.get("records", [])}
    intake_by_source = {item.get("extensions", {}).get("source_id"): item for item in intake.get("assets", [])}
    catalogs = []
    for source_id in SOURCE_ORDER:
        if source_id not in plan_by_source or source_id not in intake_by_source:
            raise SystemExit("continuation source missing from plan or intake")
        observed = public_catalog_check(intake_by_source[source_id], plan_by_source[source_id])
        catalogs.append({
            "source_id": source_id,
            "provider_product_id": intake_by_source[source_id]["extensions"]["provider_product_id"],
            "catalog_response_sha256": observed["response_sha256"],
            "content_length_bytes": observed["content_length_bytes"],
            "provider_md5": observed["provider_md5"],
            "provider_blake3_metadata": observed["provider_blake3_metadata"],
            "checks": observed["checks"],
        })

    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-SENTINEL-CONTINUATION-001-FINAL-PREFLIGHT-001",
        "verified_at_utc": args.verified_at_utc,
        "status": "pass_no_payload_ready_for_single_secret_pipe_handoff",
        "source_ids_in_exact_order": list(SOURCE_ORDER),
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": sha256_file(ROOT / PROPOSAL_REF),
            "implementation_readiness_ref": IMPLEMENTATION_READINESS_REF,
            "implementation_readiness_sha256": sha256_file(ROOT / IMPLEMENTATION_READINESS_REF),
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256_file(gate_path),
            "activation_ref": ACTIVATION_REF,
            "activation_sha256": sha256_file(activation_path),
            "continuation_contract_ref": CONTRACT_REF,
            "continuation_contract_sha256": sha256_file(contract_path),
            "active_intake_ref": ACTIVE_INTAKE_REF,
            "active_intake_sha256": sha256_file(ROOT / ACTIVE_INTAKE_REF),
            "public_commit": head,
        },
        "current_state": {
            "fresh_authorized_sources": snapshots,
            "path_absence": paths,
            "retained_and_recovered_bytes": retained,
            "free_gib": free_gib,
            "minimum_free_gib": MINIMUM_FREE_GIB,
        },
        "live_metadata_checks": {
            "official_page_observations": page_observations,
            "catalog_products": catalogs,
        },
        "assertions": {
            "metadata_network_requests_performed": True,
            "authentication_performed": False,
            "credential_presence_checked": False,
            "credential_values_read_or_recorded": False,
            "product_payload_requested": False,
            "product_payload_bytes_received": 0,
            "external_files_mutated": False,
            "m1_src_004_requested": False,
            "automatic_retry_authorized": False,
            "pixel_processing_released": False,
        },
        "next_gate": "open the continuation broker once and paste one fresh owner token into the hidden prompt",
    }
    write_new_json(output, payload)
    print(json.dumps({
        "status": payload["status"],
        "output": str(output.relative_to(ROOT)).replace("\\", "/"),
        "catalog_product_count": len(catalogs),
        "credential_values_read_or_recorded": False,
        "product_payload_requested": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
