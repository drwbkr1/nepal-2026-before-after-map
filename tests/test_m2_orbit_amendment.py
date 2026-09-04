from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AMENDMENT = load_module("prepare_m2_orbit_amendment", "scripts/prepare_m2_orbit_amendment.py")
CONTROLS = load_module("prepare_m2_orbit_controls", "scripts/prepare_m2_orbit_controls.py")


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2OrbitAmendmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = read_json("records/source-gates/m2-orbit-metadata-receipt.json")
        cls.manifest = read_json("records/source-gates/m2-orbit-candidate-manifest.json")
        cls.gate = read_json("records/source-gates/m2-orbit-source-gate.json")
        cls.proposal = read_json("contracts/milestone-002-orbit-amendment-proposal.json")
        cls.intake = read_json("contracts/m2-orbit-intake-candidate.json")
        cls.verification = read_json("contracts/m2-orbit-offline-verification-candidate.json")
        cls.surface = read_json("records/surface-receipts/m2-orbit-amendment-review.json")
        cls.bundle = read_json("reviews/m2-orbit-amendment/review-bundle.json")
        cls.contract = read_json("reviews/m2-orbit-amendment/review-contract.json")
        cls.blank = read_json("reviews/m2-orbit-amendment/blank-response.json")

    def test_exact_four_file_boundary_covers_six_sentinel_sources(self) -> None:
        self.assertEqual(
            {record["source_id"] for record in self.manifest["records"]},
            {"M2-ORB-001", "M2-ORB-002", "M2-ORB-003", "M2-ORB-004"},
        )
        covered = {source_id for record in self.manifest["records"] for source_id in record["sentinel_source_ids"]}
        self.assertEqual(covered, {f"M1-SRC-{index:03d}" for index in range(1, 7)})
        self.assertEqual(self.manifest["summary"]["covered_sentinel_source_count"], 6)

    def test_selected_candidates_follow_declared_temporal_margin_rule(self) -> None:
        for group in self.receipt["searches"]:
            resorb = next(item for item in group["searches"] if item["orbit_type"] == "RESORB")
            selected = AMENDMENT.select_candidate(resorb["candidates"])
            self.assertEqual(selected["provider_product_id"], group["selected_provider_product_id"])
            record = next(item for item in self.manifest["records"] if item["group_id"] == group["group_id"])
            self.assertEqual(record["provider_product_id"], selected["provider_product_id"])
            self.assertGreaterEqual(record["minimum_scene_margin_seconds"], 3600)

    def test_no_precise_orbit_candidate_was_available(self) -> None:
        poe_counts = [
            search["candidate_count"]
            for group in self.receipt["searches"]
            for search in group["searches"]
            if search["orbit_type"] == "POEORB"
        ]
        self.assertEqual(poe_counts, [0, 0, 0, 0])
        self.assertEqual(self.manifest["summary"]["precise_covering_file_count_at_assessment"], 0)

    def test_metadata_capture_requested_no_payload_or_credentials(self) -> None:
        assertions = self.receipt["assertions"]
        self.assertFalse(assertions["payload_bytes_requested"])
        self.assertFalse(assertions["authentication_used"])
        self.assertFalse(assertions["credential_values_read_or_recorded"])
        self.assertFalse(assertions["authority_created"])
        self.assertEqual(
            self.manifest["rights"]["legal_notice_sha256"],
            "fa2955ff48a1d82e77fc7296d63681670ecdb9d2811a0505ae60d0683b62fa64",
        )

    def test_source_gate_is_blocked_only_on_scope_authority(self) -> None:
        self.assertEqual(self.gate["decision"]["status"], "blocked")
        self.assertEqual(len(self.gate["decision"]["blocking_reasons"]), 1)
        for source in self.gate["sources"]:
            statuses = {criterion["id"]: criterion["status"] for criterion in source["criteria"]}
            self.assertEqual(statuses["scope-authority"], "unknown")
            self.assertTrue(all(value == "pass" for key, value in statuses.items() if key != "scope-authority"))
        self.assertNotIn(
            "download the four exact restituted orbit files with an existing secret-safe owner token reference",
            self.gate["decision"]["approved_actions"],
        )

    def test_proposal_binds_current_sources_without_granting_authority(self) -> None:
        self.assertEqual(self.proposal["status"], "proposed_not_active")
        self.assertEqual(self.proposal["candidate_manifest_sha256"], sha256("records/source-gates/m2-orbit-candidate-manifest.json"))
        self.assertEqual(self.proposal["metadata_receipt_sha256"], sha256("records/source-gates/m2-orbit-metadata-receipt.json"))
        self.assertEqual(self.proposal["source_gate_sha256"], sha256("records/source-gates/m2-orbit-source-gate.json"))
        self.assertEqual(self.proposal["authority"]["mode"], "not_granted")
        self.assertIn("silently substitute later precise orbit files", self.proposal["authority"]["not_requested"])

    def test_candidate_controls_are_deterministic_and_non_authorizing(self) -> None:
        rebuilt_intake = CONTROLS.build_intake()
        self.assertEqual(rebuilt_intake, self.intake)
        intake_sha = hashlib.sha256(CONTROLS.canonical_bytes(rebuilt_intake)).hexdigest()
        rebuilt_verification = CONTROLS.build_verification(intake_sha)
        self.assertEqual(rebuilt_verification, self.verification)
        self.assertEqual(CONTROLS.validate(rebuilt_intake, rebuilt_verification), [])
        self.assertTrue(all(asset["state"] == "not_authorized" for asset in self.intake["assets"]))
        self.assertFalse(self.verification["application_boundary"]["radar_pixel_processing_authorized_by_this_contract"])

    def test_manifest_summary_matches_exact_records(self) -> None:
        total = sum(record["content_length_bytes"] for record in self.manifest["records"])
        self.assertEqual(total, 2_539_715)
        self.assertEqual(total, self.manifest["summary"]["combined_content_length_bytes"])
        self.assertTrue(all(record["orbit_type"] == "AUX_RESORB" for record in self.manifest["records"]))

    def test_review_packet_is_exactly_bound_and_contains_zero_decisions(self) -> None:
        proposal_sha = sha256("contracts/milestone-002-orbit-amendment-proposal.json")
        bundle_sha = sha256("reviews/m2-orbit-amendment/review-bundle.json")
        self.assertEqual(proposal_sha, "b17e256068759946be611bf4e7beffe0d3121e9e731b6c42163525eca2cf0292")
        self.assertEqual(bundle_sha, "ee5fbf4933b52be8f97441b78a73559a973bd975efc21b43625f1ceca54e2ff1")
        self.assertEqual(self.bundle["candidate_identity"], f"M2-ORBIT-AMENDMENT-PROPOSAL-SHA256:{proposal_sha}")
        self.assertEqual(self.contract["review_bundle"]["manifest_sha256"], bundle_sha)
        self.assertEqual(self.surface["surface_sha256"], sha256("docs/assets/m2-orbit-amendment-review.png"))
        self.assertEqual(self.surface["human_decision_count"], 0)
        self.assertFalse(self.blank["completed"])
        self.assertEqual(self.blank["reviewer"], {"attestation": False})
        self.assertEqual(len(self.blank["responses"]), 1)
        self.assertIsNone(self.blank["responses"][0]["decision"])
        self.assertEqual(self.blank["responses"][0]["evidence_sha256"], bundle_sha)


if __name__ == "__main__":
    unittest.main()
