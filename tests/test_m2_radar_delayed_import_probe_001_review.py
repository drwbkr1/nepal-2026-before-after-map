import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_radar_delayed_import_probe_001_implementation_pending,
    current_radar_delayed_import_probe_001_review_publication_pending,
    current_radar_delayed_import_probe_001_review_required,
    current_radar_pixel_orbit_application_recovery_001_terminal,
)

PREFIX = "m2-radar-delayed-import-probe-001"
PROPOSAL_REF = "contracts/milestone-002-radar-delayed-import-probe-001-proposal.json"
PREPARATION_APPROVAL_REF = "records/source-gates/m2-radar-delayed-import-probe-001-review-preparation-approval.json"
PREFLIGHT_REF = f"records/readiness/{PREFIX}-review-preflight.json"
DOC_REF = "docs/M2_RADAR_DELAYED_IMPORT_PROBE_001_REVIEW.md"
IMAGE_REF = f"docs/assets/{PREFIX}-review.png"
SURFACE_REF = f"records/surface-receipts/{PREFIX}-review.json"
BUNDLE_REF = f"reviews/{PREFIX}/review-bundle.json"
CONTRACT_REF = f"reviews/{PREFIX}/review-contract.json"
BLANK_REF = f"reviews/{PREFIX}/blank-response.json"
READINESS_REF = f"records/readiness/{PREFIX}-review-readiness.json"
PUBLICATION_GATE_REF = f"records/readiness/{PREFIX}-review-publication-gate.json"
PUBLICATION_RECONCILIATION_REF = f"records/readiness/{PREFIX}-review-publication-reconciliation.json"
TERMINAL_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-001-terminal-reconciliation.json"
OUTCOME_REF = "records/processing/m2-radar-pixel-orbit-application-recovery-001-outcome-reconciliation.json"
PROPOSAL_SHA256 = "7d3474eeed2dd679ca1f755d1ebcf6542b977b87418b40f4b40204ae5ac02de9"
BUNDLE_SHA256 = "1084597b5db7b20e24ad241c5550a58623571747d5ef7d37a086298830bd45e5"
READINESS_SHA256 = "37ce53da206e71ed20db5a4b1b0fef50d3acd953ea9d865de2253a20339ad170"
CHECKPOINT = "M2-RADAR-DELAYED-IMPORT-PROBE-001-IMPLEMENTATION"


def load(ref: str) -> dict:
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


def sha256(ref: str) -> str:
    return hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()


