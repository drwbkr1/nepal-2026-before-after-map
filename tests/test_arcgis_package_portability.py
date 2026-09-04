from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arcgis_package_portability_core import (  # noqa: E402
    EXPECTED_DATASET_COUNTS,
    evaluate_runtime,
    inventory_sha256,
    inventory_summary,
    stable_inventory,
    validate_contract,
)


def contract_fixture() -> dict:
    return {
        "contract_id": "NEPAL-M6-ARCGIS-PACKAGE-PORTABILITY-001",
        "status": "predeclared_not_executed",
        "analysis_crs": {"wkid": 32645},
        "source_workspace": {
            "root": r"C:\Projects\Active\nepal-2026-before-after-map\scratch\arcgis-evidence-workspace-attempt-006",
            "project": "Nepal_2026_Evidence.aprx",
            "geodatabase": "Nepal_2026_Evidence.gdb",
            "overview_png": "Evidence_Workspace_Overview.png",
            "overview_pdf": "Evidence_Workspace_Overview.pdf",
            "project_sha256": "a" * 64,
            "overview_png_sha256": "b" * 64,
            "overview_pdf_sha256": "c" * 64,
            "expected_inventory": {
                "file_count": 110,
                "total_bytes": 1171536,
                "inventory_sha256": "f8f3c94f77c904954d729c7340d82a09183ad52671736e3d1d80f6609b67617a",
            },
            "expected_dataset_counts": EXPECTED_DATASET_COUNTS,
        },
        "external_output": {
            "root": r"C:\Projects\Active\nepal-2026-before-after-map-data\derived\arcgis-package-portability\attempt-001",
            "package": "Nepal_2026_Evidence.ppkx",
            "extract_root": "extracted",
            "reexport_png": "reexport/Evidence_Workspace_Overview.png",
            "reexport_pdf": "reexport/Evidence_Workspace_Overview.pdf",
            "manifest": "stable-manifest.json",
            "receipt": "receipt.json",
            "failure_receipt": "failure.json",
        },
        "operation": {
            "sharing_internal": "EXTERNAL",
            "package_as_template": "PROJECT_PACKAGE",
            "version": "3.7",
            "include_toolboxes": "NO_TOOLBOXES",
            "include_history_items": "NO_HISTORY_ITEMS",
            "read_only": "READ_WRITE",
            "select_related_rows": "KEEP_ALL_RELATED_ROWS",
            "preserve_sqlite": "CONVERT_SQLITE",
            "extract_cache": "NO_CACHE",
        },
        "execution_boundary": {
            "network_requests": "prohibited",
            "authentication": "prohibited",
            "credential_access": "prohibited",
            "source_workspace_mutation": "prohibited",
            "scientific_data_inclusion": "prohibited_metadata_only",
            "output_collision": "stop",
            "output_location": "external_non_git_append_only",
        },
        "required_checks": {
            "expected_dataset_counts": EXPECTED_DATASET_COUNTS,
            "forbidden_extracted_suffixes": [".crf", ".h5", ".hdf", ".img", ".jp2", ".nc", ".tif", ".tiff", ".vrt"],
            "required_operational_layer_count": 3,
            "required_basemap_layer_count": 0,
            "maximum_package_bytes": 50_000_000,
            "maximum_extracted_stable_files": 500,
        },
        "claim_boundary": {
            "clean_machine_portability_established": False,
            "cross_version_portability_established": False,
            "satellite_pixels_packaged": False,
            "dem_pixels_packaged": False,
            "scientific_evidence_packaged": False,
            "mapped_change_established": False,
            "scientific_admission_authorized": False,
            "m6_complete": False,
            "current_checkpoint_changed": False,
        },
    }


def passing_report(contract: dict) -> dict:
    expected = contract["source_workspace"]["expected_inventory"]
    return {
        "source": {"before": expected, "after": expected, "unchanged": True},
        "package": {"exists": True, "size_bytes": 1000, "sha256": "d" * 64},
        "extracted": {"stable_file_count": 20, "forbidden_raster_files": [], "symlink_count": 0},
        "extracted_project": {
            "project_count": 1,
            "map_count": 1,
            "layout_count": 1,
            "map_wkid": 32645,
            "broken_layer_count": 0,
            "external_operational_source_count": 0,
            "basemap_layer_count": 0,
            "operational_geodatabase_count": 1,
            "layers": [{}, {}, {}],
            "dataset_counts": EXPECTED_DATASET_COUNTS,
            "scientific_record_count": 0,
            "relationship_count": 8,
            "domain_count": 14,
        },
        "reexports": {
            "png_exists": True,
            "pdf_exists": True,
            "png_size_bytes": 100,
            "pdf_size_bytes": 200,
            "png_sha256": "e" * 64,
            "pdf_sha256": "f" * 64,
            "png_dimensions": [1760, 1360],
            "png_pixel_sha256_matches_source": True,
        },
    }


class ArcGISPackagePortabilityTests(unittest.TestCase):
    def test_tracked_contract_is_valid(self) -> None:
        contract = json.loads(
            (ROOT / "config/qa/arcgis-package-portability-contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validate_contract(contract), [])

    def test_contract_is_bounded(self) -> None:
        self.assertEqual(validate_contract(contract_fixture()), [])

    def test_contract_rejects_network_or_scientific_claim(self) -> None:
        contract = contract_fixture()
        contract["execution_boundary"]["network_requests"] = "allowed"
        contract["claim_boundary"]["m6_complete"] = True
        errors = validate_contract(contract)
        self.assertTrue(any("network_requests" in item for item in errors))
        self.assertTrue(any("overstates" in item for item in errors))

    def test_inventory_is_deterministic_and_excludes_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.txt").write_text("b", encoding="utf-8")
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "transient.lock").write_text("lock", encoding="utf-8")
            first = stable_inventory(root)
            second = stable_inventory(root)
            self.assertEqual([item["relative_path"] for item in first], ["a.txt", "b.txt"])
            self.assertEqual(inventory_sha256(first), inventory_sha256(second))
            self.assertEqual(inventory_summary(first)["total_bytes"], 2)

    def test_runtime_pass_is_limited_and_requires_visual_review(self) -> None:
        contract = contract_fixture()
        decision = evaluate_runtime(passing_report(contract), contract)
        self.assertEqual(decision["status"], "pass_same_machine_runtime_manual_visual_review_pending")
        self.assertTrue(decision["same_machine_round_trip_established"])
        self.assertTrue(decision["manual_visual_review_required"])
        self.assertFalse(decision["m6_complete"])

    def test_runtime_blocks_external_layer_reference(self) -> None:
        contract = contract_fixture()
        report = passing_report(contract)
        report["extracted_project"]["external_operational_source_count"] = 1
        decision = evaluate_runtime(report, contract)
        self.assertEqual(decision["status"], "fail_retained")

    def test_runtime_blocks_scientific_rows(self) -> None:
        contract = contract_fixture()
        report = passing_report(contract)
        report["extracted_project"]["dataset_counts"] = copy.deepcopy(EXPECTED_DATASET_COUNTS)
        report["extracted_project"]["dataset_counts"]["ObservedChange"] = 1
        report["extracted_project"]["scientific_record_count"] = 1
        decision = evaluate_runtime(report, contract)
        self.assertEqual(decision["status"], "fail_retained")


if __name__ == "__main__":
    unittest.main()
