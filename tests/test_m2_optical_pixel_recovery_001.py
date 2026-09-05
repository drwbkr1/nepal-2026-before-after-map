from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import optical_pixel_recovery_core_001 as CORE  # noqa: E402
from run_m2_optical_pixel_readiness_recovery_001 import normalized_execution_contract  # noqa: E402


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class OpticalPixelRecovery001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load("config/qa/optical-pixel-readiness-contract-001.json")
        cls.recovery = load("config/qa/optical-pixel-readiness-contract-recovery-001.json")

    def test_exact_recovery_contract_is_valid(self):
        self.assertEqual(CORE.validate_recovery_contract(self.recovery, self.original), [])

    def test_nested_production_extent_is_normalized(self):
        grid = self.original["analysis_grid"]
        self.assertNotIn("xmin", grid)
        normalized = CORE.normalize_analysis_grid(grid)
        self.assertEqual(normalized["xmin"], grid["extent"]["xmin"])
        self.assertEqual(normalized["ymin"], grid["extent"]["ymin"])
        self.assertEqual(normalized["xmax"], grid["extent"]["xmax"])
        self.assertEqual(normalized["ymax"], grid["extent"]["ymax"])

    def test_normalization_does_not_mutate_contract(self):
        grid = copy.deepcopy(self.original["analysis_grid"])
        before = copy.deepcopy(grid)
        CORE.normalize_analysis_grid(grid)
        self.assertEqual(grid, before)

    def test_conflicting_flat_bound_is_rejected(self):
        grid = copy.deepcopy(self.original["analysis_grid"])
        grid["xmin"] = grid["extent"]["xmin"] + 20.0
        with self.assertRaisesRegex(ValueError, "conflicts"):
            CORE.normalize_analysis_grid(grid)

    def test_missing_nested_extent_is_rejected(self):
        grid = copy.deepcopy(self.original["analysis_grid"])
        del grid["extent"]
        with self.assertRaisesRegex(ValueError, "extent"):
            CORE.normalize_analysis_grid(grid)

    def test_execution_copy_changes_only_operational_grid_shape(self):
        normalized = normalized_execution_contract(self.recovery)
        for key in self.recovery:
            if key != "analysis_grid":
                self.assertEqual(normalized[key], self.recovery[key])
        expected = copy.deepcopy(self.recovery["analysis_grid"])
        expected.update(expected["extent"])
        self.assertEqual(normalized["analysis_grid"], expected)

    def test_scientific_sections_are_byte_for_byte_structurally_equal(self):
        for key in ("inputs", "exact_pair", "approved_aoi_ids", "products", "analysis_grid", "mask", "registration", "execution_boundary", "decision_domain", "claim_boundary"):
            self.assertEqual(self.recovery[key], self.original[key])

    def test_real_001_and_approval_are_exactly_bound(self):
        self.assertEqual(sha256(CORE.REAL_001_RECEIPT_REF), CORE.REAL_001_RECEIPT_SHA256)
        self.assertEqual(sha256(CORE.REAL_001_RECONCILIATION_REF), CORE.REAL_001_RECONCILIATION_SHA256)
        self.assertEqual(sha256(CORE.APPROVAL_REF), CORE.APPROVAL_SHA256)
        self.assertFalse(self.recovery["attempt"]["automatic_retry_authorized"])

    def test_operational_review_contract_corrections_do_not_change_decision_fields(self):
        original = load("reviews/m2-optical-pixel-recovery-001/review-contract.json")
        corrected = load("reviews/m2-optical-pixel-recovery-001/review-contract-lock-002.json")
        self.assertEqual(corrected["hash_prefix_length"], 16)
        self.assertEqual(corrected["workflow_authority"]["post_review_actions"], corrected["workflow_authority"]["authorized_action_classes"])
        for key in ("review_id", "response_schema_version", "review_bundle", "allowed_decisions", "required_attestation", "max_notes_length", "items"):
            self.assertEqual(corrected[key], original[key])

    def test_runner_retains_scientific_prohibitions(self):
        text = (ROOT / "scripts/run_m2_optical_pixel_readiness_recovery_001.py").read_text(encoding="utf-8")
        self.assertNotIn("NDVI", text)
        self.assertNotIn("MNDWI", text)
        self.assertNotIn("NBR", text)
        self.assertIn('"automatic_retry_authorized": False', text)
        self.assertIn('"real_001_reused_or_retried": False', text)


if __name__ == "__main__":
    unittest.main()
