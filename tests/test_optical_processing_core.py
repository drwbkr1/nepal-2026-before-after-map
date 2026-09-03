from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "optical_processing_core", ROOT / "scripts/optical_processing_core.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_optical_processing_contract as PREPARE  # noqa: E402

CONTRACT = json.loads(
    (ROOT / "config/qa/optical-baseline-processing-contract.json").read_text(encoding="utf-8")
)


def synthetic_metadata_xml(
    missing_band_id: int | None = None,
    duplicate_band_id: int | None = None,
) -> str:
    offsets = "".join(
        f'<BOA_ADD_OFFSET band_id="{band_id}">-1000</BOA_ADD_OFFSET>'
        for band_id in range(13)
        if band_id != missing_band_id
    )
    if duplicate_band_id is not None:
        offsets += f'<BOA_ADD_OFFSET band_id="{duplicate_band_id}">-999</BOA_ADD_OFFSET>'
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Level2A_User_Product xmlns="urn:synthetic:sentinel2">
  <General_Info>
    <Product_Info><PROCESSING_BASELINE>05.12</PROCESSING_BASELINE></Product_Info>
    <Product_Image_Characteristics>
      <Special_Values><SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT><SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX></Special_Values>
      <BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>
      <BOA_ADD_OFFSET_VALUES_LIST>{offsets}</BOA_ADD_OFFSET_VALUES_LIST>
    </Product_Image_Characteristics>
  </General_Info>
