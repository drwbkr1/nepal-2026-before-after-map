#!/usr/bin/env python3
"""Record that public CI releases only the final orbit-continuation preflight."""

from __future__ import annotations

import argparse
import json

from m2_orbit_continuation_001_core import (
    APPROVAL_REF,
    CONTROL_RECONCILIATION_REF,
    PUBLICATION_GATE_REF,
    ROOT,
    SOURCE_ORDER,
    load_object,
    sha256_file,
    validate_approval_files,
    validate_publication_gate,
    write_new_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled-at-utc", required=True)
    args = parser.parse_args()
    output = ROOT / CONTROL_RECONCILIATION_REF
    if output.exists():
        raise SystemExit("refusing control-reconciliation output collision")
    validate_approval_files()
    gate = load_object(ROOT / PUBLICATION_GATE_REF)
    validate_publication_gate(gate)
    milestone = load_object(ROOT / "contracts/milestone-002.json")
    profile = load_object(ROOT / "records/project-control-profile.json")
    units = {item.get("id"): item for item in milestone.get("units", [])}
    review = units.get("M2-ORBIT-CONTINUATION-001-REVIEW", {})
    implementation = units.get("M2-ORBIT-CONTINUATION-001-IMPLEMENTATION", {})
    continuation = units.get("M2-ORBIT-CONTINUATION-001", {})
    if (
        review.get("status") != "complete"
        or review.get("disposition") != "pass"
        or review.get("gates", {}).get("continuation_authorized") is not True
        or implementation.get("status") != "in_progress"
        or implementation.get("gates", {}).get("public_ci") != "pending"
        or continuation.get("status") != "planned"
        or profile.get("current_checkpoint", {}).get("checkpoint_id") != "M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"
    ):
        raise SystemExit("tracked implementation checkpoint drift")
    payload = {
        "schema_version": "1.0",
        "receipt_id": "NEPAL-M2-ORBIT-CONTINUATION-001-CONTROL-RECONCILIATION",
        "reconciled_at_utc": args.reconciled_at_utc,
        "status": "pass_public_ci_exact_continuation_ready_final_preflight_pending",
        "source_ids_in_exact_order": list(SOURCE_ORDER),
        "bindings": {
            "approval_sha256": sha256_file(ROOT / APPROVAL_REF),
            "publication_gate_sha256": sha256_file(ROOT / PUBLICATION_GATE_REF),
            "milestone_sha256": sha256_file(ROOT / "contracts/milestone-002.json"),
            "profile_sha256": sha256_file(ROOT / "records/project-control-profile.json"),
            "goal_sha256": sha256_file(ROOT / "records/long-term-goal.json"),
        },
        "released_now": {
            "final_no_payload_preflight": True,
            "owner_handoff_after_passing_preflight": True,
            "maximum_owner_handoffs": 1,
            "maximum_real_attempts_per_source": 1,
            "stop_on_first_failure": True,
            "automatic_retry": False,
            "m2_orb_001_request_or_mutation": False,
            "orbit_application_or_downstream_science": False,
        },
        "assertions": {
            "credential_values_read_or_recorded": False,
            "network_or_payload_request_performed": False,
            "external_data_mutated": False,
        },
        "next_gate": "activate the exact continuation contract and run its single final no-payload preflight",
    }
    write_new_json(output, payload)
    print(json.dumps({"status": payload["status"], "output": str(output.relative_to(ROOT)).replace("\\", "/")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