class M2RadarDelayedImportProbe001ReviewTests(unittest.TestCase):
    def test_preparation_approval_is_review_only(self) -> None:
        approval = load(PREPARATION_APPROVAL_REF)
        boundary = approval["authority_boundary"]
        self.assertEqual(approval["status"], "approved_review_preparation_only")
        self.assertEqual(approval["human_decision_count"], 1)
        self.assertTrue(boundary["review_packet_preparation_authorized"])
        self.assertTrue(boundary["public_review_packet_publication_authorized"])
        for key in (
            "probe_implementation_authorized",
            "probe_execution_authorized",
            "project_data_content_read_authorized",
            "recovery_retry_or_reuse_authorized",
            "radar_processing_authorized",
            "baseline_or_change_authorized",
            "scientific_publication_authorized",
        ):
            self.assertFalse(boundary[key])

    def test_proposal_preserves_terminal_evidence_and_uncertainty(self) -> None:
        proposal = load(PROPOSAL_REF)
        terminal = load(TERMINAL_REF)
        outcome = load(OUTCOME_REF)
        self.assertEqual(sha256(PROPOSAL_REF), PROPOSAL_SHA256)
        self.assertEqual(proposal["status"], "proposed_inactive_owner_review_required")
        self.assertEqual(proposal["human_decision_count"], 0)
        self.assertEqual(proposal["trigger"]["terminal_reconciliation_sha256"], sha256(TERMINAL_REF))
        self.assertEqual(proposal["trigger"]["outcome_reconciliation_sha256"], sha256(OUTCOME_REF))
        self.assertEqual(terminal["status"], "failed_supervisor_no_retry")
        self.assertEqual(outcome["status"], "block_terminal_arcgis_product_license_not_initialized_no_retry")
        assessment = proposal["evidence_assessment"]
        self.assertFalse(assessment["historical_exact_failing_statement_identified"])
        self.assertFalse(assessment["root_cause_resolved"])
        self.assertFalse(assessment["sequence_difference_causal"])

    def test_probe_reproduces_exact_observed_delay_without_project_data(self) -> None:
        proposal = load(PROPOSAL_REF)
        probe = proposal["exact_probe_contract"]
        self.assertEqual(probe["attempt_id"], "radar-delayed-import-probe-001-real-001")
        self.assertEqual(probe["process_count"], 1)
        self.assertEqual(probe["corpus"]["file_count"], 156)
        self.assertEqual(probe["corpus"]["total_logical_bytes"], 10_367_157_634)
        self.assertFalse(probe["corpus"]["source_names_or_source_bytes_used"])
        self.assertLess(probe["stage_order"].index("corpus_hash_completed"), probe["stage_order"].index("arcpy_import_started"))
        self.assertLess(probe["stage_order"].index("arcpy_import_completed"), probe["stage_order"].index("product_info_started"))
        self.assertLess(probe["stage_order"].index("spatial_checkout_completed"), probe["stage_order"].index("disposable_mosaic_started"))
        self.assertFalse(probe["geoprocessing"]["project_crs_or_project_aoi_used"])
        self.assertFalse(probe["result_semantics"]["historical_root_cause_claim_allowed"])
        self.assertFalse(probe["result_semantics"]["recovery_readiness_claim_allowed"])
        limits = proposal["limits"]
        self.assertEqual(limits["live_probe_attempts"], 1)
        self.assertFalse(limits["automatic_retry"])
        for key in (
            "network_requests",
            "credential_or_token_actions",
            "software_installations",
            "uac_actions",
            "project_data_content_reads",
            "external_custody_reads",
            "external_custody_mutations",
            "recovery_attempts",
            "orbit_applications",
            "radar_pixel_reads",
            "scientific_outputs",
        ):
            self.assertEqual(limits[key], 0)

    def test_bundle_contract_and_blank_response_are_exact(self) -> None:
        bundle = load(BUNDLE_REF)
        contract = load(CONTRACT_REF)
        blank = load(BLANK_REF)
        self.assertEqual(sha256(BUNDLE_REF), BUNDLE_SHA256)
        self.assertEqual(bundle["human_decision_count"], 0)
        for artifact in bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertTrue(contract["required_attestation"])
        for key, value in contract["authority_boundary"].items():
            if key != "packet_creates_authority":
                self.assertFalse(value)
        self.assertFalse(contract["authority_boundary"]["packet_creates_authority"])
        self.assertFalse(blank["completed"])
        self.assertFalse(blank["reviewer"]["attestation"])
        self.assertIsNone(blank["responses"][0]["decision"])

    def test_review_surface_and_preflight_make_no_execution_claim(self) -> None:
        preflight = load(PREFLIGHT_REF)
        surface = load(SURFACE_REF)
        readiness = load(READINESS_REF)
        self.assertEqual(sha256(READINESS_REF), READINESS_SHA256)
        self.assertEqual(preflight["status"], "pass_ready_prepare_zero_decision_review")
        self.assertFalse(preflight["checks"]["current_authority_allows_probe_implementation_or_execution"])
        for key in (
            "probe_process_started",
            "disposable_corpus_created",
            "arcpy_invoked",
            "geoprocessing_tool_invoked",
            "project_data_content_read",
            "external_custody_accessed",
            "external_custody_mutated",
            "recovery_attempt_reused_or_retried",
            "implementation_authorized",
            "probe_execution_authorized",
            "scientific_result_established",
        ):
            self.assertFalse(preflight["assertions"][key])
        self.assertEqual(surface["status"], "pass_static_review_surface")
        self.assertEqual((surface["width_px"], surface["height_px"]), (1800, 1660))
        self.assertEqual(surface["artifact_sha256"], sha256(IMAGE_REF))
        self.assertEqual(readiness["status"], "pass_ready_publication_zero_decisions")
        self.assertFalse(readiness["released_now"]["implementation"])
        self.assertFalse(readiness["released_now"]["probe_execution"])

    def test_public_ci_releases_owner_review_only(self) -> None:
        gate = load(PUBLICATION_GATE_REF)
        reconciliation = load(PUBLICATION_RECONCILIATION_REF)
        self.assertEqual(gate["status"], "pass_public_default_branch_ci_zero_decision_review_ready")
        self.assertEqual(gate["commit_sha"], "83d94782d255b674843ac4f12cda49327a924fb1")
        self.assertEqual(gate["public_ci_run_id"], 35411448542)
        self.assertEqual(gate["repository_required_file_count"], 1058)
        self.assertEqual(gate["public_test_count"], 584)
        self.assertEqual(gate["public_intentional_skip_count"], 13)
        self.assertTrue(gate["assertions"]["owner_review_ready"])
        self.assertEqual(reconciliation["status"], "pass_public_gate_owner_review_ready")
        self.assertEqual(reconciliation["publication_gate_sha256"], sha256(PUBLICATION_GATE_REF))
        self.assertTrue(reconciliation["released_now"]["owner_review"])
        for key in (
            "implementation",
            "probe_execution",
            "project_data_content_read",
            "recovery_retry_or_reuse",
            "radar_processing",
            "baseline_or_change_analysis",
            "scientific_publication",
        ):
            self.assertFalse(reconciliation["released_now"][key])

    def test_canonical_state_routes_to_approved_implementation(self) -> None:
        milestone = load("contracts/milestone-002.json")
        profile = load("records/project-control-profile.json")
        goal = load("records/long-term-goal.json")
        self.assertEqual(milestone["handoff"]["current_checkpoint"], CHECKPOINT)
        self.assertEqual(profile["current_checkpoint"]["checkpoint_id"], CHECKPOINT)
        self.assertEqual(goal["current_checkpoint"], CHECKPOINT)
        self.assertEqual(goal["proposed_amendments"], [])
        units = {item["id"]: item for item in milestone["units"]}
        review = units["M2-RADAR-DELAYED-IMPORT-PROBE-001-REVIEW"]
        self.assertEqual(review["status"], "complete")
        self.assertEqual(review["gates"]["public_ci"], "success")
        self.assertTrue(review["gates"]["implementation_authorized"])
        self.assertTrue(review["gates"]["probe_execution_authorized"])
        self.assertTrue(current_radar_pixel_orbit_application_recovery_001_terminal(ROOT, {"promoted": 8}))
        self.assertFalse(current_radar_delayed_import_probe_001_review_publication_pending(ROOT, {"promoted": 8}))
        self.assertFalse(current_radar_delayed_import_probe_001_review_required(ROOT, {"promoted": 8}))
        self.assertTrue(current_radar_delayed_import_probe_001_implementation_pending(ROOT, {"promoted": 8}))


if __name__ == "__main__":
    unittest.main()
