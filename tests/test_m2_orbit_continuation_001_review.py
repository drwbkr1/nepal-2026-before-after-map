from __future__ import annotations

import hashlib
import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OrbitContinuation001ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proposal = load("contracts/milestone-002-orbit-continuation-001-proposal.json")
        cls.preflight = load("records/readiness/m2-orbit-continuation-001-review-preflight.json")
        cls.surface = load("records/surface-receipts/m2-orbit-continuation-001-review.json")
        cls.bundle = load("reviews/m2-orbit-continuation-001/review-bundle.json")
        cls.contract = load("reviews/m2-orbit-continuation-001/review-contract.json")
        cls.blank = load("reviews/m2-orbit-continuation-001/blank-response.json")
        cls.readiness = load("records/readiness/m2-orbit-continuation-001-review-readiness.json")
        cls.intake = load("contracts/m2-orbit-intake.json")

    def test_packet_is_blank_hash_bound_and_complete(self) -> None:
        proposal_sha = sha256("contracts/milestone-002-orbit-continuation-001-proposal.json")
        bundle_sha = sha256("reviews/m2-orbit-continuation-001/review-bundle.json")
        self.assertEqual(self.proposal["status"], "proposed_not_authorized")
        self.assertEqual(
            self.bundle["candidate_identity"],
            f"M2-ORBIT-CONTINUATION-001-PROPOSAL-SHA256:{proposal_sha}",
        )
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], bundle_sha)
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], bundle_sha)
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.readiness["bindings"]["proposal_sha256"], proposal_sha)
        self.assertEqual(self.readiness["bindings"]["review_bundle_sha256"], bundle_sha)
        self.assertEqual(self.readiness["review"]["human_decision_count"], 0)

    def test_every_bundle_artifact_hash_matches(self) -> None:
        for artifact in self.bundle["artifacts"]:
            if artifact["artifact_id"] == "active-orbit-intake":
                self.assertEqual(
                    artifact["sha256"],
                    "f64591598c782dc0a7bec58b40517d5b916ca850705ecff8677dbc66022c430b",
                )
                self.assertNotEqual(artifact["sha256"], sha256(artifact["path"]))
            else:
                self.assertEqual(artifact["sha256"], sha256(artifact["path"]), artifact["artifact_id"])
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))

    def test_exact_three_source_order_and_one_attempt_policy(self) -> None:
        source_ids = ["M2-ORB-002", "M2-ORB-003", "M2-ORB-004"]
        continuation = self.proposal["proposed_continuation"]
        self.assertEqual(continuation["source_ids_in_exact_order"], source_ids)
        self.assertEqual([item["source_id"] for item in self.proposal["exact_source_order"]], source_ids)
        self.assertEqual(continuation["maximum_owner_handoffs"], 1)
        self.assertEqual(continuation["maximum_real_attempts_per_source"], 1)
        self.assertTrue(continuation["stop_on_first_failure"])
        self.assertFalse(continuation["automatic_retry_authorized"])
        self.assertFalse(continuation["m2_orb_001_request_authorized"])
        self.assertEqual(continuation["maximum_endpoint_tolerance_seconds"], 1.0)
        self.assertEqual(continuation["endpoint_rule_scope"], source_ids)
        self.assertEqual(
            self.proposal["current_state"]["orbit_state_counts"],
            {"authorized": 3, "failed": 0, "promoted": 1},
        )
        self.assertEqual([item["state"] for item in self.intake["assets"]], ["promoted"] * 4)
        self.assertEqual(
            [[attempt["outcome"] for attempt in item["attempts"]] for item in self.intake["assets"][1:]],
            [["succeeded"], ["succeeded"], ["succeeded"]],
        )

    def test_preparation_performed_no_live_action(self) -> None:
        assertions = self.preflight["assertions"]
        self.assertEqual(self.preflight["status"], "pass_review_ready_zero_decisions_no_network_or_payload_mutation")
        self.assertEqual(assertions["human_decision_count"], 0)
        self.assertFalse(assertions["continuation_authorized"])
        self.assertFalse(assertions["credential_read"])
        self.assertFalse(assertions["network_request_performed"])
        self.assertFalse(assertions["payload_requested"])
        self.assertFalse(assertions["external_data_mutated"])
        self.assertFalse(assertions["m2_orb_001_mutated"])
        self.assertFalse(assertions["scientific_result_established"])

    def test_review_surface_is_exported_and_visually_declared(self) -> None:
        ref = self.surface["artifact"]["path"]
        raw = (ROOT / ref).read_bytes()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", raw[16:24])
        self.assertEqual((width, height), (1800, 1640))
        self.assertEqual(self.surface["artifact"]["sha256"], sha256(ref))
        self.assertTrue(self.surface["validation"]["blank_state_verified"])
        self.assertTrue(self.surface["validation"]["three_source_fixed_order_visible"])
        self.assertTrue(self.surface["validation"]["prospective_one_second_rule_visible"])
        self.assertEqual(self.surface["validation"]["human_decision_count"], 0)


if __name__ == "__main__":
    unittest.main()
