#!/usr/bin/env python3
"""Prepare and run fail-closed, offline verification for the approved M2 products."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import BadZipFile, ZipFile


VERIFICATION_ID = "NEPAL-M2-OFFLINE-VERIFICATION-001"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

S1_REQUIREMENTS = [
    {"pattern": "manifest.safe", "minimum_count": 1, "nonempty": True},
    {"pattern": "annotation/*-vv-*.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "annotation/*-vh-*.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "annotation/calibration/calibration-*-vv-*.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "annotation/calibration/calibration-*-vh-*.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "annotation/calibration/noise-*-vv-*.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "annotation/calibration/noise-*-vh-*.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "measurement/*-vv-*.tiff", "minimum_count": 1, "nonempty": True},
    {"pattern": "measurement/*-vh-*.tiff", "minimum_count": 1, "nonempty": True},
]

S2_REQUIREMENTS = [
    {"pattern": "manifest.safe", "minimum_count": 1, "nonempty": True},
    {"pattern": "MTD_MSIL2A.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "DATASTRIP/*/MTD_DS.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/MTD_TL.xml", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R10m/*_B02_10m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R10m/*_B03_10m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R10m/*_B04_10m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R10m/*_B08_10m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R20m/*_B05_20m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R20m/*_B06_20m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R20m/*_B07_20m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R20m/*_B8A_20m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R20m/*_B11_20m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R20m/*_B12_20m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/IMG_DATA/R20m/*_SCL_20m.jp2", "minimum_count": 1, "nonempty": True},
    {"pattern": "GRANULE/*/QI_DATA/*", "minimum_count": 1, "nonempty": True},
]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    # MD5 is used only to compare with the provider-declared value; SHA-256 is the local identity.
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").utcoffset() is not None
    except ValueError:
        return False


def safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts)


def provider_checksum(record: dict[str, Any], algorithm: str) -> str:
    matches = [
        item["Value"].casefold()
        for item in record["provider_checksums"]
        if item["Algorithm"].casefold() == algorithm.casefold()
    ]
    if len(matches) != 1:
        raise ValueError(f"{record['source_id']} must have one provider {algorithm} checksum")
    return matches[0]


def structural_profile(sensor_route: str) -> tuple[str, list[dict[str, Any]]]:
    if sensor_route == "radar":
        return "sentinel1_iw_grd_dual_vv_vh", S1_REQUIREMENTS
    if sensor_route == "optical":
        return "sentinel2_l2a_optical_change_core", S2_REQUIREMENTS
    raise ValueError(f"unsupported sensor route: {sensor_route}")


def build_contract(
    plan: dict[str, Any],
    intake: dict[str, Any],
    plan_sha256: str,
    intake_sha256: str,
    manifest_approval_sha256: str,
    review_bundle_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    intake_by_source = {
        item["extensions"]["source_id"]: item
        for item in intake["assets"]
    }
    assets = []
    for record in plan["records"]:
        source_id = record["source_id"]
        intake_asset = intake_by_source[source_id]
        profile_name, requirements = structural_profile(record["sensor_route"])
        assets.append({
            "source_id": source_id,
            "asset_id": intake_asset["asset_id"],
            "exact_product_id": record["exact_product_id"],
            "provider_product_id": record["provider_product_id"],
            "sensor_route": record["sensor_route"],
            "event_role": record["event_role"],
            "archive_relative_path": intake_asset["destination_relative_path"],
            "catalog_content_length_bytes": record["catalog_content_length_bytes"],
            "provider_md5": provider_checksum(record, "MD5"),
            "provider_blake3_metadata": provider_checksum(record, "BLAKE3"),
            "structural_profile": profile_name,
            "required_members": requirements,
        })
    return {
        "contract_version": "1.0",
        "verification_id": VERIFICATION_ID,
        "created_at": created_at,
        "status": "candidate_static_control_not_authorized",
        "inputs": {
            "acquisition_plan_ref": "records/acquisition-plan.json",
            "acquisition_plan_sha256": plan_sha256,
            "intake_contract_ref": "contracts/m2-intake-candidate.json",
            "intake_contract_sha256": intake_sha256,
            "manifest_approval_ref": "records/source-gates/source-manifest-approval.json",
            "manifest_approval_sha256": manifest_approval_sha256,
            "m2_review_bundle_ref": "reviews/m2-activation/review-bundle.json",
            "m2_review_bundle_sha256": review_bundle_sha256,
        },
        "authority": {
            "m2_activation_status": "not_granted",
            "network_access_authorized": False,
            "authentication_authorized": False,
            "custody_root_creation_authorized": False,
            "product_download_authorized": False,
            "this_contract_creates_authority": False,
        },
        "execution_boundary": {
            "custody_root_from_plan": plan["custody"]["planned_external_root"] + "\\custody",
            "custody_root_must_already_exist": True,
            "source_archives_are_read_only": True,
            "output_parent_must_already_exist": True,
            "overwrite_existing_receipt": False,
            "network_requests": "prohibited",
            "archive_extraction": "prohibited",
        },
        "archive_controls": {
            "required_format": "zip",
            "local_identity_algorithm": "SHA-256",
            "provider_comparison_algorithm": "MD5",
            "require_exact_catalog_size": True,
            "require_crc_test": True,
            "reject_encrypted_entries": True,
            "reject_symbolic_links": True,
            "reject_unsafe_or_duplicate_member_paths": True,
            "maximum_member_count": 100000,
            "maximum_single_uncompressed_bytes": 8589934592,
            "maximum_total_uncompressed_bytes_floor": 2147483648,
            "maximum_total_uncompressed_to_archive_ratio": 6.0,
        },
        "assets": assets,
        "post_container_gates": [
            "current access terms and intended-use rights",
            "raster readability and internal metadata identity",
            "AOI intersection and coverage fraction",
            "Sentinel-2 processing baseline, quantification value, BOA_ADD_OFFSET parsing, and reflectance scaling",
            "valid-pixel, nodata, cloud, cirrus, shadow, snow, saturation, and SCL inspection for optical data",
            "orbit, polarization, calibration, border-noise, layover, shadow, and terrain-correction fitness for radar data",
            "before/after grid, extent, resolution, and co-registration QA in EPSG:32645",
            "stable-reference behavior and quantitative registration residual",
            "human review of exclusions, uncertainty, baseline admission, and any scientific use",
        ],
        "source_references": [
            {"role": "sentinel_safe_format", "url": "https://sentiwiki.copernicus.eu/web/safe-format", "checked_at_utc": created_at},
            {"role": "sentinel1_product_structure", "url": "https://sentiwiki.copernicus.eu/web/s1-products", "checked_at_utc": created_at},
            {"role": "sentinel2_l2a_bands_and_scl", "url": "https://sentiwiki.copernicus.eu/web/s2-products", "checked_at_utc": created_at},
        ],
        "limitations": [
            "A container pass establishes exact archive identity, provider-MD5 agreement, ZIP integrity, and required member presence only.",
            "MD5 comparison is retained for provider consistency and does not replace the computed local SHA-256 identity.",
            "Member names and nonzero sizes do not establish readable rasters, valid pixels, AOI coverage, masks, registration, or scientific fitness.",
            "No scan may begin until M2 is activated and the exact external custody root already exists under that authority.",
        ],
    }


def build_readiness_input(source_manifest_sha256: str) -> dict[str, Any]:
    gate_specs = [
        (
            "source-and-terms", "source_and_terms",
            ["records/source-manifest.json", "records/source-gates/source-manifest-approval.json"],
            "Exact sources are approved for planning, but current access-time terms and intended-use rights have not been verified.",
            "After M2 activation, record the current provider terms and rights assessment without accepting changed terms automatically.",
        ),
        (
            "provenance-and-custody", "provenance_and_custody",
            ["records/acquisition-plan.json", "contracts/m2-intake-candidate.json"],
            "No full-product archive, transfer receipt, local SHA-256, or immutable custody chain exists.",
            "Acquire only the exact approved products under M2 authority and retain transfer, checksum, failure, and promotion evidence.",
        ),
        (
            "schema-and-quality", "schema_and_quality",
            ["contracts/m2-offline-verification-candidate.json"],
            "Archive integrity, SAFE structure, required bands or polarizations, and raster readability have not been tested on product bytes.",
            "Run the offline container verifier, then inspect every required raster and internal metadata identity.",
        ),
        (
            "coverage-and-balance", "coverage_and_balance",
            ["config/aoi/approved-study-areas.geojson", "records/source-manifest.json"],
            "Catalog footprints do not establish usable coverage of each approved AOI or balanced before/after evidence routes.",
            "Measure AOI intersection, valid-pixel fractions, and before/after optical and radar coverage after opening the rasters.",
        ),
        (
            "uncertainty-and-exclusions", "uncertainty_and_exclusions",
            ["config/arcgis/evidence-workspace-schema.json"],
            "The schema can retain exclusions and adverse states, but no product-level cloud, terrain, radar, nodata, or uncertainty evidence exists.",
            "Populate explicit exclusion and QA records without coercing unresolved pixels or products into accepted evidence.",
        ),
        (
            "temporal-and-pair-fitness", "leakage_and_split_fitness",
            ["records/acquisition-plan.json", "docs/DATA_AND_METHODS_PLAN.md"],
            "Product dates and roles are fixed, but orbit geometry, comparable grids, stable controls, and before/after pair fitness remain unverified.",
            "Evaluate optical and radar pairs independently and quantify registration on stable terrain before change analysis.",
        ),
        (
            "reproducibility", "reproducibility",
            ["scripts/prepare_m2_intake.py", "scripts/prepare_m2_verification.py"],
            "Static controls are reproducible, but no acquired product or analysis-ready derivative can yet be rebuilt from local custody.",
            "Bind acquired bytes, environment, processing parameters, intermediate hashes, and rerun evidence after M2 activation.",
        ),
        (
            "evaluation-design", "evaluation_design",
            ["docs/VALIDATION.md", "docs/ARCGIS_EVIDENCE_MODEL.md"],
            "Required QA families are documented, but scene-specific thresholds, stable-reference results, and acceptance criteria are not complete.",
            "Fix scene-specific QA thresholds before change classification and preserve failed or inconclusive routes.",
        ),
        (
            "human-review", "human_review",
            ["reviews/m2-activation/review-bundle.json", "docs/M2_CONTROLLED_ACQUISITION_REVIEW.md"],
            "The exact M2 acquisition proposal has not received a completed owner decision.",
            "Obtain and lock an exact M2 activation decision before authentication, custody creation, or download.",
        ),
    ]
    return {
        "audit_contract_version": "dataset-readiness-audit-v1",
        "template": False,
        "audit_id": "nepal-m2-product-readiness-001",
        "candidate_id": "nepal-m2-approved-product-set-001",
        "candidate_manifest_sha256": source_manifest_sha256,
        "required_gate_ids": [item[0] for item in gate_specs],
        "gates": [
            {
                "gate_id": gate_id,
                "category": category,
                "required": True,
                "status": "defer",
                "evidence_refs": evidence_refs,
                "finding": finding,
                "remediation": remediation,
            }
            for gate_id, category, evidence_refs, finding, remediation in gate_specs
        ],
        "count_checks": [
            {
                "check_id": "approved-product-count",
                "observed": 8,
                "operator": ">=",
                "threshold": 8,
                "on_failure": "defer",
            }
        ],
        "next_step_authority": {
            "mode": "not_granted",
            "authority_ref": "reviews/m2-activation/review-bundle.json",
            "authorized_actions": [],
        },
    }


def validate_candidate(
    plan: dict[str, Any],
    intake: dict[str, Any],
    contract: dict[str, Any],
    expected_contract: dict[str, Any],
    readiness_input: dict[str, Any],
    expected_readiness_input: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if plan.get("status") != "candidate_for_owner_review":
        errors.append("M2 acquisition plan status changed")
    if intake.get("extensions", {}).get("authority_status") != "not_granted_pending_exact_M2_ACTIVATE_decision":
        errors.append("M2 intake authority status changed")
    if contract != expected_contract:
        errors.append("offline verification contract differs from deterministic approved-plan derivation")
    if readiness_input != expected_readiness_input:
        errors.append("readiness audit input differs from deterministic deferred-state derivation")
    if contract.get("status") != "candidate_static_control_not_authorized":
        errors.append("offline verification contract must remain non-authorizing")
    authority = contract.get("authority", {})
    authority_flags = [
        value for key, value in authority.items()
        if key != "m2_activation_status"
    ]
    if authority.get("m2_activation_status") != "not_granted" or any(authority_flags):
        errors.append("offline verification contract authority flags must all remain false")
    assets = contract.get("assets", [])
    if len(assets) != 8:
        errors.append("offline verification contract must contain eight assets")
    if {item.get("source_id") for item in assets} != {item["source_id"] for item in plan["records"]}:
        errors.append("offline verification source set differs from the approved acquisition plan")
    for item in assets:
        if not safe_relative(item.get("archive_relative_path")):
            errors.append(f"unsafe archive path for {item.get('source_id')}")
        if not HEX64_RE.fullmatch(str(item.get("provider_blake3_metadata", ""))):
            errors.append(f"invalid provider BLAKE3 metadata for {item.get('source_id')}")
        if len(str(item.get("provider_md5", ""))) != 32:
            errors.append(f"invalid provider MD5 metadata for {item.get('source_id')}")
    if any(gate.get("status") != "defer" for gate in readiness_input.get("gates", [])):
        errors.append("pre-acquisition readiness gates must all remain deferred")
    if readiness_input.get("next_step_authority", {}).get("mode") != "not_granted":
        errors.append("readiness audit must not create next-step authority")
    return sorted(set(errors))


def _relative_members(infos: list[Any], product_id: str) -> tuple[list[tuple[Any, str]], list[str]]:
    errors: list[str] = []
    members: list[tuple[Any, str]] = []
    seen: set[str] = set()
    expected_root = product_id + "/"
    for info in infos:
        name = info.filename
        if "\\" in name:
            errors.append(f"unsafe backslash member path: {name}")
            continue
        path = PurePosixPath(name)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            errors.append(f"unsafe member path: {name}")
            continue
        folded = name.casefold()
        if folded in seen:
            errors.append(f"duplicate member path: {name}")
            continue
        seen.add(folded)
        if info.flag_bits & 0x1:
            errors.append(f"encrypted member is not allowed: {name}")
        mode = (info.external_attr >> 16) & 0o170000
        if mode == stat.S_IFLNK:
            errors.append(f"symbolic-link member is not allowed: {name}")
        if name == product_id or name == expected_root:
            continue
        if not name.startswith(expected_root):
            errors.append(f"member lies outside exact SAFE root: {name}")
            continue
        members.append((info, name[len(expected_root):]))
    return members, errors


def scan_archive(asset: dict[str, Any], archive_path: Path, controls: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_id": asset["source_id"],
        "archive_relative_path": asset["archive_relative_path"],
        "status": "defer",
        "local_size_bytes": None,
        "local_sha256": None,
        "local_md5": None,
        "member_count": None,
        "total_uncompressed_bytes": None,
        "checks": {},
        "errors": [],
        "pixel_usability_established": False,
        "eligible_for_post_container_qa": False,
    }
    if not archive_path.is_file():
        result["errors"].append("approved archive is not present at the exact custody path")
        return result

    local_size = archive_path.stat().st_size
    local_sha = sha256_file(archive_path)
    local_md5 = md5_file(archive_path)
    result.update({
        "local_size_bytes": local_size,
        "local_sha256": local_sha,
        "local_md5": local_md5,
    })
    if local_size == asset["catalog_content_length_bytes"]:
        result["checks"]["catalog_size"] = "pass"
    else:
        result["checks"]["catalog_size"] = "block"
        result["errors"].append("local archive size differs from provider catalog metadata")
    if local_md5 == asset["provider_md5"]:
        result["checks"]["provider_md5"] = "pass"
    else:
        result["checks"]["provider_md5"] = "block"
        result["errors"].append("local MD5 differs from provider metadata")
    result["checks"]["local_sha256"] = "pass" if HEX64_RE.fullmatch(local_sha) else "block"

    try:
        with ZipFile(archive_path) as archive:
            infos = archive.infolist()
            result["member_count"] = len(infos)
            if len(infos) > controls["maximum_member_count"]:
                result["errors"].append("ZIP member count exceeds the contract limit")
            members, path_errors = _relative_members(infos, asset["exact_product_id"])
            result["errors"].extend(path_errors)
            files = [(info, relative) for info, relative in members if not info.is_dir()]
            total_uncompressed = sum(info.file_size for info, _ in files)
            result["total_uncompressed_bytes"] = total_uncompressed
            if any(info.file_size > controls["maximum_single_uncompressed_bytes"] for info, _ in files):
                result["errors"].append("ZIP member exceeds the single-member uncompressed limit")
            total_limit = max(
                controls["maximum_total_uncompressed_bytes_floor"],
                int(local_size * controls["maximum_total_uncompressed_to_archive_ratio"]),
            )
            if total_uncompressed > total_limit:
                result["errors"].append("ZIP total uncompressed size exceeds the contract limit")
            for requirement in asset["required_members"]:
                matched = [
                    info for info, relative in files
                    if fnmatch.fnmatchcase(relative.casefold(), requirement["pattern"].casefold())
                ]
                check_name = "member:" + requirement["pattern"]
                if len(matched) < requirement["minimum_count"]:
                    result["checks"][check_name] = "block"
                    result["errors"].append(f"required SAFE member pattern is missing: {requirement['pattern']}")
                elif requirement["nonempty"] and any(info.file_size <= 0 for info in matched):
                    result["checks"][check_name] = "block"
                    result["errors"].append(f"required SAFE member is empty: {requirement['pattern']}")
                else:
                    result["checks"][check_name] = "pass"
            if result["errors"]:
                result["checks"]["zip_crc"] = "not_run_due_preflight_block"
            else:
                bad_member = archive.testzip()
                if bad_member is None:
                    result["checks"]["zip_crc"] = "pass"
                else:
                    result["checks"]["zip_crc"] = "block"
                    result["errors"].append(f"ZIP CRC failed for member: {bad_member}")
    except (BadZipFile, OSError, RuntimeError, ValueError) as exc:
        result["checks"]["zip_open"] = "block"
        result["errors"].append(f"ZIP inspection failed: {type(exc).__name__}: {exc}")

    if result["errors"]:
        result["status"] = "block"
    else:
        result["status"] = "pass_container_only"
        result["eligible_for_post_container_qa"] = True
    return result


def scan_contract(contract: dict[str, Any], custody_root: Path, scanned_at_utc: str) -> dict[str, Any]:
    if not utc_timestamp(scanned_at_utc):
        raise ValueError("scan timestamp must be RFC 3339 UTC ending in Z")
    if not custody_root.is_dir():
        raise ValueError("custody root must already exist; this tool will not create it")
    expected_root = Path(contract["execution_boundary"]["custody_root_from_plan"]).resolve()
    if custody_root.resolve() != expected_root:
        raise ValueError("custody root differs from the exact approved plan")
    controls = contract["archive_controls"]
    results = []
    for asset in contract["assets"]:
        relative = PurePosixPath(asset["archive_relative_path"])
        archive_path = custody_root.joinpath(*relative.parts)
        results.append(scan_archive(asset, archive_path, controls))
    statuses = {item["status"] for item in results}
    if "block" in statuses:
        status = "block"
    elif "defer" in statuses:
        status = "defer"
    else:
        status = "pass_container_only"
    return {
        "receipt_version": "1.0",
        "receipt_id": "NEPAL-M2-OFFLINE-VERIFICATION-RECEIPT-001",
        "verification_id": contract["verification_id"],
        "verification_contract_sha256": sha256_bytes(canonical_bytes(contract)),
        "scanned_at_utc": scanned_at_utc,
        "status": status,
        "custody_root": str(custody_root.resolve()),
        "network_requests_performed": False,
        "authentication_performed": False,
        "archive_extraction_performed": False,
        "source_archive_mutation_performed": False,
        "this_receipt_creates_authority": False,
        "pixel_usability_established": False,
        "assets": results,
        "next_required_gate": "post_container_gates" if status == "pass_container_only" else "resolve container findings",
        "limitations": contract["limitations"],
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


def write_scan_receipt(path: Path, value: Any) -> None:
    if not path.parent.is_dir():
        raise SystemExit("REFUSED: scan receipt parent must already exist")
    try:
        with path.open("xb") as handle:
            handle.write(canonical_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise SystemExit("REFUSED: scan receipt output already exists") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("records/acquisition-plan.json"))
    parser.add_argument("--intake", type=Path, default=Path("contracts/m2-intake-candidate.json"))
    parser.add_argument("--manifest-approval", type=Path, default=Path("records/source-gates/source-manifest-approval.json"))
    parser.add_argument("--source-manifest", type=Path, default=Path("records/source-manifest.json"))
    parser.add_argument("--review-bundle", type=Path, default=Path("reviews/m2-activation/review-bundle.json"))
    parser.add_argument("--contract-output", type=Path, default=Path("contracts/m2-offline-verification-candidate.json"))
    parser.add_argument("--readiness-input-output", type=Path, default=Path("records/readiness/m2-readiness-audit-input.json"))
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--scan-custody-root", type=Path)
    parser.add_argument("--scan-output", type=Path)
    parser.add_argument("--scanned-at-utc")
    args = parser.parse_args()

    if not utc_timestamp(args.created_at):
        raise SystemExit("--created-at must be an RFC 3339 UTC timestamp ending in Z")
    plan = load_json(args.plan)
    intake = load_json(args.intake)
    expected_contract = build_contract(
        plan,
        intake,
        sha256_file(args.plan),
        sha256_file(args.intake),
        sha256_file(args.manifest_approval),
        sha256_file(args.review_bundle),
        args.created_at,
    )
    expected_readiness = build_readiness_input(sha256_file(args.source_manifest))
    if args.verify_only:
        contract = load_json(args.contract_output)
        readiness = load_json(args.readiness_input_output)
    else:
        contract = expected_contract
        readiness = expected_readiness
    errors = validate_candidate(plan, intake, contract, expected_contract, readiness, expected_readiness)
    if errors:
        raise SystemExit("STATIC VALIDATION FAIL:\n- " + "\n- ".join(errors))
    write_or_verify(args.contract_output, expected_contract, args.verify_only)
    write_or_verify(args.readiness_input_output, expected_readiness, args.verify_only)

    scan_status = "not_requested"
    if args.scan_custody_root is not None or args.scan_output is not None or args.scanned_at_utc is not None:
        if args.scan_custody_root is None or args.scan_output is None or args.scanned_at_utc is None:
            raise SystemExit("--scan-custody-root, --scan-output, and --scanned-at-utc are required together")
        custody_root = args.scan_custody_root.resolve()
        scan_output = args.scan_output.resolve()
        if scan_output.is_relative_to(custody_root):
            raise SystemExit("REFUSED: scan receipt must remain outside read-only product custody")
        receipt = scan_contract(contract, args.scan_custody_root, args.scanned_at_utc)
        write_scan_receipt(args.scan_output, receipt)
        scan_status = receipt["status"]

    print(json.dumps({
        "status": "verified" if args.verify_only else "prepared",
        "authority_created": False,
        "network_or_authentication_performed": False,
        "external_custody_access": scan_status != "not_requested",
        "scan_status": scan_status,
        "asset_count": len(contract["assets"]),
        "contract": str(args.contract_output),
        "contract_sha256": sha256_bytes(canonical_bytes(contract)),
        "readiness_input": str(args.readiness_input_output),
        "readiness_input_sha256": sha256_bytes(canonical_bytes(readiness)),
    }, indent=2))


if __name__ == "__main__":
    main()
