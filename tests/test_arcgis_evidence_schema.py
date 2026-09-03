"""Portable tests for the ArcGIS evidence schema and retained receipt."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "config/arcgis/evidence-workspace-schema.json"
RECEIPT_PATH = ROOT / "records/surface-receipts/arcgis-evidence-workspace.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ArcGISEvidenceSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        cls.receipt = load_json(RECEIPT_PATH)
        cls.datasets = {item["name"]: item for item in cls.schema["datasets"]}

    def test_workspace_has_expected_projected_structure(self) -> None:
        self.assertEqual(self.schema["analysis_crs"]["wkid"], 32645)
        self.assertEqual(len(self.datasets), 9)
        self.assertEqual(len(self.schema["domains"]), 14)
        self.assertEqual(len(self.schema["relationships"]), 8)

    def test_observation_interpretation_and_attribution_are_distinct(self) -> None:
        self.assertEqual(self.datasets["ObservedChange"]["kind"], "feature_class")
        self.assertEqual(self.datasets["Interpretations"]["kind"], "table")
        self.assertEqual(self.datasets["AttributionAssessments"]["kind"], "table")
        relationship_names = {item["name"] for item in self.schema["relationships"]}
        self.assertIn("ObservedChange_Interpretations", relationship_names)
        self.assertIn("Interpretations_Attribution", relationship_names)
        self.assertIn("ObservedChange_ObservationSources", relationship_names)
        self.assertIn("SourceProducts_ObservationSources", relationship_names)

    def test_initial_state_contains_metadata_but_no_scientific_records(self) -> None:
        expected_counts = {
            "StudyAreas": 3,
            "SourceProducts": 10,
            "ObservedChange": 0,
            "AnalysisExclusions": 0,
            "StableControls": 0,
            "ObservationSources": 0,
            "Interpretations": 0,
            "AttributionAssessments": 0,
            "AnalysisQA": 0,
        }
        self.assertEqual(self.schema["initial_counts"], expected_counts)

    def test_failure_and_uncertainty_states_remain_representable(self) -> None:
        record_states = set(self.schema["domains"]["DOM_RECORD_STATUS"]["coded_values"])
        self.assertTrue(
            {"rejected", "deferred", "inconclusive", "invalid", "superseded"}.issubset(record_states)
        )
        qa_states = set(self.schema["domains"]["DOM_QA_STATUS"]["coded_values"])
        self.assertTrue({"fail", "inconclusive", "invalid"}.issubset(qa_states))

    def test_receipt_binds_public_inputs_and_preview(self) -> None:
        inputs = self.receipt["inputs"]
        for path_key, hash_key in (
            ("schema", "schema_sha256"),
            ("approved_aoi", "approved_aoi_sha256"),
            ("source_manifest", "source_manifest_sha256"),
            ("manifest_approval", "manifest_approval_sha256"),
            ("builder", "builder_sha256"),
        ):
            path = ROOT / inputs[path_key]
            self.assertTrue(path.is_file())
            self.assertEqual(sha256(path), inputs[hash_key])
        preview = ROOT / self.receipt["public_preview"]["path"]
        self.assertEqual(sha256(preview), self.receipt["public_preview"]["sha256"])

    def test_receipt_records_native_validation_and_empty_claim_surface(self) -> None:
        self.assertEqual(self.receipt["status"], "pass_with_retained_failures")
        self.assertEqual(self.receipt["runtime"], {
            "product": "ArcGISPro",
            "version": "3.7.1",
            "license_level": "Advanced",
        })
        self.assertEqual(self.receipt["checks"]["visual_inspection"], "pass")
        self.assertEqual(self.receipt["project"]["map_spatial_reference_wkid"], 32645)
        self.assertEqual(
            {name: item["row_count"] for name, item in self.receipt["workspace"]["datasets"].items()},
            self.schema["initial_counts"],
        )
        self.assertEqual(len(self.receipt["retained_failures"]), 6)
        self.assertEqual(
            {item["status"] for item in self.receipt["retained_failures"]},
            {"fail", "fail_visual"},
        )
        self.assertIn("No satellite pixels", self.schema["claim_boundary"])
        self.assertTrue(any("No satellite pixels" in item for item in self.receipt["limitations"]))


if __name__ == "__main__":
    unittest.main()
