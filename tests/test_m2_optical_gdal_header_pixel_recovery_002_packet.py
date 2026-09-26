"""Portable checks for the exact approved, conditional optical GDAL packet."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-optical-gdal-header-pixel-recovery-002-proposal.json"
BUNDLE_REF = "reviews/m2-optical-gdal-header-pixel-recovery-002/review-bundle.json"
APPROVAL_REF = "records/source-gates/m2-optical-gdal-header-pixel-recovery-002-approval.json"
PROPOSAL_SHA256 = "293a9f90a1d6ca9d1531423798d191901d3772999763fbce34ca6b583e5f7d8e"
BUNDLE_SHA256 = "933f141a4474edafb0fe2580e97428c3dd47a802e4ae8d6d434fb0e6803fb785"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def digest(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class OpticalGdalPacketTests(unittest.TestCase):
    def test_approval_binds_exact_review_and_conditional_scope(self) -> None:
        approval = load(APPROVAL_REF)
        self.assertEqual(approval["owner_statement_verbatim"], "approval optical")
        self.assertEqual(approval["decision"], "approve")
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertEqual(approval["bindings"]["proposal_sha256"], PROPOSAL_SHA256)
        self.assertEqual(approval["bindings"]["review_bundle_sha256"], BUNDLE_SHA256)
        self.assertEqual(digest(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(digest(BUNDLE_REF), BUNDLE_SHA256)
        authority = approval["authority"]
        self.assertEqual(authority["conditional_maximum_new_real_processes"], 1)
        self.assertEqual(authority["fixed_source_order"], ["M2-OPT-001", "M2-OPT-002"])
        for key in ("automatic_retry", "network_credential_terms_or_reacquisition_action",
                    "consumed_attempt_reuse_resume_or_mutation", "radar_activation",
                    "baseline_change_analysis_interpretation_or_attribution",
                    "derived_pixel_or_scientific_publication"):
            self.assertFalse(authority[key], key)

    def test_every_bundle_and_proposal_input_is_exact(self) -> None:
        bundle = load(BUNDLE_REF)
        proposal = load(PROPOSAL_REF)
        self.assertEqual(bundle["status"], "local_zero_decision_one_owner_decision_required")
        self.assertEqual(bundle["human_decision_count"], 0)
        for binding in bundle["artifacts"] + proposal["input_bindings"]:
            ref = binding.get("path", binding.get("ref"))
            self.assertEqual(digest(ref), binding["sha256"], ref)
        terminal = bundle["route_relationship"]
        self.assertEqual(digest(terminal["radar_recovery_003_terminal_ref"]),
                         terminal["radar_recovery_003_terminal_sha256"])
        self.assertTrue(terminal["radar_recovery_003_already_consumed"])

    def test_exact_existing_pair_and_old_terminals_are_preserved(self) -> None:
        proposal = load(PROPOSAL_REF)
        preflight = load("records/readiness/m2-optical-pair-header-receipt-recovery-001-final-preflight.json")
        for proposed, observed in zip(proposal["exact_existing_sources"], preflight["sources_in_order"], strict=True):
            self.assertEqual(proposed["source_id"], observed["source_id"])
            self.assertEqual(proposed["archive_sha256"], observed["archive_sha256"])
            self.assertEqual(proposed["materialization_manifest_sha256"], observed["manifest_sha256"])
        optical_terminal = load("records/readiness/m2-optical-pair-header-receipt-recovery-001-post-ci-reconciliation.json")
        radar_terminal = load("records/readiness/m2-radar-event-area-pair-native-gtc-grid-recovery-003-terminal-publication-reconciliation.json")
        self.assertTrue(optical_terminal["attempt"]["consumed"])
        self.assertFalse(optical_terminal["attempt"]["header_or_pixel_receipt_present"])
        self.assertTrue(radar_terminal["assertions"]["exact_method_terminal_at_approved_extent_guard"])
        self.assertTrue(radar_terminal["assertions"]["e1_a2_real_process_not_started"])

    def test_real_access_remains_conditional_and_science_blocked(self) -> None:
        proposal = load(PROPOSAL_REF)
        bundle = load(BUNDLE_REF)
        envelope = proposal["requested_single_conditional_envelope"]
        self.assertEqual(envelope["new_real_process_maximum"], 1)
        self.assertFalse(envelope["automatic_retry"])
        self.assertFalse(envelope["reacquisition_or_rematerialization"])
        self.assertFalse(envelope["baseline_change_analysis_or_scientific_publication"])
        self.assertFalse(proposal["claim_boundary"]["difference_raster_or_change_polygon_authorized"])
        self.assertFalse(bundle["authority_boundary"]["fresh_real_optical_process_authorized"])


if __name__ == "__main__":
    unittest.main()
