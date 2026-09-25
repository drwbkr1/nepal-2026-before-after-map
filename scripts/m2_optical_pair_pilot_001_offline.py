#!/usr/bin/env python3
"""Distinct offline materialization and header checks for the approved pair."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from inspect_optical_inputs_arcgis import describe_raster
from m2_materialization_core import MaterializationError, materialize_archive
from m2_optical_pair_pilot_001_core import PilotControlError, require_execution_release, sha256_file
from m2_optical_pair_pilot_001_transfer import DATA_ROOT, MATERIALIZATION_CONTRACT, now_utc, read_json, write_new_json
from optical_input_readiness_core import RASTER_ROLES, decide_header_readiness, select_required_members, validate_pair_grids
from optical_processing_core import parse_l2a_scaling_metadata, processing_baseline_from_product_id


ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = DATA_ROOT / "derived/m2-optical-pair-pilot-001"
HEADER_CONTRACT = ROOT / "config/qa/optical-input-readiness-contract.json"


def promoted_transfer(source: Mapping[str, Any]) -> dict[str, Any]:
    attempts = PILOT_ROOT / "transport" / source["source_id"].casefold()
    if not attempts.is_dir():
        raise PilotControlError("pilot_transfer_missing")
    terminals: list[dict[str, Any]] = []
    for path in sorted(attempts.iterdir()):
        if not path.is_dir() or not (path / "terminal.json").is_file():
            raise PilotControlError("pilot_transfer_indeterminate")
        terminals.append(read_json(path / "terminal.json"))
    if len(terminals) not in (1, 2) or terminals[-1].get("status") != "promoted_verified":
        raise PilotControlError("pilot_transfer_not_promoted_verified")
    if len(terminals) == 2 and terminals[0].get("status") != "transport_interrupted":
        raise PilotControlError("pilot_transfer_retry_history_invalid")
    terminal = terminals[-1]
    path = Path(terminal["destination"])
    expected = PILOT_ROOT / "custody" / source["source_id"].casefold() / (source["exact_product_name"] + ".zip")
    if path != expected or not path.is_file():
        raise PilotControlError("pilot_promoted_archive_path_drift")
    if path.stat().st_size != source["content_length_bytes"] or sha256_file(path) != terminal["archive_sha256"]:
        raise PilotControlError("pilot_promoted_archive_identity_drift")
    if terminal.get("provider_md5_verified") is not True or terminal.get("provider_blake3_verified") is not True:
        raise PilotControlError("pilot_provider_hash_verification_missing")
    return terminal


def materialize_one(source: Mapping[str, Any]) -> dict[str, Any]:
    require_execution_release(source["source_id"])
    transfer = promoted_transfer(source)
    output = PILOT_ROOT / "materialized" / source["source_id"].casefold() / "materialization-001"
    if output.exists():
        raise PilotControlError("pilot_materialization_attempt_consumed")
    archive = Path(transfer["destination"])
    controls = read_json(MATERIALIZATION_CONTRACT)["member_controls"]
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = materialize_archive(
            archive_path=archive,
            attempt_root=output,
            source_id=source["source_id"],
            exact_product_id=source["exact_product_name"],
            archive_sha256=transfer["archive_sha256"],
            controls=controls,
            started_at_utc=now_utc(),
        )
    except BaseException as exc:
        if output.is_dir():
            code = exc.code if isinstance(exc, MaterializationError) else "unexpected_materialization_failure"
            write_new_json(output / "failure.json", {
                "status": "invalid", "source_id": source["source_id"],
                "code": code, "exception_text_recorded": False, "automatic_retry": False,
            })
        raise
    return result


def inspect_materialized_one(source: Mapping[str, Any], arcpy: Any, header_contract: Mapping[str, Any]) -> dict[str, Any]:
    transfer = promoted_transfer(source)
    attempt = PILOT_ROOT / "materialized" / source["source_id"].casefold() / "materialization-001"
    complete = attempt / "completed.json"
    manifest_path = attempt / "materialization-manifest.json"
    safe_root = attempt / source["exact_product_name"]
    if not complete.is_file() or not manifest_path.is_file() or not safe_root.is_dir():
        raise PilotControlError("pilot_materialization_not_complete")
    marker = read_json(complete)
    manifest = read_json(manifest_path)
    if (
        marker.get("status") != "complete"
        or marker.get("manifest_sha256") != sha256_file(manifest_path)
        or manifest.get("archive_sha256") != transfer["archive_sha256"]
        or manifest.get("exact_product_id") != source["exact_product_name"]
        or manifest.get("source_id") != source["source_id"]
    ):
        raise PilotControlError("pilot_materialization_identity_drift")
    selected = select_required_members(manifest, dict(header_contract))
    if selected["status"] != "pass_inventory_only":
        return {"source_id": source["source_id"], "inventory": selected, "metadata_errors": selected["errors"], "descriptions": {}}
    paths: dict[str, Path] = {}
    for role, item in selected["members"].items():
        path = safe_root.joinpath(*PurePosixPath(item["relative_path"]).parts)
        if not path.is_file() or path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            raise PilotControlError("pilot_selected_member_identity_drift")
        paths[role] = path
    try:
        parsed = parse_l2a_scaling_metadata(paths["metadata_product"].read_text(encoding="utf-8"))
        metadata_errors = list(parsed["errors"])
    except (OSError, UnicodeError, ValueError) as exc:
        parsed = {}
        metadata_errors = [f"metadata_parse_failed_{type(exc).__name__}"]
    if parsed.get("processing_baseline") != "05.12" or processing_baseline_from_product_id(source["exact_product_name"]) != "05.12":
        metadata_errors.append("processing_baseline_drift")
    descriptions: dict[str, Any] = {}
    for role in sorted(RASTER_ROLES):
        try:
            descriptions[role] = describe_raster(arcpy, paths[role])
        except Exception as exc:
            metadata_errors.append(f"{role}_header_open_failed_{type(exc).__name__}")
    return {
        "source_id": source["source_id"], "inventory": selected,
        "metadata": parsed, "metadata_errors": metadata_errors,
        "descriptions": descriptions, "manifest_sha256": sha256_file(manifest_path),
    }


def inspect_pair_headers(sources: list[dict[str, Any]], arcpy: Any, output: Path) -> dict[str, Any]:
    require_execution_release()
    if len(sources) != 2 or [item["source_id"] for item in sources] != ["M2-OPT-001", "M2-OPT-002"]:
        raise PilotControlError("pilot_header_pair_order_drift")
    if output.exists():
        raise PilotControlError("pilot_header_attempt_consumed")
    contract = read_json(HEADER_CONTRACT)
    products = [inspect_materialized_one(source, arcpy, contract) for source in sources]
    grid_errors = validate_pair_grids(products[0]["descriptions"], products[1]["descriptions"], contract)
    decision = decide_header_readiness(
        {item["source_id"]: item["inventory"]["status"] for item in products},
        {item["source_id"]: item["metadata_errors"] for item in products},
        grid_errors,
    )
    receipt = {
        "schema_version": "1.0", "receipt_id": "NEPAL-M2-OPTICAL-PAIR-PILOT-001-HEADER",
        "status": decision["status"], "checked_at_utc": now_utc(),
        "pair": [item["source_id"] for item in sources],
        "products": {item["source_id"]: item for item in products},
        "decision": decision,
        "activity": {"pixel_values_examined": False, "network_requests": False, "authentication": False},
        "claim_boundary": {"baseline_established": False, "change_established": False, "scientific_admission": False},
    }
    write_new_json(output, receipt)
    return receipt
