"""Guard the approved HyP3 review identity and its pre-execution boundaries."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = "contracts/milestone-002-asf-hyp3-rtc-map-route-001-proposal.json"
BUNDLE = "reviews/m2-asf-hyp3-rtc-map-route-001/review-bundle.json"
APPROVAL = "records/source-gates/m2-asf-hyp3-rtc-map-route-001-approval.json"
SOURCE_GATE = "records/source-gates/m2-asf-hyp3-rtc-source-assessment-001-local.json"
CANDIDATE = "records/observations/m2-asf-rtc-four-scene-candidate-001-local.json"
PROPOSAL_SHA256 = "5118b0bb3727e9ef6080bed9015a68cd64bbbba226dc422948ec5cac294fbb55"
BUNDLE_SHA256 = "f6afe7e4f5b1210c6d614ca4ba7c701b8a016bc773825f72cf1eb16d07a8bdca"
ORDER = ("M1-SRC-002", "M1-SRC-005", "M1-SRC-001", "M1-SRC-004")


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


class HyP3ReviewIdentityTests(unittest.TestCase):
    def test_approved_identity_and_all_bound_artifacts(self) -> None:
        proposal = load(PROPOSAL)
        bundle = load(BUNDLE)
        approval = load(APPROVAL)
        self.assertEqual(sha256(PROPOSAL), PROPOSAL_SHA256)
        self.assertEqual(sha256(BUNDLE), BUNDLE_SHA256)
        self.assertEqual(approval["decision"], "approve")
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        for item in proposal["input_bindings"]:
            self.assertEqual(sha256(item["ref"]), item["sha256"], item["ref"])
        for item in bundle["artifacts"]:
            self.assertEqual(sha256(item["path"]), item["sha256"], item["path"])

    def test_exact_order_and_no_execution_release_before_ci(self) -> None:
        proposal = load(PROPOSAL)
        bundle = load(BUNDLE)
        candidate = load(CANDIDATE)
        source_gate = load(SOURCE_GATE)
        self.assertEqual(
            tuple(proposal["proposed_method_amendment"]["source_ids_in_proposed_event_first_order"]),
            ORDER,
        )
        self.assertEqual(tuple(job["source_id"] for job in candidate["candidate_jobs"]), ORDER)
        self.assertTrue(all(value is False for value in bundle["authority_boundary"].values()))
        self.assertEqual(source_gate["decision"]["status"], "blocked")
        self.assertEqual(source_gate["authority"]["mode"], "not_granted")
        self.assertFalse(proposal["frozen_scientific_boundaries"]["M4_change_analysis_or_threshold_adaptation_authorized"])
        self.assertFalse(proposal["frozen_scientific_boundaries"]["source_or_derived_pixel_publication_authorized"])

    def test_public_review_gate_and_parallel_map_route(self) -> None:
        gate_ref = "records/readiness/m2-asf-hyp3-rtc-map-route-001-review-publication-gate.json"
        gate = load(gate_ref)
        self.assertEqual(gate["status"], "pass_exact_review_packet_public_ci_only")
        self.assertEqual(gate["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(gate["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertEqual(gate["bindings"]["owner_approval_sha256"], sha256(APPROVAL))
        self.assertEqual(gate["bindings"]["publication_commit_sha"], "6b8c62847a3c50cdcb520a68aca8999e1ed0b0ce")
        self.assertEqual(gate["bindings"]["public_ci_run_id"], 36270829002)
        self.assertEqual(gate["observed_public_ci"]["run_conclusion"], "success")
        for ref, key in (
            ("records/project-control-profile.json", "active_map_route"),
            ("records/long-term-goal.json", "active_map_route"),
            ("contracts/milestone-002.json", "handoff"),
        ):
            state = load(ref)
            route = state[key] if key == "active_map_route" else state[key]["active_map_route"]
            self.assertEqual(route["authority_ref"], APPROVAL)
            self.assertEqual(route["public_review_gate_ref"], gate_ref)
            self.assertEqual(route["checkpoint_id"], "M2-ASF-HYP3-RTC-MAP-ROUTE-001-IMPLEMENTATION")


if __name__ == "__main__":
    unittest.main()
