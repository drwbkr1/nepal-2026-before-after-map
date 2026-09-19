from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import m2_radar_delayed_import_probe_001_core as core  # noqa: E402
import run_m2_radar_delayed_import_probe_001 as runner  # noqa: E402


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


def _fake_scan() -> dict:
    sizes = core.size_plan()
    return {
        "file_count": core.FILE_COUNT,
        "total_logical_bytes": core.TOTAL_LOGICAL_BYTES,
        "aggregate_sha256": "a" * 64,
        "elapsed_seconds": 1.25,
        "files": [
            {"name": name, "logical_bytes": size, "sha256": "b" * 64}
            for name, size in zip(core.CORPUS_NAMES, sizes, strict=True)
        ],
    }


class M2RadarDelayedImportProbe001Tests(unittest.TestCase):
    def test_size_plan_is_exact_and_balanced(self) -> None:
        sizes = core.size_plan()
        self.assertEqual(len(sizes), 156)
        self.assertEqual(sum(sizes), 10_367_157_634)
        self.assertLessEqual(max(sizes) - min(sizes), 1)

    def test_contract_stage_order_and_claim_boundary(self) -> None:
        contract = json.loads((ROOT / "config/qa/m2-radar-delayed-import-probe-001-contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["attempt"]["attempt_id"], core.ATTEMPT_ID)
        self.assertEqual(contract["stage_order"], list(core.STAGE_ORDER))
        self.assertEqual(contract["corpus"]["file_count"], 156)
        self.assertEqual(contract["corpus"]["total_logical_bytes"], 10_367_157_634)
        self.assertTrue(all(value is False for value in contract["claim_boundary"].values()))
        self.assertTrue(all(value is True for value in contract["forbidden"].values()))

    def test_runner_contains_no_top_level_arcpy_import(self) -> None:
        source = (ROOT / runner.RUNNER_REF).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        imported = []
        for node in imports:
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            else:
                imported.append(node.module or "")
        self.assertNotIn("arcpy", imported)
        self.assertNotIn("requests", imported)
        self.assertLess(source.index('"corpus_hash_completed"'), source.index('"arcpy_import"'))

    def _run_fixture(self, fail_at: str | None = None) -> tuple[int, list[str], list[str], dict, dict]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempt = root / "attempt"
            (root / "records/readiness").mkdir(parents=True)
            (root / "records/readiness/gate.json").write_text("{}\n", encoding="utf-8")
            (root / "records/readiness/preflight.json").write_text(
                json.dumps({
                    "status": "pass_final_no_content_preflight_one_probe_released",
                    "attempt_id": core.ATTEMPT_ID,
                    "bindings": {"implementation_publication_gate_sha256": core.sha256_file(root / "records/readiness/gate.json")},
                }) + "\n",
                encoding="utf-8",
            )
            events: list[str] = []

            def corpus_creator(path: Path) -> list[Path]:
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
                return _fake_scan()

            def arcpy_loader():
                events.append("arcpy_import")
                if fail_at == "arcpy_import":
                    raise RuntimeError("import-boundary")
                return _FakeArcPy(events, fail_at)

            gate = {"implementation_commit_sha": "c" * 40, "public_ci_run_id": 123}
            patches = (
                patch.object(runner, "ROOT", root),
                patch.object(runner, "PUBLICATION_GATE_REF", "records/readiness/gate.json"),
                patch.object(runner, "FINAL_PREFLIGHT_REF", "records/readiness/preflight.json"),
                patch.object(runner, "publication_gate", return_value=gate),
                patch.object(runner, "repository_bindings", return_value={"fixture": "d" * 64}),
                patch.object(runner, "attempt_root", return_value=attempt),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
                result = runner.execute_probe(
                    "2026-09-19T12:00:00Z",
                    arcpy_loader=arcpy_loader,
                    corpus_creator=corpus_creator,
                    corpus_scanner=corpus_scanner,
                )
            stages = [json.loads(line)["stage"] for line in (attempt / "stages.jsonl").read_text(encoding="utf-8").splitlines()]
            terminal = json.loads((attempt / "terminal.json").read_text(encoding="utf-8"))
            cleanup = json.loads((attempt / "cleanup.json").read_text(encoding="utf-8"))
            self.assertFalse((attempt / "corpus").exists())
            self.assertFalse((attempt / "scratch").exists())
            return result, events, stages, terminal, cleanup

    def test_success_is_full_exact_stage_order_and_reverse_checkin(self) -> None:
        result, events, stages, terminal, cleanup = self._run_fixture()
        self.assertEqual(result, 0)
        self.assertEqual(stages, list(core.STAGE_ORDER))
        self.assertLess(events.index("corpus_scan"), events.index("arcpy_import"))
        self.assertLess(events.index("checkin:Spatial"), events.index("checkin:ImageAnalyst"))
        self.assertEqual(terminal["status"], "pass_exact_disposable_delayed_import_sequence")
        self.assertEqual(len(terminal["corpus"]["inventory"]), 156)
        self.assertEqual(sum(item["logical_bytes"] for item in terminal["corpus"]["inventory"]), 10_367_157_634)
        self.assertEqual(cleanup["status"], "cleanup_completed")

    def test_four_historical_candidate_boundaries_are_terminal_no_retry(self) -> None:
        boundaries = ("arcpy_import", "overwrite_output", "checkout:ImageAnalyst", "checkout:Spatial")
        for boundary in boundaries:
            with self.subTest(boundary=boundary):
                result, events, stages, terminal, cleanup = self._run_fixture(boundary)
                self.assertEqual(result, 20)
                self.assertEqual(terminal["status"], "block_probe_failure_no_retry")
                self.assertTrue(terminal["assertions"]["attempt_consumed"])
                self.assertFalse(terminal["assertions"]["automatic_retry_performed"])
                self.assertIn("terminal_receipt_persisted", stages)
                self.assertEqual(stages[-1], "cleanup_completed_or_warning")
                self.assertEqual(cleanup["status"], "cleanup_completed")

    def test_error_sanitization_removes_token_and_paths(self) -> None:
        token = "eyJ" + "a" * 24 + "." + "b" * 24 + "." + "c" * 24
        error = RuntimeError(rf"failed C:\Users\owner\secret\payload.bin bearer {token}")
        safe = core.safe_error(error, (Path(r"C:\Users\owner\secret"),))
        rendered = json.dumps(safe)
        self.assertNotIn(token, rendered)
        self.assertNotIn("owner", rendered)
        self.assertIn("<REDACTED", rendered)

    def test_append_only_attempt_collision_fails_before_loader(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempt = root / "attempt"
            attempt.mkdir()
            (root / "gate.json").write_text("{}\n", encoding="utf-8")
            (root / "preflight.json").write_text(
                json.dumps({
                    "status": "pass_final_no_content_preflight_one_probe_released",
                    "attempt_id": core.ATTEMPT_ID,
                    "bindings": {"implementation_publication_gate_sha256": core.sha256_file(root / "gate.json")},
                }) + "\n",
                encoding="utf-8",
            )
            with (
                patch.object(runner, "ROOT", root),
                patch.object(runner, "PUBLICATION_GATE_REF", "gate.json"),
                patch.object(runner, "FINAL_PREFLIGHT_REF", "preflight.json"),
                patch.object(runner, "publication_gate", return_value={}),
                patch.object(runner, "attempt_root", return_value=attempt),
            ):
                with self.assertRaisesRegex(core.ProbeError, "probe_attempt_collision"):
                    runner.execute_probe("2026-09-19T12:00:00Z", arcpy_loader=lambda: self.fail("loader called"))

    def test_path_boundary_rejects_repository_and_external_roots(self) -> None:
        with self.assertRaisesRegex(core.ProbeError, "probe_path_inside_forbidden_root"):
            core.require_outside(ROOT / "disposable", (ROOT,))


if __name__ == "__main__":
    unittest.main()
