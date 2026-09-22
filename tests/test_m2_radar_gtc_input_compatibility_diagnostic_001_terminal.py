import json
import unittest
from pathlib import Path

from scripts import m2_radar_gtc_input_compatibility_diagnostic_001 as diagnostic


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-gtc-input-compatibility-diagnostic-001"


class PublishedTerminalEvidenceTests(unittest.TestCase):
    def test_sanitized_terminal_claims_match_approved_scope(self):
        terminal = json.loads((ROOT / f"records/processing/{PREFIX}-terminal-reconciliation.json").read_text(encoding="utf-8"))
        outcome = json.loads((ROOT / f"records/processing/{PREFIX}-outcome-reconciliation.json").read_text(encoding="utf-8"))
        self.assertEqual(terminal["attempt_id"], diagnostic.ATTEMPT_ID)
        self.assertTrue(terminal["attempt_consumed"])
        self.assertEqual([item["candidate_ref"] for item in terminal["candidate_observations"]], list(diagnostic.CANDIDATES))
        self.assertTrue(all(item["arcgis_exists"] for item in terminal["candidate_observations"]))
        self.assertFalse(terminal["limitations"]["historical_failure_root_cause_established"])
        self.assertFalse(terminal["limitations"]["radar_recovery_readiness_established"])
        self.assertFalse(outcome["assertions"]["new_radar_processing_attempt_authorized"])
        self.assertNotIn(str(diagnostic.RECOVERY_ROOT), json.dumps(terminal))


if __name__ == "__main__":
    unittest.main()
