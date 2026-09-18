from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import m2_radar_pixel_orbit_application_001_core as base  # noqa: E402
import run_m2_radar_pixel_orbit_application_recovery_001 as runner  # noqa: E402
from m2_radar_pixel_orbit_application_recovery_001_core import (  # noqa: E402
    CONTRACT_REF,
    inventories_match,
    project_inventory,
    validate_recovery_contract,
    verify_external_identities,
)


class M2RadarPixelOrbitApplicationRecovery001Tests(unittest.TestCase):
    def test_contract_is_exact_and_preserves_scientific_boundaries(self) -> None:
        contract = json.loads((ROOT / CONTRACT_REF).read_text(encoding="utf-8"))
        self.assertEqual(validate_recovery_contract(contract, ROOT), [])
        self.assertEqual(contract["fixed_source_order"], base.SOURCE_ORDER)
        self.assertEqual(contract["fixed_route_order"], base.ROUTE_ORDER)
        self.assertEqual(contract["source_to_orbit"], base.SOURCE_TO_ORBIT)
        self.assertEqual(contract["attempt"]["attempt_id"], "radar-pixel-orbit-application-recovery-001-real-001")
        self.assertEqual(contract["attempt"]["maximum_real_attempts"], 1)
        self.assertFalse(contract["attempt"]["automatic_retry_authorized"])
        self.assertTrue(all(value is False for value in contract["claim_boundary"].values()))

    def test_projection_ignores_crc_and_archive_order_only(self) -> None:
        one = {"relative_path": "manifest.safe", "size_bytes": 8, "sha256": "a" * 64}
        two = {"relative_path": "measurement/vv.tiff", "size_bytes": 6, "sha256": "b" * 64}
        manifest = [{**two, "zip_crc32": "AABBCCDD"}, {**one, "zip_crc32": "11223344"}]
        runtime = [one, two]
        self.assertTrue(inventories_match(manifest, runtime))
        self.assertEqual(project_inventory(manifest, label="manifest"), runtime)

    def test_projection_rejects_duplicate_and_unsafe_paths(self) -> None:
        duplicate = [
            {"relative_path": "measurement/VV.tiff", "size_bytes": 1, "sha256": "a" * 64},
            {"relative_path": "measurement/vv.tiff", "size_bytes": 1, "sha256": "a" * 64},
        ]
        with self.assertRaises(base.RadarRouteError) as caught:
            project_inventory(duplicate, label="manifest")
        self.assertEqual(caught.exception.code, "inventory_duplicate_normalized_path")
        for unsafe in ("../escape", "/absolute", "a\\b", "a//b", "C:/escape"):
            with self.subTest(unsafe=unsafe), self.assertRaises(base.RadarRouteError) as caught:
                project_inventory(
                    [{"relative_path": unsafe, "size_bytes": 1, "sha256": "a" * 64}],
                    label="manifest",
                )
            self.assertEqual(caught.exception.code, "inventory_path_unsafe")

    def test_projection_retains_strict_size_and_sha_identity(self) -> None:
        original = [{"relative_path": "a.bin", "size_bytes": 4, "sha256": "a" * 64}]
        self.assertFalse(inventories_match(original, [{**original[0], "size_bytes": 5}]))
        self.assertFalse(inventories_match(original, [{**original[0], "sha256": "b" * 64}]))
        self.assertFalse(
            inventories_match(original, original + [{"relative_path": "b.bin", "size_bytes": 1, "sha256": "c" * 64}])
        )

    def test_external_identity_accepts_extra_crc_and_order_but_rejects_byte_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            data_root = Path(raw)
            safe_root = data_root / "source.SAFE"
            (safe_root / "measurement").mkdir(parents=True)
            files = {
                "manifest.safe": b"manifest",
                "measurement/vv.tiff": b"pixels",
            }
            for relative, content in files.items():
                path = safe_root / Path(relative)
                path.write_bytes(content)
            runtime = base.stable_inventory(safe_root)
            manifest = {
                "source_id": "M1-SRC-001",
                "exact_product_id": "EXACT",
                "files": [{**item, "zip_crc32": "00000000"} for item in reversed(runtime)],
            }
            manifest_path = data_root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            plan = {
                "data_root": data_root,
                "sources": [
                    {
                        "source_id": "M1-SRC-001",
                        "exact_product_id": "EXACT",
                        "external_manifest_path": str(manifest_path),
                        "external_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                        "safe_root": str(safe_root),
                    }
                ],
                "orbits": {},
                "dems": [],
            }
            result = verify_external_identities(plan)
            self.assertEqual(result["sources"]["M1-SRC-001"]["file_count"], 2)
            manifest["files"][0]["sha256"] = "f" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            plan["sources"][0]["external_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            with self.assertRaises(base.RadarRouteError) as caught:
                verify_external_identities(plan)
            self.assertEqual(caught.exception.code, "materialized_safe_inventory_mismatch")

    def test_started_attempt_gets_terminal_receipts_on_identity_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            temp = Path(raw)
            repo = temp / "repo"
            data = temp / "repo-data"
            repo.mkdir()
            data.mkdir()
            gate_path = repo / runner.PUBLICATION_GATE_REF
            gate_path.parent.mkdir(parents=True)
            gate_path.write_text("{}\n", encoding="utf-8")
            preflight_path = repo / runner.FINAL_PREFLIGHT_REF
            preflight_path.parent.mkdir(parents=True, exist_ok=True)
            preflight_path.write_text(
                json.dumps(
                    {
                        "status": "pass_final_no_content_preflight",
                        "bindings": {
                            "implementation_publication_gate_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest()
                        },
                    }
                ),
                encoding="utf-8",
            )
            attempt = data / "derived" / "radar-recovery" / "attempt-001"
            plan = {
                "data_root": data,
                "contract": {"attempt": {"external_attempt_root": str(attempt), "attempt_id": "radar-pixel-orbit-application-recovery-001-real-001"}},
                "contract_sha256": "1" * 64,
                "base_contract_sha256": "2" * 64,
            }
            interruption = base.RadarRouteError("synthetic_identity_interruption", "M1-SRC-001")
            with (
                patch.object(runner, "ROOT", repo),
                patch.object(runner, "publication_gate", return_value={"implementation_commit_sha": "3" * 40, "public_ci_run_id": 1}),
                patch.object(runner, "load_execution_plan", return_value=plan),
                patch.object(runner, "verify_external_identities", side_effect=interruption),
            ):
                result = runner.run_execute("2026-09-18T00:00:00Z")
            self.assertEqual(result, 20)
            self.assertTrue((attempt / "started.json").is_file())
            external_terminal = json.loads((attempt / "terminal.json").read_text(encoding="utf-8"))
            repo_terminal = json.loads((repo / runner.TERMINAL_REF).read_text(encoding="utf-8"))
            self.assertEqual(repo_terminal, external_terminal)
            self.assertEqual(repo_terminal["failure_code"], "synthetic_identity_interruption")
            self.assertTrue(repo_terminal["assertions"]["attempt_consumed"])
            self.assertFalse(repo_terminal["assertions"]["automatic_retry_performed"])

    def test_fixed_order_and_stop_on_failure_remain_unchanged(self) -> None:
        calls: list[str] = []

        def worker(source_id: str) -> dict:
            calls.append(source_id)
            if source_id == "M1-SRC-002":
                return {"source_id": source_id, "status": "failed_source_execution_no_retry"}
            return {"source_id": source_id, "status": "pass_source_qa_only"}

        result = base.execute_fixed_order(base.SOURCE_ORDER, worker)
        self.assertEqual(calls, base.SOURCE_ORDER[:2])
        self.assertEqual(result["stopped_source_id"], "M1-SRC-002")
        self.assertFalse(result["automatic_retry_performed"])

    def test_recovery_implementation_imports_no_network_library(self) -> None:
        imports: set[str] = set()
        for relative in (
            "scripts/m2_radar_pixel_orbit_application_recovery_001_core.py",
            "scripts/run_m2_radar_pixel_orbit_application_recovery_001.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
        self.assertTrue({"requests", "urllib", "http", "socket", "ftplib"}.isdisjoint(imports))

    def test_publication_gate_fails_closed_before_project_access(self) -> None:
        with tempfile.TemporaryDirectory() as raw, patch.object(runner, "ROOT", Path(raw)):
            with self.assertRaises(base.RadarRouteError) as caught:
                runner.publication_gate()
        self.assertEqual(caught.exception.code, "recovery_implementation_publication_gate_missing")


if __name__ == "__main__":
    unittest.main()
