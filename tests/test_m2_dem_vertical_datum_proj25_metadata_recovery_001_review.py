import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from derive_m2_acquisition_checkpoint import (  # noqa: E402
    current_dem_proj25_metadata_recovery_001_review_publication_pending,
    current_dem_proj25_metadata_recovery_001_review_required,
)


PROPOSAL_SHA256 = "729d36da013a9bf987486e18f7c6bac75865eda5b75dc963e8fd31ff4ddb13cd"
BUNDLE_SHA256 = "10d55916113e2b9e578e5845a75886f6688c112adc3e0f4b6bbb035f8658460d"
GRID_SHA256 = "4191d471eefebf24091b56dbc604353cb3b8cf8cc70e448bb9ae56a272bef17a"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2DemProj25MetadataRecovery001ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proposal = load("contracts/m2-dem-vertical-datum-proj25-metadata-recovery-001-proposal.json")
        cls.reconciliation = load("records/acquisition/m2-dem-vertical-datum-proj25-acquisition-reconciliation-001.json")
        cls.terminal = load("records/acquisition/m2-geoid-001-real-001-terminal.json")
        cls.bundle = load("reviews/m2-dem-vertical-datum-proj25-metadata-recovery-001/review-bundle.json")
        cls.contract = load("reviews/m2-dem-vertical-datum-proj25-metadata-recovery-001/review-contract.json")
        cls.blank = load("reviews/m2-dem-vertical-datum-proj25-metadata-recovery-001/blank-response.json")
        cls.readiness = load("records/readiness/m2-dem-vertical-datum-proj25-metadata-recovery-001-review-readiness.json")
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")

    def test_terminal_attempt_is_preserved_and_request_authority_consumed(self) -> None:
        self.assertEqual(self.terminal["status"], "terminal_failure_no_retry")
        self.assertEqual(self.terminal["attempt_id"], "m2-geoid-001-real-001")
        self.assertEqual(self.terminal["request_count"], 1)
        self.assertFalse(self.terminal["automatic_retry_authorized"])
        self.assertEqual(self.terminal["partial_bytes_preserved"], 80585622)
        self.assertFalse(self.terminal["destination_created"])
        self.assertEqual(self.terminal["conversion_attempts_started"], 0)

    def test_reconciliation_binds_exact_bytes_and_exact_metadata_difference(self) -> None:
        self.assertEqual(
            self.reconciliation["status"],
            "block_terminal_metadata_representation_mismatch_review_required",
        )
        staged = self.reconciliation["preserved_staged_bytes"]
        self.assertEqual(staged["size_bytes"], 80585622)
        self.assertEqual(staged["sha256"], GRID_SHA256)
        self.assertTrue(staged["exact_approved_identity"])
        self.assertFalse(staged["promoted"])
        metadata = self.reconciliation["observed_gdal_metadata"]
        self.assertIsNone(metadata["source_crs"])
        self.assertIsNone(metadata["target_crs"])
        self.assertEqual(metadata["target_crs_epsg_code"], "3855")
        self.assertIn("EPSG:4979", metadata["TIFFTAG_IMAGEDESCRIPTION"])
        self.assertIn("EPSG:3855", metadata["TIFFTAG_IMAGEDESCRIPTION"])
        self.assertTrue(self.reconciliation["mismatch"]["post_observation_correction_required"])

    def test_proposal_changes_only_metadata_interpretation_and_releases_nothing(self) -> None:
        self.assertEqual(sha256("contracts/m2-dem-vertical-datum-proj25-metadata-recovery-001-proposal.json"), PROPOSAL_SHA256)
        self.assertEqual(self.proposal["status"], "proposed_inactive_owner_review_required")
        change = self.proposal["proposed_exact_change"]
        self.assertFalse(change["source_semantics_changed"])
        self.assertFalse(change["target_semantics_changed"])
        self.assertFalse(change["tolerance_changed"])
        self.assertFalse(change["source_or_url_changed"])
        self.assertEqual(self.proposal["limits"]["network_requests"], 0)
        self.assertEqual(self.proposal["limits"]["recovery_verification_attempts"], 1)
        self.assertFalse(self.proposal["limits"]["automatic_retry"])
        self.assertEqual(self.proposal["claim_boundary"]["human_decision_count"], 0)
        self.assertFalse(self.proposal["claim_boundary"]["correction_authorized"])

    def test_review_bundle_is_exact_and_blank(self) -> None:
        self.assertEqual(sha256("reviews/m2-dem-vertical-datum-proj25-metadata-recovery-001/review-bundle.json"), BUNDLE_SHA256)
        self.assertEqual(
            self.bundle["candidate_identity"],
            f"M2-DEM-VERTICAL-DATUM-PROJ25-METADATA-RECOVERY-001-PROPOSAL-SHA256:{PROPOSAL_SHA256}",
        )
        for artifact in self.bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact.get("render_receipts", []):
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))
        self.assertEqual(self.bundle["human_decision_count"], 0)
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], BUNDLE_SHA256)
        self.assertTrue(self.contract["required_attestation"])
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], BUNDLE_SHA256)

    def test_readiness_and_controls_stop_at_publication(self) -> None:
        self.assertEqual(self.readiness["status"], "pass_ready_publication_zero_decisions")
        self.assertFalse(self.readiness["assertions"]["correction_authorized"])
        self.assertFalse(self.readiness["assertions"]["network_request_authorized"])
        self.assertTrue(self.readiness["assertions"]["preserved_bytes_read_for_exact_reconciliation"])
        self.assertFalse(self.readiness["assertions"]["recovery_verification_performed"])
        self.assertFalse(self.readiness["assertions"]["grid_sample_values_read"])
        expected = "M2-DEM-PROJ25-METADATA-RECOVERY-001-REVIEW-PUBLICATION"
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], expected)
        self.assertEqual(self.goal["current_checkpoint"], expected)
        self.assertEqual(self.milestone["handoff"]["current_checkpoint"], expected)
        self.assertEqual(self.goal["proposed_amendments"], ["contracts/m2-dem-vertical-datum-proj25-metadata-recovery-001-proposal.json"])

    def test_milestone_preserves_block_and_conditional_dependency(self) -> None:
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        acquisition = units["M2-DEM-EGM2008-PROJ25-ACQUISITION"]
        review = units["M2-DEM-PROJ25-METADATA-RECOVERY-001-REVIEW"]
        implementation = units["M2-DEM-PROJ25-METADATA-RECOVERY-001-IMPLEMENTATION"]
        conversion = units["M2-DEM-VERTICAL-DATUM-CONVERSION"]
        self.assertEqual(acquisition["status"], "complete")
        self.assertEqual(acquisition["disposition"], "block_terminal_metadata_representation_mismatch")
        self.assertEqual(review["status"], "in_progress")
        self.assertEqual(review["gates"]["human_decision_count"], 0)
        self.assertFalse(review["gates"]["correction_authorized"])
        self.assertEqual(implementation["status"], "planned")
        self.assertEqual(implementation["gates"]["network_requests"], 0)
        self.assertEqual(conversion["depends_on"], [implementation["id"]])

    def test_checkpoint_derivation_routes_to_review_publication(self) -> None:
        self.assertTrue(
            current_dem_proj25_metadata_recovery_001_review_publication_pending(
                ROOT, {"promoted": 8}
            )
        )
        self.assertFalse(
            current_dem_proj25_metadata_recovery_001_review_required(ROOT, {"promoted": 8})
        )


if __name__ == "__main__":
    unittest.main()
