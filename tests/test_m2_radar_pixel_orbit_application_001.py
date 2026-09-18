from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_radar_pixel_orbit_application_001_core import (  # noqa: E402
    ROUTE_ORDER,
    SOURCE_ORDER,
    RadarRouteError,
    classify_radar_pair,
    copy_safe_exclusive,
    evaluate_route,
    evaluate_same_date_seam,
    execute_fixed_order,
    load_execution_plan,
    measure_stable_registration,
    stable_inventory,
    validate_contract,
)
import run_m2_radar_pixel_orbit_application_001 as runner  # noqa: E402


CONTRACT_REF = "config/qa/m2-radar-pixel-orbit-application-001-contract.json"
CONTRACT_SHA256 = "a25f86588979fd4b5cfb45c999a862d83d71be31925a5b39565970de526f8fb1"


class M2RadarPixelOrbitApplication001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / CONTRACT_REF).read_text(encoding="utf-8"))
        cls.pixel_contract = json.loads((ROOT / "config/qa/pixel-readiness-contract.json").read_text(encoding="utf-8"))

    def test_contract_is_exact_and_loads_repo_metadata_without_pixels(self) -> None:
        self.assertEqual(hashlib.sha256((ROOT / CONTRACT_REF).read_bytes()).hexdigest(), CONTRACT_SHA256)
        self.assertEqual(validate_contract(self.contract, ROOT), [])
        external_root = Path(self.contract["execution_boundary"]["external_data_root"])
        if external_root.is_dir():
            plan = load_execution_plan(ROOT, CONTRACT_REF)
            self.assertEqual([item["source_id"] for item in plan["sources"]], SOURCE_ORDER)
            self.assertEqual(sorted(plan["orbits"]), [f"M2-ORB-{index:03d}" for index in range(1, 5)])
            self.assertEqual([item["source_id"] for item in plan["dems"]], [f"M2-DEM-{index:03d}" for index in range(1, 5)])
        else:
            self.assertEqual(str(external_root), r"C:\Projects\Active\nepal-2026-before-after-map-data")
            self.assertEqual([item["source_id"] for item in self.contract["sources"]], SOURCE_ORDER)
            self.assertEqual([item["source_id"] for item in self.contract["orbits"]], [f"M2-ORB-{index:03d}" for index in range(1, 5)])
            self.assertEqual([item["source_id"] for item in self.contract["ellipsoidal_dem_inputs"]], [f"M2-DEM-{index:03d}" for index in range(1, 5)])

    def test_contract_preserves_attempt_and_scientific_boundaries(self) -> None:
        attempt = self.contract["attempt"]
        self.assertEqual(attempt["maximum_final_preflights"], 1)
        self.assertEqual(attempt["maximum_orbit_application_attempts_per_source"], 1)
        self.assertEqual(attempt["maximum_qa_processing_attempts_per_source"], 1)
        self.assertEqual(attempt["maximum_route_qa_attempts_per_pair"], 1)
        self.assertFalse(attempt["automatic_retry_authorized"])
        self.assertTrue(attempt["stop_on_first_source_execution_failure"])
        self.assertEqual(self.contract["fixed_route_order"], ROUTE_ORDER)
        self.assertTrue(all(value is False for value in self.contract["claim_boundary"].values()))
        self.assertEqual(
            {key: self.contract["execution_boundary"][key] for key in ("network_requests", "authentication", "source_overwrite", "output_overwrite", "automatic_retry")},
            {key: "prohibited" for key in ("network_requests", "authentication", "source_overwrite", "output_overwrite", "automatic_retry")},
        )

    def test_copy_is_exclusive_and_original_inventory_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.SAFE"
            (source / "measurement").mkdir(parents=True)
            (source / "manifest.safe").write_bytes(b"manifest")
            (source / "measurement" / "vv.tiff").write_bytes(b"pixels")
            before = stable_inventory(source)
            result = copy_safe_exclusive(source, root / "attempt" / "source.SAFE")
            self.assertEqual(stable_inventory(source), before)
            self.assertTrue(result["source_inventory_unchanged"])
            self.assertTrue(result["copied_inventory_matches_source"])
            with self.assertRaises(RadarRouteError) as caught:
                copy_safe_exclusive(source, root / "attempt" / "source.SAFE")
            self.assertEqual(caught.exception.code, "output_collision")

    def test_fixed_order_supervisor_stops_on_first_failure_without_retry(self) -> None:
        calls: list[str] = []

        def worker(source_id: str) -> dict:
            calls.append(source_id)
            if source_id == "M1-SRC-003":
                raise RadarRouteError("synthetic_interruption")
            return {"source_id": source_id, "status": "pass_source_qa_only"}

        result = execute_fixed_order(SOURCE_ORDER, worker)
        self.assertEqual(calls, SOURCE_ORDER[:3])
        self.assertEqual(result["stopped_source_id"], "M1-SRC-003")
        self.assertFalse(result["automatic_retry_performed"])
        self.assertEqual(result["completed_source_ids"], SOURCE_ORDER[:2])

    def test_mask_precedence_and_unknown_class_are_preserved(self) -> None:
        before = np.array([[1, 4, 3, 0, 9, 1]], dtype=np.int16)
        after = np.array([[2, 1, 1, 1, 1, 1]], dtype=np.int16)
        valid = np.ones(before.shape, dtype=bool)
        after_valid = valid.copy()
        after_valid[0, 5] = False
        result = classify_radar_pair(before, after, valid, after_valid)
        self.assertEqual(result["classes"].tolist(), [[1, 2, 3, 0, 90, 0]])
        self.assertTrue(result["unknown_native_class_present"])

    def test_synthetic_registration_and_route_qa_use_frozen_thresholds(self) -> None:
        rng = np.random.default_rng(20260918)
        before = rng.normal(1.0, 0.2, (180, 180)).astype(np.float64)
        after = before.copy()
        pair_valid = np.ones(before.shape, dtype=bool)
        settings = dict(self.contract["registration"])
        registration = measure_stable_registration(
            before,
            after,
            pair_valid,
            grid={"xmin": 300000.0, "ymax": 3101800.0, "cell_size_m": 10.0},
            overview_bbox=(300000.0, 3100000.0, 301800.0, 3101800.0),
            exclusion_bboxes=[],
            settings=settings,
            pixel_contract=self.pixel_contract,
        )
        self.assertEqual(registration["status"], "pass_qa_only")
        self.assertGreaterEqual(registration["accepted_control_count"], 30)
        self.assertLess(registration["rmse_pixels"], 0.01)
        grid = {
            "wkid": 32645,
            "cell_size_x": 10.0,
            "cell_size_y": 10.0,
            "origin_x": 300000.0,
            "origin_y": 3100000.0,
            "xmin": 300000.0,
            "ymin": 3100000.0,
            "xmax": 301800.0,
            "ymax": 3101800.0,
            "rotation_degrees": 0.0,
        }
        result = evaluate_route(
            route_id=ROUTE_ORDER[0],
            aoi_observations=[{
                "aoi_id": "AOI-OVERVIEW",
                "aoi_area_m2": 1000.0,
                "covered_area_m2": 1000.0,
                "valid_area_m2": 900.0,
                "excluded_area_by_reason_m2": {"layover": 100.0},
            }],
            before_grid=grid,
            after_grid=dict(grid),
            registration=registration,
            seam_observations=[evaluate_same_date_seam(before, after, pair_valid)],
            pixel_contract=self.pixel_contract,
            unknown_mask_class_present=False,
        )
        self.assertEqual(result["status"], "pass_qa_only")
        self.assertFalse(result["baseline_admission_authorized"])
        self.assertFalse(result["change_analysis_authorized"])
        self.assertFalse(result["scientific_admission_authorized"])

    def test_no_network_library_is_imported_by_implementation(self) -> None:
        imports = set()
        for relative in (
            "scripts/m2_radar_pixel_orbit_application_001_core.py",
            "scripts/run_m2_radar_pixel_orbit_application_001.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
        self.assertTrue({"requests", "urllib", "http", "socket", "ftplib"}.isdisjoint(imports))

    def test_publication_gate_refuses_before_any_project_path_read(self) -> None:
        with tempfile.TemporaryDirectory() as raw, patch.object(runner, "ROOT", Path(raw)):
            with self.assertRaises(RadarRouteError) as caught:
                runner.publication_gate()
        self.assertEqual(caught.exception.code, "implementation_publication_gate_missing")

    def test_arcgis_geoprocessing_calls_bind_required_output_arguments(self) -> None:
        tree = ast.parse((ROOT / "scripts/run_m2_radar_pixel_orbit_application_001.py").read_text(encoding="utf-8"))
        expected_counts = {
            "RemoveThermalNoise": 3,
            "ApplyRadiometricCalibration": 4,
            "ApplyRadiometricTerrainFlattening": 9,
            "ApplyGeometricTerrainCorrection": 5,
            "ConvertSARUnits": 3,
        }
        observed: dict[str, list[int]] = {key: [] for key in expected_counts}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            name = node.func.attr
            if name in observed:
                observed[name].append(len(node.args))
        for name, count in expected_counts.items():
            self.assertTrue(observed[name], name)
            self.assertTrue(all(item == count for item in observed[name]), (name, observed[name]))

    def test_attempt_and_source_receipts_are_reserved_before_content_access(self) -> None:
        tree = ast.parse((ROOT / "scripts/run_m2_radar_pixel_orbit_application_001.py").read_text(encoding="utf-8"))
        functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        source_calls = [node for node in ast.walk(functions["process_source"]) if isinstance(node, ast.Call)]
        source_write = min(node.lineno for node in source_calls if isinstance(node.func, ast.Name) and node.func.id == "write_new_json")
        source_copy = min(node.lineno for node in source_calls if isinstance(node.func, ast.Name) and node.func.id == "copy_safe_exclusive")
        self.assertLess(source_write, source_copy)
        execute_calls = [node for node in ast.walk(functions["run_execute"]) if isinstance(node, ast.Call)]
        attempt_write = min(node.lineno for node in execute_calls if isinstance(node.func, ast.Name) and node.func.id == "write_new_json")
        identity_read = min(node.lineno for node in execute_calls if isinstance(node.func, ast.Name) and node.func.id == "verify_external_identities")
        self.assertLess(attempt_write, identity_read)

    def test_production_route_uses_bounded_windows_not_full_scene_numpy_reads(self) -> None:
        source = (ROOT / "scripts/run_m2_radar_pixel_orbit_application_001.py").read_text(encoding="utf-8")
        self.assertIn("measure_stable_registration_windowed", source)
        self.assertIn("evaluate_same_date_seam_windowed", source)
        self.assertNotIn("def raster_array(", source)


if __name__ == "__main__":
    unittest.main()
