from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CORE_SPEC = importlib.util.spec_from_file_location(
    "optical_input_readiness_core", ROOT / "scripts/optical_input_readiness_core.py"
)
assert CORE_SPEC and CORE_SPEC.loader
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PREP_SPEC = importlib.util.spec_from_file_location(
    "prepare_optical_input_readiness_contract",
    ROOT / "scripts/prepare_optical_input_readiness_contract.py",
)
assert PREP_SPEC and PREP_SPEC.loader
PREP = importlib.util.module_from_spec(PREP_SPEC)
PREP_SPEC.loader.exec_module(PREP)

CREATED_AT = "2026-09-03T19:37:30Z"
CONTRACT_PATH = ROOT / "config/qa/optical-input-readiness-contract.json"


def manifest_member_paths() -> dict[str, str]:
    return {
        "metadata_product": "MTD_MSIL2A.xml",
        "metadata_tile": "GRANULE/G/MTD_TL.xml",
        "B02": "GRANULE/G/IMG_DATA/R10m/T_B02_10m.jp2",
        "B03": "GRANULE/G/IMG_DATA/R10m/T_B03_10m.jp2",
        "B04": "GRANULE/G/IMG_DATA/R10m/T_B04_10m.jp2",
        "B08": "GRANULE/G/IMG_DATA/R10m/T_B08_10m.jp2",
        "B11": "GRANULE/G/IMG_DATA/R20m/T_B11_20m.jp2",
        "B12": "GRANULE/G/IMG_DATA/R20m/T_B12_20m.jp2",
        "SCL": "GRANULE/G/IMG_DATA/R20m/T_SCL_20m.jp2",
        "quality_classification": "GRANULE/G/QI_DATA/MSK_CLASSI_B00.jp2",
    }


def complete_manifest() -> dict:
    paths = manifest_member_paths()
    return {
        "status": "complete",
        "files": [
            {"relative_path": path, "size_bytes": 10, "sha256": "a" * 64}
            for path in paths.values()
        ],
    }


def complete_descriptions() -> dict[str, dict]:
    descriptions = {}
    for role in CORE.RASTER_ROLES:
        cell = 10.0 if role in CORE.TEN_METRE_ROLES else (20.0 if role in CORE.TWENTY_METRE_ROLES else 60.0)
        descriptions[role] = {
            "format": "JP2",
            "wkid": 32645,
            "band_count": 3 if role == "quality_classification" else 1,
            "width": int(120 / cell),
            "height": int(120 / cell),
            "cell_width": cell,
            "cell_height": cell,
            "pixel_type": "U8" if role in {"SCL", "quality_classification"} else "U16",
            "xmin": 273300.0,
            "ymin": 3070220.0,
            "xmax": 273420.0,
            "ymax": 3070340.0,
        }
        if role == "quality_classification":
            descriptions[role]["band_details"] = [
                {
                    "name": f"Band_{index}",
                    "width": 2,
                    "height": 2,
                    "cell_width": 60.0,
                    "cell_height": 60.0,
                    "pixel_type": "U8",
                }
                for index in (1, 2, 3)
            ]
    return descriptions


class OpticalInputReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_tracked_contract_is_deterministic_and_valid(self) -> None:
        self.assertEqual(self.contract, PREP.build_contract(CREATED_AT))
        self.assertEqual(CORE.validate_contract(self.contract), [])

    def test_contract_preserves_exact_pair_and_claim_boundary(self) -> None:
        self.assertEqual(self.contract["route"]["before_source_id"], "M1-SRC-010")
        self.assertEqual(self.contract["route"]["after_source_id"], "M1-SRC-008")
        self.assertEqual(self.contract["route"]["processing_baseline"], "05.12")
        self.assertEqual(self.contract["analysis_crs"]["wkid"], 32645)
        self.assertTrue(self.contract["header_checks"]["extent_must_equal_dimensions_times_cell_size"])
        self.assertEqual(self.contract["header_checks"]["quality_classification"]["band_count"], 3)
        self.assertEqual(self.contract["header_checks"]["quality_classification"]["cell_size_m"], 60.0)
        self.assertFalse(self.contract["claim_boundary"]["pixel_values_examined"])
        self.assertFalse(self.contract["claim_boundary"]["change_established"])

    def test_contract_binds_current_execution_files(self) -> None:
        for ref_key, hash_key in (
            ("core_ref", "core_sha256"),
            ("runner_ref", "runner_sha256"),
            ("arcgis_adapter_ref", "arcgis_adapter_sha256"),
        ):
            path = ROOT / self.contract["inputs"][ref_key]
            self.assertEqual(self.contract["inputs"][hash_key], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_complete_inventory_selects_exactly_ten_roles(self) -> None:
        result = CORE.select_required_members(complete_manifest(), self.contract)
        self.assertEqual(result["status"], "pass_inventory_only")
        self.assertEqual(set(result["members"]), set(CORE.ROLE_PATTERNS))

    def test_missing_or_duplicate_required_member_blocks(self) -> None:
        missing = complete_manifest()
        missing["files"] = missing["files"][:-1]
        self.assertEqual(CORE.select_required_members(missing, self.contract)["status"], "block")
        duplicate = complete_manifest()
        duplicate["files"].append(copy.deepcopy(duplicate["files"][0]))
        result = CORE.select_required_members(duplicate, self.contract)
        self.assertEqual(result["status"], "block")
        self.assertTrue(any("duplicate" in error for error in result["errors"]))

    def test_unsafe_or_empty_manifest_member_blocks(self) -> None:
        manifest = complete_manifest()
        manifest["files"][0]["relative_path"] = "../MTD_MSIL2A.xml"
        manifest["files"][1]["size_bytes"] = 0
        manifest["files"][2]["sha256"] = "z" * 64
        result = CORE.select_required_members(manifest, self.contract)
        self.assertEqual(result["status"], "block")
        self.assertTrue(any("unsafe" in error for error in result["errors"]))
        self.assertTrue(any("empty" in error for error in result["errors"]))
        self.assertTrue(any("SHA-256" in error for error in result["errors"]))

    def test_valid_product_grid_passes(self) -> None:
        self.assertEqual(CORE.validate_product_grid(complete_descriptions(), self.contract), [])

    def test_wrong_crs_cell_or_pixel_type_blocks(self) -> None:
        descriptions = complete_descriptions()
        descriptions["B04"]["wkid"] = 4326
        descriptions["B08"]["cell_width"] = None
        descriptions["B11"]["pixel_type"] = "F32"
        descriptions["B03"]["xmax"] += 1
        descriptions["quality_classification"]["band_count"] = 1
        descriptions["quality_classification"]["band_details"][1]["cell_width"] = 20.0
        descriptions["quality_classification"]["cell_height"] = -20
        errors = CORE.validate_product_grid(descriptions, self.contract)
        self.assertTrue(any("B04 CRS" in error for error in errors))
        self.assertTrue(any("B08 cell width" in error for error in errors))
        self.assertTrue(any("B11 pixel type" in error for error in errors))
        self.assertTrue(any("B03 width, cell size, and x extent are inconsistent" in error for error in errors))
        self.assertTrue(any("quality_classification band count differs from 3" in error for error in errors))
        self.assertTrue(any("Band_2 differs from the shared cell_width" in error for error in errors))
        self.assertTrue(any("quality_classification cell height is invalid" in error for error in errors))

    def test_within_product_extent_mismatch_blocks(self) -> None:
        descriptions = complete_descriptions()
        descriptions["B12"]["xmin"] += 20
        descriptions["B12"]["xmax"] += 20
        errors = CORE.validate_product_grid(descriptions, self.contract)
        self.assertTrue(any("B12 extent differs" in error for error in errors))

    def test_aligned_pair_passes_and_shifted_pair_blocks(self) -> None:
        before = complete_descriptions()
        after = copy.deepcopy(before)
        self.assertEqual(CORE.validate_pair_grids(before, after, self.contract), [])
        for role in CORE.RASTER_ROLES:
            after[role]["xmin"] += 10
            after[role]["xmax"] += 10
        errors = CORE.validate_pair_grids(before, after, self.contract)
        self.assertTrue(any("before/after B02" in error for error in errors))

    def test_decision_passes_headers_only_or_blocks(self) -> None:
        passed = CORE.decide_header_readiness(
            {"before": "pass_inventory_only", "after": "pass_inventory_only"},
            {"before": [], "after": []},
            [],
        )
        self.assertEqual(passed["status"], "pass_header_readability_only")
        self.assertFalse(passed["pixel_values_examined"])
        blocked = CORE.decide_header_readiness(
            {"before": "block", "after": "pass_inventory_only"},
            {"before": ["metadata error"], "after": []},
            ["grid error"],
        )
        self.assertEqual(blocked["status"], "block")
        self.assertEqual(len(blocked["reasons"]), 3)

    def test_production_runner_refuses_missing_materialization_receipts_before_arcpy(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/inspect_optical_inputs_arcgis.py"),
                "--before-materialization-receipt",
                "records/acquisition/materialization/missing-before.json",
                "--after-materialization-receipt",
                "records/acquisition/materialization/missing-after.json",
                "--checked-at-utc",
                "2026-09-03T19:11:00Z",
                "--receipt-output",
                "records/readiness/optical-input/must-not-exist.json",
            ],
            cwd=ROOT,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 12)
        self.assertEqual(json.loads(result.stdout)["code"], "materialization_receipt_missing")
        self.assertFalse((ROOT / "records/readiness/optical-input/must-not-exist.json").exists())


if __name__ == "__main__":
    unittest.main()
