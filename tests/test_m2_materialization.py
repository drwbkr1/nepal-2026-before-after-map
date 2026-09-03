from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CORE_SPEC = importlib.util.spec_from_file_location(
    "m2_materialization_core", ROOT / "scripts/m2_materialization_core.py"
)
assert CORE_SPEC and CORE_SPEC.loader
CORE = importlib.util.module_from_spec(CORE_SPEC)
CORE_SPEC.loader.exec_module(CORE)

PREP_SPEC = importlib.util.spec_from_file_location(
    "prepare_m2_materialization", ROOT / "scripts/prepare_m2_materialization.py"
)
assert PREP_SPEC and PREP_SPEC.loader
PREP = importlib.util.module_from_spec(PREP_SPEC)
PREP_SPEC.loader.exec_module(PREP)

CREATED_AT = "2026-09-03T18:55:04Z"
PRODUCT_ID = "S2X_SYNTHETIC.SAFE"
CONTROLS = {
    "maximum_member_count": 100,
    "maximum_single_uncompressed_bytes": 1024 * 1024,
    "maximum_total_uncompressed_bytes_floor": 1024 * 1024,
    "maximum_total_uncompressed_to_archive_ratio": 20.0,
}


class M2MaterializationTests(unittest.TestCase):
    def write_zip(self, path: Path, members: list[tuple[str | ZipInfo, bytes]]) -> None:
        with ZipFile(path, "w") as archive:
            for name, value in members:
                archive.writestr(name, value)

    def test_tracked_contract_is_deterministic(self) -> None:
        expected = PREP.build_contract(CREATED_AT)
        actual = json.loads((ROOT / "contracts/m2-materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.assertEqual(PREP.validate_contract(actual), [])

    def test_contract_preserves_exact_eight_product_boundary(self) -> None:
        contract = PREP.build_contract(CREATED_AT)
        plan = json.loads((ROOT / "records/acquisition-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(len(contract["assets"]), 8)
        self.assertEqual(
            {item["source_id"] for item in contract["assets"]},
            {item["source_id"] for item in plan["records"]},
        )
        self.assertFalse(contract["authority"]["dem_products_authorized"])

    def test_contract_is_offline_gate_deferred_and_non_scientific(self) -> None:
        contract = PREP.build_contract(CREATED_AT)
        self.assertEqual(contract["status"], "active_authorized_gate_deferred")
        self.assertEqual(contract["execution_boundary"]["network_requests"], "prohibited")
        self.assertEqual(contract["prerequisites"]["container_receipt_status"], "pass_container_only")
        self.assertFalse(contract["authority"]["this_contract_creates_authority"])
        self.assertFalse(contract["claim_boundary"]["pixel_usability_established"])
        self.assertFalse(contract["claim_boundary"]["change_established"])

    def test_contract_binds_current_materialization_executables(self) -> None:
        contract = PREP.build_contract(CREATED_AT)
        inputs = contract["inputs"]
        for ref_key, hash_key in (
            ("materialization_core_ref", "materialization_core_sha256"),
            ("runner_ref", "runner_sha256"),
        ):
            path = ROOT / inputs[ref_key]
            self.assertEqual(inputs[hash_key], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_safe_archive_materializes_with_file_hash_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "fixture.zip"
            members = [
                (f"{PRODUCT_ID}/manifest.safe", b"manifest"),
                (f"{PRODUCT_ID}/GRANULE/G/IMG_DATA/R20m/T_B11_20m.jp2", b"band"),
            ]
            self.write_zip(archive, members)
            attempt = root / "attempt"
            result = CORE.materialize_archive(
                archive_path=archive,
                attempt_root=attempt,
                source_id="M1-SRC-TEST",
                exact_product_id=PRODUCT_ID,
                archive_sha256=CORE.sha256_file(archive),
                controls=CONTROLS,
                started_at_utc="2026-09-03T19:01:00Z",
            )
            manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "complete")
            self.assertEqual(manifest["file_count"], 2)
            self.assertEqual(manifest["total_extracted_bytes"], 12)
            manifest_entry = next(item for item in manifest["files"] if item["relative_path"] == "manifest.safe")
            self.assertEqual(manifest_entry["sha256"], hashlib.sha256(b"manifest").hexdigest())
            self.assertTrue((attempt / PRODUCT_ID / "manifest.safe").is_file())
            self.assertEqual(json.loads((attempt / "completed.json").read_text())["manifest_sha256"], CORE.sha256_file(attempt / "materialization-manifest.json"))

    def assert_unsafe(self, member_names: list[str | ZipInfo], code: str) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "fixture.zip"
            self.write_zip(archive, [(name, b"x") for name in member_names])
            with self.assertRaises(CORE.MaterializationError) as raised:
                CORE.inspect_safe_members(archive, PRODUCT_ID, CONTROLS)
            self.assertEqual(raised.exception.code, code)

    def test_traversal_member_is_rejected(self) -> None:
        self.assert_unsafe([f"{PRODUCT_ID}/../escape.txt"], "unsafe_member_path")

    def test_ambiguous_empty_or_dot_path_component_is_rejected(self) -> None:
        self.assert_unsafe([f"{PRODUCT_ID}//escape.txt"], "unsafe_member_path")
        self.assert_unsafe([f"{PRODUCT_ID}/./escape.txt"], "unsafe_member_path")

    def test_backslash_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "fixture.zip"
            forward = f"{PRODUCT_ID}/escape.txt".encode("utf-8")
            backward = f"{PRODUCT_ID}\\escape.txt".encode("utf-8")
            self.write_zip(archive, [(forward.decode("utf-8"), b"x")])
            raw = archive.read_bytes()
            self.assertEqual(raw.count(forward), 2)
            archive.write_bytes(raw.replace(forward, backward))
            with self.assertRaises(CORE.MaterializationError) as raised:
                CORE.inspect_safe_members(archive, PRODUCT_ID, CONTROLS)
            self.assertEqual(raised.exception.code, "backslash_member_path")

    def test_windows_reserved_and_ads_names_are_rejected(self) -> None:
        self.assert_unsafe([f"{PRODUCT_ID}/AUX.txt"], "windows_reserved_member_name")
        self.assert_unsafe([f"{PRODUCT_ID}/band.jp2:stream"], "windows_forbidden_member_character")

    def test_case_insensitive_collision_is_rejected(self) -> None:
        self.assert_unsafe(
            [f"{PRODUCT_ID}/manifest.safe", f"{PRODUCT_ID}/MANIFEST.SAFE"],
            "case_insensitive_member_collision",
        )

    def test_file_directory_collision_is_rejected(self) -> None:
        self.assert_unsafe(
            [f"{PRODUCT_ID}/GRANULE", f"{PRODUCT_ID}/GRANULE/G/file.jp2"],
            "file_directory_member_collision",
        )

    def test_symbolic_link_member_is_rejected(self) -> None:
        link = ZipInfo(f"{PRODUCT_ID}/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assert_unsafe([link], "symbolic_link_member")

    def test_attempt_and_json_replacement_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "fixture.zip"
            self.write_zip(archive, [(f"{PRODUCT_ID}/manifest.safe", b"manifest")])
            attempt = root / "attempt"
            attempt.mkdir()
            with self.assertRaises(CORE.MaterializationError) as raised:
                CORE.materialize_archive(
                    archive_path=archive,
                    attempt_root=attempt,
                    source_id="M1-SRC-TEST",
                    exact_product_id=PRODUCT_ID,
                    archive_sha256=CORE.sha256_file(archive),
                    controls=CONTROLS,
                    started_at_utc="2026-09-03T19:01:00Z",
                )
            self.assertEqual(raised.exception.code, "materialization_attempt_collision")
            marker = root / "marker.json"
            CORE.write_new_json(marker, {"attempt": 1})
            with self.assertRaises(CORE.MaterializationError):
                CORE.write_new_json(marker, {"attempt": 2})

    def test_production_wrapper_refuses_before_any_custody_read_or_output(self) -> None:
        data_root = Path(r"C:\Projects\Active\nepal-2026-before-after-map-data")
        materialized = data_root / "materialized"
        before = materialized.exists()
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/materialize_m2_product.py"),
                "--source-id",
                "M1-SRC-001",
                "--attempt-id",
                "fixture-must-not-run",
                "--started-at-utc",
                "2026-09-03T19:01:00Z",
            ],
            cwd=ROOT,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 12)
        self.assertEqual(json.loads(result.stdout)["code"], "asset_not_promoted")
        self.assertEqual(materialized.exists(), before)


if __name__ == "__main__":
    unittest.main()
