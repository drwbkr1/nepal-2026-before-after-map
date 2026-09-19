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

import m2_radar_pixel_orbit_application_recovery_001_core as recovery_001  # noqa: E402
import m2_radar_pixel_orbit_application_recovery_002_core as core  # noqa: E402
import run_m2_radar_pixel_orbit_application_recovery_002 as runner  # noqa: E402


class _Environment:
    def __init__(self) -> None:
        self.overwriteOutput = None


class _FakeArcPy:
    def __init__(self, events: list[str], *, checkin_failure: bool = False) -> None:
        self.events = events
        self.env = _Environment()
        self.checkin_failure = checkin_failure

    def ProductInfo(self) -> str:
        self.events.append("product_info")
        return "ArcInfo"

    def CheckOutExtension(self, name: str) -> str:
        self.events.append(f"checkout:{name}")
        return "CheckedOut"

    def CheckInExtension(self, name: str) -> str:
        self.events.append(f"checkin:{name}")
        if self.checkin_failure and name == "Spatial":
            raise RuntimeError("synthetic-checkin-failure")
        return "CheckedIn"


class M2RadarPixelOrbitApplicationRecovery002Tests(unittest.TestCase):
    def _run_fixture(
        self,
        *,
        fail_source: str | None = None,
        fail_route: str | None = None,
        identity_error: BaseException | None = None,
        fail_terminal_write: bool = False,
        fail_cleanup_write: bool = False,
        checkin_failure: bool = False,
    ) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "attempt"
            events: list[str] = []
            scans = 0

            def identity_verifier(plan: dict) -> dict:
                nonlocal scans
                self.assertTrue((target / "terminal-reservation.json").is_file())
                self.assertTrue((target / "cleanup-reservation.json").is_file())
                self.assertTrue((target / "fallback.jsonl").is_file())
                scans += 1
                events.append(f"identity:{scans}")
                if identity_error is not None and scans == 1:
                    raise identity_error
                return {"identity": "stable"}

            def arcpy_loader() -> _FakeArcPy:
                events.append("arcpy_import")
                return _FakeArcPy(events, checkin_failure=checkin_failure)

            def dem_builder(arcpy, plan, attempt_root):
                events.append("dem")
                return "synthetic-dem"

            def support_builder(arcpy, plan, attempt_root):
                events.append("support")
                return {"synthetic": True}

            def source_processor(*, source_id: str, **kwargs) -> dict:
                events.append(f"source:{source_id}")
                return {
                    "source_id": source_id,
                    "status": "failed" if source_id == fail_source else "pass_source_qa_only",
                }

            def route_processor(*, route_id: str, **kwargs) -> dict:
                events.append(f"route:{route_id}")
                return {
                    "route_id": route_id,
                    "status": "failed" if route_id == fail_route else "pass_route_evaluated_qa_only",
                }

            def terminal_writer(path: Path, value: object) -> None:
                if fail_terminal_write:
                    raise OSError("forced-terminal-write-failure")
                core.write_new_json(path, value)

            def cleanup_writer(path: Path, value: object) -> None:
                if fail_cleanup_write:
                    raise OSError("forced-cleanup-write-failure")
                core.write_new_json(path, value)

            result = runner.execute_attempt_body(
                "2026-09-19T20:00:00Z",
                plan={"data_root": Path(temporary), "contract": {}},
                target=target,
                bindings={"synthetic": "a" * 64},
                identity_verifier=identity_verifier,
                arcpy_loader=arcpy_loader,
                dem_builder=dem_builder,
                support_builder=support_builder,
                source_processor=source_processor,
                route_processor=route_processor,
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
            }
        return snapshot

    def test_contract_exact_boundaries_and_inventory_comparator(self) -> None:
        contract = json.loads((ROOT / core.CONTRACT_REF).read_text(encoding="utf-8"))
        self.assertEqual(core.validate_contract(contract, ROOT), [])
        self.assertEqual(contract["fixed_source_order"], core.SOURCE_ORDER)
        self.assertEqual(contract["fixed_route_order"], core.ROUTE_ORDER)
        self.assertEqual(contract["stage_order"], list(core.STAGE_ORDER))
        self.assertEqual(contract["attempt"]["attempt_id"], core.ATTEMPT_ID)
        recovery_contract = json.loads((ROOT / core.RECOVERY_001_CONTRACT_REF).read_text(encoding="utf-8"))
        self.assertEqual(contract["inventory_comparison"], recovery_contract["inventory_comparison"])
        self.assertTrue(all(value is False for value in contract["claim_boundary"].values()))
        self.assertTrue(recovery_001.inventories_match([], []))

    def test_runner_has_function_local_datetime_and_delayed_arcpy(self) -> None:
        tree = ast.parse((ROOT / runner.RUNNER_REF).read_text(encoding="utf-8"))
        names: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        self.assertNotIn("datetime", names)
        self.assertNotIn("arcpy", names)
        self.assertNotIn("requests", names)
        with patch.object(runner, "datetime", object(), create=True):
            self.assertTrue(runner.now_utc().endswith("Z"))

    def test_success_preserves_order_and_receipts(self) -> None:
        result = self._run_fixture()
        self.assertEqual(result["result"], 0)
        self.assertEqual(result["events"][0:2], ["identity:1", "arcpy_import"])
        self.assertEqual(
            [item for item in result["events"] if item.startswith("source:")],
            [f"source:{source_id}" for source_id in core.SOURCE_ORDER],
        )
        self.assertEqual(
            [item for item in result["events"] if item.startswith("route:")],
            [f"route:{route_id}" for route_id in core.ROUTE_ORDER],
        )
        self.assertLess(result["events"].index("checkin:Spatial"), result["events"].index("checkin:ImageAnalyst"))
        self.assertEqual(core.stage_positions(result["stages"]), sorted(core.stage_positions(result["stages"])))
        self.assertEqual(result["terminal"]["status"], "pass_six_sources_two_routes_qa_only")
        self.assertEqual(result["cleanup"]["status"], "cleanup_completed")
        self.assertEqual(result["events"][-3:], ["identity:2", "checkin:Spatial", "checkin:ImageAnalyst"])

    def test_source_failure_stops_before_later_sources_and_routes(self) -> None:
        result = self._run_fixture(fail_source="M1-SRC-003")
        self.assertEqual(result["result"], 20)
        self.assertEqual(
            [item for item in result["events"] if item.startswith("source:")],
            ["source:M1-SRC-001", "source:M1-SRC-002", "source:M1-SRC-003"],
        )
        self.assertFalse(any(item.startswith("route:") for item in result["events"]))
        self.assertEqual(result["terminal"]["source_execution"]["stopped_source_id"], "M1-SRC-003")

    def test_route_failure_stops_before_later_route(self) -> None:
        result = self._run_fixture(fail_route=core.ROUTE_ORDER[0])
        self.assertEqual(result["result"], 20)
        self.assertEqual([item for item in result["events"] if item.startswith("route:")], [f"route:{core.ROUTE_ORDER[0]}"])
        self.assertEqual(result["terminal"]["stopped_route_id"], core.ROUTE_ORDER[0])

    def test_interruption_and_terminal_failure_preserve_first_sanitized_error(self) -> None:
        token = "eyJ" + "a" * 24 + "." + "b" * 24 + "." + "c" * 24
        error = KeyboardInterrupt(rf"first C:\Users\owner\secret\payload.bin bearer {token}")
        result = self._run_fixture(identity_error=error, fail_terminal_write=True)
        self.assertEqual(result["result"], 21)
        self.assertIsNone(result["terminal"])
        self.assertIsNotNone(result["cleanup"])
        self.assertEqual([item["event"] for item in result["fallback"]][:3], [
            "fallback_journal_initialized",
            "processing_exception_captured",
            "terminal_persistence_exception_captured",
        ])
        rendered = json.dumps(result["fallback"])
        self.assertNotIn(token, rendered)
        self.assertNotIn("owner", rendered)
        self.assertIn("KeyboardInterrupt", rendered)
        self.assertIn("forced-terminal-write-failure", rendered)

    def test_cleanup_is_independent_and_cleanup_failure_is_preserved(self) -> None:
        result = self._run_fixture(identity_error=RuntimeError("primary"), fail_terminal_write=True)
        self.assertEqual(result["result"], 21)
        self.assertEqual(result["cleanup"]["status"], "cleanup_completed")
        self.assertFalse(result["cleanup"]["terminal_persisted"])
        failed = self._run_fixture(identity_error=RuntimeError("primary"), fail_cleanup_write=True)
        self.assertEqual(failed["result"], 22)
        self.assertIn("cleanup_persistence_exception_captured", [item["event"] for item in failed["fallback"]])

    def test_cleanup_warning_fails_closed(self) -> None:
        result = self._run_fixture(checkin_failure=True)
        self.assertEqual(result["result"], 20)
        self.assertEqual(result["cleanup"]["status"], "cleanup_completed_with_warning")
        self.assertIn("spatial_checkin_exception_captured", [item["event"] for item in result["fallback"]])

    def test_append_only_attempt_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "attempt"
            target.mkdir()
            with self.assertRaisesRegex(Exception, "recovery_002_attempt_collision"):
                runner.execute_attempt_body(
                    "2026-09-19T20:00:00Z",
                    plan={"data_root": Path(temporary), "contract": {}},
                    target=target,
                    bindings={},
                )


if __name__ == "__main__":
    unittest.main()
