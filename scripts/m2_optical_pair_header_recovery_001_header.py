#!/usr/bin/env python3
"""Apply the frozen optical header predicates to one distinct recovery receipt."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from m2_optical_pair_header_recovery_001_core import (
    HEADER_RECEIPT, PilotControlError, now_utc, read_json,
    require_execution_release, write_new_json,
)
from m2_optical_pair_pilot_001_offline import (
    HEADER_CONTRACT, inspect_materialized_one,
)
from optical_input_readiness_core import decide_header_readiness, validate_pair_grids


def inspect_recovery_headers(sources: list[dict[str, Any]], arcpy: Any, output: Path = HEADER_RECEIPT) -> dict[str, Any]:
    require_execution_release()
    if [item.get("source_id") for item in sources] != ["M2-OPT-001", "M2-OPT-002"]:
        raise PilotControlError("recovery_header_pair_order_drift")
    if output.exists():
        raise PilotControlError("recovery_header_attempt_consumed")
    contract = read_json(HEADER_CONTRACT)
    products = [inspect_materialized_one(source, arcpy, contract) for source in sources]
    grid_errors = validate_pair_grids(products[0]["descriptions"], products[1]["descriptions"], contract)
    decision = decide_header_readiness(
        {item["source_id"]: item["inventory"]["status"] for item in products},
        {item["source_id"]: item["metadata_errors"] for item in products},
        grid_errors,
    )
    receipt = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-HEADER-RECEIPT-RECOVERY-001-HEADER",
        "status": decision["status"], "checked_at_utc": now_utc(),
        "pair": [item["source_id"] for item in sources],
        "products": {item["source_id"]: item for item in products},
        "decision": decision,
        "activity": {"pixel_values_examined": False, "network_requests": False, "authentication": False},
        "claim_boundary": {"baseline_established": False, "change_established": False, "scientific_admission": False},
    }
    write_new_json(output, receipt)
    return receipt
