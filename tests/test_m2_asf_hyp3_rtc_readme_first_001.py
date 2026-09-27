"""Disposable receipt tests for the first read-only HyP3 README probe."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_acquire_first_001 import EXACT_JOB_ID, SOURCE_ID  # noqa: E402
from m2_asf_hyp3_rtc_core_001 import RouteStop, load_approved_jobs  # noqa: E402
import m2_asf_hyp3_rtc_readme_first_001 as readme_module  # noqa: E402
from m2_asf_hyp3_rtc_readme_first_001 import probe_readme_once  # noqa: E402
from tests.test_m2_asf_hyp3_rtc_readme_core_001 import fixture  # noqa: E402


class ReadmeReceiptTests(unittest.TestCase):
    def test_release_requires_exact_prior_custody_and_fresh_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            custody = Path(temp) / "custody"
            product_dir = custody / "m2-asf-hyp3-rtc-products-001"
            product_dir.mkdir(parents=True)
            source = next(job for job in load_approved_jobs() if job["source_id"] == SOURCE_ID)
            granule = source["job_parameters"]["granules"][0]
            base = f"S1D_IW_{granule.split('_')[4]}_DVP_RTC10_G_gpuned_ABCD"
            archive = product_dir / f"{base}.zip"
            fixture(archive, f"Product {base}; input {granule}".encode())
            acquisition = {
                "status": "pass_local_zip_promoted_no_replace",
                "source_id": SOURCE_ID, "job_id": EXACT_JOB_ID,
                "product_filename": archive.name,
                "archive_integrity_verified": True,
                "credentials_recorded": False,
                "archive_size_bytes": archive.stat().st_size,
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            }
            acq_dir = custody / "m2-asf-hyp3-rtc-acquire-first-001" / "attempt-001"
            acq_dir.mkdir(parents=True)
            terminal_path = acq_dir / "terminal.json"
            terminal_path.write_text(json.dumps(acquisition), encoding="utf-8")
            (acq_dir / "descriptor.json").write_text(json.dumps({
                "source_id": SOURCE_ID, "job_id": EXACT_JOB_ID,
                "product_filename": archive.name,
                "expected_size_bytes": archive.stat().st_size,
            }), encoding="utf-8")
            digest = lambda path: hashlib.sha256(str(path).encode()).hexdigest()
            gate = {
                "status": "pass_readme_first_implementation_public_ci_only",
                "public_ci": {"conclusion": "success"},
                "bindings": {"implementation_file_sha256": {
                    ref: digest(root / ref) for ref in readme_module.IMPLEMENTATION_FILES
                }},
            }
            preflight = {
                "status": "pass_readme_first_no_content_preflight",
                "bindings": {
                    "implementation_gate_sha256": digest(root / readme_module.GATE_REF),
                    "acquisition_terminal_sha256": digest(terminal_path),
                },
                "assertions": {
                    "archive_exists": True, "probe_attempt_absent": True,
                    "no_product_payload_or_pixel_read": True,
                },
            }
            for ref, value in ((readme_module.GATE_REF, gate),
                               (readme_module.PREFLIGHT_REF, preflight)):
                path = root / ref
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            probe_root = custody / "m2-asf-hyp3-rtc-readme-first-001" / "attempt-001"
            with patch.object(readme_module, "_sha", side_effect=digest):
                self.assertEqual(
                    readme_module.require_readme_release(root, custody, probe_root)[0],
                    acquisition,
                )
                preflight["assertions"]["no_product_payload_or_pixel_read"] = False
                (root / readme_module.PREFLIGHT_REF).write_text(json.dumps(preflight), encoding="utf-8")
                with self.assertRaisesRegex(RouteStop, "rtc_readme_not_released"):
                    readme_module.require_readme_release(root, custody, probe_root)

    def test_verified_synthetic_archive_yields_append_only_sanitized_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            source = next(job for job in load_approved_jobs() if job["source_id"] == SOURCE_ID)
            granule = source["job_parameters"]["granules"][0]
            base = f"S1D_IW_{granule.split('_')[4]}_DVP_RTC10_G_gpuned_ABCD"
            archive = products / f"{base}.zip"
            fixture(archive, f"Product {base}; input {granule}; secret-account".encode())
            before = archive.read_bytes()
            acquisition = {
                "product_filename": archive.name,
                "archive_size_bytes": len(before),
                "archive_sha256": hashlib.sha256(before).hexdigest(),
            }
            attempt = custody / "readme-attempts" / "attempt-001"
            result = probe_readme_once(
                acquisition, archive, attempt, controlled_root=custody,
            )
            self.assertEqual(result["status"], "pass_readme_exact_source_text_only")
            self.assertTrue(result["archive_sha256_verified_current"])
            self.assertFalse(result["raster_pixels_read"])
            self.assertEqual(archive.read_bytes(), before)
            self.assertTrue((attempt / "started.json").is_file())
            receipt = (attempt / "terminal.json").read_text()
            self.assertNotIn("secret-account", receipt)
            self.assertNotIn(granule, receipt)
            self.assertEqual(json.loads(receipt)["job_id"], EXACT_JOB_ID)
            with self.assertRaisesRegex(RouteStop, "rtc_readme_attempt_collision"):
                probe_readme_once(acquisition, archive, attempt, controlled_root=custody)

    def test_hash_mismatch_stops_without_archive_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            custody = Path(temp) / "custody"
            products = custody / "products"
            products.mkdir(parents=True)
            archive = products / "synthetic.zip"
            fixture(archive, b"synthetic README")
            before = archive.read_bytes()
            acquisition = {
                "product_filename": archive.name,
                "archive_size_bytes": len(before),
                "archive_sha256": "0" * 64,
            }
            attempt = custody / "readme-attempts" / "attempt-001"
            result = probe_readme_once(
                acquisition, archive, attempt, controlled_root=custody,
            )
            self.assertEqual(result["code"], "rtc_readme_archive_hash_mismatch")
            self.assertEqual(archive.read_bytes(), before)
            self.assertTrue((attempt / "terminal.json").is_file())


if __name__ == "__main__":
    unittest.main()
