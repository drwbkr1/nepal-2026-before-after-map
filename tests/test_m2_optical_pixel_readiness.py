from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import optical_pixel_readiness_core_001 as CORE  # noqa: E402
from pixel_qa_core import load_contract as load_pixel_contract  # noqa: E402


class OpticalPixelReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "config/qa/optical-pixel-readiness-contract-001.json").read_text(encoding="utf-8"))
        cls.pixel = load_pixel_contract(ROOT / "config/qa/pixel-readiness-contract.json")

    def test_contract_is_exact_and_valid(self):
        self.assertEqual(CORE.validate_contract(self.contract), [])
        self.assertEqual(self.contract["approved_aoi_ids"], ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"])
        self.assertEqual(self.contract["attempt"]["maximum_real_invocations"], 1)

    def test_contract_binds_unchanged_predeclared_inputs(self):
        for key in ("pixel_readiness", "optical_processing", "approved_aoi", "optical_header_receipt"):
            ref = self.contract["inputs"][f"{key}_ref"]
            self.assertEqual(hashlib.sha256((ROOT / ref).read_bytes()).hexdigest(), self.contract["inputs"][f"{key}_sha256"])

    def test_contract_binds_execution_files(self):
        for key in ("core", "runner", "stage_gate", "final_preflight", "publication_gate_recorder", "arcgis_adapter"):
            ref = self.contract["implementation"][f"{key}_ref"]
            self.assertEqual(hashlib.sha256((ROOT / ref).read_bytes()).hexdigest(), self.contract["implementation"][f"{key}_sha256"])

    def test_pair_classification_uses_conservative_precedence(self):
        before_scl = np.array([[4, 9, 4, 4, 4]], dtype=np.uint8)
        after_scl = np.array([[4, 4, 3, 4, 4]], dtype=np.uint8)
        quality = np.zeros((3, 1, 5), dtype=np.uint8)
        quality[0, 0, 3] = 1
        b11 = np.array([[100, 100, 100, 100, 0]], dtype=np.uint16)
        result = CORE.classify_pair_pixels(before_scl, after_scl, quality, quality, b11, np.full_like(b11, 100))
        self.assertEqual(result["classes"].tolist(), [[1, 109, 203, 300, 400]])

    def test_unknown_scl_is_retained_as_review_reason(self):
        scl = np.array([[12]], dtype=np.uint8)
        quality = np.zeros((3, 1, 1), dtype=np.uint8)
        b11 = np.array([[100]], dtype=np.uint16)
        result = CORE.classify_pair_pixels(scl, np.array([[4]], dtype=np.uint8), quality, quality, b11, b11)
        self.assertTrue(result["unknown_scl_present"])
        self.assertEqual(int(result["classes"][0, 0]), 190)

    def test_outside_coverage_remains_nodata(self):
        scl = np.array([[255]], dtype=np.uint8)
        quality = np.zeros((3, 1, 1), dtype=np.uint8)
        b11 = np.array([[100]], dtype=np.uint16)
        result = CORE.classify_pair_pixels(scl, scl, quality, quality, b11, b11)
        self.assertEqual(int(result["classes"][0, 0]), CORE.NODATA_CLASS)

    def test_aligned_textured_controls_pass(self):
        rng = np.random.default_rng(7)
        before = rng.normal(1000, 200, size=(180, 180))
        valid = np.ones_like(before, dtype=bool)
        settings = dict(self.contract["registration"])
        settings["candidate_grid_rows"] = 12
        settings["candidate_grid_columns"] = 12
        result = CORE.measure_stable_registration(before, before.copy(), valid, grid={"xmin": 0.0, "ymin": 0.0, "xmax": 3600.0, "ymax": 3600.0, "cell_size_m": 20.0}, overview_bbox=(0, 0, 3600, 3600), exclusion_bboxes=[], settings=settings, pixel_contract=self.pixel)
        self.assertEqual(result["status"], "pass_qa_only")
        self.assertGreaterEqual(result["accepted_control_count"], 30)

    def test_two_pixel_shift_blocks_registration(self):
        rng = np.random.default_rng(8)
        before = rng.normal(1000, 200, size=(180, 180))
        after = np.roll(before, 2, axis=1)
        valid = np.ones_like(before, dtype=bool)
        settings = dict(self.contract["registration"])
        settings["candidate_grid_rows"] = 12
        settings["candidate_grid_columns"] = 12
        result = CORE.measure_stable_registration(before, after, valid, grid={"xmin": 0.0, "ymin": 0.0, "xmax": 3600.0, "ymax": 3600.0, "cell_size_m": 20.0}, overview_bbox=(0, 0, 3600, 3600), exclusion_bboxes=[], settings=settings, pixel_contract=self.pixel)
        self.assertEqual(result["status"], "block")

    def test_final_decision_preserves_precedence(self):
        self.assertEqual(CORE.final_pixel_decision(["pass_qa_only", "defer"], "pass_qa_only", "pass_qa_only"), "defer")
        self.assertEqual(CORE.final_pixel_decision(["pass_qa_only"], "block", "defer"), "block")
        self.assertEqual(CORE.final_pixel_decision(["invalid"], "pass_qa_only", "pass_qa_only"), "invalid")

    def test_final_preflight_cannot_import_pixel_readers(self):
        text = (ROOT / "scripts/preflight_m2_optical_pixel_readiness.py").read_text(encoding="utf-8")
        self.assertNotIn("import arcpy", text)
        self.assertNotIn("RasterToNumPyArray", text)

    def test_real_runner_prohibits_indices_and_change_outputs(self):
        text = (ROOT / "scripts/run_m2_optical_pixel_readiness_001.py").read_text(encoding="utf-8")
        self.assertNotIn("NDVI", text)
        self.assertNotIn("MNDWI", text)
        self.assertNotIn("NBR", text)
        self.assertIn('"candidate_change_polygons_created": False', text)


if __name__ == "__main__":
    unittest.main()
