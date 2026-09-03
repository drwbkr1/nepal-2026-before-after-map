#!/usr/bin/env python3
"""Validate the predeclared raster-pair plan against approved source records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_AOIS = {"AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_plan(plan: dict[str, Any], manifest: dict[str, Any], approval: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("schema_version") != "1.0" or plan.get("plan_id") != "NEPAL-PAIR-PLAN-001":
        errors.append("pair-plan identity differs")
    if plan.get("status") != "predeclared_candidate_routes_no_pixel_or_acquisition_authority":
        errors.append("pair-plan status differs")
    semantics = plan.get("decision_semantics", {})
    required_false = ("synthetic_inputs_create_source_association", "qa_pass_creates_scientific_admission")
    required_true = ("evaluate_routes_independently", "preserve_failed_and_inconclusive_routes", "cross_route_synthesis_requires_later_review")
    if any(semantics.get(key) is not False for key in required_false) or any(semantics.get(key) is not True for key in required_true):
        errors.append("pair-plan decision semantics differ")
    authority = plan.get("authority", {})
    if authority.get("mode") != "not_granted" or authority.get("authorized_actions") != []:
        errors.append("pair plan must not create acquisition or processing authority")

    records = {record["source_id"]: record for record in manifest.get("records", [])}
    accepted = {
        source_id
        for source_id, record in records.items()
        if record.get("proposed_disposition", {}).get("disposition") == "accept_for_controlled_acquisition_planning"
    }
    if approval.get("status") != "approved" or approval.get("reviewed_manifest_sha256") != plan.get("source_bindings", {}).get("source_manifest_sha256"):
        errors.append("source-manifest approval does not match the pair plan")

    pairs = plan.get("pairs", [])
    if not isinstance(pairs, list) or len(pairs) != 3:
        errors.append("pair plan must contain exactly three independent routes")
        pairs = []
    pair_ids = [pair.get("pair_id") for pair in pairs]
    if len(set(pair_ids)) != len(pair_ids) or any(not item for item in pair_ids):
        errors.append("pair IDs must be present and unique")

    used_sources: list[str] = []
    for pair in pairs:
        before_ids = pair.get("before_source_ids")
        after_ids = pair.get("after_source_ids")
        if not isinstance(before_ids, list) or not before_ids or not isinstance(after_ids, list) or not after_ids:
            errors.append(f"{pair.get('pair_id')} lacks before or after sources")
            continue
        source_ids = [*before_ids, *after_ids]
        used_sources.extend(source_ids)
        if any(source_id not in accepted for source_id in source_ids):
            errors.append(f"{pair.get('pair_id')} uses a source outside the approved acquisition-planning set")
            continue
        route = pair.get("sensor_route")
        expected_profile = {"radar": "radar_mask", "optical": "optical_scl"}.get(route)
        if pair.get("mask_profile") != expected_profile:
            errors.append(f"{pair.get('pair_id')} mask profile does not match its sensor route")
        if any(records[source_id].get("event_role") != "before" for source_id in before_ids):
            errors.append(f"{pair.get('pair_id')} before source role differs")
        if any(records[source_id].get("event_role") != "after" for source_id in after_ids):
            errors.append(f"{pair.get('pair_id')} after source role differs")
        if any(records[source_id].get("sensor_route") != route for source_id in source_ids):
            errors.append(f"{pair.get('pair_id')} mixes sensor routes")

        orbits = [records[source_id].get("orbit_or_tile", {}) for source_id in source_ids]
        comparison = pair.get("comparability", {})
        for key in ("relative_orbit_number", "operational_mode"):
            if any(item.get(key) != comparison.get(key) for item in orbits):
                errors.append(f"{pair.get('pair_id')} {key} differs from source metadata")
        route_key = "orbit_direction" if route == "radar" else "tile_id"
        if any(item.get(route_key) != comparison.get(route_key) for item in orbits):
            errors.append(f"{pair.get('pair_id')} {route_key} differs from source metadata")
        expected_cell = (
            contract.get("grid_compatibility", {}).get("radar_candidate_cell_size_m")
            if route == "radar"
            else contract.get("grid_compatibility", {}).get("optical_multispectral_change_cell_size_m")
        )
        if pair.get("target_cell_size_m") != expected_cell:
            errors.append(f"{pair.get('pair_id')} target cell size differs from the pixel contract")
        if set(pair.get("approved_aoi_scope", [])) != EXPECTED_AOIS:
            errors.append(f"{pair.get('pair_id')} AOI scope differs")
        if pair.get("pixel_status") != "not_evaluated_no_pixels":
            errors.append(f"{pair.get('pair_id')} invents a pixel result")

    if set(used_sources) != accepted or len(used_sources) != len(set(used_sources)):
        errors.append("approved acquisition-planning sources must appear exactly once across pair routes")
    if not str(plan.get("claim_boundary", "")).startswith("This plan fixes candidate comparison routes"):
        errors.append("pair-plan claim boundary is missing")
    return errors


def load_and_validate(plan_path: Path, repo: Path) -> dict[str, Any]:
    plan = load_json(plan_path)
    bindings = plan.get("source_bindings", {})
    paths = {
        "source_manifest": repo / bindings.get("source_manifest", ""),
        "source_manifest_approval": repo / bindings.get("source_manifest_approval", ""),
        "pixel_readiness_contract": repo / bindings.get("pixel_readiness_contract", ""),
    }
    errors: list[str] = []
    for key, path in paths.items():
        if not path.is_file():
            errors.append(f"missing bound {key}")
        elif bindings.get(f"{key}_sha256") != sha256(path):
            errors.append(f"bound {key} hash differs")
    if errors:
        raise ValueError("invalid pair plan: " + "; ".join(errors))
    errors.extend(validate_plan(plan, load_json(paths["source_manifest"]), load_json(paths["source_manifest_approval"]), load_json(paths["pixel_readiness_contract"])))
    if errors:
        raise ValueError("invalid pair plan: " + "; ".join(errors))
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("config/qa/candidate-pair-plan.json"))
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    plan_path = (repo / args.plan).resolve()
    plan = load_and_validate(plan_path, repo)
    print(json.dumps({
        "status": "valid",
        "plan_id": plan["plan_id"],
        "pair_count": len(plan["pairs"]),
        "source_count": sum(len(pair["before_source_ids"]) + len(pair["after_source_ids"]) for pair in plan["pairs"]),
        "authority_created": False,
    }, indent=2))


if __name__ == "__main__":
    main()
