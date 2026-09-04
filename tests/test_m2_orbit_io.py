from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import blake3


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from acquire_m2_orbit_file import (  # noqa: E402
    EXPECTED_SOURCE_IDS,
    build_attempt_id,
    normalized_live_product,
)
from m2_orbit_io_core import (  # noqa: E402
    REQUIRED_BLAKE3_VERSION,
    OrbitControlError,
    inspect_eof,
    provider_checksum_map,
    stream_to_exclusive_staging,
)


def synthetic_eof(
    exact_name: str,
    *,
    mission: str = "Sentinel-1D",
    validity_start: str = "UTC=2026-08-16T10:35:26",
    validity_stop: str = "UTC=2026-08-16T14:09:56",
    osv_times: tuple[str, ...] = (
        "UTC=2026-08-16T10:30:00",
        "UTC=2026-08-16T12:00:00",
        "UTC=2026-08-16T14:15:00",
    ),
    x_value: str = "7000000.0",
    position_unit: str = "m",
) -> bytes:
    rows = "".join(
        f"""
        <OSV>
          <UTC>{timestamp}</UTC>
          <X unit=\"{position_unit}\">{x_value}</X><Y unit=\"m\">1.0</Y><Z unit=\"m\">2.0</Z>
          <VX unit=\"m/s\">3.0</VX><VY unit=\"m/s\">4.0</VY><VZ unit=\"m/s\">5.0</VZ>
        </OSV>"""
        for timestamp in osv_times
    )
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Earth_Explorer_File>
  <Earth_Explorer_Header>
    <Fixed_Header>
      <File_Name>{Path(exact_name).stem}</File_Name>
      <File_Type>AUX_RESORB</File_Type>
      <Mission>{mission}</Mission>
      <Validity_Period>
        <Validity_Start>{validity_start}</Validity_Start>
        <Validity_Stop>{validity_stop}</Validity_Stop>
      </Validity_Period>
    </Fixed_Header>
  </Earth_Explorer_Header>
  <Data_Block type=\"xml\"><List_of_OSVs count=\"{len(osv_times)}\">{rows}
  </List_of_OSVs></Data_Block>
