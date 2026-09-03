from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "prepare_m2_verification.py"
SPEC = importlib.util.spec_from_file_location("prepare_m2_verification", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

CREATED_AT = "2026-09-03T16:43:33Z"


class M2OfflineVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan_path = ROOT / "records/acquisition-plan.json"
        cls.intake_path = ROOT / "contracts/m2-intake-candidate.json"
        cls.approval_path = ROOT / "records/source-gates/source-manifest-approval.json"
        cls.bundle_path = ROOT / "reviews/m2-activation/review-bundle.json"
        cls.manifest_path = ROOT / "records/source-manifest.json"
        cls.plan = MODULE.load_json(cls.plan_path)
        cls.intake = MODULE.load_json(cls.intake_path)
        cls.contract = MODULE.build_contract(
            cls.plan,
            cls.intake,
            MODULE.sha256_file(cls.plan_path),
            MODULE.sha256_file(cls.intake_path),
            MODULE.sha256_file(cls.approval_path),
            MODULE.sha256_file(cls.bundle_path),
            CREATED_AT,
        )
        cls.readiness = MODULE.build_readiness_input(MODULE.sha256_file(cls.manifest_path))

    def test_tracked_contract_and_readiness_input_are_reproducible(self) -> None:
        self.assertEqual(
            (ROOT / "contracts/m2-offline-verification-candidate.json").read_bytes(),
            MODULE.canonical_bytes(self.contract),
        )
        self.assertEqual(
            (ROOT / "records/readiness/m2-readiness-audit-input.json").read_bytes(),
            MODULE.canonical_bytes(self.readiness),
        )
        self.assertEqual(
            MODULE.validate_candidate(
                self.plan,
                self.intake,
                self.contract,
                self.contract,
                self.readiness,
                self.readiness,
            ),
            [],
        )

    def test_contract_preserves_exact_product_set_and_no_authority(self) -> None:
        self.assertEqual(len(self.contract["assets"]), 8)
        self.assertEqual(
            {item["source_id"] for item in self.contract["assets"]},
            {item["source_id"] for item in self.plan["records"]},
        )
        self.assertEqual(self.contract["authority"]["m2_activation_status"], "not_granted")
        self.assertFalse(any(
            value for key, value in self.contract["authority"].items()
            if key != "m2_activation_status"
        ))
        self.assertEqual(self.contract["execution_boundary"]["network_requests"], "prohibited")
        self.assertEqual(self.contract["execution_boundary"]["archive_extraction"], "prohibited")

    def test_sensor_profiles_require_analysis_inputs_and_masks(self) -> None:
        radar = next(item for item in self.contract["assets"] if item["sensor_route"] == "radar")
        optical = next(item for item in self.contract["assets"] if item["sensor_route"] == "optical")
        radar_patterns = {item["pattern"] for item in radar["required_members"]}
        optical_patterns = {item["pattern"] for item in optical["required_members"]}
        self.assertTrue({
            "measurement/*-vv-*.tiff",
            "measurement/*-vh-*.tiff",
            "annotation/calibration/calibration-*-vv-*.xml",
            "annotation/calibration/noise-*-vh-*.xml",
        }.issubset(radar_patterns))
        self.assertTrue({
            "GRANULE/*/IMG_DATA/R10m/*_B02_10m.jp2",
            "GRANULE/*/IMG_DATA/R10m/*_B08_10m.jp2",
            "GRANULE/*/IMG_DATA/R20m/*_B11_20m.jp2",
            "GRANULE/*/IMG_DATA/R20m/*_B12_20m.jp2",
            "GRANULE/*/IMG_DATA/R20m/*_SCL_20m.jp2",
        }.issubset(optical_patterns))

    def test_pre_acquisition_readiness_decision_is_defer(self) -> None:
        decision = json.loads((ROOT / "records/readiness/m2-readiness-decision.json").read_text(encoding="utf-8"))
        input_bytes = (ROOT / "records/readiness/m2-readiness-audit-input.json").read_bytes()
        self.assertEqual(decision["audit_input_sha256"], hashlib.sha256(input_bytes).hexdigest())
        self.assertEqual(decision["decision"], "defer")
        self.assertEqual(
            set(decision["deferred_required_gate_ids"]),
            set(self.readiness["required_gate_ids"]),
        )
        self.assertEqual(decision["training_authority"], "not_granted")
        self.assertEqual(decision["authorized_next_actions"], [])
        self.assertFalse(decision["training_authorized_by_this_audit"])

    def test_empty_existing_custody_root_defers_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture_contract = copy.deepcopy(self.contract)
            fixture_contract["execution_boundary"]["custody_root_from_plan"] = str(root.resolve())
            receipt = MODULE.scan_contract(fixture_contract, root, "2026-09-03T17:00:00Z")
            self.assertEqual(receipt["status"], "defer")
            self.assertTrue(all(item["status"] == "defer" for item in receipt["assets"]))
            self.assertFalse(receipt["network_requests_performed"])
            self.assertFalse(receipt["archive_extraction_performed"])
            self.assertEqual(list(root.iterdir()), [])

    def test_scan_refuses_a_different_custody_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "differs from the exact approved plan"):
                MODULE.scan_contract(self.contract, Path(temp), "2026-09-03T17:00:00Z")

    def test_valid_synthetic_sentinel1_container_passes_container_only(self) -> None:
        asset = copy.deepcopy(next(item for item in self.contract["assets"] if item["sensor_route"] == "radar"))
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "fixture.zip"
            self._write_s1_fixture(archive_path, asset["exact_product_id"])
            asset["catalog_content_length_bytes"] = archive_path.stat().st_size
            asset["provider_md5"] = MODULE.md5_file(archive_path)
            result = MODULE.scan_archive(asset, archive_path, self.contract["archive_controls"])
            self.assertEqual(result["status"], "pass_container_only")
            self.assertTrue(result["eligible_for_post_container_qa"])
            self.assertFalse(result["pixel_usability_established"])
            self.assertEqual(result["checks"]["zip_crc"], "pass")

    def test_unsafe_zip_member_blocks_container(self) -> None:
        asset = copy.deepcopy(next(item for item in self.contract["assets"] if item["sensor_route"] == "radar"))
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "unsafe.zip"
            self._write_s1_fixture(archive_path, asset["exact_product_id"], unsafe=True)
            asset["catalog_content_length_bytes"] = archive_path.stat().st_size
            asset["provider_md5"] = MODULE.md5_file(archive_path)
            result = MODULE.scan_archive(asset, archive_path, self.contract["archive_controls"])
            self.assertEqual(result["status"], "block")
            self.assertTrue(any("unsafe member path" in error for error in result["errors"]))

    def test_valid_synthetic_sentinel2_container_passes_container_only(self) -> None:
        asset = copy.deepcopy(next(item for item in self.contract["assets"] if item["sensor_route"] == "optical"))
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "fixture-s2.zip"
            self._write_s2_fixture(archive_path, asset["exact_product_id"])
            asset["catalog_content_length_bytes"] = archive_path.stat().st_size
            asset["provider_md5"] = MODULE.md5_file(archive_path)
            result = MODULE.scan_archive(asset, archive_path, self.contract["archive_controls"])
            self.assertEqual(result["status"], "pass_container_only")
            self.assertTrue(result["eligible_for_post_container_qa"])
            self.assertFalse(result["pixel_usability_established"])
            self.assertEqual(result["checks"]["zip_crc"], "pass")

    def test_mutated_contract_and_authority_are_rejected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["authority"]["product_download_authorized"] = True
        errors = MODULE.validate_candidate(
            self.plan,
            self.intake,
            mutated,
            self.contract,
            self.readiness,
            self.readiness,
        )
        self.assertTrue(any("authority" in error for error in errors))
        self.assertTrue(any("deterministic" in error for error in errors))

    def test_scan_receipt_refuses_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "receipt.json"
            MODULE.write_scan_receipt(output, {"attempt": 1})
            with self.assertRaises(SystemExit):
                MODULE.write_scan_receipt(output, {"attempt": 2})
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"attempt": 1})

    @staticmethod
    def _write_s1_fixture(path: Path, product_id: str, unsafe: bool = False) -> None:
        members = [
            "manifest.safe",
            "annotation/s1d-iw-grd-vv-product.xml",
            "annotation/s1d-iw-grd-vh-product.xml",
            "annotation/calibration/calibration-s1d-iw-grd-vv-product.xml",
            "annotation/calibration/calibration-s1d-iw-grd-vh-product.xml",
            "annotation/calibration/noise-s1d-iw-grd-vv-product.xml",
            "annotation/calibration/noise-s1d-iw-grd-vh-product.xml",
            "measurement/s1d-iw-grd-vv-product.tiff",
            "measurement/s1d-iw-grd-vh-product.tiff",
        ]
        with ZipFile(path, "w") as archive:
            for member in members:
                archive.writestr(f"{product_id}/{member}", b"fixture")
            if unsafe:
                archive.writestr("../escape.txt", b"unsafe")

    @staticmethod
    def _write_s2_fixture(path: Path, product_id: str) -> None:
        members = [
            "manifest.safe",
            "MTD_MSIL2A.xml",
            "DATASTRIP/DS/MTD_DS.xml",
            "GRANULE/G/MTD_TL.xml",
            "GRANULE/G/IMG_DATA/R10m/T_B02_10m.jp2",
            "GRANULE/G/IMG_DATA/R10m/T_B03_10m.jp2",
            "GRANULE/G/IMG_DATA/R10m/T_B04_10m.jp2",
            "GRANULE/G/IMG_DATA/R10m/T_B08_10m.jp2",
            "GRANULE/G/IMG_DATA/R20m/T_B05_20m.jp2",
            "GRANULE/G/IMG_DATA/R20m/T_B06_20m.jp2",
            "GRANULE/G/IMG_DATA/R20m/T_B07_20m.jp2",
            "GRANULE/G/IMG_DATA/R20m/T_B8A_20m.jp2",
            "GRANULE/G/IMG_DATA/R20m/T_B11_20m.jp2",
            "GRANULE/G/IMG_DATA/R20m/T_B12_20m.jp2",
            "GRANULE/G/IMG_DATA/R20m/T_SCL_20m.jp2",
            "GRANULE/G/QI_DATA/MSK_CLASSI_B00.jp2",
        ]
        with ZipFile(path, "w") as archive:
            for member in members:
                archive.writestr(f"{product_id}/{member}", b"fixture")


if __name__ == "__main__":
    unittest.main()
