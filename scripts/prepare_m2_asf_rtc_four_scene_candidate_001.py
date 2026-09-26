#!/usr/bin/env python3
"""Validate a four-scene, power-scale HyP3 candidate against saved public metadata.

This is offline preparation only. It never authenticates or contacts HyP3.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "records" / "observations" / "m2-asf-rtc-four-scene-candidate-001-local.json"
SCHEMA = ROOT / "scratch" / "asf-rtc-api-schema-001" / "openapi.json"
CONTRACT = ROOT / "config" / "qa" / "m2-radar-pixel-orbit-application-001-contract.json"
CATALOG = (
    ROOT / "records" / "observations" / "m2-external-rtc-route-feasibility-001-local.json",
    ROOT / "records" / "observations" / "m2-asf-ascending-adjacent-001-local.json",
)
EVENT_FIRST_ORDER = ("M1-SRC-002", "M1-SRC-005", "M1-SRC-001", "M1-SRC-004")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise RuntimeError("append-only four-scene candidate already exists")
    spec = json.loads(SCHEMA.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    old_catalog, adjacent_catalog = (
        json.loads(path.read_text(encoding="utf-8")) for path in CATALOG
    )
    choices = spec["paths"]["/jobs"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["jobs"]["items"]["oneOf"]
    rtc = [choice for choice in choices if "RTC_GAMMA" in choice.get("properties", {}).get("job_type", {}).get("enum", [])]
    if len(rtc) != 1:
        raise RuntimeError("RTC_GAMMA schema ambiguous")
    fields = rtc[0]["properties"]["job_parameters"]["properties"]
    if "power" not in fields["scale"]["enum"]:
        raise RuntimeError("power-scale option absent from saved schema")
    contract_sources = {item["source_id"]: item for item in contract["sources"]}
    if len(set(EVENT_FIRST_ORDER)) != 4:
        raise RuntimeError("candidate source order contains duplicates")
    found_catalog = {
        row["scene_name"]
        for row in old_catalog["asf_exact_scene_rows"] + adjacent_catalog["rows"]
        if row["processing_level"] == "GRD_HD" and row["flight_direction"] == "ASCENDING"
    }
    jobs = []
    for source_id in EVENT_FIRST_ORDER:
        source = contract_sources[source_id]
        scene = source["exact_product_id"].removesuffix(".SAFE")
        if scene not in found_catalog:
            raise RuntimeError(f"ASF catalog lacks exact ascending GRD: {source_id}")
        alternatives = fields["granules"]["items"]["anyOf"]
        if not any(
            re.match(option["pattern"], scene) and len(scene) == option["minLength"]
            for option in alternatives
        ):
            raise RuntimeError(f"saved HyP3 schema does not fit: {source_id}")
        parameters = {
            "granules": [scene],
            "resolution": 10.0,
            "dem_name": "copernicus",
            "radiometry": "gamma0",
            "scale": "power",
            "speckle_filter": False,
            "dem_matching": False,
            "include_dem": True,
            "include_inc_map": True,
            "include_scattering_area": True,
            "include_rgb": False,
        }
        for name, value in parameters.items():
            field = fields[name]
            if "enum" in field and value not in field["enum"]:
                raise RuntimeError(f"schema enum mismatch: {name}")
            if field["type"] == "boolean" and not isinstance(value, bool):
                raise RuntimeError(f"schema type mismatch: {name}")
        jobs.append(
            {
                "source_id": source_id,
                "event_role": source["event_role"],
                "name": f"m2-rtc-002-{source_id.lower()}",
                "job_type": "RTC_GAMMA",
                "job_parameters": parameters,
            }
        )
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-ASF-RTC-FOUR-SCENE-CANDIDATE-001-LOCAL",
        "status": "offline_candidate_shape_checked_not_approved_or_submitted",
        "prepared_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bindings": [
            {"ref": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            for path in (SCHEMA, CONTRACT, *CATALOG)
        ],
        "candidate_purpose": "Preserve all four source IDs of the frozen ascending route while prioritizing the two event-AOI scenes; method and order require separate review.",
        "candidate_jobs": jobs,
        "estimated_total_basic_credits_at_documented_60_per_job": 240,
        "owner_balance_or_job_eligibility_verified": False,
        "relationship_to_prior_two_scene_db_candidate": "distinct_unapproved_alternative_not_a_replacement_of_immutable_observation",
        "limits": {
            "hyp3_server_validation_sent": False,
            "account_or_credential_used": False,
            "job_submitted": False,
            "credits_spent": False,
            "product_acquired": False,
            "project_pixels_read": False,
            "source_or_scientific_method_adopted": False,
            "baseline_or_change_analysis_run": False,
        },
    }
    with OUT.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(receipt, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("PASS: four-scene power-scale candidate checked offline; no HyP3 request")


if __name__ == "__main__":
    main()
