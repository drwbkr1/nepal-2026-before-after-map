"""Synthetic HyP3 package member screen; no archive or pixels are read."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m2_asf_hyp3_rtc_core_001 import ORDER, RouteStop, load_approved_jobs  # noqa: E402
from m2_asf_hyp3_rtc_package_core_001 import REQUIRED_SUFFIXES, inspect_member_names  # noqa: E402


def synthetic_members(source_id: str) -> tuple[str, list[str]]:
    job = next(item for item in load_approved_jobs() if item["source_id"] == source_id)
    start = job["job_parameters"]["granules"][0].split("_")[4]
    root = f"S1D_IW_{start}_DVP_RTC10_G_gpuned_ABCD"
    return root, [f"{root}/"] + [f"{root}/{root}{suffix}" for suffix in REQUIRED_SUFFIXES]


class PackageMemberTests(unittest.TestCase):
    def test_each_exact_source_accepts_documented_member_names_only(self) -> None:
        for source_id in ORDER:
            with self.subTest(source_id=source_id):
                root, members = synthetic_members(source_id)
                result = inspect_member_names(source_id, members)
                self.assertEqual(result["product_base_name"], root)
                self.assertEqual(result["member_file_count"], len(REQUIRED_SUFFIXES))
                self.assertFalse(result["zip_integrity_verified"])
                self.assertFalse(result["geotiff_headers_or_pixels_read"])
                self.assertFalse(result["provider_mask_codes_assessed"])

    def test_missing_required_or_unapproved_rgb_stops(self) -> None:
        root, members = synthetic_members(ORDER[0])
        with self.assertRaisesRegex(RouteStop, "rtc_package_required_member_missing"):
            inspect_member_names(ORDER[0], members[:-1])
        with self.assertRaisesRegex(RouteStop, "rtc_package_unapproved_rgb_tif"):
            inspect_member_names(ORDER[0], members + [f"{root}/{root}_rgb.tif"])

    def test_source_date_and_method_cannot_be_substituted(self) -> None:
        root, members = synthetic_members(ORDER[0])
        for altered in (
            root.replace("20260816", "20260828"),
            root.replace("RTC10", "RTC20"),
            root.replace("gpuned", "sdpned"),
        ):
            with self.subTest(altered=altered), self.assertRaisesRegex(RouteStop, "rtc_package_product_identity_mismatch"):
                inspect_member_names(ORDER[0], [name.replace(root, altered) for name in members])

    def test_traversal_nested_paths_and_duplicate_names_stop(self) -> None:
        root, members = synthetic_members(ORDER[0])
        for bad in (
            members + [f"{root}/../escape"],
            members + [f"{root}/nested/file.tif"],
            members + [members[1].upper()],
            members + ["C:\\private\\file.tif"],
            members + [f"{root}/bad:stream.tif"],
        ):
            with self.subTest(bad=bad[-1]), self.assertRaises(RouteStop):
                inspect_member_names(ORDER[0], bad)


if __name__ == "__main__":
    unittest.main()
