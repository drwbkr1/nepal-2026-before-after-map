#!/usr/bin/env python3
"""Reconcile eleven DEM derivatives and measure every touching correction seam."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from convert_m2_dem_vertical_datum_proj25 import correction_edge
from m2_dem_vertical_datum_proj25_core import controlled_path, sha256_file
from m2_radar_event_pair_dem_conversion_001 import BATCH_REF, OLD_CONTRACT_REF, conversion_items
from m2_radar_event_pair_dem_intake_001 import IntakeError, ROOT


OUTPUT = ROOT / "records" / "processing" / "m2-radar-event-area-pair-001-dem-conversion-reconciliation.json"
CELL_PATTERN = re.compile(r"_N(\d{2})_00_E(\d{3})_00_DEM")


def cell_for(item: dict[str, Any]) -> tuple[int, int]:
    matched = CELL_PATTERN.search(Path(item["source_relative_path"]).name)
    if not matched:
        raise IntakeError("dem_cell_name_unparseable")
    return int(matched.group(1)), int(matched.group(2))


def adjacent_pairs(items: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str, dict[str, Any], str, str]]:
    by_cell = {cell_for(item): item for item in items}
    if len(by_cell) != 11:
        raise IntakeError("eleven_distinct_cells_required")
    pairs = []
    for (latitude, longitude), first in sorted(by_cell.items()):
        right = by_cell.get((latitude, longitude + 1))
        top = by_cell.get((latitude + 1, longitude))
        if right is not None:
            pairs.append((first, "right", right, "left", f"E{longitude + 1}-N{latitude}"))
        if top is not None:
            pairs.append((first, "top", top, "bottom", f"N{latitude + 1}-E{longitude}"))
    if len(pairs) != 15:
        raise IntakeError("touching_seam_count_drift")
    return pairs


def validate_derivatives(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for item in items:
        source = controlled_path(item["source_relative_path"])
        output = controlled_path(item["output_relative_path"])
        receipt_path = ROOT / "records" / "processing" / f"{item['source_id'].lower()}-proj25-conversion-001-terminal.json"
        if not source.is_file() or not output.is_file() or not receipt_path.is_file():
            raise IntakeError("conversion_source_output_or_receipt_missing")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            receipt.get("status") != "pass_converted_verified_promoted"
            or receipt.get("source_id") != item["source_id"]
            or receipt.get("source_immutable") is not True
            or receipt.get("source_before", {}).get("sha256") != item["source_sha256"]
            or receipt.get("source_after") != receipt.get("source_before")
            or sha256_file(source) != item["source_sha256"]
            or sha256_file(output) != receipt.get("promoted", {}).get("sha256")
            or receipt.get("verification", {}).get("source_valid_pixel_count") != 12960000
            or receipt.get("verification", {}).get("nodata_mismatch_count") != 0
            or receipt.get("verification", {}).get("approved_aoi_nonfinite_count") != 0
        ):
            raise IntakeError("conversion_derivative_identity_or_validity_drift")
        results.append({
            "source_id": item["source_id"],
            "cell": list(cell_for(item)),
            "source_sha256": item["source_sha256"],
            "ellipsoidal_sha256": receipt["promoted"]["sha256"],
            "output_size_bytes": receipt["promoted"]["size_bytes"],
            "terminal_receipt_sha256": sha256_file(receipt_path),
        })
    return results


def measure_seams(items: list[dict[str, Any]], *, edge_reader=correction_edge) -> list[dict[str, Any]]:
    import numpy as np  # type: ignore

    results = []
    for first, first_edge, second, second_edge, seam_id in adjacent_pairs(items):
        first_delta = edge_reader(controlled_path(first["source_relative_path"]), controlled_path(first["output_relative_path"]), first_edge)
        second_delta = edge_reader(controlled_path(second["source_relative_path"]), controlled_path(second["output_relative_path"]), second_edge)
        finite = np.isfinite(first_delta) & np.isfinite(second_delta)
        if first_delta.size != 3600 or second_delta.size != 3600 or int(finite.sum()) != 3600:
            raise IntakeError("seam_correction_sample_incomplete")
        residual = np.abs(first_delta[finite] - second_delta[finite])
        results.append({
            "seam_id": seam_id,
            "first_source_id": first["source_id"],
            "second_source_id": second["source_id"],
            "sample_count": int(residual.size),
            "correction_discontinuity_abs_median_m": float(np.median(residual)),
            "correction_discontinuity_abs_p99_m": float(np.percentile(residual, 99)),
            "correction_discontinuity_abs_max_m": float(np.max(residual)),
        })
    return results


def reconcile() -> dict[str, Any]:
    if OUTPUT.exists():
        raise IntakeError("conversion_reconciliation_already_written")
    batch = json.loads(BATCH_REF.read_text(encoding="utf-8"))
    if batch.get("status") != "pass_seven_fixed_order_conversions_verified" or len(batch.get("attempted", [])) != 7:
        raise IntakeError("seven_conversion_batch_not_passing")
    old = json.loads(OLD_CONTRACT_REF.read_text(encoding="utf-8"))["dem_sources_in_exact_order"]
    new = conversion_items(require_outputs_absent=False)
    items = old + new
    if len(old) != 4 or len(new) != 7:
        raise IntakeError("eleven_dem_source_count_drift")
    identities = validate_derivatives(items)
    seams = measure_seams(items)
    return {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-EVENT-AREA-PAIR-001-DEM-CONVERSION-RECONCILIATION",
        "checked_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pass_eleven_exact_derivatives_seams_measured_not_yet_reviewed",
        "derivatives": identities,
        "seams": seams,
        "assertions": {
            "original_four_derivatives_read_only": True,
            "new_conversion_attempts": 7,
            "automatic_retries": 0,
            "source_overwrites": 0,
            "mosaic_attempts_started": 0,
            "actual_sar_extent_or_valid_elevation_proven": False,
            "radar_processing_started": False,
            "baseline_or_change_analysis_released": False,
        },
    }


def main() -> int:
    try:
        result = reconcile()
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({"status": result["status"], "derivative_count": len(result["derivatives"]), "seam_count": len(result["seams"]), "maximum_correction_seam_m": max(item["correction_discontinuity_abs_max_m"] for item in result["seams"])}))
        return 0
    except IntakeError as exc:
        print(json.dumps({"status": "stop_before_mosaic", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
