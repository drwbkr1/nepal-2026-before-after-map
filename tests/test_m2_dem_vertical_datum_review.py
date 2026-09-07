from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class M2DemVerticalDatumReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proposal = load("contracts/m2-dem-vertical-datum-proposal.json")
        cls.sources = load("records/source-gates/m2-dem-vertical-datum-source-review.json")
        cls.capability = load("records/surface-receipts/m2-dem-vertical-datum-capability.json")
        cls.bundle = load("reviews/m2-dem-vertical-datum/review-bundle.json")
        cls.contract = load("reviews/m2-dem-vertical-datum/review-contract.json")
        cls.blank = load("reviews/m2-dem-vertical-datum/blank-response.json")
        cls.reconciliation = load("records/source-gates/m2-dem-vertical-datum-review-reconciliation.json")
        cls.approval = load("records/source-gates/m2-dem-vertical-datum-approval.json")
        cls.control = load("records/readiness/m2-dem-vertical-datum-control-reconciliation.json")
        cls.profile = load("records/project-control-profile.json")
        cls.goal = load("records/long-term-goal.json")
        cls.milestone = load("contracts/milestone-002.json")

    def test_proposal_selects_exact_egm2008_preconversion_only(self) -> None:
        self.assertEqual(self.proposal["status"], "proposed_not_active")
        selected = self.proposal["selected_if_approved"]
        self.assertEqual(selected["required_arcgis_component"]["feature"], "world1x1_vert")
        self.assertEqual(selected["required_arcgis_component"]["expected_grid"], "Dataset_egm2008-1.grd")
        self.assertEqual(selected["required_arcgis_component"]["expected_wkid"], 110018)
        self.assertEqual(selected["radar_tool_parameter_after_conversion"], "NONE")
        self.assertEqual(selected["egm96_builtin_route"]["production_status"], "not_selected")

    def test_proposal_preserves_owner_install_and_science_boundaries(self) -> None:
        excluded = set(self.proposal["actions_not_authorized"])
        self.assertIn("download or install software or coordinate-system data", excluded)
        self.assertIn("approve or dismiss UAC or another privileged prompt", excluded)
        self.assertIn("use raw EGM2008 orthometric tiles with NONE", excluded)
        self.assertFalse(self.proposal["claim_boundary"]["method_decision_approved"])
        self.assertFalse(self.proposal["claim_boundary"]["radar_processing_executed"])

    def test_official_source_review_and_local_capability_are_deferred(self) -> None:
        roles = {item["role"] for item in self.sources["official_sources"]}
        self.assertEqual(len(roles), 8)
        self.assertIn("arcgis_radiometric_terrain_flattening", roles)
        self.assertIn("copernicus_dem_vertical_reference", roles)
        self.assertIn("arcgis_supported_vertical_transformations", roles)
        self.assertEqual(self.capability["status"], "defer_exact_egm2008_grid_not_installed")
        self.assertFalse(self.capability["decision"]["exact_egm2008_preconversion_available_now"])
        self.assertTrue(self.capability["decision"]["arcgis_builtin_egm96_sensitivity_available_now"])
        self.assertEqual(self.capability["inspection"]["listed_transformations"], [])

    def test_review_bundle_and_contract_bind_exact_bytes(self) -> None:
        proposal_sha = sha256("contracts/m2-dem-vertical-datum-proposal.json")
        self.assertEqual(
            self.bundle["candidate_identity"],
            f"M2-DEM-VERTICAL-DATUM-PROPOSAL-SHA256:{proposal_sha}",
        )
        self.assertEqual(
            self.contract["review_bundle"]["manifest_sha256"],
            sha256("reviews/m2-dem-vertical-datum/review-bundle.json"),
        )
        for artifact in self.bundle["artifacts"]:
            self.assertEqual(artifact["sha256"], sha256(artifact["path"]))
            for receipt in artifact["render_receipts"]:
                self.assertEqual(receipt["sha256"], sha256(receipt["path"]))

    def test_blank_response_has_no_human_decision(self) -> None:
        self.assertFalse(self.blank["completed"])
        self.assertFalse(self.blank["reviewer"]["attestation"])
        self.assertEqual(len(self.blank["responses"]), 1)
        self.assertEqual(
            self.blank["responses"][0]["evidence_sha256"],
            sha256("reviews/m2-dem-vertical-datum/review-bundle.json"),
        )
        self.assertIsNone(self.blank["responses"][0]["decision"])

    def test_exact_owner_approval_is_locked_and_reconciled(self) -> None:
        self.assertEqual(self.reconciliation["status"], "reconciled_exact_human_response")
        self.assertEqual(self.reconciliation["human_decision_count"], 1)
        self.assertEqual(self.reconciliation["decision_counts"], {"approve": 1, "revise": 0, "defer": 0})
        self.assertFalse(self.reconciliation["human_decisions_fabricated"])
        self.assertFalse(self.reconciliation["downstream_authorization_created"])
        self.assertEqual(
            self.approval["review_bundle_manifest_sha256"],
            sha256("reviews/m2-dem-vertical-datum/review-bundle.json"),
        )
        self.assertEqual(self.approval["proposal_sha256"], sha256("contracts/m2-dem-vertical-datum-proposal.json"))
        self.assertEqual(
            self.approval["review_reconciliation_sha256"],
            sha256("records/source-gates/m2-dem-vertical-datum-review-reconciliation.json"),
        )
        self.assertEqual(self.approval["locked_response_sha256"], self.reconciliation["response_sha256"])
        self.assertEqual(self.approval["lock_receipt_sha256"], self.reconciliation["receipt_sha256"])
        self.assertTrue(self.approval["attestation"])

    def test_approval_selects_method_without_claiming_installation_or_conversion(self) -> None:
        selected = self.approval["selected_method"]
        self.assertEqual(selected["route"], "arcgis_egm2008_1x1_preconversion_then_none")
        self.assertEqual(selected["required_feature"], "world1x1_vert")
        self.assertEqual(selected["required_grid"], "Dataset_egm2008-1.grd")
        self.assertEqual(selected["required_transformation_wkid"], 110018)
        self.assertEqual(selected["radar_geoid_parameter_for_verified_derivatives"], "NONE")
        self.assertEqual(selected["egm96_route_role"], "labeled_sensitivity_only")
        self.assertEqual(self.approval["owner_prerequisite"]["status"], "pending_owner_installation")
        self.assertFalse(self.approval["owner_prerequisite"]["codex_installation_authorized"])
        self.assertTrue(self.approval["claim_boundary"]["method_decision_approved"])
        for field in (
            "arcgis_coordinate_systems_data_installed",
            "egm2008_grid_in_project_custody",
            "dem_preconversion_executed",
            "vertical_datum_resolved_for_radar",
            "orbit_application_executed",
            "radar_processing_executed",
            "baseline_or_change_analysis_executed",
            "scientific_result_established",
        ):
            self.assertFalse(self.approval["claim_boundary"][field])

    def test_control_state_stops_at_owner_component_installation(self) -> None:
        checkpoint = "M2-DEM-EGM2008-COMPONENT-INSTALL"
        self.assertEqual(self.control["status"], "pass_method_selected_owner_component_install_pending")
        self.assertEqual(self.control["bindings"]["approval_sha256"], sha256("records/source-gates/m2-dem-vertical-datum-approval.json"))
        self.assertEqual(self.control["decision"]["current_checkpoint"], checkpoint)
        self.assertTrue(self.control["assertions"]["vertical_datum_method_selected"])
        self.assertFalse(self.control["assertions"]["arcgis_coordinate_systems_data_installed"])
        self.assertFalse(self.control["assertions"]["dem_preconversion_executed"])
        self.assertFalse(self.control["assertions"]["vertical_datum_resolved_for_radar"])
        self.assertEqual(self.profile["current_checkpoint"]["checkpoint_id"], checkpoint)
        self.assertEqual(self.goal["current_checkpoint"], checkpoint)
        self.assertEqual(self.goal["parallel_checkpoints"], [checkpoint])
        self.assertEqual(self.milestone["handoff"]["current_checkpoint"], checkpoint)
        units = {unit["id"]: unit for unit in self.milestone["units"]}
        self.assertEqual(units["M2-DEM-VERTICAL-DATUM-REVIEW"]["status"], "complete")
        self.assertEqual(units[checkpoint]["status"], "planned")
        self.assertEqual(units["M2-DEM-VERTICAL-DATUM-CONVERSION"]["status"], "planned")
        self.assertFalse(units[checkpoint]["gates"]["codex_download_or_install_authorized"])


if __name__ == "__main__":
    unittest.main()
