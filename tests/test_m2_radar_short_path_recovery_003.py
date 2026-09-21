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

import m2_radar_short_path_recovery_003_core as core  # noqa: E402
import m2_radar_short_path_processing_003 as short_processing  # noqa: E402
import run_m2_radar_short_path_recovery_003 as runner  # noqa: E402


class _Environment:
    overwriteOutput = None


class _FakeArcPy:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.env = _Environment()

    def ProductInfo(self) -> str:
        self.events.append("product_info")
        return "ArcInfo"

    def CheckOutExtension(self, name: str) -> str:
        self.events.append(f"checkout:{name}")
        return "CheckedOut"

    def CheckInExtension(self, name: str) -> str:
        self.events.append(f"checkin:{name}")
        return "CheckedIn"


class M2RadarShortPathRecovery003Tests(unittest.TestCase):
    def _run_fixture(self, *, fail_source: str | None = None, fail_terminal_write: bool = False) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "attempt"
            events: list[str] = []
            scans = 0

            def identity_verifier(plan: dict) -> dict:
                nonlocal scans
                self.assertTrue((target / "terminal-reservation.json").is_file())
                self.assertTrue((target / "cleanup-reservation.json").is_file())
                scans += 1
                events.append(f"identity:{scans}")
                return {"identity": "stable"}

            def path_projector(plan: dict, attempt_root: Path) -> dict:
                events.append("path_projection")
                return {
                    "status": "pass_all_projected_paths_at_or_below_240",
                    "projected_path_count": 100,
                    "maximum_projected_path_characters": 240,
                    "maximum_allowed_path_characters": 240,
                    "longest_path_kind": "verified_safe_member",
                    "absolute_paths_recorded": False,
                }

            def source_processor(*, source_id: str, **kwargs) -> dict:
                events.append(f"source:{source_id}")
                return {"source_id": source_id, "status": "failed" if source_id == fail_source else "pass_source_qa_only"}

            def route_processor(*, route_id: str, **kwargs) -> dict:
                events.append(f"route:{route_id}")
                return {"route_id": route_id, "status": "pass_route_evaluated_qa_only"}

            def terminal_writer(path: Path, value: object) -> None:
                if fail_terminal_write:
                    raise OSError(r"forced C:\Users\owner\terminal failure")
                core.write_new_json(path, value)

            code = runner.execute_attempt_body(
                "2026-09-21T17:00:00Z",
                plan={"data_root": Path(temporary), "contract": {}},
                target=target,
                bindings={"synthetic": "a" * 64},
                identity_verifier=identity_verifier,
                path_projector=path_projector,
                arcpy_loader=lambda: _FakeArcPy(events),
                dem_builder=lambda *args: "dem",
                support_builder=lambda *args: {"synthetic": True},
                source_processor=source_processor,
                route_processor=route_processor,
                terminal_writer=terminal_writer,
            )
            read = lambda name: json.loads((target / name).read_text(encoding="utf-8")) if (target / name).is_file() else None
            stages = [json.loads(line)["stage"] for line in (target / "stages.jsonl").read_text(encoding="utf-8").splitlines()]
            fallback = [json.loads(line) for line in (target / "fallback.jsonl").read_text(encoding="utf-8").splitlines()]
            return {"code": code, "events": events, "terminal": read("terminal.json"), "cleanup": read("cleanup.json"), "stages": stages, "fallback": fallback}

    def test_contract_exact_and_one_attempt_boundary(self) -> None:
        contract = json.loads((ROOT / core.CONTRACT_REF).read_text(encoding="utf-8"))
        self.assertEqual(core.validate_contract(contract, ROOT), [])
        self.assertEqual(contract["short_path"]["observed_failed_manifest_path_characters"], 260)
        self.assertEqual(contract["short_path"]["maximum_predicted_full_path_characters"], 240)
        self.assertEqual(contract["short_path"]["first_blocked_path_characters"], 241)
        self.assertEqual(contract["short_path_source_aliases"], core.SOURCE_ALIASES)
        self.assertEqual(contract["attempt"]["maximum_real_attempts"], 1)
        self.assertFalse(contract["attempt"]["automatic_retry_authorized"])
        self.assertTrue(all(value is False for value in contract["claim_boundary"].values()))

    def test_delayed_arcpy_and_no_network_import(self) -> None:
        tree = ast.parse((ROOT / runner.RUNNER_REF).read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertNotIn("arcpy", imports)
        self.assertNotIn("requests", imports)

    def test_short_alias_and_attempt_local_receipts_do_not_touch_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            attempt = Path(temporary) / "a1"
            plan = {"contract": {"short_path_source_aliases": core.SOURCE_ALIASES, "attempt_local_receipts": True}}
            self.assertEqual(short_processing.source_output_root(plan, attempt, "M1-SRC-001"), attempt / "s" / "1")
            source_path, source_ref = short_processing.source_receipt_path(plan, attempt, "M1-SRC-001", "terminal")
            route_path, route_ref = short_processing.route_receipt_path(plan, attempt, core.ROUTE_ORDER[0], "terminal")
            self.assertEqual(source_path, attempt / "receipts" / "sources" / "m1-src-001-terminal.json")
            self.assertEqual(route_path.parent, attempt / "receipts" / "routes")
            self.assertFalse(Path(source_ref).is_absolute())
            self.assertFalse(Path(route_ref).is_absolute())

    def test_path_projection_240_passes_and_241_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary)
            target = data_root / "a1"
            target.mkdir()
            allowed = target / "started.json"
            allowed.write_text("{}", encoding="utf-8")
            path_240 = target / ("x" * (240 - len(str(target)) - 1))
            path_241 = target / ("x" * (241 - len(str(target)) - 1))
            plan = {"data_root": data_root}
            with patch.object(core, "ATTEMPT_ROOT", target), patch.object(core, "is_subst_drive", return_value=False), patch.object(core, "path_chain_has_reparse", return_value=False), patch.object(core, "_declared_paths", return_value=[("boundary", path_240)]):
                self.assertEqual(core.project_short_paths(plan, target)["maximum_projected_path_characters"], 240)
            with patch.object(core, "ATTEMPT_ROOT", target), patch.object(core, "is_subst_drive", return_value=False), patch.object(core, "path_chain_has_reparse", return_value=False), patch.object(core, "_declared_paths", return_value=[("boundary", path_241)]):
                with self.assertRaisesRegex(Exception, "short_path_projection_exceeds_240"):
                    core.project_short_paths(plan, target)

    def test_projection_rejects_collision_alternate_root_and_reparse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_root = Path(temporary)
            target = data_root / "a1"
            target.mkdir()
            candidate = target / "same.tif"
            plan = {"data_root": data_root}
            with patch.object(core, "ATTEMPT_ROOT", target), patch.object(core, "is_subst_drive", return_value=False), patch.object(core, "path_chain_has_reparse", return_value=False), patch.object(core, "_declared_paths", return_value=[("a", candidate), ("b", candidate)]):
                with self.assertRaisesRegex(Exception, "short_path_projected_collision"):
                    core.project_short_paths(plan, target)
            with patch.object(core, "ATTEMPT_ROOT", target), patch.object(core, "is_subst_drive", return_value=False), patch.object(core, "path_chain_has_reparse", return_value=True):
                with self.assertRaisesRegex(Exception, "short_path_reparse_point_prohibited"):
                    core.project_short_paths(plan, target)
            with patch.object(core, "ATTEMPT_ROOT", target):
                with self.assertRaisesRegex(Exception, "short_path_attempt_root_mismatch"):
                    core.project_short_paths(plan, data_root / "different")

    def test_success_preserves_fixed_order_stage_and_terminal_receipts(self) -> None:
        result = self._run_fixture()
        self.assertEqual(result["code"], 0)
        self.assertEqual(result["events"][:3], ["identity:1", "path_projection", "product_info"])
        self.assertEqual([x for x in result["events"] if x.startswith("source:")], [f"source:{x}" for x in core.SOURCE_ORDER])
        self.assertEqual([x for x in result["events"] if x.startswith("route:")], [f"route:{x}" for x in core.ROUTE_ORDER])
        self.assertEqual(core.stage_positions(result["stages"]), sorted(core.stage_positions(result["stages"])))
        self.assertEqual(result["terminal"]["status"], "pass_six_sources_two_routes_qa_only")
        self.assertEqual(result["terminal"]["path_projection"]["maximum_projected_path_characters"], 240)
        self.assertEqual(result["cleanup"]["status"], "cleanup_completed")

    def test_first_source_failure_stops_later_sources_routes_and_retry(self) -> None:
        result = self._run_fixture(fail_source="M1-SRC-003")
        self.assertEqual(result["code"], 20)
        self.assertEqual([x for x in result["events"] if x.startswith("source:")], ["source:M1-SRC-001", "source:M1-SRC-002", "source:M1-SRC-003"])
        self.assertFalse(any(x.startswith("route:") for x in result["events"]))
        self.assertFalse(result["terminal"]["assertions"]["automatic_retry_performed"])

    def test_terminal_failure_preserves_sanitized_fallback_and_cleanup(self) -> None:
        result = self._run_fixture(fail_terminal_write=True)
        self.assertEqual(result["code"], 21)
        self.assertIsNone(result["terminal"])
        self.assertFalse(result["cleanup"]["terminal_persisted"])
        rendered = json.dumps(result["fallback"])
        self.assertNotIn("owner", rendered)
        self.assertNotIn(r"C:\Users", rendered)
        self.assertIn("terminal_persistence_exception_captured", rendered)

    def test_secret_and_absolute_path_redaction(self) -> None:
        token = "eyJ" + "a" * 24 + "." + "b" * 24 + "." + "c" * 24
        safe = core.safe_error(RuntimeError(rf"bearer {token} C:\Users\owner\secret.bin"))
        rendered = json.dumps(safe)
        self.assertNotIn(token, rendered)
        self.assertNotIn("owner", rendered)
        self.assertIn("[REDACTED_TOKEN]", rendered)
        self.assertIn("[REDACTED_PATH]", rendered)


if __name__ == "__main__":
    unittest.main()
