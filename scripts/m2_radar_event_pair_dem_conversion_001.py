#!/usr/bin/env python3
"""Fixed-order offline conversion of seven verified event-pair DEM tiles."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from convert_m2_dem_vertical_datum_proj25 import convert_one, utc_now
from m2_dem_vertical_datum_proj25_core import controlled_path, sha256_file
from m2_radar_event_pair_dem_intake_001 import (
    DATA_ROOT, ITEMS, ROOT, IntakeError, exact_assets, paths_for, require_execution_gates,
)


GRID = DATA_ROOT / "custody" / "geoid" / "proj" / "us_nga_egm08_25.tif"
GRID_SHA = "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a"
SIGN_REF = ROOT / "records" / "acquisition" / "m2-dem-vertical-datum-proj25-operation-selection-sign-preflight.json"
OLD_CONTRACT_REF = ROOT / "config" / "qa" / "m2-dem-vertical-datum-proj25-contract.json"
BATCH_REF = ROOT / "records" / "processing" / "m2-radar-event-area-pair-001-dem-conversion-batch.json"


def conversion_items(*, require_outputs_absent: bool = True) -> list[dict[str, Any]]:
    assets = exact_assets()
    if [item["item_id"] for item in assets] != list(ITEMS):
        raise IntakeError("conversion_order_drift")
    items: list[dict[str, Any]] = []
    for index, asset in enumerate(assets, 1):
        item_id = asset["item_id"]
        paths = paths_for(item_id)
        if not paths["terminal"].is_file() or not paths["destination"].is_file():
            raise IntakeError("dem_tile_not_verified")
        receipt = json.loads(paths["terminal"].read_text(encoding="utf-8"))
        if (
            receipt.get("status") != "pass_verified_and_promoted"
            or receipt.get("item_id") != item_id
            or receipt.get("size_bytes") != paths["destination"].stat().st_size
            or receipt.get("sha256") != sha256_file(paths["destination"])
        ):
            raise IntakeError("dem_tile_custody_identity_drift")
        output_relative = f"derived/dem/egm2008-ellipsoidal-proj25/{item_id}_WGS84_ELLIPSOIDAL.tif"
        if require_outputs_absent and controlled_path(output_relative).exists():
            raise IntakeError("conversion_output_collision")
        items.append({
            "source_id": f"M2-DEM-EVENT-{index:03d}",
            "source_relative_path": f"custody/dem/copernicus-glo30/{item_id}.tif",
            "source_sha256": receipt["sha256"],
            "output_relative_path": output_relative,
        })
    return items


def verify_offline_dependencies() -> None:
    require_execution_gates()
    for suffix in ("implementation-publication-gate", "execution-publication-gate"):
        gate = json.loads((ROOT / "records" / "readiness" / f"m2-radar-event-area-pair-001-{suffix}.json").read_text(encoding="utf-8"))
        if gate.get("bindings", {}).get("conversion_code_sha256") != sha256_file(Path(__file__)):
            raise IntakeError("conversion_public_gate_missing")
    if not GRID.is_file() or sha256_file(GRID) != GRID_SHA:
        raise IntakeError("exact_proj25_grid_missing_or_drifted")
    sign = json.loads(SIGN_REF.read_text(encoding="utf-8"))
    if (
        sign.get("status") != "pass_exact_local_inverse_operation_h_equals_H_plus_N"
        or sign.get("grid_sha256") != GRID_SHA
        or sign.get("source_crs") != "EPSG:9518"
        or sign.get("target_crs") != "EPSG:4979"
        or sign.get("assertions", {}).get("proj_network_enabled") is not False
    ):
        raise IntakeError("vertical_operation_sign_preflight_drift")
    old = json.loads(OLD_CONTRACT_REF.read_text(encoding="utf-8"))
    if len(old["dem_sources_in_exact_order"]) != 4:
        raise IntakeError("prior_four_tile_contract_drift")
    for prior in old["dem_sources_in_exact_order"]:
        source = controlled_path(prior["source_relative_path"])
        output = controlled_path(prior["output_relative_path"])
        receipt_path = ROOT / "records" / "processing" / f"{prior['source_id'].lower()}-proj25-conversion-001-terminal.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            not source.is_file() or sha256_file(source) != prior["source_sha256"]
            or not output.is_file()
            or receipt.get("status") != "pass_converted_verified_promoted"
            or sha256_file(output) != receipt.get("promoted", {}).get("sha256")
        ):
            raise IntakeError("prior_four_tile_derivative_identity_drift")


def run_conversion_batch(*, converter=convert_one) -> dict[str, Any]:
    verify_offline_dependencies()
    items = conversion_items()
    if BATCH_REF.exists():
        raise IntakeError("conversion_batch_already_consumed")
    BATCH_REF.parent.mkdir(parents=True, exist_ok=True)
    with BATCH_REF.open("xb") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    started = utc_now()
    results = []
    for item in items:
        try:
            result = converter(item, GRID, utc_now())
        except BaseException:
            result = {"status": "terminal_indeterminate_stop_no_retry", "attempt_id": f"{item['source_id'].lower()}-proj25-conversion-001"}
        results.append({"source_id": item["source_id"], "status": result["status"], "attempt_id": result["attempt_id"]})
        if result["status"] != "pass_converted_verified_promoted":
            break
    status = "pass_seven_fixed_order_conversions_verified" if len(results) == 7 and all(item["status"] == "pass_converted_verified_promoted" for item in results) else "terminal_failure_stop_no_retry"
    record = {"schema_version": "1.0", "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-DEM-CONVERSION-BATCH", "status": status, "started_at_utc": started, "completed_at_utc": utc_now(), "fixed_order": [item["source_id"] for item in items], "attempted": results, "automatic_retry": False, "source_overwrite": False, "radar_processing_started": False}
    with BATCH_REF.open("r+b") as stream:
        if stream.seek(0, os.SEEK_END) != 0:
            raise IntakeError("batch_receipt_already_written")
        stream.write((json.dumps(record, indent=2) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-fixed-order", action="store_true", required=True)
    parser.parse_args()
    try:
        result = run_conversion_batch()
        print(json.dumps({"status": result["status"], "attempted_count": len(result["attempted"])}))
        return 0 if result["status"] == "pass_seven_fixed_order_conversions_verified" else 20
    except IntakeError as exc:
        print(json.dumps({"status": "stopped_without_conversion", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
