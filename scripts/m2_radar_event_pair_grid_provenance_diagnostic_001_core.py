"""Strict, read-only controls for the approved event-pair grid diagnostic."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, BinaryIO


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-event-area-pair-grid-provenance-diagnostic-001"
PROPOSAL = ROOT / "contracts" / "milestone-002-radar-event-area-pair-grid-provenance-diagnostic-001-proposal.json"
BUNDLE = ROOT / "reviews" / PREFIX / "review-bundle.json"
APPROVAL = ROOT / "records" / "source-gates" / f"{PREFIX}-approval.json"
PACKET_GATE = ROOT / "records" / "readiness" / f"{PREFIX}-packet-publication-gate.json"
DATA_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
OLD_ATTEMPT = DATA_ROOT / "e1" / "a1"
SOURCE_ROOT = OLD_ATTEMPT / "s" / "2"
NAMES = (
    "gamma0_linear_slant.crf",
    "gamma0_linear_despeckled.crf",
    "gamma0_linear_gtc_raw.crf",
    "gamma0_db_gtc_raw.crf",
    "geometric_distortion_mask_gtc_raw.crf",
)
EXPECTED_CONF_SHA256 = "eff271e62660d4ae2fe64d614c9051a953c750f167926b946dcf3cb5e9c7d419"
EXPECTED_PROPOSAL_SHA256 = "715656bf5ad964eea5805d99e5416ba592e5c743cde6db6f629ce3029c7d1bf4"
EXPECTED_BUNDLE_SHA256 = "469da6bd5b69173d25561f1f9b405362ee4218685831920ef8d2933a4995d0f2"


class DiagnosticError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DiagnosticError("bound_json_root_invalid")
    return value


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def reserve(path: Path) -> BinaryIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("xb+")
    stream.flush()
    os.fsync(stream.fileno())
    return stream


def persist(stream: BinaryIO, value: Any) -> None:
    stream.seek(0)
    stream.write(canonical_bytes(value))
    stream.truncate()
    stream.flush()
    os.fsync(stream.fileno())
    stream.close()


def check_authority() -> None:
    if sha256_file(PROPOSAL) != EXPECTED_PROPOSAL_SHA256 or sha256_file(BUNDLE) != EXPECTED_BUNDLE_SHA256:
        raise DiagnosticError("proposal_or_bundle_drift")
    approval = load_json(APPROVAL)
    gate = load_json(PACKET_GATE)
    if approval.get("decision") != "approve" or approval.get("bindings", {}).get("proposal_sha256") != EXPECTED_PROPOSAL_SHA256:
        raise DiagnosticError("approval_not_exact")
    if approval.get("bindings", {}).get("review_bundle_sha256") != EXPECTED_BUNDLE_SHA256:
        raise DiagnosticError("approval_bundle_not_exact")
    if gate.get("status") != "pass_exact_public_packet_and_approval_ci_implementation_eligible":
        raise DiagnosticError("packet_gate_not_pass")
    if gate.get("bindings", {}).get("approval_sha256") != sha256_file(APPROVAL):
        raise DiagnosticError("packet_gate_approval_drift")


def candidate_paths(root: Path = SOURCE_ROOT) -> list[Path]:
    return [root / name for name in NAMES]


def check_candidate_path(path: Path, root: Path = SOURCE_ROOT) -> None:
    if path.parent != root or path.name not in NAMES:
        raise DiagnosticError("candidate_path_outside_exact_allowlist")
    if not path.is_dir() or path.is_symlink():
        raise DiagnosticError("exact_candidate_missing_or_unsafe")
    if path.resolve() != root.resolve() / path.name:
        raise DiagnosticError("candidate_path_resolved_outside_exact_root")


def _extent(value: Any) -> list[float]:
    return [float(value.XMin), float(value.YMin), float(value.XMax), float(value.YMax)]


def _metadata(value: Any, *, raster: bool) -> dict[str, Any]:
    result: dict[str, Any] = {}
    attributes = {
        "width": "width", "height": "height", "band_count": "bandCount",
        "cell_size_x": "meanCellWidth", "cell_size_y": "meanCellHeight",
    }
    for key, attribute in attributes.items():
        observed = getattr(value, attribute, None)
        result[key] = (int(observed) if key in {"width", "height", "band_count"} else float(observed)) if observed is not None else None
    spatial_reference = getattr(value, "spatialReference", None)
    result["wkid"] = int(spatial_reference.factoryCode) if spatial_reference is not None else None
    extent = getattr(value, "extent", None)
    result["bounds"] = _extent(extent) if extent is not None else None
    if raster and any(result[key] is None for key in ("width", "height", "band_count", "cell_size_x", "cell_size_y", "wkid", "bounds")):
        raise DiagnosticError("raster_metadata_missing")
    return result


def inspect_raster(arcpy: Any, path: Path, *, root: Path = SOURCE_ROOT) -> dict[str, Any]:
    check_candidate_path(path, root)
    raster = arcpy.Raster(str(path))
    described = arcpy.Describe(str(path))
    raster_metadata = _metadata(raster, raster=True)
    describe_metadata = _metadata(described, raster=False)
    for key, left in raster_metadata.items():
        right = describe_metadata[key]
        if right is None:
            continue
        if key == "bounds":
            equal = len(left) == len(right) and all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(left, right))
        elif key.startswith("cell_size"):
            equal = math.isclose(left, right, abs_tol=1e-6)
        else:
            equal = left == right
        if not equal:
            raise DiagnosticError("raster_describe_metadata_conflict")
    return {"name": path.name, "raster": raster_metadata, "describe": describe_metadata,
            "describe_unavailable_fields": [key for key, value in describe_metadata.items() if value is None]}


def verify_gtc_configuration(path: Path, *, root: Path = SOURCE_ROOT) -> dict[str, Any]:
    if path != root / "gamma0_linear_gtc_raw.crf":
        raise DiagnosticError("configuration_candidate_not_exact_gtc")
    check_candidate_path(path, root)
    configs = sorted(item for item in path.rglob("*.conf") if item.is_file() and not item.is_symlink())
    if not configs or len(configs) > 16:
        raise DiagnosticError("gtc_configuration_count_ambiguous")
    matches = []
    for item in configs:
        if item.stat().st_size > 1024 * 1024:
            raise DiagnosticError("gtc_configuration_oversized")
        if sha256_file(item) == EXPECTED_CONF_SHA256:
            matches.append(item)
    if len(matches) != 1:
        raise DiagnosticError("gtc_configuration_identity_mismatch")
    return {"configuration_sha256": EXPECTED_CONF_SHA256, "configuration_size_bytes": matches[0].stat().st_size,
            "matching_configuration_count": 1}


def first_declared_coarse_stage(records: list[dict[str, Any]]) -> str | None:
    for item in records:
        raster = item["raster"]
        if raster["wkid"] == 4326 and raster["cell_size_x"] >= 1.0 and raster["cell_size_y"] >= 1.0:
            return item["name"]
    return None
