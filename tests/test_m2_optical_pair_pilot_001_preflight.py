"""No-payload preflight fails on terms, account, or API-route uncertainty."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from m2_optical_pair_pilot_001_core import PilotControlError  # noqa: E402
from m2_optical_pair_pilot_001_preflight import (  # noqa: E402
    DOCUMENT_ROUTE_MARKERS, evaluate_current_documentation, final_preflight,
)


class OpticalPilotPreflightTests(unittest.TestCase):
    def test_api_docs_layout_drift_is_bounded_to_exact_route_markers(self) -> None:
        for page_id, markers in DOCUMENT_ROUTE_MARKERS.items():
            item = {"page_id": page_id, "url": "https://example.invalid", "sha256": "0" * 64}
            body = ("<html>" + " ".join(markers) + "</html>").encode()
            observation = evaluate_current_documentation(item, body)
            self.assertTrue(observation["raw_page_changed"])
            self.assertFalse(observation["terms_or_legal_notice_equivalence_inferred"])
            with self.assertRaisesRegex(PilotControlError, "pilot_official_api_route_changed"):
                evaluate_current_documentation(item, b"<html>unrelated endpoint</html>")
        with self.assertRaisesRegex(PilotControlError, "pilot_official_access_or_terms_page_changed"):
            evaluate_current_documentation({"page_id": "terms-and-conditions"}, b"changed terms")

    def test_final_preflight_cannot_run_before_public_execution_gate(self) -> None:
        with patch("m2_optical_pair_pilot_001_preflight.load_contract", return_value={"status": "implementation_pending_no_real_attempt"}):
            with self.assertRaisesRegex(PilotControlError, "pilot_contract_not_activated"):
                final_preflight({"source_id": "M2-OPT-001"}, "fake", arcgis_runtime={"version": "3.7.1", "spatial": "Available"})


if __name__ == "__main__":
    unittest.main()
