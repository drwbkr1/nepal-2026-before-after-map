#!/usr/bin/env python3
"""Fail-closed controls for the approved local PROJ EGM2008 2.5-minute route."""

from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
CONTRACT_REF = "config/qa/m2-dem-vertical-datum-proj25-contract.json"
APPROVAL_REF = "records/source-gates/m2-dem-vertical-datum-proj25-metadata-recovery-001-approval.json"
EXPECTED_APPROVAL_SHA256 = "b77d5b943b35efdbc9d8d3c65e1f6122d34f79f581993dc79b244a58fc0a6541"
EXPECTED_GRID_SHA256 = "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a"
EXPECTED_GRID_SIZE = 80585622
EXPECTED_GRID_DESCRIPTION = (
    "WGS 84 (EPSG:4979) to EGM2008 height (EPSG:3855). "
    "Converted from egm08_25.gtx (last modified at 2018/10/08)"
)
EXPECTED_GRID_COPYRIGHT = "Derived from work by NGA. Public Domain"
SOURCE_ORDER = ["M2-DEM-001", "M2-DEM-002", "M2-DEM-003", "M2-DEM-004"]


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def controlled_path(relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe relative path: {relative}")
    candidate = DATA_ROOT.joinpath(*pure.parts)
    resolved_root = DATA_ROOT.resolve()
    resolved_parent = candidate.parent.resolve()
    if resolved_root != resolved_parent and resolved_root not in resolved_parent.parents:
        raise ValueError(f"path escapes data root: {relative}")
    if any(parent.is_symlink() for parent in [candidate.parent, *candidate.parents] if parent.exists() and parent != resolved_root):
        raise ValueError(f"symlinked controlled path refused: {relative}")
    return candidate


def load_contract() -> dict[str, Any]:
    contract = load_json(ROOT / CONTRACT_REF)
    if sha256_file(ROOT / APPROVAL_REF) != EXPECTED_APPROVAL_SHA256:
        raise ValueError("approval identity drift")
    grid = contract.get("grid", {})
    operation = contract.get("vertical_operation", {})
    conversion = contract.get("conversion", {})
    recovery = contract.get("metadata_recovery", {})
    sources = contract.get("dem_sources_in_exact_order", [])
    if (
        contract.get("status") != "approved_metadata_recovery_implementation_public_ci_pending"
        or contract.get("approval_sha256") != EXPECTED_APPROVAL_SHA256
        or grid.get("expected_sha256") != EXPECTED_GRID_SHA256
        or grid.get("expected_size_bytes") != EXPECTED_GRID_SIZE
        or grid.get("maximum_requests") != 1
        or grid.get("resume") is not False
        or grid.get("automatic_retry") is not False
        or recovery.get("attempt_id") != "m2-geoid-001-metadata-recovery-001"
        or recovery.get("network_requests") != 0
        or recovery.get("maximum_offline_verification_attempts") != 1
        or recovery.get("automatic_retry") is not False
        or operation.get("source_crs") != "EPSG:9518"
        or operation.get("target_crs") != "EPSG:4979"
        or operation.get("height_relation") != "h = H + N"
        or operation.get("proj_network_enabled") is not False
        or [item.get("source_id") for item in sources] != SOURCE_ORDER
        or conversion.get("maximum_attempts_per_dem") != 1
        or conversion.get("stop_on_first_failure") is not True
        or conversion.get("source_overwrite_permitted") is not False
    ):
        raise ValueError("vertical-datum contract drift")
    destinations = [str(item.get("output_relative_path", "")).lower() for item in sources]
    if len(destinations) != len(set(destinations)):
        raise ValueError("duplicate output destination")
    for item in sources:
        controlled_path(str(item["source_relative_path"]))
        controlled_path(str(item["output_relative_path"]))
    controlled_path(str(grid["staging_relative_path"]))
    controlled_path(str(grid["destination_relative_path"]))
    return contract


def vertical_pipeline(grid_path: Path) -> str:
    absolute = grid_path.resolve().as_posix()
    if " " in absolute:
        raise ValueError("grid path with spaces is not supported by the frozen pipeline")
    return (
        "+proj=pipeline "
        "+step +proj=unitconvert +xy_in=deg +xy_out=rad "
        f"+step +inv +proj=vgridshift +grids={absolute} +multiplier=1 "
        "+step +proj=unitconvert +xy_in=rad +xy_out=deg"
    )


def forward_grid_pipeline(grid_path: Path) -> str:
    absolute = grid_path.resolve().as_posix()
    if " " in absolute:
        raise ValueError("grid path with spaces is not supported by the frozen pipeline")
    return (
        "+proj=pipeline "
        "+step +proj=unitconvert +xy_in=deg +xy_out=rad "
        f"+step +proj=vgridshift +grids={absolute} +multiplier=1 "
        "+step +proj=unitconvert +xy_in=rad +xy_out=deg"
    )


def ellipsoidal_height(orthometric_height: float, geoid_undulation: float) -> float:
    values = (orthometric_height, geoid_undulation)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("height inputs must be finite")
    return orthometric_height + geoid_undulation


def direction_residual(orthometric_height: float, geoid_undulation: float, observed: float) -> float:
    if not math.isfinite(observed):
        raise ValueError("observed height must be finite")
    return abs(observed - ellipsoidal_height(orthometric_height, geoid_undulation))


def snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {"size_bytes": stat.st_size, "sha256": sha256_file(path)}


def promote_no_replace(staged: Path, destination: Path, expected_size: int, expected_sha256: str) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"destination collision: {destination}")
    observed = snapshot(staged)
    if observed != {"size_bytes": expected_size, "sha256": expected_sha256}:
        raise ValueError("staged identity mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.link(staged, destination)
    promoted = snapshot(destination)
    if promoted != observed:
        destination.unlink(missing_ok=True)
        raise ValueError("promoted identity mismatch")
    return promoted


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def stream_to_exclusive_staging(response: Any, staging: Path, expected_size: int) -> dict[str, Any]:
    staging.parent.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256()
    size = 0
    with staging.open("xb") as stream:
        while True:
            block = response.read(8 * 1024 * 1024)
            if not block:
                break
            size += len(block)
            if size > expected_size:
                raise ValueError("grid payload exceeds approved length")
            digest.update(block)
            stream.write(block)
        stream.flush()
        os.fsync(stream.fileno())
    return {"size_bytes": size, "sha256": digest.hexdigest()}


def _metadata_value(metadata: dict[str, Any], key: str) -> str | None:
    folded = {str(k).casefold(): str(v) for k, v in metadata.items()}
    return folded.get(key.casefold())


def inspect_grid(path: Path) -> dict[str, Any]:
    os.environ["PROJ_NETWORK"] = "OFF"
    from osgeo import gdal  # type: ignore

    gdal.UseExceptions()
    dataset = gdal.OpenEx(str(path), gdal.OF_RASTER | gdal.OF_READONLY)
    if dataset is None:
        raise ValueError("approved grid is not GDAL-readable")
    geotransform = tuple(float(value) for value in dataset.GetGeoTransform())
    width, height = int(dataset.RasterXSize), int(dataset.RasterYSize)
    corners_x = [geotransform[0], geotransform[0] + geotransform[1] * width]
    corners_y = [geotransform[3], geotransform[3] + geotransform[5] * height]
    metadata = dict(dataset.GetMetadata() or {})
    band = dataset.GetRasterBand(1)
    band_metadata = dict(band.GetMetadata() or {}) if band else {}
    combined = {**metadata, **band_metadata}
    result = {
        "driver": dataset.GetDriver().ShortName,
        "band_count": int(dataset.RasterCount),
        "width": width,
        "height": height,
        "geotransform": list(geotransform),
        "world_coverage": min(corners_x) <= -179.9 and max(corners_x) >= 179.9
        and min(corners_y) <= -89.9 and max(corners_y) >= 89.9,
        "source_crs": _metadata_value(combined, "source_crs"),
        "target_crs": _metadata_value(combined, "target_crs"),
        "tiff_tag_imagedescription": _metadata_value(combined, "TIFFTAG_IMAGEDESCRIPTION"),
        "target_crs_epsg_code": _metadata_value(combined, "target_crs_epsg_code"),
        "type": _metadata_value(combined, "type"),
        "area_of_use": _metadata_value(combined, "area_of_use"),
        "area_or_point": _metadata_value(combined, "AREA_OR_POINT"),
        "tiff_tag_copyright": _metadata_value(combined, "TIFFTAG_COPYRIGHT"),
        "proj_network_enabled": False,
    }
    dataset = None
    validate_grid_metadata(result)
    return result


def inspect_arcgis_readability(path: Path) -> dict[str, Any]:
    import arcpy  # type: ignore

    description = arcpy.Describe(str(path))
    raster = arcpy.Raster(str(path))
    return {
        "readable": True,
        "data_type": str(description.dataType),
        "width": int(raster.width),
        "height": int(raster.height),
        "band_count": int(raster.bandCount),
        "runtime_version": arcpy.GetInstallInfo().get("Version"),
    }


def validate_grid_metadata(metadata: dict[str, Any]) -> None:
    if (
        metadata.get("driver") != "GTiff"
        or metadata.get("band_count") != 1
        or metadata.get("width") != 8640
        or metadata.get("height") != 4321
        or metadata.get("world_coverage") is not True
        or metadata.get("tiff_tag_imagedescription") != EXPECTED_GRID_DESCRIPTION
        or metadata.get("target_crs_epsg_code") != "3855"
        or metadata.get("type") != "VERTICAL_OFFSET_GEOGRAPHIC_TO_VERTICAL"
        or metadata.get("area_of_use") != "World"
        or metadata.get("area_or_point") != "Point"
        or metadata.get("tiff_tag_copyright") != EXPECTED_GRID_COPYRIGHT
    ):
        raise ValueError("grid GeoTIFF metadata does not match the approved resource")
