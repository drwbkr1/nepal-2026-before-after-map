"""Portable checks for the exact approved conditional map-route packet."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-radar-event-area-pair-gtc-tiff-warp-recovery-004-proposal.json"
BUNDLE_REF = "reviews/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004/review-bundle.json"
APPROVAL_REF = "records/source-gates/m2-radar-event-area-pair-gtc-tiff-warp-recovery-004-approval.json"
PROPOSAL_SHA256 = "69f69b8685f3f0daf9d00a361377085fccb6e954d4ba8d16e40241f2a6c8fd92"
BUNDLE_SHA256 = "1378fb4057dfa47c36f83366c47936dae553e3c52dfee9a710a9c4757b94e93d"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def digest(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class RadarGtcTiffWarpPacketTests(unittest.TestCase):
    def test_approval_binds_exact_packet_and_one_conditional_process(self) -> None:
        approval = load(APPROVAL_REF)
        self.assertEqual(approval["decision"], "approve")
        self.assertEqual(approval["owner_statement_verbatim"], "approve")
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertEqual(digest(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(digest(BUNDLE_REF), BUNDLE_SHA256)
        authority = approval["authority"]
        self.assertEqual(authority["conditional_maximum_new_real_processes"], 1)
        self.assertEqual(authority["fixed_source_order"], ["M1-SRC-002", "M1-SRC-005"])
        self.assertEqual(authority["fixed_orbit_order"], ["M2-ORB-001", "M2-ORB-003"])
        for key in ("automatic_retry", "consumed_attempt_resume_reuse_or_mutation",
                    "source_orbit_dem_aoi_crs_grid_mask_threshold_or_registration_change",
                    "baseline_or_change_analysis", "interpretation_or_attribution",
                    "derived_pixel_or_scientific_publication"):
            self.assertFalse(authority[key], key)

    def test_every_reviewed_artifact_and_input_hash_matches(self) -> None:
        bundle = load(BUNDLE_REF)
        proposal = load(PROPOSAL_REF)
        self.assertEqual(bundle["human_decision_count"], 0)
        self.assertEqual(proposal["human_decision_count"], 0)
        for binding in bundle["artifacts"] + proposal["input_bindings"]:
            ref = binding.get("path", binding.get("ref"))
            self.assertEqual(digest(ref), binding["sha256"], ref)

    def test_old_attempts_and_scientific_boundaries_stay_closed(self) -> None:
        proposal = load(PROPOSAL_REF)
        bundle = load(BUNDLE_REF)
        optical = load("records/readiness/m2-optical-gdal-header-pixel-recovery-002-post-ci-reconciliation.json")
        radar = load("records/readiness/m2-radar-event-area-pair-native-gtc-grid-recovery-003-disposable-terminal-reconciliation.json")
        self.assertEqual(optical["attempt"]["pixel_qa_status"], "block")
        self.assertEqual(radar["stopped_gates"]["fresh_e1_a2_real_process"], "not_started")
        envelope = proposal["requested_single_authority_envelope"]
        self.assertEqual(envelope["maximum_new_real_radar_processes"], 1)
        self.assertEqual(envelope["fresh_attempt_root_alias"], "e1/a3_only_if_absent_at_final_preflight")
        self.assertFalse(envelope["automatic_retry"])
        self.assertFalse(envelope["consumed_attempt_resume_reuse_or_mutation"])
        self.assertFalse(proposal["claim_boundary"]["baseline_admission_authorized"])
        self.assertFalse(proposal["claim_boundary"]["change_analysis_or_difference_raster_authorized"])
        self.assertFalse(bundle["authority_boundary"]["fresh_real_radar_process_authorized"])


if __name__ == "__main__":
    unittest.main()
