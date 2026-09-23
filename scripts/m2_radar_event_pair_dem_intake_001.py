#!/usr/bin/env python3
"""Fixed seven-tile DEM intake controls for the approved event-area QA route.

No real transfer is started by importing this module. All real stages require
separately published implementation and execution gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from m2_transfer_core import NoRedirectHandler, promote_atomic_no_replace


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
PREFIX = "m2-radar-event-area-pair-001"
PROPOSAL_REF = "contracts/milestone-002-radar-event-area-pair-001-proposal.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
APPROVAL_REF = f"records/source-gates/{PREFIX}-approval.json"
PACKET_GATE_REF = f"records/readiness/{PREFIX}-packet-publication-gate.json"
ASSESSMENT_REF = "records/source-gates/m2-radar-event-pair-seven-dem-source-assessment-001.json"
PROPOSAL_SHA = "ae5fe535123debcd8619487bbdd68e2c19ff49dbc2505795fcdc48cea324b1e2"
BUNDLE_SHA = "ad6f0f5e75c768721ebbc787e6550dcb28e61fba22c86271beed982d220a5423"
ITEMS = (
    "Copernicus_DSM_COG_10_N27_00_E086_00_DEM",
    "Copernicus_DSM_COG_10_N28_00_E083_00_DEM",
    "Copernicus_DSM_COG_10_N28_00_E086_00_DEM",
    "Copernicus_DSM_COG_10_N29_00_E083_00_DEM",
    "Copernicus_DSM_COG_10_N29_00_E084_00_DEM",
    "Copernicus_DSM_COG_10_N29_00_E085_00_DEM",
    "Copernicus_DSM_COG_10_N29_00_E086_00_DEM",
)
HOST = "copernicus-dem-30m.s3.eu-central-1.amazonaws.com"
MIN_FREE_BYTES = 4 * 1024**3


class IntakeError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(ref: str) -> dict[str, Any]:
    value = json.loads((ROOT / ref).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntakeError("control_root_not_object")
    return value


def exact_assets() -> list[dict[str, Any]]:
    if sha256(ROOT / PROPOSAL_REF) != PROPOSAL_SHA or sha256(ROOT / BUNDLE_REF) != BUNDLE_SHA:
        raise IntakeError("approved_packet_identity_drift")
    proposal, bundle, approval = load(PROPOSAL_REF), load(BUNDLE_REF), load(APPROVAL_REF)
    for item in bundle["artifacts"]:
        if sha256(ROOT / item["path"]) != item["sha256"]:
            raise IntakeError("frozen_packet_artifact_drift")
    if (
        approval.get("decision") != "approve"
        or approval.get("attestation") is not True
        or approval.get("bindings", {}).get("proposal_sha256") != PROPOSAL_SHA
        or approval.get("bindings", {}).get("review_bundle_sha256") != BUNDLE_SHA
        or approval.get("authority", {}).get("automatic_retry") is not False
        or approval.get("authority", {}).get("baseline_admission_or_change_analysis") is not False
    ):
        raise IntakeError("approval_scope_drift")
    gate = load(PACKET_GATE_REF)
    if (
        gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible"
        or gate.get("bindings", {}).get("approval_sha256") != sha256(ROOT / APPROVAL_REF)
        or gate.get("bindings", {}).get("public_ci_conclusion") != "success"
    ):
        raise IntakeError("packet_publication_gate_missing")
    assets = load(ASSESSMENT_REF)["sources"][0]["exact_assets"]
    if [item["item_id"] for item in assets] != list(ITEMS):
        raise IntakeError("fixed_tile_order_drift")
    if proposal["seven_exact_candidate_item_ids_in_fixed_order"] != list(ITEMS):
        raise IntakeError("proposal_tile_order_drift")
    if sum(item["observed_head_content_length_bytes"] for item in assets) != 273055703:
        raise IntakeError("metadata_byte_total_drift")
    for item in assets:
        url = item["anonymous_https_url"]
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != HOST or parsed.query or parsed.fragment:
            raise IntakeError("unsafe_source_url")
        if parsed.path != f"/{item['item_id']}/{item['item_id']}.tif":
            raise IntakeError("source_url_identity_drift")
    return assets


def paths_for(item_id: str, attempt_number: int = 1) -> dict[str, Path]:
    if item_id not in ITEMS or attempt_number not in (1, 2):
        raise IntakeError("unapproved_item_or_attempt")
    attempt = f"{PREFIX}-{ITEMS.index(item_id) + 1:02d}-attempt-{attempt_number:03d}"
    root = DATA_ROOT.resolve()
    paths = {
        "staging": DATA_ROOT / ".intake-staging" / PREFIX / attempt / f"{item_id}.part.tif",
        "terminal": DATA_ROOT / "derived" / "control-events" / PREFIX / f"{attempt}-terminal.json",
        "error": DATA_ROOT / "derived" / "control-events" / PREFIX / f"{attempt}-error.json",
        "cleanup": DATA_ROOT / "derived" / "control-events" / PREFIX / f"{attempt}-cleanup.json",
        "destination": DATA_ROOT / "custody" / "dem" / "copernicus-glo30" / f"{item_id}.tif",
    }
    for path in paths.values():
        resolved = path.resolve(strict=False)
        if root not in resolved.parents or any(part.is_symlink() for part in path.parents if part.exists()):
            raise IntakeError("unsafe_custody_path")
    return paths


def check_head(asset: dict[str, Any], opener: Any | None = None) -> dict[str, Any]:
    opener = opener or urllib.request.build_opener(NoRedirectHandler())
    request = urllib.request.Request(asset["anonymous_https_url"], method="HEAD", headers={"User-Agent": "nepal-event-pair-dem-intake/1.0"})
    try:
        with opener.open(request, timeout=60) as response:
            body = response.read()
            headers = {key.casefold(): value for key, value in response.headers.items()}
            result = {
                "status": int(response.status),
                "resolved_url": response.geturl(),
                "content_length": int(headers.get("content-length", "-1")),
                "etag": headers.get("etag", ""),
                "content_type": headers.get("content-type", "").split(";", 1)[0].casefold(),
                "response_body_bytes": len(body),
            }
    except urllib.error.HTTPError as exc:
        raise IntakeError("head_http_failure_or_redirect") from exc
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        raise IntakeError("head_unavailable") from exc
    if (
        result["status"] != 200
        or result["resolved_url"] != asset["anonymous_https_url"]
        or result["content_length"] != asset["observed_head_content_length_bytes"]
        or result["etag"] != asset["observed_head_etag"]
        or result["content_type"] != "image/tiff"
        or result["response_body_bytes"] != 0
    ):
        raise IntakeError("source_head_identity_drift")
    return result


def no_payload_preflight(*, opener: Any | None = None, free_bytes: int | None = None) -> list[dict[str, Any]]:
    assets = exact_assets()
    if not DATA_ROOT.is_dir() or DATA_ROOT.is_symlink():
        raise IntakeError("custody_root_missing_or_unsafe")
    available = shutil.disk_usage(DATA_ROOT).free if free_bytes is None else free_bytes
    if available < MIN_FREE_BYTES:
        raise IntakeError("insufficient_disk_space")
    for item in assets:
        paths = paths_for(item["item_id"])
        if any(path.exists() for path in paths.values()):
            raise IntakeError("fresh_attempt_or_destination_collision")
    return [check_head(item, opener=opener) for item in assets]


def verify_geotiff(path: Path, cell: list[int]) -> dict[str, Any]:
    """Read the complete data band in bounded windows before promotion."""
    from osgeo import gdal, osr  # type: ignore
    import numpy as np  # type: ignore

    gdal.UseExceptions()
    raster = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY)
    if raster is None or raster.RasterCount != 1 or (raster.RasterXSize, raster.RasterYSize) != (3600, 3600):
        raster = None
        raise IntakeError("geotiff_structure_drift")
    srs = raster.GetSpatialRef()
    if srs is None:
        raster = None
        raise IntakeError("geotiff_crs_missing")
    expected_srs = osr.SpatialReference()
    expected_srs.ImportFromEPSG(4326)
    if not srs.IsGeographic() or not srs.IsSameGeogCS(expected_srs):
        raster = None
        raise IntakeError("geotiff_crs_drift")
    west, south, east, north = cell
    gt = raster.GetGeoTransform()
    bounds = (gt[0], gt[3] + gt[5] * raster.RasterYSize, gt[0] + gt[1] * raster.RasterXSize, gt[3])
    if any(abs(a - b) > 0.001 for a, b in zip(bounds, (west, south, east, north))):
        raster = None
        raise IntakeError("geotiff_bounds_drift")
    band = raster.GetRasterBand(1)
    if gdal.GetDataTypeName(band.DataType) != "Float32":
        band = raster = None
        raise IntakeError("geotiff_data_type_drift")
    nodata = band.GetNoDataValue()
    valid = 0
    nonfinite = 0
    for y in range(0, 3600, 256):
        for x in range(0, 3600, 256):
            values = np.asarray(band.ReadAsArray(x, y, min(256, 3600 - x), min(256, 3600 - y)))
            finite = np.isfinite(values)
            nonfinite += int(np.count_nonzero(~finite))
            if nodata is not None:
                finite &= values != nodata
            valid += int(np.count_nonzero(finite))
    if valid == 0 or nonfinite:
        band = raster = None
        raise IntakeError("geotiff_pixel_validity_failed")
    band = raster = None
    return {"width": 3600, "height": 3600, "band_count": 1, "epsg": 4326, "bounds": list(bounds), "valid_pixels": valid, "nonfinite_pixels": nonfinite, "nodata_value": nodata}


def require_execution_gates() -> None:
    for suffix in ("implementation-publication-gate", "execution-publication-gate"):
        gate = load(f"records/readiness/{PREFIX}-{suffix}.json")
        if gate.get("public_ci_conclusion") != "success" or gate.get("bindings", {}).get("intake_code_sha256") != sha256(Path(__file__)):
            raise IntakeError("public_implementation_or_execution_gate_missing")
    preflight = load(f"records/readiness/{PREFIX}-final-preflight.json")
    if preflight.get("status") != "pass_no_payload" or preflight.get("bindings", {}).get("intake_code_sha256") != sha256(Path(__file__)):
        raise IntakeError("final_no_payload_preflight_missing")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_reserved(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with path.open("r+b") as stream:
        if stream.seek(0, os.SEEK_END) != 0:
            raise IntakeError("reserved_receipt_already_written")
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def acquire_one(index: int, *, opener: Any | None = None) -> dict[str, Any]:
    """One fresh byte-zero request; the caller must stop on any failure."""
    require_execution_gates()
    assets = exact_assets()
    if not 0 <= index < len(assets):
        raise IntakeError("tile_index_out_of_scope")
    for prior in assets[:index]:
        previous = paths_for(prior["item_id"])
        if not previous["terminal"].is_file() or not previous["destination"].is_file():
            raise IntakeError("prior_tile_not_terminal_and_promoted")
        receipt = json.loads(previous["terminal"].read_text(encoding="utf-8"))
        if receipt.get("status") != "pass_verified_and_promoted" or sha256(previous["destination"]) != receipt.get("sha256"):
            raise IntakeError("prior_tile_identity_drift")
    item = assets[index]
    paths = paths_for(item["item_id"])
    if any(path.exists() for path in paths.values()):
        raise IntakeError("fresh_attempt_or_destination_collision")
    if shutil.disk_usage(DATA_ROOT).free < MIN_FREE_BYTES:
        raise IntakeError("insufficient_disk_space")
    opener = opener or urllib.request.build_opener(NoRedirectHandler())
    head = check_head(item, opener)
    reserve_receipts(paths)
    status = "terminal_failure_no_retry"
    stage = "request"
    observed_sha = None
    observed_size = 0
    try:
        request = urllib.request.Request(item["anonymous_https_url"], headers={"User-Agent": "nepal-event-pair-dem-intake/1.0", "Accept": "image/tiff", "Accept-Encoding": "identity"})
        with opener.open(request, timeout=180) as response:
            headers = {key.casefold(): value for key, value in response.headers.items()}
            if (
                response.status != 200
                or response.geturl() != item["anonymous_https_url"]
                or int(headers.get("content-length", "-1")) != item["observed_head_content_length_bytes"]
                or headers.get("etag") != item["observed_head_etag"]
                or headers.get("content-type", "").split(";", 1)[0].casefold() != "image/tiff"
            ):
                raise IntakeError("get_response_identity_drift")
            paths["staging"].parent.mkdir(parents=True, exist_ok=False)
            digest = hashlib.sha256()
            stage = "transfer"
            with paths["staging"].open("xb") as stream:
                while block := response.read(8 * 1024 * 1024):
                    stream.write(block)
                    digest.update(block)
                    observed_size += len(block)
                    if observed_size > item["observed_head_content_length_bytes"]:
                        raise IntakeError("transfer_exceeds_expected_length")
                stream.flush()
                os.fsync(stream.fileno())
            observed_sha = digest.hexdigest()
        if observed_size != item["observed_head_content_length_bytes"]:
            raise IntakeError("transfer_length_mismatch")
        stage = "geotiff_verification"
        structure = verify_geotiff(paths["staging"], item["cell_wgs84"])
        stage = "no_replace_promotion"
        promote_verified(paths["staging"], paths["destination"], observed_size, observed_sha)
        status = "pass_verified_and_promoted"
        return_value = {"status": status, "item_id": item["item_id"], "sha256": observed_sha, "size_bytes": observed_size, "geotiff": structure, "anonymous_access": True, "automatic_retry": False}
    except BaseException as exc:
        code = exc.code if isinstance(exc, IntakeError) else "transport_or_runtime_failure"
        return_value = {"status": status, "item_id": item["item_id"], "failure_code": code, "last_stage": stage, "partial_bytes_preserved": paths["staging"].stat().st_size if paths["staging"].exists() else 0, "anonymous_access": True, "automatic_retry": False}
    terminal = {"schema_version": "1.0", "attempt": f"{PREFIX}-{index + 1:02d}-attempt-001", "completed_at_utc": utc_now(), "head": head, **return_value}
    if status != "pass_verified_and_promoted":
        write_reserved(paths["error"], {"schema_version": "1.0", "attempt": terminal["attempt"], "failure_code": return_value["failure_code"], "last_stage": stage, "completed_at_utc": utc_now()})
    try:
        write_reserved(paths["terminal"], terminal)
    finally:
        write_reserved(paths["cleanup"], {"schema_version": "1.0", "attempt": terminal["attempt"], "status": "partial_preserved" if status != "pass_verified_and_promoted" else "no_cleanup_required", "completed_at_utc": utc_now()})
    return terminal


def reserve_receipts(paths: dict[str, Path]) -> None:
    for key in ("terminal", "error", "cleanup"):
        path = paths[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.flush()
            os.fsync(stream.fileno())


def promote_verified(staging: Path, destination: Path, expected_size: int, expected_sha256: str) -> None:
    if staging.stat().st_size != expected_size or sha256(staging) != expected_sha256:
        raise IntakeError("staged_byte_identity_drift")
    destination.parent.mkdir(parents=True, exist_ok=True)
    promote_atomic_no_replace(staging, destination)
    if destination.stat().st_size != expected_size or sha256(destination) != expected_sha256:
        raise IntakeError("promoted_byte_identity_drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--no-payload-preflight", action="store_true")
    group.add_argument("--tile-index", type=int, choices=range(1, 8))
    args = parser.parse_args()
    try:
        if args.no_payload_preflight:
            heads = no_payload_preflight()
            print(json.dumps({"status": "pass_no_payload", "tile_count": len(heads), "total_bytes": sum(item["content_length"] for item in heads), "credential_used": False}))
            return 0
        result = acquire_one(args.tile_index - 1)
        print(json.dumps({"status": result["status"], "item_id": result["item_id"], "failure_code": result.get("failure_code"), "size_bytes": result.get("size_bytes"), "sha256": result.get("sha256")}))
        return 0 if result["status"] == "pass_verified_and_promoted" else 20
    except IntakeError as exc:
        print(json.dumps({"status": "stopped_before_payload_or_unresolved", "code": exc.code}))
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
