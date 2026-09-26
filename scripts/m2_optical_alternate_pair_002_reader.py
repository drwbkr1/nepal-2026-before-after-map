#!/usr/bin/env python3
"""Separate candidate reader for the exact PB 05.12/05.13 visual pair.

No custody is opened on import. Callers select the materialization base and
must separately enforce the approved public-CI and no-content execution gates.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from m2_optical_alternate_pair_002_core import (
    EXACT_PRODUCTS, TARGET_AOIS, decide_before_screen,
    inspect_product_metadata, single_date_usable_mask,
)
from m2_optical_gdal_recovery_002_adapter import (
    TARGET_GRID, describe, rasterize_aoi, warp_target,
)
from m2_optical_pair_pilot_001_core import sha256_file
from optical_input_readiness_core import RASTER_ROLES, select_required_members


ROOT = Path(__file__).resolve().parents[1]
HEADER_CONTRACT = ROOT / "config/qa/optical-input-readiness-contract.json"
AOI = ROOT / "config/aoi/approved-study-areas-epsg32645.json"


def inspect_materialized(source_id: str, materialization_base: Path,
                         *, contract: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Path]]:
    """Verify selected member identities before opening XML or JP2 headers."""
    if source_id not in EXACT_PRODUCTS:
        raise ValueError("alternate_pair_source_id_unapproved")
    product_name = EXACT_PRODUCTS[source_id][0]
    base = materialization_base.resolve(strict=True)
    manifest_path = base / "materialization-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = contract or json.loads(HEADER_CONTRACT.read_text(encoding="utf-8"))
    selected = select_required_members(manifest, contract)
    if selected["status"] != "pass_inventory_only":
        raise ValueError("alternate_pair_required_members_invalid")
    safe_root = (base / product_name).resolve(strict=True)
    if not safe_root.is_relative_to(base) or not safe_root.is_dir():
        raise ValueError("alternate_pair_safe_root_invalid")
    paths: dict[str, Path] = {}
    for role, item in selected["members"].items():
        relative = item["relative_path"]
        posix = PurePosixPath(relative)
        if posix.is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
            raise ValueError("alternate_pair_member_path_invalid")
        path = (safe_root / Path(*posix.parts)).resolve(strict=True)
        if (not path.is_relative_to(safe_root) or not path.is_file()
                or path.stat().st_size != item["size_bytes"]
                or sha256_file(path) != item["sha256"]):
            raise ValueError("alternate_pair_member_identity_drift")
        paths[role] = path
    parsed = inspect_product_metadata(source_id, product_name,
                                      paths["metadata_product"].read_text(encoding="utf-8"))
    descriptions = {role: describe(paths[role]) for role in sorted(RASTER_ROLES)}
    return {
        "source_id": source_id,
        "exact_product_name": product_name,
        "materialization_manifest_sha256": sha256_file(manifest_path),
        "metadata": parsed,
        "descriptions": descriptions,
        "raster_pixels_decoded": False,
    }, paths


def screen_before_arrays(paths: dict[str, Path], *,
                         aoi: dict[str, Any] | None = None,
                         grid: dict[str, Any] = TARGET_GRID) -> dict[str, Any]:
    """Read only the frozen grid for the exact before-scene acquisition screen."""
    if set(paths) < {"SCL", "B11", "quality_classification"}:
        raise ValueError("alternate_pair_before_roles_missing")
    if grid != TARGET_GRID:
        raise ValueError("alternate_pair_grid_drift")
    aoi = aoi or json.loads(AOI.read_text(encoding="utf-8"))
    if aoi.get("spatialReference", {}).get("wkid") != 32645:
        raise ValueError("alternate_pair_aoi_crs_drift")
    features = {feature["attributes"]["AOI_ID"]: feature
                for feature in aoi["features"]}
    if set(features) != {"AOI-OVERVIEW", *TARGET_AOIS}:
        raise ValueError("alternate_pair_aoi_set_drift")
    scl = warp_target(paths["SCL"], "SCL", grid)
    quality = warp_target(paths["quality_classification"], "quality_classification", grid)
    b11 = warp_target(paths["B11"], "B11", grid)
    masks = {identifier: rasterize_aoi(features[identifier], grid)
             for identifier in TARGET_AOIS}
    result = decide_before_screen(single_date_usable_mask(scl, quality, b11), masks)
    result.update({"source_id": "M2-OPT-001", "wkid": 32645, "cell_size_m": 20.0,
                   "new_source_requested": False,
                   "baseline_admission_or_change_analysis": False})
    return result
