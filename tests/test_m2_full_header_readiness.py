from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import optical_input_readiness_core_full_cohort_001 as OPTICAL  # noqa: E402
import radar_input_readiness_core_full_cohort_001 as RADAR  # noqa: E402
import m2_header_stage_gate as GATE  # noqa: E402


RADAR_REF = "config/qa/radar-input-readiness-contract-full-cohort-001.json"
OPTICAL_REF = "config/qa/optical-input-readiness-contract-full-cohort-001.json"


def load(ref):
    return json.loads((ROOT / ref).read_text(encoding="utf-8"))


class FullHeaderReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.radar = load(RADAR_REF)
        cls.optical = load(OPTICAL_REF)

    def test_radar_contract_is_valid_exact_six_source_cohort(self):
        self.assertEqual(RADAR.validate_contract(self.radar), [])
        self.assertEqual([item["source_id"] for item in self.radar["sources"]], [f"M1-SRC-{value:03d}" for value in range(1, 7)])
        self.assertEqual([item["event_role"] for item in self.radar["sources"]], ["before", "before", "before", "after", "after", "after"])

    def test_radar_contract_preserves_detected_correction_and_history(self):
        self.assertEqual(self.radar["metadata_checks"]["pixel_value"], "Detected")
        self.assertEqual(self.radar["history"]["real_001_status"], "block_preserved")
        self.assertTrue(self.radar["history"]["detected_label_correction_preserved"])
        self.assertEqual(self.radar["history"]["real_003_maximum_invocations"], 1)

    def test_radar_materialization_receipts_and_manifests_are_exactly_bound(self):
        for item in self.radar["sources"]:
            receipt = ROOT / item["materialization_receipt_ref"]
            self.assertEqual(hashlib.sha256(receipt.read_bytes()).hexdigest(), item["materialization_receipt_sha256"])
            self.assertEqual(load(item["materialization_receipt_ref"])["bindings"]["external_manifest_sha256"], item["external_manifest_sha256"])

    def test_radar_aggregate_pass_and_block_are_deterministic(self):
        passed = {source: {"status": "pass_header_readability_only"} for source in [f"M1-SRC-{value:03d}" for value in range(1, 7)]}
        self.assertEqual(RADAR.summarize_full_readiness(passed)["status"], "pass_full_radar_header_readiness_only")
        blocked = copy.deepcopy(passed)
        blocked["M1-SRC-006"]["status"] = "block"
        self.assertEqual(RADAR.summarize_full_readiness(blocked)["status"], "block")

    def test_optical_contract_is_valid_exact_pair(self):
        self.assertEqual(OPTICAL.validate_contract(self.optical), [])
        self.assertEqual(self.optical["route"]["before_source_id"], "M1-SRC-010")
        self.assertEqual(self.optical["route"]["after_source_id"], "M1-SRC-008")
        self.assertEqual(self.optical["route"]["pair_id"], "PAIR-S2-RUM-R119")

    def test_optical_contract_binds_exact_materializations(self):
        for role, source in (("before", "M1-SRC-010"), ("after", "M1-SRC-008")):
            item = self.optical["materializations"][role]
            self.assertEqual(item["source_id"], source)
            self.assertEqual(hashlib.sha256((ROOT / item["receipt_ref"]).read_bytes()).hexdigest(), item["receipt_sha256"])

    def test_both_contracts_prohibit_pixels_network_and_mutation(self):
        self.assertEqual(self.radar["execution_boundary"]["pixel_value_decoding"], "prohibited_header_and_metadata_reads_only")
        self.assertEqual(self.optical["execution_boundary"]["pixel_value_reads"], "prohibited_header_and_identity_reads_only")
        for contract in (self.radar, self.optical):
            self.assertEqual(contract["execution_boundary"]["network_requests"], "prohibited")
            self.assertEqual(contract["execution_boundary"]["external_data_mutation"], "prohibited")
            self.assertFalse(contract["claim_boundary"]["pixel_values_examined"])
            self.assertFalse(contract["claim_boundary"]["scientific_admission_authorized"])

    def test_contract_execution_file_hashes_match(self):
        for contract in (self.radar, self.optical):
            for key in ("core", "runner", "arcgis_adapter"):
                ref = contract["inputs"][f"{key}_ref"]
                self.assertEqual(hashlib.sha256((ROOT / ref).read_bytes()).hexdigest(), contract["inputs"][f"{key}_sha256"])

    def test_real_runners_require_exact_output_identities(self):
        radar = (ROOT / "scripts/inspect_radar_inputs_arcgis_full_cohort_001.py").read_text(encoding="utf-8")
        optical = (ROOT / "scripts/inspect_optical_inputs_arcgis_full_cohort_001.py").read_text(encoding="utf-8")
        self.assertIn("m2-s1-input-readiness-real-003.json", radar)
        self.assertIn("m2-s2-input-readiness-real-001.json", optical)
        self.assertIn("unexpected_optical_materialization_pair", optical)
        self.assertIn("GDAL_PAM_ENABLED", optical)
        self.assertIn("external_materialization_inventory_unchanged", optical)

    def test_final_preflight_has_no_arcpy_or_pixel_reader(self):
        text = (ROOT / "scripts/preflight_m2_full_header_readiness.py").read_text(encoding="utf-8")
        self.assertNotIn("import arcpy", text)
        self.assertNotIn("RasterToNumPyArray", text)
        self.assertIn("selected_members_rehashed", text)

    def test_gate_rejects_missing_or_nonpassing_publication(self):
        approval = {"status": "approved_exact_dependency_ordered_bounded_actions"}
        materialization = {"status": "pass_all_eight_materialized_identity_only"}
        preflight = {"status": "pass_exact_header_inputs_ready_no_real_header_access", "bindings": {"publication_gate_sha256": "x"}, "assertions": {"real_raster_headers_opened": False, "measurement_pixels_decoded": False, "real_attempt_outputs_absent": True}}
        with (
            mock.patch.object(GATE, "load", side_effect=[approval, materialization, {"status": "pending"}, preflight]),
            mock.patch.object(GATE, "git_identity", return_value=("a", "a")),
        ):
            with self.assertRaises(GATE.HeaderGateError):
                GATE.validate_header_stage_execution()

    def test_synthetic_adapters_do_not_reference_real_receipts(self):
        for ref in ("scripts/validate_radar_input_readiness_arcgis_full_cohort_001.py", "scripts/validate_optical_input_readiness_arcgis_full_cohort_001.py"):
            text = (ROOT / ref).read_text(encoding="utf-8")
            self.assertIn("external_custody_accessed", text)
            self.assertIn("real_materialization_receipt", text)


if __name__ == "__main__":
    unittest.main()
