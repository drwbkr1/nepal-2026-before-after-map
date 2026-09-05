from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-orbit-recovery-002-proposal.json"
BUNDLE_REF = "reviews/m2-orbit-recovery-002/review-bundle.json"
CONTRACT_REF = "reviews/m2-orbit-recovery-002/review-contract.json"
BLANK_REF = "reviews/m2-orbit-recovery-002/blank-response.json"
READINESS_REF = "records/readiness/m2-orbit-recovery-002-review-readiness.json"
PROPOSAL_SHA256 = "d30208c07deb66ef2c7487f8c901abd4fb5ff04aa56766bca8066d4c8d4f0db8"
BUNDLE_SHA256 = "6d43342b6bda2740667fa6e924a52f15313d8827cfb62563ea107bc483e87fa5"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2OrbitRecovery002ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proposal = load(PROPOSAL_REF)
        cls.bundle = load(BUNDLE_REF)
        cls.contract = load(CONTRACT_REF)
        cls.blank = load(BLANK_REF)
        cls.readiness = load(READINESS_REF)
        cls.milestone = load("contracts/milestone-002.json")

    def test_proposal_binds_exact_one_file_and_corrected_route(self) -> None:
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(self.proposal["status"], "proposed_not_authorized")
        recovery = self.proposal["proposed_recovery"]
        self.assertEqual(recovery["source_id"], "M2-ORB-001")
        self.assertEqual(recovery["provider_product_id"], "d4fdc474-0069-459b-9534-b5999dec5aab")
        self.assertEqual(recovery["maximum_real_attempts"], 1)
        self.assertFalse(recovery["automatic_retry_authorized"])
        self.assertEqual(self.proposal["corrected_prerequisite"]["source_ids"], [f"M1-SRC-{index:03d}" for index in range(1, 7)])
        self.assertEqual(self.proposal["stale_packet"]["old_proposal_sha256"], "ce76d633a8104ea5800f51dccd4b1037f930d41b7f08a3de32eed68c6697915a")

    def test_proposal_does_not_release_other_orbits_or_processing(self) -> None:
        prohibited = " ".join(self.proposal["approval_would_not_authorize"])
        for phrase in ("M2-ORB-002", "automatic retry", "AUX_POEORB", "convert DEM", "decode radar pixels", "scientific result"):
            self.assertIn(phrase, prohibited)
        self.assertIn("M2-DEM-VERTICAL-DATUM-REVIEW", self.proposal["independent_unresolved_gates"])
        self.assertIn("M2-DEM-TERRAIN-RESULT-REVIEW", self.proposal["independent_unresolved_gates"])

    def test_bundle_contract_and_blank_response_are_exact(self) -> None:
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(self.bundle["candidate_identity"], f"M2-ORBIT-RECOVERY-002-PROPOSAL-SHA256:{PROPOSAL_SHA256}")
        for artifact in self.bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertEqual(self.contract["items"], [{"item_id": "M2-ORBIT-RECOVERY-002", "evidence_sha256": BUNDLE_SHA256}])
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], BUNDLE_SHA256)
        self.assertEqual(self.readiness["review"]["human_decision_count"], 0)
        self.assertFalse(self.readiness["assertions"]["orbit_payload_requested"])

    def test_active_graph_stops_before_orbit_recovery(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        self.assertEqual(units["M2-RADAR-SOURCE-READINESS"]["status"], "complete")
        self.assertEqual(units["M2-ORBIT-RECOVERY-002-REVIEW"]["status"], "ready")
        self.assertEqual(units["M2-ORBIT-RECOVERY-002-IMPLEMENTATION"]["status"], "planned")
        self.assertEqual(units["M2-ORBIT-RECOVERY-002"]["status"], "planned")
        self.assertEqual(units["M2-ORBIT-ACQUIRE"]["status"], "deferred")
        self.assertIn("M2-ORBIT-RECOVERY-002", units["M2-ORBIT-ACQUIRE"]["depends_on"])
        self.assertEqual(units["M2-ORBIT-ACQUIRE"]["gates"]["retained_failure_review"], "corrected_review_ready_zero_decisions")


if __name__ == "__main__":
    unittest.main()
