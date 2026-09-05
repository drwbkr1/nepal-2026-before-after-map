#!/usr/bin/env python3
"""Verify exact header inputs without opening a real raster dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath

from m2_header_stage_gate import (
    APPROVAL_REF,
    MATERIALIZATION_RECONCILIATION_REF,
    PUBLICATION_GATE_REF,
    ROOT,
    load,
    sha256,
)
from optical_input_readiness_core_full_cohort_001 import select_required_members as select_optical
from radar_input_readiness_core_full_cohort_001 import select_required_members as select_radar


OUTPUT_REF = "records/readiness/m2-header-stage-final-preflight.json"
RADAR_CONTRACT_REF = "config/qa/radar-input-readiness-contract-full-cohort-001.json"
OPTICAL_CONTRACT_REF = "config/qa/optical-input-readiness-contract-full-cohort-001.json"
REAL_OUTPUTS = [
    "records/readiness/radar-input/m2-s1-input-readiness-real-003.json",
    "records/readiness/optical-input/m2-s2-input-readiness-real-001.json",
]


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_receipt(expected: dict, contract: dict, selector) -> dict:
    ref = expected["materialization_receipt_ref"]
    receipt = load(ref)
    if sha256(ref) != expected["materialization_receipt_sha256"] or receipt.get("status") != "pass_materialization_only":
        raise RuntimeError(f"materialization receipt differs: {ref}")
    manifest_path = Path(receipt["bindings"]["external_manifest_path"])
    safe_root = Path(receipt["external_safe_root"])
    data_root = Path(contract["execution_boundary"]["external_data_root"]).resolve(strict=True)
    for candidate in (manifest_path, safe_root):
        candidate.resolve(strict=True).relative_to(data_root)
    if file_sha(manifest_path) != expected["external_manifest_sha256"]:
        raise RuntimeError(f"external manifest differs: {ref}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inventory = selector(manifest, contract)
    if inventory.get("status") != "pass_inventory_only":
        raise RuntimeError(f"required member inventory does not pass: {ref}")
    selected = []
    for role, item in sorted(inventory["members"].items()):
        path = safe_root.joinpath(*PurePosixPath(item["relative_path"]).parts)
        path.resolve(strict=True).relative_to(safe_root.resolve(strict=True))
        digest = file_sha(path)
        if path.stat().st_size != item["size_bytes"] or digest != item["sha256"]:
            raise RuntimeError(f"selected member differs: {ref}:{role}")
        selected.append({"role": role, "relative_path": item["relative_path"], "size_bytes": item["size_bytes"], "sha256": digest})
    return {"source_id": expected["source_id"], "receipt_ref": ref, "receipt_sha256": sha256(ref), "selected_members": selected}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", required=True)
    args = parser.parse_args()
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("refusing final-preflight output collision")
    gate = load(PUBLICATION_GATE_REF)
    if gate.get("status") != "pass_public_controls_verified_before_real_header_inspections":
        raise SystemExit("header publication gate is not passing")
    radar = load(RADAR_CONTRACT_REF)
    optical = load(OPTICAL_CONTRACT_REF)
    if any((ROOT / ref).exists() for ref in REAL_OUTPUTS):
        raise SystemExit("real header attempt output collision")
    radar_sources = [inspect_receipt(item, radar, select_radar) for item in radar["sources"]]
    optical_sources = []
    for role in ("before", "after"):
        item = optical["materializations"][role]
        expected = {
            "source_id": item["source_id"],
            "materialization_receipt_ref": item["receipt_ref"],
            "materialization_receipt_sha256": item["receipt_sha256"],
            "external_manifest_sha256": item["external_manifest_sha256"],
        }
        optical_sources.append(inspect_receipt(expected, optical, select_optical))
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-FULL-HEADER-READINESS-PREFLIGHT-001",
        "observed_at_utc": args.observed_at_utc,
        "status": "pass_exact_header_inputs_ready_no_real_header_access",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(APPROVAL_REF),
            "materialization_reconciliation_ref": MATERIALIZATION_RECONCILIATION_REF,
            "materialization_reconciliation_sha256": sha256(MATERIALIZATION_RECONCILIATION_REF),
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256(PUBLICATION_GATE_REF),
            "radar_contract_ref": RADAR_CONTRACT_REF,
            "radar_contract_sha256": sha256(RADAR_CONTRACT_REF),
            "optical_contract_ref": OPTICAL_CONTRACT_REF,
            "optical_contract_sha256": sha256(OPTICAL_CONTRACT_REF),
        },
        "radar_sources": radar_sources,
        "optical_sources": optical_sources,
        "assertions": {
            "radar_source_count": 6,
            "optical_source_count": 2,
            "selected_members_rehashed": True,
            "real_attempt_outputs_absent": True,
            "network_requests_performed": False,
            "authentication_performed": False,
            "external_data_mutated": False,
            "real_raster_headers_opened": False,
            "measurement_pixels_decoded": False,
        },
        "next_gate": "invoke radar real-003 once, then optical real-001 once; retain either non-pass independently",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": record["status"], "output": OUTPUT_REF, "sha256": file_sha(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
