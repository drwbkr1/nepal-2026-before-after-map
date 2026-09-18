from __future__ import annotations

import datetime as datetime_module
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import convert_m2_dem_vertical_datum_proj25 as conversion  # noqa: E402
import preflight_m2_dem_vertical_operation_proj25 as operation  # noqa: E402
import recover_m2_dem_proj25_receipt_persistence_002 as recovery  # noqa: E402
import recover_m2_dem_vertical_grid_proj25_metadata_001 as recovery_001  # noqa: E402
from m2_dem_vertical_datum_proj25_core import (  # noqa: E402
    EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256,
    load_contract,
)


class DemProj25ReceiptPersistenceRecovery002Tests(unittest.TestCase):
    def test_contract_freezes_exact_receipt_recovery_boundary(self) -> None:
        control = load_contract()["receipt_persistence_recovery_002"]
        self.assertEqual(control["approval_sha256"], EXPECTED_RECEIPT_RECOVERY_APPROVAL_SHA256)
        self.assertEqual(control["network_requests"], 0)
        self.assertEqual(control["recovery_001_retries"], 0)
        self.assertEqual(control["new_promotion_actions"], 0)
        self.assertEqual(control["maximum_receipt_recovery_attempts"], 1)
        self.assertFalse(control["automatic_retry"])
        self.assertTrue(control["receipt_reserved_before_content_read"])

    def test_timestamp_functions_ignore_arcgis_style_global_rebinding(self) -> None:
        modules = [recovery_001, recovery, operation, conversion]
        sentinels = {module: getattr(module, "datetime", None) for module in modules}
        present = {module: hasattr(module, "datetime") for module in modules}
        try:
            for module in modules:
                module.datetime = datetime_module
                observed = module.utc_now()
                self.assertRegex(observed, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        finally:
            for module in modules:
                if present[module]:
                    module.datetime = sentinels[module]
                else:
                    delattr(module, "datetime")

    def _fixture(self, base: Path):
        repo = base / "repo"
        data = base / "data"
        output = repo / "records/acquisition/m2-geoid-001-receipt-recovery-002.json"
        output.parent.mkdir(parents=True)
        staged = data / "grid.part"
        destination = data / "grid.tif"
        staged.parent.mkdir(parents=True)
        staged.write_bytes(b"grid")
        destination.hardlink_to(staged)
        preflight = repo / "preflight.json"
        preflight.write_text("{}\n", encoding="utf-8")
        contract = {
            "grid": {"source_id": "M2-GEOID-001"},
            "receipt_persistence_recovery_002": {
                "receipt_ref": "records/acquisition/m2-geoid-001-receipt-recovery-002.json"
            },
        }
        return repo, staged, destination, preflight, output, contract

    def test_exclusive_reservation_precedes_grid_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            repo, staged, destination, preflight, output, contract = self._fixture(Path(name))

            def inspect(_contract, _staged, _destination):
                self.assertTrue(output.exists())
                self.assertEqual(output.stat().st_size, 0)
                return {
                    "identity": {"size_bytes": 4, "sha256": "grid-sha"},
                    "staged_and_destination_same_file_identity": True,
                    "metadata": {"exact": True},
                    "arcgis_readability": {"readable": True},
                }

            with (
                patch.object(recovery, "ROOT", repo),
                patch.object(recovery, "PREFLIGHT", preflight),
                patch.object(recovery, "guarded_controls", return_value=(contract, staged, destination, {})),
                patch.object(recovery, "inspect_exact_grid", side_effect=inspect),
                patch.object(recovery, "sha256_file", return_value="preflight-sha"),
            ):
                code, result = recovery.execute(output)
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "pass_exact_promoted_grid_receipt_recovered_input_only")
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(receipt["persistence"]["receipt_reserved_before_grid_content_read"])
            self.assertEqual(receipt["observed"]["sha256"], "grid-sha")

    def test_interruption_preserves_empty_reservation_and_refuses_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            repo, staged, destination, preflight, output, contract = self._fixture(Path(name))
            with (
                patch.object(recovery, "ROOT", repo),
                patch.object(recovery, "PREFLIGHT", preflight),
                patch.object(recovery, "guarded_controls", return_value=(contract, staged, destination, {})),
                patch.object(recovery, "inspect_exact_grid", side_effect=RuntimeError("synthetic interruption")),
            ):
                first_code, first = recovery.execute(output)
                second_code, second = recovery.execute(output)
            self.assertEqual(first_code, 13)
            self.assertTrue(first["reserved_receipt_preserved"])
            self.assertEqual(output.stat().st_size, 0)
            self.assertEqual(second_code, 12)
            self.assertEqual(second["code"], "receipt_output_collision")

    def test_validation_failure_is_written_through_reserved_handle(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            repo, staged, destination, preflight, output, contract = self._fixture(Path(name))
            with (
                patch.object(recovery, "ROOT", repo),
                patch.object(recovery, "PREFLIGHT", preflight),
                patch.object(recovery, "guarded_controls", return_value=(contract, staged, destination, {})),
                patch.object(recovery, "inspect_exact_grid", side_effect=recovery.ReceiptRecoveryError("synthetic_identity_drift")),
                patch.object(recovery, "sha256_file", return_value="preflight-sha"),
            ):
                code, result = recovery.execute(output)
            self.assertEqual(code, 20)
            self.assertEqual(result["status"], "terminal_failure_no_retry")
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["failure_code"], "synthetic_identity_drift")
            self.assertTrue(receipt["persistence"]["complete_receipt_written_through_reserved_handle"])

    def test_missing_parent_and_collision_stop_before_grid_inspection(self) -> None:
        for collision in (False, True):
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as name:
                repo, staged, destination, preflight, output, contract = self._fixture(Path(name))
                if collision:
                    output.write_bytes(b"existing")
                else:
                    output.parent.rmdir()
                with (
                    patch.object(recovery, "ROOT", repo),
                    patch.object(recovery, "PREFLIGHT", preflight),
                    patch.object(recovery, "guarded_controls", return_value=(contract, staged, destination, {})),
                    patch.object(recovery, "inspect_exact_grid", side_effect=AssertionError("must not inspect")),
                ):
                    code, result = recovery.execute(output)
                self.assertEqual(code, 12)
                self.assertEqual(result["status"], "stopped_before_grid_content_read")

    def test_recovery_and_preflight_have_no_network_or_promotion_route(self) -> None:
        for ref in (
            "scripts/preflight_m2_dem_proj25_receipt_persistence_recovery_002.py",
            "scripts/recover_m2_dem_proj25_receipt_persistence_002.py",
        ):
            source = (ROOT / ref).read_text(encoding="utf-8").casefold()
            self.assertNotIn("urllib", source)
            self.assertNotIn("requests.", source)
            self.assertNotIn("http://", source)
            self.assertNotIn("https://", source)
            self.assertNotIn("promote_no_replace", source)


if __name__ == "__main__":
    unittest.main()
