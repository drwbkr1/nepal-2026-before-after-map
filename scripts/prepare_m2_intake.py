#!/usr/bin/env python3
"""Build and verify a static, non-authorizing M2 controlled-intake packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit


DOWNLOAD_BASE = "https://download.dataspace.copernicus.eu/odata/v1/Products"
TERMS_URL = "https://dataspace.copernicus.eu/terms-and-conditions"
INTAKE_ID = "nepal-m2-intake-001"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_relative(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def timestamp_is_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").utcoffset() is not None
    except ValueError:
        return False


def build_contract(
    plan: dict[str, Any],
    proposal_sha256: str,
    review_bundle_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    data_root_name = PureWindowsPath(plan["custody"]["planned_external_root"]).name
    custody_root = f"{data_root_name}/custody"
    staging_root = f"{data_root_name}/.intake-staging/{INTAKE_ID}"
    assets = []
    for record in plan["records"]:
        source_id = record["source_id"]
        provider_id = record["provider_product_id"]
        archive_name = f'{record["exact_product_id"]}.zip'
        assets.append(
            {
                "asset_id": source_id.casefold(),
                "source": {
                    "kind": "https",
                    "uri": f"{DOWNLOAD_BASE}({provider_id})/$value",
                    "authorization_ref": "pending:M2-ACTIVATE:reviews/m2-activation/review-contract.json",
                    "terms_ref": TERMS_URL,
                    "transport_exception_ref": None,
                },
                "destination_relative_path": f"products/{source_id.casefold()}/{archive_name}",
                "staging_relative_path": f"{source_id.casefold()}/{archive_name}.part",
                "expected": {
                    "sha256": None,
                    "size_bytes": None,
                    "unavailable_reason": "CDSE catalog metadata records content length plus MD5 and BLAKE3, not an upstream SHA-256 or an authenticated transfer length. Capture transfer identity after activation and compute local SHA-256 before promotion.",
                },
                "observed": {
                    "staged_sha256": None,
                    "staged_size_bytes": None,
                    "promoted_sha256": None,
                    "promoted_size_bytes": None,
                },
                "state": "planned",
                "attempts": [],
                "failure": None,
                "superseded_by": None,
                "extensions": {
                    "source_id": source_id,
                    "exact_product_id": record["exact_product_id"],
                    "provider_product_id": provider_id,
                    "catalog_content_length_bytes": record["catalog_content_length_bytes"],
                    "provider_checksums": record["provider_checksums"],
                    "event_role": record["event_role"],
                    "sensor_route": record["sensor_route"],
                },
            }
        )
    return {
        "contract_version": "1.0",
        "intake_id": INTAKE_ID,
        "created_at": created_at,
        "collision_policy": "fail",
        "promotion_mode": "atomic-no-replace",
        "secret_policy": "references-only",
        "custody_root": custody_root,
        "staging_root": staging_root,
        "assets": assets,
        "extensions": {
            "status": "candidate_static_control_not_authorized",
            "project_root_basis": "parent_of_repository",
            "source_plan_ref": "records/acquisition-plan.json",
            "source_plan_sha256": sha256_bytes(canonical_bytes(plan)),
            "m2_proposal_ref": "contracts/milestone-002-proposal.json",
            "m2_proposal_sha256": proposal_sha256,
            "activation_review_bundle_ref": "reviews/m2-activation/review-bundle.json",
            "activation_review_bundle_sha256": review_bundle_sha256,
            "authority_status": "not_granted_pending_exact_M2_ACTIVATE_decision",
            "resume_policy": "disabled_until_range_support_and_unchanged_strong_remote_identity_are_verified",
            "download_route_reference": "https://documentation.dataspace.copernicus.eu/APIs/OData.html#product-download",
            "download_route_checked_at_utc": created_at,
            "static_only_no_network_or_external_filesystem_mutation": True,
        },
    }


def validate_packet(
    plan: dict[str, Any],
    proposal: dict[str, Any],
    review_bundle: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    plan_sha = sha256_bytes(canonical_bytes(plan))
    proposal_sha = sha256_bytes(canonical_bytes(proposal))
    bundle_sha = sha256_bytes(canonical_bytes(review_bundle))
    if plan.get("status") != "candidate_for_owner_review":
        errors.append("acquisition plan must remain candidate_for_owner_review")
    if proposal.get("status") != "proposed" or proposal.get("authority", {}).get("mode") != "not_granted":
        errors.append("M2 proposal must remain proposed with authority not_granted")
    if proposal.get("authority", {}).get("candidate_plan_sha256") != plan_sha:
        errors.append("M2 proposal does not bind the exact acquisition plan")
    if review_bundle.get("candidate_identity") != f"ACQUISITION-PLAN-SHA256:{plan_sha}":
        errors.append("M2 review bundle does not bind the exact acquisition plan")
    if contract.get("collision_policy") != "fail":
        errors.append("collision policy must be fail")
    if contract.get("promotion_mode") != "atomic-no-replace":
        errors.append("promotion mode must be atomic-no-replace")
    if contract.get("secret_policy") != "references-only":
        errors.append("secret policy must be references-only")
    if not timestamp_is_utc(contract.get("created_at")):
        errors.append("contract created_at must be an RFC 3339 UTC timestamp")
    for key in ("custody_root", "staging_root"):
        if not safe_relative(str(contract.get(key, ""))):
            errors.append(f"{key} must be a safe forward-slash relative path")
    if contract.get("custody_root", "").casefold().startswith("nepal-2026-before-after-map/"):
        errors.append("custody root must not resolve inside the Git repository")
    expected = build_contract(plan, proposal_sha, bundle_sha, contract.get("created_at", ""))
    if contract != expected:
        errors.append("intake contract differs from the deterministic plan-derived contract")
    assets = contract.get("assets", [])
    if len(assets) != 8:
        errors.append("intake contract must contain exactly eight assets")
    destinations: set[str] = set()
    staging_paths: set[str] = set()
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if asset.get("state") != "planned" or asset.get("attempts") != []:
            errors.append(f"{prefix} must remain planned with no attempts")
        for key, seen in (("destination_relative_path", destinations), ("staging_relative_path", staging_paths)):
            value = str(asset.get(key, ""))
            if not safe_relative(value):
                errors.append(f"{prefix}.{key} is unsafe")
            folded = value.casefold()
            if folded in seen:
                errors.append(f"{prefix}.{key} collides case-insensitively")
            seen.add(folded)
        source = asset.get("source", {})
        uri = str(source.get("uri", ""))
        parsed = urlsplit(uri)
        if parsed.scheme != "https" or parsed.netloc != "download.dataspace.copernicus.eu":
            errors.append(f"{prefix}.source.uri must use the approved CDSE HTTPS host")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            errors.append(f"{prefix}.source.uri contains unstable or secret-bearing components")
        provider_id = asset.get("extensions", {}).get("provider_product_id")
        if not isinstance(provider_id, str) or UUID_RE.fullmatch(provider_id) is None:
            errors.append(f"{prefix} has an invalid provider product UUID")
        elif uri != f"{DOWNLOAD_BASE}({provider_id})/$value":
            errors.append(f"{prefix}.source.uri does not bind its provider UUID")
    return sorted(set(errors))


def build_dry_run(
    plan: dict[str, Any],
    proposal: dict[str, Any],
    review_bundle: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    plan_sha = sha256_bytes(canonical_bytes(plan))
    proposal_sha = sha256_bytes(canonical_bytes(proposal))
    bundle_sha = sha256_bytes(canonical_bytes(review_bundle))
    contract_sha = sha256_bytes(canonical_bytes(contract))
    return {
        "schema_version": "1.0",
        "dry_run_id": "NEPAL-M2-INTAKE-STATIC-DRY-RUN-001",
        "status": "pass_static_only_no_authority",
        "generated_at_utc": contract["created_at"],
        "inputs": {
            "acquisition_plan_sha256": plan_sha,
            "m2_proposal_sha256": proposal_sha,
            "activation_review_bundle_sha256": bundle_sha,
            "intake_contract_sha256": contract_sha,
        },
        "authority": {
            "m2_status": proposal["status"],
            "mode": proposal["authority"]["mode"],
            "acquisition_authorized": False,
            "external_directory_creation_authorized": False,
            "network_or_authentication_performed": False,
        },
        "path_model": {
            "project_root_basis": "parent_of_repository",
            "custody_root": contract["custody_root"],
            "staging_root": contract["staging_root"],
            "roots_outside_one_another": True,
            "roots_outside_git_repository": True,
            "filesystem_probe_performed": False,
            "directories_created": False,
        },
        "selection": plan["selection"],
        "assets": [
            {
                "asset_id": asset["asset_id"],
                "source_id": asset["extensions"]["source_id"],
                "provider_product_id": asset["extensions"]["provider_product_id"],
                "source_uri": asset["source"]["uri"],
                "staging_relative_path": asset["staging_relative_path"],
                "destination_relative_path": asset["destination_relative_path"],
                "state": asset["state"],
                "network_request": "not_performed",
                "filesystem_mutation": "not_performed",
            }
            for asset in contract["assets"]
        ],
        "checks": {
            "exact_plan_binding": "pass",
            "exact_eight_product_set": "pass",
            "https_download_routes": "pass",
            "no_secret_values": "pass",
            "collision_policy": "pass",
            "staging_separate_from_custody": "pass",
            "atomic_no_replace_promotion": "pass",
            "failed_and_superseded_attempt_retention": "required",
            "resume_disabled_without_range_and_identity_evidence": "pass",
        },
        "limitations": [
            "This is a static control derivation, not the M2 custody preflight required after activation.",
            "No account, authenticated session, external path, remote headers, transfer length, or payload bytes were accessed.",
            "Catalog content length and provider MD5/BLAKE3 values are retained as metadata but do not substitute for local SHA-256 and verified transfer identity.",
            "The existing M2 activation review bundle remains the only pending authority gate and is unchanged by this dry run.",
        ],
    }


def write_or_verify(path: Path, value: Any, verify_only: bool) -> None:
    expected = canonical_bytes(value)
    if verify_only:
        if not path.is_file() or path.read_bytes() != expected:
            raise SystemExit(f"VERIFY FAIL: {path} differs from deterministic output")
        return
    if path.exists() and path.read_bytes() != expected:
        raise SystemExit(f"REFUSED: {path} exists with different bytes")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("records/acquisition-plan.json"))
    parser.add_argument("--proposal", type=Path, default=Path("contracts/milestone-002-proposal.json"))
    parser.add_argument("--review-bundle", type=Path, default=Path("reviews/m2-activation/review-bundle.json"))
    parser.add_argument("--contract-output", type=Path, default=Path("contracts/m2-intake-candidate.json"))
    parser.add_argument("--dry-run-output", type=Path, default=Path("records/acquisition/m2-intake-static-dry-run.json"))
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if not timestamp_is_utc(args.created_at):
        raise SystemExit("--created-at must be an RFC 3339 UTC timestamp ending in Z")
    plan = load_json(args.plan)
    proposal = load_json(args.proposal)
    review_bundle = load_json(args.review_bundle)
    contract = build_contract(plan, sha256_file(args.proposal), sha256_file(args.review_bundle), args.created_at)
    errors = validate_packet(plan, proposal, review_bundle, contract)
    if errors:
        raise SystemExit("STATIC VALIDATION FAIL:\n- " + "\n- ".join(errors))
    dry_run = build_dry_run(plan, proposal, review_bundle, contract)
    write_or_verify(args.contract_output, contract, args.verify_only)
    write_or_verify(args.dry_run_output, dry_run, args.verify_only)
    print(json.dumps({
        "status": "verified" if args.verify_only else "prepared",
        "authority_created": False,
        "network_or_external_filesystem_mutation": False,
        "asset_count": len(contract["assets"]),
        "contract": str(args.contract_output),
        "contract_sha256": sha256_bytes(canonical_bytes(contract)),
        "dry_run": str(args.dry_run_output),
        "dry_run_sha256": sha256_bytes(canonical_bytes(dry_run)),
    }, indent=2))


if __name__ == "__main__":
    main()
