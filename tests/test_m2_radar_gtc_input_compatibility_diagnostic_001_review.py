import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "m2-radar-gtc-input-compatibility-diagnostic-001"


def load(ref):
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha(ref):
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class GtcInputCompatibilityDiagnosticReviewTests(unittest.TestCase):
    def test_zero_decision_packet_is_exact_and_nonexecuting(self):
        proposal_ref = "contracts/milestone-002-radar-gtc-input-compatibility-diagnostic-001-proposal.json"
        bundle_ref = f"reviews/{PREFIX}/review-bundle.json"
        contract = load(f"reviews/{PREFIX}/review-contract.json")
        readiness = load(f"records/readiness/{PREFIX}-review-readiness.json")
        proposal = load(proposal_ref)
        bundle = load(bundle_ref)
        self.assertEqual(proposal["human_decision_count"], 0)
        self.assertEqual(bundle["human_decision_count"], 0)
        self.assertEqual(contract["proposal"]["sha256"], sha(proposal_ref))
        self.assertEqual(contract["review_bundle"]["sha256"], sha(bundle_ref))
        envelope = proposal["proposed_single_authority_envelope"]
        self.assertEqual(envelope["maximum_diagnostic_processes"], 1)
        self.assertEqual(envelope["maximum_geoprocessing_calls"], 0)
        self.assertEqual(envelope["maximum_raster_function_calls"], 0)
        self.assertEqual(envelope["maximum_pixel_reads"], 0)
        self.assertFalse(envelope["automatic_retry"])
        self.assertFalse(readiness["released_now"]["git_commit_or_push"])
        self.assertFalse(readiness["released_now"]["arcpy_invocation"])
        self.assertFalse(readiness["released_now"]["project_data_access"])

    def test_checkpoint_remains_terminal_review(self):
        expected = "M2-RADAR-ESRI-SEQUENCE-RECOVERY-005-TERMINAL-REVIEW"
        self.assertEqual(load("contracts/milestone-002.json")["handoff"]["current_checkpoint"], expected)
        self.assertEqual(load("records/project-control-profile.json")["current_checkpoint"]["checkpoint_id"], expected)
        self.assertEqual(load("records/long-term-goal.json")["current_checkpoint"], expected)


if __name__ == "__main__":
    unittest.main()
