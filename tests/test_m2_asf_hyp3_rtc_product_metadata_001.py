"""Disposable bounded metadata capture tests; no project product is opened."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m2_asf_hyp3_rtc_product_metadata_001 as metadata  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402


def fixture(path: Path, *, oversize: bool = False) -> tuple[bytes, bytes]:
    granule = load_approved_jobs()[0]["job_parameters"]["granules"][0]
    base = f"S1D_IW_{granule.split('_')[4]}_DVP_RTC10_G_gpuned_ABCD"
    readme = f"Input {granule}; account marker private-example".encode()
    with ZipFile(path, "w") as archive:
        for suffix in REQUIRED_SUFFIXES:
            payload = readme if suffix == ".README.md.txt" else b"synthetic metadata"
            if suffix == ".log":
                payload = b"processing marker private-example"
                if oversize:
                    payload = b"x" * (metadata.SUFFIX_LIMITS[".log"] + 1)
            archive.writestr(f"{base}/{base}{suffix}", payload)
        archive.writestr(f"{base}/", b"")
    return path.read_bytes(), readme


class MetadataCaptureTests(unittest.TestCase):
    def test_release_requires_exact_ci_and_no_content_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            custody = Path(temp) / "custody"
            products = custody / "m2-asf-hyp3-rtc-products-001"
            products.mkdir(parents=True)
            archive = products / "S1D_IW_20260816T122141_DVP_RTC10_G_gpuned_ABCD.zip"
            before, _ = fixture(archive)
            fake_sha = lambda path: hashlib.sha256(str(path).encode()).hexdigest()
            composite_path = custody / metadata.COMPOSITE_REF
            acquisition_path = custody / metadata.ACQUISITION_REF
            composite_path.parent.mkdir(parents=True)
            acquisition_path.parent.mkdir(parents=True)
            composite_path.write_text(json.dumps({
                "status": "pass_composite_provenance_for_local_qa_only",
                "source_id": metadata.SOURCE_ID, "job_id": metadata.JOB_ID,
                "archive_sha256": "a" * 64,
            }), encoding="utf-8")
            acquisition_path.write_text(json.dumps({
                "status": "pass_local_zip_promoted_no_replace",
                "source_id": metadata.SOURCE_ID, "job_id": metadata.JOB_ID,
                "product_filename": archive.name, "archive_sha256": "a" * 64,
                "archive_integrity_verified": True,
            }), encoding="utf-8")
            records = {
                metadata.APPROVAL_REF: {
                    "decision": "approve", "authority": {
                        "conditional_product_metadata_and_pixel_QA_under_original_route": True,
                    },
                },
                metadata.SOURCE_GATE_REF: {"decision": {"status": "ready"}},
                metadata.GATE_REF: {
                    "status": "pass_product_metadata_implementation_public_ci_only",
                    "public_ci": {"conclusion": "success"},
                    "bindings": {
                        "approval_sha256": fake_sha(root / metadata.APPROVAL_REF),
                        "source_gate_sha256": fake_sha(root / metadata.SOURCE_GATE_REF),
                        "implementation_file_sha256": {
                            ref: fake_sha(root / ref) for ref in metadata.IMPLEMENTATION_FILES
                        },
                    },
                },
                metadata.PREFLIGHT_REF: {
                    "status": "pass_product_metadata_no_content_preflight",
                    "bindings": {
                        "implementation_gate_sha256": fake_sha(root / metadata.GATE_REF),
                        "composite_terminal_sha256": fake_sha(composite_path),
                        "acquisition_terminal_sha256": fake_sha(acquisition_path),
                    },
                    "assertions": {"attempt_absent": True, "no_product_payload_read": True},
                },
            }
            for ref, value in records.items():
                path = root / ref
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            attempt = custody / "m2-asf-hyp3-rtc-product-metadata-001" / "attempt-001"
            with patch.object(metadata, "PRODUCT_FILENAME", archive.name), \
                 patch.object(metadata, "ARCHIVE_SIZE", len(before)), \
                 patch.object(metadata, "ARCHIVE_SHA256", "a" * 64), \
                 patch.object(metadata, "_sha", side_effect=fake_sha):
                self.assertEqual(metadata.require_release(root, custody, attempt)[1], archive)
                records[metadata.PREFLIGHT_REF]["assertions"]["no_product_payload_read"] = False
                (root / metadata.PREFLIGHT_REF).write_text(
                    json.dumps(records[metadata.PREFLIGHT_REF]), encoding="utf-8"
                )
                with self.assertRaisesRegex(RouteStop, "rtc_metadata_not_released"):
                    metadata.require_release(root, custody, attempt)

    def test_bounded_metadata_only_is_append_only_and_secret_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            product_dir = custody / "products"
            product_dir.mkdir(parents=True)
            archive = product_dir / "S1D_IW_20260816T122141_DVP_RTC10_G_gpuned_ABCD.zip"
            before, readme = fixture(archive)
            acquisition = {
                "archive_size_bytes": len(before),
                "archive_sha256": hashlib.sha256(before).hexdigest(),
            }
            attempt = custody / "metadata" / "attempt-001"
            with patch.object(metadata, "PRODUCT_FILENAME", archive.name), \
                 patch.object(metadata, "ARCHIVE_SHA256", acquisition["archive_sha256"]), \
                 patch.object(metadata, "README_SHA256", hashlib.sha256(readme).hexdigest()):
                result = metadata.capture_once(acquisition, archive, attempt, controlled_root=custody)
            self.assertEqual(result["status"], "pass_bounded_metadata_captured_for_local_review_only")
            self.assertEqual(len(result["captured"]), len(metadata.SUFFIX_LIMITS))
            self.assertEqual((attempt / "readme.txt").read_bytes(), readme)
            self.assertEqual(archive.read_bytes(), before)
            receipt = (attempt / "terminal.json").read_text()
            self.assertNotIn("private-example", receipt)
            self.assertNotIn(granule_text(), receipt)
            self.assertFalse(json.loads(receipt)["raster_header_or_pixel_read"])
            with self.assertRaisesRegex(RouteStop, "rtc_metadata_attempt_collision"):
                metadata.capture_once(acquisition, archive, attempt, controlled_root=custody)

    def test_oversized_log_stops_without_raster_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "S1D_IW_20260816T122141_DVP_RTC10_G_gpuned_ABCD.zip"
            before, readme = fixture(archive, oversize=True)
            acquisition = {"archive_size_bytes": len(before),
                           "archive_sha256": hashlib.sha256(before).hexdigest()}
            attempt = custody / "metadata" / "attempt-001"
            with patch.object(metadata, "PRODUCT_FILENAME", archive.name), \
                 patch.object(metadata, "ARCHIVE_SHA256", acquisition["archive_sha256"]), \
                 patch.object(metadata, "README_SHA256", hashlib.sha256(readme).hexdigest()):
                result = metadata.capture_once(acquisition, archive, attempt, controlled_root=custody)
            self.assertEqual(result["code"], "rtc_metadata_member_size_invalid")
            self.assertFalse(result["raster_header_or_pixel_read"])
            self.assertEqual(archive.read_bytes(), before)

    def test_hash_mismatch_consumes_only_distinct_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "S1D_IW_20260816T122141_DVP_RTC10_G_gpuned_ABCD.zip"
            before, _ = fixture(archive)
            acquisition = {"archive_size_bytes": len(before), "archive_sha256": "0" * 64}
            attempt = custody / "metadata" / "attempt-001"
            with patch.object(metadata, "PRODUCT_FILENAME", archive.name):
                result = metadata.capture_once(acquisition, archive, attempt, controlled_root=custody)
            self.assertEqual(result["code"], "rtc_metadata_archive_identity_mismatch")
            self.assertTrue((attempt / "terminal.json").is_file())
            self.assertEqual(archive.read_bytes(), before)


def granule_text() -> str:
    return load_approved_jobs()[0]["job_parameters"]["granules"][0]


if __name__ == "__main__":
    unittest.main()
