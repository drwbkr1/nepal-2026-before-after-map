from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import blake3


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import m2_orbit_osv_precision_amendment_001_core as amendment_core  # noqa: E402
from m2_orbit_io_core import OrbitControlError, inspect_eof, osv_endpoints_within_tolerance  # noqa: E402


EXACT_NAME = amendment_core.EXACT_NAME


def instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def synthetic_eof(first: str, last: str) -> bytes:
    rows = "".join(
        f"""
        <OSV><UTC>{timestamp}</UTC>
        <X unit="m">7000000</X><Y unit="m">1</Y><Z unit="m">2</Z>
        <VX unit="m/s">3</VX><VY unit="m/s">4</VY><VZ unit="m/s">5</VZ></OSV>"""
        for timestamp in (first, "UTC=2026-08-16T12:00:00.000000", last)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Earth_Explorer_File><Earth_Explorer_Header><Fixed_Header>
<File_Name>{Path(EXACT_NAME).stem}</File_Name><File_Type>AUX_RESORB</File_Type><Mission>Sentinel-1D</Mission>
<Validity_Period><Validity_Start>UTC=2026-08-16T10:35:26</Validity_Start><Validity_Stop>UTC=2026-08-16T14:09:56</Validity_Stop></Validity_Period>
</Fixed_Header></Earth_Explorer_Header><Data_Block type="xml"><List_of_OSVs count="3">{rows}</List_of_OSVs></Data_Block></Earth_Explorer_File>
""".encode("utf-8")


def requirement(payload: bytes, *, tolerance: float | None) -> dict:
    value = {
        "source_id": "M2-ORB-001",
        "exact_product_name": EXACT_NAME,
        "sentinel_source_ids": ["M1-SRC-001", "M1-SRC-002"],
        "scene_start_utc": "2026-08-16T12:21:16Z",
        "scene_end_utc": "2026-08-16T12:22:06Z",
        "expected_size_bytes": len(payload),
        "expected_provider_checksums": [
            {"algorithm": "BLAKE3", "value": blake3.blake3(payload).hexdigest()},
            {"algorithm": "MD5", "value": hashlib.md5(payload, usedforsecurity=False).hexdigest()},
        ],
        "expected_validity_start_utc": "2026-08-16T10:35:26.000000Z",
        "expected_validity_end_utc": "2026-08-16T14:09:56.000000Z",
        "minimum_required_scene_margin_seconds": 6350,
    }
    if tolerance is not None:
        value["maximum_osv_endpoint_tolerance_seconds"] = tolerance
    return value


class OsvPrecisionAmendment001Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = instant("2026-08-16T10:35:26Z")
        self.stop = instant("2026-08-16T14:09:56Z")

    def test_exact_endpoints_pass(self) -> None:
        self.assertTrue(osv_endpoints_within_tolerance(self.start, self.stop, self.start, self.stop, tolerance_seconds=1.0))

    def test_subsecond_shortfall_passes(self) -> None:
        self.assertTrue(osv_endpoints_within_tolerance(self.start, self.stop, self.start + timedelta(microseconds=31829), self.stop - timedelta(microseconds=31829), tolerance_seconds=1.0))

    def test_exact_one_second_boundary_passes(self) -> None:
        self.assertTrue(osv_endpoints_within_tolerance(self.start, self.stop, self.start + timedelta(seconds=1), self.stop - timedelta(seconds=1), tolerance_seconds=1.0))

    def test_greater_than_one_second_shortfall_fails(self) -> None:
        self.assertFalse(osv_endpoints_within_tolerance(self.start, self.stop, self.start, self.stop - timedelta(seconds=1, microseconds=1), tolerance_seconds=1.0))

    def test_tolerance_above_one_second_is_rejected(self) -> None:
        with self.assertRaisesRegex(OrbitControlError, "osv_endpoint_tolerance_invalid"):
            osv_endpoints_within_tolerance(self.start, self.stop, self.start, self.stop, tolerance_seconds=1.000001)

    def test_strict_default_still_rejects_subsecond_shortfall(self) -> None:
        payload = synthetic_eof("UTC=2026-08-16T10:35:26.031829", "UTC=2026-08-16T14:09:55.968171")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / EXACT_NAME
            path.write_bytes(payload)
            with self.assertRaisesRegex(OrbitControlError, "osv_times_do_not_span_validity"):
                inspect_eof(path, requirement(payload, tolerance=None))

    def test_amended_inspection_accepts_subsecond_shortfall_and_records_it(self) -> None:
        payload = synthetic_eof("UTC=2026-08-16T10:35:26.031829", "UTC=2026-08-16T14:09:55.968171")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / EXACT_NAME
            path.write_bytes(payload)
            result = inspect_eof(path, requirement(payload, tolerance=1.0))
        self.assertEqual(result["status"], "pass_orbit_input_only")
        self.assertEqual(result["xml"]["endpoint_tolerance_seconds"], 1.0)
        self.assertAlmostEqual(result["xml"]["last_endpoint_shortfall_seconds"], 0.031829, places=6)

    def test_synthetic_atomic_promotion_preserves_staging(self) -> None:
        payload = synthetic_eof("UTC=2026-08-16T10:35:26.031829", "UTC=2026-08-16T14:09:55.968171")
        identity = {
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "md5": hashlib.md5(payload, usedforsecurity=False).hexdigest(),
            "blake3": blake3.blake3(payload).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / f"{EXACT_NAME}.part"
            destination = root / "custody" / EXACT_NAME
            temp = destination.with_name(".promotion.tmp")
            destination.parent.mkdir()
            staging.write_bytes(payload)
            with (
                patch.object(amendment_core, "EXPECTED_SIZE_BYTES", identity["size_bytes"]),
                patch.object(amendment_core, "EXPECTED_SHA256", identity["sha256"]),
                patch.object(amendment_core, "EXPECTED_MD5", identity["md5"]),
                patch.object(amendment_core, "EXPECTED_BLAKE3", identity["blake3"]),
            ):
                result = amendment_core.atomic_no_replace_promote(staging, destination, temp, requirement(payload, tolerance=1.0))
            self.assertEqual(staging.read_bytes(), payload)
            self.assertEqual(destination.read_bytes(), payload)
            self.assertFalse(temp.exists())
            self.assertTrue(result["destination_created_without_replace"])

    def test_existing_destination_is_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / f"{EXACT_NAME}.part"
            destination = root / "custody" / EXACT_NAME
            temp = destination.with_name(".promotion.tmp")
            destination.parent.mkdir()
            staging.write_bytes(b"staging")
            destination.write_bytes(b"existing")
            with self.assertRaisesRegex(OrbitControlError, "promotion_path_collision"):
                amendment_core.atomic_no_replace_promote(staging, destination, temp, {})
            self.assertEqual(destination.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
