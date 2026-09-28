#!/usr/bin/env python3
"""Audit a saved local ASF partial panel after a fresh ArcGIS reopen.

This checks the handoff artifact, not source pixels or scientific fitness. It
must not be used to release real data without the separate source, QA and rights
gates in the approved partial-pair route.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from m2_asf_hyp3_rtc_partial_pair_map_001 import (
    AFTER_LABEL, BEFORE_LABEL, WARNING, _check_raster, _sha,
)


RASTERS = {
    BEFORE_LABEL: "before_common_valid_vv_db.tif",
    AFTER_LABEL: "after_common_valid_vv_db.tif",
}
PNG_FILES = (
    "Nepal_ASF_RTC_Partial_Pair_Local.png",
    "Nepal_ASF_RTC_Partial_Pair_Reopen.png",
)
APRX = "Nepal_ASF_RTC_Partial_Pair_Local.aprx"
REQUIRED_TEXT_NAMES = {"Title", "Coverage", "Partial-data warning", "Credits and DOIs"}


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("partial_panel_png_invalid")
    width, height = struct.unpack(">II", header[16:24])
    if width < 1000 or height < 500:
        raise ValueError("partial_panel_png_too_small")
    return width, height


def audit_saved_panel(output: Path, *, arcpy_module=None) -> dict:
    """Check local raster bindings, map text and two exported PNGs."""
    if arcpy_module is None:
        import arcpy as arcpy_module  # type: ignore[import-not-found]
    if not output.is_dir() or output.is_symlink():
        raise ValueError("partial_panel_output_invalid")
    receipt_path = output / "build.json"
    project_path = output / APRX
    if not receipt_path.is_file() or not project_path.is_file():
        raise ValueError("partial_panel_required_file_missing")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("partial_panel_receipt_invalid") from exc
    if (not isinstance(receipt, dict)
            or receipt.get("status") != "built_local_partial_visual_pending_fresh_reopen"
            or receipt.get("wkid") != 32645
            or receipt.get("DEM_raster_displayed") is not False
            or receipt.get("change_analysis_or_attribution") is not False
            or receipt.get("public_pixel_publication") is not False
            or not isinstance(receipt.get("staged_sha256"), list)
            or len(receipt["staged_sha256"]) != 2):
        raise ValueError("partial_panel_receipt_invalid")
    paths = [output / name for name in RASTERS.values()]
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise ValueError("partial_panel_raster_missing")
    if [_sha(path) for path in paths] != receipt["staged_sha256"]:
        raise ValueError("partial_panel_raster_hash_drift")
    if (receipt.get("aprx_sha256") != _sha(project_path)
            or receipt.get("first_png_sha256") != _sha(output / PNG_FILES[0])):
        raise ValueError("partial_panel_project_or_export_hash_drift")
    raster_headers = [_check_raster(arcpy_module, path) for path in paths]
    if raster_headers[0] != raster_headers[1]:
        raise ValueError("partial_panel_raster_grid_drift")
    project = arcpy_module.mp.ArcGISProject(str(project_path))
    maps, layouts = project.listMaps(), project.listLayouts()
    if len(maps) != 2 or len(layouts) != 1 or {item.name for item in maps} != set(RASTERS):
        raise ValueError("partial_panel_project_shape_invalid")
    for map_obj in maps:
        layers = map_obj.listLayers()
        if (map_obj.spatialReference.factoryCode != 32645 or len(layers) != 1
                or layers[0].isBroken or not layers[0].supports("DATASOURCE")):
            raise ValueError("partial_panel_layer_invalid")
        expected = output / RASTERS[map_obj.name]
        if Path(layers[0].dataSource).resolve() != expected.resolve():
            raise ValueError("partial_panel_layer_path_drift")
    text_elements = layouts[0].listElements("TEXT_ELEMENT")
    if (len(text_elements) != 6
            or not REQUIRED_TEXT_NAMES.issubset({element.name for element in text_elements})
            or sum(element.text == BEFORE_LABEL for element in text_elements) != 1
            or sum(element.text == AFTER_LABEL for element in text_elements) != 1):
        raise ValueError("partial_panel_text_set_invalid")
    by_name = {element.name: element.text for element in text_elements}
    if (by_name["Partial-data warning"] != WARNING
            or by_name["Title"] != "Nepal 2026 | EPSG:32645 | ASF RTC VV gamma0 dB"):
        raise ValueError("partial_panel_warning_or_title_drift")
    coverage = receipt.get("common_valid_by_aoi")
    if (not isinstance(coverage, dict)
            or set(coverage) != {"AOI-SOURCE", "AOI-UPPER-CORRIDOR"}
            or any(type(value) not in (int, float) or not .2 <= value <= 1
                   for value in coverage.values())):
        raise ValueError("partial_panel_coverage_receipt_invalid")
    expected_coverage = (f"Common valid VV/VH: source {coverage['AOI-SOURCE']:.1%}; "
                         f"upper corridor {coverage['AOI-UPPER-CORRIDOR']:.1%}. "
                         "Blank areas exclude layover, shadow or NoData.")
    if by_name["Coverage"] != expected_coverage:
        raise ValueError("partial_panel_coverage_text_drift")
    credits = by_name["Credits and DOIs"].casefold()
    if not all(term in credits for term in ("asf", "esa", "doi.org/")):
        raise ValueError("partial_panel_credits_missing")
    png_sizes = [_png_size(output / name) for name in PNG_FILES]
    if png_sizes[0] != png_sizes[1]:
        raise ValueError("partial_panel_export_size_drift")
    return {
        "status": "pass_local_partial_panel_artifact_audit_only",
        "map_count": 2, "layout_count": 1, "broken_layers": 0,
        "raster_paths_resolve_inside_output": True,
        "staged_raster_hashes_match_build_receipt": True,
        "warning_coverage_and_credits_present": True,
        "png_size": list(png_sizes[0]),
        "real_source_pixels_or_scientific_fitness_assessed": False,
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(audit_saved_panel(Path(sys.argv[1])), sort_keys=True))
