#!/usr/bin/env python3
"""Derive non-authorizing intake and verification controls for exact S1D orbit files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REF = "records/source-gates/m2-orbit-candidate-manifest.json"
PROPOSAL_REF = "contracts/milestone-002-orbit-amendment-proposal.json"
INTAKE_REF = "contracts/m2-orbit-intake-candidate.json"
VERIFICATION_REF = "contracts/m2-orbit-offline-verification-candidate.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(relative: str) -> str:
    return sha256_bytes((ROOT / relative).read_bytes())


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def build_intake() -> dict[str, Any]:
    manifest = load(MANIFEST_REF)
    proposal = load(PROPOSAL_REF)
    return {
        "contract_version": "1.0",
        "intake_id": "nepal-m2-orbit-intake-001",
        "status": "candidate_not_active",
        "created_at": manifest["generated_at_utc"],
        "collision_policy": "fail",
        "promotion_mode": "atomic-no-replace",
        "secret_policy": "references-only",
        "custody_root": "nepal-2026-before-after-map-data/custody/orbits/s1d/resorb",
        "staging_root": "nepal-2026-before-after-map-data/.intake-staging/nepal-m2-orbit-intake-001",
        "assets": [
            {
                "asset_id": record["source_id"].lower(),
                "source": {
                    "kind": "https",
                    "uri": record["download_url"],
                    "authorization_ref": PROPOSAL_REF,
                    "terms_ref": manifest["rights"]["terms_url"],
                    "credential_reference": "existing owner-controlled CDSE bearer token supplied only through the live secret-safe session after exact approval",
                },
                "destination_relative_path": f"{record['source_id'].lower()}/{record['exact_product_name']}",
                "staging_relative_path": f"{record['source_id'].lower()}/{record['exact_product_name']}.part",
                "expected": {
                    "sha256": None,
                    "size_bytes": record["content_length_bytes"],
                    "provider_checksums": record["provider_checksums"],
                },
                "observed": {
                    "staged_sha256": None,
                    "staged_size_bytes": None,
                    "promoted_sha256": None,
                    "promoted_size_bytes": None,
                },
                "state": "not_authorized",
                "attempts": [],
                "failure": None,
                "superseded_by": None,
                "extensions": {
                    "source_id": record["source_id"],
                    "group_id": record["group_id"],
                    "sentinel_source_ids": record["sentinel_source_ids"],
                    "provider_product_id": record["provider_product_id"],
                    "exact_product_name": record["exact_product_name"],
                    "orbit_type": record["orbit_type"],
                    "validity_start_utc": record["validity_start_utc"],
                    "validity_end_utc": record["validity_end_utc"],
                    "minimum_scene_margin_seconds": record["minimum_scene_margin_seconds"],
                    "eviction_date_utc": record["eviction_date_utc"],
                },
            }
            for record in manifest["records"]
        ],
        "extensions": {
            "manifest_ref": MANIFEST_REF,
            "manifest_sha256": sha256_file(MANIFEST_REF),
            "proposal_ref": PROPOSAL_REF,
            "proposal_sha256": sha256_file(PROPOSAL_REF),
            "parent_approval_ref": proposal["parent_approval_ref"],
            "parent_approval_sha256": proposal["parent_approval_sha256"],
            "scope_authority": "not_granted",
            "allowed_download_hosts": manifest["distribution_route"]["allowed_hosts"],
            "resume_policy": "disabled_until_range_support_and_unchanged_remote_identity_are verified",
            "payload_bytes_transferred": 0,
            "this_contract_creates_authority": False,
        },
    }


def build_verification(intake_sha256: str) -> dict[str, Any]:
    manifest = load(MANIFEST_REF)
    return {
        "schema_version": "1.0",
        "contract_id": "NEPAL-M2-ORBIT-OFFLINE-VERIFICATION-001",
        "status": "candidate_not_active",
        "created_at_utc": manifest["generated_at_utc"],
        "authority": {
            "mode": "not_granted",
            "authority_ref": PROPOSAL_REF,
            "this_contract_creates_authority": False,
        },
        "bindings": {
            "candidate_manifest_ref": MANIFEST_REF,
            "candidate_manifest_sha256": sha256_file(MANIFEST_REF),
            "candidate_intake_ref": INTAKE_REF,
            "candidate_intake_sha256": intake_sha256,
            "radar_contract_ref": "config/qa/radar-baseline-processing-contract.json",
            "radar_contract_sha256": sha256_file("config/qa/radar-baseline-processing-contract.json"),
        },
        "asset_requirements": [
            {
                "source_id": record["source_id"],
                "provider_product_id": record["provider_product_id"],
                "exact_product_name": record["exact_product_name"],
                "orbit_type": "AUX_RESORB",
                "sentinel_source_ids": record["sentinel_source_ids"],
                "scene_start_utc": record["scene_start_utc"],
                "scene_end_utc": record["scene_end_utc"],
                "expected_size_bytes": record["content_length_bytes"],
                "expected_provider_checksums": record["provider_checksums"],
                "expected_validity_start_utc": record["validity_start_utc"],
                "expected_validity_end_utc": record["validity_end_utc"],
                "minimum_required_scene_margin_seconds": record["minimum_scene_margin_seconds"],
            }
            for record in manifest["records"]
        ],
        "verification_sequence": [
            "recompute and compare exact byte length",
            "verify provider MD5 and BLAKE3 values",
            "compute and retain local SHA-256",
            "parse the EOF as XML without network access or external entities",
            "verify mission S1D, file type AUX_RESORB, and exact validity interval",
            "verify the OSV list is nonempty, ordered by UTC, unique, and spans the declared validity interval",
            "verify every position and velocity component is finite and has the declared physical unit",
            "verify the complete bound Sentinel acquisition window lies within the EOF validity interval with the required temporal margins",
            "promote only after every check passes and record a no-replace custody receipt",
        ],
        "application_boundary": {
            "arcgis_tool": "ApplyOrbitCorrection",
            "input_orbit_file_mode": "explicit exact file path",
            "may_apply_only_after_verified_sentinel_custody": True,
            "may_apply_only_to_bound_sentinel_source_ids": True,
            "preserve_original_embedded_predicted_metadata": True,
            "corrected_metadata_output": "new versioned non-Git attempt",
            "overwrite_safe_source": False,
            "radar_pixel_processing_authorized_by_this_contract": False,
        },
        "dispositions": ["invalid", "fail", "defer", "pass_orbit_input_only"],
        "stop_conditions": [
            "identity, length, checksum, XML, mission, file type, validity, OSV ordering, finite-value, unit, or scene-binding mismatch",
            "any source or destination path escapes the exact external custody roots",
            "a collision, symlink, reparse point, overwrite, or ambiguous prior attempt exists",
            "the matching Sentinel source has not passed exact custody and offline container verification",
            "ArcGIS selects or downloads a different orbit file instead of the explicit verified path",
        ],
        "claim_boundary": {
            "passing_verification_establishes": "exact orbit-input identity and structural fitness only",
            "does_not_establish": [
                "precise-orbit equivalence",
                "geolocation or registration accuracy",
                "vertical-datum fitness",
                "radar pixel fitness",
                "baseline quality",
                "event change",
                "scientific interpretation or attribution",
            ],
        },
    }


def validate(intake: dict[str, Any], verification: dict[str, Any]) -> list[str]:
    errors = []
    assets = intake.get("assets", [])
    requirements = verification.get("asset_requirements", [])
    expected_sources = {f"M2-ORB-{index:03d}" for index in range(1, 5)}
    if intake.get("status") != "candidate_not_active":
        errors.append("intake must remain candidate_not_active")
    if intake.get("secret_policy") != "references-only":
        errors.append("intake secret policy differs")
    if {asset["extensions"]["source_id"] for asset in assets} != expected_sources:
        errors.append("intake source boundary differs")
    if {item["source_id"] for item in requirements} != expected_sources:
        errors.append("verification source boundary differs")
    if any(asset.get("state") != "not_authorized" for asset in assets):
        errors.append("candidate intake contains an authorized asset")
    if any(asset["observed"]["promoted_sha256"] is not None for asset in assets):
        errors.append("candidate intake invents promoted bytes")
    if intake.get("extensions", {}).get("this_contract_creates_authority") is not False:
        errors.append("intake creates authority")
    if verification.get("authority", {}).get("this_contract_creates_authority") is not False:
        errors.append("verification creates authority")
    if verification.get("application_boundary", {}).get("overwrite_safe_source") is not False:
        errors.append("verification permits SAFE overwrite")
    if verification.get("application_boundary", {}).get("radar_pixel_processing_authorized_by_this_contract") is not False:
        errors.append("verification authorizes radar processing")
    return errors


def write_new(relative: str, value: object) -> str:
    path = ROOT / relative
    payload = canonical_bytes(value)
    if path.exists():
        raise SystemExit(f"REFUSED: output already exists: {relative}")
    path.write_bytes(payload)
    return sha256_bytes(payload)


def main() -> None:
    intake = build_intake()
    intake_payload = canonical_bytes(intake)
    verification = build_verification(sha256_bytes(intake_payload))
    errors = validate(intake, verification)
    if errors:
        raise SystemExit("INVALID: " + "; ".join(errors))
    intake_sha = write_new(INTAKE_REF, intake)
    verification_sha = write_new(VERIFICATION_REF, verification)
    print(
        json.dumps(
            {
                "status": "prepared_non_authorizing_controls",
                "asset_count": len(intake["assets"]),
                "intake_sha256": intake_sha,
                "verification_sha256": verification_sha,
                "payload_bytes_transferred": 0,
                "authority_created": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