</Earth_Explorer_File>
""".encode("utf-8")


def requirement(exact_name: str, payload: bytes) -> dict:
    return {
        "source_id": "M2-ORB-001",
        "provider_product_id": "d4fdc474-0069-459b-9534-b5999dec5aab",
        "exact_product_name": exact_name,
        "orbit_type": "AUX_RESORB",
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


class M2OrbitIOTests(unittest.TestCase):
    def test_exact_blake3_dependency_and_known_digest(self) -> None:
        self.assertEqual(blake3.__version__, REQUIRED_BLAKE3_VERSION)
        self.assertEqual(
            blake3.blake3(b"abc").hexdigest(),
            "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85",
        )

    def test_stream_verifies_sha256_md5_and_blake3(self) -> None:
        payload = b"exact-orbit-fixture" * 300
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary) / "orbit.EOF.part"
            result = stream_to_exclusive_staging(
                io.BytesIO(payload),
                staging,
                expected_size=len(payload),
                expected_md5=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                expected_blake3=blake3.blake3(payload).hexdigest(),
                chunk_size=37,
            )
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(result["md5"], hashlib.md5(payload, usedforsecurity=False).hexdigest())
            self.assertEqual(result["blake3"], blake3.blake3(payload).hexdigest())
            self.assertEqual(staging.read_bytes(), payload)

    def test_stream_failure_preserves_bytes_and_collision_refuses_overwrite(self) -> None:
        payload = b"retained-orbit-failure"
        with tempfile.TemporaryDirectory() as temporary:
            staging = Path(temporary) / "orbit.EOF.part"
            with self.assertRaisesRegex(OrbitControlError, "provider_blake3_mismatch"):
                stream_to_exclusive_staging(
                    io.BytesIO(payload),
                    staging,
                    expected_size=len(payload),
                    expected_md5=hashlib.md5(payload, usedforsecurity=False).hexdigest(),
                    expected_blake3="0" * 64,
                )
            self.assertEqual(staging.read_bytes(), payload)
            with self.assertRaisesRegex(OrbitControlError, "staging_collision"):
                stream_to_exclusive_staging(
                    io.BytesIO(b"replacement"),
                    staging,
                    expected_size=11,
                    expected_md5="0" * 32,
                    expected_blake3="0" * 64,
                )
            self.assertEqual(staging.read_bytes(), payload)

    def test_valid_eof_passes_identity_osv_and_scene_binding(self) -> None:
        exact_name = "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
        payload = synthetic_eof(exact_name)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / exact_name
            path.write_bytes(payload)
            result = inspect_eof(path, requirement(exact_name, payload))
        self.assertEqual(result["status"], "pass_orbit_input_only")
        self.assertEqual(result["xml"]["osv_observed_count"], 3)
        self.assertTrue(result["xml"]["ordered_unique_finite_osvs"])
        self.assertEqual(result["scene_binding"]["minimum_margin_seconds"], 6350)

    def test_unsafe_xml_and_wrong_mission_are_rejected(self) -> None:
        exact_name = "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
        safe = synthetic_eof(exact_name)
        unsafe = safe.replace(b"<Earth_Explorer_File>", b"<!DOCTYPE x [<!ENTITY x 'bad'>]><Earth_Explorer_File>")
        wrong_mission = synthetic_eof(exact_name, mission="Sentinel-1A")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / exact_name
            path.write_bytes(unsafe)
            with self.assertRaisesRegex(OrbitControlError, "unsafe_xml_declaration"):
                inspect_eof(path, requirement(exact_name, unsafe))
            path.write_bytes(wrong_mission)
            with self.assertRaisesRegex(OrbitControlError, "orbit_mission_mismatch"):
                inspect_eof(path, requirement(exact_name, wrong_mission))

    def test_duplicate_times_nonfinite_values_and_wrong_units_are_rejected(self) -> None:
        exact_name = "S1D_OPER_AUX_RESORB_OPOD_20260816T143208_V20260816T103526_20260816T140956.EOF"
        cases = [
            (
                synthetic_eof(
                    exact_name,
                    osv_times=(
                        "UTC=2026-08-16T10:30:00",
                        "UTC=2026-08-16T10:30:00",
                        "UTC=2026-08-16T14:15:00",
                    ),
                ),
                "osv_time_order_or_uniqueness_failure",
            ),
            (synthetic_eof(exact_name, x_value="NaN"), "osv_numeric_value_nonfinite"),
            (synthetic_eof(exact_name, position_unit="km"), "osv_unit_mismatch"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / exact_name
            for payload, error in cases:
                path.write_bytes(payload)
                with self.assertRaisesRegex(OrbitControlError, error):
                    inspect_eof(path, requirement(exact_name, payload))

    def test_catalog_normalization_and_checksum_set_are_exact(self) -> None:
        raw = {
            "Id": "uuid",
            "Name": "name.EOF",
            "S3Path": "/eodata/name.EOF",
            "ContentLength": 123,
            "ContentDate": {"Start": "start", "End": "end"},
            "PublicationDate": "published",
            "ModificationDate": "modified",
            "Online": True,
            "Checksum": [
                {"Algorithm": "BLAKE3", "Value": "AA"},
                {"Algorithm": "MD5", "Value": "BB"},
            ],
            "Locations": [{"FormatType": "Compressed", "EvictionDate": "eviction"}],
        }
        normalized = normalized_live_product(raw)
        self.assertEqual(normalized["provider_checksums"], {"BLAKE3": "aa", "MD5": "bb"})
        with self.assertRaisesRegex(OrbitControlError, "provider_checksum_set_incomplete"):
            provider_checksum_map([{"algorithm": "MD5", "value": "bb"}])

    def test_production_entrypoints_refuse_before_sentinel_custody_without_reading_token(self) -> None:
        candidate_paths = [
            ROOT / "contracts/m2-orbit-intake-candidate.json",
            ROOT / "contracts/m2-orbit-offline-verification-candidate.json",
            ROOT / "records/source-gates/m2-orbit-candidate-manifest.json",
            ROOT / "contracts/m2-orbit-intake.json",
            ROOT / "contracts/m2-orbit-offline-verification.json",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in candidate_paths}
        environment = dict(os.environ)
        environment["CDSE_ACCESS_TOKEN"] = "fixture-secret-must-not-be-read"
        transfer = subprocess.run(
            [sys.executable, str(ROOT / "scripts/acquire_m2_orbit_file.py"), "--source-id", EXPECTED_SOURCE_IDS[0]],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(transfer.returncode, 12)
        self.assertEqual(json.loads(transfer.stdout)["code"], "bound_sentinel_source_not_promoted")
        self.assertNotIn("fixture-secret", transfer.stdout + transfer.stderr)
        with tempfile.TemporaryDirectory() as temporary:
            verification = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/verify_m2_orbit_eof.py"),
                    "--source-id",
                    EXPECTED_SOURCE_IDS[0],
                    "--custody-root",
                    temporary,
                    "--output",
                    str(Path(temporary) / "receipt.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(verification.returncode, 12)
            self.assertEqual(json.loads(verification.stdout)["code"], "active_orbit_verification_binding_drift")
            self.assertFalse((Path(temporary) / "receipt.json").exists())
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in candidate_paths}
        self.assertEqual(after, before)

    def test_attempt_ids_are_lowercase_and_schema_compatible(self) -> None:
        attempt_id = build_attempt_id("m2-orb-001", "2026-09-04T02:00:00Z", "ABC123ef")
        self.assertEqual(attempt_id, "m2-orb-001-20260904t020000z-abc123ef")
        self.assertRegex(attempt_id, r"^[a-z0-9][a-z0-9._-]{0,127}$")


if __name__ == "__main__":
    unittest.main()
