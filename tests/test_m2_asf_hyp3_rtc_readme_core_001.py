"""Disposable README provenance tests; no project product is opened."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES  # noqa: E402
from m2_asf_hyp3_rtc_readme_core_001 import (  # noqa: E402
    MAX_README_BYTES, inspect_product_readme,
)


def fixture(path: Path, readme: bytes) -> tuple[str, str]:
    source = next(job for job in load_approved_jobs() if job["source_id"] == ORDER[0])
    granule = source["job_parameters"]["granules"][0]
    base = f"S1D_IW_{granule.split('_')[4]}_DVP_RTC10_G_gpuned_ABCD"
    with ZipFile(path, "w", ZIP_STORED) as archive:
        archive.writestr(base + "/", b"")
        for suffix in REQUIRED_SUFFIXES:
            payload = readme if suffix == ".README.md.txt" else b"synthetic"
            archive.writestr(f"{base}/{base}{suffix}", payload)
    return base, granule


class ReadmeScreenTests(unittest.TestCase):
    def test_exact_source_text_is_sanitized_and_does_not_claim_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.zip"
            source = next(job for job in load_approved_jobs() if job["source_id"] == ORDER[0])
            granule = source["job_parameters"]["granules"][0]
            base = f"S1D_IW_{granule.split('_')[4]}_DVP_RTC10_G_gpuned_ABCD"
            fixture(path, f"Product {base}; input {granule}".encode())
            result = inspect_product_readme(ORDER[0], path, f"{base}.zip")
            self.assertEqual(result["status"], "pass_readme_exact_source_text_only")
            self.assertFalse(result["geotiff_headers_or_pixels_read"])
            self.assertFalse(result["archive_hash_verified_by_this_check"])
            self.assertNotIn(granule, json.dumps(result))
            with self.assertRaisesRegex(RouteStop, "rtc_readme_product_identity_mismatch"):
                inspect_product_readme(ORDER[0], path, "different.zip")

    def test_missing_source_text_defers_and_oversized_readme_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.zip"
            base, _ = fixture(path, b"source not identified")
            result = inspect_product_readme(ORDER[0], path, f"{base}.zip")
            self.assertEqual(result["status"], "defer_readme_source_text_review")
            self.assertFalse(result["exact_source_granule_text_present"])
            fixture(path, b"x" * (MAX_README_BYTES + 1))
            with self.assertRaisesRegex(RouteStop, "rtc_readme_size_invalid"):
                inspect_product_readme(ORDER[0], path, f"{base}.zip")


if __name__ == "__main__":
    unittest.main()
