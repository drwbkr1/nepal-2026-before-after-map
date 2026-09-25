"""Disposable sequence tests for fixed order, bounded retry, and stop rules."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import m2_optical_pair_pilot_001_supervisor as supervisor  # noqa: E402
from m2_optical_pair_pilot_001_core import load_contract  # noqa: E402


class OpticalPilotSupervisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = copy.deepcopy(load_contract())
        self.contract["status"] = "conditional_public_ci_and_final_preflight_pending"

    def _common_patches(self, transfer):
        return (
            patch.object(supervisor, "load_contract", return_value=self.contract),
            patch.object(supervisor, "arcgis_runtime", return_value={"version": "3.7.1", "spatial": "Available"}),
            patch.object(supervisor, "final_preflight", return_value={"status": "pass_no_payload"}),
            patch.object(supervisor, "require_execution_release"),
            patch.object(supervisor, "one_transfer", side_effect=transfer),
        )

    def test_nontransport_failure_stops_before_after_source(self) -> None:
        calls = []

        def transfer(source, secret, **kwargs):
            calls.append((source["source_id"], secret))
            return {"status": "pilot_provider_md5_mismatch", "attempt_id": "synthetic-1"}

        with tempfile.TemporaryDirectory() as folder:
            patches = self._common_patches(transfer)
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                result = supervisor.run_sequence("synthetic-secret", journal=Path(folder))
        self.assertEqual(result["stage"], "transfer")
        self.assertEqual(calls, [("M2-OPT-001", "synthetic-secret")])
        self.assertNotIn("synthetic-secret", str(result))

    def test_only_one_fresh_retry_after_documented_transport_interruption(self) -> None:
        calls = []

        def transfer(source, secret, **kwargs):
            calls.append(source["source_id"])
            if len(calls) == 1:
                return {"status": "transport_interrupted", "attempt_id": "synthetic-1"}
            return {"status": "pilot_http_failure_nonretryable", "attempt_id": "synthetic-2"}

        with tempfile.TemporaryDirectory() as folder:
            patches = self._common_patches(transfer)
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                result = supervisor.run_sequence("synthetic-secret", journal=Path(folder))
        self.assertEqual(calls, ["M2-OPT-001", "M2-OPT-001"])
        self.assertEqual(result["terminal_code"], "pilot_http_failure_nonretryable")


if __name__ == "__main__":
    unittest.main()
