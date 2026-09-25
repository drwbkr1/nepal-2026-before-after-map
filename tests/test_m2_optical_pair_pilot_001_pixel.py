"""The new attempt changes source binding, not frozen optical QA predicates."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_optical_pair_pilot_001_core import PilotControlError  # noqa: E402
from m2_optical_pair_pilot_001_pixel import frozen_execution_contract  # noqa: E402


class OpticalPilotPixelTests(unittest.TestCase):
    def test_only_pair_and_attempt_are_rebound(self) -> None:
        original = json.loads((ROOT / "config/qa/optical-pixel-readiness-contract-001.json").read_text(encoding="utf-8"))
        rebound = frozen_execution_contract(["M2-OPT-001", "M2-OPT-002"])
        for section in ("analysis_grid", "mask", "registration", "approved_aoi_ids", "decision_domain", "claim_boundary"):
            if section == "analysis_grid":
                self.assertEqual(rebound[section]["extent"], original[section]["extent"])
                self.assertEqual(rebound[section]["cell_size_m"], 20.0)
                self.assertEqual((rebound[section]["rows"], rebound[section]["columns"]), (3950, 4726))
            else:
                self.assertEqual(rebound[section], original[section])
        self.assertEqual(rebound["exact_pair"]["before_source_id"], "M2-OPT-001")
        self.assertEqual(rebound["exact_pair"]["after_source_id"], "M2-OPT-002")
        self.assertFalse(rebound["attempt"]["automatic_retry_authorized"])

    def test_source_substitution_rejected(self) -> None:
        with self.assertRaisesRegex(PilotControlError, "pilot_pixel_pair_order_drift"):
            frozen_execution_contract(["M1-SRC-010", "M2-OPT-002"])


if __name__ == "__main__":
    unittest.main()
