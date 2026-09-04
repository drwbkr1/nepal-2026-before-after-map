from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arcgis_final_delivery_core import (  # noqa: E402
    EXPECTED_DATASETS,
    EXPECTED_LAYOUT_ELEMENTS,
    EXPECTED_MAPS,
    EXPECTED_RELATIONSHIPS,
    evaluate_report,
    validate_contract,
)


CONTRACT_PATH = ROOT / "config/qa/arcgis-final-delivery-contract.json"


def passing_report() -> dict:
    return {
        "report_version": "1.0",
        "runtime": {
            "environment_type": "clean_local_profile",
            "original_workspace_absent": True,
            "package_created": True,
            "package_extracted": True,
            "project_reopened": True,
            "reexport_succeeded": True,
        },
        "project": {
            "map_wkid": 32645,
            "broken_source_count": 0,
            "external_operational_source_count": 0,
            "operational_source_count": 12,
            "domain_count": 14,
            "relationship_count": 8,
            "dataset_names": sorted(EXPECTED_DATASETS),
            "relationship_names": sorted(EXPECTED_RELATIONSHIPS),
        },
        "artifacts": {
            "manifest_verified": True,
            "all_sha256_verified": True,
            "unsafe_path_count": 0,
            "missing_count": 0,
            "rights_conflict_count": 0,
            "by_class": {
                "arcgis_project": 1,
                "file_geodatabase": 1,
                "layer_file": 5,
                "analysis_geotiff": 2,
                "interoperable_geopackage": 1,
                "project_package": 1,
                "map_png": 5,
                "map_pdf": 5,
                "artifact_manifest": 1,
                "delivery_readme": 1,
            },
        },
        "maps": {
            name: {
                "layout_exists": True,
                "png_exists": True,
                "pdf_exists": True,
                "visual_review": "pass",
                "elements": sorted(EXPECTED_LAYOUT_ELEMENTS),
            }
            for name in EXPECTED_MAPS
        },
        "evidence": {
            "scientific_record_count": 2,
            "non_success_record_count": 2,
            "observed_source_links_complete": True,
            "every_observation_has_before_after": True,
            "source_identity_reconciled": True,
            "acquisition_dates_present": True,
            "uncertainty_complete": True,
            "limitations_complete": True,
            "interpretation_links_complete": True,
            "attribution_links_complete": True,
            "observation_interpretation_attribution_separate": True,
            "all_failed_deferred_inconclusive_reconciled": True,
            "qa_records_complete": True,
            "owner_review_complete": True,
        },
        "spatial": {
            "scientific_vector_wkids": [32645],
            "analysis_raster_wkids": [32645, 32645],
            "grid_metadata_complete": True,
            "registration_qa_pass": True,
            "exclusion_masks_present": True,
        },
        "claim_boundary": {
            "m5_review_complete": True,
            "public_release_authorized_by_report": False,
            "emergency_guidance": False,
        },
    }


class ArcGISFinalDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_tracked_contract_is_valid_and_predeclared(self) -> None:
        self.assertEqual(validate_contract(self.contract), [])
        self.assertEqual(self.contract["status"], "predeclared_not_executed")
        self.assertFalse(self.contract["claim_boundary"]["current_m6_complete"])

    def test_complete_future_report_passes_m6_delivery_only(self) -> None:
        decision = evaluate_report(passing_report(), self.contract)
        self.assertEqual(decision["status"], "pass_m6_delivery_only")
        self.assertTrue(decision["m6_delivery_acceptance_established"])
        self.assertFalse(decision["public_release_authorized"])

    def test_no_scientific_observation_defers(self) -> None:
        report = passing_report()
        report["evidence"]["scientific_record_count"] = 0
        decision = evaluate_report(report, self.contract)
        self.assertEqual(decision["status"], "defer")
        self.assertTrue(any("no reviewed scientific observation" in item for item in decision["defer_reasons"]))

    def test_external_source_or_wrong_crs_blocks(self) -> None:
        report = passing_report()
        report["project"]["external_operational_source_count"] = 1
        report["spatial"]["analysis_raster_wkids"] = [4326]
        decision = evaluate_report(report, self.contract)
        self.assertEqual(decision["status"], "block")
        self.assertTrue(any("outside the package" in item for item in decision["block_reasons"]))
        self.assertTrue(any("raster CRS" in item for item in decision["block_reasons"]))

    def test_missing_limitations_map_or_layout_elements_blocks(self) -> None:
        report = passing_report()
        del report["maps"]["limitations_map"]
        decision = evaluate_report(report, self.contract)
        self.assertEqual(decision["status"], "block")
        self.assertIn("required map set is incomplete", decision["block_reasons"])

    def test_obscured_failure_history_or_merged_claim_layers_blocks(self) -> None:
        report = passing_report()
        report["evidence"]["all_failed_deferred_inconclusive_reconciled"] = False
        report["evidence"]["observation_interpretation_attribution_separate"] = False
        decision = evaluate_report(report, self.contract)
        self.assertEqual(decision["status"], "block")
        self.assertTrue(any("all_failed_deferred_inconclusive_reconciled" in item for item in decision["block_reasons"]))
        self.assertTrue(any("observation_interpretation_attribution_separate" in item for item in decision["block_reasons"]))

    def test_pending_visual_or_clean_environment_review_defers(self) -> None:
        report = passing_report()
        report["runtime"]["environment_type"] = "same_machine_existing_profile"
        report["maps"]["evidence_map"]["visual_review"] = "pending"
        decision = evaluate_report(report, self.contract)
        self.assertEqual(decision["status"], "defer")
        self.assertTrue(any("independent environment" in item for item in decision["defer_reasons"]))
        self.assertTrue(any("visual review" in item for item in decision["defer_reasons"]))

    def test_report_cannot_authorize_public_release(self) -> None:
        report = copy.deepcopy(passing_report())
        report["claim_boundary"]["public_release_authorized_by_report"] = True
        decision = evaluate_report(report, self.contract)
        self.assertEqual(decision["status"], "invalid")
        self.assertTrue(any("overstates publication" in item for item in decision["errors"]))


if __name__ == "__main__":
    unittest.main()
