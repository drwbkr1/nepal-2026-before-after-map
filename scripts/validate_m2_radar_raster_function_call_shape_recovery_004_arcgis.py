#!/usr/bin/env python3
"""Validate six ArcPy Image Analyst interfaces without invoking a raster function."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import m2_radar_pixel_orbit_application_001_core as base

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_REF = "records/readiness/m2-radar-raster-function-call-shape-recovery-004-arcgis-runtime-validation.json"
EXPECTED_PARAMETERS = {
    "ApplyOrbitCorrection": ["in_radar_data", "in_orbit_file", "folder"],
    "RemoveThermalNoise": ["in_radar_data", "polarization_bands"],
    "ApplyRadiometricCalibration": ["in_radar_data", "polarization_bands", "calibration_type"],
    "ApplyRadiometricTerrainFlattening": [
        "in_radar_data", "in_dem_raster", "geoid", "polarization_bands", "calibration_type",
        "out_scattering_area", "out_geometric_distortion", "out_geometric_distortion_mask",
    ],
    "ApplyGeometricTerrainCorrection": ["in_radar_data", "polarization_bands", "in_dem_raster", "geoid"],
    "ConvertSARUnits": ["in_radar_data", "conversion_type"],
}
RASTER_RETURNING = {
    "RemoveThermalNoise", "ApplyRadiometricCalibration", "ApplyRadiometricTerrainFlattening",
    "ApplyGeometricTerrainCorrection", "ConvertSARUnits",
}



def main() -> int:
    import arcpy

    output = ROOT / OUTPUT_REF
    if output.exists():
        raise SystemExit("ArcGIS runtime validation output collision")
    observed = {}
    observed_parameters = {}
    raster_returning = {}
    docs_present = {}
    for name, expected in EXPECTED_PARAMETERS.items():
        target = getattr(arcpy.ia, name, None)
        if target is None or not callable(target):
            raise SystemExit(f"ArcPy interface unavailable: {name}")
        signature = inspect.signature(target)
        observed[name] = str(signature)
        observed_parameters[name] = list(signature.parameters)
        raster_returning[name] = "Raster" in str(signature.return_annotation)
        docs_present[name] = bool((inspect.getdoc(target) or "").strip())
    if observed_parameters != EXPECTED_PARAMETERS:
        raise SystemExit("Installed ArcPy interface parameter order differs from the approved exact set")
    if {name for name, returns_raster in raster_returning.items() if returns_raster} != RASTER_RETURNING:
        raise SystemExit("Installed ArcPy Raster-returning interface set differs from the approved exact set")
    if not all(docs_present.values()):
        raise SystemExit("Installed ArcPy interface documentation is unavailable")
    install = arcpy.GetInstallInfo()
    receipt = {
        "schema_version": "1.0",
        "record_id": "NEPAL-M2-RADAR-RASTER-FUNCTION-CALL-SHAPE-RECOVERY-004-ARCGIS-RUNTIME-VALIDATION",
        "status": "pass_installed_arcgis_runtime_six_interface_signature_only_validation",
        "runtime": {"product": install.get("ProductName"), "version": install.get("Version")},
        "expected_parameters": EXPECTED_PARAMETERS,
        "observed_parameters": observed_parameters,
        "observed_signatures": observed,
        "raster_returning": raster_returning,
        "documentation_present": docs_present,
        "assertions": {
            "signature_inspection_only": True,
            "project_data_content_read": False,
            "external_custody_accessed": False,
            "raster_function_invoked": False,
            "apply_orbit_correction_invoked": False,
            "geoprocessing_invoked": False,
            "extension_checked_out": False,
            "network_request_performed": False,
            "credential_value_read": False,
            "production_attempt_created": False,
            "scientific_result_established": False,
        },
    }
    base.write_new_json(output, receipt)
    print(json.dumps({"status": receipt["status"], "receipt": OUTPUT_REF}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
