from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import m2_radar_delayed_import_probe_receipt_recovery_001_core as core  # noqa: E402
import run_m2_radar_delayed_import_probe_receipt_recovery_001 as runner  # noqa: E402


class _Environment:
    def __init__(self, fail: bool = False):
        object.__setattr__(self, "fail", fail)
        object.__setattr__(self, "overwriteOutput", None)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "overwriteOutput" and self.fail:
            raise RuntimeError("overwrite-boundary")
        object.__setattr__(self, name, value)


class _Raster:
    def __init__(self, events: list[str]):
        self.events = events

    def save(self, path: str) -> None:
        self.events.append("raster_save")
        Path(path).write_bytes(b"fixture")


class _Management:
    def __init__(self, events: list[str]):
        self.events = events

    def MosaicToNewRaster(self, inputs, output_location, name, *args):
        self.events.append("mosaic")
        Path(output_location, name).write_bytes(b"fixture-mosaic")


class _FakeArcPy:
    def __init__(self, events: list[str], fail_at: str | None = None):
        self.events = events
        self.fail_at = fail_at
        self.env = _Environment(fail_at == "overwrite_output")
        self.management = _Management(events)

    def ProductInfo(self) -> str:
        self.events.append("product_info")
        if self.fail_at == "product_info":
            raise RuntimeError("product-info-boundary")
        return "ArcInfo"

    def CheckOutExtension(self, name: str) -> str:
        self.events.append(f"checkout:{name}")
        if self.fail_at == f"checkout:{name}":
            raise RuntimeError(f"checkout-boundary:{name}")
        return "CheckedOut"

    def CheckInExtension(self, name: str) -> str:
        self.events.append(f"checkin:{name}")
        return "CheckedIn"

    def Point(self, x: float, y: float):
        return (x, y)

    def NumPyArrayToRaster(self, *args, **kwargs):
        self.events.append("numpy_to_raster")
        return _Raster(self.events)


def _fake_scan(*, aggregate: str = core.EXPECTED_AGGREGATE_SHA256) -> dict:
    sizes = core.size_plan()
    return {
        "file_count": core.FILE_COUNT,
        "total_logical_bytes": core.TOTAL_LOGICAL_BYTES,
        "aggregate_sha256": aggregate,
        "elapsed_seconds": 1.25,
        "files": [
            {"name": name, "logical_bytes": size, "sha256": "b" * 64}
            for name, size in zip(core.CORPUS_NAMES, sizes, strict=True)
        ],
    }


