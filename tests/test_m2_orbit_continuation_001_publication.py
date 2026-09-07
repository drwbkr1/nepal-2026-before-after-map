from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_orbit_continuation_001_implementation_pending,
    current_orbit_continuation_001_review_required,
    current_orbit_offline_verification_recovery_001_review_required,
    current_orbit_offline_verification_recovery_001_review_publication_pending,
    current_orbit_verify_implementation_pending,
)


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OrbitContinuation001PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = load("records/readiness/m2-orbit-continuation-001-review-publication-gate.json")
        cls.reconciliation = load("records/readiness/m2-orbit-continuation-001-review-publication-reconciliation.json")
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")
        cls.blank = load("reviews/m2-orbit-continuation-001/blank-response.json")

    def test_exact_public_ci_gate_matches_packet_commit(self) -> None:
        self.assertEqual(self.gate["status"], "pass_exact_blank_packet_public_ci_owner_review_ready")
        self.assertEqual(self.gate["github_actions"]["run_id"], 34062485694)
        self.assertEqual(self.gate["github_actions"]["head_sha"], "998fb415a04e531c71d4ea49b554168bb99b2095")
        self.assertEqual(self.gate["github_actions"]["conclusion"], "success")
        self.assertEqual(self.gate["bindings"]["proposal_sha256"], sha256("contracts/milestone-002-orbit-continuation-001-proposal.json"))
        self.assertEqual(self.gate["bindings"]["review_bundle_sha256"], sha256("reviews/m2-orbit-continuation-001/review-bundle.json"))

    def test_publication_and_reconciliation_create_no_decision_or_access(self) -> None:
        self.assertEqual(self.reconciliation["status"], "pass_exact_public_packet_owner_review_ready_zero_decisions")
        self.assertEqual(self.reconciliation["bindings"]["publication_gate_sha256"], sha256("records/readiness/m2-orbit-continuation-001-review-publication-gate.json"))
        self.assertEqual(self.reconciliation["review"], {"human_decision_count": 0, "attestation": False, "continuation_authorized": False})
        self.assertFalse(self.reconciliation["assertions"]["implementation_started"])
        self.assertFalse(self.reconciliation["assertions"]["credential_values_read_or_recorded"])
        self.assertFalse(self.reconciliation["assertions"]["orbit_network_or_payload_request_performed_by_reconciliation"])
        self.assertFalse(self.reconciliation["assertions"]["external_data_mutated"])
        self.assertFalse(self.blank["completed"])
        self.assertIsNone(self.blank["responses"][0]["decision"])

    def test_control_plane_preserves_publication_and_activates_approved_implementation(self) -> None:
        units = {item["id"]: item for item in self.milestone["units"]}
        publication = units["M2-ORBIT-CONTINUATION-001-REVIEW-PUBLICATION"]
        review = units["M2-ORBIT-CONTINUATION-001-REVIEW"]
        implementation = units["M2-ORBIT-CONTINUATION-001-IMPLEMENTATION"]
        action = units["M2-ORBIT-CONTINUATION-001"]
        self.assertEqual((publication["status"], publication["disposition"]), ("complete", "pass"))
        self.assertEqual((review["status"], review["disposition"]), ("complete", "pass"))
        self.assertTrue(review["human_gate"])
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["continuation_authorized"])
        self.assertEqual((implementation["status"], implementation["disposition"]), ("complete", "pass"))
        self.assertFalse(implementation["gates"]["credential_or_source_access_before_public_ci"])
        self.assertEqual((action["status"], action["disposition"]), ("complete", "pass"))
        self.assertEqual(action["gates"]["source_ids_in_exact_order"], ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"])
        self.assertEqual(action["gates"]["maximum_real_attempts_per_source"], 1)
        self.assertTrue(action["gates"]["stop_on_first_failure"])
        self.assertFalse(action["gates"]["m2_orb_001_request_authorized"])

    def test_checkpoint_derives_to_approved_implementation(self) -> None:
        checkpoint = "M2-ORBIT-OFFLINE-VERIFICATION-RECOVERY-001-REVIEW"
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], checkpoint)
        self.assertEqual(self.goal["current_checkpoint"], checkpoint)
        self.assertEqual(self.milestone["handoff"]["current_checkpoint"], checkpoint)
        self.assertFalse(current_orbit_continuation_001_review_required(ROOT, {"promoted": 8}))
        self.assertFalse(current_orbit_continuation_001_implementation_pending(ROOT, {"promoted": 8}))
        self.assertFalse(current_orbit_verify_implementation_pending(ROOT, {"promoted": 8}))
        self.assertFalse(
            current_orbit_offline_verification_recovery_001_review_publication_pending(
                ROOT, {"promoted": 8}
            )
        )
        self.assertTrue(
            current_orbit_offline_verification_recovery_001_review_required(
                ROOT, {"promoted": 8}
            )
        )


if __name__ == "__main__":
    unittest.main()
