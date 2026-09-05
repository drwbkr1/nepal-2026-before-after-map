#!/usr/bin/env python3
"""Verify recovery-001 inputs and paths without opening product pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath

from m2_optical_pixel_recovery_stage_gate import (
    APPROVAL_REF,
    CONTRACT_REF,
    PUBLICATION_GATE_REF,
    REAL_001_RECONCILIATION_REF,
    ROOT,
    load,
    sha256,
    validate_recovery_publication,
)


OUTPUT_REF = "records/readiness/m2-optical-pixel-recovery-001-final-preflight.json"


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observed-at-utc", required=True)
    args = parser.parse_args()
    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("refusing optical pixel recovery preflight collision")
    validate_recovery_publication()
    contract = load(CONTRACT_REF)
    retained = load(REAL_001_RECONCILIATION_REF)
    data_root = Path(contract["execution_boundary"]["external_data_root"]).resolve(strict=True)
    attempt_root = Path(contract["attempt"]["external_attempt_root"])
    receipt_path = ROOT / contract["attempt"]["public_receipt_ref"]
    if attempt_root.exists() or receipt_path.exists():
        raise SystemExit("optical pixel recovery attempt path collision")
    if attempt_root.parent.resolve(strict=True) != (data_root / "derived").resolve(strict=True):
        raise SystemExit("optical pixel recovery attempt root differs")
    retained_root = Path(contract["retained_real_001"]["external_attempt_root"]).resolve(strict=True)
    retained_inventory = []
    for path in sorted((item for item in retained_root.rglob("*") if item.is_file()), key=lambda item: str(item).casefold()):
        retained_inventory.append(
            {
                "relative_path": path.relative_to(retained_root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": file_sha(path),
            }
        )
    if retained_inventory != retained.get("external_attempt", {}).get("inventory"):
        raise SystemExit("retained real-001 external inventory differs")
    selected = []
    for role in ("before", "after"):
        product = contract["products"][role]
        materialization = load(product["materialization_receipt_ref"])
        safe_root = Path(materialization["external_safe_root"]).resolve(strict=True)
        safe_root.relative_to(data_root)
        if sha256(product["materialization_receipt_ref"]) != product["materialization_receipt_sha256"]:
            raise SystemExit(f"materialization receipt differs: {role}")
        for member_role, member in product["selected_members"].items():
            path = safe_root.joinpath(*PurePosixPath(member["relative_path"]).parts).resolve(strict=True)
            path.relative_to(safe_root)
            digest = file_sha(path)
            if path.stat().st_size != member["size_bytes"] or digest != member["sha256"]:
                raise SystemExit(f"selected input differs: {role}:{member_role}")
            selected.append(
                {
                    "product_role": role,
                    "member_role": member_role,
                    "relative_path": member["relative_path"],
                    "size_bytes": member["size_bytes"],
                    "sha256": digest,
                }
            )
    required_free = int(contract["attempt"]["minimum_free_space_bytes"])
    free = shutil.disk_usage(data_root).free
    if free < required_free:
        raise SystemExit("insufficient free space for exact optical pixel recovery attempt")
    record = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-OPTICAL-PIXEL-RECOVERY-001-FINAL-PREFLIGHT",
        "observed_at_utc": args.observed_at_utc,
        "status": "pass_exact_optical_pixel_recovery_001_inputs_ready_no_pixel_access",
        "bindings": {
            "approval_ref": APPROVAL_REF,
            "approval_sha256": sha256(APPROVAL_REF),
            "real_001_reconciliation_ref": REAL_001_RECONCILIATION_REF,
            "real_001_reconciliation_sha256": sha256(REAL_001_RECONCILIATION_REF),
            "contract_ref": CONTRACT_REF,
            "contract_sha256": sha256(CONTRACT_REF),
            "publication_gate_ref": PUBLICATION_GATE_REF,
            "publication_gate_sha256": sha256(PUBLICATION_GATE_REF),
        },
        "attempt": {
            "attempt_id": contract["attempt"]["attempt_id"],
            "external_attempt_root": str(attempt_root),
            "public_receipt_ref": contract["attempt"]["public_receipt_ref"],
        },
        "selected_inputs": selected,
        "retained_real_001_inventory": retained_inventory,
        "storage": {"free_bytes": free, "minimum_free_space_bytes": required_free, "status": "pass"},
        "assertions": {
            "exact_pair": [contract["exact_pair"]["before_source_id"], contract["exact_pair"]["after_source_id"]],
            "approved_aoi_ids": contract["approved_aoi_ids"],
            "selected_files_rehashed": True,
            "recovery_attempt_paths_absent": True,
            "real_001_preserved_exact": True,
            "network_requests_performed": False,
            "authentication_performed": False,
            "external_files_mutated": False,
            "real_product_pixels_examined": False,
            "thresholds_sources_or_aois_changed": False,
        },
        "next_gate": "invoke optical-pixel-readiness-recovery-001 exactly once and preserve its terminal result without retry",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "output": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
