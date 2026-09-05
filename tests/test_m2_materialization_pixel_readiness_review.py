import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_REF = "contracts/milestone-002-materialization-pixel-readiness-proposal.json"
PREFLIGHT_REF = "records/readiness/m2-materialization-pixel-readiness-review-preflight.json"
BUNDLE_REF = "reviews/m2-materialization-pixel-readiness/review-bundle.json"
CONTRACT_REF = "reviews/m2-materialization-pixel-readiness/review-contract.json"
BLANK_REF = "reviews/m2-materialization-pixel-readiness/blank-response.json"
READINESS_REF = "records/readiness/m2-materialization-pixel-readiness-review-readiness.json"
SURFACE_RECEIPT_REF = "records/surface-receipts/m2-materialization-pixel-readiness-review.json"

EXPECTED_HASHES = {
    PROPOSAL_REF: "3dbbea5b16eeb297635d6487268cf8b619234fff14755668ac959f778b8e360c",
    PREFLIGHT_REF: "9a4ec0e286ab787194f76fa569293c67cc5db8529f96af9aba7e0959792af019",
    BUNDLE_REF: "8da456e9e0a0e378210b3d9b017e88990f1711da334f27b4cd3886211a97369a",
    CONTRACT_REF: "d156eac1903c233dc087f33645596f55fd76ee8efbb51607a9303f8a3e1823b4",
    BLANK_REF: "296916d31bdfbd248e27ca9fd03b7f6f0530269976fbf4accc3690bfb6965f0d",
    READINESS_REF: "a9f6a799a378b26fa28de9828254cd73c4d9fa39e494611512f26b7dc0add3aa",
    SURFACE_RECEIPT_REF: "2b0a9290a587e8fdf9bce7f7b00603773c85cdca0303445372ed7eb5bfba07a8",
    "docs/assets/m2-materialization-pixel-readiness-review.png": "d92f73e5e349207401b0b7bed4c307ffa835ae454281b006409450f5b773d527",
}

MATERIALIZATION_ORDER = ["M1-SRC-004", "M1-SRC-005", "M1-SRC-006", "M1-SRC-010", "M1-SRC-008"]
ATTEMPT_ORDER = [
    "m1-src-004-materialization-001",
    "m1-src-005-materialization-001",
    "m1-src-006-materialization-001",
    "m1-src-010-materialization-001",
    "m1-src-008-materialization-001",
]


def load(ref):
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


class MaterializationPixelReadinessReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposal = load(PROPOSAL_REF)
        cls.preflight = load(PREFLIGHT_REF)
        cls.bundle = load(BUNDLE_REF)
        cls.contract = load(CONTRACT_REF)
        cls.blank = load(BLANK_REF)
        cls.readiness = load(READINESS_REF)
        cls.surface = load(SURFACE_RECEIPT_REF)
        cls.milestone = load("contracts/milestone-002.json")
        cls.profile = load("records/project-control-profile.json")

    def test_exact_review_artifact_hashes(self):
        for ref, expected in EXPECTED_HASHES.items():
            self.assertEqual(hashlib.sha256((ROOT / ref).read_bytes()).hexdigest(), expected, ref)

    def test_stage_1_is_exact_one_attempt_fail_closed_materialization(self):
        stage = self.proposal["stage_1_exact_materialization"]
        self.assertEqual(stage["source_order"], MATERIALIZATION_ORDER)
        self.assertEqual([item["source_id"] for item in stage["sources"]], MATERIALIZATION_ORDER)
        self.assertEqual([item["planned_attempt_id"] for item in stage["sources"]], ATTEMPT_ORDER)
        self.assertEqual(stage["maximum_attempts_per_source"], 1)
        self.assertFalse(stage["automatic_retry_authorized"])
        self.assertFalse(stage["source_archive_mutation_authorized"])
        self.assertFalse(stage["network_or_authentication_authorized"])
        self.assertTrue(any("stop the materialization sequence" in item for item in stage["execution"]))

    def test_header_and_optical_pixel_stages_are_bounded(self):
        stage_2 = self.proposal["stage_2_full_cohort_header_readiness"]
        inspections = {item["inspection_id"]: item for item in stage_2["real_inspections"]}
        self.assertEqual(
            inspections["radar-input-readiness-real-003"]["sources"],
            ["M1-SRC-001", "M1-SRC-002", "M1-SRC-003", "M1-SRC-004", "M1-SRC-005", "M1-SRC-006"],
        )
        self.assertEqual(inspections["optical-input-readiness-real-001"]["sources"], ["M1-SRC-010", "M1-SRC-008"])
        for inspection in inspections.values():
            self.assertEqual(inspection["maximum_invocations"], 1)
            self.assertFalse(inspection["measurement_pixel_decoding"])
        stage_3 = self.proposal["stage_3_conditional_optical_pixel_readiness"]
        self.assertEqual(stage_3["exact_pair"]["pair_id"], "PAIR-S2-RUM-R119")
        self.assertEqual(stage_3["approved_aoi_ids"], ["AOI-OVERVIEW", "AOI-SOURCE", "AOI-UPPER-CORRIDOR"])
        self.assertEqual(stage_3["maximum_real_invocations"], 1)
        self.assertFalse(stage_3["automatic_retry_authorized"])
        self.assertFalse(self.proposal["radar_pixel_readiness"]["measurement_pixel_decoding_authorized"])
        self.assertIn("spectral-index change rasters", stage_3["prohibited_outputs"])

    def test_preflight_records_no_mutation_and_no_pixel_access(self):
        self.assertEqual(self.preflight["status"], "pass_exact_five_ready_no_mutation")
        self.assertEqual([item["source_id"] for item in self.preflight["planned_sources"]], MATERIALIZATION_ORDER)
        self.assertEqual([item["planned_attempt_id"] for item in self.preflight["planned_sources"]], ATTEMPT_ORDER)
        self.assertEqual(self.preflight["storage"]["planned_uncompressed_bytes"], 7_268_266_717)
        self.assertEqual(self.preflight["storage"]["free_space_gate"], "pass")
        assertions = self.preflight["assertions"]
        self.assertEqual(assertions["promoted_source_count"], 8)
        self.assertEqual(assertions["container_pass_source_count"], 8)
        self.assertEqual(assertions["existing_materialization_count"], 3)
        self.assertEqual(assertions["planned_materialization_count"], 5)
        self.assertTrue(assertions["planned_paths_absent"])
        self.assertFalse(assertions["archive_extraction_performed"])
        self.assertFalse(assertions["measurement_pixels_read"])
        self.assertFalse(assertions["external_files_mutated"])

    def test_review_is_blank_and_creates_no_authority(self):
        self.assertEqual(self.bundle["candidate_identity"], f"M2-MATERIALIZATION-PIXEL-READINESS-PROPOSAL-SHA256:{EXPECTED_HASHES[PROPOSAL_REF]}")
        self.assertEqual(len(self.bundle["artifacts"]), 12)
        self.assertTrue(self.bundle["review_surface"]["blank_state_verified"])
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], EXPECTED_HASHES[BUNDLE_REF])
        self.assertEqual(self.contract["allowed_decisions"], ["approve", "revise", "defer"])
        self.assertTrue(self.contract["required_attestation"])
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.readiness["review"]["human_decision_count"], 0)
        self.assertFalse(self.readiness["review"]["attestation"])
        self.assertTrue(self.readiness["review"]["ready_for_handoff"])
        self.assertFalse(self.surface["assertions"]["materialization_authorized"])
        self.assertFalse(self.surface["assertions"]["real_header_access_authorized"])
        self.assertFalse(self.surface["assertions"]["pixel_access_authorized"])

    def test_milestone_and_profile_record_exact_approval_and_stop_at_implementation(self):
        units = {item["id"]: item for item in self.milestone["units"]}
        review = units["M2-MATERIALIZATION-PIXEL-READINESS-REVIEW"]
        self.assertEqual(review["status"], "complete")
        self.assertTrue(review["human_gate"])
        self.assertEqual(review["gates"]["human_decision_count"], 1)
        self.assertTrue(review["gates"]["execution_authorized"])
        self.assertFalse(review["gates"]["radar_pixel_access_authorized"])
        self.assertEqual(units["M2-MATERIALIZATION-PIXEL-READINESS-IMPLEMENTATION"]["status"], "in_progress")
        self.assertEqual(units["M2-MATERIALIZATION-PIXEL-READINESS-IMPLEMENTATION"]["gates"]["public_ci"], "stage_1_pass_stage_2_pending")
        self.assertEqual(units["M2-MATERIALIZE-REMAINING"]["status"], "complete")
        self.assertEqual(units["M2-MATERIALIZE-REMAINING"]["gates"]["exact_source_order"], MATERIALIZATION_ORDER)
        self.assertEqual(units["M2-FULL-INPUT-READINESS"]["status"], "in_progress")
        self.assertFalse(units["M2-FULL-INPUT-READINESS"]["gates"]["measurement_pixel_decoding"])
        self.assertEqual(units["M2-OPTICAL-PIXEL-READINESS"]["status"], "planned")
        self.assertFalse(units["M2-OPTICAL-PIXEL-READINESS"]["gates"]["radar_pixel_readiness_authorized"])
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], "M2-FULL-INPUT-READINESS")


if __name__ == "__main__":
    unittest.main()