class M2RadarDelayedImportProbeReceiptRecovery001Tests(unittest.TestCase):
    def _run_fixture(
        self,
        *,
        fail_at: str | None = None,
        fail_terminal_write: bool = False,
        fail_cleanup_write: bool = False,
        scanner_error: BaseException | None = None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "attempt"
            events: list[str] = []

            def corpus_creator(path: Path) -> list[Path]:
                self.assertTrue((target / "terminal-reservation.json").is_file())
                self.assertTrue((target / "cleanup-reservation.json").is_file())
                self.assertTrue((target / "fallback.jsonl").is_file())
                events.append("corpus_create")
                path.mkdir()
                paths: list[Path] = []
                for name in core.CORPUS_NAMES:
                    item = path / name
                    item.write_bytes(b"x")
                    paths.append(item)
                return paths

            def corpus_scanner(paths) -> dict:
                events.append("corpus_scan")
                if scanner_error is not None:
                    raise scanner_error
                return _fake_scan()

            def arcpy_loader():
                events.append("arcpy_import")
                if fail_at == "arcpy_import":
                    raise RuntimeError("import-boundary")
                return _FakeArcPy(events, fail_at)

            def terminal_writer(path: Path, value: object) -> None:
                if fail_terminal_write:
                    raise OSError("forced-terminal-write-failure")
                core.write_new_json(path, value)

            def cleanup_writer(path: Path, value: object) -> None:
                if fail_cleanup_write:
                    raise OSError("forced-cleanup-write-failure")
                core.write_new_json(path, value)

            result = runner.execute_probe_body(
                "2026-09-19T20:00:00Z",
                target=target,
                bindings={"fixture": "a" * 64},
                arcpy_loader=arcpy_loader,
                corpus_creator=corpus_creator,
                corpus_scanner=corpus_scanner,
                terminal_writer=terminal_writer,
                cleanup_writer=cleanup_writer,
            )
            stages = [json.loads(line)["stage"] for line in (target / "stages.jsonl").read_text(encoding="utf-8").splitlines()]
            fallback = [json.loads(line) for line in (target / "fallback.jsonl").read_text(encoding="utf-8").splitlines()]
            terminal = json.loads((target / "terminal.json").read_text(encoding="utf-8")) if (target / "terminal.json").is_file() else None
            cleanup = json.loads((target / "cleanup.json").read_text(encoding="utf-8")) if (target / "cleanup.json").is_file() else None
            snapshot = {
                "result": result,
                "events": events,
                "stages": stages,
                "fallback": fallback,
                "terminal": terminal,
                "cleanup": cleanup,
                "corpus_exists": (target / "corpus").exists(),
                "scratch_exists": (target / "scratch").exists(),
                "terminal_reservation": json.loads((target / "terminal-reservation.json").read_text(encoding="utf-8")),
                "cleanup_reservation": json.loads((target / "cleanup-reservation.json").read_text(encoding="utf-8")),
            }
        return snapshot

    def test_contract_and_exact_corpus_identity(self) -> None:
        contract = json.loads((ROOT / runner.CONTRACT_REF).read_text(encoding="utf-8"))
        self.assertEqual(contract["attempt"]["attempt_id"], core.ATTEMPT_ID)
        self.assertEqual(contract["stage_order"], list(core.STAGE_ORDER))
        self.assertEqual(contract["corpus"]["file_count"], 156)
        self.assertEqual(contract["corpus"]["total_logical_bytes"], 10_367_157_634)
        self.assertEqual(contract["corpus"]["expected_stable_order_aggregate_sha256"], core.EXPECTED_AGGREGATE_SHA256)
        self.assertTrue(all(value is False for value in contract["claim_boundary"].values()))
        self.assertTrue(all(value is True for value in contract["forbidden"].values()))

    def test_runner_uses_function_local_datetime_and_no_top_level_arcpy(self) -> None:
        source = (ROOT / runner.RUNNER_REF).read_text(encoding="utf-8")
        tree = ast.parse(source)
        top_imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        names: list[str] = []
        for node in top_imports:
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            else:
                names.append(node.module or "")
        self.assertNotIn("arcpy", names)
        self.assertNotIn("requests", names)
        self.assertNotIn("datetime", names)
        with patch.object(runner, "datetime", object(), create=True):
            self.assertTrue(runner.now_utc().endswith("Z"))

    def test_success_preserves_stage_order_and_reverse_checkin(self) -> None:
        result = self._run_fixture()
        self.assertEqual(result["result"], 0)
        self.assertEqual(result["stages"], list(core.STAGE_ORDER))
        self.assertLess(result["events"].index("corpus_scan"), result["events"].index("arcpy_import"))
        self.assertLess(result["events"].index("checkin:Spatial"), result["events"].index("checkin:ImageAnalyst"))
        self.assertEqual(result["terminal"]["status"], "pass_exact_disposable_delayed_import_sequence")
        self.assertEqual(result["cleanup"]["status"], "cleanup_completed")
        self.assertFalse(result["corpus_exists"])
        self.assertFalse(result["scratch_exists"])

    def test_original_error_survives_forced_terminal_write_failure(self) -> None:
        token = "eyJ" + "a" * 24 + "." + "b" * 24 + "." + "c" * 24
        error = RuntimeError(rf"original C:\Users\owner\secret\payload.bin bearer {token}")
        result = self._run_fixture(scanner_error=error, fail_terminal_write=True)
        self.assertEqual(result["result"], 21)
        self.assertIsNone(result["terminal"])
        self.assertIsNotNone(result["cleanup"])
        events = [item["event"] for item in result["fallback"]]
        self.assertEqual(events[:3], [
            "fallback_journal_initialized",
            "probe_exception_captured",
            "terminal_persistence_exception_captured",
        ])
        rendered = json.dumps(result["fallback"])
        self.assertNotIn(token, rendered)
        self.assertNotIn("owner", rendered)
        self.assertIn("forced-terminal-write-failure", rendered)
        self.assertFalse(result["corpus_exists"])

    def test_cleanup_is_independent_and_persisted_after_probe_failure(self) -> None:
        result = self._run_fixture(fail_at="arcpy_import", fail_terminal_write=True)
        self.assertEqual(result["result"], 21)
        self.assertEqual(result["cleanup"]["status"], "cleanup_completed")
        self.assertFalse(result["cleanup"]["terminal_persisted"])
        self.assertIn("cleanup_disposition_recorded", [item["event"] for item in result["fallback"]])
        self.assertFalse(result["corpus_exists"])

    def test_cleanup_write_failure_is_retained_in_fallback(self) -> None:
        result = self._run_fixture(fail_at="arcpy_import", fail_cleanup_write=True)
        self.assertEqual(result["result"], 22)
        self.assertIsNotNone(result["terminal"])
        self.assertIsNone(result["cleanup"])
        self.assertIn("cleanup_persistence_exception_captured", [item["event"] for item in result["fallback"]])

    def test_interruption_retains_monotonic_stage_and_cleanup(self) -> None:
        result = self._run_fixture(scanner_error=KeyboardInterrupt("synthetic-interruption"))
        self.assertEqual(result["result"], 20)
        positions = core.stage_positions(result["stages"])
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(result["terminal"]["failure_type"], "KeyboardInterrupt")
        self.assertEqual(result["cleanup"]["status"], "cleanup_completed")

    def test_exact_digest_mismatch_fails_closed(self) -> None:
        bad = _fake_scan(aggregate="0" * 64)
        with self.assertRaisesRegex(core.ProbeError, "corpus_hash_aggregate_mismatch"):
            core.validate_scan(bad)

    def test_append_only_attempt_collision_fails_before_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "attempt"
            target.mkdir()
            with self.assertRaisesRegex(core.ProbeError, "probe_attempt_collision"):
                runner.execute_probe_body(
                    "2026-09-19T20:00:00Z",
                    target=target,
                    bindings={},
                    corpus_creator=lambda path: self.fail("corpus creator called"),
                )

    def test_secret_and_path_redaction_and_path_boundaries(self) -> None:
        token = "eyJ" + "a" * 24 + "." + "b" * 24 + "." + "c" * 24
        safe = core.safe_error(RuntimeError(rf"failed C:\Users\owner\secret\payload.bin bearer {token}"))
        rendered = json.dumps(safe)
        self.assertNotIn(token, rendered)
        self.assertNotIn("owner", rendered)
        with self.assertRaisesRegex(core.ProbeError, "probe_path_inside_forbidden_root"):
            core.require_outside(ROOT / "disposable", (ROOT,))


if __name__ == "__main__":
    unittest.main()