</Level2A_User_Product>"""


class OpticalProcessingCoreTests(unittest.TestCase):
    def complete_observation(self) -> dict:
        return {
            "verified_source_ids": ["M1-SRC-010", "M1-SRC-008"],
            "metadata_by_source": {
                source_id: {
                    "processing_baseline": "05.12",
                    "source_crs_wkid": 32645,
                    "offset_bands": sorted(MODULE.REQUIRED_CHANGE_BANDS),
                    "quantification_value": 10000,
                }
                for source_id in ("M1-SRC-010", "M1-SRC-008")
            },
            "pixel_readiness_status": "pass_qa_only",
            "registration_status": "pass_qa_only",
        }

    def test_contract_is_predeclared_and_valid(self) -> None:
        self.assertEqual(MODULE.validate_contract(CONTRACT), [])
        self.assertFalse(CONTRACT["claim_boundary"]["real_product_pixels_examined"])

    def test_contract_is_deterministically_derived(self) -> None:
        self.assertEqual(PREPARE.build_contract(CONTRACT["created_at_utc"]), CONTRACT)

    def test_product_name_processing_baseline(self) -> None:
        self.assertEqual(
            MODULE.processing_baseline_from_product_id(CONTRACT["route"]["before_product_id"]),
            "05.12",
        )
        self.assertEqual(
            MODULE.processing_baseline_from_product_id(CONTRACT["route"]["after_product_id"]),
            "05.12",
        )
        self.assertIsNone(MODULE.processing_baseline_from_product_id("not-a-product"))

    def test_parse_scaling_metadata(self) -> None:
        parsed = MODULE.parse_l2a_scaling_metadata(synthetic_metadata_xml())
        self.assertEqual(parsed["processing_baseline"], "05.12")
        self.assertEqual(parsed["quantification_value"], 10000)
        self.assertEqual(parsed["offsets_by_band"]["B04"], -1000)
        self.assertEqual(parsed["special_values"]["NODATA"], 0)
        self.assertEqual(parsed["errors"], [])

    def test_missing_required_offset_is_detected(self) -> None:
        parsed = MODULE.parse_l2a_scaling_metadata(synthetic_metadata_xml(missing_band_id=3))
        self.assertTrue(any("B04" in error for error in parsed["errors"]))

    def test_duplicate_offset_is_detected(self) -> None:
        parsed = MODULE.parse_l2a_scaling_metadata(synthetic_metadata_xml(duplicate_band_id=3))
        self.assertTrue(any("duplicate" in error and "B04" in error for error in parsed["errors"]))

    def test_reflectance_scaling_preserves_nodata_and_negative_values(self) -> None:
        self.assertIsNone(MODULE.scale_reflectance_dn(0, -1000, 10000))
        self.assertAlmostEqual(MODULE.scale_reflectance_dn(3000, -1000, 10000), 0.2)
        self.assertAlmostEqual(MODULE.scale_reflectance_dn(500, -1000, 10000), -0.05)

    def test_normalized_difference_and_small_denominator(self) -> None:
        self.assertAlmostEqual(MODULE.normalized_difference(0.4, 0.2, 1e-6), 1 / 3)
        self.assertIsNone(MODULE.normalized_difference(0.0000002, -0.0000002, 1e-6))
        self.assertIsNone(MODULE.normalized_difference(None, 0.2, 1e-6))

    def test_scl_policy_is_conservative(self) -> None:
        self.assertEqual(MODULE.classify_scl(4, CONTRACT)["status"], "valid")
        self.assertEqual(MODULE.classify_scl(9, CONTRACT)["status"], "excluded")
        self.assertEqual(MODULE.classify_scl(12, CONTRACT)["status"], "defer")

    def test_current_no_pixel_state_defers(self) -> None:
        result = MODULE.evaluate_readiness(CONTRACT, {})
        self.assertEqual(result["status"], "defer")
        self.assertFalse(result["scientific_admission_authorized"])
        self.assertFalse(result["change_established"])

    def test_exact_complete_inputs_can_be_processing_ready(self) -> None:
        result = MODULE.evaluate_readiness(CONTRACT, self.complete_observation())
        self.assertEqual(result["status"], "ready_for_controlled_processing")
        self.assertEqual(result["reasons"], [])

    def test_internal_baseline_mismatch_blocks(self) -> None:
        observed = self.complete_observation()
        observed["metadata_by_source"]["M1-SRC-008"]["processing_baseline"] = "05.11"
        result = MODULE.evaluate_readiness(CONTRACT, observed)
        self.assertEqual(result["status"], "block")
        self.assertTrue(any("baseline" in reason for reason in result["reasons"]))

    def test_extra_source_is_invalid(self) -> None:
        observed = self.complete_observation()
        observed["verified_source_ids"].append("M1-SRC-007")
        result = MODULE.evaluate_readiness(CONTRACT, observed)
        self.assertEqual(result["status"], "invalid")

    def test_arcgis_synthetic_receipt_binds_code_and_contract(self) -> None:
        receipt = json.loads(
            (ROOT / "records/surface-receipts/optical-processing-synthetic-arcgis.json").read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["status"], "pass_synthetic_only")
        self.assertEqual(receipt["runtime"]["version"], "3.7.1")
        self.assertEqual({item["status"] for item in receipt["checks"].values()}, {"pass"})
        for ref_key, hash_key in (
            ("contract", "contract_sha256"),
            ("core", "core_sha256"),
            ("arcgis_adapter", "arcgis_adapter_sha256"),
        ):
            path = ROOT / receipt["inputs"][ref_key]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), receipt["inputs"][hash_key])

    def test_arcgis_synthetic_receipt_preserves_claim_boundary(self) -> None:
        receipt = json.loads(
            (ROOT / "records/surface-receipts/optical-processing-synthetic-arcgis.json").read_text(encoding="utf-8")
        )
        assertions = receipt["assertions"]
        self.assertTrue(assertions["dn_zero_preserved_as_nodata"])
        self.assertTrue(assertions["excluded_scl_preserved_as_nodata"])
        self.assertFalse(assertions["real_product_metadata_parsed"])
        self.assertFalse(assertions["real_product_pixels_examined"])
        self.assertFalse(assertions["optical_baseline_established"])
        self.assertFalse(assertions["change_established"])
        self.assertFalse(assertions["scientific_admission_authorized"])


if __name__ == "__main__":
    unittest.main()
