#!/usr/bin/env python3
"""Installed ArcGIS/GDAL smoke test with only generated disposable JP2 data."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from m2_optical_alternate_pair_002_core import decide_before_screen, single_date_usable_mask
from m2_optical_alternate_pair_002_map import build_local_map
import m2_optical_alternate_pair_002_display as display
from m2_optical_alternate_pair_002_core import EXACT_PRODUCTS
from m2_optical_alternate_pair_002_reader import inspect_materialized
from m2_optical_gdal_recovery_002_adapter import describe, warp_target
from optical_input_readiness_core import ROLE_PATTERNS, validate_product_grid


GRID = {"xmin": 300000.0, "ymin": 3100000.0, "xmax": 301280.0,
        "ymax": 3101280.0, "rows": 64, "columns": 64,
        "cell_size_m": 20.0, "wkid": 32645}


def make_jp2(path: Path, values: np.ndarray, *, cell_size: float = 20.0) -> None:
    from osgeo import gdal, osr

    driver = gdal.GetDriverByName("JP2OpenJPEG")
    if driver is None or driver.GetMetadataItem("DCAP_CREATECOPY") != "YES":
        raise RuntimeError("disposable_jp2_writer_unavailable")
    bands, rows, columns = values.shape
    source = gdal.GetDriverByName("MEM").Create(
        "", columns, rows, bands,
        gdal.GDT_UInt16 if values.dtype == np.uint16 else gdal.GDT_Byte)
    if source is None:
        raise RuntimeError("disposable_mem_create_failed")
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32645)
    source.SetSpatialRef(srs)
    source.SetGeoTransform((GRID["xmin"], cell_size, 0.0, GRID["ymax"], 0.0, -cell_size))
    for index in range(bands):
        source.GetRasterBand(index + 1).WriteArray(values[index])
    output = driver.CreateCopy(str(path), source, strict=1,
                               options=["REVERSIBLE=YES", "QUALITY=100"])
    if output is None:
        raise RuntimeError("disposable_jp2_create_failed")
    output.Close()
    source.Close()


def validate() -> dict:
    import arcpy
    from osgeo import gdal, osr

    if arcpy.GetInstallInfo()["Version"] != "3.7.1":
        raise RuntimeError("arcgis_version_drift")
    with tempfile.TemporaryDirectory(prefix="nepal-pb0513-disposable-") as directory:
        root = Path(directory)
        product_name = EXACT_PRODUCTS["M2-OPT-003"][0]
        materialization = root / "generated-materialization"
        safe = materialization / product_name
        safe.mkdir(parents=True)
        manifest_files = []
        xml = ("<Product><PROCESSING_BASELINE>05.13</PROCESSING_BASELINE>"
               "<SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT>"
               "<SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX>"
               "<BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>"
               + "".join(f'<BOA_ADD_OFFSET band_id="{index}">-1000</BOA_ADD_OFFSET>'
                         for index in range(13)) + "</Product>")
        for role, pattern in ROLE_PATTERNS.items():
            relative = pattern.replace("*", "GENERATED")
            path = safe / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if role in {"metadata_product", "metadata_tile"}:
                path.write_text(xml if role == "metadata_product" else "<Tile/>", encoding="utf-8")
            else:
                cell = 60.0 if role == "quality_classification" else (
                    10.0 if role in {"B02", "B03", "B04", "B08"} else 20.0)
                size = int(1200 / cell)
                bands = 3 if role == "quality_classification" else 1
                dtype = np.uint8 if role in {"quality_classification", "SCL"} else np.uint16
                value = 0 if role == "quality_classification" else (4 if role == "SCL" else 1500)
                make_jp2(path, np.full((bands, size, size), value, dtype=dtype),
                         cell_size=cell)
            contents = path.read_bytes()
            manifest_files.append({"relative_path": relative,
                                   "size_bytes": len(contents),
                                   "sha256": hashlib.sha256(contents).hexdigest()})
        (materialization / "materialization-manifest.json").write_text(
            json.dumps({"status": "complete", "files": manifest_files}), encoding="utf-8")
        observed, selected = inspect_materialized("M2-OPT-003", materialization)
        contract = json.loads((Path(__file__).resolve().parents[1]
                               / "config/qa/optical-input-readiness-contract.json").read_text())
        if (observed["metadata"]["processing_baseline"] != "05.13"
                or validate_product_grid(observed["descriptions"], contract)
                or len(selected) != 10):
            raise RuntimeError("disposable_pb0513_safe_header_invalid")
        scl = np.full((1, 64, 64), 4, dtype=np.uint8)
        quality = np.zeros((3, 64, 64), dtype=np.uint8)
        b11 = np.full((1, 64, 64), 200, dtype=np.uint16)
        scl[0, :8, :] = 3
        quality[0, 10, 10] = 1
        b11[0, 11, 11] = 0
        paths = {role: root / f"generated-{role}.jp2" for role in
                 ("SCL", "quality_classification", "B11")}
        for role, values in (("SCL", scl), ("quality_classification", quality),
                             ("B11", b11)):
            make_jp2(paths[role], values)
            header = describe(paths[role])
            if header["wkid"] != 32645 or header["width"] != 64 or header["height"] != 64:
                raise RuntimeError("disposable_jp2_header_invalid")
        arrays = {role: warp_target(paths[role], role, GRID) for role in paths}
        mask = single_date_usable_mask(arrays["SCL"], arrays["quality_classification"],
                                       arrays["B11"])
        first = np.zeros((64, 64), dtype=bool)
        second = np.zeros((64, 64), dtype=bool)
        first[8:32, :] = True
        second[32:64, :] = True
        result = decide_before_screen(mask, {"AOI-SOURCE": first,
                                             "AOI-UPPER-CORRIDOR": second})
        if result["status"] != "pass_acquisition_prerequisite_only":
            raise RuntimeError("disposable_mask_screen_failed")
        if not arcpy.Exists(str(paths["SCL"])):
            raise RuntimeError("arcgis_disposable_jp2_unreadable")
        for role, value in (("B04", 1400), ("B03", 1500), ("B02", 1600)):
            path = root / f"generated-{role}.jp2"
            make_jp2(path, np.full((1, 128, 128), value, dtype=np.uint16),
                     cell_size=10.0)
            paths[role] = path
        display_inputs = []
        for name in ("before", "after"):
            path = root / f"generated-{name}-masked.tif"
            metadata = {"quantification_value": 10000,
                        "offsets_by_band": {role: -1000 for role in display.RGB_ROLES}}
            with patch.object(display, "TARGET_GRID", GRID):
                generated = display.make_masked_display(paths, metadata, path, grid=GRID)
            if generated["status"] != "local_masked_visual_only":
                raise RuntimeError("disposable_masked_rgb_failed")
            display_inputs.append(path)
        map_root = root / "local-visual"
        built = build_local_map(display_inputs[0], display_inputs[1], map_root,
                                aoi_id="AOI-SOURCE", before_usable_fraction=.92,
                                after_usable_fraction=.88)
        command = [sys.executable, "-c",
                   "import json,sys; sys.path.insert(0,'scripts'); "
                   "from pathlib import Path; "
                   "from m2_optical_alternate_pair_002_map import verify_reopen; "
                   "print(json.dumps(verify_reopen(Path(sys.argv[1]))))", str(map_root)]
        reopened = subprocess.run(command, cwd=Path(__file__).resolve().parents[1],
                                  capture_output=True, text=True, timeout=120, check=False)
        if reopened.returncode != 0:
            raise RuntimeError("disposable_arcgis_map_fresh_reopen_failed")
        reopen_receipt = json.loads(reopened.stdout)
        if (reopen_receipt["status"] != "pass_same_machine_local_arcgis_reopen_export"
                or reopen_receipt["broken_layers"] != 0
                or not reopen_receipt["pixel_identical_exports"]):
            raise RuntimeError("disposable_arcgis_map_export_not_stable")
        return {"status": "pass_disposable_arcgis_gdal_candidate_smoke",
                "arcgis_version": "3.7.1", "grid_wkid": 32645,
                "generated_pb0513_safe_member_count": len(selected),
                "generated_pb0513_product_grid_valid": True,
                "generated_jp2_roles": sorted(paths),
                "target_aoi_usable_fractions": {
                    key: item["usable_fraction_of_aoi"]
                    for key, item in result["aoi_results"].items()},
                "local_visual_map": {"build_status": built["status"],
                                     "reopen_status": reopen_receipt["status"],
                                     "pixel_identical_exports": True},
                "project_data_access": False, "protected_pixel_access": False,
                "network_or_credential_action": False}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
